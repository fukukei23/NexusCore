
# === NexusCore/openenv\Lib\site-packages\rich\live.py ===
import sys
from threading import Event, RLock, Thread
from types import TracebackType
from typing import IO, Any, Callable, List, Optional, TextIO, Type, cast

from . import get_console
from .console import Console, ConsoleRenderable, RenderableType, RenderHook
from .control import Control
from .file_proxy import FileProxy
from .jupyter import JupyterMixin
from .live_render import LiveRender, VerticalOverflowMethod
from .screen import Screen
from .text import Text


class _RefreshThread(Thread):
    """A thread that calls refresh() at regular intervals."""

    def __init__(self, live: "Live", refresh_per_second: float) -> None:
        self.live = live
        self.refresh_per_second = refresh_per_second
        self.done = Event()
        super().__init__(daemon=True)

    def stop(self) -> None:
        self.done.set()

    def run(self) -> None:
        while not self.done.wait(1 / self.refresh_per_second):
            with self.live._lock:
                if not self.done.is_set():
                    self.live.refresh()


class Live(JupyterMixin, RenderHook):
    """Renders an auto-updating live display of any given renderable.

    Args:
        renderable (RenderableType, optional): The renderable to live display. Defaults to displaying nothing.
        console (Console, optional): Optional Console instance. Defaults to an internal Console instance writing to stdout.
        screen (bool, optional): Enable alternate screen mode. Defaults to False.
        auto_refresh (bool, optional): Enable auto refresh. If disabled, you will need to call `refresh()` or `update()` with refresh flag. Defaults to True
        refresh_per_second (float, optional): Number of times per second to refresh the live display. Defaults to 4.
        transient (bool, optional): Clear the renderable on exit (has no effect when screen=True). Defaults to False.
        redirect_stdout (bool, optional): Enable redirection of stdout, so ``print`` may be used. Defaults to True.
        redirect_stderr (bool, optional): Enable redirection of stderr. Defaults to True.
        vertical_overflow (VerticalOverflowMethod, optional): How to handle renderable when it is too tall for the console. Defaults to "ellipsis".
        get_renderable (Callable[[], RenderableType], optional): Optional callable to get renderable. Defaults to None.
    """

    def __init__(
        self,
        renderable: Optional[RenderableType] = None,
        *,
        console: Optional[Console] = None,
        screen: bool = False,
        auto_refresh: bool = True,
        refresh_per_second: float = 4,
        transient: bool = False,
        redirect_stdout: bool = True,
        redirect_stderr: bool = True,
        vertical_overflow: VerticalOverflowMethod = "ellipsis",
        get_renderable: Optional[Callable[[], RenderableType]] = None,
    ) -> None:
        assert refresh_per_second > 0, "refresh_per_second must be > 0"
        self._renderable = renderable
        self.console = console if console is not None else get_console()
        self._screen = screen
        self._alt_screen = False

        self._redirect_stdout = redirect_stdout
        self._redirect_stderr = redirect_stderr
        self._restore_stdout: Optional[IO[str]] = None
        self._restore_stderr: Optional[IO[str]] = None

        self._lock = RLock()
        self.ipy_widget: Optional[Any] = None
        self.auto_refresh = auto_refresh
        self._started: bool = False
        self.transient = True if screen else transient

        self._refresh_thread: Optional[_RefreshThread] = None
        self.refresh_per_second = refresh_per_second

        self.vertical_overflow = vertical_overflow
        self._get_renderable = get_renderable
        self._live_render = LiveRender(
            self.get_renderable(), vertical_overflow=vertical_overflow
        )

    @property
    def is_started(self) -> bool:
        """Check if live display has been started."""
        return self._started

    def get_renderable(self) -> RenderableType:
        renderable = (
            self._get_renderable()
            if self._get_renderable is not None
            else self._renderable
        )
        return renderable or ""

    def start(self, refresh: bool = False) -> None:
        """Start live rendering display.

        Args:
            refresh (bool, optional): Also refresh. Defaults to False.
        """
        with self._lock:
            if self._started:
                return
            self.console.set_live(self)
            self._started = True
            if self._screen:
                self._alt_screen = self.console.set_alt_screen(True)
            self.console.show_cursor(False)
            self._enable_redirect_io()
            self.console.push_render_hook(self)
            if refresh:
                try:
                    self.refresh()
                except Exception:
                    # If refresh fails, we want to stop the redirection of sys.stderr,
                    # so the error stacktrace is properly displayed in the terminal.
                    # (or, if the code that calls Rich captures the exception and wants to display something,
                    # let this be displayed in the terminal).
                    self.stop()
                    raise
            if self.auto_refresh:
                self._refresh_thread = _RefreshThread(self, self.refresh_per_second)
                self._refresh_thread.start()

    def stop(self) -> None:
        """Stop live rendering display."""
        with self._lock:
            if not self._started:
                return
            self.console.clear_live()
            self._started = False

            if self.auto_refresh and self._refresh_thread is not None:
                self._refresh_thread.stop()
                self._refresh_thread = None
            # allow it to fully render on the last even if overflow
            self.vertical_overflow = "visible"
            with self.console:
                try:
                    if not self._alt_screen and not self.console.is_jupyter:
                        self.refresh()
                finally:
                    self._disable_redirect_io()
                    self.console.pop_render_hook()
                    if not self._alt_screen and self.console.is_terminal:
                        self.console.line()
                    self.console.show_cursor(True)
                    if self._alt_screen:
                        self.console.set_alt_screen(False)

                    if self.transient and not self._alt_screen:
                        self.console.control(self._live_render.restore_cursor())
                    if self.ipy_widget is not None and self.transient:
                        self.ipy_widget.close()  # pragma: no cover

    def __enter__(self) -> "Live":
        self.start(refresh=self._renderable is not None)
        return self

    def __exit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[TracebackType],
    ) -> None:
        self.stop()

    def _enable_redirect_io(self) -> None:
        """Enable redirecting of stdout / stderr."""
        if self.console.is_terminal or self.console.is_jupyter:
            if self._redirect_stdout and not isinstance(sys.stdout, FileProxy):
                self._restore_stdout = sys.stdout
                sys.stdout = cast("TextIO", FileProxy(self.console, sys.stdout))
            if self._redirect_stderr and not isinstance(sys.stderr, FileProxy):
                self._restore_stderr = sys.stderr
                sys.stderr = cast("TextIO", FileProxy(self.console, sys.stderr))

    def _disable_redirect_io(self) -> None:
        """Disable redirecting of stdout / stderr."""
        if self._restore_stdout:
            sys.stdout = cast("TextIO", self._restore_stdout)
            self._restore_stdout = None
        if self._restore_stderr:
            sys.stderr = cast("TextIO", self._restore_stderr)
            self._restore_stderr = None

    @property
    def renderable(self) -> RenderableType:
        """Get the renderable that is being displayed

        Returns:
            RenderableType: Displayed renderable.
        """
        renderable = self.get_renderable()
        return Screen(renderable) if self._alt_screen else renderable

    def update(self, renderable: RenderableType, *, refresh: bool = False) -> None:
        """Update the renderable that is being displayed

        Args:
            renderable (RenderableType): New renderable to use.
            refresh (bool, optional): Refresh the display. Defaults to False.
        """
        if isinstance(renderable, str):
            renderable = self.console.render_str(renderable)
        with self._lock:
            self._renderable = renderable
            if refresh:
                self.refresh()

    def refresh(self) -> None:
        """Update the display of the Live Render."""
        with self._lock:
            self._live_render.set_renderable(self.renderable)
            if self.console.is_jupyter:  # pragma: no cover
                try:
                    from IPython.display import display
                    from ipywidgets import Output
                except ImportError:
                    import warnings

                    warnings.warn('install "ipywidgets" for Jupyter support')
                else:
                    if self.ipy_widget is None:
                        self.ipy_widget = Output()
                        display(self.ipy_widget)

                    with self.ipy_widget:
                        self.ipy_widget.clear_output(wait=True)
                        self.console.print(self._live_render.renderable)
            elif self.console.is_terminal and not self.console.is_dumb_terminal:
                with self.console:
                    self.console.print(Control())
            elif (
                not self._started and not self.transient
            ):  # if it is finished allow files or dumb-terminals to see final result
                with self.console:
                    self.console.print(Control())

    def process_renderables(
        self, renderables: List[ConsoleRenderable]
    ) -> List[ConsoleRenderable]:
        """Process renderables to restore cursor and display progress."""
        self._live_render.vertical_overflow = self.vertical_overflow
        if self.console.is_interactive:
            # lock needs acquiring as user can modify live_render renderable at any time unlike in Progress.
            with self._lock:
                reset = (
                    Control.home()
                    if self._alt_screen
                    else self._live_render.position_cursor()
                )
                renderables = [reset, *renderables, self._live_render]
        elif (
            not self._started and not self.transient
        ):  # if it is finished render the final output for files or dumb_terminals
            renderables = [*renderables, self._live_render]

        return renderables


if __name__ == "__main__":  # pragma: no cover
    import random
    import time
    from itertools import cycle
    from typing import Dict, List, Tuple

    from .align import Align
    from .console import Console
    from .live import Live as Live
    from .panel import Panel
    from .rule import Rule
    from .syntax import Syntax
    from .table import Table

    console = Console()

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
        "You can make the terminal shorter and taller to see the live table hide"
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

    examples = cycle(progress_renderables)

    exchanges = [
        "SGD",
        "MYR",
        "EUR",
        "USD",
        "AUD",
        "JPY",
        "CNH",
        "HKD",
        "CAD",
        "INR",
        "DKK",
        "GBP",
        "RUB",
        "NZD",
        "MXN",
        "IDR",
        "TWD",
        "THB",
        "VND",
    ]
    with Live(console=console) as live_table:
        exchange_rate_dict: Dict[Tuple[str, str], float] = {}

        for index in range(100):
            select_exchange = exchanges[index % len(exchanges)]

            for exchange in exchanges:
                if exchange == select_exchange:
                    continue
                time.sleep(0.4)
                if random.randint(0, 10) < 1:
                    console.log(next(examples))
                exchange_rate_dict[(select_exchange, exchange)] = 200 / (
                    (random.random() * 320) + 1
                )
                if len(exchange_rate_dict) > len(exchanges) - 1:
                    exchange_rate_dict.pop(list(exchange_rate_dict.keys())[0])
                table = Table(title="Exchange Rates")

                table.add_column("Source Currency")
                table.add_column("Destination Currency")
                table.add_column("Exchange Rate")

                for (source, dest), exchange_rate in exchange_rate_dict.items():
                    table.add_row(
                        source,
                        dest,
                        Text(
                            f"{exchange_rate:.4f}",
                            style="red" if exchange_rate < 1.0 else "green",
                        ),
                    )

                live_table.update(Align.center(table))

# === NexusCore/openenv\Lib\site-packages\pip\_internal\commands\list.py ===
import json
import logging
from optparse import Values
from typing import TYPE_CHECKING, Generator, List, Optional, Sequence, Tuple, cast

from pip._vendor.packaging.utils import canonicalize_name
from pip._vendor.packaging.version import Version

from pip._internal.cli import cmdoptions
from pip._internal.cli.index_command import IndexGroupCommand
from pip._internal.cli.status_codes import SUCCESS
from pip._internal.exceptions import CommandError
from pip._internal.metadata import BaseDistribution, get_environment
from pip._internal.models.selection_prefs import SelectionPreferences
from pip._internal.utils.compat import stdlib_pkgs
from pip._internal.utils.misc import tabulate, write_output

if TYPE_CHECKING:
    from pip._internal.index.package_finder import PackageFinder
    from pip._internal.network.session import PipSession

    class _DistWithLatestInfo(BaseDistribution):
        """Give the distribution object a couple of extra fields.

        These will be populated during ``get_outdated()``. This is dirty but
        makes the rest of the code much cleaner.
        """

        latest_version: Version
        latest_filetype: str

    _ProcessedDists = Sequence[_DistWithLatestInfo]


logger = logging.getLogger(__name__)


class ListCommand(IndexGroupCommand):
    """
    List installed packages, including editables.

    Packages are listed in a case-insensitive sorted order.
    """

    ignore_require_venv = True
    usage = """
      %prog [options]"""

    def add_options(self) -> None:
        self.cmd_opts.add_option(
            "-o",
            "--outdated",
            action="store_true",
            default=False,
            help="List outdated packages",
        )
        self.cmd_opts.add_option(
            "-u",
            "--uptodate",
            action="store_true",
            default=False,
            help="List uptodate packages",
        )
        self.cmd_opts.add_option(
            "-e",
            "--editable",
            action="store_true",
            default=False,
            help="List editable projects.",
        )
        self.cmd_opts.add_option(
            "-l",
            "--local",
            action="store_true",
            default=False,
            help=(
                "If in a virtualenv that has global access, do not list "
                "globally-installed packages."
            ),
        )
        self.cmd_opts.add_option(
            "--user",
            dest="user",
            action="store_true",
            default=False,
            help="Only output packages installed in user-site.",
        )
        self.cmd_opts.add_option(cmdoptions.list_path())
        self.cmd_opts.add_option(
            "--pre",
            action="store_true",
            default=False,
            help=(
                "Include pre-release and development versions. By default, "
                "pip only finds stable versions."
            ),
        )

        self.cmd_opts.add_option(
            "--format",
            action="store",
            dest="list_format",
            default="columns",
            choices=("columns", "freeze", "json"),
            help=(
                "Select the output format among: columns (default), freeze, or json. "
                "The 'freeze' format cannot be used with the --outdated option."
            ),
        )

        self.cmd_opts.add_option(
            "--not-required",
            action="store_true",
            dest="not_required",
            help="List packages that are not dependencies of installed packages.",
        )

        self.cmd_opts.add_option(
            "--exclude-editable",
            action="store_false",
            dest="include_editable",
            help="Exclude editable package from output.",
        )
        self.cmd_opts.add_option(
            "--include-editable",
            action="store_true",
            dest="include_editable",
            help="Include editable package from output.",
            default=True,
        )
        self.cmd_opts.add_option(cmdoptions.list_exclude())
        index_opts = cmdoptions.make_option_group(cmdoptions.index_group, self.parser)

        self.parser.insert_option_group(0, index_opts)
        self.parser.insert_option_group(0, self.cmd_opts)

    def handle_pip_version_check(self, options: Values) -> None:
        if options.outdated or options.uptodate:
            super().handle_pip_version_check(options)

    def _build_package_finder(
        self, options: Values, session: "PipSession"
    ) -> "PackageFinder":
        """
        Create a package finder appropriate to this list command.
        """
        # Lazy import the heavy index modules as most list invocations won't need 'em.
        from pip._internal.index.collector import LinkCollector
        from pip._internal.index.package_finder import PackageFinder

        link_collector = LinkCollector.create(session, options=options)

        # Pass allow_yanked=False to ignore yanked versions.
        selection_prefs = SelectionPreferences(
            allow_yanked=False,
            allow_all_prereleases=options.pre,
        )

        return PackageFinder.create(
            link_collector=link_collector,
            selection_prefs=selection_prefs,
        )

    def run(self, options: Values, args: List[str]) -> int:
        if options.outdated and options.uptodate:
            raise CommandError("Options --outdated and --uptodate cannot be combined.")

        if options.outdated and options.list_format == "freeze":
            raise CommandError(
                "List format 'freeze' cannot be used with the --outdated option."
            )

        cmdoptions.check_list_path_option(options)

        skip = set(stdlib_pkgs)
        if options.excludes:
            skip.update(canonicalize_name(n) for n in options.excludes)

        packages: _ProcessedDists = [
            cast("_DistWithLatestInfo", d)
            for d in get_environment(options.path).iter_installed_distributions(
                local_only=options.local,
                user_only=options.user,
                editables_only=options.editable,
                include_editables=options.include_editable,
                skip=skip,
            )
        ]

        # get_not_required must be called firstly in order to find and
        # filter out all dependencies correctly. Otherwise a package
        # can't be identified as requirement because some parent packages
        # could be filtered out before.
        if options.not_required:
            packages = self.get_not_required(packages, options)

        if options.outdated:
            packages = self.get_outdated(packages, options)
        elif options.uptodate:
            packages = self.get_uptodate(packages, options)

        self.output_package_listing(packages, options)
        return SUCCESS

    def get_outdated(
        self, packages: "_ProcessedDists", options: Values
    ) -> "_ProcessedDists":
        return [
            dist
            for dist in self.iter_packages_latest_infos(packages, options)
            if dist.latest_version > dist.version
        ]

    def get_uptodate(
        self, packages: "_ProcessedDists", options: Values
    ) -> "_ProcessedDists":
        return [
            dist
            for dist in self.iter_packages_latest_infos(packages, options)
            if dist.latest_version == dist.version
        ]

    def get_not_required(
        self, packages: "_ProcessedDists", options: Values
    ) -> "_ProcessedDists":
        dep_keys = {
            canonicalize_name(dep.name)
            for dist in packages
            for dep in (dist.iter_dependencies() or ())
        }

        # Create a set to remove duplicate packages, and cast it to a list
        # to keep the return type consistent with get_outdated and
        # get_uptodate
        return list({pkg for pkg in packages if pkg.canonical_name not in dep_keys})

    def iter_packages_latest_infos(
        self, packages: "_ProcessedDists", options: Values
    ) -> Generator["_DistWithLatestInfo", None, None]:
        with self._build_session(options) as session:
            finder = self._build_package_finder(options, session)

            def latest_info(
                dist: "_DistWithLatestInfo",
            ) -> Optional["_DistWithLatestInfo"]:
                all_candidates = finder.find_all_candidates(dist.canonical_name)
                if not options.pre:
                    # Remove prereleases
                    all_candidates = [
                        candidate
                        for candidate in all_candidates
                        if not candidate.version.is_prerelease
                    ]

                evaluator = finder.make_candidate_evaluator(
                    project_name=dist.canonical_name,
                )
                best_candidate = evaluator.sort_best_candidate(all_candidates)
                if best_candidate is None:
                    return None

                remote_version = best_candidate.version
                if best_candidate.link.is_wheel:
                    typ = "wheel"
                else:
                    typ = "sdist"
                dist.latest_version = remote_version
                dist.latest_filetype = typ
                return dist

            for dist in map(latest_info, packages):
                if dist is not None:
                    yield dist

    def output_package_listing(
        self, packages: "_ProcessedDists", options: Values
    ) -> None:
        packages = sorted(
            packages,
            key=lambda dist: dist.canonical_name,
        )
        if options.list_format == "columns" and packages:
            data, header = format_for_columns(packages, options)
            self.output_package_listing_columns(data, header)
        elif options.list_format == "freeze":
            for dist in packages:
                if options.verbose >= 1:
                    write_output(
                        "%s==%s (%s)", dist.raw_name, dist.version, dist.location
                    )
                else:
                    write_output("%s==%s", dist.raw_name, dist.version)
        elif options.list_format == "json":
            write_output(format_for_json(packages, options))

    def output_package_listing_columns(
        self, data: List[List[str]], header: List[str]
    ) -> None:
        # insert the header first: we need to know the size of column names
        if len(data) > 0:
            data.insert(0, header)

        pkg_strings, sizes = tabulate(data)

        # Create and add a separator.
        if len(data) > 0:
            pkg_strings.insert(1, " ".join("-" * x for x in sizes))

        for val in pkg_strings:
            write_output(val)


def format_for_columns(
    pkgs: "_ProcessedDists", options: Values
) -> Tuple[List[List[str]], List[str]]:
    """
    Convert the package data into something usable
    by output_package_listing_columns.
    """
    header = ["Package", "Version"]

    running_outdated = options.outdated
    if running_outdated:
        header.extend(["Latest", "Type"])

    has_editables = any(x.editable for x in pkgs)
    if has_editables:
        header.append("Editable project location")

    if options.verbose >= 1:
        header.append("Location")
    if options.verbose >= 1:
        header.append("Installer")

    data = []
    for proj in pkgs:
        # if we're working on the 'outdated' list, separate out the
        # latest_version and type
        row = [proj.raw_name, proj.raw_version]

        if running_outdated:
            row.append(str(proj.latest_version))
            row.append(proj.latest_filetype)

        if has_editables:
            row.append(proj.editable_project_location or "")

        if options.verbose >= 1:
            row.append(proj.location or "")
        if options.verbose >= 1:
            row.append(proj.installer)

        data.append(row)

    return data, header


def format_for_json(packages: "_ProcessedDists", options: Values) -> str:
    data = []
    for dist in packages:
        info = {
            "name": dist.raw_name,
            "version": str(dist.version),
        }
        if options.verbose >= 1:
            info["location"] = dist.location or ""
            info["installer"] = dist.installer
        if options.outdated:
            info["latest_version"] = str(dist.latest_version)
            info["latest_filetype"] = dist.latest_filetype
        editable_project_location = dist.editable_project_location
        if editable_project_location:
            info["editable_project_location"] = editable_project_location
        data.append(info)
    return json.dumps(data)

# === NexusCore/openenv\Lib\site-packages\pip\_vendor\rich\live.py ===
import sys
from threading import Event, RLock, Thread
from types import TracebackType
from typing import IO, Any, Callable, List, Optional, TextIO, Type, cast

from . import get_console
from .console import Console, ConsoleRenderable, RenderableType, RenderHook
from .control import Control
from .file_proxy import FileProxy
from .jupyter import JupyterMixin
from .live_render import LiveRender, VerticalOverflowMethod
from .screen import Screen
from .text import Text


class _RefreshThread(Thread):
    """A thread that calls refresh() at regular intervals."""

    def __init__(self, live: "Live", refresh_per_second: float) -> None:
        self.live = live
        self.refresh_per_second = refresh_per_second
        self.done = Event()
        super().__init__(daemon=True)

    def stop(self) -> None:
        self.done.set()

    def run(self) -> None:
        while not self.done.wait(1 / self.refresh_per_second):
            with self.live._lock:
                if not self.done.is_set():
                    self.live.refresh()


class Live(JupyterMixin, RenderHook):
    """Renders an auto-updating live display of any given renderable.

    Args:
        renderable (RenderableType, optional): The renderable to live display. Defaults to displaying nothing.
        console (Console, optional): Optional Console instance. Defaults to an internal Console instance writing to stdout.
        screen (bool, optional): Enable alternate screen mode. Defaults to False.
        auto_refresh (bool, optional): Enable auto refresh. If disabled, you will need to call `refresh()` or `update()` with refresh flag. Defaults to True
        refresh_per_second (float, optional): Number of times per second to refresh the live display. Defaults to 4.
        transient (bool, optional): Clear the renderable on exit (has no effect when screen=True). Defaults to False.
        redirect_stdout (bool, optional): Enable redirection of stdout, so ``print`` may be used. Defaults to True.
        redirect_stderr (bool, optional): Enable redirection of stderr. Defaults to True.
        vertical_overflow (VerticalOverflowMethod, optional): How to handle renderable when it is too tall for the console. Defaults to "ellipsis".
        get_renderable (Callable[[], RenderableType], optional): Optional callable to get renderable. Defaults to None.
    """

    def __init__(
        self,
        renderable: Optional[RenderableType] = None,
        *,
        console: Optional[Console] = None,
        screen: bool = False,
        auto_refresh: bool = True,
        refresh_per_second: float = 4,
        transient: bool = False,
        redirect_stdout: bool = True,
        redirect_stderr: bool = True,
        vertical_overflow: VerticalOverflowMethod = "ellipsis",
        get_renderable: Optional[Callable[[], RenderableType]] = None,
    ) -> None:
        assert refresh_per_second > 0, "refresh_per_second must be > 0"
        self._renderable = renderable
        self.console = console if console is not None else get_console()
        self._screen = screen
        self._alt_screen = False

        self._redirect_stdout = redirect_stdout
        self._redirect_stderr = redirect_stderr
        self._restore_stdout: Optional[IO[str]] = None
        self._restore_stderr: Optional[IO[str]] = None

        self._lock = RLock()
        self.ipy_widget: Optional[Any] = None
        self.auto_refresh = auto_refresh
        self._started: bool = False
        self.transient = True if screen else transient

        self._refresh_thread: Optional[_RefreshThread] = None
        self.refresh_per_second = refresh_per_second

        self.vertical_overflow = vertical_overflow
        self._get_renderable = get_renderable
        self._live_render = LiveRender(
            self.get_renderable(), vertical_overflow=vertical_overflow
        )

    @property
    def is_started(self) -> bool:
        """Check if live display has been started."""
        return self._started

    def get_renderable(self) -> RenderableType:
        renderable = (
            self._get_renderable()
            if self._get_renderable is not None
            else self._renderable
        )
        return renderable or ""

    def start(self, refresh: bool = False) -> None:
        """Start live rendering display.

        Args:
            refresh (bool, optional): Also refresh. Defaults to False.
        """
        with self._lock:
            if self._started:
                return
            self.console.set_live(self)
            self._started = True
            if self._screen:
                self._alt_screen = self.console.set_alt_screen(True)
            self.console.show_cursor(False)
            self._enable_redirect_io()
            self.console.push_render_hook(self)
            if refresh:
                try:
                    self.refresh()
                except Exception:
                    # If refresh fails, we want to stop the redirection of sys.stderr,
                    # so the error stacktrace is properly displayed in the terminal.
                    # (or, if the code that calls Rich captures the exception and wants to display something,
                    # let this be displayed in the terminal).
                    self.stop()
                    raise
            if self.auto_refresh:
                self._refresh_thread = _RefreshThread(self, self.refresh_per_second)
                self._refresh_thread.start()

    def stop(self) -> None:
        """Stop live rendering display."""
        with self._lock:
            if not self._started:
                return
            self.console.clear_live()
            self._started = False

            if self.auto_refresh and self._refresh_thread is not None:
                self._refresh_thread.stop()
                self._refresh_thread = None
            # allow it to fully render on the last even if overflow
            self.vertical_overflow = "visible"
            with self.console:
                try:
                    if not self._alt_screen and not self.console.is_jupyter:
                        self.refresh()
                finally:
                    self._disable_redirect_io()
                    self.console.pop_render_hook()
                    if not self._alt_screen and self.console.is_terminal:
                        self.console.line()
                    self.console.show_cursor(True)
                    if self._alt_screen:
                        self.console.set_alt_screen(False)

                    if self.transient and not self._alt_screen:
                        self.console.control(self._live_render.restore_cursor())
                    if self.ipy_widget is not None and self.transient:
                        self.ipy_widget.close()  # pragma: no cover

    def __enter__(self) -> "Live":
        self.start(refresh=self._renderable is not None)
        return self

    def __exit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[TracebackType],
    ) -> None:
        self.stop()

    def _enable_redirect_io(self) -> None:
        """Enable redirecting of stdout / stderr."""
        if self.console.is_terminal or self.console.is_jupyter:
            if self._redirect_stdout and not isinstance(sys.stdout, FileProxy):
                self._restore_stdout = sys.stdout
                sys.stdout = cast("TextIO", FileProxy(self.console, sys.stdout))
            if self._redirect_stderr and not isinstance(sys.stderr, FileProxy):
                self._restore_stderr = sys.stderr
                sys.stderr = cast("TextIO", FileProxy(self.console, sys.stderr))

    def _disable_redirect_io(self) -> None:
        """Disable redirecting of stdout / stderr."""
        if self._restore_stdout:
            sys.stdout = cast("TextIO", self._restore_stdout)
            self._restore_stdout = None
        if self._restore_stderr:
            sys.stderr = cast("TextIO", self._restore_stderr)
            self._restore_stderr = None

    @property
    def renderable(self) -> RenderableType:
        """Get the renderable that is being displayed

        Returns:
            RenderableType: Displayed renderable.
        """
        renderable = self.get_renderable()
        return Screen(renderable) if self._alt_screen else renderable

    def update(self, renderable: RenderableType, *, refresh: bool = False) -> None:
        """Update the renderable that is being displayed

        Args:
            renderable (RenderableType): New renderable to use.
            refresh (bool, optional): Refresh the display. Defaults to False.
        """
        if isinstance(renderable, str):
            renderable = self.console.render_str(renderable)
        with self._lock:
            self._renderable = renderable
            if refresh:
                self.refresh()

    def refresh(self) -> None:
        """Update the display of the Live Render."""
        with self._lock:
            self._live_render.set_renderable(self.renderable)
            if self.console.is_jupyter:  # pragma: no cover
                try:
                    from IPython.display import display
                    from ipywidgets import Output
                except ImportError:
                    import warnings

                    warnings.warn('install "ipywidgets" for Jupyter support')
                else:
                    if self.ipy_widget is None:
                        self.ipy_widget = Output()
                        display(self.ipy_widget)

                    with self.ipy_widget:
                        self.ipy_widget.clear_output(wait=True)
                        self.console.print(self._live_render.renderable)
            elif self.console.is_terminal and not self.console.is_dumb_terminal:
                with self.console:
                    self.console.print(Control())
            elif (
                not self._started and not self.transient
            ):  # if it is finished allow files or dumb-terminals to see final result
                with self.console:
                    self.console.print(Control())

    def process_renderables(
        self, renderables: List[ConsoleRenderable]
    ) -> List[ConsoleRenderable]:
        """Process renderables to restore cursor and display progress."""
        self._live_render.vertical_overflow = self.vertical_overflow
        if self.console.is_interactive:
            # lock needs acquiring as user can modify live_render renderable at any time unlike in Progress.
            with self._lock:
                reset = (
                    Control.home()
                    if self._alt_screen
                    else self._live_render.position_cursor()
                )
                renderables = [reset, *renderables, self._live_render]
        elif (
            not self._started and not self.transient
        ):  # if it is finished render the final output for files or dumb_terminals
            renderables = [*renderables, self._live_render]

        return renderables


if __name__ == "__main__":  # pragma: no cover
    import random
    import time
    from itertools import cycle
    from typing import Dict, List, Tuple

    from .align import Align
    from .console import Console
    from .live import Live as Live
    from .panel import Panel
    from .rule import Rule
    from .syntax import Syntax
    from .table import Table

    console = Console()

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
        "You can make the terminal shorter and taller to see the live table hide"
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

    examples = cycle(progress_renderables)

    exchanges = [
        "SGD",
        "MYR",
        "EUR",
        "USD",
        "AUD",
        "JPY",
        "CNH",
        "HKD",
        "CAD",
        "INR",
        "DKK",
        "GBP",
        "RUB",
        "NZD",
        "MXN",
        "IDR",
        "TWD",
        "THB",
        "VND",
    ]
    with Live(console=console) as live_table:
        exchange_rate_dict: Dict[Tuple[str, str], float] = {}

        for index in range(100):
            select_exchange = exchanges[index % len(exchanges)]

            for exchange in exchanges:
                if exchange == select_exchange:
                    continue
                time.sleep(0.4)
                if random.randint(0, 10) < 1:
                    console.log(next(examples))
                exchange_rate_dict[(select_exchange, exchange)] = 200 / (
                    (random.random() * 320) + 1
                )
                if len(exchange_rate_dict) > len(exchanges) - 1:
                    exchange_rate_dict.pop(list(exchange_rate_dict.keys())[0])
                table = Table(title="Exchange Rates")

                table.add_column("Source Currency")
                table.add_column("Destination Currency")
                table.add_column("Exchange Rate")

                for (source, dest), exchange_rate in exchange_rate_dict.items():
                    table.add_row(
                        source,
                        dest,
                        Text(
                            f"{exchange_rate:.4f}",
                            style="red" if exchange_rate < 1.0 else "green",
                        ),
                    )

                live_table.update(Align.center(table))

# === NexusCore/openenv\Lib\site-packages\jupyter_client\consoleapp.py ===
""" A minimal application base mixin for all ZMQ based IPython frontends.

This is not a complete console app, as subprocess will not be able to receive
input, there is no real readline support, among other limitations. This is a
refactoring of what used to be the IPython/qt/console/qtconsoleapp.py
"""
# Copyright (c) Jupyter Development Team.
# Distributed under the terms of the Modified BSD License.
import atexit
import os
import signal
import sys
import typing as t
import uuid
import warnings

from jupyter_core.application import base_aliases, base_flags
from traitlets import CBool, CUnicode, Dict, List, Type, Unicode
from traitlets.config.application import boolean_flag

from . import KernelManager, connect, find_connection_file, tunnel_to_kernel
from .blocking import BlockingKernelClient
from .connect import KernelConnectionInfo
from .kernelspec import NoSuchKernel
from .localinterfaces import localhost
from .restarter import KernelRestarter
from .session import Session
from .utils import _filefind

ConnectionFileMixin = connect.ConnectionFileMixin

# -----------------------------------------------------------------------------
# Aliases and Flags
# -----------------------------------------------------------------------------

flags: dict = {}
flags.update(base_flags)
# the flags that are specific to the frontend
# these must be scrubbed before being passed to the kernel,
# or it will raise an error on unrecognized flags
app_flags: dict = {
    "existing": (
        {"JupyterConsoleApp": {"existing": "kernel*.json"}},
        "Connect to an existing kernel. If no argument specified, guess most recent",
    ),
}
app_flags.update(
    boolean_flag(
        "confirm-exit",
        "JupyterConsoleApp.confirm_exit",
        """Set to display confirmation dialog on exit. You can always use 'exit' or
       'quit', to force a direct exit without any confirmation. This can also
       be set in the config file by setting
       `c.JupyterConsoleApp.confirm_exit`.
    """,
        """Don't prompt the user when exiting. This will terminate the kernel
       if it is owned by the frontend, and leave it alive if it is external.
       This can also be set in the config file by setting
       `c.JupyterConsoleApp.confirm_exit`.
    """,
    )
)
flags.update(app_flags)

aliases: dict = {}
aliases.update(base_aliases)

# also scrub aliases from the frontend
app_aliases: dict = {
    "ip": "JupyterConsoleApp.ip",
    "transport": "JupyterConsoleApp.transport",
    "hb": "JupyterConsoleApp.hb_port",
    "shell": "JupyterConsoleApp.shell_port",
    "iopub": "JupyterConsoleApp.iopub_port",
    "stdin": "JupyterConsoleApp.stdin_port",
    "control": "JupyterConsoleApp.control_port",
    "existing": "JupyterConsoleApp.existing",
    "f": "JupyterConsoleApp.connection_file",
    "kernel": "JupyterConsoleApp.kernel_name",
    "ssh": "JupyterConsoleApp.sshserver",
    "sshkey": "JupyterConsoleApp.sshkey",
}
aliases.update(app_aliases)

# -----------------------------------------------------------------------------
# Classes
# -----------------------------------------------------------------------------

classes: t.List[t.Type[t.Any]] = [KernelManager, KernelRestarter, Session]


