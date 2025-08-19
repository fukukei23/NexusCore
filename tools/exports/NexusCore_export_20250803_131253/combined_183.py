
# === NexusCore/tools\exports\export_20250803_114325\combined_210.py ===

# === NexusCore/openenv\Lib\site-packages\pygments\lexers\idl.py ===
"""
    pygments.lexers.idl
    ~~~~~~~~~~~~~~~~~~~

    Lexers for IDL.

    :copyright: Copyright 2006-2025 by the Pygments team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

import re

from pygments.lexer import RegexLexer, words, bygroups
from pygments.token import Text, Comment, Operator, Keyword, Name, Number, \
    String, Whitespace

__all__ = ['IDLLexer']


class IDLLexer(RegexLexer):
    """
    Pygments Lexer for IDL (Interactive Data Language).
    """
    name = 'IDL'
    url = 'https://www.l3harrisgeospatial.com/Software-Technology/IDL'
    aliases = ['idl']
    filenames = ['*.pro']
    mimetypes = ['text/idl']
    version_added = '1.6'

    flags = re.IGNORECASE | re.MULTILINE

    _RESERVED = (
        'and', 'begin', 'break', 'case', 'common', 'compile_opt',
        'continue', 'do', 'else', 'end', 'endcase', 'endelse',
        'endfor', 'endforeach', 'endif', 'endrep', 'endswitch',
        'endwhile', 'eq', 'for', 'foreach', 'forward_function',
        'function', 'ge', 'goto', 'gt', 'if', 'inherits', 'le',
        'lt', 'mod', 'ne', 'not', 'of', 'on_ioerror', 'or', 'pro',
        'repeat', 'switch', 'then', 'until', 'while', 'xor')
    """Reserved words from: http://www.exelisvis.com/docs/reswords.html"""

    _BUILTIN_LIB = (
        'abs', 'acos', 'adapt_hist_equal', 'alog', 'alog10',
        'amoeba', 'annotate', 'app_user_dir', 'app_user_dir_query',
        'arg_present', 'array_equal', 'array_indices', 'arrow',
        'ascii_template', 'asin', 'assoc', 'atan', 'axis',
        'a_correlate', 'bandpass_filter', 'bandreject_filter',
        'barplot', 'bar_plot', 'beseli', 'beselj', 'beselk',
        'besely', 'beta', 'bilinear', 'binary_template', 'bindgen',
        'binomial', 'bin_date', 'bit_ffs', 'bit_population',
        'blas_axpy', 'blk_con', 'box_cursor', 'breakpoint',
        'broyden', 'butterworth', 'bytarr', 'byte', 'byteorder',
        'bytscl', 'caldat', 'calendar', 'call_external',
        'call_function', 'call_method', 'call_procedure', 'canny',
        'catch', 'cd', r'cdf_\w*', 'ceil', 'chebyshev',
        'check_math',
        'chisqr_cvf', 'chisqr_pdf', 'choldc', 'cholsol', 'cindgen',
        'cir_3pnt', 'close', 'cluster', 'cluster_tree', 'clust_wts',
        'cmyk_convert', 'colorbar', 'colorize_sample',
        'colormap_applicable', 'colormap_gradient',
        'colormap_rotation', 'colortable', 'color_convert',
        'color_exchange', 'color_quan', 'color_range_map', 'comfit',
        'command_line_args', 'complex', 'complexarr', 'complexround',
        'compute_mesh_normals', 'cond', 'congrid', 'conj',
        'constrained_min', 'contour', 'convert_coord', 'convol',
        'convol_fft', 'coord2to3', 'copy_lun', 'correlate', 'cos',
        'cosh', 'cpu', 'cramer', 'create_cursor', 'create_struct',
        'create_view', 'crossp', 'crvlength', 'cti_test',
        'ct_luminance', 'cursor', 'curvefit', 'cvttobm', 'cv_coord',
        'cw_animate', 'cw_animate_getp', 'cw_animate_load',
        'cw_animate_run', 'cw_arcball', 'cw_bgroup', 'cw_clr_index',
        'cw_colorsel', 'cw_defroi', 'cw_field', 'cw_filesel',
        'cw_form', 'cw_fslider', 'cw_light_editor',
        'cw_light_editor_get', 'cw_light_editor_set', 'cw_orient',
        'cw_palette_editor', 'cw_palette_editor_get',
        'cw_palette_editor_set', 'cw_pdmenu', 'cw_rgbslider',
        'cw_tmpl', 'cw_zoom', 'c_correlate', 'dblarr', 'db_exists',
        'dcindgen', 'dcomplex', 'dcomplexarr', 'define_key',
        'define_msgblk', 'define_msgblk_from_file', 'defroi',
        'defsysv', 'delvar', 'dendrogram', 'dendro_plot', 'deriv',
        'derivsig', 'determ', 'device', 'dfpmin', 'diag_matrix',
        'dialog_dbconnect', 'dialog_message', 'dialog_pickfile',
        'dialog_printersetup', 'dialog_printjob',
        'dialog_read_image', 'dialog_write_image', 'digital_filter',
        'dilate', 'dindgen', 'dissolve', 'dist', 'distance_measure',
        'dlm_load', 'dlm_register', 'doc_library', 'double',
        'draw_roi', 'edge_dog', 'efont', 'eigenql', 'eigenvec',
        'ellipse', 'elmhes', 'emboss', 'empty', 'enable_sysrtn',
        'eof', r'eos_\w*', 'erase', 'erf', 'erfc', 'erfcx',
        'erode', 'errorplot', 'errplot', 'estimator_filter',
        'execute', 'exit', 'exp', 'expand', 'expand_path', 'expint',
        'extrac', 'extract_slice', 'factorial', 'fft', 'filepath',
        'file_basename', 'file_chmod', 'file_copy', 'file_delete',
        'file_dirname', 'file_expand_path', 'file_info',
        'file_lines', 'file_link', 'file_mkdir', 'file_move',
        'file_poll_input', 'file_readlink', 'file_same',
        'file_search', 'file_test', 'file_which', 'findgen',
        'finite', 'fix', 'flick', 'float', 'floor', 'flow3',
        'fltarr', 'flush', 'format_axis_values', 'free_lun',
        'fstat', 'fulstr', 'funct', 'fv_test', 'fx_root',
        'fz_roots', 'f_cvf', 'f_pdf', 'gamma', 'gamma_ct',
        'gauss2dfit', 'gaussfit', 'gaussian_function', 'gaussint',
        'gauss_cvf', 'gauss_pdf', 'gauss_smooth', 'getenv',
        'getwindows', 'get_drive_list', 'get_dxf_objects',
        'get_kbrd', 'get_login_info', 'get_lun', 'get_screen_size',
        'greg2jul', r'grib_\w*', 'grid3', 'griddata',
        'grid_input', 'grid_tps', 'gs_iter',
        r'h5[adfgirst]_\w*', 'h5_browser', 'h5_close',
        'h5_create', 'h5_get_libversion', 'h5_open', 'h5_parse',
        'hanning', 'hash', r'hdf_\w*', 'heap_free',
        'heap_gc', 'heap_nosave', 'heap_refcount', 'heap_save',
        'help', 'hilbert', 'histogram', 'hist_2d', 'hist_equal',
        'hls', 'hough', 'hqr', 'hsv', 'h_eq_ct', 'h_eq_int',
        'i18n_multibytetoutf8', 'i18n_multibytetowidechar',
        'i18n_utf8tomultibyte', 'i18n_widechartomultibyte',
        'ibeta', 'icontour', 'iconvertcoord', 'idelete', 'identity',
        'idlexbr_assistant', 'idlitsys_createtool', 'idl_base64',
        'idl_validname', 'iellipse', 'igamma', 'igetcurrent',
        'igetdata', 'igetid', 'igetproperty', 'iimage', 'image',
        'image_cont', 'image_statistics', 'imaginary', 'imap',
        'indgen', 'intarr', 'interpol', 'interpolate',
        'interval_volume', 'int_2d', 'int_3d', 'int_tabulated',
        'invert', 'ioctl', 'iopen', 'iplot', 'ipolygon',
        'ipolyline', 'iputdata', 'iregister', 'ireset', 'iresolve',
        'irotate', 'ir_filter', 'isa', 'isave', 'iscale',
        'isetcurrent', 'isetproperty', 'ishft', 'isocontour',
        'isosurface', 'isurface', 'itext', 'itranslate', 'ivector',
        'ivolume', 'izoom', 'i_beta', 'journal', 'json_parse',
        'json_serialize', 'jul2greg', 'julday', 'keyword_set',
        'krig2d', 'kurtosis', 'kw_test', 'l64indgen', 'label_date',
        'label_region', 'ladfit', 'laguerre', 'laplacian',
        'la_choldc', 'la_cholmprove', 'la_cholsol', 'la_determ',
        'la_eigenproblem', 'la_eigenql', 'la_eigenvec', 'la_elmhes',
        'la_gm_linear_model', 'la_hqr', 'la_invert',
        'la_least_squares', 'la_least_square_equality',
        'la_linear_equation', 'la_ludc', 'la_lumprove', 'la_lusol',
        'la_svd', 'la_tridc', 'la_trimprove', 'la_triql',
        'la_trired', 'la_trisol', 'least_squares_filter', 'leefilt',
        'legend', 'legendre', 'linbcg', 'lindgen', 'linfit',
        'linkimage', 'list', 'll_arc_distance', 'lmfit', 'lmgr',
        'lngamma', 'lnp_test', 'loadct', 'locale_get',
        'logical_and', 'logical_or', 'logical_true', 'lon64arr',
        'lonarr', 'long', 'long64', 'lsode', 'ludc', 'lumprove',
        'lusol', 'lu_complex', 'machar', 'make_array', 'make_dll',
        'make_rt', 'map', 'mapcontinents', 'mapgrid', 'map_2points',
        'map_continents', 'map_grid', 'map_image', 'map_patch',
        'map_proj_forward', 'map_proj_image', 'map_proj_info',
        'map_proj_init', 'map_proj_inverse', 'map_set',
        'matrix_multiply', 'matrix_power', 'max', 'md_test',
        'mean', 'meanabsdev', 'mean_filter', 'median', 'memory',
        'mesh_clip', 'mesh_decimate', 'mesh_issolid', 'mesh_merge',
        'mesh_numtriangles', 'mesh_obj', 'mesh_smooth',
        'mesh_surfacearea', 'mesh_validate', 'mesh_volume',
        'message', 'min', 'min_curve_surf', 'mk_html_help',
        'modifyct', 'moment', 'morph_close', 'morph_distance',
        'morph_gradient', 'morph_hitormiss', 'morph_open',
        'morph_thin', 'morph_tophat', 'multi', 'm_correlate',
        r'ncdf_\w*', 'newton', 'noise_hurl', 'noise_pick',
        'noise_scatter', 'noise_slur', 'norm', 'n_elements',
        'n_params', 'n_tags', 'objarr', 'obj_class', 'obj_destroy',
        'obj_hasmethod', 'obj_isa', 'obj_new', 'obj_valid',
        'online_help', 'on_error', 'open', 'oplot', 'oploterr',
        'parse_url', 'particle_trace', 'path_cache', 'path_sep',
        'pcomp', 'plot', 'plot3d', 'ploterr', 'plots', 'plot_3dbox',
        'plot_field', 'pnt_line', 'point_lun', 'polarplot',
        'polar_contour', 'polar_surface', 'poly', 'polyfill',
        'polyfillv', 'polygon', 'polyline', 'polyshade', 'polywarp',
        'poly_2d', 'poly_area', 'poly_fit', 'popd', 'powell',
        'pref_commit', 'pref_get', 'pref_set', 'prewitt', 'primes',
        'print', 'printd', 'product', 'profile', 'profiler',
        'profiles', 'project_vol', 'psafm', 'pseudo',
        'ps_show_fonts', 'ptrarr', 'ptr_free', 'ptr_new',
        'ptr_valid', 'pushd', 'p_correlate', 'qgrid3', 'qhull',
        'qromb', 'qromo', 'qsimp', 'query_ascii', 'query_bmp',
        'query_csv', 'query_dicom', 'query_gif', 'query_image',
        'query_jpeg', 'query_jpeg2000', 'query_mrsid', 'query_pict',
        'query_png', 'query_ppm', 'query_srf', 'query_tiff',
        'query_wav', 'radon', 'randomn', 'randomu', 'ranks',
        'rdpix', 'read', 'reads', 'readu', 'read_ascii',
        'read_binary', 'read_bmp', 'read_csv', 'read_dicom',
        'read_gif', 'read_image', 'read_interfile', 'read_jpeg',
        'read_jpeg2000', 'read_mrsid', 'read_pict', 'read_png',
        'read_ppm', 'read_spr', 'read_srf', 'read_sylk',
        'read_tiff', 'read_wav', 'read_wave', 'read_x11_bitmap',
        'read_xwd', 'real_part', 'rebin', 'recall_commands',
        'recon3', 'reduce_colors', 'reform', 'region_grow',
        'register_cursor', 'regress', 'replicate',
        'replicate_inplace', 'resolve_all', 'resolve_routine',
        'restore', 'retall', 'return', 'reverse', 'rk4', 'roberts',
        'rot', 'rotate', 'round', 'routine_filepath',
        'routine_info', 'rs_test', 'r_correlate', 'r_test',
        'save', 'savgol', 'scale3', 'scale3d', 'scope_level',
        'scope_traceback', 'scope_varfetch', 'scope_varname',
        'search2d', 'search3d', 'sem_create', 'sem_delete',
        'sem_lock', 'sem_release', 'setenv', 'set_plot',
        'set_shading', 'sfit', 'shade_surf', 'shade_surf_irr',
        'shade_volume', 'shift', 'shift_diff', 'shmdebug', 'shmmap',
        'shmunmap', 'shmvar', 'show3', 'showfont', 'simplex', 'sin',
        'sindgen', 'sinh', 'size', 'skewness', 'skip_lun',
        'slicer3', 'slide_image', 'smooth', 'sobel', 'socket',
        'sort', 'spawn', 'spher_harm', 'sph_4pnt', 'sph_scat',
        'spline', 'spline_p', 'spl_init', 'spl_interp', 'sprsab',
        'sprsax', 'sprsin', 'sprstp', 'sqrt', 'standardize',
        'stddev', 'stop', 'strarr', 'strcmp', 'strcompress',
        'streamline', 'stregex', 'stretch', 'string', 'strjoin',
        'strlen', 'strlowcase', 'strmatch', 'strmessage', 'strmid',
        'strpos', 'strput', 'strsplit', 'strtrim', 'struct_assign',
        'struct_hide', 'strupcase', 'surface', 'surfr', 'svdc',
        'svdfit', 'svsol', 'swap_endian', 'swap_endian_inplace',
        'symbol', 'systime', 's_test', 't3d', 'tag_names', 'tan',
        'tanh', 'tek_color', 'temporary', 'tetra_clip',
        'tetra_surface', 'tetra_volume', 'text', 'thin', 'threed',
        'timegen', 'time_test2', 'tm_test', 'total', 'trace',
        'transpose', 'triangulate', 'trigrid', 'triql', 'trired',
        'trisol', 'tri_surf', 'truncate_lun', 'ts_coef', 'ts_diff',
        'ts_fcast', 'ts_smooth', 'tv', 'tvcrs', 'tvlct', 'tvrd',
        'tvscl', 'typename', 't_cvt', 't_pdf', 'uindgen', 'uint',
        'uintarr', 'ul64indgen', 'ulindgen', 'ulon64arr', 'ulonarr',
        'ulong', 'ulong64', 'uniq', 'unsharp_mask', 'usersym',
        'value_locate', 'variance', 'vector', 'vector_field', 'vel',
        'velovect', 'vert_t3d', 'voigt', 'voronoi', 'voxel_proj',
        'wait', 'warp_tri', 'watershed', 'wdelete', 'wf_draw',
        'where', 'widget_base', 'widget_button', 'widget_combobox',
        'widget_control', 'widget_displaycontextmen', 'widget_draw',
        'widget_droplist', 'widget_event', 'widget_info',
        'widget_label', 'widget_list', 'widget_propertysheet',
        'widget_slider', 'widget_tab', 'widget_table',
        'widget_text', 'widget_tree', 'widget_tree_move',
        'widget_window', 'wiener_filter', 'window', 'writeu',
        'write_bmp', 'write_csv', 'write_gif', 'write_image',
        'write_jpeg', 'write_jpeg2000', 'write_nrif', 'write_pict',
        'write_png', 'write_ppm', 'write_spr', 'write_srf',
        'write_sylk', 'write_tiff', 'write_wav', 'write_wave',
        'wset', 'wshow', 'wtn', 'wv_applet', 'wv_cwt',
        'wv_cw_wavelet', 'wv_denoise', 'wv_dwt', 'wv_fn_coiflet',
        'wv_fn_daubechies', 'wv_fn_gaussian', 'wv_fn_haar',
        'wv_fn_morlet', 'wv_fn_paul', 'wv_fn_symlet',
        'wv_import_data', 'wv_import_wavelet', 'wv_plot3d_wps',
        'wv_plot_multires', 'wv_pwt', 'wv_tool_denoise',
        'xbm_edit', 'xdisplayfile', 'xdxf', 'xfont',
        'xinteranimate', 'xloadct', 'xmanager', 'xmng_tmpl',
        'xmtool', 'xobjview', 'xobjview_rotate',
        'xobjview_write_image', 'xpalette', 'xpcolor', 'xplot3d',
        'xregistered', 'xroi', 'xsq_test', 'xsurface', 'xvaredit',
        'xvolume', 'xvolume_rotate', 'xvolume_write_image',
        'xyouts', 'zoom', 'zoom_24')
    """Functions from: http://www.exelisvis.com/docs/routines-1.html"""

    tokens = {
        'root': [
            (r'(^\s*)(;.*?)(\n)', bygroups(Whitespace, Comment.Single,
                Whitespace)),
            (words(_RESERVED, prefix=r'\b', suffix=r'\b'), Keyword),
            (words(_BUILTIN_LIB, prefix=r'\b', suffix=r'\b'), Name.Builtin),
            (r'\+=|-=|\^=|\*=|/=|#=|##=|<=|>=|=', Operator),
            (r'\+\+|--|->|\+|-|##|#|\*|/|<|>|&&|\^|~|\|\|\?|:', Operator),
            (r'\b(mod=|lt=|le=|eq=|ne=|ge=|gt=|not=|and=|or=|xor=)', Operator),
            (r'\b(mod|lt|le|eq|ne|ge|gt|not|and|or|xor)\b', Operator),
            (r'"[^\"]*"', String.Double),
            (r"'[^\']*'", String.Single),
            (r'\b[+\-]?([0-9]*\.[0-9]+|[0-9]+\.[0-9]*)(D|E)?([+\-]?[0-9]+)?\b',
             Number.Float),
            (r'\b\'[+\-]?[0-9A-F]+\'X(U?(S?|L{1,2})|B)\b', Number.Hex),
            (r'\b\'[+\-]?[0-7]+\'O(U?(S?|L{1,2})|B)\b', Number.Oct),
            (r'\b[+\-]?[0-9]+U?L{1,2}\b', Number.Integer.Long),
            (r'\b[+\-]?[0-9]+U?S?\b', Number.Integer),
            (r'\b[+\-]?[0-9]+B\b', Number),
            (r'[ \t]+', Whitespace),
            (r'\n', Whitespace),
            (r'.', Text),
        ]
    }

    def analyse_text(text):
        """endelse seems to be unique to IDL, endswitch is rare at least."""
        result = 0

        if 'endelse' in text:
            result += 0.2
        if 'endswitch' in text:
            result += 0.01

        return result

# === NexusCore/openenv\Lib\site-packages\pyreadline3\lineeditor\history.py ===
# -*- coding: utf-8 -*-
# *****************************************************************************
#       Copyright (C) 2006-2020 Jorgen Stenarson. <jorgen.stenarson@bostream.nu>
#       Copyright (C) 2020 Bassem Girgis. <brgirgis@gmail.com>
#
#  Distributed under the terms of the BSD License.  The full license is in
#  the file COPYING, distributed as part of this software.
# *****************************************************************************

import re, operator, string, sys, os, io

from pyreadline3.logger import log
from pyreadline3.unicode_helper import ensure_str, ensure_unicode

from . import lineobj


class EscapeHistory(Exception):
    pass


class LineHistory(object):
    def __init__(self):
        self.history = []
        self._history_length = 100
        self._history_cursor = 0
        # Cannot expand unicode strings correctly on python2.4
        self.history_filename = os.path.expanduser(ensure_str("~/.history"))
        self.lastcommand = None
        self.query = ""
        self.last_search_for = ""

    def get_current_history_length(self):
        """Return the number of lines currently in the history.
        (This is different from get_history_length(), which returns
        the maximum number of lines that will be written to a history file.)"""
        value = len(self.history)
        log("get_current_history_length:%d" % value)
        return value

    def get_history_length(self):
        """Return the desired length of the history file. Negative values imply
        unlimited history file size."""
        value = self._history_length
        log("get_history_length:%d" % value)
        return value

    def get_history_item(self, index):
        """Return the current contents of history item at index (starts with index 1)."""
        item = self.history[index - 1]
        log("get_history_item: index:%d item:%r" % (index, item))
        return item.get_line_text()

    def set_history_length(self, value):
        log("set_history_length: old:%d new:%d" % (self._history_length, value))
        self._history_length = value

    def get_history_cursor(self):
        value = self._history_cursor
        log("get_history_cursor:%d" % value)
        return value

    def set_history_cursor(self, value):
        log("set_history_cursor: old:%d new:%d" % (self._history_cursor, value))
        self._history_cursor = value

    history_length = property(get_history_length, set_history_length)
    history_cursor = property(get_history_cursor, set_history_cursor)

    def clear_history(self):
        """Clear readline history."""
        self.history[:] = []
        self.history_cursor = 0

    def read_history_file(self, filename=None):
        """Load a readline history file."""
        if filename is None:
            filename = self.history_filename
        try:
            with io.open(filename, "rt", errors="replace") as fd:
                for line in fd:
                    self.add_history(lineobj.ReadLineTextBuffer(line.rstrip()))
        except IOError:
            self.history = []
            self.history_cursor = 0

    def write_history_file(self, filename=None):
        """Save a readline history file."""
        if filename is None:
            filename = self.history_filename
        with io.open(filename, "wt", errors="replace") as fp:
            fp.writelines(
                tuple(
                    line.get_line_text()+"\n"
                    for line in self.history[-self.history_length :]
                )
            )

    def add_history(self, line):
        """Append a line to the history buffer, as if it was the last line typed."""
        line = ensure_unicode(line)
        if not hasattr(line, "get_line_text"):
            line = lineobj.ReadLineTextBuffer(line)
        if not line.get_line_text():
            pass
        elif (
            len(self.history) > 0
            and self.history[-1].get_line_text() == line.get_line_text()
        ):
            pass
        else:
            self.history.append(line)
        self.history_cursor = len(self.history)

    def previous_history(self, current):  # (C-p)
        """Move back through the history list, fetching the previous command."""
        if self.history_cursor == len(self.history):
            # do not use add_history since we do not want to increment cursor
            self.history.append(current.copy())

        if self.history_cursor > 0:
            self.history_cursor -= 1
            current.set_line(self.history[self.history_cursor].get_line_text())
            current.point = lineobj.EndOfLine

    def next_history(self, current):  # (C-n)
        """Move forward through the history list, fetching the next command."""
        if self.history_cursor < len(self.history) - 1:
            self.history_cursor += 1
            current.set_line(self.history[self.history_cursor].get_line_text())

    def beginning_of_history(self):  # (M-<)
        """Move to the first line in the history."""
        self.history_cursor = 0
        if len(self.history) > 0:
            self.l_buffer = self.history[0]

    def end_of_history(self, current):  # (M->)
        """Move to the end of the input history, i.e., the line currently
        being entered."""
        self.history_cursor = len(self.history)
        current.set_line(self.history[-1].get_line_text())

    def reverse_search_history(self, searchfor, startpos=None):
        if startpos is None:
            startpos = self.history_cursor
        origpos = startpos

        result = lineobj.ReadLineTextBuffer("")

        for idx, line in list(enumerate(self.history))[startpos:0:-1]:
            if searchfor in line:
                startpos = idx
                break

        # If we get a new search without change in search term it means
        # someone pushed ctrl-r and we should find the next match
        if self.last_search_for == searchfor and startpos > 0:
            startpos -= 1
            for idx, line in list(enumerate(self.history))[startpos:0:-1]:
                if searchfor in line:
                    startpos = idx
                    break

        if self.history:
            result = self.history[startpos].get_line_text()
        else:
            result = ""
        self.history_cursor = startpos
        self.last_search_for = searchfor
        log(
            "reverse_search_history: old:%d new:%d result:%r"
            % (origpos, self.history_cursor, result)
        )
        return result

    def forward_search_history(self, searchfor, startpos=None):
        if startpos is None:
            startpos = min(
                self.history_cursor, max(0, self.get_current_history_length() - 1)
            )
        # origpos = startpos

        result = lineobj.ReadLineTextBuffer("")

        for idx, line in list(enumerate(self.history))[startpos:]:
            if searchfor in line:
                startpos = idx
                break

        # If we get a new search without change in search term it means
        # someone pushed ctrl-r and we should find the next match
        if (
            self.last_search_for == searchfor
            and startpos < self.get_current_history_length() - 1
        ):
            startpos += 1
            for idx, line in list(enumerate(self.history))[startpos:]:
                if searchfor in line:
                    startpos = idx
                    break

        if self.history:
            result = self.history[startpos].get_line_text()
        else:
            result = ""
        self.history_cursor = startpos
        self.last_search_for = searchfor
        return result

    def _search(self, direction, partial):
        try:
            if (
                self.lastcommand != self.history_search_forward
                and self.lastcommand != self.history_search_backward
            ):
                self.query = "".join(partial[0 : partial.point].get_line_text())
            hcstart = max(self.history_cursor, 0)
            hc = self.history_cursor + direction
            while (direction < 0 and hc >= 0) or (
                direction > 0 and hc < len(self.history)
            ):
                h = self.history[hc]
                if not self.query:
                    self.history_cursor = hc
                    result = lineobj.ReadLineTextBuffer(h, point=len(h.get_line_text()))
                    return result
                elif h.get_line_text().startswith(self.query) and (
                    h != partial.get_line_text()
                ):
                    self.history_cursor = hc
                    result = lineobj.ReadLineTextBuffer(h, point=partial.point)
                    return result
                hc += direction
            else:
                if len(self.history) == 0:
                    pass
                elif hc >= len(self.history) and not self.query:
                    self.history_cursor = len(self.history)
                    return lineobj.ReadLineTextBuffer("", point=0)
                elif (
                    self.history[max(min(hcstart, len(self.history) - 1), 0)]
                    .get_line_text()
                    .startswith(self.query)
                    and self.query
                ):
                    return lineobj.ReadLineTextBuffer(
                        self.history[max(min(hcstart, len(self.history) - 1), 0)],
                        point=partial.point,
                    )
                else:
                    return lineobj.ReadLineTextBuffer(partial, point=partial.point)
                return lineobj.ReadLineTextBuffer(
                    self.query, point=min(len(self.query), partial.point)
                )
        except IndexError:
            raise

    def history_search_forward(self, partial):  # ()
        """Search forward through the history for the string of characters
        between the start of the current line and the point. This is a
        non-incremental search. By default, this command is unbound."""
        return self._search(1, partial)

    def history_search_backward(self, partial):  # ()
        """Search backward through the history for the string of characters
        between the start of the current line and the point. This is a
        non-incremental search. By default, this command is unbound."""

        return self._search(-1, partial)


if __name__ == "__main__":
    q = LineHistory()
    r = LineHistory()
    s = LineHistory()
    RL = lineobj.ReadLineTextBuffer
    q.add_history(RL("aaaa"))
    q.add_history(RL("aaba"))
    q.add_history(RL("aaca"))
    q.add_history(RL("akca"))
    q.add_history(RL("bbb"))
    q.add_history(RL("ako"))
    r.add_history(RL("ako"))

# === NexusCore/openenv\Lib\site-packages\adodbapi\ado_consts.py ===
# ADO enumerated constants documented on MSDN:
# https://learn.microsoft.com/en-us/sql/ado/reference/ado-api/ado-enumerated-constants
# TODO: Update to https://learn.microsoft.com/en-us/sql/ado/reference/ado-api/ado-enumerated-constants

# IsolationLevelEnum
adXactUnspecified = -1
adXactBrowse = 0x100
adXactChaos = 0x10
adXactCursorStability = 0x1000
adXactIsolated = 0x100000
adXactReadCommitted = 0x1000
adXactReadUncommitted = 0x100
adXactRepeatableRead = 0x10000
adXactSerializable = 0x100000

# CursorLocationEnum
adUseClient = 3
adUseServer = 2

# CursorTypeEnum
adOpenDynamic = 2
adOpenForwardOnly = 0
adOpenKeyset = 1
adOpenStatic = 3
adOpenUnspecified = -1

# CommandTypeEnum
adCmdText = 1
adCmdStoredProc = 4
adSchemaTables = 20

# ParameterDirectionEnum
adParamInput = 1
adParamInputOutput = 3
adParamOutput = 2
adParamReturnValue = 4
adParamUnknown = 0
directions = {
    0: "Unknown",
    1: "Input",
    2: "Output",
    3: "InputOutput",
    4: "Return",
}


def ado_direction_name(ado_dir):
    try:
        return "adParam" + directions[ado_dir]
    except:
        return f"unknown direction ({ado_dir})"


# ObjectStateEnum
adStateClosed = 0
adStateOpen = 1
adStateConnecting = 2
adStateExecuting = 4
adStateFetching = 8

# FieldAttributeEnum
adFldMayBeNull = 0x40

# ConnectModeEnum
adModeUnknown = 0
adModeRead = 1
adModeWrite = 2
adModeReadWrite = 3
adModeShareDenyRead = 4
adModeShareDenyWrite = 8
adModeShareExclusive = 12
adModeShareDenyNone = 16
adModeRecursive = 0x400000

# XactAttributeEnum
adXactCommitRetaining = 131072
adXactAbortRetaining = 262144

ado_error_TIMEOUT = -2147217871

# DataTypeEnum - ADO Data types documented at:
# http://msdn2.microsoft.com/en-us/library/ms675318.aspx
# TODO: Update to https://learn.microsoft.com/en-us/sql/ado/reference/ado-api/datatypeenum
adArray = 0x2000
adEmpty = 0x0
adBSTR = 0x8
adBigInt = 0x14
adBinary = 0x80
adBoolean = 0xB
adChapter = 0x88
adChar = 0x81
adCurrency = 0x6
adDBDate = 0x85
adDBTime = 0x86
adDBTimeStamp = 0x87
adDate = 0x7
adDecimal = 0xE
adDouble = 0x5
adError = 0xA
adFileTime = 0x40
adGUID = 0x48
adIDispatch = 0x9
adIUnknown = 0xD
adInteger = 0x3
adLongVarBinary = 0xCD
adLongVarChar = 0xC9
adLongVarWChar = 0xCB
adNumeric = 0x83
adPropVariant = 0x8A
adSingle = 0x4
adSmallInt = 0x2
adTinyInt = 0x10
adUnsignedBigInt = 0x15
adUnsignedInt = 0x13
adUnsignedSmallInt = 0x12
adUnsignedTinyInt = 0x11
adUserDefined = 0x84
adVarBinary = 0xCC
adVarChar = 0xC8
adVarNumeric = 0x8B
adVarWChar = 0xCA
adVariant = 0xC
adWChar = 0x82
# Additional constants used by introspection but not ADO itself
AUTO_FIELD_MARKER = -1000

adTypeNames = {
    adBSTR: "adBSTR",
    adBigInt: "adBigInt",
    adBinary: "adBinary",
    adBoolean: "adBoolean",
    adChapter: "adChapter",
    adChar: "adChar",
    adCurrency: "adCurrency",
    adDBDate: "adDBDate",
    adDBTime: "adDBTime",
    adDBTimeStamp: "adDBTimeStamp",
    adDate: "adDate",
    adDecimal: "adDecimal",
    adDouble: "adDouble",
    adEmpty: "adEmpty",
    adError: "adError",
    adFileTime: "adFileTime",
    adGUID: "adGUID",
    adIDispatch: "adIDispatch",
    adIUnknown: "adIUnknown",
    adInteger: "adInteger",
    adLongVarBinary: "adLongVarBinary",
    adLongVarChar: "adLongVarChar",
    adLongVarWChar: "adLongVarWChar",
    adNumeric: "adNumeric",
    adPropVariant: "adPropVariant",
    adSingle: "adSingle",
    adSmallInt: "adSmallInt",
    adTinyInt: "adTinyInt",
    adUnsignedBigInt: "adUnsignedBigInt",
    adUnsignedInt: "adUnsignedInt",
    adUnsignedSmallInt: "adUnsignedSmallInt",
    adUnsignedTinyInt: "adUnsignedTinyInt",
    adUserDefined: "adUserDefined",
    adVarBinary: "adVarBinary",
    adVarChar: "adVarChar",
    adVarNumeric: "adVarNumeric",
    adVarWChar: "adVarWChar",
    adVariant: "adVariant",
    adWChar: "adWChar",
}


def ado_type_name(ado_type):
    return adTypeNames.get(ado_type, f"unknown type ({ado_type})")


# here in decimal, sorted by value
# adEmpty 0 Specifies no value (DBTYPE_EMPTY).
# adSmallInt 2 Indicates a two-byte signed integer (DBTYPE_I2).
# adInteger 3 Indicates a four-byte signed integer (DBTYPE_I4).
# adSingle 4 Indicates a single-precision floating-point value (DBTYPE_R4).
# adDouble 5 Indicates a double-precision floating-point value (DBTYPE_R8).
# adCurrency 6 Indicates a currency value (DBTYPE_CY). Currency is a fixed-point number
#   with four digits to the right of the decimal point. It is stored in an eight-byte signed integer scaled by 10,000.
# adDate 7 Indicates a date value (DBTYPE_DATE). A date is stored as a double, the whole part of which is
#   the number of days since December 30, 1899, and the fractional part of which is the fraction of a day.
# adBSTR 8 Indicates a null-terminated character string (Unicode) (DBTYPE_BSTR).
# adIDispatch 9 Indicates a pointer to an IDispatch interface on a COM object (DBTYPE_IDISPATCH).
# adError 10 Indicates a 32-bit error code (DBTYPE_ERROR).
# adBoolean 11 Indicates a boolean value (DBTYPE_BOOL).
# adVariant 12 Indicates an Automation Variant (DBTYPE_VARIANT).
# adIUnknown 13 Indicates a pointer to an IUnknown interface on a COM object (DBTYPE_IUNKNOWN).
# adDecimal 14 Indicates an exact numeric value with a fixed precision and scale (DBTYPE_DECIMAL).
# adTinyInt 16 Indicates a one-byte signed integer (DBTYPE_I1).
# adUnsignedTinyInt 17 Indicates a one-byte unsigned integer (DBTYPE_UI1).
# adUnsignedSmallInt 18 Indicates a two-byte unsigned integer (DBTYPE_UI2).
# adUnsignedInt 19 Indicates a four-byte unsigned integer (DBTYPE_UI4).
# adBigInt 20 Indicates an eight-byte signed integer (DBTYPE_I8).
# adUnsignedBigInt 21 Indicates an eight-byte unsigned integer (DBTYPE_UI8).
# adFileTime 64 Indicates a 64-bit value representing the number of 100-nanosecond intervals since
#    January 1, 1601 (DBTYPE_FILETIME).
# adGUID 72 Indicates a globally unique identifier (GUID) (DBTYPE_GUID).
# adBinary 128 Indicates a binary value (DBTYPE_BYTES).
# adChar 129 Indicates a string value (DBTYPE_STR).
# adWChar 130 Indicates a null-terminated Unicode character string (DBTYPE_WSTR).
# adNumeric 131 Indicates an exact numeric value with a fixed precision and scale (DBTYPE_NUMERIC).
#   adUserDefined 132 Indicates a user-defined variable (DBTYPE_UDT).
# adUserDefined 132 Indicates a user-defined variable (DBTYPE_UDT).
# adDBDate 133 Indicates a date value (yyyymmdd) (DBTYPE_DBDATE).
# adDBTime 134 Indicates a time value (hhmmss) (DBTYPE_DBTIME).
# adDBTimeStamp 135 Indicates a date/time stamp (yyyymmddhhmmss plus a fraction in billionths) (DBTYPE_DBTIMESTAMP).
# adChapter 136 Indicates a four-byte chapter value that identifies rows in a child rowset (DBTYPE_HCHAPTER).
# adPropVariant 138 Indicates an Automation PROPVARIANT (DBTYPE_PROP_VARIANT).
# adVarNumeric 139 Indicates a numeric value (Parameter object only).
# adVarChar 200 Indicates a string value (Parameter object only).
# adLongVarChar 201 Indicates a long string value (Parameter object only).
# adVarWChar 202 Indicates a null-terminated Unicode character string (Parameter object only).
# adLongVarWChar 203 Indicates a long null-terminated Unicode string value (Parameter object only).
# adVarBinary 204 Indicates a binary value (Parameter object only).
# adLongVarBinary 205 Indicates a long binary value (Parameter object only).
# adArray (Does not apply to ADOX.) 0x2000 A flag value, always combined with another data type constant,
#   that indicates an array of that other data type.

