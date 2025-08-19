
# === NexusCore/tools\exports\export_20250803_114325\combined_52.py ===

# === NexusCore/openenv\Lib\site-packages\sortedcontainers\sortedlist.py ===
"""Sorted List
==============

:doc:`Sorted Containers<index>` is an Apache2 licensed Python sorted
collections library, written in pure-Python, and fast as C-extensions. The
:doc:`introduction<introduction>` is the best way to get started.

Sorted list implementations:

.. currentmodule:: sortedcontainers

* :class:`SortedList`
* :class:`SortedKeyList`

"""
# pylint: disable=too-many-lines
from __future__ import print_function

import sys
import traceback

from bisect import bisect_left, bisect_right, insort
from itertools import chain, repeat, starmap
from math import log
from operator import add, eq, ne, gt, ge, lt, le, iadd
from textwrap import dedent

###############################################################################
# BEGIN Python 2/3 Shims
###############################################################################

try:
    from collections.abc import Sequence, MutableSequence
except ImportError:
    from collections import Sequence, MutableSequence

from functools import wraps
from sys import hexversion

if hexversion < 0x03000000:
    from itertools import imap as map  # pylint: disable=redefined-builtin
    from itertools import izip as zip  # pylint: disable=redefined-builtin
    try:
        from thread import get_ident
    except ImportError:
        from dummy_thread import get_ident
else:
    from functools import reduce
    try:
        from _thread import get_ident
    except ImportError:
        from _dummy_thread import get_ident


def recursive_repr(fillvalue='...'):
    "Decorator to make a repr function return fillvalue for a recursive call."
    # pylint: disable=missing-docstring
    # Copied from reprlib in Python 3
    # https://hg.python.org/cpython/file/3.6/Lib/reprlib.py

    def decorating_function(user_function):
        repr_running = set()

        @wraps(user_function)
        def wrapper(self):
            key = id(self), get_ident()
            if key in repr_running:
                return fillvalue
            repr_running.add(key)
            try:
                result = user_function(self)
            finally:
                repr_running.discard(key)
            return result

        return wrapper

    return decorating_function

###############################################################################
# END Python 2/3 Shims
###############################################################################


class SortedList(MutableSequence):
    """Sorted list is a sorted mutable sequence.

    Sorted list values are maintained in sorted order.

    Sorted list values must be comparable. The total ordering of values must
    not change while they are stored in the sorted list.

    Methods for adding values:

    * :func:`SortedList.add`
    * :func:`SortedList.update`
    * :func:`SortedList.__add__`
    * :func:`SortedList.__iadd__`
    * :func:`SortedList.__mul__`
    * :func:`SortedList.__imul__`

    Methods for removing values:

    * :func:`SortedList.clear`
    * :func:`SortedList.discard`
    * :func:`SortedList.remove`
    * :func:`SortedList.pop`
    * :func:`SortedList.__delitem__`

    Methods for looking up values:

    * :func:`SortedList.bisect_left`
    * :func:`SortedList.bisect_right`
    * :func:`SortedList.count`
    * :func:`SortedList.index`
    * :func:`SortedList.__contains__`
    * :func:`SortedList.__getitem__`

    Methods for iterating values:

    * :func:`SortedList.irange`
    * :func:`SortedList.islice`
    * :func:`SortedList.__iter__`
    * :func:`SortedList.__reversed__`

    Methods for miscellany:

    * :func:`SortedList.copy`
    * :func:`SortedList.__len__`
    * :func:`SortedList.__repr__`
    * :func:`SortedList._check`
    * :func:`SortedList._reset`

    Sorted lists use lexicographical ordering semantics when compared to other
    sequences.

    Some methods of mutable sequences are not supported and will raise
    not-implemented error.

    """
    DEFAULT_LOAD_FACTOR = 1000


    def __init__(self, iterable=None, key=None):
        """Initialize sorted list instance.

        Optional `iterable` argument provides an initial iterable of values to
        initialize the sorted list.

        Runtime complexity: `O(n*log(n))`

        >>> sl = SortedList()
        >>> sl
        SortedList([])
        >>> sl = SortedList([3, 1, 2, 5, 4])
        >>> sl
        SortedList([1, 2, 3, 4, 5])

        :param iterable: initial values (optional)

        """
        assert key is None
        self._len = 0
        self._load = self.DEFAULT_LOAD_FACTOR
        self._lists = []
        self._maxes = []
        self._index = []
        self._offset = 0

        if iterable is not None:
            self._update(iterable)


    def __new__(cls, iterable=None, key=None):
        """Create new sorted list or sorted-key list instance.

        Optional `key`-function argument will return an instance of subtype
        :class:`SortedKeyList`.

        >>> sl = SortedList()
        >>> isinstance(sl, SortedList)
        True
        >>> sl = SortedList(key=lambda x: -x)
        >>> isinstance(sl, SortedList)
        True
        >>> isinstance(sl, SortedKeyList)
        True

        :param iterable: initial values (optional)
        :param key: function used to extract comparison key (optional)
        :return: sorted list or sorted-key list instance

        """
        # pylint: disable=unused-argument
        if key is None:
            return object.__new__(cls)
        else:
            if cls is SortedList:
                return object.__new__(SortedKeyList)
            else:
                raise TypeError('inherit SortedKeyList for key argument')


    @property
    def key(self):  # pylint: disable=useless-return
        """Function used to extract comparison key from values.

        Sorted list compares values directly so the key function is none.

        """
        return None


    def _reset(self, load):
        """Reset sorted list load factor.

        The `load` specifies the load-factor of the list. The default load
        factor of 1000 works well for lists from tens to tens-of-millions of
        values. Good practice is to use a value that is the cube root of the
        list size. With billions of elements, the best load factor depends on
        your usage. It's best to leave the load factor at the default until you
        start benchmarking.

        See :doc:`implementation` and :doc:`performance-scale` for more
        information.

        Runtime complexity: `O(n)`

        :param int load: load-factor for sorted list sublists

        """
        values = reduce(iadd, self._lists, [])
        self._clear()
        self._load = load
        self._update(values)


    def clear(self):
        """Remove all values from sorted list.

        Runtime complexity: `O(n)`

        """
        self._len = 0
        del self._lists[:]
        del self._maxes[:]
        del self._index[:]
        self._offset = 0

    _clear = clear


    def add(self, value):
        """Add `value` to sorted list.

        Runtime complexity: `O(log(n))` -- approximate.

        >>> sl = SortedList()
        >>> sl.add(3)
        >>> sl.add(1)
        >>> sl.add(2)
        >>> sl
        SortedList([1, 2, 3])

        :param value: value to add to sorted list

        """
        _lists = self._lists
        _maxes = self._maxes

        if _maxes:
            pos = bisect_right(_maxes, value)

            if pos == len(_maxes):
                pos -= 1
                _lists[pos].append(value)
                _maxes[pos] = value
            else:
                insort(_lists[pos], value)

            self._expand(pos)
        else:
            _lists.append([value])
            _maxes.append(value)

        self._len += 1


    def _expand(self, pos):
        """Split sublists with length greater than double the load-factor.

        Updates the index when the sublist length is less than double the load
        level. This requires incrementing the nodes in a traversal from the
        leaf node to the root. For an example traversal see
        ``SortedList._loc``.

        """
        _load = self._load
        _lists = self._lists
        _index = self._index

        if len(_lists[pos]) > (_load << 1):
            _maxes = self._maxes

            _lists_pos = _lists[pos]
            half = _lists_pos[_load:]
            del _lists_pos[_load:]
            _maxes[pos] = _lists_pos[-1]

            _lists.insert(pos + 1, half)
            _maxes.insert(pos + 1, half[-1])

            del _index[:]
        else:
            if _index:
                child = self._offset + pos
                while child:
                    _index[child] += 1
                    child = (child - 1) >> 1
                _index[0] += 1


    def update(self, iterable):
        """Update sorted list by adding all values from `iterable`.

        Runtime complexity: `O(k*log(n))` -- approximate.

        >>> sl = SortedList()
        >>> sl.update([3, 1, 2])
        >>> sl
        SortedList([1, 2, 3])

        :param iterable: iterable of values to add

        """
        _lists = self._lists
        _maxes = self._maxes
        values = sorted(iterable)

        if _maxes:
            if len(values) * 4 >= self._len:
                _lists.append(values)
                values = reduce(iadd, _lists, [])
                values.sort()
                self._clear()
            else:
                _add = self.add
                for val in values:
                    _add(val)
                return

        _load = self._load
        _lists.extend(values[pos:(pos + _load)]
                      for pos in range(0, len(values), _load))
        _maxes.extend(sublist[-1] for sublist in _lists)
        self._len = len(values)
        del self._index[:]

    _update = update


    def __contains__(self, value):
        """Return true if `value` is an element of the sorted list.

        ``sl.__contains__(value)`` <==> ``value in sl``

        Runtime complexity: `O(log(n))`

        >>> sl = SortedList([1, 2, 3, 4, 5])
        >>> 3 in sl
        True

        :param value: search for value in sorted list
        :return: true if `value` in sorted list

        """
        _maxes = self._maxes

        if not _maxes:
            return False

        pos = bisect_left(_maxes, value)

        if pos == len(_maxes):
            return False

        _lists = self._lists
        idx = bisect_left(_lists[pos], value)

        return _lists[pos][idx] == value


    def discard(self, value):
        """Remove `value` from sorted list if it is a member.

        If `value` is not a member, do nothing.

        Runtime complexity: `O(log(n))` -- approximate.

        >>> sl = SortedList([1, 2, 3, 4, 5])
        >>> sl.discard(5)
        >>> sl.discard(0)
        >>> sl == [1, 2, 3, 4]
        True

        :param value: `value` to discard from sorted list

        """
        _maxes = self._maxes

        if not _maxes:
            return

        pos = bisect_left(_maxes, value)

        if pos == len(_maxes):
            return

        _lists = self._lists
        idx = bisect_left(_lists[pos], value)

        if _lists[pos][idx] == value:
            self._delete(pos, idx)


    def remove(self, value):
        """Remove `value` from sorted list; `value` must be a member.

        If `value` is not a member, raise ValueError.

        Runtime complexity: `O(log(n))` -- approximate.

        >>> sl = SortedList([1, 2, 3, 4, 5])
        >>> sl.remove(5)
        >>> sl == [1, 2, 3, 4]
        True
        >>> sl.remove(0)
        Traceback (most recent call last):
          ...
        ValueError: 0 not in list

        :param value: `value` to remove from sorted list
        :raises ValueError: if `value` is not in sorted list

        """
        _maxes = self._maxes

        if not _maxes:
            raise ValueError('{0!r} not in list'.format(value))

        pos = bisect_left(_maxes, value)

        if pos == len(_maxes):
            raise ValueError('{0!r} not in list'.format(value))

        _lists = self._lists
        idx = bisect_left(_lists[pos], value)

        if _lists[pos][idx] == value:
            self._delete(pos, idx)
        else:
            raise ValueError('{0!r} not in list'.format(value))


    def _delete(self, pos, idx):
        """Delete value at the given `(pos, idx)`.

        Combines lists that are less than half the load level.

        Updates the index when the sublist length is more than half the load
        level. This requires decrementing the nodes in a traversal from the
        leaf node to the root. For an example traversal see
        ``SortedList._loc``.

        :param int pos: lists index
        :param int idx: sublist index

        """
        _lists = self._lists
        _maxes = self._maxes
        _index = self._index

        _lists_pos = _lists[pos]

        del _lists_pos[idx]
        self._len -= 1

        len_lists_pos = len(_lists_pos)

        if len_lists_pos > (self._load >> 1):
            _maxes[pos] = _lists_pos[-1]

            if _index:
                child = self._offset + pos
                while child > 0:
                    _index[child] -= 1
                    child = (child - 1) >> 1
                _index[0] -= 1
        elif len(_lists) > 1:
            if not pos:
                pos += 1

            prev = pos - 1
            _lists[prev].extend(_lists[pos])
            _maxes[prev] = _lists[prev][-1]

            del _lists[pos]
            del _maxes[pos]
            del _index[:]

            self._expand(prev)
        elif len_lists_pos:
            _maxes[pos] = _lists_pos[-1]
        else:
            del _lists[pos]
            del _maxes[pos]
            del _index[:]


    def _loc(self, pos, idx):
        """Convert an index pair (lists index, sublist index) into a single
        index number that corresponds to the position of the value in the
        sorted list.

        Many queries require the index be built. Details of the index are
        described in ``SortedList._build_index``.

        Indexing requires traversing the tree from a leaf node to the root. The
        parent of each node is easily computable at ``(pos - 1) // 2``.

        Left-child nodes are always at odd indices and right-child nodes are
        always at even indices.

        When traversing up from a right-child node, increment the total by the
        left-child node.

        The final index is the sum from traversal and the index in the sublist.

        For example, using the index from ``SortedList._build_index``::

            _index = 14 5 9 3 2 4 5
            _offset = 3

        Tree::

                 14
              5      9
            3   2  4   5

        Converting an index pair (2, 3) into a single index involves iterating
        like so:

        1. Starting at the leaf node: offset + alpha = 3 + 2 = 5. We identify
           the node as a left-child node. At such nodes, we simply traverse to
           the parent.

        2. At node 9, position 2, we recognize the node as a right-child node
           and accumulate the left-child in our total. Total is now 5 and we
           traverse to the parent at position 0.

        3. Iteration ends at the root.

        The index is then the sum of the total and sublist index: 5 + 3 = 8.

        :param int pos: lists index
        :param int idx: sublist index
        :return: index in sorted list

        """
        if not pos:
            return idx

        _index = self._index

        if not _index:
            self._build_index()

        total = 0

        # Increment pos to point in the index to len(self._lists[pos]).

        pos += self._offset

        # Iterate until reaching the root of the index tree at pos = 0.

        while pos:

            # Right-child nodes are at odd indices. At such indices
            # account the total below the left child node.

            if not pos & 1:
                total += _index[pos - 1]

            # Advance pos to the parent node.

            pos = (pos - 1) >> 1

        return total + idx


    def _pos(self, idx):
        """Convert an index into an index pair (lists index, sublist index)
        that can be used to access the corresponding lists position.

        Many queries require the index be built. Details of the index are
        described in ``SortedList._build_index``.

        Indexing requires traversing the tree to a leaf node. Each node has two
        children which are easily computable. Given an index, pos, the
        left-child is at ``pos * 2 + 1`` and the right-child is at ``pos * 2 +
        2``.

        When the index is less than the left-child, traversal moves to the
        left sub-tree. Otherwise, the index is decremented by the left-child
        and traversal moves to the right sub-tree.

        At a child node, the indexing pair is computed from the relative
        position of the child node as compared with the offset and the remaining
        index.

        For example, using the index from ``SortedList._build_index``::

            _index = 14 5 9 3 2 4 5
            _offset = 3

        Tree::

                 14
              5      9
            3   2  4   5

        Indexing position 8 involves iterating like so:

        1. Starting at the root, position 0, 8 is compared with the left-child
           node (5) which it is greater than. When greater the index is
           decremented and the position is updated to the right child node.

        2. At node 9 with index 3, we again compare the index to the left-child
           node with value 4. Because the index is the less than the left-child
           node, we simply traverse to the left.

        3. At node 4 with index 3, we recognize that we are at a leaf node and
           stop iterating.

        4. To compute the sublist index, we subtract the offset from the index
           of the leaf node: 5 - 3 = 2. To compute the index in the sublist, we
           simply use the index remaining from iteration. In this case, 3.

        The final index pair from our example is (2, 3) which corresponds to
        index 8 in the sorted list.

        :param int idx: index in sorted list
        :return: (lists index, sublist index) pair

        """
        if idx < 0:
            last_len = len(self._lists[-1])

            if (-idx) <= last_len:
                return len(self._lists) - 1, last_len + idx

            idx += self._len

            if idx < 0:
                raise IndexError('list index out of range')
        elif idx >= self._len:
            raise IndexError('list index out of range')

        if idx < len(self._lists[0]):
            return 0, idx

        _index = self._index

        if not _index:
            self._build_index()

        pos = 0
        child = 1
        len_index = len(_index)

        while child < len_index:
            index_child = _index[child]

            if idx < index_child:
                pos = child
            else:
                idx -= index_child
                pos = child + 1

            child = (pos << 1) + 1

        return (pos - self._offset, idx)


    def _build_index(self):
        """Build a positional index for indexing the sorted list.

        Indexes are represented as binary trees in a dense array notation
        similar to a binary heap.

        For example, given a lists representation storing integers::

            0: [1, 2, 3]
            1: [4, 5]
            2: [6, 7, 8, 9]
            3: [10, 11, 12, 13, 14]

        The first transformation maps the sub-lists by their length. The
        first row of the index is the length of the sub-lists::

            0: [3, 2, 4, 5]

        Each row after that is the sum of consecutive pairs of the previous
        row::

            1: [5, 9]
            2: [14]

        Finally, the index is built by concatenating these lists together::

            _index = [14, 5, 9, 3, 2, 4, 5]

        An offset storing the start of the first row is also stored::

            _offset = 3

        When built, the index can be used for efficient indexing into the list.
        See the comment and notes on ``SortedList._pos`` for details.

        """
        row0 = list(map(len, self._lists))

        if len(row0) == 1:
            self._index[:] = row0
            self._offset = 0
            return

        head = iter(row0)
        tail = iter(head)
        row1 = list(starmap(add, zip(head, tail)))

        if len(row0) & 1:
            row1.append(row0[-1])

        if len(row1) == 1:
            self._index[:] = row1 + row0
            self._offset = 1
            return

        size = 2 ** (int(log(len(row1) - 1, 2)) + 1)
        row1.extend(repeat(0, size - len(row1)))
        tree = [row0, row1]

        while len(tree[-1]) > 1:
            head = iter(tree[-1])
            tail = iter(head)
            row = list(starmap(add, zip(head, tail)))
            tree.append(row)

        reduce(iadd, reversed(tree), self._index)
        self._offset = size * 2 - 1


    def __delitem__(self, index):
        """Remove value at `index` from sorted list.

        ``sl.__delitem__(index)`` <==> ``del sl[index]``

        Supports slicing.

        Runtime complexity: `O(log(n))` -- approximate.

        >>> sl = SortedList('abcde')
        >>> del sl[2]
        >>> sl
        SortedList(['a', 'b', 'd', 'e'])
        >>> del sl[:2]
        >>> sl
        SortedList(['d', 'e'])

        :param index: integer or slice for indexing
        :raises IndexError: if index out of range

        """
        if isinstance(index, slice):
            start, stop, step = index.indices(self._len)

            if step == 1 and start < stop:
                if start == 0 and stop == self._len:
                    return self._clear()
                elif self._len <= 8 * (stop - start):
                    values = self._getitem(slice(None, start))
                    if stop < self._len:
                        values += self._getitem(slice(stop, None))
                    self._clear()
                    return self._update(values)

            indices = range(start, stop, step)

            # Delete items from greatest index to least so
            # that the indices remain valid throughout iteration.

            if step > 0:
                indices = reversed(indices)

            _pos, _delete = self._pos, self._delete

            for index in indices:
                pos, idx = _pos(index)
                _delete(pos, idx)
        else:
            pos, idx = self._pos(index)
            self._delete(pos, idx)


    def __getitem__(self, index):
        """Lookup value at `index` in sorted list.

        ``sl.__getitem__(index)`` <==> ``sl[index]``

        Supports slicing.

        Runtime complexity: `O(log(n))` -- approximate.

        >>> sl = SortedList('abcde')
        >>> sl[1]
        'b'
        >>> sl[-1]
        'e'
        >>> sl[2:5]
        ['c', 'd', 'e']

        :param index: integer or slice for indexing
        :return: value or list of values
        :raises IndexError: if index out of range

        """
        _lists = self._lists

        if isinstance(index, slice):
            start, stop, step = index.indices(self._len)

            if step == 1 and start < stop:
                # Whole slice optimization: start to stop slices the whole
                # sorted list.

                if start == 0 and stop == self._len:
                    return reduce(iadd, self._lists, [])

                start_pos, start_idx = self._pos(start)
                start_list = _lists[start_pos]
                stop_idx = start_idx + stop - start

                # Small slice optimization: start index and stop index are
                # within the start list.

                if len(start_list) >= stop_idx:
                    return start_list[start_idx:stop_idx]

                if stop == self._len:
                    stop_pos = len(_lists) - 1
                    stop_idx = len(_lists[stop_pos])
                else:
                    stop_pos, stop_idx = self._pos(stop)

                prefix = _lists[start_pos][start_idx:]
                middle = _lists[(start_pos + 1):stop_pos]
                result = reduce(iadd, middle, prefix)
                result += _lists[stop_pos][:stop_idx]

                return result

            if step == -1 and start > stop:
                result = self._getitem(slice(stop + 1, start + 1))
                result.reverse()
                return result

            # Return a list because a negative step could
            # reverse the order of the items and this could
            # be the desired behavior.

            indices = range(start, stop, step)
            return list(self._getitem(index) for index in indices)
        else:
            if self._len:
                if index == 0:
                    return _lists[0][0]
                elif index == -1:
                    return _lists[-1][-1]
            else:
                raise IndexError('list index out of range')

            if 0 <= index < len(_lists[0]):
                return _lists[0][index]

            len_last = len(_lists[-1])

            if -len_last < index < 0:
                return _lists[-1][len_last + index]

            pos, idx = self._pos(index)
            return _lists[pos][idx]

    _getitem = __getitem__


    def __setitem__(self, index, value):
        """Raise not-implemented error.

        ``sl.__setitem__(index, value)`` <==> ``sl[index] = value``

        :raises NotImplementedError: use ``del sl[index]`` and
            ``sl.add(value)`` instead

        """
        message = 'use ``del sl[index]`` and ``sl.add(value)`` instead'
        raise NotImplementedError(message)


    def __iter__(self):
        """Return an iterator over the sorted list.

        ``sl.__iter__()`` <==> ``iter(sl)``

        Iterating the sorted list while adding or deleting values may raise a
        :exc:`RuntimeError` or fail to iterate over all values.

        """
        return chain.from_iterable(self._lists)


    def __reversed__(self):
        """Return a reverse iterator over the sorted list.

        ``sl.__reversed__()`` <==> ``reversed(sl)``

        Iterating the sorted list while adding or deleting values may raise a
        :exc:`RuntimeError` or fail to iterate over all values.

        """
        return chain.from_iterable(map(reversed, reversed(self._lists)))


    def reverse(self):
        """Raise not-implemented error.

        Sorted list maintains values in ascending sort order. Values may not be
        reversed in-place.

        Use ``reversed(sl)`` for an iterator over values in descending sort
        order.

        Implemented to override `MutableSequence.reverse` which provides an
        erroneous default implementation.

        :raises NotImplementedError: use ``reversed(sl)`` instead

        """
        raise NotImplementedError('use ``reversed(sl)`` instead')


    def islice(self, start=None, stop=None, reverse=False):
        """Return an iterator that slices sorted list from `start` to `stop`.

        The `start` and `stop` index are treated inclusive and exclusive,
        respectively.

        Both `start` and `stop` default to `None` which is automatically
        inclusive of the beginning and end of the sorted list.

        When `reverse` is `True` the values are yielded from the iterator in
        reverse order; `reverse` defaults to `False`.

        >>> sl = SortedList('abcdefghij')
        >>> it = sl.islice(2, 6)
        >>> list(it)
        ['c', 'd', 'e', 'f']

        :param int start: start index (inclusive)
        :param int stop: stop index (exclusive)
        :param bool reverse: yield values in reverse order
        :return: iterator

        """
        _len = self._len

        if not _len:
            return iter(())

        start, stop, _ = slice(start, stop).indices(self._len)

        if start >= stop:
            return iter(())

        _pos = self._pos

        min_pos, min_idx = _pos(start)

        if stop == _len:
            max_pos = len(self._lists) - 1
            max_idx = len(self._lists[-1])
        else:
            max_pos, max_idx = _pos(stop)

        return self._islice(min_pos, min_idx, max_pos, max_idx, reverse)


    def _islice(self, min_pos, min_idx, max_pos, max_idx, reverse):
        """Return an iterator that slices sorted list using two index pairs.

        The index pairs are (min_pos, min_idx) and (max_pos, max_idx), the
        first inclusive and the latter exclusive. See `_pos` for details on how
        an index is converted to an index pair.

        When `reverse` is `True`, values are yielded from the iterator in
        reverse order.

        """
        _lists = self._lists

        if min_pos > max_pos:
            return iter(())

        if min_pos == max_pos:
            if reverse:
                indices = reversed(range(min_idx, max_idx))
                return map(_lists[min_pos].__getitem__, indices)

            indices = range(min_idx, max_idx)
            return map(_lists[min_pos].__getitem__, indices)

        next_pos = min_pos + 1

        if next_pos == max_pos:
            if reverse:
                min_indices = range(min_idx, len(_lists[min_pos]))
                max_indices = range(max_idx)
                return chain(
                    map(_lists[max_pos].__getitem__, reversed(max_indices)),
                    map(_lists[min_pos].__getitem__, reversed(min_indices)),
                )

            min_indices = range(min_idx, len(_lists[min_pos]))
            max_indices = range(max_idx)
            return chain(
                map(_lists[min_pos].__getitem__, min_indices),
                map(_lists[max_pos].__getitem__, max_indices),
            )

        if reverse:
            min_indices = range(min_idx, len(_lists[min_pos]))
            sublist_indices = range(next_pos, max_pos)
            sublists = map(_lists.__getitem__, reversed(sublist_indices))
            max_indices = range(max_idx)
            return chain(
                map(_lists[max_pos].__getitem__, reversed(max_indices)),
                chain.from_iterable(map(reversed, sublists)),
                map(_lists[min_pos].__getitem__, reversed(min_indices)),
            )

        min_indices = range(min_idx, len(_lists[min_pos]))
        sublist_indices = range(next_pos, max_pos)
        sublists = map(_lists.__getitem__, sublist_indices)
        max_indices = range(max_idx)
        return chain(
            map(_lists[min_pos].__getitem__, min_indices),
            chain.from_iterable(sublists),
            map(_lists[max_pos].__getitem__, max_indices),
        )


    def irange(self, minimum=None, maximum=None, inclusive=(True, True),
               reverse=False):
        """Create an iterator of values between `minimum` and `maximum`.

        Both `minimum` and `maximum` default to `None` which is automatically
        inclusive of the beginning and end of the sorted list.

        The argument `inclusive` is a pair of booleans that indicates whether
        the minimum and maximum ought to be included in the range,
        respectively. The default is ``(True, True)`` such that the range is
        inclusive of both minimum and maximum.

        When `reverse` is `True` the values are yielded from the iterator in
        reverse order; `reverse` defaults to `False`.

        >>> sl = SortedList('abcdefghij')
        >>> it = sl.irange('c', 'f')
        >>> list(it)
        ['c', 'd', 'e', 'f']

        :param minimum: minimum value to start iterating
        :param maximum: maximum value to stop iterating
        :param inclusive: pair of booleans
        :param bool reverse: yield values in reverse order
        :return: iterator

        """
        _maxes = self._maxes

        if not _maxes:
            return iter(())

        _lists = self._lists

        # Calculate the minimum (pos, idx) pair. By default this location
        # will be inclusive in our calculation.

        if minimum is None:
            min_pos = 0
            min_idx = 0
        else:
            if inclusive[0]:
                min_pos = bisect_left(_maxes, minimum)

                if min_pos == len(_maxes):
                    return iter(())

                min_idx = bisect_left(_lists[min_pos], minimum)
            else:
                min_pos = bisect_right(_maxes, minimum)

                if min_pos == len(_maxes):
                    return iter(())

                min_idx = bisect_right(_lists[min_pos], minimum)

        # Calculate the maximum (pos, idx) pair. By default this location
        # will be exclusive in our calculation.

        if maximum is None:
            max_pos = len(_maxes) - 1
            max_idx = len(_lists[max_pos])
        else:
            if inclusive[1]:
                max_pos = bisect_right(_maxes, maximum)

                if max_pos == len(_maxes):
                    max_pos -= 1
                    max_idx = len(_lists[max_pos])
                else:
                    max_idx = bisect_right(_lists[max_pos], maximum)
            else:
                max_pos = bisect_left(_maxes, maximum)

                if max_pos == len(_maxes):
                    max_pos -= 1
                    max_idx = len(_lists[max_pos])
                else:
                    max_idx = bisect_left(_lists[max_pos], maximum)

        return self._islice(min_pos, min_idx, max_pos, max_idx, reverse)


    def __len__(self):
        """Return the size of the sorted list.

        ``sl.__len__()`` <==> ``len(sl)``

        :return: size of sorted list

        """
        return self._len


    def bisect_left(self, value):
        """Return an index to insert `value` in the sorted list.

        If the `value` is already present, the insertion point will be before
        (to the left of) any existing values.

        Similar to the `bisect` module in the standard library.

        Runtime complexity: `O(log(n))` -- approximate.

        >>> sl = SortedList([10, 11, 12, 13, 14])
        >>> sl.bisect_left(12)
        2

        :param value: insertion index of value in sorted list
        :return: index

        """
        _maxes = self._maxes

        if not _maxes:
            return 0

        pos = bisect_left(_maxes, value)

        if pos == len(_maxes):
            return self._len

        idx = bisect_left(self._lists[pos], value)
        return self._loc(pos, idx)


    def bisect_right(self, value):
        """Return an index to insert `value` in the sorted list.

        Similar to `bisect_left`, but if `value` is already present, the
        insertion point will be after (to the right of) any existing values.

        Similar to the `bisect` module in the standard library.

        Runtime complexity: `O(log(n))` -- approximate.

        >>> sl = SortedList([10, 11, 12, 13, 14])
        >>> sl.bisect_right(12)
        3

        :param value: insertion index of value in sorted list
        :return: index

        """
        _maxes = self._maxes

        if not _maxes:
            return 0

        pos = bisect_right(_maxes, value)

        if pos == len(_maxes):
            return self._len

        idx = bisect_right(self._lists[pos], value)
        return self._loc(pos, idx)

    bisect = bisect_right
    _bisect_right = bisect_right


    def count(self, value):
        """Return number of occurrences of `value` in the sorted list.

        Runtime complexity: `O(log(n))` -- approximate.

        >>> sl = SortedList([1, 2, 2, 3, 3, 3, 4, 4, 4, 4])
        >>> sl.count(3)
        3

        :param value: value to count in sorted list
        :return: count

        """
        _maxes = self._maxes

        if not _maxes:
            return 0

        pos_left = bisect_left(_maxes, value)

        if pos_left == len(_maxes):
            return 0

        _lists = self._lists
        idx_left = bisect_left(_lists[pos_left], value)
        pos_right = bisect_right(_maxes, value)

        if pos_right == len(_maxes):
            return self._len - self._loc(pos_left, idx_left)

        idx_right = bisect_right(_lists[pos_right], value)

        if pos_left == pos_right:
            return idx_right - idx_left

        right = self._loc(pos_right, idx_right)
        left = self._loc(pos_left, idx_left)
        return right - left


    def copy(self):
        """Return a shallow copy of the sorted list.

        Runtime complexity: `O(n)`

        :return: new sorted list

        """
        return self.__class__(self)

    __copy__ = copy


    def append(self, value):
        """Raise not-implemented error.

        Implemented to override `MutableSequence.append` which provides an
        erroneous default implementation.

        :raises NotImplementedError: use ``sl.add(value)`` instead

        """
        raise NotImplementedError('use ``sl.add(value)`` instead')


    def extend(self, values):
        """Raise not-implemented error.

        Implemented to override `MutableSequence.extend` which provides an
        erroneous default implementation.

        :raises NotImplementedError: use ``sl.update(values)`` instead

        """
        raise NotImplementedError('use ``sl.update(values)`` instead')


    def insert(self, index, value):
        """Raise not-implemented error.

        :raises NotImplementedError: use ``sl.add(value)`` instead

        """
        raise NotImplementedError('use ``sl.add(value)`` instead')


    def pop(self, index=-1):
        """Remove and return value at `index` in sorted list.

        Raise :exc:`IndexError` if the sorted list is empty or index is out of
        range.

        Negative indices are supported.

        Runtime complexity: `O(log(n))` -- approximate.

        >>> sl = SortedList('abcde')
        >>> sl.pop()
        'e'
        >>> sl.pop(2)
        'c'
        >>> sl
        SortedList(['a', 'b', 'd'])

        :param int index: index of value (default -1)
        :return: value
        :raises IndexError: if index is out of range

        """
        if not self._len:
            raise IndexError('pop index out of range')

        _lists = self._lists

        if index == 0:
            val = _lists[0][0]
            self._delete(0, 0)
            return val

        if index == -1:
            pos = len(_lists) - 1
            loc = len(_lists[pos]) - 1
            val = _lists[pos][loc]
            self._delete(pos, loc)
            return val

        if 0 <= index < len(_lists[0]):
            val = _lists[0][index]
            self._delete(0, index)
            return val

        len_last = len(_lists[-1])

        if -len_last < index < 0:
            pos = len(_lists) - 1
            loc = len_last + index
            val = _lists[pos][loc]
            self._delete(pos, loc)
            return val

        pos, idx = self._pos(index)
        val = _lists[pos][idx]
        self._delete(pos, idx)
        return val


    def index(self, value, start=None, stop=None):
        """Return first index of value in sorted list.

        Raise ValueError if `value` is not present.

        Index must be between `start` and `stop` for the `value` to be
        considered present. The default value, None, for `start` and `stop`
        indicate the beginning and end of the sorted list.

        Negative indices are supported.

        Runtime complexity: `O(log(n))` -- approximate.

        >>> sl = SortedList('abcde')
        >>> sl.index('d')
        3
        >>> sl.index('z')
        Traceback (most recent call last):
          ...
        ValueError: 'z' is not in list

        :param value: value in sorted list
        :param int start: start index (default None, start of sorted list)
        :param int stop: stop index (default None, end of sorted list)
        :return: index of value
        :raises ValueError: if value is not present

        """
        _len = self._len

        if not _len:
            raise ValueError('{0!r} is not in list'.format(value))

        if start is None:
            start = 0
        if start < 0:
            start += _len
        if start < 0:
            start = 0

        if stop is None:
            stop = _len
        if stop < 0:
            stop += _len
        if stop > _len:
            stop = _len

        if stop <= start:
            raise ValueError('{0!r} is not in list'.format(value))

        _maxes = self._maxes
        pos_left = bisect_left(_maxes, value)

        if pos_left == len(_maxes):
            raise ValueError('{0!r} is not in list'.format(value))

        _lists = self._lists
        idx_left = bisect_left(_lists[pos_left], value)

        if _lists[pos_left][idx_left] != value:
            raise ValueError('{0!r} is not in list'.format(value))

        stop -= 1
        left = self._loc(pos_left, idx_left)

        if start <= left:
            if left <= stop:
                return left
        else:
            right = self._bisect_right(value) - 1

            if start <= right:
                return start

        raise ValueError('{0!r} is not in list'.format(value))


    def __add__(self, other):
        """Return new sorted list containing all values in both sequences.

        ``sl.__add__(other)`` <==> ``sl + other``

        Values in `other` do not need to be in sorted order.

        Runtime complexity: `O(n*log(n))`

        >>> sl1 = SortedList('bat')
        >>> sl2 = SortedList('cat')
        >>> sl1 + sl2
        SortedList(['a', 'a', 'b', 'c', 't', 't'])

        :param other: other iterable
        :return: new sorted list

        """
        values = reduce(iadd, self._lists, [])
        values.extend(other)
        return self.__class__(values)

    __radd__ = __add__


    def __iadd__(self, other):
        """Update sorted list with values from `other`.

        ``sl.__iadd__(other)`` <==> ``sl += other``

        Values in `other` do not need to be in sorted order.

        Runtime complexity: `O(k*log(n))` -- approximate.

        >>> sl = SortedList('bat')
        >>> sl += 'cat'
        >>> sl
        SortedList(['a', 'a', 'b', 'c', 't', 't'])

        :param other: other iterable
        :return: existing sorted list

        """
        self._update(other)
        return self


    def __mul__(self, num):
        """Return new sorted list with `num` shallow copies of values.

        ``sl.__mul__(num)`` <==> ``sl * num``

        Runtime complexity: `O(n*log(n))`

        >>> sl = SortedList('abc')
        >>> sl * 3
        SortedList(['a', 'a', 'a', 'b', 'b', 'b', 'c', 'c', 'c'])

        :param int num: count of shallow copies
        :return: new sorted list

        """
        values = reduce(iadd, self._lists, []) * num
        return self.__class__(values)

    __rmul__ = __mul__


    def __imul__(self, num):
        """Update the sorted list with `num` shallow copies of values.

        ``sl.__imul__(num)`` <==> ``sl *= num``

        Runtime complexity: `O(n*log(n))`

        >>> sl = SortedList('abc')
        >>> sl *= 3
        >>> sl
        SortedList(['a', 'a', 'a', 'b', 'b', 'b', 'c', 'c', 'c'])

        :param int num: count of shallow copies
        :return: existing sorted list

        """
        values = reduce(iadd, self._lists, []) * num
        self._clear()
        self._update(values)
        return self


    def __make_cmp(seq_op, symbol, doc):
        "Make comparator method."
        def comparer(self, other):
            "Compare method for sorted list and sequence."
            if not isinstance(other, Sequence):
                return NotImplemented

            self_len = self._len
            len_other = len(other)

            if self_len != len_other:
                if seq_op is eq:
                    return False
                if seq_op is ne:
                    return True

            for alpha, beta in zip(self, other):
                if alpha != beta:
                    return seq_op(alpha, beta)

            return seq_op(self_len, len_other)

        seq_op_name = seq_op.__name__
        comparer.__name__ = '__{0}__'.format(seq_op_name)
        doc_str = """Return true if and only if sorted list is {0} `other`.

        ``sl.__{1}__(other)`` <==> ``sl {2} other``

        Comparisons use lexicographical order as with sequences.

        Runtime complexity: `O(n)`

        :param other: `other` sequence
        :return: true if sorted list is {0} `other`

        """
        comparer.__doc__ = dedent(doc_str.format(doc, seq_op_name, symbol))
        return comparer


    __eq__ = __make_cmp(eq, '==', 'equal to')
    __ne__ = __make_cmp(ne, '!=', 'not equal to')
    __lt__ = __make_cmp(lt, '<', 'less than')
    __gt__ = __make_cmp(gt, '>', 'greater than')
    __le__ = __make_cmp(le, '<=', 'less than or equal to')
    __ge__ = __make_cmp(ge, '>=', 'greater than or equal to')
    __make_cmp = staticmethod(__make_cmp)


    def __reduce__(self):
        values = reduce(iadd, self._lists, [])
        return (type(self), (values,))


    @recursive_repr()
    def __repr__(self):
        """Return string representation of sorted list.

        ``sl.__repr__()`` <==> ``repr(sl)``

        :return: string representation

        """
        return '{0}({1!r})'.format(type(self).__name__, list(self))


    def _check(self):
        """Check invariants of sorted list.

        Runtime complexity: `O(n)`

        """
        try:
            assert self._load >= 4
            assert len(self._maxes) == len(self._lists)
            assert self._len == sum(len(sublist) for sublist in self._lists)

            # Check all sublists are sorted.

            for sublist in self._lists:
                for pos in range(1, len(sublist)):
                    assert sublist[pos - 1] <= sublist[pos]

            # Check beginning/end of sublists are sorted.

            for pos in range(1, len(self._lists)):
                assert self._lists[pos - 1][-1] <= self._lists[pos][0]

            # Check _maxes index is the last value of each sublist.

            for pos in range(len(self._maxes)):
                assert self._maxes[pos] == self._lists[pos][-1]

            # Check sublist lengths are less than double load-factor.

            double = self._load << 1
            assert all(len(sublist) <= double for sublist in self._lists)

            # Check sublist lengths are greater than half load-factor for all
            # but the last sublist.

            half = self._load >> 1
            for pos in range(0, len(self._lists) - 1):
                assert len(self._lists[pos]) >= half

            if self._index:
                assert self._len == self._index[0]
                assert len(self._index) == self._offset + len(self._lists)

                # Check index leaf nodes equal length of sublists.

                for pos in range(len(self._lists)):
                    leaf = self._index[self._offset + pos]
                    assert leaf == len(self._lists[pos])

                # Check index branch nodes are the sum of their children.

                for pos in range(self._offset):
                    child = (pos << 1) + 1
                    if child >= len(self._index):
                        assert self._index[pos] == 0
                    elif child + 1 == len(self._index):
                        assert self._index[pos] == self._index[child]
                    else:
                        child_sum = self._index[child] + self._index[child + 1]
                        assert child_sum == self._index[pos]
        except:
            traceback.print_exc(file=sys.stdout)
            print('len', self._len)
            print('load', self._load)
            print('offset', self._offset)
            print('len_index', len(self._index))
            print('index', self._index)
            print('len_maxes', len(self._maxes))
            print('maxes', self._maxes)
            print('len_lists', len(self._lists))
            print('lists', self._lists)
            raise