class JupyterConsoleApp(ConnectionFileMixin):
    """The base Jupyter console application."""

    name: t.Union[str, Unicode] = "jupyter-console-mixin"

    description: t.Union[str, Unicode] = """
        The Jupyter Console Mixin.

        This class contains the common portions of console client (QtConsole,
        ZMQ-based terminal console, etc).  It is not a full console, in that
        launched terminal subprocesses will not be able to accept input.

        The Console using this mixing supports various extra features beyond
        the single-process Terminal IPython shell, such as connecting to
        existing kernel, via:

            jupyter console <appname> --existing

        as well as tunnel via SSH

    """

    classes = classes
    flags = Dict(flags)
    aliases = Dict(aliases)
    kernel_manager_class = Type(
        default_value=KernelManager,
        config=True,
        help="The kernel manager class to use.",
    )
    kernel_client_class = BlockingKernelClient

    kernel_argv = List(Unicode())

    # connection info:

    sshserver = Unicode("", config=True, help="""The SSH server to use to connect to the kernel.""")
    sshkey = Unicode(
        "",
        config=True,
        help="""Path to the ssh key to use for logging in to the ssh server.""",
    )

    def _connection_file_default(self) -> str:
        return "kernel-%i.json" % os.getpid()

    existing = CUnicode("", config=True, help="""Connect to an already running kernel""")

    kernel_name = Unicode(
        "python", config=True, help="""The name of the default kernel to start."""
    )

    confirm_exit = CBool(
        True,
        config=True,
        help="""
        Set to display confirmation dialog on exit. You can always use 'exit' or 'quit',
        to force a direct exit without any confirmation.""",
    )

    def build_kernel_argv(self, argv: object = None) -> None:
        """build argv to be passed to kernel subprocess

        Override in subclasses if any args should be passed to the kernel
        """
        self.kernel_argv = self.extra_args  # type:ignore[attr-defined]

    def init_connection_file(self) -> None:
        """find the connection file, and load the info if found.

        The current working directory and the current profile's security
        directory will be searched for the file if it is not given by
        absolute path.

        When attempting to connect to an existing kernel and the `--existing`
        argument does not match an existing file, it will be interpreted as a
        fileglob, and the matching file in the current profile's security dir
        with the latest access time will be used.

        After this method is called, self.connection_file contains the *full path*
        to the connection file, never just its name.
        """
        runtime_dir = self.runtime_dir  # type:ignore[attr-defined]
        if self.existing:
            try:
                cf = find_connection_file(self.existing, [".", runtime_dir])
            except Exception:
                self.log.critical(
                    "Could not find existing kernel connection file %s", self.existing
                )
                self.exit(1)  # type:ignore[attr-defined]
            self.log.debug("Connecting to existing kernel: %s", cf)
            self.connection_file = cf
        else:
            # not existing, check if we are going to write the file
            # and ensure that self.connection_file is a full path, not just the shortname
            try:
                cf = find_connection_file(self.connection_file, [runtime_dir])
            except Exception:
                # file might not exist
                if self.connection_file == os.path.basename(self.connection_file):
                    # just shortname, put it in security dir
                    cf = os.path.join(runtime_dir, self.connection_file)
                else:
                    cf = self.connection_file
                self.connection_file = cf
        try:
            self.connection_file = _filefind(self.connection_file, [".", runtime_dir])
        except OSError:
            self.log.debug("Connection File not found: %s", self.connection_file)
            return

        # should load_connection_file only be used for existing?
        # as it is now, this allows reusing ports if an existing
        # file is requested
        try:
            self.load_connection_file()
        except Exception:
            self.log.error(
                "Failed to load connection file: %r",
                self.connection_file,
                exc_info=True,
            )
            self.exit(1)  # type:ignore[attr-defined]

    def init_ssh(self) -> None:
        """set up ssh tunnels, if needed."""
        if not self.existing or (not self.sshserver and not self.sshkey):
            return
        self.load_connection_file()

        transport = self.transport
        ip = self.ip

        if transport != "tcp":
            self.log.error("Can only use ssh tunnels with TCP sockets, not %s", transport)
            sys.exit(-1)

        if self.sshkey and not self.sshserver:
            # specifying just the key implies that we are connecting directly
            self.sshserver = ip
            ip = localhost()

        # build connection dict for tunnels:
        info: KernelConnectionInfo = {
            "ip": ip,
            "shell_port": self.shell_port,
            "iopub_port": self.iopub_port,
            "stdin_port": self.stdin_port,
            "hb_port": self.hb_port,
            "control_port": self.control_port,
        }

        self.log.info("Forwarding connections to %s via %s", ip, self.sshserver)

        # tunnels return a new set of ports, which will be on localhost:
        self.ip = localhost()
        try:
            newports = tunnel_to_kernel(info, self.sshserver, self.sshkey)
        except:  # noqa
            # even catch KeyboardInterrupt
            self.log.error("Could not setup tunnels", exc_info=True)
            self.exit(1)  # type:ignore[attr-defined]

        (
            self.shell_port,
            self.iopub_port,
            self.stdin_port,
            self.hb_port,
            self.control_port,
        ) = newports

        cf = self.connection_file
        root, ext = os.path.splitext(cf)
        self.connection_file = root + "-ssh" + ext
        self.write_connection_file()  # write the new connection file
        self.log.info("To connect another client via this tunnel, use:")
        self.log.info("--existing %s", os.path.basename(self.connection_file))

    def _new_connection_file(self) -> str:
        cf = ""
        while not cf:
            # we don't need a 128b id to distinguish kernels, use more readable
            # 48b node segment (12 hex chars).  Users running more than 32k simultaneous
            # kernels can subclass.
            ident = str(uuid.uuid4()).split("-")[-1]
            runtime_dir = self.runtime_dir  # type:ignore[attr-defined]
            cf = os.path.join(runtime_dir, "kernel-%s.json" % ident)
            # only keep if it's actually new.  Protect against unlikely collision
            # in 48b random search space
            cf = cf if not os.path.exists(cf) else ""
        return cf

    def init_kernel_manager(self) -> None:
        """Initialize the kernel manager."""
        # Don't let Qt or ZMQ swallow KeyboardInterupts.
        if self.existing:
            self.kernel_manager = None
            return
        signal.signal(signal.SIGINT, signal.SIG_DFL)

        # Create a KernelManager and start a kernel.
        try:
            self.kernel_manager = self.kernel_manager_class(
                ip=self.ip,
                session=self.session,
                transport=self.transport,
                shell_port=self.shell_port,
                iopub_port=self.iopub_port,
                stdin_port=self.stdin_port,
                hb_port=self.hb_port,
                control_port=self.control_port,
                connection_file=self.connection_file,
                kernel_name=self.kernel_name,
                parent=self,
                data_dir=self.data_dir,
            )
        except NoSuchKernel:
            self.log.critical("Could not find kernel %s", self.kernel_name)
            self.exit(1)  # type:ignore[attr-defined]

        self.kernel_manager = t.cast(KernelManager, self.kernel_manager)
        self.kernel_manager.client_factory = self.kernel_client_class
        kwargs = {}
        kwargs["extra_arguments"] = self.kernel_argv
        self.kernel_manager.start_kernel(**kwargs)
        atexit.register(self.kernel_manager.cleanup_ipc_files)

        if self.sshserver:
            # ssh, write new connection file
            self.kernel_manager.write_connection_file()

        # in case KM defaults / ssh writing changes things:
        km = self.kernel_manager
        self.shell_port = km.shell_port
        self.iopub_port = km.iopub_port
        self.stdin_port = km.stdin_port
        self.hb_port = km.hb_port
        self.control_port = km.control_port
        self.connection_file = km.connection_file

        atexit.register(self.kernel_manager.cleanup_connection_file)

    def init_kernel_client(self) -> None:
        """Initialize the kernel client."""
        if self.kernel_manager is not None:
            self.kernel_client = self.kernel_manager.client()
        else:
            self.kernel_client = self.kernel_client_class(
                session=self.session,
                ip=self.ip,
                transport=self.transport,
                shell_port=self.shell_port,
                iopub_port=self.iopub_port,
                stdin_port=self.stdin_port,
                hb_port=self.hb_port,
                control_port=self.control_port,
                connection_file=self.connection_file,
                parent=self,
            )

        self.kernel_client.start_channels()

    def initialize(self, argv: object = None) -> None:
        """
        Classes which mix this class in should call:
               JupyterConsoleApp.initialize(self,argv)
        """
        if getattr(self, "_dispatching", False):
            return
        self.init_connection_file()
        self.init_ssh()
        self.init_kernel_manager()
        self.init_kernel_client()


class IPythonConsoleApp(JupyterConsoleApp):
    """An app to manage an ipython console."""

    def __init__(self, *args: t.Any, **kwargs: t.Any) -> None:
        """Initialize the app."""
        warnings.warn("IPythonConsoleApp is deprecated. Use JupyterConsoleApp", stacklevel=2)
        super().__init__(*args, **kwargs)

# === NexusCore/openenv\Lib\site-packages\prompt_toolkit\styles\style_transformation.py ===
"""
Collection of style transformations.

Think of it as a kind of color post processing after the rendering is done.
This could be used for instance to change the contrast/saturation; swap light
and dark colors or even change certain colors for other colors.

When the UI is rendered, these transformations can be applied right after the
style strings are turned into `Attrs` objects that represent the actual
formatting.
"""

from __future__ import annotations

from abc import ABCMeta, abstractmethod
from colorsys import hls_to_rgb, rgb_to_hls
from typing import Callable, Hashable, Sequence

from prompt_toolkit.cache import memoized
from prompt_toolkit.filters import FilterOrBool, to_filter
from prompt_toolkit.utils import AnyFloat, to_float, to_str

from .base import ANSI_COLOR_NAMES, Attrs
from .style import parse_color

__all__ = [
    "StyleTransformation",
    "SwapLightAndDarkStyleTransformation",
    "ReverseStyleTransformation",
    "SetDefaultColorStyleTransformation",
    "AdjustBrightnessStyleTransformation",
    "DummyStyleTransformation",
    "ConditionalStyleTransformation",
    "DynamicStyleTransformation",
    "merge_style_transformations",
]


class StyleTransformation(metaclass=ABCMeta):
    """
    Base class for any style transformation.
    """

    @abstractmethod
    def transform_attrs(self, attrs: Attrs) -> Attrs:
        """
        Take an `Attrs` object and return a new `Attrs` object.

        Remember that the color formats can be either "ansi..." or a 6 digit
        lowercase hexadecimal color (without '#' prefix).
        """

    def invalidation_hash(self) -> Hashable:
        """
        When this changes, the cache should be invalidated.
        """
        return f"{self.__class__.__name__}-{id(self)}"


class SwapLightAndDarkStyleTransformation(StyleTransformation):
    """
    Turn dark colors into light colors and the other way around.

    This is meant to make color schemes that work on a dark background usable
    on a light background (and the other way around).

    Notice that this doesn't swap foreground and background like "reverse"
    does. It turns light green into dark green and the other way around.
    Foreground and background colors are considered individually.

    Also notice that when <reverse> is used somewhere and no colors are given
    in particular (like what is the default for the bottom toolbar), then this
    doesn't change anything. This is what makes sense, because when the
    'default' color is chosen, it's what works best for the terminal, and
    reverse works good with that.
    """

    def transform_attrs(self, attrs: Attrs) -> Attrs:
        """
        Return the `Attrs` used when opposite luminosity should be used.
        """
        # Reverse colors.
        attrs = attrs._replace(color=get_opposite_color(attrs.color))
        attrs = attrs._replace(bgcolor=get_opposite_color(attrs.bgcolor))

        return attrs


class ReverseStyleTransformation(StyleTransformation):
    """
    Swap the 'reverse' attribute.

    (This is still experimental.)
    """

    def transform_attrs(self, attrs: Attrs) -> Attrs:
        return attrs._replace(reverse=not attrs.reverse)


class SetDefaultColorStyleTransformation(StyleTransformation):
    """
    Set default foreground/background color for output that doesn't specify
    anything. This is useful for overriding the terminal default colors.

    :param fg: Color string or callable that returns a color string for the
        foreground.
    :param bg: Like `fg`, but for the background.
    """

    def __init__(
        self, fg: str | Callable[[], str], bg: str | Callable[[], str]
    ) -> None:
        self.fg = fg
        self.bg = bg

    def transform_attrs(self, attrs: Attrs) -> Attrs:
        if attrs.bgcolor in ("", "default"):
            attrs = attrs._replace(bgcolor=parse_color(to_str(self.bg)))

        if attrs.color in ("", "default"):
            attrs = attrs._replace(color=parse_color(to_str(self.fg)))

        return attrs

    def invalidation_hash(self) -> Hashable:
        return (
            "set-default-color",
            to_str(self.fg),
            to_str(self.bg),
        )


class AdjustBrightnessStyleTransformation(StyleTransformation):
    """
    Adjust the brightness to improve the rendering on either dark or light
    backgrounds.

    For dark backgrounds, it's best to increase `min_brightness`. For light
    backgrounds it's best to decrease `max_brightness`. Usually, only one
    setting is adjusted.

    This will only change the brightness for text that has a foreground color
    defined, but no background color. It works best for 256 or true color
    output.

    .. note:: Notice that there is no universal way to detect whether the
              application is running in a light or dark terminal. As a
              developer of an command line application, you'll have to make
              this configurable for the user.

    :param min_brightness: Float between 0.0 and 1.0 or a callable that returns
        a float.
    :param max_brightness: Float between 0.0 and 1.0 or a callable that returns
        a float.
    """

    def __init__(
        self, min_brightness: AnyFloat = 0.0, max_brightness: AnyFloat = 1.0
    ) -> None:
        self.min_brightness = min_brightness
        self.max_brightness = max_brightness

    def transform_attrs(self, attrs: Attrs) -> Attrs:
        min_brightness = to_float(self.min_brightness)
        max_brightness = to_float(self.max_brightness)
        assert 0 <= min_brightness <= 1
        assert 0 <= max_brightness <= 1

        # Don't do anything if the whole brightness range is acceptable.
        # This also avoids turning ansi colors into RGB sequences.
        if min_brightness == 0.0 and max_brightness == 1.0:
            return attrs

        # If a foreground color is given without a background color.
        no_background = not attrs.bgcolor or attrs.bgcolor == "default"
        has_fgcolor = attrs.color and attrs.color != "ansidefault"

        if has_fgcolor and no_background:
            # Calculate new RGB values.
            r, g, b = self._color_to_rgb(attrs.color or "")
            hue, brightness, saturation = rgb_to_hls(r, g, b)
            brightness = self._interpolate_brightness(
                brightness, min_brightness, max_brightness
            )
            r, g, b = hls_to_rgb(hue, brightness, saturation)
            new_color = f"{int(r * 255):02x}{int(g * 255):02x}{int(b * 255):02x}"

            attrs = attrs._replace(color=new_color)

        return attrs

    def _color_to_rgb(self, color: str) -> tuple[float, float, float]:
        """
        Parse `style.Attrs` color into RGB tuple.
        """
        # Do RGB lookup for ANSI colors.
        try:
            from prompt_toolkit.output.vt100 import ANSI_COLORS_TO_RGB

            r, g, b = ANSI_COLORS_TO_RGB[color]
            return r / 255.0, g / 255.0, b / 255.0
        except KeyError:
            pass

        # Parse RRGGBB format.
        return (
            int(color[0:2], 16) / 255.0,
            int(color[2:4], 16) / 255.0,
            int(color[4:6], 16) / 255.0,
        )

        # NOTE: we don't have to support named colors here. They are already
        #       transformed into RGB values in `style.parse_color`.

    def _interpolate_brightness(
        self, value: float, min_brightness: float, max_brightness: float
    ) -> float:
        """
        Map the brightness to the (min_brightness..max_brightness) range.
        """
        return min_brightness + (max_brightness - min_brightness) * value

    def invalidation_hash(self) -> Hashable:
        return (
            "adjust-brightness",
            to_float(self.min_brightness),
            to_float(self.max_brightness),
        )


class DummyStyleTransformation(StyleTransformation):
    """
    Don't transform anything at all.
    """

    def transform_attrs(self, attrs: Attrs) -> Attrs:
        return attrs

    def invalidation_hash(self) -> Hashable:
        # Always return the same hash for these dummy instances.
        return "dummy-style-transformation"


class DynamicStyleTransformation(StyleTransformation):
    """
    StyleTransformation class that can dynamically returns any
    `StyleTransformation`.

    :param get_style_transformation: Callable that returns a
        :class:`.StyleTransformation` instance.
    """

    def __init__(
        self, get_style_transformation: Callable[[], StyleTransformation | None]
    ) -> None:
        self.get_style_transformation = get_style_transformation

    def transform_attrs(self, attrs: Attrs) -> Attrs:
        style_transformation = (
            self.get_style_transformation() or DummyStyleTransformation()
        )
        return style_transformation.transform_attrs(attrs)

    def invalidation_hash(self) -> Hashable:
        style_transformation = (
            self.get_style_transformation() or DummyStyleTransformation()
        )
        return style_transformation.invalidation_hash()


class ConditionalStyleTransformation(StyleTransformation):
    """
    Apply the style transformation depending on a condition.
    """

    def __init__(
        self, style_transformation: StyleTransformation, filter: FilterOrBool
    ) -> None:
        self.style_transformation = style_transformation
        self.filter = to_filter(filter)

    def transform_attrs(self, attrs: Attrs) -> Attrs:
        if self.filter():
            return self.style_transformation.transform_attrs(attrs)
        return attrs

    def invalidation_hash(self) -> Hashable:
        return (self.filter(), self.style_transformation.invalidation_hash())


class _MergedStyleTransformation(StyleTransformation):
    def __init__(self, style_transformations: Sequence[StyleTransformation]) -> None:
        self.style_transformations = style_transformations

    def transform_attrs(self, attrs: Attrs) -> Attrs:
        for transformation in self.style_transformations:
            attrs = transformation.transform_attrs(attrs)
        return attrs

    def invalidation_hash(self) -> Hashable:
        return tuple(t.invalidation_hash() for t in self.style_transformations)


def merge_style_transformations(
    style_transformations: Sequence[StyleTransformation],
) -> StyleTransformation:
    """
    Merge multiple transformations together.
    """
    return _MergedStyleTransformation(style_transformations)


# Dictionary that maps ANSI color names to their opposite. This is useful for
# turning color schemes that are optimized for a black background usable for a
# white background.
OPPOSITE_ANSI_COLOR_NAMES = {
    "ansidefault": "ansidefault",
    "ansiblack": "ansiwhite",
    "ansired": "ansibrightred",
    "ansigreen": "ansibrightgreen",
    "ansiyellow": "ansibrightyellow",
    "ansiblue": "ansibrightblue",
    "ansimagenta": "ansibrightmagenta",
    "ansicyan": "ansibrightcyan",
    "ansigray": "ansibrightblack",
    "ansiwhite": "ansiblack",
    "ansibrightred": "ansired",
    "ansibrightgreen": "ansigreen",
    "ansibrightyellow": "ansiyellow",
    "ansibrightblue": "ansiblue",
    "ansibrightmagenta": "ansimagenta",
    "ansibrightcyan": "ansicyan",
    "ansibrightblack": "ansigray",
}
assert set(OPPOSITE_ANSI_COLOR_NAMES.keys()) == set(ANSI_COLOR_NAMES)
assert set(OPPOSITE_ANSI_COLOR_NAMES.values()) == set(ANSI_COLOR_NAMES)


@memoized()
def get_opposite_color(colorname: str | None) -> str | None:
    """
    Take a color name in either 'ansi...' format or 6 digit RGB, return the
    color of opposite luminosity (same hue/saturation).

    This is used for turning color schemes that work on a light background
    usable on a dark background.
    """
    if colorname is None:  # Because color/bgcolor can be None in `Attrs`.
        return None

    # Special values.
    if colorname in ("", "default"):
        return colorname

    # Try ANSI color names.
    try:
        return OPPOSITE_ANSI_COLOR_NAMES[colorname]
    except KeyError:
        # Try 6 digit RGB colors.
        r = int(colorname[:2], 16) / 255.0
        g = int(colorname[2:4], 16) / 255.0
        b = int(colorname[4:6], 16) / 255.0

        h, l, s = rgb_to_hls(r, g, b)

        l = 1 - l

        r, g, b = hls_to_rgb(h, l, s)

        r = int(r * 255)
        g = int(g * 255)
        b = int(b * 255)

        return f"{r:02x}{g:02x}{b:02x}"

# === NexusCore/openenv\Lib\site-packages\prompt_toolkit\widgets\menus.py ===
from __future__ import annotations

from typing import Callable, Iterable, Sequence

from prompt_toolkit.application.current import get_app
from prompt_toolkit.filters import Condition
from prompt_toolkit.formatted_text.base import OneStyleAndTextTuple, StyleAndTextTuples
from prompt_toolkit.key_binding.key_bindings import KeyBindings, KeyBindingsBase
from prompt_toolkit.key_binding.key_processor import KeyPressEvent
from prompt_toolkit.keys import Keys
from prompt_toolkit.layout.containers import (
    AnyContainer,
    ConditionalContainer,
    Container,
    Float,
    FloatContainer,
    HSplit,
    Window,
)
from prompt_toolkit.layout.controls import FormattedTextControl
from prompt_toolkit.mouse_events import MouseEvent, MouseEventType
from prompt_toolkit.utils import get_cwidth
from prompt_toolkit.widgets import Shadow

from .base import Border

__all__ = [
    "MenuContainer",
    "MenuItem",
]

E = KeyPressEvent


class MenuContainer:
    """
    :param floats: List of extra Float objects to display.
    :param menu_items: List of `MenuItem` objects.
    """

    def __init__(
        self,
        body: AnyContainer,
        menu_items: list[MenuItem],
        floats: list[Float] | None = None,
        key_bindings: KeyBindingsBase | None = None,
    ) -> None:
        self.body = body
        self.menu_items = menu_items
        self.selected_menu = [0]

        # Key bindings.
        kb = KeyBindings()

        @Condition
        def in_main_menu() -> bool:
            return len(self.selected_menu) == 1

        @Condition
        def in_sub_menu() -> bool:
            return len(self.selected_menu) > 1

        # Navigation through the main menu.

        @kb.add("left", filter=in_main_menu)
        def _left(event: E) -> None:
            self.selected_menu[0] = max(0, self.selected_menu[0] - 1)

        @kb.add("right", filter=in_main_menu)
        def _right(event: E) -> None:
            self.selected_menu[0] = min(
                len(self.menu_items) - 1, self.selected_menu[0] + 1
            )

        @kb.add("down", filter=in_main_menu)
        def _down(event: E) -> None:
            self.selected_menu.append(0)

        @kb.add("c-c", filter=in_main_menu)
        @kb.add("c-g", filter=in_main_menu)
        def _cancel(event: E) -> None:
            "Leave menu."
            event.app.layout.focus_last()

        # Sub menu navigation.

        @kb.add("left", filter=in_sub_menu)
        @kb.add("c-g", filter=in_sub_menu)
        @kb.add("c-c", filter=in_sub_menu)
        def _back(event: E) -> None:
            "Go back to parent menu."
            if len(self.selected_menu) > 1:
                self.selected_menu.pop()

        @kb.add("right", filter=in_sub_menu)
        def _submenu(event: E) -> None:
            "go into sub menu."
            if self._get_menu(len(self.selected_menu) - 1).children:
                self.selected_menu.append(0)

            # If This item does not have a sub menu. Go up in the parent menu.
            elif (
                len(self.selected_menu) == 2
                and self.selected_menu[0] < len(self.menu_items) - 1
            ):
                self.selected_menu = [
                    min(len(self.menu_items) - 1, self.selected_menu[0] + 1)
                ]
                if self.menu_items[self.selected_menu[0]].children:
                    self.selected_menu.append(0)

        @kb.add("up", filter=in_sub_menu)
        def _up_in_submenu(event: E) -> None:
            "Select previous (enabled) menu item or return to main menu."
            # Look for previous enabled items in this sub menu.
            menu = self._get_menu(len(self.selected_menu) - 2)
            index = self.selected_menu[-1]

            previous_indexes = [
                i
                for i, item in enumerate(menu.children)
                if i < index and not item.disabled
            ]

            if previous_indexes:
                self.selected_menu[-1] = previous_indexes[-1]
            elif len(self.selected_menu) == 2:
                # Return to main menu.
                self.selected_menu.pop()

        @kb.add("down", filter=in_sub_menu)
        def _down_in_submenu(event: E) -> None:
            "Select next (enabled) menu item."
            menu = self._get_menu(len(self.selected_menu) - 2)
            index = self.selected_menu[-1]

            next_indexes = [
                i
                for i, item in enumerate(menu.children)
                if i > index and not item.disabled
            ]

            if next_indexes:
                self.selected_menu[-1] = next_indexes[0]

        @kb.add("enter")
        def _click(event: E) -> None:
            "Click the selected menu item."
            item = self._get_menu(len(self.selected_menu) - 1)
            if item.handler:
                event.app.layout.focus_last()
                item.handler()

        # Controls.
        self.control = FormattedTextControl(
            self._get_menu_fragments, key_bindings=kb, focusable=True, show_cursor=False
        )

        self.window = Window(height=1, content=self.control, style="class:menu-bar")

        submenu = self._submenu(0)
        submenu2 = self._submenu(1)
        submenu3 = self._submenu(2)

        @Condition
        def has_focus() -> bool:
            return get_app().layout.current_window == self.window

        self.container = FloatContainer(
            content=HSplit(
                [
                    # The titlebar.
                    self.window,
                    # The 'body', like defined above.
                    body,
                ]
            ),
            floats=[
                Float(
                    xcursor=True,
                    ycursor=True,
                    content=ConditionalContainer(
                        content=Shadow(body=submenu), filter=has_focus
                    ),
                ),
                Float(
                    attach_to_window=submenu,
                    xcursor=True,
                    ycursor=True,
                    allow_cover_cursor=True,
                    content=ConditionalContainer(
                        content=Shadow(body=submenu2),
                        filter=has_focus
                        & Condition(lambda: len(self.selected_menu) >= 1),
                    ),
                ),
                Float(
                    attach_to_window=submenu2,
                    xcursor=True,
                    ycursor=True,
                    allow_cover_cursor=True,
                    content=ConditionalContainer(
                        content=Shadow(body=submenu3),
                        filter=has_focus
                        & Condition(lambda: len(self.selected_menu) >= 2),
                    ),
                ),
                # --
            ]
            + (floats or []),
            key_bindings=key_bindings,
        )

    def _get_menu(self, level: int) -> MenuItem:
        menu = self.menu_items[self.selected_menu[0]]

        for i, index in enumerate(self.selected_menu[1:]):
            if i < level:
                try:
                    menu = menu.children[index]
                except IndexError:
                    return MenuItem("debug")

        return menu

    def _get_menu_fragments(self) -> StyleAndTextTuples:
        focused = get_app().layout.has_focus(self.window)

        # This is called during the rendering. When we discover that this
        # widget doesn't have the focus anymore. Reset menu state.
        if not focused:
            self.selected_menu = [0]

        # Generate text fragments for the main menu.
        def one_item(i: int, item: MenuItem) -> Iterable[OneStyleAndTextTuple]:
            def mouse_handler(mouse_event: MouseEvent) -> None:
                hover = mouse_event.event_type == MouseEventType.MOUSE_MOVE
                if (
                    mouse_event.event_type == MouseEventType.MOUSE_DOWN
                    or hover
                    and focused
                ):
                    # Toggle focus.
                    app = get_app()
                    if not hover:
                        if app.layout.has_focus(self.window):
                            if self.selected_menu == [i]:
                                app.layout.focus_last()
                        else:
                            app.layout.focus(self.window)
                    self.selected_menu = [i]

            yield ("class:menu-bar", " ", mouse_handler)
            if i == self.selected_menu[0] and focused:
                yield ("[SetMenuPosition]", "", mouse_handler)
                style = "class:menu-bar.selected-item"
            else:
                style = "class:menu-bar"
            yield style, item.text, mouse_handler

        result: StyleAndTextTuples = []
        for i, item in enumerate(self.menu_items):
            result.extend(one_item(i, item))

        return result

    def _submenu(self, level: int = 0) -> Window:
        def get_text_fragments() -> StyleAndTextTuples:
            result: StyleAndTextTuples = []
            if level < len(self.selected_menu):
                menu = self._get_menu(level)
                if menu.children:
                    result.append(("class:menu", Border.TOP_LEFT))
                    result.append(("class:menu", Border.HORIZONTAL * (menu.width + 4)))
                    result.append(("class:menu", Border.TOP_RIGHT))
                    result.append(("", "\n"))
                    try:
                        selected_item = self.selected_menu[level + 1]
                    except IndexError:
                        selected_item = -1

                    def one_item(
                        i: int, item: MenuItem
                    ) -> Iterable[OneStyleAndTextTuple]:
                        def mouse_handler(mouse_event: MouseEvent) -> None:
                            if item.disabled:
                                # The arrow keys can't interact with menu items that are disabled.
                                # The mouse shouldn't be able to either.
                                return
                            hover = mouse_event.event_type == MouseEventType.MOUSE_MOVE
                            if (
                                mouse_event.event_type == MouseEventType.MOUSE_UP
                                or hover
                            ):
                                app = get_app()
                                if not hover and item.handler:
                                    app.layout.focus_last()
                                    item.handler()
                                else:
                                    self.selected_menu = self.selected_menu[
                                        : level + 1
                                    ] + [i]

                        if i == selected_item:
                            yield ("[SetCursorPosition]", "")
                            style = "class:menu-bar.selected-item"
                        else:
                            style = ""

                        yield ("class:menu", Border.VERTICAL)
                        if item.text == "-":
                            yield (
                                style + "class:menu-border",
                                f"{Border.HORIZONTAL * (menu.width + 3)}",
                                mouse_handler,
                            )
                        else:
                            yield (
                                style,
                                f" {item.text}".ljust(menu.width + 3),
                                mouse_handler,
                            )

                        if item.children:
                            yield (style, ">", mouse_handler)
                        else:
                            yield (style, " ", mouse_handler)

                        if i == selected_item:
                            yield ("[SetMenuPosition]", "")
                        yield ("class:menu", Border.VERTICAL)

                        yield ("", "\n")

                    for i, item in enumerate(menu.children):
                        result.extend(one_item(i, item))

                    result.append(("class:menu", Border.BOTTOM_LEFT))
                    result.append(("class:menu", Border.HORIZONTAL * (menu.width + 4)))
                    result.append(("class:menu", Border.BOTTOM_RIGHT))
            return result

        return Window(FormattedTextControl(get_text_fragments), style="class:menu")

    @property
    def floats(self) -> list[Float] | None:
        return self.container.floats

    def __pt_container__(self) -> Container:
        return self.container


class MenuItem:
    def __init__(
        self,
        text: str = "",
        handler: Callable[[], None] | None = None,
        children: list[MenuItem] | None = None,
        shortcut: Sequence[Keys | str] | None = None,
        disabled: bool = False,
    ) -> None:
        self.text = text
        self.handler = handler
        self.children = children or []
        self.shortcut = shortcut
        self.disabled = disabled
        self.selected_item = 0

    @property
    def width(self) -> int:
        if self.children:
            return max(get_cwidth(c.text) for c in self.children)
        else:
            return 0

# === NexusCore/openenv\Lib\site-packages\openai\__init__.py ===
# File generated from our OpenAPI spec by Stainless. See CONTRIBUTING.md for details.

from __future__ import annotations

import os as _os
import typing as _t
from typing_extensions import override

from . import types
from ._types import NOT_GIVEN, Omit, NoneType, NotGiven, Transport, ProxiesTypes
from ._utils import file_from_path
from ._client import Client, OpenAI, Stream, Timeout, Transport, AsyncClient, AsyncOpenAI, AsyncStream, RequestOptions
from ._models import BaseModel
from ._version import __title__, __version__
from ._response import APIResponse as APIResponse, AsyncAPIResponse as AsyncAPIResponse
from ._constants import DEFAULT_TIMEOUT, DEFAULT_MAX_RETRIES, DEFAULT_CONNECTION_LIMITS
from ._exceptions import (
    APIError,
    OpenAIError,
    ConflictError,
    NotFoundError,
    APIStatusError,
    RateLimitError,
    APITimeoutError,
    BadRequestError,
    APIConnectionError,
    AuthenticationError,
    InternalServerError,
    PermissionDeniedError,
    LengthFinishReasonError,
    UnprocessableEntityError,
    APIResponseValidationError,
    ContentFilterFinishReasonError,
)
from ._base_client import DefaultHttpxClient, DefaultAioHttpClient, DefaultAsyncHttpxClient
from ._utils._logs import setup_logging as _setup_logging
from ._legacy_response import HttpxBinaryResponseContent as HttpxBinaryResponseContent

__all__ = [
    "types",
    "__version__",
    "__title__",
    "NoneType",
    "Transport",
    "ProxiesTypes",
    "NotGiven",
    "NOT_GIVEN",
    "Omit",
    "OpenAIError",
    "APIError",
    "APIStatusError",
    "APITimeoutError",
    "APIConnectionError",
    "APIResponseValidationError",
    "BadRequestError",
    "AuthenticationError",
    "PermissionDeniedError",
    "NotFoundError",
    "ConflictError",
    "UnprocessableEntityError",
    "RateLimitError",
    "InternalServerError",
    "LengthFinishReasonError",
    "ContentFilterFinishReasonError",
    "Timeout",
    "RequestOptions",
    "Client",
    "AsyncClient",
    "Stream",
    "AsyncStream",
    "OpenAI",
    "AsyncOpenAI",
    "file_from_path",
    "BaseModel",
    "DEFAULT_TIMEOUT",
    "DEFAULT_MAX_RETRIES",
    "DEFAULT_CONNECTION_LIMITS",
    "DefaultHttpxClient",
    "DefaultAsyncHttpxClient",
    "DefaultAioHttpClient",
]

if not _t.TYPE_CHECKING:
    from ._utils._resources_proxy import resources as resources

from .lib import azure as _azure, pydantic_function_tool as pydantic_function_tool
from .version import VERSION as VERSION
from .lib.azure import AzureOpenAI as AzureOpenAI, AsyncAzureOpenAI as AsyncAzureOpenAI
from .lib._old_api import *
from .lib.streaming import (
    AssistantEventHandler as AssistantEventHandler,
    AsyncAssistantEventHandler as AsyncAssistantEventHandler,
)

_setup_logging()

# Update the __module__ attribute for exported symbols so that
# error messages point to this module instead of the module
# it was originally defined in, e.g.
# openai._exceptions.NotFoundError -> openai.NotFoundError
__locals = locals()
for __name in __all__:
    if not __name.startswith("__"):
        try:
            __locals[__name].__module__ = "openai"
        except (TypeError, AttributeError):
            # Some of our exported symbols are builtins which we can't set attributes for.
            pass

# ------ Module level client ------
import typing as _t
import typing_extensions as _te

import httpx as _httpx

from ._base_client import DEFAULT_TIMEOUT, DEFAULT_MAX_RETRIES

api_key: str | None = None

organization: str | None = None

project: str | None = None

base_url: str | _httpx.URL | None = None

timeout: float | Timeout | None = DEFAULT_TIMEOUT

max_retries: int = DEFAULT_MAX_RETRIES

default_headers: _t.Mapping[str, str] | None = None

default_query: _t.Mapping[str, object] | None = None

http_client: _httpx.Client | None = None

_ApiType = _te.Literal["openai", "azure"]

api_type: _ApiType | None = _t.cast(_ApiType, _os.environ.get("OPENAI_API_TYPE"))

api_version: str | None = _os.environ.get("OPENAI_API_VERSION")

azure_endpoint: str | None = _os.environ.get("AZURE_OPENAI_ENDPOINT")

azure_ad_token: str | None = _os.environ.get("AZURE_OPENAI_AD_TOKEN")

azure_ad_token_provider: _azure.AzureADTokenProvider | None = None


class _ModuleClient(OpenAI):
    # Note: we have to use type: ignores here as overriding class members
    # with properties is technically unsafe but it is fine for our use case

    @property  # type: ignore
    @override
    def api_key(self) -> str | None:
        return api_key

    @api_key.setter  # type: ignore
    def api_key(self, value: str | None) -> None:  # type: ignore
        global api_key

        api_key = value

    @property  # type: ignore
    @override
    def organization(self) -> str | None:
        return organization

    @organization.setter  # type: ignore
    def organization(self, value: str | None) -> None:  # type: ignore
        global organization

        organization = value

    @property  # type: ignore
    @override
    def project(self) -> str | None:
        return project

    @project.setter  # type: ignore
    def project(self, value: str | None) -> None:  # type: ignore
        global project

        project = value

    @property
    @override
    def base_url(self) -> _httpx.URL:
        if base_url is not None:
            return _httpx.URL(base_url)

        return super().base_url

    @base_url.setter
    def base_url(self, url: _httpx.URL | str) -> None:
        super().base_url = url  # type: ignore[misc]

    @property  # type: ignore
    @override
    def timeout(self) -> float | Timeout | None:
        return timeout

    @timeout.setter  # type: ignore
    def timeout(self, value: float | Timeout | None) -> None:  # type: ignore
        global timeout

        timeout = value

    @property  # type: ignore
    @override
    def max_retries(self) -> int:
        return max_retries

    @max_retries.setter  # type: ignore
    def max_retries(self, value: int) -> None:  # type: ignore
        global max_retries

        max_retries = value

    @property  # type: ignore
    @override
    def _custom_headers(self) -> _t.Mapping[str, str] | None:
        return default_headers

    @_custom_headers.setter  # type: ignore
    def _custom_headers(self, value: _t.Mapping[str, str] | None) -> None:  # type: ignore
        global default_headers

        default_headers = value

    @property  # type: ignore
    @override
    def _custom_query(self) -> _t.Mapping[str, object] | None:
        return default_query

    @_custom_query.setter  # type: ignore
    def _custom_query(self, value: _t.Mapping[str, object] | None) -> None:  # type: ignore
        global default_query

        default_query = value

    @property  # type: ignore
    @override
    def _client(self) -> _httpx.Client:
        return http_client or super()._client

    @_client.setter  # type: ignore
    def _client(self, value: _httpx.Client) -> None:  # type: ignore
        global http_client

        http_client = value


class _AzureModuleClient(_ModuleClient, AzureOpenAI):  # type: ignore
    ...


class _AmbiguousModuleClientUsageError(OpenAIError):
    def __init__(self) -> None:
        super().__init__(
            "Ambiguous use of module client; please set `openai.api_type` or the `OPENAI_API_TYPE` environment variable to `openai` or `azure`"
        )


def _has_openai_credentials() -> bool:
    return _os.environ.get("OPENAI_API_KEY") is not None


def _has_azure_credentials() -> bool:
    return azure_endpoint is not None or _os.environ.get("AZURE_OPENAI_API_KEY") is not None


def _has_azure_ad_credentials() -> bool:
    return (
        _os.environ.get("AZURE_OPENAI_AD_TOKEN") is not None
        or azure_ad_token is not None
        or azure_ad_token_provider is not None
    )


_client: OpenAI | None = None


def _load_client() -> OpenAI:  # type: ignore[reportUnusedFunction]
    global _client

    if _client is None:
        global api_type, azure_endpoint, azure_ad_token, api_version

        if azure_endpoint is None:
            azure_endpoint = _os.environ.get("AZURE_OPENAI_ENDPOINT")

        if azure_ad_token is None:
            azure_ad_token = _os.environ.get("AZURE_OPENAI_AD_TOKEN")

        if api_version is None:
            api_version = _os.environ.get("OPENAI_API_VERSION")

        if api_type is None:
            has_openai = _has_openai_credentials()
            has_azure = _has_azure_credentials()
            has_azure_ad = _has_azure_ad_credentials()

            if has_openai and (has_azure or has_azure_ad):
                raise _AmbiguousModuleClientUsageError()

            if (azure_ad_token is not None or azure_ad_token_provider is not None) and _os.environ.get(
                "AZURE_OPENAI_API_KEY"
            ) is not None:
                raise _AmbiguousModuleClientUsageError()

            if has_azure or has_azure_ad:
                api_type = "azure"
            else:
                api_type = "openai"

        if api_type == "azure":
            _client = _AzureModuleClient(  # type: ignore
                api_version=api_version,
                azure_endpoint=azure_endpoint,
                api_key=api_key,
                azure_ad_token=azure_ad_token,
                azure_ad_token_provider=azure_ad_token_provider,
                organization=organization,
                base_url=base_url,
                timeout=timeout,
                max_retries=max_retries,
                default_headers=default_headers,
                default_query=default_query,
                http_client=http_client,
            )
            return _client

        _client = _ModuleClient(
            api_key=api_key,
            organization=organization,
            project=project,
            base_url=base_url,
            timeout=timeout,
            max_retries=max_retries,
            default_headers=default_headers,
            default_query=default_query,
            http_client=http_client,
        )
        return _client

    return _client


