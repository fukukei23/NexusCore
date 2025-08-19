
# === NexusCore/openenv\Lib\site-packages\huggingface_hub\inference\_mcp\cli.py ===
import asyncio
import os
import signal
import traceback
from typing import Optional

import typer
from rich import print

from ._cli_hacks import _async_prompt, _patch_anyio_open_process
from .agent import Agent
from .utils import _load_agent_config


app = typer.Typer(
    rich_markup_mode="rich",
    help="A squad of lightweight composable AI applications built on Hugging Face's Inference Client and MCP stack.",
)

run_cli = typer.Typer(
    name="run",
    help="Run the Agent in the CLI",
    invoke_without_command=True,
)
app.add_typer(run_cli, name="run")


async def run_agent(
    agent_path: Optional[str],
) -> None:
    """
    Tiny Agent loop.

    Args:
        agent_path (`str`, *optional*):
            Path to a local folder containing an `agent.json` and optionally a custom `PROMPT.md` file or a built-in agent stored in a Hugging Face dataset.

    """
    _patch_anyio_open_process()  # Hacky way to prevent stdio connections to be stopped by Ctrl+C

    config, prompt = _load_agent_config(agent_path)

    inputs = config.get("inputs", [])
    servers = config.get("servers", [])

    abort_event = asyncio.Event()
    exit_event = asyncio.Event()
    first_sigint = True

    loop = asyncio.get_running_loop()
    original_sigint_handler = signal.getsignal(signal.SIGINT)

    def _sigint_handler() -> None:
        nonlocal first_sigint
        if first_sigint:
            first_sigint = False
            abort_event.set()
            print("\n[red]Interrupted. Press Ctrl+C again to quit.[/red]", flush=True)
            return

        print("\n[red]Exiting...[/red]", flush=True)
        exit_event.set()

    try:
        sigint_registered_in_loop = False
        try:
            loop.add_signal_handler(signal.SIGINT, _sigint_handler)
            sigint_registered_in_loop = True
        except (AttributeError, NotImplementedError):
            # Windows (or any loop that doesn't support it) : fall back to sync
            signal.signal(signal.SIGINT, lambda *_: _sigint_handler())

        # Handle inputs (i.e. env variables injection)
        if len(inputs) > 0:
            print(
                "[bold blue]Some initial inputs are required by the agent. "
                "Please provide a value or leave empty to load from env.[/bold blue]"
            )
            for input_item in inputs:
                input_id = input_item["id"]
                description = input_item["description"]
                env_special_value = "${input:" + input_id + "}"  # Special value to indicate env variable injection

                # Check env variables that will use this input
                input_vars = set()
                for server in servers:
                    # Check stdio's "env" and http/sse's "headers" mappings
                    env_or_headers = (
                        server["config"].get("env", {})
                        if server["type"] == "stdio"
                        else server["config"].get("options", {}).get("requestInit", {}).get("headers", {})
                    )
                    for key, value in env_or_headers.items():
                        if env_special_value in value:
                            input_vars.add(key)

                if not input_vars:
                    print(f"[yellow]Input {input_id} defined in config but not used by any server.[/yellow]")
                    continue

                # Prompt user for input
                print(
                    f"[blue] • {input_id}[/blue]: {description}. (default: load from {', '.join(sorted(input_vars))}).",
                    end=" ",
                )
                user_input = (await _async_prompt(exit_event=exit_event)).strip()
                if exit_event.is_set():
                    return

                # Inject user input (or env variable) into stdio's env or http/sse's headers
                for server in servers:
                    env_or_headers = (
                        server["config"].get("env", {})
                        if server["type"] == "stdio"
                        else server["config"].get("options", {}).get("requestInit", {}).get("headers", {})
                    )
                    for key, value in env_or_headers.items():
                        if env_special_value in value:
                            if user_input:
                                env_or_headers[key] = env_or_headers[key].replace(env_special_value, user_input)
                            else:
                                value_from_env = os.getenv(key, "")
                                env_or_headers[key] = env_or_headers[key].replace(env_special_value, value_from_env)
                                if value_from_env:
                                    print(f"[green]Value successfully loaded from '{key}'[/green]")
                                else:
                                    print(
                                        f"[yellow]No value found for '{key}' in environment variables. Continuing.[/yellow]"
                                    )

            print()

        # Main agent loop
        async with Agent(
            provider=config.get("provider"),  # type: ignore[arg-type]
            model=config.get("model"),
            base_url=config.get("endpointUrl"),  # type: ignore[arg-type]
            servers=servers,  # type: ignore[arg-type]
            prompt=prompt,
        ) as agent:
            await agent.load_tools()
            print(f"[bold blue]Agent loaded with {len(agent.available_tools)} tools:[/bold blue]")
            for t in agent.available_tools:
                print(f"[blue] • {t.function.name}[/blue]")

            while True:
                abort_event.clear()

                # Check if we should exit
                if exit_event.is_set():
                    return

                try:
                    user_input = await _async_prompt(exit_event=exit_event)
                    first_sigint = True
                except EOFError:
                    print("\n[red]EOF received, exiting.[/red]", flush=True)
                    break
                except KeyboardInterrupt:
                    if not first_sigint and abort_event.is_set():
                        continue
                    else:
                        print("\n[red]Keyboard interrupt during input processing.[/red]", flush=True)
                        break

                try:
                    async for chunk in agent.run(user_input, abort_event=abort_event):
                        if abort_event.is_set() and not first_sigint:
                            break
                        if exit_event.is_set():
                            return

                        if hasattr(chunk, "choices"):
                            delta = chunk.choices[0].delta
                            if delta.content:
                                print(delta.content, end="", flush=True)
                            if delta.tool_calls:
                                for call in delta.tool_calls:
                                    if call.id:
                                        print(f"<Tool {call.id}>", end="")
                                    if call.function.name:
                                        print(f"{call.function.name}", end=" ")
                                    if call.function.arguments:
                                        print(f"{call.function.arguments}", end="")
                        else:
                            print(
                                f"\n\n[green]Tool[{chunk.name}] {chunk.tool_call_id}\n{chunk.content}[/green]\n",
                                flush=True,
                            )

                    print()

                except Exception as e:
                    tb_str = traceback.format_exc()
                    print(f"\n[bold red]Error during agent run: {e}\n{tb_str}[/bold red]", flush=True)
                    first_sigint = True  # Allow graceful interrupt for the next command

    except Exception as e:
        tb_str = traceback.format_exc()
        print(f"\n[bold red]An unexpected error occurred: {e}\n{tb_str}[/bold red]", flush=True)
        raise e

    finally:
        if sigint_registered_in_loop:
            try:
                loop.remove_signal_handler(signal.SIGINT)
            except (AttributeError, NotImplementedError):
                pass
        else:
            signal.signal(signal.SIGINT, original_sigint_handler)


@run_cli.callback()
def run(
    path: Optional[str] = typer.Argument(
        None,
        help=(
            "Path to a local folder containing an agent.json file or a built-in agent "
            "stored in the 'tiny-agents/tiny-agents' Hugging Face dataset "
            "(https://huggingface.co/datasets/tiny-agents/tiny-agents)"
        ),
        show_default=False,
    ),
):
    try:
        asyncio.run(run_agent(path))
    except KeyboardInterrupt:
        print("\n[red]Application terminated by KeyboardInterrupt.[/red]", flush=True)
        raise typer.Exit(code=130)
    except Exception as e:
        print(f"\n[bold red]An unexpected error occurred: {e}[/bold red]", flush=True)
        raise e


if __name__ == "__main__":
    app()

# === NexusCore/openenv\Lib\site-packages\IPython\extensions\storemagic.py ===
# -*- coding: utf-8 -*-
"""
%store magic for lightweight persistence.

Stores variables, aliases and macros in IPython's database.

To automatically restore stored variables at startup, add this to your
:file:`ipython_config.py` file::

  c.StoreMagics.autorestore = True
"""

# Copyright (c) IPython Development Team.
# Distributed under the terms of the Modified BSD License.

import inspect, os, sys, textwrap

from IPython.core.error import UsageError
from IPython.core.magic import Magics, magics_class, line_magic
from IPython.testing.skipdoctest import skip_doctest
from traitlets import Bool


def restore_aliases(ip, alias=None):
    staliases = ip.db.get('stored_aliases', {})
    if alias is None:
        for k,v in staliases.items():
            # print("restore alias",k,v)  # dbg
            #self.alias_table[k] = v
            ip.alias_manager.define_alias(k,v)
    else:
        ip.alias_manager.define_alias(alias, staliases[alias])


def refresh_variables(ip):
    db = ip.db
    for key in db.keys('autorestore/*'):
        # strip autorestore
        justkey = os.path.basename(key)
        try:
            obj = db[key]
        except KeyError:
            print("Unable to restore variable '%s', ignoring (use %%store -d to forget!)" % justkey)
            print("The error was:", sys.exc_info()[0])
        else:
            # print("restored",justkey,"=",obj)  # dbg
            ip.user_ns[justkey] = obj


def restore_dhist(ip):
    ip.user_ns['_dh'] = ip.db.get('dhist',[])


def restore_data(ip):
    refresh_variables(ip)
    restore_aliases(ip)
    restore_dhist(ip)


@magics_class
class StoreMagics(Magics):
    """Lightweight persistence for python variables.

    Provides the %store magic."""

    autorestore = Bool(False, help=
        """If True, any %store-d variables will be automatically restored
        when IPython starts.
        """
    ).tag(config=True)

    def __init__(self, shell):
        super(StoreMagics, self).__init__(shell=shell)
        self.shell.configurables.append(self)
        if self.autorestore:
            restore_data(self.shell)

    @skip_doctest
    @line_magic
    def store(self, parameter_s=''):
        """Lightweight persistence for python variables.

        Example::

          In [1]: l = ['hello',10,'world']
          In [2]: %store l
          Stored 'l' (list)
          In [3]: exit

          (IPython session is closed and started again...)

          ville@badger:~$ ipython
          In [1]: l
          NameError: name 'l' is not defined
          In [2]: %store -r
          In [3]: l
          Out[3]: ['hello', 10, 'world']

        Usage:

        * ``%store``          - Show list of all variables and their current
                                values
        * ``%store spam bar`` - Store the *current* value of the variables spam
                                and bar to disk
        * ``%store -d spam``  - Remove the variable and its value from storage
        * ``%store -z``       - Remove all variables from storage
        * ``%store -r``       - Refresh all variables, aliases and directory history
                                from store (overwrite current vals)
        * ``%store -r spam bar`` - Refresh specified variables and aliases from store
                                   (delete current val)
        * ``%store foo >a.txt``  - Store value of foo to new file a.txt
        * ``%store foo >>a.txt`` - Append value of foo to file a.txt

        It should be noted that if you change the value of a variable, you
        need to %store it again if you want to persist the new value.

        Note also that the variables will need to be pickleable; most basic
        python types can be safely %store'd.

        Also aliases can be %store'd across sessions.
        To remove an alias from the storage, use the %unalias magic.
        """

        opts,argsl = self.parse_options(parameter_s,'drz',mode='string')
        args = argsl.split()
        ip = self.shell
        db = ip.db
        # delete
        if 'd' in opts:
            try:
                todel = args[0]
            except IndexError as e:
                raise UsageError('You must provide the variable to forget') from e
            else:
                try:
                    del db['autorestore/' + todel]
                except BaseException as e:
                    raise UsageError("Can't delete variable '%s'" % todel) from e
        # reset
        elif 'z' in opts:
            for k in db.keys('autorestore/*'):
                del db[k]

        elif 'r' in opts:
            if args:
                for arg in args:
                    try:
                        obj = db["autorestore/" + arg]
                    except KeyError:
                        try:
                            restore_aliases(ip, alias=arg)
                        except KeyError:
                            print("no stored variable or alias %s" % arg)
                    else:
                        ip.user_ns[arg] = obj
            else:
                restore_data(ip)

        # run without arguments -> list variables & values
        elif not args:
            vars = db.keys('autorestore/*')
            vars.sort()
            if vars:
                size = max(map(len, vars))
            else:
                size = 0

            print('Stored variables and their in-db values:')
            fmt = '%-'+str(size)+'s -> %s'
            get = db.get
            for var in vars:
                justkey = os.path.basename(var)
                # print 30 first characters from every var
                print(fmt % (justkey, repr(get(var, '<unavailable>'))[:50]))

        # default action - store the variable
        else:
            # %store foo >file.txt or >>file.txt
            if len(args) > 1 and args[1].startswith(">"):
                fnam = os.path.expanduser(args[1].lstrip(">").lstrip())
                if args[1].startswith(">>"):
                    fil = open(fnam, "a", encoding="utf-8")
                else:
                    fil = open(fnam, "w", encoding="utf-8")
                with fil:
                    obj = ip.ev(args[0])
                    print("Writing '%s' (%s) to file '%s'." % (args[0],
                        obj.__class__.__name__, fnam))

                    if not isinstance (obj, str):
                        from pprint import pprint
                        pprint(obj, fil)
                    else:
                        fil.write(obj)
                        if not obj.endswith('\n'):
                            fil.write('\n')

                return

            # %store foo
            for arg in args:
                try:
                    obj = ip.user_ns[arg]
                except KeyError:
                    # it might be an alias
                    name = arg
                    try:
                        cmd = ip.alias_manager.retrieve_alias(name)
                    except ValueError as e:
                        raise UsageError("Unknown variable '%s'" % name) from e

                    staliases = db.get('stored_aliases',{})
                    staliases[name] = cmd
                    db['stored_aliases'] = staliases
                    print("Alias stored: %s (%s)" % (name, cmd))
                    return

                else:
                    modname = getattr(inspect.getmodule(obj), '__name__', '')
                    if modname == '__main__':
                        print(textwrap.dedent("""\
                        Warning:%s is %s
                        Proper storage of interactively declared classes (or instances
                        of those classes) is not possible! Only instances
                        of classes in real modules on file system can be %%store'd.
                        """ % (arg, obj) ))
                        return
                    #pickled = pickle.dumps(obj)
                    db[ 'autorestore/' + arg ] = obj
                    print("Stored '%s' (%s)" % (arg, obj.__class__.__name__))


def load_ipython_extension(ip):
    """Load the extension in IPython."""
    ip.register_magics(StoreMagics)


# === NexusCore/openenv\Lib\site-packages\joblib\externals\loky\backend\queues.py ===
###############################################################################
# Queue and SimpleQueue implementation for loky
#
# authors: Thomas Moreau, Olivier Grisel
#
# based on multiprocessing/queues.py (16/02/2017)
# * Add some custom reducers for the Queues/SimpleQueue to tweak the
#   pickling process. (overload Queue._feed/SimpleQueue.put)
#
import os
import sys
import errno
import weakref
import threading
from multiprocessing import util
from multiprocessing.queues import (
    Full,
    Queue as mp_Queue,
    SimpleQueue as mp_SimpleQueue,
    _sentinel,
)
from multiprocessing.context import assert_spawning

from .reduction import dumps


__all__ = ["Queue", "SimpleQueue", "Full"]


class Queue(mp_Queue):
    def __init__(self, maxsize=0, reducers=None, ctx=None):
        super().__init__(maxsize=maxsize, ctx=ctx)
        self._reducers = reducers

    # Use custom queue set/get state to be able to reduce the custom reducers
    def __getstate__(self):
        assert_spawning(self)
        return (
            self._ignore_epipe,
            self._maxsize,
            self._reader,
            self._writer,
            self._reducers,
            self._rlock,
            self._wlock,
            self._sem,
            self._opid,
        )

    def __setstate__(self, state):
        (
            self._ignore_epipe,
            self._maxsize,
            self._reader,
            self._writer,
            self._reducers,
            self._rlock,
            self._wlock,
            self._sem,
            self._opid,
        ) = state
        if sys.version_info >= (3, 9):
            self._reset()
        else:
            self._after_fork()

    # Overload _start_thread to correctly call our custom _feed
    def _start_thread(self):
        util.debug("Queue._start_thread()")

        # Start thread which transfers data from buffer to pipe
        self._buffer.clear()
        self._thread = threading.Thread(
            target=Queue._feed,
            args=(
                self._buffer,
                self._notempty,
                self._send_bytes,
                self._wlock,
                self._writer.close,
                self._reducers,
                self._ignore_epipe,
                self._on_queue_feeder_error,
                self._sem,
            ),
            name="QueueFeederThread",
        )
        self._thread.daemon = True

        util.debug("doing self._thread.start()")
        self._thread.start()
        util.debug("... done self._thread.start()")

        # On process exit we will wait for data to be flushed to pipe.
        #
        # However, if this process created the queue then all
        # processes which use the queue will be descendants of this
        # process.  Therefore waiting for the queue to be flushed
        # is pointless once all the child processes have been joined.
        created_by_this_process = self._opid == os.getpid()
        if not self._joincancelled and not created_by_this_process:
            self._jointhread = util.Finalize(
                self._thread,
                Queue._finalize_join,
                [weakref.ref(self._thread)],
                exitpriority=-5,
            )

        # Send sentinel to the thread queue object when garbage collected
        self._close = util.Finalize(
            self,
            Queue._finalize_close,
            [self._buffer, self._notempty],
            exitpriority=10,
        )

    # Overload the _feed methods to use our custom pickling strategy.
    @staticmethod
    def _feed(
        buffer,
        notempty,
        send_bytes,
        writelock,
        close,
        reducers,
        ignore_epipe,
        onerror,
        queue_sem,
    ):
        util.debug("starting thread to feed data to pipe")
        nacquire = notempty.acquire
        nrelease = notempty.release
        nwait = notempty.wait
        bpopleft = buffer.popleft
        sentinel = _sentinel
        if sys.platform != "win32":
            wacquire = writelock.acquire
            wrelease = writelock.release
        else:
            wacquire = None

        while True:
            try:
                nacquire()
                try:
                    if not buffer:
                        nwait()
                finally:
                    nrelease()
                try:
                    while True:
                        obj = bpopleft()
                        if obj is sentinel:
                            util.debug("feeder thread got sentinel -- exiting")
                            close()
                            return

                        # serialize the data before acquiring the lock
                        obj_ = dumps(obj, reducers=reducers)
                        if wacquire is None:
                            send_bytes(obj_)
                        else:
                            wacquire()
                            try:
                                send_bytes(obj_)
                            finally:
                                wrelease()
                        # Remove references early to avoid leaking memory
                        del obj, obj_
                except IndexError:
                    pass
            except BaseException as e:
                if ignore_epipe and getattr(e, "errno", 0) == errno.EPIPE:
                    return
                # Since this runs in a daemon thread the resources it uses
                # may be become unusable while the process is cleaning up.
                # We ignore errors which happen after the process has
                # started to cleanup.
                if util.is_exiting():
                    util.info(f"error in queue thread: {e}")
                    return
                else:
                    queue_sem.release()
                    onerror(e, obj)

    def _on_queue_feeder_error(self, e, obj):
        """
        Private API hook called when feeding data in the background thread
        raises an exception.  For overriding by concurrent.futures.
        """
        import traceback

        traceback.print_exc()


class SimpleQueue(mp_SimpleQueue):
    def __init__(self, reducers=None, ctx=None):
        super().__init__(ctx=ctx)

        # Add possiblity to use custom reducers
        self._reducers = reducers

    def close(self):
        self._reader.close()
        self._writer.close()

    # Use custom queue set/get state to be able to reduce the custom reducers
    def __getstate__(self):
        assert_spawning(self)
        return (
            self._reader,
            self._writer,
            self._reducers,
            self._rlock,
            self._wlock,
        )

    def __setstate__(self, state):
        (
            self._reader,
            self._writer,
            self._reducers,
            self._rlock,
            self._wlock,
        ) = state

    # Overload put to use our customizable reducer
    def put(self, obj):
        # serialize the data before acquiring the lock
        obj = dumps(obj, reducers=self._reducers)
        if self._wlock is None:
            # writes to a message oriented win32 pipe are atomic
            self._writer.send_bytes(obj)
        else:
            with self._wlock:
                self._writer.send_bytes(obj)

# === NexusCore/openenv\Lib\site-packages\markdown_it\rules_block\table.py ===
# GFM table, https://github.github.com/gfm/#tables-extension-
from __future__ import annotations

import re

from ..common.utils import charStrAt, isStrSpace
from .state_block import StateBlock

headerLineRe = re.compile(r"^:?-+:?$")
enclosingPipesRe = re.compile(r"^\||\|$")


def getLine(state: StateBlock, line: int) -> str:
    pos = state.bMarks[line] + state.tShift[line]
    maximum = state.eMarks[line]

    # return state.src.substr(pos, max - pos)
    return state.src[pos:maximum]


def escapedSplit(string: str) -> list[str]:
    result: list[str] = []
    pos = 0
    max = len(string)
    isEscaped = False
    lastPos = 0
    current = ""
    ch = charStrAt(string, pos)

    while pos < max:
        if ch == "|":
            if not isEscaped:
                # pipe separating cells, '|'
                result.append(current + string[lastPos:pos])
                current = ""
                lastPos = pos + 1
            else:
                # escaped pipe, '\|'
                current += string[lastPos : pos - 1]
                lastPos = pos

        isEscaped = ch == "\\"
        pos += 1

        ch = charStrAt(string, pos)

    result.append(current + string[lastPos:])

    return result


def table(state: StateBlock, startLine: int, endLine: int, silent: bool) -> bool:
    tbodyLines = None

    # should have at least two lines
    if startLine + 2 > endLine:
        return False

    nextLine = startLine + 1

    if state.sCount[nextLine] < state.blkIndent:
        return False

    if state.is_code_block(nextLine):
        return False

    # first character of the second line should be '|', '-', ':',
    # and no other characters are allowed but spaces;
    # basically, this is the equivalent of /^[-:|][-:|\s]*$/ regexp

    pos = state.bMarks[nextLine] + state.tShift[nextLine]
    if pos >= state.eMarks[nextLine]:
        return False
    first_ch = state.src[pos]
    pos += 1
    if first_ch not in ("|", "-", ":"):
        return False

    if pos >= state.eMarks[nextLine]:
        return False
    second_ch = state.src[pos]
    pos += 1
    if second_ch not in ("|", "-", ":") and not isStrSpace(second_ch):
        return False

    # if first character is '-', then second character must not be a space
    # (due to parsing ambiguity with list)
    if first_ch == "-" and isStrSpace(second_ch):
        return False

    while pos < state.eMarks[nextLine]:
        ch = state.src[pos]

        if ch not in ("|", "-", ":") and not isStrSpace(ch):
            return False

        pos += 1

    lineText = getLine(state, startLine + 1)

    columns = lineText.split("|")
    aligns = []
    for i in range(len(columns)):
        t = columns[i].strip()
        if not t:
            # allow empty columns before and after table, but not in between columns;
            # e.g. allow ` |---| `, disallow ` ---||--- `
            if i == 0 or i == len(columns) - 1:
                continue
            else:
                return False

        if not headerLineRe.search(t):
            return False
        if charStrAt(t, len(t) - 1) == ":":
            aligns.append("center" if charStrAt(t, 0) == ":" else "right")
        elif charStrAt(t, 0) == ":":
            aligns.append("left")
        else:
            aligns.append("")

    lineText = getLine(state, startLine).strip()
    if "|" not in lineText:
        return False
    if state.is_code_block(startLine):
        return False
    columns = escapedSplit(lineText)
    if columns and columns[0] == "":
        columns.pop(0)
    if columns and columns[-1] == "":
        columns.pop()

    # header row will define an amount of columns in the entire table,
    # and align row should be exactly the same (the rest of the rows can differ)
    columnCount = len(columns)
    if columnCount == 0 or columnCount != len(aligns):
        return False

    if silent:
        return True

    oldParentType = state.parentType
    state.parentType = "table"

    # use 'blockquote' lists for termination because it's
    # the most similar to tables
    terminatorRules = state.md.block.ruler.getRules("blockquote")

    token = state.push("table_open", "table", 1)
    token.map = tableLines = [startLine, 0]

    token = state.push("thead_open", "thead", 1)
    token.map = [startLine, startLine + 1]

    token = state.push("tr_open", "tr", 1)
    token.map = [startLine, startLine + 1]

    for i in range(len(columns)):
        token = state.push("th_open", "th", 1)
        if aligns[i]:
            token.attrs = {"style": "text-align:" + aligns[i]}

        token = state.push("inline", "", 0)
        # note in markdown-it this map was removed in v12.0.0 however, we keep it,
        # since it is helpful to propagate to children tokens
        token.map = [startLine, startLine + 1]
        token.content = columns[i].strip()
        token.children = []

        token = state.push("th_close", "th", -1)

    token = state.push("tr_close", "tr", -1)
    token = state.push("thead_close", "thead", -1)

    nextLine = startLine + 2
    while nextLine < endLine:
        if state.sCount[nextLine] < state.blkIndent:
            break

        terminate = False
        for i in range(len(terminatorRules)):
            if terminatorRules[i](state, nextLine, endLine, True):
                terminate = True
                break

        if terminate:
            break
        lineText = getLine(state, nextLine).strip()
        if not lineText:
            break
        if state.is_code_block(nextLine):
            break
        columns = escapedSplit(lineText)
        if columns and columns[0] == "":
            columns.pop(0)
        if columns and columns[-1] == "":
            columns.pop()

        if nextLine == startLine + 2:
            token = state.push("tbody_open", "tbody", 1)
            token.map = tbodyLines = [startLine + 2, 0]

        token = state.push("tr_open", "tr", 1)
        token.map = [nextLine, nextLine + 1]

        for i in range(columnCount):
            token = state.push("td_open", "td", 1)
            if aligns[i]:
                token.attrs = {"style": "text-align:" + aligns[i]}

            token = state.push("inline", "", 0)
            # note in markdown-it this map was removed in v12.0.0 however, we keep it,
            # since it is helpful to propagate to children tokens
            token.map = [nextLine, nextLine + 1]
            try:
                token.content = columns[i].strip() if columns[i] else ""
            except IndexError:
                token.content = ""
            token.children = []

            token = state.push("td_close", "td", -1)

        token = state.push("tr_close", "tr", -1)

        nextLine += 1

    if tbodyLines:
        token = state.push("tbody_close", "tbody", -1)
        tbodyLines[1] = nextLine

    token = state.push("table_close", "table", -1)

    tableLines[1] = nextLine
    state.parentType = oldParentType
    state.line = nextLine
    return True

# === NexusCore/openenv\Lib\site-packages\nltk\tag\stanford.py ===
# Natural Language Toolkit: Interface to the Stanford Part-of-speech and Named-Entity Taggers
#
# Copyright (C) 2001-2024 NLTK Project
# Author: Nitin Madnani <nmadnani@ets.org>
#         Rami Al-Rfou' <ralrfou@cs.stonybrook.edu>
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT

"""
A module for interfacing with the Stanford taggers.

Tagger models need to be downloaded from https://nlp.stanford.edu/software
and the STANFORD_MODELS environment variable set (a colon-separated
list of paths).

For more details see the documentation for StanfordPOSTagger and StanfordNERTagger.
"""

import os
import tempfile
import warnings
from abc import abstractmethod
from subprocess import PIPE

from nltk.internals import _java_options, config_java, find_file, find_jar, java
from nltk.tag.api import TaggerI

_stanford_url = "https://nlp.stanford.edu/software"


class StanfordTagger(TaggerI):
    """
    An interface to Stanford taggers. Subclasses must define:

    - ``_cmd`` property: A property that returns the command that will be
      executed.
    - ``_SEPARATOR``: Class constant that represents that character that
      is used to separate the tokens from their tags.
    - ``_JAR`` file: Class constant that represents the jar file name.
    """

    _SEPARATOR = ""
    _JAR = ""

    def __init__(
        self,
        model_filename,
        path_to_jar=None,
        encoding="utf8",
        verbose=False,
        java_options="-mx1000m",
    ):
        # Raise deprecation warning.
        warnings.warn(
            str(
                "\nThe StanfordTokenizer will "
                "be deprecated in version 3.2.6.\n"
                "Please use \033[91mnltk.parse.corenlp.CoreNLPParser\033[0m instead."
            ),
            DeprecationWarning,
            stacklevel=2,
        )

        if not self._JAR:
            warnings.warn(
                "The StanfordTagger class is not meant to be "
                "instantiated directly. Did you mean "
                "StanfordPOSTagger or StanfordNERTagger?"
            )
        self._stanford_jar = find_jar(
            self._JAR, path_to_jar, searchpath=(), url=_stanford_url, verbose=verbose
        )

        self._stanford_model = find_file(
            model_filename, env_vars=("STANFORD_MODELS",), verbose=verbose
        )

        self._encoding = encoding
        self.java_options = java_options

    @property
    @abstractmethod
    def _cmd(self):
        """
        A property that returns the command that will be executed.
        """

    def tag(self, tokens):
        # This function should return list of tuple rather than list of list
        return sum(self.tag_sents([tokens]), [])

    def tag_sents(self, sentences):
        encoding = self._encoding
        default_options = " ".join(_java_options)
        config_java(options=self.java_options, verbose=False)

        # Create a temporary input file
        _input_fh, self._input_file_path = tempfile.mkstemp(text=True)

        cmd = list(self._cmd)
        cmd.extend(["-encoding", encoding])

        # Write the actual sentences to the temporary input file
        _input_fh = os.fdopen(_input_fh, "wb")
        _input = "\n".join(" ".join(x) for x in sentences)
        if isinstance(_input, str) and encoding:
            _input = _input.encode(encoding)
        _input_fh.write(_input)
        _input_fh.close()

        # Run the tagger and get the output
        stanpos_output, _stderr = java(
            cmd, classpath=self._stanford_jar, stdout=PIPE, stderr=PIPE
        )
        stanpos_output = stanpos_output.decode(encoding)

        # Delete the temporary file
        os.unlink(self._input_file_path)

        # Return java configurations to their default values
        config_java(options=default_options, verbose=False)

        return self.parse_output(stanpos_output, sentences)

    def parse_output(self, text, sentences=None):
        # Output the tagged sentences
        tagged_sentences = []
        for tagged_sentence in text.strip().split("\n"):
            sentence = []
            for tagged_word in tagged_sentence.strip().split():
                word_tags = tagged_word.strip().split(self._SEPARATOR)
                sentence.append(
                    ("".join(word_tags[:-1]), word_tags[-1].replace("0", "").upper())
                )
            tagged_sentences.append(sentence)
        return tagged_sentences


class StanfordPOSTagger(StanfordTagger):
    """
    A class for pos tagging with Stanford Tagger. The input is the paths to:
     - a model trained on training data
     - (optionally) the path to the stanford tagger jar file. If not specified here,
       then this jar file must be specified in the CLASSPATH environment variable.
     - (optionally) the encoding of the training data (default: UTF-8)

    Example:

        >>> from nltk.tag import StanfordPOSTagger
        >>> st = StanfordPOSTagger('english-bidirectional-distsim.tagger') # doctest: +SKIP
        >>> st.tag('What is the airspeed of an unladen swallow ?'.split()) # doctest: +SKIP
        [('What', 'WP'), ('is', 'VBZ'), ('the', 'DT'), ('airspeed', 'NN'), ('of', 'IN'), ('an', 'DT'), ('unladen', 'JJ'), ('swallow', 'VB'), ('?', '.')]
    """

    _SEPARATOR = "_"
    _JAR = "stanford-postagger.jar"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    @property
    def _cmd(self):
        return [
            "edu.stanford.nlp.tagger.maxent.MaxentTagger",
            "-model",
            self._stanford_model,
            "-textFile",
            self._input_file_path,
            "-tokenize",
            "false",
            "-outputFormatOptions",
            "keepEmptySentences",
        ]


class StanfordNERTagger(StanfordTagger):
    """
    A class for Named-Entity Tagging with Stanford Tagger. The input is the paths to:

    - a model trained on training data
    - (optionally) the path to the stanford tagger jar file. If not specified here,
      then this jar file must be specified in the CLASSPATH environment variable.
    - (optionally) the encoding of the training data (default: UTF-8)

    Example:

        >>> from nltk.tag import StanfordNERTagger
        >>> st = StanfordNERTagger('english.all.3class.distsim.crf.ser.gz') # doctest: +SKIP
        >>> st.tag('Rami Eid is studying at Stony Brook University in NY'.split()) # doctest: +SKIP
        [('Rami', 'PERSON'), ('Eid', 'PERSON'), ('is', 'O'), ('studying', 'O'),
         ('at', 'O'), ('Stony', 'ORGANIZATION'), ('Brook', 'ORGANIZATION'),
         ('University', 'ORGANIZATION'), ('in', 'O'), ('NY', 'LOCATION')]
    """

    _SEPARATOR = "/"
    _JAR = "stanford-ner.jar"
    _FORMAT = "slashTags"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    @property
    def _cmd(self):
        # Adding -tokenizerFactory edu.stanford.nlp.process.WhitespaceTokenizer -tokenizerOptions tokenizeNLs=false for not using stanford Tokenizer
        return [
            "edu.stanford.nlp.ie.crf.CRFClassifier",
            "-loadClassifier",
            self._stanford_model,
            "-textFile",
            self._input_file_path,
            "-outputFormat",
            self._FORMAT,
            "-tokenizerFactory",
            "edu.stanford.nlp.process.WhitespaceTokenizer",
            "-tokenizerOptions",
            '"tokenizeNLs=false"',
        ]

    def parse_output(self, text, sentences):
        if self._FORMAT == "slashTags":
            # Joint together to a big list
            tagged_sentences = []
            for tagged_sentence in text.strip().split("\n"):
                for tagged_word in tagged_sentence.strip().split():
                    word_tags = tagged_word.strip().split(self._SEPARATOR)
                    tagged_sentences.append(("".join(word_tags[:-1]), word_tags[-1]))

            # Separate it according to the input
            result = []
            start = 0
            for sent in sentences:
                result.append(tagged_sentences[start : start + len(sent)])
                start += len(sent)
            return result

        raise NotImplementedError

# === NexusCore/openenv\Lib\site-packages\prompt_toolkit\styles\defaults.py ===
"""
The default styling.
"""

from __future__ import annotations

from prompt_toolkit.cache import memoized

from .base import ANSI_COLOR_NAMES, BaseStyle
from .named_colors import NAMED_COLORS
from .style import Style, merge_styles

__all__ = [
    "default_ui_style",
    "default_pygments_style",
]

#: Default styling. Mapping from classnames to their style definition.
PROMPT_TOOLKIT_STYLE = [
    # Highlighting of search matches in document.
    ("search", "bg:ansibrightyellow ansiblack"),
    ("search.current", ""),
    # Incremental search.
    ("incsearch", ""),
    ("incsearch.current", "reverse"),
    # Highlighting of select text in document.
    ("selected", "reverse"),
    ("cursor-column", "bg:#dddddd"),
    ("cursor-line", "underline"),
    ("color-column", "bg:#ccaacc"),
    # Highlighting of matching brackets.
    ("matching-bracket", ""),
    ("matching-bracket.other", "#000000 bg:#aacccc"),
    ("matching-bracket.cursor", "#ff8888 bg:#880000"),
    # Styling of other cursors, in case of block editing.
    ("multiple-cursors", "#000000 bg:#ccccaa"),
    # Line numbers.
    ("line-number", "#888888"),
    ("line-number.current", "bold"),
    ("tilde", "#8888ff"),
    # Default prompt.
    ("prompt", ""),
    ("prompt.arg", "noinherit"),
    ("prompt.arg.text", ""),
    ("prompt.search", "noinherit"),
    ("prompt.search.text", ""),
    # Search toolbar.
    ("search-toolbar", "bold"),
    ("search-toolbar.text", "nobold"),
    # System toolbar
    ("system-toolbar", "bold"),
    ("system-toolbar.text", "nobold"),
    # "arg" toolbar.
    ("arg-toolbar", "bold"),
    ("arg-toolbar.text", "nobold"),
    # Validation toolbar.
    ("validation-toolbar", "bg:#550000 #ffffff"),
    ("window-too-small", "bg:#550000 #ffffff"),
    # Completions toolbar.
    ("completion-toolbar", "bg:#bbbbbb #000000"),
    ("completion-toolbar.arrow", "bg:#bbbbbb #000000 bold"),
    ("completion-toolbar.completion", "bg:#bbbbbb #000000"),
    ("completion-toolbar.completion.current", "bg:#444444 #ffffff"),
    # Completions menu.
    ("completion-menu", "bg:#bbbbbb #000000"),
    ("completion-menu.completion", ""),
    # (Note: for the current completion, we use 'reverse' on top of fg/bg
    # colors. This is to have proper rendering with NO_COLOR=1).
    ("completion-menu.completion.current", "fg:#888888 bg:#ffffff reverse"),
    ("completion-menu.meta.completion", "bg:#999999 #000000"),
    ("completion-menu.meta.completion.current", "bg:#aaaaaa #000000"),
    ("completion-menu.multi-column-meta", "bg:#aaaaaa #000000"),
    # Fuzzy matches in completion menu (for FuzzyCompleter).
    ("completion-menu.completion fuzzymatch.outside", "fg:#444444"),
    ("completion-menu.completion fuzzymatch.inside", "bold"),
    ("completion-menu.completion fuzzymatch.inside.character", "underline"),
    ("completion-menu.completion.current fuzzymatch.outside", "fg:default"),
    ("completion-menu.completion.current fuzzymatch.inside", "nobold"),
    # Styling of readline-like completions.
    ("readline-like-completions", ""),
    ("readline-like-completions.completion", ""),
    ("readline-like-completions.completion fuzzymatch.outside", "#888888"),
    ("readline-like-completions.completion fuzzymatch.inside", ""),
    ("readline-like-completions.completion fuzzymatch.inside.character", "underline"),
    # Scrollbars.
    ("scrollbar.background", "bg:#aaaaaa"),
    ("scrollbar.button", "bg:#444444"),
    ("scrollbar.arrow", "noinherit bold"),
    # Start/end of scrollbars. Adding 'underline' here provides a nice little
    # detail to the progress bar, but it doesn't look good on all terminals.
    # ('scrollbar.start',                          'underline #ffffff'),
    # ('scrollbar.end',                            'underline #000000'),
    # Auto suggestion text.
    ("auto-suggestion", "#666666"),
    # Trailing whitespace and tabs.
    ("trailing-whitespace", "#999999"),
    ("tab", "#999999"),
    # When Control-C/D has been pressed. Grayed.
    ("aborting", "#888888 bg:default noreverse noitalic nounderline noblink"),
    ("exiting", "#888888 bg:default noreverse noitalic nounderline noblink"),
    # Entering a Vi digraph.
    ("digraph", "#4444ff"),
    # Control characters, like ^C, ^X.
    ("control-character", "ansiblue"),
    # Non-breaking space.
    ("nbsp", "underline ansiyellow"),
    # Default styling of HTML elements.
    ("i", "italic"),
    ("u", "underline"),
    ("s", "strike"),
    ("b", "bold"),
    ("em", "italic"),
    ("strong", "bold"),
    ("del", "strike"),
    ("hidden", "hidden"),
    # It should be possible to use the style names in HTML.
    # <reverse>...</reverse>  or <noreverse>...</noreverse>.
    ("italic", "italic"),
    ("underline", "underline"),
    ("strike", "strike"),
    ("bold", "bold"),
    ("reverse", "reverse"),
    ("noitalic", "noitalic"),
    ("nounderline", "nounderline"),
    ("nostrike", "nostrike"),
    ("nobold", "nobold"),
    ("noreverse", "noreverse"),
    # Prompt bottom toolbar
    ("bottom-toolbar", "reverse"),
]


# Style that will turn for instance the class 'red' into 'red'.
COLORS_STYLE = [(name, "fg:" + name) for name in ANSI_COLOR_NAMES] + [
    (name.lower(), "fg:" + name) for name in NAMED_COLORS
]


WIDGETS_STYLE = [
    # Dialog windows.
    ("dialog", "bg:#4444ff"),
    ("dialog.body", "bg:#ffffff #000000"),
    ("dialog.body text-area", "bg:#cccccc"),
    ("dialog.body text-area last-line", "underline"),
    ("dialog frame.label", "#ff0000 bold"),
    # Scrollbars in dialogs.
    ("dialog.body scrollbar.background", ""),
    ("dialog.body scrollbar.button", "bg:#000000"),
    ("dialog.body scrollbar.arrow", ""),
    ("dialog.body scrollbar.start", "nounderline"),
    ("dialog.body scrollbar.end", "nounderline"),
    # Buttons.
    ("button", ""),
    ("button.arrow", "bold"),
    ("button.focused", "bg:#aa0000 #ffffff"),
    # Menu bars.
    ("menu-bar", "bg:#aaaaaa #000000"),
    ("menu-bar.selected-item", "bg:#ffffff #000000"),
    ("menu", "bg:#888888 #ffffff"),
    ("menu.border", "#aaaaaa"),
    ("menu.border shadow", "#444444"),
    # Shadows.
    ("dialog shadow", "bg:#000088"),
    ("dialog.body shadow", "bg:#aaaaaa"),
    ("progress-bar", "bg:#000088"),
    ("progress-bar.used", "bg:#ff0000"),
]


# The default Pygments style, include this by default in case a Pygments lexer
# is used.
PYGMENTS_DEFAULT_STYLE = {
    "pygments.whitespace": "#bbbbbb",
    "pygments.comment": "italic #408080",
    "pygments.comment.preproc": "noitalic #bc7a00",
    "pygments.keyword": "bold #008000",
    "pygments.keyword.pseudo": "nobold",
    "pygments.keyword.type": "nobold #b00040",
    "pygments.operator": "#666666",
    "pygments.operator.word": "bold #aa22ff",
    "pygments.name.builtin": "#008000",
    "pygments.name.function": "#0000ff",
    "pygments.name.class": "bold #0000ff",
    "pygments.name.namespace": "bold #0000ff",
    "pygments.name.exception": "bold #d2413a",
    "pygments.name.variable": "#19177c",
    "pygments.name.constant": "#880000",
    "pygments.name.label": "#a0a000",
    "pygments.name.entity": "bold #999999",
    "pygments.name.attribute": "#7d9029",
    "pygments.name.tag": "bold #008000",
    "pygments.name.decorator": "#aa22ff",
    # Note: In Pygments, Token.String is an alias for Token.Literal.String,
    #       and Token.Number as an alias for Token.Literal.Number.
    "pygments.literal.string": "#ba2121",
    "pygments.literal.string.doc": "italic",
    "pygments.literal.string.interpol": "bold #bb6688",
    "pygments.literal.string.escape": "bold #bb6622",
    "pygments.literal.string.regex": "#bb6688",
    "pygments.literal.string.symbol": "#19177c",
    "pygments.literal.string.other": "#008000",
    "pygments.literal.number": "#666666",
    "pygments.generic.heading": "bold #000080",
    "pygments.generic.subheading": "bold #800080",
    "pygments.generic.deleted": "#a00000",
    "pygments.generic.inserted": "#00a000",
    "pygments.generic.error": "#ff0000",
    "pygments.generic.emph": "italic",
    "pygments.generic.strong": "bold",
    "pygments.generic.prompt": "bold #000080",
    "pygments.generic.output": "#888",
    "pygments.generic.traceback": "#04d",
    "pygments.error": "border:#ff0000",
}


@memoized()
def default_ui_style() -> BaseStyle:
    """
    Create a default `Style` object.
    """
    return merge_styles(
        [
            Style(PROMPT_TOOLKIT_STYLE),
            Style(COLORS_STYLE),
            Style(WIDGETS_STYLE),
        ]
    )


@memoized()
def default_pygments_style() -> Style:
    """
    Create a `Style` object that contains the default Pygments style.
    """
    return Style.from_dict(PYGMENTS_DEFAULT_STYLE)

# === NexusCore/openenv\Lib\site-packages\setuptools\_distutils\file_util.py ===
"""distutils.file_util

Utility functions for operating on single files.
"""

import os

from ._log import log
from .errors import DistutilsFileError

# for generating verbose output in 'copy_file()'
_copy_action = {None: 'copying', 'hard': 'hard linking', 'sym': 'symbolically linking'}


def _copy_file_contents(src, dst, buffer_size=16 * 1024):  # noqa: C901
    """Copy the file 'src' to 'dst'; both must be filenames.  Any error
    opening either file, reading from 'src', or writing to 'dst', raises
    DistutilsFileError.  Data is read/written in chunks of 'buffer_size'
    bytes (default 16k).  No attempt is made to handle anything apart from
    regular files.
    """
    # Stolen from shutil module in the standard library, but with
    # custom error-handling added.
    fsrc = None
    fdst = None
    try:
        try:
            fsrc = open(src, 'rb')
        except OSError as e:
            raise DistutilsFileError(f"could not open '{src}': {e.strerror}")

        if os.path.exists(dst):
            try:
                os.unlink(dst)
            except OSError as e:
                raise DistutilsFileError(f"could not delete '{dst}': {e.strerror}")

        try:
            fdst = open(dst, 'wb')
        except OSError as e:
            raise DistutilsFileError(f"could not create '{dst}': {e.strerror}")

        while True:
            try:
                buf = fsrc.read(buffer_size)
            except OSError as e:
                raise DistutilsFileError(f"could not read from '{src}': {e.strerror}")

            if not buf:
                break

            try:
                fdst.write(buf)
            except OSError as e:
                raise DistutilsFileError(f"could not write to '{dst}': {e.strerror}")
    finally:
        if fdst:
            fdst.close()
        if fsrc:
            fsrc.close()


def copy_file(  # noqa: C901
    src,
    dst,
    preserve_mode=True,
    preserve_times=True,
    update=False,
    link=None,
    verbose=True,
    dry_run=False,
):
    """Copy a file 'src' to 'dst'.  If 'dst' is a directory, then 'src' is
    copied there with the same name; otherwise, it must be a filename.  (If
    the file exists, it will be ruthlessly clobbered.)  If 'preserve_mode'
    is true (the default), the file's mode (type and permission bits, or
    whatever is analogous on the current platform) is copied.  If
    'preserve_times' is true (the default), the last-modified and
    last-access times are copied as well.  If 'update' is true, 'src' will
    only be copied if 'dst' does not exist, or if 'dst' does exist but is
    older than 'src'.

    'link' allows you to make hard links (os.link) or symbolic links
    (os.symlink) instead of copying: set it to "hard" or "sym"; if it is
    None (the default), files are copied.  Don't set 'link' on systems that
    don't support it: 'copy_file()' doesn't check if hard or symbolic
    linking is available. If hardlink fails, falls back to
    _copy_file_contents().

    Under Mac OS, uses the native file copy function in macostools; on
    other systems, uses '_copy_file_contents()' to copy file contents.

    Return a tuple (dest_name, copied): 'dest_name' is the actual name of
    the output file, and 'copied' is true if the file was copied (or would
    have been copied, if 'dry_run' true).
    """
    # XXX if the destination file already exists, we clobber it if
    # copying, but blow up if linking.  Hmmm.  And I don't know what
    # macostools.copyfile() does.  Should definitely be consistent, and
    # should probably blow up if destination exists and we would be
    # changing it (ie. it's not already a hard/soft link to src OR
    # (not update) and (src newer than dst).

    from distutils._modified import newer
    from stat import S_IMODE, ST_ATIME, ST_MODE, ST_MTIME

    if not os.path.isfile(src):
        raise DistutilsFileError(
            f"can't copy '{src}': doesn't exist or not a regular file"
        )

    if os.path.isdir(dst):
        dir = dst
        dst = os.path.join(dst, os.path.basename(src))
    else:
        dir = os.path.dirname(dst)

    if update and not newer(src, dst):
        if verbose >= 1:
            log.debug("not copying %s (output up-to-date)", src)
        return (dst, False)

    try:
        action = _copy_action[link]
    except KeyError:
        raise ValueError(f"invalid value '{link}' for 'link' argument")

    if verbose >= 1:
        if os.path.basename(dst) == os.path.basename(src):
            log.info("%s %s -> %s", action, src, dir)
        else:
            log.info("%s %s -> %s", action, src, dst)

    if dry_run:
        return (dst, True)

    # If linking (hard or symbolic), use the appropriate system call
    # (Unix only, of course, but that's the caller's responsibility)
    elif link == 'hard':
        if not (os.path.exists(dst) and os.path.samefile(src, dst)):
            try:
                os.link(src, dst)
            except OSError:
                # If hard linking fails, fall back on copying file
                # (some special filesystems don't support hard linking
                #  even under Unix, see issue #8876).
                pass
            else:
                return (dst, True)
    elif link == 'sym':
        if not (os.path.exists(dst) and os.path.samefile(src, dst)):
            os.symlink(src, dst)
            return (dst, True)

    # Otherwise (non-Mac, not linking), copy the file contents and
    # (optionally) copy the times and mode.
    _copy_file_contents(src, dst)
    if preserve_mode or preserve_times:
        st = os.stat(src)

        # According to David Ascher <da@ski.org>, utime() should be done
        # before chmod() (at least under NT).
        if preserve_times:
            os.utime(dst, (st[ST_ATIME], st[ST_MTIME]))
        if preserve_mode:
            os.chmod(dst, S_IMODE(st[ST_MODE]))

    return (dst, True)


# XXX I suspect this is Unix-specific -- need porting help!
def move_file(src, dst, verbose=True, dry_run=False):  # noqa: C901
    """Move a file 'src' to 'dst'.  If 'dst' is a directory, the file will
    be moved into it with the same name; otherwise, 'src' is just renamed
    to 'dst'.  Return the new full name of the file.

    Handles cross-device moves on Unix using 'copy_file()'.  What about
    other systems???
    """
    import errno
    from os.path import basename, dirname, exists, isdir, isfile

    if verbose >= 1:
        log.info("moving %s -> %s", src, dst)

    if dry_run:
        return dst

    if not isfile(src):
        raise DistutilsFileError(f"can't move '{src}': not a regular file")

    if isdir(dst):
        dst = os.path.join(dst, basename(src))
    elif exists(dst):
        raise DistutilsFileError(
            f"can't move '{src}': destination '{dst}' already exists"
        )

    if not isdir(dirname(dst)):
        raise DistutilsFileError(
            f"can't move '{src}': destination '{dst}' not a valid path"
        )

    copy_it = False
    try:
        os.rename(src, dst)
    except OSError as e:
        (num, msg) = e.args
        if num == errno.EXDEV:
            copy_it = True
        else:
            raise DistutilsFileError(f"couldn't move '{src}' to '{dst}': {msg}")

    if copy_it:
        copy_file(src, dst, verbose=verbose)
        try:
            os.unlink(src)
        except OSError as e:
            (num, msg) = e.args
            try:
                os.unlink(dst)
            except OSError:
                pass
            raise DistutilsFileError(
                f"couldn't move '{src}' to '{dst}' by copy/delete: "
                f"delete '{src}' failed: {msg}"
            )
    return dst


def write_file(filename, contents):
    """Create a file with the specified name and write 'contents' (a
    sequence of strings without line terminators) to it.
    """
    with open(filename, 'w', encoding='utf-8') as f:
        f.writelines(line + '\n' for line in contents)

# === NexusCore/openenv\Lib\site-packages\matplotlib\category.py ===
"""
Plotting of string "category" data: ``plot(['d', 'f', 'a'], [1, 2, 3])`` will
plot three points with x-axis values of 'd', 'f', 'a'.

See :doc:`/gallery/lines_bars_and_markers/categorical_variables` for an
example.

The module uses Matplotlib's `matplotlib.units` mechanism to convert from
strings to integers and provides a tick locator, a tick formatter, and the
`.UnitData` class that creates and stores the string-to-integer mapping.
"""

from collections import OrderedDict
import dateutil.parser
import itertools
import logging

import numpy as np

from matplotlib import _api, cbook, ticker, units


_log = logging.getLogger(__name__)


class StrCategoryConverter(units.ConversionInterface):
    @staticmethod
    def convert(value, unit, axis):
        """
        Convert strings in *value* to floats using mapping information stored
        in the *unit* object.

        Parameters
        ----------
        value : str or iterable
            Value or list of values to be converted.
        unit : `.UnitData`
            An object mapping strings to integers.
        axis : `~matplotlib.axis.Axis`
            The axis on which the converted value is plotted.

            .. note:: *axis* is unused.

        Returns
        -------
        float or `~numpy.ndarray` of float
        """
        if unit is None:
            raise ValueError(
                'Missing category information for StrCategoryConverter; '
                'this might be caused by unintendedly mixing categorical and '
                'numeric data')
        StrCategoryConverter._validate_unit(unit)
        # dtype = object preserves numerical pass throughs
        values = np.atleast_1d(np.array(value, dtype=object))
        # force an update so it also does type checking
        unit.update(values)
        s = np.vectorize(unit._mapping.__getitem__, otypes=[float])(values)
        return s if not cbook.is_scalar_or_string(value) else s[0]

    @staticmethod
    def axisinfo(unit, axis):
        """
        Set the default axis ticks and labels.

        Parameters
        ----------
        unit : `.UnitData`
            object string unit information for value
        axis : `~matplotlib.axis.Axis`
            axis for which information is being set

            .. note:: *axis* is not used

        Returns
        -------
        `~matplotlib.units.AxisInfo`
            Information to support default tick labeling

        """
        StrCategoryConverter._validate_unit(unit)
        # locator and formatter take mapping dict because
        # args need to be pass by reference for updates
        majloc = StrCategoryLocator(unit._mapping)
        majfmt = StrCategoryFormatter(unit._mapping)
        return units.AxisInfo(majloc=majloc, majfmt=majfmt)

    @staticmethod
    def default_units(data, axis):
        """
        Set and update the `~matplotlib.axis.Axis` units.

        Parameters
        ----------
        data : str or iterable of str
        axis : `~matplotlib.axis.Axis`
            axis on which the data is plotted

        Returns
        -------
        `.UnitData`
            object storing string to integer mapping
        """
        # the conversion call stack is default_units -> axis_info -> convert
        if axis.units is None:
            axis.set_units(UnitData(data))
        else:
            axis.units.update(data)
        return axis.units

    @staticmethod
    def _validate_unit(unit):
        if not hasattr(unit, '_mapping'):
            raise ValueError(
                f'Provided unit "{unit}" is not valid for a categorical '
                'converter, as it does not have a _mapping attribute.')


class StrCategoryLocator(ticker.Locator):
    """Tick at every integer mapping of the string data."""
    def __init__(self, units_mapping):
        """
        Parameters
        ----------
        units_mapping : dict
            Mapping of category names (str) to indices (int).
        """
        self._units = units_mapping

    def __call__(self):
        # docstring inherited
        return list(self._units.values())

    def tick_values(self, vmin, vmax):
        # docstring inherited
        return self()


class StrCategoryFormatter(ticker.Formatter):
    """String representation of the data at every tick."""
    def __init__(self, units_mapping):
        """
        Parameters
        ----------
        units_mapping : dict
            Mapping of category names (str) to indices (int).
        """
        self._units = units_mapping

    def __call__(self, x, pos=None):
        # docstring inherited
        return self.format_ticks([x])[0]

    def format_ticks(self, values):
        # docstring inherited
        r_mapping = {v: self._text(k) for k, v in self._units.items()}
        return [r_mapping.get(round(val), '') for val in values]

    @staticmethod
    def _text(value):
        """Convert text values into utf-8 or ascii strings."""
        if isinstance(value, bytes):
            value = value.decode(encoding='utf-8')
        elif not isinstance(value, str):
            value = str(value)
        return value


class UnitData:
    def __init__(self, data=None):
        """
        Create mapping between unique categorical values and integer ids.

        Parameters
        ----------
        data : iterable
            sequence of string values
        """
        self._mapping = OrderedDict()
        self._counter = itertools.count()
        if data is not None:
            self.update(data)

    @staticmethod
    def _str_is_convertible(val):
        """
        Helper method to check whether a string can be parsed as float or date.
        """
        try:
            float(val)
        except ValueError:
            try:
                dateutil.parser.parse(val)
            except (ValueError, TypeError):
                # TypeError if dateutil >= 2.8.1 else ValueError
                return False
        return True

    def update(self, data):
        """
        Map new values to integer identifiers.

        Parameters
        ----------
        data : iterable of str or bytes

        Raises
        ------
        TypeError
            If elements in *data* are neither str nor bytes.
        """
        data = np.atleast_1d(np.array(data, dtype=object))
        # check if convertible to number:
        convertible = True
        for val in OrderedDict.fromkeys(data):
            # OrderedDict just iterates over unique values in data.
            _api.check_isinstance((str, bytes), value=val)
            if convertible:
                # this will only be called so long as convertible is True.
                convertible = self._str_is_convertible(val)
            if val not in self._mapping:
                self._mapping[val] = next(self._counter)
        if data.size and convertible:
            _log.info('Using categorical units to plot a list of strings '
                      'that are all parsable as floats or dates. If these '
                      'strings should be plotted as numbers, cast to the '
                      'appropriate data type before plotting.')


# Register the converter with Matplotlib's unit framework
# Intentionally set to a single instance
units.registry[str] = \
    units.registry[np.str_] = \
    units.registry[bytes] = \
    units.registry[np.bytes_] = StrCategoryConverter()

# === NexusCore/openenv\Lib\site-packages\debugpy\adapter\__main__.py ===
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See LICENSE in the project root
# for license information.

import argparse
import atexit
import codecs
import locale
import os
import sys

# WARNING: debugpy and submodules must not be imported on top level in this module,
# and should be imported locally inside main() instead.


def main():
    args = _parse_argv(sys.argv)

    # If we're talking DAP over stdio, stderr is not guaranteed to be read from,
    # so disable it to avoid the pipe filling and locking up. This must be done
    # as early as possible, before the logging module starts writing to it.
    if args.port is None:
        sys.stderr = stderr = open(os.devnull, "w")
        atexit.register(stderr.close)

    from debugpy import adapter
    from debugpy.common import json, log, sockets
    from debugpy.adapter import clients, servers, sessions

    if args.for_server is not None:
        if os.name == "posix":
            # On POSIX, we need to leave the process group and its session, and then
            # daemonize properly by double-forking (first fork already happened when
            # this process was spawned).
            # NOTE: if process is already the session leader, then
            # setsid would fail with `operation not permitted`
            if os.getsid(os.getpid()) != os.getpid():
                os.setsid()
            if os.fork() != 0:
                sys.exit(0)

        for stdio in sys.stdin, sys.stdout, sys.stderr:
            if stdio is not None:
                stdio.close()

    if args.log_stderr:
        log.stderr.levels |= set(log.LEVELS)
    if args.log_dir is not None:
        log.log_dir = args.log_dir

    log.to_file(prefix="debugpy.adapter")
    log.describe_environment("debugpy.adapter startup environment:")

    servers.access_token = args.server_access_token
    if args.for_server is None:
        adapter.access_token = codecs.encode(os.urandom(32), "hex").decode("ascii")

    endpoints = {}
    try:
        client_host, client_port = clients.serve(args.host, args.port)
    except Exception as exc:
        if args.for_server is None:
            raise
        endpoints = {"error": "Can't listen for client connections: " + str(exc)}
    else:
        endpoints["client"] = {"host": client_host, "port": client_port}

    if args.for_server is not None:
        try:
            server_host, server_port = servers.serve()
        except Exception as exc:
            endpoints = {"error": "Can't listen for server connections: " + str(exc)}
        else:
            endpoints["server"] = {"host": server_host, "port": server_port}

        log.info(
            "Sending endpoints info to debug server at localhost:{0}:\n{1}",
            args.for_server,
            json.repr(endpoints),
        )

        try:
            sock = sockets.create_client()
            try:
                sock.settimeout(None)
                sock.connect(("127.0.0.1", args.for_server))
                sock_io = sock.makefile("wb", 0)
                try:
                    sock_io.write(json.dumps(endpoints).encode("utf-8"))
                finally:
                    sock_io.close()
            finally:
                sockets.close_socket(sock)
        except Exception:
            log.reraise_exception("Error sending endpoints info to debug server:")

        if "error" in endpoints:
            log.error("Couldn't set up endpoints; exiting.")
            sys.exit(1)

    listener_file = os.getenv("DEBUGPY_ADAPTER_ENDPOINTS")
    if listener_file is not None:
        log.info(
            "Writing endpoints info to {0!r}:\n{1}", listener_file, json.repr(endpoints)
        )

        def delete_listener_file():
            log.info("Listener ports closed; deleting {0!r}", listener_file)
            try:
                os.remove(listener_file)
            except Exception:
                log.swallow_exception(
                    "Failed to delete {0!r}", listener_file, level="warning"
                )

        try:
            with open(listener_file, "w") as f:
                atexit.register(delete_listener_file)
                print(json.dumps(endpoints), file=f)
        except Exception:
            log.reraise_exception("Error writing endpoints info to file:")

    if args.port is None:
        clients.Client("stdio")

    # These must be registered after the one above, to ensure that the listener sockets
    # are closed before the endpoint info file is deleted - this way, another process
    # can wait for the file to go away as a signal that the ports are no longer in use.
    atexit.register(servers.stop_serving)
    atexit.register(clients.stop_serving)

    servers.wait_until_disconnected()
    log.info("All debug servers disconnected; waiting for remaining sessions...")

    sessions.wait_until_ended()
    log.info("All debug sessions have ended; exiting.")


def _parse_argv(argv):
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--for-server", type=int, metavar="PORT", help=argparse.SUPPRESS
    )

    parser.add_argument(
        "--port",
        type=int,
        default=None,
        metavar="PORT",
        help="start the adapter in debugServer mode on the specified port",
    )

    parser.add_argument(
        "--host",
        type=str,
        default="127.0.0.1",
        metavar="HOST",
        help="start the adapter in debugServer mode on the specified host",
    )

    parser.add_argument(
        "--access-token", type=str, help="access token expected from the server"
    )

    parser.add_argument(
        "--server-access-token", type=str, help="access token expected by the server"
    )

    parser.add_argument(
        "--log-dir",
        type=str,
        metavar="DIR",
        help="enable logging and use DIR to save adapter logs",
    )

    parser.add_argument(
        "--log-stderr", action="store_true", help="enable logging to stderr"
    )

    args = parser.parse_args(argv[1:])

    if args.port is None:
        if args.log_stderr:
            parser.error("--log-stderr requires --port")
        if args.for_server is not None:
            parser.error("--for-server requires --port")

    return args


if __name__ == "__main__":
    # debugpy can also be invoked directly rather than via -m. In this case, the first
    # entry on sys.path is the one added automatically by Python for the directory
    # containing this file. This means that import debugpy will not work, since we need
    # the parent directory of debugpy/ to be in sys.path, rather than debugpy/adapter/.
    #
    # The other issue is that many other absolute imports will break, because they
    # will be resolved relative to debugpy/adapter/ - e.g. `import state` will then try
    # to import debugpy/adapter/state.py.
    #
    # To fix both, we need to replace the automatically added entry such that it points
    # at parent directory of debugpy/ instead of debugpy/adapter, import debugpy with that
    # in sys.path, and then remove the first entry entry altogether, so that it doesn't
    # affect any further imports we might do. For example, suppose the user did:
    #
    #   python /foo/bar/debugpy/adapter ...
    #
    # At the beginning of this script, sys.path will contain "/foo/bar/debugpy/adapter"
    # as the first entry. What we want is to replace it with "/foo/bar', then import
    # debugpy with that in effect, and then remove the replaced entry before any more
    # code runs. The imported debugpy module will remain in sys.modules, and thus all
    # future imports of it or its submodules will resolve accordingly.
    if "debugpy" not in sys.modules:
        # Do not use dirname() to walk up - this can be a relative path, e.g. ".".
        if os.name == "nt":
            import pathlib

            windows_path = pathlib.Path(sys.path[0])
            sys.path[0] = str(windows_path.parent.parent)
        else:
            sys.path[0] = sys.path[0] + "/../../"
        __import__("debugpy")
        del sys.path[0]

    # Apply OS-global and user-specific locale settings.
    try:
        locale.setlocale(locale.LC_ALL, "")
    except Exception:
        # On POSIX, locale is set via environment variables, and this can fail if
        # those variables reference a non-existing locale. Ignore and continue using
        # the default "C" locale if so.
        pass

    main()

# === NexusCore/openenv\Lib\site-packages\fontTools\ttLib\tables\G__l_a_t.py ===
from fontTools.misc import sstruct
from fontTools.misc.fixedTools import floatToFixedToStr
from fontTools.misc.textTools import safeEval

# from itertools import *
from functools import partial
from . import DefaultTable
from . import grUtils
import struct


Glat_format_0 = """
    >        # big endian
    version: 16.16F
"""

Glat_format_3 = """
    >
    version: 16.16F
    compression:L    # compression scheme or reserved 
"""

Glat_format_1_entry = """
    >
    attNum:     B    # Attribute number of first attribute
    num:        B    # Number of attributes in this run
"""
Glat_format_23_entry = """
    >
    attNum:     H    # Attribute number of first attribute
    num:        H    # Number of attributes in this run
"""

Glat_format_3_octabox_metrics = """
    >
    subboxBitmap:   H    # Which subboxes exist on 4x4 grid
    diagNegMin:     B    # Defines minimum negatively-sloped diagonal (si)
    diagNegMax:     B    # Defines maximum negatively-sloped diagonal (sa)
    diagPosMin:     B    # Defines minimum positively-sloped diagonal (di)
    diagPosMax:     B    # Defines maximum positively-sloped diagonal (da)
"""

Glat_format_3_subbox_entry = """
    >
    left:           B    # xi
    right:          B    # xa
    bottom:         B    # yi
    top:            B    # ya
    diagNegMin:     B    # Defines minimum negatively-sloped diagonal (si)
    diagNegMax:     B    # Defines maximum negatively-sloped diagonal (sa)
    diagPosMin:     B    # Defines minimum positively-sloped diagonal (di)
    diagPosMax:     B    # Defines maximum positively-sloped diagonal (da)
"""


class _Object:
    pass


class _Dict(dict):
    pass


class table_G__l_a_t(DefaultTable.DefaultTable):
    """Graphite Glyph Attributes table

    See also https://graphite.sil.org/graphite_techAbout#graphite-font-tables
    """

    def __init__(self, tag=None):
        DefaultTable.DefaultTable.__init__(self, tag)
        self.scheme = 0

    def decompile(self, data, ttFont):
        sstruct.unpack2(Glat_format_0, data, self)
        self.version = float(floatToFixedToStr(self.version, precisionBits=16))
        if self.version <= 1.9:
            decoder = partial(self.decompileAttributes12, fmt=Glat_format_1_entry)
        elif self.version <= 2.9:
            decoder = partial(self.decompileAttributes12, fmt=Glat_format_23_entry)
        elif self.version >= 3.0:
            (data, self.scheme) = grUtils.decompress(data)
            sstruct.unpack2(Glat_format_3, data, self)
            self.hasOctaboxes = (self.compression & 1) == 1
            decoder = self.decompileAttributes3

        gloc = ttFont["Gloc"]
        self.attributes = {}
        count = 0
        for s, e in zip(gloc, gloc[1:]):
            self.attributes[ttFont.getGlyphName(count)] = decoder(data[s:e])
            count += 1

    def decompileAttributes12(self, data, fmt):
        attributes = _Dict()
        while len(data) > 3:
            e, data = sstruct.unpack2(fmt, data, _Object())
            keys = range(e.attNum, e.attNum + e.num)
            if len(data) >= 2 * e.num:
                vals = struct.unpack_from((">%dh" % e.num), data)
                attributes.update(zip(keys, vals))
                data = data[2 * e.num :]
        return attributes

    def decompileAttributes3(self, data):
        if self.hasOctaboxes:
            o, data = sstruct.unpack2(Glat_format_3_octabox_metrics, data, _Object())
            numsub = bin(o.subboxBitmap).count("1")
            o.subboxes = []
            for b in range(numsub):
                if len(data) >= 8:
                    subbox, data = sstruct.unpack2(
                        Glat_format_3_subbox_entry, data, _Object()
                    )
                    o.subboxes.append(subbox)
        attrs = self.decompileAttributes12(data, Glat_format_23_entry)
        if self.hasOctaboxes:
            attrs.octabox = o
        return attrs

    def compile(self, ttFont):
        data = sstruct.pack(Glat_format_0, self)
        if self.version <= 1.9:
            encoder = partial(self.compileAttributes12, fmt=Glat_format_1_entry)
        elif self.version <= 2.9:
            encoder = partial(self.compileAttributes12, fmt=Glat_format_1_entry)
        elif self.version >= 3.0:
            self.compression = (self.scheme << 27) + (1 if self.hasOctaboxes else 0)
            data = sstruct.pack(Glat_format_3, self)
            encoder = self.compileAttributes3

        glocs = []
        for n in range(len(self.attributes)):
            glocs.append(len(data))
            data += encoder(self.attributes[ttFont.getGlyphName(n)])
        glocs.append(len(data))
        ttFont["Gloc"].set(glocs)

        if self.version >= 3.0:
            data = grUtils.compress(self.scheme, data)
        return data

    def compileAttributes12(self, attrs, fmt):
        data = b""
        for e in grUtils.entries(attrs):
            data += sstruct.pack(fmt, {"attNum": e[0], "num": e[1]}) + struct.pack(
                (">%dh" % len(e[2])), *e[2]
            )
        return data

    def compileAttributes3(self, attrs):
        if self.hasOctaboxes:
            o = attrs.octabox
            data = sstruct.pack(Glat_format_3_octabox_metrics, o)
            numsub = bin(o.subboxBitmap).count("1")
            for b in range(numsub):
                data += sstruct.pack(Glat_format_3_subbox_entry, o.subboxes[b])
        else:
            data = ""
        return data + self.compileAttributes12(attrs, Glat_format_23_entry)

    def toXML(self, writer, ttFont):
        writer.simpletag("version", version=self.version, compressionScheme=self.scheme)
        writer.newline()
        for n, a in sorted(
            self.attributes.items(), key=lambda x: ttFont.getGlyphID(x[0])
        ):
            writer.begintag("glyph", name=n)
            writer.newline()
            if hasattr(a, "octabox"):
                o = a.octabox
                formatstring, names, fixes = sstruct.getformat(
                    Glat_format_3_octabox_metrics
                )
                vals = {}
                for k in names:
                    if k == "subboxBitmap":
                        continue
                    vals[k] = "{:.3f}%".format(getattr(o, k) * 100.0 / 255)
                vals["bitmap"] = "{:0X}".format(o.subboxBitmap)
                writer.begintag("octaboxes", **vals)
                writer.newline()
                formatstring, names, fixes = sstruct.getformat(
                    Glat_format_3_subbox_entry
                )
                for s in o.subboxes:
                    vals = {}
                    for k in names:
                        vals[k] = "{:.3f}%".format(getattr(s, k) * 100.0 / 255)
                    writer.simpletag("octabox", **vals)
                    writer.newline()
                writer.endtag("octaboxes")
                writer.newline()
            for k, v in sorted(a.items()):
                writer.simpletag("attribute", index=k, value=v)
                writer.newline()
            writer.endtag("glyph")
            writer.newline()

    def fromXML(self, name, attrs, content, ttFont):
        if name == "version":
            self.version = float(safeEval(attrs["version"]))
            self.scheme = int(safeEval(attrs["compressionScheme"]))
        if name != "glyph":
            return
        if not hasattr(self, "attributes"):
            self.attributes = {}
        gname = attrs["name"]
        attributes = _Dict()
        for element in content:
            if not isinstance(element, tuple):
                continue
            tag, attrs, subcontent = element
            if tag == "attribute":
                k = int(safeEval(attrs["index"]))
                v = int(safeEval(attrs["value"]))
                attributes[k] = v
            elif tag == "octaboxes":
                self.hasOctaboxes = True
                o = _Object()
                o.subboxBitmap = int(attrs["bitmap"], 16)
                o.subboxes = []
                del attrs["bitmap"]
                for k, v in attrs.items():
                    setattr(o, k, int(float(v[:-1]) * 255.0 / 100.0 + 0.5))
                for element in subcontent:
                    if not isinstance(element, tuple):
                        continue
                    (tag, attrs, subcontent) = element
                    so = _Object()
                    for k, v in attrs.items():
                        setattr(so, k, int(float(v[:-1]) * 255.0 / 100.0 + 0.5))
                    o.subboxes.append(so)
                attributes.octabox = o
        self.attributes[gname] = attributes

# === NexusCore/openenv\Lib\site-packages\nltk\lm\__init__.py ===
# Natural Language Toolkit: Language Models
#
# Copyright (C) 2001-2024 NLTK Project
# Authors: Ilia Kurenkov <ilia.kurenkov@gmail.com>
# URL: <https://www.nltk.org/
# For license information, see LICENSE.TXT
"""
NLTK Language Modeling Module.
------------------------------

Currently this module covers only ngram language models, but it should be easy
to extend to neural models.


Preparing Data
==============

Before we train our ngram models it is necessary to make sure the data we put in
them is in the right format.
Let's say we have a text that is a list of sentences, where each sentence is
a list of strings. For simplicity we just consider a text consisting of
characters instead of words.

    >>> text = [['a', 'b', 'c'], ['a', 'c', 'd', 'c', 'e', 'f']]

If we want to train a bigram model, we need to turn this text into bigrams.
Here's what the first sentence of our text would look like if we use a function
from NLTK for this.

    >>> from nltk.util import bigrams
    >>> list(bigrams(text[0]))
    [('a', 'b'), ('b', 'c')]

Notice how "b" occurs both as the first and second member of different bigrams
but "a" and "c" don't? Wouldn't it be nice to somehow indicate how often sentences
start with "a" and end with "c"?
A standard way to deal with this is to add special "padding" symbols to the
sentence before splitting it into ngrams.
Fortunately, NLTK also has a function for that, let's see what it does to the
first sentence.

    >>> from nltk.util import pad_sequence
    >>> list(pad_sequence(text[0],
    ... pad_left=True,
    ... left_pad_symbol="<s>",
    ... pad_right=True,
    ... right_pad_symbol="</s>",
    ... n=2))
    ['<s>', 'a', 'b', 'c', '</s>']

Note the `n` argument, that tells the function we need padding for bigrams.
Now, passing all these parameters every time is tedious and in most cases they
can be safely assumed as defaults anyway.
Thus our module provides a convenience function that has all these arguments
already set while the other arguments remain the same as for `pad_sequence`.

    >>> from nltk.lm.preprocessing import pad_both_ends
    >>> list(pad_both_ends(text[0], n=2))
    ['<s>', 'a', 'b', 'c', '</s>']

Combining the two parts discussed so far we get the following preparation steps
for one sentence.

    >>> list(bigrams(pad_both_ends(text[0], n=2)))
    [('<s>', 'a'), ('a', 'b'), ('b', 'c'), ('c', '</s>')]

To make our model more robust we could also train it on unigrams (single words)
as well as bigrams, its main source of information.
NLTK once again helpfully provides a function called `everygrams`.
While not the most efficient, it is conceptually simple.


    >>> from nltk.util import everygrams
    >>> padded_bigrams = list(pad_both_ends(text[0], n=2))
    >>> list(everygrams(padded_bigrams, max_len=2))
    [('<s>',), ('<s>', 'a'), ('a',), ('a', 'b'), ('b',), ('b', 'c'), ('c',), ('c', '</s>'), ('</s>',)]

We are almost ready to start counting ngrams, just one more step left.
During training and evaluation our model will rely on a vocabulary that
defines which words are "known" to the model.
To create this vocabulary we need to pad our sentences (just like for counting
ngrams) and then combine the sentences into one flat stream of words.

    >>> from nltk.lm.preprocessing import flatten
    >>> list(flatten(pad_both_ends(sent, n=2) for sent in text))
    ['<s>', 'a', 'b', 'c', '</s>', '<s>', 'a', 'c', 'd', 'c', 'e', 'f', '</s>']

In most cases we want to use the same text as the source for both vocabulary
and ngram counts.
Now that we understand what this means for our preprocessing, we can simply import
a function that does everything for us.

    >>> from nltk.lm.preprocessing import padded_everygram_pipeline
    >>> train, vocab = padded_everygram_pipeline(2, text)

So as to avoid re-creating the text in memory, both `train` and `vocab` are lazy
iterators. They are evaluated on demand at training time.


Training
========
Having prepared our data we are ready to start training a model.
As a simple example, let us train a Maximum Likelihood Estimator (MLE).
We only need to specify the highest ngram order to instantiate it.

    >>> from nltk.lm import MLE
    >>> lm = MLE(2)

This automatically creates an empty vocabulary...

    >>> len(lm.vocab)
    0

... which gets filled as we fit the model.

    >>> lm.fit(train, vocab)
    >>> print(lm.vocab)
    <Vocabulary with cutoff=1 unk_label='<UNK>' and 9 items>
    >>> len(lm.vocab)
    9

The vocabulary helps us handle words that have not occurred during training.

    >>> lm.vocab.lookup(text[0])
    ('a', 'b', 'c')
    >>> lm.vocab.lookup(["aliens", "from", "Mars"])
    ('<UNK>', '<UNK>', '<UNK>')

Moreover, in some cases we want to ignore words that we did see during training
but that didn't occur frequently enough, to provide us useful information.
You can tell the vocabulary to ignore such words.
To find out how that works, check out the docs for the `Vocabulary` class.


Using a Trained Model
=====================
When it comes to ngram models the training boils down to counting up the ngrams
from the training corpus.

    >>> print(lm.counts)
    <NgramCounter with 2 ngram orders and 24 ngrams>

This provides a convenient interface to access counts for unigrams...

    >>> lm.counts['a']
    2

...and bigrams (in this case "a b")

    >>> lm.counts[['a']]['b']
    1

And so on. However, the real purpose of training a language model is to have it
score how probable words are in certain contexts.
This being MLE, the model returns the item's relative frequency as its score.

    >>> lm.score("a")
    0.15384615384615385

Items that are not seen during training are mapped to the vocabulary's
"unknown label" token. This is "<UNK>" by default.

    >>> lm.score("<UNK>") == lm.score("aliens")
    True

Here's how you get the score for a word given some preceding context.
For example we want to know what is the chance that "b" is preceded by "a".

    >>> lm.score("b", ["a"])
    0.5

To avoid underflow when working with many small score values it makes sense to
take their logarithm.
For convenience this can be done with the `logscore` method.

    >>> lm.logscore("a")
    -2.700439718141092

Building on this method, we can also evaluate our model's cross-entropy and
perplexity with respect to sequences of ngrams.

    >>> test = [('a', 'b'), ('c', 'd')]
    >>> lm.entropy(test)
    1.292481250360578
    >>> lm.perplexity(test)
    2.449489742783178

It is advisable to preprocess your test text exactly the same way as you did
the training text.

One cool feature of ngram models is that they can be used to generate text.

    >>> lm.generate(1, random_seed=3)
    '<s>'
    >>> lm.generate(5, random_seed=3)
    ['<s>', 'a', 'b', 'c', 'd']

Provide `random_seed` if you want to consistently reproduce the same text all
other things being equal. Here we are using it to test the examples.

You can also condition your generation on some preceding text with the `context`
argument.

    >>> lm.generate(5, text_seed=['c'], random_seed=3)
    ['</s>', 'c', 'd', 'c', 'd']

Note that an ngram model is restricted in how much preceding context it can
take into account. For example, a trigram model can only condition its output
on 2 preceding words. If you pass in a 4-word context, the first two words
will be ignored.
"""

from nltk.lm.counter import NgramCounter
from nltk.lm.models import (
    MLE,
    AbsoluteDiscountingInterpolated,
    KneserNeyInterpolated,
    Laplace,
    Lidstone,
    StupidBackoff,
    WittenBellInterpolated,
)
from nltk.lm.vocabulary import Vocabulary

__all__ = [
    "Vocabulary",
    "NgramCounter",
    "MLE",
    "Lidstone",
    "Laplace",
    "WittenBellInterpolated",
    "KneserNeyInterpolated",
    "AbsoluteDiscountingInterpolated",
    "StupidBackoff",
]

# === NexusCore/openenv\Lib\site-packages\numpy\fft\_helper.py ===
"""
Discrete Fourier Transforms - _helper.py

"""
from numpy._core import arange, asarray, empty, integer, roll
from numpy._core.overrides import array_function_dispatch, set_module

# Created by Pearu Peterson, September 2002

__all__ = ['fftshift', 'ifftshift', 'fftfreq', 'rfftfreq']

integer_types = (int, integer)


def _fftshift_dispatcher(x, axes=None):
    return (x,)


@array_function_dispatch(_fftshift_dispatcher, module='numpy.fft')
def fftshift(x, axes=None):
    """
    Shift the zero-frequency component to the center of the spectrum.

    This function swaps half-spaces for all axes listed (defaults to all).
    Note that ``y[0]`` is the Nyquist component only if ``len(x)`` is even.

    Parameters
    ----------
    x : array_like
        Input array.
    axes : int or shape tuple, optional
        Axes over which to shift.  Default is None, which shifts all axes.

    Returns
    -------
    y : ndarray
        The shifted array.

    See Also
    --------
    ifftshift : The inverse of `fftshift`.

    Examples
    --------
    >>> import numpy as np
    >>> freqs = np.fft.fftfreq(10, 0.1)
    >>> freqs
    array([ 0.,  1.,  2., ..., -3., -2., -1.])
    >>> np.fft.fftshift(freqs)
    array([-5., -4., -3., -2., -1.,  0.,  1.,  2.,  3.,  4.])

    Shift the zero-frequency component only along the second axis:

    >>> freqs = np.fft.fftfreq(9, d=1./9).reshape(3, 3)
    >>> freqs
    array([[ 0.,  1.,  2.],
           [ 3.,  4., -4.],
           [-3., -2., -1.]])
    >>> np.fft.fftshift(freqs, axes=(1,))
    array([[ 2.,  0.,  1.],
           [-4.,  3.,  4.],
           [-1., -3., -2.]])

    """
    x = asarray(x)
    if axes is None:
        axes = tuple(range(x.ndim))
        shift = [dim // 2 for dim in x.shape]
    elif isinstance(axes, integer_types):
        shift = x.shape[axes] // 2
    else:
        shift = [x.shape[ax] // 2 for ax in axes]

    return roll(x, shift, axes)


@array_function_dispatch(_fftshift_dispatcher, module='numpy.fft')
def ifftshift(x, axes=None):
    """
    The inverse of `fftshift`. Although identical for even-length `x`, the
    functions differ by one sample for odd-length `x`.

    Parameters
    ----------
    x : array_like
        Input array.
    axes : int or shape tuple, optional
        Axes over which to calculate.  Defaults to None, which shifts all axes.

    Returns
    -------
    y : ndarray
        The shifted array.

    See Also
    --------
    fftshift : Shift zero-frequency component to the center of the spectrum.

    Examples
    --------
    >>> import numpy as np
    >>> freqs = np.fft.fftfreq(9, d=1./9).reshape(3, 3)
    >>> freqs
    array([[ 0.,  1.,  2.],
           [ 3.,  4., -4.],
           [-3., -2., -1.]])
    >>> np.fft.ifftshift(np.fft.fftshift(freqs))
    array([[ 0.,  1.,  2.],
           [ 3.,  4., -4.],
           [-3., -2., -1.]])

    """
    x = asarray(x)
    if axes is None:
        axes = tuple(range(x.ndim))
        shift = [-(dim // 2) for dim in x.shape]
    elif isinstance(axes, integer_types):
        shift = -(x.shape[axes] // 2)
    else:
        shift = [-(x.shape[ax] // 2) for ax in axes]

    return roll(x, shift, axes)


@set_module('numpy.fft')
def fftfreq(n, d=1.0, device=None):
    """
    Return the Discrete Fourier Transform sample frequencies.

    The returned float array `f` contains the frequency bin centers in cycles
    per unit of the sample spacing (with zero at the start).  For instance, if
    the sample spacing is in seconds, then the frequency unit is cycles/second.

    Given a window length `n` and a sample spacing `d`::

      f = [0, 1, ...,   n/2-1,     -n/2, ..., -1] / (d*n)   if n is even
      f = [0, 1, ..., (n-1)/2, -(n-1)/2, ..., -1] / (d*n)   if n is odd

    Parameters
    ----------
    n : int
        Window length.
    d : scalar, optional
        Sample spacing (inverse of the sampling rate). Defaults to 1.
    device : str, optional
        The device on which to place the created array. Default: ``None``.
        For Array-API interoperability only, so must be ``"cpu"`` if passed.

        .. versionadded:: 2.0.0

    Returns
    -------
    f : ndarray
        Array of length `n` containing the sample frequencies.

    Examples
    --------
    >>> import numpy as np
    >>> signal = np.array([-2, 8, 6, 4, 1, 0, 3, 5], dtype=float)
    >>> fourier = np.fft.fft(signal)
    >>> n = signal.size
    >>> timestep = 0.1
    >>> freq = np.fft.fftfreq(n, d=timestep)
    >>> freq
    array([ 0.  ,  1.25,  2.5 , ..., -3.75, -2.5 , -1.25])

    """
    if not isinstance(n, integer_types):
        raise ValueError("n should be an integer")
    val = 1.0 / (n * d)
    results = empty(n, int, device=device)
    N = (n - 1) // 2 + 1
    p1 = arange(0, N, dtype=int, device=device)
    results[:N] = p1
    p2 = arange(-(n // 2), 0, dtype=int, device=device)
    results[N:] = p2
    return results * val


@set_module('numpy.fft')
def rfftfreq(n, d=1.0, device=None):
    """
    Return the Discrete Fourier Transform sample frequencies
    (for usage with rfft, irfft).

    The returned float array `f` contains the frequency bin centers in cycles
    per unit of the sample spacing (with zero at the start).  For instance, if
    the sample spacing is in seconds, then the frequency unit is cycles/second.

    Given a window length `n` and a sample spacing `d`::

      f = [0, 1, ...,     n/2-1,     n/2] / (d*n)   if n is even
      f = [0, 1, ..., (n-1)/2-1, (n-1)/2] / (d*n)   if n is odd

    Unlike `fftfreq` (but like `scipy.fftpack.rfftfreq`)
    the Nyquist frequency component is considered to be positive.

    Parameters
    ----------
    n : int
        Window length.
    d : scalar, optional
        Sample spacing (inverse of the sampling rate). Defaults to 1.
    device : str, optional
        The device on which to place the created array. Default: ``None``.
        For Array-API interoperability only, so must be ``"cpu"`` if passed.

        .. versionadded:: 2.0.0

    Returns
    -------
    f : ndarray
        Array of length ``n//2 + 1`` containing the sample frequencies.

    Examples
    --------
    >>> import numpy as np
    >>> signal = np.array([-2, 8, 6, 4, 1, 0, 3, 5, -3, 4], dtype=float)
    >>> fourier = np.fft.rfft(signal)
    >>> n = signal.size
    >>> sample_rate = 100
    >>> freq = np.fft.fftfreq(n, d=1./sample_rate)
    >>> freq
    array([  0.,  10.,  20., ..., -30., -20., -10.])
    >>> freq = np.fft.rfftfreq(n, d=1./sample_rate)
    >>> freq
    array([  0.,  10.,  20.,  30.,  40.,  50.])

    """
    if not isinstance(n, integer_types):
        raise ValueError("n should be an integer")
    val = 1.0 / (n * d)
    N = n // 2 + 1
    results = arange(0, N, dtype=int, device=device)
    return results * val

# === NexusCore/openenv\Lib\site-packages\pythonwin\pywin\framework\editor\ModuleBrowser.py ===
# ModuleBrowser.py - A view that provides a module browser for an editor document.
import pyclbr

import commctrl
import pywin.framework.scriptutils
import pywin.mfc.docview
import win32api
import win32con
import win32ui
from pywin.mfc import afxres
from pywin.tools import hierlist


class HierListCLBRModule(hierlist.HierListItem):
    def __init__(self, modName, clbrdata):
        self.modName = modName
        self.clbrdata = clbrdata

    def GetText(self):
        return self.modName

    def GetSubList(self):
        ret = []
        for item in self.clbrdata.values():
            if (
                item.__class__ != pyclbr.Class
            ):  # ie, it is a pyclbr Function instance (only introduced post 1.5.2)
                ret.append(HierListCLBRFunction(item))
            else:
                ret.append(HierListCLBRClass(item))
        ret.sort()
        return ret

    def IsExpandable(self):
        return 1


class HierListCLBRItem(hierlist.HierListItem):
    def __init__(self, name, file, lineno, suffix=""):
        self.name = str(name)
        self.file = file
        self.lineno = lineno
        self.suffix = suffix

    def __lt__(self, other):
        return self.name < other.name

    def __eq__(self, other):
        return self.name == other.name

    def GetText(self):
        return self.name + self.suffix

    def TakeDefaultAction(self):
        if self.file:
            pywin.framework.scriptutils.JumpToDocument(
                self.file, self.lineno, bScrollToTop=1
            )
        else:
            win32ui.SetStatusText("Can not locate the source code for this object.")

    def PerformItemSelected(self):
        if self.file is None:
            msg = f"{self.name} - source can not be located."
        else:
            msg = "%s defined at line %d of %s" % (self.name, self.lineno, self.file)
        win32ui.SetStatusText(msg)


class HierListCLBRClass(HierListCLBRItem):
    def __init__(self, clbrclass, suffix=""):
        try:
            name = clbrclass.name
            file = clbrclass.file
            lineno = clbrclass.lineno
            self.super = clbrclass.super
            self.methods = clbrclass.methods
        except AttributeError:
            name = clbrclass
            file = lineno = None
            self.super = []
            self.methods = {}
        HierListCLBRItem.__init__(self, name, file, lineno, suffix)

    def GetSubList(self):
        r1 = []
        for c in self.super:
            r1.append(HierListCLBRClass(c, " (Parent class)"))
        r1.sort()
        r2 = []
        for meth, lineno in self.methods.items():
            r2.append(HierListCLBRMethod(meth, self.file, lineno))
        r2.sort()
        return r1 + r2

    def IsExpandable(self):
        return len(self.methods) + len(self.super)

    def GetBitmapColumn(self):
        return 21


class HierListCLBRFunction(HierListCLBRItem):
    def __init__(self, clbrfunc, suffix=""):
        name = clbrfunc.name
        file = clbrfunc.file
        lineno = clbrfunc.lineno
        HierListCLBRItem.__init__(self, name, file, lineno, suffix)

    def GetBitmapColumn(self):
        return 22


class HierListCLBRMethod(HierListCLBRItem):
    def GetBitmapColumn(self):
        return 22


class HierListCLBRErrorItem(hierlist.HierListItem):
    def __init__(self, text):
        self.text = text

    def GetText(self):
        return self.text

    def GetSubList(self):
        return [HierListCLBRErrorItem(self.text)]

    def IsExpandable(self):
        return 0


class HierListCLBRErrorRoot(HierListCLBRErrorItem):
    def IsExpandable(self):
        return 1


class BrowserView(pywin.mfc.docview.TreeView):
    def OnInitialUpdate(self):
        self.list = None
        rc = self._obj_.OnInitialUpdate()
        self.HookMessage(self.OnSize, win32con.WM_SIZE)
        self.bDirty = 0
        self.destroying = 0
        return rc

    def DestroyBrowser(self):
        self.DestroyList()

    def OnActivateView(self, activate, av, dv):
        # print("AV", self.bDirty, activate)
        if activate:
            self.CheckRefreshList()
        return self._obj_.OnActivateView(activate, av, dv)

    def _MakeRoot(self):
        path = self.GetDocument().GetPathName()
        if not path:
            return HierListCLBRErrorRoot(
                "Error: Can not browse a file until it is saved"
            )
        else:
            mod, path = pywin.framework.scriptutils.GetPackageModuleName(path)
            if self.bDirty:
                what = "Refreshing"
                # Hack for pyclbr being too smart
                try:
                    del pyclbr._modules[mod]
                except (KeyError, AttributeError):
                    pass
            else:
                what = "Building"
            win32ui.SetStatusText(f"{what} class list - please wait...", 1)
            win32ui.DoWaitCursor(1)
            try:
                reader = pyclbr.readmodule_ex  # new version post 1.5.2
            except AttributeError:
                reader = pyclbr.readmodule
            try:
                data = reader(mod, [path])
                if data:
                    return HierListCLBRModule(mod, data)
                else:
                    return HierListCLBRErrorRoot("No Python classes in module.")

            finally:
                win32ui.DoWaitCursor(0)
                win32ui.SetStatusText(win32ui.LoadString(afxres.AFX_IDS_IDLEMESSAGE))

    def DestroyList(self):
        self.destroying = 1
        list = getattr(
            self, "list", None
        )  # If the document was not successfully opened, we may not have a list.
        self.list = None
        if list is not None:
            list.HierTerm()
        self.destroying = 0

    def CheckMadeList(self):
        if self.list is not None or self.destroying:
            return
        self.rootitem = root = self._MakeRoot()
        self.list = list = hierlist.HierListWithItems(root, win32ui.IDB_BROWSER_HIER)
        list.HierInit(self.GetParentFrame(), self)
        list.SetStyle(
            commctrl.TVS_HASLINES | commctrl.TVS_LINESATROOT | commctrl.TVS_HASBUTTONS
        )

    def CheckRefreshList(self):
        if self.bDirty:
            if self.list is None:
                self.CheckMadeList()
            else:
                new_root = self._MakeRoot()
                if self.rootitem.__class__ == new_root.__class__ == HierListCLBRModule:
                    self.rootitem.modName = new_root.modName
                    self.rootitem.clbrdata = new_root.clbrdata
                    self.list.Refresh()
                else:
                    self.list.AcceptRoot(self._MakeRoot())
            self.bDirty = 0

    def OnSize(self, params):
        lparam = params[3]
        w = win32api.LOWORD(lparam)
        h = win32api.HIWORD(lparam)
        if w != 0:
            self.CheckMadeList()
        elif w == 0:
            self.DestroyList()
        return 1

    def _UpdateUIForState(self):
        self.bDirty = 1

# === NexusCore/openenv\Lib\site-packages\setuptools\_vendor\typeguard\_decorators.py ===
from __future__ import annotations

import ast
import inspect
import sys
from collections.abc import Sequence
from functools import partial
from inspect import isclass, isfunction
from types import CodeType, FrameType, FunctionType
from typing import TYPE_CHECKING, Any, Callable, ForwardRef, TypeVar, cast, overload
from warnings import warn

from ._config import CollectionCheckStrategy, ForwardRefPolicy, global_config
from ._exceptions import InstrumentationWarning
from ._functions import TypeCheckFailCallback
from ._transformer import TypeguardTransformer
from ._utils import Unset, function_name, get_stacklevel, is_method_of, unset

if TYPE_CHECKING:
    from typeshed.stdlib.types import _Cell

    _F = TypeVar("_F")

    def typeguard_ignore(f: _F) -> _F:
        """This decorator is a noop during static type-checking."""
        return f

else:
    from typing import no_type_check as typeguard_ignore  # noqa: F401

T_CallableOrType = TypeVar("T_CallableOrType", bound=Callable[..., Any])


def make_cell(value: object) -> _Cell:
    return (lambda: value).__closure__[0]  # type: ignore[index]


def find_target_function(
    new_code: CodeType, target_path: Sequence[str], firstlineno: int
) -> CodeType | None:
    target_name = target_path[0]
    for const in new_code.co_consts:
        if isinstance(const, CodeType):
            if const.co_name == target_name:
                if const.co_firstlineno == firstlineno:
                    return const
                elif len(target_path) > 1:
                    target_code = find_target_function(
                        const, target_path[1:], firstlineno
                    )
                    if target_code:
                        return target_code

    return None


def instrument(f: T_CallableOrType) -> FunctionType | str:
    if not getattr(f, "__code__", None):
        return "no code associated"
    elif not getattr(f, "__module__", None):
        return "__module__ attribute is not set"
    elif f.__code__.co_filename == "<stdin>":
        return "cannot instrument functions defined in a REPL"
    elif hasattr(f, "__wrapped__"):
        return (
            "@typechecked only supports instrumenting functions wrapped with "
            "@classmethod, @staticmethod or @property"
        )

    target_path = [item for item in f.__qualname__.split(".") if item != "<locals>"]
    module_source = inspect.getsource(sys.modules[f.__module__])
    module_ast = ast.parse(module_source)
    instrumentor = TypeguardTransformer(target_path, f.__code__.co_firstlineno)
    instrumentor.visit(module_ast)

    if not instrumentor.target_node or instrumentor.target_lineno is None:
        return "instrumentor did not find the target function"

    module_code = compile(module_ast, f.__code__.co_filename, "exec", dont_inherit=True)
    new_code = find_target_function(
        module_code, target_path, instrumentor.target_lineno
    )
    if not new_code:
        return "cannot find the target function in the AST"

    if global_config.debug_instrumentation and sys.version_info >= (3, 9):
        # Find the matching AST node, then unparse it to source and print to stdout
        print(
            f"Source code of {f.__qualname__}() after instrumentation:"
            "\n----------------------------------------------",
            file=sys.stderr,
        )
        print(ast.unparse(instrumentor.target_node), file=sys.stderr)
        print(
            "----------------------------------------------",
            file=sys.stderr,
        )

    closure = f.__closure__
    if new_code.co_freevars != f.__code__.co_freevars:
        # Create a new closure and find values for the new free variables
        frame = cast(FrameType, inspect.currentframe())
        frame = cast(FrameType, frame.f_back)
        frame_locals = cast(FrameType, frame.f_back).f_locals
        cells: list[_Cell] = []
        for key in new_code.co_freevars:
            if key in instrumentor.names_used_in_annotations:
                # Find the value and make a new cell from it
                value = frame_locals.get(key) or ForwardRef(key)
                cells.append(make_cell(value))
            else:
                # Reuse the cell from the existing closure
                assert f.__closure__
                cells.append(f.__closure__[f.__code__.co_freevars.index(key)])

        closure = tuple(cells)

    new_function = FunctionType(new_code, f.__globals__, f.__name__, closure=closure)
    new_function.__module__ = f.__module__
    new_function.__name__ = f.__name__
    new_function.__qualname__ = f.__qualname__
    new_function.__annotations__ = f.__annotations__
    new_function.__doc__ = f.__doc__
    new_function.__defaults__ = f.__defaults__
    new_function.__kwdefaults__ = f.__kwdefaults__
    return new_function


@overload
def typechecked(
    *,
    forward_ref_policy: ForwardRefPolicy | Unset = unset,
    typecheck_fail_callback: TypeCheckFailCallback | Unset = unset,
    collection_check_strategy: CollectionCheckStrategy | Unset = unset,
    debug_instrumentation: bool | Unset = unset,
) -> Callable[[T_CallableOrType], T_CallableOrType]: ...


@overload
def typechecked(target: T_CallableOrType) -> T_CallableOrType: ...


def typechecked(
    target: T_CallableOrType | None = None,
    *,
    forward_ref_policy: ForwardRefPolicy | Unset = unset,
    typecheck_fail_callback: TypeCheckFailCallback | Unset = unset,
    collection_check_strategy: CollectionCheckStrategy | Unset = unset,
    debug_instrumentation: bool | Unset = unset,
) -> Any:
    """
    Instrument the target function to perform run-time type checking.

    This decorator recompiles the target function, injecting code to type check
    arguments, return values, yield values (excluding ``yield from``) and assignments to
    annotated local variables.

    This can also be used as a class decorator. This will instrument all type annotated
    methods, including :func:`@classmethod <classmethod>`,
    :func:`@staticmethod <staticmethod>`,  and :class:`@property <property>` decorated
    methods in the class.

    .. note:: When Python is run in optimized mode (``-O`` or ``-OO``, this decorator
        is a no-op). This is a feature meant for selectively introducing type checking
        into a code base where the checks aren't meant to be run in production.

    :param target: the function or class to enable type checking for
    :param forward_ref_policy: override for
        :attr:`.TypeCheckConfiguration.forward_ref_policy`
    :param typecheck_fail_callback: override for
        :attr:`.TypeCheckConfiguration.typecheck_fail_callback`
    :param collection_check_strategy: override for
        :attr:`.TypeCheckConfiguration.collection_check_strategy`
    :param debug_instrumentation: override for
        :attr:`.TypeCheckConfiguration.debug_instrumentation`

    """
    if target is None:
        return partial(
            typechecked,
            forward_ref_policy=forward_ref_policy,
            typecheck_fail_callback=typecheck_fail_callback,
            collection_check_strategy=collection_check_strategy,
            debug_instrumentation=debug_instrumentation,
        )

    if not __debug__:
        return target

    if isclass(target):
        for key, attr in target.__dict__.items():
            if is_method_of(attr, target):
                retval = instrument(attr)
                if isfunction(retval):
                    setattr(target, key, retval)
            elif isinstance(attr, (classmethod, staticmethod)):
                if is_method_of(attr.__func__, target):
                    retval = instrument(attr.__func__)
                    if isfunction(retval):
                        wrapper = attr.__class__(retval)
                        setattr(target, key, wrapper)
            elif isinstance(attr, property):
                kwargs: dict[str, Any] = dict(doc=attr.__doc__)
                for name in ("fset", "fget", "fdel"):
                    property_func = kwargs[name] = getattr(attr, name)
                    if is_method_of(property_func, target):
                        retval = instrument(property_func)
                        if isfunction(retval):
                            kwargs[name] = retval

                setattr(target, key, attr.__class__(**kwargs))

        return target

    # Find either the first Python wrapper or the actual function
    wrapper_class: (
        type[classmethod[Any, Any, Any]] | type[staticmethod[Any, Any]] | None
    ) = None
    if isinstance(target, (classmethod, staticmethod)):
        wrapper_class = target.__class__
        target = target.__func__

    retval = instrument(target)
    if isinstance(retval, str):
        warn(
            f"{retval} -- not typechecking {function_name(target)}",
            InstrumentationWarning,
            stacklevel=get_stacklevel(),
        )
        return target

    if wrapper_class is None:
        return retval
    else:
        return wrapper_class(retval)

# === NexusCore/openenv\Lib\site-packages\stack_data\formatting.py ===
import inspect
import sys
import traceback
from types import FrameType, TracebackType
from typing import Union, Iterable

from stack_data import (style_with_executing_node, Options, Line, FrameInfo, LINE_GAP,
                       Variable, RepeatedFrames, BlankLineRange, BlankLines)
from stack_data.utils import assert_


class Formatter:
    def __init__(
            self, *,
            options=None,
            pygmented=False,
            show_executing_node=True,
            pygments_formatter_cls=None,
            pygments_formatter_kwargs=None,
            pygments_style="monokai",
            executing_node_modifier="bg:#005080",
            executing_node_underline="^",
            current_line_indicator="-->",
            line_gap_string="(...)",
            line_number_gap_string=":",
            line_number_format_string="{:4} | ",
            show_variables=False,
            use_code_qualname=True,
            show_linenos=True,
            strip_leading_indent=True,
            html=False,
            chain=True,
            collapse_repeated_frames=True
    ):
        if options is None:
            options = Options()

        if pygmented and not options.pygments_formatter:
            if show_executing_node:
                pygments_style = style_with_executing_node(
                    pygments_style, executing_node_modifier
                )

            if pygments_formatter_cls is None:
                from pygments.formatters.terminal256 import Terminal256Formatter \
                    as pygments_formatter_cls

            options.pygments_formatter = pygments_formatter_cls(
                style=pygments_style,
                **pygments_formatter_kwargs or {},
            )

        self.pygmented = pygmented
        self.show_executing_node = show_executing_node
        assert_(
            len(executing_node_underline) == 1,
            ValueError("executing_node_underline must be a single character"),
        )
        self.executing_node_underline = executing_node_underline
        self.current_line_indicator = current_line_indicator or ""
        self.line_gap_string = line_gap_string
        self.line_number_gap_string = line_number_gap_string
        self.line_number_format_string = line_number_format_string
        self.show_variables = show_variables
        self.show_linenos = show_linenos
        self.use_code_qualname = use_code_qualname
        self.strip_leading_indent = strip_leading_indent
        self.html = html
        self.chain = chain
        self.options = options
        self.collapse_repeated_frames = collapse_repeated_frames
        if not self.show_linenos and self.options.blank_lines == BlankLines.SINGLE:
            raise ValueError(
                "BlankLines.SINGLE option can only be used when show_linenos=True"
            )

    def set_hook(self):
        def excepthook(_etype, evalue, _tb):
            self.print_exception(evalue)

        sys.excepthook = excepthook

    def print_exception(self, e=None, *, file=None):
        self.print_lines(self.format_exception(e), file=file)

    def print_stack(self, frame_or_tb=None, *, file=None):
        if frame_or_tb is None:
            frame_or_tb = inspect.currentframe().f_back

        self.print_lines(self.format_stack(frame_or_tb), file=file)

    def print_lines(self, lines, *, file=None):
        if file is None:
            file = sys.stderr
        for line in lines:
            print(line, file=file, end="")

    def format_exception(self, e=None) -> Iterable[str]:
        if e is None:
            e = sys.exc_info()[1]

        if self.chain:
            if e.__cause__ is not None:
                yield from self.format_exception(e.__cause__)
                yield traceback._cause_message
            elif (e.__context__ is not None
                  and not e.__suppress_context__):
                yield from self.format_exception(e.__context__)
                yield traceback._context_message

        yield 'Traceback (most recent call last):\n'
        yield from self.format_stack(e.__traceback__)
        yield from traceback.format_exception_only(type(e), e)

    def format_stack(self, frame_or_tb=None) -> Iterable[str]:
        if frame_or_tb is None:
            frame_or_tb = inspect.currentframe().f_back

        yield from self.format_stack_data(
            FrameInfo.stack_data(
                frame_or_tb,
                self.options,
                collapse_repeated_frames=self.collapse_repeated_frames,
            )
        )

    def format_stack_data(
            self, stack: Iterable[Union[FrameInfo, RepeatedFrames]]
    ) -> Iterable[str]:
        for item in stack:
            if isinstance(item, FrameInfo):
                yield from self.format_frame(item)
            else:
                yield self.format_repeated_frames(item)

    def format_repeated_frames(self, repeated_frames: RepeatedFrames) -> str:
        return '    [... skipping similar frames: {}]\n'.format(
            repeated_frames.description
        )

    def format_frame(self, frame: Union[FrameInfo, FrameType, TracebackType]) -> Iterable[str]:
        if not isinstance(frame, FrameInfo):
            frame = FrameInfo(frame, self.options)

        yield self.format_frame_header(frame)

        for line in frame.lines:
            if isinstance(line, Line):
                yield self.format_line(line)
            elif isinstance(line, BlankLineRange):
                yield self.format_blank_lines_linenumbers(line)
            else:
                assert_(line is LINE_GAP)
                yield self.line_gap_string + "\n"

        if self.show_variables:
            try:
                yield from self.format_variables(frame)
            except Exception:
                pass

    def format_frame_header(self, frame_info: FrameInfo) -> str:
        return ' File "{frame_info.filename}", line {frame_info.lineno}, in {name}\n'.format(
            frame_info=frame_info,
            name=(
                frame_info.executing.code_qualname()
                if self.use_code_qualname else
                frame_info.code.co_name
            ),
        )

    def format_line(self, line: Line) -> str:
        result = ""
        if self.current_line_indicator:
            if line.is_current:
                result = self.current_line_indicator
            else:
                result = " " * len(self.current_line_indicator)
            result += " "
        else:
            result = "   "

        if self.show_linenos:
            result += self.line_number_format_string.format(line.lineno)

        prefix = result

        result += line.render(
            pygmented=self.pygmented,
            escape_html=self.html,
            strip_leading_indent=self.strip_leading_indent,
        ) + "\n"

        if self.show_executing_node and not self.pygmented:
            for line_range in line.executing_node_ranges:
                start = line_range.start - line.leading_indent
                end = line_range.end - line.leading_indent
                # if end <= start, we have an empty line inside a highlighted
                # block of code. In this case, we need to avoid inserting
                # an extra blank line with no markers present.
                if end > start:
                    result += (
                            " " * (start + len(prefix))
                            + self.executing_node_underline * (end - start)
                            + "\n"
                    )
        return result


    def format_blank_lines_linenumbers(self, blank_line):
        if self.current_line_indicator:
            result = " " * len(self.current_line_indicator) + " "
        else:
            result = "   "
        if blank_line.begin_lineno == blank_line.end_lineno:
            return result + self.line_number_format_string.format(blank_line.begin_lineno) + "\n"
        return result + "   {}\n".format(self.line_number_gap_string)


    def format_variables(self, frame_info: FrameInfo) -> Iterable[str]:
        for var in sorted(frame_info.variables, key=lambda v: v.name):
            try:
                yield self.format_variable(var) + "\n"
            except Exception:
                pass

    def format_variable(self, var: Variable) -> str:
        return "{} = {}".format(
            var.name,
            self.format_variable_value(var.value),
        )

    def format_variable_value(self, value) -> str:
        return repr(value)

# === NexusCore/openenv\Lib\site-packages\litellm\integrations\gcs_bucket\gcs_bucket.py ===
import asyncio
import json
import os
import uuid
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING, Any, Dict, List, Optional
from urllib.parse import quote

from litellm._logging import verbose_logger
from litellm.integrations.additional_logging_utils import AdditionalLoggingUtils
from litellm.integrations.gcs_bucket.gcs_bucket_base import GCSBucketBase
from litellm.proxy._types import CommonProxyErrors
from litellm.types.integrations.base_health_check import IntegrationHealthCheckStatus
from litellm.types.integrations.gcs_bucket import *
from litellm.types.utils import StandardLoggingPayload

if TYPE_CHECKING:
    from litellm.llms.vertex_ai.vertex_llm_base import VertexBase
else:
    VertexBase = Any


class GCSBucketLogger(GCSBucketBase, AdditionalLoggingUtils):
    def __init__(self, bucket_name: Optional[str] = None) -> None:
        from litellm.proxy.proxy_server import premium_user

        super().__init__(bucket_name=bucket_name)

        # Init Batch logging settings
        self.log_queue: List[GCSLogQueueItem] = []
        self.batch_size = int(os.getenv("GCS_BATCH_SIZE", GCS_DEFAULT_BATCH_SIZE))
        self.flush_interval = int(
            os.getenv("GCS_FLUSH_INTERVAL", GCS_DEFAULT_FLUSH_INTERVAL_SECONDS)
        )
        asyncio.create_task(self.periodic_flush())
        self.flush_lock = asyncio.Lock()
        super().__init__(
            flush_lock=self.flush_lock,
            batch_size=self.batch_size,
            flush_interval=self.flush_interval,
        )
        AdditionalLoggingUtils.__init__(self)

        if premium_user is not True:
            raise ValueError(
                f"GCS Bucket logging is a premium feature. Please upgrade to use it. {CommonProxyErrors.not_premium_user.value}"
            )

    #### ASYNC ####
    async def async_log_success_event(self, kwargs, response_obj, start_time, end_time):
        from litellm.proxy.proxy_server import premium_user

        if premium_user is not True:
            raise ValueError(
                f"GCS Bucket logging is a premium feature. Please upgrade to use it. {CommonProxyErrors.not_premium_user.value}"
            )
        try:
            verbose_logger.debug(
                "GCS Logger: async_log_success_event logging kwargs: %s, response_obj: %s",
                kwargs,
                response_obj,
            )
            logging_payload: Optional[StandardLoggingPayload] = kwargs.get(
                "standard_logging_object", None
            )
            if logging_payload is None:
                raise ValueError("standard_logging_object not found in kwargs")
            # Add to logging queue - this will be flushed periodically
            self.log_queue.append(
                GCSLogQueueItem(
                    payload=logging_payload, kwargs=kwargs, response_obj=response_obj
                )
            )

        except Exception as e:
            verbose_logger.exception(f"GCS Bucket logging error: {str(e)}")

    async def async_log_failure_event(self, kwargs, response_obj, start_time, end_time):
        try:
            verbose_logger.debug(
                "GCS Logger: async_log_failure_event logging kwargs: %s, response_obj: %s",
                kwargs,
                response_obj,
            )

            logging_payload: Optional[StandardLoggingPayload] = kwargs.get(
                "standard_logging_object", None
            )
            if logging_payload is None:
                raise ValueError("standard_logging_object not found in kwargs")
            # Add to logging queue - this will be flushed periodically
            self.log_queue.append(
                GCSLogQueueItem(
                    payload=logging_payload, kwargs=kwargs, response_obj=response_obj
                )
            )

        except Exception as e:
            verbose_logger.exception(f"GCS Bucket logging error: {str(e)}")

    async def async_send_batch(self):
        """
        Process queued logs in batch - sends logs to GCS Bucket


        GCS Bucket does not have a Batch endpoint to batch upload logs

        Instead, we
            - collect the logs to flush every `GCS_FLUSH_INTERVAL` seconds
            - during async_send_batch, we make 1 POST request per log to GCS Bucket

        """
        if not self.log_queue:
            return

        for log_item in self.log_queue:
            logging_payload = log_item["payload"]
            kwargs = log_item["kwargs"]
            response_obj = log_item.get("response_obj", None) or {}

            gcs_logging_config: GCSLoggingConfig = await self.get_gcs_logging_config(
                kwargs
            )

            headers = await self.construct_request_headers(
                vertex_instance=gcs_logging_config["vertex_instance"],
                service_account_json=gcs_logging_config["path_service_account"],
            )
            bucket_name = gcs_logging_config["bucket_name"]
            object_name = self._get_object_name(kwargs, logging_payload, response_obj)

            try:
                await self._log_json_data_on_gcs(
                    headers=headers,
                    bucket_name=bucket_name,
                    object_name=object_name,
                    logging_payload=logging_payload,
                )
            except Exception as e:
                # don't let one log item fail the entire batch
                verbose_logger.exception(
                    f"GCS Bucket error logging payload to GCS bucket: {str(e)}"
                )
                pass

        # Clear the queue after processing
        self.log_queue.clear()

    def _get_object_name(
        self, kwargs: Dict, logging_payload: StandardLoggingPayload, response_obj: Any
    ) -> str:
        """
        Get the object name to use for the current payload
        """
        current_date = self._get_object_date_from_datetime(datetime.now(timezone.utc))
        if logging_payload.get("error_str", None) is not None:
            object_name = self._generate_failure_object_name(
                request_date_str=current_date,
            )
        else:
            object_name = self._generate_success_object_name(
                request_date_str=current_date,
                response_id=response_obj.get("id", ""),
            )

        # used for testing
        _litellm_params = kwargs.get("litellm_params", None) or {}
        _metadata = _litellm_params.get("metadata", None) or {}
        if "gcs_log_id" in _metadata:
            object_name = _metadata["gcs_log_id"]

        return object_name

    async def get_request_response_payload(
        self,
        request_id: str,
        start_time_utc: Optional[datetime],
        end_time_utc: Optional[datetime],
    ) -> Optional[dict]:
        """
        Get the request and response payload for a given `request_id`
        Tries current day, next day, and previous day until it finds the payload
        """
        if start_time_utc is None:
            raise ValueError(
                "start_time_utc is required for getting a payload from GCS Bucket"
            )

        # Try current day, next day, and previous day
        dates_to_try = [
            start_time_utc,
            start_time_utc + timedelta(days=1),
            start_time_utc - timedelta(days=1),
        ]
        date_str = None
        for date in dates_to_try:
            try:
                date_str = self._get_object_date_from_datetime(datetime_obj=date)
                object_name = self._generate_success_object_name(
                    request_date_str=date_str,
                    response_id=request_id,
                )
                encoded_object_name = quote(object_name, safe="")
                response = await self.download_gcs_object(encoded_object_name)

                if response is not None:
                    loaded_response = json.loads(response)
                    return loaded_response
            except Exception as e:
                verbose_logger.debug(
                    f"Failed to fetch payload for date {date_str}: {str(e)}"
                )
                continue

        return None

    def _generate_success_object_name(
        self,
        request_date_str: str,
        response_id: str,
    ) -> str:
        return f"{request_date_str}/{response_id}"

    def _generate_failure_object_name(
        self,
        request_date_str: str,
    ) -> str:
        return f"{request_date_str}/failure-{uuid.uuid4().hex}"

    def _get_object_date_from_datetime(self, datetime_obj: datetime) -> str:
        return datetime_obj.strftime("%Y-%m-%d")

    async def async_health_check(self) -> IntegrationHealthCheckStatus:
        raise NotImplementedError("GCS Bucket does not support health check")

# === NexusCore/openenv\Lib\site-packages\matplotlib\testing\__init__.py ===
"""
Helper functions for testing.
"""
from pathlib import Path
from tempfile import TemporaryDirectory
import locale
import logging
import os
import subprocess
import sys

import matplotlib as mpl
from matplotlib import _api

_log = logging.getLogger(__name__)


def set_font_settings_for_testing():
    mpl.rcParams['font.family'] = 'DejaVu Sans'
    mpl.rcParams['text.hinting'] = 'none'
    mpl.rcParams['text.hinting_factor'] = 8


def set_reproducibility_for_testing():
    mpl.rcParams['svg.hashsalt'] = 'matplotlib'


def setup():
    # The baseline images are created in this locale, so we should use
    # it during all of the tests.

    try:
        locale.setlocale(locale.LC_ALL, 'en_US.UTF-8')
    except locale.Error:
        try:
            locale.setlocale(locale.LC_ALL, 'English_United States.1252')
        except locale.Error:
            _log.warning(
                "Could not set locale to English/United States. "
                "Some date-related tests may fail.")

    mpl.use('Agg')

    with _api.suppress_matplotlib_deprecation_warning():
        mpl.rcdefaults()  # Start with all defaults

    # These settings *must* be hardcoded for running the comparison tests and
    # are not necessarily the default values as specified in rcsetup.py.
    set_font_settings_for_testing()
    set_reproducibility_for_testing()


def subprocess_run_for_testing(command, env=None, timeout=60, stdout=None,
                               stderr=None, check=False, text=True,
                               capture_output=False):
    """
    Create and run a subprocess.

    Thin wrapper around `subprocess.run`, intended for testing.  Will
    mark fork() failures on Cygwin as expected failures: not a
    success, but not indicating a problem with the code either.

    Parameters
    ----------
    args : list of str
    env : dict[str, str]
    timeout : float
    stdout, stderr
    check : bool
    text : bool
        Also called ``universal_newlines`` in subprocess.  I chose this
        name since the main effect is returning bytes (`False`) vs. str
        (`True`), though it also tries to normalize newlines across
        platforms.
    capture_output : bool
        Set stdout and stderr to subprocess.PIPE

    Returns
    -------
    proc : subprocess.Popen

    See Also
    --------
    subprocess.run

    Raises
    ------
    pytest.xfail
        If platform is Cygwin and subprocess reports a fork() failure.
    """
    if capture_output:
        stdout = stderr = subprocess.PIPE
    try:
        proc = subprocess.run(
            command, env=env,
            timeout=timeout, check=check,
            stdout=stdout, stderr=stderr,
            text=text
        )
    except BlockingIOError:
        if sys.platform == "cygwin":
            # Might want to make this more specific
            import pytest
            pytest.xfail("Fork failure")
        raise
    return proc


def subprocess_run_helper(func, *args, timeout, extra_env=None):
    """
    Run a function in a sub-process.

    Parameters
    ----------
    func : function
        The function to be run.  It must be in a module that is importable.
    *args : str
        Any additional command line arguments to be passed in
        the first argument to ``subprocess.run``.
    extra_env : dict[str, str]
        Any additional environment variables to be set for the subprocess.
    """
    target = func.__name__
    module = func.__module__
    file = func.__code__.co_filename
    proc = subprocess_run_for_testing(
        [
            sys.executable,
            "-c",
            f"import importlib.util;"
            f"_spec = importlib.util.spec_from_file_location({module!r}, {file!r});"
            f"_module = importlib.util.module_from_spec(_spec);"
            f"_spec.loader.exec_module(_module);"
            f"_module.{target}()",
            *args
        ],
        env={**os.environ, "SOURCE_DATE_EPOCH": "0", **(extra_env or {})},
        timeout=timeout, check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    return proc


def _check_for_pgf(texsystem):
    """
    Check if a given TeX system + pgf is available

    Parameters
    ----------
    texsystem : str
        The executable name to check
    """
    with TemporaryDirectory() as tmpdir:
        tex_path = Path(tmpdir, "test.tex")
        tex_path.write_text(r"""
            \documentclass{article}
            \usepackage{pgf}
            \begin{document}
            \typeout{pgfversion=\pgfversion}
            \makeatletter
            \@@end
        """, encoding="utf-8")
        try:
            subprocess.check_call(
                [texsystem, "-halt-on-error", str(tex_path)], cwd=tmpdir,
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except (OSError, subprocess.CalledProcessError):
            return False
        return True


def _has_tex_package(package):
    try:
        mpl.dviread.find_tex_file(f"{package}.sty")
        return True
    except FileNotFoundError:
        return False


def ipython_in_subprocess(requested_backend_or_gui_framework, all_expected_backends):
    import pytest
    IPython = pytest.importorskip("IPython")

    if sys.platform == "win32":
        pytest.skip("Cannot change backend running IPython in subprocess on Windows")

    if (IPython.version_info[:3] == (8, 24, 0) and
            requested_backend_or_gui_framework == "osx"):
        pytest.skip("Bug using macosx backend in IPython 8.24.0 fixed in 8.24.1")

    # This code can be removed when Python 3.12, the latest version supported
    # by IPython < 8.24, reaches end-of-life in late 2028.
    for min_version, backend in all_expected_backends.items():
        if IPython.version_info[:2] >= min_version:
            expected_backend = backend
            break

    code = ("import matplotlib as mpl, matplotlib.pyplot as plt;"
            "fig, ax=plt.subplots(); ax.plot([1, 3, 2]); mpl.get_backend()")
    proc = subprocess_run_for_testing(
        [
            "ipython",
            "--no-simple-prompt",
            f"--matplotlib={requested_backend_or_gui_framework}",
            "-c", code,
        ],
        check=True,
        capture_output=True,
    )

    assert proc.stdout.strip().endswith(f"'{expected_backend}'")


def is_ci_environment():
    # Common CI variables
    ci_environment_variables = [
        'CI',        # Generic CI environment variable
        'CONTINUOUS_INTEGRATION',  # Generic CI environment variable
        'TRAVIS',    # Travis CI
        'CIRCLECI',  # CircleCI
        'JENKINS',   # Jenkins
        'GITLAB_CI',  # GitLab CI
        'GITHUB_ACTIONS',  # GitHub Actions
        'TEAMCITY_VERSION'  # TeamCity
        # Add other CI environment variables as needed
    ]

    for env_var in ci_environment_variables:
        if os.getenv(env_var):
            return True

    return False

# === NexusCore/openenv\Lib\site-packages\nltk\parse\util.py ===
# Natural Language Toolkit: Parser Utility Functions
#
# Author: Ewan Klein <ewan@inf.ed.ac.uk>
#         Tom Aarsen <>
#
# Copyright (C) 2001-2024 NLTK Project
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT


"""
Utility functions for parsers.
"""

from nltk.data import load
from nltk.grammar import CFG, PCFG, FeatureGrammar
from nltk.parse.chart import Chart, ChartParser
from nltk.parse.featurechart import FeatureChart, FeatureChartParser
from nltk.parse.pchart import InsideChartParser


def load_parser(
    grammar_url, trace=0, parser=None, chart_class=None, beam_size=0, **load_args
):
    """
    Load a grammar from a file, and build a parser based on that grammar.
    The parser depends on the grammar format, and might also depend
    on properties of the grammar itself.

    The following grammar formats are currently supported:
      - ``'cfg'``  (CFGs: ``CFG``)
      - ``'pcfg'`` (probabilistic CFGs: ``PCFG``)
      - ``'fcfg'`` (feature-based CFGs: ``FeatureGrammar``)

    :type grammar_url: str
    :param grammar_url: A URL specifying where the grammar is located.
        The default protocol is ``"nltk:"``, which searches for the file
        in the the NLTK data package.
    :type trace: int
    :param trace: The level of tracing that should be used when
        parsing a text.  ``0`` will generate no tracing output;
        and higher numbers will produce more verbose tracing output.
    :param parser: The class used for parsing; should be ``ChartParser``
        or a subclass.
        If None, the class depends on the grammar format.
    :param chart_class: The class used for storing the chart;
        should be ``Chart`` or a subclass.
        Only used for CFGs and feature CFGs.
        If None, the chart class depends on the grammar format.
    :type beam_size: int
    :param beam_size: The maximum length for the parser's edge queue.
        Only used for probabilistic CFGs.
    :param load_args: Keyword parameters used when loading the grammar.
        See ``data.load`` for more information.
    """
    grammar = load(grammar_url, **load_args)
    if not isinstance(grammar, CFG):
        raise ValueError("The grammar must be a CFG, " "or a subclass thereof.")
    if isinstance(grammar, PCFG):
        if parser is None:
            parser = InsideChartParser
        return parser(grammar, trace=trace, beam_size=beam_size)

    elif isinstance(grammar, FeatureGrammar):
        if parser is None:
            parser = FeatureChartParser
        if chart_class is None:
            chart_class = FeatureChart
        return parser(grammar, trace=trace, chart_class=chart_class)

    else:  # Plain CFG.
        if parser is None:
            parser = ChartParser
        if chart_class is None:
            chart_class = Chart
        return parser(grammar, trace=trace, chart_class=chart_class)


def taggedsent_to_conll(sentence):
    """
    A module to convert a single POS tagged sentence into CONLL format.

    >>> from nltk import word_tokenize, pos_tag
    >>> text = "This is a foobar sentence."
    >>> for line in taggedsent_to_conll(pos_tag(word_tokenize(text))): # doctest: +NORMALIZE_WHITESPACE
    ... 	print(line, end="")
        1	This	_	DT	DT	_	0	a	_	_
        2	is	_	VBZ	VBZ	_	0	a	_	_
        3	a	_	DT	DT	_	0	a	_	_
        4	foobar	_	JJ	JJ	_	0	a	_	_
        5	sentence	_	NN	NN	_	0	a	_	_
        6	.		_	.	.	_	0	a	_	_

    :param sentence: A single input sentence to parse
    :type sentence: list(tuple(str, str))
    :rtype: iter(str)
    :return: a generator yielding a single sentence in CONLL format.
    """
    for i, (word, tag) in enumerate(sentence, start=1):
        input_str = [str(i), word, "_", tag, tag, "_", "0", "a", "_", "_"]
        input_str = "\t".join(input_str) + "\n"
        yield input_str


def taggedsents_to_conll(sentences):
    """
    A module to convert the a POS tagged document stream
    (i.e. list of list of tuples, a list of sentences) and yield lines
    in CONLL format. This module yields one line per word and two newlines
    for end of sentence.

    >>> from nltk import word_tokenize, sent_tokenize, pos_tag
    >>> text = "This is a foobar sentence. Is that right?"
    >>> sentences = [pos_tag(word_tokenize(sent)) for sent in sent_tokenize(text)]
    >>> for line in taggedsents_to_conll(sentences): # doctest: +NORMALIZE_WHITESPACE
    ...     if line:
    ...         print(line, end="")
    1	This	_	DT	DT	_	0	a	_	_
    2	is	_	VBZ	VBZ	_	0	a	_	_
    3	a	_	DT	DT	_	0	a	_	_
    4	foobar	_	JJ	JJ	_	0	a	_	_
    5	sentence	_	NN	NN	_	0	a	_	_
    6	.		_	.	.	_	0	a	_	_
    <BLANKLINE>
    <BLANKLINE>
    1	Is	_	VBZ	VBZ	_	0	a	_	_
    2	that	_	IN	IN	_	0	a	_	_
    3	right	_	NN	NN	_	0	a	_	_
    4	?	_	.	.	_	0	a	_	_
    <BLANKLINE>
    <BLANKLINE>

    :param sentences: Input sentences to parse
    :type sentence: list(list(tuple(str, str)))
    :rtype: iter(str)
    :return: a generator yielding sentences in CONLL format.
    """
    for sentence in sentences:
        yield from taggedsent_to_conll(sentence)
        yield "\n\n"


######################################################################
# { Test Suites
######################################################################


class TestGrammar:
    """
    Unit tests for  CFG.
    """

    def __init__(self, grammar, suite, accept=None, reject=None):
        self.test_grammar = grammar

        self.cp = load_parser(grammar, trace=0)
        self.suite = suite
        self._accept = accept
        self._reject = reject

    def run(self, show_trees=False):
        """
        Sentences in the test suite are divided into two classes:

        - grammatical (``accept``) and
        - ungrammatical (``reject``).

        If a sentence should parse according to the grammar, the value of
        ``trees`` will be a non-empty list. If a sentence should be rejected
        according to the grammar, then the value of ``trees`` will be None.
        """
        for test in self.suite:
            print(test["doc"] + ":", end=" ")
            for key in ["accept", "reject"]:
                for sent in test[key]:
                    tokens = sent.split()
                    trees = list(self.cp.parse(tokens))
                    if show_trees and trees:
                        print()
                        print(sent)
                        for tree in trees:
                            print(tree)
                    if key == "accept":
                        if trees == []:
                            raise ValueError("Sentence '%s' failed to parse'" % sent)
                        else:
                            accepted = True
                    else:
                        if trees:
                            raise ValueError("Sentence '%s' received a parse'" % sent)
                        else:
                            rejected = True
            if accepted and rejected:
                print("All tests passed!")


def extract_test_sentences(string, comment_chars="#%;", encoding=None):
    """
    Parses a string with one test sentence per line.
    Lines can optionally begin with:

    - a bool, saying if the sentence is grammatical or not, or
    - an int, giving the number of parse trees is should have,

    The result information is followed by a colon, and then the sentence.
    Empty lines and lines beginning with a comment char are ignored.

    :return: a list of tuple of sentences and expected results,
        where a sentence is a list of str,
        and a result is None, or bool, or int

    :param comment_chars: ``str`` of possible comment characters.
    :param encoding: the encoding of the string, if it is binary
    """
    if encoding is not None:
        string = string.decode(encoding)
    sentences = []
    for sentence in string.split("\n"):
        if sentence == "" or sentence[0] in comment_chars:
            continue
        split_info = sentence.split(":", 1)
        result = None
        if len(split_info) == 2:
            if split_info[0] in ["True", "true", "False", "false"]:
                result = split_info[0] in ["True", "true"]
                sentence = split_info[1]
            else:
                result = int(split_info[0])
                sentence = split_info[1]
        tokens = sentence.split()
        if tokens == []:
            continue
        sentences += [(tokens, result)]
    return sentences

# === NexusCore/openenv\Lib\site-packages\nltk\tokenize\destructive.py ===
# Natural Language Toolkit: NLTK's very own tokenizer.
#
# Copyright (C) 2001-2024 NLTK Project
# Author: Liling Tan
#         Tom Aarsen <> (modifications)
# URL: <https://www.nltk.org>
# For license information, see LICENSE.TXT


import re
import warnings
from typing import Iterator, List, Tuple

from nltk.tokenize.api import TokenizerI
from nltk.tokenize.util import align_tokens


class MacIntyreContractions:
    """
    List of contractions adapted from Robert MacIntyre's tokenizer.
    """

    CONTRACTIONS2 = [
        r"(?i)\b(can)(?#X)(not)\b",
        r"(?i)\b(d)(?#X)('ye)\b",
        r"(?i)\b(gim)(?#X)(me)\b",
        r"(?i)\b(gon)(?#X)(na)\b",
        r"(?i)\b(got)(?#X)(ta)\b",
        r"(?i)\b(lem)(?#X)(me)\b",
        r"(?i)\b(more)(?#X)('n)\b",
        r"(?i)\b(wan)(?#X)(na)(?=\s)",
    ]
    CONTRACTIONS3 = [r"(?i) ('t)(?#X)(is)\b", r"(?i) ('t)(?#X)(was)\b"]
    CONTRACTIONS4 = [r"(?i)\b(whad)(dd)(ya)\b", r"(?i)\b(wha)(t)(cha)\b"]


class NLTKWordTokenizer(TokenizerI):
    """
    The NLTK tokenizer that has improved upon the TreebankWordTokenizer.

    This is the method that is invoked by ``word_tokenize()``.  It assumes that the
    text has already been segmented into sentences, e.g. using ``sent_tokenize()``.

    The tokenizer is "destructive" such that the regexes applied will munge the
    input string to a state beyond re-construction. It is possible to apply
    `TreebankWordDetokenizer.detokenize` to the tokenized outputs of
    `NLTKDestructiveWordTokenizer.tokenize` but there's no guarantees to
    revert to the original string.
    """

    # Starting quotes.
    STARTING_QUOTES = [
        (re.compile("([«“‘„]|[`]+)", re.U), r" \1 "),
        (re.compile(r"^\""), r"``"),
        (re.compile(r"(``)"), r" \1 "),
        (re.compile(r"([ \(\[{<])(\"|\'{2})"), r"\1 `` "),
        (re.compile(r"(?i)(\')(?!re|ve|ll|m|t|s|d|n)(\w)\b", re.U), r"\1 \2"),
    ]

    # Ending quotes.
    ENDING_QUOTES = [
        (re.compile("([»”’])", re.U), r" \1 "),
        (re.compile(r"''"), " '' "),
        (re.compile(r'"'), " '' "),
        (re.compile(r"\s+"), " "),
        (re.compile(r"([^' ])('[sS]|'[mM]|'[dD]|') "), r"\1 \2 "),
        (re.compile(r"([^' ])('ll|'LL|'re|'RE|'ve|'VE|n't|N'T) "), r"\1 \2 "),
    ]

    # For improvements for starting/closing quotes from TreebankWordTokenizer,
    # see discussion on https://github.com/nltk/nltk/pull/1437
    # Adding to TreebankWordTokenizer, nltk.word_tokenize now splits on
    # - chevron quotes u'\xab' and u'\xbb'
    # - unicode quotes u'\u2018', u'\u2019', u'\u201c' and u'\u201d'
    # See https://github.com/nltk/nltk/issues/1995#issuecomment-376741608
    # Also, behavior of splitting on clitics now follows Stanford CoreNLP
    # - clitics covered (?!re|ve|ll|m|t|s|d)(\w)\b

    # Punctuation.
    PUNCTUATION = [
        (re.compile(r'([^\.])(\.)([\]\)}>"\'' "»”’ " r"]*)\s*$", re.U), r"\1 \2 \3 "),
        (re.compile(r"([:,])([^\d])"), r" \1 \2"),
        (re.compile(r"([:,])$"), r" \1 "),
        (
            re.compile(r"\.{2,}", re.U),
            r" \g<0> ",
        ),  # See https://github.com/nltk/nltk/pull/2322
        (re.compile(r"[;@#$%&]"), r" \g<0> "),
        (
            re.compile(r'([^\.])(\.)([\]\)}>"\']*)\s*$'),
            r"\1 \2\3 ",
        ),  # Handles the final period.
        (re.compile(r"[?!]"), r" \g<0> "),
        (re.compile(r"([^'])' "), r"\1 ' "),
        (
            re.compile(r"[*]", re.U),
            r" \g<0> ",
        ),  # See https://github.com/nltk/nltk/pull/2322
    ]

    # Pads parentheses
    PARENS_BRACKETS = (re.compile(r"[\]\[\(\)\{\}\<\>]"), r" \g<0> ")

    # Optionally: Convert parentheses, brackets and converts them to PTB symbols.
    CONVERT_PARENTHESES = [
        (re.compile(r"\("), "-LRB-"),
        (re.compile(r"\)"), "-RRB-"),
        (re.compile(r"\["), "-LSB-"),
        (re.compile(r"\]"), "-RSB-"),
        (re.compile(r"\{"), "-LCB-"),
        (re.compile(r"\}"), "-RCB-"),
    ]

    DOUBLE_DASHES = (re.compile(r"--"), r" -- ")

    # List of contractions adapted from Robert MacIntyre's tokenizer.
    _contractions = MacIntyreContractions()
    CONTRACTIONS2 = list(map(re.compile, _contractions.CONTRACTIONS2))
    CONTRACTIONS3 = list(map(re.compile, _contractions.CONTRACTIONS3))

    def tokenize(
        self, text: str, convert_parentheses: bool = False, return_str: bool = False
    ) -> List[str]:
        r"""Return a tokenized copy of `text`.

        >>> from nltk.tokenize import NLTKWordTokenizer
        >>> s = '''Good muffins cost $3.88 (roughly 3,36 euros)\nin New York.  Please buy me\ntwo of them.\nThanks.'''
        >>> NLTKWordTokenizer().tokenize(s) # doctest: +NORMALIZE_WHITESPACE
        ['Good', 'muffins', 'cost', '$', '3.88', '(', 'roughly', '3,36',
        'euros', ')', 'in', 'New', 'York.', 'Please', 'buy', 'me', 'two',
        'of', 'them.', 'Thanks', '.']
        >>> NLTKWordTokenizer().tokenize(s, convert_parentheses=True) # doctest: +NORMALIZE_WHITESPACE
        ['Good', 'muffins', 'cost', '$', '3.88', '-LRB-', 'roughly', '3,36',
        'euros', '-RRB-', 'in', 'New', 'York.', 'Please', 'buy', 'me', 'two',
        'of', 'them.', 'Thanks', '.']


        :param text: A string with a sentence or sentences.
        :type text: str
        :param convert_parentheses: if True, replace parentheses to PTB symbols,
            e.g. `(` to `-LRB-`. Defaults to False.
        :type convert_parentheses: bool, optional
        :param return_str: If True, return tokens as space-separated string,
            defaults to False.
        :type return_str: bool, optional
        :return: List of tokens from `text`.
        :rtype: List[str]
        """
        if return_str:
            warnings.warn(
                "Parameter 'return_str' has been deprecated and should no "
                "longer be used.",
                category=DeprecationWarning,
                stacklevel=2,
            )

        for regexp, substitution in self.STARTING_QUOTES:
            text = regexp.sub(substitution, text)

        for regexp, substitution in self.PUNCTUATION:
            text = regexp.sub(substitution, text)

        # Handles parentheses.
        regexp, substitution = self.PARENS_BRACKETS
        text = regexp.sub(substitution, text)
        # Optionally convert parentheses
        if convert_parentheses:
            for regexp, substitution in self.CONVERT_PARENTHESES:
                text = regexp.sub(substitution, text)

        # Handles double dash.
        regexp, substitution = self.DOUBLE_DASHES
        text = regexp.sub(substitution, text)

        # add extra space to make things easier
        text = " " + text + " "

        for regexp, substitution in self.ENDING_QUOTES:
            text = regexp.sub(substitution, text)

        for regexp in self.CONTRACTIONS2:
            text = regexp.sub(r" \1 \2 ", text)
        for regexp in self.CONTRACTIONS3:
            text = regexp.sub(r" \1 \2 ", text)

        # We are not using CONTRACTIONS4 since
        # they are also commented out in the SED scripts
        # for regexp in self._contractions.CONTRACTIONS4:
        #     text = regexp.sub(r' \1 \2 \3 ', text)

        return text.split()

    def span_tokenize(self, text: str) -> Iterator[Tuple[int, int]]:
        r"""
        Returns the spans of the tokens in ``text``.
        Uses the post-hoc nltk.tokens.align_tokens to return the offset spans.

            >>> from nltk.tokenize import NLTKWordTokenizer
            >>> s = '''Good muffins cost $3.88\nin New (York).  Please (buy) me\ntwo of them.\n(Thanks).'''
            >>> expected = [(0, 4), (5, 12), (13, 17), (18, 19), (19, 23),
            ... (24, 26), (27, 30), (31, 32), (32, 36), (36, 37), (37, 38),
            ... (40, 46), (47, 48), (48, 51), (51, 52), (53, 55), (56, 59),
            ... (60, 62), (63, 68), (69, 70), (70, 76), (76, 77), (77, 78)]
            >>> list(NLTKWordTokenizer().span_tokenize(s)) == expected
            True
            >>> expected = ['Good', 'muffins', 'cost', '$', '3.88', 'in',
            ... 'New', '(', 'York', ')', '.', 'Please', '(', 'buy', ')',
            ... 'me', 'two', 'of', 'them.', '(', 'Thanks', ')', '.']
            >>> [s[start:end] for start, end in NLTKWordTokenizer().span_tokenize(s)] == expected
            True

        :param text: A string with a sentence or sentences.
        :type text: str
        :yield: Tuple[int, int]
        """
        raw_tokens = self.tokenize(text)

        # Convert converted quotes back to original double quotes
        # Do this only if original text contains double quote(s) or double
        # single-quotes (because '' might be transformed to `` if it is
        # treated as starting quotes).
        if ('"' in text) or ("''" in text):
            # Find double quotes and converted quotes
            matched = [m.group() for m in re.finditer(r"``|'{2}|\"", text)]

            # Replace converted quotes back to double quotes
            tokens = [
                matched.pop(0) if tok in ['"', "``", "''"] else tok
                for tok in raw_tokens
            ]
        else:
            tokens = raw_tokens

        yield from align_tokens(tokens, text)

# === NexusCore/openenv\Lib\site-packages\openai\resources\responses\input_items.py ===
# File generated from our OpenAPI spec by Stainless. See CONTRIBUTING.md for details.

from __future__ import annotations

from typing import Any, List, cast
from typing_extensions import Literal

import httpx

from ... import _legacy_response
from ..._types import NOT_GIVEN, Body, Query, Headers, NotGiven
from ..._utils import maybe_transform
from ..._compat import cached_property
from ..._resource import SyncAPIResource, AsyncAPIResource
from ..._response import to_streamed_response_wrapper, async_to_streamed_response_wrapper
from ...pagination import SyncCursorPage, AsyncCursorPage
from ..._base_client import AsyncPaginator, make_request_options
from ...types.responses import input_item_list_params
from ...types.responses.response_item import ResponseItem
from ...types.responses.response_includable import ResponseIncludable

__all__ = ["InputItems", "AsyncInputItems"]


class InputItems(SyncAPIResource):
    @cached_property
    def with_raw_response(self) -> InputItemsWithRawResponse:
        """
        This property can be used as a prefix for any HTTP method call to return
        the raw response object instead of the parsed content.

        For more information, see https://www.github.com/openai/openai-python#accessing-raw-response-data-eg-headers
        """
        return InputItemsWithRawResponse(self)

    @cached_property
    def with_streaming_response(self) -> InputItemsWithStreamingResponse:
        """
        An alternative to `.with_raw_response` that doesn't eagerly read the response body.

        For more information, see https://www.github.com/openai/openai-python#with_streaming_response
        """
        return InputItemsWithStreamingResponse(self)

    def list(
        self,
        response_id: str,
        *,
        after: str | NotGiven = NOT_GIVEN,
        before: str | NotGiven = NOT_GIVEN,
        include: List[ResponseIncludable] | NotGiven = NOT_GIVEN,
        limit: int | NotGiven = NOT_GIVEN,
        order: Literal["asc", "desc"] | NotGiven = NOT_GIVEN,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> SyncCursorPage[ResponseItem]:
        """
        Returns a list of input items for a given response.

        Args:
          after: An item ID to list items after, used in pagination.

          before: An item ID to list items before, used in pagination.

          include: Additional fields to include in the response. See the `include` parameter for
              Response creation above for more information.

          limit: A limit on the number of objects to be returned. Limit can range between 1 and
              100, and the default is 20.

          order: The order to return the input items in. Default is `desc`.

              - `asc`: Return the input items in ascending order.
              - `desc`: Return the input items in descending order.

          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request, in seconds
        """
        if not response_id:
            raise ValueError(f"Expected a non-empty value for `response_id` but received {response_id!r}")
        return self._get_api_list(
            f"/responses/{response_id}/input_items",
            page=SyncCursorPage[ResponseItem],
            options=make_request_options(
                extra_headers=extra_headers,
                extra_query=extra_query,
                extra_body=extra_body,
                timeout=timeout,
                query=maybe_transform(
                    {
                        "after": after,
                        "before": before,
                        "include": include,
                        "limit": limit,
                        "order": order,
                    },
                    input_item_list_params.InputItemListParams,
                ),
            ),
            model=cast(Any, ResponseItem),  # Union types cannot be passed in as arguments in the type system
        )


class AsyncInputItems(AsyncAPIResource):
    @cached_property
    def with_raw_response(self) -> AsyncInputItemsWithRawResponse:
        """
        This property can be used as a prefix for any HTTP method call to return
        the raw response object instead of the parsed content.

        For more information, see https://www.github.com/openai/openai-python#accessing-raw-response-data-eg-headers
        """
        return AsyncInputItemsWithRawResponse(self)

    @cached_property
    def with_streaming_response(self) -> AsyncInputItemsWithStreamingResponse:
        """
        An alternative to `.with_raw_response` that doesn't eagerly read the response body.

        For more information, see https://www.github.com/openai/openai-python#with_streaming_response
        """
        return AsyncInputItemsWithStreamingResponse(self)

    def list(
        self,
        response_id: str,
        *,
        after: str | NotGiven = NOT_GIVEN,
        before: str | NotGiven = NOT_GIVEN,
        include: List[ResponseIncludable] | NotGiven = NOT_GIVEN,
        limit: int | NotGiven = NOT_GIVEN,
        order: Literal["asc", "desc"] | NotGiven = NOT_GIVEN,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> AsyncPaginator[ResponseItem, AsyncCursorPage[ResponseItem]]:
        """
        Returns a list of input items for a given response.

        Args:
          after: An item ID to list items after, used in pagination.

          before: An item ID to list items before, used in pagination.

          include: Additional fields to include in the response. See the `include` parameter for
              Response creation above for more information.

          limit: A limit on the number of objects to be returned. Limit can range between 1 and
              100, and the default is 20.

          order: The order to return the input items in. Default is `desc`.

              - `asc`: Return the input items in ascending order.
              - `desc`: Return the input items in descending order.

          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request, in seconds
        """
        if not response_id:
            raise ValueError(f"Expected a non-empty value for `response_id` but received {response_id!r}")
        return self._get_api_list(
            f"/responses/{response_id}/input_items",
            page=AsyncCursorPage[ResponseItem],
            options=make_request_options(
                extra_headers=extra_headers,
                extra_query=extra_query,
                extra_body=extra_body,
                timeout=timeout,
                query=maybe_transform(
                    {
                        "after": after,
                        "before": before,
                        "include": include,
                        "limit": limit,
                        "order": order,
                    },
                    input_item_list_params.InputItemListParams,
                ),
            ),
            model=cast(Any, ResponseItem),  # Union types cannot be passed in as arguments in the type system
        )


class InputItemsWithRawResponse:
    def __init__(self, input_items: InputItems) -> None:
        self._input_items = input_items

        self.list = _legacy_response.to_raw_response_wrapper(
            input_items.list,
        )


class AsyncInputItemsWithRawResponse:
    def __init__(self, input_items: AsyncInputItems) -> None:
        self._input_items = input_items

        self.list = _legacy_response.async_to_raw_response_wrapper(
            input_items.list,
        )


class InputItemsWithStreamingResponse:
    def __init__(self, input_items: InputItems) -> None:
        self._input_items = input_items

        self.list = to_streamed_response_wrapper(
            input_items.list,
        )


class AsyncInputItemsWithStreamingResponse:
    def __init__(self, input_items: AsyncInputItems) -> None:
        self._input_items = input_items

        self.list = async_to_streamed_response_wrapper(
            input_items.list,
        )

# === NexusCore/openenv\Lib\site-packages\pyasn1\codec\streaming.py ===
#
# This file is part of pyasn1 software.
#
# Copyright (c) 2005-2019, Ilya Etingof <etingof@gmail.com>
# License: https://pyasn1.readthedocs.io/en/latest/license.html
#
import io
import os

from pyasn1 import error
from pyasn1.type import univ

class CachingStreamWrapper(io.IOBase):
    """Wrapper around non-seekable streams.

    Note that the implementation is tied to the decoder,
    not checking for dangerous arguments for the sake
    of performance.

    The read bytes are kept in an internal cache until
    setting _markedPosition which may reset the cache.
    """
    def __init__(self, raw):
        self._raw = raw
        self._cache = io.BytesIO()
        self._markedPosition = 0

    def peek(self, n):
        result = self.read(n)
        self._cache.seek(-len(result), os.SEEK_CUR)
        return result

    def seekable(self):
        return True

    def seek(self, n=-1, whence=os.SEEK_SET):
        # Note that this not safe for seeking forward.
        return self._cache.seek(n, whence)

    def read(self, n=-1):
        read_from_cache = self._cache.read(n)
        if n != -1:
            n -= len(read_from_cache)
            if not n:  # 0 bytes left to read
                return read_from_cache

        read_from_raw = self._raw.read(n)

        self._cache.write(read_from_raw)

        return read_from_cache + read_from_raw

    @property
    def markedPosition(self):
        """Position where the currently processed element starts.

        This is used for back-tracking in SingleItemDecoder.__call__
        and (indefLen)ValueDecoder and should not be used for other purposes.
        The client is not supposed to ever seek before this position.
        """
        return self._markedPosition

    @markedPosition.setter
    def markedPosition(self, value):
        # By setting the value, we ensure we won't seek back before it.
        # `value` should be the same as the current position
        # We don't check for this for performance reasons.
        self._markedPosition = value

        # Whenever we set _marked_position, we know for sure
        # that we will not return back, and thus it is
        # safe to drop all cached data.
        if self._cache.tell() > io.DEFAULT_BUFFER_SIZE:
            self._cache = io.BytesIO(self._cache.read())
            self._markedPosition = 0

    def tell(self):
        return self._cache.tell()


def asSeekableStream(substrate):
    """Convert object to seekable byte-stream.

    Parameters
    ----------
    substrate: :py:class:`bytes` or :py:class:`io.IOBase` or :py:class:`univ.OctetString`

    Returns
    -------
    : :py:class:`io.IOBase`

    Raises
    ------
    : :py:class:`~pyasn1.error.PyAsn1Error`
        If the supplied substrate cannot be converted to a seekable stream.
    """
    if isinstance(substrate, io.BytesIO):
        return substrate

    elif isinstance(substrate, bytes):
        return io.BytesIO(substrate)

    elif isinstance(substrate, univ.OctetString):
        return io.BytesIO(substrate.asOctets())

    try:
        if substrate.seekable():  # Will fail for most invalid types
            return substrate
        else:
            return CachingStreamWrapper(substrate)

    except AttributeError:
        raise error.UnsupportedSubstrateError(
            "Cannot convert " + substrate.__class__.__name__ +
            " to a seekable bit stream.")


def isEndOfStream(substrate):
    """Check whether we have reached the end of a stream.

    Although it is more effective to read and catch exceptions, this
    function

    Parameters
    ----------
    substrate: :py:class:`IOBase`
        Stream to check

    Returns
    -------
    : :py:class:`bool`
    """
    if isinstance(substrate, io.BytesIO):
        cp = substrate.tell()
        substrate.seek(0, os.SEEK_END)
        result = substrate.tell() == cp
        substrate.seek(cp, os.SEEK_SET)
        yield result

    else:
        received = substrate.read(1)
        if received is None:
            yield

        if received:
            substrate.seek(-1, os.SEEK_CUR)

        yield not received


def peekIntoStream(substrate, size=-1):
    """Peek into stream.

    Parameters
    ----------
    substrate: :py:class:`IOBase`
        Stream to read from.

    size: :py:class:`int`
        How many bytes to peek (-1 = all available)

    Returns
    -------
    : :py:class:`bytes` or :py:class:`str`
        The return type depends on Python major version
    """
    if hasattr(substrate, "peek"):
        received = substrate.peek(size)
        if received is None:
            yield

        while len(received) < size:
            yield

        yield received

    else:
        current_position = substrate.tell()
        try:
            for chunk in readFromStream(substrate, size):
                yield chunk

        finally:
            substrate.seek(current_position)


def readFromStream(substrate, size=-1, context=None):
    """Read from the stream.

    Parameters
    ----------
    substrate: :py:class:`IOBase`
        Stream to read from.

    Keyword parameters
    ------------------
    size: :py:class:`int`
        How many bytes to read (-1 = all available)

    context: :py:class:`dict`
        Opaque caller context will be attached to exception objects created
        by this function.

    Yields
    ------
    : :py:class:`bytes` or :py:class:`str` or :py:class:`SubstrateUnderrunError`
        Read data or :py:class:`~pyasn1.error.SubstrateUnderrunError`
        object if no `size` bytes is readily available in the stream. The
        data type depends on Python major version

    Raises
    ------
    : :py:class:`~pyasn1.error.EndOfStreamError`
        Input stream is exhausted
    """
    while True:
        # this will block unless stream is non-blocking
        received = substrate.read(size)
        if received is None:  # non-blocking stream can do this
            yield error.SubstrateUnderrunError(context=context)

        elif not received and size != 0:  # end-of-stream
            raise error.EndOfStreamError(context=context)

        elif len(received) < size:
            substrate.seek(-len(received), os.SEEK_CUR)

            # behave like a non-blocking stream
            yield error.SubstrateUnderrunError(context=context)

        else:
            break

    yield received

# === NexusCore/openenv\Lib\site-packages\selenium\webdriver\support\event_firing_webdriver.py ===
# Licensed to the Software Freedom Conservancy (SFC) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The SFC licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.

from typing import Any, List, Tuple

from selenium.common.exceptions import WebDriverException
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement

from .abstract_event_listener import AbstractEventListener


def _wrap_elements(result, ef_driver):
    # handle the case if another wrapper wraps EventFiringWebElement
    if isinstance(result, EventFiringWebElement):
        return result
    if isinstance(result, WebElement):
        return EventFiringWebElement(result, ef_driver)
    if isinstance(result, list):
        return [_wrap_elements(item, ef_driver) for item in result]
    return result


class EventFiringWebDriver:
    """A wrapper around an arbitrary WebDriver instance which supports firing
    events."""

    def __init__(self, driver: WebDriver, event_listener: AbstractEventListener) -> None:
        """Creates a new instance of the EventFiringWebDriver.

        :Args:
         - driver : A WebDriver instance
         - event_listener : Instance of a class that subclasses AbstractEventListener and implements it fully
                            or partially

        Example:

        ::

            from selenium.webdriver import Firefox
            from selenium.webdriver.support.events import EventFiringWebDriver, AbstractEventListener


            class MyListener(AbstractEventListener):
                def before_navigate_to(self, url, driver):
                    print("Before navigate to %s" % url)

                def after_navigate_to(self, url, driver):
                    print("After navigate to %s" % url)


            driver = Firefox()
            ef_driver = EventFiringWebDriver(driver, MyListener())
            ef_driver.get("http://www.google.co.in/")
        """
        if not isinstance(driver, WebDriver):
            raise WebDriverException("A WebDriver instance must be supplied")
        if not isinstance(event_listener, AbstractEventListener):
            raise WebDriverException("Event listener must be a subclass of AbstractEventListener")
        self._driver = driver
        self._driver._wrap_value = self._wrap_value
        self._listener = event_listener

    @property
    def wrapped_driver(self) -> WebDriver:
        """Returns the WebDriver instance wrapped by this
        EventsFiringWebDriver."""
        return self._driver

    def get(self, url: str) -> None:
        self._dispatch("navigate_to", (url, self._driver), "get", (url,))

    def back(self) -> None:
        self._dispatch("navigate_back", (self._driver,), "back", ())

    def forward(self) -> None:
        self._dispatch("navigate_forward", (self._driver,), "forward", ())

    def execute_script(self, script: str, *args):
        unwrapped_args = (script,) + self._unwrap_element_args(args)
        return self._dispatch("execute_script", (script, self._driver), "execute_script", unwrapped_args)

    def execute_async_script(self, script, *args):
        unwrapped_args = (script,) + self._unwrap_element_args(args)
        return self._dispatch("execute_script", (script, self._driver), "execute_async_script", unwrapped_args)

    def close(self) -> None:
        self._dispatch("close", (self._driver,), "close", ())

    def quit(self) -> None:
        self._dispatch("quit", (self._driver,), "quit", ())

    def find_element(self, by=By.ID, value=None) -> WebElement:
        return self._dispatch("find", (by, value, self._driver), "find_element", (by, value))

    def find_elements(self, by=By.ID, value=None) -> List[WebElement]:
        return self._dispatch("find", (by, value, self._driver), "find_elements", (by, value))

    def _dispatch(self, l_call: str, l_args: Tuple[Any, ...], d_call: str, d_args: Tuple[Any, ...]):
        getattr(self._listener, f"before_{l_call}")(*l_args)
        try:
            result = getattr(self._driver, d_call)(*d_args)
        except Exception as exc:
            self._listener.on_exception(exc, self._driver)
            raise
        getattr(self._listener, f"after_{l_call}")(*l_args)
        return _wrap_elements(result, self)

    def _unwrap_element_args(self, args):
        if isinstance(args, EventFiringWebElement):
            return args.wrapped_element
        if isinstance(args, tuple):
            return tuple(self._unwrap_element_args(item) for item in args)
        if isinstance(args, list):
            return [self._unwrap_element_args(item) for item in args]
        return args

    def _wrap_value(self, value):
        if isinstance(value, EventFiringWebElement):
            return WebDriver._wrap_value(self._driver, value.wrapped_element)
        return WebDriver._wrap_value(self._driver, value)

    def __setattr__(self, item, value):
        if item.startswith("_") or not hasattr(self._driver, item):
            object.__setattr__(self, item, value)
        else:
            try:
                object.__setattr__(self._driver, item, value)
            except Exception as exc:
                self._listener.on_exception(exc, self._driver)
                raise

    def __getattr__(self, name):
        def _wrap(*args, **kwargs):
            try:
                result = attrib(*args, **kwargs)
                return _wrap_elements(result, self)
            except Exception as exc:
                self._listener.on_exception(exc, self._driver)
                raise

        try:
            attrib = getattr(self._driver, name)
            return _wrap if callable(attrib) else attrib
        except Exception as exc:
            self._listener.on_exception(exc, self._driver)
            raise


class EventFiringWebElement:
    """A wrapper around WebElement instance which supports firing events."""

    def __init__(self, webelement: WebElement, ef_driver: EventFiringWebDriver) -> None:
        """Creates a new instance of the EventFiringWebElement."""
        self._webelement = webelement
        self._ef_driver = ef_driver
        self._driver = ef_driver.wrapped_driver
        self._listener = ef_driver._listener

    @property
    def wrapped_element(self) -> WebElement:
        """Returns the WebElement wrapped by this EventFiringWebElement
        instance."""
        return self._webelement

    def click(self) -> None:
        self._dispatch("click", (self._webelement, self._driver), "click", ())

    def clear(self) -> None:
        self._dispatch("change_value_of", (self._webelement, self._driver), "clear", ())

    def send_keys(self, *value) -> None:
        self._dispatch("change_value_of", (self._webelement, self._driver), "send_keys", value)

    def find_element(self, by=By.ID, value=None) -> WebElement:
        return self._dispatch("find", (by, value, self._driver), "find_element", (by, value))

    def find_elements(self, by=By.ID, value=None) -> List[WebElement]:
        return self._dispatch("find", (by, value, self._driver), "find_elements", (by, value))

    def _dispatch(self, l_call, l_args, d_call, d_args):
        getattr(self._listener, f"before_{l_call}")(*l_args)
        try:
            result = getattr(self._webelement, d_call)(*d_args)
        except Exception as exc:
            self._listener.on_exception(exc, self._driver)
            raise
        getattr(self._listener, f"after_{l_call}")(*l_args)
        return _wrap_elements(result, self._ef_driver)

    def __setattr__(self, item, value):
        if item.startswith("_") or not hasattr(self._webelement, item):
            object.__setattr__(self, item, value)
        else:
            try:
                object.__setattr__(self._webelement, item, value)
            except Exception as exc:
                self._listener.on_exception(exc, self._driver)
                raise

    def __getattr__(self, name):
        def _wrap(*args, **kwargs):
            try:
                result = attrib(*args, **kwargs)
                return _wrap_elements(result, self._ef_driver)
            except Exception as exc:
                self._listener.on_exception(exc, self._driver)
                raise

        try:
            attrib = getattr(self._webelement, name)
            return _wrap if callable(attrib) else attrib
        except Exception as exc:
            self._listener.on_exception(exc, self._driver)
            raise


# Register a virtual subclass.
WebElement.register(EventFiringWebElement)

# === NexusCore/openenv\Lib\site-packages\fontTools\misc\testTools.py ===
"""Helpers for writing unit tests."""

from collections.abc import Iterable
from io import BytesIO
import os
import re
import shutil
import sys
import tempfile
from unittest import TestCase as _TestCase
from fontTools.config import Config
from fontTools.misc.textTools import tobytes
from fontTools.misc.xmlWriter import XMLWriter


def parseXML(xmlSnippet):
    """Parses a snippet of XML.

    Input can be either a single string (unicode or UTF-8 bytes), or a
    a sequence of strings.

    The result is in the same format that would be returned by
    XMLReader, but the parser imposes no constraints on the root
    element so it can be called on small snippets of TTX files.
    """
    # To support snippets with multiple elements, we add a fake root.
    reader = TestXMLReader_()
    xml = b"<root>"
    if isinstance(xmlSnippet, bytes):
        xml += xmlSnippet
    elif isinstance(xmlSnippet, str):
        xml += tobytes(xmlSnippet, "utf-8")
    elif isinstance(xmlSnippet, Iterable):
        xml += b"".join(tobytes(s, "utf-8") for s in xmlSnippet)
    else:
        raise TypeError(
            "expected string or sequence of strings; found %r"
            % type(xmlSnippet).__name__
        )
    xml += b"</root>"
    reader.parser.Parse(xml, 1)
    return reader.root[2]


def parseXmlInto(font, parseInto, xmlSnippet):
    parsed_xml = [e for e in parseXML(xmlSnippet.strip()) if not isinstance(e, str)]
    for name, attrs, content in parsed_xml:
        parseInto.fromXML(name, attrs, content, font)
    if hasattr(parseInto, "populateDefaults"):
        parseInto.populateDefaults()
    return parseInto


class FakeFont:
    def __init__(self, glyphs):
        self.glyphOrder_ = glyphs
        self.reverseGlyphOrderDict_ = {g: i for i, g in enumerate(glyphs)}
        self.lazy = False
        self.tables = {}
        self.cfg = Config()

    def __contains__(self, tag):
        return tag in self.tables

    def __getitem__(self, tag):
        return self.tables[tag]

    def __setitem__(self, tag, table):
        self.tables[tag] = table

    def get(self, tag, default=None):
        return self.tables.get(tag, default)

    def getGlyphID(self, name):
        return self.reverseGlyphOrderDict_[name]

    def getGlyphIDMany(self, lst):
        return [self.getGlyphID(gid) for gid in lst]

    def getGlyphName(self, glyphID):
        if glyphID < len(self.glyphOrder_):
            return self.glyphOrder_[glyphID]
        else:
            return "glyph%.5d" % glyphID

    def getGlyphNameMany(self, lst):
        return [self.getGlyphName(gid) for gid in lst]

    def getGlyphOrder(self):
        return self.glyphOrder_

    def getReverseGlyphMap(self):
        return self.reverseGlyphOrderDict_

    def getGlyphNames(self):
        return sorted(self.getGlyphOrder())


class TestXMLReader_(object):
    def __init__(self):
        from xml.parsers.expat import ParserCreate

        self.parser = ParserCreate()
        self.parser.StartElementHandler = self.startElement_
        self.parser.EndElementHandler = self.endElement_
        self.parser.CharacterDataHandler = self.addCharacterData_
        self.root = None
        self.stack = []

    def startElement_(self, name, attrs):
        element = (name, attrs, [])
        if self.stack:
            self.stack[-1][2].append(element)
        else:
            self.root = element
        self.stack.append(element)

    def endElement_(self, name):
        self.stack.pop()

    def addCharacterData_(self, data):
        self.stack[-1][2].append(data)


def makeXMLWriter(newlinestr="\n"):
    # don't write OS-specific new lines
    writer = XMLWriter(BytesIO(), newlinestr=newlinestr)
    # erase XML declaration
    writer.file.seek(0)
    writer.file.truncate()
    return writer


def getXML(func, ttFont=None):
    """Call the passed toXML function and return the written content as a
    list of lines (unicode strings).
    Result is stripped of XML declaration and OS-specific newline characters.
    """
    writer = makeXMLWriter()
    func(writer, ttFont)
    xml = writer.file.getvalue().decode("utf-8")
    # toXML methods must always end with a writer.newline()
    assert xml.endswith("\n")
    return xml.splitlines()


def stripVariableItemsFromTTX(
    string: str,
    ttLibVersion: bool = True,
    checkSumAdjustment: bool = True,
    modified: bool = True,
    created: bool = True,
    sfntVersion: bool = False,  # opt-in only
) -> str:
    """Strip stuff like ttLibVersion, checksums, timestamps, etc. from TTX dumps."""
    # ttlib changes with the fontTools version
    if ttLibVersion:
        string = re.sub(' ttLibVersion="[^"]+"', "", string)
    # sometimes (e.g. some subsetter tests) we don't care whether it's OTF or TTF
    if sfntVersion:
        string = re.sub(' sfntVersion="[^"]+"', "", string)
    # head table checksum and creation and mod date changes with each save.
    if checkSumAdjustment:
        string = re.sub('<checkSumAdjustment value="[^"]+"/>', "", string)
    if modified:
        string = re.sub('<modified value="[^"]+"/>', "", string)
    if created:
        string = re.sub('<created value="[^"]+"/>', "", string)
    return string


class MockFont(object):
    """A font-like object that automatically adds any looked up glyphname
    to its glyphOrder."""

    def __init__(self):
        self._glyphOrder = [".notdef"]

        class AllocatingDict(dict):
            def __missing__(reverseDict, key):
                self._glyphOrder.append(key)
                gid = len(reverseDict)
                reverseDict[key] = gid
                return gid

        self._reverseGlyphOrder = AllocatingDict({".notdef": 0})
        self.lazy = False

    def getGlyphID(self, glyph):
        gid = self._reverseGlyphOrder[glyph]
        return gid

    def getReverseGlyphMap(self):
        return self._reverseGlyphOrder

    def getGlyphName(self, gid):
        return self._glyphOrder[gid]

    def getGlyphOrder(self):
        return self._glyphOrder


class TestCase(_TestCase):
    def __init__(self, methodName):
        _TestCase.__init__(self, methodName)
        # Python 3 renamed assertRaisesRegexp to assertRaisesRegex,
        # and fires deprecation warnings if a program uses the old name.
        if not hasattr(self, "assertRaisesRegex"):
            self.assertRaisesRegex = self.assertRaisesRegexp


class DataFilesHandler(TestCase):
    def setUp(self):
        self.tempdir = None
        self.num_tempfiles = 0

    def tearDown(self):
        if self.tempdir:
            shutil.rmtree(self.tempdir)

    def getpath(self, testfile):
        folder = os.path.dirname(sys.modules[self.__module__].__file__)
        return os.path.join(folder, "data", testfile)

    def temp_dir(self):
        if not self.tempdir:
            self.tempdir = tempfile.mkdtemp()

    def temp_font(self, font_path, file_name):
        self.temp_dir()
        temppath = os.path.join(self.tempdir, file_name)
        shutil.copy2(font_path, temppath)
        return temppath

# === NexusCore/openenv\Lib\site-packages\google\protobuf\message_factory.py ===
# Protocol Buffers - Google's data interchange format
# Copyright 2008 Google Inc.  All rights reserved.
#
# Use of this source code is governed by a BSD-style
# license that can be found in the LICENSE file or at
# https://developers.google.com/open-source/licenses/bsd

"""Provides a factory class for generating dynamic messages.

The easiest way to use this class is if you have access to the FileDescriptor
protos containing the messages you want to create you can just do the following:

message_classes = message_factory.GetMessages(iterable_of_file_descriptors)
my_proto_instance = message_classes['some.proto.package.MessageName']()
"""

__author__ = 'matthewtoia@google.com (Matt Toia)'

import warnings

from google.protobuf.internal import api_implementation
from google.protobuf import descriptor_pool
from google.protobuf import message

if api_implementation.Type() == 'python':
  from google.protobuf.internal import python_message as message_impl
else:
  from google.protobuf.pyext import cpp_message as message_impl  # pylint: disable=g-import-not-at-top


# The type of all Message classes.
_GENERATED_PROTOCOL_MESSAGE_TYPE = message_impl.GeneratedProtocolMessageType


def GetMessageClass(descriptor):
  """Obtains a proto2 message class based on the passed in descriptor.

  Passing a descriptor with a fully qualified name matching a previous
  invocation will cause the same class to be returned.

  Args:
    descriptor: The descriptor to build from.

  Returns:
    A class describing the passed in descriptor.
  """
  concrete_class = getattr(descriptor, '_concrete_class', None)
  if concrete_class:
    return concrete_class
  return _InternalCreateMessageClass(descriptor)


def GetMessageClassesForFiles(files, pool):
  """Gets all the messages from specified files.

  This will find and resolve dependencies, failing if the descriptor
  pool cannot satisfy them.

  Args:
    files: The file names to extract messages from.
    pool: The descriptor pool to find the files including the dependent
      files.

  Returns:
    A dictionary mapping proto names to the message classes.
  """
  result = {}
  for file_name in files:
    file_desc = pool.FindFileByName(file_name)
    for desc in file_desc.message_types_by_name.values():
      result[desc.full_name] = GetMessageClass(desc)

    # While the extension FieldDescriptors are created by the descriptor pool,
    # the python classes created in the factory need them to be registered
    # explicitly, which is done below.
    #
    # The call to RegisterExtension will specifically check if the
    # extension was already registered on the object and either
    # ignore the registration if the original was the same, or raise
    # an error if they were different.

    for extension in file_desc.extensions_by_name.values():
      extended_class = GetMessageClass(extension.containing_type)
      if api_implementation.Type() != 'python':
        # TODO: Remove this check here. Duplicate extension
        # register check should be in descriptor_pool.
        if extension is not pool.FindExtensionByNumber(
            extension.containing_type, extension.number
        ):
          raise ValueError('Double registration of Extensions')
      # Recursively load protos for extension field, in order to be able to
      # fully represent the extension. This matches the behavior for regular
      # fields too.
      if extension.message_type:
        GetMessageClass(extension.message_type)
  return result


def _InternalCreateMessageClass(descriptor):
  """Builds a proto2 message class based on the passed in descriptor.

  Args:
    descriptor: The descriptor to build from.

  Returns:
    A class describing the passed in descriptor.
  """
  descriptor_name = descriptor.name
  result_class = _GENERATED_PROTOCOL_MESSAGE_TYPE(
      descriptor_name,
      (message.Message,),
      {
          'DESCRIPTOR': descriptor,
          # If module not set, it wrongly points to message_factory module.
          '__module__': None,
      })
  for field in descriptor.fields:
    if field.message_type:
      GetMessageClass(field.message_type)
  for extension in result_class.DESCRIPTOR.extensions:
    extended_class = GetMessageClass(extension.containing_type)
    if api_implementation.Type() != 'python':
      # TODO: Remove this check here. Duplicate extension
      # register check should be in descriptor_pool.
      pool = extension.containing_type.file.pool
      if extension is not pool.FindExtensionByNumber(
          extension.containing_type, extension.number
      ):
        raise ValueError('Double registration of Extensions')
    if extension.message_type:
      GetMessageClass(extension.message_type)
  return result_class


# Deprecated. Please use GetMessageClass() or GetMessageClassesForFiles()
# method above instead.
class MessageFactory(object):
  """Factory for creating Proto2 messages from descriptors in a pool."""

  def __init__(self, pool=None):
    """Initializes a new factory."""
    self.pool = pool or descriptor_pool.DescriptorPool()

  def GetPrototype(self, descriptor):
    """Obtains a proto2 message class based on the passed in descriptor.

    Passing a descriptor with a fully qualified name matching a previous
    invocation will cause the same class to be returned.

    Args:
      descriptor: The descriptor to build from.

    Returns:
      A class describing the passed in descriptor.
    """
    warnings.warn(
        'MessageFactory class is deprecated. Please use '
        'GetMessageClass() instead of MessageFactory.GetPrototype. '
        'MessageFactory class will be removed after 2024.',
        stacklevel=2,
    )
    return GetMessageClass(descriptor)

  def CreatePrototype(self, descriptor):
    """Builds a proto2 message class based on the passed in descriptor.

    Don't call this function directly, it always creates a new class. Call
    GetMessageClass() instead.

    Args:
      descriptor: The descriptor to build from.

    Returns:
      A class describing the passed in descriptor.
    """
    warnings.warn(
        'Directly call CreatePrototype is wrong. Please use '
        'GetMessageClass() method instead. Directly use '
        'CreatePrototype will raise error after July 2023.',
        stacklevel=2,
    )
    return _InternalCreateMessageClass(descriptor)

  def GetMessages(self, files):
    """Gets all the messages from a specified file.

    This will find and resolve dependencies, failing if the descriptor
    pool cannot satisfy them.

    Args:
      files: The file names to extract messages from.

    Returns:
      A dictionary mapping proto names to the message classes. This will include
      any dependent messages as well as any messages defined in the same file as
      a specified message.
    """
    warnings.warn(
        'MessageFactory class is deprecated. Please use '
        'GetMessageClassesForFiles() instead of '
        'MessageFactory.GetMessages(). MessageFactory class '
        'will be removed after 2024.',
        stacklevel=2,
    )
    return GetMessageClassesForFiles(files, self.pool)


def GetMessages(file_protos, pool=None):
  """Builds a dictionary of all the messages available in a set of files.

  Args:
    file_protos: Iterable of FileDescriptorProto to build messages out of.
    pool: The descriptor pool to add the file protos.

  Returns:
    A dictionary mapping proto names to the message classes. This will include
    any dependent messages as well as any messages defined in the same file as
    a specified message.
  """
  # The cpp implementation of the protocol buffer library requires to add the
  # message in topological order of the dependency graph.
  des_pool = pool or descriptor_pool.DescriptorPool()
  file_by_name = {file_proto.name: file_proto for file_proto in file_protos}
  def _AddFile(file_proto):
    for dependency in file_proto.dependency:
      if dependency in file_by_name:
        # Remove from elements to be visited, in order to cut cycles.
        _AddFile(file_by_name.pop(dependency))
    des_pool.Add(file_proto)
  while file_by_name:
    _AddFile(file_by_name.popitem()[1])
  return GetMessageClassesForFiles(
      [file_proto.name for file_proto in file_protos], des_pool)

# === NexusCore/openenv\Lib\site-packages\openai\cli\_cli.py ===
from __future__ import annotations

import sys
import logging
import argparse
from typing import Any, List, Type, Optional
from typing_extensions import ClassVar

import httpx
import pydantic

import openai

from . import _tools
from .. import _ApiType, __version__
from ._api import register_commands
from ._utils import can_use_http2
from ._errors import CLIError, display_error
from .._compat import PYDANTIC_V2, ConfigDict, model_parse
from .._models import BaseModel
from .._exceptions import APIError

logger = logging.getLogger()
formatter = logging.Formatter("[%(asctime)s] %(message)s")
handler = logging.StreamHandler(sys.stderr)
handler.setFormatter(formatter)
logger.addHandler(handler)


class Arguments(BaseModel):
    if PYDANTIC_V2:
        model_config: ClassVar[ConfigDict] = ConfigDict(
            extra="ignore",
        )
    else:

        class Config(pydantic.BaseConfig):  # type: ignore
            extra: Any = pydantic.Extra.ignore  # type: ignore

    verbosity: int
    version: Optional[str] = None

    api_key: Optional[str]
    api_base: Optional[str]
    organization: Optional[str]
    proxy: Optional[List[str]]
    api_type: Optional[_ApiType] = None
    api_version: Optional[str] = None

    # azure
    azure_endpoint: Optional[str] = None
    azure_ad_token: Optional[str] = None

    # internal, set by subparsers to parse their specific args
    args_model: Optional[Type[BaseModel]] = None

    # internal, used so that subparsers can forward unknown arguments
    unknown_args: List[str] = []
    allow_unknown_args: bool = False


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=None, prog="openai")
    parser.add_argument(
        "-v",
        "--verbose",
        action="count",
        dest="verbosity",
        default=0,
        help="Set verbosity.",
    )
    parser.add_argument("-b", "--api-base", help="What API base url to use.")
    parser.add_argument("-k", "--api-key", help="What API key to use.")
    parser.add_argument("-p", "--proxy", nargs="+", help="What proxy to use.")
    parser.add_argument(
        "-o",
        "--organization",
        help="Which organization to run as (will use your default organization if not specified)",
    )
    parser.add_argument(
        "-t",
        "--api-type",
        type=str,
        choices=("openai", "azure"),
        help="The backend API to call, must be `openai` or `azure`",
    )
    parser.add_argument(
        "--api-version",
        help="The Azure API version, e.g. 'https://learn.microsoft.com/en-us/azure/ai-services/openai/reference#rest-api-versioning'",
    )

    # azure
    parser.add_argument(
        "--azure-endpoint",
        help="The Azure endpoint, e.g. 'https://endpoint.openai.azure.com'",
    )
    parser.add_argument(
        "--azure-ad-token",
        help="A token from Azure Active Directory, https://www.microsoft.com/en-us/security/business/identity-access/microsoft-entra-id",
    )

    # prints the package version
    parser.add_argument(
        "-V",
        "--version",
        action="version",
        version="%(prog)s " + __version__,
    )

    def help() -> None:
        parser.print_help()

    parser.set_defaults(func=help)

    subparsers = parser.add_subparsers()
    sub_api = subparsers.add_parser("api", help="Direct API calls")

    register_commands(sub_api)

    sub_tools = subparsers.add_parser("tools", help="Client side tools for convenience")
    _tools.register_commands(sub_tools, subparsers)

    return parser


def main() -> int:
    try:
        _main()
    except (APIError, CLIError, pydantic.ValidationError) as err:
        display_error(err)
        return 1
    except KeyboardInterrupt:
        sys.stderr.write("\n")
        return 1
    return 0


def _parse_args(parser: argparse.ArgumentParser) -> tuple[argparse.Namespace, Arguments, list[str]]:
    # argparse by default will strip out the `--` but we want to keep it for unknown arguments
    if "--" in sys.argv:
        idx = sys.argv.index("--")
        known_args = sys.argv[1:idx]
        unknown_args = sys.argv[idx:]
    else:
        known_args = sys.argv[1:]
        unknown_args = []

    parsed, remaining_unknown = parser.parse_known_args(known_args)

    # append any remaining unknown arguments from the initial parsing
    remaining_unknown.extend(unknown_args)

    args = model_parse(Arguments, vars(parsed))
    if not args.allow_unknown_args:
        # we have to parse twice to ensure any unknown arguments
        # result in an error if that behaviour is desired
        parser.parse_args()

    return parsed, args, remaining_unknown


def _main() -> None:
    parser = _build_parser()
    parsed, args, unknown = _parse_args(parser)

    if args.verbosity != 0:
        sys.stderr.write("Warning: --verbosity isn't supported yet\n")

    proxies: dict[str, httpx.BaseTransport] = {}
    if args.proxy is not None:
        for proxy in args.proxy:
            key = "https://" if proxy.startswith("https") else "http://"
            if key in proxies:
                raise CLIError(f"Multiple {key} proxies given - only the last one would be used")

            proxies[key] = httpx.HTTPTransport(proxy=httpx.Proxy(httpx.URL(proxy)))

    http_client = httpx.Client(
        mounts=proxies or None,
        http2=can_use_http2(),
    )
    openai.http_client = http_client

    if args.organization:
        openai.organization = args.organization

    if args.api_key:
        openai.api_key = args.api_key

    if args.api_base:
        openai.base_url = args.api_base

    # azure
    if args.api_type is not None:
        openai.api_type = args.api_type

    if args.azure_endpoint is not None:
        openai.azure_endpoint = args.azure_endpoint

    if args.api_version is not None:
        openai.api_version = args.api_version

    if args.azure_ad_token is not None:
        openai.azure_ad_token = args.azure_ad_token

    try:
        if args.args_model:
            parsed.func(
                model_parse(
                    args.args_model,
                    {
                        **{
                            # we omit None values so that they can be defaulted to `NotGiven`
                            # and we'll strip it from the API request
                            key: value
                            for key, value in vars(parsed).items()
                            if value is not None
                        },
                        "unknown_args": unknown,
                    },
                )
            )
        else:
            parsed.func()
    finally:
        try:
            http_client.close()
        except Exception:
            pass


if __name__ == "__main__":
    sys.exit(main())

# === NexusCore/openenv\Lib\site-packages\tornado\test\log_test.py ===
#
# Copyright 2012 Facebook
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
import contextlib
import glob
import logging
import os
import re
import subprocess
import sys
import tempfile
import unittest
import warnings

from tornado.escape import utf8
from tornado.log import LogFormatter, define_logging_options, enable_pretty_logging
from tornado.options import OptionParser
from tornado.util import basestring_type


@contextlib.contextmanager
def ignore_bytes_warning():
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", category=BytesWarning)
        yield


class LogFormatterTest(unittest.TestCase):
    # Matches the output of a single logging call (which may be multiple lines
    # if a traceback was included, so we use the DOTALL option)
    LINE_RE = re.compile(
        b"(?s)\x01\\[E [0-9]{6} [0-9]{2}:[0-9]{2}:[0-9]{2} log_test:[0-9]+\\]\x02 (.*)"
    )

    def setUp(self):
        self.formatter = LogFormatter(color=False)
        # Fake color support.  We can't guarantee anything about the $TERM
        # variable when the tests are run, so just patch in some values
        # for testing.  (testing with color off fails to expose some potential
        # encoding issues from the control characters)
        self.formatter._colors = {logging.ERROR: "\u0001"}
        self.formatter._normal = "\u0002"
        # construct a Logger directly to bypass getLogger's caching
        self.logger = logging.Logger("LogFormatterTest")
        self.logger.propagate = False
        self.tempdir = tempfile.mkdtemp()
        self.filename = os.path.join(self.tempdir, "log.out")
        self.handler = self.make_handler(self.filename)
        self.handler.setFormatter(self.formatter)
        self.logger.addHandler(self.handler)

    def tearDown(self):
        self.handler.close()
        os.unlink(self.filename)
        os.rmdir(self.tempdir)

    def make_handler(self, filename):
        return logging.FileHandler(filename, encoding="utf-8")

    def get_output(self):
        with open(self.filename, "rb") as f:
            line = f.read().strip()
            m = LogFormatterTest.LINE_RE.match(line)
            if m:
                return m.group(1)
            else:
                raise Exception("output didn't match regex: %r" % line)

    def test_basic_logging(self):
        self.logger.error("foo")
        self.assertEqual(self.get_output(), b"foo")

    def test_bytes_logging(self):
        with ignore_bytes_warning():
            # This will be "\xe9" on python 2 or "b'\xe9'" on python 3
            self.logger.error(b"\xe9")
            self.assertEqual(self.get_output(), utf8(repr(b"\xe9")))

    def test_utf8_logging(self):
        with ignore_bytes_warning():
            self.logger.error("\u00e9".encode())
        if issubclass(bytes, basestring_type):
            # on python 2, utf8 byte strings (and by extension ascii byte
            # strings) are passed through as-is.
            self.assertEqual(self.get_output(), utf8("\u00e9"))
        else:
            # on python 3, byte strings always get repr'd even if
            # they're ascii-only, so this degenerates into another
            # copy of test_bytes_logging.
            self.assertEqual(self.get_output(), utf8(repr(utf8("\u00e9"))))

    def test_bytes_exception_logging(self):
        try:
            raise Exception(b"\xe9")
        except Exception:
            self.logger.exception("caught exception")
        # This will be "Exception: \xe9" on python 2 or
        # "Exception: b'\xe9'" on python 3.
        output = self.get_output()
        self.assertRegex(output, rb"Exception.*\\xe9")
        # The traceback contains newlines, which should not have been escaped.
        self.assertNotIn(rb"\n", output)

    def test_unicode_logging(self):
        self.logger.error("\u00e9")
        self.assertEqual(self.get_output(), utf8("\u00e9"))


class EnablePrettyLoggingTest(unittest.TestCase):
    def setUp(self):
        super().setUp()
        self.options = OptionParser()
        define_logging_options(self.options)
        self.logger = logging.Logger("tornado.test.log_test.EnablePrettyLoggingTest")
        self.logger.propagate = False

    def test_log_file(self):
        tmpdir = tempfile.mkdtemp()
        try:
            self.options.log_file_prefix = tmpdir + "/test_log"
            enable_pretty_logging(options=self.options, logger=self.logger)
            self.assertEqual(1, len(self.logger.handlers))
            self.logger.error("hello")
            self.logger.handlers[0].flush()
            filenames = glob.glob(tmpdir + "/test_log*")
            self.assertEqual(1, len(filenames))
            with open(filenames[0], encoding="utf-8") as f:
                self.assertRegex(f.read(), r"^\[E [^]]*\] hello$")
        finally:
            for handler in self.logger.handlers:
                handler.flush()
                handler.close()
            for filename in glob.glob(tmpdir + "/test_log*"):
                os.unlink(filename)
            os.rmdir(tmpdir)

    def test_log_file_with_timed_rotating(self):
        tmpdir = tempfile.mkdtemp()
        try:
            self.options.log_file_prefix = tmpdir + "/test_log"
            self.options.log_rotate_mode = "time"
            enable_pretty_logging(options=self.options, logger=self.logger)
            self.logger.error("hello")
            self.logger.handlers[0].flush()
            filenames = glob.glob(tmpdir + "/test_log*")
            self.assertEqual(1, len(filenames))
            with open(filenames[0], encoding="utf-8") as f:
                self.assertRegex(f.read(), r"^\[E [^]]*\] hello$")
        finally:
            for handler in self.logger.handlers:
                handler.flush()
                handler.close()
            for filename in glob.glob(tmpdir + "/test_log*"):
                os.unlink(filename)
            os.rmdir(tmpdir)

    def test_wrong_rotate_mode_value(self):
        try:
            self.options.log_file_prefix = "some_path"
            self.options.log_rotate_mode = "wrong_mode"
            self.assertRaises(
                ValueError,
                enable_pretty_logging,
                options=self.options,
                logger=self.logger,
            )
        finally:
            for handler in self.logger.handlers:
                handler.flush()
                handler.close()


class LoggingOptionTest(unittest.TestCase):
    """Test the ability to enable and disable Tornado's logging hooks."""

    def logs_present(self, statement, args=None):
        # Each test may manipulate and/or parse the options and then logs
        # a line at the 'info' level.  This level is ignored in the
        # logging module by default, but Tornado turns it on by default
        # so it is the easiest way to tell whether tornado's logging hooks
        # ran.
        IMPORT = "from tornado.options import options, parse_command_line"
        LOG_INFO = 'import logging; logging.info("hello")'
        program = ";".join([IMPORT, statement, LOG_INFO])
        proc = subprocess.Popen(
            [sys.executable, "-c", program] + (args or []),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
        stdout, stderr = proc.communicate()
        self.assertEqual(proc.returncode, 0, "process failed: %r" % stdout)
        return b"hello" in stdout

    def test_default(self):
        self.assertFalse(self.logs_present("pass"))

    def test_tornado_default(self):
        self.assertTrue(self.logs_present("parse_command_line()"))

    def test_disable_command_line(self):
        self.assertFalse(self.logs_present("parse_command_line()", ["--logging=none"]))

    def test_disable_command_line_case_insensitive(self):
        self.assertFalse(self.logs_present("parse_command_line()", ["--logging=None"]))

    def test_disable_code_string(self):
        self.assertFalse(
            self.logs_present('options.logging = "none"; parse_command_line()')
        )

    def test_disable_code_none(self):
        self.assertFalse(
            self.logs_present("options.logging = None; parse_command_line()")
        )

    def test_disable_override(self):
        # command line trumps code defaults
        self.assertTrue(
            self.logs_present(
                "options.logging = None; parse_command_line()", ["--logging=info"]
            )
        )

# === NexusCore/myenv\Lib\site-packages\pip\_vendor\rich\highlighter.py ===
import re
from abc import ABC, abstractmethod
from typing import List, Union

from .text import Span, Text


def _combine_regex(*regexes: str) -> str:
    """Combine a number of regexes in to a single regex.

    Returns:
        str: New regex with all regexes ORed together.
    """
    return "|".join(regexes)


class Highlighter(ABC):
    """Abstract base class for highlighters."""

    def __call__(self, text: Union[str, Text]) -> Text:
        """Highlight a str or Text instance.

        Args:
            text (Union[str, ~Text]): Text to highlight.

        Raises:
            TypeError: If not called with text or str.

        Returns:
            Text: A test instance with highlighting applied.
        """
        if isinstance(text, str):
            highlight_text = Text(text)
        elif isinstance(text, Text):
            highlight_text = text.copy()
        else:
            raise TypeError(f"str or Text instance required, not {text!r}")
        self.highlight(highlight_text)
        return highlight_text

    @abstractmethod
    def highlight(self, text: Text) -> None:
        """Apply highlighting in place to text.

        Args:
            text (~Text): A text object highlight.
        """


class NullHighlighter(Highlighter):
    """A highlighter object that doesn't highlight.

    May be used to disable highlighting entirely.

    """

    def highlight(self, text: Text) -> None:
        """Nothing to do"""


class RegexHighlighter(Highlighter):
    """Applies highlighting from a list of regular expressions."""

    highlights: List[str] = []
    base_style: str = ""

    def highlight(self, text: Text) -> None:
        """Highlight :class:`rich.text.Text` using regular expressions.

        Args:
            text (~Text): Text to highlighted.

        """

        highlight_regex = text.highlight_regex
        for re_highlight in self.highlights:
            highlight_regex(re_highlight, style_prefix=self.base_style)


class ReprHighlighter(RegexHighlighter):
    """Highlights the text typically produced from ``__repr__`` methods."""

    base_style = "repr."
    highlights = [
        r"(?P<tag_start><)(?P<tag_name>[-\w.:|]*)(?P<tag_contents>[\w\W]*)(?P<tag_end>>)",
        r'(?P<attrib_name>[\w_]{1,50})=(?P<attrib_value>"?[\w_]+"?)?',
        r"(?P<brace>[][{}()])",
        _combine_regex(
            r"(?P<ipv4>[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3})",
            r"(?P<ipv6>([A-Fa-f0-9]{1,4}::?){1,7}[A-Fa-f0-9]{1,4})",
            r"(?P<eui64>(?:[0-9A-Fa-f]{1,2}-){7}[0-9A-Fa-f]{1,2}|(?:[0-9A-Fa-f]{1,2}:){7}[0-9A-Fa-f]{1,2}|(?:[0-9A-Fa-f]{4}\.){3}[0-9A-Fa-f]{4})",
            r"(?P<eui48>(?:[0-9A-Fa-f]{1,2}-){5}[0-9A-Fa-f]{1,2}|(?:[0-9A-Fa-f]{1,2}:){5}[0-9A-Fa-f]{1,2}|(?:[0-9A-Fa-f]{4}\.){2}[0-9A-Fa-f]{4})",
            r"(?P<uuid>[a-fA-F0-9]{8}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{12})",
            r"(?P<call>[\w.]*?)\(",
            r"\b(?P<bool_true>True)\b|\b(?P<bool_false>False)\b|\b(?P<none>None)\b",
            r"(?P<ellipsis>\.\.\.)",
            r"(?P<number_complex>(?<!\w)(?:\-?[0-9]+\.?[0-9]*(?:e[-+]?\d+?)?)(?:[-+](?:[0-9]+\.?[0-9]*(?:e[-+]?\d+)?))?j)",
            r"(?P<number>(?<!\w)\-?[0-9]+\.?[0-9]*(e[-+]?\d+?)?\b|0x[0-9a-fA-F]*)",
            r"(?P<path>\B(/[-\w._+]+)*\/)(?P<filename>[-\w._+]*)?",
            r"(?<![\\\w])(?P<str>b?'''.*?(?<!\\)'''|b?'.*?(?<!\\)'|b?\"\"\".*?(?<!\\)\"\"\"|b?\".*?(?<!\\)\")",
            r"(?P<url>(file|https|http|ws|wss)://[-0-9a-zA-Z$_+!`(),.?/;:&=%#~@]*)",
        ),
    ]


class JSONHighlighter(RegexHighlighter):
    """Highlights JSON"""

    # Captures the start and end of JSON strings, handling escaped quotes
    JSON_STR = r"(?<![\\\w])(?P<str>b?\".*?(?<!\\)\")"
    JSON_WHITESPACE = {" ", "\n", "\r", "\t"}

    base_style = "json."
    highlights = [
        _combine_regex(
            r"(?P<brace>[\{\[\(\)\]\}])",
            r"\b(?P<bool_true>true)\b|\b(?P<bool_false>false)\b|\b(?P<null>null)\b",
            r"(?P<number>(?<!\w)\-?[0-9]+\.?[0-9]*(e[\-\+]?\d+?)?\b|0x[0-9a-fA-F]*)",
            JSON_STR,
        ),
    ]

    def highlight(self, text: Text) -> None:
        super().highlight(text)

        # Additional work to handle highlighting JSON keys
        plain = text.plain
        append = text.spans.append
        whitespace = self.JSON_WHITESPACE
        for match in re.finditer(self.JSON_STR, plain):
            start, end = match.span()
            cursor = end
            while cursor < len(plain):
                char = plain[cursor]
                cursor += 1
                if char == ":":
                    append(Span(start, end, "json.key"))
                elif char in whitespace:
                    continue
                break


class ISO8601Highlighter(RegexHighlighter):
    """Highlights the ISO8601 date time strings.
    Regex reference: https://www.oreilly.com/library/view/regular-expressions-cookbook/9781449327453/ch04s07.html
    """

    base_style = "iso8601."
    highlights = [
        #
        # Dates
        #
        # Calendar month (e.g. 2008-08). The hyphen is required
        r"^(?P<year>[0-9]{4})-(?P<month>1[0-2]|0[1-9])$",
        # Calendar date w/o hyphens (e.g. 20080830)
        r"^(?P<date>(?P<year>[0-9]{4})(?P<month>1[0-2]|0[1-9])(?P<day>3[01]|0[1-9]|[12][0-9]))$",
        # Ordinal date (e.g. 2008-243). The hyphen is optional
        r"^(?P<date>(?P<year>[0-9]{4})-?(?P<day>36[0-6]|3[0-5][0-9]|[12][0-9]{2}|0[1-9][0-9]|00[1-9]))$",
        #
        # Weeks
        #
        # Week of the year (e.g., 2008-W35). The hyphen is optional
        r"^(?P<date>(?P<year>[0-9]{4})-?W(?P<week>5[0-3]|[1-4][0-9]|0[1-9]))$",
        # Week date (e.g., 2008-W35-6). The hyphens are optional
        r"^(?P<date>(?P<year>[0-9]{4})-?W(?P<week>5[0-3]|[1-4][0-9]|0[1-9])-?(?P<day>[1-7]))$",
        #
        # Times
        #
        # Hours and minutes (e.g., 17:21). The colon is optional
        r"^(?P<time>(?P<hour>2[0-3]|[01][0-9]):?(?P<minute>[0-5][0-9]))$",
        # Hours, minutes, and seconds w/o colons (e.g., 172159)
        r"^(?P<time>(?P<hour>2[0-3]|[01][0-9])(?P<minute>[0-5][0-9])(?P<second>[0-5][0-9]))$",
        # Time zone designator (e.g., Z, +07 or +07:00). The colons and the minutes are optional
        r"^(?P<timezone>(Z|[+-](?:2[0-3]|[01][0-9])(?::?(?:[0-5][0-9]))?))$",
        # Hours, minutes, and seconds with time zone designator (e.g., 17:21:59+07:00).
        # All the colons are optional. The minutes in the time zone designator are also optional
        r"^(?P<time>(?P<hour>2[0-3]|[01][0-9])(?P<minute>[0-5][0-9])(?P<second>[0-5][0-9]))(?P<timezone>Z|[+-](?:2[0-3]|[01][0-9])(?::?(?:[0-5][0-9]))?)$",
        #
        # Date and Time
        #
        # Calendar date with hours, minutes, and seconds (e.g., 2008-08-30 17:21:59 or 20080830 172159).
        # A space is required between the date and the time. The hyphens and colons are optional.
        # This regex matches dates and times that specify some hyphens or colons but omit others.
        # This does not follow ISO 8601
        r"^(?P<date>(?P<year>[0-9]{4})(?P<hyphen>-)?(?P<month>1[0-2]|0[1-9])(?(hyphen)-)(?P<day>3[01]|0[1-9]|[12][0-9])) (?P<time>(?P<hour>2[0-3]|[01][0-9])(?(hyphen):)(?P<minute>[0-5][0-9])(?(hyphen):)(?P<second>[0-5][0-9]))$",
        #
        # XML Schema dates and times
        #
        # Date, with optional time zone (e.g., 2008-08-30 or 2008-08-30+07:00).
        # Hyphens are required. This is the XML Schema 'date' type
        r"^(?P<date>(?P<year>-?(?:[1-9][0-9]*)?[0-9]{4})-(?P<month>1[0-2]|0[1-9])-(?P<day>3[01]|0[1-9]|[12][0-9]))(?P<timezone>Z|[+-](?:2[0-3]|[01][0-9]):[0-5][0-9])?$",
        # Time, with optional fractional seconds and time zone (e.g., 01:45:36 or 01:45:36.123+07:00).
        # There is no limit on the number of digits for the fractional seconds. This is the XML Schema 'time' type
        r"^(?P<time>(?P<hour>2[0-3]|[01][0-9]):(?P<minute>[0-5][0-9]):(?P<second>[0-5][0-9])(?P<frac>\.[0-9]+)?)(?P<timezone>Z|[+-](?:2[0-3]|[01][0-9]):[0-5][0-9])?$",
        # Date and time, with optional fractional seconds and time zone (e.g., 2008-08-30T01:45:36 or 2008-08-30T01:45:36.123Z).
        # This is the XML Schema 'dateTime' type
        r"^(?P<date>(?P<year>-?(?:[1-9][0-9]*)?[0-9]{4})-(?P<month>1[0-2]|0[1-9])-(?P<day>3[01]|0[1-9]|[12][0-9]))T(?P<time>(?P<hour>2[0-3]|[01][0-9]):(?P<minute>[0-5][0-9]):(?P<second>[0-5][0-9])(?P<ms>\.[0-9]+)?)(?P<timezone>Z|[+-](?:2[0-3]|[01][0-9]):[0-5][0-9])?$",
    ]


if __name__ == "__main__":  # pragma: no cover
    from .console import Console

    console = Console()
    console.print("[bold green]hello world![/bold green]")
    console.print("'[bold green]hello world![/bold green]'")

    console.print(" /foo")
    console.print("/foo/")
    console.print("/foo/bar")
    console.print("foo/bar/baz")

    console.print("/foo/bar/baz?foo=bar+egg&egg=baz")
    console.print("/foo/bar/baz/")
    console.print("/foo/bar/baz/egg")
    console.print("/foo/bar/baz/egg.py")
    console.print("/foo/bar/baz/egg.py word")
    console.print(" /foo/bar/baz/egg.py word")
    console.print("foo /foo/bar/baz/egg.py word")
    console.print("foo /foo/bar/ba._++z/egg+.py word")
    console.print("https://example.org?foo=bar#header")

    console.print(1234567.34)
    console.print(1 / 2)
    console.print(-1 / 123123123123)

    console.print(
        "127.0.1.1 bar 192.168.1.4 2001:0db8:85a3:0000:0000:8a2e:0370:7334 foo"
    )
    import json

    console.print_json(json.dumps(obj={"name": "apple", "count": 1}), indent=None)

# === NexusCore/openenv\Lib\site-packages\rich\highlighter.py ===
import re
from abc import ABC, abstractmethod
from typing import List, Union

from .text import Span, Text


def _combine_regex(*regexes: str) -> str:
    """Combine a number of regexes in to a single regex.

    Returns:
        str: New regex with all regexes ORed together.
    """
    return "|".join(regexes)


class Highlighter(ABC):
    """Abstract base class for highlighters."""

    def __call__(self, text: Union[str, Text]) -> Text:
        """Highlight a str or Text instance.

        Args:
            text (Union[str, ~Text]): Text to highlight.

        Raises:
            TypeError: If not called with text or str.

        Returns:
            Text: A test instance with highlighting applied.
        """
        if isinstance(text, str):
            highlight_text = Text(text)
        elif isinstance(text, Text):
            highlight_text = text.copy()
        else:
            raise TypeError(f"str or Text instance required, not {text!r}")
        self.highlight(highlight_text)
        return highlight_text

    @abstractmethod
    def highlight(self, text: Text) -> None:
        """Apply highlighting in place to text.

        Args:
            text (~Text): A text object highlight.
        """


class NullHighlighter(Highlighter):
    """A highlighter object that doesn't highlight.

    May be used to disable highlighting entirely.

    """

    def highlight(self, text: Text) -> None:
        """Nothing to do"""


class RegexHighlighter(Highlighter):
    """Applies highlighting from a list of regular expressions."""

    highlights: List[str] = []
    base_style: str = ""

    def highlight(self, text: Text) -> None:
        """Highlight :class:`rich.text.Text` using regular expressions.

        Args:
            text (~Text): Text to highlighted.

        """

        highlight_regex = text.highlight_regex
        for re_highlight in self.highlights:
            highlight_regex(re_highlight, style_prefix=self.base_style)


class ReprHighlighter(RegexHighlighter):
    """Highlights the text typically produced from ``__repr__`` methods."""

    base_style = "repr."
    highlights = [
        r"(?P<tag_start><)(?P<tag_name>[-\w.:|]*)(?P<tag_contents>[\w\W]*)(?P<tag_end>>)",
        r'(?P<attrib_name>[\w_]{1,50})=(?P<attrib_value>"?[\w_]+"?)?',
        r"(?P<brace>[][{}()])",
        _combine_regex(
            r"(?P<ipv4>[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3})",
            r"(?P<ipv6>([A-Fa-f0-9]{1,4}::?){1,7}[A-Fa-f0-9]{1,4})",
            r"(?P<eui64>(?:[0-9A-Fa-f]{1,2}-){7}[0-9A-Fa-f]{1,2}|(?:[0-9A-Fa-f]{1,2}:){7}[0-9A-Fa-f]{1,2}|(?:[0-9A-Fa-f]{4}\.){3}[0-9A-Fa-f]{4})",
            r"(?P<eui48>(?:[0-9A-Fa-f]{1,2}-){5}[0-9A-Fa-f]{1,2}|(?:[0-9A-Fa-f]{1,2}:){5}[0-9A-Fa-f]{1,2}|(?:[0-9A-Fa-f]{4}\.){2}[0-9A-Fa-f]{4})",
            r"(?P<uuid>[a-fA-F0-9]{8}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{12})",
            r"(?P<call>[\w.]*?)\(",
            r"\b(?P<bool_true>True)\b|\b(?P<bool_false>False)\b|\b(?P<none>None)\b",
            r"(?P<ellipsis>\.\.\.)",
            r"(?P<number_complex>(?<!\w)(?:\-?[0-9]+\.?[0-9]*(?:e[-+]?\d+?)?)(?:[-+](?:[0-9]+\.?[0-9]*(?:e[-+]?\d+)?))?j)",
            r"(?P<number>(?<!\w)\-?[0-9]+\.?[0-9]*(e[-+]?\d+?)?\b|0x[0-9a-fA-F]*)",
            r"(?P<path>\B(/[-\w._+]+)*\/)(?P<filename>[-\w._+]*)?",
            r"(?<![\\\w])(?P<str>b?'''.*?(?<!\\)'''|b?'.*?(?<!\\)'|b?\"\"\".*?(?<!\\)\"\"\"|b?\".*?(?<!\\)\")",
            r"(?P<url>(file|https|http|ws|wss)://[-0-9a-zA-Z$_+!`(),.?/;:&=%#~@]*)",
        ),
    ]


class JSONHighlighter(RegexHighlighter):
    """Highlights JSON"""

    # Captures the start and end of JSON strings, handling escaped quotes
    JSON_STR = r"(?<![\\\w])(?P<str>b?\".*?(?<!\\)\")"
    JSON_WHITESPACE = {" ", "\n", "\r", "\t"}

    base_style = "json."
    highlights = [
        _combine_regex(
            r"(?P<brace>[\{\[\(\)\]\}])",
            r"\b(?P<bool_true>true)\b|\b(?P<bool_false>false)\b|\b(?P<null>null)\b",
            r"(?P<number>(?<!\w)\-?[0-9]+\.?[0-9]*(e[\-\+]?\d+?)?\b|0x[0-9a-fA-F]*)",
            JSON_STR,
        ),
    ]

    def highlight(self, text: Text) -> None:
        super().highlight(text)

        # Additional work to handle highlighting JSON keys
        plain = text.plain
        append = text.spans.append
        whitespace = self.JSON_WHITESPACE
        for match in re.finditer(self.JSON_STR, plain):
            start, end = match.span()
            cursor = end
            while cursor < len(plain):
                char = plain[cursor]
                cursor += 1
                if char == ":":
                    append(Span(start, end, "json.key"))
                elif char in whitespace:
                    continue
                break


class ISO8601Highlighter(RegexHighlighter):
    """Highlights the ISO8601 date time strings.
    Regex reference: https://www.oreilly.com/library/view/regular-expressions-cookbook/9781449327453/ch04s07.html
    """

    base_style = "iso8601."
    highlights = [
        #
        # Dates
        #
        # Calendar month (e.g. 2008-08). The hyphen is required
        r"^(?P<year>[0-9]{4})-(?P<month>1[0-2]|0[1-9])$",
        # Calendar date w/o hyphens (e.g. 20080830)
        r"^(?P<date>(?P<year>[0-9]{4})(?P<month>1[0-2]|0[1-9])(?P<day>3[01]|0[1-9]|[12][0-9]))$",
        # Ordinal date (e.g. 2008-243). The hyphen is optional
        r"^(?P<date>(?P<year>[0-9]{4})-?(?P<day>36[0-6]|3[0-5][0-9]|[12][0-9]{2}|0[1-9][0-9]|00[1-9]))$",
        #
        # Weeks
        #
        # Week of the year (e.g., 2008-W35). The hyphen is optional
        r"^(?P<date>(?P<year>[0-9]{4})-?W(?P<week>5[0-3]|[1-4][0-9]|0[1-9]))$",
        # Week date (e.g., 2008-W35-6). The hyphens are optional
        r"^(?P<date>(?P<year>[0-9]{4})-?W(?P<week>5[0-3]|[1-4][0-9]|0[1-9])-?(?P<day>[1-7]))$",
        #
        # Times
        #
        # Hours and minutes (e.g., 17:21). The colon is optional
        r"^(?P<time>(?P<hour>2[0-3]|[01][0-9]):?(?P<minute>[0-5][0-9]))$",
        # Hours, minutes, and seconds w/o colons (e.g., 172159)
        r"^(?P<time>(?P<hour>2[0-3]|[01][0-9])(?P<minute>[0-5][0-9])(?P<second>[0-5][0-9]))$",
        # Time zone designator (e.g., Z, +07 or +07:00). The colons and the minutes are optional
        r"^(?P<timezone>(Z|[+-](?:2[0-3]|[01][0-9])(?::?(?:[0-5][0-9]))?))$",
        # Hours, minutes, and seconds with time zone designator (e.g., 17:21:59+07:00).
        # All the colons are optional. The minutes in the time zone designator are also optional
        r"^(?P<time>(?P<hour>2[0-3]|[01][0-9])(?P<minute>[0-5][0-9])(?P<second>[0-5][0-9]))(?P<timezone>Z|[+-](?:2[0-3]|[01][0-9])(?::?(?:[0-5][0-9]))?)$",
        #
        # Date and Time
        #
        # Calendar date with hours, minutes, and seconds (e.g., 2008-08-30 17:21:59 or 20080830 172159).
        # A space is required between the date and the time. The hyphens and colons are optional.
        # This regex matches dates and times that specify some hyphens or colons but omit others.
        # This does not follow ISO 8601
        r"^(?P<date>(?P<year>[0-9]{4})(?P<hyphen>-)?(?P<month>1[0-2]|0[1-9])(?(hyphen)-)(?P<day>3[01]|0[1-9]|[12][0-9])) (?P<time>(?P<hour>2[0-3]|[01][0-9])(?(hyphen):)(?P<minute>[0-5][0-9])(?(hyphen):)(?P<second>[0-5][0-9]))$",
        #
        # XML Schema dates and times
        #
        # Date, with optional time zone (e.g., 2008-08-30 or 2008-08-30+07:00).
        # Hyphens are required. This is the XML Schema 'date' type
        r"^(?P<date>(?P<year>-?(?:[1-9][0-9]*)?[0-9]{4})-(?P<month>1[0-2]|0[1-9])-(?P<day>3[01]|0[1-9]|[12][0-9]))(?P<timezone>Z|[+-](?:2[0-3]|[01][0-9]):[0-5][0-9])?$",
        # Time, with optional fractional seconds and time zone (e.g., 01:45:36 or 01:45:36.123+07:00).
        # There is no limit on the number of digits for the fractional seconds. This is the XML Schema 'time' type
        r"^(?P<time>(?P<hour>2[0-3]|[01][0-9]):(?P<minute>[0-5][0-9]):(?P<second>[0-5][0-9])(?P<frac>\.[0-9]+)?)(?P<timezone>Z|[+-](?:2[0-3]|[01][0-9]):[0-5][0-9])?$",
        # Date and time, with optional fractional seconds and time zone (e.g., 2008-08-30T01:45:36 or 2008-08-30T01:45:36.123Z).
        # This is the XML Schema 'dateTime' type
        r"^(?P<date>(?P<year>-?(?:[1-9][0-9]*)?[0-9]{4})-(?P<month>1[0-2]|0[1-9])-(?P<day>3[01]|0[1-9]|[12][0-9]))T(?P<time>(?P<hour>2[0-3]|[01][0-9]):(?P<minute>[0-5][0-9]):(?P<second>[0-5][0-9])(?P<ms>\.[0-9]+)?)(?P<timezone>Z|[+-](?:2[0-3]|[01][0-9]):[0-5][0-9])?$",
    ]


if __name__ == "__main__":  # pragma: no cover
    from .console import Console

    console = Console()
    console.print("[bold green]hello world![/bold green]")
    console.print("'[bold green]hello world![/bold green]'")

    console.print(" /foo")
    console.print("/foo/")
    console.print("/foo/bar")
    console.print("foo/bar/baz")

    console.print("/foo/bar/baz?foo=bar+egg&egg=baz")
    console.print("/foo/bar/baz/")
    console.print("/foo/bar/baz/egg")
    console.print("/foo/bar/baz/egg.py")
    console.print("/foo/bar/baz/egg.py word")
    console.print(" /foo/bar/baz/egg.py word")
    console.print("foo /foo/bar/baz/egg.py word")
    console.print("foo /foo/bar/ba._++z/egg+.py word")
    console.print("https://example.org?foo=bar#header")

    console.print(1234567.34)
    console.print(1 / 2)
    console.print(-1 / 123123123123)

    console.print(
        "127.0.1.1 bar 192.168.1.4 2001:0db8:85a3:0000:0000:8a2e:0370:7334 foo"
    )
    import json

    console.print_json(json.dumps(obj={"name": "apple", "count": 1}), indent=None)

# === NexusCore/openenv\Lib\site-packages\fsspec\implementations\cache_metadata.py ===
from __future__ import annotations

import os
import pickle
import time
from typing import TYPE_CHECKING

from fsspec.utils import atomic_write

try:
    import ujson as json
except ImportError:
    if not TYPE_CHECKING:
        import json

if TYPE_CHECKING:
    from typing import Any, Dict, Iterator, Literal

    from typing_extensions import TypeAlias

    from .cached import CachingFileSystem

    Detail: TypeAlias = Dict[str, Any]


class CacheMetadata:
    """Cache metadata.

    All reading and writing of cache metadata is performed by this class,
    accessing the cached files and blocks is not.

    Metadata is stored in a single file per storage directory in JSON format.
    For backward compatibility, also reads metadata stored in pickle format
    which is converted to JSON when next saved.
    """

    def __init__(self, storage: list[str]):
        """

        Parameters
        ----------
        storage: list[str]
            Directories containing cached files, must be at least one. Metadata
            is stored in the last of these directories by convention.
        """
        if not storage:
            raise ValueError("CacheMetadata expects at least one storage location")

        self._storage = storage
        self.cached_files: list[Detail] = [{}]

        # Private attribute to force saving of metadata in pickle format rather than
        # JSON for use in tests to confirm can read both pickle and JSON formats.
        self._force_save_pickle = False

    def _load(self, fn: str) -> Detail:
        """Low-level function to load metadata from specific file"""
        try:
            with open(fn, "r") as f:
                loaded = json.load(f)
        except ValueError:
            with open(fn, "rb") as f:
                loaded = pickle.load(f)
        for c in loaded.values():
            if isinstance(c.get("blocks"), list):
                c["blocks"] = set(c["blocks"])
        return loaded

    def _save(self, metadata_to_save: Detail, fn: str) -> None:
        """Low-level function to save metadata to specific file"""
        if self._force_save_pickle:
            with atomic_write(fn) as f:
                pickle.dump(metadata_to_save, f)
        else:
            with atomic_write(fn, mode="w") as f:
                json.dump(metadata_to_save, f)

    def _scan_locations(
        self, writable_only: bool = False
    ) -> Iterator[tuple[str, str, bool]]:
        """Yield locations (filenames) where metadata is stored, and whether
        writable or not.

        Parameters
        ----------
        writable: bool
            Set to True to only yield writable locations.

        Returns
        -------
        Yields (str, str, bool)
        """
        n = len(self._storage)
        for i, storage in enumerate(self._storage):
            writable = i == n - 1
            if writable_only and not writable:
                continue
            yield os.path.join(storage, "cache"), storage, writable

    def check_file(
        self, path: str, cfs: CachingFileSystem | None
    ) -> Literal[False] | tuple[Detail, str]:
        """If path is in cache return its details, otherwise return ``False``.

        If the optional CachingFileSystem is specified then it is used to
        perform extra checks to reject possible matches, such as if they are
        too old.
        """
        for (fn, base, _), cache in zip(self._scan_locations(), self.cached_files):
            if path not in cache:
                continue
            detail = cache[path].copy()

            if cfs is not None:
                if cfs.check_files and detail["uid"] != cfs.fs.ukey(path):
                    # Wrong file as determined by hash of file properties
                    continue
                if cfs.expiry and time.time() - detail["time"] > cfs.expiry:
                    # Cached file has expired
                    continue

            fn = os.path.join(base, detail["fn"])
            if os.path.exists(fn):
                return detail, fn
        return False

    def clear_expired(self, expiry_time: int) -> tuple[list[str], bool]:
        """Remove expired metadata from the cache.

        Returns names of files corresponding to expired metadata and a boolean
        flag indicating whether the writable cache is empty. Caller is
        responsible for deleting the expired files.
        """
        expired_files = []
        for path, detail in self.cached_files[-1].copy().items():
            if time.time() - detail["time"] > expiry_time:
                fn = detail.get("fn", "")
                if not fn:
                    raise RuntimeError(
                        f"Cache metadata does not contain 'fn' for {path}"
                    )
                fn = os.path.join(self._storage[-1], fn)
                expired_files.append(fn)
                self.cached_files[-1].pop(path)

        if self.cached_files[-1]:
            cache_path = os.path.join(self._storage[-1], "cache")
            self._save(self.cached_files[-1], cache_path)

        writable_cache_empty = not self.cached_files[-1]
        return expired_files, writable_cache_empty

    def load(self) -> None:
        """Load all metadata from disk and store in ``self.cached_files``"""
        cached_files = []
        for fn, _, _ in self._scan_locations():
            if os.path.exists(fn):
                # TODO: consolidate blocks here
                cached_files.append(self._load(fn))
            else:
                cached_files.append({})
        self.cached_files = cached_files or [{}]

    def on_close_cached_file(self, f: Any, path: str) -> None:
        """Perform side-effect actions on closing a cached file.

        The actual closing of the file is the responsibility of the caller.
        """
        # File must be writeble, so in self.cached_files[-1]
        c = self.cached_files[-1][path]
        if c["blocks"] is not True and len(c["blocks"]) * f.blocksize >= f.size:
            c["blocks"] = True

    def pop_file(self, path: str) -> str | None:
        """Remove metadata of cached file.

        If path is in the cache, return the filename of the cached file,
        otherwise return ``None``.  Caller is responsible for deleting the
        cached file.
        """
        details = self.check_file(path, None)
        if not details:
            return None
        _, fn = details
        if fn.startswith(self._storage[-1]):
            self.cached_files[-1].pop(path)
            self.save()
        else:
            raise PermissionError(
                "Can only delete cached file in last, writable cache location"
            )
        return fn

    def save(self) -> None:
        """Save metadata to disk"""
        for (fn, _, writable), cache in zip(self._scan_locations(), self.cached_files):
            if not writable:
                continue

            if os.path.exists(fn):
                cached_files = self._load(fn)
                for k, c in cached_files.items():
                    if k in cache:
                        if c["blocks"] is True or cache[k]["blocks"] is True:
                            c["blocks"] = True
                        else:
                            # self.cached_files[*][*]["blocks"] must continue to
                            # point to the same set object so that updates
                            # performed by MMapCache are propagated back to
                            # self.cached_files.
                            blocks = cache[k]["blocks"]
                            blocks.update(c["blocks"])
                            c["blocks"] = blocks
                        c["time"] = max(c["time"], cache[k]["time"])
                        c["uid"] = cache[k]["uid"]

                # Files can be added to cache after it was written once
                for k, c in cache.items():
                    if k not in cached_files:
                        cached_files[k] = c
            else:
                cached_files = cache
            cache = {k: v.copy() for k, v in cached_files.items()}
            for c in cache.values():
                if isinstance(c["blocks"], set):
                    c["blocks"] = list(c["blocks"])
            self._save(cache, fn)
            self.cached_files[-1] = cached_files

    def update_file(self, path: str, detail: Detail) -> None:
        """Update metadata for specific file in memory, do not save"""
        self.cached_files[-1][path] = detail

# === NexusCore/openenv\Lib\site-packages\fsspec\implementations\gist.py ===
import requests

from ..spec import AbstractFileSystem
from ..utils import infer_storage_options
from .memory import MemoryFile


class GistFileSystem(AbstractFileSystem):
    """
    Interface to files in a single GitHub Gist.

    Provides read-only access to a gist's files. Gists do not contain
    subdirectories, so file listing is straightforward.

    Parameters
    ----------
    gist_id : str
        The ID of the gist you want to access (the long hex value from the URL).
    filenames : list[str] (optional)
        If provided, only make a file system representing these files, and do not fetch
        the list of all files for this gist.
    sha : str (optional)
        If provided, fetch a particular revision of the gist. If omitted,
        the latest revision is used.
    username : str (optional)
        GitHub username for authentication (required if token is given).
    token : str (optional)
        GitHub personal access token (required if username is given).
    timeout : (float, float) or float, optional
        Connect and read timeouts for requests (default 60s each).
    kwargs : dict
        Stored on `self.request_kw` and passed to `requests.get` when fetching Gist
        metadata or reading ("opening") a file.
    """

    protocol = "gist"
    gist_url = "https://api.github.com/gists/{gist_id}"
    gist_rev_url = "https://api.github.com/gists/{gist_id}/{sha}"

    def __init__(
        self,
        gist_id,
        filenames=None,
        sha=None,
        username=None,
        token=None,
        timeout=None,
        **kwargs,
    ):
        super().__init__()
        self.gist_id = gist_id
        self.filenames = filenames
        self.sha = sha  # revision of the gist (optional)
        if (username is None) ^ (token is None):
            # Both or neither must be set
            if username or token:
                raise ValueError("Auth requires both username and token, or neither.")
        self.username = username
        self.token = token
        self.request_kw = kwargs
        # Default timeouts to 60s connect/read if none provided
        self.timeout = timeout if timeout is not None else (60, 60)

        # We use a single-level "directory" cache, because a gist is essentially flat
        self.dircache[""] = self._fetch_file_list()

    @property
    def kw(self):
        """Auth parameters passed to 'requests' if we have username/token."""
        if self.username is not None and self.token is not None:
            return {"auth": (self.username, self.token), **self.request_kw}
        return self.request_kw

    def _fetch_gist_metadata(self):
        """
        Fetch the JSON metadata for this gist (possibly for a specific revision).
        """
        if self.sha:
            url = self.gist_rev_url.format(gist_id=self.gist_id, sha=self.sha)
        else:
            url = self.gist_url.format(gist_id=self.gist_id)

        r = requests.get(url, timeout=self.timeout, **self.kw)
        if r.status_code == 404:
            raise FileNotFoundError(
                f"Gist not found: {self.gist_id}@{self.sha or 'latest'}"
            )
        r.raise_for_status()
        return r.json()

    def _fetch_file_list(self):
        """
        Returns a list of dicts describing each file in the gist. These get stored
        in self.dircache[""].
        """
        meta = self._fetch_gist_metadata()
        if self.filenames:
            available_files = meta.get("files", {})
            files = {}
            for fn in self.filenames:
                if fn not in available_files:
                    raise FileNotFoundError(fn)
                files[fn] = available_files[fn]
        else:
            files = meta.get("files", {})

        out = []
        for fname, finfo in files.items():
            if finfo is None:
                # Occasionally GitHub returns a file entry with null if it was deleted
                continue
            # Build a directory entry
            out.append(
                {
                    "name": fname,  # file's name
                    "type": "file",  # gists have no subdirectories
                    "size": finfo.get("size", 0),  # file size in bytes
                    "raw_url": finfo.get("raw_url"),
                }
            )
        return out

    @classmethod
    def _strip_protocol(cls, path):
        """
        Remove 'gist://' from the path, if present.
        """
        # The default infer_storage_options can handle gist://username:token@id/file
        # or gist://id/file, but let's ensure we handle a normal usage too.
        # We'll just strip the protocol prefix if it exists.
        path = infer_storage_options(path).get("path", path)
        return path.lstrip("/")

    @staticmethod
    def _get_kwargs_from_urls(path):
        """
        Parse 'gist://' style URLs into GistFileSystem constructor kwargs.
        For example:
          gist://:TOKEN@<gist_id>/file.txt
          gist://username:TOKEN@<gist_id>/file.txt
        """
        so = infer_storage_options(path)
        out = {}
        if "username" in so and so["username"]:
            out["username"] = so["username"]
        if "password" in so and so["password"]:
            out["token"] = so["password"]
        if "host" in so and so["host"]:
            # We interpret 'host' as the gist ID
            out["gist_id"] = so["host"]

        # Extract SHA and filename from path
        if "path" in so and so["path"]:
            path_parts = so["path"].rsplit("/", 2)[-2:]
            if len(path_parts) == 2:
                if path_parts[0]:  # SHA present
                    out["sha"] = path_parts[0]
                if path_parts[1]:  # filename also present
                    out["filenames"] = [path_parts[1]]

        return out

    def ls(self, path="", detail=False, **kwargs):
        """
        List files in the gist. Gists are single-level, so any 'path' is basically
        the filename, or empty for all files.

        Parameters
        ----------
        path : str, optional
            The filename to list. If empty, returns all files in the gist.
        detail : bool, default False
            If True, return a list of dicts; if False, return a list of filenames.
        """
        path = self._strip_protocol(path or "")
        # If path is empty, return all
        if path == "":
            results = self.dircache[""]
        else:
            # We want just the single file with this name
            all_files = self.dircache[""]
            results = [f for f in all_files if f["name"] == path]
            if not results:
                raise FileNotFoundError(path)
        if detail:
            return results
        else:
            return sorted(f["name"] for f in results)

    def _open(self, path, mode="rb", block_size=None, **kwargs):
        """
        Read a single file from the gist.
        """
        if mode != "rb":
            raise NotImplementedError("GitHub Gist FS is read-only (no write).")

        path = self._strip_protocol(path)
        # Find the file entry in our dircache
        matches = [f for f in self.dircache[""] if f["name"] == path]
        if not matches:
            raise FileNotFoundError(path)
        finfo = matches[0]

        raw_url = finfo.get("raw_url")
        if not raw_url:
            raise FileNotFoundError(f"No raw_url for file: {path}")

        r = requests.get(raw_url, timeout=self.timeout, **self.kw)
        if r.status_code == 404:
            raise FileNotFoundError(path)
        r.raise_for_status()
        return MemoryFile(path, None, r.content)

    def cat(self, path, recursive=False, on_error="raise", **kwargs):
        """
        Return {path: contents} for the given file or files. If 'recursive' is True,
        and path is empty, returns all files in the gist.
        """
        paths = self.expand_path(path, recursive=recursive)
        out = {}
        for p in paths:
            try:
                with self.open(p, "rb") as f:
                    out[p] = f.read()
            except FileNotFoundError as e:
                if on_error == "raise":
                    raise e
                elif on_error == "omit":
                    pass  # skip
                else:
                    out[p] = e
        return out

# === NexusCore/openenv\Lib\site-packages\google\generativeai\notebook\gspread_client.py ===
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
"""Module that holds a global gspread.client.Client."""
from __future__ import annotations

import abc
import datetime
from typing import Any, Callable, Mapping, Sequence
from google.auth import credentials
from google.generativeai.notebook import html_utils
from google.generativeai.notebook import ipython_env
from google.generativeai.notebook import sheets_id


# The code may be running in an environment where the gspread library has not
# been installed.
_gspread_import_error: Exception | None = None
try:
    # pylint: disable-next=g-import-not-at-top
    import gspread
except ImportError as e:
    _gspread_import_error = e
    gspread = None

# Base class of exceptions that  gspread.open(), open_by_url() and open_by_key()
# may throw.
GSpreadException = Exception if gspread is None else gspread.exceptions.GSpreadException  # type: ignore


class SpreadsheetNotFoundError(RuntimeError):
    pass


def _get_import_error() -> Exception:
    return RuntimeError('"gspread" module not imported, got: {}'.format(_gspread_import_error))


class GSpreadClient(abc.ABC):
    """Wrapper around gspread.client.Client.

    This adds a layer of indirection for us to inject mocks for testing.
    """

    @abc.abstractmethod
    def validate(self, sid: sheets_id.SheetsIdentifier) -> None:
        """Validates that `name` is the name of a Google Sheets document.

        Raises an exception if false.

        Args:
          sid: The identifier for the document.
        """

    @abc.abstractmethod
    def get_all_records(
        self,
        sid: sheets_id.SheetsIdentifier,
        worksheet_id: int,
    ) -> tuple[Sequence[Mapping[str, str]], Callable[[], None]]:
        """Returns all records for a Google Sheets worksheet."""

    @abc.abstractmethod
    def write_records(
        self,
        sid: sheets_id.SheetsIdentifier,
        rows: Sequence[Sequence[Any]],
    ) -> None:
        """Writes results to a new worksheet to the Google Sheets document."""


class GSpreadClientImpl(GSpreadClient):
    """Concrete implementation of GSpreadClient."""

    def __init__(self, client: Any, env: ipython_env.IPythonEnv | None):
        """Constructor.

        Args:
          client: Instance of gspread.client.Client.
          env: Optional instance of IPythonEnv. This is used to display messages
            such as the URL of the output Worksheet.
        """
        self._client = client
        self._ipython_env = env

    def _open(self, sid: sheets_id.SheetsIdentifier):
        """Opens a Sheets document from `sid`.

        Args:
          sid: The identifier for the Sheets document.

        Raises:
          SpreadsheetNotFoundError: If the Sheets document cannot be found or
            cannot be opened.

        Returns:
          A gspread.Worksheet instance representing the worksheet referred to by
          `sid`.
        """
        try:
            if sid.name():
                return self._client.open(sid.name())
            if sid.key():
                return self._client.open_by_key(str(sid.key()))
            if sid.url():
                return self._client.open_by_url(str(sid.url()))
        except GSpreadException as exc:
            raise SpreadsheetNotFoundError("Unable to find Sheets with {}".format(sid)) from exc
        raise SpreadsheetNotFoundError("Invalid sheets_id.SheetsIdentifier")

    def validate(self, sid: sheets_id.SheetsIdentifier) -> None:
        self._open(sid)

    def get_all_records(
        self,
        sid: sheets_id.SheetsIdentifier,
        worksheet_id: int,
    ) -> tuple[Sequence[Mapping[str, str]], Callable[[], None]]:
        sheet = self._open(sid)
        worksheet = sheet.get_worksheet(worksheet_id)

        if self._ipython_env is not None:
            env = self._ipython_env

            def _display_fn():
                env.display_html(
                    "Reading inputs from worksheet {}".format(
                        html_utils.get_anchor_tag(
                            url=sheets_id.SheetsURL(worksheet.url),
                            text="{} in {}".format(worksheet.title, sheet.title),
                        )
                    )
                )

        else:

            def _display_fn():
                print("Reading inputs from worksheet {} in {}".format(worksheet.title, sheet.title))

        return worksheet.get_all_records(), _display_fn

    def write_records(
        self,
        sid: sheets_id.SheetsIdentifier,
        rows: Sequence[Sequence[Any]],
    ) -> None:
        sheet = self._open(sid)

        # Create a new Worksheet.
        # `title` has to be carefully constructed: some characters like colon ":"
        # will not work with gspread in Worksheet.append_rows().
        current_datetime = datetime.datetime.now()
        title = f"Results {current_datetime:%Y_%m_%d} ({current_datetime:%s})"

        # append_rows() will resize the worksheet as needed, so `rows` and `cols`
        # can be set to 1 to create a worksheet with only a single cell.
        worksheet = sheet.add_worksheet(title=title, rows=1, cols=1)
        worksheet.append_rows(values=rows)

        if self._ipython_env is not None:
            self._ipython_env.display_html(
                "Results written to new worksheet {}".format(
                    html_utils.get_anchor_tag(
                        url=sheets_id.SheetsURL(worksheet.url),
                        text="{} in {}".format(worksheet.title, sheet.title),
                    )
                )
            )
        else:
            print("Results written to new worksheet {} in {}".format(worksheet.title, sheet.title))


class NullGSpreadClient(GSpreadClient):
    """Null-object implementation of GSpreadClient.

    This class raises an error if any of its methods are called. It is used when
    the gspread library is not available.
    """

    def validate(self, sid: sheets_id.SheetsIdentifier) -> None:
        raise _get_import_error()

    def get_all_records(
        self,
        sid: sheets_id.SheetsIdentifier,
        worksheet_id: int,
    ) -> tuple[Sequence[Mapping[str, str]], Callable[[], None]]:
        raise _get_import_error()

    def write_records(
        self,
        sid: sheets_id.SheetsIdentifier,
        rows: Sequence[Sequence[Any]],
    ) -> None:
        raise _get_import_error()


# Global instance of gspread client.
_gspread_client: GSpreadClient | None = None


def authorize(creds: credentials.Credentials, env: ipython_env.IPythonEnv | None) -> None:
    """Sets up credential for gspreads."""
    global _gspread_client
    if gspread is not None:
        client = gspread.authorize(creds)  # type: ignore
        _gspread_client = GSpreadClientImpl(client=client, env=env)
    else:
        _gspread_client = NullGSpreadClient()


def get_client() -> GSpreadClient:
    if not _gspread_client:
        raise RuntimeError("Must call authorize() first")
    return _gspread_client


def testonly_set_client(client: GSpreadClient) -> None:
    """Overrides the global client for testing."""
    global _gspread_client
    _gspread_client = client

# === NexusCore/openenv\Lib\site-packages\pip\_vendor\rich\highlighter.py ===
import re
from abc import ABC, abstractmethod
from typing import List, Union

from .text import Span, Text


def _combine_regex(*regexes: str) -> str:
    """Combine a number of regexes in to a single regex.

    Returns:
        str: New regex with all regexes ORed together.
    """
    return "|".join(regexes)


class Highlighter(ABC):
    """Abstract base class for highlighters."""

    def __call__(self, text: Union[str, Text]) -> Text:
        """Highlight a str or Text instance.

        Args:
            text (Union[str, ~Text]): Text to highlight.

        Raises:
            TypeError: If not called with text or str.

        Returns:
            Text: A test instance with highlighting applied.
        """
        if isinstance(text, str):
            highlight_text = Text(text)
        elif isinstance(text, Text):
            highlight_text = text.copy()
        else:
            raise TypeError(f"str or Text instance required, not {text!r}")
        self.highlight(highlight_text)
        return highlight_text

    @abstractmethod
    def highlight(self, text: Text) -> None:
        """Apply highlighting in place to text.

        Args:
            text (~Text): A text object highlight.
        """


class NullHighlighter(Highlighter):
    """A highlighter object that doesn't highlight.

    May be used to disable highlighting entirely.

    """

    def highlight(self, text: Text) -> None:
        """Nothing to do"""


class RegexHighlighter(Highlighter):
    """Applies highlighting from a list of regular expressions."""

    highlights: List[str] = []
    base_style: str = ""

    def highlight(self, text: Text) -> None:
        """Highlight :class:`rich.text.Text` using regular expressions.

        Args:
            text (~Text): Text to highlighted.

        """

        highlight_regex = text.highlight_regex
        for re_highlight in self.highlights:
            highlight_regex(re_highlight, style_prefix=self.base_style)


class ReprHighlighter(RegexHighlighter):
    """Highlights the text typically produced from ``__repr__`` methods."""

    base_style = "repr."
    highlights = [
        r"(?P<tag_start><)(?P<tag_name>[-\w.:|]*)(?P<tag_contents>[\w\W]*)(?P<tag_end>>)",
        r'(?P<attrib_name>[\w_]{1,50})=(?P<attrib_value>"?[\w_]+"?)?',
        r"(?P<brace>[][{}()])",
        _combine_regex(
            r"(?P<ipv4>[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3})",
            r"(?P<ipv6>([A-Fa-f0-9]{1,4}::?){1,7}[A-Fa-f0-9]{1,4})",
            r"(?P<eui64>(?:[0-9A-Fa-f]{1,2}-){7}[0-9A-Fa-f]{1,2}|(?:[0-9A-Fa-f]{1,2}:){7}[0-9A-Fa-f]{1,2}|(?:[0-9A-Fa-f]{4}\.){3}[0-9A-Fa-f]{4})",
            r"(?P<eui48>(?:[0-9A-Fa-f]{1,2}-){5}[0-9A-Fa-f]{1,2}|(?:[0-9A-Fa-f]{1,2}:){5}[0-9A-Fa-f]{1,2}|(?:[0-9A-Fa-f]{4}\.){2}[0-9A-Fa-f]{4})",
            r"(?P<uuid>[a-fA-F0-9]{8}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{12})",
            r"(?P<call>[\w.]*?)\(",
            r"\b(?P<bool_true>True)\b|\b(?P<bool_false>False)\b|\b(?P<none>None)\b",
            r"(?P<ellipsis>\.\.\.)",
            r"(?P<number_complex>(?<!\w)(?:\-?[0-9]+\.?[0-9]*(?:e[-+]?\d+?)?)(?:[-+](?:[0-9]+\.?[0-9]*(?:e[-+]?\d+)?))?j)",
            r"(?P<number>(?<!\w)\-?[0-9]+\.?[0-9]*(e[-+]?\d+?)?\b|0x[0-9a-fA-F]*)",
            r"(?P<path>\B(/[-\w._+]+)*\/)(?P<filename>[-\w._+]*)?",
            r"(?<![\\\w])(?P<str>b?'''.*?(?<!\\)'''|b?'.*?(?<!\\)'|b?\"\"\".*?(?<!\\)\"\"\"|b?\".*?(?<!\\)\")",
            r"(?P<url>(file|https|http|ws|wss)://[-0-9a-zA-Z$_+!`(),.?/;:&=%#~@]*)",
        ),
    ]


class JSONHighlighter(RegexHighlighter):
    """Highlights JSON"""

    # Captures the start and end of JSON strings, handling escaped quotes
    JSON_STR = r"(?<![\\\w])(?P<str>b?\".*?(?<!\\)\")"
    JSON_WHITESPACE = {" ", "\n", "\r", "\t"}

    base_style = "json."
    highlights = [
        _combine_regex(
            r"(?P<brace>[\{\[\(\)\]\}])",
            r"\b(?P<bool_true>true)\b|\b(?P<bool_false>false)\b|\b(?P<null>null)\b",
            r"(?P<number>(?<!\w)\-?[0-9]+\.?[0-9]*(e[\-\+]?\d+?)?\b|0x[0-9a-fA-F]*)",
            JSON_STR,
        ),
    ]

    def highlight(self, text: Text) -> None:
        super().highlight(text)

        # Additional work to handle highlighting JSON keys
        plain = text.plain
        append = text.spans.append
        whitespace = self.JSON_WHITESPACE
        for match in re.finditer(self.JSON_STR, plain):
            start, end = match.span()
            cursor = end
            while cursor < len(plain):
                char = plain[cursor]
                cursor += 1
                if char == ":":
                    append(Span(start, end, "json.key"))
                elif char in whitespace:
                    continue
                break


class ISO8601Highlighter(RegexHighlighter):
    """Highlights the ISO8601 date time strings.
    Regex reference: https://www.oreilly.com/library/view/regular-expressions-cookbook/9781449327453/ch04s07.html
    """

    base_style = "iso8601."
    highlights = [
        #
        # Dates
        #
        # Calendar month (e.g. 2008-08). The hyphen is required
        r"^(?P<year>[0-9]{4})-(?P<month>1[0-2]|0[1-9])$",
        # Calendar date w/o hyphens (e.g. 20080830)
        r"^(?P<date>(?P<year>[0-9]{4})(?P<month>1[0-2]|0[1-9])(?P<day>3[01]|0[1-9]|[12][0-9]))$",
        # Ordinal date (e.g. 2008-243). The hyphen is optional
        r"^(?P<date>(?P<year>[0-9]{4})-?(?P<day>36[0-6]|3[0-5][0-9]|[12][0-9]{2}|0[1-9][0-9]|00[1-9]))$",
        #
        # Weeks
        #
        # Week of the year (e.g., 2008-W35). The hyphen is optional
        r"^(?P<date>(?P<year>[0-9]{4})-?W(?P<week>5[0-3]|[1-4][0-9]|0[1-9]))$",
        # Week date (e.g., 2008-W35-6). The hyphens are optional
        r"^(?P<date>(?P<year>[0-9]{4})-?W(?P<week>5[0-3]|[1-4][0-9]|0[1-9])-?(?P<day>[1-7]))$",
        #
        # Times
        #
        # Hours and minutes (e.g., 17:21). The colon is optional
        r"^(?P<time>(?P<hour>2[0-3]|[01][0-9]):?(?P<minute>[0-5][0-9]))$",
        # Hours, minutes, and seconds w/o colons (e.g., 172159)
        r"^(?P<time>(?P<hour>2[0-3]|[01][0-9])(?P<minute>[0-5][0-9])(?P<second>[0-5][0-9]))$",
        # Time zone designator (e.g., Z, +07 or +07:00). The colons and the minutes are optional
        r"^(?P<timezone>(Z|[+-](?:2[0-3]|[01][0-9])(?::?(?:[0-5][0-9]))?))$",
        # Hours, minutes, and seconds with time zone designator (e.g., 17:21:59+07:00).
        # All the colons are optional. The minutes in the time zone designator are also optional
        r"^(?P<time>(?P<hour>2[0-3]|[01][0-9])(?P<minute>[0-5][0-9])(?P<second>[0-5][0-9]))(?P<timezone>Z|[+-](?:2[0-3]|[01][0-9])(?::?(?:[0-5][0-9]))?)$",
        #
        # Date and Time
        #
        # Calendar date with hours, minutes, and seconds (e.g., 2008-08-30 17:21:59 or 20080830 172159).
        # A space is required between the date and the time. The hyphens and colons are optional.
        # This regex matches dates and times that specify some hyphens or colons but omit others.
        # This does not follow ISO 8601
        r"^(?P<date>(?P<year>[0-9]{4})(?P<hyphen>-)?(?P<month>1[0-2]|0[1-9])(?(hyphen)-)(?P<day>3[01]|0[1-9]|[12][0-9])) (?P<time>(?P<hour>2[0-3]|[01][0-9])(?(hyphen):)(?P<minute>[0-5][0-9])(?(hyphen):)(?P<second>[0-5][0-9]))$",
        #
        # XML Schema dates and times
        #
        # Date, with optional time zone (e.g., 2008-08-30 or 2008-08-30+07:00).
        # Hyphens are required. This is the XML Schema 'date' type
        r"^(?P<date>(?P<year>-?(?:[1-9][0-9]*)?[0-9]{4})-(?P<month>1[0-2]|0[1-9])-(?P<day>3[01]|0[1-9]|[12][0-9]))(?P<timezone>Z|[+-](?:2[0-3]|[01][0-9]):[0-5][0-9])?$",
        # Time, with optional fractional seconds and time zone (e.g., 01:45:36 or 01:45:36.123+07:00).
        # There is no limit on the number of digits for the fractional seconds. This is the XML Schema 'time' type
        r"^(?P<time>(?P<hour>2[0-3]|[01][0-9]):(?P<minute>[0-5][0-9]):(?P<second>[0-5][0-9])(?P<frac>\.[0-9]+)?)(?P<timezone>Z|[+-](?:2[0-3]|[01][0-9]):[0-5][0-9])?$",
        # Date and time, with optional fractional seconds and time zone (e.g., 2008-08-30T01:45:36 or 2008-08-30T01:45:36.123Z).
        # This is the XML Schema 'dateTime' type
        r"^(?P<date>(?P<year>-?(?:[1-9][0-9]*)?[0-9]{4})-(?P<month>1[0-2]|0[1-9])-(?P<day>3[01]|0[1-9]|[12][0-9]))T(?P<time>(?P<hour>2[0-3]|[01][0-9]):(?P<minute>[0-5][0-9]):(?P<second>[0-5][0-9])(?P<ms>\.[0-9]+)?)(?P<timezone>Z|[+-](?:2[0-3]|[01][0-9]):[0-5][0-9])?$",
    ]


if __name__ == "__main__":  # pragma: no cover
    from .console import Console

    console = Console()
    console.print("[bold green]hello world![/bold green]")
    console.print("'[bold green]hello world![/bold green]'")

    console.print(" /foo")
    console.print("/foo/")
    console.print("/foo/bar")
    console.print("foo/bar/baz")

    console.print("/foo/bar/baz?foo=bar+egg&egg=baz")
    console.print("/foo/bar/baz/")
    console.print("/foo/bar/baz/egg")
    console.print("/foo/bar/baz/egg.py")
    console.print("/foo/bar/baz/egg.py word")
    console.print(" /foo/bar/baz/egg.py word")
    console.print("foo /foo/bar/baz/egg.py word")
    console.print("foo /foo/bar/ba._++z/egg+.py word")
    console.print("https://example.org?foo=bar#header")

    console.print(1234567.34)
    console.print(1 / 2)
    console.print(-1 / 123123123123)

    console.print(
        "127.0.1.1 bar 192.168.1.4 2001:0db8:85a3:0000:0000:8a2e:0370:7334 foo"
    )
    import json

    console.print_json(json.dumps(obj={"name": "apple", "count": 1}), indent=None)

# === NexusCore/openenv\Lib\site-packages\selenium\webdriver\remote\errorhandler.py ===
# Licensed to the Software Freedom Conservancy (SFC) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The SFC licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.

from typing import Any, Dict, Type

from selenium.common.exceptions import (
    DetachedShadowRootException,
    ElementClickInterceptedException,
    ElementNotInteractableException,
    ElementNotSelectableException,
    ElementNotVisibleException,
    ImeActivationFailedException,
    ImeNotAvailableException,
    InsecureCertificateException,
    InvalidArgumentException,
    InvalidCookieDomainException,
    InvalidCoordinatesException,
    InvalidElementStateException,
    InvalidSelectorException,
    InvalidSessionIdException,
    JavascriptException,
    MoveTargetOutOfBoundsException,
    NoAlertPresentException,
    NoSuchCookieException,
    NoSuchElementException,
    NoSuchFrameException,
    NoSuchShadowRootException,
    NoSuchWindowException,
    ScreenshotException,
    SessionNotCreatedException,
    StaleElementReferenceException,
    TimeoutException,
    UnableToSetCookieException,
    UnexpectedAlertPresentException,
    UnknownMethodException,
    WebDriverException,
)


class ExceptionMapping:
    """
    :Maps each errorcode in ErrorCode object to corresponding exception
    Please refer to https://www.w3.org/TR/webdriver2/#errors for w3c specification
    """

    NO_SUCH_ELEMENT = NoSuchElementException
    NO_SUCH_FRAME = NoSuchFrameException
    NO_SUCH_SHADOW_ROOT = NoSuchShadowRootException
    STALE_ELEMENT_REFERENCE = StaleElementReferenceException
    ELEMENT_NOT_VISIBLE = ElementNotVisibleException
    INVALID_ELEMENT_STATE = InvalidElementStateException
    UNKNOWN_ERROR = WebDriverException
    ELEMENT_IS_NOT_SELECTABLE = ElementNotSelectableException
    JAVASCRIPT_ERROR = JavascriptException
    TIMEOUT = TimeoutException
    NO_SUCH_WINDOW = NoSuchWindowException
    INVALID_COOKIE_DOMAIN = InvalidCookieDomainException
    UNABLE_TO_SET_COOKIE = UnableToSetCookieException
    UNEXPECTED_ALERT_OPEN = UnexpectedAlertPresentException
    NO_ALERT_OPEN = NoAlertPresentException
    SCRIPT_TIMEOUT = TimeoutException
    IME_NOT_AVAILABLE = ImeNotAvailableException
    IME_ENGINE_ACTIVATION_FAILED = ImeActivationFailedException
    INVALID_SELECTOR = InvalidSelectorException
    SESSION_NOT_CREATED = SessionNotCreatedException
    MOVE_TARGET_OUT_OF_BOUNDS = MoveTargetOutOfBoundsException
    INVALID_XPATH_SELECTOR = InvalidSelectorException
    INVALID_XPATH_SELECTOR_RETURN_TYPER = InvalidSelectorException
    ELEMENT_NOT_INTERACTABLE = ElementNotInteractableException
    INSECURE_CERTIFICATE = InsecureCertificateException
    INVALID_ARGUMENT = InvalidArgumentException
    INVALID_COORDINATES = InvalidCoordinatesException
    INVALID_SESSION_ID = InvalidSessionIdException
    NO_SUCH_COOKIE = NoSuchCookieException
    UNABLE_TO_CAPTURE_SCREEN = ScreenshotException
    ELEMENT_CLICK_INTERCEPTED = ElementClickInterceptedException
    UNKNOWN_METHOD = UnknownMethodException
    DETACHED_SHADOW_ROOT = DetachedShadowRootException


class ErrorCode:
    """Error codes defined in the WebDriver wire protocol."""

    # Keep in sync with org.openqa.selenium.remote.ErrorCodes and errorcodes.h
    SUCCESS = 0
    NO_SUCH_ELEMENT = [7, "no such element"]
    NO_SUCH_FRAME = [8, "no such frame"]
    NO_SUCH_SHADOW_ROOT = ["no such shadow root"]
    UNKNOWN_COMMAND = [9, "unknown command"]
    STALE_ELEMENT_REFERENCE = [10, "stale element reference"]
    ELEMENT_NOT_VISIBLE = [11, "element not visible"]
    INVALID_ELEMENT_STATE = [12, "invalid element state"]
    UNKNOWN_ERROR = [13, "unknown error"]
    ELEMENT_IS_NOT_SELECTABLE = [15, "element not selectable"]
    JAVASCRIPT_ERROR = [17, "javascript error"]
    XPATH_LOOKUP_ERROR = [19, "invalid selector"]
    TIMEOUT = [21, "timeout"]
    NO_SUCH_WINDOW = [23, "no such window"]
    INVALID_COOKIE_DOMAIN = [24, "invalid cookie domain"]
    UNABLE_TO_SET_COOKIE = [25, "unable to set cookie"]
    UNEXPECTED_ALERT_OPEN = [26, "unexpected alert open"]
    NO_ALERT_OPEN = [27, "no such alert"]
    SCRIPT_TIMEOUT = [28, "script timeout"]
    INVALID_ELEMENT_COORDINATES = [29, "invalid element coordinates"]
    IME_NOT_AVAILABLE = [30, "ime not available"]
    IME_ENGINE_ACTIVATION_FAILED = [31, "ime engine activation failed"]
    INVALID_SELECTOR = [32, "invalid selector"]
    SESSION_NOT_CREATED = [33, "session not created"]
    MOVE_TARGET_OUT_OF_BOUNDS = [34, "move target out of bounds"]
    INVALID_XPATH_SELECTOR = [51, "invalid selector"]
    INVALID_XPATH_SELECTOR_RETURN_TYPER = [52, "invalid selector"]

    ELEMENT_NOT_INTERACTABLE = [60, "element not interactable"]
    INSECURE_CERTIFICATE = ["insecure certificate"]
    INVALID_ARGUMENT = [61, "invalid argument"]
    INVALID_COORDINATES = ["invalid coordinates"]
    INVALID_SESSION_ID = ["invalid session id"]
    NO_SUCH_COOKIE = [62, "no such cookie"]
    UNABLE_TO_CAPTURE_SCREEN = [63, "unable to capture screen"]
    ELEMENT_CLICK_INTERCEPTED = [64, "element click intercepted"]
    UNKNOWN_METHOD = ["unknown method exception"]
    DETACHED_SHADOW_ROOT = [65, "detached shadow root"]

    METHOD_NOT_ALLOWED = [405, "unsupported operation"]


class ErrorHandler:
    """Handles errors returned by the WebDriver server."""

    def check_response(self, response: Dict[str, Any]) -> None:
        """Checks that a JSON response from the WebDriver does not have an
        error.

        :Args:
         - response - The JSON response from the WebDriver server as a dictionary
           object.

        :Raises: If the response contains an error message.
        """
        status = response.get("status", None)
        if not status or status == ErrorCode.SUCCESS:
            return
        value = None
        message = response.get("message", "")
        screen: str = response.get("screen", "")
        stacktrace = None
        if isinstance(status, int):
            value_json = response.get("value", None)
            if value_json and isinstance(value_json, str):
                import json

                try:
                    value = json.loads(value_json)
                    if len(value) == 1:
                        value = value["value"]
                    status = value.get("error", None)
                    if not status:
                        status = value.get("status", ErrorCode.UNKNOWN_ERROR)
                        message = value.get("value") or value.get("message")
                        if not isinstance(message, str):
                            value = message
                            message = message.get("message")
                    else:
                        message = value.get("message", None)
                except ValueError:
                    pass

        exception_class: Type[WebDriverException]
        e = ErrorCode()
        error_codes = [item for item in dir(e) if not item.startswith("__")]
        for error_code in error_codes:
            error_info = getattr(ErrorCode, error_code)
            if isinstance(error_info, list) and status in error_info:
                exception_class = getattr(ExceptionMapping, error_code, WebDriverException)
                break
        else:
            exception_class = WebDriverException

        if not value:
            value = response["value"]
        if isinstance(value, str):
            raise exception_class(value)
        if message == "" and "message" in value:
            message = value["message"]

        screen = None  # type: ignore[assignment]
        if "screen" in value:
            screen = value["screen"]

        stacktrace = None
        st_value = value.get("stackTrace") or value.get("stacktrace")
        if st_value:
            if isinstance(st_value, str):
                stacktrace = st_value.split("\n")
            else:
                stacktrace = []
                try:
                    for frame in st_value:
                        line = frame.get("lineNumber", "")
                        file = frame.get("fileName", "<anonymous>")
                        if line:
                            file = f"{file}:{line}"
                        meth = frame.get("methodName", "<anonymous>")
                        if "className" in frame:
                            meth = f"{frame['className']}.{meth}"
                        msg = "    at %s (%s)"
                        msg = msg % (meth, file)
                        stacktrace.append(msg)
                except TypeError:
                    pass
        if exception_class == UnexpectedAlertPresentException:
            alert_text = None
            if "data" in value:
                alert_text = value["data"].get("text")
            elif "alert" in value:
                alert_text = value["alert"].get("text")
            raise exception_class(message, screen, stacktrace, alert_text)  # type: ignore[call-arg]  # mypy is not smart enough here
        raise exception_class(message, screen, stacktrace)

# === NexusCore/openenv\Lib\site-packages\zmq\log\handlers.py ===
"""pyzmq logging handlers.

This mainly defines the PUBHandler object for publishing logging messages over
a zmq.PUB socket.

The PUBHandler can be used with the regular logging module, as in::

    >>> import logging
    >>> handler = PUBHandler('tcp://127.0.0.1:12345')
    >>> handler.root_topic = 'foo'
    >>> logger = logging.getLogger('foobar')
    >>> logger.setLevel(logging.DEBUG)
    >>> logger.addHandler(handler)

Or using ``dictConfig``, as in::

    >>> from logging.config import dictConfig
    >>> socket = Context.instance().socket(PUB)
    >>> socket.connect('tcp://127.0.0.1:12345')
    >>> dictConfig({
    >>>     'version': 1,
    >>>     'handlers': {
    >>>         'zmq': {
    >>>             'class': 'zmq.log.handlers.PUBHandler',
    >>>             'level': logging.DEBUG,
    >>>             'root_topic': 'foo',
    >>>             'interface_or_socket': socket
    >>>         }
    >>>     },
    >>>     'root': {
    >>>         'level': 'DEBUG',
    >>>         'handlers': ['zmq'],
    >>>     }
    >>> })


After this point, all messages logged by ``logger`` will be published on the
PUB socket.

Code adapted from StarCluster:

    https://github.com/jtriley/StarCluster/blob/StarCluster-0.91/starcluster/logger.py
"""

from __future__ import annotations

import logging
from copy import copy

import zmq

# Copyright (C) PyZMQ Developers
# Distributed under the terms of the Modified BSD License.


TOPIC_DELIM = "::"  # delimiter for splitting topics on the receiving end.


class PUBHandler(logging.Handler):
    """A basic logging handler that emits log messages through a PUB socket.

    Takes a PUB socket already bound to interfaces or an interface to bind to.

    Example::

        sock = context.socket(zmq.PUB)
        sock.bind('inproc://log')
        handler = PUBHandler(sock)

    Or::

        handler = PUBHandler('inproc://loc')

    These are equivalent.

    Log messages handled by this handler are broadcast with ZMQ topics
    ``this.root_topic`` comes first, followed by the log level
    (DEBUG,INFO,etc.), followed by any additional subtopics specified in the
    message by: log.debug("subtopic.subsub::the real message")
    """

    ctx: zmq.Context
    socket: zmq.Socket

    def __init__(
        self,
        interface_or_socket: str | zmq.Socket,
        context: zmq.Context | None = None,
        root_topic: str = '',
    ) -> None:
        logging.Handler.__init__(self)
        self.root_topic = root_topic
        self.formatters = {
            logging.DEBUG: logging.Formatter(
                "%(levelname)s %(filename)s:%(lineno)d - %(message)s\n"
            ),
            logging.INFO: logging.Formatter("%(message)s\n"),
            logging.WARN: logging.Formatter(
                "%(levelname)s %(filename)s:%(lineno)d - %(message)s\n"
            ),
            logging.ERROR: logging.Formatter(
                "%(levelname)s %(filename)s:%(lineno)d - %(message)s - %(exc_info)s\n"
            ),
            logging.CRITICAL: logging.Formatter(
                "%(levelname)s %(filename)s:%(lineno)d - %(message)s\n"
            ),
        }
        if isinstance(interface_or_socket, zmq.Socket):
            self.socket = interface_or_socket
            self.ctx = self.socket.context
        else:
            self.ctx = context or zmq.Context()
            self.socket = self.ctx.socket(zmq.PUB)
            self.socket.bind(interface_or_socket)

    @property
    def root_topic(self) -> str:
        return self._root_topic

    @root_topic.setter
    def root_topic(self, value: str):
        self.setRootTopic(value)

    def setRootTopic(self, root_topic: str):
        """Set the root topic for this handler.

        This value is prepended to all messages published by this handler, and it
        defaults to the empty string ''. When you subscribe to this socket, you must
        set your subscription to an empty string, or to at least the first letter of
        the binary representation of this string to ensure you receive any messages
        from this handler.

        If you use the default empty string root topic, messages will begin with
        the binary representation of the log level string (INFO, WARN, etc.).
        Note that ZMQ SUB sockets can have multiple subscriptions.
        """
        if isinstance(root_topic, bytes):
            root_topic = root_topic.decode("utf8")
        self._root_topic = root_topic

    def setFormatter(self, fmt, level=logging.NOTSET):
        """Set the Formatter for this handler.

        If no level is provided, the same format is used for all levels. This
        will overwrite all selective formatters set in the object constructor.
        """
        if level == logging.NOTSET:
            for fmt_level in self.formatters.keys():
                self.formatters[fmt_level] = fmt
        else:
            self.formatters[level] = fmt

    def format(self, record):
        """Format a record."""
        return self.formatters[record.levelno].format(record)

    def emit(self, record):
        """Emit a log message on my socket."""

        # LogRecord.getMessage explicitly allows msg to be anything _castable_ to a str
        try:
            topic, msg = str(record.msg).split(TOPIC_DELIM, 1)
        except ValueError:
            topic = ""
        else:
            # copy to avoid mutating LogRecord in-place
            record = copy(record)
            record.msg = msg

        try:
            bmsg = self.format(record).encode("utf8")
        except Exception:
            self.handleError(record)
            return

        topic_list = []

        if self.root_topic:
            topic_list.append(self.root_topic)

        topic_list.append(record.levelname)

        if topic:
            topic_list.append(topic)

        btopic = '.'.join(topic_list).encode("utf8", "replace")

        self.socket.send_multipart([btopic, bmsg])


class TopicLogger(logging.Logger):
    """A simple wrapper that takes an additional argument to log methods.

    All the regular methods exist, but instead of one msg argument, two
    arguments: topic, msg are passed.

    That is::

        logger.debug('msg')

    Would become::

        logger.debug('topic.sub', 'msg')
    """

    def log(self, level, topic, msg, *args, **kwargs):
        """Log 'msg % args' with level and topic.

        To pass exception information, use the keyword argument exc_info
        with a True value::

            logger.log(level, "zmq.fun", "We have a %s",
                    "mysterious problem", exc_info=1)
        """
        logging.Logger.log(self, level, f'{topic}{TOPIC_DELIM}{msg}', *args, **kwargs)


# Generate the methods of TopicLogger, since they are just adding a
# topic prefix to a message.
for name in "debug warn warning error critical fatal".split():
    try:
        meth = getattr(logging.Logger, name)
    except AttributeError:
        # some methods are missing, e.g. Logger.warn was removed from Python 3.13
        continue
    setattr(
        TopicLogger,
        name,
        lambda self, level, topic, msg, *args, **kwargs: meth(
            self, level, topic + TOPIC_DELIM + msg, *args, **kwargs
        ),
    )

# === NexusCore/openenv\Lib\site-packages\openai\_compat.py ===
from __future__ import annotations

from typing import TYPE_CHECKING, Any, Union, Generic, TypeVar, Callable, cast, overload
from datetime import date, datetime
from typing_extensions import Self, Literal

import pydantic
from pydantic.fields import FieldInfo

from ._types import IncEx, StrBytesIntFloat

_T = TypeVar("_T")
_ModelT = TypeVar("_ModelT", bound=pydantic.BaseModel)

# --------------- Pydantic v2 compatibility ---------------

# Pyright incorrectly reports some of our functions as overriding a method when they don't
# pyright: reportIncompatibleMethodOverride=false

PYDANTIC_V2 = pydantic.VERSION.startswith("2.")

# v1 re-exports
if TYPE_CHECKING:

    def parse_date(value: date | StrBytesIntFloat) -> date:  # noqa: ARG001
        ...

    def parse_datetime(value: Union[datetime, StrBytesIntFloat]) -> datetime:  # noqa: ARG001
        ...

    def get_args(t: type[Any]) -> tuple[Any, ...]:  # noqa: ARG001
        ...

    def is_union(tp: type[Any] | None) -> bool:  # noqa: ARG001
        ...

    def get_origin(t: type[Any]) -> type[Any] | None:  # noqa: ARG001
        ...

    def is_literal_type(type_: type[Any]) -> bool:  # noqa: ARG001
        ...

    def is_typeddict(type_: type[Any]) -> bool:  # noqa: ARG001
        ...

else:
    if PYDANTIC_V2:
        from pydantic.v1.typing import (
            get_args as get_args,
            is_union as is_union,
            get_origin as get_origin,
            is_typeddict as is_typeddict,
            is_literal_type as is_literal_type,
        )
        from pydantic.v1.datetime_parse import parse_date as parse_date, parse_datetime as parse_datetime
    else:
        from pydantic.typing import (
            get_args as get_args,
            is_union as is_union,
            get_origin as get_origin,
            is_typeddict as is_typeddict,
            is_literal_type as is_literal_type,
        )
        from pydantic.datetime_parse import parse_date as parse_date, parse_datetime as parse_datetime


# refactored config
if TYPE_CHECKING:
    from pydantic import ConfigDict as ConfigDict
else:
    if PYDANTIC_V2:
        from pydantic import ConfigDict
    else:
        # TODO: provide an error message here?
        ConfigDict = None


# renamed methods / properties
def parse_obj(model: type[_ModelT], value: object) -> _ModelT:
    if PYDANTIC_V2:
        return model.model_validate(value)
    else:
        return cast(_ModelT, model.parse_obj(value))  # pyright: ignore[reportDeprecated, reportUnnecessaryCast]


def field_is_required(field: FieldInfo) -> bool:
    if PYDANTIC_V2:
        return field.is_required()
    return field.required  # type: ignore


def field_get_default(field: FieldInfo) -> Any:
    value = field.get_default()
    if PYDANTIC_V2:
        from pydantic_core import PydanticUndefined

        if value == PydanticUndefined:
            return None
        return value
    return value


def field_outer_type(field: FieldInfo) -> Any:
    if PYDANTIC_V2:
        return field.annotation
    return field.outer_type_  # type: ignore


def get_model_config(model: type[pydantic.BaseModel]) -> Any:
    if PYDANTIC_V2:
        return model.model_config
    return model.__config__  # type: ignore


def get_model_fields(model: type[pydantic.BaseModel]) -> dict[str, FieldInfo]:
    if PYDANTIC_V2:
        return model.model_fields
    return model.__fields__  # type: ignore


def model_copy(model: _ModelT, *, deep: bool = False) -> _ModelT:
    if PYDANTIC_V2:
        return model.model_copy(deep=deep)
    return model.copy(deep=deep)  # type: ignore


def model_json(model: pydantic.BaseModel, *, indent: int | None = None) -> str:
    if PYDANTIC_V2:
        return model.model_dump_json(indent=indent)
    return model.json(indent=indent)  # type: ignore


def model_dump(
    model: pydantic.BaseModel,
    *,
    exclude: IncEx | None = None,
    exclude_unset: bool = False,
    exclude_defaults: bool = False,
    warnings: bool = True,
    mode: Literal["json", "python"] = "python",
) -> dict[str, Any]:
    if PYDANTIC_V2 or hasattr(model, "model_dump"):
        return model.model_dump(
            mode=mode,
            exclude=exclude,
            exclude_unset=exclude_unset,
            exclude_defaults=exclude_defaults,
            # warnings are not supported in Pydantic v1
            warnings=warnings if PYDANTIC_V2 else True,
        )
    return cast(
        "dict[str, Any]",
        model.dict(  # pyright: ignore[reportDeprecated, reportUnnecessaryCast]
            exclude=exclude,
            exclude_unset=exclude_unset,
            exclude_defaults=exclude_defaults,
        ),
    )


def model_parse(model: type[_ModelT], data: Any) -> _ModelT:
    if PYDANTIC_V2:
        return model.model_validate(data)
    return model.parse_obj(data)  # pyright: ignore[reportDeprecated]


def model_parse_json(model: type[_ModelT], data: str | bytes) -> _ModelT:
    if PYDANTIC_V2:
        return model.model_validate_json(data)
    return model.parse_raw(data)  # pyright: ignore[reportDeprecated]


def model_json_schema(model: type[_ModelT]) -> dict[str, Any]:
    if PYDANTIC_V2:
        return model.model_json_schema()
    return model.schema()  # pyright: ignore[reportDeprecated]


# generic models
if TYPE_CHECKING:

    class GenericModel(pydantic.BaseModel): ...

else:
    if PYDANTIC_V2:
        # there no longer needs to be a distinction in v2 but
        # we still have to create our own subclass to avoid
        # inconsistent MRO ordering errors
        class GenericModel(pydantic.BaseModel): ...

    else:
        import pydantic.generics

        class GenericModel(pydantic.generics.GenericModel, pydantic.BaseModel): ...


# cached properties
if TYPE_CHECKING:
    cached_property = property

    # we define a separate type (copied from typeshed)
    # that represents that `cached_property` is `set`able
    # at runtime, which differs from `@property`.
    #
    # this is a separate type as editors likely special case
    # `@property` and we don't want to cause issues just to have
    # more helpful internal types.

    class typed_cached_property(Generic[_T]):
        func: Callable[[Any], _T]
        attrname: str | None

        def __init__(self, func: Callable[[Any], _T]) -> None: ...

        @overload
        def __get__(self, instance: None, owner: type[Any] | None = None) -> Self: ...

        @overload
        def __get__(self, instance: object, owner: type[Any] | None = None) -> _T: ...

        def __get__(self, instance: object, owner: type[Any] | None = None) -> _T | Self:
            raise NotImplementedError()

        def __set_name__(self, owner: type[Any], name: str) -> None: ...

        # __set__ is not defined at runtime, but @cached_property is designed to be settable
        def __set__(self, instance: object, value: _T) -> None: ...
else:
    from functools import cached_property as cached_property

    typed_cached_property = cached_property

# === NexusCore/openenv\Lib\site-packages\fontTools\misc\sstruct.py ===
"""sstruct.py -- SuperStruct

Higher level layer on top of the struct module, enabling to
bind names to struct elements. The interface is similar to
struct, except the objects passed and returned are not tuples
(or argument lists), but dictionaries or instances.

Just like struct, we use fmt strings to describe a data
structure, except we use one line per element. Lines are
separated by newlines or semi-colons. Each line contains
either one of the special struct characters ('@', '=', '<',
'>' or '!') or a 'name:formatchar' combo (eg. 'myFloat:f').
Repetitions, like the struct module offers them are not useful
in this context, except for fixed length strings  (eg. 'myInt:5h'
is not allowed but 'myString:5s' is). The 'x' fmt character
(pad byte) is treated as 'special', since it is by definition
anonymous. Extra whitespace is allowed everywhere.

The sstruct module offers one feature that the "normal" struct
module doesn't: support for fixed point numbers. These are spelled
as "n.mF", where n is the number of bits before the point, and m
the number of bits after the point. Fixed point numbers get
converted to floats.

pack(fmt, object):
	'object' is either a dictionary or an instance (or actually
	anything that has a __dict__ attribute). If it is a dictionary,
	its keys are used for names. If it is an instance, it's
	attributes are used to grab struct elements from. Returns
	a string containing the data.

unpack(fmt, data, object=None)
	If 'object' is omitted (or None), a new dictionary will be
	returned. If 'object' is a dictionary, it will be used to add
	struct elements to. If it is an instance (or in fact anything
	that has a __dict__ attribute), an attribute will be added for
	each struct element. In the latter two cases, 'object' itself
	is returned.

unpack2(fmt, data, object=None)
	Convenience function. Same as unpack, except data may be longer
	than needed. The returned value is a tuple: (object, leftoverdata).

calcsize(fmt)
	like struct.calcsize(), but uses our own fmt strings:
	it returns the size of the data in bytes.
"""

from fontTools.misc.fixedTools import fixedToFloat as fi2fl, floatToFixed as fl2fi
from fontTools.misc.textTools import tobytes, tostr
import struct
import re

__version__ = "1.2"
__copyright__ = "Copyright 1998, Just van Rossum <just@letterror.com>"


class Error(Exception):
    pass


def pack(fmt, obj):
    formatstring, names, fixes = getformat(fmt, keep_pad_byte=True)
    elements = []
    if not isinstance(obj, dict):
        obj = obj.__dict__
    string_index = formatstring
    if formatstring.startswith(">"):
        string_index = formatstring[1:]
    for ix, name in enumerate(names.keys()):
        value = obj[name]
        if name in fixes:
            # fixed point conversion
            value = fl2fi(value, fixes[name])
        elif isinstance(value, str):
            value = tobytes(value)
        elements.append(value)
        # Check it fits
        try:
            struct.pack(names[name], value)
        except Exception as e:
            raise ValueError(
                "Value %s does not fit in format %s for %s" % (value, names[name], name)
            ) from e
    data = struct.pack(*(formatstring,) + tuple(elements))
    return data


def unpack(fmt, data, obj=None):
    if obj is None:
        obj = {}
    data = tobytes(data)
    formatstring, names, fixes = getformat(fmt)
    if isinstance(obj, dict):
        d = obj
    else:
        d = obj.__dict__
    elements = struct.unpack(formatstring, data)
    for i in range(len(names)):
        name = list(names.keys())[i]
        value = elements[i]
        if name in fixes:
            # fixed point conversion
            value = fi2fl(value, fixes[name])
        elif isinstance(value, bytes):
            try:
                value = tostr(value)
            except UnicodeDecodeError:
                pass
        d[name] = value
    return obj


def unpack2(fmt, data, obj=None):
    length = calcsize(fmt)
    return unpack(fmt, data[:length], obj), data[length:]


def calcsize(fmt):
    formatstring, names, fixes = getformat(fmt)
    return struct.calcsize(formatstring)


# matches "name:formatchar" (whitespace is allowed)
_elementRE = re.compile(
    r"\s*"  # whitespace
    r"([A-Za-z_][A-Za-z_0-9]*)"  # name (python identifier)
    r"\s*:\s*"  # whitespace : whitespace
    r"([xcbB?hHiIlLqQfd]|"  # formatchar...
    r"[0-9]+[ps]|"  # ...formatchar...
    r"([0-9]+)\.([0-9]+)(F))"  # ...formatchar
    r"\s*"  # whitespace
    r"(#.*)?$"  # [comment] + end of string
)

# matches the special struct fmt chars and 'x' (pad byte)
_extraRE = re.compile(r"\s*([x@=<>!])\s*(#.*)?$")

# matches an "empty" string, possibly containing whitespace and/or a comment
_emptyRE = re.compile(r"\s*(#.*)?$")

_fixedpointmappings = {8: "b", 16: "h", 32: "l"}

_formatcache = {}


def getformat(fmt, keep_pad_byte=False):
    fmt = tostr(fmt, encoding="ascii")
    try:
        formatstring, names, fixes = _formatcache[fmt]
    except KeyError:
        lines = re.split("[\n;]", fmt)
        formatstring = ""
        names = {}
        fixes = {}
        for line in lines:
            if _emptyRE.match(line):
                continue
            m = _extraRE.match(line)
            if m:
                formatchar = m.group(1)
                if formatchar != "x" and formatstring:
                    raise Error("a special fmt char must be first")
            else:
                m = _elementRE.match(line)
                if not m:
                    raise Error("syntax error in fmt: '%s'" % line)
                name = m.group(1)
                formatchar = m.group(2)
                if keep_pad_byte or formatchar != "x":
                    names[name] = formatchar
                if m.group(3):
                    # fixed point
                    before = int(m.group(3))
                    after = int(m.group(4))
                    bits = before + after
                    if bits not in [8, 16, 32]:
                        raise Error("fixed point must be 8, 16 or 32 bits long")
                    formatchar = _fixedpointmappings[bits]
                    names[name] = formatchar
                    assert m.group(5) == "F"
                    fixes[name] = after
            formatstring += formatchar
        _formatcache[fmt] = formatstring, names, fixes
    return formatstring, names, fixes


def _test():
    fmt = """
		# comments are allowed
		>  # big endian (see documentation for struct)
		# empty lines are allowed:

		ashort: h
		along: l
		abyte: b	# a byte
		achar: c
		astr: 5s
		afloat: f; adouble: d	# multiple "statements" are allowed
		afixed: 16.16F
		abool: ?
		apad: x
	"""

    print("size:", calcsize(fmt))

    class foo(object):
        pass

    i = foo()

    i.ashort = 0x7FFF
    i.along = 0x7FFFFFFF
    i.abyte = 0x7F
    i.achar = "a"
    i.astr = "12345"
    i.afloat = 0.5
    i.adouble = 0.5
    i.afixed = 1.5
    i.abool = True

    data = pack(fmt, i)
    print("data:", repr(data))
    print(unpack(fmt, data))
    i2 = foo()
    unpack(fmt, data, i2)
    print(vars(i2))


if __name__ == "__main__":
    _test()

# === NexusCore/openenv\Lib\site-packages\IPython\core\logger.py ===
"""Logger class for IPython's logging facilities.
"""

#*****************************************************************************
#       Copyright (C) 2001 Janko Hauser <jhauser@zscout.de> and
#       Copyright (C) 2001-2006 Fernando Perez <fperez@colorado.edu>
#
#  Distributed under the terms of the BSD License.  The full license is in
#  the file COPYING, distributed as part of this software.
#*****************************************************************************

#****************************************************************************
# Modules and globals

# Python standard modules
import glob
import io
import logging
import os
import time


# prevent jedi/parso's debug messages pipe into interactiveshell
logging.getLogger("parso").setLevel(logging.WARNING)

#****************************************************************************
# FIXME: This class isn't a mixin anymore, but it still needs attributes from
# ipython and does input cache management.  Finish cleanup later...

class Logger:
    """A Logfile class with different policies for file creation"""

    def __init__(self, home_dir, logfname='Logger.log', loghead=u'',
                 logmode='over'):

        # this is the full ipython instance, we need some attributes from it
        # which won't exist until later. What a mess, clean up later...
        self.home_dir = home_dir

        self.logfname = logfname
        self.loghead = loghead
        self.logmode = logmode
        self.logfile = None

        # Whether to log raw or processed input
        self.log_raw_input = False

        # whether to also log output
        self.log_output = False

        # whether to put timestamps before each log entry
        self.timestamp = False

        # activity control flags
        self.log_active = False

    # logmode is a validated property
    def _set_mode(self,mode):
        if mode not in ['append','backup','global','over','rotate']:
            raise ValueError('invalid log mode %s given' % mode)
        self._logmode = mode

    def _get_mode(self):
        return self._logmode

    logmode = property(_get_mode,_set_mode)

    def logstart(self, logfname=None, loghead=None, logmode=None,
                 log_output=False, timestamp=False, log_raw_input=False):
        """Generate a new log-file with a default header.

        Raises RuntimeError if the log has already been started"""

        if self.logfile is not None:
            raise RuntimeError('Log file is already active: %s' %
                               self.logfname)

        # The parameters can override constructor defaults
        if logfname is not None: self.logfname = logfname
        if loghead is not None: self.loghead = loghead
        if logmode is not None: self.logmode = logmode

        # Parameters not part of the constructor
        self.timestamp = timestamp
        self.log_output = log_output
        self.log_raw_input = log_raw_input

        # init depending on the log mode requested
        isfile = os.path.isfile
        logmode = self.logmode

        if logmode == 'append':
            self.logfile = io.open(self.logfname, 'a', encoding='utf-8')

        elif logmode == 'backup':
            if isfile(self.logfname):
                backup_logname = self.logfname+'~'
                # Manually remove any old backup, since os.rename may fail
                # under Windows.
                if isfile(backup_logname):
                    os.remove(backup_logname)
                os.rename(self.logfname,backup_logname)
            self.logfile = io.open(self.logfname, 'w', encoding='utf-8')

        elif logmode == 'global':
            self.logfname = os.path.join(self.home_dir,self.logfname)
            self.logfile = io.open(self.logfname, 'a', encoding='utf-8')

        elif logmode == 'over':
            if isfile(self.logfname):
                os.remove(self.logfname)
            self.logfile = io.open(self.logfname,'w', encoding='utf-8')

        elif logmode == 'rotate':
            if isfile(self.logfname):
                if isfile(self.logfname+'.001~'):
                    old = glob.glob(self.logfname+'.*~')
                    old.sort()
                    old.reverse()
                    for f in old:
                        root, ext = os.path.splitext(f)
                        num = int(ext[1:-1])+1
                        os.rename(f, root+'.'+repr(num).zfill(3)+'~')
                os.rename(self.logfname, self.logfname+'.001~')
            self.logfile = io.open(self.logfname, 'w', encoding='utf-8')

        if logmode != 'append':
            self.logfile.write(self.loghead)

        self.logfile.flush()
        self.log_active = True

    def switch_log(self,val):
        """Switch logging on/off. val should be ONLY a boolean."""

        if val not in [False,True,0,1]:
            raise ValueError('Call switch_log ONLY with a boolean argument, '
                             'not with: %s' % val)

        label = {0:'OFF',1:'ON',False:'OFF',True:'ON'}

        if self.logfile is None:
            print("""
Logging hasn't been started yet (use logstart for that).

%logon/%logoff are for temporarily starting and stopping logging for a logfile
which already exists. But you must first start the logging process with
%logstart (optionally giving a logfile name).""")

        else:
            if self.log_active == val:
                print('Logging is already',label[val])
            else:
                print('Switching logging',label[val])
                self.log_active = not self.log_active
                self.log_active_out = self.log_active

    def logstate(self):
        """Print a status message about the logger."""
        if self.logfile is None:
            print('Logging has not been activated.')
        else:
            state = self.log_active and 'active' or 'temporarily suspended'
            print('Filename       :', self.logfname)
            print('Mode           :', self.logmode)
            print('Output logging :', self.log_output)
            print('Raw input log  :', self.log_raw_input)
            print('Timestamping   :', self.timestamp)
            print('State          :', state)

    def log(self, line_mod, line_ori):
        """Write the sources to a log.

        Inputs:

        - line_mod: possibly modified input, such as the transformations made
          by input prefilters or input handlers of various kinds. This should
          always be valid Python.

        - line_ori: unmodified input line from the user. This is not
          necessarily valid Python.
        """

        # Write the log line, but decide which one according to the
        # log_raw_input flag, set when the log is started.
        if self.log_raw_input:
            self.log_write(line_ori)
        else:
            self.log_write(line_mod)

    def log_write(self, data, kind='input'):
        """Write data to the log file, if active"""

        # print('data: %r' % data)  # dbg
        if self.log_active and data:
            write = self.logfile.write
            if kind=='input':
                if self.timestamp:
                    write(time.strftime('# %a, %d %b %Y %H:%M:%S\n', time.localtime()))
                write(data)
            elif kind=='output' and self.log_output:
                odata = u'\n'.join([u'#[Out]# %s' % s
                                   for s in data.splitlines()])
                write(u'%s\n' % odata)
            try:
                self.logfile.flush()
            except OSError:
                print("Failed to flush the log file.")
                print(
                    f"Please check that {self.logfname} exists and have the right permissions."
                )
                print(
                    "Also consider turning off the log with `%logstop` to avoid this warning."
                )

    def logstop(self):
        """Fully stop logging and close log file.

        In order to start logging again, a new logstart() call needs to be
        made, possibly (though not necessarily) with a new filename, mode and
        other options."""

        if self.logfile is not None:
            self.logfile.close()
            self.logfile = None
        else:
            print("Logging hadn't been started.")
        self.log_active = False

    # For backwards compatibility, in case anyone was using this.
    close_log = logstop

# === NexusCore/openenv\Lib\site-packages\numpy\f2py\_backends\_meson.py ===
import errno
import os
import re
import shutil
import subprocess
import sys
from itertools import chain
from pathlib import Path
from string import Template

from ._backend import Backend


class MesonTemplate:
    """Template meson build file generation class."""

    def __init__(
        self,
        modulename: str,
        sources: list[Path],
        deps: list[str],
        libraries: list[str],
        library_dirs: list[Path],
        include_dirs: list[Path],
        object_files: list[Path],
        linker_args: list[str],
        fortran_args: list[str],
        build_type: str,
        python_exe: str,
    ):
        self.modulename = modulename
        self.build_template_path = (
            Path(__file__).parent.absolute() / "meson.build.template"
        )
        self.sources = sources
        self.deps = deps
        self.libraries = libraries
        self.library_dirs = library_dirs
        if include_dirs is not None:
            self.include_dirs = include_dirs
        else:
            self.include_dirs = []
        self.substitutions = {}
        self.objects = object_files
        # Convert args to '' wrapped variant for meson
        self.fortran_args = [
            f"'{x}'" if not (x.startswith("'") and x.endswith("'")) else x
            for x in fortran_args
        ]
        self.pipeline = [
            self.initialize_template,
            self.sources_substitution,
            self.deps_substitution,
            self.include_substitution,
            self.libraries_substitution,
            self.fortran_args_substitution,
        ]
        self.build_type = build_type
        self.python_exe = python_exe
        self.indent = " " * 21

    def meson_build_template(self) -> str:
        if not self.build_template_path.is_file():
            raise FileNotFoundError(
                errno.ENOENT,
                "Meson build template"
                f" {self.build_template_path.absolute()}"
                " does not exist.",
            )
        return self.build_template_path.read_text()

    def initialize_template(self) -> None:
        self.substitutions["modulename"] = self.modulename
        self.substitutions["buildtype"] = self.build_type
        self.substitutions["python"] = self.python_exe

    def sources_substitution(self) -> None:
        self.substitutions["source_list"] = ",\n".join(
            [f"{self.indent}'''{source}'''," for source in self.sources]
        )

    def deps_substitution(self) -> None:
        self.substitutions["dep_list"] = f",\n{self.indent}".join(
            [f"{self.indent}dependency('{dep}')," for dep in self.deps]
        )

    def libraries_substitution(self) -> None:
        self.substitutions["lib_dir_declarations"] = "\n".join(
            [
                f"lib_dir_{i} = declare_dependency(link_args : ['''-L{lib_dir}'''])"
                for i, lib_dir in enumerate(self.library_dirs)
            ]
        )

        self.substitutions["lib_declarations"] = "\n".join(
            [
                f"{lib.replace('.', '_')} = declare_dependency(link_args : ['-l{lib}'])"
                for lib in self.libraries
            ]
        )

        self.substitutions["lib_list"] = f"\n{self.indent}".join(
            [f"{self.indent}{lib.replace('.', '_')}," for lib in self.libraries]
        )
        self.substitutions["lib_dir_list"] = f"\n{self.indent}".join(
            [f"{self.indent}lib_dir_{i}," for i in range(len(self.library_dirs))]
        )

    def include_substitution(self) -> None:
        self.substitutions["inc_list"] = f",\n{self.indent}".join(
            [f"{self.indent}'''{inc}'''," for inc in self.include_dirs]
        )

    def fortran_args_substitution(self) -> None:
        if self.fortran_args:
            self.substitutions["fortran_args"] = (
                f"{self.indent}fortran_args: [{', '.join(list(self.fortran_args))}],"
            )
        else:
            self.substitutions["fortran_args"] = ""

    def generate_meson_build(self):
        for node in self.pipeline:
            node()
        template = Template(self.meson_build_template())
        meson_build = template.substitute(self.substitutions)
        meson_build = meson_build.replace(",,", ",")
        return meson_build


class MesonBackend(Backend):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.dependencies = self.extra_dat.get("dependencies", [])
        self.meson_build_dir = "bbdir"
        self.build_type = (
            "debug" if any("debug" in flag for flag in self.fc_flags) else "release"
        )
        self.fc_flags = _get_flags(self.fc_flags)

    def _move_exec_to_root(self, build_dir: Path):
        walk_dir = Path(build_dir) / self.meson_build_dir
        path_objects = chain(
            walk_dir.glob(f"{self.modulename}*.so"),
            walk_dir.glob(f"{self.modulename}*.pyd"),
            walk_dir.glob(f"{self.modulename}*.dll"),
        )
        # Same behavior as distutils
        # https://github.com/numpy/numpy/issues/24874#issuecomment-1835632293
        for path_object in path_objects:
            dest_path = Path.cwd() / path_object.name
            if dest_path.exists():
                dest_path.unlink()
            shutil.copy2(path_object, dest_path)
            os.remove(path_object)

    def write_meson_build(self, build_dir: Path) -> None:
        """Writes the meson build file at specified location"""
        meson_template = MesonTemplate(
            self.modulename,
            self.sources,
            self.dependencies,
            self.libraries,
            self.library_dirs,
            self.include_dirs,
            self.extra_objects,
            self.flib_flags,
            self.fc_flags,
            self.build_type,
            sys.executable,
        )
        src = meson_template.generate_meson_build()
        Path(build_dir).mkdir(parents=True, exist_ok=True)
        meson_build_file = Path(build_dir) / "meson.build"
        meson_build_file.write_text(src)
        return meson_build_file

    def _run_subprocess_command(self, command, cwd):
        subprocess.run(command, cwd=cwd, check=True)

    def run_meson(self, build_dir: Path):
        setup_command = ["meson", "setup", self.meson_build_dir]
        self._run_subprocess_command(setup_command, build_dir)
        compile_command = ["meson", "compile", "-C", self.meson_build_dir]
        self._run_subprocess_command(compile_command, build_dir)

    def compile(self) -> None:
        self.sources = _prepare_sources(self.modulename, self.sources, self.build_dir)
        self.write_meson_build(self.build_dir)
        self.run_meson(self.build_dir)
        self._move_exec_to_root(self.build_dir)


def _prepare_sources(mname, sources, bdir):
    extended_sources = sources.copy()
    Path(bdir).mkdir(parents=True, exist_ok=True)
    # Copy sources
    for source in sources:
        if Path(source).exists() and Path(source).is_file():
            shutil.copy(source, bdir)
    generated_sources = [
        Path(f"{mname}module.c"),
        Path(f"{mname}-f2pywrappers2.f90"),
        Path(f"{mname}-f2pywrappers.f"),
    ]
    bdir = Path(bdir)
    for generated_source in generated_sources:
        if generated_source.exists():
            shutil.copy(generated_source, bdir / generated_source.name)
            extended_sources.append(generated_source.name)
            generated_source.unlink()
    extended_sources = [
        Path(source).name
        for source in extended_sources
        if not Path(source).suffix == ".pyf"
    ]
    return extended_sources


def _get_flags(fc_flags):
    flag_values = []
    flag_pattern = re.compile(r"--f(77|90)flags=(.*)")
    for flag in fc_flags:
        match_result = flag_pattern.match(flag)
        if match_result:
            values = match_result.group(2).strip().split()
            values = [val.strip("'\"") for val in values]
            flag_values.extend(values)
    # Hacky way to preserve order of flags
    unique_flags = list(dict.fromkeys(flag_values))
    return unique_flags

# === NexusCore/openenv\Lib\site-packages\pygments\lexers\_cl_builtins.py ===
"""
    pygments.lexers._cl_builtins
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    ANSI Common Lisp builtins.

    :copyright: Copyright 2006-2025 by the Pygments team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

BUILTIN_FUNCTIONS = {  # 638 functions
    '<', '<=', '=', '>', '>=', '-', '/', '/=', '*', '+', '1-', '1+',
    'abort', 'abs', 'acons', 'acos', 'acosh', 'add-method', 'adjoin',
    'adjustable-array-p', 'adjust-array', 'allocate-instance',
    'alpha-char-p', 'alphanumericp', 'append', 'apply', 'apropos',
    'apropos-list', 'aref', 'arithmetic-error-operands',
    'arithmetic-error-operation', 'array-dimension', 'array-dimensions',
    'array-displacement', 'array-element-type', 'array-has-fill-pointer-p',
    'array-in-bounds-p', 'arrayp', 'array-rank', 'array-row-major-index',
    'array-total-size', 'ash', 'asin', 'asinh', 'assoc', 'assoc-if',
    'assoc-if-not', 'atan', 'atanh', 'atom', 'bit', 'bit-and', 'bit-andc1',
    'bit-andc2', 'bit-eqv', 'bit-ior', 'bit-nand', 'bit-nor', 'bit-not',
    'bit-orc1', 'bit-orc2', 'bit-vector-p', 'bit-xor', 'boole',
    'both-case-p', 'boundp', 'break', 'broadcast-stream-streams',
    'butlast', 'byte', 'byte-position', 'byte-size', 'caaaar', 'caaadr',
    'caaar', 'caadar', 'caaddr', 'caadr', 'caar', 'cadaar', 'cadadr',
    'cadar', 'caddar', 'cadddr', 'caddr', 'cadr', 'call-next-method', 'car',
    'cdaaar', 'cdaadr', 'cdaar', 'cdadar', 'cdaddr', 'cdadr', 'cdar',
    'cddaar', 'cddadr', 'cddar', 'cdddar', 'cddddr', 'cdddr', 'cddr', 'cdr',
    'ceiling', 'cell-error-name', 'cerror', 'change-class', 'char', 'char<',
    'char<=', 'char=', 'char>', 'char>=', 'char/=', 'character',
    'characterp', 'char-code', 'char-downcase', 'char-equal',
    'char-greaterp', 'char-int', 'char-lessp', 'char-name',
    'char-not-equal', 'char-not-greaterp', 'char-not-lessp', 'char-upcase',
    'cis', 'class-name', 'class-of', 'clear-input', 'clear-output',
    'close', 'clrhash', 'code-char', 'coerce', 'compile',
    'compiled-function-p', 'compile-file', 'compile-file-pathname',
    'compiler-macro-function', 'complement', 'complex', 'complexp',
    'compute-applicable-methods', 'compute-restarts', 'concatenate',
    'concatenated-stream-streams', 'conjugate', 'cons', 'consp',
    'constantly', 'constantp', 'continue', 'copy-alist', 'copy-list',
    'copy-pprint-dispatch', 'copy-readtable', 'copy-seq', 'copy-structure',
    'copy-symbol', 'copy-tree', 'cos', 'cosh', 'count', 'count-if',
    'count-if-not', 'decode-float', 'decode-universal-time', 'delete',
    'delete-duplicates', 'delete-file', 'delete-if', 'delete-if-not',
    'delete-package', 'denominator', 'deposit-field', 'describe',
    'describe-object', 'digit-char', 'digit-char-p', 'directory',
    'directory-namestring', 'disassemble', 'documentation', 'dpb',
    'dribble', 'echo-stream-input-stream', 'echo-stream-output-stream',
    'ed', 'eighth', 'elt', 'encode-universal-time', 'endp',
    'enough-namestring', 'ensure-directories-exist',
    'ensure-generic-function', 'eq', 'eql', 'equal', 'equalp', 'error',
    'eval', 'evenp', 'every', 'exp', 'export', 'expt', 'fboundp',
    'fceiling', 'fdefinition', 'ffloor', 'fifth', 'file-author',
    'file-error-pathname', 'file-length', 'file-namestring',
    'file-position', 'file-string-length', 'file-write-date',
    'fill', 'fill-pointer', 'find', 'find-all-symbols', 'find-class',
    'find-if', 'find-if-not', 'find-method', 'find-package', 'find-restart',
    'find-symbol', 'finish-output', 'first', 'float', 'float-digits',
    'floatp', 'float-precision', 'float-radix', 'float-sign', 'floor',
    'fmakunbound', 'force-output', 'format', 'fourth', 'fresh-line',
    'fround', 'ftruncate', 'funcall', 'function-keywords',
    'function-lambda-expression', 'functionp', 'gcd', 'gensym', 'gentemp',
    'get', 'get-decoded-time', 'get-dispatch-macro-character', 'getf',
    'gethash', 'get-internal-real-time', 'get-internal-run-time',
    'get-macro-character', 'get-output-stream-string', 'get-properties',
    'get-setf-expansion', 'get-universal-time', 'graphic-char-p',
    'hash-table-count', 'hash-table-p', 'hash-table-rehash-size',
    'hash-table-rehash-threshold', 'hash-table-size', 'hash-table-test',
    'host-namestring', 'identity', 'imagpart', 'import',
    'initialize-instance', 'input-stream-p', 'inspect',
    'integer-decode-float', 'integer-length', 'integerp',
    'interactive-stream-p', 'intern', 'intersection',
    'invalid-method-error', 'invoke-debugger', 'invoke-restart',
    'invoke-restart-interactively', 'isqrt', 'keywordp', 'last', 'lcm',
    'ldb', 'ldb-test', 'ldiff', 'length', 'lisp-implementation-type',
    'lisp-implementation-version', 'list', 'list*', 'list-all-packages',
    'listen', 'list-length', 'listp', 'load',
    'load-logical-pathname-translations', 'log', 'logand', 'logandc1',
    'logandc2', 'logbitp', 'logcount', 'logeqv', 'logical-pathname',
    'logical-pathname-translations', 'logior', 'lognand', 'lognor',
    'lognot', 'logorc1', 'logorc2', 'logtest', 'logxor', 'long-site-name',
    'lower-case-p', 'machine-instance', 'machine-type', 'machine-version',
    'macroexpand', 'macroexpand-1', 'macro-function', 'make-array',
    'make-broadcast-stream', 'make-concatenated-stream', 'make-condition',
    'make-dispatch-macro-character', 'make-echo-stream', 'make-hash-table',
    'make-instance', 'make-instances-obsolete', 'make-list',
    'make-load-form', 'make-load-form-saving-slots', 'make-package',
    'make-pathname', 'make-random-state', 'make-sequence', 'make-string',
    'make-string-input-stream', 'make-string-output-stream', 'make-symbol',
    'make-synonym-stream', 'make-two-way-stream', 'makunbound', 'map',
    'mapc', 'mapcan', 'mapcar', 'mapcon', 'maphash', 'map-into', 'mapl',
    'maplist', 'mask-field', 'max', 'member', 'member-if', 'member-if-not',
    'merge', 'merge-pathnames', 'method-combination-error',
    'method-qualifiers', 'min', 'minusp', 'mismatch', 'mod',
    'muffle-warning', 'name-char', 'namestring', 'nbutlast', 'nconc',
    'next-method-p', 'nintersection', 'ninth', 'no-applicable-method',
    'no-next-method', 'not', 'notany', 'notevery', 'nreconc', 'nreverse',
    'nset-difference', 'nset-exclusive-or', 'nstring-capitalize',
    'nstring-downcase', 'nstring-upcase', 'nsublis', 'nsubst', 'nsubst-if',
    'nsubst-if-not', 'nsubstitute', 'nsubstitute-if', 'nsubstitute-if-not',
    'nth', 'nthcdr', 'null', 'numberp', 'numerator', 'nunion', 'oddp',
    'open', 'open-stream-p', 'output-stream-p', 'package-error-package',
    'package-name', 'package-nicknames', 'packagep',
    'package-shadowing-symbols', 'package-used-by-list', 'package-use-list',
    'pairlis', 'parse-integer', 'parse-namestring', 'pathname',
    'pathname-device', 'pathname-directory', 'pathname-host',
    'pathname-match-p', 'pathname-name', 'pathnamep', 'pathname-type',
    'pathname-version', 'peek-char', 'phase', 'plusp', 'position',
    'position-if', 'position-if-not', 'pprint', 'pprint-dispatch',
    'pprint-fill', 'pprint-indent', 'pprint-linear', 'pprint-newline',
    'pprint-tab', 'pprint-tabular', 'prin1', 'prin1-to-string', 'princ',
    'princ-to-string', 'print', 'print-object', 'probe-file', 'proclaim',
    'provide', 'random', 'random-state-p', 'rassoc', 'rassoc-if',
    'rassoc-if-not', 'rational', 'rationalize', 'rationalp', 'read',
    'read-byte', 'read-char', 'read-char-no-hang', 'read-delimited-list',
    'read-from-string', 'read-line', 'read-preserving-whitespace',
    'read-sequence', 'readtable-case', 'readtablep', 'realp', 'realpart',
    'reduce', 'reinitialize-instance', 'rem', 'remhash', 'remove',
    'remove-duplicates', 'remove-if', 'remove-if-not', 'remove-method',
    'remprop', 'rename-file', 'rename-package', 'replace', 'require',
    'rest', 'restart-name', 'revappend', 'reverse', 'room', 'round',
    'row-major-aref', 'rplaca', 'rplacd', 'sbit', 'scale-float', 'schar',
    'search', 'second', 'set', 'set-difference',
    'set-dispatch-macro-character', 'set-exclusive-or',
    'set-macro-character', 'set-pprint-dispatch', 'set-syntax-from-char',
    'seventh', 'shadow', 'shadowing-import', 'shared-initialize',
    'short-site-name', 'signal', 'signum', 'simple-bit-vector-p',
    'simple-condition-format-arguments', 'simple-condition-format-control',
    'simple-string-p', 'simple-vector-p', 'sin', 'sinh', 'sixth', 'sleep',
    'slot-boundp', 'slot-exists-p', 'slot-makunbound', 'slot-missing',
    'slot-unbound', 'slot-value', 'software-type', 'software-version',
    'some', 'sort', 'special-operator-p', 'sqrt', 'stable-sort',
    'standard-char-p', 'store-value', 'stream-element-type',
    'stream-error-stream', 'stream-external-format', 'streamp', 'string',
    'string<', 'string<=', 'string=', 'string>', 'string>=', 'string/=',
    'string-capitalize', 'string-downcase', 'string-equal',
    'string-greaterp', 'string-left-trim', 'string-lessp',
    'string-not-equal', 'string-not-greaterp', 'string-not-lessp',
    'stringp', 'string-right-trim', 'string-trim', 'string-upcase',
    'sublis', 'subseq', 'subsetp', 'subst', 'subst-if', 'subst-if-not',
    'substitute', 'substitute-if', 'substitute-if-not', 'subtypep','svref',
    'sxhash', 'symbol-function', 'symbol-name', 'symbolp', 'symbol-package',
    'symbol-plist', 'symbol-value', 'synonym-stream-symbol', 'syntax:',
    'tailp', 'tan', 'tanh', 'tenth', 'terpri', 'third',
    'translate-logical-pathname', 'translate-pathname', 'tree-equal',
    'truename', 'truncate', 'two-way-stream-input-stream',
    'two-way-stream-output-stream', 'type-error-datum',
    'type-error-expected-type', 'type-of', 'typep', 'unbound-slot-instance',
    'unexport', 'unintern', 'union', 'unread-char', 'unuse-package',
    'update-instance-for-different-class',
    'update-instance-for-redefined-class', 'upgraded-array-element-type',
    'upgraded-complex-part-type', 'upper-case-p', 'use-package',
    'user-homedir-pathname', 'use-value', 'values', 'values-list', 'vector',
    'vectorp', 'vector-pop', 'vector-push', 'vector-push-extend', 'warn',
    'wild-pathname-p', 'write', 'write-byte', 'write-char', 'write-line',
    'write-sequence', 'write-string', 'write-to-string', 'yes-or-no-p',
    'y-or-n-p', 'zerop',
}

SPECIAL_FORMS = {
    'block', 'catch', 'declare', 'eval-when', 'flet', 'function', 'go', 'if',
    'labels', 'lambda', 'let', 'let*', 'load-time-value', 'locally', 'macrolet',
    'multiple-value-call', 'multiple-value-prog1', 'progn', 'progv', 'quote',
    'return-from', 'setq', 'symbol-macrolet', 'tagbody', 'the', 'throw',
    'unwind-protect',
}

MACROS = {
    'and', 'assert', 'call-method', 'case', 'ccase', 'check-type', 'cond',
    'ctypecase', 'decf', 'declaim', 'defclass', 'defconstant', 'defgeneric',
    'define-compiler-macro', 'define-condition', 'define-method-combination',
    'define-modify-macro', 'define-setf-expander', 'define-symbol-macro',
    'defmacro', 'defmethod', 'defpackage', 'defparameter', 'defsetf',
    'defstruct', 'deftype', 'defun', 'defvar', 'destructuring-bind', 'do',
    'do*', 'do-all-symbols', 'do-external-symbols', 'dolist', 'do-symbols',
    'dotimes', 'ecase', 'etypecase', 'formatter', 'handler-bind',
    'handler-case', 'ignore-errors', 'incf', 'in-package', 'lambda', 'loop',
    'loop-finish', 'make-method', 'multiple-value-bind', 'multiple-value-list',
    'multiple-value-setq', 'nth-value', 'or', 'pop',
    'pprint-exit-if-list-exhausted', 'pprint-logical-block', 'pprint-pop',
    'print-unreadable-object', 'prog', 'prog*', 'prog1', 'prog2', 'psetf',
    'psetq', 'push', 'pushnew', 'remf', 'restart-bind', 'restart-case',
    'return', 'rotatef', 'setf', 'shiftf', 'step', 'time', 'trace', 'typecase',
    'unless', 'untrace', 'when', 'with-accessors', 'with-compilation-unit',
    'with-condition-restarts', 'with-hash-table-iterator',
    'with-input-from-string', 'with-open-file', 'with-open-stream',
    'with-output-to-string', 'with-package-iterator', 'with-simple-restart',
    'with-slots', 'with-standard-io-syntax',
}

LAMBDA_LIST_KEYWORDS = {
    '&allow-other-keys', '&aux', '&body', '&environment', '&key', '&optional',
    '&rest', '&whole',
}

DECLARATIONS = {
    'dynamic-extent', 'ignore', 'optimize', 'ftype', 'inline', 'special',
    'ignorable', 'notinline', 'type',
}

BUILTIN_TYPES = {
    'atom', 'boolean', 'base-char', 'base-string', 'bignum', 'bit',
    'compiled-function', 'extended-char', 'fixnum', 'keyword', 'nil',
    'signed-byte', 'short-float', 'single-float', 'double-float', 'long-float',
    'simple-array', 'simple-base-string', 'simple-bit-vector', 'simple-string',
    'simple-vector', 'standard-char', 'unsigned-byte',

    # Condition Types
    'arithmetic-error', 'cell-error', 'condition', 'control-error',
    'division-by-zero', 'end-of-file', 'error', 'file-error',
    'floating-point-inexact', 'floating-point-overflow',
    'floating-point-underflow', 'floating-point-invalid-operation',
    'parse-error', 'package-error', 'print-not-readable', 'program-error',
    'reader-error', 'serious-condition', 'simple-condition', 'simple-error',
    'simple-type-error', 'simple-warning', 'stream-error', 'storage-condition',
    'style-warning', 'type-error', 'unbound-variable', 'unbound-slot',
    'undefined-function', 'warning',
}

BUILTIN_CLASSES = {
    'array', 'broadcast-stream', 'bit-vector', 'built-in-class', 'character',
    'class', 'complex', 'concatenated-stream', 'cons', 'echo-stream',
    'file-stream', 'float', 'function', 'generic-function', 'hash-table',
    'integer', 'list', 'logical-pathname', 'method-combination', 'method',
    'null', 'number', 'package', 'pathname', 'ratio', 'rational', 'readtable',
    'real', 'random-state', 'restart', 'sequence', 'standard-class',
    'standard-generic-function', 'standard-method', 'standard-object',
    'string-stream', 'stream', 'string', 'structure-class', 'structure-object',
    'symbol', 'synonym-stream', 't', 'two-way-stream', 'vector',
}

# === NexusCore/openenv\Lib\site-packages\tornado\test\concurrent_test.py ===
#
# Copyright 2012 Facebook
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
from concurrent import futures
import logging
import re
import socket
import unittest

from tornado.concurrent import (
    Future,
    chain_future,
    run_on_executor,
    future_set_result_unless_cancelled,
)
from tornado.escape import utf8, to_unicode
from tornado import gen
from tornado.iostream import IOStream
from tornado.tcpserver import TCPServer
from tornado.testing import AsyncTestCase, bind_unused_port, gen_test


class MiscFutureTest(AsyncTestCase):
    def test_future_set_result_unless_cancelled(self):
        fut = Future()  # type: Future[int]
        future_set_result_unless_cancelled(fut, 42)
        self.assertEqual(fut.result(), 42)
        self.assertFalse(fut.cancelled())

        fut = Future()
        fut.cancel()
        is_cancelled = fut.cancelled()
        future_set_result_unless_cancelled(fut, 42)
        self.assertEqual(fut.cancelled(), is_cancelled)
        if not is_cancelled:
            self.assertEqual(fut.result(), 42)


class ChainFutureTest(AsyncTestCase):
    @gen_test
    async def test_asyncio_futures(self):
        fut: Future[int] = Future()
        fut2: Future[int] = Future()
        chain_future(fut, fut2)
        fut.set_result(42)
        result = await fut2
        self.assertEqual(result, 42)

    @gen_test
    async def test_concurrent_futures(self):
        # A three-step chain: two concurrent futures (showing that both arguments to chain_future
        # can be concurrent futures), and then one from a concurrent future to an asyncio future so
        # we can use it in await.
        fut: futures.Future[int] = futures.Future()
        fut2: futures.Future[int] = futures.Future()
        fut3: Future[int] = Future()
        chain_future(fut, fut2)
        chain_future(fut2, fut3)
        fut.set_result(42)
        result = await fut3
        self.assertEqual(result, 42)


# The following series of classes demonstrate and test various styles
# of use, with and without generators and futures.


class CapServer(TCPServer):
    @gen.coroutine
    def handle_stream(self, stream, address):
        data = yield stream.read_until(b"\n")
        data = to_unicode(data)
        if data == data.upper():
            stream.write(b"error\talready capitalized\n")
        else:
            # data already has \n
            stream.write(utf8("ok\t%s" % data.upper()))
        stream.close()


class CapError(Exception):
    pass


class BaseCapClient:
    def __init__(self, port):
        self.port = port

    def process_response(self, data):
        m = re.match("(.*)\t(.*)\n", to_unicode(data))
        if m is None:
            raise Exception("did not match")
        status, message = m.groups()
        if status == "ok":
            return message
        else:
            raise CapError(message)


class GeneratorCapClient(BaseCapClient):
    @gen.coroutine
    def capitalize(self, request_data):
        logging.debug("capitalize")
        stream = IOStream(socket.socket())
        logging.debug("connecting")
        yield stream.connect(("127.0.0.1", self.port))
        stream.write(utf8(request_data + "\n"))
        logging.debug("reading")
        data = yield stream.read_until(b"\n")
        logging.debug("returning")
        stream.close()
        raise gen.Return(self.process_response(data))


class GeneratorCapClientTest(AsyncTestCase):
    def setUp(self):
        super().setUp()
        self.server = CapServer()
        sock, port = bind_unused_port()
        self.server.add_sockets([sock])
        self.client = GeneratorCapClient(port=port)

    def tearDown(self):
        self.server.stop()
        super().tearDown()

    def test_future(self):
        future = self.client.capitalize("hello")
        self.io_loop.add_future(future, self.stop)
        self.wait()
        self.assertEqual(future.result(), "HELLO")

    def test_future_error(self):
        future = self.client.capitalize("HELLO")
        self.io_loop.add_future(future, self.stop)
        self.wait()
        self.assertRaisesRegex(CapError, "already capitalized", future.result)

    def test_generator(self):
        @gen.coroutine
        def f():
            result = yield self.client.capitalize("hello")
            self.assertEqual(result, "HELLO")

        self.io_loop.run_sync(f)

    def test_generator_error(self):
        @gen.coroutine
        def f():
            with self.assertRaisesRegex(CapError, "already capitalized"):
                yield self.client.capitalize("HELLO")

        self.io_loop.run_sync(f)


class RunOnExecutorTest(AsyncTestCase):
    @gen_test
    def test_no_calling(self):
        class Object:
            def __init__(self):
                self.executor = futures.thread.ThreadPoolExecutor(1)

            @run_on_executor
            def f(self):
                return 42

        o = Object()
        answer = yield o.f()
        self.assertEqual(answer, 42)

    @gen_test
    def test_call_with_no_args(self):
        class Object:
            def __init__(self):
                self.executor = futures.thread.ThreadPoolExecutor(1)

            @run_on_executor()
            def f(self):
                return 42

        o = Object()
        answer = yield o.f()
        self.assertEqual(answer, 42)

    @gen_test
    def test_call_with_executor(self):
        class Object:
            def __init__(self):
                self.__executor = futures.thread.ThreadPoolExecutor(1)

            @run_on_executor(executor="_Object__executor")
            def f(self):
                return 42

        o = Object()
        answer = yield o.f()
        self.assertEqual(answer, 42)

    @gen_test
    def test_async_await(self):
        class Object:
            def __init__(self):
                self.executor = futures.thread.ThreadPoolExecutor(1)

            @run_on_executor()
            def f(self):
                return 42

        o = Object()

        async def f():
            answer = await o.f()
            return answer

        result = yield f()
        self.assertEqual(result, 42)


if __name__ == "__main__":
    unittest.main()

# === NexusCore/openenv\Lib\site-packages\litellm\budget_manager.py ===
# +-----------------------------------------------+
# |                                               |
# |           NOT PROXY BUDGET MANAGER            |
# |  proxy budget manager is in proxy_server.py   |
# |                                               |
# +-----------------------------------------------+
#
#  Thank you users! We ❤️ you! - Krrish & Ishaan

import json
import os
import threading
import time
from typing import Literal, Optional

import litellm
from litellm.constants import (
    DAYS_IN_A_MONTH,
    DAYS_IN_A_WEEK,
    DAYS_IN_A_YEAR,
    HOURS_IN_A_DAY,
)
from litellm.utils import ModelResponse


class BudgetManager:
    def __init__(
        self,
        project_name: str,
        client_type: str = "local",
        api_base: Optional[str] = None,
        headers: Optional[dict] = None,
    ):
        self.client_type = client_type
        self.project_name = project_name
        self.api_base = api_base or "https://api.litellm.ai"
        self.headers = headers or {"Content-Type": "application/json"}
        ## load the data or init the initial dictionaries
        self.load_data()

    def print_verbose(self, print_statement):
        try:
            if litellm.set_verbose:
                import logging

                logging.info(print_statement)
        except Exception:
            pass

    def load_data(self):
        if self.client_type == "local":
            # Check if user dict file exists
            if os.path.isfile("user_cost.json"):
                # Load the user dict
                with open("user_cost.json", "r") as json_file:
                    self.user_dict = json.load(json_file)
            else:
                self.print_verbose("User Dictionary not found!")
                self.user_dict = {}
            self.print_verbose(f"user dict from local: {self.user_dict}")
        elif self.client_type == "hosted":
            # Load the user_dict from hosted db
            url = self.api_base + "/get_budget"
            data = {"project_name": self.project_name}
            response = litellm.module_level_client.post(
                url, headers=self.headers, json=data
            )
            response = response.json()
            if response["status"] == "error":
                self.user_dict = (
                    {}
                )  # assume this means the user dict hasn't been stored yet
            else:
                self.user_dict = response["data"]

    def create_budget(
        self,
        total_budget: float,
        user: str,
        duration: Optional[Literal["daily", "weekly", "monthly", "yearly"]] = None,
        created_at: float = time.time(),
    ):
        self.user_dict[user] = {"total_budget": total_budget}
        if duration is None:
            return self.user_dict[user]

        if duration == "daily":
            duration_in_days = 1
        elif duration == "weekly":
            duration_in_days = DAYS_IN_A_WEEK
        elif duration == "monthly":
            duration_in_days = DAYS_IN_A_MONTH
        elif duration == "yearly":
            duration_in_days = DAYS_IN_A_YEAR
        else:
            raise ValueError(
                """duration needs to be one of ["daily", "weekly", "monthly", "yearly"]"""
            )
        self.user_dict[user] = {
            "total_budget": total_budget,
            "duration": duration_in_days,
            "created_at": created_at,
            "last_updated_at": created_at,
        }
        self._save_data_thread()  # [Non-Blocking] Update persistent storage without blocking execution
        return self.user_dict[user]

    def projected_cost(self, model: str, messages: list, user: str):
        text = "".join(message["content"] for message in messages)
        prompt_tokens = litellm.token_counter(model=model, text=text)
        prompt_cost, _ = litellm.cost_per_token(
            model=model, prompt_tokens=prompt_tokens, completion_tokens=0
        )
        current_cost = self.user_dict[user].get("current_cost", 0)
        projected_cost = prompt_cost + current_cost
        return projected_cost

    def get_total_budget(self, user: str):
        return self.user_dict[user]["total_budget"]

    def update_cost(
        self,
        user: str,
        completion_obj: Optional[ModelResponse] = None,
        model: Optional[str] = None,
        input_text: Optional[str] = None,
        output_text: Optional[str] = None,
    ):
        if model and input_text and output_text:
            prompt_tokens = litellm.token_counter(
                model=model, messages=[{"role": "user", "content": input_text}]
            )
            completion_tokens = litellm.token_counter(
                model=model, messages=[{"role": "user", "content": output_text}]
            )
            (
                prompt_tokens_cost_usd_dollar,
                completion_tokens_cost_usd_dollar,
            ) = litellm.cost_per_token(
                model=model,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
            )
            cost = prompt_tokens_cost_usd_dollar + completion_tokens_cost_usd_dollar
        elif completion_obj:
            cost = litellm.completion_cost(completion_response=completion_obj)
            model = completion_obj[
                "model"
            ]  # if this throws an error try, model = completion_obj['model']
        else:
            raise ValueError(
                "Either a chat completion object or the text response needs to be passed in. Learn more - https://docs.litellm.ai/docs/budget_manager"
            )

        self.user_dict[user]["current_cost"] = cost + self.user_dict[user].get(
            "current_cost", 0
        )
        if "model_cost" in self.user_dict[user]:
            self.user_dict[user]["model_cost"][model] = cost + self.user_dict[user][
                "model_cost"
            ].get(model, 0)
        else:
            self.user_dict[user]["model_cost"] = {model: cost}

        self._save_data_thread()  # [Non-Blocking] Update persistent storage without blocking execution
        return {"user": self.user_dict[user]}

    def get_current_cost(self, user):
        return self.user_dict[user].get("current_cost", 0)

    def get_model_cost(self, user):
        return self.user_dict[user].get("model_cost", 0)

    def is_valid_user(self, user: str) -> bool:
        return user in self.user_dict

    def get_users(self):
        return list(self.user_dict.keys())

    def reset_cost(self, user):
        self.user_dict[user]["current_cost"] = 0
        self.user_dict[user]["model_cost"] = {}
        return {"user": self.user_dict[user]}

    def reset_on_duration(self, user: str):
        # Get current and creation time
        last_updated_at = self.user_dict[user]["last_updated_at"]
        current_time = time.time()

        # Convert duration from days to seconds
        duration_in_seconds = (
            self.user_dict[user]["duration"] * HOURS_IN_A_DAY * 60 * 60
        )

        # Check if duration has elapsed
        if current_time - last_updated_at >= duration_in_seconds:
            # Reset cost if duration has elapsed and update the creation time
            self.reset_cost(user)
            self.user_dict[user]["last_updated_at"] = current_time
            self._save_data_thread()  # Save the data

    def update_budget_all_users(self):
        for user in self.get_users():
            if "duration" in self.user_dict[user]:
                self.reset_on_duration(user)

    def _save_data_thread(self):
        thread = threading.Thread(
            target=self.save_data
        )  # [Non-Blocking]: saves data without blocking execution
        thread.start()

    def save_data(self):
        if self.client_type == "local":
            import json

            # save the user dict
            with open("user_cost.json", "w") as json_file:
                json.dump(
                    self.user_dict, json_file, indent=4
                )  # Indent for pretty formatting
            return {"status": "success"}
        elif self.client_type == "hosted":
            url = self.api_base + "/set_budget"
            data = {"project_name": self.project_name, "user_dict": self.user_dict}
            response = litellm.module_level_client.post(
                url, headers=self.headers, json=data
            )
            response = response.json()
            return response

# === NexusCore/openenv\Lib\site-packages\google\ai\generativelanguage_v1beta\services\cache_service\transports\base.py ===
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
import abc
from typing import Awaitable, Callable, Dict, Optional, Sequence, Union

import google.api_core
from google.api_core import exceptions as core_exceptions
from google.api_core import gapic_v1
from google.api_core import retry as retries
import google.auth  # type: ignore
from google.auth import credentials as ga_credentials  # type: ignore
from google.longrunning import operations_pb2  # type: ignore
from google.oauth2 import service_account  # type: ignore
from google.protobuf import empty_pb2  # type: ignore

from google.ai.generativelanguage_v1beta import gapic_version as package_version
from google.ai.generativelanguage_v1beta.types import (
    cached_content as gag_cached_content,
)
from google.ai.generativelanguage_v1beta.types import cache_service
from google.ai.generativelanguage_v1beta.types import cached_content

DEFAULT_CLIENT_INFO = gapic_v1.client_info.ClientInfo(
    gapic_version=package_version.__version__
)


class CacheServiceTransport(abc.ABC):
    """Abstract transport class for CacheService."""

    AUTH_SCOPES = ()

    DEFAULT_HOST: str = "generativelanguage.googleapis.com"

    def __init__(
        self,
        *,
        host: str = DEFAULT_HOST,
        credentials: Optional[ga_credentials.Credentials] = None,
        credentials_file: Optional[str] = None,
        scopes: Optional[Sequence[str]] = None,
        quota_project_id: Optional[str] = None,
        client_info: gapic_v1.client_info.ClientInfo = DEFAULT_CLIENT_INFO,
        always_use_jwt_access: Optional[bool] = False,
        api_audience: Optional[str] = None,
        **kwargs,
    ) -> None:
        """Instantiate the transport.

        Args:
            host (Optional[str]):
                 The hostname to connect to (default: 'generativelanguage.googleapis.com').
            credentials (Optional[google.auth.credentials.Credentials]): The
                authorization credentials to attach to requests. These
                credentials identify the application to the service; if none
                are specified, the client will attempt to ascertain the
                credentials from the environment.
            credentials_file (Optional[str]): A file with credentials that can
                be loaded with :func:`google.auth.load_credentials_from_file`.
                This argument is mutually exclusive with credentials.
            scopes (Optional[Sequence[str]]): A list of scopes.
            quota_project_id (Optional[str]): An optional project to use for billing
                and quota.
            client_info (google.api_core.gapic_v1.client_info.ClientInfo):
                The client info used to send a user-agent string along with
                API requests. If ``None``, then default info will be used.
                Generally, you only need to set this if you're developing
                your own client library.
            always_use_jwt_access (Optional[bool]): Whether self signed JWT should
                be used for service account credentials.
        """

        scopes_kwargs = {"scopes": scopes, "default_scopes": self.AUTH_SCOPES}

        # Save the scopes.
        self._scopes = scopes

        # If no credentials are provided, then determine the appropriate
        # defaults.
        if credentials and credentials_file:
            raise core_exceptions.DuplicateCredentialArgs(
                "'credentials_file' and 'credentials' are mutually exclusive"
            )

        if credentials_file is not None:
            credentials, _ = google.auth.load_credentials_from_file(
                credentials_file, **scopes_kwargs, quota_project_id=quota_project_id
            )
        elif credentials is None:
            credentials, _ = google.auth.default(
                **scopes_kwargs, quota_project_id=quota_project_id
            )
            # Don't apply audience if the credentials file passed from user.
            if hasattr(credentials, "with_gdch_audience"):
                credentials = credentials.with_gdch_audience(
                    api_audience if api_audience else host
                )

        # If the credentials are service account credentials, then always try to use self signed JWT.
        if (
            always_use_jwt_access
            and isinstance(credentials, service_account.Credentials)
            and hasattr(service_account.Credentials, "with_always_use_jwt_access")
        ):
            credentials = credentials.with_always_use_jwt_access(True)

        # Save the credentials.
        self._credentials = credentials

        # Save the hostname. Default to port 443 (HTTPS) if none is specified.
        if ":" not in host:
            host += ":443"
        self._host = host

    @property
    def host(self):
        return self._host

    def _prep_wrapped_messages(self, client_info):
        # Precompute the wrapped methods.
        self._wrapped_methods = {
            self.list_cached_contents: gapic_v1.method.wrap_method(
                self.list_cached_contents,
                default_timeout=None,
                client_info=client_info,
            ),
            self.create_cached_content: gapic_v1.method.wrap_method(
                self.create_cached_content,
                default_timeout=None,
                client_info=client_info,
            ),
            self.get_cached_content: gapic_v1.method.wrap_method(
                self.get_cached_content,
                default_timeout=None,
                client_info=client_info,
            ),
            self.update_cached_content: gapic_v1.method.wrap_method(
                self.update_cached_content,
                default_timeout=None,
                client_info=client_info,
            ),
            self.delete_cached_content: gapic_v1.method.wrap_method(
                self.delete_cached_content,
                default_timeout=None,
                client_info=client_info,
            ),
        }

    def close(self):
        """Closes resources associated with the transport.

        .. warning::
             Only call this method if the transport is NOT shared
             with other clients - this may cause errors in other clients!
        """
        raise NotImplementedError()

    @property
    def list_cached_contents(
        self,
    ) -> Callable[
        [cache_service.ListCachedContentsRequest],
        Union[
            cache_service.ListCachedContentsResponse,
            Awaitable[cache_service.ListCachedContentsResponse],
        ],
    ]:
        raise NotImplementedError()

    @property
    def create_cached_content(
        self,
    ) -> Callable[
        [cache_service.CreateCachedContentRequest],
        Union[
            gag_cached_content.CachedContent,
            Awaitable[gag_cached_content.CachedContent],
        ],
    ]:
        raise NotImplementedError()

    @property
    def get_cached_content(
        self,
    ) -> Callable[
        [cache_service.GetCachedContentRequest],
        Union[cached_content.CachedContent, Awaitable[cached_content.CachedContent]],
    ]:
        raise NotImplementedError()

    @property
    def update_cached_content(
        self,
    ) -> Callable[
        [cache_service.UpdateCachedContentRequest],
        Union[
            gag_cached_content.CachedContent,
            Awaitable[gag_cached_content.CachedContent],
        ],
    ]:
        raise NotImplementedError()

    @property
    def delete_cached_content(
        self,
    ) -> Callable[
        [cache_service.DeleteCachedContentRequest],
        Union[empty_pb2.Empty, Awaitable[empty_pb2.Empty]],
    ]:
        raise NotImplementedError()

    @property
    def kind(self) -> str:
        raise NotImplementedError()


__all__ = ("CacheServiceTransport",)

# === NexusCore/openenv\Lib\site-packages\interpreter\computer_use\unused_markdown.py ===
import sys
from enum import Enum, auto
from typing import Set


class Style(Enum):
    NORMAL = auto()
    BOLD = auto()
    ITALIC = auto()
    CODE = auto()
    HEADER = auto()
    CODE_BLOCK = auto()


class MarkdownStreamer:
    def __init__(self):
        # ANSI escape codes
        self.BOLD = "\033[1m"
        self.CODE = "\033[7m"  # Inverted
        self.CODE_BLOCK = "\033[48;5;236m"  # Very subtle dark gray background
        self.RESET = "\033[0m"

        # State tracking
        self.active_styles: Set[Style] = set()
        self.potential_marker = ""
        self.line_start = True
        self.header_level = 0
        self.in_list = False
        self.rule_marker_count = 0

        # Code block state
        self.code_fence_count = 0
        self.in_code_block = False
        self.list_marker_count = 0

    def write_char(self, char: str):
        """Write a single character with current styling."""
        if Style.CODE in self.active_styles:
            sys.stdout.write(f"{self.CODE}{char}{self.RESET}")
        elif Style.CODE_BLOCK in self.active_styles:
            sys.stdout.write(f"{self.CODE_BLOCK}{char}{self.RESET}")
        elif Style.BOLD in self.active_styles or Style.HEADER in self.active_styles:
            sys.stdout.write(f"{self.BOLD}{char}{self.RESET}")
        else:
            sys.stdout.write(char)
        sys.stdout.flush()

    def handle_marker(self, char: str) -> bool:
        """Handle markdown markers."""
        self.potential_marker += char

        # Code block
        if char == "`" and not Style.CODE in self.active_styles:
            self.code_fence_count += 1
            if self.code_fence_count == 3:
                self.code_fence_count = 0
                if not self.in_code_block:
                    self.in_code_block = True
                    self.active_styles.add(Style.CODE_BLOCK)
                    sys.stdout.write("\n")
                else:
                    self.in_code_block = False
                    self.active_styles.remove(Style.CODE_BLOCK)
                    sys.stdout.write("\n")
                return True
        else:
            self.code_fence_count = 0

        # Inline code
        if char == "`" and len(self.potential_marker) == 1:
            if Style.CODE in self.active_styles:
                self.active_styles.remove(Style.CODE)
            else:
                self.active_styles.add(Style.CODE)
            self.potential_marker = ""
            return True

        # Bold marker
        if self.potential_marker == "**":
            if Style.BOLD in self.active_styles:
                self.active_styles.remove(Style.BOLD)
            else:
                self.active_styles.add(Style.BOLD)
            self.potential_marker = ""
            return True

        # Italic marker
        elif self.potential_marker == "*" and char != "*":
            if Style.ITALIC in self.active_styles:
                self.active_styles.remove(Style.ITALIC)
            else:
                self.active_styles.add(Style.ITALIC)
            self.write_char(char)
            self.potential_marker = ""
            return True

        # Not a complete marker
        if len(self.potential_marker) > 2:
            self.write_char(self.potential_marker[0])
            self.potential_marker = self.potential_marker[1:]

        return False

    def handle_horizontal_rule(self, char: str) -> bool:
        """Handle horizontal rule markers."""
        if self.line_start and char == "-":
            self.rule_marker_count += 1
            if self.rule_marker_count == 3:
                sys.stdout.write("\n")
                sys.stdout.write("─" * 50)
                sys.stdout.write("\n")
                self.rule_marker_count = 0
                self.line_start = True
                return True
            return True
        else:
            if self.rule_marker_count > 0:
                for _ in range(self.rule_marker_count):
                    self.write_char("-")
                self.rule_marker_count = 0
        return False

    def handle_line_start(self, char: str) -> bool:
        """Handle special characters at start of lines."""
        if not self.line_start:
            return False

        if char == "#":
            self.header_level += 1
            return True
        elif self.header_level > 0:
            if char == " ":
                self.active_styles.add(Style.HEADER)
                return True
            self.header_level = 0

        elif char == "-" and not any(
            s in self.active_styles for s in [Style.BOLD, Style.ITALIC]
        ):
            self.list_marker_count = 1
            return True
        elif self.list_marker_count == 1 and char == " ":
            sys.stdout.write("  • ")  # Write bullet point
            sys.stdout.flush()
            self.list_marker_count = 0
            self.line_start = False
            return True

        self.line_start = False
        return False

    def feed(self, char: str):
        """Feed a single character into the streamer."""
        # Handle newlines
        if char == "\n":
            self.write_char(char)
            self.line_start = True
            if not self.in_code_block:
                self.active_styles.clear()
            self.potential_marker = ""
            self.list_marker_count = 0  # Reset list state
            return

        # Handle horizontal rules
        if not self.in_code_block and self.handle_horizontal_rule(char):
            return

        # Handle line start features
        if not self.in_code_block and self.handle_line_start(char):
            return

        # Handle markdown markers
        if char in ["*", "`"]:
            if not self.handle_marker(char):
                self.write_char(char)
        else:
            if self.potential_marker:
                self.write_char(self.potential_marker)
            self.potential_marker = ""
            self.write_char(char)

    def reset(self):
        """Reset streamer state."""
        self.active_styles.clear()
        self.potential_marker = ""
        self.line_start = True
        self.header_level = 0
        self.list_marker_count = 0
        self.in_code_block = False
        self.code_fence_count = 0
        self.rule_marker_count = 0
        sys.stdout.write(self.RESET)
        sys.stdout.flush()


import requests

# Download a large markdown file to test different styles
url = "https://raw.githubusercontent.com/matiassingers/awesome-readme/master/readme.md"
url = (
    "https://raw.githubusercontent.com/OpenInterpreter/open-interpreter/main/README.md"
)

response = requests.get(url)
markdown_text = response.text

markdown_text = (
    """```python
print("Hello, world!")
```\n"""
    + markdown_text
)


# Initialize it once
md = MarkdownStreamer()

# Then feed it characters one at a time. You can do this:
md.feed("H")
md.feed("e")
md.feed("l")
md.feed("l")
md.feed("o")

# Or feed from a string:
for char in markdown_text:
    md.feed(char)

# You can reset it if needed (clears all state)
md.reset()