# Error codes to names
adoErrors = {
    0xE7B: "adErrBoundToCommand",
    0xE94: "adErrCannotComplete",
    0xEA4: "adErrCantChangeConnection",
    0xC94: "adErrCantChangeProvider",
    0xE8C: "adErrCantConvertvalue",
    0xE8D: "adErrCantCreate",
    0xEA3: "adErrCatalogNotSet",
    0xE8E: "adErrColumnNotOnThisRow",
    0xD5D: "adErrDataConversion",
    0xE89: "adErrDataOverflow",
    0xE9A: "adErrDelResOutOfScope",
    0xEA6: "adErrDenyNotSupported",
    0xEA7: "adErrDenyTypeNotSupported",
    0xCB3: "adErrFeatureNotAvailable",
    0xEA5: "adErrFieldsUpdateFailed",
    0xC93: "adErrIllegalOperation",
    0xCAE: "adErrInTransaction",
    0xE87: "adErrIntegrityViolation",
    0xBB9: "adErrInvalidArgument",
    0xE7D: "adErrInvalidConnection",
    0xE7C: "adErrInvalidParamInfo",
    0xE82: "adErrInvalidTransaction",
    0xE91: "adErrInvalidURL",
    0xCC1: "adErrItemNotFound",
    0xBCD: "adErrNoCurrentRecord",
    0xE83: "adErrNotExecuting",
    0xE7E: "adErrNotReentrant",
    0xE78: "adErrObjectClosed",
    0xD27: "adErrObjectInCollection",
    0xD5C: "adErrObjectNotSet",
    0xE79: "adErrObjectOpen",
    0xBBA: "adErrOpeningFile",
    0xE80: "adErrOperationCancelled",
    0xE96: "adErrOutOfSpace",
    0xE88: "adErrPermissionDenied",
    0xE9E: "adErrPropConflicting",
    0xE9B: "adErrPropInvalidColumn",
    0xE9C: "adErrPropInvalidOption",
    0xE9D: "adErrPropInvalidValue",
    0xE9F: "adErrPropNotAllSettable",
    0xEA0: "adErrPropNotSet",
    0xEA1: "adErrPropNotSettable",
    0xEA2: "adErrPropNotSupported",
    0xBB8: "adErrProviderFailed",
    0xE7A: "adErrProviderNotFound",
    0xBBB: "adErrReadFile",
    0xE93: "adErrResourceExists",
    0xE92: "adErrResourceLocked",
    0xE97: "adErrResourceOutOfScope",
    0xE8A: "adErrSchemaViolation",
    0xE8B: "adErrSignMismatch",
    0xE81: "adErrStillConnecting",
    0xE7F: "adErrStillExecuting",
    0xE90: "adErrTreePermissionDenied",
    0xE8F: "adErrURLDoesNotExist",
    0xE99: "adErrURLNamedRowDoesNotExist",
    0xE98: "adErrUnavailable",
    0xE84: "adErrUnsafeOperation",
    0xE95: "adErrVolumeNotFound",
    0xBBC: "adErrWriteFile",
}

# === NexusCore/openenv\Lib\site-packages\pyee\base.py ===
# -*- coding: utf-8 -*-

from collections import OrderedDict
from threading import Lock
from typing import (
    Any,
    Callable,
    Dict,
    List,
    Mapping,
    Optional,
    overload,
    Set,
    Tuple,
    TypeVar,
    Union,
)

Self = Any


class PyeeException(Exception):
    """An exception internal to pyee. Deprecated in favor of PyeeError."""


class PyeeError(PyeeException):
    """An error internal to pyee."""


Handler = TypeVar("Handler", bound=Callable)


class EventEmitter:
    """The base event emitter class. All other event emitters inherit from
    this class.

    Most events are registered with an emitter via the `on` and `once`
    methods, and fired with the `emit` method. However, pyee event emitters
    have two *special* events:

    - `new_listener`: Fires whenever a new listener is created. Listeners for
      this event do not fire upon their own creation.

    - `error`: When emitted raises an Exception by default, behavior can be
      overridden by attaching callback to the event.

      For example:

    ```py
    @ee.on('error')
    def on_error(message):
        logging.err(message)

    ee.emit('error', Exception('something blew up'))
    ```

    All callbacks are handled in a synchronous, blocking manner. As in node.js,
    raised exceptions are not automatically handled for you---you must catch
    your own exceptions, and treat them accordingly.
    """

    def __init__(self: Self) -> None:
        self._events: Dict[
            str,
            "OrderedDict[Callable, Callable]",
        ] = dict()
        self._lock: Lock = Lock()

    def __getstate__(self: Self) -> Mapping[str, Any]:
        state = self.__dict__.copy()
        del state["_lock"]
        return state

    def __setstate__(self: Self, state: Mapping[str, Any]) -> None:
        self.__dict__.update(state)
        self._lock = Lock()

    @overload
    def on(self: Self, event: str) -> Callable[[Handler], Handler]: ...
    @overload
    def on(self: Self, event: str, f: Handler) -> Handler: ...

    def on(
        self: Self, event: str, f: Optional[Handler] = None
    ) -> Union[Handler, Callable[[Handler], Handler]]:
        """Registers the function `f` to the event name `event`, if provided.

        If `f` isn't provided, this method calls `EventEmitter#listens_to`, and
        otherwise calls `EventEmitter#add_listener`. In other words, you may either
        use it as a decorator:

        ```py
        @ee.on('data')
        def data_handler(data):
            print(data)
        ```

        Or directly:

        ```py
        ee.on('data', data_handler)
        ```

        In both the decorated and undecorated forms, the event handler is
        returned. The upshot of this is that you can call decorated handlers
        directly, as well as use them in remove_listener calls.

        Note that this method's return type is a union type. If you are using
        mypy or pyright, you will probably want to use either
        `EventEmitter#listens_to` or `EventEmitter#add_listener`.
        """
        if f is None:
            return self.listens_to(event)
        else:
            return self.add_listener(event, f)

    def listens_to(self: Self, event: str) -> Callable[[Handler], Handler]:
        """Returns a decorator which will register the decorated function to
        the event name `event`:

        ```py
        @ee.listens_to("event")
        def data_handler(data):
            print(data)
        ```

        By only supporting the decorator use case, this method has improved
        type safety over `EventEmitter#on`.
        """

        def on(f: Handler) -> Handler:
            self._add_event_handler(event, f, f)
            return f

        return on

    def add_listener(self: Self, event: str, f: Handler) -> Handler:
        """Register the function `f` to the event name `event`:

        ```
        def data_handler(data):
            print(data)

        h = ee.add_listener("event", data_handler)
        ```

        By not supporting the decorator use case, this method has improved
        type safety over `EventEmitter#on`.
        """
        self._add_event_handler(event, f, f)
        return f

    def _add_event_handler(self: Self, event: str, k: Callable, v: Callable):
        # Fire 'new_listener' *before* adding the new listener!
        self.emit("new_listener", event, k)

        # Add the necessary function
        # Note that k and v are the same for `on` handlers, but
        # different for `once` handlers, where v is a wrapped version
        # of k which removes itself before calling k
        with self._lock:
            if event not in self._events:
                self._events[event] = OrderedDict()
            self._events[event][k] = v

    def _emit_run(
        self: Self,
        f: Callable,
        args: Tuple[Any, ...],
        kwargs: Dict[str, Any],
    ) -> None:
        f(*args, **kwargs)

    def event_names(self: Self) -> Set[str]:
        """Get a set of events that this emitter is listening to."""
        return set(self._events.keys())

    def _emit_handle_potential_error(self: Self, event: str, error: Any) -> None:
        if event == "error":
            if isinstance(error, Exception):
                raise error
            else:
                raise PyeeError(f"Uncaught, unspecified 'error' event: {error}")

    def _call_handlers(
        self: Self,
        event: str,
        args: Tuple[Any, ...],
        kwargs: Dict[str, Any],
    ) -> bool:
        handled = False

        with self._lock:
            funcs = list(self._events.get(event, OrderedDict()).values())
        for f in funcs:
            self._emit_run(f, args, kwargs)
            handled = True

        return handled

    def emit(
        self: Self,
        event: str,
        *args: Any,
        **kwargs: Any,
    ) -> bool:
        """Emit `event`, passing `*args` and `**kwargs` to each attached
        function. Returns `True` if any functions are attached to `event`;
        otherwise returns `False`.

        Example:

        ```py
        ee.emit('data', '00101001')
        ```

        Assuming `data` is an attached function, this will call
        `data('00101001')'`.
        """
        handled = self._call_handlers(event, args, kwargs)

        if not handled:
            self._emit_handle_potential_error(event, args[0] if args else None)

        return handled

    def once(
        self: Self,
        event: str,
        f: Optional[Callable] = None,
    ) -> Callable:
        """The same as `ee.on`, except that the listener is automatically
        removed after being called.
        """

        def _wrapper(f: Callable) -> Callable:
            def g(
                *args: Any,
                **kwargs: Any,
            ) -> Any:
                with self._lock:
                    # Check that the event wasn't removed already right
                    # before the lock
                    if event in self._events and f in self._events[event]:
                        self._remove_listener(event, f)
                    else:
                        return None
                # f may return a coroutine, so we need to return that
                # result here so that emit can schedule it
                return f(*args, **kwargs)

            self._add_event_handler(event, f, g)
            return f

        if f is None:
            return _wrapper
        else:
            return _wrapper(f)

    def _remove_listener(self: Self, event: str, f: Callable) -> None:
        """Naked unprotected removal."""
        self._events[event].pop(f)
        if not len(self._events[event]):
            del self._events[event]

    def remove_listener(self: Self, event: str, f: Callable) -> None:
        """Removes the function `f` from `event`."""
        with self._lock:
            self._remove_listener(event, f)

    def remove_all_listeners(self: Self, event: Optional[str] = None) -> None:
        """Remove all listeners attached to `event`.
        If `event` is `None`, remove all listeners on all events.
        """
        with self._lock:
            if event is not None:
                self._events[event] = OrderedDict()
            else:
                self._events = dict()

    def listeners(self: Self, event: str) -> List[Callable]:
        """Returns a list of all listeners registered to the `event`."""
        return list(self._events.get(event, OrderedDict()).keys())

# === NexusCore/openenv\Lib\site-packages\google\ai\generativelanguage_v1beta\services\model_service\pagers.py ===
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
from typing import (
    Any,
    AsyncIterator,
    Awaitable,
    Callable,
    Iterator,
    Optional,
    Sequence,
    Tuple,
)

from google.ai.generativelanguage_v1beta.types import model, model_service, tuned_model


class ListModelsPager:
    """A pager for iterating through ``list_models`` requests.

    This class thinly wraps an initial
    :class:`google.ai.generativelanguage_v1beta.types.ListModelsResponse` object, and
    provides an ``__iter__`` method to iterate through its
    ``models`` field.

    If there are more pages, the ``__iter__`` method will make additional
    ``ListModels`` requests and continue to iterate
    through the ``models`` field on the
    corresponding responses.

    All the usual :class:`google.ai.generativelanguage_v1beta.types.ListModelsResponse`
    attributes are available on the pager. If multiple requests are made, only
    the most recent response is retained, and thus used for attribute lookup.
    """

    def __init__(
        self,
        method: Callable[..., model_service.ListModelsResponse],
        request: model_service.ListModelsRequest,
        response: model_service.ListModelsResponse,
        *,
        metadata: Sequence[Tuple[str, str]] = ()
    ):
        """Instantiate the pager.

        Args:
            method (Callable): The method that was originally called, and
                which instantiated this pager.
            request (google.ai.generativelanguage_v1beta.types.ListModelsRequest):
                The initial request object.
            response (google.ai.generativelanguage_v1beta.types.ListModelsResponse):
                The initial response object.
            metadata (Sequence[Tuple[str, str]]): Strings which should be
                sent along with the request as metadata.
        """
        self._method = method
        self._request = model_service.ListModelsRequest(request)
        self._response = response
        self._metadata = metadata

    def __getattr__(self, name: str) -> Any:
        return getattr(self._response, name)

    @property
    def pages(self) -> Iterator[model_service.ListModelsResponse]:
        yield self._response
        while self._response.next_page_token:
            self._request.page_token = self._response.next_page_token
            self._response = self._method(self._request, metadata=self._metadata)
            yield self._response

    def __iter__(self) -> Iterator[model.Model]:
        for page in self.pages:
            yield from page.models

    def __repr__(self) -> str:
        return "{0}<{1!r}>".format(self.__class__.__name__, self._response)


class ListModelsAsyncPager:
    """A pager for iterating through ``list_models`` requests.

    This class thinly wraps an initial
    :class:`google.ai.generativelanguage_v1beta.types.ListModelsResponse` object, and
    provides an ``__aiter__`` method to iterate through its
    ``models`` field.

    If there are more pages, the ``__aiter__`` method will make additional
    ``ListModels`` requests and continue to iterate
    through the ``models`` field on the
    corresponding responses.

    All the usual :class:`google.ai.generativelanguage_v1beta.types.ListModelsResponse`
    attributes are available on the pager. If multiple requests are made, only
    the most recent response is retained, and thus used for attribute lookup.
    """

    def __init__(
        self,
        method: Callable[..., Awaitable[model_service.ListModelsResponse]],
        request: model_service.ListModelsRequest,
        response: model_service.ListModelsResponse,
        *,
        metadata: Sequence[Tuple[str, str]] = ()
    ):
        """Instantiates the pager.

        Args:
            method (Callable): The method that was originally called, and
                which instantiated this pager.
            request (google.ai.generativelanguage_v1beta.types.ListModelsRequest):
                The initial request object.
            response (google.ai.generativelanguage_v1beta.types.ListModelsResponse):
                The initial response object.
            metadata (Sequence[Tuple[str, str]]): Strings which should be
                sent along with the request as metadata.
        """
        self._method = method
        self._request = model_service.ListModelsRequest(request)
        self._response = response
        self._metadata = metadata

    def __getattr__(self, name: str) -> Any:
        return getattr(self._response, name)

    @property
    async def pages(self) -> AsyncIterator[model_service.ListModelsResponse]:
        yield self._response
        while self._response.next_page_token:
            self._request.page_token = self._response.next_page_token
            self._response = await self._method(self._request, metadata=self._metadata)
            yield self._response

    def __aiter__(self) -> AsyncIterator[model.Model]:
        async def async_generator():
            async for page in self.pages:
                for response in page.models:
                    yield response

        return async_generator()

    def __repr__(self) -> str:
        return "{0}<{1!r}>".format(self.__class__.__name__, self._response)


class ListTunedModelsPager:
    """A pager for iterating through ``list_tuned_models`` requests.

    This class thinly wraps an initial
    :class:`google.ai.generativelanguage_v1beta.types.ListTunedModelsResponse` object, and
    provides an ``__iter__`` method to iterate through its
    ``tuned_models`` field.

    If there are more pages, the ``__iter__`` method will make additional
    ``ListTunedModels`` requests and continue to iterate
    through the ``tuned_models`` field on the
    corresponding responses.

    All the usual :class:`google.ai.generativelanguage_v1beta.types.ListTunedModelsResponse`
    attributes are available on the pager. If multiple requests are made, only
    the most recent response is retained, and thus used for attribute lookup.
    """

    def __init__(
        self,
        method: Callable[..., model_service.ListTunedModelsResponse],
        request: model_service.ListTunedModelsRequest,
        response: model_service.ListTunedModelsResponse,
        *,
        metadata: Sequence[Tuple[str, str]] = ()
    ):
        """Instantiate the pager.

        Args:
            method (Callable): The method that was originally called, and
                which instantiated this pager.
            request (google.ai.generativelanguage_v1beta.types.ListTunedModelsRequest):
                The initial request object.
            response (google.ai.generativelanguage_v1beta.types.ListTunedModelsResponse):
                The initial response object.
            metadata (Sequence[Tuple[str, str]]): Strings which should be
                sent along with the request as metadata.
        """
        self._method = method
        self._request = model_service.ListTunedModelsRequest(request)
        self._response = response
        self._metadata = metadata

    def __getattr__(self, name: str) -> Any:
        return getattr(self._response, name)

    @property
    def pages(self) -> Iterator[model_service.ListTunedModelsResponse]:
        yield self._response
        while self._response.next_page_token:
            self._request.page_token = self._response.next_page_token
            self._response = self._method(self._request, metadata=self._metadata)
            yield self._response

    def __iter__(self) -> Iterator[tuned_model.TunedModel]:
        for page in self.pages:
            yield from page.tuned_models

    def __repr__(self) -> str:
        return "{0}<{1!r}>".format(self.__class__.__name__, self._response)


class ListTunedModelsAsyncPager:
    """A pager for iterating through ``list_tuned_models`` requests.

    This class thinly wraps an initial
    :class:`google.ai.generativelanguage_v1beta.types.ListTunedModelsResponse` object, and
    provides an ``__aiter__`` method to iterate through its
    ``tuned_models`` field.

    If there are more pages, the ``__aiter__`` method will make additional
    ``ListTunedModels`` requests and continue to iterate
    through the ``tuned_models`` field on the
    corresponding responses.

    All the usual :class:`google.ai.generativelanguage_v1beta.types.ListTunedModelsResponse`
    attributes are available on the pager. If multiple requests are made, only
    the most recent response is retained, and thus used for attribute lookup.
    """

    def __init__(
        self,
        method: Callable[..., Awaitable[model_service.ListTunedModelsResponse]],
        request: model_service.ListTunedModelsRequest,
        response: model_service.ListTunedModelsResponse,
        *,
        metadata: Sequence[Tuple[str, str]] = ()
    ):
        """Instantiates the pager.

        Args:
            method (Callable): The method that was originally called, and
                which instantiated this pager.
            request (google.ai.generativelanguage_v1beta.types.ListTunedModelsRequest):
                The initial request object.
            response (google.ai.generativelanguage_v1beta.types.ListTunedModelsResponse):
                The initial response object.
            metadata (Sequence[Tuple[str, str]]): Strings which should be
                sent along with the request as metadata.
        """
        self._method = method
        self._request = model_service.ListTunedModelsRequest(request)
        self._response = response
        self._metadata = metadata

    def __getattr__(self, name: str) -> Any:
        return getattr(self._response, name)

    @property
    async def pages(self) -> AsyncIterator[model_service.ListTunedModelsResponse]:
        yield self._response
        while self._response.next_page_token:
            self._request.page_token = self._response.next_page_token
            self._response = await self._method(self._request, metadata=self._metadata)
            yield self._response

    def __aiter__(self) -> AsyncIterator[tuned_model.TunedModel]:
        async def async_generator():
            async for page in self.pages:
                for response in page.tuned_models:
                    yield response

        return async_generator()

    def __repr__(self) -> str:
        return "{0}<{1!r}>".format(self.__class__.__name__, self._response)

# === NexusCore/openenv\Lib\site-packages\google\ai\generativelanguage_v1beta3\services\model_service\pagers.py ===
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
from typing import (
    Any,
    AsyncIterator,
    Awaitable,
    Callable,
    Iterator,
    Optional,
    Sequence,
    Tuple,
)

from google.ai.generativelanguage_v1beta3.types import model, model_service, tuned_model


class ListModelsPager:
    """A pager for iterating through ``list_models`` requests.

    This class thinly wraps an initial
    :class:`google.ai.generativelanguage_v1beta3.types.ListModelsResponse` object, and
    provides an ``__iter__`` method to iterate through its
    ``models`` field.

    If there are more pages, the ``__iter__`` method will make additional
    ``ListModels`` requests and continue to iterate
    through the ``models`` field on the
    corresponding responses.

    All the usual :class:`google.ai.generativelanguage_v1beta3.types.ListModelsResponse`
    attributes are available on the pager. If multiple requests are made, only
    the most recent response is retained, and thus used for attribute lookup.
    """

    def __init__(
        self,
        method: Callable[..., model_service.ListModelsResponse],
        request: model_service.ListModelsRequest,
        response: model_service.ListModelsResponse,
        *,
        metadata: Sequence[Tuple[str, str]] = ()
    ):
        """Instantiate the pager.

        Args:
            method (Callable): The method that was originally called, and
                which instantiated this pager.
            request (google.ai.generativelanguage_v1beta3.types.ListModelsRequest):
                The initial request object.
            response (google.ai.generativelanguage_v1beta3.types.ListModelsResponse):
                The initial response object.
            metadata (Sequence[Tuple[str, str]]): Strings which should be
                sent along with the request as metadata.
        """
        self._method = method
        self._request = model_service.ListModelsRequest(request)
        self._response = response
        self._metadata = metadata

    def __getattr__(self, name: str) -> Any:
        return getattr(self._response, name)

    @property
    def pages(self) -> Iterator[model_service.ListModelsResponse]:
        yield self._response
        while self._response.next_page_token:
            self._request.page_token = self._response.next_page_token
            self._response = self._method(self._request, metadata=self._metadata)
            yield self._response

    def __iter__(self) -> Iterator[model.Model]:
        for page in self.pages:
            yield from page.models

    def __repr__(self) -> str:
        return "{0}<{1!r}>".format(self.__class__.__name__, self._response)


class ListModelsAsyncPager:
    """A pager for iterating through ``list_models`` requests.

    This class thinly wraps an initial
    :class:`google.ai.generativelanguage_v1beta3.types.ListModelsResponse` object, and
    provides an ``__aiter__`` method to iterate through its
    ``models`` field.

    If there are more pages, the ``__aiter__`` method will make additional
    ``ListModels`` requests and continue to iterate
    through the ``models`` field on the
    corresponding responses.

    All the usual :class:`google.ai.generativelanguage_v1beta3.types.ListModelsResponse`
    attributes are available on the pager. If multiple requests are made, only
    the most recent response is retained, and thus used for attribute lookup.
    """

    def __init__(
        self,
        method: Callable[..., Awaitable[model_service.ListModelsResponse]],
        request: model_service.ListModelsRequest,
        response: model_service.ListModelsResponse,
        *,
        metadata: Sequence[Tuple[str, str]] = ()
    ):
        """Instantiates the pager.

        Args:
            method (Callable): The method that was originally called, and
                which instantiated this pager.
            request (google.ai.generativelanguage_v1beta3.types.ListModelsRequest):
                The initial request object.
            response (google.ai.generativelanguage_v1beta3.types.ListModelsResponse):
                The initial response object.
            metadata (Sequence[Tuple[str, str]]): Strings which should be
                sent along with the request as metadata.
        """
        self._method = method
        self._request = model_service.ListModelsRequest(request)
        self._response = response
        self._metadata = metadata

    def __getattr__(self, name: str) -> Any:
        return getattr(self._response, name)

    @property
    async def pages(self) -> AsyncIterator[model_service.ListModelsResponse]:
        yield self._response
        while self._response.next_page_token:
            self._request.page_token = self._response.next_page_token
            self._response = await self._method(self._request, metadata=self._metadata)
            yield self._response

    def __aiter__(self) -> AsyncIterator[model.Model]:
        async def async_generator():
            async for page in self.pages:
                for response in page.models:
                    yield response

        return async_generator()

    def __repr__(self) -> str:
        return "{0}<{1!r}>".format(self.__class__.__name__, self._response)


class ListTunedModelsPager:
    """A pager for iterating through ``list_tuned_models`` requests.

    This class thinly wraps an initial
    :class:`google.ai.generativelanguage_v1beta3.types.ListTunedModelsResponse` object, and
    provides an ``__iter__`` method to iterate through its
    ``tuned_models`` field.

    If there are more pages, the ``__iter__`` method will make additional
    ``ListTunedModels`` requests and continue to iterate
    through the ``tuned_models`` field on the
    corresponding responses.

    All the usual :class:`google.ai.generativelanguage_v1beta3.types.ListTunedModelsResponse`
    attributes are available on the pager. If multiple requests are made, only
    the most recent response is retained, and thus used for attribute lookup.
    """

    def __init__(
        self,
        method: Callable[..., model_service.ListTunedModelsResponse],
        request: model_service.ListTunedModelsRequest,
        response: model_service.ListTunedModelsResponse,
        *,
        metadata: Sequence[Tuple[str, str]] = ()
    ):
        """Instantiate the pager.

        Args:
            method (Callable): The method that was originally called, and
                which instantiated this pager.
            request (google.ai.generativelanguage_v1beta3.types.ListTunedModelsRequest):
                The initial request object.
            response (google.ai.generativelanguage_v1beta3.types.ListTunedModelsResponse):
                The initial response object.
            metadata (Sequence[Tuple[str, str]]): Strings which should be
                sent along with the request as metadata.
        """
        self._method = method
        self._request = model_service.ListTunedModelsRequest(request)
        self._response = response
        self._metadata = metadata

    def __getattr__(self, name: str) -> Any:
        return getattr(self._response, name)

    @property
    def pages(self) -> Iterator[model_service.ListTunedModelsResponse]:
        yield self._response
        while self._response.next_page_token:
            self._request.page_token = self._response.next_page_token
            self._response = self._method(self._request, metadata=self._metadata)
            yield self._response

    def __iter__(self) -> Iterator[tuned_model.TunedModel]:
        for page in self.pages:
            yield from page.tuned_models

    def __repr__(self) -> str:
        return "{0}<{1!r}>".format(self.__class__.__name__, self._response)


class ListTunedModelsAsyncPager:
    """A pager for iterating through ``list_tuned_models`` requests.

    This class thinly wraps an initial
    :class:`google.ai.generativelanguage_v1beta3.types.ListTunedModelsResponse` object, and
    provides an ``__aiter__`` method to iterate through its
    ``tuned_models`` field.

    If there are more pages, the ``__aiter__`` method will make additional
    ``ListTunedModels`` requests and continue to iterate
    through the ``tuned_models`` field on the
    corresponding responses.

    All the usual :class:`google.ai.generativelanguage_v1beta3.types.ListTunedModelsResponse`
    attributes are available on the pager. If multiple requests are made, only
    the most recent response is retained, and thus used for attribute lookup.
    """

    def __init__(
        self,
        method: Callable[..., Awaitable[model_service.ListTunedModelsResponse]],
        request: model_service.ListTunedModelsRequest,
        response: model_service.ListTunedModelsResponse,
        *,
        metadata: Sequence[Tuple[str, str]] = ()
    ):
        """Instantiates the pager.

        Args:
            method (Callable): The method that was originally called, and
                which instantiated this pager.
            request (google.ai.generativelanguage_v1beta3.types.ListTunedModelsRequest):
                The initial request object.
            response (google.ai.generativelanguage_v1beta3.types.ListTunedModelsResponse):
                The initial response object.
            metadata (Sequence[Tuple[str, str]]): Strings which should be
                sent along with the request as metadata.
        """
        self._method = method
        self._request = model_service.ListTunedModelsRequest(request)
        self._response = response
        self._metadata = metadata

    def __getattr__(self, name: str) -> Any:
        return getattr(self._response, name)

    @property
    async def pages(self) -> AsyncIterator[model_service.ListTunedModelsResponse]:
        yield self._response
        while self._response.next_page_token:
            self._request.page_token = self._response.next_page_token
            self._response = await self._method(self._request, metadata=self._metadata)
            yield self._response

    def __aiter__(self) -> AsyncIterator[tuned_model.TunedModel]:
        async def async_generator():
            async for page in self.pages:
                for response in page.tuned_models:
                    yield response

        return async_generator()

    def __repr__(self) -> str:
        return "{0}<{1!r}>".format(self.__class__.__name__, self._response)

# === NexusCore/openenv\Lib\site-packages\google\auth\transport\_custom_tls_signer.py ===
# Copyright 2022 Google LLC
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

"""
Code for configuring client side TLS to offload the signing operation to
signing libraries.
"""

import ctypes
import json
import logging
import os
import sys

import cffi  # type: ignore

from google.auth import exceptions

_LOGGER = logging.getLogger(__name__)

# C++ offload lib requires google-auth lib to provide the following callback:
#     using SignFunc = int (*)(unsigned char *sig, size_t *sig_len,
#             const unsigned char *tbs, size_t tbs_len)
# The bytes to be signed and the length are provided via `tbs` and `tbs_len`,
# the callback computes the signature, and write the signature and its length
# into `sig` and `sig_len`.
# If the signing is successful, the callback returns 1, otherwise it returns 0.
SIGN_CALLBACK_CTYPE = ctypes.CFUNCTYPE(
    ctypes.c_int,  # return type
    ctypes.POINTER(ctypes.c_ubyte),  # sig
    ctypes.POINTER(ctypes.c_size_t),  # sig_len
    ctypes.POINTER(ctypes.c_ubyte),  # tbs
    ctypes.c_size_t,  # tbs_len
)


# Cast SSL_CTX* to void*
def _cast_ssl_ctx_to_void_p_pyopenssl(ssl_ctx):
    return ctypes.cast(int(cffi.FFI().cast("intptr_t", ssl_ctx)), ctypes.c_void_p)


# Cast SSL_CTX* to void*
def _cast_ssl_ctx_to_void_p_stdlib(context):
    return ctypes.c_void_p.from_address(
        id(context) + ctypes.sizeof(ctypes.c_void_p) * 2
    )


# Load offload library and set up the function types.
def load_offload_lib(offload_lib_path):
    _LOGGER.debug("loading offload library from %s", offload_lib_path)

    # winmode parameter is only available for python 3.8+.
    lib = (
        ctypes.CDLL(offload_lib_path, winmode=0)
        if sys.version_info >= (3, 8) and os.name == "nt"
        else ctypes.CDLL(offload_lib_path)
    )

    # Set up types for:
    # int ConfigureSslContext(SignFunc sign_func, const char *cert, SSL_CTX *ctx)
    lib.ConfigureSslContext.argtypes = [
        SIGN_CALLBACK_CTYPE,
        ctypes.c_char_p,
        ctypes.c_void_p,
    ]
    lib.ConfigureSslContext.restype = ctypes.c_int

    return lib


# Load signer library and set up the function types.
# See: https://github.com/googleapis/enterprise-certificate-proxy/blob/main/cshared/main.go
def load_signer_lib(signer_lib_path):
    _LOGGER.debug("loading signer library from %s", signer_lib_path)

    # winmode parameter is only available for python 3.8+.
    lib = (
        ctypes.CDLL(signer_lib_path, winmode=0)
        if sys.version_info >= (3, 8) and os.name == "nt"
        else ctypes.CDLL(signer_lib_path)
    )

    # Set up types for:
    # func GetCertPemForPython(configFilePath *C.char, certHolder *byte, certHolderLen int)
    lib.GetCertPemForPython.argtypes = [ctypes.c_char_p, ctypes.c_char_p, ctypes.c_int]
    # Returns: certLen
    lib.GetCertPemForPython.restype = ctypes.c_int

    # Set up types for:
    # func SignForPython(configFilePath *C.char, digest *byte, digestLen int,
    #     sigHolder *byte, sigHolderLen int)
    lib.SignForPython.argtypes = [
        ctypes.c_char_p,
        ctypes.c_char_p,
        ctypes.c_int,
        ctypes.c_char_p,
        ctypes.c_int,
    ]
    # Returns: the signature length
    lib.SignForPython.restype = ctypes.c_int

    return lib


def load_provider_lib(provider_lib_path):
    _LOGGER.debug("loading provider library from %s", provider_lib_path)

    # winmode parameter is only available for python 3.8+.
    lib = (
        ctypes.CDLL(provider_lib_path, winmode=0)
        if sys.version_info >= (3, 8) and os.name == "nt"
        else ctypes.CDLL(provider_lib_path)
    )

    lib.ECP_attach_to_ctx.argtypes = [ctypes.c_void_p, ctypes.c_char_p]
    lib.ECP_attach_to_ctx.restype = ctypes.c_int

    return lib


# Computes SHA256 hash.
def _compute_sha256_digest(to_be_signed, to_be_signed_len):
    from cryptography.hazmat.primitives import hashes

    data = ctypes.string_at(to_be_signed, to_be_signed_len)
    hash = hashes.Hash(hashes.SHA256())
    hash.update(data)
    return hash.finalize()


# Create the signing callback. The actual signing work is done by the
# `SignForPython` method from the signer lib.
def get_sign_callback(signer_lib, config_file_path):
    def sign_callback(sig, sig_len, tbs, tbs_len):
        _LOGGER.debug("calling sign callback...")

        digest = _compute_sha256_digest(tbs, tbs_len)
        digestArray = ctypes.c_char * len(digest)

        # reserve 2000 bytes for the signature, shoud be more then enough.
        # RSA signature is 256 bytes, EC signature is 70~72.
        sig_holder_len = 2000
        sig_holder = ctypes.create_string_buffer(sig_holder_len)

        signature_len = signer_lib.SignForPython(
            config_file_path.encode(),  # configFilePath
            digestArray.from_buffer(bytearray(digest)),  # digest
            len(digest),  # digestLen
            sig_holder,  # sigHolder
            sig_holder_len,  # sigHolderLen
        )

        if signature_len == 0:
            # signing failed, return 0
            return 0

        sig_len[0] = signature_len
        bs = bytearray(sig_holder)
        for i in range(signature_len):
            sig[i] = bs[i]

        return 1

    return SIGN_CALLBACK_CTYPE(sign_callback)


# Obtain the certificate bytes by calling the `GetCertPemForPython` method from
# the signer lib. The method is called twice, the first time is to compute the
# cert length, then we create a buffer to hold the cert, and call it again to
# fill the buffer.
def get_cert(signer_lib, config_file_path):
    # First call to calculate the cert length
    cert_len = signer_lib.GetCertPemForPython(
        config_file_path.encode(),  # configFilePath
        None,  # certHolder
        0,  # certHolderLen
    )
    if cert_len == 0:
        raise exceptions.MutualTLSChannelError("failed to get certificate")

    # Then we create an array to hold the cert, and call again to fill the cert
    cert_holder = ctypes.create_string_buffer(cert_len)
    signer_lib.GetCertPemForPython(
        config_file_path.encode(),  # configFilePath
        cert_holder,  # certHolder
        cert_len,  # certHolderLen
    )
    return bytes(cert_holder)


class CustomTlsSigner(object):
    def __init__(self, enterprise_cert_file_path):
        """
        This class loads the offload and signer library, and calls APIs from
        these libraries to obtain the cert and a signing callback, and attach
        them to SSL context. The cert and the signing callback will be used
        for client authentication in TLS handshake.

        Args:
            enterprise_cert_file_path (str): the path to a enterprise cert JSON
                file. The file should contain the following field:

                    {
                        "libs": {
                            "ecp_client": "...",
                            "tls_offload": "..."
                        }
                    }
        """
        self._enterprise_cert_file_path = enterprise_cert_file_path
        self._cert = None
        self._sign_callback = None
        self._provider_lib = None

    def load_libraries(self):
        with open(self._enterprise_cert_file_path, "r") as f:
            enterprise_cert_json = json.load(f)
            libs = enterprise_cert_json.get("libs", {})

            signer_library = libs.get("ecp_client", None)
            offload_library = libs.get("tls_offload", None)
            provider_library = libs.get("ecp_provider", None)

        # Using newer provider implementation. This is mutually exclusive to the
        # offload implementation.
        if provider_library:
            self._provider_lib = load_provider_lib(provider_library)
            return

        # Using old offload implementation
        if offload_library and signer_library:
            self._offload_lib = load_offload_lib(offload_library)
            self._signer_lib = load_signer_lib(signer_library)
            self.set_up_custom_key()
            return

        raise exceptions.MutualTLSChannelError("enterprise cert file is invalid")

    def set_up_custom_key(self):
        # We need to keep a reference of the cert and sign callback so it won't
        # be garbage collected, otherwise it will crash when used by signer lib.
        self._cert = get_cert(self._signer_lib, self._enterprise_cert_file_path)
        self._sign_callback = get_sign_callback(
            self._signer_lib, self._enterprise_cert_file_path
        )

    def should_use_provider(self):
        if self._provider_lib:
            return True
        return False

    def attach_to_ssl_context(self, ctx):
        if self.should_use_provider():
            if not self._provider_lib.ECP_attach_to_ctx(
                _cast_ssl_ctx_to_void_p_stdlib(ctx),
                self._enterprise_cert_file_path.encode("ascii"),
            ):
                raise exceptions.MutualTLSChannelError(
                    "failed to configure ECP Provider SSL context"
                )
        elif self._offload_lib and self._signer_lib:
            if not self._offload_lib.ConfigureSslContext(
                self._sign_callback,
                ctypes.c_char_p(self._cert),
                _cast_ssl_ctx_to_void_p_pyopenssl(ctx._ctx._context),
            ):
                raise exceptions.MutualTLSChannelError(
                    "failed to configure ECP Offload SSL context"
                )
        else:
            raise exceptions.MutualTLSChannelError("Invalid ECP configuration.")

# === NexusCore/openenv\Lib\site-packages\litellm\types\files.py ===
from enum import Enum
from types import MappingProxyType
from typing import List, Set, Mapping

"""
Base Enums/Consts
"""


class FileType(Enum):
    AAC = "AAC"
    CSV = "CSV"
    DOC = "DOC"
    DOCX = "DOCX"
    FLAC = "FLAC"
    FLV = "FLV"
    GIF = "GIF"
    GOOGLE_DOC = "GOOGLE_DOC"
    GOOGLE_DRAWINGS = "GOOGLE_DRAWINGS"
    GOOGLE_SHEETS = "GOOGLE_SHEETS"
    GOOGLE_SLIDES = "GOOGLE_SLIDES"
    HEIC = "HEIC"
    HEIF = "HEIF"
    HTML = "HTML"
    JPEG = "JPEG"
    JSON = "JSON"
    M4A = "M4A"
    M4V = "M4V"
    MOV = "MOV"
    MP3 = "MP3"
    MP4 = "MP4"
    MPEG = "MPEG"
    MPEGPS = "MPEGPS"
    MPG = "MPG"
    MPA = "MPA"
    MPGA = "MPGA"
    OGG = "OGG"
    OPUS = "OPUS"
    PDF = "PDF"
    PCM = "PCM"
    PNG = "PNG"
    PPT = "PPT"
    PPTX = "PPTX"
    RTF = "RTF"
    THREE_GPP = "3GPP"
    TXT = "TXT"
    WAV = "WAV"
    WEBM = "WEBM"
    WEBP = "WEBP"
    WMV = "WMV"
    XLS = "XLS"
    XLSX = "XLSX"


FILE_EXTENSIONS: Mapping[FileType, List[str]] = MappingProxyType(
    {
        FileType.AAC: ["aac"],
        FileType.CSV: ["csv"],
        FileType.DOC: ["doc"],
        FileType.DOCX: ["docx"],
        FileType.FLAC: ["flac"],
        FileType.FLV: ["flv"],
        FileType.GIF: ["gif"],
        FileType.GOOGLE_DOC: ["gdoc"],
        FileType.GOOGLE_DRAWINGS: ["gdraw"],
        FileType.GOOGLE_SHEETS: ["gsheet"],
        FileType.GOOGLE_SLIDES: ["gslides"],
        FileType.HEIC: ["heic"],
        FileType.HEIF: ["heif"],
        FileType.HTML: ["html", "htm"],
        FileType.JPEG: ["jpeg", "jpg"],
        FileType.JSON: ["json"],
        FileType.M4A: ["m4a"],
        FileType.M4V: ["m4v"],
        FileType.MOV: ["mov"],
        FileType.MP3: ["mp3"],
        FileType.MP4: ["mp4"],
        FileType.MPEG: ["mpeg"],
        FileType.MPEGPS: ["mpegps"],
        FileType.MPG: ["mpg"],
        FileType.MPA: ["mpa"],
        FileType.MPGA: ["mpga"],
        FileType.OGG: ["ogg"],
        FileType.OPUS: ["opus"],
        FileType.PDF: ["pdf"],
        FileType.PCM: ["pcm"],
        FileType.PNG: ["png"],
        FileType.PPT: ["ppt"],
        FileType.PPTX: ["pptx"],
        FileType.RTF: ["rtf"],
        FileType.THREE_GPP: ["3gpp"],
        FileType.TXT: ["txt"],
        FileType.WAV: ["wav"],
        FileType.WEBM: ["webm"],
        FileType.WEBP: ["webp"],
        FileType.WMV: ["wmv"],
        FileType.XLS: ["xls"],
        FileType.XLSX: ["xlsx"],
    }
)