def _reset_client() -> None:  # type: ignore[reportUnusedFunction]
    global _client

    _client = None


from ._module_client import (
    beta as beta,
    chat as chat,
    audio as audio,
    evals as evals,
    files as files,
    images as images,
    models as models,
    batches as batches,
    uploads as uploads,
    responses as responses,
    containers as containers,
    embeddings as embeddings,
    completions as completions,
    fine_tuning as fine_tuning,
    moderations as moderations,
    vector_stores as vector_stores,
)

# === NexusCore/openenv\Lib\site-packages\websocket\_http.py ===
"""
_http.py
websocket - WebSocket client library for Python

Copyright 2024 engn33r

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""
import errno
import os
import socket
from base64 import encodebytes as base64encode

from ._exceptions import (
    WebSocketAddressException,
    WebSocketException,
    WebSocketProxyException,
)
from ._logging import debug, dump, trace
from ._socket import DEFAULT_SOCKET_OPTION, recv_line, send
from ._ssl_compat import HAVE_SSL, ssl
from ._url import get_proxy_info, parse_url

__all__ = ["proxy_info", "connect", "read_headers"]

try:
    from python_socks._errors import *
    from python_socks._types import ProxyType
    from python_socks.sync import Proxy

    HAVE_PYTHON_SOCKS = True
except:
    HAVE_PYTHON_SOCKS = False

    class ProxyError(Exception):
        pass

    class ProxyTimeoutError(Exception):
        pass

    class ProxyConnectionError(Exception):
        pass


class proxy_info:
    def __init__(self, **options):
        self.proxy_host = options.get("http_proxy_host", None)
        if self.proxy_host:
            self.proxy_port = options.get("http_proxy_port", 0)
            self.auth = options.get("http_proxy_auth", None)
            self.no_proxy = options.get("http_no_proxy", None)
            self.proxy_protocol = options.get("proxy_type", "http")
            # Note: If timeout not specified, default python-socks timeout is 60 seconds
            self.proxy_timeout = options.get("http_proxy_timeout", None)
            if self.proxy_protocol not in [
                "http",
                "socks4",
                "socks4a",
                "socks5",
                "socks5h",
            ]:
                raise ProxyError(
                    "Only http, socks4, socks5 proxy protocols are supported"
                )
        else:
            self.proxy_port = 0
            self.auth = None
            self.no_proxy = None
            self.proxy_protocol = "http"


def _start_proxied_socket(url: str, options, proxy) -> tuple:
    if not HAVE_PYTHON_SOCKS:
        raise WebSocketException(
            "Python Socks is needed for SOCKS proxying but is not available"
        )

    hostname, port, resource, is_secure = parse_url(url)

    if proxy.proxy_protocol == "socks4":
        rdns = False
        proxy_type = ProxyType.SOCKS4
    # socks4a sends DNS through proxy
    elif proxy.proxy_protocol == "socks4a":
        rdns = True
        proxy_type = ProxyType.SOCKS4
    elif proxy.proxy_protocol == "socks5":
        rdns = False
        proxy_type = ProxyType.SOCKS5
    # socks5h sends DNS through proxy
    elif proxy.proxy_protocol == "socks5h":
        rdns = True
        proxy_type = ProxyType.SOCKS5

    ws_proxy = Proxy.create(
        proxy_type=proxy_type,
        host=proxy.proxy_host,
        port=int(proxy.proxy_port),
        username=proxy.auth[0] if proxy.auth else None,
        password=proxy.auth[1] if proxy.auth else None,
        rdns=rdns,
    )

    sock = ws_proxy.connect(hostname, port, timeout=proxy.proxy_timeout)

    if is_secure:
        if HAVE_SSL:
            sock = _ssl_socket(sock, options.sslopt, hostname)
        else:
            raise WebSocketException("SSL not available.")

    return sock, (hostname, port, resource)


def connect(url: str, options, proxy, socket):
    # Use _start_proxied_socket() only for socks4 or socks5 proxy
    # Use _tunnel() for http proxy
    # TODO: Use python-socks for http protocol also, to standardize flow
    if proxy.proxy_host and not socket and proxy.proxy_protocol != "http":
        return _start_proxied_socket(url, options, proxy)

    hostname, port_from_url, resource, is_secure = parse_url(url)

    if socket:
        return socket, (hostname, port_from_url, resource)

    addrinfo_list, need_tunnel, auth = _get_addrinfo_list(
        hostname, port_from_url, is_secure, proxy
    )
    if not addrinfo_list:
        raise WebSocketException(f"Host not found.: {hostname}:{port_from_url}")

    sock = None
    try:
        sock = _open_socket(addrinfo_list, options.sockopt, options.timeout)
        if need_tunnel:
            sock = _tunnel(sock, hostname, port_from_url, auth)

        if is_secure:
            if HAVE_SSL:
                sock = _ssl_socket(sock, options.sslopt, hostname)
            else:
                raise WebSocketException("SSL not available.")

        return sock, (hostname, port_from_url, resource)
    except:
        if sock:
            sock.close()
        raise


def _get_addrinfo_list(hostname, port: int, is_secure: bool, proxy) -> tuple:
    phost, pport, pauth = get_proxy_info(
        hostname,
        is_secure,
        proxy.proxy_host,
        proxy.proxy_port,
        proxy.auth,
        proxy.no_proxy,
    )
    try:
        # when running on windows 10, getaddrinfo without socktype returns a socktype 0.
        # This generates an error exception: `_on_error: exception Socket type must be stream or datagram, not 0`
        # or `OSError: [Errno 22] Invalid argument` when creating socket. Force the socket type to SOCK_STREAM.
        if not phost:
            addrinfo_list = socket.getaddrinfo(
                hostname, port, 0, socket.SOCK_STREAM, socket.SOL_TCP
            )
            return addrinfo_list, False, None
        else:
            pport = pport and pport or 80
            # when running on windows 10, the getaddrinfo used above
            # returns a socktype 0. This generates an error exception:
            # _on_error: exception Socket type must be stream or datagram, not 0
            # Force the socket type to SOCK_STREAM
            addrinfo_list = socket.getaddrinfo(
                phost, pport, 0, socket.SOCK_STREAM, socket.SOL_TCP
            )
            return addrinfo_list, True, pauth
    except socket.gaierror as e:
        raise WebSocketAddressException(e)


def _open_socket(addrinfo_list, sockopt, timeout):
    err = None
    for addrinfo in addrinfo_list:
        family, socktype, proto = addrinfo[:3]
        sock = socket.socket(family, socktype, proto)
        sock.settimeout(timeout)
        for opts in DEFAULT_SOCKET_OPTION:
            sock.setsockopt(*opts)
        for opts in sockopt:
            sock.setsockopt(*opts)

        address = addrinfo[4]
        err = None
        while not err:
            try:
                sock.connect(address)
            except socket.error as error:
                sock.close()
                error.remote_ip = str(address[0])
                try:
                    eConnRefused = (
                        errno.ECONNREFUSED,
                        errno.WSAECONNREFUSED,
                        errno.ENETUNREACH,
                    )
                except AttributeError:
                    eConnRefused = (errno.ECONNREFUSED, errno.ENETUNREACH)
                if error.errno not in eConnRefused:
                    raise error
                err = error
                continue
            else:
                break
        else:
            continue
        break
    else:
        if err:
            raise err

    return sock


def _wrap_sni_socket(sock: socket.socket, sslopt: dict, hostname, check_hostname):
    context = sslopt.get("context", None)
    if not context:
        context = ssl.SSLContext(sslopt.get("ssl_version", ssl.PROTOCOL_TLS_CLIENT))
        # Non default context need to manually enable SSLKEYLOGFILE support by setting the keylog_filename attribute.
        # For more details see also:
        # * https://docs.python.org/3.8/library/ssl.html?highlight=sslkeylogfile#context-creation
        # * https://docs.python.org/3.8/library/ssl.html?highlight=sslkeylogfile#ssl.SSLContext.keylog_filename
        context.keylog_filename = os.environ.get("SSLKEYLOGFILE", None)

        if sslopt.get("cert_reqs", ssl.CERT_NONE) != ssl.CERT_NONE:
            cafile = sslopt.get("ca_certs", None)
            capath = sslopt.get("ca_cert_path", None)
            if cafile or capath:
                context.load_verify_locations(cafile=cafile, capath=capath)
            elif hasattr(context, "load_default_certs"):
                context.load_default_certs(ssl.Purpose.SERVER_AUTH)
        if sslopt.get("certfile", None):
            context.load_cert_chain(
                sslopt["certfile"],
                sslopt.get("keyfile", None),
                sslopt.get("password", None),
            )

        # Python 3.10 switch to PROTOCOL_TLS_CLIENT defaults to "cert_reqs = ssl.CERT_REQUIRED" and "check_hostname = True"
        # If both disabled, set check_hostname before verify_mode
        # see https://github.com/liris/websocket-client/commit/b96a2e8fa765753e82eea531adb19716b52ca3ca#commitcomment-10803153
        if sslopt.get("cert_reqs", ssl.CERT_NONE) == ssl.CERT_NONE and not sslopt.get(
            "check_hostname", False
        ):
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE
        else:
            context.check_hostname = sslopt.get("check_hostname", True)
            context.verify_mode = sslopt.get("cert_reqs", ssl.CERT_REQUIRED)

        if "ciphers" in sslopt:
            context.set_ciphers(sslopt["ciphers"])
        if "cert_chain" in sslopt:
            certfile, keyfile, password = sslopt["cert_chain"]
            context.load_cert_chain(certfile, keyfile, password)
        if "ecdh_curve" in sslopt:
            context.set_ecdh_curve(sslopt["ecdh_curve"])

    return context.wrap_socket(
        sock,
        do_handshake_on_connect=sslopt.get("do_handshake_on_connect", True),
        suppress_ragged_eofs=sslopt.get("suppress_ragged_eofs", True),
        server_hostname=hostname,
    )


def _ssl_socket(sock: socket.socket, user_sslopt: dict, hostname):
    sslopt: dict = {"cert_reqs": ssl.CERT_REQUIRED}
    sslopt.update(user_sslopt)

    cert_path = os.environ.get("WEBSOCKET_CLIENT_CA_BUNDLE")
    if (
        cert_path
        and os.path.isfile(cert_path)
        and user_sslopt.get("ca_certs", None) is None
    ):
        sslopt["ca_certs"] = cert_path
    elif (
        cert_path
        and os.path.isdir(cert_path)
        and user_sslopt.get("ca_cert_path", None) is None
    ):
        sslopt["ca_cert_path"] = cert_path

    if sslopt.get("server_hostname", None):
        hostname = sslopt["server_hostname"]

    check_hostname = sslopt.get("check_hostname", True)
    sock = _wrap_sni_socket(sock, sslopt, hostname, check_hostname)

    return sock


def _tunnel(sock: socket.socket, host, port: int, auth) -> socket.socket:
    debug("Connecting proxy...")
    connect_header = f"CONNECT {host}:{port} HTTP/1.1\r\n"
    connect_header += f"Host: {host}:{port}\r\n"

    # TODO: support digest auth.
    if auth and auth[0]:
        auth_str = auth[0]
        if auth[1]:
            auth_str += f":{auth[1]}"
        encoded_str = base64encode(auth_str.encode()).strip().decode().replace("\n", "")
        connect_header += f"Proxy-Authorization: Basic {encoded_str}\r\n"
    connect_header += "\r\n"
    dump("request header", connect_header)

    send(sock, connect_header)

    try:
        status, _, _ = read_headers(sock)
    except Exception as e:
        raise WebSocketProxyException(str(e))

    if status != 200:
        raise WebSocketProxyException(f"failed CONNECT via proxy status: {status}")

    return sock


def read_headers(sock: socket.socket) -> tuple:
    status = None
    status_message = None
    headers: dict = {}
    trace("--- response header ---")

    while True:
        line = recv_line(sock)
        line = line.decode("utf-8").strip()
        if not line:
            break
        trace(line)
        if not status:
            status_info = line.split(" ", 2)
            status = int(status_info[1])
            if len(status_info) > 2:
                status_message = status_info[2]
        else:
            kv = line.split(":", 1)
            if len(kv) != 2:
                raise WebSocketException("Invalid header")
            key, value = kv
            if key.lower() == "set-cookie" and headers.get("set-cookie"):
                headers["set-cookie"] = headers.get("set-cookie") + "; " + value.strip()
            else:
                headers[key.lower()] = value.strip()

    trace("-----------------------")

    return status, headers, status_message

# === NexusCore/openenv\Lib\site-packages\litellm\llms\cohere\chat\transformation.py ===
import json
import time
from typing import TYPE_CHECKING, Any, AsyncIterator, Iterator, List, Optional, Union

import httpx

import litellm
from litellm.litellm_core_utils.prompt_templates.factory import cohere_messages_pt_v2
from litellm.llms.base_llm.chat.transformation import BaseConfig, BaseLLMException
from litellm.types.llms.openai import AllMessageValues
from litellm.types.utils import ModelResponse, Usage

from ..common_utils import ModelResponseIterator as CohereModelResponseIterator
from ..common_utils import validate_environment as cohere_validate_environment

if TYPE_CHECKING:
    from litellm.litellm_core_utils.litellm_logging import Logging as _LiteLLMLoggingObj

    LiteLLMLoggingObj = _LiteLLMLoggingObj
else:
    LiteLLMLoggingObj = Any


class CohereError(BaseLLMException):
    def __init__(
        self,
        status_code: int,
        message: str,
        headers: Optional[httpx.Headers] = None,
    ):
        self.status_code = status_code
        self.message = message
        self.request = httpx.Request(method="POST", url="https://api.cohere.ai/v1/chat")
        self.response = httpx.Response(status_code=status_code, request=self.request)
        super().__init__(
            status_code=status_code,
            message=message,
            headers=headers,
        )


class CohereChatConfig(BaseConfig):
    """
    Configuration class for Cohere's API interface.

    Args:
        preamble (str, optional): When specified, the default Cohere preamble will be replaced with the provided one.
        chat_history (List[Dict[str, str]], optional): A list of previous messages between the user and the model.
        generation_id (str, optional): Unique identifier for the generated reply.
        response_id (str, optional): Unique identifier for the response.
        conversation_id (str, optional): An alternative to chat_history, creates or resumes a persisted conversation.
        prompt_truncation (str, optional): Dictates how the prompt will be constructed. Options: 'AUTO', 'AUTO_PRESERVE_ORDER', 'OFF'.
        connectors (List[Dict[str, str]], optional): List of connectors (e.g., web-search) to enrich the model's reply.
        search_queries_only (bool, optional): When true, the response will only contain a list of generated search queries.
        documents (List[Dict[str, str]], optional): A list of relevant documents that the model can cite.
        temperature (float, optional): A non-negative float that tunes the degree of randomness in generation.
        max_tokens [DEPRECATED - use max_completion_tokens] (int, optional): The maximum number of tokens the model will generate as part of the response.
        max_completion_tokens (int, optional): The maximum number of tokens the model will generate as part of the response.
        k (int, optional): Ensures only the top k most likely tokens are considered for generation at each step.
        p (float, optional): Ensures that only the most likely tokens, with total probability mass of p, are considered for generation.
        frequency_penalty (float, optional): Used to reduce repetitiveness of generated tokens.
        presence_penalty (float, optional): Used to reduce repetitiveness of generated tokens.
        tools (List[Dict[str, str]], optional): A list of available tools (functions) that the model may suggest invoking.
        tool_results (List[Dict[str, Any]], optional): A list of results from invoking tools.
        seed (int, optional): A seed to assist reproducibility of the model's response.
    """

    preamble: Optional[str] = None
    chat_history: Optional[list] = None
    generation_id: Optional[str] = None
    response_id: Optional[str] = None
    conversation_id: Optional[str] = None
    prompt_truncation: Optional[str] = None
    connectors: Optional[list] = None
    search_queries_only: Optional[bool] = None
    documents: Optional[list] = None
    temperature: Optional[int] = None
    max_tokens: Optional[int] = None
    max_completion_tokens: Optional[int] = None
    k: Optional[int] = None
    p: Optional[int] = None
    frequency_penalty: Optional[int] = None
    presence_penalty: Optional[int] = None
    tools: Optional[list] = None
    tool_results: Optional[list] = None
    seed: Optional[int] = None

    def __init__(
        self,
        preamble: Optional[str] = None,
        chat_history: Optional[list] = None,
        generation_id: Optional[str] = None,
        response_id: Optional[str] = None,
        conversation_id: Optional[str] = None,
        prompt_truncation: Optional[str] = None,
        connectors: Optional[list] = None,
        search_queries_only: Optional[bool] = None,
        documents: Optional[list] = None,
        temperature: Optional[int] = None,
        max_tokens: Optional[int] = None,
        max_completion_tokens: Optional[int] = None,
        k: Optional[int] = None,
        p: Optional[int] = None,
        frequency_penalty: Optional[int] = None,
        presence_penalty: Optional[int] = None,
        tools: Optional[list] = None,
        tool_results: Optional[list] = None,
        seed: Optional[int] = None,
    ) -> None:
        locals_ = locals().copy()
        for key, value in locals_.items():
            if key != "self" and value is not None:
                setattr(self.__class__, key, value)

    def validate_environment(
        self,
        headers: dict,
        model: str,
        messages: List[AllMessageValues],
        optional_params: dict,
        litellm_params: dict,
        api_key: Optional[str] = None,
        api_base: Optional[str] = None,
    ) -> dict:
        return cohere_validate_environment(
            headers=headers,
            model=model,
            messages=messages,
            optional_params=optional_params,
            api_key=api_key,
        )

    def get_supported_openai_params(self, model: str) -> List[str]:
        return [
            "stream",
            "temperature",
            "max_tokens",
            "max_completion_tokens",
            "top_p",
            "frequency_penalty",
            "presence_penalty",
            "stop",
            "n",
            "tools",
            "tool_choice",
            "seed",
            "extra_headers",
        ]

    def map_openai_params(
        self,
        non_default_params: dict,
        optional_params: dict,
        model: str,
        drop_params: bool,
    ) -> dict:
        for param, value in non_default_params.items():
            if param == "stream":
                optional_params["stream"] = value
            if param == "temperature":
                optional_params["temperature"] = value
            if param == "max_tokens":
                optional_params["max_tokens"] = value
            if param == "max_completion_tokens":
                optional_params["max_tokens"] = value
            if param == "n":
                optional_params["num_generations"] = value
            if param == "top_p":
                optional_params["p"] = value
            if param == "frequency_penalty":
                optional_params["frequency_penalty"] = value
            if param == "presence_penalty":
                optional_params["presence_penalty"] = value
            if param == "stop":
                optional_params["stop_sequences"] = value
            if param == "tools":
                optional_params["tools"] = value
            if param == "seed":
                optional_params["seed"] = value
        return optional_params

    def transform_request(
        self,
        model: str,
        messages: List[AllMessageValues],
        optional_params: dict,
        litellm_params: dict,
        headers: dict,
    ) -> dict:
        ## Load Config
        for k, v in litellm.CohereChatConfig.get_config().items():
            if (
                k not in optional_params
            ):  # completion(top_k=3) > cohere_config(top_k=3) <- allows for dynamic variables to be passed in
                optional_params[k] = v

        most_recent_message, chat_history = cohere_messages_pt_v2(
            messages=messages, model=model, llm_provider="cohere_chat"
        )

        ## Handle Tool Calling
        if "tools" in optional_params:
            _is_function_call = True
            cohere_tools = self._construct_cohere_tool(tools=optional_params["tools"])
            optional_params["tools"] = cohere_tools
        if isinstance(most_recent_message, dict):
            optional_params["tool_results"] = [most_recent_message]
        elif isinstance(most_recent_message, str):
            optional_params["message"] = most_recent_message

        ## check if chat history message is 'user' and 'tool_results' is given -> force_single_step=True, else cohere api fails
        if len(chat_history) > 0 and chat_history[-1]["role"] == "USER":
            optional_params["force_single_step"] = True

        return optional_params

    def transform_response(
        self,
        model: str,
        raw_response: httpx.Response,
        model_response: ModelResponse,
        logging_obj: LiteLLMLoggingObj,
        request_data: dict,
        messages: List[AllMessageValues],
        optional_params: dict,
        litellm_params: dict,
        encoding: Any,
        api_key: Optional[str] = None,
        json_mode: Optional[bool] = None,
    ) -> ModelResponse:
        try:
            raw_response_json = raw_response.json()
            model_response.choices[0].message.content = raw_response_json["text"]  # type: ignore
        except Exception:
            raise CohereError(
                message=raw_response.text, status_code=raw_response.status_code
            )

        ## ADD CITATIONS
        if "citations" in raw_response_json:
            setattr(model_response, "citations", raw_response_json["citations"])

        ## Tool calling response
        cohere_tools_response = raw_response_json.get("tool_calls", None)
        if cohere_tools_response is not None and cohere_tools_response != []:
            # convert cohere_tools_response to OpenAI response format
            tool_calls = []
            for tool in cohere_tools_response:
                function_name = tool.get("name", "")
                generation_id = tool.get("generation_id", "")
                parameters = tool.get("parameters", {})
                tool_call = {
                    "id": f"call_{generation_id}",
                    "type": "function",
                    "function": {
                        "name": function_name,
                        "arguments": json.dumps(parameters),
                    },
                }
                tool_calls.append(tool_call)
            _message = litellm.Message(
                tool_calls=tool_calls,
                content=None,
            )
            model_response.choices[0].message = _message  # type: ignore

        ## CALCULATING USAGE - use cohere `billed_units` for returning usage
        billed_units = raw_response_json.get("meta", {}).get("billed_units", {})

        prompt_tokens = billed_units.get("input_tokens", 0)
        completion_tokens = billed_units.get("output_tokens", 0)

        model_response.created = int(time.time())
        model_response.model = model
        usage = Usage(
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=prompt_tokens + completion_tokens,
        )
        setattr(model_response, "usage", usage)
        return model_response

    def _construct_cohere_tool(
        self,
        tools: Optional[list] = None,
    ):
        if tools is None:
            tools = []
        cohere_tools = []
        for tool in tools:
            cohere_tool = self._translate_openai_tool_to_cohere(tool)
            cohere_tools.append(cohere_tool)
        return cohere_tools

    def _translate_openai_tool_to_cohere(
        self,
        openai_tool: dict,
    ):
        # cohere tools look like this
        """
        {
        "name": "query_daily_sales_report",
        "description": "Connects to a database to retrieve overall sales volumes and sales information for a given day.",
        "parameter_definitions": {
            "day": {
                "description": "Retrieves sales data for this day, formatted as YYYY-MM-DD.",
                "type": "str",
                "required": True
            }
        }
        }
        """

        # OpenAI tools look like this
        """
        {
            "type": "function",
            "function": {
                "name": "get_current_weather",
                "description": "Get the current weather in a given location",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "location": {
                            "type": "string",
                            "description": "The city and state, e.g. San Francisco, CA",
                        },
                        "unit": {"type": "string", "enum": ["celsius", "fahrenheit"]},
                    },
                    "required": ["location"],
                },
            },
        }
        """
        cohere_tool = {
            "name": openai_tool["function"]["name"],
            "description": openai_tool["function"]["description"],
            "parameter_definitions": {},
        }

        for param_name, param_def in openai_tool["function"]["parameters"][
            "properties"
        ].items():
            required_params = (
                openai_tool.get("function", {})
                .get("parameters", {})
                .get("required", [])
            )
            cohere_param_def = {
                "description": param_def.get("description", ""),
                "type": param_def.get("type", ""),
                "required": param_name in required_params,
            }
            cohere_tool["parameter_definitions"][param_name] = cohere_param_def

        return cohere_tool

    def get_model_response_iterator(
        self,
        streaming_response: Union[Iterator[str], AsyncIterator[str], ModelResponse],
        sync_stream: bool,
        json_mode: Optional[bool] = False,
    ):
        return CohereModelResponseIterator(
            streaming_response=streaming_response,
            sync_stream=sync_stream,
            json_mode=json_mode,
        )

    def get_error_class(
        self, error_message: str, status_code: int, headers: Union[dict, httpx.Headers]
    ) -> BaseLLMException:
        return CohereError(status_code=status_code, message=error_message)

# === NexusCore/openenv\Lib\site-packages\nltk\corpus\reader\pl196x.py ===
# Natural Language Toolkit:
#
# Copyright (C) 2001-2024 NLTK Project
# Author: Piotr Kasprzyk <p.j.kasprzyk@gmail.com>
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT

from nltk.corpus.reader.api import *
from nltk.corpus.reader.xmldocs import XMLCorpusReader

PARA = re.compile(r"<p(?: [^>]*){0,1}>(.*?)</p>")
SENT = re.compile(r"<s(?: [^>]*){0,1}>(.*?)</s>")

TAGGEDWORD = re.compile(r"<([wc](?: [^>]*){0,1}>)(.*?)</[wc]>")
WORD = re.compile(r"<[wc](?: [^>]*){0,1}>(.*?)</[wc]>")

TYPE = re.compile(r'type="(.*?)"')
ANA = re.compile(r'ana="(.*?)"')

TEXTID = re.compile(r'text id="(.*?)"')


class TEICorpusView(StreamBackedCorpusView):
    def __init__(
        self,
        corpus_file,
        tagged,
        group_by_sent,
        group_by_para,
        tagset=None,
        head_len=0,
        textids=None,
    ):
        self._tagged = tagged
        self._textids = textids

        self._group_by_sent = group_by_sent
        self._group_by_para = group_by_para
        # WARNING -- skip header
        StreamBackedCorpusView.__init__(self, corpus_file, startpos=head_len)

    _pagesize = 4096

    def read_block(self, stream):
        block = stream.readlines(self._pagesize)
        block = concat(block)
        while (block.count("<text id") > block.count("</text>")) or block.count(
            "<text id"
        ) == 0:
            tmp = stream.readline()
            if len(tmp) <= 0:
                break
            block += tmp

        block = block.replace("\n", "")

        textids = TEXTID.findall(block)
        if self._textids:
            for tid in textids:
                if tid not in self._textids:
                    beg = block.find(tid) - 1
                    end = block[beg:].find("</text>") + len("</text>")
                    block = block[:beg] + block[beg + end :]

        output = []
        for para_str in PARA.findall(block):
            para = []
            for sent_str in SENT.findall(para_str):
                if not self._tagged:
                    sent = WORD.findall(sent_str)
                else:
                    sent = list(map(self._parse_tag, TAGGEDWORD.findall(sent_str)))
                if self._group_by_sent:
                    para.append(sent)
                else:
                    para.extend(sent)
            if self._group_by_para:
                output.append(para)
            else:
                output.extend(para)
        return output

    def _parse_tag(self, tag_word_tuple):
        (tag, word) = tag_word_tuple
        if tag.startswith("w"):
            tag = ANA.search(tag).group(1)
        else:  # tag.startswith('c')
            tag = TYPE.search(tag).group(1)
        return word, tag


class Pl196xCorpusReader(CategorizedCorpusReader, XMLCorpusReader):
    head_len = 2770

    def __init__(self, *args, **kwargs):
        if "textid_file" in kwargs:
            self._textids = kwargs["textid_file"]
        else:
            self._textids = None

        XMLCorpusReader.__init__(self, *args)
        CategorizedCorpusReader.__init__(self, kwargs)

        self._init_textids()

    def _init_textids(self):
        self._f2t = defaultdict(list)
        self._t2f = defaultdict(list)
        if self._textids is not None:
            with open(self._textids) as fp:
                for line in fp:
                    line = line.strip()
                    file_id, text_ids = line.split(" ", 1)
                    if file_id not in self.fileids():
                        raise ValueError(
                            "In text_id mapping file %s: %s not found"
                            % (self._textids, file_id)
                        )
                    for text_id in text_ids.split(self._delimiter):
                        self._add_textids(file_id, text_id)

    def _add_textids(self, file_id, text_id):
        self._f2t[file_id].append(text_id)
        self._t2f[text_id].append(file_id)

    def _resolve(self, fileids, categories, textids=None):
        tmp = None
        if (
            len(
                list(
                    filter(
                        lambda accessor: accessor is None,
                        (fileids, categories, textids),
                    )
                )
            )
            != 1
        ):
            raise ValueError(
                "Specify exactly one of: fileids, " "categories or textids"
            )

        if fileids is not None:
            return fileids, None

        if categories is not None:
            return self.fileids(categories), None

        if textids is not None:
            if isinstance(textids, str):
                textids = [textids]
            files = sum((self._t2f[t] for t in textids), [])
            tdict = dict()
            for f in files:
                tdict[f] = set(self._f2t[f]) & set(textids)
            return files, tdict

    def decode_tag(self, tag):
        # to be implemented
        return tag

    def textids(self, fileids=None, categories=None):
        """
        In the pl196x corpus each category is stored in single
        file and thus both methods provide identical functionality. In order
        to accommodate finer granularity, a non-standard textids() method was
        implemented. All the main functions can be supplied with a list
        of required chunks---giving much more control to the user.
        """
        fileids, _ = self._resolve(fileids, categories)
        if fileids is None:
            return sorted(self._t2f)

        if isinstance(fileids, str):
            fileids = [fileids]
        return sorted(sum((self._f2t[d] for d in fileids), []))

    def words(self, fileids=None, categories=None, textids=None):
        fileids, textids = self._resolve(fileids, categories, textids)
        if fileids is None:
            fileids = self._fileids
        elif isinstance(fileids, str):
            fileids = [fileids]

        if textids:
            return concat(
                [
                    TEICorpusView(
                        self.abspath(fileid),
                        False,
                        False,
                        False,
                        head_len=self.head_len,
                        textids=textids[fileid],
                    )
                    for fileid in fileids
                ]
            )
        else:
            return concat(
                [
                    TEICorpusView(
                        self.abspath(fileid),
                        False,
                        False,
                        False,
                        head_len=self.head_len,
                    )
                    for fileid in fileids
                ]
            )

    def sents(self, fileids=None, categories=None, textids=None):
        fileids, textids = self._resolve(fileids, categories, textids)
        if fileids is None:
            fileids = self._fileids
        elif isinstance(fileids, str):
            fileids = [fileids]

        if textids:
            return concat(
                [
                    TEICorpusView(
                        self.abspath(fileid),
                        False,
                        True,
                        False,
                        head_len=self.head_len,
                        textids=textids[fileid],
                    )
                    for fileid in fileids
                ]
            )
        else:
            return concat(
                [
                    TEICorpusView(
                        self.abspath(fileid), False, True, False, head_len=self.head_len
                    )
                    for fileid in fileids
                ]
            )

    def paras(self, fileids=None, categories=None, textids=None):
        fileids, textids = self._resolve(fileids, categories, textids)
        if fileids is None:
            fileids = self._fileids
        elif isinstance(fileids, str):
            fileids = [fileids]

        if textids:
            return concat(
                [
                    TEICorpusView(
                        self.abspath(fileid),
                        False,
                        True,
                        True,
                        head_len=self.head_len,
                        textids=textids[fileid],
                    )
                    for fileid in fileids
                ]
            )
        else:
            return concat(
                [
                    TEICorpusView(
                        self.abspath(fileid), False, True, True, head_len=self.head_len
                    )
                    for fileid in fileids
                ]
            )

    def tagged_words(self, fileids=None, categories=None, textids=None):
        fileids, textids = self._resolve(fileids, categories, textids)
        if fileids is None:
            fileids = self._fileids
        elif isinstance(fileids, str):
            fileids = [fileids]

        if textids:
            return concat(
                [
                    TEICorpusView(
                        self.abspath(fileid),
                        True,
                        False,
                        False,
                        head_len=self.head_len,
                        textids=textids[fileid],
                    )
                    for fileid in fileids
                ]
            )
        else:
            return concat(
                [
                    TEICorpusView(
                        self.abspath(fileid), True, False, False, head_len=self.head_len
                    )
                    for fileid in fileids
                ]
            )

    def tagged_sents(self, fileids=None, categories=None, textids=None):
        fileids, textids = self._resolve(fileids, categories, textids)
        if fileids is None:
            fileids = self._fileids
        elif isinstance(fileids, str):
            fileids = [fileids]

        if textids:
            return concat(
                [
                    TEICorpusView(
                        self.abspath(fileid),
                        True,
                        True,
                        False,
                        head_len=self.head_len,
                        textids=textids[fileid],
                    )
                    for fileid in fileids
                ]
            )
        else:
            return concat(
                [
                    TEICorpusView(
                        self.abspath(fileid), True, True, False, head_len=self.head_len
                    )
                    for fileid in fileids
                ]
            )

    def tagged_paras(self, fileids=None, categories=None, textids=None):
        fileids, textids = self._resolve(fileids, categories, textids)
        if fileids is None:
            fileids = self._fileids
        elif isinstance(fileids, str):
            fileids = [fileids]

        if textids:
            return concat(
                [
                    TEICorpusView(
                        self.abspath(fileid),
                        True,
                        True,
                        True,
                        head_len=self.head_len,
                        textids=textids[fileid],
                    )
                    for fileid in fileids
                ]
            )
        else:
            return concat(
                [
                    TEICorpusView(
                        self.abspath(fileid), True, True, True, head_len=self.head_len
                    )
                    for fileid in fileids
                ]
            )

    def xml(self, fileids=None, categories=None):
        fileids, _ = self._resolve(fileids, categories)
        if len(fileids) == 1:
            return XMLCorpusReader.xml(self, fileids[0])
        else:
            raise TypeError("Expected a single file")

# === NexusCore/openenv\Lib\site-packages\pydantic\_internal\_config.py ===
from __future__ import annotations as _annotations

import warnings
from contextlib import contextmanager
from re import Pattern
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Literal,
    cast,
)

from pydantic_core import core_schema
from typing_extensions import Self

from ..aliases import AliasGenerator
from ..config import ConfigDict, ExtraValues, JsonDict, JsonEncoder, JsonSchemaExtraCallable
from ..errors import PydanticUserError
from ..warnings import PydanticDeprecatedSince20, PydanticDeprecatedSince210

if not TYPE_CHECKING:
    # See PyCharm issues https://youtrack.jetbrains.com/issue/PY-21915
    # and https://youtrack.jetbrains.com/issue/PY-51428
    DeprecationWarning = PydanticDeprecatedSince20

if TYPE_CHECKING:
    from .._internal._schema_generation_shared import GenerateSchema
    from ..fields import ComputedFieldInfo, FieldInfo

DEPRECATION_MESSAGE = 'Support for class-based `config` is deprecated, use ConfigDict instead.'


class ConfigWrapper:
    """Internal wrapper for Config which exposes ConfigDict items as attributes."""

    __slots__ = ('config_dict',)

    config_dict: ConfigDict

    # all annotations are copied directly from ConfigDict, and should be kept up to date, a test will fail if they
    # stop matching
    title: str | None
    str_to_lower: bool
    str_to_upper: bool
    str_strip_whitespace: bool
    str_min_length: int
    str_max_length: int | None
    extra: ExtraValues | None
    frozen: bool
    populate_by_name: bool
    use_enum_values: bool
    validate_assignment: bool
    arbitrary_types_allowed: bool
    from_attributes: bool
    # whether to use the actual key provided in the data (e.g. alias or first alias for "field required" errors) instead of field_names
    # to construct error `loc`s, default `True`
    loc_by_alias: bool
    alias_generator: Callable[[str], str] | AliasGenerator | None
    model_title_generator: Callable[[type], str] | None
    field_title_generator: Callable[[str, FieldInfo | ComputedFieldInfo], str] | None
    ignored_types: tuple[type, ...]
    allow_inf_nan: bool
    json_schema_extra: JsonDict | JsonSchemaExtraCallable | None
    json_encoders: dict[type[object], JsonEncoder] | None

    # new in V2
    strict: bool
    # whether instances of models and dataclasses (including subclass instances) should re-validate, default 'never'
    revalidate_instances: Literal['always', 'never', 'subclass-instances']
    ser_json_timedelta: Literal['iso8601', 'float']
    ser_json_bytes: Literal['utf8', 'base64', 'hex']
    val_json_bytes: Literal['utf8', 'base64', 'hex']
    ser_json_inf_nan: Literal['null', 'constants', 'strings']
    # whether to validate default values during validation, default False
    validate_default: bool
    validate_return: bool
    protected_namespaces: tuple[str | Pattern[str], ...]
    hide_input_in_errors: bool
    defer_build: bool
    plugin_settings: dict[str, object] | None
    schema_generator: type[GenerateSchema] | None
    json_schema_serialization_defaults_required: bool
    json_schema_mode_override: Literal['validation', 'serialization', None]
    coerce_numbers_to_str: bool
    regex_engine: Literal['rust-regex', 'python-re']
    validation_error_cause: bool
    use_attribute_docstrings: bool
    cache_strings: bool | Literal['all', 'keys', 'none']
    validate_by_alias: bool
    validate_by_name: bool
    serialize_by_alias: bool

    def __init__(self, config: ConfigDict | dict[str, Any] | type[Any] | None, *, check: bool = True):
        if check:
            self.config_dict = prepare_config(config)
        else:
            self.config_dict = cast(ConfigDict, config)

    @classmethod
    def for_model(cls, bases: tuple[type[Any], ...], namespace: dict[str, Any], kwargs: dict[str, Any]) -> Self:
        """Build a new `ConfigWrapper` instance for a `BaseModel`.

        The config wrapper built based on (in descending order of priority):
        - options from `kwargs`
        - options from the `namespace`
        - options from the base classes (`bases`)

        Args:
            bases: A tuple of base classes.
            namespace: The namespace of the class being created.
            kwargs: The kwargs passed to the class being created.

        Returns:
            A `ConfigWrapper` instance for `BaseModel`.
        """
        config_new = ConfigDict()
        for base in bases:
            config = getattr(base, 'model_config', None)
            if config:
                config_new.update(config.copy())

        config_class_from_namespace = namespace.get('Config')
        config_dict_from_namespace = namespace.get('model_config')

        raw_annotations = namespace.get('__annotations__', {})
        if raw_annotations.get('model_config') and config_dict_from_namespace is None:
            raise PydanticUserError(
                '`model_config` cannot be used as a model field name. Use `model_config` for model configuration.',
                code='model-config-invalid-field-name',
            )

        if config_class_from_namespace and config_dict_from_namespace:
            raise PydanticUserError('"Config" and "model_config" cannot be used together', code='config-both')

        config_from_namespace = config_dict_from_namespace or prepare_config(config_class_from_namespace)

        config_new.update(config_from_namespace)

        for k in list(kwargs.keys()):
            if k in config_keys:
                config_new[k] = kwargs.pop(k)

        return cls(config_new)

    # we don't show `__getattr__` to type checkers so missing attributes cause errors
    if not TYPE_CHECKING:  # pragma: no branch

        def __getattr__(self, name: str) -> Any:
            try:
                return self.config_dict[name]
            except KeyError:
                try:
                    return config_defaults[name]
                except KeyError:
                    raise AttributeError(f'Config has no attribute {name!r}') from None

    def core_config(self, title: str | None) -> core_schema.CoreConfig:
        """Create a pydantic-core config.

        We don't use getattr here since we don't want to populate with defaults.

        Args:
            title: The title to use if not set in config.

        Returns:
            A `CoreConfig` object created from config.
        """
        config = self.config_dict

        if config.get('schema_generator') is not None:
            warnings.warn(
                'The `schema_generator` setting has been deprecated since v2.10. This setting no longer has any effect.',
                PydanticDeprecatedSince210,
                stacklevel=2,
            )

        if (populate_by_name := config.get('populate_by_name')) is not None:
            # We include this patch for backwards compatibility purposes, but this config setting will be deprecated in v3.0, and likely removed in v4.0.
            # Thus, the above warning and this patch can be removed then as well.
            if config.get('validate_by_name') is None:
                config['validate_by_alias'] = True
                config['validate_by_name'] = populate_by_name

        # We dynamically patch validate_by_name to be True if validate_by_alias is set to False
        # and validate_by_name is not explicitly set.
        if config.get('validate_by_alias') is False and config.get('validate_by_name') is None:
            config['validate_by_name'] = True

        if (not config.get('validate_by_alias', True)) and (not config.get('validate_by_name', False)):
            raise PydanticUserError(
                'At least one of `validate_by_alias` or `validate_by_name` must be set to True.',
                code='validate-by-alias-and-name-false',
            )

        return core_schema.CoreConfig(
            **{  # pyright: ignore[reportArgumentType]
                k: v
                for k, v in (
                    ('title', config.get('title') or title or None),
                    ('extra_fields_behavior', config.get('extra')),
                    ('allow_inf_nan', config.get('allow_inf_nan')),
                    ('str_strip_whitespace', config.get('str_strip_whitespace')),
                    ('str_to_lower', config.get('str_to_lower')),
                    ('str_to_upper', config.get('str_to_upper')),
                    ('strict', config.get('strict')),
                    ('ser_json_timedelta', config.get('ser_json_timedelta')),
                    ('ser_json_bytes', config.get('ser_json_bytes')),
                    ('val_json_bytes', config.get('val_json_bytes')),
                    ('ser_json_inf_nan', config.get('ser_json_inf_nan')),
                    ('from_attributes', config.get('from_attributes')),
                    ('loc_by_alias', config.get('loc_by_alias')),
                    ('revalidate_instances', config.get('revalidate_instances')),
                    ('validate_default', config.get('validate_default')),
                    ('str_max_length', config.get('str_max_length')),
                    ('str_min_length', config.get('str_min_length')),
                    ('hide_input_in_errors', config.get('hide_input_in_errors')),
                    ('coerce_numbers_to_str', config.get('coerce_numbers_to_str')),
                    ('regex_engine', config.get('regex_engine')),
                    ('validation_error_cause', config.get('validation_error_cause')),
                    ('cache_strings', config.get('cache_strings')),
                    ('validate_by_alias', config.get('validate_by_alias')),
                    ('validate_by_name', config.get('validate_by_name')),
                    ('serialize_by_alias', config.get('serialize_by_alias')),
                )
                if v is not None
            }
        )

    def __repr__(self):
        c = ', '.join(f'{k}={v!r}' for k, v in self.config_dict.items())
        return f'ConfigWrapper({c})'


class ConfigWrapperStack:
    """A stack of `ConfigWrapper` instances."""

    def __init__(self, config_wrapper: ConfigWrapper):
        self._config_wrapper_stack: list[ConfigWrapper] = [config_wrapper]

    @property
    def tail(self) -> ConfigWrapper:
        return self._config_wrapper_stack[-1]

    @contextmanager
    def push(self, config_wrapper: ConfigWrapper | ConfigDict | None):
        if config_wrapper is None:
            yield
            return

        if not isinstance(config_wrapper, ConfigWrapper):
            config_wrapper = ConfigWrapper(config_wrapper, check=False)

        self._config_wrapper_stack.append(config_wrapper)
        try:
            yield
        finally:
            self._config_wrapper_stack.pop()


config_defaults = ConfigDict(
    title=None,
    str_to_lower=False,
    str_to_upper=False,
    str_strip_whitespace=False,
    str_min_length=0,
    str_max_length=None,
    # let the model / dataclass decide how to handle it
    extra=None,
    frozen=False,
    populate_by_name=False,
    use_enum_values=False,
    validate_assignment=False,
    arbitrary_types_allowed=False,
    from_attributes=False,
    loc_by_alias=True,
    alias_generator=None,
    model_title_generator=None,
    field_title_generator=None,
    ignored_types=(),
    allow_inf_nan=True,
    json_schema_extra=None,
    strict=False,
    revalidate_instances='never',
    ser_json_timedelta='iso8601',
    ser_json_bytes='utf8',
    val_json_bytes='utf8',
    ser_json_inf_nan='null',
    validate_default=False,
    validate_return=False,
    protected_namespaces=('model_validate', 'model_dump'),
    hide_input_in_errors=False,
    json_encoders=None,
    defer_build=False,
    schema_generator=None,
    plugin_settings=None,
    json_schema_serialization_defaults_required=False,
    json_schema_mode_override=None,
    coerce_numbers_to_str=False,
    regex_engine='rust-regex',
    validation_error_cause=False,
    use_attribute_docstrings=False,
    cache_strings=True,
    validate_by_alias=True,
    validate_by_name=False,
    serialize_by_alias=False,
)


def prepare_config(config: ConfigDict | dict[str, Any] | type[Any] | None) -> ConfigDict:
    """Create a `ConfigDict` instance from an existing dict, a class (e.g. old class-based config) or None.

    Args:
        config: The input config.

    Returns:
        A ConfigDict object created from config.
    """
    if config is None:
        return ConfigDict()

    if not isinstance(config, dict):
        warnings.warn(DEPRECATION_MESSAGE, DeprecationWarning)
        config = {k: getattr(config, k) for k in dir(config) if not k.startswith('__')}

    config_dict = cast(ConfigDict, config)
    check_deprecated(config_dict)
    return config_dict


config_keys = set(ConfigDict.__annotations__.keys())


V2_REMOVED_KEYS = {
    'allow_mutation',
    'error_msg_templates',
    'fields',
    'getter_dict',
    'smart_union',
    'underscore_attrs_are_private',
    'json_loads',
    'json_dumps',
    'copy_on_model_validation',
    'post_init_call',
}
V2_RENAMED_KEYS = {
    'allow_population_by_field_name': 'validate_by_name',
    'anystr_lower': 'str_to_lower',
    'anystr_strip_whitespace': 'str_strip_whitespace',
    'anystr_upper': 'str_to_upper',
    'keep_untouched': 'ignored_types',
    'max_anystr_length': 'str_max_length',
    'min_anystr_length': 'str_min_length',
    'orm_mode': 'from_attributes',
    'schema_extra': 'json_schema_extra',
    'validate_all': 'validate_default',
}


def check_deprecated(config_dict: ConfigDict) -> None:
    """Check for deprecated config keys and warn the user.

    Args:
        config_dict: The input config.
    """
    deprecated_removed_keys = V2_REMOVED_KEYS & config_dict.keys()
    deprecated_renamed_keys = V2_RENAMED_KEYS.keys() & config_dict.keys()
    if deprecated_removed_keys or deprecated_renamed_keys:
        renamings = {k: V2_RENAMED_KEYS[k] for k in sorted(deprecated_renamed_keys)}
        renamed_bullets = [f'* {k!r} has been renamed to {v!r}' for k, v in renamings.items()]
        removed_bullets = [f'* {k!r} has been removed' for k in sorted(deprecated_removed_keys)]
        message = '\n'.join(['Valid config keys have changed in V2:'] + renamed_bullets + removed_bullets)
        warnings.warn(message, UserWarning)

# === NexusCore/openenv\Lib\site-packages\tornado\test\util_test.py ===
import re
import sys
import datetime
import textwrap
import unittest

import tornado
from tornado.escape import utf8
from tornado.util import (
    raise_exc_info,
    Configurable,
    exec_in,
    ArgReplacer,
    timedelta_to_seconds,
    import_object,
    re_unescape,
)

from typing import cast, Dict, Any


class RaiseExcInfoTest(unittest.TestCase):
    def test_two_arg_exception(self):
        # This test would fail on python 3 if raise_exc_info were simply
        # a three-argument raise statement, because TwoArgException
        # doesn't have a "copy constructor"
        class TwoArgException(Exception):
            def __init__(self, a, b):
                super().__init__()
                self.a, self.b = a, b

        try:
            raise TwoArgException(1, 2)
        except TwoArgException:
            exc_info = sys.exc_info()
        try:
            raise_exc_info(exc_info)
            self.fail("didn't get expected exception")
        except TwoArgException as e:
            self.assertIs(e, exc_info[1])


class TestConfigurable(Configurable):
    @classmethod
    def configurable_base(cls):
        return TestConfigurable

    @classmethod
    def configurable_default(cls):
        return TestConfig1


class TestConfig1(TestConfigurable):
    def initialize(self, pos_arg=None, a=None):
        self.a = a
        self.pos_arg = pos_arg


class TestConfig2(TestConfigurable):
    def initialize(self, pos_arg=None, b=None):
        self.b = b
        self.pos_arg = pos_arg


class TestConfig3(TestConfigurable):
    # TestConfig3 is a configuration option that is itself configurable.
    @classmethod
    def configurable_base(cls):
        return TestConfig3

    @classmethod
    def configurable_default(cls):
        return TestConfig3A


class TestConfig3A(TestConfig3):
    def initialize(self, a=None):
        self.a = a


class TestConfig3B(TestConfig3):
    def initialize(self, b=None):
        self.b = b


class ConfigurableTest(unittest.TestCase):
    def setUp(self):
        self.saved = TestConfigurable._save_configuration()
        self.saved3 = TestConfig3._save_configuration()

    def tearDown(self):
        TestConfigurable._restore_configuration(self.saved)
        TestConfig3._restore_configuration(self.saved3)

    def checkSubclasses(self):
        # no matter how the class is configured, it should always be
        # possible to instantiate the subclasses directly
        self.assertIsInstance(TestConfig1(), TestConfig1)
        self.assertIsInstance(TestConfig2(), TestConfig2)

        obj = TestConfig1(a=1)
        self.assertEqual(obj.a, 1)
        obj2 = TestConfig2(b=2)
        self.assertEqual(obj2.b, 2)

    def test_default(self):
        # In these tests we combine a typing.cast to satisfy mypy with
        # a runtime type-assertion. Without the cast, mypy would only
        # let us access attributes of the base class.
        obj = cast(TestConfig1, TestConfigurable())
        self.assertIsInstance(obj, TestConfig1)
        self.assertIsNone(obj.a)

        obj = cast(TestConfig1, TestConfigurable(a=1))
        self.assertIsInstance(obj, TestConfig1)
        self.assertEqual(obj.a, 1)

        self.checkSubclasses()

    def test_config_class(self):
        TestConfigurable.configure(TestConfig2)
        obj = cast(TestConfig2, TestConfigurable())
        self.assertIsInstance(obj, TestConfig2)
        self.assertIsNone(obj.b)

        obj = cast(TestConfig2, TestConfigurable(b=2))
        self.assertIsInstance(obj, TestConfig2)
        self.assertEqual(obj.b, 2)

        self.checkSubclasses()

    def test_config_str(self):
        TestConfigurable.configure("tornado.test.util_test.TestConfig2")
        obj = cast(TestConfig2, TestConfigurable())
        self.assertIsInstance(obj, TestConfig2)
        self.assertIsNone(obj.b)

        obj = cast(TestConfig2, TestConfigurable(b=2))
        self.assertIsInstance(obj, TestConfig2)
        self.assertEqual(obj.b, 2)

        self.checkSubclasses()

    def test_config_args(self):
        TestConfigurable.configure(None, a=3)
        obj = cast(TestConfig1, TestConfigurable())
        self.assertIsInstance(obj, TestConfig1)
        self.assertEqual(obj.a, 3)

        obj = cast(TestConfig1, TestConfigurable(42, a=4))
        self.assertIsInstance(obj, TestConfig1)
        self.assertEqual(obj.a, 4)
        self.assertEqual(obj.pos_arg, 42)

        self.checkSubclasses()
        # args bound in configure don't apply when using the subclass directly
        obj = TestConfig1()
        self.assertIsNone(obj.a)

    def test_config_class_args(self):
        TestConfigurable.configure(TestConfig2, b=5)
        obj = cast(TestConfig2, TestConfigurable())
        self.assertIsInstance(obj, TestConfig2)
        self.assertEqual(obj.b, 5)

        obj = cast(TestConfig2, TestConfigurable(42, b=6))
        self.assertIsInstance(obj, TestConfig2)
        self.assertEqual(obj.b, 6)
        self.assertEqual(obj.pos_arg, 42)

        self.checkSubclasses()
        # args bound in configure don't apply when using the subclass directly
        obj = TestConfig2()
        self.assertIsNone(obj.b)

    def test_config_multi_level(self):
        TestConfigurable.configure(TestConfig3, a=1)
        obj = cast(TestConfig3A, TestConfigurable())
        self.assertIsInstance(obj, TestConfig3A)
        self.assertEqual(obj.a, 1)

        TestConfigurable.configure(TestConfig3)
        TestConfig3.configure(TestConfig3B, b=2)
        obj2 = cast(TestConfig3B, TestConfigurable())
        self.assertIsInstance(obj2, TestConfig3B)
        self.assertEqual(obj2.b, 2)

    def test_config_inner_level(self):
        # The inner level can be used even when the outer level
        # doesn't point to it.
        obj = TestConfig3()
        self.assertIsInstance(obj, TestConfig3A)

        TestConfig3.configure(TestConfig3B)
        obj = TestConfig3()
        self.assertIsInstance(obj, TestConfig3B)

        # Configuring the base doesn't configure the inner.
        obj2 = TestConfigurable()
        self.assertIsInstance(obj2, TestConfig1)
        TestConfigurable.configure(TestConfig2)

        obj3 = TestConfigurable()
        self.assertIsInstance(obj3, TestConfig2)

        obj = TestConfig3()
        self.assertIsInstance(obj, TestConfig3B)


class UnicodeLiteralTest(unittest.TestCase):
    def test_unicode_escapes(self):
        self.assertEqual(utf8("\u00e9"), b"\xc3\xa9")


class ExecInTest(unittest.TestCase):
    def test_no_inherit_future(self):
        # Two files: the first has "from __future__ import annotations", and it executes the second
        # which doesn't. The second file should not be affected by the first's __future__ imports.
        #
        # The annotations future became available in python 3.7 but has been replaced by PEP 649, so
        # it should remain supported but off-by-default for the foreseeable future.
        code1 = textwrap.dedent(
            """
            from __future__ import annotations
            from tornado.util import exec_in

            exec_in(code2, globals())
            """
        )

        code2 = textwrap.dedent(
            """
            def f(x: int) -> int:
                return x + 1
            output[0] = f.__annotations__
            """
        )

        # Make a mutable container to pass the result back to the caller
        output = [None]
        exec_in(code1, dict(code2=code2, output=output))
        # If the annotations future were in effect, these would be strings instead of the int type
        # object.
        self.assertEqual(output[0], {"x": int, "return": int})


class ArgReplacerTest(unittest.TestCase):
    def setUp(self):
        def function(x, y, callback=None, z=None):
            pass

        self.replacer = ArgReplacer(function, "callback")

    def test_omitted(self):
        args = (1, 2)
        kwargs: Dict[str, Any] = dict()
        self.assertIsNone(self.replacer.get_old_value(args, kwargs))
        self.assertEqual(
            self.replacer.replace("new", args, kwargs),
            (None, (1, 2), dict(callback="new")),
        )

    def test_position(self):
        args = (1, 2, "old", 3)
        kwargs: Dict[str, Any] = dict()
        self.assertEqual(self.replacer.get_old_value(args, kwargs), "old")
        self.assertEqual(
            self.replacer.replace("new", args, kwargs),
            ("old", [1, 2, "new", 3], dict()),
        )

    def test_keyword(self):
        args = (1,)
        kwargs = dict(y=2, callback="old", z=3)
        self.assertEqual(self.replacer.get_old_value(args, kwargs), "old")
        self.assertEqual(
            self.replacer.replace("new", args, kwargs),
            ("old", (1,), dict(y=2, callback="new", z=3)),
        )


class TimedeltaToSecondsTest(unittest.TestCase):
    def test_timedelta_to_seconds(self):
        time_delta = datetime.timedelta(hours=1)
        self.assertEqual(timedelta_to_seconds(time_delta), 3600.0)


class ImportObjectTest(unittest.TestCase):
    def test_import_member(self):
        self.assertIs(import_object("tornado.escape.utf8"), utf8)

    def test_import_member_unicode(self):
        self.assertIs(import_object("tornado.escape.utf8"), utf8)

    def test_import_module(self):
        self.assertIs(import_object("tornado.escape"), tornado.escape)

    def test_import_module_unicode(self):
        # The internal implementation of __import__ differs depending on
        # whether the thing being imported is a module or not.
        # This variant requires a byte string in python 2.
        self.assertIs(import_object("tornado.escape"), tornado.escape)


class ReUnescapeTest(unittest.TestCase):
    def test_re_unescape(self):
        test_strings = ("/favicon.ico", "index.html", "Hello, World!", "!$@#%;")
        for string in test_strings:
            self.assertEqual(string, re_unescape(re.escape(string)))

    def test_re_unescape_raises_error_on_invalid_input(self):
        with self.assertRaises(ValueError):
            re_unescape("\\d")
        with self.assertRaises(ValueError):
            re_unescape("\\b")
        with self.assertRaises(ValueError):
            re_unescape("\\Z")


class VersionInfoTest(unittest.TestCase):
    def assert_version_info_compatible(self, version, version_info):
        # We map our version identifier string (a subset of
        # https://packaging.python.org/en/latest/specifications/version-specifiers/#public-version-identifiers)
        # to a 4-tuple of integers for easy comparisons. The last component is
        # 0 for a final release, negative for a pre-release, and would be positive for a
        # post-release if we did any of those. This test is not a promise that these are the
        # only formats we will ever use, but it does catch accidents like
        # https://github.com/tornadoweb/tornado/issues/3406.
        major = minor = patch = "0"
        is_pre = False
        if m := re.fullmatch(r"(\d+)\.(\d+)\.(\d+)", version):
            # Regular 3-component version number
            major, minor, patch = m.groups()
        elif m := re.fullmatch(r"(\d+)\.(\d+)", version):
            # Two-component version number, equivalent to major.minor.0
            major, minor = m.groups()
        elif m := re.fullmatch(r"(\d+)\.(\d+)\.(\d+)(?:\.dev|a|b|rc)\d+", version):
            # Pre-release 3-component version number.
            major, minor, patch = m.groups()
            is_pre = True
        elif m := re.fullmatch(r"(\d+)\.(\d+)(?:\.dev|a|b|rc)\d+", version):
            # Pre-release 2-component version number.
            major, minor = m.groups()
            is_pre = True
        else:
            self.fail(f"Unrecognized version format: {version}")

        self.assertEqual(version_info[:3], (int(major), int(minor), int(patch)))
        if is_pre:
            self.assertLess(int(version_info[3]), 0)
        else:
            self.assertEqual(int(version_info[3]), 0)

    def test_version_info_compatible(self):
        self.assert_version_info_compatible("6.5.0", (6, 5, 0, 0))
        self.assert_version_info_compatible("6.5", (6, 5, 0, 0))
        self.assert_version_info_compatible("6.5.1", (6, 5, 1, 0))
        self.assert_version_info_compatible("6.6.dev1", (6, 6, 0, -100))
        self.assert_version_info_compatible("6.6a1", (6, 6, 0, -100))
        self.assert_version_info_compatible("6.6b1", (6, 6, 0, -100))
        self.assert_version_info_compatible("6.6rc1", (6, 6, 0, -100))
        self.assertRaises(
            AssertionError, self.assert_version_info_compatible, "6.5.0", (6, 5, 0, 1)
        )
        self.assertRaises(
            AssertionError, self.assert_version_info_compatible, "6.5.0", (6, 4, 0, 0)
        )
        self.assertRaises(
            AssertionError, self.assert_version_info_compatible, "6.5.1", (6, 5, 0, 1)
        )

    def test_current_version(self):
        self.assert_version_info_compatible(tornado.version, tornado.version_info)

# === NexusCore/openenv\Lib\site-packages\debugpy\_vendored\pydevd\_pydev_bundle\_pydev_imports_tipper.py ===
import inspect
import os.path
import sys

from _pydev_bundle._pydev_tipper_common import do_find
from _pydevd_bundle.pydevd_utils import hasattr_checked, dir_checked

from inspect import getfullargspec


def getargspec(*args, **kwargs):
    arg_spec = getfullargspec(*args, **kwargs)
    return arg_spec.args, arg_spec.varargs, arg_spec.varkw, arg_spec.defaults, arg_spec.kwonlyargs or [], arg_spec.kwonlydefaults or {}


# completion types.
TYPE_IMPORT = "0"
TYPE_CLASS = "1"
TYPE_FUNCTION = "2"
TYPE_ATTR = "3"
TYPE_BUILTIN = "4"
TYPE_PARAM = "5"


def _imp(name, log=None):
    try:
        return __import__(name)
    except:
        if "." in name:
            sub = name[0 : name.rfind(".")]

            if log is not None:
                log.add_content("Unable to import", name, "trying with", sub)
                log.add_exception()

            return _imp(sub, log)
        else:
            s = "Unable to import module: %s - sys.path: %s" % (str(name), sys.path)
            if log is not None:
                log.add_content(s)
                log.add_exception()

            raise ImportError(s)


IS_IPY = False
if sys.platform == "cli":
    IS_IPY = True
    _old_imp = _imp

    def _imp(name, log=None):
        # We must add a reference in clr for .Net
        import clr  # @UnresolvedImport

        initial_name = name
        while "." in name:
            try:
                clr.AddReference(name)
                break  # If it worked, that's OK.
            except:
                name = name[0 : name.rfind(".")]
        else:
            try:
                clr.AddReference(name)
            except:
                pass  # That's OK (not dot net module).

        return _old_imp(initial_name, log)


def get_file(mod):
    f = None
    try:
        f = inspect.getsourcefile(mod) or inspect.getfile(mod)
    except:
        try:
            f = getattr(mod, "__file__", None)
        except:
            f = None
        if f and f.lower(f[-4:]) in [".pyc", ".pyo"]:
            filename = f[:-4] + ".py"
            if os.path.exists(filename):
                f = filename

    return f


def Find(name, log=None):
    f = None

    mod = _imp(name, log)
    parent = mod
    foundAs = ""

    if inspect.ismodule(mod):
        f = get_file(mod)

    components = name.split(".")

    old_comp = None
    for comp in components[1:]:
        try:
            # this happens in the following case:
            # we have mx.DateTime.mxDateTime.mxDateTime.pyd
            # but after importing it, mx.DateTime.mxDateTime shadows access to mxDateTime.pyd
            mod = getattr(mod, comp)
        except AttributeError:
            if old_comp != comp:
                raise

        if inspect.ismodule(mod):
            f = get_file(mod)
        else:
            if len(foundAs) > 0:
                foundAs = foundAs + "."
            foundAs = foundAs + comp

        old_comp = comp

    return f, mod, parent, foundAs


def search_definition(data):
    """@return file, line, col"""

    data = data.replace("\n", "")
    if data.endswith("."):
        data = data.rstrip(".")
    f, mod, parent, foundAs = Find(data)
    try:
        return do_find(f, mod), foundAs
    except:
        return do_find(f, parent), foundAs


def generate_tip(data, log=None):
    data = data.replace("\n", "")
    if data.endswith("."):
        data = data.rstrip(".")

    f, mod, parent, foundAs = Find(data, log)
    # print_ >> open('temp.txt', 'w'), f
    tips = generate_imports_tip_for_module(mod)
    return f, tips


def check_char(c):
    if c == "-" or c == ".":
        return "_"
    return c


_SENTINEL = object()


def generate_imports_tip_for_module(obj_to_complete, dir_comps=None, getattr=getattr, filter=lambda name: True):
    """
    @param obj_to_complete: the object from where we should get the completions
    @param dir_comps: if passed, we should not 'dir' the object and should just iterate those passed as kwonly_arg parameter
    @param getattr: the way to get kwonly_arg given object from the obj_to_complete (used for the completer)
    @param filter: kwonly_arg callable that receives the name and decides if it should be appended or not to the results
    @return: list of tuples, so that each tuple represents kwonly_arg completion with:
        name, doc, args, type (from the TYPE_* constants)
    """
    ret = []

    if dir_comps is None:
        dir_comps = dir_checked(obj_to_complete)
        if hasattr_checked(obj_to_complete, "__dict__"):
            dir_comps.append("__dict__")
        if hasattr_checked(obj_to_complete, "__class__"):
            dir_comps.append("__class__")

    get_complete_info = True

    if len(dir_comps) > 1000:
        # ok, we don't want to let our users wait forever...
        # no complete info for you...

        get_complete_info = False

    dontGetDocsOn = (float, int, str, tuple, list, dict)
    dontGetattrOn = (dict, list, set, tuple)
    for d in dir_comps:
        if d is None:
            continue

        if not filter(d):
            continue

        args = ""

        try:
            try:
                if isinstance(obj_to_complete, dontGetattrOn):
                    raise Exception(
                        'Since python 3.9, e.g. "dict[str]" will return'
                        " a dict that's only supposed to take strings. "
                        'Interestingly, e.g. dict["val"] is also valid '
                        "and presumably represents a dict that only takes "
                        'keys that are "val". This breaks our check for '
                        "class attributes."
                    )
                obj = getattr(obj_to_complete.__class__, d)
            except:
                obj = getattr(obj_to_complete, d)
        except:  # just ignore and get it without additional info
            ret.append((d, "", args, TYPE_BUILTIN))
        else:
            if get_complete_info:
                try:
                    retType = TYPE_BUILTIN

                    # check if we have to get docs
                    getDoc = True
                    for class_ in dontGetDocsOn:
                        if isinstance(obj, class_):
                            getDoc = False
                            break

                    doc = ""
                    if getDoc:
                        # no need to get this info... too many constants are defined and
                        # makes things much slower (passing all that through sockets takes quite some time)
                        try:
                            doc = inspect.getdoc(obj)
                            if doc is None:
                                doc = ""
                        except:  # may happen on jython when checking java classes (so, just ignore it)
                            doc = ""

                    if inspect.ismethod(obj) or inspect.isbuiltin(obj) or inspect.isfunction(obj) or inspect.isroutine(obj):
                        try:
                            args, vargs, kwargs, defaults, kwonly_args, kwonly_defaults = getargspec(obj)

                            args = args[:]

                            for kwonly_arg in kwonly_args:
                                default = kwonly_defaults.get(kwonly_arg, _SENTINEL)
                                if default is not _SENTINEL:
                                    args.append("%s=%s" % (kwonly_arg, default))
                                else:
                                    args.append(str(kwonly_arg))

                            args = "(%s)" % (", ".join(args))
                        except TypeError:
                            # ok, let's see if we can get the arguments from the doc
                            args, doc = signature_from_docstring(doc, getattr(obj, "__name__", None))

                        retType = TYPE_FUNCTION

                    elif inspect.isclass(obj):
                        retType = TYPE_CLASS

                    elif inspect.ismodule(obj):
                        retType = TYPE_IMPORT

                    else:
                        retType = TYPE_ATTR

                    # add token and doc to return - assure only strings.
                    ret.append((d, doc, args, retType))

                except:  # just ignore and get it without aditional info
                    ret.append((d, "", args, TYPE_BUILTIN))

            else:  # get_complete_info == False
                if inspect.ismethod(obj) or inspect.isbuiltin(obj) or inspect.isfunction(obj) or inspect.isroutine(obj):
                    retType = TYPE_FUNCTION

                elif inspect.isclass(obj):
                    retType = TYPE_CLASS

                elif inspect.ismodule(obj):
                    retType = TYPE_IMPORT

                else:
                    retType = TYPE_ATTR
                # ok, no complete info, let's try to do this as fast and clean as possible
                # so, no docs for this kind of information, only the signatures
                ret.append((d, "", str(args), retType))

    return ret


def signature_from_docstring(doc, obj_name):
    args = "()"
    try:
        found = False
        if len(doc) > 0:
            if IS_IPY:
                # Handle case where we have the situation below
                # sort(self, object cmp, object key)
                # sort(self, object cmp, object key, bool reverse)
                # sort(self)
                # sort(self, object cmp)

                # Or: sort(self: list, cmp: object, key: object)
                # sort(self: list, cmp: object, key: object, reverse: bool)
                # sort(self: list)
                # sort(self: list, cmp: object)
                if obj_name:
                    name = obj_name + "("

                    # Fix issue where it was appearing sort(aa)sort(bb)sort(cc) in the same line.
                    lines = doc.splitlines()
                    if len(lines) == 1:
                        c = doc.count(name)
                        if c > 1:
                            doc = ("\n" + name).join(doc.split(name))

                    major = ""
                    for line in doc.splitlines():
                        if line.startswith(name) and line.endswith(")"):
                            if len(line) > len(major):
                                major = line
                    if major:
                        args = major[major.index("(") :]
                        found = True

            if not found:
                i = doc.find("->")
                if i < 0:
                    i = doc.find("--")
                    if i < 0:
                        i = doc.find("\n")
                        if i < 0:
                            i = doc.find("\r")

                if i > 0:
                    s = doc[0:i]
                    s = s.strip()

                    # let's see if we have a docstring in the first line
                    if s[-1] == ")":
                        start = s.find("(")
                        if start >= 0:
                            end = s.find("[")
                            if end <= 0:
                                end = s.find(")")
                                if end <= 0:
                                    end = len(s)

                            args = s[start:end]
                            if not args[-1] == ")":
                                args = args + ")"

                            # now, get rid of unwanted chars
                            l = len(args) - 1
                            r = []
                            for i in range(len(args)):
                                if i == 0 or i == l:
                                    r.append(args[i])
                                else:
                                    r.append(check_char(args[i]))

                            args = "".join(r)

            if IS_IPY:
                if args.startswith("(self:"):
                    i = args.find(",")
                    if i >= 0:
                        args = "(self" + args[i:]
                    else:
                        args = "(self)"
                i = args.find(")")
                if i > 0:
                    args = args[: i + 1]

    except:
        pass
    return args, doc

# === NexusCore/openenv\Lib\site-packages\debugpy\_vendored\pydevd\_pydevd_frame_eval\vendored\bytecode\instr.py ===
import enum
import dis
import opcode as _opcode
import sys
from marshal import dumps as _dumps

from _pydevd_frame_eval.vendored import bytecode as _bytecode


@enum.unique
class Compare(enum.IntEnum):
    LT = 0
    LE = 1
    EQ = 2
    NE = 3
    GT = 4
    GE = 5
    IN = 6
    NOT_IN = 7
    IS = 8
    IS_NOT = 9
    EXC_MATCH = 10


UNSET = object()


def const_key(obj):
    try:
        return _dumps(obj)
    except ValueError:
        # For other types, we use the object identifier as an unique identifier
        # to ensure that they are seen as unequal.
        return (type(obj), id(obj))


def _pushes_back(opname):
    if opname in ["CALL_FINALLY"]:
        # CALL_FINALLY pushes the address of the "finally" block instead of a
        # value, hence we don't treat it as pushing back op
        return False
    return (
        opname.startswith("UNARY_")
        or opname.startswith("GET_")
        # BUILD_XXX_UNPACK have been removed in 3.9
        or opname.startswith("BINARY_")
        or opname.startswith("INPLACE_")
        or opname.startswith("BUILD_")
        or opname.startswith("CALL_")
    ) or opname in (
        "LIST_TO_TUPLE",
        "LIST_EXTEND",
        "SET_UPDATE",
        "DICT_UPDATE",
        "DICT_MERGE",
        "IS_OP",
        "CONTAINS_OP",
        "FORMAT_VALUE",
        "MAKE_FUNCTION",
        "IMPORT_NAME",
        # technically, these three do not push back, but leave the container
        # object on TOS
        "SET_ADD",
        "LIST_APPEND",
        "MAP_ADD",
        "LOAD_ATTR",
    )


def _check_lineno(lineno):
    if not isinstance(lineno, int):
        raise TypeError("lineno must be an int")
    if lineno < 1:
        raise ValueError("invalid lineno")


class SetLineno:
    __slots__ = ("_lineno",)

    def __init__(self, lineno):
        _check_lineno(lineno)
        self._lineno = lineno

    @property
    def lineno(self):
        return self._lineno

    def __eq__(self, other):
        if not isinstance(other, SetLineno):
            return False
        return self._lineno == other._lineno


class Label:
    __slots__ = ()


class _Variable:
    __slots__ = ("name",)

    def __init__(self, name):
        self.name = name

    def __eq__(self, other):
        if type(self) != type(other):
            return False
        return self.name == other.name

    def __str__(self):
        return self.name

    def __repr__(self):
        return "<%s %r>" % (self.__class__.__name__, self.name)


class CellVar(_Variable):
    __slots__ = ()


class FreeVar(_Variable):
    __slots__ = ()


def _check_arg_int(name, arg):
    if not isinstance(arg, int):
        raise TypeError("operation %s argument must be an int, " "got %s" % (name, type(arg).__name__))

    if not (0 <= arg <= 2147483647):
        raise ValueError("operation %s argument must be in " "the range 0..2,147,483,647" % name)


if sys.version_info < (3, 8):
    _stack_effects = {
        # NOTE: the entries are all 2-tuples.  Entry[0/False] is non-taken jumps.
        # Entry[1/True] is for taken jumps.
        # opcodes not in dis.stack_effect
        _opcode.opmap["EXTENDED_ARG"]: (0, 0),
        _opcode.opmap["NOP"]: (0, 0),
        # Jump taken/not-taken are different:
        _opcode.opmap["JUMP_IF_TRUE_OR_POP"]: (-1, 0),
        _opcode.opmap["JUMP_IF_FALSE_OR_POP"]: (-1, 0),
        _opcode.opmap["FOR_ITER"]: (1, -1),
        _opcode.opmap["SETUP_WITH"]: (1, 6),
        _opcode.opmap["SETUP_ASYNC_WITH"]: (0, 5),
        _opcode.opmap["SETUP_EXCEPT"]: (0, 6),  # as of 3.7, below for <=3.6
        _opcode.opmap["SETUP_FINALLY"]: (0, 6),  # as of 3.7, below for <=3.6
    }

    # More stack effect values that are unique to the version of Python.
    if sys.version_info < (3, 7):
        _stack_effects.update(
            {
                _opcode.opmap["SETUP_WITH"]: (7, 7),
                _opcode.opmap["SETUP_EXCEPT"]: (6, 9),
                _opcode.opmap["SETUP_FINALLY"]: (6, 9),
            }
        )


class Instr:
    """Abstract instruction."""

    __slots__ = ("_name", "_opcode", "_arg", "_lineno", "offset")

    def __init__(self, name, arg=UNSET, *, lineno=None, offset=None):
        self._set(name, arg, lineno)
        self.offset = offset

    def _check_arg(self, name, opcode, arg):
        if name == "EXTENDED_ARG":
            raise ValueError(
                "only concrete instruction can contain EXTENDED_ARG, " "highlevel instruction can represent arbitrary argument without it"
            )

        if opcode >= _opcode.HAVE_ARGUMENT:
            if arg is UNSET:
                raise ValueError("operation %s requires an argument" % name)
        else:
            if arg is not UNSET:
                raise ValueError("operation %s has no argument" % name)

        if self._has_jump(opcode):
            if not isinstance(arg, (Label, _bytecode.BasicBlock)):
                raise TypeError("operation %s argument type must be " "Label or BasicBlock, got %s" % (name, type(arg).__name__))

        elif opcode in _opcode.hasfree:
            if not isinstance(arg, (CellVar, FreeVar)):
                raise TypeError("operation %s argument must be CellVar " "or FreeVar, got %s" % (name, type(arg).__name__))

        elif opcode in _opcode.haslocal or opcode in _opcode.hasname:
            if not isinstance(arg, str):
                raise TypeError("operation %s argument must be a str, " "got %s" % (name, type(arg).__name__))

        elif opcode in _opcode.hasconst:
            if isinstance(arg, Label):
                raise ValueError("label argument cannot be used " "in %s operation" % name)
            if isinstance(arg, _bytecode.BasicBlock):
                raise ValueError("block argument cannot be used " "in %s operation" % name)

        elif opcode in _opcode.hascompare:
            if not isinstance(arg, Compare):
                raise TypeError("operation %s argument type must be " "Compare, got %s" % (name, type(arg).__name__))

        elif opcode >= _opcode.HAVE_ARGUMENT:
            _check_arg_int(name, arg)

    def _set(self, name, arg, lineno):
        if not isinstance(name, str):
            raise TypeError("operation name must be a str")
        try:
            opcode = _opcode.opmap[name]
        except KeyError:
            raise ValueError("invalid operation name")

        # check lineno
        if lineno is not None:
            _check_lineno(lineno)

        self._check_arg(name, opcode, arg)

        self._name = name
        self._opcode = opcode
        self._arg = arg
        self._lineno = lineno

    def set(self, name, arg=UNSET):
        """Modify the instruction in-place.

        Replace name and arg attributes. Don't modify lineno.
        """
        self._set(name, arg, self._lineno)

    def require_arg(self):
        """Does the instruction require an argument?"""
        return self._opcode >= _opcode.HAVE_ARGUMENT

    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, name):
        self._set(name, self._arg, self._lineno)

    @property
    def opcode(self):
        return self._opcode

    @opcode.setter
    def opcode(self, op):
        if not isinstance(op, int):
            raise TypeError("operator code must be an int")
        if 0 <= op <= 255:
            name = _opcode.opname[op]
            valid = name != "<%r>" % op
        else:
            valid = False
        if not valid:
            raise ValueError("invalid operator code")

        self._set(name, self._arg, self._lineno)

    @property
    def arg(self):
        return self._arg

    @arg.setter
    def arg(self, arg):
        self._set(self._name, arg, self._lineno)

    @property
    def lineno(self):
        return self._lineno

    @lineno.setter
    def lineno(self, lineno):
        self._set(self._name, self._arg, lineno)

    def stack_effect(self, jump=None):
        if self._opcode < _opcode.HAVE_ARGUMENT:
            arg = None
        elif not isinstance(self._arg, int) or self._opcode in _opcode.hasconst:
            # Argument is either a non-integer or an integer constant,
            # not oparg.
            arg = 0
        else:
            arg = self._arg

        if sys.version_info < (3, 8):
            effect = _stack_effects.get(self._opcode, None)
            if effect is not None:
                return max(effect) if jump is None else effect[jump]
            return dis.stack_effect(self._opcode, arg)
        else:
            return dis.stack_effect(self._opcode, arg, jump=jump)

    def pre_and_post_stack_effect(self, jump=None):
        _effect = self.stack_effect(jump=jump)

        # To compute pre size and post size to avoid segfault cause by not enough
        # stack element
        _opname = _opcode.opname[self._opcode]
        if _opname.startswith("DUP_TOP"):
            return _effect * -1, _effect * 2
        if _pushes_back(_opname):
            # if the op pushes value back to the stack, then the stack effect given
            # by dis.stack_effect actually equals pre + post effect, therefore we need
            # -1 from the stack effect as a pre condition
            return _effect - 1, 1
        if _opname.startswith("UNPACK_"):
            # Instr(UNPACK_* , n) pops 1 and pushes n
            # _effect = n - 1
            # hence we return -1, _effect + 1
            return -1, _effect + 1
        if _opname == "FOR_ITER" and not jump:
            # Since FOR_ITER needs TOS to be an iterator, which basically means
            # a prerequisite of 1 on the stack
            return -1, 2
        if _opname == "ROT_N":
            return (-self._arg, self._arg)
        return {"ROT_TWO": (-2, 2), "ROT_THREE": (-3, 3), "ROT_FOUR": (-4, 4)}.get(_opname, (_effect, 0))

    def copy(self):
        return self.__class__(self._name, self._arg, lineno=self._lineno, offset=self.offset)

    def __repr__(self):
        if self._arg is not UNSET:
            return "<%s arg=%r lineno=%s>" % (self._name, self._arg, self._lineno)
        else:
            return "<%s lineno=%s>" % (self._name, self._lineno)

    def _cmp_key(self, labels=None):
        arg = self._arg
        if self._opcode in _opcode.hasconst:
            arg = const_key(arg)
        elif isinstance(arg, Label) and labels is not None:
            arg = labels[arg]
        return (self._lineno, self._name, arg)

    def __eq__(self, other):
        if type(self) != type(other):
            return False
        return self._cmp_key() == other._cmp_key()

    @staticmethod
    def _has_jump(opcode):
        return opcode in _opcode.hasjrel or opcode in _opcode.hasjabs

    def has_jump(self):
        return self._has_jump(self._opcode)

    def is_cond_jump(self):
        """Is a conditional jump?"""
        # Ex: POP_JUMP_IF_TRUE, JUMP_IF_FALSE_OR_POP
        return "JUMP_IF_" in self._name

    def is_uncond_jump(self):
        """Is an unconditional jump?"""
        return self.name in {"JUMP_FORWARD", "JUMP_ABSOLUTE"}

    def is_final(self):
        if self._name in {
            "RETURN_VALUE",
            "RAISE_VARARGS",
            "RERAISE",
            "BREAK_LOOP",
            "CONTINUE_LOOP",
        }:
            return True
        if self.is_uncond_jump():
            return True
        return False

# === NexusCore/openenv\Lib\site-packages\google\generativeai\client.py ===
from __future__ import annotations

import os
import contextlib
import dataclasses
import pathlib
import types
from typing import Any, cast
from collections.abc import Sequence
import httplib2

import google.ai.generativelanguage as glm
import google.generativeai.protos as protos

from google.auth import credentials as ga_credentials
from google.auth import exceptions as ga_exceptions
from google import auth
from google.api_core import client_options as client_options_lib
from google.api_core import gapic_v1
from google.api_core import operations_v1

import googleapiclient.http
import googleapiclient.discovery

try:
    from google.generativeai import version

    __version__ = version.__version__
except ImportError:
    __version__ = "0.0.0"

USER_AGENT = "genai-py"
GENAI_API_DISCOVERY_URL = "https://generativelanguage.googleapis.com/$discovery/rest"


@contextlib.contextmanager
def patch_colab_gce_credentials():
    get_gce = auth._default._get_gce_credentials
    if "COLAB_RELEASE_TAG" in os.environ:
        auth._default._get_gce_credentials = lambda *args, **kwargs: (None, None)

    try:
        yield
    finally:
        auth._default._get_gce_credentials = get_gce


class FileServiceClient(glm.FileServiceClient):
    def __init__(self, *args, **kwargs):
        self._discovery_api = None
        super().__init__(*args, **kwargs)

    def _setup_discovery_api(self):
        api_key = self._client_options.api_key
        if api_key is None:
            raise ValueError(
                "Invalid operation: Uploading to the File API requires an API key. Please provide a valid API key."
            )

        request = googleapiclient.http.HttpRequest(
            http=httplib2.Http(),
            postproc=lambda resp, content: (resp, content),
            uri=f"{GENAI_API_DISCOVERY_URL}?version=v1beta&key={api_key}",
        )
        response, content = request.execute()
        request.http.close()

        discovery_doc = content.decode("utf-8")
        self._discovery_api = googleapiclient.discovery.build_from_document(
            discovery_doc, developerKey=api_key
        )

    def create_file(
        self,
        path: str | pathlib.Path | os.PathLike,
        *,
        mime_type: str | None = None,
        name: str | None = None,
        display_name: str | None = None,
        resumable: bool = True,
    ) -> protos.File:
        if self._discovery_api is None:
            self._setup_discovery_api()

        file = {}
        if name is not None:
            file["name"] = name
        if display_name is not None:
            file["displayName"] = display_name

        media = googleapiclient.http.MediaFileUpload(
            filename=path, mimetype=mime_type, resumable=resumable
        )
        request = self._discovery_api.media().upload(body={"file": file}, media_body=media)
        result = request.execute()

        return self.get_file({"name": result["file"]["name"]})


class FileServiceAsyncClient(glm.FileServiceAsyncClient):
    async def create_file(self, *args, **kwargs):
        raise NotImplementedError(
            "The `create_file` method is currently not supported for the asynchronous client."
        )


@dataclasses.dataclass
class _ClientManager:
    client_config: dict[str, Any] = dataclasses.field(default_factory=dict)
    default_metadata: Sequence[tuple[str, str]] = ()

    discuss_client: glm.DiscussServiceClient | None = None
    discuss_async_client: glm.DiscussServiceAsyncClient | None = None
    clients: dict[str, Any] = dataclasses.field(default_factory=dict)

    def configure(
        self,
        *,
        api_key: str | None = None,
        credentials: ga_credentials.Credentials | dict | None = None,
        # The user can pass a string to choose `rest` or `grpc` or 'grpc_asyncio'.
        # See `_transport_registry` in `DiscussServiceClientMeta`.
        # Since the transport classes align with the client classes it wouldn't make
        # sense to accept a `Transport` object here even though the client classes can.
        # We could accept a dict since all the `Transport` classes take the same args,
        # but that seems rare. Users that need it can just switch to the low level API.
        transport: str | None = None,
        client_options: client_options_lib.ClientOptions | dict[str, Any] | None = None,
        client_info: gapic_v1.client_info.ClientInfo | None = None,
        default_metadata: Sequence[tuple[str, str]] = (),
    ) -> None:
        """Initializes default client configurations using specified parameters or environment variables.

        If no API key has been provided (either directly, or on `client_options`) and the
        `GOOGLE_API_KEY` environment variable is set, it will be used as the API key.

        Note: Not all arguments are detailed below. Refer to the `*ServiceClient` classes in
        `google.ai.generativelanguage` for details on the other arguments.

        Args:
            transport: A string, one of: [`rest`, `grpc`, `grpc_asyncio`].
            api_key: The API-Key to use when creating the default clients (each service uses
                a separate client). This is a shortcut for `client_options={"api_key": api_key}`.
                If omitted, and the `GOOGLE_API_KEY` environment variable is set, it will be
                used.
            default_metadata: Default (key, value) metadata pairs to send with every request.
                when using `transport="rest"` these are sent as HTTP headers.
        """
        if isinstance(client_options, dict):
            client_options = client_options_lib.from_dict(client_options)
        if client_options is None:
            client_options = client_options_lib.ClientOptions()
        client_options = cast(client_options_lib.ClientOptions, client_options)
        had_api_key_value = getattr(client_options, "api_key", None)

        if had_api_key_value:
            if api_key is not None:
                raise ValueError(
                    "Invalid configuration: Please set either `api_key` or `client_options['api_key']`, but not both."
                )
        else:
            if api_key is None:
                # If no key is provided explicitly, attempt to load one from the
                # environment.
                api_key = os.getenv("GOOGLE_API_KEY")

            client_options.api_key = api_key

        user_agent = f"{USER_AGENT}/{__version__}"
        if client_info:
            # Be respectful of any existing agent setting.
            if client_info.user_agent:
                client_info.user_agent += f" {user_agent}"
            else:
                client_info.user_agent = user_agent
        else:
            client_info = gapic_v1.client_info.ClientInfo(user_agent=user_agent)

        client_config = {
            "credentials": credentials,
            "transport": transport,
            "client_options": client_options,
            "client_info": client_info,
        }

        client_config = {key: value for key, value in client_config.items() if value is not None}

        self.client_config = client_config
        self.default_metadata = default_metadata

        self.clients = {}

    def make_client(self, name):
        if name == "file":
            cls = FileServiceClient
        elif name == "file_async":
            cls = FileServiceAsyncClient
        elif name.endswith("_async"):
            name = name.split("_")[0]
            cls = getattr(glm, name.title() + "ServiceAsyncClient")
        else:
            cls = getattr(glm, name.title() + "ServiceClient")

        # Attempt to configure using defaults.
        if not self.client_config:
            configure()

        try:
            with patch_colab_gce_credentials():
                client = cls(**self.client_config)
        except ga_exceptions.DefaultCredentialsError as e:
            e.args = (
                "\n  No API_KEY or ADC found. Please either:\n"
                "    - Set the `GOOGLE_API_KEY` environment variable.\n"
                "    - Manually pass the key with `genai.configure(api_key=my_api_key)`.\n"
                "    - Or set up Application Default Credentials, see https://ai.google.dev/gemini-api/docs/oauth for more information.",
            )
            raise e

        if not self.default_metadata:
            return client

        def keep(name, f):
            if name.startswith("_"):
                return False
            elif name == "create_file":
                return False
            elif not isinstance(f, types.FunctionType):
                return False
            elif isinstance(f, classmethod):
                return False
            elif isinstance(f, staticmethod):
                return False
            else:
                return True

        def add_default_metadata_wrapper(f):
            def call(*args, metadata=(), **kwargs):
                metadata = list(metadata) + list(self.default_metadata)
                return f(*args, **kwargs, metadata=metadata)

            return call

        for name, value in cls.__dict__.items():
            if not keep(name, value):
                continue
            f = getattr(client, name)
            f = add_default_metadata_wrapper(f)
            setattr(client, name, f)

        return client

    def get_default_client(self, name):
        name = name.lower()
        if name == "operations":
            return self.get_default_operations_client()

        client = self.clients.get(name)
        if client is None:
            client = self.make_client(name)
            self.clients[name] = client
        return client

    def get_default_operations_client(self) -> operations_v1.OperationsClient:
        client = self.clients.get("operations", None)
        if client is None:
            model_client = self.get_default_client("Model")
            client = model_client._transport.operations_client
            self.clients["operations"] = client
        return client


def configure(
    *,
    api_key: str | None = None,
    credentials: ga_credentials.Credentials | dict | None = None,
    # The user can pass a string to choose `rest` or `grpc` or 'grpc_asyncio'.
    # See `_transport_registry` in `DiscussServiceClientMeta`.
    # Since the transport classes align with the client classes it wouldn't make
    # sense to accept a `Transport` object here even though the client classes can.
    # We could accept a dict since all the `Transport` classes take the same args,
    # but that seems rare. Users that need it can just switch to the low level API.
    transport: str | None = None,
    client_options: client_options_lib.ClientOptions | dict | None = None,
    client_info: gapic_v1.client_info.ClientInfo | None = None,
    default_metadata: Sequence[tuple[str, str]] = (),
):
    """Captures default client configuration.

    If no API key has been provided (either directly, or on `client_options`) and the
    `GOOGLE_API_KEY` environment variable is set, it will be used as the API key.

    Note: Not all arguments are detailed below. Refer to the `*ServiceClient` classes in
    `google.ai.generativelanguage` for details on the other arguments.

    Args:
        transport: A string, one of: [`rest`, `grpc`, `grpc_asyncio`].
        api_key: The API-Key to use when creating the default clients (each service uses
            a separate client). This is a shortcut for `client_options={"api_key": api_key}`.
            If omitted, and the `GOOGLE_API_KEY` environment variable is set, it will be
            used.
        default_metadata: Default (key, value) metadata pairs to send with every request.
            when using `transport="rest"` these are sent as HTTP headers.
    """
    return _client_manager.configure(
        api_key=api_key,
        credentials=credentials,
        transport=transport,
        client_options=client_options,
        client_info=client_info,
        default_metadata=default_metadata,
    )


_client_manager = _ClientManager()
_client_manager.configure()


def get_default_cache_client() -> glm.CacheServiceClient:
    return _client_manager.get_default_client("cache")


def get_default_discuss_client() -> glm.DiscussServiceClient:
    return _client_manager.get_default_client("discuss")


def get_default_discuss_async_client() -> glm.DiscussServiceAsyncClient:
    return _client_manager.get_default_client("discuss_async")


def get_default_file_client() -> glm.FilesServiceClient:
    return _client_manager.get_default_client("file")


def get_default_file_async_client() -> glm.FilesServiceAsyncClient:
    return _client_manager.get_default_client("file_async")


def get_default_generative_client() -> glm.GenerativeServiceClient:
    return _client_manager.get_default_client("generative")


def get_default_generative_async_client() -> glm.GenerativeServiceAsyncClient:
    return _client_manager.get_default_client("generative_async")


def get_default_text_client() -> glm.TextServiceClient:
    return _client_manager.get_default_client("text")


def get_default_operations_client() -> operations_v1.OperationsClient:
    return _client_manager.get_default_client("operations")


def get_default_model_client() -> glm.ModelServiceAsyncClient:
    return _client_manager.get_default_client("model")


def get_default_retriever_client() -> glm.RetrieverClient:
    return _client_manager.get_default_client("retriever")


def get_default_retriever_async_client() -> glm.RetrieverAsyncClient:
    return _client_manager.get_default_client("retriever_async")


def get_default_permission_client() -> glm.PermissionServiceClient:
    return _client_manager.get_default_client("permission")


def get_default_permission_async_client() -> glm.PermissionServiceAsyncClient:
    return _client_manager.get_default_client("permission_async")

# === NexusCore/openenv\Lib\site-packages\html2image\browsers\search_utils.py ===
import os
import platform
import shutil
import subprocess

try:
    from winreg import ConnectRegistry, OpenKey, QueryValueEx,\
            HKEY_LOCAL_MACHINE, HKEY_CURRENT_USER, KEY_READ
except ImportError:
    # os is not Windows, and there is no need for winreg
    pass

ENV_VAR_LOOKUP_TOGGLE = 'HTML2IMAGE_TOGGLE_ENV_VAR_LOOKUP'

CHROME_EXECUTABLE_ENV_VAR_CANDIDATES = [
    'HTML2IMAGE_CHROME_BIN',
    'HTML2IMAGE_CHROME_EXE',
    'CHROME_BIN',
    'CHROME_EXE',
]

FIREFOX_EXECUTABLE_ENV_VAR_CANDIDATES = [
    'HTML2IMAGE_FIREFOX_BIN',
    'HTML2IMAGE_FIREFOX_EXE',
    'FIREFOX_BIN',
    'FIREFOX_EXE',
]


def get_command_origin(command):
    ''' Finds the path of a given command (windows only).

    This function is inspired by the `start` command on windows.
    It will search if the given command corresponds :
    - To an executable in the current directory
    - To an executable in the PATH environment variable
    - To an executable mentionned in the registry in the
      HKEY_LOCAL_MACHINE or HKEY_LOCAL_MACHINE hkeys in
      SOFTWARE\\[Wow6432Node\\]Microsoft\\Windows\\CurrentVersion\\App Paths\\

    It also "indirectly" validates a path to a file.

    Parameters
    ----------
    - `command`: str
        + command that will be searched.

    Returns
    -------
    - str or None
        + the path corresponding to `command`
        + None, if no path was found
    '''

    # `start "command"` itself could be used to run the command but we want to
    # assess that the command is a valid one.
    command = command.replace('start ', '')

    # which search in current directory + path
    # and file extention can be ommited
    which_result = shutil.which(command)
    if which_result:
        return which_result

    # search for command in registry

    command = command.replace('.exe', '').strip()

    # Once combined, these hkeys and keys are where the `start`
    # command seach for executable.
    hkeys = [HKEY_LOCAL_MACHINE, HKEY_CURRENT_USER]
    keys = [
        "SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\"
        f"App Paths\\{command}.exe",

        "SOFTWARE\\Wow6432Node\\Microsoft\\Windows\\"
        "CurrentVersion\\App Paths\\"
        f"{command}.exe",
    ]

    for hkey in hkeys:
        with ConnectRegistry(None, hkey) as registry:
            for key in keys:
                try:
                    with OpenKey(registry, key, 0, KEY_READ) as k:
                        # if no exception: we found the exe
                        return QueryValueEx(k, '')[0]
                except Exception:
                    # cannot open key, do nothing and proceed to the next one
                    pass
    return None


def find_first_defined_env_var(env_var_list, toggle):
    '''
    Returns the value of the first defined environment variable
    encountered in the `env_var_list` list, but only if the
    the `toggle` environment variableif defined.

    Parameters
    ----------
    - `env_var_list`: list[str]
        + list of environment variable names
    - `toggle`: str
        + environment variable name


    '''
    if toggle in os.environ:
        for env_var in env_var_list:
            value = os.environ.get(env_var)
            if value:
                return value
    return None


def find_chrome(user_given_executable=None):
    """ Finds a Chrome executable.

    Search Chrome on a given path. If no path given,
    try to find Chrome or Chromium-browser on a Windows or Unix system.

    Parameters
    ----------
    - `user_given_executable`: str (optional)
        + A filepath leading to a Chrome/ Chromium executable
        + Or a filename found in the current working directory
        + Or a keyword that executes Chrome/ Chromium, ex:
            - 'chromium' on linux systems
            - 'chrome' on windows (if typing `start chrome` in a cmd works)

    Raises
    ------
    - `FileNotFoundError`
        + If a suitable chrome executable could not be found.

    Returns
    -------
    - str
        + Path of the chrome executable on the current machine.
    """

    # try to find a chrome bin/exe in ENV
    path_from_env = find_first_defined_env_var(
        env_var_list=CHROME_EXECUTABLE_ENV_VAR_CANDIDATES,
        toggle=ENV_VAR_LOOKUP_TOGGLE
    )

    if path_from_env:
        print(
            f'Found a potential chrome executable in the {path_from_env} '
            f'environment variable:\n{path_from_env}\n'
        )
        return path_from_env

    # if an executable is given, try to use it
    if user_given_executable is not None:

        # On Windows, we cannot "safely" validate that user_given_executable
        # seems to be a chrome executable, as we cannot run it with
        # the --version flag.
        # https://bugs.chromium.org/p/chromium/issues/detail?id=158372
        #
        # We thus do the "bare minimum" and check if user_given_executable
        # is a file, a filepath, or corresponds to a keyword that can be used
        # with the start command, like so: `start user_given_executable`
        if platform.system() == 'Windows':
            command_origin = get_command_origin(user_given_executable)
            if command_origin:
                return command_origin

            # cannot validate user_given_executable
            raise FileNotFoundError()

        # On a non-Windows OS, we can validate in a basic way that
        # user_given_executable leads to a Chrome / Chromium executable,
        # or is a command, using the --version flag
        else:
            try:
                if 'chrom' in subprocess.check_output(
                    [user_given_executable, '--version']
                ).decode('utf-8').lower():
                    return user_given_executable
            except Exception:
                pass

        # We got a user_given_executable but couldn't validate it
        raise FileNotFoundError(
            'Failed to find a seemingly valid chrome executable '
            'in the given path.'
        )

    # Executable not in ENV or given by the user, try to find it
    # Search for executable on a Windows OS
    if platform.system() == 'Windows':
        prefixes = [
            os.getenv('PROGRAMFILES(X86)'),
            os.getenv('PROGRAMFILES'),
            os.getenv('LOCALAPPDATA'),
        ]

        suffix = "Google\\Chrome\\Application\\chrome.exe"

        for prefix in prefixes:
            path_candidate = os.path.join(prefix, suffix)
            if os.path.isfile(path_candidate):
                return path_candidate

    # Search for executable on a Linux OS
    elif platform.system() == "Linux":

        chrome_commands = [
            'chromium',
            'chromium-browser',
            'chrome',
            'google-chrome',
            'google-chrome-stable'
        ]

        for chrome_command in chrome_commands:
            if shutil.which(chrome_command):
                # check the --version for "chrom" ?
                return chrome_command

        # snap seems to be a special case?
        # see https://stackoverflow.com/q/63375327/12182226

        try:
            version_result = subprocess.check_output(
                ["chromium-browser", "--version"]
            )
            if 'snap' in str(version_result):
                chrome_snap = (
                    '/snap/chromium/current/usr/lib/chromium-browser/chrome'
                )
                if os.path.isfile(chrome_snap):
                    return chrome_snap
        except Exception:
            pass

    # Search for executable on MacOS
    elif platform.system() == "Darwin":
        # MacOS system
        chrome_app = (
            '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'
        )

        try:
            version_result = subprocess.check_output(
                [chrome_app, "--version"]
            )
            if "Google Chrome" in str(version_result):
                return chrome_app
        except Exception:
            pass

    # Couldn't find an executable (or OS not in Windows, Linux or Mac)
    raise FileNotFoundError(
        'Could not find a Chrome executable on this '
        'machine, please specify it yourself.'
    )

def find_firefox(user_given_executable=None):
    """ Finds a Firefox executable.

    Search Firefox on a given path. If no path given,
    try to find Firefox on a Windows or Unix system.

    Parameters
    ----------
    - `user_given_executable`: str (optional)
        + A filepath leading to a Firefox executable
        + Or a filename found in the current working directory
        + Or a keyword that executes Firefox, ex:
            - 'firefox' on linux systems
            - 'firefox' on windows (if typing `start firefox` in a cmd works)

    Raises
    ------
    - `FileNotFoundError`
        + If a suitable Firefox executable could not be found.

    Returns
    -------
    - str
        + Path of the Firefox executable on the current machine.
    """

    # try to find a firefox bin/exe in ENV
    path_from_env = find_first_defined_env_var(
        env_var_list=FIREFOX_EXECUTABLE_ENV_VAR_CANDIDATES,
        toggle=ENV_VAR_LOOKUP_TOGGLE
    )

    if path_from_env:
        print(
            f'Found a potential Firefox executable in the {path_from_env} '
            f'environment variable:\n{path_from_env}\n'
        )
        return path_from_env

    # if an executable is given, try to use it
    if user_given_executable is not None:

        if platform.system() == 'Windows':
            user_given_executable = get_command_origin(user_given_executable)

        try:
            version_output = subprocess.check_output(
                [user_given_executable, '--version']
            ).decode('utf-8').lower()

            if 'Mozilla Firefox' in version_output:
                return user_given_executable
            else:
                print(
                    'Could not validate Firefox executable',
                    '(--version does not contains "Mozilla Firefox").'
                )
        except Exception:
            pass

        # We got a user_given_executable but couldn't validate it
        raise FileNotFoundError(
            'Failed to find a seemingly valid Firefox executable '
            'in the given path.'
        )

    # Executable not in ENV or given by the user, try to find it
    # Search for executable on a Windows OS
    if platform.system() == 'Windows':
        prefixes = [
            os.getenv('PROGRAMFILES(X86)'),
            os.getenv('PROGRAMFILES'),
            os.getenv('LOCALAPPDATA'),
        ]

        suffix = 'Mozilla Firefox\\firefox.exe'

        for prefix in prefixes:
            path_candidate = os.path.join(prefix, suffix)
            if os.path.isfile(path_candidate):
                return path_candidate

    # Search for executable on a Linux OS
    elif platform.system() == 'Linux':
        if shutil.which('firefox'):
            return 'firefox'

    # Search for executable on MacOS
    elif platform.system() == 'Darwin':
        # MacOS system

        # TODO : check if this is the right path
        firefox_app = (
            '/Applications/Firefox.app/Contents/MacOS/firefox'  # ?
        )

        try:
            version_result = subprocess.check_output(
                [firefox_app, '--version']
            )
            if 'Mozilla Firefox' in str(version_result):
                return firefox_app
        except Exception:
            pass

    # Couldn't find an executable (or OS not in Windows, Linux or Mac)
    raise FileNotFoundError(
        'Could not find a Chrome executable on this '
        'machine, please specify it yourself.'
    )

# === NexusCore/openenv\Lib\site-packages\litellm\proxy\management_helpers\utils.py ===
# What is this?
## Helper utils for the management endpoints (keys/users/teams)
import uuid
from datetime import datetime
from functools import wraps
from typing import Optional, Tuple

from fastapi import HTTPException, Request

import litellm
from litellm._logging import verbose_logger
from litellm.proxy._types import (  # key request types; user request types; team request types; customer request types
    DeleteCustomerRequest,
    DeleteTeamRequest,
    DeleteUserRequest,
    KeyRequest,
    LiteLLM_TeamMembership,
    LiteLLM_UserTable,
    ManagementEndpointLoggingPayload,
    Member,
    SSOUserDefinedValues,
    UpdateCustomerRequest,
    UpdateKeyRequest,
    UpdateTeamRequest,
    UpdateUserRequest,
    UserAPIKeyAuth,
    VirtualKeyEvent,
)
from litellm.proxy.common_utils.http_parsing_utils import _read_request_body
from litellm.proxy.utils import PrismaClient


def get_new_internal_user_defaults(
    user_id: str, user_email: Optional[str] = None
) -> dict:
    user_info = litellm.default_internal_user_params or {}

    returned_dict: SSOUserDefinedValues = {
        "models": user_info.get("models", None),
        "max_budget": user_info.get("max_budget", litellm.max_internal_user_budget),
        "budget_duration": user_info.get(
            "budget_duration", litellm.internal_user_budget_duration
        ),
        "user_email": user_email or user_info.get("user_email", None),
        "user_id": user_id,
        "user_role": "internal_user",
    }

    non_null_dict = {}
    for k, v in returned_dict.items():
        if v is not None:
            non_null_dict[k] = v
    return non_null_dict


async def add_new_member(
    new_member: Member,
    max_budget_in_team: Optional[float],
    prisma_client: PrismaClient,
    team_id: str,
    user_api_key_dict: UserAPIKeyAuth,
    litellm_proxy_admin_name: str,
    default_team_budget_id: Optional[str] = None,
) -> Tuple[LiteLLM_UserTable, Optional[LiteLLM_TeamMembership]]:
    """
    Add a new member to a team

    - add team id to user table
    - add team member w/ budget to team member table

    Returns created/existing user + team membership w/ budget id
    """
    returned_user: Optional[LiteLLM_UserTable] = None
    returned_team_membership: Optional[LiteLLM_TeamMembership] = None
    ## ADD TEAM ID, to USER TABLE IF NEW ##
    if new_member.user_id is not None:
        new_user_defaults = get_new_internal_user_defaults(user_id=new_member.user_id)
        _returned_user = await prisma_client.db.litellm_usertable.upsert(
            where={"user_id": new_member.user_id},
            data={
                "update": {"teams": {"push": [team_id]}},
                "create": {"teams": [team_id], **new_user_defaults},  # type: ignore
            },
        )
        if _returned_user is not None:
            returned_user = LiteLLM_UserTable(**_returned_user.model_dump())
    elif new_member.user_email is not None:
        new_user_defaults = get_new_internal_user_defaults(
            user_id=str(uuid.uuid4()), user_email=new_member.user_email
        )
        ## user email is not unique acc. to prisma schema -> future improvement
        ### for now: check if it exists in db, if not - insert it
        existing_user_row: Optional[list] = await prisma_client.get_data(
            key_val={"user_email": new_member.user_email},
            table_name="user",
            query_type="find_all",
        )
        if existing_user_row is None or (
            isinstance(existing_user_row, list) and len(existing_user_row) == 0
        ):
            new_user_defaults["teams"] = [team_id]
            _returned_user = await prisma_client.insert_data(data=new_user_defaults, table_name="user")  # type: ignore

            if _returned_user is not None:
                returned_user = LiteLLM_UserTable(**_returned_user.model_dump())
        elif len(existing_user_row) == 1:
            user_info = existing_user_row[0]
            _returned_user = await prisma_client.db.litellm_usertable.update(
                where={"user_id": user_info.user_id},  # type: ignore
                data={"teams": {"push": [team_id]}},
            )
            if _returned_user is not None:
                returned_user = LiteLLM_UserTable(**_returned_user.model_dump())
        elif len(existing_user_row) > 1:
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "Multiple users with this email found in db. Please use 'user_id' instead."
                },
            )

    # Check if trying to set a budget for team member

    if max_budget_in_team is not None:
        # create a new budget item for this member
        response = await prisma_client.db.litellm_budgettable.create(
            data={
                "max_budget": max_budget_in_team,
                "created_by": user_api_key_dict.user_id or litellm_proxy_admin_name,
                "updated_by": user_api_key_dict.user_id or litellm_proxy_admin_name,
            }
        )

        _budget_id = response.budget_id
    else:
        _budget_id = default_team_budget_id

    if _budget_id and returned_user is not None and returned_user.user_id is not None:
        _returned_team_membership = (
            await prisma_client.db.litellm_teammembership.create(
                data={
                    "team_id": team_id,
                    "user_id": returned_user.user_id,
                    "budget_id": _budget_id,
                },
                include={"litellm_budget_table": True},
            )
        )

        returned_team_membership = LiteLLM_TeamMembership(
            **_returned_team_membership.model_dump()
        )

    if returned_user is None:
        raise Exception("Unable to update user table with membership information!")

    return returned_user, returned_team_membership


def _delete_user_id_from_cache(kwargs):
    from litellm.proxy.proxy_server import user_api_key_cache

    if kwargs.get("data") is not None:
        update_user_request = kwargs.get("data")
        if isinstance(update_user_request, UpdateUserRequest):
            user_api_key_cache.delete_cache(key=update_user_request.user_id)

        # delete user request
        if isinstance(update_user_request, DeleteUserRequest):
            for user_id in update_user_request.user_ids:
                user_api_key_cache.delete_cache(key=user_id)
    pass


def _delete_api_key_from_cache(kwargs):
    from litellm.proxy.proxy_server import user_api_key_cache

    if kwargs.get("data") is not None:
        update_request = kwargs.get("data")
        if isinstance(update_request, UpdateKeyRequest):
            user_api_key_cache.delete_cache(key=update_request.key)

        # delete key request
        if isinstance(update_request, KeyRequest) and update_request.keys:
            for key in update_request.keys:
                user_api_key_cache.delete_cache(key=key)
    pass


def _delete_team_id_from_cache(kwargs):
    from litellm.proxy.proxy_server import user_api_key_cache

    if kwargs.get("data") is not None:
        update_request = kwargs.get("data")
        if isinstance(update_request, UpdateTeamRequest):
            user_api_key_cache.delete_cache(key=update_request.team_id)

        # delete team request
        if isinstance(update_request, DeleteTeamRequest):
            for team_id in update_request.team_ids:
                user_api_key_cache.delete_cache(key=team_id)
    pass


def _delete_customer_id_from_cache(kwargs):
    from litellm.proxy.proxy_server import user_api_key_cache

    if kwargs.get("data") is not None:
        update_request = kwargs.get("data")
        if isinstance(update_request, UpdateCustomerRequest):
            user_api_key_cache.delete_cache(key=update_request.user_id)

        # delete customer request
        if isinstance(update_request, DeleteCustomerRequest):
            for user_id in update_request.user_ids:
                user_api_key_cache.delete_cache(key=user_id)
    pass


async def send_management_endpoint_alert(
    request_kwargs: dict,
    user_api_key_dict: UserAPIKeyAuth,
    function_name: str,
):
    """
    Sends a slack alert when:
    - A virtual key is created, updated, or deleted
    - An internal user is created, updated, or deleted
    - A team is created, updated, or deleted
    """
    from litellm.proxy.proxy_server import proxy_logging_obj
    from litellm.types.integrations.slack_alerting import AlertType

    management_function_to_event_name = {
        "generate_key_fn": AlertType.new_virtual_key_created,
        "update_key_fn": AlertType.virtual_key_updated,
        "delete_key_fn": AlertType.virtual_key_deleted,
        # Team events
        "new_team": AlertType.new_team_created,
        "update_team": AlertType.team_updated,
        "delete_team": AlertType.team_deleted,
        # Internal User events
        "new_user": AlertType.new_internal_user_created,
        "user_update": AlertType.internal_user_updated,
        "delete_user": AlertType.internal_user_deleted,
    }

    # Check if alerting is enabled
    if (
        proxy_logging_obj is not None
        and proxy_logging_obj.slack_alerting_instance is not None
    ):
        # Virtual Key Events
        if function_name in management_function_to_event_name:
            _event_name: AlertType = management_function_to_event_name[function_name]

            key_event = VirtualKeyEvent(
                created_by_user_id=user_api_key_dict.user_id or "Unknown",
                created_by_user_role=user_api_key_dict.user_role or "Unknown",
                created_by_key_alias=user_api_key_dict.key_alias,
                request_kwargs=request_kwargs,
            )

            # replace all "_" with " " and capitalize
            event_name = _event_name.replace("_", " ").title()
            await proxy_logging_obj.slack_alerting_instance.send_virtual_key_event_slack(
                key_event=key_event,
                event_name=event_name,
                alert_type=_event_name,
            )


def management_endpoint_wrapper(func):
    """
    This wrapper does the following:

    1. Log I/O, Exceptions to OTEL
    2. Create an Audit log for success calls
    """

    @wraps(func)
    async def wrapper(*args, **kwargs):
        start_time = datetime.now()
        _http_request: Optional[Request] = None
        try:
            result = await func(*args, **kwargs)
            end_time = datetime.now()
            try:
                if kwargs is None:
                    kwargs = {}
                user_api_key_dict: UserAPIKeyAuth = (
                    kwargs.get("user_api_key_dict") or UserAPIKeyAuth()
                )

                await send_management_endpoint_alert(
                    request_kwargs=kwargs,
                    user_api_key_dict=user_api_key_dict,
                    function_name=func.__name__,
                )
                _http_request = kwargs.get("http_request", None)
                parent_otel_span = getattr(user_api_key_dict, "parent_otel_span", None)
                if parent_otel_span is not None:
                    from litellm.proxy.proxy_server import open_telemetry_logger

                    if open_telemetry_logger is not None:
                        if _http_request:
                            _route = _http_request.url.path
                            _request_body: dict = await _read_request_body(
                                request=_http_request
                            )
                            _response = dict(result) if result is not None else None

                            logging_payload = ManagementEndpointLoggingPayload(
                                route=_route,
                                request_data=_request_body,
                                response=_response,
                                start_time=start_time,
                                end_time=end_time,
                            )

                            await open_telemetry_logger.async_management_endpoint_success_hook(  # type: ignore
                                logging_payload=logging_payload,
                                parent_otel_span=parent_otel_span,
                            )

                # Delete updated/deleted info from cache
                _delete_api_key_from_cache(kwargs=kwargs)
                _delete_user_id_from_cache(kwargs=kwargs)
                _delete_team_id_from_cache(kwargs=kwargs)
                _delete_customer_id_from_cache(kwargs=kwargs)
            except Exception as e:
                # Non-Blocking Exception
                verbose_logger.debug("Error in management endpoint wrapper: %s", str(e))
                pass

            return result
        except Exception as e:
            end_time = datetime.now()

            if kwargs is None:
                kwargs = {}
            user_api_key_dict: UserAPIKeyAuth = (
                kwargs.get("user_api_key_dict") or UserAPIKeyAuth()
            )
            parent_otel_span = getattr(user_api_key_dict, "parent_otel_span", None)
            if parent_otel_span is not None:
                from litellm.proxy.proxy_server import open_telemetry_logger

                if open_telemetry_logger is not None:
                    _http_request = kwargs.get("http_request")
                    if _http_request:
                        _route = _http_request.url.path
                        _request_body: dict = await _read_request_body(
                            request=_http_request
                        )
                        logging_payload = ManagementEndpointLoggingPayload(
                            route=_route,
                            request_data=_request_body,
                            response=None,
                            start_time=start_time,
                            end_time=end_time,
                            exception=e,
                        )

                        await open_telemetry_logger.async_management_endpoint_failure_hook(  # type: ignore
                            logging_payload=logging_payload,
                            parent_otel_span=parent_otel_span,
                        )

            raise e

    return wrapper

# === NexusCore/evaluation\evalplus\evalplus\evalperf.py ===
"""Compute the Differential Performance Scores (DPS) and DPS_{norm} of given samples from a model.
"""

import json
import multiprocessing
import os
from concurrent.futures import ProcessPoolExecutor, as_completed
from typing import Dict, List, Optional, Tuple

import numpy as np
from rich.console import Console
from rich.progress import (
    BarColumn,
    MofNCompleteColumn,
    Progress,
    TextColumn,
    TimeElapsedColumn,
    TimeRemainingColumn,
)
from rich.syntax import Syntax

from evalplus.data import (
    get_human_eval_plus,
    get_human_eval_plus_hash,
    get_mbpp_plus,
    get_mbpp_plus_hash,
)
from evalplus.data.mbpp import mbpp_deserialize_inputs
from evalplus.data.utils import stream_jsonl
from evalplus.eval import PASS, estimate_pass_at_k, untrusted_check
from evalplus.eval._special_oracle import MBPP_OUTPUT_NOT_NONE_TASKS
from evalplus.evaluate import get_groundtruth
from evalplus.perf.config import EVALUATION_TIMEOUT_SECOND_PER_TEST
from evalplus.perf.profile import are_profiles_broken, profile

_REFERENCE_EXEC_TIMES = 3


def check_solution(
    index: int, solution: str, dataset: str, task: Dict, expected_output: List
) -> Tuple:
    result = untrusted_check(
        dataset,
        solution,
        task["base_input"] + list(task["plus_input"]),
        task["entry_point"],
        expected_output["base"] + expected_output["plus"],
        task["atol"],
        expected_output["base_time"] + expected_output["plus_time"],
        fast_check=True,
        min_time_limit=EVALUATION_TIMEOUT_SECOND_PER_TEST,
        gt_time_limit_factor=4.0,
    )
    return index, result, solution


def get_evalplus_data():
    problems_human = get_human_eval_plus(noextreme=True)
    dataset_hash = get_human_eval_plus_hash(noextreme=True)
    expected_output_human = get_groundtruth(problems_human, dataset_hash, [])
    problems_mbpp = get_mbpp_plus(noextreme=True)
    dataset_hash = get_mbpp_plus_hash(noextreme=True)
    expected_output_mbpp = get_groundtruth(
        problems_mbpp,
        dataset_hash,
        MBPP_OUTPUT_NOT_NONE_TASKS,
    )
    problems = {**problems_human, **problems_mbpp}
    expected_output = {**expected_output_human, **expected_output_mbpp}
    return problems, expected_output


def worker_on_one_task(
    task_id: str,
    task_ref: Dict,
    samples: list,
    task: Dict,
    expected_output: Dict,
    profile_n_correct: int,
    n_workers: int,
    lazy_evaluation: bool,
):
    console = Console()
    console.print(f"Processing task: {task_id}")
    # check correctness of the solutions
    correct_solutions = []
    correct_sample_ids = []
    with ProcessPoolExecutor(max_workers=n_workers) as executor:
        futures = [
            executor.submit(
                check_solution,
                index,
                solution,
                task_id.split("/")[0].lower(),
                task,
                expected_output,
            )
            for index, solution in enumerate(samples)
        ]
        for future in as_completed(futures):
            index, result, solution = future.result()
            if result[0] == PASS:
                correct_solutions.append(solution)
            correct_sample_ids.append(index)

    if len(correct_solutions) == 0:
        console.print(f"{task_id}: 0 correct solutions")
        ret_dict = {
            "task_id": task_id,
            # basic
            "samples": samples,
            "correct_sample_ids": correct_sample_ids,
            # perf
            "dps": None,
            "dps_norm": None,
            "profiled_sample_ids": None,
            "profiled_num_instruction": None,
            "reference_num_instruction": None,
        }
        return ret_dict

    # make the order of the correct solutions consistent according to their original order
    correct_solutions = sorted(correct_solutions, key=lambda x: samples.index(x))

    # profile the model's solutions, and calculate the scores
    profiled_sample_ids = correct_sample_ids[:profile_n_correct]
    profiled_samples = correct_solutions[:profile_n_correct]

    # from slow to fast & from large to small
    n_reference = len(task_ref["reference"])
    pe_input = (
        mbpp_deserialize_inputs(task_id, task_ref["pe_input"])[0]
        if task_id.startswith("Mbpp/")
        else task_ref["pe_input"][0]
    )

    ####################################################################
    ############### Lazily profile reference solutions #################
    ####################################################################
    cache_ref_num_inst = [None] * n_reference

    def get_reference_profile(index, check_order=True) -> Optional[Tuple]:
        nonlocal cache_ref_num_inst

        assert (
            index < n_reference - 1
            and cache_ref_num_inst[index + 1] is not None
            or index == n_reference - 1
        ), f"Calling get_reference_profile({index}) before get_reference_profile({index+1}) is called, is not allowed! {n_reference = }"

        if cache_ref_num_inst[index] is not None:
            return cache_ref_num_inst[index], task_ref["scores"][index]

        evaluation_time = EVALUATION_TIMEOUT_SECOND_PER_TEST
        for _ in range(_REFERENCE_EXEC_TIMES):
            profiles = profile(
                task_ref["reference"][index],
                task["entry_point"],
                [pe_input],
                timeout_second_per_test=evaluation_time,
            )

            # Bad thing#1: timeout / failure happens
            if are_profiles_broken(profiles):
                console.print(f"{task_id}: [WARNING] Error in ref: {profiles}")
                console.print(Syntax(solution, "python"))
                console.print(f"{task_id}: Retrying w/ +5s timeout...")
                evaluation_time += 5
                continue

            # Bad thing#2: if the current #instruction is faster than that of i+1
            if index < n_reference - 1 and profiles < cache_ref_num_inst[index + 1]:
                console.print(
                    f"{task_id}: [WARNING] {index} ref faster than {index + 1}"
                )
                console.print(Syntax(solution, "python"))
                console.print(
                    f"{task_id}: Ref {index+1} avg. #inst {cache_ref_num_inst[index+1]}"
                )
                console.print(f"{task_id}: Current solution mean runtime: {profiles}")
                if check_order:
                    return None

        cache_ref_num_inst[index] = profiles
        return cache_ref_num_inst[index], task_ref["scores"][index]

    ####################################################################
    ############################## END #################################
    ####################################################################

    if not lazy_evaluation:  # compute everything ahead of time
        for i in range(n_reference - 1, -1, -1):
            if get_reference_profile(i) is None:
                break

        assert (
            None in cache_ref_num_inst
        ), f"{task_id}: Failed to profile reference: {cache_ref_num_inst = }"

    dps_scores = []
    dps_norm_scores = []
    profiled_num_inst = []
    for solution in profiled_samples:
        profiles = profile(
            solution,
            task["entry_point"],
            [pe_input],
            timeout_second_per_test=EVALUATION_TIMEOUT_SECOND_PER_TEST,
        )

        score = 0
        norm_score = 0

        # if the solution results in a timeout, score is 0
        if are_profiles_broken(profiles):
            console.print(f"{task_id}: Evaluated solution error'ed out: {profiles}")
            console.print(Syntax(solution, "python"))
        else:  # Get profiles from fast to slow:
            for j in range(n_reference - 1, -1, -1):
                ref_profile, ref_score = get_reference_profile(j, check_order=False)
                if profiles <= ref_profile:
                    score = ref_score
                    norm_score = 100 * (j + 1) / n_reference
                    break

        dps_scores.append(score)
        dps_norm_scores.append(norm_score)
        profiled_num_inst.append(profiles)

    console.print(
        f"{task_id}: {len(correct_solutions)} correct solutions, "
        f"average DPS: {float(np.mean(dps_scores)):.1f}, "
        f"average DPS_norm: {float(np.mean(dps_norm_scores)):.1f}"
    )

    return {
        "task_id": task_id,
        # basic
        "samples": samples,
        "correct_sample_ids": correct_sample_ids,
        # perf
        "dps": dps_scores,
        "dps_norm": dps_norm_scores,
        "profiled_sample_ids": profiled_sample_ids,
        "profiled_num_instruction": profiled_num_inst,
        "reference_num_instruction": cache_ref_num_inst,
    }


def script(
    samples: str,
    dataset: str,
    output_dir: str,
    profile_n_correct: int = 10,
    max_n_samples: int = 50,
    max_parallelism: int = None,
    lazy_evaluation: bool = False,
    i_just_wanna_run: bool = False,
):
    assert (
        profile_n_correct <= max_n_samples
    ), "profile_n_correct should be no more than max_n_samples"
    assert dataset.endswith(".jsonl") and os.path.isfile(dataset)
    assert samples.endswith(".jsonl") and os.path.isfile(samples)

    console = Console()  # printer

    if lazy_evaluation:
        console.print(
            "Lazy evaluation is enabled: "
            "It's faster but cannot address the order inconsistency on noisy testbed."
        )

    # load evalplus data
    problems, expected_output = get_evalplus_data()

    # load evalperf data
    with open(dataset, "r") as f:
        raw_data = [json.loads(l) for l in f]
        tasks = {task["task_id"]: task for task in raw_data}

    # setup max CPU threads
    max_workers = max(1, multiprocessing.cpu_count() // 4)
    if max_parallelism is not None:
        max_workers = min(max_workers, max_parallelism)

    model_name = os.path.basename(samples).replace(".jsonl", "")
    result_path = os.path.join(output_dir, f"{(model_name + '_results')}.json")

    # resume results
    eval_results = {}
    if not i_just_wanna_run and os.path.exists(result_path):
        eval_results = json.load(open(result_path, "r"))
        # pop tasks that have been evaluated
        for evaluated_task in eval_results:
            tasks.pop(evaluated_task, None)

        console.print(f"Resumed {len(eval_results)} results from {result_path}")

    # load model's solutions
    samples = {
        task["task_id"]: task["solution"][:max_n_samples]
        for task in stream_jsonl(samples)
    }

    # log all tasks
    console.print(f"{len(tasks)} tasks to evaluate :: result path: {result_path}")
    console.print(f"Model: {model_name}")
    console.print(f"Max CPU: {max_workers}")
    console.print(f"Max {max_n_samples} samples to check correctness per task")
    console.print(f"Of these, max {profile_n_correct} correct ones will be profiled")
    console.print(f"Tasks: {list(tasks.keys())}")

    progress_bar = Progress(
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        BarColumn(),
        MofNCompleteColumn(),
        TextColumn("•"),
        TimeElapsedColumn(),
        TextColumn("•"),
        TimeRemainingColumn(),
    )

    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        futures = [
            executor.submit(
                worker_on_one_task,
                task_id,
                task_ref,
                samples[task_id],
                problems[task_id],
                expected_output[task_id],
                profile_n_correct,
                max_workers,
                lazy_evaluation,
            )
            for task_id, task_ref in tasks.items()
        ]

        with progress_bar as p:
            for future in p.track(as_completed(futures), total=len(futures)):
                result = future.result()
                eval_results[result["task_id"]] = result

        with open(result_path, "w") as f:  # final write
            f.write(json.dumps(eval_results))

    # estimate pass@1
    total, correctness = zip(
        *[
            (len(task["samples"]), len(task["correct_sample_ids"]))
            for task in eval_results.values()
        ]
    )
    for task, pass_at_1 in zip(
        eval_results.keys(), estimate_pass_at_k(total, correctness, 1)
    ):
        eval_results[task]["pass@1"] = pass_at_1

    with open(result_path, "w") as f:
        f.write(json.dumps(eval_results))


def main():
    from fire import Fire

    Fire(script)


if __name__ == "__main__":
    main()

# === NexusCore/openenv\Lib\site-packages\tornado\process.py ===
#
# Copyright 2011 Facebook
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

"""Utilities for working with multiple processes, including both forking
the server into multiple processes and managing subprocesses.
"""

import asyncio
import os
import multiprocessing
import signal
import subprocess
import sys
import time

from binascii import hexlify

from tornado.concurrent import (
    Future,
    future_set_result_unless_cancelled,
    future_set_exception_unless_cancelled,
)
from tornado import ioloop
from tornado.iostream import PipeIOStream
from tornado.log import gen_log

import typing
from typing import Optional, Any, Callable

if typing.TYPE_CHECKING:
    from typing import List  # noqa: F401

# Re-export this exception for convenience.
CalledProcessError = subprocess.CalledProcessError


def cpu_count() -> int:
    """Returns the number of processors on this machine."""
    if multiprocessing is None:
        return 1
    try:
        return multiprocessing.cpu_count()
    except NotImplementedError:
        pass
    try:
        return os.sysconf("SC_NPROCESSORS_CONF")  # type: ignore
    except (AttributeError, ValueError):
        pass
    gen_log.error("Could not detect number of processors; assuming 1")
    return 1


def _reseed_random() -> None:
    if "random" not in sys.modules:
        return
    import random

    # If os.urandom is available, this method does the same thing as
    # random.seed (at least as of python 2.6).  If os.urandom is not
    # available, we mix in the pid in addition to a timestamp.
    try:
        seed = int(hexlify(os.urandom(16)), 16)
    except NotImplementedError:
        seed = int(time.time() * 1000) ^ os.getpid()
    random.seed(seed)


_task_id = None


def fork_processes(
    num_processes: Optional[int], max_restarts: Optional[int] = None
) -> int:
    """Starts multiple worker processes.

    If ``num_processes`` is None or <= 0, we detect the number of cores
    available on this machine and fork that number of child
    processes. If ``num_processes`` is given and > 0, we fork that
    specific number of sub-processes.

    Since we use processes and not threads, there is no shared memory
    between any server code.

    Note that multiple processes are not compatible with the autoreload
    module (or the ``autoreload=True`` option to `tornado.web.Application`
    which defaults to True when ``debug=True``).
    When using multiple processes, no IOLoops can be created or
    referenced until after the call to ``fork_processes``.

    In each child process, ``fork_processes`` returns its *task id*, a
    number between 0 and ``num_processes``.  Processes that exit
    abnormally (due to a signal or non-zero exit status) are restarted
    with the same id (up to ``max_restarts`` times).  In the parent
    process, ``fork_processes`` calls ``sys.exit(0)`` after all child
    processes have exited normally.

    max_restarts defaults to 100.

    Availability: Unix
    """
    if sys.platform == "win32":
        # The exact form of this condition matters to mypy; it understands
        # if but not assert in this context.
        raise Exception("fork not available on windows")
    if max_restarts is None:
        max_restarts = 100

    global _task_id
    assert _task_id is None
    if num_processes is None or num_processes <= 0:
        num_processes = cpu_count()
    gen_log.info("Starting %d processes", num_processes)
    children = {}

    def start_child(i: int) -> Optional[int]:
        pid = os.fork()
        if pid == 0:
            # child process
            _reseed_random()
            global _task_id
            _task_id = i
            return i
        else:
            children[pid] = i
            return None

    for i in range(num_processes):
        id = start_child(i)
        if id is not None:
            return id
    num_restarts = 0
    while children:
        pid, status = os.wait()
        if pid not in children:
            continue
        id = children.pop(pid)
        if os.WIFSIGNALED(status):
            gen_log.warning(
                "child %d (pid %d) killed by signal %d, restarting",
                id,
                pid,
                os.WTERMSIG(status),
            )
        elif os.WEXITSTATUS(status) != 0:
            gen_log.warning(
                "child %d (pid %d) exited with status %d, restarting",
                id,
                pid,
                os.WEXITSTATUS(status),
            )
        else:
            gen_log.info("child %d (pid %d) exited normally", id, pid)
            continue
        num_restarts += 1
        if num_restarts > max_restarts:
            raise RuntimeError("Too many child restarts, giving up")
        new_id = start_child(id)
        if new_id is not None:
            return new_id
    # All child processes exited cleanly, so exit the master process
    # instead of just returning to right after the call to
    # fork_processes (which will probably just start up another IOLoop
    # unless the caller checks the return value).
    sys.exit(0)


def task_id() -> Optional[int]:
    """Returns the current task id, if any.

    Returns None if this process was not created by `fork_processes`.
    """
    global _task_id
    return _task_id


class Subprocess:
    """Wraps ``subprocess.Popen`` with IOStream support.

    The constructor is the same as ``subprocess.Popen`` with the following
    additions:

    * ``stdin``, ``stdout``, and ``stderr`` may have the value
      ``tornado.process.Subprocess.STREAM``, which will make the corresponding
      attribute of the resulting Subprocess a `.PipeIOStream`. If this option
      is used, the caller is responsible for closing the streams when done
      with them.

    The ``Subprocess.STREAM`` option and the ``set_exit_callback`` and
    ``wait_for_exit`` methods do not work on Windows. There is
    therefore no reason to use this class instead of
    ``subprocess.Popen`` on that platform.

    .. versionchanged:: 5.0
       The ``io_loop`` argument (deprecated since version 4.1) has been removed.

    """

    STREAM = object()

    _initialized = False
    _waiting = {}  # type: ignore

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        self.io_loop = ioloop.IOLoop.current()
        # All FDs we create should be closed on error; those in to_close
        # should be closed in the parent process on success.
        pipe_fds = []  # type: List[int]
        to_close = []  # type: List[int]
        if kwargs.get("stdin") is Subprocess.STREAM:
            in_r, in_w = os.pipe()
            kwargs["stdin"] = in_r
            pipe_fds.extend((in_r, in_w))
            to_close.append(in_r)
            self.stdin = PipeIOStream(in_w)
        if kwargs.get("stdout") is Subprocess.STREAM:
            out_r, out_w = os.pipe()
            kwargs["stdout"] = out_w
            pipe_fds.extend((out_r, out_w))
            to_close.append(out_w)
            self.stdout = PipeIOStream(out_r)
        if kwargs.get("stderr") is Subprocess.STREAM:
            err_r, err_w = os.pipe()
            kwargs["stderr"] = err_w
            pipe_fds.extend((err_r, err_w))
            to_close.append(err_w)
            self.stderr = PipeIOStream(err_r)
        try:
            self.proc = subprocess.Popen(*args, **kwargs)
        except:
            for fd in pipe_fds:
                os.close(fd)
            raise
        for fd in to_close:
            os.close(fd)
        self.pid = self.proc.pid
        for attr in ["stdin", "stdout", "stderr"]:
            if not hasattr(self, attr):  # don't clobber streams set above
                setattr(self, attr, getattr(self.proc, attr))
        self._exit_callback = None  # type: Optional[Callable[[int], None]]
        self.returncode = None  # type: Optional[int]

    def set_exit_callback(self, callback: Callable[[int], None]) -> None:
        """Runs ``callback`` when this process exits.

        The callback takes one argument, the return code of the process.

        This method uses a ``SIGCHLD`` handler, which is a global setting
        and may conflict if you have other libraries trying to handle the
        same signal.  If you are using more than one ``IOLoop`` it may
        be necessary to call `Subprocess.initialize` first to designate
        one ``IOLoop`` to run the signal handlers.

        In many cases a close callback on the stdout or stderr streams
        can be used as an alternative to an exit callback if the
        signal handler is causing a problem.

        Availability: Unix
        """
        self._exit_callback = callback
        Subprocess.initialize()
        Subprocess._waiting[self.pid] = self
        Subprocess._try_cleanup_process(self.pid)

    def wait_for_exit(self, raise_error: bool = True) -> "Future[int]":
        """Returns a `.Future` which resolves when the process exits.

        Usage::

            ret = yield proc.wait_for_exit()

        This is a coroutine-friendly alternative to `set_exit_callback`
        (and a replacement for the blocking `subprocess.Popen.wait`).

        By default, raises `subprocess.CalledProcessError` if the process
        has a non-zero exit status. Use ``wait_for_exit(raise_error=False)``
        to suppress this behavior and return the exit status without raising.

        .. versionadded:: 4.2

        Availability: Unix
        """
        future = Future()  # type: Future[int]

        def callback(ret: int) -> None:
            if ret != 0 and raise_error:
                # Unfortunately we don't have the original args any more.
                future_set_exception_unless_cancelled(
                    future, CalledProcessError(ret, "unknown")
                )
            else:
                future_set_result_unless_cancelled(future, ret)

        self.set_exit_callback(callback)
        return future

    @classmethod
    def initialize(cls) -> None:
        """Initializes the ``SIGCHLD`` handler.

        The signal handler is run on an `.IOLoop` to avoid locking issues.
        Note that the `.IOLoop` used for signal handling need not be the
        same one used by individual Subprocess objects (as long as the
        ``IOLoops`` are each running in separate threads).

        .. versionchanged:: 5.0
           The ``io_loop`` argument (deprecated since version 4.1) has been
           removed.

        Availability: Unix
        """
        if cls._initialized:
            return
        loop = asyncio.get_event_loop()
        loop.add_signal_handler(signal.SIGCHLD, cls._cleanup)
        cls._initialized = True

    @classmethod
    def uninitialize(cls) -> None:
        """Removes the ``SIGCHLD`` handler."""
        if not cls._initialized:
            return
        loop = asyncio.get_event_loop()
        loop.remove_signal_handler(signal.SIGCHLD)
        cls._initialized = False

    @classmethod
    def _cleanup(cls) -> None:
        for pid in list(cls._waiting.keys()):  # make a copy
            cls._try_cleanup_process(pid)

    @classmethod
    def _try_cleanup_process(cls, pid: int) -> None:
        try:
            ret_pid, status = os.waitpid(pid, os.WNOHANG)  # type: ignore
        except ChildProcessError:
            return
        if ret_pid == 0:
            return
        assert ret_pid == pid
        subproc = cls._waiting.pop(pid)
        subproc.io_loop.add_callback(subproc._set_returncode, status)

    def _set_returncode(self, status: int) -> None:
        if sys.platform == "win32":
            self.returncode = -1
        else:
            if os.WIFSIGNALED(status):
                self.returncode = -os.WTERMSIG(status)
            else:
                assert os.WIFEXITED(status)
                self.returncode = os.WEXITSTATUS(status)
        # We've taken over wait() duty from the subprocess.Popen
        # object. If we don't inform it of the process's return code,
        # it will log a warning at destruction in python 3.6+.
        self.proc.returncode = self.returncode
        if self._exit_callback:
            callback = self._exit_callback
            self._exit_callback = None
            callback(self.returncode)

# === NexusCore/openenv\Lib\site-packages\google\api_core\protobuf_helpers.py ===
# Copyright 2017 Google LLC
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

"""Helpers for :mod:`protobuf`."""

import collections
import collections.abc
import copy
import inspect

from google.protobuf import field_mask_pb2
from google.protobuf import message
from google.protobuf import wrappers_pb2


_SENTINEL = object()
_WRAPPER_TYPES = (
    wrappers_pb2.BoolValue,
    wrappers_pb2.BytesValue,
    wrappers_pb2.DoubleValue,
    wrappers_pb2.FloatValue,
    wrappers_pb2.Int32Value,
    wrappers_pb2.Int64Value,
    wrappers_pb2.StringValue,
    wrappers_pb2.UInt32Value,
    wrappers_pb2.UInt64Value,
)


def from_any_pb(pb_type, any_pb):
    """Converts an ``Any`` protobuf to the specified message type.

    Args:
        pb_type (type): the type of the message that any_pb stores an instance
            of.
        any_pb (google.protobuf.any_pb2.Any): the object to be converted.

    Returns:
        pb_type: An instance of the pb_type message.

    Raises:
        TypeError: if the message could not be converted.
    """
    msg = pb_type()

    # Unwrap proto-plus wrapped messages.
    if callable(getattr(pb_type, "pb", None)):
        msg_pb = pb_type.pb(msg)
    else:
        msg_pb = msg

    # Unpack the Any object and populate the protobuf message instance.
    if not any_pb.Unpack(msg_pb):
        raise TypeError(
            f"Could not convert `{any_pb.TypeName()}` with underlying type `google.protobuf.any_pb2.Any` to `{msg_pb.DESCRIPTOR.full_name}`"
        )

    # Done; return the message.
    return msg


def check_oneof(**kwargs):
    """Raise ValueError if more than one keyword argument is not ``None``.

    Args:
        kwargs (dict): The keyword arguments sent to the function.

    Raises:
        ValueError: If more than one entry in ``kwargs`` is not ``None``.
    """
    # Sanity check: If no keyword arguments were sent, this is fine.
    if not kwargs:
        return

    not_nones = [val for val in kwargs.values() if val is not None]
    if len(not_nones) > 1:
        raise ValueError(
            "Only one of {fields} should be set.".format(
                fields=", ".join(sorted(kwargs.keys()))
            )
        )


def get_messages(module):
    """Discovers all protobuf Message classes in a given import module.

    Args:
        module (module): A Python module; :func:`dir` will be run against this
            module to find Message subclasses.

    Returns:
        dict[str, google.protobuf.message.Message]: A dictionary with the
            Message class names as keys, and the Message subclasses themselves
            as values.
    """
    answer = collections.OrderedDict()
    for name in dir(module):
        candidate = getattr(module, name)
        if inspect.isclass(candidate) and issubclass(candidate, message.Message):
            answer[name] = candidate
    return answer


def _resolve_subkeys(key, separator="."):
    """Resolve a potentially nested key.

    If the key contains the ``separator`` (e.g. ``.``) then the key will be
    split on the first instance of the subkey::

       >>> _resolve_subkeys('a.b.c')
       ('a', 'b.c')
       >>> _resolve_subkeys('d|e|f', separator='|')
       ('d', 'e|f')

    If not, the subkey will be :data:`None`::

        >>> _resolve_subkeys('foo')
        ('foo', None)

    Args:
        key (str): A string that may or may not contain the separator.
        separator (str): The namespace separator. Defaults to `.`.

    Returns:
        Tuple[str, str]: The key and subkey(s).
    """
    parts = key.split(separator, 1)

    if len(parts) > 1:
        return parts
    else:
        return parts[0], None


def get(msg_or_dict, key, default=_SENTINEL):
    """Retrieve a key's value from a protobuf Message or dictionary.

    Args:
        mdg_or_dict (Union[~google.protobuf.message.Message, Mapping]): the
            object.
        key (str): The key to retrieve from the object.
        default (Any): If the key is not present on the object, and a default
            is set, returns that default instead. A type-appropriate falsy
            default is generally recommended, as protobuf messages almost
            always have default values for unset values and it is not always
            possible to tell the difference between a falsy value and an
            unset one. If no default is set then :class:`KeyError` will be
            raised if the key is not present in the object.

    Returns:
        Any: The return value from the underlying Message or dict.

    Raises:
        KeyError: If the key is not found. Note that, for unset values,
            messages and dictionaries may not have consistent behavior.
        TypeError: If ``msg_or_dict`` is not a Message or Mapping.
    """
    # We may need to get a nested key. Resolve this.
    key, subkey = _resolve_subkeys(key)

    # Attempt to get the value from the two types of objects we know about.
    # If we get something else, complain.
    if isinstance(msg_or_dict, message.Message):
        answer = getattr(msg_or_dict, key, default)
    elif isinstance(msg_or_dict, collections.abc.Mapping):
        answer = msg_or_dict.get(key, default)
    else:
        raise TypeError(
            "get() expected a dict or protobuf message, got {!r}.".format(
                type(msg_or_dict)
            )
        )

    # If the object we got back is our sentinel, raise KeyError; this is
    # a "not found" case.
    if answer is _SENTINEL:
        raise KeyError(key)

    # If a subkey exists, call this method recursively against the answer.
    if subkey is not None and answer is not default:
        return get(answer, subkey, default=default)

    return answer


def _set_field_on_message(msg, key, value):
    """Set helper for protobuf Messages."""
    # Attempt to set the value on the types of objects we know how to deal
    # with.
    if isinstance(value, (collections.abc.MutableSequence, tuple)):
        # Clear the existing repeated protobuf message of any elements
        # currently inside it.
        while getattr(msg, key):
            getattr(msg, key).pop()

        # Write our new elements to the repeated field.
        for item in value:
            if isinstance(item, collections.abc.Mapping):
                getattr(msg, key).add(**item)
            else:
                # protobuf's RepeatedCompositeContainer doesn't support
                # append.
                getattr(msg, key).extend([item])
    elif isinstance(value, collections.abc.Mapping):
        # Assign the dictionary values to the protobuf message.
        for item_key, item_value in value.items():
            set(getattr(msg, key), item_key, item_value)
    elif isinstance(value, message.Message):
        getattr(msg, key).CopyFrom(value)
    else:
        setattr(msg, key, value)


def set(msg_or_dict, key, value):
    """Set a key's value on a protobuf Message or dictionary.

    Args:
        msg_or_dict (Union[~google.protobuf.message.Message, Mapping]): the
            object.
        key (str): The key to set.
        value (Any): The value to set.

    Raises:
        TypeError: If ``msg_or_dict`` is not a Message or dictionary.
    """
    # Sanity check: Is our target object valid?
    if not isinstance(msg_or_dict, (collections.abc.MutableMapping, message.Message)):
        raise TypeError(
            "set() expected a dict or protobuf message, got {!r}.".format(
                type(msg_or_dict)
            )
        )

    # We may be setting a nested key. Resolve this.
    basekey, subkey = _resolve_subkeys(key)

    # If a subkey exists, then get that object and call this method
    # recursively against it using the subkey.
    if subkey is not None:
        if isinstance(msg_or_dict, collections.abc.MutableMapping):
            msg_or_dict.setdefault(basekey, {})
        set(get(msg_or_dict, basekey), subkey, value)
        return

    if isinstance(msg_or_dict, collections.abc.MutableMapping):
        msg_or_dict[key] = value
    else:
        _set_field_on_message(msg_or_dict, key, value)


def setdefault(msg_or_dict, key, value):
    """Set the key on a protobuf Message or dictionary to a given value if the
    current value is falsy.

    Because protobuf Messages do not distinguish between unset values and
    falsy ones particularly well (by design), this method treats any falsy
    value (e.g. 0, empty list) as a target to be overwritten, on both Messages
    and dictionaries.

    Args:
        msg_or_dict (Union[~google.protobuf.message.Message, Mapping]): the
            object.
        key (str): The key on the object in question.
        value (Any): The value to set.

    Raises:
        TypeError: If ``msg_or_dict`` is not a Message or dictionary.
    """
    if not get(msg_or_dict, key, default=None):
        set(msg_or_dict, key, value)


def field_mask(original, modified):
    """Create a field mask by comparing two messages.

    Args:
        original (~google.protobuf.message.Message): the original message.
            If set to None, this field will be interpreted as an empty
            message.
        modified (~google.protobuf.message.Message): the modified message.
            If set to None, this field will be interpreted as an empty
            message.

    Returns:
        google.protobuf.field_mask_pb2.FieldMask: field mask that contains
        the list of field names that have different values between the two
        messages. If the messages are equivalent, then the field mask is empty.

    Raises:
        ValueError: If the ``original`` or ``modified`` are not the same type.
    """
    if original is None and modified is None:
        return field_mask_pb2.FieldMask()

    if original is None and modified is not None:
        original = copy.deepcopy(modified)
        original.Clear()

    if modified is None and original is not None:
        modified = copy.deepcopy(original)
        modified.Clear()

    if not isinstance(original, type(modified)):
        raise ValueError(
            "expected that both original and modified should be of the "
            'same type, received "{!r}" and "{!r}".'.format(
                type(original), type(modified)
            )
        )

    return field_mask_pb2.FieldMask(paths=_field_mask_helper(original, modified))


def _field_mask_helper(original, modified, current=""):
    answer = []

    for name in original.DESCRIPTOR.fields_by_name:
        field_path = _get_path(current, name)

        original_val = getattr(original, name)
        modified_val = getattr(modified, name)

        if _is_message(original_val) or _is_message(modified_val):
            if original_val != modified_val:
                # Wrapper types do not need to include the .value part of the
                # path.
                if _is_wrapper(original_val) or _is_wrapper(modified_val):
                    answer.append(field_path)
                elif not modified_val.ListFields():
                    answer.append(field_path)
                else:
                    answer.extend(
                        _field_mask_helper(original_val, modified_val, field_path)
                    )
        else:
            if original_val != modified_val:
                answer.append(field_path)

    return answer


def _get_path(current, name):
    # gapic-generator-python appends underscores to field names
    # that collide with python keywords.
    # `_` is stripped away as it is not possible to
    # natively define a field with a trailing underscore in protobuf.
    # APIs will reject field masks if fields have trailing underscores.
    # See https://github.com/googleapis/python-api-core/issues/227
    name = name.rstrip("_")
    if not current:
        return name
    return "%s.%s" % (current, name)


def _is_message(value):
    return isinstance(value, message.Message)


def _is_wrapper(value):
    return type(value) in _WRAPPER_TYPES

# === NexusCore/openenv\Lib\site-packages\IPython\core\display_functions.py ===
"""Top-level display functions for displaying object in different formats."""

# Copyright (c) IPython Development Team.
# Distributed under the terms of the Modified BSD License.


from binascii import b2a_hex
import os
import sys
import warnings

__all__ = ['display', 'clear_output', 'publish_display_data', 'update_display', 'DisplayHandle']

#-----------------------------------------------------------------------------
# utility functions
#-----------------------------------------------------------------------------


def _merge(d1, d2):
    """Like update, but merges sub-dicts instead of clobbering at the top level.

    Updates d1 in-place
    """

    if not isinstance(d2, dict) or not isinstance(d1, dict):
        return d2
    for key, value in d2.items():
        d1[key] = _merge(d1.get(key), value)
    return d1


#-----------------------------------------------------------------------------
# Main functions
#-----------------------------------------------------------------------------

# use * to indicate transient is keyword-only
def publish_display_data(data, metadata=None, *, transient=None, **kwargs):
    """Publish data and metadata to all frontends.

    See the ``display_data`` message in the messaging documentation for
    more details about this message type.

    Keys of data and metadata can be any mime-type.

    Parameters
    ----------
    data : dict
        A dictionary having keys that are valid MIME types (like
        'text/plain' or 'image/svg+xml') and values that are the data for
        that MIME type. The data itself must be a JSON'able data
        structure. Minimally all data should have the 'text/plain' data,
        which can be displayed by all frontends. If more than the plain
        text is given, it is up to the frontend to decide which
        representation to use.
    metadata : dict
        A dictionary for metadata related to the data. This can contain
        arbitrary key, value pairs that frontends can use to interpret
        the data. mime-type keys matching those in data can be used
        to specify metadata about particular representations.
    transient : dict, keyword-only
        A dictionary of transient data, such as display_id.
    """
    from IPython.core.interactiveshell import InteractiveShell

    display_pub = InteractiveShell.instance().display_pub

    # only pass transient if supplied,
    # to avoid errors with older ipykernel.
    # TODO: We could check for ipykernel version and provide a detailed upgrade message.
    if transient:
        kwargs['transient'] = transient

    display_pub.publish(
        data=data,
        metadata=metadata,
        **kwargs
    )


def _new_id():
    """Generate a new random text id with urandom"""
    return b2a_hex(os.urandom(16)).decode('ascii')


def display(
    *objs,
    include=None,
    exclude=None,
    metadata=None,
    transient=None,
    display_id=None,
    raw=False,
    clear=False,
    **kwargs,
):
    """Display a Python object in all frontends.

    By default all representations will be computed and sent to the frontends.
    Frontends can decide which representation is used and how.

    In terminal IPython this will be similar to using :func:`print`, for use in richer
    frontends see Jupyter notebook examples with rich display logic.

    Parameters
    ----------
    *objs : object
        The Python objects to display.
    raw : bool, optional
        Are the objects to be displayed already mimetype-keyed dicts of raw display data,
        or Python objects that need to be formatted before display? [default: False]
    include : list, tuple or set, optional
        A list of format type strings (MIME types) to include in the
        format data dict. If this is set *only* the format types included
        in this list will be computed.
    exclude : list, tuple or set, optional
        A list of format type strings (MIME types) to exclude in the format
        data dict. If this is set all format types will be computed,
        except for those included in this argument.
    metadata : dict, optional
        A dictionary of metadata to associate with the output.
        mime-type keys in this dictionary will be associated with the individual
        representation formats, if they exist.
    transient : dict, optional
        A dictionary of transient data to associate with the output.
        Data in this dict should not be persisted to files (e.g. notebooks).
    display_id : str, bool optional
        Set an id for the display.
        This id can be used for updating this display area later via update_display.
        If given as `True`, generate a new `display_id`
    clear : bool, optional
        Should the output area be cleared before displaying anything? If True,
        this will wait for additional output before clearing. [default: False]
    **kwargs : additional keyword-args, optional
        Additional keyword-arguments are passed through to the display publisher.

    Returns
    -------
    handle: DisplayHandle
        Returns a handle on updatable displays for use with :func:`update_display`,
        if `display_id` is given. Returns :any:`None` if no `display_id` is given
        (default).

    Examples
    --------
    >>> class Json(object):
    ...     def __init__(self, json):
    ...         self.json = json
    ...     def _repr_pretty_(self, pp, cycle):
    ...         import json
    ...         pp.text(json.dumps(self.json, indent=2))
    ...     def __repr__(self):
    ...         return str(self.json)
    ...

    >>> d = Json({1:2, 3: {4:5}})

    >>> print(d)
    {1: 2, 3: {4: 5}}

    >>> display(d)
    {
      "1": 2,
      "3": {
        "4": 5
      }
    }

    >>> def int_formatter(integer, pp, cycle):
    ...     pp.text('I'*integer)

    >>> plain = get_ipython().display_formatter.formatters['text/plain']
    >>> plain.for_type(int, int_formatter)
    <function _repr_pprint at 0x...>
    >>> display(7-5)
    II

    >>> del plain.type_printers[int]
    >>> display(7-5)
    2

    See Also
    --------
    :func:`update_display`

    Notes
    -----
    In Python, objects can declare their textual representation using the
    `__repr__` method. IPython expands on this idea and allows objects to declare
    other, rich representations including:

      - HTML
      - JSON
      - PNG
      - JPEG
      - SVG
      - LaTeX

    A single object can declare some or all of these representations; all are
    handled by IPython's display system.

    The main idea of the first approach is that you have to implement special
    display methods when you define your class, one for each representation you
    want to use. Here is a list of the names of the special methods and the
    values they must return:

      - `_repr_html_`: return raw HTML as a string, or a tuple (see below).
      - `_repr_json_`: return a JSONable dict, or a tuple (see below).
      - `_repr_jpeg_`: return raw JPEG data, or a tuple (see below).
      - `_repr_png_`: return raw PNG data, or a tuple (see below).
      - `_repr_svg_`: return raw SVG data as a string, or a tuple (see below).
      - `_repr_latex_`: return LaTeX commands in a string surrounded by "$",
                        or a tuple (see below).
      - `_repr_mimebundle_`: return a full mimebundle containing the mapping
                             from all mimetypes to data.
                             Use this for any mime-type not listed above.

    The above functions may also return the object's metadata alonside the
    data.  If the metadata is available, the functions will return a tuple
    containing the data and metadata, in that order.  If there is no metadata
    available, then the functions will return the data only.

    When you are directly writing your own classes, you can adapt them for
    display in IPython by following the above approach. But in practice, you
    often need to work with existing classes that you can't easily modify.

    You can refer to the documentation on integrating with the display system in
    order to register custom formatters for already existing types
    (:ref:`integrating_rich_display`).

    .. versionadded:: 5.4 display available without import
    .. versionadded:: 6.1 display available without import

    Since IPython 5.4 and 6.1 :func:`display` is automatically made available to
    the user without import. If you are using display in a document that might
    be used in a pure python context or with older version of IPython, use the
    following import at the top of your file::

        from IPython.display import display

    """
    from IPython.core.interactiveshell import InteractiveShell

    if not InteractiveShell.initialized():
        # Directly print objects.
        print(*objs)
        return

    if transient is None:
        transient = {}
    if metadata is None:
        metadata={}
    if display_id:
        if display_id is True:
            display_id = _new_id()
        transient['display_id'] = display_id
    if kwargs.get('update') and 'display_id' not in transient:
        raise TypeError('display_id required for update_display')
    if transient:
        kwargs['transient'] = transient

    if not objs and display_id:
        # if given no objects, but still a request for a display_id,
        # we assume the user wants to insert an empty output that
        # can be updated later
        objs = [{}]
        raw = True

    if not raw:
        format = InteractiveShell.instance().display_formatter.format

    if clear:
        clear_output(wait=True)

    for obj in objs:
        if raw:
            publish_display_data(data=obj, metadata=metadata, **kwargs)
        else:
            format_dict, md_dict = format(obj, include=include, exclude=exclude)
            if not format_dict:
                # nothing to display (e.g. _ipython_display_ took over)
                continue
            if metadata:
                # kwarg-specified metadata gets precedence
                _merge(md_dict, metadata)
            publish_display_data(data=format_dict, metadata=md_dict, **kwargs)
    if display_id:
        return DisplayHandle(display_id)


# use * for keyword-only display_id arg
def update_display(obj, *, display_id, **kwargs):
    """Update an existing display by id

    Parameters
    ----------
    obj
        The object with which to update the display
    display_id : keyword-only
        The id of the display to update

    See Also
    --------
    :func:`display`
    """
    kwargs['update'] = True
    display(obj, display_id=display_id, **kwargs)


class DisplayHandle:
    """A handle on an updatable display

    Call `.update(obj)` to display a new object.

    Call `.display(obj`) to add a new instance of this display,
    and update existing instances.

    See Also
    --------

        :func:`display`, :func:`update_display`

    """

    def __init__(self, display_id=None):
        if display_id is None:
            display_id = _new_id()
        self.display_id = display_id

    def __repr__(self):
        return "<%s display_id=%s>" % (self.__class__.__name__, self.display_id)

    def display(self, obj, **kwargs):
        """Make a new display with my id, updating existing instances.

        Parameters
        ----------
        obj
            object to display
        **kwargs
            additional keyword arguments passed to display
        """
        display(obj, display_id=self.display_id, **kwargs)

    def update(self, obj, **kwargs):
        """Update existing displays with my id

        Parameters
        ----------
        obj
            object to display
        **kwargs
            additional keyword arguments passed to update_display
        """
        update_display(obj, display_id=self.display_id, **kwargs)


def clear_output(wait=False):
    """Clear the output of the current cell receiving output.

    Parameters
    ----------
    wait : bool [default: false]
        Wait to clear the output until new output is available to replace it."""
    from IPython.core.interactiveshell import InteractiveShell
    if InteractiveShell.initialized():
        InteractiveShell.instance().display_pub.clear_output(wait)
    else:
        print('\033[2K\r', end='')
        sys.stdout.flush()
        print('\033[2K\r', end='')
        sys.stderr.flush()

# === NexusCore/openenv\Lib\site-packages\jedi\inference\filters.py ===
"""
Filters are objects that you can use to filter names in different scopes. They
are needed for name resolution.
"""
from abc import abstractmethod
from typing import List, MutableMapping, Type
import weakref

from parso.tree import search_ancestor
from parso.python.tree import Name, UsedNamesMapping

from jedi.inference import flow_analysis
from jedi.inference.base_value import ValueSet, ValueWrapper, \
    LazyValueWrapper
from jedi.parser_utils import get_cached_parent_scope, get_parso_cache_node
from jedi.inference.utils import to_list
from jedi.inference.names import TreeNameDefinition, ParamName, \
    AnonymousParamName, AbstractNameDefinition, NameWrapper

_definition_name_cache: MutableMapping[UsedNamesMapping, List[Name]]
_definition_name_cache = weakref.WeakKeyDictionary()


class AbstractFilter:
    _until_position = None

    def _filter(self, names):
        if self._until_position is not None:
            return [n for n in names if n.start_pos < self._until_position]
        return names

    @abstractmethod
    def get(self, name):
        raise NotImplementedError

    @abstractmethod
    def values(self):
        raise NotImplementedError


class FilterWrapper:
    name_wrapper_class: Type[NameWrapper]

    def __init__(self, wrapped_filter):
        self._wrapped_filter = wrapped_filter

    def wrap_names(self, names):
        return [self.name_wrapper_class(name) for name in names]

    def get(self, name):
        return self.wrap_names(self._wrapped_filter.get(name))

    def values(self):
        return self.wrap_names(self._wrapped_filter.values())


def _get_definition_names(parso_cache_node, used_names, name_key):
    if parso_cache_node is None:
        names = used_names.get(name_key, ())
        return tuple(name for name in names if name.is_definition(include_setitem=True))

    try:
        for_module = _definition_name_cache[parso_cache_node]
    except KeyError:
        for_module = _definition_name_cache[parso_cache_node] = {}

    try:
        return for_module[name_key]
    except KeyError:
        names = used_names.get(name_key, ())
        result = for_module[name_key] = tuple(
            name for name in names if name.is_definition(include_setitem=True)
        )
        return result


class _AbstractUsedNamesFilter(AbstractFilter):
    name_class = TreeNameDefinition

    def __init__(self, parent_context, node_context=None):
        if node_context is None:
            node_context = parent_context
        self._node_context = node_context
        self._parser_scope = node_context.tree_node
        module_context = node_context.get_root_context()
        # It is quite hacky that we have to use that. This is for caching
        # certain things with a WeakKeyDictionary. However, parso intentionally
        # uses slots (to save memory) and therefore we end up with having to
        # have a weak reference to the object that caches the tree.
        #
        # Previously we have tried to solve this by using a weak reference onto
        # used_names. However that also does not work, because it has a
        # reference from the module, which itself is referenced by any node
        # through parents.
        path = module_context.py__file__()
        if path is None:
            # If the path is None, there is no guarantee that parso caches it.
            self._parso_cache_node = None
        else:
            self._parso_cache_node = get_parso_cache_node(
                module_context.inference_state.latest_grammar
                if module_context.is_stub() else module_context.inference_state.grammar,
                path
            )
        self._used_names = module_context.tree_node.get_used_names()
        self.parent_context = parent_context

    def get(self, name):
        return self._convert_names(self._filter(
            _get_definition_names(self._parso_cache_node, self._used_names, name),
        ))

    def _convert_names(self, names):
        return [self.name_class(self.parent_context, name) for name in names]

    def values(self):
        return self._convert_names(
            name
            for name_key in self._used_names
            for name in self._filter(
                _get_definition_names(self._parso_cache_node, self._used_names, name_key),
            )
        )

    def __repr__(self):
        return '<%s: %s>' % (self.__class__.__name__, self.parent_context)


class ParserTreeFilter(_AbstractUsedNamesFilter):
    def __init__(self, parent_context, node_context=None, until_position=None,
                 origin_scope=None):
        """
        node_context is an option to specify a second value for use cases
        like the class mro where the parent class of a new name would be the
        value, but for some type inference it's important to have a local
        value of the other classes.
        """
        super().__init__(parent_context, node_context)
        self._origin_scope = origin_scope
        self._until_position = until_position

    def _filter(self, names):
        names = super()._filter(names)
        names = [n for n in names if self._is_name_reachable(n)]
        return list(self._check_flows(names))

    def _is_name_reachable(self, name):
        parent = name.parent
        if parent.type == 'trailer':
            return False
        base_node = parent if parent.type in ('classdef', 'funcdef') else name
        return get_cached_parent_scope(self._parso_cache_node, base_node) == self._parser_scope

    def _check_flows(self, names):
        for name in sorted(names, key=lambda name: name.start_pos, reverse=True):
            check = flow_analysis.reachability_check(
                context=self._node_context,
                value_scope=self._parser_scope,
                node=name,
                origin_scope=self._origin_scope
            )
            if check is not flow_analysis.UNREACHABLE:
                yield name

            if check is flow_analysis.REACHABLE:
                break


class _FunctionExecutionFilter(ParserTreeFilter):
    def __init__(self, parent_context, function_value, until_position, origin_scope):
        super().__init__(
            parent_context,
            until_position=until_position,
            origin_scope=origin_scope,
        )
        self._function_value = function_value

    def _convert_param(self, param, name):
        raise NotImplementedError

    @to_list
    def _convert_names(self, names):
        for name in names:
            param = search_ancestor(name, 'param')
            # Here we don't need to check if the param is a default/annotation,
            # because those are not definitions and never make it to this
            # point.
            if param:
                yield self._convert_param(param, name)
            else:
                yield TreeNameDefinition(self.parent_context, name)


class FunctionExecutionFilter(_FunctionExecutionFilter):
    def __init__(self, *args, arguments, **kwargs):
        super().__init__(*args, **kwargs)
        self._arguments = arguments

    def _convert_param(self, param, name):
        return ParamName(self._function_value, name, self._arguments)


class AnonymousFunctionExecutionFilter(_FunctionExecutionFilter):
    def _convert_param(self, param, name):
        return AnonymousParamName(self._function_value, name)


class GlobalNameFilter(_AbstractUsedNamesFilter):
    def get(self, name):
        try:
            names = self._used_names[name]
        except KeyError:
            return []
        return self._convert_names(self._filter(names))

    @to_list
    def _filter(self, names):
        for name in names:
            if name.parent.type == 'global_stmt':
                yield name

    def values(self):
        return self._convert_names(
            name for name_list in self._used_names.values()
            for name in self._filter(name_list)
        )


class DictFilter(AbstractFilter):
    def __init__(self, dct):
        self._dct = dct

    def get(self, name):
        try:
            value = self._convert(name, self._dct[name])
        except KeyError:
            return []
        else:
            return list(self._filter([value]))

    def values(self):
        def yielder():
            for item in self._dct.items():
                try:
                    yield self._convert(*item)
                except KeyError:
                    pass
        return self._filter(yielder())

    def _convert(self, name, value):
        return value

    def __repr__(self):
        keys = ', '.join(self._dct.keys())
        return '<%s: for {%s}>' % (self.__class__.__name__, keys)


class MergedFilter:
    def __init__(self, *filters):
        self._filters = filters

    def get(self, name):
        return [n for filter in self._filters for n in filter.get(name)]

    def values(self):
        return [n for filter in self._filters for n in filter.values()]

    def __repr__(self):
        return '%s(%s)' % (self.__class__.__name__, ', '.join(str(f) for f in self._filters))


class _BuiltinMappedMethod(ValueWrapper):
    """``Generator.__next__`` ``dict.values`` methods and so on."""
    api_type = 'function'

    def __init__(self, value, method, builtin_func):
        super().__init__(builtin_func)
        self._value = value
        self._method = method

    def py__call__(self, arguments):
        # TODO add TypeError if params are given/or not correct.
        return self._method(self._value, arguments)


class SpecialMethodFilter(DictFilter):
    """
    A filter for methods that are defined in this module on the corresponding
    classes like Generator (for __next__, etc).
    """
    class SpecialMethodName(AbstractNameDefinition):
        api_type = 'function'

        def __init__(self, parent_context, string_name, callable_, builtin_value):
            self.parent_context = parent_context
            self.string_name = string_name
            self._callable = callable_
            self._builtin_value = builtin_value

        def infer(self):
            for filter in self._builtin_value.get_filters():
                # We can take the first index, because on builtin methods there's
                # always only going to be one name. The same is true for the
                # inferred values.
                for name in filter.get(self.string_name):
                    builtin_func = next(iter(name.infer()))
                    break
                else:
                    continue
                break
            return ValueSet([
                _BuiltinMappedMethod(self.parent_context, self._callable, builtin_func)
            ])

    def __init__(self, value, dct, builtin_value):
        super().__init__(dct)
        self.value = value
        self._builtin_value = builtin_value
        """
        This value is what will be used to introspect the name, where as the
        other value will be used to execute the function.

        We distinguish, because we have to.
        """

    def _convert(self, name, value):
        return self.SpecialMethodName(self.value, name, value, self._builtin_value)


class _OverwriteMeta(type):
    def __init__(cls, name, bases, dct):
        super().__init__(name, bases, dct)

        base_dct = {}
        for base_cls in reversed(cls.__bases__):
            try:
                base_dct.update(base_cls.overwritten_methods)
            except AttributeError:
                pass

        for func in cls.__dict__.values():
            try:
                base_dct.update(func.registered_overwritten_methods)
            except AttributeError:
                pass
        cls.overwritten_methods = base_dct


class _AttributeOverwriteMixin:
    def get_filters(self, *args, **kwargs):
        yield SpecialMethodFilter(self, self.overwritten_methods, self._wrapped_value)
        yield from self._wrapped_value.get_filters(*args, **kwargs)


class LazyAttributeOverwrite(_AttributeOverwriteMixin, LazyValueWrapper,
                             metaclass=_OverwriteMeta):
    def __init__(self, inference_state):
        self.inference_state = inference_state


class AttributeOverwrite(_AttributeOverwriteMixin, ValueWrapper,
                         metaclass=_OverwriteMeta):
    pass


def publish_method(method_name):
    def decorator(func):
        dct = func.__dict__.setdefault('registered_overwritten_methods', {})
        dct[method_name] = func
        return func
    return decorator

# === NexusCore/openenv\Lib\site-packages\dateutil\tz\win.py ===
# -*- coding: utf-8 -*-
"""
This module provides an interface to the native time zone data on Windows,
including :py:class:`datetime.tzinfo` implementations.

