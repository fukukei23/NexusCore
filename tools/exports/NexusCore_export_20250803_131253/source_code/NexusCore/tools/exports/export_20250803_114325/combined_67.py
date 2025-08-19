
# === NexusCore/openenv\Lib\site-packages\nltk\parse\chart.py ===
# Natural Language Toolkit: A Chart Parser
#
# Copyright (C) 2001-2024 NLTK Project
# Author: Edward Loper <edloper@gmail.com>
#         Steven Bird <stevenbird1@gmail.com>
#         Jean Mark Gawron <gawron@mail.sdsu.edu>
#         Peter Ljunglöf <peter.ljunglof@heatherleaf.se>
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT

"""
Data classes and parser implementations for "chart parsers", which
use dynamic programming to efficiently parse a text.  A chart
parser derives parse trees for a text by iteratively adding "edges"
to a "chart."  Each edge represents a hypothesis about the tree
structure for a subsequence of the text.  The chart is a
"blackboard" for composing and combining these hypotheses.

When a chart parser begins parsing a text, it creates a new (empty)
chart, spanning the text.  It then incrementally adds new edges to the
chart.  A set of "chart rules" specifies the conditions under which
new edges should be added to the chart.  Once the chart reaches a
stage where none of the chart rules adds any new edges, parsing is
complete.

Charts are encoded with the ``Chart`` class, and edges are encoded with
the ``TreeEdge`` and ``LeafEdge`` classes.  The chart parser module
defines three chart parsers:

  - ``ChartParser`` is a simple and flexible chart parser.  Given a
    set of chart rules, it will apply those rules to the chart until
    no more edges are added.

  - ``SteppingChartParser`` is a subclass of ``ChartParser`` that can
    be used to step through the parsing process.
"""

import itertools
import re
import warnings
from functools import total_ordering

from nltk.grammar import PCFG, is_nonterminal, is_terminal
from nltk.internals import raise_unorderable_types
from nltk.parse.api import ParserI
from nltk.tree import Tree
from nltk.util import OrderedDict

########################################################################
##  Edges
########################################################################


@total_ordering
class EdgeI:
    """
    A hypothesis about the structure of part of a sentence.
    Each edge records the fact that a structure is (partially)
    consistent with the sentence.  An edge contains:

    - A span, indicating what part of the sentence is
      consistent with the hypothesized structure.
    - A left-hand side, specifying what kind of structure is
      hypothesized.
    - A right-hand side, specifying the contents of the
      hypothesized structure.
    - A dot position, indicating how much of the hypothesized
      structure is consistent with the sentence.

    Every edge is either complete or incomplete:

    - An edge is complete if its structure is fully consistent
      with the sentence.
    - An edge is incomplete if its structure is partially
      consistent with the sentence.  For every incomplete edge, the
      span specifies a possible prefix for the edge's structure.

    There are two kinds of edge:

    - A ``TreeEdge`` records which trees have been found to
      be (partially) consistent with the text.
    - A ``LeafEdge`` records the tokens occurring in the text.

    The ``EdgeI`` interface provides a common interface to both types
    of edge, allowing chart parsers to treat them in a uniform manner.
    """

    def __init__(self):
        if self.__class__ == EdgeI:
            raise TypeError("Edge is an abstract interface")

    # ////////////////////////////////////////////////////////////
    # Span
    # ////////////////////////////////////////////////////////////

    def span(self):
        """
        Return a tuple ``(s, e)``, where ``tokens[s:e]`` is the
        portion of the sentence that is consistent with this
        edge's structure.

        :rtype: tuple(int, int)
        """
        raise NotImplementedError()

    def start(self):
        """
        Return the start index of this edge's span.

        :rtype: int
        """
        raise NotImplementedError()

    def end(self):
        """
        Return the end index of this edge's span.

        :rtype: int
        """
        raise NotImplementedError()

    def length(self):
        """
        Return the length of this edge's span.

        :rtype: int
        """
        raise NotImplementedError()

    # ////////////////////////////////////////////////////////////
    # Left Hand Side
    # ////////////////////////////////////////////////////////////

    def lhs(self):
        """
        Return this edge's left-hand side, which specifies what kind
        of structure is hypothesized by this edge.

        :see: ``TreeEdge`` and ``LeafEdge`` for a description of
            the left-hand side values for each edge type.
        """
        raise NotImplementedError()

    # ////////////////////////////////////////////////////////////
    # Right Hand Side
    # ////////////////////////////////////////////////////////////

    def rhs(self):
        """
        Return this edge's right-hand side, which specifies
        the content of the structure hypothesized by this edge.

        :see: ``TreeEdge`` and ``LeafEdge`` for a description of
            the right-hand side values for each edge type.
        """
        raise NotImplementedError()

    def dot(self):
        """
        Return this edge's dot position, which indicates how much of
        the hypothesized structure is consistent with the
        sentence.  In particular, ``self.rhs[:dot]`` is consistent
        with ``tokens[self.start():self.end()]``.

        :rtype: int
        """
        raise NotImplementedError()

    def nextsym(self):
        """
        Return the element of this edge's right-hand side that
        immediately follows its dot.

        :rtype: Nonterminal or terminal or None
        """
        raise NotImplementedError()

    def is_complete(self):
        """
        Return True if this edge's structure is fully consistent
        with the text.

        :rtype: bool
        """
        raise NotImplementedError()

    def is_incomplete(self):
        """
        Return True if this edge's structure is partially consistent
        with the text.

        :rtype: bool
        """
        raise NotImplementedError()

    # ////////////////////////////////////////////////////////////
    # Comparisons & hashing
    # ////////////////////////////////////////////////////////////

    def __eq__(self, other):
        return (
            self.__class__ is other.__class__
            and self._comparison_key == other._comparison_key
        )

    def __ne__(self, other):
        return not self == other

    def __lt__(self, other):
        if not isinstance(other, EdgeI):
            raise_unorderable_types("<", self, other)
        if self.__class__ is other.__class__:
            return self._comparison_key < other._comparison_key
        else:
            return self.__class__.__name__ < other.__class__.__name__

    def __hash__(self):
        try:
            return self._hash
        except AttributeError:
            self._hash = hash(self._comparison_key)
            return self._hash


class TreeEdge(EdgeI):
    """
    An edge that records the fact that a tree is (partially)
    consistent with the sentence.  A tree edge consists of:

    - A span, indicating what part of the sentence is
      consistent with the hypothesized tree.
    - A left-hand side, specifying the hypothesized tree's node
      value.
    - A right-hand side, specifying the hypothesized tree's
      children.  Each element of the right-hand side is either a
      terminal, specifying a token with that terminal as its leaf
      value; or a nonterminal, specifying a subtree with that
      nonterminal's symbol as its node value.
    - A dot position, indicating which children are consistent
      with part of the sentence.  In particular, if ``dot`` is the
      dot position, ``rhs`` is the right-hand size, ``(start,end)``
      is the span, and ``sentence`` is the list of tokens in the
      sentence, then ``tokens[start:end]`` can be spanned by the
      children specified by ``rhs[:dot]``.

    For more information about edges, see the ``EdgeI`` interface.
    """

    def __init__(self, span, lhs, rhs, dot=0):
        """
        Construct a new ``TreeEdge``.

        :type span: tuple(int, int)
        :param span: A tuple ``(s, e)``, where ``tokens[s:e]`` is the
            portion of the sentence that is consistent with the new
            edge's structure.
        :type lhs: Nonterminal
        :param lhs: The new edge's left-hand side, specifying the
            hypothesized tree's node value.
        :type rhs: list(Nonterminal and str)
        :param rhs: The new edge's right-hand side, specifying the
            hypothesized tree's children.
        :type dot: int
        :param dot: The position of the new edge's dot.  This position
            specifies what prefix of the production's right hand side
            is consistent with the text.  In particular, if
            ``sentence`` is the list of tokens in the sentence, then
            ``okens[span[0]:span[1]]`` can be spanned by the
            children specified by ``rhs[:dot]``.
        """
        self._span = span
        self._lhs = lhs
        rhs = tuple(rhs)
        self._rhs = rhs
        self._dot = dot
        self._comparison_key = (span, lhs, rhs, dot)

    @staticmethod
    def from_production(production, index):
        """
        Return a new ``TreeEdge`` formed from the given production.
        The new edge's left-hand side and right-hand side will
        be taken from ``production``; its span will be
        ``(index,index)``; and its dot position will be ``0``.

        :rtype: TreeEdge
        """
        return TreeEdge(
            span=(index, index), lhs=production.lhs(), rhs=production.rhs(), dot=0
        )

    def move_dot_forward(self, new_end):
        """
        Return a new ``TreeEdge`` formed from this edge.
        The new edge's dot position is increased by ``1``,
        and its end index will be replaced by ``new_end``.

        :param new_end: The new end index.
        :type new_end: int
        :rtype: TreeEdge
        """
        return TreeEdge(
            span=(self._span[0], new_end),
            lhs=self._lhs,
            rhs=self._rhs,
            dot=self._dot + 1,
        )

    # Accessors
    def lhs(self):
        return self._lhs

    def span(self):
        return self._span

    def start(self):
        return self._span[0]

    def end(self):
        return self._span[1]

    def length(self):
        return self._span[1] - self._span[0]

    def rhs(self):
        return self._rhs

    def dot(self):
        return self._dot

    def is_complete(self):
        return self._dot == len(self._rhs)

    def is_incomplete(self):
        return self._dot != len(self._rhs)

    def nextsym(self):
        if self._dot >= len(self._rhs):
            return None
        else:
            return self._rhs[self._dot]

    # String representation
    def __str__(self):
        str = f"[{self._span[0]}:{self._span[1]}] "
        str += "%-2r ->" % (self._lhs,)

        for i in range(len(self._rhs)):
            if i == self._dot:
                str += " *"
            str += " %s" % repr(self._rhs[i])
        if len(self._rhs) == self._dot:
            str += " *"
        return str

    def __repr__(self):
        return "[Edge: %s]" % self


class LeafEdge(EdgeI):
    """
    An edge that records the fact that a leaf value is consistent with
    a word in the sentence.  A leaf edge consists of:

    - An index, indicating the position of the word.
    - A leaf, specifying the word's content.

    A leaf edge's left-hand side is its leaf value, and its right hand
    side is ``()``.  Its span is ``[index, index+1]``, and its dot
    position is ``0``.
    """

    def __init__(self, leaf, index):
        """
        Construct a new ``LeafEdge``.

        :param leaf: The new edge's leaf value, specifying the word
            that is recorded by this edge.
        :param index: The new edge's index, specifying the position of
            the word that is recorded by this edge.
        """
        self._leaf = leaf
        self._index = index
        self._comparison_key = (leaf, index)

    # Accessors
    def lhs(self):
        return self._leaf

    def span(self):
        return (self._index, self._index + 1)

    def start(self):
        return self._index

    def end(self):
        return self._index + 1

    def length(self):
        return 1

    def rhs(self):
        return ()

    def dot(self):
        return 0

    def is_complete(self):
        return True

    def is_incomplete(self):
        return False

    def nextsym(self):
        return None

    # String representations
    def __str__(self):
        return f"[{self._index}:{self._index + 1}] {repr(self._leaf)}"

    def __repr__(self):
        return "[Edge: %s]" % (self)


########################################################################
##  Chart
########################################################################


class Chart:
    """
    A blackboard for hypotheses about the syntactic constituents of a
    sentence.  A chart contains a set of edges, and each edge encodes
    a single hypothesis about the structure of some portion of the
    sentence.

    The ``select`` method can be used to select a specific collection
    of edges.  For example ``chart.select(is_complete=True, start=0)``
    yields all complete edges whose start indices are 0.  To ensure
    the efficiency of these selection operations, ``Chart`` dynamically
    creates and maintains an index for each set of attributes that
    have been selected on.

    In order to reconstruct the trees that are represented by an edge,
    the chart associates each edge with a set of child pointer lists.
    A child pointer list is a list of the edges that license an
    edge's right-hand side.

    :ivar _tokens: The sentence that the chart covers.
    :ivar _num_leaves: The number of tokens.
    :ivar _edges: A list of the edges in the chart
    :ivar _edge_to_cpls: A dictionary mapping each edge to a set
        of child pointer lists that are associated with that edge.
    :ivar _indexes: A dictionary mapping tuples of edge attributes
        to indices, where each index maps the corresponding edge
        attribute values to lists of edges.
    """

    def __init__(self, tokens):
        """
        Construct a new chart. The chart is initialized with the
        leaf edges corresponding to the terminal leaves.

        :type tokens: list
        :param tokens: The sentence that this chart will be used to parse.
        """
        # Record the sentence token and the sentence length.
        self._tokens = tuple(tokens)
        self._num_leaves = len(self._tokens)

        # Initialise the chart.
        self.initialize()

    def initialize(self):
        """
        Clear the chart.
        """
        # A list of edges contained in this chart.
        self._edges = []

        # The set of child pointer lists associated with each edge.
        self._edge_to_cpls = {}

        # Indexes mapping attribute values to lists of edges
        # (used by select()).
        self._indexes = {}

    # ////////////////////////////////////////////////////////////
    # Sentence Access
    # ////////////////////////////////////////////////////////////

    def num_leaves(self):
        """
        Return the number of words in this chart's sentence.

        :rtype: int
        """
        return self._num_leaves

    def leaf(self, index):
        """
        Return the leaf value of the word at the given index.

        :rtype: str
        """
        return self._tokens[index]

    def leaves(self):
        """
        Return a list of the leaf values of each word in the
        chart's sentence.

        :rtype: list(str)
        """
        return self._tokens

    # ////////////////////////////////////////////////////////////
    # Edge access
    # ////////////////////////////////////////////////////////////

    def edges(self):
        """
        Return a list of all edges in this chart.  New edges
        that are added to the chart after the call to edges()
        will *not* be contained in this list.

        :rtype: list(EdgeI)
        :see: ``iteredges``, ``select``
        """
        return self._edges[:]

    def iteredges(self):
        """
        Return an iterator over the edges in this chart.  It is
        not guaranteed that new edges which are added to the
        chart before the iterator is exhausted will also be generated.

        :rtype: iter(EdgeI)
        :see: ``edges``, ``select``
        """
        return iter(self._edges)

    # Iterating over the chart yields its edges.
    __iter__ = iteredges

    def num_edges(self):
        """
        Return the number of edges contained in this chart.

        :rtype: int
        """
        return len(self._edge_to_cpls)

    def select(self, **restrictions):
        """
        Return an iterator over the edges in this chart.  Any
        new edges that are added to the chart before the iterator
        is exahusted will also be generated.  ``restrictions``
        can be used to restrict the set of edges that will be
        generated.

        :param span: Only generate edges ``e`` where ``e.span()==span``
        :param start: Only generate edges ``e`` where ``e.start()==start``
        :param end: Only generate edges ``e`` where ``e.end()==end``
        :param length: Only generate edges ``e`` where ``e.length()==length``
        :param lhs: Only generate edges ``e`` where ``e.lhs()==lhs``
        :param rhs: Only generate edges ``e`` where ``e.rhs()==rhs``
        :param nextsym: Only generate edges ``e`` where
            ``e.nextsym()==nextsym``
        :param dot: Only generate edges ``e`` where ``e.dot()==dot``
        :param is_complete: Only generate edges ``e`` where
            ``e.is_complete()==is_complete``
        :param is_incomplete: Only generate edges ``e`` where
            ``e.is_incomplete()==is_incomplete``
        :rtype: iter(EdgeI)
        """
        # If there are no restrictions, then return all edges.
        if restrictions == {}:
            return iter(self._edges)

        # Find the index corresponding to the given restrictions.
        restr_keys = sorted(restrictions.keys())
        restr_keys = tuple(restr_keys)

        # If it doesn't exist, then create it.
        if restr_keys not in self._indexes:
            self._add_index(restr_keys)

        vals = tuple(restrictions[key] for key in restr_keys)
        return iter(self._indexes[restr_keys].get(vals, []))

    def _add_index(self, restr_keys):
        """
        A helper function for ``select``, which creates a new index for
        a given set of attributes (aka restriction keys).
        """
        # Make sure it's a valid index.
        for key in restr_keys:
            if not hasattr(EdgeI, key):
                raise ValueError("Bad restriction: %s" % key)

        # Create the index.
        index = self._indexes[restr_keys] = {}

        # Add all existing edges to the index.
        for edge in self._edges:
            vals = tuple(getattr(edge, key)() for key in restr_keys)
            index.setdefault(vals, []).append(edge)

    def _register_with_indexes(self, edge):
        """
        A helper function for ``insert``, which registers the new
        edge with all existing indexes.
        """
        for restr_keys, index in self._indexes.items():
            vals = tuple(getattr(edge, key)() for key in restr_keys)
            index.setdefault(vals, []).append(edge)

    # ////////////////////////////////////////////////////////////
    # Edge Insertion
    # ////////////////////////////////////////////////////////////

    def insert_with_backpointer(self, new_edge, previous_edge, child_edge):
        """
        Add a new edge to the chart, using a pointer to the previous edge.
        """
        cpls = self.child_pointer_lists(previous_edge)
        new_cpls = [cpl + (child_edge,) for cpl in cpls]
        return self.insert(new_edge, *new_cpls)

    def insert(self, edge, *child_pointer_lists):
        """
        Add a new edge to the chart, and return True if this operation
        modified the chart.  In particular, return true iff the chart
        did not already contain ``edge``, or if it did not already associate
        ``child_pointer_lists`` with ``edge``.

        :type edge: EdgeI
        :param edge: The new edge
        :type child_pointer_lists: sequence of tuple(EdgeI)
        :param child_pointer_lists: A sequence of lists of the edges that
            were used to form this edge.  This list is used to reconstruct
            the trees (or partial trees) that are associated with ``edge``.
        :rtype: bool
        """
        # Is it a new edge?
        if edge not in self._edge_to_cpls:
            # Add it to the list of edges.
            self._append_edge(edge)
            # Register with indexes.
            self._register_with_indexes(edge)

        # Get the set of child pointer lists for this edge.
        cpls = self._edge_to_cpls.setdefault(edge, OrderedDict())
        chart_was_modified = False
        for child_pointer_list in child_pointer_lists:
            child_pointer_list = tuple(child_pointer_list)
            if child_pointer_list not in cpls:
                # It's a new CPL; register it, and return true.
                cpls[child_pointer_list] = True
                chart_was_modified = True
        return chart_was_modified

    def _append_edge(self, edge):
        self._edges.append(edge)

    # ////////////////////////////////////////////////////////////
    # Tree extraction & child pointer lists
    # ////////////////////////////////////////////////////////////

    def parses(self, root, tree_class=Tree):
        """
        Return an iterator of the complete tree structures that span
        the entire chart, and whose root node is ``root``.
        """
        for edge in self.select(start=0, end=self._num_leaves, lhs=root):
            yield from self.trees(edge, tree_class=tree_class, complete=True)

    def trees(self, edge, tree_class=Tree, complete=False):
        """
        Return an iterator of the tree structures that are associated
        with ``edge``.

        If ``edge`` is incomplete, then the unexpanded children will be
        encoded as childless subtrees, whose node value is the
        corresponding terminal or nonterminal.

        :rtype: list(Tree)
        :note: If two trees share a common subtree, then the same
            Tree may be used to encode that subtree in
            both trees.  If you need to eliminate this subtree
            sharing, then create a deep copy of each tree.
        """
        return iter(self._trees(edge, complete, memo={}, tree_class=tree_class))

    def _trees(self, edge, complete, memo, tree_class):
        """
        A helper function for ``trees``.

        :param memo: A dictionary used to record the trees that we've
            generated for each edge, so that when we see an edge more
            than once, we can reuse the same trees.
        """
        # If we've seen this edge before, then reuse our old answer.
        if edge in memo:
            return memo[edge]

        # when we're reading trees off the chart, don't use incomplete edges
        if complete and edge.is_incomplete():
            return []

        # Leaf edges.
        if isinstance(edge, LeafEdge):
            leaf = self._tokens[edge.start()]
            memo[edge] = [leaf]
            return [leaf]

        # Until we're done computing the trees for edge, set
        # memo[edge] to be empty.  This has the effect of filtering
        # out any cyclic trees (i.e., trees that contain themselves as
        # descendants), because if we reach this edge via a cycle,
        # then it will appear that the edge doesn't generate any trees.
        memo[edge] = []
        trees = []
        lhs = edge.lhs().symbol()

        # Each child pointer list can be used to form trees.
        for cpl in self.child_pointer_lists(edge):
            # Get the set of child choices for each child pointer.
            # child_choices[i] is the set of choices for the tree's
            # ith child.
            child_choices = [self._trees(cp, complete, memo, tree_class) for cp in cpl]

            # For each combination of children, add a tree.
            for children in itertools.product(*child_choices):
                trees.append(tree_class(lhs, children))

        # If the edge is incomplete, then extend it with "partial trees":
        if edge.is_incomplete():
            unexpanded = [tree_class(elt, []) for elt in edge.rhs()[edge.dot() :]]
            for tree in trees:
                tree.extend(unexpanded)

        # Update the memoization dictionary.
        memo[edge] = trees

        # Return the list of trees.
        return trees

    def child_pointer_lists(self, edge):
        """
        Return the set of child pointer lists for the given edge.
        Each child pointer list is a list of edges that have
        been used to form this edge.

        :rtype: list(list(EdgeI))
        """
        # Make a copy, in case they modify it.
        return self._edge_to_cpls.get(edge, {}).keys()

    # ////////////////////////////////////////////////////////////
    # Display
    # ////////////////////////////////////////////////////////////
    def pretty_format_edge(self, edge, width=None):
        """
        Return a pretty-printed string representation of a given edge
        in this chart.

        :rtype: str
        :param width: The number of characters allotted to each
            index in the sentence.
        """
        if width is None:
            width = 50 // (self.num_leaves() + 1)
        (start, end) = (edge.start(), edge.end())

        str = "|" + ("." + " " * (width - 1)) * start

        # Zero-width edges are "#" if complete, ">" if incomplete
        if start == end:
            if edge.is_complete():
                str += "#"
            else:
                str += ">"

        # Spanning complete edges are "[===]"; Other edges are
        # "[---]" if complete, "[--->" if incomplete
        elif edge.is_complete() and edge.span() == (0, self._num_leaves):
            str += "[" + ("=" * width) * (end - start - 1) + "=" * (width - 1) + "]"
        elif edge.is_complete():
            str += "[" + ("-" * width) * (end - start - 1) + "-" * (width - 1) + "]"
        else:
            str += "[" + ("-" * width) * (end - start - 1) + "-" * (width - 1) + ">"

        str += (" " * (width - 1) + ".") * (self._num_leaves - end)
        return str + "| %s" % edge

    def pretty_format_leaves(self, width=None):
        """
        Return a pretty-printed string representation of this
        chart's leaves.  This string can be used as a header
        for calls to ``pretty_format_edge``.
        """
        if width is None:
            width = 50 // (self.num_leaves() + 1)

        if self._tokens is not None and width > 1:
            header = "|."
            for tok in self._tokens:
                header += tok[: width - 1].center(width - 1) + "."
            header += "|"
        else:
            header = ""

        return header

    def pretty_format(self, width=None):
        """
        Return a pretty-printed string representation of this chart.

        :param width: The number of characters allotted to each
            index in the sentence.
        :rtype: str
        """
        if width is None:
            width = 50 // (self.num_leaves() + 1)
        # sort edges: primary key=length, secondary key=start index.
        # (and filter out the token edges)
        edges = sorted((e.length(), e.start(), e) for e in self)
        edges = [e for (_, _, e) in edges]

        return (
            self.pretty_format_leaves(width)
            + "\n"
            + "\n".join(self.pretty_format_edge(edge, width) for edge in edges)
        )

    # ////////////////////////////////////////////////////////////
    # Display: Dot (AT&T Graphviz)
    # ////////////////////////////////////////////////////////////

    def dot_digraph(self):
        # Header
        s = "digraph nltk_chart {\n"
        # s += '  size="5,5";\n'
        s += "  rankdir=LR;\n"
        s += "  node [height=0.1,width=0.1];\n"
        s += '  node [style=filled, color="lightgray"];\n'

        # Set up the nodes
        for y in range(self.num_edges(), -1, -1):
            if y == 0:
                s += '  node [style=filled, color="black"];\n'
            for x in range(self.num_leaves() + 1):
                if y == 0 or (
                    x <= self._edges[y - 1].start() or x >= self._edges[y - 1].end()
                ):
                    s += '  %04d.%04d [label=""];\n' % (x, y)

        # Add a spacer
        s += "  x [style=invis]; x->0000.0000 [style=invis];\n"

        # Declare ranks.
        for x in range(self.num_leaves() + 1):
            s += "  {rank=same;"
            for y in range(self.num_edges() + 1):
                if y == 0 or (
                    x <= self._edges[y - 1].start() or x >= self._edges[y - 1].end()
                ):
                    s += " %04d.%04d" % (x, y)
            s += "}\n"

        # Add the leaves
        s += "  edge [style=invis, weight=100];\n"
        s += "  node [shape=plaintext]\n"
        s += "  0000.0000"
        for x in range(self.num_leaves()):
            s += "->%s->%04d.0000" % (self.leaf(x), x + 1)
        s += ";\n\n"

        # Add the edges
        s += "  edge [style=solid, weight=1];\n"
        for y, edge in enumerate(self):
            for x in range(edge.start()):
                s += '  %04d.%04d -> %04d.%04d [style="invis"];\n' % (
                    x,
                    y + 1,
                    x + 1,
                    y + 1,
                )
            s += '  %04d.%04d -> %04d.%04d [label="%s"];\n' % (
                edge.start(),
                y + 1,
                edge.end(),
                y + 1,
                edge,
            )
            for x in range(edge.end(), self.num_leaves()):
                s += '  %04d.%04d -> %04d.%04d [style="invis"];\n' % (
                    x,
                    y + 1,
                    x + 1,
                    y + 1,
                )
        s += "}\n"
        return s


########################################################################
##  Chart Rules
########################################################################


class ChartRuleI:
    """
    A rule that specifies what new edges are licensed by any given set
    of existing edges.  Each chart rule expects a fixed number of
    edges, as indicated by the class variable ``NUM_EDGES``.  In
    particular:

    - A chart rule with ``NUM_EDGES=0`` specifies what new edges are
      licensed, regardless of existing edges.
    - A chart rule with ``NUM_EDGES=1`` specifies what new edges are
      licensed by a single existing edge.
    - A chart rule with ``NUM_EDGES=2`` specifies what new edges are
      licensed by a pair of existing edges.

    :type NUM_EDGES: int
    :cvar NUM_EDGES: The number of existing edges that this rule uses
        to license new edges.  Typically, this number ranges from zero
        to two.
    """

    def apply(self, chart, grammar, *edges):
        """
        Return a generator that will add edges licensed by this rule
        and the given edges to the chart, one at a time.  Each
        time the generator is resumed, it will either add a new
        edge and yield that edge; or return.

        :type edges: list(EdgeI)
        :param edges: A set of existing edges.  The number of edges
            that should be passed to ``apply()`` is specified by the
            ``NUM_EDGES`` class variable.
        :rtype: iter(EdgeI)
        """
        raise NotImplementedError()

    def apply_everywhere(self, chart, grammar):
        """
        Return a generator that will add all edges licensed by
        this rule, given the edges that are currently in the
        chart, one at a time.  Each time the generator is resumed,
        it will either add a new edge and yield that edge; or return.

        :rtype: iter(EdgeI)
        """
        raise NotImplementedError()


class AbstractChartRule(ChartRuleI):
    """
    An abstract base class for chart rules.  ``AbstractChartRule``
    provides:

    - A default implementation for ``apply``.
    - A default implementation for ``apply_everywhere``,
      (Currently, this implementation assumes that ``NUM_EDGES <= 3``.)
    - A default implementation for ``__str__``, which returns a
      name based on the rule's class name.
    """

    # Subclasses must define apply.
    def apply(self, chart, grammar, *edges):
        raise NotImplementedError()

    # Default: loop through the given number of edges, and call
    # self.apply() for each set of edges.
    def apply_everywhere(self, chart, grammar):
        if self.NUM_EDGES == 0:
            yield from self.apply(chart, grammar)

        elif self.NUM_EDGES == 1:
            for e1 in chart:
                yield from self.apply(chart, grammar, e1)

        elif self.NUM_EDGES == 2:
            for e1 in chart:
                for e2 in chart:
                    yield from self.apply(chart, grammar, e1, e2)

        elif self.NUM_EDGES == 3:
            for e1 in chart:
                for e2 in chart:
                    for e3 in chart:
                        yield from self.apply(chart, grammar, e1, e2, e3)

        else:
            raise AssertionError("NUM_EDGES>3 is not currently supported")

    # Default: return a name based on the class name.
    def __str__(self):
        # Add spaces between InitialCapsWords.
        return re.sub("([a-z])([A-Z])", r"\1 \2", self.__class__.__name__)


# ////////////////////////////////////////////////////////////
# Fundamental Rule
# ////////////////////////////////////////////////////////////


class FundamentalRule(AbstractChartRule):
    r"""
    A rule that joins two adjacent edges to form a single combined
    edge.  In particular, this rule specifies that any pair of edges

    - ``[A -> alpha \* B beta][i:j]``
    - ``[B -> gamma \*][j:k]``

    licenses the edge:

    - ``[A -> alpha B * beta][i:j]``
    """

    NUM_EDGES = 2

    def apply(self, chart, grammar, left_edge, right_edge):
        # Make sure the rule is applicable.
        if not (
            left_edge.is_incomplete()
            and right_edge.is_complete()
            and left_edge.end() == right_edge.start()
            and left_edge.nextsym() == right_edge.lhs()
        ):
            return

        # Construct the new edge.
        new_edge = left_edge.move_dot_forward(right_edge.end())

        # Insert it into the chart.
        if chart.insert_with_backpointer(new_edge, left_edge, right_edge):
            yield new_edge


class SingleEdgeFundamentalRule(FundamentalRule):
    r"""
    A rule that joins a given edge with adjacent edges in the chart,
    to form combined edges.  In particular, this rule specifies that
    either of the edges:

    - ``[A -> alpha \* B beta][i:j]``
    - ``[B -> gamma \*][j:k]``

    licenses the edge:

    - ``[A -> alpha B * beta][i:j]``

    if the other edge is already in the chart.

    :note: This is basically ``FundamentalRule``, with one edge left
        unspecified.
    """

    NUM_EDGES = 1

    def apply(self, chart, grammar, edge):
        if edge.is_incomplete():
            yield from self._apply_incomplete(chart, grammar, edge)
        else:
            yield from self._apply_complete(chart, grammar, edge)

    def _apply_complete(self, chart, grammar, right_edge):
        for left_edge in chart.select(
            end=right_edge.start(), is_complete=False, nextsym=right_edge.lhs()
        ):
            new_edge = left_edge.move_dot_forward(right_edge.end())
            if chart.insert_with_backpointer(new_edge, left_edge, right_edge):
                yield new_edge

    def _apply_incomplete(self, chart, grammar, left_edge):
        for right_edge in chart.select(
            start=left_edge.end(), is_complete=True, lhs=left_edge.nextsym()
        ):
            new_edge = left_edge.move_dot_forward(right_edge.end())
            if chart.insert_with_backpointer(new_edge, left_edge, right_edge):
                yield new_edge


# ////////////////////////////////////////////////////////////
# Inserting Terminal Leafs
# ////////////////////////////////////////////////////////////


class LeafInitRule(AbstractChartRule):
    NUM_EDGES = 0

    def apply(self, chart, grammar):
        for index in range(chart.num_leaves()):
            new_edge = LeafEdge(chart.leaf(index), index)
            if chart.insert(new_edge, ()):
                yield new_edge


# ////////////////////////////////////////////////////////////
# Top-Down Prediction
# ////////////////////////////////////////////////////////////


class TopDownInitRule(AbstractChartRule):
    r"""
    A rule licensing edges corresponding to the grammar productions for
    the grammar's start symbol.  In particular, this rule specifies that
    ``[S -> \* alpha][0:i]`` is licensed for each grammar production
    ``S -> alpha``, where ``S`` is the grammar's start symbol.
    """

    NUM_EDGES = 0

    def apply(self, chart, grammar):
        for prod in grammar.productions(lhs=grammar.start()):
            new_edge = TreeEdge.from_production(prod, 0)
            if chart.insert(new_edge, ()):
                yield new_edge


class TopDownPredictRule(AbstractChartRule):
    r"""
    A rule licensing edges corresponding to the grammar productions
    for the nonterminal following an incomplete edge's dot.  In
    particular, this rule specifies that
    ``[A -> alpha \* B beta][i:j]`` licenses the edge
    ``[B -> \* gamma][j:j]`` for each grammar production ``B -> gamma``.

    :note: This rule corresponds to the Predictor Rule in Earley parsing.
    """

    NUM_EDGES = 1

    def apply(self, chart, grammar, edge):
        if edge.is_complete():
            return
        for prod in grammar.productions(lhs=edge.nextsym()):
            new_edge = TreeEdge.from_production(prod, edge.end())
            if chart.insert(new_edge, ()):
                yield new_edge


class CachedTopDownPredictRule(TopDownPredictRule):
    r"""
    A cached version of ``TopDownPredictRule``.  After the first time
    this rule is applied to an edge with a given ``end`` and ``next``,
    it will not generate any more edges for edges with that ``end`` and
    ``next``.

    If ``chart`` or ``grammar`` are changed, then the cache is flushed.
    """

    def __init__(self):
        TopDownPredictRule.__init__(self)
        self._done = {}

    def apply(self, chart, grammar, edge):
        if edge.is_complete():
            return
        nextsym, index = edge.nextsym(), edge.end()
        if not is_nonterminal(nextsym):
            return

        # If we've already applied this rule to an edge with the same
        # next & end, and the chart & grammar have not changed, then
        # just return (no new edges to add).
        done = self._done.get((nextsym, index), (None, None))
        if done[0] is chart and done[1] is grammar:
            return

        # Add all the edges indicated by the top down expand rule.
        for prod in grammar.productions(lhs=nextsym):
            # If the left corner in the predicted production is
            # leaf, it must match with the input.
            if prod.rhs():
                first = prod.rhs()[0]
                if is_terminal(first):
                    if index >= chart.num_leaves() or first != chart.leaf(index):
                        continue

            new_edge = TreeEdge.from_production(prod, index)
            if chart.insert(new_edge, ()):
                yield new_edge

        # Record the fact that we've applied this rule.
        self._done[nextsym, index] = (chart, grammar)


# ////////////////////////////////////////////////////////////
# Bottom-Up Prediction
# ////////////////////////////////////////////////////////////


class BottomUpPredictRule(AbstractChartRule):
    r"""
    A rule licensing any edge corresponding to a production whose
    right-hand side begins with a complete edge's left-hand side.  In
    particular, this rule specifies that ``[A -> alpha \*]`` licenses
    the edge ``[B -> \* A beta]`` for each grammar production ``B -> A beta``.
    """

    NUM_EDGES = 1

    def apply(self, chart, grammar, edge):
        if edge.is_incomplete():
            return
        for prod in grammar.productions(rhs=edge.lhs()):
            new_edge = TreeEdge.from_production(prod, edge.start())
            if chart.insert(new_edge, ()):
                yield new_edge


class BottomUpPredictCombineRule(BottomUpPredictRule):
    r"""
    A rule licensing any edge corresponding to a production whose
    right-hand side begins with a complete edge's left-hand side.  In
    particular, this rule specifies that ``[A -> alpha \*]``
    licenses the edge ``[B -> A \* beta]`` for each grammar
    production ``B -> A beta``.

    :note: This is like ``BottomUpPredictRule``, but it also applies
        the ``FundamentalRule`` to the resulting edge.
    """

    NUM_EDGES = 1

    def apply(self, chart, grammar, edge):
        if edge.is_incomplete():
            return
        for prod in grammar.productions(rhs=edge.lhs()):
            new_edge = TreeEdge(edge.span(), prod.lhs(), prod.rhs(), 1)
            if chart.insert(new_edge, (edge,)):
                yield new_edge


class EmptyPredictRule(AbstractChartRule):
    """
    A rule that inserts all empty productions as passive edges,
    in every position in the chart.
    """

    NUM_EDGES = 0

    def apply(self, chart, grammar):
        for prod in grammar.productions(empty=True):
            for index in range(chart.num_leaves() + 1):
                new_edge = TreeEdge.from_production(prod, index)
                if chart.insert(new_edge, ()):
                    yield new_edge


########################################################################
##  Filtered Bottom Up
########################################################################


class FilteredSingleEdgeFundamentalRule(SingleEdgeFundamentalRule):
    def _apply_complete(self, chart, grammar, right_edge):
        end = right_edge.end()
        nexttoken = end < chart.num_leaves() and chart.leaf(end)
        for left_edge in chart.select(
            end=right_edge.start(), is_complete=False, nextsym=right_edge.lhs()
        ):
            if _bottomup_filter(grammar, nexttoken, left_edge.rhs(), left_edge.dot()):
                new_edge = left_edge.move_dot_forward(right_edge.end())
                if chart.insert_with_backpointer(new_edge, left_edge, right_edge):
                    yield new_edge

    def _apply_incomplete(self, chart, grammar, left_edge):
        for right_edge in chart.select(
            start=left_edge.end(), is_complete=True, lhs=left_edge.nextsym()
        ):
            end = right_edge.end()
            nexttoken = end < chart.num_leaves() and chart.leaf(end)
            if _bottomup_filter(grammar, nexttoken, left_edge.rhs(), left_edge.dot()):
                new_edge = left_edge.move_dot_forward(right_edge.end())
                if chart.insert_with_backpointer(new_edge, left_edge, right_edge):
                    yield new_edge


class FilteredBottomUpPredictCombineRule(BottomUpPredictCombineRule):
    def apply(self, chart, grammar, edge):
        if edge.is_incomplete():
            return

        end = edge.end()
        nexttoken = end < chart.num_leaves() and chart.leaf(end)
        for prod in grammar.productions(rhs=edge.lhs()):
            if _bottomup_filter(grammar, nexttoken, prod.rhs()):
                new_edge = TreeEdge(edge.span(), prod.lhs(), prod.rhs(), 1)
                if chart.insert(new_edge, (edge,)):
                    yield new_edge


def _bottomup_filter(grammar, nexttoken, rhs, dot=0):
    if len(rhs) <= dot + 1:
        return True
    _next = rhs[dot + 1]
    if is_terminal(_next):
        return nexttoken == _next
    else:
        return grammar.is_leftcorner(_next, nexttoken)


########################################################################
##  Generic Chart Parser
########################################################################

TD_STRATEGY = [
    LeafInitRule(),
    TopDownInitRule(),
    CachedTopDownPredictRule(),
    SingleEdgeFundamentalRule(),
]
BU_STRATEGY = [
    LeafInitRule(),
    EmptyPredictRule(),
    BottomUpPredictRule(),
    SingleEdgeFundamentalRule(),
]
BU_LC_STRATEGY = [
    LeafInitRule(),
    EmptyPredictRule(),
    BottomUpPredictCombineRule(),
    SingleEdgeFundamentalRule(),
]

LC_STRATEGY = [
    LeafInitRule(),
    FilteredBottomUpPredictCombineRule(),
    FilteredSingleEdgeFundamentalRule(),
]


class ChartParser(ParserI):
    """
    A generic chart parser.  A "strategy", or list of
    ``ChartRuleI`` instances, is used to decide what edges to add to
    the chart.  In particular, ``ChartParser`` uses the following
    algorithm to parse texts:

    | Until no new edges are added:
    |   For each *rule* in *strategy*:
    |     Apply *rule* to any applicable edges in the chart.
    | Return any complete parses in the chart
    """

    def __init__(
        self,
        grammar,
        strategy=BU_LC_STRATEGY,
        trace=0,
        trace_chart_width=50,
        use_agenda=True,
        chart_class=Chart,
    ):
        """
        Create a new chart parser, that uses ``grammar`` to parse
        texts.

        :type grammar: CFG
        :param grammar: The grammar used to parse texts.
        :type strategy: list(ChartRuleI)
        :param strategy: A list of rules that should be used to decide
            what edges to add to the chart (top-down strategy by default).
        :type trace: int
        :param trace: The level of tracing that should be used when
            parsing a text.  ``0`` will generate no tracing output;
            and higher numbers will produce more verbose tracing
            output.
        :type trace_chart_width: int
        :param trace_chart_width: The default total width reserved for
            the chart in trace output.  The remainder of each line will
            be used to display edges.
        :type use_agenda: bool
        :param use_agenda: Use an optimized agenda-based algorithm,
            if possible.
        :param chart_class: The class that should be used to create
            the parse charts.
        """
        self._grammar = grammar
        self._strategy = strategy
        self._trace = trace
        self._trace_chart_width = trace_chart_width
        # If the strategy only consists of axioms (NUM_EDGES==0) and
        # inference rules (NUM_EDGES==1), we can use an agenda-based algorithm:
        self._use_agenda = use_agenda
        self._chart_class = chart_class

        self._axioms = []
        self._inference_rules = []
        for rule in strategy:
            if rule.NUM_EDGES == 0:
                self._axioms.append(rule)
            elif rule.NUM_EDGES == 1:
                self._inference_rules.append(rule)
            else:
                self._use_agenda = False

    def grammar(self):
        return self._grammar

    def _trace_new_edges(self, chart, rule, new_edges, trace, edge_width):
        if not trace:
            return
        print_rule_header = trace > 1
        for edge in new_edges:
            if print_rule_header:
                print("%s:" % rule)
                print_rule_header = False
            print(chart.pretty_format_edge(edge, edge_width))

    def chart_parse(self, tokens, trace=None):
        """
        Return the final parse ``Chart`` from which all possible
        parse trees can be extracted.

        :param tokens: The sentence to be parsed
        :type tokens: list(str)
        :rtype: Chart
        """
        if trace is None:
            trace = self._trace
        trace_new_edges = self._trace_new_edges

        tokens = list(tokens)
        self._grammar.check_coverage(tokens)
        chart = self._chart_class(tokens)
        grammar = self._grammar

        # Width, for printing trace edges.
        trace_edge_width = self._trace_chart_width // (chart.num_leaves() + 1)
        if trace:
            print(chart.pretty_format_leaves(trace_edge_width))

        if self._use_agenda:
            # Use an agenda-based algorithm.
            for axiom in self._axioms:
                new_edges = list(axiom.apply(chart, grammar))
                trace_new_edges(chart, axiom, new_edges, trace, trace_edge_width)

            inference_rules = self._inference_rules
            agenda = chart.edges()
            # We reverse the initial agenda, since it is a stack
            # but chart.edges() functions as a queue.
            agenda.reverse()
            while agenda:
                edge = agenda.pop()
                for rule in inference_rules:
                    new_edges = list(rule.apply(chart, grammar, edge))
                    if trace:
                        trace_new_edges(chart, rule, new_edges, trace, trace_edge_width)
                    agenda += new_edges

        else:
            # Do not use an agenda-based algorithm.
            edges_added = True
            while edges_added:
                edges_added = False
                for rule in self._strategy:
                    new_edges = list(rule.apply_everywhere(chart, grammar))
                    edges_added = len(new_edges)
                    trace_new_edges(chart, rule, new_edges, trace, trace_edge_width)

        # Return the final chart.
        return chart

    def parse(self, tokens, tree_class=Tree):
        chart = self.chart_parse(tokens)
        return iter(chart.parses(self._grammar.start(), tree_class=tree_class))


class TopDownChartParser(ChartParser):
    """
    A ``ChartParser`` using a top-down parsing strategy.
    See ``ChartParser`` for more information.
    """

    def __init__(self, grammar, **parser_args):
        ChartParser.__init__(self, grammar, TD_STRATEGY, **parser_args)


class BottomUpChartParser(ChartParser):
    """
    A ``ChartParser`` using a bottom-up parsing strategy.
    See ``ChartParser`` for more information.
    """

    def __init__(self, grammar, **parser_args):
        if isinstance(grammar, PCFG):
            warnings.warn(
                "BottomUpChartParser only works for CFG, "
                "use BottomUpProbabilisticChartParser instead",
                category=DeprecationWarning,
            )
        ChartParser.__init__(self, grammar, BU_STRATEGY, **parser_args)


class BottomUpLeftCornerChartParser(ChartParser):
    """
    A ``ChartParser`` using a bottom-up left-corner parsing strategy.
    This strategy is often more efficient than standard bottom-up.
    See ``ChartParser`` for more information.
    """

    def __init__(self, grammar, **parser_args):
        ChartParser.__init__(self, grammar, BU_LC_STRATEGY, **parser_args)


class LeftCornerChartParser(ChartParser):
    def __init__(self, grammar, **parser_args):
        if not grammar.is_nonempty():
            raise ValueError(
                "LeftCornerParser only works for grammars " "without empty productions."
            )
        ChartParser.__init__(self, grammar, LC_STRATEGY, **parser_args)


########################################################################
##  Stepping Chart Parser
########################################################################


class SteppingChartParser(ChartParser):
    """
    A ``ChartParser`` that allows you to step through the parsing
    process, adding a single edge at a time.  It also allows you to
    change the parser's strategy or grammar midway through parsing a
    text.

    The ``initialize`` method is used to start parsing a text.  ``step``
    adds a single edge to the chart.  ``set_strategy`` changes the
    strategy used by the chart parser.  ``parses`` returns the set of
    parses that has been found by the chart parser.

    :ivar _restart: Records whether the parser's strategy, grammar,
        or chart has been changed.  If so, then ``step`` must restart
        the parsing algorithm.
    """

    def __init__(self, grammar, strategy=[], trace=0):
        self._chart = None
        self._current_chartrule = None
        self._restart = False
        ChartParser.__init__(self, grammar, strategy, trace)

    # ////////////////////////////////////////////////////////////
    # Initialization
    # ////////////////////////////////////////////////////////////

    def initialize(self, tokens):
        "Begin parsing the given tokens."
        self._chart = Chart(list(tokens))
        self._restart = True

    # ////////////////////////////////////////////////////////////
    # Stepping
    # ////////////////////////////////////////////////////////////

    def step(self):
        """
        Return a generator that adds edges to the chart, one at a
        time.  Each time the generator is resumed, it adds a single
        edge and yields that edge.  If no more edges can be added,
        then it yields None.

        If the parser's strategy, grammar, or chart is changed, then
        the generator will continue adding edges using the new
        strategy, grammar, or chart.

        Note that this generator never terminates, since the grammar
        or strategy might be changed to values that would add new
        edges.  Instead, it yields None when no more edges can be
        added with the current strategy and grammar.
        """
        if self._chart is None:
            raise ValueError("Parser must be initialized first")
        while True:
            self._restart = False
            w = 50 // (self._chart.num_leaves() + 1)

            for e in self._parse():
                if self._trace > 1:
                    print(self._current_chartrule)
                if self._trace > 0:
                    print(self._chart.pretty_format_edge(e, w))
                yield e
                if self._restart:
                    break
            else:
                yield None  # No more edges.

    def _parse(self):
        """
        A generator that implements the actual parsing algorithm.
        ``step`` iterates through this generator, and restarts it
        whenever the parser's strategy, grammar, or chart is modified.
        """
        chart = self._chart
        grammar = self._grammar
        edges_added = 1
        while edges_added > 0:
            edges_added = 0
            for rule in self._strategy:
                self._current_chartrule = rule
                for e in rule.apply_everywhere(chart, grammar):
                    edges_added += 1
                    yield e

    # ////////////////////////////////////////////////////////////
    # Accessors
    # ////////////////////////////////////////////////////////////

    def strategy(self):
        "Return the strategy used by this parser."
        return self._strategy

    def grammar(self):
        "Return the grammar used by this parser."
        return self._grammar

    def chart(self):
        "Return the chart that is used by this parser."
        return self._chart

    def current_chartrule(self):
        "Return the chart rule used to generate the most recent edge."
        return self._current_chartrule

    def parses(self, tree_class=Tree):
        "Return the parse trees currently contained in the chart."
        return self._chart.parses(self._grammar.start(), tree_class)

    # ////////////////////////////////////////////////////////////
    # Parser modification
    # ////////////////////////////////////////////////////////////

    def set_strategy(self, strategy):
        """
        Change the strategy that the parser uses to decide which edges
        to add to the chart.

        :type strategy: list(ChartRuleI)
        :param strategy: A list of rules that should be used to decide
            what edges to add to the chart.
        """
        if strategy == self._strategy:
            return
        self._strategy = strategy[:]  # Make a copy.
        self._restart = True

    def set_grammar(self, grammar):
        "Change the grammar used by the parser."
        if grammar is self._grammar:
            return
        self._grammar = grammar
        self._restart = True

    def set_chart(self, chart):
        "Load a given chart into the chart parser."
        if chart is self._chart:
            return
        self._chart = chart
        self._restart = True

    # ////////////////////////////////////////////////////////////
    # Standard parser methods
    # ////////////////////////////////////////////////////////////

    def parse(self, tokens, tree_class=Tree):
        tokens = list(tokens)
        self._grammar.check_coverage(tokens)

        # Initialize ourselves.
        self.initialize(tokens)

        # Step until no more edges are generated.
        for e in self.step():
            if e is None:
                break

        # Return an iterator of complete parses.
        return self.parses(tree_class=tree_class)


########################################################################
##  Demo Code
########################################################################


def demo_grammar():
    from nltk.grammar import CFG

    return CFG.fromstring(
        """
S  -> NP VP
PP -> "with" NP
NP -> NP PP
VP -> VP PP
VP -> Verb NP
VP -> Verb
NP -> Det Noun
NP -> "John"
NP -> "I"
Det -> "the"
Det -> "my"
Det -> "a"
Noun -> "dog"
Noun -> "cookie"
Verb -> "ate"
Verb -> "saw"
Prep -> "with"
Prep -> "under"
"""
    )


def demo(
    choice=None,
    print_times=True,
    print_grammar=False,
    print_trees=True,
    trace=2,
    sent="I saw John with a dog with my cookie",
    numparses=5,
):
    """
    A demonstration of the chart parsers.
    """
    import sys
    import time

    from nltk import CFG, Production, nonterminals

    # The grammar for ChartParser and SteppingChartParser:
    grammar = demo_grammar()
    if print_grammar:
        print("* Grammar")
        print(grammar)

    # Tokenize the sample sentence.
    print("* Sentence:")
    print(sent)
    tokens = sent.split()
    print(tokens)
    print()

    # Ask the user which parser to test,
    # if the parser wasn't provided as an argument
    if choice is None:
        print("  1: Top-down chart parser")
        print("  2: Bottom-up chart parser")
        print("  3: Bottom-up left-corner chart parser")
        print("  4: Left-corner chart parser with bottom-up filter")
        print("  5: Stepping chart parser (alternating top-down & bottom-up)")
        print("  6: All parsers")
        print("\nWhich parser (1-6)? ", end=" ")
        choice = sys.stdin.readline().strip()
        print()

    choice = str(choice)
    if choice not in "123456":
        print("Bad parser number")
        return

    # Keep track of how long each parser takes.
    times = {}

    strategies = {
        "1": ("Top-down", TD_STRATEGY),
        "2": ("Bottom-up", BU_STRATEGY),
        "3": ("Bottom-up left-corner", BU_LC_STRATEGY),
        "4": ("Filtered left-corner", LC_STRATEGY),
    }
    choices = []
    if choice in strategies:
        choices = [choice]
    if choice == "6":
        choices = "1234"

    # Run the requested chart parser(s), except the stepping parser.
    for strategy in choices:
        print("* Strategy: " + strategies[strategy][0])
        print()
        cp = ChartParser(grammar, strategies[strategy][1], trace=trace)
        t = time.time()
        chart = cp.chart_parse(tokens)
        parses = list(chart.parses(grammar.start()))

        times[strategies[strategy][0]] = time.time() - t
        print("Nr edges in chart:", len(chart.edges()))
        if numparses:
            assert len(parses) == numparses, "Not all parses found"
        if print_trees:
            for tree in parses:
                print(tree)
        else:
            print("Nr trees:", len(parses))
        print()

    # Run the stepping parser, if requested.
    if choice in "56":
        print("* Strategy: Stepping (top-down vs bottom-up)")
        print()
        t = time.time()
        cp = SteppingChartParser(grammar, trace=trace)
        cp.initialize(tokens)
        for i in range(5):
            print("*** SWITCH TO TOP DOWN")
            cp.set_strategy(TD_STRATEGY)
            for j, e in enumerate(cp.step()):
                if j > 20 or e is None:
                    break
            print("*** SWITCH TO BOTTOM UP")
            cp.set_strategy(BU_STRATEGY)
            for j, e in enumerate(cp.step()):
                if j > 20 or e is None:
                    break
        times["Stepping"] = time.time() - t
        print("Nr edges in chart:", len(cp.chart().edges()))
        if numparses:
            assert len(list(cp.parses())) == numparses, "Not all parses found"
        if print_trees:
            for tree in cp.parses():
                print(tree)
        else:
            print("Nr trees:", len(list(cp.parses())))
        print()

    # Print the times of all parsers:
    if not (print_times and times):
        return
    print("* Parsing times")
    print()
    maxlen = max(len(key) for key in times)
    format = "%" + repr(maxlen) + "s parser: %6.3fsec"
    times_items = times.items()
    for parser, t in sorted(times_items, key=lambda a: a[1]):
        print(format % (parser, t))


if __name__ == "__main__":
    demo()

# === NexusCore/openenv\Lib\site-packages\matplotlib\dates.py ===
"""
Matplotlib provides sophisticated date plotting capabilities, standing on the
shoulders of python :mod:`datetime` and the add-on module dateutil_.

By default, Matplotlib uses the units machinery described in
`~matplotlib.units` to convert `datetime.datetime`, and `numpy.datetime64`
objects when plotted on an x- or y-axis. The user does not
need to do anything for dates to be formatted, but dates often have strict
formatting needs, so this module provides many tick locators and formatters.
A basic example using `numpy.datetime64` is::

    import numpy as np

    times = np.arange(np.datetime64('2001-01-02'),
                      np.datetime64('2002-02-03'), np.timedelta64(75, 'm'))
    y = np.random.randn(len(times))

    fig, ax = plt.subplots()
    ax.plot(times, y)

.. seealso::

    - :doc:`/gallery/text_labels_and_annotations/date`
    - :doc:`/gallery/ticks/date_concise_formatter`
    - :doc:`/gallery/ticks/date_demo_convert`

.. _date-format:

Matplotlib date format
----------------------

Matplotlib represents dates using floating point numbers specifying the number
of days since a default epoch of 1970-01-01 UTC; for example,
1970-01-01, 06:00 is the floating point number 0.25. The formatters and
locators require the use of `datetime.datetime` objects, so only dates between
year 0001 and 9999 can be represented.  Microsecond precision
is achievable for (approximately) 70 years on either side of the epoch, and
20 microseconds for the rest of the allowable range of dates (year 0001 to
9999). The epoch can be changed at import time via `.dates.set_epoch` or
:rc:`date.epoch` to other dates if necessary; see
:doc:`/gallery/ticks/date_precision_and_epochs` for a discussion.

.. note::

   Before Matplotlib 3.3, the epoch was 0000-12-31 which lost modern
   microsecond precision and also made the default axis limit of 0 an invalid
   datetime.  In 3.3 the epoch was changed as above.  To convert old
   ordinal floats to the new epoch, users can do::

     new_ordinal = old_ordinal + mdates.date2num(np.datetime64('0000-12-31'))


There are a number of helper functions to convert between :mod:`datetime`
objects and Matplotlib dates:

.. currentmodule:: matplotlib.dates

.. autosummary::
   :nosignatures:

   datestr2num
   date2num
   num2date
   num2timedelta
   drange
   set_epoch
   get_epoch

.. note::

   Like Python's `datetime.datetime`, Matplotlib uses the Gregorian calendar
   for all conversions between dates and floating point numbers. This practice
   is not universal, and calendar differences can cause confusing
   differences between what Python and Matplotlib give as the number of days
   since 0001-01-01 and what other software and databases yield.  For
   example, the US Naval Observatory uses a calendar that switches
   from Julian to Gregorian in October, 1582.  Hence, using their
   calculator, the number of days between 0001-01-01 and 2006-04-01 is
   732403, whereas using the Gregorian calendar via the datetime
   module we find::

     In [1]: date(2006, 4, 1).toordinal() - date(1, 1, 1).toordinal()
     Out[1]: 732401

All the Matplotlib date converters, locators and formatters are timezone aware.
If no explicit timezone is provided, :rc:`timezone` is assumed, provided as a
string.  If you want to use a different timezone, pass the *tz* keyword
argument of `num2date` to any date tick locators or formatters you create. This
can be either a `datetime.tzinfo` instance or a string with the timezone name
that can be parsed by `~dateutil.tz.gettz`.

A wide range of specific and general purpose date tick locators and
formatters are provided in this module.  See
:mod:`matplotlib.ticker` for general information on tick locators
and formatters.  These are described below.

The dateutil_ module provides additional code to handle date ticking, making it
easy to place ticks on any kinds of dates.  See examples below.

.. _dateutil: https://dateutil.readthedocs.io

.. _date-locators:

Date tick locators
------------------

Most of the date tick locators can locate single or multiple ticks. For example::

    # import constants for the days of the week
    from matplotlib.dates import MO, TU, WE, TH, FR, SA, SU

    # tick on Mondays every week
    loc = WeekdayLocator(byweekday=MO, tz=tz)

    # tick on Mondays and Saturdays
    loc = WeekdayLocator(byweekday=(MO, SA))

In addition, most of the constructors take an interval argument::

    # tick on Mondays every second week
    loc = WeekdayLocator(byweekday=MO, interval=2)

The rrule locator allows completely general date ticking::

    # tick every 5th easter
    rule = rrulewrapper(YEARLY, byeaster=1, interval=5)
    loc = RRuleLocator(rule)

The available date tick locators are:

* `MicrosecondLocator`: Locate microseconds.

* `SecondLocator`: Locate seconds.

* `MinuteLocator`: Locate minutes.

* `HourLocator`: Locate hours.

* `DayLocator`: Locate specified days of the month.

* `WeekdayLocator`: Locate days of the week, e.g., MO, TU.

* `MonthLocator`: Locate months, e.g., 7 for July.

* `YearLocator`: Locate years that are multiples of base.

* `RRuleLocator`: Locate using a `rrulewrapper`.
  `rrulewrapper` is a simple wrapper around dateutil_'s `dateutil.rrule`
  which allow almost arbitrary date tick specifications.
  See :doc:`rrule example </gallery/ticks/date_demo_rrule>`.

* `AutoDateLocator`: On autoscale, this class picks the best `DateLocator`
  (e.g., `RRuleLocator`) to set the view limits and the tick locations.  If
  called with ``interval_multiples=True`` it will make ticks line up with
  sensible multiples of the tick intervals.  For example, if the interval is
  4 hours, it will pick hours 0, 4, 8, etc. as ticks.  This behaviour is not
  guaranteed by default.

.. _date-formatters:

Date formatters
---------------

The available date formatters are:

* `AutoDateFormatter`: attempts to figure out the best format to use.  This is
  most useful when used with the `AutoDateLocator`.

* `ConciseDateFormatter`: also attempts to figure out the best format to use,
  and to make the format as compact as possible while still having complete
  date information.  This is most useful when used with the `AutoDateLocator`.

* `DateFormatter`: use `~datetime.datetime.strftime` format strings.
"""

import datetime
import functools
import logging
import re

from dateutil.rrule import (rrule, MO, TU, WE, TH, FR, SA, SU, YEARLY,
                            MONTHLY, WEEKLY, DAILY, HOURLY, MINUTELY,
                            SECONDLY)
from dateutil.relativedelta import relativedelta
import dateutil.parser
import dateutil.tz
import numpy as np

import matplotlib as mpl
from matplotlib import _api, cbook, ticker, units

__all__ = ('datestr2num', 'date2num', 'num2date', 'num2timedelta', 'drange',
           'set_epoch', 'get_epoch', 'DateFormatter', 'ConciseDateFormatter',
           'AutoDateFormatter', 'DateLocator', 'RRuleLocator',
           'AutoDateLocator', 'YearLocator', 'MonthLocator', 'WeekdayLocator',
           'DayLocator', 'HourLocator', 'MinuteLocator',
           'SecondLocator', 'MicrosecondLocator',
           'rrule', 'MO', 'TU', 'WE', 'TH', 'FR', 'SA', 'SU',
           'YEARLY', 'MONTHLY', 'WEEKLY', 'DAILY',
           'HOURLY', 'MINUTELY', 'SECONDLY', 'MICROSECONDLY', 'relativedelta',
           'DateConverter', 'ConciseDateConverter', 'rrulewrapper')


_log = logging.getLogger(__name__)
UTC = datetime.timezone.utc


def _get_tzinfo(tz=None):
    """
    Generate `~datetime.tzinfo` from a string or return `~datetime.tzinfo`.
    If None, retrieve the preferred timezone from the rcParams dictionary.
    """
    tz = mpl._val_or_rc(tz, 'timezone')
    if tz == 'UTC':
        return UTC
    if isinstance(tz, str):
        tzinfo = dateutil.tz.gettz(tz)
        if tzinfo is None:
            raise ValueError(f"{tz} is not a valid timezone as parsed by"
                             " dateutil.tz.gettz.")
        return tzinfo
    if isinstance(tz, datetime.tzinfo):
        return tz
    raise TypeError(f"tz must be string or tzinfo subclass, not {tz!r}.")


# Time-related constants.
EPOCH_OFFSET = float(datetime.datetime(1970, 1, 1).toordinal())
# EPOCH_OFFSET is not used by matplotlib
MICROSECONDLY = SECONDLY + 1
HOURS_PER_DAY = 24.
MIN_PER_HOUR = 60.
SEC_PER_MIN = 60.
MONTHS_PER_YEAR = 12.

DAYS_PER_WEEK = 7.
DAYS_PER_MONTH = 30.
DAYS_PER_YEAR = 365.0

MINUTES_PER_DAY = MIN_PER_HOUR * HOURS_PER_DAY

SEC_PER_HOUR = SEC_PER_MIN * MIN_PER_HOUR
SEC_PER_DAY = SEC_PER_HOUR * HOURS_PER_DAY
SEC_PER_WEEK = SEC_PER_DAY * DAYS_PER_WEEK

MUSECONDS_PER_DAY = 1e6 * SEC_PER_DAY

MONDAY, TUESDAY, WEDNESDAY, THURSDAY, FRIDAY, SATURDAY, SUNDAY = (
    MO, TU, WE, TH, FR, SA, SU)
WEEKDAYS = (MONDAY, TUESDAY, WEDNESDAY, THURSDAY, FRIDAY, SATURDAY, SUNDAY)

# default epoch: passed to np.datetime64...
_epoch = None


def _reset_epoch_test_example():
    """
    Reset the Matplotlib date epoch so it can be set again.

    Only for use in tests and examples.
    """
    global _epoch
    _epoch = None


def set_epoch(epoch):
    """
    Set the epoch (origin for dates) for datetime calculations.

    The default epoch is :rc:`date.epoch`.

    If microsecond accuracy is desired, the date being plotted needs to be
    within approximately 70 years of the epoch. Matplotlib internally
    represents dates as days since the epoch, so floating point dynamic
    range needs to be within a factor of 2^52.

    `~.dates.set_epoch` must be called before any dates are converted
    (i.e. near the import section) or a RuntimeError will be raised.

    See also :doc:`/gallery/ticks/date_precision_and_epochs`.

    Parameters
    ----------
    epoch : str
        valid UTC date parsable by `numpy.datetime64` (do not include
        timezone).

    """
    global _epoch
    if _epoch is not None:
        raise RuntimeError('set_epoch must be called before dates plotted.')
    _epoch = epoch


def get_epoch():
    """
    Get the epoch used by `.dates`.

    Returns
    -------
    epoch : str
        String for the epoch (parsable by `numpy.datetime64`).
    """
    global _epoch

    _epoch = mpl._val_or_rc(_epoch, 'date.epoch')
    return _epoch


def _dt64_to_ordinalf(d):
    """
    Convert `numpy.datetime64` or an `numpy.ndarray` of those types to
    Gregorian date as UTC float relative to the epoch (see `.get_epoch`).
    Roundoff is float64 precision.  Practically: microseconds for dates
    between 290301 BC, 294241 AD, milliseconds for larger dates
    (see `numpy.datetime64`).
    """

    # the "extra" ensures that we at least allow the dynamic range out to
    # seconds.  That should get out to +/-2e11 years.
    dseconds = d.astype('datetime64[s]')
    extra = (d - dseconds).astype('timedelta64[ns]')
    t0 = np.datetime64(get_epoch(), 's')
    dt = (dseconds - t0).astype(np.float64)
    dt += extra.astype(np.float64) / 1.0e9
    dt = dt / SEC_PER_DAY

    NaT_int = np.datetime64('NaT').astype(np.int64)
    d_int = d.astype(np.int64)
    dt[d_int == NaT_int] = np.nan
    return dt


def _from_ordinalf(x, tz=None):
    """
    Convert Gregorian float of the date, preserving hours, minutes,
    seconds and microseconds.  Return value is a `.datetime`.

    The input date *x* is a float in ordinal days at UTC, and the output will
    be the specified `.datetime` object corresponding to that time in
    timezone *tz*, or if *tz* is ``None``, in the timezone specified in
    :rc:`timezone`.
    """

    tz = _get_tzinfo(tz)

    dt = (np.datetime64(get_epoch()) +
          np.timedelta64(int(np.round(x * MUSECONDS_PER_DAY)), 'us'))
    if dt < np.datetime64('0001-01-01') or dt >= np.datetime64('10000-01-01'):
        raise ValueError(f'Date ordinal {x} converts to {dt} (using '
                         f'epoch {get_epoch()}), but Matplotlib dates must be '
                          'between year 0001 and 9999.')
    # convert from datetime64 to datetime:
    dt = dt.tolist()

    # datetime64 is always UTC:
    dt = dt.replace(tzinfo=dateutil.tz.gettz('UTC'))
    # but maybe we are working in a different timezone so move.
    dt = dt.astimezone(tz)
    # fix round off errors
    if np.abs(x) > 70 * 365:
        # if x is big, round off to nearest twenty microseconds.
        # This avoids floating point roundoff error
        ms = round(dt.microsecond / 20) * 20
        if ms == 1000000:
            dt = dt.replace(microsecond=0) + datetime.timedelta(seconds=1)
        else:
            dt = dt.replace(microsecond=ms)

    return dt


# a version of _from_ordinalf that can operate on numpy arrays
_from_ordinalf_np_vectorized = np.vectorize(_from_ordinalf, otypes="O")
# a version of dateutil.parser.parse that can operate on numpy arrays
_dateutil_parser_parse_np_vectorized = np.vectorize(dateutil.parser.parse)


def datestr2num(d, default=None):
    """
    Convert a date string to a datenum using `dateutil.parser.parse`.

    Parameters
    ----------
    d : str or sequence of str
        The dates to convert.

    default : datetime.datetime, optional
        The default date to use when fields are missing in *d*.
    """
    if isinstance(d, str):
        dt = dateutil.parser.parse(d, default=default)
        return date2num(dt)
    else:
        if default is not None:
            d = [date2num(dateutil.parser.parse(s, default=default))
                 for s in d]
            return np.asarray(d)
        d = np.asarray(d)
        if not d.size:
            return d
        return date2num(_dateutil_parser_parse_np_vectorized(d))


def date2num(d):
    """
    Convert datetime objects to Matplotlib dates.

    Parameters
    ----------
    d : `datetime.datetime` or `numpy.datetime64` or sequences of these

    Returns
    -------
    float or sequence of floats
        Number of days since the epoch.  See `.get_epoch` for the
        epoch, which can be changed by :rc:`date.epoch` or `.set_epoch`.  If
        the epoch is "1970-01-01T00:00:00" (default) then noon Jan 1 1970
        ("1970-01-01T12:00:00") returns 0.5.

    Notes
    -----
    The Gregorian calendar is assumed; this is not universal practice.
    For details see the module docstring.
    """
    # Unpack in case of e.g. Pandas or xarray object
    d = cbook._unpack_to_numpy(d)

    # make an iterable, but save state to unpack later:
    iterable = np.iterable(d)
    if not iterable:
        d = [d]

    masked = np.ma.is_masked(d)
    mask = np.ma.getmask(d)
    d = np.asarray(d)

    # convert to datetime64 arrays, if not already:
    if not np.issubdtype(d.dtype, np.datetime64):
        # datetime arrays
        if not d.size:
            # deals with an empty array...
            return d
        tzi = getattr(d[0], 'tzinfo', None)
        if tzi is not None:
            # make datetime naive:
            d = [dt.astimezone(UTC).replace(tzinfo=None) for dt in d]
            d = np.asarray(d)
        d = d.astype('datetime64[us]')

    d = np.ma.masked_array(d, mask=mask) if masked else d
    d = _dt64_to_ordinalf(d)

    return d if iterable else d[0]


def num2date(x, tz=None):
    """
    Convert Matplotlib dates to `~datetime.datetime` objects.

    Parameters
    ----------
    x : float or sequence of floats
        Number of days (fraction part represents hours, minutes, seconds)
        since the epoch.  See `.get_epoch` for the
        epoch, which can be changed by :rc:`date.epoch` or `.set_epoch`.
    tz : str or `~datetime.tzinfo`, default: :rc:`timezone`
        Timezone of *x*. If a string, *tz* is passed to `dateutil.tz`.

    Returns
    -------
    `~datetime.datetime` or sequence of `~datetime.datetime`
        Dates are returned in timezone *tz*.

        If *x* is a sequence, a sequence of `~datetime.datetime` objects will
        be returned.

    Notes
    -----
    The Gregorian calendar is assumed; this is not universal practice.
    For details, see the module docstring.
    """
    tz = _get_tzinfo(tz)
    return _from_ordinalf_np_vectorized(x, tz).tolist()


_ordinalf_to_timedelta_np_vectorized = np.vectorize(
    lambda x: datetime.timedelta(days=x), otypes="O")


def num2timedelta(x):
    """
    Convert number of days to a `~datetime.timedelta` object.

    If *x* is a sequence, a sequence of `~datetime.timedelta` objects will
    be returned.

    Parameters
    ----------
    x : float, sequence of floats
        Number of days. The fraction part represents hours, minutes, seconds.

    Returns
    -------
    `datetime.timedelta` or list[`datetime.timedelta`]
    """
    return _ordinalf_to_timedelta_np_vectorized(x).tolist()


def drange(dstart, dend, delta):
    """
    Return a sequence of equally spaced Matplotlib dates.

    The dates start at *dstart* and reach up to, but not including *dend*.
    They are spaced by *delta*.

    Parameters
    ----------
    dstart, dend : `~datetime.datetime`
        The date limits.
    delta : `datetime.timedelta`
        Spacing of the dates.

    Returns
    -------
    `numpy.array`
        A list floats representing Matplotlib dates.

    """
    f1 = date2num(dstart)
    f2 = date2num(dend)
    step = delta.total_seconds() / SEC_PER_DAY

    # calculate the difference between dend and dstart in times of delta
    num = int(np.ceil((f2 - f1) / step))

    # calculate end of the interval which will be generated
    dinterval_end = dstart + num * delta

    # ensure, that an half open interval will be generated [dstart, dend)
    if dinterval_end >= dend:
        # if the endpoint is greater than or equal to dend,
        # just subtract one delta
        dinterval_end -= delta
        num -= 1

    f2 = date2num(dinterval_end)  # new float-endpoint
    return np.linspace(f1, f2, num + 1)


def _wrap_in_tex(text):
    p = r'([a-zA-Z]+)'
    ret_text = re.sub(p, r'}$\1$\\mathdefault{', text)

    # Braces ensure symbols are not spaced like binary operators.
    ret_text = ret_text.replace('-', '{-}').replace(':', '{:}')
    # To not concatenate space between numbers.
    ret_text = ret_text.replace(' ', r'\;')
    ret_text = '$\\mathdefault{' + ret_text + '}$'
    ret_text = ret_text.replace('$\\mathdefault{}$', '')
    return ret_text


## date tick locators and formatters ###


class DateFormatter(ticker.Formatter):
    """
    Format a tick (in days since the epoch) with a
    `~datetime.datetime.strftime` format string.
    """

    def __init__(self, fmt, tz=None, *, usetex=None):
        """
        Parameters
        ----------
        fmt : str
            `~datetime.datetime.strftime` format string
        tz : str or `~datetime.tzinfo`, default: :rc:`timezone`
            Ticks timezone. If a string, *tz* is passed to `dateutil.tz`.
        usetex : bool, default: :rc:`text.usetex`
            To enable/disable the use of TeX's math mode for rendering the
            results of the formatter.
        """
        self.tz = _get_tzinfo(tz)
        self.fmt = fmt
        self._usetex = mpl._val_or_rc(usetex, 'text.usetex')

    def __call__(self, x, pos=0):
        result = num2date(x, self.tz).strftime(self.fmt)
        return _wrap_in_tex(result) if self._usetex else result

    def set_tzinfo(self, tz):
        self.tz = _get_tzinfo(tz)


class ConciseDateFormatter(ticker.Formatter):
    """
    A `.Formatter` which attempts to figure out the best format to use for the
    date, and to make it as compact as possible, but still be complete. This is
    most useful when used with the `AutoDateLocator`::

    >>> locator = AutoDateLocator()
    >>> formatter = ConciseDateFormatter(locator)

    Parameters
    ----------
    locator : `.ticker.Locator`
        Locator that this axis is using.

    tz : str or `~datetime.tzinfo`, default: :rc:`timezone`
        Ticks timezone, passed to `.dates.num2date`.

    formats : list of 6 strings, optional
        Format strings for 6 levels of tick labelling: mostly years,
        months, days, hours, minutes, and seconds.  Strings use
        the same format codes as `~datetime.datetime.strftime`.  Default is
        ``['%Y', '%b', '%d', '%H:%M', '%H:%M', '%S.%f']``

    zero_formats : list of 6 strings, optional
        Format strings for tick labels that are "zeros" for a given tick
        level.  For instance, if most ticks are months, ticks around 1 Jan 2005
        will be labeled "Dec", "2005", "Feb".  The default is
        ``['', '%Y', '%b', '%b-%d', '%H:%M', '%H:%M']``

    offset_formats : list of 6 strings, optional
        Format strings for the 6 levels that is applied to the "offset"
        string found on the right side of an x-axis, or top of a y-axis.
        Combined with the tick labels this should completely specify the
        date.  The default is::

            ['', '%Y', '%Y-%b', '%Y-%b-%d', '%Y-%b-%d', '%Y-%b-%d %H:%M']

    show_offset : bool, default: True
        Whether to show the offset or not.

    usetex : bool, default: :rc:`text.usetex`
        To enable/disable the use of TeX's math mode for rendering the results
        of the formatter.

    Examples
    --------
    See :doc:`/gallery/ticks/date_concise_formatter`

    .. plot::

        import datetime
        import matplotlib.dates as mdates

        base = datetime.datetime(2005, 2, 1)
        dates = np.array([base + datetime.timedelta(hours=(2 * i))
                          for i in range(732)])
        N = len(dates)
        np.random.seed(19680801)
        y = np.cumsum(np.random.randn(N))

        fig, ax = plt.subplots(constrained_layout=True)
        locator = mdates.AutoDateLocator()
        formatter = mdates.ConciseDateFormatter(locator)
        ax.xaxis.set_major_locator(locator)
        ax.xaxis.set_major_formatter(formatter)

        ax.plot(dates, y)
        ax.set_title('Concise Date Formatter')

    """

    def __init__(self, locator, tz=None, formats=None, offset_formats=None,
                 zero_formats=None, show_offset=True, *, usetex=None):
        """
        Autoformat the date labels.  The default format is used to form an
        initial string, and then redundant elements are removed.
        """
        self._locator = locator
        self._tz = tz
        self.defaultfmt = '%Y'
        # there are 6 levels with each level getting a specific format
        # 0: mostly years,  1: months,  2: days,
        # 3: hours, 4: minutes, 5: seconds
        if formats:
            if len(formats) != 6:
                raise ValueError('formats argument must be a list of '
                                 '6 format strings (or None)')
            self.formats = formats
        else:
            self.formats = ['%Y',  # ticks are mostly years
                            '%b',          # ticks are mostly months
                            '%d',          # ticks are mostly days
                            '%H:%M',       # hrs
                            '%H:%M',       # min
                            '%S.%f',       # secs
                            ]
        # fmt for zeros ticks at this level.  These are
        # ticks that should be labeled w/ info the level above.
        # like 1 Jan can just be labelled "Jan".  02:02:00 can
        # just be labeled 02:02.
        if zero_formats:
            if len(zero_formats) != 6:
                raise ValueError('zero_formats argument must be a list of '
                                 '6 format strings (or None)')
            self.zero_formats = zero_formats
        elif formats:
            # use the users formats for the zero tick formats
            self.zero_formats = [''] + self.formats[:-1]
        else:
            # make the defaults a bit nicer:
            self.zero_formats = [''] + self.formats[:-1]
            self.zero_formats[3] = '%b-%d'

        if offset_formats:
            if len(offset_formats) != 6:
                raise ValueError('offset_formats argument must be a list of '
                                 '6 format strings (or None)')
            self.offset_formats = offset_formats
        else:
            self.offset_formats = ['',
                                   '%Y',
                                   '%Y-%b',
                                   '%Y-%b-%d',
                                   '%Y-%b-%d',
                                   '%Y-%b-%d %H:%M']
        self.offset_string = ''
        self.show_offset = show_offset
        self._usetex = mpl._val_or_rc(usetex, 'text.usetex')

    def __call__(self, x, pos=None):
        formatter = DateFormatter(self.defaultfmt, self._tz,
                                  usetex=self._usetex)
        return formatter(x, pos=pos)

    def format_ticks(self, values):
        tickdatetime = [num2date(value, tz=self._tz) for value in values]
        tickdate = np.array([tdt.timetuple()[:6] for tdt in tickdatetime])

        # basic algorithm:
        # 1) only display a part of the date if it changes over the ticks.
        # 2) don't display the smaller part of the date if:
        #    it is always the same or if it is the start of the
        #    year, month, day etc.
        # fmt for most ticks at this level
        fmts = self.formats
        # format beginnings of days, months, years, etc.
        zerofmts = self.zero_formats
        # offset fmt are for the offset in the upper left of the
        # or lower right of the axis.
        offsetfmts = self.offset_formats
        show_offset = self.show_offset

        # determine the level we will label at:
        # mostly 0: years,  1: months,  2: days,
        # 3: hours, 4: minutes, 5: seconds, 6: microseconds
        for level in range(5, -1, -1):
            unique = np.unique(tickdate[:, level])
            if len(unique) > 1:
                # if 1 is included in unique, the year is shown in ticks
                if level < 2 and np.any(unique == 1):
                    show_offset = False
                break
            elif level == 0:
                # all tickdate are the same, so only micros might be different
                # set to the most precise (6: microseconds doesn't exist...)
                level = 5

        # level is the basic level we will label at.
        # now loop through and decide the actual ticklabels
        zerovals = [0, 1, 1, 0, 0, 0, 0]
        labels = [''] * len(tickdate)
        for nn in range(len(tickdate)):
            if level < 5:
                if tickdate[nn][level] == zerovals[level]:
                    fmt = zerofmts[level]
                else:
                    fmt = fmts[level]
            else:
                # special handling for seconds + microseconds
                if (tickdatetime[nn].second == tickdatetime[nn].microsecond
                        == 0):
                    fmt = zerofmts[level]
                else:
                    fmt = fmts[level]
            labels[nn] = tickdatetime[nn].strftime(fmt)

        # special handling of seconds and microseconds:
        # strip extra zeros and decimal if possible.
        # this is complicated by two factors.  1) we have some level-4 strings
        # here (i.e. 03:00, '0.50000', '1.000') 2) we would like to have the
        # same number of decimals for each string (i.e. 0.5 and 1.0).
        if level >= 5:
            trailing_zeros = min(
                (len(s) - len(s.rstrip('0')) for s in labels if '.' in s),
                default=None)
            if trailing_zeros:
                for nn in range(len(labels)):
                    if '.' in labels[nn]:
                        labels[nn] = labels[nn][:-trailing_zeros].rstrip('.')

        if show_offset:
            # set the offset string:
            if (self._locator.axis and
                    self._locator.axis.__name__ in ('xaxis', 'yaxis')
                    and self._locator.axis.get_inverted()):
                self.offset_string = tickdatetime[0].strftime(offsetfmts[level])
            else:
                self.offset_string = tickdatetime[-1].strftime(offsetfmts[level])
            if self._usetex:
                self.offset_string = _wrap_in_tex(self.offset_string)
        else:
            self.offset_string = ''

        if self._usetex:
            return [_wrap_in_tex(l) for l in labels]
        else:
            return labels

    def get_offset(self):
        return self.offset_string

    def format_data_short(self, value):
        return num2date(value, tz=self._tz).strftime('%Y-%m-%d %H:%M:%S')


class AutoDateFormatter(ticker.Formatter):
    """
    A `.Formatter` which attempts to figure out the best format to use.  This
    is most useful when used with the `AutoDateLocator`.

    `.AutoDateFormatter` has a ``.scale`` dictionary that maps tick scales (the
    interval in days between one major tick) to format strings; this dictionary
    defaults to ::

        self.scaled = {
            DAYS_PER_YEAR: rcParams['date.autoformatter.year'],
            DAYS_PER_MONTH: rcParams['date.autoformatter.month'],
            1: rcParams['date.autoformatter.day'],
            1 / HOURS_PER_DAY: rcParams['date.autoformatter.hour'],
            1 / MINUTES_PER_DAY: rcParams['date.autoformatter.minute'],
            1 / SEC_PER_DAY: rcParams['date.autoformatter.second'],
            1 / MUSECONDS_PER_DAY: rcParams['date.autoformatter.microsecond'],
        }

    The formatter uses the format string corresponding to the lowest key in
    the dictionary that is greater or equal to the current scale.  Dictionary
    entries can be customized::

        locator = AutoDateLocator()
        formatter = AutoDateFormatter(locator)
        formatter.scaled[1/(24*60)] = '%M:%S' # only show min and sec

    Custom callables can also be used instead of format strings.  The following
    example shows how to use a custom format function to strip trailing zeros
    from decimal seconds and adds the date to the first ticklabel::

        def my_format_function(x, pos=None):
            x = matplotlib.dates.num2date(x)
            if pos == 0:
                fmt = '%D %H:%M:%S.%f'
            else:
                fmt = '%H:%M:%S.%f'
            label = x.strftime(fmt)
            label = label.rstrip("0")
            label = label.rstrip(".")
            return label

        formatter.scaled[1/(24*60)] = my_format_function
    """

    # This can be improved by providing some user-level direction on
    # how to choose the best format (precedence, etc.).

    # Perhaps a 'struct' that has a field for each time-type where a
    # zero would indicate "don't show" and a number would indicate
    # "show" with some sort of priority.  Same priorities could mean
    # show all with the same priority.

    # Or more simply, perhaps just a format string for each
    # possibility...

    def __init__(self, locator, tz=None, defaultfmt='%Y-%m-%d', *,
                 usetex=None):
        """
        Autoformat the date labels.

        Parameters
        ----------
        locator : `.ticker.Locator`
            Locator that this axis is using.

        tz : str or `~datetime.tzinfo`, default: :rc:`timezone`
            Ticks timezone. If a string, *tz* is passed to `dateutil.tz`.

        defaultfmt : str
            The default format to use if none of the values in ``self.scaled``
            are greater than the unit returned by ``locator._get_unit()``.

        usetex : bool, default: :rc:`text.usetex`
            To enable/disable the use of TeX's math mode for rendering the
            results of the formatter. If any entries in ``self.scaled`` are set
            as functions, then it is up to the customized function to enable or
            disable TeX's math mode itself.
        """
        self._locator = locator
        self._tz = tz
        self.defaultfmt = defaultfmt
        self._formatter = DateFormatter(self.defaultfmt, tz)
        rcParams = mpl.rcParams
        self._usetex = mpl._val_or_rc(usetex, 'text.usetex')
        self.scaled = {
            DAYS_PER_YEAR: rcParams['date.autoformatter.year'],
            DAYS_PER_MONTH: rcParams['date.autoformatter.month'],
            1: rcParams['date.autoformatter.day'],
            1 / HOURS_PER_DAY: rcParams['date.autoformatter.hour'],
            1 / MINUTES_PER_DAY: rcParams['date.autoformatter.minute'],
            1 / SEC_PER_DAY: rcParams['date.autoformatter.second'],
            1 / MUSECONDS_PER_DAY: rcParams['date.autoformatter.microsecond']
        }

    def _set_locator(self, locator):
        self._locator = locator

    def __call__(self, x, pos=None):
        try:
            locator_unit_scale = float(self._locator._get_unit())
        except AttributeError:
            locator_unit_scale = 1
        # Pick the first scale which is greater than the locator unit.
        fmt = next((fmt for scale, fmt in sorted(self.scaled.items())
                    if scale >= locator_unit_scale),
                   self.defaultfmt)

        if isinstance(fmt, str):
            self._formatter = DateFormatter(fmt, self._tz, usetex=self._usetex)
            result = self._formatter(x, pos)
        elif callable(fmt):
            result = fmt(x, pos)
        else:
            raise TypeError(f'Unexpected type passed to {self!r}.')

        return result


class rrulewrapper:
    """
    A simple wrapper around a `dateutil.rrule` allowing flexible
    date tick specifications.
    """
    def __init__(self, freq, tzinfo=None, **kwargs):
        """
        Parameters
        ----------
        freq : {YEARLY, MONTHLY, WEEKLY, DAILY, HOURLY, MINUTELY, SECONDLY}
            Tick frequency. These constants are defined in `dateutil.rrule`,
            but they are accessible from `matplotlib.dates` as well.
        tzinfo : `datetime.tzinfo`, optional
            Time zone information. The default is None.
        **kwargs
            Additional keyword arguments are passed to the `dateutil.rrule`.
        """
        kwargs['freq'] = freq
        self._base_tzinfo = tzinfo

        self._update_rrule(**kwargs)

    def set(self, **kwargs):
        """Set parameters for an existing wrapper."""
        self._construct.update(kwargs)

        self._update_rrule(**self._construct)

    def _update_rrule(self, **kwargs):
        tzinfo = self._base_tzinfo

        # rrule does not play nicely with timezones - especially pytz time
        # zones, it's best to use naive zones and attach timezones once the
        # datetimes are returned
        if 'dtstart' in kwargs:
            dtstart = kwargs['dtstart']
            if dtstart.tzinfo is not None:
                if tzinfo is None:
                    tzinfo = dtstart.tzinfo
                else:
                    dtstart = dtstart.astimezone(tzinfo)

                kwargs['dtstart'] = dtstart.replace(tzinfo=None)

        if 'until' in kwargs:
            until = kwargs['until']
            if until.tzinfo is not None:
                if tzinfo is not None:
                    until = until.astimezone(tzinfo)
                else:
                    raise ValueError('until cannot be aware if dtstart '
                                     'is naive and tzinfo is None')

                kwargs['until'] = until.replace(tzinfo=None)

        self._construct = kwargs.copy()
        self._tzinfo = tzinfo
        self._rrule = rrule(**self._construct)

    def _attach_tzinfo(self, dt, tzinfo):
        # pytz zones are attached by "localizing" the datetime
        if hasattr(tzinfo, 'localize'):
            return tzinfo.localize(dt, is_dst=True)

        return dt.replace(tzinfo=tzinfo)

    def _aware_return_wrapper(self, f, returns_list=False):
        """Decorator function that allows rrule methods to handle tzinfo."""
        # This is only necessary if we're actually attaching a tzinfo
        if self._tzinfo is None:
            return f

        # All datetime arguments must be naive. If they are not naive, they are
        # converted to the _tzinfo zone before dropping the zone.
        def normalize_arg(arg):
            if isinstance(arg, datetime.datetime) and arg.tzinfo is not None:
                if arg.tzinfo is not self._tzinfo:
                    arg = arg.astimezone(self._tzinfo)

                return arg.replace(tzinfo=None)

            return arg

        def normalize_args(args, kwargs):
            args = tuple(normalize_arg(arg) for arg in args)
            kwargs = {kw: normalize_arg(arg) for kw, arg in kwargs.items()}

            return args, kwargs

        # There are two kinds of functions we care about - ones that return
        # dates and ones that return lists of dates.
        if not returns_list:
            def inner_func(*args, **kwargs):
                args, kwargs = normalize_args(args, kwargs)
                dt = f(*args, **kwargs)
                return self._attach_tzinfo(dt, self._tzinfo)
        else:
            def inner_func(*args, **kwargs):
                args, kwargs = normalize_args(args, kwargs)
                dts = f(*args, **kwargs)
                return [self._attach_tzinfo(dt, self._tzinfo) for dt in dts]

        return functools.wraps(f)(inner_func)

    def __getattr__(self, name):
        if name in self.__dict__:
            return self.__dict__[name]

        f = getattr(self._rrule, name)

        if name in {'after', 'before'}:
            return self._aware_return_wrapper(f)
        elif name in {'xafter', 'xbefore', 'between'}:
            return self._aware_return_wrapper(f, returns_list=True)
        else:
            return f

    def __setstate__(self, state):
        self.__dict__.update(state)


class DateLocator(ticker.Locator):
    """
    Determines the tick locations when plotting dates.

    This class is subclassed by other Locators and
    is not meant to be used on its own.
    """
    hms0d = {'byhour': 0, 'byminute': 0, 'bysecond': 0}

    def __init__(self, tz=None):
        """
        Parameters
        ----------
        tz : str or `~datetime.tzinfo`, default: :rc:`timezone`
            Ticks timezone. If a string, *tz* is passed to `dateutil.tz`.
        """
        self.tz = _get_tzinfo(tz)

    def set_tzinfo(self, tz):
        """
        Set timezone info.

        Parameters
        ----------
        tz : str or `~datetime.tzinfo`, default: :rc:`timezone`
            Ticks timezone. If a string, *tz* is passed to `dateutil.tz`.
        """
        self.tz = _get_tzinfo(tz)

    def datalim_to_dt(self):
        """Convert axis data interval to datetime objects."""
        dmin, dmax = self.axis.get_data_interval()
        if dmin > dmax:
            dmin, dmax = dmax, dmin

        return num2date(dmin, self.tz), num2date(dmax, self.tz)

    def viewlim_to_dt(self):
        """Convert the view interval to datetime objects."""
        vmin, vmax = self.axis.get_view_interval()
        if vmin > vmax:
            vmin, vmax = vmax, vmin
        return num2date(vmin, self.tz), num2date(vmax, self.tz)

    def _get_unit(self):
        """
        Return how many days a unit of the locator is; used for
        intelligent autoscaling.
        """
        return 1

    def _get_interval(self):
        """
        Return the number of units for each tick.
        """
        return 1

    def nonsingular(self, vmin, vmax):
        """
        Given the proposed upper and lower extent, adjust the range
        if it is too close to being singular (i.e. a range of ~0).
        """
        if not np.isfinite(vmin) or not np.isfinite(vmax):
            # Except if there is no data, then use 1970 as default.
            return (date2num(datetime.date(1970, 1, 1)),
                    date2num(datetime.date(1970, 1, 2)))
        if vmax < vmin:
            vmin, vmax = vmax, vmin
        unit = self._get_unit()
        interval = self._get_interval()
        if abs(vmax - vmin) < 1e-6:
            vmin -= 2 * unit * interval
            vmax += 2 * unit * interval
        return vmin, vmax


class RRuleLocator(DateLocator):
    # use the dateutil rrule instance

    def __init__(self, o, tz=None):
        super().__init__(tz)
        self.rule = o

    def __call__(self):
        # if no data have been set, this will tank with a ValueError
        try:
            dmin, dmax = self.viewlim_to_dt()
        except ValueError:
            return []

        return self.tick_values(dmin, dmax)

    def tick_values(self, vmin, vmax):
        start, stop = self._create_rrule(vmin, vmax)
        dates = self.rule.between(start, stop, True)
        if len(dates) == 0:
            return date2num([vmin, vmax])
        return self.raise_if_exceeds(date2num(dates))

    def _create_rrule(self, vmin, vmax):
        # set appropriate rrule dtstart and until and return
        # start and end
        delta = relativedelta(vmax, vmin)

        # We need to cap at the endpoints of valid datetime
        try:
            start = vmin - delta
        except (ValueError, OverflowError):
            # cap
            start = datetime.datetime(1, 1, 1, 0, 0, 0,
                                      tzinfo=datetime.timezone.utc)

        try:
            stop = vmax + delta
        except (ValueError, OverflowError):
            # cap
            stop = datetime.datetime(9999, 12, 31, 23, 59, 59,
                                     tzinfo=datetime.timezone.utc)

        self.rule.set(dtstart=start, until=stop)

        return vmin, vmax

    def _get_unit(self):
        # docstring inherited
        freq = self.rule._rrule._freq
        return self.get_unit_generic(freq)

    @staticmethod
    def get_unit_generic(freq):
        if freq == YEARLY:
            return DAYS_PER_YEAR
        elif freq == MONTHLY:
            return DAYS_PER_MONTH
        elif freq == WEEKLY:
            return DAYS_PER_WEEK
        elif freq == DAILY:
            return 1.0
        elif freq == HOURLY:
            return 1.0 / HOURS_PER_DAY
        elif freq == MINUTELY:
            return 1.0 / MINUTES_PER_DAY
        elif freq == SECONDLY:
            return 1.0 / SEC_PER_DAY
        else:
            # error
            return -1  # or should this just return '1'?

    def _get_interval(self):
        return self.rule._rrule._interval


class AutoDateLocator(DateLocator):
    """
    On autoscale, this class picks the best `DateLocator` to set the view
    limits and the tick locations.

    Attributes
    ----------
    intervald : dict

        Mapping of tick frequencies to multiples allowed for that ticking.
        The default is ::

            self.intervald = {
                YEARLY  : [1, 2, 4, 5, 10, 20, 40, 50, 100, 200, 400, 500,
                           1000, 2000, 4000, 5000, 10000],
                MONTHLY : [1, 2, 3, 4, 6],
                DAILY   : [1, 2, 3, 7, 14, 21],
                HOURLY  : [1, 2, 3, 4, 6, 12],
                MINUTELY: [1, 5, 10, 15, 30],
                SECONDLY: [1, 5, 10, 15, 30],
                MICROSECONDLY: [1, 2, 5, 10, 20, 50, 100, 200, 500,
                                1000, 2000, 5000, 10000, 20000, 50000,
                                100000, 200000, 500000, 1000000],
            }

        where the keys are defined in `dateutil.rrule`.

        The interval is used to specify multiples that are appropriate for
        the frequency of ticking. For instance, every 7 days is sensible
        for daily ticks, but for minutes/seconds, 15 or 30 make sense.

        When customizing, you should only modify the values for the existing
        keys. You should not add or delete entries.

        Example for forcing ticks every 3 hours::

            locator = AutoDateLocator()
            locator.intervald[HOURLY] = [3]  # only show every 3 hours
    """

    def __init__(self, tz=None, minticks=5, maxticks=None,
                 interval_multiples=True):
        """
        Parameters
        ----------
        tz : str or `~datetime.tzinfo`, default: :rc:`timezone`
            Ticks timezone. If a string, *tz* is passed to `dateutil.tz`.
        minticks : int
            The minimum number of ticks desired; controls whether ticks occur
            yearly, monthly, etc.
        maxticks : int
            The maximum number of ticks desired; controls the interval between
            ticks (ticking every other, every 3, etc.).  For fine-grained
            control, this can be a dictionary mapping individual rrule
            frequency constants (YEARLY, MONTHLY, etc.) to their own maximum
            number of ticks.  This can be used to keep the number of ticks
            appropriate to the format chosen in `AutoDateFormatter`. Any
            frequency not specified in this dictionary is given a default
            value.
        interval_multiples : bool, default: True
            Whether ticks should be chosen to be multiple of the interval,
            locking them to 'nicer' locations.  For example, this will force
            the ticks to be at hours 0, 6, 12, 18 when hourly ticking is done
            at 6 hour intervals.
        """
        super().__init__(tz=tz)
        self._freq = YEARLY
        self._freqs = [YEARLY, MONTHLY, DAILY, HOURLY, MINUTELY,
                       SECONDLY, MICROSECONDLY]
        self.minticks = minticks

        self.maxticks = {YEARLY: 11, MONTHLY: 12, DAILY: 11, HOURLY: 12,
                         MINUTELY: 11, SECONDLY: 11, MICROSECONDLY: 8}
        if maxticks is not None:
            try:
                self.maxticks.update(maxticks)
            except TypeError:
                # Assume we were given an integer. Use this as the maximum
                # number of ticks for every frequency and create a
                # dictionary for this
                self.maxticks = dict.fromkeys(self._freqs, maxticks)
        self.interval_multiples = interval_multiples
        self.intervald = {
            YEARLY:   [1, 2, 4, 5, 10, 20, 40, 50, 100, 200, 400, 500,
                       1000, 2000, 4000, 5000, 10000],
            MONTHLY:  [1, 2, 3, 4, 6],
            DAILY:    [1, 2, 3, 7, 14, 21],
            HOURLY:   [1, 2, 3, 4, 6, 12],
            MINUTELY: [1, 5, 10, 15, 30],
            SECONDLY: [1, 5, 10, 15, 30],
            MICROSECONDLY: [1, 2, 5, 10, 20, 50, 100, 200, 500, 1000, 2000,
                            5000, 10000, 20000, 50000, 100000, 200000, 500000,
                            1000000],
                            }
        if interval_multiples:
            # Swap "3" for "4" in the DAILY list; If we use 3 we get bad
            # tick loc for months w/ 31 days: 1, 4, ..., 28, 31, 1
            # If we use 4 then we get: 1, 5, ... 25, 29, 1
            self.intervald[DAILY] = [1, 2, 4, 7, 14]

        self._byranges = [None, range(1, 13), range(1, 32),
                          range(0, 24), range(0, 60), range(0, 60), None]

    def __call__(self):
        # docstring inherited
        dmin, dmax = self.viewlim_to_dt()
        locator = self.get_locator(dmin, dmax)
        return locator()

    def tick_values(self, vmin, vmax):
        return self.get_locator(vmin, vmax).tick_values(vmin, vmax)

    def nonsingular(self, vmin, vmax):
        # whatever is thrown at us, we can scale the unit.
        # But default nonsingular date plots at an ~4 year period.
        if not np.isfinite(vmin) or not np.isfinite(vmax):
            # Except if there is no data, then use 1970 as default.
            return (date2num(datetime.date(1970, 1, 1)),
                    date2num(datetime.date(1970, 1, 2)))
        if vmax < vmin:
            vmin, vmax = vmax, vmin
        if vmin == vmax:
            vmin = vmin - DAYS_PER_YEAR * 2
            vmax = vmax + DAYS_PER_YEAR * 2
        return vmin, vmax

    def _get_unit(self):
        if self._freq in [MICROSECONDLY]:
            return 1. / MUSECONDS_PER_DAY
        else:
            return RRuleLocator.get_unit_generic(self._freq)

    def get_locator(self, dmin, dmax):
        """Pick the best locator based on a distance."""
        delta = relativedelta(dmax, dmin)
        tdelta = dmax - dmin

        # take absolute difference
        if dmin > dmax:
            delta = -delta
            tdelta = -tdelta
        # The following uses a mix of calls to relativedelta and timedelta
        # methods because there is incomplete overlap in the functionality of
        # these similar functions, and it's best to avoid doing our own math
        # whenever possible.
        numYears = float(delta.years)
        numMonths = numYears * MONTHS_PER_YEAR + delta.months
        numDays = tdelta.days  # Avoids estimates of days/month, days/year.
        numHours = numDays * HOURS_PER_DAY + delta.hours
        numMinutes = numHours * MIN_PER_HOUR + delta.minutes
        numSeconds = np.floor(tdelta.total_seconds())
        numMicroseconds = np.floor(tdelta.total_seconds() * 1e6)

        nums = [numYears, numMonths, numDays, numHours, numMinutes,
                numSeconds, numMicroseconds]

        use_rrule_locator = [True] * 6 + [False]

        # Default setting of bymonth, etc. to pass to rrule
        # [unused (for year), bymonth, bymonthday, byhour, byminute,
        #  bysecond, unused (for microseconds)]
        byranges = [None, 1, 1, 0, 0, 0, None]

        # Loop over all the frequencies and try to find one that gives at
        # least a minticks tick positions.  Once this is found, look for
        # an interval from a list specific to that frequency that gives no
        # more than maxticks tick positions. Also, set up some ranges
        # (bymonth, etc.) as appropriate to be passed to rrulewrapper.
        for i, (freq, num) in enumerate(zip(self._freqs, nums)):
            # If this particular frequency doesn't give enough ticks, continue
            if num < self.minticks:
                # Since we're not using this particular frequency, set
                # the corresponding by_ to None so the rrule can act as
                # appropriate
                byranges[i] = None
                continue

            # Find the first available interval that doesn't give too many
            # ticks
            for interval in self.intervald[freq]:
                if num <= interval * (self.maxticks[freq] - 1):
                    break
            else:
                if not (self.interval_multiples and freq == DAILY):
                    _api.warn_external(
                        f"AutoDateLocator was unable to pick an appropriate "
                        f"interval for this date range. It may be necessary "
                        f"to add an interval value to the AutoDateLocator's "
                        f"intervald dictionary. Defaulting to {interval}.")

            # Set some parameters as appropriate
            self._freq = freq

            if self._byranges[i] and self.interval_multiples:
                byranges[i] = self._byranges[i][::interval]
                if i in (DAILY, WEEKLY):
                    if interval == 14:
                        # just make first and 15th.  Avoids 30th.
                        byranges[i] = [1, 15]
                    elif interval == 7:
                        byranges[i] = [1, 8, 15, 22]

                interval = 1
            else:
                byranges[i] = self._byranges[i]
            break
        else:
            interval = 1

        if (freq == YEARLY) and self.interval_multiples:
            locator = YearLocator(interval, tz=self.tz)
        elif use_rrule_locator[i]:
            _, bymonth, bymonthday, byhour, byminute, bysecond, _ = byranges
            rrule = rrulewrapper(self._freq, interval=interval,
                                 dtstart=dmin, until=dmax,
                                 bymonth=bymonth, bymonthday=bymonthday,
                                 byhour=byhour, byminute=byminute,
                                 bysecond=bysecond)

            locator = RRuleLocator(rrule, tz=self.tz)
        else:
            locator = MicrosecondLocator(interval, tz=self.tz)
            if date2num(dmin) > 70 * 365 and interval < 1000:
                _api.warn_external(
                    'Plotting microsecond time intervals for dates far from '
                    f'the epoch (time origin: {get_epoch()}) is not well-'
                    'supported. See matplotlib.dates.set_epoch to change the '
                    'epoch.')

        locator.set_axis(self.axis)
        return locator


class YearLocator(RRuleLocator):
    """
    Make ticks on a given day of each year that is a multiple of base.

    Examples::

      # Tick every year on Jan 1st
      locator = YearLocator()

      # Tick every 5 years on July 4th
      locator = YearLocator(5, month=7, day=4)
    """
    def __init__(self, base=1, month=1, day=1, tz=None):
        """
        Parameters
        ----------
        base : int, default: 1
            Mark ticks every *base* years.
        month : int, default: 1
            The month on which to place the ticks, starting from 1. Default is
            January.
        day : int, default: 1
            The day on which to place the ticks.
        tz : str or `~datetime.tzinfo`, default: :rc:`timezone`
            Ticks timezone. If a string, *tz* is passed to `dateutil.tz`.
        """
        rule = rrulewrapper(YEARLY, interval=base, bymonth=month,
                            bymonthday=day, **self.hms0d)
        super().__init__(rule, tz=tz)
        self.base = ticker._Edge_integer(base, 0)

    def _create_rrule(self, vmin, vmax):
        # 'start' needs to be a multiple of the interval to create ticks on
        # interval multiples when the tick frequency is YEARLY
        ymin = max(self.base.le(vmin.year) * self.base.step, 1)
        ymax = min(self.base.ge(vmax.year) * self.base.step, 9999)

        c = self.rule._construct
        replace = {'year': ymin,
                   'month': c.get('bymonth', 1),
                   'day': c.get('bymonthday', 1),
                   'hour': 0, 'minute': 0, 'second': 0}

        start = vmin.replace(**replace)
        stop = start.replace(year=ymax)
        self.rule.set(dtstart=start, until=stop)

        return start, stop


class MonthLocator(RRuleLocator):
    """
    Make ticks on occurrences of each month, e.g., 1, 3, 12.
    """
    def __init__(self, bymonth=None, bymonthday=1, interval=1, tz=None):
        """
        Parameters
        ----------
        bymonth : int or list of int, default: all months
            Ticks will be placed on every month in *bymonth*. Default is
            ``range(1, 13)``, i.e. every month.
        bymonthday : int, default: 1
            The day on which to place the ticks.
        interval : int, default: 1
            The interval between each iteration. For example, if
            ``interval=2``, mark every second occurrence.
        tz : str or `~datetime.tzinfo`, default: :rc:`timezone`
            Ticks timezone. If a string, *tz* is passed to `dateutil.tz`.
        """
        if bymonth is None:
            bymonth = range(1, 13)

        rule = rrulewrapper(MONTHLY, bymonth=bymonth, bymonthday=bymonthday,
                            interval=interval, **self.hms0d)
        super().__init__(rule, tz=tz)


class WeekdayLocator(RRuleLocator):
    """
    Make ticks on occurrences of each weekday.
    """

    def __init__(self, byweekday=1, interval=1, tz=None):
        """
        Parameters
        ----------
        byweekday : int or list of int, default: all days
            Ticks will be placed on every weekday in *byweekday*. Default is
            every day.

            Elements of *byweekday* must be one of MO, TU, WE, TH, FR, SA,
            SU, the constants from :mod:`dateutil.rrule`, which have been
            imported into the :mod:`matplotlib.dates` namespace.
        interval : int, default: 1
            The interval between each iteration. For example, if
            ``interval=2``, mark every second occurrence.
        tz : str or `~datetime.tzinfo`, default: :rc:`timezone`
            Ticks timezone. If a string, *tz* is passed to `dateutil.tz`.
        """
        rule = rrulewrapper(DAILY, byweekday=byweekday,
                            interval=interval, **self.hms0d)
        super().__init__(rule, tz=tz)


class DayLocator(RRuleLocator):
    """
    Make ticks on occurrences of each day of the month.  For example,
    1, 15, 30.
    """
    def __init__(self, bymonthday=None, interval=1, tz=None):
        """
        Parameters
        ----------
        bymonthday : int or list of int, default: all days
            Ticks will be placed on every day in *bymonthday*. Default is
            ``bymonthday=range(1, 32)``, i.e., every day of the month.
        interval : int, default: 1
            The interval between each iteration. For example, if
            ``interval=2``, mark every second occurrence.
        tz : str or `~datetime.tzinfo`, default: :rc:`timezone`
            Ticks timezone. If a string, *tz* is passed to `dateutil.tz`.
        """
        if interval != int(interval) or interval < 1:
            raise ValueError("interval must be an integer greater than 0")
        if bymonthday is None:
            bymonthday = range(1, 32)

        rule = rrulewrapper(DAILY, bymonthday=bymonthday,
                            interval=interval, **self.hms0d)
        super().__init__(rule, tz=tz)


class HourLocator(RRuleLocator):
    """
    Make ticks on occurrences of each hour.
    """
    def __init__(self, byhour=None, interval=1, tz=None):
        """
        Parameters
        ----------
        byhour : int or list of int, default: all hours
            Ticks will be placed on every hour in *byhour*. Default is
            ``byhour=range(24)``, i.e., every hour.
        interval : int, default: 1
            The interval between each iteration. For example, if
            ``interval=2``, mark every second occurrence.
        tz : str or `~datetime.tzinfo`, default: :rc:`timezone`
            Ticks timezone. If a string, *tz* is passed to `dateutil.tz`.
        """
        if byhour is None:
            byhour = range(24)

        rule = rrulewrapper(HOURLY, byhour=byhour, interval=interval,
                            byminute=0, bysecond=0)
        super().__init__(rule, tz=tz)


class MinuteLocator(RRuleLocator):
    """
    Make ticks on occurrences of each minute.
    """
    def __init__(self, byminute=None, interval=1, tz=None):
        """
        Parameters
        ----------
        byminute : int or list of int, default: all minutes
            Ticks will be placed on every minute in *byminute*. Default is
            ``byminute=range(60)``, i.e., every minute.
        interval : int, default: 1
            The interval between each iteration. For example, if
            ``interval=2``, mark every second occurrence.
        tz : str or `~datetime.tzinfo`, default: :rc:`timezone`
            Ticks timezone. If a string, *tz* is passed to `dateutil.tz`.
        """
        if byminute is None:
            byminute = range(60)

        rule = rrulewrapper(MINUTELY, byminute=byminute, interval=interval,
                            bysecond=0)
        super().__init__(rule, tz=tz)


class SecondLocator(RRuleLocator):
    """
    Make ticks on occurrences of each second.
    """
    def __init__(self, bysecond=None, interval=1, tz=None):
        """
        Parameters
        ----------
        bysecond : int or list of int, default: all seconds
            Ticks will be placed on every second in *bysecond*. Default is
            ``bysecond = range(60)``, i.e., every second.
        interval : int, default: 1
            The interval between each iteration. For example, if
            ``interval=2``, mark every second occurrence.
        tz : str or `~datetime.tzinfo`, default: :rc:`timezone`
            Ticks timezone. If a string, *tz* is passed to `dateutil.tz`.
        """
        if bysecond is None:
            bysecond = range(60)

        rule = rrulewrapper(SECONDLY, bysecond=bysecond, interval=interval)
        super().__init__(rule, tz=tz)


class MicrosecondLocator(DateLocator):
    """
    Make ticks on regular intervals of one or more microsecond(s).

    .. note::

        By default, Matplotlib uses a floating point representation of time in
        days since the epoch, so plotting data with
        microsecond time resolution does not work well for
        dates that are far (about 70 years) from the epoch (check with
        `~.dates.get_epoch`).

        If you want sub-microsecond resolution time plots, it is strongly
        recommended to use floating point seconds, not datetime-like
        time representation.

        If you really must use datetime.datetime() or similar and still
        need microsecond precision, change the time origin via
        `.dates.set_epoch` to something closer to the dates being plotted.
        See :doc:`/gallery/ticks/date_precision_and_epochs`.

    """
    def __init__(self, interval=1, tz=None):
        """
        Parameters
        ----------
        interval : int, default: 1
            The interval between each iteration. For example, if
            ``interval=2``, mark every second occurrence.
        tz : str or `~datetime.tzinfo`, default: :rc:`timezone`
            Ticks timezone. If a string, *tz* is passed to `dateutil.tz`.
        """
        super().__init__(tz=tz)
        self._interval = interval
        self._wrapped_locator = ticker.MultipleLocator(interval)

    def set_axis(self, axis):
        self._wrapped_locator.set_axis(axis)
        return super().set_axis(axis)

    def __call__(self):
        # if no data have been set, this will tank with a ValueError
        try:
            dmin, dmax = self.viewlim_to_dt()
        except ValueError:
            return []

        return self.tick_values(dmin, dmax)

    def tick_values(self, vmin, vmax):
        nmin, nmax = date2num((vmin, vmax))
        t0 = np.floor(nmin)
        nmax = nmax - t0
        nmin = nmin - t0
        nmin *= MUSECONDS_PER_DAY
        nmax *= MUSECONDS_PER_DAY

        ticks = self._wrapped_locator.tick_values(nmin, nmax)

        ticks = ticks / MUSECONDS_PER_DAY + t0
        return ticks

    def _get_unit(self):
        # docstring inherited
        return 1. / MUSECONDS_PER_DAY

    def _get_interval(self):
        # docstring inherited
        return self._interval


class DateConverter(units.ConversionInterface):
    """
    Converter for `datetime.date` and `datetime.datetime` data, or for
    date/time data represented as it would be converted by `date2num`.

    The 'unit' tag for such data is None or a `~datetime.tzinfo` instance.
    """

    def __init__(self, *, interval_multiples=True):
        self._interval_multiples = interval_multiples
        super().__init__()

    def axisinfo(self, unit, axis):
        """
        Return the `~matplotlib.units.AxisInfo` for *unit*.

        *unit* is a `~datetime.tzinfo` instance or None.
        The *axis* argument is required but not used.
        """
        tz = unit

        majloc = AutoDateLocator(tz=tz,
                                 interval_multiples=self._interval_multiples)
        majfmt = AutoDateFormatter(majloc, tz=tz)
        datemin = datetime.date(1970, 1, 1)
        datemax = datetime.date(1970, 1, 2)

        return units.AxisInfo(majloc=majloc, majfmt=majfmt, label='',
                              default_limits=(datemin, datemax))

    @staticmethod
    def convert(value, unit, axis):
        """
        If *value* is not already a number or sequence of numbers, convert it
        with `date2num`.

        The *unit* and *axis* arguments are not used.
        """
        return date2num(value)

    @staticmethod
    def default_units(x, axis):
        """
        Return the `~datetime.tzinfo` instance of *x* or of its first element,
        or None
        """
        if isinstance(x, np.ndarray):
            x = x.ravel()

        try:
            x = cbook._safe_first_finite(x)
        except (TypeError, StopIteration):
            pass

        try:
            return x.tzinfo
        except AttributeError:
            pass
        return None


class ConciseDateConverter(DateConverter):
    # docstring inherited

    def __init__(self, formats=None, zero_formats=None, offset_formats=None,
                 show_offset=True, *, interval_multiples=True):
        self._formats = formats
        self._zero_formats = zero_formats
        self._offset_formats = offset_formats
        self._show_offset = show_offset
        self._interval_multiples = interval_multiples
        super().__init__()

    def axisinfo(self, unit, axis):
        # docstring inherited
        tz = unit
        majloc = AutoDateLocator(tz=tz,
                                 interval_multiples=self._interval_multiples)
        majfmt = ConciseDateFormatter(majloc, tz=tz, formats=self._formats,
                                      zero_formats=self._zero_formats,
                                      offset_formats=self._offset_formats,
                                      show_offset=self._show_offset)
        datemin = datetime.date(1970, 1, 1)
        datemax = datetime.date(1970, 1, 2)
        return units.AxisInfo(majloc=majloc, majfmt=majfmt, label='',
                              default_limits=(datemin, datemax))


class _SwitchableDateConverter:
    """
    Helper converter-like object that generates and dispatches to
    temporary ConciseDateConverter or DateConverter instances based on
    :rc:`date.converter` and :rc:`date.interval_multiples`.
    """

    @staticmethod
    def _get_converter():
        converter_cls = {
            "concise": ConciseDateConverter, "auto": DateConverter}[
                mpl.rcParams["date.converter"]]
        interval_multiples = mpl.rcParams["date.interval_multiples"]
        return converter_cls(interval_multiples=interval_multiples)

    def axisinfo(self, *args, **kwargs):
        return self._get_converter().axisinfo(*args, **kwargs)

    def default_units(self, *args, **kwargs):
        return self._get_converter().default_units(*args, **kwargs)

    def convert(self, *args, **kwargs):
        return self._get_converter().convert(*args, **kwargs)


units.registry[np.datetime64] = \
    units.registry[datetime.date] = \
    units.registry[datetime.datetime] = \
    _SwitchableDateConverter()

# === NexusCore/openenv\Lib\site-packages\google\protobuf\text_format.py ===
# Protocol Buffers - Google's data interchange format
# Copyright 2008 Google Inc.  All rights reserved.
#
# Use of this source code is governed by a BSD-style
# license that can be found in the LICENSE file or at
# https://developers.google.com/open-source/licenses/bsd

"""Contains routines for printing protocol messages in text format.

Simple usage example::

  # Create a proto object and serialize it to a text proto string.
  message = my_proto_pb2.MyMessage(foo='bar')
  text_proto = text_format.MessageToString(message)

  # Parse a text proto string.
  message = text_format.Parse(text_proto, my_proto_pb2.MyMessage())
"""

__author__ = 'kenton@google.com (Kenton Varda)'

# TODO Import thread contention leads to test failures.
import encodings.raw_unicode_escape  # pylint: disable=unused-import
import encodings.unicode_escape  # pylint: disable=unused-import
import io
import math
import re

from google.protobuf.internal import decoder
from google.protobuf.internal import type_checkers
from google.protobuf import descriptor
from google.protobuf import text_encoding
from google.protobuf import unknown_fields

# pylint: disable=g-import-not-at-top
__all__ = ['MessageToString', 'Parse', 'PrintMessage', 'PrintField',
           'PrintFieldValue', 'Merge', 'MessageToBytes']

_INTEGER_CHECKERS = (type_checkers.Uint32ValueChecker(),
                     type_checkers.Int32ValueChecker(),
                     type_checkers.Uint64ValueChecker(),
                     type_checkers.Int64ValueChecker())
_FLOAT_INFINITY = re.compile('-?inf(?:inity)?f?$', re.IGNORECASE)
_FLOAT_NAN = re.compile('nanf?$', re.IGNORECASE)
_QUOTES = frozenset(("'", '"'))
_ANY_FULL_TYPE_NAME = 'google.protobuf.Any'
_DEBUG_STRING_SILENT_MARKER = '\t '


class Error(Exception):
  """Top-level module error for text_format."""


class ParseError(Error):
  """Thrown in case of text parsing or tokenizing error."""

  def __init__(self, message=None, line=None, column=None):
    if message is not None and line is not None:
      loc = str(line)
      if column is not None:
        loc += ':{0}'.format(column)
      message = '{0} : {1}'.format(loc, message)
    if message is not None:
      super(ParseError, self).__init__(message)
    else:
      super(ParseError, self).__init__()
    self._line = line
    self._column = column

  def GetLine(self):
    return self._line

  def GetColumn(self):
    return self._column


class TextWriter(object):

  def __init__(self, as_utf8):
    self._writer = io.StringIO()

  def write(self, val):
    return self._writer.write(val)

  def close(self):
    return self._writer.close()

  def getvalue(self):
    return self._writer.getvalue()


def MessageToString(
    message,
    as_utf8=False,
    as_one_line=False,
    use_short_repeated_primitives=False,
    pointy_brackets=False,
    use_index_order=False,
    float_format=None,
    double_format=None,
    use_field_number=False,
    descriptor_pool=None,
    indent=0,
    message_formatter=None,
    print_unknown_fields=False,
    force_colon=False) -> str:
  """Convert protobuf message to text format.

  Double values can be formatted compactly with 15 digits of
  precision (which is the most that IEEE 754 "double" can guarantee)
  using double_format='.15g'. To ensure that converting to text and back to a
  proto will result in an identical value, double_format='.17g' should be used.

  Args:
    message: The protocol buffers message.
    as_utf8: Return unescaped Unicode for non-ASCII characters.
    as_one_line: Don't introduce newlines between fields.
    use_short_repeated_primitives: Use short repeated format for primitives.
    pointy_brackets: If True, use angle brackets instead of curly braces for
      nesting.
    use_index_order: If True, fields of a proto message will be printed using
      the order defined in source code instead of the field number, extensions
      will be printed at the end of the message and their relative order is
      determined by the extension number. By default, use the field number
      order.
    float_format (str): If set, use this to specify float field formatting
      (per the "Format Specification Mini-Language"); otherwise, shortest float
      that has same value in wire will be printed. Also affect double field
      if double_format is not set but float_format is set.
    double_format (str): If set, use this to specify double field formatting
      (per the "Format Specification Mini-Language"); if it is not set but
      float_format is set, use float_format. Otherwise, use ``str()``
    use_field_number: If True, print field numbers instead of names.
    descriptor_pool (DescriptorPool): Descriptor pool used to resolve Any types.
    indent (int): The initial indent level, in terms of spaces, for pretty
      print.
    message_formatter (function(message, indent, as_one_line) -> unicode|None):
      Custom formatter for selected sub-messages (usually based on message
      type). Use to pretty print parts of the protobuf for easier diffing.
    print_unknown_fields: If True, unknown fields will be printed.
    force_colon: If set, a colon will be added after the field name even if the
      field is a proto message.

  Returns:
    str: A string of the text formatted protocol buffer message.
  """
  out = TextWriter(as_utf8)
  printer = _Printer(
      out,
      indent,
      as_utf8,
      as_one_line,
      use_short_repeated_primitives,
      pointy_brackets,
      use_index_order,
      float_format,
      double_format,
      use_field_number,
      descriptor_pool,
      message_formatter,
      print_unknown_fields=print_unknown_fields,
      force_colon=force_colon)
  printer.PrintMessage(message)
  result = out.getvalue()
  out.close()
  if as_one_line:
    return result.rstrip()
  return result


def MessageToBytes(message, **kwargs) -> bytes:
  """Convert protobuf message to encoded text format.  See MessageToString."""
  text = MessageToString(message, **kwargs)
  if isinstance(text, bytes):
    return text
  codec = 'utf-8' if kwargs.get('as_utf8') else 'ascii'
  return text.encode(codec)


def _IsMapEntry(field):
  return (field.type == descriptor.FieldDescriptor.TYPE_MESSAGE and
          field.message_type.has_options and
          field.message_type.GetOptions().map_entry)


def PrintMessage(message,
                 out,
                 indent=0,
                 as_utf8=False,
                 as_one_line=False,
                 use_short_repeated_primitives=False,
                 pointy_brackets=False,
                 use_index_order=False,
                 float_format=None,
                 double_format=None,
                 use_field_number=False,
                 descriptor_pool=None,
                 message_formatter=None,
                 print_unknown_fields=False,
                 force_colon=False):
  """Convert the message to text format and write it to the out stream.

  Args:
    message: The Message object to convert to text format.
    out: A file handle to write the message to.
    indent: The initial indent level for pretty print.
    as_utf8: Return unescaped Unicode for non-ASCII characters.
    as_one_line: Don't introduce newlines between fields.
    use_short_repeated_primitives: Use short repeated format for primitives.
    pointy_brackets: If True, use angle brackets instead of curly braces for
      nesting.
    use_index_order: If True, print fields of a proto message using the order
      defined in source code instead of the field number. By default, use the
      field number order.
    float_format: If set, use this to specify float field formatting
      (per the "Format Specification Mini-Language"); otherwise, shortest
      float that has same value in wire will be printed. Also affect double
      field if double_format is not set but float_format is set.
    double_format: If set, use this to specify double field formatting
      (per the "Format Specification Mini-Language"); if it is not set but
      float_format is set, use float_format. Otherwise, str() is used.
    use_field_number: If True, print field numbers instead of names.
    descriptor_pool: A DescriptorPool used to resolve Any types.
    message_formatter: A function(message, indent, as_one_line): unicode|None
      to custom format selected sub-messages (usually based on message type).
      Use to pretty print parts of the protobuf for easier diffing.
    print_unknown_fields: If True, unknown fields will be printed.
    force_colon: If set, a colon will be added after the field name even if
      the field is a proto message.
  """
  printer = _Printer(
      out=out, indent=indent, as_utf8=as_utf8,
      as_one_line=as_one_line,
      use_short_repeated_primitives=use_short_repeated_primitives,
      pointy_brackets=pointy_brackets,
      use_index_order=use_index_order,
      float_format=float_format,
      double_format=double_format,
      use_field_number=use_field_number,
      descriptor_pool=descriptor_pool,
      message_formatter=message_formatter,
      print_unknown_fields=print_unknown_fields,
      force_colon=force_colon)
  printer.PrintMessage(message)


def PrintField(field,
               value,
               out,
               indent=0,
               as_utf8=False,
               as_one_line=False,
               use_short_repeated_primitives=False,
               pointy_brackets=False,
               use_index_order=False,
               float_format=None,
               double_format=None,
               message_formatter=None,
               print_unknown_fields=False,
               force_colon=False):
  """Print a single field name/value pair."""
  printer = _Printer(out, indent, as_utf8, as_one_line,
                     use_short_repeated_primitives, pointy_brackets,
                     use_index_order, float_format, double_format,
                     message_formatter=message_formatter,
                     print_unknown_fields=print_unknown_fields,
                     force_colon=force_colon)
  printer.PrintField(field, value)


def PrintFieldValue(field,
                    value,
                    out,
                    indent=0,
                    as_utf8=False,
                    as_one_line=False,
                    use_short_repeated_primitives=False,
                    pointy_brackets=False,
                    use_index_order=False,
                    float_format=None,
                    double_format=None,
                    message_formatter=None,
                    print_unknown_fields=False,
                    force_colon=False):
  """Print a single field value (not including name)."""
  printer = _Printer(out, indent, as_utf8, as_one_line,
                     use_short_repeated_primitives, pointy_brackets,
                     use_index_order, float_format, double_format,
                     message_formatter=message_formatter,
                     print_unknown_fields=print_unknown_fields,
                     force_colon=force_colon)
  printer.PrintFieldValue(field, value)


def _BuildMessageFromTypeName(type_name, descriptor_pool):
  """Returns a protobuf message instance.

  Args:
    type_name: Fully-qualified protobuf  message type name string.
    descriptor_pool: DescriptorPool instance.

  Returns:
    A Message instance of type matching type_name, or None if the a Descriptor
    wasn't found matching type_name.
  """
  # pylint: disable=g-import-not-at-top
  if descriptor_pool is None:
    from google.protobuf import descriptor_pool as pool_mod
    descriptor_pool = pool_mod.Default()
  from google.protobuf import message_factory
  try:
    message_descriptor = descriptor_pool.FindMessageTypeByName(type_name)
  except KeyError:
    return None
  message_type = message_factory.GetMessageClass(message_descriptor)
  return message_type()


# These values must match WireType enum in //google/protobuf/wire_format.h.
WIRETYPE_LENGTH_DELIMITED = 2
WIRETYPE_START_GROUP = 3


class _Printer(object):
  """Text format printer for protocol message."""

  def __init__(
      self,
      out,
      indent=0,
      as_utf8=False,
      as_one_line=False,
      use_short_repeated_primitives=False,
      pointy_brackets=False,
      use_index_order=False,
      float_format=None,
      double_format=None,
      use_field_number=False,
      descriptor_pool=None,
      message_formatter=None,
      print_unknown_fields=False,
      force_colon=False):
    """Initialize the Printer.

    Double values can be formatted compactly with 15 digits of precision
    (which is the most that IEEE 754 "double" can guarantee) using
    double_format='.15g'. To ensure that converting to text and back to a proto
    will result in an identical value, double_format='.17g' should be used.

    Args:
      out: To record the text format result.
      indent: The initial indent level for pretty print.
      as_utf8: Return unescaped Unicode for non-ASCII characters.
      as_one_line: Don't introduce newlines between fields.
      use_short_repeated_primitives: Use short repeated format for primitives.
      pointy_brackets: If True, use angle brackets instead of curly braces for
        nesting.
      use_index_order: If True, print fields of a proto message using the order
        defined in source code instead of the field number. By default, use the
        field number order.
      float_format: If set, use this to specify float field formatting
        (per the "Format Specification Mini-Language"); otherwise, shortest
        float that has same value in wire will be printed. Also affect double
        field if double_format is not set but float_format is set.
      double_format: If set, use this to specify double field formatting
        (per the "Format Specification Mini-Language"); if it is not set but
        float_format is set, use float_format. Otherwise, str() is used.
      use_field_number: If True, print field numbers instead of names.
      descriptor_pool: A DescriptorPool used to resolve Any types.
      message_formatter: A function(message, indent, as_one_line): unicode|None
        to custom format selected sub-messages (usually based on message type).
        Use to pretty print parts of the protobuf for easier diffing.
      print_unknown_fields: If True, unknown fields will be printed.
      force_colon: If set, a colon will be added after the field name even if
        the field is a proto message.
    """
    self.out = out
    self.indent = indent
    self.as_utf8 = as_utf8
    self.as_one_line = as_one_line
    self.use_short_repeated_primitives = use_short_repeated_primitives
    self.pointy_brackets = pointy_brackets
    self.use_index_order = use_index_order
    self.float_format = float_format
    if double_format is not None:
      self.double_format = double_format
    else:
      self.double_format = float_format
    self.use_field_number = use_field_number
    self.descriptor_pool = descriptor_pool
    self.message_formatter = message_formatter
    self.print_unknown_fields = print_unknown_fields
    self.force_colon = force_colon

  def _TryPrintAsAnyMessage(self, message):
    """Serializes if message is a google.protobuf.Any field."""
    if '/' not in message.type_url:
      return False
    packed_message = _BuildMessageFromTypeName(message.TypeName(),
                                               self.descriptor_pool)
    if packed_message:
      packed_message.MergeFromString(message.value)
      colon = ':' if self.force_colon else ''
      self.out.write('%s[%s]%s ' % (self.indent * ' ', message.type_url, colon))
      self._PrintMessageFieldValue(packed_message)
      self.out.write(' ' if self.as_one_line else '\n')
      return True
    else:
      return False

  def _TryCustomFormatMessage(self, message):
    formatted = self.message_formatter(message, self.indent, self.as_one_line)
    if formatted is None:
      return False

    out = self.out
    out.write(' ' * self.indent)
    out.write(formatted)
    out.write(' ' if self.as_one_line else '\n')
    return True

  def PrintMessage(self, message):
    """Convert protobuf message to text format.

    Args:
      message: The protocol buffers message.
    """
    if self.message_formatter and self._TryCustomFormatMessage(message):
      return
    if (message.DESCRIPTOR.full_name == _ANY_FULL_TYPE_NAME and
        self._TryPrintAsAnyMessage(message)):
      return
    fields = message.ListFields()
    if self.use_index_order:
      fields.sort(
          key=lambda x: x[0].number if x[0].is_extension else x[0].index)
    for field, value in fields:
      if _IsMapEntry(field):
        for key in sorted(value):
          # This is slow for maps with submessage entries because it copies the
          # entire tree.  Unfortunately this would take significant refactoring
          # of this file to work around.
          #
          # TODO: refactor and optimize if this becomes an issue.
          entry_submsg = value.GetEntryClass()(key=key, value=value[key])
          self.PrintField(field, entry_submsg)
      elif field.label == descriptor.FieldDescriptor.LABEL_REPEATED:
        if (self.use_short_repeated_primitives
            and field.cpp_type != descriptor.FieldDescriptor.CPPTYPE_MESSAGE
            and field.cpp_type != descriptor.FieldDescriptor.CPPTYPE_STRING):
          self._PrintShortRepeatedPrimitivesValue(field, value)
        else:
          for element in value:
            self.PrintField(field, element)
      else:
        self.PrintField(field, value)

    if self.print_unknown_fields:
      self._PrintUnknownFields(unknown_fields.UnknownFieldSet(message))

  def _PrintUnknownFields(self, unknown_field_set):
    """Print unknown fields."""
    out = self.out
    for field in unknown_field_set:
      out.write(' ' * self.indent)
      out.write(str(field.field_number))
      if field.wire_type == WIRETYPE_START_GROUP:
        if self.as_one_line:
          out.write(' { ')
        else:
          out.write(' {\n')
          self.indent += 2

        self._PrintUnknownFields(field.data)

        if self.as_one_line:
          out.write('} ')
        else:
          self.indent -= 2
          out.write(' ' * self.indent + '}\n')
      elif field.wire_type == WIRETYPE_LENGTH_DELIMITED:
        try:
          # If this field is parseable as a Message, it is probably
          # an embedded message.
          # pylint: disable=protected-access
          (embedded_unknown_message, pos) = decoder._DecodeUnknownFieldSet(
              memoryview(field.data), 0, len(field.data))
        except Exception:    # pylint: disable=broad-except
          pos = 0

        if pos == len(field.data):
          if self.as_one_line:
            out.write(' { ')
          else:
            out.write(' {\n')
            self.indent += 2

          self._PrintUnknownFields(embedded_unknown_message)

          if self.as_one_line:
            out.write('} ')
          else:
            self.indent -= 2
            out.write(' ' * self.indent + '}\n')
        else:
          # A string or bytes field. self.as_utf8 may not work.
          out.write(': \"')
          out.write(text_encoding.CEscape(field.data, False))
          out.write('\" ' if self.as_one_line else '\"\n')
      else:
        # varint, fixed32, fixed64
        out.write(': ')
        out.write(str(field.data))
        out.write(' ' if self.as_one_line else '\n')

  def _PrintFieldName(self, field):
    """Print field name."""
    out = self.out
    out.write(' ' * self.indent)
    if self.use_field_number:
      out.write(str(field.number))
    else:
      if field.is_extension:
        out.write('[')
        if (field.containing_type.GetOptions().message_set_wire_format and
            field.type == descriptor.FieldDescriptor.TYPE_MESSAGE and
            field.label == descriptor.FieldDescriptor.LABEL_OPTIONAL):
          out.write(field.message_type.full_name)
        else:
          out.write(field.full_name)
        out.write(']')
      elif field.type == descriptor.FieldDescriptor.TYPE_GROUP:
        # For groups, use the capitalized name.
        out.write(field.message_type.name)
      else:
        out.write(field.name)

    if (self.force_colon or
        field.cpp_type != descriptor.FieldDescriptor.CPPTYPE_MESSAGE):
      # The colon is optional in this case, but our cross-language golden files
      # don't include it. Here, the colon is only included if force_colon is
      # set to True
      out.write(':')

  def PrintField(self, field, value):
    """Print a single field name/value pair."""
    self._PrintFieldName(field)
    self.out.write(' ')
    self.PrintFieldValue(field, value)
    self.out.write(' ' if self.as_one_line else '\n')

  def _PrintShortRepeatedPrimitivesValue(self, field, value):
    """"Prints short repeated primitives value."""
    # Note: this is called only when value has at least one element.
    self._PrintFieldName(field)
    self.out.write(' [')
    for i in range(len(value) - 1):
      self.PrintFieldValue(field, value[i])
      self.out.write(', ')
    self.PrintFieldValue(field, value[-1])
    self.out.write(']')
    self.out.write(' ' if self.as_one_line else '\n')

  def _PrintMessageFieldValue(self, value):
    if self.pointy_brackets:
      openb = '<'
      closeb = '>'
    else:
      openb = '{'
      closeb = '}'

    if self.as_one_line:
      self.out.write('%s ' % openb)
      self.PrintMessage(value)
      self.out.write(closeb)
    else:
      self.out.write('%s\n' % openb)
      self.indent += 2
      self.PrintMessage(value)
      self.indent -= 2
      self.out.write(' ' * self.indent + closeb)

  def PrintFieldValue(self, field, value):
    """Print a single field value (not including name).

    For repeated fields, the value should be a single element.

    Args:
      field: The descriptor of the field to be printed.
      value: The value of the field.
    """
    out = self.out
    if field.cpp_type == descriptor.FieldDescriptor.CPPTYPE_MESSAGE:
      self._PrintMessageFieldValue(value)
    elif field.cpp_type == descriptor.FieldDescriptor.CPPTYPE_ENUM:
      enum_value = field.enum_type.values_by_number.get(value, None)
      if enum_value is not None:
        out.write(enum_value.name)
      else:
        out.write(str(value))
    elif field.cpp_type == descriptor.FieldDescriptor.CPPTYPE_STRING:
      out.write('\"')
      if isinstance(value, str) and not self.as_utf8:
        out_value = value.encode('utf-8')
      else:
        out_value = value
      if field.type == descriptor.FieldDescriptor.TYPE_BYTES:
        # We always need to escape all binary data in TYPE_BYTES fields.
        out_as_utf8 = False
      else:
        out_as_utf8 = self.as_utf8
      out.write(text_encoding.CEscape(out_value, out_as_utf8))
      out.write('\"')
    elif field.cpp_type == descriptor.FieldDescriptor.CPPTYPE_BOOL:
      if value:
        out.write('true')
      else:
        out.write('false')
    elif field.cpp_type == descriptor.FieldDescriptor.CPPTYPE_FLOAT:
      if self.float_format is not None:
        out.write('{1:{0}}'.format(self.float_format, value))
      else:
        if math.isnan(value):
          out.write(str(value))
        else:
          out.write(str(type_checkers.ToShortestFloat(value)))
    elif (field.cpp_type == descriptor.FieldDescriptor.CPPTYPE_DOUBLE and
          self.double_format is not None):
      out.write('{1:{0}}'.format(self.double_format, value))
    else:
      out.write(str(value))


def Parse(text,
          message,
          allow_unknown_extension=False,
          allow_field_number=False,
          descriptor_pool=None,
          allow_unknown_field=False):
  """Parses a text representation of a protocol message into a message.

  NOTE: for historical reasons this function does not clear the input
  message. This is different from what the binary msg.ParseFrom(...) does.
  If text contains a field already set in message, the value is appended if the
  field is repeated. Otherwise, an error is raised.

  Example::

    a = MyProto()
    a.repeated_field.append('test')
    b = MyProto()

    # Repeated fields are combined
    text_format.Parse(repr(a), b)
    text_format.Parse(repr(a), b) # repeated_field contains ["test", "test"]

    # Non-repeated fields cannot be overwritten
    a.singular_field = 1
    b.singular_field = 2
    text_format.Parse(repr(a), b) # ParseError

    # Binary version:
    b.ParseFromString(a.SerializeToString()) # repeated_field is now "test"

  Caller is responsible for clearing the message as needed.

  Args:
    text (str): Message text representation.
    message (Message): A protocol buffer message to merge into.
    allow_unknown_extension: if True, skip over missing extensions and keep
      parsing
    allow_field_number: if True, both field number and field name are allowed.
    descriptor_pool (DescriptorPool): Descriptor pool used to resolve Any types.
    allow_unknown_field: if True, skip over unknown field and keep
      parsing. Avoid to use this option if possible. It may hide some
      errors (e.g. spelling error on field name)

  Returns:
    Message: The same message passed as argument.

  Raises:
    ParseError: On text parsing problems.
  """
  return ParseLines(text.split(b'\n' if isinstance(text, bytes) else u'\n'),
                    message,
                    allow_unknown_extension,
                    allow_field_number,
                    descriptor_pool=descriptor_pool,
                    allow_unknown_field=allow_unknown_field)


def Merge(text,
          message,
          allow_unknown_extension=False,
          allow_field_number=False,
          descriptor_pool=None,
          allow_unknown_field=False):
  """Parses a text representation of a protocol message into a message.

  Like Parse(), but allows repeated values for a non-repeated field, and uses
  the last one. This means any non-repeated, top-level fields specified in text
  replace those in the message.

  Args:
    text (str): Message text representation.
    message (Message): A protocol buffer message to merge into.
    allow_unknown_extension: if True, skip over missing extensions and keep
      parsing
    allow_field_number: if True, both field number and field name are allowed.
    descriptor_pool (DescriptorPool): Descriptor pool used to resolve Any types.
    allow_unknown_field: if True, skip over unknown field and keep
      parsing. Avoid to use this option if possible. It may hide some
      errors (e.g. spelling error on field name)

  Returns:
    Message: The same message passed as argument.

  Raises:
    ParseError: On text parsing problems.
  """
  return MergeLines(
      text.split(b'\n' if isinstance(text, bytes) else u'\n'),
      message,
      allow_unknown_extension,
      allow_field_number,
      descriptor_pool=descriptor_pool,
      allow_unknown_field=allow_unknown_field)


def ParseLines(lines,
               message,
               allow_unknown_extension=False,
               allow_field_number=False,
               descriptor_pool=None,
               allow_unknown_field=False):
  """Parses a text representation of a protocol message into a message.

  See Parse() for caveats.

  Args:
    lines: An iterable of lines of a message's text representation.
    message: A protocol buffer message to merge into.
    allow_unknown_extension: if True, skip over missing extensions and keep
      parsing
    allow_field_number: if True, both field number and field name are allowed.
    descriptor_pool: A DescriptorPool used to resolve Any types.
    allow_unknown_field: if True, skip over unknown field and keep
      parsing. Avoid to use this option if possible. It may hide some
      errors (e.g. spelling error on field name)

  Returns:
    The same message passed as argument.

  Raises:
    ParseError: On text parsing problems.
  """
  parser = _Parser(allow_unknown_extension,
                   allow_field_number,
                   descriptor_pool=descriptor_pool,
                   allow_unknown_field=allow_unknown_field)
  return parser.ParseLines(lines, message)


def MergeLines(lines,
               message,
               allow_unknown_extension=False,
               allow_field_number=False,
               descriptor_pool=None,
               allow_unknown_field=False):
  """Parses a text representation of a protocol message into a message.

  See Merge() for more details.

  Args:
    lines: An iterable of lines of a message's text representation.
    message: A protocol buffer message to merge into.
    allow_unknown_extension: if True, skip over missing extensions and keep
      parsing
    allow_field_number: if True, both field number and field name are allowed.
    descriptor_pool: A DescriptorPool used to resolve Any types.
    allow_unknown_field: if True, skip over unknown field and keep
      parsing. Avoid to use this option if possible. It may hide some
      errors (e.g. spelling error on field name)

  Returns:
    The same message passed as argument.

  Raises:
    ParseError: On text parsing problems.
  """
  parser = _Parser(allow_unknown_extension,
                   allow_field_number,
                   descriptor_pool=descriptor_pool,
                   allow_unknown_field=allow_unknown_field)
  return parser.MergeLines(lines, message)


class _Parser(object):
  """Text format parser for protocol message."""

  def __init__(self,
               allow_unknown_extension=False,
               allow_field_number=False,
               descriptor_pool=None,
               allow_unknown_field=False):
    self.allow_unknown_extension = allow_unknown_extension
    self.allow_field_number = allow_field_number
    self.descriptor_pool = descriptor_pool
    self.allow_unknown_field = allow_unknown_field

  def ParseLines(self, lines, message):
    """Parses a text representation of a protocol message into a message."""
    self._allow_multiple_scalars = False
    self._ParseOrMerge(lines, message)
    return message

  def MergeLines(self, lines, message):
    """Merges a text representation of a protocol message into a message."""
    self._allow_multiple_scalars = True
    self._ParseOrMerge(lines, message)
    return message

  def _ParseOrMerge(self, lines, message):
    """Converts a text representation of a protocol message into a message.

    Args:
      lines: Lines of a message's text representation.
      message: A protocol buffer message to merge into.

    Raises:
      ParseError: On text parsing problems.
    """
    # Tokenize expects native str lines.
    try:
      str_lines = (
          line if isinstance(line, str) else line.decode('utf-8')
          for line in lines)
      tokenizer = Tokenizer(str_lines)
    except UnicodeDecodeError as e:
      raise ParseError from e
    if message:
      self.root_type = message.DESCRIPTOR.full_name
    while not tokenizer.AtEnd():
      self._MergeField(tokenizer, message)

  def _MergeField(self, tokenizer, message):
    """Merges a single protocol message field into a message.

    Args:
      tokenizer: A tokenizer to parse the field name and values.
      message: A protocol message to record the data.

    Raises:
      ParseError: In case of text parsing problems.
    """
    message_descriptor = message.DESCRIPTOR
    if (message_descriptor.full_name == _ANY_FULL_TYPE_NAME and
        tokenizer.TryConsume('[')):
      type_url_prefix, packed_type_name = self._ConsumeAnyTypeUrl(tokenizer)
      tokenizer.Consume(']')
      tokenizer.TryConsume(':')
      self._DetectSilentMarker(tokenizer, message_descriptor.full_name,
                               type_url_prefix + '/' + packed_type_name)
      if tokenizer.TryConsume('<'):
        expanded_any_end_token = '>'
      else:
        tokenizer.Consume('{')
        expanded_any_end_token = '}'
      expanded_any_sub_message = _BuildMessageFromTypeName(packed_type_name,
                                                           self.descriptor_pool)
      # Direct comparison with None is used instead of implicit bool conversion
      # to avoid false positives with falsy initial values, e.g. for
      # google.protobuf.ListValue.
      if expanded_any_sub_message is None:
        raise ParseError('Type %s not found in descriptor pool' %
                         packed_type_name)
      while not tokenizer.TryConsume(expanded_any_end_token):
        if tokenizer.AtEnd():
          raise tokenizer.ParseErrorPreviousToken('Expected "%s".' %
                                                  (expanded_any_end_token,))
        self._MergeField(tokenizer, expanded_any_sub_message)
      deterministic = False

      message.Pack(expanded_any_sub_message,
                   type_url_prefix=type_url_prefix,
                   deterministic=deterministic)
      return

    if tokenizer.TryConsume('['):
      name = [tokenizer.ConsumeIdentifier()]
      while tokenizer.TryConsume('.'):
        name.append(tokenizer.ConsumeIdentifier())
      name = '.'.join(name)

      if not message_descriptor.is_extendable:
        raise tokenizer.ParseErrorPreviousToken(
            'Message type "%s" does not have extensions.' %
            message_descriptor.full_name)
      # pylint: disable=protected-access
      field = message.Extensions._FindExtensionByName(name)
      # pylint: enable=protected-access
      if not field:
        if self.allow_unknown_extension:
          field = None
        else:
          raise tokenizer.ParseErrorPreviousToken(
              'Extension "%s" not registered. '
              'Did you import the _pb2 module which defines it? '
              'If you are trying to place the extension in the MessageSet '
              'field of another message that is in an Any or MessageSet field, '
              'that message\'s _pb2 module must be imported as well' % name)
      elif message_descriptor != field.containing_type:
        raise tokenizer.ParseErrorPreviousToken(
            'Extension "%s" does not extend message type "%s".' %
            (name, message_descriptor.full_name))

      tokenizer.Consume(']')

    else:
      name = tokenizer.ConsumeIdentifierOrNumber()
      if self.allow_field_number and name.isdigit():
        number = ParseInteger(name, True, True)
        field = message_descriptor.fields_by_number.get(number, None)
        if not field and message_descriptor.is_extendable:
          field = message.Extensions._FindExtensionByNumber(number)
      else:
        field = message_descriptor.fields_by_name.get(name, None)

        # Group names are expected to be capitalized as they appear in the
        # .proto file, which actually matches their type names, not their field
        # names.
        if not field:
          field = message_descriptor.fields_by_name.get(name.lower(), None)
          if field and field.type != descriptor.FieldDescriptor.TYPE_GROUP:
            field = None

        if (field and field.type == descriptor.FieldDescriptor.TYPE_GROUP and
            field.message_type.name != name):
          field = None

      if not field and not self.allow_unknown_field:
        raise tokenizer.ParseErrorPreviousToken(
            'Message type "%s" has no field named "%s".' %
            (message_descriptor.full_name, name))

    if field:
      if not self._allow_multiple_scalars and field.containing_oneof:
        # Check if there's a different field set in this oneof.
        # Note that we ignore the case if the same field was set before, and we
        # apply _allow_multiple_scalars to non-scalar fields as well.
        which_oneof = message.WhichOneof(field.containing_oneof.name)
        if which_oneof is not None and which_oneof != field.name:
          raise tokenizer.ParseErrorPreviousToken(
              'Field "%s" is specified along with field "%s", another member '
              'of oneof "%s" for message type "%s".' %
              (field.name, which_oneof, field.containing_oneof.name,
               message_descriptor.full_name))

      if field.cpp_type == descriptor.FieldDescriptor.CPPTYPE_MESSAGE:
        tokenizer.TryConsume(':')
        self._DetectSilentMarker(tokenizer, message_descriptor.full_name,
                                 field.full_name)
        merger = self._MergeMessageField
      else:
        tokenizer.Consume(':')
        self._DetectSilentMarker(tokenizer, message_descriptor.full_name,
                                 field.full_name)
        merger = self._MergeScalarField

      if (field.label == descriptor.FieldDescriptor.LABEL_REPEATED and
          tokenizer.TryConsume('[')):
        # Short repeated format, e.g. "foo: [1, 2, 3]"
        if not tokenizer.TryConsume(']'):
          while True:
            merger(tokenizer, message, field)
            if tokenizer.TryConsume(']'):
              break
            tokenizer.Consume(',')

      else:
        merger(tokenizer, message, field)

    else:  # Proto field is unknown.
      assert (self.allow_unknown_extension or self.allow_unknown_field)
      self._SkipFieldContents(tokenizer, name, message_descriptor.full_name)

    # For historical reasons, fields may optionally be separated by commas or
    # semicolons.
    if not tokenizer.TryConsume(','):
      tokenizer.TryConsume(';')

  def _LogSilentMarker(self, immediate_message_type, field_name):
    pass

  def _DetectSilentMarker(self, tokenizer, immediate_message_type, field_name):
    if tokenizer.contains_silent_marker_before_current_token:
      self._LogSilentMarker(immediate_message_type, field_name)

  def _ConsumeAnyTypeUrl(self, tokenizer):
    """Consumes a google.protobuf.Any type URL and returns the type name."""
    # Consume "type.googleapis.com/".
    prefix = [tokenizer.ConsumeIdentifier()]
    tokenizer.Consume('.')
    prefix.append(tokenizer.ConsumeIdentifier())
    tokenizer.Consume('.')
    prefix.append(tokenizer.ConsumeIdentifier())
    tokenizer.Consume('/')
    # Consume the fully-qualified type name.
    name = [tokenizer.ConsumeIdentifier()]
    while tokenizer.TryConsume('.'):
      name.append(tokenizer.ConsumeIdentifier())
    return '.'.join(prefix), '.'.join(name)

  def _MergeMessageField(self, tokenizer, message, field):
    """Merges a single scalar field into a message.

    Args:
      tokenizer: A tokenizer to parse the field value.
      message: The message of which field is a member.
      field: The descriptor of the field to be merged.

    Raises:
      ParseError: In case of text parsing problems.
    """
    is_map_entry = _IsMapEntry(field)

    if tokenizer.TryConsume('<'):
      end_token = '>'
    else:
      tokenizer.Consume('{')
      end_token = '}'

    if field.label == descriptor.FieldDescriptor.LABEL_REPEATED:
      if field.is_extension:
        sub_message = message.Extensions[field].add()
      elif is_map_entry:
        sub_message = getattr(message, field.name).GetEntryClass()()
      else:
        sub_message = getattr(message, field.name).add()
    else:
      if field.is_extension:
        if (not self._allow_multiple_scalars and
            message.HasExtension(field)):
          raise tokenizer.ParseErrorPreviousToken(
              'Message type "%s" should not have multiple "%s" extensions.' %
              (message.DESCRIPTOR.full_name, field.full_name))
        sub_message = message.Extensions[field]
      else:
        # Also apply _allow_multiple_scalars to message field.
        # TODO: Change to _allow_singular_overwrites.
        if (not self._allow_multiple_scalars and
            message.HasField(field.name)):
          raise tokenizer.ParseErrorPreviousToken(
              'Message type "%s" should not have multiple "%s" fields.' %
              (message.DESCRIPTOR.full_name, field.name))
        sub_message = getattr(message, field.name)
      sub_message.SetInParent()

    while not tokenizer.TryConsume(end_token):
      if tokenizer.AtEnd():
        raise tokenizer.ParseErrorPreviousToken('Expected "%s".' % (end_token,))
      self._MergeField(tokenizer, sub_message)

    if is_map_entry:
      value_cpptype = field.message_type.fields_by_name['value'].cpp_type
      if value_cpptype == descriptor.FieldDescriptor.CPPTYPE_MESSAGE:
        value = getattr(message, field.name)[sub_message.key]
        value.CopyFrom(sub_message.value)
      else:
        getattr(message, field.name)[sub_message.key] = sub_message.value

  def _MergeScalarField(self, tokenizer, message, field):
    """Merges a single scalar field into a message.

    Args:
      tokenizer: A tokenizer to parse the field value.
      message: A protocol message to record the data.
      field: The descriptor of the field to be merged.

    Raises:
      ParseError: In case of text parsing problems.
      RuntimeError: On runtime errors.
    """
    _ = self.allow_unknown_extension
    value = None

    if field.type in (descriptor.FieldDescriptor.TYPE_INT32,
                      descriptor.FieldDescriptor.TYPE_SINT32,
                      descriptor.FieldDescriptor.TYPE_SFIXED32):
      value = _ConsumeInt32(tokenizer)
    elif field.type in (descriptor.FieldDescriptor.TYPE_INT64,
                        descriptor.FieldDescriptor.TYPE_SINT64,
                        descriptor.FieldDescriptor.TYPE_SFIXED64):
      value = _ConsumeInt64(tokenizer)
    elif field.type in (descriptor.FieldDescriptor.TYPE_UINT32,
                        descriptor.FieldDescriptor.TYPE_FIXED32):
      value = _ConsumeUint32(tokenizer)
    elif field.type in (descriptor.FieldDescriptor.TYPE_UINT64,
                        descriptor.FieldDescriptor.TYPE_FIXED64):
      value = _ConsumeUint64(tokenizer)
    elif field.type in (descriptor.FieldDescriptor.TYPE_FLOAT,
                        descriptor.FieldDescriptor.TYPE_DOUBLE):
      value = tokenizer.ConsumeFloat()
    elif field.type == descriptor.FieldDescriptor.TYPE_BOOL:
      value = tokenizer.ConsumeBool()
    elif field.type == descriptor.FieldDescriptor.TYPE_STRING:
      value = tokenizer.ConsumeString()
    elif field.type == descriptor.FieldDescriptor.TYPE_BYTES:
      value = tokenizer.ConsumeByteString()
    elif field.type == descriptor.FieldDescriptor.TYPE_ENUM:
      value = tokenizer.ConsumeEnum(field)
    else:
      raise RuntimeError('Unknown field type %d' % field.type)

    if field.label == descriptor.FieldDescriptor.LABEL_REPEATED:
      if field.is_extension:
        message.Extensions[field].append(value)
      else:
        getattr(message, field.name).append(value)
    else:
      if field.is_extension:
        if (not self._allow_multiple_scalars and
            field.has_presence and
            message.HasExtension(field)):
          raise tokenizer.ParseErrorPreviousToken(
              'Message type "%s" should not have multiple "%s" extensions.' %
              (message.DESCRIPTOR.full_name, field.full_name))
        else:
          message.Extensions[field] = value
      else:
        duplicate_error = False
        if not self._allow_multiple_scalars:
          if field.has_presence:
            duplicate_error = message.HasField(field.name)
          else:
            # For field that doesn't represent presence, try best effort to
            # check multiple scalars by compare to default values.
            duplicate_error = bool(getattr(message, field.name))

        if duplicate_error:
          raise tokenizer.ParseErrorPreviousToken(
              'Message type "%s" should not have multiple "%s" fields.' %
              (message.DESCRIPTOR.full_name, field.name))
        else:
          setattr(message, field.name, value)

  def _SkipFieldContents(self, tokenizer, field_name, immediate_message_type):
    """Skips over contents (value or message) of a field.

    Args:
      tokenizer: A tokenizer to parse the field name and values.
      field_name: The field name currently being parsed.
      immediate_message_type: The type of the message immediately containing
        the silent marker.
    """
    # Try to guess the type of this field.
    # If this field is not a message, there should be a ":" between the
    # field name and the field value and also the field value should not
    # start with "{" or "<" which indicates the beginning of a message body.
    # If there is no ":" or there is a "{" or "<" after ":", this field has
    # to be a message or the input is ill-formed.
    if tokenizer.TryConsume(
        ':') and not tokenizer.LookingAt('{') and not tokenizer.LookingAt('<'):
      self._DetectSilentMarker(tokenizer, immediate_message_type, field_name)
      if tokenizer.LookingAt('['):
        self._SkipRepeatedFieldValue(tokenizer)
      else:
        self._SkipFieldValue(tokenizer)
    else:
      self._DetectSilentMarker(tokenizer, immediate_message_type, field_name)
      self._SkipFieldMessage(tokenizer, immediate_message_type)

  def _SkipField(self, tokenizer, immediate_message_type):
    """Skips over a complete field (name and value/message).

    Args:
      tokenizer: A tokenizer to parse the field name and values.
      immediate_message_type: The type of the message immediately containing
        the silent marker.
    """
    field_name = ''
    if tokenizer.TryConsume('['):
      # Consume extension or google.protobuf.Any type URL
      field_name += '[' + tokenizer.ConsumeIdentifier()
      num_identifiers = 1
      while tokenizer.TryConsume('.'):
        field_name += '.' + tokenizer.ConsumeIdentifier()
        num_identifiers += 1
      # This is possibly a type URL for an Any message.
      if num_identifiers == 3 and tokenizer.TryConsume('/'):
        field_name += '/' + tokenizer.ConsumeIdentifier()
        while tokenizer.TryConsume('.'):
          field_name += '.' + tokenizer.ConsumeIdentifier()
      tokenizer.Consume(']')
      field_name += ']'
    else:
      field_name += tokenizer.ConsumeIdentifierOrNumber()

    self._SkipFieldContents(tokenizer, field_name, immediate_message_type)

    # For historical reasons, fields may optionally be separated by commas or
    # semicolons.
    if not tokenizer.TryConsume(','):
      tokenizer.TryConsume(';')

  def _SkipFieldMessage(self, tokenizer, immediate_message_type):
    """Skips over a field message.

    Args:
      tokenizer: A tokenizer to parse the field name and values.
      immediate_message_type: The type of the message immediately containing
        the silent marker
    """
    if tokenizer.TryConsume('<'):
      delimiter = '>'
    else:
      tokenizer.Consume('{')
      delimiter = '}'

    while not tokenizer.LookingAt('>') and not tokenizer.LookingAt('}'):
      self._SkipField(tokenizer, immediate_message_type)

    tokenizer.Consume(delimiter)

  def _SkipFieldValue(self, tokenizer):
    """Skips over a field value.

    Args:
      tokenizer: A tokenizer to parse the field name and values.

    Raises:
      ParseError: In case an invalid field value is found.
    """
    if (not tokenizer.TryConsumeByteString()and
        not tokenizer.TryConsumeIdentifier() and
        not _TryConsumeInt64(tokenizer) and
        not _TryConsumeUint64(tokenizer) and
        not tokenizer.TryConsumeFloat()):
      raise ParseError('Invalid field value: ' + tokenizer.token)

  def _SkipRepeatedFieldValue(self, tokenizer):
    """Skips over a repeated field value.

    Args:
      tokenizer: A tokenizer to parse the field value.
    """
    tokenizer.Consume('[')
    if not tokenizer.LookingAt(']'):
      self._SkipFieldValue(tokenizer)
      while tokenizer.TryConsume(','):
        self._SkipFieldValue(tokenizer)
    tokenizer.Consume(']')


class Tokenizer(object):
  """Protocol buffer text representation tokenizer.

  This class handles the lower level string parsing by splitting it into
  meaningful tokens.

  It was directly ported from the Java protocol buffer API.
  """

  _WHITESPACE = re.compile(r'\s+')
  _COMMENT = re.compile(r'(\s*#.*$)', re.MULTILINE)
  _WHITESPACE_OR_COMMENT = re.compile(r'(\s|(#.*$))+', re.MULTILINE)
  _TOKEN = re.compile('|'.join([
      r'[a-zA-Z_][0-9a-zA-Z_+-]*',  # an identifier
      r'([0-9+-]|(\.[0-9]))[0-9a-zA-Z_.+-]*',  # a number
  ] + [  # quoted str for each quote mark
      # Avoid backtracking! https://stackoverflow.com/a/844267
      r'{qt}[^{qt}\n\\]*((\\.)+[^{qt}\n\\]*)*({qt}|\\?$)'.format(qt=mark)
      for mark in _QUOTES
  ]))

  _IDENTIFIER = re.compile(r'[^\d\W]\w*')
  _IDENTIFIER_OR_NUMBER = re.compile(r'\w+')

  def __init__(self, lines, skip_comments=True):
    self._position = 0
    self._line = -1
    self._column = 0
    self._token_start = None
    self.token = ''
    self._lines = iter(lines)
    self._current_line = ''
    self._previous_line = 0
    self._previous_column = 0
    self._more_lines = True
    self._skip_comments = skip_comments
    self._whitespace_pattern = (skip_comments and self._WHITESPACE_OR_COMMENT
                                or self._WHITESPACE)
    self.contains_silent_marker_before_current_token = False

    self._SkipWhitespace()
    self.NextToken()

  def LookingAt(self, token):
    return self.token == token

  def AtEnd(self):
    """Checks the end of the text was reached.

    Returns:
      True iff the end was reached.
    """
    return not self.token

  def _PopLine(self):
    while len(self._current_line) <= self._column:
      try:
        self._current_line = next(self._lines)
      except StopIteration:
        self._current_line = ''
        self._more_lines = False
        return
      else:
        self._line += 1
        self._column = 0

  def _SkipWhitespace(self):
    while True:
      self._PopLine()
      match = self._whitespace_pattern.match(self._current_line, self._column)
      if not match:
        break
      self.contains_silent_marker_before_current_token = match.group(0) == (
          ' ' + _DEBUG_STRING_SILENT_MARKER)
      length = len(match.group(0))
      self._column += length

  def TryConsume(self, token):
    """Tries to consume a given piece of text.

    Args:
      token: Text to consume.

    Returns:
      True iff the text was consumed.
    """
    if self.token == token:
      self.NextToken()
      return True
    return False

  def Consume(self, token):
    """Consumes a piece of text.

    Args:
      token: Text to consume.

    Raises:
      ParseError: If the text couldn't be consumed.
    """
    if not self.TryConsume(token):
      raise self.ParseError('Expected "%s".' % token)

  def ConsumeComment(self):
    result = self.token
    if not self._COMMENT.match(result):
      raise self.ParseError('Expected comment.')
    self.NextToken()
    return result

  def ConsumeCommentOrTrailingComment(self):
    """Consumes a comment, returns a 2-tuple (trailing bool, comment str)."""

    # Tokenizer initializes _previous_line and _previous_column to 0. As the
    # tokenizer starts, it looks like there is a previous token on the line.
    just_started = self._line == 0 and self._column == 0

    before_parsing = self._previous_line
    comment = self.ConsumeComment()

    # A trailing comment is a comment on the same line than the previous token.
    trailing = (self._previous_line == before_parsing
                and not just_started)

    return trailing, comment

  def TryConsumeIdentifier(self):
    try:
      self.ConsumeIdentifier()
      return True
    except ParseError:
      return False

  def ConsumeIdentifier(self):
    """Consumes protocol message field identifier.

    Returns:
      Identifier string.

    Raises:
      ParseError: If an identifier couldn't be consumed.
    """
    result = self.token
    if not self._IDENTIFIER.match(result):
      raise self.ParseError('Expected identifier.')
    self.NextToken()
    return result

  def TryConsumeIdentifierOrNumber(self):
    try:
      self.ConsumeIdentifierOrNumber()
      return True
    except ParseError:
      return False

  def ConsumeIdentifierOrNumber(self):
    """Consumes protocol message field identifier.

    Returns:
      Identifier string.

    Raises:
      ParseError: If an identifier couldn't be consumed.
    """
    result = self.token
    if not self._IDENTIFIER_OR_NUMBER.match(result):
      raise self.ParseError('Expected identifier or number, got %s.' % result)
    self.NextToken()
    return result

  def TryConsumeInteger(self):
    try:
      self.ConsumeInteger()
      return True
    except ParseError:
      return False

  def ConsumeInteger(self):
    """Consumes an integer number.

    Returns:
      The integer parsed.

    Raises:
      ParseError: If an integer couldn't be consumed.
    """
    try:
      result = _ParseAbstractInteger(self.token)
    except ValueError as e:
      raise self.ParseError(str(e))
    self.NextToken()
    return result

  def TryConsumeFloat(self):
    try:
      self.ConsumeFloat()
      return True
    except ParseError:
      return False

  def ConsumeFloat(self):
    """Consumes an floating point number.

    Returns:
      The number parsed.

    Raises:
      ParseError: If a floating point number couldn't be consumed.
    """
    try:
      result = ParseFloat(self.token)
    except ValueError as e:
      raise self.ParseError(str(e))
    self.NextToken()
    return result

  def ConsumeBool(self):
    """Consumes a boolean value.

    Returns:
      The bool parsed.

    Raises:
      ParseError: If a boolean value couldn't be consumed.
    """
    try:
      result = ParseBool(self.token)
    except ValueError as e:
      raise self.ParseError(str(e))
    self.NextToken()
    return result

  def TryConsumeByteString(self):
    try:
      self.ConsumeByteString()
      return True
    except ParseError:
      return False

  def ConsumeString(self):
    """Consumes a string value.

    Returns:
      The string parsed.

    Raises:
      ParseError: If a string value couldn't be consumed.
    """
    the_bytes = self.ConsumeByteString()
    try:
      return str(the_bytes, 'utf-8')
    except UnicodeDecodeError as e:
      raise self._StringParseError(e)

  def ConsumeByteString(self):
    """Consumes a byte array value.

    Returns:
      The array parsed (as a string).

    Raises:
      ParseError: If a byte array value couldn't be consumed.
    """
    the_list = [self._ConsumeSingleByteString()]
    while self.token and self.token[0] in _QUOTES:
      the_list.append(self._ConsumeSingleByteString())
    return b''.join(the_list)

  def _ConsumeSingleByteString(self):
    """Consume one token of a string literal.

    String literals (whether bytes or text) can come in multiple adjacent
    tokens which are automatically concatenated, like in C or Python.  This
    method only consumes one token.

    Returns:
      The token parsed.
    Raises:
      ParseError: When the wrong format data is found.
    """
    text = self.token
    if len(text) < 1 or text[0] not in _QUOTES:
      raise self.ParseError('Expected string but found: %r' % (text,))

    if len(text) < 2 or text[-1] != text[0]:
      raise self.ParseError('String missing ending quote: %r' % (text,))

    try:
      result = text_encoding.CUnescape(text[1:-1])
    except ValueError as e:
      raise self.ParseError(str(e))
    self.NextToken()
    return result

  def ConsumeEnum(self, field):
    try:
      result = ParseEnum(field, self.token)
    except ValueError as e:
      raise self.ParseError(str(e))
    self.NextToken()
    return result

  def ParseErrorPreviousToken(self, message):
    """Creates and *returns* a ParseError for the previously read token.

    Args:
      message: A message to set for the exception.

    Returns:
      A ParseError instance.
    """
    return ParseError(message, self._previous_line + 1,
                      self._previous_column + 1)

  def ParseError(self, message):
    """Creates and *returns* a ParseError for the current token."""
    return ParseError('\'' + self._current_line + '\': ' + message,
                      self._line + 1, self._column + 1)

  def _StringParseError(self, e):
    return self.ParseError('Couldn\'t parse string: ' + str(e))

  def NextToken(self):
    """Reads the next meaningful token."""
    self._previous_line = self._line
    self._previous_column = self._column
    self.contains_silent_marker_before_current_token = False

    self._column += len(self.token)
    self._SkipWhitespace()

    if not self._more_lines:
      self.token = ''
      return

    match = self._TOKEN.match(self._current_line, self._column)
    if not match and not self._skip_comments:
      match = self._COMMENT.match(self._current_line, self._column)
    if match:
      token = match.group(0)
      self.token = token
    else:
      self.token = self._current_line[self._column]

# Aliased so it can still be accessed by current visibility violators.
# TODO: Migrate violators to textformat_tokenizer.
_Tokenizer = Tokenizer  # pylint: disable=invalid-name


def _ConsumeInt32(tokenizer):
  """Consumes a signed 32bit integer number from tokenizer.

  Args:
    tokenizer: A tokenizer used to parse the number.

  Returns:
    The integer parsed.

  Raises:
    ParseError: If a signed 32bit integer couldn't be consumed.
  """
  return _ConsumeInteger(tokenizer, is_signed=True, is_long=False)


def _ConsumeUint32(tokenizer):
  """Consumes an unsigned 32bit integer number from tokenizer.

  Args:
    tokenizer: A tokenizer used to parse the number.

  Returns:
    The integer parsed.

  Raises:
    ParseError: If an unsigned 32bit integer couldn't be consumed.
  """
  return _ConsumeInteger(tokenizer, is_signed=False, is_long=False)


def _TryConsumeInt64(tokenizer):
  try:
    _ConsumeInt64(tokenizer)
    return True
  except ParseError:
    return False


def _ConsumeInt64(tokenizer):
  """Consumes a signed 32bit integer number from tokenizer.

  Args:
    tokenizer: A tokenizer used to parse the number.

  Returns:
    The integer parsed.

  Raises:
    ParseError: If a signed 32bit integer couldn't be consumed.
  """
  return _ConsumeInteger(tokenizer, is_signed=True, is_long=True)


def _TryConsumeUint64(tokenizer):
  try:
    _ConsumeUint64(tokenizer)
    return True
  except ParseError:
    return False


def _ConsumeUint64(tokenizer):
  """Consumes an unsigned 64bit integer number from tokenizer.

  Args:
    tokenizer: A tokenizer used to parse the number.

  Returns:
    The integer parsed.

  Raises:
    ParseError: If an unsigned 64bit integer couldn't be consumed.
  """
  return _ConsumeInteger(tokenizer, is_signed=False, is_long=True)


def _ConsumeInteger(tokenizer, is_signed=False, is_long=False):
  """Consumes an integer number from tokenizer.

  Args:
    tokenizer: A tokenizer used to parse the number.
    is_signed: True if a signed integer must be parsed.
    is_long: True if a long integer must be parsed.

  Returns:
    The integer parsed.

  Raises:
    ParseError: If an integer with given characteristics couldn't be consumed.
  """
  try:
    result = ParseInteger(tokenizer.token, is_signed=is_signed, is_long=is_long)
  except ValueError as e:
    raise tokenizer.ParseError(str(e))
  tokenizer.NextToken()
  return result


def ParseInteger(text, is_signed=False, is_long=False):
  """Parses an integer.

  Args:
    text: The text to parse.
    is_signed: True if a signed integer must be parsed.
    is_long: True if a long integer must be parsed.

  Returns:
    The integer value.

  Raises:
    ValueError: Thrown Iff the text is not a valid integer.
  """
  # Do the actual parsing. Exception handling is propagated to caller.
  result = _ParseAbstractInteger(text)

  # Check if the integer is sane. Exceptions handled by callers.
  checker = _INTEGER_CHECKERS[2 * int(is_long) + int(is_signed)]
  checker.CheckValue(result)
  return result


def _ParseAbstractInteger(text):
  """Parses an integer without checking size/signedness.

  Args:
    text: The text to parse.

  Returns:
    The integer value.

  Raises:
    ValueError: Thrown Iff the text is not a valid integer.
  """
  # Do the actual parsing. Exception handling is propagated to caller.
  orig_text = text
  c_octal_match = re.match(r'(-?)0(\d+)$', text)
  if c_octal_match:
    # Python 3 no longer supports 0755 octal syntax without the 'o', so
    # we always use the '0o' prefix for multi-digit numbers starting with 0.
    text = c_octal_match.group(1) + '0o' + c_octal_match.group(2)
  try:
    return int(text, 0)
  except ValueError:
    raise ValueError('Couldn\'t parse integer: %s' % orig_text)


def ParseFloat(text):
  """Parse a floating point number.

  Args:
    text: Text to parse.

  Returns:
    The number parsed.

  Raises:
    ValueError: If a floating point number couldn't be parsed.
  """
  try:
    # Assume Python compatible syntax.
    return float(text)
  except ValueError:
    # Check alternative spellings.
    if _FLOAT_INFINITY.match(text):
      if text[0] == '-':
        return float('-inf')
      else:
        return float('inf')
    elif _FLOAT_NAN.match(text):
      return float('nan')
    else:
      # assume '1.0f' format
      try:
        return float(text.rstrip('f'))
      except ValueError:
        raise ValueError('Couldn\'t parse float: %s' % text)


def ParseBool(text):
  """Parse a boolean value.

  Args:
    text: Text to parse.

  Returns:
    Boolean values parsed

  Raises:
    ValueError: If text is not a valid boolean.
  """
  if text in ('true', 't', '1', 'True'):
    return True
  elif text in ('false', 'f', '0', 'False'):
    return False
  else:
    raise ValueError('Expected "true" or "false".')


def ParseEnum(field, value):
  """Parse an enum value.

  The value can be specified by a number (the enum value), or by
  a string literal (the enum name).

  Args:
    field: Enum field descriptor.
    value: String value.

  Returns:
    Enum value number.

  Raises:
    ValueError: If the enum value could not be parsed.
  """
  enum_descriptor = field.enum_type
  try:
    number = int(value, 0)
  except ValueError:
    # Identifier.
    enum_value = enum_descriptor.values_by_name.get(value, None)
    if enum_value is None:
      raise ValueError('Enum type "%s" has no value named %s.' %
                       (enum_descriptor.full_name, value))
  else:
    if not field.enum_type.is_closed:
      return number
    enum_value = enum_descriptor.values_by_number.get(number, None)
    if enum_value is None:
      raise ValueError('Enum type "%s" has no value with number %d.' %
                       (enum_descriptor.full_name, number))
  return enum_value.number

# === NexusCore/openenv\Lib\site-packages\debugpy\_vendored\pydevd\pydevd_attach_to_process\winappdbg\win32\user32.py ===
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
Wrapper for user32.dll in ctypes.
"""

__revision__ = "$Id$"

from winappdbg.win32.defines import *
from winappdbg.win32.version import bits
from winappdbg.win32.kernel32 import GetLastError, SetLastError
from winappdbg.win32.gdi32 import POINT, PPOINT, LPPOINT, RECT, PRECT, LPRECT

# ==============================================================================
# This is used later on to calculate the list of exported symbols.
_all = None
_all = set(vars().keys())
# ==============================================================================

# --- Helpers ------------------------------------------------------------------


def MAKE_WPARAM(wParam):
    """
    Convert arguments to the WPARAM type.
    Used automatically by SendMessage, PostMessage, etc.
    You shouldn't need to call this function.
    """
    wParam = ctypes.cast(wParam, LPVOID).value
    if wParam is None:
        wParam = 0
    return wParam


def MAKE_LPARAM(lParam):
    """
    Convert arguments to the LPARAM type.
    Used automatically by SendMessage, PostMessage, etc.
    You shouldn't need to call this function.
    """
    return ctypes.cast(lParam, LPARAM)


class __WindowEnumerator(object):
    """
    Window enumerator class. Used internally by the window enumeration APIs.
    """

    def __init__(self):
        self.hwnd = list()

    def __call__(self, hwnd, lParam):
        ##        print hwnd  # XXX DEBUG
        self.hwnd.append(hwnd)
        return TRUE


# --- Types --------------------------------------------------------------------

WNDENUMPROC = WINFUNCTYPE(BOOL, HWND, PVOID)

# --- Constants ----------------------------------------------------------------

HWND_DESKTOP = 0
HWND_TOP = 1
HWND_BOTTOM = 1
HWND_TOPMOST = -1
HWND_NOTOPMOST = -2
HWND_MESSAGE = -3

# GetWindowLong / SetWindowLong
GWL_WNDPROC = -4
GWL_HINSTANCE = -6
GWL_HWNDPARENT = -8
GWL_ID = -12
GWL_STYLE = -16
GWL_EXSTYLE = -20
GWL_USERDATA = -21

# GetWindowLongPtr / SetWindowLongPtr
GWLP_WNDPROC = GWL_WNDPROC
GWLP_HINSTANCE = GWL_HINSTANCE
GWLP_HWNDPARENT = GWL_HWNDPARENT
GWLP_STYLE = GWL_STYLE
GWLP_EXSTYLE = GWL_EXSTYLE
GWLP_USERDATA = GWL_USERDATA
GWLP_ID = GWL_ID

# ShowWindow
SW_HIDE = 0
SW_SHOWNORMAL = 1
SW_NORMAL = 1
SW_SHOWMINIMIZED = 2
SW_SHOWMAXIMIZED = 3
SW_MAXIMIZE = 3
SW_SHOWNOACTIVATE = 4
SW_SHOW = 5
SW_MINIMIZE = 6
SW_SHOWMINNOACTIVE = 7
SW_SHOWNA = 8
SW_RESTORE = 9
SW_SHOWDEFAULT = 10
SW_FORCEMINIMIZE = 11

# SendMessageTimeout flags
SMTO_NORMAL = 0
SMTO_BLOCK = 1
SMTO_ABORTIFHUNG = 2
SMTO_NOTIMEOUTIFNOTHUNG = 8
SMTO_ERRORONEXIT = 0x20

# WINDOWPLACEMENT flags
WPF_SETMINPOSITION = 1
WPF_RESTORETOMAXIMIZED = 2
WPF_ASYNCWINDOWPLACEMENT = 4

# GetAncestor flags
GA_PARENT = 1
GA_ROOT = 2
GA_ROOTOWNER = 3

# GetWindow flags
GW_HWNDFIRST = 0
GW_HWNDLAST = 1
GW_HWNDNEXT = 2
GW_HWNDPREV = 3
GW_OWNER = 4
GW_CHILD = 5
GW_ENABLEDPOPUP = 6

# --- Window messages ----------------------------------------------------------

WM_USER = 0x400
WM_APP = 0x800

WM_NULL = 0
WM_CREATE = 1
WM_DESTROY = 2
WM_MOVE = 3
WM_SIZE = 5
WM_ACTIVATE = 6
WA_INACTIVE = 0
WA_ACTIVE = 1
WA_CLICKACTIVE = 2
WM_SETFOCUS = 7
WM_KILLFOCUS = 8
WM_ENABLE = 0x0A
WM_SETREDRAW = 0x0B
WM_SETTEXT = 0x0C
WM_GETTEXT = 0x0D
WM_GETTEXTLENGTH = 0x0E
WM_PAINT = 0x0F
WM_CLOSE = 0x10
WM_QUERYENDSESSION = 0x11
WM_QUIT = 0x12
WM_QUERYOPEN = 0x13
WM_ERASEBKGND = 0x14
WM_SYSCOLORCHANGE = 0x15
WM_ENDSESSION = 0x16
WM_SHOWWINDOW = 0x18
WM_WININICHANGE = 0x1A
WM_SETTINGCHANGE = WM_WININICHANGE
WM_DEVMODECHANGE = 0x1B
WM_ACTIVATEAPP = 0x1C
WM_FONTCHANGE = 0x1D
WM_TIMECHANGE = 0x1E
WM_CANCELMODE = 0x1F
WM_SETCURSOR = 0x20
WM_MOUSEACTIVATE = 0x21
WM_CHILDACTIVATE = 0x22
WM_QUEUESYNC = 0x23
WM_GETMINMAXINFO = 0x24
WM_PAINTICON = 0x26
WM_ICONERASEBKGND = 0x27
WM_NEXTDLGCTL = 0x28
WM_SPOOLERSTATUS = 0x2A
WM_DRAWITEM = 0x2B
WM_MEASUREITEM = 0x2C
WM_DELETEITEM = 0x2D
WM_VKEYTOITEM = 0x2E
WM_CHARTOITEM = 0x2F
WM_SETFONT = 0x30
WM_GETFONT = 0x31
WM_SETHOTKEY = 0x32
WM_GETHOTKEY = 0x33
WM_QUERYDRAGICON = 0x37
WM_COMPAREITEM = 0x39
WM_GETOBJECT = 0x3D
WM_COMPACTING = 0x41
WM_OTHERWINDOWCREATED = 0x42
WM_OTHERWINDOWDESTROYED = 0x43
WM_COMMNOTIFY = 0x44

CN_RECEIVE = 0x1
CN_TRANSMIT = 0x2
CN_EVENT = 0x4

WM_WINDOWPOSCHANGING = 0x46
WM_WINDOWPOSCHANGED = 0x47
WM_POWER = 0x48

PWR_OK = 1
PWR_FAIL = -1
PWR_SUSPENDREQUEST = 1
PWR_SUSPENDRESUME = 2
PWR_CRITICALRESUME = 3

WM_COPYDATA = 0x4A
WM_CANCELJOURNAL = 0x4B
WM_NOTIFY = 0x4E
WM_INPUTLANGCHANGEREQUEST = 0x50
WM_INPUTLANGCHANGE = 0x51
WM_TCARD = 0x52
WM_HELP = 0x53
WM_USERCHANGED = 0x54
WM_NOTIFYFORMAT = 0x55
WM_CONTEXTMENU = 0x7B
WM_STYLECHANGING = 0x7C
WM_STYLECHANGED = 0x7D
WM_DISPLAYCHANGE = 0x7E
WM_GETICON = 0x7F
WM_SETICON = 0x80
WM_NCCREATE = 0x81
WM_NCDESTROY = 0x82
WM_NCCALCSIZE = 0x83
WM_NCHITTEST = 0x84
WM_NCPAINT = 0x85
WM_NCACTIVATE = 0x86
WM_GETDLGCODE = 0x87
WM_SYNCPAINT = 0x88
WM_NCMOUSEMOVE = 0x0A0
WM_NCLBUTTONDOWN = 0x0A1
WM_NCLBUTTONUP = 0x0A2
WM_NCLBUTTONDBLCLK = 0x0A3
WM_NCRBUTTONDOWN = 0x0A4
WM_NCRBUTTONUP = 0x0A5
WM_NCRBUTTONDBLCLK = 0x0A6
WM_NCMBUTTONDOWN = 0x0A7
WM_NCMBUTTONUP = 0x0A8
WM_NCMBUTTONDBLCLK = 0x0A9
WM_KEYFIRST = 0x100
WM_KEYDOWN = 0x100
WM_KEYUP = 0x101
WM_CHAR = 0x102
WM_DEADCHAR = 0x103
WM_SYSKEYDOWN = 0x104
WM_SYSKEYUP = 0x105
WM_SYSCHAR = 0x106
WM_SYSDEADCHAR = 0x107
WM_KEYLAST = 0x108
WM_INITDIALOG = 0x110
WM_COMMAND = 0x111
WM_SYSCOMMAND = 0x112
WM_TIMER = 0x113
WM_HSCROLL = 0x114
WM_VSCROLL = 0x115
WM_INITMENU = 0x116
WM_INITMENUPOPUP = 0x117
WM_MENUSELECT = 0x11F
WM_MENUCHAR = 0x120
WM_ENTERIDLE = 0x121
WM_CTLCOLORMSGBOX = 0x132
WM_CTLCOLOREDIT = 0x133
WM_CTLCOLORLISTBOX = 0x134
WM_CTLCOLORBTN = 0x135
WM_CTLCOLORDLG = 0x136
WM_CTLCOLORSCROLLBAR = 0x137
WM_CTLCOLORSTATIC = 0x138
WM_MOUSEFIRST = 0x200
WM_MOUSEMOVE = 0x200
WM_LBUTTONDOWN = 0x201
WM_LBUTTONUP = 0x202
WM_LBUTTONDBLCLK = 0x203
WM_RBUTTONDOWN = 0x204
WM_RBUTTONUP = 0x205
WM_RBUTTONDBLCLK = 0x206
WM_MBUTTONDOWN = 0x207
WM_MBUTTONUP = 0x208
WM_MBUTTONDBLCLK = 0x209
WM_MOUSELAST = 0x209
WM_PARENTNOTIFY = 0x210
WM_ENTERMENULOOP = 0x211
WM_EXITMENULOOP = 0x212
WM_MDICREATE = 0x220
WM_MDIDESTROY = 0x221
WM_MDIACTIVATE = 0x222
WM_MDIRESTORE = 0x223
WM_MDINEXT = 0x224
WM_MDIMAXIMIZE = 0x225
WM_MDITILE = 0x226
WM_MDICASCADE = 0x227
WM_MDIICONARRANGE = 0x228
WM_MDIGETACTIVE = 0x229
WM_MDISETMENU = 0x230
WM_DROPFILES = 0x233
WM_MDIREFRESHMENU = 0x234
WM_CUT = 0x300
WM_COPY = 0x301
WM_PASTE = 0x302
WM_CLEAR = 0x303
WM_UNDO = 0x304
WM_RENDERFORMAT = 0x305
WM_RENDERALLFORMATS = 0x306
WM_DESTROYCLIPBOARD = 0x307
WM_DRAWCLIPBOARD = 0x308
WM_PAINTCLIPBOARD = 0x309
WM_VSCROLLCLIPBOARD = 0x30A
WM_SIZECLIPBOARD = 0x30B
WM_ASKCBFORMATNAME = 0x30C
WM_CHANGECBCHAIN = 0x30D
WM_HSCROLLCLIPBOARD = 0x30E
WM_QUERYNEWPALETTE = 0x30F
WM_PALETTEISCHANGING = 0x310
WM_PALETTECHANGED = 0x311
WM_HOTKEY = 0x312
WM_PRINT = 0x317
WM_PRINTCLIENT = 0x318
WM_PENWINFIRST = 0x380
WM_PENWINLAST = 0x38F

# --- Structures ---------------------------------------------------------------


# typedef struct _WINDOWPLACEMENT {
#     UINT length;
#     UINT flags;
#     UINT showCmd;
#     POINT ptMinPosition;
#     POINT ptMaxPosition;
#     RECT rcNormalPosition;
# } WINDOWPLACEMENT;
class WINDOWPLACEMENT(Structure):
    _fields_ = [
        ("length", UINT),
        ("flags", UINT),
        ("showCmd", UINT),
        ("ptMinPosition", POINT),
        ("ptMaxPosition", POINT),
        ("rcNormalPosition", RECT),
    ]


PWINDOWPLACEMENT = POINTER(WINDOWPLACEMENT)
LPWINDOWPLACEMENT = PWINDOWPLACEMENT


# typedef struct tagGUITHREADINFO {
#     DWORD cbSize;
#     DWORD flags;
#     HWND hwndActive;
#     HWND hwndFocus;
#     HWND hwndCapture;
#     HWND hwndMenuOwner;
#     HWND hwndMoveSize;
#     HWND hwndCaret;
#     RECT rcCaret;
# } GUITHREADINFO, *PGUITHREADINFO;
class GUITHREADINFO(Structure):
    _fields_ = [
        ("cbSize", DWORD),
        ("flags", DWORD),
        ("hwndActive", HWND),
        ("hwndFocus", HWND),
        ("hwndCapture", HWND),
        ("hwndMenuOwner", HWND),
        ("hwndMoveSize", HWND),
        ("hwndCaret", HWND),
        ("rcCaret", RECT),
    ]


PGUITHREADINFO = POINTER(GUITHREADINFO)
LPGUITHREADINFO = PGUITHREADINFO

# --- High level classes -------------------------------------------------------

# Point() and Rect() are here instead of gdi32.py because they were mainly
# created to handle window coordinates rather than drawing on the screen.

# XXX not sure if these classes should be psyco-optimized,
# it may not work if the user wants to serialize them for some reason


class Point(object):
    """
    Python wrapper over the L{POINT} class.

    @type x: int
    @ivar x: Horizontal coordinate
    @type y: int
    @ivar y: Vertical coordinate
    """

    def __init__(self, x=0, y=0):
        """
        @see: L{POINT}
        @type  x: int
        @param x: Horizontal coordinate
        @type  y: int
        @param y: Vertical coordinate
        """
        self.x = x
        self.y = y

    def __iter__(self):
        return (self.x, self.y).__iter__()

    def __len__(self):
        return 2

    def __getitem__(self, index):
        return (self.x, self.y)[index]

    def __setitem__(self, index, value):
        if index == 0:
            self.x = value
        elif index == 1:
            self.y = value
        else:
            raise IndexError("index out of range")

    @property
    def _as_parameter_(self):
        """
        Compatibility with ctypes.
        Allows passing transparently a Point object to an API call.
        """
        return POINT(self.x, self.y)

    def screen_to_client(self, hWnd):
        """
        Translates window screen coordinates to client coordinates.

        @see: L{client_to_screen}, L{translate}

        @type  hWnd: int or L{HWND} or L{system.Window}
        @param hWnd: Window handle.

        @rtype:  L{Point}
        @return: New object containing the translated coordinates.
        """
        return ScreenToClient(hWnd, self)

    def client_to_screen(self, hWnd):
        """
        Translates window client coordinates to screen coordinates.

        @see: L{screen_to_client}, L{translate}

        @type  hWnd: int or L{HWND} or L{system.Window}
        @param hWnd: Window handle.

        @rtype:  L{Point}
        @return: New object containing the translated coordinates.
        """
        return ClientToScreen(hWnd, self)

    def translate(self, hWndFrom=HWND_DESKTOP, hWndTo=HWND_DESKTOP):
        """
        Translate coordinates from one window to another.

        @note: To translate multiple points it's more efficient to use the
            L{MapWindowPoints} function instead.

        @see: L{client_to_screen}, L{screen_to_client}

        @type  hWndFrom: int or L{HWND} or L{system.Window}
        @param hWndFrom: Window handle to translate from.
            Use C{HWND_DESKTOP} for screen coordinates.

        @type  hWndTo: int or L{HWND} or L{system.Window}
        @param hWndTo: Window handle to translate to.
            Use C{HWND_DESKTOP} for screen coordinates.

        @rtype:  L{Point}
        @return: New object containing the translated coordinates.
        """
        return MapWindowPoints(hWndFrom, hWndTo, [self])


class Rect(object):
    """
    Python wrapper over the L{RECT} class.

    @type   left: int
    @ivar   left: Horizontal coordinate for the top left corner.
    @type    top: int
    @ivar    top: Vertical coordinate for the top left corner.
    @type  right: int
    @ivar  right: Horizontal coordinate for the bottom right corner.
    @type bottom: int
    @ivar bottom: Vertical coordinate for the bottom right corner.

    @type  width: int
    @ivar  width: Width in pixels. Same as C{right - left}.
    @type height: int
    @ivar height: Height in pixels. Same as C{bottom - top}.
    """

    def __init__(self, left=0, top=0, right=0, bottom=0):
        """
        @see: L{RECT}
        @type    left: int
        @param   left: Horizontal coordinate for the top left corner.
        @type     top: int
        @param    top: Vertical coordinate for the top left corner.
        @type   right: int
        @param  right: Horizontal coordinate for the bottom right corner.
        @type  bottom: int
        @param bottom: Vertical coordinate for the bottom right corner.
        """
        self.left = left
        self.top = top
        self.right = right
        self.bottom = bottom

    def __iter__(self):
        return (self.left, self.top, self.right, self.bottom).__iter__()

    def __len__(self):
        return 2

    def __getitem__(self, index):
        return (self.left, self.top, self.right, self.bottom)[index]

    def __setitem__(self, index, value):
        if index == 0:
            self.left = value
        elif index == 1:
            self.top = value
        elif index == 2:
            self.right = value
        elif index == 3:
            self.bottom = value
        else:
            raise IndexError("index out of range")

    @property
    def _as_parameter_(self):
        """
        Compatibility with ctypes.
        Allows passing transparently a Point object to an API call.
        """
        return RECT(self.left, self.top, self.right, self.bottom)

    def __get_width(self):
        return self.right - self.left

    def __get_height(self):
        return self.bottom - self.top

    def __set_width(self, value):
        self.right = value - self.left

    def __set_height(self, value):
        self.bottom = value - self.top

    width = property(__get_width, __set_width)
    height = property(__get_height, __set_height)

    def screen_to_client(self, hWnd):
        """
        Translates window screen coordinates to client coordinates.

        @see: L{client_to_screen}, L{translate}

        @type  hWnd: int or L{HWND} or L{system.Window}
        @param hWnd: Window handle.

        @rtype:  L{Rect}
        @return: New object containing the translated coordinates.
        """
        topleft = ScreenToClient(hWnd, (self.left, self.top))
        bottomright = ScreenToClient(hWnd, (self.bottom, self.right))
        return Rect(topleft.x, topleft.y, bottomright.x, bottomright.y)

    def client_to_screen(self, hWnd):
        """
        Translates window client coordinates to screen coordinates.

        @see: L{screen_to_client}, L{translate}

        @type  hWnd: int or L{HWND} or L{system.Window}
        @param hWnd: Window handle.

        @rtype:  L{Rect}
        @return: New object containing the translated coordinates.
        """
        topleft = ClientToScreen(hWnd, (self.left, self.top))
        bottomright = ClientToScreen(hWnd, (self.bottom, self.right))
        return Rect(topleft.x, topleft.y, bottomright.x, bottomright.y)

    def translate(self, hWndFrom=HWND_DESKTOP, hWndTo=HWND_DESKTOP):
        """
        Translate coordinates from one window to another.

        @see: L{client_to_screen}, L{screen_to_client}

        @type  hWndFrom: int or L{HWND} or L{system.Window}
        @param hWndFrom: Window handle to translate from.
            Use C{HWND_DESKTOP} for screen coordinates.

        @type  hWndTo: int or L{HWND} or L{system.Window}
        @param hWndTo: Window handle to translate to.
            Use C{HWND_DESKTOP} for screen coordinates.

        @rtype:  L{Rect}
        @return: New object containing the translated coordinates.
        """
        points = [(self.left, self.top), (self.right, self.bottom)]
        return MapWindowPoints(hWndFrom, hWndTo, points)


class WindowPlacement(object):
    """
    Python wrapper over the L{WINDOWPLACEMENT} class.
    """

    def __init__(self, wp=None):
        """
        @type  wp: L{WindowPlacement} or L{WINDOWPLACEMENT}
        @param wp: Another window placement object.
        """

        # Initialize all properties with empty values.
        self.flags = 0
        self.showCmd = 0
        self.ptMinPosition = Point()
        self.ptMaxPosition = Point()
        self.rcNormalPosition = Rect()

        # If a window placement was given copy it's properties.
        if wp:
            self.flags = wp.flags
            self.showCmd = wp.showCmd
            self.ptMinPosition = Point(wp.ptMinPosition.x, wp.ptMinPosition.y)
            self.ptMaxPosition = Point(wp.ptMaxPosition.x, wp.ptMaxPosition.y)
            self.rcNormalPosition = Rect(
                wp.rcNormalPosition.left,
                wp.rcNormalPosition.top,
                wp.rcNormalPosition.right,
                wp.rcNormalPosition.bottom,
            )

    @property
    def _as_parameter_(self):
        """
        Compatibility with ctypes.
        Allows passing transparently a Point object to an API call.
        """
        wp = WINDOWPLACEMENT()
        wp.length = sizeof(wp)
        wp.flags = self.flags
        wp.showCmd = self.showCmd
        wp.ptMinPosition.x = self.ptMinPosition.x
        wp.ptMinPosition.y = self.ptMinPosition.y
        wp.ptMaxPosition.x = self.ptMaxPosition.x
        wp.ptMaxPosition.y = self.ptMaxPosition.y
        wp.rcNormalPosition.left = self.rcNormalPosition.left
        wp.rcNormalPosition.top = self.rcNormalPosition.top
        wp.rcNormalPosition.right = self.rcNormalPosition.right
        wp.rcNormalPosition.bottom = self.rcNormalPosition.bottom
        return wp


# --- user32.dll ---------------------------------------------------------------


# void WINAPI SetLastErrorEx(
#   __in  DWORD dwErrCode,
#   __in  DWORD dwType
# );
def SetLastErrorEx(dwErrCode, dwType=0):
    _SetLastErrorEx = windll.user32.SetLastErrorEx
    _SetLastErrorEx.argtypes = [DWORD, DWORD]
    _SetLastErrorEx.restype = None
    _SetLastErrorEx(dwErrCode, dwType)


# HWND FindWindow(
#     LPCTSTR lpClassName,
#     LPCTSTR lpWindowName
# );
def FindWindowA(lpClassName=None, lpWindowName=None):
    _FindWindowA = windll.user32.FindWindowA
    _FindWindowA.argtypes = [LPSTR, LPSTR]
    _FindWindowA.restype = HWND

    hWnd = _FindWindowA(lpClassName, lpWindowName)
    if not hWnd:
        errcode = GetLastError()
        if errcode != ERROR_SUCCESS:
            raise ctypes.WinError(errcode)
    return hWnd


def FindWindowW(lpClassName=None, lpWindowName=None):
    _FindWindowW = windll.user32.FindWindowW
    _FindWindowW.argtypes = [LPWSTR, LPWSTR]
    _FindWindowW.restype = HWND

    hWnd = _FindWindowW(lpClassName, lpWindowName)
    if not hWnd:
        errcode = GetLastError()
        if errcode != ERROR_SUCCESS:
            raise ctypes.WinError(errcode)
    return hWnd


FindWindow = GuessStringType(FindWindowA, FindWindowW)


# HWND WINAPI FindWindowEx(
#   __in_opt  HWND hwndParent,
#   __in_opt  HWND hwndChildAfter,
#   __in_opt  LPCTSTR lpszClass,
#   __in_opt  LPCTSTR lpszWindow
# );
def FindWindowExA(hwndParent=None, hwndChildAfter=None, lpClassName=None, lpWindowName=None):
    _FindWindowExA = windll.user32.FindWindowExA
    _FindWindowExA.argtypes = [HWND, HWND, LPSTR, LPSTR]
    _FindWindowExA.restype = HWND

    hWnd = _FindWindowExA(hwndParent, hwndChildAfter, lpClassName, lpWindowName)
    if not hWnd:
        errcode = GetLastError()
        if errcode != ERROR_SUCCESS:
            raise ctypes.WinError(errcode)
    return hWnd


def FindWindowExW(hwndParent=None, hwndChildAfter=None, lpClassName=None, lpWindowName=None):
    _FindWindowExW = windll.user32.FindWindowExW
    _FindWindowExW.argtypes = [HWND, HWND, LPWSTR, LPWSTR]
    _FindWindowExW.restype = HWND

    hWnd = _FindWindowExW(hwndParent, hwndChildAfter, lpClassName, lpWindowName)
    if not hWnd:
        errcode = GetLastError()
        if errcode != ERROR_SUCCESS:
            raise ctypes.WinError(errcode)
    return hWnd


FindWindowEx = GuessStringType(FindWindowExA, FindWindowExW)


# int GetClassName(
#     HWND hWnd,
#     LPTSTR lpClassName,
#     int nMaxCount
# );
def GetClassNameA(hWnd):
    _GetClassNameA = windll.user32.GetClassNameA
    _GetClassNameA.argtypes = [HWND, LPSTR, ctypes.c_int]
    _GetClassNameA.restype = ctypes.c_int

    nMaxCount = 0x1000
    dwCharSize = sizeof(CHAR)
    while 1:
        lpClassName = ctypes.create_string_buffer("", nMaxCount)
        nCount = _GetClassNameA(hWnd, lpClassName, nMaxCount)
        if nCount == 0:
            raise ctypes.WinError()
        if nCount < nMaxCount - dwCharSize:
            break
        nMaxCount += 0x1000
    return lpClassName.value


def GetClassNameW(hWnd):
    _GetClassNameW = windll.user32.GetClassNameW
    _GetClassNameW.argtypes = [HWND, LPWSTR, ctypes.c_int]
    _GetClassNameW.restype = ctypes.c_int

    nMaxCount = 0x1000
    dwCharSize = sizeof(WCHAR)
    while 1:
        lpClassName = ctypes.create_unicode_buffer("", nMaxCount)
        nCount = _GetClassNameW(hWnd, lpClassName, nMaxCount)
        if nCount == 0:
            raise ctypes.WinError()
        if nCount < nMaxCount - dwCharSize:
            break
        nMaxCount += 0x1000
    return lpClassName.value


GetClassName = GuessStringType(GetClassNameA, GetClassNameW)


# int WINAPI GetWindowText(
#   __in   HWND hWnd,
#   __out  LPTSTR lpString,
#   __in   int nMaxCount
# );
def GetWindowTextA(hWnd):
    _GetWindowTextA = windll.user32.GetWindowTextA
    _GetWindowTextA.argtypes = [HWND, LPSTR, ctypes.c_int]
    _GetWindowTextA.restype = ctypes.c_int

    nMaxCount = 0x1000
    dwCharSize = sizeof(CHAR)
    while 1:
        lpString = ctypes.create_string_buffer("", nMaxCount)
        nCount = _GetWindowTextA(hWnd, lpString, nMaxCount)
        if nCount == 0:
            raise ctypes.WinError()
        if nCount < nMaxCount - dwCharSize:
            break
        nMaxCount += 0x1000
    return lpString.value


def GetWindowTextW(hWnd):
    _GetWindowTextW = windll.user32.GetWindowTextW
    _GetWindowTextW.argtypes = [HWND, LPWSTR, ctypes.c_int]
    _GetWindowTextW.restype = ctypes.c_int

    nMaxCount = 0x1000
    dwCharSize = sizeof(CHAR)
    while 1:
        lpString = ctypes.create_string_buffer("", nMaxCount)
        nCount = _GetWindowTextW(hWnd, lpString, nMaxCount)
        if nCount == 0:
            raise ctypes.WinError()
        if nCount < nMaxCount - dwCharSize:
            break
        nMaxCount += 0x1000
    return lpString.value


GetWindowText = GuessStringType(GetWindowTextA, GetWindowTextW)


# BOOL WINAPI SetWindowText(
#   __in      HWND hWnd,
#   __in_opt  LPCTSTR lpString
# );
def SetWindowTextA(hWnd, lpString=None):
    _SetWindowTextA = windll.user32.SetWindowTextA
    _SetWindowTextA.argtypes = [HWND, LPSTR]
    _SetWindowTextA.restype = bool
    _SetWindowTextA.errcheck = RaiseIfZero
    _SetWindowTextA(hWnd, lpString)


def SetWindowTextW(hWnd, lpString=None):
    _SetWindowTextW = windll.user32.SetWindowTextW
    _SetWindowTextW.argtypes = [HWND, LPWSTR]
    _SetWindowTextW.restype = bool
    _SetWindowTextW.errcheck = RaiseIfZero
    _SetWindowTextW(hWnd, lpString)


SetWindowText = GuessStringType(SetWindowTextA, SetWindowTextW)


# LONG GetWindowLong(
#     HWND hWnd,
#     int nIndex
# );
def GetWindowLongA(hWnd, nIndex=0):
    _GetWindowLongA = windll.user32.GetWindowLongA
    _GetWindowLongA.argtypes = [HWND, ctypes.c_int]
    _GetWindowLongA.restype = DWORD

    SetLastError(ERROR_SUCCESS)
    retval = _GetWindowLongA(hWnd, nIndex)
    if retval == 0:
        errcode = GetLastError()
        if errcode != ERROR_SUCCESS:
            raise ctypes.WinError(errcode)
    return retval


def GetWindowLongW(hWnd, nIndex=0):
    _GetWindowLongW = windll.user32.GetWindowLongW
    _GetWindowLongW.argtypes = [HWND, ctypes.c_int]
    _GetWindowLongW.restype = DWORD

    SetLastError(ERROR_SUCCESS)
    retval = _GetWindowLongW(hWnd, nIndex)
    if retval == 0:
        errcode = GetLastError()
        if errcode != ERROR_SUCCESS:
            raise ctypes.WinError(errcode)
    return retval


GetWindowLong = DefaultStringType(GetWindowLongA, GetWindowLongW)

# LONG_PTR WINAPI GetWindowLongPtr(
#   _In_  HWND hWnd,
#   _In_  int nIndex
# );

if bits == 32:
    GetWindowLongPtrA = GetWindowLongA
    GetWindowLongPtrW = GetWindowLongW
    GetWindowLongPtr = GetWindowLong

else:

    def GetWindowLongPtrA(hWnd, nIndex=0):
        _GetWindowLongPtrA = windll.user32.GetWindowLongPtrA
        _GetWindowLongPtrA.argtypes = [HWND, ctypes.c_int]
        _GetWindowLongPtrA.restype = SIZE_T

        SetLastError(ERROR_SUCCESS)
        retval = _GetWindowLongPtrA(hWnd, nIndex)
        if retval == 0:
            errcode = GetLastError()
            if errcode != ERROR_SUCCESS:
                raise ctypes.WinError(errcode)
        return retval

    def GetWindowLongPtrW(hWnd, nIndex=0):
        _GetWindowLongPtrW = windll.user32.GetWindowLongPtrW
        _GetWindowLongPtrW.argtypes = [HWND, ctypes.c_int]
        _GetWindowLongPtrW.restype = DWORD

        SetLastError(ERROR_SUCCESS)
        retval = _GetWindowLongPtrW(hWnd, nIndex)
        if retval == 0:
            errcode = GetLastError()
            if errcode != ERROR_SUCCESS:
                raise ctypes.WinError(errcode)
        return retval

    GetWindowLongPtr = DefaultStringType(GetWindowLongPtrA, GetWindowLongPtrW)

# LONG WINAPI SetWindowLong(
#   _In_  HWND hWnd,
#   _In_  int nIndex,
#   _In_  LONG dwNewLong
# );


def SetWindowLongA(hWnd, nIndex, dwNewLong):
    _SetWindowLongA = windll.user32.SetWindowLongA
    _SetWindowLongA.argtypes = [HWND, ctypes.c_int, DWORD]
    _SetWindowLongA.restype = DWORD

    SetLastError(ERROR_SUCCESS)
    retval = _SetWindowLongA(hWnd, nIndex, dwNewLong)
    if retval == 0:
        errcode = GetLastError()
        if errcode != ERROR_SUCCESS:
            raise ctypes.WinError(errcode)
    return retval


def SetWindowLongW(hWnd, nIndex, dwNewLong):
    _SetWindowLongW = windll.user32.SetWindowLongW
    _SetWindowLongW.argtypes = [HWND, ctypes.c_int, DWORD]
    _SetWindowLongW.restype = DWORD

    SetLastError(ERROR_SUCCESS)
    retval = _SetWindowLongW(hWnd, nIndex, dwNewLong)
    if retval == 0:
        errcode = GetLastError()
        if errcode != ERROR_SUCCESS:
            raise ctypes.WinError(errcode)
    return retval


SetWindowLong = DefaultStringType(SetWindowLongA, SetWindowLongW)

# LONG_PTR WINAPI SetWindowLongPtr(
#   _In_  HWND hWnd,
#   _In_  int nIndex,
#   _In_  LONG_PTR dwNewLong
# );

if bits == 32:
    SetWindowLongPtrA = SetWindowLongA
    SetWindowLongPtrW = SetWindowLongW
    SetWindowLongPtr = SetWindowLong

else:

    def SetWindowLongPtrA(hWnd, nIndex, dwNewLong):
        _SetWindowLongPtrA = windll.user32.SetWindowLongPtrA
        _SetWindowLongPtrA.argtypes = [HWND, ctypes.c_int, SIZE_T]
        _SetWindowLongPtrA.restype = SIZE_T

        SetLastError(ERROR_SUCCESS)
        retval = _SetWindowLongPtrA(hWnd, nIndex, dwNewLong)
        if retval == 0:
            errcode = GetLastError()
            if errcode != ERROR_SUCCESS:
                raise ctypes.WinError(errcode)
        return retval

    def SetWindowLongPtrW(hWnd, nIndex, dwNewLong):
        _SetWindowLongPtrW = windll.user32.SetWindowLongPtrW
        _SetWindowLongPtrW.argtypes = [HWND, ctypes.c_int, SIZE_T]
        _SetWindowLongPtrW.restype = SIZE_T

        SetLastError(ERROR_SUCCESS)
        retval = _SetWindowLongPtrW(hWnd, nIndex, dwNewLong)
        if retval == 0:
            errcode = GetLastError()
            if errcode != ERROR_SUCCESS:
                raise ctypes.WinError(errcode)
        return retval

    SetWindowLongPtr = DefaultStringType(SetWindowLongPtrA, SetWindowLongPtrW)


# HWND GetShellWindow(VOID);
def GetShellWindow():
    _GetShellWindow = windll.user32.GetShellWindow
    _GetShellWindow.argtypes = []
    _GetShellWindow.restype = HWND
    _GetShellWindow.errcheck = RaiseIfZero
    return _GetShellWindow()


# DWORD GetWindowThreadProcessId(
#     HWND hWnd,
#     LPDWORD lpdwProcessId
# );
def GetWindowThreadProcessId(hWnd):
    _GetWindowThreadProcessId = windll.user32.GetWindowThreadProcessId
    _GetWindowThreadProcessId.argtypes = [HWND, LPDWORD]
    _GetWindowThreadProcessId.restype = DWORD
    _GetWindowThreadProcessId.errcheck = RaiseIfZero

    dwProcessId = DWORD(0)
    dwThreadId = _GetWindowThreadProcessId(hWnd, byref(dwProcessId))
    return (dwThreadId, dwProcessId.value)


# HWND WINAPI GetWindow(
#   __in  HWND hwnd,
#   __in  UINT uCmd
# );
def GetWindow(hWnd, uCmd):
    _GetWindow = windll.user32.GetWindow
    _GetWindow.argtypes = [HWND, UINT]
    _GetWindow.restype = HWND

    SetLastError(ERROR_SUCCESS)
    hWndTarget = _GetWindow(hWnd, uCmd)
    if not hWndTarget:
        winerr = GetLastError()
        if winerr != ERROR_SUCCESS:
            raise ctypes.WinError(winerr)
    return hWndTarget


# HWND GetParent(
#       HWND hWnd
# );
def GetParent(hWnd):
    _GetParent = windll.user32.GetParent
    _GetParent.argtypes = [HWND]
    _GetParent.restype = HWND

    SetLastError(ERROR_SUCCESS)
    hWndParent = _GetParent(hWnd)
    if not hWndParent:
        winerr = GetLastError()
        if winerr != ERROR_SUCCESS:
            raise ctypes.WinError(winerr)
    return hWndParent


# HWND WINAPI GetAncestor(
#   __in  HWND hwnd,
#   __in  UINT gaFlags
# );
def GetAncestor(hWnd, gaFlags=GA_PARENT):
    _GetAncestor = windll.user32.GetAncestor
    _GetAncestor.argtypes = [HWND, UINT]
    _GetAncestor.restype = HWND

    SetLastError(ERROR_SUCCESS)
    hWndParent = _GetAncestor(hWnd, gaFlags)
    if not hWndParent:
        winerr = GetLastError()
        if winerr != ERROR_SUCCESS:
            raise ctypes.WinError(winerr)
    return hWndParent


# BOOL EnableWindow(
#     HWND hWnd,
#     BOOL bEnable
# );
def EnableWindow(hWnd, bEnable=True):
    _EnableWindow = windll.user32.EnableWindow
    _EnableWindow.argtypes = [HWND, BOOL]
    _EnableWindow.restype = bool
    return _EnableWindow(hWnd, bool(bEnable))


# BOOL ShowWindow(
#     HWND hWnd,
#     int nCmdShow
# );
def ShowWindow(hWnd, nCmdShow=SW_SHOW):
    _ShowWindow = windll.user32.ShowWindow
    _ShowWindow.argtypes = [HWND, ctypes.c_int]
    _ShowWindow.restype = bool
    return _ShowWindow(hWnd, nCmdShow)


# BOOL ShowWindowAsync(
#     HWND hWnd,
#     int nCmdShow
# );
def ShowWindowAsync(hWnd, nCmdShow=SW_SHOW):
    _ShowWindowAsync = windll.user32.ShowWindowAsync
    _ShowWindowAsync.argtypes = [HWND, ctypes.c_int]
    _ShowWindowAsync.restype = bool
    return _ShowWindowAsync(hWnd, nCmdShow)


# HWND GetDesktopWindow(VOID);
def GetDesktopWindow():
    _GetDesktopWindow = windll.user32.GetDesktopWindow
    _GetDesktopWindow.argtypes = []
    _GetDesktopWindow.restype = HWND
    _GetDesktopWindow.errcheck = RaiseIfZero
    return _GetDesktopWindow()


# HWND GetForegroundWindow(VOID);
def GetForegroundWindow():
    _GetForegroundWindow = windll.user32.GetForegroundWindow
    _GetForegroundWindow.argtypes = []
    _GetForegroundWindow.restype = HWND
    _GetForegroundWindow.errcheck = RaiseIfZero
    return _GetForegroundWindow()


# BOOL IsWindow(
#     HWND hWnd
# );
def IsWindow(hWnd):
    _IsWindow = windll.user32.IsWindow
    _IsWindow.argtypes = [HWND]
    _IsWindow.restype = bool
    return _IsWindow(hWnd)


# BOOL IsWindowVisible(
#     HWND hWnd
# );
def IsWindowVisible(hWnd):
    _IsWindowVisible = windll.user32.IsWindowVisible
    _IsWindowVisible.argtypes = [HWND]
    _IsWindowVisible.restype = bool
    return _IsWindowVisible(hWnd)


# BOOL IsWindowEnabled(
#     HWND hWnd
# );
def IsWindowEnabled(hWnd):
    _IsWindowEnabled = windll.user32.IsWindowEnabled
    _IsWindowEnabled.argtypes = [HWND]
    _IsWindowEnabled.restype = bool
    return _IsWindowEnabled(hWnd)


# BOOL IsZoomed(
#     HWND hWnd
# );
def IsZoomed(hWnd):
    _IsZoomed = windll.user32.IsZoomed
    _IsZoomed.argtypes = [HWND]
    _IsZoomed.restype = bool
    return _IsZoomed(hWnd)


# BOOL IsIconic(
#     HWND hWnd
# );
def IsIconic(hWnd):
    _IsIconic = windll.user32.IsIconic
    _IsIconic.argtypes = [HWND]
    _IsIconic.restype = bool
    return _IsIconic(hWnd)


# BOOL IsChild(
#     HWND hWnd
# );
def IsChild(hWnd):
    _IsChild = windll.user32.IsChild
    _IsChild.argtypes = [HWND]
    _IsChild.restype = bool
    return _IsChild(hWnd)


# HWND WindowFromPoint(
#     POINT Point
# );
def WindowFromPoint(point):
    _WindowFromPoint = windll.user32.WindowFromPoint
    _WindowFromPoint.argtypes = [POINT]
    _WindowFromPoint.restype = HWND
    _WindowFromPoint.errcheck = RaiseIfZero
    if isinstance(point, tuple):
        point = POINT(*point)
    return _WindowFromPoint(point)


# HWND ChildWindowFromPoint(
#     HWND hWndParent,
#     POINT Point
# );
def ChildWindowFromPoint(hWndParent, point):
    _ChildWindowFromPoint = windll.user32.ChildWindowFromPoint
    _ChildWindowFromPoint.argtypes = [HWND, POINT]
    _ChildWindowFromPoint.restype = HWND
    _ChildWindowFromPoint.errcheck = RaiseIfZero
    if isinstance(point, tuple):
        point = POINT(*point)
    return _ChildWindowFromPoint(hWndParent, point)


# HWND RealChildWindowFromPoint(
#    HWND hwndParent,
#    POINT ptParentClientCoords
# );
def RealChildWindowFromPoint(hWndParent, ptParentClientCoords):
    _RealChildWindowFromPoint = windll.user32.RealChildWindowFromPoint
    _RealChildWindowFromPoint.argtypes = [HWND, POINT]
    _RealChildWindowFromPoint.restype = HWND
    _RealChildWindowFromPoint.errcheck = RaiseIfZero
    if isinstance(ptParentClientCoords, tuple):
        ptParentClientCoords = POINT(*ptParentClientCoords)
    return _RealChildWindowFromPoint(hWndParent, ptParentClientCoords)


# BOOL ScreenToClient(
#   __in  HWND hWnd,
#         LPPOINT lpPoint
# );
def ScreenToClient(hWnd, lpPoint):
    _ScreenToClient = windll.user32.ScreenToClient
    _ScreenToClient.argtypes = [HWND, LPPOINT]
    _ScreenToClient.restype = bool
    _ScreenToClient.errcheck = RaiseIfZero

    if isinstance(lpPoint, tuple):
        lpPoint = POINT(*lpPoint)
    else:
        lpPoint = POINT(lpPoint.x, lpPoint.y)
    _ScreenToClient(hWnd, byref(lpPoint))
    return Point(lpPoint.x, lpPoint.y)


# BOOL ClientToScreen(
#   HWND hWnd,
#   LPPOINT lpPoint
# );
def ClientToScreen(hWnd, lpPoint):
    _ClientToScreen = windll.user32.ClientToScreen
    _ClientToScreen.argtypes = [HWND, LPPOINT]
    _ClientToScreen.restype = bool
    _ClientToScreen.errcheck = RaiseIfZero

    if isinstance(lpPoint, tuple):
        lpPoint = POINT(*lpPoint)
    else:
        lpPoint = POINT(lpPoint.x, lpPoint.y)
    _ClientToScreen(hWnd, byref(lpPoint))
    return Point(lpPoint.x, lpPoint.y)


# int MapWindowPoints(
#   __in     HWND hWndFrom,
#   __in     HWND hWndTo,
#   __inout  LPPOINT lpPoints,
#   __in     UINT cPoints
# );
def MapWindowPoints(hWndFrom, hWndTo, lpPoints):
    _MapWindowPoints = windll.user32.MapWindowPoints
    _MapWindowPoints.argtypes = [HWND, HWND, LPPOINT, UINT]
    _MapWindowPoints.restype = ctypes.c_int

    cPoints = len(lpPoints)
    lpPoints = (POINT * cPoints)(*lpPoints)
    SetLastError(ERROR_SUCCESS)
    number = _MapWindowPoints(hWndFrom, hWndTo, byref(lpPoints), cPoints)
    if number == 0:
        errcode = GetLastError()
        if errcode != ERROR_SUCCESS:
            raise ctypes.WinError(errcode)
    x_delta = number & 0xFFFF
    y_delta = (number >> 16) & 0xFFFF
    return x_delta, y_delta, [(Point.x, Point.y) for Point in lpPoints]


# BOOL SetForegroundWindow(
#    HWND hWnd
# );
def SetForegroundWindow(hWnd):
    _SetForegroundWindow = windll.user32.SetForegroundWindow
    _SetForegroundWindow.argtypes = [HWND]
    _SetForegroundWindow.restype = bool
    _SetForegroundWindow.errcheck = RaiseIfZero
    return _SetForegroundWindow(hWnd)


# BOOL GetWindowPlacement(
#     HWND hWnd,
#     WINDOWPLACEMENT *lpwndpl
# );
def GetWindowPlacement(hWnd):
    _GetWindowPlacement = windll.user32.GetWindowPlacement
    _GetWindowPlacement.argtypes = [HWND, PWINDOWPLACEMENT]
    _GetWindowPlacement.restype = bool
    _GetWindowPlacement.errcheck = RaiseIfZero

    lpwndpl = WINDOWPLACEMENT()
    lpwndpl.length = sizeof(lpwndpl)
    _GetWindowPlacement(hWnd, byref(lpwndpl))
    return WindowPlacement(lpwndpl)


# BOOL SetWindowPlacement(
#     HWND hWnd,
#     WINDOWPLACEMENT *lpwndpl
# );
def SetWindowPlacement(hWnd, lpwndpl):
    _SetWindowPlacement = windll.user32.SetWindowPlacement
    _SetWindowPlacement.argtypes = [HWND, PWINDOWPLACEMENT]
    _SetWindowPlacement.restype = bool
    _SetWindowPlacement.errcheck = RaiseIfZero

    if isinstance(lpwndpl, WINDOWPLACEMENT):
        lpwndpl.length = sizeof(lpwndpl)
    _SetWindowPlacement(hWnd, byref(lpwndpl))


# BOOL WINAPI GetWindowRect(
#   __in   HWND hWnd,
#   __out  LPRECT lpRect
# );
def GetWindowRect(hWnd):
    _GetWindowRect = windll.user32.GetWindowRect
    _GetWindowRect.argtypes = [HWND, LPRECT]
    _GetWindowRect.restype = bool
    _GetWindowRect.errcheck = RaiseIfZero

    lpRect = RECT()
    _GetWindowRect(hWnd, byref(lpRect))
    return Rect(lpRect.left, lpRect.top, lpRect.right, lpRect.bottom)


# BOOL WINAPI GetClientRect(
#   __in   HWND hWnd,
#   __out  LPRECT lpRect
# );
def GetClientRect(hWnd):
    _GetClientRect = windll.user32.GetClientRect
    _GetClientRect.argtypes = [HWND, LPRECT]
    _GetClientRect.restype = bool
    _GetClientRect.errcheck = RaiseIfZero

    lpRect = RECT()
    _GetClientRect(hWnd, byref(lpRect))
    return Rect(lpRect.left, lpRect.top, lpRect.right, lpRect.bottom)


# BOOL MoveWindow(
#    HWND hWnd,
#    int X,
#    int Y,
#    int nWidth,
#    int nHeight,
#    BOOL bRepaint
# );
def MoveWindow(hWnd, X, Y, nWidth, nHeight, bRepaint=True):
    _MoveWindow = windll.user32.MoveWindow
    _MoveWindow.argtypes = [HWND, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int, BOOL]
    _MoveWindow.restype = bool
    _MoveWindow.errcheck = RaiseIfZero
    _MoveWindow(hWnd, X, Y, nWidth, nHeight, bool(bRepaint))


# BOOL GetGUIThreadInfo(
#     DWORD idThread,
#     LPGUITHREADINFO lpgui
# );
def GetGUIThreadInfo(idThread):
    _GetGUIThreadInfo = windll.user32.GetGUIThreadInfo
    _GetGUIThreadInfo.argtypes = [DWORD, LPGUITHREADINFO]
    _GetGUIThreadInfo.restype = bool
    _GetGUIThreadInfo.errcheck = RaiseIfZero

    gui = GUITHREADINFO()
    _GetGUIThreadInfo(idThread, byref(gui))
    return gui


# BOOL CALLBACK EnumWndProc(
#     HWND hwnd,
#     LPARAM lParam
# );
class __EnumWndProc(__WindowEnumerator):
    pass


# BOOL EnumWindows(
#     WNDENUMPROC lpEnumFunc,
#     LPARAM lParam
# );
def EnumWindows():
    _EnumWindows = windll.user32.EnumWindows
    _EnumWindows.argtypes = [WNDENUMPROC, LPARAM]
    _EnumWindows.restype = bool

    EnumFunc = __EnumWndProc()
    lpEnumFunc = WNDENUMPROC(EnumFunc)
    if not _EnumWindows(lpEnumFunc, NULL):
        errcode = GetLastError()
        if errcode not in (ERROR_NO_MORE_FILES, ERROR_SUCCESS):
            raise ctypes.WinError(errcode)
    return EnumFunc.hwnd


# BOOL CALLBACK EnumThreadWndProc(
#     HWND hwnd,
#     LPARAM lParam
# );
class __EnumThreadWndProc(__WindowEnumerator):
    pass


# BOOL EnumThreadWindows(
#     DWORD dwThreadId,
#     WNDENUMPROC lpfn,
#     LPARAM lParam
# );
def EnumThreadWindows(dwThreadId):
    _EnumThreadWindows = windll.user32.EnumThreadWindows
    _EnumThreadWindows.argtypes = [DWORD, WNDENUMPROC, LPARAM]
    _EnumThreadWindows.restype = bool

    fn = __EnumThreadWndProc()
    lpfn = WNDENUMPROC(fn)
    if not _EnumThreadWindows(dwThreadId, lpfn, NULL):
        errcode = GetLastError()
        if errcode not in (ERROR_NO_MORE_FILES, ERROR_SUCCESS):
            raise ctypes.WinError(errcode)
    return fn.hwnd


# BOOL CALLBACK EnumChildProc(
#     HWND hwnd,
#     LPARAM lParam
# );
class __EnumChildProc(__WindowEnumerator):
    pass


# BOOL EnumChildWindows(
#     HWND hWndParent,
#     WNDENUMPROC lpEnumFunc,
#     LPARAM lParam
# );
def EnumChildWindows(hWndParent=NULL):
    _EnumChildWindows = windll.user32.EnumChildWindows
    _EnumChildWindows.argtypes = [HWND, WNDENUMPROC, LPARAM]
    _EnumChildWindows.restype = bool

    EnumFunc = __EnumChildProc()
    lpEnumFunc = WNDENUMPROC(EnumFunc)
    SetLastError(ERROR_SUCCESS)
    _EnumChildWindows(hWndParent, lpEnumFunc, NULL)
    errcode = GetLastError()
    if errcode != ERROR_SUCCESS and errcode not in (ERROR_NO_MORE_FILES, ERROR_SUCCESS):
        raise ctypes.WinError(errcode)
    return EnumFunc.hwnd


# LRESULT SendMessage(
#     HWND hWnd,
#     UINT Msg,
#     WPARAM wParam,
#     LPARAM lParam
# );
def SendMessageA(hWnd, Msg, wParam=0, lParam=0):
    _SendMessageA = windll.user32.SendMessageA
    _SendMessageA.argtypes = [HWND, UINT, WPARAM, LPARAM]
    _SendMessageA.restype = LRESULT

    wParam = MAKE_WPARAM(wParam)
    lParam = MAKE_LPARAM(lParam)
    return _SendMessageA(hWnd, Msg, wParam, lParam)


def SendMessageW(hWnd, Msg, wParam=0, lParam=0):
    _SendMessageW = windll.user32.SendMessageW
    _SendMessageW.argtypes = [HWND, UINT, WPARAM, LPARAM]
    _SendMessageW.restype = LRESULT

    wParam = MAKE_WPARAM(wParam)
    lParam = MAKE_LPARAM(lParam)
    return _SendMessageW(hWnd, Msg, wParam, lParam)


SendMessage = GuessStringType(SendMessageA, SendMessageW)


# BOOL PostMessage(
#     HWND hWnd,
#     UINT Msg,
#     WPARAM wParam,
#     LPARAM lParam
# );
def PostMessageA(hWnd, Msg, wParam=0, lParam=0):
    _PostMessageA = windll.user32.PostMessageA
    _PostMessageA.argtypes = [HWND, UINT, WPARAM, LPARAM]
    _PostMessageA.restype = bool
    _PostMessageA.errcheck = RaiseIfZero

    wParam = MAKE_WPARAM(wParam)
    lParam = MAKE_LPARAM(lParam)
    _PostMessageA(hWnd, Msg, wParam, lParam)


def PostMessageW(hWnd, Msg, wParam=0, lParam=0):
    _PostMessageW = windll.user32.PostMessageW
    _PostMessageW.argtypes = [HWND, UINT, WPARAM, LPARAM]
    _PostMessageW.restype = bool
    _PostMessageW.errcheck = RaiseIfZero

    wParam = MAKE_WPARAM(wParam)
    lParam = MAKE_LPARAM(lParam)
    _PostMessageW(hWnd, Msg, wParam, lParam)


PostMessage = GuessStringType(PostMessageA, PostMessageW)


# BOOL PostThreadMessage(
#     DWORD idThread,
#     UINT Msg,
#     WPARAM wParam,
#     LPARAM lParam
# );
def PostThreadMessageA(idThread, Msg, wParam=0, lParam=0):
    _PostThreadMessageA = windll.user32.PostThreadMessageA
    _PostThreadMessageA.argtypes = [DWORD, UINT, WPARAM, LPARAM]
    _PostThreadMessageA.restype = bool
    _PostThreadMessageA.errcheck = RaiseIfZero

    wParam = MAKE_WPARAM(wParam)
    lParam = MAKE_LPARAM(lParam)
    _PostThreadMessageA(idThread, Msg, wParam, lParam)


def PostThreadMessageW(idThread, Msg, wParam=0, lParam=0):
    _PostThreadMessageW = windll.user32.PostThreadMessageW
    _PostThreadMessageW.argtypes = [DWORD, UINT, WPARAM, LPARAM]
    _PostThreadMessageW.restype = bool
    _PostThreadMessageW.errcheck = RaiseIfZero

    wParam = MAKE_WPARAM(wParam)
    lParam = MAKE_LPARAM(lParam)
    _PostThreadMessageW(idThread, Msg, wParam, lParam)


PostThreadMessage = GuessStringType(PostThreadMessageA, PostThreadMessageW)


# LRESULT c(
#     HWND hWnd,
#     UINT Msg,
#     WPARAM wParam,
#     LPARAM lParam,
#     UINT fuFlags,
#     UINT uTimeout,
#     PDWORD_PTR lpdwResult
# );
def SendMessageTimeoutA(hWnd, Msg, wParam=0, lParam=0, fuFlags=0, uTimeout=0):
    _SendMessageTimeoutA = windll.user32.SendMessageTimeoutA
    _SendMessageTimeoutA.argtypes = [HWND, UINT, WPARAM, LPARAM, UINT, UINT, PDWORD_PTR]
    _SendMessageTimeoutA.restype = LRESULT
    _SendMessageTimeoutA.errcheck = RaiseIfZero

    wParam = MAKE_WPARAM(wParam)
    lParam = MAKE_LPARAM(lParam)
    dwResult = DWORD(0)
    _SendMessageTimeoutA(hWnd, Msg, wParam, lParam, fuFlags, uTimeout, byref(dwResult))
    return dwResult.value


def SendMessageTimeoutW(hWnd, Msg, wParam=0, lParam=0):
    _SendMessageTimeoutW = windll.user32.SendMessageTimeoutW
    _SendMessageTimeoutW.argtypes = [HWND, UINT, WPARAM, LPARAM, UINT, UINT, PDWORD_PTR]
    _SendMessageTimeoutW.restype = LRESULT
    _SendMessageTimeoutW.errcheck = RaiseIfZero

    wParam = MAKE_WPARAM(wParam)
    lParam = MAKE_LPARAM(lParam)
    dwResult = DWORD(0)
    _SendMessageTimeoutW(hWnd, Msg, wParam, lParam, fuFlags, uTimeout, byref(dwResult))
    return dwResult.value


SendMessageTimeout = GuessStringType(SendMessageTimeoutA, SendMessageTimeoutW)


# BOOL SendNotifyMessage(
#     HWND hWnd,
#     UINT Msg,
#     WPARAM wParam,
#     LPARAM lParam
# );
def SendNotifyMessageA(hWnd, Msg, wParam=0, lParam=0):
    _SendNotifyMessageA = windll.user32.SendNotifyMessageA
    _SendNotifyMessageA.argtypes = [HWND, UINT, WPARAM, LPARAM]
    _SendNotifyMessageA.restype = bool
    _SendNotifyMessageA.errcheck = RaiseIfZero

    wParam = MAKE_WPARAM(wParam)
    lParam = MAKE_LPARAM(lParam)
    _SendNotifyMessageA(hWnd, Msg, wParam, lParam)


def SendNotifyMessageW(hWnd, Msg, wParam=0, lParam=0):
    _SendNotifyMessageW = windll.user32.SendNotifyMessageW
    _SendNotifyMessageW.argtypes = [HWND, UINT, WPARAM, LPARAM]
    _SendNotifyMessageW.restype = bool
    _SendNotifyMessageW.errcheck = RaiseIfZero

    wParam = MAKE_WPARAM(wParam)
    lParam = MAKE_LPARAM(lParam)
    _SendNotifyMessageW(hWnd, Msg, wParam, lParam)


SendNotifyMessage = GuessStringType(SendNotifyMessageA, SendNotifyMessageW)


# LRESULT SendDlgItemMessage(
#     HWND hDlg,
#     int nIDDlgItem,
#     UINT Msg,
#     WPARAM wParam,
#     LPARAM lParam
# );
def SendDlgItemMessageA(hDlg, nIDDlgItem, Msg, wParam=0, lParam=0):
    _SendDlgItemMessageA = windll.user32.SendDlgItemMessageA
    _SendDlgItemMessageA.argtypes = [HWND, ctypes.c_int, UINT, WPARAM, LPARAM]
    _SendDlgItemMessageA.restype = LRESULT

    wParam = MAKE_WPARAM(wParam)
    lParam = MAKE_LPARAM(lParam)
    return _SendDlgItemMessageA(hDlg, nIDDlgItem, Msg, wParam, lParam)


def SendDlgItemMessageW(hDlg, nIDDlgItem, Msg, wParam=0, lParam=0):
    _SendDlgItemMessageW = windll.user32.SendDlgItemMessageW
    _SendDlgItemMessageW.argtypes = [HWND, ctypes.c_int, UINT, WPARAM, LPARAM]
    _SendDlgItemMessageW.restype = LRESULT

    wParam = MAKE_WPARAM(wParam)
    lParam = MAKE_LPARAM(lParam)
    return _SendDlgItemMessageW(hDlg, nIDDlgItem, Msg, wParam, lParam)


SendDlgItemMessage = GuessStringType(SendDlgItemMessageA, SendDlgItemMessageW)


# DWORD WINAPI WaitForInputIdle(
#   _In_  HANDLE hProcess,
#   _In_  DWORD dwMilliseconds
# );
def WaitForInputIdle(hProcess, dwMilliseconds=INFINITE):
    _WaitForInputIdle = windll.user32.WaitForInputIdle
    _WaitForInputIdle.argtypes = [HANDLE, DWORD]
    _WaitForInputIdle.restype = DWORD

    r = _WaitForInputIdle(hProcess, dwMilliseconds)
    if r == WAIT_FAILED:
        raise ctypes.WinError()
    return r


# UINT RegisterWindowMessage(
#     LPCTSTR lpString
# );
def RegisterWindowMessageA(lpString):
    _RegisterWindowMessageA = windll.user32.RegisterWindowMessageA
    _RegisterWindowMessageA.argtypes = [LPSTR]
    _RegisterWindowMessageA.restype = UINT
    _RegisterWindowMessageA.errcheck = RaiseIfZero
    return _RegisterWindowMessageA(lpString)


def RegisterWindowMessageW(lpString):
    _RegisterWindowMessageW = windll.user32.RegisterWindowMessageW
    _RegisterWindowMessageW.argtypes = [LPWSTR]
    _RegisterWindowMessageW.restype = UINT
    _RegisterWindowMessageW.errcheck = RaiseIfZero
    return _RegisterWindowMessageW(lpString)


RegisterWindowMessage = GuessStringType(RegisterWindowMessageA, RegisterWindowMessageW)


# UINT RegisterClipboardFormat(
#     LPCTSTR lpString
# );
def RegisterClipboardFormatA(lpString):
    _RegisterClipboardFormatA = windll.user32.RegisterClipboardFormatA
    _RegisterClipboardFormatA.argtypes = [LPSTR]
    _RegisterClipboardFormatA.restype = UINT
    _RegisterClipboardFormatA.errcheck = RaiseIfZero
    return _RegisterClipboardFormatA(lpString)


def RegisterClipboardFormatW(lpString):
    _RegisterClipboardFormatW = windll.user32.RegisterClipboardFormatW
    _RegisterClipboardFormatW.argtypes = [LPWSTR]
    _RegisterClipboardFormatW.restype = UINT
    _RegisterClipboardFormatW.errcheck = RaiseIfZero
    return _RegisterClipboardFormatW(lpString)


RegisterClipboardFormat = GuessStringType(RegisterClipboardFormatA, RegisterClipboardFormatW)


# HANDLE WINAPI GetProp(
#   __in  HWND hWnd,
#   __in  LPCTSTR lpString
# );
def GetPropA(hWnd, lpString):
    _GetPropA = windll.user32.GetPropA
    _GetPropA.argtypes = [HWND, LPSTR]
    _GetPropA.restype = HANDLE
    return _GetPropA(hWnd, lpString)


def GetPropW(hWnd, lpString):
    _GetPropW = windll.user32.GetPropW
    _GetPropW.argtypes = [HWND, LPWSTR]
    _GetPropW.restype = HANDLE
    return _GetPropW(hWnd, lpString)


GetProp = GuessStringType(GetPropA, GetPropW)


# BOOL WINAPI SetProp(
#   __in      HWND hWnd,
#   __in      LPCTSTR lpString,
#   __in_opt  HANDLE hData
# );
def SetPropA(hWnd, lpString, hData):
    _SetPropA = windll.user32.SetPropA
    _SetPropA.argtypes = [HWND, LPSTR, HANDLE]
    _SetPropA.restype = BOOL
    _SetPropA.errcheck = RaiseIfZero
    _SetPropA(hWnd, lpString, hData)


def SetPropW(hWnd, lpString, hData):
    _SetPropW = windll.user32.SetPropW
    _SetPropW.argtypes = [HWND, LPWSTR, HANDLE]
    _SetPropW.restype = BOOL
    _SetPropW.errcheck = RaiseIfZero
    _SetPropW(hWnd, lpString, hData)


SetProp = GuessStringType(SetPropA, SetPropW)


# HANDLE WINAPI RemoveProp(
#   __in  HWND hWnd,
#   __in  LPCTSTR lpString
# );
def RemovePropA(hWnd, lpString):
    _RemovePropA = windll.user32.RemovePropA
    _RemovePropA.argtypes = [HWND, LPSTR]
    _RemovePropA.restype = HANDLE
    return _RemovePropA(hWnd, lpString)


def RemovePropW(hWnd, lpString):
    _RemovePropW = windll.user32.RemovePropW
    _RemovePropW.argtypes = [HWND, LPWSTR]
    _RemovePropW.restype = HANDLE
    return _RemovePropW(hWnd, lpString)


RemoveProp = GuessStringType(RemovePropA, RemovePropW)

# ==============================================================================
# This calculates the list of exported symbols.
_all = set(vars().keys()).difference(_all)
__all__ = [_x for _x in _all if not _x.startswith("_")]
__all__.sort()
# ==============================================================================

# === NexusCore/openenv\Lib\site-packages\nltk\tokenize\punkt.py ===
# Natural Language Toolkit: Punkt sentence tokenizer
#
# Copyright (C) 2001-2024 NLTK Project
# Algorithm: Kiss & Strunk (2006)
# Author: Willy <willy@csse.unimelb.edu.au> (original Python port)
#         Steven Bird <stevenbird1@gmail.com> (additions)
#         Edward Loper <edloper@gmail.com> (rewrite)
#         Joel Nothman <jnothman@student.usyd.edu.au> (almost rewrite)
#         Arthur Darcet <arthur@darcet.fr> (fixes)
#         Tom Aarsen <> (tackle ReDoS & performance issues)
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT

r"""
Punkt Sentence Tokenizer

This tokenizer divides a text into a list of sentences
by using an unsupervised algorithm to build a model for abbreviation
words, collocations, and words that start sentences.  It must be
trained on a large collection of plaintext in the target language
before it can be used.

The NLTK data package includes a pre-trained Punkt tokenizer for
English.

    >>> from nltk.tokenize import PunktTokenizer
    >>> text = '''
    ... Punkt knows that the periods in Mr. Smith and Johann S. Bach
    ... do not mark sentence boundaries.  And sometimes sentences
    ... can start with non-capitalized words.  i is a good variable
    ... name.
    ... '''
    >>> sent_detector = PunktTokenizer()
    >>> print('\n-----\n'.join(sent_detector.tokenize(text.strip())))
    Punkt knows that the periods in Mr. Smith and Johann S. Bach
    do not mark sentence boundaries.
    -----
    And sometimes sentences
    can start with non-capitalized words.
    -----
    i is a good variable
    name.

(Note that whitespace from the original text, including newlines, is
retained in the output.)

Punctuation following sentences is also included by default
(from NLTK 3.0 onwards). It can be excluded with the realign_boundaries
flag.

    >>> text = '''
    ... (How does it deal with this parenthesis?)  "It should be part of the
    ... previous sentence." "(And the same with this one.)" ('And this one!')
    ... "('(And (this)) '?)" [(and this. )]
    ... '''
    >>> print('\n-----\n'.join(
    ...     sent_detector.tokenize(text.strip())))
    (How does it deal with this parenthesis?)
    -----
    "It should be part of the
    previous sentence."
    -----
    "(And the same with this one.)"
    -----
    ('And this one!')
    -----
    "('(And (this)) '?)"
    -----
    [(and this. )]
    >>> print('\n-----\n'.join(
    ...     sent_detector.tokenize(text.strip(), realign_boundaries=False)))
    (How does it deal with this parenthesis?
    -----
    )  "It should be part of the
    previous sentence.
    -----
    " "(And the same with this one.
    -----
    )" ('And this one!
    -----
    ')
    "('(And (this)) '?
    -----
    )" [(and this.
    -----
    )]

However, Punkt is designed to learn parameters (a list of abbreviations, etc.)
unsupervised from a corpus similar to the target domain. The pre-packaged models
may therefore be unsuitable: use ``PunktSentenceTokenizer(text)`` to learn
parameters from the given text.

:class:`.PunktTrainer` learns parameters such as a list of abbreviations
(without supervision) from portions of text. Using a ``PunktTrainer`` directly
allows for incremental training and modification of the hyper-parameters used
to decide what is considered an abbreviation, etc.

The algorithm for this tokenizer is described in::

  Kiss, Tibor and Strunk, Jan (2006): Unsupervised Multilingual Sentence
    Boundary Detection.  Computational Linguistics 32: 485-525.
"""

# TODO: Make orthographic heuristic less susceptible to overtraining
# TODO: Frequent sentence starters optionally exclude always-capitalised words
# FIXME: Problem with ending string with e.g. '!!!' -> '!! !'

import math
import re
import string
from collections import defaultdict
from typing import Any, Dict, Iterator, List, Match, Optional, Tuple, Union

from nltk.probability import FreqDist
from nltk.tokenize.api import TokenizerI

######################################################################
# { Orthographic Context Constants
######################################################################
# The following constants are used to describe the orthographic
# contexts in which a word can occur.  BEG=beginning, MID=middle,
# UNK=unknown, UC=uppercase, LC=lowercase, NC=no case.

_ORTHO_BEG_UC = 1 << 1
"""Orthographic context: beginning of a sentence with upper case."""

_ORTHO_MID_UC = 1 << 2
"""Orthographic context: middle of a sentence with upper case."""

_ORTHO_UNK_UC = 1 << 3
"""Orthographic context: unknown position in a sentence with upper case."""

_ORTHO_BEG_LC = 1 << 4
"""Orthographic context: beginning of a sentence with lower case."""

_ORTHO_MID_LC = 1 << 5
"""Orthographic context: middle of a sentence with lower case."""

_ORTHO_UNK_LC = 1 << 6
"""Orthographic context: unknown position in a sentence with lower case."""

_ORTHO_UC = _ORTHO_BEG_UC + _ORTHO_MID_UC + _ORTHO_UNK_UC
"""Orthographic context: occurs with upper case."""

_ORTHO_LC = _ORTHO_BEG_LC + _ORTHO_MID_LC + _ORTHO_UNK_LC
"""Orthographic context: occurs with lower case."""

_ORTHO_MAP = {
    ("initial", "upper"): _ORTHO_BEG_UC,
    ("internal", "upper"): _ORTHO_MID_UC,
    ("unknown", "upper"): _ORTHO_UNK_UC,
    ("initial", "lower"): _ORTHO_BEG_LC,
    ("internal", "lower"): _ORTHO_MID_LC,
    ("unknown", "lower"): _ORTHO_UNK_LC,
}
"""A map from context position and first-letter case to the
appropriate orthographic context flag."""

# } (end orthographic context constants)
######################################################################

######################################################################
# { Decision reasons for debugging
######################################################################

REASON_DEFAULT_DECISION = "default decision"
REASON_KNOWN_COLLOCATION = "known collocation (both words)"
REASON_ABBR_WITH_ORTHOGRAPHIC_HEURISTIC = "abbreviation + orthographic heuristic"
REASON_ABBR_WITH_SENTENCE_STARTER = "abbreviation + frequent sentence starter"
REASON_INITIAL_WITH_ORTHOGRAPHIC_HEURISTIC = "initial + orthographic heuristic"
REASON_NUMBER_WITH_ORTHOGRAPHIC_HEURISTIC = "initial + orthographic heuristic"
REASON_INITIAL_WITH_SPECIAL_ORTHOGRAPHIC_HEURISTIC = (
    "initial + special orthographic heuristic"
)


# } (end decision reasons for debugging)
######################################################################

######################################################################
# { Language-dependent variables
######################################################################


class PunktLanguageVars:
    """
    Stores variables, mostly regular expressions, which may be
    language-dependent for correct application of the algorithm.
    An extension of this class may modify its properties to suit
    a language other than English; an instance can then be passed
    as an argument to PunktSentenceTokenizer and PunktTrainer
    constructors.
    """

    __slots__ = ("_re_period_context", "_re_word_tokenizer")

    def __getstate__(self):
        # All modifications to the class are performed by inheritance.
        # Non-default parameters to be saved must be defined in the inherited
        # class.
        return 1

    def __setstate__(self, state):
        return 1

    sent_end_chars = (".", "?", "!")
    """Characters which are candidates for sentence boundaries"""

    @property
    def _re_sent_end_chars(self):
        return "[%s]" % re.escape("".join(self.sent_end_chars))

    internal_punctuation = ",:;"  # might want to extend this..
    """sentence internal punctuation, which indicates an abbreviation if
    preceded by a period-final token."""

    re_boundary_realignment = re.compile(r'["\')\]}]+?(?:\s+|(?=--)|$)', re.MULTILINE)
    """Used to realign punctuation that should be included in a sentence
    although it follows the period (or ?, !)."""

    _re_word_start = r"[^\(\"\`{\[:;&\#\*@\)}\]\-,]"
    """Excludes some characters from starting word tokens"""

    @property
    def _re_non_word_chars(self):
        return r"(?:[)\";}\]\*:@\'\({\[%s])" % re.escape(
            "".join(set(self.sent_end_chars) - {"."})
        )

    """Characters that cannot appear within words"""

    _re_multi_char_punct = r"(?:\-{2,}|\.{2,}|(?:\.\s){2,}\.)"
    """Hyphen and ellipsis are multi-character punctuation"""

    _word_tokenize_fmt = r"""(
        %(MultiChar)s
        |
        (?=%(WordStart)s)\S+?  # Accept word characters until end is found
        (?= # Sequences marking a word's end
            \s|                                 # White-space
            $|                                  # End-of-string
            %(NonWord)s|%(MultiChar)s|          # Punctuation
            ,(?=$|\s|%(NonWord)s|%(MultiChar)s) # Comma if at end of word
        )
        |
        \S
    )"""
    """Format of a regular expression to split punctuation from words,
    excluding period."""

    def _word_tokenizer_re(self):
        """Compiles and returns a regular expression for word tokenization"""
        try:
            return self._re_word_tokenizer
        except AttributeError:
            self._re_word_tokenizer = re.compile(
                self._word_tokenize_fmt
                % {
                    "NonWord": self._re_non_word_chars,
                    "MultiChar": self._re_multi_char_punct,
                    "WordStart": self._re_word_start,
                },
                re.UNICODE | re.VERBOSE,
            )
            return self._re_word_tokenizer

    def word_tokenize(self, s):
        """Tokenize a string to split off punctuation other than periods"""
        return self._word_tokenizer_re().findall(s)

    _period_context_fmt = r"""
        %(SentEndChars)s             # a potential sentence ending
        (?=(?P<after_tok>
            %(NonWord)s              # either other punctuation
            |
            \s+(?P<next_tok>\S+)     # or whitespace and some other token
        ))"""
    """Format of a regular expression to find contexts including possible
    sentence boundaries. Matches token which the possible sentence boundary
    ends, and matches the following token within a lookahead expression."""

    def period_context_re(self):
        """Compiles and returns a regular expression to find contexts
        including possible sentence boundaries."""
        try:
            return self._re_period_context
        except:
            self._re_period_context = re.compile(
                self._period_context_fmt
                % {
                    "NonWord": self._re_non_word_chars,
                    "SentEndChars": self._re_sent_end_chars,
                },
                re.UNICODE | re.VERBOSE,
            )
            return self._re_period_context


_re_non_punct = re.compile(r"[^\W\d]", re.UNICODE)
"""Matches token types that are not merely punctuation. (Types for
numeric tokens are changed to ##number## and hence contain alpha.)"""


# }
######################################################################


# ////////////////////////////////////////////////////////////
# { Helper Functions
# ////////////////////////////////////////////////////////////


def _pair_iter(iterator):
    """
    Yields pairs of tokens from the given iterator such that each input
    token will appear as the first element in a yielded tuple. The last
    pair will have None as its second element.
    """
    iterator = iter(iterator)
    try:
        prev = next(iterator)
    except StopIteration:
        return
    for el in iterator:
        yield (prev, el)
        prev = el
    yield (prev, None)


######################################################################
# { Punkt Parameters
######################################################################


class PunktParameters:
    """Stores data used to perform sentence boundary detection with Punkt."""

    def __init__(self):
        self.abbrev_types = set()
        """A set of word types for known abbreviations."""

        self.collocations = set()
        """A set of word type tuples for known common collocations
        where the first word ends in a period.  E.g., ('S.', 'Bach')
        is a common collocation in a text that discusses 'Johann
        S. Bach'.  These count as negative evidence for sentence
        boundaries."""

        self.sent_starters = set()
        """A set of word types for words that often appear at the
        beginning of sentences."""

        self.ortho_context = defaultdict(int)
        """A dictionary mapping word types to the set of orthographic
        contexts that word type appears in.  Contexts are represented
        by adding orthographic context flags: ..."""

    def clear_abbrevs(self):
        self.abbrev_types = set()

    def clear_collocations(self):
        self.collocations = set()

    def clear_sent_starters(self):
        self.sent_starters = set()

    def clear_ortho_context(self):
        self.ortho_context = defaultdict(int)

    def add_ortho_context(self, typ, flag):
        self.ortho_context[typ] |= flag

    def _debug_ortho_context(self, typ):
        context = self.ortho_context[typ]
        if context & _ORTHO_BEG_UC:
            yield "BEG-UC"
        if context & _ORTHO_MID_UC:
            yield "MID-UC"
        if context & _ORTHO_UNK_UC:
            yield "UNK-UC"
        if context & _ORTHO_BEG_LC:
            yield "BEG-LC"
        if context & _ORTHO_MID_LC:
            yield "MID-LC"
        if context & _ORTHO_UNK_LC:
            yield "UNK-LC"


######################################################################
# { PunktToken
######################################################################


class PunktToken:
    """Stores a token of text with annotations produced during
    sentence boundary detection."""

    _properties = ["parastart", "linestart", "sentbreak", "abbr", "ellipsis"]
    __slots__ = ["tok", "type", "period_final"] + _properties

    def __init__(self, tok, **params):
        self.tok = tok
        self.type = self._get_type(tok)
        self.period_final = tok.endswith(".")

        for prop in self._properties:
            setattr(self, prop, None)
        for k in params:
            setattr(self, k, params[k])

    # ////////////////////////////////////////////////////////////
    # { Regular expressions for properties
    # ////////////////////////////////////////////////////////////
    # Note: [A-Za-z] is approximated by [^\W\d] in the general case.
    _RE_ELLIPSIS = re.compile(r"\.\.+$")
    _RE_NUMERIC = re.compile(r"^-?[\.,]?\d[\d,\.-]*\.?$")
    _RE_INITIAL = re.compile(r"[^\W\d]\.$", re.UNICODE)
    _RE_ALPHA = re.compile(r"[^\W\d]+$", re.UNICODE)

    # ////////////////////////////////////////////////////////////
    # { Derived properties
    # ////////////////////////////////////////////////////////////

    def _get_type(self, tok):
        """Returns a case-normalized representation of the token."""
        return self._RE_NUMERIC.sub("##number##", tok.lower())

    @property
    def type_no_period(self):
        """
        The type with its final period removed if it has one.
        """
        if len(self.type) > 1 and self.type[-1] == ".":
            return self.type[:-1]
        return self.type

    @property
    def type_no_sentperiod(self):
        """
        The type with its final period removed if it is marked as a
        sentence break.
        """
        if self.sentbreak:
            return self.type_no_period
        return self.type

    @property
    def first_upper(self):
        """True if the token's first character is uppercase."""
        return self.tok[0].isupper()

    @property
    def first_lower(self):
        """True if the token's first character is lowercase."""
        return self.tok[0].islower()

    @property
    def first_case(self):
        if self.first_lower:
            return "lower"
        if self.first_upper:
            return "upper"
        return "none"

    @property
    def is_ellipsis(self):
        """True if the token text is that of an ellipsis."""
        return self._RE_ELLIPSIS.match(self.tok)

    @property
    def is_number(self):
        """True if the token text is that of a number."""
        return self.type.startswith("##number##")

    @property
    def is_initial(self):
        """True if the token text is that of an initial."""
        return self._RE_INITIAL.match(self.tok)

    @property
    def is_alpha(self):
        """True if the token text is all alphabetic."""
        return self._RE_ALPHA.match(self.tok)

    @property
    def is_non_punct(self):
        """True if the token is either a number or is alphabetic."""
        return _re_non_punct.search(self.type)

    # ////////////////////////////////////////////////////////////
    # { String representation
    # ////////////////////////////////////////////////////////////

    def __repr__(self):
        """
        A string representation of the token that can reproduce it
        with eval(), which lists all the token's non-default
        annotations.
        """
        typestr = " type=%s," % repr(self.type) if self.type != self.tok else ""

        propvals = ", ".join(
            f"{p}={repr(getattr(self, p))}"
            for p in self._properties
            if getattr(self, p)
        )

        return "{}({},{} {})".format(
            self.__class__.__name__,
            repr(self.tok),
            typestr,
            propvals,
        )

    def __str__(self):
        """
        A string representation akin to that used by Kiss and Strunk.
        """
        res = self.tok
        if self.abbr:
            res += "<A>"
        if self.ellipsis:
            res += "<E>"
        if self.sentbreak:
            res += "<S>"
        return res


######################################################################
# { Punkt base class
######################################################################


class PunktBaseClass:
    """
    Includes common components of PunktTrainer and PunktSentenceTokenizer.
    """

    def __init__(self, lang_vars=None, token_cls=PunktToken, params=None):
        if lang_vars is None:
            lang_vars = PunktLanguageVars()
        if params is None:
            params = PunktParameters()
        self._params = params
        self._lang_vars = lang_vars
        self._Token = token_cls
        """The collection of parameters that determines the behavior
        of the punkt tokenizer."""

    # ////////////////////////////////////////////////////////////
    # { Word tokenization
    # ////////////////////////////////////////////////////////////

    def _tokenize_words(self, plaintext):
        """
        Divide the given text into tokens, using the punkt word
        segmentation regular expression, and generate the resulting list
        of tokens augmented as three-tuples with two boolean values for whether
        the given token occurs at the start of a paragraph or a new line,
        respectively.
        """
        parastart = False
        for line in plaintext.split("\n"):
            if line.strip():
                line_toks = iter(self._lang_vars.word_tokenize(line))

                try:
                    tok = next(line_toks)
                except StopIteration:
                    continue

                yield self._Token(tok, parastart=parastart, linestart=True)
                parastart = False

                for tok in line_toks:
                    yield self._Token(tok)
            else:
                parastart = True

    # ////////////////////////////////////////////////////////////
    # { Annotation Procedures
    # ////////////////////////////////////////////////////////////

    def _annotate_first_pass(
        self, tokens: Iterator[PunktToken]
    ) -> Iterator[PunktToken]:
        """
        Perform the first pass of annotation, which makes decisions
        based purely based on the word type of each word:

          - '?', '!', and '.' are marked as sentence breaks.
          - sequences of two or more periods are marked as ellipsis.
          - any word ending in '.' that's a known abbreviation is
            marked as an abbreviation.
          - any other word ending in '.' is marked as a sentence break.

        Return these annotations as a tuple of three sets:

          - sentbreak_toks: The indices of all sentence breaks.
          - abbrev_toks: The indices of all abbreviations.
          - ellipsis_toks: The indices of all ellipsis marks.
        """
        for aug_tok in tokens:
            self._first_pass_annotation(aug_tok)
            yield aug_tok

    def _first_pass_annotation(self, aug_tok: PunktToken) -> None:
        """
        Performs type-based annotation on a single token.
        """

        tok = aug_tok.tok

        if tok in self._lang_vars.sent_end_chars:
            aug_tok.sentbreak = True
        elif aug_tok.is_ellipsis:
            aug_tok.ellipsis = True
        elif aug_tok.period_final and not tok.endswith(".."):
            if (
                tok[:-1].lower() in self._params.abbrev_types
                or tok[:-1].lower().split("-")[-1] in self._params.abbrev_types
            ):
                aug_tok.abbr = True
            else:
                aug_tok.sentbreak = True

        return


######################################################################
# { Punkt Trainer
######################################################################


class PunktTrainer(PunktBaseClass):
    """Learns parameters used in Punkt sentence boundary detection."""

    def __init__(
        self, train_text=None, verbose=False, lang_vars=None, token_cls=PunktToken
    ):
        PunktBaseClass.__init__(self, lang_vars=lang_vars, token_cls=token_cls)

        self._type_fdist = FreqDist()
        """A frequency distribution giving the frequency of each
        case-normalized token type in the training data."""

        self._num_period_toks = 0
        """The number of words ending in period in the training data."""

        self._collocation_fdist = FreqDist()
        """A frequency distribution giving the frequency of all
        bigrams in the training data where the first word ends in a
        period.  Bigrams are encoded as tuples of word types.
        Especially common collocations are extracted from this
        frequency distribution, and stored in
        ``_params``.``collocations <PunktParameters.collocations>``."""

        self._sent_starter_fdist = FreqDist()
        """A frequency distribution giving the frequency of all words
        that occur at the training data at the beginning of a sentence
        (after the first pass of annotation).  Especially common
        sentence starters are extracted from this frequency
        distribution, and stored in ``_params.sent_starters``.
        """

        self._sentbreak_count = 0
        """The total number of sentence breaks identified in training, used for
        calculating the frequent sentence starter heuristic."""

        self._finalized = True
        """A flag as to whether the training has been finalized by finding
        collocations and sentence starters, or whether finalize_training()
        still needs to be called."""

        if train_text:
            self.train(train_text, verbose, finalize=True)

    def get_params(self):
        """
        Calculates and returns parameters for sentence boundary detection as
        derived from training."""
        if not self._finalized:
            self.finalize_training()
        return self._params

    # ////////////////////////////////////////////////////////////
    # { Customization Variables
    # ////////////////////////////////////////////////////////////

    ABBREV = 0.3
    """cut-off value whether a 'token' is an abbreviation"""

    IGNORE_ABBREV_PENALTY = False
    """allows the disabling of the abbreviation penalty heuristic, which
    exponentially disadvantages words that are found at times without a
    final period."""

    ABBREV_BACKOFF = 5
    """upper cut-off for Mikheev's(2002) abbreviation detection algorithm"""

    COLLOCATION = 7.88
    """minimal log-likelihood value that two tokens need to be considered
    as a collocation"""

    SENT_STARTER = 30
    """minimal log-likelihood value that a token requires to be considered
    as a frequent sentence starter"""

    INCLUDE_ALL_COLLOCS = False
    """this includes as potential collocations all word pairs where the first
    word ends in a period. It may be useful in corpora where there is a lot
    of variation that makes abbreviations like Mr difficult to identify."""

    INCLUDE_ABBREV_COLLOCS = False
    """this includes as potential collocations all word pairs where the first
    word is an abbreviation. Such collocations override the orthographic
    heuristic, but not the sentence starter heuristic. This is overridden by
    INCLUDE_ALL_COLLOCS, and if both are false, only collocations with initials
    and ordinals are considered."""
    """"""

    MIN_COLLOC_FREQ = 1
    """this sets a minimum bound on the number of times a bigram needs to
    appear before it can be considered a collocation, in addition to log
    likelihood statistics. This is useful when INCLUDE_ALL_COLLOCS is True."""

    # ////////////////////////////////////////////////////////////
    # { Training..
    # ////////////////////////////////////////////////////////////

    def train(self, text, verbose=False, finalize=True):
        """
        Collects training data from a given text. If finalize is True, it
        will determine all the parameters for sentence boundary detection. If
        not, this will be delayed until get_params() or finalize_training() is
        called. If verbose is True, abbreviations found will be listed.
        """
        # Break the text into tokens; record which token indices correspond to
        # line starts and paragraph starts; and determine their types.
        self._train_tokens(self._tokenize_words(text), verbose)
        if finalize:
            self.finalize_training(verbose)

    def train_tokens(self, tokens, verbose=False, finalize=True):
        """
        Collects training data from a given list of tokens.
        """
        self._train_tokens((self._Token(t) for t in tokens), verbose)
        if finalize:
            self.finalize_training(verbose)

    def _train_tokens(self, tokens, verbose):
        self._finalized = False

        # Ensure tokens are a list
        tokens = list(tokens)

        # Find the frequency of each case-normalized type.  (Don't
        # strip off final periods.)  Also keep track of the number of
        # tokens that end in periods.
        for aug_tok in tokens:
            self._type_fdist[aug_tok.type] += 1
            if aug_tok.period_final:
                self._num_period_toks += 1

        # Look for new abbreviations, and for types that no longer are
        unique_types = self._unique_types(tokens)
        for abbr, score, is_add in self._reclassify_abbrev_types(unique_types):
            if score >= self.ABBREV:
                if is_add:
                    self._params.abbrev_types.add(abbr)
                    if verbose:
                        print(f"  Abbreviation: [{score:6.4f}] {abbr}")
            else:
                if not is_add:
                    self._params.abbrev_types.remove(abbr)
                    if verbose:
                        print(f"  Removed abbreviation: [{score:6.4f}] {abbr}")

        # Make a preliminary pass through the document, marking likely
        # sentence breaks, abbreviations, and ellipsis tokens.
        tokens = list(self._annotate_first_pass(tokens))

        # Check what contexts each word type can appear in, given the
        # case of its first letter.
        self._get_orthography_data(tokens)

        # We need total number of sentence breaks to find sentence starters
        self._sentbreak_count += self._get_sentbreak_count(tokens)

        # The remaining heuristics relate to pairs of tokens where the first
        # ends in a period.
        for aug_tok1, aug_tok2 in _pair_iter(tokens):
            if not aug_tok1.period_final or not aug_tok2:
                continue

            # Is the first token a rare abbreviation?
            if self._is_rare_abbrev_type(aug_tok1, aug_tok2):
                self._params.abbrev_types.add(aug_tok1.type_no_period)
                if verbose:
                    print("  Rare Abbrev: %s" % aug_tok1.type)

            # Does second token have a high likelihood of starting a sentence?
            if self._is_potential_sent_starter(aug_tok2, aug_tok1):
                self._sent_starter_fdist[aug_tok2.type] += 1

            # Is this bigram a potential collocation?
            if self._is_potential_collocation(aug_tok1, aug_tok2):
                self._collocation_fdist[
                    (aug_tok1.type_no_period, aug_tok2.type_no_sentperiod)
                ] += 1

    def _unique_types(self, tokens):
        return {aug_tok.type for aug_tok in tokens}

    def finalize_training(self, verbose=False):
        """
        Uses data that has been gathered in training to determine likely
        collocations and sentence starters.
        """
        self._params.clear_sent_starters()
        for typ, log_likelihood in self._find_sent_starters():
            self._params.sent_starters.add(typ)
            if verbose:
                print(f"  Sent Starter: [{log_likelihood:6.4f}] {typ!r}")

        self._params.clear_collocations()
        for (typ1, typ2), log_likelihood in self._find_collocations():
            self._params.collocations.add((typ1, typ2))
            if verbose:
                print(f"  Collocation: [{log_likelihood:6.4f}] {typ1!r}+{typ2!r}")

        self._finalized = True

    # ////////////////////////////////////////////////////////////
    # { Overhead reduction
    # ////////////////////////////////////////////////////////////

    def freq_threshold(
        self, ortho_thresh=2, type_thresh=2, colloc_thres=2, sentstart_thresh=2
    ):
        """
        Allows memory use to be reduced after much training by removing data
        about rare tokens that are unlikely to have a statistical effect with
        further training. Entries occurring above the given thresholds will be
        retained.
        """
        if ortho_thresh > 1:
            old_oc = self._params.ortho_context
            self._params.clear_ortho_context()
            for tok in self._type_fdist:
                count = self._type_fdist[tok]
                if count >= ortho_thresh:
                    self._params.ortho_context[tok] = old_oc[tok]

        self._type_fdist = self._freq_threshold(self._type_fdist, type_thresh)
        self._collocation_fdist = self._freq_threshold(
            self._collocation_fdist, colloc_thres
        )
        self._sent_starter_fdist = self._freq_threshold(
            self._sent_starter_fdist, sentstart_thresh
        )

    def _freq_threshold(self, fdist, threshold):
        """
        Returns a FreqDist containing only data with counts below a given
        threshold, as well as a mapping (None -> count_removed).
        """
        # We assume that there is more data below the threshold than above it
        # and so create a new FreqDist rather than working in place.
        res = FreqDist()
        num_removed = 0
        for tok in fdist:
            count = fdist[tok]
            if count < threshold:
                num_removed += 1
            else:
                res[tok] += count
        res[None] += num_removed
        return res

    # ////////////////////////////////////////////////////////////
    # { Orthographic data
    # ////////////////////////////////////////////////////////////

    def _get_orthography_data(self, tokens):
        """
        Collect information about whether each token type occurs
        with different case patterns (i) overall, (ii) at
        sentence-initial positions, and (iii) at sentence-internal
        positions.
        """
        # 'initial' or 'internal' or 'unknown'
        context = "internal"
        tokens = list(tokens)

        for aug_tok in tokens:
            # If we encounter a paragraph break, then it's a good sign
            # that it's a sentence break.  But err on the side of
            # caution (by not positing a sentence break) if we just
            # saw an abbreviation.
            if aug_tok.parastart and context != "unknown":
                context = "initial"

            # If we're at the beginning of a line, then we can't decide
            # between 'internal' and 'initial'.
            if aug_tok.linestart and context == "internal":
                context = "unknown"

            # Find the case-normalized type of the token.  If it's a
            # sentence-final token, strip off the period.
            typ = aug_tok.type_no_sentperiod

            # Update the orthographic context table.
            flag = _ORTHO_MAP.get((context, aug_tok.first_case), 0)
            if flag:
                self._params.add_ortho_context(typ, flag)

            # Decide whether the next word is at a sentence boundary.
            if aug_tok.sentbreak:
                if not (aug_tok.is_number or aug_tok.is_initial):
                    context = "initial"
                else:
                    context = "unknown"
            elif aug_tok.ellipsis or aug_tok.abbr:
                context = "unknown"
            else:
                context = "internal"

    # ////////////////////////////////////////////////////////////
    # { Abbreviations
    # ////////////////////////////////////////////////////////////

    def _reclassify_abbrev_types(self, types):
        """
        (Re)classifies each given token if
          - it is period-final and not a known abbreviation; or
          - it is not period-final and is otherwise a known abbreviation
        by checking whether its previous classification still holds according
        to the heuristics of section 3.
        Yields triples (abbr, score, is_add) where abbr is the type in question,
        score is its log-likelihood with penalties applied, and is_add specifies
        whether the present type is a candidate for inclusion or exclusion as an
        abbreviation, such that:
          - (is_add and score >= 0.3)    suggests a new abbreviation; and
          - (not is_add and score < 0.3) suggests excluding an abbreviation.
        """
        # (While one could recalculate abbreviations from all .-final tokens at
        # every iteration, in cases requiring efficiency, the number of tokens
        # in the present training document will be much less.)

        for typ in types:
            # Check some basic conditions, to rule out words that are
            # clearly not abbrev_types.
            if not _re_non_punct.search(typ) or typ == "##number##":
                continue

            if typ.endswith("."):
                if typ in self._params.abbrev_types:
                    continue
                typ = typ[:-1]
                is_add = True
            else:
                if typ not in self._params.abbrev_types:
                    continue
                is_add = False

            # Count how many periods & nonperiods are in the
            # candidate.
            num_periods = typ.count(".") + 1
            num_nonperiods = len(typ) - num_periods + 1

            # Let <a> be the candidate without the period, and <b>
            # be the period.  Find a log likelihood ratio that
            # indicates whether <ab> occurs as a single unit (high
            # value of log_likelihood), or as two independent units <a> and
            # <b> (low value of log_likelihood).
            count_with_period = self._type_fdist[typ + "."]
            count_without_period = self._type_fdist[typ]
            log_likelihood = self._dunning_log_likelihood(
                count_with_period + count_without_period,
                self._num_period_toks,
                count_with_period,
                self._type_fdist.N(),
            )

            # Apply three scaling factors to 'tweak' the basic log
            # likelihood ratio:
            #   F_length: long word -> less likely to be an abbrev
            #   F_periods: more periods -> more likely to be an abbrev
            #   F_penalty: penalize occurrences w/o a period
            f_length = math.exp(-num_nonperiods)
            f_periods = num_periods
            f_penalty = int(self.IGNORE_ABBREV_PENALTY) or math.pow(
                num_nonperiods, -count_without_period
            )
            score = log_likelihood * f_length * f_periods * f_penalty

            yield typ, score, is_add

    def find_abbrev_types(self):
        """
        Recalculates abbreviations given type frequencies, despite no prior
        determination of abbreviations.
        This fails to include abbreviations otherwise found as "rare".
        """
        self._params.clear_abbrevs()
        tokens = (typ for typ in self._type_fdist if typ and typ.endswith("."))
        for abbr, score, _is_add in self._reclassify_abbrev_types(tokens):
            if score >= self.ABBREV:
                self._params.abbrev_types.add(abbr)

    # This function combines the work done by the original code's
    # functions `count_orthography_context`, `get_orthography_count`,
    # and `get_rare_abbreviations`.
    def _is_rare_abbrev_type(self, cur_tok, next_tok):
        """
        A word type is counted as a rare abbreviation if...
          - it's not already marked as an abbreviation
          - it occurs fewer than ABBREV_BACKOFF times
          - either it is followed by a sentence-internal punctuation
            mark, *or* it is followed by a lower-case word that
            sometimes appears with upper case, but never occurs with
            lower case at the beginning of sentences.
        """
        if cur_tok.abbr or not cur_tok.sentbreak:
            return False

        # Find the case-normalized type of the token.  If it's
        # a sentence-final token, strip off the period.
        typ = cur_tok.type_no_sentperiod

        # Proceed only if the type hasn't been categorized as an
        # abbreviation already, and is sufficiently rare...
        count = self._type_fdist[typ] + self._type_fdist[typ[:-1]]
        if typ in self._params.abbrev_types or count >= self.ABBREV_BACKOFF:
            return False

        # Record this token as an abbreviation if the next
        # token is a sentence-internal punctuation mark.
        # [XX] :1 or check the whole thing??
        if next_tok.tok[:1] in self._lang_vars.internal_punctuation:
            return True

        # Record this type as an abbreviation if the next
        # token...  (i) starts with a lower case letter,
        # (ii) sometimes occurs with an uppercase letter,
        # and (iii) never occus with an uppercase letter
        # sentence-internally.
        # [xx] should the check for (ii) be modified??
        if next_tok.first_lower:
            typ2 = next_tok.type_no_sentperiod
            typ2ortho_context = self._params.ortho_context[typ2]
            if (typ2ortho_context & _ORTHO_BEG_UC) and not (
                typ2ortho_context & _ORTHO_MID_UC
            ):
                return True

    # ////////////////////////////////////////////////////////////
    # { Log Likelihoods
    # ////////////////////////////////////////////////////////////

    # helper for _reclassify_abbrev_types:
    @staticmethod
    def _dunning_log_likelihood(count_a, count_b, count_ab, N):
        """
        A function that calculates the modified Dunning log-likelihood
        ratio scores for abbreviation candidates.  The details of how
        this works is available in the paper.
        """
        p1 = count_b / N
        p2 = 0.99

        null_hypo = count_ab * math.log(p1 + 1e-8) + (count_a - count_ab) * math.log(
            1.0 - p1 + 1e-8
        )
        alt_hypo = count_ab * math.log(p2) + (count_a - count_ab) * math.log(1.0 - p2)

        likelihood = null_hypo - alt_hypo

        return -2.0 * likelihood

    @staticmethod
    def _col_log_likelihood(count_a, count_b, count_ab, N):
        """
        A function that will just compute log-likelihood estimate, in
        the original paper it's described in algorithm 6 and 7.

        This *should* be the original Dunning log-likelihood values,
        unlike the previous log_l function where it used modified
        Dunning log-likelihood values
        """
        p = count_b / N
        p1 = count_ab / count_a
        try:
            p2 = (count_b - count_ab) / (N - count_a)
        except ZeroDivisionError:
            p2 = 1

        try:
            summand1 = count_ab * math.log(p) + (count_a - count_ab) * math.log(1.0 - p)
        except ValueError:
            summand1 = 0

        try:
            summand2 = (count_b - count_ab) * math.log(p) + (
                N - count_a - count_b + count_ab
            ) * math.log(1.0 - p)
        except ValueError:
            summand2 = 0

        if count_a == count_ab or p1 <= 0 or p1 >= 1:
            summand3 = 0
        else:
            summand3 = count_ab * math.log(p1) + (count_a - count_ab) * math.log(
                1.0 - p1
            )

        if count_b == count_ab or p2 <= 0 or p2 >= 1:
            summand4 = 0
        else:
            summand4 = (count_b - count_ab) * math.log(p2) + (
                N - count_a - count_b + count_ab
            ) * math.log(1.0 - p2)

        likelihood = summand1 + summand2 - summand3 - summand4

        return -2.0 * likelihood

    # ////////////////////////////////////////////////////////////
    # { Collocation Finder
    # ////////////////////////////////////////////////////////////

    def _is_potential_collocation(self, aug_tok1, aug_tok2):
        """
        Returns True if the pair of tokens may form a collocation given
        log-likelihood statistics.
        """
        return (
            (
                self.INCLUDE_ALL_COLLOCS
                or (self.INCLUDE_ABBREV_COLLOCS and aug_tok1.abbr)
                or (aug_tok1.sentbreak and (aug_tok1.is_number or aug_tok1.is_initial))
            )
            and aug_tok1.is_non_punct
            and aug_tok2.is_non_punct
        )

    def _find_collocations(self):
        """
        Generates likely collocations and their log-likelihood.
        """
        for types in self._collocation_fdist:
            try:
                typ1, typ2 = types
            except TypeError:
                # types may be None after calling freq_threshold()
                continue
            if typ2 in self._params.sent_starters:
                continue

            col_count = self._collocation_fdist[types]
            typ1_count = self._type_fdist[typ1] + self._type_fdist[typ1 + "."]
            typ2_count = self._type_fdist[typ2] + self._type_fdist[typ2 + "."]
            if (
                typ1_count > 1
                and typ2_count > 1
                and self.MIN_COLLOC_FREQ < col_count <= min(typ1_count, typ2_count)
            ):
                log_likelihood = self._col_log_likelihood(
                    typ1_count, typ2_count, col_count, self._type_fdist.N()
                )
                # Filter out the not-so-collocative
                if log_likelihood >= self.COLLOCATION and (
                    self._type_fdist.N() / typ1_count > typ2_count / col_count
                ):
                    yield (typ1, typ2), log_likelihood

    # ////////////////////////////////////////////////////////////
    # { Sentence-Starter Finder
    # ////////////////////////////////////////////////////////////

    def _is_potential_sent_starter(self, cur_tok, prev_tok):
        """
        Returns True given a token and the token that precedes it if it
        seems clear that the token is beginning a sentence.
        """
        # If a token (i) is preceded by a sentence break that is
        # not a potential ordinal number or initial, and (ii) is
        # alphabetic, then it is a a sentence-starter.
        return (
            prev_tok.sentbreak
            and not (prev_tok.is_number or prev_tok.is_initial)
            and cur_tok.is_alpha
        )

    def _find_sent_starters(self):
        """
        Uses collocation heuristics for each candidate token to
        determine if it frequently starts sentences.
        """
        for typ in self._sent_starter_fdist:
            if not typ:
                continue

            typ_at_break_count = self._sent_starter_fdist[typ]
            typ_count = self._type_fdist[typ] + self._type_fdist[typ + "."]
            if typ_count < typ_at_break_count:
                # needed after freq_threshold
                continue

            log_likelihood = self._col_log_likelihood(
                self._sentbreak_count,
                typ_count,
                typ_at_break_count,
                self._type_fdist.N(),
            )

            if (
                log_likelihood >= self.SENT_STARTER
                and self._type_fdist.N() / self._sentbreak_count
                > typ_count / typ_at_break_count
            ):
                yield typ, log_likelihood

    def _get_sentbreak_count(self, tokens):
        """
        Returns the number of sentence breaks marked in a given set of
        augmented tokens.
        """
        return sum(1 for aug_tok in tokens if aug_tok.sentbreak)


######################################################################
# { Punkt Sentence Tokenizer
######################################################################


class PunktSentenceTokenizer(PunktBaseClass, TokenizerI):
    """
    A sentence tokenizer which uses an unsupervised algorithm to build
    a model for abbreviation words, collocations, and words that start
    sentences; and then uses that model to find sentence boundaries.
    This approach has been shown to work well for many European
    languages.
    """

    def __init__(
        self, train_text=None, verbose=False, lang_vars=None, token_cls=PunktToken
    ):
        """
        train_text can either be the sole training text for this sentence
        boundary detector, or can be a PunktParameters object.
        """
        PunktBaseClass.__init__(self, lang_vars=lang_vars, token_cls=token_cls)

        if train_text:
            self._params = self.train(train_text, verbose)

    def train(self, train_text, verbose=False):
        """
        Derives parameters from a given training text, or uses the parameters
        given. Repeated calls to this method destroy previous parameters. For
        incremental training, instantiate a separate PunktTrainer instance.
        """
        if not isinstance(train_text, str):
            return train_text
        return PunktTrainer(
            train_text, lang_vars=self._lang_vars, token_cls=self._Token
        ).get_params()

    # ////////////////////////////////////////////////////////////
    # { Tokenization
    # ////////////////////////////////////////////////////////////

    def tokenize(self, text: str, realign_boundaries: bool = True) -> List[str]:
        """
        Given a text, returns a list of the sentences in that text.
        """
        return list(self.sentences_from_text(text, realign_boundaries))

    def debug_decisions(self, text: str) -> Iterator[Dict[str, Any]]:
        """
        Classifies candidate periods as sentence breaks, yielding a dict for
        each that may be used to understand why the decision was made.

        See format_debug_decision() to help make this output readable.
        """

        for match, decision_text in self._match_potential_end_contexts(text):
            tokens = self._tokenize_words(decision_text)
            tokens = list(self._annotate_first_pass(tokens))
            while tokens and not tokens[0].tok.endswith(self._lang_vars.sent_end_chars):
                tokens.pop(0)
            yield {
                "period_index": match.end() - 1,
                "text": decision_text,
                "type1": tokens[0].type,
                "type2": tokens[1].type,
                "type1_in_abbrs": bool(tokens[0].abbr),
                "type1_is_initial": bool(tokens[0].is_initial),
                "type2_is_sent_starter": tokens[1].type_no_sentperiod
                in self._params.sent_starters,
                "type2_ortho_heuristic": self._ortho_heuristic(tokens[1]),
                "type2_ortho_contexts": set(
                    self._params._debug_ortho_context(tokens[1].type_no_sentperiod)
                ),
                "collocation": (
                    tokens[0].type_no_sentperiod,
                    tokens[1].type_no_sentperiod,
                )
                in self._params.collocations,
                "reason": self._second_pass_annotation(tokens[0], tokens[1])
                or REASON_DEFAULT_DECISION,
                "break_decision": tokens[0].sentbreak,
            }

    def span_tokenize(
        self, text: str, realign_boundaries: bool = True
    ) -> Iterator[Tuple[int, int]]:
        """
        Given a text, generates (start, end) spans of sentences
        in the text.
        """
        slices = self._slices_from_text(text)
        if realign_boundaries:
            slices = self._realign_boundaries(text, slices)
        for sentence in slices:
            yield (sentence.start, sentence.stop)

    def sentences_from_text(
        self, text: str, realign_boundaries: bool = True
    ) -> List[str]:
        """
        Given a text, generates the sentences in that text by only
        testing candidate sentence breaks. If realign_boundaries is
        True, includes in the sentence closing punctuation that
        follows the period.
        """
        return [text[s:e] for s, e in self.span_tokenize(text, realign_boundaries)]

    def _get_last_whitespace_index(self, text: str) -> int:
        """
        Given a text, find the index of the *last* occurrence of *any*
        whitespace character, i.e. " ", "\n", "\t", "\r", etc.
        If none is found, return 0.
        """
        for i in range(len(text) - 1, -1, -1):
            if text[i] in string.whitespace:
                return i
        return 0

    def _match_potential_end_contexts(self, text: str) -> Iterator[Tuple[Match, str]]:
        """
        Given a text, find the matches of potential sentence breaks,
        alongside the contexts surrounding these sentence breaks.

        Since the fix for the ReDOS discovered in issue #2866, we no longer match
        the word before a potential end of sentence token. Instead, we use a separate
        regex for this. As a consequence, `finditer`'s desire to find non-overlapping
        matches no longer aids us in finding the single longest match.
        Where previously, we could use::

            >>> pst = PunktSentenceTokenizer()
            >>> text = "Very bad acting!!! I promise."
            >>> list(pst._lang_vars.period_context_re().finditer(text)) # doctest: +SKIP
            [<re.Match object; span=(9, 18), match='acting!!!'>]

        Now we have to find the word before (i.e. 'acting') separately, and `finditer`
        returns::

            >>> pst = PunktSentenceTokenizer()
            >>> text = "Very bad acting!!! I promise."
            >>> list(pst._lang_vars.period_context_re().finditer(text)) # doctest: +NORMALIZE_WHITESPACE
            [<re.Match object; span=(15, 16), match='!'>,
            <re.Match object; span=(16, 17), match='!'>,
            <re.Match object; span=(17, 18), match='!'>]

        So, we need to find the word before the match from right to left, and then manually remove
        the overlaps. That is what this method does::

            >>> pst = PunktSentenceTokenizer()
            >>> text = "Very bad acting!!! I promise."
            >>> list(pst._match_potential_end_contexts(text))
            [(<re.Match object; span=(17, 18), match='!'>, 'acting!!! I')]

        :param text: String of one or more sentences
        :type text: str
        :return: Generator of match-context tuples.
        :rtype: Iterator[Tuple[Match, str]]
        """
        previous_slice = slice(0, 0)
        previous_match = None
        for match in self._lang_vars.period_context_re().finditer(text):
            # Get the slice of the previous word
            before_text = text[previous_slice.stop : match.start()]
            index_after_last_space = self._get_last_whitespace_index(before_text)
            if index_after_last_space:
                # + 1 to exclude the space itself
                index_after_last_space += previous_slice.stop + 1
            else:
                index_after_last_space = previous_slice.start
            prev_word_slice = slice(index_after_last_space, match.start())

            # If the previous slice does not overlap with this slice, then
            # we can yield the previous match and slice. If there is an overlap,
            # then we do not yield the previous match and slice.
            if previous_match and previous_slice.stop <= prev_word_slice.start:
                yield (
                    previous_match,
                    text[previous_slice]
                    + previous_match.group()
                    + previous_match.group("after_tok"),
                )
            previous_match = match
            previous_slice = prev_word_slice

        # Yield the last match and context, if it exists
        if previous_match:
            yield (
                previous_match,
                text[previous_slice]
                + previous_match.group()
                + previous_match.group("after_tok"),
            )

    def _slices_from_text(self, text: str) -> Iterator[slice]:
        last_break = 0
        for match, context in self._match_potential_end_contexts(text):
            if self.text_contains_sentbreak(context):
                yield slice(last_break, match.end())
                if match.group("next_tok"):
                    # next sentence starts after whitespace
                    last_break = match.start("next_tok")
                else:
                    # next sentence starts at following punctuation
                    last_break = match.end()
        # The last sentence should not contain trailing whitespace.
        yield slice(last_break, len(text.rstrip()))

    def _realign_boundaries(
        self, text: str, slices: Iterator[slice]
    ) -> Iterator[slice]:
        """
        Attempts to realign punctuation that falls after the period but
        should otherwise be included in the same sentence.

        For example: "(Sent1.) Sent2." will otherwise be split as::

            ["(Sent1.", ") Sent1."].

        This method will produce::

            ["(Sent1.)", "Sent2."].
        """
        realign = 0
        for sentence1, sentence2 in _pair_iter(slices):
            sentence1 = slice(sentence1.start + realign, sentence1.stop)
            if not sentence2:
                if text[sentence1]:
                    yield sentence1
                continue

            m = self._lang_vars.re_boundary_realignment.match(text[sentence2])
            if m:
                yield slice(sentence1.start, sentence2.start + len(m.group(0).rstrip()))
                realign = m.end()
            else:
                realign = 0
                if text[sentence1]:
                    yield sentence1

    def text_contains_sentbreak(self, text: str) -> bool:
        """
        Returns True if the given text includes a sentence break.
        """
        found = False  # used to ignore last token
        for tok in self._annotate_tokens(self._tokenize_words(text)):
            if found:
                return True
            if tok.sentbreak:
                found = True
        return False

    def sentences_from_text_legacy(self, text: str) -> Iterator[str]:
        """
        Given a text, generates the sentences in that text. Annotates all
        tokens, rather than just those with possible sentence breaks. Should
        produce the same results as ``sentences_from_text``.
        """
        tokens = self._annotate_tokens(self._tokenize_words(text))
        return self._build_sentence_list(text, tokens)

    def sentences_from_tokens(
        self, tokens: Iterator[PunktToken]
    ) -> Iterator[PunktToken]:
        """
        Given a sequence of tokens, generates lists of tokens, each list
        corresponding to a sentence.
        """
        tokens = iter(self._annotate_tokens(self._Token(t) for t in tokens))
        sentence = []
        for aug_tok in tokens:
            sentence.append(aug_tok.tok)
            if aug_tok.sentbreak:
                yield sentence
                sentence = []
        if sentence:
            yield sentence

    def _annotate_tokens(self, tokens: Iterator[PunktToken]) -> Iterator[PunktToken]:
        """
        Given a set of tokens augmented with markers for line-start and
        paragraph-start, returns an iterator through those tokens with full
        annotation including predicted sentence breaks.
        """
        # Make a preliminary pass through the document, marking likely
        # sentence breaks, abbreviations, and ellipsis tokens.
        tokens = self._annotate_first_pass(tokens)

        # Make a second pass through the document, using token context
        # information to change our preliminary decisions about where
        # sentence breaks, abbreviations, and ellipsis occurs.
        tokens = self._annotate_second_pass(tokens)

        ## [XX] TESTING
        # tokens = list(tokens)
        # self.dump(tokens)

        return tokens

    def _build_sentence_list(
        self, text: str, tokens: Iterator[PunktToken]
    ) -> Iterator[str]:
        """
        Given the original text and the list of augmented word tokens,
        construct and return a tokenized list of sentence strings.
        """
        # Most of the work here is making sure that we put the right
        # pieces of whitespace back in all the right places.

        # Our position in the source text, used to keep track of which
        # whitespace to add:
        pos = 0

        # A regular expression that finds pieces of whitespace:
        white_space_regexp = re.compile(r"\s*")

        sentence = ""
        for aug_tok in tokens:
            tok = aug_tok.tok

            # Find the whitespace before this token, and update pos.
            white_space = white_space_regexp.match(text, pos).group()
            pos += len(white_space)

            # Some of the rules used by the punkt word tokenizer
            # strip whitespace out of the text, resulting in tokens
            # that contain whitespace in the source text.  If our
            # token doesn't match, see if adding whitespace helps.
            # If so, then use the version with whitespace.
            if text[pos : pos + len(tok)] != tok:
                pat = r"\s*".join(re.escape(c) for c in tok)
                m = re.compile(pat).match(text, pos)
                if m:
                    tok = m.group()

            # Move our position pointer to the end of the token.
            assert text[pos : pos + len(tok)] == tok
            pos += len(tok)

            # Add this token.  If it's not at the beginning of the
            # sentence, then include any whitespace that separated it
            # from the previous token.
            if sentence:
                sentence += white_space
            sentence += tok

            # If we're at a sentence break, then start a new sentence.
            if aug_tok.sentbreak:
                yield sentence
                sentence = ""

        # If the last sentence is empty, discard it.
        if sentence:
            yield sentence

    # [XX] TESTING
    def dump(self, tokens: Iterator[PunktToken]) -> None:
        print("writing to /tmp/punkt.new...")
        with open("/tmp/punkt.new", "w") as outfile:
            for aug_tok in tokens:
                if aug_tok.parastart:
                    outfile.write("\n\n")
                elif aug_tok.linestart:
                    outfile.write("\n")
                else:
                    outfile.write(" ")

                outfile.write(str(aug_tok))

    # ////////////////////////////////////////////////////////////
    # { Customization Variables
    # ////////////////////////////////////////////////////////////

    PUNCTUATION = tuple(";:,.!?")

    # ////////////////////////////////////////////////////////////
    # { Annotation Procedures
    # ////////////////////////////////////////////////////////////

    def _annotate_second_pass(
        self, tokens: Iterator[PunktToken]
    ) -> Iterator[PunktToken]:
        """
        Performs a token-based classification (section 4) over the given
        tokens, making use of the orthographic heuristic (4.1.1), collocation
        heuristic (4.1.2) and frequent sentence starter heuristic (4.1.3).
        """
        for token1, token2 in _pair_iter(tokens):
            self._second_pass_annotation(token1, token2)
            yield token1

    def _second_pass_annotation(
        self, aug_tok1: PunktToken, aug_tok2: Optional[PunktToken]
    ) -> Optional[str]:
        """
        Performs token-based classification over a pair of contiguous tokens
        updating the first.
        """
        # Is it the last token? We can't do anything then.
        if not aug_tok2:
            return

        if not aug_tok1.period_final:
            # We only care about words ending in periods.
            return
        typ = aug_tok1.type_no_period
        next_typ = aug_tok2.type_no_sentperiod
        tok_is_initial = aug_tok1.is_initial

        # [4.1.2. Collocation Heuristic] If there's a
        # collocation between the word before and after the
        # period, then label tok as an abbreviation and NOT
        # a sentence break. Note that collocations with
        # frequent sentence starters as their second word are
        # excluded in training.
        if (typ, next_typ) in self._params.collocations:
            aug_tok1.sentbreak = False
            aug_tok1.abbr = True
            return REASON_KNOWN_COLLOCATION

        # [4.2. Token-Based Reclassification of Abbreviations] If
        # the token is an abbreviation or an ellipsis, then decide
        # whether we should *also* classify it as a sentbreak.
        if (aug_tok1.abbr or aug_tok1.ellipsis) and (not tok_is_initial):
            # [4.1.1. Orthographic Heuristic] Check if there's
            # orthogrpahic evidence about whether the next word
            # starts a sentence or not.
            is_sent_starter = self._ortho_heuristic(aug_tok2)
            if is_sent_starter == True:
                aug_tok1.sentbreak = True
                return REASON_ABBR_WITH_ORTHOGRAPHIC_HEURISTIC

            # [4.1.3. Frequent Sentence Starter Heruistic] If the
            # next word is capitalized, and is a member of the
            # frequent-sentence-starters list, then label tok as a
            # sentence break.
            if aug_tok2.first_upper and next_typ in self._params.sent_starters:
                aug_tok1.sentbreak = True
                return REASON_ABBR_WITH_SENTENCE_STARTER

        # [4.3. Token-Based Detection of Initials and Ordinals]
        # Check if any initials or ordinals tokens that are marked
        # as sentbreaks should be reclassified as abbreviations.
        if tok_is_initial or typ == "##number##":
            # [4.1.1. Orthographic Heuristic] Check if there's
            # orthogrpahic evidence about whether the next word
            # starts a sentence or not.
            is_sent_starter = self._ortho_heuristic(aug_tok2)

            if is_sent_starter == False:
                aug_tok1.sentbreak = False
                aug_tok1.abbr = True
                if tok_is_initial:
                    return REASON_INITIAL_WITH_ORTHOGRAPHIC_HEURISTIC
                return REASON_NUMBER_WITH_ORTHOGRAPHIC_HEURISTIC

            # Special heuristic for initials: if orthogrpahic
            # heuristic is unknown, and next word is always
            # capitalized, then mark as abbrev (eg: J. Bach).
            if (
                is_sent_starter == "unknown"
                and tok_is_initial
                and aug_tok2.first_upper
                and not (self._params.ortho_context[next_typ] & _ORTHO_LC)
            ):
                aug_tok1.sentbreak = False
                aug_tok1.abbr = True
                return REASON_INITIAL_WITH_SPECIAL_ORTHOGRAPHIC_HEURISTIC

        return

    def _ortho_heuristic(self, aug_tok: PunktToken) -> Union[bool, str]:
        """
        Decide whether the given token is the first token in a sentence.
        """
        # Sentences don't start with punctuation marks:
        if aug_tok.tok in self.PUNCTUATION:
            return False

        ortho_context = self._params.ortho_context[aug_tok.type_no_sentperiod]

        # If the word is capitalized, occurs at least once with a
        # lower case first letter, and never occurs with an upper case
        # first letter sentence-internally, then it's a sentence starter.
        if (
            aug_tok.first_upper
            and (ortho_context & _ORTHO_LC)
            and not (ortho_context & _ORTHO_MID_UC)
        ):
            return True

        # If the word is lower case, and either (a) we've seen it used
        # with upper case, or (b) we've never seen it used
        # sentence-initially with lower case, then it's not a sentence
        # starter.
        if aug_tok.first_lower and (
            (ortho_context & _ORTHO_UC) or not (ortho_context & _ORTHO_BEG_LC)
        ):
            return False

        # Otherwise, we're not sure.
        return "unknown"


class PunktTokenizer(PunktSentenceTokenizer):
    """
    Punkt Sentence Tokenizer that loads/saves its parameters from/to data files
    """

    def __init__(self, lang="english"):
        PunktSentenceTokenizer.__init__(self)
        self.load_lang(lang)

    def load_lang(self, lang="english"):
        from nltk.data import find

        lang_dir = find(f"tokenizers/punkt_tab/{lang}/")
        self._params = load_punkt_params(lang_dir)
        self._lang = lang

    def save_params(self):
        save_punkt_params(self._params, dir=f"/tmp/{self._lang}")


def load_punkt_params(lang_dir):
    from nltk.tabdata import PunktDecoder

    pdec = PunktDecoder()
    # Make a new Parameters object:
    params = PunktParameters()
    with open(f"{lang_dir}/collocations.tab", encoding="utf-8") as f:
        params.collocations = pdec.tab2tups(f)
    with open(f"{lang_dir}/sent_starters.txt", encoding="utf-8") as f:
        params.sent_starters = pdec.txt2set(f)
    with open(f"{lang_dir}/abbrev_types.txt", encoding="utf-8") as f:
        params.abbrev_types = pdec.txt2set(f)
    with open(f"{lang_dir}/ortho_context.tab", encoding="utf-8") as f:
        params.ortho_context = pdec.tab2intdict(f)
    return params


def save_punkt_params(params, dir="/tmp/punkt_tab"):
    from os import mkdir
    from os.path import isdir

    from nltk.tabdata import TabEncoder

    if not isdir(dir):
        mkdir(dir)
    tenc = TabEncoder()
    with open(f"{dir}/collocations.tab", "w") as f:
        f.write(f"{tenc.tups2tab(params.collocations)}")
    with open(f"{dir}/sent_starters.txt", "w") as f:
        f.write(f"{tenc.set2txt(params.sent_starters)}")
    with open(f"{dir}/abbrev_types.txt", "w") as f:
        f.write(f"{tenc.set2txt(params.abbrev_types)}")
    with open(f"{dir}/ortho_context.tab", "w") as f:
        f.write(f"{tenc.ivdict2tab(params.ortho_context)}")


# def punkt_tokenizer(lang="english"):
# Make a new Tokenizer
#    tokenizer = PunktTokenizer(lang)
#    return tokenizer


DEBUG_DECISION_FMT = """Text: {text!r} (at offset {period_index})
Sentence break? {break_decision} ({reason})
Collocation? {collocation}
{type1!r}:
    known abbreviation: {type1_in_abbrs}
    is initial: {type1_is_initial}
{type2!r}:
    known sentence starter: {type2_is_sent_starter}
    orthographic heuristic suggests is a sentence starter? {type2_ortho_heuristic}
    orthographic contexts in training: {type2_ortho_contexts}
"""


def format_debug_decision(d):
    return DEBUG_DECISION_FMT.format(**d)


def demo(text, tok_cls=PunktSentenceTokenizer, train_cls=PunktTrainer):
    """Builds a punkt model and applies it to the same text"""
    cleanup = (
        lambda s: re.compile(r"(?:\r|^\s+)", re.MULTILINE).sub("", s).replace("\n", " ")
    )
    trainer = train_cls()
    trainer.INCLUDE_ALL_COLLOCS = True
    trainer.train(text)
    sbd = tok_cls(trainer.get_params())
    for sentence in sbd.sentences_from_text(text):
        print(cleanup(sentence))

# === NexusCore/openenv\Lib\site-packages\matplotlib\animation.py ===
import abc
import base64
import contextlib
from io import BytesIO, TextIOWrapper
import itertools
import logging
from pathlib import Path
import shutil
import subprocess
import sys
from tempfile import TemporaryDirectory
import uuid
import warnings

import numpy as np
from PIL import Image

import matplotlib as mpl
from matplotlib._animation_data import (
    DISPLAY_TEMPLATE, INCLUDED_FRAMES, JS_INCLUDE, STYLE_INCLUDE)
from matplotlib import _api, cbook
import matplotlib.colors as mcolors

_log = logging.getLogger(__name__)

# Process creation flag for subprocess to prevent it raising a terminal
# window. See for example https://stackoverflow.com/q/24130623/
subprocess_creation_flags = (
    subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0)


def adjusted_figsize(w, h, dpi, n):
    """
    Compute figure size so that pixels are a multiple of n.

    Parameters
    ----------
    w, h : float
        Size in inches.

    dpi : float
        The dpi.

    n : int
        The target multiple.

    Returns
    -------
    wnew, hnew : float
        The new figure size in inches.
    """

    # this maybe simplified if / when we adopt consistent rounding for
    # pixel size across the whole library
    def correct_roundoff(x, dpi, n):
        if int(x*dpi) % n != 0:
            if int(np.nextafter(x, np.inf)*dpi) % n == 0:
                x = np.nextafter(x, np.inf)
            elif int(np.nextafter(x, -np.inf)*dpi) % n == 0:
                x = np.nextafter(x, -np.inf)
        return x

    wnew = int(w * dpi / n) * n / dpi
    hnew = int(h * dpi / n) * n / dpi
    return correct_roundoff(wnew, dpi, n), correct_roundoff(hnew, dpi, n)


class MovieWriterRegistry:
    """Registry of available writer classes by human readable name."""

    def __init__(self):
        self._registered = dict()

    def register(self, name):
        """
        Decorator for registering a class under a name.

        Example use::

            @registry.register(name)
            class Foo:
                pass
        """
        def wrapper(writer_cls):
            self._registered[name] = writer_cls
            return writer_cls
        return wrapper

    def is_available(self, name):
        """
        Check if given writer is available by name.

        Parameters
        ----------
        name : str

        Returns
        -------
        bool
        """
        try:
            cls = self._registered[name]
        except KeyError:
            return False
        return cls.isAvailable()

    def __iter__(self):
        """Iterate over names of available writer class."""
        for name in self._registered:
            if self.is_available(name):
                yield name

    def list(self):
        """Get a list of available MovieWriters."""
        return [*self]

    def __getitem__(self, name):
        """Get an available writer class from its name."""
        if self.is_available(name):
            return self._registered[name]
        raise RuntimeError(f"Requested MovieWriter ({name}) not available")


writers = MovieWriterRegistry()


class AbstractMovieWriter(abc.ABC):
    """
    Abstract base class for writing movies, providing a way to grab frames by
    calling `~AbstractMovieWriter.grab_frame`.

    `setup` is called to start the process and `finish` is called afterwards.
    `saving` is provided as a context manager to facilitate this process as ::

        with moviewriter.saving(fig, outfile='myfile.mp4', dpi=100):
            # Iterate over frames
            moviewriter.grab_frame(**savefig_kwargs)

    The use of the context manager ensures that `setup` and `finish` are
    performed as necessary.

    An instance of a concrete subclass of this class can be given as the
    ``writer`` argument of `Animation.save()`.
    """

    def __init__(self, fps=5, metadata=None, codec=None, bitrate=None):
        self.fps = fps
        self.metadata = metadata if metadata is not None else {}
        self.codec = mpl._val_or_rc(codec, 'animation.codec')
        self.bitrate = mpl._val_or_rc(bitrate, 'animation.bitrate')

    @abc.abstractmethod
    def setup(self, fig, outfile, dpi=None):
        """
        Setup for writing the movie file.

        Parameters
        ----------
        fig : `~matplotlib.figure.Figure`
            The figure object that contains the information for frames.
        outfile : str
            The filename of the resulting movie file.
        dpi : float, default: ``fig.dpi``
            The DPI (or resolution) for the file.  This controls the size
            in pixels of the resulting movie file.
        """
        # Check that path is valid
        Path(outfile).parent.resolve(strict=True)
        self.outfile = outfile
        self.fig = fig
        if dpi is None:
            dpi = self.fig.dpi
        self.dpi = dpi

    @property
    def frame_size(self):
        """A tuple ``(width, height)`` in pixels of a movie frame."""
        w, h = self.fig.get_size_inches()
        return int(w * self.dpi), int(h * self.dpi)

    def _supports_transparency(self):
        """
        Whether this writer supports transparency.

        Writers may consult output file type and codec to determine this at runtime.
        """
        return False

    @abc.abstractmethod
    def grab_frame(self, **savefig_kwargs):
        """
        Grab the image information from the figure and save as a movie frame.

        All keyword arguments in *savefig_kwargs* are passed on to the
        `~.Figure.savefig` call that saves the figure.  However, several
        keyword arguments that are supported by `~.Figure.savefig` may not be
        passed as they are controlled by the MovieWriter:

        - *dpi*, *bbox_inches*:  These may not be passed because each frame of the
           animation much be exactly the same size in pixels.
        - *format*: This is controlled by the MovieWriter.
        """

    @abc.abstractmethod
    def finish(self):
        """Finish any processing for writing the movie."""

    @contextlib.contextmanager
    def saving(self, fig, outfile, dpi, *args, **kwargs):
        """
        Context manager to facilitate writing the movie file.

        ``*args, **kw`` are any parameters that should be passed to `setup`.
        """
        if mpl.rcParams['savefig.bbox'] == 'tight':
            _log.info("Disabling savefig.bbox = 'tight', as it may cause "
                      "frame size to vary, which is inappropriate for "
                      "animation.")

        # This particular sequence is what contextlib.contextmanager wants
        self.setup(fig, outfile, dpi, *args, **kwargs)
        with mpl.rc_context({'savefig.bbox': None}):
            try:
                yield self
            finally:
                self.finish()


class MovieWriter(AbstractMovieWriter):
    """
    Base class for writing movies.

    This is a base class for MovieWriter subclasses that write a movie frame
    data to a pipe. You cannot instantiate this class directly.
    See examples for how to use its subclasses.

    Attributes
    ----------
    frame_format : str
        The format used in writing frame data, defaults to 'rgba'.
    fig : `~matplotlib.figure.Figure`
        The figure to capture data from.
        This must be provided by the subclasses.
    """

    # Builtin writer subclasses additionally define the _exec_key and _args_key
    # attributes, which indicate the rcParams entries where the path to the
    # executable and additional command-line arguments to the executable are
    # stored.  Third-party writers cannot meaningfully set these as they cannot
    # extend rcParams with new keys.

    # Pipe-based writers only support RGBA, but file-based ones support more
    # formats.
    supported_formats = ["rgba"]

    def __init__(self, fps=5, codec=None, bitrate=None, extra_args=None,
                 metadata=None):
        """
        Parameters
        ----------
        fps : int, default: 5
            Movie frame rate (per second).
        codec : str or None, default: :rc:`animation.codec`
            The codec to use.
        bitrate : int, default: :rc:`animation.bitrate`
            The bitrate of the movie, in kilobits per second.  Higher values
            means higher quality movies, but increase the file size.  A value
            of -1 lets the underlying movie encoder select the bitrate.
        extra_args : list of str or None, optional
            Extra command-line arguments passed to the underlying movie encoder. These
            arguments are passed last to the encoder, just before the filename. The
            default, None, means to use :rc:`animation.[name-of-encoder]_args` for the
            builtin writers.
        metadata : dict[str, str], default: {}
            A dictionary of keys and values for metadata to include in the
            output file. Some keys that may be of use include:
            title, artist, genre, subject, copyright, srcform, comment.
        """
        if type(self) is MovieWriter:
            # TODO MovieWriter is still an abstract class and needs to be
            #      extended with a mixin. This should be clearer in naming
            #      and description. For now, just give a reasonable error
            #      message to users.
            raise TypeError(
                'MovieWriter cannot be instantiated directly. Please use one '
                'of its subclasses.')

        super().__init__(fps=fps, metadata=metadata, codec=codec,
                         bitrate=bitrate)
        self.frame_format = self.supported_formats[0]
        self.extra_args = extra_args

    def _adjust_frame_size(self):
        if self.codec == 'h264':
            wo, ho = self.fig.get_size_inches()
            w, h = adjusted_figsize(wo, ho, self.dpi, 2)
            if (wo, ho) != (w, h):
                self.fig.set_size_inches(w, h, forward=True)
                _log.info('figure size in inches has been adjusted '
                          'from %s x %s to %s x %s', wo, ho, w, h)
        else:
            w, h = self.fig.get_size_inches()
        _log.debug('frame size in pixels is %s x %s', *self.frame_size)
        return w, h

    def setup(self, fig, outfile, dpi=None):
        # docstring inherited
        super().setup(fig, outfile, dpi=dpi)
        self._w, self._h = self._adjust_frame_size()
        # Run here so that grab_frame() can write the data to a pipe. This
        # eliminates the need for temp files.
        self._run()

    def _run(self):
        # Uses subprocess to call the program for assembling frames into a
        # movie file.  *args* returns the sequence of command line arguments
        # from a few configuration options.
        command = self._args()
        _log.info('MovieWriter._run: running command: %s',
                  cbook._pformat_subprocess(command))
        PIPE = subprocess.PIPE
        self._proc = subprocess.Popen(
            command, stdin=PIPE, stdout=PIPE, stderr=PIPE,
            creationflags=subprocess_creation_flags)

    def finish(self):
        """Finish any processing for writing the movie."""
        out, err = self._proc.communicate()
        # Use the encoding/errors that universal_newlines would use.
        out = TextIOWrapper(BytesIO(out)).read()
        err = TextIOWrapper(BytesIO(err)).read()
        if out:
            _log.log(
                logging.WARNING if self._proc.returncode else logging.DEBUG,
                "MovieWriter stdout:\n%s", out)
        if err:
            _log.log(
                logging.WARNING if self._proc.returncode else logging.DEBUG,
                "MovieWriter stderr:\n%s", err)
        if self._proc.returncode:
            raise subprocess.CalledProcessError(
                self._proc.returncode, self._proc.args, out, err)

    def grab_frame(self, **savefig_kwargs):
        # docstring inherited
        _validate_grabframe_kwargs(savefig_kwargs)
        _log.debug('MovieWriter.grab_frame: Grabbing frame.')
        # Readjust the figure size in case it has been changed by the user.
        # All frames must have the same size to save the movie correctly.
        self.fig.set_size_inches(self._w, self._h)
        # Save the figure data to the sink, using the frame format and dpi.
        self.fig.savefig(self._proc.stdin, format=self.frame_format,
                         dpi=self.dpi, **savefig_kwargs)

    def _args(self):
        """Assemble list of encoder-specific command-line arguments."""
        return NotImplementedError("args needs to be implemented by subclass.")

    @classmethod
    def bin_path(cls):
        """
        Return the binary path to the commandline tool used by a specific
        subclass. This is a class method so that the tool can be looked for
        before making a particular MovieWriter subclass available.
        """
        return str(mpl.rcParams[cls._exec_key])

    @classmethod
    def isAvailable(cls):
        """Return whether a MovieWriter subclass is actually available."""
        return shutil.which(cls.bin_path()) is not None


class FileMovieWriter(MovieWriter):
    """
    `MovieWriter` for writing to individual files and stitching at the end.

    This must be sub-classed to be useful.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.frame_format = mpl.rcParams['animation.frame_format']

    def setup(self, fig, outfile, dpi=None, frame_prefix=None):
        """
        Setup for writing the movie file.

        Parameters
        ----------
        fig : `~matplotlib.figure.Figure`
            The figure to grab the rendered frames from.
        outfile : str
            The filename of the resulting movie file.
        dpi : float, default: ``fig.dpi``
            The dpi of the output file. This, with the figure size,
            controls the size in pixels of the resulting movie file.
        frame_prefix : str, optional
            The filename prefix to use for temporary files.  If *None* (the
            default), files are written to a temporary directory which is
            deleted by `finish`; if not *None*, no temporary files are
            deleted.
        """
        # Check that path is valid
        Path(outfile).parent.resolve(strict=True)
        self.fig = fig
        self.outfile = outfile
        if dpi is None:
            dpi = self.fig.dpi
        self.dpi = dpi
        self._adjust_frame_size()

        if frame_prefix is None:
            self._tmpdir = TemporaryDirectory()
            self.temp_prefix = str(Path(self._tmpdir.name, 'tmp'))
        else:
            self._tmpdir = None
            self.temp_prefix = frame_prefix
        self._frame_counter = 0  # used for generating sequential file names
        self._temp_paths = list()
        self.fname_format_str = '%s%%07d.%s'

    def __del__(self):
        if hasattr(self, '_tmpdir') and self._tmpdir:
            self._tmpdir.cleanup()

    @property
    def frame_format(self):
        """
        Format (png, jpeg, etc.) to use for saving the frames, which can be
        decided by the individual subclasses.
        """
        return self._frame_format

    @frame_format.setter
    def frame_format(self, frame_format):
        if frame_format in self.supported_formats:
            self._frame_format = frame_format
        else:
            _api.warn_external(
                f"Ignoring file format {frame_format!r} which is not "
                f"supported by {type(self).__name__}; using "
                f"{self.supported_formats[0]} instead.")
            self._frame_format = self.supported_formats[0]

    def _base_temp_name(self):
        # Generates a template name (without number) given the frame format
        # for extension and the prefix.
        return self.fname_format_str % (self.temp_prefix, self.frame_format)

    def grab_frame(self, **savefig_kwargs):
        # docstring inherited
        # Creates a filename for saving using basename and counter.
        _validate_grabframe_kwargs(savefig_kwargs)
        path = Path(self._base_temp_name() % self._frame_counter)
        self._temp_paths.append(path)  # Record the filename for later use.
        self._frame_counter += 1  # Ensures each created name is unique.
        _log.debug('FileMovieWriter.grab_frame: Grabbing frame %d to path=%s',
                   self._frame_counter, path)
        with open(path, 'wb') as sink:  # Save figure to the sink.
            self.fig.savefig(sink, format=self.frame_format, dpi=self.dpi,
                             **savefig_kwargs)

    def finish(self):
        # Call run here now that all frame grabbing is done. All temp files
        # are available to be assembled.
        try:
            self._run()
            super().finish()
        finally:
            if self._tmpdir:
                _log.debug(
                    'MovieWriter: clearing temporary path=%s', self._tmpdir
                )
                self._tmpdir.cleanup()


@writers.register('pillow')
class PillowWriter(AbstractMovieWriter):
    def _supports_transparency(self):
        return True

    @classmethod
    def isAvailable(cls):
        return True

    def setup(self, fig, outfile, dpi=None):
        super().setup(fig, outfile, dpi=dpi)
        self._frames = []

    def grab_frame(self, **savefig_kwargs):
        _validate_grabframe_kwargs(savefig_kwargs)
        buf = BytesIO()
        self.fig.savefig(
            buf, **{**savefig_kwargs, "format": "rgba", "dpi": self.dpi})
        im = Image.frombuffer(
            "RGBA", self.frame_size, buf.getbuffer(), "raw", "RGBA", 0, 1)
        if im.getextrema()[3][0] < 255:
            # This frame has transparency, so we'll just add it as is.
            self._frames.append(im)
        else:
            # Without transparency, we switch to RGB mode, which converts to P mode a
            # little better if needed (specifically, this helps with GIF output.)
            self._frames.append(im.convert("RGB"))

    def finish(self):
        self._frames[0].save(
            self.outfile, save_all=True, append_images=self._frames[1:],
            duration=int(1000 / self.fps), loop=0)


# Base class of ffmpeg information. Has the config keys and the common set
# of arguments that controls the *output* side of things.
class FFMpegBase:
    """
    Mixin class for FFMpeg output.

    This is a base class for the concrete `FFMpegWriter` and `FFMpegFileWriter`
    classes.
    """

    _exec_key = 'animation.ffmpeg_path'
    _args_key = 'animation.ffmpeg_args'

    def _supports_transparency(self):
        suffix = Path(self.outfile).suffix
        if suffix in {'.apng', '.avif', '.gif', '.webm', '.webp'}:
            return True
        # This list was found by going through `ffmpeg -codecs` for video encoders,
        # running them with _support_transparency() forced to True, and checking that
        # the "Pixel format" in Kdenlive included alpha. Note this is not a guarantee
        # that transparency will work; you may also need to pass `-pix_fmt`, but we
        # trust the user has done so if they are asking for these formats.
        return self.codec in {
            'apng', 'avrp', 'bmp', 'cfhd', 'dpx', 'ffv1', 'ffvhuff', 'gif', 'huffyuv',
            'jpeg2000', 'ljpeg', 'png', 'prores', 'prores_aw', 'prores_ks', 'qtrle',
            'rawvideo', 'targa', 'tiff', 'utvideo', 'v408', }

    @property
    def output_args(self):
        args = []
        suffix = Path(self.outfile).suffix
        if suffix in {'.apng', '.avif', '.gif', '.webm', '.webp'}:
            self.codec = suffix[1:]
        else:
            args.extend(['-vcodec', self.codec])
        extra_args = (self.extra_args if self.extra_args is not None
                      else mpl.rcParams[self._args_key])
        # For h264, the default format is yuv444p, which is not compatible
        # with quicktime (and others). Specifying yuv420p fixes playback on
        # iOS, as well as HTML5 video in firefox and safari (on both Windows and
        # macOS). Also fixes internet explorer. This is as of 2015/10/29.
        if self.codec == 'h264' and '-pix_fmt' not in extra_args:
            args.extend(['-pix_fmt', 'yuv420p'])
        # For GIF, we're telling FFmpeg to split the video stream, to generate
        # a palette, and then use it for encoding.
        elif self.codec == 'gif' and '-filter_complex' not in extra_args:
            args.extend(['-filter_complex',
                         'split [a][b];[a] palettegen [p];[b][p] paletteuse'])
        # For AVIF, we're telling FFmpeg to split the video stream, extract the alpha,
        # in order to place it in a secondary stream, as needed by AVIF-in-FFmpeg.
        elif self.codec == 'avif' and '-filter_complex' not in extra_args:
            args.extend(['-filter_complex',
                         'split [rgb][rgba]; [rgba] alphaextract [alpha]',
                         '-map', '[rgb]', '-map', '[alpha]'])
        if self.bitrate > 0:
            args.extend(['-b', '%dk' % self.bitrate])  # %dk: bitrate in kbps.
        for k, v in self.metadata.items():
            args.extend(['-metadata', f'{k}={v}'])
        args.extend(extra_args)

        return args + ['-y', self.outfile]


# Combine FFMpeg options with pipe-based writing
@writers.register('ffmpeg')
class FFMpegWriter(FFMpegBase, MovieWriter):
    """
    Pipe-based ffmpeg writer.

    Frames are streamed directly to ffmpeg via a pipe and written in a single pass.

    This effectively works as a slideshow input to ffmpeg with the fps passed as
    ``-framerate``, so see also `their notes on frame rates`_ for further details.

    .. _their notes on frame rates: https://trac.ffmpeg.org/wiki/Slideshow#Framerates
    """
    def _args(self):
        # Returns the command line parameters for subprocess to use
        # ffmpeg to create a movie using a pipe.
        args = [self.bin_path(), '-f', 'rawvideo', '-vcodec', 'rawvideo',
                '-s', '%dx%d' % self.frame_size, '-pix_fmt', self.frame_format,
                '-framerate', str(self.fps)]
        # Logging is quieted because subprocess.PIPE has limited buffer size.
        # If you have a lot of frames in your animation and set logging to
        # DEBUG, you will have a buffer overrun.
        if _log.getEffectiveLevel() > logging.DEBUG:
            args += ['-loglevel', 'error']
        args += ['-i', 'pipe:'] + self.output_args
        return args


# Combine FFMpeg options with temp file-based writing
@writers.register('ffmpeg_file')
class FFMpegFileWriter(FFMpegBase, FileMovieWriter):
    """
    File-based ffmpeg writer.

    Frames are written to temporary files on disk and then stitched together at the end.

    This effectively works as a slideshow input to ffmpeg with the fps passed as
    ``-framerate``, so see also `their notes on frame rates`_ for further details.

    .. _their notes on frame rates: https://trac.ffmpeg.org/wiki/Slideshow#Framerates
    """
    supported_formats = ['png', 'jpeg', 'tiff', 'raw', 'rgba']

    def _args(self):
        # Returns the command line parameters for subprocess to use
        # ffmpeg to create a movie using a collection of temp images
        args = []
        # For raw frames, we need to explicitly tell ffmpeg the metadata.
        if self.frame_format in {'raw', 'rgba'}:
            args += [
                '-f', 'image2', '-vcodec', 'rawvideo',
                '-video_size', '%dx%d' % self.frame_size,
                '-pixel_format', 'rgba',
            ]
        args += ['-framerate', str(self.fps), '-i', self._base_temp_name()]
        if not self._tmpdir:
            args += ['-frames:v', str(self._frame_counter)]
        # Logging is quieted because subprocess.PIPE has limited buffer size.
        # If you have a lot of frames in your animation and set logging to
        # DEBUG, you will have a buffer overrun.
        if _log.getEffectiveLevel() > logging.DEBUG:
            args += ['-loglevel', 'error']
        return [self.bin_path(), *args, *self.output_args]


# Base class for animated GIFs with ImageMagick
class ImageMagickBase:
    """
    Mixin class for ImageMagick output.

    This is a base class for the concrete `ImageMagickWriter` and
    `ImageMagickFileWriter` classes, which define an ``input_names`` attribute
    (or property) specifying the input names passed to ImageMagick.
    """

    _exec_key = 'animation.convert_path'
    _args_key = 'animation.convert_args'

    def _supports_transparency(self):
        suffix = Path(self.outfile).suffix
        return suffix in {'.apng', '.avif', '.gif', '.webm', '.webp'}

    def _args(self):
        # ImageMagick does not recognize "raw".
        fmt = "rgba" if self.frame_format == "raw" else self.frame_format
        extra_args = (self.extra_args if self.extra_args is not None
                      else mpl.rcParams[self._args_key])
        return [
            self.bin_path(),
            "-size", "%ix%i" % self.frame_size,
            "-depth", "8",
            "-delay", str(100 / self.fps),
            "-loop", "0",
            f"{fmt}:{self.input_names}",
            *extra_args,
            self.outfile,
        ]

    @classmethod
    def bin_path(cls):
        binpath = super().bin_path()
        if binpath == 'convert':
            binpath = mpl._get_executable_info('magick').executable
        return binpath

    @classmethod
    def isAvailable(cls):
        try:
            return super().isAvailable()
        except mpl.ExecutableNotFoundError as _enf:
            # May be raised by get_executable_info.
            _log.debug('ImageMagick unavailable due to: %s', _enf)
            return False


# Combine ImageMagick options with pipe-based writing
@writers.register('imagemagick')
class ImageMagickWriter(ImageMagickBase, MovieWriter):
    """
    Pipe-based animated gif writer.

    Frames are streamed directly to ImageMagick via a pipe and written
    in a single pass.
    """

    input_names = "-"  # stdin


# Combine ImageMagick options with temp file-based writing
@writers.register('imagemagick_file')
class ImageMagickFileWriter(ImageMagickBase, FileMovieWriter):
    """
    File-based animated gif writer.

    Frames are written to temporary files on disk and then stitched
    together at the end.
    """

    supported_formats = ['png', 'jpeg', 'tiff', 'raw', 'rgba']
    input_names = property(
        lambda self: f'{self.temp_prefix}*.{self.frame_format}')


# Taken directly from jakevdp's JSAnimation package at
# http://github.com/jakevdp/JSAnimation
def _included_frames(frame_count, frame_format, frame_dir):
    return INCLUDED_FRAMES.format(Nframes=frame_count,
                                  frame_dir=frame_dir,
                                  frame_format=frame_format)


def _embedded_frames(frame_list, frame_format):
    """frame_list should be a list of base64-encoded png files"""
    if frame_format == 'svg':
        # Fix MIME type for svg
        frame_format = 'svg+xml'
    template = '  frames[{0}] = "data:image/{1};base64,{2}"\n'
    return "\n" + "".join(
        template.format(i, frame_format, frame_data.replace('\n', '\\\n'))
        for i, frame_data in enumerate(frame_list))


@writers.register('html')
class HTMLWriter(FileMovieWriter):
    """Writer for JavaScript-based HTML movies."""

    supported_formats = ['png', 'jpeg', 'tiff', 'svg']

    @classmethod
    def isAvailable(cls):
        return True

    def __init__(self, fps=30, codec=None, bitrate=None, extra_args=None,
                 metadata=None, embed_frames=False, default_mode='loop',
                 embed_limit=None):

        if extra_args:
            _log.warning("HTMLWriter ignores 'extra_args'")
        extra_args = ()  # Don't lookup nonexistent rcParam[args_key].
        self.embed_frames = embed_frames
        self.default_mode = default_mode.lower()
        _api.check_in_list(['loop', 'once', 'reflect'],
                           default_mode=self.default_mode)

        # Save embed limit, which is given in MB
        self._bytes_limit = mpl._val_or_rc(embed_limit, 'animation.embed_limit')
        # Convert from MB to bytes
        self._bytes_limit *= 1024 * 1024

        super().__init__(fps, codec, bitrate, extra_args, metadata)

    def setup(self, fig, outfile, dpi=None, frame_dir=None):
        outfile = Path(outfile)
        _api.check_in_list(['.html', '.htm'], outfile_extension=outfile.suffix)

        self._saved_frames = []
        self._total_bytes = 0
        self._hit_limit = False

        if not self.embed_frames:
            if frame_dir is None:
                frame_dir = outfile.with_name(outfile.stem + '_frames')
            frame_dir.mkdir(parents=True, exist_ok=True)
            frame_prefix = frame_dir / 'frame'
        else:
            frame_prefix = None

        super().setup(fig, outfile, dpi, frame_prefix)
        self._clear_temp = False

    def grab_frame(self, **savefig_kwargs):
        _validate_grabframe_kwargs(savefig_kwargs)
        if self.embed_frames:
            # Just stop processing if we hit the limit
            if self._hit_limit:
                return
            f = BytesIO()
            self.fig.savefig(f, format=self.frame_format,
                             dpi=self.dpi, **savefig_kwargs)
            imgdata64 = base64.encodebytes(f.getvalue()).decode('ascii')
            self._total_bytes += len(imgdata64)
            if self._total_bytes >= self._bytes_limit:
                _log.warning(
                    "Animation size has reached %s bytes, exceeding the limit "
                    "of %s. If you're sure you want a larger animation "
                    "embedded, set the animation.embed_limit rc parameter to "
                    "a larger value (in MB). This and further frames will be "
                    "dropped.", self._total_bytes, self._bytes_limit)
                self._hit_limit = True
            else:
                self._saved_frames.append(imgdata64)
        else:
            return super().grab_frame(**savefig_kwargs)

    def finish(self):
        # save the frames to an html file
        if self.embed_frames:
            fill_frames = _embedded_frames(self._saved_frames,
                                           self.frame_format)
            frame_count = len(self._saved_frames)
        else:
            # temp names is filled by FileMovieWriter
            frame_count = len(self._temp_paths)
            fill_frames = _included_frames(
                frame_count, self.frame_format,
                self._temp_paths[0].parent.relative_to(self.outfile.parent))
        mode_dict = dict(once_checked='',
                         loop_checked='',
                         reflect_checked='')
        mode_dict[self.default_mode + '_checked'] = 'checked'

        interval = 1000 // self.fps

        with open(self.outfile, 'w') as of:
            of.write(JS_INCLUDE + STYLE_INCLUDE)
            of.write(DISPLAY_TEMPLATE.format(id=uuid.uuid4().hex,
                                             Nframes=frame_count,
                                             fill_frames=fill_frames,
                                             interval=interval,
                                             **mode_dict))

        # Duplicate the temporary file clean up logic from
        # FileMovieWriter.finish.  We cannot call the inherited version of
        # finish because it assumes that there is a subprocess that we either
        # need to call to merge many frames together or that there is a
        # subprocess call that we need to clean up.
        if self._tmpdir:
            _log.debug('MovieWriter: clearing temporary path=%s', self._tmpdir)
            self._tmpdir.cleanup()


class Animation:
    """
    A base class for Animations.

    This class is not usable as is, and should be subclassed to provide needed
    behavior.

    .. note::

        You must store the created Animation in a variable that lives as long
        as the animation should run. Otherwise, the Animation object will be
        garbage-collected and the animation stops.

    Parameters
    ----------
    fig : `~matplotlib.figure.Figure`
        The figure object used to get needed events, such as draw or resize.

    event_source : object, optional
        A class that can run a callback when desired events
        are generated, as well as be stopped and started.

        Examples include timers (see `TimedAnimation`) and file
        system notifications.

    blit : bool, default: False
        Whether blitting is used to optimize drawing.  If the backend does not
        support blitting, then this parameter has no effect.

    See Also
    --------
    FuncAnimation,  ArtistAnimation
    """

    def __init__(self, fig, event_source=None, blit=False):
        self._draw_was_started = False

        self._fig = fig
        # Disables blitting for backends that don't support it.  This
        # allows users to request it if available, but still have a
        # fallback that works if it is not.
        self._blit = blit and fig.canvas.supports_blit

        # These are the basics of the animation.  The frame sequence represents
        # information for each frame of the animation and depends on how the
        # drawing is handled by the subclasses. The event source fires events
        # that cause the frame sequence to be iterated.
        self.frame_seq = self.new_frame_seq()
        self.event_source = event_source

        # Instead of starting the event source now, we connect to the figure's
        # draw_event, so that we only start once the figure has been drawn.
        self._first_draw_id = fig.canvas.mpl_connect('draw_event', self._start)

        # Connect to the figure's close_event so that we don't continue to
        # fire events and try to draw to a deleted figure.
        self._close_id = self._fig.canvas.mpl_connect('close_event',
                                                      self._stop)
        if self._blit:
            self._setup_blit()

    def __del__(self):
        if not getattr(self, '_draw_was_started', True):
            warnings.warn(
                'Animation was deleted without rendering anything. This is '
                'most likely not intended. To prevent deletion, assign the '
                'Animation to a variable, e.g. `anim`, that exists until you '
                'output the Animation using `plt.show()` or '
                '`anim.save()`.'
            )

    def _start(self, *args):
        """
        Starts interactive animation. Adds the draw frame command to the GUI
        handler, calls show to start the event loop.
        """
        # Do not start the event source if saving() it.
        if self._fig.canvas.is_saving():
            return
        # First disconnect our draw event handler
        self._fig.canvas.mpl_disconnect(self._first_draw_id)

        # Now do any initial draw
        self._init_draw()

        # Add our callback for stepping the animation and
        # actually start the event_source.
        self.event_source.add_callback(self._step)
        self.event_source.start()

    def _stop(self, *args):
        # On stop we disconnect all of our events.
        if self._blit:
            self._fig.canvas.mpl_disconnect(self._resize_id)
        self._fig.canvas.mpl_disconnect(self._close_id)
        self.event_source.remove_callback(self._step)
        self.event_source = None

    def save(self, filename, writer=None, fps=None, dpi=None, codec=None,
             bitrate=None, extra_args=None, metadata=None, extra_anim=None,
             savefig_kwargs=None, *, progress_callback=None):
        """
        Save the animation as a movie file by drawing every frame.

        Parameters
        ----------
        filename : str
            The output filename, e.g., :file:`mymovie.mp4`.

        writer : `MovieWriter` or str, default: :rc:`animation.writer`
            A `MovieWriter` instance to use or a key that identifies a
            class to use, such as 'ffmpeg'.

        fps : int, optional
            Movie frame rate (per second).  If not set, the frame rate from the
            animation's frame interval.

        dpi : float, default: :rc:`savefig.dpi`
            Controls the dots per inch for the movie frames.  Together with
            the figure's size in inches, this controls the size of the movie.

        codec : str, default: :rc:`animation.codec`.
            The video codec to use.  Not all codecs are supported by a given
            `MovieWriter`.

        bitrate : int, default: :rc:`animation.bitrate`
            The bitrate of the movie, in kilobits per second.  Higher values
            means higher quality movies, but increase the file size.  A value
            of -1 lets the underlying movie encoder select the bitrate.

        extra_args : list of str or None, optional
            Extra command-line arguments passed to the underlying movie encoder. These
            arguments are passed last to the encoder, just before the output filename.
            The default, None, means to use :rc:`animation.[name-of-encoder]_args` for
            the builtin writers.

        metadata : dict[str, str], default: {}
            Dictionary of keys and values for metadata to include in
            the output file. Some keys that may be of use include:
            title, artist, genre, subject, copyright, srcform, comment.

        extra_anim : list, default: []
            Additional `Animation` objects that should be included
            in the saved movie file. These need to be from the same
            `.Figure` instance. Also, animation frames will
            just be simply combined, so there should be a 1:1 correspondence
            between the frames from the different animations.

        savefig_kwargs : dict, default: {}
            Keyword arguments passed to each `~.Figure.savefig` call used to
            save the individual frames.

        progress_callback : function, optional
            A callback function that will be called for every frame to notify
            the saving progress. It must have the signature ::

                def func(current_frame: int, total_frames: int) -> Any

            where *current_frame* is the current frame number and *total_frames* is the
            total number of frames to be saved. *total_frames* is set to None, if the
            total number of frames cannot be determined. Return values may exist but are
            ignored.

            Example code to write the progress to stdout::

                progress_callback = lambda i, n: print(f'Saving frame {i}/{n}')

        Notes
        -----
        *fps*, *codec*, *bitrate*, *extra_args* and *metadata* are used to
        construct a `.MovieWriter` instance and can only be passed if
        *writer* is a string.  If they are passed as non-*None* and *writer*
        is a `.MovieWriter`, a `RuntimeError` will be raised.
        """

        all_anim = [self]
        if extra_anim is not None:
            all_anim.extend(anim for anim in extra_anim
                            if anim._fig is self._fig)

        # Disable "Animation was deleted without rendering" warning.
        for anim in all_anim:
            anim._draw_was_started = True

        if writer is None:
            writer = mpl.rcParams['animation.writer']
        elif (not isinstance(writer, str) and
              any(arg is not None
                  for arg in (fps, codec, bitrate, extra_args, metadata))):
            raise RuntimeError('Passing in values for arguments '
                               'fps, codec, bitrate, extra_args, or metadata '
                               'is not supported when writer is an existing '
                               'MovieWriter instance. These should instead be '
                               'passed as arguments when creating the '
                               'MovieWriter instance.')

        if savefig_kwargs is None:
            savefig_kwargs = {}
        else:
            # we are going to mutate this below
            savefig_kwargs = dict(savefig_kwargs)

        if fps is None and hasattr(self, '_interval'):
            # Convert interval in ms to frames per second
            fps = 1000. / self._interval

        # Reuse the savefig DPI for ours if none is given.
        dpi = mpl._val_or_rc(dpi, 'savefig.dpi')
        if dpi == 'figure':
            dpi = self._fig.dpi

        writer_kwargs = {}
        if codec is not None:
            writer_kwargs['codec'] = codec
        if bitrate is not None:
            writer_kwargs['bitrate'] = bitrate
        if extra_args is not None:
            writer_kwargs['extra_args'] = extra_args
        if metadata is not None:
            writer_kwargs['metadata'] = metadata

        # If we have the name of a writer, instantiate an instance of the
        # registered class.
        if isinstance(writer, str):
            try:
                writer_cls = writers[writer]
            except RuntimeError:  # Raised if not available.
                writer_cls = PillowWriter  # Always available.
                _log.warning("MovieWriter %s unavailable; using Pillow "
                             "instead.", writer)
            writer = writer_cls(fps, **writer_kwargs)
        _log.info('Animation.save using %s', type(writer))

        if 'bbox_inches' in savefig_kwargs:
            _log.warning("Warning: discarding the 'bbox_inches' argument in "
                         "'savefig_kwargs' as it may cause frame size "
                         "to vary, which is inappropriate for animation.")
            savefig_kwargs.pop('bbox_inches')

        # Create a new sequence of frames for saved data. This is different
        # from new_frame_seq() to give the ability to save 'live' generated
        # frame information to be saved later.
        # TODO: Right now, after closing the figure, saving a movie won't work
        # since GUI widgets are gone. Either need to remove extra code to
        # allow for this non-existent use case or find a way to make it work.

        def _pre_composite_to_white(color):
            r, g, b, a = mcolors.to_rgba(color)
            return a * np.array([r, g, b]) + 1 - a

        # canvas._is_saving = True makes the draw_event animation-starting
        # callback a no-op; canvas.manager = None prevents resizing the GUI
        # widget (both are likewise done in savefig()).
        with (writer.saving(self._fig, filename, dpi),
              cbook._setattr_cm(self._fig.canvas, _is_saving=True, manager=None)):
            if not writer._supports_transparency():
                facecolor = savefig_kwargs.get('facecolor',
                                               mpl.rcParams['savefig.facecolor'])
                if facecolor == 'auto':
                    facecolor = self._fig.get_facecolor()
                savefig_kwargs['facecolor'] = _pre_composite_to_white(facecolor)
                savefig_kwargs['transparent'] = False   # just to be safe!

            for anim in all_anim:
                anim._init_draw()  # Clear the initial frame
            frame_number = 0
            # TODO: Currently only FuncAnimation has a save_count
            #       attribute. Can we generalize this to all Animations?
            save_count_list = [getattr(a, '_save_count', None)
                               for a in all_anim]
            if None in save_count_list:
                total_frames = None
            else:
                total_frames = sum(save_count_list)
            for data in zip(*[a.new_saved_frame_seq() for a in all_anim]):
                for anim, d in zip(all_anim, data):
                    # TODO: See if turning off blit is really necessary
                    anim._draw_next_frame(d, blit=False)
                    if progress_callback is not None:
                        progress_callback(frame_number, total_frames)
                        frame_number += 1
                writer.grab_frame(**savefig_kwargs)

    def _step(self, *args):
        """
        Handler for getting events. By default, gets the next frame in the
        sequence and hands the data off to be drawn.
        """
        # Returns True to indicate that the event source should continue to
        # call _step, until the frame sequence reaches the end of iteration,
        # at which point False will be returned.
        try:
            framedata = next(self.frame_seq)
            self._draw_next_frame(framedata, self._blit)
            return True
        except StopIteration:
            return False

    def new_frame_seq(self):
        """Return a new sequence of frame information."""
        # Default implementation is just an iterator over self._framedata
        return iter(self._framedata)

    def new_saved_frame_seq(self):
        """Return a new sequence of saved/cached frame information."""
        # Default is the same as the regular frame sequence
        return self.new_frame_seq()

    def _draw_next_frame(self, framedata, blit):
        # Breaks down the drawing of the next frame into steps of pre- and
        # post- draw, as well as the drawing of the frame itself.
        self._pre_draw(framedata, blit)
        self._draw_frame(framedata)
        self._post_draw(framedata, blit)

    def _init_draw(self):
        # Initial draw to clear the frame. Also used by the blitting code
        # when a clean base is required.
        self._draw_was_started = True

    def _pre_draw(self, framedata, blit):
        # Perform any cleaning or whatnot before the drawing of the frame.
        # This default implementation allows blit to clear the frame.
        if blit:
            self._blit_clear(self._drawn_artists)

    def _draw_frame(self, framedata):
        # Performs actual drawing of the frame.
        raise NotImplementedError('Needs to be implemented by subclasses to'
                                  ' actually make an animation.')

    def _post_draw(self, framedata, blit):
        # After the frame is rendered, this handles the actual flushing of
        # the draw, which can be a direct draw_idle() or make use of the
        # blitting.
        if blit and self._drawn_artists:
            self._blit_draw(self._drawn_artists)
        else:
            self._fig.canvas.draw_idle()

    # The rest of the code in this class is to facilitate easy blitting
    def _blit_draw(self, artists):
        # Handles blitted drawing, which renders only the artists given instead
        # of the entire figure.
        updated_ax = {a.axes for a in artists}
        # Enumerate artists to cache Axes backgrounds. We do not draw
        # artists yet to not cache foreground from plots with shared Axes
        for ax in updated_ax:
            # If we haven't cached the background for the current view of this
            # Axes object, do so now. This might not always be reliable, but
            # it's an attempt to automate the process.
            cur_view = ax._get_view()
            view, bg = self._blit_cache.get(ax, (object(), None))
            if cur_view != view:
                self._blit_cache[ax] = (
                    cur_view, ax.figure.canvas.copy_from_bbox(ax.bbox))
        # Make a separate pass to draw foreground.
        for a in artists:
            a.axes.draw_artist(a)
        # After rendering all the needed artists, blit each Axes individually.
        for ax in updated_ax:
            ax.figure.canvas.blit(ax.bbox)

    def _blit_clear(self, artists):
        # Get a list of the Axes that need clearing from the artists that
        # have been drawn. Grab the appropriate saved background from the
        # cache and restore.
        axes = {a.axes for a in artists}
        for ax in axes:
            try:
                view, bg = self._blit_cache[ax]
            except KeyError:
                continue
            if ax._get_view() == view:
                ax.figure.canvas.restore_region(bg)
            else:
                self._blit_cache.pop(ax)

    def _setup_blit(self):
        # Setting up the blit requires: a cache of the background for the Axes
        self._blit_cache = dict()
        self._drawn_artists = []
        # _post_draw needs to be called first to initialize the renderer
        self._post_draw(None, self._blit)
        # Then we need to clear the Frame for the initial draw
        # This is typically handled in _on_resize because QT and Tk
        # emit a resize event on launch, but the macosx backend does not,
        # thus we force it here for everyone for consistency
        self._init_draw()
        # Connect to future resize events
        self._resize_id = self._fig.canvas.mpl_connect('resize_event',
                                                       self._on_resize)

    def _on_resize(self, event):
        # On resize, we need to disable the resize event handling so we don't
        # get too many events. Also stop the animation events, so that
        # we're paused. Reset the cache and re-init. Set up an event handler
        # to catch once the draw has actually taken place.
        self._fig.canvas.mpl_disconnect(self._resize_id)
        self.event_source.stop()
        self._blit_cache.clear()
        self._init_draw()
        self._resize_id = self._fig.canvas.mpl_connect('draw_event',
                                                       self._end_redraw)

    def _end_redraw(self, event):
        # Now that the redraw has happened, do the post draw flushing and
        # blit handling. Then re-enable all of the original events.
        self._post_draw(None, False)
        self.event_source.start()
        self._fig.canvas.mpl_disconnect(self._resize_id)
        self._resize_id = self._fig.canvas.mpl_connect('resize_event',
                                                       self._on_resize)

    def to_html5_video(self, embed_limit=None):
        """
        Convert the animation to an HTML5 ``<video>`` tag.

        This saves the animation as an h264 video, encoded in base64
        directly into the HTML5 video tag. This respects :rc:`animation.writer`
        and :rc:`animation.bitrate`. This also makes use of the
        *interval* to control the speed, and uses the *repeat*
        parameter to decide whether to loop.

        Parameters
        ----------
        embed_limit : float, optional
            Limit, in MB, of the returned animation. No animation is created
            if the limit is exceeded.
            Defaults to :rc:`animation.embed_limit` = 20.0.

        Returns
        -------
        str
            An HTML5 video tag with the animation embedded as base64 encoded
            h264 video.
            If the *embed_limit* is exceeded, this returns the string
            "Video too large to embed."
        """
        VIDEO_TAG = r'''<video {size} {options}>
  <source type="video/mp4" src="data:video/mp4;base64,{video}">
  Your browser does not support the video tag.
</video>'''
        # Cache the rendering of the video as HTML
        if not hasattr(self, '_base64_video'):
            # Save embed limit, which is given in MB
            embed_limit = mpl._val_or_rc(embed_limit, 'animation.embed_limit')

            # Convert from MB to bytes
            embed_limit *= 1024 * 1024

            # Can't open a NamedTemporaryFile twice on Windows, so use a
            # TemporaryDirectory instead.
            with TemporaryDirectory() as tmpdir:
                path = Path(tmpdir, "temp.m4v")
                # We create a writer manually so that we can get the
                # appropriate size for the tag
                Writer = writers[mpl.rcParams['animation.writer']]
                writer = Writer(codec='h264',
                                bitrate=mpl.rcParams['animation.bitrate'],
                                fps=1000. / self._interval)
                self.save(str(path), writer=writer)
                # Now open and base64 encode.
                vid64 = base64.encodebytes(path.read_bytes())

            vid_len = len(vid64)
            if vid_len >= embed_limit:
                _log.warning(
                    "Animation movie is %s bytes, exceeding the limit of %s. "
                    "If you're sure you want a large animation embedded, set "
                    "the animation.embed_limit rc parameter to a larger value "
                    "(in MB).", vid_len, embed_limit)
            else:
                self._base64_video = vid64.decode('ascii')
                self._video_size = 'width="{}" height="{}"'.format(
                        *writer.frame_size)

        # If we exceeded the size, this attribute won't exist
        if hasattr(self, '_base64_video'):
            # Default HTML5 options are to autoplay and display video controls
            options = ['controls', 'autoplay']

            # If we're set to repeat, make it loop
            if getattr(self, '_repeat', False):
                options.append('loop')

            return VIDEO_TAG.format(video=self._base64_video,
                                    size=self._video_size,
                                    options=' '.join(options))
        else:
            return 'Video too large to embed.'

    def to_jshtml(self, fps=None, embed_frames=True, default_mode=None):
        """
        Generate HTML representation of the animation.

        Parameters
        ----------
        fps : int, optional
            Movie frame rate (per second). If not set, the frame rate from
            the animation's frame interval.
        embed_frames : bool, optional
        default_mode : str, optional
            What to do when the animation ends. Must be one of ``{'loop',
            'once', 'reflect'}``. Defaults to ``'loop'`` if the *repeat*
            parameter is True, otherwise ``'once'``.

        Returns
        -------
        str
            An HTML representation of the animation embedded as a js object as
            produced with the `.HTMLWriter`.
        """
        if fps is None and hasattr(self, '_interval'):
            # Convert interval in ms to frames per second
            fps = 1000 / self._interval

        # If we're not given a default mode, choose one base on the value of
        # the _repeat attribute
        if default_mode is None:
            default_mode = 'loop' if getattr(self, '_repeat',
                                             False) else 'once'

        if not hasattr(self, "_html_representation"):
            # Can't open a NamedTemporaryFile twice on Windows, so use a
            # TemporaryDirectory instead.
            with TemporaryDirectory() as tmpdir:
                path = Path(tmpdir, "temp.html")
                writer = HTMLWriter(fps=fps,
                                    embed_frames=embed_frames,
                                    default_mode=default_mode)
                self.save(str(path), writer=writer)
                self._html_representation = path.read_text()

        return self._html_representation

    def _repr_html_(self):
        """IPython display hook for rendering."""
        fmt = mpl.rcParams['animation.html']
        if fmt == 'html5':
            return self.to_html5_video()
        elif fmt == 'jshtml':
            return self.to_jshtml()

    def pause(self):
        """Pause the animation."""
        self.event_source.stop()
        if self._blit:
            for artist in self._drawn_artists:
                artist.set_animated(False)

    def resume(self):
        """Resume the animation."""
        self.event_source.start()
        if self._blit:
            for artist in self._drawn_artists:
                artist.set_animated(True)


class TimedAnimation(Animation):
    """
    `Animation` subclass for time-based animation.

    A new frame is drawn every *interval* milliseconds.

    .. note::

        You must store the created Animation in a variable that lives as long
        as the animation should run. Otherwise, the Animation object will be
        garbage-collected and the animation stops.

    Parameters
    ----------
    fig : `~matplotlib.figure.Figure`
        The figure object used to get needed events, such as draw or resize.
    interval : int, default: 200
        Delay between frames in milliseconds.
    repeat_delay : int, default: 0
        The delay in milliseconds between consecutive animation runs, if
        *repeat* is True.
    repeat : bool, default: True
        Whether the animation repeats when the sequence of frames is completed.
    blit : bool, default: False
        Whether blitting is used to optimize drawing.
    """
    def __init__(self, fig, interval=200, repeat_delay=0, repeat=True,
                 event_source=None, *args, **kwargs):
        self._interval = interval
        # Undocumented support for repeat_delay = None as backcompat.
        self._repeat_delay = repeat_delay if repeat_delay is not None else 0
        self._repeat = repeat
        # If we're not given an event source, create a new timer. This permits
        # sharing timers between animation objects for syncing animations.
        if event_source is None:
            event_source = fig.canvas.new_timer(interval=self._interval)
        super().__init__(fig, event_source=event_source, *args, **kwargs)

    def _step(self, *args):
        """Handler for getting events."""
        # Extends the _step() method for the Animation class.  If
        # Animation._step signals that it reached the end and we want to
        # repeat, we refresh the frame sequence and return True. If
        # _repeat_delay is set, change the event_source's interval to our loop
        # delay and set the callback to one which will then set the interval
        # back.
        still_going = super()._step(*args)
        if not still_going:
            if self._repeat:
                # Restart the draw loop
                self._init_draw()
                self.frame_seq = self.new_frame_seq()
                self.event_source.interval = self._repeat_delay
                return True
            else:
                # We are done with the animation. Call pause to remove
                # animated flags from artists that were using blitting
                self.pause()
                if self._blit:
                    # Remove the resize callback if we were blitting
                    self._fig.canvas.mpl_disconnect(self._resize_id)
                self._fig.canvas.mpl_disconnect(self._close_id)
                self.event_source = None
                return False

        self.event_source.interval = self._interval
        return True


class ArtistAnimation(TimedAnimation):
    """
    `TimedAnimation` subclass that creates an animation by using a fixed
    set of `.Artist` objects.

    Before creating an instance, all plotting should have taken place
    and the relevant artists saved.

    .. note::

        You must store the created Animation in a variable that lives as long
        as the animation should run. Otherwise, the Animation object will be
        garbage-collected and the animation stops.

    Parameters
    ----------
    fig : `~matplotlib.figure.Figure`
        The figure object used to get needed events, such as draw or resize.
    artists : list
        Each list entry is a collection of `.Artist` objects that are made
        visible on the corresponding frame.  Other artists are made invisible.
    interval : int, default: 200
        Delay between frames in milliseconds.
    repeat_delay : int, default: 0
        The delay in milliseconds between consecutive animation runs, if
        *repeat* is True.
    repeat : bool, default: True
        Whether the animation repeats when the sequence of frames is completed.
    blit : bool, default: False
        Whether blitting is used to optimize drawing.
    """

    def __init__(self, fig, artists, *args, **kwargs):
        # Internal list of artists drawn in the most recent frame.
        self._drawn_artists = []

        # Use the list of artists as the framedata, which will be iterated
        # over by the machinery.
        self._framedata = artists
        super().__init__(fig, *args, **kwargs)

    def _init_draw(self):
        super()._init_draw()
        # Make all the artists involved in *any* frame invisible
        figs = set()
        for f in self.new_frame_seq():
            for artist in f:
                artist.set_visible(False)
                artist.set_animated(self._blit)
                # Assemble a list of unique figures that need flushing
                if artist.get_figure() not in figs:
                    figs.add(artist.get_figure())

        # Flush the needed figures
        for fig in figs:
            fig.canvas.draw_idle()

    def _pre_draw(self, framedata, blit):
        """Clears artists from the last frame."""
        if blit:
            # Let blit handle clearing
            self._blit_clear(self._drawn_artists)
        else:
            # Otherwise, make all the artists from the previous frame invisible
            for artist in self._drawn_artists:
                artist.set_visible(False)

    def _draw_frame(self, artists):
        # Save the artists that were passed in as framedata for the other
        # steps (esp. blitting) to use.
        self._drawn_artists = artists

        # Make all the artists from the current frame visible
        for artist in artists:
            artist.set_visible(True)


class FuncAnimation(TimedAnimation):
    """
    `TimedAnimation` subclass that makes an animation by repeatedly calling
    a function *func*.

    .. note::

        You must store the created Animation in a variable that lives as long
        as the animation should run. Otherwise, the Animation object will be
        garbage-collected and the animation stops.

    Parameters
    ----------
    fig : `~matplotlib.figure.Figure`
        The figure object used to get needed events, such as draw or resize.

    func : callable
        The function to call at each frame.  The first argument will
        be the next value in *frames*.   Any additional positional
        arguments can be supplied using `functools.partial` or via the *fargs*
        parameter.

        The required signature is::

            def func(frame, *fargs) -> iterable_of_artists

        It is often more convenient to provide the arguments using
        `functools.partial`. In this way it is also possible to pass keyword
        arguments. To pass a function with both positional and keyword
        arguments, set all arguments as keyword arguments, just leaving the
        *frame* argument unset::

            def func(frame, art, *, y=None):
                ...

            ani = FuncAnimation(fig, partial(func, art=ln, y='foo'))

        If ``blit == True``, *func* must return an iterable of all artists
        that were modified or created. This information is used by the blitting
        algorithm to determine which parts of the figure have to be updated.
        The return value is unused if ``blit == False`` and may be omitted in
        that case.

    frames : iterable, int, generator function, or None, optional
        Source of data to pass *func* and each frame of the animation

        - If an iterable, then simply use the values provided.  If the
          iterable has a length, it will override the *save_count* kwarg.

        - If an integer, then equivalent to passing ``range(frames)``

        - If a generator function, then must have the signature::

             def gen_function() -> obj

        - If *None*, then equivalent to passing ``itertools.count``.

        In all of these cases, the values in *frames* is simply passed through
        to the user-supplied *func* and thus can be of any type.

    init_func : callable, optional
        A function used to draw a clear frame. If not given, the results of
        drawing from the first item in the frames sequence will be used. This
        function will be called once before the first frame.

        The required signature is::

            def init_func() -> iterable_of_artists

        If ``blit == True``, *init_func* must return an iterable of artists
        to be re-drawn. This information is used by the blitting algorithm to
        determine which parts of the figure have to be updated.  The return
        value is unused if ``blit == False`` and may be omitted in that case.

    fargs : tuple or None, optional
        Additional arguments to pass to each call to *func*. Note: the use of
        `functools.partial` is preferred over *fargs*. See *func* for details.

    save_count : int, optional
        Fallback for the number of values from *frames* to cache. This is
        only used if the number of frames cannot be inferred from *frames*,
        i.e. when it's an iterator without length or a generator.

    interval : int, default: 200
        Delay between frames in milliseconds.

    repeat_delay : int, default: 0
        The delay in milliseconds between consecutive animation runs, if
        *repeat* is True.

    repeat : bool, default: True
        Whether the animation repeats when the sequence of frames is completed.

    blit : bool, default: False
        Whether blitting is used to optimize drawing.  Note: when using
        blitting, any animated artists will be drawn according to their zorder;
        however, they will be drawn on top of any previous artists, regardless
        of their zorder.

    cache_frame_data : bool, default: True
        Whether frame data is cached.  Disabling cache might be helpful when
        frames contain large objects.
    """
    def __init__(self, fig, func, frames=None, init_func=None, fargs=None,
                 save_count=None, *, cache_frame_data=True, **kwargs):
        if fargs:
            self._args = fargs
        else:
            self._args = ()
        self._func = func
        self._init_func = init_func

        # Amount of framedata to keep around for saving movies. This is only
        # used if we don't know how many frames there will be: in the case
        # of no generator or in the case of a callable.
        self._save_count = save_count
        # Set up a function that creates a new iterable when needed. If nothing
        # is passed in for frames, just use itertools.count, which will just
        # keep counting from 0. A callable passed in for frames is assumed to
        # be a generator. An iterable will be used as is, and anything else
        # will be treated as a number of frames.
        if frames is None:
            self._iter_gen = itertools.count
        elif callable(frames):
            self._iter_gen = frames
        elif np.iterable(frames):
            if kwargs.get('repeat', True):
                self._tee_from = frames
                def iter_frames(frames=frames):
                    this, self._tee_from = itertools.tee(self._tee_from, 2)
                    yield from this
                self._iter_gen = iter_frames
            else:
                self._iter_gen = lambda: iter(frames)
            if hasattr(frames, '__len__'):
                self._save_count = len(frames)
                if save_count is not None:
                    _api.warn_external(
                        f"You passed in an explicit {save_count=} "
                        "which is being ignored in favor of "
                        f"{len(frames)=}."
                    )
        else:
            self._iter_gen = lambda: iter(range(frames))
            self._save_count = frames
            if save_count is not None:
                _api.warn_external(
                    f"You passed in an explicit {save_count=} which is being "
                    f"ignored in favor of {frames=}."
                )
        if self._save_count is None and cache_frame_data:
            _api.warn_external(
                f"{frames=!r} which we can infer the length of, "
                "did not pass an explicit *save_count* "
                f"and passed {cache_frame_data=}.  To avoid a possibly "
                "unbounded cache, frame data caching has been disabled. "
                "To suppress this warning either pass "
                "`cache_frame_data=False` or `save_count=MAX_FRAMES`."
            )
            cache_frame_data = False

        self._cache_frame_data = cache_frame_data

        # Needs to be initialized so the draw functions work without checking
        self._save_seq = []

        super().__init__(fig, **kwargs)

        # Need to reset the saved seq, since right now it will contain data
        # for a single frame from init, which is not what we want.
        self._save_seq = []

    def new_frame_seq(self):
        # Use the generating function to generate a new frame sequence
        return self._iter_gen()

    def new_saved_frame_seq(self):
        # Generate an iterator for the sequence of saved data. If there are
        # no saved frames, generate a new frame sequence and take the first
        # save_count entries in it.
        if self._save_seq:
            # While iterating we are going to update _save_seq
            # so make a copy to safely iterate over
            self._old_saved_seq = list(self._save_seq)
            return iter(self._old_saved_seq)
        else:
            if self._save_count is None:
                frame_seq = self.new_frame_seq()

                def gen():
                    try:
                        while True:
                            yield next(frame_seq)
                    except StopIteration:
                        pass
                return gen()
            else:
                return itertools.islice(self.new_frame_seq(), self._save_count)

    def _init_draw(self):
        super()._init_draw()
        # Initialize the drawing either using the given init_func or by
        # calling the draw function with the first item of the frame sequence.
        # For blitting, the init_func should return a sequence of modified
        # artists.
        if self._init_func is None:
            try:
                frame_data = next(self.new_frame_seq())
            except StopIteration:
                # we can't start the iteration, it may have already been
                # exhausted by a previous save or just be 0 length.
                # warn and bail.
                warnings.warn(
                    "Can not start iterating the frames for the initial draw. "
                    "This can be caused by passing in a 0 length sequence "
                    "for *frames*.\n\n"
                    "If you passed *frames* as a generator "
                    "it may be exhausted due to a previous display or save."
                )
                return
            self._draw_frame(frame_data)
        else:
            self._drawn_artists = self._init_func()
            if self._blit:
                if self._drawn_artists is None:
                    raise RuntimeError('The init_func must return a '
                                       'sequence of Artist objects.')
                for a in self._drawn_artists:
                    a.set_animated(self._blit)
        self._save_seq = []

    def _draw_frame(self, framedata):
        if self._cache_frame_data:
            # Save the data for potential saving of movies.
            self._save_seq.append(framedata)
            self._save_seq = self._save_seq[-self._save_count:]

        # Call the func with framedata and args. If blitting is desired,
        # func needs to return a sequence of any artists that were modified.
        self._drawn_artists = self._func(framedata, *self._args)

        if self._blit:

            err = RuntimeError('The animation function must return a sequence '
                               'of Artist objects.')
            try:
                # check if a sequence
                iter(self._drawn_artists)
            except TypeError:
                raise err from None

            # check each item if it's artist
            for i in self._drawn_artists:
                if not isinstance(i, mpl.artist.Artist):
                    raise err

            self._drawn_artists = sorted(self._drawn_artists,
                                         key=lambda x: x.get_zorder())

            for a in self._drawn_artists:
                a.set_animated(self._blit)


def _validate_grabframe_kwargs(savefig_kwargs):
    if mpl.rcParams['savefig.bbox'] == 'tight':
        raise ValueError(
            f"{mpl.rcParams['savefig.bbox']=} must not be 'tight' as it "
            "may cause frame size to vary, which is inappropriate for animation."
        )
    for k in ('dpi', 'bbox_inches', 'format'):
        if k in savefig_kwargs:
            raise TypeError(
                f"grab_frame got an unexpected keyword argument {k!r}"
            )