def identity(value):
    "Identity function."
    return value


class SortedKeyList(SortedList):
    """Sorted-key list is a subtype of sorted list.

    The sorted-key list maintains values in comparison order based on the
    result of a key function applied to every value.

    All the same methods that are available in :class:`SortedList` are also
    available in :class:`SortedKeyList`.

    Additional methods provided:

    * :attr:`SortedKeyList.key`
    * :func:`SortedKeyList.bisect_key_left`
    * :func:`SortedKeyList.bisect_key_right`
    * :func:`SortedKeyList.irange_key`

    Some examples below use:

    >>> from operator import neg
    >>> neg
    <built-in function neg>
    >>> neg(1)
    -1

    """
    def __init__(self, iterable=None, key=identity):
        """Initialize sorted-key list instance.

        Optional `iterable` argument provides an initial iterable of values to
        initialize the sorted-key list.

        Optional `key` argument defines a callable that, like the `key`
        argument to Python's `sorted` function, extracts a comparison key from
        each value. The default is the identity function.

        Runtime complexity: `O(n*log(n))`

        >>> from operator import neg
        >>> skl = SortedKeyList(key=neg)
        >>> skl
        SortedKeyList([], key=<built-in function neg>)
        >>> skl = SortedKeyList([3, 1, 2], key=neg)
        >>> skl
        SortedKeyList([3, 2, 1], key=<built-in function neg>)

        :param iterable: initial values (optional)
        :param key: function used to extract comparison key (optional)

        """
        self._key = key
        self._len = 0
        self._load = self.DEFAULT_LOAD_FACTOR
        self._lists = []
        self._keys = []
        self._maxes = []
        self._index = []
        self._offset = 0

        if iterable is not None:
            self._update(iterable)


    def __new__(cls, iterable=None, key=identity):
        return object.__new__(cls)


    @property
    def key(self):
        "Function used to extract comparison key from values."
        return self._key


    def clear(self):
        """Remove all values from sorted-key list.

        Runtime complexity: `O(n)`

        """
        self._len = 0
        del self._lists[:]
        del self._keys[:]
        del self._maxes[:]
        del self._index[:]

    _clear = clear


    def add(self, value):
        """Add `value` to sorted-key list.

        Runtime complexity: `O(log(n))` -- approximate.

        >>> from operator import neg
        >>> skl = SortedKeyList(key=neg)
        >>> skl.add(3)
        >>> skl.add(1)
        >>> skl.add(2)
        >>> skl
        SortedKeyList([3, 2, 1], key=<built-in function neg>)

        :param value: value to add to sorted-key list

        """
        _lists = self._lists
        _keys = self._keys
        _maxes = self._maxes

        key = self._key(value)

        if _maxes:
            pos = bisect_right(_maxes, key)

            if pos == len(_maxes):
                pos -= 1
                _lists[pos].append(value)
                _keys[pos].append(key)
                _maxes[pos] = key
            else:
                idx = bisect_right(_keys[pos], key)
                _lists[pos].insert(idx, value)
                _keys[pos].insert(idx, key)

            self._expand(pos)
        else:
            _lists.append([value])
            _keys.append([key])
            _maxes.append(key)

        self._len += 1


    def _expand(self, pos):
        """Split sublists with length greater than double the load-factor.

        Updates the index when the sublist length is less than double the load
        level. This requires incrementing the nodes in a traversal from the
        leaf node to the root. For an example traversal see
        ``SortedList._loc``.

        """
        _lists = self._lists
        _keys = self._keys
        _index = self._index

        if len(_keys[pos]) > (self._load << 1):
            _maxes = self._maxes
            _load = self._load

            _lists_pos = _lists[pos]
            _keys_pos = _keys[pos]
            half = _lists_pos[_load:]
            half_keys = _keys_pos[_load:]
            del _lists_pos[_load:]
            del _keys_pos[_load:]
            _maxes[pos] = _keys_pos[-1]

            _lists.insert(pos + 1, half)
            _keys.insert(pos + 1, half_keys)
            _maxes.insert(pos + 1, half_keys[-1])

            del _index[:]
        else:
            if _index:
                child = self._offset + pos
                while child:
                    _index[child] += 1
                    child = (child - 1) >> 1
                _index[0] += 1


    def update(self, iterable):
        """Update sorted-key list by adding all values from `iterable`.

        Runtime complexity: `O(k*log(n))` -- approximate.

        >>> from operator import neg
        >>> skl = SortedKeyList(key=neg)
        >>> skl.update([3, 1, 2])
        >>> skl
        SortedKeyList([3, 2, 1], key=<built-in function neg>)

        :param iterable: iterable of values to add

        """
        _lists = self._lists
        _keys = self._keys
        _maxes = self._maxes
        values = sorted(iterable, key=self._key)

        if _maxes:
            if len(values) * 4 >= self._len:
                _lists.append(values)
                values = reduce(iadd, _lists, [])
                values.sort(key=self._key)
                self._clear()
            else:
                _add = self.add
                for val in values:
                    _add(val)
                return

        _load = self._load
        _lists.extend(values[pos:(pos + _load)]
                      for pos in range(0, len(values), _load))
        _keys.extend(list(map(self._key, _list)) for _list in _lists)
        _maxes.extend(sublist[-1] for sublist in _keys)
        self._len = len(values)
        del self._index[:]

    _update = update


    def __contains__(self, value):
        """Return true if `value` is an element of the sorted-key list.

        ``skl.__contains__(value)`` <==> ``value in skl``

        Runtime complexity: `O(log(n))`

        >>> from operator import neg
        >>> skl = SortedKeyList([1, 2, 3, 4, 5], key=neg)
        >>> 3 in skl
        True

        :param value: search for value in sorted-key list
        :return: true if `value` in sorted-key list

        """
        _maxes = self._maxes

        if not _maxes:
            return False

        key = self._key(value)
        pos = bisect_left(_maxes, key)

        if pos == len(_maxes):
            return False

        _lists = self._lists
        _keys = self._keys

        idx = bisect_left(_keys[pos], key)

        len_keys = len(_keys)
        len_sublist = len(_keys[pos])

        while True:
            if _keys[pos][idx] != key:
                return False
            if _lists[pos][idx] == value:
                return True
            idx += 1
            if idx == len_sublist:
                pos += 1
                if pos == len_keys:
                    return False
                len_sublist = len(_keys[pos])
                idx = 0


    def discard(self, value):
        """Remove `value` from sorted-key list if it is a member.

        If `value` is not a member, do nothing.

        Runtime complexity: `O(log(n))` -- approximate.

        >>> from operator import neg
        >>> skl = SortedKeyList([5, 4, 3, 2, 1], key=neg)
        >>> skl.discard(1)
        >>> skl.discard(0)
        >>> skl == [5, 4, 3, 2]
        True

        :param value: `value` to discard from sorted-key list

        """
        _maxes = self._maxes

        if not _maxes:
            return

        key = self._key(value)
        pos = bisect_left(_maxes, key)

        if pos == len(_maxes):
            return

        _lists = self._lists
        _keys = self._keys
        idx = bisect_left(_keys[pos], key)
        len_keys = len(_keys)
        len_sublist = len(_keys[pos])

        while True:
            if _keys[pos][idx] != key:
                return
            if _lists[pos][idx] == value:
                self._delete(pos, idx)
                return
            idx += 1
            if idx == len_sublist:
                pos += 1
                if pos == len_keys:
                    return
                len_sublist = len(_keys[pos])
                idx = 0


    def remove(self, value):
        """Remove `value` from sorted-key list; `value` must be a member.

        If `value` is not a member, raise ValueError.

        Runtime complexity: `O(log(n))` -- approximate.

        >>> from operator import neg
        >>> skl = SortedKeyList([1, 2, 3, 4, 5], key=neg)
        >>> skl.remove(5)
        >>> skl == [4, 3, 2, 1]
        True
        >>> skl.remove(0)
        Traceback (most recent call last):
          ...
        ValueError: 0 not in list

        :param value: `value` to remove from sorted-key list
        :raises ValueError: if `value` is not in sorted-key list

        """
        _maxes = self._maxes

        if not _maxes:
            raise ValueError('{0!r} not in list'.format(value))

        key = self._key(value)
        pos = bisect_left(_maxes, key)

        if pos == len(_maxes):
            raise ValueError('{0!r} not in list'.format(value))

        _lists = self._lists
        _keys = self._keys
        idx = bisect_left(_keys[pos], key)
        len_keys = len(_keys)
        len_sublist = len(_keys[pos])

        while True:
            if _keys[pos][idx] != key:
                raise ValueError('{0!r} not in list'.format(value))
            if _lists[pos][idx] == value:
                self._delete(pos, idx)
                return
            idx += 1
            if idx == len_sublist:
                pos += 1
                if pos == len_keys:
                    raise ValueError('{0!r} not in list'.format(value))
                len_sublist = len(_keys[pos])
                idx = 0


    def _delete(self, pos, idx):
        """Delete value at the given `(pos, idx)`.

        Combines lists that are less than half the load level.

        Updates the index when the sublist length is more than half the load
        level. This requires decrementing the nodes in a traversal from the
        leaf node to the root. For an example traversal see
        ``SortedList._loc``.

        :param int pos: lists index
        :param int idx: sublist index

        """
        _lists = self._lists
        _keys = self._keys
        _maxes = self._maxes
        _index = self._index
        keys_pos = _keys[pos]
        lists_pos = _lists[pos]

        del keys_pos[idx]
        del lists_pos[idx]
        self._len -= 1

        len_keys_pos = len(keys_pos)

        if len_keys_pos > (self._load >> 1):
            _maxes[pos] = keys_pos[-1]

            if _index:
                child = self._offset + pos
                while child > 0:
                    _index[child] -= 1
                    child = (child - 1) >> 1
                _index[0] -= 1
        elif len(_keys) > 1:
            if not pos:
                pos += 1

            prev = pos - 1
            _keys[prev].extend(_keys[pos])
            _lists[prev].extend(_lists[pos])
            _maxes[prev] = _keys[prev][-1]

            del _lists[pos]
            del _keys[pos]
            del _maxes[pos]
            del _index[:]

            self._expand(prev)
        elif len_keys_pos:
            _maxes[pos] = keys_pos[-1]
        else:
            del _lists[pos]
            del _keys[pos]
            del _maxes[pos]
            del _index[:]


    def irange(self, minimum=None, maximum=None, inclusive=(True, True),
               reverse=False):
        """Create an iterator of values between `minimum` and `maximum`.

        Both `minimum` and `maximum` default to `None` which is automatically
        inclusive of the beginning and end of the sorted-key list.

        The argument `inclusive` is a pair of booleans that indicates whether
        the minimum and maximum ought to be included in the range,
        respectively. The default is ``(True, True)`` such that the range is
        inclusive of both minimum and maximum.

        When `reverse` is `True` the values are yielded from the iterator in
        reverse order; `reverse` defaults to `False`.

        >>> from operator import neg
        >>> skl = SortedKeyList([11, 12, 13, 14, 15], key=neg)
        >>> it = skl.irange(14.5, 11.5)
        >>> list(it)
        [14, 13, 12]

        :param minimum: minimum value to start iterating
        :param maximum: maximum value to stop iterating
        :param inclusive: pair of booleans
        :param bool reverse: yield values in reverse order
        :return: iterator

        """
        min_key = self._key(minimum) if minimum is not None else None
        max_key = self._key(maximum) if maximum is not None else None
        return self._irange_key(
            min_key=min_key, max_key=max_key,
            inclusive=inclusive, reverse=reverse,
        )


    def irange_key(self, min_key=None, max_key=None, inclusive=(True, True),
                   reverse=False):
        """Create an iterator of values between `min_key` and `max_key`.

        Both `min_key` and `max_key` default to `None` which is automatically
        inclusive of the beginning and end of the sorted-key list.

        The argument `inclusive` is a pair of booleans that indicates whether
        the minimum and maximum ought to be included in the range,
        respectively. The default is ``(True, True)`` such that the range is
        inclusive of both minimum and maximum.

        When `reverse` is `True` the values are yielded from the iterator in
        reverse order; `reverse` defaults to `False`.

        >>> from operator import neg
        >>> skl = SortedKeyList([11, 12, 13, 14, 15], key=neg)
        >>> it = skl.irange_key(-14, -12)
        >>> list(it)
        [14, 13, 12]

        :param min_key: minimum key to start iterating
        :param max_key: maximum key to stop iterating
        :param inclusive: pair of booleans
        :param bool reverse: yield values in reverse order
        :return: iterator

        """
        _maxes = self._maxes

        if not _maxes:
            return iter(())

        _keys = self._keys

        # Calculate the minimum (pos, idx) pair. By default this location
        # will be inclusive in our calculation.

        if min_key is None:
            min_pos = 0
            min_idx = 0
        else:
            if inclusive[0]:
                min_pos = bisect_left(_maxes, min_key)

                if min_pos == len(_maxes):
                    return iter(())

                min_idx = bisect_left(_keys[min_pos], min_key)
            else:
                min_pos = bisect_right(_maxes, min_key)

                if min_pos == len(_maxes):
                    return iter(())

                min_idx = bisect_right(_keys[min_pos], min_key)

        # Calculate the maximum (pos, idx) pair. By default this location
        # will be exclusive in our calculation.

        if max_key is None:
            max_pos = len(_maxes) - 1
            max_idx = len(_keys[max_pos])
        else:
            if inclusive[1]:
                max_pos = bisect_right(_maxes, max_key)

                if max_pos == len(_maxes):
                    max_pos -= 1
                    max_idx = len(_keys[max_pos])
                else:
                    max_idx = bisect_right(_keys[max_pos], max_key)
            else:
                max_pos = bisect_left(_maxes, max_key)

                if max_pos == len(_maxes):
                    max_pos -= 1
                    max_idx = len(_keys[max_pos])
                else:
                    max_idx = bisect_left(_keys[max_pos], max_key)

        return self._islice(min_pos, min_idx, max_pos, max_idx, reverse)

    _irange_key = irange_key


    def bisect_left(self, value):
        """Return an index to insert `value` in the sorted-key list.

        If the `value` is already present, the insertion point will be before
        (to the left of) any existing values.

        Similar to the `bisect` module in the standard library.

        Runtime complexity: `O(log(n))` -- approximate.

        >>> from operator import neg
        >>> skl = SortedKeyList([5, 4, 3, 2, 1], key=neg)
        >>> skl.bisect_left(1)
        4

        :param value: insertion index of value in sorted-key list
        :return: index

        """
        return self._bisect_key_left(self._key(value))


    def bisect_right(self, value):
        """Return an index to insert `value` in the sorted-key list.

        Similar to `bisect_left`, but if `value` is already present, the
        insertion point will be after (to the right of) any existing values.

        Similar to the `bisect` module in the standard library.

        Runtime complexity: `O(log(n))` -- approximate.

        >>> from operator import neg
        >>> skl = SortedList([5, 4, 3, 2, 1], key=neg)
        >>> skl.bisect_right(1)
        5

        :param value: insertion index of value in sorted-key list
        :return: index

        """
        return self._bisect_key_right(self._key(value))

    bisect = bisect_right


    def bisect_key_left(self, key):
        """Return an index to insert `key` in the sorted-key list.

        If the `key` is already present, the insertion point will be before (to
        the left of) any existing keys.

        Similar to the `bisect` module in the standard library.

        Runtime complexity: `O(log(n))` -- approximate.

        >>> from operator import neg
        >>> skl = SortedKeyList([5, 4, 3, 2, 1], key=neg)
        >>> skl.bisect_key_left(-1)
        4

        :param key: insertion index of key in sorted-key list
        :return: index

        """
        _maxes = self._maxes

        if not _maxes:
            return 0

        pos = bisect_left(_maxes, key)

        if pos == len(_maxes):
            return self._len

        idx = bisect_left(self._keys[pos], key)

        return self._loc(pos, idx)

    _bisect_key_left = bisect_key_left


    def bisect_key_right(self, key):
        """Return an index to insert `key` in the sorted-key list.

        Similar to `bisect_key_left`, but if `key` is already present, the
        insertion point will be after (to the right of) any existing keys.

        Similar to the `bisect` module in the standard library.

        Runtime complexity: `O(log(n))` -- approximate.

        >>> from operator import neg
        >>> skl = SortedList([5, 4, 3, 2, 1], key=neg)
        >>> skl.bisect_key_right(-1)
        5

        :param key: insertion index of key in sorted-key list
        :return: index

        """
        _maxes = self._maxes

        if not _maxes:
            return 0

        pos = bisect_right(_maxes, key)

        if pos == len(_maxes):
            return self._len

        idx = bisect_right(self._keys[pos], key)

        return self._loc(pos, idx)

    bisect_key = bisect_key_right
    _bisect_key_right = bisect_key_right


    def count(self, value):
        """Return number of occurrences of `value` in the sorted-key list.

        Runtime complexity: `O(log(n))` -- approximate.

        >>> from operator import neg
        >>> skl = SortedKeyList([4, 4, 4, 4, 3, 3, 3, 2, 2, 1], key=neg)
        >>> skl.count(2)
        2

        :param value: value to count in sorted-key list
        :return: count

        """
        _maxes = self._maxes

        if not _maxes:
            return 0

        key = self._key(value)
        pos = bisect_left(_maxes, key)

        if pos == len(_maxes):
            return 0

        _lists = self._lists
        _keys = self._keys
        idx = bisect_left(_keys[pos], key)
        total = 0
        len_keys = len(_keys)
        len_sublist = len(_keys[pos])

        while True:
            if _keys[pos][idx] != key:
                return total
            if _lists[pos][idx] == value:
                total += 1
            idx += 1
            if idx == len_sublist:
                pos += 1
                if pos == len_keys:
                    return total
                len_sublist = len(_keys[pos])
                idx = 0


    def copy(self):
        """Return a shallow copy of the sorted-key list.

        Runtime complexity: `O(n)`

        :return: new sorted-key list

        """
        return self.__class__(self, key=self._key)

    __copy__ = copy


    def index(self, value, start=None, stop=None):
        """Return first index of value in sorted-key list.

        Raise ValueError if `value` is not present.

        Index must be between `start` and `stop` for the `value` to be
        considered present. The default value, None, for `start` and `stop`
        indicate the beginning and end of the sorted-key list.

        Negative indices are supported.

        Runtime complexity: `O(log(n))` -- approximate.

        >>> from operator import neg
        >>> skl = SortedKeyList([5, 4, 3, 2, 1], key=neg)
        >>> skl.index(2)
        3
        >>> skl.index(0)
        Traceback (most recent call last):
          ...
        ValueError: 0 is not in list

        :param value: value in sorted-key list
        :param int start: start index (default None, start of sorted-key list)
        :param int stop: stop index (default None, end of sorted-key list)
        :return: index of value
        :raises ValueError: if value is not present

        """
        _len = self._len

        if not _len:
            raise ValueError('{0!r} is not in list'.format(value))

        if start is None:
            start = 0
        if start < 0:
            start += _len
        if start < 0:
            start = 0

        if stop is None:
            stop = _len
        if stop < 0:
            stop += _len
        if stop > _len:
            stop = _len

        if stop <= start:
            raise ValueError('{0!r} is not in list'.format(value))

        _maxes = self._maxes
        key = self._key(value)
        pos = bisect_left(_maxes, key)

        if pos == len(_maxes):
            raise ValueError('{0!r} is not in list'.format(value))

        stop -= 1
        _lists = self._lists
        _keys = self._keys
        idx = bisect_left(_keys[pos], key)
        len_keys = len(_keys)
        len_sublist = len(_keys[pos])

        while True:
            if _keys[pos][idx] != key:
                raise ValueError('{0!r} is not in list'.format(value))
            if _lists[pos][idx] == value:
                loc = self._loc(pos, idx)
                if start <= loc <= stop:
                    return loc
                elif loc > stop:
                    break
            idx += 1
            if idx == len_sublist:
                pos += 1
                if pos == len_keys:
                    raise ValueError('{0!r} is not in list'.format(value))
                len_sublist = len(_keys[pos])
                idx = 0

        raise ValueError('{0!r} is not in list'.format(value))


    def __add__(self, other):
        """Return new sorted-key list containing all values in both sequences.

        ``skl.__add__(other)`` <==> ``skl + other``

        Values in `other` do not need to be in sorted-key order.

        Runtime complexity: `O(n*log(n))`

        >>> from operator import neg
        >>> skl1 = SortedKeyList([5, 4, 3], key=neg)
        >>> skl2 = SortedKeyList([2, 1, 0], key=neg)
        >>> skl1 + skl2
        SortedKeyList([5, 4, 3, 2, 1, 0], key=<built-in function neg>)

        :param other: other iterable
        :return: new sorted-key list

        """
        values = reduce(iadd, self._lists, [])
        values.extend(other)
        return self.__class__(values, key=self._key)

    __radd__ = __add__


    def __mul__(self, num):
        """Return new sorted-key list with `num` shallow copies of values.

        ``skl.__mul__(num)`` <==> ``skl * num``

        Runtime complexity: `O(n*log(n))`

        >>> from operator import neg
        >>> skl = SortedKeyList([3, 2, 1], key=neg)
        >>> skl * 2
        SortedKeyList([3, 3, 2, 2, 1, 1], key=<built-in function neg>)

        :param int num: count of shallow copies
        :return: new sorted-key list

        """
        values = reduce(iadd, self._lists, []) * num
        return self.__class__(values, key=self._key)


    def __reduce__(self):
        values = reduce(iadd, self._lists, [])
        return (type(self), (values, self.key))


    @recursive_repr()
    def __repr__(self):
        """Return string representation of sorted-key list.

        ``skl.__repr__()`` <==> ``repr(skl)``

        :return: string representation

        """
        type_name = type(self).__name__
        return '{0}({1!r}, key={2!r})'.format(type_name, list(self), self._key)


    def _check(self):
        """Check invariants of sorted-key list.

        Runtime complexity: `O(n)`

        """
        try:
            assert self._load >= 4
            assert len(self._maxes) == len(self._lists) == len(self._keys)
            assert self._len == sum(len(sublist) for sublist in self._lists)

            # Check all sublists are sorted.

            for sublist in self._keys:
                for pos in range(1, len(sublist)):
                    assert sublist[pos - 1] <= sublist[pos]

            # Check beginning/end of sublists are sorted.

            for pos in range(1, len(self._keys)):
                assert self._keys[pos - 1][-1] <= self._keys[pos][0]

            # Check _keys matches _key mapped to _lists.

            for val_sublist, key_sublist in zip(self._lists, self._keys):
                assert len(val_sublist) == len(key_sublist)
                for val, key in zip(val_sublist, key_sublist):
                    assert self._key(val) == key

            # Check _maxes index is the last value of each sublist.

            for pos in range(len(self._maxes)):
                assert self._maxes[pos] == self._keys[pos][-1]

            # Check sublist lengths are less than double load-factor.

            double = self._load << 1
            assert all(len(sublist) <= double for sublist in self._lists)

            # Check sublist lengths are greater than half load-factor for all
            # but the last sublist.

            half = self._load >> 1
            for pos in range(0, len(self._lists) - 1):
                assert len(self._lists[pos]) >= half

            if self._index:
                assert self._len == self._index[0]
                assert len(self._index) == self._offset + len(self._lists)

                # Check index leaf nodes equal length of sublists.

                for pos in range(len(self._lists)):
                    leaf = self._index[self._offset + pos]
                    assert leaf == len(self._lists[pos])

                # Check index branch nodes are the sum of their children.

                for pos in range(self._offset):
                    child = (pos << 1) + 1
                    if child >= len(self._index):
                        assert self._index[pos] == 0
                    elif child + 1 == len(self._index):
                        assert self._index[pos] == self._index[child]
                    else:
                        child_sum = self._index[child] + self._index[child + 1]
                        assert child_sum == self._index[pos]
        except:
            traceback.print_exc(file=sys.stdout)
            print('len', self._len)
            print('load', self._load)
            print('offset', self._offset)
            print('len_index', len(self._index))
            print('index', self._index)
            print('len_maxes', len(self._maxes))
            print('maxes', self._maxes)
            print('len_keys', len(self._keys))
            print('keys', self._keys)
            print('len_lists', len(self._lists))
            print('lists', self._lists)
            raise


SortedListWithKey = SortedKeyList

# === NexusCore/openenv\Lib\site-packages\litellm\llms\custom_httpx\llm_http_handler.py ===
import json
from typing import (
    TYPE_CHECKING,
    Any,
    AsyncIterator,
    Coroutine,
    Dict,
    List,
    Literal,
    Optional,
    Tuple,
    Union,
    cast,
)

import httpx  # type: ignore

import litellm
import litellm.litellm_core_utils
import litellm.types
import litellm.types.utils
from litellm._logging import verbose_logger
from litellm.litellm_core_utils.realtime_streaming import RealTimeStreaming
from litellm.llms.base_llm.anthropic_messages.transformation import (
    BaseAnthropicMessagesConfig,
)
from litellm.llms.base_llm.audio_transcription.transformation import (
    BaseAudioTranscriptionConfig,
)
from litellm.llms.base_llm.base_model_iterator import MockResponseIterator
from litellm.llms.base_llm.chat.transformation import BaseConfig
from litellm.llms.base_llm.embedding.transformation import BaseEmbeddingConfig
from litellm.llms.base_llm.files.transformation import BaseFilesConfig
from litellm.llms.base_llm.image_edit.transformation import BaseImageEditConfig
from litellm.llms.base_llm.realtime.transformation import BaseRealtimeConfig
from litellm.llms.base_llm.rerank.transformation import BaseRerankConfig
from litellm.llms.base_llm.responses.transformation import BaseResponsesAPIConfig
from litellm.llms.custom_httpx.http_handler import (
    AsyncHTTPHandler,
    HTTPHandler,
    _get_httpx_client,
    get_async_httpx_client,
)
from litellm.responses.streaming_iterator import (
    BaseResponsesAPIStreamingIterator,
    MockResponsesAPIStreamingIterator,
    ResponsesAPIStreamingIterator,
    SyncResponsesAPIStreamingIterator,
)
from litellm.types.llms.anthropic_messages.anthropic_response import (
    AnthropicMessagesResponse,
)
from litellm.types.llms.openai import (
    CreateFileRequest,
    OpenAIFileObject,
    ResponseInputParam,
    ResponsesAPIResponse,
)
from litellm.types.rerank import OptionalRerankParams, RerankResponse
from litellm.types.responses.main import DeleteResponseResult
from litellm.types.router import GenericLiteLLMParams
from litellm.types.utils import EmbeddingResponse, FileTypes, TranscriptionResponse
from litellm.utils import (
    CustomStreamWrapper,
    ImageResponse,
    ModelResponse,
    ProviderConfigManager,
)

if TYPE_CHECKING:
    from litellm.litellm_core_utils.litellm_logging import Logging as _LiteLLMLoggingObj

    LiteLLMLoggingObj = _LiteLLMLoggingObj
else:
    LiteLLMLoggingObj = Any