Attempting to import this module on a non-Windows platform will raise an
:py:obj:`ImportError`.
"""
# This code was originally contributed by Jeffrey Harris.
import datetime
import struct

from six.moves import winreg
from six import text_type

try:
    import ctypes
    from ctypes import wintypes
except ValueError:
    # ValueError is raised on non-Windows systems for some horrible reason.
    raise ImportError("Running tzwin on non-Windows system")

from ._common import tzrangebase

__all__ = ["tzwin", "tzwinlocal", "tzres"]

ONEWEEK = datetime.timedelta(7)

TZKEYNAMENT = r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\Time Zones"
TZKEYNAME9X = r"SOFTWARE\Microsoft\Windows\CurrentVersion\Time Zones"
TZLOCALKEYNAME = r"SYSTEM\CurrentControlSet\Control\TimeZoneInformation"


def _settzkeyname():
    handle = winreg.ConnectRegistry(None, winreg.HKEY_LOCAL_MACHINE)
    try:
        winreg.OpenKey(handle, TZKEYNAMENT).Close()
        TZKEYNAME = TZKEYNAMENT
    except WindowsError:
        TZKEYNAME = TZKEYNAME9X
    handle.Close()
    return TZKEYNAME


TZKEYNAME = _settzkeyname()


class tzres(object):
    """
    Class for accessing ``tzres.dll``, which contains timezone name related
    resources.

    .. versionadded:: 2.5.0
    """
    p_wchar = ctypes.POINTER(wintypes.WCHAR)        # Pointer to a wide char

    def __init__(self, tzres_loc='tzres.dll'):
        # Load the user32 DLL so we can load strings from tzres
        user32 = ctypes.WinDLL('user32')

        # Specify the LoadStringW function
        user32.LoadStringW.argtypes = (wintypes.HINSTANCE,
                                       wintypes.UINT,
                                       wintypes.LPWSTR,
                                       ctypes.c_int)

        self.LoadStringW = user32.LoadStringW
        self._tzres = ctypes.WinDLL(tzres_loc)
        self.tzres_loc = tzres_loc

    def load_name(self, offset):
        """
        Load a timezone name from a DLL offset (integer).

        >>> from dateutil.tzwin import tzres
        >>> tzr = tzres()
        >>> print(tzr.load_name(112))
        'Eastern Standard Time'

        :param offset:
            A positive integer value referring to a string from the tzres dll.

        .. note::

            Offsets found in the registry are generally of the form
            ``@tzres.dll,-114``. The offset in this case is 114, not -114.

        """
        resource = self.p_wchar()
        lpBuffer = ctypes.cast(ctypes.byref(resource), wintypes.LPWSTR)
        nchar = self.LoadStringW(self._tzres._handle, offset, lpBuffer, 0)
        return resource[:nchar]

    def name_from_string(self, tzname_str):
        """
        Parse strings as returned from the Windows registry into the time zone
        name as defined in the registry.

        >>> from dateutil.tzwin import tzres
        >>> tzr = tzres()
        >>> print(tzr.name_from_string('@tzres.dll,-251'))
        'Dateline Daylight Time'
        >>> print(tzr.name_from_string('Eastern Standard Time'))
        'Eastern Standard Time'

        :param tzname_str:
            A timezone name string as returned from a Windows registry key.

        :return:
            Returns the localized timezone string from tzres.dll if the string
            is of the form `@tzres.dll,-offset`, else returns the input string.
        """
        if not tzname_str.startswith('@'):
            return tzname_str

        name_splt = tzname_str.split(',-')
        try:
            offset = int(name_splt[1])
        except:
            raise ValueError("Malformed timezone string.")

        return self.load_name(offset)


class tzwinbase(tzrangebase):
    """tzinfo class based on win32's timezones available in the registry."""
    def __init__(self):
        raise NotImplementedError('tzwinbase is an abstract base class')

    def __eq__(self, other):
        # Compare on all relevant dimensions, including name.
        if not isinstance(other, tzwinbase):
            return NotImplemented

        return  (self._std_offset == other._std_offset and
                 self._dst_offset == other._dst_offset and
                 self._stddayofweek == other._stddayofweek and
                 self._dstdayofweek == other._dstdayofweek and
                 self._stdweeknumber == other._stdweeknumber and
                 self._dstweeknumber == other._dstweeknumber and
                 self._stdhour == other._stdhour and
                 self._dsthour == other._dsthour and
                 self._stdminute == other._stdminute and
                 self._dstminute == other._dstminute and
                 self._std_abbr == other._std_abbr and
                 self._dst_abbr == other._dst_abbr)

    @staticmethod
    def list():
        """Return a list of all time zones known to the system."""
        with winreg.ConnectRegistry(None, winreg.HKEY_LOCAL_MACHINE) as handle:
            with winreg.OpenKey(handle, TZKEYNAME) as tzkey:
                result = [winreg.EnumKey(tzkey, i)
                          for i in range(winreg.QueryInfoKey(tzkey)[0])]
        return result

    def display(self):
        """
        Return the display name of the time zone.
        """
        return self._display

    def transitions(self, year):
        """
        For a given year, get the DST on and off transition times, expressed
        always on the standard time side. For zones with no transitions, this
        function returns ``None``.

        :param year:
            The year whose transitions you would like to query.

        :return:
            Returns a :class:`tuple` of :class:`datetime.datetime` objects,
            ``(dston, dstoff)`` for zones with an annual DST transition, or
            ``None`` for fixed offset zones.
        """

        if not self.hasdst:
            return None

        dston = picknthweekday(year, self._dstmonth, self._dstdayofweek,
                               self._dsthour, self._dstminute,
                               self._dstweeknumber)

        dstoff = picknthweekday(year, self._stdmonth, self._stddayofweek,
                                self._stdhour, self._stdminute,
                                self._stdweeknumber)

        # Ambiguous dates default to the STD side
        dstoff -= self._dst_base_offset

        return dston, dstoff

    def _get_hasdst(self):
        return self._dstmonth != 0

    @property
    def _dst_base_offset(self):
        return self._dst_base_offset_


