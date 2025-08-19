
# === NexusCore/openenv\Lib\site-packages\matplotlib\figure.py ===
"""
`matplotlib.figure` implements the following classes:

`Figure`
    Top level `~matplotlib.artist.Artist`, which holds all plot elements.
    Many methods are implemented in `FigureBase`.

`SubFigure`
    A logical figure inside a figure, usually added to a figure (or parent `SubFigure`)
    with `Figure.add_subfigure` or `Figure.subfigures` methods.

Figures are typically created using pyplot methods `~.pyplot.figure`,
`~.pyplot.subplots`, and `~.pyplot.subplot_mosaic`.

.. plot::
    :include-source:

    fig, ax = plt.subplots(figsize=(2, 2), facecolor='lightskyblue',
                           layout='constrained')
    fig.suptitle('Figure')
    ax.set_title('Axes', loc='left', fontstyle='oblique', fontsize='medium')

Some situations call for directly instantiating a `~.figure.Figure` class,
usually inside an application of some sort (see :ref:`user_interfaces` for a
list of examples) .  More information about Figures can be found at
:ref:`figure-intro`.
"""

from contextlib import ExitStack
import inspect
import itertools
import functools
import logging
from numbers import Integral
import threading

import numpy as np

import matplotlib as mpl
from matplotlib import _blocking_input, backend_bases, _docstring, projections
from matplotlib.artist import (
    Artist, allow_rasterization, _finalize_rasterization)
from matplotlib.backend_bases import (
    DrawEvent, FigureCanvasBase, NonGuiException, MouseButton, _get_renderer)
import matplotlib._api as _api
import matplotlib.cbook as cbook
import matplotlib.colorbar as cbar
import matplotlib.image as mimage

from matplotlib.axes import Axes
from matplotlib.gridspec import GridSpec, SubplotParams
from matplotlib.layout_engine import (
    ConstrainedLayoutEngine, TightLayoutEngine, LayoutEngine,
    PlaceHolderLayoutEngine
)
import matplotlib.legend as mlegend
from matplotlib.patches import Rectangle
from matplotlib.text import Text
from matplotlib.transforms import (Affine2D, Bbox, BboxTransformTo,
                                   TransformedBbox)

_log = logging.getLogger(__name__)


def _stale_figure_callback(self, val):
    if (fig := self.get_figure(root=False)) is not None:
        fig.stale = val


class _AxesStack:
    """
    Helper class to track Axes in a figure.

    Axes are tracked both in the order in which they have been added
    (``self._axes`` insertion/iteration order) and in the separate "gca" stack
    (which is the index to which they map in the ``self._axes`` dict).
    """

    def __init__(self):
        self._axes = {}  # Mapping of Axes to "gca" order.
        self._counter = itertools.count()

    def as_list(self):
        """List the Axes that have been added to the figure."""
        return [*self._axes]  # This relies on dict preserving order.

    def remove(self, a):
        """Remove the Axes from the stack."""
        self._axes.pop(a)

    def bubble(self, a):
        """Move an Axes, which must already exist in the stack, to the top."""
        if a not in self._axes:
            raise ValueError("Axes has not been added yet")
        self._axes[a] = next(self._counter)

    def add(self, a):
        """Add an Axes to the stack, ignoring it if already present."""
        if a not in self._axes:
            self._axes[a] = next(self._counter)

    def current(self):
        """Return the active Axes, or None if the stack is empty."""
        return max(self._axes, key=self._axes.__getitem__, default=None)

    def __getstate__(self):
        return {
            **vars(self),
            "_counter": max(self._axes.values(), default=0)
        }

    def __setstate__(self, state):
        next_counter = state.pop('_counter')
        vars(self).update(state)
        self._counter = itertools.count(next_counter)


class FigureBase(Artist):
    """
    Base class for `.Figure` and `.SubFigure` containing the methods that add
    artists to the figure or subfigure, create Axes, etc.
    """
    def __init__(self, **kwargs):
        super().__init__()
        # remove the non-figure artist _axes property
        # as it makes no sense for a figure to be _in_ an Axes
        # this is used by the property methods in the artist base class
        # which are over-ridden in this class
        del self._axes

        self._suptitle = None
        self._supxlabel = None
        self._supylabel = None

        # groupers to keep track of x, y labels and title we want to align.
        # see self.align_xlabels, self.align_ylabels,
        # self.align_titles, and axis._get_tick_boxes_siblings
        self._align_label_groups = {
            "x": cbook.Grouper(),
            "y": cbook.Grouper(),
            "title": cbook.Grouper()
        }

        self._localaxes = []  # track all Axes
        self.artists = []
        self.lines = []
        self.patches = []
        self.texts = []
        self.images = []
        self.legends = []
        self.subfigs = []
        self.stale = True
        self.suppressComposite = None
        self.set(**kwargs)

    def _get_draw_artists(self, renderer):
        """Also runs apply_aspect"""
        artists = self.get_children()

        artists.remove(self.patch)
        artists = sorted(
            (artist for artist in artists if not artist.get_animated()),
            key=lambda artist: artist.get_zorder())
        for ax in self._localaxes:
            locator = ax.get_axes_locator()
            ax.apply_aspect(locator(ax, renderer) if locator else None)

            for child in ax.get_children():
                if hasattr(child, 'apply_aspect'):
                    locator = child.get_axes_locator()
                    child.apply_aspect(
                        locator(child, renderer) if locator else None)
        return artists

    def autofmt_xdate(
            self, bottom=0.2, rotation=30, ha='right', which='major'):
        """
        Date ticklabels often overlap, so it is useful to rotate them
        and right align them.  Also, a common use case is a number of
        subplots with shared x-axis where the x-axis is date data.  The
        ticklabels are often long, and it helps to rotate them on the
        bottom subplot and turn them off on other subplots, as well as
        turn off xlabels.

        Parameters
        ----------
        bottom : float, default: 0.2
            The bottom of the subplots for `subplots_adjust`.
        rotation : float, default: 30 degrees
            The rotation angle of the xtick labels in degrees.
        ha : {'left', 'center', 'right'}, default: 'right'
            The horizontal alignment of the xticklabels.
        which : {'major', 'minor', 'both'}, default: 'major'
            Selects which ticklabels to rotate.
        """
        _api.check_in_list(['major', 'minor', 'both'], which=which)
        axes = [ax for ax in self.axes if ax._label != '<colorbar>']
        allsubplots = all(ax.get_subplotspec() for ax in axes)
        if len(axes) == 1:
            for label in self.axes[0].get_xticklabels(which=which):
                label.set_ha(ha)
                label.set_rotation(rotation)
        else:
            if allsubplots:
                for ax in axes:
                    if ax.get_subplotspec().is_last_row():
                        for label in ax.get_xticklabels(which=which):
                            label.set_ha(ha)
                            label.set_rotation(rotation)
                    else:
                        for label in ax.get_xticklabels(which=which):
                            label.set_visible(False)
                        ax.set_xlabel('')

        engine = self.get_layout_engine()
        if allsubplots and (engine is None or engine.adjust_compatible):
            self.subplots_adjust(bottom=bottom)
        self.stale = True

    def get_children(self):
        """Get a list of artists contained in the figure."""
        return [self.patch,
                *self.artists,
                *self._localaxes,
                *self.lines,
                *self.patches,
                *self.texts,
                *self.images,
                *self.legends,
                *self.subfigs]

    def get_figure(self, root=None):
        """
        Return the `.Figure` or `.SubFigure` instance the (Sub)Figure belongs to.

        Parameters
        ----------
        root : bool, default=True
            If False, return the (Sub)Figure this artist is on.  If True,
            return the root Figure for a nested tree of SubFigures.

            .. deprecated:: 3.10

                From version 3.12 *root* will default to False.
        """
        if self._root_figure is self:
            # Top level Figure
            return self

        if self._parent is self._root_figure:
            # Return early to prevent the deprecation warning when *root* does not
            # matter
            return self._parent

        if root is None:
            # When deprecation expires, consider removing the docstring and just
            # inheriting the one from Artist.
            message = ('From Matplotlib 3.12 SubFigure.get_figure will by default '
                       'return the direct parent figure, which may be a SubFigure. '
                       'To suppress this warning, pass the root parameter.  Pass '
                       '`True` to maintain the old behavior and `False` to opt-in to '
                       'the future behavior.')
            _api.warn_deprecated('3.10', message=message)
            root = True

        if root:
            return self._root_figure

        return self._parent

    def set_figure(self, fig):
        """
        .. deprecated:: 3.10
            Currently this method will raise an exception if *fig* is anything other
            than the root `.Figure` this (Sub)Figure is on.  In future it will always
            raise an exception.
        """
        no_switch = ("The parent and root figures of a (Sub)Figure are set at "
                     "instantiation and cannot be changed.")
        if fig is self._root_figure:
            _api.warn_deprecated(
                "3.10",
                message=(f"{no_switch} From Matplotlib 3.12 this operation will raise "
                         "an exception."))
            return

        raise ValueError(no_switch)

    figure = property(functools.partial(get_figure, root=True), set_figure,
                      doc=("The root `Figure`.  To get the parent of a `SubFigure`, "
                           "use the `get_figure` method."))

    def contains(self, mouseevent):
        """
        Test whether the mouse event occurred on the figure.

        Returns
        -------
            bool, {}
        """
        if self._different_canvas(mouseevent):
            return False, {}
        inside = self.bbox.contains(mouseevent.x, mouseevent.y)
        return inside, {}

    def get_window_extent(self, renderer=None):
        # docstring inherited
        return self.bbox

    def _suplabels(self, t, info, **kwargs):
        """
        Add a centered %(name)s to the figure.

        Parameters
        ----------
        t : str
            The %(name)s text.
        x : float, default: %(x0)s
            The x location of the text in figure coordinates.
        y : float, default: %(y0)s
            The y location of the text in figure coordinates.
        horizontalalignment, ha : {'center', 'left', 'right'}, default: %(ha)s
            The horizontal alignment of the text relative to (*x*, *y*).
        verticalalignment, va : {'top', 'center', 'bottom', 'baseline'}, \
default: %(va)s
            The vertical alignment of the text relative to (*x*, *y*).
        fontsize, size : default: :rc:`figure.%(rc)ssize`
            The font size of the text. See `.Text.set_size` for possible
            values.
        fontweight, weight : default: :rc:`figure.%(rc)sweight`
            The font weight of the text. See `.Text.set_weight` for possible
            values.

        Returns
        -------
        text
            The `.Text` instance of the %(name)s.

        Other Parameters
        ----------------
        fontproperties : None or dict, optional
            A dict of font properties. If *fontproperties* is given the
            default values for font size and weight are taken from the
            `.FontProperties` defaults. :rc:`figure.%(rc)ssize` and
            :rc:`figure.%(rc)sweight` are ignored in this case.

        **kwargs
            Additional kwargs are `matplotlib.text.Text` properties.
        """

        x = kwargs.pop('x', None)
        y = kwargs.pop('y', None)
        if info['name'] in ['_supxlabel', '_suptitle']:
            autopos = y is None
        elif info['name'] == '_supylabel':
            autopos = x is None
        if x is None:
            x = info['x0']
        if y is None:
            y = info['y0']

        kwargs = cbook.normalize_kwargs(kwargs, Text)
        kwargs.setdefault('horizontalalignment', info['ha'])
        kwargs.setdefault('verticalalignment', info['va'])
        kwargs.setdefault('rotation', info['rotation'])

        if 'fontproperties' not in kwargs:
            kwargs.setdefault('fontsize', mpl.rcParams[info['size']])
            kwargs.setdefault('fontweight', mpl.rcParams[info['weight']])

        suplab = getattr(self, info['name'])
        if suplab is not None:
            suplab.set_text(t)
            suplab.set_position((x, y))
            suplab.set(**kwargs)
        else:
            suplab = self.text(x, y, t, **kwargs)
            setattr(self, info['name'], suplab)
        suplab._autopos = autopos
        self.stale = True
        return suplab

    @_docstring.Substitution(x0=0.5, y0=0.98, name='super title', ha='center',
                             va='top', rc='title')
    @_docstring.copy(_suplabels)
    def suptitle(self, t, **kwargs):
        # docstring from _suplabels...
        info = {'name': '_suptitle', 'x0': 0.5, 'y0': 0.98,
                'ha': 'center', 'va': 'top', 'rotation': 0,
                'size': 'figure.titlesize', 'weight': 'figure.titleweight'}
        return self._suplabels(t, info, **kwargs)

    def get_suptitle(self):
        """Return the suptitle as string or an empty string if not set."""
        text_obj = self._suptitle
        return "" if text_obj is None else text_obj.get_text()

    @_docstring.Substitution(x0=0.5, y0=0.01, name='super xlabel', ha='center',
                             va='bottom', rc='label')
    @_docstring.copy(_suplabels)
    def supxlabel(self, t, **kwargs):
        # docstring from _suplabels...
        info = {'name': '_supxlabel', 'x0': 0.5, 'y0': 0.01,
                'ha': 'center', 'va': 'bottom', 'rotation': 0,
                'size': 'figure.labelsize', 'weight': 'figure.labelweight'}
        return self._suplabels(t, info, **kwargs)

    def get_supxlabel(self):
        """Return the supxlabel as string or an empty string if not set."""
        text_obj = self._supxlabel
        return "" if text_obj is None else text_obj.get_text()

    @_docstring.Substitution(x0=0.02, y0=0.5, name='super ylabel', ha='left',
                             va='center', rc='label')
    @_docstring.copy(_suplabels)
    def supylabel(self, t, **kwargs):
        # docstring from _suplabels...
        info = {'name': '_supylabel', 'x0': 0.02, 'y0': 0.5,
                'ha': 'left', 'va': 'center', 'rotation': 'vertical',
                'rotation_mode': 'anchor', 'size': 'figure.labelsize',
                'weight': 'figure.labelweight'}
        return self._suplabels(t, info, **kwargs)

    def get_supylabel(self):
        """Return the supylabel as string or an empty string if not set."""
        text_obj = self._supylabel
        return "" if text_obj is None else text_obj.get_text()

    def get_edgecolor(self):
        """Get the edge color of the Figure rectangle."""
        return self.patch.get_edgecolor()

    def get_facecolor(self):
        """Get the face color of the Figure rectangle."""
        return self.patch.get_facecolor()

    def get_frameon(self):
        """
        Return the figure's background patch visibility, i.e.
        whether the figure background will be drawn. Equivalent to
        ``Figure.patch.get_visible()``.
        """
        return self.patch.get_visible()

    def set_linewidth(self, linewidth):
        """
        Set the line width of the Figure rectangle.

        Parameters
        ----------
        linewidth : number
        """
        self.patch.set_linewidth(linewidth)

    def get_linewidth(self):
        """
        Get the line width of the Figure rectangle.
        """
        return self.patch.get_linewidth()

    def set_edgecolor(self, color):
        """
        Set the edge color of the Figure rectangle.

        Parameters
        ----------
        color : :mpltype:`color`
        """
        self.patch.set_edgecolor(color)

    def set_facecolor(self, color):
        """
        Set the face color of the Figure rectangle.

        Parameters
        ----------
        color : :mpltype:`color`
        """
        self.patch.set_facecolor(color)

    def set_frameon(self, b):
        """
        Set the figure's background patch visibility, i.e.
        whether the figure background will be drawn. Equivalent to
        ``Figure.patch.set_visible()``.

        Parameters
        ----------
        b : bool
        """
        self.patch.set_visible(b)
        self.stale = True

    frameon = property(get_frameon, set_frameon)

    def add_artist(self, artist, clip=False):
        """
        Add an `.Artist` to the figure.

        Usually artists are added to `~.axes.Axes` objects using
        `.Axes.add_artist`; this method can be used in the rare cases where
        one needs to add artists directly to the figure instead.

        Parameters
        ----------
        artist : `~matplotlib.artist.Artist`
            The artist to add to the figure. If the added artist has no
            transform previously set, its transform will be set to
            ``figure.transSubfigure``.
        clip : bool, default: False
            Whether the added artist should be clipped by the figure patch.

        Returns
        -------
        `~matplotlib.artist.Artist`
            The added artist.
        """
        artist.set_figure(self)
        self.artists.append(artist)
        artist._remove_method = self.artists.remove

        if not artist.is_transform_set():
            artist.set_transform(self.transSubfigure)

        if clip and artist.get_clip_path() is None:
            artist.set_clip_path(self.patch)

        self.stale = True
        return artist

    @_docstring.interpd
    def add_axes(self, *args, **kwargs):
        """
        Add an `~.axes.Axes` to the figure.

        Call signatures::

            add_axes(rect, projection=None, polar=False, **kwargs)
            add_axes(ax)

        Parameters
        ----------
        rect : tuple (left, bottom, width, height)
            The dimensions (left, bottom, width, height) of the new
            `~.axes.Axes`. All quantities are in fractions of figure width and
            height.

        projection : {None, 'aitoff', 'hammer', 'lambert', 'mollweide', \
'polar', 'rectilinear', str}, optional
            The projection type of the `~.axes.Axes`. *str* is the name of
            a custom projection, see `~matplotlib.projections`. The default
            None results in a 'rectilinear' projection.

        polar : bool, default: False
            If True, equivalent to projection='polar'.

        axes_class : subclass type of `~.axes.Axes`, optional
            The `.axes.Axes` subclass that is instantiated.  This parameter
            is incompatible with *projection* and *polar*.  See
            :ref:`axisartist_users-guide-index` for examples.

        sharex, sharey : `~matplotlib.axes.Axes`, optional
            Share the x or y `~matplotlib.axis` with sharex and/or sharey.
            The axis will have the same limits, ticks, and scale as the axis
            of the shared Axes.

        label : str
            A label for the returned Axes.

        Returns
        -------
        `~.axes.Axes`, or a subclass of `~.axes.Axes`
            The returned Axes class depends on the projection used. It is
            `~.axes.Axes` if rectilinear projection is used and
            `.projections.polar.PolarAxes` if polar projection is used.

        Other Parameters
        ----------------
        **kwargs
            This method also takes the keyword arguments for
            the returned Axes class. The keyword arguments for the
            rectilinear Axes class `~.axes.Axes` can be found in
            the following table but there might also be other keyword
            arguments if another projection is used, see the actual Axes
            class.

            %(Axes:kwdoc)s

        Notes
        -----
        In rare circumstances, `.add_axes` may be called with a single
        argument, an Axes instance already created in the present figure but
        not in the figure's list of Axes.

        See Also
        --------
        .Figure.add_subplot
        .pyplot.subplot
        .pyplot.axes
        .Figure.subplots
        .pyplot.subplots

        Examples
        --------
        Some simple examples::

            rect = l, b, w, h
            fig = plt.figure()
            fig.add_axes(rect)
            fig.add_axes(rect, frameon=False, facecolor='g')
            fig.add_axes(rect, polar=True)
            ax = fig.add_axes(rect, projection='polar')
            fig.delaxes(ax)
            fig.add_axes(ax)
        """

        if not len(args) and 'rect' not in kwargs:
            raise TypeError("add_axes() missing 1 required positional argument: 'rect'")
        elif 'rect' in kwargs:
            if len(args):
                raise TypeError("add_axes() got multiple values for argument 'rect'")
            args = (kwargs.pop('rect'), )
        if len(args) != 1:
            raise _api.nargs_error("add_axes", 1, len(args))

        if isinstance(args[0], Axes):
            a, = args
            key = a._projection_init
            if a.get_figure(root=False) is not self:
                raise ValueError(
                    "The Axes must have been created in the present figure")
        else:
            rect, = args
            if not np.isfinite(rect).all():
                raise ValueError(f'all entries in rect must be finite not {rect}')
            projection_class, pkw = self._process_projection_requirements(**kwargs)

            # create the new Axes using the Axes class given
            a = projection_class(self, rect, **pkw)
            key = (projection_class, pkw)

        return self._add_axes_internal(a, key)

    @_docstring.interpd
    def add_subplot(self, *args, **kwargs):
        """
        Add an `~.axes.Axes` to the figure as part of a subplot arrangement.

        Call signatures::

           add_subplot(nrows, ncols, index, **kwargs)
           add_subplot(pos, **kwargs)
           add_subplot(ax)
           add_subplot()

        Parameters
        ----------
        *args : int, (int, int, *index*), or `.SubplotSpec`, default: (1, 1, 1)
            The position of the subplot described by one of

            - Three integers (*nrows*, *ncols*, *index*). The subplot will
              take the *index* position on a grid with *nrows* rows and
              *ncols* columns. *index* starts at 1 in the upper left corner
              and increases to the right.  *index* can also be a two-tuple
              specifying the (*first*, *last*) indices (1-based, and including
              *last*) of the subplot, e.g., ``fig.add_subplot(3, 1, (1, 2))``
              makes a subplot that spans the upper 2/3 of the figure.
            - A 3-digit integer. The digits are interpreted as if given
              separately as three single-digit integers, i.e.
              ``fig.add_subplot(235)`` is the same as
              ``fig.add_subplot(2, 3, 5)``. Note that this can only be used
              if there are no more than 9 subplots.
            - A `.SubplotSpec`.

            In rare circumstances, `.add_subplot` may be called with a single
            argument, a subplot Axes instance already created in the
            present figure but not in the figure's list of Axes.

        projection : {None, 'aitoff', 'hammer', 'lambert', 'mollweide', \
'polar', 'rectilinear', str}, optional
            The projection type of the subplot (`~.axes.Axes`). *str* is the
            name of a custom projection, see `~matplotlib.projections`. The
            default None results in a 'rectilinear' projection.

        polar : bool, default: False
            If True, equivalent to projection='polar'.

        axes_class : subclass type of `~.axes.Axes`, optional
            The `.axes.Axes` subclass that is instantiated.  This parameter
            is incompatible with *projection* and *polar*.  See
            :ref:`axisartist_users-guide-index` for examples.

        sharex, sharey : `~matplotlib.axes.Axes`, optional
            Share the x or y `~matplotlib.axis` with sharex and/or sharey.
            The axis will have the same limits, ticks, and scale as the axis
            of the shared Axes.

        label : str
            A label for the returned Axes.

        Returns
        -------
        `~.axes.Axes`

            The Axes of the subplot. The returned Axes can actually be an
            instance of a subclass, such as `.projections.polar.PolarAxes` for
            polar projections.

        Other Parameters
        ----------------
        **kwargs
            This method also takes the keyword arguments for the returned Axes
            base class; except for the *figure* argument. The keyword arguments
            for the rectilinear base class `~.axes.Axes` can be found in
            the following table but there might also be other keyword
            arguments if another projection is used.

            %(Axes:kwdoc)s

        See Also
        --------
        .Figure.add_axes
        .pyplot.subplot
        .pyplot.axes
        .Figure.subplots
        .pyplot.subplots

        Examples
        --------
        ::

            fig = plt.figure()

            fig.add_subplot(231)
            ax1 = fig.add_subplot(2, 3, 1)  # equivalent but more general

            fig.add_subplot(232, frameon=False)  # subplot with no frame
            fig.add_subplot(233, projection='polar')  # polar subplot
            fig.add_subplot(234, sharex=ax1)  # subplot sharing x-axis with ax1
            fig.add_subplot(235, facecolor="red")  # red subplot

            ax1.remove()  # delete ax1 from the figure
            fig.add_subplot(ax1)  # add ax1 back to the figure
        """
        if 'figure' in kwargs:
            # Axes itself allows for a 'figure' kwarg, but since we want to
            # bind the created Axes to self, it is not allowed here.
            raise _api.kwarg_error("add_subplot", "figure")

        if (len(args) == 1
                and isinstance(args[0], mpl.axes._base._AxesBase)
                and args[0].get_subplotspec()):
            ax = args[0]
            key = ax._projection_init
            if ax.get_figure(root=False) is not self:
                raise ValueError("The Axes must have been created in "
                                 "the present figure")
        else:
            if not args:
                args = (1, 1, 1)
            # Normalize correct ijk values to (i, j, k) here so that
            # add_subplot(211) == add_subplot(2, 1, 1).  Invalid values will
            # trigger errors later (via SubplotSpec._from_subplot_args).
            if (len(args) == 1 and isinstance(args[0], Integral)
                    and 100 <= args[0] <= 999):
                args = tuple(map(int, str(args[0])))
            projection_class, pkw = self._process_projection_requirements(**kwargs)
            ax = projection_class(self, *args, **pkw)
            key = (projection_class, pkw)
        return self._add_axes_internal(ax, key)

    def _add_axes_internal(self, ax, key):
        """Private helper for `add_axes` and `add_subplot`."""
        self._axstack.add(ax)
        if ax not in self._localaxes:
            self._localaxes.append(ax)
        self.sca(ax)
        ax._remove_method = self.delaxes
        # this is to support plt.subplot's re-selection logic
        ax._projection_init = key
        self.stale = True
        ax.stale_callback = _stale_figure_callback
        return ax

    def subplots(self, nrows=1, ncols=1, *, sharex=False, sharey=False,
                 squeeze=True, width_ratios=None, height_ratios=None,
                 subplot_kw=None, gridspec_kw=None):
        """
        Add a set of subplots to this figure.

        This utility wrapper makes it convenient to create common layouts of
        subplots in a single call.

        Parameters
        ----------
        nrows, ncols : int, default: 1
            Number of rows/columns of the subplot grid.

        sharex, sharey : bool or {'none', 'all', 'row', 'col'}, default: False
            Controls sharing of x-axis (*sharex*) or y-axis (*sharey*):

            - True or 'all': x- or y-axis will be shared among all subplots.
            - False or 'none': each subplot x- or y-axis will be independent.
            - 'row': each subplot row will share an x- or y-axis.
            - 'col': each subplot column will share an x- or y-axis.

            When subplots have a shared x-axis along a column, only the x tick
            labels of the bottom subplot are created. Similarly, when subplots
            have a shared y-axis along a row, only the y tick labels of the
            first column subplot are created. To later turn other subplots'
            ticklabels on, use `~matplotlib.axes.Axes.tick_params`.

            When subplots have a shared axis that has units, calling
            `.Axis.set_units` will update each axis with the new units.

            Note that it is not possible to unshare axes.

        squeeze : bool, default: True
            - If True, extra dimensions are squeezed out from the returned
              array of Axes:

              - if only one subplot is constructed (nrows=ncols=1), the
                resulting single Axes object is returned as a scalar.
              - for Nx1 or 1xM subplots, the returned object is a 1D numpy
                object array of Axes objects.
              - for NxM, subplots with N>1 and M>1 are returned as a 2D array.

            - If False, no squeezing at all is done: the returned Axes object
              is always a 2D array containing Axes instances, even if it ends
              up being 1x1.

        width_ratios : array-like of length *ncols*, optional
            Defines the relative widths of the columns. Each column gets a
            relative width of ``width_ratios[i] / sum(width_ratios)``.
            If not given, all columns will have the same width.  Equivalent
            to ``gridspec_kw={'width_ratios': [...]}``.

        height_ratios : array-like of length *nrows*, optional
            Defines the relative heights of the rows. Each row gets a
            relative height of ``height_ratios[i] / sum(height_ratios)``.
            If not given, all rows will have the same height. Equivalent
            to ``gridspec_kw={'height_ratios': [...]}``.

        subplot_kw : dict, optional
            Dict with keywords passed to the `.Figure.add_subplot` call used to
            create each subplot.

        gridspec_kw : dict, optional
            Dict with keywords passed to the
            `~matplotlib.gridspec.GridSpec` constructor used to create
            the grid the subplots are placed on.

        Returns
        -------
        `~.axes.Axes` or array of Axes
            Either a single `~matplotlib.axes.Axes` object or an array of Axes
            objects if more than one subplot was created. The dimensions of the
            resulting array can be controlled with the *squeeze* keyword, see
            above.

        See Also
        --------
        .pyplot.subplots
        .Figure.add_subplot
        .pyplot.subplot

        Examples
        --------
        ::

            # First create some toy data:
            x = np.linspace(0, 2*np.pi, 400)
            y = np.sin(x**2)

            # Create a figure
            fig = plt.figure()

            # Create a subplot
            ax = fig.subplots()
            ax.plot(x, y)
            ax.set_title('Simple plot')

            # Create two subplots and unpack the output array immediately
            ax1, ax2 = fig.subplots(1, 2, sharey=True)
            ax1.plot(x, y)
            ax1.set_title('Sharing Y axis')
            ax2.scatter(x, y)

            # Create four polar Axes and access them through the returned array
            axes = fig.subplots(2, 2, subplot_kw=dict(projection='polar'))
            axes[0, 0].plot(x, y)
            axes[1, 1].scatter(x, y)

            # Share an X-axis with each column of subplots
            fig.subplots(2, 2, sharex='col')

            # Share a Y-axis with each row of subplots
            fig.subplots(2, 2, sharey='row')

            # Share both X- and Y-axes with all subplots
            fig.subplots(2, 2, sharex='all', sharey='all')

            # Note that this is the same as
            fig.subplots(2, 2, sharex=True, sharey=True)
        """
        gridspec_kw = dict(gridspec_kw or {})
        if height_ratios is not None:
            if 'height_ratios' in gridspec_kw:
                raise ValueError("'height_ratios' must not be defined both as "
                                 "parameter and as key in 'gridspec_kw'")
            gridspec_kw['height_ratios'] = height_ratios
        if width_ratios is not None:
            if 'width_ratios' in gridspec_kw:
                raise ValueError("'width_ratios' must not be defined both as "
                                 "parameter and as key in 'gridspec_kw'")
            gridspec_kw['width_ratios'] = width_ratios

        gs = self.add_gridspec(nrows, ncols, figure=self, **gridspec_kw)
        axs = gs.subplots(sharex=sharex, sharey=sharey, squeeze=squeeze,
                          subplot_kw=subplot_kw)
        return axs

    def delaxes(self, ax):
        """
        Remove the `~.axes.Axes` *ax* from the figure; update the current Axes.
        """
        self._remove_axes(ax, owners=[self._axstack, self._localaxes])

    def _remove_axes(self, ax, owners):
        """
        Common helper for removal of standard Axes (via delaxes) and of child Axes.

        Parameters
        ----------
        ax : `~.AxesBase`
            The Axes to remove.
        owners
            List of objects (list or _AxesStack) "owning" the Axes, from which the Axes
            will be remove()d.
        """
        for owner in owners:
            owner.remove(ax)

        self._axobservers.process("_axes_change_event", self)
        self.stale = True
        self._root_figure.canvas.release_mouse(ax)

        for name in ax._axis_names:  # Break link between any shared Axes
            grouper = ax._shared_axes[name]
            siblings = [other for other in grouper.get_siblings(ax) if other is not ax]
            if not siblings:  # Axes was not shared along this axis; we're done.
                continue
            grouper.remove(ax)
            # Formatters and locators may previously have been associated with the now
            # removed axis.  Update them to point to an axis still there (we can pick
            # any of them, and use the first sibling).
            remaining_axis = siblings[0]._axis_map[name]
            remaining_axis.get_major_formatter().set_axis(remaining_axis)
            remaining_axis.get_major_locator().set_axis(remaining_axis)
            remaining_axis.get_minor_formatter().set_axis(remaining_axis)
            remaining_axis.get_minor_locator().set_axis(remaining_axis)

        ax._twinned_axes.remove(ax)  # Break link between any twinned Axes.

    def clear(self, keep_observers=False):
        """
        Clear the figure.

        Parameters
        ----------
        keep_observers : bool, default: False
            Set *keep_observers* to True if, for example,
            a gui widget is tracking the Axes in the figure.
        """
        self.suppressComposite = None

        # first clear the Axes in any subfigures
        for subfig in self.subfigs:
            subfig.clear(keep_observers=keep_observers)
        self.subfigs = []

        for ax in tuple(self.axes):  # Iterate over the copy.
            ax.clear()
            self.delaxes(ax)  # Remove ax from self._axstack.

        self.artists = []
        self.lines = []
        self.patches = []
        self.texts = []
        self.images = []
        self.legends = []
        if not keep_observers:
            self._axobservers = cbook.CallbackRegistry()
        self._suptitle = None
        self._supxlabel = None
        self._supylabel = None

        self.stale = True

    # synonym for `clear`.
    def clf(self, keep_observers=False):
        """
        [*Discouraged*] Alias for the `clear()` method.

        .. admonition:: Discouraged

            The use of ``clf()`` is discouraged. Use ``clear()`` instead.

        Parameters
        ----------
        keep_observers : bool, default: False
            Set *keep_observers* to True if, for example,
            a gui widget is tracking the Axes in the figure.
        """
        return self.clear(keep_observers=keep_observers)

    # Note: the docstring below is modified with replace for the pyplot
    # version of this function because the method name differs (plt.figlegend)
    # the replacements are:
    #    " legend(" -> " figlegend(" for the signatures
    #    "fig.legend(" -> "plt.figlegend" for the code examples
    #    "ax.plot" -> "plt.plot" for consistency in using pyplot when able
    @_docstring.interpd
    def legend(self, *args, **kwargs):
        """
        Place a legend on the figure.

        Call signatures::

            legend()
            legend(handles, labels)
            legend(handles=handles)
            legend(labels)

        The call signatures correspond to the following different ways to use
        this method:

        **1. Automatic detection of elements to be shown in the legend**

        The elements to be added to the legend are automatically determined,
        when you do not pass in any extra arguments.

        In this case, the labels are taken from the artist. You can specify
        them either at artist creation or by calling the
        :meth:`~.Artist.set_label` method on the artist::

            ax.plot([1, 2, 3], label='Inline label')
            fig.legend()

        or::

            line, = ax.plot([1, 2, 3])
            line.set_label('Label via method')
            fig.legend()

        Specific lines can be excluded from the automatic legend element
        selection by defining a label starting with an underscore.
        This is default for all artists, so calling `.Figure.legend` without
        any arguments and without setting the labels manually will result in
        no legend being drawn.


        **2. Explicitly listing the artists and labels in the legend**

        For full control of which artists have a legend entry, it is possible
        to pass an iterable of legend artists followed by an iterable of
        legend labels respectively::

            fig.legend([line1, line2, line3], ['label1', 'label2', 'label3'])


        **3. Explicitly listing the artists in the legend**

        This is similar to 2, but the labels are taken from the artists'
        label properties. Example::

            line1, = ax1.plot([1, 2, 3], label='label1')
            line2, = ax2.plot([1, 2, 3], label='label2')
            fig.legend(handles=[line1, line2])


        **4. Labeling existing plot elements**

        .. admonition:: Discouraged

            This call signature is discouraged, because the relation between
            plot elements and labels is only implicit by their order and can
            easily be mixed up.

        To make a legend for all artists on all Axes, call this function with
        an iterable of strings, one for each legend item. For example::

            fig, (ax1, ax2) = plt.subplots(1, 2)
            ax1.plot([1, 3, 5], color='blue')
            ax2.plot([2, 4, 6], color='red')
            fig.legend(['the blues', 'the reds'])


        Parameters
        ----------
        handles : list of `.Artist`, optional
            A list of Artists (lines, patches) to be added to the legend.
            Use this together with *labels*, if you need full control on what
            is shown in the legend and the automatic mechanism described above
            is not sufficient.

            The length of handles and labels should be the same in this
            case. If they are not, they are truncated to the smaller length.

        labels : list of str, optional
            A list of labels to show next to the artists.
            Use this together with *handles*, if you need full control on what
            is shown in the legend and the automatic mechanism described above
            is not sufficient.

        Returns
        -------
        `~matplotlib.legend.Legend`

        Other Parameters
        ----------------
        %(_legend_kw_figure)s

        See Also
        --------
        .Axes.legend

        Notes
        -----
        Some artists are not supported by this function.  See
        :ref:`legend_guide` for details.
        """

        handles, labels, kwargs = mlegend._parse_legend_args(self.axes, *args, **kwargs)
        # explicitly set the bbox transform if the user hasn't.
        kwargs.setdefault("bbox_transform", self.transSubfigure)
        l = mlegend.Legend(self, handles, labels, **kwargs)
        self.legends.append(l)
        l._remove_method = self.legends.remove
        self.stale = True
        return l

    @_docstring.interpd
    def text(self, x, y, s, fontdict=None, **kwargs):
        """
        Add text to figure.

        Parameters
        ----------
        x, y : float
            The position to place the text. By default, this is in figure
            coordinates, floats in [0, 1]. The coordinate system can be changed
            using the *transform* keyword.

        s : str
            The text string.

        fontdict : dict, optional
            A dictionary to override the default text properties. If not given,
            the defaults are determined by :rc:`font.*`. Properties passed as
            *kwargs* override the corresponding ones given in *fontdict*.

        Returns
        -------
        `~.text.Text`

        Other Parameters
        ----------------
        **kwargs : `~matplotlib.text.Text` properties
            Other miscellaneous text parameters.

            %(Text:kwdoc)s

        See Also
        --------
        .Axes.text
        .pyplot.text
        """
        effective_kwargs = {
            'transform': self.transSubfigure,
            **(fontdict if fontdict is not None else {}),
            **kwargs,
        }
        text = Text(x=x, y=y, text=s, **effective_kwargs)
        text.set_figure(self)
        text.stale_callback = _stale_figure_callback

        self.texts.append(text)
        text._remove_method = self.texts.remove
        self.stale = True
        return text

    @_docstring.interpd
    def colorbar(
            self, mappable, cax=None, ax=None, use_gridspec=True, **kwargs):
        """
        Add a colorbar to a plot.

        Parameters
        ----------
        mappable
            The `matplotlib.cm.ScalarMappable` (i.e., `.AxesImage`,
            `.ContourSet`, etc.) described by this colorbar.  This argument is
            mandatory for the `.Figure.colorbar` method but optional for the
            `.pyplot.colorbar` function, which sets the default to the current
            image.

            Note that one can create a `.ScalarMappable` "on-the-fly" to
            generate colorbars not attached to a previously drawn artist, e.g.
            ::

                fig.colorbar(cm.ScalarMappable(norm=norm, cmap=cmap), ax=ax)

        cax : `~matplotlib.axes.Axes`, optional
            Axes into which the colorbar will be drawn.  If `None`, then a new
            Axes is created and the space for it will be stolen from the Axes(s)
            specified in *ax*.

        ax : `~matplotlib.axes.Axes` or iterable or `numpy.ndarray` of Axes, optional
            The one or more parent Axes from which space for a new colorbar Axes
            will be stolen. This parameter is only used if *cax* is not set.

            Defaults to the Axes that contains the mappable used to create the
            colorbar.

        use_gridspec : bool, optional
            If *cax* is ``None``, a new *cax* is created as an instance of
            Axes.  If *ax* is positioned with a subplotspec and *use_gridspec*
            is ``True``, then *cax* is also positioned with a subplotspec.

        Returns
        -------
        colorbar : `~matplotlib.colorbar.Colorbar`

        Other Parameters
        ----------------
        %(_make_axes_kw_doc)s
        %(_colormap_kw_doc)s

        Notes
        -----
        If *mappable* is a `~.contour.ContourSet`, its *extend* kwarg is
        included automatically.

        The *shrink* kwarg provides a simple way to scale the colorbar with
        respect to the Axes. Note that if *cax* is specified, it determines the
        size of the colorbar, and *shrink* and *aspect* are ignored.

        For more precise control, you can manually specify the positions of the
        axes objects in which the mappable and the colorbar are drawn.  In this
        case, do not use any of the Axes properties kwargs.

        It is known that some vector graphics viewers (svg and pdf) render
        white gaps between segments of the colorbar.  This is due to bugs in
        the viewers, not Matplotlib.  As a workaround, the colorbar can be
        rendered with overlapping segments::

            cbar = colorbar()
            cbar.solids.set_edgecolor("face")
            draw()

        However, this has negative consequences in other circumstances, e.g.
        with semi-transparent images (alpha < 1) and colorbar extensions;
        therefore, this workaround is not used by default (see issue #1188).

        """

        if ax is None:
            ax = getattr(mappable, "axes", None)

        if cax is None:
            if ax is None:
                raise ValueError(
                    'Unable to determine Axes to steal space for Colorbar. '
                    'Either provide the *cax* argument to use as the Axes for '
                    'the Colorbar, provide the *ax* argument to steal space '
                    'from it, or add *mappable* to an Axes.')
            fig = (  # Figure of first Axes; logic copied from make_axes.
                [*ax.flat] if isinstance(ax, np.ndarray)
                else [*ax] if np.iterable(ax)
                else [ax])[0].get_figure(root=False)
            current_ax = fig.gca()
            if (fig.get_layout_engine() is not None and
                    not fig.get_layout_engine().colorbar_gridspec):
                use_gridspec = False
            if (use_gridspec
                    and isinstance(ax, mpl.axes._base._AxesBase)
                    and ax.get_subplotspec()):
                cax, kwargs = cbar.make_axes_gridspec(ax, **kwargs)
            else:
                cax, kwargs = cbar.make_axes(ax, **kwargs)
            # make_axes calls add_{axes,subplot} which changes gca; undo that.
            fig.sca(current_ax)
            cax.grid(visible=False, which='both', axis='both')

        if (hasattr(mappable, "get_figure") and
                (mappable_host_fig := mappable.get_figure(root=True)) is not None):
            # Warn in case of mismatch
            if mappable_host_fig is not self._root_figure:
                _api.warn_external(
                        f'Adding colorbar to a different Figure '
                        f'{repr(mappable_host_fig)} than '
                        f'{repr(self._root_figure)} which '
                        f'fig.colorbar is called on.')

        NON_COLORBAR_KEYS = [  # remove kws that cannot be passed to Colorbar
            'fraction', 'pad', 'shrink', 'aspect', 'anchor', 'panchor']
        cb = cbar.Colorbar(cax, mappable, **{
            k: v for k, v in kwargs.items() if k not in NON_COLORBAR_KEYS})
        cax.get_figure(root=False).stale = True
        return cb

    def subplots_adjust(self, left=None, bottom=None, right=None, top=None,
                        wspace=None, hspace=None):
        """
        Adjust the subplot layout parameters.

        Unset parameters are left unmodified; initial values are given by
        :rc:`figure.subplot.[name]`.

        .. plot:: _embedded_plots/figure_subplots_adjust.py

        Parameters
        ----------
        left : float, optional
            The position of the left edge of the subplots,
            as a fraction of the figure width.
        right : float, optional
            The position of the right edge of the subplots,
            as a fraction of the figure width.
        bottom : float, optional
            The position of the bottom edge of the subplots,
            as a fraction of the figure height.
        top : float, optional
            The position of the top edge of the subplots,
            as a fraction of the figure height.
        wspace : float, optional
            The width of the padding between subplots,
            as a fraction of the average Axes width.
        hspace : float, optional
            The height of the padding between subplots,
            as a fraction of the average Axes height.
        """
        if (self.get_layout_engine() is not None and
                not self.get_layout_engine().adjust_compatible):
            _api.warn_external(
                "This figure was using a layout engine that is "
                "incompatible with subplots_adjust and/or tight_layout; "
                "not calling subplots_adjust.")
            return
        self.subplotpars.update(left, bottom, right, top, wspace, hspace)
        for ax in self.axes:
            if ax.get_subplotspec() is not None:
                ax._set_position(ax.get_subplotspec().get_position(self))
        self.stale = True

    def align_xlabels(self, axs=None):
        """
        Align the xlabels of subplots in the same subplot row if label
        alignment is being done automatically (i.e. the label position is
        not manually set).

        Alignment persists for draw events after this is called.

        If a label is on the bottom, it is aligned with labels on Axes that
        also have their label on the bottom and that have the same
        bottom-most subplot row.  If the label is on the top,
        it is aligned with labels on Axes with the same top-most row.

        Parameters
        ----------
        axs : list of `~matplotlib.axes.Axes`
            Optional list of (or `~numpy.ndarray`) `~matplotlib.axes.Axes`
            to align the xlabels.
            Default is to align all Axes on the figure.

        See Also
        --------
        matplotlib.figure.Figure.align_ylabels
        matplotlib.figure.Figure.align_titles
        matplotlib.figure.Figure.align_labels

        Notes
        -----
        This assumes that all Axes in ``axs`` are from the same `.GridSpec`,
        so that their `.SubplotSpec` positions correspond to figure positions.

        Examples
        --------
        Example with rotated xtick labels::

            fig, axs = plt.subplots(1, 2)
            for tick in axs[0].get_xticklabels():
                tick.set_rotation(55)
            axs[0].set_xlabel('XLabel 0')
            axs[1].set_xlabel('XLabel 1')
            fig.align_xlabels()
        """
        if axs is None:
            axs = self.axes
        axs = [ax for ax in np.ravel(axs) if ax.get_subplotspec() is not None]
        for ax in axs:
            _log.debug(' Working on: %s', ax.get_xlabel())
            rowspan = ax.get_subplotspec().rowspan
            pos = ax.xaxis.get_label_position()  # top or bottom
            # Search through other Axes for label positions that are same as
            # this one and that share the appropriate row number.
            # Add to a grouper associated with each Axes of siblings.
            # This list is inspected in `axis.draw` by
            # `axis._update_label_position`.
            for axc in axs:
                if axc.xaxis.get_label_position() == pos:
                    rowspanc = axc.get_subplotspec().rowspan
                    if (pos == 'top' and rowspan.start == rowspanc.start or
                            pos == 'bottom' and rowspan.stop == rowspanc.stop):
                        # grouper for groups of xlabels to align
                        self._align_label_groups['x'].join(ax, axc)

    def align_ylabels(self, axs=None):
        """
        Align the ylabels of subplots in the same subplot column if label
        alignment is being done automatically (i.e. the label position is
        not manually set).

        Alignment persists for draw events after this is called.

        If a label is on the left, it is aligned with labels on Axes that
        also have their label on the left and that have the same
        left-most subplot column.  If the label is on the right,
        it is aligned with labels on Axes with the same right-most column.

        Parameters
        ----------
        axs : list of `~matplotlib.axes.Axes`
            Optional list (or `~numpy.ndarray`) of `~matplotlib.axes.Axes`
            to align the ylabels.
            Default is to align all Axes on the figure.

        See Also
        --------
        matplotlib.figure.Figure.align_xlabels
        matplotlib.figure.Figure.align_titles
        matplotlib.figure.Figure.align_labels

        Notes
        -----
        This assumes that all Axes in ``axs`` are from the same `.GridSpec`,
        so that their `.SubplotSpec` positions correspond to figure positions.

        Examples
        --------
        Example with large yticks labels::

            fig, axs = plt.subplots(2, 1)
            axs[0].plot(np.arange(0, 1000, 50))
            axs[0].set_ylabel('YLabel 0')
            axs[1].set_ylabel('YLabel 1')
            fig.align_ylabels()
        """
        if axs is None:
            axs = self.axes
        axs = [ax for ax in np.ravel(axs) if ax.get_subplotspec() is not None]
        for ax in axs:
            _log.debug(' Working on: %s', ax.get_ylabel())
            colspan = ax.get_subplotspec().colspan
            pos = ax.yaxis.get_label_position()  # left or right
            # Search through other Axes for label positions that are same as
            # this one and that share the appropriate column number.
            # Add to a list associated with each Axes of siblings.
            # This list is inspected in `axis.draw` by
            # `axis._update_label_position`.
            for axc in axs:
                if axc.yaxis.get_label_position() == pos:
                    colspanc = axc.get_subplotspec().colspan
                    if (pos == 'left' and colspan.start == colspanc.start or
                            pos == 'right' and colspan.stop == colspanc.stop):
                        # grouper for groups of ylabels to align
                        self._align_label_groups['y'].join(ax, axc)

    def align_titles(self, axs=None):
        """
        Align the titles of subplots in the same subplot row if title
        alignment is being done automatically (i.e. the title position is
        not manually set).

        Alignment persists for draw events after this is called.

        Parameters
        ----------
        axs : list of `~matplotlib.axes.Axes`
            Optional list of (or ndarray) `~matplotlib.axes.Axes`
            to align the titles.
            Default is to align all Axes on the figure.

        See Also
        --------
        matplotlib.figure.Figure.align_xlabels
        matplotlib.figure.Figure.align_ylabels
        matplotlib.figure.Figure.align_labels

        Notes
        -----
        This assumes that all Axes in ``axs`` are from the same `.GridSpec`,
        so that their `.SubplotSpec` positions correspond to figure positions.

        Examples
        --------
        Example with titles::

            fig, axs = plt.subplots(1, 2)
            axs[0].set_aspect('equal')
            axs[0].set_title('Title 0')
            axs[1].set_title('Title 1')
            fig.align_titles()
        """
        if axs is None:
            axs = self.axes
        axs = [ax for ax in np.ravel(axs) if ax.get_subplotspec() is not None]
        for ax in axs:
            _log.debug(' Working on: %s', ax.get_title())
            rowspan = ax.get_subplotspec().rowspan
            for axc in axs:
                rowspanc = axc.get_subplotspec().rowspan
                if (rowspan.start == rowspanc.start):
                    self._align_label_groups['title'].join(ax, axc)

    def align_labels(self, axs=None):
        """
        Align the xlabels and ylabels of subplots with the same subplots
        row or column (respectively) if label alignment is being
        done automatically (i.e. the label position is not manually set).

        Alignment persists for draw events after this is called.

        Parameters
        ----------
        axs : list of `~matplotlib.axes.Axes`
            Optional list (or `~numpy.ndarray`) of `~matplotlib.axes.Axes`
            to align the labels.
            Default is to align all Axes on the figure.

        See Also
        --------
        matplotlib.figure.Figure.align_xlabels
        matplotlib.figure.Figure.align_ylabels
        matplotlib.figure.Figure.align_titles

        Notes
        -----
        This assumes that all Axes in ``axs`` are from the same `.GridSpec`,
        so that their `.SubplotSpec` positions correspond to figure positions.
        """
        self.align_xlabels(axs=axs)
        self.align_ylabels(axs=axs)

    def add_gridspec(self, nrows=1, ncols=1, **kwargs):
        """
        Low-level API for creating a `.GridSpec` that has this figure as a parent.

        This is a low-level API, allowing you to create a gridspec and
        subsequently add subplots based on the gridspec. Most users do
        not need that freedom and should use the higher-level methods
        `~.Figure.subplots` or `~.Figure.subplot_mosaic`.

        Parameters
        ----------
        nrows : int, default: 1
            Number of rows in grid.

        ncols : int, default: 1
            Number of columns in grid.

        Returns
        -------
        `.GridSpec`

        Other Parameters
        ----------------
        **kwargs
            Keyword arguments are passed to `.GridSpec`.

        See Also
        --------
        matplotlib.pyplot.subplots

        Examples
        --------
        Adding a subplot that spans two rows::

            fig = plt.figure()
            gs = fig.add_gridspec(2, 2)
            ax1 = fig.add_subplot(gs[0, 0])
            ax2 = fig.add_subplot(gs[1, 0])
            # spans two rows:
            ax3 = fig.add_subplot(gs[:, 1])

        """

        _ = kwargs.pop('figure', None)  # pop in case user has added this...
        gs = GridSpec(nrows=nrows, ncols=ncols, figure=self, **kwargs)
        return gs

    def subfigures(self, nrows=1, ncols=1, squeeze=True,
                   wspace=None, hspace=None,
                   width_ratios=None, height_ratios=None,
                   **kwargs):
        """
        Add a set of subfigures to this figure or subfigure.

        A subfigure has the same artist methods as a figure, and is logically
        the same as a figure, but cannot print itself.
        See :doc:`/gallery/subplots_axes_and_figures/subfigures`.

        .. versionchanged:: 3.10
            subfigures are now added in row-major order.

        Parameters
        ----------
        nrows, ncols : int, default: 1
            Number of rows/columns of the subfigure grid.

        squeeze : bool, default: True
            If True, extra dimensions are squeezed out from the returned
            array of subfigures.

        wspace, hspace : float, default: None
            The amount of width/height reserved for space between subfigures,
            expressed as a fraction of the average subfigure width/height.
            If not given, the values will be inferred from rcParams if using
            constrained layout (see `~.ConstrainedLayoutEngine`), or zero if
            not using a layout engine.

        width_ratios : array-like of length *ncols*, optional
            Defines the relative widths of the columns. Each column gets a
            relative width of ``width_ratios[i] / sum(width_ratios)``.
            If not given, all columns will have the same width.

        height_ratios : array-like of length *nrows*, optional
            Defines the relative heights of the rows. Each row gets a
            relative height of ``height_ratios[i] / sum(height_ratios)``.
            If not given, all rows will have the same height.
        """
        gs = GridSpec(nrows=nrows, ncols=ncols, figure=self,
                      wspace=wspace, hspace=hspace,
                      width_ratios=width_ratios,
                      height_ratios=height_ratios,
                      left=0, right=1, bottom=0, top=1)

        sfarr = np.empty((nrows, ncols), dtype=object)
        for i in range(nrows):
            for j in range(ncols):
                sfarr[i, j] = self.add_subfigure(gs[i, j], **kwargs)

        if self.get_layout_engine() is None and (wspace is not None or
                                                 hspace is not None):
            # Gridspec wspace and hspace is ignored on subfigure instantiation,
            # and no space is left.  So need to account for it here if required.
            bottoms, tops, lefts, rights = gs.get_grid_positions(self)
            for sfrow, bottom, top in zip(sfarr, bottoms, tops):
                for sf, left, right in zip(sfrow, lefts, rights):
                    bbox = Bbox.from_extents(left, bottom, right, top)
                    sf._redo_transform_rel_fig(bbox=bbox)

        if squeeze:
            # Discarding unneeded dimensions that equal 1.  If we only have one
            # subfigure, just return it instead of a 1-element array.
            return sfarr.item() if sfarr.size == 1 else sfarr.squeeze()
        else:
            # Returned axis array will be always 2-d, even if nrows=ncols=1.
            return sfarr

    def add_subfigure(self, subplotspec, **kwargs):
        """
        Add a `.SubFigure` to the figure as part of a subplot arrangement.

        Parameters
        ----------
        subplotspec : `.gridspec.SubplotSpec`
            Defines the region in a parent gridspec where the subfigure will
            be placed.

        Returns
        -------
        `.SubFigure`

        Other Parameters
        ----------------
        **kwargs
            Are passed to the `.SubFigure` object.

        See Also
        --------
        .Figure.subfigures
        """
        sf = SubFigure(self, subplotspec, **kwargs)
        self.subfigs += [sf]
        sf._remove_method = self.subfigs.remove
        sf.stale_callback = _stale_figure_callback
        self.stale = True
        return sf

    def sca(self, a):
        """Set the current Axes to be *a* and return *a*."""
        self._axstack.bubble(a)
        self._axobservers.process("_axes_change_event", self)
        return a

    def gca(self):
        """
        Get the current Axes.

        If there is currently no Axes on this Figure, a new one is created
        using `.Figure.add_subplot`.  (To test whether there is currently an
        Axes on a Figure, check whether ``figure.axes`` is empty.  To test
        whether there is currently a Figure on the pyplot figure stack, check
        whether `.pyplot.get_fignums()` is empty.)
        """
        ax = self._axstack.current()
        return ax if ax is not None else self.add_subplot()

    def _gci(self):
        # Helper for `~matplotlib.pyplot.gci`.  Do not use elsewhere.
        """
        Get the current colorable artist.

        Specifically, returns the current `.ScalarMappable` instance (`.Image`
        created by `imshow` or `figimage`, `.Collection` created by `pcolor` or
        `scatter`, etc.), or *None* if no such instance has been defined.

        The current image is an attribute of the current Axes, or the nearest
        earlier Axes in the current figure that contains an image.

        Notes
        -----
        Historically, the only colorable artists were images; hence the name
        ``gci`` (get current image).
        """
        # Look first for an image in the current Axes.
        ax = self._axstack.current()
        if ax is None:
            return None
        im = ax._gci()
        if im is not None:
            return im
        # If there is no image in the current Axes, search for
        # one in a previously created Axes.  Whether this makes
        # sense is debatable, but it is the documented behavior.
        for ax in reversed(self.axes):
            im = ax._gci()
            if im is not None:
                return im
        return None

    def _process_projection_requirements(self, *, axes_class=None, polar=False,
                                         projection=None, **kwargs):
        """
        Handle the args/kwargs to add_axes/add_subplot/gca, returning::

            (axes_proj_class, proj_class_kwargs)

        which can be used for new Axes initialization/identification.
        """
        if axes_class is not None:
            if polar or projection is not None:
                raise ValueError(
                    "Cannot combine 'axes_class' and 'projection' or 'polar'")
            projection_class = axes_class
        else:

            if polar:
                if projection is not None and projection != 'polar':
                    raise ValueError(
                        f"polar={polar}, yet projection={projection!r}. "
                        "Only one of these arguments should be supplied."
                    )
                projection = 'polar'

            if isinstance(projection, str) or projection is None:
                projection_class = projections.get_projection_class(projection)
            elif hasattr(projection, '_as_mpl_axes'):
                projection_class, extra_kwargs = projection._as_mpl_axes()
                kwargs.update(**extra_kwargs)
            else:
                raise TypeError(
                    f"projection must be a string, None or implement a "
                    f"_as_mpl_axes method, not {projection!r}")
        return projection_class, kwargs

    def get_default_bbox_extra_artists(self):
        """
        Return a list of Artists typically used in `.Figure.get_tightbbox`.
        """
        bbox_artists = [artist for artist in self.get_children()
                        if (artist.get_visible() and artist.get_in_layout())]
        for ax in self.axes:
            if ax.get_visible():
                bbox_artists.extend(ax.get_default_bbox_extra_artists())
        return bbox_artists

    def get_tightbbox(self, renderer=None, *, bbox_extra_artists=None):
        """
        Return a (tight) bounding box of the figure *in inches*.

        Note that `.FigureBase` differs from all other artists, which return
        their `.Bbox` in pixels.

        Artists that have ``artist.set_in_layout(False)`` are not included
        in the bbox.

        Parameters
        ----------
        renderer : `.RendererBase` subclass
            Renderer that will be used to draw the figures (i.e.
            ``fig.canvas.get_renderer()``)

        bbox_extra_artists : list of `.Artist` or ``None``
            List of artists to include in the tight bounding box.  If
            ``None`` (default), then all artist children of each Axes are
            included in the tight bounding box.

        Returns
        -------
        `.BboxBase`
            containing the bounding box (in figure inches).
        """

        if renderer is None:
            renderer = self.get_figure(root=True)._get_renderer()

        bb = []
        if bbox_extra_artists is None:
            artists = [artist for artist in self.get_children()
                       if (artist not in self.axes and artist.get_visible()
                           and artist.get_in_layout())]
        else:
            artists = bbox_extra_artists

        for a in artists:
            bbox = a.get_tightbbox(renderer)
            if bbox is not None:
                bb.append(bbox)

        for ax in self.axes:
            if ax.get_visible():
                # some Axes don't take the bbox_extra_artists kwarg so we
                # need this conditional....
                try:
                    bbox = ax.get_tightbbox(
                        renderer, bbox_extra_artists=bbox_extra_artists)
                except TypeError:
                    bbox = ax.get_tightbbox(renderer)
                bb.append(bbox)
        bb = [b for b in bb
              if (np.isfinite(b.width) and np.isfinite(b.height)
                  and (b.width != 0 or b.height != 0))]

        isfigure = hasattr(self, 'bbox_inches')
        if len(bb) == 0:
            if isfigure:
                return self.bbox_inches
            else:
                # subfigures do not have bbox_inches, but do have a bbox
                bb = [self.bbox]

        _bbox = Bbox.union(bb)

        if isfigure:
            # transform from pixels to inches...
            _bbox = TransformedBbox(_bbox, self.dpi_scale_trans.inverted())

        return _bbox

    @staticmethod
    def _norm_per_subplot_kw(per_subplot_kw):
        expanded = {}
        for k, v in per_subplot_kw.items():
            if isinstance(k, tuple):
                for sub_key in k:
                    if sub_key in expanded:
                        raise ValueError(f'The key {sub_key!r} appears multiple times.')
                    expanded[sub_key] = v
            else:
                if k in expanded:
                    raise ValueError(f'The key {k!r} appears multiple times.')
                expanded[k] = v
        return expanded

    @staticmethod
    def _normalize_grid_string(layout):
        if '\n' not in layout:
            # single-line string
            return [list(ln) for ln in layout.split(';')]
        else:
            # multi-line string
            layout = inspect.cleandoc(layout)
            return [list(ln) for ln in layout.strip('\n').split('\n')]

    def subplot_mosaic(self, mosaic, *, sharex=False, sharey=False,
                       width_ratios=None, height_ratios=None,
                       empty_sentinel='.',
                       subplot_kw=None, per_subplot_kw=None, gridspec_kw=None):
        """
        Build a layout of Axes based on ASCII art or nested lists.

        This is a helper function to build complex GridSpec layouts visually.

        See :ref:`mosaic`
        for an example and full API documentation

        Parameters
        ----------
        mosaic : list of list of {hashable or nested} or str

            A visual layout of how you want your Axes to be arranged
            labeled as strings.  For example ::

               x = [['A panel', 'A panel', 'edge'],
                    ['C panel', '.',       'edge']]

            produces 4 Axes:

            - 'A panel' which is 1 row high and spans the first two columns
            - 'edge' which is 2 rows high and is on the right edge
            - 'C panel' which in 1 row and 1 column wide in the bottom left
            - a blank space 1 row and 1 column wide in the bottom center

            Any of the entries in the layout can be a list of lists
            of the same form to create nested layouts.

            If input is a str, then it can either be a multi-line string of
            the form ::

              '''
              AAE
              C.E
              '''

            where each character is a column and each line is a row. Or it
            can be a single-line string where rows are separated by ``;``::

              'AB;CC'

            The string notation allows only single character Axes labels and
            does not support nesting but is very terse.

            The Axes identifiers may be `str` or a non-iterable hashable
            object (e.g. `tuple` s may not be used).

        sharex, sharey : bool, default: False
            If True, the x-axis (*sharex*) or y-axis (*sharey*) will be shared
            among all subplots.  In that case, tick label visibility and axis
            units behave as for `subplots`.  If False, each subplot's x- or
            y-axis will be independent.

        width_ratios : array-like of length *ncols*, optional
            Defines the relative widths of the columns. Each column gets a
            relative width of ``width_ratios[i] / sum(width_ratios)``.
            If not given, all columns will have the same width.  Equivalent
            to ``gridspec_kw={'width_ratios': [...]}``. In the case of nested
            layouts, this argument applies only to the outer layout.

        height_ratios : array-like of length *nrows*, optional
            Defines the relative heights of the rows. Each row gets a
            relative height of ``height_ratios[i] / sum(height_ratios)``.
            If not given, all rows will have the same height. Equivalent
            to ``gridspec_kw={'height_ratios': [...]}``. In the case of nested
            layouts, this argument applies only to the outer layout.

        subplot_kw : dict, optional
            Dictionary with keywords passed to the `.Figure.add_subplot` call
            used to create each subplot.  These values may be overridden by
            values in *per_subplot_kw*.

        per_subplot_kw : dict, optional
            A dictionary mapping the Axes identifiers or tuples of identifiers
            to a dictionary of keyword arguments to be passed to the
            `.Figure.add_subplot` call used to create each subplot.  The values
            in these dictionaries have precedence over the values in
            *subplot_kw*.

            If *mosaic* is a string, and thus all keys are single characters,
            it is possible to use a single string instead of a tuple as keys;
            i.e. ``"AB"`` is equivalent to ``("A", "B")``.

            .. versionadded:: 3.7

        gridspec_kw : dict, optional
            Dictionary with keywords passed to the `.GridSpec` constructor used
            to create the grid the subplots are placed on. In the case of
            nested layouts, this argument applies only to the outer layout.
            For more complex layouts, users should use `.Figure.subfigures`
            to create the nesting.

        empty_sentinel : object, optional
            Entry in the layout to mean "leave this space empty".  Defaults
            to ``'.'``. Note, if *layout* is a string, it is processed via
            `inspect.cleandoc` to remove leading white space, which may
            interfere with using white-space as the empty sentinel.

        Returns
        -------
        dict[label, Axes]
           A dictionary mapping the labels to the Axes objects.  The order of
           the Axes is left-to-right and top-to-bottom of their position in the
           total layout.

        """
        subplot_kw = subplot_kw or {}
        gridspec_kw = dict(gridspec_kw or {})
        per_subplot_kw = per_subplot_kw or {}

        if height_ratios is not None:
            if 'height_ratios' in gridspec_kw:
                raise ValueError("'height_ratios' must not be defined both as "
                                 "parameter and as key in 'gridspec_kw'")
            gridspec_kw['height_ratios'] = height_ratios
        if width_ratios is not None:
            if 'width_ratios' in gridspec_kw:
                raise ValueError("'width_ratios' must not be defined both as "
                                 "parameter and as key in 'gridspec_kw'")
            gridspec_kw['width_ratios'] = width_ratios

        # special-case string input
        if isinstance(mosaic, str):
            mosaic = self._normalize_grid_string(mosaic)
            per_subplot_kw = {
                tuple(k): v for k, v in per_subplot_kw.items()
            }

        per_subplot_kw = self._norm_per_subplot_kw(per_subplot_kw)

        # Only accept strict bools to allow a possible future API expansion.
        _api.check_isinstance(bool, sharex=sharex, sharey=sharey)

        def _make_array(inp):
            """
            Convert input into 2D array

            We need to have this internal function rather than
            ``np.asarray(..., dtype=object)`` so that a list of lists
            of lists does not get converted to an array of dimension > 2.

            Returns
            -------
            2D object array
            """
            r0, *rest = inp
            if isinstance(r0, str):
                raise ValueError('List mosaic specification must be 2D')
            for j, r in enumerate(rest, start=1):
                if isinstance(r, str):
                    raise ValueError('List mosaic specification must be 2D')
                if len(r0) != len(r):
                    raise ValueError(
                        "All of the rows must be the same length, however "
                        f"the first row ({r0!r}) has length {len(r0)} "
                        f"and row {j} ({r!r}) has length {len(r)}."
                    )
            out = np.zeros((len(inp), len(r0)), dtype=object)
            for j, r in enumerate(inp):
                for k, v in enumerate(r):
                    out[j, k] = v
            return out

        def _identify_keys_and_nested(mosaic):
            """
            Given a 2D object array, identify unique IDs and nested mosaics

            Parameters
            ----------
            mosaic : 2D object array

            Returns
            -------
            unique_ids : tuple
                The unique non-sub mosaic entries in this mosaic
            nested : dict[tuple[int, int], 2D object array]
            """
            # make sure we preserve the user supplied order
            unique_ids = cbook._OrderedSet()
            nested = {}
            for j, row in enumerate(mosaic):
                for k, v in enumerate(row):
                    if v == empty_sentinel:
                        continue
                    elif not cbook.is_scalar_or_string(v):
                        nested[(j, k)] = _make_array(v)
                    else:
                        unique_ids.add(v)

            return tuple(unique_ids), nested

        def _do_layout(gs, mosaic, unique_ids, nested):
            """
            Recursively do the mosaic.

            Parameters
            ----------
            gs : GridSpec
            mosaic : 2D object array
                The input converted to a 2D array for this level.
            unique_ids : tuple
                The identified scalar labels at this level of nesting.
            nested : dict[tuple[int, int]], 2D object array
                The identified nested mosaics, if any.

            Returns
            -------
            dict[label, Axes]
                A flat dict of all of the Axes created.
            """
            output = dict()

            # we need to merge together the Axes at this level and the Axes
            # in the (recursively) nested sub-mosaics so that we can add
            # them to the figure in the "natural" order if you were to
            # ravel in c-order all of the Axes that will be created
            #
            # This will stash the upper left index of each object (axes or
            # nested mosaic) at this level
            this_level = dict()

            # go through the unique keys,
            for name in unique_ids:
                # sort out where each axes starts/ends
                indx = np.argwhere(mosaic == name)
                start_row, start_col = np.min(indx, axis=0)
                end_row, end_col = np.max(indx, axis=0) + 1
                # and construct the slice object
                slc = (slice(start_row, end_row), slice(start_col, end_col))
                # some light error checking
                if (mosaic[slc] != name).any():
                    raise ValueError(
                        f"While trying to layout\n{mosaic!r}\n"
                        f"we found that the label {name!r} specifies a "
                        "non-rectangular or non-contiguous area.")
                # and stash this slice for later
                this_level[(start_row, start_col)] = (name, slc, 'axes')

            # do the same thing for the nested mosaics (simpler because these
            # cannot be spans yet!)
            for (j, k), nested_mosaic in nested.items():
                this_level[(j, k)] = (None, nested_mosaic, 'nested')

            # now go through the things in this level and add them
            # in order left-to-right top-to-bottom
            for key in sorted(this_level):
                name, arg, method = this_level[key]
                # we are doing some hokey function dispatch here based
                # on the 'method' string stashed above to sort out if this
                # element is an Axes or a nested mosaic.
                if method == 'axes':
                    slc = arg
                    # add a single Axes
                    if name in output:
                        raise ValueError(f"There are duplicate keys {name} "
                                         f"in the layout\n{mosaic!r}")
                    ax = self.add_subplot(
                        gs[slc], **{
                            'label': str(name),
                            **subplot_kw,
                            **per_subplot_kw.get(name, {})
                        }
                    )
                    output[name] = ax
                elif method == 'nested':
                    nested_mosaic = arg
                    j, k = key
                    # recursively add the nested mosaic
                    rows, cols = nested_mosaic.shape
                    nested_output = _do_layout(
                        gs[j, k].subgridspec(rows, cols),
                        nested_mosaic,
                        *_identify_keys_and_nested(nested_mosaic)
                    )
                    overlap = set(output) & set(nested_output)
                    if overlap:
                        raise ValueError(
                            f"There are duplicate keys {overlap} "
                            f"between the outer layout\n{mosaic!r}\n"
                            f"and the nested layout\n{nested_mosaic}"
                        )
                    output.update(nested_output)
                else:
                    raise RuntimeError("This should never happen")
            return output

        mosaic = _make_array(mosaic)
        rows, cols = mosaic.shape
        gs = self.add_gridspec(rows, cols, **gridspec_kw)
        ret = _do_layout(gs, mosaic, *_identify_keys_and_nested(mosaic))
        ax0 = next(iter(ret.values()))
        for ax in ret.values():
            if sharex:
                ax.sharex(ax0)
                ax._label_outer_xaxis(skip_non_rectangular_axes=True)
            if sharey:
                ax.sharey(ax0)
                ax._label_outer_yaxis(skip_non_rectangular_axes=True)
        if extra := set(per_subplot_kw) - set(ret):
            raise ValueError(
                f"The keys {extra} are in *per_subplot_kw* "
                "but not in the mosaic."
            )
        return ret

    def _set_artist_props(self, a):
        if a != self:
            a.set_figure(self)
        a.stale_callback = _stale_figure_callback
        a.set_transform(self.transSubfigure)


@_docstring.interpd
class SubFigure(FigureBase):
    """
    Logical figure that can be placed inside a figure.

    See :ref:`figure-api-subfigure` for an index of methods on this class.
    Typically instantiated using `.Figure.add_subfigure` or
    `.SubFigure.add_subfigure`, or `.SubFigure.subfigures`.  A subfigure has
    the same methods as a figure except for those particularly tied to the size
    or dpi of the figure, and is confined to a prescribed region of the figure.
    For example the following puts two subfigures side-by-side::

        fig = plt.figure()
        sfigs = fig.subfigures(1, 2)
        axsL = sfigs[0].subplots(1, 2)
        axsR = sfigs[1].subplots(2, 1)

    See :doc:`/gallery/subplots_axes_and_figures/subfigures`
    """

    def __init__(self, parent, subplotspec, *,
                 facecolor=None,
                 edgecolor=None,
                 linewidth=0.0,
                 frameon=None,
                 **kwargs):
        """
        Parameters
        ----------
        parent : `.Figure` or `.SubFigure`
            Figure or subfigure that contains the SubFigure.  SubFigures
            can be nested.

        subplotspec : `.gridspec.SubplotSpec`
            Defines the region in a parent gridspec where the subfigure will
            be placed.

        facecolor : default: ``"none"``
            The figure patch face color; transparent by default.

        edgecolor : default: :rc:`figure.edgecolor`
            The figure patch edge color.

        linewidth : float
            The linewidth of the frame (i.e. the edge linewidth of the figure
            patch).

        frameon : bool, default: :rc:`figure.frameon`
            If ``False``, suppress drawing the figure background patch.

        Other Parameters
        ----------------
        **kwargs : `.SubFigure` properties, optional

            %(SubFigure:kwdoc)s
        """
        super().__init__(**kwargs)
        if facecolor is None:
            facecolor = "none"
        if edgecolor is None:
            edgecolor = mpl.rcParams['figure.edgecolor']
        if frameon is None:
            frameon = mpl.rcParams['figure.frameon']

        self._subplotspec = subplotspec
        self._parent = parent
        self._root_figure = parent._root_figure

        # subfigures use the parent axstack
        self._axstack = parent._axstack
        self.subplotpars = parent.subplotpars
        self.dpi_scale_trans = parent.dpi_scale_trans
        self._axobservers = parent._axobservers
        self.transFigure = parent.transFigure
        self.bbox_relative = Bbox.null()
        self._redo_transform_rel_fig()
        self.figbbox = self._parent.figbbox
        self.bbox = TransformedBbox(self.bbox_relative,
                                    self._parent.transSubfigure)
        self.transSubfigure = BboxTransformTo(self.bbox)

        self.patch = Rectangle(
            xy=(0, 0), width=1, height=1, visible=frameon,
            facecolor=facecolor, edgecolor=edgecolor, linewidth=linewidth,
            # Don't let the figure patch influence bbox calculation.
            in_layout=False, transform=self.transSubfigure)
        self._set_artist_props(self.patch)
        self.patch.set_antialiased(False)

    @property
    def canvas(self):
        return self._parent.canvas

    @property
    def dpi(self):
        return self._parent.dpi

    @dpi.setter
    def dpi(self, value):
        self._parent.dpi = value

    def get_dpi(self):
        """
        Return the resolution of the parent figure in dots-per-inch as a float.
        """
        return self._parent.dpi

    def set_dpi(self, val):
        """
        Set the resolution of parent figure in dots-per-inch.

        Parameters
        ----------
        val : float
        """
        self._parent.dpi = val
        self.stale = True

    def _get_renderer(self):
        return self._parent._get_renderer()

    def _redo_transform_rel_fig(self, bbox=None):
        """
        Make the transSubfigure bbox relative to Figure transform.

        Parameters
        ----------
        bbox : bbox or None
            If not None, then the bbox is used for relative bounding box.
            Otherwise, it is calculated from the subplotspec.
        """
        if bbox is not None:
            self.bbox_relative.p0 = bbox.p0
            self.bbox_relative.p1 = bbox.p1
            return
        # need to figure out *where* this subplotspec is.
        gs = self._subplotspec.get_gridspec()
        wr = np.asarray(gs.get_width_ratios())
        hr = np.asarray(gs.get_height_ratios())
        dx = wr[self._subplotspec.colspan].sum() / wr.sum()
        dy = hr[self._subplotspec.rowspan].sum() / hr.sum()
        x0 = wr[:self._subplotspec.colspan.start].sum() / wr.sum()
        y0 = 1 - hr[:self._subplotspec.rowspan.stop].sum() / hr.sum()
        self.bbox_relative.p0 = (x0, y0)
        self.bbox_relative.p1 = (x0 + dx, y0 + dy)

    def get_constrained_layout(self):
        """
        Return whether constrained layout is being used.

        See :ref:`constrainedlayout_guide`.
        """
        return self._parent.get_constrained_layout()

    def get_constrained_layout_pads(self, relative=False):
        """
        Get padding for ``constrained_layout``.

        Returns a list of ``w_pad, h_pad`` in inches and
        ``wspace`` and ``hspace`` as fractions of the subplot.

        See :ref:`constrainedlayout_guide`.

        Parameters
        ----------
        relative : bool
            If `True`, then convert from inches to figure relative.
        """
        return self._parent.get_constrained_layout_pads(relative=relative)

    def get_layout_engine(self):
        return self._parent.get_layout_engine()

    @property
    def axes(self):
        """
        List of Axes in the SubFigure.  You can access and modify the Axes
        in the SubFigure through this list.

        Modifying this list has no effect. Instead, use `~.SubFigure.add_axes`,
        `~.SubFigure.add_subplot` or `~.SubFigure.delaxes` to add or remove an
        Axes.

        Note: The `.SubFigure.axes` property and `~.SubFigure.get_axes` method
        are equivalent.
        """
        return self._localaxes[:]

    get_axes = axes.fget

    def draw(self, renderer):
        # docstring inherited

        # draw the figure bounding box, perhaps none for white figure
        if not self.get_visible():
            return

        artists = self._get_draw_artists(renderer)

        try:
            renderer.open_group('subfigure', gid=self.get_gid())
            self.patch.draw(renderer)
            mimage._draw_list_compositing_images(
                renderer, self, artists, self.get_figure(root=True).suppressComposite)
            renderer.close_group('subfigure')

        finally:
            self.stale = False


@_docstring.interpd
class Figure(FigureBase):
    """
    The top level container for all the plot elements.

    See `matplotlib.figure` for an index of class methods.

    Attributes
    ----------
    patch
        The `.Rectangle` instance representing the figure background patch.

    suppressComposite
        For multiple images, the figure will make composite images
        depending on the renderer option_image_nocomposite function.  If
        *suppressComposite* is a boolean, this will override the renderer.
    """

    # we want to cache the fonts and mathtext at a global level so that when
    # multiple figures are created we can reuse them.  This helps with a bug on
    # windows where the creation of too many figures leads to too many open
    # file handles and improves the performance of parsing mathtext.  However,
    # these global caches are not thread safe.  The solution here is to let the
    # Figure acquire a shared lock at the start of the draw, and release it when it
    # is done.  This allows multiple renderers to share the cached fonts and
    # parsed text, but only one figure can draw at a time and so the font cache
    # and mathtext cache are used by only one renderer at a time.

    _render_lock = threading.RLock()

    def __str__(self):
        return "Figure(%gx%g)" % tuple(self.bbox.size)

    def __repr__(self):
        return "<{clsname} size {h:g}x{w:g} with {naxes} Axes>".format(
            clsname=self.__class__.__name__,
            h=self.bbox.size[0], w=self.bbox.size[1],
            naxes=len(self.axes),
        )

    def __init__(self,
                 figsize=None,
                 dpi=None,
                 *,
                 facecolor=None,
                 edgecolor=None,
                 linewidth=0.0,
                 frameon=None,
                 subplotpars=None,  # rc figure.subplot.*
                 tight_layout=None,  # rc figure.autolayout
                 constrained_layout=None,  # rc figure.constrained_layout.use
                 layout=None,
                 **kwargs
                 ):
        """
        Parameters
        ----------
        figsize : 2-tuple of floats, default: :rc:`figure.figsize`
            Figure dimension ``(width, height)`` in inches.

        dpi : float, default: :rc:`figure.dpi`
            Dots per inch.

        facecolor : default: :rc:`figure.facecolor`
            The figure patch facecolor.

        edgecolor : default: :rc:`figure.edgecolor`
            The figure patch edge color.

        linewidth : float
            The linewidth of the frame (i.e. the edge linewidth of the figure
            patch).

        frameon : bool, default: :rc:`figure.frameon`
            If ``False``, suppress drawing the figure background patch.

        subplotpars : `~matplotlib.gridspec.SubplotParams`
            Subplot parameters. If not given, the default subplot
            parameters :rc:`figure.subplot.*` are used.

        tight_layout : bool or dict, default: :rc:`figure.autolayout`
            Whether to use the tight layout mechanism. See `.set_tight_layout`.

            .. admonition:: Discouraged

                The use of this parameter is discouraged. Please use
                ``layout='tight'`` instead for the common case of
                ``tight_layout=True`` and use `.set_tight_layout` otherwise.

        constrained_layout : bool, default: :rc:`figure.constrained_layout.use`
            This is equal to ``layout='constrained'``.

            .. admonition:: Discouraged

                The use of this parameter is discouraged. Please use
                ``layout='constrained'`` instead.

        layout : {'constrained', 'compressed', 'tight', 'none', `.LayoutEngine`, \
None}, default: None
            The layout mechanism for positioning of plot elements to avoid
            overlapping Axes decorations (labels, ticks, etc). Note that
            layout managers can have significant performance penalties.

            - 'constrained': The constrained layout solver adjusts Axes sizes
              to avoid overlapping Axes decorations.  Can handle complex plot
              layouts and colorbars, and is thus recommended.

              See :ref:`constrainedlayout_guide` for examples.

            - 'compressed': uses the same algorithm as 'constrained', but
              removes extra space between fixed-aspect-ratio Axes.  Best for
              simple grids of Axes.

            - 'tight': Use the tight layout mechanism. This is a relatively
              simple algorithm that adjusts the subplot parameters so that
              decorations do not overlap.

              See :ref:`tight_layout_guide` for examples.

            - 'none': Do not use a layout engine.

            - A `.LayoutEngine` instance. Builtin layout classes are
              `.ConstrainedLayoutEngine` and `.TightLayoutEngine`, more easily
              accessible by 'constrained' and 'tight'.  Passing an instance
              allows third parties to provide their own layout engine.

            If not given, fall back to using the parameters *tight_layout* and
            *constrained_layout*, including their config defaults
            :rc:`figure.autolayout` and :rc:`figure.constrained_layout.use`.

        Other Parameters
        ----------------
        **kwargs : `.Figure` properties, optional

            %(Figure:kwdoc)s
        """
        super().__init__(**kwargs)
        self._root_figure = self
        self._layout_engine = None

        if layout is not None:
            if (tight_layout is not None):
                _api.warn_external(
                    "The Figure parameters 'layout' and 'tight_layout' cannot "
                    "be used together. Please use 'layout' only.")
            if (constrained_layout is not None):
                _api.warn_external(
                    "The Figure parameters 'layout' and 'constrained_layout' "
                    "cannot be used together. Please use 'layout' only.")
            self.set_layout_engine(layout=layout)
        elif tight_layout is not None:
            if constrained_layout is not None:
                _api.warn_external(
                    "The Figure parameters 'tight_layout' and "
                    "'constrained_layout' cannot be used together. Please use "
                    "'layout' parameter")
            self.set_layout_engine(layout='tight')
            if isinstance(tight_layout, dict):
                self.get_layout_engine().set(**tight_layout)
        elif constrained_layout is not None:
            if isinstance(constrained_layout, dict):
                self.set_layout_engine(layout='constrained')
                self.get_layout_engine().set(**constrained_layout)
            elif constrained_layout:
                self.set_layout_engine(layout='constrained')

        else:
            # everything is None, so use default:
            self.set_layout_engine(layout=layout)

        # Callbacks traditionally associated with the canvas (and exposed with
        # a proxy property), but that actually need to be on the figure for
        # pickling.
        self._canvas_callbacks = cbook.CallbackRegistry(
            signals=FigureCanvasBase.events)
        connect = self._canvas_callbacks._connect_picklable
        self._mouse_key_ids = [
            connect('key_press_event', backend_bases._key_handler),
            connect('key_release_event', backend_bases._key_handler),
            connect('key_release_event', backend_bases._key_handler),
            connect('button_press_event', backend_bases._mouse_handler),
            connect('button_release_event', backend_bases._mouse_handler),
            connect('scroll_event', backend_bases._mouse_handler),
            connect('motion_notify_event', backend_bases._mouse_handler),
        ]
        self._button_pick_id = connect('button_press_event', self.pick)
        self._scroll_pick_id = connect('scroll_event', self.pick)

        if figsize is None:
            figsize = mpl.rcParams['figure.figsize']
        if dpi is None:
            dpi = mpl.rcParams['figure.dpi']
        if facecolor is None:
            facecolor = mpl.rcParams['figure.facecolor']
        if edgecolor is None:
            edgecolor = mpl.rcParams['figure.edgecolor']
        if frameon is None:
            frameon = mpl.rcParams['figure.frameon']

        if not np.isfinite(figsize).all() or (np.array(figsize) < 0).any():
            raise ValueError('figure size must be positive finite not '
                             f'{figsize}')
        self.bbox_inches = Bbox.from_bounds(0, 0, *figsize)

        self.dpi_scale_trans = Affine2D().scale(dpi)
        # do not use property as it will trigger
        self._dpi = dpi
        self.bbox = TransformedBbox(self.bbox_inches, self.dpi_scale_trans)
        self.figbbox = self.bbox
        self.transFigure = BboxTransformTo(self.bbox)
        self.transSubfigure = self.transFigure

        self.patch = Rectangle(
            xy=(0, 0), width=1, height=1, visible=frameon,
            facecolor=facecolor, edgecolor=edgecolor, linewidth=linewidth,
            # Don't let the figure patch influence bbox calculation.
            in_layout=False)
        self._set_artist_props(self.patch)
        self.patch.set_antialiased(False)

        FigureCanvasBase(self)  # Set self.canvas.

        if subplotpars is None:
            subplotpars = SubplotParams()

        self.subplotpars = subplotpars

        self._axstack = _AxesStack()  # track all figure Axes and current Axes
        self.clear()

    def pick(self, mouseevent):
        if not self.canvas.widgetlock.locked():
            super().pick(mouseevent)

    def _check_layout_engines_compat(self, old, new):
        """
        Helper for set_layout engine

        If the figure has used the old engine and added a colorbar then the
        value of colorbar_gridspec must be the same on the new engine.
        """
        if old is None or new is None:
            return True
        if old.colorbar_gridspec == new.colorbar_gridspec:
            return True
        # colorbar layout different, so check if any colorbars are on the
        # figure...
        for ax in self.axes:
            if hasattr(ax, '_colorbar'):
                # colorbars list themselves as a colorbar.
                return False
        return True

    def set_layout_engine(self, layout=None, **kwargs):
        """
        Set the layout engine for this figure.

        Parameters
        ----------
        layout : {'constrained', 'compressed', 'tight', 'none', `.LayoutEngine`, None}

            - 'constrained' will use `~.ConstrainedLayoutEngine`
            - 'compressed' will also use `~.ConstrainedLayoutEngine`, but with
              a correction that attempts to make a good layout for fixed-aspect
              ratio Axes.
            - 'tight' uses `~.TightLayoutEngine`
            - 'none' removes layout engine.

            If a `.LayoutEngine` instance, that instance will be used.

            If `None`, the behavior is controlled by :rc:`figure.autolayout`
            (which if `True` behaves as if 'tight' was passed) and
            :rc:`figure.constrained_layout.use` (which if `True` behaves as if
            'constrained' was passed).  If both are `True`,
            :rc:`figure.autolayout` takes priority.

            Users and libraries can define their own layout engines and pass
            the instance directly as well.

        **kwargs
            The keyword arguments are passed to the layout engine to set things
            like padding and margin sizes.  Only used if *layout* is a string.

        """
        if layout is None:
            if mpl.rcParams['figure.autolayout']:
                layout = 'tight'
            elif mpl.rcParams['figure.constrained_layout.use']:
                layout = 'constrained'
            else:
                self._layout_engine = None
                return
        if layout == 'tight':
            new_layout_engine = TightLayoutEngine(**kwargs)
        elif layout == 'constrained':
            new_layout_engine = ConstrainedLayoutEngine(**kwargs)
        elif layout == 'compressed':
            new_layout_engine = ConstrainedLayoutEngine(compress=True,
                                                        **kwargs)
        elif layout == 'none':
            if self._layout_engine is not None:
                new_layout_engine = PlaceHolderLayoutEngine(
                    self._layout_engine.adjust_compatible,
                    self._layout_engine.colorbar_gridspec
                )
            else:
                new_layout_engine = None
        elif isinstance(layout, LayoutEngine):
            new_layout_engine = layout
        else:
            raise ValueError(f"Invalid value for 'layout': {layout!r}")

        if self._check_layout_engines_compat(self._layout_engine,
                                             new_layout_engine):
            self._layout_engine = new_layout_engine
        else:
            raise RuntimeError('Colorbar layout of new layout engine not '
                               'compatible with old engine, and a colorbar '
                               'has been created.  Engine not changed.')

    def get_layout_engine(self):
        return self._layout_engine

    # TODO: I'd like to dynamically add the _repr_html_ method
    # to the figure in the right context, but then IPython doesn't
    # use it, for some reason.

    def _repr_html_(self):
        # We can't use "isinstance" here, because then we'd end up importing
        # webagg unconditionally.
        if 'WebAgg' in type(self.canvas).__name__:
            from matplotlib.backends import backend_webagg
            return backend_webagg.ipython_inline_display(self)

    def show(self, warn=True):
        """
        If using a GUI backend with pyplot, display the figure window.

        If the figure was not created using `~.pyplot.figure`, it will lack
        a `~.backend_bases.FigureManagerBase`, and this method will raise an
        AttributeError.

        .. warning::

            This does not manage an GUI event loop. Consequently, the figure
            may only be shown briefly or not shown at all if you or your
            environment are not managing an event loop.

            Use cases for `.Figure.show` include running this from a GUI
            application (where there is persistently an event loop running) or
            from a shell, like IPython, that install an input hook to allow the
            interactive shell to accept input while the figure is also being
            shown and interactive.  Some, but not all, GUI toolkits will
            register an input hook on import.  See :ref:`cp_integration` for
            more details.

            If you're in a shell without input hook integration or executing a
            python script, you should use `matplotlib.pyplot.show` with
            ``block=True`` instead, which takes care of starting and running
            the event loop for you.

        Parameters
        ----------
        warn : bool, default: True
            If ``True`` and we are not running headless (i.e. on Linux with an
            unset DISPLAY), issue warning when called on a non-GUI backend.

        """
        if self.canvas.manager is None:
            raise AttributeError(
                "Figure.show works only for figures managed by pyplot, "
                "normally created by pyplot.figure()")
        try:
            self.canvas.manager.show()
        except NonGuiException as exc:
            if warn:
                _api.warn_external(str(exc))

    @property
    def axes(self):
        """
        List of Axes in the Figure. You can access and modify the Axes in the
        Figure through this list.

        Do not modify the list itself. Instead, use `~Figure.add_axes`,
        `~.Figure.add_subplot` or `~.Figure.delaxes` to add or remove an Axes.

        Note: The `.Figure.axes` property and `~.Figure.get_axes` method are
        equivalent.
        """
        return self._axstack.as_list()

    get_axes = axes.fget

    @property
    def number(self):
        """The figure id, used to identify figures in `.pyplot`."""
        # Historically, pyplot dynamically added a number attribute to figure.
        # However, this number must stay in sync with the figure manager.
        # AFAICS overwriting the number attribute does not have the desired
        # effect for pyplot. But there are some repos in GitHub that do change
        # number. So let's take it slow and properly migrate away from writing.
        #
        # Making the dynamic attribute private and wrapping it in a property
        # allows to maintain current behavior and deprecate write-access.
        #
        # When the deprecation expires, there's no need for duplicate state
        # anymore and the private _number attribute can be replaced by
        # `self.canvas.manager.num` if that exists and None otherwise.
        if hasattr(self, '_number'):
            return self._number
        else:
            raise AttributeError(
                "'Figure' object has no attribute 'number'. In the future this"
                "will change to returning 'None' instead.")

    @number.setter
    def number(self, num):
        _api.warn_deprecated(
            "3.10",
            message="Changing 'Figure.number' is deprecated since %(since)s and "
                    "will raise an error starting %(removal)s")
        self._number = num

    def _get_renderer(self):
        if hasattr(self.canvas, 'get_renderer'):
            return self.canvas.get_renderer()
        else:
            return _get_renderer(self)

    def _get_dpi(self):
        return self._dpi

    def _set_dpi(self, dpi, forward=True):
        """
        Parameters
        ----------
        dpi : float

        forward : bool
            Passed on to `~.Figure.set_size_inches`
        """
        if dpi == self._dpi:
            # We don't want to cause undue events in backends.
            return
        self._dpi = dpi
        self.dpi_scale_trans.clear().scale(dpi)
        w, h = self.get_size_inches()
        self.set_size_inches(w, h, forward=forward)

    dpi = property(_get_dpi, _set_dpi, doc="The resolution in dots per inch.")

    def get_tight_layout(self):
        """Return whether `.Figure.tight_layout` is called when drawing."""
        return isinstance(self.get_layout_engine(), TightLayoutEngine)

    @_api.deprecated("3.6", alternative="set_layout_engine",
                     pending=True)
    def set_tight_layout(self, tight):
        """
        Set whether and how `.Figure.tight_layout` is called when drawing.

        Parameters
        ----------
        tight : bool or dict with keys "pad", "w_pad", "h_pad", "rect" or None
            If a bool, sets whether to call `.Figure.tight_layout` upon drawing.
            If ``None``, use :rc:`figure.autolayout` instead.
            If a dict, pass it as kwargs to `.Figure.tight_layout`, overriding the
            default paddings.
        """
        if tight is None:
            tight = mpl.rcParams['figure.autolayout']
        _tight = 'tight' if bool(tight) else 'none'
        _tight_parameters = tight if isinstance(tight, dict) else {}
        self.set_layout_engine(_tight, **_tight_parameters)
        self.stale = True

    def get_constrained_layout(self):
        """
        Return whether constrained layout is being used.

        See :ref:`constrainedlayout_guide`.
        """
        return isinstance(self.get_layout_engine(), ConstrainedLayoutEngine)

    @_api.deprecated("3.6", alternative="set_layout_engine('constrained')",
                     pending=True)
    def set_constrained_layout(self, constrained):
        """
        Set whether ``constrained_layout`` is used upon drawing.

        If None, :rc:`figure.constrained_layout.use` value will be used.

        When providing a dict containing the keys ``w_pad``, ``h_pad``
        the default ``constrained_layout`` paddings will be
        overridden.  These pads are in inches and default to 3.0/72.0.
        ``w_pad`` is the width padding and ``h_pad`` is the height padding.

        Parameters
        ----------
        constrained : bool or dict or None
        """
        if constrained is None:
            constrained = mpl.rcParams['figure.constrained_layout.use']
        _constrained = 'constrained' if bool(constrained) else 'none'
        _parameters = constrained if isinstance(constrained, dict) else {}
        self.set_layout_engine(_constrained, **_parameters)
        self.stale = True

    @_api.deprecated(
         "3.6", alternative="figure.get_layout_engine().set()",
         pending=True)
    def set_constrained_layout_pads(self, **kwargs):
        """
        Set padding for ``constrained_layout``.

        Tip: The parameters can be passed from a dictionary by using
        ``fig.set_constrained_layout(**pad_dict)``.

        See :ref:`constrainedlayout_guide`.

        Parameters
        ----------
        w_pad : float, default: :rc:`figure.constrained_layout.w_pad`
            Width padding in inches.  This is the pad around Axes
            and is meant to make sure there is enough room for fonts to
            look good.  Defaults to 3 pts = 0.04167 inches

        h_pad : float, default: :rc:`figure.constrained_layout.h_pad`
            Height padding in inches. Defaults to 3 pts.

        wspace : float, default: :rc:`figure.constrained_layout.wspace`
            Width padding between subplots, expressed as a fraction of the
            subplot width.  The total padding ends up being w_pad + wspace.

        hspace : float, default: :rc:`figure.constrained_layout.hspace`
            Height padding between subplots, expressed as a fraction of the
            subplot width. The total padding ends up being h_pad + hspace.

        """
        if isinstance(self.get_layout_engine(), ConstrainedLayoutEngine):
            self.get_layout_engine().set(**kwargs)

    @_api.deprecated("3.6", alternative="fig.get_layout_engine().get()",
                     pending=True)
    def get_constrained_layout_pads(self, relative=False):
        """
        Get padding for ``constrained_layout``.

        Returns a list of ``w_pad, h_pad`` in inches and
        ``wspace`` and ``hspace`` as fractions of the subplot.
        All values are None if ``constrained_layout`` is not used.

        See :ref:`constrainedlayout_guide`.

        Parameters
        ----------
        relative : bool
            If `True`, then convert from inches to figure relative.
        """
        if not isinstance(self.get_layout_engine(), ConstrainedLayoutEngine):
            return None, None, None, None
        info = self.get_layout_engine().get()
        w_pad = info['w_pad']
        h_pad = info['h_pad']
        wspace = info['wspace']
        hspace = info['hspace']

        if relative and (w_pad is not None or h_pad is not None):
            renderer = self._get_renderer()
            dpi = renderer.dpi
            w_pad = w_pad * dpi / renderer.width
            h_pad = h_pad * dpi / renderer.height

        return w_pad, h_pad, wspace, hspace

    def set_canvas(self, canvas):
        """
        Set the canvas that contains the figure

        Parameters
        ----------
        canvas : FigureCanvas
        """
        self.canvas = canvas

    @_docstring.interpd
    def figimage(self, X, xo=0, yo=0, alpha=None, norm=None, cmap=None,
                 vmin=None, vmax=None, origin=None, resize=False, *,
                 colorizer=None, **kwargs):
        """
        Add a non-resampled image to the figure.

        The image is attached to the lower or upper left corner depending on
        *origin*.

        Parameters
        ----------
        X
            The image data. This is an array of one of the following shapes:

            - (M, N): an image with scalar data.  Color-mapping is controlled
              by *cmap*, *norm*, *vmin*, and *vmax*.
            - (M, N, 3): an image with RGB values (0-1 float or 0-255 int).
            - (M, N, 4): an image with RGBA values (0-1 float or 0-255 int),
              i.e. including transparency.

        xo, yo : int
            The *x*/*y* image offset in pixels.

        alpha : None or float
            The alpha blending value.

        %(cmap_doc)s

            This parameter is ignored if *X* is RGB(A).

        %(norm_doc)s

            This parameter is ignored if *X* is RGB(A).

        %(vmin_vmax_doc)s

            This parameter is ignored if *X* is RGB(A).

        origin : {'upper', 'lower'}, default: :rc:`image.origin`
            Indicates where the [0, 0] index of the array is in the upper left
            or lower left corner of the Axes.

        resize : bool
            If *True*, resize the figure to match the given image size.

        %(colorizer_doc)s

            This parameter is ignored if *X* is RGB(A).

        Returns
        -------
        `matplotlib.image.FigureImage`

        Other Parameters
        ----------------
        **kwargs
            Additional kwargs are `.Artist` kwargs passed on to `.FigureImage`.

        Notes
        -----
        figimage complements the Axes image (`~matplotlib.axes.Axes.imshow`)
        which will be resampled to fit the current Axes.  If you want
        a resampled image to fill the entire figure, you can define an
        `~matplotlib.axes.Axes` with extent [0, 0, 1, 1].

        Examples
        --------
        ::

            f = plt.figure()
            nx = int(f.get_figwidth() * f.dpi)
            ny = int(f.get_figheight() * f.dpi)
            data = np.random.random((ny, nx))
            f.figimage(data)
            plt.show()
        """
        if resize:
            dpi = self.get_dpi()
            figsize = [x / dpi for x in (X.shape[1], X.shape[0])]
            self.set_size_inches(figsize, forward=True)

        im = mimage.FigureImage(self, cmap=cmap, norm=norm,
                                colorizer=colorizer,
                                offsetx=xo, offsety=yo,
                                origin=origin, **kwargs)
        im.stale_callback = _stale_figure_callback

        im.set_array(X)
        im.set_alpha(alpha)
        if norm is None:
            im._check_exclusionary_keywords(colorizer, vmin=vmin, vmax=vmax)
            im.set_clim(vmin, vmax)
        self.images.append(im)
        im._remove_method = self.images.remove
        self.stale = True
        return im

    def set_size_inches(self, w, h=None, forward=True):
        """
        Set the figure size in inches.

        Call signatures::

             fig.set_size_inches(w, h)  # OR
             fig.set_size_inches((w, h))

        Parameters
        ----------
        w : (float, float) or float
            Width and height in inches (if height not specified as a separate
            argument) or width.
        h : float
            Height in inches.
        forward : bool, default: True
            If ``True``, the canvas size is automatically updated, e.g.,
            you can resize the figure window from the shell.

        See Also
        --------
        matplotlib.figure.Figure.get_size_inches
        matplotlib.figure.Figure.set_figwidth
        matplotlib.figure.Figure.set_figheight

        Notes
        -----
        To transform from pixels to inches divide by `Figure.dpi`.
        """
        if h is None:  # Got called with a single pair as argument.
            w, h = w
        size = np.array([w, h])
        if not np.isfinite(size).all() or (size < 0).any():
            raise ValueError(f'figure size must be positive finite not {size}')
        self.bbox_inches.p1 = size
        if forward:
            manager = self.canvas.manager
            if manager is not None:
                manager.resize(*(size * self.dpi).astype(int))
        self.stale = True

    def get_size_inches(self):
        """
        Return the current size of the figure in inches.

        Returns
        -------
        ndarray
           The size (width, height) of the figure in inches.

        See Also
        --------
        matplotlib.figure.Figure.set_size_inches
        matplotlib.figure.Figure.get_figwidth
        matplotlib.figure.Figure.get_figheight

        Notes
        -----
        The size in pixels can be obtained by multiplying with `Figure.dpi`.
        """
        return np.array(self.bbox_inches.p1)

    def get_figwidth(self):
        """Return the figure width in inches."""
        return self.bbox_inches.width

    def get_figheight(self):
        """Return the figure height in inches."""
        return self.bbox_inches.height

    def get_dpi(self):
        """Return the resolution in dots per inch as a float."""
        return self.dpi

    def set_dpi(self, val):
        """
        Set the resolution of the figure in dots-per-inch.

        Parameters
        ----------
        val : float
        """
        self.dpi = val
        self.stale = True

    def set_figwidth(self, val, forward=True):
        """
        Set the width of the figure in inches.

        Parameters
        ----------
        val : float
        forward : bool
            See `set_size_inches`.

        See Also
        --------
        matplotlib.figure.Figure.set_figheight
        matplotlib.figure.Figure.set_size_inches
        """
        self.set_size_inches(val, self.get_figheight(), forward=forward)

    def set_figheight(self, val, forward=True):
        """
        Set the height of the figure in inches.

        Parameters
        ----------
        val : float
        forward : bool
            See `set_size_inches`.

        See Also
        --------
        matplotlib.figure.Figure.set_figwidth
        matplotlib.figure.Figure.set_size_inches
        """
        self.set_size_inches(self.get_figwidth(), val, forward=forward)

    def clear(self, keep_observers=False):
        # docstring inherited
        super().clear(keep_observers=keep_observers)
        # FigureBase.clear does not clear toolbars, as
        # only Figure can have toolbars
        toolbar = self.canvas.toolbar
        if toolbar is not None:
            toolbar.update()

    @_finalize_rasterization
    @allow_rasterization
    def draw(self, renderer):
        # docstring inherited
        if not self.get_visible():
            return

        with self._render_lock:

            artists = self._get_draw_artists(renderer)
            try:
                renderer.open_group('figure', gid=self.get_gid())
                if self.axes and self.get_layout_engine() is not None:
                    try:
                        self.get_layout_engine().execute(self)
                    except ValueError:
                        pass
                        # ValueError can occur when resizing a window.

                self.patch.draw(renderer)
                mimage._draw_list_compositing_images(
                    renderer, self, artists, self.suppressComposite)

                renderer.close_group('figure')
            finally:
                self.stale = False

            DrawEvent("draw_event", self.canvas, renderer)._process()

    def draw_without_rendering(self):
        """
        Draw the figure with no output.  Useful to get the final size of
        artists that require a draw before their size is known (e.g. text).
        """
        renderer = _get_renderer(self)
        with renderer._draw_disabled():
            self.draw(renderer)

    def draw_artist(self, a):
        """
        Draw `.Artist` *a* only.
        """
        a.draw(self.canvas.get_renderer())

    def __getstate__(self):
        state = super().__getstate__()

        # The canvas cannot currently be pickled, but this has the benefit
        # of meaning that a figure can be detached from one canvas, and
        # re-attached to another.
        state.pop("canvas")

        # discard any changes to the dpi due to pixel ratio changes
        state["_dpi"] = state.get('_original_dpi', state['_dpi'])

        # add version information to the state
        state['__mpl_version__'] = mpl.__version__

        # check whether the figure manager (if any) is registered with pyplot
        from matplotlib import _pylab_helpers
        if self.canvas.manager in _pylab_helpers.Gcf.figs.values():
            state['_restore_to_pylab'] = True
        return state

    def __setstate__(self, state):
        version = state.pop('__mpl_version__')
        restore_to_pylab = state.pop('_restore_to_pylab', False)

        if version != mpl.__version__:
            _api.warn_external(
                f"This figure was saved with matplotlib version {version} and "
                f"loaded with {mpl.__version__} so may not function correctly."
            )
        self.__dict__ = state

        # re-initialise some of the unstored state information
        FigureCanvasBase(self)  # Set self.canvas.

        if restore_to_pylab:
            # lazy import to avoid circularity
            import matplotlib.pyplot as plt
            import matplotlib._pylab_helpers as pylab_helpers
            allnums = plt.get_fignums()
            num = max(allnums) + 1 if allnums else 1
            backend = plt._get_backend_mod()
            mgr = backend.new_figure_manager_given_figure(num, self)
            pylab_helpers.Gcf._set_new_active_manager(mgr)
            plt.draw_if_interactive()

        self.stale = True

    def add_axobserver(self, func):
        """Whenever the Axes state change, ``func(self)`` will be called."""
        # Connect a wrapper lambda and not func itself, to avoid it being
        # weakref-collected.
        self._axobservers.connect("_axes_change_event", lambda arg: func(arg))

    def savefig(self, fname, *, transparent=None, **kwargs):
        """
        Save the current figure as an image or vector graphic to a file.

        Call signature::

          savefig(fname, *, transparent=None, dpi='figure', format=None,
                  metadata=None, bbox_inches=None, pad_inches=0.1,
                  facecolor='auto', edgecolor='auto', backend=None,
                  **kwargs
                 )

        The available output formats depend on the backend being used.

        Parameters
        ----------
        fname : str or path-like or binary file-like
            A path, or a Python file-like object, or
            possibly some backend-dependent object such as
            `matplotlib.backends.backend_pdf.PdfPages`.

            If *format* is set, it determines the output format, and the file
            is saved as *fname*.  Note that *fname* is used verbatim, and there
            is no attempt to make the extension, if any, of *fname* match
            *format*, and no extension is appended.

            If *format* is not set, then the format is inferred from the
            extension of *fname*, if there is one.  If *format* is not
            set and *fname* has no extension, then the file is saved with
            :rc:`savefig.format` and the appropriate extension is appended to
            *fname*.

        Other Parameters
        ----------------
        transparent : bool, default: :rc:`savefig.transparent`
            If *True*, the Axes patches will all be transparent; the
            Figure patch will also be transparent unless *facecolor*
            and/or *edgecolor* are specified via kwargs.

            If *False* has no effect and the color of the Axes and
            Figure patches are unchanged (unless the Figure patch
            is specified via the *facecolor* and/or *edgecolor* keyword
            arguments in which case those colors are used).

            The transparency of these patches will be restored to their
            original values upon exit of this function.

            This is useful, for example, for displaying
            a plot on top of a colored background on a web page.

        dpi : float or 'figure', default: :rc:`savefig.dpi`
            The resolution in dots per inch.  If 'figure', use the figure's
            dpi value.

        format : str
            The file format, e.g. 'png', 'pdf', 'svg', ... The behavior when
            this is unset is documented under *fname*.

        metadata : dict, optional
            Key/value pairs to store in the image metadata. The supported keys
            and defaults depend on the image format and backend:

            - 'png' with Agg backend: See the parameter ``metadata`` of
              `~.FigureCanvasAgg.print_png`.
            - 'pdf' with pdf backend: See the parameter ``metadata`` of
              `~.backend_pdf.PdfPages`.
            - 'svg' with svg backend: See the parameter ``metadata`` of
              `~.FigureCanvasSVG.print_svg`.
            - 'eps' and 'ps' with PS backend: Only 'Creator' is supported.

            Not supported for 'pgf', 'raw', and 'rgba' as those formats do not support
            embedding metadata.
            Does not currently support 'jpg', 'tiff', or 'webp', but may include
            embedding EXIF metadata in the future.

        bbox_inches : str or `.Bbox`, default: :rc:`savefig.bbox`
            Bounding box in inches: only the given portion of the figure is
            saved.  If 'tight', try to figure out the tight bbox of the figure.

        pad_inches : float or 'layout', default: :rc:`savefig.pad_inches`
            Amount of padding in inches around the figure when bbox_inches is
            'tight'. If 'layout' use the padding from the constrained or
            compressed layout engine; ignored if one of those engines is not in
            use.

        facecolor : :mpltype:`color` or 'auto', default: :rc:`savefig.facecolor`
            The facecolor of the figure.  If 'auto', use the current figure
            facecolor.

        edgecolor : :mpltype:`color` or 'auto', default: :rc:`savefig.edgecolor`
            The edgecolor of the figure.  If 'auto', use the current figure
            edgecolor.

        backend : str, optional
            Use a non-default backend to render the file, e.g. to render a
            png file with the "cairo" backend rather than the default "agg",
            or a pdf file with the "pgf" backend rather than the default
            "pdf".  Note that the default backend is normally sufficient.  See
            :ref:`the-builtin-backends` for a list of valid backends for each
            file format.  Custom backends can be referenced as "module://...".

        orientation : {'landscape', 'portrait'}
            Currently only supported by the postscript backend.

        papertype : str
            One of 'letter', 'legal', 'executive', 'ledger', 'a0' through
            'a10', 'b0' through 'b10'. Only supported for postscript
            output.

        bbox_extra_artists : list of `~matplotlib.artist.Artist`, optional
            A list of extra artists that will be considered when the
            tight bbox is calculated.

        pil_kwargs : dict, optional
            Additional keyword arguments that are passed to
            `PIL.Image.Image.save` when saving the figure.

        """

        kwargs.setdefault('dpi', mpl.rcParams['savefig.dpi'])
        if transparent is None:
            transparent = mpl.rcParams['savefig.transparent']

        with ExitStack() as stack:
            if transparent:
                def _recursively_make_subfig_transparent(exit_stack, subfig):
                    exit_stack.enter_context(
                        subfig.patch._cm_set(
                            facecolor="none", edgecolor="none"))
                    for ax in subfig.axes:
                        exit_stack.enter_context(
                            ax.patch._cm_set(
                                facecolor="none", edgecolor="none"))
                    for sub_subfig in subfig.subfigs:
                        _recursively_make_subfig_transparent(
                            exit_stack, sub_subfig)

                def _recursively_make_axes_transparent(exit_stack, ax):
                    exit_stack.enter_context(
                        ax.patch._cm_set(facecolor="none", edgecolor="none"))
                    for child_ax in ax.child_axes:
                        exit_stack.enter_context(
                            child_ax.patch._cm_set(
                                facecolor="none", edgecolor="none"))
                    for child_childax in ax.child_axes:
                        _recursively_make_axes_transparent(
                            exit_stack, child_childax)

                kwargs.setdefault('facecolor', 'none')
                kwargs.setdefault('edgecolor', 'none')
                # set subfigure to appear transparent in printed image
                for subfig in self.subfigs:
                    _recursively_make_subfig_transparent(stack, subfig)
                # set Axes to be transparent
                for ax in self.axes:
                    _recursively_make_axes_transparent(stack, ax)
            self.canvas.print_figure(fname, **kwargs)

    def ginput(self, n=1, timeout=30, show_clicks=True,
               mouse_add=MouseButton.LEFT,
               mouse_pop=MouseButton.RIGHT,
               mouse_stop=MouseButton.MIDDLE):
        """
        Blocking call to interact with a figure.

        Wait until the user clicks *n* times on the figure, and return the
        coordinates of each click in a list.

        There are three possible interactions:

        - Add a point.
        - Remove the most recently added point.
        - Stop the interaction and return the points added so far.

        The actions are assigned to mouse buttons via the arguments
        *mouse_add*, *mouse_pop* and *mouse_stop*.

        Parameters
        ----------
        n : int, default: 1
            Number of mouse clicks to accumulate. If negative, accumulate
            clicks until the input is terminated manually.
        timeout : float, default: 30 seconds
            Number of seconds to wait before timing out. If zero or negative
            will never time out.
        show_clicks : bool, default: True
            If True, show a red cross at the location of each click.
        mouse_add : `.MouseButton` or None, default: `.MouseButton.LEFT`
            Mouse button used to add points.
        mouse_pop : `.MouseButton` or None, default: `.MouseButton.RIGHT`
            Mouse button used to remove the most recently added point.
        mouse_stop : `.MouseButton` or None, default: `.MouseButton.MIDDLE`
            Mouse button used to stop input.

        Returns
        -------
        list of tuples
            A list of the clicked (x, y) coordinates.

        Notes
        -----
        The keyboard can also be used to select points in case your mouse
        does not have one or more of the buttons.  The delete and backspace
        keys act like right-clicking (i.e., remove last point), the enter key
        terminates input and any other key (not already used by the window
        manager) selects a point.
        """
        clicks = []
        marks = []

        def handler(event):
            is_button = event.name == "button_press_event"
            is_key = event.name == "key_press_event"
            # Quit (even if not in infinite mode; this is consistent with
            # MATLAB and sometimes quite useful, but will require the user to
            # test how many points were actually returned before using data).
            if (is_button and event.button == mouse_stop
                    or is_key and event.key in ["escape", "enter"]):
                self.canvas.stop_event_loop()
            # Pop last click.
            elif (is_button and event.button == mouse_pop
                  or is_key and event.key in ["backspace", "delete"]):
                if clicks:
                    clicks.pop()
                    if show_clicks:
                        marks.pop().remove()
                        self.canvas.draw()
            # Add new click.
            elif (is_button and event.button == mouse_add
                  # On macOS/gtk, some keys return None.
                  or is_key and event.key is not None):
                if event.inaxes:
                    clicks.append((event.xdata, event.ydata))
                    _log.info("input %i: %f, %f",
                              len(clicks), event.xdata, event.ydata)
                    if show_clicks:
                        line = mpl.lines.Line2D([event.xdata], [event.ydata],
                                                marker="+", color="r")
                        event.inaxes.add_line(line)
                        marks.append(line)
                        self.canvas.draw()
            if len(clicks) == n and n > 0:
                self.canvas.stop_event_loop()

        _blocking_input.blocking_input_loop(
            self, ["button_press_event", "key_press_event"], timeout, handler)

        # Cleanup.
        for mark in marks:
            mark.remove()
        self.canvas.draw()

        return clicks

    def waitforbuttonpress(self, timeout=-1):
        """
        Blocking call to interact with the figure.

        Wait for user input and return True if a key was pressed, False if a
        mouse button was pressed and None if no input was given within
        *timeout* seconds.  Negative values deactivate *timeout*.
        """
        event = None

        def handler(ev):
            nonlocal event
            event = ev
            self.canvas.stop_event_loop()

        _blocking_input.blocking_input_loop(
            self, ["button_press_event", "key_press_event"], timeout, handler)

        return None if event is None else event.name == "key_press_event"

    def tight_layout(self, *, pad=1.08, h_pad=None, w_pad=None, rect=None):
        """
        Adjust the padding between and around subplots.

        To exclude an artist on the Axes from the bounding box calculation
        that determines the subplot parameters (i.e. legend, or annotation),
        set ``a.set_in_layout(False)`` for that artist.

        Parameters
        ----------
        pad : float, default: 1.08
            Padding between the figure edge and the edges of subplots,
            as a fraction of the font size.
        h_pad, w_pad : float, default: *pad*
            Padding (height/width) between edges of adjacent subplots,
            as a fraction of the font size.
        rect : tuple (left, bottom, right, top), default: (0, 0, 1, 1)
            A rectangle in normalized figure coordinates into which the whole
            subplots area (including labels) will fit.

        See Also
        --------
        .Figure.set_layout_engine
        .pyplot.tight_layout
        """
        # note that here we do not permanently set the figures engine to
        # tight_layout but rather just perform the layout in place and remove
        # any previous engines.
        engine = TightLayoutEngine(pad=pad, h_pad=h_pad, w_pad=w_pad, rect=rect)
        try:
            previous_engine = self.get_layout_engine()
            self.set_layout_engine(engine)
            engine.execute(self)
            if previous_engine is not None and not isinstance(
                previous_engine, (TightLayoutEngine, PlaceHolderLayoutEngine)
            ):
                _api.warn_external('The figure layout has changed to tight')
        finally:
            self.set_layout_engine('none')


def figaspect(arg):
    """
    Calculate the width and height for a figure with a specified aspect ratio.

    While the height is taken from :rc:`figure.figsize`, the width is
    adjusted to match the desired aspect ratio. Additionally, it is ensured
    that the width is in the range [4., 16.] and the height is in the range
    [2., 16.]. If necessary, the default height is adjusted to ensure this.

    Parameters
    ----------
    arg : float or 2D array
        If a float, this defines the aspect ratio (i.e. the ratio height /
        width).
        In case of an array the aspect ratio is number of rows / number of
        columns, so that the array could be fitted in the figure undistorted.

    Returns
    -------
    size : (2,) array
        The width and height of the figure in inches.

    Notes
    -----
    If you want to create an Axes within the figure, that still preserves the
    aspect ratio, be sure to create it with equal width and height. See
    examples below.

    Thanks to Fernando Perez for this function.

    Examples
    --------
    Make a figure twice as tall as it is wide::

        w, h = figaspect(2.)
        fig = Figure(figsize=(w, h))
        ax = fig.add_axes([0.1, 0.1, 0.8, 0.8])
        ax.imshow(A, **kwargs)

    Make a figure with the proper aspect for an array::

        A = rand(5, 3)
        w, h = figaspect(A)
        fig = Figure(figsize=(w, h))
        ax = fig.add_axes([0.1, 0.1, 0.8, 0.8])
        ax.imshow(A, **kwargs)
    """

    isarray = hasattr(arg, 'shape') and not np.isscalar(arg)

    # min/max sizes to respect when autoscaling.  If John likes the idea, they
    # could become rc parameters, for now they're hardwired.
    figsize_min = np.array((4.0, 2.0))  # min length for width/height
    figsize_max = np.array((16.0, 16.0))  # max length for width/height

    # Extract the aspect ratio of the array
    if isarray:
        nr, nc = arg.shape[:2]
        arr_ratio = nr / nc
    else:
        arr_ratio = arg

    # Height of user figure defaults
    fig_height = mpl.rcParams['figure.figsize'][1]

    # New size for the figure, keeping the aspect ratio of the caller
    newsize = np.array((fig_height / arr_ratio, fig_height))

    # Sanity checks, don't drop either dimension below figsize_min
    newsize /= min(1.0, *(newsize / figsize_min))

    # Avoid humongous windows as well
    newsize /= max(1.0, *(newsize / figsize_max))

    # Finally, if we have a really funky aspect ratio, break it but respect
    # the min/max dimensions (we don't want figures 10 feet tall!)
    newsize = np.clip(newsize, figsize_min, figsize_max)
    return newsize

# === NexusCore/openenv\Lib\site-packages\numpy\f2py\crackfortran.py ===
"""
crackfortran --- read fortran (77,90) code and extract declaration information.

Copyright 1999 -- 2011 Pearu Peterson all rights reserved.
Copyright 2011 -- present NumPy Developers.
Permission to use, modify, and distribute this software is given under the
terms of the NumPy License.

NO WARRANTY IS EXPRESSED OR IMPLIED.  USE AT YOUR OWN RISK.


Usage of crackfortran:
======================
Command line keys: -quiet,-verbose,-fix,-f77,-f90,-show,-h <pyffilename>
                   -m <module name for f77 routines>,--ignore-contains
Functions: crackfortran, crack2fortran
The following Fortran statements/constructions are supported
(or will be if needed):
   block data,byte,call,character,common,complex,contains,data,
   dimension,double complex,double precision,end,external,function,
   implicit,integer,intent,interface,intrinsic,
   logical,module,optional,parameter,private,public,
   program,real,(sequence?),subroutine,type,use,virtual,
   include,pythonmodule
Note: 'virtual' is mapped to 'dimension'.
Note: 'implicit integer (z) static (z)' is 'implicit static (z)' (this is minor bug).
Note: code after 'contains' will be ignored until its scope ends.
Note: 'common' statement is extended: dimensions are moved to variable definitions
Note: f2py directive: <commentchar>f2py<line> is read as <line>
Note: pythonmodule is introduced to represent Python module

Usage:
  `postlist=crackfortran(files)`
  `postlist` contains declaration information read from the list of files `files`.
  `crack2fortran(postlist)` returns a fortran code to be saved to pyf-file

  `postlist` has the following structure:
 *** it is a list of dictionaries containing `blocks':
     B = {'block','body','vars','parent_block'[,'name','prefix','args','result',
          'implicit','externals','interfaced','common','sortvars',
          'commonvars','note']}
     B['block'] = 'interface' | 'function' | 'subroutine' | 'module' |
                  'program' | 'block data' | 'type' | 'pythonmodule' |
                  'abstract interface'
     B['body'] --- list containing `subblocks' with the same structure as `blocks'
     B['parent_block'] --- dictionary of a parent block:
                             C['body'][<index>]['parent_block'] is C
     B['vars'] --- dictionary of variable definitions
     B['sortvars'] --- dictionary of variable definitions sorted by dependence (independent first)
     B['name'] --- name of the block (not if B['block']=='interface')
     B['prefix'] --- prefix string (only if B['block']=='function')
     B['args'] --- list of argument names if B['block']== 'function' | 'subroutine'
     B['result'] --- name of the return value (only if B['block']=='function')
     B['implicit'] --- dictionary {'a':<variable definition>,'b':...} | None
     B['externals'] --- list of variables being external
     B['interfaced'] --- list of variables being external and defined
     B['common'] --- dictionary of common blocks (list of objects)
     B['commonvars'] --- list of variables used in common blocks (dimensions are moved to variable definitions)
     B['from'] --- string showing the 'parents' of the current block
     B['use'] --- dictionary of modules used in current block:
         {<modulename>:{['only':<0|1>],['map':{<local_name1>:<use_name1>,...}]}}
     B['note'] --- list of LaTeX comments on the block
     B['f2pyenhancements'] --- optional dictionary
          {'threadsafe':'','fortranname':<name>,
           'callstatement':<C-expr>|<multi-line block>,
           'callprotoargument':<C-expr-list>,
           'usercode':<multi-line block>|<list of multi-line blocks>,
           'pymethoddef:<multi-line block>'
           }
     B['entry'] --- dictionary {entryname:argslist,..}
     B['varnames'] --- list of variable names given in the order of reading the
                       Fortran code, useful for derived types.
     B['saved_interface'] --- a string of scanned routine signature, defines explicit interface
 *** Variable definition is a dictionary
     D = B['vars'][<variable name>] =
     {'typespec'[,'attrspec','kindselector','charselector','=','typename']}
     D['typespec'] = 'byte' | 'character' | 'complex' | 'double complex' |
                     'double precision' | 'integer' | 'logical' | 'real' | 'type'
     D['attrspec'] --- list of attributes (e.g. 'dimension(<arrayspec>)',
                       'external','intent(in|out|inout|hide|c|callback|cache|aligned4|aligned8|aligned16)',
                       'optional','required', etc)
     K = D['kindselector'] = {['*','kind']} (only if D['typespec'] =
                         'complex' | 'integer' | 'logical' | 'real' )
     C = D['charselector'] = {['*','len','kind','f2py_len']}
                             (only if D['typespec']=='character')
     D['='] --- initialization expression string
     D['typename'] --- name of the type if D['typespec']=='type'
     D['dimension'] --- list of dimension bounds
     D['intent'] --- list of intent specifications
     D['depend'] --- list of variable names on which current variable depends on
     D['check'] --- list of C-expressions; if C-expr returns zero, exception is raised
     D['note'] --- list of LaTeX comments on the variable
 *** Meaning of kind/char selectors (few examples):
     D['typespec>']*K['*']
     D['typespec'](kind=K['kind'])
     character*C['*']
     character(len=C['len'],kind=C['kind'], f2py_len=C['f2py_len'])
     (see also fortran type declaration statement formats below)

Fortran 90 type declaration statement format (F77 is subset of F90)
====================================================================
(Main source: IBM XL Fortran 5.1 Language Reference Manual)
type declaration = <typespec> [[<attrspec>]::] <entitydecl>
<typespec> = byte                          |
             character[<charselector>]     |
             complex[<kindselector>]       |
             double complex                |
             double precision              |
             integer[<kindselector>]       |
             logical[<kindselector>]       |
             real[<kindselector>]          |
             type(<typename>)
<charselector> = * <charlen>               |
             ([len=]<len>[,[kind=]<kind>]) |
             (kind=<kind>[,len=<len>])
<kindselector> = * <intlen>                |
             ([kind=]<kind>)
<attrspec> = comma separated list of attributes.
             Only the following attributes are used in
             building up the interface:
                external
                (parameter --- affects '=' key)
                optional
                intent
             Other attributes are ignored.
<intentspec> = in | out | inout
<arrayspec> = comma separated list of dimension bounds.
<entitydecl> = <name> [[*<charlen>][(<arrayspec>)] | [(<arrayspec>)]*<charlen>]
                      [/<init_expr>/ | =<init_expr>] [,<entitydecl>]

In addition, the following attributes are used: check,depend,note

TODO:
    * Apply 'parameter' attribute (e.g. 'integer parameter :: i=2' 'real x(i)'
                                   -> 'real x(2)')
    The above may be solved by creating appropriate preprocessor program, for example.

"""
import codecs
import copy
import fileinput
import os
import platform
import re
import string
import sys
from pathlib import Path

try:
    import charset_normalizer
except ImportError:
    charset_normalizer = None

from . import __version__, symbolic

# The environment provided by auxfuncs.py is needed for some calls to eval.
# As the needed functions cannot be determined by static inspection of the
# code, it is safest to use import * pending a major refactoring of f2py.
from .auxfuncs import *

f2py_version = __version__.version

# Global flags:
strictf77 = 1          # Ignore `!' comments unless line[0]=='!'
sourcecodeform = 'fix'  # 'fix','free'
quiet = 0              # Be verbose if 0 (Obsolete: not used any more)
verbose = 1            # Be quiet if 0, extra verbose if > 1.
tabchar = 4 * ' '
pyffilename = ''
f77modulename = ''
skipemptyends = 0      # for old F77 programs without 'program' statement
ignorecontains = 1
dolowercase = 1
debug = []

# Global variables
beginpattern = ''
currentfilename = ''
expectbegin = 1
f90modulevars = {}
filepositiontext = ''
gotnextfile = 1
groupcache = None
groupcounter = 0
grouplist = {groupcounter: []}
groupname = ''
include_paths = []
neededmodule = -1
onlyfuncs = []
previous_context = None
skipblocksuntil = -1
skipfuncs = []
skipfunctions = []
usermodules = []


def reset_global_f2py_vars():
    global groupcounter, grouplist, neededmodule, expectbegin
    global skipblocksuntil, usermodules, f90modulevars, gotnextfile
    global filepositiontext, currentfilename, skipfunctions, skipfuncs
    global onlyfuncs, include_paths, previous_context
    global strictf77, sourcecodeform, quiet, verbose, tabchar, pyffilename
    global f77modulename, skipemptyends, ignorecontains, dolowercase, debug

    # flags
    strictf77 = 1
    sourcecodeform = 'fix'
    quiet = 0
    verbose = 1
    tabchar = 4 * ' '
    pyffilename = ''
    f77modulename = ''
    skipemptyends = 0
    ignorecontains = 1
    dolowercase = 1
    debug = []
    # variables
    groupcounter = 0
    grouplist = {groupcounter: []}
    neededmodule = -1
    expectbegin = 1
    skipblocksuntil = -1
    usermodules = []
    f90modulevars = {}
    gotnextfile = 1
    filepositiontext = ''
    currentfilename = ''
    skipfunctions = []
    skipfuncs = []
    onlyfuncs = []
    include_paths = []
    previous_context = None


def outmess(line, flag=1):
    global filepositiontext

    if not verbose:
        return
    if not quiet:
        if flag:
            sys.stdout.write(filepositiontext)
        sys.stdout.write(line)


re._MAXCACHE = 50
defaultimplicitrules = {}
for c in "abcdefghopqrstuvwxyz$_":
    defaultimplicitrules[c] = {'typespec': 'real'}
for c in "ijklmn":
    defaultimplicitrules[c] = {'typespec': 'integer'}
badnames = {}
invbadnames = {}
for n in ['int', 'double', 'float', 'char', 'short', 'long', 'void', 'case', 'while',
          'return', 'signed', 'unsigned', 'if', 'for', 'typedef', 'sizeof', 'union',
          'struct', 'static', 'register', 'new', 'break', 'do', 'goto', 'switch',
          'continue', 'else', 'inline', 'extern', 'delete', 'const', 'auto',
          'len', 'rank', 'shape', 'index', 'slen', 'size', '_i',
          'max', 'min',
          'flen', 'fshape',
          'string', 'complex_double', 'float_double', 'stdin', 'stderr', 'stdout',
          'type', 'default']:
    badnames[n] = n + '_bn'
    invbadnames[n + '_bn'] = n


def rmbadname1(name):
    if name in badnames:
        errmess(f'rmbadname1: Replacing "{name}" with "{badnames[name]}".\n')
        return badnames[name]
    return name


def rmbadname(names):
    return [rmbadname1(_m) for _m in names]


def undo_rmbadname1(name):
    if name in invbadnames:
        errmess(f'undo_rmbadname1: Replacing "{name}" with "{invbadnames[name]}".\n')
        return invbadnames[name]
    return name


def undo_rmbadname(names):
    return [undo_rmbadname1(_m) for _m in names]


_has_f_header = re.compile(r'-\*-\s*fortran\s*-\*-', re.I).search
_has_f90_header = re.compile(r'-\*-\s*f90\s*-\*-', re.I).search
_has_fix_header = re.compile(r'-\*-\s*fix\s*-\*-', re.I).search
_free_f90_start = re.compile(r'[^c*]\s*[^\s\d\t]', re.I).match

# Extensions
COMMON_FREE_EXTENSIONS = ['.f90', '.f95', '.f03', '.f08']
COMMON_FIXED_EXTENSIONS = ['.for', '.ftn', '.f77', '.f']


def openhook(filename, mode):
    """Ensures that filename is opened with correct encoding parameter.

    This function uses charset_normalizer package, when available, for
    determining the encoding of the file to be opened. When charset_normalizer
    is not available, the function detects only UTF encodings, otherwise, ASCII
    encoding is used as fallback.
    """
    # Reads in the entire file. Robust detection of encoding.
    # Correctly handles comments or late stage unicode characters
    # gh-22871
    if charset_normalizer is not None:
        encoding = charset_normalizer.from_path(filename).best().encoding
    else:
        # hint: install charset_normalizer for correct encoding handling
        # No need to read the whole file for trying with startswith
        nbytes = min(32, os.path.getsize(filename))
        with open(filename, 'rb') as fhandle:
            raw = fhandle.read(nbytes)
            if raw.startswith(codecs.BOM_UTF8):
                encoding = 'UTF-8-SIG'
            elif raw.startswith((codecs.BOM_UTF32_LE, codecs.BOM_UTF32_BE)):
                encoding = 'UTF-32'
            elif raw.startswith((codecs.BOM_LE, codecs.BOM_BE)):
                encoding = 'UTF-16'
            else:
                # Fallback, without charset_normalizer
                encoding = 'ascii'
    return open(filename, mode, encoding=encoding)


def is_free_format(fname):
    """Check if file is in free format Fortran."""
    # f90 allows both fixed and free format, assuming fixed unless
    # signs of free format are detected.
    result = False
    if Path(fname).suffix.lower() in COMMON_FREE_EXTENSIONS:
        result = True
    with openhook(fname, 'r') as fhandle:
        line = fhandle.readline()
        n = 15  # the number of non-comment lines to scan for hints
        if _has_f_header(line):
            n = 0
        elif _has_f90_header(line):
            n = 0
            result = True
        while n > 0 and line:
            if line[0] != '!' and line.strip():
                n -= 1
                if (line[0] != '\t' and _free_f90_start(line[:5])) or line[-2:-1] == '&':
                    result = True
                    break
            line = fhandle.readline()
    return result


# Read fortran (77,90) code
def readfortrancode(ffile, dowithline=show, istop=1):
    """
    Read fortran codes from files and
     1) Get rid of comments, line continuations, and empty lines; lower cases.
     2) Call dowithline(line) on every line.
     3) Recursively call itself when statement \"include '<filename>'\" is met.
    """
    global gotnextfile, filepositiontext, currentfilename, sourcecodeform, strictf77
    global beginpattern, quiet, verbose, dolowercase, include_paths

    if not istop:
        saveglobals = gotnextfile, filepositiontext, currentfilename, sourcecodeform, strictf77,\
            beginpattern, quiet, verbose, dolowercase
    if ffile == []:
        return
    localdolowercase = dolowercase
    # cont: set to True when the content of the last line read
    # indicates statement continuation
    cont = False
    finalline = ''
    ll = ''
    includeline = re.compile(
        r'\s*include\s*(\'|")(?P<name>[^\'"]*)(\'|")', re.I)
    cont1 = re.compile(r'(?P<line>.*)&\s*\Z')
    cont2 = re.compile(r'(\s*&|)(?P<line>.*)')
    mline_mark = re.compile(r".*?'''")
    if istop:
        dowithline('', -1)
    ll, l1 = '', ''
    spacedigits = [' '] + [str(_m) for _m in range(10)]
    filepositiontext = ''
    fin = fileinput.FileInput(ffile, openhook=openhook)
    while True:
        try:
            l = fin.readline()
        except UnicodeDecodeError as msg:
            raise Exception(
                f'readfortrancode: reading {fin.filename()}#{fin.lineno()}'
                f' failed with\n{msg}.\nIt is likely that installing charset_normalizer'
                ' package will help f2py determine the input file encoding'
                ' correctly.')
        if not l:
            break
        if fin.isfirstline():
            filepositiontext = ''
            currentfilename = fin.filename()
            gotnextfile = 1
            l1 = l
            strictf77 = 0
            sourcecodeform = 'fix'
            ext = os.path.splitext(currentfilename)[1]
            if Path(currentfilename).suffix.lower() in COMMON_FIXED_EXTENSIONS and \
                    not (_has_f90_header(l) or _has_fix_header(l)):
                strictf77 = 1
            elif is_free_format(currentfilename) and not _has_fix_header(l):
                sourcecodeform = 'free'
            if strictf77:
                beginpattern = beginpattern77
            else:
                beginpattern = beginpattern90
            outmess('\tReading file %s (format:%s%s)\n'
                    % (repr(currentfilename), sourcecodeform,
                       (strictf77 and ',strict') or ''))

        l = l.expandtabs().replace('\xa0', ' ')
        # Get rid of newline characters
        while not l == '':
            if l[-1] not in "\n\r\f":
                break
            l = l[:-1]
        # Do not lower for directives, gh-2547, gh-27697, gh-26681
        is_f2py_directive = False
        # Unconditionally remove comments
        (l, rl) = split_by_unquoted(l, '!')
        l += ' '
        if rl[:5].lower() == '!f2py':  # f2py directive
            l, _ = split_by_unquoted(l + 4 * ' ' + rl[5:], '!')
            is_f2py_directive = True
        if l.strip() == '':  # Skip empty line
            if sourcecodeform == 'free':
                # In free form, a statement continues in the next line
                # that is not a comment line [3.3.2.4^1], lines with
                # blanks are comment lines [3.3.2.3^1]. Hence, the
                # line continuation flag must retain its state.
                pass
            else:
                # In fixed form, statement continuation is determined
                # by a non-blank character at the 6-th position. Empty
                # line indicates a start of a new statement
                # [3.3.3.3^1]. Hence, the line continuation flag must
                # be reset.
                cont = False
            continue
        if sourcecodeform == 'fix':
            if l[0] in ['*', 'c', '!', 'C', '#']:
                if l[1:5].lower() == 'f2py':  # f2py directive
                    l = '     ' + l[5:]
                    is_f2py_directive = True
                else:  # Skip comment line
                    cont = False
                    is_f2py_directive = False
                    continue
            elif strictf77:
                if len(l) > 72:
                    l = l[:72]
            if l[0] not in spacedigits:
                raise Exception('readfortrancode: Found non-(space,digit) char '
                                'in the first column.\n\tAre you sure that '
                                'this code is in fix form?\n\tline=%s' % repr(l))

            if (not cont or strictf77) and (len(l) > 5 and not l[5] == ' '):
                # Continuation of a previous line
                ll = ll + l[6:]
                finalline = ''
                origfinalline = ''
            else:
                r = cont1.match(l)
                if r:
                    l = r.group('line')  # Continuation follows ..
                if cont:
                    ll = ll + cont2.match(l).group('line')
                    finalline = ''
                    origfinalline = ''
                else:
                    # clean up line beginning from possible digits.
                    l = '     ' + l[5:]
                    # f2py directives are already stripped by this point
                    if localdolowercase:
                        finalline = ll.lower()
                    else:
                        finalline = ll
                    origfinalline = ll
                    ll = l

        elif sourcecodeform == 'free':
            if not cont and ext == '.pyf' and mline_mark.match(l):
                l = l + '\n'
                while True:
                    lc = fin.readline()
                    if not lc:
                        errmess(
                            'Unexpected end of file when reading multiline\n')
                        break
                    l = l + lc
                    if mline_mark.match(lc):
                        break
                l = l.rstrip()
            r = cont1.match(l)
            if r:
                l = r.group('line')  # Continuation follows ..
            if cont:
                ll = ll + cont2.match(l).group('line')
                finalline = ''
                origfinalline = ''
            else:
                if localdolowercase:
                    # only skip lowering for C style constructs
                    # gh-2547, gh-27697, gh-26681, gh-28014
                    finalline = ll.lower() if not (is_f2py_directive and iscstyledirective(ll)) else ll
                else:
                    finalline = ll
                origfinalline = ll
                ll = l
            cont = (r is not None)
        else:
            raise ValueError(
                f"Flag sourcecodeform must be either 'fix' or 'free': {repr(sourcecodeform)}")
        filepositiontext = 'Line #%d in %s:"%s"\n\t' % (
            fin.filelineno() - 1, currentfilename, l1)
        m = includeline.match(origfinalline)
        if m:
            fn = m.group('name')
            if os.path.isfile(fn):
                readfortrancode(fn, dowithline=dowithline, istop=0)
            else:
                include_dirs = [
                    os.path.dirname(currentfilename)] + include_paths
                foundfile = 0
                for inc_dir in include_dirs:
                    fn1 = os.path.join(inc_dir, fn)
                    if os.path.isfile(fn1):
                        foundfile = 1
                        readfortrancode(fn1, dowithline=dowithline, istop=0)
                        break
                if not foundfile:
                    outmess('readfortrancode: could not find include file %s in %s. Ignoring.\n' % (
                        repr(fn), os.pathsep.join(include_dirs)))
        else:
            dowithline(finalline)
        l1 = ll
    # Last line should never have an f2py directive anyway
    if localdolowercase:
        finalline = ll.lower()
    else:
        finalline = ll
    origfinalline = ll
    filepositiontext = 'Line #%d in %s:"%s"\n\t' % (
        fin.filelineno() - 1, currentfilename, l1)
    m = includeline.match(origfinalline)
    if m:
        fn = m.group('name')
        if os.path.isfile(fn):
            readfortrancode(fn, dowithline=dowithline, istop=0)
        else:
            include_dirs = [os.path.dirname(currentfilename)] + include_paths
            foundfile = 0
            for inc_dir in include_dirs:
                fn1 = os.path.join(inc_dir, fn)
                if os.path.isfile(fn1):
                    foundfile = 1
                    readfortrancode(fn1, dowithline=dowithline, istop=0)
                    break
            if not foundfile:
                outmess('readfortrancode: could not find include file %s in %s. Ignoring.\n' % (
                    repr(fn), os.pathsep.join(include_dirs)))
    else:
        dowithline(finalline)
    filepositiontext = ''
    fin.close()
    if istop:
        dowithline('', 1)
    else:
        gotnextfile, filepositiontext, currentfilename, sourcecodeform, strictf77,\
            beginpattern, quiet, verbose, dolowercase = saveglobals


# Crack line
beforethisafter = r'\s*(?P<before>%s(?=\s*(\b(%s)\b)))'\
    r'\s*(?P<this>(\b(%s)\b))'\
    r'\s*(?P<after>%s)\s*\Z'
##
fortrantypes = r'character|logical|integer|real|complex|double\s*(precision\s*(complex|)|complex)|type(?=\s*\([\w\s,=(*)]*\))|byte'
typespattern = re.compile(
    beforethisafter % ('', fortrantypes, fortrantypes, '.*'), re.I), 'type'
typespattern4implicit = re.compile(beforethisafter % (
    '', fortrantypes + '|static|automatic|undefined', fortrantypes + '|static|automatic|undefined', '.*'), re.I)
#
functionpattern = re.compile(beforethisafter % (
    r'([a-z]+[\w\s(=*+-/)]*?|)', 'function', 'function', '.*'), re.I), 'begin'
subroutinepattern = re.compile(beforethisafter % (
    r'[a-z\s]*?', 'subroutine', 'subroutine', '.*'), re.I), 'begin'
# modulepattern=re.compile(beforethisafter%('[a-z\s]*?','module','module','.*'),re.I),'begin'
#
groupbegins77 = r'program|block\s*data'
beginpattern77 = re.compile(
    beforethisafter % ('', groupbegins77, groupbegins77, '.*'), re.I), 'begin'
groupbegins90 = groupbegins77 + \
    r'|module(?!\s*procedure)|python\s*module|(abstract|)\s*interface|'\
    r'type(?!\s*\()'
beginpattern90 = re.compile(
    beforethisafter % ('', groupbegins90, groupbegins90, '.*'), re.I), 'begin'
groupends = (r'end|endprogram|endblockdata|endmodule|endpythonmodule|'
             r'endinterface|endsubroutine|endfunction')
endpattern = re.compile(
    beforethisafter % ('', groupends, groupends, '.*'), re.I), 'end'
# block, the Fortran 2008 construct needs special handling in the rest of the file
endifs = r'end\s*(if|do|where|select|while|forall|associate|'\
         r'critical|enum|team)'
endifpattern = re.compile(
    beforethisafter % (r'[\w]*?', endifs, endifs, '.*'), re.I), 'endif'
#
moduleprocedures = r'module\s*procedure'
moduleprocedurepattern = re.compile(
    beforethisafter % ('', moduleprocedures, moduleprocedures, '.*'), re.I), \
    'moduleprocedure'
implicitpattern = re.compile(
    beforethisafter % ('', 'implicit', 'implicit', '.*'), re.I), 'implicit'
dimensionpattern = re.compile(beforethisafter % (
    '', 'dimension|virtual', 'dimension|virtual', '.*'), re.I), 'dimension'
externalpattern = re.compile(
    beforethisafter % ('', 'external', 'external', '.*'), re.I), 'external'
optionalpattern = re.compile(
    beforethisafter % ('', 'optional', 'optional', '.*'), re.I), 'optional'
requiredpattern = re.compile(
    beforethisafter % ('', 'required', 'required', '.*'), re.I), 'required'
publicpattern = re.compile(
    beforethisafter % ('', 'public', 'public', '.*'), re.I), 'public'
privatepattern = re.compile(
    beforethisafter % ('', 'private', 'private', '.*'), re.I), 'private'
intrinsicpattern = re.compile(
    beforethisafter % ('', 'intrinsic', 'intrinsic', '.*'), re.I), 'intrinsic'
intentpattern = re.compile(beforethisafter % (
    '', 'intent|depend|note|check', 'intent|depend|note|check', r'\s*\(.*?\).*'), re.I), 'intent'
parameterpattern = re.compile(
    beforethisafter % ('', 'parameter', 'parameter', r'\s*\(.*'), re.I), 'parameter'
datapattern = re.compile(
    beforethisafter % ('', 'data', 'data', '.*'), re.I), 'data'
callpattern = re.compile(
    beforethisafter % ('', 'call', 'call', '.*'), re.I), 'call'
entrypattern = re.compile(
    beforethisafter % ('', 'entry', 'entry', '.*'), re.I), 'entry'
callfunpattern = re.compile(
    beforethisafter % ('', 'callfun', 'callfun', '.*'), re.I), 'callfun'
commonpattern = re.compile(
    beforethisafter % ('', 'common', 'common', '.*'), re.I), 'common'
usepattern = re.compile(
    beforethisafter % ('', 'use', 'use', '.*'), re.I), 'use'
containspattern = re.compile(
    beforethisafter % ('', 'contains', 'contains', ''), re.I), 'contains'
formatpattern = re.compile(
    beforethisafter % ('', 'format', 'format', '.*'), re.I), 'format'
# Non-fortran and f2py-specific statements
f2pyenhancementspattern = re.compile(beforethisafter % ('', 'threadsafe|fortranname|callstatement|callprotoargument|usercode|pymethoddef',
                                                        'threadsafe|fortranname|callstatement|callprotoargument|usercode|pymethoddef', '.*'), re.I | re.S), 'f2pyenhancements'
multilinepattern = re.compile(
    r"\s*(?P<before>''')(?P<this>.*?)(?P<after>''')\s*\Z", re.S), 'multiline'
##

def split_by_unquoted(line, characters):
    """
    Splits the line into (line[:i], line[i:]),
    where i is the index of first occurrence of one of the characters
    not within quotes, or len(line) if no such index exists
    """
    assert not (set('"\'') & set(characters)), "cannot split by unquoted quotes"
    r = re.compile(
        r"\A(?P<before>({single_quoted}|{double_quoted}|{not_quoted})*)"
        r"(?P<after>{char}.*)\Z".format(
            not_quoted=f"[^\"'{re.escape(characters)}]",
            char=f"[{re.escape(characters)}]",
            single_quoted=r"('([^'\\]|(\\.))*')",
            double_quoted=r'("([^"\\]|(\\.))*")'))
    m = r.match(line)
    if m:
        d = m.groupdict()
        return (d["before"], d["after"])
    return (line, "")

def _simplifyargs(argsline):
    a = []
    for n in markoutercomma(argsline).split('@,@'):
        for r in '(),':
            n = n.replace(r, '_')
        a.append(n)
    return ','.join(a)


crackline_re_1 = re.compile(r'\s*(?P<result>\b[a-z]+\w*\b)\s*=.*', re.I)
crackline_bind_1 = re.compile(r'\s*(?P<bind>\b[a-z]+\w*\b)\s*=.*', re.I)
crackline_bindlang = re.compile(r'\s*bind\(\s*(?P<lang>[^,]+)\s*,\s*name\s*=\s*"(?P<lang_name>[^"]+)"\s*\)', re.I)

def crackline(line, reset=0):
    """
    reset=-1  --- initialize
    reset=0   --- crack the line
    reset=1   --- final check if mismatch of blocks occurred

    Cracked data is saved in grouplist[0].
    """
    global beginpattern, groupcounter, groupname, groupcache, grouplist
    global filepositiontext, currentfilename, neededmodule, expectbegin
    global skipblocksuntil, skipemptyends, previous_context, gotnextfile

    _, has_semicolon = split_by_unquoted(line, ";")
    if has_semicolon and not (f2pyenhancementspattern[0].match(line) or
                               multilinepattern[0].match(line)):
        # XXX: non-zero reset values need testing
        assert reset == 0, repr(reset)
        # split line on unquoted semicolons
        line, semicolon_line = split_by_unquoted(line, ";")
        while semicolon_line:
            crackline(line, reset)
            line, semicolon_line = split_by_unquoted(semicolon_line[1:], ";")
        crackline(line, reset)
        return
    if reset < 0:
        groupcounter = 0
        groupname = {groupcounter: ''}
        groupcache = {groupcounter: {}}
        grouplist = {groupcounter: []}
        groupcache[groupcounter]['body'] = []
        groupcache[groupcounter]['vars'] = {}
        groupcache[groupcounter]['block'] = ''
        groupcache[groupcounter]['name'] = ''
        neededmodule = -1
        skipblocksuntil = -1
        return
    if reset > 0:
        fl = 0
        if f77modulename and neededmodule == groupcounter:
            fl = 2
        while groupcounter > fl:
            outmess('crackline: groupcounter=%s groupname=%s\n' %
                    (repr(groupcounter), repr(groupname)))
            outmess(
                'crackline: Mismatch of blocks encountered. Trying to fix it by assuming "end" statement.\n')
            grouplist[groupcounter - 1].append(groupcache[groupcounter])
            grouplist[groupcounter - 1][-1]['body'] = grouplist[groupcounter]
            del grouplist[groupcounter]
            groupcounter = groupcounter - 1
        if f77modulename and neededmodule == groupcounter:
            grouplist[groupcounter - 1].append(groupcache[groupcounter])
            grouplist[groupcounter - 1][-1]['body'] = grouplist[groupcounter]
            del grouplist[groupcounter]
            groupcounter = groupcounter - 1  # end interface
            grouplist[groupcounter - 1].append(groupcache[groupcounter])
            grouplist[groupcounter - 1][-1]['body'] = grouplist[groupcounter]
            del grouplist[groupcounter]
            groupcounter = groupcounter - 1  # end module
            neededmodule = -1
        return
    if line == '':
        return
    flag = 0
    for pat in [dimensionpattern, externalpattern, intentpattern, optionalpattern,
                requiredpattern,
                parameterpattern, datapattern, publicpattern, privatepattern,
                intrinsicpattern,
                endifpattern, endpattern,
                formatpattern,
                beginpattern, functionpattern, subroutinepattern,
                implicitpattern, typespattern, commonpattern,
                callpattern, usepattern, containspattern,
                entrypattern,
                f2pyenhancementspattern,
                multilinepattern,
                moduleprocedurepattern
                ]:
        m = pat[0].match(line)
        if m:
            break
        flag = flag + 1
    if not m:
        re_1 = crackline_re_1
        if 0 <= skipblocksuntil <= groupcounter:
            return
        if 'externals' in groupcache[groupcounter]:
            for name in groupcache[groupcounter]['externals']:
                if name in invbadnames:
                    name = invbadnames[name]
                if 'interfaced' in groupcache[groupcounter] and name in groupcache[groupcounter]['interfaced']:
                    continue
                m1 = re.match(
                    r'(?P<before>[^"]*)\b%s\b\s*@\(@(?P<args>[^@]*)@\)@.*\Z' % name, markouterparen(line), re.I)
                if m1:
                    m2 = re_1.match(m1.group('before'))
                    a = _simplifyargs(m1.group('args'))
                    if m2:
                        line = f"callfun {name}({a}) result ({m2.group('result')})"
                    else:
                        line = f'callfun {name}({a})'
                    m = callfunpattern[0].match(line)
                    if not m:
                        outmess(
                            f'crackline: could not resolve function call for line={repr(line)}.\n')
                        return
                    analyzeline(m, 'callfun', line)
                    return
        if verbose > 1 or (verbose == 1 and currentfilename.lower().endswith('.pyf')):
            previous_context = None
            outmess('crackline:%d: No pattern for line\n' % (groupcounter))
        return
    elif pat[1] == 'end':
        if 0 <= skipblocksuntil < groupcounter:
            groupcounter = groupcounter - 1
            if skipblocksuntil <= groupcounter:
                return
        if groupcounter <= 0:
            raise Exception('crackline: groupcounter(=%s) is nonpositive. '
                            'Check the blocks.'
                            % (groupcounter))
        m1 = beginpattern[0].match(line)
        if (m1) and (not m1.group('this') == groupname[groupcounter]):
            raise Exception('crackline: End group %s does not match with '
                            'previous Begin group %s\n\t%s' %
                            (repr(m1.group('this')), repr(groupname[groupcounter]),
                             filepositiontext)
                            )
        if skipblocksuntil == groupcounter:
            skipblocksuntil = -1
        grouplist[groupcounter - 1].append(groupcache[groupcounter])
        grouplist[groupcounter - 1][-1]['body'] = grouplist[groupcounter]
        del grouplist[groupcounter]
        groupcounter = groupcounter - 1
        if not skipemptyends:
            expectbegin = 1
    elif pat[1] == 'begin':
        if 0 <= skipblocksuntil <= groupcounter:
            groupcounter = groupcounter + 1
            return
        gotnextfile = 0
        analyzeline(m, pat[1], line)
        expectbegin = 0
    elif pat[1] == 'endif':
        pass
    elif pat[1] == 'moduleprocedure':
        analyzeline(m, pat[1], line)
    elif pat[1] == 'contains':
        if ignorecontains:
            return
        if 0 <= skipblocksuntil <= groupcounter:
            return
        skipblocksuntil = groupcounter
    else:
        if 0 <= skipblocksuntil <= groupcounter:
            return
        analyzeline(m, pat[1], line)


def markouterparen(line):
    l = ''
    f = 0
    for c in line:
        if c == '(':
            f = f + 1
            if f == 1:
                l = l + '@(@'
                continue
        elif c == ')':
            f = f - 1
            if f == 0:
                l = l + '@)@'
                continue
        l = l + c
    return l


def markoutercomma(line, comma=','):
    l = ''
    f = 0
    before, after = split_by_unquoted(line, comma + '()')
    l += before
    while after:
        if (after[0] == comma) and (f == 0):
            l += '@' + comma + '@'
        else:
            l += after[0]
            if after[0] == '(':
                f += 1
            elif after[0] == ')':
                f -= 1
        before, after = split_by_unquoted(after[1:], comma + '()')
        l += before
    assert not f, repr((f, line, l))
    return l

def unmarkouterparen(line):
    r = line.replace('@(@', '(').replace('@)@', ')')
    return r


def appenddecl(decl, decl2, force=1):
    if not decl:
        decl = {}
    if not decl2:
        return decl
    if decl is decl2:
        return decl
    for k in list(decl2.keys()):
        if k == 'typespec':
            if force or k not in decl:
                decl[k] = decl2[k]
        elif k == 'attrspec':
            for l in decl2[k]:
                decl = setattrspec(decl, l, force)
        elif k == 'kindselector':
            decl = setkindselector(decl, decl2[k], force)
        elif k == 'charselector':
            decl = setcharselector(decl, decl2[k], force)
        elif k in ['=', 'typename']:
            if force or k not in decl:
                decl[k] = decl2[k]
        elif k == 'note':
            pass
        elif k in ['intent', 'check', 'dimension', 'optional',
                   'required', 'depend']:
            errmess(f'appenddecl: "{k}" not implemented.\n')
        else:
            raise Exception('appenddecl: Unknown variable definition key: ' +
                            str(k))
    return decl


selectpattern = re.compile(
    r'\s*(?P<this>(@\(@.*?@\)@|\*[\d*]+|\*\s*@\(@.*?@\)@|))(?P<after>.*)\Z', re.I)
typedefpattern = re.compile(
    r'(?:,(?P<attributes>[\w(),]+))?(::)?(?P<name>\b[a-z$_][\w$]*\b)'
    r'(?:\((?P<params>[\w,]*)\))?\Z', re.I)
nameargspattern = re.compile(
    r'\s*(?P<name>\b[\w$]+\b)\s*(@\(@\s*(?P<args>[\w\s,]*)\s*@\)@|)\s*((result(\s*@\(@\s*(?P<result>\b[\w$]+\b)\s*@\)@|))|(bind\s*@\(@\s*(?P<bind>(?:(?!@\)@).)*)\s*@\)@))*\s*\Z', re.I)
operatorpattern = re.compile(
    r'\s*(?P<scheme>(operator|assignment))'
    r'@\(@\s*(?P<name>[^)]+)\s*@\)@\s*\Z', re.I)
callnameargspattern = re.compile(
    r'\s*(?P<name>\b[\w$]+\b)\s*@\(@\s*(?P<args>.*)\s*@\)@\s*\Z', re.I)
real16pattern = re.compile(
    r'([-+]?(?:\d+(?:\.\d*)?|\d*\.\d+))[dD]((?:[-+]?\d+)?)')
real8pattern = re.compile(
    r'([-+]?((?:\d+(?:\.\d*)?|\d*\.\d+))[eE]((?:[-+]?\d+)?)|(\d+\.\d*))')

_intentcallbackpattern = re.compile(r'intent\s*\(.*?\bcallback\b', re.I)


def _is_intent_callback(vdecl):
    for a in vdecl.get('attrspec', []):
        if _intentcallbackpattern.match(a):
            return 1
    return 0


def _resolvetypedefpattern(line):
    line = ''.join(line.split())  # removes whitespace
    m1 = typedefpattern.match(line)
    print(line, m1)
    if m1:
        attrs = m1.group('attributes')
        attrs = [a.lower() for a in attrs.split(',')] if attrs else []
        return m1.group('name'), attrs, m1.group('params')
    return None, [], None

def parse_name_for_bind(line):
    pattern = re.compile(r'bind\(\s*(?P<lang>[^,]+)(?:\s*,\s*name\s*=\s*["\'](?P<name>[^"\']+)["\']\s*)?\)', re.I)
    match = pattern.search(line)
    bind_statement = None
    if match:
        bind_statement = match.group(0)
        # Remove the 'bind' construct from the line.
        line = line[:match.start()] + line[match.end():]
    return line, bind_statement

def _resolvenameargspattern(line):
    line, bind_cname = parse_name_for_bind(line)
    line = markouterparen(line)
    m1 = nameargspattern.match(line)
    if m1:
        return m1.group('name'), m1.group('args'), m1.group('result'), bind_cname
    m1 = operatorpattern.match(line)
    if m1:
        name = m1.group('scheme') + '(' + m1.group('name') + ')'
        return name, [], None, None
    m1 = callnameargspattern.match(line)
    if m1:
        return m1.group('name'), m1.group('args'), None, None
    return None, [], None, None


def analyzeline(m, case, line):
    """
    Reads each line in the input file in sequence and updates global vars.

    Effectively reads and collects information from the input file to the
    global variable groupcache, a dictionary containing info about each part
    of the fortran module.

    At the end of analyzeline, information is filtered into the correct dict
    keys, but parameter values and dimensions are not yet interpreted.
    """
    global groupcounter, groupname, groupcache, grouplist, filepositiontext
    global currentfilename, f77modulename, neededinterface, neededmodule
    global expectbegin, gotnextfile, previous_context

    block = m.group('this')
    if case != 'multiline':
        previous_context = None
    if expectbegin and case not in ['begin', 'call', 'callfun', 'type'] \
       and not skipemptyends and groupcounter < 1:
        newname = os.path.basename(currentfilename).split('.')[0]
        outmess(
            f'analyzeline: no group yet. Creating program group with name "{newname}".\n')
        gotnextfile = 0
        groupcounter = groupcounter + 1
        groupname[groupcounter] = 'program'
        groupcache[groupcounter] = {}
        grouplist[groupcounter] = []
        groupcache[groupcounter]['body'] = []
        groupcache[groupcounter]['vars'] = {}
        groupcache[groupcounter]['block'] = 'program'
        groupcache[groupcounter]['name'] = newname
        groupcache[groupcounter]['from'] = 'fromsky'
        expectbegin = 0
    if case in ['begin', 'call', 'callfun']:
        # Crack line => block,name,args,result
        block = block.lower()
        if re.match(r'block\s*data', block, re.I):
            block = 'block data'
        elif re.match(r'python\s*module', block, re.I):
            block = 'python module'
        elif re.match(r'abstract\s*interface', block, re.I):
            block = 'abstract interface'
        if block == 'type':
            name, attrs, _ = _resolvetypedefpattern(m.group('after'))
            groupcache[groupcounter]['vars'][name] = {'attrspec': attrs}
            args = []
            result = None
        else:
            name, args, result, bindcline = _resolvenameargspattern(m.group('after'))
        if name is None:
            if block == 'block data':
                name = '_BLOCK_DATA_'
            else:
                name = ''
            if block not in ['interface', 'block data', 'abstract interface']:
                outmess('analyzeline: No name/args pattern found for line.\n')

        previous_context = (block, name, groupcounter)
        if args:
            args = rmbadname([x.strip()
                              for x in markoutercomma(args).split('@,@')])
        else:
            args = []
        if '' in args:
            while '' in args:
                args.remove('')
            outmess(
                'analyzeline: argument list is malformed (missing argument).\n')

        # end of crack line => block,name,args,result
        needmodule = 0
        needinterface = 0

        if case in ['call', 'callfun']:
            needinterface = 1
            if 'args' not in groupcache[groupcounter]:
                return
            if name not in groupcache[groupcounter]['args']:
                return
            for it in grouplist[groupcounter]:
                if it['name'] == name:
                    return
            if name in groupcache[groupcounter]['interfaced']:
                return
            block = {'call': 'subroutine', 'callfun': 'function'}[case]
        if f77modulename and neededmodule == -1 and groupcounter <= 1:
            neededmodule = groupcounter + 2
            needmodule = 1
            if block not in ['interface', 'abstract interface']:
                needinterface = 1
        # Create new block(s)
        groupcounter = groupcounter + 1
        groupcache[groupcounter] = {}
        grouplist[groupcounter] = []
        if needmodule:
            if verbose > 1:
                outmess('analyzeline: Creating module block %s\n' %
                        repr(f77modulename), 0)
            groupname[groupcounter] = 'module'
            groupcache[groupcounter]['block'] = 'python module'
            groupcache[groupcounter]['name'] = f77modulename
            groupcache[groupcounter]['from'] = ''
            groupcache[groupcounter]['body'] = []
            groupcache[groupcounter]['externals'] = []
            groupcache[groupcounter]['interfaced'] = []
            groupcache[groupcounter]['vars'] = {}
            groupcounter = groupcounter + 1
            groupcache[groupcounter] = {}
            grouplist[groupcounter] = []
        if needinterface:
            if verbose > 1:
                outmess('analyzeline: Creating additional interface block (groupcounter=%s).\n' % (
                    groupcounter), 0)
            groupname[groupcounter] = 'interface'
            groupcache[groupcounter]['block'] = 'interface'
            groupcache[groupcounter]['name'] = 'unknown_interface'
            groupcache[groupcounter]['from'] = '%s:%s' % (
                groupcache[groupcounter - 1]['from'], groupcache[groupcounter - 1]['name'])
            groupcache[groupcounter]['body'] = []
            groupcache[groupcounter]['externals'] = []
            groupcache[groupcounter]['interfaced'] = []
            groupcache[groupcounter]['vars'] = {}
            groupcounter = groupcounter + 1
            groupcache[groupcounter] = {}
            grouplist[groupcounter] = []
        groupname[groupcounter] = block
        groupcache[groupcounter]['block'] = block
        if not name:
            name = 'unknown_' + block.replace(' ', '_')
        groupcache[groupcounter]['prefix'] = m.group('before')
        groupcache[groupcounter]['name'] = rmbadname1(name)
        groupcache[groupcounter]['result'] = result
        if groupcounter == 1:
            groupcache[groupcounter]['from'] = currentfilename
        elif f77modulename and groupcounter == 3:
            groupcache[groupcounter]['from'] = '%s:%s' % (
                groupcache[groupcounter - 1]['from'], currentfilename)
        else:
            groupcache[groupcounter]['from'] = '%s:%s' % (
                groupcache[groupcounter - 1]['from'], groupcache[groupcounter - 1]['name'])
        for k in list(groupcache[groupcounter].keys()):
            if not groupcache[groupcounter][k]:
                del groupcache[groupcounter][k]

        groupcache[groupcounter]['args'] = args
        groupcache[groupcounter]['body'] = []
        groupcache[groupcounter]['externals'] = []
        groupcache[groupcounter]['interfaced'] = []
        groupcache[groupcounter]['vars'] = {}
        groupcache[groupcounter]['entry'] = {}
        # end of creation
        if block == 'type':
            groupcache[groupcounter]['varnames'] = []

        if case in ['call', 'callfun']:  # set parents variables
            if name not in groupcache[groupcounter - 2]['externals']:
                groupcache[groupcounter - 2]['externals'].append(name)
            groupcache[groupcounter]['vars'] = copy.deepcopy(
                groupcache[groupcounter - 2]['vars'])
            try:
                del groupcache[groupcounter]['vars'][name][
                    groupcache[groupcounter]['vars'][name]['attrspec'].index('external')]
            except Exception:
                pass
        if block in ['function', 'subroutine']:  # set global attributes
            # name is fortran name
            if bindcline:
                bindcdat = re.search(crackline_bindlang, bindcline)
                if bindcdat:
                    groupcache[groupcounter]['bindlang'] = {name: {}}
                    groupcache[groupcounter]['bindlang'][name]["lang"] = bindcdat.group('lang')
                    if bindcdat.group('lang_name'):
                        groupcache[groupcounter]['bindlang'][name]["name"] = bindcdat.group('lang_name')
            try:
                groupcache[groupcounter]['vars'][name] = appenddecl(
                    groupcache[groupcounter]['vars'][name], groupcache[groupcounter - 2]['vars'][''])
            except Exception:
                pass
            if case == 'callfun':  # return type
                if result and result in groupcache[groupcounter]['vars']:
                    if not name == result:
                        groupcache[groupcounter]['vars'][name] = appenddecl(
                            groupcache[groupcounter]['vars'][name], groupcache[groupcounter]['vars'][result])
            # if groupcounter>1: # name is interfaced
            try:
                groupcache[groupcounter - 2]['interfaced'].append(name)
            except Exception:
                pass
        if block == 'function':
            t = typespattern[0].match(m.group('before') + ' ' + name)
            if t:
                typespec, selector, attr, edecl = cracktypespec0(
                    t.group('this'), t.group('after'))
                updatevars(typespec, selector, attr, edecl)

        if case in ['call', 'callfun']:
            grouplist[groupcounter - 1].append(groupcache[groupcounter])
            grouplist[groupcounter - 1][-1]['body'] = grouplist[groupcounter]
            del grouplist[groupcounter]
            groupcounter = groupcounter - 1  # end routine
            grouplist[groupcounter - 1].append(groupcache[groupcounter])
            grouplist[groupcounter - 1][-1]['body'] = grouplist[groupcounter]
            del grouplist[groupcounter]
            groupcounter = groupcounter - 1  # end interface

    elif case == 'entry':
        name, args, result, _ = _resolvenameargspattern(m.group('after'))
        if name is not None:
            if args:
                args = rmbadname([x.strip()
                                  for x in markoutercomma(args).split('@,@')])
            else:
                args = []
            assert result is None, repr(result)
            groupcache[groupcounter]['entry'][name] = args
            previous_context = ('entry', name, groupcounter)
    elif case == 'type':
        typespec, selector, attr, edecl = cracktypespec0(
            block, m.group('after'))
        last_name = updatevars(typespec, selector, attr, edecl)
        if last_name is not None:
            previous_context = ('variable', last_name, groupcounter)
    elif case in ['dimension', 'intent', 'optional', 'required', 'external', 'public', 'private', 'intrinsic']:
        edecl = groupcache[groupcounter]['vars']
        ll = m.group('after').strip()
        i = ll.find('::')
        if i < 0 and case == 'intent':
            i = markouterparen(ll).find('@)@') - 2
            ll = ll[:i + 1] + '::' + ll[i + 1:]
            i = ll.find('::')
            if ll[i:] == '::' and 'args' in groupcache[groupcounter]:
                outmess('All arguments will have attribute %s%s\n' %
                        (m.group('this'), ll[:i]))
                ll = ll + ','.join(groupcache[groupcounter]['args'])
        if i < 0:
            i = 0
            pl = ''
        else:
            pl = ll[:i].strip()
            ll = ll[i + 2:]
        ch = markoutercomma(pl).split('@,@')
        if len(ch) > 1:
            pl = ch[0]
            outmess('analyzeline: cannot handle multiple attributes without type specification. Ignoring %r.\n' % (
                ','.join(ch[1:])))
        last_name = None

        for e in [x.strip() for x in markoutercomma(ll).split('@,@')]:
            m1 = namepattern.match(e)
            if not m1:
                if case in ['public', 'private']:
                    k = ''
                else:
                    print(m.groupdict())
                    outmess('analyzeline: no name pattern found in %s statement for %s. Skipping.\n' % (
                        case, repr(e)))
                    continue
            else:
                k = rmbadname1(m1.group('name'))
            if case in ['public', 'private'] and k in {'operator', 'assignment'}:
                k += m1.group('after')
            if k not in edecl:
                edecl[k] = {}
            if case == 'dimension':
                ap = case + m1.group('after')
            if case == 'intent':
                ap = m.group('this') + pl
                if _intentcallbackpattern.match(ap):
                    if k not in groupcache[groupcounter]['args']:
                        if groupcounter > 1:
                            if '__user__' not in groupcache[groupcounter - 2]['name']:
                                outmess(
                                    'analyzeline: missing __user__ module (could be nothing)\n')
                            # fixes ticket 1693
                            if k != groupcache[groupcounter]['name']:
                                outmess('analyzeline: appending intent(callback) %s'
                                        ' to %s arguments\n' % (k, groupcache[groupcounter]['name']))
                                groupcache[groupcounter]['args'].append(k)
                        else:
                            errmess(
                                f'analyzeline: intent(callback) {k} is ignored\n')
                    else:
                        errmess('analyzeline: intent(callback) %s is already'
                                ' in argument list\n' % (k))
            if case in ['optional', 'required', 'public', 'external', 'private', 'intrinsic']:
                ap = case
            if 'attrspec' in edecl[k]:
                edecl[k]['attrspec'].append(ap)
            else:
                edecl[k]['attrspec'] = [ap]
            if case == 'external':
                if groupcache[groupcounter]['block'] == 'program':
                    outmess('analyzeline: ignoring program arguments\n')
                    continue
                if k not in groupcache[groupcounter]['args']:
                    continue
                if 'externals' not in groupcache[groupcounter]:
                    groupcache[groupcounter]['externals'] = []
                groupcache[groupcounter]['externals'].append(k)
            last_name = k
        groupcache[groupcounter]['vars'] = edecl
        if last_name is not None:
            previous_context = ('variable', last_name, groupcounter)
    elif case == 'moduleprocedure':
        groupcache[groupcounter]['implementedby'] = \
            [x.strip() for x in m.group('after').split(',')]
    elif case == 'parameter':
        edecl = groupcache[groupcounter]['vars']
        ll = m.group('after').strip()[1:-1]
        last_name = None
        for e in markoutercomma(ll).split('@,@'):
            try:
                k, initexpr = [x.strip() for x in e.split('=')]
            except Exception:
                outmess(
                    f'analyzeline: could not extract name,expr in parameter statement "{e}" of "{ll}\"\n')
                continue
            params = get_parameters(edecl)
            k = rmbadname1(k)
            if k not in edecl:
                edecl[k] = {}
            if '=' in edecl[k] and (not edecl[k]['='] == initexpr):
                outmess('analyzeline: Overwriting the value of parameter "%s" ("%s") with "%s".\n' % (
                    k, edecl[k]['='], initexpr))
            t = determineexprtype(initexpr, params)
            if t:
                if t.get('typespec') == 'real':
                    tt = list(initexpr)
                    for m in real16pattern.finditer(initexpr):
                        tt[m.start():m.end()] = list(
                            initexpr[m.start():m.end()].lower().replace('d', 'e'))
                    initexpr = ''.join(tt)
                elif t.get('typespec') == 'complex':
                    initexpr = initexpr[1:].lower().replace('d', 'e').\
                        replace(',', '+1j*(')
            try:
                v = eval(initexpr, {}, params)
            except (SyntaxError, NameError, TypeError) as msg:
                errmess('analyzeline: Failed to evaluate %r. Ignoring: %s\n'
                        % (initexpr, msg))
                continue
            edecl[k]['='] = repr(v)
            if 'attrspec' in edecl[k]:
                edecl[k]['attrspec'].append('parameter')
            else:
                edecl[k]['attrspec'] = ['parameter']
            last_name = k
        groupcache[groupcounter]['vars'] = edecl
        if last_name is not None:
            previous_context = ('variable', last_name, groupcounter)
    elif case == 'implicit':
        if m.group('after').strip().lower() == 'none':
            groupcache[groupcounter]['implicit'] = None
        elif m.group('after'):
            impl = groupcache[groupcounter].get('implicit', {})
            if impl is None:
                outmess(
                    'analyzeline: Overwriting earlier "implicit none" statement.\n')
                impl = {}
            for e in markoutercomma(m.group('after')).split('@,@'):
                decl = {}
                m1 = re.match(
                    r'\s*(?P<this>.*?)\s*(\(\s*(?P<after>[a-z-, ]+)\s*\)\s*|)\Z', e, re.I)
                if not m1:
                    outmess(
                        f'analyzeline: could not extract info of implicit statement part "{e}\"\n')
                    continue
                m2 = typespattern4implicit.match(m1.group('this'))
                if not m2:
                    outmess(
                        f'analyzeline: could not extract types pattern of implicit statement part "{e}\"\n')
                    continue
                typespec, selector, attr, edecl = cracktypespec0(
                    m2.group('this'), m2.group('after'))
                kindselect, charselect, typename = cracktypespec(
                    typespec, selector)
                decl['typespec'] = typespec
                decl['kindselector'] = kindselect
                decl['charselector'] = charselect
                decl['typename'] = typename
                for k in list(decl.keys()):
                    if not decl[k]:
                        del decl[k]
                for r in markoutercomma(m1.group('after')).split('@,@'):
                    if '-' in r:
                        try:
                            begc, endc = [x.strip() for x in r.split('-')]
                        except Exception:
                            outmess(
                                f'analyzeline: expected "<char>-<char>" instead of "{r}" in range list of implicit statement\n')
                            continue
                    else:
                        begc = endc = r.strip()
                    if not len(begc) == len(endc) == 1:
                        outmess(
                            f'analyzeline: expected "<char>-<char>" instead of "{r}" in range list of implicit statement (2)\n')
                        continue
                    for o in range(ord(begc), ord(endc) + 1):
                        impl[chr(o)] = decl
            groupcache[groupcounter]['implicit'] = impl
    elif case == 'data':
        ll = []
        dl = ''
        il = ''
        f = 0
        fc = 1
        inp = 0
        for c in m.group('after'):
            if not inp:
                if c == "'":
                    fc = not fc
                if c == '/' and fc:
                    f = f + 1
                    continue
            if c == '(':
                inp = inp + 1
            elif c == ')':
                inp = inp - 1
            if f == 0:
                dl = dl + c
            elif f == 1:
                il = il + c
            elif f == 2:
                dl = dl.strip()
                if dl.startswith(','):
                    dl = dl[1:].strip()
                ll.append([dl, il])
                dl = c
                il = ''
                f = 0
        if f == 2:
            dl = dl.strip()
            if dl.startswith(','):
                dl = dl[1:].strip()
            ll.append([dl, il])
        vars = groupcache[groupcounter].get('vars', {})
        last_name = None
        for l in ll:
            l[0], l[1] = l[0].strip().removeprefix(','), l[1].strip()
            if l[0].startswith('('):
                outmess(f'analyzeline: implied-DO list "{l[0]}" is not supported. Skipping.\n')
                continue
            for idx, v in enumerate(rmbadname([x.strip() for x in markoutercomma(l[0]).split('@,@')])):
                if v.startswith('('):
                    outmess(f'analyzeline: implied-DO list "{v}" is not supported. Skipping.\n')
                    # XXX: subsequent init expressions may get wrong values.
                    # Ignoring since data statements are irrelevant for
                    # wrapping.
                    continue
                if '!' in l[1]:
                    # Fixes gh-24746 pyf generation
                    # XXX: This essentially ignores the value for generating the pyf which is fine:
                    # integer dimension(3) :: mytab
                    # common /mycom/ mytab
                    # Since in any case it is initialized in the Fortran code
                    outmess(f'Comment line in declaration "{l[1]}" is not supported. Skipping.\n')
                    continue
                vars.setdefault(v, {})
                vtype = vars[v].get('typespec')
                vdim = getdimension(vars[v])
                matches = re.findall(r"\(.*?\)", l[1]) if vtype == 'complex' else l[1].split(',')
                try:
                    new_val = f"(/{', '.join(matches)}/)" if vdim else matches[idx]
                except IndexError:
                    # gh-24746
                    # Runs only if above code fails. Fixes the line
                    # DATA IVAR1, IVAR2, IVAR3, IVAR4, EVAR5 /4*0,0.0D0/
                    # by expanding to ['0', '0', '0', '0', '0.0d0']
                    if any("*" in m for m in matches):
                        expanded_list = []
                        for match in matches:
                            if "*" in match:
                                try:
                                    multiplier, value = match.split("*")
                                    expanded_list.extend([value.strip()] * int(multiplier))
                                except ValueError:  # if int(multiplier) fails
                                    expanded_list.append(match.strip())
                            else:
                                expanded_list.append(match.strip())
                        matches = expanded_list
                    new_val = f"(/{', '.join(matches)}/)" if vdim else matches[idx]
                current_val = vars[v].get('=')
                if current_val and (current_val != new_val):
                    outmess(f'analyzeline: changing init expression of "{v}" ("{current_val}") to "{new_val}\"\n')
                vars[v]['='] = new_val
                last_name = v
        groupcache[groupcounter]['vars'] = vars
        if last_name:
            previous_context = ('variable', last_name, groupcounter)
    elif case == 'common':
        line = m.group('after').strip()
        if not line[0] == '/':
            line = '//' + line

        cl = []
        [_, bn, ol] = re.split('/', line, maxsplit=2)  # noqa: RUF039
        bn = bn.strip()
        if not bn:
            bn = '_BLNK_'
        cl.append([bn, ol])
        commonkey = {}
        if 'common' in groupcache[groupcounter]:
            commonkey = groupcache[groupcounter]['common']
        for c in cl:
            if c[0] not in commonkey:
                commonkey[c[0]] = []
            for i in [x.strip() for x in markoutercomma(c[1]).split('@,@')]:
                if i:
                    commonkey[c[0]].append(i)
        groupcache[groupcounter]['common'] = commonkey
        previous_context = ('common', bn, groupcounter)
    elif case == 'use':
        m1 = re.match(
            r'\A\s*(?P<name>\b\w+\b)\s*((,(\s*\bonly\b\s*:|(?P<notonly>))\s*(?P<list>.*))|)\s*\Z', m.group('after'), re.I)
        if m1:
            mm = m1.groupdict()
            if 'use' not in groupcache[groupcounter]:
                groupcache[groupcounter]['use'] = {}
            name = m1.group('name')
            groupcache[groupcounter]['use'][name] = {}
            isonly = 0
            if 'list' in mm and mm['list'] is not None:
                if 'notonly' in mm and mm['notonly'] is None:
                    isonly = 1
                groupcache[groupcounter]['use'][name]['only'] = isonly
                ll = [x.strip() for x in mm['list'].split(',')]
                rl = {}
                for l in ll:
                    if '=' in l:
                        m2 = re.match(
                            r'\A\s*(?P<local>\b\w+\b)\s*=\s*>\s*(?P<use>\b\w+\b)\s*\Z', l, re.I)
                        if m2:
                            rl[m2.group('local').strip()] = m2.group(
                                'use').strip()
                        else:
                            outmess(
                                f'analyzeline: Not local=>use pattern found in {repr(l)}\n')
                    else:
                        rl[l] = l
                    groupcache[groupcounter]['use'][name]['map'] = rl
        else:
            print(m.groupdict())
            outmess('analyzeline: Could not crack the use statement.\n')
    elif case in ['f2pyenhancements']:
        if 'f2pyenhancements' not in groupcache[groupcounter]:
            groupcache[groupcounter]['f2pyenhancements'] = {}
        d = groupcache[groupcounter]['f2pyenhancements']
        if m.group('this') == 'usercode' and 'usercode' in d:
            if isinstance(d['usercode'], str):
                d['usercode'] = [d['usercode']]
            d['usercode'].append(m.group('after'))
        else:
            d[m.group('this')] = m.group('after')
    elif case == 'multiline':
        if previous_context is None:
            if verbose:
                outmess('analyzeline: No context for multiline block.\n')
            return
        gc = groupcounter
        appendmultiline(groupcache[gc],
                        previous_context[:2],
                        m.group('this'))
    elif verbose > 1:
        print(m.groupdict())
        outmess('analyzeline: No code implemented for line.\n')


def appendmultiline(group, context_name, ml):
    if 'f2pymultilines' not in group:
        group['f2pymultilines'] = {}
    d = group['f2pymultilines']
    if context_name not in d:
        d[context_name] = []
    d[context_name].append(ml)


def cracktypespec0(typespec, ll):
    selector = None
    attr = None
    if re.match(r'double\s*complex', typespec, re.I):
        typespec = 'double complex'
    elif re.match(r'double\s*precision', typespec, re.I):
        typespec = 'double precision'
    else:
        typespec = typespec.strip().lower()
    m1 = selectpattern.match(markouterparen(ll))
    if not m1:
        outmess(
            'cracktypespec0: no kind/char_selector pattern found for line.\n')
        return
    d = m1.groupdict()
    for k in list(d.keys()):
        d[k] = unmarkouterparen(d[k])
    if typespec in ['complex', 'integer', 'logical', 'real', 'character', 'type']:
        selector = d['this']
        ll = d['after']
    i = ll.find('::')
    if i >= 0:
        attr = ll[:i].strip()
        ll = ll[i + 2:]
    return typespec, selector, attr, ll


#####
namepattern = re.compile(r'\s*(?P<name>\b\w+\b)\s*(?P<after>.*)\s*\Z', re.I)
kindselector = re.compile(
    r'\s*(\(\s*(kind\s*=)?\s*(?P<kind>.*)\s*\)|\*\s*(?P<kind2>.*?))\s*\Z', re.I)
charselector = re.compile(
    r'\s*(\((?P<lenkind>.*)\)|\*\s*(?P<charlen>.*))\s*\Z', re.I)
lenkindpattern = re.compile(
    r'\s*(kind\s*=\s*(?P<kind>.*?)\s*(@,@\s*len\s*=\s*(?P<len>.*)|)'
    r'|(len\s*=\s*|)(?P<len2>.*?)\s*(@,@\s*(kind\s*=\s*|)(?P<kind2>.*)'
    r'|(f2py_len\s*=\s*(?P<f2py_len>.*))|))\s*\Z', re.I)
lenarraypattern = re.compile(
    r'\s*(@\(@\s*(?!/)\s*(?P<array>.*?)\s*@\)@\s*\*\s*(?P<len>.*?)|(\*\s*(?P<len2>.*?)|)\s*(@\(@\s*(?!/)\s*(?P<array2>.*?)\s*@\)@|))\s*(=\s*(?P<init>.*?)|(@\(@|)/\s*(?P<init2>.*?)\s*/(@\)@|)|)\s*\Z', re.I)


def removespaces(expr):
    expr = expr.strip()
    if len(expr) <= 1:
        return expr
    expr2 = expr[0]
    for i in range(1, len(expr) - 1):
        if (expr[i] == ' ' and
            ((expr[i + 1] in "()[]{}=+-/* ") or
                (expr[i - 1] in "()[]{}=+-/* "))):
            continue
        expr2 = expr2 + expr[i]
    expr2 = expr2 + expr[-1]
    return expr2


def markinnerspaces(line):
    """
    The function replace all spaces in the input variable line which are
    surrounded with quotation marks, with the triplet "@_@".

    For instance, for the input "a 'b c'" the function returns "a 'b@_@c'"

    Parameters
    ----------
    line : str

    Returns
    -------
    str

    """
    fragment = ''
    inside = False
    current_quote = None
    escaped = ''
    for c in line:
        if escaped == '\\' and c in ['\\', '\'', '"']:
            fragment += c
            escaped = c
            continue
        if not inside and c in ['\'', '"']:
            current_quote = c
        if c == current_quote:
            inside = not inside
        elif c == ' ' and inside:
            fragment += '@_@'
            continue
        fragment += c
        escaped = c  # reset to non-backslash
    return fragment


def updatevars(typespec, selector, attrspec, entitydecl):
    """
    Returns last_name, the variable name without special chars, parenthesis
        or dimension specifiers.

    Alters groupcache to add the name, typespec, attrspec (and possibly value)
    of current variable.
    """
    global groupcache, groupcounter

    last_name = None
    kindselect, charselect, typename = cracktypespec(typespec, selector)
    # Clean up outer commas, whitespace and undesired chars from attrspec
    if attrspec:
        attrspec = [x.strip() for x in markoutercomma(attrspec).split('@,@')]
        l = []
        c = re.compile(r'(?P<start>[a-zA-Z]+)')
        for a in attrspec:
            if not a:
                continue
            m = c.match(a)
            if m:
                s = m.group('start').lower()
                a = s + a[len(s):]
            l.append(a)
        attrspec = l
    el = [x.strip() for x in markoutercomma(entitydecl).split('@,@')]
    el1 = []
    for e in el:
        for e1 in [x.strip() for x in markoutercomma(removespaces(markinnerspaces(e)), comma=' ').split('@ @')]:
            if e1:
                el1.append(e1.replace('@_@', ' '))
    for e in el1:
        m = namepattern.match(e)
        if not m:
            outmess(
                f'updatevars: no name pattern found for entity={repr(e)}. Skipping.\n')
            continue
        ename = rmbadname1(m.group('name'))
        edecl = {}
        if ename in groupcache[groupcounter]['vars']:
            edecl = groupcache[groupcounter]['vars'][ename].copy()
            not_has_typespec = 'typespec' not in edecl
            if not_has_typespec:
                edecl['typespec'] = typespec
            elif typespec and (not typespec == edecl['typespec']):
                outmess('updatevars: attempt to change the type of "%s" ("%s") to "%s". Ignoring.\n' % (
                    ename, edecl['typespec'], typespec))
            if 'kindselector' not in edecl:
                edecl['kindselector'] = copy.copy(kindselect)
            elif kindselect:
                for k in list(kindselect.keys()):
                    if k in edecl['kindselector'] and (not kindselect[k] == edecl['kindselector'][k]):
                        outmess('updatevars: attempt to change the kindselector "%s" of "%s" ("%s") to "%s". Ignoring.\n' % (
                            k, ename, edecl['kindselector'][k], kindselect[k]))
                    else:
                        edecl['kindselector'][k] = copy.copy(kindselect[k])
            if 'charselector' not in edecl and charselect:
                if not_has_typespec:
                    edecl['charselector'] = charselect
                else:
                    errmess('updatevars:%s: attempt to change empty charselector to %r. Ignoring.\n'
                            % (ename, charselect))
            elif charselect:
                for k in list(charselect.keys()):
                    if k in edecl['charselector'] and (not charselect[k] == edecl['charselector'][k]):
                        outmess('updatevars: attempt to change the charselector "%s" of "%s" ("%s") to "%s". Ignoring.\n' % (
                            k, ename, edecl['charselector'][k], charselect[k]))
                    else:
                        edecl['charselector'][k] = copy.copy(charselect[k])
            if 'typename' not in edecl:
                edecl['typename'] = typename
            elif typename and (not edecl['typename'] == typename):
                outmess('updatevars: attempt to change the typename of "%s" ("%s") to "%s". Ignoring.\n' % (
                    ename, edecl['typename'], typename))
            if 'attrspec' not in edecl:
                edecl['attrspec'] = copy.copy(attrspec)
            elif attrspec:
                for a in attrspec:
                    if a not in edecl['attrspec']:
                        edecl['attrspec'].append(a)
        else:
            edecl['typespec'] = copy.copy(typespec)
            edecl['kindselector'] = copy.copy(kindselect)
            edecl['charselector'] = copy.copy(charselect)
            edecl['typename'] = typename
            edecl['attrspec'] = copy.copy(attrspec)
        if 'external' in (edecl.get('attrspec') or []) and e in groupcache[groupcounter]['args']:
            if 'externals' not in groupcache[groupcounter]:
                groupcache[groupcounter]['externals'] = []
            groupcache[groupcounter]['externals'].append(e)
        if m.group('after'):
            m1 = lenarraypattern.match(markouterparen(m.group('after')))
            if m1:
                d1 = m1.groupdict()
                for lk in ['len', 'array', 'init']:
                    if d1[lk + '2'] is not None:
                        d1[lk] = d1[lk + '2']
                        del d1[lk + '2']
                for k in list(d1.keys()):
                    if d1[k] is not None:
                        d1[k] = unmarkouterparen(d1[k])
                    else:
                        del d1[k]

                if 'len' in d1 and 'array' in d1:
                    if d1['len'] == '':
                        d1['len'] = d1['array']
                        del d1['array']
                    elif typespec == 'character':
                        if ('charselector' not in edecl) or (not edecl['charselector']):
                            edecl['charselector'] = {}
                        if 'len' in edecl['charselector']:
                            del edecl['charselector']['len']
                        edecl['charselector']['*'] = d1['len']
                        del d1['len']
                    else:
                        d1['array'] = d1['array'] + ',' + d1['len']
                        del d1['len']
                        errmess('updatevars: "%s %s" is mapped to "%s %s(%s)"\n' % (
                            typespec, e, typespec, ename, d1['array']))

                if 'len' in d1:
                    if typespec in ['complex', 'integer', 'logical', 'real']:
                        if ('kindselector' not in edecl) or (not edecl['kindselector']):
                            edecl['kindselector'] = {}
                        edecl['kindselector']['*'] = d1['len']
                        del d1['len']
                    elif typespec == 'character':
                        if ('charselector' not in edecl) or (not edecl['charselector']):
                            edecl['charselector'] = {}
                        if 'len' in edecl['charselector']:
                            del edecl['charselector']['len']
                        edecl['charselector']['*'] = d1['len']
                        del d1['len']

                if 'init' in d1:
                    if '=' in edecl and (not edecl['='] == d1['init']):
                        outmess('updatevars: attempt to change the init expression of "%s" ("%s") to "%s". Ignoring.\n' % (
                            ename, edecl['='], d1['init']))
                    else:
                        edecl['='] = d1['init']

                if 'array' in d1:
                    dm = f"dimension({d1['array']})"
                    if 'attrspec' not in edecl or (not edecl['attrspec']):
                        edecl['attrspec'] = [dm]
                    else:
                        edecl['attrspec'].append(dm)
                        for dm1 in edecl['attrspec']:
                            if dm1[:9] == 'dimension' and dm1 != dm:
                                del edecl['attrspec'][-1]
                                errmess('updatevars:%s: attempt to change %r to %r. Ignoring.\n'
                                        % (ename, dm1, dm))
                                break

            else:
                outmess('updatevars: could not crack entity declaration "%s". Ignoring.\n' % (
                    ename + m.group('after')))
        for k in list(edecl.keys()):
            if not edecl[k]:
                del edecl[k]
        groupcache[groupcounter]['vars'][ename] = edecl
        if 'varnames' in groupcache[groupcounter]:
            groupcache[groupcounter]['varnames'].append(ename)
        last_name = ename
    return last_name


def cracktypespec(typespec, selector):
    kindselect = None
    charselect = None
    typename = None
    if selector:
        if typespec in ['complex', 'integer', 'logical', 'real']:
            kindselect = kindselector.match(selector)
            if not kindselect:
                outmess(
                    f'cracktypespec: no kindselector pattern found for {repr(selector)}\n')
                return
            kindselect = kindselect.groupdict()
            kindselect['*'] = kindselect['kind2']
            del kindselect['kind2']
            for k in list(kindselect.keys()):
                if not kindselect[k]:
                    del kindselect[k]
            for k, i in list(kindselect.items()):
                kindselect[k] = rmbadname1(i)
        elif typespec == 'character':
            charselect = charselector.match(selector)
            if not charselect:
                outmess(
                    f'cracktypespec: no charselector pattern found for {repr(selector)}\n')
                return
            charselect = charselect.groupdict()
            charselect['*'] = charselect['charlen']
            del charselect['charlen']
            if charselect['lenkind']:
                lenkind = lenkindpattern.match(
                    markoutercomma(charselect['lenkind']))
                lenkind = lenkind.groupdict()
                for lk in ['len', 'kind']:
                    if lenkind[lk + '2']:
                        lenkind[lk] = lenkind[lk + '2']
                    charselect[lk] = lenkind[lk]
                    del lenkind[lk + '2']
                if lenkind['f2py_len'] is not None:
                    # used to specify the length of assumed length strings
                    charselect['f2py_len'] = lenkind['f2py_len']
            del charselect['lenkind']
            for k in list(charselect.keys()):
                if not charselect[k]:
                    del charselect[k]
            for k, i in list(charselect.items()):
                charselect[k] = rmbadname1(i)
        elif typespec == 'type':
            typename = re.match(r'\s*\(\s*(?P<name>\w+)\s*\)', selector, re.I)
            if typename:
                typename = typename.group('name')
            else:
                outmess('cracktypespec: no typename found in %s\n' %
                        (repr(typespec + selector)))
        else:
            outmess(f'cracktypespec: no selector used for {repr(selector)}\n')
    return kindselect, charselect, typename
######


def setattrspec(decl, attr, force=0):
    if not decl:
        decl = {}
    if not attr:
        return decl
    if 'attrspec' not in decl:
        decl['attrspec'] = [attr]
        return decl
    if force:
        decl['attrspec'].append(attr)
    if attr in decl['attrspec']:
        return decl
    if attr == 'static' and 'automatic' not in decl['attrspec']:
        decl['attrspec'].append(attr)
    elif attr == 'automatic' and 'static' not in decl['attrspec']:
        decl['attrspec'].append(attr)
    elif attr == 'public':
        if 'private' not in decl['attrspec']:
            decl['attrspec'].append(attr)
    elif attr == 'private':
        if 'public' not in decl['attrspec']:
            decl['attrspec'].append(attr)
    else:
        decl['attrspec'].append(attr)
    return decl


def setkindselector(decl, sel, force=0):
    if not decl:
        decl = {}
    if not sel:
        return decl
    if 'kindselector' not in decl:
        decl['kindselector'] = sel
        return decl
    for k in list(sel.keys()):
        if force or k not in decl['kindselector']:
            decl['kindselector'][k] = sel[k]
    return decl


def setcharselector(decl, sel, force=0):
    if not decl:
        decl = {}
    if not sel:
        return decl
    if 'charselector' not in decl:
        decl['charselector'] = sel
        return decl

    for k in list(sel.keys()):
        if force or k not in decl['charselector']:
            decl['charselector'][k] = sel[k]
    return decl


def getblockname(block, unknown='unknown'):
    if 'name' in block:
        return block['name']
    return unknown

# post processing


def setmesstext(block):
    global filepositiontext

    try:
        filepositiontext = f"In: {block['from']}:{block['name']}\n"
    except Exception:
        pass


def get_usedict(block):
    usedict = {}
    if 'parent_block' in block:
        usedict = get_usedict(block['parent_block'])
    if 'use' in block:
        usedict.update(block['use'])
    return usedict


def get_useparameters(block, param_map=None):
    global f90modulevars

    if param_map is None:
        param_map = {}
    usedict = get_usedict(block)
    if not usedict:
        return param_map
    for usename, mapping in list(usedict.items()):
        usename = usename.lower()
        if usename not in f90modulevars:
            outmess('get_useparameters: no module %s info used by %s\n' %
                    (usename, block.get('name')))
            continue
        mvars = f90modulevars[usename]
        params = get_parameters(mvars)
        if not params:
            continue
        # XXX: apply mapping
        if mapping:
            errmess(f'get_useparameters: mapping for {mapping} not impl.\n')
        for k, v in list(params.items()):
            if k in param_map:
                outmess('get_useparameters: overriding parameter %s with'
                        ' value from module %s\n' % (repr(k), repr(usename)))
            param_map[k] = v

    return param_map


def postcrack2(block, tab='', param_map=None):
    global f90modulevars

    if not f90modulevars:
        return block
    if isinstance(block, list):
        ret = [postcrack2(g, tab=tab + '\t', param_map=param_map)
               for g in block]
        return ret
    setmesstext(block)
    outmess(f"{tab}Block: {block['name']}\n", 0)

    if param_map is None:
        param_map = get_useparameters(block)

    if param_map is not None and 'vars' in block:
        vars = block['vars']
        for n in list(vars.keys()):
            var = vars[n]
            if 'kindselector' in var:
                kind = var['kindselector']
                if 'kind' in kind:
                    val = kind['kind']
                    if val in param_map:
                        kind['kind'] = param_map[val]
    new_body = [postcrack2(b, tab=tab + '\t', param_map=param_map)
                for b in block['body']]
    block['body'] = new_body

    return block


def postcrack(block, args=None, tab=''):
    """
    TODO:
          function return values
          determine expression types if in argument list
    """
    global usermodules, onlyfunctions

    if isinstance(block, list):
        gret = []
        uret = []
        for g in block:
            setmesstext(g)
            g = postcrack(g, tab=tab + '\t')
            # sort user routines to appear first
            if 'name' in g and '__user__' in g['name']:
                uret.append(g)
            else:
                gret.append(g)
        return uret + gret
    setmesstext(block)
    if not isinstance(block, dict) and 'block' not in block:
        raise Exception('postcrack: Expected block dictionary instead of ' +
                        str(block))
    if 'name' in block and not block['name'] == 'unknown_interface':
        outmess(f"{tab}Block: {block['name']}\n", 0)
    block = analyzeargs(block)
    block = analyzecommon(block)
    block['vars'] = analyzevars(block)
    block['sortvars'] = sortvarnames(block['vars'])
    if block.get('args'):
        args = block['args']
    block['body'] = analyzebody(block, args, tab=tab)

    userisdefined = []
    if 'use' in block:
        useblock = block['use']
        for k in list(useblock.keys()):
            if '__user__' in k:
                userisdefined.append(k)
    else:
        useblock = {}
    name = ''
    if 'name' in block:
        name = block['name']
    # and not userisdefined: # Build a __user__ module
    if block.get('externals'):
        interfaced = []
        if 'interfaced' in block:
            interfaced = block['interfaced']
        mvars = copy.copy(block['vars'])
        if name:
            mname = name + '__user__routines'
        else:
            mname = 'unknown__user__routines'
        if mname in userisdefined:
            i = 1
            while f"{mname}_{i}" in userisdefined:
                i = i + 1
            mname = f"{mname}_{i}"
        interface = {'block': 'interface', 'body': [],
                     'vars': {}, 'name': name + '_user_interface'}
        for e in block['externals']:
            if e in interfaced:
                edef = []
                j = -1
                for b in block['body']:
                    j = j + 1
                    if b['block'] == 'interface':
                        i = -1
                        for bb in b['body']:
                            i = i + 1
                            if 'name' in bb and bb['name'] == e:
                                edef = copy.copy(bb)
                                del b['body'][i]
                                break
                        if edef:
                            if not b['body']:
                                del block['body'][j]
                            del interfaced[interfaced.index(e)]
                            break
                interface['body'].append(edef)
            elif e in mvars and not isexternal(mvars[e]):
                interface['vars'][e] = mvars[e]
        if interface['vars'] or interface['body']:
            block['interfaced'] = interfaced
            mblock = {'block': 'python module', 'body': [
                interface], 'vars': {}, 'name': mname, 'interfaced': block['externals']}
            useblock[mname] = {}
            usermodules.append(mblock)
    if useblock:
        block['use'] = useblock
    return block


def sortvarnames(vars):
    indep = []
    dep = []
    for v in list(vars.keys()):
        if 'depend' in vars[v] and vars[v]['depend']:
            dep.append(v)
        else:
            indep.append(v)
    n = len(dep)
    i = 0
    while dep:  # XXX: How to catch dependence cycles correctly?
        v = dep[0]
        fl = 0
        for w in dep[1:]:
            if w in vars[v]['depend']:
                fl = 1
                break
        if fl:
            dep = dep[1:] + [v]
            i = i + 1
            if i > n:
                errmess('sortvarnames: failed to compute dependencies because'
                        ' of cyclic dependencies between '
                        + ', '.join(dep) + '\n')
                indep = indep + dep
                break
        else:
            indep.append(v)
            dep = dep[1:]
            n = len(dep)
            i = 0
    return indep


def analyzecommon(block):
    if not hascommon(block):
        return block
    commonvars = []
    for k in list(block['common'].keys()):
        comvars = []
        for e in block['common'][k]:
            m = re.match(
                r'\A\s*\b(?P<name>.*?)\b\s*(\((?P<dims>.*?)\)|)\s*\Z', e, re.I)
            if m:
                dims = []
                if m.group('dims'):
                    dims = [x.strip()
                            for x in markoutercomma(m.group('dims')).split('@,@')]
                n = rmbadname1(m.group('name').strip())
                if n in block['vars']:
                    if 'attrspec' in block['vars'][n]:
                        block['vars'][n]['attrspec'].append(
                            f"dimension({','.join(dims)})")
                    else:
                        block['vars'][n]['attrspec'] = [
                            f"dimension({','.join(dims)})"]
                elif dims:
                    block['vars'][n] = {
                        'attrspec': [f"dimension({','.join(dims)})"]}
                else:
                    block['vars'][n] = {}
                if n not in commonvars:
                    commonvars.append(n)
            else:
                n = e
                errmess(
                    f'analyzecommon: failed to extract "<name>[(<dims>)]" from "{e}" in common /{k}/.\n')
            comvars.append(n)
        block['common'][k] = comvars
    if 'commonvars' not in block:
        block['commonvars'] = commonvars
    else:
        block['commonvars'] = block['commonvars'] + commonvars
    return block


def analyzebody(block, args, tab=''):
    global usermodules, skipfuncs, onlyfuncs, f90modulevars

    setmesstext(block)

    maybe_private = {
        key: value
        for key, value in block['vars'].items()
        if 'attrspec' not in value or 'public' not in value['attrspec']
    }

    body = []
    for b in block['body']:
        b['parent_block'] = block
        if b['block'] in ['function', 'subroutine']:
            if args is not None and b['name'] not in args:
                continue
            else:
                as_ = b['args']
            # Add private members to skipfuncs for gh-23879
            if b['name'] in maybe_private.keys():
                skipfuncs.append(b['name'])
            if b['name'] in skipfuncs:
                continue
            if onlyfuncs and b['name'] not in onlyfuncs:
                continue
            b['saved_interface'] = crack2fortrangen(
                b, '\n' + ' ' * 6, as_interface=True)

        else:
            as_ = args
        b = postcrack(b, as_, tab=tab + '\t')
        if b['block'] in ['interface', 'abstract interface'] and \
           not b['body'] and not b.get('implementedby'):
            if 'f2pyenhancements' not in b:
                continue
        if b['block'].replace(' ', '') == 'pythonmodule':
            usermodules.append(b)
        else:
            if b['block'] == 'module':
                f90modulevars[b['name']] = b['vars']
            body.append(b)
    return body


def buildimplicitrules(block):
    setmesstext(block)
    implicitrules = defaultimplicitrules
    attrrules = {}
    if 'implicit' in block:
        if block['implicit'] is None:
            implicitrules = None
            if verbose > 1:
                outmess(
                    f"buildimplicitrules: no implicit rules for routine {repr(block['name'])}.\n")
        else:
            for k in list(block['implicit'].keys()):
                if block['implicit'][k].get('typespec') not in ['static', 'automatic']:
                    implicitrules[k] = block['implicit'][k]
                else:
                    attrrules[k] = block['implicit'][k]['typespec']
    return implicitrules, attrrules


def myeval(e, g=None, l=None):
    """ Like `eval` but returns only integers and floats """
    r = eval(e, g, l)
    if type(r) in [int, float]:
        return r
    raise ValueError(f'r={r!r}')


getlincoef_re_1 = re.compile(r'\A\b\w+\b\Z', re.I)


def getlincoef(e, xset):  # e = a*x+b ; x in xset
    """
    Obtain ``a`` and ``b`` when ``e == "a*x+b"``, where ``x`` is a symbol in
    xset.

    >>> getlincoef('2*x + 1', {'x'})
    (2, 1, 'x')
    >>> getlincoef('3*x + x*2 + 2 + 1', {'x'})
    (5, 3, 'x')
    >>> getlincoef('0', {'x'})
    (0, 0, None)
    >>> getlincoef('0*x', {'x'})
    (0, 0, 'x')
    >>> getlincoef('x*x', {'x'})
    (None, None, None)

    This can be tricked by sufficiently complex expressions

    >>> getlincoef('(x - 0.5)*(x - 1.5)*(x - 1)*x + 2*x + 3', {'x'})
    (2.0, 3.0, 'x')
    """
    try:
        c = int(myeval(e, {}, {}))
        return 0, c, None
    except Exception:
        pass
    if getlincoef_re_1.match(e):
        return 1, 0, e
    len_e = len(e)
    for x in xset:
        if len(x) > len_e:
            continue
        if re.search(r'\w\s*\([^)]*\b' + x + r'\b', e):
            # skip function calls having x as an argument, e.g max(1, x)
            continue
        re_1 = re.compile(r'(?P<before>.*?)\b' + x + r'\b(?P<after>.*)', re.I)
        m = re_1.match(e)
        if m:
            try:
                m1 = re_1.match(e)
                while m1:
                    ee = f"{m1.group('before')}({0}){m1.group('after')}"
                    m1 = re_1.match(ee)
                b = myeval(ee, {}, {})
                m1 = re_1.match(e)
                while m1:
                    ee = f"{m1.group('before')}({1}){m1.group('after')}"
                    m1 = re_1.match(ee)
                a = myeval(ee, {}, {}) - b
                m1 = re_1.match(e)
                while m1:
                    ee = f"{m1.group('before')}({0.5}){m1.group('after')}"
                    m1 = re_1.match(ee)
                c = myeval(ee, {}, {})
                # computing another point to be sure that expression is linear
                m1 = re_1.match(e)
                while m1:
                    ee = f"{m1.group('before')}({1.5}){m1.group('after')}"
                    m1 = re_1.match(ee)
                c2 = myeval(ee, {}, {})
                if (a * 0.5 + b == c and a * 1.5 + b == c2):
                    return a, b, x
            except Exception:
                pass
            break
    return None, None, None


word_pattern = re.compile(r'\b[a-z][\w$]*\b', re.I)


def _get_depend_dict(name, vars, deps):
    if name in vars:
        words = vars[name].get('depend', [])

        if '=' in vars[name] and not isstring(vars[name]):
            for word in word_pattern.findall(vars[name]['=']):
                # The word_pattern may return values that are not
                # only variables, they can be string content for instance
                if word not in words and word in vars and word != name:
                    words.append(word)
        for word in words[:]:
            for w in deps.get(word, []) \
                    or _get_depend_dict(word, vars, deps):
                if w not in words:
                    words.append(w)
    else:
        outmess(f'_get_depend_dict: no dependence info for {repr(name)}\n')
        words = []
    deps[name] = words
    return words


def _calc_depend_dict(vars):
    names = list(vars.keys())
    depend_dict = {}
    for n in names:
        _get_depend_dict(n, vars, depend_dict)
    return depend_dict


def get_sorted_names(vars):
    depend_dict = _calc_depend_dict(vars)
    names = []
    for name in list(depend_dict.keys()):
        if not depend_dict[name]:
            names.append(name)
            del depend_dict[name]
    while depend_dict:
        for name, lst in list(depend_dict.items()):
            new_lst = [n for n in lst if n in depend_dict]
            if not new_lst:
                names.append(name)
                del depend_dict[name]
            else:
                depend_dict[name] = new_lst
    return [name for name in names if name in vars]


def _kind_func(string):
    # XXX: return something sensible.
    if string[0] in "'\"":
        string = string[1:-1]
    if real16pattern.match(string):
        return 8
    elif real8pattern.match(string):
        return 4
    return 'kind(' + string + ')'


def _selected_int_kind_func(r):
    # XXX: This should be processor dependent
    m = 10 ** r
    if m <= 2 ** 8:
        return 1
    if m <= 2 ** 16:
        return 2
    if m <= 2 ** 32:
        return 4
    if m <= 2 ** 63:
        return 8
    if m <= 2 ** 128:
        return 16
    return -1


def _selected_real_kind_func(p, r=0, radix=0):
    # XXX: This should be processor dependent
    # This is only verified for 0 <= p <= 20, possibly good for p <= 33 and above
    if p < 7:
        return 4
    if p < 16:
        return 8
    machine = platform.machine().lower()
    if machine.startswith(('aarch64', 'alpha', 'arm64', 'loongarch', 'mips', 'power', 'ppc', 'riscv', 's390x', 'sparc')):
        if p <= 33:
            return 16
    elif p < 19:
        return 10
    elif p <= 33:
        return 16
    return -1


def get_parameters(vars, global_params={}):
    params = copy.copy(global_params)
    g_params = copy.copy(global_params)
    for name, func in [('kind', _kind_func),
                       ('selected_int_kind', _selected_int_kind_func),
                       ('selected_real_kind', _selected_real_kind_func), ]:
        if name not in g_params:
            g_params[name] = func
    param_names = []
    for n in get_sorted_names(vars):
        if 'attrspec' in vars[n] and 'parameter' in vars[n]['attrspec']:
            param_names.append(n)
    kind_re = re.compile(r'\bkind\s*\(\s*(?P<value>.*)\s*\)', re.I)
    selected_int_kind_re = re.compile(
        r'\bselected_int_kind\s*\(\s*(?P<value>.*)\s*\)', re.I)
    selected_kind_re = re.compile(
        r'\bselected_(int|real)_kind\s*\(\s*(?P<value>.*)\s*\)', re.I)
    for n in param_names:
        if '=' in vars[n]:
            v = vars[n]['=']
            if islogical(vars[n]):
                v = v.lower()
                for repl in [
                    ('.false.', 'False'),
                    ('.true.', 'True'),
                    # TODO: test .eq., .neq., etc replacements.
                ]:
                    v = v.replace(*repl)

            v = kind_re.sub(r'kind("\1")', v)
            v = selected_int_kind_re.sub(r'selected_int_kind(\1)', v)

            # We need to act according to the data.
            # The easy case is if the data has a kind-specifier,
            # then we may easily remove those specifiers.
            # However, it may be that the user uses other specifiers...(!)
            is_replaced = False

            if 'kindselector' in vars[n]:
                # Remove kind specifier (including those defined
                # by parameters)
                if 'kind' in vars[n]['kindselector']:
                    orig_v_len = len(v)
                    v = v.replace('_' + vars[n]['kindselector']['kind'], '')
                    # Again, this will be true if even a single specifier
                    # has been replaced, see comment above.
                    is_replaced = len(v) < orig_v_len

            if not is_replaced:
                if not selected_kind_re.match(v):
                    v_ = v.split('_')
                    # In case there are additive parameters
                    if len(v_) > 1:
                        v = ''.join(v_[:-1]).lower().replace(v_[-1].lower(), '')

            # Currently this will not work for complex numbers.
            # There is missing code for extracting a complex number,
            # which may be defined in either of these:
            #  a) (Re, Im)
            #  b) cmplx(Re, Im)
            #  c) dcmplx(Re, Im)
            #  d) cmplx(Re, Im, <prec>)

            if isdouble(vars[n]):
                tt = list(v)
                for m in real16pattern.finditer(v):
                    tt[m.start():m.end()] = list(
                        v[m.start():m.end()].lower().replace('d', 'e'))
                v = ''.join(tt)

            elif iscomplex(vars[n]):
                outmess(f'get_parameters[TODO]: '
                        f'implement evaluation of complex expression {v}\n')

            dimspec = ([s.removeprefix('dimension').strip()
                        for s in vars[n]['attrspec']
                       if s.startswith('dimension')] or [None])[0]

            # Handle _dp for gh-6624
            # Also fixes gh-20460
            if real16pattern.search(v):
                v = 8
            elif real8pattern.search(v):
                v = 4
            try:
                params[n] = param_eval(v, g_params, params, dimspec=dimspec)
            except Exception as msg:
                params[n] = v
                outmess(f'get_parameters: got "{msg}" on {n!r}\n')

            if isstring(vars[n]) and isinstance(params[n], int):
                params[n] = chr(params[n])
            nl = n.lower()
            if nl != n:
                params[nl] = params[n]
        else:
            print(vars[n])
            outmess(f'get_parameters:parameter {n!r} does not have value?!\n')
    return params


def _eval_length(length, params):
    if length in ['(:)', '(*)', '*']:
        return '(*)'
    return _eval_scalar(length, params)


_is_kind_number = re.compile(r'\d+_').match


def _eval_scalar(value, params):
    if _is_kind_number(value):
        value = value.split('_')[0]
    try:
        # TODO: use symbolic from PR #19805
        value = eval(value, {}, params)
        value = (repr if isinstance(value, str) else str)(value)
    except (NameError, SyntaxError, TypeError):
        return value
    except Exception as msg:
        errmess('"%s" in evaluating %r '
                '(available names: %s)\n'
                % (msg, value, list(params.keys())))
    return value


def analyzevars(block):
    """
    Sets correct dimension information for each variable/parameter
    """

    global f90modulevars

    setmesstext(block)
    implicitrules, attrrules = buildimplicitrules(block)
    vars = copy.copy(block['vars'])
    if block['block'] == 'function' and block['name'] not in vars:
        vars[block['name']] = {}
    if '' in block['vars']:
        del vars['']
        if 'attrspec' in block['vars']['']:
            gen = block['vars']['']['attrspec']
            for n in set(vars) | {b['name'] for b in block['body']}:
                for k in ['public', 'private']:
                    if k in gen:
                        vars[n] = setattrspec(vars.get(n, {}), k)
    svars = []
    args = block['args']
    for a in args:
        try:
            vars[a]
            svars.append(a)
        except KeyError:
            pass
    for n in list(vars.keys()):
        if n not in args:
            svars.append(n)

    params = get_parameters(vars, get_useparameters(block))
    # At this point, params are read and interpreted, but
    # the params used to define vars are not yet parsed
    dep_matches = {}
    name_match = re.compile(r'[A-Za-z][\w$]*').match
    for v in list(vars.keys()):
        m = name_match(v)
        if m:
            n = v[m.start():m.end()]
            try:
                dep_matches[n]
            except KeyError:
                dep_matches[n] = re.compile(r'.*\b%s\b' % (v), re.I).match
    for n in svars:
        if n[0] in list(attrrules.keys()):
            vars[n] = setattrspec(vars[n], attrrules[n[0]])
        if 'typespec' not in vars[n]:
            if not ('attrspec' in vars[n] and 'external' in vars[n]['attrspec']):
                if implicitrules:
                    ln0 = n[0].lower()
                    for k in list(implicitrules[ln0].keys()):
                        if k == 'typespec' and implicitrules[ln0][k] == 'undefined':
                            continue
                        if k not in vars[n]:
                            vars[n][k] = implicitrules[ln0][k]
                        elif k == 'attrspec':
                            for l in implicitrules[ln0][k]:
                                vars[n] = setattrspec(vars[n], l)
                elif n in block['args']:
                    outmess('analyzevars: typespec of variable %s is not defined in routine %s.\n' % (
                        repr(n), block['name']))
        if 'charselector' in vars[n]:
            if 'len' in vars[n]['charselector']:
                l = vars[n]['charselector']['len']
                try:
                    l = str(eval(l, {}, params))
                except Exception:
                    pass
                vars[n]['charselector']['len'] = l

        if 'kindselector' in vars[n]:
            if 'kind' in vars[n]['kindselector']:
                l = vars[n]['kindselector']['kind']
                try:
                    l = str(eval(l, {}, params))
                except Exception:
                    pass
                vars[n]['kindselector']['kind'] = l

        dimension_exprs = {}
        if 'attrspec' in vars[n]:
            attr = vars[n]['attrspec']
            attr.reverse()
            vars[n]['attrspec'] = []
            dim, intent, depend, check, note = None, None, None, None, None
            for a in attr:
                if a[:9] == 'dimension':
                    dim = (a[9:].strip())[1:-1]
                elif a[:6] == 'intent':
                    intent = (a[6:].strip())[1:-1]
                elif a[:6] == 'depend':
                    depend = (a[6:].strip())[1:-1]
                elif a[:5] == 'check':
                    check = (a[5:].strip())[1:-1]
                elif a[:4] == 'note':
                    note = (a[4:].strip())[1:-1]
                else:
                    vars[n] = setattrspec(vars[n], a)
                if intent:
                    if 'intent' not in vars[n]:
                        vars[n]['intent'] = []
                    for c in [x.strip() for x in markoutercomma(intent).split('@,@')]:
                        # Remove spaces so that 'in out' becomes 'inout'
                        tmp = c.replace(' ', '')
                        if tmp not in vars[n]['intent']:
                            vars[n]['intent'].append(tmp)
                    intent = None
                if note:
                    note = note.replace('\\n\\n', '\n\n')
                    note = note.replace('\\n ', '\n')
                    if 'note' not in vars[n]:
                        vars[n]['note'] = [note]
                    else:
                        vars[n]['note'].append(note)
                    note = None
                if depend is not None:
                    if 'depend' not in vars[n]:
                        vars[n]['depend'] = []
                    for c in rmbadname([x.strip() for x in markoutercomma(depend).split('@,@')]):
                        if c not in vars[n]['depend']:
                            vars[n]['depend'].append(c)
                    depend = None
                if check is not None:
                    if 'check' not in vars[n]:
                        vars[n]['check'] = []
                    for c in [x.strip() for x in markoutercomma(check).split('@,@')]:
                        if c not in vars[n]['check']:
                            vars[n]['check'].append(c)
                    check = None
            if dim and 'dimension' not in vars[n]:
                vars[n]['dimension'] = []
                for d in rmbadname(
                        [x.strip() for x in markoutercomma(dim).split('@,@')]
                ):
                    # d is the expression inside the dimension declaration
                    # Evaluate `d` with respect to params
                    try:
                        # the dimension for this variable depends on a
                        # previously defined parameter
                        d = param_parse(d, params)
                    except (ValueError, IndexError, KeyError):
                        outmess(
                            'analyzevars: could not parse dimension for '
                            f'variable {d!r}\n'
                        )

                    dim_char = ':' if d == ':' else '*'
                    if d == dim_char:
                        dl = [dim_char]
                    else:
                        dl = markoutercomma(d, ':').split('@:@')
                    if len(dl) == 2 and '*' in dl:  # e.g. dimension(5:*)
                        dl = ['*']
                        d = '*'
                    if len(dl) == 1 and dl[0] != dim_char:
                        dl = ['1', dl[0]]
                    if len(dl) == 2:
                        d1, d2 = map(symbolic.Expr.parse, dl)
                        dsize = d2 - d1 + 1
                        d = dsize.tostring(language=symbolic.Language.C)
                        # find variables v that define d as a linear
                        # function, `d == a * v + b`, and store
                        # coefficients a and b for further analysis.
                        solver_and_deps = {}
                        for v in block['vars']:
                            s = symbolic.as_symbol(v)
                            if dsize.contains(s):
                                try:
                                    a, b = dsize.linear_solve(s)

                                    def solve_v(s, a=a, b=b):
                                        return (s - b) / a

                                    all_symbols = set(a.symbols())
                                    all_symbols.update(b.symbols())
                                except RuntimeError as msg:
                                    # d is not a linear function of v,
                                    # however, if v can be determined
                                    # from d using other means,
                                    # implement the corresponding
                                    # solve_v function here.
                                    solve_v = None
                                    all_symbols = set(dsize.symbols())
                                v_deps = {
                                    s.data for s in all_symbols
                                    if s.data in vars}
                                solver_and_deps[v] = solve_v, list(v_deps)
                        # Note that dsize may contain symbols that are
                        # not defined in block['vars']. Here we assume
                        # these correspond to Fortran/C intrinsic
                        # functions or that are defined by other
                        # means. We'll let the compiler validate the
                        # definiteness of such symbols.
                        dimension_exprs[d] = solver_and_deps
                    vars[n]['dimension'].append(d)

        if 'check' not in vars[n] and 'args' in block and n in block['args']:
            # n is an argument that has no checks defined. Here we
            # generate some consistency checks for n, and when n is an
            # array, generate checks for its dimensions and construct
            # initialization expressions.
            n_deps = vars[n].get('depend', [])
            n_checks = []
            n_is_input = l_or(isintent_in, isintent_inout,
                              isintent_inplace)(vars[n])
            if isarray(vars[n]):  # n is array
                for i, d in enumerate(vars[n]['dimension']):
                    coeffs_and_deps = dimension_exprs.get(d)
                    if coeffs_and_deps is None:
                        # d is `:` or `*` or a constant expression
                        pass
                    elif n_is_input:
                        # n is an input array argument and its shape
                        # may define variables used in dimension
                        # specifications.
                        for v, (solver, deps) in coeffs_and_deps.items():
                            def compute_deps(v, deps):
                                for v1 in coeffs_and_deps.get(v, [None, []])[1]:
                                    if v1 not in deps:
                                        deps.add(v1)
                                        compute_deps(v1, deps)
                            all_deps = set()
                            compute_deps(v, all_deps)
                            if (v in n_deps
                                 or '=' in vars[v]
                                 or 'depend' in vars[v]):
                                # Skip a variable that
                                # - n depends on
                                # - has user-defined initialization expression
                                # - has user-defined dependencies
                                continue
                            if solver is not None and v not in all_deps:
                                # v can be solved from d, hence, we
                                # make it an optional argument with
                                # initialization expression:
                                is_required = False
                                init = solver(symbolic.as_symbol(
                                    f'shape({n}, {i})'))
                                init = init.tostring(
                                    language=symbolic.Language.C)
                                vars[v]['='] = init
                                # n needs to be initialized before v. So,
                                # making v dependent on n and on any
                                # variables in solver or d.
                                vars[v]['depend'] = [n] + deps
                                if 'check' not in vars[v]:
                                    # add check only when no
                                    # user-specified checks exist
                                    vars[v]['check'] = [
                                        f'shape({n}, {i}) == {d}']
                            else:
                                # d is a non-linear function on v,
                                # hence, v must be a required input
                                # argument that n will depend on
                                is_required = True
                                if 'intent' not in vars[v]:
                                    vars[v]['intent'] = []
                                if 'in' not in vars[v]['intent']:
                                    vars[v]['intent'].append('in')
                                # v needs to be initialized before n
                                n_deps.append(v)
                                n_checks.append(
                                    f'shape({n}, {i}) == {d}')
                            v_attr = vars[v].get('attrspec', [])
                            if not ('optional' in v_attr
                                    or 'required' in v_attr):
                                v_attr.append(
                                    'required' if is_required else 'optional')
                            if v_attr:
                                vars[v]['attrspec'] = v_attr
                    if coeffs_and_deps is not None:
                        # extend v dependencies with ones specified in attrspec
                        for v, (solver, deps) in coeffs_and_deps.items():
                            v_deps = vars[v].get('depend', [])
                            for aa in vars[v].get('attrspec', []):
                                if aa.startswith('depend'):
                                    aa = ''.join(aa.split())
                                    v_deps.extend(aa[7:-1].split(','))
                            if v_deps:
                                vars[v]['depend'] = list(set(v_deps))
                            if n not in v_deps:
                                n_deps.append(v)
            elif isstring(vars[n]):
                if 'charselector' in vars[n]:
                    if '*' in vars[n]['charselector']:
                        length = _eval_length(vars[n]['charselector']['*'],
                                              params)
                        vars[n]['charselector']['*'] = length
                    elif 'len' in vars[n]['charselector']:
                        length = _eval_length(vars[n]['charselector']['len'],
                                              params)
                        del vars[n]['charselector']['len']
                        vars[n]['charselector']['*'] = length
            if n_checks:
                vars[n]['check'] = n_checks
            if n_deps:
                vars[n]['depend'] = list(set(n_deps))

        if '=' in vars[n]:
            if 'attrspec' not in vars[n]:
                vars[n]['attrspec'] = []
            if ('optional' not in vars[n]['attrspec']) and \
               ('required' not in vars[n]['attrspec']):
                vars[n]['attrspec'].append('optional')
            if 'depend' not in vars[n]:
                vars[n]['depend'] = []
                for v, m in list(dep_matches.items()):
                    if m(vars[n]['=']):
                        vars[n]['depend'].append(v)
                if not vars[n]['depend']:
                    del vars[n]['depend']
            if isscalar(vars[n]):
                vars[n]['='] = _eval_scalar(vars[n]['='], params)

    for n in list(vars.keys()):
        if n == block['name']:  # n is block name
            if 'note' in vars[n]:
                block['note'] = vars[n]['note']
            if block['block'] == 'function':
                if 'result' in block and block['result'] in vars:
                    vars[n] = appenddecl(vars[n], vars[block['result']])
                if 'prefix' in block:
                    pr = block['prefix']
                    pr1 = pr.replace('pure', '')
                    ispure = (not pr == pr1)
                    pr = pr1.replace('recursive', '')
                    isrec = (not pr == pr1)
                    m = typespattern[0].match(pr)
                    if m:
                        typespec, selector, attr, edecl = cracktypespec0(
                            m.group('this'), m.group('after'))
                        kindselect, charselect, typename = cracktypespec(
                            typespec, selector)
                        vars[n]['typespec'] = typespec
                        try:
                            if block['result']:
                                vars[block['result']]['typespec'] = typespec
                        except Exception:
                            pass
                        if kindselect:
                            if 'kind' in kindselect:
                                try:
                                    kindselect['kind'] = eval(
                                        kindselect['kind'], {}, params)
                                except Exception:
                                    pass
                            vars[n]['kindselector'] = kindselect
                        if charselect:
                            vars[n]['charselector'] = charselect
                        if typename:
                            vars[n]['typename'] = typename
                        if ispure:
                            vars[n] = setattrspec(vars[n], 'pure')
                        if isrec:
                            vars[n] = setattrspec(vars[n], 'recursive')
                    else:
                        outmess(
                            f"analyzevars: prefix ({repr(block['prefix'])}) were not used\n")
    if block['block'] not in ['module', 'pythonmodule', 'python module', 'block data']:
        if 'commonvars' in block:
            neededvars = copy.copy(block['args'] + block['commonvars'])
        else:
            neededvars = copy.copy(block['args'])
        for n in list(vars.keys()):
            if l_or(isintent_callback, isintent_aux)(vars[n]):
                neededvars.append(n)
        if 'entry' in block:
            neededvars.extend(list(block['entry'].keys()))
            for k in list(block['entry'].keys()):
                for n in block['entry'][k]:
                    if n not in neededvars:
                        neededvars.append(n)
        if block['block'] == 'function':
            if 'result' in block:
                neededvars.append(block['result'])
            else:
                neededvars.append(block['name'])
        if block['block'] in ['subroutine', 'function']:
            name = block['name']
            if name in vars and 'intent' in vars[name]:
                block['intent'] = vars[name]['intent']
        if block['block'] == 'type':
            neededvars.extend(list(vars.keys()))
        for n in list(vars.keys()):
            if n not in neededvars:
                del vars[n]
    return vars


analyzeargs_re_1 = re.compile(r'\A[a-z]+[\w$]*\Z', re.I)


def param_eval(v, g_params, params, dimspec=None):
    """
    Creates a dictionary of indices and values for each parameter in a
    parameter array to be evaluated later.

    WARNING: It is not possible to initialize multidimensional array
    parameters e.g. dimension(-3:1, 4, 3:5) at this point. This is because in
    Fortran initialization through array constructor requires the RESHAPE
    intrinsic function. Since the right-hand side of the parameter declaration
    is not executed in f2py, but rather at the compiled c/fortran extension,
    later, it is not possible to execute a reshape of a parameter array.
    One issue remains: if the user wants to access the array parameter from
    python, we should either
    1) allow them to access the parameter array using python standard indexing
       (which is often incompatible with the original fortran indexing)
    2) allow the parameter array to be accessed in python as a dictionary with
       fortran indices as keys
    We are choosing 2 for now.
    """
    if dimspec is None:
        try:
            p = eval(v, g_params, params)
        except Exception as msg:
            p = v
            outmess(f'param_eval: got "{msg}" on {v!r}\n')
        return p

    # This is an array parameter.
    # First, we parse the dimension information
    if len(dimspec) < 2 or dimspec[::len(dimspec) - 1] != "()":
        raise ValueError(f'param_eval: dimension {dimspec} can\'t be parsed')
    dimrange = dimspec[1:-1].split(',')
    if len(dimrange) == 1:
        # e.g. dimension(2) or dimension(-1:1)
        dimrange = dimrange[0].split(':')
        # now, dimrange is a list of 1 or 2 elements
        if len(dimrange) == 1:
            bound = param_parse(dimrange[0], params)
            dimrange = range(1, int(bound) + 1)
        else:
            lbound = param_parse(dimrange[0], params)
            ubound = param_parse(dimrange[1], params)
            dimrange = range(int(lbound), int(ubound) + 1)
    else:
        raise ValueError('param_eval: multidimensional array parameters '
                         f'{dimspec} not supported')

    # Parse parameter value
    v = (v[2:-2] if v.startswith('(/') else v).split(',')
    v_eval = []
    for item in v:
        try:
            item = eval(item, g_params, params)
        except Exception as msg:
            outmess(f'param_eval: got "{msg}" on {item!r}\n')
        v_eval.append(item)

    p = dict(zip(dimrange, v_eval))

    return p


def param_parse(d, params):
    """Recursively parse array dimensions.

    Parses the declaration of an array variable or parameter
    `dimension` keyword, and is called recursively if the
    dimension for this array is a previously defined parameter
    (found in `params`).

    Parameters
    ----------
    d : str
        Fortran expression describing the dimension of an array.
    params : dict
        Previously parsed parameters declared in the Fortran source file.

    Returns
    -------
    out : str
        Parsed dimension expression.

    Examples
    --------

    * If the line being analyzed is

      `integer, parameter, dimension(2) :: pa = (/ 3, 5 /)`

      then `d = 2` and we return immediately, with

    >>> d = '2'
    >>> param_parse(d, params)
    2

    * If the line being analyzed is

      `integer, parameter, dimension(pa) :: pb = (/1, 2, 3/)`

      then `d = 'pa'`; since `pa` is a previously parsed parameter,
      and `pa = 3`, we call `param_parse` recursively, to obtain

    >>> d = 'pa'
    >>> params = {'pa': 3}
    >>> param_parse(d, params)
    3

    * If the line being analyzed is

      `integer, parameter, dimension(pa(1)) :: pb = (/1, 2, 3/)`

      then `d = 'pa(1)'`; since `pa` is a previously parsed parameter,
      and `pa(1) = 3`, we call `param_parse` recursively, to obtain

    >>> d = 'pa(1)'
    >>> params = dict(pa={1: 3, 2: 5})
    >>> param_parse(d, params)
    3
    """
    if "(" in d:
        # this dimension expression is an array
        dname = d[:d.find("(")]
        ddims = d[d.find("(") + 1:d.rfind(")")]
        # this dimension expression is also a parameter;
        # parse it recursively
        index = int(param_parse(ddims, params))
        return str(params[dname][index])
    elif d in params:
        return str(params[d])
    else:
        for p in params:
            re_1 = re.compile(
                r'(?P<before>.*?)\b' + p + r'\b(?P<after>.*)', re.I
            )
            m = re_1.match(d)
            while m:
                d = m.group('before') + \
                    str(params[p]) + m.group('after')
                m = re_1.match(d)
        return d


def expr2name(a, block, args=[]):
    orig_a = a
    a_is_expr = not analyzeargs_re_1.match(a)
    if a_is_expr:  # `a` is an expression
        implicitrules, attrrules = buildimplicitrules(block)
        at = determineexprtype(a, block['vars'], implicitrules)
        na = 'e_'
        for c in a:
            c = c.lower()
            if c not in string.ascii_lowercase + string.digits:
                c = '_'
            na = na + c
        if na[-1] == '_':
            na = na + 'e'
        else:
            na = na + '_e'
        a = na
        while a in block['vars'] or a in block['args']:
            a = a + 'r'
    if a in args:
        k = 1
        while a + str(k) in args:
            k = k + 1
        a = a + str(k)
    if a_is_expr:
        block['vars'][a] = at
    else:
        if a not in block['vars']:
            block['vars'][a] = block['vars'].get(orig_a, {})
        if 'externals' in block and orig_a in block['externals'] + block['interfaced']:
            block['vars'][a] = setattrspec(block['vars'][a], 'external')
    return a


def analyzeargs(block):
    setmesstext(block)
    implicitrules, _ = buildimplicitrules(block)
    if 'args' not in block:
        block['args'] = []
    args = []
    for a in block['args']:
        a = expr2name(a, block, args)
        args.append(a)
    block['args'] = args
    if 'entry' in block:
        for k, args1 in list(block['entry'].items()):
            for a in args1:
                if a not in block['vars']:
                    block['vars'][a] = {}

    for b in block['body']:
        if b['name'] in args:
            if 'externals' not in block:
                block['externals'] = []
            if b['name'] not in block['externals']:
                block['externals'].append(b['name'])
    if 'result' in block and block['result'] not in block['vars']:
        block['vars'][block['result']] = {}
    return block


determineexprtype_re_1 = re.compile(r'\A\(.+?,.+?\)\Z', re.I)
determineexprtype_re_2 = re.compile(r'\A[+-]?\d+(_(?P<name>\w+)|)\Z', re.I)
determineexprtype_re_3 = re.compile(
    r'\A[+-]?[\d.]+[-\d+de.]*(_(?P<name>\w+)|)\Z', re.I)
determineexprtype_re_4 = re.compile(r'\A\(.*\)\Z', re.I)
determineexprtype_re_5 = re.compile(r'\A(?P<name>\w+)\s*\(.*?\)\s*\Z', re.I)


def _ensure_exprdict(r):
    if isinstance(r, int):
        return {'typespec': 'integer'}
    if isinstance(r, float):
        return {'typespec': 'real'}
    if isinstance(r, complex):
        return {'typespec': 'complex'}
    if isinstance(r, dict):
        return r
    raise AssertionError(repr(r))


def determineexprtype(expr, vars, rules={}):
    if expr in vars:
        return _ensure_exprdict(vars[expr])
    expr = expr.strip()
    if determineexprtype_re_1.match(expr):
        return {'typespec': 'complex'}
    m = determineexprtype_re_2.match(expr)
    if m:
        if 'name' in m.groupdict() and m.group('name'):
            outmess(
                f'determineexprtype: selected kind types not supported ({repr(expr)})\n')
        return {'typespec': 'integer'}
    m = determineexprtype_re_3.match(expr)
    if m:
        if 'name' in m.groupdict() and m.group('name'):
            outmess(
                f'determineexprtype: selected kind types not supported ({repr(expr)})\n')
        return {'typespec': 'real'}
    for op in ['+', '-', '*', '/']:
        for e in [x.strip() for x in markoutercomma(expr, comma=op).split('@' + op + '@')]:
            if e in vars:
                return _ensure_exprdict(vars[e])
    t = {}
    if determineexprtype_re_4.match(expr):  # in parenthesis
        t = determineexprtype(expr[1:-1], vars, rules)
    else:
        m = determineexprtype_re_5.match(expr)
        if m:
            rn = m.group('name')
            t = determineexprtype(m.group('name'), vars, rules)
            if t and 'attrspec' in t:
                del t['attrspec']
            if not t:
                if rn[0] in rules:
                    return _ensure_exprdict(rules[rn[0]])
    if expr[0] in '\'"':
        return {'typespec': 'character', 'charselector': {'*': '*'}}
    if not t:
        outmess(
            f'determineexprtype: could not determine expressions ({repr(expr)}) type.\n')
    return t

######


def crack2fortrangen(block, tab='\n', as_interface=False):
    global skipfuncs, onlyfuncs

    setmesstext(block)
    ret = ''
    if isinstance(block, list):
        for g in block:
            if g and g['block'] in ['function', 'subroutine']:
                if g['name'] in skipfuncs:
                    continue
                if onlyfuncs and g['name'] not in onlyfuncs:
                    continue
            ret = ret + crack2fortrangen(g, tab, as_interface=as_interface)
        return ret
    prefix = ''
    name = ''
    args = ''
    blocktype = block['block']
    if blocktype == 'program':
        return ''
    argsl = []
    if 'name' in block:
        name = block['name']
    if 'args' in block:
        vars = block['vars']
        for a in block['args']:
            a = expr2name(a, block, argsl)
            if not isintent_callback(vars[a]):
                argsl.append(a)
        if block['block'] == 'function' or argsl:
            args = f"({','.join(argsl)})"
    f2pyenhancements = ''
    if 'f2pyenhancements' in block:
        for k in list(block['f2pyenhancements'].keys()):
            f2pyenhancements = '%s%s%s %s' % (
                f2pyenhancements, tab + tabchar, k, block['f2pyenhancements'][k])
    intent_lst = block.get('intent', [])[:]
    if blocktype == 'function' and 'callback' in intent_lst:
        intent_lst.remove('callback')
    if intent_lst:
        f2pyenhancements = '%s%sintent(%s) %s' %\
                           (f2pyenhancements, tab + tabchar,
                            ','.join(intent_lst), name)
    use = ''
    if 'use' in block:
        use = use2fortran(block['use'], tab + tabchar)
    common = ''
    if 'common' in block:
        common = common2fortran(block['common'], tab + tabchar)
    if name == 'unknown_interface':
        name = ''
    result = ''
    if 'result' in block:
        result = f" result ({block['result']})"
        if block['result'] not in argsl:
            argsl.append(block['result'])
    body = crack2fortrangen(block['body'], tab + tabchar, as_interface=as_interface)
    vars = vars2fortran(
        block, block['vars'], argsl, tab + tabchar, as_interface=as_interface)
    mess = ''
    if 'from' in block and not as_interface:
        mess = f"! in {block['from']}"
    if 'entry' in block:
        entry_stmts = ''
        for k, i in list(block['entry'].items()):
            entry_stmts = f"{entry_stmts}{tab + tabchar}entry {k}({','.join(i)})"
        body = body + entry_stmts
    if blocktype == 'block data' and name == '_BLOCK_DATA_':
        name = ''
    ret = '%s%s%s %s%s%s %s%s%s%s%s%s%send %s %s' % (
        tab, prefix, blocktype, name, args, result, mess, f2pyenhancements, use, vars, common, body, tab, blocktype, name)
    return ret


def common2fortran(common, tab=''):
    ret = ''
    for k in list(common.keys()):
        if k == '_BLNK_':
            ret = f"{ret}{tab}common {','.join(common[k])}"
        else:
            ret = f"{ret}{tab}common /{k}/ {','.join(common[k])}"
    return ret


def use2fortran(use, tab=''):
    ret = ''
    for m in list(use.keys()):
        ret = f'{ret}{tab}use {m},'
        if use[m] == {}:
            if ret and ret[-1] == ',':
                ret = ret[:-1]
            continue
        if 'only' in use[m] and use[m]['only']:
            ret = f'{ret} only:'
        if 'map' in use[m] and use[m]['map']:
            c = ' '
            for k in list(use[m]['map'].keys()):
                if k == use[m]['map'][k]:
                    ret = f'{ret}{c}{k}'
                    c = ','
                else:
                    ret = f"{ret}{c}{k}=>{use[m]['map'][k]}"
                    c = ','
        if ret and ret[-1] == ',':
            ret = ret[:-1]
    return ret


def true_intent_list(var):
    lst = var['intent']
    ret = []
    for intent in lst:
        try:
            f = globals()[f'isintent_{intent}']
        except KeyError:
            pass
        else:
            if f(var):
                ret.append(intent)
    return ret


def vars2fortran(block, vars, args, tab='', as_interface=False):
    setmesstext(block)
    ret = ''
    nout = []
    for a in args:
        if a in block['vars']:
            nout.append(a)
    if 'commonvars' in block:
        for a in block['commonvars']:
            if a in vars:
                if a not in nout:
                    nout.append(a)
            else:
                errmess(
                    f'vars2fortran: Confused?!: "{a}" is not defined in vars.\n')
    if 'varnames' in block:
        nout.extend(block['varnames'])
    if not as_interface:
        for a in list(vars.keys()):
            if a not in nout:
                nout.append(a)
    for a in nout:
        if 'depend' in vars[a]:
            for d in vars[a]['depend']:
                if d in vars and 'depend' in vars[d] and a in vars[d]['depend']:
                    errmess(
                        f'vars2fortran: Warning: cross-dependence between variables "{a}" and "{d}\"\n')
        if 'externals' in block and a in block['externals']:
            if isintent_callback(vars[a]):
                ret = f'{ret}{tab}intent(callback) {a}'
            ret = f'{ret}{tab}external {a}'
            if isoptional(vars[a]):
                ret = f'{ret}{tab}optional {a}'
            if a in vars and 'typespec' not in vars[a]:
                continue
            cont = 1
            for b in block['body']:
                if a == b['name'] and b['block'] == 'function':
                    cont = 0
                    break
            if cont:
                continue
        if a not in vars:
            show(vars)
            outmess(f'vars2fortran: No definition for argument "{a}".\n')
            continue
        if a == block['name']:
            if block['block'] != 'function' or block.get('result'):
                # 1) skip declaring a variable that name matches with
                #    subroutine name
                # 2) skip declaring function when its type is
                #    declared via `result` construction
                continue
        if 'typespec' not in vars[a]:
            if 'attrspec' in vars[a] and 'external' in vars[a]['attrspec']:
                if a in args:
                    ret = f'{ret}{tab}external {a}'
                continue
            show(vars[a])
            outmess(f'vars2fortran: No typespec for argument "{a}".\n')
            continue
        vardef = vars[a]['typespec']
        if vardef == 'type' and 'typename' in vars[a]:
            vardef = f"{vardef}({vars[a]['typename']})"
        selector = {}
        if 'kindselector' in vars[a]:
            selector = vars[a]['kindselector']
        elif 'charselector' in vars[a]:
            selector = vars[a]['charselector']
        if '*' in selector:
            if selector['*'] in ['*', ':']:
                vardef = f"{vardef}*({selector['*']})"
            else:
                vardef = f"{vardef}*{selector['*']}"
        elif 'len' in selector:
            vardef = f"{vardef}(len={selector['len']}"
            if 'kind' in selector:
                vardef = f"{vardef},kind={selector['kind']})"
            else:
                vardef = f'{vardef})'
        elif 'kind' in selector:
            vardef = f"{vardef}(kind={selector['kind']})"
        c = ' '
        if 'attrspec' in vars[a]:
            attr = [l for l in vars[a]['attrspec']
                    if l not in ['external']]
            if as_interface and 'intent(in)' in attr and 'intent(out)' in attr:
                # In Fortran, intent(in, out) are conflicting while
                # intent(in, out) can be specified only via
                # `!f2py intent(out) ..`.
                # So, for the Fortran interface, we'll drop
                # intent(out) to resolve the conflict.
                attr.remove('intent(out)')
            if attr:
                vardef = f"{vardef}, {','.join(attr)}"
                c = ','
        if 'dimension' in vars[a]:
            vardef = f"{vardef}{c}dimension({','.join(vars[a]['dimension'])})"
            c = ','
        if 'intent' in vars[a]:
            lst = true_intent_list(vars[a])
            if lst:
                vardef = f"{vardef}{c}intent({','.join(lst)})"
            c = ','
        if 'check' in vars[a]:
            vardef = f"{vardef}{c}check({','.join(vars[a]['check'])})"
            c = ','
        if 'depend' in vars[a]:
            vardef = f"{vardef}{c}depend({','.join(vars[a]['depend'])})"
            c = ','
        if '=' in vars[a]:
            v = vars[a]['=']
            if vars[a]['typespec'] in ['complex', 'double complex']:
                try:
                    v = eval(v)
                    v = f'({v.real},{v.imag})'
                except Exception:
                    pass
            vardef = f'{vardef} :: {a}={v}'
        else:
            vardef = f'{vardef} :: {a}'
        ret = f'{ret}{tab}{vardef}'
    return ret
######


# We expose post_processing_hooks as global variable so that
# user-libraries could register their own hooks to f2py.
post_processing_hooks = []


def crackfortran(files):
    global usermodules, post_processing_hooks

    outmess('Reading fortran codes...\n', 0)
    readfortrancode(files, crackline)
    outmess('Post-processing...\n', 0)
    usermodules = []
    postlist = postcrack(grouplist[0])
    outmess('Applying post-processing hooks...\n', 0)
    for hook in post_processing_hooks:
        outmess(f'  {hook.__name__}\n', 0)
        postlist = traverse(postlist, hook)
    outmess('Post-processing (stage 2)...\n', 0)
    postlist = postcrack2(postlist)
    return usermodules + postlist


def crack2fortran(block):
    global f2py_version

    pyf = crack2fortrangen(block) + '\n'
    header = """!    -*- f90 -*-
! Note: the context of this file is case sensitive.
"""
    footer = """
! This file was auto-generated with f2py (version:%s).
! See:
! https://web.archive.org/web/20140822061353/http://cens.ioc.ee/projects/f2py2e
""" % (f2py_version)
    return header + pyf + footer


def _is_visit_pair(obj):
    return (isinstance(obj, tuple)
            and len(obj) == 2
            and isinstance(obj[0], (int, str)))


def traverse(obj, visit, parents=[], result=None, *args, **kwargs):
    '''Traverse f2py data structure with the following visit function:

    def visit(item, parents, result, *args, **kwargs):
        """

        parents is a list of key-"f2py data structure" pairs from which
        items are taken from.

        result is a f2py data structure that is filled with the
        return value of the visit function.

        item is 2-tuple (index, value) if parents[-1][1] is a list
        item is 2-tuple (key, value) if parents[-1][1] is a dict

        The return value of visit must be None, or of the same kind as
        item, that is, if parents[-1] is a list, the return value must
        be 2-tuple (new_index, new_value), or if parents[-1] is a
        dict, the return value must be 2-tuple (new_key, new_value).

        If new_index or new_value is None, the return value of visit
        is ignored, that is, it will not be added to the result.

        If the return value is None, the content of obj will be
        traversed, otherwise not.
        """
    '''

    if _is_visit_pair(obj):
        if obj[0] == 'parent_block':
            # avoid infinite recursion
            return obj
        new_result = visit(obj, parents, result, *args, **kwargs)
        if new_result is not None:
            assert _is_visit_pair(new_result)
            return new_result
        parent = obj
        result_key, obj = obj
    else:
        parent = (None, obj)
        result_key = None

    if isinstance(obj, list):
        new_result = []
        for index, value in enumerate(obj):
            new_index, new_item = traverse((index, value), visit,
                                           parents + [parent], result,
                                           *args, **kwargs)
            if new_index is not None:
                new_result.append(new_item)
    elif isinstance(obj, dict):
        new_result = {}
        for key, value in obj.items():
            new_key, new_value = traverse((key, value), visit,
                                          parents + [parent], result,
                                          *args, **kwargs)
            if new_key is not None:
                new_result[new_key] = new_value
    else:
        new_result = obj

    if result_key is None:
        return new_result
    return result_key, new_result


def character_backward_compatibility_hook(item, parents, result,
                                          *args, **kwargs):
    """Previously, Fortran character was incorrectly treated as
    character*1. This hook fixes the usage of the corresponding
    variables in `check`, `dimension`, `=`, and `callstatement`
    expressions.

    The usage of `char*` in `callprotoargument` expression can be left
    unchanged because C `character` is C typedef of `char`, although,
    new implementations should use `character*` in the corresponding
    expressions.

    See https://github.com/numpy/numpy/pull/19388 for more information.

    """
    parent_key, parent_value = parents[-1]
    key, value = item

    def fix_usage(varname, value):
        value = re.sub(r'[*]\s*\b' + varname + r'\b', varname, value)
        value = re.sub(r'\b' + varname + r'\b\s*[\[]\s*0\s*[\]]',
                       varname, value)
        return value

    if parent_key in ['dimension', 'check']:
        assert parents[-3][0] == 'vars'
        vars_dict = parents[-3][1]
    elif key == '=':
        assert parents[-2][0] == 'vars'
        vars_dict = parents[-2][1]
    else:
        vars_dict = None

    new_value = None
    if vars_dict is not None:
        new_value = value
        for varname, vd in vars_dict.items():
            if ischaracter(vd):
                new_value = fix_usage(varname, new_value)
    elif key == 'callstatement':
        vars_dict = parents[-2][1]['vars']
        new_value = value
        for varname, vd in vars_dict.items():
            if ischaracter(vd):
                # replace all occurrences of `<varname>` with
                # `&<varname>` in argument passing
                new_value = re.sub(
                    r'(?<![&])\b' + varname + r'\b', '&' + varname, new_value)

    if new_value is not None:
        if new_value != value:
            # We report the replacements here so that downstream
            # software could update their source codes
            # accordingly. However, such updates are recommended only
            # when BC with numpy 1.21 or older is not required.
            outmess(f'character_bc_hook[{parent_key}.{key}]:'
                    f' replaced `{value}` -> `{new_value}`\n', 1)
        return (key, new_value)


post_processing_hooks.append(character_backward_compatibility_hook)


if __name__ == "__main__":
    files = []
    funcs = []
    f = 1
    f2 = 0
    f3 = 0
    showblocklist = 0
    for l in sys.argv[1:]:
        if l == '':
            pass
        elif l[0] == ':':
            f = 0
        elif l == '-quiet':
            quiet = 1
            verbose = 0
        elif l == '-verbose':
            verbose = 2
            quiet = 0
        elif l == '-fix':
            if strictf77:
                outmess(
                    'Use option -f90 before -fix if Fortran 90 code is in fix form.\n', 0)
            skipemptyends = 1
            sourcecodeform = 'fix'
        elif l == '-skipemptyends':
            skipemptyends = 1
        elif l == '--ignore-contains':
            ignorecontains = 1
        elif l == '-f77':
            strictf77 = 1
            sourcecodeform = 'fix'
        elif l == '-f90':
            strictf77 = 0
            sourcecodeform = 'free'
            skipemptyends = 1
        elif l == '-h':
            f2 = 1
        elif l == '-show':
            showblocklist = 1
        elif l == '-m':
            f3 = 1
        elif l[0] == '-':
            errmess(f'Unknown option {repr(l)}\n')
        elif f2:
            f2 = 0
            pyffilename = l
        elif f3:
            f3 = 0
            f77modulename = l
        elif f:
            try:
                open(l).close()
                files.append(l)
            except OSError as detail:
                errmess(f'OSError: {detail!s}\n')
        else:
            funcs.append(l)
    if not strictf77 and f77modulename and not skipemptyends:
        outmess("""\
  Warning: You have specified module name for non Fortran 77 code that
  should not need one (expect if you are scanning F90 code for non
  module blocks but then you should use flag -skipemptyends and also
  be sure that the files do not contain programs without program
  statement).
""", 0)

    postlist = crackfortran(files)
    if pyffilename:
        outmess(f'Writing fortran code to file {repr(pyffilename)}\n', 0)
        pyf = crack2fortran(postlist)
        with open(pyffilename, 'w') as f:
            f.write(pyf)
    if showblocklist:
        show(postlist)

# === NexusCore/openenv\Lib\site-packages\debugpy\_vendored\pydevd\pydevd.py ===
"""
Entry point module (keep at root):

This module starts the debugger.
"""

import sys  # @NoMove

if sys.version_info[:2] < (3, 6):
    raise RuntimeError(
        "The PyDev.Debugger requires Python 3.6 onwards to be run. If you need to use an older Python version, use an older version of the debugger."
    )
import os

# On the first import of a pydevd module, add pydevd itself to the PYTHONPATH
this_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, this_dir)

import _pydev_bundle

# Import this first as it'll check for shadowed modules and will make sure that we import
# things as needed for gevent.
from _pydevd_bundle import pydevd_constants
from typing import Optional, Tuple
from types import FrameType

import atexit
import dis
import io
from collections import defaultdict
from contextlib import contextmanager
from functools import partial
import itertools
import traceback
import weakref
import getpass as getpass_mod
import functools

import pydevd_file_utils
from _pydevd_bundle.pydevd_dont_trace_files import LIB_FILES_IN_DONT_TRACE_DIRS
from _pydev_bundle import pydev_imports, pydev_log
from _pydev_bundle._pydev_filesystem_encoding import getfilesystemencoding
from _pydev_bundle.pydev_is_thread_alive import is_thread_alive
from _pydev_bundle.pydev_override import overrides
from _pydev_bundle._pydev_saved_modules import threading, time, thread, ThreadingEvent
from _pydevd_bundle import pydevd_extension_utils, pydevd_frame_utils
from _pydevd_bundle.pydevd_filtering import FilesFiltering, glob_matches_path
from _pydevd_bundle import pydevd_io, pydevd_vm_type, pydevd_defaults
from _pydevd_bundle import pydevd_utils
from _pydevd_bundle import pydevd_runpy
from _pydev_bundle.pydev_console_utils import DebugConsoleStdIn
from _pydevd_bundle.pydevd_additional_thread_info import set_additional_thread_info, remove_additional_info
from _pydevd_bundle.pydevd_breakpoints import ExceptionBreakpoint, get_exception_breakpoint
from _pydevd_bundle.pydevd_comm_constants import (
    CMD_THREAD_SUSPEND,
    CMD_STEP_INTO,
    CMD_SET_BREAK,
    CMD_STEP_INTO_MY_CODE,
    CMD_STEP_OVER,
    CMD_SMART_STEP_INTO,
    CMD_RUN_TO_LINE,
    CMD_SET_NEXT_STATEMENT,
    CMD_STEP_RETURN,
    CMD_ADD_EXCEPTION_BREAK,
    CMD_STEP_RETURN_MY_CODE,
    CMD_STEP_OVER_MY_CODE,
    constant_to_str,
    CMD_STEP_INTO_COROUTINE,
)
from _pydevd_bundle.pydevd_constants import (
    get_thread_id,
    get_current_thread_id,
    DebugInfoHolder,
    PYTHON_SUSPEND,
    STATE_SUSPEND,
    STATE_RUN,
    get_frame,
    clear_cached_thread_id,
    INTERACTIVE_MODE_AVAILABLE,
    SHOW_DEBUG_INFO_ENV,
    NULL,
    NO_FTRACE,
    IS_IRONPYTHON,
    JSON_PROTOCOL,
    IS_CPYTHON,
    HTTP_JSON_PROTOCOL,
    USE_CUSTOM_SYS_CURRENT_FRAMES_MAP,
    call_only_once,
    ForkSafeLock,
    IGNORE_BASENAMES_STARTING_WITH,
    EXCEPTION_TYPE_UNHANDLED,
    SUPPORT_GEVENT,
    PYDEVD_IPYTHON_COMPATIBLE_DEBUGGING,
    PYDEVD_IPYTHON_CONTEXT,
    PYDEVD_USE_SYS_MONITORING,
)
from _pydevd_bundle.pydevd_defaults import PydevdCustomization  # Note: import alias used on pydev_monkey.
from _pydevd_bundle.pydevd_custom_frames import CustomFramesContainer, custom_frames_container_init
from _pydevd_bundle.pydevd_dont_trace_files import DONT_TRACE, PYDEV_FILE, LIB_FILE, DONT_TRACE_DIRS
from _pydevd_bundle.pydevd_extension_api import DebuggerEventHandler
from _pydevd_bundle.pydevd_frame_utils import add_exception_to_frame, remove_exception_from_frame, short_stack
from _pydevd_bundle.pydevd_net_command_factory_xml import NetCommandFactory
from _pydevd_bundle.pydevd_trace_dispatch import (
    trace_dispatch as _trace_dispatch,
    global_cache_skips,
    global_cache_frame_skips,
    fix_top_level_trace_and_get_trace_func,
    USING_CYTHON,
)
from _pydevd_bundle.pydevd_utils import save_main_module, is_current_thread_main_thread, import_attr_from_module
from _pydevd_frame_eval.pydevd_frame_eval_main import frame_eval_func, dummy_trace_dispatch, USING_FRAME_EVAL
import pydev_ipython  # @UnusedImport
from _pydevd_bundle.pydevd_source_mapping import SourceMapping
from _pydevd_bundle.pydevd_concurrency_analyser.pydevd_concurrency_logger import (
    ThreadingLogger,
    AsyncioLogger,
    send_concurrency_message,
    cur_time,
)
from _pydevd_bundle.pydevd_concurrency_analyser.pydevd_thread_wrappers import wrap_threads
from pydevd_file_utils import (
    get_abs_path_real_path_and_base_from_frame,
    get_abs_path_real_path_and_base_from_file,
    NORM_PATHS_AND_BASE_CONTAINER,
)
from pydevd_file_utils import get_fullname, get_package_dir
from os.path import abspath as os_path_abspath
import pydevd_tracing
from _pydevd_bundle.pydevd_comm import InternalThreadCommand, InternalThreadCommandForAnyThread, create_server_socket, FSNotifyThread
from _pydevd_bundle.pydevd_comm import (
    InternalConsoleExec,
    _queue,
    ReaderThread,
    GetGlobalDebugger,
    get_global_debugger,
    set_global_debugger,
    WriterThread,
    start_client,
    start_server,
    InternalGetBreakpointException,
    InternalSendCurrExceptionTrace,
    InternalSendCurrExceptionTraceProceeded,
)
from _pydevd_bundle.pydevd_daemon_thread import PyDBDaemonThread, mark_as_pydevd_daemon_thread
from _pydevd_bundle.pydevd_process_net_command_json import PyDevJsonCommandProcessor
from _pydevd_bundle.pydevd_process_net_command import process_net_command
from _pydevd_bundle.pydevd_net_command import NetCommand, NULL_NET_COMMAND

from _pydevd_bundle.pydevd_breakpoints import stop_on_unhandled_exception
from _pydevd_bundle.pydevd_collect_bytecode_info import collect_try_except_info, collect_return_info, collect_try_except_info_from_source
from _pydevd_bundle.pydevd_suspended_frames import SuspendedFramesManager
from socket import SHUT_RDWR
from _pydevd_bundle.pydevd_api import PyDevdAPI
from _pydevd_bundle.pydevd_timeout import TimeoutTracker
from _pydevd_bundle.pydevd_thread_lifecycle import suspend_all_threads, mark_thread_suspended

if PYDEVD_USE_SYS_MONITORING:
    from _pydevd_sys_monitoring import pydevd_sys_monitoring

pydevd_gevent_integration = None

if SUPPORT_GEVENT:
    try:
        from _pydevd_bundle import pydevd_gevent_integration
    except:
        pydev_log.exception(
            "pydevd: GEVENT_SUPPORT is set but gevent is not available in the environment.\n"
            "Please unset GEVENT_SUPPORT from the environment variables or install gevent."
        )
    else:
        pydevd_gevent_integration.log_gevent_debug_info()

if USE_CUSTOM_SYS_CURRENT_FRAMES_MAP:
    from _pydevd_bundle.pydevd_constants import constructed_tid_to_last_frame

__version_info__ = (3, 2, 3)
__version_info_str__ = []
for v in __version_info__:
    __version_info_str__.append(str(v))

__version__ = ".".join(__version_info_str__)

# IMPORTANT: pydevd_constants must be the 1st thing defined because it'll keep a reference to the original sys._getframe


def install_breakpointhook(pydevd_breakpointhook=None):
    if pydevd_breakpointhook is None:

        def pydevd_breakpointhook(*args, **kwargs):
            hookname = os.getenv("PYTHONBREAKPOINT")
            if (
                hookname is not None
                and len(hookname) > 0
                and hasattr(sys, "__breakpointhook__")
                and sys.__breakpointhook__ != pydevd_breakpointhook
            ):
                sys.__breakpointhook__(*args, **kwargs)
            else:
                settrace(*args, **kwargs)

    if sys.version_info[0:2] >= (3, 7):
        # There are some choices on how to provide the breakpoint hook. Namely, we can provide a
        # PYTHONBREAKPOINT which provides the import path for a method to be executed or we
        # can override sys.breakpointhook.
        # pydevd overrides sys.breakpointhook instead of providing an environment variable because
        # it's possible that the debugger starts the user program but is not available in the
        # PYTHONPATH (and would thus fail to be imported if PYTHONBREAKPOINT was set to pydevd.settrace).
        # Note that the implementation still takes PYTHONBREAKPOINT in account (so, if it was provided
        # by someone else, it'd still work).
        sys.breakpointhook = pydevd_breakpointhook
    else:
        if sys.version_info[0] >= 3:
            import builtins as __builtin__  # Py3 noqa
        else:
            import __builtin__  # noqa

        # In older versions, breakpoint() isn't really available, so, install the hook directly
        # in the builtins.
        __builtin__.breakpoint = pydevd_breakpointhook
        sys.__breakpointhook__ = pydevd_breakpointhook


# Install the breakpoint hook at import time.
install_breakpointhook()

from _pydevd_bundle.pydevd_plugin_utils import PluginManager

threadingEnumerate = threading.enumerate
threadingCurrentThread = threading.current_thread

try:
    "dummy".encode("utf-8")  # Added because otherwise Jython 2.2.1 wasn't finding the encoding (if it wasn't loaded in the main thread).
except:
    pass

_global_redirect_stdout_to_server = False
_global_redirect_stderr_to_server = False

file_system_encoding = getfilesystemencoding()

_CACHE_FILE_TYPE = {}

pydev_log.debug("Using GEVENT_SUPPORT: %s", pydevd_constants.SUPPORT_GEVENT)
pydev_log.debug("Using GEVENT_SHOW_PAUSED_GREENLETS: %s", pydevd_constants.GEVENT_SHOW_PAUSED_GREENLETS)
pydev_log.debug("pydevd __file__: %s", os.path.abspath(__file__))
pydev_log.debug("Using PYDEVD_IPYTHON_COMPATIBLE_DEBUGGING: %s", pydevd_constants.PYDEVD_IPYTHON_COMPATIBLE_DEBUGGING)
if pydevd_constants.PYDEVD_IPYTHON_COMPATIBLE_DEBUGGING:
    pydev_log.debug("PYDEVD_IPYTHON_CONTEXT: %s", pydevd_constants.PYDEVD_IPYTHON_CONTEXT)

TIMEOUT_SLOW = 0.2
TIMEOUT_FAST = 1.0 / 50


# =======================================================================================================================
# PyDBCommandThread
# =======================================================================================================================
class PyDBCommandThread(PyDBDaemonThread):

    def __init__(self, py_db):
        PyDBDaemonThread.__init__(self, py_db)
        self._py_db_command_thread_event = py_db._py_db_command_thread_event
        self.name = "pydevd.CommandThread"

    @overrides(PyDBDaemonThread._on_run)
    def _on_run(self):
        # Delay a bit this initialization to wait for the main program to start.
        self._py_db_command_thread_event.wait(TIMEOUT_SLOW)

        if self._kill_received:
            return

        try:
            while not self._kill_received:
                try:
                    self.py_db.process_internal_commands(("*",))
                except:
                    pydev_log.info("Finishing debug communication...(2)")
                self._py_db_command_thread_event.clear()
                self._py_db_command_thread_event.wait(TIMEOUT_SLOW)
        except:
            try:
                pydev_log.debug(sys.exc_info()[0])
            except:
                # In interpreter shutdown many things can go wrong (any module variables may
                # be None, streams can be closed, etc).
                pass

            # only got this error in interpreter shutdown
            # pydev_log.info('Finishing debug communication...(3)')

    @overrides(PyDBDaemonThread.do_kill_pydev_thread)
    def do_kill_pydev_thread(self):
        PyDBDaemonThread.do_kill_pydev_thread(self)
        # Set flag so that it can exit before the usual timeout.
        self._py_db_command_thread_event.set()


# =======================================================================================================================
# CheckAliveThread
# Non-daemon thread: guarantees that all data is written even if program is finished
# =======================================================================================================================
class CheckAliveThread(PyDBDaemonThread):

    def __init__(self, py_db):
        PyDBDaemonThread.__init__(self, py_db)
        self.name = "pydevd.CheckAliveThread"
        self.daemon = False
        self._wait_event = ThreadingEvent()

    @overrides(PyDBDaemonThread._on_run)
    def _on_run(self):
        py_db = self.py_db

        def can_exit():
            with py_db._main_lock:
                # Note: it's important to get the lock besides checking that it's empty (this
                # means that we're not in the middle of some command processing).
                writer = py_db.writer
                writer_empty = writer is not None and writer.empty()

            return not py_db.has_user_threads_alive() and writer_empty

        try:
            while not self._kill_received:
                self._wait_event.wait(TIMEOUT_SLOW)
                if can_exit():
                    break

                py_db.check_output_redirect()

            if can_exit():
                pydev_log.debug("No threads alive, finishing debug session")
                py_db.dispose_and_kill_all_pydevd_threads()
        except:
            pydev_log.exception()

    def join(self, timeout=None):
        # If someone tries to join this thread, mark it to be killed.
        # This is the case for CherryPy when auto-reload is turned on.
        self.do_kill_pydev_thread()
        PyDBDaemonThread.join(self, timeout=timeout)

    @overrides(PyDBDaemonThread.do_kill_pydev_thread)
    def do_kill_pydev_thread(self):
        PyDBDaemonThread.do_kill_pydev_thread(self)
        # Set flag so that it can exit before the usual timeout.
        self._wait_event.set()


class AbstractSingleNotificationBehavior(object):
    """
    The basic usage should be:

    # Increment the request time for the suspend.
    single_notification_behavior.increment_suspend_time()

    # Notify that this is a pause request (when a pause, not a breakpoint).
    single_notification_behavior.on_pause()

    # Mark threads to be suspended.
    set_suspend(...)

    # On do_wait_suspend, use notify_thread_suspended:
    def do_wait_suspend(...):
        with single_notification_behavior.notify_thread_suspended(thread_id, thread, reason):
            ...
    """

    __slots__ = [
        "_last_resume_notification_time",
        "_last_suspend_notification_time",
        "_lock",
        "_next_request_time",
        "_suspend_time_request",
        "_suspended_thread_id_to_thread",
        "_pause_requested",
        "_py_db",
    ]

    NOTIFY_OF_PAUSE_TIMEOUT = 0.5

    def __init__(self, py_db):
        self._py_db = weakref.ref(py_db)
        self._next_request_time = partial(next, itertools.count())
        self._last_suspend_notification_time = -1
        self._last_resume_notification_time = -1
        self._suspend_time_request = self._next_request_time()
        self._lock = thread.allocate_lock()
        self._suspended_thread_id_to_thread = {}
        self._pause_requested = False

    def send_suspend_notification(self, thread_id, thread, stop_reason):
        raise AssertionError("abstract: subclasses must override.")

    def send_resume_notification(self, thread_id):
        raise AssertionError("abstract: subclasses must override.")

    def increment_suspend_time(self):
        with self._lock:
            self._suspend_time_request = self._next_request_time()

    def on_pause(self):
        # Upon a pause, we should force sending new suspend notifications
        # if no notification is sent after some time and there's some thread already stopped.
        with self._lock:
            self._pause_requested = True
            global_suspend_time = self._suspend_time_request
        py_db = self._py_db()
        if py_db is not None:
            py_db.timeout_tracker.call_on_timeout(
                self.NOTIFY_OF_PAUSE_TIMEOUT, self._notify_after_timeout, kwargs={"global_suspend_time": global_suspend_time}
            )

    def _notify_after_timeout(self, global_suspend_time):
        with self._lock:
            if self._suspended_thread_id_to_thread:
                if global_suspend_time > self._last_suspend_notification_time:
                    self._last_suspend_notification_time = global_suspend_time
                    # Notify about any thread which is currently suspended.
                    pydev_log.info("Sending suspend notification after timeout.")
                    thread_id, thread = next(iter(self._suspended_thread_id_to_thread.items()))
                    self.send_suspend_notification(thread_id, thread, CMD_THREAD_SUSPEND)

    def on_thread_suspend(self, thread_id, thread, stop_reason):
        with self._lock:
            pause_requested = self._pause_requested
            if pause_requested:
                # When a suspend notification is sent, reset the pause flag.
                self._pause_requested = False

            self._suspended_thread_id_to_thread[thread_id] = thread

            # CMD_THREAD_SUSPEND should always be a side-effect of a break, so, only
            # issue for a CMD_THREAD_SUSPEND if a pause is pending.
            if stop_reason != CMD_THREAD_SUSPEND or pause_requested:
                if self._suspend_time_request > self._last_suspend_notification_time:
                    pydev_log.info("Sending suspend notification.")
                    self._last_suspend_notification_time = self._suspend_time_request
                    self.send_suspend_notification(thread_id, thread, stop_reason)
                else:
                    pydev_log.info(
                        "Suspend not sent (it was already sent). Last suspend % <= Last resume %s",
                        self._last_suspend_notification_time,
                        self._last_resume_notification_time,
                    )
            else:
                pydev_log.info(
                    "Suspend not sent because stop reason is thread suspend and pause was not requested.",
                )

    def on_thread_resume(self, thread_id, thread):
        # on resume (step, continue all):
        with self._lock:
            self._suspended_thread_id_to_thread.pop(thread_id)
            if self._last_resume_notification_time < self._last_suspend_notification_time:
                pydev_log.info("Sending resume notification.")
                self._last_resume_notification_time = self._last_suspend_notification_time
                self.send_resume_notification(thread_id)
            else:
                pydev_log.info(
                    "Resume not sent (it was already sent). Last resume %s >= Last suspend %s",
                    self._last_resume_notification_time,
                    self._last_suspend_notification_time,
                )

    @contextmanager
    def notify_thread_suspended(self, thread_id, thread, stop_reason):
        self.on_thread_suspend(thread_id, thread, stop_reason)
        try:
            yield  # At this point the thread must be actually suspended.
        finally:
            self.on_thread_resume(thread_id, thread)


class ThreadsSuspendedSingleNotification(AbstractSingleNotificationBehavior):
    __slots__ = AbstractSingleNotificationBehavior.__slots__ + ["multi_threads_single_notification", "_callbacks", "_callbacks_lock"]

    def __init__(self, py_db):
        AbstractSingleNotificationBehavior.__init__(self, py_db)
        # If True, pydevd will send a single notification when all threads are suspended/resumed.
        self.multi_threads_single_notification = False
        self._callbacks_lock = threading.Lock()
        self._callbacks = []

    def add_on_resumed_callback(self, callback):
        with self._callbacks_lock:
            self._callbacks.append(callback)

    @overrides(AbstractSingleNotificationBehavior.send_resume_notification)
    def send_resume_notification(self, thread_id):
        py_db = self._py_db()
        if py_db is not None:
            py_db.writer.add_command(py_db.cmd_factory.make_thread_resume_single_notification(thread_id))

            with self._callbacks_lock:
                callbacks = self._callbacks
                self._callbacks = []

            for callback in callbacks:
                callback()

    @overrides(AbstractSingleNotificationBehavior.send_suspend_notification)
    def send_suspend_notification(self, thread_id, thread, stop_reason):
        py_db = self._py_db()
        if py_db is not None:
            py_db.writer.add_command(py_db.cmd_factory.make_thread_suspend_single_notification(py_db, thread_id, thread, stop_reason))

    @overrides(AbstractSingleNotificationBehavior.notify_thread_suspended)
    @contextmanager
    def notify_thread_suspended(self, thread_id, thread, stop_reason):
        if self.multi_threads_single_notification:
            pydev_log.info("Thread suspend mode: single notification")
            with AbstractSingleNotificationBehavior.notify_thread_suspended(self, thread_id, thread, stop_reason):
                yield
        else:
            pydev_log.info("Thread suspend mode: NOT single notification")
            yield


class _Authentication(object):
    __slots__ = ["access_token", "client_access_token", "_authenticated", "_wrong_attempts"]

    def __init__(self):
        # A token to be send in the command line or through the settrace api -- when such token
        # is given, the first message sent to the IDE must pass the same token to authenticate.
        # Note that if a disconnect is sent, the same message must be resent to authenticate.
        self.access_token = None

        # This token is the one that the client requires to accept a connection from pydevd
        # (it's stored here and just passed back when required, it's not used internally
        # for anything else).
        self.client_access_token = None

        self._authenticated = None

        self._wrong_attempts = 0

    def is_authenticated(self):
        if self._authenticated is None:
            return self.access_token is None
        return self._authenticated

    def login(self, access_token):
        if self._wrong_attempts >= 10:  # A user can fail to authenticate at most 10 times.
            return

        self._authenticated = access_token == self.access_token
        if not self._authenticated:
            self._wrong_attempts += 1
        else:
            self._wrong_attempts = 0

    def logout(self):
        self._authenticated = None
        self._wrong_attempts = 0


class PyDB(object):
    """Main debugging class
    Lots of stuff going on here:

    PyDB starts two threads on startup that connect to remote debugger (RDB)
    The threads continuously read & write commands to RDB.
    PyDB communicates with these threads through command queues.
       Every RDB command is processed by calling process_net_command.
       Every PyDB net command is sent to the net by posting NetCommand to WriterThread queue

       Some commands need to be executed on the right thread (suspend/resume & friends)
       These are placed on the internal command queue.
    """

    # Direct child pids which should not be terminated when terminating processes.
    # Note: class instance because it should outlive PyDB instances.
    dont_terminate_child_pids = set()

    def __init__(self, set_as_global=True):
        if set_as_global:
            pydevd_tracing.replace_sys_set_trace_func()

        self.authentication = _Authentication()

        self.reader = None
        self.writer = None
        self._fsnotify_thread = None
        self.created_pydb_daemon_threads = {}
        self._waiting_for_connection_thread = None
        self._on_configuration_done_event = ThreadingEvent()
        self.check_alive_thread = None
        self.py_db_command_thread = None
        self.quitting = None
        self.cmd_factory = NetCommandFactory()
        self._cmd_queue = defaultdict(_queue.Queue)  # Key is thread id or '*', value is Queue
        self._thread_events = defaultdict(ThreadingEvent)  # Key is thread id or '*', value is Event
        self.suspended_frames_manager = SuspendedFramesManager()
        self._files_filtering = FilesFiltering()
        self.timeout_tracker = TimeoutTracker(self)

        # Note: when the source mapping is changed we also have to clear the file types cache
        # (because if a given file is a part of the project or not may depend on it being
        # defined in the source mapping).
        self.source_mapping = SourceMapping(on_source_mapping_changed=self._clear_caches)

        # Determines whether we should terminate child processes when asked to terminate.
        self.terminate_child_processes = True

        # Determines whether we should try to do a soft terminate (i.e.: interrupt the main
        # thread with a KeyboardInterrupt).
        self.terminate_keyboard_interrupt = False

        # Set to True after a keyboard interrupt is requested the first time.
        self.keyboard_interrupt_requested = False

        # These are the breakpoints received by the PyDevdAPI. They are meant to store
        # the breakpoints in the api -- its actual contents are managed by the api.
        self.api_received_breakpoints = {}

        # These are the breakpoints meant to be consumed during runtime.
        self.breakpoints = {}
        self.function_breakpoint_name_to_breakpoint = {}

        # Set communication protocol
        PyDevdAPI().set_protocol(self, 0, PydevdCustomization.DEFAULT_PROTOCOL)

        self.variable_presentation = PyDevdAPI.VariablePresentation()

        # mtime to be raised when something that will affect the
        # tracing in place (such as breakpoints change or filtering).
        self.mtime = 0

        self.file_to_id_to_line_breakpoint = {}
        self.file_to_id_to_plugin_breakpoint = {}

        # Note: breakpoints dict should not be mutated: a copy should be created
        # and later it should be assigned back (to prevent concurrency issues).
        self.break_on_uncaught_exceptions = {}
        self.break_on_caught_exceptions = {}
        self.break_on_user_uncaught_exceptions = {}

        self.ready_to_run = False
        self._main_lock = thread.allocate_lock()
        self._lock_running_thread_ids = thread.allocate_lock()
        self._lock_create_fs_notify = thread.allocate_lock()
        self._py_db_command_thread_event = ThreadingEvent()
        if set_as_global:
            CustomFramesContainer._py_db_command_thread_event = self._py_db_command_thread_event

        self.pydb_disposed = False
        self._wait_for_threads_to_finish_called = False
        self._wait_for_threads_to_finish_called_lock = thread.allocate_lock()
        self._wait_for_threads_to_finish_called_event = ThreadingEvent()

        self.terminate_requested = False
        self._disposed_lock = thread.allocate_lock()
        self.signature_factory = None
        self.SetTrace = pydevd_tracing.SetTrace
        self.skip_on_exceptions_thrown_in_same_context = False
        self.ignore_exceptions_thrown_in_lines_with_ignore_exception = True

        # Suspend debugger even if breakpoint condition raises an exception.
        # May be changed with CMD_PYDEVD_JSON_CONFIG.
        self.skip_suspend_on_breakpoint_exception = ()  # By default suspend on any Exception.
        self.skip_print_breakpoint_exception = ()  # By default print on any Exception.

        # By default user can step into properties getter/setter/deleter methods
        self.disable_property_trace = False
        self.disable_property_getter_trace = False
        self.disable_property_setter_trace = False
        self.disable_property_deleter_trace = False

        # this is a dict of thread ids pointing to thread ids. Whenever a command is passed to the java end that
        # acknowledges that a thread was created, the thread id should be passed here -- and if at some time we do not
        # find that thread alive anymore, we must remove it from this list and make the java side know that the thread
        # was killed.
        self._running_thread_ids = {}
        # Note: also access '_enable_thread_notifications' with '_lock_running_thread_ids'
        self._enable_thread_notifications = False

        self._set_breakpoints_with_id = False

        # This attribute holds the file-> lines which have an @IgnoreException.
        self.filename_to_lines_where_exceptions_are_ignored = {}

        # working with plugins (lazily initialized)
        self.plugin = None
        self.has_plugin_line_breaks = False
        self.has_plugin_exception_breaks = False
        self.thread_analyser = None
        self.asyncio_analyser = None

        # The GUI event loop that's going to run.
        # Possible values:
        # matplotlib - Whatever GUI backend matplotlib is using.
        # 'wx'/'qt'/'none'/... - GUI toolkits that have bulitin support. See pydevd_ipython/inputhook.py:24.
        # Other - A custom function that'll be imported and run.
        self._gui_event_loop = "matplotlib"
        self._installed_gui_support = False
        self.gui_in_use = False

        # GUI event loop support in debugger
        self.activate_gui_function = None

        # matplotlib support in debugger and debug console
        self.mpl_hooks_in_debug_console = False
        self.mpl_modules_for_patching = {}

        self._filename_to_not_in_scope = {}
        self.first_breakpoint_reached = False
        self._exclude_filters_enabled = self._files_filtering.use_exclude_filters()
        self._is_libraries_filter_enabled = self._files_filtering.use_libraries_filter()
        self.is_files_filter_enabled = self._exclude_filters_enabled or self._is_libraries_filter_enabled
        self.show_return_values = False
        self.remove_return_values_flag = False
        self.redirect_output = False
        # Note that besides the `redirect_output` flag, we also need to consider that someone
        # else is already redirecting (i.e.: debugpy).
        self.is_output_redirected = False

        # this flag disables frame evaluation even if it's available
        self.use_frame_eval = True

        # If True, pydevd will send a single notification when all threads are suspended/resumed.
        self._threads_suspended_single_notification = ThreadsSuspendedSingleNotification(self)

        # If True a step command will do a step in one thread and will also resume all other threads.
        self.stepping_resumes_all_threads = False

        self._local_thread_trace_func = threading.local()

        self._client_socket = None

        self._server_socket_ready_event = ThreadingEvent()
        self._server_socket_name = None

        # Bind many locals to the debugger because upon teardown those names may become None
        # in the namespace (and thus can't be relied upon unless the reference was previously
        # saved).
        if IS_IRONPYTHON:

            # A partial() cannot be used in IronPython for sys.settrace.
            def new_trace_dispatch(frame, event, arg):
                return _trace_dispatch(self, frame, event, arg)

            self.trace_dispatch = new_trace_dispatch
        else:
            self.trace_dispatch = partial(_trace_dispatch, self)
        self.fix_top_level_trace_and_get_trace_func = fix_top_level_trace_and_get_trace_func
        self.frame_eval_func = frame_eval_func
        self.dummy_trace_dispatch = dummy_trace_dispatch

        # Note: this is different from pydevd_constants.thread_get_ident because we want Jython
        # to be None here because it also doesn't have threading._active.
        try:
            self.threading_get_ident = threading.get_ident  # Python 3
            self.threading_active = threading._active
        except:
            try:
                self.threading_get_ident = threading._get_ident  # Python 2 noqa
                self.threading_active = threading._active
            except:
                self.threading_get_ident = None  # Jython
                self.threading_active = None
        self.threading_current_thread = threading.currentThread
        self.set_additional_thread_info = set_additional_thread_info
        self.stop_on_unhandled_exception = stop_on_unhandled_exception
        self.collect_return_info = collect_return_info
        self.get_exception_breakpoint = get_exception_breakpoint
        self._dont_trace_get_file_type = DONT_TRACE.get
        self._dont_trace_dirs_get_file_type = DONT_TRACE_DIRS.get
        self.PYDEV_FILE = PYDEV_FILE
        self.LIB_FILE = LIB_FILE

        self._in_project_scope_cache = {}
        self._exclude_by_filter_cache = {}
        self._apply_filter_cache = {}
        self._ignore_system_exit_codes = set()

        # DAP related
        self._dap_messages_listeners = []

        if set_as_global:
            # Set as the global instance only after it's initialized.
            set_global_debugger(self)

        pydevd_defaults.on_pydb_init(self)
        # Stop the tracing as the last thing before the actual shutdown for a clean exit.
        atexit.register(stoptrace)

    def collect_try_except_info(self, code_obj):
        filename = code_obj.co_filename
        try:
            if os.path.exists(filename):
                pydev_log.debug("Collecting try..except info from source for %s", filename)
                try_except_infos = collect_try_except_info_from_source(filename)
                if try_except_infos:
                    # Filter for the current function
                    max_line = -1
                    min_line = sys.maxsize
                    for _, line in dis.findlinestarts(code_obj):
                        if line is not None:
                            if line > max_line:
                                max_line = line
                            if line < min_line:
                                min_line = line

                    try_except_infos = [x for x in try_except_infos if min_line <= x.try_line <= max_line]
                return try_except_infos

        except:
            pydev_log.exception("Error collecting try..except info from source (%s)", filename)

        pydev_log.debug("Collecting try..except info from bytecode for %s", filename)
        return collect_try_except_info(code_obj)

    def setup_auto_reload_watcher(self, enable_auto_reload, watch_dirs, poll_target_time, exclude_patterns, include_patterns):
        try:
            with self._lock_create_fs_notify:
                # When setting up, dispose of the previous one (if any).
                if self._fsnotify_thread is not None:
                    self._fsnotify_thread.do_kill_pydev_thread()
                    self._fsnotify_thread = None

                if not enable_auto_reload:
                    return

                exclude_patterns = tuple(exclude_patterns)
                include_patterns = tuple(include_patterns)

                def accept_directory(absolute_filename, cache={}):
                    try:
                        return cache[absolute_filename]
                    except:
                        if absolute_filename and absolute_filename[-1] not in ("/", "\\"):
                            # I.e.: for directories we always end with '/' or '\\' so that
                            # we match exclusions such as "**/node_modules/**"
                            absolute_filename += os.path.sep

                        # First include what we want
                        for include_pattern in include_patterns:
                            if glob_matches_path(absolute_filename, include_pattern):
                                cache[absolute_filename] = True
                                return True

                        # Then exclude what we don't want
                        for exclude_pattern in exclude_patterns:
                            if glob_matches_path(absolute_filename, exclude_pattern):
                                cache[absolute_filename] = False
                                return False

                        # By default track all directories not excluded.
                        cache[absolute_filename] = True
                        return True

                def accept_file(absolute_filename, cache={}):
                    try:
                        return cache[absolute_filename]
                    except:
                        # First include what we want
                        for include_pattern in include_patterns:
                            if glob_matches_path(absolute_filename, include_pattern):
                                cache[absolute_filename] = True
                                return True

                        # Then exclude what we don't want
                        for exclude_pattern in exclude_patterns:
                            if glob_matches_path(absolute_filename, exclude_pattern):
                                cache[absolute_filename] = False
                                return False

                        # By default don't track files not included.
                        cache[absolute_filename] = False
                        return False

                self._fsnotify_thread = FSNotifyThread(self, PyDevdAPI(), watch_dirs)
                watcher = self._fsnotify_thread.watcher
                watcher.accept_directory = accept_directory
                watcher.accept_file = accept_file

                watcher.target_time_for_single_scan = poll_target_time
                watcher.target_time_for_notification = poll_target_time
                self._fsnotify_thread.start()
        except:
            pydev_log.exception("Error setting up auto-reload.")

    def get_arg_ppid(self):
        try:
            setup = SetupHolder.setup
            if setup:
                return int(setup.get("ppid", 0))
        except:
            pydev_log.exception("Error getting ppid.")

        return 0

    def wait_for_ready_to_run(self):
        while not self.ready_to_run:
            # busy wait until we receive run command
            self.process_internal_commands()
            self._py_db_command_thread_event.clear()
            self._py_db_command_thread_event.wait(TIMEOUT_FAST)

    def on_initialize(self):
        """
        Note: only called when using the DAP (Debug Adapter Protocol).
        """
        self._on_configuration_done_event.clear()

    def on_configuration_done(self):
        """
        Note: only called when using the DAP (Debug Adapter Protocol).
        """
        self._on_configuration_done_event.set()
        self._py_db_command_thread_event.set()

    def is_attached(self):
        return self._on_configuration_done_event.is_set()

    def on_disconnect(self):
        """
        Note: only called when using the DAP (Debug Adapter Protocol).
        """
        self.authentication.logout()
        self._on_configuration_done_event.clear()

    def set_ignore_system_exit_codes(self, ignore_system_exit_codes):
        assert isinstance(ignore_system_exit_codes, (list, tuple, set))
        self._ignore_system_exit_codes = set(ignore_system_exit_codes)

    def ignore_system_exit_code(self, system_exit_exc):
        if hasattr(system_exit_exc, "code"):
            return system_exit_exc.code in self._ignore_system_exit_codes
        else:
            return system_exit_exc in self._ignore_system_exit_codes

    def block_until_configuration_done(self, cancel=None):
        if cancel is None:
            cancel = NULL

        while not cancel.is_set():
            if self._on_configuration_done_event.is_set():
                cancel.set()  # Set cancel to prevent reuse
                return

            self.process_internal_commands()
            self._py_db_command_thread_event.clear()
            self._py_db_command_thread_event.wait(TIMEOUT_FAST)

    def add_fake_frame(self, thread_id, frame_id, frame):
        self.suspended_frames_manager.add_fake_frame(thread_id, frame_id, frame)

    def handle_breakpoint_condition(self, info, pybreakpoint, new_frame):
        condition = pybreakpoint.condition
        try:
            if pybreakpoint.handle_hit_condition(new_frame):
                return True

            if not condition:
                return False

            return eval(condition, new_frame.f_globals, new_frame.f_locals)
        except Exception as e:
            if not isinstance(e, self.skip_print_breakpoint_exception):
                stack_trace = io.StringIO()
                etype, value, tb = sys.exc_info()
                traceback.print_exception(etype, value, tb.tb_next, file=stack_trace)

                msg = "Error while evaluating expression in conditional breakpoint: %s\n%s" % (condition, stack_trace.getvalue())
                api = PyDevdAPI()
                api.send_error_message(self, msg)

            if not isinstance(e, self.skip_suspend_on_breakpoint_exception):
                try:
                    # add exception_type and stacktrace into thread additional info
                    etype, value, tb = sys.exc_info()
                    error = "".join(traceback.format_exception_only(etype, value))
                    stack = traceback.extract_stack(f=tb.tb_frame.f_back)

                    # On self.set_suspend(thread, CMD_SET_BREAK) this info will be
                    # sent to the client.
                    info.conditional_breakpoint_exception = ("Condition:\n" + condition + "\n\nError:\n" + error, stack)
                except:
                    pydev_log.exception()
                return True

            return False

        finally:
            etype, value, tb = None, None, None

    def handle_breakpoint_expression(self, pybreakpoint, info, new_frame):
        try:
            try:
                val = eval(pybreakpoint.expression, new_frame.f_globals, new_frame.f_locals)
            except:
                val = sys.exc_info()[1]
        finally:
            if val is not None:
                info.pydev_message = str(val)

    def _internal_get_file_type(self, abs_real_path_and_basename):
        basename = abs_real_path_and_basename[-1]
        if basename.startswith(IGNORE_BASENAMES_STARTING_WITH) or abs_real_path_and_basename[0].startswith(IGNORE_BASENAMES_STARTING_WITH):
            # Note: these are the files that are completely ignored (they aren't shown to the user
            # as user nor library code as it's usually just noise in the frame stack).
            return self.PYDEV_FILE
        file_type = self._dont_trace_get_file_type(basename)
        if file_type is not None:
            return file_type

        if basename.startswith("__init__.py") or basename in LIB_FILES_IN_DONT_TRACE_DIRS:
            # i.e.: ignore the __init__ files inside pydevd (the other
            # files are ignored just by their name).
            abs_path = abs_real_path_and_basename[0]
            i = max(abs_path.rfind("/"), abs_path.rfind("\\"))
            if i:
                abs_path = abs_path[0:i]
                i = max(abs_path.rfind("/"), abs_path.rfind("\\"))
                if i:
                    dirname = abs_path[i + 1:]
                    # At this point, something as:
                    # "my_path\_pydev_runfiles\__init__.py"
                    # is now  "_pydev_runfiles".
                    return self._dont_trace_dirs_get_file_type(dirname)
        return None

    def dont_trace_external_files(self, abs_path):
        """
        :param abs_path:
            The result from get_abs_path_real_path_and_base_from_file or
            get_abs_path_real_path_and_base_from_frame.

        :return
            True :
                If files should NOT be traced.

            False:
                If files should be traced.
        """
        # By default all external files are traced. Note: this function is expected to
        # be changed for another function in PyDevdAPI.set_dont_trace_start_end_patterns.
        return False

    def get_file_type(self, frame, abs_real_path_and_basename=None, _cache_file_type=_CACHE_FILE_TYPE):
        """
        :param abs_real_path_and_basename:
            The result from get_abs_path_real_path_and_base_from_file or
            get_abs_path_real_path_and_base_from_frame.

        :return
            _pydevd_bundle.pydevd_dont_trace_files.PYDEV_FILE:
                If it's a file internal to the debugger which shouldn't be
                traced nor shown to the user.

            _pydevd_bundle.pydevd_dont_trace_files.LIB_FILE:
                If it's a file in a library which shouldn't be traced.

            None:
                If it's a regular user file which should be traced.
        """
        if abs_real_path_and_basename is None:
            try:
                # Make fast path faster!
                abs_real_path_and_basename = NORM_PATHS_AND_BASE_CONTAINER[frame.f_code.co_filename]
            except:
                abs_real_path_and_basename = get_abs_path_real_path_and_base_from_frame(frame)

        # Note 1: we have to take into account that we may have files as '<string>', and that in
        # this case the cache key can't rely only on the filename. With the current cache, there's
        # still a potential miss if 2 functions which have exactly the same content are compiled
        # with '<string>', but in practice as we only separate the one from python -c from the rest
        # this shouldn't be a problem in practice.

        # Note 2: firstlineno added to make misses faster in the first comparison.

        # Note 3: this cache key is repeated in pydevd_frame_evaluator.pyx:get_func_code_info (for
        # speedups).
        cache_key = (frame.f_code.co_firstlineno, abs_real_path_and_basename[0], frame.f_code)
        try:
            return _cache_file_type[cache_key]
        except:
            if abs_real_path_and_basename[0] == "<string>":
                f = frame.f_back
                while f is not None:
                    if self.get_file_type(f) != self.PYDEV_FILE and pydevd_file_utils.basename(f.f_code.co_filename) not in (
                        "runpy.py",
                        "<string>",
                    ):
                        # We found some back frame that's not internal, which means we must consider
                        # this a library file.
                        # This is done because we only want to trace files as <string> if they don't
                        # have any back frame (which is the case for python -c ...), for all other
                        # cases we don't want to trace them because we can't show the source to the
                        # user (at least for now...).

                        # Note that we return as a LIB_FILE and not PYDEV_FILE because we still want
                        # to show it in the stack.
                        _cache_file_type[cache_key] = LIB_FILE
                        return LIB_FILE

                    f = f.f_back
                else:
                    # This is a top-level file (used in python -c), so, trace it as usual... we
                    # still won't be able to show the sources, but some tests require this to work.
                    _cache_file_type[cache_key] = None
                    return None

            file_type = self._internal_get_file_type(abs_real_path_and_basename)
            if file_type is None:
                if self.dont_trace_external_files(abs_real_path_and_basename[0]):
                    file_type = PYDEV_FILE

            _cache_file_type[cache_key] = file_type
            return file_type

    def is_cache_file_type_empty(self):
        return not _CACHE_FILE_TYPE

    def get_cache_file_type(self, _cache=_CACHE_FILE_TYPE):  # i.e.: Make it local.
        return _cache

    def get_thread_local_trace_func(self):
        try:
            thread_trace_func = self._local_thread_trace_func.thread_trace_func
        except AttributeError:
            thread_trace_func = self.trace_dispatch
        return thread_trace_func

    def enable_tracing(self, thread_trace_func=None, apply_to_all_threads=False):
        """
        Enables tracing.

        If in regular mode (tracing), will set the tracing function to the tracing
        function for this thread -- by default it's `PyDB.trace_dispatch`, but after
        `PyDB.enable_tracing` is called with a `thread_trace_func`, the given function will
        be the default for the given thread.

        :param bool apply_to_all_threads:
            If True we'll set the tracing function in all threads, not only in the current thread.
            If False only the tracing for the current function should be changed.
            In general apply_to_all_threads should only be true if this is the first time
            this function is called on a multi-threaded program (either programmatically or attach
            to pid).
        """
        if PYDEVD_USE_SYS_MONITORING:
            pydevd_sys_monitoring.start_monitoring(all_threads=apply_to_all_threads)
            return

        if pydevd_gevent_integration is not None:
            pydevd_gevent_integration.enable_gevent_integration()

        if self.frame_eval_func is not None:
            self.frame_eval_func()
            pydevd_tracing.SetTrace(self.dummy_trace_dispatch)

            if IS_CPYTHON and apply_to_all_threads:
                pydevd_tracing.set_trace_to_threads(self.dummy_trace_dispatch)
            return

        if apply_to_all_threads:
            # If applying to all threads, don't use the local thread trace function.
            assert thread_trace_func is not None
        else:
            if thread_trace_func is None:
                thread_trace_func = self.get_thread_local_trace_func()
            else:
                self._local_thread_trace_func.thread_trace_func = thread_trace_func

        pydevd_tracing.SetTrace(thread_trace_func)
        if IS_CPYTHON and apply_to_all_threads:
            pydevd_tracing.set_trace_to_threads(thread_trace_func)

    def disable_tracing(self):
        if PYDEVD_USE_SYS_MONITORING:
            pydevd_sys_monitoring.stop_monitoring(all_threads=False)
        else:
            pydevd_tracing.SetTrace(None)

    def on_breakpoints_changed(self, removed=False):
        """
        When breakpoints change, we have to re-evaluate all the assumptions we've made so far.
        """
        if not self.ready_to_run:
            # No need to do anything if we're still not running.
            return

        self.mtime += 1
        if not removed:
            # When removing breakpoints we can leave tracing as was, but if a breakpoint was added
            # we have to reset the tracing for the existing functions to be re-evaluated.

            # The caches also need to be cleared because of django breakpoints use case,
            # where adding a file needs to start tracking a context which was previously
            # untracked.
            self._clear_caches()
            self.set_tracing_for_untraced_contexts(breakpoints_changed=True)

    def set_tracing_for_untraced_contexts(self, breakpoints_changed=False):
        # Enable the tracing for existing threads (because there may be frames being executed that
        # are currently untraced).
        if PYDEVD_USE_SYS_MONITORING and breakpoints_changed:
            pydevd_sys_monitoring.update_monitor_events()

        if IS_CPYTHON:
            # Note: use sys._current_frames instead of threading.enumerate() because this way
            # we also see C/C++ threads, not only the ones visible to the threading module.
            tid_to_frame = sys._current_frames()

            ignore_thread_ids = set(
                t.ident
                for t in threadingEnumerate()
                if getattr(t, "is_pydev_daemon_thread", False) or getattr(t, "pydev_do_not_trace", False)
            )

            for thread_ident, frame in tid_to_frame.items():
                if thread_ident not in ignore_thread_ids:
                    self.set_trace_for_frame_and_parents(thread_ident, frame)

        else:
            try:
                threads = threadingEnumerate()
                for t in threads:
                    if getattr(t, "is_pydev_daemon_thread", False) or getattr(t, "pydev_do_not_trace", False):
                        continue

                    additional_info = set_additional_thread_info(t)
                    frame = additional_info.get_topmost_frame(t)
                    try:
                        if frame is not None:
                            self.set_trace_for_frame_and_parents(t.ident, frame)
                    finally:
                        frame = None
            finally:
                frame = None
                t = None
                threads = None
                additional_info = None

        if PYDEVD_USE_SYS_MONITORING:
            pydevd_sys_monitoring.restart_events()

    @property
    def multi_threads_single_notification(self):
        return self._threads_suspended_single_notification.multi_threads_single_notification

    @multi_threads_single_notification.setter
    def multi_threads_single_notification(self, notify):
        self._threads_suspended_single_notification.multi_threads_single_notification = notify

    @property
    def threads_suspended_single_notification(self):
        return self._threads_suspended_single_notification

    def get_plugin_lazy_init(self):
        if self.plugin is None:
            self.plugin = PluginManager(self)
        return self.plugin

    def in_project_scope(self, frame, absolute_filename=None):
        """
        Note: in general this method should not be used (apply_files_filter should be used
        in most cases as it also handles the project scope check).

        :param frame:
            The frame we want to check.

        :param absolute_filename:
            Must be the result from get_abs_path_real_path_and_base_from_frame(frame)[0] (can
            be used to speed this function a bit if it's already available to the caller, but
            in general it's not needed).
        """
        try:
            if absolute_filename is None:
                try:
                    # Make fast path faster!
                    abs_real_path_and_basename = NORM_PATHS_AND_BASE_CONTAINER[frame.f_code.co_filename]
                except:
                    abs_real_path_and_basename = get_abs_path_real_path_and_base_from_frame(frame)

                absolute_filename = abs_real_path_and_basename[0]

            cache_key = (frame.f_code.co_firstlineno, absolute_filename, frame.f_code)

            return self._in_project_scope_cache[cache_key]
        except KeyError:
            cache = self._in_project_scope_cache
            try:
                abs_real_path_and_basename  # If we've gotten it previously, use it again.
            except NameError:
                abs_real_path_and_basename = get_abs_path_real_path_and_base_from_frame(frame)

            # pydevd files are never considered to be in the project scope.
            file_type = self.get_file_type(frame, abs_real_path_and_basename)
            if file_type == self.PYDEV_FILE:
                cache[cache_key] = False

            elif absolute_filename == "<string>":
                # Special handling for '<string>'
                if file_type == self.LIB_FILE:
                    cache[cache_key] = False
                else:
                    cache[cache_key] = True

            elif self.source_mapping.has_mapping_entry(absolute_filename):
                cache[cache_key] = True

            else:
                cache[cache_key] = self._files_filtering.in_project_roots(absolute_filename)

            return cache[cache_key]

    def in_project_roots_filename_uncached(self, absolute_filename):
        return self._files_filtering.in_project_roots(absolute_filename)

    def _clear_caches(self):
        # Skip caches
        global_cache_skips.clear()
        global_cache_frame_skips.clear()

        # Filter caches
        self._in_project_scope_cache.clear()
        self._exclude_by_filter_cache.clear()
        self._apply_filter_cache.clear()
        self._exclude_filters_enabled = self._files_filtering.use_exclude_filters()
        self._is_libraries_filter_enabled = self._files_filtering.use_libraries_filter()
        self.is_files_filter_enabled = self._exclude_filters_enabled or self._is_libraries_filter_enabled

        self.mtime += 1
        if PYDEVD_USE_SYS_MONITORING:
            pydevd_sys_monitoring.update_monitor_events()
            pydevd_sys_monitoring.restart_events()

    def clear_dont_trace_start_end_patterns_caches(self):
        # When start/end patterns are changed we must clear all caches which would be
        # affected by a change in get_file_type() and reset the tracing function
        # as places which were traced may no longer need to be traced and vice-versa.
        self.on_breakpoints_changed()
        _CACHE_FILE_TYPE.clear()
        self._clear_caches()

    def _exclude_by_filter(self, frame, absolute_filename):
        """
        :return: True if it should be excluded, False if it should be included and None
            if no rule matched the given file.

        :note: it'll be normalized as needed inside of this method.
        """
        cache_key = (absolute_filename, frame.f_code.co_name, frame.f_code.co_firstlineno)
        try:
            return self._exclude_by_filter_cache[cache_key]
        except KeyError:
            cache = self._exclude_by_filter_cache

            # pydevd files are always filtered out
            if self.get_file_type(frame) == self.PYDEV_FILE:
                cache[cache_key] = True
            else:
                module_name = None
                if self._files_filtering.require_module:
                    module_name = frame.f_globals.get("__name__", "")
                cache[cache_key] = self._files_filtering.exclude_by_filter(absolute_filename, module_name)

            return cache[cache_key]

    def apply_files_filter(self, frame, original_filename, force_check_project_scope):
        """
        Should only be called if `self.is_files_filter_enabled == True` or `force_check_project_scope == True`.

        Note that it covers both the filter by specific paths includes/excludes as well
        as the check which filters out libraries if not in the project scope.

        :param original_filename:
            Note can either be the original filename or the absolute version of that filename.

        :param force_check_project_scope:
            Check that the file is in the project scope even if the global setting
            is off.

        :return bool:
            True if it should be excluded when stepping and False if it should be
            included.
        """
        cache_key = (frame.f_code.co_firstlineno, original_filename, force_check_project_scope, frame.f_code)
        try:
            return self._apply_filter_cache[cache_key]
        except KeyError:
            DEBUG = True  # 'defaulttags' in original_filename
            if self.plugin is not None and (self.has_plugin_line_breaks or self.has_plugin_exception_breaks):
                # If it's explicitly needed by some plugin, we can't skip it.
                if not self.plugin.can_skip(self, frame):
                    if DEBUG:
                        pydev_log.debug_once("File traced (included by plugins): %s", original_filename)
                    self._apply_filter_cache[cache_key] = False
                    return False

            if self._exclude_filters_enabled:
                absolute_filename = pydevd_file_utils.absolute_path(original_filename)
                exclude_by_filter = self._exclude_by_filter(frame, absolute_filename)
                if exclude_by_filter is not None:
                    if exclude_by_filter:
                        # ignore files matching stepping filters
                        if DEBUG:
                            pydev_log.debug_once("File not traced (excluded by filters): %s", original_filename)

                        self._apply_filter_cache[cache_key] = True
                        return True
                    else:
                        if DEBUG:
                            pydev_log.debug_once("File traced (explicitly included by filters): %s", original_filename)

                        self._apply_filter_cache[cache_key] = False
                        return False

            if (self._is_libraries_filter_enabled or force_check_project_scope) and not self.in_project_scope(frame):
                # ignore library files while stepping
                self._apply_filter_cache[cache_key] = True
                if force_check_project_scope:
                    if DEBUG:
                        pydev_log.debug_once("File not traced (not in project): %s", original_filename)
                else:
                    if DEBUG:
                        pydev_log.debug_once("File not traced (not in project - force_check_project_scope): %s", original_filename)

                return True

            if force_check_project_scope:
                if DEBUG:
                    pydev_log.debug_once("File traced: %s (force_check_project_scope)", original_filename)
            else:
                if DEBUG:
                    pydev_log.debug_once("File traced: %s", original_filename)
            self._apply_filter_cache[cache_key] = False
            return False

    def exclude_exception_by_filter(self, exception_breakpoint, trace):
        if not exception_breakpoint.ignore_libraries and not self._exclude_filters_enabled:
            return False

        if trace is None:
            return True

        ignore_libraries = exception_breakpoint.ignore_libraries
        exclude_filters_enabled = self._exclude_filters_enabled

        if (ignore_libraries and not self.in_project_scope(trace.tb_frame)) or (
            exclude_filters_enabled
            and self._exclude_by_filter(trace.tb_frame, pydevd_file_utils.absolute_path(trace.tb_frame.f_code.co_filename))
        ):
            return True

        return False

    def set_project_roots(self, project_roots):
        self._files_filtering.set_project_roots(project_roots)
        self._clear_caches()

    def set_exclude_filters(self, exclude_filters):
        self._files_filtering.set_exclude_filters(exclude_filters)
        self._clear_caches()

    def set_use_libraries_filter(self, use_libraries_filter):
        self._files_filtering.set_use_libraries_filter(use_libraries_filter)
        self._clear_caches()

    def get_use_libraries_filter(self):
        return self._files_filtering.use_libraries_filter()

    def get_require_module_for_filters(self):
        return self._files_filtering.require_module

    def has_user_threads_alive(self):
        for t in pydevd_utils.get_non_pydevd_threads():
            if isinstance(t, PyDBDaemonThread):
                pydev_log.error_once("Error in debugger: Found PyDBDaemonThread not marked with is_pydev_daemon_thread=True.\n")

            if is_thread_alive(t):
                if not t.daemon or hasattr(t, "__pydevd_main_thread"):
                    return True

        return False

    def initialize_network(self, sock, terminate_on_socket_close=True):
        assert sock is not None
        try:
            sock.settimeout(None)  # infinite, no timeouts from now on - jython does not have it
        except:
            pass
        curr_reader = getattr(self, "reader", None)
        curr_writer = getattr(self, "writer", None)
        if curr_reader:
            curr_reader.do_kill_pydev_thread()
        if curr_writer:
            curr_writer.do_kill_pydev_thread()

        self.writer = WriterThread(sock, self, terminate_on_socket_close=terminate_on_socket_close)
        self.reader = ReaderThread(
            sock,
            self,
            PyDevJsonCommandProcessor=PyDevJsonCommandProcessor,
            process_net_command=process_net_command,
            terminate_on_socket_close=terminate_on_socket_close,
        )
        self.writer.start()
        self.reader.start()

        time.sleep(0.1)  # give threads time to start

    def connect(self, host, port):
        if host:
            s = start_client(host, port)
            self._client_socket = s
        else:
            s = start_server(port)

        self.initialize_network(s)

    def create_wait_for_connection_thread(self):
        if self._waiting_for_connection_thread is not None:
            raise AssertionError("There is already another thread waiting for a connection.")

        self._server_socket_ready_event.clear()
        self._waiting_for_connection_thread = self._WaitForConnectionThread(self)
        self._waiting_for_connection_thread.start()

    def set_server_socket_ready(self):
        self._server_socket_ready_event.set()

    def wait_for_server_socket_ready(self):
        self._server_socket_ready_event.wait()

    @property
    def dap_messages_listeners(self):
        return self._dap_messages_listeners

    def add_dap_messages_listener(self, listener):
        self._dap_messages_listeners.append(listener)

    class _WaitForConnectionThread(PyDBDaemonThread):

        def __init__(self, py_db):
            PyDBDaemonThread.__init__(self, py_db)
            self._server_socket = None

        def run(self):
            host = SetupHolder.setup["client"]
            port = SetupHolder.setup["port"]

            self._server_socket = create_server_socket(host=host, port=port)
            self.py_db._server_socket_name = self._server_socket.getsockname()
            self.py_db.set_server_socket_ready()

            while not self._kill_received:
                try:
                    s = self._server_socket
                    if s is None:
                        return

                    s.listen(1)
                    new_socket, _addr = s.accept()
                    if self._kill_received:
                        pydev_log.info("Connection (from wait_for_attach) accepted but ignored as kill was already received.")
                        return

                    pydev_log.info("Connection (from wait_for_attach) accepted.")
                    reader = getattr(self.py_db, "reader", None)
                    if reader is not None:
                        # This is needed if a new connection is done without the client properly
                        # sending a disconnect for the previous connection.
                        api = PyDevdAPI()
                        api.request_disconnect(self.py_db, resume_threads=False)

                    self.py_db.initialize_network(new_socket, terminate_on_socket_close=False)

                except:
                    if DebugInfoHolder.DEBUG_TRACE_LEVEL > 0:
                        pydev_log.exception()
                        pydev_log.debug("Exiting _WaitForConnectionThread: %s\n", port)

        def do_kill_pydev_thread(self):
            PyDBDaemonThread.do_kill_pydev_thread(self)
            s = self._server_socket
            if s is not None:
                try:
                    s.close()
                except:
                    pass
                self._server_socket = None

    def get_internal_queue_and_event(self, thread_id) -> Tuple[_queue.Queue, ThreadingEvent]:
        """returns internal command queue for a given thread.
        if new queue is created, notify the RDB about it"""
        if thread_id.startswith("__frame__"):
            thread_id = thread_id[thread_id.rfind("|") + 1:]
        return self._cmd_queue[thread_id], self._thread_events[thread_id]

    def post_method_as_internal_command(self, thread_id, method, *args, **kwargs):
        if thread_id == "*":
            internal_cmd = InternalThreadCommandForAnyThread(thread_id, method, *args, **kwargs)
        else:
            internal_cmd = InternalThreadCommand(thread_id, method, *args, **kwargs)
        self.post_internal_command(internal_cmd, thread_id)

    def post_internal_command(self, int_cmd, thread_id):
        """if thread_id is *, post to the '*' queue"""
        queue, event = self.get_internal_queue_and_event(thread_id)
        queue.put(int_cmd)
        if thread_id == "*":
            self._py_db_command_thread_event.set()
        else:
            event.set()

    def enable_output_redirection(self, redirect_stdout, redirect_stderr):
        global _global_redirect_stdout_to_server
        global _global_redirect_stderr_to_server

        _global_redirect_stdout_to_server = redirect_stdout
        _global_redirect_stderr_to_server = redirect_stderr
        self.redirect_output = redirect_stdout or redirect_stderr
        if _global_redirect_stdout_to_server:
            _init_stdout_redirect()
        if _global_redirect_stderr_to_server:
            _init_stderr_redirect()

    def check_output_redirect(self):
        global _global_redirect_stdout_to_server
        global _global_redirect_stderr_to_server

        if _global_redirect_stdout_to_server:
            _init_stdout_redirect()

        if _global_redirect_stderr_to_server:
            _init_stderr_redirect()

    def init_gui_support(self):
        if self._installed_gui_support:
            return
        self._installed_gui_support = True

        # enable_gui and enable_gui_function in activate_matplotlib should be called in main thread. Unlike integrated console,
        # in the debug console we have no interpreter instance with exec_queue, but we run this code in the main
        # thread and can call it directly.
        class _ReturnGuiLoopControlHelper:
            _return_control_osc = False

        def return_control():
            # Some of the input hooks (e.g. Qt4Agg) check return control without doing
            # a single operation, so we don't return True on every
            # call when the debug hook is in place to allow the GUI to run
            _ReturnGuiLoopControlHelper._return_control_osc = not _ReturnGuiLoopControlHelper._return_control_osc
            return _ReturnGuiLoopControlHelper._return_control_osc

        from pydev_ipython.inputhook import set_return_control_callback, enable_gui

        set_return_control_callback(return_control)

        if self._gui_event_loop == "matplotlib":
            # prepare debugger for matplotlib integration with GUI event loop
            from pydev_ipython.matplotlibtools import activate_matplotlib, activate_pylab, activate_pyplot, do_enable_gui

            self.mpl_modules_for_patching = {
                "matplotlib": lambda: activate_matplotlib(do_enable_gui),
                "matplotlib.pyplot": activate_pyplot,
                "pylab": activate_pylab,
            }
        else:
            self.activate_gui_function = enable_gui

    def _activate_gui_if_needed(self):
        if self.gui_in_use:
            return

        if len(self.mpl_modules_for_patching) > 0:
            if is_current_thread_main_thread():  # Note that we call only in the main thread.
                for module in list(self.mpl_modules_for_patching):
                    if module in sys.modules:
                        activate_function = self.mpl_modules_for_patching.pop(module, None)
                        if activate_function is not None:
                            activate_function()
                        self.gui_in_use = True

        if self.activate_gui_function:
            if is_current_thread_main_thread():  # Only call enable_gui in the main thread.
                try:
                    # First try to activate builtin GUI event loops.
                    self.activate_gui_function(self._gui_event_loop)
                    self.activate_gui_function = None
                    self.gui_in_use = True
                except ValueError:
                    # The user requested a custom GUI event loop, try to import it.
                    from pydev_ipython.inputhook import set_inputhook

                    try:
                        inputhook_function = import_attr_from_module(self._gui_event_loop)
                        set_inputhook(inputhook_function)
                        self.gui_in_use = True
                    except Exception as e:
                        pydev_log.debug("Cannot activate custom GUI event loop {}: {}".format(self._gui_event_loop, e))
                    finally:
                        self.activate_gui_function = None

    def _call_input_hook(self):
        try:
            from pydev_ipython.inputhook import get_inputhook

            inputhook = get_inputhook()
            if inputhook:
                inputhook()
        except:
            pass

    def notify_skipped_step_in_because_of_filters(self, frame):
        self.writer.add_command(self.cmd_factory.make_skipped_step_in_because_of_filters(self, frame))

    def notify_thread_created(self, thread_id, thread, use_lock=True):
        if self.writer is None:
            # Protect about threads being created before the communication structure is in place
            # (note that they will appear later on anyways as pydevd does reconcile live/dead threads
            # when processing internal commands, albeit it may take longer and in general this should
            # not be usual as it's expected that the debugger is live before other threads are created).
            return

        with self._lock_running_thread_ids if use_lock else NULL:
            if not self._enable_thread_notifications:
                return

            if thread_id in self._running_thread_ids:
                return

            additional_info = set_additional_thread_info(thread)
            if additional_info.pydev_notify_kill:
                # After we notify it should be killed, make sure we don't notify it's alive (on a racing condition
                # this could happen as we may notify before the thread is stopped internally).
                return

            self._running_thread_ids[thread_id] = thread

        self.writer.add_command(self.cmd_factory.make_thread_created_message(thread))

    def notify_thread_not_alive(self, thread_id, use_lock=True):
        """if thread is not alive, cancel trace_dispatch processing"""
        if self.writer is None:
            return

        with self._lock_running_thread_ids if use_lock else NULL:
            if not self._enable_thread_notifications:
                return

            thread = self._running_thread_ids.pop(thread_id, None)
            if thread is None:
                return

            additional_info = set_additional_thread_info(thread)
            was_notified = additional_info.pydev_notify_kill
            if not was_notified:
                additional_info.pydev_notify_kill = True
            remove_additional_info(additional_info)

        self.writer.add_command(self.cmd_factory.make_thread_killed_message(thread_id))

    def set_enable_thread_notifications(self, enable):
        with self._lock_running_thread_ids:
            if self._enable_thread_notifications != enable:
                self._enable_thread_notifications = enable

                if enable:
                    # As it was previously disabled, we have to notify about existing threads again
                    # (so, clear the cache related to that).
                    self._running_thread_ids = {}

    def process_internal_commands(self, process_thread_ids: Optional[tuple]=None):
        """
        This function processes internal commands.
        """
        # If this method is being called before the debugger is ready to run we should not notify
        # about threads and should only process commands sent to all threads.
        ready_to_run = self.ready_to_run

        dispose = False
        with self._main_lock:
            program_threads_alive = {}
            if ready_to_run:
                self.check_output_redirect()

                all_threads = threadingEnumerate()
                program_threads_dead = []
                with self._lock_running_thread_ids:
                    reset_cache = not self._running_thread_ids

                    for t in all_threads:
                        if getattr(t, "is_pydev_daemon_thread", False):
                            pass  # I.e.: skip the DummyThreads created from pydev daemon threads
                        elif isinstance(t, PyDBDaemonThread):
                            pydev_log.error_once("Error in debugger: Found PyDBDaemonThread not marked with is_pydev_daemon_thread=True.")

                        elif is_thread_alive(t):
                            if reset_cache:
                                # Fix multiprocessing debug with breakpoints in both main and child processes
                                # (https://youtrack.jetbrains.com/issue/PY-17092) When the new process is created, the main
                                # thread in the new process already has the attribute 'pydevd_id', so the new thread doesn't
                                # get new id with its process number and the debugger loses access to both threads.
                                # Therefore we should update thread_id for every main thread in the new process.
                                clear_cached_thread_id(t)

                            thread_id = get_thread_id(t)
                            program_threads_alive[thread_id] = t

                            self.notify_thread_created(thread_id, t, use_lock=False)

                    # Compute and notify about threads which are no longer alive.
                    thread_ids = list(self._running_thread_ids.keys())
                    for thread_id in thread_ids:
                        if thread_id not in program_threads_alive:
                            program_threads_dead.append(thread_id)

                    for thread_id in program_threads_dead:
                        self.notify_thread_not_alive(thread_id, use_lock=False)

            cmds_to_execute = []

            # Without self._lock_running_thread_ids
            if len(program_threads_alive) == 0 and ready_to_run:
                dispose = True
            else:
                curr_thread_id = get_current_thread_id(threadingCurrentThread())
                if process_thread_ids is None:
                    # Actually process the commands now (make sure we don't have a lock for _lock_running_thread_ids
                    # acquired at this point as it could lead to a deadlock if some command evaluated tried to
                    # create a thread and wait for it -- which would try to notify about it getting that lock).
                    if ready_to_run:
                        process_thread_ids = (curr_thread_id, "*")
                    else:
                        process_thread_ids = ("*",)

                for thread_id in process_thread_ids:
                    queue, _event = self.get_internal_queue_and_event(thread_id)

                    # some commands must be processed by the thread itself... if that's the case,
                    # we will re-add the commands to the queue after executing.
                    cmds_to_add_back = []

                    try:
                        while True:
                            internal_cmd = queue.get(False)
                            try:
                                if internal_cmd.can_be_executed_by(curr_thread_id):
                                    cmds_to_execute.append(internal_cmd)
                                else:
                                    pydev_log.verbose("NOT processing internal command: %s ", internal_cmd)
                                    cmds_to_add_back.append(internal_cmd)
                            except:
                                pydev_log.exception()
                                raise

                    except _queue.Empty:  # @UndefinedVariable
                        # this is how we exit
                        for internal_cmd in cmds_to_add_back:
                            queue.put(internal_cmd)

        if dispose:
            # Note: must be called without the main lock to avoid deadlocks.
            self.dispose_and_kill_all_pydevd_threads()
        else:
            # Actually execute the commands without the main lock!
            for internal_cmd in cmds_to_execute:
                pydev_log.verbose("processing internal command: %s", internal_cmd)
                try:
                    internal_cmd.do_it(self)
                except:
                    pydev_log.exception("Error processing internal command.")

    def consolidate_breakpoints(self, canonical_normalized_filename, id_to_breakpoint, file_to_line_to_breakpoints):
        break_dict = {}
        for _breakpoint_id, pybreakpoint in id_to_breakpoint.items():
            break_dict[pybreakpoint.line] = pybreakpoint

        file_to_line_to_breakpoints[canonical_normalized_filename] = break_dict
        self._clear_caches()

    def add_break_on_exception(
        self,
        exception,
        condition,
        expression,
        notify_on_handled_exceptions,
        notify_on_unhandled_exceptions,
        notify_on_user_unhandled_exceptions,
        notify_on_first_raise_only,
        ignore_libraries=False,
    ):
        try:
            eb = ExceptionBreakpoint(
                exception,
                condition,
                expression,
                notify_on_handled_exceptions,
                notify_on_unhandled_exceptions,
                notify_on_user_unhandled_exceptions,
                notify_on_first_raise_only,
                ignore_libraries,
            )
        except ImportError:
            pydev_log.critical("Error unable to add break on exception for: %s (exception could not be imported).", exception)
            return None

        if eb.notify_on_unhandled_exceptions:
            cp = self.break_on_uncaught_exceptions.copy()
            cp[exception] = eb
            pydev_log.info("Exceptions to hook on terminate: %s.", cp)
            self.break_on_uncaught_exceptions = cp

        if eb.notify_on_handled_exceptions:
            cp = self.break_on_caught_exceptions.copy()
            cp[exception] = eb
            pydev_log.info("Exceptions to hook always: %s.", cp)
            self.break_on_caught_exceptions = cp

        if eb.notify_on_user_unhandled_exceptions:
            cp = self.break_on_user_uncaught_exceptions.copy()
            cp[exception] = eb
            pydev_log.info("Exceptions to hook on user uncaught code: %s.", cp)
            self.break_on_user_uncaught_exceptions = cp

        return eb

    def set_suspend(
        self,
        thread,
        stop_reason: int,
        suspend_other_threads: bool=False,
        is_pause=False,
        original_step_cmd: int=-1,
        suspend_requested: bool=False,
    ):
        """
        :param thread:
            The thread which should be suspended.

        :param stop_reason:
            Reason why the thread was suspended.

        :param suspend_other_threads:
            Whether to force other threads to be suspended (i.e.: when hitting a breakpoint
            with a suspend all threads policy).

        :param is_pause:
            If this is a pause to suspend all threads, any thread can be considered as the 'main'
            thread paused.

        :param original_step_cmd:
            If given we may change the stop reason to this.

        :param suspend_requested:
            If the execution will be suspended right away then this may be false, otherwise,
            if the thread should be stopped due to this suspend at a later time then it
            should be true.
        """
        self._threads_suspended_single_notification.increment_suspend_time()
        if is_pause:
            self._threads_suspended_single_notification.on_pause()

        info = mark_thread_suspended(thread, stop_reason, original_step_cmd=original_step_cmd)

        if (suspend_requested or is_pause) and PYDEVD_USE_SYS_MONITORING:
            pydevd_sys_monitoring.update_monitor_events(suspend_requested=True)

        if is_pause:
            # Must set tracing after setting the state to suspend.
            frame = info.get_topmost_frame(thread)
            if frame is not None:
                # Where suspend was requested
                # traceback.print_stack(frame)
                try:
                    self.set_trace_for_frame_and_parents(thread.ident, frame)
                finally:
                    frame = None

        # If conditional breakpoint raises any exception during evaluation send the details to the client.
        if stop_reason == CMD_SET_BREAK and info.conditional_breakpoint_exception is not None:
            conditional_breakpoint_exception_tuple = info.conditional_breakpoint_exception
            info.conditional_breakpoint_exception = None
            self._send_breakpoint_condition_exception(thread, conditional_breakpoint_exception_tuple)

        if not suspend_other_threads and self.multi_threads_single_notification:
            # In the mode which gives a single notification when all threads are
            # stopped, stop all threads whenever a set_suspend is issued.
            suspend_other_threads = True

        if suspend_other_threads:
            # Suspend all except the current one (which we're currently suspending already).
            suspend_all_threads(self, except_thread=thread)

        if PYDEVD_USE_SYS_MONITORING:
            pydevd_sys_monitoring.restart_events()

    def _send_breakpoint_condition_exception(self, thread, conditional_breakpoint_exception_tuple):
        """If conditional breakpoint raises an exception during evaluation
        send exception details to java
        """
        thread_id = get_thread_id(thread)
        # conditional_breakpoint_exception_tuple - should contain 2 values (exception_type, stacktrace)
        if conditional_breakpoint_exception_tuple and len(conditional_breakpoint_exception_tuple) == 2:
            exc_type, stacktrace = conditional_breakpoint_exception_tuple
            int_cmd = InternalGetBreakpointException(thread_id, exc_type, stacktrace)
            self.post_internal_command(int_cmd, thread_id)

    def send_caught_exception_stack(self, thread, arg, curr_frame_id):
        """Sends details on the exception which was caught (and where we stopped) to the java side.

        arg is: exception type, description, traceback object
        """
        thread_id = get_thread_id(thread)
        int_cmd = InternalSendCurrExceptionTrace(thread_id, arg, curr_frame_id)
        self.post_internal_command(int_cmd, thread_id)

    def send_caught_exception_stack_proceeded(self, thread):
        """Sends that some thread was resumed and is no longer showing an exception trace."""
        thread_id = get_thread_id(thread)
        int_cmd = InternalSendCurrExceptionTraceProceeded(thread_id)
        self.post_internal_command(int_cmd, thread_id)
        self.process_internal_commands()

    def send_process_created_message(self):
        """Sends a message that a new process has been created."""
        if self.writer is None or self.cmd_factory is None:
            return
        cmd = self.cmd_factory.make_process_created_message()
        self.writer.add_command(cmd)

    def send_process_about_to_be_replaced(self):
        """Sends a message that a new process has been created."""
        if self.writer is None or self.cmd_factory is None:
            return
        cmd = self.cmd_factory.make_process_about_to_be_replaced_message()
        if cmd is NULL_NET_COMMAND:
            return

        sent = [False]

        def after_sent(*args, **kwargs):
            sent[0] = True

        cmd.call_after_send(after_sent)
        self.writer.add_command(cmd)

        timeout = 5  # Wait up to 5 seconds
        initial_time = time.time()
        while not sent[0]:
            time.sleep(0.05)

            if (time.time() - initial_time) > timeout:
                pydev_log.critical("pydevd: Sending message related to process being replaced timed-out after %s seconds", timeout)
                break

    def set_next_statement(self, frame, event, func_name, next_line):
        stop = False
        response_msg = ""
        old_line = frame.f_lineno
        if event == "line" or event == "exception":
            # If we're already in the correct context, we have to stop it now, because we can act only on
            # line events -- if a return was the next statement it wouldn't work (so, we have this code
            # repeated at pydevd_frame).

            curr_func_name = frame.f_code.co_name

            # global context is set with an empty name
            if curr_func_name in ("?", "<module>"):
                curr_func_name = ""

            if func_name == "*" or curr_func_name == func_name:
                line = next_line
                frame.f_trace = self.trace_dispatch
                frame.f_lineno = line
                stop = True
            else:
                response_msg = "jump is available only within the bottom frame"
        return stop, old_line, response_msg

    def cancel_async_evaluation(self, thread_id, frame_id):
        with self._main_lock:
            try:
                all_threads = threadingEnumerate()
                for t in all_threads:
                    if (
                        getattr(t, "is_pydev_daemon_thread", False)
                        and hasattr(t, "cancel_event")
                        and t.thread_id == thread_id
                        and t.frame_id == frame_id
                    ):
                        t.cancel_event.set()
            except:
                pydev_log.exception()

    def find_frame(self, thread_id, frame_id):
        """returns a frame on the thread that has a given frame_id"""
        return self.suspended_frames_manager.find_frame(thread_id, frame_id)

    def do_wait_suspend(self, thread, frame, event, arg, exception_type=None):  # @UnusedVariable
        """busy waits until the thread state changes to RUN
        it expects thread's state as attributes of the thread.
        Upon running, processes any outstanding Stepping commands.

        :param exception_type:
            If pausing due to an exception, its type.
        """
        if USE_CUSTOM_SYS_CURRENT_FRAMES_MAP:
            constructed_tid_to_last_frame[thread.ident] = sys._getframe()

        # Only process from all threads, not for current one (we'll do that later on in this method).
        self.process_internal_commands(("*",))

        thread_id = get_current_thread_id(thread)

        # if DebugInfoHolder.DEBUG_TRACE_LEVEL >= 2:
        #     pydev_log.debug('do_wait_suspend %s %s %s %s %s %s (%s)' % (frame.f_lineno, frame.f_code.co_name, frame.f_code.co_filename, event, arg, constant_to_str(thread.additional_info.pydev_step_cmd), constant_to_str(thread.additional_info.pydev_original_step_cmd)))
        #     pydev_log.debug('--- internal stack ---')
        #     _f = sys._getframe()
        #     while _f is not None:
        #         pydev_log.debug('  -> %s' % (_f))
        #         _f = _f.f_back
        #     pydev_log.debug('--- end internal stack ---')

        # Send the suspend message
        message = thread.additional_info.pydev_message
        trace_suspend_type = thread.additional_info.trace_suspend_type
        thread.additional_info.trace_suspend_type = "trace"  # Reset to trace mode for next call.
        stop_reason = thread.stop_reason

        frames_list = None

        if arg is not None and event == "exception":
            # arg must be the exception info (tuple(exc_type, exc, traceback))
            exc_type, exc_desc, trace_obj = arg
            if trace_obj is not None:
                frames_list = pydevd_frame_utils.create_frames_list_from_traceback(
                    trace_obj, frame, exc_type, exc_desc, exception_type=exception_type
                )

        if frames_list is None:
            frames_list = pydevd_frame_utils.create_frames_list_from_frame(frame)

        if DebugInfoHolder.DEBUG_TRACE_LEVEL > 2:
            pydev_log.debug(
                "PyDB.do_wait_suspend\nname: %s (line: %s)\n file: %s\n event: %s\n arg: %s\n step: %s (original step: %s)\n thread: %s, thread id: %s, id(thread): %s",
                frame.f_code.co_name,
                frame.f_lineno,
                frame.f_code.co_filename,
                event,
                arg,
                constant_to_str(thread.additional_info.pydev_step_cmd),
                constant_to_str(thread.additional_info.pydev_original_step_cmd),
                thread,
                thread_id,
                id(thread),
            )
            for f in frames_list:
                pydev_log.debug("  Stack: %s, %s, %s", f.f_code.co_filename, f.f_code.co_name, f.f_lineno)

        with self.suspended_frames_manager.track_frames(self) as frames_tracker:
            frames_tracker.track(thread_id, frames_list)
            cmd = frames_tracker.create_thread_suspend_command(
                thread_id, stop_reason, message, trace_suspend_type, thread, thread.additional_info
            )
            self.writer.add_command(cmd)

            with CustomFramesContainer.custom_frames_lock:  # @UndefinedVariable
                from_this_thread = []

                for frame_custom_thread_id, custom_frame in CustomFramesContainer.custom_frames.items():
                    if custom_frame.thread_id == thread.ident:
                        frames_tracker.track(
                            thread_id,
                            pydevd_frame_utils.create_frames_list_from_frame(custom_frame.frame),
                            frame_custom_thread_id=frame_custom_thread_id,
                        )
                        # print('Frame created as thread: %s' % (frame_custom_thread_id,))

                        self.writer.add_command(
                            self.cmd_factory.make_custom_frame_created_message(frame_custom_thread_id, custom_frame.name)
                        )

                        self.writer.add_command(
                            frames_tracker.create_thread_suspend_command(
                                frame_custom_thread_id, CMD_THREAD_SUSPEND, "", trace_suspend_type, thread, thread.additional_info
                            )
                        )

                    from_this_thread.append(frame_custom_thread_id)

            with self._threads_suspended_single_notification.notify_thread_suspended(thread_id, thread, stop_reason):
                keep_suspended = self._do_wait_suspend(thread, frame, event, arg, trace_suspend_type, from_this_thread, frames_tracker)

        frames_list = None

        if keep_suspended:
            # This means that we should pause again after a set next statement.
            self._threads_suspended_single_notification.increment_suspend_time()
            self.do_wait_suspend(thread, frame, event, arg, exception_type)
        if DebugInfoHolder.DEBUG_TRACE_LEVEL > 2:
            pydev_log.debug("Leaving PyDB.do_wait_suspend: %s (%s) %s", thread, thread_id, id(thread))

    def _do_wait_suspend(self, thread, frame, event, arg, trace_suspend_type, from_this_thread, frames_tracker):
        info = thread.additional_info
        try:
            info.is_in_wait_loop = True
            info.update_stepping_info()
            info.step_in_initial_location = None
            keep_suspended = False

            with self._main_lock:  # Use lock to check if suspended state changed
                activate_gui = info.pydev_state == STATE_SUSPEND and not self.pydb_disposed

            in_main_thread = is_current_thread_main_thread()
            if activate_gui and in_main_thread:
                # before every stop check if matplotlib modules were imported inside script code
                # or some GUI event loop needs to be activated
                self._activate_gui_if_needed()

            # self.process_internal_commands(): processes for all the threads
            # and updates running threads. This was called once in `do_wait_suspend`
            # At this point it's just processing for this thread.
            # Note that clients may not post an actual event (for instance, it
            # could just set the internal state and signal the event instead
            # of posting a command to the queue). In any case, if an item is
            # put in the queue, the event must be set too.
            curr_thread_id = get_current_thread_id(threadingCurrentThread())
            queue, notify_event = self.get_internal_queue_and_event(curr_thread_id)

            wait_timeout = TIMEOUT_SLOW
            while True:
                with self._main_lock:  # Use lock to check if suspended state changed
                    if info.pydev_state != STATE_SUSPEND or (self.pydb_disposed and not self.terminate_requested):
                        # Note: we can't exit here if terminate was requested while a breakpoint was hit.
                        break

                if in_main_thread and self.gui_in_use:
                    wait_timeout = TIMEOUT_FAST
                    # call input hooks if only GUI is in use
                    self._call_input_hook()

                # No longer process commands for '*' at this point, just the
                # ones related to this thread.
                try:
                    internal_cmd = queue.get(False)
                except _queue.Empty:
                    pass
                else:
                    if internal_cmd.can_be_executed_by(curr_thread_id):
                        pydev_log.verbose("processing internal command: %s", internal_cmd)
                        try:
                            internal_cmd.do_it(self)
                        except:
                            pydev_log.exception("Error processing internal command.")
                    else:
                        # This shouldn't really happen...
                        pydev_log.verbose("NOT processing internal command: %s ", internal_cmd)
                        queue.put(internal_cmd)
                        wait_timeout = TIMEOUT_FAST

                notify_event.wait(wait_timeout)
                notify_event.clear()

        finally:
            info.is_in_wait_loop = False
            info.update_stepping_info()

        self.cancel_async_evaluation(get_current_thread_id(thread), str(id(frame)))

        # process any stepping instructions
        if info.pydev_step_cmd in (CMD_STEP_INTO, CMD_STEP_INTO_MY_CODE):
            info.step_in_initial_location = (frame, frame.f_lineno)
            if frame.f_code.co_flags & 0x80:  # CO_COROUTINE = 0x80
                # When in a coroutine we switch to CMD_STEP_INTO_COROUTINE.
                info.pydev_step_cmd = CMD_STEP_INTO_COROUTINE
                info.pydev_step_stop = frame
                self.set_trace_for_frame_and_parents(thread.ident, frame)
            else:
                info.pydev_step_stop = None
                self.set_trace_for_frame_and_parents(thread.ident, frame)

        elif info.pydev_step_cmd in (CMD_STEP_OVER, CMD_STEP_OVER_MY_CODE, CMD_SMART_STEP_INTO):
            info.pydev_step_stop = frame
            self.set_trace_for_frame_and_parents(thread.ident, frame)

        elif info.pydev_step_cmd == CMD_RUN_TO_LINE or info.pydev_step_cmd == CMD_SET_NEXT_STATEMENT:
            info.pydev_step_stop = None
            self.set_trace_for_frame_and_parents(thread.ident, frame)
            stop = False
            response_msg = ""
            try:
                stop, _old_line, response_msg = self.set_next_statement(frame, event, info.pydev_func_name, info.pydev_next_line)
            except ValueError as e:
                response_msg = "%s" % e
            finally:
                seq = info.pydev_message
                cmd = self.cmd_factory.make_set_next_stmnt_status_message(seq, stop, response_msg)
                self.writer.add_command(cmd)
                info.pydev_message = ""

            if stop:
                # Uninstall the current frames tracker before running it.
                frames_tracker.untrack_all()
                cmd = self.cmd_factory.make_thread_run_message(self, get_current_thread_id(thread), info.pydev_step_cmd)
                self.writer.add_command(cmd)
                info.pydev_state = STATE_SUSPEND
                thread.stop_reason = CMD_SET_NEXT_STATEMENT
                keep_suspended = True

            else:
                # Set next did not work...
                info.pydev_original_step_cmd = -1
                info.pydev_step_cmd = -1
                info.pydev_state = STATE_SUSPEND
                thread.stop_reason = CMD_THREAD_SUSPEND
                # return to the suspend state and wait for other command (without sending any
                # additional notification to the client).
                return self._do_wait_suspend(thread, frame, event, arg, trace_suspend_type, from_this_thread, frames_tracker)

        elif info.pydev_step_cmd in (CMD_STEP_RETURN, CMD_STEP_RETURN_MY_CODE):
            back_frame = frame.f_back
            force_check_project_scope = info.pydev_step_cmd == CMD_STEP_RETURN_MY_CODE

            if force_check_project_scope or self.is_files_filter_enabled:
                while back_frame is not None:
                    if self.apply_files_filter(back_frame, back_frame.f_code.co_filename, force_check_project_scope):
                        frame = back_frame
                        back_frame = back_frame.f_back
                    else:
                        break

            if back_frame is not None:
                # steps back to the same frame (in a return call it will stop in the 'back frame' for the user)
                info.pydev_step_stop = frame
                self.set_trace_for_frame_and_parents(thread.ident, frame)
            else:
                # No back frame?!? -- this happens in jython when we have some frame created from an awt event
                # (the previous frame would be the awt event, but this doesn't make part of 'jython', only 'java')
                # so, if we're doing a step return in this situation, it's the same as just making it run
                info.pydev_step_stop = None
                info.pydev_original_step_cmd = -1
                info.pydev_step_cmd = -1
                info.pydev_state = STATE_RUN

        if PYDEVD_IPYTHON_COMPATIBLE_DEBUGGING:
            info.pydev_use_scoped_step_frame = False
            if info.pydev_step_cmd in (CMD_STEP_OVER, CMD_STEP_OVER_MY_CODE, CMD_STEP_INTO, CMD_STEP_INTO_MY_CODE):
                # i.e.: We're stepping: check if the stepping should be scoped (i.e.: in ipython
                # each line is executed separately in a new frame, in which case we need to consider
                # the next line as if it was still in the same frame).
                f = frame.f_back
                if f and f.f_code.co_name == PYDEVD_IPYTHON_CONTEXT[1]:
                    f = f.f_back
                    if f and f.f_code.co_name == PYDEVD_IPYTHON_CONTEXT[2]:
                        info.pydev_use_scoped_step_frame = True
                        pydev_log.info("Using (ipython) scoped stepping.")
                del f

        del frame
        cmd = self.cmd_factory.make_thread_run_message(self, get_current_thread_id(thread), info.pydev_step_cmd)
        self.writer.add_command(cmd)

        with CustomFramesContainer.custom_frames_lock:
            # The ones that remained on last_running must now be removed.
            for frame_id in from_this_thread:
                # print('Removing created frame: %s' % (frame_id,))
                self.writer.add_command(self.cmd_factory.make_thread_killed_message(frame_id))

        info.update_stepping_info()
        return keep_suspended

    def do_stop_on_unhandled_exception(self, thread, frame, frames_byid, arg):
        pydev_log.debug("We are stopping in unhandled exception.")
        try:
            add_exception_to_frame(frame, arg)
            self.send_caught_exception_stack(thread, arg, id(frame))
            try:
                self.set_suspend(thread, CMD_ADD_EXCEPTION_BREAK)
                self.do_wait_suspend(thread, frame, "exception", arg, EXCEPTION_TYPE_UNHANDLED)
            except:
                self.send_caught_exception_stack_proceeded(thread)
        except:
            pydev_log.exception("We've got an error while stopping in unhandled exception: %s.", arg[0])
        finally:
            remove_exception_from_frame(frame)
            frame = None

    def set_trace_for_frame_and_parents(self, thread_ident: Optional[int], frame, **kwargs):
        disable = kwargs.pop("disable", False)
        assert not kwargs

        DEBUG = True  # 'defaulttags' in frame.f_code.co_filename

        while frame is not None:
            if not isinstance(frame, FrameType):
                # This is the case for django/jinja frames.
                frame = frame.f_back
                continue

            # Don't change the tracing on debugger-related files
            file_type = self.get_file_type(frame)
            if PYDEVD_USE_SYS_MONITORING:
                if file_type is None:
                    if disable:
                        if DEBUG:
                            pydev_log.debug("Disable tracing of frame: %s - %s", frame.f_code.co_filename, frame.f_code.co_name)
                        pydevd_sys_monitoring.disable_code_tracing(frame.f_code)

                    else:
                        if DEBUG:
                            pydev_log.debug("Set tracing of frame: %s - %s", frame.f_code.co_filename, frame.f_code.co_name)
                        pydevd_sys_monitoring.enable_code_tracing(thread_ident, frame.f_code, frame)
                else:
                    if DEBUG:
                        pydev_log.debug("SKIP set tracing of frame: %s - %s", frame.f_code.co_filename, frame.f_code.co_name)
            else:
                # Not using sys.monitoring.
                if file_type is None:
                    if disable:
                        if DEBUG:
                            pydev_log.debug("Disable tracing of frame: %s - %s", frame.f_code.co_filename, frame.f_code.co_name)
                        if frame.f_trace is not None and frame.f_trace is not NO_FTRACE:
                            frame.f_trace = NO_FTRACE

                    elif frame.f_trace is not self.trace_dispatch:
                        if DEBUG:
                            pydev_log.debug("Set tracing of frame: %s - %s", frame.f_code.co_filename, frame.f_code.co_name)
                        frame.f_trace = self.trace_dispatch
                else:
                    if DEBUG:
                        pydev_log.debug("SKIP set tracing of frame: %s - %s", frame.f_code.co_filename, frame.f_code.co_name)

            frame = frame.f_back

        del frame

    def _create_pydb_command_thread(self):
        curr_pydb_command_thread = self.py_db_command_thread
        if curr_pydb_command_thread is not None:
            curr_pydb_command_thread.do_kill_pydev_thread()

        new_pydb_command_thread = self.py_db_command_thread = PyDBCommandThread(self)
        new_pydb_command_thread.start()

    def _create_check_output_thread(self):
        curr_output_checker_thread = self.check_alive_thread
        if curr_output_checker_thread is not None:
            curr_output_checker_thread.do_kill_pydev_thread()

        check_alive_thread = self.check_alive_thread = CheckAliveThread(self)
        check_alive_thread.start()

    def start_auxiliary_daemon_threads(self):
        self._create_pydb_command_thread()
        self._create_check_output_thread()

    def __wait_for_threads_to_finish(self, timeout):
        try:
            with self._wait_for_threads_to_finish_called_lock:
                wait_for_threads_to_finish_called = self._wait_for_threads_to_finish_called
                self._wait_for_threads_to_finish_called = True

            if wait_for_threads_to_finish_called:
                # Make sure that we wait for the previous call to be finished.
                self._wait_for_threads_to_finish_called_event.wait(timeout=timeout)
            else:
                try:

                    def get_pydb_daemon_threads_to_wait():
                        pydb_daemon_threads = set(self.created_pydb_daemon_threads)
                        pydb_daemon_threads.discard(self.check_alive_thread)
                        pydb_daemon_threads.discard(threading.current_thread())
                        return pydb_daemon_threads

                    pydev_log.debug("PyDB.dispose_and_kill_all_pydevd_threads waiting for pydb daemon threads to finish")
                    started_at = time.time()
                    # Note: we wait for all except the check_alive_thread (which is not really a daemon
                    # thread and it can call this method itself).
                    while time.time() < started_at + timeout:
                        if len(get_pydb_daemon_threads_to_wait()) == 0:
                            break
                        time.sleep(1 / 10.0)
                    else:
                        thread_names = [t.name for t in get_pydb_daemon_threads_to_wait()]
                        if thread_names:
                            pydev_log.debug("The following pydb threads may not have finished correctly: %s", ", ".join(thread_names))
                finally:
                    self._wait_for_threads_to_finish_called_event.set()
        except:
            pydev_log.exception()

    def dispose_and_kill_all_pydevd_threads(self, wait=True, timeout=0.5):
        """
        When this method is called we finish the debug session, terminate threads
        and if this was registered as the global instance, unregister it -- afterwards
        it should be possible to create a new instance and set as global to start
        a new debug session.

        :param bool wait:
            If True we'll wait for the threads to be actually finished before proceeding
            (based on the available timeout).
            Note that this must be thread-safe and if one thread is waiting the other thread should
            also wait.
        """
        try:
            back_frame = sys._getframe().f_back
            pydev_log.debug(
                'PyDB.dispose_and_kill_all_pydevd_threads (called from: File "%s", line %s, in %s)',
                back_frame.f_code.co_filename,
                back_frame.f_lineno,
                back_frame.f_code.co_name,
            )
            back_frame = None
            with self._disposed_lock:
                disposed = self.pydb_disposed
                self.pydb_disposed = True

            if disposed:
                if wait:
                    pydev_log.debug("PyDB.dispose_and_kill_all_pydevd_threads (already disposed - wait)")
                    self.__wait_for_threads_to_finish(timeout)
                else:
                    pydev_log.debug("PyDB.dispose_and_kill_all_pydevd_threads (already disposed - no wait)")
                return

            pydev_log.debug("PyDB.dispose_and_kill_all_pydevd_threads (first call)")

            # Wait until a time when there are no commands being processed to kill the threads.
            started_at = time.time()
            while time.time() < started_at + timeout:
                with self._main_lock:
                    writer = self.writer
                    if writer is None or writer.empty():
                        pydev_log.debug("PyDB.dispose_and_kill_all_pydevd_threads no commands being processed.")
                        break
            else:
                pydev_log.debug("PyDB.dispose_and_kill_all_pydevd_threads timed out waiting for writer to be empty.")

            pydb_daemon_threads = set(self.created_pydb_daemon_threads)
            for t in pydb_daemon_threads:
                if hasattr(t, "do_kill_pydev_thread"):
                    pydev_log.debug("PyDB.dispose_and_kill_all_pydevd_threads killing thread: %s", t)
                    t.do_kill_pydev_thread()

            if wait:
                self.__wait_for_threads_to_finish(timeout)
            else:
                pydev_log.debug("PyDB.dispose_and_kill_all_pydevd_threads: no wait")

            py_db = get_global_debugger()
            if py_db is self:
                set_global_debugger(None)
        except:
            pydev_log.debug("PyDB.dispose_and_kill_all_pydevd_threads: exception")
            try:
                if DebugInfoHolder.DEBUG_TRACE_LEVEL >= 3:
                    pydev_log.exception()
            except:
                pass
        finally:
            if self._client_socket:
                self._client_socket.close()
                self._client_socket = None

            pydev_log.debug("PyDB.dispose_and_kill_all_pydevd_threads: finished")

    def prepare_to_run(self):
        """Shared code to prepare debugging by installing traces and registering threads"""
        self.patch_threads()
        self.start_auxiliary_daemon_threads()

    def patch_threads(self):
        if PYDEVD_USE_SYS_MONITORING:
            pydevd_sys_monitoring.start_monitoring(all_threads=True)
        else:
            try:
                # not available in jython!
                threading.settrace(self.trace_dispatch)  # for all future threads
            except:
                pass

        from _pydev_bundle.pydev_monkey import patch_thread_modules

        patch_thread_modules()

    def run(self, file, globals=None, locals=None, is_module=False, set_trace=True):
        module_name = None
        entry_point_fn = ""
        if is_module:
            # When launching with `python -m <module>`, python automatically adds
            # an empty path to the PYTHONPATH which resolves files in the current
            # directory, so, depending how pydevd itself is launched, we may need
            # to manually add such an entry to properly resolve modules in the
            # current directory (see: https://github.com/Microsoft/ptvsd/issues/1010).
            if "" not in sys.path:
                sys.path.insert(0, "")
            file, _, entry_point_fn = file.partition(":")
            module_name = file
            filename = get_fullname(file)
            if filename is None:
                mod_dir = get_package_dir(module_name)
                if mod_dir is None:
                    sys.stderr.write("No module named %s\n" % file)
                    return
                else:
                    filename = get_fullname("%s.__main__" % module_name)
                    if filename is None:
                        sys.stderr.write("No module named %s\n" % file)
                        return
                    else:
                        file = filename
            else:
                file = filename
                mod_dir = os.path.dirname(filename)
                main_py = os.path.join(mod_dir, "__main__.py")
                main_pyc = os.path.join(mod_dir, "__main__.pyc")
                if filename.endswith("__init__.pyc"):
                    if os.path.exists(main_pyc):
                        filename = main_pyc
                    elif os.path.exists(main_py):
                        filename = main_py
                elif filename.endswith("__init__.py"):
                    if os.path.exists(main_pyc) and not os.path.exists(main_py):
                        filename = main_pyc
                    elif os.path.exists(main_py):
                        filename = main_py

            sys.argv[0] = filename

        if os.path.isdir(file):
            new_target = os.path.join(file, "__main__.py")
            if os.path.isfile(new_target):
                file = new_target

        m = None
        if globals is None:
            m = save_main_module(file, "pydevd")
            globals = m.__dict__
            try:
                globals["__builtins__"] = __builtins__
            except NameError:
                pass  # Not there on Jython...

        if locals is None:
            locals = globals

        # Predefined (writable) attributes: __name__ is the module's name;
        # __doc__ is the module's documentation string, or None if unavailable;
        # __file__ is the pathname of the file from which the module was loaded,
        # if it was loaded from a file. The __file__ attribute is not present for
        # C modules that are statically linked into the interpreter; for extension modules
        # loaded dynamically from a shared library, it is the pathname of the shared library file.

        # I think this is an ugly hack, bug it works (seems to) for the bug that says that sys.path should be the same in
        # debug and run.
        if sys.path[0] != "" and m is not None and m.__file__.startswith(sys.path[0]):
            # print >> sys.stderr, 'Deleting: ', sys.path[0]
            del sys.path[0]

        if not is_module:
            # now, the local directory has to be added to the pythonpath
            # sys.path.insert(0, os.getcwd())
            # Changed: it's not the local directory, but the directory of the file launched
            # The file being run must be in the pythonpath (even if it was not before)
            sys.path.insert(0, os.path.split(os_path_abspath(file))[0])

        if set_trace:
            self.wait_for_ready_to_run()

            # call prepare_to_run when we already have all information about breakpoints
            self.prepare_to_run()

        t = threadingCurrentThread()
        thread_id = get_current_thread_id(t)

        if self.thread_analyser is not None:
            wrap_threads()
            self.thread_analyser.set_start_time(cur_time())
            send_concurrency_message("threading_event", 0, t.name, thread_id, "thread", "start", file, 1, None, parent=thread_id)

        if self.asyncio_analyser is not None:
            # we don't have main thread in asyncio graph, so we should add a fake event
            send_concurrency_message("asyncio_event", 0, "Task", "Task", "thread", "stop", file, 1, frame=None, parent=None)

        try:
            if INTERACTIVE_MODE_AVAILABLE:
                self.init_gui_support()
        except:
            pydev_log.exception("Matplotlib support in debugger failed")

        if hasattr(sys, "exc_clear"):
            # we should clean exception information in Python 2, before user's code execution
            sys.exc_clear()

        # Notify that the main thread is created.
        self.notify_thread_created(thread_id, t)

        # Note: important: set the tracing right before calling _exec.
        if set_trace:
            self.enable_tracing()

        return self._exec(is_module, entry_point_fn, module_name, file, globals, locals)

    def _exec(self, is_module, entry_point_fn, module_name, file, globals, locals):
        """
        This function should have frames tracked by unhandled exceptions (the `_exec` name is important).
        """
        t = threading.current_thread()  # Keep in 't' local variable to be accessed afterwards from frame.f_locals.
        if not is_module:
            globals = pydevd_runpy.run_path(file, globals, "__main__")
        else:
            # treat ':' as a separator between module and entry point function
            # if there is no entry point we run we same as with -m switch. Otherwise we perform
            # an import and execute the entry point
            if entry_point_fn:
                mod = __import__(module_name, level=0, fromlist=[entry_point_fn], globals=globals, locals=locals)
                func = getattr(mod, entry_point_fn)
                func()
            else:
                # Run with the -m switch
                globals = pydevd_runpy._run_module_as_main(module_name, alter_argv=False)
        return globals

    def wait_for_commands(self, globals):
        self._activate_gui_if_needed()

        thread = threading.current_thread()
        from _pydevd_bundle import pydevd_frame_utils

        frame = pydevd_frame_utils.Frame(
            None, -1, pydevd_frame_utils.FCode("Console", os.path.abspath(os.path.dirname(__file__))), globals, globals
        )
        thread_id = get_current_thread_id(thread)
        self.add_fake_frame(thread_id, id(frame), frame)

        cmd = self.cmd_factory.make_show_console_message(self, thread_id, frame)
        if self.writer is not None:
            self.writer.add_command(cmd)

        while True:
            if self.gui_in_use:
                # call input hooks if only GUI is in use
                self._call_input_hook()
            self.process_internal_commands()
            time.sleep(0.01)


class IDAPMessagesListener(object):

    def before_send(self, message_as_dict):
        """
        Called just before a message is sent to the IDE.

        :type message_as_dict: dict
        """

    def after_receive(self, message_as_dict):
        """
        Called just after a message is received from the IDE.

        :type message_as_dict: dict
        """


def add_dap_messages_listener(dap_messages_listener):
    """
    Adds a listener for the DAP (debug adapter protocol) messages.

    :type dap_messages_listener: IDAPMessagesListener

    :note: messages from the xml backend are not notified through this API.

    :note: the notifications are sent from threads and they are not synchronized (so,
    it's possible that a message is sent and received from different threads at the same time).
    """
    py_db = get_global_debugger()
    if py_db is None:
        raise AssertionError("PyDB is still not setup.")

    py_db.add_dap_messages_listener(dap_messages_listener)


def send_json_message(msg):
    """
    API to send some custom json message.

    :param dict|pydevd_schema.BaseSchema msg:
        The custom message to be sent.

    :return bool:
        True if the message was added to the queue to be sent and False otherwise.
    """
    py_db = get_global_debugger()
    if py_db is None:
        return False

    writer = py_db.writer
    if writer is None:
        return False

    cmd = NetCommand(-1, 0, msg, is_json=True)
    writer.add_command(cmd)
    return True


def enable_qt_support(qt_support_mode):
    from _pydev_bundle import pydev_monkey_qt

    pydev_monkey_qt.patch_qt(qt_support_mode)


def start_dump_threads_thread(filename_template, timeout, recurrent):
    """
    Helper to dump threads after a timeout.

    :param filename_template:
        A template filename, such as 'c:/temp/thread_dump_%s.txt', where the %s will
        be replaced by the time for the dump.
    :param timeout:
        The timeout (in seconds) for the dump.
    :param recurrent:
        If True we'll keep on doing thread dumps.
    """
    assert filename_template.count("%s") == 1, "Expected one %%s to appear in: %s" % (filename_template,)

    def _threads_on_timeout():
        try:
            while True:
                time.sleep(timeout)
                filename = filename_template % (time.time(),)
                try:
                    os.makedirs(os.path.dirname(filename))
                except Exception:
                    pass
                with open(filename, "w") as stream:
                    dump_threads(stream)
                if not recurrent:
                    return
        except Exception:
            pydev_log.exception()

    t = threading.Thread(target=_threads_on_timeout)
    mark_as_pydevd_daemon_thread(t)
    t.start()


def dump_threads(stream=None):
    """
    Helper to dump thread info (default is printing to stderr).
    """
    pydevd_utils.dump_threads(stream)


def usage(doExit=0):
    sys.stdout.write("Usage:\n")
    sys.stdout.write("pydevd.py --port N [(--client hostname) | --server] --file executable [file_options]\n")
    if doExit:
        sys.exit(0)


def _init_stdout_redirect():
    pydevd_io.redirect_stream_to_pydb_io_messages(std="stdout")


def _init_stderr_redirect():
    pydevd_io.redirect_stream_to_pydb_io_messages(std="stderr")


def _enable_attach(
    address,
    dont_trace_start_patterns=(),
    dont_trace_end_patterns=(),
    patch_multiprocessing=False,
    access_token=None,
    client_access_token=None,
):
    """
    Starts accepting connections at the given host/port. The debugger will not be initialized nor
    configured, it'll only start accepting connections (and will have the tracing setup in this
    thread).

    Meant to be used with the DAP (Debug Adapter Protocol) with _wait_for_attach().

    :param address: (host, port)
    :type address: tuple(str, int)
    """
    host = address[0]
    port = int(address[1])

    if SetupHolder.setup is not None:
        if port != SetupHolder.setup["port"]:
            raise AssertionError("Unable to listen in port: %s (already listening in port: %s)" % (port, SetupHolder.setup["port"]))
    settrace(
        host=host,
        port=port,
        suspend=False,
        wait_for_ready_to_run=False,
        block_until_connected=False,
        dont_trace_start_patterns=dont_trace_start_patterns,
        dont_trace_end_patterns=dont_trace_end_patterns,
        patch_multiprocessing=patch_multiprocessing,
        access_token=access_token,
        client_access_token=client_access_token,
    )

    py_db = get_global_debugger()
    py_db.wait_for_server_socket_ready()
    return py_db._server_socket_name


def _wait_for_attach(cancel=None):
    """
    Meant to be called after _enable_attach() -- the current thread will only unblock after a
    connection is in place and the DAP (Debug Adapter Protocol) sends the ConfigurationDone
    request.
    """
    py_db = get_global_debugger()
    if py_db is None:
        raise AssertionError("Debugger still not created. Please use _enable_attach() before using _wait_for_attach().")

    py_db.block_until_configuration_done(cancel=cancel)


def _is_attached():
    """
    Can be called any time to check if the connection was established and the DAP (Debug Adapter Protocol) has sent
    the ConfigurationDone request.
    """
    py_db = get_global_debugger()
    return (py_db is not None) and py_db.is_attached()


# =======================================================================================================================
# settrace
# =======================================================================================================================
def settrace(
    host=None,
    stdout_to_server=False,
    stderr_to_server=False,
    port=5678,
    suspend=True,
    trace_only_current_thread=False,
    overwrite_prev_trace=False,  # Deprecated
    patch_multiprocessing=False,
    stop_at_frame=None,
    block_until_connected=True,
    wait_for_ready_to_run=True,
    dont_trace_start_patterns=(),
    dont_trace_end_patterns=(),
    access_token=None,
    client_access_token=None,
    notify_stdin=True,
    protocol=None,
    **kwargs,
):
    """Sets the tracing function with the pydev debug function and initializes needed facilities.

    :param host: the user may specify another host, if the debug server is not in the same machine (default is the local
        host)

    :param stdout_to_server: when this is true, the stdout is passed to the debug server

    :param stderr_to_server: when this is true, the stderr is passed to the debug server
        so that they are printed in its console and not in this process console.

    :param port: specifies which port to use for communicating with the server (note that the server must be started
        in the same port). @note: currently it's hard-coded at 5678 in the client

    :param suspend: whether a breakpoint should be emulated as soon as this function is called.

    :param trace_only_current_thread: determines if only the current thread will be traced or all current and future
        threads will also have the tracing enabled.

    :param overwrite_prev_trace: deprecated

    :param patch_multiprocessing: if True we'll patch the functions which create new processes so that launched
        processes are debugged.

    :param stop_at_frame: if passed it'll stop at the given frame, otherwise it'll stop in the function which
        called this method.

    :param wait_for_ready_to_run: if True settrace will block until the ready_to_run flag is set to True,
        otherwise, it'll set ready_to_run to True and this function won't block.

        Note that if wait_for_ready_to_run == False, there are no guarantees that the debugger is synchronized
        with what's configured in the client (IDE), the only guarantee is that when leaving this function
        the debugger will be already connected.

    :param dont_trace_start_patterns: if set, then any path that starts with one fo the patterns in the collection
        will not be traced

    :param dont_trace_end_patterns: if set, then any path that ends with one fo the patterns in the collection
        will not be traced

    :param access_token: token to be sent from the client (i.e.: IDE) to the debugger when a connection
        is established (verified by the debugger).

    :param client_access_token: token to be sent from the debugger to the client (i.e.: IDE) when
        a connection is established (verified by the client).

    :param notify_stdin:
        If True sys.stdin will be patched to notify the client when a message is requested
        from the IDE. This is done so that when reading the stdin the client is notified.
        Clients may need this to know when something that is being written should be interpreted
        as an input to the process or as a command to be evaluated.
        Note that parallel-python has issues with this (because it tries to assert that sys.stdin
        is of a given type instead of just checking that it has what it needs).

    :param protocol:
        When using in Eclipse the protocol should not be passed, but when used in VSCode
        or some other IDE/editor that accepts the Debug Adapter Protocol then 'dap' should
        be passed.
    """
    if protocol and protocol.lower() == "dap":
        pydevd_defaults.PydevdCustomization.DEFAULT_PROTOCOL = pydevd_constants.HTTP_JSON_PROTOCOL

    stdout_to_server = stdout_to_server or kwargs.get("stdoutToServer", False)  # Backward compatibility
    stderr_to_server = stderr_to_server or kwargs.get("stderrToServer", False)  # Backward compatibility

    # Internal use (may be used to set the setup info directly for subprocesess).
    __setup_holder__ = kwargs.get("__setup_holder__")

    with _set_trace_lock:
        _locked_settrace(
            host,
            stdout_to_server,
            stderr_to_server,
            port,
            suspend,
            trace_only_current_thread,
            patch_multiprocessing,
            stop_at_frame,
            block_until_connected,
            wait_for_ready_to_run,
            dont_trace_start_patterns,
            dont_trace_end_patterns,
            access_token,
            client_access_token,
            __setup_holder__=__setup_holder__,
            notify_stdin=notify_stdin,
        )


_set_trace_lock = ForkSafeLock()


def _locked_settrace(
    host,
    stdout_to_server,
    stderr_to_server,
    port,
    suspend,
    trace_only_current_thread,
    patch_multiprocessing,
    stop_at_frame,
    block_until_connected,
    wait_for_ready_to_run,
    dont_trace_start_patterns,
    dont_trace_end_patterns,
    access_token,
    client_access_token,
    __setup_holder__,
    notify_stdin,
):
    if patch_multiprocessing:
        try:
            from _pydev_bundle import pydev_monkey
        except:
            pass
        else:
            pydev_monkey.patch_new_process_functions()

    if host is None:
        from _pydev_bundle import pydev_localhost

        host = pydev_localhost.get_localhost()

    global _global_redirect_stdout_to_server
    global _global_redirect_stderr_to_server

    py_db = get_global_debugger()
    if __setup_holder__:
        SetupHolder.setup = __setup_holder__
    if py_db is None:
        py_db = PyDB()
        pydevd_vm_type.setup_type()

        if SetupHolder.setup is None:
            setup = {
                "client": host,  # dispatch expects client to be set to the host address when server is False
                "server": False,
                "port": int(port),
                "multiprocess": patch_multiprocessing,
                "skip-notify-stdin": not notify_stdin,
            }
            SetupHolder.setup = setup

        if access_token is not None:
            py_db.authentication.access_token = access_token
            SetupHolder.setup["access-token"] = access_token
        if client_access_token is not None:
            py_db.authentication.client_access_token = client_access_token
            SetupHolder.setup["client-access-token"] = client_access_token

        if block_until_connected:
            py_db.connect(host, port)  # Note: connect can raise error.
        else:
            # Create a dummy writer and wait for the real connection.
            py_db.writer = WriterThread(NULL, py_db, terminate_on_socket_close=False)
            py_db.create_wait_for_connection_thread()

        if dont_trace_start_patterns or dont_trace_end_patterns:
            PyDevdAPI().set_dont_trace_start_end_patterns(py_db, dont_trace_start_patterns, dont_trace_end_patterns)

        _global_redirect_stdout_to_server = stdout_to_server
        _global_redirect_stderr_to_server = stderr_to_server

        if _global_redirect_stdout_to_server:
            _init_stdout_redirect()

        if _global_redirect_stderr_to_server:
            _init_stderr_redirect()

        if notify_stdin:
            patch_stdin()

        t = threadingCurrentThread()
        additional_info = set_additional_thread_info(t)

        if not wait_for_ready_to_run:
            py_db.ready_to_run = True

        py_db.wait_for_ready_to_run()
        py_db.start_auxiliary_daemon_threads()

        try:
            if INTERACTIVE_MODE_AVAILABLE:
                py_db.init_gui_support()
        except:
            pydev_log.exception("Matplotlib support in debugger failed")

        if trace_only_current_thread:
            py_db.enable_tracing()
        else:
            # Trace future threads.
            py_db.patch_threads()

            py_db.enable_tracing(py_db.trace_dispatch, apply_to_all_threads=True)

            # As this is the first connection, also set tracing for any untraced threads
            py_db.set_tracing_for_untraced_contexts()

        py_db.set_trace_for_frame_and_parents(t.ident, get_frame().f_back)

        with CustomFramesContainer.custom_frames_lock:  # @UndefinedVariable
            for _frameId, custom_frame in CustomFramesContainer.custom_frames.items():
                py_db.set_trace_for_frame_and_parents(None, custom_frame.frame)

    else:
        # ok, we're already in debug mode, with all set, so, let's just set the break
        if access_token is not None:
            py_db.authentication.access_token = access_token
        if client_access_token is not None:
            py_db.authentication.client_access_token = client_access_token

        t = threadingCurrentThread()
        py_db.set_trace_for_frame_and_parents(t.ident, get_frame().f_back)
        additional_info = set_additional_thread_info(t)

        if trace_only_current_thread:
            py_db.enable_tracing()
        else:
            # Trace future threads.
            py_db.patch_threads()
            py_db.enable_tracing(py_db.trace_dispatch, apply_to_all_threads=True)

    # Suspend as the last thing after all tracing is in place.
    if suspend:
        additional_info.pydev_original_step_cmd = CMD_SET_BREAK
        if stop_at_frame is not None:
            # If the step was set we have to go to run state and
            # set the proper frame for it to stop.
            additional_info.pydev_state = STATE_RUN
            additional_info.pydev_step_cmd = CMD_STEP_OVER
            additional_info.pydev_step_stop = stop_at_frame
            additional_info.suspend_type = PYTHON_SUSPEND
            additional_info.update_stepping_info()
            if PYDEVD_USE_SYS_MONITORING:
                pydevd_sys_monitoring.update_monitor_events(suspend_requested=True)
                py_db.set_trace_for_frame_and_parents(t.ident, stop_at_frame)
        else:
            # Ask to break as soon as possible.
            py_db.set_suspend(t, CMD_SET_BREAK, suspend_requested=True)
            py_db.set_trace_for_frame_and_parents(t.ident, get_frame().f_back)

        if PYDEVD_USE_SYS_MONITORING:
            pydevd_sys_monitoring.restart_events()


def stoptrace():
    pydev_log.debug("pydevd.stoptrace()")
    pydevd_tracing.restore_sys_set_trace_func()
    if PYDEVD_USE_SYS_MONITORING:
        pydevd_sys_monitoring.stop_monitoring(all_threads=True)
    else:
        sys.settrace(None)
        try:
            # not available in jython!
            threading.settrace(None)  # for all future threads
        except:
            pass

    from _pydev_bundle.pydev_monkey import undo_patch_thread_modules

    undo_patch_thread_modules()

    # Either or both standard streams can be closed at this point,
    # in which case flush() will fail.
    try:
        sys.stdout.flush()
    except:
        pass
    try:
        sys.stderr.flush()
    except:
        pass

    py_db = get_global_debugger()

    if py_db is not None:
        py_db.dispose_and_kill_all_pydevd_threads()


class Dispatcher(object):

    def __init__(self):
        self.port = None

    def connect(self, host, port):
        self.host = host
        self.port = port
        self.client = start_client(self.host, self.port)
        self.reader = DispatchReader(self)
        self.reader.pydev_do_not_trace = False  # we run reader in the same thread so we don't want to loose tracing
        self.reader.run()

    def close(self):
        try:
            self.reader.do_kill_pydev_thread()
        except:
            pass


class DispatchReader(ReaderThread):

    def __init__(self, dispatcher):
        self.dispatcher = dispatcher

        ReaderThread.__init__(
            self,
            get_global_debugger(),
            self.dispatcher.client,
            PyDevJsonCommandProcessor=PyDevJsonCommandProcessor,
            process_net_command=process_net_command,
        )

    @overrides(ReaderThread._on_run)
    def _on_run(self):
        dummy_thread = threading.current_thread()
        dummy_thread.is_pydev_daemon_thread = False
        return ReaderThread._on_run(self)

    @overrides(PyDBDaemonThread.do_kill_pydev_thread)
    def do_kill_pydev_thread(self):
        if not self._kill_received:
            ReaderThread.do_kill_pydev_thread(self)
            try:
                self.sock.shutdown(SHUT_RDWR)
            except:
                pass
            try:
                self.sock.close()
            except:
                pass

    def process_command(self, cmd_id, seq, text):
        if cmd_id == 99:
            self.dispatcher.port = int(text)
            self._kill_received = True


DISPATCH_APPROACH_NEW_CONNECTION = 1  # Used by PyDev
DISPATCH_APPROACH_EXISTING_CONNECTION = 2  # Used by PyCharm
DISPATCH_APPROACH = DISPATCH_APPROACH_NEW_CONNECTION


def dispatch():
    setup = SetupHolder.setup
    host = setup["client"]
    port = setup["port"]
    if DISPATCH_APPROACH == DISPATCH_APPROACH_EXISTING_CONNECTION:
        dispatcher = Dispatcher()
        try:
            dispatcher.connect(host, port)
            port = dispatcher.port
        finally:
            dispatcher.close()
    return host, port


def settrace_forked(setup_tracing=True):
    """
    When creating a fork from a process in the debugger, we need to reset the whole debugger environment!
    """
    from _pydevd_bundle.pydevd_constants import GlobalDebuggerHolder

    py_db = GlobalDebuggerHolder.global_dbg
    if py_db is not None:
        py_db.created_pydb_daemon_threads = {}  # Just making sure we won't touch those (paused) threads.
        py_db = None

    GlobalDebuggerHolder.global_dbg = None
    threading.current_thread().additional_info = None

    # Make sure that we keep the same access tokens for subprocesses started through fork.
    setup = SetupHolder.setup
    if setup is None:
        setup = {}
    else:
        # i.e.: Get the ppid at this point as it just changed.
        # If we later do an exec() it should remain the same ppid.
        setup[pydevd_constants.ARGUMENT_PPID] = PyDevdAPI().get_ppid()
    access_token = setup.get("access-token")
    client_access_token = setup.get("client-access-token")

    if setup_tracing:
        from _pydevd_frame_eval.pydevd_frame_eval_main import clear_thread_local_info

        host, port = dispatch()

    import pydevd_tracing

    pydevd_tracing.restore_sys_set_trace_func()

    if setup_tracing:
        if port is not None:
            custom_frames_container_init()

            if clear_thread_local_info is not None:
                clear_thread_local_info()

            settrace(
                host,
                port=port,
                suspend=False,
                trace_only_current_thread=False,
                overwrite_prev_trace=True,
                patch_multiprocessing=True,
                access_token=access_token,
                client_access_token=client_access_token,
            )


@contextmanager
def skip_subprocess_arg_patch():
    """
    May be used to skip the monkey-patching that pydevd does to
    skip changing arguments to embed the debugger into child processes.

    i.e.:

    with pydevd.skip_subprocess_arg_patch():
        subprocess.call(...)
    """
    from _pydev_bundle import pydev_monkey

    with pydev_monkey.skip_subprocess_arg_patch():
        yield


def add_dont_terminate_child_pid(pid):
    """
    May be used to ask pydevd to skip the termination of some process
    when it's asked to terminate (debug adapter protocol only).

    :param int pid:
        The pid to be ignored.

    i.e.:

    process = subprocess.Popen(...)
    pydevd.add_dont_terminate_child_pid(process.pid)
    """
    py_db = get_global_debugger()
    if py_db is not None:
        py_db.dont_terminate_child_pids.add(pid)


class SetupHolder:
    setup = None


def apply_debugger_options(setup_options):
    """

    :type setup_options: dict[str, bool]
    """
    default_options = {"save-signatures": False, "qt-support": ""}
    default_options.update(setup_options)
    setup_options = default_options

    debugger = get_global_debugger()
    if setup_options["save-signatures"]:
        if pydevd_vm_type.get_vm_type() == pydevd_vm_type.PydevdVmType.JYTHON:
            sys.stderr.write("Collecting run-time type information is not supported for Jython\n")
        else:
            # Only import it if we're going to use it!
            from _pydevd_bundle.pydevd_signature import SignatureFactory

            debugger.signature_factory = SignatureFactory()

    if setup_options["qt-support"]:
        enable_qt_support(setup_options["qt-support"])


@call_only_once
def patch_stdin():
    _internal_patch_stdin(None, sys, getpass_mod)


def _internal_patch_stdin(py_db=None, sys=None, getpass_mod=None):
    """
    Note: don't use this function directly, use `patch_stdin()` instead.
    (this function is only meant to be used on test-cases to avoid patching the actual globals).
    """
    # Patch stdin so that we notify when readline() is called.
    original_sys_stdin = sys.stdin
    debug_console_stdin = DebugConsoleStdIn(py_db, original_sys_stdin)
    sys.stdin = debug_console_stdin

    _original_getpass = getpass_mod.getpass

    @functools.wraps(_original_getpass)
    def getpass(*args, **kwargs):
        with DebugConsoleStdIn.notify_input_requested(debug_console_stdin):
            try:
                curr_stdin = sys.stdin
                if curr_stdin is debug_console_stdin:
                    sys.stdin = original_sys_stdin
                return _original_getpass(*args, **kwargs)
            finally:
                sys.stdin = curr_stdin

    getpass_mod.getpass = getpass

# Dispatch on_debugger_modules_loaded here, after all primary py_db modules are loaded


for handler in pydevd_extension_utils.extensions_of_type(DebuggerEventHandler):
    handler.on_debugger_modules_loaded(debugger_version=__version__)


def log_to(log_file: str, log_level=3) -> None:
    """
    In pydevd it's possible to log by setting the following environment variables:

    PYDEVD_DEBUG=1 (sets the default log level to 3 along with other default options)
    PYDEVD_DEBUG_FILE=</path/to/file.log>

    Note that the file will have the pid of the process added to it (so, logging to
    /path/to/file.log would actually start logging to /path/to/file.<pid>.log -- if subprocesses are
    logged, each new subprocess will have the logging set to its own pid).

    Usually setting the environment variable is preferred as it'd log information while
    pydevd is still doing its imports and not just after this method is called, but on
    cases where this is hard to do this function may be called to set the tracing after
    pydevd itself is already imported.
    """
    pydev_log.log_to(log_file, log_level)


def _log_initial_info():
    pydev_log.debug("Initial arguments: %s", (sys.argv,))
    pydev_log.debug("Current pid: %s", os.getpid())
    pydev_log.debug("Using cython: %s", USING_CYTHON)
    pydev_log.debug("Using frame eval: %s", USING_FRAME_EVAL)
    pydev_log.debug("Using gevent mode: %s / imported gevent module support: %s", SUPPORT_GEVENT, bool(pydevd_gevent_integration))


def config(protocol="", debug_mode="", preimport=""):
    pydev_log.debug("Config: protocol: %s, debug_mode: %s, preimport: %s", protocol, debug_mode, preimport)
    PydevdCustomization.DEFAULT_PROTOCOL = protocol
    PydevdCustomization.DEBUG_MODE = debug_mode
    PydevdCustomization.PREIMPORT = preimport


# =======================================================================================================================
# main
# =======================================================================================================================
def main():
    # parse the command line. --file is our last argument that is required
    _log_initial_info()
    original_argv = sys.argv[:]
    try:
        from _pydevd_bundle.pydevd_command_line_handling import process_command_line

        setup = process_command_line(sys.argv)
        SetupHolder.setup = setup
    except ValueError:
        pydev_log.exception()
        usage(1)

    preimport = setup.get("preimport")
    if preimport:
        pydevd_defaults.PydevdCustomization.PREIMPORT = preimport

    debug_mode = setup.get("debug-mode")
    if debug_mode:
        pydevd_defaults.PydevdCustomization.DEBUG_MODE = debug_mode

    log_trace_level = setup.get("log-level")

    # Note: the logging info could've been changed (this would happen if this is a
    # subprocess and the value in the environment variable does not match the value in the
    # argument because the user used `pydevd.log_to` instead of supplying the environment
    # variable). If this is the case, update the logging info and re-log some information
    # in the new target.
    new_debug_file = setup.get("log-file")
    if new_debug_file and DebugInfoHolder.PYDEVD_DEBUG_FILE != new_debug_file:
        # The debug file can't be set directly, we need to use log_to() so that the a
        # new stream is actually created for the new file.
        log_to(new_debug_file, log_trace_level if log_trace_level is not None else 3)
        _log_initial_info()  # The redirection info just changed, log it again.

    elif log_trace_level is not None:
        # The log file was not specified
        DebugInfoHolder.DEBUG_TRACE_LEVEL = log_trace_level
    pydev_log.debug("Original sys.argv: %s", original_argv)

    if setup["print-in-debugger-startup"]:
        try:
            pid = " (pid: %s)" % os.getpid()
        except:
            pid = ""
        sys.stderr.write("pydev debugger: starting%s\n" % pid)

    pydev_log.debug("Executing file %s", setup["file"])
    pydev_log.debug("arguments: %s", (sys.argv,))

    pydevd_vm_type.setup_type(setup.get("vm_type", None))

    port = setup["port"]
    host = setup["client"]
    f = setup["file"]
    fix_app_engine_debug = False

    debugger = get_global_debugger()
    if debugger is None:
        debugger = PyDB()

    try:
        from _pydev_bundle import pydev_monkey
    except:
        pass  # Not usable on jython 2.1
    else:
        if setup["multiprocess"]:  # PyDev
            pydev_monkey.patch_new_process_functions()

        elif setup["multiproc"]:  # PyCharm
            pydev_log.debug("Started in multiproc mode\n")
            global DISPATCH_APPROACH
            DISPATCH_APPROACH = DISPATCH_APPROACH_EXISTING_CONNECTION

            dispatcher = Dispatcher()
            try:
                dispatcher.connect(host, port)
                if dispatcher.port is not None:
                    port = dispatcher.port
                    pydev_log.debug("Received port %d\n", port)
                    pydev_log.info("pydev debugger: process %d is connecting\n" % os.getpid())

                    try:
                        pydev_monkey.patch_new_process_functions()
                    except:
                        pydev_log.exception("Error patching process functions.")
                else:
                    pydev_log.critical("pydev debugger: couldn't get port for new debug process.")
            finally:
                dispatcher.close()
        else:
            try:
                pydev_monkey.patch_new_process_functions_with_warning()
            except:
                pydev_log.exception("Error patching process functions.")

            # Only do this patching if we're not running with multiprocess turned on.
            if f.find("dev_appserver.py") != -1:
                if os.path.basename(f).startswith("dev_appserver.py"):
                    appserver_dir = os.path.dirname(f)
                    version_file = os.path.join(appserver_dir, "VERSION")
                    if os.path.exists(version_file):
                        try:
                            stream = open(version_file, "r")
                            try:
                                for line in stream.read().splitlines():
                                    line = line.strip()
                                    if line.startswith("release:"):
                                        line = line[8:].strip()
                                        version = line.replace('"', "")
                                        version = version.split(".")
                                        if int(version[0]) > 1:
                                            fix_app_engine_debug = True

                                        elif int(version[0]) == 1:
                                            if int(version[1]) >= 7:
                                                # Only fix from 1.7 onwards
                                                fix_app_engine_debug = True
                                        break
                            finally:
                                stream.close()
                        except:
                            pydev_log.exception()

    try:
        # In the default run (i.e.: run directly on debug mode), we try to patch stackless as soon as possible
        # on a run where we have a remote debug, we may have to be more careful because patching stackless means
        # that if the user already had a stackless.set_schedule_callback installed, he'd loose it and would need
        # to call it again (because stackless provides no way of getting the last function which was registered
        # in set_schedule_callback).
        #
        # So, ideally, if there's an application using stackless and the application wants to use the remote debugger
        # and benefit from stackless debugging, the application itself must call:
        #
        # import pydevd_stackless
        # pydevd_stackless.patch_stackless()
        #
        # itself to be able to benefit from seeing the tasklets created before the remote debugger is attached.
        from _pydevd_bundle import pydevd_stackless

        pydevd_stackless.patch_stackless()
    except:
        # It's ok not having stackless there...
        try:
            if hasattr(sys, "exc_clear"):
                sys.exc_clear()  # the exception information should be cleaned in Python 2
        except:
            pass

    is_module = setup["module"]
    if not setup["skip-notify-stdin"]:
        patch_stdin()

    if setup[pydevd_constants.ARGUMENT_JSON_PROTOCOL]:
        PyDevdAPI().set_protocol(debugger, 0, JSON_PROTOCOL)

    elif setup[pydevd_constants.ARGUMENT_HTTP_JSON_PROTOCOL]:
        PyDevdAPI().set_protocol(debugger, 0, HTTP_JSON_PROTOCOL)

    elif setup[pydevd_constants.ARGUMENT_HTTP_PROTOCOL]:
        PyDevdAPI().set_protocol(debugger, 0, pydevd_constants.HTTP_PROTOCOL)

    elif setup[pydevd_constants.ARGUMENT_QUOTED_LINE_PROTOCOL]:
        PyDevdAPI().set_protocol(debugger, 0, pydevd_constants.QUOTED_LINE_PROTOCOL)

    access_token = setup["access-token"]
    if access_token:
        debugger.authentication.access_token = access_token

    client_access_token = setup["client-access-token"]
    if client_access_token:
        debugger.authentication.client_access_token = client_access_token

    if fix_app_engine_debug:
        sys.stderr.write("pydev debugger: google app engine integration enabled\n")
        curr_dir = os.path.dirname(__file__)
        app_engine_startup_file = os.path.join(curr_dir, "pydev_app_engine_debug_startup.py")

        sys.argv.insert(1, "--python_startup_script=" + app_engine_startup_file)
        import json

        setup["pydevd"] = __file__
        sys.argv.insert(
            2,
            "--python_startup_args=%s" % json.dumps(setup),
        )
        sys.argv.insert(3, "--automatic_restart=no")
        sys.argv.insert(4, "--max_module_instances=1")

        # Run the dev_appserver
        debugger.run(setup["file"], None, None, is_module, set_trace=False)
    else:
        if setup["save-threading"]:
            debugger.thread_analyser = ThreadingLogger()
        if setup["save-asyncio"]:
            debugger.asyncio_analyser = AsyncioLogger()

        apply_debugger_options(setup)

        try:
            debugger.connect(host, port)
        except:
            sys.stderr.write("Could not connect to %s: %s\n" % (host, port))
            pydev_log.exception()
            sys.exit(1)

        globals = debugger.run(setup["file"], None, None, is_module)

        if setup["cmd-line"]:
            debugger.wait_for_commands(globals)


try:
    # Remove the entry we added: it should no longer be needed as
    # what we need should've been imported already
    if sys.path[:1] == [this_dir]:
        sys.path.remove(this_dir)
except Exception:
    pass

if __name__ == "__main__":
    main()