
# === NexusCore/openenv\Lib\site-packages\matplotlib\axes\_axes.py ===
import functools
import itertools
import logging
import math
from numbers import Integral, Number, Real

import re
import numpy as np

import matplotlib as mpl
import matplotlib.category  # Register category unit converter as side effect.
import matplotlib.cbook as cbook
import matplotlib.collections as mcoll
import matplotlib.colorizer as mcolorizer
import matplotlib.colors as mcolors
import matplotlib.contour as mcontour
import matplotlib.dates  # noqa: F401, Register date unit converter as side effect.
import matplotlib.image as mimage
import matplotlib.inset as minset
import matplotlib.legend as mlegend
import matplotlib.lines as mlines
import matplotlib.markers as mmarkers
import matplotlib.mlab as mlab
import matplotlib.patches as mpatches
import matplotlib.path as mpath
import matplotlib.quiver as mquiver
import matplotlib.stackplot as mstack
import matplotlib.streamplot as mstream
import matplotlib.table as mtable
import matplotlib.text as mtext
import matplotlib.ticker as mticker
import matplotlib.transforms as mtransforms
import matplotlib.tri as mtri
import matplotlib.units as munits
from matplotlib import _api, _docstring, _preprocess_data
from matplotlib.axes._base import (
    _AxesBase, _TransformedBoundsLocator, _process_plot_format)
from matplotlib.axes._secondary_axes import SecondaryAxis
from matplotlib.container import BarContainer, ErrorbarContainer, StemContainer
from matplotlib.transforms import _ScaledRotation

_log = logging.getLogger(__name__)


# The axes module contains all the wrappers to plotting functions.
# All the other methods should go in the _AxesBase class.


def _make_axes_method(func):
    """
    Patch the qualname for functions that are directly added to Axes.

    Some Axes functionality is defined in functions in other submodules.
    These are simply added as attributes to Axes. As a result, their
    ``__qualname__`` is e.g. only "table" and not "Axes.table". This
    function fixes that.

    Note that the function itself is patched, so that
    ``matplotlib.table.table.__qualname__` will also show "Axes.table".
    However, since these functions are not intended to be standalone,
    this is bearable.
    """
    func.__qualname__ = f"Axes.{func.__name__}"
    return func


@_docstring.interpd
class Axes(_AxesBase):
    """
    An Axes object encapsulates all the elements of an individual (sub-)plot in
    a figure.

    It contains most of the (sub-)plot elements: `~.axis.Axis`,
    `~.axis.Tick`, `~.lines.Line2D`, `~.text.Text`, `~.patches.Polygon`, etc.,
    and sets the coordinate system.

    Like all visible elements in a figure, Axes is an `.Artist` subclass.

    The `Axes` instance supports callbacks through a callbacks attribute which
    is a `~.cbook.CallbackRegistry` instance.  The events you can connect to
    are 'xlim_changed' and 'ylim_changed' and the callback will be called with
    func(*ax*) where *ax* is the `Axes` instance.

    .. note::

        As a user, you do not instantiate Axes directly, but use Axes creation
        methods instead; e.g. from `.pyplot` or `.Figure`:
        `~.pyplot.subplots`, `~.pyplot.subplot_mosaic` or `.Figure.add_axes`.

    """
    ### Labelling, legend and texts

    def get_title(self, loc="center"):
        """
        Get an Axes title.

        Get one of the three available Axes titles. The available titles
        are positioned above the Axes in the center, flush with the left
        edge, and flush with the right edge.

        Parameters
        ----------
        loc : {'center', 'left', 'right'}, str, default: 'center'
            Which title to return.

        Returns
        -------
        str
            The title text string.

        """
        titles = {'left': self._left_title,
                  'center': self.title,
                  'right': self._right_title}
        title = _api.check_getitem(titles, loc=loc.lower())
        return title.get_text()

    def set_title(self, label, fontdict=None, loc=None, pad=None, *, y=None,
                  **kwargs):
        """
        Set a title for the Axes.

        Set one of the three available Axes titles. The available titles
        are positioned above the Axes in the center, flush with the left
        edge, and flush with the right edge.

        Parameters
        ----------
        label : str
            Text to use for the title

        fontdict : dict

            .. admonition:: Discouraged

               The use of *fontdict* is discouraged. Parameters should be passed as
               individual keyword arguments or using dictionary-unpacking
               ``set_title(..., **fontdict)``.

            A dictionary controlling the appearance of the title text,
            the default *fontdict* is::

               {'fontsize': rcParams['axes.titlesize'],
                'fontweight': rcParams['axes.titleweight'],
                'color': rcParams['axes.titlecolor'],
                'verticalalignment': 'baseline',
                'horizontalalignment': loc}

        loc : {'center', 'left', 'right'}, default: :rc:`axes.titlelocation`
            Which title to set.

        y : float, default: :rc:`axes.titley`
            Vertical Axes location for the title (1.0 is the top).  If
            None (the default) and :rc:`axes.titley` is also None, y is
            determined automatically to avoid decorators on the Axes.

        pad : float, default: :rc:`axes.titlepad`
            The offset of the title from the top of the Axes, in points.

        Returns
        -------
        `.Text`
            The matplotlib text instance representing the title

        Other Parameters
        ----------------
        **kwargs : `~matplotlib.text.Text` properties
            Other keyword arguments are text properties, see `.Text` for a list
            of valid text properties.
        """
        if loc is None:
            loc = mpl.rcParams['axes.titlelocation']

        if y is None:
            y = mpl.rcParams['axes.titley']
        if y is None:
            y = 1.0
        else:
            self._autotitlepos = False
        kwargs['y'] = y

        titles = {'left': self._left_title,
                  'center': self.title,
                  'right': self._right_title}
        title = _api.check_getitem(titles, loc=loc.lower())
        default = {
            'fontsize': mpl.rcParams['axes.titlesize'],
            'fontweight': mpl.rcParams['axes.titleweight'],
            'verticalalignment': 'baseline',
            'horizontalalignment': loc.lower()}
        titlecolor = mpl.rcParams['axes.titlecolor']
        if not cbook._str_lower_equal(titlecolor, 'auto'):
            default["color"] = titlecolor
        if pad is None:
            pad = mpl.rcParams['axes.titlepad']
        self._set_title_offset_trans(float(pad))
        title.set_text(label)
        title.update(default)
        if fontdict is not None:
            title.update(fontdict)
        title._internal_update(kwargs)
        return title

    def get_legend_handles_labels(self, legend_handler_map=None):
        """
        Return handles and labels for legend

        ``ax.legend()`` is equivalent to ::

          h, l = ax.get_legend_handles_labels()
          ax.legend(h, l)
        """
        # pass through to legend.
        handles, labels = mlegend._get_legend_handles_labels(
            [self], legend_handler_map)
        return handles, labels

    @_docstring.interpd
    def legend(self, *args, **kwargs):
        """
        Place a legend on the Axes.

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
            ax.legend()

        or::

            line, = ax.plot([1, 2, 3])
            line.set_label('Label via method')
            ax.legend()

        .. note::
            Specific artists can be excluded from the automatic legend element
            selection by using a label starting with an underscore, "_".
            A string starting with an underscore is the default label for all
            artists, so calling `.Axes.legend` without any arguments and
            without setting the labels manually will result in a ``UserWarning``
            and an empty legend being drawn.


        **2. Explicitly listing the artists and labels in the legend**

        For full control of which artists have a legend entry, it is possible
        to pass an iterable of legend artists followed by an iterable of
        legend labels respectively::

            ax.legend([line1, line2, line3], ['label1', 'label2', 'label3'])


        **3. Explicitly listing the artists in the legend**

        This is similar to 2, but the labels are taken from the artists'
        label properties. Example::

            line1, = ax.plot([1, 2, 3], label='label1')
            line2, = ax.plot([1, 2, 3], label='label2')
            ax.legend(handles=[line1, line2])


        **4. Labeling existing plot elements**

        .. admonition:: Discouraged

            This call signature is discouraged, because the relation between
            plot elements and labels is only implicit by their order and can
            easily be mixed up.

        To make a legend for all artists on an Axes, call this function with
        an iterable of strings, one for each legend item. For example::

            ax.plot([1, 2, 3])
            ax.plot([5, 6, 7])
            ax.legend(['First line', 'Second line'])


        Parameters
        ----------
        handles : list of (`.Artist` or tuple of `.Artist`), optional
            A list of Artists (lines, patches) to be added to the legend.
            Use this together with *labels*, if you need full control on what
            is shown in the legend and the automatic mechanism described above
            is not sufficient.

            The length of handles and labels should be the same in this
            case. If they are not, they are truncated to the smaller length.

            If an entry contains a tuple, then the legend handler for all Artists in the
            tuple will be placed alongside a single label.

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
        %(_legend_kw_axes)s

        See Also
        --------
        .Figure.legend

        Notes
        -----
        Some artists are not supported by this function.  See
        :ref:`legend_guide` for details.

        Examples
        --------
        .. plot:: gallery/text_labels_and_annotations/legend.py
        """
        handles, labels, kwargs = mlegend._parse_legend_args([self], *args, **kwargs)
        self.legend_ = mlegend.Legend(self, handles, labels, **kwargs)
        self.legend_._remove_method = self._remove_legend
        return self.legend_

    def _remove_legend(self, legend):
        self.legend_ = None

    def inset_axes(self, bounds, *, transform=None, zorder=5, **kwargs):
        """
        Add a child inset Axes to this existing Axes.


        Parameters
        ----------
        bounds : [x0, y0, width, height]
            Lower-left corner of inset Axes, and its width and height.

        transform : `.Transform`
            Defaults to `ax.transAxes`, i.e. the units of *rect* are in
            Axes-relative coordinates.

        projection : {None, 'aitoff', 'hammer', 'lambert', 'mollweide', \
'polar', 'rectilinear', str}, optional
            The projection type of the inset `~.axes.Axes`. *str* is the name
            of a custom projection, see `~matplotlib.projections`. The default
            None results in a 'rectilinear' projection.

        polar : bool, default: False
            If True, equivalent to projection='polar'.

        axes_class : subclass type of `~.axes.Axes`, optional
            The `.axes.Axes` subclass that is instantiated.  This parameter
            is incompatible with *projection* and *polar*.  See
            :ref:`axisartist_users-guide-index` for examples.

        zorder : number
            Defaults to 5 (same as `.Axes.legend`).  Adjust higher or lower
            to change whether it is above or below data plotted on the
            parent Axes.

        **kwargs
            Other keyword arguments are passed on to the inset Axes class.

        Returns
        -------
        ax
            The created `~.axes.Axes` instance.

        Examples
        --------
        This example makes two inset Axes, the first is in Axes-relative
        coordinates, and the second in data-coordinates::

            fig, ax = plt.subplots()
            ax.plot(range(10))
            axin1 = ax.inset_axes([0.8, 0.1, 0.15, 0.15])
            axin2 = ax.inset_axes(
                    [5, 7, 2.3, 2.3], transform=ax.transData)

        """
        if transform is None:
            transform = self.transAxes
        kwargs.setdefault('label', 'inset_axes')

        # This puts the rectangle into figure-relative coordinates.
        inset_locator = _TransformedBoundsLocator(bounds, transform)
        bounds = inset_locator(self, None).bounds
        fig = self.get_figure(root=False)
        projection_class, pkw = fig._process_projection_requirements(**kwargs)
        inset_ax = projection_class(fig, bounds, zorder=zorder, **pkw)

        # this locator lets the axes move if in data coordinates.
        # it gets called in `ax.apply_aspect() (of all places)
        inset_ax.set_axes_locator(inset_locator)

        self.add_child_axes(inset_ax)

        return inset_ax

    @_docstring.interpd
    def indicate_inset(self, bounds=None, inset_ax=None, *, transform=None,
                       facecolor='none', edgecolor='0.5', alpha=0.5,
                       zorder=None, **kwargs):
        """
        Add an inset indicator to the Axes.  This is a rectangle on the plot
        at the position indicated by *bounds* that optionally has lines that
        connect the rectangle to an inset Axes (`.Axes.inset_axes`).

        Warnings
        --------
        This method is experimental as of 3.0, and the API may change.

        Parameters
        ----------
        bounds : [x0, y0, width, height], optional
            Lower-left corner of rectangle to be marked, and its width
            and height.  If not set, the bounds will be calculated from the
            data limits of *inset_ax*, which must be supplied.

        inset_ax : `.Axes`, optional
            An optional inset Axes to draw connecting lines to.  Two lines are
            drawn connecting the indicator box to the inset Axes on corners
            chosen so as to not overlap with the indicator box.

        transform : `.Transform`
            Transform for the rectangle coordinates. Defaults to
            ``ax.transAxes``, i.e. the units of *rect* are in Axes-relative
            coordinates.

        facecolor : :mpltype:`color`, default: 'none'
            Facecolor of the rectangle.

        edgecolor : :mpltype:`color`, default: '0.5'
            Color of the rectangle and color of the connecting lines.

        alpha : float or None, default: 0.5
            Transparency of the rectangle and connector lines.  If not
            ``None``, this overrides any alpha value included in the
            *facecolor* and *edgecolor* parameters.

        zorder : float, default: 4.99
            Drawing order of the rectangle and connector lines.  The default,
            4.99, is just below the default level of inset Axes.

        **kwargs
            Other keyword arguments are passed on to the `.Rectangle` patch:

            %(Rectangle:kwdoc)s

        Returns
        -------
        inset_indicator : `.inset.InsetIndicator`
            An artist which contains

            inset_indicator.rectangle : `.Rectangle`
                The indicator frame.

            inset_indicator.connectors : 4-tuple of `.patches.ConnectionPatch`
                The four connector lines connecting to (lower_left, upper_left,
                lower_right upper_right) corners of *inset_ax*. Two lines are
                set with visibility to *False*,  but the user can set the
                visibility to True if the automatic choice is not deemed correct.

            .. versionchanged:: 3.10
                Previously the rectangle and connectors tuple were returned.
        """
        # to make the Axes connectors work, we need to apply the aspect to
        # the parent Axes.
        self.apply_aspect()

        if transform is None:
            transform = self.transData
        kwargs.setdefault('label', '_indicate_inset')

        indicator_patch = minset.InsetIndicator(
            bounds, inset_ax=inset_ax,
            facecolor=facecolor, edgecolor=edgecolor, alpha=alpha,
            zorder=zorder, transform=transform, **kwargs)
        self.add_artist(indicator_patch)

        return indicator_patch

    def indicate_inset_zoom(self, inset_ax, **kwargs):
        """
        Add an inset indicator rectangle to the Axes based on the axis
        limits for an *inset_ax* and draw connectors between *inset_ax*
        and the rectangle.

        Warnings
        --------
        This method is experimental as of 3.0, and the API may change.

        Parameters
        ----------
        inset_ax : `.Axes`
            Inset Axes to draw connecting lines to.  Two lines are
            drawn connecting the indicator box to the inset Axes on corners
            chosen so as to not overlap with the indicator box.

        **kwargs
            Other keyword arguments are passed on to `.Axes.indicate_inset`

        Returns
        -------
        inset_indicator : `.inset.InsetIndicator`
            An artist which contains

            inset_indicator.rectangle : `.Rectangle`
                The indicator frame.

            inset_indicator.connectors : 4-tuple of `.patches.ConnectionPatch`
                The four connector lines connecting to (lower_left, upper_left,
                lower_right upper_right) corners of *inset_ax*. Two lines are
                set with visibility to *False*,  but the user can set the
                visibility to True if the automatic choice is not deemed correct.

            .. versionchanged:: 3.10
                Previously the rectangle and connectors tuple were returned.
        """

        return self.indicate_inset(None, inset_ax, **kwargs)

    @_docstring.interpd
    def secondary_xaxis(self, location, functions=None, *, transform=None, **kwargs):
        """
        Add a second x-axis to this `~.axes.Axes`.

        For example if we want to have a second scale for the data plotted on
        the xaxis.

        %(_secax_docstring)s

        Examples
        --------
        The main axis shows frequency, and the secondary axis shows period.

        .. plot::

            fig, ax = plt.subplots()
            ax.loglog(range(1, 360, 5), range(1, 360, 5))
            ax.set_xlabel('frequency [Hz]')

            def invert(x):
                # 1/x with special treatment of x == 0
                x = np.array(x).astype(float)
                near_zero = np.isclose(x, 0)
                x[near_zero] = np.inf
                x[~near_zero] = 1 / x[~near_zero]
                return x

            # the inverse of 1/x is itself
            secax = ax.secondary_xaxis('top', functions=(invert, invert))
            secax.set_xlabel('Period [s]')
            plt.show()

        To add a secondary axis relative to your data, you can pass a transform
        to the new axis.

        .. plot::

            fig, ax = plt.subplots()
            ax.plot(range(0, 5), range(-1, 4))

            # Pass 'ax.transData' as a transform to place the axis
            # relative to your data at y=0
            secax = ax.secondary_xaxis(0, transform=ax.transData)
        """
        if not (location in ['top', 'bottom'] or isinstance(location, Real)):
            raise ValueError('secondary_xaxis location must be either '
                             'a float or "top"/"bottom"')

        secondary_ax = SecondaryAxis(self, 'x', location, functions,
                                     transform, **kwargs)
        self.add_child_axes(secondary_ax)
        return secondary_ax

    @_docstring.interpd
    def secondary_yaxis(self, location, functions=None, *, transform=None, **kwargs):
        """
        Add a second y-axis to this `~.axes.Axes`.

        For example if we want to have a second scale for the data plotted on
        the yaxis.

        %(_secax_docstring)s

        Examples
        --------
        Add a secondary Axes that converts from radians to degrees

        .. plot::

            fig, ax = plt.subplots()
            ax.plot(range(1, 360, 5), range(1, 360, 5))
            ax.set_ylabel('degrees')
            secax = ax.secondary_yaxis('right', functions=(np.deg2rad,
                                                           np.rad2deg))
            secax.set_ylabel('radians')

        To add a secondary axis relative to your data, you can pass a transform
        to the new axis.

        .. plot::

            fig, ax = plt.subplots()
            ax.plot(range(0, 5), range(-1, 4))

            # Pass 'ax.transData' as a transform to place the axis
            # relative to your data at x=3
            secax = ax.secondary_yaxis(3, transform=ax.transData)
        """
        if not (location in ['left', 'right'] or isinstance(location, Real)):
            raise ValueError('secondary_yaxis location must be either '
                             'a float or "left"/"right"')

        secondary_ax = SecondaryAxis(self, 'y', location, functions,
                                     transform, **kwargs)
        self.add_child_axes(secondary_ax)
        return secondary_ax

    @_docstring.interpd
    def text(self, x, y, s, fontdict=None, **kwargs):
        """
        Add text to the Axes.

        Add the text *s* to the Axes at location *x*, *y* in data coordinates,
        with a default ``horizontalalignment`` on the ``left`` and
        ``verticalalignment`` at the ``baseline``. See
        :doc:`/gallery/text_labels_and_annotations/text_alignment`.

        Parameters
        ----------
        x, y : float
            The position to place the text. By default, this is in data
            coordinates. The coordinate system can be changed using the
            *transform* parameter.

        s : str
            The text.

        fontdict : dict, default: None

            .. admonition:: Discouraged

               The use of *fontdict* is discouraged. Parameters should be passed as
               individual keyword arguments or using dictionary-unpacking
               ``text(..., **fontdict)``.

            A dictionary to override the default text properties. If fontdict
            is None, the defaults are determined by `.rcParams`.

        Returns
        -------
        `.Text`
            The created `.Text` instance.

        Other Parameters
        ----------------
        **kwargs : `~matplotlib.text.Text` properties.
            Other miscellaneous text parameters.

            %(Text:kwdoc)s

        Examples
        --------
        Individual keyword arguments can be used to override any given
        parameter::

            >>> text(x, y, s, fontsize=12)

        The default transform specifies that text is in data coords,
        alternatively, you can specify text in axis coords ((0, 0) is
        lower-left and (1, 1) is upper-right).  The example below places
        text in the center of the Axes::

            >>> text(0.5, 0.5, 'matplotlib', horizontalalignment='center',
            ...      verticalalignment='center', transform=ax.transAxes)

        You can put a rectangular box around the text instance (e.g., to
        set a background color) by using the keyword *bbox*.  *bbox* is
        a dictionary of `~matplotlib.patches.Rectangle`
        properties.  For example::

            >>> text(x, y, s, bbox=dict(facecolor='red', alpha=0.5))
        """
        effective_kwargs = {
            'verticalalignment': 'baseline',
            'horizontalalignment': 'left',
            'transform': self.transData,
            'clip_on': False,
            **(fontdict if fontdict is not None else {}),
            **kwargs,
        }
        t = mtext.Text(x, y, text=s, **effective_kwargs)
        if t.get_clip_path() is None:
            t.set_clip_path(self.patch)
        self._add_text(t)
        return t

    @_docstring.interpd
    def annotate(self, text, xy, xytext=None, xycoords='data', textcoords=None,
                 arrowprops=None, annotation_clip=None, **kwargs):
        # Signature must match Annotation. This is verified in
        # test_annotate_signature().
        a = mtext.Annotation(text, xy, xytext=xytext, xycoords=xycoords,
                             textcoords=textcoords, arrowprops=arrowprops,
                             annotation_clip=annotation_clip, **kwargs)
        a.set_transform(mtransforms.IdentityTransform())
        if kwargs.get('clip_on', False) and a.get_clip_path() is None:
            a.set_clip_path(self.patch)
        self._add_text(a)
        return a
    annotate.__doc__ = mtext.Annotation.__init__.__doc__
    #### Lines and spans

    @_docstring.interpd
    def axhline(self, y=0, xmin=0, xmax=1, **kwargs):
        """
        Add a horizontal line spanning the whole or fraction of the Axes.

        Note: If you want to set x-limits in data coordinates, use
        `~.Axes.hlines` instead.

        Parameters
        ----------
        y : float, default: 0
            y position in :ref:`data coordinates <coordinate-systems>`.

        xmin : float, default: 0
            The start x-position in :ref:`axes coordinates <coordinate-systems>`.
            Should be between 0 and 1, 0 being the far left of the plot,
            1 the far right of the plot.

        xmax : float, default: 1
            The end x-position in :ref:`axes coordinates <coordinate-systems>`.
            Should be between 0 and 1, 0 being the far left of the plot,
            1 the far right of the plot.

        Returns
        -------
        `~matplotlib.lines.Line2D`
            A `.Line2D` specified via two points ``(xmin, y)``, ``(xmax, y)``.
            Its transform is set such that *x* is in
            :ref:`axes coordinates <coordinate-systems>` and *y* is in
            :ref:`data coordinates <coordinate-systems>`.

            This is still a generic line and the horizontal character is only
            realized through using identical *y* values for both points. Thus,
            if you want to change the *y* value later, you have to provide two
            values ``line.set_ydata([3, 3])``.

        Other Parameters
        ----------------
        **kwargs
            Valid keyword arguments are `.Line2D` properties, except for
            'transform':

            %(Line2D:kwdoc)s

        See Also
        --------
        hlines : Add horizontal lines in data coordinates.
        axhspan : Add a horizontal span (rectangle) across the axis.
        axline : Add a line with an arbitrary slope.

        Examples
        --------
        * draw a thick red hline at 'y' = 0 that spans the xrange::

            >>> axhline(linewidth=4, color='r')

        * draw a default hline at 'y' = 1 that spans the xrange::

            >>> axhline(y=1)

        * draw a default hline at 'y' = .5 that spans the middle half of
          the xrange::

            >>> axhline(y=.5, xmin=0.25, xmax=0.75)
        """
        self._check_no_units([xmin, xmax], ['xmin', 'xmax'])
        if "transform" in kwargs:
            raise ValueError("'transform' is not allowed as a keyword "
                             "argument; axhline generates its own transform.")
        ymin, ymax = self.get_ybound()

        # Strip away the units for comparison with non-unitized bounds.
        yy, = self._process_unit_info([("y", y)], kwargs)
        scaley = (yy < ymin) or (yy > ymax)

        trans = self.get_yaxis_transform(which='grid')
        l = mlines.Line2D([xmin, xmax], [y, y], transform=trans, **kwargs)
        self.add_line(l)
        l.get_path()._interpolation_steps = mpl.axis.GRIDLINE_INTERPOLATION_STEPS
        if scaley:
            self._request_autoscale_view("y")
        return l

    @_docstring.interpd
    def axvline(self, x=0, ymin=0, ymax=1, **kwargs):
        """
        Add a vertical line spanning the whole or fraction of the Axes.

        Note: If you want to set y-limits in data coordinates, use
        `~.Axes.vlines` instead.

        Parameters
        ----------
        x : float, default: 0
            x position in :ref:`data coordinates <coordinate-systems>`.

        ymin : float, default: 0
            The start y-position in :ref:`axes coordinates <coordinate-systems>`.
            Should be between 0 and 1, 0 being the bottom of the plot, 1 the
            top of the plot.

        ymax : float, default: 1
            The end y-position in :ref:`axes coordinates <coordinate-systems>`.
            Should be between 0 and 1, 0 being the bottom of the plot, 1 the
            top of the plot.

        Returns
        -------
        `~matplotlib.lines.Line2D`
            A `.Line2D` specified via two points ``(x, ymin)``, ``(x, ymax)``.
            Its transform is set such that *x* is in
            :ref:`data coordinates <coordinate-systems>` and *y* is in
            :ref:`axes coordinates <coordinate-systems>`.

            This is still a generic line and the vertical character is only
            realized through using identical *x* values for both points. Thus,
            if you want to change the *x* value later, you have to provide two
            values ``line.set_xdata([3, 3])``.

        Other Parameters
        ----------------
        **kwargs
            Valid keyword arguments are `.Line2D` properties, except for
            'transform':

            %(Line2D:kwdoc)s

        See Also
        --------
        vlines : Add vertical lines in data coordinates.
        axvspan : Add a vertical span (rectangle) across the axis.
        axline : Add a line with an arbitrary slope.

        Examples
        --------
        * draw a thick red vline at *x* = 0 that spans the yrange::

            >>> axvline(linewidth=4, color='r')

        * draw a default vline at *x* = 1 that spans the yrange::

            >>> axvline(x=1)

        * draw a default vline at *x* = .5 that spans the middle half of
          the yrange::

            >>> axvline(x=.5, ymin=0.25, ymax=0.75)
        """
        self._check_no_units([ymin, ymax], ['ymin', 'ymax'])
        if "transform" in kwargs:
            raise ValueError("'transform' is not allowed as a keyword "
                             "argument; axvline generates its own transform.")
        xmin, xmax = self.get_xbound()

        # Strip away the units for comparison with non-unitized bounds.
        xx, = self._process_unit_info([("x", x)], kwargs)
        scalex = (xx < xmin) or (xx > xmax)

        trans = self.get_xaxis_transform(which='grid')
        l = mlines.Line2D([x, x], [ymin, ymax], transform=trans, **kwargs)
        self.add_line(l)
        l.get_path()._interpolation_steps = mpl.axis.GRIDLINE_INTERPOLATION_STEPS
        if scalex:
            self._request_autoscale_view("x")
        return l

    @staticmethod
    def _check_no_units(vals, names):
        # Helper method to check that vals are not unitized
        for val, name in zip(vals, names):
            if not munits._is_natively_supported(val):
                raise ValueError(f"{name} must be a single scalar value, "
                                 f"but got {val}")

    @_docstring.interpd
    def axline(self, xy1, xy2=None, *, slope=None, **kwargs):
        """
        Add an infinitely long straight line.

        The line can be defined either by two points *xy1* and *xy2*, or
        by one point *xy1* and a *slope*.

        This draws a straight line "on the screen", regardless of the x and y
        scales, and is thus also suitable for drawing exponential decays in
        semilog plots, power laws in loglog plots, etc. However, *slope*
        should only be used with linear scales; It has no clear meaning for
        all other scales, and thus the behavior is undefined. Please specify
        the line using the points *xy1*, *xy2* for non-linear scales.

        The *transform* keyword argument only applies to the points *xy1*,
        *xy2*. The *slope* (if given) is always in data coordinates. This can
        be used e.g. with ``ax.transAxes`` for drawing grid lines with a fixed
        slope.

        Parameters
        ----------
        xy1, xy2 : (float, float)
            Points for the line to pass through.
            Either *xy2* or *slope* has to be given.
        slope : float, optional
            The slope of the line. Either *xy2* or *slope* has to be given.

        Returns
        -------
        `.AxLine`

        Other Parameters
        ----------------
        **kwargs
            Valid kwargs are `.Line2D` properties

            %(Line2D:kwdoc)s

        See Also
        --------
        axhline : for horizontal lines
        axvline : for vertical lines

        Examples
        --------
        Draw a thick red line passing through (0, 0) and (1, 1)::

            >>> axline((0, 0), (1, 1), linewidth=4, color='r')
        """
        if slope is not None and (self.get_xscale() != 'linear' or
                                  self.get_yscale() != 'linear'):
            raise TypeError("'slope' cannot be used with non-linear scales")

        datalim = [xy1] if xy2 is None else [xy1, xy2]
        if "transform" in kwargs:
            # if a transform is passed (i.e. line points not in data space),
            # data limits should not be adjusted.
            datalim = []

        line = mlines.AxLine(xy1, xy2, slope, **kwargs)
        # Like add_line, but correctly handling data limits.
        self._set_artist_props(line)
        if line.get_clip_path() is None:
            line.set_clip_path(self.patch)
        if not line.get_label():
            line.set_label(f"_child{len(self._children)}")
        self._children.append(line)
        line._remove_method = self._children.remove
        self.update_datalim(datalim)

        self._request_autoscale_view()
        return line

    @_docstring.interpd
    def axhspan(self, ymin, ymax, xmin=0, xmax=1, **kwargs):
        """
        Add a horizontal span (rectangle) across the Axes.

        The rectangle spans from *ymin* to *ymax* vertically, and, by default,
        the whole x-axis horizontally.  The x-span can be set using *xmin*
        (default: 0) and *xmax* (default: 1) which are in axis units; e.g.
        ``xmin = 0.5`` always refers to the middle of the x-axis regardless of
        the limits set by `~.Axes.set_xlim`.

        Parameters
        ----------
        ymin : float
            Lower y-coordinate of the span, in data units.
        ymax : float
            Upper y-coordinate of the span, in data units.
        xmin : float, default: 0
            Lower x-coordinate of the span, in x-axis (0-1) units.
        xmax : float, default: 1
            Upper x-coordinate of the span, in x-axis (0-1) units.

        Returns
        -------
        `~matplotlib.patches.Rectangle`
            Horizontal span (rectangle) from (xmin, ymin) to (xmax, ymax).

        Other Parameters
        ----------------
        **kwargs : `~matplotlib.patches.Rectangle` properties

        %(Rectangle:kwdoc)s

        See Also
        --------
        axvspan : Add a vertical span across the Axes.
        """
        # Strip units away.
        self._check_no_units([xmin, xmax], ['xmin', 'xmax'])
        (ymin, ymax), = self._process_unit_info([("y", [ymin, ymax])], kwargs)

        p = mpatches.Rectangle((xmin, ymin), xmax - xmin, ymax - ymin, **kwargs)
        p.set_transform(self.get_yaxis_transform(which="grid"))
        # For Rectangles and non-separable transforms, add_patch can be buggy
        # and update the x limits even though it shouldn't do so for an
        # yaxis_transformed patch, so undo that update.
        ix = self.dataLim.intervalx.copy()
        mx = self.dataLim.minposx
        self.add_patch(p)
        self.dataLim.intervalx = ix
        self.dataLim.minposx = mx
        p.get_path()._interpolation_steps = mpl.axis.GRIDLINE_INTERPOLATION_STEPS
        self._request_autoscale_view("y")
        return p

    @_docstring.interpd
    def axvspan(self, xmin, xmax, ymin=0, ymax=1, **kwargs):
        """
        Add a vertical span (rectangle) across the Axes.

        The rectangle spans from *xmin* to *xmax* horizontally, and, by
        default, the whole y-axis vertically.  The y-span can be set using
        *ymin* (default: 0) and *ymax* (default: 1) which are in axis units;
        e.g. ``ymin = 0.5`` always refers to the middle of the y-axis
        regardless of the limits set by `~.Axes.set_ylim`.

        Parameters
        ----------
        xmin : float
            Lower x-coordinate of the span, in data units.
        xmax : float
            Upper x-coordinate of the span, in data units.
        ymin : float, default: 0
            Lower y-coordinate of the span, in y-axis units (0-1).
        ymax : float, default: 1
            Upper y-coordinate of the span, in y-axis units (0-1).

        Returns
        -------
        `~matplotlib.patches.Rectangle`
            Vertical span (rectangle) from (xmin, ymin) to (xmax, ymax).

        Other Parameters
        ----------------
        **kwargs : `~matplotlib.patches.Rectangle` properties

        %(Rectangle:kwdoc)s

        See Also
        --------
        axhspan : Add a horizontal span across the Axes.

        Examples
        --------
        Draw a vertical, green, translucent rectangle from x = 1.25 to
        x = 1.55 that spans the yrange of the Axes.

        >>> axvspan(1.25, 1.55, facecolor='g', alpha=0.5)

        """
        # Strip units away.
        self._check_no_units([ymin, ymax], ['ymin', 'ymax'])
        (xmin, xmax), = self._process_unit_info([("x", [xmin, xmax])], kwargs)

        p = mpatches.Rectangle((xmin, ymin), xmax - xmin, ymax - ymin, **kwargs)
        p.set_transform(self.get_xaxis_transform(which="grid"))
        # For Rectangles and non-separable transforms, add_patch can be buggy
        # and update the y limits even though it shouldn't do so for an
        # xaxis_transformed patch, so undo that update.
        iy = self.dataLim.intervaly.copy()
        my = self.dataLim.minposy
        self.add_patch(p)
        self.dataLim.intervaly = iy
        self.dataLim.minposy = my
        p.get_path()._interpolation_steps = mpl.axis.GRIDLINE_INTERPOLATION_STEPS
        self._request_autoscale_view("x")
        return p

    @_api.make_keyword_only("3.10", "label")
    @_preprocess_data(replace_names=["y", "xmin", "xmax", "colors"],
                      label_namer="y")
    def hlines(self, y, xmin, xmax, colors=None, linestyles='solid',
               label='', **kwargs):
        """
        Plot horizontal lines at each *y* from *xmin* to *xmax*.

        Parameters
        ----------
        y : float or array-like
            y-indexes where to plot the lines.

        xmin, xmax : float or array-like
            Respective beginning and end of each line. If scalars are
            provided, all lines will have the same length.

        colors : :mpltype:`color` or list of color , default: :rc:`lines.color`

        linestyles : {'solid', 'dashed', 'dashdot', 'dotted'}, default: 'solid'

        label : str, default: ''

        Returns
        -------
        `~matplotlib.collections.LineCollection`

        Other Parameters
        ----------------
        data : indexable object, optional
            DATA_PARAMETER_PLACEHOLDER
        **kwargs :  `~matplotlib.collections.LineCollection` properties.

        See Also
        --------
        vlines : vertical lines
        axhline : horizontal line across the Axes
        """

        # We do the conversion first since not all unitized data is uniform
        xmin, xmax, y = self._process_unit_info(
            [("x", xmin), ("x", xmax), ("y", y)], kwargs)

        if not np.iterable(y):
            y = [y]
        if not np.iterable(xmin):
            xmin = [xmin]
        if not np.iterable(xmax):
            xmax = [xmax]

        # Create and combine masked_arrays from input
        y, xmin, xmax = cbook._combine_masks(y, xmin, xmax)
        y = np.ravel(y)
        xmin = np.ravel(xmin)
        xmax = np.ravel(xmax)

        masked_verts = np.ma.empty((len(y), 2, 2))
        masked_verts[:, 0, 0] = xmin
        masked_verts[:, 0, 1] = y
        masked_verts[:, 1, 0] = xmax
        masked_verts[:, 1, 1] = y

        lines = mcoll.LineCollection(masked_verts, colors=colors,
                                     linestyles=linestyles, label=label)
        self.add_collection(lines, autolim=False)
        lines._internal_update(kwargs)

        if len(y) > 0:
            # Extreme values of xmin/xmax/y.  Using masked_verts here handles
            # the case of y being a masked *object* array (as can be generated
            # e.g. by errorbar()), which would make nanmin/nanmax stumble.
            updatex = True
            updatey = True
            if self.name == "rectilinear":
                datalim = lines.get_datalim(self.transData)
                t = lines.get_transform()
                updatex, updatey = t.contains_branch_seperately(self.transData)
                minx = np.nanmin(datalim.xmin)
                maxx = np.nanmax(datalim.xmax)
                miny = np.nanmin(datalim.ymin)
                maxy = np.nanmax(datalim.ymax)
            else:
                minx = np.nanmin(masked_verts[..., 0])
                maxx = np.nanmax(masked_verts[..., 0])
                miny = np.nanmin(masked_verts[..., 1])
                maxy = np.nanmax(masked_verts[..., 1])

            corners = (minx, miny), (maxx, maxy)
            self.update_datalim(corners, updatex, updatey)
            self._request_autoscale_view()
        return lines

    @_api.make_keyword_only("3.10", "label")
    @_preprocess_data(replace_names=["x", "ymin", "ymax", "colors"],
                      label_namer="x")
    def vlines(self, x, ymin, ymax, colors=None, linestyles='solid',
               label='', **kwargs):
        """
        Plot vertical lines at each *x* from *ymin* to *ymax*.

        Parameters
        ----------
        x : float or array-like
            x-indexes where to plot the lines.

        ymin, ymax : float or array-like
            Respective beginning and end of each line. If scalars are
            provided, all lines will have the same length.

        colors : :mpltype:`color` or list of color, default: :rc:`lines.color`

        linestyles : {'solid', 'dashed', 'dashdot', 'dotted'}, default: 'solid'

        label : str, default: ''

        Returns
        -------
        `~matplotlib.collections.LineCollection`

        Other Parameters
        ----------------
        data : indexable object, optional
            DATA_PARAMETER_PLACEHOLDER
        **kwargs : `~matplotlib.collections.LineCollection` properties.

        See Also
        --------
        hlines : horizontal lines
        axvline : vertical line across the Axes
        """

        # We do the conversion first since not all unitized data is uniform
        x, ymin, ymax = self._process_unit_info(
            [("x", x), ("y", ymin), ("y", ymax)], kwargs)

        if not np.iterable(x):
            x = [x]
        if not np.iterable(ymin):
            ymin = [ymin]
        if not np.iterable(ymax):
            ymax = [ymax]

        # Create and combine masked_arrays from input
        x, ymin, ymax = cbook._combine_masks(x, ymin, ymax)
        x = np.ravel(x)
        ymin = np.ravel(ymin)
        ymax = np.ravel(ymax)

        masked_verts = np.ma.empty((len(x), 2, 2))
        masked_verts[:, 0, 0] = x
        masked_verts[:, 0, 1] = ymin
        masked_verts[:, 1, 0] = x
        masked_verts[:, 1, 1] = ymax

        lines = mcoll.LineCollection(masked_verts, colors=colors,
                                     linestyles=linestyles, label=label)
        self.add_collection(lines, autolim=False)
        lines._internal_update(kwargs)

        if len(x) > 0:
            # Extreme values of x/ymin/ymax.  Using masked_verts here handles
            # the case of x being a masked *object* array (as can be generated
            # e.g. by errorbar()), which would make nanmin/nanmax stumble.
            updatex = True
            updatey = True
            if self.name == "rectilinear":
                datalim = lines.get_datalim(self.transData)
                t = lines.get_transform()
                updatex, updatey = t.contains_branch_seperately(self.transData)
                minx = np.nanmin(datalim.xmin)
                maxx = np.nanmax(datalim.xmax)
                miny = np.nanmin(datalim.ymin)
                maxy = np.nanmax(datalim.ymax)
            else:
                minx = np.nanmin(masked_verts[..., 0])
                maxx = np.nanmax(masked_verts[..., 0])
                miny = np.nanmin(masked_verts[..., 1])
                maxy = np.nanmax(masked_verts[..., 1])

            corners = (minx, miny), (maxx, maxy)
            self.update_datalim(corners, updatex, updatey)
            self._request_autoscale_view()
        return lines

    @_api.make_keyword_only("3.10", "orientation")
    @_preprocess_data(replace_names=["positions", "lineoffsets",
                                     "linelengths", "linewidths",
                                     "colors", "linestyles"])
    @_docstring.interpd
    def eventplot(self, positions, orientation='horizontal', lineoffsets=1,
                  linelengths=1, linewidths=None, colors=None, alpha=None,
                  linestyles='solid', **kwargs):
        """
        Plot identical parallel lines at the given positions.

        This type of plot is commonly used in neuroscience for representing
        neural events, where it is usually called a spike raster, dot raster,
        or raster plot.

        However, it is useful in any situation where you wish to show the
        timing or position of multiple sets of discrete events, such as the
        arrival times of people to a business on each day of the month or the
        date of hurricanes each year of the last century.

        Parameters
        ----------
        positions : array-like or list of array-like
            A 1D array-like defines the positions of one sequence of events.

            Multiple groups of events may be passed as a list of array-likes.
            Each group can be styled independently by passing lists of values
            to *lineoffsets*, *linelengths*, *linewidths*, *colors* and
            *linestyles*.

            Note that *positions* can be a 2D array, but in practice different
            event groups usually have different counts so that one will use a
            list of different-length arrays rather than a 2D array.

        orientation : {'horizontal', 'vertical'}, default: 'horizontal'
            The direction of the event sequence:

            - 'horizontal': the events are arranged horizontally.
              The indicator lines are vertical.
            - 'vertical': the events are arranged vertically.
              The indicator lines are horizontal.

        lineoffsets : float or array-like, default: 1
            The offset of the center of the lines from the origin, in the
            direction orthogonal to *orientation*.

            If *positions* is 2D, this can be a sequence with length matching
            the length of *positions*.

        linelengths : float or array-like, default: 1
            The total height of the lines (i.e. the lines stretches from
            ``lineoffset - linelength/2`` to ``lineoffset + linelength/2``).

            If *positions* is 2D, this can be a sequence with length matching
            the length of *positions*.

        linewidths : float or array-like, default: :rc:`lines.linewidth`
            The line width(s) of the event lines, in points.

            If *positions* is 2D, this can be a sequence with length matching
            the length of *positions*.

        colors : :mpltype:`color` or list of color, default: :rc:`lines.color`
            The color(s) of the event lines.

            If *positions* is 2D, this can be a sequence with length matching
            the length of *positions*.

        alpha : float or array-like, default: 1
            The alpha blending value(s), between 0 (transparent) and 1
            (opaque).

            If *positions* is 2D, this can be a sequence with length matching
            the length of *positions*.

        linestyles : str or tuple or list of such values, default: 'solid'
            Default is 'solid'. Valid strings are ['solid', 'dashed',
            'dashdot', 'dotted', '-', '--', '-.', ':']. Dash tuples
            should be of the form::

                (offset, onoffseq),

            where *onoffseq* is an even length tuple of on and off ink
            in points.

            If *positions* is 2D, this can be a sequence with length matching
            the length of *positions*.

        data : indexable object, optional
            DATA_PARAMETER_PLACEHOLDER

        **kwargs
            Other keyword arguments are line collection properties.  See
            `.LineCollection` for a list of the valid properties.

        Returns
        -------
        list of `.EventCollection`
            The `.EventCollection` that were added.

        Notes
        -----
        For *linelengths*, *linewidths*, *colors*, *alpha* and *linestyles*, if
        only a single value is given, that value is applied to all lines. If an
        array-like is given, it must have the same length as *positions*, and
        each value will be applied to the corresponding row of the array.

        Examples
        --------
        .. plot:: gallery/lines_bars_and_markers/eventplot_demo.py
        """

        lineoffsets, linelengths = self._process_unit_info(
                [("y", lineoffsets), ("y", linelengths)], kwargs)

        # fix positions, noting that it can be a list of lists:
        if not np.iterable(positions):
            positions = [positions]
        elif any(np.iterable(position) for position in positions):
            positions = [np.asanyarray(position) for position in positions]
        else:
            positions = [np.asanyarray(positions)]

        poss = []
        for position in positions:
            poss += self._process_unit_info([("x", position)], kwargs)
        positions = poss

        # prevent 'singular' keys from **kwargs dict from overriding the effect
        # of 'plural' keyword arguments (e.g. 'color' overriding 'colors')
        colors = cbook._local_over_kwdict(colors, kwargs, 'color')
        linewidths = cbook._local_over_kwdict(linewidths, kwargs, 'linewidth')
        linestyles = cbook._local_over_kwdict(linestyles, kwargs, 'linestyle')

        if not np.iterable(lineoffsets):
            lineoffsets = [lineoffsets]
        if not np.iterable(linelengths):
            linelengths = [linelengths]
        if not np.iterable(linewidths):
            linewidths = [linewidths]
        if not np.iterable(colors):
            colors = [colors]
        if not np.iterable(alpha):
            alpha = [alpha]
        if hasattr(linestyles, 'lower') or not np.iterable(linestyles):
            linestyles = [linestyles]

        lineoffsets = np.asarray(lineoffsets)
        linelengths = np.asarray(linelengths)
        linewidths = np.asarray(linewidths)

        if len(lineoffsets) == 0:
            raise ValueError('lineoffsets cannot be empty')
        if len(linelengths) == 0:
            raise ValueError('linelengths cannot be empty')
        if len(linestyles) == 0:
            raise ValueError('linestyles cannot be empty')
        if len(linewidths) == 0:
            raise ValueError('linewidths cannot be empty')
        if len(alpha) == 0:
            raise ValueError('alpha cannot be empty')
        if len(colors) == 0:
            colors = [None]
        try:
            # Early conversion of the colors into RGBA values to take care
            # of cases like colors='0.5' or colors='C1'.  (Issue #8193)
            colors = mcolors.to_rgba_array(colors)
        except ValueError:
            # Will fail if any element of *colors* is None. But as long
            # as len(colors) == 1 or len(positions), the rest of the
            # code should process *colors* properly.
            pass

        if len(lineoffsets) == 1 and len(positions) != 1:
            lineoffsets = np.tile(lineoffsets, len(positions))
            lineoffsets[0] = 0
            lineoffsets = np.cumsum(lineoffsets)
        if len(linelengths) == 1:
            linelengths = np.tile(linelengths, len(positions))
        if len(linewidths) == 1:
            linewidths = np.tile(linewidths, len(positions))
        if len(colors) == 1:
            colors = list(colors) * len(positions)
        if len(alpha) == 1:
            alpha = list(alpha) * len(positions)
        if len(linestyles) == 1:
            linestyles = [linestyles] * len(positions)

        if len(lineoffsets) != len(positions):
            raise ValueError('lineoffsets and positions are unequal sized '
                             'sequences')
        if len(linelengths) != len(positions):
            raise ValueError('linelengths and positions are unequal sized '
                             'sequences')
        if len(linewidths) != len(positions):
            raise ValueError('linewidths and positions are unequal sized '
                             'sequences')
        if len(colors) != len(positions):
            raise ValueError('colors and positions are unequal sized '
                             'sequences')
        if len(alpha) != len(positions):
            raise ValueError('alpha and positions are unequal sized '
                             'sequences')
        if len(linestyles) != len(positions):
            raise ValueError('linestyles and positions are unequal sized '
                             'sequences')

        colls = []
        for position, lineoffset, linelength, linewidth, color, alpha_, \
            linestyle in \
                zip(positions, lineoffsets, linelengths, linewidths,
                    colors, alpha, linestyles):
            coll = mcoll.EventCollection(position,
                                         orientation=orientation,
                                         lineoffset=lineoffset,
                                         linelength=linelength,
                                         linewidth=linewidth,
                                         color=color,
                                         alpha=alpha_,
                                         linestyle=linestyle)
            self.add_collection(coll, autolim=False)
            coll._internal_update(kwargs)
            colls.append(coll)

        if len(positions) > 0:
            # try to get min/max
            min_max = [(np.min(_p), np.max(_p)) for _p in positions
                       if len(_p) > 0]
            # if we have any non-empty positions, try to autoscale
            if len(min_max) > 0:
                mins, maxes = zip(*min_max)
                minpos = np.min(mins)
                maxpos = np.max(maxes)

                minline = (lineoffsets - linelengths).min()
                maxline = (lineoffsets + linelengths).max()

                if orientation == "vertical":
                    corners = (minline, minpos), (maxline, maxpos)
                else:  # "horizontal"
                    corners = (minpos, minline), (maxpos, maxline)
                self.update_datalim(corners)
                self._request_autoscale_view()

        return colls

    #### Basic plotting

    # Uses a custom implementation of data-kwarg handling in
    # _process_plot_var_args.
    @_docstring.interpd
    def plot(self, *args, scalex=True, scaley=True, data=None, **kwargs):
        """
        Plot y versus x as lines and/or markers.

        Call signatures::

            plot([x], y, [fmt], *, data=None, **kwargs)
            plot([x], y, [fmt], [x2], y2, [fmt2], ..., **kwargs)

        The coordinates of the points or line nodes are given by *x*, *y*.

        The optional parameter *fmt* is a convenient way for defining basic
        formatting like color, marker and linestyle. It's a shortcut string
        notation described in the *Notes* section below.

        >>> plot(x, y)        # plot x and y using default line style and color
        >>> plot(x, y, 'bo')  # plot x and y using blue circle markers
        >>> plot(y)           # plot y using x as index array 0..N-1
        >>> plot(y, 'r+')     # ditto, but with red plusses

        You can use `.Line2D` properties as keyword arguments for more
        control on the appearance. Line properties and *fmt* can be mixed.
        The following two calls yield identical results:

        >>> plot(x, y, 'go--', linewidth=2, markersize=12)
        >>> plot(x, y, color='green', marker='o', linestyle='dashed',
        ...      linewidth=2, markersize=12)

        When conflicting with *fmt*, keyword arguments take precedence.


        **Plotting labelled data**

        There's a convenient way for plotting objects with labelled data (i.e.
        data that can be accessed by index ``obj['y']``). Instead of giving
        the data in *x* and *y*, you can provide the object in the *data*
        parameter and just give the labels for *x* and *y*::

        >>> plot('xlabel', 'ylabel', data=obj)

        All indexable objects are supported. This could e.g. be a `dict`, a
        `pandas.DataFrame` or a structured numpy array.


        **Plotting multiple sets of data**

        There are various ways to plot multiple sets of data.

        - The most straight forward way is just to call `plot` multiple times.
          Example:

          >>> plot(x1, y1, 'bo')
          >>> plot(x2, y2, 'go')

        - If *x* and/or *y* are 2D arrays, a separate data set will be drawn
          for every column. If both *x* and *y* are 2D, they must have the
          same shape. If only one of them is 2D with shape (N, m) the other
          must have length N and will be used for every data set m.

          Example:

          >>> x = [1, 2, 3]
          >>> y = np.array([[1, 2], [3, 4], [5, 6]])
          >>> plot(x, y)

          is equivalent to:

          >>> for col in range(y.shape[1]):
          ...     plot(x, y[:, col])

        - The third way is to specify multiple sets of *[x]*, *y*, *[fmt]*
          groups::

          >>> plot(x1, y1, 'g^', x2, y2, 'g-')

          In this case, any additional keyword argument applies to all
          datasets. Also, this syntax cannot be combined with the *data*
          parameter.

        By default, each line is assigned a different style specified by a
        'style cycle'. The *fmt* and line property parameters are only
        necessary if you want explicit deviations from these defaults.
        Alternatively, you can also change the style cycle using
        :rc:`axes.prop_cycle`.


        Parameters
        ----------
        x, y : array-like or float
            The horizontal / vertical coordinates of the data points.
            *x* values are optional and default to ``range(len(y))``.

            Commonly, these parameters are 1D arrays.

            They can also be scalars, or two-dimensional (in that case, the
            columns represent separate data sets).

            These arguments cannot be passed as keywords.

        fmt : str, optional
            A format string, e.g. 'ro' for red circles. See the *Notes*
            section for a full description of the format strings.

            Format strings are just an abbreviation for quickly setting
            basic line properties. All of these and more can also be
            controlled by keyword arguments.

            This argument cannot be passed as keyword.

        data : indexable object, optional
            An object with labelled data. If given, provide the label names to
            plot in *x* and *y*.

            .. note::
                Technically there's a slight ambiguity in calls where the
                second label is a valid *fmt*. ``plot('n', 'o', data=obj)``
                could be ``plt(x, y)`` or ``plt(y, fmt)``. In such cases,
                the former interpretation is chosen, but a warning is issued.
                You may suppress the warning by adding an empty format string
                ``plot('n', 'o', '', data=obj)``.

        Returns
        -------
        list of `.Line2D`
            A list of lines representing the plotted data.

        Other Parameters
        ----------------
        scalex, scaley : bool, default: True
            These parameters determine if the view limits are adapted to the
            data limits. The values are passed on to
            `~.axes.Axes.autoscale_view`.

        **kwargs : `~matplotlib.lines.Line2D` properties, optional
            *kwargs* are used to specify properties like a line label (for
            auto legends), linewidth, antialiasing, marker face color.
            Example::

            >>> plot([1, 2, 3], [1, 2, 3], 'go-', label='line 1', linewidth=2)
            >>> plot([1, 2, 3], [1, 4, 9], 'rs', label='line 2')

            If you specify multiple lines with one plot call, the kwargs apply
            to all those lines. In case the label object is iterable, each
            element is used as labels for each set of data.

            Here is a list of available `.Line2D` properties:

            %(Line2D:kwdoc)s

        See Also
        --------
        scatter : XY scatter plot with markers of varying size and/or color (
            sometimes also called bubble chart).

        Notes
        -----
        **Format Strings**

        A format string consists of a part for color, marker and line::

            fmt = '[marker][line][color]'

        Each of them is optional. If not provided, the value from the style
        cycle is used. Exception: If ``line`` is given, but no ``marker``,
        the data will be a line without markers.

        Other combinations such as ``[color][marker][line]`` are also
        supported, but note that their parsing may be ambiguous.

        **Markers**

        =============   ===============================
        character       description
        =============   ===============================
        ``'.'``         point marker
        ``','``         pixel marker
        ``'o'``         circle marker
        ``'v'``         triangle_down marker
        ``'^'``         triangle_up marker
        ``'<'``         triangle_left marker
        ``'>'``         triangle_right marker
        ``'1'``         tri_down marker
        ``'2'``         tri_up marker
        ``'3'``         tri_left marker
        ``'4'``         tri_right marker
        ``'8'``         octagon marker
        ``'s'``         square marker
        ``'p'``         pentagon marker
        ``'P'``         plus (filled) marker
        ``'*'``         star marker
        ``'h'``         hexagon1 marker
        ``'H'``         hexagon2 marker
        ``'+'``         plus marker
        ``'x'``         x marker
        ``'X'``         x (filled) marker
        ``'D'``         diamond marker
        ``'d'``         thin_diamond marker
        ``'|'``         vline marker
        ``'_'``         hline marker
        =============   ===============================

        **Line Styles**

        =============    ===============================
        character        description
        =============    ===============================
        ``'-'``          solid line style
        ``'--'``         dashed line style
        ``'-.'``         dash-dot line style
        ``':'``          dotted line style
        =============    ===============================

        Example format strings::

            'b'    # blue markers with default shape
            'or'   # red circles
            '-g'   # green solid line
            '--'   # dashed line with default color
            '^k:'  # black triangle_up markers connected by a dotted line

        **Colors**

        The supported color abbreviations are the single letter codes

        =============    ===============================
        character        color
        =============    ===============================
        ``'b'``          blue
        ``'g'``          green
        ``'r'``          red
        ``'c'``          cyan
        ``'m'``          magenta
        ``'y'``          yellow
        ``'k'``          black
        ``'w'``          white
        =============    ===============================

        and the ``'CN'`` colors that index into the default property cycle.

        If the color is the only part of the format string, you can
        additionally use any  `matplotlib.colors` spec, e.g. full names
        (``'green'``) or hex strings (``'#008000'``).
        """
        kwargs = cbook.normalize_kwargs(kwargs, mlines.Line2D)
        lines = [*self._get_lines(self, *args, data=data, **kwargs)]
        for line in lines:
            self.add_line(line)
        if scalex:
            self._request_autoscale_view("x")
        if scaley:
            self._request_autoscale_view("y")
        return lines

    @_api.deprecated("3.9", alternative="plot")
    @_preprocess_data(replace_names=["x", "y"], label_namer="y")
    @_docstring.interpd
    def plot_date(self, x, y, fmt='o', tz=None, xdate=True, ydate=False,
                  **kwargs):
        """
        Plot coercing the axis to treat floats as dates.

        .. deprecated:: 3.9

            This method exists for historic reasons and will be removed in version 3.11.

            - ``datetime``-like data should directly be plotted using
              `~.Axes.plot`.
            -  If you need to plot plain numeric data as :ref:`date-format` or
               need to set a timezone, call ``ax.xaxis.axis_date`` /
               ``ax.yaxis.axis_date`` before `~.Axes.plot`. See
               `.Axis.axis_date`.

        Similar to `.plot`, this plots *y* vs. *x* as lines or markers.
        However, the axis labels are formatted as dates depending on *xdate*
        and *ydate*.  Note that `.plot` will work with `datetime` and
        `numpy.datetime64` objects without resorting to this method.

        Parameters
        ----------
        x, y : array-like
            The coordinates of the data points. If *xdate* or *ydate* is
            *True*, the respective values *x* or *y* are interpreted as
            :ref:`Matplotlib dates <date-format>`.

        fmt : str, optional
            The plot format string. For details, see the corresponding
            parameter in `.plot`.

        tz : timezone string or `datetime.tzinfo`, default: :rc:`timezone`
            The time zone to use in labeling dates.

        xdate : bool, default: True
            If *True*, the *x*-axis will be interpreted as Matplotlib dates.

        ydate : bool, default: False
            If *True*, the *y*-axis will be interpreted as Matplotlib dates.

        Returns
        -------
        list of `.Line2D`
            Objects representing the plotted data.

        Other Parameters
        ----------------
        data : indexable object, optional
            DATA_PARAMETER_PLACEHOLDER
        **kwargs
            Keyword arguments control the `.Line2D` properties:

            %(Line2D:kwdoc)s

        See Also
        --------
        matplotlib.dates : Helper functions on dates.
        matplotlib.dates.date2num : Convert dates to num.
        matplotlib.dates.num2date : Convert num to dates.
        matplotlib.dates.drange : Create an equally spaced sequence of dates.

        Notes
        -----
        If you are using custom date tickers and formatters, it may be
        necessary to set the formatters/locators after the call to
        `.plot_date`. `.plot_date` will set the default tick locator to
        `.AutoDateLocator` (if the tick locator is not already set to a
        `.DateLocator` instance) and the default tick formatter to
        `.AutoDateFormatter` (if the tick formatter is not already set to a
        `.DateFormatter` instance).
        """
        if xdate:
            self.xaxis_date(tz)
        if ydate:
            self.yaxis_date(tz)
        return self.plot(x, y, fmt, **kwargs)

    # @_preprocess_data() # let 'plot' do the unpacking..
    @_docstring.interpd
    def loglog(self, *args, **kwargs):
        """
        Make a plot with log scaling on both the x- and y-axis.

        Call signatures::

            loglog([x], y, [fmt], data=None, **kwargs)
            loglog([x], y, [fmt], [x2], y2, [fmt2], ..., **kwargs)

        This is just a thin wrapper around `.plot` which additionally changes
        both the x-axis and the y-axis to log scaling. All the concepts and
        parameters of plot can be used here as well.

        The additional parameters *base*, *subs* and *nonpositive* control the
        x/y-axis properties. They are just forwarded to `.Axes.set_xscale` and
        `.Axes.set_yscale`. To use different properties on the x-axis and the
        y-axis, use e.g.
        ``ax.set_xscale("log", base=10); ax.set_yscale("log", base=2)``.

        Parameters
        ----------
        base : float, default: 10
            Base of the logarithm.

        subs : sequence, optional
            The location of the minor ticks. If *None*, reasonable locations
            are automatically chosen depending on the number of decades in the
            plot. See `.Axes.set_xscale`/`.Axes.set_yscale` for details.

        nonpositive : {'mask', 'clip'}, default: 'clip'
            Non-positive values can be masked as invalid, or clipped to a very
            small positive number.

        **kwargs
            All parameters supported by `.plot`.

        Returns
        -------
        list of `.Line2D`
            Objects representing the plotted data.
        """
        dx = {k: v for k, v in kwargs.items()
              if k in ['base', 'subs', 'nonpositive',
                       'basex', 'subsx', 'nonposx']}
        self.set_xscale('log', **dx)
        dy = {k: v for k, v in kwargs.items()
              if k in ['base', 'subs', 'nonpositive',
                       'basey', 'subsy', 'nonposy']}
        self.set_yscale('log', **dy)
        return self.plot(
            *args, **{k: v for k, v in kwargs.items() if k not in {*dx, *dy}})

    # @_preprocess_data() # let 'plot' do the unpacking..
    @_docstring.interpd
    def semilogx(self, *args, **kwargs):
        """
        Make a plot with log scaling on the x-axis.

        Call signatures::

            semilogx([x], y, [fmt], data=None, **kwargs)
            semilogx([x], y, [fmt], [x2], y2, [fmt2], ..., **kwargs)

        This is just a thin wrapper around `.plot` which additionally changes
        the x-axis to log scaling. All the concepts and parameters of plot can
        be used here as well.

        The additional parameters *base*, *subs*, and *nonpositive* control the
        x-axis properties. They are just forwarded to `.Axes.set_xscale`.

        Parameters
        ----------
        base : float, default: 10
            Base of the x logarithm.

        subs : array-like, optional
            The location of the minor xticks. If *None*, reasonable locations
            are automatically chosen depending on the number of decades in the
            plot. See `.Axes.set_xscale` for details.

        nonpositive : {'mask', 'clip'}, default: 'clip'
            Non-positive values in x can be masked as invalid, or clipped to a
            very small positive number.

        **kwargs
            All parameters supported by `.plot`.

        Returns
        -------
        list of `.Line2D`
            Objects representing the plotted data.
        """
        d = {k: v for k, v in kwargs.items()
             if k in ['base', 'subs', 'nonpositive',
                      'basex', 'subsx', 'nonposx']}
        self.set_xscale('log', **d)
        return self.plot(
            *args, **{k: v for k, v in kwargs.items() if k not in d})

    # @_preprocess_data() # let 'plot' do the unpacking..
    @_docstring.interpd
    def semilogy(self, *args, **kwargs):
        """
        Make a plot with log scaling on the y-axis.

        Call signatures::

            semilogy([x], y, [fmt], data=None, **kwargs)
            semilogy([x], y, [fmt], [x2], y2, [fmt2], ..., **kwargs)

        This is just a thin wrapper around `.plot` which additionally changes
        the y-axis to log scaling. All the concepts and parameters of plot can
        be used here as well.

        The additional parameters *base*, *subs*, and *nonpositive* control the
        y-axis properties. They are just forwarded to `.Axes.set_yscale`.

        Parameters
        ----------
        base : float, default: 10
            Base of the y logarithm.

        subs : array-like, optional
            The location of the minor yticks. If *None*, reasonable locations
            are automatically chosen depending on the number of decades in the
            plot. See `.Axes.set_yscale` for details.

        nonpositive : {'mask', 'clip'}, default: 'clip'
            Non-positive values in y can be masked as invalid, or clipped to a
            very small positive number.

        **kwargs
            All parameters supported by `.plot`.

        Returns
        -------
        list of `.Line2D`
            Objects representing the plotted data.
        """
        d = {k: v for k, v in kwargs.items()
             if k in ['base', 'subs', 'nonpositive',
                      'basey', 'subsy', 'nonposy']}
        self.set_yscale('log', **d)
        return self.plot(
            *args, **{k: v for k, v in kwargs.items() if k not in d})

    @_preprocess_data(replace_names=["x"], label_namer="x")
    def acorr(self, x, **kwargs):
        """
        Plot the autocorrelation of *x*.

        Parameters
        ----------
        x : array-like
            Not run through Matplotlib's unit conversion, so this should
            be a unit-less array.

        detrend : callable, default: `.mlab.detrend_none` (no detrending)
            A detrending function applied to *x*.  It must have the
            signature ::

                detrend(x: np.ndarray) -> np.ndarray

        normed : bool, default: True
            If ``True``, input vectors are normalised to unit length.

        usevlines : bool, default: True
            Determines the plot style.

            If ``True``, vertical lines are plotted from 0 to the acorr value
            using `.Axes.vlines`. Additionally, a horizontal line is plotted
            at y=0 using `.Axes.axhline`.

            If ``False``, markers are plotted at the acorr values using
            `.Axes.plot`.

        maxlags : int, default: 10
            Number of lags to show. If ``None``, will return all
            ``2 * len(x) - 1`` lags.

        Returns
        -------
        lags : array (length ``2*maxlags+1``)
            The lag vector.
        c : array  (length ``2*maxlags+1``)
            The auto correlation vector.
        line : `.LineCollection` or `.Line2D`
            `.Artist` added to the Axes of the correlation:

            - `.LineCollection` if *usevlines* is True.
            - `.Line2D` if *usevlines* is False.
        b : `~matplotlib.lines.Line2D` or None
            Horizontal line at 0 if *usevlines* is True
            None *usevlines* is False.

        Other Parameters
        ----------------
        linestyle : `~matplotlib.lines.Line2D` property, optional
            The linestyle for plotting the data points.
            Only used if *usevlines* is ``False``.

        marker : str, default: 'o'
            The marker for plotting the data points.
            Only used if *usevlines* is ``False``.

        data : indexable object, optional
            DATA_PARAMETER_PLACEHOLDER

        **kwargs
            Additional parameters are passed to `.Axes.vlines` and
            `.Axes.axhline` if *usevlines* is ``True``; otherwise they are
            passed to `.Axes.plot`.

        Notes
        -----
        The cross correlation is performed with `numpy.correlate` with
        ``mode = "full"``.
        """
        return self.xcorr(x, x, **kwargs)

    @_api.make_keyword_only("3.10", "normed")
    @_preprocess_data(replace_names=["x", "y"], label_namer="y")
    def xcorr(self, x, y, normed=True, detrend=mlab.detrend_none,
              usevlines=True, maxlags=10, **kwargs):
        r"""
        Plot the cross correlation between *x* and *y*.

        The correlation with lag k is defined as
        :math:`\sum_n x[n+k] \cdot y^*[n]`, where :math:`y^*` is the complex
        conjugate of :math:`y`.

        Parameters
        ----------
        x, y : array-like of length n
            Neither *x* nor *y* are run through Matplotlib's unit conversion, so
            these should be unit-less arrays.

        detrend : callable, default: `.mlab.detrend_none` (no detrending)
            A detrending function applied to *x* and *y*.  It must have the
            signature ::

                detrend(x: np.ndarray) -> np.ndarray

        normed : bool, default: True
            If ``True``, input vectors are normalised to unit length.

        usevlines : bool, default: True
            Determines the plot style.

            If ``True``, vertical lines are plotted from 0 to the xcorr value
            using `.Axes.vlines`. Additionally, a horizontal line is plotted
            at y=0 using `.Axes.axhline`.

            If ``False``, markers are plotted at the xcorr values using
            `.Axes.plot`.

        maxlags : int, default: 10
            Number of lags to show. If None, will return all ``2 * len(x) - 1``
            lags.

        Returns
        -------
        lags : array (length ``2*maxlags+1``)
            The lag vector.
        c : array  (length ``2*maxlags+1``)
            The auto correlation vector.
        line : `.LineCollection` or `.Line2D`
            `.Artist` added to the Axes of the correlation:

            - `.LineCollection` if *usevlines* is True.
            - `.Line2D` if *usevlines* is False.
        b : `~matplotlib.lines.Line2D` or None
            Horizontal line at 0 if *usevlines* is True
            None *usevlines* is False.

        Other Parameters
        ----------------
        linestyle : `~matplotlib.lines.Line2D` property, optional
            The linestyle for plotting the data points.
            Only used if *usevlines* is ``False``.

        marker : str, default: 'o'
            The marker for plotting the data points.
            Only used if *usevlines* is ``False``.

        data : indexable object, optional
            DATA_PARAMETER_PLACEHOLDER

        **kwargs
            Additional parameters are passed to `.Axes.vlines` and
            `.Axes.axhline` if *usevlines* is ``True``; otherwise they are
            passed to `.Axes.plot`.

        Notes
        -----
        The cross correlation is performed with `numpy.correlate` with
        ``mode = "full"``.
        """
        Nx = len(x)
        if Nx != len(y):
            raise ValueError('x and y must be equal length')

        x = detrend(np.asarray(x))
        y = detrend(np.asarray(y))

        correls = np.correlate(x, y, mode="full")

        if normed:
            correls = correls / np.sqrt(np.dot(x, x) * np.dot(y, y))

        if maxlags is None:
            maxlags = Nx - 1

        if maxlags >= Nx or maxlags < 1:
            raise ValueError('maxlags must be None or strictly '
                             'positive < %d' % Nx)

        lags = np.arange(-maxlags, maxlags + 1)
        correls = correls[Nx - 1 - maxlags:Nx + maxlags]

        if usevlines:
            a = self.vlines(lags, [0], correls, **kwargs)
            # Make label empty so only vertical lines get a legend entry
            kwargs.pop('label', '')
            b = self.axhline(**kwargs)
        else:
            kwargs.setdefault('marker', 'o')
            kwargs.setdefault('linestyle', 'None')
            a, = self.plot(lags, correls, **kwargs)
            b = None
        return lags, correls, a, b

    #### Specialized plotting

    # @_preprocess_data() # let 'plot' do the unpacking..
    def step(self, x, y, *args, where='pre', data=None, **kwargs):
        """
        Make a step plot.

        Call signatures::

            step(x, y, [fmt], *, data=None, where='pre', **kwargs)
            step(x, y, [fmt], x2, y2, [fmt2], ..., *, where='pre', **kwargs)

        This is just a thin wrapper around `.plot` which changes some
        formatting options. Most of the concepts and parameters of plot can be
        used here as well.

        .. note::

            This method uses a standard plot with a step drawstyle: The *x*
            values are the reference positions and steps extend left/right/both
            directions depending on *where*.

            For the common case where you know the values and edges of the
            steps, use `~.Axes.stairs` instead.

        Parameters
        ----------
        x : array-like
            1D sequence of x positions. It is assumed, but not checked, that
            it is uniformly increasing.

        y : array-like
            1D sequence of y levels.

        fmt : str, optional
            A format string, e.g. 'g' for a green line. See `.plot` for a more
            detailed description.

            Note: While full format strings are accepted, it is recommended to
            only specify the color. Line styles are currently ignored (use
            the keyword argument *linestyle* instead). Markers are accepted
            and plotted on the given positions, however, this is a rarely
            needed feature for step plots.

        where : {'pre', 'post', 'mid'}, default: 'pre'
            Define where the steps should be placed:

            - 'pre': The y value is continued constantly to the left from
              every *x* position, i.e. the interval ``(x[i-1], x[i]]`` has the
              value ``y[i]``.
            - 'post': The y value is continued constantly to the right from
              every *x* position, i.e. the interval ``[x[i], x[i+1])`` has the
              value ``y[i]``.
            - 'mid': Steps occur half-way between the *x* positions.

        data : indexable object, optional
            An object with labelled data. If given, provide the label names to
            plot in *x* and *y*.

        **kwargs
            Additional parameters are the same as those for `.plot`.

        Returns
        -------
        list of `.Line2D`
            Objects representing the plotted data.
        """
        _api.check_in_list(('pre', 'post', 'mid'), where=where)
        kwargs['drawstyle'] = 'steps-' + where
        return self.plot(x, y, *args, data=data, **kwargs)

    @staticmethod
    def _convert_dx(dx, x0, xconv, convert):
        """
        Small helper to do logic of width conversion flexibly.

        *dx* and *x0* have units, but *xconv* has already been converted
        to unitless (and is an ndarray).  This allows the *dx* to have units
        that are different from *x0*, but are still accepted by the
        ``__add__`` operator of *x0*.
        """

        # x should be an array...
        assert type(xconv) is np.ndarray

        if xconv.size == 0:
            # xconv has already been converted, but maybe empty...
            return convert(dx)

        try:
            # attempt to add the width to x0; this works for
            # datetime+timedelta, for instance

            # only use the first element of x and x0.  This saves
            # having to be sure addition works across the whole
            # vector.  This is particularly an issue if
            # x0 and dx are lists so x0 + dx just concatenates the lists.
            # We can't just cast x0 and dx to numpy arrays because that
            # removes the units from unit packages like `pint` that
            # wrap numpy arrays.
            try:
                x0 = cbook._safe_first_finite(x0)
            except (TypeError, IndexError, KeyError):
                pass

            try:
                x = cbook._safe_first_finite(xconv)
            except (TypeError, IndexError, KeyError):
                x = xconv

            delist = False
            if not np.iterable(dx):
                dx = [dx]
                delist = True
            dx = [convert(x0 + ddx) - x for ddx in dx]
            if delist:
                dx = dx[0]
        except (ValueError, TypeError, AttributeError):
            # if the above fails (for any reason) just fallback to what
            # we do by default and convert dx by itself.
            dx = convert(dx)
        return dx

    def _parse_bar_color_args(self, kwargs):
        """
        Helper function to process color-related arguments of `.Axes.bar`.

        Argument precedence for facecolors:

        - kwargs['facecolor']
        - kwargs['color']
        - 'Result of ``self._get_patches_for_fill.get_next_color``

        Argument precedence for edgecolors:

        - kwargs['edgecolor']
        - None

        Parameters
        ----------
        self : Axes

        kwargs : dict
            Additional kwargs. If these keys exist, we pop and process them:
            'facecolor', 'edgecolor', 'color'
            Note: The dict is modified by this function.


        Returns
        -------
        facecolor
            The facecolor. One or more colors as (N, 4) rgba array.
        edgecolor
            The edgecolor. Not normalized; may be any valid color spec or None.
        """
        color = kwargs.pop('color', None)

        facecolor = kwargs.pop('facecolor', color)
        edgecolor = kwargs.pop('edgecolor', None)

        facecolor = (facecolor if facecolor is not None
                     else self._get_patches_for_fill.get_next_color())

        try:
            facecolor = mcolors.to_rgba_array(facecolor)
        except ValueError as err:
            raise ValueError(
                "'facecolor' or 'color' argument must be a valid color or"
                    "sequence of colors."
            ) from err

        return facecolor, edgecolor

    @_preprocess_data()
    @_docstring.interpd
    def bar(self, x, height, width=0.8, bottom=None, *, align="center",
            **kwargs):
        r"""
        Make a bar plot.

        The bars are positioned at *x* with the given *align*\ment. Their
        dimensions are given by *height* and *width*. The vertical baseline
        is *bottom* (default 0).

        Many parameters can take either a single value applying to all bars
        or a sequence of values, one for each bar.

        Parameters
        ----------
        x : float or array-like
            The x coordinates of the bars. See also *align* for the
            alignment of the bars to the coordinates.

            Bars are often used for categorical data, i.e. string labels below
            the bars. You can provide a list of strings directly to *x*.
            ``bar(['A', 'B', 'C'], [1, 2, 3])`` is often a shorter and more
            convenient notation compared to
            ``bar(range(3), [1, 2, 3], tick_label=['A', 'B', 'C'])``. They are
            equivalent as long as the names are unique. The explicit *tick_label*
            notation draws the names in the sequence given. However, when having
            duplicate values in categorical *x* data, these values map to the same
            numerical x coordinate, and hence the corresponding bars are drawn on
            top of each other.

        height : float or array-like
            The height(s) of the bars.

            Note that if *bottom* has units (e.g. datetime), *height* should be in
            units that are a difference from the value of *bottom* (e.g. timedelta).

        width : float or array-like, default: 0.8
            The width(s) of the bars.

            Note that if *x* has units (e.g. datetime), then *width* should be in
            units that are a difference (e.g. timedelta) around the *x* values.

        bottom : float or array-like, default: 0
            The y coordinate(s) of the bottom side(s) of the bars.

            Note that if *bottom* has units, then the y-axis will get a Locator and
            Formatter appropriate for the units (e.g. dates, or categorical).

        align : {'center', 'edge'}, default: 'center'
            Alignment of the bars to the *x* coordinates:

            - 'center': Center the base on the *x* positions.
            - 'edge': Align the left edges of the bars with the *x* positions.

            To align the bars on the right edge pass a negative *width* and
            ``align='edge'``.

        Returns
        -------
        `.BarContainer`
            Container with all the bars and optionally errorbars.

        Other Parameters
        ----------------
        color : :mpltype:`color` or list of :mpltype:`color`, optional
            The colors of the bar faces. This is an alias for *facecolor*.
            If both are given, *facecolor* takes precedence.

        facecolor : :mpltype:`color` or list of :mpltype:`color`, optional
            The colors of the bar faces.
            If both *color* and *facecolor are given, *facecolor* takes precedence.

        edgecolor : :mpltype:`color` or list of :mpltype:`color`, optional
            The colors of the bar edges.

        linewidth : float or array-like, optional
            Width of the bar edge(s). If 0, don't draw edges.

        tick_label : str or list of str, optional
            The tick labels of the bars.
            Default: None (Use default numeric labels.)

        label : str or list of str, optional
            A single label is attached to the resulting `.BarContainer` as a
            label for the whole dataset.
            If a list is provided, it must be the same length as *x* and
            labels the individual bars. Repeated labels are not de-duplicated
            and will cause repeated label entries, so this is best used when
            bars also differ in style (e.g., by passing a list to *color*.)

        xerr, yerr : float or array-like of shape(N,) or shape(2, N), optional
            If not *None*, add horizontal / vertical errorbars to the bar tips.
            The values are +/- sizes relative to the data:

            - scalar: symmetric +/- values for all bars
            - shape(N,): symmetric +/- values for each bar
            - shape(2, N): Separate - and + values for each bar. First row
              contains the lower errors, the second row contains the upper
              errors.
            - *None*: No errorbar. (Default)

            See :doc:`/gallery/statistics/errorbar_features` for an example on
            the usage of *xerr* and *yerr*.

        ecolor : :mpltype:`color` or list of :mpltype:`color`, default: 'black'
            The line color of the errorbars.

        capsize : float, default: :rc:`errorbar.capsize`
           The length of the error bar caps in points.

        error_kw : dict, optional
            Dictionary of keyword arguments to be passed to the
            `~.Axes.errorbar` method. Values of *ecolor* or *capsize* defined
            here take precedence over the independent keyword arguments.

        log : bool, default: False
            If *True*, set the y-axis to be log scale.

        data : indexable object, optional
            DATA_PARAMETER_PLACEHOLDER

        **kwargs : `.Rectangle` properties

        %(Rectangle:kwdoc)s

        See Also
        --------
        barh : Plot a horizontal bar plot.

        Notes
        -----
        Stacked bars can be achieved by passing individual *bottom* values per
        bar. See :doc:`/gallery/lines_bars_and_markers/bar_stacked`.
        """
        kwargs = cbook.normalize_kwargs(kwargs, mpatches.Patch)
        facecolor, edgecolor = self._parse_bar_color_args(kwargs)

        linewidth = kwargs.pop('linewidth', None)
        hatch = kwargs.pop('hatch', None)

        # Because xerr and yerr will be passed to errorbar, most dimension
        # checking and processing will be left to the errorbar method.
        xerr = kwargs.pop('xerr', None)
        yerr = kwargs.pop('yerr', None)
        error_kw = kwargs.pop('error_kw', None)
        error_kw = {} if error_kw is None else error_kw.copy()
        ezorder = error_kw.pop('zorder', None)
        if ezorder is None:
            ezorder = kwargs.get('zorder', None)
            if ezorder is not None:
                # If using the bar zorder, increment slightly to make sure
                # errorbars are drawn on top of bars
                ezorder += 0.01
        error_kw.setdefault('zorder', ezorder)
        ecolor = kwargs.pop('ecolor', 'k')
        capsize = kwargs.pop('capsize', mpl.rcParams["errorbar.capsize"])
        error_kw.setdefault('ecolor', ecolor)
        error_kw.setdefault('capsize', capsize)

        # The keyword argument *orientation* is used by barh() to defer all
        # logic and drawing to bar(). It is considered internal and is
        # intentionally not mentioned in the docstring.
        orientation = kwargs.pop('orientation', 'vertical')
        _api.check_in_list(['vertical', 'horizontal'], orientation=orientation)
        log = kwargs.pop('log', False)
        label = kwargs.pop('label', '')
        tick_labels = kwargs.pop('tick_label', None)

        y = bottom  # Matches barh call signature.
        if orientation == 'vertical':
            if y is None:
                y = 0
        else:  # horizontal
            if x is None:
                x = 0

        if orientation == 'vertical':
            # It is possible for y (bottom) to contain unit information.
            # However, it is also possible for y=0 for the default and height
            # to contain unit information.  This will prioritize the units of y.
            self._process_unit_info(
                [("x", x), ("y", y), ("y", height)], kwargs, convert=False)
            if log:
                self.set_yscale('log', nonpositive='clip')
        else:  # horizontal
            # It is possible for x (left) to contain unit information.
            # However, it is also possible for x=0 for the default and width
            # to contain unit information.  This will prioritize the units of x.
            self._process_unit_info(
                [("x", x), ("x", width), ("y", y)], kwargs, convert=False)
            if log:
                self.set_xscale('log', nonpositive='clip')

        # lets do some conversions now since some types cannot be
        # subtracted uniformly
        if self.xaxis is not None:
            x0 = x
            x = np.asarray(self.convert_xunits(x))
            width = self._convert_dx(width, x0, x, self.convert_xunits)
            if xerr is not None:
                xerr = self._convert_dx(xerr, x0, x, self.convert_xunits)
        if self.yaxis is not None:
            y0 = y
            y = np.asarray(self.convert_yunits(y))
            height = self._convert_dx(height, y0, y, self.convert_yunits)
            if yerr is not None:
                yerr = self._convert_dx(yerr, y0, y, self.convert_yunits)

        x, height, width, y, linewidth, hatch = np.broadcast_arrays(
            # Make args iterable too.
            np.atleast_1d(x), height, width, y, linewidth, hatch)

        # Now that units have been converted, set the tick locations.
        if orientation == 'vertical':
            tick_label_axis = self.xaxis
            tick_label_position = x
        else:  # horizontal
            tick_label_axis = self.yaxis
            tick_label_position = y

        if not isinstance(label, str) and np.iterable(label):
            bar_container_label = '_nolegend_'
            patch_labels = label
        else:
            bar_container_label = label
            patch_labels = ['_nolegend_'] * len(x)
        if len(patch_labels) != len(x):
            raise ValueError(f'number of labels ({len(patch_labels)}) '
                             f'does not match number of bars ({len(x)}).')

        linewidth = itertools.cycle(np.atleast_1d(linewidth))
        hatch = itertools.cycle(np.atleast_1d(hatch))
        facecolor = itertools.chain(itertools.cycle(facecolor),
                                    # Fallback if color == "none".
                                    itertools.repeat('none'))
        if edgecolor is None:
            edgecolor = itertools.repeat(None)
        else:
            edgecolor = itertools.chain(
                itertools.cycle(mcolors.to_rgba_array(edgecolor)),
                # Fallback if edgecolor == "none".
                itertools.repeat('none'))

        # We will now resolve the alignment and really have
        # left, bottom, width, height vectors
        _api.check_in_list(['center', 'edge'], align=align)
        if align == 'center':
            if orientation == 'vertical':
                try:
                    left = x - width / 2
                except TypeError as e:
                    raise TypeError(f'the dtypes of parameters x ({x.dtype}) '
                                    f'and width ({width.dtype}) '
                                    f'are incompatible') from e
                bottom = y
            else:  # horizontal
                try:
                    bottom = y - height / 2
                except TypeError as e:
                    raise TypeError(f'the dtypes of parameters y ({y.dtype}) '
                                    f'and height ({height.dtype}) '
                                    f'are incompatible') from e
                left = x
        else:  # edge
            left = x
            bottom = y

        patches = []
        args = zip(left, bottom, width, height, facecolor, edgecolor, linewidth,
                   hatch, patch_labels)
        for l, b, w, h, c, e, lw, htch, lbl in args:
            r = mpatches.Rectangle(
                xy=(l, b), width=w, height=h,
                facecolor=c,
                edgecolor=e,
                linewidth=lw,
                label=lbl,
                hatch=htch,
                )
            r._internal_update(kwargs)
            r.get_path()._interpolation_steps = 100
            if orientation == 'vertical':
                r.sticky_edges.y.append(b)
            else:  # horizontal
                r.sticky_edges.x.append(l)
            self.add_patch(r)
            patches.append(r)

        if xerr is not None or yerr is not None:
            if orientation == 'vertical':
                # using list comps rather than arrays to preserve unit info
                ex = [l + 0.5 * w for l, w in zip(left, width)]
                ey = [b + h for b, h in zip(bottom, height)]

            else:  # horizontal
                # using list comps rather than arrays to preserve unit info
                ex = [l + w for l, w in zip(left, width)]
                ey = [b + 0.5 * h for b, h in zip(bottom, height)]

            error_kw.setdefault("label", '_nolegend_')

            errorbar = self.errorbar(ex, ey, yerr=yerr, xerr=xerr, fmt='none',
                                     **error_kw)
        else:
            errorbar = None

        self._request_autoscale_view()

        if orientation == 'vertical':
            datavalues = height
        else:  # horizontal
            datavalues = width

        bar_container = BarContainer(patches, errorbar, datavalues=datavalues,
                                     orientation=orientation,
                                     label=bar_container_label)
        self.add_container(bar_container)

        if tick_labels is not None:
            tick_labels = np.broadcast_to(tick_labels, len(patches))
            tick_label_axis.set_ticks(tick_label_position)
            tick_label_axis.set_ticklabels(tick_labels)

        return bar_container

    # @_preprocess_data() # let 'bar' do the unpacking..
    @_docstring.interpd
    def barh(self, y, width, height=0.8, left=None, *, align="center",
             data=None, **kwargs):
        r"""
        Make a horizontal bar plot.

        The bars are positioned at *y* with the given *align*\ment. Their
        dimensions are given by *width* and *height*. The horizontal baseline
        is *left* (default 0).

        Many parameters can take either a single value applying to all bars
        or a sequence of values, one for each bar.

        Parameters
        ----------
        y : float or array-like
            The y coordinates of the bars. See also *align* for the
            alignment of the bars to the coordinates.

            Bars are often used for categorical data, i.e. string labels below
            the bars. You can provide a list of strings directly to *y*.
            ``barh(['A', 'B', 'C'], [1, 2, 3])`` is often a shorter and more
            convenient notation compared to
            ``barh(range(3), [1, 2, 3], tick_label=['A', 'B', 'C'])``. They are
            equivalent as long as the names are unique. The explicit *tick_label*
            notation draws the names in the sequence given. However, when having
            duplicate values in categorical *y* data, these values map to the same
            numerical y coordinate, and hence the corresponding bars are drawn on
            top of each other.

        width : float or array-like
            The width(s) of the bars.

            Note that if *left* has units (e.g. datetime), *width* should be in
            units that are a difference from the value of *left* (e.g. timedelta).

        height : float or array-like, default: 0.8
            The heights of the bars.

            Note that if *y* has units (e.g. datetime), then *height* should be in
            units that are a difference (e.g. timedelta) around the *y* values.

        left : float or array-like, default: 0
            The x coordinates of the left side(s) of the bars.

            Note that if *left* has units, then the x-axis will get a Locator and
            Formatter appropriate for the units (e.g. dates, or categorical).

        align : {'center', 'edge'}, default: 'center'
            Alignment of the base to the *y* coordinates*:

            - 'center': Center the bars on the *y* positions.
            - 'edge': Align the bottom edges of the bars with the *y*
              positions.

            To align the bars on the top edge pass a negative *height* and
            ``align='edge'``.

        Returns
        -------
        `.BarContainer`
            Container with all the bars and optionally errorbars.

        Other Parameters
        ----------------
        color : :mpltype:`color` or list of :mpltype:`color`, optional
            The colors of the bar faces.

        edgecolor : :mpltype:`color` or list of :mpltype:`color`, optional
            The colors of the bar edges.

        linewidth : float or array-like, optional
            Width of the bar edge(s). If 0, don't draw edges.

        tick_label : str or list of str, optional
            The tick labels of the bars.
            Default: None (Use default numeric labels.)

        label : str or list of str, optional
            A single label is attached to the resulting `.BarContainer` as a
            label for the whole dataset.
            If a list is provided, it must be the same length as *y* and
            labels the individual bars. Repeated labels are not de-duplicated
            and will cause repeated label entries, so this is best used when
            bars also differ in style (e.g., by passing a list to *color*.)

        xerr, yerr : float or array-like of shape(N,) or shape(2, N), optional
            If not *None*, add horizontal / vertical errorbars to the bar tips.
            The values are +/- sizes relative to the data:

            - scalar: symmetric +/- values for all bars
            - shape(N,): symmetric +/- values for each bar
            - shape(2, N): Separate - and + values for each bar. First row
              contains the lower errors, the second row contains the upper
              errors.
            - *None*: No errorbar. (default)

            See :doc:`/gallery/statistics/errorbar_features` for an example on
            the usage of *xerr* and *yerr*.

        ecolor : :mpltype:`color` or list of :mpltype:`color`, default: 'black'
            The line color of the errorbars.

        capsize : float, default: :rc:`errorbar.capsize`
           The length of the error bar caps in points.

        error_kw : dict, optional
            Dictionary of keyword arguments to be passed to the
            `~.Axes.errorbar` method. Values of *ecolor* or *capsize* defined
            here take precedence over the independent keyword arguments.

        log : bool, default: False
            If ``True``, set the x-axis to be log scale.

        data : indexable object, optional
            If given, all parameters also accept a string ``s``, which is
            interpreted as ``data[s]`` if  ``s`` is a key in ``data``.

        **kwargs : `.Rectangle` properties

        %(Rectangle:kwdoc)s

        See Also
        --------
        bar : Plot a vertical bar plot.

        Notes
        -----
        Stacked bars can be achieved by passing individual *left* values per
        bar. See
        :doc:`/gallery/lines_bars_and_markers/horizontal_barchart_distribution`.
        """
        kwargs.setdefault('orientation', 'horizontal')
        patches = self.bar(x=left, height=height, width=width, bottom=y,
                           align=align, data=data, **kwargs)
        return patches

    def bar_label(self, container, labels=None, *, fmt="%g", label_type="edge",
                  padding=0, **kwargs):
        """
        Label a bar plot.

        Adds labels to bars in the given `.BarContainer`.
        You may need to adjust the axis limits to fit the labels.

        Parameters
        ----------
        container : `.BarContainer`
            Container with all the bars and optionally errorbars, likely
            returned from `.bar` or `.barh`.

        labels : array-like, optional
            A list of label texts, that should be displayed. If not given, the
            label texts will be the data values formatted with *fmt*.

        fmt : str or callable, default: '%g'
            An unnamed %-style or {}-style format string for the label or a
            function to call with the value as the first argument.
            When *fmt* is a string and can be interpreted in both formats,
            %-style takes precedence over {}-style.

            .. versionadded:: 3.7
               Support for {}-style format string and callables.

        label_type : {'edge', 'center'}, default: 'edge'
            The label type. Possible values:

            - 'edge': label placed at the end-point of the bar segment, and the
              value displayed will be the position of that end-point.
            - 'center': label placed in the center of the bar segment, and the
              value displayed will be the length of that segment.
              (useful for stacked bars, i.e.,
              :doc:`/gallery/lines_bars_and_markers/bar_label_demo`)

        padding : float, default: 0
            Distance of label from the end of the bar, in points.

        **kwargs
            Any remaining keyword arguments are passed through to
            `.Axes.annotate`. The alignment parameters (
            *horizontalalignment* / *ha*, *verticalalignment* / *va*) are
            not supported because the labels are automatically aligned to
            the bars.

        Returns
        -------
        list of `.Annotation`
            A list of `.Annotation` instances for the labels.
        """
        for key in ['horizontalalignment', 'ha', 'verticalalignment', 'va']:
            if key in kwargs:
                raise ValueError(
                    f"Passing {key!r} to bar_label() is not supported.")

        a, b = self.yaxis.get_view_interval()
        y_inverted = a > b
        c, d = self.xaxis.get_view_interval()
        x_inverted = c > d

        # want to know whether to put label on positive or negative direction
        # cannot use np.sign here because it will return 0 if x == 0
        def sign(x):
            return 1 if x >= 0 else -1

        _api.check_in_list(['edge', 'center'], label_type=label_type)

        bars = container.patches
        errorbar = container.errorbar
        datavalues = container.datavalues
        orientation = container.orientation

        if errorbar:
            # check "ErrorbarContainer" for the definition of these elements
            lines = errorbar.lines  # attribute of "ErrorbarContainer" (tuple)
            barlinecols = lines[2]  # 0: data_line, 1: caplines, 2: barlinecols
            barlinecol = barlinecols[0]  # the "LineCollection" of error bars
            errs = barlinecol.get_segments()
        else:
            errs = []

        if labels is None:
            labels = []

        annotations = []

        for bar, err, dat, lbl in itertools.zip_longest(
                bars, errs, datavalues, labels
        ):
            (x0, y0), (x1, y1) = bar.get_bbox().get_points()
            xc, yc = (x0 + x1) / 2, (y0 + y1) / 2

            if orientation == "vertical":
                extrema = max(y0, y1) if dat >= 0 else min(y0, y1)
                length = abs(y0 - y1)
            else:  # horizontal
                extrema = max(x0, x1) if dat >= 0 else min(x0, x1)
                length = abs(x0 - x1)

            if err is None or np.size(err) == 0:
                endpt = extrema
            elif orientation == "vertical":
                endpt = err[:, 1].max() if dat >= 0 else err[:, 1].min()
            else:  # horizontal
                endpt = err[:, 0].max() if dat >= 0 else err[:, 0].min()

            if label_type == "center":
                value = sign(dat) * length
            else:  # edge
                value = extrema

            if label_type == "center":
                xy = (0.5, 0.5)
                kwargs["xycoords"] = (
                    lambda r, b=bar:
                        mtransforms.Bbox.intersection(
                            b.get_window_extent(r), b.get_clip_box()
                        ) or mtransforms.Bbox.null()
                )
            else:  # edge
                if orientation == "vertical":
                    xy = xc, endpt
                else:  # horizontal
                    xy = endpt, yc

            if orientation == "vertical":
                y_direction = -1 if y_inverted else 1
                xytext = 0, y_direction * sign(dat) * padding
            else:  # horizontal
                x_direction = -1 if x_inverted else 1
                xytext = x_direction * sign(dat) * padding, 0

            if label_type == "center":
                ha, va = "center", "center"
            else:  # edge
                if orientation == "vertical":
                    ha = 'center'
                    if y_inverted:
                        va = 'top' if dat > 0 else 'bottom'  # also handles NaN
                    else:
                        va = 'top' if dat < 0 else 'bottom'  # also handles NaN
                else:  # horizontal
                    if x_inverted:
                        ha = 'right' if dat > 0 else 'left'  # also handles NaN
                    else:
                        ha = 'right' if dat < 0 else 'left'  # also handles NaN
                    va = 'center'

            if np.isnan(dat):
                lbl = ''

            if lbl is None:
                if isinstance(fmt, str):
                    lbl = cbook._auto_format_str(fmt, value)
                elif callable(fmt):
                    lbl = fmt(value)
                else:
                    raise TypeError("fmt must be a str or callable")
            annotation = self.annotate(lbl,
                                       xy, xytext, textcoords="offset points",
                                       ha=ha, va=va, **kwargs)
            annotations.append(annotation)

        return annotations

    @_preprocess_data()
    @_docstring.interpd
    def broken_barh(self, xranges, yrange, **kwargs):
        """
        Plot a horizontal sequence of rectangles.

        A rectangle is drawn for each element of *xranges*. All rectangles
        have the same vertical position and size defined by *yrange*.

        Parameters
        ----------
        xranges : sequence of tuples (*xmin*, *xwidth*)
            The x-positions and extents of the rectangles. For each tuple
            (*xmin*, *xwidth*) a rectangle is drawn from *xmin* to *xmin* +
            *xwidth*.
        yrange : (*ymin*, *yheight*)
            The y-position and extent for all the rectangles.

        Returns
        -------
        `~.collections.PolyCollection`

        Other Parameters
        ----------------
        data : indexable object, optional
            DATA_PARAMETER_PLACEHOLDER
        **kwargs : `.PolyCollection` properties

            Each *kwarg* can be either a single argument applying to all
            rectangles, e.g.::

                facecolors='black'

            or a sequence of arguments over which is cycled, e.g.::

                facecolors=('black', 'blue')

            would create interleaving black and blue rectangles.

            Supported keywords:

            %(PolyCollection:kwdoc)s
        """
        # process the unit information
        xdata = cbook._safe_first_finite(xranges) if len(xranges) else None
        ydata = cbook._safe_first_finite(yrange) if len(yrange) else None
        self._process_unit_info(
            [("x", xdata), ("y", ydata)], kwargs, convert=False)

        vertices = []
        y0, dy = yrange
        y0, y1 = self.convert_yunits((y0, y0 + dy))
        for xr in xranges:  # convert the absolute values, not the x and dx
            try:
                x0, dx = xr
            except Exception:
                raise ValueError(
                    "each range in xrange must be a sequence with two "
                    "elements (i.e. xrange must be an (N, 2) array)") from None
            x0, x1 = self.convert_xunits((x0, x0 + dx))
            vertices.append([(x0, y0), (x0, y1), (x1, y1), (x1, y0)])

        col = mcoll.PolyCollection(np.array(vertices), **kwargs)
        self.add_collection(col, autolim=True)
        self._request_autoscale_view()

        return col

    @_preprocess_data()
    def stem(self, *args, linefmt=None, markerfmt=None, basefmt=None, bottom=0,
             label=None, orientation='vertical'):
        """
        Create a stem plot.

        A stem plot draws lines perpendicular to a baseline at each location
        *locs* from the baseline to *heads*, and places a marker there. For
        vertical stem plots (the default), the *locs* are *x* positions, and
        the *heads* are *y* values. For horizontal stem plots, the *locs* are
        *y* positions, and the *heads* are *x* values.

        Call signature::

          stem([locs,] heads, linefmt=None, markerfmt=None, basefmt=None)

        The *locs*-positions are optional. *linefmt* may be provided as
        positional, but all other formats must be provided as keyword
        arguments.

        Parameters
        ----------
        locs : array-like, default: (0, 1, ..., len(heads) - 1)
            For vertical stem plots, the x-positions of the stems.
            For horizontal stem plots, the y-positions of the stems.

        heads : array-like
            For vertical stem plots, the y-values of the stem heads.
            For horizontal stem plots, the x-values of the stem heads.

        linefmt : str, optional
            A string defining the color and/or linestyle of the vertical lines:

            =========  =============
            Character  Line Style
            =========  =============
            ``'-'``    solid line
            ``'--'``   dashed line
            ``'-.'``   dash-dot line
            ``':'``    dotted line
            =========  =============

            Default: 'C0-', i.e. solid line with the first color of the color
            cycle.

            Note: Markers specified through this parameter (e.g. 'x') will be
            silently ignored. Instead, markers should be specified using
            *markerfmt*.

        markerfmt : str, optional
            A string defining the color and/or shape of the markers at the stem
            heads. If the marker is not given, use the marker 'o', i.e. filled
            circles. If the color is not given, use the color from *linefmt*.

        basefmt : str, default: 'C3-' ('C2-' in classic mode)
            A format string defining the properties of the baseline.

        orientation : {'vertical', 'horizontal'}, default: 'vertical'
            The orientation of the stems.

        bottom : float, default: 0
            The y/x-position of the baseline (depending on *orientation*).

        label : str, optional
            The label to use for the stems in legends.

        data : indexable object, optional
            DATA_PARAMETER_PLACEHOLDER

        Returns
        -------
        `.StemContainer`
            The container may be treated like a tuple
            (*markerline*, *stemlines*, *baseline*)

        Notes
        -----
        .. seealso::
            The MATLAB function
            `stem <https://www.mathworks.com/help/matlab/ref/stem.html>`_
            which inspired this method.
        """
        if not 1 <= len(args) <= 3:
            raise _api.nargs_error('stem', '1-3', len(args))
        _api.check_in_list(['horizontal', 'vertical'], orientation=orientation)

        if len(args) == 1:
            heads, = args
            locs = np.arange(len(heads))
            args = ()
        elif isinstance(args[1], str):
            heads, *args = args
            locs = np.arange(len(heads))
        else:
            locs, heads, *args = args

        if orientation == 'vertical':
            locs, heads = self._process_unit_info([("x", locs), ("y", heads)])
        else:  # horizontal
            heads, locs = self._process_unit_info([("x", heads), ("y", locs)])

        # resolve line format
        if linefmt is None:
            linefmt = args[0] if len(args) > 0 else "C0-"
        linestyle, linemarker, linecolor = _process_plot_format(linefmt)

        # resolve marker format
        if markerfmt is None:
            # if not given as kwarg, fall back to 'o'
            markerfmt = "o"
        if markerfmt == '':
            markerfmt = ' '  # = empty line style; '' would resolve rcParams
        markerstyle, markermarker, markercolor = \
            _process_plot_format(markerfmt)
        if markermarker is None:
            markermarker = 'o'
        if markerstyle is None:
            markerstyle = 'None'
        if markercolor is None:
            markercolor = linecolor

        # resolve baseline format
        if basefmt is None:
            basefmt = ("C2-" if mpl.rcParams["_internal.classic_mode"] else
                       "C3-")
        basestyle, basemarker, basecolor = _process_plot_format(basefmt)

        # New behaviour in 3.1 is to use a LineCollection for the stemlines
        if linestyle is None:
            linestyle = mpl.rcParams['lines.linestyle']
        xlines = self.vlines if orientation == "vertical" else self.hlines
        stemlines = xlines(
            locs, bottom, heads,
            colors=linecolor, linestyles=linestyle, label="_nolegend_")

        if orientation == 'horizontal':
            marker_x = heads
            marker_y = locs
            baseline_x = [bottom, bottom]
            baseline_y = [np.min(locs), np.max(locs)]
        else:
            marker_x = locs
            marker_y = heads
            baseline_x = [np.min(locs), np.max(locs)]
            baseline_y = [bottom, bottom]

        markerline, = self.plot(marker_x, marker_y,
                                color=markercolor, linestyle=markerstyle,
                                marker=markermarker, label="_nolegend_")

        baseline, = self.plot(baseline_x, baseline_y,
                              color=basecolor, linestyle=basestyle,
                              marker=basemarker, label="_nolegend_")

        stem_container = StemContainer((markerline, stemlines, baseline),
                                       label=label)
        self.add_container(stem_container)
        return stem_container

    @_api.make_keyword_only("3.10", "explode")
    @_preprocess_data(replace_names=["x", "explode", "labels", "colors"])
    def pie(self, x, explode=None, labels=None, colors=None,
            autopct=None, pctdistance=0.6, shadow=False, labeldistance=1.1,
            startangle=0, radius=1, counterclock=True,
            wedgeprops=None, textprops=None, center=(0, 0),
            frame=False, rotatelabels=False, *, normalize=True, hatch=None):
        """
        Plot a pie chart.

        Make a pie chart of array *x*.  The fractional area of each wedge is
        given by ``x/sum(x)``.

        The wedges are plotted counterclockwise, by default starting from the
        x-axis.

        Parameters
        ----------
        x : 1D array-like
            The wedge sizes.

        explode : array-like, default: None
            If not *None*, is a ``len(x)`` array which specifies the fraction
            of the radius with which to offset each wedge.

        labels : list, default: None
            A sequence of strings providing the labels for each wedge

        colors : :mpltype:`color` or list of :mpltype:`color`, default: None
            A sequence of colors through which the pie chart will cycle.  If
            *None*, will use the colors in the currently active cycle.

        hatch : str or list, default: None
            Hatching pattern applied to all pie wedges or sequence of patterns
            through which the chart will cycle. For a list of valid patterns,
            see :doc:`/gallery/shapes_and_collections/hatch_style_reference`.

            .. versionadded:: 3.7

        autopct : None or str or callable, default: None
            If not *None*, *autopct* is a string or function used to label the
            wedges with their numeric value. The label will be placed inside
            the wedge. If *autopct* is a format string, the label will be
            ``fmt % pct``. If *autopct* is a function, then it will be called.

        pctdistance : float, default: 0.6
            The relative distance along the radius at which the text
            generated by *autopct* is drawn. To draw the text outside the pie,
            set *pctdistance* > 1. This parameter is ignored if *autopct* is
            ``None``.

        labeldistance : float or None, default: 1.1
            The relative distance along the radius at which the labels are
            drawn. To draw the labels inside the pie, set  *labeldistance* < 1.
            If set to ``None``, labels are not drawn but are still stored for
            use in `.legend`.

        shadow : bool or dict, default: False
            If bool, whether to draw a shadow beneath the pie. If dict, draw a shadow
            passing the properties in the dict to `.Shadow`.

            .. versionadded:: 3.8
                *shadow* can be a dict.

        startangle : float, default: 0 degrees
            The angle by which the start of the pie is rotated,
            counterclockwise from the x-axis.

        radius : float, default: 1
            The radius of the pie.

        counterclock : bool, default: True
            Specify fractions direction, clockwise or counterclockwise.

        wedgeprops : dict, default: None
            Dict of arguments passed to each `.patches.Wedge` of the pie.
            For example, ``wedgeprops = {'linewidth': 3}`` sets the width of
            the wedge border lines equal to 3. By default, ``clip_on=False``.
            When there is a conflict between these properties and other
            keywords, properties passed to *wedgeprops* take precedence.

        textprops : dict, default: None
            Dict of arguments to pass to the text objects.

        center : (float, float), default: (0, 0)
            The coordinates of the center of the chart.

        frame : bool, default: False
            Plot Axes frame with the chart if true.

        rotatelabels : bool, default: False
            Rotate each label to the angle of the corresponding slice if true.

        normalize : bool, default: True
            When *True*, always make a full pie by normalizing x so that
            ``sum(x) == 1``. *False* makes a partial pie if ``sum(x) <= 1``
            and raises a `ValueError` for ``sum(x) > 1``.

        data : indexable object, optional
            DATA_PARAMETER_PLACEHOLDER

        Returns
        -------
        patches : list
            A sequence of `matplotlib.patches.Wedge` instances

        texts : list
            A list of the label `.Text` instances.

        autotexts : list
            A list of `.Text` instances for the numeric labels. This will only
            be returned if the parameter *autopct* is not *None*.

        Notes
        -----
        The pie chart will probably look best if the figure and Axes are
        square, or the Axes aspect is equal.
        This method sets the aspect ratio of the axis to "equal".
        The Axes aspect ratio can be controlled with `.Axes.set_aspect`.
        """
        self.set_aspect('equal')
        # The use of float32 is "historical", but can't be changed without
        # regenerating the test baselines.
        x = np.asarray(x, np.float32)
        if x.ndim > 1:
            raise ValueError("x must be 1D")

        if np.any(x < 0):
            raise ValueError("Wedge sizes 'x' must be non negative values")

        sx = x.sum()

        if normalize:
            x = x / sx
        elif sx > 1:
            raise ValueError('Cannot plot an unnormalized pie with sum(x) > 1')
        if labels is None:
            labels = [''] * len(x)
        if explode is None:
            explode = [0] * len(x)
        if len(x) != len(labels):
            raise ValueError(f"'labels' must be of length 'x', not {len(labels)}")
        if len(x) != len(explode):
            raise ValueError(f"'explode' must be of length 'x', not {len(explode)}")
        if colors is None:
            get_next_color = self._get_patches_for_fill.get_next_color
        else:
            color_cycle = itertools.cycle(colors)

            def get_next_color():
                return next(color_cycle)

        hatch_cycle = itertools.cycle(np.atleast_1d(hatch))

        _api.check_isinstance(Real, radius=radius, startangle=startangle)
        if radius <= 0:
            raise ValueError(f"'radius' must be a positive number, not {radius}")

        # Starting theta1 is the start fraction of the circle
        theta1 = startangle / 360

        if wedgeprops is None:
            wedgeprops = {}
        if textprops is None:
            textprops = {}

        texts = []
        slices = []
        autotexts = []

        for frac, label, expl in zip(x, labels, explode):
            x, y = center
            theta2 = (theta1 + frac) if counterclock else (theta1 - frac)
            thetam = 2 * np.pi * 0.5 * (theta1 + theta2)
            x += expl * math.cos(thetam)
            y += expl * math.sin(thetam)

            w = mpatches.Wedge((x, y), radius, 360. * min(theta1, theta2),
                               360. * max(theta1, theta2),
                               facecolor=get_next_color(),
                               hatch=next(hatch_cycle),
                               clip_on=False,
                               label=label)
            w.set(**wedgeprops)
            slices.append(w)
            self.add_patch(w)

            if shadow:
                # Make sure to add a shadow after the call to add_patch so the
                # figure and transform props will be set.
                shadow_dict = {'ox': -0.02, 'oy': -0.02, 'label': '_nolegend_'}
                if isinstance(shadow, dict):
                    shadow_dict.update(shadow)
                self.add_patch(mpatches.Shadow(w, **shadow_dict))

            if labeldistance is not None:
                xt = x + labeldistance * radius * math.cos(thetam)
                yt = y + labeldistance * radius * math.sin(thetam)
                label_alignment_h = 'left' if xt > 0 else 'right'
                label_alignment_v = 'center'
                label_rotation = 'horizontal'
                if rotatelabels:
                    label_alignment_v = 'bottom' if yt > 0 else 'top'
                    label_rotation = (np.rad2deg(thetam)
                                      + (0 if xt > 0 else 180))
                t = self.text(xt, yt, label,
                              clip_on=False,
                              horizontalalignment=label_alignment_h,
                              verticalalignment=label_alignment_v,
                              rotation=label_rotation,
                              size=mpl.rcParams['xtick.labelsize'])
                t.set(**textprops)
                texts.append(t)

            if autopct is not None:
                xt = x + pctdistance * radius * math.cos(thetam)
                yt = y + pctdistance * radius * math.sin(thetam)
                if isinstance(autopct, str):
                    s = autopct % (100. * frac)
                elif callable(autopct):
                    s = autopct(100. * frac)
                else:
                    raise TypeError(
                        'autopct must be callable or a format string')
                if mpl._val_or_rc(textprops.get("usetex"), "text.usetex"):
                    # escape % (i.e. \%) if it is not already escaped
                    s = re.sub(r"([^\\])%", r"\1\\%", s)
                t = self.text(xt, yt, s,
                              clip_on=False,
                              horizontalalignment='center',
                              verticalalignment='center')
                t.set(**textprops)
                autotexts.append(t)

            theta1 = theta2

        if frame:
            self._request_autoscale_view()
        else:
            self.set(frame_on=False, xticks=[], yticks=[],
                     xlim=(-1.25 + center[0], 1.25 + center[0]),
                     ylim=(-1.25 + center[1], 1.25 + center[1]))

        if autopct is None:
            return slices, texts
        else:
            return slices, texts, autotexts

    @staticmethod
    def _errorevery_to_mask(x, errorevery):
        """
        Normalize `errorbar`'s *errorevery* to be a boolean mask for data *x*.

        This function is split out to be usable both by 2D and 3D errorbars.
        """
        if isinstance(errorevery, Integral):
            errorevery = (0, errorevery)
        if isinstance(errorevery, tuple):
            if (len(errorevery) == 2 and
                    isinstance(errorevery[0], Integral) and
                    isinstance(errorevery[1], Integral)):
                errorevery = slice(errorevery[0], None, errorevery[1])
            else:
                raise ValueError(
                    f'{errorevery=!r} is a not a tuple of two integers')
        elif isinstance(errorevery, slice):
            pass
        elif not isinstance(errorevery, str) and np.iterable(errorevery):
            try:
                x[errorevery]  # fancy indexing
            except (ValueError, IndexError) as err:
                raise ValueError(
                    f"{errorevery=!r} is iterable but not a valid NumPy fancy "
                    "index to match 'xerr'/'yerr'") from err
        else:
            raise ValueError(f"{errorevery=!r} is not a recognized value")
        everymask = np.zeros(len(x), bool)
        everymask[errorevery] = True
        return everymask

    @_api.make_keyword_only("3.10", "ecolor")
    @_preprocess_data(replace_names=["x", "y", "xerr", "yerr"],
                      label_namer="y")
    @_docstring.interpd
    def errorbar(self, x, y, yerr=None, xerr=None,
                 fmt='', ecolor=None, elinewidth=None, capsize=None,
                 barsabove=False, lolims=False, uplims=False,
                 xlolims=False, xuplims=False, errorevery=1, capthick=None,
                 **kwargs):
        """
        Plot y versus x as lines and/or markers with attached errorbars.

        *x*, *y* define the data locations, *xerr*, *yerr* define the errorbar
        sizes. By default, this draws the data markers/lines as well as the
        errorbars. Use fmt='none' to draw errorbars without any data markers.

        .. versionadded:: 3.7
           Caps and error lines are drawn in polar coordinates on polar plots.


        Parameters
        ----------
        x, y : float or array-like
            The data positions.

        xerr, yerr : float or array-like, shape(N,) or shape(2, N), optional
            The errorbar sizes:

            - scalar: Symmetric +/- values for all data points.
            - shape(N,): Symmetric +/-values for each data point.
            - shape(2, N): Separate - and + values for each bar. First row
              contains the lower errors, the second row contains the upper
              errors.
            - *None*: No errorbar.

            All values must be >= 0.

            See :doc:`/gallery/statistics/errorbar_features`
            for an example on the usage of ``xerr`` and ``yerr``.

        fmt : str, default: ''
            The format for the data points / data lines. See `.plot` for
            details.

            Use 'none' (case-insensitive) to plot errorbars without any data
            markers.

        ecolor : :mpltype:`color`, default: None
            The color of the errorbar lines.  If None, use the color of the
            line connecting the markers.

        elinewidth : float, default: None
            The linewidth of the errorbar lines. If None, the linewidth of
            the current style is used.

        capsize : float, default: :rc:`errorbar.capsize`
            The length of the error bar caps in points.

        capthick : float, default: None
            An alias to the keyword argument *markeredgewidth* (a.k.a. *mew*).
            This setting is a more sensible name for the property that
            controls the thickness of the error bar cap in points. For
            backwards compatibility, if *mew* or *markeredgewidth* are given,
            then they will over-ride *capthick*. This may change in future
            releases.

        barsabove : bool, default: False
            If True, will plot the errorbars above the plot
            symbols. Default is below.

        lolims, uplims, xlolims, xuplims : bool or array-like, default: False
            These arguments can be used to indicate that a value gives only
            upper/lower limits.  In that case a caret symbol is used to
            indicate this. *lims*-arguments may be scalars, or array-likes of
            the same length as *xerr* and *yerr*.  To use limits with inverted
            axes, `~.Axes.set_xlim` or `~.Axes.set_ylim` must be called before
            :meth:`errorbar`.  Note the tricky parameter names: setting e.g.
            *lolims* to True means that the y-value is a *lower* limit of the
            True value, so, only an *upward*-pointing arrow will be drawn!

        errorevery : int or (int, int), default: 1
            draws error bars on a subset of the data. *errorevery* =N draws
            error bars on the points (x[::N], y[::N]).
            *errorevery* =(start, N) draws error bars on the points
            (x[start::N], y[start::N]). e.g. errorevery=(6, 3)
            adds error bars to the data at (x[6], x[9], x[12], x[15], ...).
            Used to avoid overlapping error bars when two series share x-axis
            values.

        Returns
        -------
        `.ErrorbarContainer`
            The container contains:

            - data_line : A `~matplotlib.lines.Line2D` instance of x, y plot markers
              and/or line.
            - caplines : A tuple of `~matplotlib.lines.Line2D` instances of the error
              bar caps.
            - barlinecols : A tuple of `.LineCollection` with the horizontal and
              vertical error ranges.

        Other Parameters
        ----------------
        data : indexable object, optional
            DATA_PARAMETER_PLACEHOLDER

        **kwargs
            All other keyword arguments are passed on to the `~.Axes.plot` call
            drawing the markers. For example, this code makes big red squares
            with thick green edges::

                x, y, yerr = rand(3, 10)
                errorbar(x, y, yerr, marker='s', mfc='red',
                         mec='green', ms=20, mew=4)

            where *mfc*, *mec*, *ms* and *mew* are aliases for the longer
            property names, *markerfacecolor*, *markeredgecolor*, *markersize*
            and *markeredgewidth*.

            Valid kwargs for the marker properties are:

            - *dashes*
            - *dash_capstyle*
            - *dash_joinstyle*
            - *drawstyle*
            - *fillstyle*
            - *linestyle*
            - *marker*
            - *markeredgecolor*
            - *markeredgewidth*
            - *markerfacecolor*
            - *markerfacecoloralt*
            - *markersize*
            - *markevery*
            - *solid_capstyle*
            - *solid_joinstyle*

            Refer to the corresponding `.Line2D` property for more details:

            %(Line2D:kwdoc)s
        """
        kwargs = cbook.normalize_kwargs(kwargs, mlines.Line2D)
        # Drop anything that comes in as None to use the default instead.
        kwargs = {k: v for k, v in kwargs.items() if v is not None}
        kwargs.setdefault('zorder', 2)

        # Casting to object arrays preserves units.
        if not isinstance(x, np.ndarray):
            x = np.asarray(x, dtype=object)
        if not isinstance(y, np.ndarray):
            y = np.asarray(y, dtype=object)

        def _upcast_err(err):
            """
            Safely handle tuple of containers that carry units.

            This function covers the case where the input to the xerr/yerr is a
            length 2 tuple of equal length ndarray-subclasses that carry the
            unit information in the container.

            If we have a tuple of nested numpy array (subclasses), we defer
            coercing the units to be consistent to the underlying unit
            library (and implicitly the broadcasting).

            Otherwise, fallback to casting to an object array.
            """

            if (
                    # make sure it is not a scalar
                    np.iterable(err) and
                    # and it is not empty
                    len(err) > 0 and
                    # and the first element is an array sub-class use
                    # safe_first_element because getitem is index-first not
                    # location first on pandas objects so err[0] almost always
                    # fails.
                    isinstance(cbook._safe_first_finite(err), np.ndarray)
            ):
                # Get the type of the first element
                atype = type(cbook._safe_first_finite(err))
                # Promote the outer container to match the inner container
                if atype is np.ndarray:
                    # Converts using np.asarray, because data cannot
                    # be directly passed to init of np.ndarray
                    return np.asarray(err, dtype=object)
                # If atype is not np.ndarray, directly pass data to init.
                # This works for types such as unyts and astropy units
                return atype(err)
            # Otherwise wrap it in an object array
            return np.asarray(err, dtype=object)

        if xerr is not None and not isinstance(xerr, np.ndarray):
            xerr = _upcast_err(xerr)
        if yerr is not None and not isinstance(yerr, np.ndarray):
            yerr = _upcast_err(yerr)
        x, y = np.atleast_1d(x, y)  # Make sure all the args are iterable.
        if len(x) != len(y):
            raise ValueError("'x' and 'y' must have the same size")

        everymask = self._errorevery_to_mask(x, errorevery)

        label = kwargs.pop("label", None)
        kwargs['label'] = '_nolegend_'

        # Create the main line and determine overall kwargs for child artists.
        # We avoid calling self.plot() directly, or self._get_lines(), because
        # that would call self._process_unit_info again, and do other indirect
        # data processing.
        (data_line, base_style), = self._get_lines._plot_args(
            self, (x, y) if fmt == '' else (x, y, fmt), kwargs, return_kwargs=True)

        # Do this after creating `data_line` to avoid modifying `base_style`.
        if barsabove:
            data_line.set_zorder(kwargs['zorder'] - .1)
        else:
            data_line.set_zorder(kwargs['zorder'] + .1)

        # Add line to plot, or throw it away and use it to determine kwargs.
        if fmt.lower() != 'none':
            self.add_line(data_line)
        else:
            data_line = None
            # Remove alpha=0 color that _get_lines._plot_args returns for
            # 'none' format, and replace it with user-specified color, if
            # supplied.
            base_style.pop('color')
            if 'color' in kwargs:
                base_style['color'] = kwargs.pop('color')

        if 'color' not in base_style:
            base_style['color'] = 'C0'
        if ecolor is None:
            ecolor = base_style['color']

        # Eject any line-specific information from format string, as it's not
        # needed for bars or caps.
        for key in ['marker', 'markersize', 'markerfacecolor',
                    'markerfacecoloralt',
                    'markeredgewidth', 'markeredgecolor', 'markevery',
                    'linestyle', 'fillstyle', 'drawstyle', 'dash_capstyle',
                    'dash_joinstyle', 'solid_capstyle', 'solid_joinstyle',
                    'dashes']:
            base_style.pop(key, None)

        # Make the style dict for the line collections (the bars).
        eb_lines_style = {**base_style, 'color': ecolor}

        if elinewidth is not None:
            eb_lines_style['linewidth'] = elinewidth
        elif 'linewidth' in kwargs:
            eb_lines_style['linewidth'] = kwargs['linewidth']

        for key in ('transform', 'alpha', 'zorder', 'rasterized'):
            if key in kwargs:
                eb_lines_style[key] = kwargs[key]

        # Make the style dict for caps (the "hats").
        eb_cap_style = {**base_style, 'linestyle': 'none'}
        if capsize is None:
            capsize = mpl.rcParams["errorbar.capsize"]
        if capsize > 0:
            eb_cap_style['markersize'] = 2. * capsize
        if capthick is not None:
            eb_cap_style['markeredgewidth'] = capthick

        # For backwards-compat, allow explicit setting of
        # 'markeredgewidth' to over-ride capthick.
        for key in ('markeredgewidth', 'transform', 'alpha',
                    'zorder', 'rasterized'):
            if key in kwargs:
                eb_cap_style[key] = kwargs[key]
        eb_cap_style['color'] = ecolor

        barcols = []
        caplines = {'x': [], 'y': []}

        # Vectorized fancy-indexer.
        def apply_mask(arrays, mask):
            return [array[mask] for array in arrays]

        # dep: dependent dataset, indep: independent dataset
        for (dep_axis, dep, err, lolims, uplims, indep, lines_func,
             marker, lomarker, himarker) in [
                ("x", x, xerr, xlolims, xuplims, y, self.hlines,
                 "|", mlines.CARETRIGHTBASE, mlines.CARETLEFTBASE),
                ("y", y, yerr, lolims, uplims, x, self.vlines,
                 "_", mlines.CARETUPBASE, mlines.CARETDOWNBASE),
        ]:
            if err is None:
                continue
            lolims = np.broadcast_to(lolims, len(dep)).astype(bool)
            uplims = np.broadcast_to(uplims, len(dep)).astype(bool)
            try:
                np.broadcast_to(err, (2, len(dep)))
            except ValueError:
                raise ValueError(
                    f"'{dep_axis}err' (shape: {np.shape(err)}) must be a "
                    f"scalar or a 1D or (2, n) array-like whose shape matches "
                    f"'{dep_axis}' (shape: {np.shape(dep)})") from None
            if err.dtype is np.dtype(object) and np.any(err == None):  # noqa: E711
                raise ValueError(
                    f"'{dep_axis}err' must not contain None. "
                    "Use NaN if you want to skip a value.")

            # Raise if any errors are negative, but not if they are nan.
            # To avoid nan comparisons (which lead to warnings on some
            # platforms), we select with `err==err` (which is False for nan).
            # Also, since datetime.timedelta cannot be compared with 0,
            # we compare with the negative error instead.
            if np.any((check := err[err == err]) < -check):
                raise ValueError(
                    f"'{dep_axis}err' must not contain negative values")
            # This is like
            #     elow, ehigh = np.broadcast_to(...)
            #     return dep - elow * ~lolims, dep + ehigh * ~uplims
            # except that broadcast_to would strip units.
            low, high = dep + np.vstack([-(1 - lolims), 1 - uplims]) * err
            barcols.append(lines_func(
                *apply_mask([indep, low, high], everymask), **eb_lines_style))
            if self.name == "polar" and dep_axis == "x":
                for b in barcols:
                    for p in b.get_paths():
                        p._interpolation_steps = 2
            # Normal errorbars for points without upper/lower limits.
            nolims = ~(lolims | uplims)
            if nolims.any() and capsize > 0:
                indep_masked, lo_masked, hi_masked = apply_mask(
                    [indep, low, high], nolims & everymask)
                for lh_masked in [lo_masked, hi_masked]:
                    # Since this has to work for x and y as dependent data, we
                    # first set both x and y to the independent variable and
                    # overwrite the respective dependent data in a second step.
                    line = mlines.Line2D(indep_masked, indep_masked,
                                         marker=marker, **eb_cap_style)
                    line.set(**{f"{dep_axis}data": lh_masked})
                    caplines[dep_axis].append(line)
            for idx, (lims, hl) in enumerate([(lolims, high), (uplims, low)]):
                if not lims.any():
                    continue
                hlmarker = (
                    himarker
                    if self._axis_map[dep_axis].get_inverted() ^ idx
                    else lomarker)
                x_masked, y_masked, hl_masked = apply_mask(
                    [x, y, hl], lims & everymask)
                # As above, we set the dependent data in a second step.
                line = mlines.Line2D(x_masked, y_masked,
                                     marker=hlmarker, **eb_cap_style)
                line.set(**{f"{dep_axis}data": hl_masked})
                caplines[dep_axis].append(line)
                if capsize > 0:
                    caplines[dep_axis].append(mlines.Line2D(
                        x_masked, y_masked, marker=marker, **eb_cap_style))
        if self.name == 'polar':
            trans_shift = self.transShift
            for axis in caplines:
                for l in caplines[axis]:
                    # Rotate caps to be perpendicular to the error bars
                    for theta, r in zip(l.get_xdata(), l.get_ydata()):
                        rotation = _ScaledRotation(theta=theta, trans_shift=trans_shift)
                        if axis == 'y':
                            rotation += mtransforms.Affine2D().rotate(np.pi / 2)
                        ms = mmarkers.MarkerStyle(marker=marker,
                                                  transform=rotation)
                        self.add_line(mlines.Line2D([theta], [r], marker=ms,
                                                    **eb_cap_style))
        else:
            for axis in caplines:
                for l in caplines[axis]:
                    self.add_line(l)

        self._request_autoscale_view()
        caplines = caplines['x'] + caplines['y']
        errorbar_container = ErrorbarContainer(
            (data_line, tuple(caplines), tuple(barcols)),
            has_xerr=(xerr is not None), has_yerr=(yerr is not None),
            label=label)
        self.add_container(errorbar_container)

        return errorbar_container  # (l0, caplines, barcols)

    @_api.make_keyword_only("3.10", "notch")
    @_preprocess_data()
    @_api.rename_parameter("3.9", "labels", "tick_labels")
    def boxplot(self, x, notch=None, sym=None, vert=None,
                orientation='vertical', whis=None, positions=None,
                widths=None, patch_artist=None, bootstrap=None,
                usermedians=None, conf_intervals=None,
                meanline=None, showmeans=None, showcaps=None,
                showbox=None, showfliers=None, boxprops=None,
                tick_labels=None, flierprops=None, medianprops=None,
                meanprops=None, capprops=None, whiskerprops=None,
                manage_ticks=True, autorange=False, zorder=None,
                capwidths=None, label=None):
        """
        Draw a box and whisker plot.

        The box extends from the first quartile (Q1) to the third
        quartile (Q3) of the data, with a line at the median.
        The whiskers extend from the box to the farthest data point
        lying within 1.5x the inter-quartile range (IQR) from the box.
        Flier points are those past the end of the whiskers.
        See https://en.wikipedia.org/wiki/Box_plot for reference.

        .. code-block:: none

                  Q1-1.5IQR   Q1   median  Q3   Q3+1.5IQR
                               |-----:-----|
               o      |--------|     :     |--------|    o  o
                               |-----:-----|
             flier             <----------->            fliers
                                    IQR


        Parameters
        ----------
        x : Array or a sequence of vectors.
            The input data.  If a 2D array, a boxplot is drawn for each column
            in *x*.  If a sequence of 1D arrays, a boxplot is drawn for each
            array in *x*.

        notch : bool, default: :rc:`boxplot.notch`
            Whether to draw a notched boxplot (`True`), or a rectangular
            boxplot (`False`).  The notches represent the confidence interval
            (CI) around the median.  The documentation for *bootstrap*
            describes how the locations of the notches are computed by
            default, but their locations may also be overridden by setting the
            *conf_intervals* parameter.

            .. note::

                In cases where the values of the CI are less than the
                lower quartile or greater than the upper quartile, the
                notches will extend beyond the box, giving it a
                distinctive "flipped" appearance. This is expected
                behavior and consistent with other statistical
                visualization packages.

        sym : str, optional
            The default symbol for flier points.  An empty string ('') hides
            the fliers.  If `None`, then the fliers default to 'b+'.  More
            control is provided by the *flierprops* parameter.

        vert : bool, optional
            .. deprecated:: 3.11
                Use *orientation* instead.

                This is a pending deprecation for 3.10, with full deprecation
                in 3.11 and removal in 3.13.
                If this is given during the deprecation period, it overrides
                the *orientation* parameter.

            If True, plots the boxes vertically.
            If False, plots the boxes horizontally.

        orientation : {'vertical', 'horizontal'}, default: 'vertical'
            If 'horizontal', plots the boxes horizontally.
            Otherwise, plots the boxes vertically.

            .. versionadded:: 3.10

        whis : float or (float, float), default: 1.5
            The position of the whiskers.

            If a float, the lower whisker is at the lowest datum above
            ``Q1 - whis*(Q3-Q1)``, and the upper whisker at the highest datum
            below ``Q3 + whis*(Q3-Q1)``, where Q1 and Q3 are the first and
            third quartiles.  The default value of ``whis = 1.5`` corresponds
            to Tukey's original definition of boxplots.

            If a pair of floats, they indicate the percentiles at which to
            draw the whiskers (e.g., (5, 95)).  In particular, setting this to
            (0, 100) results in whiskers covering the whole range of the data.

            In the edge case where ``Q1 == Q3``, *whis* is automatically set
            to (0, 100) (cover the whole range of the data) if *autorange* is
            True.

            Beyond the whiskers, data are considered outliers and are plotted
            as individual points.

        bootstrap : int, optional
            Specifies whether to bootstrap the confidence intervals
            around the median for notched boxplots. If *bootstrap* is
            None, no bootstrapping is performed, and notches are
            calculated using a Gaussian-based asymptotic approximation
            (see McGill, R., Tukey, J.W., and Larsen, W.A., 1978, and
            Kendall and Stuart, 1967). Otherwise, bootstrap specifies
            the number of times to bootstrap the median to determine its
            95% confidence intervals. Values between 1000 and 10000 are
            recommended.

        usermedians : 1D array-like, optional
            A 1D array-like of length ``len(x)``.  Each entry that is not
            `None` forces the value of the median for the corresponding
            dataset.  For entries that are `None`, the medians are computed
            by Matplotlib as normal.

        conf_intervals : array-like, optional
            A 2D array-like of shape ``(len(x), 2)``.  Each entry that is not
            None forces the location of the corresponding notch (which is
            only drawn if *notch* is `True`).  For entries that are `None`,
            the notches are computed by the method specified by the other
            parameters (e.g., *bootstrap*).

        positions : array-like, optional
            The positions of the boxes. The ticks and limits are
            automatically set to match the positions. Defaults to
            ``range(1, N+1)`` where N is the number of boxes to be drawn.

        widths : float or array-like
            The widths of the boxes.  The default is 0.5, or ``0.15*(distance
            between extreme positions)``, if that is smaller.

        patch_artist : bool, default: :rc:`boxplot.patchartist`
            If `False` produces boxes with the Line2D artist. Otherwise,
            boxes are drawn with Patch artists.

        tick_labels : list of str, optional
            The tick labels of each boxplot.
            Ticks are always placed at the box *positions*. If *tick_labels* is given,
            the ticks are labelled accordingly. Otherwise, they keep their numeric
            values.

            .. versionchanged:: 3.9
                Renamed from *labels*, which is deprecated since 3.9
                and will be removed in 3.11.

        manage_ticks : bool, default: True
            If True, the tick locations and labels will be adjusted to match
            the boxplot positions.

        autorange : bool, default: False
            When `True` and the data are distributed such that the 25th and
            75th percentiles are equal, *whis* is set to (0, 100) such
            that the whisker ends are at the minimum and maximum of the data.

        meanline : bool, default: :rc:`boxplot.meanline`
            If `True` (and *showmeans* is `True`), will try to render the
            mean as a line spanning the full width of the box according to
            *meanprops* (see below).  Not recommended if *shownotches* is also
            True.  Otherwise, means will be shown as points.

        zorder : float, default: ``Line2D.zorder = 2``
            The zorder of the boxplot.

        Returns
        -------
        dict
          A dictionary mapping each component of the boxplot to a list
          of the `.Line2D` instances created. That dictionary has the
          following keys (assuming vertical boxplots):

          - ``boxes``: the main body of the boxplot showing the
            quartiles and the median's confidence intervals if
            enabled.

          - ``medians``: horizontal lines at the median of each box.

          - ``whiskers``: the vertical lines extending to the most
            extreme, non-outlier data points.

          - ``caps``: the horizontal lines at the ends of the
            whiskers.

          - ``fliers``: points representing data that extend beyond
            the whiskers (fliers).

          - ``means``: points or lines representing the means.

        Other Parameters
        ----------------
        showcaps : bool, default: :rc:`boxplot.showcaps`
            Show the caps on the ends of whiskers.
        showbox : bool, default: :rc:`boxplot.showbox`
            Show the central box.
        showfliers : bool, default: :rc:`boxplot.showfliers`
            Show the outliers beyond the caps.
        showmeans : bool, default: :rc:`boxplot.showmeans`
            Show the arithmetic means.
        capprops : dict, default: None
            The style of the caps.
        capwidths : float or array, default: None
            The widths of the caps.
        boxprops : dict, default: None
            The style of the box.
        whiskerprops : dict, default: None
            The style of the whiskers.
        flierprops : dict, default: None
            The style of the fliers.
        medianprops : dict, default: None
            The style of the median.
        meanprops : dict, default: None
            The style of the mean.
        label : str or list of str, optional
            Legend labels. Use a single string when all boxes have the same style and
            you only want a single legend entry for them. Use a list of strings to
            label all boxes individually. To be distinguishable, the boxes should be
            styled individually, which is currently only possible by modifying the
            returned artists, see e.g. :doc:`/gallery/statistics/boxplot_demo`.

            In the case of a single string, the legend entry will technically be
            associated with the first box only. By default, the legend will show the
            median line (``result["medians"]``); if *patch_artist* is True, the legend
            will show the box `.Patch` artists (``result["boxes"]``) instead.

            .. versionadded:: 3.9

        data : indexable object, optional
            DATA_PARAMETER_PLACEHOLDER

        See Also
        --------
        .Axes.bxp : Draw a boxplot from pre-computed statistics.
        violinplot : Draw an estimate of the probability density function.
        """

        # Missing arguments default to rcParams.
        if whis is None:
            whis = mpl.rcParams['boxplot.whiskers']
        if bootstrap is None:
            bootstrap = mpl.rcParams['boxplot.bootstrap']

        bxpstats = cbook.boxplot_stats(x, whis=whis, bootstrap=bootstrap,
                                       labels=tick_labels, autorange=autorange)
        if notch is None:
            notch = mpl.rcParams['boxplot.notch']
        if patch_artist is None:
            patch_artist = mpl.rcParams['boxplot.patchartist']
        if meanline is None:
            meanline = mpl.rcParams['boxplot.meanline']
        if showmeans is None:
            showmeans = mpl.rcParams['boxplot.showmeans']
        if showcaps is None:
            showcaps = mpl.rcParams['boxplot.showcaps']
        if showbox is None:
            showbox = mpl.rcParams['boxplot.showbox']
        if showfliers is None:
            showfliers = mpl.rcParams['boxplot.showfliers']

        if boxprops is None:
            boxprops = {}
        if whiskerprops is None:
            whiskerprops = {}
        if capprops is None:
            capprops = {}
        if medianprops is None:
            medianprops = {}
        if meanprops is None:
            meanprops = {}
        if flierprops is None:
            flierprops = {}

        if patch_artist:
            boxprops['linestyle'] = 'solid'  # Not consistent with bxp.
            if 'color' in boxprops:
                boxprops['edgecolor'] = boxprops.pop('color')

        # if non-default sym value, put it into the flier dictionary
        # the logic for providing the default symbol ('b+') now lives
        # in bxp in the initial value of flierkw
        # handle all of the *sym* related logic here so we only have to pass
        # on the flierprops dict.
        if sym is not None:
            # no-flier case, which should really be done with
            # 'showfliers=False' but none-the-less deal with it to keep back
            # compatibility
            if sym == '':
                # blow away existing dict and make one for invisible markers
                flierprops = dict(linestyle='none', marker='', color='none')
                # turn the fliers off just to be safe
                showfliers = False
            # now process the symbol string
            else:
                # process the symbol string
                # discarded linestyle
                _, marker, color = _process_plot_format(sym)
                # if we have a marker, use it
                if marker is not None:
                    flierprops['marker'] = marker
                # if we have a color, use it
                if color is not None:
                    # assume that if color is passed in the user want
                    # filled symbol, if the users want more control use
                    # flierprops
                    flierprops['color'] = color
                    flierprops['markerfacecolor'] = color
                    flierprops['markeredgecolor'] = color

        # replace medians if necessary:
        if usermedians is not None:
            if (len(np.ravel(usermedians)) != len(bxpstats) or
                    np.shape(usermedians)[0] != len(bxpstats)):
                raise ValueError(
                    "'usermedians' and 'x' have different lengths")
            else:
                # reassign medians as necessary
                for stats, med in zip(bxpstats, usermedians):
                    if med is not None:
                        stats['med'] = med

        if conf_intervals is not None:
            if len(conf_intervals) != len(bxpstats):
                raise ValueError(
                    "'conf_intervals' and 'x' have different lengths")
            else:
                for stats, ci in zip(bxpstats, conf_intervals):
                    if ci is not None:
                        if len(ci) != 2:
                            raise ValueError('each confidence interval must '
                                             'have two values')
                        else:
                            if ci[0] is not None:
                                stats['cilo'] = ci[0]
                            if ci[1] is not None:
                                stats['cihi'] = ci[1]

        artists = self.bxp(bxpstats, positions=positions, widths=widths,
                           vert=vert, patch_artist=patch_artist,
                           shownotches=notch, showmeans=showmeans,
                           showcaps=showcaps, showbox=showbox,
                           boxprops=boxprops, flierprops=flierprops,
                           medianprops=medianprops, meanprops=meanprops,
                           meanline=meanline, showfliers=showfliers,
                           capprops=capprops, whiskerprops=whiskerprops,
                           manage_ticks=manage_ticks, zorder=zorder,
                           capwidths=capwidths, label=label,
                           orientation=orientation)
        return artists

    @_api.make_keyword_only("3.10", "widths")
    def bxp(self, bxpstats, positions=None, widths=None, vert=None,
            orientation='vertical', patch_artist=False, shownotches=False,
            showmeans=False, showcaps=True, showbox=True, showfliers=True,
            boxprops=None, whiskerprops=None, flierprops=None,
            medianprops=None, capprops=None, meanprops=None,
            meanline=False, manage_ticks=True, zorder=None,
            capwidths=None, label=None):
        """
        Draw a box and whisker plot from pre-computed statistics.

        The box extends from the first quartile *q1* to the third
        quartile *q3* of the data, with a line at the median (*med*).
        The whiskers extend from *whislow* to *whishi*.
        Flier points are markers past the end of the whiskers.
        See https://en.wikipedia.org/wiki/Box_plot for reference.

        .. code-block:: none

                   whislow    q1    med    q3    whishi
                               |-----:-----|
               o      |--------|     :     |--------|    o  o
                               |-----:-----|
             flier                                      fliers

        .. note::
            This is a low-level drawing function for when you already
            have the statistical parameters. If you want a boxplot based
            on a dataset, use `~.Axes.boxplot` instead.

        Parameters
        ----------
        bxpstats : list of dicts
            A list of dictionaries containing stats for each boxplot.
            Required keys are:

            - ``med``: Median (float).
            - ``q1``, ``q3``: First & third quartiles (float).
            - ``whislo``, ``whishi``: Lower & upper whisker positions (float).

            Optional keys are:

            - ``mean``: Mean (float).  Needed if ``showmeans=True``.
            - ``fliers``: Data beyond the whiskers (array-like).
              Needed if ``showfliers=True``.
            - ``cilo``, ``cihi``: Lower & upper confidence intervals
              about the median. Needed if ``shownotches=True``.
            - ``label``: Name of the dataset (str).  If available,
              this will be used a tick label for the boxplot

        positions : array-like, default: [1, 2, ..., n]
            The positions of the boxes. The ticks and limits
            are automatically set to match the positions.

        widths : float or array-like, default: None
            The widths of the boxes.  The default is
            ``clip(0.15*(distance between extreme positions), 0.15, 0.5)``.

        capwidths : float or array-like, default: None
            Either a scalar or a vector and sets the width of each cap.
            The default is ``0.5*(width of the box)``, see *widths*.

        vert : bool, optional
            .. deprecated:: 3.11
                Use *orientation* instead.

                This is a pending deprecation for 3.10, with full deprecation
                in 3.11 and removal in 3.13.
                If this is given during the deprecation period, it overrides
                the *orientation* parameter.

            If True, plots the boxes vertically.
            If False, plots the boxes horizontally.

        orientation : {'vertical', 'horizontal'}, default: 'vertical'
            If 'horizontal', plots the boxes horizontally.
            Otherwise, plots the boxes vertically.

            .. versionadded:: 3.10

        patch_artist : bool, default: False
            If `False` produces boxes with the `.Line2D` artist.
            If `True` produces boxes with the `~matplotlib.patches.Patch` artist.

        shownotches, showmeans, showcaps, showbox, showfliers : bool
            Whether to draw the CI notches, the mean value (both default to
            False), the caps, the box, and the fliers (all three default to
            True).

        boxprops, whiskerprops, capprops, flierprops, medianprops, meanprops :\
 dict, optional
            Artist properties for the boxes, whiskers, caps, fliers, medians, and
            means.

        meanline : bool, default: False
            If `True` (and *showmeans* is `True`), will try to render the mean
            as a line spanning the full width of the box according to
            *meanprops*. Not recommended if *shownotches* is also True.
            Otherwise, means will be shown as points.

        manage_ticks : bool, default: True
            If True, the tick locations and labels will be adjusted to match the
            boxplot positions.

        label : str or list of str, optional
            Legend labels. Use a single string when all boxes have the same style and
            you only want a single legend entry for them. Use a list of strings to
            label all boxes individually. To be distinguishable, the boxes should be
            styled individually, which is currently only possible by modifying the
            returned artists, see e.g. :doc:`/gallery/statistics/boxplot_demo`.

            In the case of a single string, the legend entry will technically be
            associated with the first box only. By default, the legend will show the
            median line (``result["medians"]``); if *patch_artist* is True, the legend
            will show the box `.Patch` artists (``result["boxes"]``) instead.

            .. versionadded:: 3.9

        zorder : float, default: ``Line2D.zorder = 2``
            The zorder of the resulting boxplot.

        Returns
        -------
        dict
            A dictionary mapping each component of the boxplot to a list
            of the `.Line2D` instances created. That dictionary has the
            following keys (assuming vertical boxplots):

            - ``boxes``: main bodies of the boxplot showing the quartiles, and
              the median's confidence intervals if enabled.
            - ``medians``: horizontal lines at the median of each box.
            - ``whiskers``: vertical lines up to the last non-outlier data.
            - ``caps``: horizontal lines at the ends of the whiskers.
            - ``fliers``: points representing data beyond the whiskers (fliers).
            - ``means``: points or lines representing the means.

        See Also
        --------
        boxplot : Draw a boxplot from data instead of pre-computed statistics.
        """
        # Clamp median line to edge of box by default.
        medianprops = {
            "solid_capstyle": "butt",
            "dash_capstyle": "butt",
            **(medianprops or {}),
        }
        meanprops = {
            "solid_capstyle": "butt",
            "dash_capstyle": "butt",
            **(meanprops or {}),
        }

        # lists of artists to be output
        whiskers = []
        caps = []
        boxes = []
        medians = []
        means = []
        fliers = []

        # empty list of xticklabels
        datalabels = []

        # Use default zorder if none specified
        if zorder is None:
            zorder = mlines.Line2D.zorder

        zdelta = 0.1

        def merge_kw_rc(subkey, explicit, zdelta=0, usemarker=True):
            d = {k.split('.')[-1]: v for k, v in mpl.rcParams.items()
                 if k.startswith(f'boxplot.{subkey}props')}
            d['zorder'] = zorder + zdelta
            if not usemarker:
                d['marker'] = ''
            d.update(cbook.normalize_kwargs(explicit, mlines.Line2D))
            return d

        box_kw = {
            'linestyle': mpl.rcParams['boxplot.boxprops.linestyle'],
            'linewidth': mpl.rcParams['boxplot.boxprops.linewidth'],
            'edgecolor': mpl.rcParams['boxplot.boxprops.color'],
            'facecolor': ('white' if mpl.rcParams['_internal.classic_mode']
                          else mpl.rcParams['patch.facecolor']),
            'zorder': zorder,
            **cbook.normalize_kwargs(boxprops, mpatches.PathPatch)
        } if patch_artist else merge_kw_rc('box', boxprops, usemarker=False)
        whisker_kw = merge_kw_rc('whisker', whiskerprops, usemarker=False)
        cap_kw = merge_kw_rc('cap', capprops, usemarker=False)
        flier_kw = merge_kw_rc('flier', flierprops)
        median_kw = merge_kw_rc('median', medianprops, zdelta, usemarker=False)
        mean_kw = merge_kw_rc('mean', meanprops, zdelta)
        removed_prop = 'marker' if meanline else 'linestyle'
        # Only remove the property if it's not set explicitly as a parameter.
        if meanprops is None or removed_prop not in meanprops:
            mean_kw[removed_prop] = ''

        # vert and orientation parameters are linked until vert's
        # deprecation period expires. vert only takes precedence
        # if set to False.
        if vert is None:
            vert = mpl.rcParams['boxplot.vertical']
        else:
            _api.warn_deprecated(
                "3.11",
                name="vert: bool",
                alternative="orientation: {'vertical', 'horizontal'}",
                pending=True,
            )
        if vert is False:
            orientation = 'horizontal'
        _api.check_in_list(['horizontal', 'vertical'], orientation=orientation)

        if not mpl.rcParams['boxplot.vertical']:
            _api.warn_deprecated(
                "3.10",
                name='boxplot.vertical', obj_type="rcparam"
            )

        # vertical or horizontal plot?
        maybe_swap = slice(None) if orientation == 'vertical' else slice(None, None, -1)

        def do_plot(xs, ys, **kwargs):
            return self.plot(*[xs, ys][maybe_swap], **kwargs)[0]

        def do_patch(xs, ys, **kwargs):
            path = mpath.Path._create_closed(
                np.column_stack([xs, ys][maybe_swap]))
            patch = mpatches.PathPatch(path, **kwargs)
            self.add_artist(patch)
            return patch

        # input validation
        N = len(bxpstats)
        datashape_message = ("List of boxplot statistics and `{0}` "
                             "values must have same the length")
        # check position
        if positions is None:
            positions = list(range(1, N + 1))
        elif len(positions) != N:
            raise ValueError(datashape_message.format("positions"))

        positions = np.array(positions)
        if len(positions) > 0 and not all(isinstance(p, Real) for p in positions):
            raise TypeError("positions should be an iterable of numbers")

        # width
        if widths is None:
            widths = [np.clip(0.15 * np.ptp(positions), 0.15, 0.5)] * N
        elif np.isscalar(widths):
            widths = [widths] * N
        elif len(widths) != N:
            raise ValueError(datashape_message.format("widths"))

        # capwidth
        if capwidths is None:
            capwidths = 0.5 * np.array(widths)
        elif np.isscalar(capwidths):
            capwidths = [capwidths] * N
        elif len(capwidths) != N:
            raise ValueError(datashape_message.format("capwidths"))

        for pos, width, stats, capwidth in zip(positions, widths, bxpstats,
                                               capwidths):
            # try to find a new label
            datalabels.append(stats.get('label', pos))

            # whisker coords
            whis_x = [pos, pos]
            whislo_y = [stats['q1'], stats['whislo']]
            whishi_y = [stats['q3'], stats['whishi']]
            # cap coords
            cap_left = pos - capwidth * 0.5
            cap_right = pos + capwidth * 0.5
            cap_x = [cap_left, cap_right]
            cap_lo = np.full(2, stats['whislo'])
            cap_hi = np.full(2, stats['whishi'])
            # box and median coords
            box_left = pos - width * 0.5
            box_right = pos + width * 0.5
            med_y = [stats['med'], stats['med']]
            # notched boxes
            if shownotches:
                notch_left = pos - width * 0.25
                notch_right = pos + width * 0.25
                box_x = [box_left, box_right, box_right, notch_right,
                         box_right, box_right, box_left, box_left, notch_left,
                         box_left, box_left]
                box_y = [stats['q1'], stats['q1'], stats['cilo'],
                         stats['med'], stats['cihi'], stats['q3'],
                         stats['q3'], stats['cihi'], stats['med'],
                         stats['cilo'], stats['q1']]
                med_x = [notch_left, notch_right]
            # plain boxes
            else:
                box_x = [box_left, box_right, box_right, box_left, box_left]
                box_y = [stats['q1'], stats['q1'], stats['q3'], stats['q3'],
                         stats['q1']]
                med_x = [box_left, box_right]

            # maybe draw the box
            if showbox:
                do_box = do_patch if patch_artist else do_plot
                boxes.append(do_box(box_x, box_y, **box_kw))
                median_kw.setdefault('label', '_nolegend_')
            # draw the whiskers
            whisker_kw.setdefault('label', '_nolegend_')
            whiskers.append(do_plot(whis_x, whislo_y, **whisker_kw))
            whiskers.append(do_plot(whis_x, whishi_y, **whisker_kw))
            # maybe draw the caps
            if showcaps:
                cap_kw.setdefault('label', '_nolegend_')
                caps.append(do_plot(cap_x, cap_lo, **cap_kw))
                caps.append(do_plot(cap_x, cap_hi, **cap_kw))
            # draw the medians
            medians.append(do_plot(med_x, med_y, **median_kw))
            # maybe draw the means
            if showmeans:
                if meanline:
                    means.append(do_plot(
                        [box_left, box_right], [stats['mean'], stats['mean']],
                        **mean_kw
                    ))
                else:
                    means.append(do_plot([pos], [stats['mean']], **mean_kw))
            # maybe draw the fliers
            if showfliers:
                flier_kw.setdefault('label', '_nolegend_')
                flier_x = np.full(len(stats['fliers']), pos, dtype=np.float64)
                flier_y = stats['fliers']
                fliers.append(do_plot(flier_x, flier_y, **flier_kw))

        # Set legend labels
        if label:
            box_or_med = boxes if showbox and patch_artist else medians
            if cbook.is_scalar_or_string(label):
                # assign the label only to the first box
                box_or_med[0].set_label(label)
            else:  # label is a sequence
                if len(box_or_med) != len(label):
                    raise ValueError(datashape_message.format("label"))
                for artist, lbl in zip(box_or_med, label):
                    artist.set_label(lbl)

        if manage_ticks:
            axis_name = "x" if orientation == 'vertical' else "y"
            interval = getattr(self.dataLim, f"interval{axis_name}")
            axis = self._axis_map[axis_name]
            positions = axis.convert_units(positions)
            # The 0.5 additional padding ensures reasonable-looking boxes
            # even when drawing a single box.  We set the sticky edge to
            # prevent margins expansion, in order to match old behavior (back
            # when separate calls to boxplot() would completely reset the axis
            # limits regardless of what was drawn before).  The sticky edges
            # are attached to the median lines, as they are always present.
            interval[:] = (min(interval[0], min(positions) - .5),
                           max(interval[1], max(positions) + .5))
            for median, position in zip(medians, positions):
                getattr(median.sticky_edges, axis_name).extend(
                    [position - .5, position + .5])
            # Modified from Axis.set_ticks and Axis.set_ticklabels.
            locator = axis.get_major_locator()
            if not isinstance(axis.get_major_locator(),
                              mticker.FixedLocator):
                locator = mticker.FixedLocator([])
                axis.set_major_locator(locator)
            locator.locs = np.array([*locator.locs, *positions])
            formatter = axis.get_major_formatter()
            if not isinstance(axis.get_major_formatter(),
                              mticker.FixedFormatter):
                formatter = mticker.FixedFormatter([])
                axis.set_major_formatter(formatter)
            formatter.seq = [*formatter.seq, *datalabels]

            self._request_autoscale_view()

        return dict(whiskers=whiskers, caps=caps, boxes=boxes,
                    medians=medians, fliers=fliers, means=means)

    @staticmethod
    def _parse_scatter_color_args(c, edgecolors, kwargs, xsize,
                                  get_next_color_func):
        """
        Helper function to process color related arguments of `.Axes.scatter`.

        Argument precedence for facecolors:

        - c (if not None)
        - kwargs['facecolor']
        - kwargs['facecolors']
        - kwargs['color'] (==kwcolor)
        - 'b' if in classic mode else the result of ``get_next_color_func()``

        Argument precedence for edgecolors:

        - kwargs['edgecolor']
        - edgecolors (is an explicit kw argument in scatter())
        - kwargs['color'] (==kwcolor)
        - 'face' if not in classic mode else None

        Parameters
        ----------
        c : :mpltype:`color` or array-like or list of :mpltype:`color` or None
            See argument description of `.Axes.scatter`.
        edgecolors : :mpltype:`color` or sequence of color or {'face', 'none'} or None
            See argument description of `.Axes.scatter`.
        kwargs : dict
            Additional kwargs. If these keys exist, we pop and process them:
            'facecolors', 'facecolor', 'edgecolor', 'color'
            Note: The dict is modified by this function.
        xsize : int
            The size of the x and y arrays passed to `.Axes.scatter`.
        get_next_color_func : callable
            A callable that returns a color. This color is used as facecolor
            if no other color is provided.

            Note, that this is a function rather than a fixed color value to
            support conditional evaluation of the next color.  As of the
            current implementation obtaining the next color from the
            property cycle advances the cycle. This must only happen if we
            actually use the color, which will only be decided within this
            method.

        Returns
        -------
        c
            The input *c* if it was not *None*, else a color derived from the
            other inputs or defaults.
        colors : array(N, 4) or None
            The facecolors as RGBA values, or *None* if a colormap is used.
        edgecolors
            The edgecolor.

        """
        facecolors = kwargs.pop('facecolors', None)
        facecolors = kwargs.pop('facecolor', facecolors)
        edgecolors = kwargs.pop('edgecolor', edgecolors)

        kwcolor = kwargs.pop('color', None)

        if kwcolor is not None and c is not None:
            raise ValueError("Supply a 'c' argument or a 'color'"
                             " kwarg but not both; they differ but"
                             " their functionalities overlap.")

        if kwcolor is not None:
            try:
                mcolors.to_rgba_array(kwcolor)
            except ValueError as err:
                raise ValueError(
                    "'color' kwarg must be a color or sequence of color "
                    "specs.  For a sequence of values to be color-mapped, use "
                    "the 'c' argument instead.") from err
            if edgecolors is None:
                edgecolors = kwcolor
            if facecolors is None:
                facecolors = kwcolor

        if edgecolors is None and not mpl.rcParams['_internal.classic_mode']:
            edgecolors = mpl.rcParams['scatter.edgecolors']

        # Raise a warning if both `c` and `facecolor` are set (issue #24404).
        if c is not None and facecolors is not None:
            _api.warn_external(
                "You passed both c and facecolor/facecolors for the markers. "
                "c has precedence over facecolor/facecolors. "
                "This behavior may change in the future."
            )

        c_was_none = c is None
        if c is None:
            c = (facecolors if facecolors is not None
                 else "b" if mpl.rcParams['_internal.classic_mode']
                 else get_next_color_func())
        c_is_string_or_strings = (
            isinstance(c, str)
            or (np.iterable(c) and len(c) > 0
                and isinstance(cbook._safe_first_finite(c), str)))

        def invalid_shape_exception(csize, xsize):
            return ValueError(
                f"'c' argument has {csize} elements, which is inconsistent "
                f"with 'x' and 'y' with size {xsize}.")

        c_is_mapped = False  # Unless proven otherwise below.
        valid_shape = True  # Unless proven otherwise below.
        if not c_was_none and kwcolor is None and not c_is_string_or_strings:
            try:  # First, does 'c' look suitable for value-mapping?
                c = np.asanyarray(c, dtype=float)
            except ValueError:
                pass  # Failed to convert to float array; must be color specs.
            else:
                # handle the documented special case of a 2D array with 1
                # row which as RGB(A) to broadcast.
                if c.shape == (1, 4) or c.shape == (1, 3):
                    c_is_mapped = False
                    if c.size != xsize:
                        valid_shape = False
                # If c can be either mapped values or an RGB(A) color, prefer
                # the former if shapes match, the latter otherwise.
                elif c.size == xsize:
                    c = c.ravel()
                    c_is_mapped = True
                else:  # Wrong size; it must not be intended for mapping.
                    if c.shape in ((3,), (4,)):
                        _api.warn_external(
                            "*c* argument looks like a single numeric RGB or "
                            "RGBA sequence, which should be avoided as value-"
                            "mapping will have precedence in case its length "
                            "matches with *x* & *y*.  Please use the *color* "
                            "keyword-argument or provide a 2D array "
                            "with a single row if you intend to specify "
                            "the same RGB or RGBA value for all points.")
                    valid_shape = False
        if not c_is_mapped:
            try:  # Is 'c' acceptable as PathCollection facecolors?
                colors = mcolors.to_rgba_array(c)
            except (TypeError, ValueError) as err:
                if "RGBA values should be within 0-1 range" in str(err):
                    raise
                else:
                    if not valid_shape:
                        raise invalid_shape_exception(c.size, xsize) from err
                    # Both the mapping *and* the RGBA conversion failed: pretty
                    # severe failure => one may appreciate a verbose feedback.
                    raise ValueError(
                        f"'c' argument must be a color, a sequence of colors, "
                        f"or a sequence of numbers, not {c!r}") from err
            else:
                if len(colors) not in (0, 1, xsize):
                    # NB: remember that a single color is also acceptable.
                    # Besides *colors* will be an empty array if c == 'none'.
                    raise invalid_shape_exception(len(colors), xsize)
        else:
            colors = None  # use cmap, norm after collection is created
        return c, colors, edgecolors

    @_api.make_keyword_only("3.10", "marker")
    @_preprocess_data(replace_names=["x", "y", "s", "linewidths",
                                     "edgecolors", "c", "facecolor",
                                     "facecolors", "color"],
                      label_namer="y")
    @_docstring.interpd
    def scatter(self, x, y, s=None, c=None, marker=None, cmap=None, norm=None,
                vmin=None, vmax=None, alpha=None, linewidths=None, *,
                edgecolors=None, colorizer=None, plotnonfinite=False, **kwargs):
        """
        A scatter plot of *y* vs. *x* with varying marker size and/or color.

        Parameters
        ----------
        x, y : float or array-like, shape (n, )
            The data positions.

        s : float or array-like, shape (n, ), optional
            The marker size in points**2 (typographic points are 1/72 in.).
            Default is ``rcParams['lines.markersize'] ** 2``.

            The linewidth and edgecolor can visually interact with the marker
            size, and can lead to artifacts if the marker size is smaller than
            the linewidth.

            If the linewidth is greater than 0 and the edgecolor is anything
            but *'none'*, then the effective size of the marker will be
            increased by half the linewidth because the stroke will be centered
            on the edge of the shape.

            To eliminate the marker edge either set *linewidth=0* or
            *edgecolor='none'*.

        c : array-like or list of :mpltype:`color` or :mpltype:`color`, optional
            The marker colors. Possible values:

            - A scalar or sequence of n numbers to be mapped to colors using
              *cmap* and *norm*.
            - A 2D array in which the rows are RGB or RGBA.
            - A sequence of colors of length n.
            - A single color format string.

            Note that *c* should not be a single numeric RGB or RGBA sequence
            because that is indistinguishable from an array of values to be
            colormapped. If you want to specify the same RGB or RGBA value for
            all points, use a 2D array with a single row.  Otherwise,
            value-matching will have precedence in case of a size matching with
            *x* and *y*.

            If you wish to specify a single color for all points
            prefer the *color* keyword argument.

            Defaults to `None`. In that case the marker color is determined
            by the value of *color*, *facecolor* or *facecolors*. In case
            those are not specified or `None`, the marker color is determined
            by the next color of the ``Axes``' current "shape and fill" color
            cycle. This cycle defaults to :rc:`axes.prop_cycle`.

        marker : `~.markers.MarkerStyle`, default: :rc:`scatter.marker`
            The marker style. *marker* can be either an instance of the class
            or the text shorthand for a particular marker.
            See :mod:`matplotlib.markers` for more information about marker
            styles.

        %(cmap_doc)s

            This parameter is ignored if *c* is RGB(A).

        %(norm_doc)s

            This parameter is ignored if *c* is RGB(A).

        %(vmin_vmax_doc)s

            This parameter is ignored if *c* is RGB(A).

        alpha : float, default: None
            The alpha blending value, between 0 (transparent) and 1 (opaque).

        linewidths : float or array-like, default: :rc:`lines.linewidth`
            The linewidth of the marker edges. Note: The default *edgecolors*
            is 'face'. You may want to change this as well.

        edgecolors : {'face', 'none', *None*} or :mpltype:`color` or list of \
:mpltype:`color`, default: :rc:`scatter.edgecolors`
            The edge color of the marker. Possible values:

            - 'face': The edge color will always be the same as the face color.
            - 'none': No patch boundary will be drawn.
            - A color or sequence of colors.

            For non-filled markers, *edgecolors* is ignored. Instead, the color
            is determined like with 'face', i.e. from *c*, *colors*, or
            *facecolors*.

        %(colorizer_doc)s

            This parameter is ignored if *c* is RGB(A).

        plotnonfinite : bool, default: False
            Whether to plot points with nonfinite *c* (i.e. ``inf``, ``-inf``
            or ``nan``). If ``True`` the points are drawn with the *bad*
            colormap color (see `.Colormap.set_bad`).

        Returns
        -------
        `~matplotlib.collections.PathCollection`

        Other Parameters
        ----------------
        data : indexable object, optional
            DATA_PARAMETER_PLACEHOLDER
        **kwargs : `~matplotlib.collections.PathCollection` properties
            %(PathCollection:kwdoc)s

        See Also
        --------
        plot : To plot scatter plots when markers are identical in size and
            color.

        Notes
        -----
        * The `.plot` function will be faster for scatterplots where markers
          don't vary in size or color.

        * Any or all of *x*, *y*, *s*, and *c* may be masked arrays, in which
          case all masks will be combined and only unmasked points will be
          plotted.

        * Fundamentally, scatter works with 1D arrays; *x*, *y*, *s*, and *c*
          may be input as N-D arrays, but within scatter they will be
          flattened. The exception is *c*, which will be flattened only if its
          size matches the size of *x* and *y*.

        """
        # add edgecolors and linewidths to kwargs so they
        # can be processed by normailze_kwargs
        if edgecolors is not None:
            kwargs.update({'edgecolors': edgecolors})
        if linewidths is not None:
            kwargs.update({'linewidths': linewidths})

        kwargs = cbook.normalize_kwargs(kwargs, mcoll.Collection)
        # re direct linewidth and edgecolor so it can be
        # further processed by the rest of the function
        linewidths = kwargs.pop('linewidth', None)
        edgecolors = kwargs.pop('edgecolor', None)
        # Process **kwargs to handle aliases, conflicts with explicit kwargs:
        x, y = self._process_unit_info([("x", x), ("y", y)], kwargs)
        # np.ma.ravel yields an ndarray, not a masked array,
        # unless its argument is a masked array.
        x = np.ma.ravel(x)
        y = np.ma.ravel(y)
        if x.size != y.size:
            raise ValueError("x and y must be the same size")

        if s is None:
            s = (20 if mpl.rcParams['_internal.classic_mode'] else
                 mpl.rcParams['lines.markersize'] ** 2.0)
        s = np.ma.ravel(s)
        if (len(s) not in (1, x.size) or
                (not np.issubdtype(s.dtype, np.floating) and
                 not np.issubdtype(s.dtype, np.integer))):
            raise ValueError(
                "s must be a scalar, "
                "or float array-like with the same size as x and y")

        # get the original edgecolor the user passed before we normalize
        orig_edgecolor = edgecolors
        if edgecolors is None:
            orig_edgecolor = kwargs.get('edgecolor', None)
        c, colors, edgecolors = \
            self._parse_scatter_color_args(
                c, edgecolors, kwargs, x.size,
                get_next_color_func=self._get_patches_for_fill.get_next_color)

        if plotnonfinite and colors is None:
            c = np.ma.masked_invalid(c)
            x, y, s, edgecolors, linewidths = \
                cbook._combine_masks(x, y, s, edgecolors, linewidths)
        else:
            x, y, s, c, colors, edgecolors, linewidths = \
                cbook._combine_masks(
                    x, y, s, c, colors, edgecolors, linewidths)
        # Unmask edgecolors if it was actually a single RGB or RGBA.
        if (x.size in (3, 4)
                and np.ma.is_masked(edgecolors)
                and not np.ma.is_masked(orig_edgecolor)):
            edgecolors = edgecolors.data

        scales = s   # Renamed for readability below.

        # load default marker from rcParams
        if marker is None:
            marker = mpl.rcParams['scatter.marker']

        if isinstance(marker, mmarkers.MarkerStyle):
            marker_obj = marker
        else:
            marker_obj = mmarkers.MarkerStyle(marker)

        path = marker_obj.get_path().transformed(
            marker_obj.get_transform())
        if not marker_obj.is_filled():
            if orig_edgecolor is not None:
                _api.warn_external(
                    f"You passed a edgecolor/edgecolors ({orig_edgecolor!r}) "
                    f"for an unfilled marker ({marker!r}).  Matplotlib is "
                    "ignoring the edgecolor in favor of the facecolor.  This "
                    "behavior may change in the future."
                )
            # We need to handle markers that cannot be filled (like
            # '+' and 'x') differently than markers that can be
            # filled, but have their fillstyle set to 'none'.  This is
            # to get:
            #
            #  - respecting the fillestyle if set
            #  - maintaining back-compatibility for querying the facecolor of
            #    the un-fillable markers.
            #
            # While not an ideal situation, but is better than the
            # alternatives.
            if marker_obj.get_fillstyle() == 'none':
                # promote the facecolor to be the edgecolor
                edgecolors = colors
                # set the facecolor to 'none' (at the last chance) because
                # we cannot fill a path if the facecolor is non-null
                # (which is defendable at the renderer level).
                colors = 'none'
            else:
                # if we are not nulling the face color we can do this
                # simpler
                edgecolors = 'face'

            if linewidths is None:
                linewidths = mpl.rcParams['lines.linewidth']
            elif np.iterable(linewidths):
                linewidths = [
                    lw if lw is not None else mpl.rcParams['lines.linewidth']
                    for lw in linewidths]

        offsets = np.ma.column_stack([x, y])

        collection = mcoll.PathCollection(
            (path,), scales,
            facecolors=colors,
            edgecolors=edgecolors,
            linewidths=linewidths,
            offsets=offsets,
            offset_transform=kwargs.pop('transform', self.transData),
            alpha=alpha,
        )
        collection.set_transform(mtransforms.IdentityTransform())
        if colors is None:
            if colorizer:
                collection._set_colorizer_check_keywords(colorizer, cmap=cmap,
                                                         norm=norm, vmin=vmin,
                                                         vmax=vmax)
            else:
                collection.set_cmap(cmap)
                collection.set_norm(norm)
            collection.set_array(c)
            collection._scale_norm(norm, vmin, vmax)
        else:
            extra_kwargs = {
                    'cmap': cmap, 'norm': norm, 'vmin': vmin, 'vmax': vmax
                    }
            extra_keys = [k for k, v in extra_kwargs.items() if v is not None]
            if any(extra_keys):
                keys_str = ", ".join(f"'{k}'" for k in extra_keys)
                _api.warn_external(
                    "No data for colormapping provided via 'c'. "
                    f"Parameters {keys_str} will be ignored")
        collection._internal_update(kwargs)

        # Classic mode only:
        # ensure there are margins to allow for the
        # finite size of the symbols.  In v2.x, margins
        # are present by default, so we disable this
        # scatter-specific override.
        if mpl.rcParams['_internal.classic_mode']:
            if self._xmargin < 0.05 and x.size > 0:
                self.set_xmargin(0.05)
            if self._ymargin < 0.05 and x.size > 0:
                self.set_ymargin(0.05)

        self.add_collection(collection)
        self._request_autoscale_view()

        return collection

    @_api.make_keyword_only("3.10", "gridsize")
    @_preprocess_data(replace_names=["x", "y", "C"], label_namer="y")
    @_docstring.interpd
    def hexbin(self, x, y, C=None, gridsize=100, bins=None,
               xscale='linear', yscale='linear', extent=None,
               cmap=None, norm=None, vmin=None, vmax=None,
               alpha=None, linewidths=None, edgecolors='face',
               reduce_C_function=np.mean, mincnt=None, marginals=False,
               colorizer=None, **kwargs):
        """
        Make a 2D hexagonal binning plot of points *x*, *y*.

        If *C* is *None*, the value of the hexagon is determined by the number
        of points in the hexagon. Otherwise, *C* specifies values at the
        coordinate (x[i], y[i]). For each hexagon, these values are reduced
        using *reduce_C_function*.

        Parameters
        ----------
        x, y : array-like
            The data positions. *x* and *y* must be of the same length.

        C : array-like, optional
            If given, these values are accumulated in the bins. Otherwise,
            every point has a value of 1. Must be of the same length as *x*
            and *y*.

        gridsize : int or (int, int), default: 100
            If a single int, the number of hexagons in the *x*-direction.
            The number of hexagons in the *y*-direction is chosen such that
            the hexagons are approximately regular.

            Alternatively, if a tuple (*nx*, *ny*), the number of hexagons
            in the *x*-direction and the *y*-direction. In the
            *y*-direction, counting is done along vertically aligned
            hexagons, not along the zig-zag chains of hexagons; see the
            following illustration.

            .. plot::

               import numpy
               import matplotlib.pyplot as plt

               np.random.seed(19680801)
               n= 300
               x = np.random.standard_normal(n)
               y = np.random.standard_normal(n)

               fig, ax = plt.subplots(figsize=(4, 4))
               h = ax.hexbin(x, y, gridsize=(5, 3))
               hx, hy = h.get_offsets().T
               ax.plot(hx[24::3], hy[24::3], 'ro-')
               ax.plot(hx[-3:], hy[-3:], 'ro-')
               ax.set_title('gridsize=(5, 3)')
               ax.axis('off')

            To get approximately regular hexagons, choose
            :math:`n_x = \\sqrt{3}\\,n_y`.

        bins : 'log' or int or sequence, default: None
            Discretization of the hexagon values.

            - If *None*, no binning is applied; the color of each hexagon
              directly corresponds to its count value.
            - If 'log', use a logarithmic scale for the colormap.
              Internally, :math:`log_{10}(i+1)` is used to determine the
              hexagon color. This is equivalent to ``norm=LogNorm()``.
            - If an integer, divide the counts in the specified number
              of bins, and color the hexagons accordingly.
            - If a sequence of values, the values of the lower bound of
              the bins to be used.

        xscale : {'linear', 'log'}, default: 'linear'
            Use a linear or log10 scale on the horizontal axis.

        yscale : {'linear', 'log'}, default: 'linear'
            Use a linear or log10 scale on the vertical axis.

        mincnt : int >= 0, default: *None*
            If not *None*, only display cells with at least *mincnt*
            number of points in the cell.

        marginals : bool, default: *False*
            If marginals is *True*, plot the marginal density as
            colormapped rectangles along the bottom of the x-axis and
            left of the y-axis.

        extent : 4-tuple of float, default: *None*
            The limits of the bins (xmin, xmax, ymin, ymax).
            The default assigns the limits based on
            *gridsize*, *x*, *y*, *xscale* and *yscale*.

            If *xscale* or *yscale* is set to 'log', the limits are
            expected to be the exponent for a power of 10. E.g. for
            x-limits of 1 and 50 in 'linear' scale and y-limits
            of 10 and 1000 in 'log' scale, enter (1, 50, 1, 3).

        Returns
        -------
        `~matplotlib.collections.PolyCollection`
            A `.PolyCollection` defining the hexagonal bins.

            - `.PolyCollection.get_offsets` contains a Mx2 array containing
              the x, y positions of the M hexagon centers in data coordinates.
            - `.PolyCollection.get_array` contains the values of the M
              hexagons.

            If *marginals* is *True*, horizontal
            bar and vertical bar (both PolyCollections) will be attached
            to the return collection as attributes *hbar* and *vbar*.

        Other Parameters
        ----------------
        %(cmap_doc)s

        %(norm_doc)s

        %(vmin_vmax_doc)s

        alpha : float between 0 and 1, optional
            The alpha blending value, between 0 (transparent) and 1 (opaque).

        linewidths : float, default: *None*
            If *None*, defaults to :rc:`patch.linewidth`.

        edgecolors : {'face', 'none', *None*} or color, default: 'face'
            The color of the hexagon edges. Possible values are:

            - 'face': Draw the edges in the same color as the fill color.
            - 'none': No edges are drawn. This can sometimes lead to unsightly
              unpainted pixels between the hexagons.
            - *None*: Draw outlines in the default color.
            - An explicit color.

        reduce_C_function : callable, default: `numpy.mean`
            The function to aggregate *C* within the bins. It is ignored if
            *C* is not given. This must have the signature::

                def reduce_C_function(C: array) -> float

            Commonly used functions are:

            - `numpy.mean`: average of the points
            - `numpy.sum`: integral of the point values
            - `numpy.amax`: value taken from the largest point

            By default will only reduce cells with at least 1 point because some
            reduction functions (such as `numpy.amax`) will error/warn with empty
            input. Changing *mincnt* will adjust the cutoff, and if set to 0 will
            pass empty input to the reduction function.

        %(colorizer_doc)s

        data : indexable object, optional
            DATA_PARAMETER_PLACEHOLDER

        **kwargs : `~matplotlib.collections.PolyCollection` properties
            All other keyword arguments are passed on to `.PolyCollection`:

            %(PolyCollection:kwdoc)s

        See Also
        --------
        hist2d : 2D histogram rectangular bins
        """
        self._process_unit_info([("x", x), ("y", y)], kwargs, convert=False)

        x, y, C = cbook.delete_masked_points(x, y, C)

        # Set the size of the hexagon grid
        if np.iterable(gridsize):
            nx, ny = gridsize
        else:
            nx = gridsize
            ny = int(nx / math.sqrt(3))
        # Count the number of data in each hexagon
        x = np.asarray(x, float)
        y = np.asarray(y, float)

        # Will be log()'d if necessary, and then rescaled.
        tx = x
        ty = y

        if xscale == 'log':
            if np.any(x <= 0.0):
                raise ValueError(
                    "x contains non-positive values, so cannot be log-scaled")
            tx = np.log10(tx)
        if yscale == 'log':
            if np.any(y <= 0.0):
                raise ValueError(
                    "y contains non-positive values, so cannot be log-scaled")
            ty = np.log10(ty)
        if extent is not None:
            xmin, xmax, ymin, ymax = extent
            if xmin > xmax:
                raise ValueError("In extent, xmax must be greater than xmin")
            if ymin > ymax:
                raise ValueError("In extent, ymax must be greater than ymin")
        else:
            xmin, xmax = (tx.min(), tx.max()) if len(x) else (0, 1)
            ymin, ymax = (ty.min(), ty.max()) if len(y) else (0, 1)

            # to avoid issues with singular data, expand the min/max pairs
            xmin, xmax = mtransforms.nonsingular(xmin, xmax, expander=0.1)
            ymin, ymax = mtransforms.nonsingular(ymin, ymax, expander=0.1)

        nx1 = nx + 1
        ny1 = ny + 1
        nx2 = nx
        ny2 = ny
        n = nx1 * ny1 + nx2 * ny2

        # In the x-direction, the hexagons exactly cover the region from
        # xmin to xmax. Need some padding to avoid roundoff errors.
        padding = 1.e-9 * (xmax - xmin)
        xmin -= padding
        xmax += padding
        sx = (xmax - xmin) / nx
        sy = (ymax - ymin) / ny
        # Positions in hexagon index coordinates.
        ix = (tx - xmin) / sx
        iy = (ty - ymin) / sy
        ix1 = np.round(ix).astype(int)
        iy1 = np.round(iy).astype(int)
        ix2 = np.floor(ix).astype(int)
        iy2 = np.floor(iy).astype(int)
        # flat indices, plus one so that out-of-range points go to position 0.
        i1 = np.where((0 <= ix1) & (ix1 < nx1) & (0 <= iy1) & (iy1 < ny1),
                      ix1 * ny1 + iy1 + 1, 0)
        i2 = np.where((0 <= ix2) & (ix2 < nx2) & (0 <= iy2) & (iy2 < ny2),
                      ix2 * ny2 + iy2 + 1, 0)

        d1 = (ix - ix1) ** 2 + 3.0 * (iy - iy1) ** 2
        d2 = (ix - ix2 - 0.5) ** 2 + 3.0 * (iy - iy2 - 0.5) ** 2
        bdist = (d1 < d2)

        if C is None:  # [1:] drops out-of-range points.
            counts1 = np.bincount(i1[bdist], minlength=1 + nx1 * ny1)[1:]
            counts2 = np.bincount(i2[~bdist], minlength=1 + nx2 * ny2)[1:]
            accum = np.concatenate([counts1, counts2]).astype(float)
            if mincnt is not None:
                accum[accum < mincnt] = np.nan
            C = np.ones(len(x))
        else:
            # store the C values in a list per hexagon index
            Cs_at_i1 = [[] for _ in range(1 + nx1 * ny1)]
            Cs_at_i2 = [[] for _ in range(1 + nx2 * ny2)]
            for i in range(len(x)):
                if bdist[i]:
                    Cs_at_i1[i1[i]].append(C[i])
                else:
                    Cs_at_i2[i2[i]].append(C[i])
            if mincnt is None:
                mincnt = 1
            accum = np.array(
                [reduce_C_function(acc) if len(acc) >= mincnt else np.nan
                 for Cs_at_i in [Cs_at_i1, Cs_at_i2]
                 for acc in Cs_at_i[1:]],  # [1:] drops out-of-range points.
                float)

        good_idxs = ~np.isnan(accum)

        offsets = np.zeros((n, 2), float)
        offsets[:nx1 * ny1, 0] = np.repeat(np.arange(nx1), ny1)
        offsets[:nx1 * ny1, 1] = np.tile(np.arange(ny1), nx1)
        offsets[nx1 * ny1:, 0] = np.repeat(np.arange(nx2) + 0.5, ny2)
        offsets[nx1 * ny1:, 1] = np.tile(np.arange(ny2), nx2) + 0.5
        offsets[:, 0] *= sx
        offsets[:, 1] *= sy
        offsets[:, 0] += xmin
        offsets[:, 1] += ymin
        # remove accumulation bins with no data
        offsets = offsets[good_idxs, :]
        accum = accum[good_idxs]

        polygon = [sx, sy / 3] * np.array(
            [[.5, -.5], [.5, .5], [0., 1.], [-.5, .5], [-.5, -.5], [0., -1.]])

        if linewidths is None:
            linewidths = [mpl.rcParams['patch.linewidth']]

        if xscale == 'log' or yscale == 'log':
            polygons = np.expand_dims(polygon, 0)
            if xscale == 'log':
                polygons[:, :, 0] = 10.0 ** polygons[:, :, 0]
                xmin = 10.0 ** xmin
                xmax = 10.0 ** xmax
                self.set_xscale(xscale)
            if yscale == 'log':
                polygons[:, :, 1] = 10.0 ** polygons[:, :, 1]
                ymin = 10.0 ** ymin
                ymax = 10.0 ** ymax
                self.set_yscale(yscale)
        else:
            polygons = [polygon]

        collection = mcoll.PolyCollection(
            polygons,
            edgecolors=edgecolors,
            linewidths=linewidths,
            offsets=offsets,
            offset_transform=mtransforms.AffineDeltaTransform(self.transData)
        )

        # Set normalizer if bins is 'log'
        if cbook._str_equal(bins, 'log'):
            if norm is not None:
                _api.warn_external("Only one of 'bins' and 'norm' arguments "
                                   f"can be supplied, ignoring {bins=}")
            else:
                norm = mcolors.LogNorm(vmin=vmin, vmax=vmax)
                vmin = vmax = None
            bins = None

        if bins is not None:
            if not np.iterable(bins):
                minimum, maximum = min(accum), max(accum)
                bins -= 1  # one less edge than bins
                bins = minimum + (maximum - minimum) * np.arange(bins) / bins
            bins = np.sort(bins)
            accum = bins.searchsorted(accum)

        if colorizer:
            collection._set_colorizer_check_keywords(colorizer, cmap=cmap,
                                                     norm=norm, vmin=vmin,
                                                     vmax=vmax)
        else:
            collection.set_cmap(cmap)
            collection.set_norm(norm)
        collection.set_array(accum)
        collection.set_alpha(alpha)
        collection._internal_update(kwargs)
        collection._scale_norm(norm, vmin, vmax)

        # autoscale the norm with current accum values if it hasn't been set
        if norm is not None:
            if collection.norm.vmin is None and collection.norm.vmax is None:
                collection.norm.autoscale()

        corners = ((xmin, ymin), (xmax, ymax))
        self.update_datalim(corners)
        self._request_autoscale_view(tight=True)

        # add the collection last
        self.add_collection(collection, autolim=False)
        if not marginals:
            return collection

        # Process marginals
        bars = []
        for zname, z, zmin, zmax, zscale, nbins in [
                ("x", x, xmin, xmax, xscale, nx),
                ("y", y, ymin, ymax, yscale, 2 * ny),
        ]:

            if zscale == "log":
                bin_edges = np.geomspace(zmin, zmax, nbins + 1)
            else:
                bin_edges = np.linspace(zmin, zmax, nbins + 1)

            verts = np.empty((nbins, 4, 2))
            verts[:, 0, 0] = verts[:, 1, 0] = bin_edges[:-1]
            verts[:, 2, 0] = verts[:, 3, 0] = bin_edges[1:]
            verts[:, 0, 1] = verts[:, 3, 1] = .00
            verts[:, 1, 1] = verts[:, 2, 1] = .05
            if zname == "y":
                verts = verts[:, :, ::-1]  # Swap x and y.

            # Sort z-values into bins defined by bin_edges.
            bin_idxs = np.searchsorted(bin_edges, z) - 1
            values = np.empty(nbins)
            for i in range(nbins):
                # Get C-values for each bin, and compute bin value with
                # reduce_C_function.
                ci = C[bin_idxs == i]
                values[i] = reduce_C_function(ci) if len(ci) > 0 else np.nan

            mask = ~np.isnan(values)
            verts = verts[mask]
            values = values[mask]

            trans = getattr(self, f"get_{zname}axis_transform")(which="grid")
            bar = mcoll.PolyCollection(
                verts, transform=trans, edgecolors="face")
            bar.set_array(values)
            bar.set_cmap(cmap)
            bar.set_norm(norm)
            bar.set_alpha(alpha)
            bar._internal_update(kwargs)
            bars.append(self.add_collection(bar, autolim=False))

        collection.hbar, collection.vbar = bars

        def on_changed(collection):
            collection.hbar.set_cmap(collection.get_cmap())
            collection.hbar.set_cmap(collection.get_cmap())
            collection.vbar.set_clim(collection.get_clim())
            collection.vbar.set_clim(collection.get_clim())

        collection.callbacks.connect('changed', on_changed)

        return collection

    @_docstring.interpd
    def arrow(self, x, y, dx, dy, **kwargs):
        """
        [*Discouraged*] Add an arrow to the Axes.

        This draws an arrow from ``(x, y)`` to ``(x+dx, y+dy)``.

        .. admonition:: Discouraged

            The use of this method is discouraged because it is not guaranteed
            that the arrow renders reasonably. For example, the resulting arrow
            is affected by the Axes aspect ratio and limits, which may distort
            the arrow.

            Consider using `~.Axes.annotate` without a text instead, e.g. ::

                ax.annotate("", xytext=(0, 0), xy=(0.5, 0.5),
                            arrowprops=dict(arrowstyle="->"))

        Parameters
        ----------
        %(FancyArrow)s

        Returns
        -------
        `.FancyArrow`
            The created `.FancyArrow` object.
        """
        # Strip away units for the underlying patch since units
        # do not make sense to most patch-like code
        x = self.convert_xunits(x)
        y = self.convert_yunits(y)
        dx = self.convert_xunits(dx)
        dy = self.convert_yunits(dy)

        a = mpatches.FancyArrow(x, y, dx, dy, **kwargs)
        self.add_patch(a)
        self._request_autoscale_view()
        return a

    @_docstring.copy(mquiver.QuiverKey.__init__)
    def quiverkey(self, Q, X, Y, U, label, **kwargs):
        qk = mquiver.QuiverKey(Q, X, Y, U, label, **kwargs)
        self.add_artist(qk)
        return qk

    # Handle units for x and y, if they've been passed
    def _quiver_units(self, args, kwargs):
        if len(args) > 3:
            x, y = args[0:2]
            x, y = self._process_unit_info([("x", x), ("y", y)], kwargs)
            return (x, y) + args[2:]
        return args

    # args can be a combination of X, Y, U, V, C and all should be replaced
    @_preprocess_data()
    @_docstring.interpd
    def quiver(self, *args, **kwargs):
        """%(quiver_doc)s"""
        # Make sure units are handled for x and y values
        args = self._quiver_units(args, kwargs)
        q = mquiver.Quiver(self, *args, **kwargs)
        self.add_collection(q, autolim=True)
        self._request_autoscale_view()
        return q

    # args can be some combination of X, Y, U, V, C and all should be replaced
    @_preprocess_data()
    @_docstring.interpd
    def barbs(self, *args, **kwargs):
        """%(barbs_doc)s"""
        # Make sure units are handled for x and y values
        args = self._quiver_units(args, kwargs)
        b = mquiver.Barbs(self, *args, **kwargs)
        self.add_collection(b, autolim=True)
        self._request_autoscale_view()
        return b

    # Uses a custom implementation of data-kwarg handling in
    # _process_plot_var_args.
    def fill(self, *args, data=None, **kwargs):
        """
        Plot filled polygons.

        Parameters
        ----------
        *args : sequence of x, y, [color]
            Each polygon is defined by the lists of *x* and *y* positions of
            its nodes, optionally followed by a *color* specifier. See
            :mod:`matplotlib.colors` for supported color specifiers. The
            standard color cycle is used for polygons without a color
            specifier.

            You can plot multiple polygons by providing multiple *x*, *y*,
            *[color]* groups.

            For example, each of the following is legal::

                ax.fill(x, y)                    # a polygon with default color
                ax.fill(x, y, "b")               # a blue polygon
                ax.fill(x, y, x2, y2)            # two polygons
                ax.fill(x, y, "b", x2, y2, "r")  # a blue and a red polygon

        data : indexable object, optional
            An object with labelled data. If given, provide the label names to
            plot in *x* and *y*, e.g.::

                ax.fill("time", "signal",
                        data={"time": [0, 1, 2], "signal": [0, 1, 0]})

        Returns
        -------
        list of `~matplotlib.patches.Polygon`

        Other Parameters
        ----------------
        **kwargs : `~matplotlib.patches.Polygon` properties

        Notes
        -----
        Use :meth:`fill_between` if you would like to fill the region between
        two curves.
        """
        # For compatibility(!), get aliases from Line2D rather than Patch.
        kwargs = cbook.normalize_kwargs(kwargs, mlines.Line2D)
        # _get_patches_for_fill returns a generator, convert it to a list.
        patches = [*self._get_patches_for_fill(self, *args, data=data, **kwargs)]
        for poly in patches:
            self.add_patch(poly)
        self._request_autoscale_view()
        return patches

    def _fill_between_x_or_y(
            self, ind_dir, ind, dep1, dep2=0, *,
            where=None, interpolate=False, step=None, **kwargs):
        # Common implementation between fill_between (*ind_dir*="x") and
        # fill_betweenx (*ind_dir*="y").  *ind* is the independent variable,
        # *dep* the dependent variable.  The docstring below is interpolated
        # to generate both methods' docstrings.
        """
        Fill the area between two {dir} curves.

        The curves are defined by the points (*{ind}*, *{dep}1*) and (*{ind}*,
        *{dep}2*).  This creates one or multiple polygons describing the filled
        area.

        You may exclude some {dir} sections from filling using *where*.

        By default, the edges connect the given points directly.  Use *step*
        if the filling should be a step function, i.e. constant in between
        *{ind}*.

        Parameters
        ----------
        {ind} : array-like
            The {ind} coordinates of the nodes defining the curves.

        {dep}1 : array-like or float
            The {dep} coordinates of the nodes defining the first curve.

        {dep}2 : array-like or float, default: 0
            The {dep} coordinates of the nodes defining the second curve.

        where : array-like of bool, optional
            Define *where* to exclude some {dir} regions from being filled.
            The filled regions are defined by the coordinates ``{ind}[where]``.
            More precisely, fill between ``{ind}[i]`` and ``{ind}[i+1]`` if
            ``where[i] and where[i+1]``.  Note that this definition implies
            that an isolated *True* value between two *False* values in *where*
            will not result in filling.  Both sides of the *True* position
            remain unfilled due to the adjacent *False* values.

        interpolate : bool, default: False
            This option is only relevant if *where* is used and the two curves
            are crossing each other.

            Semantically, *where* is often used for *{dep}1* > *{dep}2* or
            similar.  By default, the nodes of the polygon defining the filled
            region will only be placed at the positions in the *{ind}* array.
            Such a polygon cannot describe the above semantics close to the
            intersection.  The {ind}-sections containing the intersection are
            simply clipped.

            Setting *interpolate* to *True* will calculate the actual
            intersection point and extend the filled region up to this point.

        step : {{'pre', 'post', 'mid'}}, optional
            Define *step* if the filling should be a step function,
            i.e. constant in between *{ind}*.  The value determines where the
            step will occur:

            - 'pre': The {dep} value is continued constantly to the left from
              every *{ind}* position, i.e. the interval ``({ind}[i-1], {ind}[i]]``
              has the value ``{dep}[i]``.
            - 'post': The y value is continued constantly to the right from
              every *{ind}* position, i.e. the interval ``[{ind}[i], {ind}[i+1])``
              has the value ``{dep}[i]``.
            - 'mid': Steps occur half-way between the *{ind}* positions.

        Returns
        -------
        `.FillBetweenPolyCollection`
            A `.FillBetweenPolyCollection` containing the plotted polygons.

        Other Parameters
        ----------------
        data : indexable object, optional
            DATA_PARAMETER_PLACEHOLDER

        **kwargs
            All other keyword arguments are passed on to
            `.FillBetweenPolyCollection`. They control the `.Polygon` properties:

            %(FillBetweenPolyCollection:kwdoc)s

        See Also
        --------
        fill_between : Fill between two sets of y-values.
        fill_betweenx : Fill between two sets of x-values.
        """
        dep_dir = mcoll.FillBetweenPolyCollection._f_dir_from_t(ind_dir)

        if not mpl.rcParams["_internal.classic_mode"]:
            kwargs = cbook.normalize_kwargs(kwargs, mcoll.Collection)
            if not any(c in kwargs for c in ("color", "facecolor")):
                kwargs["facecolor"] = self._get_patches_for_fill.get_next_color()

        ind, dep1, dep2 = self._fill_between_process_units(
            ind_dir, dep_dir, ind, dep1, dep2, **kwargs)

        collection = mcoll.FillBetweenPolyCollection(
            ind_dir, ind, dep1, dep2,
            where=where, interpolate=interpolate, step=step, **kwargs)

        self.add_collection(collection)
        self._request_autoscale_view()
        return collection

    def _fill_between_process_units(self, ind_dir, dep_dir, ind, dep1, dep2, **kwargs):
        """Handle united data, such as dates."""
        return map(np.ma.masked_invalid, self._process_unit_info(
            [(ind_dir, ind), (dep_dir, dep1), (dep_dir, dep2)], kwargs))

    def fill_between(self, x, y1, y2=0, where=None, interpolate=False,
                     step=None, **kwargs):
        return self._fill_between_x_or_y(
            "x", x, y1, y2,
            where=where, interpolate=interpolate, step=step, **kwargs)

    if _fill_between_x_or_y.__doc__:
        fill_between.__doc__ = _fill_between_x_or_y.__doc__.format(
            dir="horizontal", ind="x", dep="y"
        )
    fill_between = _preprocess_data(
        _docstring.interpd(fill_between),
        replace_names=["x", "y1", "y2", "where"])

    def fill_betweenx(self, y, x1, x2=0, where=None,
                      step=None, interpolate=False, **kwargs):
        return self._fill_between_x_or_y(
            "y", y, x1, x2,
            where=where, interpolate=interpolate, step=step, **kwargs)

    if _fill_between_x_or_y.__doc__:
        fill_betweenx.__doc__ = _fill_between_x_or_y.__doc__.format(
            dir="vertical", ind="y", dep="x"
        )
    fill_betweenx = _preprocess_data(
        _docstring.interpd(fill_betweenx),
        replace_names=["y", "x1", "x2", "where"])

    #### plotting z(x, y): imshow, pcolor and relatives, contour

    @_preprocess_data()
    @_docstring.interpd
    def imshow(self, X, cmap=None, norm=None, *, aspect=None,
               interpolation=None, alpha=None,
               vmin=None, vmax=None, colorizer=None, origin=None, extent=None,
               interpolation_stage=None, filternorm=True, filterrad=4.0,
               resample=None, url=None, **kwargs):
        """
        Display data as an image, i.e., on a 2D regular raster.

        The input may either be actual RGB(A) data, or 2D scalar data, which
        will be rendered as a pseudocolor image. For displaying a grayscale
        image, set up the colormapping using the parameters
        ``cmap='gray', vmin=0, vmax=255``.

        The number of pixels used to render an image is set by the Axes size
        and the figure *dpi*. This can lead to aliasing artifacts when
        the image is resampled, because the displayed image size will usually
        not match the size of *X* (see
        :doc:`/gallery/images_contours_and_fields/image_antialiasing`).
        The resampling can be controlled via the *interpolation* parameter
        and/or :rc:`image.interpolation`.

        Parameters
        ----------
        X : array-like or PIL image
            The image data. Supported array shapes are:

            - (M, N): an image with scalar data. The values are mapped to
              colors using normalization and a colormap. See parameters *norm*,
              *cmap*, *vmin*, *vmax*.
            - (M, N, 3): an image with RGB values (0-1 float or 0-255 int).
            - (M, N, 4): an image with RGBA values (0-1 float or 0-255 int),
              i.e. including transparency.

            The first two dimensions (M, N) define the rows and columns of
            the image.

            Out-of-range RGB(A) values are clipped.

        %(cmap_doc)s

            This parameter is ignored if *X* is RGB(A).

        %(norm_doc)s

            This parameter is ignored if *X* is RGB(A).

        %(vmin_vmax_doc)s

            This parameter is ignored if *X* is RGB(A).

        %(colorizer_doc)s

            This parameter is ignored if *X* is RGB(A).

        aspect : {'equal', 'auto'} or float or None, default: None
            The aspect ratio of the Axes.  This parameter is particularly
            relevant for images since it determines whether data pixels are
            square.

            This parameter is a shortcut for explicitly calling
            `.Axes.set_aspect`. See there for further details.

            - 'equal': Ensures an aspect ratio of 1. Pixels will be square
              (unless pixel sizes are explicitly made non-square in data
              coordinates using *extent*).
            - 'auto': The Axes is kept fixed and the aspect is adjusted so
              that the data fit in the Axes. In general, this will result in
              non-square pixels.

            Normally, None (the default) means to use :rc:`image.aspect`.  However, if
            the image uses a transform that does not contain the axes data transform,
            then None means to not modify the axes aspect at all (in that case, directly
            call `.Axes.set_aspect` if desired).

        interpolation : str, default: :rc:`image.interpolation`
            The interpolation method used.

            Supported values are 'none', 'auto', 'nearest', 'bilinear',
            'bicubic', 'spline16', 'spline36', 'hanning', 'hamming', 'hermite',
            'kaiser', 'quadric', 'catrom', 'gaussian', 'bessel', 'mitchell',
            'sinc', 'lanczos', 'blackman'.

            The data *X* is resampled to the pixel size of the image on the
            figure canvas, using the interpolation method to either up- or
            downsample the data.

            If *interpolation* is 'none', then for the ps, pdf, and svg
            backends no down- or upsampling occurs, and the image data is
            passed to the backend as a native image.  Note that different ps,
            pdf, and svg viewers may display these raw pixels differently. On
            other backends, 'none' is the same as 'nearest'.

            If *interpolation* is the default 'auto', then 'nearest'
            interpolation is used if the image is upsampled by more than a
            factor of three (i.e. the number of display pixels is at least
            three times the size of the data array).  If the upsampling rate is
            smaller than 3, or the image is downsampled, then 'hanning'
            interpolation is used to act as an anti-aliasing filter, unless the
            image happens to be upsampled by exactly a factor of two or one.

            See
            :doc:`/gallery/images_contours_and_fields/interpolation_methods`
            for an overview of the supported interpolation methods, and
            :doc:`/gallery/images_contours_and_fields/image_antialiasing` for
            a discussion of image antialiasing.

            Some interpolation methods require an additional radius parameter,
            which can be set by *filterrad*. Additionally, the antigrain image
            resize filter is controlled by the parameter *filternorm*.

        interpolation_stage : {'auto', 'data', 'rgba'}, default: 'auto'
            Supported values:

            - 'data': Interpolation is carried out on the data provided by the user
              This is useful if interpolating between pixels during upsampling.
            - 'rgba': The interpolation is carried out in RGBA-space after the
              color-mapping has been applied. This is useful if downsampling and
              combining pixels visually.
            - 'auto': Select a suitable interpolation stage automatically. This uses
              'rgba' when downsampling, or upsampling at a rate less than 3, and
              'data' when upsampling at a higher rate.

            See :doc:`/gallery/images_contours_and_fields/image_antialiasing` for
            a discussion of image antialiasing.

        alpha : float or array-like, optional
            The alpha blending value, between 0 (transparent) and 1 (opaque).
            If *alpha* is an array, the alpha blending values are applied pixel
            by pixel, and *alpha* must have the same shape as *X*.

        origin : {'upper', 'lower'}, default: :rc:`image.origin`
            Place the [0, 0] index of the array in the upper left or lower
            left corner of the Axes. The convention (the default) 'upper' is
            typically used for matrices and images.

            Note that the vertical axis points upward for 'lower'
            but downward for 'upper'.

            See the :ref:`imshow_extent` tutorial for
            examples and a more detailed description.

        extent : floats (left, right, bottom, top), optional
            The bounding box in data coordinates that the image will fill.
            These values may be unitful and match the units of the Axes.
            The image is stretched individually along x and y to fill the box.

            The default extent is determined by the following conditions.
            Pixels have unit size in data coordinates. Their centers are on
            integer coordinates, and their center coordinates range from 0 to
            columns-1 horizontally and from 0 to rows-1 vertically.

            Note that the direction of the vertical axis and thus the default
            values for top and bottom depend on *origin*:

            - For ``origin == 'upper'`` the default is
              ``(-0.5, numcols-0.5, numrows-0.5, -0.5)``.
            - For ``origin == 'lower'`` the default is
              ``(-0.5, numcols-0.5, -0.5, numrows-0.5)``.

            See the :ref:`imshow_extent` tutorial for
            examples and a more detailed description.

        filternorm : bool, default: True
            A parameter for the antigrain image resize filter (see the
            antigrain documentation).  If *filternorm* is set, the filter
            normalizes integer values and corrects the rounding errors. It
            doesn't do anything with the source floating point values, it
            corrects only integers according to the rule of 1.0 which means
            that any sum of pixel weights must be equal to 1.0.  So, the
            filter function must produce a graph of the proper shape.

        filterrad : float > 0, default: 4.0
            The filter radius for filters that have a radius parameter, i.e.
            when interpolation is one of: 'sinc', 'lanczos' or 'blackman'.

        resample : bool, default: :rc:`image.resample`
            When *True*, use a full resampling method.  When *False*, only
            resample when the output image is larger than the input image.

        url : str, optional
            Set the url of the created `.AxesImage`. See `.Artist.set_url`.

        Returns
        -------
        `~matplotlib.image.AxesImage`

        Other Parameters
        ----------------
        data : indexable object, optional
            DATA_PARAMETER_PLACEHOLDER

        **kwargs : `~matplotlib.artist.Artist` properties
            These parameters are passed on to the constructor of the
            `.AxesImage` artist.

        See Also
        --------
        matshow : Plot a matrix or an array as an image.

        Notes
        -----
        Unless *extent* is used, pixel centers will be located at integer
        coordinates. In other words: the origin will coincide with the center
        of pixel (0, 0).

        There are two common representations for RGB images with an alpha
        channel:

        -   Straight (unassociated) alpha: R, G, and B channels represent the
            color of the pixel, disregarding its opacity.
        -   Premultiplied (associated) alpha: R, G, and B channels represent
            the color of the pixel, adjusted for its opacity by multiplication.

        `~matplotlib.pyplot.imshow` expects RGB images adopting the straight
        (unassociated) alpha representation.
        """
        im = mimage.AxesImage(self, cmap=cmap, norm=norm, colorizer=colorizer,
                              interpolation=interpolation, origin=origin,
                              extent=extent, filternorm=filternorm,
                              filterrad=filterrad, resample=resample,
                              interpolation_stage=interpolation_stage,
                              **kwargs)

        if aspect is None and not (
                im.is_transform_set()
                and not im.get_transform().contains_branch(self.transData)):
            aspect = mpl.rcParams['image.aspect']
        if aspect is not None:
            self.set_aspect(aspect)

        im.set_data(X)
        im.set_alpha(alpha)
        if im.get_clip_path() is None:
            # image does not already have clipping set, clip to Axes patch
            im.set_clip_path(self.patch)
        im._check_exclusionary_keywords(colorizer, vmin=vmin, vmax=vmax)
        im._scale_norm(norm, vmin, vmax)
        im.set_url(url)

        # update ax.dataLim, and, if autoscaling, set viewLim
        # to tightly fit the image, regardless of dataLim.
        im.set_extent(im.get_extent())

        self.add_image(im)
        return im

    def _pcolorargs(self, funcname, *args, shading='auto', **kwargs):
        # - create X and Y if not present;
        # - reshape X and Y as needed if they are 1-D;
        # - check for proper sizes based on `shading` kwarg;
        # - reset shading if shading='auto' to flat or nearest
        #   depending on size;

        _valid_shading = ['gouraud', 'nearest', 'flat', 'auto']
        try:
            _api.check_in_list(_valid_shading, shading=shading)
        except ValueError:
            _api.warn_external(f"shading value '{shading}' not in list of "
                               f"valid values {_valid_shading}. Setting "
                               "shading='auto'.")
            shading = 'auto'

        if len(args) == 1:
            C = np.asanyarray(args[0])
            nrows, ncols = C.shape[:2]
            if shading in ['gouraud', 'nearest']:
                X, Y = np.meshgrid(np.arange(ncols), np.arange(nrows))
            else:
                X, Y = np.meshgrid(np.arange(ncols + 1), np.arange(nrows + 1))
                shading = 'flat'
        elif len(args) == 3:
            # Check x and y for bad data...
            C = np.asanyarray(args[2])
            # unit conversion allows e.g. datetime objects as axis values
            X, Y = args[:2]
            X, Y = self._process_unit_info([("x", X), ("y", Y)], kwargs)
            X, Y = (cbook.safe_masked_invalid(a, copy=True) for a in [X, Y])

            if funcname == 'pcolormesh':
                if np.ma.is_masked(X) or np.ma.is_masked(Y):
                    raise ValueError(
                        'x and y arguments to pcolormesh cannot have '
                        'non-finite values or be of type '
                        'numpy.ma.MaskedArray with masked values')
            nrows, ncols = C.shape[:2]
        else:
            raise _api.nargs_error(funcname, takes="1 or 3", given=len(args))

        Nx = X.shape[-1]
        Ny = Y.shape[0]
        if X.ndim != 2 or X.shape[0] == 1:
            x = X.reshape(1, Nx)
            X = x.repeat(Ny, axis=0)
        if Y.ndim != 2 or Y.shape[1] == 1:
            y = Y.reshape(Ny, 1)
            Y = y.repeat(Nx, axis=1)
        if X.shape != Y.shape:
            raise TypeError(f'Incompatible X, Y inputs to {funcname}; '
                            f'see help({funcname})')

        if shading == 'auto':
            if ncols == Nx and nrows == Ny:
                shading = 'nearest'
            else:
                shading = 'flat'

        if shading == 'flat':
            if (Nx, Ny) != (ncols + 1, nrows + 1):
                raise TypeError(f"Dimensions of C {C.shape} should"
                                f" be one smaller than X({Nx}) and Y({Ny})"
                                f" while using shading='flat'"
                                f" see help({funcname})")
        else:    # ['nearest', 'gouraud']:
            if (Nx, Ny) != (ncols, nrows):
                raise TypeError('Dimensions of C %s are incompatible with'
                                ' X (%d) and/or Y (%d); see help(%s)' % (
                                    C.shape, Nx, Ny, funcname))
            if shading == 'nearest':
                # grid is specified at the center, so define corners
                # at the midpoints between the grid centers and then use the
                # flat algorithm.
                def _interp_grid(X, require_monotonicity=False):
                    # helper for below. To ensure the cell edges are calculated
                    # correctly, when expanding columns, the monotonicity of
                    # X coords needs to be checked. When expanding rows, the
                    # monotonicity of Y coords needs to be checked.
                    if np.shape(X)[1] > 1:
                        dX = np.diff(X, axis=1) * 0.5
                        if (require_monotonicity and
                                not (np.all(dX >= 0) or np.all(dX <= 0))):
                            _api.warn_external(
                                f"The input coordinates to {funcname} are "
                                "interpreted as cell centers, but are not "
                                "monotonically increasing or decreasing. "
                                "This may lead to incorrectly calculated cell "
                                "edges, in which case, please supply "
                                f"explicit cell edges to {funcname}.")

                        hstack = np.ma.hstack if np.ma.isMA(X) else np.hstack
                        X = hstack((X[:, [0]] - dX[:, [0]],
                                    X[:, :-1] + dX,
                                    X[:, [-1]] + dX[:, [-1]]))
                    else:
                        # This is just degenerate, but we can't reliably guess
                        # a dX if there is just one value.
                        X = np.hstack((X, X))
                    return X

                if ncols == Nx:
                    X = _interp_grid(X, require_monotonicity=True)
                    Y = _interp_grid(Y)
                if nrows == Ny:
                    X = _interp_grid(X.T).T
                    Y = _interp_grid(Y.T, require_monotonicity=True).T
                shading = 'flat'

        C = cbook.safe_masked_invalid(C, copy=True)
        return X, Y, C, shading

    @_preprocess_data()
    @_docstring.interpd
    def pcolor(self, *args, shading=None, alpha=None, norm=None, cmap=None,
               vmin=None, vmax=None, colorizer=None, **kwargs):
        r"""
        Create a pseudocolor plot with a non-regular rectangular grid.

        Call signature::

            pcolor([X, Y,] C, /, **kwargs)

        *X* and *Y* can be used to specify the corners of the quadrilaterals.

        The arguments *X*, *Y*, *C* are positional-only.

        .. hint::

            ``pcolor()`` can be very slow for large arrays. In most
            cases you should use the similar but much faster
            `~.Axes.pcolormesh` instead. See
            :ref:`Differences between pcolor() and pcolormesh()
            <differences-pcolor-pcolormesh>` for a discussion of the
            differences.

        Parameters
        ----------
        C : 2D array-like
            The color-mapped values.  Color-mapping is controlled by *cmap*,
            *norm*, *vmin*, and *vmax*.

        X, Y : array-like, optional
            The coordinates of the corners of quadrilaterals of a pcolormesh::

                (X[i+1, j], Y[i+1, j])       (X[i+1, j+1], Y[i+1, j+1])
                                      ●╶───╴●
                                      │     │
                                      ●╶───╴●
                    (X[i, j], Y[i, j])       (X[i, j+1], Y[i, j+1])

            Note that the column index corresponds to the x-coordinate, and
            the row index corresponds to y. For details, see the
            :ref:`Notes <axes-pcolormesh-grid-orientation>` section below.

            If ``shading='flat'`` the dimensions of *X* and *Y* should be one
            greater than those of *C*, and the quadrilateral is colored due
            to the value at ``C[i, j]``.  If *X*, *Y* and *C* have equal
            dimensions, a warning will be raised and the last row and column
            of *C* will be ignored.

            If ``shading='nearest'``, the dimensions of *X* and *Y* should be
            the same as those of *C* (if not, a ValueError will be raised). The
            color ``C[i, j]`` will be centered on ``(X[i, j], Y[i, j])``.

            If *X* and/or *Y* are 1-D arrays or column vectors they will be
            expanded as needed into the appropriate 2D arrays, making a
            rectangular grid.

        shading : {'flat', 'nearest', 'auto'}, default: :rc:`pcolor.shading`
            The fill style for the quadrilateral. Possible values:

            - 'flat': A solid color is used for each quad. The color of the
              quad (i, j), (i+1, j), (i, j+1), (i+1, j+1) is given by
              ``C[i, j]``. The dimensions of *X* and *Y* should be
              one greater than those of *C*; if they are the same as *C*,
              then a deprecation warning is raised, and the last row
              and column of *C* are dropped.
            - 'nearest': Each grid point will have a color centered on it,
              extending halfway between the adjacent grid centers.  The
              dimensions of *X* and *Y* must be the same as *C*.
            - 'auto': Choose 'flat' if dimensions of *X* and *Y* are one
              larger than *C*.  Choose 'nearest' if dimensions are the same.

            See :doc:`/gallery/images_contours_and_fields/pcolormesh_grids`
            for more description.

        %(cmap_doc)s

        %(norm_doc)s

        %(vmin_vmax_doc)s

        %(colorizer_doc)s

        edgecolors : {'none', None, 'face', color, color sequence}, optional
            The color of the edges. Defaults to 'none'. Possible values:

            - 'none' or '': No edge.
            - *None*: :rc:`patch.edgecolor` will be used. Note that currently
              :rc:`patch.force_edgecolor` has to be True for this to work.
            - 'face': Use the adjacent face color.
            - A color or sequence of colors will set the edge color.

            The singular form *edgecolor* works as an alias.

        alpha : float, default: None
            The alpha blending value of the face color, between 0 (transparent)
            and 1 (opaque). Note: The edgecolor is currently not affected by
            this.

        snap : bool, default: False
            Whether to snap the mesh to pixel boundaries.

        Returns
        -------
        `matplotlib.collections.PolyQuadMesh`

        Other Parameters
        ----------------
        antialiaseds : bool, default: False
            The default *antialiaseds* is False if the default
            *edgecolors*\ ="none" is used.  This eliminates artificial lines
            at patch boundaries, and works regardless of the value of alpha.
            If *edgecolors* is not "none", then the default *antialiaseds*
            is taken from :rc:`patch.antialiased`.
            Stroking the edges may be preferred if *alpha* is 1, but will
            cause artifacts otherwise.

        data : indexable object, optional
            DATA_PARAMETER_PLACEHOLDER

        **kwargs
            Additionally, the following arguments are allowed. They are passed
            along to the `~matplotlib.collections.PolyQuadMesh` constructor:

        %(PolyCollection:kwdoc)s

        See Also
        --------
        pcolormesh : for an explanation of the differences between
            pcolor and pcolormesh.
        imshow : If *X* and *Y* are each equidistant, `~.Axes.imshow` can be a
            faster alternative.

        Notes
        -----
        **Masked arrays**

        *X*, *Y* and *C* may be masked arrays. If either ``C[i, j]``, or one
        of the vertices surrounding ``C[i, j]`` (*X* or *Y* at
        ``[i, j], [i+1, j], [i, j+1], [i+1, j+1]``) is masked, nothing is
        plotted.

        .. _axes-pcolor-grid-orientation:

        **Grid orientation**

        The grid orientation follows the standard matrix convention: An array
        *C* with shape (nrows, ncolumns) is plotted with the column number as
        *X* and the row number as *Y*.
        """

        if shading is None:
            shading = mpl.rcParams['pcolor.shading']
        shading = shading.lower()
        X, Y, C, shading = self._pcolorargs('pcolor', *args, shading=shading,
                                            kwargs=kwargs)
        linewidths = (0.25,)
        if 'linewidth' in kwargs:
            kwargs['linewidths'] = kwargs.pop('linewidth')
        kwargs.setdefault('linewidths', linewidths)

        if 'edgecolor' in kwargs:
            kwargs['edgecolors'] = kwargs.pop('edgecolor')
        ec = kwargs.setdefault('edgecolors', 'none')

        # aa setting will default via collections to patch.antialiased
        # unless the boundary is not stroked, in which case the
        # default will be False; with unstroked boundaries, aa
        # makes artifacts that are often disturbing.
        if 'antialiaseds' in kwargs:
            kwargs['antialiased'] = kwargs.pop('antialiaseds')
        if 'antialiased' not in kwargs and cbook._str_lower_equal(ec, "none"):
            kwargs['antialiased'] = False

        kwargs.setdefault('snap', False)

        if np.ma.isMaskedArray(X) or np.ma.isMaskedArray(Y):
            stack = np.ma.stack
            X = np.ma.asarray(X)
            Y = np.ma.asarray(Y)
            # For bounds collections later
            x = X.compressed()
            y = Y.compressed()
        else:
            stack = np.stack
            x = X
            y = Y
        coords = stack([X, Y], axis=-1)

        collection = mcoll.PolyQuadMesh(
            coords, array=C, cmap=cmap, norm=norm, colorizer=colorizer,
            alpha=alpha, **kwargs)
        collection._check_exclusionary_keywords(colorizer, vmin=vmin, vmax=vmax)
        collection._scale_norm(norm, vmin, vmax)

        # Transform from native to data coordinates?
        t = collection._transform
        if (not isinstance(t, mtransforms.Transform) and
                hasattr(t, '_as_mpl_transform')):
            t = t._as_mpl_transform(self.axes)

        if t and any(t.contains_branch_seperately(self.transData)):
            trans_to_data = t - self.transData
            pts = np.vstack([x, y]).T.astype(float)
            transformed_pts = trans_to_data.transform(pts)
            x = transformed_pts[..., 0]
            y = transformed_pts[..., 1]

        self.add_collection(collection, autolim=False)

        minx = np.min(x)
        maxx = np.max(x)
        miny = np.min(y)
        maxy = np.max(y)
        collection.sticky_edges.x[:] = [minx, maxx]
        collection.sticky_edges.y[:] = [miny, maxy]
        corners = (minx, miny), (maxx, maxy)
        self.update_datalim(corners)
        self._request_autoscale_view()
        return collection

    @_preprocess_data()
    @_docstring.interpd
    def pcolormesh(self, *args, alpha=None, norm=None, cmap=None, vmin=None,
                   vmax=None, colorizer=None, shading=None, antialiased=False,
                   **kwargs):
        """
        Create a pseudocolor plot with a non-regular rectangular grid.

        Call signature::

            pcolormesh([X, Y,] C, /, **kwargs)

        *X* and *Y* can be used to specify the corners of the quadrilaterals.

        The arguments *X*, *Y*, *C* are positional-only.

        .. hint::

           `~.Axes.pcolormesh` is similar to `~.Axes.pcolor`. It is much faster
           and preferred in most cases. For a detailed discussion on the
           differences see :ref:`Differences between pcolor() and pcolormesh()
           <differences-pcolor-pcolormesh>`.

        Parameters
        ----------
        C : array-like
            The mesh data. Supported array shapes are:

            - (M, N) or M*N: a mesh with scalar data. The values are mapped to
              colors using normalization and a colormap. See parameters *norm*,
              *cmap*, *vmin*, *vmax*.
            - (M, N, 3): an image with RGB values (0-1 float or 0-255 int).
            - (M, N, 4): an image with RGBA values (0-1 float or 0-255 int),
              i.e. including transparency.

            The first two dimensions (M, N) define the rows and columns of
            the mesh data.

        X, Y : array-like, optional
            The coordinates of the corners of quadrilaterals of a pcolormesh::

                (X[i+1, j], Y[i+1, j])       (X[i+1, j+1], Y[i+1, j+1])
                                      ●╶───╴●
                                      │     │
                                      ●╶───╴●
                    (X[i, j], Y[i, j])       (X[i, j+1], Y[i, j+1])

            Note that the column index corresponds to the x-coordinate, and
            the row index corresponds to y. For details, see the
            :ref:`Notes <axes-pcolormesh-grid-orientation>` section below.

            If ``shading='flat'`` the dimensions of *X* and *Y* should be one
            greater than those of *C*, and the quadrilateral is colored due
            to the value at ``C[i, j]``.  If *X*, *Y* and *C* have equal
            dimensions, a warning will be raised and the last row and column
            of *C* will be ignored.

            If ``shading='nearest'`` or ``'gouraud'``, the dimensions of *X*
            and *Y* should be the same as those of *C* (if not, a ValueError
            will be raised).  For ``'nearest'`` the color ``C[i, j]`` is
            centered on ``(X[i, j], Y[i, j])``.  For ``'gouraud'``, a smooth
            interpolation is carried out between the quadrilateral corners.

            If *X* and/or *Y* are 1-D arrays or column vectors they will be
            expanded as needed into the appropriate 2D arrays, making a
            rectangular grid.

        %(cmap_doc)s

        %(norm_doc)s

        %(vmin_vmax_doc)s

        %(colorizer_doc)s

        edgecolors : {'none', None, 'face', color, color sequence}, optional
            The color of the edges. Defaults to 'none'. Possible values:

            - 'none' or '': No edge.
            - *None*: :rc:`patch.edgecolor` will be used. Note that currently
              :rc:`patch.force_edgecolor` has to be True for this to work.
            - 'face': Use the adjacent face color.
            - A color or sequence of colors will set the edge color.

            The singular form *edgecolor* works as an alias.

        alpha : float, default: None
            The alpha blending value, between 0 (transparent) and 1 (opaque).

        shading : {'flat', 'nearest', 'gouraud', 'auto'}, optional
            The fill style for the quadrilateral; defaults to
            :rc:`pcolor.shading`. Possible values:

            - 'flat': A solid color is used for each quad. The color of the
              quad (i, j), (i+1, j), (i, j+1), (i+1, j+1) is given by
              ``C[i, j]``. The dimensions of *X* and *Y* should be
              one greater than those of *C*; if they are the same as *C*,
              then a deprecation warning is raised, and the last row
              and column of *C* are dropped.
            - 'nearest': Each grid point will have a color centered on it,
              extending halfway between the adjacent grid centers.  The
              dimensions of *X* and *Y* must be the same as *C*.
            - 'gouraud': Each quad will be Gouraud shaded: The color of the
              corners (i', j') are given by ``C[i', j']``. The color values of
              the area in between is interpolated from the corner values.
              The dimensions of *X* and *Y* must be the same as *C*. When
              Gouraud shading is used, *edgecolors* is ignored.
            - 'auto': Choose 'flat' if dimensions of *X* and *Y* are one
              larger than *C*.  Choose 'nearest' if dimensions are the same.

            See :doc:`/gallery/images_contours_and_fields/pcolormesh_grids`
            for more description.

        snap : bool, default: False
            Whether to snap the mesh to pixel boundaries.

        rasterized : bool, optional
            Rasterize the pcolormesh when drawing vector graphics.  This can
            speed up rendering and produce smaller files for large data sets.
            See also :doc:`/gallery/misc/rasterization_demo`.

        Returns
        -------
        `matplotlib.collections.QuadMesh`

        Other Parameters
        ----------------
        data : indexable object, optional
            DATA_PARAMETER_PLACEHOLDER

        **kwargs
            Additionally, the following arguments are allowed. They are passed
            along to the `~matplotlib.collections.QuadMesh` constructor:

        %(QuadMesh:kwdoc)s

        See Also
        --------
        pcolor : An alternative implementation with slightly different
            features. For a detailed discussion on the differences see
            :ref:`Differences between pcolor() and pcolormesh()
            <differences-pcolor-pcolormesh>`.
        imshow : If *X* and *Y* are each equidistant, `~.Axes.imshow` can be a
            faster alternative.

        Notes
        -----
        **Masked arrays**

        *C* may be a masked array. If ``C[i, j]`` is masked, the corresponding
        quadrilateral will be transparent. Masking of *X* and *Y* is not
        supported. Use `~.Axes.pcolor` if you need this functionality.

        .. _axes-pcolormesh-grid-orientation:

        **Grid orientation**

        The grid orientation follows the standard matrix convention: An array
        *C* with shape (nrows, ncolumns) is plotted with the column number as
        *X* and the row number as *Y*.

        .. _differences-pcolor-pcolormesh:

        **Differences between pcolor() and pcolormesh()**

        Both methods are used to create a pseudocolor plot of a 2D array
        using quadrilaterals.

        The main difference lies in the created object and internal data
        handling:
        While `~.Axes.pcolor` returns a `.PolyQuadMesh`, `~.Axes.pcolormesh`
        returns a `.QuadMesh`. The latter is more specialized for the given
        purpose and thus is faster. It should almost always be preferred.

        There is also a slight difference in the handling of masked arrays.
        Both `~.Axes.pcolor` and `~.Axes.pcolormesh` support masked arrays
        for *C*. However, only `~.Axes.pcolor` supports masked arrays for *X*
        and *Y*. The reason lies in the internal handling of the masked values.
        `~.Axes.pcolor` leaves out the respective polygons from the
        PolyQuadMesh. `~.Axes.pcolormesh` sets the facecolor of the masked
        elements to transparent. You can see the difference when using
        edgecolors. While all edges are drawn irrespective of masking in a
        QuadMesh, the edge between two adjacent masked quadrilaterals in
        `~.Axes.pcolor` is not drawn as the corresponding polygons do not
        exist in the PolyQuadMesh. Because PolyQuadMesh draws each individual
        polygon, it also supports applying hatches and linestyles to the collection.

        Another difference is the support of Gouraud shading in
        `~.Axes.pcolormesh`, which is not available with `~.Axes.pcolor`.

        """
        if shading is None:
            shading = mpl.rcParams['pcolor.shading']
        shading = shading.lower()
        kwargs.setdefault('edgecolors', 'none')

        X, Y, C, shading = self._pcolorargs('pcolormesh', *args,
                                            shading=shading, kwargs=kwargs)
        coords = np.stack([X, Y], axis=-1)

        kwargs.setdefault('snap', mpl.rcParams['pcolormesh.snap'])

        collection = mcoll.QuadMesh(
            coords, antialiased=antialiased, shading=shading,
            array=C, cmap=cmap, norm=norm, colorizer=colorizer, alpha=alpha, **kwargs)
        collection._check_exclusionary_keywords(colorizer, vmin=vmin, vmax=vmax)
        collection._scale_norm(norm, vmin, vmax)

        coords = coords.reshape(-1, 2)  # flatten the grid structure; keep x, y

        # Transform from native to data coordinates?
        t = collection._transform
        if (not isinstance(t, mtransforms.Transform) and
                hasattr(t, '_as_mpl_transform')):
            t = t._as_mpl_transform(self.axes)

        if t and any(t.contains_branch_seperately(self.transData)):
            trans_to_data = t - self.transData
            coords = trans_to_data.transform(coords)

        self.add_collection(collection, autolim=False)

        minx, miny = np.min(coords, axis=0)
        maxx, maxy = np.max(coords, axis=0)
        collection.sticky_edges.x[:] = [minx, maxx]
        collection.sticky_edges.y[:] = [miny, maxy]
        corners = (minx, miny), (maxx, maxy)
        self.update_datalim(corners)
        self._request_autoscale_view()
        return collection

    @_preprocess_data()
    @_docstring.interpd
    def pcolorfast(self, *args, alpha=None, norm=None, cmap=None, vmin=None,
                   vmax=None, colorizer=None, **kwargs):
        """
        Create a pseudocolor plot with a non-regular rectangular grid.

        Call signature::

            ax.pcolorfast([X, Y], C, /, **kwargs)

        The arguments *X*, *Y*, *C* are positional-only.

        This method is similar to `~.Axes.pcolor` and `~.Axes.pcolormesh`.
        It's designed to provide the fastest pcolor-type plotting with the
        Agg backend. To achieve this, it uses different algorithms internally
        depending on the complexity of the input grid (regular rectangular,
        non-regular rectangular or arbitrary quadrilateral).

        .. warning::

            This method is experimental. Compared to `~.Axes.pcolor` or
            `~.Axes.pcolormesh` it has some limitations:

            - It supports only flat shading (no outlines)
            - It lacks support for log scaling of the axes.
            - It does not have a pyplot wrapper.

        Parameters
        ----------
        C : array-like
            The image data. Supported array shapes are:

            - (M, N): an image with scalar data.  Color-mapping is controlled
              by *cmap*, *norm*, *vmin*, and *vmax*.
            - (M, N, 3): an image with RGB values (0-1 float or 0-255 int).
            - (M, N, 4): an image with RGBA values (0-1 float or 0-255 int),
              i.e. including transparency.

            The first two dimensions (M, N) define the rows and columns of
            the image.

            This parameter can only be passed positionally.

        X, Y : tuple or array-like, default: ``(0, N)``, ``(0, M)``
            *X* and *Y* are used to specify the coordinates of the
            quadrilaterals. There are different ways to do this:

            - Use tuples ``X=(xmin, xmax)`` and ``Y=(ymin, ymax)`` to define
              a *uniform rectangular grid*.

              The tuples define the outer edges of the grid. All individual
              quadrilaterals will be of the same size. This is the fastest
              version.

            - Use 1D arrays *X*, *Y* to specify a *non-uniform rectangular
              grid*.

              In this case *X* and *Y* have to be monotonic 1D arrays of length
              *N+1* and *M+1*, specifying the x and y boundaries of the cells.

              The speed is intermediate. Note: The grid is checked, and if
              found to be uniform the fast version is used.

            - Use 2D arrays *X*, *Y* if you need an *arbitrary quadrilateral
              grid* (i.e. if the quadrilaterals are not rectangular).

              In this case *X* and *Y* are 2D arrays with shape (M + 1, N + 1),
              specifying the x and y coordinates of the corners of the colored
              quadrilaterals.

              This is the most general, but the slowest to render.  It may
              produce faster and more compact output using ps, pdf, and
              svg backends, however.

            These arguments can only be passed positionally.

        %(cmap_doc)s

            This parameter is ignored if *C* is RGB(A).

        %(norm_doc)s

            This parameter is ignored if *C* is RGB(A).

        %(vmin_vmax_doc)s

            This parameter is ignored if *C* is RGB(A).

        %(colorizer_doc)s

            This parameter is ignored if *C* is RGB(A).

        alpha : float, default: None
            The alpha blending value, between 0 (transparent) and 1 (opaque).

        snap : bool, default: False
            Whether to snap the mesh to pixel boundaries.

        Returns
        -------
        `.AxesImage` or `.PcolorImage` or `.QuadMesh`
            The return type depends on the type of grid:

            - `.AxesImage` for a regular rectangular grid.
            - `.PcolorImage` for a non-regular rectangular grid.
            - `.QuadMesh` for a non-rectangular grid.

        Other Parameters
        ----------------
        data : indexable object, optional
            DATA_PARAMETER_PLACEHOLDER

        **kwargs
            Supported additional parameters depend on the type of grid.
            See return types of *image* for further description.
        """

        C = args[-1]
        nr, nc = np.shape(C)[:2]
        if len(args) == 1:
            style = "image"
            x = [0, nc]
            y = [0, nr]
        elif len(args) == 3:
            x, y = args[:2]
            x = np.asarray(x)
            y = np.asarray(y)
            if x.ndim == 1 and y.ndim == 1:
                if x.size == 2 and y.size == 2:
                    style = "image"
                else:
                    if x.size != nc + 1:
                        raise ValueError(
                            f"Length of X ({x.size}) must be one larger than the "
                            f"number of columns in C ({nc})")
                    if y.size != nr + 1:
                        raise ValueError(
                            f"Length of Y ({y.size}) must be one larger than the "
                            f"number of rows in C ({nr})"
                        )
                    dx = np.diff(x)
                    dy = np.diff(y)
                    if (np.ptp(dx) < 0.01 * abs(dx.mean()) and
                            np.ptp(dy) < 0.01 * abs(dy.mean())):
                        style = "image"
                    else:
                        style = "pcolorimage"
            elif x.ndim == 2 and y.ndim == 2:
                style = "quadmesh"
            else:
                raise TypeError(
                    f"When 3 positional parameters are passed to pcolorfast, the first "
                    f"two (X and Y) must be both 1D or both 2D; the given X was "
                    f"{x.ndim}D and the given Y was {y.ndim}D")
        else:
            raise _api.nargs_error('pcolorfast', '1 or 3', len(args))

        mcolorizer.ColorizingArtist._check_exclusionary_keywords(colorizer, vmin=vmin,
                                                                 vmax=vmax)
        if style == "quadmesh":
            # data point in each cell is value at lower left corner
            coords = np.stack([x, y], axis=-1)
            if np.ndim(C) not in {2, 3}:
                raise ValueError("C must be 2D or 3D")
            collection = mcoll.QuadMesh(
                coords, array=C,
                alpha=alpha, cmap=cmap, norm=norm, colorizer=colorizer,
                antialiased=False, edgecolors="none")
            self.add_collection(collection, autolim=False)
            xl, xr, yb, yt = x.min(), x.max(), y.min(), y.max()
            ret = collection

        else:  # It's one of the two image styles.
            extent = xl, xr, yb, yt = x[0], x[-1], y[0], y[-1]
            if style == "image":
                im = mimage.AxesImage(
                    self, cmap=cmap, norm=norm, colorizer=colorizer,
                    data=C, alpha=alpha, extent=extent,
                    interpolation='nearest', origin='lower',
                    **kwargs)
            elif style == "pcolorimage":
                im = mimage.PcolorImage(
                    self, x, y, C,
                    cmap=cmap, norm=norm, colorizer=colorizer, alpha=alpha,
                    extent=extent, **kwargs)
            self.add_image(im)
            ret = im

        if np.ndim(C) == 2:  # C.ndim == 3 is RGB(A) so doesn't need scaling.
            ret._scale_norm(norm, vmin, vmax)

        if ret.get_clip_path() is None:
            # image does not already have clipping set, clip to Axes patch
            ret.set_clip_path(self.patch)

        ret.sticky_edges.x[:] = [xl, xr]
        ret.sticky_edges.y[:] = [yb, yt]
        self.update_datalim(np.array([[xl, yb], [xr, yt]]))
        self._request_autoscale_view(tight=True)
        return ret

    @_preprocess_data()
    @_docstring.interpd
    def contour(self, *args, **kwargs):
        """
        Plot contour lines.

        Call signature::

            contour([X, Y,] Z, /, [levels], **kwargs)

        The arguments *X*, *Y*, *Z* are positional-only.
        %(contour_doc)s
        """
        kwargs['filled'] = False
        contours = mcontour.QuadContourSet(self, *args, **kwargs)
        self._request_autoscale_view()
        return contours

    @_preprocess_data()
    @_docstring.interpd
    def contourf(self, *args, **kwargs):
        """
        Plot filled contours.

        Call signature::

            contourf([X, Y,] Z, /, [levels], **kwargs)

        The arguments *X*, *Y*, *Z* are positional-only.
        %(contour_doc)s
        """
        kwargs['filled'] = True
        contours = mcontour.QuadContourSet(self, *args, **kwargs)
        self._request_autoscale_view()
        return contours

    def clabel(self, CS, levels=None, **kwargs):
        """
        Label a contour plot.

        Adds labels to line contours in given `.ContourSet`.

        Parameters
        ----------
        CS : `.ContourSet` instance
            Line contours to label.

        levels : array-like, optional
            A list of level values, that should be labeled. The list must be
            a subset of ``CS.levels``. If not given, all levels are labeled.

        **kwargs
            All other parameters are documented in `~.ContourLabeler.clabel`.
        """
        return CS.clabel(levels, **kwargs)

    #### Data analysis

    @_api.make_keyword_only("3.10", "range")
    @_preprocess_data(replace_names=["x", 'weights'], label_namer="x")
    def hist(self, x, bins=None, range=None, density=False, weights=None,
             cumulative=False, bottom=None, histtype='bar', align='mid',
             orientation='vertical', rwidth=None, log=False,
             color=None, label=None, stacked=False, **kwargs):
        """
        Compute and plot a histogram.

        This method uses `numpy.histogram` to bin the data in *x* and count the
        number of values in each bin, then draws the distribution either as a
        `.BarContainer` or `.Polygon`. The *bins*, *range*, *density*, and
        *weights* parameters are forwarded to `numpy.histogram`.

        If the data has already been binned and counted, use `~.bar` or
        `~.stairs` to plot the distribution::

            counts, bins = np.histogram(x)
            plt.stairs(counts, bins)

        Alternatively, plot pre-computed bins and counts using ``hist()`` by
        treating each bin as a single point with a weight equal to its count::

            plt.hist(bins[:-1], bins, weights=counts)

        The data input *x* can be a singular array, a list of datasets of
        potentially different lengths ([*x0*, *x1*, ...]), or a 2D ndarray in
        which each column is a dataset. Note that the ndarray form is
        transposed relative to the list form. If the input is an array, then
        the return value is a tuple (*n*, *bins*, *patches*); if the input is a
        sequence of arrays, then the return value is a tuple
        ([*n0*, *n1*, ...], *bins*, [*patches0*, *patches1*, ...]).

        Masked arrays are not supported.

        Parameters
        ----------
        x : (n,) array or sequence of (n,) arrays
            Input values, this takes either a single array or a sequence of
            arrays which are not required to be of the same length.

        bins : int or sequence or str, default: :rc:`hist.bins`
            If *bins* is an integer, it defines the number of equal-width bins
            in the range.

            If *bins* is a sequence, it defines the bin edges, including the
            left edge of the first bin and the right edge of the last bin;
            in this case, bins may be unequally spaced.  All but the last
            (righthand-most) bin is half-open.  In other words, if *bins* is::

                [1, 2, 3, 4]

            then the first bin is ``[1, 2)`` (including 1, but excluding 2) and
            the second ``[2, 3)``.  The last bin, however, is ``[3, 4]``, which
            *includes* 4.

            If *bins* is a string, it is one of the binning strategies
            supported by `numpy.histogram_bin_edges`: 'auto', 'fd', 'doane',
            'scott', 'stone', 'rice', 'sturges', or 'sqrt'.

        range : tuple or None, default: None
            The lower and upper range of the bins. Lower and upper outliers
            are ignored. If not provided, *range* is ``(x.min(), x.max())``.
            Range has no effect if *bins* is a sequence.

            If *bins* is a sequence or *range* is specified, autoscaling
            is based on the specified bin range instead of the
            range of x.

        density : bool, default: False
            If ``True``, draw and return a probability density: each bin
            will display the bin's raw count divided by the total number of
            counts *and the bin width*
            (``density = counts / (sum(counts) * np.diff(bins))``),
            so that the area under the histogram integrates to 1
            (``np.sum(density * np.diff(bins)) == 1``).

            If *stacked* is also ``True``, the sum of the histograms is
            normalized to 1.

        weights : (n,) array-like or None, default: None
            An array of weights, of the same shape as *x*.  Each value in
            *x* only contributes its associated weight towards the bin count
            (instead of 1).  If *density* is ``True``, the weights are
            normalized, so that the integral of the density over the range
            remains 1.

        cumulative : bool or -1, default: False
            If ``True``, then a histogram is computed where each bin gives the
            counts in that bin plus all bins for smaller values. The last bin
            gives the total number of datapoints.

            If *density* is also ``True`` then the histogram is normalized such
            that the last bin equals 1.

            If *cumulative* is a number less than 0 (e.g., -1), the direction
            of accumulation is reversed.  In this case, if *density* is also
            ``True``, then the histogram is normalized such that the first bin
            equals 1.

        bottom : array-like or float, default: 0
            Location of the bottom of each bin, i.e. bins are drawn from
            ``bottom`` to ``bottom + hist(x, bins)`` If a scalar, the bottom
            of each bin is shifted by the same amount. If an array, each bin
            is shifted independently and the length of bottom must match the
            number of bins. If None, defaults to 0.

        histtype : {'bar', 'barstacked', 'step', 'stepfilled'}, default: 'bar'
            The type of histogram to draw.

            - 'bar' is a traditional bar-type histogram.  If multiple data
              are given the bars are arranged side by side.
            - 'barstacked' is a bar-type histogram where multiple
              data are stacked on top of each other.
            - 'step' generates a lineplot that is by default unfilled.
            - 'stepfilled' generates a lineplot that is by default filled.

        align : {'left', 'mid', 'right'}, default: 'mid'
            The horizontal alignment of the histogram bars.

            - 'left': bars are centered on the left bin edges.
            - 'mid': bars are centered between the bin edges.
            - 'right': bars are centered on the right bin edges.

        orientation : {'vertical', 'horizontal'}, default: 'vertical'
            If 'horizontal', `~.Axes.barh` will be used for bar-type histograms
            and the *bottom* kwarg will be the left edges.

        rwidth : float or None, default: None
            The relative width of the bars as a fraction of the bin width.  If
            ``None``, automatically compute the width.

            Ignored if *histtype* is 'step' or 'stepfilled'.

        log : bool, default: False
            If ``True``, the histogram axis will be set to a log scale.

        color : :mpltype:`color` or list of :mpltype:`color` or None, default: None
            Color or sequence of colors, one per dataset.  Default (``None``)
            uses the standard line color sequence.

        label : str or list of str, optional
            String, or sequence of strings to match multiple datasets.  Bar
            charts yield multiple patches per dataset, but only the first gets
            the label, so that `~.Axes.legend` will work as expected.

        stacked : bool, default: False
            If ``True``, multiple data are stacked on top of each other If
            ``False`` multiple data are arranged side by side if histtype is
            'bar' or on top of each other if histtype is 'step'

        Returns
        -------
        n : array or list of arrays
            The values of the histogram bins. See *density* and *weights* for a
            description of the possible semantics.  If input *x* is an array,
            then this is an array of length *nbins*. If input is a sequence of
            arrays ``[data1, data2, ...]``, then this is a list of arrays with
            the values of the histograms for each of the arrays in the same
            order.  The dtype of the array *n* (or of its element arrays) will
            always be float even if no weighting or normalization is used.

        bins : array
            The edges of the bins. Length nbins + 1 (nbins left edges and right
            edge of last bin).  Always a single array even when multiple data
            sets are passed in.

        patches : `.BarContainer` or list of a single `.Polygon` or list of \
such objects
            Container of individual artists used to create the histogram
            or list of such containers if there are multiple input datasets.

        Other Parameters
        ----------------
        data : indexable object, optional
            DATA_PARAMETER_PLACEHOLDER

        **kwargs
            `~matplotlib.patches.Patch` properties. The following properties
            additionally accept a sequence of values corresponding to the
            datasets in *x*:
            *edgecolor*, *facecolor*, *linewidth*, *linestyle*, *hatch*.

            .. versionadded:: 3.10
               Allowing sequences of values in above listed Patch properties.

        See Also
        --------
        hist2d : 2D histogram with rectangular bins
        hexbin : 2D histogram with hexagonal bins
        stairs : Plot a pre-computed histogram
        bar : Plot a pre-computed histogram

        Notes
        -----
        For large numbers of bins (>1000), plotting can be significantly
        accelerated by using `~.Axes.stairs` to plot a pre-computed histogram
        (``plt.stairs(*np.histogram(data))``), or by setting *histtype* to
        'step' or 'stepfilled' rather than 'bar' or 'barstacked'.
        """
        # Avoid shadowing the builtin.
        bin_range = range
        from builtins import range

        kwargs = cbook.normalize_kwargs(kwargs, mpatches.Patch)

        if np.isscalar(x):
            x = [x]

        if bins is None:
            bins = mpl.rcParams['hist.bins']

        # Validate string inputs here to avoid cluttering subsequent code.
        _api.check_in_list(['bar', 'barstacked', 'step', 'stepfilled'],
                           histtype=histtype)
        _api.check_in_list(['left', 'mid', 'right'], align=align)
        _api.check_in_list(['horizontal', 'vertical'], orientation=orientation)

        if histtype == 'barstacked' and not stacked:
            stacked = True

        # Massage 'x' for processing.
        x = cbook._reshape_2D(x, 'x')
        nx = len(x)  # number of datasets

        # Process unit information.  _process_unit_info sets the unit and
        # converts the first dataset; then we convert each following dataset
        # one at a time.
        if orientation == "vertical":
            convert_units = self.convert_xunits
            x = [*self._process_unit_info([("x", x[0])], kwargs),
                 *map(convert_units, x[1:])]
        else:  # horizontal
            convert_units = self.convert_yunits
            x = [*self._process_unit_info([("y", x[0])], kwargs),
                 *map(convert_units, x[1:])]

        if bin_range is not None:
            bin_range = convert_units(bin_range)

        if not cbook.is_scalar_or_string(bins):
            bins = convert_units(bins)

        # We need to do to 'weights' what was done to 'x'
        if weights is not None:
            w = cbook._reshape_2D(weights, 'weights')
        else:
            w = [None] * nx

        if len(w) != nx:
            raise ValueError('weights should have the same shape as x')

        input_empty = True
        for xi, wi in zip(x, w):
            len_xi = len(xi)
            if wi is not None and len(wi) != len_xi:
                raise ValueError('weights should have the same shape as x')
            if len_xi:
                input_empty = False

        if color is None:
            colors = [self._get_lines.get_next_color() for i in range(nx)]
        else:
            colors = mcolors.to_rgba_array(color)
            if len(colors) != nx:
                raise ValueError(f"The 'color' keyword argument must have one "
                                 f"color per dataset, but {nx} datasets and "
                                 f"{len(colors)} colors were provided")

        hist_kwargs = dict()

        # if the bin_range is not given, compute without nan numpy
        # does not do this for us when guessing the range (but will
        # happily ignore nans when computing the histogram).
        if bin_range is None:
            xmin = np.inf
            xmax = -np.inf
            for xi in x:
                if len(xi):
                    # python's min/max ignore nan,
                    # np.minnan returns nan for all nan input
                    xmin = min(xmin, np.nanmin(xi))
                    xmax = max(xmax, np.nanmax(xi))
            if xmin <= xmax:  # Only happens if we have seen a finite value.
                bin_range = (xmin, xmax)

        # If bins are not specified either explicitly or via range,
        # we need to figure out the range required for all datasets,
        # and supply that to np.histogram.
        if not input_empty and len(x) > 1:
            if weights is not None:
                _w = np.concatenate(w)
            else:
                _w = None
            bins = np.histogram_bin_edges(
                np.concatenate(x), bins, bin_range, _w)
        else:
            hist_kwargs['range'] = bin_range

        density = bool(density)
        if density and not stacked:
            hist_kwargs['density'] = density

        # List to store all the top coordinates of the histograms
        tops = []  # Will have shape (n_datasets, n_bins).
        # Loop through datasets
        for i in range(nx):
            # this will automatically overwrite bins,
            # so that each histogram uses the same bins
            m, bins = np.histogram(x[i], bins, weights=w[i], **hist_kwargs)
            tops.append(m)
        tops = np.array(tops, float)  # causes problems later if it's an int
        bins = np.array(bins, float)  # causes problems if float16
        if stacked:
            tops = tops.cumsum(axis=0)
            # If a stacked density plot, normalize so the area of all the
            # stacked histograms together is 1
            if density:
                tops = (tops / np.diff(bins)) / tops[-1].sum()
        if cumulative:
            slc = slice(None)
            if isinstance(cumulative, Number) and cumulative < 0:
                slc = slice(None, None, -1)
            if density:
                tops = (tops * np.diff(bins))[:, slc].cumsum(axis=1)[:, slc]
            else:
                tops = tops[:, slc].cumsum(axis=1)[:, slc]

        patches = []

        if histtype.startswith('bar'):

            totwidth = np.diff(bins)

            if rwidth is not None:
                dr = np.clip(rwidth, 0, 1)
            elif (len(tops) > 1 and
                  ((not stacked) or mpl.rcParams['_internal.classic_mode'])):
                dr = 0.8
            else:
                dr = 1.0

            if histtype == 'bar' and not stacked:
                width = dr * totwidth / nx
                dw = width
                boffset = -0.5 * dr * totwidth * (1 - 1 / nx)
            elif histtype == 'barstacked' or stacked:
                width = dr * totwidth
                boffset, dw = 0.0, 0.0

            if align == 'mid':
                boffset += 0.5 * totwidth
            elif align == 'right':
                boffset += totwidth

            if orientation == 'horizontal':
                _barfunc = self.barh
                bottom_kwarg = 'left'
            else:  # orientation == 'vertical'
                _barfunc = self.bar
                bottom_kwarg = 'bottom'

            for top, color in zip(tops, colors):
                if bottom is None:
                    bottom = np.zeros(len(top))
                if stacked:
                    height = top - bottom
                else:
                    height = top
                bars = _barfunc(bins[:-1]+boffset, height, width,
                                align='center', log=log,
                                color=color, **{bottom_kwarg: bottom})
                patches.append(bars)
                if stacked:
                    bottom = top
                boffset += dw
            # Remove stickies from all bars but the lowest ones, as otherwise
            # margin expansion would be unable to cross the stickies in the
            # middle of the bars.
            for bars in patches[1:]:
                for patch in bars:
                    patch.sticky_edges.x[:] = patch.sticky_edges.y[:] = []

        elif histtype.startswith('step'):
            # these define the perimeter of the polygon
            x = np.zeros(4 * len(bins) - 3)
            y = np.zeros(4 * len(bins) - 3)

            x[0:2*len(bins)-1:2], x[1:2*len(bins)-1:2] = bins, bins[:-1]
            x[2*len(bins)-1:] = x[1:2*len(bins)-1][::-1]

            if bottom is None:
                bottom = 0

            y[1:2*len(bins)-1:2] = y[2:2*len(bins):2] = bottom
            y[2*len(bins)-1:] = y[1:2*len(bins)-1][::-1]

            if log:
                if orientation == 'horizontal':
                    self.set_xscale('log', nonpositive='clip')
                else:  # orientation == 'vertical'
                    self.set_yscale('log', nonpositive='clip')

            if align == 'left':
                x -= 0.5*(bins[1]-bins[0])
            elif align == 'right':
                x += 0.5*(bins[1]-bins[0])

            # If fill kwarg is set, it will be passed to the patch collection,
            # overriding this
            fill = (histtype == 'stepfilled')

            xvals, yvals = [], []
            for top in tops:
                if stacked:
                    # top of the previous polygon becomes the bottom
                    y[2*len(bins)-1:] = y[1:2*len(bins)-1][::-1]
                # set the top of this polygon
                y[1:2*len(bins)-1:2] = y[2:2*len(bins):2] = top + bottom

                # The starting point of the polygon has not yet been
                # updated. So far only the endpoint was adjusted. This
                # assignment closes the polygon. The redundant endpoint is
                # later discarded (for step and stepfilled).
                y[0] = y[-1]

                if orientation == 'horizontal':
                    xvals.append(y.copy())
                    yvals.append(x.copy())
                else:
                    xvals.append(x.copy())
                    yvals.append(y.copy())

            # stepfill is closed, step is not
            split = -1 if fill else 2 * len(bins)
            # add patches in reverse order so that when stacking,
            # items lower in the stack are plotted on top of
            # items higher in the stack
            for x, y, color in reversed(list(zip(xvals, yvals, colors))):
                patches.append(self.fill(
                    x[:split], y[:split],
                    closed=True if fill else None,
                    facecolor=color,
                    edgecolor=None if fill else color,
                    fill=fill if fill else None,
                    zorder=None if fill else mlines.Line2D.zorder))
            for patch_list in patches:
                for patch in patch_list:
                    if orientation == 'vertical':
                        patch.sticky_edges.y.append(0)
                    elif orientation == 'horizontal':
                        patch.sticky_edges.x.append(0)

            # we return patches, so put it back in the expected order
            patches.reverse()

        # If None, make all labels None (via zip_longest below); otherwise,
        # cast each element to str, but keep a single str as it.
        labels = [] if label is None else np.atleast_1d(np.asarray(label, str))

        if histtype == "step":
            ec = kwargs.get('edgecolor', colors)
        else:
            ec = kwargs.get('edgecolor', None)
        if ec is None or cbook._str_lower_equal(ec, 'none'):
            edgecolors = itertools.repeat(ec)
        else:
            edgecolors = itertools.cycle(mcolors.to_rgba_array(ec))

        fc = kwargs.get('facecolor', colors)
        if cbook._str_lower_equal(fc, 'none'):
            facecolors = itertools.repeat(fc)
        else:
            facecolors = itertools.cycle(mcolors.to_rgba_array(fc))

        hatches = itertools.cycle(np.atleast_1d(kwargs.get('hatch', None)))
        linewidths = itertools.cycle(np.atleast_1d(kwargs.get('linewidth', None)))
        if 'linestyle' in kwargs:
            linestyles = itertools.cycle(mlines._get_dash_patterns(kwargs['linestyle']))
        else:
            linestyles = itertools.repeat(None)

        for patch, lbl in itertools.zip_longest(patches, labels):
            if not patch:
                continue
            p = patch[0]
            kwargs.update({
                'hatch': next(hatches),
                'linewidth': next(linewidths),
                'linestyle': next(linestyles),
                'edgecolor': next(edgecolors),
                'facecolor': next(facecolors),
            })
            p._internal_update(kwargs)
            if lbl is not None:
                p.set_label(lbl)
            for p in patch[1:]:
                p._internal_update(kwargs)
                p.set_label('_nolegend_')

        if nx == 1:
            return tops[0], bins, patches[0]
        else:
            patch_type = ("BarContainer" if histtype.startswith("bar")
                          else "list[Polygon]")
            return tops, bins, cbook.silent_list(patch_type, patches)

    @_preprocess_data()
    def stairs(self, values, edges=None, *,
               orientation='vertical', baseline=0, fill=False, **kwargs):
        """
        Draw a stepwise constant function as a line or a filled plot.

        *edges* define the x-axis positions of the steps. *values* the function values
        between these steps. Depending on *fill*, the function is drawn either as a
        continuous line with vertical segments at the edges, or as a filled area.

        Parameters
        ----------
        values : array-like
            The step heights.

        edges : array-like
            The step positions, with ``len(edges) == len(vals) + 1``,
            between which the curve takes on vals values.

        orientation : {'vertical', 'horizontal'}, default: 'vertical'
            The direction of the steps. Vertical means that *values* are along
            the y-axis, and edges are along the x-axis.

        baseline : float, array-like or None, default: 0
            The bottom value of the bounding edges or when
            ``fill=True``, position of lower edge. If *fill* is
            True or an array is passed to *baseline*, a closed
            path is drawn.

            If None, then drawn as an unclosed Path.

        fill : bool, default: False
            Whether the area under the step curve should be filled.

            Passing both ``fill=True` and ``baseline=None`` will likely result in
            undesired filling: the first and last points will be connected
            with a straight line and the fill will be between this line and the stairs.


        Returns
        -------
        StepPatch : `~matplotlib.patches.StepPatch`

        Other Parameters
        ----------------
        data : indexable object, optional
            DATA_PARAMETER_PLACEHOLDER

        **kwargs
            `~matplotlib.patches.StepPatch` properties

        """

        if 'color' in kwargs:
            _color = kwargs.pop('color')
        else:
            _color = self._get_lines.get_next_color()
        if fill:
            kwargs.setdefault('linewidth', 0)
            kwargs.setdefault('facecolor', _color)
        else:
            kwargs.setdefault('edgecolor', _color)

        if edges is None:
            edges = np.arange(len(values) + 1)

        edges, values, baseline = self._process_unit_info(
            [("x", edges), ("y", values), ("y", baseline)], kwargs)

        patch = mpatches.StepPatch(values,
                                   edges,
                                   baseline=baseline,
                                   orientation=orientation,
                                   fill=fill,
                                   **kwargs)
        self.add_patch(patch)
        if baseline is None and fill:
            _api.warn_external(
                f"Both {baseline=} and {fill=} have been passed. "
                "baseline=None is only intended for unfilled stair plots. "
                "Because baseline is None, the Path used to draw the stairs will "
                "not be closed, thus because fill is True the polygon will be closed "
                "by drawing an (unstroked) edge from the first to last point.  It is "
                "very likely that the resulting fill patterns is not the desired "
                "result."
            )

        if baseline is not None:
            if orientation == 'vertical':
                patch.sticky_edges.y.append(np.min(baseline))
                self.update_datalim([(edges[0], np.min(baseline))])
            else:
                patch.sticky_edges.x.append(np.min(baseline))
                self.update_datalim([(np.min(baseline), edges[0])])
        self._request_autoscale_view()
        return patch

    @_api.make_keyword_only("3.10", "range")
    @_preprocess_data(replace_names=["x", "y", "weights"])
    @_docstring.interpd
    def hist2d(self, x, y, bins=10, range=None, density=False, weights=None,
               cmin=None, cmax=None, **kwargs):
        """
        Make a 2D histogram plot.

        Parameters
        ----------
        x, y : array-like, shape (n, )
            Input values

        bins : None or int or [int, int] or array-like or [array, array]

            The bin specification:

            - If int, the number of bins for the two dimensions
              (``nx = ny = bins``).
            - If ``[int, int]``, the number of bins in each dimension
              (``nx, ny = bins``).
            - If array-like, the bin edges for the two dimensions
              (``x_edges = y_edges = bins``).
            - If ``[array, array]``, the bin edges in each dimension
              (``x_edges, y_edges = bins``).

            The default value is 10.

        range : array-like shape(2, 2), optional
            The leftmost and rightmost edges of the bins along each dimension
            (if not specified explicitly in the bins parameters): ``[[xmin,
            xmax], [ymin, ymax]]``. All values outside of this range will be
            considered outliers and not tallied in the histogram.

        density : bool, default: False
            Normalize histogram.  See the documentation for the *density*
            parameter of `~.Axes.hist` for more details.

        weights : array-like, shape (n, ), optional
            An array of values w_i weighing each sample (x_i, y_i).

        cmin, cmax : float, default: None
            All bins that has count less than *cmin* or more than *cmax* will not be
            displayed (set to NaN before passing to `~.Axes.pcolormesh`) and these count
            values in the return value count histogram will also be set to nan upon
            return.

        Returns
        -------
        h : 2D array
            The bi-dimensional histogram of samples x and y. Values in x are
            histogrammed along the first dimension and values in y are
            histogrammed along the second dimension.
        xedges : 1D array
            The bin edges along the x-axis.
        yedges : 1D array
            The bin edges along the y-axis.
        image : `~.matplotlib.collections.QuadMesh`

        Other Parameters
        ----------------
        %(cmap_doc)s

        %(norm_doc)s

        %(vmin_vmax_doc)s

        %(colorizer_doc)s

        alpha : ``0 <= scalar <= 1`` or ``None``, optional
            The alpha blending value.

        data : indexable object, optional
            DATA_PARAMETER_PLACEHOLDER

        **kwargs
            Additional parameters are passed along to the
            `~.Axes.pcolormesh` method and `~matplotlib.collections.QuadMesh`
            constructor.

        See Also
        --------
        hist : 1D histogram plotting
        hexbin : 2D histogram with hexagonal bins

        Notes
        -----
        - Currently ``hist2d`` calculates its own axis limits, and any limits
          previously set are ignored.
        - Rendering the histogram with a logarithmic color scale is
          accomplished by passing a `.colors.LogNorm` instance to the *norm*
          keyword argument. Likewise, power-law normalization (similar
          in effect to gamma correction) can be accomplished with
          `.colors.PowerNorm`.
        """

        h, xedges, yedges = np.histogram2d(x, y, bins=bins, range=range,
                                           density=density, weights=weights)

        if cmin is not None:
            h[h < cmin] = None
        if cmax is not None:
            h[h > cmax] = None

        pc = self.pcolormesh(xedges, yedges, h.T, **kwargs)
        self.set_xlim(xedges[0], xedges[-1])
        self.set_ylim(yedges[0], yedges[-1])

        return h, xedges, yedges, pc

    @_preprocess_data(replace_names=["x", "weights"], label_namer="x")
    @_docstring.interpd
    def ecdf(self, x, weights=None, *, complementary=False,
             orientation="vertical", compress=False, **kwargs):
        """
        Compute and plot the empirical cumulative distribution function of *x*.

        .. versionadded:: 3.8

        Parameters
        ----------
        x : 1d array-like
            The input data.  Infinite entries are kept (and move the relevant
            end of the ecdf from 0/1), but NaNs and masked values are errors.

        weights : 1d array-like or None, default: None
            The weights of the entries; must have the same shape as *x*.
            Weights corresponding to NaN data points are dropped, and then the
            remaining weights are normalized to sum to 1.  If unset, all
            entries have the same weight.

        complementary : bool, default: False
            Whether to plot a cumulative distribution function, which increases
            from 0 to 1 (the default), or a complementary cumulative
            distribution function, which decreases from 1 to 0.

        orientation : {"vertical", "horizontal"}, default: "vertical"
            Whether the entries are plotted along the x-axis ("vertical", the
            default) or the y-axis ("horizontal").  This parameter takes the
            same values as in `~.Axes.hist`.

        compress : bool, default: False
            Whether multiple entries with the same values are grouped together
            (with a summed weight) before plotting.  This is mainly useful if
            *x* contains many identical data points, to decrease the rendering
            complexity of the plot. If *x* contains no duplicate points, this
            has no effect and just uses some time and memory.

        Other Parameters
        ----------------
        data : indexable object, optional
            DATA_PARAMETER_PLACEHOLDER

        **kwargs
            Keyword arguments control the `.Line2D` properties:

            %(Line2D:kwdoc)s

        Returns
        -------
        `.Line2D`

        Notes
        -----
        The ecdf plot can be thought of as a cumulative histogram with one bin
        per data entry; i.e. it reports on the entire dataset without any
        arbitrary binning.

        If *x* contains NaNs or masked entries, either remove them first from
        the array (if they should not taken into account), or replace them by
        -inf or +inf (if they should be sorted at the beginning or the end of
        the array).
        """
        _api.check_in_list(["horizontal", "vertical"], orientation=orientation)
        if "drawstyle" in kwargs or "ds" in kwargs:
            raise TypeError("Cannot pass 'drawstyle' or 'ds' to ecdf()")
        if np.ma.getmask(x).any():
            raise ValueError("ecdf() does not support masked entries")
        x = np.asarray(x)
        if np.isnan(x).any():
            raise ValueError("ecdf() does not support NaNs")
        argsort = np.argsort(x)
        x = x[argsort]
        if weights is None:
            # Ensure that we end at exactly 1, avoiding floating point errors.
            cum_weights = (1 + np.arange(len(x))) / len(x)
        else:
            weights = np.take(weights, argsort)   # Reorder weights like we reordered x.
            cum_weights = np.cumsum(weights / np.sum(weights))
        if compress:
            # Get indices of unique x values.
            compress_idxs = [0, *(x[:-1] != x[1:]).nonzero()[0] + 1]
            x = x[compress_idxs]
            cum_weights = cum_weights[compress_idxs]
        if orientation == "vertical":
            if not complementary:
                line, = self.plot([x[0], *x], [0, *cum_weights],
                                  drawstyle="steps-post", **kwargs)
            else:
                line, = self.plot([*x, x[-1]], [1, *1 - cum_weights],
                                  drawstyle="steps-pre", **kwargs)
            line.sticky_edges.y[:] = [0, 1]
        else:  # orientation == "horizontal":
            if not complementary:
                line, = self.plot([0, *cum_weights], [x[0], *x],
                                  drawstyle="steps-pre", **kwargs)
            else:
                line, = self.plot([1, *1 - cum_weights], [*x, x[-1]],
                                  drawstyle="steps-post", **kwargs)
            line.sticky_edges.x[:] = [0, 1]
        return line

    @_api.make_keyword_only("3.10", "NFFT")
    @_preprocess_data(replace_names=["x"])
    @_docstring.interpd
    def psd(self, x, NFFT=None, Fs=None, Fc=None, detrend=None,
            window=None, noverlap=None, pad_to=None,
            sides=None, scale_by_freq=None, return_line=None, **kwargs):
        r"""
        Plot the power spectral density.

        The power spectral density :math:`P_{xx}` by Welch's average
        periodogram method.  The vector *x* is divided into *NFFT* length
        segments.  Each segment is detrended by function *detrend* and
        windowed by function *window*.  *noverlap* gives the length of
        the overlap between segments.  The :math:`|\mathrm{fft}(i)|^2`
        of each segment :math:`i` are averaged to compute :math:`P_{xx}`,
        with a scaling to correct for power loss due to windowing.

        If len(*x*) < *NFFT*, it will be zero padded to *NFFT*.

        Parameters
        ----------
        x : 1-D array or sequence
            Array or sequence containing the data

        %(Spectral)s

        %(PSD)s

        noverlap : int, default: 0 (no overlap)
            The number of points of overlap between segments.

        Fc : int, default: 0
            The center frequency of *x*, which offsets the x extents of the
            plot to reflect the frequency range used when a signal is acquired
            and then filtered and downsampled to baseband.

        return_line : bool, default: False
            Whether to include the line object plotted in the returned values.

        Returns
        -------
        Pxx : 1-D array
            The values for the power spectrum :math:`P_{xx}` before scaling
            (real valued).

        freqs : 1-D array
            The frequencies corresponding to the elements in *Pxx*.

        line : `~matplotlib.lines.Line2D`
            The line created by this function.
            Only returned if *return_line* is True.

        Other Parameters
        ----------------
        data : indexable object, optional
            DATA_PARAMETER_PLACEHOLDER

        **kwargs
            Keyword arguments control the `.Line2D` properties:

            %(Line2D:kwdoc)s

        See Also
        --------
        specgram
            Differs in the default overlap; in not returning the mean of the
            segment periodograms; in returning the times of the segments; and
            in plotting a colormap instead of a line.
        magnitude_spectrum
            Plots the magnitude spectrum.
        csd
            Plots the spectral density between two signals.

        Notes
        -----
        For plotting, the power is plotted as
        :math:`10\log_{10}(P_{xx})` for decibels, though *Pxx* itself
        is returned.

        References
        ----------
        Bendat & Piersol -- Random Data: Analysis and Measurement Procedures,
        John Wiley & Sons (1986)
        """
        if Fc is None:
            Fc = 0

        pxx, freqs = mlab.psd(x=x, NFFT=NFFT, Fs=Fs, detrend=detrend,
                              window=window, noverlap=noverlap, pad_to=pad_to,
                              sides=sides, scale_by_freq=scale_by_freq)
        freqs += Fc

        if scale_by_freq in (None, True):
            psd_units = 'dB/Hz'
        else:
            psd_units = 'dB'

        line = self.plot(freqs, 10 * np.log10(pxx), **kwargs)
        self.set_xlabel('Frequency')
        self.set_ylabel('Power Spectral Density (%s)' % psd_units)
        self.grid(True)

        vmin, vmax = self.get_ybound()
        step = max(10 * int(np.log10(vmax - vmin)), 1)
        ticks = np.arange(math.floor(vmin), math.ceil(vmax) + 1, step)
        self.set_yticks(ticks)

        if return_line is None or not return_line:
            return pxx, freqs
        else:
            return pxx, freqs, line

    @_api.make_keyword_only("3.10", "NFFT")
    @_preprocess_data(replace_names=["x", "y"], label_namer="y")
    @_docstring.interpd
    def csd(self, x, y, NFFT=None, Fs=None, Fc=None, detrend=None,
            window=None, noverlap=None, pad_to=None,
            sides=None, scale_by_freq=None, return_line=None, **kwargs):
        r"""
        Plot the cross-spectral density.

        The cross spectral density :math:`P_{xy}` by Welch's average
        periodogram method.  The vectors *x* and *y* are divided into
        *NFFT* length segments.  Each segment is detrended by function
        *detrend* and windowed by function *window*.  *noverlap* gives
        the length of the overlap between segments.  The product of
        the direct FFTs of *x* and *y* are averaged over each segment
        to compute :math:`P_{xy}`, with a scaling to correct for power
        loss due to windowing.

        If len(*x*) < *NFFT* or len(*y*) < *NFFT*, they will be zero
        padded to *NFFT*.

        Parameters
        ----------
        x, y : 1-D arrays or sequences
            Arrays or sequences containing the data.

        %(Spectral)s

        %(PSD)s

        noverlap : int, default: 0 (no overlap)
            The number of points of overlap between segments.

        Fc : int, default: 0
            The center frequency of *x*, which offsets the x extents of the
            plot to reflect the frequency range used when a signal is acquired
            and then filtered and downsampled to baseband.

        return_line : bool, default: False
            Whether to include the line object plotted in the returned values.

        Returns
        -------
        Pxy : 1-D array
            The values for the cross spectrum :math:`P_{xy}` before scaling
            (complex valued).

        freqs : 1-D array
            The frequencies corresponding to the elements in *Pxy*.

        line : `~matplotlib.lines.Line2D`
            The line created by this function.
            Only returned if *return_line* is True.

        Other Parameters
        ----------------
        data : indexable object, optional
            DATA_PARAMETER_PLACEHOLDER

        **kwargs
            Keyword arguments control the `.Line2D` properties:

            %(Line2D:kwdoc)s

        See Also
        --------
        psd : is equivalent to setting ``y = x``.

        Notes
        -----
        For plotting, the power is plotted as
        :math:`10 \log_{10}(P_{xy})` for decibels, though :math:`P_{xy}` itself
        is returned.

        References
        ----------
        Bendat & Piersol -- Random Data: Analysis and Measurement Procedures,
        John Wiley & Sons (1986)
        """
        if Fc is None:
            Fc = 0

        pxy, freqs = mlab.csd(x=x, y=y, NFFT=NFFT, Fs=Fs, detrend=detrend,
                              window=window, noverlap=noverlap, pad_to=pad_to,
                              sides=sides, scale_by_freq=scale_by_freq)
        # pxy is complex
        freqs += Fc

        line = self.plot(freqs, 10 * np.log10(np.abs(pxy)), **kwargs)
        self.set_xlabel('Frequency')
        self.set_ylabel('Cross Spectrum Magnitude (dB)')
        self.grid(True)

        vmin, vmax = self.get_ybound()
        step = max(10 * int(np.log10(vmax - vmin)), 1)
        ticks = np.arange(math.floor(vmin), math.ceil(vmax) + 1, step)
        self.set_yticks(ticks)

        if return_line is None or not return_line:
            return pxy, freqs
        else:
            return pxy, freqs, line

    @_api.make_keyword_only("3.10", "Fs")
    @_preprocess_data(replace_names=["x"])
    @_docstring.interpd
    def magnitude_spectrum(self, x, Fs=None, Fc=None, window=None,
                           pad_to=None, sides=None, scale=None,
                           **kwargs):
        """
        Plot the magnitude spectrum.

        Compute the magnitude spectrum of *x*.  Data is padded to a
        length of *pad_to* and the windowing function *window* is applied to
        the signal.

        Parameters
        ----------
        x : 1-D array or sequence
            Array or sequence containing the data.

        %(Spectral)s

        %(Single_Spectrum)s

        scale : {'default', 'linear', 'dB'}
            The scaling of the values in the *spec*.  'linear' is no scaling.
            'dB' returns the values in dB scale, i.e., the dB amplitude
            (20 * log10). 'default' is 'linear'.

        Fc : int, default: 0
            The center frequency of *x*, which offsets the x extents of the
            plot to reflect the frequency range used when a signal is acquired
            and then filtered and downsampled to baseband.

        Returns
        -------
        spectrum : 1-D array
            The values for the magnitude spectrum before scaling (real valued).

        freqs : 1-D array
            The frequencies corresponding to the elements in *spectrum*.

        line : `~matplotlib.lines.Line2D`
            The line created by this function.

        Other Parameters
        ----------------
        data : indexable object, optional
            DATA_PARAMETER_PLACEHOLDER

        **kwargs
            Keyword arguments control the `.Line2D` properties:

            %(Line2D:kwdoc)s

        See Also
        --------
        psd
            Plots the power spectral density.
        angle_spectrum
            Plots the angles of the corresponding frequencies.
        phase_spectrum
            Plots the phase (unwrapped angle) of the corresponding frequencies.
        specgram
            Can plot the magnitude spectrum of segments within the signal in a
            colormap.
        """
        if Fc is None:
            Fc = 0

        spec, freqs = mlab.magnitude_spectrum(x=x, Fs=Fs, window=window,
                                              pad_to=pad_to, sides=sides)
        freqs += Fc

        yunits = _api.check_getitem(
            {None: 'energy', 'default': 'energy', 'linear': 'energy',
             'dB': 'dB'},
            scale=scale)
        if yunits == 'energy':
            Z = spec
        else:  # yunits == 'dB'
            Z = 20. * np.log10(spec)

        line, = self.plot(freqs, Z, **kwargs)
        self.set_xlabel('Frequency')
        self.set_ylabel('Magnitude (%s)' % yunits)

        return spec, freqs, line

    @_api.make_keyword_only("3.10", "Fs")
    @_preprocess_data(replace_names=["x"])
    @_docstring.interpd
    def angle_spectrum(self, x, Fs=None, Fc=None, window=None,
                       pad_to=None, sides=None, **kwargs):
        """
        Plot the angle spectrum.

        Compute the angle spectrum (wrapped phase spectrum) of *x*.
        Data is padded to a length of *pad_to* and the windowing function
        *window* is applied to the signal.

        Parameters
        ----------
        x : 1-D array or sequence
            Array or sequence containing the data.

        %(Spectral)s

        %(Single_Spectrum)s

        Fc : int, default: 0
            The center frequency of *x*, which offsets the x extents of the
            plot to reflect the frequency range used when a signal is acquired
            and then filtered and downsampled to baseband.

        Returns
        -------
        spectrum : 1-D array
            The values for the angle spectrum in radians (real valued).

        freqs : 1-D array
            The frequencies corresponding to the elements in *spectrum*.

        line : `~matplotlib.lines.Line2D`
            The line created by this function.

        Other Parameters
        ----------------
        data : indexable object, optional
            DATA_PARAMETER_PLACEHOLDER

        **kwargs
            Keyword arguments control the `.Line2D` properties:

            %(Line2D:kwdoc)s

        See Also
        --------
        magnitude_spectrum
            Plots the magnitudes of the corresponding frequencies.
        phase_spectrum
            Plots the unwrapped version of this function.
        specgram
            Can plot the angle spectrum of segments within the signal in a
            colormap.
        """
        if Fc is None:
            Fc = 0

        spec, freqs = mlab.angle_spectrum(x=x, Fs=Fs, window=window,
                                          pad_to=pad_to, sides=sides)
        freqs += Fc

        lines = self.plot(freqs, spec, **kwargs)
        self.set_xlabel('Frequency')
        self.set_ylabel('Angle (radians)')

        return spec, freqs, lines[0]

    @_api.make_keyword_only("3.10", "Fs")
    @_preprocess_data(replace_names=["x"])
    @_docstring.interpd
    def phase_spectrum(self, x, Fs=None, Fc=None, window=None,
                       pad_to=None, sides=None, **kwargs):
        """
        Plot the phase spectrum.

        Compute the phase spectrum (unwrapped angle spectrum) of *x*.
        Data is padded to a length of *pad_to* and the windowing function
        *window* is applied to the signal.

        Parameters
        ----------
        x : 1-D array or sequence
            Array or sequence containing the data

        %(Spectral)s

        %(Single_Spectrum)s

        Fc : int, default: 0
            The center frequency of *x*, which offsets the x extents of the
            plot to reflect the frequency range used when a signal is acquired
            and then filtered and downsampled to baseband.

        Returns
        -------
        spectrum : 1-D array
            The values for the phase spectrum in radians (real valued).

        freqs : 1-D array
            The frequencies corresponding to the elements in *spectrum*.

        line : `~matplotlib.lines.Line2D`
            The line created by this function.

        Other Parameters
        ----------------
        data : indexable object, optional
            DATA_PARAMETER_PLACEHOLDER

        **kwargs
            Keyword arguments control the `.Line2D` properties:

            %(Line2D:kwdoc)s

        See Also
        --------
        magnitude_spectrum
            Plots the magnitudes of the corresponding frequencies.
        angle_spectrum
            Plots the wrapped version of this function.
        specgram
            Can plot the phase spectrum of segments within the signal in a
            colormap.
        """
        if Fc is None:
            Fc = 0

        spec, freqs = mlab.phase_spectrum(x=x, Fs=Fs, window=window,
                                          pad_to=pad_to, sides=sides)
        freqs += Fc

        lines = self.plot(freqs, spec, **kwargs)
        self.set_xlabel('Frequency')
        self.set_ylabel('Phase (radians)')

        return spec, freqs, lines[0]

    @_api.make_keyword_only("3.10", "NFFT")
    @_preprocess_data(replace_names=["x", "y"])
    @_docstring.interpd
    def cohere(self, x, y, NFFT=256, Fs=2, Fc=0, detrend=mlab.detrend_none,
               window=mlab.window_hanning, noverlap=0, pad_to=None,
               sides='default', scale_by_freq=None, **kwargs):
        r"""
        Plot the coherence between *x* and *y*.

        Coherence is the normalized cross spectral density:

        .. math::

          C_{xy} = \frac{|P_{xy}|^2}{P_{xx}P_{yy}}

        Parameters
        ----------
        %(Spectral)s

        %(PSD)s

        noverlap : int, default: 0 (no overlap)
            The number of points of overlap between blocks.

        Fc : int, default: 0
            The center frequency of *x*, which offsets the x extents of the
            plot to reflect the frequency range used when a signal is acquired
            and then filtered and downsampled to baseband.

        Returns
        -------
        Cxy : 1-D array
            The coherence vector.

        freqs : 1-D array
            The frequencies for the elements in *Cxy*.

        Other Parameters
        ----------------
        data : indexable object, optional
            DATA_PARAMETER_PLACEHOLDER

        **kwargs
            Keyword arguments control the `.Line2D` properties:

            %(Line2D:kwdoc)s

        References
        ----------
        Bendat & Piersol -- Random Data: Analysis and Measurement Procedures,
        John Wiley & Sons (1986)
        """
        cxy, freqs = mlab.cohere(x=x, y=y, NFFT=NFFT, Fs=Fs, detrend=detrend,
                                 window=window, noverlap=noverlap,
                                 scale_by_freq=scale_by_freq, sides=sides,
                                 pad_to=pad_to)
        freqs += Fc

        self.plot(freqs, cxy, **kwargs)
        self.set_xlabel('Frequency')
        self.set_ylabel('Coherence')
        self.grid(True)

        return cxy, freqs

    @_api.make_keyword_only("3.10", "NFFT")
    @_preprocess_data(replace_names=["x"])
    @_docstring.interpd
    def specgram(self, x, NFFT=None, Fs=None, Fc=None, detrend=None,
                 window=None, noverlap=None,
                 cmap=None, xextent=None, pad_to=None, sides=None,
                 scale_by_freq=None, mode=None, scale=None,
                 vmin=None, vmax=None, **kwargs):
        """
        Plot a spectrogram.

        Compute and plot a spectrogram of data in *x*.  Data are split into
        *NFFT* length segments and the spectrum of each section is
        computed.  The windowing function *window* is applied to each
        segment, and the amount of overlap of each segment is
        specified with *noverlap*. The spectrogram is plotted as a colormap
        (using imshow).

        Parameters
        ----------
        x : 1-D array or sequence
            Array or sequence containing the data.

        %(Spectral)s

        %(PSD)s

        mode : {'default', 'psd', 'magnitude', 'angle', 'phase'}
            What sort of spectrum to use.  Default is 'psd', which takes the
            power spectral density.  'magnitude' returns the magnitude
            spectrum.  'angle' returns the phase spectrum without unwrapping.
            'phase' returns the phase spectrum with unwrapping.

        noverlap : int, default: 128
            The number of points of overlap between blocks.

        scale : {'default', 'linear', 'dB'}
            The scaling of the values in the *spec*.  'linear' is no scaling.
            'dB' returns the values in dB scale.  When *mode* is 'psd',
            this is dB power (10 * log10).  Otherwise, this is dB amplitude
            (20 * log10). 'default' is 'dB' if *mode* is 'psd' or
            'magnitude' and 'linear' otherwise.  This must be 'linear'
            if *mode* is 'angle' or 'phase'.

        Fc : int, default: 0
            The center frequency of *x*, which offsets the x extents of the
            plot to reflect the frequency range used when a signal is acquired
            and then filtered and downsampled to baseband.

        cmap : `.Colormap`, default: :rc:`image.cmap`

        xextent : *None* or (xmin, xmax)
            The image extent along the x-axis. The default sets *xmin* to the
            left border of the first bin (*spectrum* column) and *xmax* to the
            right border of the last bin. Note that for *noverlap>0* the width
            of the bins is smaller than those of the segments.

        data : indexable object, optional
            DATA_PARAMETER_PLACEHOLDER

        vmin, vmax : float, optional
            vmin and vmax define the data range that the colormap covers.
            By default, the colormap covers the complete value range of the
            data.

        **kwargs
            Additional keyword arguments are passed on to `~.axes.Axes.imshow`
            which makes the specgram image. The origin keyword argument
            is not supported.

        Returns
        -------
        spectrum : 2D array
            Columns are the periodograms of successive segments.

        freqs : 1-D array
            The frequencies corresponding to the rows in *spectrum*.

        t : 1-D array
            The times corresponding to midpoints of segments (i.e., the columns
            in *spectrum*).

        im : `.AxesImage`
            The image created by imshow containing the spectrogram.

        See Also
        --------
        psd
            Differs in the default overlap; in returning the mean of the
            segment periodograms; in not returning times; and in generating a
            line plot instead of colormap.
        magnitude_spectrum
            A single spectrum, similar to having a single segment when *mode*
            is 'magnitude'. Plots a line instead of a colormap.
        angle_spectrum
            A single spectrum, similar to having a single segment when *mode*
            is 'angle'. Plots a line instead of a colormap.
        phase_spectrum
            A single spectrum, similar to having a single segment when *mode*
            is 'phase'. Plots a line instead of a colormap.

        Notes
        -----
        The parameters *detrend* and *scale_by_freq* do only apply when *mode*
        is set to 'psd'.
        """
        if NFFT is None:
            NFFT = 256  # same default as in mlab.specgram()
        if Fc is None:
            Fc = 0  # same default as in mlab._spectral_helper()
        if noverlap is None:
            noverlap = 128  # same default as in mlab.specgram()
        if Fs is None:
            Fs = 2  # same default as in mlab._spectral_helper()

        if mode == 'complex':
            raise ValueError('Cannot plot a complex specgram')

        if scale is None or scale == 'default':
            if mode in ['angle', 'phase']:
                scale = 'linear'
            else:
                scale = 'dB'
        elif mode in ['angle', 'phase'] and scale == 'dB':
            raise ValueError('Cannot use dB scale with angle or phase mode')

        spec, freqs, t = mlab.specgram(x=x, NFFT=NFFT, Fs=Fs,
                                       detrend=detrend, window=window,
                                       noverlap=noverlap, pad_to=pad_to,
                                       sides=sides,
                                       scale_by_freq=scale_by_freq,
                                       mode=mode)

        if scale == 'linear':
            Z = spec
        elif scale == 'dB':
            if mode is None or mode == 'default' or mode == 'psd':
                Z = 10. * np.log10(spec)
            else:
                Z = 20. * np.log10(spec)
        else:
            raise ValueError(f'Unknown scale {scale!r}')

        Z = np.flipud(Z)

        if xextent is None:
            # padding is needed for first and last segment:
            pad_xextent = (NFFT-noverlap) / Fs / 2
            xextent = np.min(t) - pad_xextent, np.max(t) + pad_xextent
        xmin, xmax = xextent
        freqs += Fc
        extent = xmin, xmax, freqs[0], freqs[-1]

        if 'origin' in kwargs:
            raise _api.kwarg_error("specgram", "origin")

        im = self.imshow(Z, cmap, extent=extent, vmin=vmin, vmax=vmax,
                         origin='upper', **kwargs)
        self.axis('auto')

        return spec, freqs, t, im

    @_api.make_keyword_only("3.10", "precision")
    @_docstring.interpd
    def spy(self, Z, precision=0, marker=None, markersize=None,
            aspect='equal', origin="upper", **kwargs):
        """
        Plot the sparsity pattern of a 2D array.

        This visualizes the non-zero values of the array.

        Two plotting styles are available: image and marker. Both
        are available for full arrays, but only the marker style
        works for `scipy.sparse.spmatrix` instances.

        **Image style**

        If *marker* and *markersize* are *None*, `~.Axes.imshow` is used. Any
        extra remaining keyword arguments are passed to this method.

        **Marker style**

        If *Z* is a `scipy.sparse.spmatrix` or *marker* or *markersize* are
        *None*, a `.Line2D` object will be returned with the value of marker
        determining the marker type, and any remaining keyword arguments
        passed to `~.Axes.plot`.

        Parameters
        ----------
        Z : (M, N) array-like
            The array to be plotted.

        precision : float or 'present', default: 0
            If *precision* is 0, any non-zero value will be plotted. Otherwise,
            values of :math:`|Z| > precision` will be plotted.

            For `scipy.sparse.spmatrix` instances, you can also
            pass 'present'. In this case any value present in the array
            will be plotted, even if it is identically zero.

        aspect : {'equal', 'auto', None} or float, default: 'equal'
            The aspect ratio of the Axes.  This parameter is particularly
            relevant for images since it determines whether data pixels are
            square.

            This parameter is a shortcut for explicitly calling
            `.Axes.set_aspect`. See there for further details.

            - 'equal': Ensures an aspect ratio of 1. Pixels will be square.
            - 'auto': The Axes is kept fixed and the aspect is adjusted so
              that the data fit in the Axes. In general, this will result in
              non-square pixels.
            - *None*: Use :rc:`image.aspect`.

        origin : {'upper', 'lower'}, default: :rc:`image.origin`
            Place the [0, 0] index of the array in the upper left or lower left
            corner of the Axes. The convention 'upper' is typically used for
            matrices and images.

        Returns
        -------
        `~matplotlib.image.AxesImage` or `.Line2D`
            The return type depends on the plotting style (see above).

        Other Parameters
        ----------------
        **kwargs
            The supported additional parameters depend on the plotting style.

            For the image style, you can pass the following additional
            parameters of `~.Axes.imshow`:

            - *cmap*
            - *alpha*
            - *url*
            - any `.Artist` properties (passed on to the `.AxesImage`)

            For the marker style, you can pass any `.Line2D` property except
            for *linestyle*:

            %(Line2D:kwdoc)s
        """
        if marker is None and markersize is None and hasattr(Z, 'tocoo'):
            marker = 's'
        _api.check_in_list(["upper", "lower"], origin=origin)
        if marker is None and markersize is None:
            Z = np.asarray(Z)
            mask = np.abs(Z) > precision

            if 'cmap' not in kwargs:
                kwargs['cmap'] = mcolors.ListedColormap(['w', 'k'],
                                                        name='binary')
            if 'interpolation' in kwargs:
                raise _api.kwarg_error("spy", "interpolation")
            if 'norm' not in kwargs:
                kwargs['norm'] = mcolors.NoNorm()
            ret = self.imshow(mask, interpolation='nearest',
                              aspect=aspect, origin=origin,
                              **kwargs)
        else:
            if hasattr(Z, 'tocoo'):
                c = Z.tocoo()
                if precision == 'present':
                    y = c.row
                    x = c.col
                else:
                    nonzero = np.abs(c.data) > precision
                    y = c.row[nonzero]
                    x = c.col[nonzero]
            else:
                Z = np.asarray(Z)
                nonzero = np.abs(Z) > precision
                y, x = np.nonzero(nonzero)
            if marker is None:
                marker = 's'
            if markersize is None:
                markersize = 10
            if 'linestyle' in kwargs:
                raise _api.kwarg_error("spy", "linestyle")
            ret = mlines.Line2D(
                x, y, linestyle='None', marker=marker, markersize=markersize,
                **kwargs)
            self.add_line(ret)
            nr, nc = Z.shape
            self.set_xlim(-0.5, nc - 0.5)
            if origin == "upper":
                self.set_ylim(nr - 0.5, -0.5)
            else:
                self.set_ylim(-0.5, nr - 0.5)
            self.set_aspect(aspect)
        self.title.set_y(1.05)
        if origin == "upper":
            self.xaxis.tick_top()
        else:  # lower
            self.xaxis.tick_bottom()
        self.xaxis.set_ticks_position('both')
        self.xaxis.set_major_locator(
            mticker.MaxNLocator(nbins=9, steps=[1, 2, 5, 10], integer=True))
        self.yaxis.set_major_locator(
            mticker.MaxNLocator(nbins=9, steps=[1, 2, 5, 10], integer=True))
        return ret

    def matshow(self, Z, **kwargs):
        """
        Plot the values of a 2D matrix or array as color-coded image.

        The matrix will be shown the way it would be printed, with the first
        row at the top.  Row and column numbering is zero-based.

        Parameters
        ----------
        Z : (M, N) array-like
            The matrix to be displayed.

        Returns
        -------
        `~matplotlib.image.AxesImage`

        Other Parameters
        ----------------
        **kwargs : `~matplotlib.axes.Axes.imshow` arguments

        See Also
        --------
        imshow : More general function to plot data on a 2D regular raster.

        Notes
        -----
        This is just a convenience function wrapping `.imshow` to set useful
        defaults for displaying a matrix. In particular:

        - Set ``origin='upper'``.
        - Set ``interpolation='nearest'``.
        - Set ``aspect='equal'``.
        - Ticks are placed to the left and above.
        - Ticks are formatted to show integer indices.

        """
        Z = np.asanyarray(Z)
        kw = {'origin': 'upper',
              'interpolation': 'nearest',
              'aspect': 'equal',          # (already the imshow default)
              **kwargs}
        im = self.imshow(Z, **kw)
        self.title.set_y(1.05)
        self.xaxis.tick_top()
        self.xaxis.set_ticks_position('both')
        self.xaxis.set_major_locator(
            mticker.MaxNLocator(nbins=9, steps=[1, 2, 5, 10], integer=True))
        self.yaxis.set_major_locator(
            mticker.MaxNLocator(nbins=9, steps=[1, 2, 5, 10], integer=True))
        return im

    @_api.make_keyword_only("3.10", "vert")
    @_preprocess_data(replace_names=["dataset"])
    def violinplot(self, dataset, positions=None, vert=None,
                   orientation='vertical', widths=0.5, showmeans=False,
                   showextrema=True, showmedians=False, quantiles=None,
                   points=100, bw_method=None, side='both',):
        """
        Make a violin plot.

        Make a violin plot for each column of *dataset* or each vector in
        sequence *dataset*.  Each filled area extends to represent the
        entire data range, with optional lines at the mean, the median,
        the minimum, the maximum, and user-specified quantiles.

        Parameters
        ----------
        dataset : Array or a sequence of vectors.
            The input data.

        positions : array-like, default: [1, 2, ..., n]
            The positions of the violins; i.e. coordinates on the x-axis for
            vertical violins (or y-axis for horizontal violins).

        vert : bool, optional
            .. deprecated:: 3.10
                Use *orientation* instead.

                If this is given during the deprecation period, it overrides
                the *orientation* parameter.

            If True, plots the violins vertically.
            If False, plots the violins horizontally.

        orientation : {'vertical', 'horizontal'}, default: 'vertical'
            If 'horizontal', plots the violins horizontally.
            Otherwise, plots the violins vertically.

            .. versionadded:: 3.10

        widths : float or array-like, default: 0.5
            The maximum width of each violin in units of the *positions* axis.
            The default is 0.5, which is half the available space when using default
            *positions*.

        showmeans : bool, default: False
            Whether to show the mean with a line.

        showextrema : bool, default: True
            Whether to show extrema with a line.

        showmedians : bool, default: False
            Whether to show the median with a line.

        quantiles : array-like, default: None
            If not None, set a list of floats in interval [0, 1] for each violin,
            which stands for the quantiles that will be rendered for that
            violin.

        points : int, default: 100
            The number of points to evaluate each of the gaussian kernel density
            estimations at.

        bw_method : {'scott', 'silverman'} or float or callable, default: 'scott'
            The method used to calculate the estimator bandwidth.  If a
            float, this will be used directly as `kde.factor`.  If a
            callable, it should take a `matplotlib.mlab.GaussianKDE` instance as
            its only parameter and return a float.

        side : {'both', 'low', 'high'}, default: 'both'
            'both' plots standard violins. 'low'/'high' only
            plots the side below/above the positions value.

        data : indexable object, optional
            DATA_PARAMETER_PLACEHOLDER

        Returns
        -------
        dict
            A dictionary mapping each component of the violinplot to a
            list of the corresponding collection instances created. The
            dictionary has the following keys:

            - ``bodies``: A list of the `~.collections.PolyCollection`
              instances containing the filled area of each violin.

            - ``cmeans``: A `~.collections.LineCollection` instance that marks
              the mean values of each of the violin's distribution.

            - ``cmins``: A `~.collections.LineCollection` instance that marks
              the bottom of each violin's distribution.

            - ``cmaxes``: A `~.collections.LineCollection` instance that marks
              the top of each violin's distribution.

            - ``cbars``: A `~.collections.LineCollection` instance that marks
              the centers of each violin's distribution.

            - ``cmedians``: A `~.collections.LineCollection` instance that
              marks the median values of each of the violin's distribution.

            - ``cquantiles``: A `~.collections.LineCollection` instance created
              to identify the quantile values of each of the violin's
              distribution.

        See Also
        --------
        .Axes.violin : Draw a violin from pre-computed statistics.
        boxplot : Draw a box and whisker plot.
        """

        def _kde_method(X, coords):
            # Unpack in case of e.g. Pandas or xarray object
            X = cbook._unpack_to_numpy(X)
            # fallback gracefully if the vector contains only one value
            if np.all(X[0] == X):
                return (X[0] == coords).astype(float)
            kde = mlab.GaussianKDE(X, bw_method)
            return kde.evaluate(coords)

        vpstats = cbook.violin_stats(dataset, _kde_method, points=points,
                                     quantiles=quantiles)
        return self.violin(vpstats, positions=positions, vert=vert,
                           orientation=orientation, widths=widths,
                           showmeans=showmeans, showextrema=showextrema,
                           showmedians=showmedians, side=side)

    @_api.make_keyword_only("3.10", "vert")
    def violin(self, vpstats, positions=None, vert=None,
               orientation='vertical', widths=0.5, showmeans=False,
               showextrema=True, showmedians=False, side='both'):
        """
        Draw a violin plot from pre-computed statistics.

        Draw a violin plot for each column of *vpstats*. Each filled area
        extends to represent the entire data range, with optional lines at the
        mean, the median, the minimum, the maximum, and the quantiles values.

        Parameters
        ----------
        vpstats : list of dicts
            A list of dictionaries containing stats for each violin plot.
            Required keys are:

            - ``coords``: A list of scalars containing the coordinates that
              the violin's kernel density estimate were evaluated at.

            - ``vals``: A list of scalars containing the values of the
              kernel density estimate at each of the coordinates given
              in *coords*.

            - ``mean``: The mean value for this violin's dataset.

            - ``median``: The median value for this violin's dataset.

            - ``min``: The minimum value for this violin's dataset.

            - ``max``: The maximum value for this violin's dataset.

            Optional keys are:

            - ``quantiles``: A list of scalars containing the quantile values
              for this violin's dataset.

        positions : array-like, default: [1, 2, ..., n]
            The positions of the violins; i.e. coordinates on the x-axis for
            vertical violins (or y-axis for horizontal violins).

        vert : bool, optional
            .. deprecated:: 3.10
                Use *orientation* instead.

                If this is given during the deprecation period, it overrides
                the *orientation* parameter.

            If True, plots the violins vertically.
            If False, plots the violins horizontally.

        orientation : {'vertical', 'horizontal'}, default: 'vertical'
            If 'horizontal', plots the violins horizontally.
            Otherwise, plots the violins vertically.

            .. versionadded:: 3.10

        widths : float or array-like, default: 0.5
            The maximum width of each violin in units of the *positions* axis.
            The default is 0.5, which is half available space when using default
            *positions*.

        showmeans : bool, default: False
            Whether to show the mean with a line.

        showextrema : bool, default: True
            Whether to show extrema with a line.

        showmedians : bool, default: False
            Whether to show the median with a line.

        side : {'both', 'low', 'high'}, default: 'both'
            'both' plots standard violins. 'low'/'high' only
            plots the side below/above the positions value.

        Returns
        -------
        dict
            A dictionary mapping each component of the violinplot to a
            list of the corresponding collection instances created. The
            dictionary has the following keys:

            - ``bodies``: A list of the `~.collections.PolyCollection`
              instances containing the filled area of each violin.

            - ``cmeans``: A `~.collections.LineCollection` instance that marks
              the mean values of each of the violin's distribution.

            - ``cmins``: A `~.collections.LineCollection` instance that marks
              the bottom of each violin's distribution.

            - ``cmaxes``: A `~.collections.LineCollection` instance that marks
              the top of each violin's distribution.

            - ``cbars``: A `~.collections.LineCollection` instance that marks
              the centers of each violin's distribution.

            - ``cmedians``: A `~.collections.LineCollection` instance that
              marks the median values of each of the violin's distribution.

            - ``cquantiles``: A `~.collections.LineCollection` instance created
              to identify the quantiles values of each of the violin's
              distribution.

        See Also
        --------
        violinplot :
            Draw a violin plot from data instead of pre-computed statistics.
        """

        # Statistical quantities to be plotted on the violins
        means = []
        mins = []
        maxes = []
        medians = []
        quantiles = []

        qlens = []  # Number of quantiles in each dataset.

        artists = {}  # Collections to be returned

        N = len(vpstats)
        datashape_message = ("List of violinplot statistics and `{0}` "
                             "values must have the same length")

        # vert and orientation parameters are linked until vert's
        # deprecation period expires. If both are selected,
        # vert takes precedence.
        if vert is not None:
            _api.warn_deprecated(
                "3.11",
                name="vert: bool",
                alternative="orientation: {'vertical', 'horizontal'}",
                pending=True,
            )
            orientation = 'vertical' if vert else 'horizontal'
        _api.check_in_list(['horizontal', 'vertical'], orientation=orientation)

        # Validate positions
        if positions is None:
            positions = range(1, N + 1)
        elif len(positions) != N:
            raise ValueError(datashape_message.format("positions"))

        # Validate widths
        if np.isscalar(widths):
            widths = [widths] * N
        elif len(widths) != N:
            raise ValueError(datashape_message.format("widths"))

        # Validate side
        _api.check_in_list(["both", "low", "high"], side=side)

        # Calculate ranges for statistics lines (shape (2, N)).
        line_ends = [[-0.25 if side in ['both', 'low'] else 0],
                     [0.25 if side in ['both', 'high'] else 0]] \
                          * np.array(widths) + positions

        # Colors.
        if mpl.rcParams['_internal.classic_mode']:
            fillcolor = 'y'
            linecolor = 'r'
        else:
            fillcolor = linecolor = self._get_lines.get_next_color()

        # Check whether we are rendering vertically or horizontally
        if orientation == 'vertical':
            fill = self.fill_betweenx
            if side in ['low', 'high']:
                perp_lines = functools.partial(self.hlines, colors=linecolor,
                                                capstyle='projecting')
                par_lines = functools.partial(self.vlines, colors=linecolor,
                                                capstyle='projecting')
            else:
                perp_lines = functools.partial(self.hlines, colors=linecolor)
                par_lines = functools.partial(self.vlines, colors=linecolor)
        else:
            fill = self.fill_between
            if side in ['low', 'high']:
                perp_lines = functools.partial(self.vlines, colors=linecolor,
                                                capstyle='projecting')
                par_lines = functools.partial(self.hlines, colors=linecolor,
                                                capstyle='projecting')
            else:
                perp_lines = functools.partial(self.vlines, colors=linecolor)
                par_lines = functools.partial(self.hlines, colors=linecolor)

        # Render violins
        bodies = []
        for stats, pos, width in zip(vpstats, positions, widths):
            # The 0.5 factor reflects the fact that we plot from v-p to v+p.
            vals = np.array(stats['vals'])
            vals = 0.5 * width * vals / vals.max()
            bodies += [fill(stats['coords'],
                            -vals + pos if side in ['both', 'low'] else pos,
                            vals + pos if side in ['both', 'high'] else pos,
                            facecolor=fillcolor, alpha=0.3)]
            means.append(stats['mean'])
            mins.append(stats['min'])
            maxes.append(stats['max'])
            medians.append(stats['median'])
            q = stats.get('quantiles')  # a list of floats, or None
            if q is None:
                q = []
            quantiles.extend(q)
            qlens.append(len(q))
        artists['bodies'] = bodies

        if showmeans:  # Render means
            artists['cmeans'] = perp_lines(means, *line_ends)
        if showextrema:  # Render extrema
            artists['cmaxes'] = perp_lines(maxes, *line_ends)
            artists['cmins'] = perp_lines(mins, *line_ends)
            artists['cbars'] = par_lines(positions, mins, maxes)
        if showmedians:  # Render medians
            artists['cmedians'] = perp_lines(medians, *line_ends)
        if quantiles:  # Render quantiles: each width is repeated qlen times.
            artists['cquantiles'] = perp_lines(
                quantiles, *np.repeat(line_ends, qlens, axis=1))

        return artists

    # Methods that are entirely implemented in other modules.

    table = _make_axes_method(mtable.table)

    # args can be either Y or y1, y2, ... and all should be replaced
    stackplot = _preprocess_data()(_make_axes_method(mstack.stackplot))

    streamplot = _preprocess_data(
            replace_names=["x", "y", "u", "v", "start_points"])(
        _make_axes_method(mstream.streamplot))

    tricontour = _make_axes_method(mtri.tricontour)
    tricontourf = _make_axes_method(mtri.tricontourf)
    tripcolor = _make_axes_method(mtri.tripcolor)
    triplot = _make_axes_method(mtri.triplot)

    def _get_aspect_ratio(self):
        """
        Convenience method to calculate the aspect ratio of the Axes in
        the display coordinate system.
        """
        figure_size = self.get_figure().get_size_inches()
        ll, ur = self.get_position() * figure_size
        width, height = ur - ll
        return height / (width * self.get_data_ratio())

# === NexusCore/myenv\Lib\site-packages\pip\_vendor\idna\uts46data.py ===
# This file is automatically generated by tools/idna-data
# vim: set fileencoding=utf-8 :

from typing import List, Tuple, Union

"""IDNA Mapping Table from UTS46."""


__version__ = "15.1.0"


def _seg_0() -> List[Union[Tuple[int, str], Tuple[int, str, str]]]:
    return [
        (0x0, "3"),
        (0x1, "3"),
        (0x2, "3"),
        (0x3, "3"),
        (0x4, "3"),
        (0x5, "3"),
        (0x6, "3"),
        (0x7, "3"),
        (0x8, "3"),
        (0x9, "3"),
        (0xA, "3"),
        (0xB, "3"),
        (0xC, "3"),
        (0xD, "3"),
        (0xE, "3"),
        (0xF, "3"),
        (0x10, "3"),
        (0x11, "3"),
        (0x12, "3"),
        (0x13, "3"),
        (0x14, "3"),
        (0x15, "3"),
        (0x16, "3"),
        (0x17, "3"),
        (0x18, "3"),
        (0x19, "3"),
        (0x1A, "3"),
        (0x1B, "3"),
        (0x1C, "3"),
        (0x1D, "3"),
        (0x1E, "3"),
        (0x1F, "3"),
        (0x20, "3"),
        (0x21, "3"),
        (0x22, "3"),
        (0x23, "3"),
        (0x24, "3"),
        (0x25, "3"),
        (0x26, "3"),
        (0x27, "3"),
        (0x28, "3"),
        (0x29, "3"),
        (0x2A, "3"),
        (0x2B, "3"),
        (0x2C, "3"),
        (0x2D, "V"),
        (0x2E, "V"),
        (0x2F, "3"),
        (0x30, "V"),
        (0x31, "V"),
        (0x32, "V"),
        (0x33, "V"),
        (0x34, "V"),
        (0x35, "V"),
        (0x36, "V"),
        (0x37, "V"),
        (0x38, "V"),
        (0x39, "V"),
        (0x3A, "3"),
        (0x3B, "3"),
        (0x3C, "3"),
        (0x3D, "3"),
        (0x3E, "3"),
        (0x3F, "3"),
        (0x40, "3"),
        (0x41, "M", "a"),
        (0x42, "M", "b"),
        (0x43, "M", "c"),
        (0x44, "M", "d"),
        (0x45, "M", "e"),
        (0x46, "M", "f"),
        (0x47, "M", "g"),
        (0x48, "M", "h"),
        (0x49, "M", "i"),
        (0x4A, "M", "j"),
        (0x4B, "M", "k"),
        (0x4C, "M", "l"),
        (0x4D, "M", "m"),
        (0x4E, "M", "n"),
        (0x4F, "M", "o"),
        (0x50, "M", "p"),
        (0x51, "M", "q"),
        (0x52, "M", "r"),
        (0x53, "M", "s"),
        (0x54, "M", "t"),
        (0x55, "M", "u"),
        (0x56, "M", "v"),
        (0x57, "M", "w"),
        (0x58, "M", "x"),
        (0x59, "M", "y"),
        (0x5A, "M", "z"),
        (0x5B, "3"),
        (0x5C, "3"),
        (0x5D, "3"),
        (0x5E, "3"),
        (0x5F, "3"),
        (0x60, "3"),
        (0x61, "V"),
        (0x62, "V"),
        (0x63, "V"),
    ]


def _seg_1() -> List[Union[Tuple[int, str], Tuple[int, str, str]]]:
    return [
        (0x64, "V"),
        (0x65, "V"),
        (0x66, "V"),
        (0x67, "V"),
        (0x68, "V"),
        (0x69, "V"),
        (0x6A, "V"),
        (0x6B, "V"),
        (0x6C, "V"),
        (0x6D, "V"),
        (0x6E, "V"),
        (0x6F, "V"),
        (0x70, "V"),
        (0x71, "V"),
        (0x72, "V"),
        (0x73, "V"),
        (0x74, "V"),
        (0x75, "V"),
        (0x76, "V"),
        (0x77, "V"),
        (0x78, "V"),
        (0x79, "V"),
        (0x7A, "V"),
        (0x7B, "3"),
        (0x7C, "3"),
        (0x7D, "3"),
        (0x7E, "3"),
        (0x7F, "3"),
        (0x80, "X"),
        (0x81, "X"),
        (0x82, "X"),
        (0x83, "X"),
        (0x84, "X"),
        (0x85, "X"),
        (0x86, "X"),
        (0x87, "X"),
        (0x88, "X"),
        (0x89, "X"),
        (0x8A, "X"),
        (0x8B, "X"),
        (0x8C, "X"),
        (0x8D, "X"),
        (0x8E, "X"),
        (0x8F, "X"),
        (0x90, "X"),
        (0x91, "X"),
        (0x92, "X"),
        (0x93, "X"),
        (0x94, "X"),
        (0x95, "X"),
        (0x96, "X"),
        (0x97, "X"),
        (0x98, "X"),
        (0x99, "X"),
        (0x9A, "X"),
        (0x9B, "X"),
        (0x9C, "X"),
        (0x9D, "X"),
        (0x9E, "X"),
        (0x9F, "X"),
        (0xA0, "3", " "),
        (0xA1, "V"),
        (0xA2, "V"),
        (0xA3, "V"),
        (0xA4, "V"),
        (0xA5, "V"),
        (0xA6, "V"),
        (0xA7, "V"),
        (0xA8, "3", " ̈"),
        (0xA9, "V"),
        (0xAA, "M", "a"),
        (0xAB, "V"),
        (0xAC, "V"),
        (0xAD, "I"),
        (0xAE, "V"),
        (0xAF, "3", " ̄"),
        (0xB0, "V"),
        (0xB1, "V"),
        (0xB2, "M", "2"),
        (0xB3, "M", "3"),
        (0xB4, "3", " ́"),
        (0xB5, "M", "μ"),
        (0xB6, "V"),
        (0xB7, "V"),
        (0xB8, "3", " ̧"),
        (0xB9, "M", "1"),
        (0xBA, "M", "o"),
        (0xBB, "V"),
        (0xBC, "M", "1⁄4"),
        (0xBD, "M", "1⁄2"),
        (0xBE, "M", "3⁄4"),
        (0xBF, "V"),
        (0xC0, "M", "à"),
        (0xC1, "M", "á"),
        (0xC2, "M", "â"),
        (0xC3, "M", "ã"),
        (0xC4, "M", "ä"),
        (0xC5, "M", "å"),
        (0xC6, "M", "æ"),
        (0xC7, "M", "ç"),
    ]


def _seg_2() -> List[Union[Tuple[int, str], Tuple[int, str, str]]]:
    return [
        (0xC8, "M", "è"),
        (0xC9, "M", "é"),
        (0xCA, "M", "ê"),
        (0xCB, "M", "ë"),
        (0xCC, "M", "ì"),
        (0xCD, "M", "í"),
        (0xCE, "M", "î"),
        (0xCF, "M", "ï"),
        (0xD0, "M", "ð"),
        (0xD1, "M", "ñ"),
        (0xD2, "M", "ò"),
        (0xD3, "M", "ó"),
        (0xD4, "M", "ô"),
        (0xD5, "M", "õ"),
        (0xD6, "M", "ö"),
        (0xD7, "V"),
        (0xD8, "M", "ø"),
        (0xD9, "M", "ù"),
        (0xDA, "M", "ú"),
        (0xDB, "M", "û"),
        (0xDC, "M", "ü"),
        (0xDD, "M", "ý"),
        (0xDE, "M", "þ"),
        (0xDF, "D", "ss"),
        (0xE0, "V"),
        (0xE1, "V"),
        (0xE2, "V"),
        (0xE3, "V"),
        (0xE4, "V"),
        (0xE5, "V"),
        (0xE6, "V"),
        (0xE7, "V"),
        (0xE8, "V"),
        (0xE9, "V"),
        (0xEA, "V"),
        (0xEB, "V"),
        (0xEC, "V"),
        (0xED, "V"),
        (0xEE, "V"),
        (0xEF, "V"),
        (0xF0, "V"),
        (0xF1, "V"),
        (0xF2, "V"),
        (0xF3, "V"),
        (0xF4, "V"),
        (0xF5, "V"),
        (0xF6, "V"),
        (0xF7, "V"),
        (0xF8, "V"),
        (0xF9, "V"),
        (0xFA, "V"),
        (0xFB, "V"),
        (0xFC, "V"),
        (0xFD, "V"),
        (0xFE, "V"),
        (0xFF, "V"),
        (0x100, "M", "ā"),
        (0x101, "V"),
        (0x102, "M", "ă"),
        (0x103, "V"),
        (0x104, "M", "ą"),
        (0x105, "V"),
        (0x106, "M", "ć"),
        (0x107, "V"),
        (0x108, "M", "ĉ"),
        (0x109, "V"),
        (0x10A, "M", "ċ"),
        (0x10B, "V"),
        (0x10C, "M", "č"),
        (0x10D, "V"),
        (0x10E, "M", "ď"),
        (0x10F, "V"),
        (0x110, "M", "đ"),
        (0x111, "V"),
        (0x112, "M", "ē"),
        (0x113, "V"),
        (0x114, "M", "ĕ"),
        (0x115, "V"),
        (0x116, "M", "ė"),
        (0x117, "V"),
        (0x118, "M", "ę"),
        (0x119, "V"),
        (0x11A, "M", "ě"),
        (0x11B, "V"),
        (0x11C, "M", "ĝ"),
        (0x11D, "V"),
        (0x11E, "M", "ğ"),
        (0x11F, "V"),
        (0x120, "M", "ġ"),
        (0x121, "V"),
        (0x122, "M", "ģ"),
        (0x123, "V"),
        (0x124, "M", "ĥ"),
        (0x125, "V"),
        (0x126, "M", "ħ"),
        (0x127, "V"),
        (0x128, "M", "ĩ"),
        (0x129, "V"),
        (0x12A, "M", "ī"),
        (0x12B, "V"),
    ]


def _seg_3() -> List[Union[Tuple[int, str], Tuple[int, str, str]]]:
    return [
        (0x12C, "M", "ĭ"),
        (0x12D, "V"),
        (0x12E, "M", "į"),
        (0x12F, "V"),
        (0x130, "M", "i̇"),
        (0x131, "V"),
        (0x132, "M", "ij"),
        (0x134, "M", "ĵ"),
        (0x135, "V"),
        (0x136, "M", "ķ"),
        (0x137, "V"),
        (0x139, "M", "ĺ"),
        (0x13A, "V"),
        (0x13B, "M", "ļ"),
        (0x13C, "V"),
        (0x13D, "M", "ľ"),
        (0x13E, "V"),
        (0x13F, "M", "l·"),
        (0x141, "M", "ł"),
        (0x142, "V"),
        (0x143, "M", "ń"),
        (0x144, "V"),
        (0x145, "M", "ņ"),
        (0x146, "V"),
        (0x147, "M", "ň"),
        (0x148, "V"),
        (0x149, "M", "ʼn"),
        (0x14A, "M", "ŋ"),
        (0x14B, "V"),
        (0x14C, "M", "ō"),
        (0x14D, "V"),
        (0x14E, "M", "ŏ"),
        (0x14F, "V"),
        (0x150, "M", "ő"),
        (0x151, "V"),
        (0x152, "M", "œ"),
        (0x153, "V"),
        (0x154, "M", "ŕ"),
        (0x155, "V"),
        (0x156, "M", "ŗ"),
        (0x157, "V"),
        (0x158, "M", "ř"),
        (0x159, "V"),
        (0x15A, "M", "ś"),
        (0x15B, "V"),
        (0x15C, "M", "ŝ"),
        (0x15D, "V"),
        (0x15E, "M", "ş"),
        (0x15F, "V"),
        (0x160, "M", "š"),
        (0x161, "V"),
        (0x162, "M", "ţ"),
        (0x163, "V"),
        (0x164, "M", "ť"),
        (0x165, "V"),
        (0x166, "M", "ŧ"),
        (0x167, "V"),
        (0x168, "M", "ũ"),
        (0x169, "V"),
        (0x16A, "M", "ū"),
        (0x16B, "V"),
        (0x16C, "M", "ŭ"),
        (0x16D, "V"),
        (0x16E, "M", "ů"),
        (0x16F, "V"),
        (0x170, "M", "ű"),
        (0x171, "V"),
        (0x172, "M", "ų"),
        (0x173, "V"),
        (0x174, "M", "ŵ"),
        (0x175, "V"),
        (0x176, "M", "ŷ"),
        (0x177, "V"),
        (0x178, "M", "ÿ"),
        (0x179, "M", "ź"),
        (0x17A, "V"),
        (0x17B, "M", "ż"),
        (0x17C, "V"),
        (0x17D, "M", "ž"),
        (0x17E, "V"),
        (0x17F, "M", "s"),
        (0x180, "V"),
        (0x181, "M", "ɓ"),
        (0x182, "M", "ƃ"),
        (0x183, "V"),
        (0x184, "M", "ƅ"),
        (0x185, "V"),
        (0x186, "M", "ɔ"),
        (0x187, "M", "ƈ"),
        (0x188, "V"),
        (0x189, "M", "ɖ"),
        (0x18A, "M", "ɗ"),
        (0x18B, "M", "ƌ"),
        (0x18C, "V"),
        (0x18E, "M", "ǝ"),
        (0x18F, "M", "ə"),
        (0x190, "M", "ɛ"),
        (0x191, "M", "ƒ"),
        (0x192, "V"),
        (0x193, "M", "ɠ"),
    ]


def _seg_4() -> List[Union[Tuple[int, str], Tuple[int, str, str]]]:
    return [
        (0x194, "M", "ɣ"),
        (0x195, "V"),
        (0x196, "M", "ɩ"),
        (0x197, "M", "ɨ"),
        (0x198, "M", "ƙ"),
        (0x199, "V"),
        (0x19C, "M", "ɯ"),
        (0x19D, "M", "ɲ"),
        (0x19E, "V"),
        (0x19F, "M", "ɵ"),
        (0x1A0, "M", "ơ"),
        (0x1A1, "V"),
        (0x1A2, "M", "ƣ"),
        (0x1A3, "V"),
        (0x1A4, "M", "ƥ"),
        (0x1A5, "V"),
        (0x1A6, "M", "ʀ"),
        (0x1A7, "M", "ƨ"),
        (0x1A8, "V"),
        (0x1A9, "M", "ʃ"),
        (0x1AA, "V"),
        (0x1AC, "M", "ƭ"),
        (0x1AD, "V"),
        (0x1AE, "M", "ʈ"),
        (0x1AF, "M", "ư"),
        (0x1B0, "V"),
        (0x1B1, "M", "ʊ"),
        (0x1B2, "M", "ʋ"),
        (0x1B3, "M", "ƴ"),
        (0x1B4, "V"),
        (0x1B5, "M", "ƶ"),
        (0x1B6, "V"),
        (0x1B7, "M", "ʒ"),
        (0x1B8, "M", "ƹ"),
        (0x1B9, "V"),
        (0x1BC, "M", "ƽ"),
        (0x1BD, "V"),
        (0x1C4, "M", "dž"),
        (0x1C7, "M", "lj"),
        (0x1CA, "M", "nj"),
        (0x1CD, "M", "ǎ"),
        (0x1CE, "V"),
        (0x1CF, "M", "ǐ"),
        (0x1D0, "V"),
        (0x1D1, "M", "ǒ"),
        (0x1D2, "V"),
        (0x1D3, "M", "ǔ"),
        (0x1D4, "V"),
        (0x1D5, "M", "ǖ"),
        (0x1D6, "V"),
        (0x1D7, "M", "ǘ"),
        (0x1D8, "V"),
        (0x1D9, "M", "ǚ"),
        (0x1DA, "V"),
        (0x1DB, "M", "ǜ"),
        (0x1DC, "V"),
        (0x1DE, "M", "ǟ"),
        (0x1DF, "V"),
        (0x1E0, "M", "ǡ"),
        (0x1E1, "V"),
        (0x1E2, "M", "ǣ"),
        (0x1E3, "V"),
        (0x1E4, "M", "ǥ"),
        (0x1E5, "V"),
        (0x1E6, "M", "ǧ"),
        (0x1E7, "V"),
        (0x1E8, "M", "ǩ"),
        (0x1E9, "V"),
        (0x1EA, "M", "ǫ"),
        (0x1EB, "V"),
        (0x1EC, "M", "ǭ"),
        (0x1ED, "V"),
        (0x1EE, "M", "ǯ"),
        (0x1EF, "V"),
        (0x1F1, "M", "dz"),
        (0x1F4, "M", "ǵ"),
        (0x1F5, "V"),
        (0x1F6, "M", "ƕ"),
        (0x1F7, "M", "ƿ"),
        (0x1F8, "M", "ǹ"),
        (0x1F9, "V"),
        (0x1FA, "M", "ǻ"),
        (0x1FB, "V"),
        (0x1FC, "M", "ǽ"),
        (0x1FD, "V"),
        (0x1FE, "M", "ǿ"),
        (0x1FF, "V"),
        (0x200, "M", "ȁ"),
        (0x201, "V"),
        (0x202, "M", "ȃ"),
        (0x203, "V"),
        (0x204, "M", "ȅ"),
        (0x205, "V"),
        (0x206, "M", "ȇ"),
        (0x207, "V"),
        (0x208, "M", "ȉ"),
        (0x209, "V"),
        (0x20A, "M", "ȋ"),
        (0x20B, "V"),
        (0x20C, "M", "ȍ"),
    ]


def _seg_5() -> List[Union[Tuple[int, str], Tuple[int, str, str]]]:
    return [
        (0x20D, "V"),
        (0x20E, "M", "ȏ"),
        (0x20F, "V"),
        (0x210, "M", "ȑ"),
        (0x211, "V"),
        (0x212, "M", "ȓ"),
        (0x213, "V"),
        (0x214, "M", "ȕ"),
        (0x215, "V"),
        (0x216, "M", "ȗ"),
        (0x217, "V"),
        (0x218, "M", "ș"),
        (0x219, "V"),
        (0x21A, "M", "ț"),
        (0x21B, "V"),
        (0x21C, "M", "ȝ"),
        (0x21D, "V"),
        (0x21E, "M", "ȟ"),
        (0x21F, "V"),
        (0x220, "M", "ƞ"),
        (0x221, "V"),
        (0x222, "M", "ȣ"),
        (0x223, "V"),
        (0x224, "M", "ȥ"),
        (0x225, "V"),
        (0x226, "M", "ȧ"),
        (0x227, "V"),
        (0x228, "M", "ȩ"),
        (0x229, "V"),
        (0x22A, "M", "ȫ"),
        (0x22B, "V"),
        (0x22C, "M", "ȭ"),
        (0x22D, "V"),
        (0x22E, "M", "ȯ"),
        (0x22F, "V"),
        (0x230, "M", "ȱ"),
        (0x231, "V"),
        (0x232, "M", "ȳ"),
        (0x233, "V"),
        (0x23A, "M", "ⱥ"),
        (0x23B, "M", "ȼ"),
        (0x23C, "V"),
        (0x23D, "M", "ƚ"),
        (0x23E, "M", "ⱦ"),
        (0x23F, "V"),
        (0x241, "M", "ɂ"),
        (0x242, "V"),
        (0x243, "M", "ƀ"),
        (0x244, "M", "ʉ"),
        (0x245, "M", "ʌ"),
        (0x246, "M", "ɇ"),
        (0x247, "V"),
        (0x248, "M", "ɉ"),
        (0x249, "V"),
        (0x24A, "M", "ɋ"),
        (0x24B, "V"),
        (0x24C, "M", "ɍ"),
        (0x24D, "V"),
        (0x24E, "M", "ɏ"),
        (0x24F, "V"),
        (0x2B0, "M", "h"),
        (0x2B1, "M", "ɦ"),
        (0x2B2, "M", "j"),
        (0x2B3, "M", "r"),
        (0x2B4, "M", "ɹ"),
        (0x2B5, "M", "ɻ"),
        (0x2B6, "M", "ʁ"),
        (0x2B7, "M", "w"),
        (0x2B8, "M", "y"),
        (0x2B9, "V"),
        (0x2D8, "3", " ̆"),
        (0x2D9, "3", " ̇"),
        (0x2DA, "3", " ̊"),
        (0x2DB, "3", " ̨"),
        (0x2DC, "3", " ̃"),
        (0x2DD, "3", " ̋"),
        (0x2DE, "V"),
        (0x2E0, "M", "ɣ"),
        (0x2E1, "M", "l"),
        (0x2E2, "M", "s"),
        (0x2E3, "M", "x"),
        (0x2E4, "M", "ʕ"),
        (0x2E5, "V"),
        (0x340, "M", "̀"),
        (0x341, "M", "́"),
        (0x342, "V"),
        (0x343, "M", "̓"),
        (0x344, "M", "̈́"),
        (0x345, "M", "ι"),
        (0x346, "V"),
        (0x34F, "I"),
        (0x350, "V"),
        (0x370, "M", "ͱ"),
        (0x371, "V"),
        (0x372, "M", "ͳ"),
        (0x373, "V"),
        (0x374, "M", "ʹ"),
        (0x375, "V"),
        (0x376, "M", "ͷ"),
        (0x377, "V"),
    ]


def _seg_6() -> List[Union[Tuple[int, str], Tuple[int, str, str]]]:
    return [
        (0x378, "X"),
        (0x37A, "3", " ι"),
        (0x37B, "V"),
        (0x37E, "3", ";"),
        (0x37F, "M", "ϳ"),
        (0x380, "X"),
        (0x384, "3", " ́"),
        (0x385, "3", " ̈́"),
        (0x386, "M", "ά"),
        (0x387, "M", "·"),
        (0x388, "M", "έ"),
        (0x389, "M", "ή"),
        (0x38A, "M", "ί"),
        (0x38B, "X"),
        (0x38C, "M", "ό"),
        (0x38D, "X"),
        (0x38E, "M", "ύ"),
        (0x38F, "M", "ώ"),
        (0x390, "V"),
        (0x391, "M", "α"),
        (0x392, "M", "β"),
        (0x393, "M", "γ"),
        (0x394, "M", "δ"),
        (0x395, "M", "ε"),
        (0x396, "M", "ζ"),
        (0x397, "M", "η"),
        (0x398, "M", "θ"),
        (0x399, "M", "ι"),
        (0x39A, "M", "κ"),
        (0x39B, "M", "λ"),
        (0x39C, "M", "μ"),
        (0x39D, "M", "ν"),
        (0x39E, "M", "ξ"),
        (0x39F, "M", "ο"),
        (0x3A0, "M", "π"),
        (0x3A1, "M", "ρ"),
        (0x3A2, "X"),
        (0x3A3, "M", "σ"),
        (0x3A4, "M", "τ"),
        (0x3A5, "M", "υ"),
        (0x3A6, "M", "φ"),
        (0x3A7, "M", "χ"),
        (0x3A8, "M", "ψ"),
        (0x3A9, "M", "ω"),
        (0x3AA, "M", "ϊ"),
        (0x3AB, "M", "ϋ"),
        (0x3AC, "V"),
        (0x3C2, "D", "σ"),
        (0x3C3, "V"),
        (0x3CF, "M", "ϗ"),
        (0x3D0, "M", "β"),
        (0x3D1, "M", "θ"),
        (0x3D2, "M", "υ"),
        (0x3D3, "M", "ύ"),
        (0x3D4, "M", "ϋ"),
        (0x3D5, "M", "φ"),
        (0x3D6, "M", "π"),
        (0x3D7, "V"),
        (0x3D8, "M", "ϙ"),
        (0x3D9, "V"),
        (0x3DA, "M", "ϛ"),
        (0x3DB, "V"),
        (0x3DC, "M", "ϝ"),
        (0x3DD, "V"),
        (0x3DE, "M", "ϟ"),
        (0x3DF, "V"),
        (0x3E0, "M", "ϡ"),
        (0x3E1, "V"),
        (0x3E2, "M", "ϣ"),
        (0x3E3, "V"),
        (0x3E4, "M", "ϥ"),
        (0x3E5, "V"),
        (0x3E6, "M", "ϧ"),
        (0x3E7, "V"),
        (0x3E8, "M", "ϩ"),
        (0x3E9, "V"),
        (0x3EA, "M", "ϫ"),
        (0x3EB, "V"),
        (0x3EC, "M", "ϭ"),
        (0x3ED, "V"),
        (0x3EE, "M", "ϯ"),
        (0x3EF, "V"),
        (0x3F0, "M", "κ"),
        (0x3F1, "M", "ρ"),
        (0x3F2, "M", "σ"),
        (0x3F3, "V"),
        (0x3F4, "M", "θ"),
        (0x3F5, "M", "ε"),
        (0x3F6, "V"),
        (0x3F7, "M", "ϸ"),
        (0x3F8, "V"),
        (0x3F9, "M", "σ"),
        (0x3FA, "M", "ϻ"),
        (0x3FB, "V"),
        (0x3FD, "M", "ͻ"),
        (0x3FE, "M", "ͼ"),
        (0x3FF, "M", "ͽ"),
        (0x400, "M", "ѐ"),
        (0x401, "M", "ё"),
        (0x402, "M", "ђ"),
    ]


def _seg_7() -> List[Union[Tuple[int, str], Tuple[int, str, str]]]:
    return [
        (0x403, "M", "ѓ"),
        (0x404, "M", "є"),
        (0x405, "M", "ѕ"),
        (0x406, "M", "і"),
        (0x407, "M", "ї"),
        (0x408, "M", "ј"),
        (0x409, "M", "љ"),
        (0x40A, "M", "њ"),
        (0x40B, "M", "ћ"),
        (0x40C, "M", "ќ"),
        (0x40D, "M", "ѝ"),
        (0x40E, "M", "ў"),
        (0x40F, "M", "џ"),
        (0x410, "M", "а"),
        (0x411, "M", "б"),
        (0x412, "M", "в"),
        (0x413, "M", "г"),
        (0x414, "M", "д"),
        (0x415, "M", "е"),
        (0x416, "M", "ж"),
        (0x417, "M", "з"),
        (0x418, "M", "и"),
        (0x419, "M", "й"),
        (0x41A, "M", "к"),
        (0x41B, "M", "л"),
        (0x41C, "M", "м"),
        (0x41D, "M", "н"),
        (0x41E, "M", "о"),
        (0x41F, "M", "п"),
        (0x420, "M", "р"),
        (0x421, "M", "с"),
        (0x422, "M", "т"),
        (0x423, "M", "у"),
        (0x424, "M", "ф"),
        (0x425, "M", "х"),
        (0x426, "M", "ц"),
        (0x427, "M", "ч"),
        (0x428, "M", "ш"),
        (0x429, "M", "щ"),
        (0x42A, "M", "ъ"),
        (0x42B, "M", "ы"),
        (0x42C, "M", "ь"),
        (0x42D, "M", "э"),
        (0x42E, "M", "ю"),
        (0x42F, "M", "я"),
        (0x430, "V"),
        (0x460, "M", "ѡ"),
        (0x461, "V"),
        (0x462, "M", "ѣ"),
        (0x463, "V"),
        (0x464, "M", "ѥ"),
        (0x465, "V"),
        (0x466, "M", "ѧ"),
        (0x467, "V"),
        (0x468, "M", "ѩ"),
        (0x469, "V"),
        (0x46A, "M", "ѫ"),
        (0x46B, "V"),
        (0x46C, "M", "ѭ"),
        (0x46D, "V"),
        (0x46E, "M", "ѯ"),
        (0x46F, "V"),
        (0x470, "M", "ѱ"),
        (0x471, "V"),
        (0x472, "M", "ѳ"),
        (0x473, "V"),
        (0x474, "M", "ѵ"),
        (0x475, "V"),
        (0x476, "M", "ѷ"),
        (0x477, "V"),
        (0x478, "M", "ѹ"),
        (0x479, "V"),
        (0x47A, "M", "ѻ"),
        (0x47B, "V"),
        (0x47C, "M", "ѽ"),
        (0x47D, "V"),
        (0x47E, "M", "ѿ"),
        (0x47F, "V"),
        (0x480, "M", "ҁ"),
        (0x481, "V"),
        (0x48A, "M", "ҋ"),
        (0x48B, "V"),
        (0x48C, "M", "ҍ"),
        (0x48D, "V"),
        (0x48E, "M", "ҏ"),
        (0x48F, "V"),
        (0x490, "M", "ґ"),
        (0x491, "V"),
        (0x492, "M", "ғ"),
        (0x493, "V"),
        (0x494, "M", "ҕ"),
        (0x495, "V"),
        (0x496, "M", "җ"),
        (0x497, "V"),
        (0x498, "M", "ҙ"),
        (0x499, "V"),
        (0x49A, "M", "қ"),
        (0x49B, "V"),
        (0x49C, "M", "ҝ"),
        (0x49D, "V"),
    ]


def _seg_8() -> List[Union[Tuple[int, str], Tuple[int, str, str]]]:
    return [
        (0x49E, "M", "ҟ"),
        (0x49F, "V"),
        (0x4A0, "M", "ҡ"),
        (0x4A1, "V"),
        (0x4A2, "M", "ң"),
        (0x4A3, "V"),
        (0x4A4, "M", "ҥ"),
        (0x4A5, "V"),
        (0x4A6, "M", "ҧ"),
        (0x4A7, "V"),
        (0x4A8, "M", "ҩ"),
        (0x4A9, "V"),
        (0x4AA, "M", "ҫ"),
        (0x4AB, "V"),
        (0x4AC, "M", "ҭ"),
        (0x4AD, "V"),
        (0x4AE, "M", "ү"),
        (0x4AF, "V"),
        (0x4B0, "M", "ұ"),
        (0x4B1, "V"),
        (0x4B2, "M", "ҳ"),
        (0x4B3, "V"),
        (0x4B4, "M", "ҵ"),
        (0x4B5, "V"),
        (0x4B6, "M", "ҷ"),
        (0x4B7, "V"),
        (0x4B8, "M", "ҹ"),
        (0x4B9, "V"),
        (0x4BA, "M", "һ"),
        (0x4BB, "V"),
        (0x4BC, "M", "ҽ"),
        (0x4BD, "V"),
        (0x4BE, "M", "ҿ"),
        (0x4BF, "V"),
        (0x4C0, "X"),
        (0x4C1, "M", "ӂ"),
        (0x4C2, "V"),
        (0x4C3, "M", "ӄ"),
        (0x4C4, "V"),
        (0x4C5, "M", "ӆ"),
        (0x4C6, "V"),
        (0x4C7, "M", "ӈ"),
        (0x4C8, "V"),
        (0x4C9, "M", "ӊ"),
        (0x4CA, "V"),
        (0x4CB, "M", "ӌ"),
        (0x4CC, "V"),
        (0x4CD, "M", "ӎ"),
        (0x4CE, "V"),
        (0x4D0, "M", "ӑ"),
        (0x4D1, "V"),
        (0x4D2, "M", "ӓ"),
        (0x4D3, "V"),
        (0x4D4, "M", "ӕ"),
        (0x4D5, "V"),
        (0x4D6, "M", "ӗ"),
        (0x4D7, "V"),
        (0x4D8, "M", "ә"),
        (0x4D9, "V"),
        (0x4DA, "M", "ӛ"),
        (0x4DB, "V"),
        (0x4DC, "M", "ӝ"),
        (0x4DD, "V"),
        (0x4DE, "M", "ӟ"),
        (0x4DF, "V"),
        (0x4E0, "M", "ӡ"),
        (0x4E1, "V"),
        (0x4E2, "M", "ӣ"),
        (0x4E3, "V"),
        (0x4E4, "M", "ӥ"),
        (0x4E5, "V"),
        (0x4E6, "M", "ӧ"),
        (0x4E7, "V"),
        (0x4E8, "M", "ө"),
        (0x4E9, "V"),
        (0x4EA, "M", "ӫ"),
        (0x4EB, "V"),
        (0x4EC, "M", "ӭ"),
        (0x4ED, "V"),
        (0x4EE, "M", "ӯ"),
        (0x4EF, "V"),
        (0x4F0, "M", "ӱ"),
        (0x4F1, "V"),
        (0x4F2, "M", "ӳ"),
        (0x4F3, "V"),
        (0x4F4, "M", "ӵ"),
        (0x4F5, "V"),
        (0x4F6, "M", "ӷ"),
        (0x4F7, "V"),
        (0x4F8, "M", "ӹ"),
        (0x4F9, "V"),
        (0x4FA, "M", "ӻ"),
        (0x4FB, "V"),
        (0x4FC, "M", "ӽ"),
        (0x4FD, "V"),
        (0x4FE, "M", "ӿ"),
        (0x4FF, "V"),
        (0x500, "M", "ԁ"),
        (0x501, "V"),
        (0x502, "M", "ԃ"),
    ]


def _seg_9() -> List[Union[Tuple[int, str], Tuple[int, str, str]]]:
    return [
        (0x503, "V"),
        (0x504, "M", "ԅ"),
        (0x505, "V"),
        (0x506, "M", "ԇ"),
        (0x507, "V"),
        (0x508, "M", "ԉ"),
        (0x509, "V"),
        (0x50A, "M", "ԋ"),
        (0x50B, "V"),
        (0x50C, "M", "ԍ"),
        (0x50D, "V"),
        (0x50E, "M", "ԏ"),
        (0x50F, "V"),
        (0x510, "M", "ԑ"),
        (0x511, "V"),
        (0x512, "M", "ԓ"),
        (0x513, "V"),
        (0x514, "M", "ԕ"),
        (0x515, "V"),
        (0x516, "M", "ԗ"),
        (0x517, "V"),
        (0x518, "M", "ԙ"),
        (0x519, "V"),
        (0x51A, "M", "ԛ"),
        (0x51B, "V"),
        (0x51C, "M", "ԝ"),
        (0x51D, "V"),
        (0x51E, "M", "ԟ"),
        (0x51F, "V"),
        (0x520, "M", "ԡ"),
        (0x521, "V"),
        (0x522, "M", "ԣ"),
        (0x523, "V"),
        (0x524, "M", "ԥ"),
        (0x525, "V"),
        (0x526, "M", "ԧ"),
        (0x527, "V"),
        (0x528, "M", "ԩ"),
        (0x529, "V"),
        (0x52A, "M", "ԫ"),
        (0x52B, "V"),
        (0x52C, "M", "ԭ"),
        (0x52D, "V"),
        (0x52E, "M", "ԯ"),
        (0x52F, "V"),
        (0x530, "X"),
        (0x531, "M", "ա"),
        (0x532, "M", "բ"),
        (0x533, "M", "գ"),
        (0x534, "M", "դ"),
        (0x535, "M", "ե"),
        (0x536, "M", "զ"),
        (0x537, "M", "է"),
        (0x538, "M", "ը"),
        (0x539, "M", "թ"),
        (0x53A, "M", "ժ"),
        (0x53B, "M", "ի"),
        (0x53C, "M", "լ"),
        (0x53D, "M", "խ"),
        (0x53E, "M", "ծ"),
        (0x53F, "M", "կ"),
        (0x540, "M", "հ"),
        (0x541, "M", "ձ"),
        (0x542, "M", "ղ"),
        (0x543, "M", "ճ"),
        (0x544, "M", "մ"),
        (0x545, "M", "յ"),
        (0x546, "M", "ն"),
        (0x547, "M", "շ"),
        (0x548, "M", "ո"),
        (0x549, "M", "չ"),
        (0x54A, "M", "պ"),
        (0x54B, "M", "ջ"),
        (0x54C, "M", "ռ"),
        (0x54D, "M", "ս"),
        (0x54E, "M", "վ"),
        (0x54F, "M", "տ"),
        (0x550, "M", "ր"),
        (0x551, "M", "ց"),
        (0x552, "M", "ւ"),
        (0x553, "M", "փ"),
        (0x554, "M", "ք"),
        (0x555, "M", "օ"),
        (0x556, "M", "ֆ"),
        (0x557, "X"),
        (0x559, "V"),
        (0x587, "M", "եւ"),
        (0x588, "V"),
        (0x58B, "X"),
        (0x58D, "V"),
        (0x590, "X"),
        (0x591, "V"),
        (0x5C8, "X"),
        (0x5D0, "V"),
        (0x5EB, "X"),
        (0x5EF, "V"),
        (0x5F5, "X"),
        (0x606, "V"),
        (0x61C, "X"),
        (0x61D, "V"),
    ]


def _seg_10() -> List[Union[Tuple[int, str], Tuple[int, str, str]]]:
    return [
        (0x675, "M", "اٴ"),
        (0x676, "M", "وٴ"),
        (0x677, "M", "ۇٴ"),
        (0x678, "M", "يٴ"),
        (0x679, "V"),
        (0x6DD, "X"),
        (0x6DE, "V"),
        (0x70E, "X"),
        (0x710, "V"),
        (0x74B, "X"),
        (0x74D, "V"),
        (0x7B2, "X"),
        (0x7C0, "V"),
        (0x7FB, "X"),
        (0x7FD, "V"),
        (0x82E, "X"),
        (0x830, "V"),
        (0x83F, "X"),
        (0x840, "V"),
        (0x85C, "X"),
        (0x85E, "V"),
        (0x85F, "X"),
        (0x860, "V"),
        (0x86B, "X"),
        (0x870, "V"),
        (0x88F, "X"),
        (0x898, "V"),
        (0x8E2, "X"),
        (0x8E3, "V"),
        (0x958, "M", "क़"),
        (0x959, "M", "ख़"),
        (0x95A, "M", "ग़"),
        (0x95B, "M", "ज़"),
        (0x95C, "M", "ड़"),
        (0x95D, "M", "ढ़"),
        (0x95E, "M", "फ़"),
        (0x95F, "M", "य़"),
        (0x960, "V"),
        (0x984, "X"),
        (0x985, "V"),
        (0x98D, "X"),
        (0x98F, "V"),
        (0x991, "X"),
        (0x993, "V"),
        (0x9A9, "X"),
        (0x9AA, "V"),
        (0x9B1, "X"),
        (0x9B2, "V"),
        (0x9B3, "X"),
        (0x9B6, "V"),
        (0x9BA, "X"),
        (0x9BC, "V"),
        (0x9C5, "X"),
        (0x9C7, "V"),
        (0x9C9, "X"),
        (0x9CB, "V"),
        (0x9CF, "X"),
        (0x9D7, "V"),
        (0x9D8, "X"),
        (0x9DC, "M", "ড়"),
        (0x9DD, "M", "ঢ়"),
        (0x9DE, "X"),
        (0x9DF, "M", "য়"),
        (0x9E0, "V"),
        (0x9E4, "X"),
        (0x9E6, "V"),
        (0x9FF, "X"),
        (0xA01, "V"),
        (0xA04, "X"),
        (0xA05, "V"),
        (0xA0B, "X"),
        (0xA0F, "V"),
        (0xA11, "X"),
        (0xA13, "V"),
        (0xA29, "X"),
        (0xA2A, "V"),
        (0xA31, "X"),
        (0xA32, "V"),
        (0xA33, "M", "ਲ਼"),
        (0xA34, "X"),
        (0xA35, "V"),
        (0xA36, "M", "ਸ਼"),
        (0xA37, "X"),
        (0xA38, "V"),
        (0xA3A, "X"),
        (0xA3C, "V"),
        (0xA3D, "X"),
        (0xA3E, "V"),
        (0xA43, "X"),
        (0xA47, "V"),
        (0xA49, "X"),
        (0xA4B, "V"),
        (0xA4E, "X"),
        (0xA51, "V"),
        (0xA52, "X"),
        (0xA59, "M", "ਖ਼"),
        (0xA5A, "M", "ਗ਼"),
        (0xA5B, "M", "ਜ਼"),
        (0xA5C, "V"),
        (0xA5D, "X"),
    ]


def _seg_11() -> List[Union[Tuple[int, str], Tuple[int, str, str]]]:
    return [
        (0xA5E, "M", "ਫ਼"),
        (0xA5F, "X"),
        (0xA66, "V"),
        (0xA77, "X"),
        (0xA81, "V"),
        (0xA84, "X"),
        (0xA85, "V"),
        (0xA8E, "X"),
        (0xA8F, "V"),
        (0xA92, "X"),
        (0xA93, "V"),
        (0xAA9, "X"),
        (0xAAA, "V"),
        (0xAB1, "X"),
        (0xAB2, "V"),
        (0xAB4, "X"),
        (0xAB5, "V"),
        (0xABA, "X"),
        (0xABC, "V"),
        (0xAC6, "X"),
        (0xAC7, "V"),
        (0xACA, "X"),
        (0xACB, "V"),
        (0xACE, "X"),
        (0xAD0, "V"),
        (0xAD1, "X"),
        (0xAE0, "V"),
        (0xAE4, "X"),
        (0xAE6, "V"),
        (0xAF2, "X"),
        (0xAF9, "V"),
        (0xB00, "X"),
        (0xB01, "V"),
        (0xB04, "X"),
        (0xB05, "V"),
        (0xB0D, "X"),
        (0xB0F, "V"),
        (0xB11, "X"),
        (0xB13, "V"),
        (0xB29, "X"),
        (0xB2A, "V"),
        (0xB31, "X"),
        (0xB32, "V"),
        (0xB34, "X"),
        (0xB35, "V"),
        (0xB3A, "X"),
        (0xB3C, "V"),
        (0xB45, "X"),
        (0xB47, "V"),
        (0xB49, "X"),
        (0xB4B, "V"),
        (0xB4E, "X"),
        (0xB55, "V"),
        (0xB58, "X"),
        (0xB5C, "M", "ଡ଼"),
        (0xB5D, "M", "ଢ଼"),
        (0xB5E, "X"),
        (0xB5F, "V"),
        (0xB64, "X"),
        (0xB66, "V"),
        (0xB78, "X"),
        (0xB82, "V"),
        (0xB84, "X"),
        (0xB85, "V"),
        (0xB8B, "X"),
        (0xB8E, "V"),
        (0xB91, "X"),
        (0xB92, "V"),
        (0xB96, "X"),
        (0xB99, "V"),
        (0xB9B, "X"),
        (0xB9C, "V"),
        (0xB9D, "X"),
        (0xB9E, "V"),
        (0xBA0, "X"),
        (0xBA3, "V"),
        (0xBA5, "X"),
        (0xBA8, "V"),
        (0xBAB, "X"),
        (0xBAE, "V"),
        (0xBBA, "X"),
        (0xBBE, "V"),
        (0xBC3, "X"),
        (0xBC6, "V"),
        (0xBC9, "X"),
        (0xBCA, "V"),
        (0xBCE, "X"),
        (0xBD0, "V"),
        (0xBD1, "X"),
        (0xBD7, "V"),
        (0xBD8, "X"),
        (0xBE6, "V"),
        (0xBFB, "X"),
        (0xC00, "V"),
        (0xC0D, "X"),
        (0xC0E, "V"),
        (0xC11, "X"),
        (0xC12, "V"),
        (0xC29, "X"),
        (0xC2A, "V"),
    ]


def _seg_12() -> List[Union[Tuple[int, str], Tuple[int, str, str]]]:
    return [
        (0xC3A, "X"),
        (0xC3C, "V"),
        (0xC45, "X"),
        (0xC46, "V"),
        (0xC49, "X"),
        (0xC4A, "V"),
        (0xC4E, "X"),
        (0xC55, "V"),
        (0xC57, "X"),
        (0xC58, "V"),
        (0xC5B, "X"),
        (0xC5D, "V"),
        (0xC5E, "X"),
        (0xC60, "V"),
        (0xC64, "X"),
        (0xC66, "V"),
        (0xC70, "X"),
        (0xC77, "V"),
        (0xC8D, "X"),
        (0xC8E, "V"),
        (0xC91, "X"),
        (0xC92, "V"),
        (0xCA9, "X"),
        (0xCAA, "V"),
        (0xCB4, "X"),
        (0xCB5, "V"),
        (0xCBA, "X"),
        (0xCBC, "V"),
        (0xCC5, "X"),
        (0xCC6, "V"),
        (0xCC9, "X"),
        (0xCCA, "V"),
        (0xCCE, "X"),
        (0xCD5, "V"),
        (0xCD7, "X"),
        (0xCDD, "V"),
        (0xCDF, "X"),
        (0xCE0, "V"),
        (0xCE4, "X"),
        (0xCE6, "V"),
        (0xCF0, "X"),
        (0xCF1, "V"),
        (0xCF4, "X"),
        (0xD00, "V"),
        (0xD0D, "X"),
        (0xD0E, "V"),
        (0xD11, "X"),
        (0xD12, "V"),
        (0xD45, "X"),
        (0xD46, "V"),
        (0xD49, "X"),
        (0xD4A, "V"),
        (0xD50, "X"),
        (0xD54, "V"),
        (0xD64, "X"),
        (0xD66, "V"),
        (0xD80, "X"),
        (0xD81, "V"),
        (0xD84, "X"),
        (0xD85, "V"),
        (0xD97, "X"),
        (0xD9A, "V"),
        (0xDB2, "X"),
        (0xDB3, "V"),
        (0xDBC, "X"),
        (0xDBD, "V"),
        (0xDBE, "X"),
        (0xDC0, "V"),
        (0xDC7, "X"),
        (0xDCA, "V"),
        (0xDCB, "X"),
        (0xDCF, "V"),
        (0xDD5, "X"),
        (0xDD6, "V"),
        (0xDD7, "X"),
        (0xDD8, "V"),
        (0xDE0, "X"),
        (0xDE6, "V"),
        (0xDF0, "X"),
        (0xDF2, "V"),
        (0xDF5, "X"),
        (0xE01, "V"),
        (0xE33, "M", "ํา"),
        (0xE34, "V"),
        (0xE3B, "X"),
        (0xE3F, "V"),
        (0xE5C, "X"),
        (0xE81, "V"),
        (0xE83, "X"),
        (0xE84, "V"),
        (0xE85, "X"),
        (0xE86, "V"),
        (0xE8B, "X"),
        (0xE8C, "V"),
        (0xEA4, "X"),
        (0xEA5, "V"),
        (0xEA6, "X"),
        (0xEA7, "V"),
        (0xEB3, "M", "ໍາ"),
        (0xEB4, "V"),
    ]


def _seg_13() -> List[Union[Tuple[int, str], Tuple[int, str, str]]]:
    return [
        (0xEBE, "X"),
        (0xEC0, "V"),
        (0xEC5, "X"),
        (0xEC6, "V"),
        (0xEC7, "X"),
        (0xEC8, "V"),
        (0xECF, "X"),
        (0xED0, "V"),
        (0xEDA, "X"),
        (0xEDC, "M", "ຫນ"),
        (0xEDD, "M", "ຫມ"),
        (0xEDE, "V"),
        (0xEE0, "X"),
        (0xF00, "V"),
        (0xF0C, "M", "་"),
        (0xF0D, "V"),
        (0xF43, "M", "གྷ"),
        (0xF44, "V"),
        (0xF48, "X"),
        (0xF49, "V"),
        (0xF4D, "M", "ཌྷ"),
        (0xF4E, "V"),
        (0xF52, "M", "དྷ"),
        (0xF53, "V"),
        (0xF57, "M", "བྷ"),
        (0xF58, "V"),
        (0xF5C, "M", "ཛྷ"),
        (0xF5D, "V"),
        (0xF69, "M", "ཀྵ"),
        (0xF6A, "V"),
        (0xF6D, "X"),
        (0xF71, "V"),
        (0xF73, "M", "ཱི"),
        (0xF74, "V"),
        (0xF75, "M", "ཱུ"),
        (0xF76, "M", "ྲྀ"),
        (0xF77, "M", "ྲཱྀ"),
        (0xF78, "M", "ླྀ"),
        (0xF79, "M", "ླཱྀ"),
        (0xF7A, "V"),
        (0xF81, "M", "ཱྀ"),
        (0xF82, "V"),
        (0xF93, "M", "ྒྷ"),
        (0xF94, "V"),
        (0xF98, "X"),
        (0xF99, "V"),
        (0xF9D, "M", "ྜྷ"),
        (0xF9E, "V"),
        (0xFA2, "M", "ྡྷ"),
        (0xFA3, "V"),
        (0xFA7, "M", "ྦྷ"),
        (0xFA8, "V"),
        (0xFAC, "M", "ྫྷ"),
        (0xFAD, "V"),
        (0xFB9, "M", "ྐྵ"),
        (0xFBA, "V"),
        (0xFBD, "X"),
        (0xFBE, "V"),
        (0xFCD, "X"),
        (0xFCE, "V"),
        (0xFDB, "X"),
        (0x1000, "V"),
        (0x10A0, "X"),
        (0x10C7, "M", "ⴧ"),
        (0x10C8, "X"),
        (0x10CD, "M", "ⴭ"),
        (0x10CE, "X"),
        (0x10D0, "V"),
        (0x10FC, "M", "ნ"),
        (0x10FD, "V"),
        (0x115F, "X"),
        (0x1161, "V"),
        (0x1249, "X"),
        (0x124A, "V"),
        (0x124E, "X"),
        (0x1250, "V"),
        (0x1257, "X"),
        (0x1258, "V"),
        (0x1259, "X"),
        (0x125A, "V"),
        (0x125E, "X"),
        (0x1260, "V"),
        (0x1289, "X"),
        (0x128A, "V"),
        (0x128E, "X"),
        (0x1290, "V"),
        (0x12B1, "X"),
        (0x12B2, "V"),
        (0x12B6, "X"),
        (0x12B8, "V"),
        (0x12BF, "X"),
        (0x12C0, "V"),
        (0x12C1, "X"),
        (0x12C2, "V"),
        (0x12C6, "X"),
        (0x12C8, "V"),
        (0x12D7, "X"),
        (0x12D8, "V"),
        (0x1311, "X"),
        (0x1312, "V"),
    ]


def _seg_14() -> List[Union[Tuple[int, str], Tuple[int, str, str]]]:
    return [
        (0x1316, "X"),
        (0x1318, "V"),
        (0x135B, "X"),
        (0x135D, "V"),
        (0x137D, "X"),
        (0x1380, "V"),
        (0x139A, "X"),
        (0x13A0, "V"),
        (0x13F6, "X"),
        (0x13F8, "M", "Ᏸ"),
        (0x13F9, "M", "Ᏹ"),
        (0x13FA, "M", "Ᏺ"),
        (0x13FB, "M", "Ᏻ"),
        (0x13FC, "M", "Ᏼ"),
        (0x13FD, "M", "Ᏽ"),
        (0x13FE, "X"),
        (0x1400, "V"),
        (0x1680, "X"),
        (0x1681, "V"),
        (0x169D, "X"),
        (0x16A0, "V"),
        (0x16F9, "X"),
        (0x1700, "V"),
        (0x1716, "X"),
        (0x171F, "V"),
        (0x1737, "X"),
        (0x1740, "V"),
        (0x1754, "X"),
        (0x1760, "V"),
        (0x176D, "X"),
        (0x176E, "V"),
        (0x1771, "X"),
        (0x1772, "V"),
        (0x1774, "X"),
        (0x1780, "V"),
        (0x17B4, "X"),
        (0x17B6, "V"),
        (0x17DE, "X"),
        (0x17E0, "V"),
        (0x17EA, "X"),
        (0x17F0, "V"),
        (0x17FA, "X"),
        (0x1800, "V"),
        (0x1806, "X"),
        (0x1807, "V"),
        (0x180B, "I"),
        (0x180E, "X"),
        (0x180F, "I"),
        (0x1810, "V"),
        (0x181A, "X"),
        (0x1820, "V"),
        (0x1879, "X"),
        (0x1880, "V"),
        (0x18AB, "X"),
        (0x18B0, "V"),
        (0x18F6, "X"),
        (0x1900, "V"),
        (0x191F, "X"),
        (0x1920, "V"),
        (0x192C, "X"),
        (0x1930, "V"),
        (0x193C, "X"),
        (0x1940, "V"),
        (0x1941, "X"),
        (0x1944, "V"),
        (0x196E, "X"),
        (0x1970, "V"),
        (0x1975, "X"),
        (0x1980, "V"),
        (0x19AC, "X"),
        (0x19B0, "V"),
        (0x19CA, "X"),
        (0x19D0, "V"),
        (0x19DB, "X"),
        (0x19DE, "V"),
        (0x1A1C, "X"),
        (0x1A1E, "V"),
        (0x1A5F, "X"),
        (0x1A60, "V"),
        (0x1A7D, "X"),
        (0x1A7F, "V"),
        (0x1A8A, "X"),
        (0x1A90, "V"),
        (0x1A9A, "X"),
        (0x1AA0, "V"),
        (0x1AAE, "X"),
        (0x1AB0, "V"),
        (0x1ACF, "X"),
        (0x1B00, "V"),
        (0x1B4D, "X"),
        (0x1B50, "V"),
        (0x1B7F, "X"),
        (0x1B80, "V"),
        (0x1BF4, "X"),
        (0x1BFC, "V"),
        (0x1C38, "X"),
        (0x1C3B, "V"),
        (0x1C4A, "X"),
        (0x1C4D, "V"),
        (0x1C80, "M", "в"),
    ]


def _seg_15() -> List[Union[Tuple[int, str], Tuple[int, str, str]]]:
    return [
        (0x1C81, "M", "д"),
        (0x1C82, "M", "о"),
        (0x1C83, "M", "с"),
        (0x1C84, "M", "т"),
        (0x1C86, "M", "ъ"),
        (0x1C87, "M", "ѣ"),
        (0x1C88, "M", "ꙋ"),
        (0x1C89, "X"),
        (0x1C90, "M", "ა"),
        (0x1C91, "M", "ბ"),
        (0x1C92, "M", "გ"),
        (0x1C93, "M", "დ"),
        (0x1C94, "M", "ე"),
        (0x1C95, "M", "ვ"),
        (0x1C96, "M", "ზ"),
        (0x1C97, "M", "თ"),
        (0x1C98, "M", "ი"),
        (0x1C99, "M", "კ"),
        (0x1C9A, "M", "ლ"),
        (0x1C9B, "M", "მ"),
        (0x1C9C, "M", "ნ"),
        (0x1C9D, "M", "ო"),
        (0x1C9E, "M", "პ"),
        (0x1C9F, "M", "ჟ"),
        (0x1CA0, "M", "რ"),
        (0x1CA1, "M", "ს"),
        (0x1CA2, "M", "ტ"),
        (0x1CA3, "M", "უ"),
        (0x1CA4, "M", "ფ"),
        (0x1CA5, "M", "ქ"),
        (0x1CA6, "M", "ღ"),
        (0x1CA7, "M", "ყ"),
        (0x1CA8, "M", "შ"),
        (0x1CA9, "M", "ჩ"),
        (0x1CAA, "M", "ც"),
        (0x1CAB, "M", "ძ"),
        (0x1CAC, "M", "წ"),
        (0x1CAD, "M", "ჭ"),
        (0x1CAE, "M", "ხ"),
        (0x1CAF, "M", "ჯ"),
        (0x1CB0, "M", "ჰ"),
        (0x1CB1, "M", "ჱ"),
        (0x1CB2, "M", "ჲ"),
        (0x1CB3, "M", "ჳ"),
        (0x1CB4, "M", "ჴ"),
        (0x1CB5, "M", "ჵ"),
        (0x1CB6, "M", "ჶ"),
        (0x1CB7, "M", "ჷ"),
        (0x1CB8, "M", "ჸ"),
        (0x1CB9, "M", "ჹ"),
        (0x1CBA, "M", "ჺ"),
        (0x1CBB, "X"),
        (0x1CBD, "M", "ჽ"),
        (0x1CBE, "M", "ჾ"),
        (0x1CBF, "M", "ჿ"),
        (0x1CC0, "V"),
        (0x1CC8, "X"),
        (0x1CD0, "V"),
        (0x1CFB, "X"),
        (0x1D00, "V"),
        (0x1D2C, "M", "a"),
        (0x1D2D, "M", "æ"),
        (0x1D2E, "M", "b"),
        (0x1D2F, "V"),
        (0x1D30, "M", "d"),
        (0x1D31, "M", "e"),
        (0x1D32, "M", "ǝ"),
        (0x1D33, "M", "g"),
        (0x1D34, "M", "h"),
        (0x1D35, "M", "i"),
        (0x1D36, "M", "j"),
        (0x1D37, "M", "k"),
        (0x1D38, "M", "l"),
        (0x1D39, "M", "m"),
        (0x1D3A, "M", "n"),
        (0x1D3B, "V"),
        (0x1D3C, "M", "o"),
        (0x1D3D, "M", "ȣ"),
        (0x1D3E, "M", "p"),
        (0x1D3F, "M", "r"),
        (0x1D40, "M", "t"),
        (0x1D41, "M", "u"),
        (0x1D42, "M", "w"),
        (0x1D43, "M", "a"),
        (0x1D44, "M", "ɐ"),
        (0x1D45, "M", "ɑ"),
        (0x1D46, "M", "ᴂ"),
        (0x1D47, "M", "b"),
        (0x1D48, "M", "d"),
        (0x1D49, "M", "e"),
        (0x1D4A, "M", "ə"),
        (0x1D4B, "M", "ɛ"),
        (0x1D4C, "M", "ɜ"),
        (0x1D4D, "M", "g"),
        (0x1D4E, "V"),
        (0x1D4F, "M", "k"),
        (0x1D50, "M", "m"),
        (0x1D51, "M", "ŋ"),
        (0x1D52, "M", "o"),
        (0x1D53, "M", "ɔ"),
    ]


def _seg_16() -> List[Union[Tuple[int, str], Tuple[int, str, str]]]:
    return [
        (0x1D54, "M", "ᴖ"),
        (0x1D55, "M", "ᴗ"),
        (0x1D56, "M", "p"),
        (0x1D57, "M", "t"),
        (0x1D58, "M", "u"),
        (0x1D59, "M", "ᴝ"),
        (0x1D5A, "M", "ɯ"),
        (0x1D5B, "M", "v"),
        (0x1D5C, "M", "ᴥ"),
        (0x1D5D, "M", "β"),
        (0x1D5E, "M", "γ"),
        (0x1D5F, "M", "δ"),
        (0x1D60, "M", "φ"),
        (0x1D61, "M", "χ"),
        (0x1D62, "M", "i"),
        (0x1D63, "M", "r"),
        (0x1D64, "M", "u"),
        (0x1D65, "M", "v"),
        (0x1D66, "M", "β"),
        (0x1D67, "M", "γ"),
        (0x1D68, "M", "ρ"),
        (0x1D69, "M", "φ"),
        (0x1D6A, "M", "χ"),
        (0x1D6B, "V"),
        (0x1D78, "M", "н"),
        (0x1D79, "V"),
        (0x1D9B, "M", "ɒ"),
        (0x1D9C, "M", "c"),
        (0x1D9D, "M", "ɕ"),
        (0x1D9E, "M", "ð"),
        (0x1D9F, "M", "ɜ"),
        (0x1DA0, "M", "f"),
        (0x1DA1, "M", "ɟ"),
        (0x1DA2, "M", "ɡ"),
        (0x1DA3, "M", "ɥ"),
        (0x1DA4, "M", "ɨ"),
        (0x1DA5, "M", "ɩ"),
        (0x1DA6, "M", "ɪ"),
        (0x1DA7, "M", "ᵻ"),
        (0x1DA8, "M", "ʝ"),
        (0x1DA9, "M", "ɭ"),
        (0x1DAA, "M", "ᶅ"),
        (0x1DAB, "M", "ʟ"),
        (0x1DAC, "M", "ɱ"),
        (0x1DAD, "M", "ɰ"),
        (0x1DAE, "M", "ɲ"),
        (0x1DAF, "M", "ɳ"),
        (0x1DB0, "M", "ɴ"),
        (0x1DB1, "M", "ɵ"),
        (0x1DB2, "M", "ɸ"),
        (0x1DB3, "M", "ʂ"),
        (0x1DB4, "M", "ʃ"),
        (0x1DB5, "M", "ƫ"),
        (0x1DB6, "M", "ʉ"),
        (0x1DB7, "M", "ʊ"),
        (0x1DB8, "M", "ᴜ"),
        (0x1DB9, "M", "ʋ"),
        (0x1DBA, "M", "ʌ"),
        (0x1DBB, "M", "z"),
        (0x1DBC, "M", "ʐ"),
        (0x1DBD, "M", "ʑ"),
        (0x1DBE, "M", "ʒ"),
        (0x1DBF, "M", "θ"),
        (0x1DC0, "V"),
        (0x1E00, "M", "ḁ"),
        (0x1E01, "V"),
        (0x1E02, "M", "ḃ"),
        (0x1E03, "V"),
        (0x1E04, "M", "ḅ"),
        (0x1E05, "V"),
        (0x1E06, "M", "ḇ"),
        (0x1E07, "V"),
        (0x1E08, "M", "ḉ"),
        (0x1E09, "V"),
        (0x1E0A, "M", "ḋ"),
        (0x1E0B, "V"),
        (0x1E0C, "M", "ḍ"),
        (0x1E0D, "V"),
        (0x1E0E, "M", "ḏ"),
        (0x1E0F, "V"),
        (0x1E10, "M", "ḑ"),
        (0x1E11, "V"),
        (0x1E12, "M", "ḓ"),
        (0x1E13, "V"),
        (0x1E14, "M", "ḕ"),
        (0x1E15, "V"),
        (0x1E16, "M", "ḗ"),
        (0x1E17, "V"),
        (0x1E18, "M", "ḙ"),
        (0x1E19, "V"),
        (0x1E1A, "M", "ḛ"),
        (0x1E1B, "V"),
        (0x1E1C, "M", "ḝ"),
        (0x1E1D, "V"),
        (0x1E1E, "M", "ḟ"),
        (0x1E1F, "V"),
        (0x1E20, "M", "ḡ"),
        (0x1E21, "V"),
        (0x1E22, "M", "ḣ"),
        (0x1E23, "V"),
    ]


def _seg_17() -> List[Union[Tuple[int, str], Tuple[int, str, str]]]:
    return [
        (0x1E24, "M", "ḥ"),
        (0x1E25, "V"),
        (0x1E26, "M", "ḧ"),
        (0x1E27, "V"),
        (0x1E28, "M", "ḩ"),
        (0x1E29, "V"),
        (0x1E2A, "M", "ḫ"),
        (0x1E2B, "V"),
        (0x1E2C, "M", "ḭ"),
        (0x1E2D, "V"),
        (0x1E2E, "M", "ḯ"),
        (0x1E2F, "V"),
        (0x1E30, "M", "ḱ"),
        (0x1E31, "V"),
        (0x1E32, "M", "ḳ"),
        (0x1E33, "V"),
        (0x1E34, "M", "ḵ"),
        (0x1E35, "V"),
        (0x1E36, "M", "ḷ"),
        (0x1E37, "V"),
        (0x1E38, "M", "ḹ"),
        (0x1E39, "V"),
        (0x1E3A, "M", "ḻ"),
        (0x1E3B, "V"),
        (0x1E3C, "M", "ḽ"),
        (0x1E3D, "V"),
        (0x1E3E, "M", "ḿ"),
        (0x1E3F, "V"),
        (0x1E40, "M", "ṁ"),
        (0x1E41, "V"),
        (0x1E42, "M", "ṃ"),
        (0x1E43, "V"),
        (0x1E44, "M", "ṅ"),
        (0x1E45, "V"),
        (0x1E46, "M", "ṇ"),
        (0x1E47, "V"),
        (0x1E48, "M", "ṉ"),
        (0x1E49, "V"),
        (0x1E4A, "M", "ṋ"),
        (0x1E4B, "V"),
        (0x1E4C, "M", "ṍ"),
        (0x1E4D, "V"),
        (0x1E4E, "M", "ṏ"),
        (0x1E4F, "V"),
        (0x1E50, "M", "ṑ"),
        (0x1E51, "V"),
        (0x1E52, "M", "ṓ"),
        (0x1E53, "V"),
        (0x1E54, "M", "ṕ"),
        (0x1E55, "V"),
        (0x1E56, "M", "ṗ"),
        (0x1E57, "V"),
        (0x1E58, "M", "ṙ"),
        (0x1E59, "V"),
        (0x1E5A, "M", "ṛ"),
        (0x1E5B, "V"),
        (0x1E5C, "M", "ṝ"),
        (0x1E5D, "V"),
        (0x1E5E, "M", "ṟ"),
        (0x1E5F, "V"),
        (0x1E60, "M", "ṡ"),
        (0x1E61, "V"),
        (0x1E62, "M", "ṣ"),
        (0x1E63, "V"),
        (0x1E64, "M", "ṥ"),
        (0x1E65, "V"),
        (0x1E66, "M", "ṧ"),
        (0x1E67, "V"),
        (0x1E68, "M", "ṩ"),
        (0x1E69, "V"),
        (0x1E6A, "M", "ṫ"),
        (0x1E6B, "V"),
        (0x1E6C, "M", "ṭ"),
        (0x1E6D, "V"),
        (0x1E6E, "M", "ṯ"),
        (0x1E6F, "V"),
        (0x1E70, "M", "ṱ"),
        (0x1E71, "V"),
        (0x1E72, "M", "ṳ"),
        (0x1E73, "V"),
        (0x1E74, "M", "ṵ"),
        (0x1E75, "V"),
        (0x1E76, "M", "ṷ"),
        (0x1E77, "V"),
        (0x1E78, "M", "ṹ"),
        (0x1E79, "V"),
        (0x1E7A, "M", "ṻ"),
        (0x1E7B, "V"),
        (0x1E7C, "M", "ṽ"),
        (0x1E7D, "V"),
        (0x1E7E, "M", "ṿ"),
        (0x1E7F, "V"),
        (0x1E80, "M", "ẁ"),
        (0x1E81, "V"),
        (0x1E82, "M", "ẃ"),
        (0x1E83, "V"),
        (0x1E84, "M", "ẅ"),
        (0x1E85, "V"),
        (0x1E86, "M", "ẇ"),
        (0x1E87, "V"),
    ]


def _seg_18() -> List[Union[Tuple[int, str], Tuple[int, str, str]]]:
    return [
        (0x1E88, "M", "ẉ"),
        (0x1E89, "V"),
        (0x1E8A, "M", "ẋ"),
        (0x1E8B, "V"),
        (0x1E8C, "M", "ẍ"),
        (0x1E8D, "V"),
        (0x1E8E, "M", "ẏ"),
        (0x1E8F, "V"),
        (0x1E90, "M", "ẑ"),
        (0x1E91, "V"),
        (0x1E92, "M", "ẓ"),
        (0x1E93, "V"),
        (0x1E94, "M", "ẕ"),
        (0x1E95, "V"),
        (0x1E9A, "M", "aʾ"),
        (0x1E9B, "M", "ṡ"),
        (0x1E9C, "V"),
        (0x1E9E, "M", "ß"),
        (0x1E9F, "V"),
        (0x1EA0, "M", "ạ"),
        (0x1EA1, "V"),
        (0x1EA2, "M", "ả"),
        (0x1EA3, "V"),
        (0x1EA4, "M", "ấ"),
        (0x1EA5, "V"),
        (0x1EA6, "M", "ầ"),
        (0x1EA7, "V"),
        (0x1EA8, "M", "ẩ"),
        (0x1EA9, "V"),
        (0x1EAA, "M", "ẫ"),
        (0x1EAB, "V"),
        (0x1EAC, "M", "ậ"),
        (0x1EAD, "V"),
        (0x1EAE, "M", "ắ"),
        (0x1EAF, "V"),
        (0x1EB0, "M", "ằ"),
        (0x1EB1, "V"),
        (0x1EB2, "M", "ẳ"),
        (0x1EB3, "V"),
        (0x1EB4, "M", "ẵ"),
        (0x1EB5, "V"),
        (0x1EB6, "M", "ặ"),
        (0x1EB7, "V"),
        (0x1EB8, "M", "ẹ"),
        (0x1EB9, "V"),
        (0x1EBA, "M", "ẻ"),
        (0x1EBB, "V"),
        (0x1EBC, "M", "ẽ"),
        (0x1EBD, "V"),
        (0x1EBE, "M", "ế"),
        (0x1EBF, "V"),
        (0x1EC0, "M", "ề"),
        (0x1EC1, "V"),
        (0x1EC2, "M", "ể"),
        (0x1EC3, "V"),
        (0x1EC4, "M", "ễ"),
        (0x1EC5, "V"),
        (0x1EC6, "M", "ệ"),
        (0x1EC7, "V"),
        (0x1EC8, "M", "ỉ"),
        (0x1EC9, "V"),
        (0x1ECA, "M", "ị"),
        (0x1ECB, "V"),
        (0x1ECC, "M", "ọ"),
        (0x1ECD, "V"),
        (0x1ECE, "M", "ỏ"),
        (0x1ECF, "V"),
        (0x1ED0, "M", "ố"),
        (0x1ED1, "V"),
        (0x1ED2, "M", "ồ"),
        (0x1ED3, "V"),
        (0x1ED4, "M", "ổ"),
        (0x1ED5, "V"),
        (0x1ED6, "M", "ỗ"),
        (0x1ED7, "V"),
        (0x1ED8, "M", "ộ"),
        (0x1ED9, "V"),
        (0x1EDA, "M", "ớ"),
        (0x1EDB, "V"),
        (0x1EDC, "M", "ờ"),
        (0x1EDD, "V"),
        (0x1EDE, "M", "ở"),
        (0x1EDF, "V"),
        (0x1EE0, "M", "ỡ"),
        (0x1EE1, "V"),
        (0x1EE2, "M", "ợ"),
        (0x1EE3, "V"),
        (0x1EE4, "M", "ụ"),
        (0x1EE5, "V"),
        (0x1EE6, "M", "ủ"),
        (0x1EE7, "V"),
        (0x1EE8, "M", "ứ"),
        (0x1EE9, "V"),
        (0x1EEA, "M", "ừ"),
        (0x1EEB, "V"),
        (0x1EEC, "M", "ử"),
        (0x1EED, "V"),
        (0x1EEE, "M", "ữ"),
        (0x1EEF, "V"),
        (0x1EF0, "M", "ự"),
    ]


def _seg_19() -> List[Union[Tuple[int, str], Tuple[int, str, str]]]:
    return [
        (0x1EF1, "V"),
        (0x1EF2, "M", "ỳ"),
        (0x1EF3, "V"),
        (0x1EF4, "M", "ỵ"),
        (0x1EF5, "V"),
        (0x1EF6, "M", "ỷ"),
        (0x1EF7, "V"),
        (0x1EF8, "M", "ỹ"),
        (0x1EF9, "V"),
        (0x1EFA, "M", "ỻ"),
        (0x1EFB, "V"),
        (0x1EFC, "M", "ỽ"),
        (0x1EFD, "V"),
        (0x1EFE, "M", "ỿ"),
        (0x1EFF, "V"),
        (0x1F08, "M", "ἀ"),
        (0x1F09, "M", "ἁ"),
        (0x1F0A, "M", "ἂ"),
        (0x1F0B, "M", "ἃ"),
        (0x1F0C, "M", "ἄ"),
        (0x1F0D, "M", "ἅ"),
        (0x1F0E, "M", "ἆ"),
        (0x1F0F, "M", "ἇ"),
        (0x1F10, "V"),
        (0x1F16, "X"),
        (0x1F18, "M", "ἐ"),
        (0x1F19, "M", "ἑ"),
        (0x1F1A, "M", "ἒ"),
        (0x1F1B, "M", "ἓ"),
        (0x1F1C, "M", "ἔ"),
        (0x1F1D, "M", "ἕ"),
        (0x1F1E, "X"),
        (0x1F20, "V"),
        (0x1F28, "M", "ἠ"),
        (0x1F29, "M", "ἡ"),
        (0x1F2A, "M", "ἢ"),
        (0x1F2B, "M", "ἣ"),
        (0x1F2C, "M", "ἤ"),
        (0x1F2D, "M", "ἥ"),
        (0x1F2E, "M", "ἦ"),
        (0x1F2F, "M", "ἧ"),
        (0x1F30, "V"),
        (0x1F38, "M", "ἰ"),
        (0x1F39, "M", "ἱ"),
        (0x1F3A, "M", "ἲ"),
        (0x1F3B, "M", "ἳ"),
        (0x1F3C, "M", "ἴ"),
        (0x1F3D, "M", "ἵ"),
        (0x1F3E, "M", "ἶ"),
        (0x1F3F, "M", "ἷ"),
        (0x1F40, "V"),
        (0x1F46, "X"),
        (0x1F48, "M", "ὀ"),
        (0x1F49, "M", "ὁ"),
        (0x1F4A, "M", "ὂ"),
        (0x1F4B, "M", "ὃ"),
        (0x1F4C, "M", "ὄ"),
        (0x1F4D, "M", "ὅ"),
        (0x1F4E, "X"),
        (0x1F50, "V"),
        (0x1F58, "X"),
        (0x1F59, "M", "ὑ"),
        (0x1F5A, "X"),
        (0x1F5B, "M", "ὓ"),
        (0x1F5C, "X"),
        (0x1F5D, "M", "ὕ"),
        (0x1F5E, "X"),
        (0x1F5F, "M", "ὗ"),
        (0x1F60, "V"),
        (0x1F68, "M", "ὠ"),
        (0x1F69, "M", "ὡ"),
        (0x1F6A, "M", "ὢ"),
        (0x1F6B, "M", "ὣ"),
        (0x1F6C, "M", "ὤ"),
        (0x1F6D, "M", "ὥ"),
        (0x1F6E, "M", "ὦ"),
        (0x1F6F, "M", "ὧ"),
        (0x1F70, "V"),
        (0x1F71, "M", "ά"),
        (0x1F72, "V"),
        (0x1F73, "M", "έ"),
        (0x1F74, "V"),
        (0x1F75, "M", "ή"),
        (0x1F76, "V"),
        (0x1F77, "M", "ί"),
        (0x1F78, "V"),
        (0x1F79, "M", "ό"),
        (0x1F7A, "V"),
        (0x1F7B, "M", "ύ"),
        (0x1F7C, "V"),
        (0x1F7D, "M", "ώ"),
        (0x1F7E, "X"),
        (0x1F80, "M", "ἀι"),
        (0x1F81, "M", "ἁι"),
        (0x1F82, "M", "ἂι"),
        (0x1F83, "M", "ἃι"),
        (0x1F84, "M", "ἄι"),
        (0x1F85, "M", "ἅι"),
        (0x1F86, "M", "ἆι"),
        (0x1F87, "M", "ἇι"),
    ]


def _seg_20() -> List[Union[Tuple[int, str], Tuple[int, str, str]]]:
    return [
        (0x1F88, "M", "ἀι"),
        (0x1F89, "M", "ἁι"),
        (0x1F8A, "M", "ἂι"),
        (0x1F8B, "M", "ἃι"),
        (0x1F8C, "M", "ἄι"),
        (0x1F8D, "M", "ἅι"),
        (0x1F8E, "M", "ἆι"),
        (0x1F8F, "M", "ἇι"),
        (0x1F90, "M", "ἠι"),
        (0x1F91, "M", "ἡι"),
        (0x1F92, "M", "ἢι"),
        (0x1F93, "M", "ἣι"),
        (0x1F94, "M", "ἤι"),
        (0x1F95, "M", "ἥι"),
        (0x1F96, "M", "ἦι"),
        (0x1F97, "M", "ἧι"),
        (0x1F98, "M", "ἠι"),
        (0x1F99, "M", "ἡι"),
        (0x1F9A, "M", "ἢι"),
        (0x1F9B, "M", "ἣι"),
        (0x1F9C, "M", "ἤι"),
        (0x1F9D, "M", "ἥι"),
        (0x1F9E, "M", "ἦι"),
        (0x1F9F, "M", "ἧι"),
        (0x1FA0, "M", "ὠι"),
        (0x1FA1, "M", "ὡι"),
        (0x1FA2, "M", "ὢι"),
        (0x1FA3, "M", "ὣι"),
        (0x1FA4, "M", "ὤι"),
        (0x1FA5, "M", "ὥι"),
        (0x1FA6, "M", "ὦι"),
        (0x1FA7, "M", "ὧι"),
        (0x1FA8, "M", "ὠι"),
        (0x1FA9, "M", "ὡι"),
        (0x1FAA, "M", "ὢι"),
        (0x1FAB, "M", "ὣι"),
        (0x1FAC, "M", "ὤι"),
        (0x1FAD, "M", "ὥι"),
        (0x1FAE, "M", "ὦι"),
        (0x1FAF, "M", "ὧι"),
        (0x1FB0, "V"),
        (0x1FB2, "M", "ὰι"),
        (0x1FB3, "M", "αι"),
        (0x1FB4, "M", "άι"),
        (0x1FB5, "X"),
        (0x1FB6, "V"),
        (0x1FB7, "M", "ᾶι"),
        (0x1FB8, "M", "ᾰ"),
        (0x1FB9, "M", "ᾱ"),
        (0x1FBA, "M", "ὰ"),
        (0x1FBB, "M", "ά"),
        (0x1FBC, "M", "αι"),
        (0x1FBD, "3", " ̓"),
        (0x1FBE, "M", "ι"),
        (0x1FBF, "3", " ̓"),
        (0x1FC0, "3", " ͂"),
        (0x1FC1, "3", " ̈͂"),
        (0x1FC2, "M", "ὴι"),
        (0x1FC3, "M", "ηι"),
        (0x1FC4, "M", "ήι"),
        (0x1FC5, "X"),
        (0x1FC6, "V"),
        (0x1FC7, "M", "ῆι"),
        (0x1FC8, "M", "ὲ"),
        (0x1FC9, "M", "έ"),
        (0x1FCA, "M", "ὴ"),
        (0x1FCB, "M", "ή"),
        (0x1FCC, "M", "ηι"),
        (0x1FCD, "3", " ̓̀"),
        (0x1FCE, "3", " ̓́"),
        (0x1FCF, "3", " ̓͂"),
        (0x1FD0, "V"),
        (0x1FD3, "M", "ΐ"),
        (0x1FD4, "X"),
        (0x1FD6, "V"),
        (0x1FD8, "M", "ῐ"),
        (0x1FD9, "M", "ῑ"),
        (0x1FDA, "M", "ὶ"),
        (0x1FDB, "M", "ί"),
        (0x1FDC, "X"),
        (0x1FDD, "3", " ̔̀"),
        (0x1FDE, "3", " ̔́"),
        (0x1FDF, "3", " ̔͂"),
        (0x1FE0, "V"),
        (0x1FE3, "M", "ΰ"),
        (0x1FE4, "V"),
        (0x1FE8, "M", "ῠ"),
        (0x1FE9, "M", "ῡ"),
        (0x1FEA, "M", "ὺ"),
        (0x1FEB, "M", "ύ"),
        (0x1FEC, "M", "ῥ"),
        (0x1FED, "3", " ̈̀"),
        (0x1FEE, "3", " ̈́"),
        (0x1FEF, "3", "`"),
        (0x1FF0, "X"),
        (0x1FF2, "M", "ὼι"),
        (0x1FF3, "M", "ωι"),
        (0x1FF4, "M", "ώι"),
        (0x1FF5, "X"),
        (0x1FF6, "V"),
    ]


def _seg_21() -> List[Union[Tuple[int, str], Tuple[int, str, str]]]:
    return [
        (0x1FF7, "M", "ῶι"),
        (0x1FF8, "M", "ὸ"),
        (0x1FF9, "M", "ό"),
        (0x1FFA, "M", "ὼ"),
        (0x1FFB, "M", "ώ"),
        (0x1FFC, "M", "ωι"),
        (0x1FFD, "3", " ́"),
        (0x1FFE, "3", " ̔"),
        (0x1FFF, "X"),
        (0x2000, "3", " "),
        (0x200B, "I"),
        (0x200C, "D", ""),
        (0x200E, "X"),
        (0x2010, "V"),
        (0x2011, "M", "‐"),
        (0x2012, "V"),
        (0x2017, "3", " ̳"),
        (0x2018, "V"),
        (0x2024, "X"),
        (0x2027, "V"),
        (0x2028, "X"),
        (0x202F, "3", " "),
        (0x2030, "V"),
        (0x2033, "M", "′′"),
        (0x2034, "M", "′′′"),
        (0x2035, "V"),
        (0x2036, "M", "‵‵"),
        (0x2037, "M", "‵‵‵"),
        (0x2038, "V"),
        (0x203C, "3", "!!"),
        (0x203D, "V"),
        (0x203E, "3", " ̅"),
        (0x203F, "V"),
        (0x2047, "3", "??"),
        (0x2048, "3", "?!"),
        (0x2049, "3", "!?"),
        (0x204A, "V"),
        (0x2057, "M", "′′′′"),
        (0x2058, "V"),
        (0x205F, "3", " "),
        (0x2060, "I"),
        (0x2061, "X"),
        (0x2064, "I"),
        (0x2065, "X"),
        (0x2070, "M", "0"),
        (0x2071, "M", "i"),
        (0x2072, "X"),
        (0x2074, "M", "4"),
        (0x2075, "M", "5"),
        (0x2076, "M", "6"),
        (0x2077, "M", "7"),
        (0x2078, "M", "8"),
        (0x2079, "M", "9"),
        (0x207A, "3", "+"),
        (0x207B, "M", "−"),
        (0x207C, "3", "="),
        (0x207D, "3", "("),
        (0x207E, "3", ")"),
        (0x207F, "M", "n"),
        (0x2080, "M", "0"),
        (0x2081, "M", "1"),
        (0x2082, "M", "2"),
        (0x2083, "M", "3"),
        (0x2084, "M", "4"),
        (0x2085, "M", "5"),
        (0x2086, "M", "6"),
        (0x2087, "M", "7"),
        (0x2088, "M", "8"),
        (0x2089, "M", "9"),
        (0x208A, "3", "+"),
        (0x208B, "M", "−"),
        (0x208C, "3", "="),
        (0x208D, "3", "("),
        (0x208E, "3", ")"),
        (0x208F, "X"),
        (0x2090, "M", "a"),
        (0x2091, "M", "e"),
        (0x2092, "M", "o"),
        (0x2093, "M", "x"),
        (0x2094, "M", "ə"),
        (0x2095, "M", "h"),
        (0x2096, "M", "k"),
        (0x2097, "M", "l"),
        (0x2098, "M", "m"),
        (0x2099, "M", "n"),
        (0x209A, "M", "p"),
        (0x209B, "M", "s"),
        (0x209C, "M", "t"),
        (0x209D, "X"),
        (0x20A0, "V"),
        (0x20A8, "M", "rs"),
        (0x20A9, "V"),
        (0x20C1, "X"),
        (0x20D0, "V"),
        (0x20F1, "X"),
        (0x2100, "3", "a/c"),
        (0x2101, "3", "a/s"),
        (0x2102, "M", "c"),
        (0x2103, "M", "°c"),
        (0x2104, "V"),
    ]


def _seg_22() -> List[Union[Tuple[int, str], Tuple[int, str, str]]]:
    return [
        (0x2105, "3", "c/o"),
        (0x2106, "3", "c/u"),
        (0x2107, "M", "ɛ"),
        (0x2108, "V"),
        (0x2109, "M", "°f"),
        (0x210A, "M", "g"),
        (0x210B, "M", "h"),
        (0x210F, "M", "ħ"),
        (0x2110, "M", "i"),
        (0x2112, "M", "l"),
        (0x2114, "V"),
        (0x2115, "M", "n"),
        (0x2116, "M", "no"),
        (0x2117, "V"),
        (0x2119, "M", "p"),
        (0x211A, "M", "q"),
        (0x211B, "M", "r"),
        (0x211E, "V"),
        (0x2120, "M", "sm"),
        (0x2121, "M", "tel"),
        (0x2122, "M", "tm"),
        (0x2123, "V"),
        (0x2124, "M", "z"),
        (0x2125, "V"),
        (0x2126, "M", "ω"),
        (0x2127, "V"),
        (0x2128, "M", "z"),
        (0x2129, "V"),
        (0x212A, "M", "k"),
        (0x212B, "M", "å"),
        (0x212C, "M", "b"),
        (0x212D, "M", "c"),
        (0x212E, "V"),
        (0x212F, "M", "e"),
        (0x2131, "M", "f"),
        (0x2132, "X"),
        (0x2133, "M", "m"),
        (0x2134, "M", "o"),
        (0x2135, "M", "א"),
        (0x2136, "M", "ב"),
        (0x2137, "M", "ג"),
        (0x2138, "M", "ד"),
        (0x2139, "M", "i"),
        (0x213A, "V"),
        (0x213B, "M", "fax"),
        (0x213C, "M", "π"),
        (0x213D, "M", "γ"),
        (0x213F, "M", "π"),
        (0x2140, "M", "∑"),
        (0x2141, "V"),
        (0x2145, "M", "d"),
        (0x2147, "M", "e"),
        (0x2148, "M", "i"),
        (0x2149, "M", "j"),
        (0x214A, "V"),
        (0x2150, "M", "1⁄7"),
        (0x2151, "M", "1⁄9"),
        (0x2152, "M", "1⁄10"),
        (0x2153, "M", "1⁄3"),
        (0x2154, "M", "2⁄3"),
        (0x2155, "M", "1⁄5"),
        (0x2156, "M", "2⁄5"),
        (0x2157, "M", "3⁄5"),
        (0x2158, "M", "4⁄5"),
        (0x2159, "M", "1⁄6"),
        (0x215A, "M", "5⁄6"),
        (0x215B, "M", "1⁄8"),
        (0x215C, "M", "3⁄8"),
        (0x215D, "M", "5⁄8"),
        (0x215E, "M", "7⁄8"),
        (0x215F, "M", "1⁄"),
        (0x2160, "M", "i"),
        (0x2161, "M", "ii"),
        (0x2162, "M", "iii"),
        (0x2163, "M", "iv"),
        (0x2164, "M", "v"),
        (0x2165, "M", "vi"),
        (0x2166, "M", "vii"),
        (0x2167, "M", "viii"),
        (0x2168, "M", "ix"),
        (0x2169, "M", "x"),
        (0x216A, "M", "xi"),
        (0x216B, "M", "xii"),
        (0x216C, "M", "l"),
        (0x216D, "M", "c"),
        (0x216E, "M", "d"),
        (0x216F, "M", "m"),
        (0x2170, "M", "i"),
        (0x2171, "M", "ii"),
        (0x2172, "M", "iii"),
        (0x2173, "M", "iv"),
        (0x2174, "M", "v"),
        (0x2175, "M", "vi"),
        (0x2176, "M", "vii"),
        (0x2177, "M", "viii"),
        (0x2178, "M", "ix"),
        (0x2179, "M", "x"),
        (0x217A, "M", "xi"),
        (0x217B, "M", "xii"),
        (0x217C, "M", "l"),
    ]


def _seg_23() -> List[Union[Tuple[int, str], Tuple[int, str, str]]]:
    return [
        (0x217D, "M", "c"),
        (0x217E, "M", "d"),
        (0x217F, "M", "m"),
        (0x2180, "V"),
        (0x2183, "X"),
        (0x2184, "V"),
        (0x2189, "M", "0⁄3"),
        (0x218A, "V"),
        (0x218C, "X"),
        (0x2190, "V"),
        (0x222C, "M", "∫∫"),
        (0x222D, "M", "∫∫∫"),
        (0x222E, "V"),
        (0x222F, "M", "∮∮"),
        (0x2230, "M", "∮∮∮"),
        (0x2231, "V"),
        (0x2329, "M", "〈"),
        (0x232A, "M", "〉"),
        (0x232B, "V"),
        (0x2427, "X"),
        (0x2440, "V"),
        (0x244B, "X"),
        (0x2460, "M", "1"),
        (0x2461, "M", "2"),
        (0x2462, "M", "3"),
        (0x2463, "M", "4"),
        (0x2464, "M", "5"),
        (0x2465, "M", "6"),
        (0x2466, "M", "7"),
        (0x2467, "M", "8"),
        (0x2468, "M", "9"),
        (0x2469, "M", "10"),
        (0x246A, "M", "11"),
        (0x246B, "M", "12"),
        (0x246C, "M", "13"),
        (0x246D, "M", "14"),
        (0x246E, "M", "15"),
        (0x246F, "M", "16"),
        (0x2470, "M", "17"),
        (0x2471, "M", "18"),
        (0x2472, "M", "19"),
        (0x2473, "M", "20"),
        (0x2474, "3", "(1)"),
        (0x2475, "3", "(2)"),
        (0x2476, "3", "(3)"),
        (0x2477, "3", "(4)"),
        (0x2478, "3", "(5)"),
        (0x2479, "3", "(6)"),
        (0x247A, "3", "(7)"),
        (0x247B, "3", "(8)"),
        (0x247C, "3", "(9)"),
        (0x247D, "3", "(10)"),
        (0x247E, "3", "(11)"),
        (0x247F, "3", "(12)"),
        (0x2480, "3", "(13)"),
        (0x2481, "3", "(14)"),
        (0x2482, "3", "(15)"),
        (0x2483, "3", "(16)"),
        (0x2484, "3", "(17)"),
        (0x2485, "3", "(18)"),
        (0x2486, "3", "(19)"),
        (0x2487, "3", "(20)"),
        (0x2488, "X"),
        (0x249C, "3", "(a)"),
        (0x249D, "3", "(b)"),
        (0x249E, "3", "(c)"),
        (0x249F, "3", "(d)"),
        (0x24A0, "3", "(e)"),
        (0x24A1, "3", "(f)"),
        (0x24A2, "3", "(g)"),
        (0x24A3, "3", "(h)"),
        (0x24A4, "3", "(i)"),
        (0x24A5, "3", "(j)"),
        (0x24A6, "3", "(k)"),
        (0x24A7, "3", "(l)"),
        (0x24A8, "3", "(m)"),
        (0x24A9, "3", "(n)"),
        (0x24AA, "3", "(o)"),
        (0x24AB, "3", "(p)"),
        (0x24AC, "3", "(q)"),
        (0x24AD, "3", "(r)"),
        (0x24AE, "3", "(s)"),
        (0x24AF, "3", "(t)"),
        (0x24B0, "3", "(u)"),
        (0x24B1, "3", "(v)"),
        (0x24B2, "3", "(w)"),
        (0x24B3, "3", "(x)"),
        (0x24B4, "3", "(y)"),
        (0x24B5, "3", "(z)"),
        (0x24B6, "M", "a"),
        (0x24B7, "M", "b"),
        (0x24B8, "M", "c"),
        (0x24B9, "M", "d"),
        (0x24BA, "M", "e"),
        (0x24BB, "M", "f"),
        (0x24BC, "M", "g"),
        (0x24BD, "M", "h"),
        (0x24BE, "M", "i"),
        (0x24BF, "M", "j"),
        (0x24C0, "M", "k"),
    ]


def _seg_24() -> List[Union[Tuple[int, str], Tuple[int, str, str]]]:
    return [
        (0x24C1, "M", "l"),
        (0x24C2, "M", "m"),
        (0x24C3, "M", "n"),
        (0x24C4, "M", "o"),
        (0x24C5, "M", "p"),
        (0x24C6, "M", "q"),
        (0x24C7, "M", "r"),
        (0x24C8, "M", "s"),
        (0x24C9, "M", "t"),
        (0x24CA, "M", "u"),
        (0x24CB, "M", "v"),
        (0x24CC, "M", "w"),
        (0x24CD, "M", "x"),
        (0x24CE, "M", "y"),
        (0x24CF, "M", "z"),
        (0x24D0, "M", "a"),
        (0x24D1, "M", "b"),
        (0x24D2, "M", "c"),
        (0x24D3, "M", "d"),
        (0x24D4, "M", "e"),
        (0x24D5, "M", "f"),
        (0x24D6, "M", "g"),
        (0x24D7, "M", "h"),
        (0x24D8, "M", "i"),
        (0x24D9, "M", "j"),
        (0x24DA, "M", "k"),
        (0x24DB, "M", "l"),
        (0x24DC, "M", "m"),
        (0x24DD, "M", "n"),
        (0x24DE, "M", "o"),
        (0x24DF, "M", "p"),
        (0x24E0, "M", "q"),
        (0x24E1, "M", "r"),
        (0x24E2, "M", "s"),
        (0x24E3, "M", "t"),
        (0x24E4, "M", "u"),
        (0x24E5, "M", "v"),
        (0x24E6, "M", "w"),
        (0x24E7, "M", "x"),
        (0x24E8, "M", "y"),
        (0x24E9, "M", "z"),
        (0x24EA, "M", "0"),
        (0x24EB, "V"),
        (0x2A0C, "M", "∫∫∫∫"),
        (0x2A0D, "V"),
        (0x2A74, "3", "::="),
        (0x2A75, "3", "=="),
        (0x2A76, "3", "==="),
        (0x2A77, "V"),
        (0x2ADC, "M", "⫝̸"),
        (0x2ADD, "V"),
        (0x2B74, "X"),
        (0x2B76, "V"),
        (0x2B96, "X"),
        (0x2B97, "V"),
        (0x2C00, "M", "ⰰ"),
        (0x2C01, "M", "ⰱ"),
        (0x2C02, "M", "ⰲ"),
        (0x2C03, "M", "ⰳ"),
        (0x2C04, "M", "ⰴ"),
        (0x2C05, "M", "ⰵ"),
        (0x2C06, "M", "ⰶ"),
        (0x2C07, "M", "ⰷ"),
        (0x2C08, "M", "ⰸ"),
        (0x2C09, "M", "ⰹ"),
        (0x2C0A, "M", "ⰺ"),
        (0x2C0B, "M", "ⰻ"),
        (0x2C0C, "M", "ⰼ"),
        (0x2C0D, "M", "ⰽ"),
        (0x2C0E, "M", "ⰾ"),
        (0x2C0F, "M", "ⰿ"),
        (0x2C10, "M", "ⱀ"),
        (0x2C11, "M", "ⱁ"),
        (0x2C12, "M", "ⱂ"),
        (0x2C13, "M", "ⱃ"),
        (0x2C14, "M", "ⱄ"),
        (0x2C15, "M", "ⱅ"),
        (0x2C16, "M", "ⱆ"),
        (0x2C17, "M", "ⱇ"),
        (0x2C18, "M", "ⱈ"),
        (0x2C19, "M", "ⱉ"),
        (0x2C1A, "M", "ⱊ"),
        (0x2C1B, "M", "ⱋ"),
        (0x2C1C, "M", "ⱌ"),
        (0x2C1D, "M", "ⱍ"),
        (0x2C1E, "M", "ⱎ"),
        (0x2C1F, "M", "ⱏ"),
        (0x2C20, "M", "ⱐ"),
        (0x2C21, "M", "ⱑ"),
        (0x2C22, "M", "ⱒ"),
        (0x2C23, "M", "ⱓ"),
        (0x2C24, "M", "ⱔ"),
        (0x2C25, "M", "ⱕ"),
        (0x2C26, "M", "ⱖ"),
        (0x2C27, "M", "ⱗ"),
        (0x2C28, "M", "ⱘ"),
        (0x2C29, "M", "ⱙ"),
        (0x2C2A, "M", "ⱚ"),
        (0x2C2B, "M", "ⱛ"),
        (0x2C2C, "M", "ⱜ"),
    ]


def _seg_25() -> List[Union[Tuple[int, str], Tuple[int, str, str]]]:
    return [
        (0x2C2D, "M", "ⱝ"),
        (0x2C2E, "M", "ⱞ"),
        (0x2C2F, "M", "ⱟ"),
        (0x2C30, "V"),
        (0x2C60, "M", "ⱡ"),
        (0x2C61, "V"),
        (0x2C62, "M", "ɫ"),
        (0x2C63, "M", "ᵽ"),
        (0x2C64, "M", "ɽ"),
        (0x2C65, "V"),
        (0x2C67, "M", "ⱨ"),
        (0x2C68, "V"),
        (0x2C69, "M", "ⱪ"),
        (0x2C6A, "V"),
        (0x2C6B, "M", "ⱬ"),
        (0x2C6C, "V"),
        (0x2C6D, "M", "ɑ"),
        (0x2C6E, "M", "ɱ"),
        (0x2C6F, "M", "ɐ"),
        (0x2C70, "M", "ɒ"),
        (0x2C71, "V"),
        (0x2C72, "M", "ⱳ"),
        (0x2C73, "V"),
        (0x2C75, "M", "ⱶ"),
        (0x2C76, "V"),
        (0x2C7C, "M", "j"),
        (0x2C7D, "M", "v"),
        (0x2C7E, "M", "ȿ"),
        (0x2C7F, "M", "ɀ"),
        (0x2C80, "M", "ⲁ"),
        (0x2C81, "V"),
        (0x2C82, "M", "ⲃ"),
        (0x2C83, "V"),
        (0x2C84, "M", "ⲅ"),
        (0x2C85, "V"),
        (0x2C86, "M", "ⲇ"),
        (0x2C87, "V"),
        (0x2C88, "M", "ⲉ"),
        (0x2C89, "V"),
        (0x2C8A, "M", "ⲋ"),
        (0x2C8B, "V"),
        (0x2C8C, "M", "ⲍ"),
        (0x2C8D, "V"),
        (0x2C8E, "M", "ⲏ"),
        (0x2C8F, "V"),
        (0x2C90, "M", "ⲑ"),
        (0x2C91, "V"),
        (0x2C92, "M", "ⲓ"),
        (0x2C93, "V"),
        (0x2C94, "M", "ⲕ"),
        (0x2C95, "V"),
        (0x2C96, "M", "ⲗ"),
        (0x2C97, "V"),
        (0x2C98, "M", "ⲙ"),
        (0x2C99, "V"),
        (0x2C9A, "M", "ⲛ"),
        (0x2C9B, "V"),
        (0x2C9C, "M", "ⲝ"),
        (0x2C9D, "V"),
        (0x2C9E, "M", "ⲟ"),
        (0x2C9F, "V"),
        (0x2CA0, "M", "ⲡ"),
        (0x2CA1, "V"),
        (0x2CA2, "M", "ⲣ"),
        (0x2CA3, "V"),
        (0x2CA4, "M", "ⲥ"),
        (0x2CA5, "V"),
        (0x2CA6, "M", "ⲧ"),
        (0x2CA7, "V"),
        (0x2CA8, "M", "ⲩ"),
        (0x2CA9, "V"),
        (0x2CAA, "M", "ⲫ"),
        (0x2CAB, "V"),
        (0x2CAC, "M", "ⲭ"),
        (0x2CAD, "V"),
        (0x2CAE, "M", "ⲯ"),
        (0x2CAF, "V"),
        (0x2CB0, "M", "ⲱ"),
        (0x2CB1, "V"),
        (0x2CB2, "M", "ⲳ"),
        (0x2CB3, "V"),
        (0x2CB4, "M", "ⲵ"),
        (0x2CB5, "V"),
        (0x2CB6, "M", "ⲷ"),
        (0x2CB7, "V"),
        (0x2CB8, "M", "ⲹ"),
        (0x2CB9, "V"),
        (0x2CBA, "M", "ⲻ"),
        (0x2CBB, "V"),
        (0x2CBC, "M", "ⲽ"),
        (0x2CBD, "V"),
        (0x2CBE, "M", "ⲿ"),
        (0x2CBF, "V"),
        (0x2CC0, "M", "ⳁ"),
        (0x2CC1, "V"),
        (0x2CC2, "M", "ⳃ"),
        (0x2CC3, "V"),
        (0x2CC4, "M", "ⳅ"),
        (0x2CC5, "V"),
        (0x2CC6, "M", "ⳇ"),
    ]


def _seg_26() -> List[Union[Tuple[int, str], Tuple[int, str, str]]]:
    return [
        (0x2CC7, "V"),
        (0x2CC8, "M", "ⳉ"),
        (0x2CC9, "V"),
        (0x2CCA, "M", "ⳋ"),
        (0x2CCB, "V"),
        (0x2CCC, "M", "ⳍ"),
        (0x2CCD, "V"),
        (0x2CCE, "M", "ⳏ"),
        (0x2CCF, "V"),
        (0x2CD0, "M", "ⳑ"),
        (0x2CD1, "V"),
        (0x2CD2, "M", "ⳓ"),
        (0x2CD3, "V"),
        (0x2CD4, "M", "ⳕ"),
        (0x2CD5, "V"),
        (0x2CD6, "M", "ⳗ"),
        (0x2CD7, "V"),
        (0x2CD8, "M", "ⳙ"),
        (0x2CD9, "V"),
        (0x2CDA, "M", "ⳛ"),
        (0x2CDB, "V"),
        (0x2CDC, "M", "ⳝ"),
        (0x2CDD, "V"),
        (0x2CDE, "M", "ⳟ"),
        (0x2CDF, "V"),
        (0x2CE0, "M", "ⳡ"),
        (0x2CE1, "V"),
        (0x2CE2, "M", "ⳣ"),
        (0x2CE3, "V"),
        (0x2CEB, "M", "ⳬ"),
        (0x2CEC, "V"),
        (0x2CED, "M", "ⳮ"),
        (0x2CEE, "V"),
        (0x2CF2, "M", "ⳳ"),
        (0x2CF3, "V"),
        (0x2CF4, "X"),
        (0x2CF9, "V"),
        (0x2D26, "X"),
        (0x2D27, "V"),
        (0x2D28, "X"),
        (0x2D2D, "V"),
        (0x2D2E, "X"),
        (0x2D30, "V"),
        (0x2D68, "X"),
        (0x2D6F, "M", "ⵡ"),
        (0x2D70, "V"),
        (0x2D71, "X"),
        (0x2D7F, "V"),
        (0x2D97, "X"),
        (0x2DA0, "V"),
        (0x2DA7, "X"),
        (0x2DA8, "V"),
        (0x2DAF, "X"),
        (0x2DB0, "V"),
        (0x2DB7, "X"),
        (0x2DB8, "V"),
        (0x2DBF, "X"),
        (0x2DC0, "V"),
        (0x2DC7, "X"),
        (0x2DC8, "V"),
        (0x2DCF, "X"),
        (0x2DD0, "V"),
        (0x2DD7, "X"),
        (0x2DD8, "V"),
        (0x2DDF, "X"),
        (0x2DE0, "V"),
        (0x2E5E, "X"),
        (0x2E80, "V"),
        (0x2E9A, "X"),
        (0x2E9B, "V"),
        (0x2E9F, "M", "母"),
        (0x2EA0, "V"),
        (0x2EF3, "M", "龟"),
        (0x2EF4, "X"),
        (0x2F00, "M", "一"),
        (0x2F01, "M", "丨"),
        (0x2F02, "M", "丶"),
        (0x2F03, "M", "丿"),
        (0x2F04, "M", "乙"),
        (0x2F05, "M", "亅"),
        (0x2F06, "M", "二"),
        (0x2F07, "M", "亠"),
        (0x2F08, "M", "人"),
        (0x2F09, "M", "儿"),
        (0x2F0A, "M", "入"),
        (0x2F0B, "M", "八"),
        (0x2F0C, "M", "冂"),
        (0x2F0D, "M", "冖"),
        (0x2F0E, "M", "冫"),
        (0x2F0F, "M", "几"),
        (0x2F10, "M", "凵"),
        (0x2F11, "M", "刀"),
        (0x2F12, "M", "力"),
        (0x2F13, "M", "勹"),
        (0x2F14, "M", "匕"),
        (0x2F15, "M", "匚"),
        (0x2F16, "M", "匸"),
        (0x2F17, "M", "十"),
        (0x2F18, "M", "卜"),
        (0x2F19, "M", "卩"),
    ]


def _seg_27() -> List[Union[Tuple[int, str], Tuple[int, str, str]]]:
    return [
        (0x2F1A, "M", "厂"),
        (0x2F1B, "M", "厶"),
        (0x2F1C, "M", "又"),
        (0x2F1D, "M", "口"),
        (0x2F1E, "M", "囗"),
        (0x2F1F, "M", "土"),
        (0x2F20, "M", "士"),
        (0x2F21, "M", "夂"),
        (0x2F22, "M", "夊"),
        (0x2F23, "M", "夕"),
        (0x2F24, "M", "大"),
        (0x2F25, "M", "女"),
        (0x2F26, "M", "子"),
        (0x2F27, "M", "宀"),
        (0x2F28, "M", "寸"),
        (0x2F29, "M", "小"),
        (0x2F2A, "M", "尢"),
        (0x2F2B, "M", "尸"),
        (0x2F2C, "M", "屮"),
        (0x2F2D, "M", "山"),
        (0x2F2E, "M", "巛"),
        (0x2F2F, "M", "工"),
        (0x2F30, "M", "己"),
        (0x2F31, "M", "巾"),
        (0x2F32, "M", "干"),
        (0x2F33, "M", "幺"),
        (0x2F34, "M", "广"),
        (0x2F35, "M", "廴"),
        (0x2F36, "M", "廾"),
        (0x2F37, "M", "弋"),
        (0x2F38, "M", "弓"),
        (0x2F39, "M", "彐"),
        (0x2F3A, "M", "彡"),
        (0x2F3B, "M", "彳"),
        (0x2F3C, "M", "心"),
        (0x2F3D, "M", "戈"),
        (0x2F3E, "M", "戶"),
        (0x2F3F, "M", "手"),
        (0x2F40, "M", "支"),
        (0x2F41, "M", "攴"),
        (0x2F42, "M", "文"),
        (0x2F43, "M", "斗"),
        (0x2F44, "M", "斤"),
        (0x2F45, "M", "方"),
        (0x2F46, "M", "无"),
        (0x2F47, "M", "日"),
        (0x2F48, "M", "曰"),
        (0x2F49, "M", "月"),
        (0x2F4A, "M", "木"),
        (0x2F4B, "M", "欠"),
        (0x2F4C, "M", "止"),
        (0x2F4D, "M", "歹"),
        (0x2F4E, "M", "殳"),
        (0x2F4F, "M", "毋"),
        (0x2F50, "M", "比"),
        (0x2F51, "M", "毛"),
        (0x2F52, "M", "氏"),
        (0x2F53, "M", "气"),
        (0x2F54, "M", "水"),
        (0x2F55, "M", "火"),
        (0x2F56, "M", "爪"),
        (0x2F57, "M", "父"),
        (0x2F58, "M", "爻"),
        (0x2F59, "M", "爿"),
        (0x2F5A, "M", "片"),
        (0x2F5B, "M", "牙"),
        (0x2F5C, "M", "牛"),
        (0x2F5D, "M", "犬"),
        (0x2F5E, "M", "玄"),
        (0x2F5F, "M", "玉"),
        (0x2F60, "M", "瓜"),
        (0x2F61, "M", "瓦"),
        (0x2F62, "M", "甘"),
        (0x2F63, "M", "生"),
        (0x2F64, "M", "用"),
        (0x2F65, "M", "田"),
        (0x2F66, "M", "疋"),
        (0x2F67, "M", "疒"),
        (0x2F68, "M", "癶"),
        (0x2F69, "M", "白"),
        (0x2F6A, "M", "皮"),
        (0x2F6B, "M", "皿"),
        (0x2F6C, "M", "目"),
        (0x2F6D, "M", "矛"),
        (0x2F6E, "M", "矢"),
        (0x2F6F, "M", "石"),
        (0x2F70, "M", "示"),
        (0x2F71, "M", "禸"),
        (0x2F72, "M", "禾"),
        (0x2F73, "M", "穴"),
        (0x2F74, "M", "立"),
        (0x2F75, "M", "竹"),
        (0x2F76, "M", "米"),
        (0x2F77, "M", "糸"),
        (0x2F78, "M", "缶"),
        (0x2F79, "M", "网"),
        (0x2F7A, "M", "羊"),
        (0x2F7B, "M", "羽"),
        (0x2F7C, "M", "老"),
        (0x2F7D, "M", "而"),
    ]


def _seg_28() -> List[Union[Tuple[int, str], Tuple[int, str, str]]]:
    return [
        (0x2F7E, "M", "耒"),
        (0x2F7F, "M", "耳"),
        (0x2F80, "M", "聿"),
        (0x2F81, "M", "肉"),
        (0x2F82, "M", "臣"),
        (0x2F83, "M", "自"),
        (0x2F84, "M", "至"),
        (0x2F85, "M", "臼"),
        (0x2F86, "M", "舌"),
        (0x2F87, "M", "舛"),
        (0x2F88, "M", "舟"),
        (0x2F89, "M", "艮"),
        (0x2F8A, "M", "色"),
        (0x2F8B, "M", "艸"),
        (0x2F8C, "M", "虍"),
        (0x2F8D, "M", "虫"),
        (0x2F8E, "M", "血"),
        (0x2F8F, "M", "行"),
        (0x2F90, "M", "衣"),
        (0x2F91, "M", "襾"),
        (0x2F92, "M", "見"),
        (0x2F93, "M", "角"),
        (0x2F94, "M", "言"),
        (0x2F95, "M", "谷"),
        (0x2F96, "M", "豆"),
        (0x2F97, "M", "豕"),
        (0x2F98, "M", "豸"),
        (0x2F99, "M", "貝"),
        (0x2F9A, "M", "赤"),
        (0x2F9B, "M", "走"),
        (0x2F9C, "M", "足"),
        (0x2F9D, "M", "身"),
        (0x2F9E, "M", "車"),
        (0x2F9F, "M", "辛"),
        (0x2FA0, "M", "辰"),
        (0x2FA1, "M", "辵"),
        (0x2FA2, "M", "邑"),
        (0x2FA3, "M", "酉"),
        (0x2FA4, "M", "釆"),
        (0x2FA5, "M", "里"),
        (0x2FA6, "M", "金"),
        (0x2FA7, "M", "長"),
        (0x2FA8, "M", "門"),
        (0x2FA9, "M", "阜"),
        (0x2FAA, "M", "隶"),
        (0x2FAB, "M", "隹"),
        (0x2FAC, "M", "雨"),
        (0x2FAD, "M", "靑"),
        (0x2FAE, "M", "非"),
        (0x2FAF, "M", "面"),
        (0x2FB0, "M", "革"),
        (0x2FB1, "M", "韋"),
        (0x2FB2, "M", "韭"),
        (0x2FB3, "M", "音"),
        (0x2FB4, "M", "頁"),
        (0x2FB5, "M", "風"),
        (0x2FB6, "M", "飛"),
        (0x2FB7, "M", "食"),
        (0x2FB8, "M", "首"),
        (0x2FB9, "M", "香"),
        (0x2FBA, "M", "馬"),
        (0x2FBB, "M", "骨"),
        (0x2FBC, "M", "高"),
        (0x2FBD, "M", "髟"),
        (0x2FBE, "M", "鬥"),
        (0x2FBF, "M", "鬯"),
        (0x2FC0, "M", "鬲"),
        (0x2FC1, "M", "鬼"),
        (0x2FC2, "M", "魚"),
        (0x2FC3, "M", "鳥"),
        (0x2FC4, "M", "鹵"),
        (0x2FC5, "M", "鹿"),
        (0x2FC6, "M", "麥"),
        (0x2FC7, "M", "麻"),
        (0x2FC8, "M", "黃"),
        (0x2FC9, "M", "黍"),
        (0x2FCA, "M", "黑"),
        (0x2FCB, "M", "黹"),
        (0x2FCC, "M", "黽"),
        (0x2FCD, "M", "鼎"),
        (0x2FCE, "M", "鼓"),
        (0x2FCF, "M", "鼠"),
        (0x2FD0, "M", "鼻"),
        (0x2FD1, "M", "齊"),
        (0x2FD2, "M", "齒"),
        (0x2FD3, "M", "龍"),
        (0x2FD4, "M", "龜"),
        (0x2FD5, "M", "龠"),
        (0x2FD6, "X"),
        (0x3000, "3", " "),
        (0x3001, "V"),
        (0x3002, "M", "."),
        (0x3003, "V"),
        (0x3036, "M", "〒"),
        (0x3037, "V"),
        (0x3038, "M", "十"),
        (0x3039, "M", "卄"),
        (0x303A, "M", "卅"),
        (0x303B, "V"),
        (0x3040, "X"),
    ]


def _seg_29() -> List[Union[Tuple[int, str], Tuple[int, str, str]]]:
    return [
        (0x3041, "V"),
        (0x3097, "X"),
        (0x3099, "V"),
        (0x309B, "3", " ゙"),
        (0x309C, "3", " ゚"),
        (0x309D, "V"),
        (0x309F, "M", "より"),
        (0x30A0, "V"),
        (0x30FF, "M", "コト"),
        (0x3100, "X"),
        (0x3105, "V"),
        (0x3130, "X"),
        (0x3131, "M", "ᄀ"),
        (0x3132, "M", "ᄁ"),
        (0x3133, "M", "ᆪ"),
        (0x3134, "M", "ᄂ"),
        (0x3135, "M", "ᆬ"),
        (0x3136, "M", "ᆭ"),
        (0x3137, "M", "ᄃ"),
        (0x3138, "M", "ᄄ"),
        (0x3139, "M", "ᄅ"),
        (0x313A, "M", "ᆰ"),
        (0x313B, "M", "ᆱ"),
        (0x313C, "M", "ᆲ"),
        (0x313D, "M", "ᆳ"),
        (0x313E, "M", "ᆴ"),
        (0x313F, "M", "ᆵ"),
        (0x3140, "M", "ᄚ"),
        (0x3141, "M", "ᄆ"),
        (0x3142, "M", "ᄇ"),
        (0x3143, "M", "ᄈ"),
        (0x3144, "M", "ᄡ"),
        (0x3145, "M", "ᄉ"),
        (0x3146, "M", "ᄊ"),
        (0x3147, "M", "ᄋ"),
        (0x3148, "M", "ᄌ"),
        (0x3149, "M", "ᄍ"),
        (0x314A, "M", "ᄎ"),
        (0x314B, "M", "ᄏ"),
        (0x314C, "M", "ᄐ"),
        (0x314D, "M", "ᄑ"),
        (0x314E, "M", "ᄒ"),
        (0x314F, "M", "ᅡ"),
        (0x3150, "M", "ᅢ"),
        (0x3151, "M", "ᅣ"),
        (0x3152, "M", "ᅤ"),
        (0x3153, "M", "ᅥ"),
        (0x3154, "M", "ᅦ"),
        (0x3155, "M", "ᅧ"),
        (0x3156, "M", "ᅨ"),
        (0x3157, "M", "ᅩ"),
        (0x3158, "M", "ᅪ"),
        (0x3159, "M", "ᅫ"),
        (0x315A, "M", "ᅬ"),
        (0x315B, "M", "ᅭ"),
        (0x315C, "M", "ᅮ"),
        (0x315D, "M", "ᅯ"),
        (0x315E, "M", "ᅰ"),
        (0x315F, "M", "ᅱ"),
        (0x3160, "M", "ᅲ"),
        (0x3161, "M", "ᅳ"),
        (0x3162, "M", "ᅴ"),
        (0x3163, "M", "ᅵ"),
        (0x3164, "X"),
        (0x3165, "M", "ᄔ"),
        (0x3166, "M", "ᄕ"),
        (0x3167, "M", "ᇇ"),
        (0x3168, "M", "ᇈ"),
        (0x3169, "M", "ᇌ"),
        (0x316A, "M", "ᇎ"),
        (0x316B, "M", "ᇓ"),
        (0x316C, "M", "ᇗ"),
        (0x316D, "M", "ᇙ"),
        (0x316E, "M", "ᄜ"),
        (0x316F, "M", "ᇝ"),
        (0x3170, "M", "ᇟ"),
        (0x3171, "M", "ᄝ"),
        (0x3172, "M", "ᄞ"),
        (0x3173, "M", "ᄠ"),
        (0x3174, "M", "ᄢ"),
        (0x3175, "M", "ᄣ"),
        (0x3176, "M", "ᄧ"),
        (0x3177, "M", "ᄩ"),
        (0x3178, "M", "ᄫ"),
        (0x3179, "M", "ᄬ"),
        (0x317A, "M", "ᄭ"),
        (0x317B, "M", "ᄮ"),
        (0x317C, "M", "ᄯ"),
        (0x317D, "M", "ᄲ"),
        (0x317E, "M", "ᄶ"),
        (0x317F, "M", "ᅀ"),
        (0x3180, "M", "ᅇ"),
        (0x3181, "M", "ᅌ"),
        (0x3182, "M", "ᇱ"),
        (0x3183, "M", "ᇲ"),
        (0x3184, "M", "ᅗ"),
        (0x3185, "M", "ᅘ"),
        (0x3186, "M", "ᅙ"),
        (0x3187, "M", "ᆄ"),
        (0x3188, "M", "ᆅ"),
    ]


def _seg_30() -> List[Union[Tuple[int, str], Tuple[int, str, str]]]:
    return [
        (0x3189, "M", "ᆈ"),
        (0x318A, "M", "ᆑ"),
        (0x318B, "M", "ᆒ"),
        (0x318C, "M", "ᆔ"),
        (0x318D, "M", "ᆞ"),
        (0x318E, "M", "ᆡ"),
        (0x318F, "X"),
        (0x3190, "V"),
        (0x3192, "M", "一"),
        (0x3193, "M", "二"),
        (0x3194, "M", "三"),
        (0x3195, "M", "四"),
        (0x3196, "M", "上"),
        (0x3197, "M", "中"),
        (0x3198, "M", "下"),
        (0x3199, "M", "甲"),
        (0x319A, "M", "乙"),
        (0x319B, "M", "丙"),
        (0x319C, "M", "丁"),
        (0x319D, "M", "天"),
        (0x319E, "M", "地"),
        (0x319F, "M", "人"),
        (0x31A0, "V"),
        (0x31E4, "X"),
        (0x31F0, "V"),
        (0x3200, "3", "(ᄀ)"),
        (0x3201, "3", "(ᄂ)"),
        (0x3202, "3", "(ᄃ)"),
        (0x3203, "3", "(ᄅ)"),
        (0x3204, "3", "(ᄆ)"),
        (0x3205, "3", "(ᄇ)"),
        (0x3206, "3", "(ᄉ)"),
        (0x3207, "3", "(ᄋ)"),
        (0x3208, "3", "(ᄌ)"),
        (0x3209, "3", "(ᄎ)"),
        (0x320A, "3", "(ᄏ)"),
        (0x320B, "3", "(ᄐ)"),
        (0x320C, "3", "(ᄑ)"),
        (0x320D, "3", "(ᄒ)"),
        (0x320E, "3", "(가)"),
        (0x320F, "3", "(나)"),
        (0x3210, "3", "(다)"),
        (0x3211, "3", "(라)"),
        (0x3212, "3", "(마)"),
        (0x3213, "3", "(바)"),
        (0x3214, "3", "(사)"),
        (0x3215, "3", "(아)"),
        (0x3216, "3", "(자)"),
        (0x3217, "3", "(차)"),
        (0x3218, "3", "(카)"),
        (0x3219, "3", "(타)"),
        (0x321A, "3", "(파)"),
        (0x321B, "3", "(하)"),
        (0x321C, "3", "(주)"),
        (0x321D, "3", "(오전)"),
        (0x321E, "3", "(오후)"),
        (0x321F, "X"),
        (0x3220, "3", "(一)"),
        (0x3221, "3", "(二)"),
        (0x3222, "3", "(三)"),
        (0x3223, "3", "(四)"),
        (0x3224, "3", "(五)"),
        (0x3225, "3", "(六)"),
        (0x3226, "3", "(七)"),
        (0x3227, "3", "(八)"),
        (0x3228, "3", "(九)"),
        (0x3229, "3", "(十)"),
        (0x322A, "3", "(月)"),
        (0x322B, "3", "(火)"),
        (0x322C, "3", "(水)"),
        (0x322D, "3", "(木)"),
        (0x322E, "3", "(金)"),
        (0x322F, "3", "(土)"),
        (0x3230, "3", "(日)"),
        (0x3231, "3", "(株)"),
        (0x3232, "3", "(有)"),
        (0x3233, "3", "(社)"),
        (0x3234, "3", "(名)"),
        (0x3235, "3", "(特)"),
        (0x3236, "3", "(財)"),
        (0x3237, "3", "(祝)"),
        (0x3238, "3", "(労)"),
        (0x3239, "3", "(代)"),
        (0x323A, "3", "(呼)"),
        (0x323B, "3", "(学)"),
        (0x323C, "3", "(監)"),
        (0x323D, "3", "(企)"),
        (0x323E, "3", "(資)"),
        (0x323F, "3", "(協)"),
        (0x3240, "3", "(祭)"),
        (0x3241, "3", "(休)"),
        (0x3242, "3", "(自)"),
        (0x3243, "3", "(至)"),
        (0x3244, "M", "問"),
        (0x3245, "M", "幼"),
        (0x3246, "M", "文"),
        (0x3247, "M", "箏"),
        (0x3248, "V"),
        (0x3250, "M", "pte"),
        (0x3251, "M", "21"),
    ]


def _seg_31() -> List[Union[Tuple[int, str], Tuple[int, str, str]]]:
    return [
        (0x3252, "M", "22"),
        (0x3253, "M", "23"),
        (0x3254, "M", "24"),
        (0x3255, "M", "25"),
        (0x3256, "M", "26"),
        (0x3257, "M", "27"),
        (0x3258, "M", "28"),
        (0x3259, "M", "29"),
        (0x325A, "M", "30"),
        (0x325B, "M", "31"),
        (0x325C, "M", "32"),
        (0x325D, "M", "33"),
        (0x325E, "M", "34"),
        (0x325F, "M", "35"),
        (0x3260, "M", "ᄀ"),
        (0x3261, "M", "ᄂ"),
        (0x3262, "M", "ᄃ"),
        (0x3263, "M", "ᄅ"),
        (0x3264, "M", "ᄆ"),
        (0x3265, "M", "ᄇ"),
        (0x3266, "M", "ᄉ"),
        (0x3267, "M", "ᄋ"),
        (0x3268, "M", "ᄌ"),
        (0x3269, "M", "ᄎ"),
        (0x326A, "M", "ᄏ"),
        (0x326B, "M", "ᄐ"),
        (0x326C, "M", "ᄑ"),
        (0x326D, "M", "ᄒ"),
        (0x326E, "M", "가"),
        (0x326F, "M", "나"),
        (0x3270, "M", "다"),
        (0x3271, "M", "라"),
        (0x3272, "M", "마"),
        (0x3273, "M", "바"),
        (0x3274, "M", "사"),
        (0x3275, "M", "아"),
        (0x3276, "M", "자"),
        (0x3277, "M", "차"),
        (0x3278, "M", "카"),
        (0x3279, "M", "타"),
        (0x327A, "M", "파"),
        (0x327B, "M", "하"),
        (0x327C, "M", "참고"),
        (0x327D, "M", "주의"),
        (0x327E, "M", "우"),
        (0x327F, "V"),
        (0x3280, "M", "一"),
        (0x3281, "M", "二"),
        (0x3282, "M", "三"),
        (0x3283, "M", "四"),
        (0x3284, "M", "五"),
        (0x3285, "M", "六"),
        (0x3286, "M", "七"),
        (0x3287, "M", "八"),
        (0x3288, "M", "九"),
        (0x3289, "M", "十"),
        (0x328A, "M", "月"),
        (0x328B, "M", "火"),
        (0x328C, "M", "水"),
        (0x328D, "M", "木"),
        (0x328E, "M", "金"),
        (0x328F, "M", "土"),
        (0x3290, "M", "日"),
        (0x3291, "M", "株"),
        (0x3292, "M", "有"),
        (0x3293, "M", "社"),
        (0x3294, "M", "名"),
        (0x3295, "M", "特"),
        (0x3296, "M", "財"),
        (0x3297, "M", "祝"),
        (0x3298, "M", "労"),
        (0x3299, "M", "秘"),
        (0x329A, "M", "男"),
        (0x329B, "M", "女"),
        (0x329C, "M", "適"),
        (0x329D, "M", "優"),
        (0x329E, "M", "印"),
        (0x329F, "M", "注"),
        (0x32A0, "M", "項"),
        (0x32A1, "M", "休"),
        (0x32A2, "M", "写"),
        (0x32A3, "M", "正"),
        (0x32A4, "M", "上"),
        (0x32A5, "M", "中"),
        (0x32A6, "M", "下"),
        (0x32A7, "M", "左"),
        (0x32A8, "M", "右"),
        (0x32A9, "M", "医"),
        (0x32AA, "M", "宗"),
        (0x32AB, "M", "学"),
        (0x32AC, "M", "監"),
        (0x32AD, "M", "企"),
        (0x32AE, "M", "資"),
        (0x32AF, "M", "協"),
        (0x32B0, "M", "夜"),
        (0x32B1, "M", "36"),
        (0x32B2, "M", "37"),
        (0x32B3, "M", "38"),
        (0x32B4, "M", "39"),
        (0x32B5, "M", "40"),
    ]


def _seg_32() -> List[Union[Tuple[int, str], Tuple[int, str, str]]]:
    return [
        (0x32B6, "M", "41"),
        (0x32B7, "M", "42"),
        (0x32B8, "M", "43"),
        (0x32B9, "M", "44"),
        (0x32BA, "M", "45"),
        (0x32BB, "M", "46"),
        (0x32BC, "M", "47"),
        (0x32BD, "M", "48"),
        (0x32BE, "M", "49"),
        (0x32BF, "M", "50"),
        (0x32C0, "M", "1月"),
        (0x32C1, "M", "2月"),
        (0x32C2, "M", "3月"),
        (0x32C3, "M", "4月"),
        (0x32C4, "M", "5月"),
        (0x32C5, "M", "6月"),
        (0x32C6, "M", "7月"),
        (0x32C7, "M", "8月"),
        (0x32C8, "M", "9月"),
        (0x32C9, "M", "10月"),
        (0x32CA, "M", "11月"),
        (0x32CB, "M", "12月"),
        (0x32CC, "M", "hg"),
        (0x32CD, "M", "erg"),
        (0x32CE, "M", "ev"),
        (0x32CF, "M", "ltd"),
        (0x32D0, "M", "ア"),
        (0x32D1, "M", "イ"),
        (0x32D2, "M", "ウ"),
        (0x32D3, "M", "エ"),
        (0x32D4, "M", "オ"),
        (0x32D5, "M", "カ"),
        (0x32D6, "M", "キ"),
        (0x32D7, "M", "ク"),
        (0x32D8, "M", "ケ"),
        (0x32D9, "M", "コ"),
        (0x32DA, "M", "サ"),
        (0x32DB, "M", "シ"),
        (0x32DC, "M", "ス"),
        (0x32DD, "M", "セ"),
        (0x32DE, "M", "ソ"),
        (0x32DF, "M", "タ"),
        (0x32E0, "M", "チ"),
        (0x32E1, "M", "ツ"),
        (0x32E2, "M", "テ"),
        (0x32E3, "M", "ト"),
        (0x32E4, "M", "ナ"),
        (0x32E5, "M", "ニ"),
        (0x32E6, "M", "ヌ"),
        (0x32E7, "M", "ネ"),
        (0x32E8, "M", "ノ"),
        (0x32E9, "M", "ハ"),
        (0x32EA, "M", "ヒ"),
        (0x32EB, "M", "フ"),
        (0x32EC, "M", "ヘ"),
        (0x32ED, "M", "ホ"),
        (0x32EE, "M", "マ"),
        (0x32EF, "M", "ミ"),
        (0x32F0, "M", "ム"),
        (0x32F1, "M", "メ"),
        (0x32F2, "M", "モ"),
        (0x32F3, "M", "ヤ"),
        (0x32F4, "M", "ユ"),
        (0x32F5, "M", "ヨ"),
        (0x32F6, "M", "ラ"),
        (0x32F7, "M", "リ"),
        (0x32F8, "M", "ル"),
        (0x32F9, "M", "レ"),
        (0x32FA, "M", "ロ"),
        (0x32FB, "M", "ワ"),
        (0x32FC, "M", "ヰ"),
        (0x32FD, "M", "ヱ"),
        (0x32FE, "M", "ヲ"),
        (0x32FF, "M", "令和"),
        (0x3300, "M", "アパート"),
        (0x3301, "M", "アルファ"),
        (0x3302, "M", "アンペア"),
        (0x3303, "M", "アール"),
        (0x3304, "M", "イニング"),
        (0x3305, "M", "インチ"),
        (0x3306, "M", "ウォン"),
        (0x3307, "M", "エスクード"),
        (0x3308, "M", "エーカー"),
        (0x3309, "M", "オンス"),
        (0x330A, "M", "オーム"),
        (0x330B, "M", "カイリ"),
        (0x330C, "M", "カラット"),
        (0x330D, "M", "カロリー"),
        (0x330E, "M", "ガロン"),
        (0x330F, "M", "ガンマ"),
        (0x3310, "M", "ギガ"),
        (0x3311, "M", "ギニー"),
        (0x3312, "M", "キュリー"),
        (0x3313, "M", "ギルダー"),
        (0x3314, "M", "キロ"),
        (0x3315, "M", "キログラム"),
        (0x3316, "M", "キロメートル"),
        (0x3317, "M", "キロワット"),
        (0x3318, "M", "グラム"),
        (0x3319, "M", "グラムトン"),
    ]


def _seg_33() -> List[Union[Tuple[int, str], Tuple[int, str, str]]]:
    return [
        (0x331A, "M", "クルゼイロ"),
        (0x331B, "M", "クローネ"),
        (0x331C, "M", "ケース"),
        (0x331D, "M", "コルナ"),
        (0x331E, "M", "コーポ"),
        (0x331F, "M", "サイクル"),
        (0x3320, "M", "サンチーム"),
        (0x3321, "M", "シリング"),
        (0x3322, "M", "センチ"),
        (0x3323, "M", "セント"),
        (0x3324, "M", "ダース"),
        (0x3325, "M", "デシ"),
        (0x3326, "M", "ドル"),
        (0x3327, "M", "トン"),
        (0x3328, "M", "ナノ"),
        (0x3329, "M", "ノット"),
        (0x332A, "M", "ハイツ"),
        (0x332B, "M", "パーセント"),
        (0x332C, "M", "パーツ"),
        (0x332D, "M", "バーレル"),
        (0x332E, "M", "ピアストル"),
        (0x332F, "M", "ピクル"),
        (0x3330, "M", "ピコ"),
        (0x3331, "M", "ビル"),
        (0x3332, "M", "ファラッド"),
        (0x3333, "M", "フィート"),
        (0x3334, "M", "ブッシェル"),
        (0x3335, "M", "フラン"),
        (0x3336, "M", "ヘクタール"),
        (0x3337, "M", "ペソ"),
        (0x3338, "M", "ペニヒ"),
        (0x3339, "M", "ヘルツ"),
        (0x333A, "M", "ペンス"),
        (0x333B, "M", "ページ"),
        (0x333C, "M", "ベータ"),
        (0x333D, "M", "ポイント"),
        (0x333E, "M", "ボルト"),
        (0x333F, "M", "ホン"),
        (0x3340, "M", "ポンド"),
        (0x3341, "M", "ホール"),
        (0x3342, "M", "ホーン"),
        (0x3343, "M", "マイクロ"),
        (0x3344, "M", "マイル"),
        (0x3345, "M", "マッハ"),
        (0x3346, "M", "マルク"),
        (0x3347, "M", "マンション"),
        (0x3348, "M", "ミクロン"),
        (0x3349, "M", "ミリ"),
        (0x334A, "M", "ミリバール"),
        (0x334B, "M", "メガ"),
        (0x334C, "M", "メガトン"),
        (0x334D, "M", "メートル"),
        (0x334E, "M", "ヤード"),
        (0x334F, "M", "ヤール"),
        (0x3350, "M", "ユアン"),
        (0x3351, "M", "リットル"),
        (0x3352, "M", "リラ"),
        (0x3353, "M", "ルピー"),
        (0x3354, "M", "ルーブル"),
        (0x3355, "M", "レム"),
        (0x3356, "M", "レントゲン"),
        (0x3357, "M", "ワット"),
        (0x3358, "M", "0点"),
        (0x3359, "M", "1点"),
        (0x335A, "M", "2点"),
        (0x335B, "M", "3点"),
        (0x335C, "M", "4点"),
        (0x335D, "M", "5点"),
        (0x335E, "M", "6点"),
        (0x335F, "M", "7点"),
        (0x3360, "M", "8点"),
        (0x3361, "M", "9点"),
        (0x3362, "M", "10点"),
        (0x3363, "M", "11点"),
        (0x3364, "M", "12点"),
        (0x3365, "M", "13点"),
        (0x3366, "M", "14点"),
        (0x3367, "M", "15点"),
        (0x3368, "M", "16点"),
        (0x3369, "M", "17点"),
        (0x336A, "M", "18点"),
        (0x336B, "M", "19点"),
        (0x336C, "M", "20点"),
        (0x336D, "M", "21点"),
        (0x336E, "M", "22点"),
        (0x336F, "M", "23点"),
        (0x3370, "M", "24点"),
        (0x3371, "M", "hpa"),
        (0x3372, "M", "da"),
        (0x3373, "M", "au"),
        (0x3374, "M", "bar"),
        (0x3375, "M", "ov"),
        (0x3376, "M", "pc"),
        (0x3377, "M", "dm"),
        (0x3378, "M", "dm2"),
        (0x3379, "M", "dm3"),
        (0x337A, "M", "iu"),
        (0x337B, "M", "平成"),
        (0x337C, "M", "昭和"),
        (0x337D, "M", "大正"),
    ]


def _seg_34() -> List[Union[Tuple[int, str], Tuple[int, str, str]]]:
    return [
        (0x337E, "M", "明治"),
        (0x337F, "M", "株式会社"),
        (0x3380, "M", "pa"),
        (0x3381, "M", "na"),
        (0x3382, "M", "μa"),
        (0x3383, "M", "ma"),
        (0x3384, "M", "ka"),
        (0x3385, "M", "kb"),
        (0x3386, "M", "mb"),
        (0x3387, "M", "gb"),
        (0x3388, "M", "cal"),
        (0x3389, "M", "kcal"),
        (0x338A, "M", "pf"),
        (0x338B, "M", "nf"),
        (0x338C, "M", "μf"),
        (0x338D, "M", "μg"),
        (0x338E, "M", "mg"),
        (0x338F, "M", "kg"),
        (0x3390, "M", "hz"),
        (0x3391, "M", "khz"),
        (0x3392, "M", "mhz"),
        (0x3393, "M", "ghz"),
        (0x3394, "M", "thz"),
        (0x3395, "M", "μl"),
        (0x3396, "M", "ml"),
        (0x3397, "M", "dl"),
        (0x3398, "M", "kl"),
        (0x3399, "M", "fm"),
        (0x339A, "M", "nm"),
        (0x339B, "M", "μm"),
        (0x339C, "M", "mm"),
        (0x339D, "M", "cm"),
        (0x339E, "M", "km"),
        (0x339F, "M", "mm2"),
        (0x33A0, "M", "cm2"),
        (0x33A1, "M", "m2"),
        (0x33A2, "M", "km2"),
        (0x33A3, "M", "mm3"),
        (0x33A4, "M", "cm3"),
        (0x33A5, "M", "m3"),
        (0x33A6, "M", "km3"),
        (0x33A7, "M", "m∕s"),
        (0x33A8, "M", "m∕s2"),
        (0x33A9, "M", "pa"),
        (0x33AA, "M", "kpa"),
        (0x33AB, "M", "mpa"),
        (0x33AC, "M", "gpa"),
        (0x33AD, "M", "rad"),
        (0x33AE, "M", "rad∕s"),
        (0x33AF, "M", "rad∕s2"),
        (0x33B0, "M", "ps"),
        (0x33B1, "M", "ns"),
        (0x33B2, "M", "μs"),
        (0x33B3, "M", "ms"),
        (0x33B4, "M", "pv"),
        (0x33B5, "M", "nv"),
        (0x33B6, "M", "μv"),
        (0x33B7, "M", "mv"),
        (0x33B8, "M", "kv"),
        (0x33B9, "M", "mv"),
        (0x33BA, "M", "pw"),
        (0x33BB, "M", "nw"),
        (0x33BC, "M", "μw"),
        (0x33BD, "M", "mw"),
        (0x33BE, "M", "kw"),
        (0x33BF, "M", "mw"),
        (0x33C0, "M", "kω"),
        (0x33C1, "M", "mω"),
        (0x33C2, "X"),
        (0x33C3, "M", "bq"),
        (0x33C4, "M", "cc"),
        (0x33C5, "M", "cd"),
        (0x33C6, "M", "c∕kg"),
        (0x33C7, "X"),
        (0x33C8, "M", "db"),
        (0x33C9, "M", "gy"),
        (0x33CA, "M", "ha"),
        (0x33CB, "M", "hp"),
        (0x33CC, "M", "in"),
        (0x33CD, "M", "kk"),
        (0x33CE, "M", "km"),
        (0x33CF, "M", "kt"),
        (0x33D0, "M", "lm"),
        (0x33D1, "M", "ln"),
        (0x33D2, "M", "log"),
        (0x33D3, "M", "lx"),
        (0x33D4, "M", "mb"),
        (0x33D5, "M", "mil"),
        (0x33D6, "M", "mol"),
        (0x33D7, "M", "ph"),
        (0x33D8, "X"),
        (0x33D9, "M", "ppm"),
        (0x33DA, "M", "pr"),
        (0x33DB, "M", "sr"),
        (0x33DC, "M", "sv"),
        (0x33DD, "M", "wb"),
        (0x33DE, "M", "v∕m"),
        (0x33DF, "M", "a∕m"),
        (0x33E0, "M", "1日"),
        (0x33E1, "M", "2日"),
    ]


def _seg_35() -> List[Union[Tuple[int, str], Tuple[int, str, str]]]:
    return [
        (0x33E2, "M", "3日"),
        (0x33E3, "M", "4日"),
        (0x33E4, "M", "5日"),
        (0x33E5, "M", "6日"),
        (0x33E6, "M", "7日"),
        (0x33E7, "M", "8日"),
        (0x33E8, "M", "9日"),
        (0x33E9, "M", "10日"),
        (0x33EA, "M", "11日"),
        (0x33EB, "M", "12日"),
        (0x33EC, "M", "13日"),
        (0x33ED, "M", "14日"),
        (0x33EE, "M", "15日"),
        (0x33EF, "M", "16日"),
        (0x33F0, "M", "17日"),
        (0x33F1, "M", "18日"),
        (0x33F2, "M", "19日"),
        (0x33F3, "M", "20日"),
        (0x33F4, "M", "21日"),
        (0x33F5, "M", "22日"),
        (0x33F6, "M", "23日"),
        (0x33F7, "M", "24日"),
        (0x33F8, "M", "25日"),
        (0x33F9, "M", "26日"),
        (0x33FA, "M", "27日"),
        (0x33FB, "M", "28日"),
        (0x33FC, "M", "29日"),
        (0x33FD, "M", "30日"),
        (0x33FE, "M", "31日"),
        (0x33FF, "M", "gal"),
        (0x3400, "V"),
        (0xA48D, "X"),
        (0xA490, "V"),
        (0xA4C7, "X"),
        (0xA4D0, "V"),
        (0xA62C, "X"),
        (0xA640, "M", "ꙁ"),
        (0xA641, "V"),
        (0xA642, "M", "ꙃ"),
        (0xA643, "V"),
        (0xA644, "M", "ꙅ"),
        (0xA645, "V"),
        (0xA646, "M", "ꙇ"),
        (0xA647, "V"),
        (0xA648, "M", "ꙉ"),
        (0xA649, "V"),
        (0xA64A, "M", "ꙋ"),
        (0xA64B, "V"),
        (0xA64C, "M", "ꙍ"),
        (0xA64D, "V"),
        (0xA64E, "M", "ꙏ"),
        (0xA64F, "V"),
        (0xA650, "M", "ꙑ"),
        (0xA651, "V"),
        (0xA652, "M", "ꙓ"),
        (0xA653, "V"),
        (0xA654, "M", "ꙕ"),
        (0xA655, "V"),
        (0xA656, "M", "ꙗ"),
        (0xA657, "V"),
        (0xA658, "M", "ꙙ"),
        (0xA659, "V"),
        (0xA65A, "M", "ꙛ"),
        (0xA65B, "V"),
        (0xA65C, "M", "ꙝ"),
        (0xA65D, "V"),
        (0xA65E, "M", "ꙟ"),
        (0xA65F, "V"),
        (0xA660, "M", "ꙡ"),
        (0xA661, "V"),
        (0xA662, "M", "ꙣ"),
        (0xA663, "V"),
        (0xA664, "M", "ꙥ"),
        (0xA665, "V"),
        (0xA666, "M", "ꙧ"),
        (0xA667, "V"),
        (0xA668, "M", "ꙩ"),
        (0xA669, "V"),
        (0xA66A, "M", "ꙫ"),
        (0xA66B, "V"),
        (0xA66C, "M", "ꙭ"),
        (0xA66D, "V"),
        (0xA680, "M", "ꚁ"),
        (0xA681, "V"),
        (0xA682, "M", "ꚃ"),
        (0xA683, "V"),
        (0xA684, "M", "ꚅ"),
        (0xA685, "V"),
        (0xA686, "M", "ꚇ"),
        (0xA687, "V"),
        (0xA688, "M", "ꚉ"),
        (0xA689, "V"),
        (0xA68A, "M", "ꚋ"),
        (0xA68B, "V"),
        (0xA68C, "M", "ꚍ"),
        (0xA68D, "V"),
        (0xA68E, "M", "ꚏ"),
        (0xA68F, "V"),
        (0xA690, "M", "ꚑ"),
        (0xA691, "V"),
    ]


def _seg_36() -> List[Union[Tuple[int, str], Tuple[int, str, str]]]:
    return [
        (0xA692, "M", "ꚓ"),
        (0xA693, "V"),
        (0xA694, "M", "ꚕ"),
        (0xA695, "V"),
        (0xA696, "M", "ꚗ"),
        (0xA697, "V"),
        (0xA698, "M", "ꚙ"),
        (0xA699, "V"),
        (0xA69A, "M", "ꚛ"),
        (0xA69B, "V"),
        (0xA69C, "M", "ъ"),
        (0xA69D, "M", "ь"),
        (0xA69E, "V"),
        (0xA6F8, "X"),
        (0xA700, "V"),
        (0xA722, "M", "ꜣ"),
        (0xA723, "V"),
        (0xA724, "M", "ꜥ"),
        (0xA725, "V"),
        (0xA726, "M", "ꜧ"),
        (0xA727, "V"),
        (0xA728, "M", "ꜩ"),
        (0xA729, "V"),
        (0xA72A, "M", "ꜫ"),
        (0xA72B, "V"),
        (0xA72C, "M", "ꜭ"),
        (0xA72D, "V"),
        (0xA72E, "M", "ꜯ"),
        (0xA72F, "V"),
        (0xA732, "M", "ꜳ"),
        (0xA733, "V"),
        (0xA734, "M", "ꜵ"),
        (0xA735, "V"),
        (0xA736, "M", "ꜷ"),
        (0xA737, "V"),
        (0xA738, "M", "ꜹ"),
        (0xA739, "V"),
        (0xA73A, "M", "ꜻ"),
        (0xA73B, "V"),
        (0xA73C, "M", "ꜽ"),
        (0xA73D, "V"),
        (0xA73E, "M", "ꜿ"),
        (0xA73F, "V"),
        (0xA740, "M", "ꝁ"),
        (0xA741, "V"),
        (0xA742, "M", "ꝃ"),
        (0xA743, "V"),
        (0xA744, "M", "ꝅ"),
        (0xA745, "V"),
        (0xA746, "M", "ꝇ"),
        (0xA747, "V"),
        (0xA748, "M", "ꝉ"),
        (0xA749, "V"),
        (0xA74A, "M", "ꝋ"),
        (0xA74B, "V"),
        (0xA74C, "M", "ꝍ"),
        (0xA74D, "V"),
        (0xA74E, "M", "ꝏ"),
        (0xA74F, "V"),
        (0xA750, "M", "ꝑ"),
        (0xA751, "V"),
        (0xA752, "M", "ꝓ"),
        (0xA753, "V"),
        (0xA754, "M", "ꝕ"),
        (0xA755, "V"),
        (0xA756, "M", "ꝗ"),
        (0xA757, "V"),
        (0xA758, "M", "ꝙ"),
        (0xA759, "V"),
        (0xA75A, "M", "ꝛ"),
        (0xA75B, "V"),
        (0xA75C, "M", "ꝝ"),
        (0xA75D, "V"),
        (0xA75E, "M", "ꝟ"),
        (0xA75F, "V"),
        (0xA760, "M", "ꝡ"),
        (0xA761, "V"),
        (0xA762, "M", "ꝣ"),
        (0xA763, "V"),
        (0xA764, "M", "ꝥ"),
        (0xA765, "V"),
        (0xA766, "M", "ꝧ"),
        (0xA767, "V"),
        (0xA768, "M", "ꝩ"),
        (0xA769, "V"),
        (0xA76A, "M", "ꝫ"),
        (0xA76B, "V"),
        (0xA76C, "M", "ꝭ"),
        (0xA76D, "V"),
        (0xA76E, "M", "ꝯ"),
        (0xA76F, "V"),
        (0xA770, "M", "ꝯ"),
        (0xA771, "V"),
        (0xA779, "M", "ꝺ"),
        (0xA77A, "V"),
        (0xA77B, "M", "ꝼ"),
        (0xA77C, "V"),
        (0xA77D, "M", "ᵹ"),
        (0xA77E, "M", "ꝿ"),
        (0xA77F, "V"),
    ]


def _seg_37() -> List[Union[Tuple[int, str], Tuple[int, str, str]]]:
    return [
        (0xA780, "M", "ꞁ"),
        (0xA781, "V"),
        (0xA782, "M", "ꞃ"),
        (0xA783, "V"),
        (0xA784, "M", "ꞅ"),
        (0xA785, "V"),
        (0xA786, "M", "ꞇ"),
        (0xA787, "V"),
        (0xA78B, "M", "ꞌ"),
        (0xA78C, "V"),
        (0xA78D, "M", "ɥ"),
        (0xA78E, "V"),
        (0xA790, "M", "ꞑ"),
        (0xA791, "V"),
        (0xA792, "M", "ꞓ"),
        (0xA793, "V"),
        (0xA796, "M", "ꞗ"),
        (0xA797, "V"),
        (0xA798, "M", "ꞙ"),
        (0xA799, "V"),
        (0xA79A, "M", "ꞛ"),
        (0xA79B, "V"),
        (0xA79C, "M", "ꞝ"),
        (0xA79D, "V"),
        (0xA79E, "M", "ꞟ"),
        (0xA79F, "V"),
        (0xA7A0, "M", "ꞡ"),
        (0xA7A1, "V"),
        (0xA7A2, "M", "ꞣ"),
        (0xA7A3, "V"),
        (0xA7A4, "M", "ꞥ"),
        (0xA7A5, "V"),
        (0xA7A6, "M", "ꞧ"),
        (0xA7A7, "V"),
        (0xA7A8, "M", "ꞩ"),
        (0xA7A9, "V"),
        (0xA7AA, "M", "ɦ"),
        (0xA7AB, "M", "ɜ"),
        (0xA7AC, "M", "ɡ"),
        (0xA7AD, "M", "ɬ"),
        (0xA7AE, "M", "ɪ"),
        (0xA7AF, "V"),
        (0xA7B0, "M", "ʞ"),
        (0xA7B1, "M", "ʇ"),
        (0xA7B2, "M", "ʝ"),
        (0xA7B3, "M", "ꭓ"),
        (0xA7B4, "M", "ꞵ"),
        (0xA7B5, "V"),
        (0xA7B6, "M", "ꞷ"),
        (0xA7B7, "V"),
        (0xA7B8, "M", "ꞹ"),
        (0xA7B9, "V"),
        (0xA7BA, "M", "ꞻ"),
        (0xA7BB, "V"),
        (0xA7BC, "M", "ꞽ"),
        (0xA7BD, "V"),
        (0xA7BE, "M", "ꞿ"),
        (0xA7BF, "V"),
        (0xA7C0, "M", "ꟁ"),
        (0xA7C1, "V"),
        (0xA7C2, "M", "ꟃ"),
        (0xA7C3, "V"),
        (0xA7C4, "M", "ꞔ"),
        (0xA7C5, "M", "ʂ"),
        (0xA7C6, "M", "ᶎ"),
        (0xA7C7, "M", "ꟈ"),
        (0xA7C8, "V"),
        (0xA7C9, "M", "ꟊ"),
        (0xA7CA, "V"),
        (0xA7CB, "X"),
        (0xA7D0, "M", "ꟑ"),
        (0xA7D1, "V"),
        (0xA7D2, "X"),
        (0xA7D3, "V"),
        (0xA7D4, "X"),
        (0xA7D5, "V"),
        (0xA7D6, "M", "ꟗ"),
        (0xA7D7, "V"),
        (0xA7D8, "M", "ꟙ"),
        (0xA7D9, "V"),
        (0xA7DA, "X"),
        (0xA7F2, "M", "c"),
        (0xA7F3, "M", "f"),
        (0xA7F4, "M", "q"),
        (0xA7F5, "M", "ꟶ"),
        (0xA7F6, "V"),
        (0xA7F8, "M", "ħ"),
        (0xA7F9, "M", "œ"),
        (0xA7FA, "V"),
        (0xA82D, "X"),
        (0xA830, "V"),
        (0xA83A, "X"),
        (0xA840, "V"),
        (0xA878, "X"),
        (0xA880, "V"),
        (0xA8C6, "X"),
        (0xA8CE, "V"),
        (0xA8DA, "X"),
        (0xA8E0, "V"),
        (0xA954, "X"),
    ]


def _seg_38() -> List[Union[Tuple[int, str], Tuple[int, str, str]]]:
    return [
        (0xA95F, "V"),
        (0xA97D, "X"),
        (0xA980, "V"),
        (0xA9CE, "X"),
        (0xA9CF, "V"),
        (0xA9DA, "X"),
        (0xA9DE, "V"),
        (0xA9FF, "X"),
        (0xAA00, "V"),
        (0xAA37, "X"),
        (0xAA40, "V"),
        (0xAA4E, "X"),
        (0xAA50, "V"),
        (0xAA5A, "X"),
        (0xAA5C, "V"),
        (0xAAC3, "X"),
        (0xAADB, "V"),
        (0xAAF7, "X"),
        (0xAB01, "V"),
        (0xAB07, "X"),
        (0xAB09, "V"),
        (0xAB0F, "X"),
        (0xAB11, "V"),
        (0xAB17, "X"),
        (0xAB20, "V"),
        (0xAB27, "X"),
        (0xAB28, "V"),
        (0xAB2F, "X"),
        (0xAB30, "V"),
        (0xAB5C, "M", "ꜧ"),
        (0xAB5D, "M", "ꬷ"),
        (0xAB5E, "M", "ɫ"),
        (0xAB5F, "M", "ꭒ"),
        (0xAB60, "V"),
        (0xAB69, "M", "ʍ"),
        (0xAB6A, "V"),
        (0xAB6C, "X"),
        (0xAB70, "M", "Ꭰ"),
        (0xAB71, "M", "Ꭱ"),
        (0xAB72, "M", "Ꭲ"),
        (0xAB73, "M", "Ꭳ"),
        (0xAB74, "M", "Ꭴ"),
        (0xAB75, "M", "Ꭵ"),
        (0xAB76, "M", "Ꭶ"),
        (0xAB77, "M", "Ꭷ"),
        (0xAB78, "M", "Ꭸ"),
        (0xAB79, "M", "Ꭹ"),
        (0xAB7A, "M", "Ꭺ"),
        (0xAB7B, "M", "Ꭻ"),
        (0xAB7C, "M", "Ꭼ"),
        (0xAB7D, "M", "Ꭽ"),
        (0xAB7E, "M", "Ꭾ"),
        (0xAB7F, "M", "Ꭿ"),
        (0xAB80, "M", "Ꮀ"),
        (0xAB81, "M", "Ꮁ"),
        (0xAB82, "M", "Ꮂ"),
        (0xAB83, "M", "Ꮃ"),
        (0xAB84, "M", "Ꮄ"),
        (0xAB85, "M", "Ꮅ"),
        (0xAB86, "M", "Ꮆ"),
        (0xAB87, "M", "Ꮇ"),
        (0xAB88, "M", "Ꮈ"),
        (0xAB89, "M", "Ꮉ"),
        (0xAB8A, "M", "Ꮊ"),
        (0xAB8B, "M", "Ꮋ"),
        (0xAB8C, "M", "Ꮌ"),
        (0xAB8D, "M", "Ꮍ"),
        (0xAB8E, "M", "Ꮎ"),
        (0xAB8F, "M", "Ꮏ"),
        (0xAB90, "M", "Ꮐ"),
        (0xAB91, "M", "Ꮑ"),
        (0xAB92, "M", "Ꮒ"),
        (0xAB93, "M", "Ꮓ"),
        (0xAB94, "M", "Ꮔ"),
        (0xAB95, "M", "Ꮕ"),
        (0xAB96, "M", "Ꮖ"),
        (0xAB97, "M", "Ꮗ"),
        (0xAB98, "M", "Ꮘ"),
        (0xAB99, "M", "Ꮙ"),
        (0xAB9A, "M", "Ꮚ"),
        (0xAB9B, "M", "Ꮛ"),
        (0xAB9C, "M", "Ꮜ"),
        (0xAB9D, "M", "Ꮝ"),
        (0xAB9E, "M", "Ꮞ"),
        (0xAB9F, "M", "Ꮟ"),
        (0xABA0, "M", "Ꮠ"),
        (0xABA1, "M", "Ꮡ"),
        (0xABA2, "M", "Ꮢ"),
        (0xABA3, "M", "Ꮣ"),
        (0xABA4, "M", "Ꮤ"),
        (0xABA5, "M", "Ꮥ"),
        (0xABA6, "M", "Ꮦ"),
        (0xABA7, "M", "Ꮧ"),
        (0xABA8, "M", "Ꮨ"),
        (0xABA9, "M", "Ꮩ"),
        (0xABAA, "M", "Ꮪ"),
        (0xABAB, "M", "Ꮫ"),
        (0xABAC, "M", "Ꮬ"),
        (0xABAD, "M", "Ꮭ"),
        (0xABAE, "M", "Ꮮ"),
    ]


def _seg_39() -> List[Union[Tuple[int, str], Tuple[int, str, str]]]:
    return [
        (0xABAF, "M", "Ꮯ"),
        (0xABB0, "M", "Ꮰ"),
        (0xABB1, "M", "Ꮱ"),
        (0xABB2, "M", "Ꮲ"),
        (0xABB3, "M", "Ꮳ"),
        (0xABB4, "M", "Ꮴ"),
        (0xABB5, "M", "Ꮵ"),
        (0xABB6, "M", "Ꮶ"),
        (0xABB7, "M", "Ꮷ"),
        (0xABB8, "M", "Ꮸ"),
        (0xABB9, "M", "Ꮹ"),
        (0xABBA, "M", "Ꮺ"),
        (0xABBB, "M", "Ꮻ"),
        (0xABBC, "M", "Ꮼ"),
        (0xABBD, "M", "Ꮽ"),
        (0xABBE, "M", "Ꮾ"),
        (0xABBF, "M", "Ꮿ"),
        (0xABC0, "V"),
        (0xABEE, "X"),
        (0xABF0, "V"),
        (0xABFA, "X"),
        (0xAC00, "V"),
        (0xD7A4, "X"),
        (0xD7B0, "V"),
        (0xD7C7, "X"),
        (0xD7CB, "V"),
        (0xD7FC, "X"),
        (0xF900, "M", "豈"),
        (0xF901, "M", "更"),
        (0xF902, "M", "車"),
        (0xF903, "M", "賈"),
        (0xF904, "M", "滑"),
        (0xF905, "M", "串"),
        (0xF906, "M", "句"),
        (0xF907, "M", "龜"),
        (0xF909, "M", "契"),
        (0xF90A, "M", "金"),
        (0xF90B, "M", "喇"),
        (0xF90C, "M", "奈"),
        (0xF90D, "M", "懶"),
        (0xF90E, "M", "癩"),
        (0xF90F, "M", "羅"),
        (0xF910, "M", "蘿"),
        (0xF911, "M", "螺"),
        (0xF912, "M", "裸"),
        (0xF913, "M", "邏"),
        (0xF914, "M", "樂"),
        (0xF915, "M", "洛"),
        (0xF916, "M", "烙"),
        (0xF917, "M", "珞"),
        (0xF918, "M", "落"),
        (0xF919, "M", "酪"),
        (0xF91A, "M", "駱"),
        (0xF91B, "M", "亂"),
        (0xF91C, "M", "卵"),
        (0xF91D, "M", "欄"),
        (0xF91E, "M", "爛"),
        (0xF91F, "M", "蘭"),
        (0xF920, "M", "鸞"),
        (0xF921, "M", "嵐"),
        (0xF922, "M", "濫"),
        (0xF923, "M", "藍"),
        (0xF924, "M", "襤"),
        (0xF925, "M", "拉"),
        (0xF926, "M", "臘"),
        (0xF927, "M", "蠟"),
        (0xF928, "M", "廊"),
        (0xF929, "M", "朗"),
        (0xF92A, "M", "浪"),
        (0xF92B, "M", "狼"),
        (0xF92C, "M", "郎"),
        (0xF92D, "M", "來"),
        (0xF92E, "M", "冷"),
        (0xF92F, "M", "勞"),
        (0xF930, "M", "擄"),
        (0xF931, "M", "櫓"),
        (0xF932, "M", "爐"),
        (0xF933, "M", "盧"),
        (0xF934, "M", "老"),
        (0xF935, "M", "蘆"),
        (0xF936, "M", "虜"),
        (0xF937, "M", "路"),
        (0xF938, "M", "露"),
        (0xF939, "M", "魯"),
        (0xF93A, "M", "鷺"),
        (0xF93B, "M", "碌"),
        (0xF93C, "M", "祿"),
        (0xF93D, "M", "綠"),
        (0xF93E, "M", "菉"),
        (0xF93F, "M", "錄"),
        (0xF940, "M", "鹿"),
        (0xF941, "M", "論"),
        (0xF942, "M", "壟"),
        (0xF943, "M", "弄"),
        (0xF944, "M", "籠"),
        (0xF945, "M", "聾"),
        (0xF946, "M", "牢"),
        (0xF947, "M", "磊"),
        (0xF948, "M", "賂"),
        (0xF949, "M", "雷"),
    ]


def _seg_40() -> List[Union[Tuple[int, str], Tuple[int, str, str]]]:
    return [
        (0xF94A, "M", "壘"),
        (0xF94B, "M", "屢"),
        (0xF94C, "M", "樓"),
        (0xF94D, "M", "淚"),
        (0xF94E, "M", "漏"),
        (0xF94F, "M", "累"),
        (0xF950, "M", "縷"),
        (0xF951, "M", "陋"),
        (0xF952, "M", "勒"),
        (0xF953, "M", "肋"),
        (0xF954, "M", "凜"),
        (0xF955, "M", "凌"),
        (0xF956, "M", "稜"),
        (0xF957, "M", "綾"),
        (0xF958, "M", "菱"),
        (0xF959, "M", "陵"),
        (0xF95A, "M", "讀"),
        (0xF95B, "M", "拏"),
        (0xF95C, "M", "樂"),
        (0xF95D, "M", "諾"),
        (0xF95E, "M", "丹"),
        (0xF95F, "M", "寧"),
        (0xF960, "M", "怒"),
        (0xF961, "M", "率"),
        (0xF962, "M", "異"),
        (0xF963, "M", "北"),
        (0xF964, "M", "磻"),
        (0xF965, "M", "便"),
        (0xF966, "M", "復"),
        (0xF967, "M", "不"),
        (0xF968, "M", "泌"),
        (0xF969, "M", "數"),
        (0xF96A, "M", "索"),
        (0xF96B, "M", "參"),
        (0xF96C, "M", "塞"),
        (0xF96D, "M", "省"),
        (0xF96E, "M", "葉"),
        (0xF96F, "M", "說"),
        (0xF970, "M", "殺"),
        (0xF971, "M", "辰"),
        (0xF972, "M", "沈"),
        (0xF973, "M", "拾"),
        (0xF974, "M", "若"),
        (0xF975, "M", "掠"),
        (0xF976, "M", "略"),
        (0xF977, "M", "亮"),
        (0xF978, "M", "兩"),
        (0xF979, "M", "凉"),
        (0xF97A, "M", "梁"),
        (0xF97B, "M", "糧"),
        (0xF97C, "M", "良"),
        (0xF97D, "M", "諒"),
        (0xF97E, "M", "量"),
        (0xF97F, "M", "勵"),
        (0xF980, "M", "呂"),
        (0xF981, "M", "女"),
        (0xF982, "M", "廬"),
        (0xF983, "M", "旅"),
        (0xF984, "M", "濾"),
        (0xF985, "M", "礪"),
        (0xF986, "M", "閭"),
        (0xF987, "M", "驪"),
        (0xF988, "M", "麗"),
        (0xF989, "M", "黎"),
        (0xF98A, "M", "力"),
        (0xF98B, "M", "曆"),
        (0xF98C, "M", "歷"),
        (0xF98D, "M", "轢"),
        (0xF98E, "M", "年"),
        (0xF98F, "M", "憐"),
        (0xF990, "M", "戀"),
        (0xF991, "M", "撚"),
        (0xF992, "M", "漣"),
        (0xF993, "M", "煉"),
        (0xF994, "M", "璉"),
        (0xF995, "M", "秊"),
        (0xF996, "M", "練"),
        (0xF997, "M", "聯"),
        (0xF998, "M", "輦"),
        (0xF999, "M", "蓮"),
        (0xF99A, "M", "連"),
        (0xF99B, "M", "鍊"),
        (0xF99C, "M", "列"),
        (0xF99D, "M", "劣"),
        (0xF99E, "M", "咽"),
        (0xF99F, "M", "烈"),
        (0xF9A0, "M", "裂"),
        (0xF9A1, "M", "說"),
        (0xF9A2, "M", "廉"),
        (0xF9A3, "M", "念"),
        (0xF9A4, "M", "捻"),
        (0xF9A5, "M", "殮"),
        (0xF9A6, "M", "簾"),
        (0xF9A7, "M", "獵"),
        (0xF9A8, "M", "令"),
        (0xF9A9, "M", "囹"),
        (0xF9AA, "M", "寧"),
        (0xF9AB, "M", "嶺"),
        (0xF9AC, "M", "怜"),
        (0xF9AD, "M", "玲"),
    ]


def _seg_41() -> List[Union[Tuple[int, str], Tuple[int, str, str]]]:
    return [
        (0xF9AE, "M", "瑩"),
        (0xF9AF, "M", "羚"),
        (0xF9B0, "M", "聆"),
        (0xF9B1, "M", "鈴"),
        (0xF9B2, "M", "零"),
        (0xF9B3, "M", "靈"),
        (0xF9B4, "M", "領"),
        (0xF9B5, "M", "例"),
        (0xF9B6, "M", "禮"),
        (0xF9B7, "M", "醴"),
        (0xF9B8, "M", "隸"),
        (0xF9B9, "M", "惡"),
        (0xF9BA, "M", "了"),
        (0xF9BB, "M", "僚"),
        (0xF9BC, "M", "寮"),
        (0xF9BD, "M", "尿"),
        (0xF9BE, "M", "料"),
        (0xF9BF, "M", "樂"),
        (0xF9C0, "M", "燎"),
        (0xF9C1, "M", "療"),
        (0xF9C2, "M", "蓼"),
        (0xF9C3, "M", "遼"),
        (0xF9C4, "M", "龍"),
        (0xF9C5, "M", "暈"),
        (0xF9C6, "M", "阮"),
        (0xF9C7, "M", "劉"),
        (0xF9C8, "M", "杻"),
        (0xF9C9, "M", "柳"),
        (0xF9CA, "M", "流"),
        (0xF9CB, "M", "溜"),
        (0xF9CC, "M", "琉"),
        (0xF9CD, "M", "留"),
        (0xF9CE, "M", "硫"),
        (0xF9CF, "M", "紐"),
        (0xF9D0, "M", "類"),
        (0xF9D1, "M", "六"),
        (0xF9D2, "M", "戮"),
        (0xF9D3, "M", "陸"),
        (0xF9D4, "M", "倫"),
        (0xF9D5, "M", "崙"),
        (0xF9D6, "M", "淪"),
        (0xF9D7, "M", "輪"),
        (0xF9D8, "M", "律"),
        (0xF9D9, "M", "慄"),
        (0xF9DA, "M", "栗"),
        (0xF9DB, "M", "率"),
        (0xF9DC, "M", "隆"),
        (0xF9DD, "M", "利"),
        (0xF9DE, "M", "吏"),
        (0xF9DF, "M", "履"),
        (0xF9E0, "M", "易"),
        (0xF9E1, "M", "李"),
        (0xF9E2, "M", "梨"),
        (0xF9E3, "M", "泥"),
        (0xF9E4, "M", "理"),
        (0xF9E5, "M", "痢"),
        (0xF9E6, "M", "罹"),
        (0xF9E7, "M", "裏"),
        (0xF9E8, "M", "裡"),
        (0xF9E9, "M", "里"),
        (0xF9EA, "M", "離"),
        (0xF9EB, "M", "匿"),
        (0xF9EC, "M", "溺"),
        (0xF9ED, "M", "吝"),
        (0xF9EE, "M", "燐"),
        (0xF9EF, "M", "璘"),
        (0xF9F0, "M", "藺"),
        (0xF9F1, "M", "隣"),
        (0xF9F2, "M", "鱗"),
        (0xF9F3, "M", "麟"),
        (0xF9F4, "M", "林"),
        (0xF9F5, "M", "淋"),
        (0xF9F6, "M", "臨"),
        (0xF9F7, "M", "立"),
        (0xF9F8, "M", "笠"),
        (0xF9F9, "M", "粒"),
        (0xF9FA, "M", "狀"),
        (0xF9FB, "M", "炙"),
        (0xF9FC, "M", "識"),
        (0xF9FD, "M", "什"),
        (0xF9FE, "M", "茶"),
        (0xF9FF, "M", "刺"),
        (0xFA00, "M", "切"),
        (0xFA01, "M", "度"),
        (0xFA02, "M", "拓"),
        (0xFA03, "M", "糖"),
        (0xFA04, "M", "宅"),
        (0xFA05, "M", "洞"),
        (0xFA06, "M", "暴"),
        (0xFA07, "M", "輻"),
        (0xFA08, "M", "行"),
        (0xFA09, "M", "降"),
        (0xFA0A, "M", "見"),
        (0xFA0B, "M", "廓"),
        (0xFA0C, "M", "兀"),
        (0xFA0D, "M", "嗀"),
        (0xFA0E, "V"),
        (0xFA10, "M", "塚"),
        (0xFA11, "V"),
        (0xFA12, "M", "晴"),
    ]


def _seg_42() -> List[Union[Tuple[int, str], Tuple[int, str, str]]]:
    return [
        (0xFA13, "V"),
        (0xFA15, "M", "凞"),
        (0xFA16, "M", "猪"),
        (0xFA17, "M", "益"),
        (0xFA18, "M", "礼"),
        (0xFA19, "M", "神"),
        (0xFA1A, "M", "祥"),
        (0xFA1B, "M", "福"),
        (0xFA1C, "M", "靖"),
        (0xFA1D, "M", "精"),
        (0xFA1E, "M", "羽"),
        (0xFA1F, "V"),
        (0xFA20, "M", "蘒"),
        (0xFA21, "V"),
        (0xFA22, "M", "諸"),
        (0xFA23, "V"),
        (0xFA25, "M", "逸"),
        (0xFA26, "M", "都"),
        (0xFA27, "V"),
        (0xFA2A, "M", "飯"),
        (0xFA2B, "M", "飼"),
        (0xFA2C, "M", "館"),
        (0xFA2D, "M", "鶴"),
        (0xFA2E, "M", "郞"),
        (0xFA2F, "M", "隷"),
        (0xFA30, "M", "侮"),
        (0xFA31, "M", "僧"),
        (0xFA32, "M", "免"),
        (0xFA33, "M", "勉"),
        (0xFA34, "M", "勤"),
        (0xFA35, "M", "卑"),
        (0xFA36, "M", "喝"),
        (0xFA37, "M", "嘆"),
        (0xFA38, "M", "器"),
        (0xFA39, "M", "塀"),
        (0xFA3A, "M", "墨"),
        (0xFA3B, "M", "層"),
        (0xFA3C, "M", "屮"),
        (0xFA3D, "M", "悔"),
        (0xFA3E, "M", "慨"),
        (0xFA3F, "M", "憎"),
        (0xFA40, "M", "懲"),
        (0xFA41, "M", "敏"),
        (0xFA42, "M", "既"),
        (0xFA43, "M", "暑"),
        (0xFA44, "M", "梅"),
        (0xFA45, "M", "海"),
        (0xFA46, "M", "渚"),
        (0xFA47, "M", "漢"),
        (0xFA48, "M", "煮"),
        (0xFA49, "M", "爫"),
        (0xFA4A, "M", "琢"),
        (0xFA4B, "M", "碑"),
        (0xFA4C, "M", "社"),
        (0xFA4D, "M", "祉"),
        (0xFA4E, "M", "祈"),
        (0xFA4F, "M", "祐"),
        (0xFA50, "M", "祖"),
        (0xFA51, "M", "祝"),
        (0xFA52, "M", "禍"),
        (0xFA53, "M", "禎"),
        (0xFA54, "M", "穀"),
        (0xFA55, "M", "突"),
        (0xFA56, "M", "節"),
        (0xFA57, "M", "練"),
        (0xFA58, "M", "縉"),
        (0xFA59, "M", "繁"),
        (0xFA5A, "M", "署"),
        (0xFA5B, "M", "者"),
        (0xFA5C, "M", "臭"),
        (0xFA5D, "M", "艹"),
        (0xFA5F, "M", "著"),
        (0xFA60, "M", "褐"),
        (0xFA61, "M", "視"),
        (0xFA62, "M", "謁"),
        (0xFA63, "M", "謹"),
        (0xFA64, "M", "賓"),
        (0xFA65, "M", "贈"),
        (0xFA66, "M", "辶"),
        (0xFA67, "M", "逸"),
        (0xFA68, "M", "難"),
        (0xFA69, "M", "響"),
        (0xFA6A, "M", "頻"),
        (0xFA6B, "M", "恵"),
        (0xFA6C, "M", "𤋮"),
        (0xFA6D, "M", "舘"),
        (0xFA6E, "X"),
        (0xFA70, "M", "並"),
        (0xFA71, "M", "况"),
        (0xFA72, "M", "全"),
        (0xFA73, "M", "侀"),
        (0xFA74, "M", "充"),
        (0xFA75, "M", "冀"),
        (0xFA76, "M", "勇"),
        (0xFA77, "M", "勺"),
        (0xFA78, "M", "喝"),
        (0xFA79, "M", "啕"),
        (0xFA7A, "M", "喙"),
        (0xFA7B, "M", "嗢"),
        (0xFA7C, "M", "塚"),
    ]


def _seg_43() -> List[Union[Tuple[int, str], Tuple[int, str, str]]]:
    return [
        (0xFA7D, "M", "墳"),
        (0xFA7E, "M", "奄"),
        (0xFA7F, "M", "奔"),
        (0xFA80, "M", "婢"),
        (0xFA81, "M", "嬨"),
        (0xFA82, "M", "廒"),
        (0xFA83, "M", "廙"),
        (0xFA84, "M", "彩"),
        (0xFA85, "M", "徭"),
        (0xFA86, "M", "惘"),
        (0xFA87, "M", "慎"),
        (0xFA88, "M", "愈"),
        (0xFA89, "M", "憎"),
        (0xFA8A, "M", "慠"),
        (0xFA8B, "M", "懲"),
        (0xFA8C, "M", "戴"),
        (0xFA8D, "M", "揄"),
        (0xFA8E, "M", "搜"),
        (0xFA8F, "M", "摒"),
        (0xFA90, "M", "敖"),
        (0xFA91, "M", "晴"),
        (0xFA92, "M", "朗"),
        (0xFA93, "M", "望"),
        (0xFA94, "M", "杖"),
        (0xFA95, "M", "歹"),
        (0xFA96, "M", "殺"),
        (0xFA97, "M", "流"),
        (0xFA98, "M", "滛"),
        (0xFA99, "M", "滋"),
        (0xFA9A, "M", "漢"),
        (0xFA9B, "M", "瀞"),
        (0xFA9C, "M", "煮"),
        (0xFA9D, "M", "瞧"),
        (0xFA9E, "M", "爵"),
        (0xFA9F, "M", "犯"),
        (0xFAA0, "M", "猪"),
        (0xFAA1, "M", "瑱"),
        (0xFAA2, "M", "甆"),
        (0xFAA3, "M", "画"),
        (0xFAA4, "M", "瘝"),
        (0xFAA5, "M", "瘟"),
        (0xFAA6, "M", "益"),
        (0xFAA7, "M", "盛"),
        (0xFAA8, "M", "直"),
        (0xFAA9, "M", "睊"),
        (0xFAAA, "M", "着"),
        (0xFAAB, "M", "磌"),
        (0xFAAC, "M", "窱"),
        (0xFAAD, "M", "節"),
        (0xFAAE, "M", "类"),
        (0xFAAF, "M", "絛"),
        (0xFAB0, "M", "練"),
        (0xFAB1, "M", "缾"),
        (0xFAB2, "M", "者"),
        (0xFAB3, "M", "荒"),
        (0xFAB4, "M", "華"),
        (0xFAB5, "M", "蝹"),
        (0xFAB6, "M", "襁"),
        (0xFAB7, "M", "覆"),
        (0xFAB8, "M", "視"),
        (0xFAB9, "M", "調"),
        (0xFABA, "M", "諸"),
        (0xFABB, "M", "請"),
        (0xFABC, "M", "謁"),
        (0xFABD, "M", "諾"),
        (0xFABE, "M", "諭"),
        (0xFABF, "M", "謹"),
        (0xFAC0, "M", "變"),
        (0xFAC1, "M", "贈"),
        (0xFAC2, "M", "輸"),
        (0xFAC3, "M", "遲"),
        (0xFAC4, "M", "醙"),
        (0xFAC5, "M", "鉶"),
        (0xFAC6, "M", "陼"),
        (0xFAC7, "M", "難"),
        (0xFAC8, "M", "靖"),
        (0xFAC9, "M", "韛"),
        (0xFACA, "M", "響"),
        (0xFACB, "M", "頋"),
        (0xFACC, "M", "頻"),
        (0xFACD, "M", "鬒"),
        (0xFACE, "M", "龜"),
        (0xFACF, "M", "𢡊"),
        (0xFAD0, "M", "𢡄"),
        (0xFAD1, "M", "𣏕"),
        (0xFAD2, "M", "㮝"),
        (0xFAD3, "M", "䀘"),
        (0xFAD4, "M", "䀹"),
        (0xFAD5, "M", "𥉉"),
        (0xFAD6, "M", "𥳐"),
        (0xFAD7, "M", "𧻓"),
        (0xFAD8, "M", "齃"),
        (0xFAD9, "M", "龎"),
        (0xFADA, "X"),
        (0xFB00, "M", "ff"),
        (0xFB01, "M", "fi"),
        (0xFB02, "M", "fl"),
        (0xFB03, "M", "ffi"),
        (0xFB04, "M", "ffl"),
        (0xFB05, "M", "st"),
    ]


def _seg_44() -> List[Union[Tuple[int, str], Tuple[int, str, str]]]:
    return [
        (0xFB07, "X"),
        (0xFB13, "M", "մն"),
        (0xFB14, "M", "մե"),
        (0xFB15, "M", "մի"),
        (0xFB16, "M", "վն"),
        (0xFB17, "M", "մխ"),
        (0xFB18, "X"),
        (0xFB1D, "M", "יִ"),
        (0xFB1E, "V"),
        (0xFB1F, "M", "ײַ"),
        (0xFB20, "M", "ע"),
        (0xFB21, "M", "א"),
        (0xFB22, "M", "ד"),
        (0xFB23, "M", "ה"),
        (0xFB24, "M", "כ"),
        (0xFB25, "M", "ל"),
        (0xFB26, "M", "ם"),
        (0xFB27, "M", "ר"),
        (0xFB28, "M", "ת"),
        (0xFB29, "3", "+"),
        (0xFB2A, "M", "שׁ"),
        (0xFB2B, "M", "שׂ"),
        (0xFB2C, "M", "שּׁ"),
        (0xFB2D, "M", "שּׂ"),
        (0xFB2E, "M", "אַ"),
        (0xFB2F, "M", "אָ"),
        (0xFB30, "M", "אּ"),
        (0xFB31, "M", "בּ"),
        (0xFB32, "M", "גּ"),
        (0xFB33, "M", "דּ"),
        (0xFB34, "M", "הּ"),
        (0xFB35, "M", "וּ"),
        (0xFB36, "M", "זּ"),
        (0xFB37, "X"),
        (0xFB38, "M", "טּ"),
        (0xFB39, "M", "יּ"),
        (0xFB3A, "M", "ךּ"),
        (0xFB3B, "M", "כּ"),
        (0xFB3C, "M", "לּ"),
        (0xFB3D, "X"),
        (0xFB3E, "M", "מּ"),
        (0xFB3F, "X"),
        (0xFB40, "M", "נּ"),
        (0xFB41, "M", "סּ"),
        (0xFB42, "X"),
        (0xFB43, "M", "ףּ"),
        (0xFB44, "M", "פּ"),
        (0xFB45, "X"),
        (0xFB46, "M", "צּ"),
        (0xFB47, "M", "קּ"),
        (0xFB48, "M", "רּ"),
        (0xFB49, "M", "שּ"),
        (0xFB4A, "M", "תּ"),
        (0xFB4B, "M", "וֹ"),
        (0xFB4C, "M", "בֿ"),
        (0xFB4D, "M", "כֿ"),
        (0xFB4E, "M", "פֿ"),
        (0xFB4F, "M", "אל"),
        (0xFB50, "M", "ٱ"),
        (0xFB52, "M", "ٻ"),
        (0xFB56, "M", "پ"),
        (0xFB5A, "M", "ڀ"),
        (0xFB5E, "M", "ٺ"),
        (0xFB62, "M", "ٿ"),
        (0xFB66, "M", "ٹ"),
        (0xFB6A, "M", "ڤ"),
        (0xFB6E, "M", "ڦ"),
        (0xFB72, "M", "ڄ"),
        (0xFB76, "M", "ڃ"),
        (0xFB7A, "M", "چ"),
        (0xFB7E, "M", "ڇ"),
        (0xFB82, "M", "ڍ"),
        (0xFB84, "M", "ڌ"),
        (0xFB86, "M", "ڎ"),
        (0xFB88, "M", "ڈ"),
        (0xFB8A, "M", "ژ"),
        (0xFB8C, "M", "ڑ"),
        (0xFB8E, "M", "ک"),
        (0xFB92, "M", "گ"),
        (0xFB96, "M", "ڳ"),
        (0xFB9A, "M", "ڱ"),
        (0xFB9E, "M", "ں"),
        (0xFBA0, "M", "ڻ"),
        (0xFBA4, "M", "ۀ"),
        (0xFBA6, "M", "ہ"),
        (0xFBAA, "M", "ھ"),
        (0xFBAE, "M", "ے"),
        (0xFBB0, "M", "ۓ"),
        (0xFBB2, "V"),
        (0xFBC3, "X"),
        (0xFBD3, "M", "ڭ"),
        (0xFBD7, "M", "ۇ"),
        (0xFBD9, "M", "ۆ"),
        (0xFBDB, "M", "ۈ"),
        (0xFBDD, "M", "ۇٴ"),
        (0xFBDE, "M", "ۋ"),
        (0xFBE0, "M", "ۅ"),
        (0xFBE2, "M", "ۉ"),
        (0xFBE4, "M", "ې"),
        (0xFBE8, "M", "ى"),
    ]


def _seg_45() -> List[Union[Tuple[int, str], Tuple[int, str, str]]]:
    return [
        (0xFBEA, "M", "ئا"),
        (0xFBEC, "M", "ئە"),
        (0xFBEE, "M", "ئو"),
        (0xFBF0, "M", "ئۇ"),
        (0xFBF2, "M", "ئۆ"),
        (0xFBF4, "M", "ئۈ"),
        (0xFBF6, "M", "ئې"),
        (0xFBF9, "M", "ئى"),
        (0xFBFC, "M", "ی"),
        (0xFC00, "M", "ئج"),
        (0xFC01, "M", "ئح"),
        (0xFC02, "M", "ئم"),
        (0xFC03, "M", "ئى"),
        (0xFC04, "M", "ئي"),
        (0xFC05, "M", "بج"),
        (0xFC06, "M", "بح"),
        (0xFC07, "M", "بخ"),
        (0xFC08, "M", "بم"),
        (0xFC09, "M", "بى"),
        (0xFC0A, "M", "بي"),
        (0xFC0B, "M", "تج"),
        (0xFC0C, "M", "تح"),
        (0xFC0D, "M", "تخ"),
        (0xFC0E, "M", "تم"),
        (0xFC0F, "M", "تى"),
        (0xFC10, "M", "تي"),
        (0xFC11, "M", "ثج"),
        (0xFC12, "M", "ثم"),
        (0xFC13, "M", "ثى"),
        (0xFC14, "M", "ثي"),
        (0xFC15, "M", "جح"),
        (0xFC16, "M", "جم"),
        (0xFC17, "M", "حج"),
        (0xFC18, "M", "حم"),
        (0xFC19, "M", "خج"),
        (0xFC1A, "M", "خح"),
        (0xFC1B, "M", "خم"),
        (0xFC1C, "M", "سج"),
        (0xFC1D, "M", "سح"),
        (0xFC1E, "M", "سخ"),
        (0xFC1F, "M", "سم"),
        (0xFC20, "M", "صح"),
        (0xFC21, "M", "صم"),
        (0xFC22, "M", "ضج"),
        (0xFC23, "M", "ضح"),
        (0xFC24, "M", "ضخ"),
        (0xFC25, "M", "ضم"),
        (0xFC26, "M", "طح"),
        (0xFC27, "M", "طم"),
        (0xFC28, "M", "ظم"),
        (0xFC29, "M", "عج"),
        (0xFC2A, "M", "عم"),
        (0xFC2B, "M", "غج"),
        (0xFC2C, "M", "غم"),
        (0xFC2D, "M", "فج"),
        (0xFC2E, "M", "فح"),
        (0xFC2F, "M", "فخ"),
        (0xFC30, "M", "فم"),
        (0xFC31, "M", "فى"),
        (0xFC32, "M", "في"),
        (0xFC33, "M", "قح"),
        (0xFC34, "M", "قم"),
        (0xFC35, "M", "قى"),
        (0xFC36, "M", "قي"),
        (0xFC37, "M", "كا"),
        (0xFC38, "M", "كج"),
        (0xFC39, "M", "كح"),
        (0xFC3A, "M", "كخ"),
        (0xFC3B, "M", "كل"),
        (0xFC3C, "M", "كم"),
        (0xFC3D, "M", "كى"),
        (0xFC3E, "M", "كي"),
        (0xFC3F, "M", "لج"),
        (0xFC40, "M", "لح"),
        (0xFC41, "M", "لخ"),
        (0xFC42, "M", "لم"),
        (0xFC43, "M", "لى"),
        (0xFC44, "M", "لي"),
        (0xFC45, "M", "مج"),
        (0xFC46, "M", "مح"),
        (0xFC47, "M", "مخ"),
        (0xFC48, "M", "مم"),
        (0xFC49, "M", "مى"),
        (0xFC4A, "M", "مي"),
        (0xFC4B, "M", "نج"),
        (0xFC4C, "M", "نح"),
        (0xFC4D, "M", "نخ"),
        (0xFC4E, "M", "نم"),
        (0xFC4F, "M", "نى"),
        (0xFC50, "M", "ني"),
        (0xFC51, "M", "هج"),
        (0xFC52, "M", "هم"),
        (0xFC53, "M", "هى"),
        (0xFC54, "M", "هي"),
        (0xFC55, "M", "يج"),
        (0xFC56, "M", "يح"),
        (0xFC57, "M", "يخ"),
        (0xFC58, "M", "يم"),
        (0xFC59, "M", "يى"),
        (0xFC5A, "M", "يي"),
    ]


def _seg_46() -> List[Union[Tuple[int, str], Tuple[int, str, str]]]:
    return [
        (0xFC5B, "M", "ذٰ"),
        (0xFC5C, "M", "رٰ"),
        (0xFC5D, "M", "ىٰ"),
        (0xFC5E, "3", " ٌّ"),
        (0xFC5F, "3", " ٍّ"),
        (0xFC60, "3", " َّ"),
        (0xFC61, "3", " ُّ"),
        (0xFC62, "3", " ِّ"),
        (0xFC63, "3", " ّٰ"),
        (0xFC64, "M", "ئر"),
        (0xFC65, "M", "ئز"),
        (0xFC66, "M", "ئم"),
        (0xFC67, "M", "ئن"),
        (0xFC68, "M", "ئى"),
        (0xFC69, "M", "ئي"),
        (0xFC6A, "M", "بر"),
        (0xFC6B, "M", "بز"),
        (0xFC6C, "M", "بم"),
        (0xFC6D, "M", "بن"),
        (0xFC6E, "M", "بى"),
        (0xFC6F, "M", "بي"),
        (0xFC70, "M", "تر"),
        (0xFC71, "M", "تز"),
        (0xFC72, "M", "تم"),
        (0xFC73, "M", "تن"),
        (0xFC74, "M", "تى"),
        (0xFC75, "M", "تي"),
        (0xFC76, "M", "ثر"),
        (0xFC77, "M", "ثز"),
        (0xFC78, "M", "ثم"),
        (0xFC79, "M", "ثن"),
        (0xFC7A, "M", "ثى"),
        (0xFC7B, "M", "ثي"),
        (0xFC7C, "M", "فى"),
        (0xFC7D, "M", "في"),
        (0xFC7E, "M", "قى"),
        (0xFC7F, "M", "قي"),
        (0xFC80, "M", "كا"),
        (0xFC81, "M", "كل"),
        (0xFC82, "M", "كم"),
        (0xFC83, "M", "كى"),
        (0xFC84, "M", "كي"),
        (0xFC85, "M", "لم"),
        (0xFC86, "M", "لى"),
        (0xFC87, "M", "لي"),
        (0xFC88, "M", "ما"),
        (0xFC89, "M", "مم"),
        (0xFC8A, "M", "نر"),
        (0xFC8B, "M", "نز"),
        (0xFC8C, "M", "نم"),
        (0xFC8D, "M", "نن"),
        (0xFC8E, "M", "نى"),
        (0xFC8F, "M", "ني"),
        (0xFC90, "M", "ىٰ"),
        (0xFC91, "M", "ير"),
        (0xFC92, "M", "يز"),
        (0xFC93, "M", "يم"),
        (0xFC94, "M", "ين"),
        (0xFC95, "M", "يى"),
        (0xFC96, "M", "يي"),
        (0xFC97, "M", "ئج"),
        (0xFC98, "M", "ئح"),
        (0xFC99, "M", "ئخ"),
        (0xFC9A, "M", "ئم"),
        (0xFC9B, "M", "ئه"),
        (0xFC9C, "M", "بج"),
        (0xFC9D, "M", "بح"),
        (0xFC9E, "M", "بخ"),
        (0xFC9F, "M", "بم"),
        (0xFCA0, "M", "به"),
        (0xFCA1, "M", "تج"),
        (0xFCA2, "M", "تح"),
        (0xFCA3, "M", "تخ"),
        (0xFCA4, "M", "تم"),
        (0xFCA5, "M", "ته"),
        (0xFCA6, "M", "ثم"),
        (0xFCA7, "M", "جح"),
        (0xFCA8, "M", "جم"),
        (0xFCA9, "M", "حج"),
        (0xFCAA, "M", "حم"),
        (0xFCAB, "M", "خج"),
        (0xFCAC, "M", "خم"),
        (0xFCAD, "M", "سج"),
        (0xFCAE, "M", "سح"),
        (0xFCAF, "M", "سخ"),
        (0xFCB0, "M", "سم"),
        (0xFCB1, "M", "صح"),
        (0xFCB2, "M", "صخ"),
        (0xFCB3, "M", "صم"),
        (0xFCB4, "M", "ضج"),
        (0xFCB5, "M", "ضح"),
        (0xFCB6, "M", "ضخ"),
        (0xFCB7, "M", "ضم"),
        (0xFCB8, "M", "طح"),
        (0xFCB9, "M", "ظم"),
        (0xFCBA, "M", "عج"),
        (0xFCBB, "M", "عم"),
        (0xFCBC, "M", "غج"),
        (0xFCBD, "M", "غم"),
        (0xFCBE, "M", "فج"),
    ]


def _seg_47() -> List[Union[Tuple[int, str], Tuple[int, str, str]]]:
    return [
        (0xFCBF, "M", "فح"),
        (0xFCC0, "M", "فخ"),
        (0xFCC1, "M", "فم"),
        (0xFCC2, "M", "قح"),
        (0xFCC3, "M", "قم"),
        (0xFCC4, "M", "كج"),
        (0xFCC5, "M", "كح"),
        (0xFCC6, "M", "كخ"),
        (0xFCC7, "M", "كل"),
        (0xFCC8, "M", "كم"),
        (0xFCC9, "M", "لج"),
        (0xFCCA, "M", "لح"),
        (0xFCCB, "M", "لخ"),
        (0xFCCC, "M", "لم"),
        (0xFCCD, "M", "له"),
        (0xFCCE, "M", "مج"),
        (0xFCCF, "M", "مح"),
        (0xFCD0, "M", "مخ"),
        (0xFCD1, "M", "مم"),
        (0xFCD2, "M", "نج"),
        (0xFCD3, "M", "نح"),
        (0xFCD4, "M", "نخ"),
        (0xFCD5, "M", "نم"),
        (0xFCD6, "M", "نه"),
        (0xFCD7, "M", "هج"),
        (0xFCD8, "M", "هم"),
        (0xFCD9, "M", "هٰ"),
        (0xFCDA, "M", "يج"),
        (0xFCDB, "M", "يح"),
        (0xFCDC, "M", "يخ"),
        (0xFCDD, "M", "يم"),
        (0xFCDE, "M", "يه"),
        (0xFCDF, "M", "ئم"),
        (0xFCE0, "M", "ئه"),
        (0xFCE1, "M", "بم"),
        (0xFCE2, "M", "به"),
        (0xFCE3, "M", "تم"),
        (0xFCE4, "M", "ته"),
        (0xFCE5, "M", "ثم"),
        (0xFCE6, "M", "ثه"),
        (0xFCE7, "M", "سم"),
        (0xFCE8, "M", "سه"),
        (0xFCE9, "M", "شم"),
        (0xFCEA, "M", "شه"),
        (0xFCEB, "M", "كل"),
        (0xFCEC, "M", "كم"),
        (0xFCED, "M", "لم"),
        (0xFCEE, "M", "نم"),
        (0xFCEF, "M", "نه"),
        (0xFCF0, "M", "يم"),
        (0xFCF1, "M", "يه"),
        (0xFCF2, "M", "ـَّ"),
        (0xFCF3, "M", "ـُّ"),
        (0xFCF4, "M", "ـِّ"),
        (0xFCF5, "M", "طى"),
        (0xFCF6, "M", "طي"),
        (0xFCF7, "M", "عى"),
        (0xFCF8, "M", "عي"),
        (0xFCF9, "M", "غى"),
        (0xFCFA, "M", "غي"),
        (0xFCFB, "M", "سى"),
        (0xFCFC, "M", "سي"),
        (0xFCFD, "M", "شى"),
        (0xFCFE, "M", "شي"),
        (0xFCFF, "M", "حى"),
        (0xFD00, "M", "حي"),
        (0xFD01, "M", "جى"),
        (0xFD02, "M", "جي"),
        (0xFD03, "M", "خى"),
        (0xFD04, "M", "خي"),
        (0xFD05, "M", "صى"),
        (0xFD06, "M", "صي"),
        (0xFD07, "M", "ضى"),
        (0xFD08, "M", "ضي"),
        (0xFD09, "M", "شج"),
        (0xFD0A, "M", "شح"),
        (0xFD0B, "M", "شخ"),
        (0xFD0C, "M", "شم"),
        (0xFD0D, "M", "شر"),
        (0xFD0E, "M", "سر"),
        (0xFD0F, "M", "صر"),
        (0xFD10, "M", "ضر"),
        (0xFD11, "M", "طى"),
        (0xFD12, "M", "طي"),
        (0xFD13, "M", "عى"),
        (0xFD14, "M", "عي"),
        (0xFD15, "M", "غى"),
        (0xFD16, "M", "غي"),
        (0xFD17, "M", "سى"),
        (0xFD18, "M", "سي"),
        (0xFD19, "M", "شى"),
        (0xFD1A, "M", "شي"),
        (0xFD1B, "M", "حى"),
        (0xFD1C, "M", "حي"),
        (0xFD1D, "M", "جى"),
        (0xFD1E, "M", "جي"),
        (0xFD1F, "M", "خى"),
        (0xFD20, "M", "خي"),
        (0xFD21, "M", "صى"),
        (0xFD22, "M", "صي"),
    ]


def _seg_48() -> List[Union[Tuple[int, str], Tuple[int, str, str]]]:
    return [
        (0xFD23, "M", "ضى"),
        (0xFD24, "M", "ضي"),
        (0xFD25, "M", "شج"),
        (0xFD26, "M", "شح"),
        (0xFD27, "M", "شخ"),
        (0xFD28, "M", "شم"),
        (0xFD29, "M", "شر"),
        (0xFD2A, "M", "سر"),
        (0xFD2B, "M", "صر"),
        (0xFD2C, "M", "ضر"),
        (0xFD2D, "M", "شج"),
        (0xFD2E, "M", "شح"),
        (0xFD2F, "M", "شخ"),
        (0xFD30, "M", "شم"),
        (0xFD31, "M", "سه"),
        (0xFD32, "M", "شه"),
        (0xFD33, "M", "طم"),
        (0xFD34, "M", "سج"),
        (0xFD35, "M", "سح"),
        (0xFD36, "M", "سخ"),
        (0xFD37, "M", "شج"),
        (0xFD38, "M", "شح"),
        (0xFD39, "M", "شخ"),
        (0xFD3A, "M", "طم"),
        (0xFD3B, "M", "ظم"),
        (0xFD3C, "M", "اً"),
        (0xFD3E, "V"),
        (0xFD50, "M", "تجم"),
        (0xFD51, "M", "تحج"),
        (0xFD53, "M", "تحم"),
        (0xFD54, "M", "تخم"),
        (0xFD55, "M", "تمج"),
        (0xFD56, "M", "تمح"),
        (0xFD57, "M", "تمخ"),
        (0xFD58, "M", "جمح"),
        (0xFD5A, "M", "حمي"),
        (0xFD5B, "M", "حمى"),
        (0xFD5C, "M", "سحج"),
        (0xFD5D, "M", "سجح"),
        (0xFD5E, "M", "سجى"),
        (0xFD5F, "M", "سمح"),
        (0xFD61, "M", "سمج"),
        (0xFD62, "M", "سمم"),
        (0xFD64, "M", "صحح"),
        (0xFD66, "M", "صمم"),
        (0xFD67, "M", "شحم"),
        (0xFD69, "M", "شجي"),
        (0xFD6A, "M", "شمخ"),
        (0xFD6C, "M", "شمم"),
        (0xFD6E, "M", "ضحى"),
        (0xFD6F, "M", "ضخم"),
        (0xFD71, "M", "طمح"),
        (0xFD73, "M", "طمم"),
        (0xFD74, "M", "طمي"),
        (0xFD75, "M", "عجم"),
        (0xFD76, "M", "عمم"),
        (0xFD78, "M", "عمى"),
        (0xFD79, "M", "غمم"),
        (0xFD7A, "M", "غمي"),
        (0xFD7B, "M", "غمى"),
        (0xFD7C, "M", "فخم"),
        (0xFD7E, "M", "قمح"),
        (0xFD7F, "M", "قمم"),
        (0xFD80, "M", "لحم"),
        (0xFD81, "M", "لحي"),
        (0xFD82, "M", "لحى"),
        (0xFD83, "M", "لجج"),
        (0xFD85, "M", "لخم"),
        (0xFD87, "M", "لمح"),
        (0xFD89, "M", "محج"),
        (0xFD8A, "M", "محم"),
        (0xFD8B, "M", "محي"),
        (0xFD8C, "M", "مجح"),
        (0xFD8D, "M", "مجم"),
        (0xFD8E, "M", "مخج"),
        (0xFD8F, "M", "مخم"),
        (0xFD90, "X"),
        (0xFD92, "M", "مجخ"),
        (0xFD93, "M", "همج"),
        (0xFD94, "M", "همم"),
        (0xFD95, "M", "نحم"),
        (0xFD96, "M", "نحى"),
        (0xFD97, "M", "نجم"),
        (0xFD99, "M", "نجى"),
        (0xFD9A, "M", "نمي"),
        (0xFD9B, "M", "نمى"),
        (0xFD9C, "M", "يمم"),
        (0xFD9E, "M", "بخي"),
        (0xFD9F, "M", "تجي"),
        (0xFDA0, "M", "تجى"),
        (0xFDA1, "M", "تخي"),
        (0xFDA2, "M", "تخى"),
        (0xFDA3, "M", "تمي"),
        (0xFDA4, "M", "تمى"),
        (0xFDA5, "M", "جمي"),
        (0xFDA6, "M", "جحى"),
        (0xFDA7, "M", "جمى"),
        (0xFDA8, "M", "سخى"),
        (0xFDA9, "M", "صحي"),
        (0xFDAA, "M", "شحي"),
    ]


def _seg_49() -> List[Union[Tuple[int, str], Tuple[int, str, str]]]:
    return [
        (0xFDAB, "M", "ضحي"),
        (0xFDAC, "M", "لجي"),
        (0xFDAD, "M", "لمي"),
        (0xFDAE, "M", "يحي"),
        (0xFDAF, "M", "يجي"),
        (0xFDB0, "M", "يمي"),
        (0xFDB1, "M", "ممي"),
        (0xFDB2, "M", "قمي"),
        (0xFDB3, "M", "نحي"),
        (0xFDB4, "M", "قمح"),
        (0xFDB5, "M", "لحم"),
        (0xFDB6, "M", "عمي"),
        (0xFDB7, "M", "كمي"),
        (0xFDB8, "M", "نجح"),
        (0xFDB9, "M", "مخي"),
        (0xFDBA, "M", "لجم"),
        (0xFDBB, "M", "كمم"),
        (0xFDBC, "M", "لجم"),
        (0xFDBD, "M", "نجح"),
        (0xFDBE, "M", "جحي"),
        (0xFDBF, "M", "حجي"),
        (0xFDC0, "M", "مجي"),
        (0xFDC1, "M", "فمي"),
        (0xFDC2, "M", "بحي"),
        (0xFDC3, "M", "كمم"),
        (0xFDC4, "M", "عجم"),
        (0xFDC5, "M", "صمم"),
        (0xFDC6, "M", "سخي"),
        (0xFDC7, "M", "نجي"),
        (0xFDC8, "X"),
        (0xFDCF, "V"),
        (0xFDD0, "X"),
        (0xFDF0, "M", "صلے"),
        (0xFDF1, "M", "قلے"),
        (0xFDF2, "M", "الله"),
        (0xFDF3, "M", "اكبر"),
        (0xFDF4, "M", "محمد"),
        (0xFDF5, "M", "صلعم"),
        (0xFDF6, "M", "رسول"),
        (0xFDF7, "M", "عليه"),
        (0xFDF8, "M", "وسلم"),
        (0xFDF9, "M", "صلى"),
        (0xFDFA, "3", "صلى الله عليه وسلم"),
        (0xFDFB, "3", "جل جلاله"),
        (0xFDFC, "M", "ریال"),
        (0xFDFD, "V"),
        (0xFE00, "I"),
        (0xFE10, "3", ","),
        (0xFE11, "M", "、"),
        (0xFE12, "X"),
        (0xFE13, "3", ":"),
        (0xFE14, "3", ";"),
        (0xFE15, "3", "!"),
        (0xFE16, "3", "?"),
        (0xFE17, "M", "〖"),
        (0xFE18, "M", "〗"),
        (0xFE19, "X"),
        (0xFE20, "V"),
        (0xFE30, "X"),
        (0xFE31, "M", "—"),
        (0xFE32, "M", "–"),
        (0xFE33, "3", "_"),
        (0xFE35, "3", "("),
        (0xFE36, "3", ")"),
        (0xFE37, "3", "{"),
        (0xFE38, "3", "}"),
        (0xFE39, "M", "〔"),
        (0xFE3A, "M", "〕"),
        (0xFE3B, "M", "【"),
        (0xFE3C, "M", "】"),
        (0xFE3D, "M", "《"),
        (0xFE3E, "M", "》"),
        (0xFE3F, "M", "〈"),
        (0xFE40, "M", "〉"),
        (0xFE41, "M", "「"),
        (0xFE42, "M", "」"),
        (0xFE43, "M", "『"),
        (0xFE44, "M", "』"),
        (0xFE45, "V"),
        (0xFE47, "3", "["),
        (0xFE48, "3", "]"),
        (0xFE49, "3", " ̅"),
        (0xFE4D, "3", "_"),
        (0xFE50, "3", ","),
        (0xFE51, "M", "、"),
        (0xFE52, "X"),
        (0xFE54, "3", ";"),
        (0xFE55, "3", ":"),
        (0xFE56, "3", "?"),
        (0xFE57, "3", "!"),
        (0xFE58, "M", "—"),
        (0xFE59, "3", "("),
        (0xFE5A, "3", ")"),
        (0xFE5B, "3", "{"),
        (0xFE5C, "3", "}"),
        (0xFE5D, "M", "〔"),
        (0xFE5E, "M", "〕"),
        (0xFE5F, "3", "#"),
        (0xFE60, "3", "&"),
        (0xFE61, "3", "*"),
    ]


def _seg_50() -> List[Union[Tuple[int, str], Tuple[int, str, str]]]:
    return [
        (0xFE62, "3", "+"),
        (0xFE63, "M", "-"),
        (0xFE64, "3", "<"),
        (0xFE65, "3", ">"),
        (0xFE66, "3", "="),
        (0xFE67, "X"),
        (0xFE68, "3", "\\"),
        (0xFE69, "3", "$"),
        (0xFE6A, "3", "%"),
        (0xFE6B, "3", "@"),
        (0xFE6C, "X"),
        (0xFE70, "3", " ً"),
        (0xFE71, "M", "ـً"),
        (0xFE72, "3", " ٌ"),
        (0xFE73, "V"),
        (0xFE74, "3", " ٍ"),
        (0xFE75, "X"),
        (0xFE76, "3", " َ"),
        (0xFE77, "M", "ـَ"),
        (0xFE78, "3", " ُ"),
        (0xFE79, "M", "ـُ"),
        (0xFE7A, "3", " ِ"),
        (0xFE7B, "M", "ـِ"),
        (0xFE7C, "3", " ّ"),
        (0xFE7D, "M", "ـّ"),
        (0xFE7E, "3", " ْ"),
        (0xFE7F, "M", "ـْ"),
        (0xFE80, "M", "ء"),
        (0xFE81, "M", "آ"),
        (0xFE83, "M", "أ"),
        (0xFE85, "M", "ؤ"),
        (0xFE87, "M", "إ"),
        (0xFE89, "M", "ئ"),
        (0xFE8D, "M", "ا"),
        (0xFE8F, "M", "ب"),
        (0xFE93, "M", "ة"),
        (0xFE95, "M", "ت"),
        (0xFE99, "M", "ث"),
        (0xFE9D, "M", "ج"),
        (0xFEA1, "M", "ح"),
        (0xFEA5, "M", "خ"),
        (0xFEA9, "M", "د"),
        (0xFEAB, "M", "ذ"),
        (0xFEAD, "M", "ر"),
        (0xFEAF, "M", "ز"),
        (0xFEB1, "M", "س"),
        (0xFEB5, "M", "ش"),
        (0xFEB9, "M", "ص"),
        (0xFEBD, "M", "ض"),
        (0xFEC1, "M", "ط"),
        (0xFEC5, "M", "ظ"),
        (0xFEC9, "M", "ع"),
        (0xFECD, "M", "غ"),
        (0xFED1, "M", "ف"),
        (0xFED5, "M", "ق"),
        (0xFED9, "M", "ك"),
        (0xFEDD, "M", "ل"),
        (0xFEE1, "M", "م"),
        (0xFEE5, "M", "ن"),
        (0xFEE9, "M", "ه"),
        (0xFEED, "M", "و"),
        (0xFEEF, "M", "ى"),
        (0xFEF1, "M", "ي"),
        (0xFEF5, "M", "لآ"),
        (0xFEF7, "M", "لأ"),
        (0xFEF9, "M", "لإ"),
        (0xFEFB, "M", "لا"),
        (0xFEFD, "X"),
        (0xFEFF, "I"),
        (0xFF00, "X"),
        (0xFF01, "3", "!"),
        (0xFF02, "3", '"'),
        (0xFF03, "3", "#"),
        (0xFF04, "3", "$"),
        (0xFF05, "3", "%"),
        (0xFF06, "3", "&"),
        (0xFF07, "3", "'"),
        (0xFF08, "3", "("),
        (0xFF09, "3", ")"),
        (0xFF0A, "3", "*"),
        (0xFF0B, "3", "+"),
        (0xFF0C, "3", ","),
        (0xFF0D, "M", "-"),
        (0xFF0E, "M", "."),
        (0xFF0F, "3", "/"),
        (0xFF10, "M", "0"),
        (0xFF11, "M", "1"),
        (0xFF12, "M", "2"),
        (0xFF13, "M", "3"),
        (0xFF14, "M", "4"),
        (0xFF15, "M", "5"),
        (0xFF16, "M", "6"),
        (0xFF17, "M", "7"),
        (0xFF18, "M", "8"),
        (0xFF19, "M", "9"),
        (0xFF1A, "3", ":"),
        (0xFF1B, "3", ";"),
        (0xFF1C, "3", "<"),
        (0xFF1D, "3", "="),
        (0xFF1E, "3", ">"),
    ]


def _seg_51() -> List[Union[Tuple[int, str], Tuple[int, str, str]]]:
    return [
        (0xFF1F, "3", "?"),
        (0xFF20, "3", "@"),
        (0xFF21, "M", "a"),
        (0xFF22, "M", "b"),
        (0xFF23, "M", "c"),
        (0xFF24, "M", "d"),
        (0xFF25, "M", "e"),
        (0xFF26, "M", "f"),
        (0xFF27, "M", "g"),
        (0xFF28, "M", "h"),
        (0xFF29, "M", "i"),
        (0xFF2A, "M", "j"),
        (0xFF2B, "M", "k"),
        (0xFF2C, "M", "l"),
        (0xFF2D, "M", "m"),
        (0xFF2E, "M", "n"),
        (0xFF2F, "M", "o"),
        (0xFF30, "M", "p"),
        (0xFF31, "M", "q"),
        (0xFF32, "M", "r"),
        (0xFF33, "M", "s"),
        (0xFF34, "M", "t"),
        (0xFF35, "M", "u"),
        (0xFF36, "M", "v"),
        (0xFF37, "M", "w"),
        (0xFF38, "M", "x"),
        (0xFF39, "M", "y"),
        (0xFF3A, "M", "z"),
        (0xFF3B, "3", "["),
        (0xFF3C, "3", "\\"),
        (0xFF3D, "3", "]"),
        (0xFF3E, "3", "^"),
        (0xFF3F, "3", "_"),
        (0xFF40, "3", "`"),
        (0xFF41, "M", "a"),
        (0xFF42, "M", "b"),
        (0xFF43, "M", "c"),
        (0xFF44, "M", "d"),
        (0xFF45, "M", "e"),
        (0xFF46, "M", "f"),
        (0xFF47, "M", "g"),
        (0xFF48, "M", "h"),
        (0xFF49, "M", "i"),
        (0xFF4A, "M", "j"),
        (0xFF4B, "M", "k"),
        (0xFF4C, "M", "l"),
        (0xFF4D, "M", "m"),
        (0xFF4E, "M", "n"),
        (0xFF4F, "M", "o"),
        (0xFF50, "M", "p"),
        (0xFF51, "M", "q"),
        (0xFF52, "M", "r"),
        (0xFF53, "M", "s"),
        (0xFF54, "M", "t"),
        (0xFF55, "M", "u"),
        (0xFF56, "M", "v"),
        (0xFF57, "M", "w"),
        (0xFF58, "M", "x"),
        (0xFF59, "M", "y"),
        (0xFF5A, "M", "z"),
        (0xFF5B, "3", "{"),
        (0xFF5C, "3", "|"),
        (0xFF5D, "3", "}"),
        (0xFF5E, "3", "~"),
        (0xFF5F, "M", "⦅"),
        (0xFF60, "M", "⦆"),
        (0xFF61, "M", "."),
        (0xFF62, "M", "「"),
        (0xFF63, "M", "」"),
        (0xFF64, "M", "、"),
        (0xFF65, "M", "・"),
        (0xFF66, "M", "ヲ"),
        (0xFF67, "M", "ァ"),
        (0xFF68, "M", "ィ"),
        (0xFF69, "M", "ゥ"),
        (0xFF6A, "M", "ェ"),
        (0xFF6B, "M", "ォ"),
        (0xFF6C, "M", "ャ"),
        (0xFF6D, "M", "ュ"),
        (0xFF6E, "M", "ョ"),
        (0xFF6F, "M", "ッ"),
        (0xFF70, "M", "ー"),
        (0xFF71, "M", "ア"),
        (0xFF72, "M", "イ"),
        (0xFF73, "M", "ウ"),
        (0xFF74, "M", "エ"),
        (0xFF75, "M", "オ"),
        (0xFF76, "M", "カ"),
        (0xFF77, "M", "キ"),
        (0xFF78, "M", "ク"),
        (0xFF79, "M", "ケ"),
        (0xFF7A, "M", "コ"),
        (0xFF7B, "M", "サ"),
        (0xFF7C, "M", "シ"),
        (0xFF7D, "M", "ス"),
        (0xFF7E, "M", "セ"),
        (0xFF7F, "M", "ソ"),
        (0xFF80, "M", "タ"),
        (0xFF81, "M", "チ"),
        (0xFF82, "M", "ツ"),
    ]


def _seg_52() -> List[Union[Tuple[int, str], Tuple[int, str, str]]]:
    return [
        (0xFF83, "M", "テ"),
        (0xFF84, "M", "ト"),
        (0xFF85, "M", "ナ"),
        (0xFF86, "M", "ニ"),
        (0xFF87, "M", "ヌ"),
        (0xFF88, "M", "ネ"),
        (0xFF89, "M", "ノ"),
        (0xFF8A, "M", "ハ"),
        (0xFF8B, "M", "ヒ"),
        (0xFF8C, "M", "フ"),
        (0xFF8D, "M", "ヘ"),
        (0xFF8E, "M", "ホ"),
        (0xFF8F, "M", "マ"),
        (0xFF90, "M", "ミ"),
        (0xFF91, "M", "ム"),
        (0xFF92, "M", "メ"),
        (0xFF93, "M", "モ"),
        (0xFF94, "M", "ヤ"),
        (0xFF95, "M", "ユ"),
        (0xFF96, "M", "ヨ"),
        (0xFF97, "M", "ラ"),
        (0xFF98, "M", "リ"),
        (0xFF99, "M", "ル"),
        (0xFF9A, "M", "レ"),
        (0xFF9B, "M", "ロ"),
        (0xFF9C, "M", "ワ"),
        (0xFF9D, "M", "ン"),
        (0xFF9E, "M", "゙"),
        (0xFF9F, "M", "゚"),
        (0xFFA0, "X"),
        (0xFFA1, "M", "ᄀ"),
        (0xFFA2, "M", "ᄁ"),
        (0xFFA3, "M", "ᆪ"),
        (0xFFA4, "M", "ᄂ"),
        (0xFFA5, "M", "ᆬ"),
        (0xFFA6, "M", "ᆭ"),
        (0xFFA7, "M", "ᄃ"),
        (0xFFA8, "M", "ᄄ"),
        (0xFFA9, "M", "ᄅ"),
        (0xFFAA, "M", "ᆰ"),
        (0xFFAB, "M", "ᆱ"),
        (0xFFAC, "M", "ᆲ"),
        (0xFFAD, "M", "ᆳ"),
        (0xFFAE, "M", "ᆴ"),
        (0xFFAF, "M", "ᆵ"),
        (0xFFB0, "M", "ᄚ"),
        (0xFFB1, "M", "ᄆ"),
        (0xFFB2, "M", "ᄇ"),
        (0xFFB3, "M", "ᄈ"),
        (0xFFB4, "M", "ᄡ"),
        (0xFFB5, "M", "ᄉ"),
        (0xFFB6, "M", "ᄊ"),
        (0xFFB7, "M", "ᄋ"),
        (0xFFB8, "M", "ᄌ"),
        (0xFFB9, "M", "ᄍ"),
        (0xFFBA, "M", "ᄎ"),
        (0xFFBB, "M", "ᄏ"),
        (0xFFBC, "M", "ᄐ"),
        (0xFFBD, "M", "ᄑ"),
        (0xFFBE, "M", "ᄒ"),
        (0xFFBF, "X"),
        (0xFFC2, "M", "ᅡ"),
        (0xFFC3, "M", "ᅢ"),
        (0xFFC4, "M", "ᅣ"),
        (0xFFC5, "M", "ᅤ"),
        (0xFFC6, "M", "ᅥ"),
        (0xFFC7, "M", "ᅦ"),
        (0xFFC8, "X"),
        (0xFFCA, "M", "ᅧ"),
        (0xFFCB, "M", "ᅨ"),
        (0xFFCC, "M", "ᅩ"),
        (0xFFCD, "M", "ᅪ"),
        (0xFFCE, "M", "ᅫ"),
        (0xFFCF, "M", "ᅬ"),
        (0xFFD0, "X"),
        (0xFFD2, "M", "ᅭ"),
        (0xFFD3, "M", "ᅮ"),
        (0xFFD4, "M", "ᅯ"),
        (0xFFD5, "M", "ᅰ"),
        (0xFFD6, "M", "ᅱ"),
        (0xFFD7, "M", "ᅲ"),
        (0xFFD8, "X"),
        (0xFFDA, "M", "ᅳ"),
        (0xFFDB, "M", "ᅴ"),
        (0xFFDC, "M", "ᅵ"),
        (0xFFDD, "X"),
        (0xFFE0, "M", "¢"),
        (0xFFE1, "M", "£"),
        (0xFFE2, "M", "¬"),
        (0xFFE3, "3", " ̄"),
        (0xFFE4, "M", "¦"),
        (0xFFE5, "M", "¥"),
        (0xFFE6, "M", "₩"),
        (0xFFE7, "X"),
        (0xFFE8, "M", "│"),
        (0xFFE9, "M", "←"),
        (0xFFEA, "M", "↑"),
        (0xFFEB, "M", "→"),
        (0xFFEC, "M", "↓"),
        (0xFFED, "M", "■"),
    ]


def _seg_53() -> List[Union[Tuple[int, str], Tuple[int, str, str]]]:
    return [
        (0xFFEE, "M", "○"),
        (0xFFEF, "X"),
        (0x10000, "V"),
        (0x1000C, "X"),
        (0x1000D, "V"),
        (0x10027, "X"),
        (0x10028, "V"),
        (0x1003B, "X"),
        (0x1003C, "V"),
        (0x1003E, "X"),
        (0x1003F, "V"),
        (0x1004E, "X"),
        (0x10050, "V"),
        (0x1005E, "X"),
        (0x10080, "V"),
        (0x100FB, "X"),
        (0x10100, "V"),
        (0x10103, "X"),
        (0x10107, "V"),
        (0x10134, "X"),
        (0x10137, "V"),
        (0x1018F, "X"),
        (0x10190, "V"),
        (0x1019D, "X"),
        (0x101A0, "V"),
        (0x101A1, "X"),
        (0x101D0, "V"),
        (0x101FE, "X"),
        (0x10280, "V"),
        (0x1029D, "X"),
        (0x102A0, "V"),
        (0x102D1, "X"),
        (0x102E0, "V"),
        (0x102FC, "X"),
        (0x10300, "V"),
        (0x10324, "X"),
        (0x1032D, "V"),
        (0x1034B, "X"),
        (0x10350, "V"),
        (0x1037B, "X"),
        (0x10380, "V"),
        (0x1039E, "X"),
        (0x1039F, "V"),
        (0x103C4, "X"),
        (0x103C8, "V"),
        (0x103D6, "X"),
        (0x10400, "M", "𐐨"),
        (0x10401, "M", "𐐩"),
        (0x10402, "M", "𐐪"),
        (0x10403, "M", "𐐫"),
        (0x10404, "M", "𐐬"),
        (0x10405, "M", "𐐭"),
        (0x10406, "M", "𐐮"),
        (0x10407, "M", "𐐯"),
        (0x10408, "M", "𐐰"),
        (0x10409, "M", "𐐱"),
        (0x1040A, "M", "𐐲"),
        (0x1040B, "M", "𐐳"),
        (0x1040C, "M", "𐐴"),
        (0x1040D, "M", "𐐵"),
        (0x1040E, "M", "𐐶"),
        (0x1040F, "M", "𐐷"),
        (0x10410, "M", "𐐸"),
        (0x10411, "M", "𐐹"),
        (0x10412, "M", "𐐺"),
        (0x10413, "M", "𐐻"),
        (0x10414, "M", "𐐼"),
        (0x10415, "M", "𐐽"),
        (0x10416, "M", "𐐾"),
        (0x10417, "M", "𐐿"),
        (0x10418, "M", "𐑀"),
        (0x10419, "M", "𐑁"),
        (0x1041A, "M", "𐑂"),
        (0x1041B, "M", "𐑃"),
        (0x1041C, "M", "𐑄"),
        (0x1041D, "M", "𐑅"),
        (0x1041E, "M", "𐑆"),
        (0x1041F, "M", "𐑇"),
        (0x10420, "M", "𐑈"),
        (0x10421, "M", "𐑉"),
        (0x10422, "M", "𐑊"),
        (0x10423, "M", "𐑋"),
        (0x10424, "M", "𐑌"),
        (0x10425, "M", "𐑍"),
        (0x10426, "M", "𐑎"),
        (0x10427, "M", "𐑏"),
        (0x10428, "V"),
        (0x1049E, "X"),
        (0x104A0, "V"),
        (0x104AA, "X"),
        (0x104B0, "M", "𐓘"),
        (0x104B1, "M", "𐓙"),
        (0x104B2, "M", "𐓚"),
        (0x104B3, "M", "𐓛"),
        (0x104B4, "M", "𐓜"),
        (0x104B5, "M", "𐓝"),
        (0x104B6, "M", "𐓞"),
        (0x104B7, "M", "𐓟"),
        (0x104B8, "M", "𐓠"),
        (0x104B9, "M", "𐓡"),
    ]


def _seg_54() -> List[Union[Tuple[int, str], Tuple[int, str, str]]]:
    return [
        (0x104BA, "M", "𐓢"),
        (0x104BB, "M", "𐓣"),
        (0x104BC, "M", "𐓤"),
        (0x104BD, "M", "𐓥"),
        (0x104BE, "M", "𐓦"),
        (0x104BF, "M", "𐓧"),
        (0x104C0, "M", "𐓨"),
        (0x104C1, "M", "𐓩"),
        (0x104C2, "M", "𐓪"),
        (0x104C3, "M", "𐓫"),
        (0x104C4, "M", "𐓬"),
        (0x104C5, "M", "𐓭"),
        (0x104C6, "M", "𐓮"),
        (0x104C7, "M", "𐓯"),
        (0x104C8, "M", "𐓰"),
        (0x104C9, "M", "𐓱"),
        (0x104CA, "M", "𐓲"),
        (0x104CB, "M", "𐓳"),
        (0x104CC, "M", "𐓴"),
        (0x104CD, "M", "𐓵"),
        (0x104CE, "M", "𐓶"),
        (0x104CF, "M", "𐓷"),
        (0x104D0, "M", "𐓸"),
        (0x104D1, "M", "𐓹"),
        (0x104D2, "M", "𐓺"),
        (0x104D3, "M", "𐓻"),
        (0x104D4, "X"),
        (0x104D8, "V"),
        (0x104FC, "X"),
        (0x10500, "V"),
        (0x10528, "X"),
        (0x10530, "V"),
        (0x10564, "X"),
        (0x1056F, "V"),
        (0x10570, "M", "𐖗"),
        (0x10571, "M", "𐖘"),
        (0x10572, "M", "𐖙"),
        (0x10573, "M", "𐖚"),
        (0x10574, "M", "𐖛"),
        (0x10575, "M", "𐖜"),
        (0x10576, "M", "𐖝"),
        (0x10577, "M", "𐖞"),
        (0x10578, "M", "𐖟"),
        (0x10579, "M", "𐖠"),
        (0x1057A, "M", "𐖡"),
        (0x1057B, "X"),
        (0x1057C, "M", "𐖣"),
        (0x1057D, "M", "𐖤"),
        (0x1057E, "M", "𐖥"),
        (0x1057F, "M", "𐖦"),
        (0x10580, "M", "𐖧"),
        (0x10581, "M", "𐖨"),
        (0x10582, "M", "𐖩"),
        (0x10583, "M", "𐖪"),
        (0x10584, "M", "𐖫"),
        (0x10585, "M", "𐖬"),
        (0x10586, "M", "𐖭"),
        (0x10587, "M", "𐖮"),
        (0x10588, "M", "𐖯"),
        (0x10589, "M", "𐖰"),
        (0x1058A, "M", "𐖱"),
        (0x1058B, "X"),
        (0x1058C, "M", "𐖳"),
        (0x1058D, "M", "𐖴"),
        (0x1058E, "M", "𐖵"),
        (0x1058F, "M", "𐖶"),
        (0x10590, "M", "𐖷"),
        (0x10591, "M", "𐖸"),
        (0x10592, "M", "𐖹"),
        (0x10593, "X"),
        (0x10594, "M", "𐖻"),
        (0x10595, "M", "𐖼"),
        (0x10596, "X"),
        (0x10597, "V"),
        (0x105A2, "X"),
        (0x105A3, "V"),
        (0x105B2, "X"),
        (0x105B3, "V"),
        (0x105BA, "X"),
        (0x105BB, "V"),
        (0x105BD, "X"),
        (0x10600, "V"),
        (0x10737, "X"),
        (0x10740, "V"),
        (0x10756, "X"),
        (0x10760, "V"),
        (0x10768, "X"),
        (0x10780, "V"),
        (0x10781, "M", "ː"),
        (0x10782, "M", "ˑ"),
        (0x10783, "M", "æ"),
        (0x10784, "M", "ʙ"),
        (0x10785, "M", "ɓ"),
        (0x10786, "X"),
        (0x10787, "M", "ʣ"),
        (0x10788, "M", "ꭦ"),
        (0x10789, "M", "ʥ"),
        (0x1078A, "M", "ʤ"),
        (0x1078B, "M", "ɖ"),
        (0x1078C, "M", "ɗ"),
    ]


def _seg_55() -> List[Union[Tuple[int, str], Tuple[int, str, str]]]:
    return [
        (0x1078D, "M", "ᶑ"),
        (0x1078E, "M", "ɘ"),
        (0x1078F, "M", "ɞ"),
        (0x10790, "M", "ʩ"),
        (0x10791, "M", "ɤ"),
        (0x10792, "M", "ɢ"),
        (0x10793, "M", "ɠ"),
        (0x10794, "M", "ʛ"),
        (0x10795, "M", "ħ"),
        (0x10796, "M", "ʜ"),
        (0x10797, "M", "ɧ"),
        (0x10798, "M", "ʄ"),
        (0x10799, "M", "ʪ"),
        (0x1079A, "M", "ʫ"),
        (0x1079B, "M", "ɬ"),
        (0x1079C, "M", "𝼄"),
        (0x1079D, "M", "ꞎ"),
        (0x1079E, "M", "ɮ"),
        (0x1079F, "M", "𝼅"),
        (0x107A0, "M", "ʎ"),
        (0x107A1, "M", "𝼆"),
        (0x107A2, "M", "ø"),
        (0x107A3, "M", "ɶ"),
        (0x107A4, "M", "ɷ"),
        (0x107A5, "M", "q"),
        (0x107A6, "M", "ɺ"),
        (0x107A7, "M", "𝼈"),
        (0x107A8, "M", "ɽ"),
        (0x107A9, "M", "ɾ"),
        (0x107AA, "M", "ʀ"),
        (0x107AB, "M", "ʨ"),
        (0x107AC, "M", "ʦ"),
        (0x107AD, "M", "ꭧ"),
        (0x107AE, "M", "ʧ"),
        (0x107AF, "M", "ʈ"),
        (0x107B0, "M", "ⱱ"),
        (0x107B1, "X"),
        (0x107B2, "M", "ʏ"),
        (0x107B3, "M", "ʡ"),
        (0x107B4, "M", "ʢ"),
        (0x107B5, "M", "ʘ"),
        (0x107B6, "M", "ǀ"),
        (0x107B7, "M", "ǁ"),
        (0x107B8, "M", "ǂ"),
        (0x107B9, "M", "𝼊"),
        (0x107BA, "M", "𝼞"),
        (0x107BB, "X"),
        (0x10800, "V"),
        (0x10806, "X"),
        (0x10808, "V"),
        (0x10809, "X"),
        (0x1080A, "V"),
        (0x10836, "X"),
        (0x10837, "V"),
        (0x10839, "X"),
        (0x1083C, "V"),
        (0x1083D, "X"),
        (0x1083F, "V"),
        (0x10856, "X"),
        (0x10857, "V"),
        (0x1089F, "X"),
        (0x108A7, "V"),
        (0x108B0, "X"),
        (0x108E0, "V"),
        (0x108F3, "X"),
        (0x108F4, "V"),
        (0x108F6, "X"),
        (0x108FB, "V"),
        (0x1091C, "X"),
        (0x1091F, "V"),
        (0x1093A, "X"),
        (0x1093F, "V"),
        (0x10940, "X"),
        (0x10980, "V"),
        (0x109B8, "X"),
        (0x109BC, "V"),
        (0x109D0, "X"),
        (0x109D2, "V"),
        (0x10A04, "X"),
        (0x10A05, "V"),
        (0x10A07, "X"),
        (0x10A0C, "V"),
        (0x10A14, "X"),
        (0x10A15, "V"),
        (0x10A18, "X"),
        (0x10A19, "V"),
        (0x10A36, "X"),
        (0x10A38, "V"),
        (0x10A3B, "X"),
        (0x10A3F, "V"),
        (0x10A49, "X"),
        (0x10A50, "V"),
        (0x10A59, "X"),
        (0x10A60, "V"),
        (0x10AA0, "X"),
        (0x10AC0, "V"),
        (0x10AE7, "X"),
        (0x10AEB, "V"),
        (0x10AF7, "X"),
        (0x10B00, "V"),
    ]


def _seg_56() -> List[Union[Tuple[int, str], Tuple[int, str, str]]]:
    return [
        (0x10B36, "X"),
        (0x10B39, "V"),
        (0x10B56, "X"),
        (0x10B58, "V"),
        (0x10B73, "X"),
        (0x10B78, "V"),
        (0x10B92, "X"),
        (0x10B99, "V"),
        (0x10B9D, "X"),
        (0x10BA9, "V"),
        (0x10BB0, "X"),
        (0x10C00, "V"),
        (0x10C49, "X"),
        (0x10C80, "M", "𐳀"),
        (0x10C81, "M", "𐳁"),
        (0x10C82, "M", "𐳂"),
        (0x10C83, "M", "𐳃"),
        (0x10C84, "M", "𐳄"),
        (0x10C85, "M", "𐳅"),
        (0x10C86, "M", "𐳆"),
        (0x10C87, "M", "𐳇"),
        (0x10C88, "M", "𐳈"),
        (0x10C89, "M", "𐳉"),
        (0x10C8A, "M", "𐳊"),
        (0x10C8B, "M", "𐳋"),
        (0x10C8C, "M", "𐳌"),
        (0x10C8D, "M", "𐳍"),
        (0x10C8E, "M", "𐳎"),
        (0x10C8F, "M", "𐳏"),
        (0x10C90, "M", "𐳐"),
        (0x10C91, "M", "𐳑"),
        (0x10C92, "M", "𐳒"),
        (0x10C93, "M", "𐳓"),
        (0x10C94, "M", "𐳔"),
        (0x10C95, "M", "𐳕"),
        (0x10C96, "M", "𐳖"),
        (0x10C97, "M", "𐳗"),
        (0x10C98, "M", "𐳘"),
        (0x10C99, "M", "𐳙"),
        (0x10C9A, "M", "𐳚"),
        (0x10C9B, "M", "𐳛"),
        (0x10C9C, "M", "𐳜"),
        (0x10C9D, "M", "𐳝"),
        (0x10C9E, "M", "𐳞"),
        (0x10C9F, "M", "𐳟"),
        (0x10CA0, "M", "𐳠"),
        (0x10CA1, "M", "𐳡"),
        (0x10CA2, "M", "𐳢"),
        (0x10CA3, "M", "𐳣"),
        (0x10CA4, "M", "𐳤"),
        (0x10CA5, "M", "𐳥"),
        (0x10CA6, "M", "𐳦"),
        (0x10CA7, "M", "𐳧"),
        (0x10CA8, "M", "𐳨"),
        (0x10CA9, "M", "𐳩"),
        (0x10CAA, "M", "𐳪"),
        (0x10CAB, "M", "𐳫"),
        (0x10CAC, "M", "𐳬"),
        (0x10CAD, "M", "𐳭"),
        (0x10CAE, "M", "𐳮"),
        (0x10CAF, "M", "𐳯"),
        (0x10CB0, "M", "𐳰"),
        (0x10CB1, "M", "𐳱"),
        (0x10CB2, "M", "𐳲"),
        (0x10CB3, "X"),
        (0x10CC0, "V"),
        (0x10CF3, "X"),
        (0x10CFA, "V"),
        (0x10D28, "X"),
        (0x10D30, "V"),
        (0x10D3A, "X"),
        (0x10E60, "V"),
        (0x10E7F, "X"),
        (0x10E80, "V"),
        (0x10EAA, "X"),
        (0x10EAB, "V"),
        (0x10EAE, "X"),
        (0x10EB0, "V"),
        (0x10EB2, "X"),
        (0x10EFD, "V"),
        (0x10F28, "X"),
        (0x10F30, "V"),
        (0x10F5A, "X"),
        (0x10F70, "V"),
        (0x10F8A, "X"),
        (0x10FB0, "V"),
        (0x10FCC, "X"),
        (0x10FE0, "V"),
        (0x10FF7, "X"),
        (0x11000, "V"),
        (0x1104E, "X"),
        (0x11052, "V"),
        (0x11076, "X"),
        (0x1107F, "V"),
        (0x110BD, "X"),
        (0x110BE, "V"),
        (0x110C3, "X"),
        (0x110D0, "V"),
        (0x110E9, "X"),
        (0x110F0, "V"),
    ]


def _seg_57() -> List[Union[Tuple[int, str], Tuple[int, str, str]]]:
    return [
        (0x110FA, "X"),
        (0x11100, "V"),
        (0x11135, "X"),
        (0x11136, "V"),
        (0x11148, "X"),
        (0x11150, "V"),
        (0x11177, "X"),
        (0x11180, "V"),
        (0x111E0, "X"),
        (0x111E1, "V"),
        (0x111F5, "X"),
        (0x11200, "V"),
        (0x11212, "X"),
        (0x11213, "V"),
        (0x11242, "X"),
        (0x11280, "V"),
        (0x11287, "X"),
        (0x11288, "V"),
        (0x11289, "X"),
        (0x1128A, "V"),
        (0x1128E, "X"),
        (0x1128F, "V"),
        (0x1129E, "X"),
        (0x1129F, "V"),
        (0x112AA, "X"),
        (0x112B0, "V"),
        (0x112EB, "X"),
        (0x112F0, "V"),
        (0x112FA, "X"),
        (0x11300, "V"),
        (0x11304, "X"),
        (0x11305, "V"),
        (0x1130D, "X"),
        (0x1130F, "V"),
        (0x11311, "X"),
        (0x11313, "V"),
        (0x11329, "X"),
        (0x1132A, "V"),
        (0x11331, "X"),
        (0x11332, "V"),
        (0x11334, "X"),
        (0x11335, "V"),
        (0x1133A, "X"),
        (0x1133B, "V"),
        (0x11345, "X"),
        (0x11347, "V"),
        (0x11349, "X"),
        (0x1134B, "V"),
        (0x1134E, "X"),
        (0x11350, "V"),
        (0x11351, "X"),
        (0x11357, "V"),
        (0x11358, "X"),
        (0x1135D, "V"),
        (0x11364, "X"),
        (0x11366, "V"),
        (0x1136D, "X"),
        (0x11370, "V"),
        (0x11375, "X"),
        (0x11400, "V"),
        (0x1145C, "X"),
        (0x1145D, "V"),
        (0x11462, "X"),
        (0x11480, "V"),
        (0x114C8, "X"),
        (0x114D0, "V"),
        (0x114DA, "X"),
        (0x11580, "V"),
        (0x115B6, "X"),
        (0x115B8, "V"),
        (0x115DE, "X"),
        (0x11600, "V"),
        (0x11645, "X"),
        (0x11650, "V"),
        (0x1165A, "X"),
        (0x11660, "V"),
        (0x1166D, "X"),
        (0x11680, "V"),
        (0x116BA, "X"),
        (0x116C0, "V"),
        (0x116CA, "X"),
        (0x11700, "V"),
        (0x1171B, "X"),
        (0x1171D, "V"),
        (0x1172C, "X"),
        (0x11730, "V"),
        (0x11747, "X"),
        (0x11800, "V"),
        (0x1183C, "X"),
        (0x118A0, "M", "𑣀"),
        (0x118A1, "M", "𑣁"),
        (0x118A2, "M", "𑣂"),
        (0x118A3, "M", "𑣃"),
        (0x118A4, "M", "𑣄"),
        (0x118A5, "M", "𑣅"),
        (0x118A6, "M", "𑣆"),
        (0x118A7, "M", "𑣇"),
        (0x118A8, "M", "𑣈"),
        (0x118A9, "M", "𑣉"),
        (0x118AA, "M", "𑣊"),
    ]


def _seg_58() -> List[Union[Tuple[int, str], Tuple[int, str, str]]]:
    return [
        (0x118AB, "M", "𑣋"),
        (0x118AC, "M", "𑣌"),
        (0x118AD, "M", "𑣍"),
        (0x118AE, "M", "𑣎"),
        (0x118AF, "M", "𑣏"),
        (0x118B0, "M", "𑣐"),
        (0x118B1, "M", "𑣑"),
        (0x118B2, "M", "𑣒"),
        (0x118B3, "M", "𑣓"),
        (0x118B4, "M", "𑣔"),
        (0x118B5, "M", "𑣕"),
        (0x118B6, "M", "𑣖"),
        (0x118B7, "M", "𑣗"),
        (0x118B8, "M", "𑣘"),
        (0x118B9, "M", "𑣙"),
        (0x118BA, "M", "𑣚"),
        (0x118BB, "M", "𑣛"),
        (0x118BC, "M", "𑣜"),
        (0x118BD, "M", "𑣝"),
        (0x118BE, "M", "𑣞"),
        (0x118BF, "M", "𑣟"),
        (0x118C0, "V"),
        (0x118F3, "X"),
        (0x118FF, "V"),
        (0x11907, "X"),
        (0x11909, "V"),
        (0x1190A, "X"),
        (0x1190C, "V"),
        (0x11914, "X"),
        (0x11915, "V"),
        (0x11917, "X"),
        (0x11918, "V"),
        (0x11936, "X"),
        (0x11937, "V"),
        (0x11939, "X"),
        (0x1193B, "V"),
        (0x11947, "X"),
        (0x11950, "V"),
        (0x1195A, "X"),
        (0x119A0, "V"),
        (0x119A8, "X"),
        (0x119AA, "V"),
        (0x119D8, "X"),
        (0x119DA, "V"),
        (0x119E5, "X"),
        (0x11A00, "V"),
        (0x11A48, "X"),
        (0x11A50, "V"),
        (0x11AA3, "X"),
        (0x11AB0, "V"),
        (0x11AF9, "X"),
        (0x11B00, "V"),
        (0x11B0A, "X"),
        (0x11C00, "V"),
        (0x11C09, "X"),
        (0x11C0A, "V"),
        (0x11C37, "X"),
        (0x11C38, "V"),
        (0x11C46, "X"),
        (0x11C50, "V"),
        (0x11C6D, "X"),
        (0x11C70, "V"),
        (0x11C90, "X"),
        (0x11C92, "V"),
        (0x11CA8, "X"),
        (0x11CA9, "V"),
        (0x11CB7, "X"),
        (0x11D00, "V"),
        (0x11D07, "X"),
        (0x11D08, "V"),
        (0x11D0A, "X"),
        (0x11D0B, "V"),
        (0x11D37, "X"),
        (0x11D3A, "V"),
        (0x11D3B, "X"),
        (0x11D3C, "V"),
        (0x11D3E, "X"),
        (0x11D3F, "V"),
        (0x11D48, "X"),
        (0x11D50, "V"),
        (0x11D5A, "X"),
        (0x11D60, "V"),
        (0x11D66, "X"),
        (0x11D67, "V"),
        (0x11D69, "X"),
        (0x11D6A, "V"),
        (0x11D8F, "X"),
        (0x11D90, "V"),
        (0x11D92, "X"),
        (0x11D93, "V"),
        (0x11D99, "X"),
        (0x11DA0, "V"),
        (0x11DAA, "X"),
        (0x11EE0, "V"),
        (0x11EF9, "X"),
        (0x11F00, "V"),
        (0x11F11, "X"),
        (0x11F12, "V"),
        (0x11F3B, "X"),
        (0x11F3E, "V"),
    ]


def _seg_59() -> List[Union[Tuple[int, str], Tuple[int, str, str]]]:
    return [
        (0x11F5A, "X"),
        (0x11FB0, "V"),
        (0x11FB1, "X"),
        (0x11FC0, "V"),
        (0x11FF2, "X"),
        (0x11FFF, "V"),
        (0x1239A, "X"),
        (0x12400, "V"),
        (0x1246F, "X"),
        (0x12470, "V"),
        (0x12475, "X"),
        (0x12480, "V"),
        (0x12544, "X"),
        (0x12F90, "V"),
        (0x12FF3, "X"),
        (0x13000, "V"),
        (0x13430, "X"),
        (0x13440, "V"),
        (0x13456, "X"),
        (0x14400, "V"),
        (0x14647, "X"),
        (0x16800, "V"),
        (0x16A39, "X"),
        (0x16A40, "V"),
        (0x16A5F, "X"),
        (0x16A60, "V"),
        (0x16A6A, "X"),
        (0x16A6E, "V"),
        (0x16ABF, "X"),
        (0x16AC0, "V"),
        (0x16ACA, "X"),
        (0x16AD0, "V"),
        (0x16AEE, "X"),
        (0x16AF0, "V"),
        (0x16AF6, "X"),
        (0x16B00, "V"),
        (0x16B46, "X"),
        (0x16B50, "V"),
        (0x16B5A, "X"),
        (0x16B5B, "V"),
        (0x16B62, "X"),
        (0x16B63, "V"),
        (0x16B78, "X"),
        (0x16B7D, "V"),
        (0x16B90, "X"),
        (0x16E40, "M", "𖹠"),
        (0x16E41, "M", "𖹡"),
        (0x16E42, "M", "𖹢"),
        (0x16E43, "M", "𖹣"),
        (0x16E44, "M", "𖹤"),
        (0x16E45, "M", "𖹥"),
        (0x16E46, "M", "𖹦"),
        (0x16E47, "M", "𖹧"),
        (0x16E48, "M", "𖹨"),
        (0x16E49, "M", "𖹩"),
        (0x16E4A, "M", "𖹪"),
        (0x16E4B, "M", "𖹫"),
        (0x16E4C, "M", "𖹬"),
        (0x16E4D, "M", "𖹭"),
        (0x16E4E, "M", "𖹮"),
        (0x16E4F, "M", "𖹯"),
        (0x16E50, "M", "𖹰"),
        (0x16E51, "M", "𖹱"),
        (0x16E52, "M", "𖹲"),
        (0x16E53, "M", "𖹳"),
        (0x16E54, "M", "𖹴"),
        (0x16E55, "M", "𖹵"),
        (0x16E56, "M", "𖹶"),
        (0x16E57, "M", "𖹷"),
        (0x16E58, "M", "𖹸"),
        (0x16E59, "M", "𖹹"),
        (0x16E5A, "M", "𖹺"),
        (0x16E5B, "M", "𖹻"),
        (0x16E5C, "M", "𖹼"),
        (0x16E5D, "M", "𖹽"),
        (0x16E5E, "M", "𖹾"),
        (0x16E5F, "M", "𖹿"),
        (0x16E60, "V"),
        (0x16E9B, "X"),
        (0x16F00, "V"),
        (0x16F4B, "X"),
        (0x16F4F, "V"),
        (0x16F88, "X"),
        (0x16F8F, "V"),
        (0x16FA0, "X"),
        (0x16FE0, "V"),
        (0x16FE5, "X"),
        (0x16FF0, "V"),
        (0x16FF2, "X"),
        (0x17000, "V"),
        (0x187F8, "X"),
        (0x18800, "V"),
        (0x18CD6, "X"),
        (0x18D00, "V"),
        (0x18D09, "X"),
        (0x1AFF0, "V"),
        (0x1AFF4, "X"),
        (0x1AFF5, "V"),
        (0x1AFFC, "X"),
        (0x1AFFD, "V"),
    ]


def _seg_60() -> List[Union[Tuple[int, str], Tuple[int, str, str]]]:
    return [
        (0x1AFFF, "X"),
        (0x1B000, "V"),
        (0x1B123, "X"),
        (0x1B132, "V"),
        (0x1B133, "X"),
        (0x1B150, "V"),
        (0x1B153, "X"),
        (0x1B155, "V"),
        (0x1B156, "X"),
        (0x1B164, "V"),
        (0x1B168, "X"),
        (0x1B170, "V"),
        (0x1B2FC, "X"),
        (0x1BC00, "V"),
        (0x1BC6B, "X"),
        (0x1BC70, "V"),
        (0x1BC7D, "X"),
        (0x1BC80, "V"),
        (0x1BC89, "X"),
        (0x1BC90, "V"),
        (0x1BC9A, "X"),
        (0x1BC9C, "V"),
        (0x1BCA0, "I"),
        (0x1BCA4, "X"),
        (0x1CF00, "V"),
        (0x1CF2E, "X"),
        (0x1CF30, "V"),
        (0x1CF47, "X"),
        (0x1CF50, "V"),
        (0x1CFC4, "X"),
        (0x1D000, "V"),
        (0x1D0F6, "X"),
        (0x1D100, "V"),
        (0x1D127, "X"),
        (0x1D129, "V"),
        (0x1D15E, "M", "𝅗𝅥"),
        (0x1D15F, "M", "𝅘𝅥"),
        (0x1D160, "M", "𝅘𝅥𝅮"),
        (0x1D161, "M", "𝅘𝅥𝅯"),
        (0x1D162, "M", "𝅘𝅥𝅰"),
        (0x1D163, "M", "𝅘𝅥𝅱"),
        (0x1D164, "M", "𝅘𝅥𝅲"),
        (0x1D165, "V"),
        (0x1D173, "X"),
        (0x1D17B, "V"),
        (0x1D1BB, "M", "𝆹𝅥"),
        (0x1D1BC, "M", "𝆺𝅥"),
        (0x1D1BD, "M", "𝆹𝅥𝅮"),
        (0x1D1BE, "M", "𝆺𝅥𝅮"),
        (0x1D1BF, "M", "𝆹𝅥𝅯"),
        (0x1D1C0, "M", "𝆺𝅥𝅯"),
        (0x1D1C1, "V"),
        (0x1D1EB, "X"),
        (0x1D200, "V"),
        (0x1D246, "X"),
        (0x1D2C0, "V"),
        (0x1D2D4, "X"),
        (0x1D2E0, "V"),
        (0x1D2F4, "X"),
        (0x1D300, "V"),
        (0x1D357, "X"),
        (0x1D360, "V"),
        (0x1D379, "X"),
        (0x1D400, "M", "a"),
        (0x1D401, "M", "b"),
        (0x1D402, "M", "c"),
        (0x1D403, "M", "d"),
        (0x1D404, "M", "e"),
        (0x1D405, "M", "f"),
        (0x1D406, "M", "g"),
        (0x1D407, "M", "h"),
        (0x1D408, "M", "i"),
        (0x1D409, "M", "j"),
        (0x1D40A, "M", "k"),
        (0x1D40B, "M", "l"),
        (0x1D40C, "M", "m"),
        (0x1D40D, "M", "n"),
        (0x1D40E, "M", "o"),
        (0x1D40F, "M", "p"),
        (0x1D410, "M", "q"),
        (0x1D411, "M", "r"),
        (0x1D412, "M", "s"),
        (0x1D413, "M", "t"),
        (0x1D414, "M", "u"),
        (0x1D415, "M", "v"),
        (0x1D416, "M", "w"),
        (0x1D417, "M", "x"),
        (0x1D418, "M", "y"),
        (0x1D419, "M", "z"),
        (0x1D41A, "M", "a"),
        (0x1D41B, "M", "b"),
        (0x1D41C, "M", "c"),
        (0x1D41D, "M", "d"),
        (0x1D41E, "M", "e"),
        (0x1D41F, "M", "f"),
        (0x1D420, "M", "g"),
        (0x1D421, "M", "h"),
        (0x1D422, "M", "i"),
        (0x1D423, "M", "j"),
        (0x1D424, "M", "k"),
    ]


def _seg_61() -> List[Union[Tuple[int, str], Tuple[int, str, str]]]:
    return [
        (0x1D425, "M", "l"),
        (0x1D426, "M", "m"),
        (0x1D427, "M", "n"),
        (0x1D428, "M", "o"),
        (0x1D429, "M", "p"),
        (0x1D42A, "M", "q"),
        (0x1D42B, "M", "r"),
        (0x1D42C, "M", "s"),
        (0x1D42D, "M", "t"),
        (0x1D42E, "M", "u"),
        (0x1D42F, "M", "v"),
        (0x1D430, "M", "w"),
        (0x1D431, "M", "x"),
        (0x1D432, "M", "y"),
        (0x1D433, "M", "z"),
        (0x1D434, "M", "a"),
        (0x1D435, "M", "b"),
        (0x1D436, "M", "c"),
        (0x1D437, "M", "d"),
        (0x1D438, "M", "e"),
        (0x1D439, "M", "f"),
        (0x1D43A, "M", "g"),
        (0x1D43B, "M", "h"),
        (0x1D43C, "M", "i"),
        (0x1D43D, "M", "j"),
        (0x1D43E, "M", "k"),
        (0x1D43F, "M", "l"),
        (0x1D440, "M", "m"),
        (0x1D441, "M", "n"),
        (0x1D442, "M", "o"),
        (0x1D443, "M", "p"),
        (0x1D444, "M", "q"),
        (0x1D445, "M", "r"),
        (0x1D446, "M", "s"),
        (0x1D447, "M", "t"),
        (0x1D448, "M", "u"),
        (0x1D449, "M", "v"),
        (0x1D44A, "M", "w"),
        (0x1D44B, "M", "x"),
        (0x1D44C, "M", "y"),
        (0x1D44D, "M", "z"),
        (0x1D44E, "M", "a"),
        (0x1D44F, "M", "b"),
        (0x1D450, "M", "c"),
        (0x1D451, "M", "d"),
        (0x1D452, "M", "e"),
        (0x1D453, "M", "f"),
        (0x1D454, "M", "g"),
        (0x1D455, "X"),
        (0x1D456, "M", "i"),
        (0x1D457, "M", "j"),
        (0x1D458, "M", "k"),
        (0x1D459, "M", "l"),
        (0x1D45A, "M", "m"),
        (0x1D45B, "M", "n"),
        (0x1D45C, "M", "o"),
        (0x1D45D, "M", "p"),
        (0x1D45E, "M", "q"),
        (0x1D45F, "M", "r"),
        (0x1D460, "M", "s"),
        (0x1D461, "M", "t"),
        (0x1D462, "M", "u"),
        (0x1D463, "M", "v"),
        (0x1D464, "M", "w"),
        (0x1D465, "M", "x"),
        (0x1D466, "M", "y"),
        (0x1D467, "M", "z"),
        (0x1D468, "M", "a"),
        (0x1D469, "M", "b"),
        (0x1D46A, "M", "c"),
        (0x1D46B, "M", "d"),
        (0x1D46C, "M", "e"),
        (0x1D46D, "M", "f"),
        (0x1D46E, "M", "g"),
        (0x1D46F, "M", "h"),
        (0x1D470, "M", "i"),
        (0x1D471, "M", "j"),
        (0x1D472, "M", "k"),
        (0x1D473, "M", "l"),
        (0x1D474, "M", "m"),
        (0x1D475, "M", "n"),
        (0x1D476, "M", "o"),
        (0x1D477, "M", "p"),
        (0x1D478, "M", "q"),
        (0x1D479, "M", "r"),
        (0x1D47A, "M", "s"),
        (0x1D47B, "M", "t"),
        (0x1D47C, "M", "u"),
        (0x1D47D, "M", "v"),
        (0x1D47E, "M", "w"),
        (0x1D47F, "M", "x"),
        (0x1D480, "M", "y"),
        (0x1D481, "M", "z"),
        (0x1D482, "M", "a"),
        (0x1D483, "M", "b"),
        (0x1D484, "M", "c"),
        (0x1D485, "M", "d"),
        (0x1D486, "M", "e"),
        (0x1D487, "M", "f"),
        (0x1D488, "M", "g"),
    ]


def _seg_62() -> List[Union[Tuple[int, str], Tuple[int, str, str]]]:
    return [
        (0x1D489, "M", "h"),
        (0x1D48A, "M", "i"),
        (0x1D48B, "M", "j"),
        (0x1D48C, "M", "k"),
        (0x1D48D, "M", "l"),
        (0x1D48E, "M", "m"),
        (0x1D48F, "M", "n"),
        (0x1D490, "M", "o"),
        (0x1D491, "M", "p"),
        (0x1D492, "M", "q"),
        (0x1D493, "M", "r"),
        (0x1D494, "M", "s"),
        (0x1D495, "M", "t"),
        (0x1D496, "M", "u"),
        (0x1D497, "M", "v"),
        (0x1D498, "M", "w"),
        (0x1D499, "M", "x"),
        (0x1D49A, "M", "y"),
        (0x1D49B, "M", "z"),
        (0x1D49C, "M", "a"),
        (0x1D49D, "X"),
        (0x1D49E, "M", "c"),
        (0x1D49F, "M", "d"),
        (0x1D4A0, "X"),
        (0x1D4A2, "M", "g"),
        (0x1D4A3, "X"),
        (0x1D4A5, "M", "j"),
        (0x1D4A6, "M", "k"),
        (0x1D4A7, "X"),
        (0x1D4A9, "M", "n"),
        (0x1D4AA, "M", "o"),
        (0x1D4AB, "M", "p"),
        (0x1D4AC, "M", "q"),
        (0x1D4AD, "X"),
        (0x1D4AE, "M", "s"),
        (0x1D4AF, "M", "t"),
        (0x1D4B0, "M", "u"),
        (0x1D4B1, "M", "v"),
        (0x1D4B2, "M", "w"),
        (0x1D4B3, "M", "x"),
        (0x1D4B4, "M", "y"),
        (0x1D4B5, "M", "z"),
        (0x1D4B6, "M", "a"),
        (0x1D4B7, "M", "b"),
        (0x1D4B8, "M", "c"),
        (0x1D4B9, "M", "d"),
        (0x1D4BA, "X"),
        (0x1D4BB, "M", "f"),
        (0x1D4BC, "X"),
        (0x1D4BD, "M", "h"),
        (0x1D4BE, "M", "i"),
        (0x1D4BF, "M", "j"),
        (0x1D4C0, "M", "k"),
        (0x1D4C1, "M", "l"),
        (0x1D4C2, "M", "m"),
        (0x1D4C3, "M", "n"),
        (0x1D4C4, "X"),
        (0x1D4C5, "M", "p"),
        (0x1D4C6, "M", "q"),
        (0x1D4C7, "M", "r"),
        (0x1D4C8, "M", "s"),
        (0x1D4C9, "M", "t"),
        (0x1D4CA, "M", "u"),
        (0x1D4CB, "M", "v"),
        (0x1D4CC, "M", "w"),
        (0x1D4CD, "M", "x"),
        (0x1D4CE, "M", "y"),
        (0x1D4CF, "M", "z"),
        (0x1D4D0, "M", "a"),
        (0x1D4D1, "M", "b"),
        (0x1D4D2, "M", "c"),
        (0x1D4D3, "M", "d"),
        (0x1D4D4, "M", "e"),
        (0x1D4D5, "M", "f"),
        (0x1D4D6, "M", "g"),
        (0x1D4D7, "M", "h"),
        (0x1D4D8, "M", "i"),
        (0x1D4D9, "M", "j"),
        (0x1D4DA, "M", "k"),
        (0x1D4DB, "M", "l"),
        (0x1D4DC, "M", "m"),
        (0x1D4DD, "M", "n"),
        (0x1D4DE, "M", "o"),
        (0x1D4DF, "M", "p"),
        (0x1D4E0, "M", "q"),
        (0x1D4E1, "M", "r"),
        (0x1D4E2, "M", "s"),
        (0x1D4E3, "M", "t"),
        (0x1D4E4, "M", "u"),
        (0x1D4E5, "M", "v"),
        (0x1D4E6, "M", "w"),
        (0x1D4E7, "M", "x"),
        (0x1D4E8, "M", "y"),
        (0x1D4E9, "M", "z"),
        (0x1D4EA, "M", "a"),
        (0x1D4EB, "M", "b"),
        (0x1D4EC, "M", "c"),
        (0x1D4ED, "M", "d"),
        (0x1D4EE, "M", "e"),
        (0x1D4EF, "M", "f"),
    ]


def _seg_63() -> List[Union[Tuple[int, str], Tuple[int, str, str]]]:
    return [
        (0x1D4F0, "M", "g"),
        (0x1D4F1, "M", "h"),
        (0x1D4F2, "M", "i"),
        (0x1D4F3, "M", "j"),
        (0x1D4F4, "M", "k"),
        (0x1D4F5, "M", "l"),
        (0x1D4F6, "M", "m"),
        (0x1D4F7, "M", "n"),
        (0x1D4F8, "M", "o"),
        (0x1D4F9, "M", "p"),
        (0x1D4FA, "M", "q"),
        (0x1D4FB, "M", "r"),
        (0x1D4FC, "M", "s"),
        (0x1D4FD, "M", "t"),
        (0x1D4FE, "M", "u"),
        (0x1D4FF, "M", "v"),
        (0x1D500, "M", "w"),
        (0x1D501, "M", "x"),
        (0x1D502, "M", "y"),
        (0x1D503, "M", "z"),
        (0x1D504, "M", "a"),
        (0x1D505, "M", "b"),
        (0x1D506, "X"),
        (0x1D507, "M", "d"),
        (0x1D508, "M", "e"),
        (0x1D509, "M", "f"),
        (0x1D50A, "M", "g"),
        (0x1D50B, "X"),
        (0x1D50D, "M", "j"),
        (0x1D50E, "M", "k"),
        (0x1D50F, "M", "l"),
        (0x1D510, "M", "m"),
        (0x1D511, "M", "n"),
        (0x1D512, "M", "o"),
        (0x1D513, "M", "p"),
        (0x1D514, "M", "q"),
        (0x1D515, "X"),
        (0x1D516, "M", "s"),
        (0x1D517, "M", "t"),
        (0x1D518, "M", "u"),
        (0x1D519, "M", "v"),
        (0x1D51A, "M", "w"),
        (0x1D51B, "M", "x"),
        (0x1D51C, "M", "y"),
        (0x1D51D, "X"),
        (0x1D51E, "M", "a"),
        (0x1D51F, "M", "b"),
        (0x1D520, "M", "c"),
        (0x1D521, "M", "d"),
        (0x1D522, "M", "e"),
        (0x1D523, "M", "f"),
        (0x1D524, "M", "g"),
        (0x1D525, "M", "h"),
        (0x1D526, "M", "i"),
        (0x1D527, "M", "j"),
        (0x1D528, "M", "k"),
        (0x1D529, "M", "l"),
        (0x1D52A, "M", "m"),
        (0x1D52B, "M", "n"),
        (0x1D52C, "M", "o"),
        (0x1D52D, "M", "p"),
        (0x1D52E, "M", "q"),
        (0x1D52F, "M", "r"),
        (0x1D530, "M", "s"),
        (0x1D531, "M", "t"),
        (0x1D532, "M", "u"),
        (0x1D533, "M", "v"),
        (0x1D534, "M", "w"),
        (0x1D535, "M", "x"),
        (0x1D536, "M", "y"),
        (0x1D537, "M", "z"),
        (0x1D538, "M", "a"),
        (0x1D539, "M", "b"),
        (0x1D53A, "X"),
        (0x1D53B, "M", "d"),
        (0x1D53C, "M", "e"),
        (0x1D53D, "M", "f"),
        (0x1D53E, "M", "g"),
        (0x1D53F, "X"),
        (0x1D540, "M", "i"),
        (0x1D541, "M", "j"),
        (0x1D542, "M", "k"),
        (0x1D543, "M", "l"),
        (0x1D544, "M", "m"),
        (0x1D545, "X"),
        (0x1D546, "M", "o"),
        (0x1D547, "X"),
        (0x1D54A, "M", "s"),
        (0x1D54B, "M", "t"),
        (0x1D54C, "M", "u"),
        (0x1D54D, "M", "v"),
        (0x1D54E, "M", "w"),
        (0x1D54F, "M", "x"),
        (0x1D550, "M", "y"),
        (0x1D551, "X"),
        (0x1D552, "M", "a"),
        (0x1D553, "M", "b"),
        (0x1D554, "M", "c"),
        (0x1D555, "M", "d"),
        (0x1D556, "M", "e"),
    ]


def _seg_64() -> List[Union[Tuple[int, str], Tuple[int, str, str]]]:
    return [
        (0x1D557, "M", "f"),
        (0x1D558, "M", "g"),
        (0x1D559, "M", "h"),
        (0x1D55A, "M", "i"),
        (0x1D55B, "M", "j"),
        (0x1D55C, "M", "k"),
        (0x1D55D, "M", "l"),
        (0x1D55E, "M", "m"),
        (0x1D55F, "M", "n"),
        (0x1D560, "M", "o"),
        (0x1D561, "M", "p"),
        (0x1D562, "M", "q"),
        (0x1D563, "M", "r"),
        (0x1D564, "M", "s"),
        (0x1D565, "M", "t"),
        (0x1D566, "M", "u"),
        (0x1D567, "M", "v"),
        (0x1D568, "M", "w"),
        (0x1D569, "M", "x"),
        (0x1D56A, "M", "y"),
        (0x1D56B, "M", "z"),
        (0x1D56C, "M", "a"),
        (0x1D56D, "M", "b"),
        (0x1D56E, "M", "c"),
        (0x1D56F, "M", "d"),
        (0x1D570, "M", "e"),
        (0x1D571, "M", "f"),
        (0x1D572, "M", "g"),
        (0x1D573, "M", "h"),
        (0x1D574, "M", "i"),
        (0x1D575, "M", "j"),
        (0x1D576, "M", "k"),
        (0x1D577, "M", "l"),
        (0x1D578, "M", "m"),
        (0x1D579, "M", "n"),
        (0x1D57A, "M", "o"),
        (0x1D57B, "M", "p"),
        (0x1D57C, "M", "q"),
        (0x1D57D, "M", "r"),
        (0x1D57E, "M", "s"),
        (0x1D57F, "M", "t"),
        (0x1D580, "M", "u"),
        (0x1D581, "M", "v"),
        (0x1D582, "M", "w"),
        (0x1D583, "M", "x"),
        (0x1D584, "M", "y"),
        (0x1D585, "M", "z"),
        (0x1D586, "M", "a"),
        (0x1D587, "M", "b"),
        (0x1D588, "M", "c"),
        (0x1D589, "M", "d"),
        (0x1D58A, "M", "e"),
        (0x1D58B, "M", "f"),
        (0x1D58C, "M", "g"),
        (0x1D58D, "M", "h"),
        (0x1D58E, "M", "i"),
        (0x1D58F, "M", "j"),
        (0x1D590, "M", "k"),
        (0x1D591, "M", "l"),
        (0x1D592, "M", "m"),
        (0x1D593, "M", "n"),
        (0x1D594, "M", "o"),
        (0x1D595, "M", "p"),
        (0x1D596, "M", "q"),
        (0x1D597, "M", "r"),
        (0x1D598, "M", "s"),
        (0x1D599, "M", "t"),
        (0x1D59A, "M", "u"),
        (0x1D59B, "M", "v"),
        (0x1D59C, "M", "w"),
        (0x1D59D, "M", "x"),
        (0x1D59E, "M", "y"),
        (0x1D59F, "M", "z"),
        (0x1D5A0, "M", "a"),
        (0x1D5A1, "M", "b"),
        (0x1D5A2, "M", "c"),
        (0x1D5A3, "M", "d"),
        (0x1D5A4, "M", "e"),
        (0x1D5A5, "M", "f"),
        (0x1D5A6, "M", "g"),
        (0x1D5A7, "M", "h"),
        (0x1D5A8, "M", "i"),
        (0x1D5A9, "M", "j"),
        (0x1D5AA, "M", "k"),
        (0x1D5AB, "M", "l"),
        (0x1D5AC, "M", "m"),
        (0x1D5AD, "M", "n"),
        (0x1D5AE, "M", "o"),
        (0x1D5AF, "M", "p"),
        (0x1D5B0, "M", "q"),
        (0x1D5B1, "M", "r"),
        (0x1D5B2, "M", "s"),
        (0x1D5B3, "M", "t"),
        (0x1D5B4, "M", "u"),
        (0x1D5B5, "M", "v"),
        (0x1D5B6, "M", "w"),
        (0x1D5B7, "M", "x"),
        (0x1D5B8, "M", "y"),
        (0x1D5B9, "M", "z"),
        (0x1D5BA, "M", "a"),
    ]


def _seg_65() -> List[Union[Tuple[int, str], Tuple[int, str, str]]]:
    return [
        (0x1D5BB, "M", "b"),
        (0x1D5BC, "M", "c"),
        (0x1D5BD, "M", "d"),
        (0x1D5BE, "M", "e"),
        (0x1D5BF, "M", "f"),
        (0x1D5C0, "M", "g"),
        (0x1D5C1, "M", "h"),
        (0x1D5C2, "M", "i"),
        (0x1D5C3, "M", "j"),
        (0x1D5C4, "M", "k"),
        (0x1D5C5, "M", "l"),
        (0x1D5C6, "M", "m"),
        (0x1D5C7, "M", "n"),
        (0x1D5C8, "M", "o"),
        (0x1D5C9, "M", "p"),
        (0x1D5CA, "M", "q"),
        (0x1D5CB, "M", "r"),
        (0x1D5CC, "M", "s"),
        (0x1D5CD, "M", "t"),
        (0x1D5CE, "M", "u"),
        (0x1D5CF, "M", "v"),
        (0x1D5D0, "M", "w"),
        (0x1D5D1, "M", "x"),
        (0x1D5D2, "M", "y"),
        (0x1D5D3, "M", "z"),
        (0x1D5D4, "M", "a"),
        (0x1D5D5, "M", "b"),
        (0x1D5D6, "M", "c"),
        (0x1D5D7, "M", "d"),
        (0x1D5D8, "M", "e"),
        (0x1D5D9, "M", "f"),
        (0x1D5DA, "M", "g"),
        (0x1D5DB, "M", "h"),
        (0x1D5DC, "M", "i"),
        (0x1D5DD, "M", "j"),
        (0x1D5DE, "M", "k"),
        (0x1D5DF, "M", "l"),
        (0x1D5E0, "M", "m"),
        (0x1D5E1, "M", "n"),
        (0x1D5E2, "M", "o"),
        (0x1D5E3, "M", "p"),
        (0x1D5E4, "M", "q"),
        (0x1D5E5, "M", "r"),
        (0x1D5E6, "M", "s"),
        (0x1D5E7, "M", "t"),
        (0x1D5E8, "M", "u"),
        (0x1D5E9, "M", "v"),
        (0x1D5EA, "M", "w"),
        (0x1D5EB, "M", "x"),
        (0x1D5EC, "M", "y"),
        (0x1D5ED, "M", "z"),
        (0x1D5EE, "M", "a"),
        (0x1D5EF, "M", "b"),
        (0x1D5F0, "M", "c"),
        (0x1D5F1, "M", "d"),
        (0x1D5F2, "M", "e"),
        (0x1D5F3, "M", "f"),
        (0x1D5F4, "M", "g"),
        (0x1D5F5, "M", "h"),
        (0x1D5F6, "M", "i"),
        (0x1D5F7, "M", "j"),
        (0x1D5F8, "M", "k"),
        (0x1D5F9, "M", "l"),
        (0x1D5FA, "M", "m"),
        (0x1D5FB, "M", "n"),
        (0x1D5FC, "M", "o"),
        (0x1D5FD, "M", "p"),
        (0x1D5FE, "M", "q"),
        (0x1D5FF, "M", "r"),
        (0x1D600, "M", "s"),
        (0x1D601, "M", "t"),
        (0x1D602, "M", "u"),
        (0x1D603, "M", "v"),
        (0x1D604, "M", "w"),
        (0x1D605, "M", "x"),
        (0x1D606, "M", "y"),
        (0x1D607, "M", "z"),
        (0x1D608, "M", "a"),
        (0x1D609, "M", "b"),
        (0x1D60A, "M", "c"),
        (0x1D60B, "M", "d"),
        (0x1D60C, "M", "e"),
        (0x1D60D, "M", "f"),
        (0x1D60E, "M", "g"),
        (0x1D60F, "M", "h"),
        (0x1D610, "M", "i"),
        (0x1D611, "M", "j"),
        (0x1D612, "M", "k"),
        (0x1D613, "M", "l"),
        (0x1D614, "M", "m"),
        (0x1D615, "M", "n"),
        (0x1D616, "M", "o"),
        (0x1D617, "M", "p"),
        (0x1D618, "M", "q"),
        (0x1D619, "M", "r"),
        (0x1D61A, "M", "s"),
        (0x1D61B, "M", "t"),
        (0x1D61C, "M", "u"),
        (0x1D61D, "M", "v"),
        (0x1D61E, "M", "w"),
    ]


def _seg_66() -> List[Union[Tuple[int, str], Tuple[int, str, str]]]:
    return [
        (0x1D61F, "M", "x"),
        (0x1D620, "M", "y"),
        (0x1D621, "M", "z"),
        (0x1D622, "M", "a"),
        (0x1D623, "M", "b"),
        (0x1D624, "M", "c"),
        (0x1D625, "M", "d"),
        (0x1D626, "M", "e"),
        (0x1D627, "M", "f"),
        (0x1D628, "M", "g"),
        (0x1D629, "M", "h"),
        (0x1D62A, "M", "i"),
        (0x1D62B, "M", "j"),
        (0x1D62C, "M", "k"),
        (0x1D62D, "M", "l"),
        (0x1D62E, "M", "m"),
        (0x1D62F, "M", "n"),
        (0x1D630, "M", "o"),
        (0x1D631, "M", "p"),
        (0x1D632, "M", "q"),
        (0x1D633, "M", "r"),
        (0x1D634, "M", "s"),
        (0x1D635, "M", "t"),
        (0x1D636, "M", "u"),
        (0x1D637, "M", "v"),
        (0x1D638, "M", "w"),
        (0x1D639, "M", "x"),
        (0x1D63A, "M", "y"),
        (0x1D63B, "M", "z"),
        (0x1D63C, "M", "a"),
        (0x1D63D, "M", "b"),
        (0x1D63E, "M", "c"),
        (0x1D63F, "M", "d"),
        (0x1D640, "M", "e"),
        (0x1D641, "M", "f"),
        (0x1D642, "M", "g"),
        (0x1D643, "M", "h"),
        (0x1D644, "M", "i"),
        (0x1D645, "M", "j"),
        (0x1D646, "M", "k"),
        (0x1D647, "M", "l"),
        (0x1D648, "M", "m"),
        (0x1D649, "M", "n"),
        (0x1D64A, "M", "o"),
        (0x1D64B, "M", "p"),
        (0x1D64C, "M", "q"),
        (0x1D64D, "M", "r"),
        (0x1D64E, "M", "s"),
        (0x1D64F, "M", "t"),
        (0x1D650, "M", "u"),
        (0x1D651, "M", "v"),
        (0x1D652, "M", "w"),
        (0x1D653, "M", "x"),
        (0x1D654, "M", "y"),
        (0x1D655, "M", "z"),
        (0x1D656, "M", "a"),
        (0x1D657, "M", "b"),
        (0x1D658, "M", "c"),
        (0x1D659, "M", "d"),
        (0x1D65A, "M", "e"),
        (0x1D65B, "M", "f"),
        (0x1D65C, "M", "g"),
        (0x1D65D, "M", "h"),
        (0x1D65E, "M", "i"),
        (0x1D65F, "M", "j"),
        (0x1D660, "M", "k"),
        (0x1D661, "M", "l"),
        (0x1D662, "M", "m"),
        (0x1D663, "M", "n"),
        (0x1D664, "M", "o"),
        (0x1D665, "M", "p"),
        (0x1D666, "M", "q"),
        (0x1D667, "M", "r"),
        (0x1D668, "M", "s"),
        (0x1D669, "M", "t"),
        (0x1D66A, "M", "u"),
        (0x1D66B, "M", "v"),
        (0x1D66C, "M", "w"),
        (0x1D66D, "M", "x"),
        (0x1D66E, "M", "y"),
        (0x1D66F, "M", "z"),
        (0x1D670, "M", "a"),
        (0x1D671, "M", "b"),
        (0x1D672, "M", "c"),
        (0x1D673, "M", "d"),
        (0x1D674, "M", "e"),
        (0x1D675, "M", "f"),
        (0x1D676, "M", "g"),
        (0x1D677, "M", "h"),
        (0x1D678, "M", "i"),
        (0x1D679, "M", "j"),
        (0x1D67A, "M", "k"),
        (0x1D67B, "M", "l"),
        (0x1D67C, "M", "m"),
        (0x1D67D, "M", "n"),
        (0x1D67E, "M", "o"),
        (0x1D67F, "M", "p"),
        (0x1D680, "M", "q"),
        (0x1D681, "M", "r"),
        (0x1D682, "M", "s"),
    ]


def _seg_67() -> List[Union[Tuple[int, str], Tuple[int, str, str]]]:
    return [
        (0x1D683, "M", "t"),
        (0x1D684, "M", "u"),
        (0x1D685, "M", "v"),
        (0x1D686, "M", "w"),
        (0x1D687, "M", "x"),
        (0x1D688, "M", "y"),
        (0x1D689, "M", "z"),
        (0x1D68A, "M", "a"),
        (0x1D68B, "M", "b"),
        (0x1D68C, "M", "c"),
        (0x1D68D, "M", "d"),
        (0x1D68E, "M", "e"),
        (0x1D68F, "M", "f"),
        (0x1D690, "M", "g"),
        (0x1D691, "M", "h"),
        (0x1D692, "M", "i"),
        (0x1D693, "M", "j"),
        (0x1D694, "M", "k"),
        (0x1D695, "M", "l"),
        (0x1D696, "M", "m"),
        (0x1D697, "M", "n"),
        (0x1D698, "M", "o"),
        (0x1D699, "M", "p"),
        (0x1D69A, "M", "q"),
        (0x1D69B, "M", "r"),
        (0x1D69C, "M", "s"),
        (0x1D69D, "M", "t"),
        (0x1D69E, "M", "u"),
        (0x1D69F, "M", "v"),
        (0x1D6A0, "M", "w"),
        (0x1D6A1, "M", "x"),
        (0x1D6A2, "M", "y"),
        (0x1D6A3, "M", "z"),
        (0x1D6A4, "M", "ı"),
        (0x1D6A5, "M", "ȷ"),
        (0x1D6A6, "X"),
        (0x1D6A8, "M", "α"),
        (0x1D6A9, "M", "β"),
        (0x1D6AA, "M", "γ"),
        (0x1D6AB, "M", "δ"),
        (0x1D6AC, "M", "ε"),
        (0x1D6AD, "M", "ζ"),
        (0x1D6AE, "M", "η"),
        (0x1D6AF, "M", "θ"),
        (0x1D6B0, "M", "ι"),
        (0x1D6B1, "M", "κ"),
        (0x1D6B2, "M", "λ"),
        (0x1D6B3, "M", "μ"),
        (0x1D6B4, "M", "ν"),
        (0x1D6B5, "M", "ξ"),
        (0x1D6B6, "M", "ο"),
        (0x1D6B7, "M", "π"),
        (0x1D6B8, "M", "ρ"),
        (0x1D6B9, "M", "θ"),
        (0x1D6BA, "M", "σ"),
        (0x1D6BB, "M", "τ"),
        (0x1D6BC, "M", "υ"),
        (0x1D6BD, "M", "φ"),
        (0x1D6BE, "M", "χ"),
        (0x1D6BF, "M", "ψ"),
        (0x1D6C0, "M", "ω"),
        (0x1D6C1, "M", "∇"),
        (0x1D6C2, "M", "α"),
        (0x1D6C3, "M", "β"),
        (0x1D6C4, "M", "γ"),
        (0x1D6C5, "M", "δ"),
        (0x1D6C6, "M", "ε"),
        (0x1D6C7, "M", "ζ"),
        (0x1D6C8, "M", "η"),
        (0x1D6C9, "M", "θ"),
        (0x1D6CA, "M", "ι"),
        (0x1D6CB, "M", "κ"),
        (0x1D6CC, "M", "λ"),
        (0x1D6CD, "M", "μ"),
        (0x1D6CE, "M", "ν"),
        (0x1D6CF, "M", "ξ"),
        (0x1D6D0, "M", "ο"),
        (0x1D6D1, "M", "π"),
        (0x1D6D2, "M", "ρ"),
        (0x1D6D3, "M", "σ"),
        (0x1D6D5, "M", "τ"),
        (0x1D6D6, "M", "υ"),
        (0x1D6D7, "M", "φ"),
        (0x1D6D8, "M", "χ"),
        (0x1D6D9, "M", "ψ"),
        (0x1D6DA, "M", "ω"),
        (0x1D6DB, "M", "∂"),
        (0x1D6DC, "M", "ε"),
        (0x1D6DD, "M", "θ"),
        (0x1D6DE, "M", "κ"),
        (0x1D6DF, "M", "φ"),
        (0x1D6E0, "M", "ρ"),
        (0x1D6E1, "M", "π"),
        (0x1D6E2, "M", "α"),
        (0x1D6E3, "M", "β"),
        (0x1D6E4, "M", "γ"),
        (0x1D6E5, "M", "δ"),
        (0x1D6E6, "M", "ε"),
        (0x1D6E7, "M", "ζ"),
        (0x1D6E8, "M", "η"),
    ]


def _seg_68() -> List[Union[Tuple[int, str], Tuple[int, str, str]]]:
    return [
        (0x1D6E9, "M", "θ"),
        (0x1D6EA, "M", "ι"),
        (0x1D6EB, "M", "κ"),
        (0x1D6EC, "M", "λ"),
        (0x1D6ED, "M", "μ"),
        (0x1D6EE, "M", "ν"),
        (0x1D6EF, "M", "ξ"),
        (0x1D6F0, "M", "ο"),
        (0x1D6F1, "M", "π"),
        (0x1D6F2, "M", "ρ"),
        (0x1D6F3, "M", "θ"),
        (0x1D6F4, "M", "σ"),
        (0x1D6F5, "M", "τ"),
        (0x1D6F6, "M", "υ"),
        (0x1D6F7, "M", "φ"),
        (0x1D6F8, "M", "χ"),
        (0x1D6F9, "M", "ψ"),
        (0x1D6FA, "M", "ω"),
        (0x1D6FB, "M", "∇"),
        (0x1D6FC, "M", "α"),
        (0x1D6FD, "M", "β"),
        (0x1D6FE, "M", "γ"),
        (0x1D6FF, "M", "δ"),
        (0x1D700, "M", "ε"),
        (0x1D701, "M", "ζ"),
        (0x1D702, "M", "η"),
        (0x1D703, "M", "θ"),
        (0x1D704, "M", "ι"),
        (0x1D705, "M", "κ"),
        (0x1D706, "M", "λ"),
        (0x1D707, "M", "μ"),
        (0x1D708, "M", "ν"),
        (0x1D709, "M", "ξ"),
        (0x1D70A, "M", "ο"),
        (0x1D70B, "M", "π"),
        (0x1D70C, "M", "ρ"),
        (0x1D70D, "M", "σ"),
        (0x1D70F, "M", "τ"),
        (0x1D710, "M", "υ"),
        (0x1D711, "M", "φ"),
        (0x1D712, "M", "χ"),
        (0x1D713, "M", "ψ"),
        (0x1D714, "M", "ω"),
        (0x1D715, "M", "∂"),
        (0x1D716, "M", "ε"),
        (0x1D717, "M", "θ"),
        (0x1D718, "M", "κ"),
        (0x1D719, "M", "φ"),
        (0x1D71A, "M", "ρ"),
        (0x1D71B, "M", "π"),
        (0x1D71C, "M", "α"),
        (0x1D71D, "M", "β"),
        (0x1D71E, "M", "γ"),
        (0x1D71F, "M", "δ"),
        (0x1D720, "M", "ε"),
        (0x1D721, "M", "ζ"),
        (0x1D722, "M", "η"),
        (0x1D723, "M", "θ"),
        (0x1D724, "M", "ι"),
        (0x1D725, "M", "κ"),
        (0x1D726, "M", "λ"),
        (0x1D727, "M", "μ"),
        (0x1D728, "M", "ν"),
        (0x1D729, "M", "ξ"),
        (0x1D72A, "M", "ο"),
        (0x1D72B, "M", "π"),
        (0x1D72C, "M", "ρ"),
        (0x1D72D, "M", "θ"),
        (0x1D72E, "M", "σ"),
        (0x1D72F, "M", "τ"),
        (0x1D730, "M", "υ"),
        (0x1D731, "M", "φ"),
        (0x1D732, "M", "χ"),
        (0x1D733, "M", "ψ"),
        (0x1D734, "M", "ω"),
        (0x1D735, "M", "∇"),
        (0x1D736, "M", "α"),
        (0x1D737, "M", "β"),
        (0x1D738, "M", "γ"),
        (0x1D739, "M", "δ"),
        (0x1D73A, "M", "ε"),
        (0x1D73B, "M", "ζ"),
        (0x1D73C, "M", "η"),
        (0x1D73D, "M", "θ"),
        (0x1D73E, "M", "ι"),
        (0x1D73F, "M", "κ"),
        (0x1D740, "M", "λ"),
        (0x1D741, "M", "μ"),
        (0x1D742, "M", "ν"),
        (0x1D743, "M", "ξ"),
        (0x1D744, "M", "ο"),
        (0x1D745, "M", "π"),
        (0x1D746, "M", "ρ"),
        (0x1D747, "M", "σ"),
        (0x1D749, "M", "τ"),
        (0x1D74A, "M", "υ"),
        (0x1D74B, "M", "φ"),
        (0x1D74C, "M", "χ"),
        (0x1D74D, "M", "ψ"),
        (0x1D74E, "M", "ω"),
    ]


def _seg_69() -> List[Union[Tuple[int, str], Tuple[int, str, str]]]:
    return [
        (0x1D74F, "M", "∂"),
        (0x1D750, "M", "ε"),
        (0x1D751, "M", "θ"),
        (0x1D752, "M", "κ"),
        (0x1D753, "M", "φ"),
        (0x1D754, "M", "ρ"),
        (0x1D755, "M", "π"),
        (0x1D756, "M", "α"),
        (0x1D757, "M", "β"),
        (0x1D758, "M", "γ"),
        (0x1D759, "M", "δ"),
        (0x1D75A, "M", "ε"),
        (0x1D75B, "M", "ζ"),
        (0x1D75C, "M", "η"),
        (0x1D75D, "M", "θ"),
        (0x1D75E, "M", "ι"),
        (0x1D75F, "M", "κ"),
        (0x1D760, "M", "λ"),
        (0x1D761, "M", "μ"),
        (0x1D762, "M", "ν"),
        (0x1D763, "M", "ξ"),
        (0x1D764, "M", "ο"),
        (0x1D765, "M", "π"),
        (0x1D766, "M", "ρ"),
        (0x1D767, "M", "θ"),
        (0x1D768, "M", "σ"),
        (0x1D769, "M", "τ"),
        (0x1D76A, "M", "υ"),
        (0x1D76B, "M", "φ"),
        (0x1D76C, "M", "χ"),
        (0x1D76D, "M", "ψ"),
        (0x1D76E, "M", "ω"),
        (0x1D76F, "M", "∇"),
        (0x1D770, "M", "α"),
        (0x1D771, "M", "β"),
        (0x1D772, "M", "γ"),
        (0x1D773, "M", "δ"),
        (0x1D774, "M", "ε"),
        (0x1D775, "M", "ζ"),
        (0x1D776, "M", "η"),
        (0x1D777, "M", "θ"),
        (0x1D778, "M", "ι"),
        (0x1D779, "M", "κ"),
        (0x1D77A, "M", "λ"),
        (0x1D77B, "M", "μ"),
        (0x1D77C, "M", "ν"),
        (0x1D77D, "M", "ξ"),
        (0x1D77E, "M", "ο"),
        (0x1D77F, "M", "π"),
        (0x1D780, "M", "ρ"),
        (0x1D781, "M", "σ"),
        (0x1D783, "M", "τ"),
        (0x1D784, "M", "υ"),
        (0x1D785, "M", "φ"),
        (0x1D786, "M", "χ"),
        (0x1D787, "M", "ψ"),
        (0x1D788, "M", "ω"),
        (0x1D789, "M", "∂"),
        (0x1D78A, "M", "ε"),
        (0x1D78B, "M", "θ"),
        (0x1D78C, "M", "κ"),
        (0x1D78D, "M", "φ"),
        (0x1D78E, "M", "ρ"),
        (0x1D78F, "M", "π"),
        (0x1D790, "M", "α"),
        (0x1D791, "M", "β"),
        (0x1D792, "M", "γ"),
        (0x1D793, "M", "δ"),
        (0x1D794, "M", "ε"),
        (0x1D795, "M", "ζ"),
        (0x1D796, "M", "η"),
        (0x1D797, "M", "θ"),
        (0x1D798, "M", "ι"),
        (0x1D799, "M", "κ"),
        (0x1D79A, "M", "λ"),
        (0x1D79B, "M", "μ"),
        (0x1D79C, "M", "ν"),
        (0x1D79D, "M", "ξ"),
        (0x1D79E, "M", "ο"),
        (0x1D79F, "M", "π"),
        (0x1D7A0, "M", "ρ"),
        (0x1D7A1, "M", "θ"),
        (0x1D7A2, "M", "σ"),
        (0x1D7A3, "M", "τ"),
        (0x1D7A4, "M", "υ"),
        (0x1D7A5, "M", "φ"),
        (0x1D7A6, "M", "χ"),
        (0x1D7A7, "M", "ψ"),
        (0x1D7A8, "M", "ω"),
        (0x1D7A9, "M", "∇"),
        (0x1D7AA, "M", "α"),
        (0x1D7AB, "M", "β"),
        (0x1D7AC, "M", "γ"),
        (0x1D7AD, "M", "δ"),
        (0x1D7AE, "M", "ε"),
        (0x1D7AF, "M", "ζ"),
        (0x1D7B0, "M", "η"),
        (0x1D7B1, "M", "θ"),
        (0x1D7B2, "M", "ι"),
        (0x1D7B3, "M", "κ"),
    ]


def _seg_70() -> List[Union[Tuple[int, str], Tuple[int, str, str]]]:
    return [
        (0x1D7B4, "M", "λ"),
        (0x1D7B5, "M", "μ"),
        (0x1D7B6, "M", "ν"),
        (0x1D7B7, "M", "ξ"),
        (0x1D7B8, "M", "ο"),
        (0x1D7B9, "M", "π"),
        (0x1D7BA, "M", "ρ"),
        (0x1D7BB, "M", "σ"),
        (0x1D7BD, "M", "τ"),
        (0x1D7BE, "M", "υ"),
        (0x1D7BF, "M", "φ"),
        (0x1D7C0, "M", "χ"),
        (0x1D7C1, "M", "ψ"),
        (0x1D7C2, "M", "ω"),
        (0x1D7C3, "M", "∂"),
        (0x1D7C4, "M", "ε"),
        (0x1D7C5, "M", "θ"),
        (0x1D7C6, "M", "κ"),
        (0x1D7C7, "M", "φ"),
        (0x1D7C8, "M", "ρ"),
        (0x1D7C9, "M", "π"),
        (0x1D7CA, "M", "ϝ"),
        (0x1D7CC, "X"),
        (0x1D7CE, "M", "0"),
        (0x1D7CF, "M", "1"),
        (0x1D7D0, "M", "2"),
        (0x1D7D1, "M", "3"),
        (0x1D7D2, "M", "4"),
        (0x1D7D3, "M", "5"),
        (0x1D7D4, "M", "6"),
        (0x1D7D5, "M", "7"),
        (0x1D7D6, "M", "8"),
        (0x1D7D7, "M", "9"),
        (0x1D7D8, "M", "0"),
        (0x1D7D9, "M", "1"),
        (0x1D7DA, "M", "2"),
        (0x1D7DB, "M", "3"),
        (0x1D7DC, "M", "4"),
        (0x1D7DD, "M", "5"),
        (0x1D7DE, "M", "6"),
        (0x1D7DF, "M", "7"),
        (0x1D7E0, "M", "8"),
        (0x1D7E1, "M", "9"),
        (0x1D7E2, "M", "0"),
        (0x1D7E3, "M", "1"),
        (0x1D7E4, "M", "2"),
        (0x1D7E5, "M", "3"),
        (0x1D7E6, "M", "4"),
        (0x1D7E7, "M", "5"),
        (0x1D7E8, "M", "6"),
        (0x1D7E9, "M", "7"),
        (0x1D7EA, "M", "8"),
        (0x1D7EB, "M", "9"),
        (0x1D7EC, "M", "0"),
        (0x1D7ED, "M", "1"),
        (0x1D7EE, "M", "2"),
        (0x1D7EF, "M", "3"),
        (0x1D7F0, "M", "4"),
        (0x1D7F1, "M", "5"),
        (0x1D7F2, "M", "6"),
        (0x1D7F3, "M", "7"),
        (0x1D7F4, "M", "8"),
        (0x1D7F5, "M", "9"),
        (0x1D7F6, "M", "0"),
        (0x1D7F7, "M", "1"),
        (0x1D7F8, "M", "2"),
        (0x1D7F9, "M", "3"),
        (0x1D7FA, "M", "4"),
        (0x1D7FB, "M", "5"),
        (0x1D7FC, "M", "6"),
        (0x1D7FD, "M", "7"),
        (0x1D7FE, "M", "8"),
        (0x1D7FF, "M", "9"),
        (0x1D800, "V"),
        (0x1DA8C, "X"),
        (0x1DA9B, "V"),
        (0x1DAA0, "X"),
        (0x1DAA1, "V"),
        (0x1DAB0, "X"),
        (0x1DF00, "V"),
        (0x1DF1F, "X"),
        (0x1DF25, "V"),
        (0x1DF2B, "X"),
        (0x1E000, "V"),
        (0x1E007, "X"),
        (0x1E008, "V"),
        (0x1E019, "X"),
        (0x1E01B, "V"),
        (0x1E022, "X"),
        (0x1E023, "V"),
        (0x1E025, "X"),
        (0x1E026, "V"),
        (0x1E02B, "X"),
        (0x1E030, "M", "а"),
        (0x1E031, "M", "б"),
        (0x1E032, "M", "в"),
        (0x1E033, "M", "г"),
        (0x1E034, "M", "д"),
        (0x1E035, "M", "е"),
        (0x1E036, "M", "ж"),
    ]


def _seg_71() -> List[Union[Tuple[int, str], Tuple[int, str, str]]]:
    return [
        (0x1E037, "M", "з"),
        (0x1E038, "M", "и"),
        (0x1E039, "M", "к"),
        (0x1E03A, "M", "л"),
        (0x1E03B, "M", "м"),
        (0x1E03C, "M", "о"),
        (0x1E03D, "M", "п"),
        (0x1E03E, "M", "р"),
        (0x1E03F, "M", "с"),
        (0x1E040, "M", "т"),
        (0x1E041, "M", "у"),
        (0x1E042, "M", "ф"),
        (0x1E043, "M", "х"),
        (0x1E044, "M", "ц"),
        (0x1E045, "M", "ч"),
        (0x1E046, "M", "ш"),
        (0x1E047, "M", "ы"),
        (0x1E048, "M", "э"),
        (0x1E049, "M", "ю"),
        (0x1E04A, "M", "ꚉ"),
        (0x1E04B, "M", "ә"),
        (0x1E04C, "M", "і"),
        (0x1E04D, "M", "ј"),
        (0x1E04E, "M", "ө"),
        (0x1E04F, "M", "ү"),
        (0x1E050, "M", "ӏ"),
        (0x1E051, "M", "а"),
        (0x1E052, "M", "б"),
        (0x1E053, "M", "в"),
        (0x1E054, "M", "г"),
        (0x1E055, "M", "д"),
        (0x1E056, "M", "е"),
        (0x1E057, "M", "ж"),
        (0x1E058, "M", "з"),
        (0x1E059, "M", "и"),
        (0x1E05A, "M", "к"),
        (0x1E05B, "M", "л"),
        (0x1E05C, "M", "о"),
        (0x1E05D, "M", "п"),
        (0x1E05E, "M", "с"),
        (0x1E05F, "M", "у"),
        (0x1E060, "M", "ф"),
        (0x1E061, "M", "х"),
        (0x1E062, "M", "ц"),
        (0x1E063, "M", "ч"),
        (0x1E064, "M", "ш"),
        (0x1E065, "M", "ъ"),
        (0x1E066, "M", "ы"),
        (0x1E067, "M", "ґ"),
        (0x1E068, "M", "і"),
        (0x1E069, "M", "ѕ"),
        (0x1E06A, "M", "џ"),
        (0x1E06B, "M", "ҫ"),
        (0x1E06C, "M", "ꙑ"),
        (0x1E06D, "M", "ұ"),
        (0x1E06E, "X"),
        (0x1E08F, "V"),
        (0x1E090, "X"),
        (0x1E100, "V"),
        (0x1E12D, "X"),
        (0x1E130, "V"),
        (0x1E13E, "X"),
        (0x1E140, "V"),
        (0x1E14A, "X"),
        (0x1E14E, "V"),
        (0x1E150, "X"),
        (0x1E290, "V"),
        (0x1E2AF, "X"),
        (0x1E2C0, "V"),
        (0x1E2FA, "X"),
        (0x1E2FF, "V"),
        (0x1E300, "X"),
        (0x1E4D0, "V"),
        (0x1E4FA, "X"),
        (0x1E7E0, "V"),
        (0x1E7E7, "X"),
        (0x1E7E8, "V"),
        (0x1E7EC, "X"),
        (0x1E7ED, "V"),
        (0x1E7EF, "X"),
        (0x1E7F0, "V"),
        (0x1E7FF, "X"),
        (0x1E800, "V"),
        (0x1E8C5, "X"),
        (0x1E8C7, "V"),
        (0x1E8D7, "X"),
        (0x1E900, "M", "𞤢"),
        (0x1E901, "M", "𞤣"),
        (0x1E902, "M", "𞤤"),
        (0x1E903, "M", "𞤥"),
        (0x1E904, "M", "𞤦"),
        (0x1E905, "M", "𞤧"),
        (0x1E906, "M", "𞤨"),
        (0x1E907, "M", "𞤩"),
        (0x1E908, "M", "𞤪"),
        (0x1E909, "M", "𞤫"),
        (0x1E90A, "M", "𞤬"),
        (0x1E90B, "M", "𞤭"),
        (0x1E90C, "M", "𞤮"),
        (0x1E90D, "M", "𞤯"),
    ]


def _seg_72() -> List[Union[Tuple[int, str], Tuple[int, str, str]]]:
    return [
        (0x1E90E, "M", "𞤰"),
        (0x1E90F, "M", "𞤱"),
        (0x1E910, "M", "𞤲"),
        (0x1E911, "M", "𞤳"),
        (0x1E912, "M", "𞤴"),
        (0x1E913, "M", "𞤵"),
        (0x1E914, "M", "𞤶"),
        (0x1E915, "M", "𞤷"),
        (0x1E916, "M", "𞤸"),
        (0x1E917, "M", "𞤹"),
        (0x1E918, "M", "𞤺"),
        (0x1E919, "M", "𞤻"),
        (0x1E91A, "M", "𞤼"),
        (0x1E91B, "M", "𞤽"),
        (0x1E91C, "M", "𞤾"),
        (0x1E91D, "M", "𞤿"),
        (0x1E91E, "M", "𞥀"),
        (0x1E91F, "M", "𞥁"),
        (0x1E920, "M", "𞥂"),
        (0x1E921, "M", "𞥃"),
        (0x1E922, "V"),
        (0x1E94C, "X"),
        (0x1E950, "V"),
        (0x1E95A, "X"),
        (0x1E95E, "V"),
        (0x1E960, "X"),
        (0x1EC71, "V"),
        (0x1ECB5, "X"),
        (0x1ED01, "V"),
        (0x1ED3E, "X"),
        (0x1EE00, "M", "ا"),
        (0x1EE01, "M", "ب"),
        (0x1EE02, "M", "ج"),
        (0x1EE03, "M", "د"),
        (0x1EE04, "X"),
        (0x1EE05, "M", "و"),
        (0x1EE06, "M", "ز"),
        (0x1EE07, "M", "ح"),
        (0x1EE08, "M", "ط"),
        (0x1EE09, "M", "ي"),
        (0x1EE0A, "M", "ك"),
        (0x1EE0B, "M", "ل"),
        (0x1EE0C, "M", "م"),
        (0x1EE0D, "M", "ن"),
        (0x1EE0E, "M", "س"),
        (0x1EE0F, "M", "ع"),
        (0x1EE10, "M", "ف"),
        (0x1EE11, "M", "ص"),
        (0x1EE12, "M", "ق"),
        (0x1EE13, "M", "ر"),
        (0x1EE14, "M", "ش"),
        (0x1EE15, "M", "ت"),
        (0x1EE16, "M", "ث"),
        (0x1EE17, "M", "خ"),
        (0x1EE18, "M", "ذ"),
        (0x1EE19, "M", "ض"),
        (0x1EE1A, "M", "ظ"),
        (0x1EE1B, "M", "غ"),
        (0x1EE1C, "M", "ٮ"),
        (0x1EE1D, "M", "ں"),
        (0x1EE1E, "M", "ڡ"),
        (0x1EE1F, "M", "ٯ"),
        (0x1EE20, "X"),
        (0x1EE21, "M", "ب"),
        (0x1EE22, "M", "ج"),
        (0x1EE23, "X"),
        (0x1EE24, "M", "ه"),
        (0x1EE25, "X"),
        (0x1EE27, "M", "ح"),
        (0x1EE28, "X"),
        (0x1EE29, "M", "ي"),
        (0x1EE2A, "M", "ك"),
        (0x1EE2B, "M", "ل"),
        (0x1EE2C, "M", "م"),
        (0x1EE2D, "M", "ن"),
        (0x1EE2E, "M", "س"),
        (0x1EE2F, "M", "ع"),
        (0x1EE30, "M", "ف"),
        (0x1EE31, "M", "ص"),
        (0x1EE32, "M", "ق"),
        (0x1EE33, "X"),
        (0x1EE34, "M", "ش"),
        (0x1EE35, "M", "ت"),
        (0x1EE36, "M", "ث"),
        (0x1EE37, "M", "خ"),
        (0x1EE38, "X"),
        (0x1EE39, "M", "ض"),
        (0x1EE3A, "X"),
        (0x1EE3B, "M", "غ"),
        (0x1EE3C, "X"),
        (0x1EE42, "M", "ج"),
        (0x1EE43, "X"),
        (0x1EE47, "M", "ح"),
        (0x1EE48, "X"),
        (0x1EE49, "M", "ي"),
        (0x1EE4A, "X"),
        (0x1EE4B, "M", "ل"),
        (0x1EE4C, "X"),
        (0x1EE4D, "M", "ن"),
        (0x1EE4E, "M", "س"),
    ]


def _seg_73() -> List[Union[Tuple[int, str], Tuple[int, str, str]]]:
    return [
        (0x1EE4F, "M", "ع"),
        (0x1EE50, "X"),
        (0x1EE51, "M", "ص"),
        (0x1EE52, "M", "ق"),
        (0x1EE53, "X"),
        (0x1EE54, "M", "ش"),
        (0x1EE55, "X"),
        (0x1EE57, "M", "خ"),
        (0x1EE58, "X"),
        (0x1EE59, "M", "ض"),
        (0x1EE5A, "X"),
        (0x1EE5B, "M", "غ"),
        (0x1EE5C, "X"),
        (0x1EE5D, "M", "ں"),
        (0x1EE5E, "X"),
        (0x1EE5F, "M", "ٯ"),
        (0x1EE60, "X"),
        (0x1EE61, "M", "ب"),
        (0x1EE62, "M", "ج"),
        (0x1EE63, "X"),
        (0x1EE64, "M", "ه"),
        (0x1EE65, "X"),
        (0x1EE67, "M", "ح"),
        (0x1EE68, "M", "ط"),
        (0x1EE69, "M", "ي"),
        (0x1EE6A, "M", "ك"),
        (0x1EE6B, "X"),
        (0x1EE6C, "M", "م"),
        (0x1EE6D, "M", "ن"),
        (0x1EE6E, "M", "س"),
        (0x1EE6F, "M", "ع"),
        (0x1EE70, "M", "ف"),
        (0x1EE71, "M", "ص"),
        (0x1EE72, "M", "ق"),
        (0x1EE73, "X"),
        (0x1EE74, "M", "ش"),
        (0x1EE75, "M", "ت"),
        (0x1EE76, "M", "ث"),
        (0x1EE77, "M", "خ"),
        (0x1EE78, "X"),
        (0x1EE79, "M", "ض"),
        (0x1EE7A, "M", "ظ"),
        (0x1EE7B, "M", "غ"),
        (0x1EE7C, "M", "ٮ"),
        (0x1EE7D, "X"),
        (0x1EE7E, "M", "ڡ"),
        (0x1EE7F, "X"),
        (0x1EE80, "M", "ا"),
        (0x1EE81, "M", "ب"),
        (0x1EE82, "M", "ج"),
        (0x1EE83, "M", "د"),
        (0x1EE84, "M", "ه"),
        (0x1EE85, "M", "و"),
        (0x1EE86, "M", "ز"),
        (0x1EE87, "M", "ح"),
        (0x1EE88, "M", "ط"),
        (0x1EE89, "M", "ي"),
        (0x1EE8A, "X"),
        (0x1EE8B, "M", "ل"),
        (0x1EE8C, "M", "م"),
        (0x1EE8D, "M", "ن"),
        (0x1EE8E, "M", "س"),
        (0x1EE8F, "M", "ع"),
        (0x1EE90, "M", "ف"),
        (0x1EE91, "M", "ص"),
        (0x1EE92, "M", "ق"),
        (0x1EE93, "M", "ر"),
        (0x1EE94, "M", "ش"),
        (0x1EE95, "M", "ت"),
        (0x1EE96, "M", "ث"),
        (0x1EE97, "M", "خ"),
        (0x1EE98, "M", "ذ"),
        (0x1EE99, "M", "ض"),
        (0x1EE9A, "M", "ظ"),
        (0x1EE9B, "M", "غ"),
        (0x1EE9C, "X"),
        (0x1EEA1, "M", "ب"),
        (0x1EEA2, "M", "ج"),
        (0x1EEA3, "M", "د"),
        (0x1EEA4, "X"),
        (0x1EEA5, "M", "و"),
        (0x1EEA6, "M", "ز"),
        (0x1EEA7, "M", "ح"),
        (0x1EEA8, "M", "ط"),
        (0x1EEA9, "M", "ي"),
        (0x1EEAA, "X"),
        (0x1EEAB, "M", "ل"),
        (0x1EEAC, "M", "م"),
        (0x1EEAD, "M", "ن"),
        (0x1EEAE, "M", "س"),
        (0x1EEAF, "M", "ع"),
        (0x1EEB0, "M", "ف"),
        (0x1EEB1, "M", "ص"),
        (0x1EEB2, "M", "ق"),
        (0x1EEB3, "M", "ر"),
        (0x1EEB4, "M", "ش"),
        (0x1EEB5, "M", "ت"),
        (0x1EEB6, "M", "ث"),
        (0x1EEB7, "M", "خ"),
        (0x1EEB8, "M", "ذ"),
    ]


def _seg_74() -> List[Union[Tuple[int, str], Tuple[int, str, str]]]:
    return [
        (0x1EEB9, "M", "ض"),
        (0x1EEBA, "M", "ظ"),
        (0x1EEBB, "M", "غ"),
        (0x1EEBC, "X"),
        (0x1EEF0, "V"),
        (0x1EEF2, "X"),
        (0x1F000, "V"),
        (0x1F02C, "X"),
        (0x1F030, "V"),
        (0x1F094, "X"),
        (0x1F0A0, "V"),
        (0x1F0AF, "X"),
        (0x1F0B1, "V"),
        (0x1F0C0, "X"),
        (0x1F0C1, "V"),
        (0x1F0D0, "X"),
        (0x1F0D1, "V"),
        (0x1F0F6, "X"),
        (0x1F101, "3", "0,"),
        (0x1F102, "3", "1,"),
        (0x1F103, "3", "2,"),
        (0x1F104, "3", "3,"),
        (0x1F105, "3", "4,"),
        (0x1F106, "3", "5,"),
        (0x1F107, "3", "6,"),
        (0x1F108, "3", "7,"),
        (0x1F109, "3", "8,"),
        (0x1F10A, "3", "9,"),
        (0x1F10B, "V"),
        (0x1F110, "3", "(a)"),
        (0x1F111, "3", "(b)"),
        (0x1F112, "3", "(c)"),
        (0x1F113, "3", "(d)"),
        (0x1F114, "3", "(e)"),
        (0x1F115, "3", "(f)"),
        (0x1F116, "3", "(g)"),
        (0x1F117, "3", "(h)"),
        (0x1F118, "3", "(i)"),
        (0x1F119, "3", "(j)"),
        (0x1F11A, "3", "(k)"),
        (0x1F11B, "3", "(l)"),
        (0x1F11C, "3", "(m)"),
        (0x1F11D, "3", "(n)"),
        (0x1F11E, "3", "(o)"),
        (0x1F11F, "3", "(p)"),
        (0x1F120, "3", "(q)"),
        (0x1F121, "3", "(r)"),
        (0x1F122, "3", "(s)"),
        (0x1F123, "3", "(t)"),
        (0x1F124, "3", "(u)"),
        (0x1F125, "3", "(v)"),
        (0x1F126, "3", "(w)"),
        (0x1F127, "3", "(x)"),
        (0x1F128, "3", "(y)"),
        (0x1F129, "3", "(z)"),
        (0x1F12A, "M", "〔s〕"),
        (0x1F12B, "M", "c"),
        (0x1F12C, "M", "r"),
        (0x1F12D, "M", "cd"),
        (0x1F12E, "M", "wz"),
        (0x1F12F, "V"),
        (0x1F130, "M", "a"),
        (0x1F131, "M", "b"),
        (0x1F132, "M", "c"),
        (0x1F133, "M", "d"),
        (0x1F134, "M", "e"),
        (0x1F135, "M", "f"),
        (0x1F136, "M", "g"),
        (0x1F137, "M", "h"),
        (0x1F138, "M", "i"),
        (0x1F139, "M", "j"),
        (0x1F13A, "M", "k"),
        (0x1F13B, "M", "l"),
        (0x1F13C, "M", "m"),
        (0x1F13D, "M", "n"),
        (0x1F13E, "M", "o"),
        (0x1F13F, "M", "p"),
        (0x1F140, "M", "q"),
        (0x1F141, "M", "r"),
        (0x1F142, "M", "s"),
        (0x1F143, "M", "t"),
        (0x1F144, "M", "u"),
        (0x1F145, "M", "v"),
        (0x1F146, "M", "w"),
        (0x1F147, "M", "x"),
        (0x1F148, "M", "y"),
        (0x1F149, "M", "z"),
        (0x1F14A, "M", "hv"),
        (0x1F14B, "M", "mv"),
        (0x1F14C, "M", "sd"),
        (0x1F14D, "M", "ss"),
        (0x1F14E, "M", "ppv"),
        (0x1F14F, "M", "wc"),
        (0x1F150, "V"),
        (0x1F16A, "M", "mc"),
        (0x1F16B, "M", "md"),
        (0x1F16C, "M", "mr"),
        (0x1F16D, "V"),
        (0x1F190, "M", "dj"),
        (0x1F191, "V"),
    ]


def _seg_75() -> List[Union[Tuple[int, str], Tuple[int, str, str]]]:
    return [
        (0x1F1AE, "X"),
        (0x1F1E6, "V"),
        (0x1F200, "M", "ほか"),
        (0x1F201, "M", "ココ"),
        (0x1F202, "M", "サ"),
        (0x1F203, "X"),
        (0x1F210, "M", "手"),
        (0x1F211, "M", "字"),
        (0x1F212, "M", "双"),
        (0x1F213, "M", "デ"),
        (0x1F214, "M", "二"),
        (0x1F215, "M", "多"),
        (0x1F216, "M", "解"),
        (0x1F217, "M", "天"),
        (0x1F218, "M", "交"),
        (0x1F219, "M", "映"),
        (0x1F21A, "M", "無"),
        (0x1F21B, "M", "料"),
        (0x1F21C, "M", "前"),
        (0x1F21D, "M", "後"),
        (0x1F21E, "M", "再"),
        (0x1F21F, "M", "新"),
        (0x1F220, "M", "初"),
        (0x1F221, "M", "終"),
        (0x1F222, "M", "生"),
        (0x1F223, "M", "販"),
        (0x1F224, "M", "声"),
        (0x1F225, "M", "吹"),
        (0x1F226, "M", "演"),
        (0x1F227, "M", "投"),
        (0x1F228, "M", "捕"),
        (0x1F229, "M", "一"),
        (0x1F22A, "M", "三"),
        (0x1F22B, "M", "遊"),
        (0x1F22C, "M", "左"),
        (0x1F22D, "M", "中"),
        (0x1F22E, "M", "右"),
        (0x1F22F, "M", "指"),
        (0x1F230, "M", "走"),
        (0x1F231, "M", "打"),
        (0x1F232, "M", "禁"),
        (0x1F233, "M", "空"),
        (0x1F234, "M", "合"),
        (0x1F235, "M", "満"),
        (0x1F236, "M", "有"),
        (0x1F237, "M", "月"),
        (0x1F238, "M", "申"),
        (0x1F239, "M", "割"),
        (0x1F23A, "M", "営"),
        (0x1F23B, "M", "配"),
        (0x1F23C, "X"),
        (0x1F240, "M", "〔本〕"),
        (0x1F241, "M", "〔三〕"),
        (0x1F242, "M", "〔二〕"),
        (0x1F243, "M", "〔安〕"),
        (0x1F244, "M", "〔点〕"),
        (0x1F245, "M", "〔打〕"),
        (0x1F246, "M", "〔盗〕"),
        (0x1F247, "M", "〔勝〕"),
        (0x1F248, "M", "〔敗〕"),
        (0x1F249, "X"),
        (0x1F250, "M", "得"),
        (0x1F251, "M", "可"),
        (0x1F252, "X"),
        (0x1F260, "V"),
        (0x1F266, "X"),
        (0x1F300, "V"),
        (0x1F6D8, "X"),
        (0x1F6DC, "V"),
        (0x1F6ED, "X"),
        (0x1F6F0, "V"),
        (0x1F6FD, "X"),
        (0x1F700, "V"),
        (0x1F777, "X"),
        (0x1F77B, "V"),
        (0x1F7DA, "X"),
        (0x1F7E0, "V"),
        (0x1F7EC, "X"),
        (0x1F7F0, "V"),
        (0x1F7F1, "X"),
        (0x1F800, "V"),
        (0x1F80C, "X"),
        (0x1F810, "V"),
        (0x1F848, "X"),
        (0x1F850, "V"),
        (0x1F85A, "X"),
        (0x1F860, "V"),
        (0x1F888, "X"),
        (0x1F890, "V"),
        (0x1F8AE, "X"),
        (0x1F8B0, "V"),
        (0x1F8B2, "X"),
        (0x1F900, "V"),
        (0x1FA54, "X"),
        (0x1FA60, "V"),
        (0x1FA6E, "X"),
        (0x1FA70, "V"),
        (0x1FA7D, "X"),
        (0x1FA80, "V"),
        (0x1FA89, "X"),
    ]


def _seg_76() -> List[Union[Tuple[int, str], Tuple[int, str, str]]]:
    return [
        (0x1FA90, "V"),
        (0x1FABE, "X"),
        (0x1FABF, "V"),
        (0x1FAC6, "X"),
        (0x1FACE, "V"),
        (0x1FADC, "X"),
        (0x1FAE0, "V"),
        (0x1FAE9, "X"),
        (0x1FAF0, "V"),
        (0x1FAF9, "X"),
        (0x1FB00, "V"),
        (0x1FB93, "X"),
        (0x1FB94, "V"),
        (0x1FBCB, "X"),
        (0x1FBF0, "M", "0"),
        (0x1FBF1, "M", "1"),
        (0x1FBF2, "M", "2"),
        (0x1FBF3, "M", "3"),
        (0x1FBF4, "M", "4"),
        (0x1FBF5, "M", "5"),
        (0x1FBF6, "M", "6"),
        (0x1FBF7, "M", "7"),
        (0x1FBF8, "M", "8"),
        (0x1FBF9, "M", "9"),
        (0x1FBFA, "X"),
        (0x20000, "V"),
        (0x2A6E0, "X"),
        (0x2A700, "V"),
        (0x2B73A, "X"),
        (0x2B740, "V"),
        (0x2B81E, "X"),
        (0x2B820, "V"),
        (0x2CEA2, "X"),
        (0x2CEB0, "V"),
        (0x2EBE1, "X"),
        (0x2EBF0, "V"),
        (0x2EE5E, "X"),
        (0x2F800, "M", "丽"),
        (0x2F801, "M", "丸"),
        (0x2F802, "M", "乁"),
        (0x2F803, "M", "𠄢"),
        (0x2F804, "M", "你"),
        (0x2F805, "M", "侮"),
        (0x2F806, "M", "侻"),
        (0x2F807, "M", "倂"),
        (0x2F808, "M", "偺"),
        (0x2F809, "M", "備"),
        (0x2F80A, "M", "僧"),
        (0x2F80B, "M", "像"),
        (0x2F80C, "M", "㒞"),
        (0x2F80D, "M", "𠘺"),
        (0x2F80E, "M", "免"),
        (0x2F80F, "M", "兔"),
        (0x2F810, "M", "兤"),
        (0x2F811, "M", "具"),
        (0x2F812, "M", "𠔜"),
        (0x2F813, "M", "㒹"),
        (0x2F814, "M", "內"),
        (0x2F815, "M", "再"),
        (0x2F816, "M", "𠕋"),
        (0x2F817, "M", "冗"),
        (0x2F818, "M", "冤"),
        (0x2F819, "M", "仌"),
        (0x2F81A, "M", "冬"),
        (0x2F81B, "M", "况"),
        (0x2F81C, "M", "𩇟"),
        (0x2F81D, "M", "凵"),
        (0x2F81E, "M", "刃"),
        (0x2F81F, "M", "㓟"),
        (0x2F820, "M", "刻"),
        (0x2F821, "M", "剆"),
        (0x2F822, "M", "割"),
        (0x2F823, "M", "剷"),
        (0x2F824, "M", "㔕"),
        (0x2F825, "M", "勇"),
        (0x2F826, "M", "勉"),
        (0x2F827, "M", "勤"),
        (0x2F828, "M", "勺"),
        (0x2F829, "M", "包"),
        (0x2F82A, "M", "匆"),
        (0x2F82B, "M", "北"),
        (0x2F82C, "M", "卉"),
        (0x2F82D, "M", "卑"),
        (0x2F82E, "M", "博"),
        (0x2F82F, "M", "即"),
        (0x2F830, "M", "卽"),
        (0x2F831, "M", "卿"),
        (0x2F834, "M", "𠨬"),
        (0x2F835, "M", "灰"),
        (0x2F836, "M", "及"),
        (0x2F837, "M", "叟"),
        (0x2F838, "M", "𠭣"),
        (0x2F839, "M", "叫"),
        (0x2F83A, "M", "叱"),
        (0x2F83B, "M", "吆"),
        (0x2F83C, "M", "咞"),
        (0x2F83D, "M", "吸"),
        (0x2F83E, "M", "呈"),
        (0x2F83F, "M", "周"),
        (0x2F840, "M", "咢"),
    ]


def _seg_77() -> List[Union[Tuple[int, str], Tuple[int, str, str]]]:
    return [
        (0x2F841, "M", "哶"),
        (0x2F842, "M", "唐"),
        (0x2F843, "M", "啓"),
        (0x2F844, "M", "啣"),
        (0x2F845, "M", "善"),
        (0x2F847, "M", "喙"),
        (0x2F848, "M", "喫"),
        (0x2F849, "M", "喳"),
        (0x2F84A, "M", "嗂"),
        (0x2F84B, "M", "圖"),
        (0x2F84C, "M", "嘆"),
        (0x2F84D, "M", "圗"),
        (0x2F84E, "M", "噑"),
        (0x2F84F, "M", "噴"),
        (0x2F850, "M", "切"),
        (0x2F851, "M", "壮"),
        (0x2F852, "M", "城"),
        (0x2F853, "M", "埴"),
        (0x2F854, "M", "堍"),
        (0x2F855, "M", "型"),
        (0x2F856, "M", "堲"),
        (0x2F857, "M", "報"),
        (0x2F858, "M", "墬"),
        (0x2F859, "M", "𡓤"),
        (0x2F85A, "M", "売"),
        (0x2F85B, "M", "壷"),
        (0x2F85C, "M", "夆"),
        (0x2F85D, "M", "多"),
        (0x2F85E, "M", "夢"),
        (0x2F85F, "M", "奢"),
        (0x2F860, "M", "𡚨"),
        (0x2F861, "M", "𡛪"),
        (0x2F862, "M", "姬"),
        (0x2F863, "M", "娛"),
        (0x2F864, "M", "娧"),
        (0x2F865, "M", "姘"),
        (0x2F866, "M", "婦"),
        (0x2F867, "M", "㛮"),
        (0x2F868, "X"),
        (0x2F869, "M", "嬈"),
        (0x2F86A, "M", "嬾"),
        (0x2F86C, "M", "𡧈"),
        (0x2F86D, "M", "寃"),
        (0x2F86E, "M", "寘"),
        (0x2F86F, "M", "寧"),
        (0x2F870, "M", "寳"),
        (0x2F871, "M", "𡬘"),
        (0x2F872, "M", "寿"),
        (0x2F873, "M", "将"),
        (0x2F874, "X"),
        (0x2F875, "M", "尢"),
        (0x2F876, "M", "㞁"),
        (0x2F877, "M", "屠"),
        (0x2F878, "M", "屮"),
        (0x2F879, "M", "峀"),
        (0x2F87A, "M", "岍"),
        (0x2F87B, "M", "𡷤"),
        (0x2F87C, "M", "嵃"),
        (0x2F87D, "M", "𡷦"),
        (0x2F87E, "M", "嵮"),
        (0x2F87F, "M", "嵫"),
        (0x2F880, "M", "嵼"),
        (0x2F881, "M", "巡"),
        (0x2F882, "M", "巢"),
        (0x2F883, "M", "㠯"),
        (0x2F884, "M", "巽"),
        (0x2F885, "M", "帨"),
        (0x2F886, "M", "帽"),
        (0x2F887, "M", "幩"),
        (0x2F888, "M", "㡢"),
        (0x2F889, "M", "𢆃"),
        (0x2F88A, "M", "㡼"),
        (0x2F88B, "M", "庰"),
        (0x2F88C, "M", "庳"),
        (0x2F88D, "M", "庶"),
        (0x2F88E, "M", "廊"),
        (0x2F88F, "M", "𪎒"),
        (0x2F890, "M", "廾"),
        (0x2F891, "M", "𢌱"),
        (0x2F893, "M", "舁"),
        (0x2F894, "M", "弢"),
        (0x2F896, "M", "㣇"),
        (0x2F897, "M", "𣊸"),
        (0x2F898, "M", "𦇚"),
        (0x2F899, "M", "形"),
        (0x2F89A, "M", "彫"),
        (0x2F89B, "M", "㣣"),
        (0x2F89C, "M", "徚"),
        (0x2F89D, "M", "忍"),
        (0x2F89E, "M", "志"),
        (0x2F89F, "M", "忹"),
        (0x2F8A0, "M", "悁"),
        (0x2F8A1, "M", "㤺"),
        (0x2F8A2, "M", "㤜"),
        (0x2F8A3, "M", "悔"),
        (0x2F8A4, "M", "𢛔"),
        (0x2F8A5, "M", "惇"),
        (0x2F8A6, "M", "慈"),
        (0x2F8A7, "M", "慌"),
        (0x2F8A8, "M", "慎"),
    ]


def _seg_78() -> List[Union[Tuple[int, str], Tuple[int, str, str]]]:
    return [
        (0x2F8A9, "M", "慌"),
        (0x2F8AA, "M", "慺"),
        (0x2F8AB, "M", "憎"),
        (0x2F8AC, "M", "憲"),
        (0x2F8AD, "M", "憤"),
        (0x2F8AE, "M", "憯"),
        (0x2F8AF, "M", "懞"),
        (0x2F8B0, "M", "懲"),
        (0x2F8B1, "M", "懶"),
        (0x2F8B2, "M", "成"),
        (0x2F8B3, "M", "戛"),
        (0x2F8B4, "M", "扝"),
        (0x2F8B5, "M", "抱"),
        (0x2F8B6, "M", "拔"),
        (0x2F8B7, "M", "捐"),
        (0x2F8B8, "M", "𢬌"),
        (0x2F8B9, "M", "挽"),
        (0x2F8BA, "M", "拼"),
        (0x2F8BB, "M", "捨"),
        (0x2F8BC, "M", "掃"),
        (0x2F8BD, "M", "揤"),
        (0x2F8BE, "M", "𢯱"),
        (0x2F8BF, "M", "搢"),
        (0x2F8C0, "M", "揅"),
        (0x2F8C1, "M", "掩"),
        (0x2F8C2, "M", "㨮"),
        (0x2F8C3, "M", "摩"),
        (0x2F8C4, "M", "摾"),
        (0x2F8C5, "M", "撝"),
        (0x2F8C6, "M", "摷"),
        (0x2F8C7, "M", "㩬"),
        (0x2F8C8, "M", "敏"),
        (0x2F8C9, "M", "敬"),
        (0x2F8CA, "M", "𣀊"),
        (0x2F8CB, "M", "旣"),
        (0x2F8CC, "M", "書"),
        (0x2F8CD, "M", "晉"),
        (0x2F8CE, "M", "㬙"),
        (0x2F8CF, "M", "暑"),
        (0x2F8D0, "M", "㬈"),
        (0x2F8D1, "M", "㫤"),
        (0x2F8D2, "M", "冒"),
        (0x2F8D3, "M", "冕"),
        (0x2F8D4, "M", "最"),
        (0x2F8D5, "M", "暜"),
        (0x2F8D6, "M", "肭"),
        (0x2F8D7, "M", "䏙"),
        (0x2F8D8, "M", "朗"),
        (0x2F8D9, "M", "望"),
        (0x2F8DA, "M", "朡"),
        (0x2F8DB, "M", "杞"),
        (0x2F8DC, "M", "杓"),
        (0x2F8DD, "M", "𣏃"),
        (0x2F8DE, "M", "㭉"),
        (0x2F8DF, "M", "柺"),
        (0x2F8E0, "M", "枅"),
        (0x2F8E1, "M", "桒"),
        (0x2F8E2, "M", "梅"),
        (0x2F8E3, "M", "𣑭"),
        (0x2F8E4, "M", "梎"),
        (0x2F8E5, "M", "栟"),
        (0x2F8E6, "M", "椔"),
        (0x2F8E7, "M", "㮝"),
        (0x2F8E8, "M", "楂"),
        (0x2F8E9, "M", "榣"),
        (0x2F8EA, "M", "槪"),
        (0x2F8EB, "M", "檨"),
        (0x2F8EC, "M", "𣚣"),
        (0x2F8ED, "M", "櫛"),
        (0x2F8EE, "M", "㰘"),
        (0x2F8EF, "M", "次"),
        (0x2F8F0, "M", "𣢧"),
        (0x2F8F1, "M", "歔"),
        (0x2F8F2, "M", "㱎"),
        (0x2F8F3, "M", "歲"),
        (0x2F8F4, "M", "殟"),
        (0x2F8F5, "M", "殺"),
        (0x2F8F6, "M", "殻"),
        (0x2F8F7, "M", "𣪍"),
        (0x2F8F8, "M", "𡴋"),
        (0x2F8F9, "M", "𣫺"),
        (0x2F8FA, "M", "汎"),
        (0x2F8FB, "M", "𣲼"),
        (0x2F8FC, "M", "沿"),
        (0x2F8FD, "M", "泍"),
        (0x2F8FE, "M", "汧"),
        (0x2F8FF, "M", "洖"),
        (0x2F900, "M", "派"),
        (0x2F901, "M", "海"),
        (0x2F902, "M", "流"),
        (0x2F903, "M", "浩"),
        (0x2F904, "M", "浸"),
        (0x2F905, "M", "涅"),
        (0x2F906, "M", "𣴞"),
        (0x2F907, "M", "洴"),
        (0x2F908, "M", "港"),
        (0x2F909, "M", "湮"),
        (0x2F90A, "M", "㴳"),
        (0x2F90B, "M", "滋"),
        (0x2F90C, "M", "滇"),
    ]


def _seg_79() -> List[Union[Tuple[int, str], Tuple[int, str, str]]]:
    return [
        (0x2F90D, "M", "𣻑"),
        (0x2F90E, "M", "淹"),
        (0x2F90F, "M", "潮"),
        (0x2F910, "M", "𣽞"),
        (0x2F911, "M", "𣾎"),
        (0x2F912, "M", "濆"),
        (0x2F913, "M", "瀹"),
        (0x2F914, "M", "瀞"),
        (0x2F915, "M", "瀛"),
        (0x2F916, "M", "㶖"),
        (0x2F917, "M", "灊"),
        (0x2F918, "M", "災"),
        (0x2F919, "M", "灷"),
        (0x2F91A, "M", "炭"),
        (0x2F91B, "M", "𠔥"),
        (0x2F91C, "M", "煅"),
        (0x2F91D, "M", "𤉣"),
        (0x2F91E, "M", "熜"),
        (0x2F91F, "X"),
        (0x2F920, "M", "爨"),
        (0x2F921, "M", "爵"),
        (0x2F922, "M", "牐"),
        (0x2F923, "M", "𤘈"),
        (0x2F924, "M", "犀"),
        (0x2F925, "M", "犕"),
        (0x2F926, "M", "𤜵"),
        (0x2F927, "M", "𤠔"),
        (0x2F928, "M", "獺"),
        (0x2F929, "M", "王"),
        (0x2F92A, "M", "㺬"),
        (0x2F92B, "M", "玥"),
        (0x2F92C, "M", "㺸"),
        (0x2F92E, "M", "瑇"),
        (0x2F92F, "M", "瑜"),
        (0x2F930, "M", "瑱"),
        (0x2F931, "M", "璅"),
        (0x2F932, "M", "瓊"),
        (0x2F933, "M", "㼛"),
        (0x2F934, "M", "甤"),
        (0x2F935, "M", "𤰶"),
        (0x2F936, "M", "甾"),
        (0x2F937, "M", "𤲒"),
        (0x2F938, "M", "異"),
        (0x2F939, "M", "𢆟"),
        (0x2F93A, "M", "瘐"),
        (0x2F93B, "M", "𤾡"),
        (0x2F93C, "M", "𤾸"),
        (0x2F93D, "M", "𥁄"),
        (0x2F93E, "M", "㿼"),
        (0x2F93F, "M", "䀈"),
        (0x2F940, "M", "直"),
        (0x2F941, "M", "𥃳"),
        (0x2F942, "M", "𥃲"),
        (0x2F943, "M", "𥄙"),
        (0x2F944, "M", "𥄳"),
        (0x2F945, "M", "眞"),
        (0x2F946, "M", "真"),
        (0x2F948, "M", "睊"),
        (0x2F949, "M", "䀹"),
        (0x2F94A, "M", "瞋"),
        (0x2F94B, "M", "䁆"),
        (0x2F94C, "M", "䂖"),
        (0x2F94D, "M", "𥐝"),
        (0x2F94E, "M", "硎"),
        (0x2F94F, "M", "碌"),
        (0x2F950, "M", "磌"),
        (0x2F951, "M", "䃣"),
        (0x2F952, "M", "𥘦"),
        (0x2F953, "M", "祖"),
        (0x2F954, "M", "𥚚"),
        (0x2F955, "M", "𥛅"),
        (0x2F956, "M", "福"),
        (0x2F957, "M", "秫"),
        (0x2F958, "M", "䄯"),
        (0x2F959, "M", "穀"),
        (0x2F95A, "M", "穊"),
        (0x2F95B, "M", "穏"),
        (0x2F95C, "M", "𥥼"),
        (0x2F95D, "M", "𥪧"),
        (0x2F95F, "X"),
        (0x2F960, "M", "䈂"),
        (0x2F961, "M", "𥮫"),
        (0x2F962, "M", "篆"),
        (0x2F963, "M", "築"),
        (0x2F964, "M", "䈧"),
        (0x2F965, "M", "𥲀"),
        (0x2F966, "M", "糒"),
        (0x2F967, "M", "䊠"),
        (0x2F968, "M", "糨"),
        (0x2F969, "M", "糣"),
        (0x2F96A, "M", "紀"),
        (0x2F96B, "M", "𥾆"),
        (0x2F96C, "M", "絣"),
        (0x2F96D, "M", "䌁"),
        (0x2F96E, "M", "緇"),
        (0x2F96F, "M", "縂"),
        (0x2F970, "M", "繅"),
        (0x2F971, "M", "䌴"),
        (0x2F972, "M", "𦈨"),
        (0x2F973, "M", "𦉇"),
    ]


def _seg_80() -> List[Union[Tuple[int, str], Tuple[int, str, str]]]:
    return [
        (0x2F974, "M", "䍙"),
        (0x2F975, "M", "𦋙"),
        (0x2F976, "M", "罺"),
        (0x2F977, "M", "𦌾"),
        (0x2F978, "M", "羕"),
        (0x2F979, "M", "翺"),
        (0x2F97A, "M", "者"),
        (0x2F97B, "M", "𦓚"),
        (0x2F97C, "M", "𦔣"),
        (0x2F97D, "M", "聠"),
        (0x2F97E, "M", "𦖨"),
        (0x2F97F, "M", "聰"),
        (0x2F980, "M", "𣍟"),
        (0x2F981, "M", "䏕"),
        (0x2F982, "M", "育"),
        (0x2F983, "M", "脃"),
        (0x2F984, "M", "䐋"),
        (0x2F985, "M", "脾"),
        (0x2F986, "M", "媵"),
        (0x2F987, "M", "𦞧"),
        (0x2F988, "M", "𦞵"),
        (0x2F989, "M", "𣎓"),
        (0x2F98A, "M", "𣎜"),
        (0x2F98B, "M", "舁"),
        (0x2F98C, "M", "舄"),
        (0x2F98D, "M", "辞"),
        (0x2F98E, "M", "䑫"),
        (0x2F98F, "M", "芑"),
        (0x2F990, "M", "芋"),
        (0x2F991, "M", "芝"),
        (0x2F992, "M", "劳"),
        (0x2F993, "M", "花"),
        (0x2F994, "M", "芳"),
        (0x2F995, "M", "芽"),
        (0x2F996, "M", "苦"),
        (0x2F997, "M", "𦬼"),
        (0x2F998, "M", "若"),
        (0x2F999, "M", "茝"),
        (0x2F99A, "M", "荣"),
        (0x2F99B, "M", "莭"),
        (0x2F99C, "M", "茣"),
        (0x2F99D, "M", "莽"),
        (0x2F99E, "M", "菧"),
        (0x2F99F, "M", "著"),
        (0x2F9A0, "M", "荓"),
        (0x2F9A1, "M", "菊"),
        (0x2F9A2, "M", "菌"),
        (0x2F9A3, "M", "菜"),
        (0x2F9A4, "M", "𦰶"),
        (0x2F9A5, "M", "𦵫"),
        (0x2F9A6, "M", "𦳕"),
        (0x2F9A7, "M", "䔫"),
        (0x2F9A8, "M", "蓱"),
        (0x2F9A9, "M", "蓳"),
        (0x2F9AA, "M", "蔖"),
        (0x2F9AB, "M", "𧏊"),
        (0x2F9AC, "M", "蕤"),
        (0x2F9AD, "M", "𦼬"),
        (0x2F9AE, "M", "䕝"),
        (0x2F9AF, "M", "䕡"),
        (0x2F9B0, "M", "𦾱"),
        (0x2F9B1, "M", "𧃒"),
        (0x2F9B2, "M", "䕫"),
        (0x2F9B3, "M", "虐"),
        (0x2F9B4, "M", "虜"),
        (0x2F9B5, "M", "虧"),
        (0x2F9B6, "M", "虩"),
        (0x2F9B7, "M", "蚩"),
        (0x2F9B8, "M", "蚈"),
        (0x2F9B9, "M", "蜎"),
        (0x2F9BA, "M", "蛢"),
        (0x2F9BB, "M", "蝹"),
        (0x2F9BC, "M", "蜨"),
        (0x2F9BD, "M", "蝫"),
        (0x2F9BE, "M", "螆"),
        (0x2F9BF, "X"),
        (0x2F9C0, "M", "蟡"),
        (0x2F9C1, "M", "蠁"),
        (0x2F9C2, "M", "䗹"),
        (0x2F9C3, "M", "衠"),
        (0x2F9C4, "M", "衣"),
        (0x2F9C5, "M", "𧙧"),
        (0x2F9C6, "M", "裗"),
        (0x2F9C7, "M", "裞"),
        (0x2F9C8, "M", "䘵"),
        (0x2F9C9, "M", "裺"),
        (0x2F9CA, "M", "㒻"),
        (0x2F9CB, "M", "𧢮"),
        (0x2F9CC, "M", "𧥦"),
        (0x2F9CD, "M", "䚾"),
        (0x2F9CE, "M", "䛇"),
        (0x2F9CF, "M", "誠"),
        (0x2F9D0, "M", "諭"),
        (0x2F9D1, "M", "變"),
        (0x2F9D2, "M", "豕"),
        (0x2F9D3, "M", "𧲨"),
        (0x2F9D4, "M", "貫"),
        (0x2F9D5, "M", "賁"),
        (0x2F9D6, "M", "贛"),
        (0x2F9D7, "M", "起"),
    ]


def _seg_81() -> List[Union[Tuple[int, str], Tuple[int, str, str]]]:
    return [
        (0x2F9D8, "M", "𧼯"),
        (0x2F9D9, "M", "𠠄"),
        (0x2F9DA, "M", "跋"),
        (0x2F9DB, "M", "趼"),
        (0x2F9DC, "M", "跰"),
        (0x2F9DD, "M", "𠣞"),
        (0x2F9DE, "M", "軔"),
        (0x2F9DF, "M", "輸"),
        (0x2F9E0, "M", "𨗒"),
        (0x2F9E1, "M", "𨗭"),
        (0x2F9E2, "M", "邔"),
        (0x2F9E3, "M", "郱"),
        (0x2F9E4, "M", "鄑"),
        (0x2F9E5, "M", "𨜮"),
        (0x2F9E6, "M", "鄛"),
        (0x2F9E7, "M", "鈸"),
        (0x2F9E8, "M", "鋗"),
        (0x2F9E9, "M", "鋘"),
        (0x2F9EA, "M", "鉼"),
        (0x2F9EB, "M", "鏹"),
        (0x2F9EC, "M", "鐕"),
        (0x2F9ED, "M", "𨯺"),
        (0x2F9EE, "M", "開"),
        (0x2F9EF, "M", "䦕"),
        (0x2F9F0, "M", "閷"),
        (0x2F9F1, "M", "𨵷"),
        (0x2F9F2, "M", "䧦"),
        (0x2F9F3, "M", "雃"),
        (0x2F9F4, "M", "嶲"),
        (0x2F9F5, "M", "霣"),
        (0x2F9F6, "M", "𩅅"),
        (0x2F9F7, "M", "𩈚"),
        (0x2F9F8, "M", "䩮"),
        (0x2F9F9, "M", "䩶"),
        (0x2F9FA, "M", "韠"),
        (0x2F9FB, "M", "𩐊"),
        (0x2F9FC, "M", "䪲"),
        (0x2F9FD, "M", "𩒖"),
        (0x2F9FE, "M", "頋"),
        (0x2FA00, "M", "頩"),
        (0x2FA01, "M", "𩖶"),
        (0x2FA02, "M", "飢"),
        (0x2FA03, "M", "䬳"),
        (0x2FA04, "M", "餩"),
        (0x2FA05, "M", "馧"),
        (0x2FA06, "M", "駂"),
        (0x2FA07, "M", "駾"),
        (0x2FA08, "M", "䯎"),
        (0x2FA09, "M", "𩬰"),
        (0x2FA0A, "M", "鬒"),
        (0x2FA0B, "M", "鱀"),
        (0x2FA0C, "M", "鳽"),
        (0x2FA0D, "M", "䳎"),
        (0x2FA0E, "M", "䳭"),
        (0x2FA0F, "M", "鵧"),
        (0x2FA10, "M", "𪃎"),
        (0x2FA11, "M", "䳸"),
        (0x2FA12, "M", "𪄅"),
        (0x2FA13, "M", "𪈎"),
        (0x2FA14, "M", "𪊑"),
        (0x2FA15, "M", "麻"),
        (0x2FA16, "M", "䵖"),
        (0x2FA17, "M", "黹"),
        (0x2FA18, "M", "黾"),
        (0x2FA19, "M", "鼅"),
        (0x2FA1A, "M", "鼏"),
        (0x2FA1B, "M", "鼖"),
        (0x2FA1C, "M", "鼻"),
        (0x2FA1D, "M", "𪘀"),
        (0x2FA1E, "X"),
        (0x30000, "V"),
        (0x3134B, "X"),
        (0x31350, "V"),
        (0x323B0, "X"),
        (0xE0100, "I"),
        (0xE01F0, "X"),
    ]


uts46data = tuple(
    _seg_0()
    + _seg_1()
    + _seg_2()
    + _seg_3()
    + _seg_4()
    + _seg_5()
    + _seg_6()
    + _seg_7()
    + _seg_8()
    + _seg_9()
    + _seg_10()
    + _seg_11()
    + _seg_12()
    + _seg_13()
    + _seg_14()
    + _seg_15()
    + _seg_16()
    + _seg_17()
    + _seg_18()
    + _seg_19()
    + _seg_20()
    + _seg_21()
    + _seg_22()
    + _seg_23()
    + _seg_24()
    + _seg_25()
    + _seg_26()
    + _seg_27()
    + _seg_28()
    + _seg_29()
    + _seg_30()
    + _seg_31()
    + _seg_32()
    + _seg_33()
    + _seg_34()
    + _seg_35()
    + _seg_36()
    + _seg_37()
    + _seg_38()
    + _seg_39()
    + _seg_40()
    + _seg_41()
    + _seg_42()
    + _seg_43()
    + _seg_44()
    + _seg_45()
    + _seg_46()
    + _seg_47()
    + _seg_48()
    + _seg_49()
    + _seg_50()
    + _seg_51()
    + _seg_52()
    + _seg_53()
    + _seg_54()
    + _seg_55()
    + _seg_56()
    + _seg_57()
    + _seg_58()
    + _seg_59()
    + _seg_60()
    + _seg_61()
    + _seg_62()
    + _seg_63()
    + _seg_64()
    + _seg_65()
    + _seg_66()
    + _seg_67()
    + _seg_68()
    + _seg_69()
    + _seg_70()
    + _seg_71()
    + _seg_72()
    + _seg_73()
    + _seg_74()
    + _seg_75()
    + _seg_76()
    + _seg_77()
    + _seg_78()
    + _seg_79()
    + _seg_80()
    + _seg_81()
)  # type: Tuple[Union[Tuple[int, str], Tuple[int, str, str]], ...]