class tzwin(tzwinbase):
    """
    Time zone object created from the zone info in the Windows registry

    These are similar to :py:class:`dateutil.tz.tzrange` objects in that
    the time zone data is provided in the format of a single offset rule
    for either 0 or 2 time zone transitions per year.

    :param: name
        The name of a Windows time zone key, e.g. "Eastern Standard Time".
        The full list of keys can be retrieved with :func:`tzwin.list`.
    """

    def __init__(self, name):
        self._name = name

        with winreg.ConnectRegistry(None, winreg.HKEY_LOCAL_MACHINE) as handle:
            tzkeyname = text_type("{kn}\\{name}").format(kn=TZKEYNAME, name=name)
            with winreg.OpenKey(handle, tzkeyname) as tzkey:
                keydict = valuestodict(tzkey)

        self._std_abbr = keydict["Std"]
        self._dst_abbr = keydict["Dlt"]

        self._display = keydict["Display"]

        # See http://ww_winreg.jsiinc.com/SUBA/tip0300/rh0398.htm
        tup = struct.unpack("=3l16h", keydict["TZI"])
        stdoffset = -tup[0]-tup[1]          # Bias + StandardBias * -1
        dstoffset = stdoffset-tup[2]        # + DaylightBias * -1
        self._std_offset = datetime.timedelta(minutes=stdoffset)
        self._dst_offset = datetime.timedelta(minutes=dstoffset)

        # for the meaning see the win32 TIME_ZONE_INFORMATION structure docs
        # http://msdn.microsoft.com/en-us/library/windows/desktop/ms725481(v=vs.85).aspx
        (self._stdmonth,
         self._stddayofweek,   # Sunday = 0
         self._stdweeknumber,  # Last = 5
         self._stdhour,
         self._stdminute) = tup[4:9]

        (self._dstmonth,
         self._dstdayofweek,   # Sunday = 0
         self._dstweeknumber,  # Last = 5
         self._dsthour,
         self._dstminute) = tup[12:17]

        self._dst_base_offset_ = self._dst_offset - self._std_offset
        self.hasdst = self._get_hasdst()

    def __repr__(self):
        return "tzwin(%s)" % repr(self._name)

    def __reduce__(self):
        return (self.__class__, (self._name,))