FILE_MIME_TYPES: Mapping[FileType, str] = MappingProxyType(
    {
        FileType.AAC: "audio/aac",
        FileType.CSV: "text/csv",
        FileType.DOC: "application/msword",
        FileType.DOCX: "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        FileType.FLAC: "audio/flac",
        FileType.FLV: "video/x-flv",
        FileType.GIF: "image/gif",
        FileType.GOOGLE_DOC: "application/vnd.google-apps.document",
        FileType.GOOGLE_DRAWINGS: "application/vnd.google-apps.drawing",
        FileType.GOOGLE_SHEETS: "application/vnd.google-apps.spreadsheet",
        FileType.GOOGLE_SLIDES: "application/vnd.google-apps.presentation",
        FileType.HEIC: "image/heic",
        FileType.HEIF: "image/heif",
        FileType.HTML: "text/html",
        FileType.JPEG: "image/jpeg",
        FileType.JSON: "application/json",
        FileType.M4A: "audio/x-m4a",
        FileType.M4V: "video/x-m4v",
        FileType.MOV: "video/quicktime",
        FileType.MP3: "audio/mpeg",
        FileType.MP4: "video/mp4",
        FileType.MPEG: "video/mpeg",
        FileType.MPEGPS: "video/mpegps",
        FileType.MPG: "video/mpg",
        FileType.MPA: "audio/m4a",
        FileType.MPGA: "audio/mpga",
        FileType.OGG: "audio/ogg",
        FileType.OPUS: "audio/opus",
        FileType.PDF: "application/pdf",
        FileType.PCM: "audio/pcm",
        FileType.PNG: "image/png",
        FileType.PPT: "application/vnd.ms-powerpoint",
        FileType.PPTX: "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        FileType.RTF: "application/rtf",
        FileType.THREE_GPP: "video/3gpp",
        FileType.TXT: "text/plain",
        FileType.WAV: "audio/wav",
        FileType.WEBM: "video/webm",
        FileType.WEBP: "image/webp",
        FileType.WMV: "video/wmv",
        FileType.XLS: "application/vnd.ms-excel",
        FileType.XLSX: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    }
)

"""
Util Functions
"""


def get_file_extension_from_mime_type(mime_type: str) -> str:
    for file_type, mime in FILE_MIME_TYPES.items():
        if mime.lower() == mime_type.lower():
            return FILE_EXTENSIONS[file_type][0]
    raise ValueError(f"Unknown extension for mime type: {mime_type}")


def get_file_type_from_extension(extension: str) -> FileType:
    for file_type, extensions in FILE_EXTENSIONS.items():
        if extension.lower() in extensions:
            return file_type

    raise ValueError(f"Unknown file type for extension: {extension}")


def get_file_extension_for_file_type(file_type: FileType) -> str:
    return FILE_EXTENSIONS[file_type][0]


def get_file_mime_type_for_file_type(file_type: FileType) -> str:
    return FILE_MIME_TYPES[file_type]


def get_file_mime_type_from_extension(extension: str) -> str:
    file_type = get_file_type_from_extension(extension)
    return get_file_mime_type_for_file_type(file_type)


"""
FileType Type Groupings (Videos, Images, etc)
"""

# Images
IMAGE_FILE_TYPES = {
    FileType.PNG,
    FileType.JPEG,
    FileType.GIF,
    FileType.WEBP,
    FileType.HEIC,
    FileType.HEIF,
}


def is_image_file_type(file_type):
    return file_type in IMAGE_FILE_TYPES


# Videos
VIDEO_FILE_TYPES = {
    FileType.MOV,
    FileType.MP4,
    FileType.MPEG,
    FileType.M4V,
    FileType.FLV,
    FileType.MPEGPS,
    FileType.MPG,
    FileType.WEBM,
    FileType.WMV,
    FileType.THREE_GPP,
}


def is_video_file_type(file_type):
    return file_type in VIDEO_FILE_TYPES


# Audio
AUDIO_FILE_TYPES = {
    FileType.AAC,
    FileType.FLAC,
    FileType.MP3,
    FileType.MPA,
    FileType.MPGA,
    FileType.OPUS,
    FileType.PCM,
    FileType.WAV,
}


def is_audio_file_type(file_type):
    return file_type in AUDIO_FILE_TYPES


# Text
TEXT_FILE_TYPES = {FileType.CSV, FileType.HTML, FileType.RTF, FileType.TXT}


def is_text_file_type(file_type):
    return file_type in TEXT_FILE_TYPES


"""
Other FileType Groupings
"""
# Accepted file types for GEMINI 1.5 through Vertex AI
# https://cloud.google.com/vertex-ai/generative-ai/docs/multimodal/send-multimodal-prompts#gemini-send-multimodal-samples-images-nodejs
GEMINI_1_5_ACCEPTED_FILE_TYPES: Set[FileType] = {
    # Image
    FileType.PNG,
    FileType.JPEG,
    FileType.WEBP,
    # Audio
    FileType.AAC,
    FileType.FLAC,
    FileType.MP3,
    FileType.MPA,
    FileType.MPEG,
    FileType.MPGA,
    FileType.OPUS,
    FileType.PCM,
    FileType.WAV,
    FileType.WEBM,
    # Video
    FileType.FLV,
    FileType.MOV,
    FileType.MPEG,
    FileType.MPEGPS,
    FileType.MPG,
    FileType.MP4,
    FileType.WEBM,
    FileType.WMV,
    FileType.THREE_GPP,
    # PDF
    FileType.PDF,
    FileType.TXT,
}


def is_gemini_1_5_accepted_file_type(file_type: FileType) -> bool:
    return file_type in GEMINI_1_5_ACCEPTED_FILE_TYPES

# === NexusCore/openenv\Lib\site-packages\litellm\llms\azure\files\handler.py ===
from typing import Any, Coroutine, Optional, Union, cast

import httpx
from openai import AsyncAzureOpenAI, AzureOpenAI
from openai.types.file_deleted import FileDeleted

from litellm._logging import verbose_logger
from litellm.types.llms.openai import *

from ..common_utils import BaseAzureLLM


class AzureOpenAIFilesAPI(BaseAzureLLM):
    """
    AzureOpenAI methods to support for batches
    - create_file()
    - retrieve_file()
    - list_files()
    - delete_file()
    - file_content()
    - update_file()
    """

    def __init__(self) -> None:
        super().__init__()

    async def acreate_file(
        self,
        create_file_data: CreateFileRequest,
        openai_client: AsyncAzureOpenAI,
    ) -> OpenAIFileObject:
        verbose_logger.debug("create_file_data=%s", create_file_data)
        response = await openai_client.files.create(**create_file_data)
        verbose_logger.debug("create_file_response=%s", response)
        return OpenAIFileObject(**response.model_dump())

    def create_file(
        self,
        _is_async: bool,
        create_file_data: CreateFileRequest,
        api_base: Optional[str],
        api_key: Optional[str],
        api_version: Optional[str],
        timeout: Union[float, httpx.Timeout],
        max_retries: Optional[int],
        client: Optional[Union[AzureOpenAI, AsyncAzureOpenAI]] = None,
        litellm_params: Optional[dict] = None,
    ) -> Union[OpenAIFileObject, Coroutine[Any, Any, OpenAIFileObject]]:
        openai_client: Optional[
            Union[AzureOpenAI, AsyncAzureOpenAI]
        ] = self.get_azure_openai_client(
            litellm_params=litellm_params or {},
            api_key=api_key,
            api_base=api_base,
            api_version=api_version,
            client=client,
            _is_async=_is_async,
        )
        if openai_client is None:
            raise ValueError(
                "AzureOpenAI client is not initialized. Make sure api_key is passed or OPENAI_API_KEY is set in the environment."
            )

        if _is_async is True:
            if not isinstance(openai_client, AsyncAzureOpenAI):
                raise ValueError(
                    "AzureOpenAI client is not an instance of AsyncAzureOpenAI. Make sure you passed an AsyncAzureOpenAI client."
                )
            return self.acreate_file(
                create_file_data=create_file_data, openai_client=openai_client
            )
        response = cast(AzureOpenAI, openai_client).files.create(**create_file_data)
        return OpenAIFileObject(**response.model_dump())

    async def afile_content(
        self,
        file_content_request: FileContentRequest,
        openai_client: AsyncAzureOpenAI,
    ) -> HttpxBinaryResponseContent:
        response = await openai_client.files.content(**file_content_request)
        return HttpxBinaryResponseContent(response=response.response)

    def file_content(
        self,
        _is_async: bool,
        file_content_request: FileContentRequest,
        api_base: Optional[str],
        api_key: Optional[str],
        timeout: Union[float, httpx.Timeout],
        max_retries: Optional[int],
        api_version: Optional[str] = None,
        client: Optional[Union[AzureOpenAI, AsyncAzureOpenAI]] = None,
        litellm_params: Optional[dict] = None,
    ) -> Union[
        HttpxBinaryResponseContent, Coroutine[Any, Any, HttpxBinaryResponseContent]
    ]:
        openai_client: Optional[
            Union[AzureOpenAI, AsyncAzureOpenAI]
        ] = self.get_azure_openai_client(
            litellm_params=litellm_params or {},
            api_key=api_key,
            api_base=api_base,
            api_version=api_version,
            client=client,
            _is_async=_is_async,
        )
        if openai_client is None:
            raise ValueError(
                "AzureOpenAI client is not initialized. Make sure api_key is passed or OPENAI_API_KEY is set in the environment."
            )

        if _is_async is True:
            if not isinstance(openai_client, AsyncAzureOpenAI):
                raise ValueError(
                    "AzureOpenAI client is not an instance of AsyncAzureOpenAI. Make sure you passed an AsyncAzureOpenAI client."
                )
            return self.afile_content(  # type: ignore
                file_content_request=file_content_request,
                openai_client=openai_client,
            )
        response = cast(AzureOpenAI, openai_client).files.content(
            **file_content_request
        )

        return HttpxBinaryResponseContent(response=response.response)

    async def aretrieve_file(
        self,
        file_id: str,
        openai_client: AsyncAzureOpenAI,
    ) -> FileObject:
        response = await openai_client.files.retrieve(file_id=file_id)
        return response

    def retrieve_file(
        self,
        _is_async: bool,
        file_id: str,
        api_base: Optional[str],
        api_key: Optional[str],
        timeout: Union[float, httpx.Timeout],
        max_retries: Optional[int],
        api_version: Optional[str] = None,
        client: Optional[Union[AzureOpenAI, AsyncAzureOpenAI]] = None,
        litellm_params: Optional[dict] = None,
    ):
        openai_client: Optional[
            Union[AzureOpenAI, AsyncAzureOpenAI]
        ] = self.get_azure_openai_client(
            litellm_params=litellm_params or {},
            api_key=api_key,
            api_base=api_base,
            api_version=api_version,
            client=client,
            _is_async=_is_async,
        )
        if openai_client is None:
            raise ValueError(
                "AzureOpenAI client is not initialized. Make sure api_key is passed or OPENAI_API_KEY is set in the environment."
            )

        if _is_async is True:
            if not isinstance(openai_client, AsyncAzureOpenAI):
                raise ValueError(
                    "AzureOpenAI client is not an instance of AsyncAzureOpenAI. Make sure you passed an AsyncAzureOpenAI client."
                )
            return self.aretrieve_file(  # type: ignore
                file_id=file_id,
                openai_client=openai_client,
            )
        response = openai_client.files.retrieve(file_id=file_id)

        return response

    async def adelete_file(
        self,
        file_id: str,
        openai_client: AsyncAzureOpenAI,
    ) -> FileDeleted:
        response = await openai_client.files.delete(file_id=file_id)

        if not isinstance(response, FileDeleted):  # azure returns an empty string
            return FileDeleted(id=file_id, deleted=True, object="file")
        return response

    def delete_file(
        self,
        _is_async: bool,
        file_id: str,
        api_base: Optional[str],
        api_key: Optional[str],
        timeout: Union[float, httpx.Timeout],
        max_retries: Optional[int],
        organization: Optional[str] = None,
        api_version: Optional[str] = None,
        client: Optional[Union[AzureOpenAI, AsyncAzureOpenAI]] = None,
        litellm_params: Optional[dict] = None,
    ):
        openai_client: Optional[
            Union[AzureOpenAI, AsyncAzureOpenAI]
        ] = self.get_azure_openai_client(
            litellm_params=litellm_params or {},
            api_key=api_key,
            api_base=api_base,
            api_version=api_version,
            client=client,
            _is_async=_is_async,
        )
        if openai_client is None:
            raise ValueError(
                "AzureOpenAI client is not initialized. Make sure api_key is passed or OPENAI_API_KEY is set in the environment."
            )

        if _is_async is True:
            if not isinstance(openai_client, AsyncAzureOpenAI):
                raise ValueError(
                    "AzureOpenAI client is not an instance of AsyncAzureOpenAI. Make sure you passed an AsyncAzureOpenAI client."
                )
            return self.adelete_file(  # type: ignore
                file_id=file_id,
                openai_client=openai_client,
            )
        response = openai_client.files.delete(file_id=file_id)

        if not isinstance(response, FileDeleted):  # azure returns an empty string
            return FileDeleted(id=file_id, deleted=True, object="file")

        return response

    async def alist_files(
        self,
        openai_client: AsyncAzureOpenAI,
        purpose: Optional[str] = None,
    ):
        if isinstance(purpose, str):
            response = await openai_client.files.list(purpose=purpose)
        else:
            response = await openai_client.files.list()
        return response

    def list_files(
        self,
        _is_async: bool,
        api_base: Optional[str],
        api_key: Optional[str],
        timeout: Union[float, httpx.Timeout],
        max_retries: Optional[int],
        purpose: Optional[str] = None,
        api_version: Optional[str] = None,
        client: Optional[Union[AzureOpenAI, AsyncAzureOpenAI]] = None,
        litellm_params: Optional[dict] = None,
    ):
        openai_client: Optional[
            Union[AzureOpenAI, AsyncAzureOpenAI]
        ] = self.get_azure_openai_client(
            litellm_params=litellm_params or {},
            api_key=api_key,
            api_base=api_base,
            api_version=api_version,
            client=client,
            _is_async=_is_async,
        )
        if openai_client is None:
            raise ValueError(
                "AzureOpenAI client is not initialized. Make sure api_key is passed or OPENAI_API_KEY is set in the environment."
            )

        if _is_async is True:
            if not isinstance(openai_client, AsyncAzureOpenAI):
                raise ValueError(
                    "AzureOpenAI client is not an instance of AsyncAzureOpenAI. Make sure you passed an AsyncAzureOpenAI client."
                )
            return self.alist_files(  # type: ignore
                purpose=purpose,
                openai_client=openai_client,
            )

        if isinstance(purpose, str):
            response = openai_client.files.list(purpose=purpose)
        else:
            response = openai_client.files.list()

        return response

# === NexusCore/openenv\Lib\site-packages\selenium\webdriver\common\devtools\v135\autofill.py ===
# DO NOT EDIT THIS FILE!
#
# This file is generated from the CDP specification. If you need to make
# changes, edit the generator and regenerate all of the modules.
#
# CDP domain: Autofill (experimental)
from __future__ import annotations
from .util import event_class, T_JSON_DICT
from dataclasses import dataclass
import enum
import typing
from . import dom
from . import page


@dataclass
class CreditCard:
    #: 16-digit credit card number.
    number: str

    #: Name of the credit card owner.
    name: str

    #: 2-digit expiry month.
    expiry_month: str

    #: 4-digit expiry year.
    expiry_year: str

    #: 3-digit card verification code.
    cvc: str

    def to_json(self):
        json = dict()
        json['number'] = self.number
        json['name'] = self.name
        json['expiryMonth'] = self.expiry_month
        json['expiryYear'] = self.expiry_year
        json['cvc'] = self.cvc
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            number=str(json['number']),
            name=str(json['name']),
            expiry_month=str(json['expiryMonth']),
            expiry_year=str(json['expiryYear']),
            cvc=str(json['cvc']),
        )


@dataclass
class AddressField:
    #: address field name, for example GIVEN_NAME.
    name: str

    #: address field value, for example Jon Doe.
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
class AddressFields:
    '''
    A list of address fields.
    '''
    fields: typing.List[AddressField]

    def to_json(self):
        json = dict()
        json['fields'] = [i.to_json() for i in self.fields]
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            fields=[AddressField.from_json(i) for i in json['fields']],
        )


@dataclass
class Address:
    #: fields and values defining an address.
    fields: typing.List[AddressField]

    def to_json(self):
        json = dict()
        json['fields'] = [i.to_json() for i in self.fields]
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            fields=[AddressField.from_json(i) for i in json['fields']],
        )


@dataclass
class AddressUI:
    '''
    Defines how an address can be displayed like in chrome://settings/addresses.
    Address UI is a two dimensional array, each inner array is an "address information line", and when rendered in a UI surface should be displayed as such.
    The following address UI for instance:
    [[{name: "GIVE_NAME", value: "Jon"}, {name: "FAMILY_NAME", value: "Doe"}], [{name: "CITY", value: "Munich"}, {name: "ZIP", value: "81456"}]]
    should allow the receiver to render:
    Jon Doe
    Munich 81456
    '''
    #: A two dimension array containing the representation of values from an address profile.
    address_fields: typing.List[AddressFields]

    def to_json(self):
        json = dict()
        json['addressFields'] = [i.to_json() for i in self.address_fields]
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            address_fields=[AddressFields.from_json(i) for i in json['addressFields']],
        )


class FillingStrategy(enum.Enum):
    '''
    Specified whether a filled field was done so by using the html autocomplete attribute or autofill heuristics.
    '''
    AUTOCOMPLETE_ATTRIBUTE = "autocompleteAttribute"
    AUTOFILL_INFERRED = "autofillInferred"

    def to_json(self):
        return self.value

    @classmethod
    def from_json(cls, json):
        return cls(json)


@dataclass
class FilledField:
    #: The type of the field, e.g text, password etc.
    html_type: str

    #: the html id
    id_: str

    #: the html name
    name: str

    #: the field value
    value: str

    #: The actual field type, e.g FAMILY_NAME
    autofill_type: str

    #: The filling strategy
    filling_strategy: FillingStrategy

    #: The frame the field belongs to
    frame_id: page.FrameId

    #: The form field's DOM node
    field_id: dom.BackendNodeId

    def to_json(self):
        json = dict()
        json['htmlType'] = self.html_type
        json['id'] = self.id_
        json['name'] = self.name
        json['value'] = self.value
        json['autofillType'] = self.autofill_type
        json['fillingStrategy'] = self.filling_strategy.to_json()
        json['frameId'] = self.frame_id.to_json()
        json['fieldId'] = self.field_id.to_json()
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            html_type=str(json['htmlType']),
            id_=str(json['id']),
            name=str(json['name']),
            value=str(json['value']),
            autofill_type=str(json['autofillType']),
            filling_strategy=FillingStrategy.from_json(json['fillingStrategy']),
            frame_id=page.FrameId.from_json(json['frameId']),
            field_id=dom.BackendNodeId.from_json(json['fieldId']),
        )


def trigger(
        field_id: dom.BackendNodeId,
        frame_id: typing.Optional[page.FrameId] = None,
        card: CreditCard = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Trigger autofill on a form identified by the fieldId.
    If the field and related form cannot be autofilled, returns an error.

    :param field_id: Identifies a field that serves as an anchor for autofill.
    :param frame_id: *(Optional)* Identifies the frame that field belongs to.
    :param card: Credit card information to fill out the form. Credit card data is not saved.
    '''
    params: T_JSON_DICT = dict()
    params['fieldId'] = field_id.to_json()
    if frame_id is not None:
        params['frameId'] = frame_id.to_json()
    params['card'] = card.to_json()
    cmd_dict: T_JSON_DICT = {
        'method': 'Autofill.trigger',
        'params': params,
    }
    json = yield cmd_dict


def set_addresses(
        addresses: typing.List[Address]
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Set addresses so that developers can verify their forms implementation.

    :param addresses:
    '''
    params: T_JSON_DICT = dict()
    params['addresses'] = [i.to_json() for i in addresses]
    cmd_dict: T_JSON_DICT = {
        'method': 'Autofill.setAddresses',
        'params': params,
    }
    json = yield cmd_dict


def disable() -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Disables autofill domain notifications.
    '''
    cmd_dict: T_JSON_DICT = {
        'method': 'Autofill.disable',
    }
    json = yield cmd_dict


def enable() -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Enables autofill domain notifications.
    '''
    cmd_dict: T_JSON_DICT = {
        'method': 'Autofill.enable',
    }
    json = yield cmd_dict


@event_class('Autofill.addressFormFilled')
@dataclass
class AddressFormFilled:
    '''
    Emitted when an address form is filled.
    '''
    #: Information about the fields that were filled
    filled_fields: typing.List[FilledField]
    #: An UI representation of the address used to fill the form.
    #: Consists of a 2D array where each child represents an address/profile line.
    address_ui: AddressUI

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> AddressFormFilled:
        return cls(
            filled_fields=[FilledField.from_json(i) for i in json['filledFields']],
            address_ui=AddressUI.from_json(json['addressUi'])
        )

# === NexusCore/openenv\Lib\site-packages\selenium\webdriver\common\devtools\v136\autofill.py ===
# DO NOT EDIT THIS FILE!
#
# This file is generated from the CDP specification. If you need to make
# changes, edit the generator and regenerate all of the modules.
#
# CDP domain: Autofill (experimental)
from __future__ import annotations
from .util import event_class, T_JSON_DICT
from dataclasses import dataclass
import enum
import typing
from . import dom
from . import page


@dataclass
class CreditCard:
    #: 16-digit credit card number.
    number: str

    #: Name of the credit card owner.
    name: str

    #: 2-digit expiry month.
    expiry_month: str

    #: 4-digit expiry year.
    expiry_year: str

    #: 3-digit card verification code.
    cvc: str

    def to_json(self):
        json = dict()
        json['number'] = self.number
        json['name'] = self.name
        json['expiryMonth'] = self.expiry_month
        json['expiryYear'] = self.expiry_year
        json['cvc'] = self.cvc
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            number=str(json['number']),
            name=str(json['name']),
            expiry_month=str(json['expiryMonth']),
            expiry_year=str(json['expiryYear']),
            cvc=str(json['cvc']),
        )


@dataclass
class AddressField:
    #: address field name, for example GIVEN_NAME.
    name: str

    #: address field value, for example Jon Doe.
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
class AddressFields:
    '''
    A list of address fields.
    '''
    fields: typing.List[AddressField]

    def to_json(self):
        json = dict()
        json['fields'] = [i.to_json() for i in self.fields]
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            fields=[AddressField.from_json(i) for i in json['fields']],
        )


@dataclass
class Address:
    #: fields and values defining an address.
    fields: typing.List[AddressField]

    def to_json(self):
        json = dict()
        json['fields'] = [i.to_json() for i in self.fields]
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            fields=[AddressField.from_json(i) for i in json['fields']],
        )


@dataclass
class AddressUI:
    '''
    Defines how an address can be displayed like in chrome://settings/addresses.
    Address UI is a two dimensional array, each inner array is an "address information line", and when rendered in a UI surface should be displayed as such.
    The following address UI for instance:
    [[{name: "GIVE_NAME", value: "Jon"}, {name: "FAMILY_NAME", value: "Doe"}], [{name: "CITY", value: "Munich"}, {name: "ZIP", value: "81456"}]]
    should allow the receiver to render:
    Jon Doe
    Munich 81456
    '''
    #: A two dimension array containing the representation of values from an address profile.
    address_fields: typing.List[AddressFields]

    def to_json(self):
        json = dict()
        json['addressFields'] = [i.to_json() for i in self.address_fields]
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            address_fields=[AddressFields.from_json(i) for i in json['addressFields']],
        )


class FillingStrategy(enum.Enum):
    '''
    Specified whether a filled field was done so by using the html autocomplete attribute or autofill heuristics.
    '''
    AUTOCOMPLETE_ATTRIBUTE = "autocompleteAttribute"
    AUTOFILL_INFERRED = "autofillInferred"

    def to_json(self):
        return self.value

    @classmethod
    def from_json(cls, json):
        return cls(json)


@dataclass
class FilledField:
    #: The type of the field, e.g text, password etc.
    html_type: str

    #: the html id
    id_: str

    #: the html name
    name: str

    #: the field value
    value: str

    #: The actual field type, e.g FAMILY_NAME
    autofill_type: str

    #: The filling strategy
    filling_strategy: FillingStrategy

    #: The frame the field belongs to
    frame_id: page.FrameId

    #: The form field's DOM node
    field_id: dom.BackendNodeId

    def to_json(self):
        json = dict()
        json['htmlType'] = self.html_type
        json['id'] = self.id_
        json['name'] = self.name
        json['value'] = self.value
        json['autofillType'] = self.autofill_type
        json['fillingStrategy'] = self.filling_strategy.to_json()
        json['frameId'] = self.frame_id.to_json()
        json['fieldId'] = self.field_id.to_json()
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            html_type=str(json['htmlType']),
            id_=str(json['id']),
            name=str(json['name']),
            value=str(json['value']),
            autofill_type=str(json['autofillType']),
            filling_strategy=FillingStrategy.from_json(json['fillingStrategy']),
            frame_id=page.FrameId.from_json(json['frameId']),
            field_id=dom.BackendNodeId.from_json(json['fieldId']),
        )


def trigger(
        field_id: dom.BackendNodeId,
        frame_id: typing.Optional[page.FrameId] = None,
        card: CreditCard = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Trigger autofill on a form identified by the fieldId.
    If the field and related form cannot be autofilled, returns an error.

    :param field_id: Identifies a field that serves as an anchor for autofill.
    :param frame_id: *(Optional)* Identifies the frame that field belongs to.
    :param card: Credit card information to fill out the form. Credit card data is not saved.
    '''
    params: T_JSON_DICT = dict()
    params['fieldId'] = field_id.to_json()
    if frame_id is not None:
        params['frameId'] = frame_id.to_json()
    params['card'] = card.to_json()
    cmd_dict: T_JSON_DICT = {
        'method': 'Autofill.trigger',
        'params': params,
    }
    json = yield cmd_dict


def set_addresses(
        addresses: typing.List[Address]
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Set addresses so that developers can verify their forms implementation.

    :param addresses:
    '''
    params: T_JSON_DICT = dict()
    params['addresses'] = [i.to_json() for i in addresses]
    cmd_dict: T_JSON_DICT = {
        'method': 'Autofill.setAddresses',
        'params': params,
    }
    json = yield cmd_dict


def disable() -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Disables autofill domain notifications.
    '''
    cmd_dict: T_JSON_DICT = {
        'method': 'Autofill.disable',
    }
    json = yield cmd_dict


def enable() -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Enables autofill domain notifications.
    '''
    cmd_dict: T_JSON_DICT = {
        'method': 'Autofill.enable',
    }
    json = yield cmd_dict


@event_class('Autofill.addressFormFilled')
@dataclass
class AddressFormFilled:
    '''
    Emitted when an address form is filled.
    '''
    #: Information about the fields that were filled
    filled_fields: typing.List[FilledField]
    #: An UI representation of the address used to fill the form.
    #: Consists of a 2D array where each child represents an address/profile line.
    address_ui: AddressUI

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> AddressFormFilled:
        return cls(
            filled_fields=[FilledField.from_json(i) for i in json['filledFields']],
            address_ui=AddressUI.from_json(json['addressUi'])
        )

# === NexusCore/openenv\Lib\site-packages\selenium\webdriver\common\devtools\v137\autofill.py ===
# DO NOT EDIT THIS FILE!
#
# This file is generated from the CDP specification. If you need to make
# changes, edit the generator and regenerate all of the modules.
#
# CDP domain: Autofill (experimental)
from __future__ import annotations
from .util import event_class, T_JSON_DICT
from dataclasses import dataclass
import enum
import typing
from . import dom
from . import page


@dataclass
class CreditCard:
    #: 16-digit credit card number.
    number: str

    #: Name of the credit card owner.
    name: str

    #: 2-digit expiry month.
    expiry_month: str

    #: 4-digit expiry year.
    expiry_year: str

    #: 3-digit card verification code.
    cvc: str

    def to_json(self):
        json = dict()
        json['number'] = self.number
        json['name'] = self.name
        json['expiryMonth'] = self.expiry_month
        json['expiryYear'] = self.expiry_year
        json['cvc'] = self.cvc
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            number=str(json['number']),
            name=str(json['name']),
            expiry_month=str(json['expiryMonth']),
            expiry_year=str(json['expiryYear']),
            cvc=str(json['cvc']),
        )


@dataclass
class AddressField:
    #: address field name, for example GIVEN_NAME.
    name: str

    #: address field value, for example Jon Doe.
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
class AddressFields:
    '''
    A list of address fields.
    '''
    fields: typing.List[AddressField]

    def to_json(self):
        json = dict()
        json['fields'] = [i.to_json() for i in self.fields]
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            fields=[AddressField.from_json(i) for i in json['fields']],
        )


@dataclass
class Address:
    #: fields and values defining an address.
    fields: typing.List[AddressField]

    def to_json(self):
        json = dict()
        json['fields'] = [i.to_json() for i in self.fields]
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            fields=[AddressField.from_json(i) for i in json['fields']],
        )


@dataclass
class AddressUI:
    '''
    Defines how an address can be displayed like in chrome://settings/addresses.
    Address UI is a two dimensional array, each inner array is an "address information line", and when rendered in a UI surface should be displayed as such.
    The following address UI for instance:
    [[{name: "GIVE_NAME", value: "Jon"}, {name: "FAMILY_NAME", value: "Doe"}], [{name: "CITY", value: "Munich"}, {name: "ZIP", value: "81456"}]]
    should allow the receiver to render:
    Jon Doe
    Munich 81456
    '''
    #: A two dimension array containing the representation of values from an address profile.
    address_fields: typing.List[AddressFields]

    def to_json(self):
        json = dict()
        json['addressFields'] = [i.to_json() for i in self.address_fields]
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            address_fields=[AddressFields.from_json(i) for i in json['addressFields']],
        )


class FillingStrategy(enum.Enum):
    '''
    Specified whether a filled field was done so by using the html autocomplete attribute or autofill heuristics.
    '''
    AUTOCOMPLETE_ATTRIBUTE = "autocompleteAttribute"
    AUTOFILL_INFERRED = "autofillInferred"

    def to_json(self):
        return self.value

    @classmethod
    def from_json(cls, json):
        return cls(json)


@dataclass
class FilledField:
    #: The type of the field, e.g text, password etc.
    html_type: str

    #: the html id
    id_: str

    #: the html name
    name: str

    #: the field value
    value: str

    #: The actual field type, e.g FAMILY_NAME
    autofill_type: str

    #: The filling strategy
    filling_strategy: FillingStrategy

    #: The frame the field belongs to
    frame_id: page.FrameId

    #: The form field's DOM node
    field_id: dom.BackendNodeId

    def to_json(self):
        json = dict()
        json['htmlType'] = self.html_type
        json['id'] = self.id_
        json['name'] = self.name
        json['value'] = self.value
        json['autofillType'] = self.autofill_type
        json['fillingStrategy'] = self.filling_strategy.to_json()
        json['frameId'] = self.frame_id.to_json()
        json['fieldId'] = self.field_id.to_json()
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            html_type=str(json['htmlType']),
            id_=str(json['id']),
            name=str(json['name']),
            value=str(json['value']),
            autofill_type=str(json['autofillType']),
            filling_strategy=FillingStrategy.from_json(json['fillingStrategy']),
            frame_id=page.FrameId.from_json(json['frameId']),
            field_id=dom.BackendNodeId.from_json(json['fieldId']),
        )