class BaseLLMHTTPHandler:
    async def _make_common_async_call(
        self,
        async_httpx_client: AsyncHTTPHandler,
        provider_config: BaseConfig,
        api_base: str,
        headers: dict,
        data: dict,
        timeout: Union[float, httpx.Timeout],
        litellm_params: dict,
        logging_obj: LiteLLMLoggingObj,
        stream: bool = False,
        signed_json_body: Optional[bytes] = None,
    ) -> httpx.Response:
        """Common implementation across stream + non-stream calls. Meant to ensure consistent error-handling."""
        max_retry_on_unprocessable_entity_error = (
            provider_config.max_retry_on_unprocessable_entity_error
        )

        response: Optional[httpx.Response] = None
        for i in range(max(max_retry_on_unprocessable_entity_error, 1)):
            try:
                response = await async_httpx_client.post(
                    url=api_base,
                    headers=headers,
                    data=(
                        signed_json_body
                        if signed_json_body is not None
                        else json.dumps(data)
                    ),
                    timeout=timeout,
                    stream=stream,
                    logging_obj=logging_obj,
                )
            except httpx.HTTPStatusError as e:
                hit_max_retry = i + 1 == max_retry_on_unprocessable_entity_error
                should_retry = provider_config.should_retry_llm_api_inside_llm_translation_on_http_error(
                    e=e, litellm_params=litellm_params
                )
                if should_retry and not hit_max_retry:
                    data = (
                        provider_config.transform_request_on_unprocessable_entity_error(
                            e=e, request_data=data
                        )
                    )
                    continue
                else:
                    raise self._handle_error(e=e, provider_config=provider_config)
            except Exception as e:
                raise self._handle_error(e=e, provider_config=provider_config)
            break

        if response is None:
            raise provider_config.get_error_class(
                error_message="No response from the API",
                status_code=422,  # don't retry on this error
                headers={},
            )

        return response

    def _make_common_sync_call(
        self,
        sync_httpx_client: HTTPHandler,
        provider_config: BaseConfig,
        api_base: str,
        headers: dict,
        data: dict,
        timeout: Union[float, httpx.Timeout],
        litellm_params: dict,
        logging_obj: LiteLLMLoggingObj,
        stream: bool = False,
        signed_json_body: Optional[bytes] = None,
    ) -> httpx.Response:
        max_retry_on_unprocessable_entity_error = (
            provider_config.max_retry_on_unprocessable_entity_error
        )

        response: Optional[httpx.Response] = None

        for i in range(max(max_retry_on_unprocessable_entity_error, 1)):
            try:
                response = sync_httpx_client.post(
                    url=api_base,
                    headers=headers,
                    data=(
                        signed_json_body
                        if signed_json_body is not None
                        else json.dumps(data)
                    ),
                    timeout=timeout,
                    stream=stream,
                    logging_obj=logging_obj,
                )
            except httpx.HTTPStatusError as e:
                hit_max_retry = i + 1 == max_retry_on_unprocessable_entity_error
                should_retry = provider_config.should_retry_llm_api_inside_llm_translation_on_http_error(
                    e=e, litellm_params=litellm_params
                )
                if should_retry and not hit_max_retry:
                    data = (
                        provider_config.transform_request_on_unprocessable_entity_error(
                            e=e, request_data=data
                        )
                    )
                    continue
                else:
                    raise self._handle_error(e=e, provider_config=provider_config)
            except Exception as e:
                raise self._handle_error(e=e, provider_config=provider_config)
            break

        if response is None:
            raise provider_config.get_error_class(
                error_message="No response from the API",
                status_code=422,  # don't retry on this error
                headers={},
            )

        return response

    async def async_completion(
        self,
        custom_llm_provider: str,
        provider_config: BaseConfig,
        api_base: str,
        headers: dict,
        data: dict,
        timeout: Union[float, httpx.Timeout],
        model: str,
        model_response: ModelResponse,
        logging_obj: LiteLLMLoggingObj,
        messages: list,
        optional_params: dict,
        litellm_params: dict,
        encoding: Any,
        api_key: Optional[str] = None,
        client: Optional[AsyncHTTPHandler] = None,
        json_mode: bool = False,
        signed_json_body: Optional[bytes] = None,
    ):
        if client is None:
            async_httpx_client = get_async_httpx_client(
                llm_provider=litellm.LlmProviders(custom_llm_provider),
                params={"ssl_verify": litellm_params.get("ssl_verify", None)},
            )
        else:
            async_httpx_client = client

        response = await self._make_common_async_call(
            async_httpx_client=async_httpx_client,
            provider_config=provider_config,
            api_base=api_base,
            headers=headers,
            data=data,
            timeout=timeout,
            litellm_params=litellm_params,
            stream=False,
            logging_obj=logging_obj,
            signed_json_body=signed_json_body,
        )
        return provider_config.transform_response(
            model=model,
            raw_response=response,
            model_response=model_response,
            logging_obj=logging_obj,
            api_key=api_key,
            request_data=data,
            messages=messages,
            optional_params=optional_params,
            litellm_params=litellm_params,
            encoding=encoding,
            json_mode=json_mode,
        )

    def completion(
        self,
        model: str,
        messages: list,
        api_base: str,
        custom_llm_provider: str,
        model_response: ModelResponse,
        encoding,
        logging_obj: LiteLLMLoggingObj,
        optional_params: dict,
        timeout: Union[float, httpx.Timeout],
        litellm_params: dict,
        acompletion: bool,
        stream: Optional[bool] = False,
        fake_stream: bool = False,
        api_key: Optional[str] = None,
        headers: Optional[Dict[str, Any]] = None,
        client: Optional[Union[HTTPHandler, AsyncHTTPHandler]] = None,
        provider_config: Optional[BaseConfig] = None,
    ):
        json_mode: bool = optional_params.pop("json_mode", False)
        extra_body: Optional[dict] = optional_params.pop("extra_body", None)

        provider_config = (
            provider_config
            or ProviderConfigManager.get_provider_chat_config(
                model=model, provider=litellm.LlmProviders(custom_llm_provider)
            )
        )
        if provider_config is None:
            raise ValueError(
                f"Provider config not found for model: {model} and provider: {custom_llm_provider}"
            )

        fake_stream = (
            fake_stream
            or optional_params.pop("fake_stream", False)
            or provider_config.should_fake_stream(
                model=model, custom_llm_provider=custom_llm_provider, stream=stream
            )
        )

        # get config from model, custom llm provider
        headers = provider_config.validate_environment(
            api_key=api_key,
            headers=headers or {},
            model=model,
            messages=messages,
            optional_params=optional_params,
            api_base=api_base,
            litellm_params=litellm_params,
        )

        api_base = provider_config.get_complete_url(
            api_base=api_base,
            api_key=api_key,
            model=model,
            optional_params=optional_params,
            stream=stream,
            litellm_params=litellm_params,
        )

        data = provider_config.transform_request(
            model=model,
            messages=messages,
            optional_params=optional_params,
            litellm_params=litellm_params,
            headers=headers,
        )

        if extra_body is not None:
            data = {**data, **extra_body}

        headers, signed_json_body = provider_config.sign_request(
            headers=headers,
            optional_params=optional_params,
            request_data=data,
            api_base=api_base,
            stream=stream,
            fake_stream=fake_stream,
            model=model,
        )

        ## LOGGING
        logging_obj.pre_call(
            input=messages,
            api_key=api_key,
            additional_args={
                "complete_input_dict": data,
                "api_base": api_base,
                "headers": headers,
            },
        )

        if acompletion is True:
            if stream is True:
                data = self._add_stream_param_to_request_body(
                    data=data,
                    provider_config=provider_config,
                    fake_stream=fake_stream,
                )
                return self.acompletion_stream_function(
                    model=model,
                    messages=messages,
                    api_base=api_base,
                    headers=headers,
                    custom_llm_provider=custom_llm_provider,
                    provider_config=provider_config,
                    timeout=timeout,
                    logging_obj=logging_obj,
                    data=data,
                    fake_stream=fake_stream,
                    client=(
                        client
                        if client is not None and isinstance(client, AsyncHTTPHandler)
                        else None
                    ),
                    litellm_params=litellm_params,
                    json_mode=json_mode,
                    optional_params=optional_params,
                    signed_json_body=signed_json_body,
                )

            else:
                return self.async_completion(
                    custom_llm_provider=custom_llm_provider,
                    provider_config=provider_config,
                    api_base=api_base,
                    headers=headers,
                    data=data,
                    timeout=timeout,
                    model=model,
                    model_response=model_response,
                    logging_obj=logging_obj,
                    api_key=api_key,
                    messages=messages,
                    optional_params=optional_params,
                    litellm_params=litellm_params,
                    encoding=encoding,
                    client=(
                        client
                        if client is not None and isinstance(client, AsyncHTTPHandler)
                        else None
                    ),
                    json_mode=json_mode,
                    signed_json_body=signed_json_body,
                )

        if stream is True:
            data = self._add_stream_param_to_request_body(
                data=data,
                provider_config=provider_config,
                fake_stream=fake_stream,
            )
            if provider_config.has_custom_stream_wrapper is True:
                return provider_config.get_sync_custom_stream_wrapper(
                    model=model,
                    custom_llm_provider=custom_llm_provider,
                    logging_obj=logging_obj,
                    api_base=api_base,
                    headers=headers,
                    data=data,
                    signed_json_body=signed_json_body,
                    messages=messages,
                    client=client,
                    json_mode=json_mode,
                )
            completion_stream, headers = self.make_sync_call(
                provider_config=provider_config,
                api_base=api_base,
                headers=headers,  # type: ignore
                data=data,
                signed_json_body=signed_json_body,
                original_data=data,
                model=model,
                messages=messages,
                logging_obj=logging_obj,
                timeout=timeout,
                fake_stream=fake_stream,
                client=(
                    client
                    if client is not None and isinstance(client, HTTPHandler)
                    else None
                ),
                litellm_params=litellm_params,
                json_mode=json_mode,
                optional_params=optional_params,
            )
            return CustomStreamWrapper(
                completion_stream=completion_stream,
                model=model,
                custom_llm_provider=custom_llm_provider,
                logging_obj=logging_obj,
            )

        if client is None or not isinstance(client, HTTPHandler):
            sync_httpx_client = _get_httpx_client(
                params={"ssl_verify": litellm_params.get("ssl_verify", None)}
            )
        else:
            sync_httpx_client = client

        response = self._make_common_sync_call(
            sync_httpx_client=sync_httpx_client,
            provider_config=provider_config,
            api_base=api_base,
            headers=headers,
            data=data,
            signed_json_body=signed_json_body,
            timeout=timeout,
            litellm_params=litellm_params,
            logging_obj=logging_obj,
        )
        return provider_config.transform_response(
            model=model,
            raw_response=response,
            model_response=model_response,
            logging_obj=logging_obj,
            api_key=api_key,
            request_data=data,
            messages=messages,
            optional_params=optional_params,
            litellm_params=litellm_params,
            encoding=encoding,
            json_mode=json_mode,
        )

    def make_sync_call(
        self,
        provider_config: BaseConfig,
        api_base: str,
        headers: dict,
        data: dict,
        signed_json_body: Optional[bytes],
        original_data: dict,
        model: str,
        messages: list,
        logging_obj,
        optional_params: dict,
        litellm_params: dict,
        timeout: Union[float, httpx.Timeout],
        fake_stream: bool = False,
        client: Optional[HTTPHandler] = None,
        json_mode: bool = False,
    ) -> Tuple[Any, dict]:
        if client is None or not isinstance(client, HTTPHandler):
            sync_httpx_client = _get_httpx_client(
                {
                    "ssl_verify": litellm_params.get("ssl_verify", None),
                }
            )
        else:
            sync_httpx_client = client
        stream = True
        if fake_stream is True:
            stream = False

        response = self._make_common_sync_call(
            sync_httpx_client=sync_httpx_client,
            provider_config=provider_config,
            api_base=api_base,
            headers=headers,
            data=data,
            signed_json_body=signed_json_body,
            timeout=timeout,
            litellm_params=litellm_params,
            stream=stream,
            logging_obj=logging_obj,
        )

        if fake_stream is True:
            model_response: ModelResponse = provider_config.transform_response(
                model=model,
                raw_response=response,
                model_response=litellm.ModelResponse(),
                logging_obj=logging_obj,
                request_data=original_data,
                messages=messages,
                optional_params=optional_params,
                litellm_params=litellm_params,
                encoding=None,
                json_mode=json_mode,
            )

            completion_stream: Any = MockResponseIterator(
                model_response=model_response, json_mode=json_mode
            )
        else:
            completion_stream = provider_config.get_model_response_iterator(
                streaming_response=response.iter_lines(),
                sync_stream=True,
                json_mode=json_mode,
            )

        # LOGGING
        logging_obj.post_call(
            input=messages,
            api_key="",
            original_response="first stream response received",
            additional_args={"complete_input_dict": data},
        )

        return completion_stream, dict(response.headers)

    async def acompletion_stream_function(
        self,
        model: str,
        messages: list,
        api_base: str,
        custom_llm_provider: str,
        headers: dict,
        provider_config: BaseConfig,
        timeout: Union[float, httpx.Timeout],
        logging_obj: LiteLLMLoggingObj,
        data: dict,
        litellm_params: dict,
        optional_params: dict,
        fake_stream: bool = False,
        client: Optional[AsyncHTTPHandler] = None,
        json_mode: Optional[bool] = None,
        signed_json_body: Optional[bytes] = None,
    ):
        if provider_config.has_custom_stream_wrapper is True:
            return await provider_config.get_async_custom_stream_wrapper(
                model=model,
                custom_llm_provider=custom_llm_provider,
                logging_obj=logging_obj,
                api_base=api_base,
                headers=headers,
                data=data,
                messages=messages,
                client=client,
                json_mode=json_mode,
                signed_json_body=signed_json_body,
            )

        completion_stream, _response_headers = await self.make_async_call_stream_helper(
            model=model,
            custom_llm_provider=custom_llm_provider,
            provider_config=provider_config,
            api_base=api_base,
            headers=headers,
            data=data,
            messages=messages,
            logging_obj=logging_obj,
            timeout=timeout,
            fake_stream=fake_stream,
            client=client,
            litellm_params=litellm_params,
            optional_params=optional_params,
            json_mode=json_mode,
            signed_json_body=signed_json_body,
        )
        streamwrapper = CustomStreamWrapper(
            completion_stream=completion_stream,
            model=model,
            custom_llm_provider=custom_llm_provider,
            logging_obj=logging_obj,
        )
        return streamwrapper

    async def make_async_call_stream_helper(
        self,
        model: str,
        custom_llm_provider: str,
        provider_config: BaseConfig,
        api_base: str,
        headers: dict,
        data: dict,
        messages: list,
        logging_obj: LiteLLMLoggingObj,
        timeout: Union[float, httpx.Timeout],
        litellm_params: dict,
        optional_params: dict,
        fake_stream: bool = False,
        client: Optional[AsyncHTTPHandler] = None,
        json_mode: Optional[bool] = None,
        signed_json_body: Optional[bytes] = None,
    ) -> Tuple[Any, httpx.Headers]:
        """
        Helper function for making an async call with stream.

        Handles fake stream as well.
        """
        if client is None:
            async_httpx_client = get_async_httpx_client(
                llm_provider=litellm.LlmProviders(custom_llm_provider),
                params={"ssl_verify": litellm_params.get("ssl_verify", None)},
            )
        else:
            async_httpx_client = client
        stream = True
        if fake_stream is True:
            stream = False

        response = await self._make_common_async_call(
            async_httpx_client=async_httpx_client,
            provider_config=provider_config,
            api_base=api_base,
            headers=headers,
            data=data,
            signed_json_body=signed_json_body,
            timeout=timeout,
            litellm_params=litellm_params,
            stream=stream,
            logging_obj=logging_obj,
        )

        if fake_stream is True:
            model_response: ModelResponse = provider_config.transform_response(
                model=model,
                raw_response=response,
                model_response=litellm.ModelResponse(),
                logging_obj=logging_obj,
                request_data=data,
                messages=messages,
                optional_params=optional_params,
                litellm_params=litellm_params,
                encoding=None,
                json_mode=json_mode,
            )

            completion_stream: Any = MockResponseIterator(
                model_response=model_response, json_mode=json_mode
            )
        else:
            completion_stream = provider_config.get_model_response_iterator(
                streaming_response=response.aiter_lines(), sync_stream=False
            )
        # LOGGING
        logging_obj.post_call(
            input=messages,
            api_key="",
            original_response="first stream response received",
            additional_args={"complete_input_dict": data},
        )

        return completion_stream, response.headers

    def _add_stream_param_to_request_body(
        self,
        data: dict,
        provider_config: BaseConfig,
        fake_stream: bool,
    ) -> dict:
        """
        Some providers like Bedrock invoke do not support the stream parameter in the request body, we only pass `stream` in the request body the provider supports it.
        """

        if fake_stream is True:
            # remove 'stream' from data
            new_data = data.copy()
            new_data.pop("stream", None)
            return new_data
        if provider_config.supports_stream_param_in_request_body is True:
            data["stream"] = True
        return data

    def embedding(
        self,
        model: str,
        input: list,
        timeout: float,
        custom_llm_provider: str,
        logging_obj: LiteLLMLoggingObj,
        api_base: Optional[str],
        optional_params: dict,
        litellm_params: dict,
        model_response: EmbeddingResponse,
        api_key: Optional[str] = None,
        client: Optional[Union[HTTPHandler, AsyncHTTPHandler]] = None,
        aembedding: bool = False,
        headers: Optional[Dict[str, Any]] = None,
    ) -> EmbeddingResponse:
        provider_config = ProviderConfigManager.get_provider_embedding_config(
            model=model, provider=litellm.LlmProviders(custom_llm_provider)
        )
        if provider_config is None:
            raise ValueError(
                f"Provider {custom_llm_provider} does not support embedding"
            )
        # get config from model, custom llm provider
        headers = provider_config.validate_environment(
            api_key=api_key,
            headers=headers or {},
            model=model,
            messages=[],
            optional_params=optional_params,
            litellm_params=litellm_params,
        )

        api_base = provider_config.get_complete_url(
            api_base=api_base,
            api_key=api_key,
            model=model,
            optional_params=optional_params,
            litellm_params=litellm_params,
        )

        data = provider_config.transform_embedding_request(
            model=model,
            input=input,
            optional_params=optional_params,
            headers=headers,
        )

        ## LOGGING
        logging_obj.pre_call(
            input=input,
            api_key=api_key,
            additional_args={
                "complete_input_dict": data,
                "api_base": api_base,
                "headers": headers,
            },
        )

        if aembedding is True:
            return self.aembedding(  # type: ignore
                request_data=data,
                api_base=api_base,
                headers=headers,
                model=model,
                custom_llm_provider=custom_llm_provider,
                provider_config=provider_config,
                model_response=model_response,
                logging_obj=logging_obj,
                api_key=api_key,
                timeout=timeout,
                client=client,
                optional_params=optional_params,
                litellm_params=litellm_params,
            )

        if client is None or not isinstance(client, HTTPHandler):
            sync_httpx_client = _get_httpx_client()
        else:
            sync_httpx_client = client

        try:
            response = sync_httpx_client.post(
                url=api_base,
                headers=headers,
                data=json.dumps(data),
                timeout=timeout,
            )
        except Exception as e:
            raise self._handle_error(
                e=e,
                provider_config=provider_config,
            )

        return provider_config.transform_embedding_response(
            model=model,
            raw_response=response,
            model_response=model_response,
            logging_obj=logging_obj,
            api_key=api_key,
            request_data=data,
            optional_params=optional_params,
            litellm_params=litellm_params,
        )

    async def aembedding(
        self,
        request_data: dict,
        api_base: str,
        headers: dict,
        model: str,
        custom_llm_provider: str,
        provider_config: BaseEmbeddingConfig,
        model_response: EmbeddingResponse,
        logging_obj: LiteLLMLoggingObj,
        optional_params: dict,
        litellm_params: dict,
        api_key: Optional[str] = None,
        timeout: Optional[Union[float, httpx.Timeout]] = None,
        client: Optional[Union[HTTPHandler, AsyncHTTPHandler]] = None,
    ) -> EmbeddingResponse:
        if client is None or not isinstance(client, AsyncHTTPHandler):
            async_httpx_client = get_async_httpx_client(
                llm_provider=litellm.LlmProviders(custom_llm_provider)
            )
        else:
            async_httpx_client = client

        try:
            response = await async_httpx_client.post(
                url=api_base,
                headers=headers,
                json=request_data,
                timeout=timeout,
            )
        except Exception as e:
            raise self._handle_error(e=e, provider_config=provider_config)

        return provider_config.transform_embedding_response(
            model=model,
            raw_response=response,
            model_response=model_response,
            logging_obj=logging_obj,
            api_key=api_key,
            request_data=request_data,
            optional_params=optional_params,
            litellm_params=litellm_params,
        )

    def rerank(
        self,
        model: str,
        custom_llm_provider: str,
        logging_obj: LiteLLMLoggingObj,
        provider_config: BaseRerankConfig,
        optional_rerank_params: OptionalRerankParams,
        timeout: Optional[Union[float, httpx.Timeout]],
        model_response: RerankResponse,
        _is_async: bool = False,
        headers: Optional[Dict[str, Any]] = None,
        api_key: Optional[str] = None,
        api_base: Optional[str] = None,
        client: Optional[Union[HTTPHandler, AsyncHTTPHandler]] = None,
    ) -> RerankResponse:
        # get config from model, custom llm provider
        headers = provider_config.validate_environment(
            api_key=api_key,
            headers=headers or {},
            model=model,
        )

        api_base = provider_config.get_complete_url(
            api_base=api_base,
            model=model,
        )

        data = provider_config.transform_rerank_request(
            model=model,
            optional_rerank_params=optional_rerank_params,
            headers=headers,
        )

        ## LOGGING
        logging_obj.pre_call(
            input=optional_rerank_params.get("query", ""),
            api_key=api_key,
            additional_args={
                "complete_input_dict": data,
                "api_base": api_base,
                "headers": headers,
            },
        )

        if _is_async is True:
            return self.arerank(  # type: ignore
                model=model,
                request_data=data,
                custom_llm_provider=custom_llm_provider,
                provider_config=provider_config,
                logging_obj=logging_obj,
                model_response=model_response,
                api_base=api_base,
                headers=headers,
                api_key=api_key,
                timeout=timeout,
                client=client,
            )

        if client is None or not isinstance(client, HTTPHandler):
            sync_httpx_client = _get_httpx_client()
        else:
            sync_httpx_client = client

        try:
            response = sync_httpx_client.post(
                url=api_base,
                headers=headers,
                data=json.dumps(data),
                timeout=timeout,
            )
        except Exception as e:
            raise self._handle_error(
                e=e,
                provider_config=provider_config,
            )

        return provider_config.transform_rerank_response(
            model=model,
            raw_response=response,
            model_response=model_response,
            logging_obj=logging_obj,
            api_key=api_key,
            request_data=data,
        )

    async def arerank(
        self,
        model: str,
        request_data: dict,
        custom_llm_provider: str,
        provider_config: BaseRerankConfig,
        logging_obj: LiteLLMLoggingObj,
        model_response: RerankResponse,
        api_base: str,
        headers: dict,
        api_key: Optional[str] = None,
        timeout: Optional[Union[float, httpx.Timeout]] = None,
        client: Optional[Union[HTTPHandler, AsyncHTTPHandler]] = None,
    ) -> RerankResponse:
        if client is None or not isinstance(client, AsyncHTTPHandler):
            async_httpx_client = get_async_httpx_client(
                llm_provider=litellm.LlmProviders(custom_llm_provider)
            )
        else:
            async_httpx_client = client
        try:
            response = await async_httpx_client.post(
                url=api_base,
                headers=headers,
                data=json.dumps(request_data),
                timeout=timeout,
            )
        except Exception as e:
            raise self._handle_error(e=e, provider_config=provider_config)

        return provider_config.transform_rerank_response(
            model=model,
            raw_response=response,
            model_response=model_response,
            logging_obj=logging_obj,
            api_key=api_key,
            request_data=request_data,
        )

    def _prepare_audio_transcription_request(
        self,
        model: str,
        audio_file: FileTypes,
        optional_params: dict,
        litellm_params: dict,
        logging_obj: LiteLLMLoggingObj,
        api_key: Optional[str],
        api_base: Optional[str],
        headers: Optional[Dict[str, Any]],
        provider_config: BaseAudioTranscriptionConfig,
    ) -> Tuple[dict, str, Optional[bytes], Optional[dict]]:
        """
        Shared logic for preparing audio transcription requests.
        Returns: (headers, complete_url, binary_data, json_data)
        """
        headers = provider_config.validate_environment(
            api_key=api_key,
            headers=headers or {},
            model=model,
            messages=[],
            optional_params=optional_params,
            litellm_params=litellm_params,
        )

        complete_url = provider_config.get_complete_url(
            api_base=api_base,
            api_key=api_key,
            model=model,
            optional_params=optional_params,
            litellm_params=litellm_params,
        )

        # Handle the audio file based on type
        data = provider_config.transform_audio_transcription_request(
            model=model,
            audio_file=audio_file,
            optional_params=optional_params,
            litellm_params=litellm_params,
        )
        binary_data: Optional[bytes] = None
        json_data: Optional[dict] = None
        if isinstance(data, bytes):
            binary_data = data
        else:
            json_data = data

        ## LOGGING
        logging_obj.pre_call(
            input=optional_params.get("query", ""),
            api_key=api_key,
            additional_args={
                "complete_input_dict": {},
                "api_base": complete_url,
                "headers": headers,
            },
        )

        return headers, complete_url, binary_data, json_data

    def _transform_audio_transcription_response(
        self,
        provider_config: BaseAudioTranscriptionConfig,
        model: str,
        response: httpx.Response,
        model_response: TranscriptionResponse,
        logging_obj: LiteLLMLoggingObj,
        optional_params: dict,
        api_key: Optional[str],
    ) -> TranscriptionResponse:
        """Shared logic for transforming audio transcription responses."""
        if isinstance(provider_config, litellm.DeepgramAudioTranscriptionConfig):
            return provider_config.transform_audio_transcription_response(
                model=model,
                raw_response=response,
                model_response=model_response,
                logging_obj=logging_obj,
                request_data={},
                optional_params=optional_params,
                litellm_params={},
                api_key=api_key,
            )
        return model_response

    def audio_transcriptions(
        self,
        model: str,
        audio_file: FileTypes,
        optional_params: dict,
        litellm_params: dict,
        model_response: TranscriptionResponse,
        timeout: float,
        max_retries: int,
        logging_obj: LiteLLMLoggingObj,
        api_key: Optional[str],
        api_base: Optional[str],
        custom_llm_provider: str,
        client: Optional[Union[HTTPHandler, AsyncHTTPHandler]] = None,
        atranscription: bool = False,
        headers: Optional[Dict[str, Any]] = None,
        provider_config: Optional[BaseAudioTranscriptionConfig] = None,
    ) -> Union[TranscriptionResponse, Coroutine[Any, Any, TranscriptionResponse]]:
        if provider_config is None:
            raise ValueError(
                f"No provider config found for model: {model} and provider: {custom_llm_provider}"
            )

        if atranscription is True:
            return self.async_audio_transcriptions(  # type: ignore
                model=model,
                audio_file=audio_file,
                optional_params=optional_params,
                litellm_params=litellm_params,
                model_response=model_response,
                timeout=timeout,
                max_retries=max_retries,
                logging_obj=logging_obj,
                api_key=api_key,
                api_base=api_base,
                custom_llm_provider=custom_llm_provider,
                client=client,
                headers=headers,
                provider_config=provider_config,
            )

        # Prepare the request
        headers, complete_url, binary_data, json_data = (
            self._prepare_audio_transcription_request(
                model=model,
                audio_file=audio_file,
                optional_params=optional_params,
                litellm_params=litellm_params,
                logging_obj=logging_obj,
                api_key=api_key,
                api_base=api_base,
                headers=headers,
                provider_config=provider_config,
            )
        )

        if client is None or not isinstance(client, HTTPHandler):
            client = _get_httpx_client()

        try:
            # Make the POST request
            response = client.post(
                url=complete_url,
                headers=headers,
                content=binary_data,
                json=json_data,
                timeout=timeout,
            )
        except Exception as e:
            raise self._handle_error(e=e, provider_config=provider_config)

        return self._transform_audio_transcription_response(
            provider_config=provider_config,
            model=model,
            response=response,
            model_response=model_response,
            logging_obj=logging_obj,
            optional_params=optional_params,
            api_key=api_key,
        )

    async def async_audio_transcriptions(
        self,
        model: str,
        audio_file: FileTypes,
        optional_params: dict,
        litellm_params: dict,
        model_response: TranscriptionResponse,
        timeout: float,
        max_retries: int,
        logging_obj: LiteLLMLoggingObj,
        api_key: Optional[str],
        api_base: Optional[str],
        custom_llm_provider: str,
        client: Optional[Union[HTTPHandler, AsyncHTTPHandler]] = None,
        headers: Optional[Dict[str, Any]] = None,
        provider_config: Optional[BaseAudioTranscriptionConfig] = None,
    ) -> TranscriptionResponse:
        if provider_config is None:
            raise ValueError(
                f"No provider config found for model: {model} and provider: {custom_llm_provider}"
            )

        # Prepare the request
        headers, complete_url, binary_data, json_data = (
            self._prepare_audio_transcription_request(
                model=model,
                audio_file=audio_file,
                optional_params=optional_params,
                litellm_params=litellm_params,
                logging_obj=logging_obj,
                api_key=api_key,
                api_base=api_base,
                headers=headers,
                provider_config=provider_config,
            )
        )

        if client is None or not isinstance(client, AsyncHTTPHandler):
            async_httpx_client = get_async_httpx_client(
                llm_provider=litellm.LlmProviders(custom_llm_provider),
                params={"ssl_verify": litellm_params.get("ssl_verify", None)},
            )
        else:
            async_httpx_client = client

        try:
            # Make the async POST request
            response = await async_httpx_client.post(
                url=complete_url,
                headers=headers,
                content=binary_data,
                json=json_data,
                timeout=timeout,
            )
        except Exception as e:
            raise self._handle_error(e=e, provider_config=provider_config)

        return self._transform_audio_transcription_response(
            provider_config=provider_config,
            model=model,
            response=response,
            model_response=model_response,
            logging_obj=logging_obj,
            optional_params=optional_params,
            api_key=api_key,
        )

    async def async_anthropic_messages_handler(
        self,
        model: str,
        messages: List[Dict],
        anthropic_messages_provider_config: BaseAnthropicMessagesConfig,
        anthropic_messages_optional_request_params: Dict,
        custom_llm_provider: str,
        litellm_params: GenericLiteLLMParams,
        logging_obj: LiteLLMLoggingObj,
        client: Optional[AsyncHTTPHandler] = None,
        extra_headers: Optional[Dict[str, Any]] = None,
        api_key: Optional[str] = None,
        api_base: Optional[str] = None,
        stream: Optional[bool] = False,
        kwargs: Optional[Dict[str, Any]] = None,
    ) -> Union[AnthropicMessagesResponse, AsyncIterator]:
        if client is None or not isinstance(client, AsyncHTTPHandler):
            async_httpx_client = get_async_httpx_client(
                llm_provider=litellm.LlmProviders.ANTHROPIC
            )
        else:
            async_httpx_client = client

        # Prepare headers
        kwargs = kwargs or {}
        provider_specific_header = cast(
            Optional[litellm.types.utils.ProviderSpecificHeader],
            kwargs.get("provider_specific_header", None),
        )
        extra_headers = (
            provider_specific_header.get("extra_headers", {})
            if provider_specific_header
            else {}
        )
        (
            headers,
            api_base,
        ) = anthropic_messages_provider_config.validate_anthropic_messages_environment(
            headers=extra_headers or {},
            model=model,
            messages=messages,
            optional_params=anthropic_messages_optional_request_params,
            litellm_params=dict(litellm_params),
            api_key=api_key,
            api_base=api_base,
        )

        logging_obj.update_environment_variables(
            model=model,
            optional_params=dict(anthropic_messages_optional_request_params),
            litellm_params={
                "metadata": kwargs.get("metadata", {}),
                "preset_cache_key": None,
                "stream_response": {},
                **anthropic_messages_optional_request_params,
            },
            custom_llm_provider=custom_llm_provider,
        )
        # Prepare request body
        request_body = anthropic_messages_provider_config.transform_anthropic_messages_request(
            model=model,
            messages=messages,
            anthropic_messages_optional_request_params=anthropic_messages_optional_request_params,
            litellm_params=litellm_params,
            headers=headers,
        )
        logging_obj.stream = stream
        logging_obj.model_call_details.update(request_body)

        # Make the request
        request_url = anthropic_messages_provider_config.get_complete_url(
            api_base=api_base,
            api_key=api_key,
            model=model,
            optional_params=dict(
                litellm_params
            ),  # this uses the invoke config, which expects aws_* params in optional_params
            litellm_params=dict(litellm_params),
            stream=stream,
        )

        headers, signed_json_body = anthropic_messages_provider_config.sign_request(
            headers=headers,
            optional_params=dict(
                litellm_params
            ),  # dynamic aws_* params are passed under litellm_params
            request_data=request_body,
            api_base=request_url,
            stream=stream,
            fake_stream=False,
            model=model,
        )

        logging_obj.pre_call(
            input=[{"role": "user", "content": json.dumps(request_body)}],
            api_key="",
            additional_args={
                "complete_input_dict": request_body,
                "api_base": str(request_url),
                "headers": headers,
            },
        )

        response = await async_httpx_client.post(
            url=request_url,
            headers=headers,
            data=signed_json_body or json.dumps(request_body),
            stream=stream or False,
            logging_obj=logging_obj,
        )
        response.raise_for_status()

        # used for logging + cost tracking
        logging_obj.model_call_details["httpx_response"] = response

        if stream:
            completion_stream = anthropic_messages_provider_config.get_async_streaming_response_iterator(
                model=model,
                httpx_response=response,
                request_body=request_body,
                litellm_logging_obj=logging_obj,
            )
            return completion_stream
        else:
            return anthropic_messages_provider_config.transform_anthropic_messages_response(
                model=model,
                raw_response=response,
                logging_obj=logging_obj,
            )

    def anthropic_messages_handler(
        self,
        model: str,
        messages: List[Dict],
        anthropic_messages_provider_config: BaseAnthropicMessagesConfig,
        anthropic_messages_optional_request_params: Dict,
        custom_llm_provider: str,
        _is_async: bool,
        litellm_params: GenericLiteLLMParams,
        logging_obj: LiteLLMLoggingObj,
        client: Optional[Union[HTTPHandler, AsyncHTTPHandler]] = None,
        api_key: Optional[str] = None,
        api_base: Optional[str] = None,
        stream: Optional[bool] = False,
        kwargs: Optional[Dict[str, Any]] = None,
    ) -> Union[
        AnthropicMessagesResponse,
        Coroutine[Any, Any, Union[AnthropicMessagesResponse, AsyncIterator]],
    ]:
        """
        LLM HTTP Handler for Anthropic Messages
        """
        if _is_async:
            # Return the async coroutine if called with _is_async=True
            return self.async_anthropic_messages_handler(
                model=model,
                messages=messages,
                anthropic_messages_provider_config=anthropic_messages_provider_config,
                anthropic_messages_optional_request_params=anthropic_messages_optional_request_params,
                client=client if isinstance(client, AsyncHTTPHandler) else None,
                custom_llm_provider=custom_llm_provider,
                litellm_params=litellm_params,
                logging_obj=logging_obj,
                api_key=api_key,
                api_base=api_base,
                stream=stream,
                kwargs=kwargs,
            )
        raise ValueError("anthropic_messages_handler is not implemented for sync calls")

    def response_api_handler(
        self,
        model: str,
        input: Union[str, ResponseInputParam],
        responses_api_provider_config: BaseResponsesAPIConfig,
        response_api_optional_request_params: Dict,
        custom_llm_provider: str,
        litellm_params: GenericLiteLLMParams,
        logging_obj: LiteLLMLoggingObj,
        extra_headers: Optional[Dict[str, Any]] = None,
        extra_body: Optional[Dict[str, Any]] = None,
        timeout: Optional[Union[float, httpx.Timeout]] = None,
        client: Optional[Union[HTTPHandler, AsyncHTTPHandler]] = None,
        _is_async: bool = False,
        fake_stream: bool = False,
        litellm_metadata: Optional[Dict[str, Any]] = None,
    ) -> Union[
        ResponsesAPIResponse,
        BaseResponsesAPIStreamingIterator,
        Coroutine[
            Any, Any, Union[ResponsesAPIResponse, BaseResponsesAPIStreamingIterator]
        ],
    ]:
        """
        Handles responses API requests.
        When _is_async=True, returns a coroutine instead of making the call directly.
        """
        if _is_async:
            # Return the async coroutine if called with _is_async=True
            return self.async_response_api_handler(
                model=model,
                input=input,
                responses_api_provider_config=responses_api_provider_config,
                response_api_optional_request_params=response_api_optional_request_params,
                custom_llm_provider=custom_llm_provider,
                litellm_params=litellm_params,
                logging_obj=logging_obj,
                extra_headers=extra_headers,
                extra_body=extra_body,
                timeout=timeout,
                client=client if isinstance(client, AsyncHTTPHandler) else None,
                fake_stream=fake_stream,
                litellm_metadata=litellm_metadata,
            )

        if client is None or not isinstance(client, HTTPHandler):
            sync_httpx_client = _get_httpx_client(
                params={"ssl_verify": litellm_params.get("ssl_verify", None)}
            )
        else:
            sync_httpx_client = client

        headers = responses_api_provider_config.validate_environment(
            api_key=litellm_params.api_key,
            headers=response_api_optional_request_params.get("extra_headers", {}) or {},
            model=model,
        )

        if extra_headers:
            headers.update(extra_headers)

        # Check if streaming is requested
        stream = response_api_optional_request_params.get("stream", False)

        api_base = responses_api_provider_config.get_complete_url(
            api_base=litellm_params.api_base,
            litellm_params=dict(litellm_params),
        )

        data = responses_api_provider_config.transform_responses_api_request(
            model=model,
            input=input,
            response_api_optional_request_params=response_api_optional_request_params,
            litellm_params=litellm_params,
            headers=headers,
        )

        ## LOGGING
        logging_obj.pre_call(
            input=input,
            api_key="",
            additional_args={
                "complete_input_dict": data,
                "api_base": api_base,
                "headers": headers,
            },
        )

        try:
            if stream:
                # For streaming, use stream=True in the request
                if fake_stream is True:
                    stream, data = self._prepare_fake_stream_request(
                        stream=stream,
                        data=data,
                        fake_stream=fake_stream,
                    )
                response = sync_httpx_client.post(
                    url=api_base,
                    headers=headers,
                    json=data,
                    timeout=timeout
                    or response_api_optional_request_params.get("timeout"),
                    stream=stream,
                )
                if fake_stream is True:
                    return MockResponsesAPIStreamingIterator(
                        response=response,
                        model=model,
                        logging_obj=logging_obj,
                        responses_api_provider_config=responses_api_provider_config,
                        litellm_metadata=litellm_metadata,
                        custom_llm_provider=custom_llm_provider,
                    )

                return SyncResponsesAPIStreamingIterator(
                    response=response,
                    model=model,
                    logging_obj=logging_obj,
                    responses_api_provider_config=responses_api_provider_config,
                    litellm_metadata=litellm_metadata,
                    custom_llm_provider=custom_llm_provider,
                )
            else:
                # For non-streaming requests
                response = sync_httpx_client.post(
                    url=api_base,
                    headers=headers,
                    json=data,
                    timeout=timeout
                    or response_api_optional_request_params.get("timeout"),
                )
        except Exception as e:
            raise self._handle_error(
                e=e,
                provider_config=responses_api_provider_config,
            )

        return responses_api_provider_config.transform_response_api_response(
            model=model,
            raw_response=response,
            logging_obj=logging_obj,
        )

    async def async_response_api_handler(
        self,
        model: str,
        input: Union[str, ResponseInputParam],
        responses_api_provider_config: BaseResponsesAPIConfig,
        response_api_optional_request_params: Dict,
        custom_llm_provider: str,
        litellm_params: GenericLiteLLMParams,
        logging_obj: LiteLLMLoggingObj,
        extra_headers: Optional[Dict[str, Any]] = None,
        extra_body: Optional[Dict[str, Any]] = None,
        timeout: Optional[Union[float, httpx.Timeout]] = None,
        client: Optional[Union[HTTPHandler, AsyncHTTPHandler]] = None,
        fake_stream: bool = False,
        litellm_metadata: Optional[Dict[str, Any]] = None,
    ) -> Union[ResponsesAPIResponse, BaseResponsesAPIStreamingIterator]:
        """
        Async version of the responses API handler.
        Uses async HTTP client to make requests.
        """
        if client is None or not isinstance(client, AsyncHTTPHandler):
            async_httpx_client = get_async_httpx_client(
                llm_provider=litellm.LlmProviders(custom_llm_provider),
                params={"ssl_verify": litellm_params.get("ssl_verify", None)},
            )
        else:
            async_httpx_client = client

        headers = responses_api_provider_config.validate_environment(
            api_key=litellm_params.api_key,
            headers=response_api_optional_request_params.get("extra_headers", {}) or {},
            model=model,
        )

        if extra_headers:
            headers.update(extra_headers)

        # Check if streaming is requested
        stream = response_api_optional_request_params.get("stream", False)

        api_base = responses_api_provider_config.get_complete_url(
            api_base=litellm_params.api_base,
            litellm_params=dict(litellm_params),
        )

        data = responses_api_provider_config.transform_responses_api_request(
            model=model,
            input=input,
            response_api_optional_request_params=response_api_optional_request_params,
            litellm_params=litellm_params,
            headers=headers,
        )

        ## LOGGING
        logging_obj.pre_call(
            input=input,
            api_key="",
            additional_args={
                "complete_input_dict": data,
                "api_base": api_base,
                "headers": headers,
            },
        )

        try:
            if stream:
                # For streaming, we need to use stream=True in the request
                if fake_stream is True:
                    stream, data = self._prepare_fake_stream_request(
                        stream=stream,
                        data=data,
                        fake_stream=fake_stream,
                    )

                response = await async_httpx_client.post(
                    url=api_base,
                    headers=headers,
                    json=data,
                    timeout=timeout
                    or response_api_optional_request_params.get("timeout"),
                    stream=stream,
                )

                if fake_stream is True:
                    return MockResponsesAPIStreamingIterator(
                        response=response,
                        model=model,
                        logging_obj=logging_obj,
                        responses_api_provider_config=responses_api_provider_config,
                        litellm_metadata=litellm_metadata,
                        custom_llm_provider=custom_llm_provider,
                    )

                # Return the streaming iterator
                return ResponsesAPIStreamingIterator(
                    response=response,
                    model=model,
                    logging_obj=logging_obj,
                    responses_api_provider_config=responses_api_provider_config,
                    litellm_metadata=litellm_metadata,
                    custom_llm_provider=custom_llm_provider,
                )
            else:
                # For non-streaming, proceed as before
                response = await async_httpx_client.post(
                    url=api_base,
                    headers=headers,
                    json=data,
                    timeout=timeout
                    or response_api_optional_request_params.get("timeout"),
                )

        except Exception as e:
            raise self._handle_error(
                e=e,
                provider_config=responses_api_provider_config,
            )

        return responses_api_provider_config.transform_response_api_response(
            model=model,
            raw_response=response,
            logging_obj=logging_obj,
        )

    async def async_delete_response_api_handler(
        self,
        response_id: str,
        responses_api_provider_config: BaseResponsesAPIConfig,
        litellm_params: GenericLiteLLMParams,
        logging_obj: LiteLLMLoggingObj,
        custom_llm_provider: Optional[str],
        extra_headers: Optional[Dict[str, Any]] = None,
        extra_body: Optional[Dict[str, Any]] = None,
        timeout: Optional[Union[float, httpx.Timeout]] = None,
        client: Optional[Union[HTTPHandler, AsyncHTTPHandler]] = None,
        _is_async: bool = False,
    ) -> DeleteResponseResult:
        """
        Async version of the delete response API handler.
        Uses async HTTP client to make requests.
        """
        if client is None or not isinstance(client, AsyncHTTPHandler):
            async_httpx_client = get_async_httpx_client(
                llm_provider=litellm.LlmProviders(custom_llm_provider),
                params={"ssl_verify": litellm_params.get("ssl_verify", None)},
            )
        else:
            async_httpx_client = client

        headers = responses_api_provider_config.validate_environment(
            api_key=litellm_params.api_key,
            headers=extra_headers or {},
            model="None",
        )

        if extra_headers:
            headers.update(extra_headers)

        api_base = responses_api_provider_config.get_complete_url(
            api_base=litellm_params.api_base,
            litellm_params=dict(litellm_params),
        )

        url, data = responses_api_provider_config.transform_delete_response_api_request(
            response_id=response_id,
            api_base=api_base,
            litellm_params=litellm_params,
            headers=headers,
        )

        ## LOGGING
        logging_obj.pre_call(
            input=input,
            api_key="",
            additional_args={
                "complete_input_dict": data,
                "api_base": api_base,
                "headers": headers,
            },
        )

        try:
            response = await async_httpx_client.delete(
                url=url, headers=headers, json=data, timeout=timeout
            )

        except Exception as e:
            raise self._handle_error(
                e=e,
                provider_config=responses_api_provider_config,
            )

        return responses_api_provider_config.transform_delete_response_api_response(
            raw_response=response,
            logging_obj=logging_obj,
        )

    def delete_response_api_handler(
        self,
        response_id: str,
        responses_api_provider_config: BaseResponsesAPIConfig,
        litellm_params: GenericLiteLLMParams,
        logging_obj: LiteLLMLoggingObj,
        custom_llm_provider: Optional[str],
        extra_headers: Optional[Dict[str, Any]] = None,
        extra_body: Optional[Dict[str, Any]] = None,
        timeout: Optional[Union[float, httpx.Timeout]] = None,
        client: Optional[Union[HTTPHandler, AsyncHTTPHandler]] = None,
        _is_async: bool = False,
    ) -> Union[DeleteResponseResult, Coroutine[Any, Any, DeleteResponseResult]]:
        """
        Async version of the responses API handler.
        Uses async HTTP client to make requests.
        """
        if _is_async:
            return self.async_delete_response_api_handler(
                response_id=response_id,
                responses_api_provider_config=responses_api_provider_config,
                litellm_params=litellm_params,
                logging_obj=logging_obj,
                custom_llm_provider=custom_llm_provider,
                extra_headers=extra_headers,
                extra_body=extra_body,
                timeout=timeout,
                client=client,
            )
        if client is None or not isinstance(client, HTTPHandler):
            sync_httpx_client = _get_httpx_client(
                params={"ssl_verify": litellm_params.get("ssl_verify", None)}
            )
        else:
            sync_httpx_client = client

        headers = responses_api_provider_config.validate_environment(
            api_key=litellm_params.api_key,
            headers=extra_headers or {},
            model="None",
        )

        if extra_headers:
            headers.update(extra_headers)

        api_base = responses_api_provider_config.get_complete_url(
            api_base=litellm_params.api_base,
            litellm_params=dict(litellm_params),
        )

        url, data = responses_api_provider_config.transform_delete_response_api_request(
            response_id=response_id,
            api_base=api_base,
            litellm_params=litellm_params,
            headers=headers,
        )

        ## LOGGING
        logging_obj.pre_call(
            input=input,
            api_key="",
            additional_args={
                "complete_input_dict": data,
                "api_base": api_base,
                "headers": headers,
            },
        )

        try:
            response = sync_httpx_client.delete(
                url=url, headers=headers, json=data, timeout=timeout
            )

        except Exception as e:
            raise self._handle_error(
                e=e,
                provider_config=responses_api_provider_config,
            )

        return responses_api_provider_config.transform_delete_response_api_response(
            raw_response=response,
            logging_obj=logging_obj,
        )

    def get_responses(
        self,
        response_id: str,
        responses_api_provider_config: BaseResponsesAPIConfig,
        litellm_params: GenericLiteLLMParams,
        logging_obj: LiteLLMLoggingObj,
        custom_llm_provider: Optional[str] = None,
        extra_headers: Optional[Dict[str, Any]] = None,
        extra_body: Optional[Dict[str, Any]] = None,
        timeout: Optional[Union[float, httpx.Timeout]] = None,
        client: Optional[Union[HTTPHandler, AsyncHTTPHandler]] = None,
        _is_async: bool = False,
    ) -> Union[ResponsesAPIResponse, Coroutine[Any, Any, ResponsesAPIResponse]]:
        """
        Get a response by ID
        Uses GET /v1/responses/{response_id} endpoint in the responses API
        """
        if _is_async:
            return self.async_get_responses(
                response_id=response_id,
                responses_api_provider_config=responses_api_provider_config,
                litellm_params=litellm_params,
                logging_obj=logging_obj,
                custom_llm_provider=custom_llm_provider,
                extra_headers=extra_headers,
                extra_body=extra_body,
                timeout=timeout,
                client=client,
            )

        if client is None or not isinstance(client, HTTPHandler):
            sync_httpx_client = _get_httpx_client(
                params={"ssl_verify": litellm_params.get("ssl_verify", None)}
            )
        else:
            sync_httpx_client = client

        headers = responses_api_provider_config.validate_environment(
            api_key=litellm_params.api_key,
            headers=extra_headers or {},
            model="None",
        )

        if extra_headers:
            headers.update(extra_headers)

        api_base = responses_api_provider_config.get_complete_url(
            api_base=litellm_params.api_base,
            litellm_params=dict(litellm_params),
        )

        url, data = responses_api_provider_config.transform_get_response_api_request(
            response_id=response_id,
            api_base=api_base,
            litellm_params=litellm_params,
            headers=headers,
        )

        ## LOGGING
        logging_obj.pre_call(
            input="",
            api_key="",
            additional_args={
                "complete_input_dict": data,
                "api_base": api_base,
                "headers": headers,
            },
        )

        try:
            response = sync_httpx_client.get(url=url, headers=headers, params=data)
        except Exception as e:
            raise self._handle_error(
                e=e,
                provider_config=responses_api_provider_config,
            )

        return responses_api_provider_config.transform_get_response_api_response(
            raw_response=response,
            logging_obj=logging_obj,
        )

    async def async_get_responses(
        self,
        response_id: str,
        responses_api_provider_config: BaseResponsesAPIConfig,
        litellm_params: GenericLiteLLMParams,
        logging_obj: LiteLLMLoggingObj,
        custom_llm_provider: Optional[str] = None,
        extra_headers: Optional[Dict[str, Any]] = None,
        extra_body: Optional[Dict[str, Any]] = None,
        timeout: Optional[Union[float, httpx.Timeout]] = None,
        client: Optional[Union[HTTPHandler, AsyncHTTPHandler]] = None,
    ) -> ResponsesAPIResponse:
        """
        Async version of get_responses
        """
        if client is None or not isinstance(client, AsyncHTTPHandler):
            async_httpx_client = get_async_httpx_client(
                llm_provider=litellm.LlmProviders(custom_llm_provider),
                params={"ssl_verify": litellm_params.get("ssl_verify", None)},
            )
        else:
            async_httpx_client = client

        headers = responses_api_provider_config.validate_environment(
            api_key=litellm_params.api_key,
            headers=extra_headers or {},
            model="None",
        )

        if extra_headers:
            headers.update(extra_headers)

        api_base = responses_api_provider_config.get_complete_url(
            api_base=litellm_params.api_base,
            litellm_params=dict(litellm_params),
        )

        url, data = responses_api_provider_config.transform_get_response_api_request(
            response_id=response_id,
            api_base=api_base,
            litellm_params=litellm_params,
            headers=headers,
        )

        ## LOGGING
        logging_obj.pre_call(
            input="",
            api_key="",
            additional_args={
                "complete_input_dict": data,
                "api_base": api_base,
                "headers": headers,
            },
        )

        try:
            response = await async_httpx_client.get(
                url=url, headers=headers, params=data
            )

        except Exception as e:
            verbose_logger.exception(f"Error retrieving response: {e}")
            raise self._handle_error(
                e=e,
                provider_config=responses_api_provider_config,
            )

        return responses_api_provider_config.transform_get_response_api_response(
            raw_response=response,
            logging_obj=logging_obj,
        )

    #####################################################################
    ################ LIST RESPONSES INPUT ITEMS HANDLER ###########################
    #####################################################################
    def list_responses_input_items(
        self,
        response_id: str,
        responses_api_provider_config: BaseResponsesAPIConfig,
        litellm_params: GenericLiteLLMParams,
        logging_obj: LiteLLMLoggingObj,
        custom_llm_provider: Optional[str] = None,
        after: Optional[str] = None,
        before: Optional[str] = None,
        include: Optional[List[str]] = None,
        limit: int = 20,
        order: Literal["asc", "desc"] = "desc",
        extra_headers: Optional[Dict[str, Any]] = None,
        timeout: Optional[Union[float, httpx.Timeout]] = None,
        client: Optional[Union[HTTPHandler, AsyncHTTPHandler]] = None,
        _is_async: bool = False,
    ) -> Union[Dict, Coroutine[Any, Any, Dict]]:
        if _is_async:
            return self.async_list_responses_input_items(
                response_id=response_id,
                responses_api_provider_config=responses_api_provider_config,
                litellm_params=litellm_params,
                logging_obj=logging_obj,
                custom_llm_provider=custom_llm_provider,
                after=after,
                before=before,
                include=include,
                limit=limit,
                order=order,
                extra_headers=extra_headers,
                timeout=timeout,
                client=client,
            )

        if client is None or not isinstance(client, HTTPHandler):
            sync_httpx_client = _get_httpx_client(
                params={"ssl_verify": litellm_params.get("ssl_verify", None)}
            )
        else:
            sync_httpx_client = client

        headers = responses_api_provider_config.validate_environment(
            api_key=litellm_params.api_key,
            headers=extra_headers or {},
            model="None",
        )

        if extra_headers:
            headers.update(extra_headers)

        api_base = responses_api_provider_config.get_complete_url(
            api_base=litellm_params.api_base,
            litellm_params=dict(litellm_params),
        )

        url, params = responses_api_provider_config.transform_list_input_items_request(
            response_id=response_id,
            api_base=api_base,
            litellm_params=litellm_params,
            headers=headers,
            after=after,
            before=before,
            include=include,
            limit=limit,
            order=order,
        )

        logging_obj.pre_call(
            input="",
            api_key="",
            additional_args={
                "complete_input_dict": params,
                "api_base": api_base,
                "headers": headers,
            },
        )

        try:
            response = sync_httpx_client.get(url=url, headers=headers, params=params)
        except Exception as e:
            raise self._handle_error(e=e, provider_config=responses_api_provider_config)

        return responses_api_provider_config.transform_list_input_items_response(
            raw_response=response,
            logging_obj=logging_obj,
        )

    async def async_list_responses_input_items(
        self,
        response_id: str,
        responses_api_provider_config: BaseResponsesAPIConfig,
        litellm_params: GenericLiteLLMParams,
        logging_obj: LiteLLMLoggingObj,
        custom_llm_provider: Optional[str] = None,
        after: Optional[str] = None,
        before: Optional[str] = None,
        include: Optional[List[str]] = None,
        limit: int = 20,
        order: Literal["asc", "desc"] = "desc",
        extra_headers: Optional[Dict[str, Any]] = None,
        timeout: Optional[Union[float, httpx.Timeout]] = None,
        client: Optional[Union[HTTPHandler, AsyncHTTPHandler]] = None,
    ) -> Dict:
        if client is None or not isinstance(client, AsyncHTTPHandler):
            async_httpx_client = get_async_httpx_client(
                llm_provider=litellm.LlmProviders(custom_llm_provider),
                params={"ssl_verify": litellm_params.get("ssl_verify", None)},
            )
        else:
            async_httpx_client = client

        headers = responses_api_provider_config.validate_environment(
            api_key=litellm_params.api_key,
            headers=extra_headers or {},
            model="None",
        )

        if extra_headers:
            headers.update(extra_headers)

        api_base = responses_api_provider_config.get_complete_url(
            api_base=litellm_params.api_base,
            litellm_params=dict(litellm_params),
        )

        url, params = responses_api_provider_config.transform_list_input_items_request(
            response_id=response_id,
            api_base=api_base,
            litellm_params=litellm_params,
            headers=headers,
            after=after,
            before=before,
            include=include,
            limit=limit,
            order=order,
        )

        logging_obj.pre_call(
            input="",
            api_key="",
            additional_args={
                "complete_input_dict": params,
                "api_base": api_base,
                "headers": headers,
            },
        )

        try:
            response = await async_httpx_client.get(
                url=url, headers=headers, params=params
            )
        except Exception as e:
            raise self._handle_error(e=e, provider_config=responses_api_provider_config)

        return responses_api_provider_config.transform_list_input_items_response(
            raw_response=response,
            logging_obj=logging_obj,
        )

    def create_file(
        self,
        create_file_data: CreateFileRequest,
        litellm_params: dict,
        provider_config: BaseFilesConfig,
        headers: dict,
        api_base: Optional[str],
        api_key: Optional[str],
        logging_obj: LiteLLMLoggingObj,
        _is_async: bool = False,
        client: Optional[Union[HTTPHandler, AsyncHTTPHandler]] = None,
        timeout: Optional[Union[float, httpx.Timeout]] = None,
    ) -> Union[OpenAIFileObject, Coroutine[Any, Any, OpenAIFileObject]]:
        """
        Creates a file using Gemini's two-step upload process
        """
        # get config from model, custom llm provider
        headers = provider_config.validate_environment(
            api_key=api_key,
            headers=headers,
            model="",
            messages=[],
            optional_params={},
            litellm_params=litellm_params,
        )

        api_base = provider_config.get_complete_file_url(
            api_base=api_base,
            api_key=api_key,
            model="",
            optional_params={},
            litellm_params=litellm_params,
            data=create_file_data,
        )
        if api_base is None:
            raise ValueError("api_base is required for create_file")

        # Get the transformed request data for both steps
        transformed_request = provider_config.transform_create_file_request(
            model="",
            create_file_data=create_file_data,
            litellm_params=litellm_params,
            optional_params={},
        )

        if _is_async:
            return self.async_create_file(
                transformed_request=transformed_request,
                litellm_params=litellm_params,
                provider_config=provider_config,
                headers=headers,
                api_base=api_base,
                logging_obj=logging_obj,
                client=client,
                timeout=timeout,
            )

        if client is None or not isinstance(client, HTTPHandler):
            sync_httpx_client = _get_httpx_client()
        else:
            sync_httpx_client = client

        if isinstance(transformed_request, str) or isinstance(
            transformed_request, bytes
        ):
            upload_response = sync_httpx_client.post(
                url=api_base,
                headers=headers,
                data=transformed_request,
                timeout=timeout,
            )
        else:
            try:
                # Step 1: Initial request to get upload URL
                initial_response = sync_httpx_client.post(
                    url=api_base,
                    headers={
                        **headers,
                        **transformed_request["initial_request"]["headers"],
                    },
                    data=json.dumps(transformed_request["initial_request"]["data"]),
                    timeout=timeout,
                )

                # Extract upload URL from response headers
                upload_url = initial_response.headers.get("X-Goog-Upload-URL")

                if not upload_url:
                    raise ValueError("Failed to get upload URL from initial request")

                # Step 2: Upload the actual file
                upload_response = sync_httpx_client.post(
                    url=upload_url,
                    headers=transformed_request["upload_request"]["headers"],
                    data=transformed_request["upload_request"]["data"],
                    timeout=timeout,
                )
            except Exception as e:
                raise self._handle_error(
                    e=e,
                    provider_config=provider_config,
                )

        return provider_config.transform_create_file_response(
            model=None,
            raw_response=upload_response,
            logging_obj=logging_obj,
            litellm_params=litellm_params,
        )

    async def async_create_file(
        self,
        transformed_request: Union[bytes, str, dict],
        litellm_params: dict,
        provider_config: BaseFilesConfig,
        headers: dict,
        api_base: str,
        logging_obj: LiteLLMLoggingObj,
        client: Optional[Union[HTTPHandler, AsyncHTTPHandler]] = None,
        timeout: Optional[Union[float, httpx.Timeout]] = None,
    ):
        """
        Creates a file using Gemini's two-step upload process
        """
        if client is None or not isinstance(client, AsyncHTTPHandler):
            async_httpx_client = get_async_httpx_client(
                llm_provider=provider_config.custom_llm_provider
            )
        else:
            async_httpx_client = client

        if isinstance(transformed_request, str) or isinstance(
            transformed_request, bytes
        ):
            upload_response = await async_httpx_client.post(
                url=api_base,
                headers=headers,
                data=transformed_request,
                timeout=timeout,
            )
        else:
            try:
                # Step 1: Initial request to get upload URL
                initial_response = await async_httpx_client.post(
                    url=api_base,
                    headers={
                        **headers,
                        **transformed_request["initial_request"]["headers"],
                    },
                    data=json.dumps(transformed_request["initial_request"]["data"]),
                    timeout=timeout,
                )

                # Extract upload URL from response headers
                upload_url = initial_response.headers.get("X-Goog-Upload-URL")

                if not upload_url:
                    raise ValueError("Failed to get upload URL from initial request")

                # Step 2: Upload the actual file
                upload_response = await async_httpx_client.post(
                    url=upload_url,
                    headers=transformed_request["upload_request"]["headers"],
                    data=transformed_request["upload_request"]["data"],
                    timeout=timeout,
                )
            except Exception as e:
                verbose_logger.exception(f"Error creating file: {e}")
                raise self._handle_error(
                    e=e,
                    provider_config=provider_config,
                )

        return provider_config.transform_create_file_response(
            model=None,
            raw_response=upload_response,
            logging_obj=logging_obj,
            litellm_params=litellm_params,
        )

    def list_files(self):
        """
        Lists all files
        """
        pass

    def delete_file(self):
        """
        Deletes a file
        """
        pass

    def retrieve_file(self):
        """
        Returns the metadata of the file
        """
        pass

    def retrieve_file_content(self):
        """
        Returns the content of the file
        """
        pass

    def _prepare_fake_stream_request(
        self,
        stream: bool,
        data: dict,
        fake_stream: bool,
    ) -> Tuple[bool, dict]:
        """
        Handles preparing a request when `fake_stream` is True.
        """
        if fake_stream is True:
            stream = False
            data.pop("stream", None)
            return stream, data
        return stream, data

    def _handle_error(
        self,
        e: Exception,
        provider_config: Union[
            BaseConfig, BaseRerankConfig, BaseResponsesAPIConfig, BaseImageEditConfig
        ],
    ):
        status_code = getattr(e, "status_code", 500)
        error_headers = getattr(e, "headers", None)
        if isinstance(e, httpx.HTTPStatusError):
            error_text = e.response.text
            status_code = e.response.status_code
        else:
            error_text = getattr(e, "text", str(e))
        error_response = getattr(e, "response", None)
        if error_headers is None and error_response:
            error_headers = getattr(error_response, "headers", None)
        if error_response and hasattr(error_response, "text"):
            error_text = getattr(error_response, "text", error_text)
        if error_headers:
            error_headers = dict(error_headers)
        else:
            error_headers = {}

        raise provider_config.get_error_class(
            error_message=error_text,
            status_code=status_code,
            headers=error_headers,
        )

    async def async_realtime(
        self,
        model: str,
        websocket: Any,
        logging_obj: LiteLLMLoggingObj,
        provider_config: BaseRealtimeConfig,
        headers: dict,
        api_base: Optional[str] = None,
        api_key: Optional[str] = None,
        client: Optional[Any] = None,
        timeout: Optional[float] = None,
    ):
        import websockets
        from websockets.asyncio.client import ClientConnection

        url = provider_config.get_complete_url(api_base, model, api_key)
        headers = provider_config.validate_environment(
            headers=headers,
            model=model,
            api_key=api_key,
        )

        try:
            async with websockets.connect(  # type: ignore
                url, extra_headers=headers
            ) as backend_ws:
                realtime_streaming = RealTimeStreaming(
                    websocket,
                    cast(ClientConnection, backend_ws),
                    logging_obj,
                    provider_config,
                    model,
                )
                await realtime_streaming.bidirectional_forward()

        except websockets.exceptions.InvalidStatusCode as e:  # type: ignore
            verbose_logger.exception(f"Error connecting to backend: {e}")
            await websocket.close(code=e.status_code, reason=str(e))
        except Exception as e:
            verbose_logger.exception(f"Error connecting to backend: {e}")
            try:
                await websocket.close(
                    code=1011, reason=f"Internal server error: {str(e)}"
                )
            except RuntimeError as close_error:
                if "already completed" in str(close_error) or "websocket.close" in str(
                    close_error
                ):
                    # The WebSocket is already closed or the response is completed, so we can ignore this error
                    pass
                else:
                    # If it's a different RuntimeError, we might want to log it or handle it differently
                    raise Exception(
                        f"Unexpected error while closing WebSocket: {close_error}"
                    )

    def image_edit_handler(
        self,
        model: str,
        image: Any,
        prompt: str,
        image_edit_provider_config: BaseImageEditConfig,
        image_edit_optional_request_params: Dict,
        custom_llm_provider: str,
        litellm_params: GenericLiteLLMParams,
        logging_obj: LiteLLMLoggingObj,
        timeout: Union[float, httpx.Timeout],
        extra_headers: Optional[Dict[str, Any]] = None,
        extra_body: Optional[Dict[str, Any]] = None,
        client: Optional[Union[HTTPHandler, AsyncHTTPHandler]] = None,
        _is_async: bool = False,
        fake_stream: bool = False,
        litellm_metadata: Optional[Dict[str, Any]] = None,
    ) -> Union[
        ImageResponse,
        Coroutine[Any, Any, ImageResponse],
    ]:
        """

        Handles image edit requests.
        When _is_async=True, returns a coroutine instead of making the call directly.
        """
        if _is_async:
            # Return the async coroutine if called with _is_async=True
            return self.async_image_edit_handler(
                model=model,
                image=image,
                prompt=prompt,
                image_edit_provider_config=image_edit_provider_config,
                image_edit_optional_request_params=image_edit_optional_request_params,
                custom_llm_provider=custom_llm_provider,
                litellm_params=litellm_params,
                logging_obj=logging_obj,
                extra_headers=extra_headers,
                extra_body=extra_body,
                timeout=timeout,
                client=client if isinstance(client, AsyncHTTPHandler) else None,
                fake_stream=fake_stream,
                litellm_metadata=litellm_metadata,
            )

        if client is None or not isinstance(client, HTTPHandler):
            sync_httpx_client = _get_httpx_client(
                params={"ssl_verify": litellm_params.get("ssl_verify", None)}
            )
        else:
            sync_httpx_client = client

        headers = image_edit_provider_config.validate_environment(
            api_key=litellm_params.api_key,
            headers=image_edit_optional_request_params.get("extra_headers", {}) or {},
            model=model,
        )

        if extra_headers:
            headers.update(extra_headers)

        api_base = image_edit_provider_config.get_complete_url(
            model=model,
            api_base=litellm_params.api_base,
            litellm_params=dict(litellm_params),
        )

        data, files = image_edit_provider_config.transform_image_edit_request(
            model=model,
            image=image,
            prompt=prompt,
            image_edit_optional_request_params=image_edit_optional_request_params,
            litellm_params=litellm_params,
            headers=headers,
        )

        ## LOGGING
        logging_obj.pre_call(
            input=prompt,
            api_key="",
            additional_args={
                "complete_input_dict": data,
                "api_base": api_base,
                "headers": headers,
            },
        )

        try:
            response = sync_httpx_client.post(
                url=api_base,
                headers=headers,
                data=data,
                files=files,
                timeout=timeout,
            )

        except Exception as e:
            raise self._handle_error(
                e=e,
                provider_config=image_edit_provider_config,
            )

        return image_edit_provider_config.transform_image_edit_response(
            model=model,
            raw_response=response,
            logging_obj=logging_obj,
        )

    async def async_image_edit_handler(
        self,
        model: str,
        image: FileTypes,
        prompt: str,
        image_edit_provider_config: BaseImageEditConfig,
        image_edit_optional_request_params: Dict,
        custom_llm_provider: str,
        litellm_params: GenericLiteLLMParams,
        logging_obj: LiteLLMLoggingObj,
        timeout: Union[float, httpx.Timeout],
        extra_headers: Optional[Dict[str, Any]] = None,
        extra_body: Optional[Dict[str, Any]] = None,
        client: Optional[Union[HTTPHandler, AsyncHTTPHandler]] = None,
        fake_stream: bool = False,
        litellm_metadata: Optional[Dict[str, Any]] = None,
    ) -> ImageResponse:
        """
        Async version of the image edit handler.
        Uses async HTTP client to make requests.
        """
        if client is None or not isinstance(client, AsyncHTTPHandler):
            async_httpx_client = get_async_httpx_client(
                llm_provider=litellm.LlmProviders(custom_llm_provider),
                params={"ssl_verify": litellm_params.get("ssl_verify", None)},
            )
        else:
            async_httpx_client = client

        headers = image_edit_provider_config.validate_environment(
            api_key=litellm_params.api_key,
            headers=image_edit_optional_request_params.get("extra_headers", {}) or {},
            model=model,
        )

        if extra_headers:
            headers.update(extra_headers)

        api_base = image_edit_provider_config.get_complete_url(
            model=model,
            api_base=litellm_params.api_base,
            litellm_params=dict(litellm_params),
        )

        data, files = image_edit_provider_config.transform_image_edit_request(
            model=model,
            image=image,
            prompt=prompt,
            image_edit_optional_request_params=image_edit_optional_request_params,
            litellm_params=litellm_params,
            headers=headers,
        )

        ## LOGGING
        logging_obj.pre_call(
            input=prompt,
            api_key="",
            additional_args={
                "complete_input_dict": data,
                "api_base": api_base,
                "headers": headers,
            },
        )

        try:
            response = await async_httpx_client.post(
                url=api_base,
                headers=headers,
                data=data,
                files=files,
                timeout=timeout,
            )

        except Exception as e:
            raise self._handle_error(
                e=e,
                provider_config=image_edit_provider_config,
            )

        return image_edit_provider_config.transform_image_edit_response(
            model=model,
            raw_response=response,
            logging_obj=logging_obj,
        )