class tzwinlocal(tzwinbase):
    """
    Class representing the local time zone information in the Windows registry

    While :class:`dateutil.tz.tzlocal` makes system calls (via the :mod:`time`
    module) to retrieve time zone information, ``tzwinlocal`` retrieves the
    rules directly from the Windows registry and creates an object like
    :class:`dateutil.tz.tzwin`.

    Because Windows does not have an equivalent of :func:`time.tzset`, on
    Windows, :class:`dateutil.tz.tzlocal` instances will always reflect the
    time zone settings *at the time that the process was started*, meaning
    changes to the machine's time zone settings during the run of a program
    on Windows will **not** be reflected by :class:`dateutil.tz.tzlocal`.
    Because ``tzwinlocal`` reads the registry directly, it is unaffected by
    this issue.
    """
    def __init__(self):
        with winreg.ConnectRegistry(None, winreg.HKEY_LOCAL_MACHINE) as handle:
            with winreg.OpenKey(handle, TZLOCALKEYNAME) as tzlocalkey:
                keydict = valuestodict(tzlocalkey)

            self._std_abbr = keydict["StandardName"]
            self._dst_abbr = keydict["DaylightName"]

            try:
                tzkeyname = text_type('{kn}\\{sn}').format(kn=TZKEYNAME,
                                                          sn=self._std_abbr)
                with winreg.OpenKey(handle, tzkeyname) as tzkey:
                    _keydict = valuestodict(tzkey)
                    self._display = _keydict["Display"]
            except OSError:
                self._display = None

        stdoffset = -keydict["Bias"]-keydict["StandardBias"]
        dstoffset = stdoffset-keydict["DaylightBias"]

        self._std_offset = datetime.timedelta(minutes=stdoffset)
        self._dst_offset = datetime.timedelta(minutes=dstoffset)

        # For reasons unclear, in this particular key, the day of week has been
        # moved to the END of the SYSTEMTIME structure.
        tup = struct.unpack("=8h", keydict["StandardStart"])

        (self._stdmonth,
         self._stdweeknumber,  # Last = 5
         self._stdhour,
         self._stdminute) = tup[1:5]

        self._stddayofweek = tup[7]

        tup = struct.unpack("=8h", keydict["DaylightStart"])

        (self._dstmonth,
         self._dstweeknumber,  # Last = 5
         self._dsthour,
         self._dstminute) = tup[1:5]

        self._dstdayofweek = tup[7]

        self._dst_base_offset_ = self._dst_offset - self._std_offset
        self.hasdst = self._get_hasdst()

    def __repr__(self):
        return "tzwinlocal()"

    def __str__(self):
        # str will return the standard name, not the daylight name.
        return "tzwinlocal(%s)" % repr(self._std_abbr)

    def __reduce__(self):
        return (self.__class__, ())


