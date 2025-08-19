
# === NexusCore/openenv\Lib\site-packages\matplotlib\projections\polar.py ===
import math
import types

import numpy as np

import matplotlib as mpl
from matplotlib import _api, cbook
from matplotlib.axes import Axes
import matplotlib.axis as maxis
import matplotlib.markers as mmarkers
import matplotlib.patches as mpatches
from matplotlib.path import Path
import matplotlib.ticker as mticker
import matplotlib.transforms as mtransforms
from matplotlib.spines import Spine


def _apply_theta_transforms_warn():
    _api.warn_deprecated(
                "3.9",
                message=(
                    "Passing `apply_theta_transforms=True` (the default) "
                    "is deprecated since Matplotlib %(since)s. "
                    "Support for this will be removed in Matplotlib in %(removal)s. "
                    "To prevent this warning, set `apply_theta_transforms=False`, "
                    "and make sure to shift theta values before being passed to "
                    "this transform."
                )
            )


class PolarTransform(mtransforms.Transform):
    r"""
    The base polar transform.

    This transform maps polar coordinates :math:`\theta, r` into Cartesian
    coordinates :math:`x, y = r \cos(\theta), r \sin(\theta)`
    (but does not fully transform into Axes coordinates or
    handle positioning in screen space).

    This transformation is designed to be applied to data after any scaling
    along the radial axis (e.g. log-scaling) has been applied to the input
    data.

    Path segments at a fixed radius are automatically transformed to circular
    arcs as long as ``path._interpolation_steps > 1``.
    """

    input_dims = output_dims = 2

    def __init__(self, axis=None, use_rmin=True, *,
                 apply_theta_transforms=True, scale_transform=None):
        """
        Parameters
        ----------
        axis : `~matplotlib.axis.Axis`, optional
            Axis associated with this transform. This is used to get the
            minimum radial limit.
        use_rmin : `bool`, optional
            If ``True``, subtract the minimum radial axis limit before
            transforming to Cartesian coordinates. *axis* must also be
            specified for this to take effect.
        """
        super().__init__()
        self._axis = axis
        self._use_rmin = use_rmin
        self._apply_theta_transforms = apply_theta_transforms
        self._scale_transform = scale_transform
        if apply_theta_transforms:
            _apply_theta_transforms_warn()

    __str__ = mtransforms._make_str_method(
        "_axis",
        use_rmin="_use_rmin",
        apply_theta_transforms="_apply_theta_transforms")

    def _get_rorigin(self):
        # Get lower r limit after being scaled by the radial scale transform
        return self._scale_transform.transform(
            (0, self._axis.get_rorigin()))[1]

    def transform_non_affine(self, values):
        # docstring inherited
        theta, r = np.transpose(values)
        # PolarAxes does not use the theta transforms here, but apply them for
        # backwards-compatibility if not being used by it.
        if self._apply_theta_transforms and self._axis is not None:
            theta *= self._axis.get_theta_direction()
            theta += self._axis.get_theta_offset()
        if self._use_rmin and self._axis is not None:
            r = (r - self._get_rorigin()) * self._axis.get_rsign()
        r = np.where(r >= 0, r, np.nan)
        return np.column_stack([r * np.cos(theta), r * np.sin(theta)])

    def transform_path_non_affine(self, path):
        # docstring inherited
        if not len(path) or path._interpolation_steps == 1:
            return Path(self.transform_non_affine(path.vertices), path.codes)
        xys = []
        codes = []
        last_t = last_r = None
        for trs, c in path.iter_segments():
            trs = trs.reshape((-1, 2))
            if c == Path.LINETO:
                (t, r), = trs
                if t == last_t:  # Same angle: draw a straight line.
                    xys.extend(self.transform_non_affine(trs))
                    codes.append(Path.LINETO)
                elif r == last_r:  # Same radius: draw an arc.
                    # The following is complicated by Path.arc() being
                    # "helpful" and unwrapping the angles, but we don't want
                    # that behavior here.
                    last_td, td = np.rad2deg([last_t, t])
                    if self._use_rmin and self._axis is not None:
                        r = ((r - self._get_rorigin())
                             * self._axis.get_rsign())
                    if last_td <= td:
                        while td - last_td > 360:
                            arc = Path.arc(last_td, last_td + 360)
                            xys.extend(arc.vertices[1:] * r)
                            codes.extend(arc.codes[1:])
                            last_td += 360
                        arc = Path.arc(last_td, td)
                        xys.extend(arc.vertices[1:] * r)
                        codes.extend(arc.codes[1:])
                    else:
                        # The reverse version also relies on the fact that all
                        # codes but the first one are the same.
                        while last_td - td > 360:
                            arc = Path.arc(last_td - 360, last_td)
                            xys.extend(arc.vertices[::-1][1:] * r)
                            codes.extend(arc.codes[1:])
                            last_td -= 360
                        arc = Path.arc(td, last_td)
                        xys.extend(arc.vertices[::-1][1:] * r)
                        codes.extend(arc.codes[1:])
                else:  # Interpolate.
                    trs = cbook.simple_linear_interpolation(
                        np.vstack([(last_t, last_r), trs]),
                        path._interpolation_steps)[1:]
                    xys.extend(self.transform_non_affine(trs))
                    codes.extend([Path.LINETO] * len(trs))
            else:  # Not a straight line.
                xys.extend(self.transform_non_affine(trs))
                codes.extend([c] * len(trs))
            last_t, last_r = trs[-1]
        return Path(xys, codes)

    def inverted(self):
        # docstring inherited
        return PolarAxes.InvertedPolarTransform(
            self._axis, self._use_rmin,
            apply_theta_transforms=self._apply_theta_transforms
        )


class PolarAffine(mtransforms.Affine2DBase):
    r"""
    The affine part of the polar projection.

    Scales the output so that maximum radius rests on the edge of the Axes
    circle and the origin is mapped to (0.5, 0.5). The transform applied is
    the same to x and y components and given by:

    .. math::

        x_{1} = 0.5 \left [ \frac{x_{0}}{(r_{\max} - r_{\min})} + 1 \right ]

    :math:`r_{\min}, r_{\max}` are the minimum and maximum radial limits after
    any scaling (e.g. log scaling) has been removed.
    """
    def __init__(self, scale_transform, limits):
        """
        Parameters
        ----------
        scale_transform : `~matplotlib.transforms.Transform`
            Scaling transform for the data. This is used to remove any scaling
            from the radial view limits.
        limits : `~matplotlib.transforms.BboxBase`
            View limits of the data. The only part of its bounds that is used
            is the y limits (for the radius limits).
        """
        super().__init__()
        self._scale_transform = scale_transform
        self._limits = limits
        self.set_children(scale_transform, limits)
        self._mtx = None

    __str__ = mtransforms._make_str_method("_scale_transform", "_limits")

    def get_matrix(self):
        # docstring inherited
        if self._invalid:
            limits_scaled = self._limits.transformed(self._scale_transform)
            yscale = limits_scaled.ymax - limits_scaled.ymin
            affine = mtransforms.Affine2D() \
                .scale(0.5 / yscale) \
                .translate(0.5, 0.5)
            self._mtx = affine.get_matrix()
            self._inverted = None
            self._invalid = 0
        return self._mtx


class InvertedPolarTransform(mtransforms.Transform):
    """
    The inverse of the polar transform, mapping Cartesian
    coordinate space *x* and *y* back to *theta* and *r*.
    """
    input_dims = output_dims = 2

    def __init__(self, axis=None, use_rmin=True,
                 *, apply_theta_transforms=True):
        """
        Parameters
        ----------
        axis : `~matplotlib.axis.Axis`, optional
            Axis associated with this transform. This is used to get the
            minimum radial limit.
        use_rmin : `bool`, optional
            If ``True``, add the minimum radial axis limit after
            transforming from Cartesian coordinates. *axis* must also be
            specified for this to take effect.
        """
        super().__init__()
        self._axis = axis
        self._use_rmin = use_rmin
        self._apply_theta_transforms = apply_theta_transforms
        if apply_theta_transforms:
            _apply_theta_transforms_warn()

    __str__ = mtransforms._make_str_method(
        "_axis",
        use_rmin="_use_rmin",
        apply_theta_transforms="_apply_theta_transforms")

    def transform_non_affine(self, values):
        # docstring inherited
        x, y = values.T
        r = np.hypot(x, y)
        theta = (np.arctan2(y, x) + 2 * np.pi) % (2 * np.pi)
        # PolarAxes does not use the theta transforms here, but apply them for
        # backwards-compatibility if not being used by it.
        if self._apply_theta_transforms and self._axis is not None:
            theta -= self._axis.get_theta_offset()
            theta *= self._axis.get_theta_direction()
            theta %= 2 * np.pi
        if self._use_rmin and self._axis is not None:
            r += self._axis.get_rorigin()
            r *= self._axis.get_rsign()
        return np.column_stack([theta, r])

    def inverted(self):
        # docstring inherited
        return PolarAxes.PolarTransform(
            self._axis, self._use_rmin,
            apply_theta_transforms=self._apply_theta_transforms
        )


class ThetaFormatter(mticker.Formatter):
    """
    Used to format the *theta* tick labels.  Converts the native
    unit of radians into degrees and adds a degree symbol.
    """

    def __call__(self, x, pos=None):
        vmin, vmax = self.axis.get_view_interval()
        d = np.rad2deg(abs(vmax - vmin))
        digits = max(-int(np.log10(d) - 1.5), 0)
        return f"{np.rad2deg(x):0.{digits}f}\N{DEGREE SIGN}"


class _AxisWrapper:
    def __init__(self, axis):
        self._axis = axis

    def get_view_interval(self):
        return np.rad2deg(self._axis.get_view_interval())

    def set_view_interval(self, vmin, vmax):
        self._axis.set_view_interval(*np.deg2rad((vmin, vmax)))

    def get_minpos(self):
        return np.rad2deg(self._axis.get_minpos())

    def get_data_interval(self):
        return np.rad2deg(self._axis.get_data_interval())

    def set_data_interval(self, vmin, vmax):
        self._axis.set_data_interval(*np.deg2rad((vmin, vmax)))

    def get_tick_space(self):
        return self._axis.get_tick_space()


class ThetaLocator(mticker.Locator):
    """
    Used to locate theta ticks.

    This will work the same as the base locator except in the case that the
    view spans the entire circle. In such cases, the previously used default
    locations of every 45 degrees are returned.
    """

    def __init__(self, base):
        self.base = base
        self.axis = self.base.axis = _AxisWrapper(self.base.axis)

    def set_axis(self, axis):
        self.axis = _AxisWrapper(axis)
        self.base.set_axis(self.axis)

    def __call__(self):
        lim = self.axis.get_view_interval()
        if _is_full_circle_deg(lim[0], lim[1]):
            return np.deg2rad(min(lim)) + np.arange(8) * 2 * np.pi / 8
        else:
            return np.deg2rad(self.base())

    def view_limits(self, vmin, vmax):
        vmin, vmax = np.rad2deg((vmin, vmax))
        return np.deg2rad(self.base.view_limits(vmin, vmax))


class ThetaTick(maxis.XTick):
    """
    A theta-axis tick.

    This subclass of `.XTick` provides angular ticks with some small
    modification to their re-positioning such that ticks are rotated based on
    tick location. This results in ticks that are correctly perpendicular to
    the arc spine.

    When 'auto' rotation is enabled, labels are also rotated to be parallel to
    the spine. The label padding is also applied here since it's not possible
    to use a generic axes transform to produce tick-specific padding.
    """

    def __init__(self, axes, *args, **kwargs):
        self._text1_translate = mtransforms.ScaledTranslation(
            0, 0, axes.get_figure(root=False).dpi_scale_trans)
        self._text2_translate = mtransforms.ScaledTranslation(
            0, 0, axes.get_figure(root=False).dpi_scale_trans)
        super().__init__(axes, *args, **kwargs)
        self.label1.set(
            rotation_mode='anchor',
            transform=self.label1.get_transform() + self._text1_translate)
        self.label2.set(
            rotation_mode='anchor',
            transform=self.label2.get_transform() + self._text2_translate)

    def _apply_params(self, **kwargs):
        super()._apply_params(**kwargs)
        # Ensure transform is correct; sometimes this gets reset.
        trans = self.label1.get_transform()
        if not trans.contains_branch(self._text1_translate):
            self.label1.set_transform(trans + self._text1_translate)
        trans = self.label2.get_transform()
        if not trans.contains_branch(self._text2_translate):
            self.label2.set_transform(trans + self._text2_translate)

    def _update_padding(self, pad, angle):
        padx = pad * np.cos(angle) / 72
        pady = pad * np.sin(angle) / 72
        self._text1_translate._t = (padx, pady)
        self._text1_translate.invalidate()
        self._text2_translate._t = (-padx, -pady)
        self._text2_translate.invalidate()

    def update_position(self, loc):
        super().update_position(loc)
        axes = self.axes
        angle = loc * axes.get_theta_direction() + axes.get_theta_offset()
        text_angle = np.rad2deg(angle) % 360 - 90
        angle -= np.pi / 2

        marker = self.tick1line.get_marker()
        if marker in (mmarkers.TICKUP, '|'):
            trans = mtransforms.Affine2D().scale(1, 1).rotate(angle)
        elif marker == mmarkers.TICKDOWN:
            trans = mtransforms.Affine2D().scale(1, -1).rotate(angle)
        else:
            # Don't modify custom tick line markers.
            trans = self.tick1line._marker._transform
        self.tick1line._marker._transform = trans

        marker = self.tick2line.get_marker()
        if marker in (mmarkers.TICKUP, '|'):
            trans = mtransforms.Affine2D().scale(1, 1).rotate(angle)
        elif marker == mmarkers.TICKDOWN:
            trans = mtransforms.Affine2D().scale(1, -1).rotate(angle)
        else:
            # Don't modify custom tick line markers.
            trans = self.tick2line._marker._transform
        self.tick2line._marker._transform = trans

        mode, user_angle = self._labelrotation
        if mode == 'default':
            text_angle = user_angle
        else:
            if text_angle > 90:
                text_angle -= 180
            elif text_angle < -90:
                text_angle += 180
            text_angle += user_angle
        self.label1.set_rotation(text_angle)
        self.label2.set_rotation(text_angle)

        # This extra padding helps preserve the look from previous releases but
        # is also needed because labels are anchored to their center.
        pad = self._pad + 7
        self._update_padding(pad,
                             self._loc * axes.get_theta_direction() +
                             axes.get_theta_offset())


class ThetaAxis(maxis.XAxis):
    """
    A theta Axis.

    This overrides certain properties of an `.XAxis` to provide special-casing
    for an angular axis.
    """
    __name__ = 'thetaaxis'
    axis_name = 'theta'  #: Read-only name identifying the axis.
    _tick_class = ThetaTick

    def _wrap_locator_formatter(self):
        self.set_major_locator(ThetaLocator(self.get_major_locator()))
        self.set_major_formatter(ThetaFormatter())
        self.isDefault_majloc = True
        self.isDefault_majfmt = True

    def clear(self):
        # docstring inherited
        super().clear()
        self.set_ticks_position('none')
        self._wrap_locator_formatter()

    def _set_scale(self, value, **kwargs):
        if value != 'linear':
            raise NotImplementedError(
                "The xscale cannot be set on a polar plot")
        super()._set_scale(value, **kwargs)
        # LinearScale.set_default_locators_and_formatters just set the major
        # locator to be an AutoLocator, so we customize it here to have ticks
        # at sensible degree multiples.
        self.get_major_locator().set_params(steps=[1, 1.5, 3, 4.5, 9, 10])
        self._wrap_locator_formatter()

    def _copy_tick_props(self, src, dest):
        """Copy the props from src tick to dest tick."""
        if src is None or dest is None:
            return
        super()._copy_tick_props(src, dest)

        # Ensure that tick transforms are independent so that padding works.
        trans = dest._get_text1_transform()[0]
        dest.label1.set_transform(trans + dest._text1_translate)
        trans = dest._get_text2_transform()[0]
        dest.label2.set_transform(trans + dest._text2_translate)


class RadialLocator(mticker.Locator):
    """
    Used to locate radius ticks.

    Ensures that all ticks are strictly positive.  For all other tasks, it
    delegates to the base `.Locator` (which may be different depending on the
    scale of the *r*-axis).
    """

    def __init__(self, base, axes=None):
        self.base = base
        self._axes = axes

    def set_axis(self, axis):
        self.base.set_axis(axis)

    def __call__(self):
        # Ensure previous behaviour with full circle non-annular views.
        if self._axes:
            if _is_full_circle_rad(*self._axes.viewLim.intervalx):
                rorigin = self._axes.get_rorigin() * self._axes.get_rsign()
                if self._axes.get_rmin() <= rorigin:
                    return [tick for tick in self.base() if tick > rorigin]
        return self.base()

    def _zero_in_bounds(self):
        """
        Return True if zero is within the valid values for the
        scale of the radial axis.
        """
        vmin, vmax = self._axes.yaxis._scale.limit_range_for_scale(0, 1, 1e-5)
        return vmin == 0

    def nonsingular(self, vmin, vmax):
        # docstring inherited
        if self._zero_in_bounds() and (vmin, vmax) == (-np.inf, np.inf):
            # Initial view limits
            return (0, 1)
        else:
            return self.base.nonsingular(vmin, vmax)

    def view_limits(self, vmin, vmax):
        vmin, vmax = self.base.view_limits(vmin, vmax)
        if self._zero_in_bounds() and vmax > vmin:
            # this allows inverted r/y-lims
            vmin = min(0, vmin)
        return mtransforms.nonsingular(vmin, vmax)


class _ThetaShift(mtransforms.ScaledTranslation):
    """
    Apply a padding shift based on axes theta limits.

    This is used to create padding for radial ticks.

    Parameters
    ----------
    axes : `~matplotlib.axes.Axes`
        The owning Axes; used to determine limits.
    pad : float
        The padding to apply, in points.
    mode : {'min', 'max', 'rlabel'}
        Whether to shift away from the start (``'min'``) or the end (``'max'``)
        of the axes, or using the rlabel position (``'rlabel'``).
    """
    def __init__(self, axes, pad, mode):
        super().__init__(pad, pad, axes.get_figure(root=False).dpi_scale_trans)
        self.set_children(axes._realViewLim)
        self.axes = axes
        self.mode = mode
        self.pad = pad

    __str__ = mtransforms._make_str_method("axes", "pad", "mode")

    def get_matrix(self):
        if self._invalid:
            if self.mode == 'rlabel':
                angle = (
                    np.deg2rad(self.axes.get_rlabel_position()
                               * self.axes.get_theta_direction())
                    + self.axes.get_theta_offset()
                    - np.pi / 2
                )
            elif self.mode == 'min':
                angle = self.axes._realViewLim.xmin - np.pi / 2
            elif self.mode == 'max':
                angle = self.axes._realViewLim.xmax + np.pi / 2
            self._t = (self.pad * np.cos(angle) / 72, self.pad * np.sin(angle) / 72)
        return super().get_matrix()


class RadialTick(maxis.YTick):
    """
    A radial-axis tick.

    This subclass of `.YTick` provides radial ticks with some small
    modification to their re-positioning such that ticks are rotated based on
    axes limits.  This results in ticks that are correctly perpendicular to
    the spine. Labels are also rotated to be perpendicular to the spine, when
    'auto' rotation is enabled.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.label1.set_rotation_mode('anchor')
        self.label2.set_rotation_mode('anchor')

    def _determine_anchor(self, mode, angle, start):
        # Note: angle is the (spine angle - 90) because it's used for the tick
        # & text setup, so all numbers below are -90 from (normed) spine angle.
        if mode == 'auto':
            if start:
                if -90 <= angle <= 90:
                    return 'left', 'center'
                else:
                    return 'right', 'center'
            else:
                if -90 <= angle <= 90:
                    return 'right', 'center'
                else:
                    return 'left', 'center'
        else:
            if start:
                if angle < -68.5:
                    return 'center', 'top'
                elif angle < -23.5:
                    return 'left', 'top'
                elif angle < 22.5:
                    return 'left', 'center'
                elif angle < 67.5:
                    return 'left', 'bottom'
                elif angle < 112.5:
                    return 'center', 'bottom'
                elif angle < 157.5:
                    return 'right', 'bottom'
                elif angle < 202.5:
                    return 'right', 'center'
                elif angle < 247.5:
                    return 'right', 'top'
                else:
                    return 'center', 'top'
            else:
                if angle < -68.5:
                    return 'center', 'bottom'
                elif angle < -23.5:
                    return 'right', 'bottom'
                elif angle < 22.5:
                    return 'right', 'center'
                elif angle < 67.5:
                    return 'right', 'top'
                elif angle < 112.5:
                    return 'center', 'top'
                elif angle < 157.5:
                    return 'left', 'top'
                elif angle < 202.5:
                    return 'left', 'center'
                elif angle < 247.5:
                    return 'left', 'bottom'
                else:
                    return 'center', 'bottom'

    def update_position(self, loc):
        super().update_position(loc)
        axes = self.axes
        thetamin = axes.get_thetamin()
        thetamax = axes.get_thetamax()
        direction = axes.get_theta_direction()
        offset_rad = axes.get_theta_offset()
        offset = np.rad2deg(offset_rad)
        full = _is_full_circle_deg(thetamin, thetamax)

        if full:
            angle = (axes.get_rlabel_position() * direction +
                     offset) % 360 - 90
            tick_angle = 0
        else:
            angle = (thetamin * direction + offset) % 360 - 90
            if direction > 0:
                tick_angle = np.deg2rad(angle)
            else:
                tick_angle = np.deg2rad(angle + 180)
        text_angle = (angle + 90) % 180 - 90  # between -90 and +90.
        mode, user_angle = self._labelrotation
        if mode == 'auto':
            text_angle += user_angle
        else:
            text_angle = user_angle

        if full:
            ha = self.label1.get_horizontalalignment()
            va = self.label1.get_verticalalignment()
        else:
            ha, va = self._determine_anchor(mode, angle, direction > 0)
        self.label1.set_horizontalalignment(ha)
        self.label1.set_verticalalignment(va)
        self.label1.set_rotation(text_angle)

        marker = self.tick1line.get_marker()
        if marker == mmarkers.TICKLEFT:
            trans = mtransforms.Affine2D().rotate(tick_angle)
        elif marker == '_':
            trans = mtransforms.Affine2D().rotate(tick_angle + np.pi / 2)
        elif marker == mmarkers.TICKRIGHT:
            trans = mtransforms.Affine2D().scale(-1, 1).rotate(tick_angle)
        else:
            # Don't modify custom tick line markers.
            trans = self.tick1line._marker._transform
        self.tick1line._marker._transform = trans

        if full:
            self.label2.set_visible(False)
            self.tick2line.set_visible(False)
        angle = (thetamax * direction + offset) % 360 - 90
        if direction > 0:
            tick_angle = np.deg2rad(angle)
        else:
            tick_angle = np.deg2rad(angle + 180)
        text_angle = (angle + 90) % 180 - 90  # between -90 and +90.
        mode, user_angle = self._labelrotation
        if mode == 'auto':
            text_angle += user_angle
        else:
            text_angle = user_angle

        ha, va = self._determine_anchor(mode, angle, direction < 0)
        self.label2.set_ha(ha)
        self.label2.set_va(va)
        self.label2.set_rotation(text_angle)

        marker = self.tick2line.get_marker()
        if marker == mmarkers.TICKLEFT:
            trans = mtransforms.Affine2D().rotate(tick_angle)
        elif marker == '_':
            trans = mtransforms.Affine2D().rotate(tick_angle + np.pi / 2)
        elif marker == mmarkers.TICKRIGHT:
            trans = mtransforms.Affine2D().scale(-1, 1).rotate(tick_angle)
        else:
            # Don't modify custom tick line markers.
            trans = self.tick2line._marker._transform
        self.tick2line._marker._transform = trans


class RadialAxis(maxis.YAxis):
    """
    A radial Axis.

    This overrides certain properties of a `.YAxis` to provide special-casing
    for a radial axis.
    """
    __name__ = 'radialaxis'
    axis_name = 'radius'  #: Read-only name identifying the axis.
    _tick_class = RadialTick

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.sticky_edges.y.append(0)

    def _wrap_locator_formatter(self):
        self.set_major_locator(RadialLocator(self.get_major_locator(),
                                             self.axes))
        self.isDefault_majloc = True

    def clear(self):
        # docstring inherited
        super().clear()
        self.set_ticks_position('none')
        self._wrap_locator_formatter()

    def _set_scale(self, value, **kwargs):
        super()._set_scale(value, **kwargs)
        self._wrap_locator_formatter()


def _is_full_circle_deg(thetamin, thetamax):
    """
    Determine if a wedge (in degrees) spans the full circle.

    The condition is derived from :class:`~matplotlib.patches.Wedge`.
    """
    return abs(abs(thetamax - thetamin) - 360.0) < 1e-12


def _is_full_circle_rad(thetamin, thetamax):
    """
    Determine if a wedge (in radians) spans the full circle.

    The condition is derived from :class:`~matplotlib.patches.Wedge`.
    """
    return abs(abs(thetamax - thetamin) - 2 * np.pi) < 1.74e-14


class _WedgeBbox(mtransforms.Bbox):
    """
    Transform (theta, r) wedge Bbox into Axes bounding box.

    Parameters
    ----------
    center : (float, float)
        Center of the wedge
    viewLim : `~matplotlib.transforms.Bbox`
        Bbox determining the boundaries of the wedge
    originLim : `~matplotlib.transforms.Bbox`
        Bbox determining the origin for the wedge, if different from *viewLim*
    """
    def __init__(self, center, viewLim, originLim, **kwargs):
        super().__init__([[0, 0], [1, 1]], **kwargs)
        self._center = center
        self._viewLim = viewLim
        self._originLim = originLim
        self.set_children(viewLim, originLim)

    __str__ = mtransforms._make_str_method("_center", "_viewLim", "_originLim")

    def get_points(self):
        # docstring inherited
        if self._invalid:
            points = self._viewLim.get_points().copy()
            # Scale angular limits to work with Wedge.
            points[:, 0] *= 180 / np.pi
            if points[0, 0] > points[1, 0]:
                points[:, 0] = points[::-1, 0]

            # Scale radial limits based on origin radius.
            points[:, 1] -= self._originLim.y0

            # Scale radial limits to match axes limits.
            rscale = 0.5 / points[1, 1]
            points[:, 1] *= rscale
            width = min(points[1, 1] - points[0, 1], 0.5)

            # Generate bounding box for wedge.
            wedge = mpatches.Wedge(self._center, points[1, 1],
                                   points[0, 0], points[1, 0],
                                   width=width)
            self.update_from_path(wedge.get_path())

            # Ensure equal aspect ratio.
            w, h = self._points[1] - self._points[0]
            deltah = max(w - h, 0) / 2
            deltaw = max(h - w, 0) / 2
            self._points += np.array([[-deltaw, -deltah], [deltaw, deltah]])

            self._invalid = 0

        return self._points


class PolarAxes(Axes):
    """
    A polar graph projection, where the input dimensions are *theta*, *r*.

    Theta starts pointing east and goes anti-clockwise.
    """
    name = 'polar'

    def __init__(self, *args,
                 theta_offset=0, theta_direction=1, rlabel_position=22.5,
                 **kwargs):
        # docstring inherited
        self._default_theta_offset = theta_offset
        self._default_theta_direction = theta_direction
        self._default_rlabel_position = np.deg2rad(rlabel_position)
        super().__init__(*args, **kwargs)
        self.use_sticky_edges = True
        self.set_aspect('equal', adjustable='box', anchor='C')
        self.clear()

    def clear(self):
        # docstring inherited
        super().clear()

        self.title.set_y(1.05)

        start = self.spines.get('start', None)
        if start:
            start.set_visible(False)
        end = self.spines.get('end', None)
        if end:
            end.set_visible(False)
        self.set_xlim(0.0, 2 * np.pi)

        self.grid(mpl.rcParams['polaraxes.grid'])
        inner = self.spines.get('inner', None)
        if inner:
            inner.set_visible(False)

        self.set_rorigin(None)
        self.set_theta_offset(self._default_theta_offset)
        self.set_theta_direction(self._default_theta_direction)

    def _init_axis(self):
        # This is moved out of __init__ because non-separable axes don't use it
        self.xaxis = ThetaAxis(self, clear=False)
        self.yaxis = RadialAxis(self, clear=False)
        self.spines['polar'].register_axis(self.yaxis)

    def _set_lim_and_transforms(self):
        # A view limit where the minimum radius can be locked if the user
        # specifies an alternate origin.
        self._originViewLim = mtransforms.LockableBbox(self.viewLim)

        # Handle angular offset and direction.
        self._direction = mtransforms.Affine2D() \
            .scale(self._default_theta_direction, 1.0)
        self._theta_offset = mtransforms.Affine2D() \
            .translate(self._default_theta_offset, 0.0)
        self.transShift = self._direction + self._theta_offset
        # A view limit shifted to the correct location after accounting for
        # orientation and offset.
        self._realViewLim = mtransforms.TransformedBbox(self.viewLim,
                                                        self.transShift)

        # Transforms the x and y axis separately by a scale factor
        # It is assumed that this part will have non-linear components
        self.transScale = mtransforms.TransformWrapper(
            mtransforms.IdentityTransform())

        # Scale view limit into a bbox around the selected wedge. This may be
        # smaller than the usual unit axes rectangle if not plotting the full
        # circle.
        self.axesLim = _WedgeBbox((0.5, 0.5),
                                  self._realViewLim, self._originViewLim)

        # Scale the wedge to fill the axes.
        self.transWedge = mtransforms.BboxTransformFrom(self.axesLim)

        # Scale the axes to fill the figure.
        self.transAxes = mtransforms.BboxTransformTo(self.bbox)

        # A (possibly non-linear) projection on the (already scaled)
        # data.  This one is aware of rmin
        self.transProjection = self.PolarTransform(
            self,
            apply_theta_transforms=False,
            scale_transform=self.transScale
        )
        # Add dependency on rorigin.
        self.transProjection.set_children(self._originViewLim)

        # An affine transformation on the data, generally to limit the
        # range of the axes
        self.transProjectionAffine = self.PolarAffine(self.transScale,
                                                      self._originViewLim)

        # The complete data transformation stack -- from data all the
        # way to display coordinates
        #
        # 1. Remove any radial axis scaling (e.g. log scaling)
        # 2. Shift data in the theta direction
        # 3. Project the data from polar to cartesian values
        #    (with the origin in the same place)
        # 4. Scale and translate the cartesian values to Axes coordinates
        #    (here the origin is moved to the lower left of the Axes)
        # 5. Move and scale to fill the Axes
        # 6. Convert from Axes coordinates to Figure coordinates
        self.transData = (
            self.transScale +
            self.transShift +
            self.transProjection +
            (
                self.transProjectionAffine +
                self.transWedge +
                self.transAxes
            )
        )

        # This is the transform for theta-axis ticks.  It is
        # equivalent to transData, except it always puts r == 0.0 and r == 1.0
        # at the edge of the axis circles.
        self._xaxis_transform = (
            mtransforms.blended_transform_factory(
                mtransforms.IdentityTransform(),
                mtransforms.BboxTransformTo(self.viewLim)) +
            self.transData)
        # The theta labels are flipped along the radius, so that text 1 is on
        # the outside by default. This should work the same as before.
        flipr_transform = mtransforms.Affine2D() \
            .translate(0.0, -0.5) \
            .scale(1.0, -1.0) \
            .translate(0.0, 0.5)
        self._xaxis_text_transform = flipr_transform + self._xaxis_transform

        # This is the transform for r-axis ticks.  It scales the theta
        # axis so the gridlines from 0.0 to 1.0, now go from thetamin to
        # thetamax.
        self._yaxis_transform = (
            mtransforms.blended_transform_factory(
                mtransforms.BboxTransformTo(self.viewLim),
                mtransforms.IdentityTransform()) +
            self.transData)
        # The r-axis labels are put at an angle and padded in the r-direction
        self._r_label_position = mtransforms.Affine2D() \
            .translate(self._default_rlabel_position, 0.0)
        self._yaxis_text_transform = mtransforms.TransformWrapper(
            self._r_label_position + self.transData)

    def get_xaxis_transform(self, which='grid'):
        _api.check_in_list(['tick1', 'tick2', 'grid'], which=which)
        return self._xaxis_transform

    def get_xaxis_text1_transform(self, pad):
        return self._xaxis_text_transform, 'center', 'center'

    def get_xaxis_text2_transform(self, pad):
        return self._xaxis_text_transform, 'center', 'center'

    def get_yaxis_transform(self, which='grid'):
        if which in ('tick1', 'tick2'):
            return self._yaxis_text_transform
        elif which == 'grid':
            return self._yaxis_transform
        else:
            _api.check_in_list(['tick1', 'tick2', 'grid'], which=which)

    def get_yaxis_text1_transform(self, pad):
        thetamin, thetamax = self._realViewLim.intervalx
        if _is_full_circle_rad(thetamin, thetamax):
            return self._yaxis_text_transform, 'bottom', 'left'
        elif self.get_theta_direction() > 0:
            halign = 'left'
            pad_shift = _ThetaShift(self, pad, 'min')
        else:
            halign = 'right'
            pad_shift = _ThetaShift(self, pad, 'max')
        return self._yaxis_text_transform + pad_shift, 'center', halign

    def get_yaxis_text2_transform(self, pad):
        if self.get_theta_direction() > 0:
            halign = 'right'
            pad_shift = _ThetaShift(self, pad, 'max')
        else:
            halign = 'left'
            pad_shift = _ThetaShift(self, pad, 'min')
        return self._yaxis_text_transform + pad_shift, 'center', halign

    def draw(self, renderer):
        self._unstale_viewLim()
        thetamin, thetamax = np.rad2deg(self._realViewLim.intervalx)
        if thetamin > thetamax:
            thetamin, thetamax = thetamax, thetamin
        rmin, rmax = ((self._realViewLim.intervaly - self.get_rorigin()) *
                      self.get_rsign())
        if isinstance(self.patch, mpatches.Wedge):
            # Backwards-compatibility: Any subclassed Axes might override the
            # patch to not be the Wedge that PolarAxes uses.
            center = self.transWedge.transform((0.5, 0.5))
            self.patch.set_center(center)
            self.patch.set_theta1(thetamin)
            self.patch.set_theta2(thetamax)

            edge, _ = self.transWedge.transform((1, 0))
            radius = edge - center[0]
            width = min(radius * (rmax - rmin) / rmax, radius)
            self.patch.set_radius(radius)
            self.patch.set_width(width)

            inner_width = radius - width
            inner = self.spines.get('inner', None)
            if inner:
                inner.set_visible(inner_width != 0.0)

        visible = not _is_full_circle_deg(thetamin, thetamax)
        # For backwards compatibility, any subclassed Axes might override the
        # spines to not include start/end that PolarAxes uses.
        start = self.spines.get('start', None)
        end = self.spines.get('end', None)
        if start:
            start.set_visible(visible)
        if end:
            end.set_visible(visible)
        if visible:
            yaxis_text_transform = self._yaxis_transform
        else:
            yaxis_text_transform = self._r_label_position + self.transData
        if self._yaxis_text_transform != yaxis_text_transform:
            self._yaxis_text_transform.set(yaxis_text_transform)
            self.yaxis.reset_ticks()
            self.yaxis.set_clip_path(self.patch)

        super().draw(renderer)

    def _gen_axes_patch(self):
        return mpatches.Wedge((0.5, 0.5), 0.5, 0.0, 360.0)

    def _gen_axes_spines(self):
        spines = {
            'polar': Spine.arc_spine(self, 'top', (0.5, 0.5), 0.5, 0, 360),
            'start': Spine.linear_spine(self, 'left'),
            'end': Spine.linear_spine(self, 'right'),
            'inner': Spine.arc_spine(self, 'bottom', (0.5, 0.5), 0.0, 0, 360),
        }
        spines['polar'].set_transform(self.transWedge + self.transAxes)
        spines['inner'].set_transform(self.transWedge + self.transAxes)
        spines['start'].set_transform(self._yaxis_transform)
        spines['end'].set_transform(self._yaxis_transform)
        return spines

    def set_thetamax(self, thetamax):
        """Set the maximum theta limit in degrees."""
        self.viewLim.x1 = np.deg2rad(thetamax)

    def get_thetamax(self):
        """Return the maximum theta limit in degrees."""
        return np.rad2deg(self.viewLim.xmax)

    def set_thetamin(self, thetamin):
        """Set the minimum theta limit in degrees."""
        self.viewLim.x0 = np.deg2rad(thetamin)

    def get_thetamin(self):
        """Get the minimum theta limit in degrees."""
        return np.rad2deg(self.viewLim.xmin)

    def set_thetalim(self, *args, **kwargs):
        r"""
        Set the minimum and maximum theta values.

        Can take the following signatures:

        - ``set_thetalim(minval, maxval)``: Set the limits in radians.
        - ``set_thetalim(thetamin=minval, thetamax=maxval)``: Set the limits
          in degrees.

        where minval and maxval are the minimum and maximum limits. Values are
        wrapped in to the range :math:`[0, 2\pi]` (in radians), so for example
        it is possible to do ``set_thetalim(-np.pi / 2, np.pi / 2)`` to have
        an axis symmetric around 0. A ValueError is raised if the absolute
        angle difference is larger than a full circle.
        """
        orig_lim = self.get_xlim()  # in radians
        if 'thetamin' in kwargs:
            kwargs['xmin'] = np.deg2rad(kwargs.pop('thetamin'))
        if 'thetamax' in kwargs:
            kwargs['xmax'] = np.deg2rad(kwargs.pop('thetamax'))
        new_min, new_max = self.set_xlim(*args, **kwargs)
        # Parsing all permutations of *args, **kwargs is tricky; it is simpler
        # to let set_xlim() do it and then validate the limits.
        if abs(new_max - new_min) > 2 * np.pi:
            self.set_xlim(orig_lim)  # un-accept the change
            raise ValueError("The angle range must be less than a full circle")
        return tuple(np.rad2deg((new_min, new_max)))

    def set_theta_offset(self, offset):
        """
        Set the offset for the location of 0 in radians.
        """
        mtx = self._theta_offset.get_matrix()
        mtx[0, 2] = offset
        self._theta_offset.invalidate()

    def get_theta_offset(self):
        """
        Get the offset for the location of 0 in radians.
        """
        return self._theta_offset.get_matrix()[0, 2]

    def set_theta_zero_location(self, loc, offset=0.0):
        """
        Set the location of theta's zero.

        This simply calls `set_theta_offset` with the correct value in radians.

        Parameters
        ----------
        loc : str
            May be one of "N", "NW", "W", "SW", "S", "SE", "E", or "NE".
        offset : float, default: 0
            An offset in degrees to apply from the specified *loc*. **Note:**
            this offset is *always* applied counter-clockwise regardless of
            the direction setting.
        """
        mapping = {
            'N': np.pi * 0.5,
            'NW': np.pi * 0.75,
            'W': np.pi,
            'SW': np.pi * 1.25,
            'S': np.pi * 1.5,
            'SE': np.pi * 1.75,
            'E': 0,
            'NE': np.pi * 0.25}
        return self.set_theta_offset(mapping[loc] + np.deg2rad(offset))

    def set_theta_direction(self, direction):
        """
        Set the direction in which theta increases.

        clockwise, -1:
           Theta increases in the clockwise direction

        counterclockwise, anticlockwise, 1:
           Theta increases in the counterclockwise direction
        """
        mtx = self._direction.get_matrix()
        if direction in ('clockwise', -1):
            mtx[0, 0] = -1
        elif direction in ('counterclockwise', 'anticlockwise', 1):
            mtx[0, 0] = 1
        else:
            _api.check_in_list(
                [-1, 1, 'clockwise', 'counterclockwise', 'anticlockwise'],
                direction=direction)
        self._direction.invalidate()

    def get_theta_direction(self):
        """
        Get the direction in which theta increases.

        -1:
           Theta increases in the clockwise direction

        1:
           Theta increases in the counterclockwise direction
        """
        return self._direction.get_matrix()[0, 0]

    def set_rmax(self, rmax):
        """
        Set the outer radial limit.

        Parameters
        ----------
        rmax : float
        """
        self.viewLim.y1 = rmax

    def get_rmax(self):
        """
        Returns
        -------
        float
            Outer radial limit.
        """
        return self.viewLim.ymax

    def set_rmin(self, rmin):
        """
        Set the inner radial limit.

        Parameters
        ----------
        rmin : float
        """
        self.viewLim.y0 = rmin

    def get_rmin(self):
        """
        Returns
        -------
        float
            The inner radial limit.
        """
        return self.viewLim.ymin

    def set_rorigin(self, rorigin):
        """
        Update the radial origin.

        Parameters
        ----------
        rorigin : float
        """
        self._originViewLim.locked_y0 = rorigin

    def get_rorigin(self):
        """
        Returns
        -------
        float
        """
        return self._originViewLim.y0

    def get_rsign(self):
        return np.sign(self._originViewLim.y1 - self._originViewLim.y0)

    def set_rlim(self, bottom=None, top=None, *,
                 emit=True, auto=False, **kwargs):
        """
        Set the radial axis view limits.

        This function behaves like `.Axes.set_ylim`, but additionally supports
        *rmin* and *rmax* as aliases for *bottom* and *top*.

        See Also
        --------
        .Axes.set_ylim
        """
        if 'rmin' in kwargs:
            if bottom is None:
                bottom = kwargs.pop('rmin')
            else:
                raise ValueError('Cannot supply both positional "bottom"'
                                 'argument and kwarg "rmin"')
        if 'rmax' in kwargs:
            if top is None:
                top = kwargs.pop('rmax')
            else:
                raise ValueError('Cannot supply both positional "top"'
                                 'argument and kwarg "rmax"')
        return self.set_ylim(bottom=bottom, top=top, emit=emit, auto=auto,
                             **kwargs)

    def get_rlabel_position(self):
        """
        Returns
        -------
        float
            The theta position of the radius labels in degrees.
        """
        return np.rad2deg(self._r_label_position.get_matrix()[0, 2])

    def set_rlabel_position(self, value):
        """
        Update the theta position of the radius labels.

        Parameters
        ----------
        value : number
            The angular position of the radius labels in degrees.
        """
        self._r_label_position.clear().translate(np.deg2rad(value), 0.0)

    def set_yscale(self, *args, **kwargs):
        super().set_yscale(*args, **kwargs)
        self.yaxis.set_major_locator(
            self.RadialLocator(self.yaxis.get_major_locator(), self))

    def set_rscale(self, *args, **kwargs):
        return Axes.set_yscale(self, *args, **kwargs)

    def set_rticks(self, *args, **kwargs):
        return Axes.set_yticks(self, *args, **kwargs)

    def set_thetagrids(self, angles, labels=None, fmt=None, **kwargs):
        """
        Set the theta gridlines in a polar plot.

        Parameters
        ----------
        angles : tuple with floats, degrees
            The angles of the theta gridlines.

        labels : tuple with strings or None
            The labels to use at each theta gridline. The
            `.projections.polar.ThetaFormatter` will be used if None.

        fmt : str or None
            Format string used in `matplotlib.ticker.FormatStrFormatter`.
            For example '%f'. Note that the angle that is used is in
            radians.

        Returns
        -------
        lines : list of `.lines.Line2D`
            The theta gridlines.

        labels : list of `.text.Text`
            The tick labels.

        Other Parameters
        ----------------
        **kwargs
            *kwargs* are optional `.Text` properties for the labels.

            .. warning::

                This only sets the properties of the current ticks.
                Ticks are not guaranteed to be persistent. Various operations
                can create, delete and modify the Tick instances. There is an
                imminent risk that these settings can get lost if you work on
                the figure further (including also panning/zooming on a
                displayed figure).

                Use `.set_tick_params` instead if possible.

        See Also
        --------
        .PolarAxes.set_rgrids
        .Axis.get_gridlines
        .Axis.get_ticklabels
        """

        # Make sure we take into account unitized data
        angles = self.convert_yunits(angles)
        angles = np.deg2rad(angles)
        self.set_xticks(angles)
        if labels is not None:
            self.set_xticklabels(labels)
        elif fmt is not None:
            self.xaxis.set_major_formatter(mticker.FormatStrFormatter(fmt))
        for t in self.xaxis.get_ticklabels():
            t._internal_update(kwargs)
        return self.xaxis.get_ticklines(), self.xaxis.get_ticklabels()

    def set_rgrids(self, radii, labels=None, angle=None, fmt=None, **kwargs):
        """
        Set the radial gridlines on a polar plot.

        Parameters
        ----------
        radii : tuple with floats
            The radii for the radial gridlines

        labels : tuple with strings or None
            The labels to use at each radial gridline. The
            `matplotlib.ticker.ScalarFormatter` will be used if None.

        angle : float
            The angular position of the radius labels in degrees.

        fmt : str or None
            Format string used in `matplotlib.ticker.FormatStrFormatter`.
            For example '%f'.

        Returns
        -------
        lines : list of `.lines.Line2D`
            The radial gridlines.

        labels : list of `.text.Text`
            The tick labels.

        Other Parameters
        ----------------
        **kwargs
            *kwargs* are optional `.Text` properties for the labels.

            .. warning::

                This only sets the properties of the current ticks.
                Ticks are not guaranteed to be persistent. Various operations
                can create, delete and modify the Tick instances. There is an
                imminent risk that these settings can get lost if you work on
                the figure further (including also panning/zooming on a
                displayed figure).

                Use `.set_tick_params` instead if possible.

        See Also
        --------
        .PolarAxes.set_thetagrids
        .Axis.get_gridlines
        .Axis.get_ticklabels
        """
        # Make sure we take into account unitized data
        radii = self.convert_xunits(radii)
        radii = np.asarray(radii)

        self.set_yticks(radii)
        if labels is not None:
            self.set_yticklabels(labels)
        elif fmt is not None:
            self.yaxis.set_major_formatter(mticker.FormatStrFormatter(fmt))
        if angle is None:
            angle = self.get_rlabel_position()
        self.set_rlabel_position(angle)
        for t in self.yaxis.get_ticklabels():
            t._internal_update(kwargs)
        return self.yaxis.get_gridlines(), self.yaxis.get_ticklabels()

    def format_coord(self, theta, r):
        # docstring inherited
        screen_xy = self.transData.transform((theta, r))
        screen_xys = screen_xy + np.stack(
            np.meshgrid([-1, 0, 1], [-1, 0, 1])).reshape((2, -1)).T
        ts, rs = self.transData.inverted().transform(screen_xys).T
        delta_t = abs((ts - theta + np.pi) % (2 * np.pi) - np.pi).max()
        delta_t_halfturns = delta_t / np.pi
        delta_t_degrees = delta_t_halfturns * 180
        delta_r = abs(rs - r).max()
        if theta < 0:
            theta += 2 * np.pi
        theta_halfturns = theta / np.pi
        theta_degrees = theta_halfturns * 180

        # See ScalarFormatter.format_data_short.  For r, use #g-formatting
        # (as for linear axes), but for theta, use f-formatting as scientific
        # notation doesn't make sense and the trailing dot is ugly.
        def format_sig(value, delta, opt, fmt):
            # For "f", only count digits after decimal point.
            prec = (max(0, -math.floor(math.log10(delta))) if fmt == "f" else
                    cbook._g_sig_digits(value, delta))
            return f"{value:-{opt}.{prec}{fmt}}"

        # In case fmt_xdata was not specified, resort to default

        if self.fmt_ydata is None:
            r_label = format_sig(r, delta_r, "#", "g")
        else:
            r_label = self.format_ydata(r)

        if self.fmt_xdata is None:
            return ('\N{GREEK SMALL LETTER THETA}={}\N{GREEK SMALL LETTER PI} '
                    '({}\N{DEGREE SIGN}), r={}').format(
                    format_sig(theta_halfturns, delta_t_halfturns, "", "f"),
                    format_sig(theta_degrees, delta_t_degrees, "", "f"),
                    r_label
                )
        else:
            return '\N{GREEK SMALL LETTER THETA}={}, r={}'.format(
                        self.format_xdata(theta),
                        r_label
                        )

    def get_data_ratio(self):
        """
        Return the aspect ratio of the data itself.  For a polar plot,
        this should always be 1.0
        """
        return 1.0

    # # # Interactive panning

    def can_zoom(self):
        """
        Return whether this Axes supports the zoom box button functionality.

        A polar Axes does not support zoom boxes.
        """
        return False

    def can_pan(self):
        """
        Return whether this Axes supports the pan/zoom button functionality.

        For a polar Axes, this is slightly misleading. Both panning and
        zooming are performed by the same button. Panning is performed
        in azimuth while zooming is done along the radial.
        """
        return True

    def start_pan(self, x, y, button):
        angle = np.deg2rad(self.get_rlabel_position())
        mode = ''
        if button == 1:
            epsilon = np.pi / 45.0
            t, r = self.transData.inverted().transform((x, y))
            if angle - epsilon <= t <= angle + epsilon:
                mode = 'drag_r_labels'
        elif button == 3:
            mode = 'zoom'

        self._pan_start = types.SimpleNamespace(
            rmax=self.get_rmax(),
            trans=self.transData.frozen(),
            trans_inverse=self.transData.inverted().frozen(),
            r_label_angle=self.get_rlabel_position(),
            x=x,
            y=y,
            mode=mode)

    def end_pan(self):
        del self._pan_start

    def drag_pan(self, button, key, x, y):
        p = self._pan_start

        if p.mode == 'drag_r_labels':
            (startt, startr), (t, r) = p.trans_inverse.transform(
                [(p.x, p.y), (x, y)])

            # Deal with theta
            dt = np.rad2deg(startt - t)
            self.set_rlabel_position(p.r_label_angle - dt)

            trans, vert1, horiz1 = self.get_yaxis_text1_transform(0.0)
            trans, vert2, horiz2 = self.get_yaxis_text2_transform(0.0)
            for t in self.yaxis.majorTicks + self.yaxis.minorTicks:
                t.label1.set_va(vert1)
                t.label1.set_ha(horiz1)
                t.label2.set_va(vert2)
                t.label2.set_ha(horiz2)

        elif p.mode == 'zoom':
            (startt, startr), (t, r) = p.trans_inverse.transform(
                [(p.x, p.y), (x, y)])

            # Deal with r
            scale = r / startr
            self.set_rmax(p.rmax / scale)


# To keep things all self-contained, we can put aliases to the Polar classes
# defined above. This isn't strictly necessary, but it makes some of the
# code more readable, and provides a backwards compatible Polar API. In
# particular, this is used by the :doc:`/gallery/specialty_plots/radar_chart`
# example to override PolarTransform on a PolarAxes subclass, so make sure that
# that example is unaffected before changing this.
PolarAxes.PolarTransform = PolarTransform
PolarAxes.PolarAffine = PolarAffine
PolarAxes.InvertedPolarTransform = InvertedPolarTransform
PolarAxes.ThetaFormatter = ThetaFormatter
PolarAxes.RadialLocator = RadialLocator
PolarAxes.ThetaLocator = ThetaLocator

# === NexusCore/openenv\Lib\site-packages\PIL\PngImagePlugin.py ===
#
# The Python Imaging Library.
# $Id$
#
# PNG support code
#
# See "PNG (Portable Network Graphics) Specification, version 1.0;
# W3C Recommendation", 1996-10-01, Thomas Boutell (ed.).
#
# history:
# 1996-05-06 fl   Created (couldn't resist it)
# 1996-12-14 fl   Upgraded, added read and verify support (0.2)
# 1996-12-15 fl   Separate PNG stream parser
# 1996-12-29 fl   Added write support, added getchunks
# 1996-12-30 fl   Eliminated circular references in decoder (0.3)
# 1998-07-12 fl   Read/write 16-bit images as mode I (0.4)
# 2001-02-08 fl   Added transparency support (from Zircon) (0.5)
# 2001-04-16 fl   Don't close data source in "open" method (0.6)
# 2004-02-24 fl   Don't even pretend to support interlaced files (0.7)
# 2004-08-31 fl   Do basic sanity check on chunk identifiers (0.8)
# 2004-09-20 fl   Added PngInfo chunk container
# 2004-12-18 fl   Added DPI read support (based on code by Niki Spahiev)
# 2008-08-13 fl   Added tRNS support for RGB images
# 2009-03-06 fl   Support for preserving ICC profiles (by Florian Hoech)
# 2009-03-08 fl   Added zTXT support (from Lowell Alleman)
# 2009-03-29 fl   Read interlaced PNG files (from Conrado Porto Lopes Gouvua)
#
# Copyright (c) 1997-2009 by Secret Labs AB
# Copyright (c) 1996 by Fredrik Lundh
#
# See the README file for information on usage and redistribution.
#
from __future__ import annotations

import itertools
import logging
import re
import struct
import warnings
import zlib
from collections.abc import Callable
from enum import IntEnum
from typing import IO, Any, NamedTuple, NoReturn, cast

from . import Image, ImageChops, ImageFile, ImagePalette, ImageSequence
from ._binary import i16be as i16
from ._binary import i32be as i32
from ._binary import o8
from ._binary import o16be as o16
from ._binary import o32be as o32
from ._util import DeferredError

TYPE_CHECKING = False
if TYPE_CHECKING:
    from . import _imaging

logger = logging.getLogger(__name__)

is_cid = re.compile(rb"\w\w\w\w").match


_MAGIC = b"\211PNG\r\n\032\n"


_MODES = {
    # supported bits/color combinations, and corresponding modes/rawmodes
    # Grayscale
    (1, 0): ("1", "1"),
    (2, 0): ("L", "L;2"),
    (4, 0): ("L", "L;4"),
    (8, 0): ("L", "L"),
    (16, 0): ("I;16", "I;16B"),
    # Truecolour
    (8, 2): ("RGB", "RGB"),
    (16, 2): ("RGB", "RGB;16B"),
    # Indexed-colour
    (1, 3): ("P", "P;1"),
    (2, 3): ("P", "P;2"),
    (4, 3): ("P", "P;4"),
    (8, 3): ("P", "P"),
    # Grayscale with alpha
    (8, 4): ("LA", "LA"),
    (16, 4): ("RGBA", "LA;16B"),  # LA;16B->LA not yet available
    # Truecolour with alpha
    (8, 6): ("RGBA", "RGBA"),
    (16, 6): ("RGBA", "RGBA;16B"),
}


_simple_palette = re.compile(b"^\xff*\x00\xff*$")

MAX_TEXT_CHUNK = ImageFile.SAFEBLOCK
"""
Maximum decompressed size for a iTXt or zTXt chunk.
Eliminates decompression bombs where compressed chunks can expand 1000x.
See :ref:`Text in PNG File Format<png-text>`.
"""
MAX_TEXT_MEMORY = 64 * MAX_TEXT_CHUNK
"""
Set the maximum total text chunk size.
See :ref:`Text in PNG File Format<png-text>`.
"""


# APNG frame disposal modes
class Disposal(IntEnum):
    OP_NONE = 0
    """
    No disposal is done on this frame before rendering the next frame.
    See :ref:`Saving APNG sequences<apng-saving>`.
    """
    OP_BACKGROUND = 1
    """
    This frame’s modified region is cleared to fully transparent black before rendering
    the next frame.
    See :ref:`Saving APNG sequences<apng-saving>`.
    """
    OP_PREVIOUS = 2
    """
    This frame’s modified region is reverted to the previous frame’s contents before
    rendering the next frame.
    See :ref:`Saving APNG sequences<apng-saving>`.
    """


# APNG frame blend modes
class Blend(IntEnum):
    OP_SOURCE = 0
    """
    All color components of this frame, including alpha, overwrite the previous output
    image contents.
    See :ref:`Saving APNG sequences<apng-saving>`.
    """
    OP_OVER = 1
    """
    This frame should be alpha composited with the previous output image contents.
    See :ref:`Saving APNG sequences<apng-saving>`.
    """


def _safe_zlib_decompress(s: bytes) -> bytes:
    dobj = zlib.decompressobj()
    plaintext = dobj.decompress(s, MAX_TEXT_CHUNK)
    if dobj.unconsumed_tail:
        msg = "Decompressed data too large for PngImagePlugin.MAX_TEXT_CHUNK"
        raise ValueError(msg)
    return plaintext


def _crc32(data: bytes, seed: int = 0) -> int:
    return zlib.crc32(data, seed) & 0xFFFFFFFF


# --------------------------------------------------------------------
# Support classes.  Suitable for PNG and related formats like MNG etc.


class ChunkStream:
    def __init__(self, fp: IO[bytes]) -> None:
        self.fp: IO[bytes] | None = fp
        self.queue: list[tuple[bytes, int, int]] | None = []

    def read(self) -> tuple[bytes, int, int]:
        """Fetch a new chunk. Returns header information."""
        cid = None

        assert self.fp is not None
        if self.queue:
            cid, pos, length = self.queue.pop()
            self.fp.seek(pos)
        else:
            s = self.fp.read(8)
            cid = s[4:]
            pos = self.fp.tell()
            length = i32(s)

        if not is_cid(cid):
            if not ImageFile.LOAD_TRUNCATED_IMAGES:
                msg = f"broken PNG file (chunk {repr(cid)})"
                raise SyntaxError(msg)

        return cid, pos, length

    def __enter__(self) -> ChunkStream:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()

    def close(self) -> None:
        self.queue = self.fp = None

    def push(self, cid: bytes, pos: int, length: int) -> None:
        assert self.queue is not None
        self.queue.append((cid, pos, length))

    def call(self, cid: bytes, pos: int, length: int) -> bytes:
        """Call the appropriate chunk handler"""

        logger.debug("STREAM %r %s %s", cid, pos, length)
        return getattr(self, f"chunk_{cid.decode('ascii')}")(pos, length)

    def crc(self, cid: bytes, data: bytes) -> None:
        """Read and verify checksum"""

        # Skip CRC checks for ancillary chunks if allowed to load truncated
        # images
        # 5th byte of first char is 1 [specs, section 5.4]
        if ImageFile.LOAD_TRUNCATED_IMAGES and (cid[0] >> 5 & 1):
            self.crc_skip(cid, data)
            return

        assert self.fp is not None
        try:
            crc1 = _crc32(data, _crc32(cid))
            crc2 = i32(self.fp.read(4))
            if crc1 != crc2:
                msg = f"broken PNG file (bad header checksum in {repr(cid)})"
                raise SyntaxError(msg)
        except struct.error as e:
            msg = f"broken PNG file (incomplete checksum in {repr(cid)})"
            raise SyntaxError(msg) from e

    def crc_skip(self, cid: bytes, data: bytes) -> None:
        """Read checksum"""

        assert self.fp is not None
        self.fp.read(4)

    def verify(self, endchunk: bytes = b"IEND") -> list[bytes]:
        # Simple approach; just calculate checksum for all remaining
        # blocks.  Must be called directly after open.

        cids = []

        assert self.fp is not None
        while True:
            try:
                cid, pos, length = self.read()
            except struct.error as e:
                msg = "truncated PNG file"
                raise OSError(msg) from e

            if cid == endchunk:
                break
            self.crc(cid, ImageFile._safe_read(self.fp, length))
            cids.append(cid)

        return cids


class iTXt(str):
    """
    Subclass of string to allow iTXt chunks to look like strings while
    keeping their extra information

    """

    lang: str | bytes | None
    tkey: str | bytes | None

    @staticmethod
    def __new__(
        cls, text: str, lang: str | None = None, tkey: str | None = None
    ) -> iTXt:
        """
        :param cls: the class to use when creating the instance
        :param text: value for this key
        :param lang: language code
        :param tkey: UTF-8 version of the key name
        """

        self = str.__new__(cls, text)
        self.lang = lang
        self.tkey = tkey
        return self


class PngInfo:
    """
    PNG chunk container (for use with save(pnginfo=))

    """

    def __init__(self) -> None:
        self.chunks: list[tuple[bytes, bytes, bool]] = []

    def add(self, cid: bytes, data: bytes, after_idat: bool = False) -> None:
        """Appends an arbitrary chunk. Use with caution.

        :param cid: a byte string, 4 bytes long.
        :param data: a byte string of the encoded data
        :param after_idat: for use with private chunks. Whether the chunk
                           should be written after IDAT

        """

        self.chunks.append((cid, data, after_idat))

    def add_itxt(
        self,
        key: str | bytes,
        value: str | bytes,
        lang: str | bytes = "",
        tkey: str | bytes = "",
        zip: bool = False,
    ) -> None:
        """Appends an iTXt chunk.

        :param key: latin-1 encodable text key name
        :param value: value for this key
        :param lang: language code
        :param tkey: UTF-8 version of the key name
        :param zip: compression flag

        """

        if not isinstance(key, bytes):
            key = key.encode("latin-1", "strict")
        if not isinstance(value, bytes):
            value = value.encode("utf-8", "strict")
        if not isinstance(lang, bytes):
            lang = lang.encode("utf-8", "strict")
        if not isinstance(tkey, bytes):
            tkey = tkey.encode("utf-8", "strict")

        if zip:
            self.add(
                b"iTXt",
                key + b"\0\x01\0" + lang + b"\0" + tkey + b"\0" + zlib.compress(value),
            )
        else:
            self.add(b"iTXt", key + b"\0\0\0" + lang + b"\0" + tkey + b"\0" + value)

    def add_text(
        self, key: str | bytes, value: str | bytes | iTXt, zip: bool = False
    ) -> None:
        """Appends a text chunk.

        :param key: latin-1 encodable text key name
        :param value: value for this key, text or an
           :py:class:`PIL.PngImagePlugin.iTXt` instance
        :param zip: compression flag

        """
        if isinstance(value, iTXt):
            return self.add_itxt(
                key,
                value,
                value.lang if value.lang is not None else b"",
                value.tkey if value.tkey is not None else b"",
                zip=zip,
            )

        # The tEXt chunk stores latin-1 text
        if not isinstance(value, bytes):
            try:
                value = value.encode("latin-1", "strict")
            except UnicodeError:
                return self.add_itxt(key, value, zip=zip)

        if not isinstance(key, bytes):
            key = key.encode("latin-1", "strict")

        if zip:
            self.add(b"zTXt", key + b"\0\0" + zlib.compress(value))
        else:
            self.add(b"tEXt", key + b"\0" + value)


# --------------------------------------------------------------------
# PNG image stream (IHDR/IEND)


class _RewindState(NamedTuple):
    info: dict[str | tuple[int, int], Any]
    tile: list[ImageFile._Tile]
    seq_num: int | None


class PngStream(ChunkStream):
    def __init__(self, fp: IO[bytes]) -> None:
        super().__init__(fp)

        # local copies of Image attributes
        self.im_info: dict[str | tuple[int, int], Any] = {}
        self.im_text: dict[str, str | iTXt] = {}
        self.im_size = (0, 0)
        self.im_mode = ""
        self.im_tile: list[ImageFile._Tile] = []
        self.im_palette: tuple[str, bytes] | None = None
        self.im_custom_mimetype: str | None = None
        self.im_n_frames: int | None = None
        self._seq_num: int | None = None
        self.rewind_state = _RewindState({}, [], None)

        self.text_memory = 0

    def check_text_memory(self, chunklen: int) -> None:
        self.text_memory += chunklen
        if self.text_memory > MAX_TEXT_MEMORY:
            msg = (
                "Too much memory used in text chunks: "
                f"{self.text_memory}>MAX_TEXT_MEMORY"
            )
            raise ValueError(msg)

    def save_rewind(self) -> None:
        self.rewind_state = _RewindState(
            self.im_info.copy(),
            self.im_tile,
            self._seq_num,
        )

    def rewind(self) -> None:
        self.im_info = self.rewind_state.info.copy()
        self.im_tile = self.rewind_state.tile
        self._seq_num = self.rewind_state.seq_num

    def chunk_iCCP(self, pos: int, length: int) -> bytes:
        # ICC profile
        assert self.fp is not None
        s = ImageFile._safe_read(self.fp, length)
        # according to PNG spec, the iCCP chunk contains:
        # Profile name  1-79 bytes (character string)
        # Null separator        1 byte (null character)
        # Compression method    1 byte (0)
        # Compressed profile    n bytes (zlib with deflate compression)
        i = s.find(b"\0")
        logger.debug("iCCP profile name %r", s[:i])
        comp_method = s[i + 1]
        logger.debug("Compression method %s", comp_method)
        if comp_method != 0:
            msg = f"Unknown compression method {comp_method} in iCCP chunk"
            raise SyntaxError(msg)
        try:
            icc_profile = _safe_zlib_decompress(s[i + 2 :])
        except ValueError:
            if ImageFile.LOAD_TRUNCATED_IMAGES:
                icc_profile = None
            else:
                raise
        except zlib.error:
            icc_profile = None  # FIXME
        self.im_info["icc_profile"] = icc_profile
        return s

    def chunk_IHDR(self, pos: int, length: int) -> bytes:
        # image header
        assert self.fp is not None
        s = ImageFile._safe_read(self.fp, length)
        if length < 13:
            if ImageFile.LOAD_TRUNCATED_IMAGES:
                return s
            msg = "Truncated IHDR chunk"
            raise ValueError(msg)
        self.im_size = i32(s, 0), i32(s, 4)
        try:
            self.im_mode, self.im_rawmode = _MODES[(s[8], s[9])]
        except Exception:
            pass
        if s[12]:
            self.im_info["interlace"] = 1
        if s[11]:
            msg = "unknown filter category"
            raise SyntaxError(msg)
        return s

    def chunk_IDAT(self, pos: int, length: int) -> NoReturn:
        # image data
        if "bbox" in self.im_info:
            tile = [ImageFile._Tile("zip", self.im_info["bbox"], pos, self.im_rawmode)]
        else:
            if self.im_n_frames is not None:
                self.im_info["default_image"] = True
            tile = [ImageFile._Tile("zip", (0, 0) + self.im_size, pos, self.im_rawmode)]
        self.im_tile = tile
        self.im_idat = length
        msg = "image data found"
        raise EOFError(msg)

    def chunk_IEND(self, pos: int, length: int) -> NoReturn:
        msg = "end of PNG image"
        raise EOFError(msg)

    def chunk_PLTE(self, pos: int, length: int) -> bytes:
        # palette
        assert self.fp is not None
        s = ImageFile._safe_read(self.fp, length)
        if self.im_mode == "P":
            self.im_palette = "RGB", s
        return s

    def chunk_tRNS(self, pos: int, length: int) -> bytes:
        # transparency
        assert self.fp is not None
        s = ImageFile._safe_read(self.fp, length)
        if self.im_mode == "P":
            if _simple_palette.match(s):
                # tRNS contains only one full-transparent entry,
                # other entries are full opaque
                i = s.find(b"\0")
                if i >= 0:
                    self.im_info["transparency"] = i
            else:
                # otherwise, we have a byte string with one alpha value
                # for each palette entry
                self.im_info["transparency"] = s
        elif self.im_mode in ("1", "L", "I;16"):
            self.im_info["transparency"] = i16(s)
        elif self.im_mode == "RGB":
            self.im_info["transparency"] = i16(s), i16(s, 2), i16(s, 4)
        return s

    def chunk_gAMA(self, pos: int, length: int) -> bytes:
        # gamma setting
        assert self.fp is not None
        s = ImageFile._safe_read(self.fp, length)
        self.im_info["gamma"] = i32(s) / 100000.0
        return s

    def chunk_cHRM(self, pos: int, length: int) -> bytes:
        # chromaticity, 8 unsigned ints, actual value is scaled by 100,000
        # WP x,y, Red x,y, Green x,y Blue x,y

        assert self.fp is not None
        s = ImageFile._safe_read(self.fp, length)
        raw_vals = struct.unpack(f">{len(s) // 4}I", s)
        self.im_info["chromaticity"] = tuple(elt / 100000.0 for elt in raw_vals)
        return s

    def chunk_sRGB(self, pos: int, length: int) -> bytes:
        # srgb rendering intent, 1 byte
        # 0 perceptual
        # 1 relative colorimetric
        # 2 saturation
        # 3 absolute colorimetric

        assert self.fp is not None
        s = ImageFile._safe_read(self.fp, length)
        if length < 1:
            if ImageFile.LOAD_TRUNCATED_IMAGES:
                return s
            msg = "Truncated sRGB chunk"
            raise ValueError(msg)
        self.im_info["srgb"] = s[0]
        return s

    def chunk_pHYs(self, pos: int, length: int) -> bytes:
        # pixels per unit
        assert self.fp is not None
        s = ImageFile._safe_read(self.fp, length)
        if length < 9:
            if ImageFile.LOAD_TRUNCATED_IMAGES:
                return s
            msg = "Truncated pHYs chunk"
            raise ValueError(msg)
        px, py = i32(s, 0), i32(s, 4)
        unit = s[8]
        if unit == 1:  # meter
            dpi = px * 0.0254, py * 0.0254
            self.im_info["dpi"] = dpi
        elif unit == 0:
            self.im_info["aspect"] = px, py
        return s

    def chunk_tEXt(self, pos: int, length: int) -> bytes:
        # text
        assert self.fp is not None
        s = ImageFile._safe_read(self.fp, length)
        try:
            k, v = s.split(b"\0", 1)
        except ValueError:
            # fallback for broken tEXt tags
            k = s
            v = b""
        if k:
            k_str = k.decode("latin-1", "strict")
            v_str = v.decode("latin-1", "replace")

            self.im_info[k_str] = v if k == b"exif" else v_str
            self.im_text[k_str] = v_str
            self.check_text_memory(len(v_str))

        return s

    def chunk_zTXt(self, pos: int, length: int) -> bytes:
        # compressed text
        assert self.fp is not None
        s = ImageFile._safe_read(self.fp, length)
        try:
            k, v = s.split(b"\0", 1)
        except ValueError:
            k = s
            v = b""
        if v:
            comp_method = v[0]
        else:
            comp_method = 0
        if comp_method != 0:
            msg = f"Unknown compression method {comp_method} in zTXt chunk"
            raise SyntaxError(msg)
        try:
            v = _safe_zlib_decompress(v[1:])
        except ValueError:
            if ImageFile.LOAD_TRUNCATED_IMAGES:
                v = b""
            else:
                raise
        except zlib.error:
            v = b""

        if k:
            k_str = k.decode("latin-1", "strict")
            v_str = v.decode("latin-1", "replace")

            self.im_info[k_str] = self.im_text[k_str] = v_str
            self.check_text_memory(len(v_str))

        return s

    def chunk_iTXt(self, pos: int, length: int) -> bytes:
        # international text
        assert self.fp is not None
        r = s = ImageFile._safe_read(self.fp, length)
        try:
            k, r = r.split(b"\0", 1)
        except ValueError:
            return s
        if len(r) < 2:
            return s
        cf, cm, r = r[0], r[1], r[2:]
        try:
            lang, tk, v = r.split(b"\0", 2)
        except ValueError:
            return s
        if cf != 0:
            if cm == 0:
                try:
                    v = _safe_zlib_decompress(v)
                except ValueError:
                    if ImageFile.LOAD_TRUNCATED_IMAGES:
                        return s
                    else:
                        raise
                except zlib.error:
                    return s
            else:
                return s
        if k == b"XML:com.adobe.xmp":
            self.im_info["xmp"] = v
        try:
            k_str = k.decode("latin-1", "strict")
            lang_str = lang.decode("utf-8", "strict")
            tk_str = tk.decode("utf-8", "strict")
            v_str = v.decode("utf-8", "strict")
        except UnicodeError:
            return s

        self.im_info[k_str] = self.im_text[k_str] = iTXt(v_str, lang_str, tk_str)
        self.check_text_memory(len(v_str))

        return s

    def chunk_eXIf(self, pos: int, length: int) -> bytes:
        assert self.fp is not None
        s = ImageFile._safe_read(self.fp, length)
        self.im_info["exif"] = b"Exif\x00\x00" + s
        return s

    # APNG chunks
    def chunk_acTL(self, pos: int, length: int) -> bytes:
        assert self.fp is not None
        s = ImageFile._safe_read(self.fp, length)
        if length < 8:
            if ImageFile.LOAD_TRUNCATED_IMAGES:
                return s
            msg = "APNG contains truncated acTL chunk"
            raise ValueError(msg)
        if self.im_n_frames is not None:
            self.im_n_frames = None
            warnings.warn("Invalid APNG, will use default PNG image if possible")
            return s
        n_frames = i32(s)
        if n_frames == 0 or n_frames > 0x80000000:
            warnings.warn("Invalid APNG, will use default PNG image if possible")
            return s
        self.im_n_frames = n_frames
        self.im_info["loop"] = i32(s, 4)
        self.im_custom_mimetype = "image/apng"
        return s

    def chunk_fcTL(self, pos: int, length: int) -> bytes:
        assert self.fp is not None
        s = ImageFile._safe_read(self.fp, length)
        if length < 26:
            if ImageFile.LOAD_TRUNCATED_IMAGES:
                return s
            msg = "APNG contains truncated fcTL chunk"
            raise ValueError(msg)
        seq = i32(s)
        if (self._seq_num is None and seq != 0) or (
            self._seq_num is not None and self._seq_num != seq - 1
        ):
            msg = "APNG contains frame sequence errors"
            raise SyntaxError(msg)
        self._seq_num = seq
        width, height = i32(s, 4), i32(s, 8)
        px, py = i32(s, 12), i32(s, 16)
        im_w, im_h = self.im_size
        if px + width > im_w or py + height > im_h:
            msg = "APNG contains invalid frames"
            raise SyntaxError(msg)
        self.im_info["bbox"] = (px, py, px + width, py + height)
        delay_num, delay_den = i16(s, 20), i16(s, 22)
        if delay_den == 0:
            delay_den = 100
        self.im_info["duration"] = float(delay_num) / float(delay_den) * 1000
        self.im_info["disposal"] = s[24]
        self.im_info["blend"] = s[25]
        return s

    def chunk_fdAT(self, pos: int, length: int) -> bytes:
        assert self.fp is not None
        if length < 4:
            if ImageFile.LOAD_TRUNCATED_IMAGES:
                s = ImageFile._safe_read(self.fp, length)
                return s
            msg = "APNG contains truncated fDAT chunk"
            raise ValueError(msg)
        s = ImageFile._safe_read(self.fp, 4)
        seq = i32(s)
        if self._seq_num != seq - 1:
            msg = "APNG contains frame sequence errors"
            raise SyntaxError(msg)
        self._seq_num = seq
        return self.chunk_IDAT(pos + 4, length - 4)


# --------------------------------------------------------------------
# PNG reader


def _accept(prefix: bytes) -> bool:
    return prefix.startswith(_MAGIC)


##
# Image plugin for PNG images.


class PngImageFile(ImageFile.ImageFile):
    format = "PNG"
    format_description = "Portable network graphics"

    def _open(self) -> None:
        if not _accept(self.fp.read(8)):
            msg = "not a PNG file"
            raise SyntaxError(msg)
        self._fp = self.fp
        self.__frame = 0

        #
        # Parse headers up to the first IDAT or fDAT chunk

        self.private_chunks: list[tuple[bytes, bytes] | tuple[bytes, bytes, bool]] = []
        self.png: PngStream | None = PngStream(self.fp)

        while True:
            #
            # get next chunk

            cid, pos, length = self.png.read()

            try:
                s = self.png.call(cid, pos, length)
            except EOFError:
                break
            except AttributeError:
                logger.debug("%r %s %s (unknown)", cid, pos, length)
                s = ImageFile._safe_read(self.fp, length)
                if cid[1:2].islower():
                    self.private_chunks.append((cid, s))

            self.png.crc(cid, s)

        #
        # Copy relevant attributes from the PngStream.  An alternative
        # would be to let the PngStream class modify these attributes
        # directly, but that introduces circular references which are
        # difficult to break if things go wrong in the decoder...
        # (believe me, I've tried ;-)

        self._mode = self.png.im_mode
        self._size = self.png.im_size
        self.info = self.png.im_info
        self._text: dict[str, str | iTXt] | None = None
        self.tile = self.png.im_tile
        self.custom_mimetype = self.png.im_custom_mimetype
        self.n_frames = self.png.im_n_frames or 1
        self.default_image = self.info.get("default_image", False)

        if self.png.im_palette:
            rawmode, data = self.png.im_palette
            self.palette = ImagePalette.raw(rawmode, data)

        if cid == b"fdAT":
            self.__prepare_idat = length - 4
        else:
            self.__prepare_idat = length  # used by load_prepare()

        if self.png.im_n_frames is not None:
            self._close_exclusive_fp_after_loading = False
            self.png.save_rewind()
            self.__rewind_idat = self.__prepare_idat
            self.__rewind = self._fp.tell()
            if self.default_image:
                # IDAT chunk contains default image and not first animation frame
                self.n_frames += 1
            self._seek(0)
        self.is_animated = self.n_frames > 1

    @property
    def text(self) -> dict[str, str | iTXt]:
        # experimental
        if self._text is None:
            # iTxt, tEXt and zTXt chunks may appear at the end of the file
            # So load the file to ensure that they are read
            if self.is_animated:
                frame = self.__frame
                # for APNG, seek to the final frame before loading
                self.seek(self.n_frames - 1)
            self.load()
            if self.is_animated:
                self.seek(frame)
        assert self._text is not None
        return self._text

    def verify(self) -> None:
        """Verify PNG file"""

        if self.fp is None:
            msg = "verify must be called directly after open"
            raise RuntimeError(msg)

        # back up to beginning of IDAT block
        self.fp.seek(self.tile[0][2] - 8)

        assert self.png is not None
        self.png.verify()
        self.png.close()

        if self._exclusive_fp:
            self.fp.close()
        self.fp = None

    def seek(self, frame: int) -> None:
        if not self._seek_check(frame):
            return
        if frame < self.__frame:
            self._seek(0, True)

        last_frame = self.__frame
        for f in range(self.__frame + 1, frame + 1):
            try:
                self._seek(f)
            except EOFError as e:
                self.seek(last_frame)
                msg = "no more images in APNG file"
                raise EOFError(msg) from e

    def _seek(self, frame: int, rewind: bool = False) -> None:
        assert self.png is not None
        if isinstance(self._fp, DeferredError):
            raise self._fp.ex

        self.dispose: _imaging.ImagingCore | None
        dispose_extent = None
        if frame == 0:
            if rewind:
                self._fp.seek(self.__rewind)
                self.png.rewind()
                self.__prepare_idat = self.__rewind_idat
                self._im = None
                self.info = self.png.im_info
                self.tile = self.png.im_tile
                self.fp = self._fp
            self._prev_im = None
            self.dispose = None
            self.default_image = self.info.get("default_image", False)
            self.dispose_op = self.info.get("disposal")
            self.blend_op = self.info.get("blend")
            dispose_extent = self.info.get("bbox")
            self.__frame = 0
        else:
            if frame != self.__frame + 1:
                msg = f"cannot seek to frame {frame}"
                raise ValueError(msg)

            # ensure previous frame was loaded
            self.load()

            if self.dispose:
                self.im.paste(self.dispose, self.dispose_extent)
            self._prev_im = self.im.copy()

            self.fp = self._fp

            # advance to the next frame
            if self.__prepare_idat:
                ImageFile._safe_read(self.fp, self.__prepare_idat)
                self.__prepare_idat = 0
            frame_start = False
            while True:
                self.fp.read(4)  # CRC

                try:
                    cid, pos, length = self.png.read()
                except (struct.error, SyntaxError):
                    break

                if cid == b"IEND":
                    msg = "No more images in APNG file"
                    raise EOFError(msg)
                if cid == b"fcTL":
                    if frame_start:
                        # there must be at least one fdAT chunk between fcTL chunks
                        msg = "APNG missing frame data"
                        raise SyntaxError(msg)
                    frame_start = True

                try:
                    self.png.call(cid, pos, length)
                except UnicodeDecodeError:
                    break
                except EOFError:
                    if cid == b"fdAT":
                        length -= 4
                        if frame_start:
                            self.__prepare_idat = length
                            break
                    ImageFile._safe_read(self.fp, length)
                except AttributeError:
                    logger.debug("%r %s %s (unknown)", cid, pos, length)
                    ImageFile._safe_read(self.fp, length)

            self.__frame = frame
            self.tile = self.png.im_tile
            self.dispose_op = self.info.get("disposal")
            self.blend_op = self.info.get("blend")
            dispose_extent = self.info.get("bbox")

            if not self.tile:
                msg = "image not found in APNG frame"
                raise EOFError(msg)
        if dispose_extent:
            self.dispose_extent: tuple[float, float, float, float] = dispose_extent

        # setup frame disposal (actual disposal done when needed in the next _seek())
        if self._prev_im is None and self.dispose_op == Disposal.OP_PREVIOUS:
            self.dispose_op = Disposal.OP_BACKGROUND

        self.dispose = None
        if self.dispose_op == Disposal.OP_PREVIOUS:
            if self._prev_im:
                self.dispose = self._prev_im.copy()
                self.dispose = self._crop(self.dispose, self.dispose_extent)
        elif self.dispose_op == Disposal.OP_BACKGROUND:
            self.dispose = Image.core.fill(self.mode, self.size)
            self.dispose = self._crop(self.dispose, self.dispose_extent)

    def tell(self) -> int:
        return self.__frame

    def load_prepare(self) -> None:
        """internal: prepare to read PNG file"""

        if self.info.get("interlace"):
            self.decoderconfig = self.decoderconfig + (1,)

        self.__idat = self.__prepare_idat  # used by load_read()
        ImageFile.ImageFile.load_prepare(self)

    def load_read(self, read_bytes: int) -> bytes:
        """internal: read more image data"""

        assert self.png is not None
        while self.__idat == 0:
            # end of chunk, skip forward to next one

            self.fp.read(4)  # CRC

            cid, pos, length = self.png.read()

            if cid not in [b"IDAT", b"DDAT", b"fdAT"]:
                self.png.push(cid, pos, length)
                return b""

            if cid == b"fdAT":
                try:
                    self.png.call(cid, pos, length)
                except EOFError:
                    pass
                self.__idat = length - 4  # sequence_num has already been read
            else:
                self.__idat = length  # empty chunks are allowed

        # read more data from this chunk
        if read_bytes <= 0:
            read_bytes = self.__idat
        else:
            read_bytes = min(read_bytes, self.__idat)

        self.__idat = self.__idat - read_bytes

        return self.fp.read(read_bytes)

    def load_end(self) -> None:
        """internal: finished reading image data"""
        assert self.png is not None
        if self.__idat != 0:
            self.fp.read(self.__idat)
        while True:
            self.fp.read(4)  # CRC

            try:
                cid, pos, length = self.png.read()
            except (struct.error, SyntaxError):
                break

            if cid == b"IEND":
                break
            elif cid == b"fcTL" and self.is_animated:
                # start of the next frame, stop reading
                self.__prepare_idat = 0
                self.png.push(cid, pos, length)
                break

            try:
                self.png.call(cid, pos, length)
            except UnicodeDecodeError:
                break
            except EOFError:
                if cid == b"fdAT":
                    length -= 4
                try:
                    ImageFile._safe_read(self.fp, length)
                except OSError as e:
                    if ImageFile.LOAD_TRUNCATED_IMAGES:
                        break
                    else:
                        raise e
            except AttributeError:
                logger.debug("%r %s %s (unknown)", cid, pos, length)
                s = ImageFile._safe_read(self.fp, length)
                if cid[1:2].islower():
                    self.private_chunks.append((cid, s, True))
        self._text = self.png.im_text
        if not self.is_animated:
            self.png.close()
            self.png = None
        else:
            if self._prev_im and self.blend_op == Blend.OP_OVER:
                updated = self._crop(self.im, self.dispose_extent)
                if self.im.mode == "RGB" and "transparency" in self.info:
                    mask = updated.convert_transparent(
                        "RGBA", self.info["transparency"]
                    )
                else:
                    if self.im.mode == "P" and "transparency" in self.info:
                        t = self.info["transparency"]
                        if isinstance(t, bytes):
                            updated.putpalettealphas(t)
                        elif isinstance(t, int):
                            updated.putpalettealpha(t)
                    mask = updated.convert("RGBA")
                self._prev_im.paste(updated, self.dispose_extent, mask)
                self.im = self._prev_im

    def _getexif(self) -> dict[int, Any] | None:
        if "exif" not in self.info:
            self.load()
        if "exif" not in self.info and "Raw profile type exif" not in self.info:
            return None
        return self.getexif()._get_merged_dict()

    def getexif(self) -> Image.Exif:
        if "exif" not in self.info:
            self.load()

        return super().getexif()


# --------------------------------------------------------------------
# PNG writer

_OUTMODES = {
    # supported PIL modes, and corresponding rawmode, bit depth and color type
    "1": ("1", b"\x01", b"\x00"),
    "L;1": ("L;1", b"\x01", b"\x00"),
    "L;2": ("L;2", b"\x02", b"\x00"),
    "L;4": ("L;4", b"\x04", b"\x00"),
    "L": ("L", b"\x08", b"\x00"),
    "LA": ("LA", b"\x08", b"\x04"),
    "I": ("I;16B", b"\x10", b"\x00"),
    "I;16": ("I;16B", b"\x10", b"\x00"),
    "I;16B": ("I;16B", b"\x10", b"\x00"),
    "P;1": ("P;1", b"\x01", b"\x03"),
    "P;2": ("P;2", b"\x02", b"\x03"),
    "P;4": ("P;4", b"\x04", b"\x03"),
    "P": ("P", b"\x08", b"\x03"),
    "RGB": ("RGB", b"\x08", b"\x02"),
    "RGBA": ("RGBA", b"\x08", b"\x06"),
}


def putchunk(fp: IO[bytes], cid: bytes, *data: bytes) -> None:
    """Write a PNG chunk (including CRC field)"""

    byte_data = b"".join(data)

    fp.write(o32(len(byte_data)) + cid)
    fp.write(byte_data)
    crc = _crc32(byte_data, _crc32(cid))
    fp.write(o32(crc))


class _idat:
    # wrap output from the encoder in IDAT chunks

    def __init__(self, fp: IO[bytes], chunk: Callable[..., None]) -> None:
        self.fp = fp
        self.chunk = chunk

    def write(self, data: bytes) -> None:
        self.chunk(self.fp, b"IDAT", data)


class _fdat:
    # wrap encoder output in fdAT chunks

    def __init__(self, fp: IO[bytes], chunk: Callable[..., None], seq_num: int) -> None:
        self.fp = fp
        self.chunk = chunk
        self.seq_num = seq_num

    def write(self, data: bytes) -> None:
        self.chunk(self.fp, b"fdAT", o32(self.seq_num), data)
        self.seq_num += 1


class _Frame(NamedTuple):
    im: Image.Image
    bbox: tuple[int, int, int, int] | None
    encoderinfo: dict[str, Any]


def _write_multiple_frames(
    im: Image.Image,
    fp: IO[bytes],
    chunk: Callable[..., None],
    mode: str,
    rawmode: str,
    default_image: Image.Image | None,
    append_images: list[Image.Image],
) -> Image.Image | None:
    duration = im.encoderinfo.get("duration")
    loop = im.encoderinfo.get("loop", im.info.get("loop", 0))
    disposal = im.encoderinfo.get("disposal", im.info.get("disposal", Disposal.OP_NONE))
    blend = im.encoderinfo.get("blend", im.info.get("blend", Blend.OP_SOURCE))

    if default_image:
        chain = itertools.chain(append_images)
    else:
        chain = itertools.chain([im], append_images)

    im_frames: list[_Frame] = []
    frame_count = 0
    for im_seq in chain:
        for im_frame in ImageSequence.Iterator(im_seq):
            if im_frame.mode == mode:
                im_frame = im_frame.copy()
            else:
                im_frame = im_frame.convert(mode)
            encoderinfo = im.encoderinfo.copy()
            if isinstance(duration, (list, tuple)):
                encoderinfo["duration"] = duration[frame_count]
            elif duration is None and "duration" in im_frame.info:
                encoderinfo["duration"] = im_frame.info["duration"]
            if isinstance(disposal, (list, tuple)):
                encoderinfo["disposal"] = disposal[frame_count]
            if isinstance(blend, (list, tuple)):
                encoderinfo["blend"] = blend[frame_count]
            frame_count += 1

            if im_frames:
                previous = im_frames[-1]
                prev_disposal = previous.encoderinfo.get("disposal")
                prev_blend = previous.encoderinfo.get("blend")
                if prev_disposal == Disposal.OP_PREVIOUS and len(im_frames) < 2:
                    prev_disposal = Disposal.OP_BACKGROUND

                if prev_disposal == Disposal.OP_BACKGROUND:
                    base_im = previous.im.copy()
                    dispose = Image.core.fill("RGBA", im.size, (0, 0, 0, 0))
                    bbox = previous.bbox
                    if bbox:
                        dispose = dispose.crop(bbox)
                    else:
                        bbox = (0, 0) + im.size
                    base_im.paste(dispose, bbox)
                elif prev_disposal == Disposal.OP_PREVIOUS:
                    base_im = im_frames[-2].im
                else:
                    base_im = previous.im
                delta = ImageChops.subtract_modulo(
                    im_frame.convert("RGBA"), base_im.convert("RGBA")
                )
                bbox = delta.getbbox(alpha_only=False)
                if (
                    not bbox
                    and prev_disposal == encoderinfo.get("disposal")
                    and prev_blend == encoderinfo.get("blend")
                    and "duration" in encoderinfo
                ):
                    previous.encoderinfo["duration"] += encoderinfo["duration"]
                    continue
            else:
                bbox = None
            im_frames.append(_Frame(im_frame, bbox, encoderinfo))

    if len(im_frames) == 1 and not default_image:
        return im_frames[0].im

    # animation control
    chunk(
        fp,
        b"acTL",
        o32(len(im_frames)),  # 0: num_frames
        o32(loop),  # 4: num_plays
    )

    # default image IDAT (if it exists)
    if default_image:
        if im.mode != mode:
            im = im.convert(mode)
        ImageFile._save(
            im,
            cast(IO[bytes], _idat(fp, chunk)),
            [ImageFile._Tile("zip", (0, 0) + im.size, 0, rawmode)],
        )

    seq_num = 0
    for frame, frame_data in enumerate(im_frames):
        im_frame = frame_data.im
        if not frame_data.bbox:
            bbox = (0, 0) + im_frame.size
        else:
            bbox = frame_data.bbox
            im_frame = im_frame.crop(bbox)
        size = im_frame.size
        encoderinfo = frame_data.encoderinfo
        frame_duration = int(round(encoderinfo.get("duration", 0)))
        frame_disposal = encoderinfo.get("disposal", disposal)
        frame_blend = encoderinfo.get("blend", blend)
        # frame control
        chunk(
            fp,
            b"fcTL",
            o32(seq_num),  # sequence_number
            o32(size[0]),  # width
            o32(size[1]),  # height
            o32(bbox[0]),  # x_offset
            o32(bbox[1]),  # y_offset
            o16(frame_duration),  # delay_numerator
            o16(1000),  # delay_denominator
            o8(frame_disposal),  # dispose_op
            o8(frame_blend),  # blend_op
        )
        seq_num += 1
        # frame data
        if frame == 0 and not default_image:
            # first frame must be in IDAT chunks for backwards compatibility
            ImageFile._save(
                im_frame,
                cast(IO[bytes], _idat(fp, chunk)),
                [ImageFile._Tile("zip", (0, 0) + im_frame.size, 0, rawmode)],
            )
        else:
            fdat_chunks = _fdat(fp, chunk, seq_num)
            ImageFile._save(
                im_frame,
                cast(IO[bytes], fdat_chunks),
                [ImageFile._Tile("zip", (0, 0) + im_frame.size, 0, rawmode)],
            )
            seq_num = fdat_chunks.seq_num
    return None


def _save_all(im: Image.Image, fp: IO[bytes], filename: str | bytes) -> None:
    _save(im, fp, filename, save_all=True)


def _save(
    im: Image.Image,
    fp: IO[bytes],
    filename: str | bytes,
    chunk: Callable[..., None] = putchunk,
    save_all: bool = False,
) -> None:
    # save an image to disk (called by the save method)

    if save_all:
        default_image = im.encoderinfo.get(
            "default_image", im.info.get("default_image")
        )
        modes = set()
        sizes = set()
        append_images = im.encoderinfo.get("append_images", [])
        for im_seq in itertools.chain([im], append_images):
            for im_frame in ImageSequence.Iterator(im_seq):
                modes.add(im_frame.mode)
                sizes.add(im_frame.size)
        for mode in ("RGBA", "RGB", "P"):
            if mode in modes:
                break
        else:
            mode = modes.pop()
        size = tuple(max(frame_size[i] for frame_size in sizes) for i in range(2))
    else:
        size = im.size
        mode = im.mode

    outmode = mode
    if mode == "P":
        #
        # attempt to minimize storage requirements for palette images
        if "bits" in im.encoderinfo:
            # number of bits specified by user
            colors = min(1 << im.encoderinfo["bits"], 256)
        else:
            # check palette contents
            if im.palette:
                colors = max(min(len(im.palette.getdata()[1]) // 3, 256), 1)
            else:
                colors = 256

        if colors <= 16:
            if colors <= 2:
                bits = 1
            elif colors <= 4:
                bits = 2
            else:
                bits = 4
            outmode += f";{bits}"

    # encoder options
    im.encoderconfig = (
        im.encoderinfo.get("optimize", False),
        im.encoderinfo.get("compress_level", -1),
        im.encoderinfo.get("compress_type", -1),
        im.encoderinfo.get("dictionary", b""),
    )

    # get the corresponding PNG mode
    try:
        rawmode, bit_depth, color_type = _OUTMODES[outmode]
    except KeyError as e:
        msg = f"cannot write mode {mode} as PNG"
        raise OSError(msg) from e

    #
    # write minimal PNG file

    fp.write(_MAGIC)

    chunk(
        fp,
        b"IHDR",
        o32(size[0]),  # 0: size
        o32(size[1]),
        bit_depth,
        color_type,
        b"\0",  # 10: compression
        b"\0",  # 11: filter category
        b"\0",  # 12: interlace flag
    )

    chunks = [b"cHRM", b"cICP", b"gAMA", b"sBIT", b"sRGB", b"tIME"]

    icc = im.encoderinfo.get("icc_profile", im.info.get("icc_profile"))
    if icc:
        # ICC profile
        # according to PNG spec, the iCCP chunk contains:
        # Profile name  1-79 bytes (character string)
        # Null separator        1 byte (null character)
        # Compression method    1 byte (0)
        # Compressed profile    n bytes (zlib with deflate compression)
        name = b"ICC Profile"
        data = name + b"\0\0" + zlib.compress(icc)
        chunk(fp, b"iCCP", data)

        # You must either have sRGB or iCCP.
        # Disallow sRGB chunks when an iCCP-chunk has been emitted.
        chunks.remove(b"sRGB")

    info = im.encoderinfo.get("pnginfo")
    if info:
        chunks_multiple_allowed = [b"sPLT", b"iTXt", b"tEXt", b"zTXt"]
        for info_chunk in info.chunks:
            cid, data = info_chunk[:2]
            if cid in chunks:
                chunks.remove(cid)
                chunk(fp, cid, data)
            elif cid in chunks_multiple_allowed:
                chunk(fp, cid, data)
            elif cid[1:2].islower():
                # Private chunk
                after_idat = len(info_chunk) == 3 and info_chunk[2]
                if not after_idat:
                    chunk(fp, cid, data)

    if im.mode == "P":
        palette_byte_number = colors * 3
        palette_bytes = im.im.getpalette("RGB")[:palette_byte_number]
        while len(palette_bytes) < palette_byte_number:
            palette_bytes += b"\0"
        chunk(fp, b"PLTE", palette_bytes)

    transparency = im.encoderinfo.get("transparency", im.info.get("transparency", None))

    if transparency or transparency == 0:
        if im.mode == "P":
            # limit to actual palette size
            alpha_bytes = colors
            if isinstance(transparency, bytes):
                chunk(fp, b"tRNS", transparency[:alpha_bytes])
            else:
                transparency = max(0, min(255, transparency))
                alpha = b"\xff" * transparency + b"\0"
                chunk(fp, b"tRNS", alpha[:alpha_bytes])
        elif im.mode in ("1", "L", "I", "I;16"):
            transparency = max(0, min(65535, transparency))
            chunk(fp, b"tRNS", o16(transparency))
        elif im.mode == "RGB":
            red, green, blue = transparency
            chunk(fp, b"tRNS", o16(red) + o16(green) + o16(blue))
        else:
            if "transparency" in im.encoderinfo:
                # don't bother with transparency if it's an RGBA
                # and it's in the info dict. It's probably just stale.
                msg = "cannot use transparency for this mode"
                raise OSError(msg)
    else:
        if im.mode == "P" and im.im.getpalettemode() == "RGBA":
            alpha = im.im.getpalette("RGBA", "A")
            alpha_bytes = colors
            chunk(fp, b"tRNS", alpha[:alpha_bytes])

    dpi = im.encoderinfo.get("dpi")
    if dpi:
        chunk(
            fp,
            b"pHYs",
            o32(int(dpi[0] / 0.0254 + 0.5)),
            o32(int(dpi[1] / 0.0254 + 0.5)),
            b"\x01",
        )

    if info:
        chunks = [b"bKGD", b"hIST"]
        for info_chunk in info.chunks:
            cid, data = info_chunk[:2]
            if cid in chunks:
                chunks.remove(cid)
                chunk(fp, cid, data)

    exif = im.encoderinfo.get("exif")
    if exif:
        if isinstance(exif, Image.Exif):
            exif = exif.tobytes(8)
        if exif.startswith(b"Exif\x00\x00"):
            exif = exif[6:]
        chunk(fp, b"eXIf", exif)

    single_im: Image.Image | None = im
    if save_all:
        single_im = _write_multiple_frames(
            im, fp, chunk, mode, rawmode, default_image, append_images
        )
    if single_im:
        ImageFile._save(
            single_im,
            cast(IO[bytes], _idat(fp, chunk)),
            [ImageFile._Tile("zip", (0, 0) + single_im.size, 0, rawmode)],
        )

    if info:
        for info_chunk in info.chunks:
            cid, data = info_chunk[:2]
            if cid[1:2].islower():
                # Private chunk
                after_idat = len(info_chunk) == 3 and info_chunk[2]
                if after_idat:
                    chunk(fp, cid, data)

    chunk(fp, b"IEND", b"")

    if hasattr(fp, "flush"):
        fp.flush()


# --------------------------------------------------------------------
# PNG chunk converter


def getchunks(im: Image.Image, **params: Any) -> list[tuple[bytes, bytes, bytes]]:
    """Return a list of PNG chunks representing this image."""
    from io import BytesIO

    chunks = []

    def append(fp: IO[bytes], cid: bytes, *data: bytes) -> None:
        byte_data = b"".join(data)
        crc = o32(_crc32(byte_data, _crc32(cid)))
        chunks.append((cid, byte_data, crc))

    fp = BytesIO()

    try:
        im.encoderinfo = params
        _save(im, fp, "", append)
    finally:
        del im.encoderinfo

    return chunks


# --------------------------------------------------------------------
# Registry

Image.register_open(PngImageFile.format, PngImageFile, _accept)
Image.register_save(PngImageFile.format, _save)
Image.register_save_all(PngImageFile.format, _save_all)

Image.register_extensions(PngImageFile.format, [".png", ".apng"])

Image.register_mime(PngImageFile.format, "image/png")

# === NexusCore/openenv\Lib\site-packages\adodbapi\test\adodbapitest.py ===
"""Unit tests version 2.6.1.0 for adodbapi"""

"""
    adodbapi - A python DB API 2.0 interface to Microsoft ADO

    Copyright (C) 2002  Henrik Ekelund

    This library is free software; you can redistribute it and/or
    modify it under the terms of the GNU Lesser General Public
    License as published by the Free Software Foundation; either
    version 2.1 of the License, or (at your option) any later version.

    This library is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
    Lesser General Public License for more details.

    You should have received a copy of the GNU Lesser General Public
    License along with this library; if not, write to the Free Software
    Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA

    Updates by Vernon Cole
"""

import copy
import datetime
import decimal
import random
import string
import time
import unittest

import adodbapitestconfig as config  # run the configuration module. # will set sys.path to find correct version of adodbapi
import tryconnection  # in our code below, all our switches are from config.whatever

import adodbapi
import adodbapi.apibase as api


def randomstring(length):
    return "".join([random.choice(string.ascii_letters) for n in range(32)])


class CommonDBTests(unittest.TestCase):
    "Self contained super-simple tests in easy syntax, should work on everything between mySQL and Oracle"

    def setUp(self):
        self.engine = "unknown"

    def getEngine(self):
        return self.engine

    def getConnection(self):
        raise NotImplementedError  # "This method must be overriden by a subclass"

    def getCursor(self):
        return self.getConnection().cursor()

    def testConnection(self):
        crsr = self.getCursor()
        assert crsr.__class__.__name__ == "Cursor"

    def testErrorHandlerInherits(self):
        conn = self.getConnection()
        mycallable = lambda connection, cursor, errorclass, errorvalue: 1
        conn.errorhandler = mycallable
        crsr = conn.cursor()
        assert (
            crsr.errorhandler == mycallable
        ), "Error handler on crsr should be same as on connection"

    def testDefaultErrorHandlerConnection(self):
        conn = self.getConnection()
        del conn.messages[:]
        try:
            conn.close()
            conn.commit()  # Should not be able to use connection after it is closed
        except:
            assert len(conn.messages) == 1
            assert len(conn.messages[0]) == 2
            assert conn.messages[0][0] == api.ProgrammingError

    def testOwnErrorHandlerConnection(self):
        mycallable = (
            lambda connection, cursor, errorclass, errorvalue: 1
        )  # does not raise anything
        conn = self.getConnection()
        conn.errorhandler = mycallable
        conn.close()
        conn.commit()  # Should not be able to use connection after it is closed
        assert len(conn.messages) == 0

        conn.errorhandler = None  # This should bring back the standard error handler
        try:
            conn.close()
            conn.commit()  # Should not be able to use connection after it is closed
        except:
            pass
        # The Standard errorhandler appends error to messages attribute
        assert (
            len(conn.messages) > 0
        ), "Setting errorhandler to none  should bring back the standard error handler"

    def testDefaultErrorHandlerCursor(self):
        crsr = self.getConnection().cursor()
        del crsr.messages[:]
        try:
            crsr.execute("SELECT abbtytddrf FROM dasdasd")
        except:
            assert len(crsr.messages) == 1
            assert len(crsr.messages[0]) == 2
            assert crsr.messages[0][0] == api.DatabaseError

    def testOwnErrorHandlerCursor(self):
        mycallable = (
            lambda connection, cursor, errorclass, errorvalue: 1
        )  # does not raise anything
        crsr = self.getConnection().cursor()
        crsr.errorhandler = mycallable
        crsr.execute("SELECT abbtytddrf FROM dasdasd")
        assert len(crsr.messages) == 0

        crsr.errorhandler = None  # This should bring back the standard error handler
        try:
            crsr.execute("SELECT abbtytddrf FROM dasdasd")
        except:
            pass
        # The Standard errorhandler appends error to messages attribute
        assert (
            len(crsr.messages) > 0
        ), "Setting errorhandler to none  should bring back the standard error handler"

    def testUserDefinedConversions(self):
        try:
            duplicatingConverter = lambda aStringField: aStringField * 2
            assert duplicatingConverter("gabba") == "gabbagabba"

            self.helpForceDropOnTblTemp()
            conn = self.getConnection()
            # the variantConversions attribute should not exist on a normal connection object
            self.assertRaises(AttributeError, lambda x: conn.variantConversions[x], [2])
            # create a variantConversions attribute on the connection
            conn.variantConversions = copy.copy(api.variantConversions)
            crsr = conn.cursor()
            tabdef = (
                "CREATE TABLE xx_%s (fldData VARCHAR(100) NOT NULL, fld2 VARCHAR(20))"
                % config.tmp
            )
            crsr.execute(tabdef)
            crsr.execute(
                "INSERT INTO xx_%s(fldData,fld2) VALUES('gabba','booga')" % config.tmp
            )
            crsr.execute(
                "INSERT INTO xx_%s(fldData,fld2) VALUES('hey','yo')" % config.tmp
            )
            # change converter for ALL adoStringTypes columns
            conn.variantConversions[api.adoStringTypes] = duplicatingConverter
            crsr.execute("SELECT fldData,fld2 FROM xx_%s ORDER BY fldData" % config.tmp)

            rows = crsr.fetchall()
            row = rows[0]
            self.assertEqual(row[0], "gabbagabba")
            row = rows[1]
            self.assertEqual(row[0], "heyhey")
            self.assertEqual(row[1], "yoyo")

            upcaseConverter = lambda aStringField: aStringField.upper()
            assert upcaseConverter("upThis") == "UPTHIS"

            # now use a single column converter
            rows.converters[1] = upcaseConverter  # convert second column
            self.assertEqual(row[0], "heyhey")  # first will be unchanged
            self.assertEqual(row[1], "YO")  # second will convert to upper case

        finally:
            try:
                del conn.variantConversions  # Restore the default
            except:
                pass
            self.helpRollbackTblTemp()

    def helpTestDataType(
        self,
        sqlDataTypeString,
        DBAPIDataTypeString,
        pyData,
        pyDataInputAlternatives=None,
        compareAlmostEqual=None,
        allowedReturnValues=None,
    ):
        self.helpForceDropOnTblTemp()
        conn = self.getConnection()
        crsr = conn.cursor()
        tabdef = (
            """
            CREATE TABLE xx_%s (
                fldId integer NOT NULL,
                fldData """
            % config.tmp
            + sqlDataTypeString
            + ")\n"
        )

        crsr.execute(tabdef)

        # Test Null values mapped to None
        crsr.execute("INSERT INTO xx_%s (fldId) VALUES (1)" % config.tmp)

        crsr.execute("SELECT fldId,fldData FROM xx_%s" % config.tmp)
        rs = crsr.fetchone()
        self.assertEqual(rs[1], None)  # Null should be mapped to None
        assert rs[0] == 1

        # Test description related
        descTuple = crsr.description[1]
        assert descTuple[0] in ["fldData", "flddata"], 'was "%s" expected "%s"' % (
            descTuple[0],
            "fldData",
        )

        if DBAPIDataTypeString == "STRING":
            assert descTuple[1] == api.STRING, 'was "%s" expected "%s"' % (
                descTuple[1],
                api.STRING.values,
            )
        elif DBAPIDataTypeString == "NUMBER":
            assert descTuple[1] == api.NUMBER, 'was "%s" expected "%s"' % (
                descTuple[1],
                api.NUMBER.values,
            )
        elif DBAPIDataTypeString == "BINARY":
            assert descTuple[1] == api.BINARY, 'was "%s" expected "%s"' % (
                descTuple[1],
                api.BINARY.values,
            )
        elif DBAPIDataTypeString == "DATETIME":
            assert descTuple[1] == api.DATETIME, 'was "%s" expected "%s"' % (
                descTuple[1],
                api.DATETIME.values,
            )
        elif DBAPIDataTypeString == "ROWID":
            assert descTuple[1] == api.ROWID, 'was "%s" expected "%s"' % (
                descTuple[1],
                api.ROWID.values,
            )
        elif DBAPIDataTypeString == "UUID":
            assert descTuple[1] == api.OTHER, 'was "%s" expected "%s"' % (
                descTuple[1],
                api.OTHER.values,
            )
        else:
            raise NotImplementedError  # "DBAPIDataTypeString not provided"

        # Test data binding
        inputs = [pyData]
        if pyDataInputAlternatives:
            inputs.extend(pyDataInputAlternatives)
        inputs = set(inputs)  # removes redundant string==unicode tests
        fldId = 1
        for inParam in inputs:
            fldId += 1
            try:
                crsr.execute(
                    "INSERT INTO xx_%s (fldId,fldData) VALUES (?,?)" % config.tmp,
                    (fldId, inParam),
                )
            except:
                conn.printADOerrors()
                raise
            crsr.execute(
                "SELECT fldData FROM xx_%s WHERE ?=fldID" % config.tmp, [fldId]
            )
            rs = crsr.fetchone()
            if allowedReturnValues:
                allowedTypes = tuple([type(aRV) for aRV in allowedReturnValues])
                assert isinstance(rs[0], allowedTypes), (
                    'result type "%s" must be one of %s' % (type(rs[0]), allowedTypes)
                )
            else:
                assert isinstance(rs[0], type(pyData)), (
                    'result type "%s" must be instance of %s'
                    % (
                        type(rs[0]),
                        type(pyData),
                    )
                )

            if compareAlmostEqual and DBAPIDataTypeString == "DATETIME":
                iso1 = adodbapi.dateconverter.DateObjectToIsoFormatString(rs[0])
                iso2 = adodbapi.dateconverter.DateObjectToIsoFormatString(pyData)
                self.assertEqual(iso1, iso2)
            elif compareAlmostEqual:
                s = float(pyData)
                v = float(rs[0])
                assert abs(v - s) / s < 0.00001, (
                    "Values not almost equal recvd=%s, expected=%f" % (rs[0], s)
                )
            else:
                if allowedReturnValues:
                    ok = False
                    self.assertTrue(
                        rs[0] in allowedReturnValues,
                        f'Value "{rs[0]!r}" not in {allowedReturnValues}',
                    )
                else:
                    self.assertEqual(
                        rs[0],
                        pyData,
                        'Values are not equal recvd="%s", expected="%s"'
                        % (rs[0], pyData),
                    )

    def testDataTypeFloat(self):
        self.helpTestDataType("real", "NUMBER", 3.45, compareAlmostEqual=True)
        self.helpTestDataType("float", "NUMBER", 1.79e37, compareAlmostEqual=True)

    def testDataTypeDecmal(self):
        self.helpTestDataType(
            "decimal(18,2)",
            "NUMBER",
            3.45,
            allowedReturnValues=["3.45", "3,45", decimal.Decimal("3.45")],
        )
        self.helpTestDataType(
            "numeric(18,2)",
            "NUMBER",
            3.45,
            allowedReturnValues=["3.45", "3,45", decimal.Decimal("3.45")],
        )
        self.helpTestDataType(
            "decimal(20,2)",
            "NUMBER",
            444444444444444444,
            allowedReturnValues=[
                "444444444444444444.00",
                "444444444444444444,00",
                decimal.Decimal("444444444444444444"),
            ],
        )
        if self.getEngine() == "MSSQL":
            self.helpTestDataType(
                "uniqueidentifier",
                "UUID",
                "{71A4F49E-39F3-42B1-A41E-48FF154996E6}",
                allowedReturnValues=["{71A4F49E-39F3-42B1-A41E-48FF154996E6}"],
            )

    def testDataTypeMoney(self):  # v2.1 Cole -- use decimal for money
        if self.getEngine() == "MySQL":
            self.helpTestDataType(
                "DECIMAL(20,4)", "NUMBER", decimal.Decimal("-922337203685477.5808")
            )
        elif self.getEngine() == "PostgreSQL":
            self.helpTestDataType(
                "money",
                "NUMBER",
                decimal.Decimal("-922337203685477.5808"),
                compareAlmostEqual=True,
                allowedReturnValues=[
                    -922337203685477.5808,
                    decimal.Decimal("-922337203685477.5808"),
                ],
            )
        else:
            self.helpTestDataType("smallmoney", "NUMBER", decimal.Decimal("214748.02"))
            self.helpTestDataType(
                "money", "NUMBER", decimal.Decimal("-922337203685477.5808")
            )

    def testDataTypeInt(self):
        if self.getEngine() != "PostgreSQL":
            self.helpTestDataType("tinyint", "NUMBER", 115)
        self.helpTestDataType("smallint", "NUMBER", -32768)
        if self.getEngine() not in ["ACCESS", "PostgreSQL"]:
            self.helpTestDataType(
                "bit", "NUMBER", 1
            )  # Does not work correctly with access
        if self.getEngine() in ["MSSQL", "PostgreSQL"]:
            self.helpTestDataType(
                "bigint",
                "NUMBER",
                3000000000,
                allowedReturnValues=[3000000000, 3000000000],
            )
        self.helpTestDataType("int", "NUMBER", 2147483647)

    def testDataTypeChar(self):
        for sqlDataType in ("char(6)", "nchar(6)"):
            self.helpTestDataType(
                sqlDataType,
                "STRING",
                "spam  ",
                allowedReturnValues=["spam", "spam", "spam  ", "spam  "],
            )

    def testDataTypeVarChar(self):
        if self.getEngine() == "MySQL":
            stringKinds = ["varchar(10)", "text"]
        elif self.getEngine() == "PostgreSQL":
            stringKinds = ["varchar(10)", "text", "character varying"]
        else:
            stringKinds = [
                "varchar(10)",
                "nvarchar(10)",
                "text",
                "ntext",
            ]  # ,"varchar(max)"]

        for sqlDataType in stringKinds:
            self.helpTestDataType(sqlDataType, "STRING", "spam", ["spam"])

    def testDataTypeDate(self):
        if self.getEngine() == "PostgreSQL":
            dt = "timestamp"
        else:
            dt = "datetime"
        self.helpTestDataType(
            dt, "DATETIME", adodbapi.Date(2002, 10, 28), compareAlmostEqual=True
        )
        if self.getEngine() not in ["MySQL", "PostgreSQL"]:
            self.helpTestDataType(
                "smalldatetime",
                "DATETIME",
                adodbapi.Date(2002, 10, 28),
                compareAlmostEqual=True,
            )
        if tag != "pythontime" and self.getEngine() not in [
            "MySQL",
            "PostgreSQL",
        ]:  # fails when using pythonTime
            self.helpTestDataType(
                dt,
                "DATETIME",
                adodbapi.Timestamp(2002, 10, 28, 12, 15, 1),
                compareAlmostEqual=True,
            )

    def testDataTypeBinary(self):
        binfld = b"\x07\x00\xe2\x40*"
        arv = [binfld, adodbapi.Binary(binfld), bytes(binfld)]
        if self.getEngine() == "PostgreSQL":
            self.helpTestDataType(
                "bytea", "BINARY", adodbapi.Binary(binfld), allowedReturnValues=arv
            )
        else:
            self.helpTestDataType(
                "binary(5)", "BINARY", adodbapi.Binary(binfld), allowedReturnValues=arv
            )
            self.helpTestDataType(
                "varbinary(100)",
                "BINARY",
                adodbapi.Binary(binfld),
                allowedReturnValues=arv,
            )
            if self.getEngine() != "MySQL":
                self.helpTestDataType(
                    "image", "BINARY", adodbapi.Binary(binfld), allowedReturnValues=arv
                )

    def helpRollbackTblTemp(self):
        self.helpForceDropOnTblTemp()

    def helpForceDropOnTblTemp(self):
        conn = self.getConnection()
        with conn.cursor() as crsr:
            try:
                crsr.execute("DROP TABLE xx_%s" % config.tmp)
                if not conn.autocommit:
                    conn.commit()
            except:
                pass

    def helpCreateAndPopulateTableTemp(self, crsr):
        tabdef = (
            """
            CREATE TABLE xx_%s (
                fldData INTEGER
            )
            """
            % config.tmp
        )
        try:  # EAFP
            crsr.execute(tabdef)
        except api.DatabaseError:  # was not dropped before
            self.helpForceDropOnTblTemp()  # so drop it now
            crsr.execute(tabdef)
        for i in range(9):  # note: this poor SQL code, but a valid test
            crsr.execute("INSERT INTO xx_%s (fldData) VALUES (%i)" % (config.tmp, i))
            # NOTE: building the test table without using parameter substitution

    def testFetchAll(self):
        crsr = self.getCursor()
        self.helpCreateAndPopulateTableTemp(crsr)
        crsr.execute("SELECT fldData FROM xx_%s" % config.tmp)
        rs = crsr.fetchall()
        assert len(rs) == 9
        # test slice of rows
        i = 3
        for row in rs[3:-2]:  # should have rowid 3..6
            assert row[0] == i
            i += 1
        self.helpRollbackTblTemp()

    def testPreparedStatement(self):
        crsr = self.getCursor()
        self.helpCreateAndPopulateTableTemp(crsr)
        crsr.prepare("SELECT fldData FROM xx_%s" % config.tmp)
        crsr.execute(crsr.command)  # remember the one that was prepared
        rs = crsr.fetchall()
        assert len(rs) == 9
        assert rs[2][0] == 2
        self.helpRollbackTblTemp()

    def testWrongPreparedStatement(self):
        crsr = self.getCursor()
        self.helpCreateAndPopulateTableTemp(crsr)
        crsr.prepare("SELECT * FROM nowhere")
        crsr.execute(
            "SELECT fldData FROM xx_%s" % config.tmp
        )  # should execute this one, not the prepared one
        rs = crsr.fetchall()
        assert len(rs) == 9
        assert rs[2][0] == 2
        self.helpRollbackTblTemp()

    def testIterator(self):
        crsr = self.getCursor()
        self.helpCreateAndPopulateTableTemp(crsr)
        crsr.execute("SELECT fldData FROM xx_%s" % config.tmp)
        for i, row in enumerate(
            crsr
        ):  # using cursor as an iterator, rather than fetchxxx
            assert row[0] == i
        self.helpRollbackTblTemp()

    def testExecuteMany(self):
        crsr = self.getCursor()
        self.helpCreateAndPopulateTableTemp(crsr)
        seq_of_values = [(111,), (222,)]
        crsr.executemany(
            "INSERT INTO xx_%s (fldData) VALUES (?)" % config.tmp, seq_of_values
        )
        if crsr.rowcount == -1:
            print(
                self.getEngine()
                + " Provider does not support rowcount (on .executemany())"
            )
        else:
            self.assertEqual(crsr.rowcount, 2)
        crsr.execute("SELECT fldData FROM xx_%s" % config.tmp)
        rs = crsr.fetchall()
        assert len(rs) == 11
        self.helpRollbackTblTemp()

    def testRowCount(self):
        crsr = self.getCursor()
        self.helpCreateAndPopulateTableTemp(crsr)
        crsr.execute("SELECT fldData FROM xx_%s" % config.tmp)
        if crsr.rowcount == -1:
            # print("provider does not support rowcount on select")
            pass
        else:
            self.assertEqual(crsr.rowcount, 9)
        self.helpRollbackTblTemp()

    def testRowCountNoRecordset(self):
        crsr = self.getCursor()
        self.helpCreateAndPopulateTableTemp(crsr)
        crsr.execute("DELETE FROM xx_%s WHERE fldData >= 5" % config.tmp)
        if crsr.rowcount == -1:
            print(self.getEngine() + " Provider does not support rowcount (on DELETE)")
        else:
            self.assertEqual(crsr.rowcount, 4)
        self.helpRollbackTblTemp()

    def testFetchMany(self):
        crsr = self.getCursor()
        self.helpCreateAndPopulateTableTemp(crsr)
        crsr.execute("SELECT fldData FROM xx_%s" % config.tmp)
        rs = crsr.fetchmany(3)
        assert len(rs) == 3
        rs = crsr.fetchmany(5)
        assert len(rs) == 5
        rs = crsr.fetchmany(5)
        assert len(rs) == 1  # Asked for five, but there is only one left
        self.helpRollbackTblTemp()

    def testFetchManyWithArraySize(self):
        crsr = self.getCursor()
        self.helpCreateAndPopulateTableTemp(crsr)
        crsr.execute("SELECT fldData FROM xx_%s" % config.tmp)
        rs = crsr.fetchmany()
        assert len(rs) == 1  # arraysize Defaults to one
        crsr.arraysize = 4
        rs = crsr.fetchmany()
        assert len(rs) == 4
        rs = crsr.fetchmany()
        assert len(rs) == 4
        rs = crsr.fetchmany()
        assert len(rs) == 0
        self.helpRollbackTblTemp()

    def testErrorConnect(self):
        conn = self.getConnection()
        conn.close()
        self.assertRaises(api.DatabaseError, self.db, "not a valid connect string", {})

    def testRowIterator(self):
        self.helpForceDropOnTblTemp()
        conn = self.getConnection()
        crsr = conn.cursor()
        tabdef = (
            """
            CREATE TABLE xx_%s (
                fldId integer NOT NULL,
                fldTwo integer,
                fldThree integer,
                fldFour integer)
                """
            % config.tmp
        )
        crsr.execute(tabdef)

        inputs = [(2, 3, 4), (102, 103, 104)]
        fldId = 1
        for inParam in inputs:
            fldId += 1
            try:
                crsr.execute(
                    "INSERT INTO xx_%s (fldId,fldTwo,fldThree,fldFour) VALUES (?,?,?,?)"
                    % config.tmp,
                    (fldId, inParam[0], inParam[1], inParam[2]),
                )
            except:
                conn.printADOerrors()
                raise
            crsr.execute(
                "SELECT fldTwo,fldThree,fldFour FROM xx_%s WHERE ?=fldID" % config.tmp,
                [fldId],
            )
            rec = crsr.fetchone()
            # check that stepping through an emulated row works
            for j in range(len(inParam)):
                assert rec[j] == inParam[j], (
                    'returned value:"%s" != test value:"%s"' % (rec[j], inParam[j])
                )
            # check that we can get a complete tuple from a row
            assert (
                tuple(rec) == inParam
            ), f'returned value:"{rec!r}" != test value:"{inParam!r}"'
            # test that slices of rows work
            slice1 = tuple(rec[:-1])
            slice2 = tuple(inParam[0:2])
            assert (
                slice1 == slice2
            ), f'returned value:"{slice1!r}" != test value:"{slice2!r}"'
            # now test named column retrieval
            assert rec["fldTwo"] == inParam[0]
            assert rec.fldThree == inParam[1]
            assert rec.fldFour == inParam[2]
        # test array operation
        # note that the fields vv        vv     vv    are out of order
        crsr.execute("select fldThree,fldFour,fldTwo from xx_%s" % config.tmp)
        recs = crsr.fetchall()
        assert recs[1][0] == 103
        assert recs[0][1] == 4
        assert recs[1]["fldFour"] == 104
        assert recs[0, 0] == 3
        assert recs[0, "fldTwo"] == 2
        assert recs[1, 2] == 102
        for i in range(1):
            for j in range(2):
                assert recs[i][j] == recs[i, j]

    def testFormatParamstyle(self):
        self.helpForceDropOnTblTemp()
        conn = self.getConnection()
        conn.paramstyle = "format"  # test nonstandard use of paramstyle
        crsr = conn.cursor()
        tabdef = (
            """
            CREATE TABLE xx_%s (
                fldId integer NOT NULL,
                fldData varchar(10),
                fldConst varchar(30))
                """
            % config.tmp
        )
        crsr.execute(tabdef)

        inputs = ["one", "two", "three"]
        fldId = 2
        for inParam in inputs:
            fldId += 1
            sql = (
                "INSERT INTO xx_"
                + config.tmp
                + " (fldId,fldConst,fldData) VALUES (%s,'thi%s :may cause? trouble', %s)"
            )
            try:
                crsr.execute(sql, (fldId, inParam))
            except:
                conn.printADOerrors()
                raise
            crsr.execute(
                "SELECT fldData, fldConst FROM xx_" + config.tmp + " WHERE %s=fldID",
                [fldId],
            )
            rec = crsr.fetchone()
            self.assertEqual(
                rec[0],
                inParam,
                'returned value:"%s" != test value:"%s"' % (rec[0], inParam),
            )
            self.assertEqual(rec[1], "thi%s :may cause? trouble")

        # now try an operation with a "%s" as part of a literal
        sel = (
            "insert into xx_" + config.tmp + " (fldId,fldData) VALUES (%s,'four%sfive')"
        )
        params = (20,)
        crsr.execute(sel, params)

        # test the .query implementation
        assert "(?," in crsr.query, 'expected:"%s" in "%s"' % ("(?,", crsr.query)
        # test the .command attribute
        assert crsr.command == sel, 'expected:"%s" but found "%s"' % (sel, crsr.command)

        # test the .parameters attribute
        self.assertEqual(crsr.parameters, params)
        # now make sure the data made it
        crsr.execute("SELECT fldData FROM xx_%s WHERE fldID=20" % config.tmp)
        rec = crsr.fetchone()
        self.assertEqual(rec[0], "four%sfive")

    def testNamedParamstyle(self):
        self.helpForceDropOnTblTemp()
        conn = self.getConnection()
        crsr = conn.cursor()
        crsr.paramstyle = "named"  # test nonstandard use of paramstyle
        tabdef = (
            """
            CREATE TABLE xx_%s (
                fldId integer NOT NULL,
                fldData varchar(10))
                """
            % config.tmp
        )
        crsr.execute(tabdef)

        inputs = ["four", "five", "six"]
        fldId = 10
        for inParam in inputs:
            fldId += 1
            try:
                crsr.execute(
                    "INSERT INTO xx_%s (fldId,fldData) VALUES (:Id,:f_Val)"
                    % config.tmp,
                    {"f_Val": inParam, "Id": fldId},
                )
            except:
                conn.printADOerrors()
                raise
            crsr.execute(
                "SELECT fldData FROM xx_%s WHERE fldID=:Id" % config.tmp, {"Id": fldId}
            )
            rec = crsr.fetchone()
            self.assertEqual(
                rec[0],
                inParam,
                'returned value:"%s" != test value:"%s"' % (rec[0], inParam),
            )
        # now a test with a ":" as part of a literal
        crsr.execute(
            "insert into xx_%s (fldId,fldData) VALUES (:xyz,'six:five')" % config.tmp,
            {"xyz": 30},
        )
        crsr.execute("SELECT fldData FROM xx_%s WHERE fldID=30" % config.tmp)
        rec = crsr.fetchone()
        self.assertEqual(rec[0], "six:five")

    def testPyformatParamstyle(self):
        self.helpForceDropOnTblTemp()
        conn = self.getConnection()
        crsr = conn.cursor()
        crsr.paramstyle = "pyformat"  # test nonstandard use of paramstyle
        tabdef = (
            """
            CREATE TABLE xx_%s (
                fldId integer NOT NULL,
                fldData varchar(10))
                """
            % config.tmp
        )
        crsr.execute(tabdef)

        inputs = ["four", "five", "six"]
        fldId = 10
        for inParam in inputs:
            fldId += 1
            try:
                crsr.execute(
                    "INSERT INTO xx_%s (fldId,fldData) VALUES (%%(Id)s,%%(f_Val)s)"
                    % config.tmp,
                    {"f_Val": inParam, "Id": fldId},
                )
            except:
                conn.printADOerrors()
                raise
            crsr.execute(
                "SELECT fldData FROM xx_%s WHERE fldID=%%(Id)s" % config.tmp,
                {"Id": fldId},
            )
            rec = crsr.fetchone()
            self.assertEqual(
                rec[0],
                inParam,
                'returned value:"%s" != test value:"%s"' % (rec[0], inParam),
            )
        # now a test with a "%" as part of a literal
        crsr.execute(
            "insert into xx_%s (fldId,fldData) VALUES (%%(xyz)s,'six%%five')"
            % config.tmp,
            {"xyz": 30},
        )
        crsr.execute("SELECT fldData FROM xx_%s WHERE fldID=30" % config.tmp)
        rec = crsr.fetchone()
        self.assertEqual(rec[0], "six%five")

    def testAutomaticParamstyle(self):
        self.helpForceDropOnTblTemp()
        conn = self.getConnection()
        conn.paramstyle = "dynamic"  # test nonstandard use of paramstyle
        crsr = conn.cursor()
        tabdef = (
            """
            CREATE TABLE xx_%s (
                fldId integer NOT NULL,
                fldData varchar(10),
                fldConst varchar(30))
                """
            % config.tmp
        )
        crsr.execute(tabdef)
        inputs = ["one", "two", "three"]
        fldId = 2
        for inParam in inputs:
            fldId += 1
            try:
                crsr.execute(
                    "INSERT INTO xx_"
                    + config.tmp
                    + " (fldId,fldConst,fldData) VALUES (?,'thi%s :may cause? troub:1e', ?)",
                    (fldId, inParam),
                )
            except:
                conn.printADOerrors()
                raise
            trouble = "thi%s :may cause? troub:1e"
            crsr.execute(
                "SELECT fldData, fldConst FROM xx_" + config.tmp + " WHERE ?=fldID",
                [fldId],
            )
            rec = crsr.fetchone()
            self.assertEqual(
                rec[0],
                inParam,
                'returned value:"%s" != test value:"%s"' % (rec[0], inParam),
            )
            self.assertEqual(rec[1], trouble)
        #     inputs = [u'four',u'five',u'six']
        fldId = 10
        for inParam in inputs:
            fldId += 1
            try:
                crsr.execute(
                    "INSERT INTO xx_%s (fldId,fldData) VALUES (:Id,:f_Val)"
                    % config.tmp,
                    {"f_Val": inParam, "Id": fldId},
                )
            except:
                conn.printADOerrors()
                raise
            crsr.execute(
                "SELECT fldData FROM xx_%s WHERE :Id=fldID" % config.tmp, {"Id": fldId}
            )
            rec = crsr.fetchone()
            self.assertEqual(
                rec[0],
                inParam,
                'returned value:"%s" != test value:"%s"' % (rec[0], inParam),
            )
        # now a test with a ":" as part of a literal -- and use a prepared query
        ppdcmd = (
            "insert into xx_%s (fldId,fldData) VALUES (:xyz,'six:five')" % config.tmp
        )
        crsr.prepare(ppdcmd)
        crsr.execute(ppdcmd, {"xyz": 30})
        crsr.execute("SELECT fldData FROM xx_%s WHERE fldID=30" % config.tmp)
        rec = crsr.fetchone()
        self.assertEqual(rec[0], "six:five")

    def testRollBack(self):
        conn = self.getConnection()
        crsr = conn.cursor()
        assert not crsr.connection.autocommit, "Unexpected beginning condition"
        self.helpCreateAndPopulateTableTemp(crsr)
        crsr.connection.commit()  # commit the first bunch

        crsr.execute("INSERT INTO xx_%s (fldData) VALUES(100)" % config.tmp)

        selectSql = "SELECT fldData FROM xx_%s WHERE fldData=100" % config.tmp
        crsr.execute(selectSql)
        rs = crsr.fetchall()
        assert len(rs) == 1
        self.conn.rollback()
        crsr.execute(selectSql)
        assert (
            crsr.fetchone() is None
        ), "cursor.fetchone should return None if a query retrieves no rows"
        crsr.execute("SELECT fldData from xx_%s" % config.tmp)
        rs = crsr.fetchall()
        assert len(rs) == 9, "the original records should still be present"
        self.helpRollbackTblTemp()

    def testCommit(self):
        try:
            con2 = self.getAnotherConnection()
        except NotImplementedError:
            return  # should be "SKIP" for ACCESS
        assert not con2.autocommit, "default should be manual commit"
        crsr = con2.cursor()
        self.helpCreateAndPopulateTableTemp(crsr)

        crsr.execute("INSERT INTO xx_%s (fldData) VALUES(100)" % config.tmp)
        con2.commit()

        selectSql = "SELECT fldData FROM xx_%s WHERE fldData=100" % config.tmp
        crsr.execute(selectSql)
        rs = crsr.fetchall()
        assert len(rs) == 1
        crsr.close()
        con2.close()
        conn = self.getConnection()
        crsr = self.getCursor()
        with conn.cursor() as crsr:
            crsr.execute(selectSql)
            rs = crsr.fetchall()
            assert len(rs) == 1
            assert rs[0][0] == 100
        self.helpRollbackTblTemp()

    def testAutoRollback(self):
        try:
            con2 = self.getAnotherConnection()
        except NotImplementedError:
            return  # should be "SKIP" for ACCESS
        assert not con2.autocommit, "unexpected beginning condition"
        crsr = con2.cursor()
        self.helpCreateAndPopulateTableTemp(crsr)
        crsr.execute("INSERT INTO xx_%s (fldData) VALUES(100)" % config.tmp)
        selectSql = "SELECT fldData FROM xx_%s WHERE fldData=100" % config.tmp
        crsr.execute(selectSql)
        rs = crsr.fetchall()
        assert len(rs) == 1
        crsr.close()
        con2.close()
        crsr = self.getCursor()
        try:
            crsr.execute(
                selectSql
            )  # closing the connection should have forced rollback
            row = crsr.fetchone()
        except api.DatabaseError:
            row = None  # if the entire table disappeared the rollback was perfect and the test passed
        assert (
            row is None
        ), f"cursor.fetchone should return None if a query retrieves no rows. Got {row!r}"
        self.helpRollbackTblTemp()

    def testAutoCommit(self):
        try:
            ac_conn = self.getAnotherConnection({"autocommit": True})
        except NotImplementedError:
            return  # should be "SKIP" for ACCESS
        crsr = ac_conn.cursor()
        self.helpCreateAndPopulateTableTemp(crsr)
        crsr.execute("INSERT INTO xx_%s (fldData) VALUES(100)" % config.tmp)
        crsr.close()
        with self.getCursor() as crsr:
            selectSql = "SELECT fldData from xx_%s" % config.tmp
            crsr.execute(
                selectSql
            )  # closing the connection should _not_ have forced rollback
            rs = crsr.fetchall()
            assert len(rs) == 10, "all records should still be present"
        ac_conn.close()
        self.helpRollbackTblTemp()

    def testSwitchedAutoCommit(self):
        try:
            ac_conn = self.getAnotherConnection()
        except NotImplementedError:
            return  # should be "SKIP" for ACCESS
        ac_conn.autocommit = True
        crsr = ac_conn.cursor()
        self.helpCreateAndPopulateTableTemp(crsr)
        crsr.execute("INSERT INTO xx_%s (fldData) VALUES(100)" % config.tmp)
        crsr.close()
        conn = self.getConnection()
        ac_conn.close()
        with self.getCursor() as crsr:
            selectSql = "SELECT fldData from xx_%s" % config.tmp
            crsr.execute(
                selectSql
            )  # closing the connection should _not_ have forced rollback
            rs = crsr.fetchall()
            assert len(rs) == 10, "all records should still be present"
        self.helpRollbackTblTemp()

    def testExtendedTypeHandling(self):
        class XtendString(str):
            pass

        class XtendInt(int):
            pass

        class XtendFloat(float):
            pass

        xs = XtendString(randomstring(30))
        xi = XtendInt(random.randint(-100, 500))
        xf = XtendFloat(random.random())
        self.helpForceDropOnTblTemp()
        conn = self.getConnection()
        crsr = conn.cursor()
        tabdef = (
            """
            CREATE TABLE xx_%s (
                s VARCHAR(40) NOT NULL,
                i INTEGER NOT NULL,
                f REAL NOT NULL)"""
            % config.tmp
        )
        crsr.execute(tabdef)
        crsr.execute(
            "INSERT INTO xx_%s (s, i, f) VALUES (?, ?, ?)" % config.tmp, (xs, xi, xf)
        )
        crsr.close()
        conn = self.getConnection()
        with self.getCursor() as crsr:
            selectSql = "SELECT s, i, f from xx_%s" % config.tmp
            crsr.execute(
                selectSql
            )  # closing the connection should _not_ have forced rollback
            row = crsr.fetchone()
            self.assertEqual(row.s, xs)
            self.assertEqual(row.i, xi)
            self.assertAlmostEqual(row.f, xf)
        self.helpRollbackTblTemp()


class TestADOwithSQLServer(CommonDBTests):
    def setUp(self):
        self.conn = config.dbSqlServerconnect(
            *config.connStrSQLServer[0], **config.connStrSQLServer[1]
        )
        self.conn.timeout = 30  # turn timeout back up
        self.engine = "MSSQL"
        self.db = config.dbSqlServerconnect

    def tearDown(self):
        try:
            self.conn.rollback()
        except:
            pass
        try:
            self.conn.close()
        except:
            pass
        self.conn = None

    def getConnection(self):
        return self.conn

    def getAnotherConnection(self, addkeys=None):
        keys = config.connStrSQLServer[1].copy()
        if addkeys:
            keys.update(addkeys)
        return config.dbSqlServerconnect(*config.connStrSQLServer[0], **keys)

    def testVariableReturningStoredProcedure(self):
        crsr = self.conn.cursor()
        spdef = """
            CREATE PROCEDURE sp_DeleteMeOnlyForTesting
                @theInput varchar(50),
                @theOtherInput varchar(50),
                @theOutput varchar(100) OUTPUT
            AS
                SET @theOutput=@theInput+@theOtherInput
                    """
        try:
            crsr.execute("DROP PROCEDURE sp_DeleteMeOnlyForTesting")
            self.conn.commit()
        except:  # Make sure it is empty
            pass
        crsr.execute(spdef)

        retvalues = crsr.callproc(
            "sp_DeleteMeOnlyForTesting", ("Dodsworth", "Anne", "              ")
        )
        assert retvalues[0] == "Dodsworth", f'{retvalues[0]!r} is not "Dodsworth"'
        assert retvalues[1] == "Anne", f'{retvalues[1]!r} is not "Anne"'
        assert (
            retvalues[2] == "DodsworthAnne"
        ), f'{retvalues[2]!r} is not "DodsworthAnne"'
        self.conn.rollback()

    def testMultipleSetReturn(self):
        crsr = self.getCursor()
        self.helpCreateAndPopulateTableTemp(crsr)

        spdef = """
            CREATE PROCEDURE sp_DeleteMe_OnlyForTesting
            AS
                SELECT fldData FROM xx_%s ORDER BY fldData ASC
                SELECT fldData From xx_%s where fldData = -9999
                SELECT fldData FROM xx_%s ORDER BY fldData DESC
                    """ % (
            config.tmp,
            config.tmp,
            config.tmp,
        )
        try:
            crsr.execute("DROP PROCEDURE sp_DeleteMe_OnlyForTesting")
            self.conn.commit()
        except:  # Make sure it is empty
            pass
        crsr.execute(spdef)

        retvalues = crsr.callproc("sp_DeleteMe_OnlyForTesting")
        row = crsr.fetchone()
        self.assertEqual(row[0], 0)
        assert crsr.nextset() == True, "Operation should succeed"
        assert not crsr.fetchall(), "Should be an empty second set"
        assert crsr.nextset() == True, "third set should be present"
        rowdesc = crsr.fetchall()
        self.assertEqual(rowdesc[0][0], 8)
        assert crsr.nextset() is None, "No more return sets, should return None"

        self.helpRollbackTblTemp()

    def testDatetimeProcedureParameter(self):
        crsr = self.conn.cursor()
        spdef = """
            CREATE PROCEDURE sp_DeleteMeOnlyForTesting
                @theInput DATETIME,
                @theOtherInput varchar(50),
                @theOutput varchar(100) OUTPUT
            AS
                SET @theOutput = CONVERT(CHARACTER(20), @theInput, 0) + @theOtherInput
                    """
        try:
            crsr.execute("DROP PROCEDURE sp_DeleteMeOnlyForTesting")
            self.conn.commit()
        except:  # Make sure it is empty
            pass
        crsr.execute(spdef)

        result = crsr.callproc(
            "sp_DeleteMeOnlyForTesting",
            [adodbapi.Timestamp(2014, 12, 25, 0, 1, 0), "Beep", " " * 30],
        )

        assert result[2] == "Dec 25 2014 12:01AM Beep", 'value was="%s"' % result[2]
        self.conn.rollback()

    def testIncorrectStoredProcedureParameter(self):
        crsr = self.conn.cursor()
        spdef = """
            CREATE PROCEDURE sp_DeleteMeOnlyForTesting
                @theInput DATETIME,
                @theOtherInput varchar(50),
                @theOutput varchar(100) OUTPUT
            AS
                SET @theOutput = CONVERT(CHARACTER(20), @theInput) + @theOtherInput
                    """
        try:
            crsr.execute("DROP PROCEDURE sp_DeleteMeOnlyForTesting")
            self.conn.commit()
        except:  # Make sure it is empty
            pass
        crsr.execute(spdef)

        # calling the sproc with a string for the first parameter where a DateTime is expected
        result = tryconnection.try_operation_with_expected_exception(
            (api.DataError, api.DatabaseError),
            crsr.callproc,
            ["sp_DeleteMeOnlyForTesting"],
            {"parameters": ["this is wrong", "Anne", "not Alice"]},
        )
        if result[0]:  # the expected exception was raised
            assert "@theInput" in str(result[1]) or "DatabaseError" in str(
                result
            ), "Identifies the wrong erroneous parameter"
        else:
            assert result[0], result[1]  # incorrect or no exception
        self.conn.rollback()


class TestADOwithAccessDB(CommonDBTests):
    def setUp(self):
        self.conn = config.dbAccessconnect(
            *config.connStrAccess[0], **config.connStrAccess[1]
        )
        self.conn.timeout = 30  # turn timeout back up
        self.engine = "ACCESS"
        self.db = config.dbAccessconnect

    def tearDown(self):
        try:
            self.conn.rollback()
        except:
            pass
        try:
            self.conn.close()
        except:
            pass
        self.conn = None

    def getConnection(self):
        return self.conn

    def getAnotherConnection(self, addkeys=None):
        raise NotImplementedError("Jet cannot use a second connection to the database")

    def testOkConnect(self):
        c = self.db(*config.connStrAccess[0], **config.connStrAccess[1])
        assert c is not None
        c.close()


class TestADOwithMySql(CommonDBTests):
    def setUp(self):
        self.conn = config.dbMySqlconnect(
            *config.connStrMySql[0], **config.connStrMySql[1]
        )
        self.conn.timeout = 30  # turn timeout back up
        self.engine = "MySQL"
        self.db = config.dbMySqlconnect

    def tearDown(self):
        try:
            self.conn.rollback()
        except:
            pass
        try:
            self.conn.close()
        except:
            pass
        self.conn = None

    def getConnection(self):
        return self.conn

    def getAnotherConnection(self, addkeys=None):
        keys = config.connStrMySql[1].copy()
        if addkeys:
            keys.update(addkeys)
        return config.dbMySqlconnect(*config.connStrMySql[0], **keys)

    def testOkConnect(self):
        c = self.db(*config.connStrMySql[0], **config.connStrMySql[1])
        assert c is not None

    # def testStoredProcedure(self):
    #     crsr = self.conn.cursor()
    #     try:
    #         crsr.execute("DROP PROCEDURE DeleteMeOnlyForTesting")
    #         self.conn.commit()
    #     except:  # Make sure it is empty
    #         pass
    #     spdef = """
    #             DELIMITER $$
    #             CREATE PROCEDURE DeleteMeOnlyForTesting (onein CHAR(10), twoin CHAR(10), OUT theout CHAR(20))
    #             DETERMINISTIC
    #              BEGIN
    #                 SET theout = onein //|| twoin;
    #                 /* (SELECT 'a small string' as result; */
    #                 END $$
    #             """
    #     crsr.execute(spdef)
    #     retvalues = crsr.callproc(
    #         "DeleteMeOnlyForTesting", ("Dodsworth", "Anne", "              ")
    #     )
    #     # print(f"return value (mysql)={crsr.returnValue!r}")
    #     assert retvalues[0] == "Dodsworth", f'{retvalues[0]!r} is not "Dodsworth"'
    #     assert retvalues[1] == "Anne", f'{retvalues[1]!r} is not "Anne"'
    #     assert (
    #         retvalues[2] == "DodsworthAnne"
    #     ), f'{retvalues[2]!r} is not "DodsworthAnne"'
    #     try:
    #         crsr.execute("DROP PROCEDURE, DeleteMeOnlyForTesting")
    #         self.conn.commit()
    #     except:  # Make sure it is empty
    #         pass


class TestADOwithPostgres(CommonDBTests):
    def setUp(self):
        self.conn = config.dbPostgresConnect(
            *config.connStrPostgres[0], **config.connStrPostgres[1]
        )
        self.conn.timeout = 30  # turn timeout back up
        self.engine = "PostgreSQL"
        self.db = config.dbPostgresConnect

    def tearDown(self):
        try:
            self.conn.rollback()
        except:
            pass
        try:
            self.conn.close()
        except:
            pass
        self.conn = None

    def getConnection(self):
        return self.conn

    def getAnotherConnection(self, addkeys=None):
        keys = config.connStrPostgres[1].copy()
        if addkeys:
            keys.update(addkeys)
        return config.dbPostgresConnect(*config.connStrPostgres[0], **keys)

    def testOkConnect(self):
        c = self.db(*config.connStrPostgres[0], **config.connStrPostgres[1])
        assert c is not None

    # def testStoredProcedure(self):
    #     crsr = self.conn.cursor()
    #     spdef = """
    #         CREATE OR REPLACE FUNCTION DeleteMeOnlyForTesting (text, text)
    #         RETURNS text AS $funk$
    #         BEGIN
    #           RETURN $1 || $2;
    #         END;
    #         $funk$
    #         LANGUAGE SQL;
    #         """

    #     crsr.execute(spdef)
    #     retvalues = crsr.callproc(
    #         "DeleteMeOnlyForTesting", ("Dodsworth", "Anne", "              ")
    #     )
    #     # print(f"return value (pg)={crsr.returnValue!r}")
    #     assert retvalues[0] == "Dodsworth", f'{retvalues[0]!r} is not "Dodsworth"'
    #     assert retvalues[1] == "Anne", f'{retvalues[1]!r} is not "Anne"'
    #     assert (
    #         retvalues[2] == "DodsworthAnne"
    #     ), f'{retvalues[2]!r} is not "DodsworthAnne"'
    #     self.conn.rollback()
    #     try:
    #         crsr.execute("DROP PROCEDURE, DeleteMeOnlyForTesting")
    #         self.conn.commit()
    #     except:  # Make sure it is empty
    #         pass


class TimeConverterInterfaceTest(unittest.TestCase):
    def testIDate(self):
        assert self.tc.Date(1990, 2, 2)

    def testITime(self):
        assert self.tc.Time(13, 2, 2)

    def testITimestamp(self):
        assert self.tc.Timestamp(1990, 2, 2, 13, 2, 1)

    def testIDateObjectFromCOMDate(self):
        assert self.tc.DateObjectFromCOMDate(37435.7604282)

    def testICOMDate(self):
        assert hasattr(self.tc, "COMDate")

    def testExactDate(self):
        d = self.tc.Date(1994, 11, 15)
        comDate = self.tc.COMDate(d)
        correct = 34653.0
        assert comDate == correct, comDate

    def testExactTimestamp(self):
        d = self.tc.Timestamp(1994, 11, 15, 12, 0, 0)
        comDate = self.tc.COMDate(d)
        correct = 34653.5
        self.assertEqual(comDate, correct)

        d = self.tc.Timestamp(2003, 5, 6, 14, 15, 17)
        comDate = self.tc.COMDate(d)
        correct = 37747.593946759262
        self.assertEqual(comDate, correct)

    def testIsoFormat(self):
        d = self.tc.Timestamp(1994, 11, 15, 12, 3, 10)
        iso = self.tc.DateObjectToIsoFormatString(d)
        self.assertEqual(str(iso[:19]), "1994-11-15 12:03:10")

        dt = self.tc.Date(2003, 5, 2)
        iso = self.tc.DateObjectToIsoFormatString(dt)
        self.assertEqual(str(iso[:10]), "2003-05-02")


class TestPythonTimeConverter(TimeConverterInterfaceTest):
    def setUp(self):
        self.tc = api.pythonTimeConverter()

    def testCOMDate(self):
        mk = time.mktime((2002, 6, 28, 18, 15, 1, 4, 31 + 28 + 31 + 30 + 31 + 28, -1))
        t = time.localtime(mk)
        # Fri, 28 Jun 2002 18:15:01 +0000
        cmd = self.tc.COMDate(t)
        assert abs(cmd - 37435.7604282) < 1.0 / 24, "%f more than an hour wrong" % cmd

    def testDateObjectFromCOMDate(self):
        cmd = self.tc.DateObjectFromCOMDate(37435.7604282)
        t1 = time.gmtime(
            time.mktime((2002, 6, 28, 0, 14, 1, 4, 31 + 28 + 31 + 30 + 31 + 28, -1))
        )
        # there are errors in the implementation of gmtime which we ignore
        t2 = time.gmtime(
            time.mktime((2002, 6, 29, 12, 14, 2, 4, 31 + 28 + 31 + 30 + 31 + 28, -1))
        )
        assert t1 < cmd < t2, f'"{cmd}" should be about 2002-6-28 12:15:01'

    def testDate(self):
        t1 = time.mktime((2002, 6, 28, 18, 15, 1, 4, 31 + 28 + 31 + 30 + 31 + 30, 0))
        t2 = time.mktime((2002, 6, 30, 18, 15, 1, 4, 31 + 28 + 31 + 30 + 31 + 28, 0))
        obj = self.tc.Date(2002, 6, 29)
        assert t1 < time.mktime(obj) < t2, obj

    def testTime(self):
        self.assertEqual(
            self.tc.Time(18, 15, 2), time.gmtime(18 * 60 * 60 + 15 * 60 + 2)
        )

    def testTimestamp(self):
        t1 = time.localtime(
            time.mktime((2002, 6, 28, 18, 14, 1, 4, 31 + 28 + 31 + 30 + 31 + 28, -1))
        )
        t2 = time.localtime(
            time.mktime((2002, 6, 28, 18, 16, 1, 4, 31 + 28 + 31 + 30 + 31 + 28, -1))
        )
        obj = self.tc.Timestamp(2002, 6, 28, 18, 15, 2)
        assert t1 < obj < t2, obj


class TestPythonDateTimeConverter(TimeConverterInterfaceTest):
    def setUp(self):
        self.tc = api.pythonDateTimeConverter()

    def testCOMDate(self):
        t = datetime.datetime(2002, 6, 28, 18, 15, 1)
        # Fri, 28 Jun 2002 18:15:01 +0000
        cmd = self.tc.COMDate(t)
        assert abs(cmd - 37435.7604282) < 1.0 / 24, "more than an hour wrong"

    def testDateObjectFromCOMDate(self):
        cmd = self.tc.DateObjectFromCOMDate(37435.7604282)
        t1 = datetime.datetime(2002, 6, 28, 18, 14, 1)
        t2 = datetime.datetime(2002, 6, 28, 18, 16, 1)
        assert t1 < cmd < t2, cmd

        tx = datetime.datetime(
            2002, 6, 28, 18, 14, 1, 900000
        )  # testing that microseconds don't become milliseconds
        c1 = self.tc.DateObjectFromCOMDate(self.tc.COMDate(tx))
        assert t1 < c1 < t2, c1

    def testDate(self):
        t1 = datetime.date(2002, 6, 28)
        t2 = datetime.date(2002, 6, 30)
        obj = self.tc.Date(2002, 6, 29)
        assert t1 < obj < t2, obj

    def testTime(self):
        self.assertEqual(self.tc.Time(18, 15, 2).isoformat()[:8], "18:15:02")

    def testTimestamp(self):
        t1 = datetime.datetime(2002, 6, 28, 18, 14, 1)
        t2 = datetime.datetime(2002, 6, 28, 18, 16, 1)
        obj = self.tc.Timestamp(2002, 6, 28, 18, 15, 2)
        assert t1 < obj < t2, obj


suites = [
    unittest.defaultTestLoader.loadTestsFromModule(TestPythonDateTimeConverter, "test")
]
if config.doTimeTest:
    suites.append(
        unittest.defaultTestLoader.loadTestsFromModule(TestPythonTimeConverter, "test")
    )
if config.doAccessTest:
    suites.append(
        unittest.defaultTestLoader.loadTestsFromModule(TestADOwithAccessDB, "test")
    )
if config.doSqlServerTest:
    suites.append(
        unittest.defaultTestLoader.loadTestsFromModule(TestADOwithSQLServer, "test")
    )
if config.doMySqlTest:
    suites.append(
        unittest.defaultTestLoader.loadTestsFromModule(TestADOwithMySql, "test")
    )
if config.doPostgresTest:
    suites.append(
        unittest.defaultTestLoader.loadTestsFromModule(TestADOwithPostgres, "test")
    )


class cleanup_manager:
    def __enter__(self):
        pass

    def __exit__(self, exc_type, exc_val, exc_tb):
        config.cleanup(config.testfolder, config.mdb_name)


suite = unittest.TestSuite(suites)
if __name__ == "__main__":
    mysuite = copy.deepcopy(suite)
    with cleanup_manager():
        defaultDateConverter = adodbapi.dateconverter
        print(__doc__)
        print("Default Date Converter is %s" % (defaultDateConverter,))
        dateconverter = defaultDateConverter
        unittest.TextTestRunner().run(mysuite)

        if config.doTimeTest:
            mysuite = copy.deepcopy(
                suite
            )  # work around a side effect of unittest.TextTestRunner
            adodbapi.adodbapi.dateconverter = api.pythonTimeConverter()
            print("Changed dateconverter to ")
            print(adodbapi.adodbapi.dateconverter)
            unittest.TextTestRunner().run(mysuite)

# === NexusCore/openenv\Lib\site-packages\google\protobuf\internal\python_message.py ===
# Protocol Buffers - Google's data interchange format
# Copyright 2008 Google Inc.  All rights reserved.
#
# Use of this source code is governed by a BSD-style
# license that can be found in the LICENSE file or at
# https://developers.google.com/open-source/licenses/bsd

# This code is meant to work on Python 2.4 and above only.
#
# TODO: Helpers for verbose, common checks like seeing if a
# descriptor's cpp_type is CPPTYPE_MESSAGE.

"""Contains a metaclass and helper functions used to create
protocol message classes from Descriptor objects at runtime.

Recall that a metaclass is the "type" of a class.
(A class is to a metaclass what an instance is to a class.)

In this case, we use the GeneratedProtocolMessageType metaclass
to inject all the useful functionality into the classes
output by the protocol compiler at compile-time.

The upshot of all this is that the real implementation
details for ALL pure-Python protocol buffers are *here in
this file*.
"""

__author__ = 'robinson@google.com (Will Robinson)'

from io import BytesIO
import struct
import sys
import warnings
import weakref

from google.protobuf import descriptor as descriptor_mod
from google.protobuf import message as message_mod
from google.protobuf import text_format
# We use "as" to avoid name collisions with variables.
from google.protobuf.internal import api_implementation
from google.protobuf.internal import containers
from google.protobuf.internal import decoder
from google.protobuf.internal import encoder
from google.protobuf.internal import enum_type_wrapper
from google.protobuf.internal import extension_dict
from google.protobuf.internal import message_listener as message_listener_mod
from google.protobuf.internal import type_checkers
from google.protobuf.internal import well_known_types
from google.protobuf.internal import wire_format

_FieldDescriptor = descriptor_mod.FieldDescriptor
_AnyFullTypeName = 'google.protobuf.Any'
_ExtensionDict = extension_dict._ExtensionDict

class GeneratedProtocolMessageType(type):

  """Metaclass for protocol message classes created at runtime from Descriptors.

  We add implementations for all methods described in the Message class.  We
  also create properties to allow getting/setting all fields in the protocol
  message.  Finally, we create slots to prevent users from accidentally
  "setting" nonexistent fields in the protocol message, which then wouldn't get
  serialized / deserialized properly.

  The protocol compiler currently uses this metaclass to create protocol
  message classes at runtime.  Clients can also manually create their own
  classes at runtime, as in this example:

  mydescriptor = Descriptor(.....)
  factory = symbol_database.Default()
  factory.pool.AddDescriptor(mydescriptor)
  MyProtoClass = factory.GetPrototype(mydescriptor)
  myproto_instance = MyProtoClass()
  myproto.foo_field = 23
  ...
  """

  # Must be consistent with the protocol-compiler code in
  # proto2/compiler/internal/generator.*.
  _DESCRIPTOR_KEY = 'DESCRIPTOR'

  def __new__(cls, name, bases, dictionary):
    """Custom allocation for runtime-generated class types.

    We override __new__ because this is apparently the only place
    where we can meaningfully set __slots__ on the class we're creating(?).
    (The interplay between metaclasses and slots is not very well-documented).

    Args:
      name: Name of the class (ignored, but required by the
        metaclass protocol).
      bases: Base classes of the class we're constructing.
        (Should be message.Message).  We ignore this field, but
        it's required by the metaclass protocol
      dictionary: The class dictionary of the class we're
        constructing.  dictionary[_DESCRIPTOR_KEY] must contain
        a Descriptor object describing this protocol message
        type.

    Returns:
      Newly-allocated class.

    Raises:
      RuntimeError: Generated code only work with python cpp extension.
    """
    descriptor = dictionary[GeneratedProtocolMessageType._DESCRIPTOR_KEY]

    if isinstance(descriptor, str):
      raise RuntimeError('The generated code only work with python cpp '
                         'extension, but it is using pure python runtime.')

    # If a concrete class already exists for this descriptor, don't try to
    # create another.  Doing so will break any messages that already exist with
    # the existing class.
    #
    # The C++ implementation appears to have its own internal `PyMessageFactory`
    # to achieve similar results.
    #
    # This most commonly happens in `text_format.py` when using descriptors from
    # a custom pool; it calls symbol_database.Global().getPrototype() on a
    # descriptor which already has an existing concrete class.
    new_class = getattr(descriptor, '_concrete_class', None)
    if new_class:
      return new_class

    if descriptor.full_name in well_known_types.WKTBASES:
      bases += (well_known_types.WKTBASES[descriptor.full_name],)
    _AddClassAttributesForNestedExtensions(descriptor, dictionary)
    _AddSlots(descriptor, dictionary)

    superclass = super(GeneratedProtocolMessageType, cls)
    new_class = superclass.__new__(cls, name, bases, dictionary)
    return new_class

  def __init__(cls, name, bases, dictionary):
    """Here we perform the majority of our work on the class.
    We add enum getters, an __init__ method, implementations
    of all Message methods, and properties for all fields
    in the protocol type.

    Args:
      name: Name of the class (ignored, but required by the
        metaclass protocol).
      bases: Base classes of the class we're constructing.
        (Should be message.Message).  We ignore this field, but
        it's required by the metaclass protocol
      dictionary: The class dictionary of the class we're
        constructing.  dictionary[_DESCRIPTOR_KEY] must contain
        a Descriptor object describing this protocol message
        type.
    """
    descriptor = dictionary[GeneratedProtocolMessageType._DESCRIPTOR_KEY]

    # If this is an _existing_ class looked up via `_concrete_class` in the
    # __new__ method above, then we don't need to re-initialize anything.
    existing_class = getattr(descriptor, '_concrete_class', None)
    if existing_class:
      assert existing_class is cls, (
          'Duplicate `GeneratedProtocolMessageType` created for descriptor %r'
          % (descriptor.full_name))
      return

    cls._message_set_decoders_by_tag = {}
    cls._fields_by_tag = {}
    if (descriptor.has_options and
        descriptor.GetOptions().message_set_wire_format):
      cls._message_set_decoders_by_tag[decoder.MESSAGE_SET_ITEM_TAG] = (
          decoder.MessageSetItemDecoder(descriptor),
          None,
      )

    # Attach stuff to each FieldDescriptor for quick lookup later on.
    for field in descriptor.fields:
      _AttachFieldHelpers(cls, field)

    if descriptor.is_extendable and hasattr(descriptor.file, 'pool'):
      extensions = descriptor.file.pool.FindAllExtensions(descriptor)
      for ext in extensions:
        _AttachFieldHelpers(cls, ext)

    descriptor._concrete_class = cls  # pylint: disable=protected-access
    _AddEnumValues(descriptor, cls)
    _AddInitMethod(descriptor, cls)
    _AddPropertiesForFields(descriptor, cls)
    _AddPropertiesForExtensions(descriptor, cls)
    _AddStaticMethods(cls)
    _AddMessageMethods(descriptor, cls)
    _AddPrivateHelperMethods(descriptor, cls)

    superclass = super(GeneratedProtocolMessageType, cls)
    superclass.__init__(name, bases, dictionary)


# Stateless helpers for GeneratedProtocolMessageType below.
# Outside clients should not access these directly.
#
# I opted not to make any of these methods on the metaclass, to make it more
# clear that I'm not really using any state there and to keep clients from
# thinking that they have direct access to these construction helpers.


def _PropertyName(proto_field_name):
  """Returns the name of the public property attribute which
  clients can use to get and (in some cases) set the value
  of a protocol message field.

  Args:
    proto_field_name: The protocol message field name, exactly
      as it appears (or would appear) in a .proto file.
  """
  # TODO: Escape Python keywords (e.g., yield), and test this support.
  # nnorwitz makes my day by writing:
  # """
  # FYI.  See the keyword module in the stdlib. This could be as simple as:
  #
  # if keyword.iskeyword(proto_field_name):
  #   return proto_field_name + "_"
  # return proto_field_name
  # """
  # Kenton says:  The above is a BAD IDEA.  People rely on being able to use
  #   getattr() and setattr() to reflectively manipulate field values.  If we
  #   rename the properties, then every such user has to also make sure to apply
  #   the same transformation.  Note that currently if you name a field "yield",
  #   you can still access it just fine using getattr/setattr -- it's not even
  #   that cumbersome to do so.
  # TODO:  Remove this method entirely if/when everyone agrees with my
  #   position.
  return proto_field_name


def _AddSlots(message_descriptor, dictionary):
  """Adds a __slots__ entry to dictionary, containing the names of all valid
  attributes for this message type.

  Args:
    message_descriptor: A Descriptor instance describing this message type.
    dictionary: Class dictionary to which we'll add a '__slots__' entry.
  """
  dictionary['__slots__'] = ['_cached_byte_size',
                             '_cached_byte_size_dirty',
                             '_fields',
                             '_unknown_fields',
                             '_unknown_field_set',
                             '_is_present_in_parent',
                             '_listener',
                             '_listener_for_children',
                             '__weakref__',
                             '_oneofs']


def _IsMessageSetExtension(field):
  return (field.is_extension and
          field.containing_type.has_options and
          field.containing_type.GetOptions().message_set_wire_format and
          field.type == _FieldDescriptor.TYPE_MESSAGE and
          field.label == _FieldDescriptor.LABEL_OPTIONAL)


def _IsMapField(field):
  return (field.type == _FieldDescriptor.TYPE_MESSAGE and
          field.message_type._is_map_entry)


def _IsMessageMapField(field):
  value_type = field.message_type.fields_by_name['value']
  return value_type.cpp_type == _FieldDescriptor.CPPTYPE_MESSAGE

def _AttachFieldHelpers(cls, field_descriptor):
  is_repeated = field_descriptor.label == _FieldDescriptor.LABEL_REPEATED
  field_descriptor._default_constructor = _DefaultValueConstructorForField(
      field_descriptor
  )

  def AddFieldByTag(wiretype, is_packed):
    tag_bytes = encoder.TagBytes(field_descriptor.number, wiretype)
    cls._fields_by_tag[tag_bytes] = (field_descriptor, is_packed)

  AddFieldByTag(
      type_checkers.FIELD_TYPE_TO_WIRE_TYPE[field_descriptor.type], False
  )

  if is_repeated and wire_format.IsTypePackable(field_descriptor.type):
    # To support wire compatibility of adding packed = true, add a decoder for
    # packed values regardless of the field's options.
    AddFieldByTag(wire_format.WIRETYPE_LENGTH_DELIMITED, True)


def _MaybeAddEncoder(cls, field_descriptor):
  if hasattr(field_descriptor, '_encoder'):
    return
  is_repeated = (field_descriptor.label == _FieldDescriptor.LABEL_REPEATED)
  is_map_entry = _IsMapField(field_descriptor)
  is_packed = field_descriptor.is_packed

  if is_map_entry:
    field_encoder = encoder.MapEncoder(field_descriptor)
    sizer = encoder.MapSizer(field_descriptor,
                             _IsMessageMapField(field_descriptor))
  elif _IsMessageSetExtension(field_descriptor):
    field_encoder = encoder.MessageSetItemEncoder(field_descriptor.number)
    sizer = encoder.MessageSetItemSizer(field_descriptor.number)
  else:
    field_encoder = type_checkers.TYPE_TO_ENCODER[field_descriptor.type](
        field_descriptor.number, is_repeated, is_packed)
    sizer = type_checkers.TYPE_TO_SIZER[field_descriptor.type](
        field_descriptor.number, is_repeated, is_packed)

  field_descriptor._sizer = sizer
  field_descriptor._encoder = field_encoder


def _MaybeAddDecoder(cls, field_descriptor):
  if hasattr(field_descriptor, '_decoders'):
    return

  is_repeated = field_descriptor.label == _FieldDescriptor.LABEL_REPEATED
  is_map_entry = _IsMapField(field_descriptor)
  helper_decoders = {}

  def AddDecoder(is_packed):
    decode_type = field_descriptor.type
    if (decode_type == _FieldDescriptor.TYPE_ENUM and
        not field_descriptor.enum_type.is_closed):
      decode_type = _FieldDescriptor.TYPE_INT32

    oneof_descriptor = None
    if field_descriptor.containing_oneof is not None:
      oneof_descriptor = field_descriptor

    if is_map_entry:
      is_message_map = _IsMessageMapField(field_descriptor)

      field_decoder = decoder.MapDecoder(
          field_descriptor, _GetInitializeDefaultForMap(field_descriptor),
          is_message_map)
    elif decode_type == _FieldDescriptor.TYPE_STRING:
      field_decoder = decoder.StringDecoder(
          field_descriptor.number, is_repeated, is_packed,
          field_descriptor, field_descriptor._default_constructor,
          not field_descriptor.has_presence)
    elif field_descriptor.cpp_type == _FieldDescriptor.CPPTYPE_MESSAGE:
      field_decoder = type_checkers.TYPE_TO_DECODER[decode_type](
          field_descriptor.number, is_repeated, is_packed,
          field_descriptor, field_descriptor._default_constructor)
    else:
      field_decoder = type_checkers.TYPE_TO_DECODER[decode_type](
          field_descriptor.number, is_repeated, is_packed,
          # pylint: disable=protected-access
          field_descriptor, field_descriptor._default_constructor,
          not field_descriptor.has_presence)

    helper_decoders[is_packed] = field_decoder

  AddDecoder(False)

  if is_repeated and wire_format.IsTypePackable(field_descriptor.type):
    # To support wire compatibility of adding packed = true, add a decoder for
    # packed values regardless of the field's options.
    AddDecoder(True)

  field_descriptor._decoders = helper_decoders


def _AddClassAttributesForNestedExtensions(descriptor, dictionary):
  extensions = descriptor.extensions_by_name
  for extension_name, extension_field in extensions.items():
    assert extension_name not in dictionary
    dictionary[extension_name] = extension_field


def _AddEnumValues(descriptor, cls):
  """Sets class-level attributes for all enum fields defined in this message.

  Also exporting a class-level object that can name enum values.

  Args:
    descriptor: Descriptor object for this message type.
    cls: Class we're constructing for this message type.
  """
  for enum_type in descriptor.enum_types:
    setattr(cls, enum_type.name, enum_type_wrapper.EnumTypeWrapper(enum_type))
    for enum_value in enum_type.values:
      setattr(cls, enum_value.name, enum_value.number)


def _GetInitializeDefaultForMap(field):
  if field.label != _FieldDescriptor.LABEL_REPEATED:
    raise ValueError('map_entry set on non-repeated field %s' % (
        field.name))
  fields_by_name = field.message_type.fields_by_name
  key_checker = type_checkers.GetTypeChecker(fields_by_name['key'])

  value_field = fields_by_name['value']
  if _IsMessageMapField(field):
    def MakeMessageMapDefault(message):
      return containers.MessageMap(
          message._listener_for_children, value_field.message_type, key_checker,
          field.message_type)
    return MakeMessageMapDefault
  else:
    value_checker = type_checkers.GetTypeChecker(value_field)
    def MakePrimitiveMapDefault(message):
      return containers.ScalarMap(
          message._listener_for_children, key_checker, value_checker,
          field.message_type)
    return MakePrimitiveMapDefault

def _DefaultValueConstructorForField(field):
  """Returns a function which returns a default value for a field.

  Args:
    field: FieldDescriptor object for this field.

  The returned function has one argument:
    message: Message instance containing this field, or a weakref proxy
      of same.

  That function in turn returns a default value for this field.  The default
    value may refer back to |message| via a weak reference.
  """

  if _IsMapField(field):
    return _GetInitializeDefaultForMap(field)

  if field.label == _FieldDescriptor.LABEL_REPEATED:
    if field.has_default_value and field.default_value != []:
      raise ValueError('Repeated field default value not empty list: %s' % (
          field.default_value))
    if field.cpp_type == _FieldDescriptor.CPPTYPE_MESSAGE:
      # We can't look at _concrete_class yet since it might not have
      # been set.  (Depends on order in which we initialize the classes).
      message_type = field.message_type
      def MakeRepeatedMessageDefault(message):
        return containers.RepeatedCompositeFieldContainer(
            message._listener_for_children, field.message_type)
      return MakeRepeatedMessageDefault
    else:
      type_checker = type_checkers.GetTypeChecker(field)
      def MakeRepeatedScalarDefault(message):
        return containers.RepeatedScalarFieldContainer(
            message._listener_for_children, type_checker)
      return MakeRepeatedScalarDefault

  if field.cpp_type == _FieldDescriptor.CPPTYPE_MESSAGE:
    message_type = field.message_type
    def MakeSubMessageDefault(message):
      # _concrete_class may not yet be initialized.
      if not hasattr(message_type, '_concrete_class'):
        from google.protobuf import message_factory
        message_factory.GetMessageClass(message_type)
      result = message_type._concrete_class()
      result._SetListener(
          _OneofListener(message, field)
          if field.containing_oneof is not None
          else message._listener_for_children)
      return result
    return MakeSubMessageDefault

  def MakeScalarDefault(message):
    # TODO: This may be broken since there may not be
    # default_value.  Combine with has_default_value somehow.
    return field.default_value
  return MakeScalarDefault


def _ReraiseTypeErrorWithFieldName(message_name, field_name):
  """Re-raise the currently-handled TypeError with the field name added."""
  exc = sys.exc_info()[1]
  if len(exc.args) == 1 and type(exc) is TypeError:
    # simple TypeError; add field name to exception message
    exc = TypeError('%s for field %s.%s' % (str(exc), message_name, field_name))

  # re-raise possibly-amended exception with original traceback:
  raise exc.with_traceback(sys.exc_info()[2])


def _AddInitMethod(message_descriptor, cls):
  """Adds an __init__ method to cls."""

  def _GetIntegerEnumValue(enum_type, value):
    """Convert a string or integer enum value to an integer.

    If the value is a string, it is converted to the enum value in
    enum_type with the same name.  If the value is not a string, it's
    returned as-is.  (No conversion or bounds-checking is done.)
    """
    if isinstance(value, str):
      try:
        return enum_type.values_by_name[value].number
      except KeyError:
        raise ValueError('Enum type %s: unknown label "%s"' % (
            enum_type.full_name, value))
    return value

  def init(self, **kwargs):
    self._cached_byte_size = 0
    self._cached_byte_size_dirty = len(kwargs) > 0
    self._fields = {}
    # Contains a mapping from oneof field descriptors to the descriptor
    # of the currently set field in that oneof field.
    self._oneofs = {}

    # _unknown_fields is () when empty for efficiency, and will be turned into
    # a list if fields are added.
    self._unknown_fields = ()
    # _unknown_field_set is None when empty for efficiency, and will be
    # turned into UnknownFieldSet struct if fields are added.
    self._unknown_field_set = None      # pylint: disable=protected-access
    self._is_present_in_parent = False
    self._listener = message_listener_mod.NullMessageListener()
    self._listener_for_children = _Listener(self)
    for field_name, field_value in kwargs.items():
      field = _GetFieldByName(message_descriptor, field_name)
      if field is None:
        raise TypeError('%s() got an unexpected keyword argument "%s"' %
                        (message_descriptor.name, field_name))
      if field_value is None:
        # field=None is the same as no field at all.
        continue
      if field.label == _FieldDescriptor.LABEL_REPEATED:
        copy = field._default_constructor(self)
        if field.cpp_type == _FieldDescriptor.CPPTYPE_MESSAGE:  # Composite
          if _IsMapField(field):
            if _IsMessageMapField(field):
              for key in field_value:
                copy[key].MergeFrom(field_value[key])
            else:
              copy.update(field_value)
          else:
            for val in field_value:
              if isinstance(val, dict):
                copy.add(**val)
              else:
                copy.add().MergeFrom(val)
        else:  # Scalar
          if field.cpp_type == _FieldDescriptor.CPPTYPE_ENUM:
            field_value = [_GetIntegerEnumValue(field.enum_type, val)
                           for val in field_value]
          copy.extend(field_value)
        self._fields[field] = copy
      elif field.cpp_type == _FieldDescriptor.CPPTYPE_MESSAGE:
        copy = field._default_constructor(self)
        new_val = field_value
        if isinstance(field_value, dict):
          new_val = field.message_type._concrete_class(**field_value)
        try:
          copy.MergeFrom(new_val)
        except TypeError:
          _ReraiseTypeErrorWithFieldName(message_descriptor.name, field_name)
        self._fields[field] = copy
      else:
        if field.cpp_type == _FieldDescriptor.CPPTYPE_ENUM:
          field_value = _GetIntegerEnumValue(field.enum_type, field_value)
        try:
          setattr(self, field_name, field_value)
        except TypeError:
          _ReraiseTypeErrorWithFieldName(message_descriptor.name, field_name)

  init.__module__ = None
  init.__doc__ = None
  cls.__init__ = init


def _GetFieldByName(message_descriptor, field_name):
  """Returns a field descriptor by field name.

  Args:
    message_descriptor: A Descriptor describing all fields in message.
    field_name: The name of the field to retrieve.
  Returns:
    The field descriptor associated with the field name.
  """
  try:
    return message_descriptor.fields_by_name[field_name]
  except KeyError:
    raise ValueError('Protocol message %s has no "%s" field.' %
                     (message_descriptor.name, field_name))


def _AddPropertiesForFields(descriptor, cls):
  """Adds properties for all fields in this protocol message type."""
  for field in descriptor.fields:
    _AddPropertiesForField(field, cls)

  if descriptor.is_extendable:
    # _ExtensionDict is just an adaptor with no state so we allocate a new one
    # every time it is accessed.
    cls.Extensions = property(lambda self: _ExtensionDict(self))


def _AddPropertiesForField(field, cls):
  """Adds a public property for a protocol message field.
  Clients can use this property to get and (in the case
  of non-repeated scalar fields) directly set the value
  of a protocol message field.

  Args:
    field: A FieldDescriptor for this field.
    cls: The class we're constructing.
  """
  # Catch it if we add other types that we should
  # handle specially here.
  assert _FieldDescriptor.MAX_CPPTYPE == 10

  constant_name = field.name.upper() + '_FIELD_NUMBER'
  setattr(cls, constant_name, field.number)

  if field.label == _FieldDescriptor.LABEL_REPEATED:
    _AddPropertiesForRepeatedField(field, cls)
  elif field.cpp_type == _FieldDescriptor.CPPTYPE_MESSAGE:
    _AddPropertiesForNonRepeatedCompositeField(field, cls)
  else:
    _AddPropertiesForNonRepeatedScalarField(field, cls)


class _FieldProperty(property):
  __slots__ = ('DESCRIPTOR',)

  def __init__(self, descriptor, getter, setter, doc):
    property.__init__(self, getter, setter, doc=doc)
    self.DESCRIPTOR = descriptor


def _AddPropertiesForRepeatedField(field, cls):
  """Adds a public property for a "repeated" protocol message field.  Clients
  can use this property to get the value of the field, which will be either a
  RepeatedScalarFieldContainer or RepeatedCompositeFieldContainer (see
  below).

  Note that when clients add values to these containers, we perform
  type-checking in the case of repeated scalar fields, and we also set any
  necessary "has" bits as a side-effect.

  Args:
    field: A FieldDescriptor for this field.
    cls: The class we're constructing.
  """
  proto_field_name = field.name
  property_name = _PropertyName(proto_field_name)

  def getter(self):
    field_value = self._fields.get(field)
    if field_value is None:
      # Construct a new object to represent this field.
      field_value = field._default_constructor(self)

      # Atomically check if another thread has preempted us and, if not, swap
      # in the new object we just created.  If someone has preempted us, we
      # take that object and discard ours.
      # WARNING:  We are relying on setdefault() being atomic.  This is true
      #   in CPython but we haven't investigated others.  This warning appears
      #   in several other locations in this file.
      field_value = self._fields.setdefault(field, field_value)
    return field_value
  getter.__module__ = None
  getter.__doc__ = 'Getter for %s.' % proto_field_name

  # We define a setter just so we can throw an exception with a more
  # helpful error message.
  def setter(self, new_value):
    raise AttributeError('Assignment not allowed to repeated field '
                         '"%s" in protocol message object.' % proto_field_name)

  doc = 'Magic attribute generated for "%s" proto field.' % proto_field_name
  setattr(cls, property_name, _FieldProperty(field, getter, setter, doc=doc))


def _AddPropertiesForNonRepeatedScalarField(field, cls):
  """Adds a public property for a nonrepeated, scalar protocol message field.
  Clients can use this property to get and directly set the value of the field.
  Note that when the client sets the value of a field by using this property,
  all necessary "has" bits are set as a side-effect, and we also perform
  type-checking.

  Args:
    field: A FieldDescriptor for this field.
    cls: The class we're constructing.
  """
  proto_field_name = field.name
  property_name = _PropertyName(proto_field_name)
  type_checker = type_checkers.GetTypeChecker(field)
  default_value = field.default_value

  def getter(self):
    # TODO: This may be broken since there may not be
    # default_value.  Combine with has_default_value somehow.
    return self._fields.get(field, default_value)
  getter.__module__ = None
  getter.__doc__ = 'Getter for %s.' % proto_field_name

  def field_setter(self, new_value):
    # pylint: disable=protected-access
    # Testing the value for truthiness captures all of the proto3 defaults
    # (0, 0.0, enum 0, and False).
    try:
      new_value = type_checker.CheckValue(new_value)
    except TypeError as e:
      raise TypeError(
          'Cannot set %s to %.1024r: %s' % (field.full_name, new_value, e))
    if not field.has_presence and not new_value:
      self._fields.pop(field, None)
    else:
      self._fields[field] = new_value
    # Check _cached_byte_size_dirty inline to improve performance, since scalar
    # setters are called frequently.
    if not self._cached_byte_size_dirty:
      self._Modified()

  if field.containing_oneof:
    def setter(self, new_value):
      field_setter(self, new_value)
      self._UpdateOneofState(field)
  else:
    setter = field_setter

  setter.__module__ = None
  setter.__doc__ = 'Setter for %s.' % proto_field_name

  # Add a property to encapsulate the getter/setter.
  doc = 'Magic attribute generated for "%s" proto field.' % proto_field_name
  setattr(cls, property_name, _FieldProperty(field, getter, setter, doc=doc))


def _AddPropertiesForNonRepeatedCompositeField(field, cls):
  """Adds a public property for a nonrepeated, composite protocol message field.
  A composite field is a "group" or "message" field.

  Clients can use this property to get the value of the field, but cannot
  assign to the property directly.

  Args:
    field: A FieldDescriptor for this field.
    cls: The class we're constructing.
  """
  # TODO: Remove duplication with similar method
  # for non-repeated scalars.
  proto_field_name = field.name
  property_name = _PropertyName(proto_field_name)

  def getter(self):
    field_value = self._fields.get(field)
    if field_value is None:
      # Construct a new object to represent this field.
      field_value = field._default_constructor(self)

      # Atomically check if another thread has preempted us and, if not, swap
      # in the new object we just created.  If someone has preempted us, we
      # take that object and discard ours.
      # WARNING:  We are relying on setdefault() being atomic.  This is true
      #   in CPython but we haven't investigated others.  This warning appears
      #   in several other locations in this file.
      field_value = self._fields.setdefault(field, field_value)
    return field_value
  getter.__module__ = None
  getter.__doc__ = 'Getter for %s.' % proto_field_name

  # We define a setter just so we can throw an exception with a more
  # helpful error message.
  def setter(self, new_value):
    raise AttributeError('Assignment not allowed to composite field '
                         '"%s" in protocol message object.' % proto_field_name)

  # Add a property to encapsulate the getter.
  doc = 'Magic attribute generated for "%s" proto field.' % proto_field_name
  setattr(cls, property_name, _FieldProperty(field, getter, setter, doc=doc))


def _AddPropertiesForExtensions(descriptor, cls):
  """Adds properties for all fields in this protocol message type."""
  extensions = descriptor.extensions_by_name
  for extension_name, extension_field in extensions.items():
    constant_name = extension_name.upper() + '_FIELD_NUMBER'
    setattr(cls, constant_name, extension_field.number)

  # TODO: Migrate all users of these attributes to functions like
  #   pool.FindExtensionByNumber(descriptor).
  if descriptor.file is not None:
    # TODO: Use cls.MESSAGE_FACTORY.pool when available.
    pool = descriptor.file.pool

def _AddStaticMethods(cls):
  # TODO: This probably needs to be thread-safe(?)
  def RegisterExtension(field_descriptor):
    field_descriptor.containing_type = cls.DESCRIPTOR
    # TODO: Use cls.MESSAGE_FACTORY.pool when available.
    # pylint: disable=protected-access
    cls.DESCRIPTOR.file.pool._AddExtensionDescriptor(field_descriptor)
    _AttachFieldHelpers(cls, field_descriptor)
  cls.RegisterExtension = staticmethod(RegisterExtension)

  def FromString(s):
    message = cls()
    message.MergeFromString(s)
    return message
  cls.FromString = staticmethod(FromString)


def _IsPresent(item):
  """Given a (FieldDescriptor, value) tuple from _fields, return true if the
  value should be included in the list returned by ListFields()."""

  if item[0].label == _FieldDescriptor.LABEL_REPEATED:
    return bool(item[1])
  elif item[0].cpp_type == _FieldDescriptor.CPPTYPE_MESSAGE:
    return item[1]._is_present_in_parent
  else:
    return True


def _AddListFieldsMethod(message_descriptor, cls):
  """Helper for _AddMessageMethods()."""

  def ListFields(self):
    all_fields = [item for item in self._fields.items() if _IsPresent(item)]
    all_fields.sort(key = lambda item: item[0].number)
    return all_fields

  cls.ListFields = ListFields


def _AddHasFieldMethod(message_descriptor, cls):
  """Helper for _AddMessageMethods()."""

  hassable_fields = {}
  for field in message_descriptor.fields:
    if field.label == _FieldDescriptor.LABEL_REPEATED:
      continue
    # For proto3, only submessages and fields inside a oneof have presence.
    if not field.has_presence:
      continue
    hassable_fields[field.name] = field

  # Has methods are supported for oneof descriptors.
  for oneof in message_descriptor.oneofs:
    hassable_fields[oneof.name] = oneof

  def HasField(self, field_name):
    try:
      field = hassable_fields[field_name]
    except KeyError as exc:
      raise ValueError('Protocol message %s has no non-repeated field "%s" '
                       'nor has presence is not available for this field.' % (
                           message_descriptor.full_name, field_name)) from exc

    if isinstance(field, descriptor_mod.OneofDescriptor):
      try:
        return HasField(self, self._oneofs[field].name)
      except KeyError:
        return False
    else:
      if field.cpp_type == _FieldDescriptor.CPPTYPE_MESSAGE:
        value = self._fields.get(field)
        return value is not None and value._is_present_in_parent
      else:
        return field in self._fields

  cls.HasField = HasField


def _AddClearFieldMethod(message_descriptor, cls):
  """Helper for _AddMessageMethods()."""
  def ClearField(self, field_name):
    try:
      field = message_descriptor.fields_by_name[field_name]
    except KeyError:
      try:
        field = message_descriptor.oneofs_by_name[field_name]
        if field in self._oneofs:
          field = self._oneofs[field]
        else:
          return
      except KeyError:
        raise ValueError('Protocol message %s has no "%s" field.' %
                         (message_descriptor.name, field_name))

    if field in self._fields:
      # To match the C++ implementation, we need to invalidate iterators
      # for map fields when ClearField() happens.
      if hasattr(self._fields[field], 'InvalidateIterators'):
        self._fields[field].InvalidateIterators()

      # Note:  If the field is a sub-message, its listener will still point
      #   at us.  That's fine, because the worst than can happen is that it
      #   will call _Modified() and invalidate our byte size.  Big deal.
      del self._fields[field]

      if self._oneofs.get(field.containing_oneof, None) is field:
        del self._oneofs[field.containing_oneof]

    # Always call _Modified() -- even if nothing was changed, this is
    # a mutating method, and thus calling it should cause the field to become
    # present in the parent message.
    self._Modified()

  cls.ClearField = ClearField


def _AddClearExtensionMethod(cls):
  """Helper for _AddMessageMethods()."""
  def ClearExtension(self, field_descriptor):
    extension_dict._VerifyExtensionHandle(self, field_descriptor)

    # Similar to ClearField(), above.
    if field_descriptor in self._fields:
      del self._fields[field_descriptor]
    self._Modified()
  cls.ClearExtension = ClearExtension


def _AddHasExtensionMethod(cls):
  """Helper for _AddMessageMethods()."""
  def HasExtension(self, field_descriptor):
    extension_dict._VerifyExtensionHandle(self, field_descriptor)
    if field_descriptor.label == _FieldDescriptor.LABEL_REPEATED:
      raise KeyError('"%s" is repeated.' % field_descriptor.full_name)

    if field_descriptor.cpp_type == _FieldDescriptor.CPPTYPE_MESSAGE:
      value = self._fields.get(field_descriptor)
      return value is not None and value._is_present_in_parent
    else:
      return field_descriptor in self._fields
  cls.HasExtension = HasExtension

def _InternalUnpackAny(msg):
  """Unpacks Any message and returns the unpacked message.

  This internal method is different from public Any Unpack method which takes
  the target message as argument. _InternalUnpackAny method does not have
  target message type and need to find the message type in descriptor pool.

  Args:
    msg: An Any message to be unpacked.

  Returns:
    The unpacked message.
  """
  # TODO: Don't use the factory of generated messages.
  # To make Any work with custom factories, use the message factory of the
  # parent message.
  # pylint: disable=g-import-not-at-top
  from google.protobuf import symbol_database
  factory = symbol_database.Default()

  type_url = msg.type_url

  if not type_url:
    return None

  # TODO: For now we just strip the hostname.  Better logic will be
  # required.
  type_name = type_url.split('/')[-1]
  descriptor = factory.pool.FindMessageTypeByName(type_name)

  if descriptor is None:
    return None

  message_class = factory.GetPrototype(descriptor)
  message = message_class()

  message.ParseFromString(msg.value)
  return message


def _AddEqualsMethod(message_descriptor, cls):
  """Helper for _AddMessageMethods()."""
  def __eq__(self, other):
    if (not isinstance(other, message_mod.Message) or
        other.DESCRIPTOR != self.DESCRIPTOR):
      return NotImplemented

    if self is other:
      return True

    if self.DESCRIPTOR.full_name == _AnyFullTypeName:
      any_a = _InternalUnpackAny(self)
      any_b = _InternalUnpackAny(other)
      if any_a and any_b:
        return any_a == any_b

    if not self.ListFields() == other.ListFields():
      return False

    # TODO: Fix UnknownFieldSet to consider MessageSet extensions,
    # then use it for the comparison.
    unknown_fields = list(self._unknown_fields)
    unknown_fields.sort()
    other_unknown_fields = list(other._unknown_fields)
    other_unknown_fields.sort()
    return unknown_fields == other_unknown_fields

  cls.__eq__ = __eq__


def _AddStrMethod(message_descriptor, cls):
  """Helper for _AddMessageMethods()."""
  def __str__(self):
    return text_format.MessageToString(self)
  cls.__str__ = __str__


def _AddReprMethod(message_descriptor, cls):
  """Helper for _AddMessageMethods()."""
  def __repr__(self):
    return text_format.MessageToString(self)
  cls.__repr__ = __repr__


def _AddUnicodeMethod(unused_message_descriptor, cls):
  """Helper for _AddMessageMethods()."""

  def __unicode__(self):
    return text_format.MessageToString(self, as_utf8=True).decode('utf-8')
  cls.__unicode__ = __unicode__


def _BytesForNonRepeatedElement(value, field_number, field_type):
  """Returns the number of bytes needed to serialize a non-repeated element.
  The returned byte count includes space for tag information and any
  other additional space associated with serializing value.

  Args:
    value: Value we're serializing.
    field_number: Field number of this value.  (Since the field number
      is stored as part of a varint-encoded tag, this has an impact
      on the total bytes required to serialize the value).
    field_type: The type of the field.  One of the TYPE_* constants
      within FieldDescriptor.
  """
  try:
    fn = type_checkers.TYPE_TO_BYTE_SIZE_FN[field_type]
    return fn(field_number, value)
  except KeyError:
    raise message_mod.EncodeError('Unrecognized field type: %d' % field_type)


def _AddByteSizeMethod(message_descriptor, cls):
  """Helper for _AddMessageMethods()."""

  def ByteSize(self):
    if not self._cached_byte_size_dirty:
      return self._cached_byte_size

    size = 0
    descriptor = self.DESCRIPTOR
    if descriptor._is_map_entry:
      # Fields of map entry should always be serialized.
      key_field = descriptor.fields_by_name['key']
      _MaybeAddEncoder(cls, key_field)
      size = key_field._sizer(self.key)
      value_field = descriptor.fields_by_name['value']
      _MaybeAddEncoder(cls, value_field)
      size += value_field._sizer(self.value)
    else:
      for field_descriptor, field_value in self.ListFields():
        _MaybeAddEncoder(cls, field_descriptor)
        size += field_descriptor._sizer(field_value)
      for tag_bytes, value_bytes in self._unknown_fields:
        size += len(tag_bytes) + len(value_bytes)

    self._cached_byte_size = size
    self._cached_byte_size_dirty = False
    self._listener_for_children.dirty = False
    return size

  cls.ByteSize = ByteSize


def _AddSerializeToStringMethod(message_descriptor, cls):
  """Helper for _AddMessageMethods()."""

  def SerializeToString(self, **kwargs):
    # Check if the message has all of its required fields set.
    if not self.IsInitialized():
      raise message_mod.EncodeError(
          'Message %s is missing required fields: %s' % (
          self.DESCRIPTOR.full_name, ','.join(self.FindInitializationErrors())))
    return self.SerializePartialToString(**kwargs)
  cls.SerializeToString = SerializeToString


def _AddSerializePartialToStringMethod(message_descriptor, cls):
  """Helper for _AddMessageMethods()."""

  def SerializePartialToString(self, **kwargs):
    out = BytesIO()
    self._InternalSerialize(out.write, **kwargs)
    return out.getvalue()
  cls.SerializePartialToString = SerializePartialToString

  def InternalSerialize(self, write_bytes, deterministic=None):
    if deterministic is None:
      deterministic = (
          api_implementation.IsPythonDefaultSerializationDeterministic())
    else:
      deterministic = bool(deterministic)

    descriptor = self.DESCRIPTOR
    if descriptor._is_map_entry:
      # Fields of map entry should always be serialized.
      key_field = descriptor.fields_by_name['key']
      _MaybeAddEncoder(cls, key_field)
      key_field._encoder(write_bytes, self.key, deterministic)
      value_field = descriptor.fields_by_name['value']
      _MaybeAddEncoder(cls, value_field)
      value_field._encoder(write_bytes, self.value, deterministic)
    else:
      for field_descriptor, field_value in self.ListFields():
        _MaybeAddEncoder(cls, field_descriptor)
        field_descriptor._encoder(write_bytes, field_value, deterministic)
      for tag_bytes, value_bytes in self._unknown_fields:
        write_bytes(tag_bytes)
        write_bytes(value_bytes)
  cls._InternalSerialize = InternalSerialize


def _AddMergeFromStringMethod(message_descriptor, cls):
  """Helper for _AddMessageMethods()."""
  def MergeFromString(self, serialized):
    serialized = memoryview(serialized)
    length = len(serialized)
    try:
      if self._InternalParse(serialized, 0, length) != length:
        # The only reason _InternalParse would return early is if it
        # encountered an end-group tag.
        raise message_mod.DecodeError('Unexpected end-group tag.')
    except (IndexError, TypeError):
      # Now ord(buf[p:p+1]) == ord('') gets TypeError.
      raise message_mod.DecodeError('Truncated message.')
    except struct.error as e:
      raise message_mod.DecodeError(e)
    return length   # Return this for legacy reasons.
  cls.MergeFromString = MergeFromString

  local_ReadTag = decoder.ReadTag
  local_SkipField = decoder.SkipField
  fields_by_tag = cls._fields_by_tag
  message_set_decoders_by_tag = cls._message_set_decoders_by_tag

  def InternalParse(self, buffer, pos, end, current_depth=0):
    """Create a message from serialized bytes.

    Args:
      self: Message, instance of the proto message object.
      buffer: memoryview of the serialized data.
      pos: int, position to start in the serialized data.
      end: int, end position of the serialized data.

    Returns:
      Message object.
    """
    # Guard against internal misuse, since this function is called internally
    # quite extensively, and its easy to accidentally pass bytes.
    assert isinstance(buffer, memoryview)
    self._Modified()
    field_dict = self._fields
    # pylint: disable=protected-access
    unknown_field_set = self._unknown_field_set
    while pos != end:
      (tag_bytes, new_pos) = local_ReadTag(buffer, pos)
      field_decoder, field_des = message_set_decoders_by_tag.get(
          tag_bytes, (None, None)
      )
      if field_decoder:
        pos = field_decoder(buffer, new_pos, end, self, field_dict)
        continue
      field_des, is_packed = fields_by_tag.get(tag_bytes, (None, None))
      if field_des is None:
        if not self._unknown_fields:   # pylint: disable=protected-access
          self._unknown_fields = []    # pylint: disable=protected-access
        if unknown_field_set is None:
          # pylint: disable=protected-access
          self._unknown_field_set = containers.UnknownFieldSet()
          # pylint: disable=protected-access
          unknown_field_set = self._unknown_field_set
        # pylint: disable=protected-access
        (tag, _) = decoder._DecodeVarint(tag_bytes, 0)
        field_number, wire_type = wire_format.UnpackTag(tag)
        if field_number == 0:
          raise message_mod.DecodeError('Field number 0 is illegal.')
        # TODO: remove old_pos.
        old_pos = new_pos
        (data, new_pos) = decoder._DecodeUnknownField(
            buffer, new_pos, wire_type, current_depth)  # pylint: disable=protected-access
        if new_pos == -1:
          return pos
        # pylint: disable=protected-access
        unknown_field_set._add(field_number, wire_type, data)
        # TODO: remove _unknown_fields.
        new_pos = local_SkipField(buffer, old_pos, end, tag_bytes)
        if new_pos == -1:
          return pos
        self._unknown_fields.append(
            (tag_bytes, buffer[old_pos:new_pos].tobytes()))
        pos = new_pos
      else:
        _MaybeAddDecoder(cls, field_des)
        field_decoder = field_des._decoders[is_packed]
        pos = field_decoder(buffer, new_pos, end, self, field_dict, current_depth)
        if field_des.containing_oneof:
          self._UpdateOneofState(field_des)
    return pos
  cls._InternalParse = InternalParse


def _AddIsInitializedMethod(message_descriptor, cls):
  """Adds the IsInitialized and FindInitializationError methods to the
  protocol message class."""

  required_fields = [field for field in message_descriptor.fields
                           if field.label == _FieldDescriptor.LABEL_REQUIRED]

  def IsInitialized(self, errors=None):
    """Checks if all required fields of a message are set.

    Args:
      errors:  A list which, if provided, will be populated with the field
               paths of all missing required fields.

    Returns:
      True iff the specified message has all required fields set.
    """

    # Performance is critical so we avoid HasField() and ListFields().

    for field in required_fields:
      if (field not in self._fields or
          (field.cpp_type == _FieldDescriptor.CPPTYPE_MESSAGE and
           not self._fields[field]._is_present_in_parent)):
        if errors is not None:
          errors.extend(self.FindInitializationErrors())
        return False

    for field, value in list(self._fields.items()):  # dict can change size!
      if field.cpp_type == _FieldDescriptor.CPPTYPE_MESSAGE:
        if field.label == _FieldDescriptor.LABEL_REPEATED:
          if (field.message_type._is_map_entry):
            continue
          for element in value:
            if not element.IsInitialized():
              if errors is not None:
                errors.extend(self.FindInitializationErrors())
              return False
        elif value._is_present_in_parent and not value.IsInitialized():
          if errors is not None:
            errors.extend(self.FindInitializationErrors())
          return False

    return True

  cls.IsInitialized = IsInitialized

  def FindInitializationErrors(self):
    """Finds required fields which are not initialized.

    Returns:
      A list of strings.  Each string is a path to an uninitialized field from
      the top-level message, e.g. "foo.bar[5].baz".
    """

    errors = []  # simplify things

    for field in required_fields:
      if not self.HasField(field.name):
        errors.append(field.name)

    for field, value in self.ListFields():
      if field.cpp_type == _FieldDescriptor.CPPTYPE_MESSAGE:
        if field.is_extension:
          name = '(%s)' % field.full_name
        else:
          name = field.name

        if _IsMapField(field):
          if _IsMessageMapField(field):
            for key in value:
              element = value[key]
              prefix = '%s[%s].' % (name, key)
              sub_errors = element.FindInitializationErrors()
              errors += [prefix + error for error in sub_errors]
          else:
            # ScalarMaps can't have any initialization errors.
            pass
        elif field.label == _FieldDescriptor.LABEL_REPEATED:
          for i in range(len(value)):
            element = value[i]
            prefix = '%s[%d].' % (name, i)
            sub_errors = element.FindInitializationErrors()
            errors += [prefix + error for error in sub_errors]
        else:
          prefix = name + '.'
          sub_errors = value.FindInitializationErrors()
          errors += [prefix + error for error in sub_errors]

    return errors

  cls.FindInitializationErrors = FindInitializationErrors


def _FullyQualifiedClassName(klass):
  module = klass.__module__
  name = getattr(klass, '__qualname__', klass.__name__)
  if module in (None, 'builtins', '__builtin__'):
    return name
  return module + '.' + name


def _AddMergeFromMethod(cls):
  LABEL_REPEATED = _FieldDescriptor.LABEL_REPEATED
  CPPTYPE_MESSAGE = _FieldDescriptor.CPPTYPE_MESSAGE

  def MergeFrom(self, msg):
    if not isinstance(msg, cls):
      raise TypeError(
          'Parameter to MergeFrom() must be instance of same class: '
          'expected %s got %s.' % (_FullyQualifiedClassName(cls),
                                   _FullyQualifiedClassName(msg.__class__)))

    assert msg is not self
    self._Modified()

    fields = self._fields

    for field, value in msg._fields.items():
      if field.label == LABEL_REPEATED:
        field_value = fields.get(field)
        if field_value is None:
          # Construct a new object to represent this field.
          field_value = field._default_constructor(self)
          fields[field] = field_value
        field_value.MergeFrom(value)
      elif field.cpp_type == CPPTYPE_MESSAGE:
        if value._is_present_in_parent:
          field_value = fields.get(field)
          if field_value is None:
            # Construct a new object to represent this field.
            field_value = field._default_constructor(self)
            fields[field] = field_value
          field_value.MergeFrom(value)
      else:
        self._fields[field] = value
        if field.containing_oneof:
          self._UpdateOneofState(field)

    if msg._unknown_fields:
      if not self._unknown_fields:
        self._unknown_fields = []
      self._unknown_fields.extend(msg._unknown_fields)
      # pylint: disable=protected-access
      if self._unknown_field_set is None:
        self._unknown_field_set = containers.UnknownFieldSet()
      self._unknown_field_set._extend(msg._unknown_field_set)

  cls.MergeFrom = MergeFrom


def _AddWhichOneofMethod(message_descriptor, cls):
  def WhichOneof(self, oneof_name):
    """Returns the name of the currently set field inside a oneof, or None."""
    try:
      field = message_descriptor.oneofs_by_name[oneof_name]
    except KeyError:
      raise ValueError(
          'Protocol message has no oneof "%s" field.' % oneof_name)

    nested_field = self._oneofs.get(field, None)
    if nested_field is not None and self.HasField(nested_field.name):
      return nested_field.name
    else:
      return None

  cls.WhichOneof = WhichOneof


def _Clear(self):
  # Clear fields.
  self._fields = {}
  self._unknown_fields = ()
  # pylint: disable=protected-access
  if self._unknown_field_set is not None:
    self._unknown_field_set._clear()
    self._unknown_field_set = None

  self._oneofs = {}
  self._Modified()


def _UnknownFields(self):
  warnings.warn(
      'message.UnknownFields() is deprecated. Please use the add one '
      'feature unknown_fields.UnknownFieldSet(message) in '
      'unknown_fields.py instead.'
  )
  if self._unknown_field_set is None:  # pylint: disable=protected-access
    # pylint: disable=protected-access
    self._unknown_field_set = containers.UnknownFieldSet()
  return self._unknown_field_set    # pylint: disable=protected-access


def _DiscardUnknownFields(self):
  self._unknown_fields = []
  self._unknown_field_set = None      # pylint: disable=protected-access
  for field, value in self.ListFields():
    if field.cpp_type == _FieldDescriptor.CPPTYPE_MESSAGE:
      if _IsMapField(field):
        if _IsMessageMapField(field):
          for key in value:
            value[key].DiscardUnknownFields()
      elif field.label == _FieldDescriptor.LABEL_REPEATED:
        for sub_message in value:
          sub_message.DiscardUnknownFields()
      else:
        value.DiscardUnknownFields()


def _SetListener(self, listener):
  if listener is None:
    self._listener = message_listener_mod.NullMessageListener()
  else:
    self._listener = listener


def _AddMessageMethods(message_descriptor, cls):
  """Adds implementations of all Message methods to cls."""
  _AddListFieldsMethod(message_descriptor, cls)
  _AddHasFieldMethod(message_descriptor, cls)
  _AddClearFieldMethod(message_descriptor, cls)
  if message_descriptor.is_extendable:
    _AddClearExtensionMethod(cls)
    _AddHasExtensionMethod(cls)
  _AddEqualsMethod(message_descriptor, cls)
  _AddStrMethod(message_descriptor, cls)
  _AddReprMethod(message_descriptor, cls)
  _AddUnicodeMethod(message_descriptor, cls)
  _AddByteSizeMethod(message_descriptor, cls)
  _AddSerializeToStringMethod(message_descriptor, cls)
  _AddSerializePartialToStringMethod(message_descriptor, cls)
  _AddMergeFromStringMethod(message_descriptor, cls)
  _AddIsInitializedMethod(message_descriptor, cls)
  _AddMergeFromMethod(cls)
  _AddWhichOneofMethod(message_descriptor, cls)
  # Adds methods which do not depend on cls.
  cls.Clear = _Clear
  cls.UnknownFields = _UnknownFields
  cls.DiscardUnknownFields = _DiscardUnknownFields
  cls._SetListener = _SetListener


def _AddPrivateHelperMethods(message_descriptor, cls):
  """Adds implementation of private helper methods to cls."""

  def Modified(self):
    """Sets the _cached_byte_size_dirty bit to true,
    and propagates this to our listener iff this was a state change.
    """

    # Note:  Some callers check _cached_byte_size_dirty before calling
    #   _Modified() as an extra optimization.  So, if this method is ever
    #   changed such that it does stuff even when _cached_byte_size_dirty is
    #   already true, the callers need to be updated.
    if not self._cached_byte_size_dirty:
      self._cached_byte_size_dirty = True
      self._listener_for_children.dirty = True
      self._is_present_in_parent = True
      self._listener.Modified()

  def _UpdateOneofState(self, field):
    """Sets field as the active field in its containing oneof.

    Will also delete currently active field in the oneof, if it is different
    from the argument. Does not mark the message as modified.
    """
    other_field = self._oneofs.setdefault(field.containing_oneof, field)
    if other_field is not field:
      del self._fields[other_field]
      self._oneofs[field.containing_oneof] = field

  cls._Modified = Modified
  cls.SetInParent = Modified
  cls._UpdateOneofState = _UpdateOneofState


class _Listener(object):

  """MessageListener implementation that a parent message registers with its
  child message.

  In order to support semantics like:

    foo.bar.baz.moo = 23
    assert foo.HasField('bar')

  ...child objects must have back references to their parents.
  This helper class is at the heart of this support.
  """

  def __init__(self, parent_message):
    """Args:
      parent_message: The message whose _Modified() method we should call when
        we receive Modified() messages.
    """
    # This listener establishes a back reference from a child (contained) object
    # to its parent (containing) object.  We make this a weak reference to avoid
    # creating cyclic garbage when the client finishes with the 'parent' object
    # in the tree.
    if isinstance(parent_message, weakref.ProxyType):
      self._parent_message_weakref = parent_message
    else:
      self._parent_message_weakref = weakref.proxy(parent_message)

    # As an optimization, we also indicate directly on the listener whether
    # or not the parent message is dirty.  This way we can avoid traversing
    # up the tree in the common case.
    self.dirty = False

  def Modified(self):
    if self.dirty:
      return
    try:
      # Propagate the signal to our parents iff this is the first field set.
      self._parent_message_weakref._Modified()
    except ReferenceError:
      # We can get here if a client has kept a reference to a child object,
      # and is now setting a field on it, but the child's parent has been
      # garbage-collected.  This is not an error.
      pass


class _OneofListener(_Listener):
  """Special listener implementation for setting composite oneof fields."""

  def __init__(self, parent_message, field):
    """Args:
      parent_message: The message whose _Modified() method we should call when
        we receive Modified() messages.
      field: The descriptor of the field being set in the parent message.
    """
    super(_OneofListener, self).__init__(parent_message)
    self._field = field

  def Modified(self):
    """Also updates the state of the containing oneof in the parent message."""
    try:
      self._parent_message_weakref._UpdateOneofState(self._field)
      super(_OneofListener, self).Modified()
    except ReferenceError:
      pass

# === NexusCore/openenv\Lib\site-packages\joblib\externals\cloudpickle\cloudpickle.py ===
"""Pickler class to extend the standard pickle.Pickler functionality

The main objective is to make it natural to perform distributed computing on
clusters (such as PySpark, Dask, Ray...) with interactively defined code
(functions, classes, ...) written in notebooks or console.

In particular this pickler adds the following features:
- serialize interactively-defined or locally-defined functions, classes,
  enums, typevars, lambdas and nested functions to compiled byte code;
- deal with some other non-serializable objects in an ad-hoc manner where
  applicable.

This pickler is therefore meant to be used for the communication between short
lived Python processes running the same version of Python and libraries. In
particular, it is not meant to be used for long term storage of Python objects.

It does not include an unpickler, as standard Python unpickling suffices.

This module was extracted from the `cloud` package, developed by `PiCloud, Inc.
<https://web.archive.org/web/20140626004012/http://www.picloud.com/>`_.

Copyright (c) 2012-now, CloudPickle developers and contributors.
Copyright (c) 2012, Regents of the University of California.
Copyright (c) 2009 `PiCloud, Inc. <https://web.archive.org/web/20140626004012/http://www.picloud.com/>`_.
All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions
are met:
    * Redistributions of source code must retain the above copyright
      notice, this list of conditions and the following disclaimer.
    * Redistributions in binary form must reproduce the above copyright
      notice, this list of conditions and the following disclaimer in the
      documentation and/or other materials provided with the distribution.
    * Neither the name of the University of California, Berkeley nor the
      names of its contributors may be used to endorse or promote
      products derived from this software without specific prior written
      permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
"AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED
TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR
PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF
LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING
NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
"""

import _collections_abc
from collections import ChainMap, OrderedDict
import abc
import builtins
import copyreg
import dataclasses
import dis
from enum import Enum
import io
import itertools
import logging
import opcode
import pickle
from pickle import _getattribute as _pickle_getattribute
import platform
import struct
import sys
import threading
import types
import typing
import uuid
import warnings
import weakref

# The following import is required to be imported in the cloudpickle
# namespace to be able to load pickle files generated with older versions of
# cloudpickle. See: tests/test_backward_compat.py
from types import CellType  # noqa: F401


# cloudpickle is meant for inter process communication: we expect all
# communicating processes to run the same Python version hence we favor
# communication speed over compatibility:
DEFAULT_PROTOCOL = pickle.HIGHEST_PROTOCOL

# Names of modules whose resources should be treated as dynamic.
_PICKLE_BY_VALUE_MODULES = set()

# Track the provenance of reconstructed dynamic classes to make it possible to
# reconstruct instances from the matching singleton class definition when
# appropriate and preserve the usual "isinstance" semantics of Python objects.
_DYNAMIC_CLASS_TRACKER_BY_CLASS = weakref.WeakKeyDictionary()
_DYNAMIC_CLASS_TRACKER_BY_ID = weakref.WeakValueDictionary()
_DYNAMIC_CLASS_TRACKER_LOCK = threading.Lock()

PYPY = platform.python_implementation() == "PyPy"

builtin_code_type = None
if PYPY:
    # builtin-code objects only exist in pypy
    builtin_code_type = type(float.__new__.__code__)

_extract_code_globals_cache = weakref.WeakKeyDictionary()


def _get_or_create_tracker_id(class_def):
    with _DYNAMIC_CLASS_TRACKER_LOCK:
        class_tracker_id = _DYNAMIC_CLASS_TRACKER_BY_CLASS.get(class_def)
        if class_tracker_id is None:
            class_tracker_id = uuid.uuid4().hex
            _DYNAMIC_CLASS_TRACKER_BY_CLASS[class_def] = class_tracker_id
            _DYNAMIC_CLASS_TRACKER_BY_ID[class_tracker_id] = class_def
    return class_tracker_id


def _lookup_class_or_track(class_tracker_id, class_def):
    if class_tracker_id is not None:
        with _DYNAMIC_CLASS_TRACKER_LOCK:
            class_def = _DYNAMIC_CLASS_TRACKER_BY_ID.setdefault(
                class_tracker_id, class_def
            )
            _DYNAMIC_CLASS_TRACKER_BY_CLASS[class_def] = class_tracker_id
    return class_def


def register_pickle_by_value(module):
    """Register a module to make its functions and classes picklable by value.

    By default, functions and classes that are attributes of an importable
    module are to be pickled by reference, that is relying on re-importing
    the attribute from the module at load time.

    If `register_pickle_by_value(module)` is called, all its functions and
    classes are subsequently to be pickled by value, meaning that they can
    be loaded in Python processes where the module is not importable.

    This is especially useful when developing a module in a distributed
    execution environment: restarting the client Python process with the new
    source code is enough: there is no need to re-install the new version
    of the module on all the worker nodes nor to restart the workers.

    Note: this feature is considered experimental. See the cloudpickle
    README.md file for more details and limitations.
    """
    if not isinstance(module, types.ModuleType):
        raise ValueError(f"Input should be a module object, got {str(module)} instead")
    # In the future, cloudpickle may need a way to access any module registered
    # for pickling by value in order to introspect relative imports inside
    # functions pickled by value. (see
    # https://github.com/cloudpipe/cloudpickle/pull/417#issuecomment-873684633).
    # This access can be ensured by checking that module is present in
    # sys.modules at registering time and assuming that it will still be in
    # there when accessed during pickling. Another alternative would be to
    # store a weakref to the module. Even though cloudpickle does not implement
    # this introspection yet, in order to avoid a possible breaking change
    # later, we still enforce the presence of module inside sys.modules.
    if module.__name__ not in sys.modules:
        raise ValueError(
            f"{module} was not imported correctly, have you used an "
            "`import` statement to access it?"
        )
    _PICKLE_BY_VALUE_MODULES.add(module.__name__)


def unregister_pickle_by_value(module):
    """Unregister that the input module should be pickled by value."""
    if not isinstance(module, types.ModuleType):
        raise ValueError(f"Input should be a module object, got {str(module)} instead")
    if module.__name__ not in _PICKLE_BY_VALUE_MODULES:
        raise ValueError(f"{module} is not registered for pickle by value")
    else:
        _PICKLE_BY_VALUE_MODULES.remove(module.__name__)


def list_registry_pickle_by_value():
    return _PICKLE_BY_VALUE_MODULES.copy()


def _is_registered_pickle_by_value(module):
    module_name = module.__name__
    if module_name in _PICKLE_BY_VALUE_MODULES:
        return True
    while True:
        parent_name = module_name.rsplit(".", 1)[0]
        if parent_name == module_name:
            break
        if parent_name in _PICKLE_BY_VALUE_MODULES:
            return True
        module_name = parent_name
    return False


if sys.version_info >= (3, 14):
    def _getattribute(obj, name):
        return _pickle_getattribute(obj, name.split('.'))
else:
    def _getattribute(obj, name):
        return _pickle_getattribute(obj, name)[0]


def _whichmodule(obj, name):
    """Find the module an object belongs to.

    This function differs from ``pickle.whichmodule`` in two ways:
    - it does not mangle the cases where obj's module is __main__ and obj was
      not found in any module.
    - Errors arising during module introspection are ignored, as those errors
      are considered unwanted side effects.
    """
    module_name = getattr(obj, "__module__", None)

    if module_name is not None:
        return module_name
    # Protect the iteration by using a copy of sys.modules against dynamic
    # modules that trigger imports of other modules upon calls to getattr or
    # other threads importing at the same time.
    for module_name, module in sys.modules.copy().items():
        # Some modules such as coverage can inject non-module objects inside
        # sys.modules
        if (
            module_name == "__main__"
            or module_name == "__mp_main__"
            or module is None
            or not isinstance(module, types.ModuleType)
        ):
            continue
        try:
            if _getattribute(module, name) is obj:
                return module_name
        except Exception:
            pass
    return None


def _should_pickle_by_reference(obj, name=None):
    """Test whether an function or a class should be pickled by reference

    Pickling by reference means by that the object (typically a function or a
    class) is an attribute of a module that is assumed to be importable in the
    target Python environment. Loading will therefore rely on importing the
    module and then calling `getattr` on it to access the function or class.

    Pickling by reference is the only option to pickle functions and classes
    in the standard library. In cloudpickle the alternative option is to
    pickle by value (for instance for interactively or locally defined
    functions and classes or for attributes of modules that have been
    explicitly registered to be pickled by value.
    """
    if isinstance(obj, types.FunctionType) or issubclass(type(obj), type):
        module_and_name = _lookup_module_and_qualname(obj, name=name)
        if module_and_name is None:
            return False
        module, name = module_and_name
        return not _is_registered_pickle_by_value(module)

    elif isinstance(obj, types.ModuleType):
        # We assume that sys.modules is primarily used as a cache mechanism for
        # the Python import machinery. Checking if a module has been added in
        # is sys.modules therefore a cheap and simple heuristic to tell us
        # whether we can assume that a given module could be imported by name
        # in another Python process.
        if _is_registered_pickle_by_value(obj):
            return False
        return obj.__name__ in sys.modules
    else:
        raise TypeError(
            "cannot check importability of {} instances".format(type(obj).__name__)
        )


def _lookup_module_and_qualname(obj, name=None):
    if name is None:
        name = getattr(obj, "__qualname__", None)
    if name is None:  # pragma: no cover
        # This used to be needed for Python 2.7 support but is probably not
        # needed anymore. However we keep the __name__ introspection in case
        # users of cloudpickle rely on this old behavior for unknown reasons.
        name = getattr(obj, "__name__", None)

    module_name = _whichmodule(obj, name)

    if module_name is None:
        # In this case, obj.__module__ is None AND obj was not found in any
        # imported module. obj is thus treated as dynamic.
        return None

    if module_name == "__main__":
        return None

    # Note: if module_name is in sys.modules, the corresponding module is
    # assumed importable at unpickling time. See #357
    module = sys.modules.get(module_name, None)
    if module is None:
        # The main reason why obj's module would not be imported is that this
        # module has been dynamically created, using for example
        # types.ModuleType. The other possibility is that module was removed
        # from sys.modules after obj was created/imported. But this case is not
        # supported, as the standard pickle does not support it either.
        return None

    try:
        obj2 = _getattribute(module, name)
    except AttributeError:
        # obj was not found inside the module it points to
        return None
    if obj2 is not obj:
        return None
    return module, name


def _extract_code_globals(co):
    """Find all globals names read or written to by codeblock co."""
    out_names = _extract_code_globals_cache.get(co)
    if out_names is None:
        # We use a dict with None values instead of a set to get a
        # deterministic order and avoid introducing non-deterministic pickle
        # bytes as a results.
        out_names = {name: None for name in _walk_global_ops(co)}

        # Declaring a function inside another one using the "def ..." syntax
        # generates a constant code object corresponding to the one of the
        # nested function's As the nested function may itself need global
        # variables, we need to introspect its code, extract its globals, (look
        # for code object in it's co_consts attribute..) and add the result to
        # code_globals
        if co.co_consts:
            for const in co.co_consts:
                if isinstance(const, types.CodeType):
                    out_names.update(_extract_code_globals(const))

        _extract_code_globals_cache[co] = out_names

    return out_names


def _find_imported_submodules(code, top_level_dependencies):
    """Find currently imported submodules used by a function.

    Submodules used by a function need to be detected and referenced for the
    function to work correctly at depickling time. Because submodules can be
    referenced as attribute of their parent package (``package.submodule``), we
    need a special introspection technique that does not rely on GLOBAL-related
    opcodes to find references of them in a code object.

    Example:
    ```
    import concurrent.futures
    import cloudpickle
    def func():
        x = concurrent.futures.ThreadPoolExecutor
    if __name__ == '__main__':
        cloudpickle.dumps(func)
    ```
    The globals extracted by cloudpickle in the function's state include the
    concurrent package, but not its submodule (here, concurrent.futures), which
    is the module used by func. Find_imported_submodules will detect the usage
    of concurrent.futures. Saving this module alongside with func will ensure
    that calling func once depickled does not fail due to concurrent.futures
    not being imported
    """

    subimports = []
    # check if any known dependency is an imported package
    for x in top_level_dependencies:
        if (
            isinstance(x, types.ModuleType)
            and hasattr(x, "__package__")
            and x.__package__
        ):
            # check if the package has any currently loaded sub-imports
            prefix = x.__name__ + "."
            # A concurrent thread could mutate sys.modules,
            # make sure we iterate over a copy to avoid exceptions
            for name in list(sys.modules):
                # Older versions of pytest will add a "None" module to
                # sys.modules.
                if name is not None and name.startswith(prefix):
                    # check whether the function can address the sub-module
                    tokens = set(name[len(prefix) :].split("."))
                    if not tokens - set(code.co_names):
                        subimports.append(sys.modules[name])
    return subimports


# relevant opcodes
STORE_GLOBAL = opcode.opmap["STORE_GLOBAL"]
DELETE_GLOBAL = opcode.opmap["DELETE_GLOBAL"]
LOAD_GLOBAL = opcode.opmap["LOAD_GLOBAL"]
GLOBAL_OPS = (STORE_GLOBAL, DELETE_GLOBAL, LOAD_GLOBAL)
HAVE_ARGUMENT = dis.HAVE_ARGUMENT
EXTENDED_ARG = dis.EXTENDED_ARG


_BUILTIN_TYPE_NAMES = {}
for k, v in types.__dict__.items():
    if type(v) is type:
        _BUILTIN_TYPE_NAMES[v] = k


def _builtin_type(name):
    if name == "ClassType":  # pragma: no cover
        # Backward compat to load pickle files generated with cloudpickle
        # < 1.3 even if loading pickle files from older versions is not
        # officially supported.
        return type
    return getattr(types, name)


def _walk_global_ops(code):
    """Yield referenced name for global-referencing instructions in code."""
    for instr in dis.get_instructions(code):
        op = instr.opcode
        if op in GLOBAL_OPS:
            yield instr.argval


def _extract_class_dict(cls):
    """Retrieve a copy of the dict of a class without the inherited method."""
    # Hack to circumvent non-predictable memoization caused by string interning.
    # See the inline comment in _class_setstate for details.
    clsdict = {"".join(k): cls.__dict__[k] for k in sorted(cls.__dict__)}

    if len(cls.__bases__) == 1:
        inherited_dict = cls.__bases__[0].__dict__
    else:
        inherited_dict = {}
        for base in reversed(cls.__bases__):
            inherited_dict.update(base.__dict__)
    to_remove = []
    for name, value in clsdict.items():
        try:
            base_value = inherited_dict[name]
            if value is base_value:
                to_remove.append(name)
        except KeyError:
            pass
    for name in to_remove:
        clsdict.pop(name)
    return clsdict


def is_tornado_coroutine(func):
    """Return whether `func` is a Tornado coroutine function.

    Running coroutines are not supported.
    """
    warnings.warn(
        "is_tornado_coroutine is deprecated in cloudpickle 3.0 and will be "
        "removed in cloudpickle 4.0. Use tornado.gen.is_coroutine_function "
        "directly instead.",
        category=DeprecationWarning,
    )
    if "tornado.gen" not in sys.modules:
        return False
    gen = sys.modules["tornado.gen"]
    if not hasattr(gen, "is_coroutine_function"):
        # Tornado version is too old
        return False
    return gen.is_coroutine_function(func)


def subimport(name):
    # We cannot do simply: `return __import__(name)`: Indeed, if ``name`` is
    # the name of a submodule, __import__ will return the top-level root module
    # of this submodule. For instance, __import__('os.path') returns the `os`
    # module.
    __import__(name)
    return sys.modules[name]


def dynamic_subimport(name, vars):
    mod = types.ModuleType(name)
    mod.__dict__.update(vars)
    mod.__dict__["__builtins__"] = builtins.__dict__
    return mod


def _get_cell_contents(cell):
    try:
        return cell.cell_contents
    except ValueError:
        # Handle empty cells explicitly with a sentinel value.
        return _empty_cell_value


def instance(cls):
    """Create a new instance of a class.

    Parameters
    ----------
    cls : type
        The class to create an instance of.

    Returns
    -------
    instance : cls
        A new instance of ``cls``.
    """
    return cls()


@instance
class _empty_cell_value:
    """Sentinel for empty closures."""

    @classmethod
    def __reduce__(cls):
        return cls.__name__


def _make_function(code, globals, name, argdefs, closure):
    # Setting __builtins__ in globals is needed for nogil CPython.
    globals["__builtins__"] = __builtins__
    return types.FunctionType(code, globals, name, argdefs, closure)


def _make_empty_cell():
    if False:
        # trick the compiler into creating an empty cell in our lambda
        cell = None
        raise AssertionError("this route should not be executed")

    return (lambda: cell).__closure__[0]


def _make_cell(value=_empty_cell_value):
    cell = _make_empty_cell()
    if value is not _empty_cell_value:
        cell.cell_contents = value
    return cell


def _make_skeleton_class(
    type_constructor, name, bases, type_kwargs, class_tracker_id, extra
):
    """Build dynamic class with an empty __dict__ to be filled once memoized

    If class_tracker_id is not None, try to lookup an existing class definition
    matching that id. If none is found, track a newly reconstructed class
    definition under that id so that other instances stemming from the same
    class id will also reuse this class definition.

    The "extra" variable is meant to be a dict (or None) that can be used for
    forward compatibility shall the need arise.
    """
    # We need to intern the keys of the type_kwargs dict to avoid having
    # different pickles for the same dynamic class depending on whether it was
    # dynamically created or reconstructed from a pickled stream.
    type_kwargs = {sys.intern(k): v for k, v in type_kwargs.items()}

    skeleton_class = types.new_class(
        name, bases, {"metaclass": type_constructor}, lambda ns: ns.update(type_kwargs)
    )

    return _lookup_class_or_track(class_tracker_id, skeleton_class)


def _make_skeleton_enum(
    bases, name, qualname, members, module, class_tracker_id, extra
):
    """Build dynamic enum with an empty __dict__ to be filled once memoized

    The creation of the enum class is inspired by the code of
    EnumMeta._create_.

    If class_tracker_id is not None, try to lookup an existing enum definition
    matching that id. If none is found, track a newly reconstructed enum
    definition under that id so that other instances stemming from the same
    class id will also reuse this enum definition.

    The "extra" variable is meant to be a dict (or None) that can be used for
    forward compatibility shall the need arise.
    """
    # enums always inherit from their base Enum class at the last position in
    # the list of base classes:
    enum_base = bases[-1]
    metacls = enum_base.__class__
    classdict = metacls.__prepare__(name, bases)

    for member_name, member_value in members.items():
        classdict[member_name] = member_value
    enum_class = metacls.__new__(metacls, name, bases, classdict)
    enum_class.__module__ = module
    enum_class.__qualname__ = qualname

    return _lookup_class_or_track(class_tracker_id, enum_class)


def _make_typevar(name, bound, constraints, covariant, contravariant, class_tracker_id):
    tv = typing.TypeVar(
        name,
        *constraints,
        bound=bound,
        covariant=covariant,
        contravariant=contravariant,
    )
    return _lookup_class_or_track(class_tracker_id, tv)


def _decompose_typevar(obj):
    return (
        obj.__name__,
        obj.__bound__,
        obj.__constraints__,
        obj.__covariant__,
        obj.__contravariant__,
        _get_or_create_tracker_id(obj),
    )


def _typevar_reduce(obj):
    # TypeVar instances require the module information hence why we
    # are not using the _should_pickle_by_reference directly
    module_and_name = _lookup_module_and_qualname(obj, name=obj.__name__)

    if module_and_name is None:
        return (_make_typevar, _decompose_typevar(obj))
    elif _is_registered_pickle_by_value(module_and_name[0]):
        return (_make_typevar, _decompose_typevar(obj))

    return (getattr, module_and_name)


def _get_bases(typ):
    if "__orig_bases__" in getattr(typ, "__dict__", {}):
        # For generic types (see PEP 560)
        # Note that simply checking `hasattr(typ, '__orig_bases__')` is not
        # correct.  Subclasses of a fully-parameterized generic class does not
        # have `__orig_bases__` defined, but `hasattr(typ, '__orig_bases__')`
        # will return True because it's defined in the base class.
        bases_attr = "__orig_bases__"
    else:
        # For regular class objects
        bases_attr = "__bases__"
    return getattr(typ, bases_attr)


def _make_dict_keys(obj, is_ordered=False):
    if is_ordered:
        return OrderedDict.fromkeys(obj).keys()
    else:
        return dict.fromkeys(obj).keys()


def _make_dict_values(obj, is_ordered=False):
    if is_ordered:
        return OrderedDict((i, _) for i, _ in enumerate(obj)).values()
    else:
        return {i: _ for i, _ in enumerate(obj)}.values()


def _make_dict_items(obj, is_ordered=False):
    if is_ordered:
        return OrderedDict(obj).items()
    else:
        return obj.items()


# COLLECTION OF OBJECTS __getnewargs__-LIKE METHODS
# -------------------------------------------------


def _class_getnewargs(obj):
    type_kwargs = {}
    if "__module__" in obj.__dict__:
        type_kwargs["__module__"] = obj.__module__

    __dict__ = obj.__dict__.get("__dict__", None)
    if isinstance(__dict__, property):
        type_kwargs["__dict__"] = __dict__

    return (
        type(obj),
        obj.__name__,
        _get_bases(obj),
        type_kwargs,
        _get_or_create_tracker_id(obj),
        None,
    )


def _enum_getnewargs(obj):
    members = {e.name: e.value for e in obj}
    return (
        obj.__bases__,
        obj.__name__,
        obj.__qualname__,
        members,
        obj.__module__,
        _get_or_create_tracker_id(obj),
        None,
    )


# COLLECTION OF OBJECTS RECONSTRUCTORS
# ------------------------------------
def _file_reconstructor(retval):
    return retval


# COLLECTION OF OBJECTS STATE GETTERS
# -----------------------------------


def _function_getstate(func):
    # - Put func's dynamic attributes (stored in func.__dict__) in state. These
    #   attributes will be restored at unpickling time using
    #   f.__dict__.update(state)
    # - Put func's members into slotstate. Such attributes will be restored at
    #   unpickling time by iterating over slotstate and calling setattr(func,
    #   slotname, slotvalue)
    slotstate = {
        # Hack to circumvent non-predictable memoization caused by string interning.
        # See the inline comment in _class_setstate for details.
        "__name__": "".join(func.__name__),
        "__qualname__": "".join(func.__qualname__),
        "__annotations__": func.__annotations__,
        "__kwdefaults__": func.__kwdefaults__,
        "__defaults__": func.__defaults__,
        "__module__": func.__module__,
        "__doc__": func.__doc__,
        "__closure__": func.__closure__,
    }

    f_globals_ref = _extract_code_globals(func.__code__)
    f_globals = {k: func.__globals__[k] for k in f_globals_ref if k in func.__globals__}

    if func.__closure__ is not None:
        closure_values = list(map(_get_cell_contents, func.__closure__))
    else:
        closure_values = ()

    # Extract currently-imported submodules used by func. Storing these modules
    # in a smoke _cloudpickle_subimports attribute of the object's state will
    # trigger the side effect of importing these modules at unpickling time
    # (which is necessary for func to work correctly once depickled)
    slotstate["_cloudpickle_submodules"] = _find_imported_submodules(
        func.__code__, itertools.chain(f_globals.values(), closure_values)
    )
    slotstate["__globals__"] = f_globals

    # Hack to circumvent non-predictable memoization caused by string interning.
    # See the inline comment in _class_setstate for details.
    state = {"".join(k): v for k, v in func.__dict__.items()}
    return state, slotstate


def _class_getstate(obj):
    clsdict = _extract_class_dict(obj)
    clsdict.pop("__weakref__", None)

    if issubclass(type(obj), abc.ABCMeta):
        # If obj is an instance of an ABCMeta subclass, don't pickle the
        # cache/negative caches populated during isinstance/issubclass
        # checks, but pickle the list of registered subclasses of obj.
        clsdict.pop("_abc_cache", None)
        clsdict.pop("_abc_negative_cache", None)
        clsdict.pop("_abc_negative_cache_version", None)
        registry = clsdict.pop("_abc_registry", None)
        if registry is None:
            # The abc caches and registered subclasses of a
            # class are bundled into the single _abc_impl attribute
            clsdict.pop("_abc_impl", None)
            (registry, _, _, _) = abc._get_dump(obj)

            clsdict["_abc_impl"] = [subclass_weakref() for subclass_weakref in registry]
        else:
            # In the above if clause, registry is a set of weakrefs -- in
            # this case, registry is a WeakSet
            clsdict["_abc_impl"] = [type_ for type_ in registry]

    if "__slots__" in clsdict:
        # pickle string length optimization: member descriptors of obj are
        # created automatically from obj's __slots__ attribute, no need to
        # save them in obj's state
        if isinstance(obj.__slots__, str):
            clsdict.pop(obj.__slots__)
        else:
            for k in obj.__slots__:
                clsdict.pop(k, None)

    clsdict.pop("__dict__", None)  # unpicklable property object

    return (clsdict, {})


def _enum_getstate(obj):
    clsdict, slotstate = _class_getstate(obj)

    members = {e.name: e.value for e in obj}
    # Cleanup the clsdict that will be passed to _make_skeleton_enum:
    # Those attributes are already handled by the metaclass.
    for attrname in [
        "_generate_next_value_",
        "_member_names_",
        "_member_map_",
        "_member_type_",
        "_value2member_map_",
    ]:
        clsdict.pop(attrname, None)
    for member in members:
        clsdict.pop(member)
        # Special handling of Enum subclasses
    return clsdict, slotstate


# COLLECTIONS OF OBJECTS REDUCERS
# -------------------------------
# A reducer is a function taking a single argument (obj), and that returns a
# tuple with all the necessary data to re-construct obj. Apart from a few
# exceptions (list, dict, bytes, int, etc.), a reducer is necessary to
# correctly pickle an object.
# While many built-in objects (Exceptions objects, instances of the "object"
# class, etc), are shipped with their own built-in reducer (invoked using
# obj.__reduce__), some do not. The following methods were created to "fill
# these holes".


def _code_reduce(obj):
    """code object reducer."""
    # If you are not sure about the order of arguments, take a look at help
    # of the specific type from types, for example:
    # >>> from types import CodeType
    # >>> help(CodeType)

    # Hack to circumvent non-predictable memoization caused by string interning.
    # See the inline comment in _class_setstate for details.
    co_name = "".join(obj.co_name)

    # Create shallow copies of these tuple to make cloudpickle payload deterministic.
    # When creating a code object during load, copies of these four tuples are
    # created, while in the main process, these tuples can be shared.
    # By always creating copies, we make sure the resulting payload is deterministic.
    co_names = tuple(name for name in obj.co_names)
    co_varnames = tuple(name for name in obj.co_varnames)
    co_freevars = tuple(name for name in obj.co_freevars)
    co_cellvars = tuple(name for name in obj.co_cellvars)
    if hasattr(obj, "co_exceptiontable"):
        # Python 3.11 and later: there are some new attributes
        # related to the enhanced exceptions.
        args = (
            obj.co_argcount,
            obj.co_posonlyargcount,
            obj.co_kwonlyargcount,
            obj.co_nlocals,
            obj.co_stacksize,
            obj.co_flags,
            obj.co_code,
            obj.co_consts,
            co_names,
            co_varnames,
            obj.co_filename,
            co_name,
            obj.co_qualname,
            obj.co_firstlineno,
            obj.co_linetable,
            obj.co_exceptiontable,
            co_freevars,
            co_cellvars,
        )
    elif hasattr(obj, "co_linetable"):
        # Python 3.10 and later: obj.co_lnotab is deprecated and constructor
        # expects obj.co_linetable instead.
        args = (
            obj.co_argcount,
            obj.co_posonlyargcount,
            obj.co_kwonlyargcount,
            obj.co_nlocals,
            obj.co_stacksize,
            obj.co_flags,
            obj.co_code,
            obj.co_consts,
            co_names,
            co_varnames,
            obj.co_filename,
            co_name,
            obj.co_firstlineno,
            obj.co_linetable,
            co_freevars,
            co_cellvars,
        )
    elif hasattr(obj, "co_nmeta"):  # pragma: no cover
        # "nogil" Python: modified attributes from 3.9
        args = (
            obj.co_argcount,
            obj.co_posonlyargcount,
            obj.co_kwonlyargcount,
            obj.co_nlocals,
            obj.co_framesize,
            obj.co_ndefaultargs,
            obj.co_nmeta,
            obj.co_flags,
            obj.co_code,
            obj.co_consts,
            co_varnames,
            obj.co_filename,
            co_name,
            obj.co_firstlineno,
            obj.co_lnotab,
            obj.co_exc_handlers,
            obj.co_jump_table,
            co_freevars,
            co_cellvars,
            obj.co_free2reg,
            obj.co_cell2reg,
        )
    else:
        # Backward compat for 3.8 and 3.9
        args = (
            obj.co_argcount,
            obj.co_posonlyargcount,
            obj.co_kwonlyargcount,
            obj.co_nlocals,
            obj.co_stacksize,
            obj.co_flags,
            obj.co_code,
            obj.co_consts,
            co_names,
            co_varnames,
            obj.co_filename,
            co_name,
            obj.co_firstlineno,
            obj.co_lnotab,
            co_freevars,
            co_cellvars,
        )
    return types.CodeType, args


def _cell_reduce(obj):
    """Cell (containing values of a function's free variables) reducer."""
    try:
        obj.cell_contents
    except ValueError:  # cell is empty
        return _make_empty_cell, ()
    else:
        return _make_cell, (obj.cell_contents,)


def _classmethod_reduce(obj):
    orig_func = obj.__func__
    return type(obj), (orig_func,)


def _file_reduce(obj):
    """Save a file."""
    import io

    if not hasattr(obj, "name") or not hasattr(obj, "mode"):
        raise pickle.PicklingError(
            "Cannot pickle files that do not map to an actual file"
        )
    if obj is sys.stdout:
        return getattr, (sys, "stdout")
    if obj is sys.stderr:
        return getattr, (sys, "stderr")
    if obj is sys.stdin:
        raise pickle.PicklingError("Cannot pickle standard input")
    if obj.closed:
        raise pickle.PicklingError("Cannot pickle closed files")
    if hasattr(obj, "isatty") and obj.isatty():
        raise pickle.PicklingError("Cannot pickle files that map to tty objects")
    if "r" not in obj.mode and "+" not in obj.mode:
        raise pickle.PicklingError(
            "Cannot pickle files that are not opened for reading: %s" % obj.mode
        )

    name = obj.name

    retval = io.StringIO()

    try:
        # Read the whole file
        curloc = obj.tell()
        obj.seek(0)
        contents = obj.read()
        obj.seek(curloc)
    except OSError as e:
        raise pickle.PicklingError(
            "Cannot pickle file %s as it cannot be read" % name
        ) from e
    retval.write(contents)
    retval.seek(curloc)

    retval.name = name
    return _file_reconstructor, (retval,)


def _getset_descriptor_reduce(obj):
    return getattr, (obj.__objclass__, obj.__name__)


def _mappingproxy_reduce(obj):
    return types.MappingProxyType, (dict(obj),)


def _memoryview_reduce(obj):
    return bytes, (obj.tobytes(),)


def _module_reduce(obj):
    if _should_pickle_by_reference(obj):
        return subimport, (obj.__name__,)
    else:
        # Some external libraries can populate the "__builtins__" entry of a
        # module's `__dict__` with unpicklable objects (see #316). For that
        # reason, we do not attempt to pickle the "__builtins__" entry, and
        # restore a default value for it at unpickling time.
        state = obj.__dict__.copy()
        state.pop("__builtins__", None)
        return dynamic_subimport, (obj.__name__, state)


def _method_reduce(obj):
    return (types.MethodType, (obj.__func__, obj.__self__))


def _logger_reduce(obj):
    return logging.getLogger, (obj.name,)


def _root_logger_reduce(obj):
    return logging.getLogger, ()


def _property_reduce(obj):
    return property, (obj.fget, obj.fset, obj.fdel, obj.__doc__)


def _weakset_reduce(obj):
    return weakref.WeakSet, (list(obj),)


def _dynamic_class_reduce(obj):
    """Save a class that can't be referenced as a module attribute.

    This method is used to serialize classes that are defined inside
    functions, or that otherwise can't be serialized as attribute lookups
    from importable modules.
    """
    if Enum is not None and issubclass(obj, Enum):
        return (
            _make_skeleton_enum,
            _enum_getnewargs(obj),
            _enum_getstate(obj),
            None,
            None,
            _class_setstate,
        )
    else:
        return (
            _make_skeleton_class,
            _class_getnewargs(obj),
            _class_getstate(obj),
            None,
            None,
            _class_setstate,
        )


def _class_reduce(obj):
    """Select the reducer depending on the dynamic nature of the class obj."""
    if obj is type(None):  # noqa
        return type, (None,)
    elif obj is type(Ellipsis):
        return type, (Ellipsis,)
    elif obj is type(NotImplemented):
        return type, (NotImplemented,)
    elif obj in _BUILTIN_TYPE_NAMES:
        return _builtin_type, (_BUILTIN_TYPE_NAMES[obj],)
    elif not _should_pickle_by_reference(obj):
        return _dynamic_class_reduce(obj)
    return NotImplemented


def _dict_keys_reduce(obj):
    # Safer not to ship the full dict as sending the rest might
    # be unintended and could potentially cause leaking of
    # sensitive information
    return _make_dict_keys, (list(obj),)


def _dict_values_reduce(obj):
    # Safer not to ship the full dict as sending the rest might
    # be unintended and could potentially cause leaking of
    # sensitive information
    return _make_dict_values, (list(obj),)


def _dict_items_reduce(obj):
    return _make_dict_items, (dict(obj),)


def _odict_keys_reduce(obj):
    # Safer not to ship the full dict as sending the rest might
    # be unintended and could potentially cause leaking of
    # sensitive information
    return _make_dict_keys, (list(obj), True)


def _odict_values_reduce(obj):
    # Safer not to ship the full dict as sending the rest might
    # be unintended and could potentially cause leaking of
    # sensitive information
    return _make_dict_values, (list(obj), True)


def _odict_items_reduce(obj):
    return _make_dict_items, (dict(obj), True)


def _dataclass_field_base_reduce(obj):
    return _get_dataclass_field_type_sentinel, (obj.name,)


# COLLECTIONS OF OBJECTS STATE SETTERS
# ------------------------------------
# state setters are called at unpickling time, once the object is created and
# it has to be updated to how it was at unpickling time.


def _function_setstate(obj, state):
    """Update the state of a dynamic function.

    As __closure__ and __globals__ are readonly attributes of a function, we
    cannot rely on the native setstate routine of pickle.load_build, that calls
    setattr on items of the slotstate. Instead, we have to modify them inplace.
    """
    state, slotstate = state
    obj.__dict__.update(state)

    obj_globals = slotstate.pop("__globals__")
    obj_closure = slotstate.pop("__closure__")
    # _cloudpickle_subimports is a set of submodules that must be loaded for
    # the pickled function to work correctly at unpickling time. Now that these
    # submodules are depickled (hence imported), they can be removed from the
    # object's state (the object state only served as a reference holder to
    # these submodules)
    slotstate.pop("_cloudpickle_submodules")

    obj.__globals__.update(obj_globals)
    obj.__globals__["__builtins__"] = __builtins__

    if obj_closure is not None:
        for i, cell in enumerate(obj_closure):
            try:
                value = cell.cell_contents
            except ValueError:  # cell is empty
                continue
            obj.__closure__[i].cell_contents = value

    for k, v in slotstate.items():
        setattr(obj, k, v)


def _class_setstate(obj, state):
    state, slotstate = state
    registry = None
    for attrname, attr in state.items():
        if attrname == "_abc_impl":
            registry = attr
        else:
            # Note: setting attribute names on a class automatically triggers their
            # interning in CPython:
            # https://github.com/python/cpython/blob/v3.12.0/Objects/object.c#L957
            #
            # This means that to get deterministic pickling for a dynamic class that
            # was initially defined in a different Python process, the pickler
            # needs to ensure that dynamic class and function attribute names are
            # systematically copied into a non-interned version to avoid
            # unpredictable pickle payloads.
            #
            # Indeed the Pickler's memoizer relies on physical object identity to break
            # cycles in the reference graph of the object being serialized.
            setattr(obj, attrname, attr)

    if sys.version_info >= (3, 13) and "__firstlineno__" in state:
        # Set the Python 3.13+ only __firstlineno__  attribute one more time, as it
        # will be automatically deleted by the `setattr(obj, attrname, attr)` call
        # above when `attrname` is "__firstlineno__". We assume that preserving this
        # information might be important for some users and that it not stale in the
        # context of cloudpickle usage, hence legitimate to propagate. Furthermore it
        # is necessary to do so to keep deterministic chained pickling as tested in
        # test_deterministic_str_interning_for_chained_dynamic_class_pickling.
        obj.__firstlineno__ = state["__firstlineno__"]

    if registry is not None:
        for subclass in registry:
            obj.register(subclass)

    return obj


# COLLECTION OF DATACLASS UTILITIES
# ---------------------------------
# There are some internal sentinel values whose identity must be preserved when
# unpickling dataclass fields. Each sentinel value has a unique name that we can
# use to retrieve its identity at unpickling time.


_DATACLASSE_FIELD_TYPE_SENTINELS = {
    dataclasses._FIELD.name: dataclasses._FIELD,
    dataclasses._FIELD_CLASSVAR.name: dataclasses._FIELD_CLASSVAR,
    dataclasses._FIELD_INITVAR.name: dataclasses._FIELD_INITVAR,
}


def _get_dataclass_field_type_sentinel(name):
    return _DATACLASSE_FIELD_TYPE_SENTINELS[name]


class Pickler(pickle.Pickler):
    # set of reducers defined and used by cloudpickle (private)
    _dispatch_table = {}
    _dispatch_table[classmethod] = _classmethod_reduce
    _dispatch_table[io.TextIOWrapper] = _file_reduce
    _dispatch_table[logging.Logger] = _logger_reduce
    _dispatch_table[logging.RootLogger] = _root_logger_reduce
    _dispatch_table[memoryview] = _memoryview_reduce
    _dispatch_table[property] = _property_reduce
    _dispatch_table[staticmethod] = _classmethod_reduce
    _dispatch_table[CellType] = _cell_reduce
    _dispatch_table[types.CodeType] = _code_reduce
    _dispatch_table[types.GetSetDescriptorType] = _getset_descriptor_reduce
    _dispatch_table[types.ModuleType] = _module_reduce
    _dispatch_table[types.MethodType] = _method_reduce
    _dispatch_table[types.MappingProxyType] = _mappingproxy_reduce
    _dispatch_table[weakref.WeakSet] = _weakset_reduce
    _dispatch_table[typing.TypeVar] = _typevar_reduce
    _dispatch_table[_collections_abc.dict_keys] = _dict_keys_reduce
    _dispatch_table[_collections_abc.dict_values] = _dict_values_reduce
    _dispatch_table[_collections_abc.dict_items] = _dict_items_reduce
    _dispatch_table[type(OrderedDict().keys())] = _odict_keys_reduce
    _dispatch_table[type(OrderedDict().values())] = _odict_values_reduce
    _dispatch_table[type(OrderedDict().items())] = _odict_items_reduce
    _dispatch_table[abc.abstractmethod] = _classmethod_reduce
    _dispatch_table[abc.abstractclassmethod] = _classmethod_reduce
    _dispatch_table[abc.abstractstaticmethod] = _classmethod_reduce
    _dispatch_table[abc.abstractproperty] = _property_reduce
    _dispatch_table[dataclasses._FIELD_BASE] = _dataclass_field_base_reduce

    dispatch_table = ChainMap(_dispatch_table, copyreg.dispatch_table)

    # function reducers are defined as instance methods of cloudpickle.Pickler
    # objects, as they rely on a cloudpickle.Pickler attribute (globals_ref)
    def _dynamic_function_reduce(self, func):
        """Reduce a function that is not pickleable via attribute lookup."""
        newargs = self._function_getnewargs(func)
        state = _function_getstate(func)
        return (_make_function, newargs, state, None, None, _function_setstate)

    def _function_reduce(self, obj):
        """Reducer for function objects.

        If obj is a top-level attribute of a file-backed module, this reducer
        returns NotImplemented, making the cloudpickle.Pickler fall back to
        traditional pickle.Pickler routines to save obj. Otherwise, it reduces
        obj using a custom cloudpickle reducer designed specifically to handle
        dynamic functions.
        """
        if _should_pickle_by_reference(obj):
            return NotImplemented
        else:
            return self._dynamic_function_reduce(obj)

    def _function_getnewargs(self, func):
        code = func.__code__

        # base_globals represents the future global namespace of func at
        # unpickling time. Looking it up and storing it in
        # cloudpickle.Pickler.globals_ref allow functions sharing the same
        # globals at pickling time to also share them once unpickled, at one
        # condition: since globals_ref is an attribute of a cloudpickle.Pickler
        # instance, and that a new cloudpickle.Pickler is created each time
        # cloudpickle.dump or cloudpickle.dumps is called, functions also need
        # to be saved within the same invocation of
        # cloudpickle.dump/cloudpickle.dumps (for example:
        # cloudpickle.dumps([f1, f2])). There is no such limitation when using
        # cloudpickle.Pickler.dump, as long as the multiple invocations are
        # bound to the same cloudpickle.Pickler instance.
        base_globals = self.globals_ref.setdefault(id(func.__globals__), {})

        if base_globals == {}:
            # Add module attributes used to resolve relative imports
            # instructions inside func.
            for k in ["__package__", "__name__", "__path__", "__file__"]:
                if k in func.__globals__:
                    base_globals[k] = func.__globals__[k]

        # Do not bind the free variables before the function is created to
        # avoid infinite recursion.
        if func.__closure__ is None:
            closure = None
        else:
            closure = tuple(_make_empty_cell() for _ in range(len(code.co_freevars)))

        return code, base_globals, None, None, closure

    def dump(self, obj):
        try:
            return super().dump(obj)
        except RuntimeError as e:
            if len(e.args) > 0 and "recursion" in e.args[0]:
                msg = "Could not pickle object as excessively deep recursion required."
                raise pickle.PicklingError(msg) from e
            else:
                raise

    def __init__(self, file, protocol=None, buffer_callback=None):
        if protocol is None:
            protocol = DEFAULT_PROTOCOL
        super().__init__(file, protocol=protocol, buffer_callback=buffer_callback)
        # map functions __globals__ attribute ids, to ensure that functions
        # sharing the same global namespace at pickling time also share
        # their global namespace at unpickling time.
        self.globals_ref = {}
        self.proto = int(protocol)

    if not PYPY:
        # pickle.Pickler is the C implementation of the CPython pickler and
        # therefore we rely on reduce_override method to customize the pickler
        # behavior.

        # `cloudpickle.Pickler.dispatch` is only left for backward
        # compatibility - note that when using protocol 5,
        # `cloudpickle.Pickler.dispatch` is not an extension of
        # `pickle._Pickler.dispatch` dictionary, because `cloudpickle.Pickler`
        # subclasses the C-implemented `pickle.Pickler`, which does not expose
        # a `dispatch` attribute.  Earlier versions of `cloudpickle.Pickler`
        # used `cloudpickle.Pickler.dispatch` as a class-level attribute
        # storing all reducers implemented by cloudpickle, but the attribute
        # name was not a great choice given because it would collide with a
        # similarly named attribute in the pure-Python `pickle._Pickler`
        # implementation in the standard library.
        dispatch = dispatch_table

        # Implementation of the reducer_override callback, in order to
        # efficiently serialize dynamic functions and classes by subclassing
        # the C-implemented `pickle.Pickler`.
        # TODO: decorrelate reducer_override (which is tied to CPython's
        # implementation - would it make sense to backport it to pypy? - and
        # pickle's protocol 5 which is implementation agnostic. Currently, the
        # availability of both notions coincide on CPython's pickle, but it may
        # not be the case anymore when pypy implements protocol 5.

        def reducer_override(self, obj):
            """Type-agnostic reducing callback for function and classes.

            For performance reasons, subclasses of the C `pickle.Pickler` class
            cannot register custom reducers for functions and classes in the
            dispatch_table attribute. Reducers for such types must instead
            implemented via the special `reducer_override` method.

            Note that this method will be called for any object except a few
            builtin-types (int, lists, dicts etc.), which differs from reducers
            in the Pickler's dispatch_table, each of them being invoked for
            objects of a specific type only.

            This property comes in handy for classes: although most classes are
            instances of the ``type`` metaclass, some of them can be instances
            of other custom metaclasses (such as enum.EnumMeta for example). In
            particular, the metaclass will likely not be known in advance, and
            thus cannot be special-cased using an entry in the dispatch_table.
            reducer_override, among other things, allows us to register a
            reducer that will be called for any class, independently of its
            type.

            Notes:

            * reducer_override has the priority over dispatch_table-registered
            reducers.
            * reducer_override can be used to fix other limitations of
              cloudpickle for other types that suffered from type-specific
              reducers, such as Exceptions. See
              https://github.com/cloudpipe/cloudpickle/issues/248
            """
            t = type(obj)
            try:
                is_anyclass = issubclass(t, type)
            except TypeError:  # t is not a class (old Boost; see SF #502085)
                is_anyclass = False

            if is_anyclass:
                return _class_reduce(obj)
            elif isinstance(obj, types.FunctionType):
                return self._function_reduce(obj)
            else:
                # fallback to save_global, including the Pickler's
                # dispatch_table
                return NotImplemented

    else:
        # When reducer_override is not available, hack the pure-Python
        # Pickler's types.FunctionType and type savers. Note: the type saver
        # must override Pickler.save_global, because pickle.py contains a
        # hard-coded call to save_global when pickling meta-classes.
        dispatch = pickle.Pickler.dispatch.copy()

        def _save_reduce_pickle5(
            self,
            func,
            args,
            state=None,
            listitems=None,
            dictitems=None,
            state_setter=None,
            obj=None,
        ):
            save = self.save
            write = self.write
            self.save_reduce(
                func,
                args,
                state=None,
                listitems=listitems,
                dictitems=dictitems,
                obj=obj,
            )
            # backport of the Python 3.8 state_setter pickle operations
            save(state_setter)
            save(obj)  # simple BINGET opcode as obj is already memoized.
            save(state)
            write(pickle.TUPLE2)
            # Trigger a state_setter(obj, state) function call.
            write(pickle.REDUCE)
            # The purpose of state_setter is to carry-out an
            # inplace modification of obj. We do not care about what the
            # method might return, so its output is eventually removed from
            # the stack.
            write(pickle.POP)

        def save_global(self, obj, name=None, pack=struct.pack):
            """Main dispatch method.

            The name of this method is somewhat misleading: all types get
            dispatched here.
            """
            if obj is type(None):  # noqa
                return self.save_reduce(type, (None,), obj=obj)
            elif obj is type(Ellipsis):
                return self.save_reduce(type, (Ellipsis,), obj=obj)
            elif obj is type(NotImplemented):
                return self.save_reduce(type, (NotImplemented,), obj=obj)
            elif obj in _BUILTIN_TYPE_NAMES:
                return self.save_reduce(
                    _builtin_type, (_BUILTIN_TYPE_NAMES[obj],), obj=obj
                )

            if name is not None:
                super().save_global(obj, name=name)
            elif not _should_pickle_by_reference(obj, name=name):
                self._save_reduce_pickle5(*_dynamic_class_reduce(obj), obj=obj)
            else:
                super().save_global(obj, name=name)

        dispatch[type] = save_global

        def save_function(self, obj, name=None):
            """Registered with the dispatch to handle all function types.

            Determines what kind of function obj is (e.g. lambda, defined at
            interactive prompt, etc) and handles the pickling appropriately.
            """
            if _should_pickle_by_reference(obj, name=name):
                return super().save_global(obj, name=name)
            elif PYPY and isinstance(obj.__code__, builtin_code_type):
                return self.save_pypy_builtin_func(obj)
            else:
                return self._save_reduce_pickle5(
                    *self._dynamic_function_reduce(obj), obj=obj
                )

        def save_pypy_builtin_func(self, obj):
            """Save pypy equivalent of builtin functions.

            PyPy does not have the concept of builtin-functions. Instead,
            builtin-functions are simple function instances, but with a
            builtin-code attribute.
            Most of the time, builtin functions should be pickled by attribute.
            But PyPy has flaky support for __qualname__, so some builtin
            functions such as float.__new__ will be classified as dynamic. For
            this reason only, we created this special routine. Because
            builtin-functions are not expected to have closure or globals,
            there is no additional hack (compared the one already implemented
            in pickle) to protect ourselves from reference cycles. A simple
            (reconstructor, newargs, obj.__dict__) tuple is save_reduced.  Note
            also that PyPy improved their support for __qualname__ in v3.6, so
            this routing should be removed when cloudpickle supports only PyPy
            3.6 and later.
            """
            rv = (
                types.FunctionType,
                (obj.__code__, {}, obj.__name__, obj.__defaults__, obj.__closure__),
                obj.__dict__,
            )
            self.save_reduce(*rv, obj=obj)

        dispatch[types.FunctionType] = save_function


# Shorthands similar to pickle.dump/pickle.dumps


def dump(obj, file, protocol=None, buffer_callback=None):
    """Serialize obj as bytes streamed into file

    protocol defaults to cloudpickle.DEFAULT_PROTOCOL which is an alias to
    pickle.HIGHEST_PROTOCOL. This setting favors maximum communication
    speed between processes running the same Python version.

    Set protocol=pickle.DEFAULT_PROTOCOL instead if you need to ensure
    compatibility with older versions of Python (although this is not always
    guaranteed to work because cloudpickle relies on some internal
    implementation details that can change from one Python version to the
    next).
    """
    Pickler(file, protocol=protocol, buffer_callback=buffer_callback).dump(obj)


def dumps(obj, protocol=None, buffer_callback=None):
    """Serialize obj as a string of bytes allocated in memory

    protocol defaults to cloudpickle.DEFAULT_PROTOCOL which is an alias to
    pickle.HIGHEST_PROTOCOL. This setting favors maximum communication
    speed between processes running the same Python version.

    Set protocol=pickle.DEFAULT_PROTOCOL instead if you need to ensure
    compatibility with older versions of Python (although this is not always
    guaranteed to work because cloudpickle relies on some internal
    implementation details that can change from one Python version to the
    next).
    """
    with io.BytesIO() as file:
        cp = Pickler(file, protocol=protocol, buffer_callback=buffer_callback)
        cp.dump(obj)
        return file.getvalue()


# Include pickles unloading functions in this namespace for convenience.
load, loads = pickle.load, pickle.loads

# Backward compat alias.
CloudPickler = Pickler

# === NexusCore/openenv\Lib\site-packages\pyasn1_modules\rfc3280.py ===
# coding: utf-8
#
# This file is part of pyasn1-modules software.
#
# Created by Stanisław Pitucha with asn1ate tool.
# Copyright (c) 2005-2020, Ilya Etingof <etingof@gmail.com>
# License: http://snmplabs.com/pyasn1/license.html
#
# Internet X.509 Public Key Infrastructure Certificate and Certificate
# Revocation List (CRL) Profile
#
# ASN.1 source from:
# http://www.ietf.org/rfc/rfc3280.txt
#
from pyasn1.type import char
from pyasn1.type import constraint
from pyasn1.type import namedtype
from pyasn1.type import namedval
from pyasn1.type import tag
from pyasn1.type import univ
from pyasn1.type import useful

MAX = float('inf')


def _OID(*components):
    output = []
    for x in tuple(components):
        if isinstance(x, univ.ObjectIdentifier):
            output.extend(list(x))
        else:
            output.append(int(x))

    return univ.ObjectIdentifier(output)


unformatted_postal_address = univ.Integer(16)

ub_organizational_units = univ.Integer(4)

ub_organizational_unit_name_length = univ.Integer(32)


class OrganizationalUnitName(char.PrintableString):
    pass


OrganizationalUnitName.subtypeSpec = constraint.ValueSizeConstraint(1, ub_organizational_unit_name_length)


class OrganizationalUnitNames(univ.SequenceOf):
    pass


OrganizationalUnitNames.componentType = OrganizationalUnitName()
OrganizationalUnitNames.sizeSpec = constraint.ValueSizeConstraint(1, ub_organizational_units)


class AttributeType(univ.ObjectIdentifier):
    pass


id_at = _OID(2, 5, 4)

id_at_name = _OID(id_at, 41)

ub_pds_parameter_length = univ.Integer(30)


class PDSParameter(univ.Set):
    pass


PDSParameter.componentType = namedtype.NamedTypes(
    namedtype.OptionalNamedType('printable-string', char.PrintableString().subtype(
        subtypeSpec=constraint.ValueSizeConstraint(1, ub_pds_parameter_length))),
    namedtype.OptionalNamedType('teletex-string', char.TeletexString().subtype(
        subtypeSpec=constraint.ValueSizeConstraint(1, ub_pds_parameter_length)))
)


class PhysicalDeliveryOrganizationName(PDSParameter):
    pass


ub_organization_name_length = univ.Integer(64)

ub_domain_defined_attribute_type_length = univ.Integer(8)

ub_domain_defined_attribute_value_length = univ.Integer(128)


class TeletexDomainDefinedAttribute(univ.Sequence):
    pass


TeletexDomainDefinedAttribute.componentType = namedtype.NamedTypes(
    namedtype.NamedType('type', char.TeletexString().subtype(
        subtypeSpec=constraint.ValueSizeConstraint(1, ub_domain_defined_attribute_type_length))),
    namedtype.NamedType('value', char.TeletexString().subtype(
        subtypeSpec=constraint.ValueSizeConstraint(1, ub_domain_defined_attribute_value_length)))
)

id_pkix = _OID(1, 3, 6, 1, 5, 5, 7)

id_qt = _OID(id_pkix, 2)


class PresentationAddress(univ.Sequence):
    pass


PresentationAddress.componentType = namedtype.NamedTypes(
    namedtype.OptionalNamedType('pSelector', univ.OctetString().subtype(
        explicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 0))),
    namedtype.OptionalNamedType('sSelector', univ.OctetString().subtype(
        explicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 1))),
    namedtype.OptionalNamedType('tSelector', univ.OctetString().subtype(
        explicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 2))),
    namedtype.NamedType('nAddresses', univ.SetOf(componentType=univ.OctetString()).subtype(
        explicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 3)))
)


class AlgorithmIdentifier(univ.Sequence):
    pass


AlgorithmIdentifier.componentType = namedtype.NamedTypes(
    namedtype.NamedType('algorithm', univ.ObjectIdentifier()),
    namedtype.OptionalNamedType('parameters', univ.Any())
)


class UniqueIdentifier(univ.BitString):
    pass


class Extension(univ.Sequence):
    pass


Extension.componentType = namedtype.NamedTypes(
    namedtype.NamedType('extnID', univ.ObjectIdentifier()),
    namedtype.DefaultedNamedType('critical', univ.Boolean().subtype(value=0)),
    namedtype.NamedType('extnValue', univ.OctetString())
)


class Extensions(univ.SequenceOf):
    pass


Extensions.componentType = Extension()
Extensions.sizeSpec = constraint.ValueSizeConstraint(1, MAX)


class CertificateSerialNumber(univ.Integer):
    pass


class SubjectPublicKeyInfo(univ.Sequence):
    pass


SubjectPublicKeyInfo.componentType = namedtype.NamedTypes(
    namedtype.NamedType('algorithm', AlgorithmIdentifier()),
    namedtype.NamedType('subjectPublicKey', univ.BitString())
)


class Time(univ.Choice):
    pass


Time.componentType = namedtype.NamedTypes(
    namedtype.NamedType('utcTime', useful.UTCTime()),
    namedtype.NamedType('generalTime', useful.GeneralizedTime())
)


class Validity(univ.Sequence):
    pass


Validity.componentType = namedtype.NamedTypes(
    namedtype.NamedType('notBefore', Time()),
    namedtype.NamedType('notAfter', Time())
)


class Version(univ.Integer):
    pass


Version.namedValues = namedval.NamedValues(
    ('v1', 0),
    ('v2', 1),
    ('v3', 2)
)


class AttributeValue(univ.Any):
    pass


class AttributeTypeAndValue(univ.Sequence):
    pass


AttributeTypeAndValue.componentType = namedtype.NamedTypes(
    namedtype.NamedType('type', AttributeType()),
    namedtype.NamedType('value', AttributeValue())
)


class RelativeDistinguishedName(univ.SetOf):
    pass


RelativeDistinguishedName.componentType = AttributeTypeAndValue()
RelativeDistinguishedName.sizeSpec = constraint.ValueSizeConstraint(1, MAX)


class RDNSequence(univ.SequenceOf):
    pass


RDNSequence.componentType = RelativeDistinguishedName()


class Name(univ.Choice):
    pass


Name.componentType = namedtype.NamedTypes(
    namedtype.NamedType('rdnSequence', RDNSequence())
)


class TBSCertificate(univ.Sequence):
    pass


TBSCertificate.componentType = namedtype.NamedTypes(
    namedtype.DefaultedNamedType('version',
                                 Version().subtype(explicitTag=tag.Tag(tag.tagClassContext,
                                                                       tag.tagFormatSimple, 0)).subtype(value="v1")),
    namedtype.NamedType('serialNumber', CertificateSerialNumber()),
    namedtype.NamedType('signature', AlgorithmIdentifier()),
    namedtype.NamedType('issuer', Name()),
    namedtype.NamedType('validity', Validity()),
    namedtype.NamedType('subject', Name()),
    namedtype.NamedType('subjectPublicKeyInfo', SubjectPublicKeyInfo()),
    namedtype.OptionalNamedType('issuerUniqueID', UniqueIdentifier().subtype(
        implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 1))),
    namedtype.OptionalNamedType('subjectUniqueID', UniqueIdentifier().subtype(
        implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 2))),
    namedtype.OptionalNamedType('extensions',
                                Extensions().subtype(explicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 3)))
)


class Certificate(univ.Sequence):
    pass


Certificate.componentType = namedtype.NamedTypes(
    namedtype.NamedType('tbsCertificate', TBSCertificate()),
    namedtype.NamedType('signatureAlgorithm', AlgorithmIdentifier()),
    namedtype.NamedType('signature', univ.BitString())
)

ub_surname_length = univ.Integer(40)


class TeletexOrganizationName(char.TeletexString):
    pass


TeletexOrganizationName.subtypeSpec = constraint.ValueSizeConstraint(1, ub_organization_name_length)

ub_e163_4_sub_address_length = univ.Integer(40)

teletex_common_name = univ.Integer(2)

ub_country_name_alpha_length = univ.Integer(2)

ub_country_name_numeric_length = univ.Integer(3)


class CountryName(univ.Choice):
    pass


CountryName.tagSet = univ.Choice.tagSet.tagExplicitly(tag.Tag(tag.tagClassApplication, tag.tagFormatConstructed, 1))
CountryName.componentType = namedtype.NamedTypes(
    namedtype.NamedType('x121-dcc-code', char.NumericString().subtype(
        subtypeSpec=constraint.ValueSizeConstraint(ub_country_name_numeric_length, ub_country_name_numeric_length))),
    namedtype.NamedType('iso-3166-alpha2-code', char.PrintableString().subtype(
        subtypeSpec=constraint.ValueSizeConstraint(ub_country_name_alpha_length, ub_country_name_alpha_length)))
)

extension_OR_address_components = univ.Integer(12)

id_at_dnQualifier = _OID(id_at, 46)

ub_e163_4_number_length = univ.Integer(15)


class ExtendedNetworkAddress(univ.Choice):
    pass


ExtendedNetworkAddress.componentType = namedtype.NamedTypes(
    namedtype.NamedType('e163-4-address', univ.Sequence(componentType=namedtype.NamedTypes(
        namedtype.NamedType('number', char.NumericString().subtype(
            subtypeSpec=constraint.ValueSizeConstraint(1, ub_e163_4_number_length)).subtype(
            implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 0))),
        namedtype.OptionalNamedType('sub-address', char.NumericString().subtype(
            subtypeSpec=constraint.ValueSizeConstraint(1, ub_e163_4_sub_address_length)).subtype(
            implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 1)))
    ))
                        ),
    namedtype.NamedType('psap-address', PresentationAddress().subtype(
        implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatConstructed, 0)))
)

terminal_type = univ.Integer(23)

id_domainComponent = _OID(0, 9, 2342, 19200300, 100, 1, 25)

ub_state_name = univ.Integer(128)


class X520StateOrProvinceName(univ.Choice):
    pass


X520StateOrProvinceName.componentType = namedtype.NamedTypes(
    namedtype.NamedType('teletexString',
                        char.TeletexString().subtype(subtypeSpec=constraint.ValueSizeConstraint(1, ub_state_name))),
    namedtype.NamedType('printableString',
                        char.PrintableString().subtype(subtypeSpec=constraint.ValueSizeConstraint(1, ub_state_name))),
    namedtype.NamedType('universalString',
                        char.UniversalString().subtype(subtypeSpec=constraint.ValueSizeConstraint(1, ub_state_name))),
    namedtype.NamedType('utf8String',
                        char.UTF8String().subtype(subtypeSpec=constraint.ValueSizeConstraint(1, ub_state_name))),
    namedtype.NamedType('bmpString',
                        char.BMPString().subtype(subtypeSpec=constraint.ValueSizeConstraint(1, ub_state_name)))
)

ub_organization_name = univ.Integer(64)


class X520OrganizationName(univ.Choice):
    pass


X520OrganizationName.componentType = namedtype.NamedTypes(
    namedtype.NamedType('teletexString', char.TeletexString().subtype(
        subtypeSpec=constraint.ValueSizeConstraint(1, ub_organization_name))),
    namedtype.NamedType('printableString', char.PrintableString().subtype(
        subtypeSpec=constraint.ValueSizeConstraint(1, ub_organization_name))),
    namedtype.NamedType('universalString', char.UniversalString().subtype(
        subtypeSpec=constraint.ValueSizeConstraint(1, ub_organization_name))),
    namedtype.NamedType('utf8String',
                        char.UTF8String().subtype(subtypeSpec=constraint.ValueSizeConstraint(1, ub_organization_name))),
    namedtype.NamedType('bmpString',
                        char.BMPString().subtype(subtypeSpec=constraint.ValueSizeConstraint(1, ub_organization_name)))
)

ub_emailaddress_length = univ.Integer(128)


class ExtensionPhysicalDeliveryAddressComponents(PDSParameter):
    pass


id_at_surname = _OID(id_at, 4)

ub_common_name_length = univ.Integer(64)

id_ad = _OID(id_pkix, 48)

ub_numeric_user_id_length = univ.Integer(32)


class NumericUserIdentifier(char.NumericString):
    pass


NumericUserIdentifier.subtypeSpec = constraint.ValueSizeConstraint(1, ub_numeric_user_id_length)


class OrganizationName(char.PrintableString):
    pass


OrganizationName.subtypeSpec = constraint.ValueSizeConstraint(1, ub_organization_name_length)

ub_domain_name_length = univ.Integer(16)


class AdministrationDomainName(univ.Choice):
    pass


AdministrationDomainName.tagSet = univ.Choice.tagSet.tagExplicitly(
    tag.Tag(tag.tagClassApplication, tag.tagFormatConstructed, 2))
AdministrationDomainName.componentType = namedtype.NamedTypes(
    namedtype.NamedType('numeric', char.NumericString().subtype(
        subtypeSpec=constraint.ValueSizeConstraint(0, ub_domain_name_length))),
    namedtype.NamedType('printable', char.PrintableString().subtype(
        subtypeSpec=constraint.ValueSizeConstraint(0, ub_domain_name_length)))
)


class PrivateDomainName(univ.Choice):
    pass


PrivateDomainName.componentType = namedtype.NamedTypes(
    namedtype.NamedType('numeric', char.NumericString().subtype(
        subtypeSpec=constraint.ValueSizeConstraint(1, ub_domain_name_length))),
    namedtype.NamedType('printable', char.PrintableString().subtype(
        subtypeSpec=constraint.ValueSizeConstraint(1, ub_domain_name_length)))
)

ub_generation_qualifier_length = univ.Integer(3)

ub_given_name_length = univ.Integer(16)

ub_initials_length = univ.Integer(5)


class PersonalName(univ.Set):
    pass


PersonalName.componentType = namedtype.NamedTypes(
    namedtype.NamedType('surname', char.PrintableString().subtype(
        subtypeSpec=constraint.ValueSizeConstraint(1, ub_surname_length)).subtype(
        implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 0))),
    namedtype.OptionalNamedType('given-name', char.PrintableString().subtype(
        subtypeSpec=constraint.ValueSizeConstraint(1, ub_given_name_length)).subtype(
        implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 1))),
    namedtype.OptionalNamedType('initials', char.PrintableString().subtype(
        subtypeSpec=constraint.ValueSizeConstraint(1, ub_initials_length)).subtype(
        implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 2))),
    namedtype.OptionalNamedType('generation-qualifier', char.PrintableString().subtype(
        subtypeSpec=constraint.ValueSizeConstraint(1, ub_generation_qualifier_length)).subtype(
        implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 3)))
)

ub_terminal_id_length = univ.Integer(24)


class TerminalIdentifier(char.PrintableString):
    pass


TerminalIdentifier.subtypeSpec = constraint.ValueSizeConstraint(1, ub_terminal_id_length)

ub_x121_address_length = univ.Integer(16)


class X121Address(char.NumericString):
    pass


X121Address.subtypeSpec = constraint.ValueSizeConstraint(1, ub_x121_address_length)


class NetworkAddress(X121Address):
    pass


class BuiltInStandardAttributes(univ.Sequence):
    pass


BuiltInStandardAttributes.componentType = namedtype.NamedTypes(
    namedtype.OptionalNamedType('country-name', CountryName()),
    namedtype.OptionalNamedType('administration-domain-name', AdministrationDomainName()),
    namedtype.OptionalNamedType('network-address', NetworkAddress().subtype(
        implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 0))),
    namedtype.OptionalNamedType('terminal-identifier', TerminalIdentifier().subtype(
        implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 1))),
    namedtype.OptionalNamedType('private-domain-name', PrivateDomainName().subtype(
        explicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatConstructed, 2))),
    namedtype.OptionalNamedType('organization-name', OrganizationName().subtype(
        implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 3))),
    namedtype.OptionalNamedType('numeric-user-identifier', NumericUserIdentifier().subtype(
        implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 4))),
    namedtype.OptionalNamedType('personal-name', PersonalName().subtype(
        implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatConstructed, 5))),
    namedtype.OptionalNamedType('organizational-unit-names', OrganizationalUnitNames().subtype(
        implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 6)))
)

ub_domain_defined_attributes = univ.Integer(4)


class BuiltInDomainDefinedAttribute(univ.Sequence):
    pass


BuiltInDomainDefinedAttribute.componentType = namedtype.NamedTypes(
    namedtype.NamedType('type', char.PrintableString().subtype(
        subtypeSpec=constraint.ValueSizeConstraint(1, ub_domain_defined_attribute_type_length))),
    namedtype.NamedType('value', char.PrintableString().subtype(
        subtypeSpec=constraint.ValueSizeConstraint(1, ub_domain_defined_attribute_value_length)))
)


class BuiltInDomainDefinedAttributes(univ.SequenceOf):
    pass


BuiltInDomainDefinedAttributes.componentType = BuiltInDomainDefinedAttribute()
BuiltInDomainDefinedAttributes.sizeSpec = constraint.ValueSizeConstraint(1, ub_domain_defined_attributes)

ub_extension_attributes = univ.Integer(256)


class ExtensionAttribute(univ.Sequence):
    pass


ExtensionAttribute.componentType = namedtype.NamedTypes(
    namedtype.NamedType('extension-attribute-type', univ.Integer().subtype(
        subtypeSpec=constraint.ValueRangeConstraint(0, ub_extension_attributes)).subtype(
        implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 0))),
    namedtype.NamedType('extension-attribute-value',
                        univ.Any().subtype(explicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 1)))
)


class ExtensionAttributes(univ.SetOf):
    pass


ExtensionAttributes.componentType = ExtensionAttribute()
ExtensionAttributes.sizeSpec = constraint.ValueSizeConstraint(1, ub_extension_attributes)


class ORAddress(univ.Sequence):
    pass


ORAddress.componentType = namedtype.NamedTypes(
    namedtype.NamedType('built-in-standard-attributes', BuiltInStandardAttributes()),
    namedtype.OptionalNamedType('built-in-domain-defined-attributes', BuiltInDomainDefinedAttributes()),
    namedtype.OptionalNamedType('extension-attributes', ExtensionAttributes())
)

id_pe = _OID(id_pkix, 1)

ub_title = univ.Integer(64)


class X520Title(univ.Choice):
    pass


X520Title.componentType = namedtype.NamedTypes(
    namedtype.NamedType('teletexString',
                        char.TeletexString().subtype(subtypeSpec=constraint.ValueSizeConstraint(1, ub_title))),
    namedtype.NamedType('printableString',
                        char.PrintableString().subtype(subtypeSpec=constraint.ValueSizeConstraint(1, ub_title))),
    namedtype.NamedType('universalString',
                        char.UniversalString().subtype(subtypeSpec=constraint.ValueSizeConstraint(1, ub_title))),
    namedtype.NamedType('utf8String',
                        char.UTF8String().subtype(subtypeSpec=constraint.ValueSizeConstraint(1, ub_title))),
    namedtype.NamedType('bmpString', char.BMPString().subtype(subtypeSpec=constraint.ValueSizeConstraint(1, ub_title)))
)

id_at_organizationalUnitName = _OID(id_at, 11)


class EmailAddress(char.IA5String):
    pass


EmailAddress.subtypeSpec = constraint.ValueSizeConstraint(1, ub_emailaddress_length)

physical_delivery_country_name = univ.Integer(8)

id_at_givenName = _OID(id_at, 42)


class TeletexCommonName(char.TeletexString):
    pass


TeletexCommonName.subtypeSpec = constraint.ValueSizeConstraint(1, ub_common_name_length)

id_qt_cps = _OID(id_qt, 1)


class LocalPostalAttributes(PDSParameter):
    pass


class StreetAddress(PDSParameter):
    pass


id_kp = _OID(id_pkix, 3)


class DirectoryString(univ.Choice):
    pass


DirectoryString.componentType = namedtype.NamedTypes(
    namedtype.NamedType('teletexString',
                        char.TeletexString().subtype(subtypeSpec=constraint.ValueSizeConstraint(1, MAX))),
    namedtype.NamedType('printableString',
                        char.PrintableString().subtype(subtypeSpec=constraint.ValueSizeConstraint(1, MAX))),
    namedtype.NamedType('universalString',
                        char.UniversalString().subtype(subtypeSpec=constraint.ValueSizeConstraint(1, MAX))),
    namedtype.NamedType('utf8String', char.UTF8String().subtype(subtypeSpec=constraint.ValueSizeConstraint(1, MAX))),
    namedtype.NamedType('bmpString', char.BMPString().subtype(subtypeSpec=constraint.ValueSizeConstraint(1, MAX)))
)


class DomainComponent(char.IA5String):
    pass


id_at_initials = _OID(id_at, 43)

id_qt_unotice = _OID(id_qt, 2)

ub_pds_name_length = univ.Integer(16)


class PDSName(char.PrintableString):
    pass


PDSName.subtypeSpec = constraint.ValueSizeConstraint(1, ub_pds_name_length)


class PosteRestanteAddress(PDSParameter):
    pass


class DistinguishedName(RDNSequence):
    pass


class CommonName(char.PrintableString):
    pass


CommonName.subtypeSpec = constraint.ValueSizeConstraint(1, ub_common_name_length)

ub_serial_number = univ.Integer(64)


class X520SerialNumber(char.PrintableString):
    pass


X520SerialNumber.subtypeSpec = constraint.ValueSizeConstraint(1, ub_serial_number)

id_at_generationQualifier = _OID(id_at, 44)

ub_organizational_unit_name = univ.Integer(64)

id_ad_ocsp = _OID(id_ad, 1)


class TeletexOrganizationalUnitName(char.TeletexString):
    pass


TeletexOrganizationalUnitName.subtypeSpec = constraint.ValueSizeConstraint(1, ub_organizational_unit_name_length)


class TeletexPersonalName(univ.Set):
    pass


TeletexPersonalName.componentType = namedtype.NamedTypes(
    namedtype.NamedType('surname', char.TeletexString().subtype(
        subtypeSpec=constraint.ValueSizeConstraint(1, ub_surname_length)).subtype(
        implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 0))),
    namedtype.OptionalNamedType('given-name', char.TeletexString().subtype(
        subtypeSpec=constraint.ValueSizeConstraint(1, ub_given_name_length)).subtype(
        implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 1))),
    namedtype.OptionalNamedType('initials', char.TeletexString().subtype(
        subtypeSpec=constraint.ValueSizeConstraint(1, ub_initials_length)).subtype(
        implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 2))),
    namedtype.OptionalNamedType('generation-qualifier', char.TeletexString().subtype(
        subtypeSpec=constraint.ValueSizeConstraint(1, ub_generation_qualifier_length)).subtype(
        implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 3)))
)


class TeletexDomainDefinedAttributes(univ.SequenceOf):
    pass


TeletexDomainDefinedAttributes.componentType = TeletexDomainDefinedAttribute()
TeletexDomainDefinedAttributes.sizeSpec = constraint.ValueSizeConstraint(1, ub_domain_defined_attributes)


class TBSCertList(univ.Sequence):
    pass


TBSCertList.componentType = namedtype.NamedTypes(
    namedtype.OptionalNamedType('version', Version()),
    namedtype.NamedType('signature', AlgorithmIdentifier()),
    namedtype.NamedType('issuer', Name()),
    namedtype.NamedType('thisUpdate', Time()),
    namedtype.OptionalNamedType('nextUpdate', Time()),
    namedtype.OptionalNamedType('revokedCertificates',
                                univ.SequenceOf(componentType=univ.Sequence(componentType=namedtype.NamedTypes(
                                    namedtype.NamedType('userCertificate', CertificateSerialNumber()),
                                    namedtype.NamedType('revocationDate', Time()),
                                    namedtype.OptionalNamedType('crlEntryExtensions', Extensions())
                                ))
                                )),
    namedtype.OptionalNamedType('crlExtensions',
                                Extensions().subtype(explicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 0)))
)

local_postal_attributes = univ.Integer(21)

pkcs_9 = _OID(1, 2, 840, 113549, 1, 9)


class PhysicalDeliveryCountryName(univ.Choice):
    pass


PhysicalDeliveryCountryName.componentType = namedtype.NamedTypes(
    namedtype.NamedType('x121-dcc-code', char.NumericString().subtype(
        subtypeSpec=constraint.ValueSizeConstraint(ub_country_name_numeric_length, ub_country_name_numeric_length))),
    namedtype.NamedType('iso-3166-alpha2-code', char.PrintableString().subtype(
        subtypeSpec=constraint.ValueSizeConstraint(ub_country_name_alpha_length, ub_country_name_alpha_length)))
)

ub_name = univ.Integer(32768)


class X520name(univ.Choice):
    pass


X520name.componentType = namedtype.NamedTypes(
    namedtype.NamedType('teletexString',
                        char.TeletexString().subtype(subtypeSpec=constraint.ValueSizeConstraint(1, ub_name))),
    namedtype.NamedType('printableString',
                        char.PrintableString().subtype(subtypeSpec=constraint.ValueSizeConstraint(1, ub_name))),
    namedtype.NamedType('universalString',
                        char.UniversalString().subtype(subtypeSpec=constraint.ValueSizeConstraint(1, ub_name))),
    namedtype.NamedType('utf8String',
                        char.UTF8String().subtype(subtypeSpec=constraint.ValueSizeConstraint(1, ub_name))),
    namedtype.NamedType('bmpString', char.BMPString().subtype(subtypeSpec=constraint.ValueSizeConstraint(1, ub_name)))
)

id_emailAddress = _OID(pkcs_9, 1)


class TerminalType(univ.Integer):
    pass


TerminalType.namedValues = namedval.NamedValues(
    ('telex', 3),
    ('teletex', 4),
    ('g3-facsimile', 5),
    ('g4-facsimile', 6),
    ('ia5-terminal', 7),
    ('videotex', 8)
)


class X520OrganizationalUnitName(univ.Choice):
    pass


X520OrganizationalUnitName.componentType = namedtype.NamedTypes(
    namedtype.NamedType('teletexString', char.TeletexString().subtype(
        subtypeSpec=constraint.ValueSizeConstraint(1, ub_organizational_unit_name))),
    namedtype.NamedType('printableString', char.PrintableString().subtype(
        subtypeSpec=constraint.ValueSizeConstraint(1, ub_organizational_unit_name))),
    namedtype.NamedType('universalString', char.UniversalString().subtype(
        subtypeSpec=constraint.ValueSizeConstraint(1, ub_organizational_unit_name))),
    namedtype.NamedType('utf8String', char.UTF8String().subtype(
        subtypeSpec=constraint.ValueSizeConstraint(1, ub_organizational_unit_name))),
    namedtype.NamedType('bmpString', char.BMPString().subtype(
        subtypeSpec=constraint.ValueSizeConstraint(1, ub_organizational_unit_name)))
)

id_at_commonName = _OID(id_at, 3)

pds_name = univ.Integer(7)

post_office_box_address = univ.Integer(18)

ub_locality_name = univ.Integer(128)


class X520LocalityName(univ.Choice):
    pass


X520LocalityName.componentType = namedtype.NamedTypes(
    namedtype.NamedType('teletexString',
                        char.TeletexString().subtype(subtypeSpec=constraint.ValueSizeConstraint(1, ub_locality_name))),
    namedtype.NamedType('printableString', char.PrintableString().subtype(
        subtypeSpec=constraint.ValueSizeConstraint(1, ub_locality_name))),
    namedtype.NamedType('universalString', char.UniversalString().subtype(
        subtypeSpec=constraint.ValueSizeConstraint(1, ub_locality_name))),
    namedtype.NamedType('utf8String',
                        char.UTF8String().subtype(subtypeSpec=constraint.ValueSizeConstraint(1, ub_locality_name))),
    namedtype.NamedType('bmpString',
                        char.BMPString().subtype(subtypeSpec=constraint.ValueSizeConstraint(1, ub_locality_name)))
)

id_ad_timeStamping = _OID(id_ad, 3)

id_at_countryName = _OID(id_at, 6)

physical_delivery_personal_name = univ.Integer(13)

teletex_personal_name = univ.Integer(4)

teletex_organizational_unit_names = univ.Integer(5)


class PhysicalDeliveryPersonalName(PDSParameter):
    pass


ub_postal_code_length = univ.Integer(16)


class PostalCode(univ.Choice):
    pass


PostalCode.componentType = namedtype.NamedTypes(
    namedtype.NamedType('numeric-code', char.NumericString().subtype(
        subtypeSpec=constraint.ValueSizeConstraint(1, ub_postal_code_length))),
    namedtype.NamedType('printable-code', char.PrintableString().subtype(
        subtypeSpec=constraint.ValueSizeConstraint(1, ub_postal_code_length)))
)


class X520countryName(char.PrintableString):
    pass


X520countryName.subtypeSpec = constraint.ValueSizeConstraint(2, 2)

postal_code = univ.Integer(9)

id_ad_caRepository = _OID(id_ad, 5)

extension_physical_delivery_address_components = univ.Integer(15)


class PostOfficeBoxAddress(PDSParameter):
    pass


class PhysicalDeliveryOfficeName(PDSParameter):
    pass


id_at_title = _OID(id_at, 12)

id_at_serialNumber = _OID(id_at, 5)

id_ad_caIssuers = _OID(id_ad, 2)

ub_integer_options = univ.Integer(256)


class CertificateList(univ.Sequence):
    pass


CertificateList.componentType = namedtype.NamedTypes(
    namedtype.NamedType('tbsCertList', TBSCertList()),
    namedtype.NamedType('signatureAlgorithm', AlgorithmIdentifier()),
    namedtype.NamedType('signature', univ.BitString())
)


class PhysicalDeliveryOfficeNumber(PDSParameter):
    pass


class TeletexOrganizationalUnitNames(univ.SequenceOf):
    pass


TeletexOrganizationalUnitNames.componentType = TeletexOrganizationalUnitName()
TeletexOrganizationalUnitNames.sizeSpec = constraint.ValueSizeConstraint(1, ub_organizational_units)

physical_delivery_office_name = univ.Integer(10)

ub_common_name = univ.Integer(64)


class ExtensionORAddressComponents(PDSParameter):
    pass


ub_pseudonym = univ.Integer(128)

poste_restante_address = univ.Integer(19)

id_at_organizationName = _OID(id_at, 10)

physical_delivery_office_number = univ.Integer(11)

id_at_pseudonym = _OID(id_at, 65)


class X520CommonName(univ.Choice):
    pass


X520CommonName.componentType = namedtype.NamedTypes(
    namedtype.NamedType('teletexString',
                        char.TeletexString().subtype(subtypeSpec=constraint.ValueSizeConstraint(1, ub_common_name))),
    namedtype.NamedType('printableString',
                        char.PrintableString().subtype(subtypeSpec=constraint.ValueSizeConstraint(1, ub_common_name))),
    namedtype.NamedType('universalString',
                        char.UniversalString().subtype(subtypeSpec=constraint.ValueSizeConstraint(1, ub_common_name))),
    namedtype.NamedType('utf8String',
                        char.UTF8String().subtype(subtypeSpec=constraint.ValueSizeConstraint(1, ub_common_name))),
    namedtype.NamedType('bmpString',
                        char.BMPString().subtype(subtypeSpec=constraint.ValueSizeConstraint(1, ub_common_name)))
)

physical_delivery_organization_name = univ.Integer(14)


class X520dnQualifier(char.PrintableString):
    pass


id_at_stateOrProvinceName = _OID(id_at, 8)

common_name = univ.Integer(1)

id_at_localityName = _OID(id_at, 7)

ub_match = univ.Integer(128)

ub_unformatted_address_length = univ.Integer(180)


class Attribute(univ.Sequence):
    pass


Attribute.componentType = namedtype.NamedTypes(
    namedtype.NamedType('type', AttributeType()),
    namedtype.NamedType('values', univ.SetOf(componentType=AttributeValue()))
)

extended_network_address = univ.Integer(22)

unique_postal_name = univ.Integer(20)

ub_pds_physical_address_lines = univ.Integer(6)


class UnformattedPostalAddress(univ.Set):
    pass


UnformattedPostalAddress.componentType = namedtype.NamedTypes(
    namedtype.OptionalNamedType('printable-address', univ.SequenceOf(componentType=char.PrintableString().subtype(
        subtypeSpec=constraint.ValueSizeConstraint(1, ub_pds_parameter_length)))),
    namedtype.OptionalNamedType('teletex-string', char.TeletexString().subtype(
        subtypeSpec=constraint.ValueSizeConstraint(1, ub_unformatted_address_length)))
)


class UniquePostalName(PDSParameter):
    pass


class X520Pseudonym(univ.Choice):
    pass


X520Pseudonym.componentType = namedtype.NamedTypes(
    namedtype.NamedType('teletexString',
                        char.TeletexString().subtype(subtypeSpec=constraint.ValueSizeConstraint(1, ub_pseudonym))),
    namedtype.NamedType('printableString',
                        char.PrintableString().subtype(subtypeSpec=constraint.ValueSizeConstraint(1, ub_pseudonym))),
    namedtype.NamedType('universalString',
                        char.UniversalString().subtype(subtypeSpec=constraint.ValueSizeConstraint(1, ub_pseudonym))),
    namedtype.NamedType('utf8String',
                        char.UTF8String().subtype(subtypeSpec=constraint.ValueSizeConstraint(1, ub_pseudonym))),
    namedtype.NamedType('bmpString',
                        char.BMPString().subtype(subtypeSpec=constraint.ValueSizeConstraint(1, ub_pseudonym)))
)

teletex_organization_name = univ.Integer(3)

teletex_domain_defined_attributes = univ.Integer(6)

street_address = univ.Integer(17)

id_kp_OCSPSigning = _OID(id_kp, 9)

id_ce = _OID(2, 5, 29)

id_ce_certificatePolicies = _OID(id_ce, 32)


class EDIPartyName(univ.Sequence):
    pass


EDIPartyName.componentType = namedtype.NamedTypes(
    namedtype.OptionalNamedType('nameAssigner', DirectoryString().subtype(
        implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 0))),
    namedtype.NamedType('partyName',
                        DirectoryString().subtype(implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 1)))
)


class AnotherName(univ.Sequence):
    pass


AnotherName.componentType = namedtype.NamedTypes(
    namedtype.NamedType('type-id', univ.ObjectIdentifier()),
    namedtype.NamedType('value', univ.Any().subtype(explicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 0)))
)


class GeneralName(univ.Choice):
    pass


GeneralName.componentType = namedtype.NamedTypes(
    namedtype.NamedType('otherName',
                        AnotherName().subtype(implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatConstructed, 0))),
    namedtype.NamedType('rfc822Name',
                        char.IA5String().subtype(implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 1))),
    namedtype.NamedType('dNSName',
                        char.IA5String().subtype(implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 2))),
    namedtype.NamedType('x400Address',
                        ORAddress().subtype(implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 3))),
    namedtype.NamedType('directoryName',
                        Name().subtype(implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatConstructed, 4))),
    namedtype.NamedType('ediPartyName',
                        EDIPartyName().subtype(implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatConstructed, 5))),
    namedtype.NamedType('uniformResourceIdentifier',
                        char.IA5String().subtype(implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 6))),
    namedtype.NamedType('iPAddress',
                        univ.OctetString().subtype(implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 7))),
    namedtype.NamedType('registeredID', univ.ObjectIdentifier().subtype(
        implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 8)))
)


class GeneralNames(univ.SequenceOf):
    pass


GeneralNames.componentType = GeneralName()
GeneralNames.sizeSpec = constraint.ValueSizeConstraint(1, MAX)


class IssuerAltName(GeneralNames):
    pass


id_ce_cRLDistributionPoints = _OID(id_ce, 31)


class CertPolicyId(univ.ObjectIdentifier):
    pass


class PolicyMappings(univ.SequenceOf):
    pass


PolicyMappings.componentType = univ.Sequence(componentType=namedtype.NamedTypes(
    namedtype.NamedType('issuerDomainPolicy', CertPolicyId()),
    namedtype.NamedType('subjectDomainPolicy', CertPolicyId())
))

PolicyMappings.sizeSpec = constraint.ValueSizeConstraint(1, MAX)


class PolicyQualifierId(univ.ObjectIdentifier):
    pass


holdInstruction = _OID(2, 2, 840, 10040, 2)

id_ce_subjectDirectoryAttributes = _OID(id_ce, 9)

id_holdinstruction_callissuer = _OID(holdInstruction, 2)


class SubjectDirectoryAttributes(univ.SequenceOf):
    pass


SubjectDirectoryAttributes.componentType = Attribute()
SubjectDirectoryAttributes.sizeSpec = constraint.ValueSizeConstraint(1, MAX)

anyPolicy = _OID(id_ce_certificatePolicies, 0)

id_ce_subjectAltName = _OID(id_ce, 17)

id_kp_emailProtection = _OID(id_kp, 4)


class ReasonFlags(univ.BitString):
    pass


ReasonFlags.namedValues = namedval.NamedValues(
    ('unused', 0),
    ('keyCompromise', 1),
    ('cACompromise', 2),
    ('affiliationChanged', 3),
    ('superseded', 4),
    ('cessationOfOperation', 5),
    ('certificateHold', 6),
    ('privilegeWithdrawn', 7),
    ('aACompromise', 8)
)


class DistributionPointName(univ.Choice):
    pass


DistributionPointName.componentType = namedtype.NamedTypes(
    namedtype.NamedType('fullName',
                        GeneralNames().subtype(implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 0))),
    namedtype.NamedType('nameRelativeToCRLIssuer', RelativeDistinguishedName().subtype(
        implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 1)))
)


class DistributionPoint(univ.Sequence):
    pass


DistributionPoint.componentType = namedtype.NamedTypes(
    namedtype.OptionalNamedType('distributionPoint', DistributionPointName().subtype(
        implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatConstructed, 0))),
    namedtype.OptionalNamedType('reasons', ReasonFlags().subtype(
        implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 1))),
    namedtype.OptionalNamedType('cRLIssuer', GeneralNames().subtype(
        implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 2)))
)

id_ce_keyUsage = _OID(id_ce, 15)


class PolicyQualifierInfo(univ.Sequence):
    pass


PolicyQualifierInfo.componentType = namedtype.NamedTypes(
    namedtype.NamedType('policyQualifierId', PolicyQualifierId()),
    namedtype.NamedType('qualifier', univ.Any())
)


class PolicyInformation(univ.Sequence):
    pass


PolicyInformation.componentType = namedtype.NamedTypes(
    namedtype.NamedType('policyIdentifier', CertPolicyId()),
    namedtype.OptionalNamedType('policyQualifiers', univ.SequenceOf(componentType=PolicyQualifierInfo()))
)


class CertificatePolicies(univ.SequenceOf):
    pass


CertificatePolicies.componentType = PolicyInformation()
CertificatePolicies.sizeSpec = constraint.ValueSizeConstraint(1, MAX)

id_ce_basicConstraints = _OID(id_ce, 19)


class HoldInstructionCode(univ.ObjectIdentifier):
    pass


class KeyPurposeId(univ.ObjectIdentifier):
    pass


class ExtKeyUsageSyntax(univ.SequenceOf):
    pass


ExtKeyUsageSyntax.componentType = KeyPurposeId()
ExtKeyUsageSyntax.sizeSpec = constraint.ValueSizeConstraint(1, MAX)


class SubjectAltName(GeneralNames):
    pass


class BasicConstraints(univ.Sequence):
    pass


BasicConstraints.componentType = namedtype.NamedTypes(
    namedtype.DefaultedNamedType('cA', univ.Boolean().subtype(value=0)),
    namedtype.OptionalNamedType('pathLenConstraint',
                                univ.Integer().subtype(subtypeSpec=constraint.ValueRangeConstraint(0, MAX)))
)


class SkipCerts(univ.Integer):
    pass


SkipCerts.subtypeSpec = constraint.ValueRangeConstraint(0, MAX)


class InhibitAnyPolicy(SkipCerts):
    pass


class CRLNumber(univ.Integer):
    pass


CRLNumber.subtypeSpec = constraint.ValueRangeConstraint(0, MAX)


class BaseCRLNumber(CRLNumber):
    pass


class KeyIdentifier(univ.OctetString):
    pass


class AuthorityKeyIdentifier(univ.Sequence):
    pass


AuthorityKeyIdentifier.componentType = namedtype.NamedTypes(
    namedtype.OptionalNamedType('keyIdentifier', KeyIdentifier().subtype(
        implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 0))),
    namedtype.OptionalNamedType('authorityCertIssuer', GeneralNames().subtype(
        implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 1))),
    namedtype.OptionalNamedType('authorityCertSerialNumber', CertificateSerialNumber().subtype(
        implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 2)))
)

id_ce_nameConstraints = _OID(id_ce, 30)

id_kp_serverAuth = _OID(id_kp, 1)

id_ce_freshestCRL = _OID(id_ce, 46)

id_ce_cRLReasons = _OID(id_ce, 21)


class CRLDistributionPoints(univ.SequenceOf):
    pass


CRLDistributionPoints.componentType = DistributionPoint()
CRLDistributionPoints.sizeSpec = constraint.ValueSizeConstraint(1, MAX)


class FreshestCRL(CRLDistributionPoints):
    pass


id_ce_inhibitAnyPolicy = _OID(id_ce, 54)


class CRLReason(univ.Enumerated):
    pass


CRLReason.namedValues = namedval.NamedValues(
    ('unspecified', 0),
    ('keyCompromise', 1),
    ('cACompromise', 2),
    ('affiliationChanged', 3),
    ('superseded', 4),
    ('cessationOfOperation', 5),
    ('certificateHold', 6),
    ('removeFromCRL', 8),
    ('privilegeWithdrawn', 9),
    ('aACompromise', 10)
)


class BaseDistance(univ.Integer):
    pass


BaseDistance.subtypeSpec = constraint.ValueRangeConstraint(0, MAX)


class GeneralSubtree(univ.Sequence):
    pass


GeneralSubtree.componentType = namedtype.NamedTypes(
    namedtype.NamedType('base', GeneralName()),
    namedtype.DefaultedNamedType('minimum', BaseDistance().subtype(
        implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 0)).subtype(value=0)),
    namedtype.OptionalNamedType('maximum', BaseDistance().subtype(
        implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 1)))
)


class GeneralSubtrees(univ.SequenceOf):
    pass


GeneralSubtrees.componentType = GeneralSubtree()
GeneralSubtrees.sizeSpec = constraint.ValueSizeConstraint(1, MAX)


class NameConstraints(univ.Sequence):
    pass


NameConstraints.componentType = namedtype.NamedTypes(
    namedtype.OptionalNamedType('permittedSubtrees', GeneralSubtrees().subtype(
        implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 0))),
    namedtype.OptionalNamedType('excludedSubtrees', GeneralSubtrees().subtype(
        implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 1)))
)

id_pe_authorityInfoAccess = _OID(id_pe, 1)

id_pe_subjectInfoAccess = _OID(id_pe, 11)

id_ce_certificateIssuer = _OID(id_ce, 29)

id_ce_invalidityDate = _OID(id_ce, 24)


class DirectoryString(univ.Choice):
    pass


DirectoryString.componentType = namedtype.NamedTypes(
    namedtype.NamedType('any', univ.Any())
)

id_ce_authorityKeyIdentifier = _OID(id_ce, 35)


class AccessDescription(univ.Sequence):
    pass


AccessDescription.componentType = namedtype.NamedTypes(
    namedtype.NamedType('accessMethod', univ.ObjectIdentifier()),
    namedtype.NamedType('accessLocation', GeneralName())
)


class AuthorityInfoAccessSyntax(univ.SequenceOf):
    pass


AuthorityInfoAccessSyntax.componentType = AccessDescription()
AuthorityInfoAccessSyntax.sizeSpec = constraint.ValueSizeConstraint(1, MAX)

id_ce_issuingDistributionPoint = _OID(id_ce, 28)


class CPSuri(char.IA5String):
    pass


class DisplayText(univ.Choice):
    pass


DisplayText.componentType = namedtype.NamedTypes(
    namedtype.NamedType('ia5String', char.IA5String().subtype(subtypeSpec=constraint.ValueSizeConstraint(1, 200))),
    namedtype.NamedType('visibleString',
                        char.VisibleString().subtype(subtypeSpec=constraint.ValueSizeConstraint(1, 200))),
    namedtype.NamedType('bmpString', char.BMPString().subtype(subtypeSpec=constraint.ValueSizeConstraint(1, 200))),
    namedtype.NamedType('utf8String', char.UTF8String().subtype(subtypeSpec=constraint.ValueSizeConstraint(1, 200)))
)


class NoticeReference(univ.Sequence):
    pass


NoticeReference.componentType = namedtype.NamedTypes(
    namedtype.NamedType('organization', DisplayText()),
    namedtype.NamedType('noticeNumbers', univ.SequenceOf(componentType=univ.Integer()))
)


class UserNotice(univ.Sequence):
    pass


UserNotice.componentType = namedtype.NamedTypes(
    namedtype.OptionalNamedType('noticeRef', NoticeReference()),
    namedtype.OptionalNamedType('explicitText', DisplayText())
)


class PrivateKeyUsagePeriod(univ.Sequence):
    pass


PrivateKeyUsagePeriod.componentType = namedtype.NamedTypes(
    namedtype.OptionalNamedType('notBefore', useful.GeneralizedTime().subtype(
        implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 0))),
    namedtype.OptionalNamedType('notAfter', useful.GeneralizedTime().subtype(
        implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 1)))
)

id_ce_subjectKeyIdentifier = _OID(id_ce, 14)


class CertificateIssuer(GeneralNames):
    pass


class InvalidityDate(useful.GeneralizedTime):
    pass


class SubjectInfoAccessSyntax(univ.SequenceOf):
    pass


SubjectInfoAccessSyntax.componentType = AccessDescription()
SubjectInfoAccessSyntax.sizeSpec = constraint.ValueSizeConstraint(1, MAX)


class KeyUsage(univ.BitString):
    pass


KeyUsage.namedValues = namedval.NamedValues(
    ('digitalSignature', 0),
    ('nonRepudiation', 1),
    ('keyEncipherment', 2),
    ('dataEncipherment', 3),
    ('keyAgreement', 4),
    ('keyCertSign', 5),
    ('cRLSign', 6),
    ('encipherOnly', 7),
    ('decipherOnly', 8)
)

id_ce_extKeyUsage = _OID(id_ce, 37)

anyExtendedKeyUsage = _OID(id_ce_extKeyUsage, 0)

id_ce_privateKeyUsagePeriod = _OID(id_ce, 16)

id_ce_policyMappings = _OID(id_ce, 33)

id_ce_cRLNumber = _OID(id_ce, 20)

id_ce_policyConstraints = _OID(id_ce, 36)

id_holdinstruction_none = _OID(holdInstruction, 1)

id_holdinstruction_reject = _OID(holdInstruction, 3)

id_kp_timeStamping = _OID(id_kp, 8)


class PolicyConstraints(univ.Sequence):
    pass


PolicyConstraints.componentType = namedtype.NamedTypes(
    namedtype.OptionalNamedType('requireExplicitPolicy',
                                SkipCerts().subtype(implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 0))),
    namedtype.OptionalNamedType('inhibitPolicyMapping',
                                SkipCerts().subtype(implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 1)))
)


class SubjectKeyIdentifier(KeyIdentifier):
    pass


id_kp_clientAuth = _OID(id_kp, 2)

id_ce_deltaCRLIndicator = _OID(id_ce, 27)

id_ce_issuerAltName = _OID(id_ce, 18)

id_kp_codeSigning = _OID(id_kp, 3)

id_ce_holdInstructionCode = _OID(id_ce, 23)


class IssuingDistributionPoint(univ.Sequence):
    pass


IssuingDistributionPoint.componentType = namedtype.NamedTypes(
    namedtype.OptionalNamedType('distributionPoint', DistributionPointName().subtype(
        implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatConstructed, 0))),
    namedtype.DefaultedNamedType('onlyContainsUserCerts', univ.Boolean().subtype(
        implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 1)).subtype(value=0)),
    namedtype.DefaultedNamedType('onlyContainsCACerts', univ.Boolean().subtype(
        implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 2)).subtype(value=0)),
    namedtype.OptionalNamedType('onlySomeReasons', ReasonFlags().subtype(
        implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 3))),
    namedtype.DefaultedNamedType('indirectCRL', univ.Boolean().subtype(
        implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 4)).subtype(value=0)),
    namedtype.DefaultedNamedType('onlyContainsAttributeCerts', univ.Boolean().subtype(
        implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 5)).subtype(value=0))
)

# === NexusCore/openenv\Lib\site-packages\setuptools\msvc.py ===
"""
Environment info about Microsoft Compilers.

>>> getfixture('windows_only')
>>> ei = EnvironmentInfo('amd64')
"""

from __future__ import annotations

import contextlib
import itertools
import json
import os
import os.path
import platform
from typing import TYPE_CHECKING, TypedDict

from more_itertools import unique_everseen

import distutils.errors

if TYPE_CHECKING:
    from typing_extensions import LiteralString, NotRequired

# https://github.com/python/mypy/issues/8166
if not TYPE_CHECKING and platform.system() == 'Windows':
    import winreg
    from os import environ
else:
    # Mock winreg and environ so the module can be imported on this platform.

    class winreg:
        HKEY_USERS = None
        HKEY_CURRENT_USER = None
        HKEY_LOCAL_MACHINE = None
        HKEY_CLASSES_ROOT = None

    environ: dict[str, str] = dict()


class PlatformInfo:
    """
    Current and Target Architectures information.

    Parameters
    ----------
    arch: str
        Target architecture.
    """

    current_cpu = environ.get('processor_architecture', '').lower()

    def __init__(self, arch) -> None:
        self.arch = arch.lower().replace('x64', 'amd64')

    @property
    def target_cpu(self):
        """
        Return Target CPU architecture.

        Return
        ------
        str
            Target CPU
        """
        return self.arch[self.arch.find('_') + 1 :]

    def target_is_x86(self):
        """
        Return True if target CPU is x86 32 bits..

        Return
        ------
        bool
            CPU is x86 32 bits
        """
        return self.target_cpu == 'x86'

    def current_is_x86(self):
        """
        Return True if current CPU is x86 32 bits..

        Return
        ------
        bool
            CPU is x86 32 bits
        """
        return self.current_cpu == 'x86'

    def current_dir(self, hidex86=False, x64=False) -> str:
        """
        Current platform specific subfolder.

        Parameters
        ----------
        hidex86: bool
            return '' and not '\x86' if architecture is x86.
        x64: bool
            return '\x64' and not '\amd64' if architecture is amd64.

        Return
        ------
        str
            subfolder: '\target', or '' (see hidex86 parameter)
        """
        return (
            ''
            if (self.current_cpu == 'x86' and hidex86)
            else r'\x64'
            if (self.current_cpu == 'amd64' and x64)
            else rf'\{self.current_cpu}'
        )

    def target_dir(self, hidex86=False, x64=False) -> str:
        r"""
        Target platform specific subfolder.

        Parameters
        ----------
        hidex86: bool
            return '' and not '\x86' if architecture is x86.
        x64: bool
            return '\x64' and not '\amd64' if architecture is amd64.

        Return
        ------
        str
            subfolder: '\current', or '' (see hidex86 parameter)
        """
        return (
            ''
            if (self.target_cpu == 'x86' and hidex86)
            else r'\x64'
            if (self.target_cpu == 'amd64' and x64)
            else rf'\{self.target_cpu}'
        )

    def cross_dir(self, forcex86=False):
        r"""
        Cross platform specific subfolder.

        Parameters
        ----------
        forcex86: bool
            Use 'x86' as current architecture even if current architecture is
            not x86.

        Return
        ------
        str
            subfolder: '' if target architecture is current architecture,
            '\current_target' if not.
        """
        current = 'x86' if forcex86 else self.current_cpu
        return (
            ''
            if self.target_cpu == current
            else self.target_dir().replace('\\', f'\\{current}_')
        )


class RegistryInfo:
    """
    Microsoft Visual Studio related registry information.

    Parameters
    ----------
    platform_info: PlatformInfo
        "PlatformInfo" instance.
    """

    HKEYS = (
        winreg.HKEY_USERS,
        winreg.HKEY_CURRENT_USER,
        winreg.HKEY_LOCAL_MACHINE,
        winreg.HKEY_CLASSES_ROOT,
    )

    def __init__(self, platform_info) -> None:
        self.pi = platform_info

    @property
    def visualstudio(self) -> str:
        """
        Microsoft Visual Studio root registry key.

        Return
        ------
        str
            Registry key
        """
        return 'VisualStudio'

    @property
    def sxs(self):
        """
        Microsoft Visual Studio SxS registry key.

        Return
        ------
        str
            Registry key
        """
        return os.path.join(self.visualstudio, 'SxS')

    @property
    def vc(self):
        """
        Microsoft Visual C++ VC7 registry key.

        Return
        ------
        str
            Registry key
        """
        return os.path.join(self.sxs, 'VC7')

    @property
    def vs(self):
        """
        Microsoft Visual Studio VS7 registry key.

        Return
        ------
        str
            Registry key
        """
        return os.path.join(self.sxs, 'VS7')

    @property
    def vc_for_python(self) -> str:
        """
        Microsoft Visual C++ for Python registry key.

        Return
        ------
        str
            Registry key
        """
        return r'DevDiv\VCForPython'

    @property
    def microsoft_sdk(self) -> str:
        """
        Microsoft SDK registry key.

        Return
        ------
        str
            Registry key
        """
        return 'Microsoft SDKs'

    @property
    def windows_sdk(self):
        """
        Microsoft Windows/Platform SDK registry key.

        Return
        ------
        str
            Registry key
        """
        return os.path.join(self.microsoft_sdk, 'Windows')

    @property
    def netfx_sdk(self):
        """
        Microsoft .NET Framework SDK registry key.

        Return
        ------
        str
            Registry key
        """
        return os.path.join(self.microsoft_sdk, 'NETFXSDK')

    @property
    def windows_kits_roots(self) -> str:
        """
        Microsoft Windows Kits Roots registry key.

        Return
        ------
        str
            Registry key
        """
        return r'Windows Kits\Installed Roots'

    def microsoft(self, key, x86=False):
        """
        Return key in Microsoft software registry.

        Parameters
        ----------
        key: str
            Registry key path where look.
        x86: str
            Force x86 software registry.

        Return
        ------
        str
            Registry key
        """
        node64 = '' if self.pi.current_is_x86() or x86 else 'Wow6432Node'
        return os.path.join('Software', node64, 'Microsoft', key)

    def lookup(self, key, name):
        """
        Look for values in registry in Microsoft software registry.

        Parameters
        ----------
        key: str
            Registry key path where look.
        name: str
            Value name to find.

        Return
        ------
        str
            value
        """
        key_read = winreg.KEY_READ
        openkey = winreg.OpenKey
        closekey = winreg.CloseKey
        ms = self.microsoft
        for hkey in self.HKEYS:
            bkey = None
            try:
                bkey = openkey(hkey, ms(key), 0, key_read)
            except OSError:
                if not self.pi.current_is_x86():
                    try:
                        bkey = openkey(hkey, ms(key, True), 0, key_read)
                    except OSError:
                        continue
                else:
                    continue
            try:
                return winreg.QueryValueEx(bkey, name)[0]
            except OSError:
                pass
            finally:
                if bkey:
                    closekey(bkey)
        return None


class SystemInfo:
    """
    Microsoft Windows and Visual Studio related system information.

    Parameters
    ----------
    registry_info: RegistryInfo
        "RegistryInfo" instance.
    vc_ver: float
        Required Microsoft Visual C++ version.
    """

    # Variables and properties in this class use originals CamelCase variables
    # names from Microsoft source files for more easy comparison.
    WinDir = environ.get('WinDir', '')
    ProgramFiles = environ.get('ProgramFiles', '')
    ProgramFilesx86 = environ.get('ProgramFiles(x86)', ProgramFiles)

    def __init__(self, registry_info, vc_ver=None) -> None:
        self.ri = registry_info
        self.pi = self.ri.pi

        self.known_vs_paths = self.find_programdata_vs_vers()

        # Except for VS15+, VC version is aligned with VS version
        self.vs_ver = self.vc_ver = vc_ver or self._find_latest_available_vs_ver()

    def _find_latest_available_vs_ver(self):
        """
        Find the latest VC version

        Return
        ------
        float
            version
        """
        reg_vc_vers = self.find_reg_vs_vers()

        if not (reg_vc_vers or self.known_vs_paths):
            raise distutils.errors.DistutilsPlatformError(
                'No Microsoft Visual C++ version found'
            )

        vc_vers = set(reg_vc_vers)
        vc_vers.update(self.known_vs_paths)
        return sorted(vc_vers)[-1]

    def find_reg_vs_vers(self):
        """
        Find Microsoft Visual Studio versions available in registry.

        Return
        ------
        list of float
            Versions
        """
        ms = self.ri.microsoft
        vckeys = (self.ri.vc, self.ri.vc_for_python, self.ri.vs)
        vs_vers = []
        for hkey, key in itertools.product(self.ri.HKEYS, vckeys):
            try:
                bkey = winreg.OpenKey(hkey, ms(key), 0, winreg.KEY_READ)
            except OSError:
                continue
            with bkey:
                subkeys, values, _ = winreg.QueryInfoKey(bkey)
                for i in range(values):
                    with contextlib.suppress(ValueError):
                        ver = float(winreg.EnumValue(bkey, i)[0])
                        if ver not in vs_vers:
                            vs_vers.append(ver)
                for i in range(subkeys):
                    with contextlib.suppress(ValueError):
                        ver = float(winreg.EnumKey(bkey, i))
                        if ver not in vs_vers:
                            vs_vers.append(ver)
        return sorted(vs_vers)

    def find_programdata_vs_vers(self) -> dict[float, str]:
        r"""
        Find Visual studio 2017+ versions from information in
        "C:\ProgramData\Microsoft\VisualStudio\Packages\_Instances".

        Return
        ------
        dict
            float version as key, path as value.
        """
        vs_versions: dict[float, str] = {}
        instances_dir = r'C:\ProgramData\Microsoft\VisualStudio\Packages\_Instances'

        try:
            hashed_names = os.listdir(instances_dir)

        except OSError:
            # Directory not exists with all Visual Studio versions
            return vs_versions

        for name in hashed_names:
            try:
                # Get VS installation path from "state.json" file
                state_path = os.path.join(instances_dir, name, 'state.json')
                with open(state_path, 'rt', encoding='utf-8') as state_file:
                    state = json.load(state_file)
                vs_path = state['installationPath']

                # Raises OSError if this VS installation does not contain VC
                os.listdir(os.path.join(vs_path, r'VC\Tools\MSVC'))

                # Store version and path
                vs_versions[self._as_float_version(state['installationVersion'])] = (
                    vs_path
                )

            except (OSError, KeyError):
                # Skip if "state.json" file is missing or bad format
                continue

        return vs_versions

    @staticmethod
    def _as_float_version(version):
        """
        Return a string version as a simplified float version (major.minor)

        Parameters
        ----------
        version: str
            Version.

        Return
        ------
        float
            version
        """
        return float('.'.join(version.split('.')[:2]))

    @property
    def VSInstallDir(self):
        """
        Microsoft Visual Studio directory.

        Return
        ------
        str
            path
        """
        # Default path
        default = os.path.join(
            self.ProgramFilesx86, f'Microsoft Visual Studio {self.vs_ver:0.1f}'
        )

        # Try to get path from registry, if fail use default path
        return self.ri.lookup(self.ri.vs, f'{self.vs_ver:0.1f}') or default

    @property
    def VCInstallDir(self):
        """
        Microsoft Visual C++ directory.

        Return
        ------
        str
            path
        """
        path = self._guess_vc() or self._guess_vc_legacy()

        if not os.path.isdir(path):
            msg = 'Microsoft Visual C++ directory not found'
            raise distutils.errors.DistutilsPlatformError(msg)

        return path

    def _guess_vc(self):
        """
        Locate Visual C++ for VS2017+.

        Return
        ------
        str
            path
        """
        if self.vs_ver <= 14.0:
            return ''

        try:
            # First search in known VS paths
            vs_dir = self.known_vs_paths[self.vs_ver]
        except KeyError:
            # Else, search with path from registry
            vs_dir = self.VSInstallDir

        guess_vc = os.path.join(vs_dir, r'VC\Tools\MSVC')

        # Subdir with VC exact version as name
        try:
            # Update the VC version with real one instead of VS version
            vc_ver = os.listdir(guess_vc)[-1]
            self.vc_ver = self._as_float_version(vc_ver)
            return os.path.join(guess_vc, vc_ver)
        except (OSError, IndexError):
            return ''

    def _guess_vc_legacy(self):
        """
        Locate Visual C++ for versions prior to 2017.

        Return
        ------
        str
            path
        """
        default = os.path.join(
            self.ProgramFilesx86,
            rf'Microsoft Visual Studio {self.vs_ver:0.1f}\VC',
        )

        # Try to get "VC++ for Python" path from registry as default path
        reg_path = os.path.join(self.ri.vc_for_python, f'{self.vs_ver:0.1f}')
        python_vc = self.ri.lookup(reg_path, 'installdir')
        default_vc = os.path.join(python_vc, 'VC') if python_vc else default

        # Try to get path from registry, if fail use default path
        return self.ri.lookup(self.ri.vc, f'{self.vs_ver:0.1f}') or default_vc

    @property
    def WindowsSdkVersion(self) -> tuple[LiteralString, ...]:
        """
        Microsoft Windows SDK versions for specified MSVC++ version.

        Return
        ------
        tuple of str
            versions
        """
        if self.vs_ver <= 9.0:
            return '7.0', '6.1', '6.0a'
        elif self.vs_ver == 10.0:
            return '7.1', '7.0a'
        elif self.vs_ver == 11.0:
            return '8.0', '8.0a'
        elif self.vs_ver == 12.0:
            return '8.1', '8.1a'
        elif self.vs_ver >= 14.0:
            return '10.0', '8.1'
        return ()

    @property
    def WindowsSdkLastVersion(self):
        """
        Microsoft Windows SDK last version.

        Return
        ------
        str
            version
        """
        return self._use_last_dir_name(os.path.join(self.WindowsSdkDir, 'lib'))

    @property
    def WindowsSdkDir(self) -> str | None:  # noqa: C901  # is too complex (12)  # FIXME
        """
        Microsoft Windows SDK directory.

        Return
        ------
        str
            path
        """
        sdkdir: str | None = ''
        for ver in self.WindowsSdkVersion:
            # Try to get it from registry
            loc = os.path.join(self.ri.windows_sdk, f'v{ver}')
            sdkdir = self.ri.lookup(loc, 'installationfolder')
            if sdkdir:
                break
        if not sdkdir or not os.path.isdir(sdkdir):
            # Try to get "VC++ for Python" version from registry
            path = os.path.join(self.ri.vc_for_python, f'{self.vc_ver:0.1f}')
            install_base = self.ri.lookup(path, 'installdir')
            if install_base:
                sdkdir = os.path.join(install_base, 'WinSDK')
        if not sdkdir or not os.path.isdir(sdkdir):
            # If fail, use default new path
            for ver in self.WindowsSdkVersion:
                intver = ver[: ver.rfind('.')]
                path = rf'Microsoft SDKs\Windows Kits\{intver}'
                d = os.path.join(self.ProgramFiles, path)
                if os.path.isdir(d):
                    sdkdir = d
        if not sdkdir or not os.path.isdir(sdkdir):
            # If fail, use default old path
            for ver in self.WindowsSdkVersion:
                path = rf'Microsoft SDKs\Windows\v{ver}'
                d = os.path.join(self.ProgramFiles, path)
                if os.path.isdir(d):
                    sdkdir = d
        if not sdkdir:
            # If fail, use Platform SDK
            sdkdir = os.path.join(self.VCInstallDir, 'PlatformSDK')
        return sdkdir

    @property
    def WindowsSDKExecutablePath(self):
        """
        Microsoft Windows SDK executable directory.

        Return
        ------
        str
            path
        """
        # Find WinSDK NetFx Tools registry dir name
        if self.vs_ver <= 11.0:
            netfxver = 35
            arch = ''
        else:
            netfxver = 40
            hidex86 = True if self.vs_ver <= 12.0 else False
            arch = self.pi.current_dir(x64=True, hidex86=hidex86).replace('\\', '-')
        fx = f'WinSDK-NetFx{netfxver}Tools{arch}'

        # list all possibles registry paths
        regpaths = []
        if self.vs_ver >= 14.0:
            for ver in self.NetFxSdkVersion:
                regpaths += [os.path.join(self.ri.netfx_sdk, ver, fx)]

        for ver in self.WindowsSdkVersion:
            regpaths += [os.path.join(self.ri.windows_sdk, f'v{ver}A', fx)]

        # Return installation folder from the more recent path
        for path in regpaths:
            execpath = self.ri.lookup(path, 'installationfolder')
            if execpath:
                return execpath

        return None

    @property
    def FSharpInstallDir(self):
        """
        Microsoft Visual F# directory.

        Return
        ------
        str
            path
        """
        path = os.path.join(self.ri.visualstudio, rf'{self.vs_ver:0.1f}\Setup\F#')
        return self.ri.lookup(path, 'productdir') or ''

    @property
    def UniversalCRTSdkDir(self):
        """
        Microsoft Universal CRT SDK directory.

        Return
        ------
        str
            path
        """
        # Set Kit Roots versions for specified MSVC++ version
        vers = ('10', '81') if self.vs_ver >= 14.0 else ()

        # Find path of the more recent Kit
        for ver in vers:
            sdkdir = self.ri.lookup(self.ri.windows_kits_roots, f'kitsroot{ver}')
            if sdkdir:
                return sdkdir or ''

        return None

    @property
    def UniversalCRTSdkLastVersion(self):
        """
        Microsoft Universal C Runtime SDK last version.

        Return
        ------
        str
            version
        """
        return self._use_last_dir_name(os.path.join(self.UniversalCRTSdkDir, 'lib'))

    @property
    def NetFxSdkVersion(self):
        """
        Microsoft .NET Framework SDK versions.

        Return
        ------
        tuple of str
            versions
        """
        # Set FxSdk versions for specified VS version
        return (
            ('4.7.2', '4.7.1', '4.7', '4.6.2', '4.6.1', '4.6', '4.5.2', '4.5.1', '4.5')
            if self.vs_ver >= 14.0
            else ()
        )

    @property
    def NetFxSdkDir(self):
        """
        Microsoft .NET Framework SDK directory.

        Return
        ------
        str
            path
        """
        sdkdir = ''
        for ver in self.NetFxSdkVersion:
            loc = os.path.join(self.ri.netfx_sdk, ver)
            sdkdir = self.ri.lookup(loc, 'kitsinstallationfolder')
            if sdkdir:
                break
        return sdkdir

    @property
    def FrameworkDir32(self):
        """
        Microsoft .NET Framework 32bit directory.

        Return
        ------
        str
            path
        """
        # Default path
        guess_fw = os.path.join(self.WinDir, r'Microsoft.NET\Framework')

        # Try to get path from registry, if fail use default path
        return self.ri.lookup(self.ri.vc, 'frameworkdir32') or guess_fw

    @property
    def FrameworkDir64(self):
        """
        Microsoft .NET Framework 64bit directory.

        Return
        ------
        str
            path
        """
        # Default path
        guess_fw = os.path.join(self.WinDir, r'Microsoft.NET\Framework64')

        # Try to get path from registry, if fail use default path
        return self.ri.lookup(self.ri.vc, 'frameworkdir64') or guess_fw

    @property
    def FrameworkVersion32(self) -> tuple[str, ...]:
        """
        Microsoft .NET Framework 32bit versions.

        Return
        ------
        tuple of str
            versions
        """
        return self._find_dot_net_versions(32)

    @property
    def FrameworkVersion64(self) -> tuple[str, ...]:
        """
        Microsoft .NET Framework 64bit versions.

        Return
        ------
        tuple of str
            versions
        """
        return self._find_dot_net_versions(64)

    def _find_dot_net_versions(self, bits) -> tuple[str, ...]:
        """
        Find Microsoft .NET Framework versions.

        Parameters
        ----------
        bits: int
            Platform number of bits: 32 or 64.

        Return
        ------
        tuple of str
            versions
        """
        # Find actual .NET version in registry
        reg_ver = self.ri.lookup(self.ri.vc, f'frameworkver{bits}')
        dot_net_dir = getattr(self, f'FrameworkDir{bits}')
        ver = reg_ver or self._use_last_dir_name(dot_net_dir, 'v') or ''

        # Set .NET versions for specified MSVC++ version
        if self.vs_ver >= 12.0:
            return ver, 'v4.0'
        elif self.vs_ver >= 10.0:
            return 'v4.0.30319' if ver.lower()[:2] != 'v4' else ver, 'v3.5'
        elif self.vs_ver == 9.0:
            return 'v3.5', 'v2.0.50727'
        elif self.vs_ver == 8.0:
            return 'v3.0', 'v2.0.50727'
        return ()

    @staticmethod
    def _use_last_dir_name(path, prefix=''):
        """
        Return name of the last dir in path or '' if no dir found.

        Parameters
        ----------
        path: str
            Use dirs in this path
        prefix: str
            Use only dirs starting by this prefix

        Return
        ------
        str
            name
        """
        matching_dirs = (
            dir_name
            for dir_name in reversed(os.listdir(path))
            if os.path.isdir(os.path.join(path, dir_name))
            and dir_name.startswith(prefix)
        )
        return next(matching_dirs, None) or ''


class _EnvironmentDict(TypedDict):
    include: str
    lib: str
    libpath: str
    path: str
    py_vcruntime_redist: NotRequired[str | None]


class EnvironmentInfo:
    """
    Return environment variables for specified Microsoft Visual C++ version
    and platform : Lib, Include, Path and libpath.

    This function is compatible with Microsoft Visual C++ 9.0 to 14.X.

    Script created by analysing Microsoft environment configuration files like
    "vcvars[...].bat", "SetEnv.Cmd", "vcbuildtools.bat", ...

    Parameters
    ----------
    arch: str
        Target architecture.
    vc_ver: float
        Required Microsoft Visual C++ version. If not set, autodetect the last
        version.
    vc_min_ver: float
        Minimum Microsoft Visual C++ version.
    """

    # Variables and properties in this class use originals CamelCase variables
    # names from Microsoft source files for more easy comparison.

    def __init__(self, arch, vc_ver=None, vc_min_ver=0) -> None:
        self.pi = PlatformInfo(arch)
        self.ri = RegistryInfo(self.pi)
        self.si = SystemInfo(self.ri, vc_ver)

        if self.vc_ver < vc_min_ver:
            err = 'No suitable Microsoft Visual C++ version found'
            raise distutils.errors.DistutilsPlatformError(err)

    @property
    def vs_ver(self):
        """
        Microsoft Visual Studio.

        Return
        ------
        float
            version
        """
        return self.si.vs_ver

    @property
    def vc_ver(self):
        """
        Microsoft Visual C++ version.

        Return
        ------
        float
            version
        """
        return self.si.vc_ver

    @property
    def VSTools(self):
        """
        Microsoft Visual Studio Tools.

        Return
        ------
        list of str
            paths
        """
        paths = [r'Common7\IDE', r'Common7\Tools']

        if self.vs_ver >= 14.0:
            arch_subdir = self.pi.current_dir(hidex86=True, x64=True)
            paths += [r'Common7\IDE\CommonExtensions\Microsoft\TestWindow']
            paths += [r'Team Tools\Performance Tools']
            paths += [rf'Team Tools\Performance Tools{arch_subdir}']

        return [os.path.join(self.si.VSInstallDir, path) for path in paths]

    @property
    def VCIncludes(self):
        """
        Microsoft Visual C++ & Microsoft Foundation Class Includes.

        Return
        ------
        list of str
            paths
        """
        return [
            os.path.join(self.si.VCInstallDir, 'Include'),
            os.path.join(self.si.VCInstallDir, r'ATLMFC\Include'),
        ]

    @property
    def VCLibraries(self):
        """
        Microsoft Visual C++ & Microsoft Foundation Class Libraries.

        Return
        ------
        list of str
            paths
        """
        if self.vs_ver >= 15.0:
            arch_subdir = self.pi.target_dir(x64=True)
        else:
            arch_subdir = self.pi.target_dir(hidex86=True)
        paths = [f'Lib{arch_subdir}', rf'ATLMFC\Lib{arch_subdir}']

        if self.vs_ver >= 14.0:
            paths += [rf'Lib\store{arch_subdir}']

        return [os.path.join(self.si.VCInstallDir, path) for path in paths]

    @property
    def VCStoreRefs(self):
        """
        Microsoft Visual C++ store references Libraries.

        Return
        ------
        list of str
            paths
        """
        if self.vs_ver < 14.0:
            return []
        return [os.path.join(self.si.VCInstallDir, r'Lib\store\references')]

    @property
    def VCTools(self):
        """
        Microsoft Visual C++ Tools.

        Return
        ------
        list of str
            paths

        When host CPU is ARM, the tools should be found for ARM.

        >>> getfixture('windows_only')
        >>> mp = getfixture('monkeypatch')
        >>> mp.setattr(PlatformInfo, 'current_cpu', 'arm64')
        >>> ei = EnvironmentInfo(arch='irrelevant')
        >>> paths = ei.VCTools
        >>> any('HostARM64' in path for path in paths)
        True
        """
        si = self.si
        tools = [os.path.join(si.VCInstallDir, 'VCPackages')]

        forcex86 = True if self.vs_ver <= 10.0 else False
        arch_subdir = self.pi.cross_dir(forcex86)
        if arch_subdir:
            tools += [os.path.join(si.VCInstallDir, f'Bin{arch_subdir}')]

        if self.vs_ver == 14.0:
            path = f'Bin{self.pi.current_dir(hidex86=True)}'
            tools += [os.path.join(si.VCInstallDir, path)]

        elif self.vs_ver >= 15.0:
            host_id = self.pi.current_cpu.replace('amd64', 'x64').upper()
            host_dir = os.path.join('bin', f'Host{host_id}%s')
            tools += [
                os.path.join(si.VCInstallDir, host_dir % self.pi.target_dir(x64=True))
            ]

            if self.pi.current_cpu != self.pi.target_cpu:
                tools += [
                    os.path.join(
                        si.VCInstallDir, host_dir % self.pi.current_dir(x64=True)
                    )
                ]

        else:
            tools += [os.path.join(si.VCInstallDir, 'Bin')]

        return tools

    @property
    def OSLibraries(self):
        """
        Microsoft Windows SDK Libraries.

        Return
        ------
        list of str
            paths
        """
        if self.vs_ver <= 10.0:
            arch_subdir = self.pi.target_dir(hidex86=True, x64=True)
            return [os.path.join(self.si.WindowsSdkDir, f'Lib{arch_subdir}')]

        else:
            arch_subdir = self.pi.target_dir(x64=True)
            lib = os.path.join(self.si.WindowsSdkDir, 'lib')
            libver = self._sdk_subdir
            return [os.path.join(lib, f'{libver}um{arch_subdir}')]

    @property
    def OSIncludes(self):
        """
        Microsoft Windows SDK Include.

        Return
        ------
        list of str
            paths
        """
        include = os.path.join(self.si.WindowsSdkDir, 'include')

        if self.vs_ver <= 10.0:
            return [include, os.path.join(include, 'gl')]

        else:
            if self.vs_ver >= 14.0:
                sdkver = self._sdk_subdir
            else:
                sdkver = ''
            return [
                os.path.join(include, f'{sdkver}shared'),
                os.path.join(include, f'{sdkver}um'),
                os.path.join(include, f'{sdkver}winrt'),
            ]

    @property
    def OSLibpath(self):
        """
        Microsoft Windows SDK Libraries Paths.

        Return
        ------
        list of str
            paths
        """
        ref = os.path.join(self.si.WindowsSdkDir, 'References')
        libpath = []

        if self.vs_ver <= 9.0:
            libpath += self.OSLibraries

        if self.vs_ver >= 11.0:
            libpath += [os.path.join(ref, r'CommonConfiguration\Neutral')]

        if self.vs_ver >= 14.0:
            libpath += [
                ref,
                os.path.join(self.si.WindowsSdkDir, 'UnionMetadata'),
                os.path.join(ref, 'Windows.Foundation.UniversalApiContract', '1.0.0.0'),
                os.path.join(ref, 'Windows.Foundation.FoundationContract', '1.0.0.0'),
                os.path.join(
                    ref, 'Windows.Networking.Connectivity.WwanContract', '1.0.0.0'
                ),
                os.path.join(
                    self.si.WindowsSdkDir,
                    'ExtensionSDKs',
                    'Microsoft.VCLibs',
                    f'{self.vs_ver:0.1f}',
                    'References',
                    'CommonConfiguration',
                    'neutral',
                ),
            ]
        return libpath

    @property
    def SdkTools(self):
        """
        Microsoft Windows SDK Tools.

        Return
        ------
        list of str
            paths
        """
        return list(self._sdk_tools())

    def _sdk_tools(self):
        """
        Microsoft Windows SDK Tools paths generator.

        Return
        ------
        generator of str
            paths
        """
        if self.vs_ver < 15.0:
            bin_dir = 'Bin' if self.vs_ver <= 11.0 else r'Bin\x86'
            yield os.path.join(self.si.WindowsSdkDir, bin_dir)

        if not self.pi.current_is_x86():
            arch_subdir = self.pi.current_dir(x64=True)
            path = f'Bin{arch_subdir}'
            yield os.path.join(self.si.WindowsSdkDir, path)

        if self.vs_ver in (10.0, 11.0):
            if self.pi.target_is_x86():
                arch_subdir = ''
            else:
                arch_subdir = self.pi.current_dir(hidex86=True, x64=True)
            path = rf'Bin\NETFX 4.0 Tools{arch_subdir}'
            yield os.path.join(self.si.WindowsSdkDir, path)

        elif self.vs_ver >= 15.0:
            path = os.path.join(self.si.WindowsSdkDir, 'Bin')
            arch_subdir = self.pi.current_dir(x64=True)
            sdkver = self.si.WindowsSdkLastVersion
            yield os.path.join(path, f'{sdkver}{arch_subdir}')

        if self.si.WindowsSDKExecutablePath:
            yield self.si.WindowsSDKExecutablePath

    @property
    def _sdk_subdir(self):
        """
        Microsoft Windows SDK version subdir.

        Return
        ------
        str
            subdir
        """
        ucrtver = self.si.WindowsSdkLastVersion
        return (f'{ucrtver}\\') if ucrtver else ''

    @property
    def SdkSetup(self):
        """
        Microsoft Windows SDK Setup.

        Return
        ------
        list of str
            paths
        """
        if self.vs_ver > 9.0:
            return []

        return [os.path.join(self.si.WindowsSdkDir, 'Setup')]

    @property
    def FxTools(self):
        """
        Microsoft .NET Framework Tools.

        Return
        ------
        list of str
            paths
        """
        pi = self.pi
        si = self.si

        if self.vs_ver <= 10.0:
            include32 = True
            include64 = not pi.target_is_x86() and not pi.current_is_x86()
        else:
            include32 = pi.target_is_x86() or pi.current_is_x86()
            include64 = pi.current_cpu == 'amd64' or pi.target_cpu == 'amd64'

        tools = []
        if include32:
            tools += [
                os.path.join(si.FrameworkDir32, ver) for ver in si.FrameworkVersion32
            ]
        if include64:
            tools += [
                os.path.join(si.FrameworkDir64, ver) for ver in si.FrameworkVersion64
            ]
        return tools

    @property
    def NetFxSDKLibraries(self):
        """
        Microsoft .Net Framework SDK Libraries.

        Return
        ------
        list of str
            paths
        """
        if self.vs_ver < 14.0 or not self.si.NetFxSdkDir:
            return []

        arch_subdir = self.pi.target_dir(x64=True)
        return [os.path.join(self.si.NetFxSdkDir, rf'lib\um{arch_subdir}')]

    @property
    def NetFxSDKIncludes(self):
        """
        Microsoft .Net Framework SDK Includes.

        Return
        ------
        list of str
            paths
        """
        if self.vs_ver < 14.0 or not self.si.NetFxSdkDir:
            return []

        return [os.path.join(self.si.NetFxSdkDir, r'include\um')]

    @property
    def VsTDb(self):
        """
        Microsoft Visual Studio Team System Database.

        Return
        ------
        list of str
            paths
        """
        return [os.path.join(self.si.VSInstallDir, r'VSTSDB\Deploy')]

    @property
    def MSBuild(self):
        """
        Microsoft Build Engine.

        Return
        ------
        list of str
            paths
        """
        if self.vs_ver < 12.0:
            return []
        elif self.vs_ver < 15.0:
            base_path = self.si.ProgramFilesx86
            arch_subdir = self.pi.current_dir(hidex86=True)
        else:
            base_path = self.si.VSInstallDir
            arch_subdir = ''

        path = rf'MSBuild\{self.vs_ver:0.1f}\bin{arch_subdir}'
        build = [os.path.join(base_path, path)]

        if self.vs_ver >= 15.0:
            # Add Roslyn C# & Visual Basic Compiler
            build += [os.path.join(base_path, path, 'Roslyn')]

        return build

    @property
    def HTMLHelpWorkshop(self):
        """
        Microsoft HTML Help Workshop.

        Return
        ------
        list of str
            paths
        """
        if self.vs_ver < 11.0:
            return []

        return [os.path.join(self.si.ProgramFilesx86, 'HTML Help Workshop')]

    @property
    def UCRTLibraries(self):
        """
        Microsoft Universal C Runtime SDK Libraries.

        Return
        ------
        list of str
            paths
        """
        if self.vs_ver < 14.0:
            return []

        arch_subdir = self.pi.target_dir(x64=True)
        lib = os.path.join(self.si.UniversalCRTSdkDir, 'lib')
        ucrtver = self._ucrt_subdir
        return [os.path.join(lib, f'{ucrtver}ucrt{arch_subdir}')]

    @property
    def UCRTIncludes(self):
        """
        Microsoft Universal C Runtime SDK Include.

        Return
        ------
        list of str
            paths
        """
        if self.vs_ver < 14.0:
            return []

        include = os.path.join(self.si.UniversalCRTSdkDir, 'include')
        return [os.path.join(include, f'{self._ucrt_subdir}ucrt')]

    @property
    def _ucrt_subdir(self):
        """
        Microsoft Universal C Runtime SDK version subdir.

        Return
        ------
        str
            subdir
        """
        ucrtver = self.si.UniversalCRTSdkLastVersion
        return (f'{ucrtver}\\') if ucrtver else ''

    @property
    def FSharp(self):
        """
        Microsoft Visual F#.

        Return
        ------
        list of str
            paths
        """
        if 11.0 > self.vs_ver > 12.0:
            return []

        return [self.si.FSharpInstallDir]

    @property
    def VCRuntimeRedist(self) -> str | None:
        """
        Microsoft Visual C++ runtime redistributable dll.

        Returns the first suitable path found or None.
        """
        vcruntime = f'vcruntime{self.vc_ver}0.dll'
        arch_subdir = self.pi.target_dir(x64=True).strip('\\')

        # Installation prefixes candidates
        prefixes = []
        tools_path = self.si.VCInstallDir
        redist_path = os.path.dirname(tools_path.replace(r'\Tools', r'\Redist'))
        if os.path.isdir(redist_path):
            # Redist version may not be exactly the same as tools
            redist_path = os.path.join(redist_path, os.listdir(redist_path)[-1])
            prefixes += [redist_path, os.path.join(redist_path, 'onecore')]

        prefixes += [os.path.join(tools_path, 'redist')]  # VS14 legacy path

        # CRT directory
        crt_dirs = (
            f'Microsoft.VC{self.vc_ver * 10}.CRT',
            # Sometime store in directory with VS version instead of VC
            f'Microsoft.VC{int(self.vs_ver) * 10}.CRT',
        )

        # vcruntime path
        candidate_paths = (
            os.path.join(prefix, arch_subdir, crt_dir, vcruntime)
            for (prefix, crt_dir) in itertools.product(prefixes, crt_dirs)
        )
        return next(filter(os.path.isfile, candidate_paths), None)  # type: ignore[arg-type] #python/mypy#12682

    def return_env(self, exists: bool = True) -> _EnvironmentDict:
        """
        Return environment dict.

        Parameters
        ----------
        exists: bool
            It True, only return existing paths.

        Return
        ------
        dict
            environment
        """
        env = _EnvironmentDict(
            include=self._build_paths(
                'include',
                [
                    self.VCIncludes,
                    self.OSIncludes,
                    self.UCRTIncludes,
                    self.NetFxSDKIncludes,
                ],
                exists,
            ),
            lib=self._build_paths(
                'lib',
                [
                    self.VCLibraries,
                    self.OSLibraries,
                    self.FxTools,
                    self.UCRTLibraries,
                    self.NetFxSDKLibraries,
                ],
                exists,
            ),
            libpath=self._build_paths(
                'libpath',
                [self.VCLibraries, self.FxTools, self.VCStoreRefs, self.OSLibpath],
                exists,
            ),
            path=self._build_paths(
                'path',
                [
                    self.VCTools,
                    self.VSTools,
                    self.VsTDb,
                    self.SdkTools,
                    self.SdkSetup,
                    self.FxTools,
                    self.MSBuild,
                    self.HTMLHelpWorkshop,
                    self.FSharp,
                ],
                exists,
            ),
        )
        if self.vs_ver >= 14 and self.VCRuntimeRedist:
            env['py_vcruntime_redist'] = self.VCRuntimeRedist
        return env

    def _build_paths(self, name, spec_path_lists, exists):
        """
        Given an environment variable name and specified paths,
        return a pathsep-separated string of paths containing
        unique, extant, directories from those paths and from
        the environment variable. Raise an error if no paths
        are resolved.

        Parameters
        ----------
        name: str
            Environment variable name
        spec_path_lists: list of str
            Paths
        exists: bool
            It True, only return existing paths.

        Return
        ------
        str
            Pathsep-separated paths
        """
        # flatten spec_path_lists
        spec_paths = itertools.chain.from_iterable(spec_path_lists)
        env_paths = environ.get(name, '').split(os.pathsep)
        paths = itertools.chain(spec_paths, env_paths)
        extant_paths = list(filter(os.path.isdir, paths)) if exists else paths
        if not extant_paths:
            msg = f"{name.upper()} environment variable is empty"
            raise distutils.errors.DistutilsPlatformError(msg)
        unique_paths = unique_everseen(extant_paths)
        return os.pathsep.join(unique_paths)