# === NexusCore/openenv\Lib\site-packages\google\generativeai\notebook\lib\llmfn_input_utils.py ===
# -*- coding: utf-8 -*-
# Copyright 2023 Google LLC
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
"""Utilities for handling input variables."""
from __future__ import annotations

from typing import Any, Mapping, Sequence, Union

from google.generativeai.notebook.lib import llmfn_inputs_source


_NormalizedInputsList = llmfn_inputs_source.NormalizedInputsList

_ColumnOrderValuesList = Mapping[str, Sequence[str]]

LLMFunctionInputs = Union[_ColumnOrderValuesList, llmfn_inputs_source.LLMFnInputsSource]


def _is_column_order_values_list(inputs: Any) -> bool:
    """See if inputs is of the form: {"key1": ["val1", "val2", ...]}.

    This is similar to the format produced by:
      pandas.DataFrame.to_dict(orient="list")

    Args:
      inputs: The inputs passed into an LLMFunction.

    Returns:
      Whether `inputs` is a column-ordered list of values.
    """
    if not isinstance(inputs, Mapping):
        return False
    for x in inputs.values():
        if not isinstance(x, Sequence):
            return False
        # Strings and bytes are also considered Sequences but we disallow them
        # here because the values contained in their Sequences are single
        # characters rather than words.
        if isinstance(x, str) or isinstance(x, bytes):
            return False
    return True


# TODO(b/273688393): Perform stricter validation on `inputs`.
def _normalize_column_order_values_list(
    inputs: _ColumnOrderValuesList,
) -> _NormalizedInputsList:
    """Transforms prompt inputs into a list of dictionaries."""
    return_list: list[dict[str, str]] = []
    keys = list(inputs.keys())
    if keys:
        first_key = keys[0]
        for row_num in range(len(inputs[first_key])):
            row_dict = {}
            return_list.append(row_dict)
            for key in keys:
                row_dict[key] = inputs[key][row_num]
    return return_list


def to_normalized_inputs(inputs: LLMFunctionInputs) -> _NormalizedInputsList:
    """Handles the different types of `inputs` and returns a normalized form."""
    normalized_inputs: list[Mapping[str, str]] = []
    if isinstance(inputs, llmfn_inputs_source.LLMFnInputsSource):
        normalized_inputs.extend(inputs.to_normalized_inputs())
    elif _is_column_order_values_list(inputs):
        normalized_inputs.extend(_normalize_column_order_values_list(inputs))
    else:
        raise ValueError("Unsupported input type {!r}".format(inputs))
    return normalized_inputs

# === NexusCore/openenv\Lib\site-packages\openai\resources\responses\responses.py ===
# File generated from our OpenAPI spec by Stainless. See CONTRIBUTING.md for details.

from __future__ import annotations

from typing import Any, List, Type, Union, Iterable, Optional, cast
from functools import partial
from typing_extensions import Literal, overload

import httpx

from ... import _legacy_response
from ..._types import NOT_GIVEN, Body, Query, Headers, NoneType, NotGiven
from ..._utils import is_given, maybe_transform, async_maybe_transform
from ..._compat import cached_property
from ..._resource import SyncAPIResource, AsyncAPIResource
from ..._response import to_streamed_response_wrapper, async_to_streamed_response_wrapper
from .input_items import (
    InputItems,
    AsyncInputItems,
    InputItemsWithRawResponse,
    AsyncInputItemsWithRawResponse,
    InputItemsWithStreamingResponse,
    AsyncInputItemsWithStreamingResponse,
)
from ..._streaming import Stream, AsyncStream
from ...lib._tools import PydanticFunctionTool, ResponsesPydanticFunctionTool
from ..._base_client import make_request_options
from ...types.responses import response_create_params, response_retrieve_params
from ...lib._parsing._responses import (
    TextFormatT,
    parse_response,
    type_to_text_format_param as _type_to_text_format_param,
)
from ...types.shared.chat_model import ChatModel
from ...types.responses.response import Response
from ...types.responses.tool_param import ToolParam, ParseableToolParam
from ...types.shared_params.metadata import Metadata
from ...types.shared_params.reasoning import Reasoning
from ...types.responses.parsed_response import ParsedResponse
from ...lib.streaming.responses._responses import ResponseStreamManager, AsyncResponseStreamManager
from ...types.responses.response_includable import ResponseIncludable
from ...types.shared_params.responses_model import ResponsesModel
from ...types.responses.response_input_param import ResponseInputParam
from ...types.responses.response_prompt_param import ResponsePromptParam
from ...types.responses.response_stream_event import ResponseStreamEvent
from ...types.responses.response_text_config_param import ResponseTextConfigParam

__all__ = ["Responses", "AsyncResponses"]