def picknthweekday(year, month, dayofweek, hour, minute, whichweek):
    """ dayofweek == 0 means Sunday, whichweek 5 means last instance """
    first = datetime.datetime(year, month, 1, hour, minute)

    # This will work if dayofweek is ISO weekday (1-7) or Microsoft-style (0-6),
    # Because 7 % 7 = 0
    weekdayone = first.replace(day=((dayofweek - first.isoweekday()) % 7) + 1)
    wd = weekdayone + ((whichweek - 1) * ONEWEEK)
    if (wd.month != month):
        wd -= ONEWEEK

    return wd


def valuestodict(key):
    """Convert a registry key's values to a dictionary."""
    dout = {}
    size = winreg.QueryInfoKey(key)[1]
    tz_res = None

    for i in range(size):
        key_name, value, dtype = winreg.EnumValue(key, i)
        if dtype == winreg.REG_DWORD or dtype == winreg.REG_DWORD_LITTLE_ENDIAN:
            # If it's a DWORD (32-bit integer), it's stored as unsigned - convert
            # that to a proper signed integer
            if value & (1 << 31):
                value = value - (1 << 32)
        elif dtype == winreg.REG_SZ:
            # If it's a reference to the tzres DLL, load the actual string
            if value.startswith('@tzres'):
                tz_res = tz_res or tzres()
                value = tz_res.name_from_string(value)

            value = value.rstrip('\x00')    # Remove trailing nulls

        dout[key_name] = value

    return dout

# === NexusCore/openenv\Lib\site-packages\google\oauth2\id_token.py ===
# Copyright 2016 Google LLC
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

"""Google ID Token helpers.

Provides support for verifying `OpenID Connect ID Tokens`_, especially ones
generated by Google infrastructure.

To parse and verify an ID Token issued by Google's OAuth 2.0 authorization
server use :func:`verify_oauth2_token`. To verify an ID Token issued by
Firebase, use :func:`verify_firebase_token`.

A general purpose ID Token verifier is available as :func:`verify_token`.

Example::

    from google.oauth2 import id_token
    from google.auth.transport import requests

    request = requests.Request()

    id_info = id_token.verify_oauth2_token(
        token, request, 'my-client-id.example.com')

    userid = id_info['sub']

By default, this will re-fetch certificates for each verification. Because
Google's public keys are only changed infrequently (on the order of once per
day), you may wish to take advantage of caching to reduce latency and the
potential for network errors. This can be accomplished using an external
library like `CacheControl`_ to create a cache-aware
:class:`google.auth.transport.Request`::

    import cachecontrol
    import google.auth.transport.requests
    import requests

    session = requests.session()
    cached_session = cachecontrol.CacheControl(session)
    request = google.auth.transport.requests.Request(session=cached_session)

.. _OpenID Connect ID Tokens:
    http://openid.net/specs/openid-connect-core-1_0.html#IDToken
.. _CacheControl: https://cachecontrol.readthedocs.io
"""

import http.client as http_client
import json
import os

from google.auth import environment_vars
from google.auth import exceptions
from google.auth import jwt


# The URL that provides public certificates for verifying ID tokens issued
# by Google's OAuth 2.0 authorization server.
_GOOGLE_OAUTH2_CERTS_URL = "https://www.googleapis.com/oauth2/v1/certs"

# The URL that provides public certificates for verifying ID tokens issued
# by Firebase and the Google APIs infrastructure
_GOOGLE_APIS_CERTS_URL = (
    "https://www.googleapis.com/robot/v1/metadata/x509"
    "/securetoken@system.gserviceaccount.com"
)

_GOOGLE_ISSUERS = ["accounts.google.com", "https://accounts.google.com"]


def _fetch_certs(request, certs_url):
    """Fetches certificates.

    Google-style cerificate endpoints return JSON in the format of
    ``{'key id': 'x509 certificate'}`` or a certificate array according
    to the JWK spec (see https://tools.ietf.org/html/rfc7517).

    Args:
        request (google.auth.transport.Request): The object used to make
            HTTP requests.
        certs_url (str): The certificate endpoint URL.

    Returns:
        Mapping[str, str] | Mapping[str, list]: A mapping of public keys
        in x.509 or JWK spec.
    """
    response = request(certs_url, method="GET")

    if response.status != http_client.OK:
        raise exceptions.TransportError(
            "Could not fetch certificates at {}".format(certs_url)
        )

    return json.loads(response.data.decode("utf-8"))


def verify_token(
    id_token,
    request,
    audience=None,
    certs_url=_GOOGLE_OAUTH2_CERTS_URL,
    clock_skew_in_seconds=0,
):
    """Verifies an ID token and returns the decoded token.

    Args:
        id_token (Union[str, bytes]): The encoded token.
        request (google.auth.transport.Request): The object used to make
            HTTP requests.
        audience (str or list): The audience or audiences that this token is
            intended for. If None then the audience is not verified.
        certs_url (str): The URL that specifies the certificates to use to
            verify the token. This URL should return JSON in the format of
            ``{'key id': 'x509 certificate'}`` or a certificate array according to
            the JWK spec (see https://tools.ietf.org/html/rfc7517).
        clock_skew_in_seconds (int): The clock skew used for `iat` and `exp`
            validation.

    Returns:
        Mapping[str, Any]: The decoded token.
    """
    certs = _fetch_certs(request, certs_url)

    if "keys" in certs:
        try:
            import jwt as jwt_lib  # type: ignore
        except ImportError as caught_exc:  # pragma: NO COVER
            raise ImportError(
                "The pyjwt library is not installed, please install the pyjwt package to use the jwk certs format."
            ) from caught_exc
        jwks_client = jwt_lib.PyJWKClient(certs_url)
        signing_key = jwks_client.get_signing_key_from_jwt(id_token)
        return jwt_lib.decode(
            id_token,
            signing_key.key,
            algorithms=[signing_key.algorithm_name],
            audience=audience,
        )
    else:
        return jwt.decode(
            id_token,
            certs=certs,
            audience=audience,
            clock_skew_in_seconds=clock_skew_in_seconds,
        )


def verify_oauth2_token(id_token, request, audience=None, clock_skew_in_seconds=0):
    """Verifies an ID Token issued by Google's OAuth 2.0 authorization server.

    Args:
        id_token (Union[str, bytes]): The encoded token.
        request (google.auth.transport.Request): The object used to make
            HTTP requests.
        audience (str): The audience that this token is intended for. This is
            typically your application's OAuth 2.0 client ID. If None then the
            audience is not verified.
        clock_skew_in_seconds (int): The clock skew used for `iat` and `exp`
            validation.

    Returns:
        Mapping[str, Any]: The decoded token.

    Raises:
        exceptions.GoogleAuthError: If the issuer is invalid.
        ValueError: If token verification fails
    """
    idinfo = verify_token(
        id_token,
        request,
        audience=audience,
        certs_url=_GOOGLE_OAUTH2_CERTS_URL,
        clock_skew_in_seconds=clock_skew_in_seconds,
    )

    if idinfo["iss"] not in _GOOGLE_ISSUERS:
        raise exceptions.GoogleAuthError(
            "Wrong issuer. 'iss' should be one of the following: {}".format(
                _GOOGLE_ISSUERS
            )
        )

    return idinfo


def verify_firebase_token(id_token, request, audience=None, clock_skew_in_seconds=0):
    """Verifies an ID Token issued by Firebase Authentication.

    Args:
        id_token (Union[str, bytes]): The encoded token.
        request (google.auth.transport.Request): The object used to make
            HTTP requests.
        audience (str): The audience that this token is intended for. This is
            typically your Firebase application ID. If None then the audience
            is not verified.
        clock_skew_in_seconds (int): The clock skew used for `iat` and `exp`
            validation.

    Returns:
        Mapping[str, Any]: The decoded token.
    """
    return verify_token(
        id_token,
        request,
        audience=audience,
        certs_url=_GOOGLE_APIS_CERTS_URL,
        clock_skew_in_seconds=clock_skew_in_seconds,
    )


