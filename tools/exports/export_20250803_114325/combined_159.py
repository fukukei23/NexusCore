
# === NexusCore/openenv\Lib\site-packages\jedi\inference\imports.py ===
"""
:mod:`jedi.inference.imports` is here to resolve import statements and return
the modules/classes/functions/whatever, which they stand for. However there's
not any actual importing done. This module is about finding modules in the
filesystem. This can be quite tricky sometimes, because Python imports are not
always that simple.

This module also supports import autocompletion, which means to complete
statements like ``from datetim`` (cursor at the end would return ``datetime``).
"""
import os
from pathlib import Path

from parso.python import tree
from parso.tree import search_ancestor

from jedi import debug
from jedi import settings
from jedi.file_io import FolderIO
from jedi.parser_utils import get_cached_code_lines
from jedi.inference import sys_path
from jedi.inference import helpers
from jedi.inference import compiled
from jedi.inference import analysis
from jedi.inference.utils import unite
from jedi.inference.cache import inference_state_method_cache
from jedi.inference.names import ImportName, SubModuleName
from jedi.inference.base_value import ValueSet, NO_VALUES
from jedi.inference.gradual.typeshed import import_module_decorator, \
    create_stub_module, parse_stub_module
from jedi.inference.compiled.subprocess.functions import ImplicitNSInfo
from jedi.plugins import plugin_manager


class ModuleCache:
    def __init__(self):
        self._name_cache = {}

    def add(self, string_names, value_set):
        if string_names is not None:
            self._name_cache[string_names] = value_set

    def get(self, string_names):
        return self._name_cache.get(string_names)


# This memoization is needed, because otherwise we will infinitely loop on
# certain imports.
@inference_state_method_cache(default=NO_VALUES)
def infer_import(context, tree_name):
    module_context = context.get_root_context()
    from_import_name, import_path, level, values = \
        _prepare_infer_import(module_context, tree_name)
    if values:

        if from_import_name is not None:
            values = values.py__getattribute__(
                from_import_name,
                name_context=context,
                analysis_errors=False
            )

            if not values:
                path = import_path + (from_import_name,)
                importer = Importer(context.inference_state, path, module_context, level)
                values = importer.follow()
    debug.dbg('after import: %s', values)
    return values


@inference_state_method_cache(default=[])
def goto_import(context, tree_name):
    module_context = context.get_root_context()
    from_import_name, import_path, level, values = \
        _prepare_infer_import(module_context, tree_name)
    if not values:
        return []

    if from_import_name is not None:
        names = unite([
            c.goto(
                from_import_name,
                name_context=context,
                analysis_errors=False
            ) for c in values
        ])
        # Avoid recursion on the same names.
        if names and not any(n.tree_name is tree_name for n in names):
            return names

        path = import_path + (from_import_name,)
        importer = Importer(context.inference_state, path, module_context, level)
        values = importer.follow()
    return set(s.name for s in values)


def _prepare_infer_import(module_context, tree_name):
    import_node = search_ancestor(tree_name, 'import_name', 'import_from')
    import_path = import_node.get_path_for_name(tree_name)
    from_import_name = None
    try:
        from_names = import_node.get_from_names()
    except AttributeError:
        # Is an import_name
        pass
    else:
        if len(from_names) + 1 == len(import_path):
            # We have to fetch the from_names part first and then check
            # if from_names exists in the modules.
            from_import_name = import_path[-1]
            import_path = from_names

    importer = Importer(module_context.inference_state, tuple(import_path),
                        module_context, import_node.level)

    return from_import_name, tuple(import_path), import_node.level, importer.follow()


def _add_error(value, name, message):
    if hasattr(name, 'parent') and value is not None:
        analysis.add(value, 'import-error', name, message)
    else:
        debug.warning('ImportError without origin: ' + message)


def _level_to_base_import_path(project_path, directory, level):
    """
    In case the level is outside of the currently known package (something like
    import .....foo), we can still try our best to help the user for
    completions.
    """
    for i in range(level - 1):
        old = directory
        directory = os.path.dirname(directory)
        if old == directory:
            return None, None

    d = directory
    level_import_paths = []
    # Now that we are on the level that the user wants to be, calculate the
    # import path for it.
    while True:
        if d == project_path:
            return level_import_paths, d
        dir_name = os.path.basename(d)
        if dir_name:
            level_import_paths.insert(0, dir_name)
            d = os.path.dirname(d)
        else:
            return None, directory


class Importer:
    def __init__(self, inference_state, import_path, module_context, level=0):
        """
        An implementation similar to ``__import__``. Use `follow`
        to actually follow the imports.

        *level* specifies whether to use absolute or relative imports. 0 (the
        default) means only perform absolute imports. Positive values for level
        indicate the number of parent directories to search relative to the
        directory of the module calling ``__import__()`` (see PEP 328 for the
        details).

        :param import_path: List of namespaces (strings or Names).
        """
        debug.speed('import %s %s' % (import_path, module_context))
        self._inference_state = inference_state
        self.level = level
        self._module_context = module_context

        self._fixed_sys_path = None
        self._infer_possible = True
        if level:
            base = module_context.get_value().py__package__()
            # We need to care for two cases, the first one is if it's a valid
            # Python import. This import has a properly defined module name
            # chain like `foo.bar.baz` and an import in baz is made for
            # `..lala.` It can then resolve to `foo.bar.lala`.
            # The else here is a heuristic for all other cases, if for example
            # in `foo` you search for `...bar`, it's obviously out of scope.
            # However since Jedi tries to just do it's best, we help the user
            # here, because he might have specified something wrong in his
            # project.
            if level <= len(base):
                # Here we basically rewrite the level to 0.
                base = tuple(base)
                if level > 1:
                    base = base[:-level + 1]
                import_path = base + tuple(import_path)
            else:
                path = module_context.py__file__()
                project_path = self._inference_state.project.path
                import_path = list(import_path)
                if path is None:
                    # If no path is defined, our best guess is that the current
                    # file is edited by a user on the current working
                    # directory. We need to add an initial path, because it
                    # will get removed as the name of the current file.
                    directory = project_path
                else:
                    directory = os.path.dirname(path)

                base_import_path, base_directory = _level_to_base_import_path(
                    project_path, directory, level,
                )
                if base_directory is None:
                    # Everything is lost, the relative import does point
                    # somewhere out of the filesystem.
                    self._infer_possible = False
                else:
                    self._fixed_sys_path = [base_directory]

                if base_import_path is None:
                    if import_path:
                        _add_error(
                            module_context, import_path[0],
                            message='Attempted relative import beyond top-level package.'
                        )
                else:
                    import_path = base_import_path + import_path
        self.import_path = import_path

    @property
    def _str_import_path(self):
        """Returns the import path as pure strings instead of `Name`."""
        return tuple(
            name.value if isinstance(name, tree.Name) else name
            for name in self.import_path
        )

    def _sys_path_with_modifications(self, is_completion):
        if self._fixed_sys_path is not None:
            return self._fixed_sys_path

        return (
            # For import completions we don't want to see init paths, but for
            # inference we want to show the user as much as possible.
            # See GH #1446.
            self._inference_state.get_sys_path(add_init_paths=not is_completion)
            + [
                str(p) for p
                in sys_path.check_sys_path_modifications(self._module_context)
            ]
        )

    def follow(self):
        if not self.import_path:
            if self._fixed_sys_path:
                # This is a bit of a special case, that maybe should be
                # revisited. If the project path is wrong or the user uses
                # relative imports the wrong way, we might end up here, where
                # the `fixed_sys_path == project.path` in that case we kind of
                # use the project.path.parent directory as our path. This is
                # usually not a problem, except if imports in other places are
                # using the same names. Example:
                #
                # foo/                       < #1
                #   - setup.py
                #   - foo/                   < #2
                #     - __init__.py
                #     - foo.py               < #3
                #
                # If the top foo is our project folder and somebody uses
                # `from . import foo` in `setup.py`, it will resolve to foo #2,
                # which means that the import for foo.foo is cached as
                # `__init__.py` (#2) and not as `foo.py` (#3). This is usually
                # not an issue, because this case is probably pretty rare, but
                # might be an issue for some people.
                #
                # However for most normal cases where we work with different
                # file names, this code path hits where we basically change the
                # project path to an ancestor of project path.
                from jedi.inference.value.namespace import ImplicitNamespaceValue
                import_path = (os.path.basename(self._fixed_sys_path[0]),)
                ns = ImplicitNamespaceValue(
                    self._inference_state,
                    string_names=import_path,
                    paths=self._fixed_sys_path,
                )
                return ValueSet({ns})
            return NO_VALUES
        if not self._infer_possible:
            return NO_VALUES

        # Check caches first
        from_cache = self._inference_state.stub_module_cache.get(self._str_import_path)
        if from_cache is not None:
            return ValueSet({from_cache})
        from_cache = self._inference_state.module_cache.get(self._str_import_path)
        if from_cache is not None:
            return from_cache

        sys_path = self._sys_path_with_modifications(is_completion=False)

        return import_module_by_names(
            self._inference_state, self.import_path, sys_path, self._module_context
        )

    def _get_module_names(self, search_path=None, in_module=None):
        """
        Get the names of all modules in the search_path. This means file names
        and not names defined in the files.
        """
        if search_path is None:
            sys_path = self._sys_path_with_modifications(is_completion=True)
        else:
            sys_path = search_path
        return list(iter_module_names(
            self._inference_state, self._module_context, sys_path,
            module_cls=ImportName if in_module is None else SubModuleName,
            add_builtin_modules=search_path is None and in_module is None,
        ))

    def completion_names(self, inference_state, only_modules=False):
        """
        :param only_modules: Indicates wheter it's possible to import a
            definition that is not defined in a module.
        """
        if not self._infer_possible:
            return []

        names = []
        if self.import_path:
            # flask
            if self._str_import_path == ('flask', 'ext'):
                # List Flask extensions like ``flask_foo``
                for mod in self._get_module_names():
                    modname = mod.string_name
                    if modname.startswith('flask_'):
                        extname = modname[len('flask_'):]
                        names.append(ImportName(self._module_context, extname))
                # Now the old style: ``flaskext.foo``
                for dir in self._sys_path_with_modifications(is_completion=True):
                    flaskext = os.path.join(dir, 'flaskext')
                    if os.path.isdir(flaskext):
                        names += self._get_module_names([flaskext])

            values = self.follow()
            for value in values:
                # Non-modules are not completable.
                if value.api_type not in ('module', 'namespace'):  # not a module
                    continue
                if not value.is_compiled():
                    # sub_modules_dict is not implemented for compiled modules.
                    names += value.sub_modules_dict().values()

            if not only_modules:
                from jedi.inference.gradual.conversion import convert_values

                both_values = values | convert_values(values)
                for c in both_values:
                    for filter in c.get_filters():
                        names += filter.values()
        else:
            if self.level:
                # We only get here if the level cannot be properly calculated.
                names += self._get_module_names(self._fixed_sys_path)
            else:
                # This is just the list of global imports.
                names += self._get_module_names()
        return names


def import_module_by_names(inference_state, import_names, sys_path=None,
                           module_context=None, prefer_stubs=True):
    if sys_path is None:
        sys_path = inference_state.get_sys_path()

    str_import_names = tuple(
        i.value if isinstance(i, tree.Name) else i
        for i in import_names
    )
    value_set = [None]
    for i, name in enumerate(import_names):
        value_set = ValueSet.from_sets([
            import_module(
                inference_state,
                str_import_names[:i+1],
                parent_module_value,
                sys_path,
                prefer_stubs=prefer_stubs,
            ) for parent_module_value in value_set
        ])
        if not value_set:
            message = 'No module named ' + '.'.join(str_import_names)
            if module_context is not None:
                _add_error(module_context, name, message)
            else:
                debug.warning(message)
            return NO_VALUES
    return value_set


@plugin_manager.decorate()
@import_module_decorator
def import_module(inference_state, import_names, parent_module_value, sys_path):
    """
    This method is very similar to importlib's `_gcd_import`.
    """
    if import_names[0] in settings.auto_import_modules:
        module = _load_builtin_module(inference_state, import_names, sys_path)
        if module is None:
            return NO_VALUES
        return ValueSet([module])

    module_name = '.'.join(import_names)
    if parent_module_value is None:
        # Override the sys.path. It works only good that way.
        # Injecting the path directly into `find_module` did not work.
        file_io_or_ns, is_pkg = inference_state.compiled_subprocess.get_module_info(
            string=import_names[-1],
            full_name=module_name,
            sys_path=sys_path,
            is_global_search=True,
        )
        if is_pkg is None:
            return NO_VALUES
    else:
        paths = parent_module_value.py__path__()
        if paths is None:
            # The module might not be a package.
            return NO_VALUES

        file_io_or_ns, is_pkg = inference_state.compiled_subprocess.get_module_info(
            string=import_names[-1],
            path=paths,
            full_name=module_name,
            is_global_search=False,
        )
        if is_pkg is None:
            return NO_VALUES

    if isinstance(file_io_or_ns, ImplicitNSInfo):
        from jedi.inference.value.namespace import ImplicitNamespaceValue
        module = ImplicitNamespaceValue(
            inference_state,
            string_names=tuple(file_io_or_ns.name.split('.')),
            paths=file_io_or_ns.paths,
        )
    elif file_io_or_ns is None:
        module = _load_builtin_module(inference_state, import_names, sys_path)
        if module is None:
            return NO_VALUES
    else:
        module = _load_python_module(
            inference_state, file_io_or_ns,
            import_names=import_names,
            is_package=is_pkg,
        )

    if parent_module_value is None:
        debug.dbg('global search_module %s: %s', import_names[-1], module)
    else:
        debug.dbg('search_module %s in paths %s: %s', module_name, paths, module)
    return ValueSet([module])


def _load_python_module(inference_state, file_io,
                        import_names=None, is_package=False):
    module_node = inference_state.parse(
        file_io=file_io,
        cache=True,
        diff_cache=settings.fast_parser,
        cache_path=settings.cache_directory,
    )

    from jedi.inference.value import ModuleValue
    return ModuleValue(
        inference_state, module_node,
        file_io=file_io,
        string_names=import_names,
        code_lines=get_cached_code_lines(inference_state.grammar, file_io.path),
        is_package=is_package,
    )


def _load_builtin_module(inference_state, import_names=None, sys_path=None):
    project = inference_state.project
    if sys_path is None:
        sys_path = inference_state.get_sys_path()
    if not project._load_unsafe_extensions:
        safe_paths = project._get_base_sys_path(inference_state)
        sys_path = [p for p in sys_path if p in safe_paths]

    dotted_name = '.'.join(import_names)
    assert dotted_name is not None
    module = compiled.load_module(inference_state, dotted_name=dotted_name, sys_path=sys_path)
    if module is None:
        # The file might raise an ImportError e.g. and therefore not be
        # importable.
        return None
    return module


def load_module_from_path(inference_state, file_io, import_names=None, is_package=None):
    """
    This should pretty much only be used for get_modules_containing_name. It's
    here to ensure that a random path is still properly loaded into the Jedi
    module structure.
    """
    path = Path(file_io.path)
    if import_names is None:
        e_sys_path = inference_state.get_sys_path()
        import_names, is_package = sys_path.transform_path_to_dotted(e_sys_path, path)
    else:
        assert isinstance(is_package, bool)

    is_stub = path.suffix == '.pyi'
    if is_stub:
        folder_io = file_io.get_parent_folder()
        if folder_io.path.endswith('-stubs'):
            folder_io = FolderIO(folder_io.path[:-6])
        if path.name == '__init__.pyi':
            python_file_io = folder_io.get_file_io('__init__.py')
        else:
            python_file_io = folder_io.get_file_io(import_names[-1] + '.py')

        try:
            v = load_module_from_path(
                inference_state, python_file_io,
                import_names, is_package=is_package
            )
            values = ValueSet([v])
        except FileNotFoundError:
            values = NO_VALUES

        return create_stub_module(
            inference_state, inference_state.latest_grammar, values,
            parse_stub_module(inference_state, file_io), file_io, import_names
        )
    else:
        module = _load_python_module(
            inference_state, file_io,
            import_names=import_names,
            is_package=is_package,
        )
        inference_state.module_cache.add(import_names, ValueSet([module]))
        return module


def load_namespace_from_path(inference_state, folder_io):
    import_names, is_package = sys_path.transform_path_to_dotted(
        inference_state.get_sys_path(),
        Path(folder_io.path)
    )
    from jedi.inference.value.namespace import ImplicitNamespaceValue
    return ImplicitNamespaceValue(inference_state, import_names, [folder_io.path])


def follow_error_node_imports_if_possible(context, name):
    error_node = tree.search_ancestor(name, 'error_node')
    if error_node is not None:
        # Get the first command start of a started simple_stmt. The error
        # node is sometimes a small_stmt and sometimes a simple_stmt. Check
        # for ; leaves that start a new statements.
        start_index = 0
        for index, n in enumerate(error_node.children):
            if n.start_pos > name.start_pos:
                break
            if n == ';':
                start_index = index + 1
        nodes = error_node.children[start_index:]
        first_name = nodes[0].get_first_leaf().value

        # Make it possible to infer stuff like `import foo.` or
        # `from foo.bar`.
        if first_name in ('from', 'import'):
            is_import_from = first_name == 'from'
            level, names = helpers.parse_dotted_names(
                nodes,
                is_import_from=is_import_from,
                until_node=name,
            )
            return Importer(
                context.inference_state, names, context.get_root_context(), level).follow()
    return None


def iter_module_names(inference_state, module_context, search_path,
                      module_cls=ImportName, add_builtin_modules=True):
    """
    Get the names of all modules in the search_path. This means file names
    and not names defined in the files.
    """
    # add builtin module names
    if add_builtin_modules:
        for name in inference_state.compiled_subprocess.get_builtin_module_names():
            yield module_cls(module_context, name)

    for name in inference_state.compiled_subprocess.iter_module_names(search_path):
        yield module_cls(module_context, name)

# === NexusCore/openenv\Lib\site-packages\matplotlib\backends\qt_editor\_formlayout.py ===
"""
formlayout
==========

Module creating Qt form dialogs/layouts to edit various type of parameters


formlayout License Agreement (MIT License)
------------------------------------------

Copyright (c) 2009 Pierre Raybaut

Permission is hereby granted, free of charge, to any person
obtaining a copy of this software and associated documentation
files (the "Software"), to deal in the Software without
restriction, including without limitation the rights to use,
copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the
Software is furnished to do so, subject to the following
conditions:

The above copyright notice and this permission notice shall be
included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES
OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY,
WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
OTHER DEALINGS IN THE SOFTWARE.
"""

# History:
# 1.0.10: added float validator
#         (disable "Ok" and "Apply" button when not valid)
# 1.0.7: added support for "Apply" button
# 1.0.6: code cleaning

__version__ = '1.0.10'
__license__ = __doc__

from ast import literal_eval

import copy
import datetime
import logging
from numbers import Integral, Real

from matplotlib import _api, colors as mcolors
from matplotlib.backends.qt_compat import _to_int, QtGui, QtWidgets, QtCore

_log = logging.getLogger(__name__)

BLACKLIST = {"title", "label"}


class ColorButton(QtWidgets.QPushButton):
    """
    Color choosing push button
    """
    colorChanged = QtCore.Signal(QtGui.QColor)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(20, 20)
        self.setIconSize(QtCore.QSize(12, 12))
        self.clicked.connect(self.choose_color)
        self._color = QtGui.QColor()

    def choose_color(self):
        color = QtWidgets.QColorDialog.getColor(
            self._color, self.parentWidget(), "",
            QtWidgets.QColorDialog.ColorDialogOption.ShowAlphaChannel)
        if color.isValid():
            self.set_color(color)

    def get_color(self):
        return self._color

    @QtCore.Slot(QtGui.QColor)
    def set_color(self, color):
        if color != self._color:
            self._color = color
            self.colorChanged.emit(self._color)
            pixmap = QtGui.QPixmap(self.iconSize())
            pixmap.fill(color)
            self.setIcon(QtGui.QIcon(pixmap))

    color = QtCore.Property(QtGui.QColor, get_color, set_color)


def to_qcolor(color):
    """Create a QColor from a matplotlib color"""
    qcolor = QtGui.QColor()
    try:
        rgba = mcolors.to_rgba(color)
    except ValueError:
        _api.warn_external(f'Ignoring invalid color {color!r}')
        return qcolor  # return invalid QColor
    qcolor.setRgbF(*rgba)
    return qcolor


class ColorLayout(QtWidgets.QHBoxLayout):
    """Color-specialized QLineEdit layout"""
    def __init__(self, color, parent=None):
        super().__init__()
        assert isinstance(color, QtGui.QColor)
        self.lineedit = QtWidgets.QLineEdit(
            mcolors.to_hex(color.getRgbF(), keep_alpha=True), parent)
        self.lineedit.editingFinished.connect(self.update_color)
        self.addWidget(self.lineedit)
        self.colorbtn = ColorButton(parent)
        self.colorbtn.color = color
        self.colorbtn.colorChanged.connect(self.update_text)
        self.addWidget(self.colorbtn)

    def update_color(self):
        color = self.text()
        qcolor = to_qcolor(color)  # defaults to black if not qcolor.isValid()
        self.colorbtn.color = qcolor

    def update_text(self, color):
        self.lineedit.setText(mcolors.to_hex(color.getRgbF(), keep_alpha=True))

    def text(self):
        return self.lineedit.text()


def font_is_installed(font):
    """Check if font is installed"""
    return [fam for fam in QtGui.QFontDatabase().families()
            if str(fam) == font]


def tuple_to_qfont(tup):
    """
    Create a QFont from tuple:
        (family [string], size [int], italic [bool], bold [bool])
    """
    if not (isinstance(tup, tuple) and len(tup) == 4
            and font_is_installed(tup[0])
            and isinstance(tup[1], Integral)
            and isinstance(tup[2], bool)
            and isinstance(tup[3], bool)):
        return None
    font = QtGui.QFont()
    family, size, italic, bold = tup
    font.setFamily(family)
    font.setPointSize(size)
    font.setItalic(italic)
    font.setBold(bold)
    return font


def qfont_to_tuple(font):
    return (str(font.family()), int(font.pointSize()),
            font.italic(), font.bold())


class FontLayout(QtWidgets.QGridLayout):
    """Font selection"""
    def __init__(self, value, parent=None):
        super().__init__()
        font = tuple_to_qfont(value)
        assert font is not None

        # Font family
        self.family = QtWidgets.QFontComboBox(parent)
        self.family.setCurrentFont(font)
        self.addWidget(self.family, 0, 0, 1, -1)

        # Font size
        self.size = QtWidgets.QComboBox(parent)
        self.size.setEditable(True)
        sizelist = [*range(6, 12), *range(12, 30, 2), 36, 48, 72]
        size = font.pointSize()
        if size not in sizelist:
            sizelist.append(size)
            sizelist.sort()
        self.size.addItems([str(s) for s in sizelist])
        self.size.setCurrentIndex(sizelist.index(size))
        self.addWidget(self.size, 1, 0)

        # Italic or not
        self.italic = QtWidgets.QCheckBox(self.tr("Italic"), parent)
        self.italic.setChecked(font.italic())
        self.addWidget(self.italic, 1, 1)

        # Bold or not
        self.bold = QtWidgets.QCheckBox(self.tr("Bold"), parent)
        self.bold.setChecked(font.bold())
        self.addWidget(self.bold, 1, 2)

    def get_font(self):
        font = self.family.currentFont()
        font.setItalic(self.italic.isChecked())
        font.setBold(self.bold.isChecked())
        font.setPointSize(int(self.size.currentText()))
        return qfont_to_tuple(font)


def is_edit_valid(edit):
    text = edit.text()
    state = edit.validator().validate(text, 0)[0]
    return state == QtGui.QDoubleValidator.State.Acceptable


class FormWidget(QtWidgets.QWidget):
    update_buttons = QtCore.Signal()

    def __init__(self, data, comment="", with_margin=False, parent=None):
        """
        Parameters
        ----------
        data : list of (label, value) pairs
            The data to be edited in the form.
        comment : str, optional
        with_margin : bool, default: False
            If False, the form elements reach to the border of the widget.
            This is the desired behavior if the FormWidget is used as a widget
            alongside with other widgets such as a QComboBox, which also do
            not have a margin around them.
            However, a margin can be desired if the FormWidget is the only
            widget within a container, e.g. a tab in a QTabWidget.
        parent : QWidget or None
            The parent widget.
        """
        super().__init__(parent)
        self.data = copy.deepcopy(data)
        self.widgets = []
        self.formlayout = QtWidgets.QFormLayout(self)
        if not with_margin:
            self.formlayout.setContentsMargins(0, 0, 0, 0)
        if comment:
            self.formlayout.addRow(QtWidgets.QLabel(comment))
            self.formlayout.addRow(QtWidgets.QLabel(" "))

    def get_dialog(self):
        """Return FormDialog instance"""
        dialog = self.parent()
        while not isinstance(dialog, QtWidgets.QDialog):
            dialog = dialog.parent()
        return dialog

    def setup(self):
        for label, value in self.data:
            if label is None and value is None:
                # Separator: (None, None)
                self.formlayout.addRow(QtWidgets.QLabel(" "),
                                       QtWidgets.QLabel(" "))
                self.widgets.append(None)
                continue
            elif label is None:
                # Comment
                self.formlayout.addRow(QtWidgets.QLabel(value))
                self.widgets.append(None)
                continue
            elif tuple_to_qfont(value) is not None:
                field = FontLayout(value, self)
            elif (label.lower() not in BLACKLIST
                  and mcolors.is_color_like(value)):
                field = ColorLayout(to_qcolor(value), self)
            elif isinstance(value, str):
                field = QtWidgets.QLineEdit(value, self)
            elif isinstance(value, (list, tuple)):
                if isinstance(value, tuple):
                    value = list(value)
                # Note: get() below checks the type of value[0] in self.data so
                # it is essential that value gets modified in-place.
                # This means that the code is actually broken in the case where
                # value is a tuple, but fortunately we always pass a list...
                selindex = value.pop(0)
                field = QtWidgets.QComboBox(self)
                if isinstance(value[0], (list, tuple)):
                    keys = [key for key, _val in value]
                    value = [val for _key, val in value]
                else:
                    keys = value
                field.addItems(value)
                if selindex in value:
                    selindex = value.index(selindex)
                elif selindex in keys:
                    selindex = keys.index(selindex)
                elif not isinstance(selindex, Integral):
                    _log.warning(
                        "index '%s' is invalid (label: %s, value: %s)",
                        selindex, label, value)
                    selindex = 0
                field.setCurrentIndex(selindex)
            elif isinstance(value, bool):
                field = QtWidgets.QCheckBox(self)
                field.setChecked(value)
            elif isinstance(value, Integral):
                field = QtWidgets.QSpinBox(self)
                field.setRange(-10**9, 10**9)
                field.setValue(value)
            elif isinstance(value, Real):
                field = QtWidgets.QLineEdit(repr(value), self)
                field.setCursorPosition(0)
                field.setValidator(QtGui.QDoubleValidator(field))
                field.validator().setLocale(QtCore.QLocale("C"))
                dialog = self.get_dialog()
                dialog.register_float_field(field)
                field.textChanged.connect(lambda text: dialog.update_buttons())
            elif isinstance(value, datetime.datetime):
                field = QtWidgets.QDateTimeEdit(self)
                field.setDateTime(value)
            elif isinstance(value, datetime.date):
                field = QtWidgets.QDateEdit(self)
                field.setDate(value)
            else:
                field = QtWidgets.QLineEdit(repr(value), self)
            self.formlayout.addRow(label, field)
            self.widgets.append(field)

    def get(self):
        valuelist = []
        for index, (label, value) in enumerate(self.data):
            field = self.widgets[index]
            if label is None:
                # Separator / Comment
                continue
            elif tuple_to_qfont(value) is not None:
                value = field.get_font()
            elif isinstance(value, str) or mcolors.is_color_like(value):
                value = str(field.text())
            elif isinstance(value, (list, tuple)):
                index = int(field.currentIndex())
                if isinstance(value[0], (list, tuple)):
                    value = value[index][0]
                else:
                    value = value[index]
            elif isinstance(value, bool):
                value = field.isChecked()
            elif isinstance(value, Integral):
                value = int(field.value())
            elif isinstance(value, Real):
                value = float(str(field.text()))
            elif isinstance(value, datetime.datetime):
                datetime_ = field.dateTime()
                if hasattr(datetime_, "toPyDateTime"):
                    value = datetime_.toPyDateTime()
                else:
                    value = datetime_.toPython()
            elif isinstance(value, datetime.date):
                date_ = field.date()
                if hasattr(date_, "toPyDate"):
                    value = date_.toPyDate()
                else:
                    value = date_.toPython()
            else:
                value = literal_eval(str(field.text()))
            valuelist.append(value)
        return valuelist


class FormComboWidget(QtWidgets.QWidget):
    update_buttons = QtCore.Signal()

    def __init__(self, datalist, comment="", parent=None):
        super().__init__(parent)
        layout = QtWidgets.QVBoxLayout()
        self.setLayout(layout)
        self.combobox = QtWidgets.QComboBox()
        layout.addWidget(self.combobox)

        self.stackwidget = QtWidgets.QStackedWidget(self)
        layout.addWidget(self.stackwidget)
        self.combobox.currentIndexChanged.connect(
            self.stackwidget.setCurrentIndex)

        self.widgetlist = []
        for data, title, comment in datalist:
            self.combobox.addItem(title)
            widget = FormWidget(data, comment=comment, parent=self)
            self.stackwidget.addWidget(widget)
            self.widgetlist.append(widget)

    def setup(self):
        for widget in self.widgetlist:
            widget.setup()

    def get(self):
        return [widget.get() for widget in self.widgetlist]


class FormTabWidget(QtWidgets.QWidget):
    update_buttons = QtCore.Signal()

    def __init__(self, datalist, comment="", parent=None):
        super().__init__(parent)
        layout = QtWidgets.QVBoxLayout()
        self.tabwidget = QtWidgets.QTabWidget()
        layout.addWidget(self.tabwidget)
        layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(layout)
        self.widgetlist = []
        for data, title, comment in datalist:
            if len(data[0]) == 3:
                widget = FormComboWidget(data, comment=comment, parent=self)
            else:
                widget = FormWidget(data, with_margin=True, comment=comment,
                                    parent=self)
            index = self.tabwidget.addTab(widget, title)
            self.tabwidget.setTabToolTip(index, comment)
            self.widgetlist.append(widget)

    def setup(self):
        for widget in self.widgetlist:
            widget.setup()

    def get(self):
        return [widget.get() for widget in self.widgetlist]


class FormDialog(QtWidgets.QDialog):
    """Form Dialog"""
    def __init__(self, data, title="", comment="",
                 icon=None, parent=None, apply=None):
        super().__init__(parent)

        self.apply_callback = apply

        # Form
        if isinstance(data[0][0], (list, tuple)):
            self.formwidget = FormTabWidget(data, comment=comment,
                                            parent=self)
        elif len(data[0]) == 3:
            self.formwidget = FormComboWidget(data, comment=comment,
                                              parent=self)
        else:
            self.formwidget = FormWidget(data, comment=comment,
                                         parent=self)
        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(self.formwidget)

        self.float_fields = []
        self.formwidget.setup()

        # Button box
        self.bbox = bbox = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.StandardButton(
                    _to_int(QtWidgets.QDialogButtonBox.StandardButton.Ok) |
                    _to_int(QtWidgets.QDialogButtonBox.StandardButton.Cancel)
            ))
        self.formwidget.update_buttons.connect(self.update_buttons)
        if self.apply_callback is not None:
            apply_btn = bbox.addButton(
                QtWidgets.QDialogButtonBox.StandardButton.Apply)
            apply_btn.clicked.connect(self.apply)

        bbox.accepted.connect(self.accept)
        bbox.rejected.connect(self.reject)
        layout.addWidget(bbox)

        self.setLayout(layout)

        self.setWindowTitle(title)
        if not isinstance(icon, QtGui.QIcon):
            icon = QtWidgets.QWidget().style().standardIcon(
                QtWidgets.QStyle.SP_MessageBoxQuestion)
        self.setWindowIcon(icon)

    def register_float_field(self, field):
        self.float_fields.append(field)

    def update_buttons(self):
        valid = True
        for field in self.float_fields:
            if not is_edit_valid(field):
                valid = False
        for btn_type in ["Ok", "Apply"]:
            btn = self.bbox.button(
                getattr(QtWidgets.QDialogButtonBox.StandardButton,
                        btn_type))
            if btn is not None:
                btn.setEnabled(valid)

    def accept(self):
        self.data = self.formwidget.get()
        self.apply_callback(self.data)
        super().accept()

    def reject(self):
        self.data = None
        super().reject()

    def apply(self):
        self.apply_callback(self.formwidget.get())

    def get(self):
        """Return form result"""
        return self.data


def fedit(data, title="", comment="", icon=None, parent=None, apply=None):
    """
    Create form dialog

    data: datalist, datagroup
    title: str
    comment: str
    icon: QIcon instance
    parent: parent QWidget
    apply: apply callback (function)

    datalist: list/tuple of (field_name, field_value)
    datagroup: list/tuple of (datalist *or* datagroup, title, comment)

    -> one field for each member of a datalist
    -> one tab for each member of a top-level datagroup
    -> one page (of a multipage widget, each page can be selected with a combo
       box) for each member of a datagroup inside a datagroup

    Supported types for field_value:
      - int, float, str, bool
      - colors: in Qt-compatible text form, i.e. in hex format or name
                (red, ...) (automatically detected from a string)
      - list/tuple:
          * the first element will be the selected index (or value)
          * the other elements can be couples (key, value) or only values
    """

    # Create a QApplication instance if no instance currently exists
    # (e.g., if the module is used directly from the interpreter)
    if QtWidgets.QApplication.startingUp():
        _app = QtWidgets.QApplication([])
    dialog = FormDialog(data, title, comment, icon, parent, apply)

    if parent is not None:
        if hasattr(parent, "_fedit_dialog"):
            parent._fedit_dialog.close()
        parent._fedit_dialog = dialog

    dialog.show()


if __name__ == "__main__":

    _app = QtWidgets.QApplication([])

    def create_datalist_example():
        return [('str', 'this is a string'),
                ('list', [0, '1', '3', '4']),
                ('list2', ['--', ('none', 'None'), ('--', 'Dashed'),
                           ('-.', 'DashDot'), ('-', 'Solid'),
                           ('steps', 'Steps'), (':', 'Dotted')]),
                ('float', 1.2),
                (None, 'Other:'),
                ('int', 12),
                ('font', ('Arial', 10, False, True)),
                ('color', '#123409'),
                ('bool', True),
                ('date', datetime.date(2010, 10, 10)),
                ('datetime', datetime.datetime(2010, 10, 10)),
                ]

    def create_datagroup_example():
        datalist = create_datalist_example()
        return ((datalist, "Category 1", "Category 1 comment"),
                (datalist, "Category 2", "Category 2 comment"),
                (datalist, "Category 3", "Category 3 comment"))

    # --------- datalist example
    datalist = create_datalist_example()

    def apply_test(data):
        print("data:", data)
    fedit(datalist, title="Example",
          comment="This is just an <b>example</b>.",
          apply=apply_test)

    _app.exec()

    # --------- datagroup example
    datagroup = create_datagroup_example()
    fedit(datagroup, "Global title",
          apply=apply_test)
    _app.exec()

    # --------- datagroup inside a datagroup example
    datalist = create_datalist_example()
    datagroup = create_datagroup_example()
    fedit(((datagroup, "Title 1", "Tab 1 comment"),
           (datalist, "Title 2", "Tab 2 comment"),
           (datalist, "Title 3", "Tab 3 comment")),
          "Global title",
          apply=apply_test)
    _app.exec()

# === NexusCore/openenv\Lib\site-packages\tornado\curl_httpclient.py ===
#
# Copyright 2009 Facebook
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

"""Non-blocking HTTP client implementation using pycurl."""

import collections
import functools
import logging
import pycurl
import re
import threading
import time
from io import BytesIO

from tornado import httputil
from tornado import ioloop

from tornado.escape import utf8, native_str
from tornado.httpclient import (
    HTTPRequest,
    HTTPResponse,
    HTTPError,
    AsyncHTTPClient,
    main,
)
from tornado.log import app_log

from typing import Dict, Any, Callable, Union, Optional
import typing

if typing.TYPE_CHECKING:
    from typing import Deque, Tuple  # noqa: F401

curl_log = logging.getLogger("tornado.curl_httpclient")

CR_OR_LF_RE = re.compile(b"\r|\n")


class CurlAsyncHTTPClient(AsyncHTTPClient):
    def initialize(  # type: ignore
        self, max_clients: int = 10, defaults: Optional[Dict[str, Any]] = None
    ) -> None:
        super().initialize(defaults=defaults)
        # Typeshed is incomplete for CurlMulti, so just use Any for now.
        self._multi = pycurl.CurlMulti()  # type: Any
        self._multi.setopt(pycurl.M_TIMERFUNCTION, self._set_timeout)
        self._multi.setopt(pycurl.M_SOCKETFUNCTION, self._handle_socket)
        self._curls = [self._curl_create() for i in range(max_clients)]
        self._free_list = self._curls[:]
        self._requests = (
            collections.deque()
        )  # type: Deque[Tuple[HTTPRequest, Callable[[HTTPResponse], None], float]]
        self._fds = {}  # type: Dict[int, int]
        self._timeout = None  # type: Optional[object]

        # libcurl has bugs that sometimes cause it to not report all
        # relevant file descriptors and timeouts to TIMERFUNCTION/
        # SOCKETFUNCTION.  Mitigate the effects of such bugs by
        # forcing a periodic scan of all active requests.
        self._force_timeout_callback = ioloop.PeriodicCallback(
            self._handle_force_timeout, 1000
        )
        self._force_timeout_callback.start()

        # Work around a bug in libcurl 7.29.0: Some fields in the curl
        # multi object are initialized lazily, and its destructor will
        # segfault if it is destroyed without having been used.  Add
        # and remove a dummy handle to make sure everything is
        # initialized.
        dummy_curl_handle = pycurl.Curl()
        self._multi.add_handle(dummy_curl_handle)
        self._multi.remove_handle(dummy_curl_handle)

    def close(self) -> None:
        self._force_timeout_callback.stop()
        if self._timeout is not None:
            self.io_loop.remove_timeout(self._timeout)
        for curl in self._curls:
            curl.close()
        self._multi.close()
        super().close()

        # Set below properties to None to reduce the reference count of current
        # instance, because those properties hold some methods of current
        # instance that will case circular reference.
        self._force_timeout_callback = None  # type: ignore
        self._multi = None

    def fetch_impl(
        self, request: HTTPRequest, callback: Callable[[HTTPResponse], None]
    ) -> None:
        self._requests.append((request, callback, self.io_loop.time()))
        self._process_queue()
        self._set_timeout(0)

    def _handle_socket(self, event: int, fd: int, multi: Any, data: bytes) -> None:
        """Called by libcurl when it wants to change the file descriptors
        it cares about.
        """
        event_map = {
            pycurl.POLL_NONE: ioloop.IOLoop.NONE,
            pycurl.POLL_IN: ioloop.IOLoop.READ,
            pycurl.POLL_OUT: ioloop.IOLoop.WRITE,
            pycurl.POLL_INOUT: ioloop.IOLoop.READ | ioloop.IOLoop.WRITE,
        }
        if event == pycurl.POLL_REMOVE:
            if fd in self._fds:
                self.io_loop.remove_handler(fd)
                del self._fds[fd]
        else:
            ioloop_event = event_map[event]
            # libcurl sometimes closes a socket and then opens a new
            # one using the same FD without giving us a POLL_NONE in
            # between.  This is a problem with the epoll IOLoop,
            # because the kernel can tell when a socket is closed and
            # removes it from the epoll automatically, causing future
            # update_handler calls to fail.  Since we can't tell when
            # this has happened, always use remove and re-add
            # instead of update.
            if fd in self._fds:
                self.io_loop.remove_handler(fd)
            self.io_loop.add_handler(fd, self._handle_events, ioloop_event)
            self._fds[fd] = ioloop_event

    def _set_timeout(self, msecs: int) -> None:
        """Called by libcurl to schedule a timeout."""
        if self._timeout is not None:
            self.io_loop.remove_timeout(self._timeout)
        self._timeout = self.io_loop.add_timeout(
            self.io_loop.time() + msecs / 1000.0, self._handle_timeout
        )

    def _handle_events(self, fd: int, events: int) -> None:
        """Called by IOLoop when there is activity on one of our
        file descriptors.
        """
        action = 0
        if events & ioloop.IOLoop.READ:
            action |= pycurl.CSELECT_IN
        if events & ioloop.IOLoop.WRITE:
            action |= pycurl.CSELECT_OUT
        while True:
            try:
                ret, num_handles = self._multi.socket_action(fd, action)
            except pycurl.error as e:
                ret = e.args[0]
            if ret != pycurl.E_CALL_MULTI_PERFORM:
                break
        self._finish_pending_requests()

    def _handle_timeout(self) -> None:
        """Called by IOLoop when the requested timeout has passed."""
        self._timeout = None
        while True:
            try:
                ret, num_handles = self._multi.socket_action(pycurl.SOCKET_TIMEOUT, 0)
            except pycurl.error as e:
                ret = e.args[0]
            if ret != pycurl.E_CALL_MULTI_PERFORM:
                break
        self._finish_pending_requests()

        # In theory, we shouldn't have to do this because curl will
        # call _set_timeout whenever the timeout changes.  However,
        # sometimes after _handle_timeout we will need to reschedule
        # immediately even though nothing has changed from curl's
        # perspective.  This is because when socket_action is
        # called with SOCKET_TIMEOUT, libcurl decides internally which
        # timeouts need to be processed by using a monotonic clock
        # (where available) while tornado uses python's time.time()
        # to decide when timeouts have occurred.  When those clocks
        # disagree on elapsed time (as they will whenever there is an
        # NTP adjustment), tornado might call _handle_timeout before
        # libcurl is ready.  After each timeout, resync the scheduled
        # timeout with libcurl's current state.
        new_timeout = self._multi.timeout()
        if new_timeout >= 0:
            self._set_timeout(new_timeout)

    def _handle_force_timeout(self) -> None:
        """Called by IOLoop periodically to ask libcurl to process any
        events it may have forgotten about.
        """
        while True:
            try:
                ret, num_handles = self._multi.socket_all()
            except pycurl.error as e:
                ret = e.args[0]
            if ret != pycurl.E_CALL_MULTI_PERFORM:
                break
        self._finish_pending_requests()

    def _finish_pending_requests(self) -> None:
        """Process any requests that were completed by the last
        call to multi.socket_action.
        """
        while True:
            num_q, ok_list, err_list = self._multi.info_read()
            for curl in ok_list:
                self._finish(curl)
            for curl, errnum, errmsg in err_list:
                self._finish(curl, errnum, errmsg)
            if num_q == 0:
                break
        self._process_queue()

    def _process_queue(self) -> None:
        while True:
            started = 0
            while self._free_list and self._requests:
                started += 1
                curl = self._free_list.pop()
                (request, callback, queue_start_time) = self._requests.popleft()
                # TODO: Don't smuggle extra data on an attribute of the Curl object.
                curl.info = {  # type: ignore
                    "headers": httputil.HTTPHeaders(),
                    "buffer": BytesIO(),
                    "request": request,
                    "callback": callback,
                    "queue_start_time": queue_start_time,
                    "curl_start_time": time.time(),
                    "curl_start_ioloop_time": self.io_loop.current().time(),  # type: ignore
                }
                try:
                    self._curl_setup_request(
                        curl,
                        request,
                        curl.info["buffer"],  # type: ignore
                        curl.info["headers"],  # type: ignore
                    )
                except Exception as e:
                    # If there was an error in setup, pass it on
                    # to the callback. Note that allowing the
                    # error to escape here will appear to work
                    # most of the time since we are still in the
                    # caller's original stack frame, but when
                    # _process_queue() is called from
                    # _finish_pending_requests the exceptions have
                    # nowhere to go.
                    self._free_list.append(curl)
                    callback(HTTPResponse(request=request, code=599, error=e))
                else:
                    self._multi.add_handle(curl)

            if not started:
                break

    def _finish(
        self,
        curl: pycurl.Curl,
        curl_error: Optional[int] = None,
        curl_message: Optional[str] = None,
    ) -> None:
        info = curl.info  # type: ignore
        curl.info = None  # type: ignore
        self._multi.remove_handle(curl)
        self._free_list.append(curl)
        buffer = info["buffer"]
        if curl_error:
            assert curl_message is not None
            error = CurlError(curl_error, curl_message)  # type: Optional[CurlError]
            assert error is not None
            code = error.code
            effective_url = None
            buffer.close()
            buffer = None
        else:
            error = None
            code = curl.getinfo(pycurl.HTTP_CODE)
            effective_url = curl.getinfo(pycurl.EFFECTIVE_URL)
            buffer.seek(0)
        # the various curl timings are documented at
        # http://curl.haxx.se/libcurl/c/curl_easy_getinfo.html
        time_info = dict(
            queue=info["curl_start_ioloop_time"] - info["queue_start_time"],
            namelookup=curl.getinfo(pycurl.NAMELOOKUP_TIME),
            connect=curl.getinfo(pycurl.CONNECT_TIME),
            appconnect=curl.getinfo(pycurl.APPCONNECT_TIME),
            pretransfer=curl.getinfo(pycurl.PRETRANSFER_TIME),
            starttransfer=curl.getinfo(pycurl.STARTTRANSFER_TIME),
            total=curl.getinfo(pycurl.TOTAL_TIME),
            redirect=curl.getinfo(pycurl.REDIRECT_TIME),
        )
        try:
            info["callback"](
                HTTPResponse(
                    request=info["request"],
                    code=code,
                    headers=info["headers"],
                    buffer=buffer,
                    effective_url=effective_url,
                    error=error,
                    reason=info["headers"].get("X-Http-Reason", None),
                    request_time=self.io_loop.time() - info["curl_start_ioloop_time"],
                    start_time=info["curl_start_time"],
                    time_info=time_info,
                )
            )
        except Exception:
            self.handle_callback_exception(info["callback"])

    def handle_callback_exception(self, callback: Any) -> None:
        app_log.error("Exception in callback %r", callback, exc_info=True)

    def _curl_create(self) -> pycurl.Curl:
        curl = pycurl.Curl()
        if curl_log.isEnabledFor(logging.DEBUG):
            curl.setopt(pycurl.VERBOSE, 1)
            curl.setopt(pycurl.DEBUGFUNCTION, self._curl_debug)
        if hasattr(
            pycurl, "PROTOCOLS"
        ):  # PROTOCOLS first appeared in pycurl 7.19.5 (2014-07-12)
            curl.setopt(pycurl.PROTOCOLS, pycurl.PROTO_HTTP | pycurl.PROTO_HTTPS)
            curl.setopt(pycurl.REDIR_PROTOCOLS, pycurl.PROTO_HTTP | pycurl.PROTO_HTTPS)
        return curl

    def _curl_setup_request(
        self,
        curl: pycurl.Curl,
        request: HTTPRequest,
        buffer: BytesIO,
        headers: httputil.HTTPHeaders,
    ) -> None:
        curl.setopt(pycurl.URL, native_str(request.url))

        # libcurl's magic "Expect: 100-continue" behavior causes delays
        # with servers that don't support it (which include, among others,
        # Google's OpenID endpoint).  Additionally, this behavior has
        # a bug in conjunction with the curl_multi_socket_action API
        # (https://sourceforge.net/tracker/?func=detail&atid=100976&aid=3039744&group_id=976),
        # which increases the delays.  It's more trouble than it's worth,
        # so just turn off the feature (yes, setting Expect: to an empty
        # value is the official way to disable this)
        if "Expect" not in request.headers:
            request.headers["Expect"] = ""

        # libcurl adds Pragma: no-cache by default; disable that too
        if "Pragma" not in request.headers:
            request.headers["Pragma"] = ""

        encoded_headers = [
            b"%s: %s"
            % (native_str(k).encode("ASCII"), native_str(v).encode("ISO8859-1"))
            for k, v in request.headers.get_all()
        ]
        for line in encoded_headers:
            if CR_OR_LF_RE.search(line):
                raise ValueError("Illegal characters in header (CR or LF): %r" % line)
        curl.setopt(pycurl.HTTPHEADER, encoded_headers)

        curl.setopt(
            pycurl.HEADERFUNCTION,
            functools.partial(
                self._curl_header_callback, headers, request.header_callback
            ),
        )
        if request.streaming_callback:

            def write_function(b: Union[bytes, bytearray]) -> int:
                assert request.streaming_callback is not None
                self.io_loop.add_callback(request.streaming_callback, b)
                return len(b)

        else:
            write_function = buffer.write  # type: ignore
        curl.setopt(pycurl.WRITEFUNCTION, write_function)
        curl.setopt(pycurl.FOLLOWLOCATION, request.follow_redirects)
        curl.setopt(pycurl.MAXREDIRS, request.max_redirects)
        assert request.connect_timeout is not None
        curl.setopt(pycurl.CONNECTTIMEOUT_MS, int(1000 * request.connect_timeout))
        assert request.request_timeout is not None
        curl.setopt(pycurl.TIMEOUT_MS, int(1000 * request.request_timeout))
        if request.user_agent:
            curl.setopt(pycurl.USERAGENT, native_str(request.user_agent))
        else:
            curl.setopt(pycurl.USERAGENT, "Mozilla/5.0 (compatible; pycurl)")
        if request.network_interface:
            curl.setopt(pycurl.INTERFACE, request.network_interface)
        if request.decompress_response:
            curl.setopt(pycurl.ENCODING, "gzip,deflate")
        else:
            curl.setopt(pycurl.ENCODING, None)
        if request.proxy_host and request.proxy_port:
            curl.setopt(pycurl.PROXY, request.proxy_host)
            curl.setopt(pycurl.PROXYPORT, request.proxy_port)
            if request.proxy_username:
                assert request.proxy_password is not None
                credentials = httputil.encode_username_password(
                    request.proxy_username, request.proxy_password
                )
                curl.setopt(pycurl.PROXYUSERPWD, credentials)

            if request.proxy_auth_mode is None or request.proxy_auth_mode == "basic":
                curl.setopt(pycurl.PROXYAUTH, pycurl.HTTPAUTH_BASIC)
            elif request.proxy_auth_mode == "digest":
                curl.setopt(pycurl.PROXYAUTH, pycurl.HTTPAUTH_DIGEST)
            else:
                raise ValueError(
                    "Unsupported proxy_auth_mode %s" % request.proxy_auth_mode
                )
        else:
            try:
                curl.unsetopt(pycurl.PROXY)
            except TypeError:  # not supported, disable proxy
                curl.setopt(pycurl.PROXY, "")
            curl.unsetopt(pycurl.PROXYUSERPWD)
        if request.validate_cert:
            curl.setopt(pycurl.SSL_VERIFYPEER, 1)
            curl.setopt(pycurl.SSL_VERIFYHOST, 2)
        else:
            curl.setopt(pycurl.SSL_VERIFYPEER, 0)
            curl.setopt(pycurl.SSL_VERIFYHOST, 0)
        if request.ca_certs is not None:
            curl.setopt(pycurl.CAINFO, request.ca_certs)
        else:
            # There is no way to restore pycurl.CAINFO to its default value
            # (Using unsetopt makes it reject all certificates).
            # I don't see any way to read the default value from python so it
            # can be restored later.  We'll have to just leave CAINFO untouched
            # if no ca_certs file was specified, and require that if any
            # request uses a custom ca_certs file, they all must.
            pass

        if request.allow_ipv6 is False:
            # Curl behaves reasonably when DNS resolution gives an ipv6 address
            # that we can't reach, so allow ipv6 unless the user asks to disable.
            curl.setopt(pycurl.IPRESOLVE, pycurl.IPRESOLVE_V4)
        else:
            curl.setopt(pycurl.IPRESOLVE, pycurl.IPRESOLVE_WHATEVER)

        # Set the request method through curl's irritating interface which makes
        # up names for almost every single method
        curl_options = {
            "GET": pycurl.HTTPGET,
            "POST": pycurl.POST,
            "PUT": pycurl.UPLOAD,
            "HEAD": pycurl.NOBODY,
        }
        custom_methods = {"DELETE", "OPTIONS", "PATCH"}
        for o in curl_options.values():
            curl.setopt(o, False)
        if request.method in curl_options:
            curl.unsetopt(pycurl.CUSTOMREQUEST)
            curl.setopt(curl_options[request.method], True)
        elif request.allow_nonstandard_methods or request.method in custom_methods:
            curl.setopt(pycurl.CUSTOMREQUEST, request.method)
        else:
            raise KeyError("unknown method " + request.method)

        body_expected = request.method in ("POST", "PATCH", "PUT")
        body_present = request.body is not None
        if not request.allow_nonstandard_methods:
            # Some HTTP methods nearly always have bodies while others
            # almost never do. Fail in this case unless the user has
            # opted out of sanity checks with allow_nonstandard_methods.
            if (body_expected and not body_present) or (
                body_present and not body_expected
            ):
                raise ValueError(
                    "Body must %sbe None for method %s (unless "
                    "allow_nonstandard_methods is true)"
                    % ("not " if body_expected else "", request.method)
                )

        if body_expected or body_present:
            if request.method == "GET":
                # Even with `allow_nonstandard_methods` we disallow
                # GET with a body (because libcurl doesn't allow it
                # unless we use CUSTOMREQUEST). While the spec doesn't
                # forbid clients from sending a body, it arguably
                # disallows the server from doing anything with them.
                raise ValueError("Body must be None for GET request")
            request_buffer = BytesIO(utf8(request.body or ""))

            def ioctl(cmd: int) -> None:
                if cmd == curl.IOCMD_RESTARTREAD:  # type: ignore
                    request_buffer.seek(0)

            curl.setopt(pycurl.READFUNCTION, request_buffer.read)
            curl.setopt(pycurl.IOCTLFUNCTION, ioctl)
            if request.method == "POST":
                curl.setopt(pycurl.POSTFIELDSIZE, len(request.body or ""))
            else:
                curl.setopt(pycurl.UPLOAD, True)
                curl.setopt(pycurl.INFILESIZE, len(request.body or ""))

        if request.auth_username is not None:
            assert request.auth_password is not None
            if request.auth_mode is None or request.auth_mode == "basic":
                curl.setopt(pycurl.HTTPAUTH, pycurl.HTTPAUTH_BASIC)
            elif request.auth_mode == "digest":
                curl.setopt(pycurl.HTTPAUTH, pycurl.HTTPAUTH_DIGEST)
            else:
                raise ValueError("Unsupported auth_mode %s" % request.auth_mode)

            userpwd = httputil.encode_username_password(
                request.auth_username, request.auth_password
            )
            curl.setopt(pycurl.USERPWD, userpwd)
            curl_log.debug(
                "%s %s (username: %r)",
                request.method,
                request.url,
                request.auth_username,
            )
        else:
            curl.unsetopt(pycurl.USERPWD)
            curl_log.debug("%s %s", request.method, request.url)

        if request.client_cert is not None:
            curl.setopt(pycurl.SSLCERT, request.client_cert)

        if request.client_key is not None:
            curl.setopt(pycurl.SSLKEY, request.client_key)

        if request.ssl_options is not None:
            raise ValueError("ssl_options not supported in curl_httpclient")

        if threading.active_count() > 1:
            # libcurl/pycurl is not thread-safe by default.  When multiple threads
            # are used, signals should be disabled.  This has the side effect
            # of disabling DNS timeouts in some environments (when libcurl is
            # not linked against ares), so we don't do it when there is only one
            # thread.  Applications that use many short-lived threads may need
            # to set NOSIGNAL manually in a prepare_curl_callback since
            # there may not be any other threads running at the time we call
            # threading.activeCount.
            curl.setopt(pycurl.NOSIGNAL, 1)
        if request.prepare_curl_callback is not None:
            request.prepare_curl_callback(curl)

    def _curl_header_callback(
        self,
        headers: httputil.HTTPHeaders,
        header_callback: Callable[[str], None],
        header_line_bytes: bytes,
    ) -> None:
        header_line = native_str(header_line_bytes.decode("latin1"))
        if header_callback is not None:
            self.io_loop.add_callback(header_callback, header_line)
        # header_line as returned by curl includes the end-of-line characters.
        # whitespace at the start should be preserved to allow multi-line headers
        header_line = header_line.rstrip()
        if header_line.startswith("HTTP/"):
            headers.clear()
            try:
                (_version, _code, reason) = httputil.parse_response_start_line(
                    header_line
                )
                header_line = "X-Http-Reason: %s" % reason
            except httputil.HTTPInputError:
                return
        if not header_line:
            return
        headers.parse_line(header_line)

    def _curl_debug(self, debug_type: int, debug_msg: str) -> None:
        debug_types = ("I", "<", ">", "<", ">")
        if debug_type == 0:
            debug_msg = native_str(debug_msg)
            curl_log.debug("%s", debug_msg.strip())
        elif debug_type in (1, 2):
            debug_msg = native_str(debug_msg)
            for line in debug_msg.splitlines():
                curl_log.debug("%s %s", debug_types[debug_type], line)
        elif debug_type == 4:
            curl_log.debug("%s %r", debug_types[debug_type], debug_msg)


class CurlError(HTTPError):
    def __init__(self, errno: int, message: str) -> None:
        HTTPError.__init__(self, 599, message)
        self.errno = errno


if __name__ == "__main__":
    AsyncHTTPClient.configure(CurlAsyncHTTPClient)
    main()

# === NexusCore/openenv\Lib\site-packages\trio\socket.py ===
from __future__ import annotations

# This is a public namespace, so we don't want to expose any non-underscored
# attributes that aren't actually part of our public API. But it's very
# annoying to carefully always use underscored names for module-level
# temporaries, imports, etc. when implementing the module. So we put the
# implementation in an underscored module, and then re-export the public parts
# here.
# We still have some underscore names though but only a few.
import socket as _stdlib_socket

# static checkers don't understand if importing this as _sys, so it's deleted later
import sys
import typing as _t

from . import _socket

_bad_symbols: set[str] = set()
if sys.platform == "win32":
    # See https://github.com/python-trio/trio/issues/39
    # Do not import for windows platform
    # (you can still get it from stdlib socket, of course, if you want it)
    _bad_symbols.add("SO_REUSEADDR")

# Dynamically re-export whatever constants this particular Python happens to
# have:
globals().update(
    {
        _name: getattr(_stdlib_socket, _name)
        for _name in _stdlib_socket.__all__
        if _name.isupper() and _name not in _bad_symbols
    },
)

# import the overwrites
from contextlib import suppress as _suppress

# Uses `from x import y as y` for compatibility with `pyright --verifytypes` (#2625)
from ._socket import (
    SocketType as SocketType,
    from_stdlib_socket as from_stdlib_socket,
    fromfd as fromfd,
    getaddrinfo as getaddrinfo,
    getnameinfo as getnameinfo,
    getprotobyname as getprotobyname,
    set_custom_hostname_resolver as set_custom_hostname_resolver,
    set_custom_socket_factory as set_custom_socket_factory,
    socket as socket,
    socketpair as socketpair,
)

# not always available so expose only if
if sys.platform == "win32" or not _t.TYPE_CHECKING:
    with _suppress(ImportError):
        from ._socket import fromshare as fromshare

# expose these functions to trio.socket
from socket import (
    gaierror as gaierror,
    gethostname as gethostname,
    herror as herror,
    htonl as htonl,
    htons as htons,
    inet_aton as inet_aton,
    inet_ntoa as inet_ntoa,
    inet_ntop as inet_ntop,
    inet_pton as inet_pton,
    ntohs as ntohs,
)

if sys.implementation.name == "cpython":
    from socket import (
        if_indextoname as if_indextoname,
        if_nametoindex as if_nametoindex,
    )

    # For android devices, if_nameindex support was introduced in API 24,
    # so it doesn't exist for any version prior.
    with _suppress(ImportError):
        from socket import (
            if_nameindex as if_nameindex,
        )


# not always available so expose only if
if sys.platform != "win32" or not _t.TYPE_CHECKING:
    with _suppress(ImportError):
        from socket import (
            sethostname as sethostname,
        )

if _t.TYPE_CHECKING:
    IP_BIND_ADDRESS_NO_PORT: int
else:
    try:
        IP_BIND_ADDRESS_NO_PORT  # noqa: B018  # "useless expression"
    except NameError:
        if sys.platform == "linux":
            IP_BIND_ADDRESS_NO_PORT = 24

del sys


# The socket module exports a bunch of platform-specific constants. We want to
# re-export them. Since the exact set of constants varies depending on Python
# version, platform, the libc installed on the system where Python was built,
# etc., we figure out which constants to re-export dynamically at runtime (see
# above). But that confuses static analysis tools like jedi and mypy. So this
# import statement statically lists every constant that *could* be
# exported. There's a test in test_exports.py to make sure that the list is
# kept up to date.
if _t.TYPE_CHECKING:
    from socket import (  # type: ignore[attr-defined]
        AF_ALG as AF_ALG,
        AF_APPLETALK as AF_APPLETALK,
        AF_ASH as AF_ASH,
        AF_ATMPVC as AF_ATMPVC,
        AF_ATMSVC as AF_ATMSVC,
        AF_AX25 as AF_AX25,
        AF_BLUETOOTH as AF_BLUETOOTH,
        AF_BRIDGE as AF_BRIDGE,
        AF_CAN as AF_CAN,
        AF_ECONET as AF_ECONET,
        AF_HYPERV as AF_HYPERV,
        AF_INET as AF_INET,
        AF_INET6 as AF_INET6,
        AF_IPX as AF_IPX,
        AF_IRDA as AF_IRDA,
        AF_KEY as AF_KEY,
        AF_LINK as AF_LINK,
        AF_LLC as AF_LLC,
        AF_NETBEUI as AF_NETBEUI,
        AF_NETLINK as AF_NETLINK,
        AF_NETROM as AF_NETROM,
        AF_PACKET as AF_PACKET,
        AF_PPPOX as AF_PPPOX,
        AF_QIPCRTR as AF_QIPCRTR,
        AF_RDS as AF_RDS,
        AF_ROSE as AF_ROSE,
        AF_ROUTE as AF_ROUTE,
        AF_SECURITY as AF_SECURITY,
        AF_SNA as AF_SNA,
        AF_SYSTEM as AF_SYSTEM,
        AF_TIPC as AF_TIPC,
        AF_UNIX as AF_UNIX,
        AF_UNSPEC as AF_UNSPEC,
        AF_VSOCK as AF_VSOCK,
        AF_WANPIPE as AF_WANPIPE,
        AF_X25 as AF_X25,
        AI_ADDRCONFIG as AI_ADDRCONFIG,
        AI_ALL as AI_ALL,
        AI_CANONNAME as AI_CANONNAME,
        AI_DEFAULT as AI_DEFAULT,
        AI_MASK as AI_MASK,
        AI_NUMERICHOST as AI_NUMERICHOST,
        AI_NUMERICSERV as AI_NUMERICSERV,
        AI_PASSIVE as AI_PASSIVE,
        AI_V4MAPPED as AI_V4MAPPED,
        AI_V4MAPPED_CFG as AI_V4MAPPED_CFG,
        ALG_OP_DECRYPT as ALG_OP_DECRYPT,
        ALG_OP_ENCRYPT as ALG_OP_ENCRYPT,
        ALG_OP_SIGN as ALG_OP_SIGN,
        ALG_OP_VERIFY as ALG_OP_VERIFY,
        ALG_SET_AEAD_ASSOCLEN as ALG_SET_AEAD_ASSOCLEN,
        ALG_SET_AEAD_AUTHSIZE as ALG_SET_AEAD_AUTHSIZE,
        ALG_SET_IV as ALG_SET_IV,
        ALG_SET_KEY as ALG_SET_KEY,
        ALG_SET_OP as ALG_SET_OP,
        ALG_SET_PUBKEY as ALG_SET_PUBKEY,
        BDADDR_ANY as BDADDR_ANY,
        BDADDR_LOCAL as BDADDR_LOCAL,
        BTPROTO_HCI as BTPROTO_HCI,
        BTPROTO_L2CAP as BTPROTO_L2CAP,
        BTPROTO_RFCOMM as BTPROTO_RFCOMM,
        BTPROTO_SCO as BTPROTO_SCO,
        CAN_BCM as CAN_BCM,
        CAN_BCM_CAN_FD_FRAME as CAN_BCM_CAN_FD_FRAME,
        CAN_BCM_RX_ANNOUNCE_RESUME as CAN_BCM_RX_ANNOUNCE_RESUME,
        CAN_BCM_RX_CHANGED as CAN_BCM_RX_CHANGED,
        CAN_BCM_RX_CHECK_DLC as CAN_BCM_RX_CHECK_DLC,
        CAN_BCM_RX_DELETE as CAN_BCM_RX_DELETE,
        CAN_BCM_RX_FILTER_ID as CAN_BCM_RX_FILTER_ID,
        CAN_BCM_RX_NO_AUTOTIMER as CAN_BCM_RX_NO_AUTOTIMER,
        CAN_BCM_RX_READ as CAN_BCM_RX_READ,
        CAN_BCM_RX_RTR_FRAME as CAN_BCM_RX_RTR_FRAME,
        CAN_BCM_RX_SETUP as CAN_BCM_RX_SETUP,
        CAN_BCM_RX_STATUS as CAN_BCM_RX_STATUS,
        CAN_BCM_RX_TIMEOUT as CAN_BCM_RX_TIMEOUT,
        CAN_BCM_SETTIMER as CAN_BCM_SETTIMER,
        CAN_BCM_STARTTIMER as CAN_BCM_STARTTIMER,
        CAN_BCM_TX_ANNOUNCE as CAN_BCM_TX_ANNOUNCE,
        CAN_BCM_TX_COUNTEVT as CAN_BCM_TX_COUNTEVT,
        CAN_BCM_TX_CP_CAN_ID as CAN_BCM_TX_CP_CAN_ID,
        CAN_BCM_TX_DELETE as CAN_BCM_TX_DELETE,
        CAN_BCM_TX_EXPIRED as CAN_BCM_TX_EXPIRED,
        CAN_BCM_TX_READ as CAN_BCM_TX_READ,
        CAN_BCM_TX_RESET_MULTI_IDX as CAN_BCM_TX_RESET_MULTI_IDX,
        CAN_BCM_TX_SEND as CAN_BCM_TX_SEND,
        CAN_BCM_TX_SETUP as CAN_BCM_TX_SETUP,
        CAN_BCM_TX_STATUS as CAN_BCM_TX_STATUS,
        CAN_EFF_FLAG as CAN_EFF_FLAG,
        CAN_EFF_MASK as CAN_EFF_MASK,
        CAN_ERR_FLAG as CAN_ERR_FLAG,
        CAN_ERR_MASK as CAN_ERR_MASK,
        CAN_ISOTP as CAN_ISOTP,
        CAN_J1939 as CAN_J1939,
        CAN_RAW as CAN_RAW,
        CAN_RAW_ERR_FILTER as CAN_RAW_ERR_FILTER,
        CAN_RAW_FD_FRAMES as CAN_RAW_FD_FRAMES,
        CAN_RAW_FILTER as CAN_RAW_FILTER,
        CAN_RAW_JOIN_FILTERS as CAN_RAW_JOIN_FILTERS,
        CAN_RAW_LOOPBACK as CAN_RAW_LOOPBACK,
        CAN_RAW_RECV_OWN_MSGS as CAN_RAW_RECV_OWN_MSGS,
        CAN_RTR_FLAG as CAN_RTR_FLAG,
        CAN_SFF_MASK as CAN_SFF_MASK,
        CAPI as CAPI,
        CMSG_LEN as CMSG_LEN,
        CMSG_SPACE as CMSG_SPACE,
        EAGAIN as EAGAIN,
        EAI_ADDRFAMILY as EAI_ADDRFAMILY,
        EAI_AGAIN as EAI_AGAIN,
        EAI_BADFLAGS as EAI_BADFLAGS,
        EAI_BADHINTS as EAI_BADHINTS,
        EAI_FAIL as EAI_FAIL,
        EAI_FAMILY as EAI_FAMILY,
        EAI_MAX as EAI_MAX,
        EAI_MEMORY as EAI_MEMORY,
        EAI_NODATA as EAI_NODATA,
        EAI_NONAME as EAI_NONAME,
        EAI_OVERFLOW as EAI_OVERFLOW,
        EAI_PROTOCOL as EAI_PROTOCOL,
        EAI_SERVICE as EAI_SERVICE,
        EAI_SOCKTYPE as EAI_SOCKTYPE,
        EAI_SYSTEM as EAI_SYSTEM,
        EBADF as EBADF,
        ETH_P_ALL as ETH_P_ALL,
        ETHERTYPE_ARP as ETHERTYPE_ARP,
        ETHERTYPE_IP as ETHERTYPE_IP,
        ETHERTYPE_IPV6 as ETHERTYPE_IPV6,
        ETHERTYPE_VLAN as ETHERTYPE_VLAN,
        EWOULDBLOCK as EWOULDBLOCK,
        FD_ACCEPT as FD_ACCEPT,
        FD_CLOSE as FD_CLOSE,
        FD_CLOSE_BIT as FD_CLOSE_BIT,
        FD_CONNECT as FD_CONNECT,
        FD_CONNECT_BIT as FD_CONNECT_BIT,
        FD_READ as FD_READ,
        FD_SETSIZE as FD_SETSIZE,
        FD_WRITE as FD_WRITE,
        HCI_DATA_DIR as HCI_DATA_DIR,
        HCI_FILTER as HCI_FILTER,
        HCI_TIME_STAMP as HCI_TIME_STAMP,
        HV_GUID_BROADCAST as HV_GUID_BROADCAST,
        HV_GUID_CHILDREN as HV_GUID_CHILDREN,
        HV_GUID_LOOPBACK as HV_GUID_LOOPBACK,
        HV_GUID_PARENT as HV_GUID_PARENT,
        HV_GUID_WILDCARD as HV_GUID_WILDCARD,
        HV_GUID_ZERO as HV_GUID_ZERO,
        HV_PROTOCOL_RAW as HV_PROTOCOL_RAW,
        HVSOCKET_ADDRESS_FLAG_PASSTHRU as HVSOCKET_ADDRESS_FLAG_PASSTHRU,
        HVSOCKET_CONNECT_TIMEOUT as HVSOCKET_CONNECT_TIMEOUT,
        HVSOCKET_CONNECT_TIMEOUT_MAX as HVSOCKET_CONNECT_TIMEOUT_MAX,
        HVSOCKET_CONNECTED_SUSPEND as HVSOCKET_CONNECTED_SUSPEND,
        INADDR_ALLHOSTS_GROUP as INADDR_ALLHOSTS_GROUP,
        INADDR_ANY as INADDR_ANY,
        INADDR_BROADCAST as INADDR_BROADCAST,
        INADDR_LOOPBACK as INADDR_LOOPBACK,
        INADDR_MAX_LOCAL_GROUP as INADDR_MAX_LOCAL_GROUP,
        INADDR_NONE as INADDR_NONE,
        INADDR_UNSPEC_GROUP as INADDR_UNSPEC_GROUP,
        INFINITE as INFINITE,
        IOCTL_VM_SOCKETS_GET_LOCAL_CID as IOCTL_VM_SOCKETS_GET_LOCAL_CID,
        IP_ADD_MEMBERSHIP as IP_ADD_MEMBERSHIP,
        IP_ADD_SOURCE_MEMBERSHIP as IP_ADD_SOURCE_MEMBERSHIP,
        IP_BLOCK_SOURCE as IP_BLOCK_SOURCE,
        IP_DEFAULT_MULTICAST_LOOP as IP_DEFAULT_MULTICAST_LOOP,
        IP_DEFAULT_MULTICAST_TTL as IP_DEFAULT_MULTICAST_TTL,
        IP_DROP_MEMBERSHIP as IP_DROP_MEMBERSHIP,
        IP_DROP_SOURCE_MEMBERSHIP as IP_DROP_SOURCE_MEMBERSHIP,
        IP_HDRINCL as IP_HDRINCL,
        IP_MAX_MEMBERSHIPS as IP_MAX_MEMBERSHIPS,
        IP_MULTICAST_IF as IP_MULTICAST_IF,
        IP_MULTICAST_LOOP as IP_MULTICAST_LOOP,
        IP_MULTICAST_TTL as IP_MULTICAST_TTL,
        IP_OPTIONS as IP_OPTIONS,
        IP_PKTINFO as IP_PKTINFO,
        IP_RECVDSTADDR as IP_RECVDSTADDR,
        IP_RECVOPTS as IP_RECVOPTS,
        IP_RECVRETOPTS as IP_RECVRETOPTS,
        IP_RECVTOS as IP_RECVTOS,
        IP_RETOPTS as IP_RETOPTS,
        IP_TOS as IP_TOS,
        IP_TRANSPARENT as IP_TRANSPARENT,
        IP_TTL as IP_TTL,
        IP_UNBLOCK_SOURCE as IP_UNBLOCK_SOURCE,
        IPPORT_RESERVED as IPPORT_RESERVED,
        IPPORT_USERRESERVED as IPPORT_USERRESERVED,
        IPPROTO_AH as IPPROTO_AH,
        IPPROTO_CBT as IPPROTO_CBT,
        IPPROTO_DSTOPTS as IPPROTO_DSTOPTS,
        IPPROTO_EGP as IPPROTO_EGP,
        IPPROTO_EON as IPPROTO_EON,
        IPPROTO_ESP as IPPROTO_ESP,
        IPPROTO_FRAGMENT as IPPROTO_FRAGMENT,
        IPPROTO_GGP as IPPROTO_GGP,
        IPPROTO_GRE as IPPROTO_GRE,
        IPPROTO_HELLO as IPPROTO_HELLO,
        IPPROTO_HOPOPTS as IPPROTO_HOPOPTS,
        IPPROTO_ICLFXBM as IPPROTO_ICLFXBM,
        IPPROTO_ICMP as IPPROTO_ICMP,
        IPPROTO_ICMPV6 as IPPROTO_ICMPV6,
        IPPROTO_IDP as IPPROTO_IDP,
        IPPROTO_IGMP as IPPROTO_IGMP,
        IPPROTO_IGP as IPPROTO_IGP,
        IPPROTO_IP as IPPROTO_IP,
        IPPROTO_IPCOMP as IPPROTO_IPCOMP,
        IPPROTO_IPIP as IPPROTO_IPIP,
        IPPROTO_IPV4 as IPPROTO_IPV4,
        IPPROTO_IPV6 as IPPROTO_IPV6,
        IPPROTO_L2TP as IPPROTO_L2TP,
        IPPROTO_MAX as IPPROTO_MAX,
        IPPROTO_MOBILE as IPPROTO_MOBILE,
        IPPROTO_MPTCP as IPPROTO_MPTCP,
        IPPROTO_ND as IPPROTO_ND,
        IPPROTO_NONE as IPPROTO_NONE,
        IPPROTO_PGM as IPPROTO_PGM,
        IPPROTO_PIM as IPPROTO_PIM,
        IPPROTO_PUP as IPPROTO_PUP,
        IPPROTO_RAW as IPPROTO_RAW,
        IPPROTO_RDP as IPPROTO_RDP,
        IPPROTO_ROUTING as IPPROTO_ROUTING,
        IPPROTO_RSVP as IPPROTO_RSVP,
        IPPROTO_SCTP as IPPROTO_SCTP,
        IPPROTO_ST as IPPROTO_ST,
        IPPROTO_TCP as IPPROTO_TCP,
        IPPROTO_TP as IPPROTO_TP,
        IPPROTO_UDP as IPPROTO_UDP,
        IPPROTO_UDPLITE as IPPROTO_UDPLITE,
        IPPROTO_XTP as IPPROTO_XTP,
        IPV6_CHECKSUM as IPV6_CHECKSUM,
        IPV6_DONTFRAG as IPV6_DONTFRAG,
        IPV6_DSTOPTS as IPV6_DSTOPTS,
        IPV6_HOPLIMIT as IPV6_HOPLIMIT,
        IPV6_HOPOPTS as IPV6_HOPOPTS,
        IPV6_JOIN_GROUP as IPV6_JOIN_GROUP,
        IPV6_LEAVE_GROUP as IPV6_LEAVE_GROUP,
        IPV6_MULTICAST_HOPS as IPV6_MULTICAST_HOPS,
        IPV6_MULTICAST_IF as IPV6_MULTICAST_IF,
        IPV6_MULTICAST_LOOP as IPV6_MULTICAST_LOOP,
        IPV6_NEXTHOP as IPV6_NEXTHOP,
        IPV6_PATHMTU as IPV6_PATHMTU,
        IPV6_PKTINFO as IPV6_PKTINFO,
        IPV6_RECVDSTOPTS as IPV6_RECVDSTOPTS,
        IPV6_RECVHOPLIMIT as IPV6_RECVHOPLIMIT,
        IPV6_RECVHOPOPTS as IPV6_RECVHOPOPTS,
        IPV6_RECVPATHMTU as IPV6_RECVPATHMTU,
        IPV6_RECVPKTINFO as IPV6_RECVPKTINFO,
        IPV6_RECVRTHDR as IPV6_RECVRTHDR,
        IPV6_RECVTCLASS as IPV6_RECVTCLASS,
        IPV6_RTHDR as IPV6_RTHDR,
        IPV6_RTHDR_TYPE_0 as IPV6_RTHDR_TYPE_0,
        IPV6_RTHDRDSTOPTS as IPV6_RTHDRDSTOPTS,
        IPV6_TCLASS as IPV6_TCLASS,
        IPV6_UNICAST_HOPS as IPV6_UNICAST_HOPS,
        IPV6_USE_MIN_MTU as IPV6_USE_MIN_MTU,
        IPV6_V6ONLY as IPV6_V6ONLY,
        J1939_EE_INFO_NONE as J1939_EE_INFO_NONE,
        J1939_EE_INFO_TX_ABORT as J1939_EE_INFO_TX_ABORT,
        J1939_FILTER_MAX as J1939_FILTER_MAX,
        J1939_IDLE_ADDR as J1939_IDLE_ADDR,
        J1939_MAX_UNICAST_ADDR as J1939_MAX_UNICAST_ADDR,
        J1939_NLA_BYTES_ACKED as J1939_NLA_BYTES_ACKED,
        J1939_NLA_PAD as J1939_NLA_PAD,
        J1939_NO_ADDR as J1939_NO_ADDR,
        J1939_NO_NAME as J1939_NO_NAME,
        J1939_NO_PGN as J1939_NO_PGN,
        J1939_PGN_ADDRESS_CLAIMED as J1939_PGN_ADDRESS_CLAIMED,
        J1939_PGN_ADDRESS_COMMANDED as J1939_PGN_ADDRESS_COMMANDED,
        J1939_PGN_MAX as J1939_PGN_MAX,
        J1939_PGN_PDU1_MAX as J1939_PGN_PDU1_MAX,
        J1939_PGN_REQUEST as J1939_PGN_REQUEST,
        LOCAL_PEERCRED as LOCAL_PEERCRED,
        MSG_BCAST as MSG_BCAST,
        MSG_CMSG_CLOEXEC as MSG_CMSG_CLOEXEC,
        MSG_CONFIRM as MSG_CONFIRM,
        MSG_CTRUNC as MSG_CTRUNC,
        MSG_DONTROUTE as MSG_DONTROUTE,
        MSG_DONTWAIT as MSG_DONTWAIT,
        MSG_EOF as MSG_EOF,
        MSG_EOR as MSG_EOR,
        MSG_ERRQUEUE as MSG_ERRQUEUE,
        MSG_FASTOPEN as MSG_FASTOPEN,
        MSG_MCAST as MSG_MCAST,
        MSG_MORE as MSG_MORE,
        MSG_NOSIGNAL as MSG_NOSIGNAL,
        MSG_NOTIFICATION as MSG_NOTIFICATION,
        MSG_OOB as MSG_OOB,
        MSG_PEEK as MSG_PEEK,
        MSG_TRUNC as MSG_TRUNC,
        MSG_WAITALL as MSG_WAITALL,
        NETLINK_CRYPTO as NETLINK_CRYPTO,
        NETLINK_DNRTMSG as NETLINK_DNRTMSG,
        NETLINK_FIREWALL as NETLINK_FIREWALL,
        NETLINK_IP6_FW as NETLINK_IP6_FW,
        NETLINK_NFLOG as NETLINK_NFLOG,
        NETLINK_ROUTE as NETLINK_ROUTE,
        NETLINK_USERSOCK as NETLINK_USERSOCK,
        NETLINK_XFRM as NETLINK_XFRM,
        NI_DGRAM as NI_DGRAM,
        NI_IDN as NI_IDN,
        NI_MAXHOST as NI_MAXHOST,
        NI_MAXSERV as NI_MAXSERV,
        NI_NAMEREQD as NI_NAMEREQD,
        NI_NOFQDN as NI_NOFQDN,
        NI_NUMERICHOST as NI_NUMERICHOST,
        NI_NUMERICSERV as NI_NUMERICSERV,
        PACKET_BROADCAST as PACKET_BROADCAST,
        PACKET_FASTROUTE as PACKET_FASTROUTE,
        PACKET_HOST as PACKET_HOST,
        PACKET_LOOPBACK as PACKET_LOOPBACK,
        PACKET_MULTICAST as PACKET_MULTICAST,
        PACKET_OTHERHOST as PACKET_OTHERHOST,
        PACKET_OUTGOING as PACKET_OUTGOING,
        PF_CAN as PF_CAN,
        PF_PACKET as PF_PACKET,
        PF_RDS as PF_RDS,
        PF_SYSTEM as PF_SYSTEM,
        POLLERR as POLLERR,
        POLLHUP as POLLHUP,
        POLLIN as POLLIN,
        POLLMSG as POLLMSG,
        POLLNVAL as POLLNVAL,
        POLLOUT as POLLOUT,
        POLLPRI as POLLPRI,
        POLLRDBAND as POLLRDBAND,
        POLLRDNORM as POLLRDNORM,
        POLLWRNORM as POLLWRNORM,
        RCVALL_MAX as RCVALL_MAX,
        RCVALL_OFF as RCVALL_OFF,
        RCVALL_ON as RCVALL_ON,
        RCVALL_SOCKETLEVELONLY as RCVALL_SOCKETLEVELONLY,
        SCM_CREDENTIALS as SCM_CREDENTIALS,
        SCM_CREDS as SCM_CREDS,
        SCM_J1939_DEST_ADDR as SCM_J1939_DEST_ADDR,
        SCM_J1939_DEST_NAME as SCM_J1939_DEST_NAME,
        SCM_J1939_ERRQUEUE as SCM_J1939_ERRQUEUE,
        SCM_J1939_PRIO as SCM_J1939_PRIO,
        SCM_RIGHTS as SCM_RIGHTS,
        SHUT_RD as SHUT_RD,
        SHUT_RDWR as SHUT_RDWR,
        SHUT_WR as SHUT_WR,
        SIO_KEEPALIVE_VALS as SIO_KEEPALIVE_VALS,
        SIO_LOOPBACK_FAST_PATH as SIO_LOOPBACK_FAST_PATH,
        SIO_RCVALL as SIO_RCVALL,
        SIOCGIFINDEX as SIOCGIFINDEX,
        SIOCGIFNAME as SIOCGIFNAME,
        SO_ACCEPTCONN as SO_ACCEPTCONN,
        SO_BINDTODEVICE as SO_BINDTODEVICE,
        SO_BINDTOIFINDEX as SO_BINDTOIFINDEX,
        SO_BROADCAST as SO_BROADCAST,
        SO_DEBUG as SO_DEBUG,
        SO_DOMAIN as SO_DOMAIN,
        SO_DONTROUTE as SO_DONTROUTE,
        SO_ERROR as SO_ERROR,
        SO_EXCLUSIVEADDRUSE as SO_EXCLUSIVEADDRUSE,
        SO_INCOMING_CPU as SO_INCOMING_CPU,
        SO_J1939_ERRQUEUE as SO_J1939_ERRQUEUE,
        SO_J1939_FILTER as SO_J1939_FILTER,
        SO_J1939_PROMISC as SO_J1939_PROMISC,
        SO_J1939_SEND_PRIO as SO_J1939_SEND_PRIO,
        SO_KEEPALIVE as SO_KEEPALIVE,
        SO_LINGER as SO_LINGER,
        SO_MARK as SO_MARK,
        SO_OOBINLINE as SO_OOBINLINE,
        SO_PASSCRED as SO_PASSCRED,
        SO_PASSSEC as SO_PASSSEC,
        SO_PEERCRED as SO_PEERCRED,
        SO_PEERSEC as SO_PEERSEC,
        SO_PRIORITY as SO_PRIORITY,
        SO_PROTOCOL as SO_PROTOCOL,
        SO_RCVBUF as SO_RCVBUF,
        SO_RCVLOWAT as SO_RCVLOWAT,
        SO_RCVTIMEO as SO_RCVTIMEO,
        SO_REUSEADDR as SO_REUSEADDR,
        SO_REUSEPORT as SO_REUSEPORT,
        SO_SETFIB as SO_SETFIB,
        SO_SNDBUF as SO_SNDBUF,
        SO_SNDLOWAT as SO_SNDLOWAT,
        SO_SNDTIMEO as SO_SNDTIMEO,
        SO_TYPE as SO_TYPE,
        SO_USELOOPBACK as SO_USELOOPBACK,
        SO_VM_SOCKETS_BUFFER_MAX_SIZE as SO_VM_SOCKETS_BUFFER_MAX_SIZE,
        SO_VM_SOCKETS_BUFFER_MIN_SIZE as SO_VM_SOCKETS_BUFFER_MIN_SIZE,
        SO_VM_SOCKETS_BUFFER_SIZE as SO_VM_SOCKETS_BUFFER_SIZE,
        SOCK_CLOEXEC as SOCK_CLOEXEC,
        SOCK_DGRAM as SOCK_DGRAM,
        SOCK_NONBLOCK as SOCK_NONBLOCK,
        SOCK_RAW as SOCK_RAW,
        SOCK_RDM as SOCK_RDM,
        SOCK_SEQPACKET as SOCK_SEQPACKET,
        SOCK_STREAM as SOCK_STREAM,
        SOL_ALG as SOL_ALG,
        SOL_CAN_BASE as SOL_CAN_BASE,
        SOL_CAN_RAW as SOL_CAN_RAW,
        SOL_HCI as SOL_HCI,
        SOL_IP as SOL_IP,
        SOL_RDS as SOL_RDS,
        SOL_SOCKET as SOL_SOCKET,
        SOL_TCP as SOL_TCP,
        SOL_TIPC as SOL_TIPC,
        SOL_UDP as SOL_UDP,
        SOMAXCONN as SOMAXCONN,
        SYSPROTO_CONTROL as SYSPROTO_CONTROL,
        TCP_CC_INFO as TCP_CC_INFO,
        TCP_CONGESTION as TCP_CONGESTION,
        TCP_CONNECTION_INFO as TCP_CONNECTION_INFO,
        TCP_CORK as TCP_CORK,
        TCP_DEFER_ACCEPT as TCP_DEFER_ACCEPT,
        TCP_FASTOPEN as TCP_FASTOPEN,
        TCP_FASTOPEN_CONNECT as TCP_FASTOPEN_CONNECT,
        TCP_FASTOPEN_KEY as TCP_FASTOPEN_KEY,
        TCP_FASTOPEN_NO_COOKIE as TCP_FASTOPEN_NO_COOKIE,
        TCP_INFO as TCP_INFO,
        TCP_INQ as TCP_INQ,
        TCP_KEEPALIVE as TCP_KEEPALIVE,
        TCP_KEEPCNT as TCP_KEEPCNT,
        TCP_KEEPIDLE as TCP_KEEPIDLE,
        TCP_KEEPINTVL as TCP_KEEPINTVL,
        TCP_LINGER2 as TCP_LINGER2,
        TCP_MAXSEG as TCP_MAXSEG,
        TCP_MD5SIG as TCP_MD5SIG,
        TCP_MD5SIG_EXT as TCP_MD5SIG_EXT,
        TCP_NODELAY as TCP_NODELAY,
        TCP_NOTSENT_LOWAT as TCP_NOTSENT_LOWAT,
        TCP_QUEUE_SEQ as TCP_QUEUE_SEQ,
        TCP_QUICKACK as TCP_QUICKACK,
        TCP_REPAIR as TCP_REPAIR,
        TCP_REPAIR_OPTIONS as TCP_REPAIR_OPTIONS,
        TCP_REPAIR_QUEUE as TCP_REPAIR_QUEUE,
        TCP_REPAIR_WINDOW as TCP_REPAIR_WINDOW,
        TCP_SAVE_SYN as TCP_SAVE_SYN,
        TCP_SAVED_SYN as TCP_SAVED_SYN,
        TCP_SYNCNT as TCP_SYNCNT,
        TCP_THIN_DUPACK as TCP_THIN_DUPACK,
        TCP_THIN_LINEAR_TIMEOUTS as TCP_THIN_LINEAR_TIMEOUTS,
        TCP_TIMESTAMP as TCP_TIMESTAMP,
        TCP_TX_DELAY as TCP_TX_DELAY,
        TCP_ULP as TCP_ULP,
        TCP_USER_TIMEOUT as TCP_USER_TIMEOUT,
        TCP_WINDOW_CLAMP as TCP_WINDOW_CLAMP,
        TCP_ZEROCOPY_RECEIVE as TCP_ZEROCOPY_RECEIVE,
        TIPC_ADDR_ID as TIPC_ADDR_ID,
        TIPC_ADDR_NAME as TIPC_ADDR_NAME,
        TIPC_ADDR_NAMESEQ as TIPC_ADDR_NAMESEQ,
        TIPC_CFG_SRV as TIPC_CFG_SRV,
        TIPC_CLUSTER_SCOPE as TIPC_CLUSTER_SCOPE,
        TIPC_CONN_TIMEOUT as TIPC_CONN_TIMEOUT,
        TIPC_CRITICAL_IMPORTANCE as TIPC_CRITICAL_IMPORTANCE,
        TIPC_DEST_DROPPABLE as TIPC_DEST_DROPPABLE,
        TIPC_HIGH_IMPORTANCE as TIPC_HIGH_IMPORTANCE,
        TIPC_IMPORTANCE as TIPC_IMPORTANCE,
        TIPC_LOW_IMPORTANCE as TIPC_LOW_IMPORTANCE,
        TIPC_MEDIUM_IMPORTANCE as TIPC_MEDIUM_IMPORTANCE,
        TIPC_NODE_SCOPE as TIPC_NODE_SCOPE,
        TIPC_PUBLISHED as TIPC_PUBLISHED,
        TIPC_SRC_DROPPABLE as TIPC_SRC_DROPPABLE,
        TIPC_SUB_CANCEL as TIPC_SUB_CANCEL,
        TIPC_SUB_PORTS as TIPC_SUB_PORTS,
        TIPC_SUB_SERVICE as TIPC_SUB_SERVICE,
        TIPC_SUBSCR_TIMEOUT as TIPC_SUBSCR_TIMEOUT,
        TIPC_TOP_SRV as TIPC_TOP_SRV,
        TIPC_WAIT_FOREVER as TIPC_WAIT_FOREVER,
        TIPC_WITHDRAWN as TIPC_WITHDRAWN,
        TIPC_ZONE_SCOPE as TIPC_ZONE_SCOPE,
        UDPLITE_RECV_CSCOV as UDPLITE_RECV_CSCOV,
        UDPLITE_SEND_CSCOV as UDPLITE_SEND_CSCOV,
        VM_SOCKETS_INVALID_VERSION as VM_SOCKETS_INVALID_VERSION,
        VMADDR_CID_ANY as VMADDR_CID_ANY,
        VMADDR_CID_HOST as VMADDR_CID_HOST,
        VMADDR_PORT_ANY as VMADDR_PORT_ANY,
        WSA_FLAG_OVERLAPPED as WSA_FLAG_OVERLAPPED,
        WSA_INVALID_HANDLE as WSA_INVALID_HANDLE,
        WSA_INVALID_PARAMETER as WSA_INVALID_PARAMETER,
        WSA_IO_INCOMPLETE as WSA_IO_INCOMPLETE,
        WSA_IO_PENDING as WSA_IO_PENDING,
        WSA_NOT_ENOUGH_MEMORY as WSA_NOT_ENOUGH_MEMORY,
        WSA_OPERATION_ABORTED as WSA_OPERATION_ABORTED,
        WSA_WAIT_FAILED as WSA_WAIT_FAILED,
        WSA_WAIT_TIMEOUT as WSA_WAIT_TIMEOUT,
    )

# === NexusCore/openenv\Lib\site-packages\litellm\router_strategy\lowest_latency.py ===
#### What this does ####
#   picks based on response time (for streaming, this is time to first token)
import random
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Union

import litellm
from litellm import ModelResponse, token_counter, verbose_logger
from litellm.caching.caching import DualCache
from litellm.integrations.custom_logger import CustomLogger
from litellm.litellm_core_utils.core_helpers import _get_parent_otel_span_from_kwargs
from litellm.types.utils import LiteLLMPydanticObjectBase

if TYPE_CHECKING:
    from opentelemetry.trace import Span as _Span

    Span = Union[_Span, Any]
else:
    Span = Any


class RoutingArgs(LiteLLMPydanticObjectBase):
    ttl: float = 1 * 60 * 60  # 1 hour
    lowest_latency_buffer: float = 0
    max_latency_list_size: int = 10


class LowestLatencyLoggingHandler(CustomLogger):
    test_flag: bool = False
    logged_success: int = 0
    logged_failure: int = 0

    def __init__(
        self, router_cache: DualCache, model_list: list, routing_args: dict = {}
    ):
        self.router_cache = router_cache
        self.model_list = model_list
        self.routing_args = RoutingArgs(**routing_args)

    def log_success_event(  # noqa: PLR0915
        self, kwargs, response_obj, start_time, end_time
    ):
        try:
            """
            Update latency usage on success
            """
            if kwargs["litellm_params"].get("metadata") is None:
                pass
            else:
                model_group = kwargs["litellm_params"]["metadata"].get(
                    "model_group", None
                )

                id = kwargs["litellm_params"].get("model_info", {}).get("id", None)
                if model_group is None or id is None:
                    return
                elif isinstance(id, int):
                    id = str(id)

                # ------------
                # Setup values
                # ------------
                """
                {
                    {model_group}_map: {
                        id: {
                            "latency": [..]
                            f"{date:hour:minute}" : {"tpm": 34, "rpm": 3}
                        }
                    }
                }
                """
                latency_key = f"{model_group}_map"

                current_date = datetime.now().strftime("%Y-%m-%d")
                current_hour = datetime.now().strftime("%H")
                current_minute = datetime.now().strftime("%M")
                precise_minute = f"{current_date}-{current_hour}-{current_minute}"

                response_ms: timedelta = end_time - start_time
                time_to_first_token_response_time: Optional[timedelta] = None

                if kwargs.get("stream", None) is not None and kwargs["stream"] is True:
                    # only log ttft for streaming request
                    time_to_first_token_response_time = (
                        kwargs.get("completion_start_time", end_time) - start_time
                    )

                final_value: Union[float, timedelta] = response_ms
                time_to_first_token: Optional[float] = None
                total_tokens = 0

                if isinstance(response_obj, ModelResponse):
                    _usage = getattr(response_obj, "usage", None)
                    if _usage is not None:
                        completion_tokens = _usage.completion_tokens
                        total_tokens = _usage.total_tokens
                        final_value = float(
                            response_ms.total_seconds() / completion_tokens
                        )

                        if time_to_first_token_response_time is not None:
                            time_to_first_token = float(
                                time_to_first_token_response_time.total_seconds()
                                / completion_tokens
                            )

                # ------------
                # Update usage
                # ------------
                parent_otel_span = _get_parent_otel_span_from_kwargs(kwargs)
                request_count_dict = (
                    self.router_cache.get_cache(
                        key=latency_key, parent_otel_span=parent_otel_span
                    )
                    or {}
                )

                if id not in request_count_dict:
                    request_count_dict[id] = {}

                ## Latency
                if (
                    len(request_count_dict[id].get("latency", []))
                    < self.routing_args.max_latency_list_size
                ):
                    request_count_dict[id].setdefault("latency", []).append(final_value)
                else:
                    request_count_dict[id]["latency"] = request_count_dict[id][
                        "latency"
                    ][: self.routing_args.max_latency_list_size - 1] + [final_value]

                ## Time to first token
                if time_to_first_token is not None:
                    if (
                        len(request_count_dict[id].get("time_to_first_token", []))
                        < self.routing_args.max_latency_list_size
                    ):
                        request_count_dict[id].setdefault(
                            "time_to_first_token", []
                        ).append(time_to_first_token)
                    else:
                        request_count_dict[id][
                            "time_to_first_token"
                        ] = request_count_dict[id]["time_to_first_token"][
                            : self.routing_args.max_latency_list_size - 1
                        ] + [
                            time_to_first_token
                        ]

                if precise_minute not in request_count_dict[id]:
                    request_count_dict[id][precise_minute] = {}

                ## TPM
                request_count_dict[id][precise_minute]["tpm"] = (
                    request_count_dict[id][precise_minute].get("tpm", 0) + total_tokens
                )

                ## RPM
                request_count_dict[id][precise_minute]["rpm"] = (
                    request_count_dict[id][precise_minute].get("rpm", 0) + 1
                )

                self.router_cache.set_cache(
                    key=latency_key, value=request_count_dict, ttl=self.routing_args.ttl
                )  # reset map within window

                ### TESTING ###
                if self.test_flag:
                    self.logged_success += 1
        except Exception as e:
            verbose_logger.exception(
                "litellm.proxy.hooks.prompt_injection_detection.py::async_pre_call_hook(): Exception occured - {}".format(
                    str(e)
                )
            )
            pass

    async def async_log_failure_event(self, kwargs, response_obj, start_time, end_time):
        """
        Check if Timeout Error, if timeout set deployment latency -> 100
        """
        try:
            _exception = kwargs.get("exception", None)
            if isinstance(_exception, litellm.Timeout):
                if kwargs["litellm_params"].get("metadata") is None:
                    pass
                else:
                    model_group = kwargs["litellm_params"]["metadata"].get(
                        "model_group", None
                    )

                    id = kwargs["litellm_params"].get("model_info", {}).get("id", None)
                    if model_group is None or id is None:
                        return
                    elif isinstance(id, int):
                        id = str(id)

                    # ------------
                    # Setup values
                    # ------------
                    """
                    {
                        {model_group}_map: {
                            id: {
                                "latency": [..]
                                f"{date:hour:minute}" : {"tpm": 34, "rpm": 3}
                            }
                        }
                    }
                    """
                    latency_key = f"{model_group}_map"
                    request_count_dict = (
                        await self.router_cache.async_get_cache(key=latency_key) or {}
                    )

                    if id not in request_count_dict:
                        request_count_dict[id] = {}

                    ## Latency - give 1000s penalty for failing
                    if (
                        len(request_count_dict[id].get("latency", []))
                        < self.routing_args.max_latency_list_size
                    ):
                        request_count_dict[id].setdefault("latency", []).append(1000.0)
                    else:
                        request_count_dict[id]["latency"] = request_count_dict[id][
                            "latency"
                        ][: self.routing_args.max_latency_list_size - 1] + [1000.0]

                    await self.router_cache.async_set_cache(
                        key=latency_key,
                        value=request_count_dict,
                        ttl=self.routing_args.ttl,
                    )  # reset map within window
            else:
                # do nothing if it's not a timeout error
                return
        except Exception as e:
            verbose_logger.exception(
                "litellm.proxy.hooks.prompt_injection_detection.py::async_pre_call_hook(): Exception occured - {}".format(
                    str(e)
                )
            )
            pass

    async def async_log_success_event(  # noqa: PLR0915
        self, kwargs, response_obj, start_time, end_time
    ):
        try:
            """
            Update latency usage on success
            """
            if kwargs["litellm_params"].get("metadata") is None:
                pass
            else:
                model_group = kwargs["litellm_params"]["metadata"].get(
                    "model_group", None
                )

                id = kwargs["litellm_params"].get("model_info", {}).get("id", None)
                if model_group is None or id is None:
                    return
                elif isinstance(id, int):
                    id = str(id)

                # ------------
                # Setup values
                # ------------
                """
                {
                    {model_group}_map: {
                        id: {
                            "latency": [..]
                            "time_to_first_token": [..]
                            f"{date:hour:minute}" : {"tpm": 34, "rpm": 3}
                        }
                    }
                }
                """
                latency_key = f"{model_group}_map"

                current_date = datetime.now().strftime("%Y-%m-%d")
                current_hour = datetime.now().strftime("%H")
                current_minute = datetime.now().strftime("%M")
                precise_minute = f"{current_date}-{current_hour}-{current_minute}"

                response_ms: timedelta = end_time - start_time
                time_to_first_token_response_time: Optional[timedelta] = None
                if kwargs.get("stream", None) is not None and kwargs["stream"] is True:
                    # only log ttft for streaming request
                    time_to_first_token_response_time = (
                        kwargs.get("completion_start_time", end_time) - start_time
                    )

                final_value: Union[float, timedelta] = response_ms
                total_tokens = 0
                time_to_first_token: Optional[float] = None

                if isinstance(response_obj, ModelResponse):
                    _usage = getattr(response_obj, "usage", None)
                    if _usage is not None:
                        completion_tokens = _usage.completion_tokens
                        total_tokens = _usage.total_tokens
                        final_value = float(
                            response_ms.total_seconds() / completion_tokens
                        )

                        if time_to_first_token_response_time is not None:
                            time_to_first_token = float(
                                time_to_first_token_response_time.total_seconds()
                                / completion_tokens
                            )
                # ------------
                # Update usage
                # ------------
                parent_otel_span = _get_parent_otel_span_from_kwargs(kwargs)
                request_count_dict = (
                    await self.router_cache.async_get_cache(
                        key=latency_key,
                        parent_otel_span=parent_otel_span,
                        local_only=True,
                    )
                    or {}
                )

                if id not in request_count_dict:
                    request_count_dict[id] = {}

                ## Latency
                if (
                    len(request_count_dict[id].get("latency", []))
                    < self.routing_args.max_latency_list_size
                ):
                    request_count_dict[id].setdefault("latency", []).append(final_value)
                else:
                    request_count_dict[id]["latency"] = request_count_dict[id][
                        "latency"
                    ][: self.routing_args.max_latency_list_size - 1] + [final_value]

                ## Time to first token
                if time_to_first_token is not None:
                    if (
                        len(request_count_dict[id].get("time_to_first_token", []))
                        < self.routing_args.max_latency_list_size
                    ):
                        request_count_dict[id].setdefault(
                            "time_to_first_token", []
                        ).append(time_to_first_token)
                    else:
                        request_count_dict[id][
                            "time_to_first_token"
                        ] = request_count_dict[id]["time_to_first_token"][
                            : self.routing_args.max_latency_list_size - 1
                        ] + [
                            time_to_first_token
                        ]

                if precise_minute not in request_count_dict[id]:
                    request_count_dict[id][precise_minute] = {}

                ## TPM
                request_count_dict[id][precise_minute]["tpm"] = (
                    request_count_dict[id][precise_minute].get("tpm", 0) + total_tokens
                )

                ## RPM
                request_count_dict[id][precise_minute]["rpm"] = (
                    request_count_dict[id][precise_minute].get("rpm", 0) + 1
                )

                await self.router_cache.async_set_cache(
                    key=latency_key, value=request_count_dict, ttl=self.routing_args.ttl
                )  # reset map within window

                ### TESTING ###
                if self.test_flag:
                    self.logged_success += 1
        except Exception as e:
            verbose_logger.exception(
                "litellm.router_strategy.lowest_latency.py::async_log_success_event(): Exception occured - {}".format(
                    str(e)
                )
            )
            pass

    def _get_available_deployments(  # noqa: PLR0915
        self,
        model_group: str,
        healthy_deployments: list,
        messages: Optional[List[Dict[str, str]]] = None,
        input: Optional[Union[str, List]] = None,
        request_kwargs: Optional[Dict] = None,
        request_count_dict: Optional[Dict] = None,
    ):
        """Common logic for both sync and async get_available_deployments"""

        # -----------------------
        # Find lowest used model
        # ----------------------
        _latency_per_deployment = {}
        lowest_latency = float("inf")

        current_date = datetime.now().strftime("%Y-%m-%d")
        current_hour = datetime.now().strftime("%H")
        current_minute = datetime.now().strftime("%M")
        precise_minute = f"{current_date}-{current_hour}-{current_minute}"

        deployment = None

        if request_count_dict is None:  # base case
            return

        all_deployments = request_count_dict
        for d in healthy_deployments:
            ## if healthy deployment not yet used
            if d["model_info"]["id"] not in all_deployments:
                all_deployments[d["model_info"]["id"]] = {
                    "latency": [0],
                    precise_minute: {"tpm": 0, "rpm": 0},
                }

        try:
            input_tokens = token_counter(messages=messages, text=input)
        except Exception:
            input_tokens = 0

        # randomly sample from all_deployments, incase all deployments have latency=0.0
        _items = all_deployments.items()

        _all_deployments = random.sample(list(_items), len(_items))
        all_deployments = dict(_all_deployments)
        ### GET AVAILABLE DEPLOYMENTS ### filter out any deployments > tpm/rpm limits

        potential_deployments = []
        for item, item_map in all_deployments.items():
            ## get the item from model list
            _deployment = None
            for m in healthy_deployments:
                if item == m["model_info"]["id"]:
                    _deployment = m

            if _deployment is None:
                continue  # skip to next one

            _deployment_tpm = (
                _deployment.get("tpm", None)
                or _deployment.get("litellm_params", {}).get("tpm", None)
                or _deployment.get("model_info", {}).get("tpm", None)
                or float("inf")
            )

            _deployment_rpm = (
                _deployment.get("rpm", None)
                or _deployment.get("litellm_params", {}).get("rpm", None)
                or _deployment.get("model_info", {}).get("rpm", None)
                or float("inf")
            )
            item_latency = item_map.get("latency", [])
            item_ttft_latency = item_map.get("time_to_first_token", [])
            item_rpm = item_map.get(precise_minute, {}).get("rpm", 0)
            item_tpm = item_map.get(precise_minute, {}).get("tpm", 0)

            # get average latency or average ttft (depending on streaming/non-streaming)
            total: float = 0.0
            if (
                request_kwargs is not None
                and request_kwargs.get("stream", None) is not None
                and request_kwargs["stream"] is True
                and len(item_ttft_latency) > 0
            ):
                for _call_latency in item_ttft_latency:
                    if isinstance(_call_latency, float):
                        total += _call_latency
            else:
                for _call_latency in item_latency:
                    if isinstance(_call_latency, float):
                        total += _call_latency
            item_latency = total / len(item_latency)

            # -------------- #
            # Debugging Logic
            # -------------- #
            # We use _latency_per_deployment to log to langfuse, slack - this is not used to make a decision on routing
            # this helps a user to debug why the router picked a specfic deployment      #
            _deployment_api_base = _deployment.get("litellm_params", {}).get(
                "api_base", ""
            )
            if _deployment_api_base is not None:
                _latency_per_deployment[_deployment_api_base] = item_latency
            # -------------- #
            # End of Debugging Logic
            # -------------- #

            if (
                item_tpm + input_tokens > _deployment_tpm
                or item_rpm + 1 > _deployment_rpm
            ):  # if user passed in tpm / rpm in the model_list
                continue
            else:
                potential_deployments.append((_deployment, item_latency))

        if len(potential_deployments) == 0:
            return None

        # Sort potential deployments by latency
        sorted_deployments = sorted(potential_deployments, key=lambda x: x[1])

        # Find lowest latency deployment
        lowest_latency = sorted_deployments[0][1]

        # Find deployments within buffer of lowest latency
        buffer = self.routing_args.lowest_latency_buffer * lowest_latency

        valid_deployments = [
            x for x in sorted_deployments if x[1] <= lowest_latency + buffer
        ]

        # Pick a random deployment from valid deployments
        random_valid_deployment = random.choice(valid_deployments)
        deployment = random_valid_deployment[0]

        if request_kwargs is not None and "metadata" in request_kwargs:
            request_kwargs["metadata"][
                "_latency_per_deployment"
            ] = _latency_per_deployment
        return deployment

    async def async_get_available_deployments(
        self,
        model_group: str,
        healthy_deployments: list,
        messages: Optional[List[Dict[str, str]]] = None,
        input: Optional[Union[str, List]] = None,
        request_kwargs: Optional[Dict] = None,
    ):
        # get list of potential deployments
        latency_key = f"{model_group}_map"

        parent_otel_span: Optional[Span] = _get_parent_otel_span_from_kwargs(
            request_kwargs
        )
        request_count_dict = (
            await self.router_cache.async_get_cache(
                key=latency_key, parent_otel_span=parent_otel_span
            )
            or {}
        )

        return self._get_available_deployments(
            model_group,
            healthy_deployments,
            messages,
            input,
            request_kwargs,
            request_count_dict,
        )

    def get_available_deployments(
        self,
        model_group: str,
        healthy_deployments: list,
        messages: Optional[List[Dict[str, str]]] = None,
        input: Optional[Union[str, List]] = None,
        request_kwargs: Optional[Dict] = None,
    ):
        """
        Returns a deployment with the lowest latency
        """
        # get list of potential deployments
        latency_key = f"{model_group}_map"

        parent_otel_span: Optional[Span] = _get_parent_otel_span_from_kwargs(
            request_kwargs
        )
        request_count_dict = (
            self.router_cache.get_cache(
                key=latency_key, parent_otel_span=parent_otel_span
            )
            or {}
        )

        return self._get_available_deployments(
            model_group,
            healthy_deployments,
            messages,
            input,
            request_kwargs,
            request_count_dict,
        )

# === NexusCore/openenv\Lib\site-packages\litellm\llms\huggingface\embedding\transformation.py ===
import json
import os
import time
from copy import deepcopy
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple, Union

import httpx

import litellm
from litellm.litellm_core_utils.prompt_templates.common_utils import (
    convert_content_list_to_str,
)
from litellm.litellm_core_utils.prompt_templates.factory import (
    custom_prompt,
    prompt_factory,
)
from litellm.litellm_core_utils.streaming_handler import CustomStreamWrapper
from litellm.llms.base_llm.chat.transformation import BaseConfig, BaseLLMException
from litellm.secret_managers.main import get_secret_str
from litellm.types.llms.openai import AllMessageValues
from litellm.types.utils import Choices, Message, ModelResponse, Usage
from litellm.utils import token_counter

from ..common_utils import HuggingFaceError, hf_task_list, hf_tasks, output_parser

if TYPE_CHECKING:
    from litellm.litellm_core_utils.litellm_logging import Logging as LiteLLMLoggingObj

    LoggingClass = LiteLLMLoggingObj
else:
    LoggingClass = Any


tgi_models_cache = None
conv_models_cache = None


class HuggingFaceEmbeddingConfig(BaseConfig):
    """
    Reference: https://huggingface.github.io/text-generation-inference/#/Text%20Generation%20Inference/compat_generate
    """

    hf_task: Optional[
        hf_tasks
    ] = None  # litellm-specific param, used to know the api spec to use when calling huggingface api
    best_of: Optional[int] = None
    decoder_input_details: Optional[bool] = None
    details: Optional[bool] = True  # enables returning logprobs + best of
    max_new_tokens: Optional[int] = None
    repetition_penalty: Optional[float] = None
    return_full_text: Optional[
        bool
    ] = False  # by default don't return the input as part of the output
    seed: Optional[int] = None
    temperature: Optional[float] = None
    top_k: Optional[int] = None
    top_n_tokens: Optional[int] = None
    top_p: Optional[int] = None
    truncate: Optional[int] = None
    typical_p: Optional[float] = None
    watermark: Optional[bool] = None

    def __init__(
        self,
        best_of: Optional[int] = None,
        decoder_input_details: Optional[bool] = None,
        details: Optional[bool] = None,
        max_new_tokens: Optional[int] = None,
        repetition_penalty: Optional[float] = None,
        return_full_text: Optional[bool] = None,
        seed: Optional[int] = None,
        temperature: Optional[float] = None,
        top_k: Optional[int] = None,
        top_n_tokens: Optional[int] = None,
        top_p: Optional[int] = None,
        truncate: Optional[int] = None,
        typical_p: Optional[float] = None,
        watermark: Optional[bool] = None,
    ) -> None:
        locals_ = locals().copy()
        for key, value in locals_.items():
            if key != "self" and value is not None:
                setattr(self.__class__, key, value)

    @classmethod
    def get_config(cls):
        return super().get_config()

    def get_special_options_params(self):
        return ["use_cache", "wait_for_model"]

    def get_supported_openai_params(self, model: str):
        return [
            "stream",
            "temperature",
            "max_tokens",
            "max_completion_tokens",
            "top_p",
            "stop",
            "n",
            "echo",
        ]

    def map_openai_params(
        self,
        non_default_params: Dict,
        optional_params: Dict,
        model: str,
        drop_params: bool,
    ) -> Dict:
        for param, value in non_default_params.items():
            # temperature, top_p, n, stream, stop, max_tokens, n, presence_penalty default to None
            if param == "temperature":
                if value == 0.0 or value == 0:
                    # hugging face exception raised when temp==0
                    # Failed: Error occurred: HuggingfaceException - Input validation error: `temperature` must be strictly positive
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
            if param == "max_tokens" or param == "max_completion_tokens":
                # HF TGI raises the following exception when max_new_tokens==0
                # Failed: Error occurred: HuggingfaceException - Input validation error: `max_new_tokens` must be strictly positive
                if value == 0:
                    value = 1
                optional_params["max_new_tokens"] = value
            if param == "echo":
                # https://huggingface.co/docs/huggingface_hub/main/en/package_reference/inference_client#huggingface_hub.InferenceClient.text_generation.decoder_input_details
                #  Return the decoder input token logprobs and ids. You must set details=True as well for it to be taken into account. Defaults to False
                optional_params["decoder_input_details"] = True

        return optional_params

    def get_hf_api_key(self) -> Optional[str]:
        return get_secret_str("HUGGINGFACE_API_KEY")

    def read_tgi_conv_models(self):
        try:
            global tgi_models_cache, conv_models_cache
            # Check if the cache is already populated
            # so we don't keep on reading txt file if there are 1k requests
            if (tgi_models_cache is not None) and (conv_models_cache is not None):
                return tgi_models_cache, conv_models_cache
            # If not, read the file and populate the cache
            tgi_models = set()
            script_directory = os.path.dirname(os.path.abspath(__file__))
            script_directory = os.path.dirname(script_directory)
            # Construct the file path relative to the script's directory
            file_path = os.path.join(
                script_directory,
                "huggingface_llms_metadata",
                "hf_text_generation_models.txt",
            )

            with open(file_path, "r") as file:
                for line in file:
                    tgi_models.add(line.strip())

            # Cache the set for future use
            tgi_models_cache = tgi_models

            # If not, read the file and populate the cache
            file_path = os.path.join(
                script_directory,
                "huggingface_llms_metadata",
                "hf_conversational_models.txt",
            )
            conv_models = set()
            with open(file_path, "r") as file:
                for line in file:
                    conv_models.add(line.strip())
            # Cache the set for future use
            conv_models_cache = conv_models
            return tgi_models, conv_models
        except Exception:
            return set(), set()

    def get_hf_task_for_model(self, model: str) -> Tuple[hf_tasks, str]:
        # read text file, cast it to set
        # read the file called "huggingface_llms_metadata/hf_text_generation_models.txt"
        if model.split("/")[0] in hf_task_list:
            split_model = model.split("/", 1)
            return split_model[0], split_model[1]  # type: ignore
        tgi_models, conversational_models = self.read_tgi_conv_models()

        if model in tgi_models:
            return "text-generation-inference", model
        elif model in conversational_models:
            return "conversational", model
        elif "roneneldan/TinyStories" in model:
            return "text-generation", model
        else:
            return "text-generation-inference", model  # default to tgi

    def transform_request(
        self,
        model: str,
        messages: List[AllMessageValues],
        optional_params: dict,
        litellm_params: dict,
        headers: dict,
    ) -> dict:
        task = litellm_params.get("task", None)
        ## VALIDATE API FORMAT
        if task is None or not isinstance(task, str) or task not in hf_task_list:
            raise Exception(
                "Invalid hf task - {}. Valid formats - {}.".format(task, hf_tasks)
            )

        ## Load Config
        config = litellm.HuggingFaceEmbeddingConfig.get_config()
        for k, v in config.items():
            if (
                k not in optional_params
            ):  # completion(top_k=3) > huggingfaceConfig(top_k=3) <- allows for dynamic variables to be passed in
                optional_params[k] = v

        ### MAP INPUT PARAMS
        #### HANDLE SPECIAL PARAMS
        special_params = self.get_special_options_params()
        special_params_dict = {}
        # Create a list of keys to pop after iteration
        keys_to_pop = []

        for k, v in optional_params.items():
            if k in special_params:
                special_params_dict[k] = v
                keys_to_pop.append(k)

        # Pop the keys from the dictionary after iteration
        for k in keys_to_pop:
            optional_params.pop(k)
        if task == "conversational":
            inference_params = deepcopy(optional_params)
            inference_params.pop("details")
            inference_params.pop("return_full_text")
            past_user_inputs = []
            generated_responses = []
            text = ""
            for message in messages:
                if message["role"] == "user":
                    if text != "":
                        past_user_inputs.append(text)
                    text = convert_content_list_to_str(message)
                elif message["role"] == "assistant" or message["role"] == "system":
                    generated_responses.append(convert_content_list_to_str(message))
            data = {
                "inputs": {
                    "text": text,
                    "past_user_inputs": past_user_inputs,
                    "generated_responses": generated_responses,
                },
                "parameters": inference_params,
            }

        elif task == "text-generation-inference":
            # always send "details" and "return_full_text" as params
            if model in litellm.custom_prompt_dict:
                # check if the model has a registered custom prompt
                model_prompt_details = litellm.custom_prompt_dict[model]
                prompt = custom_prompt(
                    role_dict=model_prompt_details.get("roles", None),
                    initial_prompt_value=model_prompt_details.get(
                        "initial_prompt_value", ""
                    ),
                    final_prompt_value=model_prompt_details.get(
                        "final_prompt_value", ""
                    ),
                    messages=messages,
                )
            else:
                prompt = prompt_factory(model=model, messages=messages)
            data = {
                "inputs": prompt,  # type: ignore
                "parameters": optional_params,
                "stream": (  # type: ignore
                    True
                    if "stream" in optional_params
                    and isinstance(optional_params["stream"], bool)
                    and optional_params["stream"] is True  # type: ignore
                    else False
                ),
            }
        else:
            # Non TGI and Conversational llms
            # We need this branch, it removes 'details' and 'return_full_text' from params
            if model in litellm.custom_prompt_dict:
                # check if the model has a registered custom prompt
                model_prompt_details = litellm.custom_prompt_dict[model]
                prompt = custom_prompt(
                    role_dict=model_prompt_details.get("roles", {}),
                    initial_prompt_value=model_prompt_details.get(
                        "initial_prompt_value", ""
                    ),
                    final_prompt_value=model_prompt_details.get(
                        "final_prompt_value", ""
                    ),
                    bos_token=model_prompt_details.get("bos_token", ""),
                    eos_token=model_prompt_details.get("eos_token", ""),
                    messages=messages,
                )
            else:
                prompt = prompt_factory(model=model, messages=messages)
            inference_params = deepcopy(optional_params)
            inference_params.pop("details")
            inference_params.pop("return_full_text")
            data = {
                "inputs": prompt,  # type: ignore
            }
            if task == "text-generation-inference":
                data["parameters"] = inference_params
                data["stream"] = (  # type: ignore
                    True  # type: ignore
                    if "stream" in optional_params and optional_params["stream"] is True
                    else False
                )

        ### RE-ADD SPECIAL PARAMS
        if len(special_params_dict.keys()) > 0:
            data.update({"options": special_params_dict})

        return data

    def get_api_base(self, api_base: Optional[str], model: str) -> str:
        """
        Get the API base for the Huggingface API.

        Do not add the chat/embedding/rerank extension here. Let the handler do this.
        """
        if "https" in model:
            completion_url = model
        elif api_base is not None:
            completion_url = api_base
        elif "HF_API_BASE" in os.environ:
            completion_url = os.getenv("HF_API_BASE", "")
        elif "HUGGINGFACE_API_BASE" in os.environ:
            completion_url = os.getenv("HUGGINGFACE_API_BASE", "")
        else:
            completion_url = f"https://api-inference.huggingface.co/models/{model}"

        return completion_url

    def validate_environment(
        self,
        headers: Dict,
        model: str,
        messages: List[AllMessageValues],
        optional_params: Dict,
        litellm_params: dict,
        api_key: Optional[str] = None,
        api_base: Optional[str] = None,
    ) -> Dict:
        default_headers = {
            "content-type": "application/json",
        }
        if api_key is not None:
            default_headers[
                "Authorization"
            ] = f"Bearer {api_key}"  # Huggingface Inference Endpoint default is to accept bearer tokens

        headers = {**headers, **default_headers}
        return headers

    def get_error_class(
        self, error_message: str, status_code: int, headers: Union[dict, httpx.Headers]
    ) -> BaseLLMException:
        return HuggingFaceError(
            status_code=status_code, message=error_message, headers=headers
        )

    def _convert_streamed_response_to_complete_response(
        self,
        response: httpx.Response,
        logging_obj: LoggingClass,
        model: str,
        data: dict,
        api_key: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        streamed_response = CustomStreamWrapper(
            completion_stream=response.iter_lines(),
            model=model,
            custom_llm_provider="huggingface",
            logging_obj=logging_obj,
        )
        content = ""
        for chunk in streamed_response:
            content += chunk["choices"][0]["delta"]["content"]
        completion_response: List[Dict[str, Any]] = [{"generated_text": content}]
        ## LOGGING
        logging_obj.post_call(
            input=data,
            api_key=api_key,
            original_response=completion_response,
            additional_args={"complete_input_dict": data},
        )
        return completion_response

    def convert_to_model_response_object(  # noqa: PLR0915
        self,
        completion_response: Union[List[Dict[str, Any]], Dict[str, Any]],
        model_response: ModelResponse,
        task: Optional[hf_tasks],
        optional_params: dict,
        encoding: Any,
        messages: List[AllMessageValues],
        model: str,
    ):
        if task is None:
            task = "text-generation-inference"  # default to tgi

        if task == "conversational":
            if len(completion_response["generated_text"]) > 0:  # type: ignore
                model_response.choices[0].message.content = completion_response[  # type: ignore
                    "generated_text"
                ]
        elif task == "text-generation-inference":
            if (
                not isinstance(completion_response, list)
                or not isinstance(completion_response[0], dict)
                or "generated_text" not in completion_response[0]
            ):
                raise HuggingFaceError(
                    status_code=422,
                    message=f"response is not in expected format - {completion_response}",
                    headers=None,
                )

            if len(completion_response[0]["generated_text"]) > 0:
                model_response.choices[0].message.content = output_parser(  # type: ignore
                    completion_response[0]["generated_text"]
                )
            ## GETTING LOGPROBS + FINISH REASON
            if (
                "details" in completion_response[0]
                and "tokens" in completion_response[0]["details"]
            ):
                model_response.choices[0].finish_reason = completion_response[0][
                    "details"
                ]["finish_reason"]
                sum_logprob = 0
                for token in completion_response[0]["details"]["tokens"]:
                    if token["logprob"] is not None:
                        sum_logprob += token["logprob"]
                setattr(model_response.choices[0].message, "_logprob", sum_logprob)  # type: ignore
            if "best_of" in optional_params and optional_params["best_of"] > 1:
                if (
                    "details" in completion_response[0]
                    and "best_of_sequences" in completion_response[0]["details"]
                ):
                    choices_list = []
                    for idx, item in enumerate(
                        completion_response[0]["details"]["best_of_sequences"]
                    ):
                        sum_logprob = 0
                        for token in item["tokens"]:
                            if token["logprob"] is not None:
                                sum_logprob += token["logprob"]
                        if len(item["generated_text"]) > 0:
                            message_obj = Message(
                                content=output_parser(item["generated_text"]),
                                logprobs=sum_logprob,
                            )
                        else:
                            message_obj = Message(content=None)
                        choice_obj = Choices(
                            finish_reason=item["finish_reason"],
                            index=idx + 1,
                            message=message_obj,
                        )
                        choices_list.append(choice_obj)
                    model_response.choices.extend(choices_list)
        elif task == "text-classification":
            model_response.choices[0].message.content = json.dumps(  # type: ignore
                completion_response
            )
        else:
            if (
                isinstance(completion_response, list)
                and len(completion_response[0]["generated_text"]) > 0
            ):
                model_response.choices[0].message.content = output_parser(  # type: ignore
                    completion_response[0]["generated_text"]
                )
        ## CALCULATING USAGE
        prompt_tokens = 0
        try:
            prompt_tokens = token_counter(model=model, messages=messages)
        except Exception:
            # this should remain non blocking we should not block a response returning if calculating usage fails
            pass
        output_text = model_response["choices"][0]["message"].get("content", "")
        if output_text is not None and len(output_text) > 0:
            completion_tokens = 0
            try:
                completion_tokens = len(
                    encoding.encode(
                        model_response["choices"][0]["message"].get("content", "")
                    )
                )  ##[TODO] use the llama2 tokenizer here
            except Exception:
                # this should remain non blocking we should not block a response returning if calculating usage fails
                pass
        else:
            completion_tokens = 0

        model_response.created = int(time.time())
        model_response.model = model
        usage = Usage(
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=prompt_tokens + completion_tokens,
        )
        setattr(model_response, "usage", usage)
        model_response._hidden_params["original_response"] = completion_response
        return model_response

    def transform_response(
        self,
        model: str,
        raw_response: httpx.Response,
        model_response: ModelResponse,
        logging_obj: LoggingClass,
        request_data: Dict,
        messages: List[AllMessageValues],
        optional_params: Dict,
        litellm_params: Dict,
        encoding: Any,
        api_key: Optional[str] = None,
        json_mode: Optional[bool] = None,
    ) -> ModelResponse:
        ## Some servers might return streaming responses even though stream was not set to true. (e.g. Baseten)
        task = litellm_params.get("task", None)
        is_streamed = False
        if (
            raw_response.__dict__["headers"].get("Content-Type", "")
            == "text/event-stream"
        ):
            is_streamed = True

        # iterate over the complete streamed response, and return the final answer
        if is_streamed:
            completion_response = self._convert_streamed_response_to_complete_response(
                response=raw_response,
                logging_obj=logging_obj,
                model=model,
                data=request_data,
                api_key=api_key,
            )
        else:
            ## LOGGING
            logging_obj.post_call(
                input=request_data,
                api_key=api_key,
                original_response=raw_response.text,
                additional_args={"complete_input_dict": request_data},
            )
            ## RESPONSE OBJECT
            try:
                completion_response = raw_response.json()
                if isinstance(completion_response, dict):
                    completion_response = [completion_response]
            except Exception:
                raise HuggingFaceError(
                    message=f"Original Response received: {raw_response.text}",
                    status_code=raw_response.status_code,
                )

        if isinstance(completion_response, dict) and "error" in completion_response:
            raise HuggingFaceError(
                message=completion_response["error"],  # type: ignore
                status_code=raw_response.status_code,
            )
        return self.convert_to_model_response_object(
            completion_response=completion_response,
            model_response=model_response,
            task=task if task is not None and task in hf_task_list else None,
            optional_params=optional_params,
            encoding=encoding,
            messages=messages,
            model=model,
        )

# === NexusCore/openenv\Lib\site-packages\nltk\tree\parented.py ===
# Natural Language Toolkit: Text Trees
#
# Copyright (C) 2001-2024 NLTK Project
# Author: Edward Loper <edloper@gmail.com>
#         Steven Bird <stevenbird1@gmail.com>
#         Peter Ljunglöf <peter.ljunglof@gu.se>
#         Tom Aarsen <>
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT

import warnings
from abc import ABCMeta, abstractmethod

from nltk.tree.tree import Tree
from nltk.util import slice_bounds


######################################################################
## Parented trees
######################################################################
class AbstractParentedTree(Tree, metaclass=ABCMeta):
    """
    An abstract base class for a ``Tree`` that automatically maintains
    pointers to parent nodes.  These parent pointers are updated
    whenever any change is made to a tree's structure.  Two subclasses
    are currently defined:

      - ``ParentedTree`` is used for tree structures where each subtree
        has at most one parent.  This class should be used in cases
        where there is no"sharing" of subtrees.

      - ``MultiParentedTree`` is used for tree structures where a
        subtree may have zero or more parents.  This class should be
        used in cases where subtrees may be shared.

    Subclassing
    ===========
    The ``AbstractParentedTree`` class redefines all operations that
    modify a tree's structure to call two methods, which are used by
    subclasses to update parent information:

      - ``_setparent()`` is called whenever a new child is added.
      - ``_delparent()`` is called whenever a child is removed.
    """

    def __init__(self, node, children=None):
        super().__init__(node, children)
        # If children is None, the tree is read from node, and
        # all parents will be set during parsing.
        if children is not None:
            # Otherwise we have to set the parent of the children.
            # Iterate over self, and *not* children, because children
            # might be an iterator.
            for i, child in enumerate(self):
                if isinstance(child, Tree):
                    self._setparent(child, i, dry_run=True)
            for i, child in enumerate(self):
                if isinstance(child, Tree):
                    self._setparent(child, i)

    # ////////////////////////////////////////////////////////////
    # Parent management
    # ////////////////////////////////////////////////////////////
    @abstractmethod
    def _setparent(self, child, index, dry_run=False):
        """
        Update the parent pointer of ``child`` to point to ``self``.  This
        method is only called if the type of ``child`` is ``Tree``;
        i.e., it is not called when adding a leaf to a tree.  This method
        is always called before the child is actually added to the
        child list of ``self``.

        :type child: Tree
        :type index: int
        :param index: The index of ``child`` in ``self``.
        :raise TypeError: If ``child`` is a tree with an impropriate
            type.  Typically, if ``child`` is a tree, then its type needs
            to match the type of ``self``.  This prevents mixing of
            different tree types (single-parented, multi-parented, and
            non-parented).
        :param dry_run: If true, the don't actually set the child's
            parent pointer; just check for any error conditions, and
            raise an exception if one is found.
        """

    @abstractmethod
    def _delparent(self, child, index):
        """
        Update the parent pointer of ``child`` to not point to self.  This
        method is only called if the type of ``child`` is ``Tree``; i.e., it
        is not called when removing a leaf from a tree.  This method
        is always called before the child is actually removed from the
        child list of ``self``.

        :type child: Tree
        :type index: int
        :param index: The index of ``child`` in ``self``.
        """

    # ////////////////////////////////////////////////////////////
    # Methods that add/remove children
    # ////////////////////////////////////////////////////////////
    # Every method that adds or removes a child must make
    # appropriate calls to _setparent() and _delparent().

    def __delitem__(self, index):
        # del ptree[start:stop]
        if isinstance(index, slice):
            start, stop, step = slice_bounds(self, index, allow_step=True)
            # Clear all the children pointers.
            for i in range(start, stop, step):
                if isinstance(self[i], Tree):
                    self._delparent(self[i], i)
            # Delete the children from our child list.
            super().__delitem__(index)

        # del ptree[i]
        elif isinstance(index, int):
            if index < 0:
                index += len(self)
            if index < 0:
                raise IndexError("index out of range")
            # Clear the child's parent pointer.
            if isinstance(self[index], Tree):
                self._delparent(self[index], index)
            # Remove the child from our child list.
            super().__delitem__(index)

        elif isinstance(index, (list, tuple)):
            # del ptree[()]
            if len(index) == 0:
                raise IndexError("The tree position () may not be deleted.")
            # del ptree[(i,)]
            elif len(index) == 1:
                del self[index[0]]
            # del ptree[i1, i2, i3]
            else:
                del self[index[0]][index[1:]]

        else:
            raise TypeError(
                "%s indices must be integers, not %s"
                % (type(self).__name__, type(index).__name__)
            )

    def __setitem__(self, index, value):
        # ptree[start:stop] = value
        if isinstance(index, slice):
            start, stop, step = slice_bounds(self, index, allow_step=True)
            # make a copy of value, in case it's an iterator
            if not isinstance(value, (list, tuple)):
                value = list(value)
            # Check for any error conditions, so we can avoid ending
            # up in an inconsistent state if an error does occur.
            for i, child in enumerate(value):
                if isinstance(child, Tree):
                    self._setparent(child, start + i * step, dry_run=True)
            # clear the child pointers of all parents we're removing
            for i in range(start, stop, step):
                if isinstance(self[i], Tree):
                    self._delparent(self[i], i)
            # set the child pointers of the new children.  We do this
            # after clearing *all* child pointers, in case we're e.g.
            # reversing the elements in a tree.
            for i, child in enumerate(value):
                if isinstance(child, Tree):
                    self._setparent(child, start + i * step)
            # finally, update the content of the child list itself.
            super().__setitem__(index, value)

        # ptree[i] = value
        elif isinstance(index, int):
            if index < 0:
                index += len(self)
            if index < 0:
                raise IndexError("index out of range")
            # if the value is not changing, do nothing.
            if value is self[index]:
                return
            # Set the new child's parent pointer.
            if isinstance(value, Tree):
                self._setparent(value, index)
            # Remove the old child's parent pointer
            if isinstance(self[index], Tree):
                self._delparent(self[index], index)
            # Update our child list.
            super().__setitem__(index, value)

        elif isinstance(index, (list, tuple)):
            # ptree[()] = value
            if len(index) == 0:
                raise IndexError("The tree position () may not be assigned to.")
            # ptree[(i,)] = value
            elif len(index) == 1:
                self[index[0]] = value
            # ptree[i1, i2, i3] = value
            else:
                self[index[0]][index[1:]] = value

        else:
            raise TypeError(
                "%s indices must be integers, not %s"
                % (type(self).__name__, type(index).__name__)
            )

    def append(self, child):
        if isinstance(child, Tree):
            self._setparent(child, len(self))
        super().append(child)

    def extend(self, children):
        for child in children:
            if isinstance(child, Tree):
                self._setparent(child, len(self))
            super().append(child)

    def insert(self, index, child):
        # Handle negative indexes.  Note that if index < -len(self),
        # we do *not* raise an IndexError, unlike __getitem__.  This
        # is done for consistency with list.__getitem__ and list.index.
        if index < 0:
            index += len(self)
        if index < 0:
            index = 0
        # Set the child's parent, and update our child list.
        if isinstance(child, Tree):
            self._setparent(child, index)
        super().insert(index, child)

    def pop(self, index=-1):
        if index < 0:
            index += len(self)
        if index < 0:
            raise IndexError("index out of range")
        if isinstance(self[index], Tree):
            self._delparent(self[index], index)
        return super().pop(index)

    # n.b.: like `list`, this is done by equality, not identity!
    # To remove a specific child, use del ptree[i].
    def remove(self, child):
        index = self.index(child)
        if isinstance(self[index], Tree):
            self._delparent(self[index], index)
        super().remove(child)

    # We need to implement __getslice__ and friends, even though
    # they're deprecated, because otherwise list.__getslice__ will get
    # called (since we're subclassing from list).  Just delegate to
    # __getitem__ etc., but use max(0, start) and max(0, stop) because
    # because negative indices are already handled *before*
    # __getslice__ is called; and we don't want to double-count them.
    if hasattr(list, "__getslice__"):

        def __getslice__(self, start, stop):
            return self.__getitem__(slice(max(0, start), max(0, stop)))

        def __delslice__(self, start, stop):
            return self.__delitem__(slice(max(0, start), max(0, stop)))

        def __setslice__(self, start, stop, value):
            return self.__setitem__(slice(max(0, start), max(0, stop)), value)

    def __getnewargs__(self):
        """Method used by the pickle module when un-pickling.
        This method provides the arguments passed to ``__new__``
        upon un-pickling. Without this method, ParentedTree instances
        cannot be pickled and unpickled in Python 3.7+ onwards.

        :return: Tuple of arguments for ``__new__``, i.e. the label
            and the children of this node.
        :rtype: Tuple[Any, List[AbstractParentedTree]]
        """
        return (self._label, list(self))


class ParentedTree(AbstractParentedTree):
    """
    A ``Tree`` that automatically maintains parent pointers for
    single-parented trees.  The following are methods for querying
    the structure of a parented tree: ``parent``, ``parent_index``,
    ``left_sibling``, ``right_sibling``, ``root``, ``treeposition``.

    Each ``ParentedTree`` may have at most one parent.  In
    particular, subtrees may not be shared.  Any attempt to reuse a
    single ``ParentedTree`` as a child of more than one parent (or
    as multiple children of the same parent) will cause a
    ``ValueError`` exception to be raised.

    ``ParentedTrees`` should never be used in the same tree as ``Trees``
    or ``MultiParentedTrees``.  Mixing tree implementations may result
    in incorrect parent pointers and in ``TypeError`` exceptions.
    """

    def __init__(self, node, children=None):
        self._parent = None
        """The parent of this Tree, or None if it has no parent."""
        super().__init__(node, children)
        if children is None:
            # If children is None, the tree is read from node.
            # After parsing, the parent of the immediate children
            # will point to an intermediate tree, not self.
            # We fix this by brute force:
            for i, child in enumerate(self):
                if isinstance(child, Tree):
                    child._parent = None
                    self._setparent(child, i)

    def _frozen_class(self):
        from nltk.tree.immutable import ImmutableParentedTree

        return ImmutableParentedTree

    def copy(self, deep=False):
        if not deep:
            warnings.warn(
                f"{self.__class__.__name__} objects do not support shallow copies. Defaulting to a deep copy."
            )
        return super().copy(deep=True)

    # /////////////////////////////////////////////////////////////////
    # Methods
    # /////////////////////////////////////////////////////////////////

    def parent(self):
        """The parent of this tree, or None if it has no parent."""
        return self._parent

    def parent_index(self):
        """
        The index of this tree in its parent.  I.e.,
        ``ptree.parent()[ptree.parent_index()] is ptree``.  Note that
        ``ptree.parent_index()`` is not necessarily equal to
        ``ptree.parent.index(ptree)``, since the ``index()`` method
        returns the first child that is equal to its argument.
        """
        if self._parent is None:
            return None
        for i, child in enumerate(self._parent):
            if child is self:
                return i
        assert False, "expected to find self in self._parent!"

    def left_sibling(self):
        """The left sibling of this tree, or None if it has none."""
        parent_index = self.parent_index()
        if self._parent and parent_index > 0:
            return self._parent[parent_index - 1]
        return None  # no left sibling

    def right_sibling(self):
        """The right sibling of this tree, or None if it has none."""
        parent_index = self.parent_index()
        if self._parent and parent_index < (len(self._parent) - 1):
            return self._parent[parent_index + 1]
        return None  # no right sibling

    def root(self):
        """
        The root of this tree.  I.e., the unique ancestor of this tree
        whose parent is None.  If ``ptree.parent()`` is None, then
        ``ptree`` is its own root.
        """
        root = self
        while root.parent() is not None:
            root = root.parent()
        return root

    def treeposition(self):
        """
        The tree position of this tree, relative to the root of the
        tree.  I.e., ``ptree.root[ptree.treeposition] is ptree``.
        """
        if self.parent() is None:
            return ()
        else:
            return self.parent().treeposition() + (self.parent_index(),)

    # /////////////////////////////////////////////////////////////////
    # Parent Management
    # /////////////////////////////////////////////////////////////////

    def _delparent(self, child, index):
        # Sanity checks
        assert isinstance(child, ParentedTree)
        assert self[index] is child
        assert child._parent is self

        # Delete child's parent pointer.
        child._parent = None

    def _setparent(self, child, index, dry_run=False):
        # If the child's type is incorrect, then complain.
        if not isinstance(child, ParentedTree):
            raise TypeError("Can not insert a non-ParentedTree into a ParentedTree")

        # If child already has a parent, then complain.
        if hasattr(child, "_parent") and child._parent is not None:
            raise ValueError("Can not insert a subtree that already has a parent.")

        # Set child's parent pointer & index.
        if not dry_run:
            child._parent = self


class MultiParentedTree(AbstractParentedTree):
    """
    A ``Tree`` that automatically maintains parent pointers for
    multi-parented trees.  The following are methods for querying the
    structure of a multi-parented tree: ``parents()``, ``parent_indices()``,
    ``left_siblings()``, ``right_siblings()``, ``roots``, ``treepositions``.

    Each ``MultiParentedTree`` may have zero or more parents.  In
    particular, subtrees may be shared.  If a single
    ``MultiParentedTree`` is used as multiple children of the same
    parent, then that parent will appear multiple times in its
    ``parents()`` method.

    ``MultiParentedTrees`` should never be used in the same tree as
    ``Trees`` or ``ParentedTrees``.  Mixing tree implementations may
    result in incorrect parent pointers and in ``TypeError`` exceptions.
    """

    def __init__(self, node, children=None):
        self._parents = []
        """A list of this tree's parents.  This list should not
           contain duplicates, even if a parent contains this tree
           multiple times."""
        super().__init__(node, children)
        if children is None:
            # If children is None, the tree is read from node.
            # After parsing, the parent(s) of the immediate children
            # will point to an intermediate tree, not self.
            # We fix this by brute force:
            for i, child in enumerate(self):
                if isinstance(child, Tree):
                    child._parents = []
                    self._setparent(child, i)

    def _frozen_class(self):
        from nltk.tree.immutable import ImmutableMultiParentedTree

        return ImmutableMultiParentedTree

    # /////////////////////////////////////////////////////////////////
    # Methods
    # /////////////////////////////////////////////////////////////////

    def parents(self):
        """
        The set of parents of this tree.  If this tree has no parents,
        then ``parents`` is the empty set.  To check if a tree is used
        as multiple children of the same parent, use the
        ``parent_indices()`` method.

        :type: list(MultiParentedTree)
        """
        return list(self._parents)

    def left_siblings(self):
        """
        A list of all left siblings of this tree, in any of its parent
        trees.  A tree may be its own left sibling if it is used as
        multiple contiguous children of the same parent.  A tree may
        appear multiple times in this list if it is the left sibling
        of this tree with respect to multiple parents.

        :type: list(MultiParentedTree)
        """
        return [
            parent[index - 1]
            for (parent, index) in self._get_parent_indices()
            if index > 0
        ]

    def right_siblings(self):
        """
        A list of all right siblings of this tree, in any of its parent
        trees.  A tree may be its own right sibling if it is used as
        multiple contiguous children of the same parent.  A tree may
        appear multiple times in this list if it is the right sibling
        of this tree with respect to multiple parents.

        :type: list(MultiParentedTree)
        """
        return [
            parent[index + 1]
            for (parent, index) in self._get_parent_indices()
            if index < (len(parent) - 1)
        ]

    def _get_parent_indices(self):
        return [
            (parent, index)
            for parent in self._parents
            for index, child in enumerate(parent)
            if child is self
        ]

    def roots(self):
        """
        The set of all roots of this tree.  This set is formed by
        tracing all possible parent paths until trees with no parents
        are found.

        :type: list(MultiParentedTree)
        """
        return list(self._get_roots_helper({}).values())

    def _get_roots_helper(self, result):
        if self._parents:
            for parent in self._parents:
                parent._get_roots_helper(result)
        else:
            result[id(self)] = self
        return result

    def parent_indices(self, parent):
        """
        Return a list of the indices where this tree occurs as a child
        of ``parent``.  If this child does not occur as a child of
        ``parent``, then the empty list is returned.  The following is
        always true::

          for parent_index in ptree.parent_indices(parent):
              parent[parent_index] is ptree
        """
        if parent not in self._parents:
            return []
        else:
            return [index for (index, child) in enumerate(parent) if child is self]

    def treepositions(self, root):
        """
        Return a list of all tree positions that can be used to reach
        this multi-parented tree starting from ``root``.  I.e., the
        following is always true::

          for treepos in ptree.treepositions(root):
              root[treepos] is ptree
        """
        if self is root:
            return [()]
        else:
            return [
                treepos + (index,)
                for parent in self._parents
                for treepos in parent.treepositions(root)
                for (index, child) in enumerate(parent)
                if child is self
            ]

    # /////////////////////////////////////////////////////////////////
    # Parent Management
    # /////////////////////////////////////////////////////////////////

    def _delparent(self, child, index):
        # Sanity checks
        assert isinstance(child, MultiParentedTree)
        assert self[index] is child
        assert len([p for p in child._parents if p is self]) == 1

        # If the only copy of child in self is at index, then delete
        # self from child's parent list.
        for i, c in enumerate(self):
            if c is child and i != index:
                break
        else:
            child._parents.remove(self)

    def _setparent(self, child, index, dry_run=False):
        # If the child's type is incorrect, then complain.
        if not isinstance(child, MultiParentedTree):
            raise TypeError(
                "Can not insert a non-MultiParentedTree into a MultiParentedTree"
            )

        # Add self as a parent pointer if it's not already listed.
        if not dry_run:
            for parent in child._parents:
                if parent is self:
                    break
            else:
                child._parents.append(self)


__all__ = [
    "ParentedTree",
    "MultiParentedTree",
]

# === NexusCore/openenv\Lib\site-packages\trio\testing\_fake_net.py ===
# This should eventually be cleaned up and become public, but for right now I'm just
# implementing enough to test DTLS.

# TODO:
# - user-defined routers
# - TCP
# - UDP broadcast

from __future__ import annotations

import contextlib
import errno
import ipaddress
import os
import socket
import sys
from typing import (
    TYPE_CHECKING,
    Any,
    NoReturn,
    Union,
    overload,
)

import attrs

import trio
from trio._util import NoPublicConstructor, final

if TYPE_CHECKING:
    import builtins
    from collections.abc import Iterable
    from socket import AddressFamily, SocketKind
    from types import TracebackType

    from typing_extensions import Buffer, Self, TypeAlias

    from trio._socket import AddressFormat

IPAddress: TypeAlias = Union[ipaddress.IPv4Address, ipaddress.IPv6Address]


def _family_for(ip: IPAddress) -> int:
    if isinstance(ip, ipaddress.IPv4Address):
        return trio.socket.AF_INET
    elif isinstance(ip, ipaddress.IPv6Address):
        return trio.socket.AF_INET6
    raise NotImplementedError("Unhandled IPAddress instance type")  # pragma: no cover


def _wildcard_ip_for(family: int) -> IPAddress:
    if family == trio.socket.AF_INET:
        return ipaddress.ip_address("0.0.0.0")
    elif family == trio.socket.AF_INET6:
        return ipaddress.ip_address("::")
    raise NotImplementedError("Unhandled ip address family")  # pragma: no cover


# not used anywhere
def _localhost_ip_for(family: int) -> IPAddress:  # pragma: no cover
    if family == trio.socket.AF_INET:
        return ipaddress.ip_address("127.0.0.1")
    elif family == trio.socket.AF_INET6:
        return ipaddress.ip_address("::1")
    raise NotImplementedError("Unhandled ip address family")


def _fake_err(code: int) -> NoReturn:
    raise OSError(code, os.strerror(code))


def _scatter(data: bytes, buffers: Iterable[Buffer]) -> int:
    written = 0
    for buf in buffers:  # pragma: no branch
        next_piece = data[written : written + memoryview(buf).nbytes]
        with memoryview(buf) as mbuf:
            mbuf[: len(next_piece)] = next_piece
        written += len(next_piece)
        if written == len(data):  # pragma: no branch
            break
    return written


@attrs.frozen
class UDPEndpoint:
    ip: IPAddress
    port: int

    def as_python_sockaddr(self) -> tuple[str, int] | tuple[str, int, int, int]:
        sockaddr: tuple[str, int] | tuple[str, int, int, int] = (
            self.ip.compressed,
            self.port,
        )
        if isinstance(self.ip, ipaddress.IPv6Address):
            sockaddr += (0, 0)  # type: ignore[assignment]
        return sockaddr

    @classmethod
    def from_python_sockaddr(
        cls,
        sockaddr: tuple[str, int] | tuple[str, int, int, int],
    ) -> UDPEndpoint:
        ip, port = sockaddr[:2]
        return cls(ip=ipaddress.ip_address(ip), port=port)


@attrs.frozen
class UDPBinding:
    local: UDPEndpoint
    # remote: UDPEndpoint # ??


@attrs.frozen
class UDPPacket:
    source: UDPEndpoint
    destination: UDPEndpoint
    payload: bytes = attrs.field(repr=lambda p: p.hex())

    # not used/tested anywhere
    def reply(self, payload: bytes) -> UDPPacket:  # pragma: no cover
        return UDPPacket(
            source=self.destination,
            destination=self.source,
            payload=payload,
        )


@attrs.frozen
class FakeSocketFactory(trio.abc.SocketFactory):
    fake_net: FakeNet

    def socket(self, family: int, type_: int, proto: int) -> FakeSocket:  # type: ignore[override]
        return FakeSocket._create(self.fake_net, family, type_, proto)


@attrs.frozen
class FakeHostnameResolver(trio.abc.HostnameResolver):
    fake_net: FakeNet

    async def getaddrinfo(
        self,
        host: bytes | None,
        port: bytes | str | int | None,
        family: int = 0,
        type: int = 0,
        proto: int = 0,
        flags: int = 0,
    ) -> list[
        tuple[
            AddressFamily,
            SocketKind,
            int,
            str,
            tuple[str, int] | tuple[str, int, int, int] | tuple[int, bytes],
        ]
    ]:
        raise NotImplementedError("FakeNet doesn't do fake DNS yet")

    async def getnameinfo(
        self,
        sockaddr: tuple[str, int] | tuple[str, int, int, int],
        flags: int,
    ) -> tuple[str, str]:
        raise NotImplementedError("FakeNet doesn't do fake DNS yet")


@final
class FakeNet:
    def __init__(self) -> None:
        # When we need to pick an arbitrary unique ip address/port, use these:
        self._auto_ipv4_iter = ipaddress.IPv4Network("1.0.0.0/8").hosts()  # untested
        self._auto_ipv6_iter = ipaddress.IPv6Network("1::/16").hosts()  # untested
        self._auto_port_iter = iter(range(50000, 65535))

        self._bound: dict[UDPBinding, FakeSocket] = {}

        self.route_packet = None

    def _bind(self, binding: UDPBinding, socket: FakeSocket) -> None:
        if binding in self._bound:
            _fake_err(errno.EADDRINUSE)
        self._bound[binding] = socket

    def enable(self) -> None:
        trio.socket.set_custom_socket_factory(FakeSocketFactory(self))
        trio.socket.set_custom_hostname_resolver(FakeHostnameResolver(self))

    def send_packet(self, packet: UDPPacket) -> None:
        if self.route_packet is None:
            self.deliver_packet(packet)
        else:
            self.route_packet(packet)

    def deliver_packet(self, packet: UDPPacket) -> None:
        binding = UDPBinding(local=packet.destination)
        if binding in self._bound:
            self._bound[binding]._deliver_packet(packet)
        else:
            # No valid destination, so drop it
            pass


@final
class FakeSocket(trio.socket.SocketType, metaclass=NoPublicConstructor):
    def __init__(
        self,
        fake_net: FakeNet,
        family: AddressFamily,
        type: SocketKind,
        proto: int,
    ) -> None:
        self._fake_net = fake_net

        if not family:  # pragma: no cover
            family = trio.socket.AF_INET
        if not type:  # pragma: no cover
            type = trio.socket.SOCK_STREAM  # noqa: A001  # name shadowing builtin

        if family not in (trio.socket.AF_INET, trio.socket.AF_INET6):
            raise NotImplementedError(f"FakeNet doesn't (yet) support family={family}")
        if type != trio.socket.SOCK_DGRAM:
            raise NotImplementedError(f"FakeNet doesn't (yet) support type={type}")

        self._family = family
        self._type = type
        self._proto = proto

        self._closed = False

        self._packet_sender, self._packet_receiver = trio.open_memory_channel[
            UDPPacket
        ](float("inf"))

        # This is the source-of-truth for what port etc. this socket is bound to
        self._binding: UDPBinding | None = None

    @property
    def type(self) -> SocketKind:
        return self._type

    @property
    def family(self) -> AddressFamily:
        return self._family

    @property
    def proto(self) -> int:
        return self._proto

    def _check_closed(self) -> None:
        if self._closed:
            _fake_err(errno.EBADF)

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        if self._binding is not None:
            del self._fake_net._bound[self._binding]
        self._packet_receiver.close()

    async def _resolve_address_nocp(
        self,
        address: object,
        *,
        local: bool,
    ) -> tuple[str, int]:
        return await trio._socket._resolve_address_nocp(  # type: ignore[no-any-return]
            self.type,
            self.family,
            self.proto,
            address=address,
            ipv6_v6only=False,
            local=local,
        )

    def _deliver_packet(self, packet: UDPPacket) -> None:
        # sending to a closed socket -- UDP packets get dropped
        with contextlib.suppress(trio.BrokenResourceError):
            self._packet_sender.send_nowait(packet)

    ################################################################
    # Actual IO operation implementations
    ################################################################

    async def bind(self, addr: object) -> None:
        self._check_closed()
        if self._binding is not None:
            _fake_err(errno.EINVAL)
        await trio.lowlevel.checkpoint()
        ip_str, port, *_ = await self._resolve_address_nocp(addr, local=True)
        assert _ == [], "TODO: handle other values?"

        ip = ipaddress.ip_address(ip_str)
        assert _family_for(ip) == self.family
        # We convert binds to INET_ANY into binds to localhost
        if ip == ipaddress.ip_address("0.0.0.0"):
            ip = ipaddress.ip_address("127.0.0.1")
        elif ip == ipaddress.ip_address("::"):
            ip = ipaddress.ip_address("::1")
        if port == 0:
            port = next(self._fake_net._auto_port_iter)
        binding = UDPBinding(local=UDPEndpoint(ip, port))
        self._fake_net._bind(binding, self)
        self._binding = binding

    async def connect(self, peer: object) -> NoReturn:
        raise NotImplementedError("FakeNet does not (yet) support connected sockets")

    async def _sendmsg(
        self,
        buffers: Iterable[Buffer],
        ancdata: Iterable[tuple[int, int, Buffer]] = (),
        flags: int = 0,
        address: AddressFormat | None = None,
    ) -> int:
        self._check_closed()

        await trio.lowlevel.checkpoint()

        if address is not None:
            address = await self._resolve_address_nocp(address, local=False)
        if ancdata:
            raise NotImplementedError("FakeNet doesn't support ancillary data")
        if flags:
            raise NotImplementedError(f"FakeNet send flags must be 0, not {flags}")

        if address is None:
            _fake_err(errno.ENOTCONN)

        destination = UDPEndpoint.from_python_sockaddr(address)

        if self._binding is None:
            await self.bind((_wildcard_ip_for(self.family).compressed, 0))

        payload = b"".join(buffers)

        assert self._binding is not None
        packet = UDPPacket(
            source=self._binding.local,
            destination=destination,
            payload=payload,
        )

        self._fake_net.send_packet(packet)

        return len(payload)

    if sys.platform != "win32" or (
        not TYPE_CHECKING and hasattr(socket.socket, "sendmsg")
    ):
        sendmsg = _sendmsg

    async def _recvmsg_into(
        self,
        buffers: Iterable[Buffer],
        ancbufsize: int = 0,
        flags: int = 0,
    ) -> tuple[
        int,
        list[tuple[int, int, bytes]],
        int,
        tuple[str, int] | tuple[str, int, int, int],
    ]:
        if ancbufsize != 0:
            raise NotImplementedError("FakeNet doesn't support ancillary data")
        if flags != 0:
            raise NotImplementedError("FakeNet doesn't support any recv flags")
        if self._binding is None:
            # I messed this up a few times when writing tests ... but it also never happens
            # in any of the existing tests, so maybe it could be intentional...
            raise NotImplementedError(
                "The code will most likely hang if you try to receive on a fakesocket "
                "without a binding. If that is not the case, or you explicitly want to "
                "test that, remove this warning.",
            )

        self._check_closed()

        ancdata: list[tuple[int, int, bytes]] = []
        msg_flags = 0

        packet = await self._packet_receiver.receive()
        address = packet.source.as_python_sockaddr()
        written = _scatter(packet.payload, buffers)
        if written < len(packet.payload):
            msg_flags |= trio.socket.MSG_TRUNC
        return written, ancdata, msg_flags, address

    if sys.platform != "win32" or (
        not TYPE_CHECKING and hasattr(socket.socket, "sendmsg")
    ):
        recvmsg_into = _recvmsg_into

    ################################################################
    # Simple state query stuff
    ################################################################

    def getsockname(self) -> tuple[str, int] | tuple[str, int, int, int]:
        self._check_closed()
        if self._binding is not None:
            return self._binding.local.as_python_sockaddr()
        elif self.family == trio.socket.AF_INET:
            return ("0.0.0.0", 0)
        else:
            assert self.family == trio.socket.AF_INET6
            return ("::", 0)

    # TODO: This method is not tested, and seems to make incorrect assumptions. It should maybe raise NotImplementedError.
    def getpeername(self) -> tuple[str, int] | tuple[str, int, int, int]:
        self._check_closed()
        if self._binding is not None:
            assert hasattr(
                self._binding,
                "remote",
            ), "This method seems to assume that self._binding has a remote UDPEndpoint"
            if self._binding.remote is not None:  # pragma: no cover
                assert isinstance(
                    self._binding.remote,
                    UDPEndpoint,
                ), "Self._binding.remote should be a UDPEndpoint"
                return self._binding.remote.as_python_sockaddr()
        _fake_err(errno.ENOTCONN)

    @overload
    def getsockopt(self, /, level: int, optname: int) -> int: ...

    @overload
    def getsockopt(self, /, level: int, optname: int, buflen: int) -> bytes: ...

    def getsockopt(
        self,
        /,
        level: int,
        optname: int,
        buflen: int | None = None,
    ) -> int | bytes:
        self._check_closed()
        raise OSError(f"FakeNet doesn't implement getsockopt({level}, {optname})")

    @overload
    def setsockopt(self, /, level: int, optname: int, value: int | Buffer) -> None: ...

    @overload
    def setsockopt(
        self,
        /,
        level: int,
        optname: int,
        value: None,
        optlen: int,
    ) -> None: ...

    def setsockopt(
        self,
        /,
        level: int,
        optname: int,
        value: int | Buffer | None,
        optlen: int | None = None,
    ) -> None:
        self._check_closed()

        if (level, optname) == (
            trio.socket.IPPROTO_IPV6,
            trio.socket.IPV6_V6ONLY,
        ) and not value:
            raise NotImplementedError("FakeNet always has IPV6_V6ONLY=True")

        raise OSError(f"FakeNet doesn't implement setsockopt({level}, {optname}, ...)")

    ################################################################
    # Various boilerplate and trivial stubs
    ################################################################

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self,
        exc_type: builtins.type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self.close()

    async def send(self, data: Buffer, flags: int = 0) -> int:
        return await self.sendto(data, flags, None)

    # __ prefixed arguments because typeshed uses that and typechecker issues
    @overload
    async def sendto(
        self,
        __data: Buffer,  # noqa: PYI063
        __address: tuple[object, ...] | str | Buffer,
    ) -> int: ...

    # __ prefixed arguments because typeshed uses that and typechecker issues
    @overload
    async def sendto(
        self,
        __data: Buffer,  # noqa: PYI063
        __flags: int,
        __address: tuple[object, ...] | str | Buffer | None,
    ) -> int: ...

    async def sendto(  # type: ignore[explicit-any]
        self,
        *args: Any,
    ) -> int:
        data: Buffer
        flags: int
        address: tuple[object, ...] | str | Buffer
        if len(args) == 2:
            data, address = args
            flags = 0
        elif len(args) == 3:
            data, flags, address = args
        else:
            raise TypeError("wrong number of arguments")
        return await self._sendmsg([data], [], flags, address)

    async def recv(self, bufsize: int, flags: int = 0) -> bytes:
        data, _address = await self.recvfrom(bufsize, flags)
        return data

    async def recv_into(self, buf: Buffer, nbytes: int = 0, flags: int = 0) -> int:
        got_bytes, _address = await self.recvfrom_into(buf, nbytes, flags)
        return got_bytes

    async def recvfrom(
        self,
        bufsize: int,
        flags: int = 0,
    ) -> tuple[bytes, AddressFormat]:
        data, _ancdata, _msg_flags, address = await self._recvmsg(bufsize, flags)
        return data, address

    async def recvfrom_into(
        self,
        buf: Buffer,
        nbytes: int = 0,
        flags: int = 0,
    ) -> tuple[int, AddressFormat]:
        if nbytes != 0 and nbytes != memoryview(buf).nbytes:
            raise NotImplementedError("partial recvfrom_into")
        got_nbytes, _ancdata, _msg_flags, address = await self._recvmsg_into(
            [buf],
            0,
            flags,
        )
        return got_nbytes, address

    async def _recvmsg(
        self,
        bufsize: int,
        ancbufsize: int = 0,
        flags: int = 0,
    ) -> tuple[bytes, list[tuple[int, int, bytes]], int, AddressFormat]:
        buf = bytearray(bufsize)
        got_nbytes, ancdata, msg_flags, address = await self._recvmsg_into(
            [buf],
            ancbufsize,
            flags,
        )
        return (bytes(buf[:got_nbytes]), ancdata, msg_flags, address)

    if sys.platform != "win32" or (
        not TYPE_CHECKING and hasattr(socket.socket, "sendmsg")
    ):
        recvmsg = _recvmsg

    def fileno(self) -> int:
        raise NotImplementedError("can't get fileno() for FakeNet sockets")

    def detach(self) -> int:
        raise NotImplementedError("can't detach() a FakeNet socket")

    def get_inheritable(self) -> bool:
        return False

    def set_inheritable(self, inheritable: bool) -> None:
        if inheritable:
            raise NotImplementedError("FakeNet can't make inheritable sockets")

    if sys.platform == "win32" or (
        not TYPE_CHECKING and hasattr(socket.socket, "share")
    ):

        def share(self, process_id: int) -> bytes:
            raise NotImplementedError("FakeNet can't share sockets")

# === NexusCore/myenv\Lib\site-packages\pip\_vendor\pygments\lexers\_mapping.py ===
# Automatically generated by scripts/gen_mapfiles.py.
# DO NOT EDIT BY HAND; run `tox -e mapfiles` instead.

LEXERS = {
    'ABAPLexer': ('pip._vendor.pygments.lexers.business', 'ABAP', ('abap',), ('*.abap', '*.ABAP'), ('text/x-abap',)),
    'AMDGPULexer': ('pip._vendor.pygments.lexers.amdgpu', 'AMDGPU', ('amdgpu',), ('*.isa',), ()),
    'APLLexer': ('pip._vendor.pygments.lexers.apl', 'APL', ('apl',), ('*.apl', '*.aplf', '*.aplo', '*.apln', '*.aplc', '*.apli', '*.dyalog'), ()),
    'AbnfLexer': ('pip._vendor.pygments.lexers.grammar_notation', 'ABNF', ('abnf',), ('*.abnf',), ('text/x-abnf',)),
    'ActionScript3Lexer': ('pip._vendor.pygments.lexers.actionscript', 'ActionScript 3', ('actionscript3', 'as3'), ('*.as',), ('application/x-actionscript3', 'text/x-actionscript3', 'text/actionscript3')),
    'ActionScriptLexer': ('pip._vendor.pygments.lexers.actionscript', 'ActionScript', ('actionscript', 'as'), ('*.as',), ('application/x-actionscript', 'text/x-actionscript', 'text/actionscript')),
    'AdaLexer': ('pip._vendor.pygments.lexers.ada', 'Ada', ('ada', 'ada95', 'ada2005'), ('*.adb', '*.ads', '*.ada'), ('text/x-ada',)),
    'AdlLexer': ('pip._vendor.pygments.lexers.archetype', 'ADL', ('adl',), ('*.adl', '*.adls', '*.adlf', '*.adlx'), ()),
    'AgdaLexer': ('pip._vendor.pygments.lexers.haskell', 'Agda', ('agda',), ('*.agda',), ('text/x-agda',)),
    'AheuiLexer': ('pip._vendor.pygments.lexers.esoteric', 'Aheui', ('aheui',), ('*.aheui',), ()),
    'AlloyLexer': ('pip._vendor.pygments.lexers.dsls', 'Alloy', ('alloy',), ('*.als',), ('text/x-alloy',)),
    'AmbientTalkLexer': ('pip._vendor.pygments.lexers.ambient', 'AmbientTalk', ('ambienttalk', 'ambienttalk/2', 'at'), ('*.at',), ('text/x-ambienttalk',)),
    'AmplLexer': ('pip._vendor.pygments.lexers.ampl', 'Ampl', ('ampl',), ('*.run',), ()),
    'Angular2HtmlLexer': ('pip._vendor.pygments.lexers.templates', 'HTML + Angular2', ('html+ng2',), ('*.ng2',), ()),
    'Angular2Lexer': ('pip._vendor.pygments.lexers.templates', 'Angular2', ('ng2',), (), ()),
    'AntlrActionScriptLexer': ('pip._vendor.pygments.lexers.parsers', 'ANTLR With ActionScript Target', ('antlr-actionscript', 'antlr-as'), ('*.G', '*.g'), ()),
    'AntlrCSharpLexer': ('pip._vendor.pygments.lexers.parsers', 'ANTLR With C# Target', ('antlr-csharp', 'antlr-c#'), ('*.G', '*.g'), ()),
    'AntlrCppLexer': ('pip._vendor.pygments.lexers.parsers', 'ANTLR With CPP Target', ('antlr-cpp',), ('*.G', '*.g'), ()),
    'AntlrJavaLexer': ('pip._vendor.pygments.lexers.parsers', 'ANTLR With Java Target', ('antlr-java',), ('*.G', '*.g'), ()),
    'AntlrLexer': ('pip._vendor.pygments.lexers.parsers', 'ANTLR', ('antlr',), (), ()),
    'AntlrObjectiveCLexer': ('pip._vendor.pygments.lexers.parsers', 'ANTLR With ObjectiveC Target', ('antlr-objc',), ('*.G', '*.g'), ()),
    'AntlrPerlLexer': ('pip._vendor.pygments.lexers.parsers', 'ANTLR With Perl Target', ('antlr-perl',), ('*.G', '*.g'), ()),
    'AntlrPythonLexer': ('pip._vendor.pygments.lexers.parsers', 'ANTLR With Python Target', ('antlr-python',), ('*.G', '*.g'), ()),
    'AntlrRubyLexer': ('pip._vendor.pygments.lexers.parsers', 'ANTLR With Ruby Target', ('antlr-ruby', 'antlr-rb'), ('*.G', '*.g'), ()),
    'ApacheConfLexer': ('pip._vendor.pygments.lexers.configs', 'ApacheConf', ('apacheconf', 'aconf', 'apache'), ('.htaccess', 'apache.conf', 'apache2.conf'), ('text/x-apacheconf',)),
    'AppleScriptLexer': ('pip._vendor.pygments.lexers.scripting', 'AppleScript', ('applescript',), ('*.applescript',), ()),
    'ArduinoLexer': ('pip._vendor.pygments.lexers.c_like', 'Arduino', ('arduino',), ('*.ino',), ('text/x-arduino',)),
    'ArrowLexer': ('pip._vendor.pygments.lexers.arrow', 'Arrow', ('arrow',), ('*.arw',), ()),
    'ArturoLexer': ('pip._vendor.pygments.lexers.arturo', 'Arturo', ('arturo', 'art'), ('*.art',), ()),
    'AscLexer': ('pip._vendor.pygments.lexers.asc', 'ASCII armored', ('asc', 'pem'), ('*.asc', '*.pem', 'id_dsa', 'id_ecdsa', 'id_ecdsa_sk', 'id_ed25519', 'id_ed25519_sk', 'id_rsa'), ('application/pgp-keys', 'application/pgp-encrypted', 'application/pgp-signature', 'application/pem-certificate-chain')),
    'Asn1Lexer': ('pip._vendor.pygments.lexers.asn1', 'ASN.1', ('asn1',), ('*.asn1',), ()),
    'AspectJLexer': ('pip._vendor.pygments.lexers.jvm', 'AspectJ', ('aspectj',), ('*.aj',), ('text/x-aspectj',)),
    'AsymptoteLexer': ('pip._vendor.pygments.lexers.graphics', 'Asymptote', ('asymptote', 'asy'), ('*.asy',), ('text/x-asymptote',)),
    'AugeasLexer': ('pip._vendor.pygments.lexers.configs', 'Augeas', ('augeas',), ('*.aug',), ()),
    'AutoItLexer': ('pip._vendor.pygments.lexers.automation', 'AutoIt', ('autoit',), ('*.au3',), ('text/x-autoit',)),
    'AutohotkeyLexer': ('pip._vendor.pygments.lexers.automation', 'autohotkey', ('autohotkey', 'ahk'), ('*.ahk', '*.ahkl'), ('text/x-autohotkey',)),
    'AwkLexer': ('pip._vendor.pygments.lexers.textedit', 'Awk', ('awk', 'gawk', 'mawk', 'nawk'), ('*.awk',), ('application/x-awk',)),
    'BBCBasicLexer': ('pip._vendor.pygments.lexers.basic', 'BBC Basic', ('bbcbasic',), ('*.bbc',), ()),
    'BBCodeLexer': ('pip._vendor.pygments.lexers.markup', 'BBCode', ('bbcode',), (), ('text/x-bbcode',)),
    'BCLexer': ('pip._vendor.pygments.lexers.algebra', 'BC', ('bc',), ('*.bc',), ()),
    'BQNLexer': ('pip._vendor.pygments.lexers.bqn', 'BQN', ('bqn',), ('*.bqn',), ()),
    'BSTLexer': ('pip._vendor.pygments.lexers.bibtex', 'BST', ('bst', 'bst-pybtex'), ('*.bst',), ()),
    'BareLexer': ('pip._vendor.pygments.lexers.bare', 'BARE', ('bare',), ('*.bare',), ()),
    'BaseMakefileLexer': ('pip._vendor.pygments.lexers.make', 'Base Makefile', ('basemake',), (), ()),
    'BashLexer': ('pip._vendor.pygments.lexers.shell', 'Bash', ('bash', 'sh', 'ksh', 'zsh', 'shell', 'openrc'), ('*.sh', '*.ksh', '*.bash', '*.ebuild', '*.eclass', '*.exheres-0', '*.exlib', '*.zsh', '.bashrc', 'bashrc', '.bash_*', 'bash_*', 'zshrc', '.zshrc', '.kshrc', 'kshrc', 'PKGBUILD'), ('application/x-sh', 'application/x-shellscript', 'text/x-shellscript')),
    'BashSessionLexer': ('pip._vendor.pygments.lexers.shell', 'Bash Session', ('console', 'shell-session'), ('*.sh-session', '*.shell-session'), ('application/x-shell-session', 'application/x-sh-session')),
    'BatchLexer': ('pip._vendor.pygments.lexers.shell', 'Batchfile', ('batch', 'bat', 'dosbatch', 'winbatch'), ('*.bat', '*.cmd'), ('application/x-dos-batch',)),
    'BddLexer': ('pip._vendor.pygments.lexers.bdd', 'Bdd', ('bdd',), ('*.feature',), ('text/x-bdd',)),
    'BefungeLexer': ('pip._vendor.pygments.lexers.esoteric', 'Befunge', ('befunge',), ('*.befunge',), ('application/x-befunge',)),
    'BerryLexer': ('pip._vendor.pygments.lexers.berry', 'Berry', ('berry', 'be'), ('*.be',), ('text/x-berry', 'application/x-berry')),
    'BibTeXLexer': ('pip._vendor.pygments.lexers.bibtex', 'BibTeX', ('bibtex', 'bib'), ('*.bib',), ('text/x-bibtex',)),
    'BlitzBasicLexer': ('pip._vendor.pygments.lexers.basic', 'BlitzBasic', ('blitzbasic', 'b3d', 'bplus'), ('*.bb', '*.decls'), ('text/x-bb',)),
    'BlitzMaxLexer': ('pip._vendor.pygments.lexers.basic', 'BlitzMax', ('blitzmax', 'bmax'), ('*.bmx',), ('text/x-bmx',)),
    'BlueprintLexer': ('pip._vendor.pygments.lexers.blueprint', 'Blueprint', ('blueprint',), ('*.blp',), ('text/x-blueprint',)),
    'BnfLexer': ('pip._vendor.pygments.lexers.grammar_notation', 'BNF', ('bnf',), ('*.bnf',), ('text/x-bnf',)),
    'BoaLexer': ('pip._vendor.pygments.lexers.boa', 'Boa', ('boa',), ('*.boa',), ()),
    'BooLexer': ('pip._vendor.pygments.lexers.dotnet', 'Boo', ('boo',), ('*.boo',), ('text/x-boo',)),
    'BoogieLexer': ('pip._vendor.pygments.lexers.verification', 'Boogie', ('boogie',), ('*.bpl',), ()),
    'BrainfuckLexer': ('pip._vendor.pygments.lexers.esoteric', 'Brainfuck', ('brainfuck', 'bf'), ('*.bf', '*.b'), ('application/x-brainfuck',)),
    'BugsLexer': ('pip._vendor.pygments.lexers.modeling', 'BUGS', ('bugs', 'winbugs', 'openbugs'), ('*.bug',), ()),
    'CAmkESLexer': ('pip._vendor.pygments.lexers.esoteric', 'CAmkES', ('camkes', 'idl4'), ('*.camkes', '*.idl4'), ()),
    'CLexer': ('pip._vendor.pygments.lexers.c_cpp', 'C', ('c',), ('*.c', '*.h', '*.idc', '*.x[bp]m'), ('text/x-chdr', 'text/x-csrc', 'image/x-xbitmap', 'image/x-xpixmap')),
    'CMakeLexer': ('pip._vendor.pygments.lexers.make', 'CMake', ('cmake',), ('*.cmake', 'CMakeLists.txt'), ('text/x-cmake',)),
    'CObjdumpLexer': ('pip._vendor.pygments.lexers.asm', 'c-objdump', ('c-objdump',), ('*.c-objdump',), ('text/x-c-objdump',)),
    'CPSALexer': ('pip._vendor.pygments.lexers.lisp', 'CPSA', ('cpsa',), ('*.cpsa',), ()),
    'CSSUL4Lexer': ('pip._vendor.pygments.lexers.ul4', 'CSS+UL4', ('css+ul4',), ('*.cssul4',), ()),
    'CSharpAspxLexer': ('pip._vendor.pygments.lexers.dotnet', 'aspx-cs', ('aspx-cs',), ('*.aspx', '*.asax', '*.ascx', '*.ashx', '*.asmx', '*.axd'), ()),
    'CSharpLexer': ('pip._vendor.pygments.lexers.dotnet', 'C#', ('csharp', 'c#', 'cs'), ('*.cs',), ('text/x-csharp',)),
    'Ca65Lexer': ('pip._vendor.pygments.lexers.asm', 'ca65 assembler', ('ca65',), ('*.s',), ()),
    'CadlLexer': ('pip._vendor.pygments.lexers.archetype', 'cADL', ('cadl',), ('*.cadl',), ()),
    'CapDLLexer': ('pip._vendor.pygments.lexers.esoteric', 'CapDL', ('capdl',), ('*.cdl',), ()),
    'CapnProtoLexer': ('pip._vendor.pygments.lexers.capnproto', "Cap'n Proto", ('capnp',), ('*.capnp',), ()),
    'CarbonLexer': ('pip._vendor.pygments.lexers.carbon', 'Carbon', ('carbon',), ('*.carbon',), ('text/x-carbon',)),
    'CbmBasicV2Lexer': ('pip._vendor.pygments.lexers.basic', 'CBM BASIC V2', ('cbmbas',), ('*.bas',), ()),
    'CddlLexer': ('pip._vendor.pygments.lexers.cddl', 'CDDL', ('cddl',), ('*.cddl',), ('text/x-cddl',)),
    'CeylonLexer': ('pip._vendor.pygments.lexers.jvm', 'Ceylon', ('ceylon',), ('*.ceylon',), ('text/x-ceylon',)),
    'Cfengine3Lexer': ('pip._vendor.pygments.lexers.configs', 'CFEngine3', ('cfengine3', 'cf3'), ('*.cf',), ()),
    'ChaiscriptLexer': ('pip._vendor.pygments.lexers.scripting', 'ChaiScript', ('chaiscript', 'chai'), ('*.chai',), ('text/x-chaiscript', 'application/x-chaiscript')),
    'ChapelLexer': ('pip._vendor.pygments.lexers.chapel', 'Chapel', ('chapel', 'chpl'), ('*.chpl',), ()),
    'CharmciLexer': ('pip._vendor.pygments.lexers.c_like', 'Charmci', ('charmci',), ('*.ci',), ()),
    'CheetahHtmlLexer': ('pip._vendor.pygments.lexers.templates', 'HTML+Cheetah', ('html+cheetah', 'html+spitfire', 'htmlcheetah'), (), ('text/html+cheetah', 'text/html+spitfire')),
    'CheetahJavascriptLexer': ('pip._vendor.pygments.lexers.templates', 'JavaScript+Cheetah', ('javascript+cheetah', 'js+cheetah', 'javascript+spitfire', 'js+spitfire'), (), ('application/x-javascript+cheetah', 'text/x-javascript+cheetah', 'text/javascript+cheetah', 'application/x-javascript+spitfire', 'text/x-javascript+spitfire', 'text/javascript+spitfire')),
    'CheetahLexer': ('pip._vendor.pygments.lexers.templates', 'Cheetah', ('cheetah', 'spitfire'), ('*.tmpl', '*.spt'), ('application/x-cheetah', 'application/x-spitfire')),
    'CheetahXmlLexer': ('pip._vendor.pygments.lexers.templates', 'XML+Cheetah', ('xml+cheetah', 'xml+spitfire'), (), ('application/xml+cheetah', 'application/xml+spitfire')),
    'CirruLexer': ('pip._vendor.pygments.lexers.webmisc', 'Cirru', ('cirru',), ('*.cirru',), ('text/x-cirru',)),
    'ClayLexer': ('pip._vendor.pygments.lexers.c_like', 'Clay', ('clay',), ('*.clay',), ('text/x-clay',)),
    'CleanLexer': ('pip._vendor.pygments.lexers.clean', 'Clean', ('clean',), ('*.icl', '*.dcl'), ()),
    'ClojureLexer': ('pip._vendor.pygments.lexers.jvm', 'Clojure', ('clojure', 'clj'), ('*.clj', '*.cljc'), ('text/x-clojure', 'application/x-clojure')),
    'ClojureScriptLexer': ('pip._vendor.pygments.lexers.jvm', 'ClojureScript', ('clojurescript', 'cljs'), ('*.cljs',), ('text/x-clojurescript', 'application/x-clojurescript')),
    'CobolFreeformatLexer': ('pip._vendor.pygments.lexers.business', 'COBOLFree', ('cobolfree',), ('*.cbl', '*.CBL'), ()),
    'CobolLexer': ('pip._vendor.pygments.lexers.business', 'COBOL', ('cobol',), ('*.cob', '*.COB', '*.cpy', '*.CPY'), ('text/x-cobol',)),
    'CoffeeScriptLexer': ('pip._vendor.pygments.lexers.javascript', 'CoffeeScript', ('coffeescript', 'coffee-script', 'coffee'), ('*.coffee',), ('text/coffeescript',)),
    'ColdfusionCFCLexer': ('pip._vendor.pygments.lexers.templates', 'Coldfusion CFC', ('cfc',), ('*.cfc',), ()),
    'ColdfusionHtmlLexer': ('pip._vendor.pygments.lexers.templates', 'Coldfusion HTML', ('cfm',), ('*.cfm', '*.cfml'), ('application/x-coldfusion',)),
    'ColdfusionLexer': ('pip._vendor.pygments.lexers.templates', 'cfstatement', ('cfs',), (), ()),
    'Comal80Lexer': ('pip._vendor.pygments.lexers.comal', 'COMAL-80', ('comal', 'comal80'), ('*.cml', '*.comal'), ()),
    'CommonLispLexer': ('pip._vendor.pygments.lexers.lisp', 'Common Lisp', ('common-lisp', 'cl', 'lisp'), ('*.cl', '*.lisp'), ('text/x-common-lisp',)),
    'ComponentPascalLexer': ('pip._vendor.pygments.lexers.oberon', 'Component Pascal', ('componentpascal', 'cp'), ('*.cp', '*.cps'), ('text/x-component-pascal',)),
    'CoqLexer': ('pip._vendor.pygments.lexers.theorem', 'Coq', ('coq',), ('*.v',), ('text/x-coq',)),
    'CplintLexer': ('pip._vendor.pygments.lexers.cplint', 'cplint', ('cplint',), ('*.ecl', '*.prolog', '*.pro', '*.pl', '*.P', '*.lpad', '*.cpl'), ('text/x-cplint',)),
    'CppLexer': ('pip._vendor.pygments.lexers.c_cpp', 'C++', ('cpp', 'c++'), ('*.cpp', '*.hpp', '*.c++', '*.h++', '*.cc', '*.hh', '*.cxx', '*.hxx', '*.C', '*.H', '*.cp', '*.CPP', '*.tpp'), ('text/x-c++hdr', 'text/x-c++src')),
    'CppObjdumpLexer': ('pip._vendor.pygments.lexers.asm', 'cpp-objdump', ('cpp-objdump', 'c++-objdumb', 'cxx-objdump'), ('*.cpp-objdump', '*.c++-objdump', '*.cxx-objdump'), ('text/x-cpp-objdump',)),
    'CrmshLexer': ('pip._vendor.pygments.lexers.dsls', 'Crmsh', ('crmsh', 'pcmk'), ('*.crmsh', '*.pcmk'), ()),
    'CrocLexer': ('pip._vendor.pygments.lexers.d', 'Croc', ('croc',), ('*.croc',), ('text/x-crocsrc',)),
    'CryptolLexer': ('pip._vendor.pygments.lexers.haskell', 'Cryptol', ('cryptol', 'cry'), ('*.cry',), ('text/x-cryptol',)),
    'CrystalLexer': ('pip._vendor.pygments.lexers.crystal', 'Crystal', ('cr', 'crystal'), ('*.cr',), ('text/x-crystal',)),
    'CsoundDocumentLexer': ('pip._vendor.pygments.lexers.csound', 'Csound Document', ('csound-document', 'csound-csd'), ('*.csd',), ()),
    'CsoundOrchestraLexer': ('pip._vendor.pygments.lexers.csound', 'Csound Orchestra', ('csound', 'csound-orc'), ('*.orc', '*.udo'), ()),
    'CsoundScoreLexer': ('pip._vendor.pygments.lexers.csound', 'Csound Score', ('csound-score', 'csound-sco'), ('*.sco',), ()),
    'CssDjangoLexer': ('pip._vendor.pygments.lexers.templates', 'CSS+Django/Jinja', ('css+django', 'css+jinja'), ('*.css.j2', '*.css.jinja2'), ('text/css+django', 'text/css+jinja')),
    'CssErbLexer': ('pip._vendor.pygments.lexers.templates', 'CSS+Ruby', ('css+ruby', 'css+erb'), (), ('text/css+ruby',)),
    'CssGenshiLexer': ('pip._vendor.pygments.lexers.templates', 'CSS+Genshi Text', ('css+genshitext', 'css+genshi'), (), ('text/css+genshi',)),
    'CssLexer': ('pip._vendor.pygments.lexers.css', 'CSS', ('css',), ('*.css',), ('text/css',)),
    'CssPhpLexer': ('pip._vendor.pygments.lexers.templates', 'CSS+PHP', ('css+php',), (), ('text/css+php',)),
    'CssSmartyLexer': ('pip._vendor.pygments.lexers.templates', 'CSS+Smarty', ('css+smarty',), (), ('text/css+smarty',)),
    'CudaLexer': ('pip._vendor.pygments.lexers.c_like', 'CUDA', ('cuda', 'cu'), ('*.cu', '*.cuh'), ('text/x-cuda',)),
    'CypherLexer': ('pip._vendor.pygments.lexers.graph', 'Cypher', ('cypher',), ('*.cyp', '*.cypher'), ()),
    'CythonLexer': ('pip._vendor.pygments.lexers.python', 'Cython', ('cython', 'pyx', 'pyrex'), ('*.pyx', '*.pxd', '*.pxi'), ('text/x-cython', 'application/x-cython')),
    'DLexer': ('pip._vendor.pygments.lexers.d', 'D', ('d',), ('*.d', '*.di'), ('text/x-dsrc',)),
    'DObjdumpLexer': ('pip._vendor.pygments.lexers.asm', 'd-objdump', ('d-objdump',), ('*.d-objdump',), ('text/x-d-objdump',)),
    'DarcsPatchLexer': ('pip._vendor.pygments.lexers.diff', 'Darcs Patch', ('dpatch',), ('*.dpatch', '*.darcspatch'), ()),
    'DartLexer': ('pip._vendor.pygments.lexers.javascript', 'Dart', ('dart',), ('*.dart',), ('text/x-dart',)),
    'Dasm16Lexer': ('pip._vendor.pygments.lexers.asm', 'DASM16', ('dasm16',), ('*.dasm16', '*.dasm'), ('text/x-dasm16',)),
    'DaxLexer': ('pip._vendor.pygments.lexers.dax', 'Dax', ('dax',), ('*.dax',), ()),
    'DebianControlLexer': ('pip._vendor.pygments.lexers.installers', 'Debian Control file', ('debcontrol', 'control'), ('control',), ()),
    'DelphiLexer': ('pip._vendor.pygments.lexers.pascal', 'Delphi', ('delphi', 'pas', 'pascal', 'objectpascal'), ('*.pas', '*.dpr'), ('text/x-pascal',)),
    'DesktopLexer': ('pip._vendor.pygments.lexers.configs', 'Desktop file', ('desktop',), ('*.desktop',), ('application/x-desktop',)),
    'DevicetreeLexer': ('pip._vendor.pygments.lexers.devicetree', 'Devicetree', ('devicetree', 'dts'), ('*.dts', '*.dtsi'), ('text/x-c',)),
    'DgLexer': ('pip._vendor.pygments.lexers.python', 'dg', ('dg',), ('*.dg',), ('text/x-dg',)),
    'DiffLexer': ('pip._vendor.pygments.lexers.diff', 'Diff', ('diff', 'udiff'), ('*.diff', '*.patch'), ('text/x-diff', 'text/x-patch')),
    'DjangoLexer': ('pip._vendor.pygments.lexers.templates', 'Django/Jinja', ('django', 'jinja'), (), ('application/x-django-templating', 'application/x-jinja')),
    'DnsZoneLexer': ('pip._vendor.pygments.lexers.dns', 'Zone', ('zone',), ('*.zone',), ('text/dns',)),
    'DockerLexer': ('pip._vendor.pygments.lexers.configs', 'Docker', ('docker', 'dockerfile'), ('Dockerfile', '*.docker'), ('text/x-dockerfile-config',)),
    'DtdLexer': ('pip._vendor.pygments.lexers.html', 'DTD', ('dtd',), ('*.dtd',), ('application/xml-dtd',)),
    'DuelLexer': ('pip._vendor.pygments.lexers.webmisc', 'Duel', ('duel', 'jbst', 'jsonml+bst'), ('*.duel', '*.jbst'), ('text/x-duel', 'text/x-jbst')),
    'DylanConsoleLexer': ('pip._vendor.pygments.lexers.dylan', 'Dylan session', ('dylan-console', 'dylan-repl'), ('*.dylan-console',), ('text/x-dylan-console',)),
    'DylanLexer': ('pip._vendor.pygments.lexers.dylan', 'Dylan', ('dylan',), ('*.dylan', '*.dyl', '*.intr'), ('text/x-dylan',)),
    'DylanLidLexer': ('pip._vendor.pygments.lexers.dylan', 'DylanLID', ('dylan-lid', 'lid'), ('*.lid', '*.hdp'), ('text/x-dylan-lid',)),
    'ECLLexer': ('pip._vendor.pygments.lexers.ecl', 'ECL', ('ecl',), ('*.ecl',), ('application/x-ecl',)),
    'ECLexer': ('pip._vendor.pygments.lexers.c_like', 'eC', ('ec',), ('*.ec', '*.eh'), ('text/x-echdr', 'text/x-ecsrc')),
    'EarlGreyLexer': ('pip._vendor.pygments.lexers.javascript', 'Earl Grey', ('earl-grey', 'earlgrey', 'eg'), ('*.eg',), ('text/x-earl-grey',)),
    'EasytrieveLexer': ('pip._vendor.pygments.lexers.scripting', 'Easytrieve', ('easytrieve',), ('*.ezt', '*.mac'), ('text/x-easytrieve',)),
    'EbnfLexer': ('pip._vendor.pygments.lexers.parsers', 'EBNF', ('ebnf',), ('*.ebnf',), ('text/x-ebnf',)),
    'EiffelLexer': ('pip._vendor.pygments.lexers.eiffel', 'Eiffel', ('eiffel',), ('*.e',), ('text/x-eiffel',)),
    'ElixirConsoleLexer': ('pip._vendor.pygments.lexers.erlang', 'Elixir iex session', ('iex',), (), ('text/x-elixir-shellsession',)),
    'ElixirLexer': ('pip._vendor.pygments.lexers.erlang', 'Elixir', ('elixir', 'ex', 'exs'), ('*.ex', '*.eex', '*.exs', '*.leex'), ('text/x-elixir',)),
    'ElmLexer': ('pip._vendor.pygments.lexers.elm', 'Elm', ('elm',), ('*.elm',), ('text/x-elm',)),
    'ElpiLexer': ('pip._vendor.pygments.lexers.elpi', 'Elpi', ('elpi',), ('*.elpi',), ('text/x-elpi',)),
    'EmacsLispLexer': ('pip._vendor.pygments.lexers.lisp', 'EmacsLisp', ('emacs-lisp', 'elisp', 'emacs'), ('*.el',), ('text/x-elisp', 'application/x-elisp')),
    'EmailLexer': ('pip._vendor.pygments.lexers.email', 'E-mail', ('email', 'eml'), ('*.eml',), ('message/rfc822',)),
    'ErbLexer': ('pip._vendor.pygments.lexers.templates', 'ERB', ('erb',), (), ('application/x-ruby-templating',)),
    'ErlangLexer': ('pip._vendor.pygments.lexers.erlang', 'Erlang', ('erlang',), ('*.erl', '*.hrl', '*.es', '*.escript'), ('text/x-erlang',)),
    'ErlangShellLexer': ('pip._vendor.pygments.lexers.erlang', 'Erlang erl session', ('erl',), ('*.erl-sh',), ('text/x-erl-shellsession',)),
    'EvoqueHtmlLexer': ('pip._vendor.pygments.lexers.templates', 'HTML+Evoque', ('html+evoque',), ('*.html',), ('text/html+evoque',)),
    'EvoqueLexer': ('pip._vendor.pygments.lexers.templates', 'Evoque', ('evoque',), ('*.evoque',), ('application/x-evoque',)),
    'EvoqueXmlLexer': ('pip._vendor.pygments.lexers.templates', 'XML+Evoque', ('xml+evoque',), ('*.xml',), ('application/xml+evoque',)),
    'ExeclineLexer': ('pip._vendor.pygments.lexers.shell', 'execline', ('execline',), ('*.exec',), ()),
    'EzhilLexer': ('pip._vendor.pygments.lexers.ezhil', 'Ezhil', ('ezhil',), ('*.n',), ('text/x-ezhil',)),
    'FSharpLexer': ('pip._vendor.pygments.lexers.dotnet', 'F#', ('fsharp', 'f#'), ('*.fs', '*.fsi', '*.fsx'), ('text/x-fsharp',)),
    'FStarLexer': ('pip._vendor.pygments.lexers.ml', 'FStar', ('fstar',), ('*.fst', '*.fsti'), ('text/x-fstar',)),
    'FactorLexer': ('pip._vendor.pygments.lexers.factor', 'Factor', ('factor',), ('*.factor',), ('text/x-factor',)),
    'FancyLexer': ('pip._vendor.pygments.lexers.ruby', 'Fancy', ('fancy', 'fy'), ('*.fy', '*.fancypack'), ('text/x-fancysrc',)),
    'FantomLexer': ('pip._vendor.pygments.lexers.fantom', 'Fantom', ('fan',), ('*.fan',), ('application/x-fantom',)),
    'FelixLexer': ('pip._vendor.pygments.lexers.felix', 'Felix', ('felix', 'flx'), ('*.flx', '*.flxh'), ('text/x-felix',)),
    'FennelLexer': ('pip._vendor.pygments.lexers.lisp', 'Fennel', ('fennel', 'fnl'), ('*.fnl',), ()),
    'FiftLexer': ('pip._vendor.pygments.lexers.fift', 'Fift', ('fift', 'fif'), ('*.fif',), ()),
    'FishShellLexer': ('pip._vendor.pygments.lexers.shell', 'Fish', ('fish', 'fishshell'), ('*.fish', '*.load'), ('application/x-fish',)),
    'FlatlineLexer': ('pip._vendor.pygments.lexers.dsls', 'Flatline', ('flatline',), (), ('text/x-flatline',)),
    'FloScriptLexer': ('pip._vendor.pygments.lexers.floscript', 'FloScript', ('floscript', 'flo'), ('*.flo',), ()),
    'ForthLexer': ('pip._vendor.pygments.lexers.forth', 'Forth', ('forth',), ('*.frt', '*.fs'), ('application/x-forth',)),
    'FortranFixedLexer': ('pip._vendor.pygments.lexers.fortran', 'FortranFixed', ('fortranfixed',), ('*.f', '*.F'), ()),
    'FortranLexer': ('pip._vendor.pygments.lexers.fortran', 'Fortran', ('fortran', 'f90'), ('*.f03', '*.f90', '*.F03', '*.F90'), ('text/x-fortran',)),
    'FoxProLexer': ('pip._vendor.pygments.lexers.foxpro', 'FoxPro', ('foxpro', 'vfp', 'clipper', 'xbase'), ('*.PRG', '*.prg'), ()),
    'FreeFemLexer': ('pip._vendor.pygments.lexers.freefem', 'Freefem', ('freefem',), ('*.edp',), ('text/x-freefem',)),
    'FuncLexer': ('pip._vendor.pygments.lexers.func', 'FunC', ('func', 'fc'), ('*.fc', '*.func'), ()),
    'FutharkLexer': ('pip._vendor.pygments.lexers.futhark', 'Futhark', ('futhark',), ('*.fut',), ('text/x-futhark',)),
    'GAPConsoleLexer': ('pip._vendor.pygments.lexers.algebra', 'GAP session', ('gap-console', 'gap-repl'), ('*.tst',), ()),
    'GAPLexer': ('pip._vendor.pygments.lexers.algebra', 'GAP', ('gap',), ('*.g', '*.gd', '*.gi', '*.gap'), ()),
    'GDScriptLexer': ('pip._vendor.pygments.lexers.gdscript', 'GDScript', ('gdscript', 'gd'), ('*.gd',), ('text/x-gdscript', 'application/x-gdscript')),
    'GLShaderLexer': ('pip._vendor.pygments.lexers.graphics', 'GLSL', ('glsl',), ('*.vert', '*.frag', '*.geo'), ('text/x-glslsrc',)),
    'GSQLLexer': ('pip._vendor.pygments.lexers.gsql', 'GSQL', ('gsql',), ('*.gsql',), ()),
    'GasLexer': ('pip._vendor.pygments.lexers.asm', 'GAS', ('gas', 'asm'), ('*.s', '*.S'), ('text/x-gas',)),
    'GcodeLexer': ('pip._vendor.pygments.lexers.gcodelexer', 'g-code', ('gcode',), ('*.gcode',), ()),
    'GenshiLexer': ('pip._vendor.pygments.lexers.templates', 'Genshi', ('genshi', 'kid', 'xml+genshi', 'xml+kid'), ('*.kid',), ('application/x-genshi', 'application/x-kid')),
    'GenshiTextLexer': ('pip._vendor.pygments.lexers.templates', 'Genshi Text', ('genshitext',), (), ('application/x-genshi-text', 'text/x-genshi')),
    'GettextLexer': ('pip._vendor.pygments.lexers.textfmts', 'Gettext Catalog', ('pot', 'po'), ('*.pot', '*.po'), ('application/x-gettext', 'text/x-gettext', 'text/gettext')),
    'GherkinLexer': ('pip._vendor.pygments.lexers.testing', 'Gherkin', ('gherkin', 'cucumber'), ('*.feature',), ('text/x-gherkin',)),
    'GnuplotLexer': ('pip._vendor.pygments.lexers.graphics', 'Gnuplot', ('gnuplot',), ('*.plot', '*.plt'), ('text/x-gnuplot',)),
    'GoLexer': ('pip._vendor.pygments.lexers.go', 'Go', ('go', 'golang'), ('*.go',), ('text/x-gosrc',)),
    'GoloLexer': ('pip._vendor.pygments.lexers.jvm', 'Golo', ('golo',), ('*.golo',), ()),
    'GoodDataCLLexer': ('pip._vendor.pygments.lexers.business', 'GoodData-CL', ('gooddata-cl',), ('*.gdc',), ('text/x-gooddata-cl',)),
    'GosuLexer': ('pip._vendor.pygments.lexers.jvm', 'Gosu', ('gosu',), ('*.gs', '*.gsx', '*.gsp', '*.vark'), ('text/x-gosu',)),
    'GosuTemplateLexer': ('pip._vendor.pygments.lexers.jvm', 'Gosu Template', ('gst',), ('*.gst',), ('text/x-gosu-template',)),
    'GraphQLLexer': ('pip._vendor.pygments.lexers.graphql', 'GraphQL', ('graphql',), ('*.graphql',), ()),
    'GraphvizLexer': ('pip._vendor.pygments.lexers.graphviz', 'Graphviz', ('graphviz', 'dot'), ('*.gv', '*.dot'), ('text/x-graphviz', 'text/vnd.graphviz')),
    'GroffLexer': ('pip._vendor.pygments.lexers.markup', 'Groff', ('groff', 'nroff', 'man'), ('*.[1-9]', '*.man', '*.1p', '*.3pm'), ('application/x-troff', 'text/troff')),
    'GroovyLexer': ('pip._vendor.pygments.lexers.jvm', 'Groovy', ('groovy',), ('*.groovy', '*.gradle'), ('text/x-groovy',)),
    'HLSLShaderLexer': ('pip._vendor.pygments.lexers.graphics', 'HLSL', ('hlsl',), ('*.hlsl', '*.hlsli'), ('text/x-hlsl',)),
    'HTMLUL4Lexer': ('pip._vendor.pygments.lexers.ul4', 'HTML+UL4', ('html+ul4',), ('*.htmlul4',), ()),
    'HamlLexer': ('pip._vendor.pygments.lexers.html', 'Haml', ('haml',), ('*.haml',), ('text/x-haml',)),
    'HandlebarsHtmlLexer': ('pip._vendor.pygments.lexers.templates', 'HTML+Handlebars', ('html+handlebars',), ('*.handlebars', '*.hbs'), ('text/html+handlebars', 'text/x-handlebars-template')),
    'HandlebarsLexer': ('pip._vendor.pygments.lexers.templates', 'Handlebars', ('handlebars',), (), ()),
    'HaskellLexer': ('pip._vendor.pygments.lexers.haskell', 'Haskell', ('haskell', 'hs'), ('*.hs',), ('text/x-haskell',)),
    'HaxeLexer': ('pip._vendor.pygments.lexers.haxe', 'Haxe', ('haxe', 'hxsl', 'hx'), ('*.hx', '*.hxsl'), ('text/haxe', 'text/x-haxe', 'text/x-hx')),
    'HexdumpLexer': ('pip._vendor.pygments.lexers.hexdump', 'Hexdump', ('hexdump',), (), ()),
    'HsailLexer': ('pip._vendor.pygments.lexers.asm', 'HSAIL', ('hsail', 'hsa'), ('*.hsail',), ('text/x-hsail',)),
    'HspecLexer': ('pip._vendor.pygments.lexers.haskell', 'Hspec', ('hspec',), ('*Spec.hs',), ()),
    'HtmlDjangoLexer': ('pip._vendor.pygments.lexers.templates', 'HTML+Django/Jinja', ('html+django', 'html+jinja', 'htmldjango'), ('*.html.j2', '*.htm.j2', '*.xhtml.j2', '*.html.jinja2', '*.htm.jinja2', '*.xhtml.jinja2'), ('text/html+django', 'text/html+jinja')),
    'HtmlGenshiLexer': ('pip._vendor.pygments.lexers.templates', 'HTML+Genshi', ('html+genshi', 'html+kid'), (), ('text/html+genshi',)),
    'HtmlLexer': ('pip._vendor.pygments.lexers.html', 'HTML', ('html',), ('*.html', '*.htm', '*.xhtml', '*.xslt'), ('text/html', 'application/xhtml+xml')),
    'HtmlPhpLexer': ('pip._vendor.pygments.lexers.templates', 'HTML+PHP', ('html+php',), ('*.phtml',), ('application/x-php', 'application/x-httpd-php', 'application/x-httpd-php3', 'application/x-httpd-php4', 'application/x-httpd-php5')),
    'HtmlSmartyLexer': ('pip._vendor.pygments.lexers.templates', 'HTML+Smarty', ('html+smarty',), (), ('text/html+smarty',)),
    'HttpLexer': ('pip._vendor.pygments.lexers.textfmts', 'HTTP', ('http',), (), ()),
    'HxmlLexer': ('pip._vendor.pygments.lexers.haxe', 'Hxml', ('haxeml', 'hxml'), ('*.hxml',), ()),
    'HyLexer': ('pip._vendor.pygments.lexers.lisp', 'Hy', ('hylang', 'hy'), ('*.hy',), ('text/x-hy', 'application/x-hy')),
    'HybrisLexer': ('pip._vendor.pygments.lexers.scripting', 'Hybris', ('hybris',), ('*.hyb',), ('text/x-hybris', 'application/x-hybris')),
    'IDLLexer': ('pip._vendor.pygments.lexers.idl', 'IDL', ('idl',), ('*.pro',), ('text/idl',)),
    'IconLexer': ('pip._vendor.pygments.lexers.unicon', 'Icon', ('icon',), ('*.icon', '*.ICON'), ()),
    'IdrisLexer': ('pip._vendor.pygments.lexers.haskell', 'Idris', ('idris', 'idr'), ('*.idr',), ('text/x-idris',)),
    'IgorLexer': ('pip._vendor.pygments.lexers.igor', 'Igor', ('igor', 'igorpro'), ('*.ipf',), ('text/ipf',)),
    'Inform6Lexer': ('pip._vendor.pygments.lexers.int_fiction', 'Inform 6', ('inform6', 'i6'), ('*.inf',), ()),
    'Inform6TemplateLexer': ('pip._vendor.pygments.lexers.int_fiction', 'Inform 6 template', ('i6t',), ('*.i6t',), ()),
    'Inform7Lexer': ('pip._vendor.pygments.lexers.int_fiction', 'Inform 7', ('inform7', 'i7'), ('*.ni', '*.i7x'), ()),
    'IniLexer': ('pip._vendor.pygments.lexers.configs', 'INI', ('ini', 'cfg', 'dosini'), ('*.ini', '*.cfg', '*.inf', '.editorconfig'), ('text/x-ini', 'text/inf')),
    'IoLexer': ('pip._vendor.pygments.lexers.iolang', 'Io', ('io',), ('*.io',), ('text/x-iosrc',)),
    'IokeLexer': ('pip._vendor.pygments.lexers.jvm', 'Ioke', ('ioke', 'ik'), ('*.ik',), ('text/x-iokesrc',)),
    'IrcLogsLexer': ('pip._vendor.pygments.lexers.textfmts', 'IRC logs', ('irc',), ('*.weechatlog',), ('text/x-irclog',)),
    'IsabelleLexer': ('pip._vendor.pygments.lexers.theorem', 'Isabelle', ('isabelle',), ('*.thy',), ('text/x-isabelle',)),
    'JLexer': ('pip._vendor.pygments.lexers.j', 'J', ('j',), ('*.ijs',), ('text/x-j',)),
    'JMESPathLexer': ('pip._vendor.pygments.lexers.jmespath', 'JMESPath', ('jmespath', 'jp'), ('*.jp',), ()),
    'JSLTLexer': ('pip._vendor.pygments.lexers.jslt', 'JSLT', ('jslt',), ('*.jslt',), ('text/x-jslt',)),
    'JagsLexer': ('pip._vendor.pygments.lexers.modeling', 'JAGS', ('jags',), ('*.jag', '*.bug'), ()),
    'JanetLexer': ('pip._vendor.pygments.lexers.lisp', 'Janet', ('janet',), ('*.janet', '*.jdn'), ('text/x-janet', 'application/x-janet')),
    'JasminLexer': ('pip._vendor.pygments.lexers.jvm', 'Jasmin', ('jasmin', 'jasminxt'), ('*.j',), ()),
    'JavaLexer': ('pip._vendor.pygments.lexers.jvm', 'Java', ('java',), ('*.java',), ('text/x-java',)),
    'JavascriptDjangoLexer': ('pip._vendor.pygments.lexers.templates', 'JavaScript+Django/Jinja', ('javascript+django', 'js+django', 'javascript+jinja', 'js+jinja'), ('*.js.j2', '*.js.jinja2'), ('application/x-javascript+django', 'application/x-javascript+jinja', 'text/x-javascript+django', 'text/x-javascript+jinja', 'text/javascript+django', 'text/javascript+jinja')),
    'JavascriptErbLexer': ('pip._vendor.pygments.lexers.templates', 'JavaScript+Ruby', ('javascript+ruby', 'js+ruby', 'javascript+erb', 'js+erb'), (), ('application/x-javascript+ruby', 'text/x-javascript+ruby', 'text/javascript+ruby')),
    'JavascriptGenshiLexer': ('pip._vendor.pygments.lexers.templates', 'JavaScript+Genshi Text', ('js+genshitext', 'js+genshi', 'javascript+genshitext', 'javascript+genshi'), (), ('application/x-javascript+genshi', 'text/x-javascript+genshi', 'text/javascript+genshi')),
    'JavascriptLexer': ('pip._vendor.pygments.lexers.javascript', 'JavaScript', ('javascript', 'js'), ('*.js', '*.jsm', '*.mjs', '*.cjs'), ('application/javascript', 'application/x-javascript', 'text/x-javascript', 'text/javascript')),
    'JavascriptPhpLexer': ('pip._vendor.pygments.lexers.templates', 'JavaScript+PHP', ('javascript+php', 'js+php'), (), ('application/x-javascript+php', 'text/x-javascript+php', 'text/javascript+php')),
    'JavascriptSmartyLexer': ('pip._vendor.pygments.lexers.templates', 'JavaScript+Smarty', ('javascript+smarty', 'js+smarty'), (), ('application/x-javascript+smarty', 'text/x-javascript+smarty', 'text/javascript+smarty')),
    'JavascriptUL4Lexer': ('pip._vendor.pygments.lexers.ul4', 'Javascript+UL4', ('js+ul4',), ('*.jsul4',), ()),
    'JclLexer': ('pip._vendor.pygments.lexers.scripting', 'JCL', ('jcl',), ('*.jcl',), ('text/x-jcl',)),
    'JsgfLexer': ('pip._vendor.pygments.lexers.grammar_notation', 'JSGF', ('jsgf',), ('*.jsgf',), ('application/jsgf', 'application/x-jsgf', 'text/jsgf')),
    'JsonBareObjectLexer': ('pip._vendor.pygments.lexers.data', 'JSONBareObject', (), (), ()),
    'JsonLdLexer': ('pip._vendor.pygments.lexers.data', 'JSON-LD', ('jsonld', 'json-ld'), ('*.jsonld',), ('application/ld+json',)),
    'JsonLexer': ('pip._vendor.pygments.lexers.data', 'JSON', ('json', 'json-object'), ('*.json', '*.jsonl', '*.ndjson', 'Pipfile.lock'), ('application/json', 'application/json-object', 'application/x-ndjson', 'application/jsonl', 'application/json-seq')),
    'JsonnetLexer': ('pip._vendor.pygments.lexers.jsonnet', 'Jsonnet', ('jsonnet',), ('*.jsonnet', '*.libsonnet'), ()),
    'JspLexer': ('pip._vendor.pygments.lexers.templates', 'Java Server Page', ('jsp',), ('*.jsp',), ('application/x-jsp',)),
    'JsxLexer': ('pip._vendor.pygments.lexers.jsx', 'JSX', ('jsx', 'react'), ('*.jsx', '*.react'), ('text/jsx', 'text/typescript-jsx')),
    'JuliaConsoleLexer': ('pip._vendor.pygments.lexers.julia', 'Julia console', ('jlcon', 'julia-repl'), (), ()),
    'JuliaLexer': ('pip._vendor.pygments.lexers.julia', 'Julia', ('julia', 'jl'), ('*.jl',), ('text/x-julia', 'application/x-julia')),
    'JuttleLexer': ('pip._vendor.pygments.lexers.javascript', 'Juttle', ('juttle',), ('*.juttle',), ('application/juttle', 'application/x-juttle', 'text/x-juttle', 'text/juttle')),
    'KLexer': ('pip._vendor.pygments.lexers.q', 'K', ('k',), ('*.k',), ()),
    'KalLexer': ('pip._vendor.pygments.lexers.javascript', 'Kal', ('kal',), ('*.kal',), ('text/kal', 'application/kal')),
    'KconfigLexer': ('pip._vendor.pygments.lexers.configs', 'Kconfig', ('kconfig', 'menuconfig', 'linux-config', 'kernel-config'), ('Kconfig*', '*Config.in*', 'external.in*', 'standard-modules.in'), ('text/x-kconfig',)),
    'KernelLogLexer': ('pip._vendor.pygments.lexers.textfmts', 'Kernel log', ('kmsg', 'dmesg'), ('*.kmsg', '*.dmesg'), ()),
    'KokaLexer': ('pip._vendor.pygments.lexers.haskell', 'Koka', ('koka',), ('*.kk', '*.kki'), ('text/x-koka',)),
    'KotlinLexer': ('pip._vendor.pygments.lexers.jvm', 'Kotlin', ('kotlin',), ('*.kt', '*.kts'), ('text/x-kotlin',)),
    'KuinLexer': ('pip._vendor.pygments.lexers.kuin', 'Kuin', ('kuin',), ('*.kn',), ()),
    'KustoLexer': ('pip._vendor.pygments.lexers.kusto', 'Kusto', ('kql', 'kusto'), ('*.kql', '*.kusto', '.csl'), ()),
    'LSLLexer': ('pip._vendor.pygments.lexers.scripting', 'LSL', ('lsl',), ('*.lsl',), ('text/x-lsl',)),
    'LassoCssLexer': ('pip._vendor.pygments.lexers.templates', 'CSS+Lasso', ('css+lasso',), (), ('text/css+lasso',)),
    'LassoHtmlLexer': ('pip._vendor.pygments.lexers.templates', 'HTML+Lasso', ('html+lasso',), (), ('text/html+lasso', 'application/x-httpd-lasso', 'application/x-httpd-lasso[89]')),
    'LassoJavascriptLexer': ('pip._vendor.pygments.lexers.templates', 'JavaScript+Lasso', ('javascript+lasso', 'js+lasso'), (), ('application/x-javascript+lasso', 'text/x-javascript+lasso', 'text/javascript+lasso')),
    'LassoLexer': ('pip._vendor.pygments.lexers.javascript', 'Lasso', ('lasso', 'lassoscript'), ('*.lasso', '*.lasso[89]'), ('text/x-lasso',)),
    'LassoXmlLexer': ('pip._vendor.pygments.lexers.templates', 'XML+Lasso', ('xml+lasso',), (), ('application/xml+lasso',)),
    'LdaprcLexer': ('pip._vendor.pygments.lexers.ldap', 'LDAP configuration file', ('ldapconf', 'ldaprc'), ('.ldaprc', 'ldaprc', 'ldap.conf'), ('text/x-ldapconf',)),
    'LdifLexer': ('pip._vendor.pygments.lexers.ldap', 'LDIF', ('ldif',), ('*.ldif',), ('text/x-ldif',)),
    'Lean3Lexer': ('pip._vendor.pygments.lexers.lean', 'Lean', ('lean', 'lean3'), ('*.lean',), ('text/x-lean', 'text/x-lean3')),
    'Lean4Lexer': ('pip._vendor.pygments.lexers.lean', 'Lean4', ('lean4',), ('*.lean',), ('text/x-lean4',)),
    'LessCssLexer': ('pip._vendor.pygments.lexers.css', 'LessCss', ('less',), ('*.less',), ('text/x-less-css',)),
    'LighttpdConfLexer': ('pip._vendor.pygments.lexers.configs', 'Lighttpd configuration file', ('lighttpd', 'lighty'), ('lighttpd.conf',), ('text/x-lighttpd-conf',)),
    'LilyPondLexer': ('pip._vendor.pygments.lexers.lilypond', 'LilyPond', ('lilypond',), ('*.ly',), ()),
    'LimboLexer': ('pip._vendor.pygments.lexers.inferno', 'Limbo', ('limbo',), ('*.b',), ('text/limbo',)),
    'LiquidLexer': ('pip._vendor.pygments.lexers.templates', 'liquid', ('liquid',), ('*.liquid',), ()),
    'LiterateAgdaLexer': ('pip._vendor.pygments.lexers.haskell', 'Literate Agda', ('literate-agda', 'lagda'), ('*.lagda',), ('text/x-literate-agda',)),
    'LiterateCryptolLexer': ('pip._vendor.pygments.lexers.haskell', 'Literate Cryptol', ('literate-cryptol', 'lcryptol', 'lcry'), ('*.lcry',), ('text/x-literate-cryptol',)),
    'LiterateHaskellLexer': ('pip._vendor.pygments.lexers.haskell', 'Literate Haskell', ('literate-haskell', 'lhaskell', 'lhs'), ('*.lhs',), ('text/x-literate-haskell',)),
    'LiterateIdrisLexer': ('pip._vendor.pygments.lexers.haskell', 'Literate Idris', ('literate-idris', 'lidris', 'lidr'), ('*.lidr',), ('text/x-literate-idris',)),
    'LiveScriptLexer': ('pip._vendor.pygments.lexers.javascript', 'LiveScript', ('livescript', 'live-script'), ('*.ls',), ('text/livescript',)),
    'LlvmLexer': ('pip._vendor.pygments.lexers.asm', 'LLVM', ('llvm',), ('*.ll',), ('text/x-llvm',)),
    'LlvmMirBodyLexer': ('pip._vendor.pygments.lexers.asm', 'LLVM-MIR Body', ('llvm-mir-body',), (), ()),
    'LlvmMirLexer': ('pip._vendor.pygments.lexers.asm', 'LLVM-MIR', ('llvm-mir',), ('*.mir',), ()),
    'LogosLexer': ('pip._vendor.pygments.lexers.objective', 'Logos', ('logos',), ('*.x', '*.xi', '*.xm', '*.xmi'), ('text/x-logos',)),
    'LogtalkLexer': ('pip._vendor.pygments.lexers.prolog', 'Logtalk', ('logtalk',), ('*.lgt', '*.logtalk'), ('text/x-logtalk',)),
    'LuaLexer': ('pip._vendor.pygments.lexers.scripting', 'Lua', ('lua',), ('*.lua', '*.wlua'), ('text/x-lua', 'application/x-lua')),
    'LuauLexer': ('pip._vendor.pygments.lexers.scripting', 'Luau', ('luau',), ('*.luau',), ()),
    'MCFunctionLexer': ('pip._vendor.pygments.lexers.minecraft', 'MCFunction', ('mcfunction', 'mcf'), ('*.mcfunction',), ('text/mcfunction',)),
    'MCSchemaLexer': ('pip._vendor.pygments.lexers.minecraft', 'MCSchema', ('mcschema',), ('*.mcschema',), ('text/mcschema',)),
    'MIMELexer': ('pip._vendor.pygments.lexers.mime', 'MIME', ('mime',), (), ('multipart/mixed', 'multipart/related', 'multipart/alternative')),
    'MIPSLexer': ('pip._vendor.pygments.lexers.mips', 'MIPS', ('mips',), ('*.mips', '*.MIPS'), ()),
    'MOOCodeLexer': ('pip._vendor.pygments.lexers.scripting', 'MOOCode', ('moocode', 'moo'), ('*.moo',), ('text/x-moocode',)),
    'MSDOSSessionLexer': ('pip._vendor.pygments.lexers.shell', 'MSDOS Session', ('doscon',), (), ()),
    'Macaulay2Lexer': ('pip._vendor.pygments.lexers.macaulay2', 'Macaulay2', ('macaulay2',), ('*.m2',), ()),
    'MakefileLexer': ('pip._vendor.pygments.lexers.make', 'Makefile', ('make', 'makefile', 'mf', 'bsdmake'), ('*.mak', '*.mk', 'Makefile', 'makefile', 'Makefile.*', 'GNUmakefile'), ('text/x-makefile',)),
    'MakoCssLexer': ('pip._vendor.pygments.lexers.templates', 'CSS+Mako', ('css+mako',), (), ('text/css+mako',)),
    'MakoHtmlLexer': ('pip._vendor.pygments.lexers.templates', 'HTML+Mako', ('html+mako',), (), ('text/html+mako',)),
    'MakoJavascriptLexer': ('pip._vendor.pygments.lexers.templates', 'JavaScript+Mako', ('javascript+mako', 'js+mako'), (), ('application/x-javascript+mako', 'text/x-javascript+mako', 'text/javascript+mako')),
    'MakoLexer': ('pip._vendor.pygments.lexers.templates', 'Mako', ('mako',), ('*.mao',), ('application/x-mako',)),
    'MakoXmlLexer': ('pip._vendor.pygments.lexers.templates', 'XML+Mako', ('xml+mako',), (), ('application/xml+mako',)),
    'MaqlLexer': ('pip._vendor.pygments.lexers.business', 'MAQL', ('maql',), ('*.maql',), ('text/x-gooddata-maql', 'application/x-gooddata-maql')),
    'MarkdownLexer': ('pip._vendor.pygments.lexers.markup', 'Markdown', ('markdown', 'md'), ('*.md', '*.markdown'), ('text/x-markdown',)),
    'MaskLexer': ('pip._vendor.pygments.lexers.javascript', 'Mask', ('mask',), ('*.mask',), ('text/x-mask',)),
    'MasonLexer': ('pip._vendor.pygments.lexers.templates', 'Mason', ('mason',), ('*.m', '*.mhtml', '*.mc', '*.mi', 'autohandler', 'dhandler'), ('application/x-mason',)),
    'MathematicaLexer': ('pip._vendor.pygments.lexers.algebra', 'Mathematica', ('mathematica', 'mma', 'nb'), ('*.nb', '*.cdf', '*.nbp', '*.ma'), ('application/mathematica', 'application/vnd.wolfram.mathematica', 'application/vnd.wolfram.mathematica.package', 'application/vnd.wolfram.cdf')),
    'MatlabLexer': ('pip._vendor.pygments.lexers.matlab', 'Matlab', ('matlab',), ('*.m',), ('text/matlab',)),
    'MatlabSessionLexer': ('pip._vendor.pygments.lexers.matlab', 'Matlab session', ('matlabsession',), (), ()),
    'MaximaLexer': ('pip._vendor.pygments.lexers.maxima', 'Maxima', ('maxima', 'macsyma'), ('*.mac', '*.max'), ()),
    'MesonLexer': ('pip._vendor.pygments.lexers.meson', 'Meson', ('meson', 'meson.build'), ('meson.build', 'meson_options.txt'), ('text/x-meson',)),
    'MiniDLexer': ('pip._vendor.pygments.lexers.d', 'MiniD', ('minid',), (), ('text/x-minidsrc',)),
    'MiniScriptLexer': ('pip._vendor.pygments.lexers.scripting', 'MiniScript', ('miniscript', 'ms'), ('*.ms',), ('text/x-minicript', 'application/x-miniscript')),
    'ModelicaLexer': ('pip._vendor.pygments.lexers.modeling', 'Modelica', ('modelica',), ('*.mo',), ('text/x-modelica',)),
    'Modula2Lexer': ('pip._vendor.pygments.lexers.modula2', 'Modula-2', ('modula2', 'm2'), ('*.def', '*.mod'), ('text/x-modula2',)),
    'MoinWikiLexer': ('pip._vendor.pygments.lexers.markup', 'MoinMoin/Trac Wiki markup', ('trac-wiki', 'moin'), (), ('text/x-trac-wiki',)),
    'MojoLexer': ('pip._vendor.pygments.lexers.mojo', 'Mojo', ('mojo', '🔥'), ('*.mojo', '*.🔥'), ('text/x-mojo', 'application/x-mojo')),
    'MonkeyLexer': ('pip._vendor.pygments.lexers.basic', 'Monkey', ('monkey',), ('*.monkey',), ('text/x-monkey',)),
    'MonteLexer': ('pip._vendor.pygments.lexers.monte', 'Monte', ('monte',), ('*.mt',), ()),
    'MoonScriptLexer': ('pip._vendor.pygments.lexers.scripting', 'MoonScript', ('moonscript', 'moon'), ('*.moon',), ('text/x-moonscript', 'application/x-moonscript')),
    'MoselLexer': ('pip._vendor.pygments.lexers.mosel', 'Mosel', ('mosel',), ('*.mos',), ()),
    'MozPreprocCssLexer': ('pip._vendor.pygments.lexers.markup', 'CSS+mozpreproc', ('css+mozpreproc',), ('*.css.in',), ()),
    'MozPreprocHashLexer': ('pip._vendor.pygments.lexers.markup', 'mozhashpreproc', ('mozhashpreproc',), (), ()),
    'MozPreprocJavascriptLexer': ('pip._vendor.pygments.lexers.markup', 'Javascript+mozpreproc', ('javascript+mozpreproc',), ('*.js.in',), ()),
    'MozPreprocPercentLexer': ('pip._vendor.pygments.lexers.markup', 'mozpercentpreproc', ('mozpercentpreproc',), (), ()),
    'MozPreprocXulLexer': ('pip._vendor.pygments.lexers.markup', 'XUL+mozpreproc', ('xul+mozpreproc',), ('*.xul.in',), ()),
    'MqlLexer': ('pip._vendor.pygments.lexers.c_like', 'MQL', ('mql', 'mq4', 'mq5', 'mql4', 'mql5'), ('*.mq4', '*.mq5', '*.mqh'), ('text/x-mql',)),
    'MscgenLexer': ('pip._vendor.pygments.lexers.dsls', 'Mscgen', ('mscgen', 'msc'), ('*.msc',), ()),
    'MuPADLexer': ('pip._vendor.pygments.lexers.algebra', 'MuPAD', ('mupad',), ('*.mu',), ()),
    'MxmlLexer': ('pip._vendor.pygments.lexers.actionscript', 'MXML', ('mxml',), ('*.mxml',), ()),
    'MySqlLexer': ('pip._vendor.pygments.lexers.sql', 'MySQL', ('mysql',), (), ('text/x-mysql',)),
    'MyghtyCssLexer': ('pip._vendor.pygments.lexers.templates', 'CSS+Myghty', ('css+myghty',), (), ('text/css+myghty',)),
    'MyghtyHtmlLexer': ('pip._vendor.pygments.lexers.templates', 'HTML+Myghty', ('html+myghty',), (), ('text/html+myghty',)),
    'MyghtyJavascriptLexer': ('pip._vendor.pygments.lexers.templates', 'JavaScript+Myghty', ('javascript+myghty', 'js+myghty'), (), ('application/x-javascript+myghty', 'text/x-javascript+myghty', 'text/javascript+mygthy')),
    'MyghtyLexer': ('pip._vendor.pygments.lexers.templates', 'Myghty', ('myghty',), ('*.myt', 'autodelegate'), ('application/x-myghty',)),
    'MyghtyXmlLexer': ('pip._vendor.pygments.lexers.templates', 'XML+Myghty', ('xml+myghty',), (), ('application/xml+myghty',)),
    'NCLLexer': ('pip._vendor.pygments.lexers.ncl', 'NCL', ('ncl',), ('*.ncl',), ('text/ncl',)),
    'NSISLexer': ('pip._vendor.pygments.lexers.installers', 'NSIS', ('nsis', 'nsi', 'nsh'), ('*.nsi', '*.nsh'), ('text/x-nsis',)),
    'NasmLexer': ('pip._vendor.pygments.lexers.asm', 'NASM', ('nasm',), ('*.asm', '*.ASM', '*.nasm'), ('text/x-nasm',)),
    'NasmObjdumpLexer': ('pip._vendor.pygments.lexers.asm', 'objdump-nasm', ('objdump-nasm',), ('*.objdump-intel',), ('text/x-nasm-objdump',)),
    'NemerleLexer': ('pip._vendor.pygments.lexers.dotnet', 'Nemerle', ('nemerle',), ('*.n',), ('text/x-nemerle',)),
    'NesCLexer': ('pip._vendor.pygments.lexers.c_like', 'nesC', ('nesc',), ('*.nc',), ('text/x-nescsrc',)),
    'NestedTextLexer': ('pip._vendor.pygments.lexers.configs', 'NestedText', ('nestedtext', 'nt'), ('*.nt',), ()),
    'NewLispLexer': ('pip._vendor.pygments.lexers.lisp', 'NewLisp', ('newlisp',), ('*.lsp', '*.nl', '*.kif'), ('text/x-newlisp', 'application/x-newlisp')),
    'NewspeakLexer': ('pip._vendor.pygments.lexers.smalltalk', 'Newspeak', ('newspeak',), ('*.ns2',), ('text/x-newspeak',)),
    'NginxConfLexer': ('pip._vendor.pygments.lexers.configs', 'Nginx configuration file', ('nginx',), ('nginx.conf',), ('text/x-nginx-conf',)),
    'NimrodLexer': ('pip._vendor.pygments.lexers.nimrod', 'Nimrod', ('nimrod', 'nim'), ('*.nim', '*.nimrod'), ('text/x-nim',)),
    'NitLexer': ('pip._vendor.pygments.lexers.nit', 'Nit', ('nit',), ('*.nit',), ()),
    'NixLexer': ('pip._vendor.pygments.lexers.nix', 'Nix', ('nixos', 'nix'), ('*.nix',), ('text/x-nix',)),
    'NodeConsoleLexer': ('pip._vendor.pygments.lexers.javascript', 'Node.js REPL console session', ('nodejsrepl',), (), ('text/x-nodejsrepl',)),
    'NotmuchLexer': ('pip._vendor.pygments.lexers.textfmts', 'Notmuch', ('notmuch',), (), ()),
    'NuSMVLexer': ('pip._vendor.pygments.lexers.smv', 'NuSMV', ('nusmv',), ('*.smv',), ()),
    'NumPyLexer': ('pip._vendor.pygments.lexers.python', 'NumPy', ('numpy',), (), ()),
    'ObjdumpLexer': ('pip._vendor.pygments.lexers.asm', 'objdump', ('objdump',), ('*.objdump',), ('text/x-objdump',)),
    'ObjectiveCLexer': ('pip._vendor.pygments.lexers.objective', 'Objective-C', ('objective-c', 'objectivec', 'obj-c', 'objc'), ('*.m', '*.h'), ('text/x-objective-c',)),
    'ObjectiveCppLexer': ('pip._vendor.pygments.lexers.objective', 'Objective-C++', ('objective-c++', 'objectivec++', 'obj-c++', 'objc++'), ('*.mm', '*.hh'), ('text/x-objective-c++',)),
    'ObjectiveJLexer': ('pip._vendor.pygments.lexers.javascript', 'Objective-J', ('objective-j', 'objectivej', 'obj-j', 'objj'), ('*.j',), ('text/x-objective-j',)),
    'OcamlLexer': ('pip._vendor.pygments.lexers.ml', 'OCaml', ('ocaml',), ('*.ml', '*.mli', '*.mll', '*.mly'), ('text/x-ocaml',)),
    'OctaveLexer': ('pip._vendor.pygments.lexers.matlab', 'Octave', ('octave',), ('*.m',), ('text/octave',)),
    'OdinLexer': ('pip._vendor.pygments.lexers.archetype', 'ODIN', ('odin',), ('*.odin',), ('text/odin',)),
    'OmgIdlLexer': ('pip._vendor.pygments.lexers.c_like', 'OMG Interface Definition Language', ('omg-idl',), ('*.idl', '*.pidl'), ()),
    'OocLexer': ('pip._vendor.pygments.lexers.ooc', 'Ooc', ('ooc',), ('*.ooc',), ('text/x-ooc',)),
    'OpaLexer': ('pip._vendor.pygments.lexers.ml', 'Opa', ('opa',), ('*.opa',), ('text/x-opa',)),
    'OpenEdgeLexer': ('pip._vendor.pygments.lexers.business', 'OpenEdge ABL', ('openedge', 'abl', 'progress'), ('*.p', '*.cls'), ('text/x-openedge', 'application/x-openedge')),
    'OpenScadLexer': ('pip._vendor.pygments.lexers.openscad', 'OpenSCAD', ('openscad',), ('*.scad',), ('application/x-openscad',)),
    'OrgLexer': ('pip._vendor.pygments.lexers.markup', 'Org Mode', ('org', 'orgmode', 'org-mode'), ('*.org',), ('text/org',)),
    'OutputLexer': ('pip._vendor.pygments.lexers.special', 'Text output', ('output',), (), ()),
    'PacmanConfLexer': ('pip._vendor.pygments.lexers.configs', 'PacmanConf', ('pacmanconf',), ('pacman.conf',), ()),
    'PanLexer': ('pip._vendor.pygments.lexers.dsls', 'Pan', ('pan',), ('*.pan',), ()),
    'ParaSailLexer': ('pip._vendor.pygments.lexers.parasail', 'ParaSail', ('parasail',), ('*.psi', '*.psl'), ('text/x-parasail',)),
    'PawnLexer': ('pip._vendor.pygments.lexers.pawn', 'Pawn', ('pawn',), ('*.p', '*.pwn', '*.inc'), ('text/x-pawn',)),
    'PegLexer': ('pip._vendor.pygments.lexers.grammar_notation', 'PEG', ('peg',), ('*.peg',), ('text/x-peg',)),
    'Perl6Lexer': ('pip._vendor.pygments.lexers.perl', 'Perl6', ('perl6', 'pl6', 'raku'), ('*.pl', '*.pm', '*.nqp', '*.p6', '*.6pl', '*.p6l', '*.pl6', '*.6pm', '*.p6m', '*.pm6', '*.t', '*.raku', '*.rakumod', '*.rakutest', '*.rakudoc'), ('text/x-perl6', 'application/x-perl6')),
    'PerlLexer': ('pip._vendor.pygments.lexers.perl', 'Perl', ('perl', 'pl'), ('*.pl', '*.pm', '*.t', '*.perl'), ('text/x-perl', 'application/x-perl')),
    'PhixLexer': ('pip._vendor.pygments.lexers.phix', 'Phix', ('phix',), ('*.exw',), ('text/x-phix',)),
    'PhpLexer': ('pip._vendor.pygments.lexers.php', 'PHP', ('php', 'php3', 'php4', 'php5'), ('*.php', '*.php[345]', '*.inc'), ('text/x-php',)),
    'PigLexer': ('pip._vendor.pygments.lexers.jvm', 'Pig', ('pig',), ('*.pig',), ('text/x-pig',)),
    'PikeLexer': ('pip._vendor.pygments.lexers.c_like', 'Pike', ('pike',), ('*.pike', '*.pmod'), ('text/x-pike',)),
    'PkgConfigLexer': ('pip._vendor.pygments.lexers.configs', 'PkgConfig', ('pkgconfig',), ('*.pc',), ()),
    'PlPgsqlLexer': ('pip._vendor.pygments.lexers.sql', 'PL/pgSQL', ('plpgsql',), (), ('text/x-plpgsql',)),
    'PointlessLexer': ('pip._vendor.pygments.lexers.pointless', 'Pointless', ('pointless',), ('*.ptls',), ()),
    'PonyLexer': ('pip._vendor.pygments.lexers.pony', 'Pony', ('pony',), ('*.pony',), ()),
    'PortugolLexer': ('pip._vendor.pygments.lexers.pascal', 'Portugol', ('portugol',), ('*.alg', '*.portugol'), ()),
    'PostScriptLexer': ('pip._vendor.pygments.lexers.graphics', 'PostScript', ('postscript', 'postscr'), ('*.ps', '*.eps'), ('application/postscript',)),
    'PostgresConsoleLexer': ('pip._vendor.pygments.lexers.sql', 'PostgreSQL console (psql)', ('psql', 'postgresql-console', 'postgres-console'), (), ('text/x-postgresql-psql',)),
    'PostgresExplainLexer': ('pip._vendor.pygments.lexers.sql', 'PostgreSQL EXPLAIN dialect', ('postgres-explain',), ('*.explain',), ('text/x-postgresql-explain',)),
    'PostgresLexer': ('pip._vendor.pygments.lexers.sql', 'PostgreSQL SQL dialect', ('postgresql', 'postgres'), (), ('text/x-postgresql',)),
    'PovrayLexer': ('pip._vendor.pygments.lexers.graphics', 'POVRay', ('pov',), ('*.pov', '*.inc'), ('text/x-povray',)),
    'PowerShellLexer': ('pip._vendor.pygments.lexers.shell', 'PowerShell', ('powershell', 'pwsh', 'posh', 'ps1', 'psm1'), ('*.ps1', '*.psm1'), ('text/x-powershell',)),
    'PowerShellSessionLexer': ('pip._vendor.pygments.lexers.shell', 'PowerShell Session', ('pwsh-session', 'ps1con'), (), ()),
    'PraatLexer': ('pip._vendor.pygments.lexers.praat', 'Praat', ('praat',), ('*.praat', '*.proc', '*.psc'), ()),
    'ProcfileLexer': ('pip._vendor.pygments.lexers.procfile', 'Procfile', ('procfile',), ('Procfile',), ()),
    'PrologLexer': ('pip._vendor.pygments.lexers.prolog', 'Prolog', ('prolog',), ('*.ecl', '*.prolog', '*.pro', '*.pl'), ('text/x-prolog',)),
    'PromQLLexer': ('pip._vendor.pygments.lexers.promql', 'PromQL', ('promql',), ('*.promql',), ()),
    'PromelaLexer': ('pip._vendor.pygments.lexers.c_like', 'Promela', ('promela',), ('*.pml', '*.prom', '*.prm', '*.promela', '*.pr', '*.pm'), ('text/x-promela',)),
    'PropertiesLexer': ('pip._vendor.pygments.lexers.configs', 'Properties', ('properties', 'jproperties'), ('*.properties',), ('text/x-java-properties',)),
    'ProtoBufLexer': ('pip._vendor.pygments.lexers.dsls', 'Protocol Buffer', ('protobuf', 'proto'), ('*.proto',), ()),
    'PrqlLexer': ('pip._vendor.pygments.lexers.prql', 'PRQL', ('prql',), ('*.prql',), ('application/prql', 'application/x-prql')),
    'PsyshConsoleLexer': ('pip._vendor.pygments.lexers.php', 'PsySH console session for PHP', ('psysh',), (), ()),
    'PtxLexer': ('pip._vendor.pygments.lexers.ptx', 'PTX', ('ptx',), ('*.ptx',), ('text/x-ptx',)),
    'PugLexer': ('pip._vendor.pygments.lexers.html', 'Pug', ('pug', 'jade'), ('*.pug', '*.jade'), ('text/x-pug', 'text/x-jade')),
    'PuppetLexer': ('pip._vendor.pygments.lexers.dsls', 'Puppet', ('puppet',), ('*.pp',), ()),
    'PyPyLogLexer': ('pip._vendor.pygments.lexers.console', 'PyPy Log', ('pypylog', 'pypy'), ('*.pypylog',), ('application/x-pypylog',)),
    'Python2Lexer': ('pip._vendor.pygments.lexers.python', 'Python 2.x', ('python2', 'py2'), (), ('text/x-python2', 'application/x-python2')),
    'Python2TracebackLexer': ('pip._vendor.pygments.lexers.python', 'Python 2.x Traceback', ('py2tb',), ('*.py2tb',), ('text/x-python2-traceback',)),
    'PythonConsoleLexer': ('pip._vendor.pygments.lexers.python', 'Python console session', ('pycon', 'python-console'), (), ('text/x-python-doctest',)),
    'PythonLexer': ('pip._vendor.pygments.lexers.python', 'Python', ('python', 'py', 'sage', 'python3', 'py3', 'bazel', 'starlark'), ('*.py', '*.pyw', '*.pyi', '*.jy', '*.sage', '*.sc', 'SConstruct', 'SConscript', '*.bzl', 'BUCK', 'BUILD', 'BUILD.bazel', 'WORKSPACE', '*.tac'), ('text/x-python', 'application/x-python', 'text/x-python3', 'application/x-python3')),
    'PythonTracebackLexer': ('pip._vendor.pygments.lexers.python', 'Python Traceback', ('pytb', 'py3tb'), ('*.pytb', '*.py3tb'), ('text/x-python-traceback', 'text/x-python3-traceback')),
    'PythonUL4Lexer': ('pip._vendor.pygments.lexers.ul4', 'Python+UL4', ('py+ul4',), ('*.pyul4',), ()),
    'QBasicLexer': ('pip._vendor.pygments.lexers.basic', 'QBasic', ('qbasic', 'basic'), ('*.BAS', '*.bas'), ('text/basic',)),
    'QLexer': ('pip._vendor.pygments.lexers.q', 'Q', ('q',), ('*.q',), ()),
    'QVToLexer': ('pip._vendor.pygments.lexers.qvt', 'QVTO', ('qvto', 'qvt'), ('*.qvto',), ()),
    'QlikLexer': ('pip._vendor.pygments.lexers.qlik', 'Qlik', ('qlik', 'qlikview', 'qliksense', 'qlikscript'), ('*.qvs', '*.qvw'), ()),
    'QmlLexer': ('pip._vendor.pygments.lexers.webmisc', 'QML', ('qml', 'qbs'), ('*.qml', '*.qbs'), ('application/x-qml', 'application/x-qt.qbs+qml')),
    'RConsoleLexer': ('pip._vendor.pygments.lexers.r', 'RConsole', ('rconsole', 'rout'), ('*.Rout',), ()),
    'RNCCompactLexer': ('pip._vendor.pygments.lexers.rnc', 'Relax-NG Compact', ('rng-compact', 'rnc'), ('*.rnc',), ()),
    'RPMSpecLexer': ('pip._vendor.pygments.lexers.installers', 'RPMSpec', ('spec',), ('*.spec',), ('text/x-rpm-spec',)),
    'RacketLexer': ('pip._vendor.pygments.lexers.lisp', 'Racket', ('racket', 'rkt'), ('*.rkt', '*.rktd', '*.rktl'), ('text/x-racket', 'application/x-racket')),
    'RagelCLexer': ('pip._vendor.pygments.lexers.parsers', 'Ragel in C Host', ('ragel-c',), ('*.rl',), ()),
    'RagelCppLexer': ('pip._vendor.pygments.lexers.parsers', 'Ragel in CPP Host', ('ragel-cpp',), ('*.rl',), ()),
    'RagelDLexer': ('pip._vendor.pygments.lexers.parsers', 'Ragel in D Host', ('ragel-d',), ('*.rl',), ()),
    'RagelEmbeddedLexer': ('pip._vendor.pygments.lexers.parsers', 'Embedded Ragel', ('ragel-em',), ('*.rl',), ()),
    'RagelJavaLexer': ('pip._vendor.pygments.lexers.parsers', 'Ragel in Java Host', ('ragel-java',), ('*.rl',), ()),
    'RagelLexer': ('pip._vendor.pygments.lexers.parsers', 'Ragel', ('ragel',), (), ()),
    'RagelObjectiveCLexer': ('pip._vendor.pygments.lexers.parsers', 'Ragel in Objective C Host', ('ragel-objc',), ('*.rl',), ()),
    'RagelRubyLexer': ('pip._vendor.pygments.lexers.parsers', 'Ragel in Ruby Host', ('ragel-ruby', 'ragel-rb'), ('*.rl',), ()),
    'RawTokenLexer': ('pip._vendor.pygments.lexers.special', 'Raw token data', (), (), ('application/x-pygments-tokens',)),
    'RdLexer': ('pip._vendor.pygments.lexers.r', 'Rd', ('rd',), ('*.Rd',), ('text/x-r-doc',)),
    'ReasonLexer': ('pip._vendor.pygments.lexers.ml', 'ReasonML', ('reasonml', 'reason'), ('*.re', '*.rei'), ('text/x-reasonml',)),
    'RebolLexer': ('pip._vendor.pygments.lexers.rebol', 'REBOL', ('rebol',), ('*.r', '*.r3', '*.reb'), ('text/x-rebol',)),
    'RedLexer': ('pip._vendor.pygments.lexers.rebol', 'Red', ('red', 'red/system'), ('*.red', '*.reds'), ('text/x-red', 'text/x-red-system')),
    'RedcodeLexer': ('pip._vendor.pygments.lexers.esoteric', 'Redcode', ('redcode',), ('*.cw',), ()),
    'RegeditLexer': ('pip._vendor.pygments.lexers.configs', 'reg', ('registry',), ('*.reg',), ('text/x-windows-registry',)),
    'ResourceLexer': ('pip._vendor.pygments.lexers.resource', 'ResourceBundle', ('resourcebundle', 'resource'), (), ()),
    'RexxLexer': ('pip._vendor.pygments.lexers.scripting', 'Rexx', ('rexx', 'arexx'), ('*.rexx', '*.rex', '*.rx', '*.arexx'), ('text/x-rexx',)),
    'RhtmlLexer': ('pip._vendor.pygments.lexers.templates', 'RHTML', ('rhtml', 'html+erb', 'html+ruby'), ('*.rhtml',), ('text/html+ruby',)),
    'RideLexer': ('pip._vendor.pygments.lexers.ride', 'Ride', ('ride',), ('*.ride',), ('text/x-ride',)),
    'RitaLexer': ('pip._vendor.pygments.lexers.rita', 'Rita', ('rita',), ('*.rita',), ('text/rita',)),
    'RoboconfGraphLexer': ('pip._vendor.pygments.lexers.roboconf', 'Roboconf Graph', ('roboconf-graph',), ('*.graph',), ()),
    'RoboconfInstancesLexer': ('pip._vendor.pygments.lexers.roboconf', 'Roboconf Instances', ('roboconf-instances',), ('*.instances',), ()),
    'RobotFrameworkLexer': ('pip._vendor.pygments.lexers.robotframework', 'RobotFramework', ('robotframework',), ('*.robot', '*.resource'), ('text/x-robotframework',)),
    'RqlLexer': ('pip._vendor.pygments.lexers.sql', 'RQL', ('rql',), ('*.rql',), ('text/x-rql',)),
    'RslLexer': ('pip._vendor.pygments.lexers.dsls', 'RSL', ('rsl',), ('*.rsl',), ('text/rsl',)),
    'RstLexer': ('pip._vendor.pygments.lexers.markup', 'reStructuredText', ('restructuredtext', 'rst', 'rest'), ('*.rst', '*.rest'), ('text/x-rst', 'text/prs.fallenstein.rst')),
    'RtsLexer': ('pip._vendor.pygments.lexers.trafficscript', 'TrafficScript', ('trafficscript', 'rts'), ('*.rts',), ()),
    'RubyConsoleLexer': ('pip._vendor.pygments.lexers.ruby', 'Ruby irb session', ('rbcon', 'irb'), (), ('text/x-ruby-shellsession',)),
    'RubyLexer': ('pip._vendor.pygments.lexers.ruby', 'Ruby', ('ruby', 'rb', 'duby'), ('*.rb', '*.rbw', 'Rakefile', '*.rake', '*.gemspec', '*.rbx', '*.duby', 'Gemfile', 'Vagrantfile'), ('text/x-ruby', 'application/x-ruby')),
    'RustLexer': ('pip._vendor.pygments.lexers.rust', 'Rust', ('rust', 'rs'), ('*.rs', '*.rs.in'), ('text/rust', 'text/x-rust')),
    'SASLexer': ('pip._vendor.pygments.lexers.sas', 'SAS', ('sas',), ('*.SAS', '*.sas'), ('text/x-sas', 'text/sas', 'application/x-sas')),
    'SLexer': ('pip._vendor.pygments.lexers.r', 'S', ('splus', 's', 'r'), ('*.S', '*.R', '.Rhistory', '.Rprofile', '.Renviron'), ('text/S-plus', 'text/S', 'text/x-r-source', 'text/x-r', 'text/x-R', 'text/x-r-history', 'text/x-r-profile')),
    'SMLLexer': ('pip._vendor.pygments.lexers.ml', 'Standard ML', ('sml',), ('*.sml', '*.sig', '*.fun'), ('text/x-standardml', 'application/x-standardml')),
    'SNBTLexer': ('pip._vendor.pygments.lexers.minecraft', 'SNBT', ('snbt',), ('*.snbt',), ('text/snbt',)),
    'SarlLexer': ('pip._vendor.pygments.lexers.jvm', 'SARL', ('sarl',), ('*.sarl',), ('text/x-sarl',)),
    'SassLexer': ('pip._vendor.pygments.lexers.css', 'Sass', ('sass',), ('*.sass',), ('text/x-sass',)),
    'SaviLexer': ('pip._vendor.pygments.lexers.savi', 'Savi', ('savi',), ('*.savi',), ()),
    'ScalaLexer': ('pip._vendor.pygments.lexers.jvm', 'Scala', ('scala',), ('*.scala',), ('text/x-scala',)),
    'ScamlLexer': ('pip._vendor.pygments.lexers.html', 'Scaml', ('scaml',), ('*.scaml',), ('text/x-scaml',)),
    'ScdocLexer': ('pip._vendor.pygments.lexers.scdoc', 'scdoc', ('scdoc', 'scd'), ('*.scd', '*.scdoc'), ()),
    'SchemeLexer': ('pip._vendor.pygments.lexers.lisp', 'Scheme', ('scheme', 'scm'), ('*.scm', '*.ss'), ('text/x-scheme', 'application/x-scheme')),
    'ScilabLexer': ('pip._vendor.pygments.lexers.matlab', 'Scilab', ('scilab',), ('*.sci', '*.sce', '*.tst'), ('text/scilab',)),
    'ScssLexer': ('pip._vendor.pygments.lexers.css', 'SCSS', ('scss',), ('*.scss',), ('text/x-scss',)),
    'SedLexer': ('pip._vendor.pygments.lexers.textedit', 'Sed', ('sed', 'gsed', 'ssed'), ('*.sed', '*.[gs]sed'), ('text/x-sed',)),
    'ShExCLexer': ('pip._vendor.pygments.lexers.rdf', 'ShExC', ('shexc', 'shex'), ('*.shex',), ('text/shex',)),
    'ShenLexer': ('pip._vendor.pygments.lexers.lisp', 'Shen', ('shen',), ('*.shen',), ('text/x-shen', 'application/x-shen')),
    'SieveLexer': ('pip._vendor.pygments.lexers.sieve', 'Sieve', ('sieve',), ('*.siv', '*.sieve'), ()),
    'SilverLexer': ('pip._vendor.pygments.lexers.verification', 'Silver', ('silver',), ('*.sil', '*.vpr'), ()),
    'SingularityLexer': ('pip._vendor.pygments.lexers.configs', 'Singularity', ('singularity',), ('*.def', 'Singularity'), ()),
    'SlashLexer': ('pip._vendor.pygments.lexers.slash', 'Slash', ('slash',), ('*.sla',), ()),
    'SlimLexer': ('pip._vendor.pygments.lexers.webmisc', 'Slim', ('slim',), ('*.slim',), ('text/x-slim',)),
    'SlurmBashLexer': ('pip._vendor.pygments.lexers.shell', 'Slurm', ('slurm', 'sbatch'), ('*.sl',), ()),
    'SmaliLexer': ('pip._vendor.pygments.lexers.dalvik', 'Smali', ('smali',), ('*.smali',), ('text/smali',)),
    'SmalltalkLexer': ('pip._vendor.pygments.lexers.smalltalk', 'Smalltalk', ('smalltalk', 'squeak', 'st'), ('*.st',), ('text/x-smalltalk',)),
    'SmartGameFormatLexer': ('pip._vendor.pygments.lexers.sgf', 'SmartGameFormat', ('sgf',), ('*.sgf',), ()),
    'SmartyLexer': ('pip._vendor.pygments.lexers.templates', 'Smarty', ('smarty',), ('*.tpl',), ('application/x-smarty',)),
    'SmithyLexer': ('pip._vendor.pygments.lexers.smithy', 'Smithy', ('smithy',), ('*.smithy',), ()),
    'SnobolLexer': ('pip._vendor.pygments.lexers.snobol', 'Snobol', ('snobol',), ('*.snobol',), ('text/x-snobol',)),
    'SnowballLexer': ('pip._vendor.pygments.lexers.dsls', 'Snowball', ('snowball',), ('*.sbl',), ()),
    'SolidityLexer': ('pip._vendor.pygments.lexers.solidity', 'Solidity', ('solidity',), ('*.sol',), ()),
    'SoongLexer': ('pip._vendor.pygments.lexers.soong', 'Soong', ('androidbp', 'bp', 'soong'), ('Android.bp',), ()),
    'SophiaLexer': ('pip._vendor.pygments.lexers.sophia', 'Sophia', ('sophia',), ('*.aes',), ()),
    'SourcePawnLexer': ('pip._vendor.pygments.lexers.pawn', 'SourcePawn', ('sp',), ('*.sp',), ('text/x-sourcepawn',)),
    'SourcesListLexer': ('pip._vendor.pygments.lexers.installers', 'Debian Sourcelist', ('debsources', 'sourceslist', 'sources.list'), ('sources.list',), ()),
    'SparqlLexer': ('pip._vendor.pygments.lexers.rdf', 'SPARQL', ('sparql',), ('*.rq', '*.sparql'), ('application/sparql-query',)),
    'SpiceLexer': ('pip._vendor.pygments.lexers.spice', 'Spice', ('spice', 'spicelang'), ('*.spice',), ('text/x-spice',)),
    'SqlJinjaLexer': ('pip._vendor.pygments.lexers.templates', 'SQL+Jinja', ('sql+jinja',), ('*.sql', '*.sql.j2', '*.sql.jinja2'), ()),
    'SqlLexer': ('pip._vendor.pygments.lexers.sql', 'SQL', ('sql',), ('*.sql',), ('text/x-sql',)),
    'SqliteConsoleLexer': ('pip._vendor.pygments.lexers.sql', 'sqlite3con', ('sqlite3',), ('*.sqlite3-console',), ('text/x-sqlite3-console',)),
    'SquidConfLexer': ('pip._vendor.pygments.lexers.configs', 'SquidConf', ('squidconf', 'squid.conf', 'squid'), ('squid.conf',), ('text/x-squidconf',)),
    'SrcinfoLexer': ('pip._vendor.pygments.lexers.srcinfo', 'Srcinfo', ('srcinfo',), ('.SRCINFO',), ()),
    'SspLexer': ('pip._vendor.pygments.lexers.templates', 'Scalate Server Page', ('ssp',), ('*.ssp',), ('application/x-ssp',)),
    'StanLexer': ('pip._vendor.pygments.lexers.modeling', 'Stan', ('stan',), ('*.stan',), ()),
    'StataLexer': ('pip._vendor.pygments.lexers.stata', 'Stata', ('stata', 'do'), ('*.do', '*.ado'), ('text/x-stata', 'text/stata', 'application/x-stata')),
    'SuperColliderLexer': ('pip._vendor.pygments.lexers.supercollider', 'SuperCollider', ('supercollider', 'sc'), ('*.sc', '*.scd'), ('application/supercollider', 'text/supercollider')),
    'SwiftLexer': ('pip._vendor.pygments.lexers.objective', 'Swift', ('swift',), ('*.swift',), ('text/x-swift',)),
    'SwigLexer': ('pip._vendor.pygments.lexers.c_like', 'SWIG', ('swig',), ('*.swg', '*.i'), ('text/swig',)),
    'SystemVerilogLexer': ('pip._vendor.pygments.lexers.hdl', 'systemverilog', ('systemverilog', 'sv'), ('*.sv', '*.svh'), ('text/x-systemverilog',)),
    'SystemdLexer': ('pip._vendor.pygments.lexers.configs', 'Systemd', ('systemd',), ('*.service', '*.socket', '*.device', '*.mount', '*.automount', '*.swap', '*.target', '*.path', '*.timer', '*.slice', '*.scope'), ()),
    'TAPLexer': ('pip._vendor.pygments.lexers.testing', 'TAP', ('tap',), ('*.tap',), ()),
    'TNTLexer': ('pip._vendor.pygments.lexers.tnt', 'Typographic Number Theory', ('tnt',), ('*.tnt',), ()),
    'TOMLLexer': ('pip._vendor.pygments.lexers.configs', 'TOML', ('toml',), ('*.toml', 'Pipfile', 'poetry.lock'), ('application/toml',)),
    'TactLexer': ('pip._vendor.pygments.lexers.tact', 'Tact', ('tact',), ('*.tact',), ()),
    'Tads3Lexer': ('pip._vendor.pygments.lexers.int_fiction', 'TADS 3', ('tads3',), ('*.t',), ()),
    'TalLexer': ('pip._vendor.pygments.lexers.tal', 'Tal', ('tal', 'uxntal'), ('*.tal',), ('text/x-uxntal',)),
    'TasmLexer': ('pip._vendor.pygments.lexers.asm', 'TASM', ('tasm',), ('*.asm', '*.ASM', '*.tasm'), ('text/x-tasm',)),
    'TclLexer': ('pip._vendor.pygments.lexers.tcl', 'Tcl', ('tcl',), ('*.tcl', '*.rvt'), ('text/x-tcl', 'text/x-script.tcl', 'application/x-tcl')),
    'TcshLexer': ('pip._vendor.pygments.lexers.shell', 'Tcsh', ('tcsh', 'csh'), ('*.tcsh', '*.csh'), ('application/x-csh',)),
    'TcshSessionLexer': ('pip._vendor.pygments.lexers.shell', 'Tcsh Session', ('tcshcon',), (), ()),
    'TeaTemplateLexer': ('pip._vendor.pygments.lexers.templates', 'Tea', ('tea',), ('*.tea',), ('text/x-tea',)),
    'TealLexer': ('pip._vendor.pygments.lexers.teal', 'teal', ('teal',), ('*.teal',), ()),
    'TeraTermLexer': ('pip._vendor.pygments.lexers.teraterm', 'Tera Term macro', ('teratermmacro', 'teraterm', 'ttl'), ('*.ttl',), ('text/x-teratermmacro',)),
    'TermcapLexer': ('pip._vendor.pygments.lexers.configs', 'Termcap', ('termcap',), ('termcap', 'termcap.src'), ()),
    'TerminfoLexer': ('pip._vendor.pygments.lexers.configs', 'Terminfo', ('terminfo',), ('terminfo', 'terminfo.src'), ()),
    'TerraformLexer': ('pip._vendor.pygments.lexers.configs', 'Terraform', ('terraform', 'tf', 'hcl'), ('*.tf', '*.hcl'), ('application/x-tf', 'application/x-terraform')),
    'TexLexer': ('pip._vendor.pygments.lexers.markup', 'TeX', ('tex', 'latex'), ('*.tex', '*.aux', '*.toc'), ('text/x-tex', 'text/x-latex')),
    'TextLexer': ('pip._vendor.pygments.lexers.special', 'Text only', ('text',), ('*.txt',), ('text/plain',)),
    'ThingsDBLexer': ('pip._vendor.pygments.lexers.thingsdb', 'ThingsDB', ('ti', 'thingsdb'), ('*.ti',), ()),
    'ThriftLexer': ('pip._vendor.pygments.lexers.dsls', 'Thrift', ('thrift',), ('*.thrift',), ('application/x-thrift',)),
    'TiddlyWiki5Lexer': ('pip._vendor.pygments.lexers.markup', 'tiddler', ('tid',), ('*.tid',), ('text/vnd.tiddlywiki',)),
    'TlbLexer': ('pip._vendor.pygments.lexers.tlb', 'Tl-b', ('tlb',), ('*.tlb',), ()),
    'TlsLexer': ('pip._vendor.pygments.lexers.tls', 'TLS Presentation Language', ('tls',), (), ()),
    'TodotxtLexer': ('pip._vendor.pygments.lexers.textfmts', 'Todotxt', ('todotxt',), ('todo.txt', '*.todotxt'), ('text/x-todo',)),
    'TransactSqlLexer': ('pip._vendor.pygments.lexers.sql', 'Transact-SQL', ('tsql', 't-sql'), ('*.sql',), ('text/x-tsql',)),
    'TreetopLexer': ('pip._vendor.pygments.lexers.parsers', 'Treetop', ('treetop',), ('*.treetop', '*.tt'), ()),
    'TurtleLexer': ('pip._vendor.pygments.lexers.rdf', 'Turtle', ('turtle',), ('*.ttl',), ('text/turtle', 'application/x-turtle')),
    'TwigHtmlLexer': ('pip._vendor.pygments.lexers.templates', 'HTML+Twig', ('html+twig',), ('*.twig',), ('text/html+twig',)),
    'TwigLexer': ('pip._vendor.pygments.lexers.templates', 'Twig', ('twig',), (), ('application/x-twig',)),
    'TypeScriptLexer': ('pip._vendor.pygments.lexers.javascript', 'TypeScript', ('typescript', 'ts'), ('*.ts',), ('application/x-typescript', 'text/x-typescript')),
    'TypoScriptCssDataLexer': ('pip._vendor.pygments.lexers.typoscript', 'TypoScriptCssData', ('typoscriptcssdata',), (), ()),
    'TypoScriptHtmlDataLexer': ('pip._vendor.pygments.lexers.typoscript', 'TypoScriptHtmlData', ('typoscripthtmldata',), (), ()),
    'TypoScriptLexer': ('pip._vendor.pygments.lexers.typoscript', 'TypoScript', ('typoscript',), ('*.typoscript',), ('text/x-typoscript',)),
    'TypstLexer': ('pip._vendor.pygments.lexers.typst', 'Typst', ('typst',), ('*.typ',), ('text/x-typst',)),
    'UL4Lexer': ('pip._vendor.pygments.lexers.ul4', 'UL4', ('ul4',), ('*.ul4',), ()),
    'UcodeLexer': ('pip._vendor.pygments.lexers.unicon', 'ucode', ('ucode',), ('*.u', '*.u1', '*.u2'), ()),
    'UniconLexer': ('pip._vendor.pygments.lexers.unicon', 'Unicon', ('unicon',), ('*.icn',), ('text/unicon',)),
    'UnixConfigLexer': ('pip._vendor.pygments.lexers.configs', 'Unix/Linux config files', ('unixconfig', 'linuxconfig'), (), ()),
    'UrbiscriptLexer': ('pip._vendor.pygments.lexers.urbi', 'UrbiScript', ('urbiscript',), ('*.u',), ('application/x-urbiscript',)),
    'UrlEncodedLexer': ('pip._vendor.pygments.lexers.html', 'urlencoded', ('urlencoded',), (), ('application/x-www-form-urlencoded',)),
    'UsdLexer': ('pip._vendor.pygments.lexers.usd', 'USD', ('usd', 'usda'), ('*.usd', '*.usda'), ()),
    'VBScriptLexer': ('pip._vendor.pygments.lexers.basic', 'VBScript', ('vbscript',), ('*.vbs', '*.VBS'), ()),
    'VCLLexer': ('pip._vendor.pygments.lexers.varnish', 'VCL', ('vcl',), ('*.vcl',), ('text/x-vclsrc',)),
    'VCLSnippetLexer': ('pip._vendor.pygments.lexers.varnish', 'VCLSnippets', ('vclsnippets', 'vclsnippet'), (), ('text/x-vclsnippet',)),
    'VCTreeStatusLexer': ('pip._vendor.pygments.lexers.console', 'VCTreeStatus', ('vctreestatus',), (), ()),
    'VGLLexer': ('pip._vendor.pygments.lexers.dsls', 'VGL', ('vgl',), ('*.rpf',), ()),
    'ValaLexer': ('pip._vendor.pygments.lexers.c_like', 'Vala', ('vala', 'vapi'), ('*.vala', '*.vapi'), ('text/x-vala',)),
    'VbNetAspxLexer': ('pip._vendor.pygments.lexers.dotnet', 'aspx-vb', ('aspx-vb',), ('*.aspx', '*.asax', '*.ascx', '*.ashx', '*.asmx', '*.axd'), ()),
    'VbNetLexer': ('pip._vendor.pygments.lexers.dotnet', 'VB.net', ('vb.net', 'vbnet', 'lobas', 'oobas', 'sobas', 'visual-basic', 'visualbasic'), ('*.vb', '*.bas'), ('text/x-vbnet', 'text/x-vba')),
    'VelocityHtmlLexer': ('pip._vendor.pygments.lexers.templates', 'HTML+Velocity', ('html+velocity',), (), ('text/html+velocity',)),
    'VelocityLexer': ('pip._vendor.pygments.lexers.templates', 'Velocity', ('velocity',), ('*.vm', '*.fhtml'), ()),
    'VelocityXmlLexer': ('pip._vendor.pygments.lexers.templates', 'XML+Velocity', ('xml+velocity',), (), ('application/xml+velocity',)),
    'VerifpalLexer': ('pip._vendor.pygments.lexers.verifpal', 'Verifpal', ('verifpal',), ('*.vp',), ('text/x-verifpal',)),
    'VerilogLexer': ('pip._vendor.pygments.lexers.hdl', 'verilog', ('verilog', 'v'), ('*.v',), ('text/x-verilog',)),
    'VhdlLexer': ('pip._vendor.pygments.lexers.hdl', 'vhdl', ('vhdl',), ('*.vhdl', '*.vhd'), ('text/x-vhdl',)),
    'VimLexer': ('pip._vendor.pygments.lexers.textedit', 'VimL', ('vim',), ('*.vim', '.vimrc', '.exrc', '.gvimrc', '_vimrc', '_exrc', '_gvimrc', 'vimrc', 'gvimrc'), ('text/x-vim',)),
    'VisualPrologGrammarLexer': ('pip._vendor.pygments.lexers.vip', 'Visual Prolog Grammar', ('visualprologgrammar',), ('*.vipgrm',), ()),
    'VisualPrologLexer': ('pip._vendor.pygments.lexers.vip', 'Visual Prolog', ('visualprolog',), ('*.pro', '*.cl', '*.i', '*.pack', '*.ph'), ()),
    'VyperLexer': ('pip._vendor.pygments.lexers.vyper', 'Vyper', ('vyper',), ('*.vy',), ()),
    'WDiffLexer': ('pip._vendor.pygments.lexers.diff', 'WDiff', ('wdiff',), ('*.wdiff',), ()),
    'WatLexer': ('pip._vendor.pygments.lexers.webassembly', 'WebAssembly', ('wast', 'wat'), ('*.wat', '*.wast'), ()),
    'WebIDLLexer': ('pip._vendor.pygments.lexers.webidl', 'Web IDL', ('webidl',), ('*.webidl',), ()),
    'WgslLexer': ('pip._vendor.pygments.lexers.wgsl', 'WebGPU Shading Language', ('wgsl',), ('*.wgsl',), ('text/wgsl',)),
    'WhileyLexer': ('pip._vendor.pygments.lexers.whiley', 'Whiley', ('whiley',), ('*.whiley',), ('text/x-whiley',)),
    'WikitextLexer': ('pip._vendor.pygments.lexers.markup', 'Wikitext', ('wikitext', 'mediawiki'), (), ('text/x-wiki',)),
    'WoWTocLexer': ('pip._vendor.pygments.lexers.wowtoc', 'World of Warcraft TOC', ('wowtoc',), ('*.toc',), ()),
    'WrenLexer': ('pip._vendor.pygments.lexers.wren', 'Wren', ('wren',), ('*.wren',), ()),
    'X10Lexer': ('pip._vendor.pygments.lexers.x10', 'X10', ('x10', 'xten'), ('*.x10',), ('text/x-x10',)),
    'XMLUL4Lexer': ('pip._vendor.pygments.lexers.ul4', 'XML+UL4', ('xml+ul4',), ('*.xmlul4',), ()),
    'XQueryLexer': ('pip._vendor.pygments.lexers.webmisc', 'XQuery', ('xquery', 'xqy', 'xq', 'xql', 'xqm'), ('*.xqy', '*.xquery', '*.xq', '*.xql', '*.xqm'), ('text/xquery', 'application/xquery')),
    'XmlDjangoLexer': ('pip._vendor.pygments.lexers.templates', 'XML+Django/Jinja', ('xml+django', 'xml+jinja'), ('*.xml.j2', '*.xml.jinja2'), ('application/xml+django', 'application/xml+jinja')),
    'XmlErbLexer': ('pip._vendor.pygments.lexers.templates', 'XML+Ruby', ('xml+ruby', 'xml+erb'), (), ('application/xml+ruby',)),
    'XmlLexer': ('pip._vendor.pygments.lexers.html', 'XML', ('xml',), ('*.xml', '*.xsl', '*.rss', '*.xslt', '*.xsd', '*.wsdl', '*.wsf'), ('text/xml', 'application/xml', 'image/svg+xml', 'application/rss+xml', 'application/atom+xml')),
    'XmlPhpLexer': ('pip._vendor.pygments.lexers.templates', 'XML+PHP', ('xml+php',), (), ('application/xml+php',)),
    'XmlSmartyLexer': ('pip._vendor.pygments.lexers.templates', 'XML+Smarty', ('xml+smarty',), (), ('application/xml+smarty',)),
    'XorgLexer': ('pip._vendor.pygments.lexers.xorg', 'Xorg', ('xorg.conf',), ('xorg.conf',), ()),
    'XppLexer': ('pip._vendor.pygments.lexers.dotnet', 'X++', ('xpp', 'x++'), ('*.xpp',), ()),
    'XsltLexer': ('pip._vendor.pygments.lexers.html', 'XSLT', ('xslt',), ('*.xsl', '*.xslt', '*.xpl'), ('application/xsl+xml', 'application/xslt+xml')),
    'XtendLexer': ('pip._vendor.pygments.lexers.jvm', 'Xtend', ('xtend',), ('*.xtend',), ('text/x-xtend',)),
    'XtlangLexer': ('pip._vendor.pygments.lexers.lisp', 'xtlang', ('extempore',), ('*.xtm',), ()),
    'YamlJinjaLexer': ('pip._vendor.pygments.lexers.templates', 'YAML+Jinja', ('yaml+jinja', 'salt', 'sls'), ('*.sls', '*.yaml.j2', '*.yml.j2', '*.yaml.jinja2', '*.yml.jinja2'), ('text/x-yaml+jinja', 'text/x-sls')),
    'YamlLexer': ('pip._vendor.pygments.lexers.data', 'YAML', ('yaml',), ('*.yaml', '*.yml'), ('text/x-yaml',)),
    'YangLexer': ('pip._vendor.pygments.lexers.yang', 'YANG', ('yang',), ('*.yang',), ('application/yang',)),
    'YaraLexer': ('pip._vendor.pygments.lexers.yara', 'YARA', ('yara', 'yar'), ('*.yar',), ('text/x-yara',)),
    'ZeekLexer': ('pip._vendor.pygments.lexers.dsls', 'Zeek', ('zeek', 'bro'), ('*.zeek', '*.bro'), ()),
    'ZephirLexer': ('pip._vendor.pygments.lexers.php', 'Zephir', ('zephir',), ('*.zep',), ()),
    'ZigLexer': ('pip._vendor.pygments.lexers.zig', 'Zig', ('zig',), ('*.zig',), ('text/zig',)),
    'apdlexer': ('pip._vendor.pygments.lexers.apdlexer', 'ANSYS parametric design language', ('ansys', 'apdl'), ('*.ans',), ()),
}

# === NexusCore/openenv\Lib\site-packages\yaml\parser.py ===

# The following YAML grammar is LL(1) and is parsed by a recursive descent
# parser.
#
# stream            ::= STREAM-START implicit_document? explicit_document* STREAM-END
# implicit_document ::= block_node DOCUMENT-END*
# explicit_document ::= DIRECTIVE* DOCUMENT-START block_node? DOCUMENT-END*
# block_node_or_indentless_sequence ::=
#                       ALIAS
#                       | properties (block_content | indentless_block_sequence)?
#                       | block_content
#                       | indentless_block_sequence
# block_node        ::= ALIAS
#                       | properties block_content?
#                       | block_content
# flow_node         ::= ALIAS
#                       | properties flow_content?
#                       | flow_content
# properties        ::= TAG ANCHOR? | ANCHOR TAG?
# block_content     ::= block_collection | flow_collection | SCALAR
# flow_content      ::= flow_collection | SCALAR
# block_collection  ::= block_sequence | block_mapping
# flow_collection   ::= flow_sequence | flow_mapping
# block_sequence    ::= BLOCK-SEQUENCE-START (BLOCK-ENTRY block_node?)* BLOCK-END
# indentless_sequence   ::= (BLOCK-ENTRY block_node?)+
# block_mapping     ::= BLOCK-MAPPING_START
#                       ((KEY block_node_or_indentless_sequence?)?
#                       (VALUE block_node_or_indentless_sequence?)?)*
#                       BLOCK-END
# flow_sequence     ::= FLOW-SEQUENCE-START
#                       (flow_sequence_entry FLOW-ENTRY)*
#                       flow_sequence_entry?
#                       FLOW-SEQUENCE-END
# flow_sequence_entry   ::= flow_node | KEY flow_node? (VALUE flow_node?)?
# flow_mapping      ::= FLOW-MAPPING-START
#                       (flow_mapping_entry FLOW-ENTRY)*
#                       flow_mapping_entry?
#                       FLOW-MAPPING-END
# flow_mapping_entry    ::= flow_node | KEY flow_node? (VALUE flow_node?)?
#
# FIRST sets:
#
# stream: { STREAM-START }
# explicit_document: { DIRECTIVE DOCUMENT-START }
# implicit_document: FIRST(block_node)
# block_node: { ALIAS TAG ANCHOR SCALAR BLOCK-SEQUENCE-START BLOCK-MAPPING-START FLOW-SEQUENCE-START FLOW-MAPPING-START }
# flow_node: { ALIAS ANCHOR TAG SCALAR FLOW-SEQUENCE-START FLOW-MAPPING-START }
# block_content: { BLOCK-SEQUENCE-START BLOCK-MAPPING-START FLOW-SEQUENCE-START FLOW-MAPPING-START SCALAR }
# flow_content: { FLOW-SEQUENCE-START FLOW-MAPPING-START SCALAR }
# block_collection: { BLOCK-SEQUENCE-START BLOCK-MAPPING-START }
# flow_collection: { FLOW-SEQUENCE-START FLOW-MAPPING-START }
# block_sequence: { BLOCK-SEQUENCE-START }
# block_mapping: { BLOCK-MAPPING-START }
# block_node_or_indentless_sequence: { ALIAS ANCHOR TAG SCALAR BLOCK-SEQUENCE-START BLOCK-MAPPING-START FLOW-SEQUENCE-START FLOW-MAPPING-START BLOCK-ENTRY }
# indentless_sequence: { ENTRY }
# flow_collection: { FLOW-SEQUENCE-START FLOW-MAPPING-START }
# flow_sequence: { FLOW-SEQUENCE-START }
# flow_mapping: { FLOW-MAPPING-START }
# flow_sequence_entry: { ALIAS ANCHOR TAG SCALAR FLOW-SEQUENCE-START FLOW-MAPPING-START KEY }
# flow_mapping_entry: { ALIAS ANCHOR TAG SCALAR FLOW-SEQUENCE-START FLOW-MAPPING-START KEY }

__all__ = ['Parser', 'ParserError']

from .error import MarkedYAMLError
from .tokens import *
from .events import *
from .scanner import *

class ParserError(MarkedYAMLError):
    pass

class Parser:
    # Since writing a recursive-descendant parser is a straightforward task, we
    # do not give many comments here.

    DEFAULT_TAGS = {
        '!':   '!',
        '!!':  'tag:yaml.org,2002:',
    }

    def __init__(self):
        self.current_event = None
        self.yaml_version = None
        self.tag_handles = {}
        self.states = []
        self.marks = []
        self.state = self.parse_stream_start

    def dispose(self):
        # Reset the state attributes (to clear self-references)
        self.states = []
        self.state = None

    def check_event(self, *choices):
        # Check the type of the next event.
        if self.current_event is None:
            if self.state:
                self.current_event = self.state()
        if self.current_event is not None:
            if not choices:
                return True
            for choice in choices:
                if isinstance(self.current_event, choice):
                    return True
        return False

    def peek_event(self):
        # Get the next event.
        if self.current_event is None:
            if self.state:
                self.current_event = self.state()
        return self.current_event

    def get_event(self):
        # Get the next event and proceed further.
        if self.current_event is None:
            if self.state:
                self.current_event = self.state()
        value = self.current_event
        self.current_event = None
        return value

    # stream    ::= STREAM-START implicit_document? explicit_document* STREAM-END
    # implicit_document ::= block_node DOCUMENT-END*
    # explicit_document ::= DIRECTIVE* DOCUMENT-START block_node? DOCUMENT-END*

    def parse_stream_start(self):

        # Parse the stream start.
        token = self.get_token()
        event = StreamStartEvent(token.start_mark, token.end_mark,
                encoding=token.encoding)

        # Prepare the next state.
        self.state = self.parse_implicit_document_start

        return event

    def parse_implicit_document_start(self):

        # Parse an implicit document.
        if not self.check_token(DirectiveToken, DocumentStartToken,
                StreamEndToken):
            self.tag_handles = self.DEFAULT_TAGS
            token = self.peek_token()
            start_mark = end_mark = token.start_mark
            event = DocumentStartEvent(start_mark, end_mark,
                    explicit=False)

            # Prepare the next state.
            self.states.append(self.parse_document_end)
            self.state = self.parse_block_node

            return event

        else:
            return self.parse_document_start()

    def parse_document_start(self):

        # Parse any extra document end indicators.
        while self.check_token(DocumentEndToken):
            self.get_token()

        # Parse an explicit document.
        if not self.check_token(StreamEndToken):
            token = self.peek_token()
            start_mark = token.start_mark
            version, tags = self.process_directives()
            if not self.check_token(DocumentStartToken):
                raise ParserError(None, None,
                        "expected '<document start>', but found %r"
                        % self.peek_token().id,
                        self.peek_token().start_mark)
            token = self.get_token()
            end_mark = token.end_mark
            event = DocumentStartEvent(start_mark, end_mark,
                    explicit=True, version=version, tags=tags)
            self.states.append(self.parse_document_end)
            self.state = self.parse_document_content
        else:
            # Parse the end of the stream.
            token = self.get_token()
            event = StreamEndEvent(token.start_mark, token.end_mark)
            assert not self.states
            assert not self.marks
            self.state = None
        return event

    def parse_document_end(self):

        # Parse the document end.
        token = self.peek_token()
        start_mark = end_mark = token.start_mark
        explicit = False
        if self.check_token(DocumentEndToken):
            token = self.get_token()
            end_mark = token.end_mark
            explicit = True
        event = DocumentEndEvent(start_mark, end_mark,
                explicit=explicit)

        # Prepare the next state.
        self.state = self.parse_document_start

        return event

    def parse_document_content(self):
        if self.check_token(DirectiveToken,
                DocumentStartToken, DocumentEndToken, StreamEndToken):
            event = self.process_empty_scalar(self.peek_token().start_mark)
            self.state = self.states.pop()
            return event
        else:
            return self.parse_block_node()

    def process_directives(self):
        self.yaml_version = None
        self.tag_handles = {}
        while self.check_token(DirectiveToken):
            token = self.get_token()
            if token.name == 'YAML':
                if self.yaml_version is not None:
                    raise ParserError(None, None,
                            "found duplicate YAML directive", token.start_mark)
                major, minor = token.value
                if major != 1:
                    raise ParserError(None, None,
                            "found incompatible YAML document (version 1.* is required)",
                            token.start_mark)
                self.yaml_version = token.value
            elif token.name == 'TAG':
                handle, prefix = token.value
                if handle in self.tag_handles:
                    raise ParserError(None, None,
                            "duplicate tag handle %r" % handle,
                            token.start_mark)
                self.tag_handles[handle] = prefix
        if self.tag_handles:
            value = self.yaml_version, self.tag_handles.copy()
        else:
            value = self.yaml_version, None
        for key in self.DEFAULT_TAGS:
            if key not in self.tag_handles:
                self.tag_handles[key] = self.DEFAULT_TAGS[key]
        return value

    # block_node_or_indentless_sequence ::= ALIAS
    #               | properties (block_content | indentless_block_sequence)?
    #               | block_content
    #               | indentless_block_sequence
    # block_node    ::= ALIAS
    #                   | properties block_content?
    #                   | block_content
    # flow_node     ::= ALIAS
    #                   | properties flow_content?
    #                   | flow_content
    # properties    ::= TAG ANCHOR? | ANCHOR TAG?
    # block_content     ::= block_collection | flow_collection | SCALAR
    # flow_content      ::= flow_collection | SCALAR
    # block_collection  ::= block_sequence | block_mapping
    # flow_collection   ::= flow_sequence | flow_mapping

    def parse_block_node(self):
        return self.parse_node(block=True)

    def parse_flow_node(self):
        return self.parse_node()

    def parse_block_node_or_indentless_sequence(self):
        return self.parse_node(block=True, indentless_sequence=True)

    def parse_node(self, block=False, indentless_sequence=False):
        if self.check_token(AliasToken):
            token = self.get_token()
            event = AliasEvent(token.value, token.start_mark, token.end_mark)
            self.state = self.states.pop()
        else:
            anchor = None
            tag = None
            start_mark = end_mark = tag_mark = None
            if self.check_token(AnchorToken):
                token = self.get_token()
                start_mark = token.start_mark
                end_mark = token.end_mark
                anchor = token.value
                if self.check_token(TagToken):
                    token = self.get_token()
                    tag_mark = token.start_mark
                    end_mark = token.end_mark
                    tag = token.value
            elif self.check_token(TagToken):
                token = self.get_token()
                start_mark = tag_mark = token.start_mark
                end_mark = token.end_mark
                tag = token.value
                if self.check_token(AnchorToken):
                    token = self.get_token()
                    end_mark = token.end_mark
                    anchor = token.value
            if tag is not None:
                handle, suffix = tag
                if handle is not None:
                    if handle not in self.tag_handles:
                        raise ParserError("while parsing a node", start_mark,
                                "found undefined tag handle %r" % handle,
                                tag_mark)
                    tag = self.tag_handles[handle]+suffix
                else:
                    tag = suffix
            #if tag == '!':
            #    raise ParserError("while parsing a node", start_mark,
            #            "found non-specific tag '!'", tag_mark,
            #            "Please check 'http://pyyaml.org/wiki/YAMLNonSpecificTag' and share your opinion.")
            if start_mark is None:
                start_mark = end_mark = self.peek_token().start_mark
            event = None
            implicit = (tag is None or tag == '!')
            if indentless_sequence and self.check_token(BlockEntryToken):
                end_mark = self.peek_token().end_mark
                event = SequenceStartEvent(anchor, tag, implicit,
                        start_mark, end_mark)
                self.state = self.parse_indentless_sequence_entry
            else:
                if self.check_token(ScalarToken):
                    token = self.get_token()
                    end_mark = token.end_mark
                    if (token.plain and tag is None) or tag == '!':
                        implicit = (True, False)
                    elif tag is None:
                        implicit = (False, True)
                    else:
                        implicit = (False, False)
                    event = ScalarEvent(anchor, tag, implicit, token.value,
                            start_mark, end_mark, style=token.style)
                    self.state = self.states.pop()
                elif self.check_token(FlowSequenceStartToken):
                    end_mark = self.peek_token().end_mark
                    event = SequenceStartEvent(anchor, tag, implicit,
                            start_mark, end_mark, flow_style=True)
                    self.state = self.parse_flow_sequence_first_entry
                elif self.check_token(FlowMappingStartToken):
                    end_mark = self.peek_token().end_mark
                    event = MappingStartEvent(anchor, tag, implicit,
                            start_mark, end_mark, flow_style=True)
                    self.state = self.parse_flow_mapping_first_key
                elif block and self.check_token(BlockSequenceStartToken):
                    end_mark = self.peek_token().start_mark
                    event = SequenceStartEvent(anchor, tag, implicit,
                            start_mark, end_mark, flow_style=False)
                    self.state = self.parse_block_sequence_first_entry
                elif block and self.check_token(BlockMappingStartToken):
                    end_mark = self.peek_token().start_mark
                    event = MappingStartEvent(anchor, tag, implicit,
                            start_mark, end_mark, flow_style=False)
                    self.state = self.parse_block_mapping_first_key
                elif anchor is not None or tag is not None:
                    # Empty scalars are allowed even if a tag or an anchor is
                    # specified.
                    event = ScalarEvent(anchor, tag, (implicit, False), '',
                            start_mark, end_mark)
                    self.state = self.states.pop()
                else:
                    if block:
                        node = 'block'
                    else:
                        node = 'flow'
                    token = self.peek_token()
                    raise ParserError("while parsing a %s node" % node, start_mark,
                            "expected the node content, but found %r" % token.id,
                            token.start_mark)
        return event

    # block_sequence ::= BLOCK-SEQUENCE-START (BLOCK-ENTRY block_node?)* BLOCK-END

    def parse_block_sequence_first_entry(self):
        token = self.get_token()
        self.marks.append(token.start_mark)
        return self.parse_block_sequence_entry()

    def parse_block_sequence_entry(self):
        if self.check_token(BlockEntryToken):
            token = self.get_token()
            if not self.check_token(BlockEntryToken, BlockEndToken):
                self.states.append(self.parse_block_sequence_entry)
                return self.parse_block_node()
            else:
                self.state = self.parse_block_sequence_entry
                return self.process_empty_scalar(token.end_mark)
        if not self.check_token(BlockEndToken):
            token = self.peek_token()
            raise ParserError("while parsing a block collection", self.marks[-1],
                    "expected <block end>, but found %r" % token.id, token.start_mark)
        token = self.get_token()
        event = SequenceEndEvent(token.start_mark, token.end_mark)
        self.state = self.states.pop()
        self.marks.pop()
        return event

    # indentless_sequence ::= (BLOCK-ENTRY block_node?)+

    def parse_indentless_sequence_entry(self):
        if self.check_token(BlockEntryToken):
            token = self.get_token()
            if not self.check_token(BlockEntryToken,
                    KeyToken, ValueToken, BlockEndToken):
                self.states.append(self.parse_indentless_sequence_entry)
                return self.parse_block_node()
            else:
                self.state = self.parse_indentless_sequence_entry
                return self.process_empty_scalar(token.end_mark)
        token = self.peek_token()
        event = SequenceEndEvent(token.start_mark, token.start_mark)
        self.state = self.states.pop()
        return event

    # block_mapping     ::= BLOCK-MAPPING_START
    #                       ((KEY block_node_or_indentless_sequence?)?
    #                       (VALUE block_node_or_indentless_sequence?)?)*
    #                       BLOCK-END

    def parse_block_mapping_first_key(self):
        token = self.get_token()
        self.marks.append(token.start_mark)
        return self.parse_block_mapping_key()

    def parse_block_mapping_key(self):
        if self.check_token(KeyToken):
            token = self.get_token()
            if not self.check_token(KeyToken, ValueToken, BlockEndToken):
                self.states.append(self.parse_block_mapping_value)
                return self.parse_block_node_or_indentless_sequence()
            else:
                self.state = self.parse_block_mapping_value
                return self.process_empty_scalar(token.end_mark)
        if not self.check_token(BlockEndToken):
            token = self.peek_token()
            raise ParserError("while parsing a block mapping", self.marks[-1],
                    "expected <block end>, but found %r" % token.id, token.start_mark)
        token = self.get_token()
        event = MappingEndEvent(token.start_mark, token.end_mark)
        self.state = self.states.pop()
        self.marks.pop()
        return event

    def parse_block_mapping_value(self):
        if self.check_token(ValueToken):
            token = self.get_token()
            if not self.check_token(KeyToken, ValueToken, BlockEndToken):
                self.states.append(self.parse_block_mapping_key)
                return self.parse_block_node_or_indentless_sequence()
            else:
                self.state = self.parse_block_mapping_key
                return self.process_empty_scalar(token.end_mark)
        else:
            self.state = self.parse_block_mapping_key
            token = self.peek_token()
            return self.process_empty_scalar(token.start_mark)

    # flow_sequence     ::= FLOW-SEQUENCE-START
    #                       (flow_sequence_entry FLOW-ENTRY)*
    #                       flow_sequence_entry?
    #                       FLOW-SEQUENCE-END
    # flow_sequence_entry   ::= flow_node | KEY flow_node? (VALUE flow_node?)?
    #
    # Note that while production rules for both flow_sequence_entry and
    # flow_mapping_entry are equal, their interpretations are different.
    # For `flow_sequence_entry`, the part `KEY flow_node? (VALUE flow_node?)?`
    # generate an inline mapping (set syntax).

    def parse_flow_sequence_first_entry(self):
        token = self.get_token()
        self.marks.append(token.start_mark)
        return self.parse_flow_sequence_entry(first=True)

    def parse_flow_sequence_entry(self, first=False):
        if not self.check_token(FlowSequenceEndToken):
            if not first:
                if self.check_token(FlowEntryToken):
                    self.get_token()
                else:
                    token = self.peek_token()
                    raise ParserError("while parsing a flow sequence", self.marks[-1],
                            "expected ',' or ']', but got %r" % token.id, token.start_mark)
            
            if self.check_token(KeyToken):
                token = self.peek_token()
                event = MappingStartEvent(None, None, True,
                        token.start_mark, token.end_mark,
                        flow_style=True)
                self.state = self.parse_flow_sequence_entry_mapping_key
                return event
            elif not self.check_token(FlowSequenceEndToken):
                self.states.append(self.parse_flow_sequence_entry)
                return self.parse_flow_node()
        token = self.get_token()
        event = SequenceEndEvent(token.start_mark, token.end_mark)
        self.state = self.states.pop()
        self.marks.pop()
        return event

    def parse_flow_sequence_entry_mapping_key(self):
        token = self.get_token()
        if not self.check_token(ValueToken,
                FlowEntryToken, FlowSequenceEndToken):
            self.states.append(self.parse_flow_sequence_entry_mapping_value)
            return self.parse_flow_node()
        else:
            self.state = self.parse_flow_sequence_entry_mapping_value
            return self.process_empty_scalar(token.end_mark)

    def parse_flow_sequence_entry_mapping_value(self):
        if self.check_token(ValueToken):
            token = self.get_token()
            if not self.check_token(FlowEntryToken, FlowSequenceEndToken):
                self.states.append(self.parse_flow_sequence_entry_mapping_end)
                return self.parse_flow_node()
            else:
                self.state = self.parse_flow_sequence_entry_mapping_end
                return self.process_empty_scalar(token.end_mark)
        else:
            self.state = self.parse_flow_sequence_entry_mapping_end
            token = self.peek_token()
            return self.process_empty_scalar(token.start_mark)

    def parse_flow_sequence_entry_mapping_end(self):
        self.state = self.parse_flow_sequence_entry
        token = self.peek_token()
        return MappingEndEvent(token.start_mark, token.start_mark)

    # flow_mapping  ::= FLOW-MAPPING-START
    #                   (flow_mapping_entry FLOW-ENTRY)*
    #                   flow_mapping_entry?
    #                   FLOW-MAPPING-END
    # flow_mapping_entry    ::= flow_node | KEY flow_node? (VALUE flow_node?)?

    def parse_flow_mapping_first_key(self):
        token = self.get_token()
        self.marks.append(token.start_mark)
        return self.parse_flow_mapping_key(first=True)

    def parse_flow_mapping_key(self, first=False):
        if not self.check_token(FlowMappingEndToken):
            if not first:
                if self.check_token(FlowEntryToken):
                    self.get_token()
                else:
                    token = self.peek_token()
                    raise ParserError("while parsing a flow mapping", self.marks[-1],
                            "expected ',' or '}', but got %r" % token.id, token.start_mark)
            if self.check_token(KeyToken):
                token = self.get_token()
                if not self.check_token(ValueToken,
                        FlowEntryToken, FlowMappingEndToken):
                    self.states.append(self.parse_flow_mapping_value)
                    return self.parse_flow_node()
                else:
                    self.state = self.parse_flow_mapping_value
                    return self.process_empty_scalar(token.end_mark)
            elif not self.check_token(FlowMappingEndToken):
                self.states.append(self.parse_flow_mapping_empty_value)
                return self.parse_flow_node()
        token = self.get_token()
        event = MappingEndEvent(token.start_mark, token.end_mark)
        self.state = self.states.pop()
        self.marks.pop()
        return event

    def parse_flow_mapping_value(self):
        if self.check_token(ValueToken):
            token = self.get_token()
            if not self.check_token(FlowEntryToken, FlowMappingEndToken):
                self.states.append(self.parse_flow_mapping_key)
                return self.parse_flow_node()
            else:
                self.state = self.parse_flow_mapping_key
                return self.process_empty_scalar(token.end_mark)
        else:
            self.state = self.parse_flow_mapping_key
            token = self.peek_token()
            return self.process_empty_scalar(token.start_mark)

    def parse_flow_mapping_empty_value(self):
        self.state = self.parse_flow_mapping_key
        return self.process_empty_scalar(self.peek_token().start_mark)

    def process_empty_scalar(self, mark):
        return ScalarEvent(None, None, (True, False), '', mark, mark)


# === NexusCore/openenv\Lib\site-packages\pip\_vendor\pygments\lexers\_mapping.py ===
# Automatically generated by scripts/gen_mapfiles.py.
# DO NOT EDIT BY HAND; run `tox -e mapfiles` instead.

LEXERS = {
    'ABAPLexer': ('pip._vendor.pygments.lexers.business', 'ABAP', ('abap',), ('*.abap', '*.ABAP'), ('text/x-abap',)),
    'AMDGPULexer': ('pip._vendor.pygments.lexers.amdgpu', 'AMDGPU', ('amdgpu',), ('*.isa',), ()),
    'APLLexer': ('pip._vendor.pygments.lexers.apl', 'APL', ('apl',), ('*.apl', '*.aplf', '*.aplo', '*.apln', '*.aplc', '*.apli', '*.dyalog'), ()),
    'AbnfLexer': ('pip._vendor.pygments.lexers.grammar_notation', 'ABNF', ('abnf',), ('*.abnf',), ('text/x-abnf',)),
    'ActionScript3Lexer': ('pip._vendor.pygments.lexers.actionscript', 'ActionScript 3', ('actionscript3', 'as3'), ('*.as',), ('application/x-actionscript3', 'text/x-actionscript3', 'text/actionscript3')),
    'ActionScriptLexer': ('pip._vendor.pygments.lexers.actionscript', 'ActionScript', ('actionscript', 'as'), ('*.as',), ('application/x-actionscript', 'text/x-actionscript', 'text/actionscript')),
    'AdaLexer': ('pip._vendor.pygments.lexers.ada', 'Ada', ('ada', 'ada95', 'ada2005'), ('*.adb', '*.ads', '*.ada'), ('text/x-ada',)),
    'AdlLexer': ('pip._vendor.pygments.lexers.archetype', 'ADL', ('adl',), ('*.adl', '*.adls', '*.adlf', '*.adlx'), ()),
    'AgdaLexer': ('pip._vendor.pygments.lexers.haskell', 'Agda', ('agda',), ('*.agda',), ('text/x-agda',)),
    'AheuiLexer': ('pip._vendor.pygments.lexers.esoteric', 'Aheui', ('aheui',), ('*.aheui',), ()),
    'AlloyLexer': ('pip._vendor.pygments.lexers.dsls', 'Alloy', ('alloy',), ('*.als',), ('text/x-alloy',)),
    'AmbientTalkLexer': ('pip._vendor.pygments.lexers.ambient', 'AmbientTalk', ('ambienttalk', 'ambienttalk/2', 'at'), ('*.at',), ('text/x-ambienttalk',)),
    'AmplLexer': ('pip._vendor.pygments.lexers.ampl', 'Ampl', ('ampl',), ('*.run',), ()),
    'Angular2HtmlLexer': ('pip._vendor.pygments.lexers.templates', 'HTML + Angular2', ('html+ng2',), ('*.ng2',), ()),
    'Angular2Lexer': ('pip._vendor.pygments.lexers.templates', 'Angular2', ('ng2',), (), ()),
    'AntlrActionScriptLexer': ('pip._vendor.pygments.lexers.parsers', 'ANTLR With ActionScript Target', ('antlr-actionscript', 'antlr-as'), ('*.G', '*.g'), ()),
    'AntlrCSharpLexer': ('pip._vendor.pygments.lexers.parsers', 'ANTLR With C# Target', ('antlr-csharp', 'antlr-c#'), ('*.G', '*.g'), ()),
    'AntlrCppLexer': ('pip._vendor.pygments.lexers.parsers', 'ANTLR With CPP Target', ('antlr-cpp',), ('*.G', '*.g'), ()),
    'AntlrJavaLexer': ('pip._vendor.pygments.lexers.parsers', 'ANTLR With Java Target', ('antlr-java',), ('*.G', '*.g'), ()),
    'AntlrLexer': ('pip._vendor.pygments.lexers.parsers', 'ANTLR', ('antlr',), (), ()),
    'AntlrObjectiveCLexer': ('pip._vendor.pygments.lexers.parsers', 'ANTLR With ObjectiveC Target', ('antlr-objc',), ('*.G', '*.g'), ()),
    'AntlrPerlLexer': ('pip._vendor.pygments.lexers.parsers', 'ANTLR With Perl Target', ('antlr-perl',), ('*.G', '*.g'), ()),
    'AntlrPythonLexer': ('pip._vendor.pygments.lexers.parsers', 'ANTLR With Python Target', ('antlr-python',), ('*.G', '*.g'), ()),
    'AntlrRubyLexer': ('pip._vendor.pygments.lexers.parsers', 'ANTLR With Ruby Target', ('antlr-ruby', 'antlr-rb'), ('*.G', '*.g'), ()),
    'ApacheConfLexer': ('pip._vendor.pygments.lexers.configs', 'ApacheConf', ('apacheconf', 'aconf', 'apache'), ('.htaccess', 'apache.conf', 'apache2.conf'), ('text/x-apacheconf',)),
    'AppleScriptLexer': ('pip._vendor.pygments.lexers.scripting', 'AppleScript', ('applescript',), ('*.applescript',), ()),
    'ArduinoLexer': ('pip._vendor.pygments.lexers.c_like', 'Arduino', ('arduino',), ('*.ino',), ('text/x-arduino',)),
    'ArrowLexer': ('pip._vendor.pygments.lexers.arrow', 'Arrow', ('arrow',), ('*.arw',), ()),
    'ArturoLexer': ('pip._vendor.pygments.lexers.arturo', 'Arturo', ('arturo', 'art'), ('*.art',), ()),
    'AscLexer': ('pip._vendor.pygments.lexers.asc', 'ASCII armored', ('asc', 'pem'), ('*.asc', '*.pem', 'id_dsa', 'id_ecdsa', 'id_ecdsa_sk', 'id_ed25519', 'id_ed25519_sk', 'id_rsa'), ('application/pgp-keys', 'application/pgp-encrypted', 'application/pgp-signature', 'application/pem-certificate-chain')),
    'Asn1Lexer': ('pip._vendor.pygments.lexers.asn1', 'ASN.1', ('asn1',), ('*.asn1',), ()),
    'AspectJLexer': ('pip._vendor.pygments.lexers.jvm', 'AspectJ', ('aspectj',), ('*.aj',), ('text/x-aspectj',)),
    'AsymptoteLexer': ('pip._vendor.pygments.lexers.graphics', 'Asymptote', ('asymptote', 'asy'), ('*.asy',), ('text/x-asymptote',)),
    'AugeasLexer': ('pip._vendor.pygments.lexers.configs', 'Augeas', ('augeas',), ('*.aug',), ()),
    'AutoItLexer': ('pip._vendor.pygments.lexers.automation', 'AutoIt', ('autoit',), ('*.au3',), ('text/x-autoit',)),
    'AutohotkeyLexer': ('pip._vendor.pygments.lexers.automation', 'autohotkey', ('autohotkey', 'ahk'), ('*.ahk', '*.ahkl'), ('text/x-autohotkey',)),
    'AwkLexer': ('pip._vendor.pygments.lexers.textedit', 'Awk', ('awk', 'gawk', 'mawk', 'nawk'), ('*.awk',), ('application/x-awk',)),
    'BBCBasicLexer': ('pip._vendor.pygments.lexers.basic', 'BBC Basic', ('bbcbasic',), ('*.bbc',), ()),
    'BBCodeLexer': ('pip._vendor.pygments.lexers.markup', 'BBCode', ('bbcode',), (), ('text/x-bbcode',)),
    'BCLexer': ('pip._vendor.pygments.lexers.algebra', 'BC', ('bc',), ('*.bc',), ()),
    'BQNLexer': ('pip._vendor.pygments.lexers.bqn', 'BQN', ('bqn',), ('*.bqn',), ()),
    'BSTLexer': ('pip._vendor.pygments.lexers.bibtex', 'BST', ('bst', 'bst-pybtex'), ('*.bst',), ()),
    'BareLexer': ('pip._vendor.pygments.lexers.bare', 'BARE', ('bare',), ('*.bare',), ()),
    'BaseMakefileLexer': ('pip._vendor.pygments.lexers.make', 'Base Makefile', ('basemake',), (), ()),
    'BashLexer': ('pip._vendor.pygments.lexers.shell', 'Bash', ('bash', 'sh', 'ksh', 'zsh', 'shell', 'openrc'), ('*.sh', '*.ksh', '*.bash', '*.ebuild', '*.eclass', '*.exheres-0', '*.exlib', '*.zsh', '.bashrc', 'bashrc', '.bash_*', 'bash_*', 'zshrc', '.zshrc', '.kshrc', 'kshrc', 'PKGBUILD'), ('application/x-sh', 'application/x-shellscript', 'text/x-shellscript')),
    'BashSessionLexer': ('pip._vendor.pygments.lexers.shell', 'Bash Session', ('console', 'shell-session'), ('*.sh-session', '*.shell-session'), ('application/x-shell-session', 'application/x-sh-session')),
    'BatchLexer': ('pip._vendor.pygments.lexers.shell', 'Batchfile', ('batch', 'bat', 'dosbatch', 'winbatch'), ('*.bat', '*.cmd'), ('application/x-dos-batch',)),
    'BddLexer': ('pip._vendor.pygments.lexers.bdd', 'Bdd', ('bdd',), ('*.feature',), ('text/x-bdd',)),
    'BefungeLexer': ('pip._vendor.pygments.lexers.esoteric', 'Befunge', ('befunge',), ('*.befunge',), ('application/x-befunge',)),
    'BerryLexer': ('pip._vendor.pygments.lexers.berry', 'Berry', ('berry', 'be'), ('*.be',), ('text/x-berry', 'application/x-berry')),
    'BibTeXLexer': ('pip._vendor.pygments.lexers.bibtex', 'BibTeX', ('bibtex', 'bib'), ('*.bib',), ('text/x-bibtex',)),
    'BlitzBasicLexer': ('pip._vendor.pygments.lexers.basic', 'BlitzBasic', ('blitzbasic', 'b3d', 'bplus'), ('*.bb', '*.decls'), ('text/x-bb',)),
    'BlitzMaxLexer': ('pip._vendor.pygments.lexers.basic', 'BlitzMax', ('blitzmax', 'bmax'), ('*.bmx',), ('text/x-bmx',)),
    'BlueprintLexer': ('pip._vendor.pygments.lexers.blueprint', 'Blueprint', ('blueprint',), ('*.blp',), ('text/x-blueprint',)),
    'BnfLexer': ('pip._vendor.pygments.lexers.grammar_notation', 'BNF', ('bnf',), ('*.bnf',), ('text/x-bnf',)),
    'BoaLexer': ('pip._vendor.pygments.lexers.boa', 'Boa', ('boa',), ('*.boa',), ()),
    'BooLexer': ('pip._vendor.pygments.lexers.dotnet', 'Boo', ('boo',), ('*.boo',), ('text/x-boo',)),
    'BoogieLexer': ('pip._vendor.pygments.lexers.verification', 'Boogie', ('boogie',), ('*.bpl',), ()),
    'BrainfuckLexer': ('pip._vendor.pygments.lexers.esoteric', 'Brainfuck', ('brainfuck', 'bf'), ('*.bf', '*.b'), ('application/x-brainfuck',)),
    'BugsLexer': ('pip._vendor.pygments.lexers.modeling', 'BUGS', ('bugs', 'winbugs', 'openbugs'), ('*.bug',), ()),
    'CAmkESLexer': ('pip._vendor.pygments.lexers.esoteric', 'CAmkES', ('camkes', 'idl4'), ('*.camkes', '*.idl4'), ()),
    'CLexer': ('pip._vendor.pygments.lexers.c_cpp', 'C', ('c',), ('*.c', '*.h', '*.idc', '*.x[bp]m'), ('text/x-chdr', 'text/x-csrc', 'image/x-xbitmap', 'image/x-xpixmap')),
    'CMakeLexer': ('pip._vendor.pygments.lexers.make', 'CMake', ('cmake',), ('*.cmake', 'CMakeLists.txt'), ('text/x-cmake',)),
    'CObjdumpLexer': ('pip._vendor.pygments.lexers.asm', 'c-objdump', ('c-objdump',), ('*.c-objdump',), ('text/x-c-objdump',)),
    'CPSALexer': ('pip._vendor.pygments.lexers.lisp', 'CPSA', ('cpsa',), ('*.cpsa',), ()),
    'CSSUL4Lexer': ('pip._vendor.pygments.lexers.ul4', 'CSS+UL4', ('css+ul4',), ('*.cssul4',), ()),
    'CSharpAspxLexer': ('pip._vendor.pygments.lexers.dotnet', 'aspx-cs', ('aspx-cs',), ('*.aspx', '*.asax', '*.ascx', '*.ashx', '*.asmx', '*.axd'), ()),
    'CSharpLexer': ('pip._vendor.pygments.lexers.dotnet', 'C#', ('csharp', 'c#', 'cs'), ('*.cs',), ('text/x-csharp',)),
    'Ca65Lexer': ('pip._vendor.pygments.lexers.asm', 'ca65 assembler', ('ca65',), ('*.s',), ()),
    'CadlLexer': ('pip._vendor.pygments.lexers.archetype', 'cADL', ('cadl',), ('*.cadl',), ()),
    'CapDLLexer': ('pip._vendor.pygments.lexers.esoteric', 'CapDL', ('capdl',), ('*.cdl',), ()),
    'CapnProtoLexer': ('pip._vendor.pygments.lexers.capnproto', "Cap'n Proto", ('capnp',), ('*.capnp',), ()),
    'CarbonLexer': ('pip._vendor.pygments.lexers.carbon', 'Carbon', ('carbon',), ('*.carbon',), ('text/x-carbon',)),
    'CbmBasicV2Lexer': ('pip._vendor.pygments.lexers.basic', 'CBM BASIC V2', ('cbmbas',), ('*.bas',), ()),
    'CddlLexer': ('pip._vendor.pygments.lexers.cddl', 'CDDL', ('cddl',), ('*.cddl',), ('text/x-cddl',)),
    'CeylonLexer': ('pip._vendor.pygments.lexers.jvm', 'Ceylon', ('ceylon',), ('*.ceylon',), ('text/x-ceylon',)),
    'Cfengine3Lexer': ('pip._vendor.pygments.lexers.configs', 'CFEngine3', ('cfengine3', 'cf3'), ('*.cf',), ()),
    'ChaiscriptLexer': ('pip._vendor.pygments.lexers.scripting', 'ChaiScript', ('chaiscript', 'chai'), ('*.chai',), ('text/x-chaiscript', 'application/x-chaiscript')),
    'ChapelLexer': ('pip._vendor.pygments.lexers.chapel', 'Chapel', ('chapel', 'chpl'), ('*.chpl',), ()),
    'CharmciLexer': ('pip._vendor.pygments.lexers.c_like', 'Charmci', ('charmci',), ('*.ci',), ()),
    'CheetahHtmlLexer': ('pip._vendor.pygments.lexers.templates', 'HTML+Cheetah', ('html+cheetah', 'html+spitfire', 'htmlcheetah'), (), ('text/html+cheetah', 'text/html+spitfire')),
    'CheetahJavascriptLexer': ('pip._vendor.pygments.lexers.templates', 'JavaScript+Cheetah', ('javascript+cheetah', 'js+cheetah', 'javascript+spitfire', 'js+spitfire'), (), ('application/x-javascript+cheetah', 'text/x-javascript+cheetah', 'text/javascript+cheetah', 'application/x-javascript+spitfire', 'text/x-javascript+spitfire', 'text/javascript+spitfire')),
    'CheetahLexer': ('pip._vendor.pygments.lexers.templates', 'Cheetah', ('cheetah', 'spitfire'), ('*.tmpl', '*.spt'), ('application/x-cheetah', 'application/x-spitfire')),
    'CheetahXmlLexer': ('pip._vendor.pygments.lexers.templates', 'XML+Cheetah', ('xml+cheetah', 'xml+spitfire'), (), ('application/xml+cheetah', 'application/xml+spitfire')),
    'CirruLexer': ('pip._vendor.pygments.lexers.webmisc', 'Cirru', ('cirru',), ('*.cirru',), ('text/x-cirru',)),
    'ClayLexer': ('pip._vendor.pygments.lexers.c_like', 'Clay', ('clay',), ('*.clay',), ('text/x-clay',)),
    'CleanLexer': ('pip._vendor.pygments.lexers.clean', 'Clean', ('clean',), ('*.icl', '*.dcl'), ()),
    'ClojureLexer': ('pip._vendor.pygments.lexers.jvm', 'Clojure', ('clojure', 'clj'), ('*.clj', '*.cljc'), ('text/x-clojure', 'application/x-clojure')),
    'ClojureScriptLexer': ('pip._vendor.pygments.lexers.jvm', 'ClojureScript', ('clojurescript', 'cljs'), ('*.cljs',), ('text/x-clojurescript', 'application/x-clojurescript')),
    'CobolFreeformatLexer': ('pip._vendor.pygments.lexers.business', 'COBOLFree', ('cobolfree',), ('*.cbl', '*.CBL'), ()),
    'CobolLexer': ('pip._vendor.pygments.lexers.business', 'COBOL', ('cobol',), ('*.cob', '*.COB', '*.cpy', '*.CPY'), ('text/x-cobol',)),
    'CoffeeScriptLexer': ('pip._vendor.pygments.lexers.javascript', 'CoffeeScript', ('coffeescript', 'coffee-script', 'coffee'), ('*.coffee',), ('text/coffeescript',)),
    'ColdfusionCFCLexer': ('pip._vendor.pygments.lexers.templates', 'Coldfusion CFC', ('cfc',), ('*.cfc',), ()),
    'ColdfusionHtmlLexer': ('pip._vendor.pygments.lexers.templates', 'Coldfusion HTML', ('cfm',), ('*.cfm', '*.cfml'), ('application/x-coldfusion',)),
    'ColdfusionLexer': ('pip._vendor.pygments.lexers.templates', 'cfstatement', ('cfs',), (), ()),
    'Comal80Lexer': ('pip._vendor.pygments.lexers.comal', 'COMAL-80', ('comal', 'comal80'), ('*.cml', '*.comal'), ()),
    'CommonLispLexer': ('pip._vendor.pygments.lexers.lisp', 'Common Lisp', ('common-lisp', 'cl', 'lisp'), ('*.cl', '*.lisp'), ('text/x-common-lisp',)),
    'ComponentPascalLexer': ('pip._vendor.pygments.lexers.oberon', 'Component Pascal', ('componentpascal', 'cp'), ('*.cp', '*.cps'), ('text/x-component-pascal',)),
    'CoqLexer': ('pip._vendor.pygments.lexers.theorem', 'Coq', ('coq',), ('*.v',), ('text/x-coq',)),
    'CplintLexer': ('pip._vendor.pygments.lexers.cplint', 'cplint', ('cplint',), ('*.ecl', '*.prolog', '*.pro', '*.pl', '*.P', '*.lpad', '*.cpl'), ('text/x-cplint',)),
    'CppLexer': ('pip._vendor.pygments.lexers.c_cpp', 'C++', ('cpp', 'c++'), ('*.cpp', '*.hpp', '*.c++', '*.h++', '*.cc', '*.hh', '*.cxx', '*.hxx', '*.C', '*.H', '*.cp', '*.CPP', '*.tpp'), ('text/x-c++hdr', 'text/x-c++src')),
    'CppObjdumpLexer': ('pip._vendor.pygments.lexers.asm', 'cpp-objdump', ('cpp-objdump', 'c++-objdumb', 'cxx-objdump'), ('*.cpp-objdump', '*.c++-objdump', '*.cxx-objdump'), ('text/x-cpp-objdump',)),
    'CrmshLexer': ('pip._vendor.pygments.lexers.dsls', 'Crmsh', ('crmsh', 'pcmk'), ('*.crmsh', '*.pcmk'), ()),
    'CrocLexer': ('pip._vendor.pygments.lexers.d', 'Croc', ('croc',), ('*.croc',), ('text/x-crocsrc',)),
    'CryptolLexer': ('pip._vendor.pygments.lexers.haskell', 'Cryptol', ('cryptol', 'cry'), ('*.cry',), ('text/x-cryptol',)),
    'CrystalLexer': ('pip._vendor.pygments.lexers.crystal', 'Crystal', ('cr', 'crystal'), ('*.cr',), ('text/x-crystal',)),
    'CsoundDocumentLexer': ('pip._vendor.pygments.lexers.csound', 'Csound Document', ('csound-document', 'csound-csd'), ('*.csd',), ()),
    'CsoundOrchestraLexer': ('pip._vendor.pygments.lexers.csound', 'Csound Orchestra', ('csound', 'csound-orc'), ('*.orc', '*.udo'), ()),
    'CsoundScoreLexer': ('pip._vendor.pygments.lexers.csound', 'Csound Score', ('csound-score', 'csound-sco'), ('*.sco',), ()),
    'CssDjangoLexer': ('pip._vendor.pygments.lexers.templates', 'CSS+Django/Jinja', ('css+django', 'css+jinja'), ('*.css.j2', '*.css.jinja2'), ('text/css+django', 'text/css+jinja')),
    'CssErbLexer': ('pip._vendor.pygments.lexers.templates', 'CSS+Ruby', ('css+ruby', 'css+erb'), (), ('text/css+ruby',)),
    'CssGenshiLexer': ('pip._vendor.pygments.lexers.templates', 'CSS+Genshi Text', ('css+genshitext', 'css+genshi'), (), ('text/css+genshi',)),
    'CssLexer': ('pip._vendor.pygments.lexers.css', 'CSS', ('css',), ('*.css',), ('text/css',)),
    'CssPhpLexer': ('pip._vendor.pygments.lexers.templates', 'CSS+PHP', ('css+php',), (), ('text/css+php',)),
    'CssSmartyLexer': ('pip._vendor.pygments.lexers.templates', 'CSS+Smarty', ('css+smarty',), (), ('text/css+smarty',)),
    'CudaLexer': ('pip._vendor.pygments.lexers.c_like', 'CUDA', ('cuda', 'cu'), ('*.cu', '*.cuh'), ('text/x-cuda',)),
    'CypherLexer': ('pip._vendor.pygments.lexers.graph', 'Cypher', ('cypher',), ('*.cyp', '*.cypher'), ()),
    'CythonLexer': ('pip._vendor.pygments.lexers.python', 'Cython', ('cython', 'pyx', 'pyrex'), ('*.pyx', '*.pxd', '*.pxi'), ('text/x-cython', 'application/x-cython')),
    'DLexer': ('pip._vendor.pygments.lexers.d', 'D', ('d',), ('*.d', '*.di'), ('text/x-dsrc',)),
    'DObjdumpLexer': ('pip._vendor.pygments.lexers.asm', 'd-objdump', ('d-objdump',), ('*.d-objdump',), ('text/x-d-objdump',)),
    'DarcsPatchLexer': ('pip._vendor.pygments.lexers.diff', 'Darcs Patch', ('dpatch',), ('*.dpatch', '*.darcspatch'), ()),
    'DartLexer': ('pip._vendor.pygments.lexers.javascript', 'Dart', ('dart',), ('*.dart',), ('text/x-dart',)),
    'Dasm16Lexer': ('pip._vendor.pygments.lexers.asm', 'DASM16', ('dasm16',), ('*.dasm16', '*.dasm'), ('text/x-dasm16',)),
    'DaxLexer': ('pip._vendor.pygments.lexers.dax', 'Dax', ('dax',), ('*.dax',), ()),
    'DebianControlLexer': ('pip._vendor.pygments.lexers.installers', 'Debian Control file', ('debcontrol', 'control'), ('control',), ()),
    'DelphiLexer': ('pip._vendor.pygments.lexers.pascal', 'Delphi', ('delphi', 'pas', 'pascal', 'objectpascal'), ('*.pas', '*.dpr'), ('text/x-pascal',)),
    'DesktopLexer': ('pip._vendor.pygments.lexers.configs', 'Desktop file', ('desktop',), ('*.desktop',), ('application/x-desktop',)),
    'DevicetreeLexer': ('pip._vendor.pygments.lexers.devicetree', 'Devicetree', ('devicetree', 'dts'), ('*.dts', '*.dtsi'), ('text/x-c',)),
    'DgLexer': ('pip._vendor.pygments.lexers.python', 'dg', ('dg',), ('*.dg',), ('text/x-dg',)),
    'DiffLexer': ('pip._vendor.pygments.lexers.diff', 'Diff', ('diff', 'udiff'), ('*.diff', '*.patch'), ('text/x-diff', 'text/x-patch')),
    'DjangoLexer': ('pip._vendor.pygments.lexers.templates', 'Django/Jinja', ('django', 'jinja'), (), ('application/x-django-templating', 'application/x-jinja')),
    'DnsZoneLexer': ('pip._vendor.pygments.lexers.dns', 'Zone', ('zone',), ('*.zone',), ('text/dns',)),
    'DockerLexer': ('pip._vendor.pygments.lexers.configs', 'Docker', ('docker', 'dockerfile'), ('Dockerfile', '*.docker'), ('text/x-dockerfile-config',)),
    'DtdLexer': ('pip._vendor.pygments.lexers.html', 'DTD', ('dtd',), ('*.dtd',), ('application/xml-dtd',)),
    'DuelLexer': ('pip._vendor.pygments.lexers.webmisc', 'Duel', ('duel', 'jbst', 'jsonml+bst'), ('*.duel', '*.jbst'), ('text/x-duel', 'text/x-jbst')),
    'DylanConsoleLexer': ('pip._vendor.pygments.lexers.dylan', 'Dylan session', ('dylan-console', 'dylan-repl'), ('*.dylan-console',), ('text/x-dylan-console',)),
    'DylanLexer': ('pip._vendor.pygments.lexers.dylan', 'Dylan', ('dylan',), ('*.dylan', '*.dyl', '*.intr'), ('text/x-dylan',)),
    'DylanLidLexer': ('pip._vendor.pygments.lexers.dylan', 'DylanLID', ('dylan-lid', 'lid'), ('*.lid', '*.hdp'), ('text/x-dylan-lid',)),
    'ECLLexer': ('pip._vendor.pygments.lexers.ecl', 'ECL', ('ecl',), ('*.ecl',), ('application/x-ecl',)),
    'ECLexer': ('pip._vendor.pygments.lexers.c_like', 'eC', ('ec',), ('*.ec', '*.eh'), ('text/x-echdr', 'text/x-ecsrc')),
    'EarlGreyLexer': ('pip._vendor.pygments.lexers.javascript', 'Earl Grey', ('earl-grey', 'earlgrey', 'eg'), ('*.eg',), ('text/x-earl-grey',)),
    'EasytrieveLexer': ('pip._vendor.pygments.lexers.scripting', 'Easytrieve', ('easytrieve',), ('*.ezt', '*.mac'), ('text/x-easytrieve',)),
    'EbnfLexer': ('pip._vendor.pygments.lexers.parsers', 'EBNF', ('ebnf',), ('*.ebnf',), ('text/x-ebnf',)),
    'EiffelLexer': ('pip._vendor.pygments.lexers.eiffel', 'Eiffel', ('eiffel',), ('*.e',), ('text/x-eiffel',)),
    'ElixirConsoleLexer': ('pip._vendor.pygments.lexers.erlang', 'Elixir iex session', ('iex',), (), ('text/x-elixir-shellsession',)),
    'ElixirLexer': ('pip._vendor.pygments.lexers.erlang', 'Elixir', ('elixir', 'ex', 'exs'), ('*.ex', '*.eex', '*.exs', '*.leex'), ('text/x-elixir',)),
    'ElmLexer': ('pip._vendor.pygments.lexers.elm', 'Elm', ('elm',), ('*.elm',), ('text/x-elm',)),
    'ElpiLexer': ('pip._vendor.pygments.lexers.elpi', 'Elpi', ('elpi',), ('*.elpi',), ('text/x-elpi',)),
    'EmacsLispLexer': ('pip._vendor.pygments.lexers.lisp', 'EmacsLisp', ('emacs-lisp', 'elisp', 'emacs'), ('*.el',), ('text/x-elisp', 'application/x-elisp')),
    'EmailLexer': ('pip._vendor.pygments.lexers.email', 'E-mail', ('email', 'eml'), ('*.eml',), ('message/rfc822',)),
    'ErbLexer': ('pip._vendor.pygments.lexers.templates', 'ERB', ('erb',), (), ('application/x-ruby-templating',)),
    'ErlangLexer': ('pip._vendor.pygments.lexers.erlang', 'Erlang', ('erlang',), ('*.erl', '*.hrl', '*.es', '*.escript'), ('text/x-erlang',)),
    'ErlangShellLexer': ('pip._vendor.pygments.lexers.erlang', 'Erlang erl session', ('erl',), ('*.erl-sh',), ('text/x-erl-shellsession',)),
    'EvoqueHtmlLexer': ('pip._vendor.pygments.lexers.templates', 'HTML+Evoque', ('html+evoque',), ('*.html',), ('text/html+evoque',)),
    'EvoqueLexer': ('pip._vendor.pygments.lexers.templates', 'Evoque', ('evoque',), ('*.evoque',), ('application/x-evoque',)),
    'EvoqueXmlLexer': ('pip._vendor.pygments.lexers.templates', 'XML+Evoque', ('xml+evoque',), ('*.xml',), ('application/xml+evoque',)),
    'ExeclineLexer': ('pip._vendor.pygments.lexers.shell', 'execline', ('execline',), ('*.exec',), ()),
    'EzhilLexer': ('pip._vendor.pygments.lexers.ezhil', 'Ezhil', ('ezhil',), ('*.n',), ('text/x-ezhil',)),
    'FSharpLexer': ('pip._vendor.pygments.lexers.dotnet', 'F#', ('fsharp', 'f#'), ('*.fs', '*.fsi', '*.fsx'), ('text/x-fsharp',)),
    'FStarLexer': ('pip._vendor.pygments.lexers.ml', 'FStar', ('fstar',), ('*.fst', '*.fsti'), ('text/x-fstar',)),
    'FactorLexer': ('pip._vendor.pygments.lexers.factor', 'Factor', ('factor',), ('*.factor',), ('text/x-factor',)),
    'FancyLexer': ('pip._vendor.pygments.lexers.ruby', 'Fancy', ('fancy', 'fy'), ('*.fy', '*.fancypack'), ('text/x-fancysrc',)),
    'FantomLexer': ('pip._vendor.pygments.lexers.fantom', 'Fantom', ('fan',), ('*.fan',), ('application/x-fantom',)),
    'FelixLexer': ('pip._vendor.pygments.lexers.felix', 'Felix', ('felix', 'flx'), ('*.flx', '*.flxh'), ('text/x-felix',)),
    'FennelLexer': ('pip._vendor.pygments.lexers.lisp', 'Fennel', ('fennel', 'fnl'), ('*.fnl',), ()),
    'FiftLexer': ('pip._vendor.pygments.lexers.fift', 'Fift', ('fift', 'fif'), ('*.fif',), ()),
    'FishShellLexer': ('pip._vendor.pygments.lexers.shell', 'Fish', ('fish', 'fishshell'), ('*.fish', '*.load'), ('application/x-fish',)),
    'FlatlineLexer': ('pip._vendor.pygments.lexers.dsls', 'Flatline', ('flatline',), (), ('text/x-flatline',)),
    'FloScriptLexer': ('pip._vendor.pygments.lexers.floscript', 'FloScript', ('floscript', 'flo'), ('*.flo',), ()),
    'ForthLexer': ('pip._vendor.pygments.lexers.forth', 'Forth', ('forth',), ('*.frt', '*.fs'), ('application/x-forth',)),
    'FortranFixedLexer': ('pip._vendor.pygments.lexers.fortran', 'FortranFixed', ('fortranfixed',), ('*.f', '*.F'), ()),
    'FortranLexer': ('pip._vendor.pygments.lexers.fortran', 'Fortran', ('fortran', 'f90'), ('*.f03', '*.f90', '*.F03', '*.F90'), ('text/x-fortran',)),
    'FoxProLexer': ('pip._vendor.pygments.lexers.foxpro', 'FoxPro', ('foxpro', 'vfp', 'clipper', 'xbase'), ('*.PRG', '*.prg'), ()),
    'FreeFemLexer': ('pip._vendor.pygments.lexers.freefem', 'Freefem', ('freefem',), ('*.edp',), ('text/x-freefem',)),
    'FuncLexer': ('pip._vendor.pygments.lexers.func', 'FunC', ('func', 'fc'), ('*.fc', '*.func'), ()),
    'FutharkLexer': ('pip._vendor.pygments.lexers.futhark', 'Futhark', ('futhark',), ('*.fut',), ('text/x-futhark',)),
    'GAPConsoleLexer': ('pip._vendor.pygments.lexers.algebra', 'GAP session', ('gap-console', 'gap-repl'), ('*.tst',), ()),
    'GAPLexer': ('pip._vendor.pygments.lexers.algebra', 'GAP', ('gap',), ('*.g', '*.gd', '*.gi', '*.gap'), ()),
    'GDScriptLexer': ('pip._vendor.pygments.lexers.gdscript', 'GDScript', ('gdscript', 'gd'), ('*.gd',), ('text/x-gdscript', 'application/x-gdscript')),
    'GLShaderLexer': ('pip._vendor.pygments.lexers.graphics', 'GLSL', ('glsl',), ('*.vert', '*.frag', '*.geo'), ('text/x-glslsrc',)),
    'GSQLLexer': ('pip._vendor.pygments.lexers.gsql', 'GSQL', ('gsql',), ('*.gsql',), ()),
    'GasLexer': ('pip._vendor.pygments.lexers.asm', 'GAS', ('gas', 'asm'), ('*.s', '*.S'), ('text/x-gas',)),
    'GcodeLexer': ('pip._vendor.pygments.lexers.gcodelexer', 'g-code', ('gcode',), ('*.gcode',), ()),
    'GenshiLexer': ('pip._vendor.pygments.lexers.templates', 'Genshi', ('genshi', 'kid', 'xml+genshi', 'xml+kid'), ('*.kid',), ('application/x-genshi', 'application/x-kid')),
    'GenshiTextLexer': ('pip._vendor.pygments.lexers.templates', 'Genshi Text', ('genshitext',), (), ('application/x-genshi-text', 'text/x-genshi')),
    'GettextLexer': ('pip._vendor.pygments.lexers.textfmts', 'Gettext Catalog', ('pot', 'po'), ('*.pot', '*.po'), ('application/x-gettext', 'text/x-gettext', 'text/gettext')),
    'GherkinLexer': ('pip._vendor.pygments.lexers.testing', 'Gherkin', ('gherkin', 'cucumber'), ('*.feature',), ('text/x-gherkin',)),
    'GnuplotLexer': ('pip._vendor.pygments.lexers.graphics', 'Gnuplot', ('gnuplot',), ('*.plot', '*.plt'), ('text/x-gnuplot',)),
    'GoLexer': ('pip._vendor.pygments.lexers.go', 'Go', ('go', 'golang'), ('*.go',), ('text/x-gosrc',)),
    'GoloLexer': ('pip._vendor.pygments.lexers.jvm', 'Golo', ('golo',), ('*.golo',), ()),
    'GoodDataCLLexer': ('pip._vendor.pygments.lexers.business', 'GoodData-CL', ('gooddata-cl',), ('*.gdc',), ('text/x-gooddata-cl',)),
    'GosuLexer': ('pip._vendor.pygments.lexers.jvm', 'Gosu', ('gosu',), ('*.gs', '*.gsx', '*.gsp', '*.vark'), ('text/x-gosu',)),
    'GosuTemplateLexer': ('pip._vendor.pygments.lexers.jvm', 'Gosu Template', ('gst',), ('*.gst',), ('text/x-gosu-template',)),
    'GraphQLLexer': ('pip._vendor.pygments.lexers.graphql', 'GraphQL', ('graphql',), ('*.graphql',), ()),
    'GraphvizLexer': ('pip._vendor.pygments.lexers.graphviz', 'Graphviz', ('graphviz', 'dot'), ('*.gv', '*.dot'), ('text/x-graphviz', 'text/vnd.graphviz')),
    'GroffLexer': ('pip._vendor.pygments.lexers.markup', 'Groff', ('groff', 'nroff', 'man'), ('*.[1-9]', '*.man', '*.1p', '*.3pm'), ('application/x-troff', 'text/troff')),
    'GroovyLexer': ('pip._vendor.pygments.lexers.jvm', 'Groovy', ('groovy',), ('*.groovy', '*.gradle'), ('text/x-groovy',)),
    'HLSLShaderLexer': ('pip._vendor.pygments.lexers.graphics', 'HLSL', ('hlsl',), ('*.hlsl', '*.hlsli'), ('text/x-hlsl',)),
    'HTMLUL4Lexer': ('pip._vendor.pygments.lexers.ul4', 'HTML+UL4', ('html+ul4',), ('*.htmlul4',), ()),
    'HamlLexer': ('pip._vendor.pygments.lexers.html', 'Haml', ('haml',), ('*.haml',), ('text/x-haml',)),
    'HandlebarsHtmlLexer': ('pip._vendor.pygments.lexers.templates', 'HTML+Handlebars', ('html+handlebars',), ('*.handlebars', '*.hbs'), ('text/html+handlebars', 'text/x-handlebars-template')),
    'HandlebarsLexer': ('pip._vendor.pygments.lexers.templates', 'Handlebars', ('handlebars',), (), ()),
    'HaskellLexer': ('pip._vendor.pygments.lexers.haskell', 'Haskell', ('haskell', 'hs'), ('*.hs',), ('text/x-haskell',)),
    'HaxeLexer': ('pip._vendor.pygments.lexers.haxe', 'Haxe', ('haxe', 'hxsl', 'hx'), ('*.hx', '*.hxsl'), ('text/haxe', 'text/x-haxe', 'text/x-hx')),
    'HexdumpLexer': ('pip._vendor.pygments.lexers.hexdump', 'Hexdump', ('hexdump',), (), ()),
    'HsailLexer': ('pip._vendor.pygments.lexers.asm', 'HSAIL', ('hsail', 'hsa'), ('*.hsail',), ('text/x-hsail',)),
    'HspecLexer': ('pip._vendor.pygments.lexers.haskell', 'Hspec', ('hspec',), ('*Spec.hs',), ()),
    'HtmlDjangoLexer': ('pip._vendor.pygments.lexers.templates', 'HTML+Django/Jinja', ('html+django', 'html+jinja', 'htmldjango'), ('*.html.j2', '*.htm.j2', '*.xhtml.j2', '*.html.jinja2', '*.htm.jinja2', '*.xhtml.jinja2'), ('text/html+django', 'text/html+jinja')),
    'HtmlGenshiLexer': ('pip._vendor.pygments.lexers.templates', 'HTML+Genshi', ('html+genshi', 'html+kid'), (), ('text/html+genshi',)),
    'HtmlLexer': ('pip._vendor.pygments.lexers.html', 'HTML', ('html',), ('*.html', '*.htm', '*.xhtml', '*.xslt'), ('text/html', 'application/xhtml+xml')),
    'HtmlPhpLexer': ('pip._vendor.pygments.lexers.templates', 'HTML+PHP', ('html+php',), ('*.phtml',), ('application/x-php', 'application/x-httpd-php', 'application/x-httpd-php3', 'application/x-httpd-php4', 'application/x-httpd-php5')),
    'HtmlSmartyLexer': ('pip._vendor.pygments.lexers.templates', 'HTML+Smarty', ('html+smarty',), (), ('text/html+smarty',)),
    'HttpLexer': ('pip._vendor.pygments.lexers.textfmts', 'HTTP', ('http',), (), ()),
    'HxmlLexer': ('pip._vendor.pygments.lexers.haxe', 'Hxml', ('haxeml', 'hxml'), ('*.hxml',), ()),
    'HyLexer': ('pip._vendor.pygments.lexers.lisp', 'Hy', ('hylang', 'hy'), ('*.hy',), ('text/x-hy', 'application/x-hy')),
    'HybrisLexer': ('pip._vendor.pygments.lexers.scripting', 'Hybris', ('hybris',), ('*.hyb',), ('text/x-hybris', 'application/x-hybris')),
    'IDLLexer': ('pip._vendor.pygments.lexers.idl', 'IDL', ('idl',), ('*.pro',), ('text/idl',)),
    'IconLexer': ('pip._vendor.pygments.lexers.unicon', 'Icon', ('icon',), ('*.icon', '*.ICON'), ()),
    'IdrisLexer': ('pip._vendor.pygments.lexers.haskell', 'Idris', ('idris', 'idr'), ('*.idr',), ('text/x-idris',)),
    'IgorLexer': ('pip._vendor.pygments.lexers.igor', 'Igor', ('igor', 'igorpro'), ('*.ipf',), ('text/ipf',)),
    'Inform6Lexer': ('pip._vendor.pygments.lexers.int_fiction', 'Inform 6', ('inform6', 'i6'), ('*.inf',), ()),
    'Inform6TemplateLexer': ('pip._vendor.pygments.lexers.int_fiction', 'Inform 6 template', ('i6t',), ('*.i6t',), ()),
    'Inform7Lexer': ('pip._vendor.pygments.lexers.int_fiction', 'Inform 7', ('inform7', 'i7'), ('*.ni', '*.i7x'), ()),
    'IniLexer': ('pip._vendor.pygments.lexers.configs', 'INI', ('ini', 'cfg', 'dosini'), ('*.ini', '*.cfg', '*.inf', '.editorconfig'), ('text/x-ini', 'text/inf')),
    'IoLexer': ('pip._vendor.pygments.lexers.iolang', 'Io', ('io',), ('*.io',), ('text/x-iosrc',)),
    'IokeLexer': ('pip._vendor.pygments.lexers.jvm', 'Ioke', ('ioke', 'ik'), ('*.ik',), ('text/x-iokesrc',)),
    'IrcLogsLexer': ('pip._vendor.pygments.lexers.textfmts', 'IRC logs', ('irc',), ('*.weechatlog',), ('text/x-irclog',)),
    'IsabelleLexer': ('pip._vendor.pygments.lexers.theorem', 'Isabelle', ('isabelle',), ('*.thy',), ('text/x-isabelle',)),
    'JLexer': ('pip._vendor.pygments.lexers.j', 'J', ('j',), ('*.ijs',), ('text/x-j',)),
    'JMESPathLexer': ('pip._vendor.pygments.lexers.jmespath', 'JMESPath', ('jmespath', 'jp'), ('*.jp',), ()),
    'JSLTLexer': ('pip._vendor.pygments.lexers.jslt', 'JSLT', ('jslt',), ('*.jslt',), ('text/x-jslt',)),
    'JagsLexer': ('pip._vendor.pygments.lexers.modeling', 'JAGS', ('jags',), ('*.jag', '*.bug'), ()),
    'JanetLexer': ('pip._vendor.pygments.lexers.lisp', 'Janet', ('janet',), ('*.janet', '*.jdn'), ('text/x-janet', 'application/x-janet')),
    'JasminLexer': ('pip._vendor.pygments.lexers.jvm', 'Jasmin', ('jasmin', 'jasminxt'), ('*.j',), ()),
    'JavaLexer': ('pip._vendor.pygments.lexers.jvm', 'Java', ('java',), ('*.java',), ('text/x-java',)),
    'JavascriptDjangoLexer': ('pip._vendor.pygments.lexers.templates', 'JavaScript+Django/Jinja', ('javascript+django', 'js+django', 'javascript+jinja', 'js+jinja'), ('*.js.j2', '*.js.jinja2'), ('application/x-javascript+django', 'application/x-javascript+jinja', 'text/x-javascript+django', 'text/x-javascript+jinja', 'text/javascript+django', 'text/javascript+jinja')),
    'JavascriptErbLexer': ('pip._vendor.pygments.lexers.templates', 'JavaScript+Ruby', ('javascript+ruby', 'js+ruby', 'javascript+erb', 'js+erb'), (), ('application/x-javascript+ruby', 'text/x-javascript+ruby', 'text/javascript+ruby')),
    'JavascriptGenshiLexer': ('pip._vendor.pygments.lexers.templates', 'JavaScript+Genshi Text', ('js+genshitext', 'js+genshi', 'javascript+genshitext', 'javascript+genshi'), (), ('application/x-javascript+genshi', 'text/x-javascript+genshi', 'text/javascript+genshi')),
    'JavascriptLexer': ('pip._vendor.pygments.lexers.javascript', 'JavaScript', ('javascript', 'js'), ('*.js', '*.jsm', '*.mjs', '*.cjs'), ('application/javascript', 'application/x-javascript', 'text/x-javascript', 'text/javascript')),
    'JavascriptPhpLexer': ('pip._vendor.pygments.lexers.templates', 'JavaScript+PHP', ('javascript+php', 'js+php'), (), ('application/x-javascript+php', 'text/x-javascript+php', 'text/javascript+php')),
    'JavascriptSmartyLexer': ('pip._vendor.pygments.lexers.templates', 'JavaScript+Smarty', ('javascript+smarty', 'js+smarty'), (), ('application/x-javascript+smarty', 'text/x-javascript+smarty', 'text/javascript+smarty')),
    'JavascriptUL4Lexer': ('pip._vendor.pygments.lexers.ul4', 'Javascript+UL4', ('js+ul4',), ('*.jsul4',), ()),
    'JclLexer': ('pip._vendor.pygments.lexers.scripting', 'JCL', ('jcl',), ('*.jcl',), ('text/x-jcl',)),
    'JsgfLexer': ('pip._vendor.pygments.lexers.grammar_notation', 'JSGF', ('jsgf',), ('*.jsgf',), ('application/jsgf', 'application/x-jsgf', 'text/jsgf')),
    'JsonBareObjectLexer': ('pip._vendor.pygments.lexers.data', 'JSONBareObject', (), (), ()),
    'JsonLdLexer': ('pip._vendor.pygments.lexers.data', 'JSON-LD', ('jsonld', 'json-ld'), ('*.jsonld',), ('application/ld+json',)),
    'JsonLexer': ('pip._vendor.pygments.lexers.data', 'JSON', ('json', 'json-object'), ('*.json', '*.jsonl', '*.ndjson', 'Pipfile.lock'), ('application/json', 'application/json-object', 'application/x-ndjson', 'application/jsonl', 'application/json-seq')),
    'JsonnetLexer': ('pip._vendor.pygments.lexers.jsonnet', 'Jsonnet', ('jsonnet',), ('*.jsonnet', '*.libsonnet'), ()),
    'JspLexer': ('pip._vendor.pygments.lexers.templates', 'Java Server Page', ('jsp',), ('*.jsp',), ('application/x-jsp',)),
    'JsxLexer': ('pip._vendor.pygments.lexers.jsx', 'JSX', ('jsx', 'react'), ('*.jsx', '*.react'), ('text/jsx', 'text/typescript-jsx')),
    'JuliaConsoleLexer': ('pip._vendor.pygments.lexers.julia', 'Julia console', ('jlcon', 'julia-repl'), (), ()),
    'JuliaLexer': ('pip._vendor.pygments.lexers.julia', 'Julia', ('julia', 'jl'), ('*.jl',), ('text/x-julia', 'application/x-julia')),
    'JuttleLexer': ('pip._vendor.pygments.lexers.javascript', 'Juttle', ('juttle',), ('*.juttle',), ('application/juttle', 'application/x-juttle', 'text/x-juttle', 'text/juttle')),
    'KLexer': ('pip._vendor.pygments.lexers.q', 'K', ('k',), ('*.k',), ()),
    'KalLexer': ('pip._vendor.pygments.lexers.javascript', 'Kal', ('kal',), ('*.kal',), ('text/kal', 'application/kal')),
    'KconfigLexer': ('pip._vendor.pygments.lexers.configs', 'Kconfig', ('kconfig', 'menuconfig', 'linux-config', 'kernel-config'), ('Kconfig*', '*Config.in*', 'external.in*', 'standard-modules.in'), ('text/x-kconfig',)),
    'KernelLogLexer': ('pip._vendor.pygments.lexers.textfmts', 'Kernel log', ('kmsg', 'dmesg'), ('*.kmsg', '*.dmesg'), ()),
    'KokaLexer': ('pip._vendor.pygments.lexers.haskell', 'Koka', ('koka',), ('*.kk', '*.kki'), ('text/x-koka',)),
    'KotlinLexer': ('pip._vendor.pygments.lexers.jvm', 'Kotlin', ('kotlin',), ('*.kt', '*.kts'), ('text/x-kotlin',)),
    'KuinLexer': ('pip._vendor.pygments.lexers.kuin', 'Kuin', ('kuin',), ('*.kn',), ()),
    'KustoLexer': ('pip._vendor.pygments.lexers.kusto', 'Kusto', ('kql', 'kusto'), ('*.kql', '*.kusto', '.csl'), ()),
    'LSLLexer': ('pip._vendor.pygments.lexers.scripting', 'LSL', ('lsl',), ('*.lsl',), ('text/x-lsl',)),
    'LassoCssLexer': ('pip._vendor.pygments.lexers.templates', 'CSS+Lasso', ('css+lasso',), (), ('text/css+lasso',)),
    'LassoHtmlLexer': ('pip._vendor.pygments.lexers.templates', 'HTML+Lasso', ('html+lasso',), (), ('text/html+lasso', 'application/x-httpd-lasso', 'application/x-httpd-lasso[89]')),
    'LassoJavascriptLexer': ('pip._vendor.pygments.lexers.templates', 'JavaScript+Lasso', ('javascript+lasso', 'js+lasso'), (), ('application/x-javascript+lasso', 'text/x-javascript+lasso', 'text/javascript+lasso')),
    'LassoLexer': ('pip._vendor.pygments.lexers.javascript', 'Lasso', ('lasso', 'lassoscript'), ('*.lasso', '*.lasso[89]'), ('text/x-lasso',)),
    'LassoXmlLexer': ('pip._vendor.pygments.lexers.templates', 'XML+Lasso', ('xml+lasso',), (), ('application/xml+lasso',)),
    'LdaprcLexer': ('pip._vendor.pygments.lexers.ldap', 'LDAP configuration file', ('ldapconf', 'ldaprc'), ('.ldaprc', 'ldaprc', 'ldap.conf'), ('text/x-ldapconf',)),
    'LdifLexer': ('pip._vendor.pygments.lexers.ldap', 'LDIF', ('ldif',), ('*.ldif',), ('text/x-ldif',)),
    'Lean3Lexer': ('pip._vendor.pygments.lexers.lean', 'Lean', ('lean', 'lean3'), ('*.lean',), ('text/x-lean', 'text/x-lean3')),
    'Lean4Lexer': ('pip._vendor.pygments.lexers.lean', 'Lean4', ('lean4',), ('*.lean',), ('text/x-lean4',)),
    'LessCssLexer': ('pip._vendor.pygments.lexers.css', 'LessCss', ('less',), ('*.less',), ('text/x-less-css',)),
    'LighttpdConfLexer': ('pip._vendor.pygments.lexers.configs', 'Lighttpd configuration file', ('lighttpd', 'lighty'), ('lighttpd.conf',), ('text/x-lighttpd-conf',)),
    'LilyPondLexer': ('pip._vendor.pygments.lexers.lilypond', 'LilyPond', ('lilypond',), ('*.ly',), ()),
    'LimboLexer': ('pip._vendor.pygments.lexers.inferno', 'Limbo', ('limbo',), ('*.b',), ('text/limbo',)),
    'LiquidLexer': ('pip._vendor.pygments.lexers.templates', 'liquid', ('liquid',), ('*.liquid',), ()),
    'LiterateAgdaLexer': ('pip._vendor.pygments.lexers.haskell', 'Literate Agda', ('literate-agda', 'lagda'), ('*.lagda',), ('text/x-literate-agda',)),
    'LiterateCryptolLexer': ('pip._vendor.pygments.lexers.haskell', 'Literate Cryptol', ('literate-cryptol', 'lcryptol', 'lcry'), ('*.lcry',), ('text/x-literate-cryptol',)),
    'LiterateHaskellLexer': ('pip._vendor.pygments.lexers.haskell', 'Literate Haskell', ('literate-haskell', 'lhaskell', 'lhs'), ('*.lhs',), ('text/x-literate-haskell',)),
    'LiterateIdrisLexer': ('pip._vendor.pygments.lexers.haskell', 'Literate Idris', ('literate-idris', 'lidris', 'lidr'), ('*.lidr',), ('text/x-literate-idris',)),
    'LiveScriptLexer': ('pip._vendor.pygments.lexers.javascript', 'LiveScript', ('livescript', 'live-script'), ('*.ls',), ('text/livescript',)),
    'LlvmLexer': ('pip._vendor.pygments.lexers.asm', 'LLVM', ('llvm',), ('*.ll',), ('text/x-llvm',)),
    'LlvmMirBodyLexer': ('pip._vendor.pygments.lexers.asm', 'LLVM-MIR Body', ('llvm-mir-body',), (), ()),
    'LlvmMirLexer': ('pip._vendor.pygments.lexers.asm', 'LLVM-MIR', ('llvm-mir',), ('*.mir',), ()),
    'LogosLexer': ('pip._vendor.pygments.lexers.objective', 'Logos', ('logos',), ('*.x', '*.xi', '*.xm', '*.xmi'), ('text/x-logos',)),
    'LogtalkLexer': ('pip._vendor.pygments.lexers.prolog', 'Logtalk', ('logtalk',), ('*.lgt', '*.logtalk'), ('text/x-logtalk',)),
    'LuaLexer': ('pip._vendor.pygments.lexers.scripting', 'Lua', ('lua',), ('*.lua', '*.wlua'), ('text/x-lua', 'application/x-lua')),
    'LuauLexer': ('pip._vendor.pygments.lexers.scripting', 'Luau', ('luau',), ('*.luau',), ()),
    'MCFunctionLexer': ('pip._vendor.pygments.lexers.minecraft', 'MCFunction', ('mcfunction', 'mcf'), ('*.mcfunction',), ('text/mcfunction',)),
    'MCSchemaLexer': ('pip._vendor.pygments.lexers.minecraft', 'MCSchema', ('mcschema',), ('*.mcschema',), ('text/mcschema',)),
    'MIMELexer': ('pip._vendor.pygments.lexers.mime', 'MIME', ('mime',), (), ('multipart/mixed', 'multipart/related', 'multipart/alternative')),
    'MIPSLexer': ('pip._vendor.pygments.lexers.mips', 'MIPS', ('mips',), ('*.mips', '*.MIPS'), ()),
    'MOOCodeLexer': ('pip._vendor.pygments.lexers.scripting', 'MOOCode', ('moocode', 'moo'), ('*.moo',), ('text/x-moocode',)),
    'MSDOSSessionLexer': ('pip._vendor.pygments.lexers.shell', 'MSDOS Session', ('doscon',), (), ()),
    'Macaulay2Lexer': ('pip._vendor.pygments.lexers.macaulay2', 'Macaulay2', ('macaulay2',), ('*.m2',), ()),
    'MakefileLexer': ('pip._vendor.pygments.lexers.make', 'Makefile', ('make', 'makefile', 'mf', 'bsdmake'), ('*.mak', '*.mk', 'Makefile', 'makefile', 'Makefile.*', 'GNUmakefile'), ('text/x-makefile',)),
    'MakoCssLexer': ('pip._vendor.pygments.lexers.templates', 'CSS+Mako', ('css+mako',), (), ('text/css+mako',)),
    'MakoHtmlLexer': ('pip._vendor.pygments.lexers.templates', 'HTML+Mako', ('html+mako',), (), ('text/html+mako',)),
    'MakoJavascriptLexer': ('pip._vendor.pygments.lexers.templates', 'JavaScript+Mako', ('javascript+mako', 'js+mako'), (), ('application/x-javascript+mako', 'text/x-javascript+mako', 'text/javascript+mako')),
    'MakoLexer': ('pip._vendor.pygments.lexers.templates', 'Mako', ('mako',), ('*.mao',), ('application/x-mako',)),
    'MakoXmlLexer': ('pip._vendor.pygments.lexers.templates', 'XML+Mako', ('xml+mako',), (), ('application/xml+mako',)),
    'MaqlLexer': ('pip._vendor.pygments.lexers.business', 'MAQL', ('maql',), ('*.maql',), ('text/x-gooddata-maql', 'application/x-gooddata-maql')),
    'MarkdownLexer': ('pip._vendor.pygments.lexers.markup', 'Markdown', ('markdown', 'md'), ('*.md', '*.markdown'), ('text/x-markdown',)),
    'MaskLexer': ('pip._vendor.pygments.lexers.javascript', 'Mask', ('mask',), ('*.mask',), ('text/x-mask',)),
    'MasonLexer': ('pip._vendor.pygments.lexers.templates', 'Mason', ('mason',), ('*.m', '*.mhtml', '*.mc', '*.mi', 'autohandler', 'dhandler'), ('application/x-mason',)),
    'MathematicaLexer': ('pip._vendor.pygments.lexers.algebra', 'Mathematica', ('mathematica', 'mma', 'nb'), ('*.nb', '*.cdf', '*.nbp', '*.ma'), ('application/mathematica', 'application/vnd.wolfram.mathematica', 'application/vnd.wolfram.mathematica.package', 'application/vnd.wolfram.cdf')),
    'MatlabLexer': ('pip._vendor.pygments.lexers.matlab', 'Matlab', ('matlab',), ('*.m',), ('text/matlab',)),
    'MatlabSessionLexer': ('pip._vendor.pygments.lexers.matlab', 'Matlab session', ('matlabsession',), (), ()),
    'MaximaLexer': ('pip._vendor.pygments.lexers.maxima', 'Maxima', ('maxima', 'macsyma'), ('*.mac', '*.max'), ()),
    'MesonLexer': ('pip._vendor.pygments.lexers.meson', 'Meson', ('meson', 'meson.build'), ('meson.build', 'meson_options.txt'), ('text/x-meson',)),
    'MiniDLexer': ('pip._vendor.pygments.lexers.d', 'MiniD', ('minid',), (), ('text/x-minidsrc',)),
    'MiniScriptLexer': ('pip._vendor.pygments.lexers.scripting', 'MiniScript', ('miniscript', 'ms'), ('*.ms',), ('text/x-minicript', 'application/x-miniscript')),
    'ModelicaLexer': ('pip._vendor.pygments.lexers.modeling', 'Modelica', ('modelica',), ('*.mo',), ('text/x-modelica',)),
    'Modula2Lexer': ('pip._vendor.pygments.lexers.modula2', 'Modula-2', ('modula2', 'm2'), ('*.def', '*.mod'), ('text/x-modula2',)),
    'MoinWikiLexer': ('pip._vendor.pygments.lexers.markup', 'MoinMoin/Trac Wiki markup', ('trac-wiki', 'moin'), (), ('text/x-trac-wiki',)),
    'MojoLexer': ('pip._vendor.pygments.lexers.mojo', 'Mojo', ('mojo', '🔥'), ('*.mojo', '*.🔥'), ('text/x-mojo', 'application/x-mojo')),
    'MonkeyLexer': ('pip._vendor.pygments.lexers.basic', 'Monkey', ('monkey',), ('*.monkey',), ('text/x-monkey',)),
    'MonteLexer': ('pip._vendor.pygments.lexers.monte', 'Monte', ('monte',), ('*.mt',), ()),
    'MoonScriptLexer': ('pip._vendor.pygments.lexers.scripting', 'MoonScript', ('moonscript', 'moon'), ('*.moon',), ('text/x-moonscript', 'application/x-moonscript')),
    'MoselLexer': ('pip._vendor.pygments.lexers.mosel', 'Mosel', ('mosel',), ('*.mos',), ()),
    'MozPreprocCssLexer': ('pip._vendor.pygments.lexers.markup', 'CSS+mozpreproc', ('css+mozpreproc',), ('*.css.in',), ()),
    'MozPreprocHashLexer': ('pip._vendor.pygments.lexers.markup', 'mozhashpreproc', ('mozhashpreproc',), (), ()),
    'MozPreprocJavascriptLexer': ('pip._vendor.pygments.lexers.markup', 'Javascript+mozpreproc', ('javascript+mozpreproc',), ('*.js.in',), ()),
    'MozPreprocPercentLexer': ('pip._vendor.pygments.lexers.markup', 'mozpercentpreproc', ('mozpercentpreproc',), (), ()),
    'MozPreprocXulLexer': ('pip._vendor.pygments.lexers.markup', 'XUL+mozpreproc', ('xul+mozpreproc',), ('*.xul.in',), ()),
    'MqlLexer': ('pip._vendor.pygments.lexers.c_like', 'MQL', ('mql', 'mq4', 'mq5', 'mql4', 'mql5'), ('*.mq4', '*.mq5', '*.mqh'), ('text/x-mql',)),
    'MscgenLexer': ('pip._vendor.pygments.lexers.dsls', 'Mscgen', ('mscgen', 'msc'), ('*.msc',), ()),
    'MuPADLexer': ('pip._vendor.pygments.lexers.algebra', 'MuPAD', ('mupad',), ('*.mu',), ()),
    'MxmlLexer': ('pip._vendor.pygments.lexers.actionscript', 'MXML', ('mxml',), ('*.mxml',), ()),
    'MySqlLexer': ('pip._vendor.pygments.lexers.sql', 'MySQL', ('mysql',), (), ('text/x-mysql',)),
    'MyghtyCssLexer': ('pip._vendor.pygments.lexers.templates', 'CSS+Myghty', ('css+myghty',), (), ('text/css+myghty',)),
    'MyghtyHtmlLexer': ('pip._vendor.pygments.lexers.templates', 'HTML+Myghty', ('html+myghty',), (), ('text/html+myghty',)),
    'MyghtyJavascriptLexer': ('pip._vendor.pygments.lexers.templates', 'JavaScript+Myghty', ('javascript+myghty', 'js+myghty'), (), ('application/x-javascript+myghty', 'text/x-javascript+myghty', 'text/javascript+mygthy')),
    'MyghtyLexer': ('pip._vendor.pygments.lexers.templates', 'Myghty', ('myghty',), ('*.myt', 'autodelegate'), ('application/x-myghty',)),
    'MyghtyXmlLexer': ('pip._vendor.pygments.lexers.templates', 'XML+Myghty', ('xml+myghty',), (), ('application/xml+myghty',)),
    'NCLLexer': ('pip._vendor.pygments.lexers.ncl', 'NCL', ('ncl',), ('*.ncl',), ('text/ncl',)),
    'NSISLexer': ('pip._vendor.pygments.lexers.installers', 'NSIS', ('nsis', 'nsi', 'nsh'), ('*.nsi', '*.nsh'), ('text/x-nsis',)),
    'NasmLexer': ('pip._vendor.pygments.lexers.asm', 'NASM', ('nasm',), ('*.asm', '*.ASM', '*.nasm'), ('text/x-nasm',)),
    'NasmObjdumpLexer': ('pip._vendor.pygments.lexers.asm', 'objdump-nasm', ('objdump-nasm',), ('*.objdump-intel',), ('text/x-nasm-objdump',)),
    'NemerleLexer': ('pip._vendor.pygments.lexers.dotnet', 'Nemerle', ('nemerle',), ('*.n',), ('text/x-nemerle',)),
    'NesCLexer': ('pip._vendor.pygments.lexers.c_like', 'nesC', ('nesc',), ('*.nc',), ('text/x-nescsrc',)),
    'NestedTextLexer': ('pip._vendor.pygments.lexers.configs', 'NestedText', ('nestedtext', 'nt'), ('*.nt',), ()),
    'NewLispLexer': ('pip._vendor.pygments.lexers.lisp', 'NewLisp', ('newlisp',), ('*.lsp', '*.nl', '*.kif'), ('text/x-newlisp', 'application/x-newlisp')),
    'NewspeakLexer': ('pip._vendor.pygments.lexers.smalltalk', 'Newspeak', ('newspeak',), ('*.ns2',), ('text/x-newspeak',)),
    'NginxConfLexer': ('pip._vendor.pygments.lexers.configs', 'Nginx configuration file', ('nginx',), ('nginx.conf',), ('text/x-nginx-conf',)),
    'NimrodLexer': ('pip._vendor.pygments.lexers.nimrod', 'Nimrod', ('nimrod', 'nim'), ('*.nim', '*.nimrod'), ('text/x-nim',)),
    'NitLexer': ('pip._vendor.pygments.lexers.nit', 'Nit', ('nit',), ('*.nit',), ()),
    'NixLexer': ('pip._vendor.pygments.lexers.nix', 'Nix', ('nixos', 'nix'), ('*.nix',), ('text/x-nix',)),
    'NodeConsoleLexer': ('pip._vendor.pygments.lexers.javascript', 'Node.js REPL console session', ('nodejsrepl',), (), ('text/x-nodejsrepl',)),
    'NotmuchLexer': ('pip._vendor.pygments.lexers.textfmts', 'Notmuch', ('notmuch',), (), ()),
    'NuSMVLexer': ('pip._vendor.pygments.lexers.smv', 'NuSMV', ('nusmv',), ('*.smv',), ()),
    'NumPyLexer': ('pip._vendor.pygments.lexers.python', 'NumPy', ('numpy',), (), ()),
    'ObjdumpLexer': ('pip._vendor.pygments.lexers.asm', 'objdump', ('objdump',), ('*.objdump',), ('text/x-objdump',)),
    'ObjectiveCLexer': ('pip._vendor.pygments.lexers.objective', 'Objective-C', ('objective-c', 'objectivec', 'obj-c', 'objc'), ('*.m', '*.h'), ('text/x-objective-c',)),
    'ObjectiveCppLexer': ('pip._vendor.pygments.lexers.objective', 'Objective-C++', ('objective-c++', 'objectivec++', 'obj-c++', 'objc++'), ('*.mm', '*.hh'), ('text/x-objective-c++',)),
    'ObjectiveJLexer': ('pip._vendor.pygments.lexers.javascript', 'Objective-J', ('objective-j', 'objectivej', 'obj-j', 'objj'), ('*.j',), ('text/x-objective-j',)),
    'OcamlLexer': ('pip._vendor.pygments.lexers.ml', 'OCaml', ('ocaml',), ('*.ml', '*.mli', '*.mll', '*.mly'), ('text/x-ocaml',)),
    'OctaveLexer': ('pip._vendor.pygments.lexers.matlab', 'Octave', ('octave',), ('*.m',), ('text/octave',)),
    'OdinLexer': ('pip._vendor.pygments.lexers.archetype', 'ODIN', ('odin',), ('*.odin',), ('text/odin',)),
    'OmgIdlLexer': ('pip._vendor.pygments.lexers.c_like', 'OMG Interface Definition Language', ('omg-idl',), ('*.idl', '*.pidl'), ()),
    'OocLexer': ('pip._vendor.pygments.lexers.ooc', 'Ooc', ('ooc',), ('*.ooc',), ('text/x-ooc',)),
    'OpaLexer': ('pip._vendor.pygments.lexers.ml', 'Opa', ('opa',), ('*.opa',), ('text/x-opa',)),
    'OpenEdgeLexer': ('pip._vendor.pygments.lexers.business', 'OpenEdge ABL', ('openedge', 'abl', 'progress'), ('*.p', '*.cls'), ('text/x-openedge', 'application/x-openedge')),
    'OpenScadLexer': ('pip._vendor.pygments.lexers.openscad', 'OpenSCAD', ('openscad',), ('*.scad',), ('application/x-openscad',)),
    'OrgLexer': ('pip._vendor.pygments.lexers.markup', 'Org Mode', ('org', 'orgmode', 'org-mode'), ('*.org',), ('text/org',)),
    'OutputLexer': ('pip._vendor.pygments.lexers.special', 'Text output', ('output',), (), ()),
    'PacmanConfLexer': ('pip._vendor.pygments.lexers.configs', 'PacmanConf', ('pacmanconf',), ('pacman.conf',), ()),
    'PanLexer': ('pip._vendor.pygments.lexers.dsls', 'Pan', ('pan',), ('*.pan',), ()),
    'ParaSailLexer': ('pip._vendor.pygments.lexers.parasail', 'ParaSail', ('parasail',), ('*.psi', '*.psl'), ('text/x-parasail',)),
    'PawnLexer': ('pip._vendor.pygments.lexers.pawn', 'Pawn', ('pawn',), ('*.p', '*.pwn', '*.inc'), ('text/x-pawn',)),
    'PegLexer': ('pip._vendor.pygments.lexers.grammar_notation', 'PEG', ('peg',), ('*.peg',), ('text/x-peg',)),
    'Perl6Lexer': ('pip._vendor.pygments.lexers.perl', 'Perl6', ('perl6', 'pl6', 'raku'), ('*.pl', '*.pm', '*.nqp', '*.p6', '*.6pl', '*.p6l', '*.pl6', '*.6pm', '*.p6m', '*.pm6', '*.t', '*.raku', '*.rakumod', '*.rakutest', '*.rakudoc'), ('text/x-perl6', 'application/x-perl6')),
    'PerlLexer': ('pip._vendor.pygments.lexers.perl', 'Perl', ('perl', 'pl'), ('*.pl', '*.pm', '*.t', '*.perl'), ('text/x-perl', 'application/x-perl')),
    'PhixLexer': ('pip._vendor.pygments.lexers.phix', 'Phix', ('phix',), ('*.exw',), ('text/x-phix',)),
    'PhpLexer': ('pip._vendor.pygments.lexers.php', 'PHP', ('php', 'php3', 'php4', 'php5'), ('*.php', '*.php[345]', '*.inc'), ('text/x-php',)),
    'PigLexer': ('pip._vendor.pygments.lexers.jvm', 'Pig', ('pig',), ('*.pig',), ('text/x-pig',)),
    'PikeLexer': ('pip._vendor.pygments.lexers.c_like', 'Pike', ('pike',), ('*.pike', '*.pmod'), ('text/x-pike',)),
    'PkgConfigLexer': ('pip._vendor.pygments.lexers.configs', 'PkgConfig', ('pkgconfig',), ('*.pc',), ()),
    'PlPgsqlLexer': ('pip._vendor.pygments.lexers.sql', 'PL/pgSQL', ('plpgsql',), (), ('text/x-plpgsql',)),
    'PointlessLexer': ('pip._vendor.pygments.lexers.pointless', 'Pointless', ('pointless',), ('*.ptls',), ()),
    'PonyLexer': ('pip._vendor.pygments.lexers.pony', 'Pony', ('pony',), ('*.pony',), ()),
    'PortugolLexer': ('pip._vendor.pygments.lexers.pascal', 'Portugol', ('portugol',), ('*.alg', '*.portugol'), ()),
    'PostScriptLexer': ('pip._vendor.pygments.lexers.graphics', 'PostScript', ('postscript', 'postscr'), ('*.ps', '*.eps'), ('application/postscript',)),
    'PostgresConsoleLexer': ('pip._vendor.pygments.lexers.sql', 'PostgreSQL console (psql)', ('psql', 'postgresql-console', 'postgres-console'), (), ('text/x-postgresql-psql',)),
    'PostgresExplainLexer': ('pip._vendor.pygments.lexers.sql', 'PostgreSQL EXPLAIN dialect', ('postgres-explain',), ('*.explain',), ('text/x-postgresql-explain',)),
    'PostgresLexer': ('pip._vendor.pygments.lexers.sql', 'PostgreSQL SQL dialect', ('postgresql', 'postgres'), (), ('text/x-postgresql',)),
    'PovrayLexer': ('pip._vendor.pygments.lexers.graphics', 'POVRay', ('pov',), ('*.pov', '*.inc'), ('text/x-povray',)),
    'PowerShellLexer': ('pip._vendor.pygments.lexers.shell', 'PowerShell', ('powershell', 'pwsh', 'posh', 'ps1', 'psm1'), ('*.ps1', '*.psm1'), ('text/x-powershell',)),
    'PowerShellSessionLexer': ('pip._vendor.pygments.lexers.shell', 'PowerShell Session', ('pwsh-session', 'ps1con'), (), ()),
    'PraatLexer': ('pip._vendor.pygments.lexers.praat', 'Praat', ('praat',), ('*.praat', '*.proc', '*.psc'), ()),
    'ProcfileLexer': ('pip._vendor.pygments.lexers.procfile', 'Procfile', ('procfile',), ('Procfile',), ()),
    'PrologLexer': ('pip._vendor.pygments.lexers.prolog', 'Prolog', ('prolog',), ('*.ecl', '*.prolog', '*.pro', '*.pl'), ('text/x-prolog',)),
    'PromQLLexer': ('pip._vendor.pygments.lexers.promql', 'PromQL', ('promql',), ('*.promql',), ()),
    'PromelaLexer': ('pip._vendor.pygments.lexers.c_like', 'Promela', ('promela',), ('*.pml', '*.prom', '*.prm', '*.promela', '*.pr', '*.pm'), ('text/x-promela',)),
    'PropertiesLexer': ('pip._vendor.pygments.lexers.configs', 'Properties', ('properties', 'jproperties'), ('*.properties',), ('text/x-java-properties',)),
    'ProtoBufLexer': ('pip._vendor.pygments.lexers.dsls', 'Protocol Buffer', ('protobuf', 'proto'), ('*.proto',), ()),
    'PrqlLexer': ('pip._vendor.pygments.lexers.prql', 'PRQL', ('prql',), ('*.prql',), ('application/prql', 'application/x-prql')),
    'PsyshConsoleLexer': ('pip._vendor.pygments.lexers.php', 'PsySH console session for PHP', ('psysh',), (), ()),
    'PtxLexer': ('pip._vendor.pygments.lexers.ptx', 'PTX', ('ptx',), ('*.ptx',), ('text/x-ptx',)),
    'PugLexer': ('pip._vendor.pygments.lexers.html', 'Pug', ('pug', 'jade'), ('*.pug', '*.jade'), ('text/x-pug', 'text/x-jade')),
    'PuppetLexer': ('pip._vendor.pygments.lexers.dsls', 'Puppet', ('puppet',), ('*.pp',), ()),
    'PyPyLogLexer': ('pip._vendor.pygments.lexers.console', 'PyPy Log', ('pypylog', 'pypy'), ('*.pypylog',), ('application/x-pypylog',)),
    'Python2Lexer': ('pip._vendor.pygments.lexers.python', 'Python 2.x', ('python2', 'py2'), (), ('text/x-python2', 'application/x-python2')),
    'Python2TracebackLexer': ('pip._vendor.pygments.lexers.python', 'Python 2.x Traceback', ('py2tb',), ('*.py2tb',), ('text/x-python2-traceback',)),
    'PythonConsoleLexer': ('pip._vendor.pygments.lexers.python', 'Python console session', ('pycon', 'python-console'), (), ('text/x-python-doctest',)),
    'PythonLexer': ('pip._vendor.pygments.lexers.python', 'Python', ('python', 'py', 'sage', 'python3', 'py3', 'bazel', 'starlark'), ('*.py', '*.pyw', '*.pyi', '*.jy', '*.sage', '*.sc', 'SConstruct', 'SConscript', '*.bzl', 'BUCK', 'BUILD', 'BUILD.bazel', 'WORKSPACE', '*.tac'), ('text/x-python', 'application/x-python', 'text/x-python3', 'application/x-python3')),
    'PythonTracebackLexer': ('pip._vendor.pygments.lexers.python', 'Python Traceback', ('pytb', 'py3tb'), ('*.pytb', '*.py3tb'), ('text/x-python-traceback', 'text/x-python3-traceback')),
    'PythonUL4Lexer': ('pip._vendor.pygments.lexers.ul4', 'Python+UL4', ('py+ul4',), ('*.pyul4',), ()),
    'QBasicLexer': ('pip._vendor.pygments.lexers.basic', 'QBasic', ('qbasic', 'basic'), ('*.BAS', '*.bas'), ('text/basic',)),
    'QLexer': ('pip._vendor.pygments.lexers.q', 'Q', ('q',), ('*.q',), ()),
    'QVToLexer': ('pip._vendor.pygments.lexers.qvt', 'QVTO', ('qvto', 'qvt'), ('*.qvto',), ()),
    'QlikLexer': ('pip._vendor.pygments.lexers.qlik', 'Qlik', ('qlik', 'qlikview', 'qliksense', 'qlikscript'), ('*.qvs', '*.qvw'), ()),
    'QmlLexer': ('pip._vendor.pygments.lexers.webmisc', 'QML', ('qml', 'qbs'), ('*.qml', '*.qbs'), ('application/x-qml', 'application/x-qt.qbs+qml')),
    'RConsoleLexer': ('pip._vendor.pygments.lexers.r', 'RConsole', ('rconsole', 'rout'), ('*.Rout',), ()),
    'RNCCompactLexer': ('pip._vendor.pygments.lexers.rnc', 'Relax-NG Compact', ('rng-compact', 'rnc'), ('*.rnc',), ()),
    'RPMSpecLexer': ('pip._vendor.pygments.lexers.installers', 'RPMSpec', ('spec',), ('*.spec',), ('text/x-rpm-spec',)),
    'RacketLexer': ('pip._vendor.pygments.lexers.lisp', 'Racket', ('racket', 'rkt'), ('*.rkt', '*.rktd', '*.rktl'), ('text/x-racket', 'application/x-racket')),
    'RagelCLexer': ('pip._vendor.pygments.lexers.parsers', 'Ragel in C Host', ('ragel-c',), ('*.rl',), ()),
    'RagelCppLexer': ('pip._vendor.pygments.lexers.parsers', 'Ragel in CPP Host', ('ragel-cpp',), ('*.rl',), ()),
    'RagelDLexer': ('pip._vendor.pygments.lexers.parsers', 'Ragel in D Host', ('ragel-d',), ('*.rl',), ()),
    'RagelEmbeddedLexer': ('pip._vendor.pygments.lexers.parsers', 'Embedded Ragel', ('ragel-em',), ('*.rl',), ()),
    'RagelJavaLexer': ('pip._vendor.pygments.lexers.parsers', 'Ragel in Java Host', ('ragel-java',), ('*.rl',), ()),
    'RagelLexer': ('pip._vendor.pygments.lexers.parsers', 'Ragel', ('ragel',), (), ()),
    'RagelObjectiveCLexer': ('pip._vendor.pygments.lexers.parsers', 'Ragel in Objective C Host', ('ragel-objc',), ('*.rl',), ()),
    'RagelRubyLexer': ('pip._vendor.pygments.lexers.parsers', 'Ragel in Ruby Host', ('ragel-ruby', 'ragel-rb'), ('*.rl',), ()),
    'RawTokenLexer': ('pip._vendor.pygments.lexers.special', 'Raw token data', (), (), ('application/x-pygments-tokens',)),
    'RdLexer': ('pip._vendor.pygments.lexers.r', 'Rd', ('rd',), ('*.Rd',), ('text/x-r-doc',)),
    'ReasonLexer': ('pip._vendor.pygments.lexers.ml', 'ReasonML', ('reasonml', 'reason'), ('*.re', '*.rei'), ('text/x-reasonml',)),
    'RebolLexer': ('pip._vendor.pygments.lexers.rebol', 'REBOL', ('rebol',), ('*.r', '*.r3', '*.reb'), ('text/x-rebol',)),
    'RedLexer': ('pip._vendor.pygments.lexers.rebol', 'Red', ('red', 'red/system'), ('*.red', '*.reds'), ('text/x-red', 'text/x-red-system')),
    'RedcodeLexer': ('pip._vendor.pygments.lexers.esoteric', 'Redcode', ('redcode',), ('*.cw',), ()),
    'RegeditLexer': ('pip._vendor.pygments.lexers.configs', 'reg', ('registry',), ('*.reg',), ('text/x-windows-registry',)),
    'ResourceLexer': ('pip._vendor.pygments.lexers.resource', 'ResourceBundle', ('resourcebundle', 'resource'), (), ()),
    'RexxLexer': ('pip._vendor.pygments.lexers.scripting', 'Rexx', ('rexx', 'arexx'), ('*.rexx', '*.rex', '*.rx', '*.arexx'), ('text/x-rexx',)),
    'RhtmlLexer': ('pip._vendor.pygments.lexers.templates', 'RHTML', ('rhtml', 'html+erb', 'html+ruby'), ('*.rhtml',), ('text/html+ruby',)),
    'RideLexer': ('pip._vendor.pygments.lexers.ride', 'Ride', ('ride',), ('*.ride',), ('text/x-ride',)),
    'RitaLexer': ('pip._vendor.pygments.lexers.rita', 'Rita', ('rita',), ('*.rita',), ('text/rita',)),
    'RoboconfGraphLexer': ('pip._vendor.pygments.lexers.roboconf', 'Roboconf Graph', ('roboconf-graph',), ('*.graph',), ()),
    'RoboconfInstancesLexer': ('pip._vendor.pygments.lexers.roboconf', 'Roboconf Instances', ('roboconf-instances',), ('*.instances',), ()),
    'RobotFrameworkLexer': ('pip._vendor.pygments.lexers.robotframework', 'RobotFramework', ('robotframework',), ('*.robot', '*.resource'), ('text/x-robotframework',)),
    'RqlLexer': ('pip._vendor.pygments.lexers.sql', 'RQL', ('rql',), ('*.rql',), ('text/x-rql',)),
    'RslLexer': ('pip._vendor.pygments.lexers.dsls', 'RSL', ('rsl',), ('*.rsl',), ('text/rsl',)),
    'RstLexer': ('pip._vendor.pygments.lexers.markup', 'reStructuredText', ('restructuredtext', 'rst', 'rest'), ('*.rst', '*.rest'), ('text/x-rst', 'text/prs.fallenstein.rst')),
    'RtsLexer': ('pip._vendor.pygments.lexers.trafficscript', 'TrafficScript', ('trafficscript', 'rts'), ('*.rts',), ()),
    'RubyConsoleLexer': ('pip._vendor.pygments.lexers.ruby', 'Ruby irb session', ('rbcon', 'irb'), (), ('text/x-ruby-shellsession',)),
    'RubyLexer': ('pip._vendor.pygments.lexers.ruby', 'Ruby', ('ruby', 'rb', 'duby'), ('*.rb', '*.rbw', 'Rakefile', '*.rake', '*.gemspec', '*.rbx', '*.duby', 'Gemfile', 'Vagrantfile'), ('text/x-ruby', 'application/x-ruby')),
    'RustLexer': ('pip._vendor.pygments.lexers.rust', 'Rust', ('rust', 'rs'), ('*.rs', '*.rs.in'), ('text/rust', 'text/x-rust')),
    'SASLexer': ('pip._vendor.pygments.lexers.sas', 'SAS', ('sas',), ('*.SAS', '*.sas'), ('text/x-sas', 'text/sas', 'application/x-sas')),
    'SLexer': ('pip._vendor.pygments.lexers.r', 'S', ('splus', 's', 'r'), ('*.S', '*.R', '.Rhistory', '.Rprofile', '.Renviron'), ('text/S-plus', 'text/S', 'text/x-r-source', 'text/x-r', 'text/x-R', 'text/x-r-history', 'text/x-r-profile')),
    'SMLLexer': ('pip._vendor.pygments.lexers.ml', 'Standard ML', ('sml',), ('*.sml', '*.sig', '*.fun'), ('text/x-standardml', 'application/x-standardml')),
    'SNBTLexer': ('pip._vendor.pygments.lexers.minecraft', 'SNBT', ('snbt',), ('*.snbt',), ('text/snbt',)),
    'SarlLexer': ('pip._vendor.pygments.lexers.jvm', 'SARL', ('sarl',), ('*.sarl',), ('text/x-sarl',)),
    'SassLexer': ('pip._vendor.pygments.lexers.css', 'Sass', ('sass',), ('*.sass',), ('text/x-sass',)),
    'SaviLexer': ('pip._vendor.pygments.lexers.savi', 'Savi', ('savi',), ('*.savi',), ()),
    'ScalaLexer': ('pip._vendor.pygments.lexers.jvm', 'Scala', ('scala',), ('*.scala',), ('text/x-scala',)),
    'ScamlLexer': ('pip._vendor.pygments.lexers.html', 'Scaml', ('scaml',), ('*.scaml',), ('text/x-scaml',)),
    'ScdocLexer': ('pip._vendor.pygments.lexers.scdoc', 'scdoc', ('scdoc', 'scd'), ('*.scd', '*.scdoc'), ()),
    'SchemeLexer': ('pip._vendor.pygments.lexers.lisp', 'Scheme', ('scheme', 'scm'), ('*.scm', '*.ss'), ('text/x-scheme', 'application/x-scheme')),
    'ScilabLexer': ('pip._vendor.pygments.lexers.matlab', 'Scilab', ('scilab',), ('*.sci', '*.sce', '*.tst'), ('text/scilab',)),
    'ScssLexer': ('pip._vendor.pygments.lexers.css', 'SCSS', ('scss',), ('*.scss',), ('text/x-scss',)),
    'SedLexer': ('pip._vendor.pygments.lexers.textedit', 'Sed', ('sed', 'gsed', 'ssed'), ('*.sed', '*.[gs]sed'), ('text/x-sed',)),
    'ShExCLexer': ('pip._vendor.pygments.lexers.rdf', 'ShExC', ('shexc', 'shex'), ('*.shex',), ('text/shex',)),
    'ShenLexer': ('pip._vendor.pygments.lexers.lisp', 'Shen', ('shen',), ('*.shen',), ('text/x-shen', 'application/x-shen')),
    'SieveLexer': ('pip._vendor.pygments.lexers.sieve', 'Sieve', ('sieve',), ('*.siv', '*.sieve'), ()),
    'SilverLexer': ('pip._vendor.pygments.lexers.verification', 'Silver', ('silver',), ('*.sil', '*.vpr'), ()),
    'SingularityLexer': ('pip._vendor.pygments.lexers.configs', 'Singularity', ('singularity',), ('*.def', 'Singularity'), ()),
    'SlashLexer': ('pip._vendor.pygments.lexers.slash', 'Slash', ('slash',), ('*.sla',), ()),
    'SlimLexer': ('pip._vendor.pygments.lexers.webmisc', 'Slim', ('slim',), ('*.slim',), ('text/x-slim',)),
    'SlurmBashLexer': ('pip._vendor.pygments.lexers.shell', 'Slurm', ('slurm', 'sbatch'), ('*.sl',), ()),
    'SmaliLexer': ('pip._vendor.pygments.lexers.dalvik', 'Smali', ('smali',), ('*.smali',), ('text/smali',)),
    'SmalltalkLexer': ('pip._vendor.pygments.lexers.smalltalk', 'Smalltalk', ('smalltalk', 'squeak', 'st'), ('*.st',), ('text/x-smalltalk',)),
    'SmartGameFormatLexer': ('pip._vendor.pygments.lexers.sgf', 'SmartGameFormat', ('sgf',), ('*.sgf',), ()),
    'SmartyLexer': ('pip._vendor.pygments.lexers.templates', 'Smarty', ('smarty',), ('*.tpl',), ('application/x-smarty',)),
    'SmithyLexer': ('pip._vendor.pygments.lexers.smithy', 'Smithy', ('smithy',), ('*.smithy',), ()),
    'SnobolLexer': ('pip._vendor.pygments.lexers.snobol', 'Snobol', ('snobol',), ('*.snobol',), ('text/x-snobol',)),
    'SnowballLexer': ('pip._vendor.pygments.lexers.dsls', 'Snowball', ('snowball',), ('*.sbl',), ()),
    'SolidityLexer': ('pip._vendor.pygments.lexers.solidity', 'Solidity', ('solidity',), ('*.sol',), ()),
    'SoongLexer': ('pip._vendor.pygments.lexers.soong', 'Soong', ('androidbp', 'bp', 'soong'), ('Android.bp',), ()),
    'SophiaLexer': ('pip._vendor.pygments.lexers.sophia', 'Sophia', ('sophia',), ('*.aes',), ()),
    'SourcePawnLexer': ('pip._vendor.pygments.lexers.pawn', 'SourcePawn', ('sp',), ('*.sp',), ('text/x-sourcepawn',)),
    'SourcesListLexer': ('pip._vendor.pygments.lexers.installers', 'Debian Sourcelist', ('debsources', 'sourceslist', 'sources.list'), ('sources.list',), ()),
    'SparqlLexer': ('pip._vendor.pygments.lexers.rdf', 'SPARQL', ('sparql',), ('*.rq', '*.sparql'), ('application/sparql-query',)),
    'SpiceLexer': ('pip._vendor.pygments.lexers.spice', 'Spice', ('spice', 'spicelang'), ('*.spice',), ('text/x-spice',)),
    'SqlJinjaLexer': ('pip._vendor.pygments.lexers.templates', 'SQL+Jinja', ('sql+jinja',), ('*.sql', '*.sql.j2', '*.sql.jinja2'), ()),
    'SqlLexer': ('pip._vendor.pygments.lexers.sql', 'SQL', ('sql',), ('*.sql',), ('text/x-sql',)),
    'SqliteConsoleLexer': ('pip._vendor.pygments.lexers.sql', 'sqlite3con', ('sqlite3',), ('*.sqlite3-console',), ('text/x-sqlite3-console',)),
    'SquidConfLexer': ('pip._vendor.pygments.lexers.configs', 'SquidConf', ('squidconf', 'squid.conf', 'squid'), ('squid.conf',), ('text/x-squidconf',)),
    'SrcinfoLexer': ('pip._vendor.pygments.lexers.srcinfo', 'Srcinfo', ('srcinfo',), ('.SRCINFO',), ()),
    'SspLexer': ('pip._vendor.pygments.lexers.templates', 'Scalate Server Page', ('ssp',), ('*.ssp',), ('application/x-ssp',)),
    'StanLexer': ('pip._vendor.pygments.lexers.modeling', 'Stan', ('stan',), ('*.stan',), ()),
    'StataLexer': ('pip._vendor.pygments.lexers.stata', 'Stata', ('stata', 'do'), ('*.do', '*.ado'), ('text/x-stata', 'text/stata', 'application/x-stata')),
    'SuperColliderLexer': ('pip._vendor.pygments.lexers.supercollider', 'SuperCollider', ('supercollider', 'sc'), ('*.sc', '*.scd'), ('application/supercollider', 'text/supercollider')),
    'SwiftLexer': ('pip._vendor.pygments.lexers.objective', 'Swift', ('swift',), ('*.swift',), ('text/x-swift',)),
    'SwigLexer': ('pip._vendor.pygments.lexers.c_like', 'SWIG', ('swig',), ('*.swg', '*.i'), ('text/swig',)),
    'SystemVerilogLexer': ('pip._vendor.pygments.lexers.hdl', 'systemverilog', ('systemverilog', 'sv'), ('*.sv', '*.svh'), ('text/x-systemverilog',)),
    'SystemdLexer': ('pip._vendor.pygments.lexers.configs', 'Systemd', ('systemd',), ('*.service', '*.socket', '*.device', '*.mount', '*.automount', '*.swap', '*.target', '*.path', '*.timer', '*.slice', '*.scope'), ()),
    'TAPLexer': ('pip._vendor.pygments.lexers.testing', 'TAP', ('tap',), ('*.tap',), ()),
    'TNTLexer': ('pip._vendor.pygments.lexers.tnt', 'Typographic Number Theory', ('tnt',), ('*.tnt',), ()),
    'TOMLLexer': ('pip._vendor.pygments.lexers.configs', 'TOML', ('toml',), ('*.toml', 'Pipfile', 'poetry.lock'), ('application/toml',)),
    'TactLexer': ('pip._vendor.pygments.lexers.tact', 'Tact', ('tact',), ('*.tact',), ()),
    'Tads3Lexer': ('pip._vendor.pygments.lexers.int_fiction', 'TADS 3', ('tads3',), ('*.t',), ()),
    'TalLexer': ('pip._vendor.pygments.lexers.tal', 'Tal', ('tal', 'uxntal'), ('*.tal',), ('text/x-uxntal',)),
    'TasmLexer': ('pip._vendor.pygments.lexers.asm', 'TASM', ('tasm',), ('*.asm', '*.ASM', '*.tasm'), ('text/x-tasm',)),
    'TclLexer': ('pip._vendor.pygments.lexers.tcl', 'Tcl', ('tcl',), ('*.tcl', '*.rvt'), ('text/x-tcl', 'text/x-script.tcl', 'application/x-tcl')),
    'TcshLexer': ('pip._vendor.pygments.lexers.shell', 'Tcsh', ('tcsh', 'csh'), ('*.tcsh', '*.csh'), ('application/x-csh',)),
    'TcshSessionLexer': ('pip._vendor.pygments.lexers.shell', 'Tcsh Session', ('tcshcon',), (), ()),
    'TeaTemplateLexer': ('pip._vendor.pygments.lexers.templates', 'Tea', ('tea',), ('*.tea',), ('text/x-tea',)),
    'TealLexer': ('pip._vendor.pygments.lexers.teal', 'teal', ('teal',), ('*.teal',), ()),
    'TeraTermLexer': ('pip._vendor.pygments.lexers.teraterm', 'Tera Term macro', ('teratermmacro', 'teraterm', 'ttl'), ('*.ttl',), ('text/x-teratermmacro',)),
    'TermcapLexer': ('pip._vendor.pygments.lexers.configs', 'Termcap', ('termcap',), ('termcap', 'termcap.src'), ()),
    'TerminfoLexer': ('pip._vendor.pygments.lexers.configs', 'Terminfo', ('terminfo',), ('terminfo', 'terminfo.src'), ()),
    'TerraformLexer': ('pip._vendor.pygments.lexers.configs', 'Terraform', ('terraform', 'tf', 'hcl'), ('*.tf', '*.hcl'), ('application/x-tf', 'application/x-terraform')),
    'TexLexer': ('pip._vendor.pygments.lexers.markup', 'TeX', ('tex', 'latex'), ('*.tex', '*.aux', '*.toc'), ('text/x-tex', 'text/x-latex')),
    'TextLexer': ('pip._vendor.pygments.lexers.special', 'Text only', ('text',), ('*.txt',), ('text/plain',)),
    'ThingsDBLexer': ('pip._vendor.pygments.lexers.thingsdb', 'ThingsDB', ('ti', 'thingsdb'), ('*.ti',), ()),
    'ThriftLexer': ('pip._vendor.pygments.lexers.dsls', 'Thrift', ('thrift',), ('*.thrift',), ('application/x-thrift',)),
    'TiddlyWiki5Lexer': ('pip._vendor.pygments.lexers.markup', 'tiddler', ('tid',), ('*.tid',), ('text/vnd.tiddlywiki',)),
    'TlbLexer': ('pip._vendor.pygments.lexers.tlb', 'Tl-b', ('tlb',), ('*.tlb',), ()),
    'TlsLexer': ('pip._vendor.pygments.lexers.tls', 'TLS Presentation Language', ('tls',), (), ()),
    'TodotxtLexer': ('pip._vendor.pygments.lexers.textfmts', 'Todotxt', ('todotxt',), ('todo.txt', '*.todotxt'), ('text/x-todo',)),
    'TransactSqlLexer': ('pip._vendor.pygments.lexers.sql', 'Transact-SQL', ('tsql', 't-sql'), ('*.sql',), ('text/x-tsql',)),
    'TreetopLexer': ('pip._vendor.pygments.lexers.parsers', 'Treetop', ('treetop',), ('*.treetop', '*.tt'), ()),
    'TurtleLexer': ('pip._vendor.pygments.lexers.rdf', 'Turtle', ('turtle',), ('*.ttl',), ('text/turtle', 'application/x-turtle')),
    'TwigHtmlLexer': ('pip._vendor.pygments.lexers.templates', 'HTML+Twig', ('html+twig',), ('*.twig',), ('text/html+twig',)),
    'TwigLexer': ('pip._vendor.pygments.lexers.templates', 'Twig', ('twig',), (), ('application/x-twig',)),
    'TypeScriptLexer': ('pip._vendor.pygments.lexers.javascript', 'TypeScript', ('typescript', 'ts'), ('*.ts',), ('application/x-typescript', 'text/x-typescript')),
    'TypoScriptCssDataLexer': ('pip._vendor.pygments.lexers.typoscript', 'TypoScriptCssData', ('typoscriptcssdata',), (), ()),
    'TypoScriptHtmlDataLexer': ('pip._vendor.pygments.lexers.typoscript', 'TypoScriptHtmlData', ('typoscripthtmldata',), (), ()),
    'TypoScriptLexer': ('pip._vendor.pygments.lexers.typoscript', 'TypoScript', ('typoscript',), ('*.typoscript',), ('text/x-typoscript',)),
    'TypstLexer': ('pip._vendor.pygments.lexers.typst', 'Typst', ('typst',), ('*.typ',), ('text/x-typst',)),
    'UL4Lexer': ('pip._vendor.pygments.lexers.ul4', 'UL4', ('ul4',), ('*.ul4',), ()),
    'UcodeLexer': ('pip._vendor.pygments.lexers.unicon', 'ucode', ('ucode',), ('*.u', '*.u1', '*.u2'), ()),
    'UniconLexer': ('pip._vendor.pygments.lexers.unicon', 'Unicon', ('unicon',), ('*.icn',), ('text/unicon',)),
    'UnixConfigLexer': ('pip._vendor.pygments.lexers.configs', 'Unix/Linux config files', ('unixconfig', 'linuxconfig'), (), ()),
    'UrbiscriptLexer': ('pip._vendor.pygments.lexers.urbi', 'UrbiScript', ('urbiscript',), ('*.u',), ('application/x-urbiscript',)),
    'UrlEncodedLexer': ('pip._vendor.pygments.lexers.html', 'urlencoded', ('urlencoded',), (), ('application/x-www-form-urlencoded',)),
    'UsdLexer': ('pip._vendor.pygments.lexers.usd', 'USD', ('usd', 'usda'), ('*.usd', '*.usda'), ()),
    'VBScriptLexer': ('pip._vendor.pygments.lexers.basic', 'VBScript', ('vbscript',), ('*.vbs', '*.VBS'), ()),
    'VCLLexer': ('pip._vendor.pygments.lexers.varnish', 'VCL', ('vcl',), ('*.vcl',), ('text/x-vclsrc',)),
    'VCLSnippetLexer': ('pip._vendor.pygments.lexers.varnish', 'VCLSnippets', ('vclsnippets', 'vclsnippet'), (), ('text/x-vclsnippet',)),
    'VCTreeStatusLexer': ('pip._vendor.pygments.lexers.console', 'VCTreeStatus', ('vctreestatus',), (), ()),
    'VGLLexer': ('pip._vendor.pygments.lexers.dsls', 'VGL', ('vgl',), ('*.rpf',), ()),
    'ValaLexer': ('pip._vendor.pygments.lexers.c_like', 'Vala', ('vala', 'vapi'), ('*.vala', '*.vapi'), ('text/x-vala',)),
    'VbNetAspxLexer': ('pip._vendor.pygments.lexers.dotnet', 'aspx-vb', ('aspx-vb',), ('*.aspx', '*.asax', '*.ascx', '*.ashx', '*.asmx', '*.axd'), ()),
    'VbNetLexer': ('pip._vendor.pygments.lexers.dotnet', 'VB.net', ('vb.net', 'vbnet', 'lobas', 'oobas', 'sobas', 'visual-basic', 'visualbasic'), ('*.vb', '*.bas'), ('text/x-vbnet', 'text/x-vba')),
    'VelocityHtmlLexer': ('pip._vendor.pygments.lexers.templates', 'HTML+Velocity', ('html+velocity',), (), ('text/html+velocity',)),
    'VelocityLexer': ('pip._vendor.pygments.lexers.templates', 'Velocity', ('velocity',), ('*.vm', '*.fhtml'), ()),
    'VelocityXmlLexer': ('pip._vendor.pygments.lexers.templates', 'XML+Velocity', ('xml+velocity',), (), ('application/xml+velocity',)),
    'VerifpalLexer': ('pip._vendor.pygments.lexers.verifpal', 'Verifpal', ('verifpal',), ('*.vp',), ('text/x-verifpal',)),
    'VerilogLexer': ('pip._vendor.pygments.lexers.hdl', 'verilog', ('verilog', 'v'), ('*.v',), ('text/x-verilog',)),
    'VhdlLexer': ('pip._vendor.pygments.lexers.hdl', 'vhdl', ('vhdl',), ('*.vhdl', '*.vhd'), ('text/x-vhdl',)),
    'VimLexer': ('pip._vendor.pygments.lexers.textedit', 'VimL', ('vim',), ('*.vim', '.vimrc', '.exrc', '.gvimrc', '_vimrc', '_exrc', '_gvimrc', 'vimrc', 'gvimrc'), ('text/x-vim',)),
    'VisualPrologGrammarLexer': ('pip._vendor.pygments.lexers.vip', 'Visual Prolog Grammar', ('visualprologgrammar',), ('*.vipgrm',), ()),
    'VisualPrologLexer': ('pip._vendor.pygments.lexers.vip', 'Visual Prolog', ('visualprolog',), ('*.pro', '*.cl', '*.i', '*.pack', '*.ph'), ()),
    'VyperLexer': ('pip._vendor.pygments.lexers.vyper', 'Vyper', ('vyper',), ('*.vy',), ()),
    'WDiffLexer': ('pip._vendor.pygments.lexers.diff', 'WDiff', ('wdiff',), ('*.wdiff',), ()),
    'WatLexer': ('pip._vendor.pygments.lexers.webassembly', 'WebAssembly', ('wast', 'wat'), ('*.wat', '*.wast'), ()),
    'WebIDLLexer': ('pip._vendor.pygments.lexers.webidl', 'Web IDL', ('webidl',), ('*.webidl',), ()),
    'WgslLexer': ('pip._vendor.pygments.lexers.wgsl', 'WebGPU Shading Language', ('wgsl',), ('*.wgsl',), ('text/wgsl',)),
    'WhileyLexer': ('pip._vendor.pygments.lexers.whiley', 'Whiley', ('whiley',), ('*.whiley',), ('text/x-whiley',)),
    'WikitextLexer': ('pip._vendor.pygments.lexers.markup', 'Wikitext', ('wikitext', 'mediawiki'), (), ('text/x-wiki',)),
    'WoWTocLexer': ('pip._vendor.pygments.lexers.wowtoc', 'World of Warcraft TOC', ('wowtoc',), ('*.toc',), ()),
    'WrenLexer': ('pip._vendor.pygments.lexers.wren', 'Wren', ('wren',), ('*.wren',), ()),
    'X10Lexer': ('pip._vendor.pygments.lexers.x10', 'X10', ('x10', 'xten'), ('*.x10',), ('text/x-x10',)),
    'XMLUL4Lexer': ('pip._vendor.pygments.lexers.ul4', 'XML+UL4', ('xml+ul4',), ('*.xmlul4',), ()),
    'XQueryLexer': ('pip._vendor.pygments.lexers.webmisc', 'XQuery', ('xquery', 'xqy', 'xq', 'xql', 'xqm'), ('*.xqy', '*.xquery', '*.xq', '*.xql', '*.xqm'), ('text/xquery', 'application/xquery')),
    'XmlDjangoLexer': ('pip._vendor.pygments.lexers.templates', 'XML+Django/Jinja', ('xml+django', 'xml+jinja'), ('*.xml.j2', '*.xml.jinja2'), ('application/xml+django', 'application/xml+jinja')),
    'XmlErbLexer': ('pip._vendor.pygments.lexers.templates', 'XML+Ruby', ('xml+ruby', 'xml+erb'), (), ('application/xml+ruby',)),
    'XmlLexer': ('pip._vendor.pygments.lexers.html', 'XML', ('xml',), ('*.xml', '*.xsl', '*.rss', '*.xslt', '*.xsd', '*.wsdl', '*.wsf'), ('text/xml', 'application/xml', 'image/svg+xml', 'application/rss+xml', 'application/atom+xml')),
    'XmlPhpLexer': ('pip._vendor.pygments.lexers.templates', 'XML+PHP', ('xml+php',), (), ('application/xml+php',)),
    'XmlSmartyLexer': ('pip._vendor.pygments.lexers.templates', 'XML+Smarty', ('xml+smarty',), (), ('application/xml+smarty',)),
    'XorgLexer': ('pip._vendor.pygments.lexers.xorg', 'Xorg', ('xorg.conf',), ('xorg.conf',), ()),
    'XppLexer': ('pip._vendor.pygments.lexers.dotnet', 'X++', ('xpp', 'x++'), ('*.xpp',), ()),
    'XsltLexer': ('pip._vendor.pygments.lexers.html', 'XSLT', ('xslt',), ('*.xsl', '*.xslt', '*.xpl'), ('application/xsl+xml', 'application/xslt+xml')),
    'XtendLexer': ('pip._vendor.pygments.lexers.jvm', 'Xtend', ('xtend',), ('*.xtend',), ('text/x-xtend',)),
    'XtlangLexer': ('pip._vendor.pygments.lexers.lisp', 'xtlang', ('extempore',), ('*.xtm',), ()),
    'YamlJinjaLexer': ('pip._vendor.pygments.lexers.templates', 'YAML+Jinja', ('yaml+jinja', 'salt', 'sls'), ('*.sls', '*.yaml.j2', '*.yml.j2', '*.yaml.jinja2', '*.yml.jinja2'), ('text/x-yaml+jinja', 'text/x-sls')),
    'YamlLexer': ('pip._vendor.pygments.lexers.data', 'YAML', ('yaml',), ('*.yaml', '*.yml'), ('text/x-yaml',)),
    'YangLexer': ('pip._vendor.pygments.lexers.yang', 'YANG', ('yang',), ('*.yang',), ('application/yang',)),
    'YaraLexer': ('pip._vendor.pygments.lexers.yara', 'YARA', ('yara', 'yar'), ('*.yar',), ('text/x-yara',)),
    'ZeekLexer': ('pip._vendor.pygments.lexers.dsls', 'Zeek', ('zeek', 'bro'), ('*.zeek', '*.bro'), ()),
    'ZephirLexer': ('pip._vendor.pygments.lexers.php', 'Zephir', ('zephir',), ('*.zep',), ()),
    'ZigLexer': ('pip._vendor.pygments.lexers.zig', 'Zig', ('zig',), ('*.zig',), ('text/zig',)),
    'apdlexer': ('pip._vendor.pygments.lexers.apdlexer', 'ANSYS parametric design language', ('ansys', 'apdl'), ('*.ans',), ()),
}

# === NexusCore/openenv\Lib\site-packages\pythonwin\pywin\framework\winout.py ===
# winout.py
#
# generic "output window"
#
# This Window will detect itself closing, and recreate next time output is
# written to it.

# This has the option of writing output at idle time (by hooking the
# idle message, and queueing output) or writing as each
# write is executed.
# Updating the window directly gives a jerky appearance as many writes
# take place between commands, and the windows scrolls, and updates etc
# Updating at idle-time may defer all output of a long process, giving the
# appearence nothing is happening.
# There is a compromise "line" mode, which will output whenever
# a complete line is available.

# behaviour depends on self.writeQueueing

# This module is thread safe - output can originate from any thread.  If any thread
# other than the main thread attempts to print, it is always queued until next idle time

import queue
import re

import pywin.scintilla.document
import win32api
import win32con
import win32ui
from pywin.framework import app, window
from pywin.mfc import docview
from pywin.scintilla import scintillacon

debug = lambda msg: None
# debug=win32ui.OutputDebugString
# import win32trace;win32trace.InitWrite() # for debugging - delete me!
# debug = win32trace.write
# WindowOutputDocumentParent=docview.RichEditDoc
# WindowOutputDocumentParent=docview.Document
WindowOutputDocumentParent = pywin.scintilla.document.CScintillaDocument


class flags:
    # queueing of output.
    WQ_NONE = 0
    WQ_LINE = 1
    WQ_IDLE = 2


class WindowOutputDocument(WindowOutputDocumentParent):
    def SaveModified(self):
        return 1  # say it is OK to destroy my document

    def OnSaveDocument(self, fileName):
        win32ui.SetStatusText("Saving file...", 1)
        try:
            self.SaveFile(fileName)
        except OSError as details:
            win32ui.MessageBox("Error - could not save file\r\n\r\n%s" % details)
            return 0
        win32ui.SetStatusText("Ready")
        return 1


class WindowOutputFrame(window.MDIChildWnd):
    def __init__(self, wnd=None):
        window.MDIChildWnd.__init__(self, wnd)
        self.HookMessage(self.OnSizeMove, win32con.WM_SIZE)
        self.HookMessage(self.OnSizeMove, win32con.WM_MOVE)

    def LoadFrame(self, idResource, style, wndParent, context):
        self.template = context.template
        return self._obj_.LoadFrame(idResource, style, wndParent, context)

    def PreCreateWindow(self, cc):
        cc = self._obj_.PreCreateWindow(cc)
        if (
            self.template.defSize
            and self.template.defSize[0] != self.template.defSize[1]
        ):
            rect = app.RectToCreateStructRect(self.template.defSize)
            cc = cc[0], cc[1], cc[2], cc[3], rect, cc[5], cc[6], cc[7], cc[8]
        return cc

    def OnSizeMove(self, msg):
        # so recreate maintains position.
        # Need to map coordinates from the
        # frame windows first child.
        mdiClient = self.GetParent()
        self.template.defSize = mdiClient.ScreenToClient(self.GetWindowRect())

    def OnDestroy(self, message):
        self.template.OnFrameDestroy(self)
        return 1


class WindowOutputViewImpl:
    def __init__(self):
        self.patErrorMessage = re.compile(r'\W*File "(.*)", line ([0-9]+)')
        self.template = self.GetDocument().GetDocTemplate()

    def HookHandlers(self):
        # Hook for the right-click menu.
        self.HookMessage(self.OnRClick, win32con.WM_RBUTTONDOWN)

    def OnDestroy(self, msg):
        self.template.OnViewDestroy(self)

    def OnInitialUpdate(self):
        self.RestoreKillBuffer()
        self.SetSel(-2)  # end of buffer

    def GetRightMenuItems(self):
        ret = []
        flags = win32con.MF_STRING | win32con.MF_ENABLED
        ret.append((flags, win32ui.ID_EDIT_COPY, "&Copy"))
        ret.append((flags, win32ui.ID_EDIT_SELECT_ALL, "&Select all"))
        return ret

    #
    # Windows command handlers, virtuals, etc.
    #
    def OnRClick(self, params):
        paramsList = self.GetRightMenuItems()
        menu = win32ui.CreatePopupMenu()
        for appendParams in paramsList:
            if not isinstance(appendParams, tuple):
                appendParams = (appendParams,)
            menu.AppendMenu(*appendParams)
        menu.TrackPopupMenu(params[5])  # track at mouse position.
        return 0

    # as this is often used as an output window, exeptions will often
    # be printed.  Therefore, we support this functionality at this level.
    # Returns TRUE if the current line is an error message line, and will
    # jump to it.  FALSE if no error (and no action taken)
    def HandleSpecialLine(self):
        from . import scriptutils

        line = self.GetLine()
        if line[:11] == "com_error: ":
            # An OLE Exception - pull apart the exception
            # and try and locate a help file.
            try:
                import win32api
                import win32con

                det = eval(line[line.find(":") + 1 :].strip())
                win32ui.SetStatusText("Opening help file on OLE error...")
                from . import help

                help.OpenHelpFile(det[2][3], win32con.HELP_CONTEXT, det[2][4])
                return 1
            except win32api.error as details:
                win32ui.SetStatusText(
                    "The help file could not be opened - %s" % details.strerror
                )
                return 1
            except:
                win32ui.SetStatusText(
                    "Line is a COM error, but no WinHelp details can be parsed"
                )
        # Look for a Python traceback.
        matchResult = self.patErrorMessage.match(line)
        if matchResult is None:
            # No match - try the previous line
            lineNo = self.LineFromChar()
            if lineNo > 0:
                line = self.GetLine(lineNo - 1)
                matchResult = self.patErrorMessage.match(line)
        if matchResult is not None:
            # we have an error line.
            fileName = matchResult.group(1)
            if fileName[0] == "<":
                win32ui.SetStatusText("Can not load this file")
                return 1  # still was an error message.
            else:
                lineNoString = matchResult.group(2)
                # Attempt to locate the file (in case it is a relative spec)
                fileNameSpec = fileName
                fileName = scriptutils.LocatePythonFile(fileName)
                if fileName is None:
                    # Don't force update, so it replaces the idle prompt.
                    win32ui.SetStatusText(
                        "Can't locate the file '%s'" % (fileNameSpec), 0
                    )
                    return 1

                win32ui.SetStatusText(
                    "Jumping to line " + lineNoString + " of file " + fileName, 1
                )
                if not scriptutils.JumpToDocument(fileName, int(lineNoString)):
                    win32ui.SetStatusText("Could not open %s" % fileName)
                    return 1  # still was an error message.
                return 1
        return 0  # not an error line

    def write(self, msg):
        return self.template.write(msg)

    def writelines(self, lines):
        for line in lines:
            self.write(line)

    def flush(self):
        self.template.flush()


class WindowOutputViewRTF(docview.RichEditView, WindowOutputViewImpl):
    def __init__(self, doc):
        docview.RichEditView.__init__(self, doc)
        WindowOutputViewImpl.__init__(self)

    def OnInitialUpdate(self):
        WindowOutputViewImpl.OnInitialUpdate(self)
        return docview.RichEditView.OnInitialUpdate(self)

    def OnDestroy(self, msg):
        WindowOutputViewImpl.OnDestroy(self, msg)
        docview.RichEditView.OnDestroy(self, msg)

    def HookHandlers(self):
        WindowOutputViewImpl.HookHandlers(self)
        # Hook for finding and locating error messages
        self.HookMessage(self.OnLDoubleClick, win32con.WM_LBUTTONDBLCLK)

    # 		docview.RichEditView.HookHandlers(self)

    def OnLDoubleClick(self, params):
        if self.HandleSpecialLine():
            return 0  # don't pass on
        return 1  # pass it on by default.

    def RestoreKillBuffer(self):
        if len(self.template.killBuffer):
            self.StreamIn(win32con.SF_RTF, self._StreamRTFIn)
            self.template.killBuffer = []

    def SaveKillBuffer(self):
        self.StreamOut(win32con.SF_RTFNOOBJS, self._StreamRTFOut)

    def _StreamRTFOut(self, data):
        self.template.killBuffer.append(data)
        return 1  # keep em coming!

    def _StreamRTFIn(self, bytes):
        try:
            item = self.template.killBuffer[0]
            self.template.killBuffer.remove(item)
            if bytes < len(item):
                print("Warning - output buffer not big enough!")
            return item
        except IndexError:
            return None

    def dowrite(self, str):
        self.SetSel(-2)
        self.ReplaceSel(str)


import pywin.scintilla.view


class WindowOutputViewScintilla(
    pywin.scintilla.view.CScintillaView, WindowOutputViewImpl
):
    def __init__(self, doc):
        pywin.scintilla.view.CScintillaView.__init__(self, doc)
        WindowOutputViewImpl.__init__(self)

    def OnInitialUpdate(self):
        pywin.scintilla.view.CScintillaView.OnInitialUpdate(self)
        self.SCISetMarginWidth(3)
        WindowOutputViewImpl.OnInitialUpdate(self)

    def OnDestroy(self, msg):
        WindowOutputViewImpl.OnDestroy(self, msg)
        pywin.scintilla.view.CScintillaView.OnDestroy(self, msg)

    def HookHandlers(self):
        WindowOutputViewImpl.HookHandlers(self)
        pywin.scintilla.view.CScintillaView.HookHandlers(self)
        self.GetParent().HookNotify(
            self.OnScintillaDoubleClick, scintillacon.SCN_DOUBLECLICK
        )

    ##		self.HookMessage(self.OnLDoubleClick,win32con.WM_LBUTTONDBLCLK)

    def OnScintillaDoubleClick(self, std, extra):
        self.HandleSpecialLine()

    ##	def OnLDoubleClick(self,params):
    ##			return 0	# never don't pass on

    def RestoreKillBuffer(self):
        assert len(self.template.killBuffer) in (0, 1), "Unexpected killbuffer contents"
        if self.template.killBuffer:
            self.SCIAddText(self.template.killBuffer[0])
        self.template.killBuffer = []

    def SaveKillBuffer(self):
        self.template.killBuffer = [self.GetTextRange(0, -1)]

    def dowrite(self, str):
        end = self.GetTextLength()
        atEnd = end == self.GetSel()[0]
        self.SCIInsertText(str, end)
        if atEnd:
            self.SetSel(self.GetTextLength())

    def SetWordWrap(self, bWrapOn=1):
        if bWrapOn:
            wrap_mode = scintillacon.SC_WRAP_WORD
        else:
            wrap_mode = scintillacon.SC_WRAP_NONE
        self.SCISetWrapMode(wrap_mode)

    def _MakeColorizer(self):
        return None  # No colorizer for me!


WindowOutputView = WindowOutputViewScintilla


# The WindowOutput class is actually an MFC template.  This is a conventient way of
# making sure that my state can exist beyond the life of the windows themselves.
# This is primarily to support the functionality of a WindowOutput window automatically
# being recreated if necessary when written to.
class WindowOutput(docview.DocTemplate):
    """Looks like a general Output Window - text can be written by the 'write' method.
    Will auto-create itself on first write, and also on next write after being closed"""

    softspace = 1

    def __init__(
        self,
        title=None,
        defSize=None,
        queueing=flags.WQ_LINE,
        bAutoRestore=1,
        style=None,
        makeDoc=None,
        makeFrame=None,
        makeView=None,
    ):
        """init the output window -
        Params
        title=None -- What is the title of the window
        defSize=None -- What is the default size for the window - if this
                        is a string, the size will be loaded from the ini file.
        queueing = flags.WQ_LINE -- When should output be written
        bAutoRestore=1 -- Should a minimized window be restored.
        style -- Style for Window, or None for default.
        makeDoc, makeFrame, makeView -- Classes for frame, view and window respectively.
        """
        if makeDoc is None:
            makeDoc = WindowOutputDocument
        if makeFrame is None:
            makeFrame = WindowOutputFrame
        if makeView is None:
            makeView = WindowOutputViewScintilla
        docview.DocTemplate.__init__(
            self, win32ui.IDR_PYTHONTYPE, makeDoc, makeFrame, makeView
        )
        self.SetDocStrings("\nOutput\n\nText Documents (*.txt)\n.txt\n\n\n")
        win32ui.GetApp().AddDocTemplate(self)
        self.writeQueueing = queueing
        self.errorCantRecreate = 0
        self.killBuffer = []
        self.style = style
        self.bAutoRestore = bAutoRestore
        self.title = title
        self.bCreating = 0
        self.interruptCount = 0
        if isinstance(defSize, str):  # maintain size pos from ini file.
            self.iniSizeSection = defSize
            self.defSize = app.LoadWindowSize(defSize)
            self.loadedSize = self.defSize
        else:
            self.iniSizeSection = None
            self.defSize = defSize
        self.currentView = None
        self.outputQueue = queue.Queue(-1)
        self.mainThreadId = win32api.GetCurrentThreadId()
        self.idleHandlerSet = 0
        self.SetIdleHandler()

    def __del__(self):
        self.Close()

    def Create(self, title=None, style=None):
        self.bCreating = 1
        if title:
            self.title = title
        if style:
            self.style = style
        doc = self.OpenDocumentFile()
        if doc is None:
            return
        self.currentView = doc.GetFirstView()
        self.bCreating = 0
        if self.title:
            doc.SetTitle(self.title)

    def Close(self):
        self.RemoveIdleHandler()
        try:
            parent = self.currentView.GetParent()
        except (AttributeError, win32ui.error):  # Already closed
            return
        parent.DestroyWindow()

    def SetTitle(self, title):
        self.title = title
        if self.currentView:
            self.currentView.GetDocument().SetTitle(self.title)

    def OnViewDestroy(self, view):
        self.currentView.SaveKillBuffer()
        self.currentView = None

    def OnFrameDestroy(self, frame):
        if self.iniSizeSection:
            # use GetWindowPlacement(), as it works even when min'd or max'd
            newSize = frame.GetWindowPlacement()[4]
            if self.loadedSize != newSize:
                app.SaveWindowSize(self.iniSizeSection, newSize)

    def SetIdleHandler(self):
        if not self.idleHandlerSet:
            debug("Idle handler set\n")
            win32ui.GetApp().AddIdleHandler(self.QueueIdleHandler)
            self.idleHandlerSet = 1

    def RemoveIdleHandler(self):
        if self.idleHandlerSet:
            debug("Idle handler reset\n")
            if win32ui.GetApp().DeleteIdleHandler(self.QueueIdleHandler) == 0:
                debug("Error deleting idle handler\n")
            self.idleHandlerSet = 0

    def RecreateWindow(self):
        if self.errorCantRecreate:
            debug("Error = not trying again")
            return 0
        try:
            # This will fail if app shutting down
            win32ui.GetMainFrame().GetSafeHwnd()
            self.Create()
            return 1
        except (win32ui.error, AttributeError):
            self.errorCantRecreate = 1
            debug("Winout can not recreate the Window!\n")
            return 0

    # this handles the idle message, and does the printing.
    def QueueIdleHandler(self, handler, count):
        try:
            bEmpty = self.QueueFlush(20)
            # If the queue is empty, then we are back to idle and restart interrupt logic.
            if bEmpty:
                self.interruptCount = 0
        except KeyboardInterrupt:
            # First interrupt since idle we just pass on.
            # later ones we dump the queue and give up.
            self.interruptCount += 1
            if self.interruptCount > 1:
                # Drop the queue quickly as the user is already annoyed :-)
                self.outputQueue = queue.Queue(-1)
                print("Interrupted.")
                bEmpty = 1
            else:
                raise  # re-raise the error so the users exception filters up.
        return not bEmpty  # More to do if not empty.

    # Returns true if the Window needs to be recreated.
    def NeedRecreateWindow(self):
        try:
            if self.currentView is not None and self.currentView.IsWindow():
                return 0
        except (
            win32ui.error,
            AttributeError,
        ):  # Attribute error if the win32ui object has died.
            pass
        return 1

    # Returns true if the Window is OK (either cos it was, or because it was recreated
    def CheckRecreateWindow(self):
        if self.bCreating:
            return 1
        if not self.NeedRecreateWindow():
            return 1
        if self.bAutoRestore:
            if self.RecreateWindow():
                return 1
        return 0

    def QueueFlush(self, max=None):
        # Returns true if the queue is empty after the flush
        # 		debug("Queueflush - %d, %d\n" % (max, self.outputQueue.qsize()))
        if self.bCreating:
            return 1
        items = []
        rc = 0
        while max is None or max > 0:
            try:
                item = self.outputQueue.get_nowait()
                items.append(item)
            except queue.Empty:
                rc = 1
                break
            if max is not None:
                max -= 1
        if len(items) != 0:
            if not self.CheckRecreateWindow():
                debug(":Recreate failed!\n")
                return 1  # In trouble - so say we have nothing to do.
            win32ui.PumpWaitingMessages()  # Pump paint messages
            self.currentView.dowrite("".join(items))
        return rc

    def HandleOutput(self, message):
        # 		debug("QueueOutput on thread %d, flags %d with '%s'...\n" % (win32api.GetCurrentThreadId(), self.writeQueueing, message ))
        self.outputQueue.put(message)
        if win32api.GetCurrentThreadId() != self.mainThreadId:
            pass
        # 			debug("not my thread - ignoring queue options!\n")
        elif self.writeQueueing == flags.WQ_LINE:
            pos = message.rfind("\n")
            if pos >= 0:
                # 				debug("Line queueing - forcing flush\n")
                self.QueueFlush()
                return
        elif self.writeQueueing == flags.WQ_NONE:
            # 			debug("WQ_NONE - flushing!\n")
            self.QueueFlush()
            return
        # Let our idle handler get it - wake it up
        try:
            win32ui.GetMainFrame().PostMessage(
                win32con.WM_USER
            )  # Kick main thread off.
        except win32ui.error:
            # This can happen as the app is shutting down, so we send it to the C++ debugger
            win32api.OutputDebugString(message)

    # delegate certain fns to my view.
    def writelines(self, lines):
        for line in lines:
            self.write(line)

    def write(self, message):
        self.HandleOutput(message)

    def flush(self):
        self.QueueFlush()

    def HandleSpecialLine(self):
        self.currentView.HandleSpecialLine()


def RTFWindowOutput(*args, **kw):
    kw["makeView"] = WindowOutputViewRTF
    return WindowOutput(*args, **kw)


def thread_test(o):
    for i in range(5):
        o.write("Hi from thread %d\n" % (win32api.GetCurrentThreadId()))
        win32api.Sleep(100)


def test():
    w = WindowOutput(queueing=flags.WQ_IDLE)
    w.write("First bit of text\n")
    import _thread

    for i in range(5):
        w.write("Hello from the main thread\n")
        _thread.start_new(thread_test, (w,))
    for i in range(2):
        w.write("Hello from the main thread\n")
        win32api.Sleep(50)
    return w


if __name__ == "__main__":
    test()

# === NexusCore/openenv\Lib\site-packages\grpc\_simple_stubs.py ===
# Copyright 2020 The gRPC authors.
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
"""Functions that obviate explicit stubs and explicit channels."""

import collections
import datetime
import logging
import os
import threading
from typing import (
    Any,
    AnyStr,
    Callable,
    Dict,
    Iterator,
    Optional,
    Sequence,
    Tuple,
    TypeVar,
    Union,
)

import grpc
from grpc.experimental import experimental_api

RequestType = TypeVar("RequestType")
ResponseType = TypeVar("ResponseType")

OptionsType = Sequence[Tuple[str, str]]
CacheKey = Tuple[
    str,
    OptionsType,
    Optional[grpc.ChannelCredentials],
    Optional[grpc.Compression],
]

_LOGGER = logging.getLogger(__name__)

_EVICTION_PERIOD_KEY = "GRPC_PYTHON_MANAGED_CHANNEL_EVICTION_SECONDS"
if _EVICTION_PERIOD_KEY in os.environ:
    _EVICTION_PERIOD = datetime.timedelta(
        seconds=float(os.environ[_EVICTION_PERIOD_KEY])
    )
    _LOGGER.debug(
        "Setting managed channel eviction period to %s", _EVICTION_PERIOD
    )
else:
    _EVICTION_PERIOD = datetime.timedelta(minutes=10)

_MAXIMUM_CHANNELS_KEY = "GRPC_PYTHON_MANAGED_CHANNEL_MAXIMUM"
if _MAXIMUM_CHANNELS_KEY in os.environ:
    _MAXIMUM_CHANNELS = int(os.environ[_MAXIMUM_CHANNELS_KEY])
    _LOGGER.debug("Setting maximum managed channels to %d", _MAXIMUM_CHANNELS)
else:
    _MAXIMUM_CHANNELS = 2**8

_DEFAULT_TIMEOUT_KEY = "GRPC_PYTHON_DEFAULT_TIMEOUT_SECONDS"
if _DEFAULT_TIMEOUT_KEY in os.environ:
    _DEFAULT_TIMEOUT = float(os.environ[_DEFAULT_TIMEOUT_KEY])
    _LOGGER.debug("Setting default timeout seconds to %f", _DEFAULT_TIMEOUT)
else:
    _DEFAULT_TIMEOUT = 60.0


def _create_channel(
    target: str,
    options: Sequence[Tuple[str, str]],
    channel_credentials: Optional[grpc.ChannelCredentials],
    compression: Optional[grpc.Compression],
) -> grpc.Channel:
    _LOGGER.debug(
        f"Creating secure channel with credentials '{channel_credentials}', "
        + f"options '{options}' and compression '{compression}'"
    )
    return grpc.secure_channel(
        target,
        credentials=channel_credentials,
        options=options,
        compression=compression,
    )


class ChannelCache:
    # NOTE(rbellevi): Untyped due to reference cycle.
    _singleton = None
    _lock: threading.RLock = threading.RLock()
    _condition: threading.Condition = threading.Condition(lock=_lock)
    _eviction_ready: threading.Event = threading.Event()

    _mapping: Dict[CacheKey, Tuple[grpc.Channel, datetime.datetime]]
    _eviction_thread: threading.Thread

    def __init__(self):
        self._mapping = collections.OrderedDict()
        self._eviction_thread = threading.Thread(
            target=ChannelCache._perform_evictions, daemon=True
        )
        self._eviction_thread.start()

    @staticmethod
    def get():
        with ChannelCache._lock:
            if ChannelCache._singleton is None:
                ChannelCache._singleton = ChannelCache()
        ChannelCache._eviction_ready.wait()
        return ChannelCache._singleton

    def _evict_locked(self, key: CacheKey):
        channel, _ = self._mapping.pop(key)
        _LOGGER.debug(
            "Evicting channel %s with configuration %s.", channel, key
        )
        channel.close()
        del channel

    @staticmethod
    def _perform_evictions():
        while True:
            with ChannelCache._lock:
                ChannelCache._eviction_ready.set()
                if not ChannelCache._singleton._mapping:
                    ChannelCache._condition.wait()
                elif len(ChannelCache._singleton._mapping) > _MAXIMUM_CHANNELS:
                    key = next(iter(ChannelCache._singleton._mapping.keys()))
                    ChannelCache._singleton._evict_locked(key)
                    # And immediately reevaluate.
                else:
                    key, (_, eviction_time) = next(
                        iter(ChannelCache._singleton._mapping.items())
                    )
                    now = datetime.datetime.now()
                    if eviction_time <= now:
                        ChannelCache._singleton._evict_locked(key)
                        continue
                    else:
                        time_to_eviction = (eviction_time - now).total_seconds()
                        # NOTE: We aim to *eventually* coalesce to a state in
                        # which no overdue channels are in the cache and the
                        # length of the cache is longer than _MAXIMUM_CHANNELS.
                        # We tolerate momentary states in which these two
                        # criteria are not met.
                        ChannelCache._condition.wait(timeout=time_to_eviction)

    def get_channel(
        self,
        target: str,
        options: Sequence[Tuple[str, str]],
        channel_credentials: Optional[grpc.ChannelCredentials],
        insecure: bool,
        compression: Optional[grpc.Compression],
        method: str,
        _registered_method: bool,
    ) -> Tuple[grpc.Channel, Optional[int]]:
        """Get a channel from cache or creates a new channel.

        This method also takes care of register method for channel,
          which means we'll register a new call handle if we're calling a
          non-registered method for an existing channel.

        Returns:
            A tuple with two items. The first item is the channel, second item is
              the call handle if the method is registered, None if it's not registered.
        """
        if insecure and channel_credentials:
            raise ValueError(
                "The insecure option is mutually exclusive with "
                + "the channel_credentials option. Please use one "
                + "or the other."
            )
        if insecure:
            channel_credentials = (
                grpc.experimental.insecure_channel_credentials()
            )
        elif channel_credentials is None:
            _LOGGER.debug("Defaulting to SSL channel credentials.")
            channel_credentials = grpc.ssl_channel_credentials()
        key = (target, options, channel_credentials, compression)
        with self._lock:
            channel_data = self._mapping.get(key, None)
            call_handle = None
            if channel_data is not None:
                channel = channel_data[0]
                # Register a new call handle if we're calling a registered method for an
                # existing channel and this method is not registered.
                if _registered_method:
                    call_handle = channel._get_registered_call_handle(method)
                self._mapping.pop(key)
                self._mapping[key] = (
                    channel,
                    datetime.datetime.now() + _EVICTION_PERIOD,
                )
                return channel, call_handle
            else:
                channel = _create_channel(
                    target, options, channel_credentials, compression
                )
                if _registered_method:
                    call_handle = channel._get_registered_call_handle(method)
                self._mapping[key] = (
                    channel,
                    datetime.datetime.now() + _EVICTION_PERIOD,
                )
                if (
                    len(self._mapping) == 1
                    or len(self._mapping) >= _MAXIMUM_CHANNELS
                ):
                    self._condition.notify()
                return channel, call_handle

    def _test_only_channel_count(self) -> int:
        with self._lock:
            return len(self._mapping)


@experimental_api
# pylint: disable=too-many-locals
def unary_unary(
    request: RequestType,
    target: str,
    method: str,
    request_serializer: Optional[Callable[[Any], bytes]] = None,
    response_deserializer: Optional[Callable[[bytes], Any]] = None,
    options: Sequence[Tuple[AnyStr, AnyStr]] = (),
    channel_credentials: Optional[grpc.ChannelCredentials] = None,
    insecure: bool = False,
    call_credentials: Optional[grpc.CallCredentials] = None,
    compression: Optional[grpc.Compression] = None,
    wait_for_ready: Optional[bool] = None,
    timeout: Optional[float] = _DEFAULT_TIMEOUT,
    metadata: Optional[Sequence[Tuple[str, Union[str, bytes]]]] = None,
    _registered_method: Optional[bool] = False,
) -> ResponseType:
    """Invokes a unary-unary RPC without an explicitly specified channel.

    THIS IS AN EXPERIMENTAL API.

    This is backed by a per-process cache of channels. Channels are evicted
    from the cache after a fixed period by a background. Channels will also be
    evicted if more than a configured maximum accumulate.

    The default eviction period is 10 minutes. One may set the environment
    variable "GRPC_PYTHON_MANAGED_CHANNEL_EVICTION_SECONDS" to configure this.

    The default maximum number of channels is 256. One may set the
    environment variable "GRPC_PYTHON_MANAGED_CHANNEL_MAXIMUM" to configure
    this.

    Args:
      request: An iterator that yields request values for the RPC.
      target: The server address.
      method: The name of the RPC method.
      request_serializer: Optional :term:`serializer` for serializing the request
        message. Request goes unserialized in case None is passed.
      response_deserializer: Optional :term:`deserializer` for deserializing the response
        message. Response goes undeserialized in case None is passed.
      options: An optional list of key-value pairs (:term:`channel_arguments` in gRPC Core
        runtime) to configure the channel.
      channel_credentials: A credential applied to the whole channel, e.g. the
        return value of grpc.ssl_channel_credentials() or
        grpc.insecure_channel_credentials().
      insecure: If True, specifies channel_credentials as
        :term:`grpc.insecure_channel_credentials()`. This option is mutually
        exclusive with the `channel_credentials` option.
      call_credentials: A call credential applied to each call individually,
        e.g. the output of grpc.metadata_call_credentials() or
        grpc.access_token_call_credentials().
      compression: An optional value indicating the compression method to be
        used over the lifetime of the channel, e.g. grpc.Compression.Gzip.
      wait_for_ready: An optional flag indicating whether the RPC should fail
        immediately if the connection is not ready at the time the RPC is
        invoked, or if it should wait until the connection to the server
        becomes ready. When using this option, the user will likely also want
        to set a timeout. Defaults to True.
      timeout: An optional duration of time in seconds to allow for the RPC,
        after which an exception will be raised. If timeout is unspecified,
        defaults to a timeout controlled by the
        GRPC_PYTHON_DEFAULT_TIMEOUT_SECONDS environment variable. If that is
        unset, defaults to 60 seconds. Supply a value of None to indicate that
        no timeout should be enforced.
      metadata: Optional metadata to send to the server.

    Returns:
      The response to the RPC.
    """
    channel, method_handle = ChannelCache.get().get_channel(
        target,
        options,
        channel_credentials,
        insecure,
        compression,
        method,
        _registered_method,
    )
    multicallable = channel.unary_unary(
        method, request_serializer, response_deserializer, method_handle
    )
    wait_for_ready = wait_for_ready if wait_for_ready is not None else True
    return multicallable(
        request,
        metadata=metadata,
        wait_for_ready=wait_for_ready,
        credentials=call_credentials,
        timeout=timeout,
    )


@experimental_api
# pylint: disable=too-many-locals
def unary_stream(
    request: RequestType,
    target: str,
    method: str,
    request_serializer: Optional[Callable[[Any], bytes]] = None,
    response_deserializer: Optional[Callable[[bytes], Any]] = None,
    options: Sequence[Tuple[AnyStr, AnyStr]] = (),
    channel_credentials: Optional[grpc.ChannelCredentials] = None,
    insecure: bool = False,
    call_credentials: Optional[grpc.CallCredentials] = None,
    compression: Optional[grpc.Compression] = None,
    wait_for_ready: Optional[bool] = None,
    timeout: Optional[float] = _DEFAULT_TIMEOUT,
    metadata: Optional[Sequence[Tuple[str, Union[str, bytes]]]] = None,
    _registered_method: Optional[bool] = False,
) -> Iterator[ResponseType]:
    """Invokes a unary-stream RPC without an explicitly specified channel.

    THIS IS AN EXPERIMENTAL API.

    This is backed by a per-process cache of channels. Channels are evicted
    from the cache after a fixed period by a background. Channels will also be
    evicted if more than a configured maximum accumulate.

    The default eviction period is 10 minutes. One may set the environment
    variable "GRPC_PYTHON_MANAGED_CHANNEL_EVICTION_SECONDS" to configure this.

    The default maximum number of channels is 256. One may set the
    environment variable "GRPC_PYTHON_MANAGED_CHANNEL_MAXIMUM" to configure
    this.

    Args:
      request: An iterator that yields request values for the RPC.
      target: The server address.
      method: The name of the RPC method.
      request_serializer: Optional :term:`serializer` for serializing the request
        message. Request goes unserialized in case None is passed.
      response_deserializer: Optional :term:`deserializer` for deserializing the response
        message. Response goes undeserialized in case None is passed.
      options: An optional list of key-value pairs (:term:`channel_arguments` in gRPC Core
        runtime) to configure the channel.
      channel_credentials: A credential applied to the whole channel, e.g. the
        return value of grpc.ssl_channel_credentials().
      insecure: If True, specifies channel_credentials as
        :term:`grpc.insecure_channel_credentials()`. This option is mutually
        exclusive with the `channel_credentials` option.
      call_credentials: A call credential applied to each call individually,
        e.g. the output of grpc.metadata_call_credentials() or
        grpc.access_token_call_credentials().
      compression: An optional value indicating the compression method to be
        used over the lifetime of the channel, e.g. grpc.Compression.Gzip.
      wait_for_ready: An optional flag indicating whether the RPC should fail
        immediately if the connection is not ready at the time the RPC is
        invoked, or if it should wait until the connection to the server
        becomes ready. When using this option, the user will likely also want
        to set a timeout. Defaults to True.
      timeout: An optional duration of time in seconds to allow for the RPC,
        after which an exception will be raised. If timeout is unspecified,
        defaults to a timeout controlled by the
        GRPC_PYTHON_DEFAULT_TIMEOUT_SECONDS environment variable. If that is
        unset, defaults to 60 seconds. Supply a value of None to indicate that
        no timeout should be enforced.
      metadata: Optional metadata to send to the server.

    Returns:
      An iterator of responses.
    """
    channel, method_handle = ChannelCache.get().get_channel(
        target,
        options,
        channel_credentials,
        insecure,
        compression,
        method,
        _registered_method,
    )
    multicallable = channel.unary_stream(
        method, request_serializer, response_deserializer, method_handle
    )
    wait_for_ready = wait_for_ready if wait_for_ready is not None else True
    return multicallable(
        request,
        metadata=metadata,
        wait_for_ready=wait_for_ready,
        credentials=call_credentials,
        timeout=timeout,
    )


@experimental_api
# pylint: disable=too-many-locals
def stream_unary(
    request_iterator: Iterator[RequestType],
    target: str,
    method: str,
    request_serializer: Optional[Callable[[Any], bytes]] = None,
    response_deserializer: Optional[Callable[[bytes], Any]] = None,
    options: Sequence[Tuple[AnyStr, AnyStr]] = (),
    channel_credentials: Optional[grpc.ChannelCredentials] = None,
    insecure: bool = False,
    call_credentials: Optional[grpc.CallCredentials] = None,
    compression: Optional[grpc.Compression] = None,
    wait_for_ready: Optional[bool] = None,
    timeout: Optional[float] = _DEFAULT_TIMEOUT,
    metadata: Optional[Sequence[Tuple[str, Union[str, bytes]]]] = None,
    _registered_method: Optional[bool] = False,
) -> ResponseType:
    """Invokes a stream-unary RPC without an explicitly specified channel.

    THIS IS AN EXPERIMENTAL API.

    This is backed by a per-process cache of channels. Channels are evicted
    from the cache after a fixed period by a background. Channels will also be
    evicted if more than a configured maximum accumulate.

    The default eviction period is 10 minutes. One may set the environment
    variable "GRPC_PYTHON_MANAGED_CHANNEL_EVICTION_SECONDS" to configure this.

    The default maximum number of channels is 256. One may set the
    environment variable "GRPC_PYTHON_MANAGED_CHANNEL_MAXIMUM" to configure
    this.

    Args:
      request_iterator: An iterator that yields request values for the RPC.
      target: The server address.
      method: The name of the RPC method.
      request_serializer: Optional :term:`serializer` for serializing the request
        message. Request goes unserialized in case None is passed.
      response_deserializer: Optional :term:`deserializer` for deserializing the response
        message. Response goes undeserialized in case None is passed.
      options: An optional list of key-value pairs (:term:`channel_arguments` in gRPC Core
        runtime) to configure the channel.
      channel_credentials: A credential applied to the whole channel, e.g. the
        return value of grpc.ssl_channel_credentials().
      call_credentials: A call credential applied to each call individually,
        e.g. the output of grpc.metadata_call_credentials() or
        grpc.access_token_call_credentials().
      insecure: If True, specifies channel_credentials as
        :term:`grpc.insecure_channel_credentials()`. This option is mutually
        exclusive with the `channel_credentials` option.
      compression: An optional value indicating the compression method to be
        used over the lifetime of the channel, e.g. grpc.Compression.Gzip.
      wait_for_ready: An optional flag indicating whether the RPC should fail
        immediately if the connection is not ready at the time the RPC is
        invoked, or if it should wait until the connection to the server
        becomes ready. When using this option, the user will likely also want
        to set a timeout. Defaults to True.
      timeout: An optional duration of time in seconds to allow for the RPC,
        after which an exception will be raised. If timeout is unspecified,
        defaults to a timeout controlled by the
        GRPC_PYTHON_DEFAULT_TIMEOUT_SECONDS environment variable. If that is
        unset, defaults to 60 seconds. Supply a value of None to indicate that
        no timeout should be enforced.
      metadata: Optional metadata to send to the server.

    Returns:
      The response to the RPC.
    """
    channel, method_handle = ChannelCache.get().get_channel(
        target,
        options,
        channel_credentials,
        insecure,
        compression,
        method,
        _registered_method,
    )
    multicallable = channel.stream_unary(
        method, request_serializer, response_deserializer, method_handle
    )
    wait_for_ready = wait_for_ready if wait_for_ready is not None else True
    return multicallable(
        request_iterator,
        metadata=metadata,
        wait_for_ready=wait_for_ready,
        credentials=call_credentials,
        timeout=timeout,
    )


@experimental_api
# pylint: disable=too-many-locals
def stream_stream(
    request_iterator: Iterator[RequestType],
    target: str,
    method: str,
    request_serializer: Optional[Callable[[Any], bytes]] = None,
    response_deserializer: Optional[Callable[[bytes], Any]] = None,
    options: Sequence[Tuple[AnyStr, AnyStr]] = (),
    channel_credentials: Optional[grpc.ChannelCredentials] = None,
    insecure: bool = False,
    call_credentials: Optional[grpc.CallCredentials] = None,
    compression: Optional[grpc.Compression] = None,
    wait_for_ready: Optional[bool] = None,
    timeout: Optional[float] = _DEFAULT_TIMEOUT,
    metadata: Optional[Sequence[Tuple[str, Union[str, bytes]]]] = None,
    _registered_method: Optional[bool] = False,
) -> Iterator[ResponseType]:
    """Invokes a stream-stream RPC without an explicitly specified channel.

    THIS IS AN EXPERIMENTAL API.

    This is backed by a per-process cache of channels. Channels are evicted
    from the cache after a fixed period by a background. Channels will also be
    evicted if more than a configured maximum accumulate.

    The default eviction period is 10 minutes. One may set the environment
    variable "GRPC_PYTHON_MANAGED_CHANNEL_EVICTION_SECONDS" to configure this.

    The default maximum number of channels is 256. One may set the
    environment variable "GRPC_PYTHON_MANAGED_CHANNEL_MAXIMUM" to configure
    this.

    Args:
      request_iterator: An iterator that yields request values for the RPC.
      target: The server address.
      method: The name of the RPC method.
      request_serializer: Optional :term:`serializer` for serializing the request
        message. Request goes unserialized in case None is passed.
      response_deserializer: Optional :term:`deserializer` for deserializing the response
        message. Response goes undeserialized in case None is passed.
      options: An optional list of key-value pairs (:term:`channel_arguments` in gRPC Core
        runtime) to configure the channel.
      channel_credentials: A credential applied to the whole channel, e.g. the
        return value of grpc.ssl_channel_credentials().
      call_credentials: A call credential applied to each call individually,
        e.g. the output of grpc.metadata_call_credentials() or
        grpc.access_token_call_credentials().
      insecure: If True, specifies channel_credentials as
        :term:`grpc.insecure_channel_credentials()`. This option is mutually
        exclusive with the `channel_credentials` option.
      compression: An optional value indicating the compression method to be
        used over the lifetime of the channel, e.g. grpc.Compression.Gzip.
      wait_for_ready: An optional flag indicating whether the RPC should fail
        immediately if the connection is not ready at the time the RPC is
        invoked, or if it should wait until the connection to the server
        becomes ready. When using this option, the user will likely also want
        to set a timeout. Defaults to True.
      timeout: An optional duration of time in seconds to allow for the RPC,
        after which an exception will be raised. If timeout is unspecified,
        defaults to a timeout controlled by the
        GRPC_PYTHON_DEFAULT_TIMEOUT_SECONDS environment variable. If that is
        unset, defaults to 60 seconds. Supply a value of None to indicate that
        no timeout should be enforced.
      metadata: Optional metadata to send to the server.

    Returns:
      An iterator of responses.
    """
    channel, method_handle = ChannelCache.get().get_channel(
        target,
        options,
        channel_credentials,
        insecure,
        compression,
        method,
        _registered_method,
    )
    multicallable = channel.stream_stream(
        method, request_serializer, response_deserializer, method_handle
    )
    wait_for_ready = wait_for_ready if wait_for_ready is not None else True
    return multicallable(
        request_iterator,
        metadata=metadata,
        wait_for_ready=wait_for_ready,
        credentials=call_credentials,
        timeout=timeout,
    )

# === NexusCore/openenv\Lib\site-packages\pyasn1_modules\rfc2985.py ===
#
# This file is part of pyasn1-modules software.
#
# Created by Russ Housley with assistance from asn1ate v.0.6.0.
#
# Copyright (c) 2019, Vigil Security, LLC
# License: http://snmplabs.com/pyasn1/license.html
#
# PKCS#9: Selected Attribute Types (Version 2.0)
#
# ASN.1 source from:
# https://www.rfc-editor.org/rfc/rfc2985.txt
#

from pyasn1.type import char
from pyasn1.type import constraint
from pyasn1.type import namedtype
from pyasn1.type import namedval
from pyasn1.type import opentype
from pyasn1.type import tag
from pyasn1.type import univ
from pyasn1.type import useful

from pyasn1_modules import rfc7292
from pyasn1_modules import rfc5958
from pyasn1_modules import rfc5652
from pyasn1_modules import rfc5280


def _OID(*components):
    output = []
    for x in tuple(components):
        if isinstance(x, univ.ObjectIdentifier):
            output.extend(list(x))
        else:
            output.append(int(x))

    return univ.ObjectIdentifier(output)


MAX = float('inf')


# Imports from RFC 5280

AlgorithmIdentifier = rfc5280.AlgorithmIdentifier

Attribute = rfc5280.Attribute

EmailAddress = rfc5280.EmailAddress

Extensions = rfc5280.Extensions

Time = rfc5280.Time

X520countryName = rfc5280.X520countryName

X520SerialNumber = rfc5280.X520SerialNumber


# Imports from RFC 5652

ContentInfo = rfc5652.ContentInfo

ContentType = rfc5652.ContentType

Countersignature = rfc5652.Countersignature

MessageDigest = rfc5652.MessageDigest

SignerInfo = rfc5652.SignerInfo

SigningTime = rfc5652.SigningTime


# Imports from RFC 5958

EncryptedPrivateKeyInfo = rfc5958.EncryptedPrivateKeyInfo


# Imports from RFC 7292

PFX = rfc7292.PFX


# TODO:
# Need a place to import PKCS15Token; it does not yet appear in an RFC


# SingleAttribute is the same as Attribute in RFC 5280, except that the
# attrValues SET must have one and only one member

class AttributeType(univ.ObjectIdentifier):
    pass


class AttributeValue(univ.Any):
    pass


class AttributeValues(univ.SetOf):
    pass

AttributeValues.componentType = AttributeValue()


class SingleAttributeValues(univ.SetOf):
    pass

SingleAttributeValues.componentType = AttributeValue()


class SingleAttribute(univ.Sequence):
    pass

SingleAttribute.componentType = namedtype.NamedTypes(
    namedtype.NamedType('type', AttributeType()),
    namedtype.NamedType('values',
        AttributeValues().subtype(sizeSpec=constraint.ValueSizeConstraint(1, 1)),
        openType=opentype.OpenType('type', rfc5280.certificateAttributesMap)
    )
)


# CMSAttribute is the same as Attribute in RFC 5652, and CMSSingleAttribute
# is the companion where the attrValues SET must have one and only one member

CMSAttribute = rfc5652.Attribute


class CMSSingleAttribute(univ.Sequence):
    pass

CMSSingleAttribute.componentType = namedtype.NamedTypes(
    namedtype.NamedType('attrType', AttributeType()),
    namedtype.NamedType('attrValues',
        AttributeValues().subtype(sizeSpec=constraint.ValueSizeConstraint(1, 1)),
        openType=opentype.OpenType('attrType', rfc5652.cmsAttributesMap)
    )
)


# DirectoryString is the same as RFC 5280, except the length is limited to 255

class DirectoryString(univ.Choice):
    pass

DirectoryString.componentType = namedtype.NamedTypes(
    namedtype.NamedType('teletexString', char.TeletexString().subtype(
        subtypeSpec=constraint.ValueSizeConstraint(1, 255))),
    namedtype.NamedType('printableString', char.PrintableString().subtype(
        subtypeSpec=constraint.ValueSizeConstraint(1, 255))),
    namedtype.NamedType('universalString', char.UniversalString().subtype(
        subtypeSpec=constraint.ValueSizeConstraint(1, 255))),
    namedtype.NamedType('utf8String', char.UTF8String().subtype(
        subtypeSpec=constraint.ValueSizeConstraint(1, 255))),
    namedtype.NamedType('bmpString', char.BMPString().subtype(
        subtypeSpec=constraint.ValueSizeConstraint(1, 255)))
)


# PKCS9String is DirectoryString with an additional choice of IA5String,
# and the SIZE is limited to 255

class PKCS9String(univ.Choice):
    pass

PKCS9String.componentType = namedtype.NamedTypes(
    namedtype.NamedType('ia5String', char.IA5String().subtype(
        subtypeSpec=constraint.ValueSizeConstraint(1, 255))),
    namedtype.NamedType('directoryString', DirectoryString())
)


# Upper Bounds

pkcs_9_ub_pkcs9String = univ.Integer(255)

pkcs_9_ub_challengePassword = univ.Integer(pkcs_9_ub_pkcs9String)

pkcs_9_ub_emailAddress = univ.Integer(pkcs_9_ub_pkcs9String)

pkcs_9_ub_friendlyName = univ.Integer(pkcs_9_ub_pkcs9String)

pkcs_9_ub_match = univ.Integer(pkcs_9_ub_pkcs9String)

pkcs_9_ub_signingDescription = univ.Integer(pkcs_9_ub_pkcs9String)

pkcs_9_ub_unstructuredAddress = univ.Integer(pkcs_9_ub_pkcs9String)

pkcs_9_ub_unstructuredName = univ.Integer(pkcs_9_ub_pkcs9String)


ub_name = univ.Integer(32768)

pkcs_9_ub_placeOfBirth = univ.Integer(ub_name)

pkcs_9_ub_pseudonym = univ.Integer(ub_name)


# Object Identifier Arcs

ietf_at = _OID(1, 3, 6, 1, 5, 5, 7, 9)

id_at = _OID(2, 5, 4)

pkcs_9 = _OID(1, 2, 840, 113549, 1, 9)

pkcs_9_mo = _OID(pkcs_9, 0)

smime = _OID(pkcs_9, 16)

certTypes = _OID(pkcs_9, 22)

crlTypes = _OID(pkcs_9, 23)

pkcs_9_oc = _OID(pkcs_9, 24)

pkcs_9_at = _OID(pkcs_9, 25)

pkcs_9_sx = _OID(pkcs_9, 26)

pkcs_9_mr = _OID(pkcs_9, 27)


# Object Identifiers for Syntaxes for use with LDAP-accessible directories

pkcs_9_sx_pkcs9String = _OID(pkcs_9_sx, 1)

pkcs_9_sx_signingTime = _OID(pkcs_9_sx, 2)


# Object Identifiers for object classes

pkcs_9_oc_pkcsEntity = _OID(pkcs_9_oc, 1)

pkcs_9_oc_naturalPerson = _OID(pkcs_9_oc, 2)


# Object Identifiers for matching rules

pkcs_9_mr_caseIgnoreMatch = _OID(pkcs_9_mr, 1)

pkcs_9_mr_signingTimeMatch = _OID(pkcs_9_mr, 2)


# PKCS #7 PDU

pkcs_9_at_pkcs7PDU = _OID(pkcs_9_at, 5)

pKCS7PDU = Attribute()
pKCS7PDU['type'] = pkcs_9_at_pkcs7PDU
pKCS7PDU['values'][0] = ContentInfo()


# PKCS #12 token

pkcs_9_at_userPKCS12 = _OID(2, 16, 840, 1, 113730, 3, 1, 216)

userPKCS12 = Attribute()
userPKCS12['type'] = pkcs_9_at_userPKCS12
userPKCS12['values'][0] = PFX()


# PKCS #15 token

pkcs_9_at_pkcs15Token = _OID(pkcs_9_at, 1)

# TODO: Once PKCS15Token can be imported, this can be included
# 
# pKCS15Token = Attribute()
# userPKCS12['type'] = pkcs_9_at_pkcs15Token
# userPKCS12['values'][0] = PKCS15Token()


# PKCS #8 encrypted private key information

pkcs_9_at_encryptedPrivateKeyInfo = _OID(pkcs_9_at, 2)

encryptedPrivateKeyInfo = Attribute()
encryptedPrivateKeyInfo['type'] = pkcs_9_at_encryptedPrivateKeyInfo
encryptedPrivateKeyInfo['values'][0] = EncryptedPrivateKeyInfo()


# Electronic-mail address

pkcs_9_at_emailAddress = rfc5280.id_emailAddress

emailAddress = Attribute()
emailAddress['type'] = pkcs_9_at_emailAddress
emailAddress['values'][0] = EmailAddress()


# Unstructured name

pkcs_9_at_unstructuredName = _OID(pkcs_9, 2)

unstructuredName = Attribute()
unstructuredName['type'] = pkcs_9_at_unstructuredName
unstructuredName['values'][0] = PKCS9String()


# Unstructured address

pkcs_9_at_unstructuredAddress = _OID(pkcs_9, 8)

unstructuredAddress = Attribute()
unstructuredAddress['type'] = pkcs_9_at_unstructuredAddress
unstructuredAddress['values'][0] = DirectoryString()


# Date of birth

pkcs_9_at_dateOfBirth = _OID(ietf_at, 1)

dateOfBirth = SingleAttribute()
dateOfBirth['type'] = pkcs_9_at_dateOfBirth
dateOfBirth['values'][0] = useful.GeneralizedTime()


# Place of birth

pkcs_9_at_placeOfBirth = _OID(ietf_at, 2)

placeOfBirth = SingleAttribute()
placeOfBirth['type'] = pkcs_9_at_placeOfBirth
placeOfBirth['values'][0] = DirectoryString()


# Gender

class GenderString(char.PrintableString):
    pass

GenderString.subtypeSpec = constraint.ValueSizeConstraint(1, 1)
GenderString.subtypeSpec = constraint.SingleValueConstraint("M", "F", "m", "f")


pkcs_9_at_gender = _OID(ietf_at, 3)

gender = SingleAttribute()
gender['type'] = pkcs_9_at_gender
gender['values'][0] = GenderString()


# Country of citizenship

pkcs_9_at_countryOfCitizenship = _OID(ietf_at, 4)

countryOfCitizenship = Attribute()
countryOfCitizenship['type'] = pkcs_9_at_countryOfCitizenship
countryOfCitizenship['values'][0] = X520countryName()


#  Country of residence

pkcs_9_at_countryOfResidence = _OID(ietf_at, 5)

countryOfResidence = Attribute()
countryOfResidence['type'] = pkcs_9_at_countryOfResidence
countryOfResidence['values'][0] = X520countryName()


# Pseudonym

id_at_pseudonym = _OID(2, 5, 4, 65)

pseudonym = Attribute()
pseudonym['type'] = id_at_pseudonym
pseudonym['values'][0] = DirectoryString()


# Serial number

id_at_serialNumber = rfc5280.id_at_serialNumber

serialNumber = Attribute()
serialNumber['type'] = id_at_serialNumber
serialNumber['values'][0] = X520SerialNumber()


# Content type

pkcs_9_at_contentType = rfc5652.id_contentType

contentType = CMSSingleAttribute()
contentType['attrType'] = pkcs_9_at_contentType
contentType['attrValues'][0] = ContentType()


# Message digest

pkcs_9_at_messageDigest = rfc5652.id_messageDigest

messageDigest = CMSSingleAttribute()
messageDigest['attrType'] = pkcs_9_at_messageDigest
messageDigest['attrValues'][0] = MessageDigest()


# Signing time

pkcs_9_at_signingTime = rfc5652.id_signingTime

signingTime = CMSSingleAttribute()
signingTime['attrType'] = pkcs_9_at_signingTime
signingTime['attrValues'][0] = SigningTime()


# Random nonce

class RandomNonce(univ.OctetString):
    pass

RandomNonce.subtypeSpec = constraint.ValueSizeConstraint(4, MAX)


pkcs_9_at_randomNonce = _OID(pkcs_9_at, 3)

randomNonce = CMSSingleAttribute()
randomNonce['attrType'] = pkcs_9_at_randomNonce
randomNonce['attrValues'][0] = RandomNonce()


# Sequence number

class SequenceNumber(univ.Integer):
    pass

SequenceNumber.subtypeSpec = constraint.ValueRangeConstraint(1, MAX)


pkcs_9_at_sequenceNumber = _OID(pkcs_9_at, 4)

sequenceNumber = CMSSingleAttribute()
sequenceNumber['attrType'] = pkcs_9_at_sequenceNumber
sequenceNumber['attrValues'][0] = SequenceNumber()


# Countersignature

pkcs_9_at_counterSignature = rfc5652.id_countersignature

counterSignature = CMSAttribute()
counterSignature['attrType'] = pkcs_9_at_counterSignature
counterSignature['attrValues'][0] = Countersignature()


# Challenge password

pkcs_9_at_challengePassword = _OID(pkcs_9, 7)

challengePassword = SingleAttribute()
challengePassword['type'] = pkcs_9_at_challengePassword
challengePassword['values'][0] = DirectoryString()


# Extension request

class ExtensionRequest(Extensions):
    pass


pkcs_9_at_extensionRequest = _OID(pkcs_9, 14)

extensionRequest = SingleAttribute()
extensionRequest['type'] = pkcs_9_at_extensionRequest
extensionRequest['values'][0] = ExtensionRequest()


# Extended-certificate attributes (deprecated)

class AttributeSet(univ.SetOf):
    pass

AttributeSet.componentType = Attribute()


pkcs_9_at_extendedCertificateAttributes = _OID(pkcs_9, 9)

extendedCertificateAttributes = SingleAttribute()
extendedCertificateAttributes['type'] = pkcs_9_at_extendedCertificateAttributes
extendedCertificateAttributes['values'][0] = AttributeSet()


# Friendly name

class FriendlyName(char.BMPString):
    pass

FriendlyName.subtypeSpec = constraint.ValueSizeConstraint(1, pkcs_9_ub_friendlyName)


pkcs_9_at_friendlyName = _OID(pkcs_9, 20)

friendlyName = SingleAttribute()
friendlyName['type'] = pkcs_9_at_friendlyName
friendlyName['values'][0] = FriendlyName()


# Local key identifier

pkcs_9_at_localKeyId = _OID(pkcs_9, 21)

localKeyId = SingleAttribute()
localKeyId['type'] = pkcs_9_at_localKeyId
localKeyId['values'][0] = univ.OctetString()


# Signing description

pkcs_9_at_signingDescription = _OID(pkcs_9, 13)

signingDescription = CMSSingleAttribute()
signingDescription['attrType'] = pkcs_9_at_signingDescription
signingDescription['attrValues'][0] = DirectoryString()


# S/MIME capabilities

class SMIMECapability(AlgorithmIdentifier):
    pass


class SMIMECapabilities(univ.SequenceOf):
    pass

SMIMECapabilities.componentType = SMIMECapability()


pkcs_9_at_smimeCapabilities = _OID(pkcs_9, 15)

smimeCapabilities = CMSSingleAttribute()
smimeCapabilities['attrType'] = pkcs_9_at_smimeCapabilities
smimeCapabilities['attrValues'][0] = SMIMECapabilities()


# Certificate Attribute Map

_certificateAttributesMapUpdate = {
    # Attribute types for use with the "pkcsEntity" object class
    pkcs_9_at_pkcs7PDU: ContentInfo(),
    pkcs_9_at_userPKCS12: PFX(),
    # TODO: Once PKCS15Token can be imported, this can be included
    # pkcs_9_at_pkcs15Token: PKCS15Token(),
    pkcs_9_at_encryptedPrivateKeyInfo: EncryptedPrivateKeyInfo(),
    # Attribute types for use with the "naturalPerson" object class
    pkcs_9_at_emailAddress: EmailAddress(),
    pkcs_9_at_unstructuredName: PKCS9String(),
    pkcs_9_at_unstructuredAddress: DirectoryString(),
    pkcs_9_at_dateOfBirth: useful.GeneralizedTime(),
    pkcs_9_at_placeOfBirth: DirectoryString(),
    pkcs_9_at_gender: GenderString(),
    pkcs_9_at_countryOfCitizenship: X520countryName(),
    pkcs_9_at_countryOfResidence: X520countryName(),
    id_at_pseudonym: DirectoryString(),
    id_at_serialNumber: X520SerialNumber(),
    # Attribute types for use with PKCS #10 certificate requests
    pkcs_9_at_challengePassword: DirectoryString(),
    pkcs_9_at_extensionRequest: ExtensionRequest(),
    pkcs_9_at_extendedCertificateAttributes: AttributeSet(),
}

rfc5280.certificateAttributesMap.update(_certificateAttributesMapUpdate)


# CMS Attribute Map

# Note: pkcs_9_at_smimeCapabilities is not included in the map because
#       the definition in RFC 5751 is preferred, which produces the same
#       encoding, but it allows different parameters for SMIMECapability
#       and AlgorithmIdentifier.

_cmsAttributesMapUpdate = {
    # Attribute types for use in PKCS #7 data (a.k.a. CMS)
    pkcs_9_at_contentType: ContentType(),
    pkcs_9_at_messageDigest: MessageDigest(),
    pkcs_9_at_signingTime: SigningTime(),
    pkcs_9_at_randomNonce: RandomNonce(),
    pkcs_9_at_sequenceNumber: SequenceNumber(),
    pkcs_9_at_counterSignature: Countersignature(),
    # Attributes for use in PKCS #12 "PFX" PDUs or PKCS #15 tokens
    pkcs_9_at_friendlyName: FriendlyName(),
    pkcs_9_at_localKeyId: univ.OctetString(),
    pkcs_9_at_signingDescription: DirectoryString(),
    # pkcs_9_at_smimeCapabilities: SMIMECapabilities(),
}

rfc5652.cmsAttributesMap.update(_cmsAttributesMapUpdate)

# === NexusCore/openenv\Lib\site-packages\smmap\mman.py ===
"""Module containing a memory memory manager which provides a sliding window on a number of memory mapped files"""
from .util import (
    MapWindow,
    MapRegion,
    MapRegionList,
    is_64_bit,
)

import sys
from functools import reduce

__all__ = ["StaticWindowMapManager", "SlidingWindowMapManager", "WindowCursor"]
#{ Utilities

#}END utilities


class WindowCursor:

    """
    Pointer into the mapped region of the memory manager, keeping the map
    alive until it is destroyed and no other client uses it.

    Cursors should not be created manually, but are instead returned by the SlidingWindowMapManager

    **Note:**: The current implementation is suited for static and sliding window managers, but it also means
    that it must be suited for the somewhat quite different sliding manager. It could be improved, but
    I see no real need to do so."""
    __slots__ = (
        '_manager',  # the manager keeping all file regions
        '_rlist',   # a regions list with regions for our file
        '_region',  # our current class:`MapRegion` or None
        '_ofs',     # relative offset from the actually mapped area to our start area
        '_size'     # maximum size we should provide
    )

    def __init__(self, manager=None, regions=None):
        self._manager = manager
        self._rlist = regions
        self._region = None
        self._ofs = 0
        self._size = 0

    def __del__(self):
        self._destroy()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self._destroy()

    def _destroy(self):
        """Destruction code to decrement counters"""
        self.unuse_region()

        if self._rlist is not None:
            # Actual client count, which doesn't include the reference kept by the manager, nor ours
            # as we are about to be deleted
            try:
                if len(self._rlist) == 0:
                    # Free all resources associated with the mapped file
                    self._manager._fdict.pop(self._rlist.path_or_fd())
                # END remove regions list from manager
            except (TypeError, KeyError):
                # sometimes, during shutdown, getrefcount is None. Its possible
                # to re-import it, however, its probably better to just ignore
                # this python problem (for now).
                # The next step is to get rid of the error prone getrefcount altogether.
                pass
            # END exception handling
        # END handle regions

    def _copy_from(self, rhs):
        """Copy all data from rhs into this instance, handles usage count"""
        self._manager = rhs._manager
        self._rlist = type(rhs._rlist)(rhs._rlist)
        self._region = rhs._region
        self._ofs = rhs._ofs
        self._size = rhs._size

        for region in self._rlist:
            region.increment_client_count()

        if self._region is not None:
            self._region.increment_client_count()
        # END handle regions

    def __copy__(self):
        """copy module interface"""
        cpy = type(self)()
        cpy._copy_from(self)
        return cpy

    #{ Interface
    def assign(self, rhs):
        """Assign rhs to this instance. This is required in order to get a real copy.
        Alternatively, you can copy an existing instance using the copy module"""
        self._destroy()
        self._copy_from(rhs)

    def use_region(self, offset=0, size=0, flags=0):
        """Assure we point to a window which allows access to the given offset into the file

        :param offset: absolute offset in bytes into the file
        :param size: amount of bytes to map. If 0, all available bytes will be mapped
        :param flags: additional flags to be given to os.open in case a file handle is initially opened
            for mapping. Has no effect if a region can actually be reused.
        :return: this instance - it should be queried for whether it points to a valid memory region.
            This is not the case if the mapping failed because we reached the end of the file

        **Note:**: The size actually mapped may be smaller than the given size. If that is the case,
        either the file has reached its end, or the map was created between two existing regions"""
        need_region = True
        man = self._manager
        fsize = self._rlist.file_size()
        size = min(size or fsize, man.window_size() or fsize)   # clamp size to window size

        if self._region is not None:
            if self._region.includes_ofs(offset):
                need_region = False
            else:
                self.unuse_region()
            # END handle existing region
        # END check existing region

        # offset too large ?
        if offset >= fsize:
            return self
        # END handle offset

        if need_region:
            self._region = man._obtain_region(self._rlist, offset, size, flags, False)
            self._region.increment_client_count()
        # END need region handling

        self._ofs = offset - self._region._b
        self._size = min(size, self._region.ofs_end() - offset)

        return self

    def unuse_region(self):
        """Unuse the current region. Does nothing if we have no current region

        **Note:** the cursor unuses the region automatically upon destruction. It is recommended
        to un-use the region once you are done reading from it in persistent cursors as it
        helps to free up resource more quickly"""
        if self._region is not None:
            self._region.increment_client_count(-1)
        self._region = None
        # note: should reset ofs and size, but we spare that for performance. Its not
        # allowed to query information if we are not valid !

    def buffer(self):
        """Return a buffer object which allows access to our memory region from our offset
        to the window size. Please note that it might be smaller than you requested when calling use_region()

        **Note:** You can only obtain a buffer if this instance is_valid() !

        **Note:** buffers should not be cached passed the duration of your access as it will
        prevent resources from being freed even though they might not be accounted for anymore !"""
        return memoryview(self._region.buffer())[self._ofs:self._ofs+self._size]

    def map(self):
        """
        :return: the underlying raw memory map. Please not that the offset and size is likely to be different
            to what you set as offset and size. Use it only if you are sure about the region it maps, which is the whole
            file in case of StaticWindowMapManager"""
        return self._region.map()

    def is_valid(self):
        """:return: True if we have a valid and usable region"""
        return self._region is not None

    def is_associated(self):
        """:return: True if we are associated with a specific file already"""
        return self._rlist is not None

    def ofs_begin(self):
        """:return: offset to the first byte pointed to by our cursor

        **Note:** only if is_valid() is True"""
        return self._region._b + self._ofs

    def ofs_end(self):
        """:return: offset to one past the last available byte"""
        # unroll method calls for performance !
        return self._region._b + self._ofs + self._size

    def size(self):
        """:return: amount of bytes we point to"""
        return self._size

    def region(self):
        """:return: our mapped region, or None if nothing is mapped yet
        :raise AssertionError: if we have no current region. This is only useful for debugging"""
        return self._region

    def includes_ofs(self, ofs):
        """:return: True if the given absolute offset is contained in the cursors
            current region

        **Note:** cursor must be valid for this to work"""
        # unroll methods
        return (self._region._b + self._ofs) <= ofs < (self._region._b + self._ofs + self._size)

    def file_size(self):
        """:return: size of the underlying file"""
        return self._rlist.file_size()

    def path_or_fd(self):
        """:return: path or file descriptor of the underlying mapped file"""
        return self._rlist.path_or_fd()

    def path(self):
        """:return: path of the underlying mapped file
        :raise ValueError: if attached path is not a path"""
        if isinstance(self._rlist.path_or_fd(), int):
            raise ValueError("Path queried although mapping was applied to a file descriptor")
        # END handle type
        return self._rlist.path_or_fd()

    def fd(self):
        """:return: file descriptor used to create the underlying mapping.

        **Note:** it is not required to be valid anymore
        :raise ValueError: if the mapping was not created by a file descriptor"""
        if isinstance(self._rlist.path_or_fd(), str):
            raise ValueError("File descriptor queried although mapping was generated from path")
        # END handle type
        return self._rlist.path_or_fd()

    #} END interface


class StaticWindowMapManager:

    """Provides a manager which will produce single size cursors that are allowed
    to always map the whole file.

    Clients must be written to specifically know that they are accessing their data
    through a StaticWindowMapManager, as they otherwise have to deal with their window size.

    These clients would have to use a SlidingWindowMapBuffer to hide this fact.

    This type will always use a maximum window size, and optimize certain methods to
    accommodate this fact"""

    __slots__ = [
        '_fdict',           # mapping of path -> StorageHelper (of some kind
        '_window_size',     # maximum size of a window
        '_max_memory_size',  # maximum amount of memory we may allocate
        '_max_handle_count',        # maximum amount of handles to keep open
        '_memory_size',     # currently allocated memory size
        '_handle_count',        # amount of currently allocated file handles
    ]

    #{ Configuration
    MapRegionListCls = MapRegionList
    MapWindowCls = MapWindow
    MapRegionCls = MapRegion
    WindowCursorCls = WindowCursor
    #} END configuration

    _MB_in_bytes = 1024 * 1024

    def __init__(self, window_size=0, max_memory_size=0, max_open_handles=sys.maxsize):
        """initialize the manager with the given parameters.
        :param window_size: if -1, a default window size will be chosen depending on
            the operating system's architecture. It will internally be quantified to a multiple of the page size
            If 0, the window may have any size, which basically results in mapping the whole file at one
        :param max_memory_size: maximum amount of memory we may map at once before releasing mapped regions.
            If 0, a viable default will be set depending on the system's architecture.
            It is a soft limit that is tried to be kept, but nothing bad happens if we have to over-allocate
        :param max_open_handles: if not maxint, limit the amount of open file handles to the given number.
            Otherwise the amount is only limited by the system itself. If a system or soft limit is hit,
            the manager will free as many handles as possible"""
        self._fdict = dict()
        self._window_size = window_size
        self._max_memory_size = max_memory_size
        self._max_handle_count = max_open_handles
        self._memory_size = 0
        self._handle_count = 0

        if window_size < 0:
            coeff = 64
            if is_64_bit():
                coeff = 1024
            # END handle arch
            self._window_size = coeff * self._MB_in_bytes
        # END handle max window size

        if max_memory_size == 0:
            coeff = 1024
            if is_64_bit():
                coeff = 8192
            # END handle arch
            self._max_memory_size = coeff * self._MB_in_bytes
        # END handle max memory size

    #{ Internal Methods

    def _collect_lru_region(self, size):
        """Unmap the region which was least-recently used and has no client
        :param size: size of the region we want to map next (assuming its not already mapped partially or full
            if 0, we try to free any available region
        :return: Amount of freed regions

        .. Note::
            We don't raise exceptions anymore, in order to keep the system working, allowing temporary overallocation.
            If the system runs out of memory, it will tell.

        .. TODO::
            implement a case where all unusued regions are discarded efficiently.
            Currently its only brute force
        """
        num_found = 0
        while (size == 0) or (self._memory_size + size > self._max_memory_size):
            lru_region = None
            lru_list = None
            for regions in self._fdict.values():
                for region in regions:
                    # check client count - if it's 1, it's just us
                    if (region.client_count() == 1 and
                            (lru_region is None or region._uc < lru_region._uc)):
                        lru_region = region
                        lru_list = regions
                    # END update lru_region
                # END for each region
            # END for each regions list

            if lru_region is None:
                break
            # END handle region not found

            num_found += 1
            del(lru_list[lru_list.index(lru_region)])
            lru_region.increment_client_count(-1)
            self._memory_size -= lru_region.size()
            self._handle_count -= 1
        # END while there is more memory to free
        return num_found

    def _obtain_region(self, a, offset, size, flags, is_recursive):
        """Utility to create a new region - for more information on the parameters,
        see MapCursor.use_region.
        :param a: A regions (a)rray
        :return: The newly created region"""
        if self._memory_size + size > self._max_memory_size:
            self._collect_lru_region(size)
        # END handle collection

        r = None
        if a:
            assert len(a) == 1
            r = a[0]
        else:
            try:
                r = self.MapRegionCls(a.path_or_fd(), 0, sys.maxsize, flags)
            except Exception:
                # apparently we are out of system resources or hit a limit
                # As many more operations are likely to fail in that condition (
                # like reading a file from disk, etc) we free up as much as possible
                # As this invalidates our insert position, we have to recurse here
                if is_recursive:
                    # we already tried this, and still have no success in obtaining
                    # a mapping. This is an exception, so we propagate it
                    raise
                # END handle existing recursion
                self._collect_lru_region(0)
                return self._obtain_region(a, offset, size, flags, True)
            # END handle exceptions

            self._handle_count += 1
            self._memory_size += r.size()
            a.append(r)
        # END handle array

        assert r.includes_ofs(offset)
        return r

    #}END internal methods

    #{ Interface
    def make_cursor(self, path_or_fd):
        """
        :return: a cursor pointing to the given path or file descriptor.
            It can be used to map new regions of the file into memory

        **Note:** if a file descriptor is given, it is assumed to be open and valid,
        but may be closed afterwards. To refer to the same file, you may reuse
        your existing file descriptor, but keep in mind that new windows can only
        be mapped as long as it stays valid. This is why the using actual file paths
        are preferred unless you plan to keep the file descriptor open.

        **Note:** file descriptors are problematic as they are not necessarily unique, as two
        different files opened and closed in succession might have the same file descriptor id.

        **Note:** Using file descriptors directly is faster once new windows are mapped as it
        prevents the file to be opened again just for the purpose of mapping it."""
        regions = self._fdict.get(path_or_fd)
        if regions is None:
            regions = self.MapRegionListCls(path_or_fd)
            self._fdict[path_or_fd] = regions
        # END obtain region for path
        return self.WindowCursorCls(self, regions)

    def collect(self):
        """Collect all available free-to-collect mapped regions
        :return: Amount of freed handles"""
        return self._collect_lru_region(0)

    def num_file_handles(self):
        """:return: amount of file handles in use. Each mapped region uses one file handle"""
        return self._handle_count

    def num_open_files(self):
        """Amount of opened files in the system"""
        return reduce(lambda x, y: x + y, (1 for rlist in self._fdict.values() if len(rlist) > 0), 0)

    def window_size(self):
        """:return: size of each window when allocating new regions"""
        return self._window_size

    def mapped_memory_size(self):
        """:return: amount of bytes currently mapped in total"""
        return self._memory_size

    def max_file_handles(self):
        """:return: maximum amount of handles we may have opened"""
        return self._max_handle_count

    def max_mapped_memory_size(self):
        """:return: maximum amount of memory we may allocate"""
        return self._max_memory_size

    #} END interface

    #{ Special Purpose Interface

    def force_map_handle_removal_win(self, base_path):
        """ONLY AVAILABLE ON WINDOWS
        On windows removing files is not allowed if anybody still has it opened.
        If this process is ourselves, and if the whole process uses this memory
        manager (as far as the parent framework is concerned) we can enforce
        closing all memory maps whose path matches the given base path to
        allow the respective operation after all.
        The respective system must NOT access the closed memory regions anymore !
        This really may only be used if you know that the items which keep
        the cursors alive will not be using it anymore. They need to be recreated !
        :return: Amount of closed handles

        **Note:** does nothing on non-windows platforms"""
        if sys.platform != 'win32':
            return
        # END early bailout

        num_closed = 0
        for path, rlist in self._fdict.items():
            if path.startswith(base_path):
                for region in rlist:
                    region.release()
                    num_closed += 1
            # END path matches
        # END for each path
        return num_closed
    #} END special purpose interface


class SlidingWindowMapManager(StaticWindowMapManager):

    """Maintains a list of ranges of mapped memory regions in one or more files and allows to easily
    obtain additional regions assuring there is no overlap.
    Once a certain memory limit is reached globally, or if there cannot be more open file handles
    which result from each mmap call, the least recently used, and currently unused mapped regions
    are unloaded automatically.

    **Note:** currently not thread-safe !

    **Note:** in the current implementation, we will automatically unload windows if we either cannot
        create more memory maps (as the open file handles limit is hit) or if we have allocated more than
        a safe amount of memory already, which would possibly cause memory allocations to fail as our address
        space is full."""

    __slots__ = tuple()

    def __init__(self, window_size=-1, max_memory_size=0, max_open_handles=sys.maxsize):
        """Adjusts the default window size to -1"""
        super().__init__(window_size, max_memory_size, max_open_handles)

    def _obtain_region(self, a, offset, size, flags, is_recursive):
        # bisect to find an existing region. The c++ implementation cannot
        # do that as it uses a linked list for regions.
        r = None
        lo = 0
        hi = len(a)
        while lo < hi:
            mid = (lo + hi) // 2
            ofs = a[mid]._b
            if ofs <= offset:
                if a[mid].includes_ofs(offset):
                    r = a[mid]
                    break
                # END have region
                lo = mid + 1
            else:
                hi = mid
            # END handle position
        # END while bisecting

        if r is None:
            window_size = self._window_size
            left = self.MapWindowCls(0, 0)
            mid = self.MapWindowCls(offset, size)
            right = self.MapWindowCls(a.file_size(), 0)

            # we want to honor the max memory size, and assure we have anough
            # memory available
            # Save calls !
            if self._memory_size + window_size > self._max_memory_size:
                self._collect_lru_region(window_size)
            # END handle collection

            # we assume the list remains sorted by offset
            insert_pos = 0
            len_regions = len(a)
            if len_regions == 1:
                if a[0]._b <= offset:
                    insert_pos = 1
                # END maintain sort
            else:
                # find insert position
                insert_pos = len_regions
                for i, region in enumerate(a):
                    if region._b > offset:
                        insert_pos = i
                        break
                    # END if insert position is correct
                # END for each region
            # END obtain insert pos

            # adjust the actual offset and size values to create the largest
            # possible mapping
            if insert_pos == 0:
                if len_regions:
                    right = self.MapWindowCls.from_region(a[insert_pos])
                # END adjust right side
            else:
                if insert_pos != len_regions:
                    right = self.MapWindowCls.from_region(a[insert_pos])
                # END adjust right window
                left = self.MapWindowCls.from_region(a[insert_pos - 1])
            # END adjust surrounding windows

            mid.extend_left_to(left, window_size)
            mid.extend_right_to(right, window_size)
            mid.align()

            # it can happen that we align beyond the end of the file
            if mid.ofs_end() > right.ofs:
                mid.size = right.ofs - mid.ofs
            # END readjust size

            # insert new region at the right offset to keep the order
            try:
                if self._handle_count >= self._max_handle_count:
                    raise Exception
                # END assert own imposed max file handles
                r = self.MapRegionCls(a.path_or_fd(), mid.ofs, mid.size, flags)
            except Exception:
                # apparently we are out of system resources or hit a limit
                # As many more operations are likely to fail in that condition (
                # like reading a file from disk, etc) we free up as much as possible
                # As this invalidates our insert position, we have to recurse here
                if is_recursive:
                    # we already tried this, and still have no success in obtaining
                    # a mapping. This is an exception, so we propagate it
                    raise
                # END handle existing recursion
                self._collect_lru_region(0)
                return self._obtain_region(a, offset, size, flags, True)
            # END handle exceptions

            self._handle_count += 1
            self._memory_size += r.size()
            a.insert(insert_pos, r)
        # END create new region
        return r

# === NexusCore/openenv\Lib\site-packages\tornado\locale.py ===
# Copyright 2009 Facebook
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

"""Translation methods for generating localized strings.

To load a locale and generate a translated string::

    user_locale = tornado.locale.get("es_LA")
    print(user_locale.translate("Sign out"))

`tornado.locale.get()` returns the closest matching locale, not necessarily the
specific locale you requested. You can support pluralization with
additional arguments to `~Locale.translate()`, e.g.::

    people = [...]
    message = user_locale.translate(
        "%(list)s is online", "%(list)s are online", len(people))
    print(message % {"list": user_locale.list(people)})

The first string is chosen if ``len(people) == 1``, otherwise the second
string is chosen.

Applications should call one of `load_translations` (which uses a simple
CSV format) or `load_gettext_translations` (which uses the ``.mo`` format
supported by `gettext` and related tools).  If neither method is called,
the `Locale.translate` method will simply return the original string.
"""

import codecs
import csv
import datetime
import gettext
import glob
import os
import re

from tornado import escape
from tornado.log import gen_log

from tornado._locale_data import LOCALE_NAMES

from typing import Iterable, Any, Union, Dict, Optional

_default_locale = "en_US"
_translations = {}  # type: Dict[str, Any]
_supported_locales = frozenset([_default_locale])
_use_gettext = False
CONTEXT_SEPARATOR = "\x04"


def get(*locale_codes: str) -> "Locale":
    """Returns the closest match for the given locale codes.

    We iterate over all given locale codes in order. If we have a tight
    or a loose match for the code (e.g., "en" for "en_US"), we return
    the locale. Otherwise we move to the next code in the list.

    By default we return ``en_US`` if no translations are found for any of
    the specified locales. You can change the default locale with
    `set_default_locale()`.
    """
    return Locale.get_closest(*locale_codes)


def set_default_locale(code: str) -> None:
    """Sets the default locale.

    The default locale is assumed to be the language used for all strings
    in the system. The translations loaded from disk are mappings from
    the default locale to the destination locale. Consequently, you don't
    need to create a translation file for the default locale.
    """
    global _default_locale
    global _supported_locales
    _default_locale = code
    _supported_locales = frozenset(list(_translations.keys()) + [_default_locale])


def load_translations(directory: str, encoding: Optional[str] = None) -> None:
    """Loads translations from CSV files in a directory.

    Translations are strings with optional Python-style named placeholders
    (e.g., ``My name is %(name)s``) and their associated translations.

    The directory should have translation files of the form ``LOCALE.csv``,
    e.g. ``es_GT.csv``. The CSV files should have two or three columns: string,
    translation, and an optional plural indicator. Plural indicators should
    be one of "plural" or "singular". A given string can have both singular
    and plural forms. For example ``%(name)s liked this`` may have a
    different verb conjugation depending on whether %(name)s is one
    name or a list of names. There should be two rows in the CSV file for
    that string, one with plural indicator "singular", and one "plural".
    For strings with no verbs that would change on translation, simply
    use "unknown" or the empty string (or don't include the column at all).

    The file is read using the `csv` module in the default "excel" dialect.
    In this format there should not be spaces after the commas.

    If no ``encoding`` parameter is given, the encoding will be
    detected automatically (among UTF-8 and UTF-16) if the file
    contains a byte-order marker (BOM), defaulting to UTF-8 if no BOM
    is present.

    Example translation ``es_LA.csv``::

        "I love you","Te amo"
        "%(name)s liked this","A %(name)s les gustó esto","plural"
        "%(name)s liked this","A %(name)s le gustó esto","singular"

    .. versionchanged:: 4.3
       Added ``encoding`` parameter. Added support for BOM-based encoding
       detection, UTF-16, and UTF-8-with-BOM.
    """
    global _translations
    global _supported_locales
    _translations = {}
    for path in os.listdir(directory):
        if not path.endswith(".csv"):
            continue
        locale, extension = path.split(".")
        if not re.match("[a-z]+(_[A-Z]+)?$", locale):
            gen_log.error(
                "Unrecognized locale %r (path: %s)",
                locale,
                os.path.join(directory, path),
            )
            continue
        full_path = os.path.join(directory, path)
        if encoding is None:
            # Try to autodetect encoding based on the BOM.
            with open(full_path, "rb") as bf:
                data = bf.read(len(codecs.BOM_UTF16_LE))
            if data in (codecs.BOM_UTF16_LE, codecs.BOM_UTF16_BE):
                encoding = "utf-16"
            else:
                # utf-8-sig is "utf-8 with optional BOM". It's discouraged
                # in most cases but is common with CSV files because Excel
                # cannot read utf-8 files without a BOM.
                encoding = "utf-8-sig"
        # python 3: csv.reader requires a file open in text mode.
        # Specify an encoding to avoid dependence on $LANG environment variable.
        with open(full_path, encoding=encoding) as f:
            _translations[locale] = {}
            for i, row in enumerate(csv.reader(f)):
                if not row or len(row) < 2:
                    continue
                row = [escape.to_unicode(c).strip() for c in row]
                english, translation = row[:2]
                if len(row) > 2:
                    plural = row[2] or "unknown"
                else:
                    plural = "unknown"
                if plural not in ("plural", "singular", "unknown"):
                    gen_log.error(
                        "Unrecognized plural indicator %r in %s line %d",
                        plural,
                        path,
                        i + 1,
                    )
                    continue
                _translations[locale].setdefault(plural, {})[english] = translation
    _supported_locales = frozenset(list(_translations.keys()) + [_default_locale])
    gen_log.debug("Supported locales: %s", sorted(_supported_locales))


def load_gettext_translations(directory: str, domain: str) -> None:
    """Loads translations from `gettext`'s locale tree

    Locale tree is similar to system's ``/usr/share/locale``, like::

        {directory}/{lang}/LC_MESSAGES/{domain}.mo

    Three steps are required to have your app translated:

    1. Generate POT translation file::

        xgettext --language=Python --keyword=_:1,2 -d mydomain file1.py file2.html etc

    2. Merge against existing POT file::

        msgmerge old.po mydomain.po > new.po

    3. Compile::

        msgfmt mydomain.po -o {directory}/pt_BR/LC_MESSAGES/mydomain.mo
    """
    global _translations
    global _supported_locales
    global _use_gettext
    _translations = {}

    for filename in glob.glob(
        os.path.join(directory, "*", "LC_MESSAGES", domain + ".mo")
    ):
        lang = os.path.basename(os.path.dirname(os.path.dirname(filename)))
        try:
            _translations[lang] = gettext.translation(
                domain, directory, languages=[lang]
            )
        except Exception as e:
            gen_log.error("Cannot load translation for '%s': %s", lang, str(e))
            continue
    _supported_locales = frozenset(list(_translations.keys()) + [_default_locale])
    _use_gettext = True
    gen_log.debug("Supported locales: %s", sorted(_supported_locales))


def get_supported_locales() -> Iterable[str]:
    """Returns a list of all the supported locale codes."""
    return _supported_locales


class Locale:
    """Object representing a locale.

    After calling one of `load_translations` or `load_gettext_translations`,
    call `get` or `get_closest` to get a Locale object.
    """

    _cache = {}  # type: Dict[str, Locale]

    @classmethod
    def get_closest(cls, *locale_codes: str) -> "Locale":
        """Returns the closest match for the given locale code."""
        for code in locale_codes:
            if not code:
                continue
            code = code.replace("-", "_")
            parts = code.split("_")
            if len(parts) > 2:
                continue
            elif len(parts) == 2:
                code = parts[0].lower() + "_" + parts[1].upper()
            if code in _supported_locales:
                return cls.get(code)
            if parts[0].lower() in _supported_locales:
                return cls.get(parts[0].lower())
        return cls.get(_default_locale)

    @classmethod
    def get(cls, code: str) -> "Locale":
        """Returns the Locale for the given locale code.

        If it is not supported, we raise an exception.
        """
        if code not in cls._cache:
            assert code in _supported_locales
            translations = _translations.get(code, None)
            if translations is None:
                locale = CSVLocale(code, {})  # type: Locale
            elif _use_gettext:
                locale = GettextLocale(code, translations)
            else:
                locale = CSVLocale(code, translations)
            cls._cache[code] = locale
        return cls._cache[code]

    def __init__(self, code: str) -> None:
        self.code = code
        self.name = LOCALE_NAMES.get(code, {}).get("name", "Unknown")
        self.rtl = False
        for prefix in ["fa", "ar", "he"]:
            if self.code.startswith(prefix):
                self.rtl = True
                break

        # Initialize strings for date formatting
        _ = self.translate
        self._months = [
            _("January"),
            _("February"),
            _("March"),
            _("April"),
            _("May"),
            _("June"),
            _("July"),
            _("August"),
            _("September"),
            _("October"),
            _("November"),
            _("December"),
        ]
        self._weekdays = [
            _("Monday"),
            _("Tuesday"),
            _("Wednesday"),
            _("Thursday"),
            _("Friday"),
            _("Saturday"),
            _("Sunday"),
        ]

    def translate(
        self,
        message: str,
        plural_message: Optional[str] = None,
        count: Optional[int] = None,
    ) -> str:
        """Returns the translation for the given message for this locale.

        If ``plural_message`` is given, you must also provide
        ``count``. We return ``plural_message`` when ``count != 1``,
        and we return the singular form for the given message when
        ``count == 1``.
        """
        raise NotImplementedError()

    def pgettext(
        self,
        context: str,
        message: str,
        plural_message: Optional[str] = None,
        count: Optional[int] = None,
    ) -> str:
        raise NotImplementedError()

    def format_date(
        self,
        date: Union[int, float, datetime.datetime],
        gmt_offset: int = 0,
        relative: bool = True,
        shorter: bool = False,
        full_format: bool = False,
    ) -> str:
        """Formats the given date.

        By default, we return a relative time (e.g., "2 minutes ago"). You
        can return an absolute date string with ``relative=False``.

        You can force a full format date ("July 10, 1980") with
        ``full_format=True``.

        This method is primarily intended for dates in the past.
        For dates in the future, we fall back to full format.

        .. versionchanged:: 6.4
           Aware `datetime.datetime` objects are now supported (naive
           datetimes are still assumed to be UTC).
        """
        if isinstance(date, (int, float)):
            date = datetime.datetime.fromtimestamp(date, datetime.timezone.utc)
        if date.tzinfo is None:
            date = date.replace(tzinfo=datetime.timezone.utc)
        now = datetime.datetime.now(datetime.timezone.utc)
        if date > now:
            if relative and (date - now).seconds < 60:
                # Due to click skew, things are some things slightly
                # in the future. Round timestamps in the immediate
                # future down to now in relative mode.
                date = now
            else:
                # Otherwise, future dates always use the full format.
                full_format = True
        local_date = date - datetime.timedelta(minutes=gmt_offset)
        local_now = now - datetime.timedelta(minutes=gmt_offset)
        local_yesterday = local_now - datetime.timedelta(hours=24)
        difference = now - date
        seconds = difference.seconds
        days = difference.days

        _ = self.translate
        format = None
        if not full_format:
            if relative and days == 0:
                if seconds < 50:
                    return _("1 second ago", "%(seconds)d seconds ago", seconds) % {
                        "seconds": seconds
                    }

                if seconds < 50 * 60:
                    minutes = round(seconds / 60.0)
                    return _("1 minute ago", "%(minutes)d minutes ago", minutes) % {
                        "minutes": minutes
                    }

                hours = round(seconds / (60.0 * 60))
                return _("1 hour ago", "%(hours)d hours ago", hours) % {"hours": hours}

            if days == 0:
                format = _("%(time)s")
            elif days == 1 and local_date.day == local_yesterday.day and relative:
                format = _("yesterday") if shorter else _("yesterday at %(time)s")
            elif days < 5:
                format = _("%(weekday)s") if shorter else _("%(weekday)s at %(time)s")
            elif days < 334:  # 11mo, since confusing for same month last year
                format = (
                    _("%(month_name)s %(day)s")
                    if shorter
                    else _("%(month_name)s %(day)s at %(time)s")
                )

        if format is None:
            format = (
                _("%(month_name)s %(day)s, %(year)s")
                if shorter
                else _("%(month_name)s %(day)s, %(year)s at %(time)s")
            )

        tfhour_clock = self.code not in ("en", "en_US", "zh_CN")
        if tfhour_clock:
            str_time = "%d:%02d" % (local_date.hour, local_date.minute)
        elif self.code == "zh_CN":
            str_time = "%s%d:%02d" % (
                ("\u4e0a\u5348", "\u4e0b\u5348")[local_date.hour >= 12],
                local_date.hour % 12 or 12,
                local_date.minute,
            )
        else:
            str_time = "%d:%02d %s" % (
                local_date.hour % 12 or 12,
                local_date.minute,
                ("am", "pm")[local_date.hour >= 12],
            )

        return format % {
            "month_name": self._months[local_date.month - 1],
            "weekday": self._weekdays[local_date.weekday()],
            "day": str(local_date.day),
            "year": str(local_date.year),
            "time": str_time,
        }

    def format_day(
        self, date: datetime.datetime, gmt_offset: int = 0, dow: bool = True
    ) -> bool:
        """Formats the given date as a day of week.

        Example: "Monday, January 22". You can remove the day of week with
        ``dow=False``.
        """
        local_date = date - datetime.timedelta(minutes=gmt_offset)
        _ = self.translate
        if dow:
            return _("%(weekday)s, %(month_name)s %(day)s") % {
                "month_name": self._months[local_date.month - 1],
                "weekday": self._weekdays[local_date.weekday()],
                "day": str(local_date.day),
            }
        else:
            return _("%(month_name)s %(day)s") % {
                "month_name": self._months[local_date.month - 1],
                "day": str(local_date.day),
            }

    def list(self, parts: Any) -> str:
        """Returns a comma-separated list for the given list of parts.

        The format is, e.g., "A, B and C", "A and B" or just "A" for lists
        of size 1.
        """
        _ = self.translate
        if len(parts) == 0:
            return ""
        if len(parts) == 1:
            return parts[0]
        comma = " \u0648 " if self.code.startswith("fa") else ", "
        return _("%(commas)s and %(last)s") % {
            "commas": comma.join(parts[:-1]),
            "last": parts[len(parts) - 1],
        }

    def friendly_number(self, value: int) -> str:
        """Returns a comma-separated number for the given integer."""
        if self.code not in ("en", "en_US"):
            return str(value)
        s = str(value)
        parts = []
        while s:
            parts.append(s[-3:])
            s = s[:-3]
        return ",".join(reversed(parts))


class CSVLocale(Locale):
    """Locale implementation using tornado's CSV translation format."""

    def __init__(self, code: str, translations: Dict[str, Dict[str, str]]) -> None:
        self.translations = translations
        super().__init__(code)

    def translate(
        self,
        message: str,
        plural_message: Optional[str] = None,
        count: Optional[int] = None,
    ) -> str:
        if plural_message is not None:
            assert count is not None
            if count != 1:
                message = plural_message
                message_dict = self.translations.get("plural", {})
            else:
                message_dict = self.translations.get("singular", {})
        else:
            message_dict = self.translations.get("unknown", {})
        return message_dict.get(message, message)

    def pgettext(
        self,
        context: str,
        message: str,
        plural_message: Optional[str] = None,
        count: Optional[int] = None,
    ) -> str:
        if self.translations:
            gen_log.warning("pgettext is not supported by CSVLocale")
        return self.translate(message, plural_message, count)


class GettextLocale(Locale):
    """Locale implementation using the `gettext` module."""

    def __init__(self, code: str, translations: gettext.NullTranslations) -> None:
        self.ngettext = translations.ngettext
        self.gettext = translations.gettext
        # self.gettext must exist before __init__ is called, since it
        # calls into self.translate
        super().__init__(code)

    def translate(
        self,
        message: str,
        plural_message: Optional[str] = None,
        count: Optional[int] = None,
    ) -> str:
        if plural_message is not None:
            assert count is not None
            return self.ngettext(message, plural_message, count)
        else:
            return self.gettext(message)

    def pgettext(
        self,
        context: str,
        message: str,
        plural_message: Optional[str] = None,
        count: Optional[int] = None,
    ) -> str:
        """Allows to set context for translation, accepts plural forms.

        Usage example::

            pgettext("law", "right")
            pgettext("good", "right")

        Plural message example::

            pgettext("organization", "club", "clubs", len(clubs))
            pgettext("stick", "club", "clubs", len(clubs))

        To generate POT file with context, add following options to step 1
        of `load_gettext_translations` sequence::

            xgettext [basic options] --keyword=pgettext:1c,2 --keyword=pgettext:1c,2,3

        .. versionadded:: 4.2
        """
        if plural_message is not None:
            assert count is not None
            msgs_with_ctxt = (
                f"{context}{CONTEXT_SEPARATOR}{message}",
                f"{context}{CONTEXT_SEPARATOR}{plural_message}",
                count,
            )
            result = self.ngettext(*msgs_with_ctxt)
            if CONTEXT_SEPARATOR in result:
                # Translation not found
                result = self.ngettext(message, plural_message, count)
            return result
        else:
            msg_with_ctxt = f"{context}{CONTEXT_SEPARATOR}{message}"
            result = self.gettext(msg_with_ctxt)
            if CONTEXT_SEPARATOR in result:
                # Translation not found
                result = message
            return result

# === NexusCore/openenv\Lib\site-packages\typing_inspection\introspection.py ===
"""High-level introspection utilities, used to inspect type annotations."""

from __future__ import annotations

import sys
import types
from collections.abc import Generator
from dataclasses import InitVar
from enum import Enum, IntEnum, auto
from typing import Any, Literal, NamedTuple, cast

from typing_extensions import TypeAlias, assert_never, get_args, get_origin

from . import typing_objects

__all__ = (
    'AnnotationSource',
    'ForbiddenQualifier',
    'InspectedAnnotation',
    'Qualifier',
    'get_literal_values',
    'inspect_annotation',
    'is_union_origin',
)

if sys.version_info >= (3, 14) or sys.version_info < (3, 10):

    def is_union_origin(obj: Any, /) -> bool:
        """Return whether the provided origin is the union form.

        ```pycon
        >>> is_union_origin(typing.Union)
        True
        >>> is_union_origin(get_origin(int | str))
        True
        >>> is_union_origin(types.UnionType)
        True
        ```

        !!! note
            Since Python 3.14, both `Union[<t1>, <t2>, ...]` and `<t1> | <t2> | ...` forms create instances
            of the same [`typing.Union`][] class. As such, it is recommended to not use this function
            anymore (provided that you only support Python 3.14 or greater), and instead use the
            [`typing_objects.is_union()`][typing_inspection.typing_objects.is_union] function directly:

            ```python
            from typing import Union, get_origin

            from typing_inspection import typing_objects

            typ = int | str  # Or Union[int, str]
            origin = get_origin(typ)
            if typing_objects.is_union(origin):
                ...
            ```
        """
        return typing_objects.is_union(obj)


else:

    def is_union_origin(obj: Any, /) -> bool:
        """Return whether the provided origin is the union form.

        ```pycon
        >>> is_union_origin(typing.Union)
        True
        >>> is_union_origin(get_origin(int | str))
        True
        >>> is_union_origin(types.UnionType)
        True
        ```

        !!! note
            Since Python 3.14, both `Union[<t1>, <t2>, ...]` and `<t1> | <t2> | ...` forms create instances
            of the same [`typing.Union`][] class. As such, it is recommended to not use this function
            anymore (provided that you only support Python 3.14 or greater), and instead use the
            [`typing_objects.is_union()`][typing_inspection.typing_objects.is_union] function directly:

            ```python
            from typing import Union, get_origin

            from typing_inspection import typing_objects

            typ = int | str  # Or Union[int, str]
            origin = get_origin(typ)
            if typing_objects.is_union(origin):
                ...
            ```
        """
        return typing_objects.is_union(obj) or obj is types.UnionType


def _literal_type_check(value: Any, /) -> None:
    """Type check the provided literal value against the legal parameters."""
    if (
        not isinstance(value, (int, bytes, str, bool, Enum, typing_objects.NoneType))
        and value is not typing_objects.NoneType
    ):
        raise TypeError(f'{value} is not a valid literal value, must be one of: int, bytes, str, Enum, None.')


def get_literal_values(
    annotation: Any,
    /,
    *,
    type_check: bool = False,
    unpack_type_aliases: Literal['skip', 'lenient', 'eager'] = 'eager',
) -> Generator[Any]:
    """Yield the values contained in the provided [`Literal`][typing.Literal] [special form][].

    Args:
        annotation: The [`Literal`][typing.Literal] [special form][] to unpack.
        type_check: Whether to check if the literal values are [legal parameters][literal-legal-parameters].
            Raises a [`TypeError`][] otherwise.
        unpack_type_aliases: What to do when encountering [PEP 695](https://peps.python.org/pep-0695/)
            [type aliases][type-aliases]. Can be one of:

            - `'skip'`: Do not try to parse type aliases. Note that this can lead to incorrect results:
              ```pycon
              >>> type MyAlias = Literal[1, 2]
              >>> list(get_literal_values(Literal[MyAlias, 3], unpack_type_aliases="skip"))
              [MyAlias, 3]
              ```

            - `'lenient'`: Try to parse type aliases, and fallback to `'skip'` if the type alias can't be inspected
              (because of an undefined forward reference).

            - `'eager'`: Parse type aliases and raise any encountered [`NameError`][] exceptions (the default):
              ```pycon
              >>> type MyAlias = Literal[1, 2]
              >>> list(get_literal_values(Literal[MyAlias, 3], unpack_type_aliases="eager"))
              [1, 2, 3]
              ```

    Note:
        While `None` is [equivalent to][none] `type(None)`, the runtime implementation of [`Literal`][typing.Literal]
        does not de-duplicate them. This function makes sure this de-duplication is applied:

        ```pycon
        >>> list(get_literal_values(Literal[NoneType, None]))
        [None]
        ```

    Example:
        ```pycon
        >>> type Ints = Literal[1, 2]
        >>> list(get_literal_values(Literal[1, Ints], unpack_type_alias="skip"))
        ["a", Ints]
        >>> list(get_literal_values(Literal[1, Ints]))
        [1, 2]
        >>> list(get_literal_values(Literal[1.0], type_check=True))
        Traceback (most recent call last):
        ...
        TypeError: 1.0 is not a valid literal value, must be one of: int, bytes, str, Enum, None.
        ```
    """
    # `literal` is guaranteed to be a `Literal[...]` special form, so use
    # `__args__` directly instead of calling `get_args()`.

    if unpack_type_aliases == 'skip':
        _has_none = False
        # `Literal` parameters are already deduplicated, no need to do it ourselves.
        # (we only check for `None` and `NoneType`, which should be considered as duplicates).
        for arg in annotation.__args__:
            if type_check:
                _literal_type_check(arg)
            if arg is None or arg is typing_objects.NoneType:
                if not _has_none:
                    yield None
                _has_none = True
            else:
                yield arg
    else:
        # We'll need to manually deduplicate parameters, see the `Literal` implementation in `typing`.
        values_and_type: list[tuple[Any, type[Any]]] = []

        for arg in annotation.__args__:
            # Note: we could also check for generic aliases with a type alias as an origin.
            # However, it is very unlikely that this happens as type variables can't appear in
            # `Literal` forms, so the only valid (but unnecessary) use case would be something like:
            # `type Test[T] = Literal['a']` (and then use `Test[SomeType]`).
            if typing_objects.is_typealiastype(arg):
                try:
                    alias_value = arg.__value__
                except NameError:
                    if unpack_type_aliases == 'eager':
                        raise
                    # unpack_type_aliases == "lenient":
                    if type_check:
                        _literal_type_check(arg)
                    values_and_type.append((arg, type(arg)))
                else:
                    sub_args = get_literal_values(
                        alias_value, type_check=type_check, unpack_type_aliases=unpack_type_aliases
                    )
                    values_and_type.extend((a, type(a)) for a in sub_args)  # pyright: ignore[reportUnknownArgumentType]
            else:
                if type_check:
                    _literal_type_check(arg)
                if arg is typing_objects.NoneType:
                    values_and_type.append((None, typing_objects.NoneType))
                else:
                    values_and_type.append((arg, type(arg)))  # pyright: ignore[reportUnknownArgumentType]

        try:
            dct = dict.fromkeys(values_and_type)
        except TypeError:
            # Unhashable parameters, the Python implementation allows them
            yield from (p for p, _ in values_and_type)
        else:
            yield from (p for p, _ in dct)


Qualifier: TypeAlias = Literal['required', 'not_required', 'read_only', 'class_var', 'init_var', 'final']
"""A [type qualifier][]."""

_all_qualifiers: set[Qualifier] = set(get_args(Qualifier))


# TODO at some point, we could switch to an enum flag, so that multiple sources
# can be combined. However, is there a need for this?
class AnnotationSource(IntEnum):
    # TODO if/when https://peps.python.org/pep-0767/ is accepted, add 'read_only'
    # to CLASS and NAMED_TUPLE (even though for named tuples it is redundant).

    """The source of an annotation, e.g. a class or a function.

    Depending on the source, different [type qualifiers][type qualifier] may be (dis)allowed.
    """

    ASSIGNMENT_OR_VARIABLE = auto()
    """An annotation used in an assignment or variable annotation:

    ```python
    x: Final[int] = 1
    y: Final[str]
    ```

    **Allowed type qualifiers:** [`Final`][typing.Final].
    """

    CLASS = auto()
    """An annotation used in the body of a class:

    ```python
    class Test:
        x: Final[int] = 1
        y: ClassVar[str]
    ```

    **Allowed type qualifiers:** [`ClassVar`][typing.ClassVar], [`Final`][typing.Final].
    """

    DATACLASS = auto()
    """An annotation used in the body of a dataclass:

    ```python
    @dataclass
    class Test:
        x: Final[int] = 1
        y: InitVar[str] = 'test'
    ```

    **Allowed type qualifiers:** [`ClassVar`][typing.ClassVar], [`Final`][typing.Final], [`InitVar`][dataclasses.InitVar].
    """  # noqa: E501

    TYPED_DICT = auto()
    """An annotation used in the body of a [`TypedDict`][typing.TypedDict]:

    ```python
    class TD(TypedDict):
        x: Required[ReadOnly[int]]
        y: ReadOnly[NotRequired[str]]
    ```

    **Allowed type qualifiers:** [`ReadOnly`][typing.ReadOnly], [`Required`][typing.Required],
    [`NotRequired`][typing.NotRequired].
    """

    NAMED_TUPLE = auto()
    """An annotation used in the body of a [`NamedTuple`][typing.NamedTuple].

    ```python
    class NT(NamedTuple):
        x: int
        y: str
    ```

    **Allowed type qualifiers:** none.
    """

    FUNCTION = auto()
    """An annotation used in a function, either for a parameter or the return value.

    ```python
    def func(a: int) -> str:
        ...
    ```

    **Allowed type qualifiers:** none.
    """

    ANY = auto()
    """An annotation that might come from any source.

    **Allowed type qualifiers:** all.
    """

    BARE = auto()
    """An annotation that is inspected as is.

    **Allowed type qualifiers:** none.
    """

    @property
    def allowed_qualifiers(self) -> set[Qualifier]:
        """The allowed [type qualifiers][type qualifier] for this annotation source."""
        # TODO use a match statement when Python 3.9 support is dropped.
        if self is AnnotationSource.ASSIGNMENT_OR_VARIABLE:
            return {'final'}
        elif self is AnnotationSource.CLASS:
            return {'final', 'class_var'}
        elif self is AnnotationSource.DATACLASS:
            return {'final', 'class_var', 'init_var'}
        elif self is AnnotationSource.TYPED_DICT:
            return {'required', 'not_required', 'read_only'}
        elif self in (AnnotationSource.NAMED_TUPLE, AnnotationSource.FUNCTION, AnnotationSource.BARE):
            return set()
        elif self is AnnotationSource.ANY:
            return _all_qualifiers
        else:  # pragma: no cover
            assert_never(self)


class ForbiddenQualifier(Exception):
    """The provided [type qualifier][] is forbidden."""

    qualifier: Qualifier
    """The forbidden qualifier."""

    def __init__(self, qualifier: Qualifier, /) -> None:
        self.qualifier = qualifier


class _UnknownTypeEnum(Enum):
    UNKNOWN = auto()

    def __str__(self) -> str:
        return 'UNKNOWN'

    def __repr__(self) -> str:
        return '<UNKNOWN>'


UNKNOWN = _UnknownTypeEnum.UNKNOWN
"""A sentinel value used when no [type expression][] is present."""

_UnkownType: TypeAlias = Literal[_UnknownTypeEnum.UNKNOWN]
"""The type of the [`UNKNOWN`][typing_inspection.introspection.UNKNOWN] sentinel value."""


class InspectedAnnotation(NamedTuple):
    """The result of the inspected annotation."""

    type: Any | _UnkownType
    """The final [type expression][], with [type qualifiers][type qualifier] and annotated metadata stripped.

    If no type expression is available, the [`UNKNOWN`][typing_inspection.introspection.UNKNOWN] sentinel
    value is used instead. This is the case when a [type qualifier][] is used with no type annotation:

    ```python
    ID: Final = 1

    class C:
        x: ClassVar = 'test'
    ```
    """

    qualifiers: set[Qualifier]
    """The [type qualifiers][type qualifier] present on the annotation."""

    metadata: list[Any]
    """The annotated metadata."""


def inspect_annotation(  # noqa: PLR0915
    annotation: Any,
    /,
    *,
    annotation_source: AnnotationSource,
    unpack_type_aliases: Literal['skip', 'lenient', 'eager'] = 'skip',
) -> InspectedAnnotation:
    """Inspect an [annotation expression][], extracting any [type qualifier][] and metadata.

    An [annotation expression][] is a [type expression][] optionally surrounded by one or more
    [type qualifiers][type qualifier] or by [`Annotated`][typing.Annotated]. This function will:

    - Unwrap the type expression, keeping track of the type qualifiers.
    - Unwrap [`Annotated`][typing.Annotated] forms, keeping track of the annotated metadata.

    Args:
        annotation: The annotation expression to be inspected.
        annotation_source: The source of the annotation. Depending on the source (e.g. a class), different type
            qualifiers may be (dis)allowed. To allow any type qualifier, use
            [`AnnotationSource.ANY`][typing_inspection.introspection.AnnotationSource.ANY].
        unpack_type_aliases: What to do when encountering [PEP 695](https://peps.python.org/pep-0695/)
            [type aliases][type-aliases]. Can be one of:

            - `'skip'`: Do not try to parse type aliases (the default):
              ```pycon
              >>> type MyInt = Annotated[int, 'meta']
              >>> inspect_annotation(MyInt, annotation_source=AnnotationSource.BARE, unpack_type_aliases='skip')
              InspectedAnnotation(type=MyInt, qualifiers={}, metadata=[])
              ```

            - `'lenient'`: Try to parse type aliases, and fallback to `'skip'` if the type alias
              can't be inspected (because of an undefined forward reference):
              ```pycon
              >>> type MyInt = Annotated[Undefined, 'meta']
              >>> inspect_annotation(MyInt, annotation_source=AnnotationSource.BARE, unpack_type_aliases='lenient')
              InspectedAnnotation(type=MyInt, qualifiers={}, metadata=[])
              >>> Undefined = int
              >>> inspect_annotation(MyInt, annotation_source=AnnotationSource.BARE, unpack_type_aliases='lenient')
              InspectedAnnotation(type=int, qualifiers={}, metadata=['meta'])
              ```

            - `'eager'`: Parse type aliases and raise any encountered [`NameError`][] exceptions.

    Returns:
        The result of the inspected annotation, where the type expression, used qualifiers and metadata is stored.

    Example:
        ```pycon
        >>> inspect_annotation(
        ...     Final[Annotated[ClassVar[Annotated[int, 'meta_1']], 'meta_2']],
        ...     annotation_source=AnnotationSource.CLASS,
        ... )
        ...
        InspectedAnnotation(type=int, qualifiers={'class_var', 'final'}, metadata=['meta_1', 'meta_2'])
        ```
    """
    allowed_qualifiers = annotation_source.allowed_qualifiers
    qualifiers: set[Qualifier] = set()
    metadata: list[Any] = []

    while True:
        annotation, _meta = _unpack_annotated(annotation, unpack_type_aliases=unpack_type_aliases)
        if _meta:
            metadata = _meta + metadata
            continue

        origin = get_origin(annotation)
        if origin is not None:
            if typing_objects.is_classvar(origin):
                if 'class_var' not in allowed_qualifiers:
                    raise ForbiddenQualifier('class_var')
                qualifiers.add('class_var')
                annotation = annotation.__args__[0]
            elif typing_objects.is_final(origin):
                if 'final' not in allowed_qualifiers:
                    raise ForbiddenQualifier('final')
                qualifiers.add('final')
                annotation = annotation.__args__[0]
            elif typing_objects.is_required(origin):
                if 'required' not in allowed_qualifiers:
                    raise ForbiddenQualifier('required')
                qualifiers.add('required')
                annotation = annotation.__args__[0]
            elif typing_objects.is_notrequired(origin):
                if 'not_required' not in allowed_qualifiers:
                    raise ForbiddenQualifier('not_required')
                qualifiers.add('not_required')
                annotation = annotation.__args__[0]
            elif typing_objects.is_readonly(origin):
                if 'read_only' not in allowed_qualifiers:
                    raise ForbiddenQualifier('not_required')
                qualifiers.add('read_only')
                annotation = annotation.__args__[0]
            else:
                # origin is not None but not a type qualifier nor `Annotated` (e.g. `list[int]`):
                break
        elif isinstance(annotation, InitVar):
            if 'init_var' not in allowed_qualifiers:
                raise ForbiddenQualifier('init_var')
            qualifiers.add('init_var')
            annotation = cast(Any, annotation.type)
        else:
            break

    # `Final`, `ClassVar` and `InitVar` are type qualifiers allowed to be used as a bare annotation:
    if typing_objects.is_final(annotation):
        if 'final' not in allowed_qualifiers:
            raise ForbiddenQualifier('final')
        qualifiers.add('final')
        annotation = UNKNOWN
    elif typing_objects.is_classvar(annotation):
        if 'class_var' not in allowed_qualifiers:
            raise ForbiddenQualifier('class_var')
        qualifiers.add('class_var')
        annotation = UNKNOWN
    elif annotation is InitVar:
        if 'init_var' not in allowed_qualifiers:
            raise ForbiddenQualifier('init_var')
        qualifiers.add('init_var')
        annotation = UNKNOWN

    return InspectedAnnotation(annotation, qualifiers, metadata)


def _unpack_annotated_inner(
    annotation: Any, unpack_type_aliases: Literal['lenient', 'eager'], check_annotated: bool
) -> tuple[Any, list[Any]]:
    origin = get_origin(annotation)
    if check_annotated and typing_objects.is_annotated(origin):
        annotated_type = annotation.__origin__
        metadata = list(annotation.__metadata__)

        # The annotated type might be a PEP 695 type alias, so we need to recursively
        # unpack it. Because Python already flattens `Annotated[Annotated[<type>, ...], ...]` forms,
        # we can skip the `is_annotated()` check in the next call:
        annotated_type, sub_meta = _unpack_annotated_inner(
            annotated_type, unpack_type_aliases=unpack_type_aliases, check_annotated=False
        )
        metadata = sub_meta + metadata
        return annotated_type, metadata
    elif typing_objects.is_typealiastype(annotation):
        try:
            value = annotation.__value__
        except NameError:
            if unpack_type_aliases == 'eager':
                raise
        else:
            typ, metadata = _unpack_annotated_inner(
                value, unpack_type_aliases=unpack_type_aliases, check_annotated=True
            )
            if metadata:
                # Having metadata means the type alias' `__value__` was an `Annotated` form
                # (or, recursively, a type alias to an `Annotated` form). It is important to check
                # for this, as we don't want to unpack other type aliases (e.g. `type MyInt = int`).
                return typ, metadata
            return annotation, []
    elif typing_objects.is_typealiastype(origin):
        # When parameterized, PEP 695 type aliases become generic aliases
        # (e.g. with `type MyList[T] = Annotated[list[T], ...]`, `MyList[int]`
        # is a generic alias).
        try:
            value = origin.__value__
        except NameError:
            if unpack_type_aliases == 'eager':
                raise
        else:
            # While Python already handles type variable replacement for simple `Annotated` forms,
            # we need to manually apply the same logic for PEP 695 type aliases:
            # - With `MyList = Annotated[list[T], ...]`, `MyList[int] == Annotated[list[int], ...]`
            # - With `type MyList[T] = Annotated[list[T], ...]`, `MyList[int].__value__ == Annotated[list[T], ...]`.

            try:
                # To do so, we emulate the parameterization of the value with the arguments:
                # with `type MyList[T] = Annotated[list[T], ...]`, to emulate `MyList[int]`,
                # we do `Annotated[list[T], ...][int]` (which gives `Annotated[list[T], ...]`):
                value = value[annotation.__args__]
            except TypeError:
                # Might happen if the type alias is parameterized, but its value doesn't have any
                # type variables, e.g. `type MyInt[T] = int`.
                pass
            typ, metadata = _unpack_annotated_inner(
                value, unpack_type_aliases=unpack_type_aliases, check_annotated=True
            )
            if metadata:
                return typ, metadata
            return annotation, []

    return annotation, []


# This could eventually be made public:
def _unpack_annotated(
    annotation: Any, /, *, unpack_type_aliases: Literal['skip', 'lenient', 'eager'] = 'eager'
) -> tuple[Any, list[Any]]:
    if unpack_type_aliases == 'skip':
        if typing_objects.is_annotated(get_origin(annotation)):
            return annotation.__origin__, list(annotation.__metadata__)
        else:
            return annotation, []

    return _unpack_annotated_inner(annotation, unpack_type_aliases=unpack_type_aliases, check_annotated=True)