class Responses(SyncAPIResource):
    @cached_property
    def input_items(self) -> InputItems:
        return InputItems(self._client)

    @cached_property
    def with_raw_response(self) -> ResponsesWithRawResponse:
        """
        This property can be used as a prefix for any HTTP method call to return
        the raw response object instead of the parsed content.

        For more information, see https://www.github.com/openai/openai-python#accessing-raw-response-data-eg-headers
        """
        return ResponsesWithRawResponse(self)

    @cached_property
    def with_streaming_response(self) -> ResponsesWithStreamingResponse:
        """
        An alternative to `.with_raw_response` that doesn't eagerly read the response body.

        For more information, see https://www.github.com/openai/openai-python#with_streaming_response
        """
        return ResponsesWithStreamingResponse(self)

    @overload
    def create(
        self,
        *,
        background: Optional[bool] | NotGiven = NOT_GIVEN,
        include: Optional[List[ResponseIncludable]] | NotGiven = NOT_GIVEN,
        input: Union[str, ResponseInputParam] | NotGiven = NOT_GIVEN,
        instructions: Optional[str] | NotGiven = NOT_GIVEN,
        max_output_tokens: Optional[int] | NotGiven = NOT_GIVEN,
        metadata: Optional[Metadata] | NotGiven = NOT_GIVEN,
        model: ResponsesModel | NotGiven = NOT_GIVEN,
        parallel_tool_calls: Optional[bool] | NotGiven = NOT_GIVEN,
        previous_response_id: Optional[str] | NotGiven = NOT_GIVEN,
        prompt: Optional[ResponsePromptParam] | NotGiven = NOT_GIVEN,
        reasoning: Optional[Reasoning] | NotGiven = NOT_GIVEN,
        service_tier: Optional[Literal["auto", "default", "flex", "scale"]] | NotGiven = NOT_GIVEN,
        store: Optional[bool] | NotGiven = NOT_GIVEN,
        stream: Optional[Literal[False]] | NotGiven = NOT_GIVEN,
        temperature: Optional[float] | NotGiven = NOT_GIVEN,
        text: ResponseTextConfigParam | NotGiven = NOT_GIVEN,
        tool_choice: response_create_params.ToolChoice | NotGiven = NOT_GIVEN,
        tools: Iterable[ToolParam] | NotGiven = NOT_GIVEN,
        top_p: Optional[float] | NotGiven = NOT_GIVEN,
        truncation: Optional[Literal["auto", "disabled"]] | NotGiven = NOT_GIVEN,
        user: str | NotGiven = NOT_GIVEN,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> Response:
        """Creates a model response.

        Provide
        [text](https://platform.openai.com/docs/guides/text) or
        [image](https://platform.openai.com/docs/guides/images) inputs to generate
        [text](https://platform.openai.com/docs/guides/text) or
        [JSON](https://platform.openai.com/docs/guides/structured-outputs) outputs. Have
        the model call your own
        [custom code](https://platform.openai.com/docs/guides/function-calling) or use
        built-in [tools](https://platform.openai.com/docs/guides/tools) like
        [web search](https://platform.openai.com/docs/guides/tools-web-search) or
        [file search](https://platform.openai.com/docs/guides/tools-file-search) to use
        your own data as input for the model's response.

        Args:
          background: Whether to run the model response in the background.
              [Learn more](https://platform.openai.com/docs/guides/background).

          include: Specify additional output data to include in the model response. Currently
              supported values are:

              - `file_search_call.results`: Include the search results of the file search tool
                call.
              - `message.input_image.image_url`: Include image urls from the input message.
              - `computer_call_output.output.image_url`: Include image urls from the computer
                call output.
              - `reasoning.encrypted_content`: Includes an encrypted version of reasoning
                tokens in reasoning item outputs. This enables reasoning items to be used in
                multi-turn conversations when using the Responses API statelessly (like when
                the `store` parameter is set to `false`, or when an organization is enrolled
                in the zero data retention program).
              - `code_interpreter_call.outputs`: Includes the outputs of python code execution
                in code interpreter tool call items.

          input: Text, image, or file inputs to the model, used to generate a response.

              Learn more:

              - [Text inputs and outputs](https://platform.openai.com/docs/guides/text)
              - [Image inputs](https://platform.openai.com/docs/guides/images)
              - [File inputs](https://platform.openai.com/docs/guides/pdf-files)
              - [Conversation state](https://platform.openai.com/docs/guides/conversation-state)
              - [Function calling](https://platform.openai.com/docs/guides/function-calling)

          instructions: A system (or developer) message inserted into the model's context.

              When using along with `previous_response_id`, the instructions from a previous
              response will not be carried over to the next response. This makes it simple to
              swap out system (or developer) messages in new responses.

          max_output_tokens: An upper bound for the number of tokens that can be generated for a response,
              including visible output tokens and
              [reasoning tokens](https://platform.openai.com/docs/guides/reasoning).

          metadata: Set of 16 key-value pairs that can be attached to an object. This can be useful
              for storing additional information about the object in a structured format, and
              querying for objects via API or the dashboard.

              Keys are strings with a maximum length of 64 characters. Values are strings with
              a maximum length of 512 characters.

          model: Model ID used to generate the response, like `gpt-4o` or `o3`. OpenAI offers a
              wide range of models with different capabilities, performance characteristics,
              and price points. Refer to the
              [model guide](https://platform.openai.com/docs/models) to browse and compare
              available models.

          parallel_tool_calls: Whether to allow the model to run tool calls in parallel.

          previous_response_id: The unique ID of the previous response to the model. Use this to create
              multi-turn conversations. Learn more about
              [conversation state](https://platform.openai.com/docs/guides/conversation-state).

          prompt: Reference to a prompt template and its variables.
              [Learn more](https://platform.openai.com/docs/guides/text?api-mode=responses#reusable-prompts).

          reasoning: **o-series models only**

              Configuration options for
              [reasoning models](https://platform.openai.com/docs/guides/reasoning).

          service_tier: Specifies the latency tier to use for processing the request. This parameter is
              relevant for customers subscribed to the scale tier service:

              - If set to 'auto', and the Project is Scale tier enabled, the system will
                utilize scale tier credits until they are exhausted.
              - If set to 'auto', and the Project is not Scale tier enabled, the request will
                be processed using the default service tier with a lower uptime SLA and no
                latency guarantee.
              - If set to 'default', the request will be processed using the default service
                tier with a lower uptime SLA and no latency guarantee.
              - If set to 'flex', the request will be processed with the Flex Processing
                service tier.
                [Learn more](https://platform.openai.com/docs/guides/flex-processing).
              - When not set, the default behavior is 'auto'.

              When this parameter is set, the response body will include the `service_tier`
              utilized.

          store: Whether to store the generated model response for later retrieval via API.

          stream: If set to true, the model response data will be streamed to the client as it is
              generated using
              [server-sent events](https://developer.mozilla.org/en-US/docs/Web/API/Server-sent_events/Using_server-sent_events#Event_stream_format).
              See the
              [Streaming section below](https://platform.openai.com/docs/api-reference/responses-streaming)
              for more information.

          temperature: What sampling temperature to use, between 0 and 2. Higher values like 0.8 will
              make the output more random, while lower values like 0.2 will make it more
              focused and deterministic. We generally recommend altering this or `top_p` but
              not both.

          text: Configuration options for a text response from the model. Can be plain text or
              structured JSON data. Learn more:

              - [Text inputs and outputs](https://platform.openai.com/docs/guides/text)
              - [Structured Outputs](https://platform.openai.com/docs/guides/structured-outputs)

          tool_choice: How the model should select which tool (or tools) to use when generating a
              response. See the `tools` parameter to see how to specify which tools the model
              can call.

          tools: An array of tools the model may call while generating a response. You can
              specify which tool to use by setting the `tool_choice` parameter.

              The two categories of tools you can provide the model are:

              - **Built-in tools**: Tools that are provided by OpenAI that extend the model's
                capabilities, like
                [web search](https://platform.openai.com/docs/guides/tools-web-search) or
                [file search](https://platform.openai.com/docs/guides/tools-file-search).
                Learn more about
                [built-in tools](https://platform.openai.com/docs/guides/tools).
              - **Function calls (custom tools)**: Functions that are defined by you, enabling
                the model to call your own code. Learn more about
                [function calling](https://platform.openai.com/docs/guides/function-calling).

          top_p: An alternative to sampling with temperature, called nucleus sampling, where the
              model considers the results of the tokens with top_p probability mass. So 0.1
              means only the tokens comprising the top 10% probability mass are considered.

              We generally recommend altering this or `temperature` but not both.

          truncation: The truncation strategy to use for the model response.

              - `auto`: If the context of this response and previous ones exceeds the model's
                context window size, the model will truncate the response to fit the context
                window by dropping input items in the middle of the conversation.
              - `disabled` (default): If a model response will exceed the context window size
                for a model, the request will fail with a 400 error.

          user: A stable identifier for your end-users. Used to boost cache hit rates by better
              bucketing similar requests and to help OpenAI detect and prevent abuse.
              [Learn more](https://platform.openai.com/docs/guides/safety-best-practices#end-user-ids).

          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request, in seconds
        """
        ...

    @overload
    def create(
        self,
        *,
        stream: Literal[True],
        background: Optional[bool] | NotGiven = NOT_GIVEN,
        include: Optional[List[ResponseIncludable]] | NotGiven = NOT_GIVEN,
        input: Union[str, ResponseInputParam] | NotGiven = NOT_GIVEN,
        instructions: Optional[str] | NotGiven = NOT_GIVEN,
        max_output_tokens: Optional[int] | NotGiven = NOT_GIVEN,
        metadata: Optional[Metadata] | NotGiven = NOT_GIVEN,
        model: ResponsesModel | NotGiven = NOT_GIVEN,
        parallel_tool_calls: Optional[bool] | NotGiven = NOT_GIVEN,
        previous_response_id: Optional[str] | NotGiven = NOT_GIVEN,
        prompt: Optional[ResponsePromptParam] | NotGiven = NOT_GIVEN,
        reasoning: Optional[Reasoning] | NotGiven = NOT_GIVEN,
        service_tier: Optional[Literal["auto", "default", "flex", "scale"]] | NotGiven = NOT_GIVEN,
        store: Optional[bool] | NotGiven = NOT_GIVEN,
        temperature: Optional[float] | NotGiven = NOT_GIVEN,
        text: ResponseTextConfigParam | NotGiven = NOT_GIVEN,
        tool_choice: response_create_params.ToolChoice | NotGiven = NOT_GIVEN,
        tools: Iterable[ToolParam] | NotGiven = NOT_GIVEN,
        top_p: Optional[float] | NotGiven = NOT_GIVEN,
        truncation: Optional[Literal["auto", "disabled"]] | NotGiven = NOT_GIVEN,
        user: str | NotGiven = NOT_GIVEN,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> Stream[ResponseStreamEvent]:
        """Creates a model response.

        Provide
        [text](https://platform.openai.com/docs/guides/text) or
        [image](https://platform.openai.com/docs/guides/images) inputs to generate
        [text](https://platform.openai.com/docs/guides/text) or
        [JSON](https://platform.openai.com/docs/guides/structured-outputs) outputs. Have
        the model call your own
        [custom code](https://platform.openai.com/docs/guides/function-calling) or use
        built-in [tools](https://platform.openai.com/docs/guides/tools) like
        [web search](https://platform.openai.com/docs/guides/tools-web-search) or
        [file search](https://platform.openai.com/docs/guides/tools-file-search) to use
        your own data as input for the model's response.

        Args:
          stream: If set to true, the model response data will be streamed to the client as it is
              generated using
              [server-sent events](https://developer.mozilla.org/en-US/docs/Web/API/Server-sent_events/Using_server-sent_events#Event_stream_format).
              See the
              [Streaming section below](https://platform.openai.com/docs/api-reference/responses-streaming)
              for more information.

          background: Whether to run the model response in the background.
              [Learn more](https://platform.openai.com/docs/guides/background).

          include: Specify additional output data to include in the model response. Currently
              supported values are:

              - `file_search_call.results`: Include the search results of the file search tool
                call.
              - `message.input_image.image_url`: Include image urls from the input message.
              - `computer_call_output.output.image_url`: Include image urls from the computer
                call output.
              - `reasoning.encrypted_content`: Includes an encrypted version of reasoning
                tokens in reasoning item outputs. This enables reasoning items to be used in
                multi-turn conversations when using the Responses API statelessly (like when
                the `store` parameter is set to `false`, or when an organization is enrolled
                in the zero data retention program).
              - `code_interpreter_call.outputs`: Includes the outputs of python code execution
                in code interpreter tool call items.

          input: Text, image, or file inputs to the model, used to generate a response.

              Learn more:

              - [Text inputs and outputs](https://platform.openai.com/docs/guides/text)
              - [Image inputs](https://platform.openai.com/docs/guides/images)
              - [File inputs](https://platform.openai.com/docs/guides/pdf-files)
              - [Conversation state](https://platform.openai.com/docs/guides/conversation-state)
              - [Function calling](https://platform.openai.com/docs/guides/function-calling)

          instructions: A system (or developer) message inserted into the model's context.

              When using along with `previous_response_id`, the instructions from a previous
              response will not be carried over to the next response. This makes it simple to
              swap out system (or developer) messages in new responses.

          max_output_tokens: An upper bound for the number of tokens that can be generated for a response,
              including visible output tokens and
              [reasoning tokens](https://platform.openai.com/docs/guides/reasoning).

          metadata: Set of 16 key-value pairs that can be attached to an object. This can be useful
              for storing additional information about the object in a structured format, and
              querying for objects via API or the dashboard.

              Keys are strings with a maximum length of 64 characters. Values are strings with
              a maximum length of 512 characters.

          model: Model ID used to generate the response, like `gpt-4o` or `o3`. OpenAI offers a
              wide range of models with different capabilities, performance characteristics,
              and price points. Refer to the
              [model guide](https://platform.openai.com/docs/models) to browse and compare
              available models.

          parallel_tool_calls: Whether to allow the model to run tool calls in parallel.

          previous_response_id: The unique ID of the previous response to the model. Use this to create
              multi-turn conversations. Learn more about
              [conversation state](https://platform.openai.com/docs/guides/conversation-state).

          prompt: Reference to a prompt template and its variables.
              [Learn more](https://platform.openai.com/docs/guides/text?api-mode=responses#reusable-prompts).

          reasoning: **o-series models only**

              Configuration options for
              [reasoning models](https://platform.openai.com/docs/guides/reasoning).

          service_tier: Specifies the latency tier to use for processing the request. This parameter is
              relevant for customers subscribed to the scale tier service:

              - If set to 'auto', and the Project is Scale tier enabled, the system will
                utilize scale tier credits until they are exhausted.
              - If set to 'auto', and the Project is not Scale tier enabled, the request will
                be processed using the default service tier with a lower uptime SLA and no
                latency guarantee.
              - If set to 'default', the request will be processed using the default service
                tier with a lower uptime SLA and no latency guarantee.
              - If set to 'flex', the request will be processed with the Flex Processing
                service tier.
                [Learn more](https://platform.openai.com/docs/guides/flex-processing).
              - When not set, the default behavior is 'auto'.

              When this parameter is set, the response body will include the `service_tier`
              utilized.

          store: Whether to store the generated model response for later retrieval via API.

          temperature: What sampling temperature to use, between 0 and 2. Higher values like 0.8 will
              make the output more random, while lower values like 0.2 will make it more
              focused and deterministic. We generally recommend altering this or `top_p` but
              not both.

          text: Configuration options for a text response from the model. Can be plain text or
              structured JSON data. Learn more:

              - [Text inputs and outputs](https://platform.openai.com/docs/guides/text)
              - [Structured Outputs](https://platform.openai.com/docs/guides/structured-outputs)

          tool_choice: How the model should select which tool (or tools) to use when generating a
              response. See the `tools` parameter to see how to specify which tools the model
              can call.

          tools: An array of tools the model may call while generating a response. You can
              specify which tool to use by setting the `tool_choice` parameter.

              The two categories of tools you can provide the model are:

              - **Built-in tools**: Tools that are provided by OpenAI that extend the model's
                capabilities, like
                [web search](https://platform.openai.com/docs/guides/tools-web-search) or
                [file search](https://platform.openai.com/docs/guides/tools-file-search).
                Learn more about
                [built-in tools](https://platform.openai.com/docs/guides/tools).
              - **Function calls (custom tools)**: Functions that are defined by you, enabling
                the model to call your own code. Learn more about
                [function calling](https://platform.openai.com/docs/guides/function-calling).

          top_p: An alternative to sampling with temperature, called nucleus sampling, where the
              model considers the results of the tokens with top_p probability mass. So 0.1
              means only the tokens comprising the top 10% probability mass are considered.

              We generally recommend altering this or `temperature` but not both.

          truncation: The truncation strategy to use for the model response.

              - `auto`: If the context of this response and previous ones exceeds the model's
                context window size, the model will truncate the response to fit the context
                window by dropping input items in the middle of the conversation.
              - `disabled` (default): If a model response will exceed the context window size
                for a model, the request will fail with a 400 error.

          user: A stable identifier for your end-users. Used to boost cache hit rates by better
              bucketing similar requests and to help OpenAI detect and prevent abuse.
              [Learn more](https://platform.openai.com/docs/guides/safety-best-practices#end-user-ids).

          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request, in seconds
        """
        ...

    @overload
    def create(
        self,
        *,
        stream: bool,
        background: Optional[bool] | NotGiven = NOT_GIVEN,
        include: Optional[List[ResponseIncludable]] | NotGiven = NOT_GIVEN,
        input: Union[str, ResponseInputParam] | NotGiven = NOT_GIVEN,
        instructions: Optional[str] | NotGiven = NOT_GIVEN,
        max_output_tokens: Optional[int] | NotGiven = NOT_GIVEN,
        metadata: Optional[Metadata] | NotGiven = NOT_GIVEN,
        model: ResponsesModel | NotGiven = NOT_GIVEN,
        parallel_tool_calls: Optional[bool] | NotGiven = NOT_GIVEN,
        previous_response_id: Optional[str] | NotGiven = NOT_GIVEN,
        prompt: Optional[ResponsePromptParam] | NotGiven = NOT_GIVEN,
        reasoning: Optional[Reasoning] | NotGiven = NOT_GIVEN,
        service_tier: Optional[Literal["auto", "default", "flex", "scale"]] | NotGiven = NOT_GIVEN,
        store: Optional[bool] | NotGiven = NOT_GIVEN,
        temperature: Optional[float] | NotGiven = NOT_GIVEN,
        text: ResponseTextConfigParam | NotGiven = NOT_GIVEN,
        tool_choice: response_create_params.ToolChoice | NotGiven = NOT_GIVEN,
        tools: Iterable[ToolParam] | NotGiven = NOT_GIVEN,
        top_p: Optional[float] | NotGiven = NOT_GIVEN,
        truncation: Optional[Literal["auto", "disabled"]] | NotGiven = NOT_GIVEN,
        user: str | NotGiven = NOT_GIVEN,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> Response | Stream[ResponseStreamEvent]:
        """Creates a model response.

        Provide
        [text](https://platform.openai.com/docs/guides/text) or
        [image](https://platform.openai.com/docs/guides/images) inputs to generate
        [text](https://platform.openai.com/docs/guides/text) or
        [JSON](https://platform.openai.com/docs/guides/structured-outputs) outputs. Have
        the model call your own
        [custom code](https://platform.openai.com/docs/guides/function-calling) or use
        built-in [tools](https://platform.openai.com/docs/guides/tools) like
        [web search](https://platform.openai.com/docs/guides/tools-web-search) or
        [file search](https://platform.openai.com/docs/guides/tools-file-search) to use
        your own data as input for the model's response.

        Args:
          stream: If set to true, the model response data will be streamed to the client as it is
              generated using
              [server-sent events](https://developer.mozilla.org/en-US/docs/Web/API/Server-sent_events/Using_server-sent_events#Event_stream_format).
              See the
              [Streaming section below](https://platform.openai.com/docs/api-reference/responses-streaming)
              for more information.

          background: Whether to run the model response in the background.
              [Learn more](https://platform.openai.com/docs/guides/background).

          include: Specify additional output data to include in the model response. Currently
              supported values are:

              - `file_search_call.results`: Include the search results of the file search tool
                call.
              - `message.input_image.image_url`: Include image urls from the input message.
              - `computer_call_output.output.image_url`: Include image urls from the computer
                call output.
              - `reasoning.encrypted_content`: Includes an encrypted version of reasoning
                tokens in reasoning item outputs. This enables reasoning items to be used in
                multi-turn conversations when using the Responses API statelessly (like when
                the `store` parameter is set to `false`, or when an organization is enrolled
                in the zero data retention program).
              - `code_interpreter_call.outputs`: Includes the outputs of python code execution
                in code interpreter tool call items.

          input: Text, image, or file inputs to the model, used to generate a response.

              Learn more:

              - [Text inputs and outputs](https://platform.openai.com/docs/guides/text)
              - [Image inputs](https://platform.openai.com/docs/guides/images)
              - [File inputs](https://platform.openai.com/docs/guides/pdf-files)
              - [Conversation state](https://platform.openai.com/docs/guides/conversation-state)
              - [Function calling](https://platform.openai.com/docs/guides/function-calling)

          instructions: A system (or developer) message inserted into the model's context.

              When using along with `previous_response_id`, the instructions from a previous
              response will not be carried over to the next response. This makes it simple to
              swap out system (or developer) messages in new responses.

          max_output_tokens: An upper bound for the number of tokens that can be generated for a response,
              including visible output tokens and
              [reasoning tokens](https://platform.openai.com/docs/guides/reasoning).

          metadata: Set of 16 key-value pairs that can be attached to an object. This can be useful
              for storing additional information about the object in a structured format, and
              querying for objects via API or the dashboard.

              Keys are strings with a maximum length of 64 characters. Values are strings with
              a maximum length of 512 characters.

          model: Model ID used to generate the response, like `gpt-4o` or `o3`. OpenAI offers a
              wide range of models with different capabilities, performance characteristics,
              and price points. Refer to the
              [model guide](https://platform.openai.com/docs/models) to browse and compare
              available models.

          parallel_tool_calls: Whether to allow the model to run tool calls in parallel.

          previous_response_id: The unique ID of the previous response to the model. Use this to create
              multi-turn conversations. Learn more about
              [conversation state](https://platform.openai.com/docs/guides/conversation-state).

          prompt: Reference to a prompt template and its variables.
              [Learn more](https://platform.openai.com/docs/guides/text?api-mode=responses#reusable-prompts).

          reasoning: **o-series models only**

              Configuration options for
              [reasoning models](https://platform.openai.com/docs/guides/reasoning).

          service_tier: Specifies the latency tier to use for processing the request. This parameter is
              relevant for customers subscribed to the scale tier service:

              - If set to 'auto', and the Project is Scale tier enabled, the system will
                utilize scale tier credits until they are exhausted.
              - If set to 'auto', and the Project is not Scale tier enabled, the request will
                be processed using the default service tier with a lower uptime SLA and no
                latency guarantee.
              - If set to 'default', the request will be processed using the default service
                tier with a lower uptime SLA and no latency guarantee.
              - If set to 'flex', the request will be processed with the Flex Processing
                service tier.
                [Learn more](https://platform.openai.com/docs/guides/flex-processing).
              - When not set, the default behavior is 'auto'.

              When this parameter is set, the response body will include the `service_tier`
              utilized.

          store: Whether to store the generated model response for later retrieval via API.

          temperature: What sampling temperature to use, between 0 and 2. Higher values like 0.8 will
              make the output more random, while lower values like 0.2 will make it more
              focused and deterministic. We generally recommend altering this or `top_p` but
              not both.

          text: Configuration options for a text response from the model. Can be plain text or
              structured JSON data. Learn more:

              - [Text inputs and outputs](https://platform.openai.com/docs/guides/text)
              - [Structured Outputs](https://platform.openai.com/docs/guides/structured-outputs)

          tool_choice: How the model should select which tool (or tools) to use when generating a
              response. See the `tools` parameter to see how to specify which tools the model
              can call.

          tools: An array of tools the model may call while generating a response. You can
              specify which tool to use by setting the `tool_choice` parameter.

              The two categories of tools you can provide the model are:

              - **Built-in tools**: Tools that are provided by OpenAI that extend the model's
                capabilities, like
                [web search](https://platform.openai.com/docs/guides/tools-web-search) or
                [file search](https://platform.openai.com/docs/guides/tools-file-search).
                Learn more about
                [built-in tools](https://platform.openai.com/docs/guides/tools).
              - **Function calls (custom tools)**: Functions that are defined by you, enabling
                the model to call your own code. Learn more about
                [function calling](https://platform.openai.com/docs/guides/function-calling).

          top_p: An alternative to sampling with temperature, called nucleus sampling, where the
              model considers the results of the tokens with top_p probability mass. So 0.1
              means only the tokens comprising the top 10% probability mass are considered.

              We generally recommend altering this or `temperature` but not both.

          truncation: The truncation strategy to use for the model response.

              - `auto`: If the context of this response and previous ones exceeds the model's
                context window size, the model will truncate the response to fit the context
                window by dropping input items in the middle of the conversation.
              - `disabled` (default): If a model response will exceed the context window size
                for a model, the request will fail with a 400 error.

          user: A stable identifier for your end-users. Used to boost cache hit rates by better
              bucketing similar requests and to help OpenAI detect and prevent abuse.
              [Learn more](https://platform.openai.com/docs/guides/safety-best-practices#end-user-ids).

          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request, in seconds
        """
        ...

    def create(
        self,
        *,
        background: Optional[bool] | NotGiven = NOT_GIVEN,
        include: Optional[List[ResponseIncludable]] | NotGiven = NOT_GIVEN,
        input: Union[str, ResponseInputParam] | NotGiven = NOT_GIVEN,
        instructions: Optional[str] | NotGiven = NOT_GIVEN,
        max_output_tokens: Optional[int] | NotGiven = NOT_GIVEN,
        metadata: Optional[Metadata] | NotGiven = NOT_GIVEN,
        model: ResponsesModel | NotGiven = NOT_GIVEN,
        parallel_tool_calls: Optional[bool] | NotGiven = NOT_GIVEN,
        previous_response_id: Optional[str] | NotGiven = NOT_GIVEN,
        prompt: Optional[ResponsePromptParam] | NotGiven = NOT_GIVEN,
        reasoning: Optional[Reasoning] | NotGiven = NOT_GIVEN,
        service_tier: Optional[Literal["auto", "default", "flex", "scale"]] | NotGiven = NOT_GIVEN,
        store: Optional[bool] | NotGiven = NOT_GIVEN,
        stream: Optional[Literal[False]] | Literal[True] | NotGiven = NOT_GIVEN,
        temperature: Optional[float] | NotGiven = NOT_GIVEN,
        text: ResponseTextConfigParam | NotGiven = NOT_GIVEN,
        tool_choice: response_create_params.ToolChoice | NotGiven = NOT_GIVEN,
        tools: Iterable[ToolParam] | NotGiven = NOT_GIVEN,
        top_p: Optional[float] | NotGiven = NOT_GIVEN,
        truncation: Optional[Literal["auto", "disabled"]] | NotGiven = NOT_GIVEN,
        user: str | NotGiven = NOT_GIVEN,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> Response | Stream[ResponseStreamEvent]:
        return self._post(
            "/responses",
            body=maybe_transform(
                {
                    "background": background,
                    "include": include,
                    "input": input,
                    "instructions": instructions,
                    "max_output_tokens": max_output_tokens,
                    "metadata": metadata,
                    "model": model,
                    "parallel_tool_calls": parallel_tool_calls,
                    "previous_response_id": previous_response_id,
                    "prompt": prompt,
                    "reasoning": reasoning,
                    "service_tier": service_tier,
                    "store": store,
                    "stream": stream,
                    "temperature": temperature,
                    "text": text,
                    "tool_choice": tool_choice,
                    "tools": tools,
                    "top_p": top_p,
                    "truncation": truncation,
                    "user": user,
                },
                response_create_params.ResponseCreateParamsStreaming
                if stream
                else response_create_params.ResponseCreateParamsNonStreaming,
            ),
            options=make_request_options(
                extra_headers=extra_headers, extra_query=extra_query, extra_body=extra_body, timeout=timeout
            ),
            cast_to=Response,
            stream=stream or False,
            stream_cls=Stream[ResponseStreamEvent],
        )

    @overload
    def stream(
        self,
        *,
        response_id: str,
        text_format: type[TextFormatT] | NotGiven = NOT_GIVEN,
        starting_after: int | NotGiven = NOT_GIVEN,
        tools: Iterable[ParseableToolParam] | NotGiven = NOT_GIVEN,
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> ResponseStreamManager[TextFormatT]: ...

    @overload
    def stream(
        self,
        *,
        input: Union[str, ResponseInputParam],
        model: Union[str, ChatModel],
        background: Optional[bool] | NotGiven = NOT_GIVEN,
        text_format: type[TextFormatT] | NotGiven = NOT_GIVEN,
        tools: Iterable[ParseableToolParam] | NotGiven = NOT_GIVEN,
        include: Optional[List[ResponseIncludable]] | NotGiven = NOT_GIVEN,
        instructions: Optional[str] | NotGiven = NOT_GIVEN,
        max_output_tokens: Optional[int] | NotGiven = NOT_GIVEN,
        metadata: Optional[Metadata] | NotGiven = NOT_GIVEN,
        parallel_tool_calls: Optional[bool] | NotGiven = NOT_GIVEN,
        previous_response_id: Optional[str] | NotGiven = NOT_GIVEN,
        reasoning: Optional[Reasoning] | NotGiven = NOT_GIVEN,
        store: Optional[bool] | NotGiven = NOT_GIVEN,
        temperature: Optional[float] | NotGiven = NOT_GIVEN,
        text: ResponseTextConfigParam | NotGiven = NOT_GIVEN,
        tool_choice: response_create_params.ToolChoice | NotGiven = NOT_GIVEN,
        top_p: Optional[float] | NotGiven = NOT_GIVEN,
        truncation: Optional[Literal["auto", "disabled"]] | NotGiven = NOT_GIVEN,
        user: str | NotGiven = NOT_GIVEN,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> ResponseStreamManager[TextFormatT]: ...

    def stream(
        self,
        *,
        response_id: str | NotGiven = NOT_GIVEN,
        input: Union[str, ResponseInputParam] | NotGiven = NOT_GIVEN,
        model: Union[str, ChatModel] | NotGiven = NOT_GIVEN,
        background: Optional[bool] | NotGiven = NOT_GIVEN,
        text_format: type[TextFormatT] | NotGiven = NOT_GIVEN,
        tools: Iterable[ParseableToolParam] | NotGiven = NOT_GIVEN,
        include: Optional[List[ResponseIncludable]] | NotGiven = NOT_GIVEN,
        instructions: Optional[str] | NotGiven = NOT_GIVEN,
        max_output_tokens: Optional[int] | NotGiven = NOT_GIVEN,
        metadata: Optional[Metadata] | NotGiven = NOT_GIVEN,
        parallel_tool_calls: Optional[bool] | NotGiven = NOT_GIVEN,
        previous_response_id: Optional[str] | NotGiven = NOT_GIVEN,
        reasoning: Optional[Reasoning] | NotGiven = NOT_GIVEN,
        store: Optional[bool] | NotGiven = NOT_GIVEN,
        temperature: Optional[float] | NotGiven = NOT_GIVEN,
        text: ResponseTextConfigParam | NotGiven = NOT_GIVEN,
        tool_choice: response_create_params.ToolChoice | NotGiven = NOT_GIVEN,
        top_p: Optional[float] | NotGiven = NOT_GIVEN,
        truncation: Optional[Literal["auto", "disabled"]] | NotGiven = NOT_GIVEN,
        user: str | NotGiven = NOT_GIVEN,
        starting_after: int | NotGiven = NOT_GIVEN,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> ResponseStreamManager[TextFormatT]:
        new_response_args = {
            "input": input,
            "model": model,
            "include": include,
            "instructions": instructions,
            "max_output_tokens": max_output_tokens,
            "metadata": metadata,
            "parallel_tool_calls": parallel_tool_calls,
            "previous_response_id": previous_response_id,
            "reasoning": reasoning,
            "store": store,
            "temperature": temperature,
            "text": text,
            "tool_choice": tool_choice,
            "top_p": top_p,
            "truncation": truncation,
            "user": user,
            "background": background,
        }
        new_response_args_names = [k for k, v in new_response_args.items() if is_given(v)]

        if (is_given(response_id) or is_given(starting_after)) and len(new_response_args_names) > 0:
            raise ValueError(
                "Cannot provide both response_id/starting_after can't be provided together with "
                + ", ".join(new_response_args_names)
            )
        tools = _make_tools(tools)
        if len(new_response_args_names) > 0:
            if not is_given(input):
                raise ValueError("input must be provided when creating a new response")

            if not is_given(model):
                raise ValueError("model must be provided when creating a new response")

            if is_given(text_format):
                if not text:
                    text = {}

                if "format" in text:
                    raise TypeError("Cannot mix and match text.format with text_format")

                text["format"] = _type_to_text_format_param(text_format)

            api_request: partial[Stream[ResponseStreamEvent]] = partial(
                self.create,
                input=input,
                model=model,
                tools=tools,
                include=include,
                instructions=instructions,
                max_output_tokens=max_output_tokens,
                metadata=metadata,
                parallel_tool_calls=parallel_tool_calls,
                previous_response_id=previous_response_id,
                store=store,
                stream=True,
                temperature=temperature,
                text=text,
                tool_choice=tool_choice,
                reasoning=reasoning,
                top_p=top_p,
                truncation=truncation,
                user=user,
                background=background,
                extra_headers=extra_headers,
                extra_query=extra_query,
                extra_body=extra_body,
                timeout=timeout,
            )

            return ResponseStreamManager(api_request, text_format=text_format, input_tools=tools, starting_after=None)
        else:
            if not is_given(response_id):
                raise ValueError("id must be provided when streaming an existing response")

            return ResponseStreamManager(
                lambda: self.retrieve(
                    response_id=response_id,
                    stream=True,
                    include=include or [],
                    extra_headers=extra_headers,
                    extra_query=extra_query,
                    extra_body=extra_body,
                    starting_after=NOT_GIVEN,
                    timeout=timeout,
                ),
                text_format=text_format,
                input_tools=tools,
                starting_after=starting_after if is_given(starting_after) else None,
            )

    def parse(
        self,
        *,
        input: Union[str, ResponseInputParam],
        model: Union[str, ChatModel],
        text_format: type[TextFormatT] | NotGiven = NOT_GIVEN,
        tools: Iterable[ParseableToolParam] | NotGiven = NOT_GIVEN,
        include: Optional[List[ResponseIncludable]] | NotGiven = NOT_GIVEN,
        instructions: Optional[str] | NotGiven = NOT_GIVEN,
        max_output_tokens: Optional[int] | NotGiven = NOT_GIVEN,
        metadata: Optional[Metadata] | NotGiven = NOT_GIVEN,
        parallel_tool_calls: Optional[bool] | NotGiven = NOT_GIVEN,
        previous_response_id: Optional[str] | NotGiven = NOT_GIVEN,
        reasoning: Optional[Reasoning] | NotGiven = NOT_GIVEN,
        store: Optional[bool] | NotGiven = NOT_GIVEN,
        stream: Optional[Literal[False]] | Literal[True] | NotGiven = NOT_GIVEN,
        temperature: Optional[float] | NotGiven = NOT_GIVEN,
        text: ResponseTextConfigParam | NotGiven = NOT_GIVEN,
        tool_choice: response_create_params.ToolChoice | NotGiven = NOT_GIVEN,
        top_p: Optional[float] | NotGiven = NOT_GIVEN,
        truncation: Optional[Literal["auto", "disabled"]] | NotGiven = NOT_GIVEN,
        user: str | NotGiven = NOT_GIVEN,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> ParsedResponse[TextFormatT]:
        if is_given(text_format):
            if not text:
                text = {}

            if "format" in text:
                raise TypeError("Cannot mix and match text.format with text_format")

            text["format"] = _type_to_text_format_param(text_format)

        tools = _make_tools(tools)

        def parser(raw_response: Response) -> ParsedResponse[TextFormatT]:
            return parse_response(
                input_tools=tools,
                text_format=text_format,
                response=raw_response,
            )

        return self._post(
            "/responses",
            body=maybe_transform(
                {
                    "input": input,
                    "model": model,
                    "include": include,
                    "instructions": instructions,
                    "max_output_tokens": max_output_tokens,
                    "metadata": metadata,
                    "parallel_tool_calls": parallel_tool_calls,
                    "previous_response_id": previous_response_id,
                    "reasoning": reasoning,
                    "store": store,
                    "stream": stream,
                    "temperature": temperature,
                    "text": text,
                    "tool_choice": tool_choice,
                    "tools": tools,
                    "top_p": top_p,
                    "truncation": truncation,
                    "user": user,
                },
                response_create_params.ResponseCreateParams,
            ),
            options=make_request_options(
                extra_headers=extra_headers,
                extra_query=extra_query,
                extra_body=extra_body,
                timeout=timeout,
                post_parser=parser,
            ),
            # we turn the `Response` instance into a `ParsedResponse`
            # in the `parser` function above
            cast_to=cast(Type[ParsedResponse[TextFormatT]], Response),
        )

    @overload
    def retrieve(
        self,
        response_id: str,
        *,
        include: List[ResponseIncludable] | NotGiven = NOT_GIVEN,
        starting_after: int | NotGiven = NOT_GIVEN,
        stream: Literal[False] | NotGiven = NOT_GIVEN,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> Response: ...

    @overload
    def retrieve(
        self,
        response_id: str,
        *,
        stream: Literal[True],
        include: List[ResponseIncludable] | NotGiven = NOT_GIVEN,
        starting_after: int | NotGiven = NOT_GIVEN,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> Stream[ResponseStreamEvent]: ...

    @overload
    def retrieve(
        self,
        response_id: str,
        *,
        stream: bool,
        include: List[ResponseIncludable] | NotGiven = NOT_GIVEN,
        starting_after: int | NotGiven = NOT_GIVEN,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> Response | Stream[ResponseStreamEvent]: ...

    @overload
    def retrieve(
        self,
        response_id: str,
        *,
        stream: bool = False,
        include: List[ResponseIncludable] | NotGiven = NOT_GIVEN,
        starting_after: int | NotGiven = NOT_GIVEN,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> Response | Stream[ResponseStreamEvent]:
        """
        Retrieves a model response with the given ID.

        Args:
          include: Additional fields to include in the response. See the `include` parameter for
              Response creation above for more information.

          starting_after: The sequence number of the event after which to start streaming.

          stream: If set to true, the model response data will be streamed to the client as it is
              generated using
              [server-sent events](https://developer.mozilla.org/en-US/docs/Web/API/Server-sent_events/Using_server-sent_events#Event_stream_format).
              See the
              [Streaming section below](https://platform.openai.com/docs/api-reference/responses-streaming)
              for more information.

          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request, in seconds
        """
        ...

    @overload
    def retrieve(
        self,
        response_id: str,
        *,
        stream: Literal[True],
        include: List[ResponseIncludable] | NotGiven = NOT_GIVEN,
        starting_after: int | NotGiven = NOT_GIVEN,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> Stream[ResponseStreamEvent]:
        """
        Retrieves a model response with the given ID.

        Args:
          stream: If set to true, the model response data will be streamed to the client as it is
              generated using
              [server-sent events](https://developer.mozilla.org/en-US/docs/Web/API/Server-sent_events/Using_server-sent_events#Event_stream_format).
              See the
              [Streaming section below](https://platform.openai.com/docs/api-reference/responses-streaming)
              for more information.

          include: Additional fields to include in the response. See the `include` parameter for
              Response creation above for more information.

          starting_after: The sequence number of the event after which to start streaming.

          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request, in seconds
        """
        ...

    @overload
    def retrieve(
        self,
        response_id: str,
        *,
        stream: bool,
        include: List[ResponseIncludable] | NotGiven = NOT_GIVEN,
        starting_after: int | NotGiven = NOT_GIVEN,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> Response | Stream[ResponseStreamEvent]:
        """
        Retrieves a model response with the given ID.

        Args:
          stream: If set to true, the model response data will be streamed to the client as it is
              generated using
              [server-sent events](https://developer.mozilla.org/en-US/docs/Web/API/Server-sent_events/Using_server-sent_events#Event_stream_format).
              See the
              [Streaming section below](https://platform.openai.com/docs/api-reference/responses-streaming)
              for more information.

          include: Additional fields to include in the response. See the `include` parameter for
              Response creation above for more information.

          starting_after: The sequence number of the event after which to start streaming.

          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request, in seconds
        """
        ...

    def retrieve(
        self,
        response_id: str,
        *,
        include: List[ResponseIncludable] | NotGiven = NOT_GIVEN,
        starting_after: int | NotGiven = NOT_GIVEN,
        stream: Literal[False] | Literal[True] | NotGiven = NOT_GIVEN,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> Response | Stream[ResponseStreamEvent]:
        if not response_id:
            raise ValueError(f"Expected a non-empty value for `response_id` but received {response_id!r}")
        return self._get(
            f"/responses/{response_id}",
            options=make_request_options(
                extra_headers=extra_headers,
                extra_query=extra_query,
                extra_body=extra_body,
                timeout=timeout,
                query=maybe_transform(
                    {
                        "include": include,
                        "starting_after": starting_after,
                        "stream": stream,
                    },
                    response_retrieve_params.ResponseRetrieveParams,
                ),
            ),
            cast_to=Response,
            stream=stream or False,
            stream_cls=Stream[ResponseStreamEvent],
        )

    def delete(
        self,
        response_id: str,
        *,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> None:
        """
        Deletes a model response with the given ID.

        Args:
          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request, in seconds
        """
        if not response_id:
            raise ValueError(f"Expected a non-empty value for `response_id` but received {response_id!r}")
        extra_headers = {"Accept": "*/*", **(extra_headers or {})}
        return self._delete(
            f"/responses/{response_id}",
            options=make_request_options(
                extra_headers=extra_headers, extra_query=extra_query, extra_body=extra_body, timeout=timeout
            ),
            cast_to=NoneType,
        )

    def cancel(
        self,
        response_id: str,
        *,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> Response:
        """Cancels a model response with the given ID.

        Only responses created with the
        `background` parameter set to `true` can be cancelled.
        [Learn more](https://platform.openai.com/docs/guides/background).

        Args:
          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request, in seconds
        """
        if not response_id:
            raise ValueError(f"Expected a non-empty value for `response_id` but received {response_id!r}")
        return self._post(
            f"/responses/{response_id}/cancel",
            options=make_request_options(
                extra_headers=extra_headers, extra_query=extra_query, extra_body=extra_body, timeout=timeout
            ),
            cast_to=Response,
        )


class AsyncResponses(AsyncAPIResource):
    @cached_property
    def input_items(self) -> AsyncInputItems:
        return AsyncInputItems(self._client)

    @cached_property
    def with_raw_response(self) -> AsyncResponsesWithRawResponse:
        """
        This property can be used as a prefix for any HTTP method call to return
        the raw response object instead of the parsed content.

        For more information, see https://www.github.com/openai/openai-python#accessing-raw-response-data-eg-headers
        """
        return AsyncResponsesWithRawResponse(self)

    @cached_property
    def with_streaming_response(self) -> AsyncResponsesWithStreamingResponse:
        """
        An alternative to `.with_raw_response` that doesn't eagerly read the response body.

        For more information, see https://www.github.com/openai/openai-python#with_streaming_response
        """
        return AsyncResponsesWithStreamingResponse(self)

    @overload
    async def create(
        self,
        *,
        background: Optional[bool] | NotGiven = NOT_GIVEN,
        include: Optional[List[ResponseIncludable]] | NotGiven = NOT_GIVEN,
        input: Union[str, ResponseInputParam] | NotGiven = NOT_GIVEN,
        instructions: Optional[str] | NotGiven = NOT_GIVEN,
        max_output_tokens: Optional[int] | NotGiven = NOT_GIVEN,
        metadata: Optional[Metadata] | NotGiven = NOT_GIVEN,
        model: ResponsesModel | NotGiven = NOT_GIVEN,
        parallel_tool_calls: Optional[bool] | NotGiven = NOT_GIVEN,
        previous_response_id: Optional[str] | NotGiven = NOT_GIVEN,
        prompt: Optional[ResponsePromptParam] | NotGiven = NOT_GIVEN,
        reasoning: Optional[Reasoning] | NotGiven = NOT_GIVEN,
        service_tier: Optional[Literal["auto", "default", "flex", "scale"]] | NotGiven = NOT_GIVEN,
        store: Optional[bool] | NotGiven = NOT_GIVEN,
        stream: Optional[Literal[False]] | NotGiven = NOT_GIVEN,
        temperature: Optional[float] | NotGiven = NOT_GIVEN,
        text: ResponseTextConfigParam | NotGiven = NOT_GIVEN,
        tool_choice: response_create_params.ToolChoice | NotGiven = NOT_GIVEN,
        tools: Iterable[ToolParam] | NotGiven = NOT_GIVEN,
        top_p: Optional[float] | NotGiven = NOT_GIVEN,
        truncation: Optional[Literal["auto", "disabled"]] | NotGiven = NOT_GIVEN,
        user: str | NotGiven = NOT_GIVEN,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> Response:
        """Creates a model response.

        Provide
        [text](https://platform.openai.com/docs/guides/text) or
        [image](https://platform.openai.com/docs/guides/images) inputs to generate
        [text](https://platform.openai.com/docs/guides/text) or
        [JSON](https://platform.openai.com/docs/guides/structured-outputs) outputs. Have
        the model call your own
        [custom code](https://platform.openai.com/docs/guides/function-calling) or use
        built-in [tools](https://platform.openai.com/docs/guides/tools) like
        [web search](https://platform.openai.com/docs/guides/tools-web-search) or
        [file search](https://platform.openai.com/docs/guides/tools-file-search) to use
        your own data as input for the model's response.

        Args:
          background: Whether to run the model response in the background.
              [Learn more](https://platform.openai.com/docs/guides/background).

          include: Specify additional output data to include in the model response. Currently
              supported values are:

              - `file_search_call.results`: Include the search results of the file search tool
                call.
              - `message.input_image.image_url`: Include image urls from the input message.
              - `computer_call_output.output.image_url`: Include image urls from the computer
                call output.
              - `reasoning.encrypted_content`: Includes an encrypted version of reasoning
                tokens in reasoning item outputs. This enables reasoning items to be used in
                multi-turn conversations when using the Responses API statelessly (like when
                the `store` parameter is set to `false`, or when an organization is enrolled
                in the zero data retention program).
              - `code_interpreter_call.outputs`: Includes the outputs of python code execution
                in code interpreter tool call items.

          input: Text, image, or file inputs to the model, used to generate a response.

              Learn more:

              - [Text inputs and outputs](https://platform.openai.com/docs/guides/text)
              - [Image inputs](https://platform.openai.com/docs/guides/images)
              - [File inputs](https://platform.openai.com/docs/guides/pdf-files)
              - [Conversation state](https://platform.openai.com/docs/guides/conversation-state)
              - [Function calling](https://platform.openai.com/docs/guides/function-calling)

          instructions: A system (or developer) message inserted into the model's context.

              When using along with `previous_response_id`, the instructions from a previous
              response will not be carried over to the next response. This makes it simple to
              swap out system (or developer) messages in new responses.

          max_output_tokens: An upper bound for the number of tokens that can be generated for a response,
              including visible output tokens and
              [reasoning tokens](https://platform.openai.com/docs/guides/reasoning).

          metadata: Set of 16 key-value pairs that can be attached to an object. This can be useful
              for storing additional information about the object in a structured format, and
              querying for objects via API or the dashboard.

              Keys are strings with a maximum length of 64 characters. Values are strings with
              a maximum length of 512 characters.

          model: Model ID used to generate the response, like `gpt-4o` or `o3`. OpenAI offers a
              wide range of models with different capabilities, performance characteristics,
              and price points. Refer to the
              [model guide](https://platform.openai.com/docs/models) to browse and compare
              available models.

          parallel_tool_calls: Whether to allow the model to run tool calls in parallel.

          previous_response_id: The unique ID of the previous response to the model. Use this to create
              multi-turn conversations. Learn more about
              [conversation state](https://platform.openai.com/docs/guides/conversation-state).

          prompt: Reference to a prompt template and its variables.
              [Learn more](https://platform.openai.com/docs/guides/text?api-mode=responses#reusable-prompts).

          reasoning: **o-series models only**

              Configuration options for
              [reasoning models](https://platform.openai.com/docs/guides/reasoning).

          service_tier: Specifies the latency tier to use for processing the request. This parameter is
              relevant for customers subscribed to the scale tier service:

              - If set to 'auto', and the Project is Scale tier enabled, the system will
                utilize scale tier credits until they are exhausted.
              - If set to 'auto', and the Project is not Scale tier enabled, the request will
                be processed using the default service tier with a lower uptime SLA and no
                latency guarantee.
              - If set to 'default', the request will be processed using the default service
                tier with a lower uptime SLA and no latency guarantee.
              - If set to 'flex', the request will be processed with the Flex Processing
                service tier.
                [Learn more](https://platform.openai.com/docs/guides/flex-processing).
              - When not set, the default behavior is 'auto'.

              When this parameter is set, the response body will include the `service_tier`
              utilized.

          store: Whether to store the generated model response for later retrieval via API.

          stream: If set to true, the model response data will be streamed to the client as it is
              generated using
              [server-sent events](https://developer.mozilla.org/en-US/docs/Web/API/Server-sent_events/Using_server-sent_events#Event_stream_format).
              See the
              [Streaming section below](https://platform.openai.com/docs/api-reference/responses-streaming)
              for more information.

          temperature: What sampling temperature to use, between 0 and 2. Higher values like 0.8 will
              make the output more random, while lower values like 0.2 will make it more
              focused and deterministic. We generally recommend altering this or `top_p` but
              not both.

          text: Configuration options for a text response from the model. Can be plain text or
              structured JSON data. Learn more:

              - [Text inputs and outputs](https://platform.openai.com/docs/guides/text)
              - [Structured Outputs](https://platform.openai.com/docs/guides/structured-outputs)

          tool_choice: How the model should select which tool (or tools) to use when generating a
              response. See the `tools` parameter to see how to specify which tools the model
              can call.

          tools: An array of tools the model may call while generating a response. You can
              specify which tool to use by setting the `tool_choice` parameter.

              The two categories of tools you can provide the model are:

              - **Built-in tools**: Tools that are provided by OpenAI that extend the model's
                capabilities, like
                [web search](https://platform.openai.com/docs/guides/tools-web-search) or
                [file search](https://platform.openai.com/docs/guides/tools-file-search).
                Learn more about
                [built-in tools](https://platform.openai.com/docs/guides/tools).
              - **Function calls (custom tools)**: Functions that are defined by you, enabling
                the model to call your own code. Learn more about
                [function calling](https://platform.openai.com/docs/guides/function-calling).

          top_p: An alternative to sampling with temperature, called nucleus sampling, where the
              model considers the results of the tokens with top_p probability mass. So 0.1
              means only the tokens comprising the top 10% probability mass are considered.

              We generally recommend altering this or `temperature` but not both.

          truncation: The truncation strategy to use for the model response.

              - `auto`: If the context of this response and previous ones exceeds the model's
                context window size, the model will truncate the response to fit the context
                window by dropping input items in the middle of the conversation.
              - `disabled` (default): If a model response will exceed the context window size
                for a model, the request will fail with a 400 error.

          user: A stable identifier for your end-users. Used to boost cache hit rates by better
              bucketing similar requests and to help OpenAI detect and prevent abuse.
              [Learn more](https://platform.openai.com/docs/guides/safety-best-practices#end-user-ids).

          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request, in seconds
        """
        ...

    @overload
    async def create(
        self,
        *,
        stream: Literal[True],
        background: Optional[bool] | NotGiven = NOT_GIVEN,
        include: Optional[List[ResponseIncludable]] | NotGiven = NOT_GIVEN,
        input: Union[str, ResponseInputParam] | NotGiven = NOT_GIVEN,
        instructions: Optional[str] | NotGiven = NOT_GIVEN,
        max_output_tokens: Optional[int] | NotGiven = NOT_GIVEN,
        metadata: Optional[Metadata] | NotGiven = NOT_GIVEN,
        model: ResponsesModel | NotGiven = NOT_GIVEN,
        parallel_tool_calls: Optional[bool] | NotGiven = NOT_GIVEN,
        previous_response_id: Optional[str] | NotGiven = NOT_GIVEN,
        prompt: Optional[ResponsePromptParam] | NotGiven = NOT_GIVEN,
        reasoning: Optional[Reasoning] | NotGiven = NOT_GIVEN,
        service_tier: Optional[Literal["auto", "default", "flex", "scale"]] | NotGiven = NOT_GIVEN,
        store: Optional[bool] | NotGiven = NOT_GIVEN,
        temperature: Optional[float] | NotGiven = NOT_GIVEN,
        text: ResponseTextConfigParam | NotGiven = NOT_GIVEN,
        tool_choice: response_create_params.ToolChoice | NotGiven = NOT_GIVEN,
        tools: Iterable[ToolParam] | NotGiven = NOT_GIVEN,
        top_p: Optional[float] | NotGiven = NOT_GIVEN,
        truncation: Optional[Literal["auto", "disabled"]] | NotGiven = NOT_GIVEN,
        user: str | NotGiven = NOT_GIVEN,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> AsyncStream[ResponseStreamEvent]:
        """Creates a model response.

        Provide
        [text](https://platform.openai.com/docs/guides/text) or
        [image](https://platform.openai.com/docs/guides/images) inputs to generate
        [text](https://platform.openai.com/docs/guides/text) or
        [JSON](https://platform.openai.com/docs/guides/structured-outputs) outputs. Have
        the model call your own
        [custom code](https://platform.openai.com/docs/guides/function-calling) or use
        built-in [tools](https://platform.openai.com/docs/guides/tools) like
        [web search](https://platform.openai.com/docs/guides/tools-web-search) or
        [file search](https://platform.openai.com/docs/guides/tools-file-search) to use
        your own data as input for the model's response.

        Args:
          stream: If set to true, the model response data will be streamed to the client as it is
              generated using
              [server-sent events](https://developer.mozilla.org/en-US/docs/Web/API/Server-sent_events/Using_server-sent_events#Event_stream_format).
              See the
              [Streaming section below](https://platform.openai.com/docs/api-reference/responses-streaming)
              for more information.

          background: Whether to run the model response in the background.
              [Learn more](https://platform.openai.com/docs/guides/background).

          include: Specify additional output data to include in the model response. Currently
              supported values are:

              - `file_search_call.results`: Include the search results of the file search tool
                call.
              - `message.input_image.image_url`: Include image urls from the input message.
              - `computer_call_output.output.image_url`: Include image urls from the computer
                call output.
              - `reasoning.encrypted_content`: Includes an encrypted version of reasoning
                tokens in reasoning item outputs. This enables reasoning items to be used in
                multi-turn conversations when using the Responses API statelessly (like when
                the `store` parameter is set to `false`, or when an organization is enrolled
                in the zero data retention program).
              - `code_interpreter_call.outputs`: Includes the outputs of python code execution
                in code interpreter tool call items.

          input: Text, image, or file inputs to the model, used to generate a response.

              Learn more:

              - [Text inputs and outputs](https://platform.openai.com/docs/guides/text)
              - [Image inputs](https://platform.openai.com/docs/guides/images)
              - [File inputs](https://platform.openai.com/docs/guides/pdf-files)
              - [Conversation state](https://platform.openai.com/docs/guides/conversation-state)
              - [Function calling](https://platform.openai.com/docs/guides/function-calling)

          instructions: A system (or developer) message inserted into the model's context.

              When using along with `previous_response_id`, the instructions from a previous
              response will not be carried over to the next response. This makes it simple to
              swap out system (or developer) messages in new responses.

          max_output_tokens: An upper bound for the number of tokens that can be generated for a response,
              including visible output tokens and
              [reasoning tokens](https://platform.openai.com/docs/guides/reasoning).

          metadata: Set of 16 key-value pairs that can be attached to an object. This can be useful
              for storing additional information about the object in a structured format, and
              querying for objects via API or the dashboard.

              Keys are strings with a maximum length of 64 characters. Values are strings with
              a maximum length of 512 characters.

          model: Model ID used to generate the response, like `gpt-4o` or `o3`. OpenAI offers a
              wide range of models with different capabilities, performance characteristics,
              and price points. Refer to the
              [model guide](https://platform.openai.com/docs/models) to browse and compare
              available models.

          parallel_tool_calls: Whether to allow the model to run tool calls in parallel.

          previous_response_id: The unique ID of the previous response to the model. Use this to create
              multi-turn conversations. Learn more about
              [conversation state](https://platform.openai.com/docs/guides/conversation-state).

          prompt: Reference to a prompt template and its variables.
              [Learn more](https://platform.openai.com/docs/guides/text?api-mode=responses#reusable-prompts).

          reasoning: **o-series models only**

              Configuration options for
              [reasoning models](https://platform.openai.com/docs/guides/reasoning).

          service_tier: Specifies the latency tier to use for processing the request. This parameter is
              relevant for customers subscribed to the scale tier service:

              - If set to 'auto', and the Project is Scale tier enabled, the system will
                utilize scale tier credits until they are exhausted.
              - If set to 'auto', and the Project is not Scale tier enabled, the request will
                be processed using the default service tier with a lower uptime SLA and no
                latency guarantee.
              - If set to 'default', the request will be processed using the default service
                tier with a lower uptime SLA and no latency guarantee.
              - If set to 'flex', the request will be processed with the Flex Processing
                service tier.
                [Learn more](https://platform.openai.com/docs/guides/flex-processing).
              - When not set, the default behavior is 'auto'.

              When this parameter is set, the response body will include the `service_tier`
              utilized.

          store: Whether to store the generated model response for later retrieval via API.

          temperature: What sampling temperature to use, between 0 and 2. Higher values like 0.8 will
              make the output more random, while lower values like 0.2 will make it more
              focused and deterministic. We generally recommend altering this or `top_p` but
              not both.

          text: Configuration options for a text response from the model. Can be plain text or
              structured JSON data. Learn more:

              - [Text inputs and outputs](https://platform.openai.com/docs/guides/text)
              - [Structured Outputs](https://platform.openai.com/docs/guides/structured-outputs)

          tool_choice: How the model should select which tool (or tools) to use when generating a
              response. See the `tools` parameter to see how to specify which tools the model
              can call.

          tools: An array of tools the model may call while generating a response. You can
              specify which tool to use by setting the `tool_choice` parameter.

              The two categories of tools you can provide the model are:

              - **Built-in tools**: Tools that are provided by OpenAI that extend the model's
                capabilities, like
                [web search](https://platform.openai.com/docs/guides/tools-web-search) or
                [file search](https://platform.openai.com/docs/guides/tools-file-search).
                Learn more about
                [built-in tools](https://platform.openai.com/docs/guides/tools).
              - **Function calls (custom tools)**: Functions that are defined by you, enabling
                the model to call your own code. Learn more about
                [function calling](https://platform.openai.com/docs/guides/function-calling).

          top_p: An alternative to sampling with temperature, called nucleus sampling, where the
              model considers the results of the tokens with top_p probability mass. So 0.1
              means only the tokens comprising the top 10% probability mass are considered.

              We generally recommend altering this or `temperature` but not both.

          truncation: The truncation strategy to use for the model response.

              - `auto`: If the context of this response and previous ones exceeds the model's
                context window size, the model will truncate the response to fit the context
                window by dropping input items in the middle of the conversation.
              - `disabled` (default): If a model response will exceed the context window size
                for a model, the request will fail with a 400 error.

          user: A stable identifier for your end-users. Used to boost cache hit rates by better
              bucketing similar requests and to help OpenAI detect and prevent abuse.
              [Learn more](https://platform.openai.com/docs/guides/safety-best-practices#end-user-ids).

          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request, in seconds
        """
        ...

    @overload
    async def create(
        self,
        *,
        stream: bool,
        background: Optional[bool] | NotGiven = NOT_GIVEN,
        include: Optional[List[ResponseIncludable]] | NotGiven = NOT_GIVEN,
        input: Union[str, ResponseInputParam] | NotGiven = NOT_GIVEN,
        instructions: Optional[str] | NotGiven = NOT_GIVEN,
        max_output_tokens: Optional[int] | NotGiven = NOT_GIVEN,
        metadata: Optional[Metadata] | NotGiven = NOT_GIVEN,
        model: ResponsesModel | NotGiven = NOT_GIVEN,
        parallel_tool_calls: Optional[bool] | NotGiven = NOT_GIVEN,
        previous_response_id: Optional[str] | NotGiven = NOT_GIVEN,
        prompt: Optional[ResponsePromptParam] | NotGiven = NOT_GIVEN,
        reasoning: Optional[Reasoning] | NotGiven = NOT_GIVEN,
        service_tier: Optional[Literal["auto", "default", "flex", "scale"]] | NotGiven = NOT_GIVEN,
        store: Optional[bool] | NotGiven = NOT_GIVEN,
        temperature: Optional[float] | NotGiven = NOT_GIVEN,
        text: ResponseTextConfigParam | NotGiven = NOT_GIVEN,
        tool_choice: response_create_params.ToolChoice | NotGiven = NOT_GIVEN,
        tools: Iterable[ToolParam] | NotGiven = NOT_GIVEN,
        top_p: Optional[float] | NotGiven = NOT_GIVEN,
        truncation: Optional[Literal["auto", "disabled"]] | NotGiven = NOT_GIVEN,
        user: str | NotGiven = NOT_GIVEN,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> Response | AsyncStream[ResponseStreamEvent]:
        """Creates a model response.

        Provide
        [text](https://platform.openai.com/docs/guides/text) or
        [image](https://platform.openai.com/docs/guides/images) inputs to generate
        [text](https://platform.openai.com/docs/guides/text) or
        [JSON](https://platform.openai.com/docs/guides/structured-outputs) outputs. Have
        the model call your own
        [custom code](https://platform.openai.com/docs/guides/function-calling) or use
        built-in [tools](https://platform.openai.com/docs/guides/tools) like
        [web search](https://platform.openai.com/docs/guides/tools-web-search) or
        [file search](https://platform.openai.com/docs/guides/tools-file-search) to use
        your own data as input for the model's response.

        Args:
          stream: If set to true, the model response data will be streamed to the client as it is
              generated using
              [server-sent events](https://developer.mozilla.org/en-US/docs/Web/API/Server-sent_events/Using_server-sent_events#Event_stream_format).
              See the
              [Streaming section below](https://platform.openai.com/docs/api-reference/responses-streaming)
              for more information.

          background: Whether to run the model response in the background.
              [Learn more](https://platform.openai.com/docs/guides/background).

          include: Specify additional output data to include in the model response. Currently
              supported values are:

              - `file_search_call.results`: Include the search results of the file search tool
                call.
              - `message.input_image.image_url`: Include image urls from the input message.
              - `computer_call_output.output.image_url`: Include image urls from the computer
                call output.
              - `reasoning.encrypted_content`: Includes an encrypted version of reasoning
                tokens in reasoning item outputs. This enables reasoning items to be used in
                multi-turn conversations when using the Responses API statelessly (like when
                the `store` parameter is set to `false`, or when an organization is enrolled
                in the zero data retention program).
              - `code_interpreter_call.outputs`: Includes the outputs of python code execution
                in code interpreter tool call items.

          input: Text, image, or file inputs to the model, used to generate a response.

              Learn more:

              - [Text inputs and outputs](https://platform.openai.com/docs/guides/text)
              - [Image inputs](https://platform.openai.com/docs/guides/images)
              - [File inputs](https://platform.openai.com/docs/guides/pdf-files)
              - [Conversation state](https://platform.openai.com/docs/guides/conversation-state)
              - [Function calling](https://platform.openai.com/docs/guides/function-calling)

          instructions: A system (or developer) message inserted into the model's context.

              When using along with `previous_response_id`, the instructions from a previous
              response will not be carried over to the next response. This makes it simple to
              swap out system (or developer) messages in new responses.

          max_output_tokens: An upper bound for the number of tokens that can be generated for a response,
              including visible output tokens and
              [reasoning tokens](https://platform.openai.com/docs/guides/reasoning).

          metadata: Set of 16 key-value pairs that can be attached to an object. This can be useful
              for storing additional information about the object in a structured format, and
              querying for objects via API or the dashboard.

              Keys are strings with a maximum length of 64 characters. Values are strings with
              a maximum length of 512 characters.

          model: Model ID used to generate the response, like `gpt-4o` or `o3`. OpenAI offers a
              wide range of models with different capabilities, performance characteristics,
              and price points. Refer to the
              [model guide](https://platform.openai.com/docs/models) to browse and compare
              available models.

          parallel_tool_calls: Whether to allow the model to run tool calls in parallel.

          previous_response_id: The unique ID of the previous response to the model. Use this to create
              multi-turn conversations. Learn more about
              [conversation state](https://platform.openai.com/docs/guides/conversation-state).

          prompt: Reference to a prompt template and its variables.
              [Learn more](https://platform.openai.com/docs/guides/text?api-mode=responses#reusable-prompts).

          reasoning: **o-series models only**

              Configuration options for
              [reasoning models](https://platform.openai.com/docs/guides/reasoning).

          service_tier: Specifies the latency tier to use for processing the request. This parameter is
              relevant for customers subscribed to the scale tier service:

              - If set to 'auto', and the Project is Scale tier enabled, the system will
                utilize scale tier credits until they are exhausted.
              - If set to 'auto', and the Project is not Scale tier enabled, the request will
                be processed using the default service tier with a lower uptime SLA and no
                latency guarantee.
              - If set to 'default', the request will be processed using the default service
                tier with a lower uptime SLA and no latency guarantee.
              - If set to 'flex', the request will be processed with the Flex Processing
                service tier.
                [Learn more](https://platform.openai.com/docs/guides/flex-processing).
              - When not set, the default behavior is 'auto'.

              When this parameter is set, the response body will include the `service_tier`
              utilized.

          store: Whether to store the generated model response for later retrieval via API.

          temperature: What sampling temperature to use, between 0 and 2. Higher values like 0.8 will
              make the output more random, while lower values like 0.2 will make it more
              focused and deterministic. We generally recommend altering this or `top_p` but
              not both.

          text: Configuration options for a text response from the model. Can be plain text or
              structured JSON data. Learn more:

              - [Text inputs and outputs](https://platform.openai.com/docs/guides/text)
              - [Structured Outputs](https://platform.openai.com/docs/guides/structured-outputs)

          tool_choice: How the model should select which tool (or tools) to use when generating a
              response. See the `tools` parameter to see how to specify which tools the model
              can call.

          tools: An array of tools the model may call while generating a response. You can
              specify which tool to use by setting the `tool_choice` parameter.

              The two categories of tools you can provide the model are:

              - **Built-in tools**: Tools that are provided by OpenAI that extend the model's
                capabilities, like
                [web search](https://platform.openai.com/docs/guides/tools-web-search) or
                [file search](https://platform.openai.com/docs/guides/tools-file-search).
                Learn more about
                [built-in tools](https://platform.openai.com/docs/guides/tools).
              - **Function calls (custom tools)**: Functions that are defined by you, enabling
                the model to call your own code. Learn more about
                [function calling](https://platform.openai.com/docs/guides/function-calling).

          top_p: An alternative to sampling with temperature, called nucleus sampling, where the
              model considers the results of the tokens with top_p probability mass. So 0.1
              means only the tokens comprising the top 10% probability mass are considered.

              We generally recommend altering this or `temperature` but not both.

          truncation: The truncation strategy to use for the model response.

              - `auto`: If the context of this response and previous ones exceeds the model's
                context window size, the model will truncate the response to fit the context
                window by dropping input items in the middle of the conversation.
              - `disabled` (default): If a model response will exceed the context window size
                for a model, the request will fail with a 400 error.

          user: A stable identifier for your end-users. Used to boost cache hit rates by better
              bucketing similar requests and to help OpenAI detect and prevent abuse.
              [Learn more](https://platform.openai.com/docs/guides/safety-best-practices#end-user-ids).

          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request, in seconds
        """
        ...

    async def create(
        self,
        *,
        background: Optional[bool] | NotGiven = NOT_GIVEN,
        include: Optional[List[ResponseIncludable]] | NotGiven = NOT_GIVEN,
        input: Union[str, ResponseInputParam] | NotGiven = NOT_GIVEN,
        instructions: Optional[str] | NotGiven = NOT_GIVEN,
        max_output_tokens: Optional[int] | NotGiven = NOT_GIVEN,
        metadata: Optional[Metadata] | NotGiven = NOT_GIVEN,
        model: ResponsesModel | NotGiven = NOT_GIVEN,
        parallel_tool_calls: Optional[bool] | NotGiven = NOT_GIVEN,
        previous_response_id: Optional[str] | NotGiven = NOT_GIVEN,
        prompt: Optional[ResponsePromptParam] | NotGiven = NOT_GIVEN,
        reasoning: Optional[Reasoning] | NotGiven = NOT_GIVEN,
        service_tier: Optional[Literal["auto", "default", "flex", "scale"]] | NotGiven = NOT_GIVEN,
        store: Optional[bool] | NotGiven = NOT_GIVEN,
        stream: Optional[Literal[False]] | Literal[True] | NotGiven = NOT_GIVEN,
        temperature: Optional[float] | NotGiven = NOT_GIVEN,
        text: ResponseTextConfigParam | NotGiven = NOT_GIVEN,
        tool_choice: response_create_params.ToolChoice | NotGiven = NOT_GIVEN,
        tools: Iterable[ToolParam] | NotGiven = NOT_GIVEN,
        top_p: Optional[float] | NotGiven = NOT_GIVEN,
        truncation: Optional[Literal["auto", "disabled"]] | NotGiven = NOT_GIVEN,
        user: str | NotGiven = NOT_GIVEN,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> Response | AsyncStream[ResponseStreamEvent]:
        return await self._post(
            "/responses",
            body=await async_maybe_transform(
                {
                    "background": background,
                    "include": include,
                    "input": input,
                    "instructions": instructions,
                    "max_output_tokens": max_output_tokens,
                    "metadata": metadata,
                    "model": model,
                    "parallel_tool_calls": parallel_tool_calls,
                    "previous_response_id": previous_response_id,
                    "prompt": prompt,
                    "reasoning": reasoning,
                    "service_tier": service_tier,
                    "store": store,
                    "stream": stream,
                    "temperature": temperature,
                    "text": text,
                    "tool_choice": tool_choice,
                    "tools": tools,
                    "top_p": top_p,
                    "truncation": truncation,
                    "user": user,
                },
                response_create_params.ResponseCreateParamsStreaming
                if stream
                else response_create_params.ResponseCreateParamsNonStreaming,
            ),
            options=make_request_options(
                extra_headers=extra_headers, extra_query=extra_query, extra_body=extra_body, timeout=timeout
            ),
            cast_to=Response,
            stream=stream or False,
            stream_cls=AsyncStream[ResponseStreamEvent],
        )

    @overload
    def stream(
        self,
        *,
        response_id: str,
        text_format: type[TextFormatT] | NotGiven = NOT_GIVEN,
        starting_after: int | NotGiven = NOT_GIVEN,
        tools: Iterable[ParseableToolParam] | NotGiven = NOT_GIVEN,
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> AsyncResponseStreamManager[TextFormatT]: ...

    @overload
    def stream(
        self,
        *,
        input: Union[str, ResponseInputParam],
        model: Union[str, ChatModel],
        background: Optional[bool] | NotGiven = NOT_GIVEN,
        text_format: type[TextFormatT] | NotGiven = NOT_GIVEN,
        tools: Iterable[ParseableToolParam] | NotGiven = NOT_GIVEN,
        include: Optional[List[ResponseIncludable]] | NotGiven = NOT_GIVEN,
        instructions: Optional[str] | NotGiven = NOT_GIVEN,
        max_output_tokens: Optional[int] | NotGiven = NOT_GIVEN,
        metadata: Optional[Metadata] | NotGiven = NOT_GIVEN,
        parallel_tool_calls: Optional[bool] | NotGiven = NOT_GIVEN,
        previous_response_id: Optional[str] | NotGiven = NOT_GIVEN,
        reasoning: Optional[Reasoning] | NotGiven = NOT_GIVEN,
        store: Optional[bool] | NotGiven = NOT_GIVEN,
        temperature: Optional[float] | NotGiven = NOT_GIVEN,
        text: ResponseTextConfigParam | NotGiven = NOT_GIVEN,
        tool_choice: response_create_params.ToolChoice | NotGiven = NOT_GIVEN,
        top_p: Optional[float] | NotGiven = NOT_GIVEN,
        truncation: Optional[Literal["auto", "disabled"]] | NotGiven = NOT_GIVEN,
        user: str | NotGiven = NOT_GIVEN,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> AsyncResponseStreamManager[TextFormatT]: ...

    def stream(
        self,
        *,
        response_id: str | NotGiven = NOT_GIVEN,
        input: Union[str, ResponseInputParam] | NotGiven = NOT_GIVEN,
        model: Union[str, ChatModel] | NotGiven = NOT_GIVEN,
        background: Optional[bool] | NotGiven = NOT_GIVEN,
        text_format: type[TextFormatT] | NotGiven = NOT_GIVEN,
        tools: Iterable[ParseableToolParam] | NotGiven = NOT_GIVEN,
        include: Optional[List[ResponseIncludable]] | NotGiven = NOT_GIVEN,
        instructions: Optional[str] | NotGiven = NOT_GIVEN,
        max_output_tokens: Optional[int] | NotGiven = NOT_GIVEN,
        metadata: Optional[Metadata] | NotGiven = NOT_GIVEN,
        parallel_tool_calls: Optional[bool] | NotGiven = NOT_GIVEN,
        previous_response_id: Optional[str] | NotGiven = NOT_GIVEN,
        reasoning: Optional[Reasoning] | NotGiven = NOT_GIVEN,
        store: Optional[bool] | NotGiven = NOT_GIVEN,
        temperature: Optional[float] | NotGiven = NOT_GIVEN,
        text: ResponseTextConfigParam | NotGiven = NOT_GIVEN,
        tool_choice: response_create_params.ToolChoice | NotGiven = NOT_GIVEN,
        top_p: Optional[float] | NotGiven = NOT_GIVEN,
        truncation: Optional[Literal["auto", "disabled"]] | NotGiven = NOT_GIVEN,
        user: str | NotGiven = NOT_GIVEN,
        starting_after: int | NotGiven = NOT_GIVEN,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> AsyncResponseStreamManager[TextFormatT]:
        new_response_args = {
            "input": input,
            "model": model,
            "include": include,
            "instructions": instructions,
            "max_output_tokens": max_output_tokens,
            "metadata": metadata,
            "parallel_tool_calls": parallel_tool_calls,
            "previous_response_id": previous_response_id,
            "reasoning": reasoning,
            "store": store,
            "temperature": temperature,
            "text": text,
            "tool_choice": tool_choice,
            "top_p": top_p,
            "truncation": truncation,
            "user": user,
            "background": background,
        }
        new_response_args_names = [k for k, v in new_response_args.items() if is_given(v)]

        if (is_given(response_id) or is_given(starting_after)) and len(new_response_args_names) > 0:
            raise ValueError(
                "Cannot provide both response_id/starting_after can't be provided together with "
                + ", ".join(new_response_args_names)
            )

        tools = _make_tools(tools)
        if len(new_response_args_names) > 0:
            if isinstance(input, NotGiven):
                raise ValueError("input must be provided when creating a new response")

            if not is_given(model):
                raise ValueError("model must be provided when creating a new response")

            if is_given(text_format):
                if not text:
                    text = {}

                if "format" in text:
                    raise TypeError("Cannot mix and match text.format with text_format")

                text["format"] = _type_to_text_format_param(text_format)

            api_request = self.create(
                input=input,
                model=model,
                stream=True,
                tools=tools,
                include=include,
                instructions=instructions,
                max_output_tokens=max_output_tokens,
                metadata=metadata,
                parallel_tool_calls=parallel_tool_calls,
                previous_response_id=previous_response_id,
                store=store,
                temperature=temperature,
                text=text,
                tool_choice=tool_choice,
                reasoning=reasoning,
                top_p=top_p,
                truncation=truncation,
                user=user,
                extra_headers=extra_headers,
                extra_query=extra_query,
                extra_body=extra_body,
                timeout=timeout,
            )

            return AsyncResponseStreamManager(
                api_request,
                text_format=text_format,
                input_tools=tools,
                starting_after=None,
            )
        else:
            if isinstance(response_id, NotGiven):
                raise ValueError("response_id must be provided when streaming an existing response")

            api_request = self.retrieve(
                response_id,
                stream=True,
                include=include or [],
                extra_headers=extra_headers,
                extra_query=extra_query,
                extra_body=extra_body,
                timeout=timeout,
            )
            return AsyncResponseStreamManager(
                api_request,
                text_format=text_format,
                input_tools=tools,
                starting_after=starting_after if is_given(starting_after) else None,
            )

    async def parse(
        self,
        *,
        input: Union[str, ResponseInputParam],
        model: Union[str, ChatModel],
        text_format: type[TextFormatT] | NotGiven = NOT_GIVEN,
        tools: Iterable[ParseableToolParam] | NotGiven = NOT_GIVEN,
        include: Optional[List[ResponseIncludable]] | NotGiven = NOT_GIVEN,
        instructions: Optional[str] | NotGiven = NOT_GIVEN,
        max_output_tokens: Optional[int] | NotGiven = NOT_GIVEN,
        metadata: Optional[Metadata] | NotGiven = NOT_GIVEN,
        parallel_tool_calls: Optional[bool] | NotGiven = NOT_GIVEN,
        previous_response_id: Optional[str] | NotGiven = NOT_GIVEN,
        reasoning: Optional[Reasoning] | NotGiven = NOT_GIVEN,
        store: Optional[bool] | NotGiven = NOT_GIVEN,
        stream: Optional[Literal[False]] | Literal[True] | NotGiven = NOT_GIVEN,
        temperature: Optional[float] | NotGiven = NOT_GIVEN,
        text: ResponseTextConfigParam | NotGiven = NOT_GIVEN,
        tool_choice: response_create_params.ToolChoice | NotGiven = NOT_GIVEN,
        top_p: Optional[float] | NotGiven = NOT_GIVEN,
        truncation: Optional[Literal["auto", "disabled"]] | NotGiven = NOT_GIVEN,
        user: str | NotGiven = NOT_GIVEN,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> ParsedResponse[TextFormatT]:
        if is_given(text_format):
            if not text:
                text = {}

            if "format" in text:
                raise TypeError("Cannot mix and match text.format with text_format")

            text["format"] = _type_to_text_format_param(text_format)

        tools = _make_tools(tools)

        def parser(raw_response: Response) -> ParsedResponse[TextFormatT]:
            return parse_response(
                input_tools=tools,
                text_format=text_format,
                response=raw_response,
            )

        return await self._post(
            "/responses",
            body=maybe_transform(
                {
                    "input": input,
                    "model": model,
                    "include": include,
                    "instructions": instructions,
                    "max_output_tokens": max_output_tokens,
                    "metadata": metadata,
                    "parallel_tool_calls": parallel_tool_calls,
                    "previous_response_id": previous_response_id,
                    "reasoning": reasoning,
                    "store": store,
                    "stream": stream,
                    "temperature": temperature,
                    "text": text,
                    "tool_choice": tool_choice,
                    "tools": tools,
                    "top_p": top_p,
                    "truncation": truncation,
                    "user": user,
                },
                response_create_params.ResponseCreateParams,
            ),
            options=make_request_options(
                extra_headers=extra_headers,
                extra_query=extra_query,
                extra_body=extra_body,
                timeout=timeout,
                post_parser=parser,
            ),
            # we turn the `Response` instance into a `ParsedResponse`
            # in the `parser` function above
            cast_to=cast(Type[ParsedResponse[TextFormatT]], Response),
        )

    @overload
    async def retrieve(
        self,
        response_id: str,
        *,
        include: List[ResponseIncludable] | NotGiven = NOT_GIVEN,
        starting_after: int | NotGiven = NOT_GIVEN,
        stream: Literal[False] | NotGiven = NOT_GIVEN,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> Response: ...

    @overload
    async def retrieve(
        self,
        response_id: str,
        *,
        stream: Literal[True],
        include: List[ResponseIncludable] | NotGiven = NOT_GIVEN,
        starting_after: int | NotGiven = NOT_GIVEN,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> AsyncStream[ResponseStreamEvent]: ...

    @overload
    async def retrieve(
        self,
        response_id: str,
        *,
        stream: bool,
        include: List[ResponseIncludable] | NotGiven = NOT_GIVEN,
        starting_after: int | NotGiven = NOT_GIVEN,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> Response | AsyncStream[ResponseStreamEvent]: ...

    @overload
    async def retrieve(
        self,
        response_id: str,
        *,
        stream: bool = False,
        include: List[ResponseIncludable] | NotGiven = NOT_GIVEN,
        starting_after: int | NotGiven = NOT_GIVEN,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> Response | AsyncStream[ResponseStreamEvent]:
        """
        Retrieves a model response with the given ID.

        Args:
          include: Additional fields to include in the response. See the `include` parameter for
              Response creation above for more information.

          starting_after: The sequence number of the event after which to start streaming.

          stream: If set to true, the model response data will be streamed to the client as it is
              generated using
              [server-sent events](https://developer.mozilla.org/en-US/docs/Web/API/Server-sent_events/Using_server-sent_events#Event_stream_format).
              See the
              [Streaming section below](https://platform.openai.com/docs/api-reference/responses-streaming)
              for more information.

          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request, in seconds
        """
        ...

    @overload
    async def retrieve(
        self,
        response_id: str,
        *,
        stream: Literal[True],
        include: List[ResponseIncludable] | NotGiven = NOT_GIVEN,
        starting_after: int | NotGiven = NOT_GIVEN,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> AsyncStream[ResponseStreamEvent]:
        """
        Retrieves a model response with the given ID.

        Args:
          stream: If set to true, the model response data will be streamed to the client as it is
              generated using
              [server-sent events](https://developer.mozilla.org/en-US/docs/Web/API/Server-sent_events/Using_server-sent_events#Event_stream_format).
              See the
              [Streaming section below](https://platform.openai.com/docs/api-reference/responses-streaming)
              for more information.

          include: Additional fields to include in the response. See the `include` parameter for
              Response creation above for more information.

          starting_after: The sequence number of the event after which to start streaming.

          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request, in seconds
        """
        ...

    @overload
    async def retrieve(
        self,
        response_id: str,
        *,
        stream: bool,
        include: List[ResponseIncludable] | NotGiven = NOT_GIVEN,
        starting_after: int | NotGiven = NOT_GIVEN,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> Response | AsyncStream[ResponseStreamEvent]:
        """
        Retrieves a model response with the given ID.

        Args:
          stream: If set to true, the model response data will be streamed to the client as it is
              generated using
              [server-sent events](https://developer.mozilla.org/en-US/docs/Web/API/Server-sent_events/Using_server-sent_events#Event_stream_format).
              See the
              [Streaming section below](https://platform.openai.com/docs/api-reference/responses-streaming)
              for more information.

          include: Additional fields to include in the response. See the `include` parameter for
              Response creation above for more information.

          starting_after: The sequence number of the event after which to start streaming.

          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request, in seconds
        """
        ...

    async def retrieve(
        self,
        response_id: str,
        *,
        include: List[ResponseIncludable] | NotGiven = NOT_GIVEN,
        starting_after: int | NotGiven = NOT_GIVEN,
        stream: Literal[False] | Literal[True] | NotGiven = NOT_GIVEN,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> Response | AsyncStream[ResponseStreamEvent]:
        if not response_id:
            raise ValueError(f"Expected a non-empty value for `response_id` but received {response_id!r}")
        return await self._get(
            f"/responses/{response_id}",
            options=make_request_options(
                extra_headers=extra_headers,
                extra_query=extra_query,
                extra_body=extra_body,
                timeout=timeout,
                query=await async_maybe_transform(
                    {
                        "include": include,
                        "starting_after": starting_after,
                        "stream": stream,
                    },
                    response_retrieve_params.ResponseRetrieveParams,
                ),
            ),
            cast_to=Response,
            stream=stream or False,
            stream_cls=AsyncStream[ResponseStreamEvent],
        )

    async def delete(
        self,
        response_id: str,
        *,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> None:
        """
        Deletes a model response with the given ID.

        Args:
          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request, in seconds
        """
        if not response_id:
            raise ValueError(f"Expected a non-empty value for `response_id` but received {response_id!r}")
        extra_headers = {"Accept": "*/*", **(extra_headers or {})}
        return await self._delete(
            f"/responses/{response_id}",
            options=make_request_options(
                extra_headers=extra_headers, extra_query=extra_query, extra_body=extra_body, timeout=timeout
            ),
            cast_to=NoneType,
        )

    async def cancel(
        self,
        response_id: str,
        *,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> Response:
        """Cancels a model response with the given ID.

        Only responses created with the
        `background` parameter set to `true` can be cancelled.
        [Learn more](https://platform.openai.com/docs/guides/background).

        Args:
          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request, in seconds
        """
        if not response_id:
            raise ValueError(f"Expected a non-empty value for `response_id` but received {response_id!r}")
        return await self._post(
            f"/responses/{response_id}/cancel",
            options=make_request_options(
                extra_headers=extra_headers, extra_query=extra_query, extra_body=extra_body, timeout=timeout
            ),
            cast_to=Response,
        )


class ResponsesWithRawResponse:
    def __init__(self, responses: Responses) -> None:
        self._responses = responses

        self.create = _legacy_response.to_raw_response_wrapper(
            responses.create,
        )
        self.retrieve = _legacy_response.to_raw_response_wrapper(
            responses.retrieve,
        )
        self.delete = _legacy_response.to_raw_response_wrapper(
            responses.delete,
        )
        self.cancel = _legacy_response.to_raw_response_wrapper(
            responses.cancel,
        )
        self.parse = _legacy_response.to_raw_response_wrapper(
            responses.parse,
        )

    @cached_property
    def input_items(self) -> InputItemsWithRawResponse:
        return InputItemsWithRawResponse(self._responses.input_items)


class AsyncResponsesWithRawResponse:
    def __init__(self, responses: AsyncResponses) -> None:
        self._responses = responses

        self.create = _legacy_response.async_to_raw_response_wrapper(
            responses.create,
        )
        self.retrieve = _legacy_response.async_to_raw_response_wrapper(
            responses.retrieve,
        )
        self.delete = _legacy_response.async_to_raw_response_wrapper(
            responses.delete,
        )
        self.cancel = _legacy_response.async_to_raw_response_wrapper(
            responses.cancel,
        )
        self.parse = _legacy_response.async_to_raw_response_wrapper(
            responses.parse,
        )

    @cached_property
    def input_items(self) -> AsyncInputItemsWithRawResponse:
        return AsyncInputItemsWithRawResponse(self._responses.input_items)


class ResponsesWithStreamingResponse:
    def __init__(self, responses: Responses) -> None:
        self._responses = responses

        self.create = to_streamed_response_wrapper(
            responses.create,
        )
        self.retrieve = to_streamed_response_wrapper(
            responses.retrieve,
        )
        self.delete = to_streamed_response_wrapper(
            responses.delete,
        )
        self.cancel = to_streamed_response_wrapper(
            responses.cancel,
        )

    @cached_property
    def input_items(self) -> InputItemsWithStreamingResponse:
        return InputItemsWithStreamingResponse(self._responses.input_items)


class AsyncResponsesWithStreamingResponse:
    def __init__(self, responses: AsyncResponses) -> None:
        self._responses = responses

        self.create = async_to_streamed_response_wrapper(
            responses.create,
        )
        self.retrieve = async_to_streamed_response_wrapper(
            responses.retrieve,
        )
        self.delete = async_to_streamed_response_wrapper(
            responses.delete,
        )
        self.cancel = async_to_streamed_response_wrapper(
            responses.cancel,
        )

    @cached_property
    def input_items(self) -> AsyncInputItemsWithStreamingResponse:
        return AsyncInputItemsWithStreamingResponse(self._responses.input_items)


def _make_tools(tools: Iterable[ParseableToolParam] | NotGiven) -> List[ToolParam] | NotGiven:
    if not is_given(tools):
        return NOT_GIVEN

    converted_tools: List[ToolParam] = []
    for tool in tools:
        if tool["type"] != "function":
            converted_tools.append(tool)
            continue

        if "function" not in tool:
            # standard Responses API case
            converted_tools.append(tool)
            continue

        function = cast(Any, tool)["function"]  # pyright: ignore[reportUnnecessaryCast]
        if not isinstance(function, PydanticFunctionTool):
            raise Exception(
                "Expected Chat Completions function tool shape to be created using `openai.pydantic_function_tool()`"
            )

        assert "parameters" in function
        new_tool = ResponsesPydanticFunctionTool(
            {
                "type": "function",
                "name": function["name"],
                "description": function.get("description"),
                "parameters": function["parameters"],
                "strict": function.get("strict") or False,
            },
            function.model,
        )

        converted_tools.append(new_tool.cast())

    return converted_tools

# === NexusCore/openenv\Lib\site-packages\pygments\lexers\_openedge_builtins.py ===
"""
    pygments.lexers._openedge_builtins
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    Builtin list for the OpenEdgeLexer.

    :copyright: Copyright 2006-2025 by the Pygments team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

OPENEDGEKEYWORDS = (
    'ABS',
    'ABSO',
    'ABSOL',
    'ABSOLU',
    'ABSOLUT',
    'ABSOLUTE',
    'ABSTRACT',
    'ACCELERATOR',
    'ACCUM',
    'ACCUMU',
    'ACCUMUL',
    'ACCUMULA',
    'ACCUMULAT',
    'ACCUMULATE',
    'ACTIVE-FORM',
    'ACTIVE-WINDOW',
    'ADD',
    'ADD-BUFFER',
    'ADD-CALC-COLUMN',
    'ADD-COLUMNS-FROM',
    'ADD-EVENTS-PROCEDURE',
    'ADD-FIELDS-FROM',
    'ADD-FIRST',
    'ADD-INDEX-FIELD',
    'ADD-LAST',
    'ADD-LIKE-COLUMN',
    'ADD-LIKE-FIELD',
    'ADD-LIKE-INDEX',
    'ADD-NEW-FIELD',
    'ADD-NEW-INDEX',
    'ADD-SCHEMA-LOCATION',
    'ADD-SUPER-PROCEDURE',
    'ADM-DATA',
    'ADVISE',
    'ALERT-BOX',
    'ALIAS',
    'ALL',
    'ALLOW-COLUMN-SEARCHING',
    'ALLOW-REPLICATION',
    'ALTER',
    'ALWAYS-ON-TOP',
    'AMBIG',
    'AMBIGU',
    'AMBIGUO',
    'AMBIGUOU',
    'AMBIGUOUS',
    'ANALYZ',
    'ANALYZE',
    'AND',
    'ANSI-ONLY',
    'ANY',
    'ANYWHERE',
    'APPEND',
    'APPL-ALERT',
    'APPL-ALERT-',
    'APPL-ALERT-B',
    'APPL-ALERT-BO',
    'APPL-ALERT-BOX',
    'APPL-ALERT-BOXE',
    'APPL-ALERT-BOXES',
    'APPL-CONTEXT-ID',
    'APPLICATION',
    'APPLY',
    'APPSERVER-INFO',
    'APPSERVER-PASSWORD',
    'APPSERVER-USERID',
    'ARRAY-MESSAGE',
    'AS',
    'ASC',
    'ASCE',
    'ASCEN',
    'ASCEND',
    'ASCENDI',
    'ASCENDIN',
    'ASCENDING',
    'ASK-OVERWRITE',
    'ASSEMBLY',
    'ASSIGN',
    'ASYNC-REQUEST-COUNT',
    'ASYNC-REQUEST-HANDLE',
    'ASYNCHRONOUS',
    'AT',
    'ATTACHED-PAIRLIST',
    'ATTR',
    'ATTR-SPACE',
    'ATTRI',
    'ATTRIB',
    'ATTRIBU',
    'ATTRIBUT',
    'AUDIT-CONTROL',
    'AUDIT-ENABLED',
    'AUDIT-EVENT-CONTEXT',
    'AUDIT-POLICY',
    'AUTHENTICATION-FAILED',
    'AUTHORIZATION',
    'AUTO-COMP',
    'AUTO-COMPL',
    'AUTO-COMPLE',
    'AUTO-COMPLET',
    'AUTO-COMPLETI',
    'AUTO-COMPLETIO',
    'AUTO-COMPLETION',
    'AUTO-END-KEY',
    'AUTO-ENDKEY',
    'AUTO-GO',
    'AUTO-IND',
    'AUTO-INDE',
    'AUTO-INDEN',
    'AUTO-INDENT',
    'AUTO-RESIZE',
    'AUTO-RET',
    'AUTO-RETU',
    'AUTO-RETUR',
    'AUTO-RETURN',
    'AUTO-SYNCHRONIZE',
    'AUTO-Z',
    'AUTO-ZA',
    'AUTO-ZAP',
    'AUTOMATIC',
    'AVAIL',
    'AVAILA',
    'AVAILAB',
    'AVAILABL',
    'AVAILABLE',
    'AVAILABLE-FORMATS',
    'AVE',
    'AVER',
    'AVERA',
    'AVERAG',
    'AVERAGE',
    'AVG',
    'BACK',
    'BACKG',
    'BACKGR',
    'BACKGRO',
    'BACKGROU',
    'BACKGROUN',
    'BACKGROUND',
    'BACKWARD',
    'BACKWARDS',
    'BASE64-DECODE',
    'BASE64-ENCODE',
    'BASE-ADE',
    'BASE-KEY',
    'BATCH',
    'BATCH-',
    'BATCH-M',
    'BATCH-MO',
    'BATCH-MOD',
    'BATCH-MODE',
    'BATCH-SIZE',
    'BEFORE-H',
    'BEFORE-HI',
    'BEFORE-HID',
    'BEFORE-HIDE',
    'BEGIN-EVENT-GROUP',
    'BEGINS',
    'BELL',
    'BETWEEN',
    'BGC',
    'BGCO',
    'BGCOL',
    'BGCOLO',
    'BGCOLOR',
    'BIG-ENDIAN',
    'BINARY',
    'BIND',
    'BIND-WHERE',
    'BLANK',
    'BLOCK-ITERATION-DISPLAY',
    'BLOCK-LEVEL',
    'BORDER-B',
    'BORDER-BO',
    'BORDER-BOT',
    'BORDER-BOTT',
    'BORDER-BOTTO',
    'BORDER-BOTTOM-CHARS',
    'BORDER-BOTTOM-P',
    'BORDER-BOTTOM-PI',
    'BORDER-BOTTOM-PIX',
    'BORDER-BOTTOM-PIXE',
    'BORDER-BOTTOM-PIXEL',
    'BORDER-BOTTOM-PIXELS',
    'BORDER-L',
    'BORDER-LE',
    'BORDER-LEF',
    'BORDER-LEFT',
    'BORDER-LEFT-',
    'BORDER-LEFT-C',
    'BORDER-LEFT-CH',
    'BORDER-LEFT-CHA',
    'BORDER-LEFT-CHAR',
    'BORDER-LEFT-CHARS',
    'BORDER-LEFT-P',
    'BORDER-LEFT-PI',
    'BORDER-LEFT-PIX',
    'BORDER-LEFT-PIXE',
    'BORDER-LEFT-PIXEL',
    'BORDER-LEFT-PIXELS',
    'BORDER-R',
    'BORDER-RI',
    'BORDER-RIG',
    'BORDER-RIGH',
    'BORDER-RIGHT',
    'BORDER-RIGHT-',
    'BORDER-RIGHT-C',
    'BORDER-RIGHT-CH',
    'BORDER-RIGHT-CHA',
    'BORDER-RIGHT-CHAR',
    'BORDER-RIGHT-CHARS',
    'BORDER-RIGHT-P',
    'BORDER-RIGHT-PI',
    'BORDER-RIGHT-PIX',
    'BORDER-RIGHT-PIXE',
    'BORDER-RIGHT-PIXEL',
    'BORDER-RIGHT-PIXELS',
    'BORDER-T',
    'BORDER-TO',
    'BORDER-TOP',
    'BORDER-TOP-',
    'BORDER-TOP-C',
    'BORDER-TOP-CH',
    'BORDER-TOP-CHA',
    'BORDER-TOP-CHAR',
    'BORDER-TOP-CHARS',
    'BORDER-TOP-P',
    'BORDER-TOP-PI',
    'BORDER-TOP-PIX',
    'BORDER-TOP-PIXE',
    'BORDER-TOP-PIXEL',
    'BORDER-TOP-PIXELS',
    'BOX',
    'BOX-SELECT',
    'BOX-SELECTA',
    'BOX-SELECTAB',
    'BOX-SELECTABL',
    'BOX-SELECTABLE',
    'BREAK',
    'BROWSE',
    'BUFFER',
    'BUFFER-CHARS',
    'BUFFER-COMPARE',
    'BUFFER-COPY',
    'BUFFER-CREATE',
    'BUFFER-DELETE',
    'BUFFER-FIELD',
    'BUFFER-HANDLE',
    'BUFFER-LINES',
    'BUFFER-NAME',
    'BUFFER-PARTITION-ID',
    'BUFFER-RELEASE',
    'BUFFER-VALUE',
    'BUTTON',
    'BUTTONS',
    'BY',
    'BY-POINTER',
    'BY-VARIANT-POINTER',
    'CACHE',
    'CACHE-SIZE',
    'CALL',
    'CALL-NAME',
    'CALL-TYPE',
    'CAN-CREATE',
    'CAN-DELETE',
    'CAN-DO',
    'CAN-DO-DOMAIN-SUPPORT',
    'CAN-FIND',
    'CAN-QUERY',
    'CAN-READ',
    'CAN-SET',
    'CAN-WRITE',
    'CANCEL-BREAK',
    'CANCEL-BUTTON',
    'CAPS',
    'CAREFUL-PAINT',
    'CASE',
    'CASE-SEN',
    'CASE-SENS',
    'CASE-SENSI',
    'CASE-SENSIT',
    'CASE-SENSITI',
    'CASE-SENSITIV',
    'CASE-SENSITIVE',
    'CAST',
    'CATCH',
    'CDECL',
    'CENTER',
    'CENTERE',
    'CENTERED',
    'CHAINED',
    'CHARACTER',
    'CHARACTER_LENGTH',
    'CHARSET',
    'CHECK',
    'CHECKED',
    'CHOOSE',
    'CHR',
    'CLASS',
    'CLASS-TYPE',
    'CLEAR',
    'CLEAR-APPL-CONTEXT',
    'CLEAR-LOG',
    'CLEAR-SELECT',
    'CLEAR-SELECTI',
    'CLEAR-SELECTIO',
    'CLEAR-SELECTION',
    'CLEAR-SORT-ARROW',
    'CLEAR-SORT-ARROWS',
    'CLIENT-CONNECTION-ID',
    'CLIENT-PRINCIPAL',
    'CLIENT-TTY',
    'CLIENT-TYPE',
    'CLIENT-WORKSTATION',
    'CLIPBOARD',
    'CLOSE',
    'CLOSE-LOG',
    'CODE',
    'CODEBASE-LOCATOR',
    'CODEPAGE',
    'CODEPAGE-CONVERT',
    'COL',
    'COL-OF',
    'COLLATE',
    'COLON',
    'COLON-ALIGN',
    'COLON-ALIGNE',
    'COLON-ALIGNED',
    'COLOR',
    'COLOR-TABLE',
    'COLU',
    'COLUM',
    'COLUMN',
    'COLUMN-BGCOLOR',
    'COLUMN-DCOLOR',
    'COLUMN-FGCOLOR',
    'COLUMN-FONT',
    'COLUMN-LAB',
    'COLUMN-LABE',
    'COLUMN-LABEL',
    'COLUMN-MOVABLE',
    'COLUMN-OF',
    'COLUMN-PFCOLOR',
    'COLUMN-READ-ONLY',
    'COLUMN-RESIZABLE',
    'COLUMN-SCROLLING',
    'COLUMNS',
    'COM-HANDLE',
    'COM-SELF',
    'COMBO-BOX',
    'COMMAND',
    'COMPARES',
    'COMPILE',
    'COMPILER',
    'COMPLETE',
    'CONFIG-NAME',
    'CONNECT',
    'CONNECTED',
    'CONSTRUCTOR',
    'CONTAINS',
    'CONTENTS',
    'CONTEXT',
    'CONTEXT-HELP',
    'CONTEXT-HELP-FILE',
    'CONTEXT-HELP-ID',
    'CONTEXT-POPUP',
    'CONTROL',
    'CONTROL-BOX',
    'CONTROL-FRAME',
    'CONVERT',
    'CONVERT-3D-COLORS',
    'CONVERT-TO-OFFS',
    'CONVERT-TO-OFFSE',
    'CONVERT-TO-OFFSET',
    'COPY-DATASET',
    'COPY-LOB',
    'COPY-SAX-ATTRIBUTES',
    'COPY-TEMP-TABLE',
    'COUNT',
    'COUNT-OF',
    'CPCASE',
    'CPCOLL',
    'CPINTERNAL',
    'CPLOG',
    'CPPRINT',
    'CPRCODEIN',
    'CPRCODEOUT',
    'CPSTREAM',
    'CPTERM',
    'CRC-VALUE',
    'CREATE',
    'CREATE-LIKE',
    'CREATE-LIKE-SEQUENTIAL',
    'CREATE-NODE-NAMESPACE',
    'CREATE-RESULT-LIST-ENTRY',
    'CREATE-TEST-FILE',
    'CURRENT',
    'CURRENT-CHANGED',
    'CURRENT-COLUMN',
    'CURRENT-ENV',
    'CURRENT-ENVI',
    'CURRENT-ENVIR',
    'CURRENT-ENVIRO',
    'CURRENT-ENVIRON',
    'CURRENT-ENVIRONM',
    'CURRENT-ENVIRONME',
    'CURRENT-ENVIRONMEN',
    'CURRENT-ENVIRONMENT',
    'CURRENT-ITERATION',
    'CURRENT-LANG',
    'CURRENT-LANGU',
    'CURRENT-LANGUA',
    'CURRENT-LANGUAG',
    'CURRENT-LANGUAGE',
    'CURRENT-QUERY',
    'CURRENT-REQUEST-INFO',
    'CURRENT-RESPONSE-INFO',
    'CURRENT-RESULT-ROW',
    'CURRENT-ROW-MODIFIED',
    'CURRENT-VALUE',
    'CURRENT-WINDOW',
    'CURRENT_DATE',
    'CURS',
    'CURSO',
    'CURSOR',
    'CURSOR-CHAR',
    'CURSOR-LINE',
    'CURSOR-OFFSET',
    'DATA-BIND',
    'DATA-ENTRY-RET',
    'DATA-ENTRY-RETU',
    'DATA-ENTRY-RETUR',
    'DATA-ENTRY-RETURN',
    'DATA-REL',
    'DATA-RELA',
    'DATA-RELAT',
    'DATA-RELATI',
    'DATA-RELATIO',
    'DATA-RELATION',
    'DATA-SOURCE',
    'DATA-SOURCE-COMPLETE-MAP',
    'DATA-SOURCE-MODIFIED',
    'DATA-SOURCE-ROWID',
    'DATA-T',
    'DATA-TY',
    'DATA-TYP',
    'DATA-TYPE',
    'DATABASE',
    'DATASERVERS',
    'DATASET',
    'DATASET-HANDLE',
    'DATE',
    'DATE-F',
    'DATE-FO',
    'DATE-FOR',
    'DATE-FORM',
    'DATE-FORMA',
    'DATE-FORMAT',
    'DAY',
    'DB-CONTEXT',
    'DB-REFERENCES',
    'DBCODEPAGE',
    'DBCOLLATION',
    'DBNAME',
    'DBPARAM',
    'DBREST',
    'DBRESTR',
    'DBRESTRI',
    'DBRESTRIC',
    'DBRESTRICT',
    'DBRESTRICTI',
    'DBRESTRICTIO',
    'DBRESTRICTION',
    'DBRESTRICTIONS',
    'DBTASKID',
    'DBTYPE',
    'DBVERS',
    'DBVERSI',
    'DBVERSIO',
    'DBVERSION',
    'DCOLOR',
    'DDE',
    'DDE-ERROR',
    'DDE-I',
    'DDE-ID',
    'DDE-ITEM',
    'DDE-NAME',
    'DDE-TOPIC',
    'DEBLANK',
    'DEBU',
    'DEBUG',
    'DEBUG-ALERT',
    'DEBUG-LIST',
    'DEBUGGER',
    'DECIMAL',
    'DECIMALS',
    'DECLARE',
    'DECLARE-NAMESPACE',
    'DECRYPT',
    'DEFAULT',
    'DEFAULT-B',
    'DEFAULT-BU',
    'DEFAULT-BUFFER-HANDLE',
    'DEFAULT-BUT',
    'DEFAULT-BUTT',
    'DEFAULT-BUTTO',
    'DEFAULT-BUTTON',
    'DEFAULT-COMMIT',
    'DEFAULT-EX',
    'DEFAULT-EXT',
    'DEFAULT-EXTE',
    'DEFAULT-EXTEN',
    'DEFAULT-EXTENS',
    'DEFAULT-EXTENSI',
    'DEFAULT-EXTENSIO',
    'DEFAULT-EXTENSION',
    'DEFAULT-NOXL',
    'DEFAULT-NOXLA',
    'DEFAULT-NOXLAT',
    'DEFAULT-NOXLATE',
    'DEFAULT-VALUE',
    'DEFAULT-WINDOW',
    'DEFINE',
    'DEFINE-USER-EVENT-MANAGER',
    'DEFINED',
    'DEL',
    'DELE',
    'DELEGATE',
    'DELET',
    'DELETE PROCEDURE',
    'DELETE',
    'DELETE-CHAR',
    'DELETE-CHARA',
    'DELETE-CHARAC',
    'DELETE-CHARACT',
    'DELETE-CHARACTE',
    'DELETE-CHARACTER',
    'DELETE-CURRENT-ROW',
    'DELETE-LINE',
    'DELETE-RESULT-LIST-ENTRY',
    'DELETE-SELECTED-ROW',
    'DELETE-SELECTED-ROWS',
    'DELIMITER',
    'DESC',
    'DESCE',
    'DESCEN',
    'DESCEND',
    'DESCENDI',
    'DESCENDIN',
    'DESCENDING',
    'DESELECT-FOCUSED-ROW',
    'DESELECT-ROWS',
    'DESELECT-SELECTED-ROW',
    'DESELECTION',
    'DESTRUCTOR',
    'DIALOG-BOX',
    'DICT',
    'DICTI',
    'DICTIO',
    'DICTION',
    'DICTIONA',
    'DICTIONAR',
    'DICTIONARY',
    'DIR',
    'DISABLE',
    'DISABLE-AUTO-ZAP',
    'DISABLE-DUMP-TRIGGERS',
    'DISABLE-LOAD-TRIGGERS',
    'DISABLED',
    'DISCON',
    'DISCONN',
    'DISCONNE',
    'DISCONNEC',
    'DISCONNECT',
    'DISP',
    'DISPL',
    'DISPLA',
    'DISPLAY',
    'DISPLAY-MESSAGE',
    'DISPLAY-T',
    'DISPLAY-TY',
    'DISPLAY-TYP',
    'DISPLAY-TYPE',
    'DISTINCT',
    'DO',
    'DOMAIN-DESCRIPTION',
    'DOMAIN-NAME',
    'DOMAIN-TYPE',
    'DOS',
    'DOUBLE',
    'DOWN',
    'DRAG-ENABLED',
    'DROP',
    'DROP-DOWN',
    'DROP-DOWN-LIST',
    'DROP-FILE-NOTIFY',
    'DROP-TARGET',
    'DS-CLOSE-CURSOR',
    'DSLOG-MANAGER',
    'DUMP',
    'DYNAMIC',
    'DYNAMIC-ENUM',
    'DYNAMIC-FUNCTION',
    'DYNAMIC-INVOKE',
    'EACH',
    'ECHO',
    'EDGE',
    'EDGE-',
    'EDGE-C',
    'EDGE-CH',
    'EDGE-CHA',
    'EDGE-CHAR',
    'EDGE-CHARS',
    'EDGE-P',
    'EDGE-PI',
    'EDGE-PIX',
    'EDGE-PIXE',
    'EDGE-PIXEL',
    'EDGE-PIXELS',
    'EDIT-CAN-PASTE',
    'EDIT-CAN-UNDO',
    'EDIT-CLEAR',
    'EDIT-COPY',
    'EDIT-CUT',
    'EDIT-PASTE',
    'EDIT-UNDO',
    'EDITING',
    'EDITOR',
    'ELSE',
    'EMPTY',
    'EMPTY-TEMP-TABLE',
    'ENABLE',
    'ENABLED-FIELDS',
    'ENCODE',
    'ENCRYPT',
    'ENCRYPT-AUDIT-MAC-KEY',
    'ENCRYPTION-SALT',
    'END',
    'END-DOCUMENT',
    'END-ELEMENT',
    'END-EVENT-GROUP',
    'END-FILE-DROP',
    'END-KEY',
    'END-MOVE',
    'END-RESIZE',
    'END-ROW-RESIZE',
    'END-USER-PROMPT',
    'ENDKEY',
    'ENTERED',
    'ENTITY-EXPANSION-LIMIT',
    'ENTRY',
    'ENUM',
    'EQ',
    'ERROR',
    'ERROR-COL',
    'ERROR-COLU',
    'ERROR-COLUM',
    'ERROR-COLUMN',
    'ERROR-ROW',
    'ERROR-STACK-TRACE',
    'ERROR-STAT',
    'ERROR-STATU',
    'ERROR-STATUS',
    'ESCAPE',
    'ETIME',
    'EVENT',
    'EVENT-GROUP-ID',
    'EVENT-PROCEDURE',
    'EVENT-PROCEDURE-CONTEXT',
    'EVENT-T',
    'EVENT-TY',
    'EVENT-TYP',
    'EVENT-TYPE',
    'EVENTS',
    'EXCEPT',
    'EXCLUSIVE',
    'EXCLUSIVE-',
    'EXCLUSIVE-ID',
    'EXCLUSIVE-L',
    'EXCLUSIVE-LO',
    'EXCLUSIVE-LOC',
    'EXCLUSIVE-LOCK',
    'EXCLUSIVE-WEB-USER',
    'EXECUTE',
    'EXISTS',
    'EXP',
    'EXPAND',
    'EXPANDABLE',
    'EXPLICIT',
    'EXPORT',
    'EXPORT-PRINCIPAL',
    'EXTENDED',
    'EXTENT',
    'EXTERNAL',
    'FALSE',
    'FETCH',
    'FETCH-SELECTED-ROW',
    'FGC',
    'FGCO',
    'FGCOL',
    'FGCOLO',
    'FGCOLOR',
    'FIELD',
    'FIELDS',
    'FILE',
    'FILE-CREATE-DATE',
    'FILE-CREATE-TIME',
    'FILE-INFO',
    'FILE-INFOR',
    'FILE-INFORM',
    'FILE-INFORMA',
    'FILE-INFORMAT',
    'FILE-INFORMATI',
    'FILE-INFORMATIO',
    'FILE-INFORMATION',
    'FILE-MOD-DATE',
    'FILE-MOD-TIME',
    'FILE-NAME',
    'FILE-OFF',
    'FILE-OFFS',
    'FILE-OFFSE',
    'FILE-OFFSET',
    'FILE-SIZE',
    'FILE-TYPE',
    'FILENAME',
    'FILL',
    'FILL-IN',
    'FILLED',
    'FILTERS',
    'FINAL',
    'FINALLY',
    'FIND',
    'FIND-BY-ROWID',
    'FIND-CASE-SENSITIVE',
    'FIND-CURRENT',
    'FIND-FIRST',
    'FIND-GLOBAL',
    'FIND-LAST',
    'FIND-NEXT-OCCURRENCE',
    'FIND-PREV-OCCURRENCE',
    'FIND-SELECT',
    'FIND-UNIQUE',
    'FIND-WRAP-AROUND',
    'FINDER',
    'FIRST',
    'FIRST-ASYNCH-REQUEST',
    'FIRST-CHILD',
    'FIRST-COLUMN',
    'FIRST-FORM',
    'FIRST-OBJECT',
    'FIRST-OF',
    'FIRST-PROC',
    'FIRST-PROCE',
    'FIRST-PROCED',
    'FIRST-PROCEDU',
    'FIRST-PROCEDUR',
    'FIRST-PROCEDURE',
    'FIRST-SERVER',
    'FIRST-TAB-I',
    'FIRST-TAB-IT',
    'FIRST-TAB-ITE',
    'FIRST-TAB-ITEM',
    'FIT-LAST-COLUMN',
    'FIXED-ONLY',
    'FLAT-BUTTON',
    'FLOAT',
    'FOCUS',
    'FOCUSED-ROW',
    'FOCUSED-ROW-SELECTED',
    'FONT',
    'FONT-TABLE',
    'FOR',
    'FORCE-FILE',
    'FORE',
    'FOREG',
    'FOREGR',
    'FOREGRO',
    'FOREGROU',
    'FOREGROUN',
    'FOREGROUND',
    'FORM INPUT',
    'FORM',
    'FORM-LONG-INPUT',
    'FORMA',
    'FORMAT',
    'FORMATTE',
    'FORMATTED',
    'FORWARD',
    'FORWARDS',
    'FRAGMEN',
    'FRAGMENT',
    'FRAM',
    'FRAME',
    'FRAME-COL',
    'FRAME-DB',
    'FRAME-DOWN',
    'FRAME-FIELD',
    'FRAME-FILE',
    'FRAME-INDE',
    'FRAME-INDEX',
    'FRAME-LINE',
    'FRAME-NAME',
    'FRAME-ROW',
    'FRAME-SPA',
    'FRAME-SPAC',
    'FRAME-SPACI',
    'FRAME-SPACIN',
    'FRAME-SPACING',
    'FRAME-VAL',
    'FRAME-VALU',
    'FRAME-VALUE',
    'FRAME-X',
    'FRAME-Y',
    'FREQUENCY',
    'FROM',
    'FROM-C',
    'FROM-CH',
    'FROM-CHA',
    'FROM-CHAR',
    'FROM-CHARS',
    'FROM-CUR',
    'FROM-CURR',
    'FROM-CURRE',
    'FROM-CURREN',
    'FROM-CURRENT',
    'FROM-P',
    'FROM-PI',
    'FROM-PIX',
    'FROM-PIXE',
    'FROM-PIXEL',
    'FROM-PIXELS',
    'FULL-HEIGHT',
    'FULL-HEIGHT-',
    'FULL-HEIGHT-C',
    'FULL-HEIGHT-CH',
    'FULL-HEIGHT-CHA',
    'FULL-HEIGHT-CHAR',
    'FULL-HEIGHT-CHARS',
    'FULL-HEIGHT-P',
    'FULL-HEIGHT-PI',
    'FULL-HEIGHT-PIX',
    'FULL-HEIGHT-PIXE',
    'FULL-HEIGHT-PIXEL',
    'FULL-HEIGHT-PIXELS',
    'FULL-PATHN',
    'FULL-PATHNA',
    'FULL-PATHNAM',
    'FULL-PATHNAME',
    'FULL-WIDTH',
    'FULL-WIDTH-',
    'FULL-WIDTH-C',
    'FULL-WIDTH-CH',
    'FULL-WIDTH-CHA',
    'FULL-WIDTH-CHAR',
    'FULL-WIDTH-CHARS',
    'FULL-WIDTH-P',
    'FULL-WIDTH-PI',
    'FULL-WIDTH-PIX',
    'FULL-WIDTH-PIXE',
    'FULL-WIDTH-PIXEL',
    'FULL-WIDTH-PIXELS',
    'FUNCTION',
    'FUNCTION-CALL-TYPE',
    'GATEWAY',
    'GATEWAYS',
    'GE',
    'GENERATE-MD5',
    'GENERATE-PBE-KEY',
    'GENERATE-PBE-SALT',
    'GENERATE-RANDOM-KEY',
    'GENERATE-UUID',
    'GET',
    'GET-ATTR-CALL-TYPE',
    'GET-ATTRIBUTE-NODE',
    'GET-BINARY-DATA',
    'GET-BLUE',
    'GET-BLUE-',
    'GET-BLUE-V',
    'GET-BLUE-VA',
    'GET-BLUE-VAL',
    'GET-BLUE-VALU',
    'GET-BLUE-VALUE',
    'GET-BROWSE-COLUMN',
    'GET-BUFFER-HANDLE',
    'GET-BYTE',
    'GET-CALLBACK-PROC-CONTEXT',
    'GET-CALLBACK-PROC-NAME',
    'GET-CGI-LIST',
    'GET-CGI-LONG-VALUE',
    'GET-CGI-VALUE',
    'GET-CLASS',
    'GET-CODEPAGES',
    'GET-COLLATIONS',
    'GET-CONFIG-VALUE',
    'GET-CURRENT',
    'GET-DOUBLE',
    'GET-DROPPED-FILE',
    'GET-DYNAMIC',
    'GET-ERROR-COLUMN',
    'GET-ERROR-ROW',
    'GET-FILE',
    'GET-FILE-NAME',
    'GET-FILE-OFFSE',
    'GET-FILE-OFFSET',
    'GET-FIRST',
    'GET-FLOAT',
    'GET-GREEN',
    'GET-GREEN-',
    'GET-GREEN-V',
    'GET-GREEN-VA',
    'GET-GREEN-VAL',
    'GET-GREEN-VALU',
    'GET-GREEN-VALUE',
    'GET-INDEX-BY-NAMESPACE-NAME',
    'GET-INDEX-BY-QNAME',
    'GET-INT64',
    'GET-ITERATION',
    'GET-KEY-VAL',
    'GET-KEY-VALU',
    'GET-KEY-VALUE',
    'GET-LAST',
    'GET-LOCALNAME-BY-INDEX',
    'GET-LONG',
    'GET-MESSAGE',
    'GET-NEXT',
    'GET-NUMBER',
    'GET-POINTER-VALUE',
    'GET-PREV',
    'GET-PRINTERS',
    'GET-PROPERTY',
    'GET-QNAME-BY-INDEX',
    'GET-RED',
    'GET-RED-',
    'GET-RED-V',
    'GET-RED-VA',
    'GET-RED-VAL',
    'GET-RED-VALU',
    'GET-RED-VALUE',
    'GET-REPOSITIONED-ROW',
    'GET-RGB-VALUE',
    'GET-SELECTED',
    'GET-SELECTED-',
    'GET-SELECTED-W',
    'GET-SELECTED-WI',
    'GET-SELECTED-WID',
    'GET-SELECTED-WIDG',
    'GET-SELECTED-WIDGE',
    'GET-SELECTED-WIDGET',
    'GET-SHORT',
    'GET-SIGNATURE',
    'GET-SIZE',
    'GET-STRING',
    'GET-TAB-ITEM',
    'GET-TEXT-HEIGHT',
    'GET-TEXT-HEIGHT-',
    'GET-TEXT-HEIGHT-C',
    'GET-TEXT-HEIGHT-CH',
    'GET-TEXT-HEIGHT-CHA',
    'GET-TEXT-HEIGHT-CHAR',
    'GET-TEXT-HEIGHT-CHARS',
    'GET-TEXT-HEIGHT-P',
    'GET-TEXT-HEIGHT-PI',
    'GET-TEXT-HEIGHT-PIX',
    'GET-TEXT-HEIGHT-PIXE',
    'GET-TEXT-HEIGHT-PIXEL',
    'GET-TEXT-HEIGHT-PIXELS',
    'GET-TEXT-WIDTH',
    'GET-TEXT-WIDTH-',
    'GET-TEXT-WIDTH-C',
    'GET-TEXT-WIDTH-CH',
    'GET-TEXT-WIDTH-CHA',
    'GET-TEXT-WIDTH-CHAR',
    'GET-TEXT-WIDTH-CHARS',
    'GET-TEXT-WIDTH-P',
    'GET-TEXT-WIDTH-PI',
    'GET-TEXT-WIDTH-PIX',
    'GET-TEXT-WIDTH-PIXE',
    'GET-TEXT-WIDTH-PIXEL',
    'GET-TEXT-WIDTH-PIXELS',
    'GET-TYPE-BY-INDEX',
    'GET-TYPE-BY-NAMESPACE-NAME',
    'GET-TYPE-BY-QNAME',
    'GET-UNSIGNED-LONG',
    'GET-UNSIGNED-SHORT',
    'GET-URI-BY-INDEX',
    'GET-VALUE-BY-INDEX',
    'GET-VALUE-BY-NAMESPACE-NAME',
    'GET-VALUE-BY-QNAME',
    'GET-WAIT-STATE',
    'GETBYTE',
    'GLOBAL',
    'GO-ON',
    'GO-PEND',
    'GO-PENDI',
    'GO-PENDIN',
    'GO-PENDING',
    'GRANT',
    'GRAPHIC-E',
    'GRAPHIC-ED',
    'GRAPHIC-EDG',
    'GRAPHIC-EDGE',
    'GRID-FACTOR-H',
    'GRID-FACTOR-HO',
    'GRID-FACTOR-HOR',
    'GRID-FACTOR-HORI',
    'GRID-FACTOR-HORIZ',
    'GRID-FACTOR-HORIZO',
    'GRID-FACTOR-HORIZON',
    'GRID-FACTOR-HORIZONT',
    'GRID-FACTOR-HORIZONTA',
    'GRID-FACTOR-HORIZONTAL',
    'GRID-FACTOR-V',
    'GRID-FACTOR-VE',
    'GRID-FACTOR-VER',
    'GRID-FACTOR-VERT',
    'GRID-FACTOR-VERTI',
    'GRID-FACTOR-VERTIC',
    'GRID-FACTOR-VERTICA',
    'GRID-FACTOR-VERTICAL',
    'GRID-SNAP',
    'GRID-UNIT-HEIGHT',
    'GRID-UNIT-HEIGHT-',
    'GRID-UNIT-HEIGHT-C',
    'GRID-UNIT-HEIGHT-CH',
    'GRID-UNIT-HEIGHT-CHA',
    'GRID-UNIT-HEIGHT-CHARS',
    'GRID-UNIT-HEIGHT-P',
    'GRID-UNIT-HEIGHT-PI',
    'GRID-UNIT-HEIGHT-PIX',
    'GRID-UNIT-HEIGHT-PIXE',
    'GRID-UNIT-HEIGHT-PIXEL',
    'GRID-UNIT-HEIGHT-PIXELS',
    'GRID-UNIT-WIDTH',
    'GRID-UNIT-WIDTH-',
    'GRID-UNIT-WIDTH-C',
    'GRID-UNIT-WIDTH-CH',
    'GRID-UNIT-WIDTH-CHA',
    'GRID-UNIT-WIDTH-CHAR',
    'GRID-UNIT-WIDTH-CHARS',
    'GRID-UNIT-WIDTH-P',
    'GRID-UNIT-WIDTH-PI',
    'GRID-UNIT-WIDTH-PIX',
    'GRID-UNIT-WIDTH-PIXE',
    'GRID-UNIT-WIDTH-PIXEL',
    'GRID-UNIT-WIDTH-PIXELS',
    'GRID-VISIBLE',
    'GROUP',
    'GT',
    'GUID',
    'HANDLE',
    'HANDLER',
    'HAS-RECORDS',
    'HAVING',
    'HEADER',
    'HEIGHT',
    'HEIGHT-',
    'HEIGHT-C',
    'HEIGHT-CH',
    'HEIGHT-CHA',
    'HEIGHT-CHAR',
    'HEIGHT-CHARS',
    'HEIGHT-P',
    'HEIGHT-PI',
    'HEIGHT-PIX',
    'HEIGHT-PIXE',
    'HEIGHT-PIXEL',
    'HEIGHT-PIXELS',
    'HELP',
    'HEX-DECODE',
    'HEX-ENCODE',
    'HIDDEN',
    'HIDE',
    'HORI',
    'HORIZ',
    'HORIZO',
    'HORIZON',
    'HORIZONT',
    'HORIZONTA',
    'HORIZONTAL',
    'HOST-BYTE-ORDER',
    'HTML-CHARSET',
    'HTML-END-OF-LINE',
    'HTML-END-OF-PAGE',
    'HTML-FRAME-BEGIN',
    'HTML-FRAME-END',
    'HTML-HEADER-BEGIN',
    'HTML-HEADER-END',
    'HTML-TITLE-BEGIN',
    'HTML-TITLE-END',
    'HWND',
    'ICON',
    'IF',
    'IMAGE',
    'IMAGE-DOWN',
    'IMAGE-INSENSITIVE',
    'IMAGE-SIZE',
    'IMAGE-SIZE-C',
    'IMAGE-SIZE-CH',
    'IMAGE-SIZE-CHA',
    'IMAGE-SIZE-CHAR',
    'IMAGE-SIZE-CHARS',
    'IMAGE-SIZE-P',
    'IMAGE-SIZE-PI',
    'IMAGE-SIZE-PIX',
    'IMAGE-SIZE-PIXE',
    'IMAGE-SIZE-PIXEL',
    'IMAGE-SIZE-PIXELS',
    'IMAGE-UP',
    'IMMEDIATE-DISPLAY',
    'IMPLEMENTS',
    'IMPORT',
    'IMPORT-PRINCIPAL',
    'IN',
    'IN-HANDLE',
    'INCREMENT-EXCLUSIVE-ID',
    'INDEX',
    'INDEX-HINT',
    'INDEX-INFORMATION',
    'INDEXED-REPOSITION',
    'INDICATOR',
    'INFO',
    'INFOR',
    'INFORM',
    'INFORMA',
    'INFORMAT',
    'INFORMATI',
    'INFORMATIO',
    'INFORMATION',
    'INHERIT-BGC',
    'INHERIT-BGCO',
    'INHERIT-BGCOL',
    'INHERIT-BGCOLO',
    'INHERIT-BGCOLOR',
    'INHERIT-FGC',
    'INHERIT-FGCO',
    'INHERIT-FGCOL',
    'INHERIT-FGCOLO',
    'INHERIT-FGCOLOR',
    'INHERITS',
    'INIT',
    'INITI',
    'INITIA',
    'INITIAL',
    'INITIAL-DIR',
    'INITIAL-FILTER',
    'INITIALIZE-DOCUMENT-TYPE',
    'INITIATE',
    'INNER-CHARS',
    'INNER-LINES',
    'INPUT',
    'INPUT-O',
    'INPUT-OU',
    'INPUT-OUT',
    'INPUT-OUTP',
    'INPUT-OUTPU',
    'INPUT-OUTPUT',
    'INPUT-VALUE',
    'INSERT',
    'INSERT-ATTRIBUTE',
    'INSERT-B',
    'INSERT-BA',
    'INSERT-BAC',
    'INSERT-BACK',
    'INSERT-BACKT',
    'INSERT-BACKTA',
    'INSERT-BACKTAB',
    'INSERT-FILE',
    'INSERT-ROW',
    'INSERT-STRING',
    'INSERT-T',
    'INSERT-TA',
    'INSERT-TAB',
    'INT64',
    'INT',
    'INTEGER',
    'INTERFACE',
    'INTERNAL-ENTRIES',
    'INTO',
    'INVOKE',
    'IS',
    'IS-ATTR',
    'IS-ATTR-',
    'IS-ATTR-S',
    'IS-ATTR-SP',
    'IS-ATTR-SPA',
    'IS-ATTR-SPAC',
    'IS-ATTR-SPACE',
    'IS-CLASS',
    'IS-JSON',
    'IS-LEAD-BYTE',
    'IS-OPEN',
    'IS-PARAMETER-SET',
    'IS-PARTITIONED',
    'IS-ROW-SELECTED',
    'IS-SELECTED',
    'IS-XML',
    'ITEM',
    'ITEMS-PER-ROW',
    'JOIN',
    'JOIN-BY-SQLDB',
    'KBLABEL',
    'KEEP-CONNECTION-OPEN',
    'KEEP-FRAME-Z',
    'KEEP-FRAME-Z-',
    'KEEP-FRAME-Z-O',
    'KEEP-FRAME-Z-OR',
    'KEEP-FRAME-Z-ORD',
    'KEEP-FRAME-Z-ORDE',
    'KEEP-FRAME-Z-ORDER',
    'KEEP-MESSAGES',
    'KEEP-SECURITY-CACHE',
    'KEEP-TAB-ORDER',
    'KEY',
    'KEY-CODE',
    'KEY-FUNC',
    'KEY-FUNCT',
    'KEY-FUNCTI',
    'KEY-FUNCTIO',
    'KEY-FUNCTION',
    'KEY-LABEL',
    'KEYCODE',
    'KEYFUNC',
    'KEYFUNCT',
    'KEYFUNCTI',
    'KEYFUNCTIO',
    'KEYFUNCTION',
    'KEYLABEL',
    'KEYS',
    'KEYWORD',
    'KEYWORD-ALL',
    'LABEL',
    'LABEL-BGC',
    'LABEL-BGCO',
    'LABEL-BGCOL',
    'LABEL-BGCOLO',
    'LABEL-BGCOLOR',
    'LABEL-DC',
    'LABEL-DCO',
    'LABEL-DCOL',
    'LABEL-DCOLO',
    'LABEL-DCOLOR',
    'LABEL-FGC',
    'LABEL-FGCO',
    'LABEL-FGCOL',
    'LABEL-FGCOLO',
    'LABEL-FGCOLOR',
    'LABEL-FONT',
    'LABEL-PFC',
    'LABEL-PFCO',
    'LABEL-PFCOL',
    'LABEL-PFCOLO',
    'LABEL-PFCOLOR',
    'LABELS',
    'LABELS-HAVE-COLONS',
    'LANDSCAPE',
    'LANGUAGE',
    'LANGUAGES',
    'LARGE',
    'LARGE-TO-SMALL',
    'LAST',
    'LAST-ASYNCH-REQUEST',
    'LAST-BATCH',
    'LAST-CHILD',
    'LAST-EVEN',
    'LAST-EVENT',
    'LAST-FORM',
    'LAST-KEY',
    'LAST-OBJECT',
    'LAST-OF',
    'LAST-PROCE',
    'LAST-PROCED',
    'LAST-PROCEDU',
    'LAST-PROCEDUR',
    'LAST-PROCEDURE',
    'LAST-SERVER',
    'LAST-TAB-I',
    'LAST-TAB-IT',
    'LAST-TAB-ITE',
    'LAST-TAB-ITEM',
    'LASTKEY',
    'LC',
    'LDBNAME',
    'LE',
    'LEAVE',
    'LEFT-ALIGN',
    'LEFT-ALIGNE',
    'LEFT-ALIGNED',
    'LEFT-TRIM',
    'LENGTH',
    'LIBRARY',
    'LIKE',
    'LIKE-SEQUENTIAL',
    'LINE',
    'LINE-COUNT',
    'LINE-COUNTE',
    'LINE-COUNTER',
    'LIST-EVENTS',
    'LIST-ITEM-PAIRS',
    'LIST-ITEMS',
    'LIST-PROPERTY-NAMES',
    'LIST-QUERY-ATTRS',
    'LIST-SET-ATTRS',
    'LIST-WIDGETS',
    'LISTI',
    'LISTIN',
    'LISTING',
    'LITERAL-QUESTION',
    'LITTLE-ENDIAN',
    'LOAD',
    'LOAD-DOMAINS',
    'LOAD-ICON',
    'LOAD-IMAGE',
    'LOAD-IMAGE-DOWN',
    'LOAD-IMAGE-INSENSITIVE',
    'LOAD-IMAGE-UP',
    'LOAD-MOUSE-P',
    'LOAD-MOUSE-PO',
    'LOAD-MOUSE-POI',
    'LOAD-MOUSE-POIN',
    'LOAD-MOUSE-POINT',
    'LOAD-MOUSE-POINTE',
    'LOAD-MOUSE-POINTER',
    'LOAD-PICTURE',
    'LOAD-SMALL-ICON',
    'LOCAL-NAME',
    'LOCAL-VERSION-INFO',
    'LOCATOR-COLUMN-NUMBER',
    'LOCATOR-LINE-NUMBER',
    'LOCATOR-PUBLIC-ID',
    'LOCATOR-SYSTEM-ID',
    'LOCATOR-TYPE',
    'LOCK-REGISTRATION',
    'LOCKED',
    'LOG',
    'LOG-AUDIT-EVENT',
    'LOG-MANAGER',
    'LOGICAL',
    'LOGIN-EXPIRATION-TIMESTAMP',
    'LOGIN-HOST',
    'LOGIN-STATE',
    'LOGOUT',
    'LONGCHAR',
    'LOOKAHEAD',
    'LOOKUP',
    'LT',
    'MACHINE-CLASS',
    'MANDATORY',
    'MANUAL-HIGHLIGHT',
    'MAP',
    'MARGIN-EXTRA',
    'MARGIN-HEIGHT',
    'MARGIN-HEIGHT-',
    'MARGIN-HEIGHT-C',
    'MARGIN-HEIGHT-CH',
    'MARGIN-HEIGHT-CHA',
    'MARGIN-HEIGHT-CHAR',
    'MARGIN-HEIGHT-CHARS',
    'MARGIN-HEIGHT-P',
    'MARGIN-HEIGHT-PI',
    'MARGIN-HEIGHT-PIX',
    'MARGIN-HEIGHT-PIXE',
    'MARGIN-HEIGHT-PIXEL',
    'MARGIN-HEIGHT-PIXELS',
    'MARGIN-WIDTH',
    'MARGIN-WIDTH-',
    'MARGIN-WIDTH-C',
    'MARGIN-WIDTH-CH',
    'MARGIN-WIDTH-CHA',
    'MARGIN-WIDTH-CHAR',
    'MARGIN-WIDTH-CHARS',
    'MARGIN-WIDTH-P',
    'MARGIN-WIDTH-PI',
    'MARGIN-WIDTH-PIX',
    'MARGIN-WIDTH-PIXE',
    'MARGIN-WIDTH-PIXEL',
    'MARGIN-WIDTH-PIXELS',
    'MARK-NEW',
    'MARK-ROW-STATE',
    'MATCHES',
    'MAX',
    'MAX-BUTTON',
    'MAX-CHARS',
    'MAX-DATA-GUESS',
    'MAX-HEIGHT',
    'MAX-HEIGHT-C',
    'MAX-HEIGHT-CH',
    'MAX-HEIGHT-CHA',
    'MAX-HEIGHT-CHAR',
    'MAX-HEIGHT-CHARS',
    'MAX-HEIGHT-P',
    'MAX-HEIGHT-PI',
    'MAX-HEIGHT-PIX',
    'MAX-HEIGHT-PIXE',
    'MAX-HEIGHT-PIXEL',
    'MAX-HEIGHT-PIXELS',
    'MAX-ROWS',
    'MAX-SIZE',
    'MAX-VAL',
    'MAX-VALU',
    'MAX-VALUE',
    'MAX-WIDTH',
    'MAX-WIDTH-',
    'MAX-WIDTH-C',
    'MAX-WIDTH-CH',
    'MAX-WIDTH-CHA',
    'MAX-WIDTH-CHAR',
    'MAX-WIDTH-CHARS',
    'MAX-WIDTH-P',
    'MAX-WIDTH-PI',
    'MAX-WIDTH-PIX',
    'MAX-WIDTH-PIXE',
    'MAX-WIDTH-PIXEL',
    'MAX-WIDTH-PIXELS',
    'MAXI',
    'MAXIM',
    'MAXIMIZE',
    'MAXIMU',
    'MAXIMUM',
    'MAXIMUM-LEVEL',
    'MD5-DIGEST',
    'MEMBER',
    'MEMPTR-TO-NODE-VALUE',
    'MENU',
    'MENU-BAR',
    'MENU-ITEM',
    'MENU-K',
    'MENU-KE',
    'MENU-KEY',
    'MENU-M',
    'MENU-MO',
    'MENU-MOU',
    'MENU-MOUS',
    'MENU-MOUSE',
    'MENUBAR',
    'MERGE-BY-FIELD',
    'MESSAGE',
    'MESSAGE-AREA',
    'MESSAGE-AREA-FONT',
    'MESSAGE-LINES',
    'METHOD',
    'MIN',
    'MIN-BUTTON',
    'MIN-COLUMN-WIDTH-C',
    'MIN-COLUMN-WIDTH-CH',
    'MIN-COLUMN-WIDTH-CHA',
    'MIN-COLUMN-WIDTH-CHAR',
    'MIN-COLUMN-WIDTH-CHARS',
    'MIN-COLUMN-WIDTH-P',
    'MIN-COLUMN-WIDTH-PI',
    'MIN-COLUMN-WIDTH-PIX',
    'MIN-COLUMN-WIDTH-PIXE',
    'MIN-COLUMN-WIDTH-PIXEL',
    'MIN-COLUMN-WIDTH-PIXELS',
    'MIN-HEIGHT',
    'MIN-HEIGHT-',
    'MIN-HEIGHT-C',
    'MIN-HEIGHT-CH',
    'MIN-HEIGHT-CHA',
    'MIN-HEIGHT-CHAR',
    'MIN-HEIGHT-CHARS',
    'MIN-HEIGHT-P',
    'MIN-HEIGHT-PI',
    'MIN-HEIGHT-PIX',
    'MIN-HEIGHT-PIXE',
    'MIN-HEIGHT-PIXEL',
    'MIN-HEIGHT-PIXELS',
    'MIN-SIZE',
    'MIN-VAL',
    'MIN-VALU',
    'MIN-VALUE',
    'MIN-WIDTH',
    'MIN-WIDTH-',
    'MIN-WIDTH-C',
    'MIN-WIDTH-CH',
    'MIN-WIDTH-CHA',
    'MIN-WIDTH-CHAR',
    'MIN-WIDTH-CHARS',
    'MIN-WIDTH-P',
    'MIN-WIDTH-PI',
    'MIN-WIDTH-PIX',
    'MIN-WIDTH-PIXE',
    'MIN-WIDTH-PIXEL',
    'MIN-WIDTH-PIXELS',
    'MINI',
    'MINIM',
    'MINIMU',
    'MINIMUM',
    'MOD',
    'MODIFIED',
    'MODU',
    'MODUL',
    'MODULO',
    'MONTH',
    'MOUSE',
    'MOUSE-P',
    'MOUSE-PO',
    'MOUSE-POI',
    'MOUSE-POIN',
    'MOUSE-POINT',
    'MOUSE-POINTE',
    'MOUSE-POINTER',
    'MOVABLE',
    'MOVE-AFTER',
    'MOVE-AFTER-',
    'MOVE-AFTER-T',
    'MOVE-AFTER-TA',
    'MOVE-AFTER-TAB',
    'MOVE-AFTER-TAB-',
    'MOVE-AFTER-TAB-I',
    'MOVE-AFTER-TAB-IT',
    'MOVE-AFTER-TAB-ITE',
    'MOVE-AFTER-TAB-ITEM',
    'MOVE-BEFOR',
    'MOVE-BEFORE',
    'MOVE-BEFORE-',
    'MOVE-BEFORE-T',
    'MOVE-BEFORE-TA',
    'MOVE-BEFORE-TAB',
    'MOVE-BEFORE-TAB-',
    'MOVE-BEFORE-TAB-I',
    'MOVE-BEFORE-TAB-IT',
    'MOVE-BEFORE-TAB-ITE',
    'MOVE-BEFORE-TAB-ITEM',
    'MOVE-COL',
    'MOVE-COLU',
    'MOVE-COLUM',
    'MOVE-COLUMN',
    'MOVE-TO-B',
    'MOVE-TO-BO',
    'MOVE-TO-BOT',
    'MOVE-TO-BOTT',
    'MOVE-TO-BOTTO',
    'MOVE-TO-BOTTOM',
    'MOVE-TO-EOF',
    'MOVE-TO-T',
    'MOVE-TO-TO',
    'MOVE-TO-TOP',
    'MPE',
    'MTIME',
    'MULTI-COMPILE',
    'MULTIPLE',
    'MULTIPLE-KEY',
    'MULTITASKING-INTERVAL',
    'MUST-EXIST',
    'NAME',
    'NAMESPACE-PREFIX',
    'NAMESPACE-URI',
    'NATIVE',
    'NE',
    'NEEDS-APPSERVER-PROMPT',
    'NEEDS-PROMPT',
    'NEW',
    'NEW-INSTANCE',
    'NEW-ROW',
    'NEXT',
    'NEXT-COLUMN',
    'NEXT-PROMPT',
    'NEXT-ROWID',
    'NEXT-SIBLING',
    'NEXT-TAB-I',
    'NEXT-TAB-IT',
    'NEXT-TAB-ITE',
    'NEXT-TAB-ITEM',
    'NEXT-VALUE',
    'NO',
    'NO-APPLY',
    'NO-ARRAY-MESSAGE',
    'NO-ASSIGN',
    'NO-ATTR',
    'NO-ATTR-',
    'NO-ATTR-L',
    'NO-ATTR-LI',
    'NO-ATTR-LIS',
    'NO-ATTR-LIST',
    'NO-ATTR-S',
    'NO-ATTR-SP',
    'NO-ATTR-SPA',
    'NO-ATTR-SPAC',
    'NO-ATTR-SPACE',
    'NO-AUTO-VALIDATE',
    'NO-BIND-WHERE',
    'NO-BOX',
    'NO-CONSOLE',
    'NO-CONVERT',
    'NO-CONVERT-3D-COLORS',
    'NO-CURRENT-VALUE',
    'NO-DEBUG',
    'NO-DRAG',
    'NO-ECHO',
    'NO-EMPTY-SPACE',
    'NO-ERROR',
    'NO-F',
    'NO-FI',
    'NO-FIL',
    'NO-FILL',
    'NO-FOCUS',
    'NO-HELP',
    'NO-HIDE',
    'NO-INDEX-HINT',
    'NO-INHERIT-BGC',
    'NO-INHERIT-BGCO',
    'NO-INHERIT-BGCOLOR',
    'NO-INHERIT-FGC',
    'NO-INHERIT-FGCO',
    'NO-INHERIT-FGCOL',
    'NO-INHERIT-FGCOLO',
    'NO-INHERIT-FGCOLOR',
    'NO-JOIN-BY-SQLDB',
    'NO-LABE',
    'NO-LABELS',
    'NO-LOBS',
    'NO-LOCK',
    'NO-LOOKAHEAD',
    'NO-MAP',
    'NO-MES',
    'NO-MESS',
    'NO-MESSA',
    'NO-MESSAG',
    'NO-MESSAGE',
    'NO-PAUSE',
    'NO-PREFE',
    'NO-PREFET',
    'NO-PREFETC',
    'NO-PREFETCH',
    'NO-ROW-MARKERS',
    'NO-SCROLLBAR-VERTICAL',
    'NO-SEPARATE-CONNECTION',
    'NO-SEPARATORS',
    'NO-TAB-STOP',
    'NO-UND',
    'NO-UNDE',
    'NO-UNDER',
    'NO-UNDERL',
    'NO-UNDERLI',
    'NO-UNDERLIN',
    'NO-UNDERLINE',
    'NO-UNDO',
    'NO-VAL',
    'NO-VALI',
    'NO-VALID',
    'NO-VALIDA',
    'NO-VALIDAT',
    'NO-VALIDATE',
    'NO-WAIT',
    'NO-WORD-WRAP',
    'NODE-VALUE-TO-MEMPTR',
    'NONAMESPACE-SCHEMA-LOCATION',
    'NONE',
    'NORMALIZE',
    'NOT',
    'NOT-ACTIVE',
    'NOW',
    'NULL',
    'NUM-ALI',
    'NUM-ALIA',
    'NUM-ALIAS',
    'NUM-ALIASE',
    'NUM-ALIASES',
    'NUM-BUFFERS',
    'NUM-BUT',
    'NUM-BUTT',
    'NUM-BUTTO',
    'NUM-BUTTON',
    'NUM-BUTTONS',
    'NUM-COL',
    'NUM-COLU',
    'NUM-COLUM',
    'NUM-COLUMN',
    'NUM-COLUMNS',
    'NUM-COPIES',
    'NUM-DBS',
    'NUM-DROPPED-FILES',
    'NUM-ENTRIES',
    'NUM-FIELDS',
    'NUM-FORMATS',
    'NUM-ITEMS',
    'NUM-ITERATIONS',
    'NUM-LINES',
    'NUM-LOCKED-COL',
    'NUM-LOCKED-COLU',
    'NUM-LOCKED-COLUM',
    'NUM-LOCKED-COLUMN',
    'NUM-LOCKED-COLUMNS',
    'NUM-MESSAGES',
    'NUM-PARAMETERS',
    'NUM-REFERENCES',
    'NUM-REPLACED',
    'NUM-RESULTS',
    'NUM-SELECTED',
    'NUM-SELECTED-',
    'NUM-SELECTED-ROWS',
    'NUM-SELECTED-W',
    'NUM-SELECTED-WI',
    'NUM-SELECTED-WID',
    'NUM-SELECTED-WIDG',
    'NUM-SELECTED-WIDGE',
    'NUM-SELECTED-WIDGET',
    'NUM-SELECTED-WIDGETS',
    'NUM-TABS',
    'NUM-TO-RETAIN',
    'NUM-VISIBLE-COLUMNS',
    'NUMERIC',
    'NUMERIC-F',
    'NUMERIC-FO',
    'NUMERIC-FOR',
    'NUMERIC-FORM',
    'NUMERIC-FORMA',
    'NUMERIC-FORMAT',
    'OCTET-LENGTH',
    'OF',
    'OFF',
    'OK',
    'OK-CANCEL',
    'OLD',
    'ON',
    'ON-FRAME',
    'ON-FRAME-',
    'ON-FRAME-B',
    'ON-FRAME-BO',
    'ON-FRAME-BOR',
    'ON-FRAME-BORD',
    'ON-FRAME-BORDE',
    'ON-FRAME-BORDER',
    'OPEN',
    'OPSYS',
    'OPTION',
    'OR',
    'ORDERED-JOIN',
    'ORDINAL',
    'OS-APPEND',
    'OS-COMMAND',
    'OS-COPY',
    'OS-CREATE-DIR',
    'OS-DELETE',
    'OS-DIR',
    'OS-DRIVE',
    'OS-DRIVES',
    'OS-ERROR',
    'OS-GETENV',
    'OS-RENAME',
    'OTHERWISE',
    'OUTPUT',
    'OVERLAY',
    'OVERRIDE',
    'OWNER',
    'PAGE',
    'PAGE-BOT',
    'PAGE-BOTT',
    'PAGE-BOTTO',
    'PAGE-BOTTOM',
    'PAGE-NUM',
    'PAGE-NUMB',
    'PAGE-NUMBE',
    'PAGE-NUMBER',
    'PAGE-SIZE',
    'PAGE-TOP',
    'PAGE-WID',
    'PAGE-WIDT',
    'PAGE-WIDTH',
    'PAGED',
    'PARAM',
    'PARAME',
    'PARAMET',
    'PARAMETE',
    'PARAMETER',
    'PARENT',
    'PARSE-STATUS',
    'PARTIAL-KEY',
    'PASCAL',
    'PASSWORD-FIELD',
    'PATHNAME',
    'PAUSE',
    'PBE-HASH-ALG',
    'PBE-HASH-ALGO',
    'PBE-HASH-ALGOR',
    'PBE-HASH-ALGORI',
    'PBE-HASH-ALGORIT',
    'PBE-HASH-ALGORITH',
    'PBE-HASH-ALGORITHM',
    'PBE-KEY-ROUNDS',
    'PDBNAME',
    'PERSIST',
    'PERSISTE',
    'PERSISTEN',
    'PERSISTENT',
    'PERSISTENT-CACHE-DISABLED',
    'PFC',
    'PFCO',
    'PFCOL',
    'PFCOLO',
    'PFCOLOR',
    'PIXELS',
    'PIXELS-PER-COL',
    'PIXELS-PER-COLU',
    'PIXELS-PER-COLUM',
    'PIXELS-PER-COLUMN',
    'PIXELS-PER-ROW',
    'POPUP-M',
    'POPUP-ME',
    'POPUP-MEN',
    'POPUP-MENU',
    'POPUP-O',
    'POPUP-ON',
    'POPUP-ONL',
    'POPUP-ONLY',
    'PORTRAIT',
    'POSITION',
    'PRECISION',
    'PREFER-DATASET',
    'PREPARE-STRING',
    'PREPARED',
    'PREPROC',
    'PREPROCE',
    'PREPROCES',
    'PREPROCESS',
    'PRESEL',
    'PRESELE',
    'PRESELEC',
    'PRESELECT',
    'PREV',
    'PREV-COLUMN',
    'PREV-SIBLING',
    'PREV-TAB-I',
    'PREV-TAB-IT',
    'PREV-TAB-ITE',
    'PREV-TAB-ITEM',
    'PRIMARY',
    'PRINTER',
    'PRINTER-CONTROL-HANDLE',
    'PRINTER-HDC',
    'PRINTER-NAME',
    'PRINTER-PORT',
    'PRINTER-SETUP',
    'PRIVATE',
    'PRIVATE-D',
    'PRIVATE-DA',
    'PRIVATE-DAT',
    'PRIVATE-DATA',
    'PRIVILEGES',
    'PROC-HA',
    'PROC-HAN',
    'PROC-HAND',
    'PROC-HANDL',
    'PROC-HANDLE',
    'PROC-ST',
    'PROC-STA',
    'PROC-STAT',
    'PROC-STATU',
    'PROC-STATUS',
    'PROC-TEXT',
    'PROC-TEXT-BUFFER',
    'PROCE',
    'PROCED',
    'PROCEDU',
    'PROCEDUR',
    'PROCEDURE',
    'PROCEDURE-CALL-TYPE',
    'PROCEDURE-TYPE',
    'PROCESS',
    'PROFILER',
    'PROGRAM-NAME',
    'PROGRESS',
    'PROGRESS-S',
    'PROGRESS-SO',
    'PROGRESS-SOU',
    'PROGRESS-SOUR',
    'PROGRESS-SOURC',
    'PROGRESS-SOURCE',
    'PROMPT',
    'PROMPT-F',
    'PROMPT-FO',
    'PROMPT-FOR',
    'PROMSGS',
    'PROPATH',
    'PROPERTY',
    'PROTECTED',
    'PROVERS',
    'PROVERSI',
    'PROVERSIO',
    'PROVERSION',
    'PROXY',
    'PROXY-PASSWORD',
    'PROXY-USERID',
    'PUBLIC',
    'PUBLIC-ID',
    'PUBLISH',
    'PUBLISHED-EVENTS',
    'PUT',
    'PUT-BYTE',
    'PUT-DOUBLE',
    'PUT-FLOAT',
    'PUT-INT64',
    'PUT-KEY-VAL',
    'PUT-KEY-VALU',
    'PUT-KEY-VALUE',
    'PUT-LONG',
    'PUT-SHORT',
    'PUT-STRING',
    'PUT-UNSIGNED-LONG',
    'PUTBYTE',
    'QUERY',
    'QUERY-CLOSE',
    'QUERY-OFF-END',
    'QUERY-OPEN',
    'QUERY-PREPARE',
    'QUERY-TUNING',
    'QUESTION',
    'QUIT',
    'QUOTER',
    'R-INDEX',
    'RADIO-BUTTONS',
    'RADIO-SET',
    'RANDOM',
    'RAW',
    'RAW-TRANSFER',
    'RCODE-INFO',
    'RCODE-INFOR',
    'RCODE-INFORM',
    'RCODE-INFORMA',
    'RCODE-INFORMAT',
    'RCODE-INFORMATI',
    'RCODE-INFORMATIO',
    'RCODE-INFORMATION',
    'READ-AVAILABLE',
    'READ-EXACT-NUM',
    'READ-FILE',
    'READ-JSON',
    'READ-ONLY',
    'READ-XML',
    'READ-XMLSCHEMA',
    'READKEY',
    'REAL',
    'RECID',
    'RECORD-LENGTH',
    'RECT',
    'RECTA',
    'RECTAN',
    'RECTANG',
    'RECTANGL',
    'RECTANGLE',
    'RECURSIVE',
    'REFERENCE-ONLY',
    'REFRESH',
    'REFRESH-AUDIT-POLICY',
    'REFRESHABLE',
    'REGISTER-DOMAIN',
    'RELEASE',
    'REMOTE',
    'REMOVE-EVENTS-PROCEDURE',
    'REMOVE-SUPER-PROCEDURE',
    'REPEAT',
    'REPLACE',
    'REPLACE-SELECTION-TEXT',
    'REPOSITION',
    'REPOSITION-BACKWARD',
    'REPOSITION-FORWARD',
    'REPOSITION-MODE',
    'REPOSITION-TO-ROW',
    'REPOSITION-TO-ROWID',
    'REQUEST',
    'REQUEST-INFO',
    'RESET',
    'RESIZA',
    'RESIZAB',
    'RESIZABL',
    'RESIZABLE',
    'RESIZE',
    'RESPONSE-INFO',
    'RESTART-ROW',
    'RESTART-ROWID',
    'RETAIN',
    'RETAIN-SHAPE',
    'RETRY',
    'RETRY-CANCEL',
    'RETURN',
    'RETURN-ALIGN',
    'RETURN-ALIGNE',
    'RETURN-INS',
    'RETURN-INSE',
    'RETURN-INSER',
    'RETURN-INSERT',
    'RETURN-INSERTE',
    'RETURN-INSERTED',
    'RETURN-TO-START-DI',
    'RETURN-TO-START-DIR',
    'RETURN-VAL',
    'RETURN-VALU',
    'RETURN-VALUE',
    'RETURN-VALUE-DATA-TYPE',
    'RETURNS',
    'REVERSE-FROM',
    'REVERT',
    'REVOKE',
    'RGB-VALUE',
    'RIGHT-ALIGNED',
    'RIGHT-TRIM',
    'ROLES',
    'ROUND',
    'ROUTINE-LEVEL',
    'ROW',
    'ROW-HEIGHT-CHARS',
    'ROW-HEIGHT-PIXELS',
    'ROW-MARKERS',
    'ROW-OF',
    'ROW-RESIZABLE',
    'ROWID',
    'RULE',
    'RUN',
    'RUN-PROCEDURE',
    'SAVE CACHE',
    'SAVE',
    'SAVE-AS',
    'SAVE-FILE',
    'SAX-COMPLE',
    'SAX-COMPLET',
    'SAX-COMPLETE',
    'SAX-PARSE',
    'SAX-PARSE-FIRST',
    'SAX-PARSE-NEXT',
    'SAX-PARSER-ERROR',
    'SAX-RUNNING',
    'SAX-UNINITIALIZED',
    'SAX-WRITE-BEGIN',
    'SAX-WRITE-COMPLETE',
    'SAX-WRITE-CONTENT',
    'SAX-WRITE-ELEMENT',
    'SAX-WRITE-ERROR',
    'SAX-WRITE-IDLE',
    'SAX-WRITE-TAG',
    'SAX-WRITER',
    'SCHEMA',
    'SCHEMA-LOCATION',
    'SCHEMA-MARSHAL',
    'SCHEMA-PATH',
    'SCREEN',
    'SCREEN-IO',
    'SCREEN-LINES',
    'SCREEN-VAL',
    'SCREEN-VALU',
    'SCREEN-VALUE',
    'SCROLL',
    'SCROLL-BARS',
    'SCROLL-DELTA',
    'SCROLL-OFFSET',
    'SCROLL-TO-CURRENT-ROW',
    'SCROLL-TO-I',
    'SCROLL-TO-IT',
    'SCROLL-TO-ITE',
    'SCROLL-TO-ITEM',
    'SCROLL-TO-SELECTED-ROW',
    'SCROLLABLE',
    'SCROLLBAR-H',
    'SCROLLBAR-HO',
    'SCROLLBAR-HOR',
    'SCROLLBAR-HORI',
    'SCROLLBAR-HORIZ',
    'SCROLLBAR-HORIZO',
    'SCROLLBAR-HORIZON',
    'SCROLLBAR-HORIZONT',
    'SCROLLBAR-HORIZONTA',
    'SCROLLBAR-HORIZONTAL',
    'SCROLLBAR-V',
    'SCROLLBAR-VE',
    'SCROLLBAR-VER',
    'SCROLLBAR-VERT',
    'SCROLLBAR-VERTI',
    'SCROLLBAR-VERTIC',
    'SCROLLBAR-VERTICA',
    'SCROLLBAR-VERTICAL',
    'SCROLLED-ROW-POS',
    'SCROLLED-ROW-POSI',
    'SCROLLED-ROW-POSIT',
    'SCROLLED-ROW-POSITI',
    'SCROLLED-ROW-POSITIO',
    'SCROLLED-ROW-POSITION',
    'SCROLLING',
    'SDBNAME',
    'SEAL',
    'SEAL-TIMESTAMP',
    'SEARCH',
    'SEARCH-SELF',
    'SEARCH-TARGET',
    'SECTION',
    'SECURITY-POLICY',
    'SEEK',
    'SELECT',
    'SELECT-ALL',
    'SELECT-FOCUSED-ROW',
    'SELECT-NEXT-ROW',
    'SELECT-PREV-ROW',
    'SELECT-ROW',
    'SELECTABLE',
    'SELECTED',
    'SELECTION',
    'SELECTION-END',
    'SELECTION-LIST',
    'SELECTION-START',
    'SELECTION-TEXT',
    'SELF',
    'SEND',
    'SEND-SQL-STATEMENT',
    'SENSITIVE',
    'SEPARATE-CONNECTION',
    'SEPARATOR-FGCOLOR',
    'SEPARATORS',
    'SERIALIZABLE',
    'SERIALIZE-HIDDEN',
    'SERIALIZE-NAME',
    'SERVER',
    'SERVER-CONNECTION-BOUND',
    'SERVER-CONNECTION-BOUND-REQUEST',
    'SERVER-CONNECTION-CONTEXT',
    'SERVER-CONNECTION-ID',
    'SERVER-OPERATING-MODE',
    'SESSION',
    'SESSION-ID',
    'SET',
    'SET-APPL-CONTEXT',
    'SET-ATTR-CALL-TYPE',
    'SET-ATTRIBUTE-NODE',
    'SET-BLUE',
    'SET-BLUE-',
    'SET-BLUE-V',
    'SET-BLUE-VA',
    'SET-BLUE-VAL',
    'SET-BLUE-VALU',
    'SET-BLUE-VALUE',
    'SET-BREAK',
    'SET-BUFFERS',
    'SET-CALLBACK',
    'SET-CLIENT',
    'SET-COMMIT',
    'SET-CONTENTS',
    'SET-CURRENT-VALUE',
    'SET-DB-CLIENT',
    'SET-DYNAMIC',
    'SET-EVENT-MANAGER-OPTION',
    'SET-GREEN',
    'SET-GREEN-',
    'SET-GREEN-V',
    'SET-GREEN-VA',
    'SET-GREEN-VAL',
    'SET-GREEN-VALU',
    'SET-GREEN-VALUE',
    'SET-INPUT-SOURCE',
    'SET-OPTION',
    'SET-OUTPUT-DESTINATION',
    'SET-PARAMETER',
    'SET-POINTER-VALUE',
    'SET-PROPERTY',
    'SET-RED',
    'SET-RED-',
    'SET-RED-V',
    'SET-RED-VA',
    'SET-RED-VAL',
    'SET-RED-VALU',
    'SET-RED-VALUE',
    'SET-REPOSITIONED-ROW',
    'SET-RGB-VALUE',
    'SET-ROLLBACK',
    'SET-SELECTION',
    'SET-SIZE',
    'SET-SORT-ARROW',
    'SET-WAIT-STATE',
    'SETUSER',
    'SETUSERI',
    'SETUSERID',
    'SHA1-DIGEST',
    'SHARE',
    'SHARE-',
    'SHARE-L',
    'SHARE-LO',
    'SHARE-LOC',
    'SHARE-LOCK',
    'SHARED',
    'SHOW-IN-TASKBAR',
    'SHOW-STAT',
    'SHOW-STATS',
    'SIDE-LAB',
    'SIDE-LABE',
    'SIDE-LABEL',
    'SIDE-LABEL-H',
    'SIDE-LABEL-HA',
    'SIDE-LABEL-HAN',
    'SIDE-LABEL-HAND',
    'SIDE-LABEL-HANDL',
    'SIDE-LABEL-HANDLE',
    'SIDE-LABELS',
    'SIGNATURE',
    'SILENT',
    'SIMPLE',
    'SINGLE',
    'SINGLE-RUN',
    'SINGLETON',
    'SIZE',
    'SIZE-C',
    'SIZE-CH',
    'SIZE-CHA',
    'SIZE-CHAR',
    'SIZE-CHARS',
    'SIZE-P',
    'SIZE-PI',
    'SIZE-PIX',
    'SIZE-PIXE',
    'SIZE-PIXEL',
    'SIZE-PIXELS',
    'SKIP',
    'SKIP-DELETED-RECORD',
    'SLIDER',
    'SMALL-ICON',
    'SMALL-TITLE',
    'SMALLINT',
    'SOME',
    'SORT',
    'SORT-ASCENDING',
    'SORT-NUMBER',
    'SOURCE',
    'SOURCE-PROCEDURE',
    'SPACE',
    'SQL',
    'SQRT',
    'SSL-SERVER-NAME',
    'STANDALONE',
    'START',
    'START-DOCUMENT',
    'START-ELEMENT',
    'START-MOVE',
    'START-RESIZE',
    'START-ROW-RESIZE',
    'STATE-DETAIL',
    'STATIC',
    'STATUS',
    'STATUS-AREA',
    'STATUS-AREA-FONT',
    'STDCALL',
    'STOP',
    'STOP-AFTER',
    'STOP-PARSING',
    'STOPPE',
    'STOPPED',
    'STORED-PROC',
    'STORED-PROCE',
    'STORED-PROCED',
    'STORED-PROCEDU',
    'STORED-PROCEDUR',
    'STORED-PROCEDURE',
    'STREAM',
    'STREAM-HANDLE',
    'STREAM-IO',
    'STRETCH-TO-FIT',
    'STRICT',
    'STRICT-ENTITY-RESOLUTION',
    'STRING',
    'STRING-VALUE',
    'STRING-XREF',
    'SUB-AVE',
    'SUB-AVER',
    'SUB-AVERA',
    'SUB-AVERAG',
    'SUB-AVERAGE',
    'SUB-COUNT',
    'SUB-MAXIMUM',
    'SUB-MENU',
    'SUB-MIN',
    'SUB-MINIMUM',
    'SUB-TOTAL',
    'SUBSCRIBE',
    'SUBST',
    'SUBSTI',
    'SUBSTIT',
    'SUBSTITU',
    'SUBSTITUT',
    'SUBSTITUTE',
    'SUBSTR',
    'SUBSTRI',
    'SUBSTRIN',
    'SUBSTRING',
    'SUBTYPE',
    'SUM',
    'SUM-MAX',
    'SUM-MAXI',
    'SUM-MAXIM',
    'SUM-MAXIMU',
    'SUPER',
    'SUPER-PROCEDURES',
    'SUPPRESS-NAMESPACE-PROCESSING',
    'SUPPRESS-W',
    'SUPPRESS-WA',
    'SUPPRESS-WAR',
    'SUPPRESS-WARN',
    'SUPPRESS-WARNI',
    'SUPPRESS-WARNIN',
    'SUPPRESS-WARNING',
    'SUPPRESS-WARNINGS',
    'SYMMETRIC-ENCRYPTION-ALGORITHM',
    'SYMMETRIC-ENCRYPTION-IV',
    'SYMMETRIC-ENCRYPTION-KEY',
    'SYMMETRIC-SUPPORT',
    'SYSTEM-ALERT',
    'SYSTEM-ALERT-',
    'SYSTEM-ALERT-B',
    'SYSTEM-ALERT-BO',
    'SYSTEM-ALERT-BOX',
    'SYSTEM-ALERT-BOXE',
    'SYSTEM-ALERT-BOXES',
    'SYSTEM-DIALOG',
    'SYSTEM-HELP',
    'SYSTEM-ID',
    'TAB-POSITION',
    'TAB-STOP',
    'TABLE',
    'TABLE-HANDLE',
    'TABLE-NUMBER',
    'TABLE-SCAN',
    'TARGET',
    'TARGET-PROCEDURE',
    'TEMP-DIR',
    'TEMP-DIRE',
    'TEMP-DIREC',
    'TEMP-DIRECT',
    'TEMP-DIRECTO',
    'TEMP-DIRECTOR',
    'TEMP-DIRECTORY',
    'TEMP-TABLE',
    'TEMP-TABLE-PREPARE',
    'TERM',
    'TERMI',
    'TERMIN',
    'TERMINA',
    'TERMINAL',
    'TERMINATE',
    'TEXT',
    'TEXT-CURSOR',
    'TEXT-SEG-GROW',
    'TEXT-SELECTED',
    'THEN',
    'THIS-OBJECT',
    'THIS-PROCEDURE',
    'THREAD-SAFE',
    'THREE-D',
    'THROUGH',
    'THROW',
    'THRU',
    'TIC-MARKS',
    'TIME',
    'TIME-SOURCE',
    'TITLE',
    'TITLE-BGC',
    'TITLE-BGCO',
    'TITLE-BGCOL',
    'TITLE-BGCOLO',
    'TITLE-BGCOLOR',
    'TITLE-DC',
    'TITLE-DCO',
    'TITLE-DCOL',
    'TITLE-DCOLO',
    'TITLE-DCOLOR',
    'TITLE-FGC',
    'TITLE-FGCO',
    'TITLE-FGCOL',
    'TITLE-FGCOLO',
    'TITLE-FGCOLOR',
    'TITLE-FO',
    'TITLE-FON',
    'TITLE-FONT',
    'TO',
    'TO-ROWID',
    'TODAY',
    'TOGGLE-BOX',
    'TOOLTIP',
    'TOOLTIPS',
    'TOP-NAV-QUERY',
    'TOP-ONLY',
    'TOPIC',
    'TOTAL',
    'TRAILING',
    'TRANS',
    'TRANS-INIT-PROCEDURE',
    'TRANSACTION',
    'TRANSACTION-MODE',
    'TRANSPARENT',
    'TRIGGER',
    'TRIGGERS',
    'TRIM',
    'TRUE',
    'TRUNC',
    'TRUNCA',
    'TRUNCAT',
    'TRUNCATE',
    'TYPE',
    'TYPE-OF',
    'UNBOX',
    'UNBUFF',
    'UNBUFFE',
    'UNBUFFER',
    'UNBUFFERE',
    'UNBUFFERED',
    'UNDERL',
    'UNDERLI',
    'UNDERLIN',
    'UNDERLINE',
    'UNDO',
    'UNFORM',
    'UNFORMA',
    'UNFORMAT',
    'UNFORMATT',
    'UNFORMATTE',
    'UNFORMATTED',
    'UNION',
    'UNIQUE',
    'UNIQUE-ID',
    'UNIQUE-MATCH',
    'UNIX',
    'UNLESS-HIDDEN',
    'UNLOAD',
    'UNSIGNED-LONG',
    'UNSUBSCRIBE',
    'UP',
    'UPDATE',
    'UPDATE-ATTRIBUTE',
    'URL',
    'URL-DECODE',
    'URL-ENCODE',
    'URL-PASSWORD',
    'URL-USERID',
    'USE',
    'USE-DICT-EXPS',
    'USE-FILENAME',
    'USE-INDEX',
    'USE-REVVIDEO',
    'USE-TEXT',
    'USE-UNDERLINE',
    'USE-WIDGET-POOL',
    'USER',
    'USER-ID',
    'USERID',
    'USING',
    'V6DISPLAY',
    'V6FRAME',
    'VALID-EVENT',
    'VALID-HANDLE',
    'VALID-OBJECT',
    'VALIDATE',
    'VALIDATE-EXPRESSION',
    'VALIDATE-MESSAGE',
    'VALIDATE-SEAL',
    'VALIDATION-ENABLED',
    'VALUE',
    'VALUE-CHANGED',
    'VALUES',
    'VAR',
    'VARI',
    'VARIA',
    'VARIAB',
    'VARIABL',
    'VARIABLE',
    'VERBOSE',
    'VERSION',
    'VERT',
    'VERTI',
    'VERTIC',
    'VERTICA',
    'VERTICAL',
    'VIEW',
    'VIEW-AS',
    'VIEW-FIRST-COLUMN-ON-REOPEN',
    'VIRTUAL-HEIGHT',
    'VIRTUAL-HEIGHT-',
    'VIRTUAL-HEIGHT-C',
    'VIRTUAL-HEIGHT-CH',
    'VIRTUAL-HEIGHT-CHA',
    'VIRTUAL-HEIGHT-CHAR',
    'VIRTUAL-HEIGHT-CHARS',
    'VIRTUAL-HEIGHT-P',
    'VIRTUAL-HEIGHT-PI',
    'VIRTUAL-HEIGHT-PIX',
    'VIRTUAL-HEIGHT-PIXE',
    'VIRTUAL-HEIGHT-PIXEL',
    'VIRTUAL-HEIGHT-PIXELS',
    'VIRTUAL-WIDTH',
    'VIRTUAL-WIDTH-',
    'VIRTUAL-WIDTH-C',
    'VIRTUAL-WIDTH-CH',
    'VIRTUAL-WIDTH-CHA',
    'VIRTUAL-WIDTH-CHAR',
    'VIRTUAL-WIDTH-CHARS',
    'VIRTUAL-WIDTH-P',
    'VIRTUAL-WIDTH-PI',
    'VIRTUAL-WIDTH-PIX',
    'VIRTUAL-WIDTH-PIXE',
    'VIRTUAL-WIDTH-PIXEL',
    'VIRTUAL-WIDTH-PIXELS',
    'VISIBLE',
    'VOID',
    'WAIT',
    'WAIT-FOR',
    'WARNING',
    'WEB-CONTEXT',
    'WEEKDAY',
    'WHEN',
    'WHERE',
    'WHILE',
    'WIDGET',
    'WIDGET-E',
    'WIDGET-EN',
    'WIDGET-ENT',
    'WIDGET-ENTE',
    'WIDGET-ENTER',
    'WIDGET-ID',
    'WIDGET-L',
    'WIDGET-LE',
    'WIDGET-LEA',
    'WIDGET-LEAV',
    'WIDGET-LEAVE',
    'WIDGET-POOL',
    'WIDTH',
    'WIDTH-',
    'WIDTH-C',
    'WIDTH-CH',
    'WIDTH-CHA',
    'WIDTH-CHAR',
    'WIDTH-CHARS',
    'WIDTH-P',
    'WIDTH-PI',
    'WIDTH-PIX',
    'WIDTH-PIXE',
    'WIDTH-PIXEL',
    'WIDTH-PIXELS',
    'WINDOW',
    'WINDOW-MAXIM',
    'WINDOW-MAXIMI',
    'WINDOW-MAXIMIZ',
    'WINDOW-MAXIMIZE',
    'WINDOW-MAXIMIZED',
    'WINDOW-MINIM',
    'WINDOW-MINIMI',
    'WINDOW-MINIMIZ',
    'WINDOW-MINIMIZE',
    'WINDOW-MINIMIZED',
    'WINDOW-NAME',
    'WINDOW-NORMAL',
    'WINDOW-STA',
    'WINDOW-STAT',
    'WINDOW-STATE',
    'WINDOW-SYSTEM',
    'WITH',
    'WORD-INDEX',
    'WORD-WRAP',
    'WORK-AREA-HEIGHT-PIXELS',
    'WORK-AREA-WIDTH-PIXELS',
    'WORK-AREA-X',
    'WORK-AREA-Y',
    'WORK-TAB',
    'WORK-TABL',
    'WORK-TABLE',
    'WORKFILE',
    'WRITE',
    'WRITE-CDATA',
    'WRITE-CHARACTERS',
    'WRITE-COMMENT',
    'WRITE-DATA-ELEMENT',
    'WRITE-EMPTY-ELEMENT',
    'WRITE-ENTITY-REF',
    'WRITE-EXTERNAL-DTD',
    'WRITE-FRAGMENT',
    'WRITE-JSON',
    'WRITE-MESSAGE',
    'WRITE-PROCESSING-INSTRUCTION',
    'WRITE-STATUS',
    'WRITE-XML',
    'WRITE-XMLSCHEMA',
    'X',
    'X-OF',
    'XCODE',
    'XML-DATA-TYPE',
    'XML-ENTITY-EXPANSION-LIMIT',
    'XML-NODE-TYPE',
    'XML-SCHEMA-PATH',
    'XML-STRICT-ENTITY-RESOLUTION',
    'XML-SUPPRESS-NAMESPACE-PROCESSING',
    'XREF',
    'XREF-XML',
    'Y',
    'Y-OF',
    'YEAR',
    'YEAR-OFFSET',
    'YES',
    'YES-NO',
    'YES-NO-CANCEL'
)