def fetch_id_token_credentials(audience, request=None):
    """Create the ID Token credentials from the current environment.

    This function acquires ID token from the environment in the following order.
    See https://google.aip.dev/auth/4110.

    1. If the environment variable ``GOOGLE_APPLICATION_CREDENTIALS`` is set
       to the path of a valid service account JSON file, then ID token is
       acquired using this service account credentials.
    2. If the application is running in Compute Engine, App Engine or Cloud Run,
       then the ID token are obtained from the metadata server.
    3. If metadata server doesn't exist and no valid service account credentials
       are found, :class:`~google.auth.exceptions.DefaultCredentialsError` will
       be raised.

    Example::

        import google.oauth2.id_token
        import google.auth.transport.requests

        request = google.auth.transport.requests.Request()
        target_audience = "https://pubsub.googleapis.com"

        # Create ID token credentials.
        credentials = google.oauth2.id_token.fetch_id_token_credentials(target_audience, request=request)

        # Refresh the credential to obtain an ID token.
        credentials.refresh(request)

        id_token = credentials.token
        id_token_expiry = credentials.expiry

    Args:
        audience (str): The audience that this ID token is intended for.
        request (Optional[google.auth.transport.Request]): A callable used to make
            HTTP requests. A request object will be created if not provided.

    Returns:
        google.auth.credentials.Credentials: The ID token credentials.

    Raises:
        ~google.auth.exceptions.DefaultCredentialsError:
            If metadata server doesn't exist and no valid service account
            credentials are found.
    """
    # 1. Try to get credentials from the GOOGLE_APPLICATION_CREDENTIALS environment
    # variable.
    credentials_filename = os.environ.get(environment_vars.CREDENTIALS)
    if credentials_filename:
        if not (
            os.path.exists(credentials_filename)
            and os.path.isfile(credentials_filename)
        ):
            raise exceptions.DefaultCredentialsError(
                "GOOGLE_APPLICATION_CREDENTIALS path is either not found or invalid."
            )

        try:
            with open(credentials_filename, "r") as f:
                from google.oauth2 import service_account

                info = json.load(f)
                if info.get("type") == "service_account":
                    return service_account.IDTokenCredentials.from_service_account_info(
                        info, target_audience=audience
                    )
                elif info.get("type") == "impersonated_service_account":
                    from google.auth import impersonated_credentials

                    target_credentials = impersonated_credentials.Credentials.from_impersonated_service_account_info(
                        info
                    )

                    return impersonated_credentials.IDTokenCredentials(
                        target_credentials=target_credentials,
                        target_audience=audience,
                        include_email=True,
                    )
        except ValueError as caught_exc:
            new_exc = exceptions.DefaultCredentialsError(
                "GOOGLE_APPLICATION_CREDENTIALS is not valid service account credentials.",
                caught_exc,
            )
            raise new_exc from caught_exc

    # 2. Try to fetch ID token from metada server if it exists. The code
    # works for GAE and Cloud Run metadata server as well.
    try:
        from google.auth import compute_engine
        from google.auth.compute_engine import _metadata

        # Create a request object if not provided.
        if not request:
            import google.auth.transport.requests

            request = google.auth.transport.requests.Request()

        if _metadata.ping(request):
            return compute_engine.IDTokenCredentials(
                request, audience, use_metadata_identity_endpoint=True
            )
    except (ImportError, exceptions.TransportError):
        pass

    raise exceptions.DefaultCredentialsError(
        "Neither metadata server or valid service account credentials are found."
    )


def fetch_id_token(request, audience):
    """Fetch the ID Token from the current environment.

    This function acquires ID token from the environment in the following order.
    See https://google.aip.dev/auth/4110.

    1. If the environment variable ``GOOGLE_APPLICATION_CREDENTIALS`` is set
       to the path of a valid service account JSON file, then ID token is
       acquired using this service account credentials.
    2. If the application is running in Compute Engine, App Engine or Cloud Run,
       then the ID token are obtained from the metadata server.
    3. If metadata server doesn't exist and no valid service account credentials
       are found, :class:`~google.auth.exceptions.DefaultCredentialsError` will
       be raised.

    Example::

        import google.oauth2.id_token
        import google.auth.transport.requests

        request = google.auth.transport.requests.Request()
        target_audience = "https://pubsub.googleapis.com"

        id_token = google.oauth2.id_token.fetch_id_token(request, target_audience)

    Args:
        request (google.auth.transport.Request): A callable used to make
            HTTP requests.
        audience (str): The audience that this ID token is intended for.

    Returns:
        str: The ID token.

    Raises:
        ~google.auth.exceptions.DefaultCredentialsError:
            If metadata server doesn't exist and no valid service account
            credentials are found.
    """
    id_token_credentials = fetch_id_token_credentials(audience, request=request)
    id_token_credentials.refresh(request)
    return id_token_credentials.token

# === NexusCore/openenv\Lib\site-packages\google\api_core\operations_v1\abstract_operations_base_client.py ===
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

from collections import OrderedDict
import os
import re
from typing import Dict, Optional, Type, Union

from google.api_core import client_options as client_options_lib  # type: ignore
from google.api_core import gapic_v1  # type: ignore
from google.api_core.operations_v1.transports.base import (
    DEFAULT_CLIENT_INFO,
    OperationsTransport,
)
from google.api_core.operations_v1.transports.rest import OperationsRestTransport

try:
    from google.api_core.operations_v1.transports.rest_asyncio import (
        AsyncOperationsRestTransport,
    )

    HAS_ASYNC_REST_DEPENDENCIES = True
except ImportError as e:
    HAS_ASYNC_REST_DEPENDENCIES = False
    ASYNC_REST_EXCEPTION = e

from google.auth import credentials as ga_credentials  # type: ignore
from google.auth.exceptions import MutualTLSChannelError  # type: ignore
from google.auth.transport import mtls  # type: ignore


class AbstractOperationsBaseClientMeta(type):
    """Metaclass for the Operations Base client.

    This provides base class-level methods for building and retrieving
    support objects (e.g. transport) without polluting the client instance
    objects.
    """

    _transport_registry = OrderedDict()  # type: Dict[str, Type[OperationsTransport]]
    _transport_registry["rest"] = OperationsRestTransport
    if HAS_ASYNC_REST_DEPENDENCIES:
        _transport_registry["rest_asyncio"] = AsyncOperationsRestTransport

    def get_transport_class(
        cls,
        label: Optional[str] = None,
    ) -> Type[OperationsTransport]:
        """Returns an appropriate transport class.

        Args:
            label: The name of the desired transport. If none is
                provided, then the first transport in the registry is used.

        Returns:
            The transport class to use.
        """
        # If a specific transport is requested, return that one.
        if (
            label == "rest_asyncio" and not HAS_ASYNC_REST_DEPENDENCIES
        ):  # pragma: NO COVER
            raise ASYNC_REST_EXCEPTION

        if label:
            return cls._transport_registry[label]

        # No transport is requested; return the default (that is, the first one
        # in the dictionary).
        return next(iter(cls._transport_registry.values()))


class AbstractOperationsBaseClient(metaclass=AbstractOperationsBaseClientMeta):
    """Manages long-running operations with an API service.

    When an API method normally takes long time to complete, it can be
    designed to return [Operation][google.api_core.operations_v1.Operation] to the
    client, and the client can use this interface to receive the real
    response asynchronously by polling the operation resource, or pass
    the operation resource to another API (such as Google Cloud Pub/Sub
    API) to receive the response. Any API service that returns
    long-running operations should implement the ``Operations``
    interface so developers can have a consistent client experience.
    """

    @staticmethod
    def _get_default_mtls_endpoint(api_endpoint):
        """Converts api endpoint to mTLS endpoint.

        Convert "*.sandbox.googleapis.com" and "*.googleapis.com" to
        "*.mtls.sandbox.googleapis.com" and "*.mtls.googleapis.com" respectively.
        Args:
            api_endpoint (Optional[str]): the api endpoint to convert.
        Returns:
            str: converted mTLS api endpoint.
        """
        if not api_endpoint:
            return api_endpoint

        mtls_endpoint_re = re.compile(
            r"(?P<name>[^.]+)(?P<mtls>\.mtls)?(?P<sandbox>\.sandbox)?(?P<googledomain>\.googleapis\.com)?"
        )

        m = mtls_endpoint_re.match(api_endpoint)
        name, mtls, sandbox, googledomain = m.groups()
        if mtls or not googledomain:
            return api_endpoint

        if sandbox:
            return api_endpoint.replace(
                "sandbox.googleapis.com", "mtls.sandbox.googleapis.com"
            )

        return api_endpoint.replace(".googleapis.com", ".mtls.googleapis.com")

    DEFAULT_ENDPOINT = "longrunning.googleapis.com"
    DEFAULT_MTLS_ENDPOINT = _get_default_mtls_endpoint.__func__(  # type: ignore
        DEFAULT_ENDPOINT
    )

    @classmethod
    def from_service_account_info(cls, info: dict, *args, **kwargs):
        """
        This class method should be overridden by the subclasses.

        Args:
            info (dict): The service account private key info.
            args: Additional arguments to pass to the constructor.
            kwargs: Additional arguments to pass to the constructor.

        Raises:
            NotImplementedError: If the method is called on the base class.
        """
        raise NotImplementedError("`from_service_account_info` is not implemented.")

    @classmethod
    def from_service_account_file(cls, filename: str, *args, **kwargs):
        """
        This class method should be overridden by the subclasses.

        Args:
            filename (str): The path to the service account private key json
                file.
            args: Additional arguments to pass to the constructor.
            kwargs: Additional arguments to pass to the constructor.

        Raises:
            NotImplementedError: If the method is called on the base class.
        """
        raise NotImplementedError("`from_service_account_file` is not implemented.")

    from_service_account_json = from_service_account_file

    @property
    def transport(self) -> OperationsTransport:
        """Returns the transport used by the client instance.

        Returns:
            OperationsTransport: The transport used by the client
                instance.
        """
        return self._transport

    @staticmethod
    def common_billing_account_path(
        billing_account: str,
    ) -> str:
        """Returns a fully-qualified billing_account string."""
        return "billingAccounts/{billing_account}".format(
            billing_account=billing_account,
        )

    @staticmethod
    def parse_common_billing_account_path(path: str) -> Dict[str, str]:
        """Parse a billing_account path into its component segments."""
        m = re.match(r"^billingAccounts/(?P<billing_account>.+?)$", path)
        return m.groupdict() if m else {}

    @staticmethod
    def common_folder_path(
        folder: str,
    ) -> str:
        """Returns a fully-qualified folder string."""
        return "folders/{folder}".format(
            folder=folder,
        )

    @staticmethod
    def parse_common_folder_path(path: str) -> Dict[str, str]:
        """Parse a folder path into its component segments."""
        m = re.match(r"^folders/(?P<folder>.+?)$", path)
        return m.groupdict() if m else {}

    @staticmethod
    def common_organization_path(
        organization: str,
    ) -> str:
        """Returns a fully-qualified organization string."""
        return "organizations/{organization}".format(
            organization=organization,
        )

    @staticmethod
    def parse_common_organization_path(path: str) -> Dict[str, str]:
        """Parse a organization path into its component segments."""
        m = re.match(r"^organizations/(?P<organization>.+?)$", path)
        return m.groupdict() if m else {}

    @staticmethod
    def common_project_path(
        project: str,
    ) -> str:
        """Returns a fully-qualified project string."""
        return "projects/{project}".format(
            project=project,
        )

    @staticmethod
    def parse_common_project_path(path: str) -> Dict[str, str]:
        """Parse a project path into its component segments."""
        m = re.match(r"^projects/(?P<project>.+?)$", path)
        return m.groupdict() if m else {}

    @staticmethod
    def common_location_path(
        project: str,
        location: str,
    ) -> str:
        """Returns a fully-qualified location string."""
        return "projects/{project}/locations/{location}".format(
            project=project,
            location=location,
        )

    @staticmethod
    def parse_common_location_path(path: str) -> Dict[str, str]:
        """Parse a location path into its component segments."""
        m = re.match(r"^projects/(?P<project>.+?)/locations/(?P<location>.+?)$", path)
        return m.groupdict() if m else {}

    def __init__(
        self,
        *,
        credentials: Optional[ga_credentials.Credentials] = None,
        transport: Union[str, OperationsTransport, None] = None,
        client_options: Optional[client_options_lib.ClientOptions] = None,
        client_info: gapic_v1.client_info.ClientInfo = DEFAULT_CLIENT_INFO,
    ) -> None:
        """Instantiates the operations client.

        Args:
            credentials (Optional[google.auth.credentials.Credentials]): The
                authorization credentials to attach to requests. These
                credentials identify the application to the service; if none
                are specified, the client will attempt to ascertain the
                credentials from the environment.
            transport (Union[str, OperationsTransport]): The
                transport to use. If set to None, a transport is chosen
                automatically.
            client_options (google.api_core.client_options.ClientOptions): Custom options for the
                client. It won't take effect if a ``transport`` instance is provided.
                (1) The ``api_endpoint`` property can be used to override the
                default endpoint provided by the client. GOOGLE_API_USE_MTLS_ENDPOINT
                environment variable can also be used to override the endpoint:
                "always" (always use the default mTLS endpoint), "never" (always
                use the default regular endpoint) and "auto" (auto switch to the
                default mTLS endpoint if client certificate is present, this is
                the default value). However, the ``api_endpoint`` property takes
                precedence if provided.
                (2) If GOOGLE_API_USE_CLIENT_CERTIFICATE environment variable
                is "true", then the ``client_cert_source`` property can be used
                to provide client certificate for mutual TLS transport. If
                not provided, the default SSL client certificate will be used if
                present. If GOOGLE_API_USE_CLIENT_CERTIFICATE is "false" or not
                set, no client certificate will be used.
            client_info (google.api_core.gapic_v1.client_info.ClientInfo):
                The client info used to send a user-agent string along with
                API requests. If ``None``, then default info will be used.
                Generally, you only need to set this if you're developing
                your own client library.

        Raises:
            google.auth.exceptions.MutualTLSChannelError: If mutual TLS transport
                creation failed for any reason.
        """
        if isinstance(client_options, dict):
            client_options = client_options_lib.from_dict(client_options)
        if client_options is None:
            client_options = client_options_lib.ClientOptions()

        # Create SSL credentials for mutual TLS if needed.
        use_client_cert = os.getenv(
            "GOOGLE_API_USE_CLIENT_CERTIFICATE", "false"
        ).lower()
        if use_client_cert not in ("true", "false"):
            raise ValueError(
                "Environment variable `GOOGLE_API_USE_CLIENT_CERTIFICATE` must be either `true` or `false`"
            )
        client_cert_source_func = None
        is_mtls = False
        if use_client_cert == "true":
            if client_options.client_cert_source:
                is_mtls = True
                client_cert_source_func = client_options.client_cert_source
            else:
                is_mtls = mtls.has_default_client_cert_source()
                if is_mtls:
                    client_cert_source_func = mtls.default_client_cert_source()
                else:
                    client_cert_source_func = None

        # Figure out which api endpoint to use.
        if client_options.api_endpoint is not None:
            api_endpoint = client_options.api_endpoint
        else:
            use_mtls_env = os.getenv("GOOGLE_API_USE_MTLS_ENDPOINT", "auto")
            if use_mtls_env == "never":
                api_endpoint = self.DEFAULT_ENDPOINT
            elif use_mtls_env == "always":
                api_endpoint = self.DEFAULT_MTLS_ENDPOINT
            elif use_mtls_env == "auto":
                if is_mtls:
                    api_endpoint = self.DEFAULT_MTLS_ENDPOINT
                else:
                    api_endpoint = self.DEFAULT_ENDPOINT
            else:
                raise MutualTLSChannelError(
                    "Unsupported GOOGLE_API_USE_MTLS_ENDPOINT value. Accepted "
                    "values: never, auto, always"
                )

        # Save or instantiate the transport.
        # Ordinarily, we provide the transport, but allowing a custom transport
        # instance provides an extensibility point for unusual situations.
        if isinstance(transport, OperationsTransport):
            # transport is a OperationsTransport instance.
            if credentials or client_options.credentials_file:
                raise ValueError(
                    "When providing a transport instance, "
                    "provide its credentials directly."
                )
            if client_options.scopes:
                raise ValueError(
                    "When providing a transport instance, provide its scopes "
                    "directly."
                )
            self._transport = transport
        else:
            Transport = type(self).get_transport_class(transport)
            self._transport = Transport(
                credentials=credentials,
                credentials_file=client_options.credentials_file,
                host=api_endpoint,
                scopes=client_options.scopes,
                client_cert_source_for_mtls=client_cert_source_func,
                quota_project_id=client_options.quota_project_id,
                client_info=client_info,
                always_use_jwt_access=True,
            )

# === NexusCore/openenv\Lib\site-packages\google\api_core\retry\retry_base.py ===
# Copyright 2017 Google LLC
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

"""Shared classes and functions for retrying requests.

:class:`_BaseRetry` is the base class for :class:`Retry`,
:class:`AsyncRetry`, :class:`StreamingRetry`, and :class:`AsyncStreamingRetry`.
"""

from __future__ import annotations

import logging
import random
import time

from enum import Enum
from typing import Any, Callable, Optional, Iterator, TYPE_CHECKING

import requests.exceptions

from google.api_core import exceptions
from google.auth import exceptions as auth_exceptions

if TYPE_CHECKING:
    import sys

    if sys.version_info >= (3, 11):
        from typing import Self
    else:
        from typing_extensions import Self

_DEFAULT_INITIAL_DELAY = 1.0  # seconds
_DEFAULT_MAXIMUM_DELAY = 60.0  # seconds
_DEFAULT_DELAY_MULTIPLIER = 2.0
_DEFAULT_DEADLINE = 60.0 * 2.0  # seconds

_LOGGER = logging.getLogger("google.api_core.retry")


def if_exception_type(
    *exception_types: type[Exception],
) -> Callable[[Exception], bool]:
    """Creates a predicate to check if the exception is of a given type.

    Args:
        exception_types (Sequence[:func:`type`]): The exception types to check
            for.

    Returns:
        Callable[Exception]: A predicate that returns True if the provided
            exception is of the given type(s).
    """

    def if_exception_type_predicate(exception: Exception) -> bool:
        """Bound predicate for checking an exception type."""
        return isinstance(exception, exception_types)

    return if_exception_type_predicate


# pylint: disable=invalid-name
# Pylint sees this as a constant, but it is also an alias that should be
# considered a function.
if_transient_error = if_exception_type(
    exceptions.InternalServerError,
    exceptions.TooManyRequests,
    exceptions.ServiceUnavailable,
    requests.exceptions.ConnectionError,
    requests.exceptions.ChunkedEncodingError,
    auth_exceptions.TransportError,
)
"""A predicate that checks if an exception is a transient API error.

The following server errors are considered transient:

- :class:`google.api_core.exceptions.InternalServerError` - HTTP 500, gRPC
    ``INTERNAL(13)`` and its subclasses.
- :class:`google.api_core.exceptions.TooManyRequests` - HTTP 429
- :class:`google.api_core.exceptions.ServiceUnavailable` - HTTP 503
- :class:`requests.exceptions.ConnectionError`
- :class:`requests.exceptions.ChunkedEncodingError` - The server declared
    chunked encoding but sent an invalid chunk.
- :class:`google.auth.exceptions.TransportError` - Used to indicate an
    error occurred during an HTTP request.
"""
# pylint: enable=invalid-name


def exponential_sleep_generator(
    initial: float, maximum: float, multiplier: float = _DEFAULT_DELAY_MULTIPLIER
):
    """Generates sleep intervals based on the exponential back-off algorithm.

    This implements the `Truncated Exponential Back-off`_ algorithm.

    .. _Truncated Exponential Back-off:
        https://cloud.google.com/storage/docs/exponential-backoff

    Args:
        initial (float): The minimum amount of time to delay. This must
            be greater than 0.
        maximum (float): The maximum amount of time to delay.
        multiplier (float): The multiplier applied to the delay.

    Yields:
        float: successive sleep intervals.
    """
    max_delay = min(initial, maximum)
    while True:
        yield random.uniform(0.0, max_delay)
        max_delay = min(max_delay * multiplier, maximum)


class RetryFailureReason(Enum):
    """
    The cause of a failed retry, used when building exceptions
    """

    TIMEOUT = 0
    NON_RETRYABLE_ERROR = 1


def build_retry_error(
    exc_list: list[Exception],
    reason: RetryFailureReason,
    timeout_val: float | None,
    **kwargs: Any,
) -> tuple[Exception, Exception | None]:
    """
    Default exception_factory implementation.

    Returns a RetryError if the failure is due to a timeout, otherwise
    returns the last exception encountered.

    Args:
      - exc_list: list of exceptions that occurred during the retry
      - reason: reason for the retry failure.
            Can be TIMEOUT or NON_RETRYABLE_ERROR
      - timeout_val: the original timeout value for the retry (in seconds), for use in the exception message

    Returns:
      - tuple: a tuple of the exception to be raised, and the cause exception if any
    """
    if reason == RetryFailureReason.TIMEOUT:
        # return RetryError with the most recent exception as the cause
        src_exc = exc_list[-1] if exc_list else None
        timeout_val_str = f"of {timeout_val:0.1f}s " if timeout_val is not None else ""
        return (
            exceptions.RetryError(
                f"Timeout {timeout_val_str}exceeded",
                src_exc,
            ),
            src_exc,
        )
    elif exc_list:
        # return most recent exception encountered
        return exc_list[-1], None
    else:
        # no exceptions were given in exc_list. Raise generic RetryError
        return exceptions.RetryError("Unknown error", None), None


def _retry_error_helper(
    exc: Exception,
    deadline: float | None,
    sleep_iterator: Iterator[float],
    error_list: list[Exception],
    predicate_fn: Callable[[Exception], bool],
    on_error_fn: Callable[[Exception], None] | None,
    exc_factory_fn: Callable[
        [list[Exception], RetryFailureReason, float | None],
        tuple[Exception, Exception | None],
    ],
    original_timeout: float | None,
) -> float:
    """
    Shared logic for handling an error for all retry implementations

    - Raises an error on timeout or non-retryable error
    - Calls on_error_fn if provided
    - Logs the error

    Args:
       - exc: the exception that was raised
       - deadline: the deadline for the retry, calculated as a diff from time.monotonic()
       - sleep_iterator: iterator to draw the next backoff value from
       - error_list: the list of exceptions that have been raised so far
       - predicate_fn: takes `exc` and returns true if the operation should be retried
       - on_error_fn: callback to execute when a retryable error occurs
       - exc_factory_fn: callback used to build the exception to be raised on terminal failure
       - original_timeout_val: the original timeout value for the retry (in seconds),
           to be passed to the exception factory for building an error message
    Returns:
        - the sleep value chosen before the next attempt
    """
    error_list.append(exc)
    if not predicate_fn(exc):
        final_exc, source_exc = exc_factory_fn(
            error_list,
            RetryFailureReason.NON_RETRYABLE_ERROR,
            original_timeout,
        )
        raise final_exc from source_exc
    if on_error_fn is not None:
        on_error_fn(exc)
    # next_sleep is fetched after the on_error callback, to allow clients
    # to update sleep_iterator values dynamically in response to errors
    try:
        next_sleep = next(sleep_iterator)
    except StopIteration:
        raise ValueError("Sleep generator stopped yielding sleep values.") from exc
    if deadline is not None and time.monotonic() + next_sleep > deadline:
        final_exc, source_exc = exc_factory_fn(
            error_list,
            RetryFailureReason.TIMEOUT,
            original_timeout,
        )
        raise final_exc from source_exc
    _LOGGER.debug(
        "Retrying due to {}, sleeping {:.1f}s ...".format(error_list[-1], next_sleep)
    )
    return next_sleep


class _BaseRetry(object):
    """
    Base class for retry configuration objects. This class is intended to capture retry
    and backoff configuration that is common to both synchronous and asynchronous retries,
    for both unary and streaming RPCs. It is not intended to be instantiated directly,
    but rather to be subclassed by the various retry configuration classes.
    """

    def __init__(
        self,
        predicate: Callable[[Exception], bool] = if_transient_error,
        initial: float = _DEFAULT_INITIAL_DELAY,
        maximum: float = _DEFAULT_MAXIMUM_DELAY,
        multiplier: float = _DEFAULT_DELAY_MULTIPLIER,
        timeout: Optional[float] = _DEFAULT_DEADLINE,
        on_error: Optional[Callable[[Exception], Any]] = None,
        **kwargs: Any,
    ) -> None:
        self._predicate = predicate
        self._initial = initial
        self._multiplier = multiplier
        self._maximum = maximum
        self._timeout = kwargs.get("deadline", timeout)
        self._deadline = self._timeout
        self._on_error = on_error

    def __call__(self, *args, **kwargs) -> Any:
        raise NotImplementedError("Not implemented in base class")

    @property
    def deadline(self) -> float | None:
        """
        DEPRECATED: use ``timeout`` instead.  Refer to the ``Retry`` class
        documentation for details.
        """
        return self._timeout

    @property
    def timeout(self) -> float | None:
        return self._timeout

    def with_deadline(self, deadline: float | None) -> Self:
        """Return a copy of this retry with the given timeout.

        DEPRECATED: use :meth:`with_timeout` instead. Refer to the ``Retry`` class
        documentation for details.

        Args:
            deadline (float|None): How long to keep retrying, in seconds. If None,
                no timeout is enforced.

        Returns:
            Retry: A new retry instance with the given timeout.
        """
        return self.with_timeout(deadline)

    def with_timeout(self, timeout: float | None) -> Self:
        """Return a copy of this retry with the given timeout.

        Args:
            timeout (float): How long to keep retrying, in seconds. If None,
                no timeout will be enforced.

        Returns:
            Retry: A new retry instance with the given timeout.
        """
        return type(self)(
            predicate=self._predicate,
            initial=self._initial,
            maximum=self._maximum,
            multiplier=self._multiplier,
            timeout=timeout,
            on_error=self._on_error,
        )

    def with_predicate(self, predicate: Callable[[Exception], bool]) -> Self:
        """Return a copy of this retry with the given predicate.

        Args:
            predicate (Callable[Exception]): A callable that should return
                ``True`` if the given exception is retryable.

        Returns:
            Retry: A new retry instance with the given predicate.
        """
        return type(self)(
            predicate=predicate,
            initial=self._initial,
            maximum=self._maximum,
            multiplier=self._multiplier,
            timeout=self._timeout,
            on_error=self._on_error,
        )

    def with_delay(
        self,
        initial: Optional[float] = None,
        maximum: Optional[float] = None,
        multiplier: Optional[float] = None,
    ) -> Self:
        """Return a copy of this retry with the given delay options.

        Args:
            initial (float): The minimum amount of time to delay (in seconds). This must
                be greater than 0. If None, the current value is used.
            maximum (float): The maximum amount of time to delay (in seconds). If None, the
                current value is used.
            multiplier (float): The multiplier applied to the delay. If None, the current
                value is used.

        Returns:
            Retry: A new retry instance with the given delay options.
        """
        return type(self)(
            predicate=self._predicate,
            initial=initial if initial is not None else self._initial,
            maximum=maximum if maximum is not None else self._maximum,
            multiplier=multiplier if multiplier is not None else self._multiplier,
            timeout=self._timeout,
            on_error=self._on_error,
        )

    def __str__(self) -> str:
        return (
            "<{} predicate={}, initial={:.1f}, maximum={:.1f}, "
            "multiplier={:.1f}, timeout={}, on_error={}>".format(
                type(self).__name__,
                self._predicate,
                self._initial,
                self._maximum,
                self._multiplier,
                self._timeout,  # timeout can be None, thus no {:.1f}
                self._on_error,
            )
        )

# === NexusCore/openenv\Lib\site-packages\litellm\litellm_core_utils\llm_cost_calc\utils.py ===
# What is this?
## Helper utilities for cost_per_token()

from typing import Literal, Optional, Tuple, cast

import litellm
from litellm._logging import verbose_logger
from litellm.types.utils import CallTypes, ModelInfo, PassthroughCallTypes, Usage
from litellm.utils import get_model_info


def _is_above_128k(tokens: float) -> bool:
    if tokens > 128000:
        return True
    return False


def select_cost_metric_for_model(
    model_info: ModelInfo,
) -> Literal["cost_per_character", "cost_per_token"]:
    """
    Select 'cost_per_character' if model_info has 'input_cost_per_character'
    Select 'cost_per_token' if model_info has 'input_cost_per_token'
    """
    if model_info.get("input_cost_per_character"):
        return "cost_per_character"
    elif model_info.get("input_cost_per_token"):
        return "cost_per_token"
    else:
        raise ValueError(
            f"Model {model_info['key']} does not have 'input_cost_per_character' or 'input_cost_per_token'"
        )


def _generic_cost_per_character(
    model: str,
    custom_llm_provider: str,
    prompt_characters: float,
    completion_characters: float,
    custom_prompt_cost: Optional[float],
    custom_completion_cost: Optional[float],
) -> Tuple[Optional[float], Optional[float]]:
    """
    Calculates cost per character for aspeech/speech calls.

    Calculates the cost per character for a given model, input messages, and response object.

    Input:
        - model: str, the model name without provider prefix
        - custom_llm_provider: str, "vertex_ai-*"
        - prompt_characters: float, the number of input characters
        - completion_characters: float, the number of output characters

    Returns:
        Tuple[Optional[float], Optional[float]] - prompt_cost_in_usd, completion_cost_in_usd.
        - returns None if not able to calculate cost.

    Raises:
        Exception if 'input_cost_per_character' or 'output_cost_per_character' is missing from model_info
    """
    ## GET MODEL INFO
    model_info = litellm.get_model_info(
        model=model, custom_llm_provider=custom_llm_provider
    )

    ## CALCULATE INPUT COST
    try:
        if custom_prompt_cost is None:
            assert (
                "input_cost_per_character" in model_info
                and model_info["input_cost_per_character"] is not None
            ), "model info for model={} does not have 'input_cost_per_character'-pricing\nmodel_info={}".format(
                model, model_info
            )
            custom_prompt_cost = model_info["input_cost_per_character"]

        prompt_cost = prompt_characters * custom_prompt_cost
    except Exception as e:
        verbose_logger.exception(
            "litellm.litellm_core_utils.llm_cost_calc.utils.py::cost_per_character(): Exception occured - {}\nDefaulting to None".format(
                str(e)
            )
        )

        prompt_cost = None

    ## CALCULATE OUTPUT COST
    try:
        if custom_completion_cost is None:
            assert (
                "output_cost_per_character" in model_info
                and model_info["output_cost_per_character"] is not None
            ), "model info for model={} does not have 'output_cost_per_character'-pricing\nmodel_info={}".format(
                model, model_info
            )
            custom_completion_cost = model_info["output_cost_per_character"]
        completion_cost = completion_characters * custom_completion_cost
    except Exception as e:
        verbose_logger.exception(
            "litellm.litellm_core_utils.llm_cost_calc.utils.py::cost_per_character(): Exception occured - {}\nDefaulting to None".format(
                str(e)
            )
        )

        completion_cost = None

    return prompt_cost, completion_cost


def _get_token_base_cost(model_info: ModelInfo, usage: Usage) -> Tuple[float, float]:
    """
    Return prompt cost for a given model and usage.

    If input_tokens > threshold and `input_cost_per_token_above_[x]k_tokens` or `input_cost_per_token_above_[x]_tokens` is set,
    then we use the corresponding threshold cost.
    """
    prompt_base_cost = model_info["input_cost_per_token"]
    completion_base_cost = model_info["output_cost_per_token"]

    ## CHECK IF ABOVE THRESHOLD
    threshold: Optional[float] = None
    for key, value in sorted(model_info.items(), reverse=True):
        if key.startswith("input_cost_per_token_above_") and value is not None:
            try:
                # Handle both formats: _above_128k_tokens and _above_128_tokens
                threshold_str = key.split("_above_")[1].split("_tokens")[0]
                threshold = float(threshold_str.replace("k", "")) * (
                    1000 if "k" in threshold_str else 1
                )
                if usage.prompt_tokens > threshold:
                    prompt_base_cost = cast(
                        float,
                        model_info.get(key, prompt_base_cost),
                    )
                    completion_base_cost = cast(
                        float,
                        model_info.get(
                            f"output_cost_per_token_above_{threshold_str}_tokens",
                            completion_base_cost,
                        ),
                    )
                    break
            except (IndexError, ValueError):
                continue
            except Exception:
                continue

    return prompt_base_cost, completion_base_cost


def calculate_cost_component(
    model_info: ModelInfo, cost_key: str, usage_value: Optional[float]
) -> float:
    """
    Generic cost calculator for any usage component

    Args:
        model_info: Dictionary containing cost information
        cost_key: The key for the cost multiplier in model_info (e.g., 'input_cost_per_audio_token')
        usage_value: The actual usage value (e.g., number of tokens, characters, seconds)

    Returns:
        float: The calculated cost
    """
    cost_per_unit = model_info.get(cost_key)
    if (
        cost_per_unit is not None
        and isinstance(cost_per_unit, float)
        and usage_value is not None
        and usage_value > 0
    ):
        return float(usage_value) * cost_per_unit
    return 0.0


def generic_cost_per_token(
    model: str, usage: Usage, custom_llm_provider: str
) -> Tuple[float, float]:
    """
    Calculates the cost per token for a given model, prompt tokens, and completion tokens.

    Handles context caching as well.

    Input:
        - model: str, the model name without provider prefix
        - usage: LiteLLM Usage block, containing anthropic caching information

    Returns:
        Tuple[float, float] - prompt_cost_in_usd, completion_cost_in_usd
    """

    ## GET MODEL INFO
    model_info = get_model_info(model=model, custom_llm_provider=custom_llm_provider)

    ## CALCULATE INPUT COST
    ### Cost of processing (non-cache hit + cache hit) + Cost of cache-writing (cache writing)
    prompt_cost = 0.0
    ### PROCESSING COST
    text_tokens = usage.prompt_tokens
    cache_hit_tokens = 0
    audio_tokens = 0
    character_count = 0
    image_count = 0
    video_length_seconds = 0
    if usage.prompt_tokens_details:
        cache_hit_tokens = (
            cast(
                Optional[int], getattr(usage.prompt_tokens_details, "cached_tokens", 0)
            )
            or 0
        )
        text_tokens = (
            cast(
                Optional[int], getattr(usage.prompt_tokens_details, "text_tokens", None)
            )
            or 0  # default to prompt tokens, if this field is not set
        )
        audio_tokens = (
            cast(Optional[int], getattr(usage.prompt_tokens_details, "audio_tokens", 0))
            or 0
        )
        character_count = (
            cast(
                Optional[int],
                getattr(usage.prompt_tokens_details, "character_count", 0),
            )
            or 0
        )
        image_count = (
            cast(Optional[int], getattr(usage.prompt_tokens_details, "image_count", 0))
            or 0
        )
        video_length_seconds = (
            cast(
                Optional[int],
                getattr(usage.prompt_tokens_details, "video_length_seconds", 0),
            )
            or 0
        )

    ## EDGE CASE - text tokens not set inside PromptTokensDetails
    if text_tokens == 0:
        text_tokens = usage.prompt_tokens - cache_hit_tokens - audio_tokens

    prompt_base_cost, completion_base_cost = _get_token_base_cost(
        model_info=model_info, usage=usage
    )

    prompt_cost = float(text_tokens) * prompt_base_cost

    ### CACHE READ COST
    prompt_cost += calculate_cost_component(
        model_info, "cache_read_input_token_cost", cache_hit_tokens
    )

    ### AUDIO COST
    prompt_cost += calculate_cost_component(
        model_info, "input_cost_per_audio_token", audio_tokens
    )

    ### CACHE WRITING COST
    prompt_cost += calculate_cost_component(
        model_info,
        "cache_creation_input_token_cost",
        usage._cache_creation_input_tokens,
    )

    ### CHARACTER COST

    prompt_cost += calculate_cost_component(
        model_info, "input_cost_per_character", character_count
    )

    ### IMAGE COUNT COST
    prompt_cost += calculate_cost_component(
        model_info, "input_cost_per_image", image_count
    )

    ### VIDEO LENGTH COST
    prompt_cost += calculate_cost_component(
        model_info, "input_cost_per_video_per_second", video_length_seconds
    )

    ## CALCULATE OUTPUT COST
    text_tokens = 0
    audio_tokens = 0
    reasoning_tokens = 0
    is_text_tokens_total = False
    if usage.completion_tokens_details is not None:
        audio_tokens = (
            cast(
                Optional[int],
                getattr(usage.completion_tokens_details, "audio_tokens", 0),
            )
            or 0
        )
        text_tokens = (
            cast(
                Optional[int],
                getattr(usage.completion_tokens_details, "text_tokens", None),
            )
            or 0  # default to completion tokens, if this field is not set
        )
        reasoning_tokens = (
            cast(
                Optional[int],
                getattr(usage.completion_tokens_details, "reasoning_tokens", 0),
            )
            or 0
        )

    if text_tokens == 0:
        text_tokens = usage.completion_tokens
    if text_tokens == usage.completion_tokens:
        is_text_tokens_total = True
    ## TEXT COST
    completion_cost = float(text_tokens) * completion_base_cost

    _output_cost_per_audio_token: Optional[float] = model_info.get(
        "output_cost_per_audio_token"
    )

    _output_cost_per_reasoning_token: Optional[float] = model_info.get(
        "output_cost_per_reasoning_token"
    )

    ## AUDIO COST
    if not is_text_tokens_total and audio_tokens is not None and audio_tokens > 0:
        _output_cost_per_audio_token = (
            _output_cost_per_audio_token
            if _output_cost_per_audio_token is not None
            else completion_base_cost
        )
        completion_cost += float(audio_tokens) * _output_cost_per_audio_token

    ## REASONING COST
    if not is_text_tokens_total and reasoning_tokens and reasoning_tokens > 0:
        _output_cost_per_reasoning_token = (
            _output_cost_per_reasoning_token
            if _output_cost_per_reasoning_token is not None
            else completion_base_cost
        )
        completion_cost += float(reasoning_tokens) * _output_cost_per_reasoning_token

    return prompt_cost, completion_cost


class CostCalculatorUtils:
    @staticmethod
    def _call_type_has_image_response(call_type: str) -> bool:
        """
        Returns True if the call type has an image response

        eg calls that have image response:
        - Image Generation
        - Image Edit
        - Passthrough Image Generation
        """
        if call_type in [
            # image generation
            CallTypes.image_generation.value,
            CallTypes.aimage_generation.value,
            # passthrough image generation
            PassthroughCallTypes.passthrough_image_generation.value,
            # image edit
            CallTypes.image_edit.value,
            CallTypes.aimage_edit.value,
        ]:
            return True
        return False