def trigger(
        field_id: dom.BackendNodeId,
        frame_id: typing.Optional[page.FrameId] = None,
        card: CreditCard = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Trigger autofill on a form identified by the fieldId.
    If the field and related form cannot be autofilled, returns an error.

    :param field_id: Identifies a field that serves as an anchor for autofill.
    :param frame_id: *(Optional)* Identifies the frame that field belongs to.
    :param card: Credit card information to fill out the form. Credit card data is not saved.
    '''
    params: T_JSON_DICT = dict()
    params['fieldId'] = field_id.to_json()
    if frame_id is not None:
        params['frameId'] = frame_id.to_json()
    params['card'] = card.to_json()
    cmd_dict: T_JSON_DICT = {
        'method': 'Autofill.trigger',
        'params': params,
    }
    json = yield cmd_dict


def set_addresses(
        addresses: typing.List[Address]
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Set addresses so that developers can verify their forms implementation.

    :param addresses:
    '''
    params: T_JSON_DICT = dict()
    params['addresses'] = [i.to_json() for i in addresses]
    cmd_dict: T_JSON_DICT = {
        'method': 'Autofill.setAddresses',
        'params': params,
    }
    json = yield cmd_dict


def disable() -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Disables autofill domain notifications.
    '''
    cmd_dict: T_JSON_DICT = {
        'method': 'Autofill.disable',
    }
    json = yield cmd_dict


def enable() -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Enables autofill domain notifications.
    '''
    cmd_dict: T_JSON_DICT = {
        'method': 'Autofill.enable',
    }
    json = yield cmd_dict


@event_class('Autofill.addressFormFilled')
@dataclass
class AddressFormFilled:
    '''
    Emitted when an address form is filled.
    '''
    #: Information about the fields that were filled
    filled_fields: typing.List[FilledField]
    #: An UI representation of the address used to fill the form.
    #: Consists of a 2D array where each child represents an address/profile line.
    address_ui: AddressUI

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> AddressFormFilled:
        return cls(
            filled_fields=[FilledField.from_json(i) for i in json['filledFields']],
            address_ui=AddressUI.from_json(json['addressUi'])
        )

# === NexusCore/openenv\Lib\site-packages\h11\_headers.py ===
import re
from typing import AnyStr, cast, List, overload, Sequence, Tuple, TYPE_CHECKING, Union

from ._abnf import field_name, field_value
from ._util import bytesify, LocalProtocolError, validate

if TYPE_CHECKING:
    from ._events import Request

try:
    from typing import Literal
except ImportError:
    from typing_extensions import Literal  # type: ignore

CONTENT_LENGTH_MAX_DIGITS = 20  # allow up to 1 billion TB - 1


# Facts
# -----
#
# Headers are:
#   keys: case-insensitive ascii
#   values: mixture of ascii and raw bytes
#
# "Historically, HTTP has allowed field content with text in the ISO-8859-1
# charset [ISO-8859-1], supporting other charsets only through use of
# [RFC2047] encoding.  In practice, most HTTP header field values use only a
# subset of the US-ASCII charset [USASCII]. Newly defined header fields SHOULD
# limit their field values to US-ASCII octets.  A recipient SHOULD treat other
# octets in field content (obs-text) as opaque data."
# And it deprecates all non-ascii values
#
# Leading/trailing whitespace in header names is forbidden
#
# Values get leading/trailing whitespace stripped
#
# Content-Disposition actually needs to contain unicode semantically; to
# accomplish this it has a terrifically weird way of encoding the filename
# itself as ascii (and even this still has lots of cross-browser
# incompatibilities)
#
# Order is important:
# "a proxy MUST NOT change the order of these field values when forwarding a
# message"
# (and there are several headers where the order indicates a preference)
#
# Multiple occurences of the same header:
# "A sender MUST NOT generate multiple header fields with the same field name
# in a message unless either the entire field value for that header field is
# defined as a comma-separated list [or the header is Set-Cookie which gets a
# special exception]" - RFC 7230. (cookies are in RFC 6265)
#
# So every header aside from Set-Cookie can be merged by b", ".join if it
# occurs repeatedly. But, of course, they can't necessarily be split by
# .split(b","), because quoting.
#
# Given all this mess (case insensitive, duplicates allowed, order is
# important, ...), there doesn't appear to be any standard way to handle
# headers in Python -- they're almost like dicts, but... actually just
# aren't. For now we punt and just use a super simple representation: headers
# are a list of pairs
#
#   [(name1, value1), (name2, value2), ...]
#
# where all entries are bytestrings, names are lowercase and have no
# leading/trailing whitespace, and values are bytestrings with no
# leading/trailing whitespace. Searching and updating are done via naive O(n)
# methods.
#
# Maybe a dict-of-lists would be better?

_content_length_re = re.compile(rb"[0-9]+")
_field_name_re = re.compile(field_name.encode("ascii"))
_field_value_re = re.compile(field_value.encode("ascii"))


class Headers(Sequence[Tuple[bytes, bytes]]):
    """
    A list-like interface that allows iterating over headers as byte-pairs
    of (lowercased-name, value).

    Internally we actually store the representation as three-tuples,
    including both the raw original casing, in order to preserve casing
    over-the-wire, and the lowercased name, for case-insensitive comparisions.

    r = Request(
        method="GET",
        target="/",
        headers=[("Host", "example.org"), ("Connection", "keep-alive")],
        http_version="1.1",
    )
    assert r.headers == [
        (b"host", b"example.org"),
        (b"connection", b"keep-alive")
    ]
    assert r.headers.raw_items() == [
        (b"Host", b"example.org"),
        (b"Connection", b"keep-alive")
    ]
    """

    __slots__ = "_full_items"

    def __init__(self, full_items: List[Tuple[bytes, bytes, bytes]]) -> None:
        self._full_items = full_items

    def __bool__(self) -> bool:
        return bool(self._full_items)

    def __eq__(self, other: object) -> bool:
        return list(self) == list(other)  # type: ignore

    def __len__(self) -> int:
        return len(self._full_items)

    def __repr__(self) -> str:
        return "<Headers(%s)>" % repr(list(self))

    def __getitem__(self, idx: int) -> Tuple[bytes, bytes]:  # type: ignore[override]
        _, name, value = self._full_items[idx]
        return (name, value)

    def raw_items(self) -> List[Tuple[bytes, bytes]]:
        return [(raw_name, value) for raw_name, _, value in self._full_items]


HeaderTypes = Union[
    List[Tuple[bytes, bytes]],
    List[Tuple[bytes, str]],
    List[Tuple[str, bytes]],
    List[Tuple[str, str]],
]


@overload
def normalize_and_validate(headers: Headers, _parsed: Literal[True]) -> Headers:
    ...


@overload
def normalize_and_validate(headers: HeaderTypes, _parsed: Literal[False]) -> Headers:
    ...


@overload
def normalize_and_validate(
    headers: Union[Headers, HeaderTypes], _parsed: bool = False
) -> Headers:
    ...


def normalize_and_validate(
    headers: Union[Headers, HeaderTypes], _parsed: bool = False
) -> Headers:
    new_headers = []
    seen_content_length = None
    saw_transfer_encoding = False
    for name, value in headers:
        # For headers coming out of the parser, we can safely skip some steps,
        # because it always returns bytes and has already run these regexes
        # over the data:
        if not _parsed:
            name = bytesify(name)
            value = bytesify(value)
            validate(_field_name_re, name, "Illegal header name {!r}", name)
            validate(_field_value_re, value, "Illegal header value {!r}", value)
        assert isinstance(name, bytes)
        assert isinstance(value, bytes)

        raw_name = name
        name = name.lower()
        if name == b"content-length":
            lengths = {length.strip() for length in value.split(b",")}
            if len(lengths) != 1:
                raise LocalProtocolError("conflicting Content-Length headers")
            value = lengths.pop()
            validate(_content_length_re, value, "bad Content-Length")
            if len(value) > CONTENT_LENGTH_MAX_DIGITS:
                raise LocalProtocolError("bad Content-Length")
            if seen_content_length is None:
                seen_content_length = value
                new_headers.append((raw_name, name, value))
            elif seen_content_length != value:
                raise LocalProtocolError("conflicting Content-Length headers")
        elif name == b"transfer-encoding":
            # "A server that receives a request message with a transfer coding
            # it does not understand SHOULD respond with 501 (Not
            # Implemented)."
            # https://tools.ietf.org/html/rfc7230#section-3.3.1
            if saw_transfer_encoding:
                raise LocalProtocolError(
                    "multiple Transfer-Encoding headers", error_status_hint=501
                )
            # "All transfer-coding names are case-insensitive"
            # -- https://tools.ietf.org/html/rfc7230#section-4
            value = value.lower()
            if value != b"chunked":
                raise LocalProtocolError(
                    "Only Transfer-Encoding: chunked is supported",
                    error_status_hint=501,
                )
            saw_transfer_encoding = True
            new_headers.append((raw_name, name, value))
        else:
            new_headers.append((raw_name, name, value))
    return Headers(new_headers)


def get_comma_header(headers: Headers, name: bytes) -> List[bytes]:
    # Should only be used for headers whose value is a list of
    # comma-separated, case-insensitive values.
    #
    # The header name `name` is expected to be lower-case bytes.
    #
    # Connection: meets these criteria (including cast insensitivity).
    #
    # Content-Length: technically is just a single value (1*DIGIT), but the
    # standard makes reference to implementations that do multiple values, and
    # using this doesn't hurt. Ditto, case insensitivity doesn't things either
    # way.
    #
    # Transfer-Encoding: is more complex (allows for quoted strings), so
    # splitting on , is actually wrong. For example, this is legal:
    #
    #    Transfer-Encoding: foo; options="1,2", chunked
    #
    # and should be parsed as
    #
    #    foo; options="1,2"
    #    chunked
    #
    # but this naive function will parse it as
    #
    #    foo; options="1
    #    2"
    #    chunked
    #
    # However, this is okay because the only thing we are going to do with
    # any Transfer-Encoding is reject ones that aren't just "chunked", so
    # both of these will be treated the same anyway.
    #
    # Expect: the only legal value is the literal string
    # "100-continue". Splitting on commas is harmless. Case insensitive.
    #
    out: List[bytes] = []
    for _, found_name, found_raw_value in headers._full_items:
        if found_name == name:
            found_raw_value = found_raw_value.lower()
            for found_split_value in found_raw_value.split(b","):
                found_split_value = found_split_value.strip()
                if found_split_value:
                    out.append(found_split_value)
    return out


def set_comma_header(headers: Headers, name: bytes, new_values: List[bytes]) -> Headers:
    # The header name `name` is expected to be lower-case bytes.
    #
    # Note that when we store the header we use title casing for the header
    # names, in order to match the conventional HTTP header style.
    #
    # Simply calling `.title()` is a blunt approach, but it's correct
    # here given the cases where we're using `set_comma_header`...
    #
    # Connection, Content-Length, Transfer-Encoding.
    new_headers: List[Tuple[bytes, bytes]] = []
    for found_raw_name, found_name, found_raw_value in headers._full_items:
        if found_name != name:
            new_headers.append((found_raw_name, found_raw_value))
    for new_value in new_values:
        new_headers.append((name.title(), new_value))
    return normalize_and_validate(new_headers)


def has_expect_100_continue(request: "Request") -> bool:
    # https://tools.ietf.org/html/rfc7231#section-5.1.1
    # "A server that receives a 100-continue expectation in an HTTP/1.0 request
    # MUST ignore that expectation."
    if request.http_version < b"1.1":
        return False
    expect = get_comma_header(request.headers, b"expect")
    return b"100-continue" in expect

# === NexusCore/openenv\Lib\site-packages\jupyter_core\migrate.py ===
# PYTHON_ARGCOMPLETE_OK
"""Migrating IPython < 4.0 to Jupyter

This *copies* configuration and resources to their new locations in Jupyter

Migrations:

- .ipython/
  - nbextensions -> JUPYTER_DATA_DIR/nbextensions
  - kernels ->  JUPYTER_DATA_DIR/kernels

- .ipython/profile_default/
  - static/custom -> .jupyter/custom
  - nbconfig -> .jupyter/nbconfig
  - security/

    - notebook_secret, notebook_cookie_secret, nbsignatures.db -> JUPYTER_DATA_DIR

  - ipython_{notebook,nbconvert,qtconsole}_config.py -> .jupyter/jupyter_{name}_config.py


"""

# Copyright (c) Jupyter Development Team.
# Distributed under the terms of the Modified BSD License.
from __future__ import annotations

import os
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from traitlets.config.loader import JSONFileConfigLoader, PyFileConfigLoader
from traitlets.log import get_logger

from .application import JupyterApp
from .paths import jupyter_config_dir, jupyter_data_dir
from .utils import ensure_dir_exists

# mypy: disable-error-code="no-untyped-call"


migrations = {
    str(Path("{ipython_dir}", "nbextensions")): str(Path("{jupyter_data}", "nbextensions")),
    str(Path("{ipython_dir}", "kernels")): str(Path("{jupyter_data}", "kernels")),
    str(Path("{profile}", "nbconfig")): str(Path("{jupyter_config}", "nbconfig")),
}

custom_src_t = str(Path("{profile}", "static", "custom"))
custom_dst_t = str(Path("{jupyter_config}", "custom"))

for security_file in ("notebook_secret", "notebook_cookie_secret", "nbsignatures.db"):
    src = str(Path("{profile}", "security", security_file))
    dst = str(Path("{jupyter_data}", security_file))
    migrations[src] = dst

config_migrations = ["notebook", "nbconvert", "qtconsole"]

regex = re.compile

config_substitutions = {
    regex(r"\bIPythonQtConsoleApp\b"): "JupyterQtConsoleApp",
    regex(r"\bIPythonWidget\b"): "JupyterWidget",
    regex(r"\bRichIPythonWidget\b"): "RichJupyterWidget",
    regex(r"\bIPython\.html\b"): "notebook",
    regex(r"\bIPython\.nbconvert\b"): "nbconvert",
}


def get_ipython_dir() -> str:
    """Return the IPython directory location.

    Not imported from IPython because the IPython implementation
    ensures that a writable directory exists,
    creating a temporary directory if not.
    We don't want to trigger that when checking if migration should happen.

    We only need to support the IPython < 4 behavior for migration,
    so importing for forward-compatibility and edge cases is not important.
    """
    return os.environ.get("IPYTHONDIR", str(Path("~/.ipython").expanduser()))


def migrate_dir(src: str, dst: str) -> bool:
    """Migrate a directory from src to dst"""
    log = get_logger()
    src_path = Path(src)
    dst_path = Path(dst)
    if not any(src_path.iterdir()):
        log.debug("No files in %s", src)
        return False
    if dst_path.exists():
        if any(dst_path.iterdir()):
            # already exists, non-empty
            log.debug("%s already exists", dst)
            return False
        dst_path.rmdir()
    log.info("Copying %s -> %s", src, dst)
    ensure_dir_exists(dst_path.parent)
    shutil.copytree(src, dst, symlinks=True)
    return True


def migrate_file(src: str | Path, dst: str | Path, substitutions: Any = None) -> bool:
    """Migrate a single file from src to dst

    substitutions is an optional dict of {regex: replacement} for performing replacements on the file.
    """
    log = get_logger()
    dst_path = Path(dst)
    if dst_path.exists():
        # already exists
        log.debug("%s already exists", dst)
        return False
    log.info("Copying %s -> %s", src, dst)
    ensure_dir_exists(dst_path.parent)
    shutil.copy(src, dst)
    if substitutions:
        with dst_path.open() as f:
            text = f.read()
        for pat, replacement in substitutions.items():
            text = pat.sub(replacement, text)
        with dst_path.open("w") as f:
            f.write(text)
    return True


def migrate_one(src: str, dst: str) -> bool:
    """Migrate one item

    dispatches to migrate_dir/_file
    """
    log = get_logger()
    if Path(src).is_file():
        return migrate_file(src, dst)
    if Path(src).is_dir():
        return migrate_dir(src, dst)
    log.debug("Nothing to migrate for %s", src)
    return False


def migrate_static_custom(src: str, dst: str) -> bool:
    """Migrate non-empty custom.js,css from src to dst

    src, dst are 'custom' directories containing custom.{js,css}
    """
    log = get_logger()
    migrated = False

    custom_js = Path(src, "custom.js")
    custom_css = Path(src, "custom.css")
    # check if custom_js is empty:
    custom_js_empty = True
    if Path(custom_js).is_file():
        with Path.open(custom_js, encoding="utf-8") as f:
            js = f.read().strip()
            for line in js.splitlines():
                if not (line.isspace() or line.strip().startswith(("/*", "*", "//"))):
                    custom_js_empty = False
                    break

    # check if custom_css is empty:
    custom_css_empty = True
    if Path(custom_css).is_file():
        with Path.open(custom_css, encoding="utf-8") as f:
            css = f.read().strip()
            custom_css_empty = css.startswith("/*") and css.endswith("*/")

    if custom_js_empty:
        log.debug("Ignoring empty %s", custom_js)
    if custom_css_empty:
        log.debug("Ignoring empty %s", custom_css)

    if custom_js_empty and custom_css_empty:
        # nothing to migrate
        return False
    ensure_dir_exists(dst)

    if not custom_js_empty or not custom_css_empty:
        ensure_dir_exists(dst)

    if not custom_js_empty and migrate_file(custom_js, Path(dst, "custom.js")):
        migrated = True
    if not custom_css_empty and migrate_file(custom_css, Path(dst, "custom.css")):
        migrated = True

    return migrated


def migrate_config(name: str, env: Any) -> list[Any]:
    """Migrate a config file.

    Includes substitutions for updated configurable names.
    """
    log = get_logger()
    src_base = str(Path(f"{env['profile']}", f"ipython_{name}_config"))
    dst_base = str(Path(f"{env['jupyter_config']}", f"jupyter_{name}_config"))
    loaders = {
        ".py": PyFileConfigLoader,
        ".json": JSONFileConfigLoader,
    }
    migrated = []
    for ext in (".py", ".json"):
        src = src_base + ext
        dst = dst_base + ext
        if Path(src).exists():
            cfg = loaders[ext](src).load_config()
            if cfg:
                if migrate_file(src, dst, substitutions=config_substitutions):
                    migrated.append(src)
            else:
                # don't migrate empty config files
                log.debug("Not migrating empty config file: %s", src)
    return migrated


def migrate() -> bool:
    """Migrate IPython configuration to Jupyter"""
    env = {
        "jupyter_data": jupyter_data_dir(),
        "jupyter_config": jupyter_config_dir(),
        "ipython_dir": get_ipython_dir(),
        "profile": str(Path(get_ipython_dir(), "profile_default")),
    }
    migrated = False
    for src_t, dst_t in migrations.items():
        src = src_t.format(**env)
        dst = dst_t.format(**env)
        if Path(src).exists() and migrate_one(src, dst):
            migrated = True

    for name in config_migrations:
        if migrate_config(name, env):
            migrated = True

    custom_src = custom_src_t.format(**env)
    custom_dst = custom_dst_t.format(**env)

    if Path(custom_src).exists() and migrate_static_custom(custom_src, custom_dst):
        migrated = True

    # write a marker to avoid re-running migration checks
    ensure_dir_exists(env["jupyter_config"])
    with Path.open(Path(env["jupyter_config"], "migrated"), "w", encoding="utf-8") as f:
        f.write(datetime.now(tz=timezone.utc).isoformat())

    return migrated


class JupyterMigrate(JupyterApp):
    """A Jupyter Migration App."""

    name = "jupyter-migrate"
    description = """
    Migrate configuration and data from .ipython prior to 4.0 to Jupyter locations.

    This migrates:

    - config files in the default profile
    - kernels in ~/.ipython/kernels
    - notebook javascript extensions in ~/.ipython/extensions
    - custom.js/css to .jupyter/custom

    to their new Jupyter locations.

    All files are copied, not moved.
    If the destinations already exist, nothing will be done.
    """

    def start(self) -> None:
        """Start the application."""
        if not migrate():
            self.log.info("Found nothing to migrate.")


main = JupyterMigrate.launch_instance


if __name__ == "__main__":
    main()

# === NexusCore/openenv\Lib\site-packages\google\auth\_default_async.py ===
# Copyright 2020 Google Inc.
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

"""Application default credentials.

Implements application default credentials and project ID detection.
"""

import io
import json
import os

from google.auth import _default
from google.auth import environment_vars
from google.auth import exceptions


def load_credentials_from_file(filename, scopes=None, quota_project_id=None):
    """Loads Google credentials from a file.

    The credentials file must be a service account key or stored authorized
    user credentials.

    Args:
        filename (str): The full path to the credentials file.
        scopes (Optional[Sequence[str]]): The list of scopes for the credentials. If
            specified, the credentials will automatically be scoped if
            necessary
        quota_project_id (Optional[str]):  The project ID used for
                quota and billing.

    Returns:
        Tuple[google.auth.credentials.Credentials, Optional[str]]: Loaded
            credentials and the project ID. Authorized user credentials do not
            have the project ID information.

    Raises:
        google.auth.exceptions.DefaultCredentialsError: if the file is in the
            wrong format or is missing.
    """
    if not os.path.exists(filename):
        raise exceptions.DefaultCredentialsError(
            "File {} was not found.".format(filename)
        )

    with io.open(filename, "r") as file_obj:
        try:
            info = json.load(file_obj)
        except ValueError as caught_exc:
            new_exc = exceptions.DefaultCredentialsError(
                "File {} is not a valid json file.".format(filename), caught_exc
            )
            raise new_exc from caught_exc

    # The type key should indicate that the file is either a service account
    # credentials file or an authorized user credentials file.
    credential_type = info.get("type")

    if credential_type == _default._AUTHORIZED_USER_TYPE:
        from google.oauth2 import _credentials_async as credentials

        try:
            credentials = credentials.Credentials.from_authorized_user_info(
                info, scopes=scopes
            )
        except ValueError as caught_exc:
            msg = "Failed to load authorized user credentials from {}".format(filename)
            new_exc = exceptions.DefaultCredentialsError(msg, caught_exc)
            raise new_exc from caught_exc
        if quota_project_id:
            credentials = credentials.with_quota_project(quota_project_id)
        if not credentials.quota_project_id:
            _default._warn_about_problematic_credentials(credentials)
        return credentials, None

    elif credential_type == _default._SERVICE_ACCOUNT_TYPE:
        from google.oauth2 import _service_account_async as service_account

        try:
            credentials = service_account.Credentials.from_service_account_info(
                info, scopes=scopes
            ).with_quota_project(quota_project_id)
        except ValueError as caught_exc:
            msg = "Failed to load service account credentials from {}".format(filename)
            new_exc = exceptions.DefaultCredentialsError(msg, caught_exc)
            raise new_exc from caught_exc
        return credentials, info.get("project_id")

    else:
        raise exceptions.DefaultCredentialsError(
            "The file {file} does not have a valid type. "
            "Type is {type}, expected one of {valid_types}.".format(
                file=filename, type=credential_type, valid_types=_default._VALID_TYPES
            )
        )


def _get_gcloud_sdk_credentials(quota_project_id=None):
    """Gets the credentials and project ID from the Cloud SDK."""
    from google.auth import _cloud_sdk

    # Check if application default credentials exist.
    credentials_filename = _cloud_sdk.get_application_default_credentials_path()

    if not os.path.isfile(credentials_filename):
        return None, None

    credentials, project_id = load_credentials_from_file(
        credentials_filename, quota_project_id=quota_project_id
    )

    if not project_id:
        project_id = _cloud_sdk.get_project_id()

    return credentials, project_id


def _get_explicit_environ_credentials(quota_project_id=None):
    """Gets credentials from the GOOGLE_APPLICATION_CREDENTIALS environment
    variable."""
    from google.auth import _cloud_sdk

    cloud_sdk_adc_path = _cloud_sdk.get_application_default_credentials_path()
    explicit_file = os.environ.get(environment_vars.CREDENTIALS)

    if explicit_file is not None and explicit_file == cloud_sdk_adc_path:
        # Cloud sdk flow calls gcloud to fetch project id, so if the explicit
        # file path is cloud sdk credentials path, then we should fall back
        # to cloud sdk flow, otherwise project id cannot be obtained.
        return _get_gcloud_sdk_credentials(quota_project_id=quota_project_id)

    if explicit_file is not None:
        credentials, project_id = load_credentials_from_file(
            os.environ[environment_vars.CREDENTIALS], quota_project_id=quota_project_id
        )

        return credentials, project_id

    else:
        return None, None


def _get_gae_credentials():
    """Gets Google App Engine App Identity credentials and project ID."""
    # While this library is normally bundled with app_engine, there are
    # some cases where it's not available, so we tolerate ImportError.

    return _default._get_gae_credentials()


def _get_gce_credentials(request=None):
    """Gets credentials and project ID from the GCE Metadata Service."""
    # Ping requires a transport, but we want application default credentials
    # to require no arguments. So, we'll use the _http_client transport which
    # uses http.client. This is only acceptable because the metadata server
    # doesn't do SSL and never requires proxies.

    # While this library is normally bundled with compute_engine, there are
    # some cases where it's not available, so we tolerate ImportError.

    return _default._get_gce_credentials(request)


def default_async(scopes=None, request=None, quota_project_id=None):
    """Gets the default credentials for the current environment.

    `Application Default Credentials`_ provides an easy way to obtain
    credentials to call Google APIs for server-to-server or local applications.
    This function acquires credentials from the environment in the following
    order:

    1. If the environment variable ``GOOGLE_APPLICATION_CREDENTIALS`` is set
       to the path of a valid service account JSON private key file, then it is
       loaded and returned. The project ID returned is the project ID defined
       in the service account file if available (some older files do not
       contain project ID information).
    2. If the `Google Cloud SDK`_ is installed and has application default
       credentials set they are loaded and returned.

       To enable application default credentials with the Cloud SDK run::

            gcloud auth application-default login

       If the Cloud SDK has an active project, the project ID is returned. The
       active project can be set using::

            gcloud config set project

    3. If the application is running in the `App Engine standard environment`_
       (first generation) then the credentials and project ID from the
       `App Identity Service`_ are used.
    4. If the application is running in `Compute Engine`_ or `Cloud Run`_ or
       the `App Engine flexible environment`_ or the `App Engine standard
       environment`_ (second generation) then the credentials and project ID
       are obtained from the `Metadata Service`_.
    5. If no credentials are found,
       :class:`~google.auth.exceptions.DefaultCredentialsError` will be raised.

    .. _Application Default Credentials: https://developers.google.com\
            /identity/protocols/application-default-credentials
    .. _Google Cloud SDK: https://cloud.google.com/sdk
    .. _App Engine standard environment: https://cloud.google.com/appengine
    .. _App Identity Service: https://cloud.google.com/appengine/docs/python\
            /appidentity/
    .. _Compute Engine: https://cloud.google.com/compute
    .. _App Engine flexible environment: https://cloud.google.com\
            /appengine/flexible
    .. _Metadata Service: https://cloud.google.com/compute/docs\
            /storing-retrieving-metadata
    .. _Cloud Run: https://cloud.google.com/run

    Example::

        import google.auth

        credentials, project_id = google.auth.default()

    Args:
        scopes (Sequence[str]): The list of scopes for the credentials. If
            specified, the credentials will automatically be scoped if
            necessary.
        request (google.auth.transport.Request): An object used to make
            HTTP requests. This is used to detect whether the application
            is running on Compute Engine. If not specified, then it will
            use the standard library http client to make requests.
        quota_project_id (Optional[str]):  The project ID used for
            quota and billing.
    Returns:
        Tuple[~google.auth.credentials.Credentials, Optional[str]]:
            the current environment's credentials and project ID. Project ID
            may be None, which indicates that the Project ID could not be
            ascertained from the environment.

    Raises:
        ~google.auth.exceptions.DefaultCredentialsError:
            If no credentials were found, or if the credentials found were
            invalid.
    """
    from google.auth._credentials_async import with_scopes_if_required
    from google.auth.credentials import CredentialsWithQuotaProject

    explicit_project_id = os.environ.get(
        environment_vars.PROJECT, os.environ.get(environment_vars.LEGACY_PROJECT)
    )

    checkers = (
        lambda: _get_explicit_environ_credentials(quota_project_id=quota_project_id),
        lambda: _get_gcloud_sdk_credentials(quota_project_id=quota_project_id),
        _get_gae_credentials,
        lambda: _get_gce_credentials(request),
    )

    for checker in checkers:
        credentials, project_id = checker()
        if credentials is not None:
            credentials = with_scopes_if_required(credentials, scopes)
            if quota_project_id and isinstance(
                credentials, CredentialsWithQuotaProject
            ):
                credentials = credentials.with_quota_project(quota_project_id)
            effective_project_id = explicit_project_id or project_id
            if not effective_project_id:
                _default._LOGGER.warning(
                    "No project ID could be determined. Consider running "
                    "`gcloud config set project` or setting the %s "
                    "environment variable",
                    environment_vars.PROJECT,
                )
            return credentials, effective_project_id

    raise exceptions.DefaultCredentialsError(_default._CLOUD_SDK_MISSING_CREDENTIALS)

# === NexusCore/openenv\Lib\site-packages\interpreter\computer_use\tools\computer.py ===
import asyncio
import base64
import math
import os
import platform
import shlex
import shutil
import tempfile
import time
from enum import StrEnum
from pathlib import Path
from typing import Literal, TypedDict
from uuid import uuid4

# Add import for PyAutoGUI
import pyautogui
from anthropic.types.beta import BetaToolComputerUse20241022Param

from .base import BaseAnthropicTool, ToolError, ToolResult
from .run import run

OUTPUT_DIR = "/tmp/outputs"

TYPING_DELAY_MS = 12
TYPING_GROUP_SIZE = 50

Action = Literal[
    "key",
    "type",
    "mouse_move",
    "left_click",
    "left_click_drag",
    "right_click",
    "middle_click",
    "double_click",
    "screenshot",
    "cursor_position",
]


class Resolution(TypedDict):
    width: int
    height: int


# sizes above XGA/WXGA are not recommended (see README.md)
# scale down to one of these targets if ComputerTool._scaling_enabled is set
MAX_SCALING_TARGETS: dict[str, Resolution] = {
    "XGA": Resolution(width=1024, height=768),  # 4:3
    "WXGA": Resolution(width=1280, height=800),  # 16:10
    "FWXGA": Resolution(width=1366, height=768),  # ~16:9
}


class ScalingSource(StrEnum):
    COMPUTER = "computer"
    API = "api"


class ComputerToolOptions(TypedDict):
    display_height_px: int
    display_width_px: int
    display_number: int | None


def chunks(s: str, chunk_size: int) -> list[str]:
    return [s[i : i + chunk_size] for i in range(0, len(s), chunk_size)]


def smooth_move_to(x, y, duration=1.2):
    start_x, start_y = pyautogui.position()
    dx = x - start_x
    dy = y - start_y
    distance = math.hypot(dx, dy)  # Calculate the distance in pixels

    start_time = time.time()

    while True:
        elapsed_time = time.time() - start_time
        if elapsed_time > duration:
            break

        t = elapsed_time / duration
        eased_t = (1 - math.cos(t * math.pi)) / 2  # easeInOutSine function

        target_x = start_x + dx * eased_t
        target_y = start_y + dy * eased_t
        pyautogui.moveTo(target_x, target_y)

    # Ensure the mouse ends up exactly at the target (x, y)
    pyautogui.moveTo(x, y)


class ComputerTool(BaseAnthropicTool):
    """
    A tool that allows the agent to interact with the primary monitor's screen, keyboard, and mouse.
    The tool parameters are defined by Anthropic and are not editable.
    """

    name: Literal["computer"] = "computer"
    api_type: Literal["computer_20241022"] = "computer_20241022"
    width: int
    height: int
    display_num: None  # Simplified to always be None since we're only using primary display

    _screenshot_delay = 2.0
    _scaling_enabled = True

    @property
    def options(self) -> ComputerToolOptions:
        width, height = self.scale_coordinates(
            ScalingSource.COMPUTER, self.width, self.height
        )
        return {
            "display_width_px": width,
            "display_height_px": height,
            "display_number": self.display_num,
        }

    def to_params(self) -> BetaToolComputerUse20241022Param:
        return {"name": self.name, "type": self.api_type, **self.options}

    def __init__(self):
        super().__init__()
        self.width, self.height = pyautogui.size()
        self.display_num = None

    async def __call__(
        self,
        *,
        action: Action,
        text: str | None = None,
        coordinate: tuple[int, int] | None = None,
        **kwargs,
    ):
        if action in ("mouse_move", "left_click_drag"):
            if coordinate is None:
                raise ToolError(f"coordinate is required for {action}")
            x, y = self.scale_coordinates(
                ScalingSource.API, coordinate[0], coordinate[1]
            )

            if action == "mouse_move":
                smooth_move_to(x, y)
            elif action == "left_click_drag":
                smooth_move_to(x, y)
                pyautogui.dragTo(x, y, button="left")

        elif action in ("key", "type"):
            if text is None:
                raise ToolError(f"text is required for {action}")

            if action == "key":
                if platform.system() == "Darwin":  # Check if we're on macOS
                    text = text.replace("super+", "command+")

                # Normalize key names
                def normalize_key(key):
                    key = key.lower().replace("_", "")
                    key_map = {
                        "pagedown": "pgdn",
                        "pageup": "pgup",
                        "enter": "return",
                        "return": "enter",
                        # Add more mappings as needed
                    }
                    return key_map.get(key, key)

                keys = [normalize_key(k) for k in text.split("+")]

                if len(keys) > 1:
                    if "darwin" in platform.system().lower():
                        # Use AppleScript for hotkey on macOS
                        keystroke, modifier = (keys[-1], "+".join(keys[:-1]))
                        modifier = modifier.lower() + " down"
                        if keystroke.lower() == "space":
                            keystroke = " "
                        elif keystroke.lower() == "enter":
                            keystroke = "\n"
                        script = f"""
                        tell application "System Events"
                            keystroke "{keystroke}" using {modifier}
                        end tell
                        """
                        os.system("osascript -e '{}'".format(script))
                    else:
                        pyautogui.hotkey(*keys)
                else:
                    pyautogui.press(keys[0])
            elif action == "type":
                pyautogui.write(text, interval=TYPING_DELAY_MS / 1000)

        elif action in ("left_click", "right_click", "double_click", "middle_click"):
            time.sleep(0.1)
            button = {
                "left_click": "left",
                "right_click": "right",
                "middle_click": "middle",
            }
            if action == "double_click":
                pyautogui.click()
                time.sleep(0.1)
                pyautogui.click()
            else:
                pyautogui.click(button=button.get(action, "left"))

        elif action == "screenshot":
            return await self.screenshot()

        elif action == "cursor_position":
            x, y = pyautogui.position()
            x, y = self.scale_coordinates(ScalingSource.COMPUTER, x, y)
            return ToolResult(output=f"X={x},Y={y}")

        else:
            raise ToolError(f"Invalid action: {action}")

        # Take a screenshot after the action (except for cursor_position)
        if action != "cursor_position":
            return await self.screenshot()

    async def screenshot(self):
        """Take a screenshot of the current screen and return the base64 encoded image."""
        temp_dir = Path(tempfile.gettempdir())
        path = temp_dir / f"screenshot_{uuid4().hex}.png"

        screenshot = pyautogui.screenshot()
        screenshot.save(str(path))

        if self._scaling_enabled:
            x, y = self.scale_coordinates(
                ScalingSource.COMPUTER, self.width, self.height
            )
            # Use PIL directly instead of shell convert command
            from PIL import Image

            with Image.open(path) as img:
                img = img.resize((x, y), Image.Resampling.LANCZOS)
                img.save(path)

        if path.exists():
            base64_image = base64.b64encode(path.read_bytes()).decode()
            path.unlink()  # Remove the temporary file
            return ToolResult(base64_image=base64_image)
        raise ToolError(f"Failed to take screenshot")

    async def shell(self, command: str, take_screenshot=True) -> ToolResult:
        """Run a shell command and return the output, error, and optionally a screenshot."""
        _, stdout, stderr = await run(command)
        base64_image = None

        if take_screenshot:
            # delay to let things settle before taking a screenshot
            await asyncio.sleep(self._screenshot_delay)
            base64_image = (await self.screenshot()).base64_image

        return ToolResult(output=stdout, error=stderr, base64_image=base64_image)

    def scale_coordinates(self, source: ScalingSource, x: int, y: int):
        """Scale coordinates to a target maximum resolution."""
        if not self._scaling_enabled:
            return x, y
        ratio = self.width / self.height
        target_dimension = None
        for dimension in MAX_SCALING_TARGETS.values():
            # allow some error in the aspect ratio - not ratios are exactly 16:9
            if abs(dimension["width"] / dimension["height"] - ratio) < 0.02:
                if dimension["width"] < self.width:
                    target_dimension = dimension
                break
        if target_dimension is None:
            return x, y
        # should be less than 1
        x_scaling_factor = target_dimension["width"] / self.width
        y_scaling_factor = target_dimension["height"] / self.height
        if source == ScalingSource.API:
            if x > self.width or y > self.height:
                raise ToolError(f"Coordinates {x}, {y} are out of bounds")
            # scale up
            return round(x / x_scaling_factor), round(y / y_scaling_factor)
        # scale down
        return round(x * x_scaling_factor), round(y * y_scaling_factor)

# === NexusCore/openenv\Lib\site-packages\litellm\proxy\hooks\prompt_injection_detection.py ===
# +------------------------------------+
#
#        Prompt Injection Detection
#
# +------------------------------------+
#  Thank you users! We ❤️ you! - Krrish & Ishaan
## Reject a call if it contains a prompt injection attack.


from difflib import SequenceMatcher
from typing import List, Literal, Optional

from fastapi import HTTPException

import litellm
from litellm._logging import verbose_proxy_logger
from litellm.caching.caching import DualCache
from litellm.constants import DEFAULT_PROMPT_INJECTION_SIMILARITY_THRESHOLD
from litellm.integrations.custom_logger import CustomLogger
from litellm.litellm_core_utils.prompt_templates.factory import (
    prompt_injection_detection_default_pt,
)
from litellm.proxy._types import LiteLLMPromptInjectionParams, UserAPIKeyAuth
from litellm.router import Router
from litellm.utils import get_formatted_prompt


class _OPTIONAL_PromptInjectionDetection(CustomLogger):
    # Class variables or attributes
    def __init__(
        self,
        prompt_injection_params: Optional[LiteLLMPromptInjectionParams] = None,
    ):
        self.prompt_injection_params = prompt_injection_params
        self.llm_router: Optional[Router] = None

        self.verbs = [
            "Ignore",
            "Disregard",
            "Skip",
            "Forget",
            "Neglect",
            "Overlook",
            "Omit",
            "Bypass",
            "Pay no attention to",
            "Do not follow",
            "Do not obey",
        ]
        self.adjectives = [
            "",
            "prior",
            "previous",
            "preceding",
            "above",
            "foregoing",
            "earlier",
            "initial",
        ]
        self.prepositions = [
            "",
            "and start over",
            "and start anew",
            "and begin afresh",
            "and start from scratch",
        ]

    def print_verbose(self, print_statement, level: Literal["INFO", "DEBUG"] = "DEBUG"):
        if level == "INFO":
            verbose_proxy_logger.info(print_statement)
        elif level == "DEBUG":
            verbose_proxy_logger.debug(print_statement)

        if litellm.set_verbose is True:
            print(print_statement)  # noqa

    def update_environment(self, router: Optional[Router] = None):
        self.llm_router = router

        if (
            self.prompt_injection_params is not None
            and self.prompt_injection_params.llm_api_check is True
        ):
            if self.llm_router is None:
                raise Exception(
                    "PromptInjectionDetection: Model List not set. Required for Prompt Injection detection."
                )

            self.print_verbose(
                f"model_names: {self.llm_router.model_names}; self.prompt_injection_params.llm_api_name: {self.prompt_injection_params.llm_api_name}"
            )
            if (
                self.prompt_injection_params.llm_api_name is None
                or self.prompt_injection_params.llm_api_name
                not in self.llm_router.model_names
            ):
                raise Exception(
                    "PromptInjectionDetection: Invalid LLM API Name. LLM API Name must be a 'model_name' in 'model_list'."
                )

    def generate_injection_keywords(self) -> List[str]:
        combinations = []
        for verb in self.verbs:
            for adj in self.adjectives:
                for prep in self.prepositions:
                    phrase = " ".join(filter(None, [verb, adj, prep])).strip()
                    if (
                        len(phrase.split()) > 2
                    ):  # additional check to ensure more than 2 words
                        combinations.append(phrase.lower())
        return combinations

    def check_user_input_similarity(
        self,
        user_input: str,
        similarity_threshold: float = DEFAULT_PROMPT_INJECTION_SIMILARITY_THRESHOLD,
    ) -> bool:
        user_input_lower = user_input.lower()
        keywords = self.generate_injection_keywords()

        for keyword in keywords:
            # Calculate the length of the keyword to extract substrings of the same length from user input
            keyword_length = len(keyword)

            for i in range(len(user_input_lower) - keyword_length + 1):
                # Extract a substring of the same length as the keyword
                substring = user_input_lower[i : i + keyword_length]

                # Calculate similarity
                match_ratio = SequenceMatcher(None, substring, keyword).ratio()
                if match_ratio > similarity_threshold:
                    self.print_verbose(
                        print_statement=f"Rejected user input - {user_input}. {match_ratio} similar to {keyword}",
                        level="INFO",
                    )
                    return True  # Found a highly similar substring
        return False  # No substring crossed the threshold

    async def async_pre_call_hook(
        self,
        user_api_key_dict: UserAPIKeyAuth,
        cache: DualCache,
        data: dict,
        call_type: str,  # "completion", "embeddings", "image_generation", "moderation"
    ):
        try:
            """
            - check if user id part of call
            - check if user id part of blocked list
            """
            self.print_verbose("Inside Prompt Injection Detection Pre-Call Hook")
            try:
                assert call_type in [
                    "completion",
                    "text_completion",
                    "embeddings",
                    "image_generation",
                    "moderation",
                    "audio_transcription",
                ]
            except Exception:
                self.print_verbose(
                    f"Call Type - {call_type}, not in accepted list - ['completion','embeddings','image_generation','moderation','audio_transcription']"
                )
                return data
            formatted_prompt = get_formatted_prompt(data=data, call_type=call_type)  # type: ignore

            is_prompt_attack = False

            if self.prompt_injection_params is not None:
                # 1. check if heuristics check turned on
                if self.prompt_injection_params.heuristics_check is True:
                    is_prompt_attack = self.check_user_input_similarity(
                        user_input=formatted_prompt
                    )
                    if is_prompt_attack is True:
                        raise HTTPException(
                            status_code=400,
                            detail={
                                "error": "Rejected message. This is a prompt injection attack."
                            },
                        )
                # 2. check if vector db similarity check turned on [TODO] Not Implemented yet
                if self.prompt_injection_params.vector_db_check is True:
                    pass
            else:
                is_prompt_attack = self.check_user_input_similarity(
                    user_input=formatted_prompt
                )

            if is_prompt_attack is True:
                raise HTTPException(
                    status_code=400,
                    detail={
                        "error": "Rejected message. This is a prompt injection attack."
                    },
                )

            return data

        except HTTPException as e:
            if (
                e.status_code == 400
                and isinstance(e.detail, dict)
                and "error" in e.detail  # type: ignore
                and self.prompt_injection_params is not None
                and self.prompt_injection_params.reject_as_response
            ):
                return e.detail.get("error")
            raise e
        except Exception as e:
            verbose_proxy_logger.exception(
                "litellm.proxy.hooks.prompt_injection_detection.py::async_pre_call_hook(): Exception occured - {}".format(
                    str(e)
                )
            )

    async def async_moderation_hook(  # type: ignore
        self,
        data: dict,
        user_api_key_dict: UserAPIKeyAuth,
        call_type: Literal[
            "completion",
            "embeddings",
            "image_generation",
            "moderation",
            "audio_transcription",
        ],
    ) -> Optional[bool]:
        self.print_verbose(
            f"IN ASYNC MODERATION HOOK - self.prompt_injection_params = {self.prompt_injection_params}"
        )

        if self.prompt_injection_params is None:
            return None

        formatted_prompt = get_formatted_prompt(data=data, call_type=call_type)  # type: ignore
        is_prompt_attack = False

        prompt_injection_system_prompt = getattr(
            self.prompt_injection_params,
            "llm_api_system_prompt",
            prompt_injection_detection_default_pt(),
        )

        # 3. check if llm api check turned on
        if (
            self.prompt_injection_params.llm_api_check is True
            and self.prompt_injection_params.llm_api_name is not None
            and self.llm_router is not None
        ):
            # make a call to the llm api
            response = await self.llm_router.acompletion(
                model=self.prompt_injection_params.llm_api_name,
                messages=[
                    {
                        "role": "system",
                        "content": prompt_injection_system_prompt,
                    },
                    {"role": "user", "content": formatted_prompt},
                ],
            )

            self.print_verbose(f"Received LLM Moderation response: {response}")
            self.print_verbose(
                f"llm_api_fail_call_string: {self.prompt_injection_params.llm_api_fail_call_string}"
            )
            if isinstance(response, litellm.ModelResponse) and isinstance(
                response.choices[0], litellm.Choices
            ):
                if self.prompt_injection_params.llm_api_fail_call_string in response.choices[0].message.content:  # type: ignore
                    is_prompt_attack = True

        if is_prompt_attack is True:
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "Rejected message. This is a prompt injection attack."
                },
            )

        return is_prompt_attack

# === NexusCore/openenv\Lib\site-packages\openai\resources\beta\realtime\transcription_sessions.py ===
# File generated from our OpenAPI spec by Stainless. See CONTRIBUTING.md for details.

from __future__ import annotations

from typing import List
from typing_extensions import Literal

import httpx

from .... import _legacy_response
from ...._types import NOT_GIVEN, Body, Query, Headers, NotGiven
from ...._utils import maybe_transform, async_maybe_transform
from ...._compat import cached_property
from ...._resource import SyncAPIResource, AsyncAPIResource
from ...._response import to_streamed_response_wrapper, async_to_streamed_response_wrapper
from ...._base_client import make_request_options
from ....types.beta.realtime import transcription_session_create_params
from ....types.beta.realtime.transcription_session import TranscriptionSession

__all__ = ["TranscriptionSessions", "AsyncTranscriptionSessions"]


class TranscriptionSessions(SyncAPIResource):
    @cached_property
    def with_raw_response(self) -> TranscriptionSessionsWithRawResponse:
        """
        This property can be used as a prefix for any HTTP method call to return
        the raw response object instead of the parsed content.

        For more information, see https://www.github.com/openai/openai-python#accessing-raw-response-data-eg-headers
        """
        return TranscriptionSessionsWithRawResponse(self)

    @cached_property
    def with_streaming_response(self) -> TranscriptionSessionsWithStreamingResponse:
        """
        An alternative to `.with_raw_response` that doesn't eagerly read the response body.

        For more information, see https://www.github.com/openai/openai-python#with_streaming_response
        """
        return TranscriptionSessionsWithStreamingResponse(self)

    def create(
        self,
        *,
        client_secret: transcription_session_create_params.ClientSecret | NotGiven = NOT_GIVEN,
        include: List[str] | NotGiven = NOT_GIVEN,
        input_audio_format: Literal["pcm16", "g711_ulaw", "g711_alaw"] | NotGiven = NOT_GIVEN,
        input_audio_noise_reduction: transcription_session_create_params.InputAudioNoiseReduction
        | NotGiven = NOT_GIVEN,
        input_audio_transcription: transcription_session_create_params.InputAudioTranscription | NotGiven = NOT_GIVEN,
        modalities: List[Literal["text", "audio"]] | NotGiven = NOT_GIVEN,
        turn_detection: transcription_session_create_params.TurnDetection | NotGiven = NOT_GIVEN,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> TranscriptionSession:
        """
        Create an ephemeral API token for use in client-side applications with the
        Realtime API specifically for realtime transcriptions. Can be configured with
        the same session parameters as the `transcription_session.update` client event.

        It responds with a session object, plus a `client_secret` key which contains a
        usable ephemeral API token that can be used to authenticate browser clients for
        the Realtime API.

        Args:
          client_secret: Configuration options for the generated client secret.

          include:
              The set of items to include in the transcription. Current available items are:

              - `item.input_audio_transcription.logprobs`

          input_audio_format: The format of input audio. Options are `pcm16`, `g711_ulaw`, or `g711_alaw`. For
              `pcm16`, input audio must be 16-bit PCM at a 24kHz sample rate, single channel
              (mono), and little-endian byte order.

          input_audio_noise_reduction: Configuration for input audio noise reduction. This can be set to `null` to turn
              off. Noise reduction filters audio added to the input audio buffer before it is
              sent to VAD and the model. Filtering the audio can improve VAD and turn
              detection accuracy (reducing false positives) and model performance by improving
              perception of the input audio.

          input_audio_transcription: Configuration for input audio transcription. The client can optionally set the
              language and prompt for transcription, these offer additional guidance to the
              transcription service.

          modalities: The set of modalities the model can respond with. To disable audio, set this to
              ["text"].

          turn_detection: Configuration for turn detection, ether Server VAD or Semantic VAD. This can be
              set to `null` to turn off, in which case the client must manually trigger model
              response. Server VAD means that the model will detect the start and end of
              speech based on audio volume and respond at the end of user speech. Semantic VAD
              is more advanced and uses a turn detection model (in conjuction with VAD) to
              semantically estimate whether the user has finished speaking, then dynamically
              sets a timeout based on this probability. For example, if user audio trails off
              with "uhhm", the model will score a low probability of turn end and wait longer
              for the user to continue speaking. This can be useful for more natural
              conversations, but may have a higher latency.

          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request, in seconds
        """
        extra_headers = {"OpenAI-Beta": "assistants=v2", **(extra_headers or {})}
        return self._post(
            "/realtime/transcription_sessions",
            body=maybe_transform(
                {
                    "client_secret": client_secret,
                    "include": include,
                    "input_audio_format": input_audio_format,
                    "input_audio_noise_reduction": input_audio_noise_reduction,
                    "input_audio_transcription": input_audio_transcription,
                    "modalities": modalities,
                    "turn_detection": turn_detection,
                },
                transcription_session_create_params.TranscriptionSessionCreateParams,
            ),
            options=make_request_options(
                extra_headers=extra_headers, extra_query=extra_query, extra_body=extra_body, timeout=timeout
            ),
            cast_to=TranscriptionSession,
        )


class AsyncTranscriptionSessions(AsyncAPIResource):
    @cached_property
    def with_raw_response(self) -> AsyncTranscriptionSessionsWithRawResponse:
        """
        This property can be used as a prefix for any HTTP method call to return
        the raw response object instead of the parsed content.

        For more information, see https://www.github.com/openai/openai-python#accessing-raw-response-data-eg-headers
        """
        return AsyncTranscriptionSessionsWithRawResponse(self)

    @cached_property
    def with_streaming_response(self) -> AsyncTranscriptionSessionsWithStreamingResponse:
        """
        An alternative to `.with_raw_response` that doesn't eagerly read the response body.

        For more information, see https://www.github.com/openai/openai-python#with_streaming_response
        """
        return AsyncTranscriptionSessionsWithStreamingResponse(self)

    async def create(
        self,
        *,
        client_secret: transcription_session_create_params.ClientSecret | NotGiven = NOT_GIVEN,
        include: List[str] | NotGiven = NOT_GIVEN,
        input_audio_format: Literal["pcm16", "g711_ulaw", "g711_alaw"] | NotGiven = NOT_GIVEN,
        input_audio_noise_reduction: transcription_session_create_params.InputAudioNoiseReduction
        | NotGiven = NOT_GIVEN,
        input_audio_transcription: transcription_session_create_params.InputAudioTranscription | NotGiven = NOT_GIVEN,
        modalities: List[Literal["text", "audio"]] | NotGiven = NOT_GIVEN,
        turn_detection: transcription_session_create_params.TurnDetection | NotGiven = NOT_GIVEN,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> TranscriptionSession:
        """
        Create an ephemeral API token for use in client-side applications with the
        Realtime API specifically for realtime transcriptions. Can be configured with
        the same session parameters as the `transcription_session.update` client event.

        It responds with a session object, plus a `client_secret` key which contains a
        usable ephemeral API token that can be used to authenticate browser clients for
        the Realtime API.

        Args:
          client_secret: Configuration options for the generated client secret.

          include:
              The set of items to include in the transcription. Current available items are:

              - `item.input_audio_transcription.logprobs`

          input_audio_format: The format of input audio. Options are `pcm16`, `g711_ulaw`, or `g711_alaw`. For
              `pcm16`, input audio must be 16-bit PCM at a 24kHz sample rate, single channel
              (mono), and little-endian byte order.

          input_audio_noise_reduction: Configuration for input audio noise reduction. This can be set to `null` to turn
              off. Noise reduction filters audio added to the input audio buffer before it is
              sent to VAD and the model. Filtering the audio can improve VAD and turn
              detection accuracy (reducing false positives) and model performance by improving
              perception of the input audio.

          input_audio_transcription: Configuration for input audio transcription. The client can optionally set the
              language and prompt for transcription, these offer additional guidance to the
              transcription service.

          modalities: The set of modalities the model can respond with. To disable audio, set this to
              ["text"].

          turn_detection: Configuration for turn detection, ether Server VAD or Semantic VAD. This can be
              set to `null` to turn off, in which case the client must manually trigger model
              response. Server VAD means that the model will detect the start and end of
              speech based on audio volume and respond at the end of user speech. Semantic VAD
              is more advanced and uses a turn detection model (in conjuction with VAD) to
              semantically estimate whether the user has finished speaking, then dynamically
              sets a timeout based on this probability. For example, if user audio trails off
              with "uhhm", the model will score a low probability of turn end and wait longer
              for the user to continue speaking. This can be useful for more natural
              conversations, but may have a higher latency.

          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request, in seconds
        """
        extra_headers = {"OpenAI-Beta": "assistants=v2", **(extra_headers or {})}
        return await self._post(
            "/realtime/transcription_sessions",
            body=await async_maybe_transform(
                {
                    "client_secret": client_secret,
                    "include": include,
                    "input_audio_format": input_audio_format,
                    "input_audio_noise_reduction": input_audio_noise_reduction,
                    "input_audio_transcription": input_audio_transcription,
                    "modalities": modalities,
                    "turn_detection": turn_detection,
                },
                transcription_session_create_params.TranscriptionSessionCreateParams,
            ),
            options=make_request_options(
                extra_headers=extra_headers, extra_query=extra_query, extra_body=extra_body, timeout=timeout
            ),
            cast_to=TranscriptionSession,
        )


class TranscriptionSessionsWithRawResponse:
    def __init__(self, transcription_sessions: TranscriptionSessions) -> None:
        self._transcription_sessions = transcription_sessions

        self.create = _legacy_response.to_raw_response_wrapper(
            transcription_sessions.create,
        )


class AsyncTranscriptionSessionsWithRawResponse:
    def __init__(self, transcription_sessions: AsyncTranscriptionSessions) -> None:
        self._transcription_sessions = transcription_sessions

        self.create = _legacy_response.async_to_raw_response_wrapper(
            transcription_sessions.create,
        )


class TranscriptionSessionsWithStreamingResponse:
    def __init__(self, transcription_sessions: TranscriptionSessions) -> None:
        self._transcription_sessions = transcription_sessions

        self.create = to_streamed_response_wrapper(
            transcription_sessions.create,
        )


class AsyncTranscriptionSessionsWithStreamingResponse:
    def __init__(self, transcription_sessions: AsyncTranscriptionSessions) -> None:
        self._transcription_sessions = transcription_sessions

        self.create = async_to_streamed_response_wrapper(
            transcription_sessions.create,
        )

# === NexusCore/openenv\Lib\site-packages\openai\resources\fine_tuning\alpha\graders.py ===
# File generated from our OpenAPI spec by Stainless. See CONTRIBUTING.md for details.

from __future__ import annotations

import httpx

from .... import _legacy_response
from ...._types import NOT_GIVEN, Body, Query, Headers, NotGiven
from ...._utils import maybe_transform, async_maybe_transform
from ...._compat import cached_property
from ...._resource import SyncAPIResource, AsyncAPIResource
from ...._response import to_streamed_response_wrapper, async_to_streamed_response_wrapper
from ...._base_client import make_request_options
from ....types.fine_tuning.alpha import grader_run_params, grader_validate_params
from ....types.fine_tuning.alpha.grader_run_response import GraderRunResponse
from ....types.fine_tuning.alpha.grader_validate_response import GraderValidateResponse

__all__ = ["Graders", "AsyncGraders"]


class Graders(SyncAPIResource):
    @cached_property
    def with_raw_response(self) -> GradersWithRawResponse:
        """
        This property can be used as a prefix for any HTTP method call to return
        the raw response object instead of the parsed content.

        For more information, see https://www.github.com/openai/openai-python#accessing-raw-response-data-eg-headers
        """
        return GradersWithRawResponse(self)

    @cached_property
    def with_streaming_response(self) -> GradersWithStreamingResponse:
        """
        An alternative to `.with_raw_response` that doesn't eagerly read the response body.

        For more information, see https://www.github.com/openai/openai-python#with_streaming_response
        """
        return GradersWithStreamingResponse(self)

    def run(
        self,
        *,
        grader: grader_run_params.Grader,
        model_sample: str,
        item: object | NotGiven = NOT_GIVEN,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> GraderRunResponse:
        """
        Run a grader.

        Args:
          grader: The grader used for the fine-tuning job.

          model_sample: The model sample to be evaluated. This value will be used to populate the
              `sample` namespace. See
              [the guide](https://platform.openai.com/docs/guides/graders) for more details.
              The `output_json` variable will be populated if the model sample is a valid JSON
              string.

          item: The dataset item provided to the grader. This will be used to populate the
              `item` namespace. See
              [the guide](https://platform.openai.com/docs/guides/graders) for more details.

          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request, in seconds
        """
        return self._post(
            "/fine_tuning/alpha/graders/run",
            body=maybe_transform(
                {
                    "grader": grader,
                    "model_sample": model_sample,
                    "item": item,
                },
                grader_run_params.GraderRunParams,
            ),
            options=make_request_options(
                extra_headers=extra_headers, extra_query=extra_query, extra_body=extra_body, timeout=timeout
            ),
            cast_to=GraderRunResponse,
        )

    def validate(
        self,
        *,
        grader: grader_validate_params.Grader,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> GraderValidateResponse:
        """
        Validate a grader.

        Args:
          grader: The grader used for the fine-tuning job.

          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request, in seconds
        """
        return self._post(
            "/fine_tuning/alpha/graders/validate",
            body=maybe_transform({"grader": grader}, grader_validate_params.GraderValidateParams),
            options=make_request_options(
                extra_headers=extra_headers, extra_query=extra_query, extra_body=extra_body, timeout=timeout
            ),
            cast_to=GraderValidateResponse,
        )


class AsyncGraders(AsyncAPIResource):
    @cached_property
    def with_raw_response(self) -> AsyncGradersWithRawResponse:
        """
        This property can be used as a prefix for any HTTP method call to return
        the raw response object instead of the parsed content.

        For more information, see https://www.github.com/openai/openai-python#accessing-raw-response-data-eg-headers
        """
        return AsyncGradersWithRawResponse(self)

    @cached_property
    def with_streaming_response(self) -> AsyncGradersWithStreamingResponse:
        """
        An alternative to `.with_raw_response` that doesn't eagerly read the response body.

        For more information, see https://www.github.com/openai/openai-python#with_streaming_response
        """
        return AsyncGradersWithStreamingResponse(self)

    async def run(
        self,
        *,
        grader: grader_run_params.Grader,
        model_sample: str,
        item: object | NotGiven = NOT_GIVEN,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> GraderRunResponse:
        """
        Run a grader.

        Args:
          grader: The grader used for the fine-tuning job.

          model_sample: The model sample to be evaluated. This value will be used to populate the
              `sample` namespace. See
              [the guide](https://platform.openai.com/docs/guides/graders) for more details.
              The `output_json` variable will be populated if the model sample is a valid JSON
              string.

          item: The dataset item provided to the grader. This will be used to populate the
              `item` namespace. See
              [the guide](https://platform.openai.com/docs/guides/graders) for more details.

          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request, in seconds
        """
        return await self._post(
            "/fine_tuning/alpha/graders/run",
            body=await async_maybe_transform(
                {
                    "grader": grader,
                    "model_sample": model_sample,
                    "item": item,
                },
                grader_run_params.GraderRunParams,
            ),
            options=make_request_options(
                extra_headers=extra_headers, extra_query=extra_query, extra_body=extra_body, timeout=timeout
            ),
            cast_to=GraderRunResponse,
        )

    async def validate(
        self,
        *,
        grader: grader_validate_params.Grader,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> GraderValidateResponse:
        """
        Validate a grader.

        Args:
          grader: The grader used for the fine-tuning job.

          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request, in seconds
        """
        return await self._post(
            "/fine_tuning/alpha/graders/validate",
            body=await async_maybe_transform({"grader": grader}, grader_validate_params.GraderValidateParams),
            options=make_request_options(
                extra_headers=extra_headers, extra_query=extra_query, extra_body=extra_body, timeout=timeout
            ),
            cast_to=GraderValidateResponse,
        )


class GradersWithRawResponse:
    def __init__(self, graders: Graders) -> None:
        self._graders = graders

        self.run = _legacy_response.to_raw_response_wrapper(
            graders.run,
        )
        self.validate = _legacy_response.to_raw_response_wrapper(
            graders.validate,
        )


class AsyncGradersWithRawResponse:
    def __init__(self, graders: AsyncGraders) -> None:
        self._graders = graders

        self.run = _legacy_response.async_to_raw_response_wrapper(
            graders.run,
        )
        self.validate = _legacy_response.async_to_raw_response_wrapper(
            graders.validate,
        )


class GradersWithStreamingResponse:
    def __init__(self, graders: Graders) -> None:
        self._graders = graders

        self.run = to_streamed_response_wrapper(
            graders.run,
        )
        self.validate = to_streamed_response_wrapper(
            graders.validate,
        )


class AsyncGradersWithStreamingResponse:
    def __init__(self, graders: AsyncGraders) -> None:
        self._graders = graders

        self.run = async_to_streamed_response_wrapper(
            graders.run,
        )
        self.validate = async_to_streamed_response_wrapper(
            graders.validate,
        )

# === NexusCore/openenv\Lib\site-packages\git\objects\fun.py ===
# This module is part of GitPython and is released under the
# 3-Clause BSD License: https://opensource.org/license/bsd-3-clause/

"""Functions that are supposed to be as fast as possible."""

__all__ = [
    "tree_to_stream",
    "tree_entries_from_data",
    "traverse_trees_recursive",
    "traverse_tree_recursive",
]

from stat import S_ISDIR

from git.compat import safe_decode, defenc

# typing ----------------------------------------------

from typing import (
    Callable,
    List,
    MutableSequence,
    Sequence,
    Tuple,
    TYPE_CHECKING,
    Union,
    overload,
)

if TYPE_CHECKING:
    from _typeshed import ReadableBuffer

    from git import GitCmdObjectDB

EntryTup = Tuple[bytes, int, str]  # Same as TreeCacheTup in tree.py.
EntryTupOrNone = Union[EntryTup, None]

# ---------------------------------------------------


def tree_to_stream(entries: Sequence[EntryTup], write: Callable[["ReadableBuffer"], Union[int, None]]) -> None:
    """Write the given list of entries into a stream using its ``write`` method.

    :param entries:
        **Sorted** list of tuples with (binsha, mode, name).

    :param write:
        A ``write`` method which takes a data string.
    """
    ord_zero = ord("0")
    bit_mask = 7  # 3 bits set.

    for binsha, mode, name in entries:
        mode_str = b""
        for i in range(6):
            mode_str = bytes([((mode >> (i * 3)) & bit_mask) + ord_zero]) + mode_str
        # END for each 8 octal value

        # git slices away the first octal if it's zero.
        if mode_str[0] == ord_zero:
            mode_str = mode_str[1:]
        # END save a byte

        # Here it comes: If the name is actually unicode, the replacement below will not
        # work as the binsha is not part of the ascii unicode encoding - hence we must
        # convert to an UTF-8 string for it to work properly. According to my tests,
        # this is exactly what git does, that is it just takes the input literally,
        # which appears to be UTF-8 on linux.
        if isinstance(name, str):
            name_bytes = name.encode(defenc)
        else:
            name_bytes = name  # type: ignore[unreachable]  # check runtime types - is always str?
        write(b"".join((mode_str, b" ", name_bytes, b"\0", binsha)))
    # END for each item


def tree_entries_from_data(data: bytes) -> List[EntryTup]:
    """Read the binary representation of a tree and returns tuples of
    :class:`~git.objects.tree.Tree` items.

    :param data:
        Data block with tree data (as bytes).

    :return:
        list(tuple(binsha, mode, tree_relative_path), ...)
    """
    ord_zero = ord("0")
    space_ord = ord(" ")
    len_data = len(data)
    i = 0
    out = []
    while i < len_data:
        mode = 0

        # Read Mode
        # Some git versions truncate the leading 0, some don't.
        # The type will be extracted from the mode later.
        while data[i] != space_ord:
            # Move existing mode integer up one level being 3 bits and add the actual
            # ordinal value of the character.
            mode = (mode << 3) + (data[i] - ord_zero)
            i += 1
        # END while reading mode

        # Byte is space now, skip it.
        i += 1

        # Parse name, it is NULL separated.

        ns = i
        while data[i] != 0:
            i += 1
        # END while not reached NULL

        # Default encoding for strings in git is UTF-8.
        # Only use the respective unicode object if the byte stream was encoded.
        name_bytes = data[ns:i]
        name = safe_decode(name_bytes)

        # Byte is NULL, get next 20.
        i += 1
        sha = data[i : i + 20]
        i = i + 20
        out.append((sha, mode, name))
    # END for each byte in data stream
    return out


def _find_by_name(tree_data: MutableSequence[EntryTupOrNone], name: str, is_dir: bool, start_at: int) -> EntryTupOrNone:
    """Return data entry matching the given name and tree mode or ``None``.

    Before the item is returned, the respective data item is set None in the `tree_data`
    list to mark it done.
    """

    try:
        item = tree_data[start_at]
        if item and item[2] == name and S_ISDIR(item[1]) == is_dir:
            tree_data[start_at] = None
            return item
    except IndexError:
        pass
    # END exception handling
    for index, item in enumerate(tree_data):
        if item and item[2] == name and S_ISDIR(item[1]) == is_dir:
            tree_data[index] = None
            return item
        # END if item matches
    # END for each item
    return None


@overload
def _to_full_path(item: None, path_prefix: str) -> None: ...


@overload
def _to_full_path(item: EntryTup, path_prefix: str) -> EntryTup: ...


def _to_full_path(item: EntryTupOrNone, path_prefix: str) -> EntryTupOrNone:
    """Rebuild entry with given path prefix."""
    if not item:
        return item
    return (item[0], item[1], path_prefix + item[2])


def traverse_trees_recursive(
    odb: "GitCmdObjectDB", tree_shas: Sequence[Union[bytes, None]], path_prefix: str
) -> List[Tuple[EntryTupOrNone, ...]]:
    """
    :return:
        List of list with entries according to the given binary tree-shas.

        The result is encoded in a list
        of n tuple|None per blob/commit, (n == len(tree_shas)), where:

        * [0] == 20 byte sha
        * [1] == mode as int
        * [2] == path relative to working tree root

        The entry tuple is ``None`` if the respective blob/commit did not exist in the
        given tree.

    :param tree_shas:
        Iterable of shas pointing to trees. All trees must be on the same level.
        A tree-sha may be ``None``, in which case ``None``.

    :param path_prefix:
        A prefix to be added to the returned paths on this level.
        Set it ``""`` for the first iteration.

    :note:
        The ordering of the returned items will be partially lost.
    """
    trees_data: List[List[EntryTupOrNone]] = []

    nt = len(tree_shas)
    for tree_sha in tree_shas:
        if tree_sha is None:
            data: List[EntryTupOrNone] = []
        else:
            # Make new list for typing as list invariant.
            data = list(tree_entries_from_data(odb.stream(tree_sha).read()))
        # END handle muted trees
        trees_data.append(data)
    # END for each sha to get data for

    out: List[Tuple[EntryTupOrNone, ...]] = []

    # Find all matching entries and recursively process them together if the match is a
    # tree. If the match is a non-tree item, put it into the result.
    # Processed items will be set None.
    for ti, tree_data in enumerate(trees_data):
        for ii, item in enumerate(tree_data):
            if not item:
                continue
            # END skip already done items
            entries: List[EntryTupOrNone]
            entries = [None for _ in range(nt)]
            entries[ti] = item
            _sha, mode, name = item
            is_dir = S_ISDIR(mode)  # Type mode bits

            # Find this item in all other tree data items.
            # Wrap around, but stop one before our current index, hence ti+nt, not
            # ti+1+nt.
            for tio in range(ti + 1, ti + nt):
                tio = tio % nt
                entries[tio] = _find_by_name(trees_data[tio], name, is_dir, ii)

            # END for each other item data
            # If we are a directory, enter recursion.
            if is_dir:
                out.extend(
                    traverse_trees_recursive(
                        odb,
                        [((ei and ei[0]) or None) for ei in entries],
                        path_prefix + name + "/",
                    )
                )
            else:
                out.append(tuple(_to_full_path(e, path_prefix) for e in entries))

            # END handle recursion
            # Finally mark it done.
            tree_data[ii] = None
        # END for each item

        # We are done with one tree, set all its data empty.
        del tree_data[:]
    # END for each tree_data chunk
    return out


def traverse_tree_recursive(odb: "GitCmdObjectDB", tree_sha: bytes, path_prefix: str) -> List[EntryTup]:
    """
    :return:
        List of entries of the tree pointed to by the binary `tree_sha`.

        An entry has the following format:

        * [0] 20 byte sha
        * [1] mode as int
        * [2] path relative to the repository

    :param path_prefix:
        Prefix to prepend to the front of all returned paths.
    """
    entries = []
    data = tree_entries_from_data(odb.stream(tree_sha).read())

    # Unpacking/packing is faster than accessing individual items.
    for sha, mode, name in data:
        if S_ISDIR(mode):
            entries.extend(traverse_tree_recursive(odb, sha, path_prefix + name + "/"))
        else:
            entries.append((sha, mode, path_prefix + name))
    # END for each item

    return entries

# === NexusCore/openenv\Lib\site-packages\google\oauth2\challenges.py ===
# Copyright 2021 Google LLC
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

""" Challenges for reauthentication.
"""

import abc
import base64
import getpass
import sys

from google.auth import _helpers
from google.auth import exceptions
from google.oauth2 import webauthn_handler_factory
from google.oauth2.webauthn_types import (
    AuthenticationExtensionsClientInputs,
    GetRequest,
    PublicKeyCredentialDescriptor,
)


REAUTH_ORIGIN = "https://accounts.google.com"
SAML_CHALLENGE_MESSAGE = (
    "Please run `gcloud auth login` to complete reauthentication with SAML."
)
WEBAUTHN_TIMEOUT_MS = 120000  # Two minute timeout


def get_user_password(text):
    """Get password from user.

    Override this function with a different logic if you are using this library
    outside a CLI.

    Args:
        text (str): message for the password prompt.

    Returns:
        str: password string.
    """
    return getpass.getpass(text)


class ReauthChallenge(metaclass=abc.ABCMeta):
    """Base class for reauth challenges."""

    @property
    @abc.abstractmethod
    def name(self):  # pragma: NO COVER
        """Returns the name of the challenge."""
        raise NotImplementedError("name property must be implemented")

    @property
    @abc.abstractmethod
    def is_locally_eligible(self):  # pragma: NO COVER
        """Returns true if a challenge is supported locally on this machine."""
        raise NotImplementedError("is_locally_eligible property must be implemented")

    @abc.abstractmethod
    def obtain_challenge_input(self, metadata):  # pragma: NO COVER
        """Performs logic required to obtain credentials and returns it.

        Args:
            metadata (Mapping): challenge metadata returned in the 'challenges' field in
                the initial reauth request. Includes the 'challengeType' field
                and other challenge-specific fields.

        Returns:
            response that will be send to the reauth service as the content of
            the 'proposalResponse' field in the request body. Usually a dict
            with the keys specific to the challenge. For example,
            ``{'credential': password}`` for password challenge.
        """
        raise NotImplementedError("obtain_challenge_input method must be implemented")


class PasswordChallenge(ReauthChallenge):
    """Challenge that asks for user's password."""

    @property
    def name(self):
        return "PASSWORD"

    @property
    def is_locally_eligible(self):
        return True

    @_helpers.copy_docstring(ReauthChallenge)
    def obtain_challenge_input(self, unused_metadata):
        passwd = get_user_password("Please enter your password:")
        if not passwd:
            passwd = " "  # avoid the server crashing in case of no password :D
        return {"credential": passwd}


class SecurityKeyChallenge(ReauthChallenge):
    """Challenge that asks for user's security key touch."""

    @property
    def name(self):
        return "SECURITY_KEY"

    @property
    def is_locally_eligible(self):
        return True

    @_helpers.copy_docstring(ReauthChallenge)
    def obtain_challenge_input(self, metadata):
        # Check if there is an available Webauthn Handler, if not use pyu2f
        try:
            factory = webauthn_handler_factory.WebauthnHandlerFactory()
            webauthn_handler = factory.get_handler()
            if webauthn_handler is not None:
                sys.stderr.write("Please insert and touch your security key\n")
                return self._obtain_challenge_input_webauthn(metadata, webauthn_handler)
        except Exception:
            # Attempt pyu2f if exception in webauthn flow
            pass

        try:
            import pyu2f.convenience.authenticator  # type: ignore
            import pyu2f.errors  # type: ignore
            import pyu2f.model  # type: ignore
        except ImportError:
            raise exceptions.ReauthFailError(
                "pyu2f dependency is required to use Security key reauth feature. "
                "It can be installed via `pip install pyu2f` or `pip install google-auth[reauth]`."
            )
        sk = metadata["securityKey"]
        challenges = sk["challenges"]
        # Read both 'applicationId' and 'relyingPartyId', if they are the same, use
        # applicationId, if they are different, use relyingPartyId first and retry
        # with applicationId
        application_id = sk["applicationId"]
        relying_party_id = sk["relyingPartyId"]

        if application_id != relying_party_id:
            application_parameters = [relying_party_id, application_id]
        else:
            application_parameters = [application_id]

        challenge_data = []
        for c in challenges:
            kh = c["keyHandle"].encode("ascii")
            key = pyu2f.model.RegisteredKey(bytearray(base64.urlsafe_b64decode(kh)))
            challenge = c["challenge"].encode("ascii")
            challenge = base64.urlsafe_b64decode(challenge)
            challenge_data.append({"key": key, "challenge": challenge})

        # Track number of tries to suppress error message until all application_parameters
        # are tried.
        tries = 0
        for app_id in application_parameters:
            try:
                tries += 1
                api = pyu2f.convenience.authenticator.CreateCompositeAuthenticator(
                    REAUTH_ORIGIN
                )
                response = api.Authenticate(
                    app_id, challenge_data, print_callback=sys.stderr.write
                )
                return {"securityKey": response}
            except pyu2f.errors.U2FError as e:
                if e.code == pyu2f.errors.U2FError.DEVICE_INELIGIBLE:
                    # Only show error if all app_ids have been tried
                    if tries == len(application_parameters):
                        sys.stderr.write("Ineligible security key.\n")
                        return None
                    continue
                if e.code == pyu2f.errors.U2FError.TIMEOUT:
                    sys.stderr.write(
                        "Timed out while waiting for security key touch.\n"
                    )
                else:
                    raise e
            except pyu2f.errors.PluginError as e:
                sys.stderr.write("Plugin error: {}.\n".format(e))
                continue
            except pyu2f.errors.NoDeviceFoundError:
                sys.stderr.write("No security key found.\n")
            return None

    def _obtain_challenge_input_webauthn(self, metadata, webauthn_handler):
        sk = metadata.get("securityKey")
        if sk is None:
            raise exceptions.InvalidValue("securityKey is None")
        challenges = sk.get("challenges")
        application_id = sk.get("applicationId")
        relying_party_id = sk.get("relyingPartyId")
        if challenges is None or len(challenges) < 1:
            raise exceptions.InvalidValue("challenges is None or empty")
        if application_id is None:
            raise exceptions.InvalidValue("application_id is None")
        if relying_party_id is None:
            raise exceptions.InvalidValue("relying_party_id is None")

        allow_credentials = []
        for challenge in challenges:
            kh = challenge.get("keyHandle")
            if kh is None:
                raise exceptions.InvalidValue("keyHandle is None")
            key_handle = self._unpadded_urlsafe_b64recode(kh)
            allow_credentials.append(PublicKeyCredentialDescriptor(id=key_handle))

        extension = AuthenticationExtensionsClientInputs(appid=application_id)

        challenge = challenges[0].get("challenge")
        if challenge is None:
            raise exceptions.InvalidValue("challenge is None")

        get_request = GetRequest(
            origin=REAUTH_ORIGIN,
            rpid=relying_party_id,
            challenge=self._unpadded_urlsafe_b64recode(challenge),
            timeout_ms=WEBAUTHN_TIMEOUT_MS,
            allow_credentials=allow_credentials,
            user_verification="required",
            extensions=extension,
        )

        try:
            get_response = webauthn_handler.get(get_request)
        except Exception as e:
            sys.stderr.write("Webauthn Error: {}.\n".format(e))
            raise e

        response = {
            "clientData": get_response.response.client_data_json,
            "authenticatorData": get_response.response.authenticator_data,
            "signatureData": get_response.response.signature,
            "applicationId": application_id,
            "keyHandle": get_response.id,
            "securityKeyReplyType": 2,
        }
        return {"securityKey": response}

    def _unpadded_urlsafe_b64recode(self, s):
        """Converts standard b64 encoded string to url safe b64 encoded string
        with no padding."""
        b = base64.urlsafe_b64decode(s)
        return base64.urlsafe_b64encode(b).decode().rstrip("=")


class SamlChallenge(ReauthChallenge):
    """Challenge that asks the users to browse to their ID Providers.

    Currently SAML challenge is not supported. When obtaining the challenge
    input, exception will be raised to instruct the users to run
    `gcloud auth login` for reauthentication.
    """

    @property
    def name(self):
        return "SAML"

    @property
    def is_locally_eligible(self):
        return True

    def obtain_challenge_input(self, metadata):
        # Magic Arch has not fully supported returning a proper dedirect URL
        # for programmatic SAML users today. So we error our here and request
        # users to use gcloud to complete a login.
        raise exceptions.ReauthSamlChallengeFailError(SAML_CHALLENGE_MESSAGE)


AVAILABLE_CHALLENGES = {
    challenge.name: challenge
    for challenge in [SecurityKeyChallenge(), PasswordChallenge(), SamlChallenge()]
}

# === NexusCore/openenv\Lib\site-packages\litellm\integrations\prometheus_services.py ===
# used for monitoring litellm services health on `/metrics` endpoint on LiteLLM Proxy
#### What this does ####
#    On success + failure, log events to Prometheus for litellm / adjacent services (litellm, redis, postgres, llm api providers)


from typing import Dict, List, Optional, Union

from litellm._logging import print_verbose, verbose_logger
from litellm.types.integrations.prometheus import LATENCY_BUCKETS
from litellm.types.services import (
    DEFAULT_SERVICE_CONFIGS,
    ServiceLoggerPayload,
    ServiceMetrics,
    ServiceTypes,
)

FAILED_REQUESTS_LABELS = ["error_class", "function_name"]


class PrometheusServicesLogger:
    # Class variables or attributes
    litellm_service_latency = None  # Class-level attribute to store the Histogram

    def __init__(
        self,
        mock_testing: bool = False,
        **kwargs,
    ):
        try:
            try:
                from prometheus_client import REGISTRY, Counter, Gauge, Histogram
                from prometheus_client.gc_collector import Collector
            except ImportError:
                raise Exception(
                    "Missing prometheus_client. Run `pip install prometheus-client`"
                )

            self.Histogram = Histogram
            self.Counter = Counter
            self.Gauge = Gauge
            self.REGISTRY = REGISTRY

            verbose_logger.debug("in init prometheus services metrics")

            self.payload_to_prometheus_map: Dict[
                str, List[Union[Histogram, Counter, Gauge, Collector]]
            ] = {}

            for service in ServiceTypes:
                service_metrics: List[Union[Histogram, Counter, Gauge, Collector]] = []

                metrics_to_initialize = self._get_service_metrics_initialize(service)

                # Initialize only the configured metrics for each service
                if ServiceMetrics.HISTOGRAM in metrics_to_initialize:
                    histogram = self.create_histogram(
                        service.value, type_of_request="latency"
                    )
                    if histogram:
                        service_metrics.append(histogram)

                if ServiceMetrics.COUNTER in metrics_to_initialize:
                    counter_failed_request = self.create_counter(
                        service.value,
                        type_of_request="failed_requests",
                        additional_labels=FAILED_REQUESTS_LABELS,
                    )
                    if counter_failed_request:
                        service_metrics.append(counter_failed_request)
                    counter_total_requests = self.create_counter(
                        service.value, type_of_request="total_requests"
                    )
                    if counter_total_requests:
                        service_metrics.append(counter_total_requests)

                if ServiceMetrics.GAUGE in metrics_to_initialize:
                    gauge = self.create_gauge(service.value, type_of_request="size")
                    if gauge:
                        service_metrics.append(gauge)

                if service_metrics:
                    self.payload_to_prometheus_map[service.value] = service_metrics

            self.prometheus_to_amount_map: dict = {}
            ### MOCK TESTING ###
            self.mock_testing = mock_testing
            self.mock_testing_success_calls = 0
            self.mock_testing_failure_calls = 0

        except Exception as e:
            print_verbose(f"Got exception on init prometheus client {str(e)}")
            raise e

    def _get_service_metrics_initialize(
        self, service: ServiceTypes
    ) -> List[ServiceMetrics]:
        DEFAULT_METRICS = [ServiceMetrics.COUNTER, ServiceMetrics.HISTOGRAM]
        if service not in DEFAULT_SERVICE_CONFIGS:
            return DEFAULT_METRICS

        metrics = DEFAULT_SERVICE_CONFIGS.get(service, {}).get("metrics", [])
        if not metrics:
            verbose_logger.debug(f"No metrics found for service {service}")
            return DEFAULT_METRICS
        return metrics

    def is_metric_registered(self, metric_name) -> bool:
        for metric in self.REGISTRY.collect():
            if metric_name == metric.name:
                return True
        return False

    def _get_metric(self, metric_name):
        """
        Helper function to get a metric from the registry by name.
        """
        return self.REGISTRY._names_to_collectors.get(metric_name)

    def create_histogram(self, service: str, type_of_request: str):
        metric_name = "litellm_{}_{}".format(service, type_of_request)
        is_registered = self.is_metric_registered(metric_name)
        if is_registered:
            return self._get_metric(metric_name)
        return self.Histogram(
            metric_name,
            "Latency for {} service".format(service),
            labelnames=[service],
            buckets=LATENCY_BUCKETS,
        )

    def create_gauge(self, service: str, type_of_request: str):
        metric_name = "litellm_{}_{}".format(service, type_of_request)
        is_registered = self.is_metric_registered(metric_name)
        if is_registered:
            return self._get_metric(metric_name)
        return self.Gauge(
            metric_name, "Gauge for {} service".format(service), labelnames=[service]
        )

    def create_counter(
        self,
        service: str,
        type_of_request: str,
        additional_labels: Optional[List[str]] = None,
    ):
        metric_name = "litellm_{}_{}".format(service, type_of_request)
        is_registered = self.is_metric_registered(metric_name)
        if is_registered:
            return self._get_metric(metric_name)
        return self.Counter(
            metric_name,
            "Total {} for {} service".format(type_of_request, service),
            labelnames=[service] + (additional_labels or []),
        )

    def observe_histogram(
        self,
        histogram,
        labels: str,
        amount: float,
    ):
        assert isinstance(histogram, self.Histogram)

        histogram.labels(labels).observe(amount)

    def update_gauge(
        self,
        gauge,
        labels: str,
        amount: float,
    ):
        assert isinstance(gauge, self.Gauge)
        gauge.labels(labels).set(amount)

    def increment_counter(
        self,
        counter,
        labels: str,
        amount: float,
        additional_labels: Optional[List[str]] = [],
    ):
        assert isinstance(counter, self.Counter)

        if additional_labels:
            counter.labels(labels, *additional_labels).inc(amount)
        else:
            counter.labels(labels).inc(amount)

    def service_success_hook(self, payload: ServiceLoggerPayload):
        if self.mock_testing:
            self.mock_testing_success_calls += 1

        if payload.service.value in self.payload_to_prometheus_map:
            prom_objects = self.payload_to_prometheus_map[payload.service.value]
            for obj in prom_objects:
                if isinstance(obj, self.Histogram):
                    self.observe_histogram(
                        histogram=obj,
                        labels=payload.service.value,
                        amount=payload.duration,
                    )
                elif isinstance(obj, self.Counter) and "total_requests" in obj._name:
                    self.increment_counter(
                        counter=obj,
                        labels=payload.service.value,
                        amount=1,  # LOG TOTAL REQUESTS TO PROMETHEUS
                    )

    def service_failure_hook(self, payload: ServiceLoggerPayload):
        if self.mock_testing:
            self.mock_testing_failure_calls += 1

        if payload.service.value in self.payload_to_prometheus_map:
            prom_objects = self.payload_to_prometheus_map[payload.service.value]
            for obj in prom_objects:
                if isinstance(obj, self.Counter):
                    self.increment_counter(
                        counter=obj,
                        labels=payload.service.value,
                        amount=1,  # LOG ERROR COUNT / TOTAL REQUESTS TO PROMETHEUS
                    )

    async def async_service_success_hook(self, payload: ServiceLoggerPayload):
        """
        Log successful call to prometheus
        """
        if self.mock_testing:
            self.mock_testing_success_calls += 1

        if payload.service.value in self.payload_to_prometheus_map:
            prom_objects = self.payload_to_prometheus_map[payload.service.value]
            for obj in prom_objects:
                if isinstance(obj, self.Histogram):
                    self.observe_histogram(
                        histogram=obj,
                        labels=payload.service.value,
                        amount=payload.duration,
                    )
                elif isinstance(obj, self.Counter) and "total_requests" in obj._name:
                    self.increment_counter(
                        counter=obj,
                        labels=payload.service.value,
                        amount=1,  # LOG TOTAL REQUESTS TO PROMETHEUS
                    )
                elif isinstance(obj, self.Gauge):
                    if payload.event_metadata:
                        self.update_gauge(
                            gauge=obj,
                            labels=payload.event_metadata.get("gauge_labels") or "",
                            amount=payload.event_metadata.get("gauge_value") or 0,
                        )

    async def async_service_failure_hook(
        self,
        payload: ServiceLoggerPayload,
        error: Union[str, Exception],
    ):
        if self.mock_testing:
            self.mock_testing_failure_calls += 1
        error_class = error.__class__.__name__
        function_name = payload.call_type

        if payload.service.value in self.payload_to_prometheus_map:
            prom_objects = self.payload_to_prometheus_map[payload.service.value]
            for obj in prom_objects:
                # increment both failed and total requests
                if isinstance(obj, self.Counter):
                    if "failed_requests" in obj._name:
                        self.increment_counter(
                            counter=obj,
                            labels=payload.service.value,
                            # log additional_labels=["error_class", "function_name"], used for debugging what's going wrong with the DB
                            additional_labels=[error_class, function_name],
                            amount=1,  # LOG ERROR COUNT TO PROMETHEUS
                        )
                    else:
                        self.increment_counter(
                            counter=obj,
                            labels=payload.service.value,
                            amount=1,  # LOG TOTAL REQUESTS TO PROMETHEUS
                        )

# === NexusCore/openenv\Lib\site-packages\litellm\proxy\common_utils\debug_utils.py ===
# Start tracing memory allocations
import asyncio
import json
import os
import tracemalloc
from collections import Counter

from fastapi import APIRouter

from litellm import get_secret_str
from litellm._logging import verbose_proxy_logger

router = APIRouter()


@router.get("/debug/asyncio-tasks")
async def get_active_tasks_stats():
    """
    Returns:
      total_active_tasks: int
      by_name: { coroutine_name: count }
    """
    MAX_TASKS_TO_CHECK = 5000
    # Gather all tasks in this event loop (including this endpoint’s own task).
    all_tasks = asyncio.all_tasks()

    # Filter out tasks that are already done.
    active_tasks = [t for t in all_tasks if not t.done()]

    # Count how many active tasks exist, grouped by coroutine function name.
    counter = Counter()
    for idx, task in enumerate(active_tasks):

        # reasonable max circuit breaker
        if idx >= MAX_TASKS_TO_CHECK:
            break
        coro = task.get_coro()
        # Derive a human‐readable name from the coroutine:
        name = (
            getattr(coro, "__qualname__", None)
            or getattr(coro, "__name__", None)
            or repr(coro)
        )
        counter[name] += 1

    return {
        "total_active_tasks": len(active_tasks),
        "by_name": dict(counter),
    }


if os.environ.get("LITELLM_PROFILE", "false").lower() == "true":
    try:
        import objgraph  # type: ignore

        print("growth of objects")  # noqa
        objgraph.show_growth()
        print("\n\nMost common types")  # noqa
        objgraph.show_most_common_types()
        roots = objgraph.get_leaking_objects()
        print("\n\nLeaking objects")  # noqa
        objgraph.show_most_common_types(objects=roots)
    except ImportError:
        raise ImportError(
            "objgraph not found. Please install objgraph to use this feature."
        )

    tracemalloc.start(10)

    @router.get("/memory-usage", include_in_schema=False)
    async def memory_usage():
        # Take a snapshot of the current memory usage
        snapshot = tracemalloc.take_snapshot()
        top_stats = snapshot.statistics("lineno")
        verbose_proxy_logger.debug("TOP STATS: %s", top_stats)

        # Get the top 50 memory usage lines
        top_50 = top_stats[:50]
        result = []
        for stat in top_50:
            result.append(f"{stat.traceback.format(limit=10)}: {stat.size / 1024} KiB")

        return {"top_50_memory_usage": result}


@router.get("/memory-usage-in-mem-cache", include_in_schema=False)
async def memory_usage_in_mem_cache():
    # returns the size of all in-memory caches on the proxy server
    """
    1. user_api_key_cache
    2. router_cache
    3. proxy_logging_cache
    4. internal_usage_cache
    """
    from litellm.proxy.proxy_server import (
        llm_router,
        proxy_logging_obj,
        user_api_key_cache,
    )

    if llm_router is None:
        num_items_in_llm_router_cache = 0
    else:
        num_items_in_llm_router_cache = len(
            llm_router.cache.in_memory_cache.cache_dict
        ) + len(llm_router.cache.in_memory_cache.ttl_dict)

    num_items_in_user_api_key_cache = len(
        user_api_key_cache.in_memory_cache.cache_dict
    ) + len(user_api_key_cache.in_memory_cache.ttl_dict)

    num_items_in_proxy_logging_obj_cache = len(
        proxy_logging_obj.internal_usage_cache.dual_cache.in_memory_cache.cache_dict
    ) + len(proxy_logging_obj.internal_usage_cache.dual_cache.in_memory_cache.ttl_dict)

    return {
        "num_items_in_user_api_key_cache": num_items_in_user_api_key_cache,
        "num_items_in_llm_router_cache": num_items_in_llm_router_cache,
        "num_items_in_proxy_logging_obj_cache": num_items_in_proxy_logging_obj_cache,
    }


@router.get("/memory-usage-in-mem-cache-items", include_in_schema=False)
async def memory_usage_in_mem_cache_items():
    # returns the size of all in-memory caches on the proxy server
    """
    1. user_api_key_cache
    2. router_cache
    3. proxy_logging_cache
    4. internal_usage_cache
    """
    from litellm.proxy.proxy_server import (
        llm_router,
        proxy_logging_obj,
        user_api_key_cache,
    )

    if llm_router is None:
        llm_router_in_memory_cache_dict = {}
        llm_router_in_memory_ttl_dict = {}
    else:
        llm_router_in_memory_cache_dict = llm_router.cache.in_memory_cache.cache_dict
        llm_router_in_memory_ttl_dict = llm_router.cache.in_memory_cache.ttl_dict

    return {
        "user_api_key_cache": user_api_key_cache.in_memory_cache.cache_dict,
        "user_api_key_ttl": user_api_key_cache.in_memory_cache.ttl_dict,
        "llm_router_cache": llm_router_in_memory_cache_dict,
        "llm_router_ttl": llm_router_in_memory_ttl_dict,
        "proxy_logging_obj_cache": proxy_logging_obj.internal_usage_cache.dual_cache.in_memory_cache.cache_dict,
        "proxy_logging_obj_ttl": proxy_logging_obj.internal_usage_cache.dual_cache.in_memory_cache.ttl_dict,
    }


@router.get("/otel-spans", include_in_schema=False)
async def get_otel_spans():
    from litellm.proxy.proxy_server import open_telemetry_logger

    if open_telemetry_logger is None:
        return {
            "otel_spans": [],
            "spans_grouped_by_parent": {},
            "most_recent_parent": None,
        }

    otel_exporter = open_telemetry_logger.OTEL_EXPORTER
    if hasattr(otel_exporter, "get_finished_spans"):
        recorded_spans = otel_exporter.get_finished_spans()  # type: ignore
    else:
        recorded_spans = []

    print("Spans: ", recorded_spans)  # noqa

    most_recent_parent = None
    most_recent_start_time = 1000000
    spans_grouped_by_parent = {}
    for span in recorded_spans:
        if span.parent is not None:
            parent_trace_id = span.parent.trace_id
            if parent_trace_id not in spans_grouped_by_parent:
                spans_grouped_by_parent[parent_trace_id] = []
            spans_grouped_by_parent[parent_trace_id].append(span.name)

            # check time of span
            if span.start_time > most_recent_start_time:
                most_recent_parent = parent_trace_id
                most_recent_start_time = span.start_time

    # these are otel spans - get the span name
    span_names = [span.name for span in recorded_spans]
    return {
        "otel_spans": span_names,
        "spans_grouped_by_parent": spans_grouped_by_parent,
        "most_recent_parent": most_recent_parent,
    }


# Helper functions for debugging
def init_verbose_loggers():
    try:
        worker_config = get_secret_str("WORKER_CONFIG")
        # if not, assume it's a json string
        if worker_config is None:
            return
        if os.path.isfile(worker_config):
            return
        _settings = json.loads(worker_config)
        if not isinstance(_settings, dict):
            return

        debug = _settings.get("debug", None)
        detailed_debug = _settings.get("detailed_debug", None)
        if debug is True:  # this needs to be first, so users can see Router init debugg
            import logging

            from litellm._logging import (
                verbose_logger,
                verbose_proxy_logger,
                verbose_router_logger,
            )

            # this must ALWAYS remain logging.INFO, DO NOT MODIFY THIS
            verbose_logger.setLevel(level=logging.INFO)  # sets package logs to info
            verbose_router_logger.setLevel(
                level=logging.INFO
            )  # set router logs to info
            verbose_proxy_logger.setLevel(level=logging.INFO)  # set proxy logs to info
        if detailed_debug is True:
            import logging

            from litellm._logging import (
                verbose_logger,
                verbose_proxy_logger,
                verbose_router_logger,
            )

            verbose_logger.setLevel(level=logging.DEBUG)  # set package log to debug
            verbose_router_logger.setLevel(
                level=logging.DEBUG
            )  # set router logs to debug
            verbose_proxy_logger.setLevel(
                level=logging.DEBUG
            )  # set proxy logs to debug
        elif debug is False and detailed_debug is False:
            # users can control proxy debugging using env variable = 'LITELLM_LOG'
            litellm_log_setting = os.environ.get("LITELLM_LOG", "")
            if litellm_log_setting is not None:
                if litellm_log_setting.upper() == "INFO":
                    import logging

                    from litellm._logging import (
                        verbose_proxy_logger,
                        verbose_router_logger,
                    )

                    # this must ALWAYS remain logging.INFO, DO NOT MODIFY THIS

                    verbose_router_logger.setLevel(
                        level=logging.INFO
                    )  # set router logs to info
                    verbose_proxy_logger.setLevel(
                        level=logging.INFO
                    )  # set proxy logs to info
                elif litellm_log_setting.upper() == "DEBUG":
                    import logging

                    from litellm._logging import (
                        verbose_proxy_logger,
                        verbose_router_logger,
                    )

                    verbose_router_logger.setLevel(
                        level=logging.DEBUG
                    )  # set router logs to info
                    verbose_proxy_logger.setLevel(
                        level=logging.DEBUG
                    )  # set proxy logs to debug
    except Exception as e:
        import logging

        logging.warning(f"Failed to init verbose loggers: {str(e)}")

# === NexusCore/openenv\Lib\site-packages\litellm\proxy\image_endpoints\endpoints.py ===
import asyncio
import traceback
from typing import List

import orjson
from fastapi import APIRouter, Depends, File, HTTPException, Request, Response, status
from fastapi.responses import ORJSONResponse

import litellm
from litellm._logging import verbose_proxy_logger
from litellm.proxy._types import *
from litellm.proxy.auth.user_api_key_auth import UserAPIKeyAuth, user_api_key_auth
from litellm.proxy.common_request_processing import ProxyBaseLLMRequestProcessing
from litellm.proxy.route_llm_request import route_request

router = APIRouter()

import io

from fastapi import UploadFile


async def uploadfile_to_bytesio(upload: UploadFile) -> io.BytesIO:
    """
    Read a FastAPI UploadFile into a BytesIO and set .name so OpenAI SDK
    infers filename/content-type correctly.
    """
    data = await upload.read()
    buffer = io.BytesIO(data)
    buffer.name = upload.filename
    return buffer


async def batch_to_bytesio(
    uploads: Optional[List[UploadFile]],
) -> Optional[List[io.BytesIO]]:
    """
    Convert a list of UploadFiles to a list of BytesIO buffers, or None.
    """
    if not uploads:
        return None
    return [await uploadfile_to_bytesio(u) for u in uploads]


@router.post(
    "/v1/images/generations",
    dependencies=[Depends(user_api_key_auth)],
    response_class=ORJSONResponse,
    tags=["images"],
)
@router.post(
    "/images/generations",
    dependencies=[Depends(user_api_key_auth)],
    response_class=ORJSONResponse,
    tags=["images"],
)
@router.post(
    "/openai/deployments/{model:path}/images/generations",
    dependencies=[Depends(user_api_key_auth)],
    response_class=ORJSONResponse,
    tags=["images"],
)  # azure compatible endpoint
async def image_generation(
    request: Request,
    fastapi_response: Response,
    user_api_key_dict: UserAPIKeyAuth = Depends(user_api_key_auth),
    model: Optional[str] = None,
):
    from litellm.proxy.proxy_server import (
        add_litellm_data_to_request,
        general_settings,
        llm_router,
        proxy_config,
        proxy_logging_obj,
        user_model,
        version,
    )

    data = {}
    try:
        # Use orjson to parse JSON data, orjson speeds up requests significantly
        body = await request.body()
        data = orjson.loads(body)

        # Include original request and headers in the data
        data = await add_litellm_data_to_request(
            data=data,
            request=request,
            general_settings=general_settings,
            user_api_key_dict=user_api_key_dict,
            version=version,
            proxy_config=proxy_config,
        )

        data["model"] = (
            model
            or general_settings.get("image_generation_model", None)  # server default
            or user_model  # model name passed via cli args
            or data.get("model", None)  # default passed in http request
        )
        if user_model:
            data["model"] = user_model

        ### MODEL ALIAS MAPPING ###
        # check if model name in model alias map
        # get the actual model name
        if data["model"] in litellm.model_alias_map:
            data["model"] = litellm.model_alias_map[data["model"]]

        ### CALL HOOKS ### - modify incoming data / reject request before calling the model
        data = await proxy_logging_obj.pre_call_hook(
            user_api_key_dict=user_api_key_dict, data=data, call_type="image_generation"
        )

        ## ROUTE TO CORRECT ENDPOINT ##
        llm_call = await route_request(
            data=data,
            route_type="aimage_generation",
            llm_router=llm_router,
            user_model=user_model,
        )
        response = await llm_call

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
        response_cost = hidden_params.get("response_cost", None) or ""
        litellm_call_id = hidden_params.get("litellm_call_id", None) or ""

        fastapi_response.headers.update(
            ProxyBaseLLMRequestProcessing.get_custom_headers(
                user_api_key_dict=user_api_key_dict,
                model_id=model_id,
                cache_key=cache_key,
                api_base=api_base,
                version=version,
                response_cost=response_cost,
                model_region=getattr(user_api_key_dict, "allowed_model_region", ""),
                call_id=litellm_call_id,
                request_data=data,
                hidden_params=hidden_params,
            )
        )

        return response
    except Exception as e:
        await proxy_logging_obj.post_call_failure_hook(
            user_api_key_dict=user_api_key_dict, original_exception=e, request_data=data
        )
        verbose_proxy_logger.error(
            "litellm.proxy.proxy_server.image_generation(): Exception occured - {}".format(
                str(e)
            )
        )
        verbose_proxy_logger.debug(traceback.format_exc())
        if isinstance(e, HTTPException):
            raise ProxyException(
                message=getattr(e, "message", str(e)),
                type=getattr(e, "type", "None"),
                param=getattr(e, "param", "None"),
                code=getattr(e, "status_code", status.HTTP_400_BAD_REQUEST),
            )
        else:
            error_msg = f"{str(e)}"
            raise ProxyException(
                message=getattr(e, "message", error_msg),
                type=getattr(e, "type", "None"),
                param=getattr(e, "param", "None"),
                openai_code=getattr(e, "code", None),
                code=getattr(e, "status_code", 500),
            )


@router.post(
    "/v1/images/edits",
    dependencies=[Depends(user_api_key_auth)],
    tags=["images"],
)
@router.post(
    "/images/edits",
    dependencies=[Depends(user_api_key_auth)],
    tags=["images"],
)
@router.post(
    "/openai/deployments/{model:path}/images/edits",
    dependencies=[Depends(user_api_key_auth)],
    response_class=ORJSONResponse,
    tags=["images"],
)  # azure compatible endpoint
async def image_edit_api(
    request: Request,
    fastapi_response: Response,
    image: List[UploadFile] = File(...),
    mask: Optional[List[UploadFile]] = File(None),
    user_api_key_dict: UserAPIKeyAuth = Depends(user_api_key_auth),
    model: Optional[str] = None,
):
    """
    Follows the OpenAI Images API spec: https://platform.openai.com/docs/api-reference/images/create

    ```bash
    curl -s -D >(grep -i x-request-id >&2) \
    -o >(jq -r '.data[0].b64_json' | base64 --decode > gift-basket.png) \
    -X POST "http://localhost:4000/v1/images/edits" \
    -H "Authorization: Bearer sk-1234" \
        -F "model=gpt-image-1" \
        -F "image[]=@soap.png" \
        -F 'prompt=Create a studio ghibli image of this'
    ```
    """
    from litellm.proxy.proxy_server import (
        _read_request_body,
        general_settings,
        llm_router,
        proxy_config,
        proxy_logging_obj,
        select_data_generator,
        user_api_base,
        user_max_tokens,
        user_model,
        user_request_timeout,
        user_temperature,
        version,
    )

    #########################################################
    # Read request body and convert UploadFiles to BytesIO
    #########################################################
    data = await _read_request_body(request=request)
    image_files = await batch_to_bytesio(image)
    mask_files = await batch_to_bytesio(mask)
    if image_files:
        data["image"] = image_files
    if mask_files:
        data["mask"] = mask_files

    data["model"] = (
        model
        or general_settings.get("image_generation_model", None)  # server default
        or user_model  # model name passed via cli args
        or data.get("model", None)  # default passed in http request
    )
    #########################################################
    # Process request
    #########################################################

    processor = ProxyBaseLLMRequestProcessing(data=data)
    try:
        return await processor.base_process_llm_request(
            request=request,
            fastapi_response=fastapi_response,
            user_api_key_dict=user_api_key_dict,
            route_type="aimage_edit",
            proxy_logging_obj=proxy_logging_obj,
            llm_router=llm_router,
            general_settings=general_settings,
            proxy_config=proxy_config,
            select_data_generator=select_data_generator,
            model=None,
            user_model=user_model,
            user_temperature=user_temperature,
            user_request_timeout=user_request_timeout,
            user_max_tokens=user_max_tokens,
            user_api_base=user_api_base,
            version=version,
        )
    except Exception as e:
        raise await processor._handle_llm_api_exception(
            e=e,
            user_api_key_dict=user_api_key_dict,
            proxy_logging_obj=proxy_logging_obj,
            version=version,
        )

# === NexusCore/openenv\Lib\site-packages\openai\types\beta\realtime\session.py ===
# File generated from our OpenAPI spec by Stainless. See CONTRIBUTING.md for details.

from typing import List, Union, Optional
from typing_extensions import Literal, TypeAlias

from ...._models import BaseModel

__all__ = [
    "Session",
    "InputAudioNoiseReduction",
    "InputAudioTranscription",
    "Tool",
    "Tracing",
    "TracingTracingConfiguration",
    "TurnDetection",
]


class InputAudioNoiseReduction(BaseModel):
    type: Optional[Literal["near_field", "far_field"]] = None
    """Type of noise reduction.

    `near_field` is for close-talking microphones such as headphones, `far_field` is
    for far-field microphones such as laptop or conference room microphones.
    """


class InputAudioTranscription(BaseModel):
    language: Optional[str] = None
    """The language of the input audio.

    Supplying the input language in
    [ISO-639-1](https://en.wikipedia.org/wiki/List_of_ISO_639-1_codes) (e.g. `en`)
    format will improve accuracy and latency.
    """

    model: Optional[str] = None
    """
    The model to use for transcription, current options are `gpt-4o-transcribe`,
    `gpt-4o-mini-transcribe`, and `whisper-1`.
    """

    prompt: Optional[str] = None
    """
    An optional text to guide the model's style or continue a previous audio
    segment. For `whisper-1`, the
    [prompt is a list of keywords](https://platform.openai.com/docs/guides/speech-to-text#prompting).
    For `gpt-4o-transcribe` models, the prompt is a free text string, for example
    "expect words related to technology".
    """


class Tool(BaseModel):
    description: Optional[str] = None
    """
    The description of the function, including guidance on when and how to call it,
    and guidance about what to tell the user when calling (if anything).
    """

    name: Optional[str] = None
    """The name of the function."""

    parameters: Optional[object] = None
    """Parameters of the function in JSON Schema."""

    type: Optional[Literal["function"]] = None
    """The type of the tool, i.e. `function`."""


class TracingTracingConfiguration(BaseModel):
    group_id: Optional[str] = None
    """
    The group id to attach to this trace to enable filtering and grouping in the
    traces dashboard.
    """

    metadata: Optional[object] = None
    """
    The arbitrary metadata to attach to this trace to enable filtering in the traces
    dashboard.
    """

    workflow_name: Optional[str] = None
    """The name of the workflow to attach to this trace.

    This is used to name the trace in the traces dashboard.
    """


Tracing: TypeAlias = Union[Literal["auto"], TracingTracingConfiguration]


class TurnDetection(BaseModel):
    create_response: Optional[bool] = None
    """
    Whether or not to automatically generate a response when a VAD stop event
    occurs.
    """

    eagerness: Optional[Literal["low", "medium", "high", "auto"]] = None
    """Used only for `semantic_vad` mode.

    The eagerness of the model to respond. `low` will wait longer for the user to
    continue speaking, `high` will respond more quickly. `auto` is the default and
    is equivalent to `medium`.
    """

    interrupt_response: Optional[bool] = None
    """
    Whether or not to automatically interrupt any ongoing response with output to
    the default conversation (i.e. `conversation` of `auto`) when a VAD start event
    occurs.
    """

    prefix_padding_ms: Optional[int] = None
    """Used only for `server_vad` mode.

    Amount of audio to include before the VAD detected speech (in milliseconds).
    Defaults to 300ms.
    """

    silence_duration_ms: Optional[int] = None
    """Used only for `server_vad` mode.

    Duration of silence to detect speech stop (in milliseconds). Defaults to 500ms.
    With shorter values the model will respond more quickly, but may jump in on
    short pauses from the user.
    """

    threshold: Optional[float] = None
    """Used only for `server_vad` mode.

    Activation threshold for VAD (0.0 to 1.0), this defaults to 0.5. A higher
    threshold will require louder audio to activate the model, and thus might
    perform better in noisy environments.
    """

    type: Optional[Literal["server_vad", "semantic_vad"]] = None
    """Type of turn detection."""


class Session(BaseModel):
    id: Optional[str] = None
    """Unique identifier for the session that looks like `sess_1234567890abcdef`."""

    input_audio_format: Optional[Literal["pcm16", "g711_ulaw", "g711_alaw"]] = None
    """The format of input audio.

    Options are `pcm16`, `g711_ulaw`, or `g711_alaw`. For `pcm16`, input audio must
    be 16-bit PCM at a 24kHz sample rate, single channel (mono), and little-endian
    byte order.
    """

    input_audio_noise_reduction: Optional[InputAudioNoiseReduction] = None
    """Configuration for input audio noise reduction.

    This can be set to `null` to turn off. Noise reduction filters audio added to
    the input audio buffer before it is sent to VAD and the model. Filtering the
    audio can improve VAD and turn detection accuracy (reducing false positives) and
    model performance by improving perception of the input audio.
    """

    input_audio_transcription: Optional[InputAudioTranscription] = None
    """
    Configuration for input audio transcription, defaults to off and can be set to
    `null` to turn off once on. Input audio transcription is not native to the
    model, since the model consumes audio directly. Transcription runs
    asynchronously through
    [the /audio/transcriptions endpoint](https://platform.openai.com/docs/api-reference/audio/createTranscription)
    and should be treated as guidance of input audio content rather than precisely
    what the model heard. The client can optionally set the language and prompt for
    transcription, these offer additional guidance to the transcription service.
    """

    instructions: Optional[str] = None
    """The default system instructions (i.e.

    system message) prepended to model calls. This field allows the client to guide
    the model on desired responses. The model can be instructed on response content
    and format, (e.g. "be extremely succinct", "act friendly", "here are examples of
    good responses") and on audio behavior (e.g. "talk quickly", "inject emotion
    into your voice", "laugh frequently"). The instructions are not guaranteed to be
    followed by the model, but they provide guidance to the model on the desired
    behavior.

    Note that the server sets default instructions which will be used if this field
    is not set and are visible in the `session.created` event at the start of the
    session.
    """

    max_response_output_tokens: Union[int, Literal["inf"], None] = None
    """
    Maximum number of output tokens for a single assistant response, inclusive of
    tool calls. Provide an integer between 1 and 4096 to limit output tokens, or
    `inf` for the maximum available tokens for a given model. Defaults to `inf`.
    """

    modalities: Optional[List[Literal["text", "audio"]]] = None
    """The set of modalities the model can respond with.

    To disable audio, set this to ["text"].
    """

    model: Optional[
        Literal[
            "gpt-4o-realtime-preview",
            "gpt-4o-realtime-preview-2024-10-01",
            "gpt-4o-realtime-preview-2024-12-17",
            "gpt-4o-realtime-preview-2025-06-03",
            "gpt-4o-mini-realtime-preview",
            "gpt-4o-mini-realtime-preview-2024-12-17",
        ]
    ] = None
    """The Realtime model used for this session."""

    output_audio_format: Optional[Literal["pcm16", "g711_ulaw", "g711_alaw"]] = None
    """The format of output audio.

    Options are `pcm16`, `g711_ulaw`, or `g711_alaw`. For `pcm16`, output audio is
    sampled at a rate of 24kHz.
    """

    speed: Optional[float] = None
    """The speed of the model's spoken response.

    1.0 is the default speed. 0.25 is the minimum speed. 1.5 is the maximum speed.
    This value can only be changed in between model turns, not while a response is
    in progress.
    """

    temperature: Optional[float] = None
    """Sampling temperature for the model, limited to [0.6, 1.2].

    For audio models a temperature of 0.8 is highly recommended for best
    performance.
    """

    tool_choice: Optional[str] = None
    """How the model chooses tools.

    Options are `auto`, `none`, `required`, or specify a function.
    """

    tools: Optional[List[Tool]] = None
    """Tools (functions) available to the model."""

    tracing: Optional[Tracing] = None
    """Configuration options for tracing.

    Set to null to disable tracing. Once tracing is enabled for a session, the
    configuration cannot be modified.

    `auto` will create a trace for the session with default values for the workflow
    name, group id, and metadata.
    """

    turn_detection: Optional[TurnDetection] = None
    """Configuration for turn detection, ether Server VAD or Semantic VAD.

    This can be set to `null` to turn off, in which case the client must manually
    trigger model response. Server VAD means that the model will detect the start
    and end of speech based on audio volume and respond at the end of user speech.
    Semantic VAD is more advanced and uses a turn detection model (in conjuction
    with VAD) to semantically estimate whether the user has finished speaking, then
    dynamically sets a timeout based on this probability. For example, if user audio
    trails off with "uhhm", the model will score a low probability of turn end and
    wait longer for the user to continue speaking. This can be useful for more
    natural conversations, but may have a higher latency.
    """

    voice: Union[
        str,
        Literal["alloy", "ash", "ballad", "coral", "echo", "fable", "onyx", "nova", "sage", "shimmer", "verse"],
        None,
    ] = None
    """The voice the model uses to respond.

    Voice cannot be changed during the session once the model has responded with
    audio at least once. Current voice options are `alloy`, `ash`, `ballad`,
    `coral`, `echo`, `fable`, `onyx`, `nova`, `sage`, `shimmer`, and `verse`.
    """

# === NexusCore/openenv\Lib\site-packages\selenium\webdriver\common\devtools\v135\fed_cm.py ===
# DO NOT EDIT THIS FILE!
#
# This file is generated from the CDP specification. If you need to make
# changes, edit the generator and regenerate all of the modules.
#
# CDP domain: FedCm (experimental)
from __future__ import annotations
from .util import event_class, T_JSON_DICT
from dataclasses import dataclass
import enum
import typing

class LoginState(enum.Enum):
    '''
    Whether this is a sign-up or sign-in action for this account, i.e.
    whether this account has ever been used to sign in to this RP before.
    '''
    SIGN_IN = "SignIn"
    SIGN_UP = "SignUp"

    def to_json(self):
        return self.value

    @classmethod
    def from_json(cls, json):
        return cls(json)


class DialogType(enum.Enum):
    '''
    The types of FedCM dialogs.
    '''
    ACCOUNT_CHOOSER = "AccountChooser"
    AUTO_REAUTHN = "AutoReauthn"
    CONFIRM_IDP_LOGIN = "ConfirmIdpLogin"
    ERROR = "Error"

    def to_json(self):
        return self.value

    @classmethod
    def from_json(cls, json):
        return cls(json)


class DialogButton(enum.Enum):
    '''
    The buttons on the FedCM dialog.
    '''
    CONFIRM_IDP_LOGIN_CONTINUE = "ConfirmIdpLoginContinue"
    ERROR_GOT_IT = "ErrorGotIt"
    ERROR_MORE_DETAILS = "ErrorMoreDetails"

    def to_json(self):
        return self.value

    @classmethod
    def from_json(cls, json):
        return cls(json)


class AccountUrlType(enum.Enum):
    '''
    The URLs that each account has
    '''
    TERMS_OF_SERVICE = "TermsOfService"
    PRIVACY_POLICY = "PrivacyPolicy"

    def to_json(self):
        return self.value

    @classmethod
    def from_json(cls, json):
        return cls(json)


@dataclass
class Account:
    '''
    Corresponds to IdentityRequestAccount
    '''
    account_id: str

    email: str

    name: str

    given_name: str

    picture_url: str

    idp_config_url: str

    idp_login_url: str

    login_state: LoginState

    #: These two are only set if the loginState is signUp
    terms_of_service_url: typing.Optional[str] = None

    privacy_policy_url: typing.Optional[str] = None

    def to_json(self):
        json = dict()
        json['accountId'] = self.account_id
        json['email'] = self.email
        json['name'] = self.name
        json['givenName'] = self.given_name
        json['pictureUrl'] = self.picture_url
        json['idpConfigUrl'] = self.idp_config_url
        json['idpLoginUrl'] = self.idp_login_url
        json['loginState'] = self.login_state.to_json()
        if self.terms_of_service_url is not None:
            json['termsOfServiceUrl'] = self.terms_of_service_url
        if self.privacy_policy_url is not None:
            json['privacyPolicyUrl'] = self.privacy_policy_url
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            account_id=str(json['accountId']),
            email=str(json['email']),
            name=str(json['name']),
            given_name=str(json['givenName']),
            picture_url=str(json['pictureUrl']),
            idp_config_url=str(json['idpConfigUrl']),
            idp_login_url=str(json['idpLoginUrl']),
            login_state=LoginState.from_json(json['loginState']),
            terms_of_service_url=str(json['termsOfServiceUrl']) if 'termsOfServiceUrl' in json else None,
            privacy_policy_url=str(json['privacyPolicyUrl']) if 'privacyPolicyUrl' in json else None,
        )


def enable(
        disable_rejection_delay: typing.Optional[bool] = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    :param disable_rejection_delay: *(Optional)* Allows callers to disable the promise rejection delay that would normally happen, if this is unimportant to what's being tested. (step 4 of https://fedidcg.github.io/FedCM/#browser-api-rp-sign-in)
    '''
    params: T_JSON_DICT = dict()
    if disable_rejection_delay is not None:
        params['disableRejectionDelay'] = disable_rejection_delay
    cmd_dict: T_JSON_DICT = {
        'method': 'FedCm.enable',
        'params': params,
    }
    json = yield cmd_dict


def disable() -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:

    cmd_dict: T_JSON_DICT = {
        'method': 'FedCm.disable',
    }
    json = yield cmd_dict


def select_account(
        dialog_id: str,
        account_index: int
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    :param dialog_id:
    :param account_index:
    '''
    params: T_JSON_DICT = dict()
    params['dialogId'] = dialog_id
    params['accountIndex'] = account_index
    cmd_dict: T_JSON_DICT = {
        'method': 'FedCm.selectAccount',
        'params': params,
    }
    json = yield cmd_dict


def click_dialog_button(
        dialog_id: str,
        dialog_button: DialogButton
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    :param dialog_id:
    :param dialog_button:
    '''
    params: T_JSON_DICT = dict()
    params['dialogId'] = dialog_id
    params['dialogButton'] = dialog_button.to_json()
    cmd_dict: T_JSON_DICT = {
        'method': 'FedCm.clickDialogButton',
        'params': params,
    }
    json = yield cmd_dict


def open_url(
        dialog_id: str,
        account_index: int,
        account_url_type: AccountUrlType
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    :param dialog_id:
    :param account_index:
    :param account_url_type:
    '''
    params: T_JSON_DICT = dict()
    params['dialogId'] = dialog_id
    params['accountIndex'] = account_index
    params['accountUrlType'] = account_url_type.to_json()
    cmd_dict: T_JSON_DICT = {
        'method': 'FedCm.openUrl',
        'params': params,
    }
    json = yield cmd_dict


def dismiss_dialog(
        dialog_id: str,
        trigger_cooldown: typing.Optional[bool] = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    :param dialog_id:
    :param trigger_cooldown: *(Optional)*
    '''
    params: T_JSON_DICT = dict()
    params['dialogId'] = dialog_id
    if trigger_cooldown is not None:
        params['triggerCooldown'] = trigger_cooldown
    cmd_dict: T_JSON_DICT = {
        'method': 'FedCm.dismissDialog',
        'params': params,
    }
    json = yield cmd_dict


def reset_cooldown() -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Resets the cooldown time, if any, to allow the next FedCM call to show
    a dialog even if one was recently dismissed by the user.
    '''
    cmd_dict: T_JSON_DICT = {
        'method': 'FedCm.resetCooldown',
    }
    json = yield cmd_dict


@event_class('FedCm.dialogShown')
@dataclass
class DialogShown:
    dialog_id: str
    dialog_type: DialogType
    accounts: typing.List[Account]
    #: These exist primarily so that the caller can verify the
    #: RP context was used appropriately.
    title: str
    subtitle: typing.Optional[str]

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> DialogShown:
        return cls(
            dialog_id=str(json['dialogId']),
            dialog_type=DialogType.from_json(json['dialogType']),
            accounts=[Account.from_json(i) for i in json['accounts']],
            title=str(json['title']),
            subtitle=str(json['subtitle']) if 'subtitle' in json else None
        )


@event_class('FedCm.dialogClosed')
@dataclass
class DialogClosed:
    '''
    Triggered when a dialog is closed, either by user action, JS abort,
    or a command below.
    '''
    dialog_id: str

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> DialogClosed:
        return cls(
            dialog_id=str(json['dialogId'])
        )

# === NexusCore/openenv\Lib\site-packages\selenium\webdriver\common\devtools\v136\fed_cm.py ===
# DO NOT EDIT THIS FILE!
#
# This file is generated from the CDP specification. If you need to make
# changes, edit the generator and regenerate all of the modules.
#
# CDP domain: FedCm (experimental)
from __future__ import annotations
from .util import event_class, T_JSON_DICT
from dataclasses import dataclass
import enum
import typing

class LoginState(enum.Enum):
    '''
    Whether this is a sign-up or sign-in action for this account, i.e.
    whether this account has ever been used to sign in to this RP before.
    '''
    SIGN_IN = "SignIn"
    SIGN_UP = "SignUp"

    def to_json(self):
        return self.value

    @classmethod
    def from_json(cls, json):
        return cls(json)


class DialogType(enum.Enum):
    '''
    The types of FedCM dialogs.
    '''
    ACCOUNT_CHOOSER = "AccountChooser"
    AUTO_REAUTHN = "AutoReauthn"
    CONFIRM_IDP_LOGIN = "ConfirmIdpLogin"
    ERROR = "Error"

    def to_json(self):
        return self.value

    @classmethod
    def from_json(cls, json):
        return cls(json)


class DialogButton(enum.Enum):
    '''
    The buttons on the FedCM dialog.
    '''
    CONFIRM_IDP_LOGIN_CONTINUE = "ConfirmIdpLoginContinue"
    ERROR_GOT_IT = "ErrorGotIt"
    ERROR_MORE_DETAILS = "ErrorMoreDetails"

    def to_json(self):
        return self.value

    @classmethod
    def from_json(cls, json):
        return cls(json)


class AccountUrlType(enum.Enum):
    '''
    The URLs that each account has
    '''
    TERMS_OF_SERVICE = "TermsOfService"
    PRIVACY_POLICY = "PrivacyPolicy"

    def to_json(self):
        return self.value

    @classmethod
    def from_json(cls, json):
        return cls(json)


@dataclass
class Account:
    '''
    Corresponds to IdentityRequestAccount
    '''
    account_id: str

    email: str

    name: str

    given_name: str

    picture_url: str

    idp_config_url: str

    idp_login_url: str

    login_state: LoginState

    #: These two are only set if the loginState is signUp
    terms_of_service_url: typing.Optional[str] = None

    privacy_policy_url: typing.Optional[str] = None

    def to_json(self):
        json = dict()
        json['accountId'] = self.account_id
        json['email'] = self.email
        json['name'] = self.name
        json['givenName'] = self.given_name
        json['pictureUrl'] = self.picture_url
        json['idpConfigUrl'] = self.idp_config_url
        json['idpLoginUrl'] = self.idp_login_url
        json['loginState'] = self.login_state.to_json()
        if self.terms_of_service_url is not None:
            json['termsOfServiceUrl'] = self.terms_of_service_url
        if self.privacy_policy_url is not None:
            json['privacyPolicyUrl'] = self.privacy_policy_url
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            account_id=str(json['accountId']),
            email=str(json['email']),
            name=str(json['name']),
            given_name=str(json['givenName']),
            picture_url=str(json['pictureUrl']),
            idp_config_url=str(json['idpConfigUrl']),
            idp_login_url=str(json['idpLoginUrl']),
            login_state=LoginState.from_json(json['loginState']),
            terms_of_service_url=str(json['termsOfServiceUrl']) if 'termsOfServiceUrl' in json else None,
            privacy_policy_url=str(json['privacyPolicyUrl']) if 'privacyPolicyUrl' in json else None,
        )


def enable(
        disable_rejection_delay: typing.Optional[bool] = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    :param disable_rejection_delay: *(Optional)* Allows callers to disable the promise rejection delay that would normally happen, if this is unimportant to what's being tested. (step 4 of https://fedidcg.github.io/FedCM/#browser-api-rp-sign-in)
    '''
    params: T_JSON_DICT = dict()
    if disable_rejection_delay is not None:
        params['disableRejectionDelay'] = disable_rejection_delay
    cmd_dict: T_JSON_DICT = {
        'method': 'FedCm.enable',
        'params': params,
    }
    json = yield cmd_dict


def disable() -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:

    cmd_dict: T_JSON_DICT = {
        'method': 'FedCm.disable',
    }
    json = yield cmd_dict


def select_account(
        dialog_id: str,
        account_index: int
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    :param dialog_id:
    :param account_index:
    '''
    params: T_JSON_DICT = dict()
    params['dialogId'] = dialog_id
    params['accountIndex'] = account_index
    cmd_dict: T_JSON_DICT = {
        'method': 'FedCm.selectAccount',
        'params': params,
    }
    json = yield cmd_dict


def click_dialog_button(
        dialog_id: str,
        dialog_button: DialogButton
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    :param dialog_id:
    :param dialog_button:
    '''
    params: T_JSON_DICT = dict()
    params['dialogId'] = dialog_id
    params['dialogButton'] = dialog_button.to_json()
    cmd_dict: T_JSON_DICT = {
        'method': 'FedCm.clickDialogButton',
        'params': params,
    }
    json = yield cmd_dict


def open_url(
        dialog_id: str,
        account_index: int,
        account_url_type: AccountUrlType
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    :param dialog_id:
    :param account_index:
    :param account_url_type:
    '''
    params: T_JSON_DICT = dict()
    params['dialogId'] = dialog_id
    params['accountIndex'] = account_index
    params['accountUrlType'] = account_url_type.to_json()
    cmd_dict: T_JSON_DICT = {
        'method': 'FedCm.openUrl',
        'params': params,
    }
    json = yield cmd_dict


def dismiss_dialog(
        dialog_id: str,
        trigger_cooldown: typing.Optional[bool] = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    :param dialog_id:
    :param trigger_cooldown: *(Optional)*
    '''
    params: T_JSON_DICT = dict()
    params['dialogId'] = dialog_id
    if trigger_cooldown is not None:
        params['triggerCooldown'] = trigger_cooldown
    cmd_dict: T_JSON_DICT = {
        'method': 'FedCm.dismissDialog',
        'params': params,
    }
    json = yield cmd_dict


def reset_cooldown() -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Resets the cooldown time, if any, to allow the next FedCM call to show
    a dialog even if one was recently dismissed by the user.
    '''
    cmd_dict: T_JSON_DICT = {
        'method': 'FedCm.resetCooldown',
    }
    json = yield cmd_dict


@event_class('FedCm.dialogShown')
@dataclass
class DialogShown:
    dialog_id: str
    dialog_type: DialogType
    accounts: typing.List[Account]
    #: These exist primarily so that the caller can verify the
    #: RP context was used appropriately.
    title: str
    subtitle: typing.Optional[str]

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> DialogShown:
        return cls(
            dialog_id=str(json['dialogId']),
            dialog_type=DialogType.from_json(json['dialogType']),
            accounts=[Account.from_json(i) for i in json['accounts']],
            title=str(json['title']),
            subtitle=str(json['subtitle']) if 'subtitle' in json else None
        )


@event_class('FedCm.dialogClosed')
@dataclass
class DialogClosed:
    '''
    Triggered when a dialog is closed, either by user action, JS abort,
    or a command below.
    '''
    dialog_id: str

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> DialogClosed:
        return cls(
            dialog_id=str(json['dialogId'])
        )

# === NexusCore/openenv\Lib\site-packages\selenium\webdriver\common\devtools\v137\fed_cm.py ===
# DO NOT EDIT THIS FILE!
#
# This file is generated from the CDP specification. If you need to make
# changes, edit the generator and regenerate all of the modules.
#
# CDP domain: FedCm (experimental)
from __future__ import annotations
from .util import event_class, T_JSON_DICT
from dataclasses import dataclass
import enum
import typing

class LoginState(enum.Enum):
    '''
    Whether this is a sign-up or sign-in action for this account, i.e.
    whether this account has ever been used to sign in to this RP before.
    '''
    SIGN_IN = "SignIn"
    SIGN_UP = "SignUp"

    def to_json(self):
        return self.value

    @classmethod
    def from_json(cls, json):
        return cls(json)


class DialogType(enum.Enum):
    '''
    The types of FedCM dialogs.
    '''
    ACCOUNT_CHOOSER = "AccountChooser"
    AUTO_REAUTHN = "AutoReauthn"
    CONFIRM_IDP_LOGIN = "ConfirmIdpLogin"
    ERROR = "Error"

    def to_json(self):
        return self.value

    @classmethod
    def from_json(cls, json):
        return cls(json)


class DialogButton(enum.Enum):
    '''
    The buttons on the FedCM dialog.
    '''
    CONFIRM_IDP_LOGIN_CONTINUE = "ConfirmIdpLoginContinue"
    ERROR_GOT_IT = "ErrorGotIt"
    ERROR_MORE_DETAILS = "ErrorMoreDetails"

    def to_json(self):
        return self.value

    @classmethod
    def from_json(cls, json):
        return cls(json)


class AccountUrlType(enum.Enum):
    '''
    The URLs that each account has
    '''
    TERMS_OF_SERVICE = "TermsOfService"
    PRIVACY_POLICY = "PrivacyPolicy"

    def to_json(self):
        return self.value

    @classmethod
    def from_json(cls, json):
        return cls(json)


@dataclass
class Account:
    '''
    Corresponds to IdentityRequestAccount
    '''
    account_id: str

    email: str

    name: str

    given_name: str

    picture_url: str

    idp_config_url: str

    idp_login_url: str

    login_state: LoginState

    #: These two are only set if the loginState is signUp
    terms_of_service_url: typing.Optional[str] = None

    privacy_policy_url: typing.Optional[str] = None

    def to_json(self):
        json = dict()
        json['accountId'] = self.account_id
        json['email'] = self.email
        json['name'] = self.name
        json['givenName'] = self.given_name
        json['pictureUrl'] = self.picture_url
        json['idpConfigUrl'] = self.idp_config_url
        json['idpLoginUrl'] = self.idp_login_url
        json['loginState'] = self.login_state.to_json()
        if self.terms_of_service_url is not None:
            json['termsOfServiceUrl'] = self.terms_of_service_url
        if self.privacy_policy_url is not None:
            json['privacyPolicyUrl'] = self.privacy_policy_url
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            account_id=str(json['accountId']),
            email=str(json['email']),
            name=str(json['name']),
            given_name=str(json['givenName']),
            picture_url=str(json['pictureUrl']),
            idp_config_url=str(json['idpConfigUrl']),
            idp_login_url=str(json['idpLoginUrl']),
            login_state=LoginState.from_json(json['loginState']),
            terms_of_service_url=str(json['termsOfServiceUrl']) if 'termsOfServiceUrl' in json else None,
            privacy_policy_url=str(json['privacyPolicyUrl']) if 'privacyPolicyUrl' in json else None,
        )


def enable(
        disable_rejection_delay: typing.Optional[bool] = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    :param disable_rejection_delay: *(Optional)* Allows callers to disable the promise rejection delay that would normally happen, if this is unimportant to what's being tested. (step 4 of https://fedidcg.github.io/FedCM/#browser-api-rp-sign-in)
    '''
    params: T_JSON_DICT = dict()
    if disable_rejection_delay is not None:
        params['disableRejectionDelay'] = disable_rejection_delay
    cmd_dict: T_JSON_DICT = {
        'method': 'FedCm.enable',
        'params': params,
    }
    json = yield cmd_dict


def disable() -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:

    cmd_dict: T_JSON_DICT = {
        'method': 'FedCm.disable',
    }
    json = yield cmd_dict


def select_account(
        dialog_id: str,
        account_index: int
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    :param dialog_id:
    :param account_index:
    '''
    params: T_JSON_DICT = dict()
    params['dialogId'] = dialog_id
    params['accountIndex'] = account_index
    cmd_dict: T_JSON_DICT = {
        'method': 'FedCm.selectAccount',
        'params': params,
    }
    json = yield cmd_dict


def click_dialog_button(
        dialog_id: str,
        dialog_button: DialogButton
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    :param dialog_id:
    :param dialog_button:
    '''
    params: T_JSON_DICT = dict()
    params['dialogId'] = dialog_id
    params['dialogButton'] = dialog_button.to_json()
    cmd_dict: T_JSON_DICT = {
        'method': 'FedCm.clickDialogButton',
        'params': params,
    }
    json = yield cmd_dict


def open_url(
        dialog_id: str,
        account_index: int,
        account_url_type: AccountUrlType
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    :param dialog_id:
    :param account_index:
    :param account_url_type:
    '''
    params: T_JSON_DICT = dict()
    params['dialogId'] = dialog_id
    params['accountIndex'] = account_index
    params['accountUrlType'] = account_url_type.to_json()
    cmd_dict: T_JSON_DICT = {
        'method': 'FedCm.openUrl',
        'params': params,
    }
    json = yield cmd_dict


def dismiss_dialog(
        dialog_id: str,
        trigger_cooldown: typing.Optional[bool] = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    :param dialog_id:
    :param trigger_cooldown: *(Optional)*
    '''
    params: T_JSON_DICT = dict()
    params['dialogId'] = dialog_id
    if trigger_cooldown is not None:
        params['triggerCooldown'] = trigger_cooldown
    cmd_dict: T_JSON_DICT = {
        'method': 'FedCm.dismissDialog',
        'params': params,
    }
    json = yield cmd_dict


def reset_cooldown() -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Resets the cooldown time, if any, to allow the next FedCM call to show
    a dialog even if one was recently dismissed by the user.
    '''
    cmd_dict: T_JSON_DICT = {
        'method': 'FedCm.resetCooldown',
    }
    json = yield cmd_dict


@event_class('FedCm.dialogShown')
@dataclass
class DialogShown:
    dialog_id: str
    dialog_type: DialogType
    accounts: typing.List[Account]
    #: These exist primarily so that the caller can verify the
    #: RP context was used appropriately.
    title: str
    subtitle: typing.Optional[str]

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> DialogShown:
        return cls(
            dialog_id=str(json['dialogId']),
            dialog_type=DialogType.from_json(json['dialogType']),
            accounts=[Account.from_json(i) for i in json['accounts']],
            title=str(json['title']),
            subtitle=str(json['subtitle']) if 'subtitle' in json else None
        )


@event_class('FedCm.dialogClosed')
@dataclass
class DialogClosed:
    '''
    Triggered when a dialog is closed, either by user action, JS abort,
    or a command below.
    '''
    dialog_id: str

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> DialogClosed:
        return cls(
            dialog_id=str(json['dialogId'])
        )

# === NexusCore/openenv\Lib\site-packages\trio\_tests\test_timeouts.py ===
from __future__ import annotations

import time
from typing import TYPE_CHECKING, Protocol, TypeVar

import outcome
import pytest

import trio

from .. import _core
from .._core._tests.tutil import slow
from .._timeouts import (
    TooSlowError,
    fail_after,
    fail_at,
    move_on_after,
    move_on_at,
    sleep,
    sleep_forever,
    sleep_until,
)
from ..testing import assert_checkpoints

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

T = TypeVar("T")


async def check_takes_about(f: Callable[[], Awaitable[T]], expected_dur: float) -> T:
    start = time.perf_counter()
    result = await outcome.acapture(f)
    dur = time.perf_counter() - start
    print(dur / expected_dur)
    # 1.5 is an arbitrary fudge factor because there's always some delay
    # between when we become eligible to wake up and when we actually do. We
    # used to sleep for 0.05, and regularly observed overruns of 1.6x on
    # Appveyor, and then started seeing overruns of 2.3x on Travis's macOS, so
    # now we bumped up the sleep to 1 second, marked the tests as slow, and
    # hopefully now the proportional error will be less huge.
    #
    # We also also for durations that are a hair shorter than expected. For
    # example, here's a run on Windows where a 1.0 second sleep was measured
    # to take 0.9999999999999858 seconds:
    #   https://ci.appveyor.com/project/njsmith/trio/build/1.0.768/job/3lbdyxl63q3h9s21
    # I believe that what happened here is that Windows's low clock resolution
    # meant that our calls to time.monotonic() returned exactly the same
    # values as the calls inside the actual run loop, but the two subtractions
    # returned slightly different values because the run loop's clock adds a
    # random floating point offset to both times, which should cancel out, but
    # lol floating point we got slightly different rounding errors. (That
    # value above is exactly 128 ULPs below 1.0, which would make sense if it
    # started as a 1 ULP error at a different dynamic range.)
    assert (1 - 1e-8) <= (dur / expected_dur) < 1.5

    return result.unwrap()


# How long to (attempt to) sleep for when testing. Smaller numbers make the
# test suite go faster.
TARGET = 1.0


@slow
async def test_sleep() -> None:
    async def sleep_1() -> None:
        await sleep_until(_core.current_time() + TARGET)

    await check_takes_about(sleep_1, TARGET)

    async def sleep_2() -> None:
        await sleep(TARGET)

    await check_takes_about(sleep_2, TARGET)

    with assert_checkpoints():
        await sleep(0)
    # This also serves as a test of the trivial move_on_at
    with move_on_at(_core.current_time()):
        with pytest.raises(_core.Cancelled):
            await sleep(0)


@slow
async def test_move_on_after() -> None:
    async def sleep_3() -> None:
        with move_on_after(TARGET):
            await sleep(100)

    await check_takes_about(sleep_3, TARGET)


async def test_cannot_wake_sleep_forever() -> None:
    # Test an error occurs if you manually wake sleep_forever().
    task = trio.lowlevel.current_task()

    async def wake_task() -> None:
        await trio.lowlevel.checkpoint()
        trio.lowlevel.reschedule(task, outcome.Value(None))

    async with trio.open_nursery() as nursery:
        nursery.start_soon(wake_task)
        with pytest.raises(RuntimeError):
            await trio.sleep_forever()


class TimeoutScope(Protocol):
    def __call__(self, seconds: float, *, shield: bool) -> trio.CancelScope: ...


@pytest.mark.parametrize("scope", [move_on_after, fail_after])
async def test_context_shields_from_outer(scope: TimeoutScope) -> None:
    with _core.CancelScope() as outer, scope(TARGET, shield=True) as inner:
        outer.cancel()
        try:
            await trio.lowlevel.checkpoint()
        except trio.Cancelled:  # pragma: no cover
            pytest.fail("shield didn't work")
        inner.shield = False
        with pytest.raises(trio.Cancelled):
            await trio.lowlevel.checkpoint()


@slow
async def test_move_on_after_moves_on_even_if_shielded() -> None:
    async def task() -> None:
        with _core.CancelScope() as outer, move_on_after(TARGET, shield=True):
            outer.cancel()
            # The outer scope is cancelled, but this task is protected by the
            # shield, so it manages to get to sleep until deadline is met
            await sleep_forever()

    await check_takes_about(task, TARGET)


@slow
async def test_fail_after_fails_even_if_shielded() -> None:
    async def task() -> None:
        # fmt: off
        # Remove after 3.9 unsupported, black formats in a way that breaks if
        # you do `-X oldparser`
        with pytest.raises(TooSlowError), _core.CancelScope() as outer, fail_after(
            TARGET,
            shield=True,
        ):
            # fmt: on
            outer.cancel()
            # The outer scope is cancelled, but this task is protected by the
            # shield, so it manages to get to sleep until deadline is met
            await sleep_forever()

    await check_takes_about(task, TARGET)


@slow
async def test_fail() -> None:
    async def sleep_4() -> None:
        with fail_at(_core.current_time() + TARGET):
            await sleep(100)

    with pytest.raises(TooSlowError):
        await check_takes_about(sleep_4, TARGET)

    with fail_at(_core.current_time() + 100):
        await sleep(0)

    async def sleep_5() -> None:
        with fail_after(TARGET):
            await sleep(100)

    with pytest.raises(TooSlowError):
        await check_takes_about(sleep_5, TARGET)

    with fail_after(100):
        await sleep(0)


async def test_timeouts_raise_value_error() -> None:
    # deadlines are allowed to be negative, but not delays.
    # neither delays nor deadlines are allowed to be NaN

    nan = float("nan")

    for fun, val in (
        (sleep, -1),
        (sleep, nan),
        (sleep_until, nan),
    ):
        with pytest.raises(
            ValueError,
            match=r"^(deadline|`seconds`) must (not )*be (non-negative|NaN)$",
        ):
            await fun(val)

    for cm, val in (
        (fail_after, -1),
        (fail_after, nan),
        (fail_at, nan),
        (move_on_after, -1),
        (move_on_after, nan),
        (move_on_at, nan),
    ):
        with pytest.raises(
            ValueError,
            match=r"^(deadline|`seconds`) must (not )*be (non-negative|NaN)$",
        ):
            with cm(val):
                pass  # pragma: no cover


async def test_timeout_deadline_on_entry(mock_clock: _core.MockClock) -> None:
    rcs = move_on_after(5)
    assert rcs.relative_deadline == 5

    mock_clock.jump(3)
    start = _core.current_time()
    with rcs as cs:
        assert cs.is_relative is None

        # This would previously be start+2
        assert cs.deadline == start + 5
        assert cs.relative_deadline == 5

        cs.deadline = start + 3
        assert cs.deadline == start + 3
        assert cs.relative_deadline == 3

        cs.relative_deadline = 4
        assert cs.deadline == start + 4
        assert cs.relative_deadline == 4

    rcs = move_on_after(5)
    assert rcs.shield is False
    rcs.shield = True
    assert rcs.shield is True

    mock_clock.jump(3)
    start = _core.current_time()
    with rcs as cs:
        assert cs.deadline == start + 5

        assert rcs is cs


async def test_invalid_access_unentered(mock_clock: _core.MockClock) -> None:
    cs = move_on_after(5)
    mock_clock.jump(3)
    start = _core.current_time()

    match_str = "^unentered relative cancel scope does not have an absolute deadline"
    with pytest.warns(DeprecationWarning, match=match_str):
        assert cs.deadline == start + 5
    mock_clock.jump(1)
    # this is hella sketchy, but they *have* been warned
    with pytest.warns(DeprecationWarning, match=match_str):
        assert cs.deadline == start + 6

    with pytest.warns(DeprecationWarning, match=match_str):
        cs.deadline = 7
    # now transformed into absolute
    assert cs.deadline == 7
    assert not cs.is_relative

    cs = move_on_at(5)

    match_str = (
        "^unentered non-relative cancel scope does not have a relative deadline$"
    )
    with pytest.raises(RuntimeError, match=match_str):
        assert cs.relative_deadline
    with pytest.raises(RuntimeError, match=match_str):
        cs.relative_deadline = 7


@pytest.mark.xfail(reason="not implemented")
async def test_fail_access_before_entering() -> None:  # pragma: no cover
    my_fail_at = fail_at(5)
    assert my_fail_at.deadline  # type: ignore[attr-defined]
    my_fail_after = fail_after(5)
    assert my_fail_after.relative_deadline  # type: ignore[attr-defined]

# === NexusCore/myenv\Lib\site-packages\pip\_internal\commands\configuration.py ===
import logging
import os
import subprocess
from optparse import Values
from typing import Any, List, Optional

from pip._internal.cli.base_command import Command
from pip._internal.cli.status_codes import ERROR, SUCCESS
from pip._internal.configuration import (
    Configuration,
    Kind,
    get_configuration_files,
    kinds,
)
from pip._internal.exceptions import PipError
from pip._internal.utils.logging import indent_log
from pip._internal.utils.misc import get_prog, write_output

logger = logging.getLogger(__name__)


class ConfigurationCommand(Command):
    """
    Manage local and global configuration.

    Subcommands:

    - list: List the active configuration (or from the file specified)
    - edit: Edit the configuration file in an editor
    - get: Get the value associated with command.option
    - set: Set the command.option=value
    - unset: Unset the value associated with command.option
    - debug: List the configuration files and values defined under them

    Configuration keys should be dot separated command and option name,
    with the special prefix "global" affecting any command. For example,
    "pip config set global.index-url https://example.org/" would configure
    the index url for all commands, but "pip config set download.timeout 10"
    would configure a 10 second timeout only for "pip download" commands.

    If none of --user, --global and --site are passed, a virtual
    environment configuration file is used if one is active and the file
    exists. Otherwise, all modifications happen to the user file by
    default.
    """

    ignore_require_venv = True
    usage = """
        %prog [<file-option>] list
        %prog [<file-option>] [--editor <editor-path>] edit

        %prog [<file-option>] get command.option
        %prog [<file-option>] set command.option value
        %prog [<file-option>] unset command.option
        %prog [<file-option>] debug
    """

    def add_options(self) -> None:
        self.cmd_opts.add_option(
            "--editor",
            dest="editor",
            action="store",
            default=None,
            help=(
                "Editor to use to edit the file. Uses VISUAL or EDITOR "
                "environment variables if not provided."
            ),
        )

        self.cmd_opts.add_option(
            "--global",
            dest="global_file",
            action="store_true",
            default=False,
            help="Use the system-wide configuration file only",
        )

        self.cmd_opts.add_option(
            "--user",
            dest="user_file",
            action="store_true",
            default=False,
            help="Use the user configuration file only",
        )

        self.cmd_opts.add_option(
            "--site",
            dest="site_file",
            action="store_true",
            default=False,
            help="Use the current environment configuration file only",
        )

        self.parser.insert_option_group(0, self.cmd_opts)

    def run(self, options: Values, args: List[str]) -> int:
        handlers = {
            "list": self.list_values,
            "edit": self.open_in_editor,
            "get": self.get_name,
            "set": self.set_name_value,
            "unset": self.unset_name,
            "debug": self.list_config_values,
        }

        # Determine action
        if not args or args[0] not in handlers:
            logger.error(
                "Need an action (%s) to perform.",
                ", ".join(sorted(handlers)),
            )
            return ERROR

        action = args[0]

        # Determine which configuration files are to be loaded
        #    Depends on whether the command is modifying.
        try:
            load_only = self._determine_file(
                options, need_value=(action in ["get", "set", "unset", "edit"])
            )
        except PipError as e:
            logger.error(e.args[0])
            return ERROR

        # Load a new configuration
        self.configuration = Configuration(
            isolated=options.isolated_mode, load_only=load_only
        )
        self.configuration.load()

        # Error handling happens here, not in the action-handlers.
        try:
            handlers[action](options, args[1:])
        except PipError as e:
            logger.error(e.args[0])
            return ERROR

        return SUCCESS

    def _determine_file(self, options: Values, need_value: bool) -> Optional[Kind]:
        file_options = [
            key
            for key, value in (
                (kinds.USER, options.user_file),
                (kinds.GLOBAL, options.global_file),
                (kinds.SITE, options.site_file),
            )
            if value
        ]

        if not file_options:
            if not need_value:
                return None
            # Default to user, unless there's a site file.
            elif any(
                os.path.exists(site_config_file)
                for site_config_file in get_configuration_files()[kinds.SITE]
            ):
                return kinds.SITE
            else:
                return kinds.USER
        elif len(file_options) == 1:
            return file_options[0]

        raise PipError(
            "Need exactly one file to operate upon "
            "(--user, --site, --global) to perform."
        )

    def list_values(self, options: Values, args: List[str]) -> None:
        self._get_n_args(args, "list", n=0)

        for key, value in sorted(self.configuration.items()):
            write_output("%s=%r", key, value)

    def get_name(self, options: Values, args: List[str]) -> None:
        key = self._get_n_args(args, "get [name]", n=1)
        value = self.configuration.get_value(key)

        write_output("%s", value)

    def set_name_value(self, options: Values, args: List[str]) -> None:
        key, value = self._get_n_args(args, "set [name] [value]", n=2)
        self.configuration.set_value(key, value)

        self._save_configuration()

    def unset_name(self, options: Values, args: List[str]) -> None:
        key = self._get_n_args(args, "unset [name]", n=1)
        self.configuration.unset_value(key)

        self._save_configuration()

    def list_config_values(self, options: Values, args: List[str]) -> None:
        """List config key-value pairs across different config files"""
        self._get_n_args(args, "debug", n=0)

        self.print_env_var_values()
        # Iterate over config files and print if they exist, and the
        # key-value pairs present in them if they do
        for variant, files in sorted(self.configuration.iter_config_files()):
            write_output("%s:", variant)
            for fname in files:
                with indent_log():
                    file_exists = os.path.exists(fname)
                    write_output("%s, exists: %r", fname, file_exists)
                    if file_exists:
                        self.print_config_file_values(variant)

    def print_config_file_values(self, variant: Kind) -> None:
        """Get key-value pairs from the file of a variant"""
        for name, value in self.configuration.get_values_in_config(variant).items():
            with indent_log():
                write_output("%s: %s", name, value)

    def print_env_var_values(self) -> None:
        """Get key-values pairs present as environment variables"""
        write_output("%s:", "env_var")
        with indent_log():
            for key, value in sorted(self.configuration.get_environ_vars()):
                env_var = f"PIP_{key.upper()}"
                write_output("%s=%r", env_var, value)

    def open_in_editor(self, options: Values, args: List[str]) -> None:
        editor = self._determine_editor(options)

        fname = self.configuration.get_file_to_edit()
        if fname is None:
            raise PipError("Could not determine appropriate file.")
        elif '"' in fname:
            # This shouldn't happen, unless we see a username like that.
            # If that happens, we'd appreciate a pull request fixing this.
            raise PipError(
                f'Can not open an editor for a file name containing "\n{fname}'
            )

        try:
            subprocess.check_call(f'{editor} "{fname}"', shell=True)
        except FileNotFoundError as e:
            if not e.filename:
                e.filename = editor
            raise
        except subprocess.CalledProcessError as e:
            raise PipError(f"Editor Subprocess exited with exit code {e.returncode}")

    def _get_n_args(self, args: List[str], example: str, n: int) -> Any:
        """Helper to make sure the command got the right number of arguments"""
        if len(args) != n:
            msg = (
                f"Got unexpected number of arguments, expected {n}. "
                f'(example: "{get_prog()} config {example}")'
            )
            raise PipError(msg)

        if n == 1:
            return args[0]
        else:
            return args

    def _save_configuration(self) -> None:
        # We successfully ran a modifying command. Need to save the
        # configuration.
        try:
            self.configuration.save()
        except Exception:
            logger.exception(
                "Unable to save configuration. Please report this as a bug."
            )
            raise PipError("Internal Error.")

    def _determine_editor(self, options: Values) -> str:
        if options.editor is not None:
            return options.editor
        elif "VISUAL" in os.environ:
            return os.environ["VISUAL"]
        elif "EDITOR" in os.environ:
            return os.environ["EDITOR"]
        else:
            raise PipError("Could not determine editor to use.")

# === NexusCore/openenv\Lib\site-packages\pip\_internal\commands\configuration.py ===
import logging
import os
import subprocess
from optparse import Values
from typing import Any, List, Optional

from pip._internal.cli.base_command import Command
from pip._internal.cli.status_codes import ERROR, SUCCESS
from pip._internal.configuration import (
    Configuration,
    Kind,
    get_configuration_files,
    kinds,
)
from pip._internal.exceptions import PipError
from pip._internal.utils.logging import indent_log
from pip._internal.utils.misc import get_prog, write_output

logger = logging.getLogger(__name__)


class ConfigurationCommand(Command):
    """
    Manage local and global configuration.

    Subcommands:

    - list: List the active configuration (or from the file specified)
    - edit: Edit the configuration file in an editor
    - get: Get the value associated with command.option
    - set: Set the command.option=value
    - unset: Unset the value associated with command.option
    - debug: List the configuration files and values defined under them

    Configuration keys should be dot separated command and option name,
    with the special prefix "global" affecting any command. For example,
    "pip config set global.index-url https://example.org/" would configure
    the index url for all commands, but "pip config set download.timeout 10"
    would configure a 10 second timeout only for "pip download" commands.

    If none of --user, --global and --site are passed, a virtual
    environment configuration file is used if one is active and the file
    exists. Otherwise, all modifications happen to the user file by
    default.
    """

    ignore_require_venv = True
    usage = """
        %prog [<file-option>] list
        %prog [<file-option>] [--editor <editor-path>] edit

        %prog [<file-option>] get command.option
        %prog [<file-option>] set command.option value
        %prog [<file-option>] unset command.option
        %prog [<file-option>] debug
    """

    def add_options(self) -> None:
        self.cmd_opts.add_option(
            "--editor",
            dest="editor",
            action="store",
            default=None,
            help=(
                "Editor to use to edit the file. Uses VISUAL or EDITOR "
                "environment variables if not provided."
            ),
        )

        self.cmd_opts.add_option(
            "--global",
            dest="global_file",
            action="store_true",
            default=False,
            help="Use the system-wide configuration file only",
        )

        self.cmd_opts.add_option(
            "--user",
            dest="user_file",
            action="store_true",
            default=False,
            help="Use the user configuration file only",
        )

        self.cmd_opts.add_option(
            "--site",
            dest="site_file",
            action="store_true",
            default=False,
            help="Use the current environment configuration file only",
        )

        self.parser.insert_option_group(0, self.cmd_opts)

    def run(self, options: Values, args: List[str]) -> int:
        handlers = {
            "list": self.list_values,
            "edit": self.open_in_editor,
            "get": self.get_name,
            "set": self.set_name_value,
            "unset": self.unset_name,
            "debug": self.list_config_values,
        }

        # Determine action
        if not args or args[0] not in handlers:
            logger.error(
                "Need an action (%s) to perform.",
                ", ".join(sorted(handlers)),
            )
            return ERROR

        action = args[0]

        # Determine which configuration files are to be loaded
        #    Depends on whether the command is modifying.
        try:
            load_only = self._determine_file(
                options, need_value=(action in ["get", "set", "unset", "edit"])
            )
        except PipError as e:
            logger.error(e.args[0])
            return ERROR

        # Load a new configuration
        self.configuration = Configuration(
            isolated=options.isolated_mode, load_only=load_only
        )
        self.configuration.load()

        # Error handling happens here, not in the action-handlers.
        try:
            handlers[action](options, args[1:])
        except PipError as e:
            logger.error(e.args[0])
            return ERROR

        return SUCCESS

    def _determine_file(self, options: Values, need_value: bool) -> Optional[Kind]:
        file_options = [
            key
            for key, value in (
                (kinds.USER, options.user_file),
                (kinds.GLOBAL, options.global_file),
                (kinds.SITE, options.site_file),
            )
            if value
        ]

        if not file_options:
            if not need_value:
                return None
            # Default to user, unless there's a site file.
            elif any(
                os.path.exists(site_config_file)
                for site_config_file in get_configuration_files()[kinds.SITE]
            ):
                return kinds.SITE
            else:
                return kinds.USER
        elif len(file_options) == 1:
            return file_options[0]

        raise PipError(
            "Need exactly one file to operate upon "
            "(--user, --site, --global) to perform."
        )

    def list_values(self, options: Values, args: List[str]) -> None:
        self._get_n_args(args, "list", n=0)

        for key, value in sorted(self.configuration.items()):
            write_output("%s=%r", key, value)

    def get_name(self, options: Values, args: List[str]) -> None:
        key = self._get_n_args(args, "get [name]", n=1)
        value = self.configuration.get_value(key)

        write_output("%s", value)

    def set_name_value(self, options: Values, args: List[str]) -> None:
        key, value = self._get_n_args(args, "set [name] [value]", n=2)
        self.configuration.set_value(key, value)

        self._save_configuration()

    def unset_name(self, options: Values, args: List[str]) -> None:
        key = self._get_n_args(args, "unset [name]", n=1)
        self.configuration.unset_value(key)

        self._save_configuration()

    def list_config_values(self, options: Values, args: List[str]) -> None:
        """List config key-value pairs across different config files"""
        self._get_n_args(args, "debug", n=0)

        self.print_env_var_values()
        # Iterate over config files and print if they exist, and the
        # key-value pairs present in them if they do
        for variant, files in sorted(self.configuration.iter_config_files()):
            write_output("%s:", variant)
            for fname in files:
                with indent_log():
                    file_exists = os.path.exists(fname)
                    write_output("%s, exists: %r", fname, file_exists)
                    if file_exists:
                        self.print_config_file_values(variant)

    def print_config_file_values(self, variant: Kind) -> None:
        """Get key-value pairs from the file of a variant"""
        for name, value in self.configuration.get_values_in_config(variant).items():
            with indent_log():
                write_output("%s: %s", name, value)

    def print_env_var_values(self) -> None:
        """Get key-values pairs present as environment variables"""
        write_output("%s:", "env_var")
        with indent_log():
            for key, value in sorted(self.configuration.get_environ_vars()):
                env_var = f"PIP_{key.upper()}"
                write_output("%s=%r", env_var, value)

    def open_in_editor(self, options: Values, args: List[str]) -> None:
        editor = self._determine_editor(options)

        fname = self.configuration.get_file_to_edit()
        if fname is None:
            raise PipError("Could not determine appropriate file.")
        elif '"' in fname:
            # This shouldn't happen, unless we see a username like that.
            # If that happens, we'd appreciate a pull request fixing this.
            raise PipError(
                f'Can not open an editor for a file name containing "\n{fname}'
            )

        try:
            subprocess.check_call(f'{editor} "{fname}"', shell=True)
        except FileNotFoundError as e:
            if not e.filename:
                e.filename = editor
            raise
        except subprocess.CalledProcessError as e:
            raise PipError(f"Editor Subprocess exited with exit code {e.returncode}")

    def _get_n_args(self, args: List[str], example: str, n: int) -> Any:
        """Helper to make sure the command got the right number of arguments"""
        if len(args) != n:
            msg = (
                f"Got unexpected number of arguments, expected {n}. "
                f'(example: "{get_prog()} config {example}")'
            )
            raise PipError(msg)

        if n == 1:
            return args[0]
        else:
            return args

    def _save_configuration(self) -> None:
        # We successfully ran a modifying command. Need to save the
        # configuration.
        try:
            self.configuration.save()
        except Exception:
            logger.exception(
                "Unable to save configuration. Please report this as a bug."
            )
            raise PipError("Internal Error.")

    def _determine_editor(self, options: Values) -> str:
        if options.editor is not None:
            return options.editor
        elif "VISUAL" in os.environ:
            return os.environ["VISUAL"]
        elif "EDITOR" in os.environ:
            return os.environ["EDITOR"]
        else:
            raise PipError("Could not determine editor to use.")

# === NexusCore/openenv\Lib\site-packages\litellm\llms\sagemaker\completion\transformation.py ===
"""
Translate from OpenAI's `/v1/chat/completions` to Sagemaker's `/invoke`

In the Huggingface TGI format. 
"""

import json
import time
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Union

from httpx._models import Headers, Response

import litellm
from litellm.litellm_core_utils.asyncify import asyncify
from litellm.litellm_core_utils.prompt_templates.factory import (
    custom_prompt,
    prompt_factory,
)
from litellm.llms.base_llm.chat.transformation import BaseConfig, BaseLLMException
from litellm.types.llms.openai import AllMessageValues
from litellm.types.utils import ModelResponse, Usage
from litellm.utils import token_counter

from ..common_utils import SagemakerError

if TYPE_CHECKING:
    from litellm.litellm_core_utils.litellm_logging import Logging as _LiteLLMLoggingObj

    LiteLLMLoggingObj = _LiteLLMLoggingObj
else:
    LiteLLMLoggingObj = Any


class SagemakerConfig(BaseConfig):
    """
    Reference: https://d-uuwbxj1u4cnu.studio.us-west-2.sagemaker.aws/jupyter/default/lab/workspaces/auto-q/tree/DemoNotebooks/meta-textgeneration-llama-2-7b-SDK_1.ipynb
    """

    max_new_tokens: Optional[int] = None
    max_completion_tokens: Optional[int] = None
    top_p: Optional[float] = None
    temperature: Optional[float] = None
    return_full_text: Optional[bool] = None

    def __init__(
        self,
        max_new_tokens: Optional[int] = None,
        max_completion_tokens: Optional[int] = None,
        top_p: Optional[float] = None,
        temperature: Optional[float] = None,
        return_full_text: Optional[bool] = None,
    ) -> None:
        locals_ = locals().copy()
        for key, value in locals_.items():
            if key != "self" and value is not None:
                setattr(self.__class__, key, value)

    @classmethod
    def get_config(cls):
        return super().get_config()

    def get_error_class(
        self, error_message: str, status_code: int, headers: Union[dict, Headers]
    ) -> BaseLLMException:
        return SagemakerError(
            message=error_message, status_code=status_code, headers=headers
        )

    def get_supported_openai_params(self, model: str) -> List:
        return ["stream", "temperature", "max_tokens", "max_completion_tokens", "top_p", "stop", "n"]

    def map_openai_params(
        self,
        non_default_params: dict,
        optional_params: dict,
        model: str,
        drop_params: bool,
    ) -> dict:
        for param, value in non_default_params.items():
            if param == "temperature":
                if value == 0.0 or value == 0:
                    # hugging face exception raised when temp==0
                    # Failed: Error occurred: HuggingfaceException - Input validation error: `temperature` must be strictly positive
                    if not non_default_params.get(
                        "aws_sagemaker_allow_zero_temp", False
                    ):
                        value = 0.01

                optional_params["temperature"] = value
            if param == "top_p":
                optional_params["top_p"] = value
            if param == "n":
                optional_params["best_of"] = value
                optional_params[
                    "do_sample"
                ] = True  # Need to sample if you want best of for hf inference endpoints
            if param == "stream":
                optional_params["stream"] = value
            if param == "stop":
                optional_params["stop"] = value
            if param == "max_tokens":
                # HF TGI raises the following exception when max_new_tokens==0
                # Failed: Error occurred: HuggingfaceException - Input validation error: `max_new_tokens` must be strictly positive
                if value == 0:
                    value = 1
                optional_params["max_new_tokens"] = value
            if param == "max_completion_tokens":
                optional_params["max_new_tokens"] = value
        non_default_params.pop("aws_sagemaker_allow_zero_temp", None)
        return optional_params

    def _transform_prompt(
        self,
        model: str,
        messages: List,
        custom_prompt_dict: dict,
        hf_model_name: Optional[str],
    ) -> str:
        if model in custom_prompt_dict:
            # check if the model has a registered custom prompt
            model_prompt_details = custom_prompt_dict[model]
            prompt = custom_prompt(
                role_dict=model_prompt_details.get("roles", None),
                initial_prompt_value=model_prompt_details.get(
                    "initial_prompt_value", ""
                ),
                final_prompt_value=model_prompt_details.get("final_prompt_value", ""),
                messages=messages,
            )
        elif hf_model_name in custom_prompt_dict:
            # check if the base huggingface model has a registered custom prompt
            model_prompt_details = custom_prompt_dict[hf_model_name]
            prompt = custom_prompt(
                role_dict=model_prompt_details.get("roles", None),
                initial_prompt_value=model_prompt_details.get(
                    "initial_prompt_value", ""
                ),
                final_prompt_value=model_prompt_details.get("final_prompt_value", ""),
                messages=messages,
            )
        else:
            if hf_model_name is None:
                if "llama-2" in model.lower():  # llama-2 model
                    if "chat" in model.lower():  # apply llama2 chat template
                        hf_model_name = "meta-llama/Llama-2-7b-chat-hf"
                    else:  # apply regular llama2 template
                        hf_model_name = "meta-llama/Llama-2-7b"
            hf_model_name = (
                hf_model_name or model
            )  # pass in hf model name for pulling it's prompt template - (e.g. `hf_model_name="meta-llama/Llama-2-7b-chat-hf` applies the llama2 chat template to the prompt)
            prompt: str = prompt_factory(model=hf_model_name, messages=messages)  # type: ignore

        return prompt

    def transform_request(
        self,
        model: str,
        messages: List[AllMessageValues],
        optional_params: dict,
        litellm_params: dict,
        headers: dict,
    ) -> dict:
        inference_params = optional_params.copy()
        stream = inference_params.pop("stream", False)
        data: Dict = {"parameters": inference_params}
        if stream is True:
            data["stream"] = True

        custom_prompt_dict = (
            litellm_params.get("custom_prompt_dict", None) or litellm.custom_prompt_dict
        )

        hf_model_name = litellm_params.get("hf_model_name", None)

        prompt = self._transform_prompt(
            model=model,
            messages=messages,
            custom_prompt_dict=custom_prompt_dict,
            hf_model_name=hf_model_name,
        )
        data["inputs"] = prompt

        return data

    async def async_transform_request(
        self,
        model: str,
        messages: List[AllMessageValues],
        optional_params: dict,
        litellm_params: dict,
        headers: dict,
    ) -> dict:
        return await asyncify(self.transform_request)(
            model, messages, optional_params, litellm_params, headers
        )

    def transform_response(
        self,
        model: str,
        raw_response: Response,
        model_response: ModelResponse,
        logging_obj: LiteLLMLoggingObj,
        request_data: dict,
        messages: List[AllMessageValues],
        optional_params: dict,
        litellm_params: dict,
        encoding: str,
        api_key: Optional[str] = None,
        json_mode: Optional[bool] = None,
    ) -> ModelResponse:
        completion_response = raw_response.json()
        ## LOGGING
        logging_obj.post_call(
            input=messages,
            api_key="",
            original_response=completion_response,
            additional_args={"complete_input_dict": request_data},
        )

        prompt = request_data["inputs"]

        ## RESPONSE OBJECT
        try:
            if isinstance(completion_response, list):
                completion_response_choices = completion_response[0]
            else:
                completion_response_choices = completion_response
            completion_output = ""
            if "generation" in completion_response_choices:
                completion_output += completion_response_choices["generation"]
            elif "generated_text" in completion_response_choices:
                completion_output += completion_response_choices["generated_text"]

            # check if the prompt template is part of output, if so - filter it out
            if completion_output.startswith(prompt) and "<s>" in prompt:
                completion_output = completion_output.replace(prompt, "", 1)

            model_response.choices[0].message.content = completion_output  # type: ignore
        except Exception:
            raise SagemakerError(
                message=f"LiteLLM Error: Unable to parse sagemaker RAW RESPONSE {json.dumps(completion_response)}",
                status_code=500,
            )

        ## CALCULATING USAGE - baseten charges on time, not tokens - have some mapping of cost here.
        prompt_tokens = token_counter(
            text=prompt, count_response_tokens=True
        )  # doesn't apply any default token count from openai's chat template
        completion_tokens = token_counter(
            text=model_response["choices"][0]["message"].get("content", ""),
            count_response_tokens=True,
        )

        model_response.created = int(time.time())
        model_response.model = model
        usage = Usage(
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=prompt_tokens + completion_tokens,
        )
        setattr(model_response, "usage", usage)
        return model_response

    def validate_environment(
        self,
        headers: Optional[dict],
        model: str,
        messages: List[AllMessageValues],
        optional_params: dict,
        litellm_params: dict,
        api_key: Optional[str] = None,
        api_base: Optional[str] = None,
    ) -> dict:
        headers = {"Content-Type": "application/json"}

        if headers is not None:
            headers = {"Content-Type": "application/json", **headers}

        return headers

# === NexusCore/openenv\Lib\site-packages\prompt_toolkit\contrib\regular_languages\regex_parser.py ===
"""
Parser for parsing a regular expression.
Take a string representing a regular expression and return the root node of its
parse tree.

usage::

    root_node = parse_regex('(hello|world)')

Remarks:
- The regex parser processes multiline, it ignores all whitespace and supports
  multiple named groups with the same name and #-style comments.

Limitations:
- Lookahead is not supported.
"""

from __future__ import annotations

import re

__all__ = [
    "Repeat",
    "Variable",
    "Regex",
    "Lookahead",
    "tokenize_regex",
    "parse_regex",
]


class Node:
    """
    Base class for all the grammar nodes.
    (You don't initialize this one.)
    """

    def __add__(self, other_node: Node) -> NodeSequence:
        return NodeSequence([self, other_node])

    def __or__(self, other_node: Node) -> AnyNode:
        return AnyNode([self, other_node])


class AnyNode(Node):
    """
    Union operation (OR operation) between several grammars. You don't
    initialize this yourself, but it's a result of a "Grammar1 | Grammar2"
    operation.
    """

    def __init__(self, children: list[Node]) -> None:
        self.children = children

    def __or__(self, other_node: Node) -> AnyNode:
        return AnyNode(self.children + [other_node])

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.children!r})"


class NodeSequence(Node):
    """
    Concatenation operation of several grammars. You don't initialize this
    yourself, but it's a result of a "Grammar1 + Grammar2" operation.
    """

    def __init__(self, children: list[Node]) -> None:
        self.children = children

    def __add__(self, other_node: Node) -> NodeSequence:
        return NodeSequence(self.children + [other_node])

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.children!r})"


class Regex(Node):
    """
    Regular expression.
    """

    def __init__(self, regex: str) -> None:
        re.compile(regex)  # Validate

        self.regex = regex

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(/{self.regex}/)"


class Lookahead(Node):
    """
    Lookahead expression.
    """

    def __init__(self, childnode: Node, negative: bool = False) -> None:
        self.childnode = childnode
        self.negative = negative

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.childnode!r})"


class Variable(Node):
    """
    Mark a variable in the regular grammar. This will be translated into a
    named group. Each variable can have his own completer, validator, etc..

    :param childnode: The grammar which is wrapped inside this variable.
    :param varname: String.
    """

    def __init__(self, childnode: Node, varname: str = "") -> None:
        self.childnode = childnode
        self.varname = varname

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(childnode={self.childnode!r}, varname={self.varname!r})"


class Repeat(Node):
    def __init__(
        self,
        childnode: Node,
        min_repeat: int = 0,
        max_repeat: int | None = None,
        greedy: bool = True,
    ) -> None:
        self.childnode = childnode
        self.min_repeat = min_repeat
        self.max_repeat = max_repeat
        self.greedy = greedy

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(childnode={self.childnode!r})"


def tokenize_regex(input: str) -> list[str]:
    """
    Takes a string, representing a regular expression as input, and tokenizes
    it.

    :param input: string, representing a regular expression.
    :returns: List of tokens.
    """
    # Regular expression for tokenizing other regular expressions.
    p = re.compile(
        r"""^(
        \(\?P\<[a-zA-Z0-9_-]+\>  | # Start of named group.
        \(\?#[^)]*\)             | # Comment
        \(\?=                    | # Start of lookahead assertion
        \(\?!                    | # Start of negative lookahead assertion
        \(\?<=                   | # If preceded by.
        \(\?<                    | # If not preceded by.
        \(?:                     | # Start of group. (non capturing.)
        \(                       | # Start of group.
        \(?[iLmsux]              | # Flags.
        \(?P=[a-zA-Z]+\)         | # Back reference to named group
        \)                       | # End of group.
        \{[^{}]*\}               | # Repetition
        \*\? | \+\? | \?\?\      | # Non greedy repetition.
        \* | \+ | \?             | # Repetition
        \#.*\n                   | # Comment
        \\. |

        # Character group.
        \[
            ( [^\]\\]  |  \\.)*
        \]                  |

        [^(){}]             |
        .
    )""",
        re.VERBOSE,
    )

    tokens = []

    while input:
        m = p.match(input)
        if m:
            token, input = input[: m.end()], input[m.end() :]
            if not token.isspace():
                tokens.append(token)
        else:
            raise Exception("Could not tokenize input regex.")

    return tokens


def parse_regex(regex_tokens: list[str]) -> Node:
    """
    Takes a list of tokens from the tokenizer, and returns a parse tree.
    """
    # We add a closing brace because that represents the final pop of the stack.
    tokens: list[str] = [")"] + regex_tokens[::-1]

    def wrap(lst: list[Node]) -> Node:
        """Turn list into sequence when it contains several items."""
        if len(lst) == 1:
            return lst[0]
        else:
            return NodeSequence(lst)

    def _parse() -> Node:
        or_list: list[list[Node]] = []
        result: list[Node] = []

        def wrapped_result() -> Node:
            if or_list == []:
                return wrap(result)
            else:
                or_list.append(result)
                return AnyNode([wrap(i) for i in or_list])

        while tokens:
            t = tokens.pop()

            if t.startswith("(?P<"):
                variable = Variable(_parse(), varname=t[4:-1])
                result.append(variable)

            elif t in ("*", "*?"):
                greedy = t == "*"
                result[-1] = Repeat(result[-1], greedy=greedy)

            elif t in ("+", "+?"):
                greedy = t == "+"
                result[-1] = Repeat(result[-1], min_repeat=1, greedy=greedy)

            elif t in ("?", "??"):
                if result == []:
                    raise Exception("Nothing to repeat." + repr(tokens))
                else:
                    greedy = t == "?"
                    result[-1] = Repeat(
                        result[-1], min_repeat=0, max_repeat=1, greedy=greedy
                    )

            elif t == "|":
                or_list.append(result)
                result = []

            elif t in ("(", "(?:"):
                result.append(_parse())

            elif t == "(?!":
                result.append(Lookahead(_parse(), negative=True))

            elif t == "(?=":
                result.append(Lookahead(_parse(), negative=False))

            elif t == ")":
                return wrapped_result()

            elif t.startswith("#"):
                pass

            elif t.startswith("{"):
                # TODO: implement!
                raise Exception(f"{t}-style repetition not yet supported")

            elif t.startswith("(?"):
                raise Exception(f"{t!r} not supported")

            elif t.isspace():
                pass
            else:
                result.append(Regex(t))

        raise Exception("Expecting ')' token")

    result = _parse()

    if len(tokens) != 0:
        raise Exception("Unmatched parentheses.")
    else:
        return result

# === NexusCore/openenv\Lib\site-packages\pygments\lexers\dylan.py ===
"""
    pygments.lexers.dylan
    ~~~~~~~~~~~~~~~~~~~~~

    Lexers for the Dylan language.

    :copyright: Copyright 2006-2025 by the Pygments team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

import re

from pygments.lexer import Lexer, RegexLexer, bygroups, do_insertions, \
    default, line_re
from pygments.token import Comment, Operator, Keyword, Name, String, \
    Number, Punctuation, Generic, Literal, Whitespace

__all__ = ['DylanLexer', 'DylanConsoleLexer', 'DylanLidLexer']


class DylanLexer(RegexLexer):
    """
    For the Dylan language.
    """

    name = 'Dylan'
    url = 'http://www.opendylan.org/'
    aliases = ['dylan']
    filenames = ['*.dylan', '*.dyl', '*.intr']
    mimetypes = ['text/x-dylan']
    version_added = '0.7'

    flags = re.IGNORECASE

    builtins = {
        'subclass', 'abstract', 'block', 'concrete', 'constant', 'class',
        'compiler-open', 'compiler-sideways', 'domain', 'dynamic',
        'each-subclass', 'exception', 'exclude', 'function', 'generic',
        'handler', 'inherited', 'inline', 'inline-only', 'instance',
        'interface', 'import', 'keyword', 'library', 'macro', 'method',
        'module', 'open', 'primary', 'required', 'sealed', 'sideways',
        'singleton', 'slot', 'thread', 'variable', 'virtual'}

    keywords = {
        'above', 'afterwards', 'begin', 'below', 'by', 'case', 'cleanup',
        'create', 'define', 'else', 'elseif', 'end', 'export', 'finally',
        'for', 'from', 'if', 'in', 'let', 'local', 'otherwise', 'rename',
        'select', 'signal', 'then', 'to', 'unless', 'until', 'use', 'when',
        'while'}

    operators = {
        '~', '+', '-', '*', '|', '^', '=', '==', '~=', '~==', '<', '<=',
        '>', '>=', '&', '|'}

    functions = {
        'abort', 'abs', 'add', 'add!', 'add-method', 'add-new', 'add-new!',
        'all-superclasses', 'always', 'any?', 'applicable-method?', 'apply',
        'aref', 'aref-setter', 'as', 'as-lowercase', 'as-lowercase!',
        'as-uppercase', 'as-uppercase!', 'ash', 'backward-iteration-protocol',
        'break', 'ceiling', 'ceiling/', 'cerror', 'check-type', 'choose',
        'choose-by', 'complement', 'compose', 'concatenate', 'concatenate-as',
        'condition-format-arguments', 'condition-format-string', 'conjoin',
        'copy-sequence', 'curry', 'default-handler', 'dimension', 'dimensions',
        'direct-subclasses', 'direct-superclasses', 'disjoin', 'do',
        'do-handlers', 'element', 'element-setter', 'empty?', 'error', 'even?',
        'every?', 'false-or', 'fill!', 'find-key', 'find-method', 'first',
        'first-setter', 'floor', 'floor/', 'forward-iteration-protocol',
        'function-arguments', 'function-return-values',
        'function-specializers', 'gcd', 'generic-function-mandatory-keywords',
        'generic-function-methods', 'head', 'head-setter', 'identity',
        'initialize', 'instance?', 'integral?', 'intersection',
        'key-sequence', 'key-test', 'last', 'last-setter', 'lcm', 'limited',
        'list', 'logand', 'logbit?', 'logior', 'lognot', 'logxor', 'make',
        'map', 'map-as', 'map-into', 'max', 'member?', 'merge-hash-codes',
        'min', 'modulo', 'negative', 'negative?', 'next-method',
        'object-class', 'object-hash', 'odd?', 'one-of', 'pair', 'pop',
        'pop-last', 'positive?', 'push', 'push-last', 'range', 'rank',
        'rcurry', 'reduce', 'reduce1', 'remainder', 'remove', 'remove!',
        'remove-duplicates', 'remove-duplicates!', 'remove-key!',
        'remove-method', 'replace-elements!', 'replace-subsequence!',
        'restart-query', 'return-allowed?', 'return-description',
        'return-query', 'reverse', 'reverse!', 'round', 'round/',
        'row-major-index', 'second', 'second-setter', 'shallow-copy',
        'signal', 'singleton', 'size', 'size-setter', 'slot-initialized?',
        'sort', 'sort!', 'sorted-applicable-methods', 'subsequence-position',
        'subtype?', 'table-protocol', 'tail', 'tail-setter', 'third',
        'third-setter', 'truncate', 'truncate/', 'type-error-expected-type',
        'type-error-value', 'type-for-copy', 'type-union', 'union', 'values',
        'vector', 'zero?'}

    valid_name = '\\\\?[\\w!&*<>|^$%@\\-+~?/=]+'

    def get_tokens_unprocessed(self, text):
        for index, token, value in RegexLexer.get_tokens_unprocessed(self, text):
            if token is Name:
                lowercase_value = value.lower()
                if lowercase_value in self.builtins:
                    yield index, Name.Builtin, value
                    continue
                if lowercase_value in self.keywords:
                    yield index, Keyword, value
                    continue
                if lowercase_value in self.functions:
                    yield index, Name.Builtin, value
                    continue
                if lowercase_value in self.operators:
                    yield index, Operator, value
                    continue
            yield index, token, value

    tokens = {
        'root': [
            # Whitespace
            (r'\s+', Whitespace),

            # single line comment
            (r'//.*?\n', Comment.Single),

            # lid header
            (r'([a-z0-9-]+)(:)([ \t]*)(.*(?:\n[ \t].+)*)',
                bygroups(Name.Attribute, Operator, Whitespace, String)),

            default('code')  # no header match, switch to code
        ],
        'code': [
            # Whitespace
            (r'\s+', Whitespace),

            # single line comment
            (r'(//.*?)(\n)', bygroups(Comment.Single, Whitespace)),

            # multi-line comment
            (r'/\*', Comment.Multiline, 'comment'),

            # strings and characters
            (r'"', String, 'string'),
            (r"'(\\.|\\[0-7]{1,3}|\\x[a-f0-9]{1,2}|[^\\\'\n])'", String.Char),

            # binary integer
            (r'#b[01]+', Number.Bin),

            # octal integer
            (r'#o[0-7]+', Number.Oct),

            # floating point
            (r'[-+]?(\d*\.\d+(e[-+]?\d+)?|\d+(\.\d*)?e[-+]?\d+)', Number.Float),

            # decimal integer
            (r'[-+]?\d+', Number.Integer),

            # hex integer
            (r'#x[0-9a-f]+', Number.Hex),

            # Macro parameters
            (r'(\?' + valid_name + ')(:)'
             r'(token|name|variable|expression|body|case-body|\*)',
                bygroups(Name.Tag, Operator, Name.Builtin)),
            (r'(\?)(:)(token|name|variable|expression|body|case-body|\*)',
                bygroups(Name.Tag, Operator, Name.Builtin)),
            (r'\?' + valid_name, Name.Tag),

            # Punctuation
            (r'(=>|::|#\(|#\[|##|\?\?|\?=|\?|[(){}\[\],.;])', Punctuation),

            # Most operators are picked up as names and then re-flagged.
            # This one isn't valid in a name though, so we pick it up now.
            (r':=', Operator),

            # Pick up #t / #f before we match other stuff with #.
            (r'#[tf]', Literal),

            # #"foo" style keywords
            (r'#"', String.Symbol, 'keyword'),

            # #rest, #key, #all-keys, etc.
            (r'#[a-z0-9-]+', Keyword),

            # required-init-keyword: style keywords.
            (valid_name + ':', Keyword),

            # class names
            ('<' + valid_name + '>', Name.Class),

            # define variable forms.
            (r'\*' + valid_name + r'\*', Name.Variable.Global),

            # define constant forms.
            (r'\$' + valid_name, Name.Constant),

            # everything else. We re-flag some of these in the method above.
            (valid_name, Name),
        ],
        'comment': [
            (r'[^*/]+', Comment.Multiline),
            (r'/\*', Comment.Multiline, '#push'),
            (r'\*/', Comment.Multiline, '#pop'),
            (r'[*/]', Comment.Multiline)
        ],
        'keyword': [
            (r'"', String.Symbol, '#pop'),
            (r'[^\\"]+', String.Symbol),  # all other characters
        ],
        'string': [
            (r'"', String, '#pop'),
            (r'\\([\\abfnrtv"\']|x[a-f0-9]{2,4}|[0-7]{1,3})', String.Escape),
            (r'[^\\"\n]+', String),  # all other characters
            (r'\\\n', String),  # line continuation
            (r'\\', String),  # stray backslash
        ]
    }


class DylanLidLexer(RegexLexer):
    """
    For Dylan LID (Library Interchange Definition) files.
    """

    name = 'DylanLID'
    aliases = ['dylan-lid', 'lid']
    filenames = ['*.lid', '*.hdp']
    mimetypes = ['text/x-dylan-lid']
    url = 'http://www.opendylan.org/'
    version_added = '1.6'
    flags = re.IGNORECASE

    tokens = {
        'root': [
            # Whitespace
            (r'\s+', Whitespace),

            # single line comment
            (r'(//.*?)(\n)', bygroups(Comment.Single, Whitespace)),

            # lid header
            (r'(.*?)(:)([ \t]*)(.*(?:\n[ \t].+)*)',
             bygroups(Name.Attribute, Operator, Whitespace, String)),
        ]
    }


class DylanConsoleLexer(Lexer):
    """
    For Dylan interactive console output.

    This is based on a copy of the ``RubyConsoleLexer``.
    """
    name = 'Dylan session'
    aliases = ['dylan-console', 'dylan-repl']
    filenames = ['*.dylan-console']
    mimetypes = ['text/x-dylan-console']
    url = 'http://www.opendylan.org/'
    version_added = '1.6'
    _example = 'dylan-console/console.dylan-console'

    _prompt_re = re.compile(r'\?| ')

    def get_tokens_unprocessed(self, text):
        dylexer = DylanLexer(**self.options)

        curcode = ''
        insertions = []
        for match in line_re.finditer(text):
            line = match.group()
            m = self._prompt_re.match(line)
            if m is not None:
                end = m.end()
                insertions.append((len(curcode),
                                   [(0, Generic.Prompt, line[:end])]))
                curcode += line[end:]
            else:
                if curcode:
                    yield from do_insertions(insertions,
                                             dylexer.get_tokens_unprocessed(curcode))
                    curcode = ''
                    insertions = []
                yield match.start(), Generic.Output, line
        if curcode:
            yield from do_insertions(insertions,
                                     dylexer.get_tokens_unprocessed(curcode))

# === NexusCore/openenv\Lib\site-packages\pygments\lexers\_vbscript_builtins.py ===
"""
    pygments.lexers._vbscript_builtins
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    These are manually translated lists from
    http://www.indusoft.com/pdf/VBScript%20Reference.pdf.

    :copyright: Copyright 2006-2025 by the Pygments team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

KEYWORDS = [
    'ByRef',
    'ByVal',
    # dim: special rule
    'call',
    'case',
    'class',
    # const: special rule
    'do',
    'each',
    'else',
    'elseif',
    'end',
    'erase',
    'execute',
    'function',
    'exit',
    'for',
    'function',
    'GetRef',
    'global',
    'if',
    'let',
    'loop',
    'next',
    'new',
    # option: special rule
    'private',
    'public',
    'redim',
    'select',
    'set',
    'sub',
    'then',
    'wend',
    'while',
    'with',
]

BUILTIN_FUNCTIONS = [
    'Abs',
    'Array',
    'Asc',
    'Atn',
    'CBool',
    'CByte',
    'CCur',
    'CDate',
    'CDbl',
    'Chr',
    'CInt',
    'CLng',
    'Cos',
    'CreateObject',
    'CSng',
    'CStr',
    'Date',
    'DateAdd',
    'DateDiff',
    'DatePart',
    'DateSerial',
    'DateValue',
    'Day',
    'Eval',
    'Exp',
    'Filter',
    'Fix',
    'FormatCurrency',
    'FormatDateTime',
    'FormatNumber',
    'FormatPercent',
    'GetObject',
    'GetLocale',
    'Hex',
    'Hour',
    'InStr',
    'inStrRev',
    'Int',
    'IsArray',
    'IsDate',
    'IsEmpty',
    'IsNull',
    'IsNumeric',
    'IsObject',
    'Join',
    'LBound',
    'LCase',
    'Left',
    'Len',
    'LoadPicture',
    'Log',
    'LTrim',
    'Mid',
    'Minute',
    'Month',
    'MonthName',
    'MsgBox',
    'Now',
    'Oct',
    'Randomize',
    'RegExp',
    'Replace',
    'RGB',
    'Right',
    'Rnd',
    'Round',
    'RTrim',
    'ScriptEngine',
    'ScriptEngineBuildVersion',
    'ScriptEngineMajorVersion',
    'ScriptEngineMinorVersion',
    'Second',
    'SetLocale',
    'Sgn',
    'Space',
    'Split',
    'Sqr',
    'StrComp',
    'String',
    'StrReverse',
    'Tan',
    'Time',
    'Timer',
    'TimeSerial',
    'TimeValue',
    'Trim',
    'TypeName',
    'UBound',
    'UCase',
    'VarType',
    'Weekday',
    'WeekdayName',
    'Year',
]

BUILTIN_VARIABLES = [
    'Debug',
    'Dictionary',
    'Drive',
    'Drives',
    'Err',
    'File',
    'Files',
    'FileSystemObject',
    'Folder',
    'Folders',
    'Match',
    'Matches',
    'RegExp',
    'Submatches',
    'TextStream',
]

OPERATORS = [
    '+',
    '-',
    '*',
    '/',
    '\\',
    '^',
    '|',
    '<',
    '<=',
    '>',
    '>=',
    '=',
    '<>',
    '&',
    '$',
]

OPERATOR_WORDS = [
    'mod',
    'and',
    'or',
    'xor',
    'eqv',
    'imp',
    'is',
    'not',
]

BUILTIN_CONSTANTS = [
    'False',
    'True',
    'vbAbort',
    'vbAbortRetryIgnore',
    'vbApplicationModal',
    'vbArray',
    'vbBinaryCompare',
    'vbBlack',
    'vbBlue',
    'vbBoole',
    'vbByte',
    'vbCancel',
    'vbCr',
    'vbCritical',
    'vbCrLf',
    'vbCurrency',
    'vbCyan',
    'vbDataObject',
    'vbDate',
    'vbDefaultButton1',
    'vbDefaultButton2',
    'vbDefaultButton3',
    'vbDefaultButton4',
    'vbDouble',
    'vbEmpty',
    'vbError',
    'vbExclamation',
    'vbFalse',
    'vbFirstFullWeek',
    'vbFirstJan1',
    'vbFormFeed',
    'vbFriday',
    'vbGeneralDate',
    'vbGreen',
    'vbIgnore',
    'vbInformation',
    'vbInteger',
    'vbLf',
    'vbLong',
    'vbLongDate',
    'vbLongTime',
    'vbMagenta',
    'vbMonday',
    'vbMsgBoxHelpButton',
    'vbMsgBoxRight',
    'vbMsgBoxRtlReading',
    'vbMsgBoxSetForeground',
    'vbNewLine',
    'vbNo',
    'vbNull',
    'vbNullChar',
    'vbNullString',
    'vbObject',
    'vbObjectError',
    'vbOK',
    'vbOKCancel',
    'vbOKOnly',
    'vbQuestion',
    'vbRed',
    'vbRetry',
    'vbRetryCancel',
    'vbSaturday',
    'vbShortDate',
    'vbShortTime',
    'vbSingle',
    'vbString',
    'vbSunday',
    'vbSystemModal',
    'vbTab',
    'vbTextCompare',
    'vbThursday',
    'vbTrue',
    'vbTuesday',
    'vbUseDefault',
    'vbUseSystem',
    'vbUseSystem',
    'vbVariant',
    'vbVerticalTab',
    'vbWednesday',
    'vbWhite',
    'vbYellow',
    'vbYes',
    'vbYesNo',
    'vbYesNoCancel',
]

# === NexusCore/openenv\Lib\site-packages\pythonwin\pywin\framework\toolmenu.py ===
# toolmenu.py

import sys

import win32api
import win32con
import win32ui

tools = {}
idPos = 100

# The default items should no tools menu exist in the INI file.
defaultToolMenuItems = [
    ("Browser", "win32ui.GetApp().OnViewBrowse(0,0)"),
    (
        "Browse PythonPath",
        "from pywin.tools import browseProjects;browseProjects.Browse()",
    ),
    ("Edit Python Path", "from pywin.tools import regedit;regedit.EditRegistry()"),
    ("COM Makepy utility", "from win32com.client import makepy;makepy.main()"),
    (
        "COM Browser",
        "from win32com.client import combrowse;combrowse.main(modal=False)",
    ),
    (
        "Trace Collector Debugging tool",
        "from pywin.tools import TraceCollector;TraceCollector.MakeOutputWindow()",
    ),
]


def LoadToolMenuItems():
    # Load from the registry.
    items = []
    lookNo = 1
    while 1:
        menu = win32ui.GetProfileVal("Tools Menu\\%s" % lookNo, "", "")
        if menu == "":
            break
        cmd = win32ui.GetProfileVal("Tools Menu\\%s" % lookNo, "Command", "")
        items.append((menu, cmd))
        lookNo += 1

    if len(items) == 0:
        items = defaultToolMenuItems
    return items


def WriteToolMenuItems(items):
    # Items is a list of (menu, command)
    # Delete the entire registry tree.
    try:
        mainKey = win32ui.GetAppRegistryKey()
        toolKey = win32api.RegOpenKey(mainKey, "Tools Menu")
    except win32ui.error:
        toolKey = None
    if toolKey is not None:
        while 1:
            try:
                subkey = win32api.RegEnumKey(toolKey, 0)
            except win32api.error:
                break
            win32api.RegDeleteKey(toolKey, subkey)
    # Keys are now removed - write the new ones.
    # But first check if we have the defaults - and if so, don't write anything!
    if items == defaultToolMenuItems:
        return
    itemNo = 1
    for menu, cmd in items:
        win32ui.WriteProfileVal("Tools Menu\\%s" % itemNo, "", menu)
        win32ui.WriteProfileVal("Tools Menu\\%s" % itemNo, "Command", cmd)
        itemNo += 1


def SetToolsMenu(menu, menuPos=None):
    global tools
    global idPos

    # todo - check the menu does not already exist.
    # Create the new menu
    toolsMenu = win32ui.CreatePopupMenu()

    # Load from the ini file.
    items = LoadToolMenuItems()
    for menuString, cmd in items:
        tools[idPos] = (menuString, cmd, menuString)
        toolsMenu.AppendMenu(
            win32con.MF_ENABLED | win32con.MF_STRING, idPos, menuString
        )
        win32ui.GetMainFrame().HookCommand(HandleToolCommand, idPos)
        idPos += 1

    # Find the correct spot to insert the new tools menu.
    if menuPos is None:
        menuPos = menu.GetMenuItemCount() - 2
        if menuPos < 0:
            menuPos = 0

    menu.InsertMenu(
        menuPos,
        win32con.MF_BYPOSITION
        | win32con.MF_ENABLED
        | win32con.MF_STRING
        | win32con.MF_POPUP,
        toolsMenu.GetHandle(),
        "&Tools",
    )


def HandleToolCommand(cmd, code):
    import re
    import traceback

    global tools
    (menuString, pyCmd, desc) = tools[cmd]
    win32ui.SetStatusText("Executing tool %s" % desc, 1)
    pyCmd = re.sub(r"\\n", "\n", pyCmd)
    win32ui.DoWaitCursor(1)
    oldFlag = None
    try:
        oldFlag = sys.stdout.template.writeQueueing
        sys.stdout.template.writeQueueing = 0
    except (NameError, AttributeError):
        pass

    try:
        exec("%s\n" % pyCmd)
        worked = 1
    except SystemExit:
        # The program raised a SystemExit - ignore it.
        worked = 1
    except:
        print("Failed to execute command:\n%s" % pyCmd)
        traceback.print_exc()
        worked = 0
    if oldFlag is not None:
        sys.stdout.template.writeQueueing = oldFlag
    win32ui.DoWaitCursor(0)
    if worked:
        text = "Completed successfully."
    else:
        text = "Error executing %s." % desc
    win32ui.SetStatusText(text, 1)


# The property page for maintaing the items on the Tools menu.
import commctrl
from pywin.mfc import dialog

LVN_ENDLABELEDIT = commctrl.LVN_ENDLABELEDITW


class ToolMenuPropPage(dialog.PropertyPage):
    def __init__(self):
        self.bImChangingEditControls = 0  # Am I programatically changing the controls?
        dialog.PropertyPage.__init__(self, win32ui.IDD_PP_TOOLMENU)

    def OnInitDialog(self):
        self.editMenuCommand = self.GetDlgItem(win32ui.IDC_EDIT2)
        self.butNew = self.GetDlgItem(win32ui.IDC_BUTTON3)

        # Now hook the change notification messages for the edit controls.
        self.HookCommand(self.OnCommandEditControls, win32ui.IDC_EDIT1)
        self.HookCommand(self.OnCommandEditControls, win32ui.IDC_EDIT2)

        self.HookNotify(self.OnNotifyListControl, commctrl.LVN_ITEMCHANGED)
        self.HookNotify(self.OnNotifyListControlEndLabelEdit, commctrl.LVN_ENDLABELEDIT)

        # Hook the button clicks.
        self.HookCommand(self.OnButtonNew, win32ui.IDC_BUTTON3)  # New Item
        self.HookCommand(self.OnButtonDelete, win32ui.IDC_BUTTON4)  # Delete item
        self.HookCommand(self.OnButtonMove, win32ui.IDC_BUTTON1)  # Move up
        self.HookCommand(self.OnButtonMove, win32ui.IDC_BUTTON2)  # Move down

        # Setup the columns in the list control
        lc = self.GetDlgItem(win32ui.IDC_LIST1)
        rect = lc.GetWindowRect()
        cx = rect[2] - rect[0]
        colSize = cx / 2 - win32api.GetSystemMetrics(win32con.SM_CXBORDER) - 1

        item = commctrl.LVCFMT_LEFT, colSize, "Menu Text"
        lc.InsertColumn(0, item)

        item = commctrl.LVCFMT_LEFT, colSize, "Python Command"
        lc.InsertColumn(1, item)

        # Insert the existing tools menu
        itemNo = 0
        for desc, cmd in LoadToolMenuItems():
            lc.InsertItem(itemNo, desc)
            lc.SetItemText(itemNo, 1, cmd)
            itemNo += 1

        self.listControl = lc
        return dialog.PropertyPage.OnInitDialog(self)

    def OnOK(self):
        # Write the menu back to the registry.
        items = []
        itemLook = 0
        while 1:
            try:
                text = self.listControl.GetItemText(itemLook, 0)
                if not text:
                    break
                items.append((text, self.listControl.GetItemText(itemLook, 1)))
            except win32ui.error:
                # no more items!
                break
            itemLook += 1
        WriteToolMenuItems(items)
        return self._obj_.OnOK()

    def OnCommandEditControls(self, id, cmd):
        # print("OnEditControls", id, cmd)
        if cmd == win32con.EN_CHANGE and not self.bImChangingEditControls:
            itemNo = self.listControl.GetNextItem(-1, commctrl.LVNI_SELECTED)
            newText = self.editMenuCommand.GetWindowText()
            self.listControl.SetItemText(itemNo, 1, newText)

        return 0

    def OnNotifyListControlEndLabelEdit(self, id, cmd):
        newText = self.listControl.GetEditControl().GetWindowText()
        itemNo = self.listControl.GetNextItem(-1, commctrl.LVNI_SELECTED)
        self.listControl.SetItemText(itemNo, 0, newText)

    def OnNotifyListControl(self, id, cmd):
        # print(id, cmd)
        try:
            itemNo = self.listControl.GetNextItem(-1, commctrl.LVNI_SELECTED)
        except win32ui.error:  # No selection!
            return

        self.bImChangingEditControls = 1
        try:
            item = self.listControl.GetItem(itemNo, 1)
            self.editMenuCommand.SetWindowText(item[4])
        finally:
            self.bImChangingEditControls = 0

        return 0  # we have handled this!

    def OnButtonNew(self, id, cmd):
        if cmd == win32con.BN_CLICKED:
            newIndex = self.listControl.GetItemCount()
            self.listControl.InsertItem(newIndex, "Click to edit the text")
            self.listControl.EnsureVisible(newIndex, 0)

    def OnButtonMove(self, id, cmd):
        if cmd == win32con.BN_CLICKED:
            try:
                itemNo = self.listControl.GetNextItem(-1, commctrl.LVNI_SELECTED)
            except win32ui.error:
                return
            menu = self.listControl.GetItemText(itemNo, 0)
            cmd = self.listControl.GetItemText(itemNo, 1)
            if id == win32ui.IDC_BUTTON1:
                # Move up
                if itemNo > 0:
                    self.listControl.DeleteItem(itemNo)
                    # reinsert it.
                    self.listControl.InsertItem(itemNo - 1, menu)
                    self.listControl.SetItemText(itemNo - 1, 1, cmd)
            else:
                # Move down.
                if itemNo < self.listControl.GetItemCount() - 1:
                    self.listControl.DeleteItem(itemNo)
                    # reinsert it.
                    self.listControl.InsertItem(itemNo + 1, menu)
                    self.listControl.SetItemText(itemNo + 1, 1, cmd)

    def OnButtonDelete(self, id, cmd):
        if cmd == win32con.BN_CLICKED:
            try:
                itemNo = self.listControl.GetNextItem(-1, commctrl.LVNI_SELECTED)
            except win32ui.error:  # No selection!
                return
            self.listControl.DeleteItem(itemNo)