
# === NexusCore/tools\exports\export_20250803_114325\combined_168.py ===

# === NexusCore/openenv\Lib\site-packages\huggingface_hub\_login.py ===
# Copyright 2020 The HuggingFace Team. All rights reserved.
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
"""Contains methods to log in to the Hub."""

import os
import subprocess
from getpass import getpass
from pathlib import Path
from typing import Optional

from . import constants
from .commands._cli_utils import ANSI
from .utils import (
    capture_output,
    get_token,
    is_google_colab,
    is_notebook,
    list_credential_helpers,
    logging,
    run_subprocess,
    set_git_credential,
    unset_git_credential,
)
from .utils._auth import (
    _get_token_by_name,
    _get_token_from_environment,
    _get_token_from_file,
    _get_token_from_google_colab,
    _save_stored_tokens,
    _save_token,
    get_stored_tokens,
)
from .utils._deprecation import _deprecate_arguments, _deprecate_positional_args


logger = logging.get_logger(__name__)

_HF_LOGO_ASCII = """
    _|    _|  _|    _|    _|_|_|    _|_|_|  _|_|_|  _|      _|    _|_|_|      _|_|_|_|    _|_|      _|_|_|  _|_|_|_|
    _|    _|  _|    _|  _|        _|          _|    _|_|    _|  _|            _|        _|    _|  _|        _|
    _|_|_|_|  _|    _|  _|  _|_|  _|  _|_|    _|    _|  _|  _|  _|  _|_|      _|_|_|    _|_|_|_|  _|        _|_|_|
    _|    _|  _|    _|  _|    _|  _|    _|    _|    _|    _|_|  _|    _|      _|        _|    _|  _|        _|
    _|    _|    _|_|      _|_|_|    _|_|_|  _|_|_|  _|      _|    _|_|_|      _|        _|    _|    _|_|_|  _|_|_|_|
"""


@_deprecate_arguments(
    version="1.0",
    deprecated_args="write_permission",
    custom_message="Fine-grained tokens added complexity to the permissions, making it irrelevant to check if a token has 'write' access.",
)
@_deprecate_positional_args(version="1.0")
def login(
    token: Optional[str] = None,
    *,
    add_to_git_credential: bool = False,
    new_session: bool = True,
    write_permission: bool = False,
) -> None:
    """Login the machine to access the Hub.

    The `token` is persisted in cache and set as a git credential. Once done, the machine
    is logged in and the access token will be available across all `huggingface_hub`
    components. If `token` is not provided, it will be prompted to the user either with
    a widget (in a notebook) or via the terminal.

    To log in from outside of a script, one can also use `huggingface-cli login` which is
    a cli command that wraps [`login`].

    <Tip>

    [`login`] is a drop-in replacement method for [`notebook_login`] as it wraps and
    extends its capabilities.

    </Tip>

    <Tip>

    When the token is not passed, [`login`] will automatically detect if the script runs
    in a notebook or not. However, this detection might not be accurate due to the
    variety of notebooks that exists nowadays. If that is the case, you can always force
    the UI by using [`notebook_login`] or [`interpreter_login`].

    </Tip>

    Args:
        token (`str`, *optional*):
            User access token to generate from https://huggingface.co/settings/token.
        add_to_git_credential (`bool`, defaults to `False`):
            If `True`, token will be set as git credential. If no git credential helper
            is configured, a warning will be displayed to the user. If `token` is `None`,
            the value of `add_to_git_credential` is ignored and will be prompted again
            to the end user.
        new_session (`bool`, defaults to `True`):
            If `True`, will request a token even if one is already saved on the machine.
        write_permission (`bool`):
            Ignored and deprecated argument.
    Raises:
        [`ValueError`](https://docs.python.org/3/library/exceptions.html#ValueError)
            If an organization token is passed. Only personal account tokens are valid
            to log in.
        [`ValueError`](https://docs.python.org/3/library/exceptions.html#ValueError)
            If token is invalid.
        [`ImportError`](https://docs.python.org/3/library/exceptions.html#ImportError)
            If running in a notebook but `ipywidgets` is not installed.
    """
    if token is not None:
        if not add_to_git_credential:
            logger.info(
                "The token has not been saved to the git credentials helper. Pass "
                "`add_to_git_credential=True` in this function directly or "
                "`--add-to-git-credential` if using via `huggingface-cli` if "
                "you want to set the git credential as well."
            )
        _login(token, add_to_git_credential=add_to_git_credential)
    elif is_notebook():
        notebook_login(new_session=new_session)
    else:
        interpreter_login(new_session=new_session)


def logout(token_name: Optional[str] = None) -> None:
    """Logout the machine from the Hub.

    Token is deleted from the machine and removed from git credential.

    Args:
        token_name (`str`, *optional*):
            Name of the access token to logout from. If `None`, will logout from all saved access tokens.
    Raises:
        [`ValueError`](https://docs.python.org/3/library/exceptions.html#ValueError):
            If the access token name is not found.
    """
    if get_token() is None and not get_stored_tokens():  # No active token and no saved access tokens
        logger.warning("Not logged in!")
        return
    if not token_name:
        # Delete all saved access tokens and token
        for file_path in (constants.HF_TOKEN_PATH, constants.HF_STORED_TOKENS_PATH):
            try:
                Path(file_path).unlink()
            except FileNotFoundError:
                pass
        logger.info("Successfully logged out from all access tokens.")
    else:
        _logout_from_token(token_name)
        logger.info(f"Successfully logged out from access token: {token_name}.")

    unset_git_credential()

    # Check if still logged in
    if _get_token_from_google_colab() is not None:
        raise EnvironmentError(
            "You are automatically logged in using a Google Colab secret.\n"
            "To log out, you must unset the `HF_TOKEN` secret in your Colab settings."
        )
    if _get_token_from_environment() is not None:
        raise EnvironmentError(
            "Token has been deleted from your machine but you are still logged in.\n"
            "To log out, you must clear out both `HF_TOKEN` and `HUGGING_FACE_HUB_TOKEN` environment variables."
        )


def auth_switch(token_name: str, add_to_git_credential: bool = False) -> None:
    """Switch to a different access token.

    Args:
        token_name (`str`):
            Name of the access token to switch to.
        add_to_git_credential (`bool`, defaults to `False`):
            If `True`, token will be set as git credential. If no git credential helper
            is configured, a warning will be displayed to the user. If `token` is `None`,
            the value of `add_to_git_credential` is ignored and will be prompted again
            to the end user.

    Raises:
        [`ValueError`](https://docs.python.org/3/library/exceptions.html#ValueError):
            If the access token name is not found.
    """
    token = _get_token_by_name(token_name)
    if not token:
        raise ValueError(f"Access token {token_name} not found in {constants.HF_STORED_TOKENS_PATH}")
    # Write token to HF_TOKEN_PATH
    _set_active_token(token_name, add_to_git_credential)
    logger.info(f"The current active token is: {token_name}")
    token_from_environment = _get_token_from_environment()
    if token_from_environment is not None and token_from_environment != token:
        logger.warning(
            "The environment variable `HF_TOKEN` is set and will override the access token you've just switched to."
        )


def auth_list() -> None:
    """List all stored access tokens."""
    tokens = get_stored_tokens()

    if not tokens:
        logger.info("No access tokens found.")
        return
    # Find current token
    current_token = get_token()
    current_token_name = None
    for token_name in tokens:
        if tokens.get(token_name) == current_token:
            current_token_name = token_name
    # Print header
    max_offset = max(len("token"), max(len(token) for token in tokens)) + 2
    print(f"  {{:<{max_offset}}}| {{:<15}}".format("name", "token"))
    print("-" * (max_offset + 2) + "|" + "-" * 15)

    # Print saved access tokens
    for token_name in tokens:
        token = tokens.get(token_name, "<not set>")
        masked_token = f"{token[:3]}****{token[-4:]}" if token != "<not set>" else token
        is_current = "*" if token == current_token else " "

        print(f"{is_current} {{:<{max_offset}}}| {{:<15}}".format(token_name, masked_token))

    if _get_token_from_environment():
        logger.warning(
            "\nNote: Environment variable `HF_TOKEN` is set and is the current active token independently from the stored tokens listed above."
        )
    elif current_token_name is None:
        logger.warning(
            "\nNote: No active token is set and no environment variable `HF_TOKEN` is found. Use `huggingface-cli login` to log in."
        )


###
# Interpreter-based login (text)
###


@_deprecate_arguments(
    version="1.0",
    deprecated_args="write_permission",
    custom_message="Fine-grained tokens added complexity to the permissions, making it irrelevant to check if a token has 'write' access.",
)
@_deprecate_positional_args(version="1.0")
def interpreter_login(*, new_session: bool = True, write_permission: bool = False) -> None:
    """
    Displays a prompt to log in to the HF website and store the token.

    This is equivalent to [`login`] without passing a token when not run in a notebook.
    [`interpreter_login`] is useful if you want to force the use of the terminal prompt
    instead of a notebook widget.

    For more details, see [`login`].

    Args:
        new_session (`bool`, defaults to `True`):
            If `True`, will request a token even if one is already saved on the machine.
        write_permission (`bool`):
            Ignored and deprecated argument.
    """
    if not new_session and get_token() is not None:
        logger.info("User is already logged in.")
        return

    from .commands.delete_cache import _ask_for_confirmation_no_tui

    print(_HF_LOGO_ASCII)
    if get_token() is not None:
        logger.info(
            "    A token is already saved on your machine. Run `huggingface-cli"
            " whoami` to get more information or `huggingface-cli logout` if you want"
            " to log out."
        )
        logger.info("    Setting a new token will erase the existing one.")

    logger.info(
        "    To log in, `huggingface_hub` requires a token generated from https://huggingface.co/settings/tokens ."
    )
    if os.name == "nt":
        logger.info("Token can be pasted using 'Right-Click'.")
    token = getpass("Enter your token (input will not be visible): ")
    add_to_git_credential = _ask_for_confirmation_no_tui("Add token as git credential?")

    _login(token=token, add_to_git_credential=add_to_git_credential)


###
# Notebook-based login (widget)
###

NOTEBOOK_LOGIN_PASSWORD_HTML = """<center> <img
src=https://huggingface.co/front/assets/huggingface_logo-noborder.svg
alt='Hugging Face'> <br> Immediately click login after typing your password or
it might be stored in plain text in this notebook file. </center>"""


NOTEBOOK_LOGIN_TOKEN_HTML_START = """<center> <img
src=https://huggingface.co/front/assets/huggingface_logo-noborder.svg
alt='Hugging Face'> <br> Copy a token from <a
href="https://huggingface.co/settings/tokens" target="_blank">your Hugging Face
tokens page</a> and paste it below. <br> Immediately click login after copying
your token or it might be stored in plain text in this notebook file. </center>"""


NOTEBOOK_LOGIN_TOKEN_HTML_END = """
<b>Pro Tip:</b> If you don't already have one, you can create a dedicated
'notebooks' token with 'write' access, that you can then easily reuse for all
notebooks. </center>"""


@_deprecate_arguments(
    version="1.0",
    deprecated_args="write_permission",
    custom_message="Fine-grained tokens added complexity to the permissions, making it irrelevant to check if a token has 'write' access.",
)
@_deprecate_positional_args(version="1.0")
def notebook_login(*, new_session: bool = True, write_permission: bool = False) -> None:
    """
    Displays a widget to log in to the HF website and store the token.

    This is equivalent to [`login`] without passing a token when run in a notebook.
    [`notebook_login`] is useful if you want to force the use of the notebook widget
    instead of a prompt in the terminal.

    For more details, see [`login`].

    Args:
        new_session (`bool`, defaults to `True`):
            If `True`, will request a token even if one is already saved on the machine.
        write_permission (`bool`):
            Ignored and deprecated argument.
    """
    try:
        import ipywidgets.widgets as widgets  # type: ignore
        from IPython.display import display  # type: ignore
    except ImportError:
        raise ImportError(
            "The `notebook_login` function can only be used in a notebook (Jupyter or"
            " Colab) and you need the `ipywidgets` module: `pip install ipywidgets`."
        )
    if not new_session and get_token() is not None:
        logger.info("User is already logged in.")
        return

    box_layout = widgets.Layout(display="flex", flex_flow="column", align_items="center", width="50%")

    token_widget = widgets.Password(description="Token:")
    git_checkbox_widget = widgets.Checkbox(value=True, description="Add token as git credential?")
    token_finish_button = widgets.Button(description="Login")

    login_token_widget = widgets.VBox(
        [
            widgets.HTML(NOTEBOOK_LOGIN_TOKEN_HTML_START),
            token_widget,
            git_checkbox_widget,
            token_finish_button,
            widgets.HTML(NOTEBOOK_LOGIN_TOKEN_HTML_END),
        ],
        layout=box_layout,
    )
    display(login_token_widget)

    # On click events
    def login_token_event(t):
        """Event handler for the login button."""
        token = token_widget.value
        add_to_git_credential = git_checkbox_widget.value
        # Erase token and clear value to make sure it's not saved in the notebook.
        token_widget.value = ""
        # Hide inputs
        login_token_widget.children = [widgets.Label("Connecting...")]
        try:
            with capture_output() as captured:
                _login(token, add_to_git_credential=add_to_git_credential)
            message = captured.getvalue()
        except Exception as error:
            message = str(error)
        # Print result (success message or error)
        login_token_widget.children = [widgets.Label(line) for line in message.split("\n") if line.strip()]

    token_finish_button.on_click(login_token_event)


###
# Login private helpers
###


def _login(
    token: str,
    add_to_git_credential: bool,
) -> None:
    from .hf_api import whoami  # avoid circular import

    if token.startswith("api_org"):
        raise ValueError("You must use your personal account token, not an organization token.")

    token_info = whoami(token)
    permission = token_info["auth"]["accessToken"]["role"]
    logger.info(f"Token is valid (permission: {permission}).")

    token_name = token_info["auth"]["accessToken"]["displayName"]
    # Store token locally
    _save_token(token=token, token_name=token_name)
    # Set active token
    _set_active_token(token_name=token_name, add_to_git_credential=add_to_git_credential)
    logger.info("Login successful.")
    if _get_token_from_environment():
        logger.warning(
            "Note: Environment variable`HF_TOKEN` is set and is the current active token independently from the token you've just configured."
        )
    else:
        logger.info(f"The current active token is: `{token_name}`")


def _logout_from_token(token_name: str) -> None:
    """Logout from a specific access token.

    Args:
        token_name (`str`):
            The name of the access token to logout from.
    Raises:
        [`ValueError`](https://docs.python.org/3/library/exceptions.html#ValueError):
            If the access token name is not found.
    """
    stored_tokens = get_stored_tokens()
    # If there is no access tokens saved or the access token name is not found, do nothing
    if not stored_tokens or token_name not in stored_tokens:
        return

    token = stored_tokens.pop(token_name)
    _save_stored_tokens(stored_tokens)

    if token == _get_token_from_file():
        logger.warning(f"Active token '{token_name}' has been deleted.")
        Path(constants.HF_TOKEN_PATH).unlink(missing_ok=True)


def _set_active_token(
    token_name: str,
    add_to_git_credential: bool,
) -> None:
    """Set the active access token.

    Args:
        token_name (`str`):
            The name of the token to set as active.
    """
    token = _get_token_by_name(token_name)
    if not token:
        raise ValueError(f"Token {token_name} not found in {constants.HF_STORED_TOKENS_PATH}")
    if add_to_git_credential:
        if _is_git_credential_helper_configured():
            set_git_credential(token)
            logger.info(
                "Your token has been saved in your configured git credential helpers"
                + f" ({','.join(list_credential_helpers())})."
            )
        else:
            logger.warning("Token has not been saved to git credential helper.")
    # Write token to HF_TOKEN_PATH
    path = Path(constants.HF_TOKEN_PATH)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(token)
    logger.info(f"Your token has been saved to {constants.HF_TOKEN_PATH}")


def _is_git_credential_helper_configured() -> bool:
    """Check if a git credential helper is configured.

    Warns user if not the case (except for Google Colab where "store" is set by default
    by `huggingface_hub`).
    """
    helpers = list_credential_helpers()
    if len(helpers) > 0:
        return True  # Do not warn: at least 1 helper is set

    # Only in Google Colab to avoid the warning message
    # See https://github.com/huggingface/huggingface_hub/issues/1043#issuecomment-1247010710
    if is_google_colab():
        _set_store_as_git_credential_helper_globally()
        return True  # Do not warn: "store" is used by default in Google Colab

    # Otherwise, warn user
    print(
        ANSI.red(
            "Cannot authenticate through git-credential as no helper is defined on your"
            " machine.\nYou might have to re-authenticate when pushing to the Hugging"
            " Face Hub.\nRun the following command in your terminal in case you want to"
            " set the 'store' credential helper as default.\n\ngit config --global"
            " credential.helper store\n\nRead"
            " https://git-scm.com/book/en/v2/Git-Tools-Credential-Storage for more"
            " details."
        )
    )
    return False


def _set_store_as_git_credential_helper_globally() -> None:
    """Set globally the credential.helper to `store`.

    To be used only in Google Colab as we assume the user doesn't care about the git
    credential config. It is the only particular case where we don't want to display the
    warning message in [`notebook_login()`].

    Related:
    - https://github.com/huggingface/huggingface_hub/issues/1043
    - https://github.com/huggingface/huggingface_hub/issues/1051
    - https://git-scm.com/docs/git-credential-store
    """
    try:
        run_subprocess("git config --global credential.helper store")
    except subprocess.CalledProcessError as exc:
        raise EnvironmentError(exc.stderr)

# === NexusCore/openenv\Lib\site-packages\joblib\test\test_hashing.py ===
"""
Test the hashing module.
"""

# Author: Gael Varoquaux <gael dot varoquaux at normalesup dot org>
# Copyright (c) 2009 Gael Varoquaux
# License: BSD Style, 3 clauses.

import collections
import gc
import hashlib
import io
import itertools
import pickle
import random
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from decimal import Decimal

from joblib.func_inspect import filter_args
from joblib.hashing import hash
from joblib.memory import Memory
from joblib.test.common import np, with_numpy
from joblib.testing import fixture, parametrize, raises, skipif


def unicode(s):
    return s


###############################################################################
# Helper functions for the tests
def time_func(func, *args):
    """Time function func on *args."""
    times = list()
    for _ in range(3):
        t1 = time.time()
        func(*args)
        times.append(time.time() - t1)
    return min(times)


def relative_time(func1, func2, *args):
    """Return the relative time between func1 and func2 applied on
    *args.
    """
    time_func1 = time_func(func1, *args)
    time_func2 = time_func(func2, *args)
    relative_diff = 0.5 * (abs(time_func1 - time_func2) / (time_func1 + time_func2))
    return relative_diff


class Klass(object):
    def f(self, x):
        return x


class KlassWithCachedMethod(object):
    def __init__(self, cachedir):
        mem = Memory(location=cachedir)
        self.f = mem.cache(self.f)

    def f(self, x):
        return x


###############################################################################
# Tests

input_list = [
    1,
    2,
    1.0,
    2.0,
    1 + 1j,
    2.0 + 1j,
    "a",
    "b",
    (1,),
    (
        1,
        1,
    ),
    [
        1,
    ],
    [
        1,
        1,
    ],
    {1: 1},
    {1: 2},
    {2: 1},
    None,
    gc.collect,
    [
        1,
    ].append,
    # Next 2 sets have unorderable elements in python 3.
    set(("a", 1)),
    set(("a", 1, ("a", 1))),
    # Next 2 dicts have unorderable type of keys in python 3.
    {"a": 1, 1: 2},
    {"a": 1, 1: 2, "d": {"a": 1}},
]


@parametrize("obj1", input_list)
@parametrize("obj2", input_list)
def test_trivial_hash(obj1, obj2):
    """Smoke test hash on various types."""
    # Check that 2 objects have the same hash only if they are the same.
    are_hashes_equal = hash(obj1) == hash(obj2)
    are_objs_identical = obj1 is obj2
    assert are_hashes_equal == are_objs_identical


def test_hash_methods():
    # Check that hashing instance methods works
    a = io.StringIO(unicode("a"))
    assert hash(a.flush) == hash(a.flush)
    a1 = collections.deque(range(10))
    a2 = collections.deque(range(9))
    assert hash(a1.extend) != hash(a2.extend)


@fixture(scope="function")
@with_numpy
def three_np_arrays():
    rnd = np.random.RandomState(0)
    arr1 = rnd.random_sample((10, 10))
    arr2 = arr1.copy()
    arr3 = arr2.copy()
    arr3[0] += 1
    return arr1, arr2, arr3


def test_hash_numpy_arrays(three_np_arrays):
    arr1, arr2, arr3 = three_np_arrays

    for obj1, obj2 in itertools.product(three_np_arrays, repeat=2):
        are_hashes_equal = hash(obj1) == hash(obj2)
        are_arrays_equal = np.all(obj1 == obj2)
        assert are_hashes_equal == are_arrays_equal

    assert hash(arr1) != hash(arr1.T)


def test_hash_numpy_dict_of_arrays(three_np_arrays):
    arr1, arr2, arr3 = three_np_arrays

    d1 = {1: arr1, 2: arr2}
    d2 = {1: arr2, 2: arr1}
    d3 = {1: arr2, 2: arr3}

    assert hash(d1) == hash(d2)
    assert hash(d1) != hash(d3)


@with_numpy
@parametrize("dtype", ["datetime64[s]", "timedelta64[D]"])
def test_numpy_datetime_array(dtype):
    # memoryview is not supported for some dtypes e.g. datetime64
    # see https://github.com/joblib/joblib/issues/188 for more details
    a_hash = hash(np.arange(10))
    array = np.arange(0, 10, dtype=dtype)
    assert hash(array) != a_hash


@with_numpy
def test_hash_numpy_noncontiguous():
    a = np.asarray(np.arange(6000).reshape((1000, 2, 3)), order="F")[:, :1, :]
    b = np.ascontiguousarray(a)
    assert hash(a) != hash(b)

    c = np.asfortranarray(a)
    assert hash(a) != hash(c)


@with_numpy
@parametrize("coerce_mmap", [True, False])
def test_hash_memmap(tmpdir, coerce_mmap):
    """Check that memmap and arrays hash identically if coerce_mmap is True."""
    filename = tmpdir.join("memmap_temp").strpath
    try:
        m = np.memmap(filename, shape=(10, 10), mode="w+")
        a = np.asarray(m)
        are_hashes_equal = hash(a, coerce_mmap=coerce_mmap) == hash(
            m, coerce_mmap=coerce_mmap
        )
        assert are_hashes_equal == coerce_mmap
    finally:
        if "m" in locals():
            del m
            # Force a garbage-collection cycle, to be certain that the
            # object is delete, and we don't run in a problem under
            # Windows with a file handle still open.
            gc.collect()


@with_numpy
@skipif(
    sys.platform == "win32",
    reason="This test is not stable under windows for some reason",
)
def test_hash_numpy_performance():
    """Check the performance of hashing numpy arrays:

    In [22]: a = np.random.random(1000000)

    In [23]: %timeit hashlib.md5(a).hexdigest()
    100 loops, best of 3: 20.7 ms per loop

    In [24]: %timeit hashlib.md5(pickle.dumps(a, protocol=2)).hexdigest()
    1 loops, best of 3: 73.1 ms per loop

    In [25]: %timeit hashlib.md5(cPickle.dumps(a, protocol=2)).hexdigest()
    10 loops, best of 3: 53.9 ms per loop

    In [26]: %timeit hash(a)
    100 loops, best of 3: 20.8 ms per loop
    """
    rnd = np.random.RandomState(0)
    a = rnd.random_sample(1000000)

    def md5_hash(x):
        return hashlib.md5(memoryview(x)).hexdigest()

    relative_diff = relative_time(md5_hash, hash, a)
    assert relative_diff < 0.3

    # Check that hashing an tuple of 3 arrays takes approximately
    # 3 times as much as hashing one array
    time_hashlib = 3 * time_func(md5_hash, a)
    time_hash = time_func(hash, (a, a, a))
    relative_diff = 0.5 * (abs(time_hash - time_hashlib) / (time_hash + time_hashlib))
    assert relative_diff < 0.3


def test_bound_methods_hash():
    """Make sure that calling the same method on two different instances
    of the same class does resolve to the same hashes.
    """
    a = Klass()
    b = Klass()
    assert hash(filter_args(a.f, [], (1,))) == hash(filter_args(b.f, [], (1,)))


def test_bound_cached_methods_hash(tmpdir):
    """Make sure that calling the same _cached_ method on two different
    instances of the same class does resolve to the same hashes.
    """
    a = KlassWithCachedMethod(tmpdir.strpath)
    b = KlassWithCachedMethod(tmpdir.strpath)
    assert hash(filter_args(a.f.func, [], (1,))) == hash(
        filter_args(b.f.func, [], (1,))
    )


@with_numpy
def test_hash_object_dtype():
    """Make sure that ndarrays with dtype `object' hash correctly."""

    a = np.array([np.arange(i) for i in range(6)], dtype=object)
    b = np.array([np.arange(i) for i in range(6)], dtype=object)

    assert hash(a) == hash(b)


@with_numpy
def test_numpy_scalar():
    # Numpy scalars are built from compiled functions, and lead to
    # strange pickling paths explored, that can give hash collisions
    a = np.float64(2.0)
    b = np.float64(3.0)
    assert hash(a) != hash(b)


def test_dict_hash(tmpdir):
    # Check that dictionaries hash consistently, even though the ordering
    # of the keys is not guaranteed
    k = KlassWithCachedMethod(tmpdir.strpath)

    d = {
        "#s12069__c_maps.nii.gz": [33],
        "#s12158__c_maps.nii.gz": [33],
        "#s12258__c_maps.nii.gz": [33],
        "#s12277__c_maps.nii.gz": [33],
        "#s12300__c_maps.nii.gz": [33],
        "#s12401__c_maps.nii.gz": [33],
        "#s12430__c_maps.nii.gz": [33],
        "#s13817__c_maps.nii.gz": [33],
        "#s13903__c_maps.nii.gz": [33],
        "#s13916__c_maps.nii.gz": [33],
        "#s13981__c_maps.nii.gz": [33],
        "#s13982__c_maps.nii.gz": [33],
        "#s13983__c_maps.nii.gz": [33],
    }

    a = k.f(d)
    b = k.f(a)

    assert hash(a) == hash(b)


def test_set_hash(tmpdir):
    # Check that sets hash consistently, even though their ordering
    # is not guaranteed
    k = KlassWithCachedMethod(tmpdir.strpath)

    s = set(
        [
            "#s12069__c_maps.nii.gz",
            "#s12158__c_maps.nii.gz",
            "#s12258__c_maps.nii.gz",
            "#s12277__c_maps.nii.gz",
            "#s12300__c_maps.nii.gz",
            "#s12401__c_maps.nii.gz",
            "#s12430__c_maps.nii.gz",
            "#s13817__c_maps.nii.gz",
            "#s13903__c_maps.nii.gz",
            "#s13916__c_maps.nii.gz",
            "#s13981__c_maps.nii.gz",
            "#s13982__c_maps.nii.gz",
            "#s13983__c_maps.nii.gz",
        ]
    )

    a = k.f(s)
    b = k.f(a)

    assert hash(a) == hash(b)


def test_set_decimal_hash():
    # Check that sets containing decimals hash consistently, even though
    # ordering is not guaranteed
    assert hash(set([Decimal(0), Decimal("NaN")])) == hash(
        set([Decimal("NaN"), Decimal(0)])
    )


def test_string():
    # Test that we obtain the same hash for object owning several strings,
    # whatever the past of these strings (which are immutable in Python)
    string = "foo"
    a = {string: "bar"}
    b = {string: "bar"}
    c = pickle.loads(pickle.dumps(b))
    assert hash([a, b]) == hash([a, c])


@with_numpy
def test_numpy_dtype_pickling():
    # numpy dtype hashing is tricky to get right: see #231, #239, #251 #1080,
    # #1082, and explanatory comments inside
    # ``joblib.hashing.NumpyHasher.save``.

    # In this test, we make sure that the pickling of numpy dtypes is robust to
    # object identity and object copy.

    dt1 = np.dtype("f4")
    dt2 = np.dtype("f4")

    # simple dtypes objects are interned
    assert dt1 is dt2
    assert hash(dt1) == hash(dt2)

    dt1_roundtripped = pickle.loads(pickle.dumps(dt1))
    assert dt1 is not dt1_roundtripped
    assert hash(dt1) == hash(dt1_roundtripped)

    assert hash([dt1, dt1]) == hash([dt1_roundtripped, dt1_roundtripped])
    assert hash([dt1, dt1]) == hash([dt1, dt1_roundtripped])

    complex_dt1 = np.dtype([("name", np.str_, 16), ("grades", np.float64, (2,))])
    complex_dt2 = np.dtype([("name", np.str_, 16), ("grades", np.float64, (2,))])

    # complex dtypes objects are not interned
    assert hash(complex_dt1) == hash(complex_dt2)

    complex_dt1_roundtripped = pickle.loads(pickle.dumps(complex_dt1))
    assert complex_dt1_roundtripped is not complex_dt1
    assert hash(complex_dt1) == hash(complex_dt1_roundtripped)

    assert hash([complex_dt1, complex_dt1]) == hash(
        [complex_dt1_roundtripped, complex_dt1_roundtripped]
    )
    assert hash([complex_dt1, complex_dt1]) == hash(
        [complex_dt1_roundtripped, complex_dt1]
    )


@parametrize(
    "to_hash,expected",
    [
        ("This is a string to hash", "71b3f47df22cb19431d85d92d0b230b2"),
        ("C'est l\xe9t\xe9", "2d8d189e9b2b0b2e384d93c868c0e576"),
        ((123456, 54321, -98765), "e205227dd82250871fa25aa0ec690aa3"),
        (
            [random.Random(42).random() for _ in range(5)],
            "a11ffad81f9682a7d901e6edc3d16c84",
        ),
        ({"abcde": 123, "sadfas": [-9999, 2, 3]}, "aeda150553d4bb5c69f0e69d51b0e2ef"),
    ],
)
def test_hashes_stay_the_same(to_hash, expected):
    # We want to make sure that hashes don't change with joblib
    # version. For end users, that would mean that they have to
    # regenerate their cache from scratch, which potentially means
    # lengthy recomputations.
    # Expected results have been generated with joblib 0.9.2
    assert hash(to_hash) == expected


@with_numpy
def test_hashes_are_different_between_c_and_fortran_contiguous_arrays():
    # We want to be sure that the c-contiguous and f-contiguous versions of the
    # same array produce 2 different hashes.
    rng = np.random.RandomState(0)
    arr_c = rng.random_sample((10, 10))
    arr_f = np.asfortranarray(arr_c)
    assert hash(arr_c) != hash(arr_f)


@with_numpy
def test_0d_array():
    hash(np.array(0))


@with_numpy
def test_0d_and_1d_array_hashing_is_different():
    assert hash(np.array(0)) != hash(np.array([0]))


@with_numpy
def test_hashes_stay_the_same_with_numpy_objects():
    # Note: joblib used to test numpy objects hashing by comparing the produced
    # hash of an object with some hard-coded target value to guarantee that
    # hashing remains the same across joblib versions. However, since numpy
    # 1.20 and joblib 1.0, joblib relies on potentially unstable implementation
    # details of numpy to hash np.dtype objects, which makes the stability of
    # hash values across different environments hard to guarantee and to test.
    # As a result, hashing stability across joblib versions becomes best-effort
    # only, and we only test the consistency within a single environment by
    # making sure:
    # - the hash of two copies of the same objects is the same
    # - hashing some object in two different python processes produces the same
    #   value. This should be viewed as a proxy for testing hash consistency
    #   through time between Python sessions (provided no change in the
    #   environment was done between sessions).

    def create_objects_to_hash():
        rng = np.random.RandomState(42)
        # Being explicit about dtypes in order to avoid
        # architecture-related differences. Also using 'f4' rather than
        # 'f8' for float arrays because 'f8' arrays generated by
        # rng.random.randn don't seem to be bit-identical on 32bit and
        # 64bit machines.
        to_hash_list = [
            rng.randint(-1000, high=1000, size=50).astype("<i8"),
            tuple(rng.randn(3).astype("<f4") for _ in range(5)),
            [rng.randn(3).astype("<f4") for _ in range(5)],
            {
                -3333: rng.randn(3, 5).astype("<f4"),
                0: [
                    rng.randint(10, size=20).astype("<i8"),
                    rng.randn(10).astype("<f4"),
                ],
            },
            # Non regression cases for
            # https://github.com/joblib/joblib/issues/308
            np.arange(100, dtype="<i8").reshape((10, 10)),
            # Fortran contiguous array
            np.asfortranarray(np.arange(100, dtype="<i8").reshape((10, 10))),
            # Non contiguous array
            np.arange(100, dtype="<i8").reshape((10, 10))[:, :2],
        ]
        return to_hash_list

    # Create two lists containing copies of the same objects.  joblib.hash
    # should return the same hash for to_hash_list_one[i] and
    # to_hash_list_two[i]
    to_hash_list_one = create_objects_to_hash()
    to_hash_list_two = create_objects_to_hash()

    e1 = ProcessPoolExecutor(max_workers=1)
    e2 = ProcessPoolExecutor(max_workers=1)

    try:
        for obj_1, obj_2 in zip(to_hash_list_one, to_hash_list_two):
            # testing consistency of hashes across python processes
            hash_1 = e1.submit(hash, obj_1).result()
            hash_2 = e2.submit(hash, obj_1).result()
            assert hash_1 == hash_2

            # testing consistency when hashing two copies of the same objects.
            hash_3 = e1.submit(hash, obj_2).result()
            assert hash_1 == hash_3

    finally:
        e1.shutdown()
        e2.shutdown()


def test_hashing_pickling_error():
    def non_picklable():
        return 42

    with raises(pickle.PicklingError) as excinfo:
        hash(non_picklable)
    excinfo.match("PicklingError while hashing")


def test_wrong_hash_name():
    msg = "Valid options for 'hash_name' are"
    with raises(ValueError, match=msg):
        data = {"foo": "bar"}
        hash(data, hash_name="invalid")

# === NexusCore/openenv\Lib\site-packages\trio\_core\_windows_cffi.py ===
from __future__ import annotations

import enum
import re
from typing import TYPE_CHECKING, NewType, NoReturn, Protocol, cast

if TYPE_CHECKING:
    from typing_extensions import TypeAlias

import cffi

################################################################
# Functions and types
################################################################

LIB = """
// https://msdn.microsoft.com/en-us/library/windows/desktop/aa383751(v=vs.85).aspx
typedef int BOOL;
typedef unsigned char BYTE;
typedef BYTE BOOLEAN;
typedef void* PVOID;
typedef PVOID HANDLE;
typedef unsigned long DWORD;
typedef unsigned long ULONG;
typedef unsigned int NTSTATUS;
typedef unsigned long u_long;
typedef ULONG *PULONG;
typedef const void *LPCVOID;
typedef void *LPVOID;
typedef const wchar_t *LPCWSTR;

typedef uintptr_t ULONG_PTR;
typedef uintptr_t UINT_PTR;

typedef UINT_PTR SOCKET;

typedef struct _OVERLAPPED {
    ULONG_PTR Internal;
    ULONG_PTR InternalHigh;
    union {
        struct {
            DWORD Offset;
            DWORD OffsetHigh;
        } DUMMYSTRUCTNAME;
        PVOID Pointer;
    } DUMMYUNIONNAME;

    HANDLE  hEvent;
} OVERLAPPED, *LPOVERLAPPED;

typedef OVERLAPPED WSAOVERLAPPED;
typedef LPOVERLAPPED LPWSAOVERLAPPED;
typedef PVOID LPSECURITY_ATTRIBUTES;
typedef PVOID LPCSTR;

typedef struct _OVERLAPPED_ENTRY {
    ULONG_PTR lpCompletionKey;
    LPOVERLAPPED lpOverlapped;
    ULONG_PTR Internal;
    DWORD dwNumberOfBytesTransferred;
} OVERLAPPED_ENTRY, *LPOVERLAPPED_ENTRY;

// kernel32.dll
HANDLE WINAPI CreateIoCompletionPort(
  _In_     HANDLE    FileHandle,
  _In_opt_ HANDLE    ExistingCompletionPort,
  _In_     ULONG_PTR CompletionKey,
  _In_     DWORD     NumberOfConcurrentThreads
);

BOOL SetFileCompletionNotificationModes(
  HANDLE FileHandle,
  UCHAR  Flags
);

HANDLE CreateFileW(
  LPCWSTR               lpFileName,
  DWORD                 dwDesiredAccess,
  DWORD                 dwShareMode,
  LPSECURITY_ATTRIBUTES lpSecurityAttributes,
  DWORD                 dwCreationDisposition,
  DWORD                 dwFlagsAndAttributes,
  HANDLE                hTemplateFile
);

BOOL WINAPI CloseHandle(
  _In_ HANDLE hObject
);

BOOL WINAPI PostQueuedCompletionStatus(
  _In_     HANDLE       CompletionPort,
  _In_     DWORD        dwNumberOfBytesTransferred,
  _In_     ULONG_PTR    dwCompletionKey,
  _In_opt_ LPOVERLAPPED lpOverlapped
);

BOOL WINAPI GetQueuedCompletionStatusEx(
  _In_  HANDLE             CompletionPort,
  _Out_ LPOVERLAPPED_ENTRY lpCompletionPortEntries,
  _In_  ULONG              ulCount,
  _Out_ PULONG             ulNumEntriesRemoved,
  _In_  DWORD              dwMilliseconds,
  _In_  BOOL               fAlertable
);

BOOL WINAPI CancelIoEx(
  _In_     HANDLE       hFile,
  _In_opt_ LPOVERLAPPED lpOverlapped
);

BOOL WriteFile(
  HANDLE       hFile,
  LPCVOID      lpBuffer,
  DWORD        nNumberOfBytesToWrite,
  LPDWORD      lpNumberOfBytesWritten,
  LPOVERLAPPED lpOverlapped
);

BOOL ReadFile(
  HANDLE       hFile,
  LPVOID       lpBuffer,
  DWORD        nNumberOfBytesToRead,
  LPDWORD      lpNumberOfBytesRead,
  LPOVERLAPPED lpOverlapped
);

BOOL WINAPI SetConsoleCtrlHandler(
  _In_opt_ void*            HandlerRoutine,
  _In_     BOOL             Add
);

HANDLE CreateEventA(
  LPSECURITY_ATTRIBUTES lpEventAttributes,
  BOOL                  bManualReset,
  BOOL                  bInitialState,
  LPCSTR                lpName
);

BOOL SetEvent(
  HANDLE hEvent
);

BOOL ResetEvent(
  HANDLE hEvent
);

DWORD WaitForSingleObject(
  HANDLE hHandle,
  DWORD  dwMilliseconds
);

DWORD WaitForMultipleObjects(
  DWORD        nCount,
  HANDLE       *lpHandles,
  BOOL         bWaitAll,
  DWORD        dwMilliseconds
);

ULONG RtlNtStatusToDosError(
  NTSTATUS Status
);

int WSAIoctl(
  SOCKET                             s,
  DWORD                              dwIoControlCode,
  LPVOID                             lpvInBuffer,
  DWORD                              cbInBuffer,
  LPVOID                             lpvOutBuffer,
  DWORD                              cbOutBuffer,
  LPDWORD                            lpcbBytesReturned,
  LPWSAOVERLAPPED                    lpOverlapped,
  // actually LPWSAOVERLAPPED_COMPLETION_ROUTINE
  void* lpCompletionRoutine
);

int WSAGetLastError();

BOOL DeviceIoControl(
  HANDLE       hDevice,
  DWORD        dwIoControlCode,
  LPVOID       lpInBuffer,
  DWORD        nInBufferSize,
  LPVOID       lpOutBuffer,
  DWORD        nOutBufferSize,
  LPDWORD      lpBytesReturned,
  LPOVERLAPPED lpOverlapped
);

// From https://github.com/piscisaureus/wepoll/blob/master/src/afd.h
typedef struct _AFD_POLL_HANDLE_INFO {
  HANDLE Handle;
  ULONG Events;
  NTSTATUS Status;
} AFD_POLL_HANDLE_INFO, *PAFD_POLL_HANDLE_INFO;

// This is really defined as a messy union to allow stuff like
// i.DUMMYSTRUCTNAME.LowPart, but we don't need those complications.
// Under all that it's just an int64.
typedef int64_t LARGE_INTEGER;

typedef struct _AFD_POLL_INFO {
  LARGE_INTEGER Timeout;
  ULONG NumberOfHandles;
  ULONG Exclusive;
  AFD_POLL_HANDLE_INFO Handles[1];
} AFD_POLL_INFO, *PAFD_POLL_INFO;

"""

# cribbed from pywincffi
# programmatically strips out those annotations MSDN likes, like _In_
REGEX_SAL_ANNOTATION = re.compile(
    r"\b(_In_|_Inout_|_Out_|_Outptr_|_Reserved_)(opt_)?\b",
)
LIB = REGEX_SAL_ANNOTATION.sub(" ", LIB)

# Other fixups:
# - get rid of FAR, cffi doesn't like it
LIB = re.sub(r"\bFAR\b", " ", LIB)
# - PASCAL is apparently an alias for __stdcall (on modern compilers - modern
#   being _MSC_VER >= 800)
LIB = re.sub(r"\bPASCAL\b", "__stdcall", LIB)

ffi = cffi.api.FFI()
ffi.cdef(LIB)

CData: TypeAlias = cffi.api.FFI.CData
CType: TypeAlias = cffi.api.FFI.CType
AlwaysNull: TypeAlias = CType  # We currently always pass ffi.NULL here.
Handle = NewType("Handle", CData)
HandleArray = NewType("HandleArray", CData)


class _Kernel32(Protocol):
    """Statically typed version of the kernel32.dll functions we use."""

    def CreateIoCompletionPort(
        self,
        FileHandle: Handle,
        ExistingCompletionPort: CData | AlwaysNull,
        CompletionKey: int,
        NumberOfConcurrentThreads: int,
        /,
    ) -> Handle: ...

    def CreateEventA(
        self,
        lpEventAttributes: AlwaysNull,
        bManualReset: bool,
        bInitialState: bool,
        lpName: AlwaysNull,
        /,
    ) -> Handle: ...

    def SetFileCompletionNotificationModes(
        self,
        handle: Handle,
        flags: CompletionModes,
        /,
    ) -> int: ...

    def PostQueuedCompletionStatus(
        self,
        CompletionPort: Handle,
        dwNumberOfBytesTransferred: int,
        dwCompletionKey: int,
        lpOverlapped: CData | AlwaysNull,
        /,
    ) -> bool: ...

    def CancelIoEx(
        self,
        hFile: Handle,
        lpOverlapped: CData | AlwaysNull,
        /,
    ) -> bool: ...

    def WriteFile(
        self,
        hFile: Handle,
        # not sure about this type
        lpBuffer: CData,
        nNumberOfBytesToWrite: int,
        lpNumberOfBytesWritten: AlwaysNull,
        lpOverlapped: _Overlapped,
        /,
    ) -> bool: ...

    def ReadFile(
        self,
        hFile: Handle,
        # not sure about this type
        lpBuffer: CData,
        nNumberOfBytesToRead: int,
        lpNumberOfBytesRead: AlwaysNull,
        lpOverlapped: _Overlapped,
        /,
    ) -> bool: ...

    def GetQueuedCompletionStatusEx(
        self,
        CompletionPort: Handle,
        lpCompletionPortEntries: CData,
        ulCount: int,
        ulNumEntriesRemoved: CData,
        dwMilliseconds: int,
        fAlertable: bool | int,
        /,
    ) -> CData: ...

    def CreateFileW(
        self,
        lpFileName: CData,
        dwDesiredAccess: FileFlags,
        dwShareMode: FileFlags,
        lpSecurityAttributes: AlwaysNull,
        dwCreationDisposition: FileFlags,
        dwFlagsAndAttributes: FileFlags,
        hTemplateFile: AlwaysNull,
        /,
    ) -> Handle: ...

    def WaitForSingleObject(self, hHandle: Handle, dwMilliseconds: int, /) -> CData: ...

    def WaitForMultipleObjects(
        self,
        nCount: int,
        lpHandles: HandleArray,
        bWaitAll: bool,
        dwMilliseconds: int,
        /,
    ) -> ErrorCodes: ...

    def SetEvent(self, handle: Handle, /) -> None: ...

    def CloseHandle(self, handle: Handle, /) -> bool: ...

    def DeviceIoControl(
        self,
        hDevice: Handle,
        dwIoControlCode: int,
        # this is wrong (it's not always null)
        lpInBuffer: AlwaysNull,
        nInBufferSize: int,
        # this is also wrong
        lpOutBuffer: AlwaysNull,
        nOutBufferSize: int,
        lpBytesReturned: AlwaysNull,
        lpOverlapped: CData,
        /,
    ) -> bool: ...


class _Nt(Protocol):
    """Statically typed version of the dtdll.dll functions we use."""

    def RtlNtStatusToDosError(self, status: int, /) -> ErrorCodes: ...


class _Ws2(Protocol):
    """Statically typed version of the ws2_32.dll functions we use."""

    def WSAGetLastError(self) -> int: ...

    def WSAIoctl(
        self,
        socket: CData,
        dwIoControlCode: WSAIoctls,
        lpvInBuffer: AlwaysNull,
        cbInBuffer: int,
        lpvOutBuffer: CData,
        cbOutBuffer: int,
        lpcbBytesReturned: CData,  # int*
        lpOverlapped: AlwaysNull,
        # actually LPWSAOVERLAPPED_COMPLETION_ROUTINE
        lpCompletionRoutine: AlwaysNull,
        /,
    ) -> int: ...


class _DummyStruct(Protocol):
    Offset: int
    OffsetHigh: int


class _DummyUnion(Protocol):
    DUMMYSTRUCTNAME: _DummyStruct
    Pointer: object


class _Overlapped(Protocol):
    Internal: int
    InternalHigh: int
    DUMMYUNIONNAME: _DummyUnion
    hEvent: Handle


kernel32 = cast("_Kernel32", ffi.dlopen("kernel32.dll"))
ntdll = cast("_Nt", ffi.dlopen("ntdll.dll"))
ws2_32 = cast("_Ws2", ffi.dlopen("ws2_32.dll"))

################################################################
# Magic numbers
################################################################

# Here's a great resource for looking these up:
#   https://www.magnumdb.com
# (Tip: check the box to see "Hex value")

INVALID_HANDLE_VALUE = Handle(ffi.cast("HANDLE", -1))


class ErrorCodes(enum.IntEnum):
    STATUS_TIMEOUT = 0x102
    WAIT_TIMEOUT = 0x102
    WAIT_ABANDONED = 0x80
    WAIT_OBJECT_0 = 0x00  # object is signaled
    WAIT_FAILED = 0xFFFFFFFF
    ERROR_IO_PENDING = 997
    ERROR_OPERATION_ABORTED = 995
    ERROR_ABANDONED_WAIT_0 = 735
    ERROR_INVALID_HANDLE = 6
    ERROR_INVALID_PARAMETER = 87
    ERROR_NOT_FOUND = 1168
    ERROR_NOT_SOCKET = 10038


class FileFlags(enum.IntFlag):
    GENERIC_READ = 0x80000000
    SYNCHRONIZE = 0x00100000
    FILE_FLAG_OVERLAPPED = 0x40000000
    FILE_SHARE_READ = 1
    FILE_SHARE_WRITE = 2
    FILE_SHARE_DELETE = 4
    CREATE_NEW = 1
    CREATE_ALWAYS = 2
    OPEN_EXISTING = 3
    OPEN_ALWAYS = 4
    TRUNCATE_EXISTING = 5


class AFDPollFlags(enum.IntFlag):
    # These are drawn from a combination of:
    #   https://github.com/piscisaureus/wepoll/blob/master/src/afd.h
    #   https://github.com/reactos/reactos/blob/master/sdk/include/reactos/drivers/afd/shared.h
    AFD_POLL_RECEIVE = 0x0001
    AFD_POLL_RECEIVE_EXPEDITED = 0x0002  # OOB/urgent data
    AFD_POLL_SEND = 0x0004
    AFD_POLL_DISCONNECT = 0x0008  # received EOF (FIN)
    AFD_POLL_ABORT = 0x0010  # received RST
    AFD_POLL_LOCAL_CLOSE = 0x0020  # local socket object closed
    AFD_POLL_CONNECT = 0x0040  # socket is successfully connected
    AFD_POLL_ACCEPT = 0x0080  # you can call accept on this socket
    AFD_POLL_CONNECT_FAIL = 0x0100  # connect() terminated unsuccessfully
    # See WSAEventSelect docs for more details on these four:
    AFD_POLL_QOS = 0x0200
    AFD_POLL_GROUP_QOS = 0x0400
    AFD_POLL_ROUTING_INTERFACE_CHANGE = 0x0800
    AFD_POLL_EVENT_ADDRESS_LIST_CHANGE = 0x1000


class WSAIoctls(enum.IntEnum):
    SIO_BASE_HANDLE = 0x48000022
    SIO_BSP_HANDLE_SELECT = 0x4800001C
    SIO_BSP_HANDLE_POLL = 0x4800001D


class CompletionModes(enum.IntFlag):
    FILE_SKIP_COMPLETION_PORT_ON_SUCCESS = 0x1
    FILE_SKIP_SET_EVENT_ON_HANDLE = 0x2


class IoControlCodes(enum.IntEnum):
    IOCTL_AFD_POLL = 0x00012024


################################################################
# Generic helpers
################################################################


def _handle(obj: int | CData) -> Handle:
    # For now, represent handles as either cffi HANDLEs or as ints.  If you
    # try to pass in a file descriptor instead, it's not going to work
    # out. (For that msvcrt.get_osfhandle does the trick, but I don't know if
    # we'll actually need that for anything...) For sockets this doesn't
    # matter, Python never allocates an fd. So let's wait until we actually
    # encounter the problem before worrying about it.
    if isinstance(obj, int):
        return Handle(ffi.cast("HANDLE", obj))
    return Handle(obj)


def handle_array(count: int) -> HandleArray:
    """Make an array of handles."""
    return HandleArray(ffi.new(f"HANDLE[{count}]"))


def raise_winerror(
    winerror: int | None = None,
    *,
    filename: str | None = None,
    filename2: str | None = None,
) -> NoReturn:
    # assert sys.platform == "win32"  # TODO: make this work in MyPy
    # ... in the meanwhile, ffi.getwinerror() is undefined on non-Windows, necessitating the type
    # ignores.

    if winerror is None:
        err = ffi.getwinerror()  # type: ignore[attr-defined,unused-ignore]
        if err is None:
            raise RuntimeError("No error set?")
        winerror, msg = err
    else:
        err = ffi.getwinerror(winerror)  # type: ignore[attr-defined,unused-ignore]
        if err is None:
            raise RuntimeError("No error set?")
        _, msg = err
    # https://docs.python.org/3/library/exceptions.html#OSError
    raise OSError(0, msg, filename, winerror, filename2)

# === NexusCore/myenv\Lib\site-packages\pip\_vendor\urllib3\contrib\_securetransport\bindings.py ===
"""
This module uses ctypes to bind a whole bunch of functions and constants from
SecureTransport. The goal here is to provide the low-level API to
SecureTransport. These are essentially the C-level functions and constants, and
they're pretty gross to work with.

This code is a bastardised version of the code found in Will Bond's oscrypto
library. An enormous debt is owed to him for blazing this trail for us. For
that reason, this code should be considered to be covered both by urllib3's
license and by oscrypto's:

    Copyright (c) 2015-2016 Will Bond <will@wbond.net>

    Permission is hereby granted, free of charge, to any person obtaining a
    copy of this software and associated documentation files (the "Software"),
    to deal in the Software without restriction, including without limitation
    the rights to use, copy, modify, merge, publish, distribute, sublicense,
    and/or sell copies of the Software, and to permit persons to whom the
    Software is furnished to do so, subject to the following conditions:

    The above copyright notice and this permission notice shall be included in
    all copies or substantial portions of the Software.

    THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
    IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
    FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
    AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
    LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
    FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
    DEALINGS IN THE SOFTWARE.
"""
from __future__ import absolute_import

import platform
from ctypes import (
    CDLL,
    CFUNCTYPE,
    POINTER,
    c_bool,
    c_byte,
    c_char_p,
    c_int32,
    c_long,
    c_size_t,
    c_uint32,
    c_ulong,
    c_void_p,
)
from ctypes.util import find_library

from ...packages.six import raise_from

if platform.system() != "Darwin":
    raise ImportError("Only macOS is supported")

version = platform.mac_ver()[0]
version_info = tuple(map(int, version.split(".")))
if version_info < (10, 8):
    raise OSError(
        "Only OS X 10.8 and newer are supported, not %s.%s"
        % (version_info[0], version_info[1])
    )


def load_cdll(name, macos10_16_path):
    """Loads a CDLL by name, falling back to known path on 10.16+"""
    try:
        # Big Sur is technically 11 but we use 10.16 due to the Big Sur
        # beta being labeled as 10.16.
        if version_info >= (10, 16):
            path = macos10_16_path
        else:
            path = find_library(name)
        if not path:
            raise OSError  # Caught and reraised as 'ImportError'
        return CDLL(path, use_errno=True)
    except OSError:
        raise_from(ImportError("The library %s failed to load" % name), None)


Security = load_cdll(
    "Security", "/System/Library/Frameworks/Security.framework/Security"
)
CoreFoundation = load_cdll(
    "CoreFoundation",
    "/System/Library/Frameworks/CoreFoundation.framework/CoreFoundation",
)


Boolean = c_bool
CFIndex = c_long
CFStringEncoding = c_uint32
CFData = c_void_p
CFString = c_void_p
CFArray = c_void_p
CFMutableArray = c_void_p
CFDictionary = c_void_p
CFError = c_void_p
CFType = c_void_p
CFTypeID = c_ulong

CFTypeRef = POINTER(CFType)
CFAllocatorRef = c_void_p

OSStatus = c_int32

CFDataRef = POINTER(CFData)
CFStringRef = POINTER(CFString)
CFArrayRef = POINTER(CFArray)
CFMutableArrayRef = POINTER(CFMutableArray)
CFDictionaryRef = POINTER(CFDictionary)
CFArrayCallBacks = c_void_p
CFDictionaryKeyCallBacks = c_void_p
CFDictionaryValueCallBacks = c_void_p

SecCertificateRef = POINTER(c_void_p)
SecExternalFormat = c_uint32
SecExternalItemType = c_uint32
SecIdentityRef = POINTER(c_void_p)
SecItemImportExportFlags = c_uint32
SecItemImportExportKeyParameters = c_void_p
SecKeychainRef = POINTER(c_void_p)
SSLProtocol = c_uint32
SSLCipherSuite = c_uint32
SSLContextRef = POINTER(c_void_p)
SecTrustRef = POINTER(c_void_p)
SSLConnectionRef = c_uint32
SecTrustResultType = c_uint32
SecTrustOptionFlags = c_uint32
SSLProtocolSide = c_uint32
SSLConnectionType = c_uint32
SSLSessionOption = c_uint32


try:
    Security.SecItemImport.argtypes = [
        CFDataRef,
        CFStringRef,
        POINTER(SecExternalFormat),
        POINTER(SecExternalItemType),
        SecItemImportExportFlags,
        POINTER(SecItemImportExportKeyParameters),
        SecKeychainRef,
        POINTER(CFArrayRef),
    ]
    Security.SecItemImport.restype = OSStatus

    Security.SecCertificateGetTypeID.argtypes = []
    Security.SecCertificateGetTypeID.restype = CFTypeID

    Security.SecIdentityGetTypeID.argtypes = []
    Security.SecIdentityGetTypeID.restype = CFTypeID

    Security.SecKeyGetTypeID.argtypes = []
    Security.SecKeyGetTypeID.restype = CFTypeID

    Security.SecCertificateCreateWithData.argtypes = [CFAllocatorRef, CFDataRef]
    Security.SecCertificateCreateWithData.restype = SecCertificateRef

    Security.SecCertificateCopyData.argtypes = [SecCertificateRef]
    Security.SecCertificateCopyData.restype = CFDataRef

    Security.SecCopyErrorMessageString.argtypes = [OSStatus, c_void_p]
    Security.SecCopyErrorMessageString.restype = CFStringRef

    Security.SecIdentityCreateWithCertificate.argtypes = [
        CFTypeRef,
        SecCertificateRef,
        POINTER(SecIdentityRef),
    ]
    Security.SecIdentityCreateWithCertificate.restype = OSStatus

    Security.SecKeychainCreate.argtypes = [
        c_char_p,
        c_uint32,
        c_void_p,
        Boolean,
        c_void_p,
        POINTER(SecKeychainRef),
    ]
    Security.SecKeychainCreate.restype = OSStatus

    Security.SecKeychainDelete.argtypes = [SecKeychainRef]
    Security.SecKeychainDelete.restype = OSStatus

    Security.SecPKCS12Import.argtypes = [
        CFDataRef,
        CFDictionaryRef,
        POINTER(CFArrayRef),
    ]
    Security.SecPKCS12Import.restype = OSStatus

    SSLReadFunc = CFUNCTYPE(OSStatus, SSLConnectionRef, c_void_p, POINTER(c_size_t))
    SSLWriteFunc = CFUNCTYPE(
        OSStatus, SSLConnectionRef, POINTER(c_byte), POINTER(c_size_t)
    )

    Security.SSLSetIOFuncs.argtypes = [SSLContextRef, SSLReadFunc, SSLWriteFunc]
    Security.SSLSetIOFuncs.restype = OSStatus

    Security.SSLSetPeerID.argtypes = [SSLContextRef, c_char_p, c_size_t]
    Security.SSLSetPeerID.restype = OSStatus

    Security.SSLSetCertificate.argtypes = [SSLContextRef, CFArrayRef]
    Security.SSLSetCertificate.restype = OSStatus

    Security.SSLSetCertificateAuthorities.argtypes = [SSLContextRef, CFTypeRef, Boolean]
    Security.SSLSetCertificateAuthorities.restype = OSStatus

    Security.SSLSetConnection.argtypes = [SSLContextRef, SSLConnectionRef]
    Security.SSLSetConnection.restype = OSStatus

    Security.SSLSetPeerDomainName.argtypes = [SSLContextRef, c_char_p, c_size_t]
    Security.SSLSetPeerDomainName.restype = OSStatus

    Security.SSLHandshake.argtypes = [SSLContextRef]
    Security.SSLHandshake.restype = OSStatus

    Security.SSLRead.argtypes = [SSLContextRef, c_char_p, c_size_t, POINTER(c_size_t)]
    Security.SSLRead.restype = OSStatus

    Security.SSLWrite.argtypes = [SSLContextRef, c_char_p, c_size_t, POINTER(c_size_t)]
    Security.SSLWrite.restype = OSStatus

    Security.SSLClose.argtypes = [SSLContextRef]
    Security.SSLClose.restype = OSStatus

    Security.SSLGetNumberSupportedCiphers.argtypes = [SSLContextRef, POINTER(c_size_t)]
    Security.SSLGetNumberSupportedCiphers.restype = OSStatus

    Security.SSLGetSupportedCiphers.argtypes = [
        SSLContextRef,
        POINTER(SSLCipherSuite),
        POINTER(c_size_t),
    ]
    Security.SSLGetSupportedCiphers.restype = OSStatus

    Security.SSLSetEnabledCiphers.argtypes = [
        SSLContextRef,
        POINTER(SSLCipherSuite),
        c_size_t,
    ]
    Security.SSLSetEnabledCiphers.restype = OSStatus

    Security.SSLGetNumberEnabledCiphers.argtype = [SSLContextRef, POINTER(c_size_t)]
    Security.SSLGetNumberEnabledCiphers.restype = OSStatus

    Security.SSLGetEnabledCiphers.argtypes = [
        SSLContextRef,
        POINTER(SSLCipherSuite),
        POINTER(c_size_t),
    ]
    Security.SSLGetEnabledCiphers.restype = OSStatus

    Security.SSLGetNegotiatedCipher.argtypes = [SSLContextRef, POINTER(SSLCipherSuite)]
    Security.SSLGetNegotiatedCipher.restype = OSStatus

    Security.SSLGetNegotiatedProtocolVersion.argtypes = [
        SSLContextRef,
        POINTER(SSLProtocol),
    ]
    Security.SSLGetNegotiatedProtocolVersion.restype = OSStatus

    Security.SSLCopyPeerTrust.argtypes = [SSLContextRef, POINTER(SecTrustRef)]
    Security.SSLCopyPeerTrust.restype = OSStatus

    Security.SecTrustSetAnchorCertificates.argtypes = [SecTrustRef, CFArrayRef]
    Security.SecTrustSetAnchorCertificates.restype = OSStatus

    Security.SecTrustSetAnchorCertificatesOnly.argstypes = [SecTrustRef, Boolean]
    Security.SecTrustSetAnchorCertificatesOnly.restype = OSStatus

    Security.SecTrustEvaluate.argtypes = [SecTrustRef, POINTER(SecTrustResultType)]
    Security.SecTrustEvaluate.restype = OSStatus

    Security.SecTrustGetCertificateCount.argtypes = [SecTrustRef]
    Security.SecTrustGetCertificateCount.restype = CFIndex

    Security.SecTrustGetCertificateAtIndex.argtypes = [SecTrustRef, CFIndex]
    Security.SecTrustGetCertificateAtIndex.restype = SecCertificateRef

    Security.SSLCreateContext.argtypes = [
        CFAllocatorRef,
        SSLProtocolSide,
        SSLConnectionType,
    ]
    Security.SSLCreateContext.restype = SSLContextRef

    Security.SSLSetSessionOption.argtypes = [SSLContextRef, SSLSessionOption, Boolean]
    Security.SSLSetSessionOption.restype = OSStatus

    Security.SSLSetProtocolVersionMin.argtypes = [SSLContextRef, SSLProtocol]
    Security.SSLSetProtocolVersionMin.restype = OSStatus

    Security.SSLSetProtocolVersionMax.argtypes = [SSLContextRef, SSLProtocol]
    Security.SSLSetProtocolVersionMax.restype = OSStatus

    try:
        Security.SSLSetALPNProtocols.argtypes = [SSLContextRef, CFArrayRef]
        Security.SSLSetALPNProtocols.restype = OSStatus
    except AttributeError:
        # Supported only in 10.12+
        pass

    Security.SecCopyErrorMessageString.argtypes = [OSStatus, c_void_p]
    Security.SecCopyErrorMessageString.restype = CFStringRef

    Security.SSLReadFunc = SSLReadFunc
    Security.SSLWriteFunc = SSLWriteFunc
    Security.SSLContextRef = SSLContextRef
    Security.SSLProtocol = SSLProtocol
    Security.SSLCipherSuite = SSLCipherSuite
    Security.SecIdentityRef = SecIdentityRef
    Security.SecKeychainRef = SecKeychainRef
    Security.SecTrustRef = SecTrustRef
    Security.SecTrustResultType = SecTrustResultType
    Security.SecExternalFormat = SecExternalFormat
    Security.OSStatus = OSStatus

    Security.kSecImportExportPassphrase = CFStringRef.in_dll(
        Security, "kSecImportExportPassphrase"
    )
    Security.kSecImportItemIdentity = CFStringRef.in_dll(
        Security, "kSecImportItemIdentity"
    )

    # CoreFoundation time!
    CoreFoundation.CFRetain.argtypes = [CFTypeRef]
    CoreFoundation.CFRetain.restype = CFTypeRef

    CoreFoundation.CFRelease.argtypes = [CFTypeRef]
    CoreFoundation.CFRelease.restype = None

    CoreFoundation.CFGetTypeID.argtypes = [CFTypeRef]
    CoreFoundation.CFGetTypeID.restype = CFTypeID

    CoreFoundation.CFStringCreateWithCString.argtypes = [
        CFAllocatorRef,
        c_char_p,
        CFStringEncoding,
    ]
    CoreFoundation.CFStringCreateWithCString.restype = CFStringRef

    CoreFoundation.CFStringGetCStringPtr.argtypes = [CFStringRef, CFStringEncoding]
    CoreFoundation.CFStringGetCStringPtr.restype = c_char_p

    CoreFoundation.CFStringGetCString.argtypes = [
        CFStringRef,
        c_char_p,
        CFIndex,
        CFStringEncoding,
    ]
    CoreFoundation.CFStringGetCString.restype = c_bool

    CoreFoundation.CFDataCreate.argtypes = [CFAllocatorRef, c_char_p, CFIndex]
    CoreFoundation.CFDataCreate.restype = CFDataRef

    CoreFoundation.CFDataGetLength.argtypes = [CFDataRef]
    CoreFoundation.CFDataGetLength.restype = CFIndex

    CoreFoundation.CFDataGetBytePtr.argtypes = [CFDataRef]
    CoreFoundation.CFDataGetBytePtr.restype = c_void_p

    CoreFoundation.CFDictionaryCreate.argtypes = [
        CFAllocatorRef,
        POINTER(CFTypeRef),
        POINTER(CFTypeRef),
        CFIndex,
        CFDictionaryKeyCallBacks,
        CFDictionaryValueCallBacks,
    ]
    CoreFoundation.CFDictionaryCreate.restype = CFDictionaryRef

    CoreFoundation.CFDictionaryGetValue.argtypes = [CFDictionaryRef, CFTypeRef]
    CoreFoundation.CFDictionaryGetValue.restype = CFTypeRef

    CoreFoundation.CFArrayCreate.argtypes = [
        CFAllocatorRef,
        POINTER(CFTypeRef),
        CFIndex,
        CFArrayCallBacks,
    ]
    CoreFoundation.CFArrayCreate.restype = CFArrayRef

    CoreFoundation.CFArrayCreateMutable.argtypes = [
        CFAllocatorRef,
        CFIndex,
        CFArrayCallBacks,
    ]
    CoreFoundation.CFArrayCreateMutable.restype = CFMutableArrayRef

    CoreFoundation.CFArrayAppendValue.argtypes = [CFMutableArrayRef, c_void_p]
    CoreFoundation.CFArrayAppendValue.restype = None

    CoreFoundation.CFArrayGetCount.argtypes = [CFArrayRef]
    CoreFoundation.CFArrayGetCount.restype = CFIndex

    CoreFoundation.CFArrayGetValueAtIndex.argtypes = [CFArrayRef, CFIndex]
    CoreFoundation.CFArrayGetValueAtIndex.restype = c_void_p

    CoreFoundation.kCFAllocatorDefault = CFAllocatorRef.in_dll(
        CoreFoundation, "kCFAllocatorDefault"
    )
    CoreFoundation.kCFTypeArrayCallBacks = c_void_p.in_dll(
        CoreFoundation, "kCFTypeArrayCallBacks"
    )
    CoreFoundation.kCFTypeDictionaryKeyCallBacks = c_void_p.in_dll(
        CoreFoundation, "kCFTypeDictionaryKeyCallBacks"
    )
    CoreFoundation.kCFTypeDictionaryValueCallBacks = c_void_p.in_dll(
        CoreFoundation, "kCFTypeDictionaryValueCallBacks"
    )

    CoreFoundation.CFTypeRef = CFTypeRef
    CoreFoundation.CFArrayRef = CFArrayRef
    CoreFoundation.CFStringRef = CFStringRef
    CoreFoundation.CFDictionaryRef = CFDictionaryRef

except (AttributeError):
    raise ImportError("Error initializing ctypes")


class CFConst(object):
    """
    A class object that acts as essentially a namespace for CoreFoundation
    constants.
    """

    kCFStringEncodingUTF8 = CFStringEncoding(0x08000100)


class SecurityConst(object):
    """
    A class object that acts as essentially a namespace for Security constants.
    """

    kSSLSessionOptionBreakOnServerAuth = 0

    kSSLProtocol2 = 1
    kSSLProtocol3 = 2
    kTLSProtocol1 = 4
    kTLSProtocol11 = 7
    kTLSProtocol12 = 8
    # SecureTransport does not support TLS 1.3 even if there's a constant for it
    kTLSProtocol13 = 10
    kTLSProtocolMaxSupported = 999

    kSSLClientSide = 1
    kSSLStreamType = 0

    kSecFormatPEMSequence = 10

    kSecTrustResultInvalid = 0
    kSecTrustResultProceed = 1
    # This gap is present on purpose: this was kSecTrustResultConfirm, which
    # is deprecated.
    kSecTrustResultDeny = 3
    kSecTrustResultUnspecified = 4
    kSecTrustResultRecoverableTrustFailure = 5
    kSecTrustResultFatalTrustFailure = 6
    kSecTrustResultOtherError = 7

    errSSLProtocol = -9800
    errSSLWouldBlock = -9803
    errSSLClosedGraceful = -9805
    errSSLClosedNoNotify = -9816
    errSSLClosedAbort = -9806

    errSSLXCertChainInvalid = -9807
    errSSLCrypto = -9809
    errSSLInternal = -9810
    errSSLCertExpired = -9814
    errSSLCertNotYetValid = -9815
    errSSLUnknownRootCert = -9812
    errSSLNoRootCert = -9813
    errSSLHostNameMismatch = -9843
    errSSLPeerHandshakeFail = -9824
    errSSLPeerUserCancelled = -9839
    errSSLWeakPeerEphemeralDHKey = -9850
    errSSLServerAuthCompleted = -9841
    errSSLRecordOverflow = -9847

    errSecVerifyFailed = -67808
    errSecNoTrustSettings = -25263
    errSecItemNotFound = -25300
    errSecInvalidTrustSettings = -25262

    # Cipher suites. We only pick the ones our default cipher string allows.
    # Source: https://developer.apple.com/documentation/security/1550981-ssl_cipher_suite_values
    TLS_ECDHE_ECDSA_WITH_AES_256_GCM_SHA384 = 0xC02C
    TLS_ECDHE_RSA_WITH_AES_256_GCM_SHA384 = 0xC030
    TLS_ECDHE_ECDSA_WITH_AES_128_GCM_SHA256 = 0xC02B
    TLS_ECDHE_RSA_WITH_AES_128_GCM_SHA256 = 0xC02F
    TLS_ECDHE_ECDSA_WITH_CHACHA20_POLY1305_SHA256 = 0xCCA9
    TLS_ECDHE_RSA_WITH_CHACHA20_POLY1305_SHA256 = 0xCCA8
    TLS_DHE_RSA_WITH_AES_256_GCM_SHA384 = 0x009F
    TLS_DHE_RSA_WITH_AES_128_GCM_SHA256 = 0x009E
    TLS_ECDHE_ECDSA_WITH_AES_256_CBC_SHA384 = 0xC024
    TLS_ECDHE_RSA_WITH_AES_256_CBC_SHA384 = 0xC028
    TLS_ECDHE_ECDSA_WITH_AES_256_CBC_SHA = 0xC00A
    TLS_ECDHE_RSA_WITH_AES_256_CBC_SHA = 0xC014
    TLS_DHE_RSA_WITH_AES_256_CBC_SHA256 = 0x006B
    TLS_DHE_RSA_WITH_AES_256_CBC_SHA = 0x0039
    TLS_ECDHE_ECDSA_WITH_AES_128_CBC_SHA256 = 0xC023
    TLS_ECDHE_RSA_WITH_AES_128_CBC_SHA256 = 0xC027
    TLS_ECDHE_ECDSA_WITH_AES_128_CBC_SHA = 0xC009
    TLS_ECDHE_RSA_WITH_AES_128_CBC_SHA = 0xC013
    TLS_DHE_RSA_WITH_AES_128_CBC_SHA256 = 0x0067
    TLS_DHE_RSA_WITH_AES_128_CBC_SHA = 0x0033
    TLS_RSA_WITH_AES_256_GCM_SHA384 = 0x009D
    TLS_RSA_WITH_AES_128_GCM_SHA256 = 0x009C
    TLS_RSA_WITH_AES_256_CBC_SHA256 = 0x003D
    TLS_RSA_WITH_AES_128_CBC_SHA256 = 0x003C
    TLS_RSA_WITH_AES_256_CBC_SHA = 0x0035
    TLS_RSA_WITH_AES_128_CBC_SHA = 0x002F
    TLS_AES_128_GCM_SHA256 = 0x1301
    TLS_AES_256_GCM_SHA384 = 0x1302
    TLS_AES_128_CCM_8_SHA256 = 0x1305
    TLS_AES_128_CCM_SHA256 = 0x1304

# === NexusCore/openenv\Lib\site-packages\typer\models.py ===
import inspect
import io
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Dict,
    List,
    Optional,
    Sequence,
    Type,
    TypeVar,
    Union,
)

import click
import click.shell_completion

if TYPE_CHECKING:  # pragma: no cover
    from .core import TyperCommand, TyperGroup
    from .main import Typer


NoneType = type(None)

AnyType = Type[Any]

Required = ...


class Context(click.Context):
    pass


class FileText(io.TextIOWrapper):
    pass


class FileTextWrite(FileText):
    pass


class FileBinaryRead(io.BufferedReader):
    pass


class FileBinaryWrite(io.BufferedWriter):
    pass


class CallbackParam(click.Parameter):
    pass


class DefaultPlaceholder:
    """
    You shouldn't use this class directly.

    It's used internally to recognize when a default value has been overwritten, even
    if the new value is `None`.
    """

    def __init__(self, value: Any):
        self.value = value

    def __bool__(self) -> bool:
        return bool(self.value)


DefaultType = TypeVar("DefaultType")

CommandFunctionType = TypeVar("CommandFunctionType", bound=Callable[..., Any])


def Default(value: DefaultType) -> DefaultType:
    """
    You shouldn't use this function directly.

    It's used internally to recognize when a default value has been overwritten, even
    if the new value is `None`.
    """
    return DefaultPlaceholder(value)  # type: ignore


class CommandInfo:
    def __init__(
        self,
        name: Optional[str] = None,
        *,
        cls: Optional[Type["TyperCommand"]] = None,
        context_settings: Optional[Dict[Any, Any]] = None,
        callback: Optional[Callable[..., Any]] = None,
        help: Optional[str] = None,
        epilog: Optional[str] = None,
        short_help: Optional[str] = None,
        options_metavar: str = "[OPTIONS]",
        add_help_option: bool = True,
        no_args_is_help: bool = False,
        hidden: bool = False,
        deprecated: bool = False,
        # Rich settings
        rich_help_panel: Union[str, None] = None,
    ):
        self.name = name
        self.cls = cls
        self.context_settings = context_settings
        self.callback = callback
        self.help = help
        self.epilog = epilog
        self.short_help = short_help
        self.options_metavar = options_metavar
        self.add_help_option = add_help_option
        self.no_args_is_help = no_args_is_help
        self.hidden = hidden
        self.deprecated = deprecated
        # Rich settings
        self.rich_help_panel = rich_help_panel


class TyperInfo:
    def __init__(
        self,
        typer_instance: Optional["Typer"] = Default(None),
        *,
        name: Optional[str] = Default(None),
        cls: Optional[Type["TyperGroup"]] = Default(None),
        invoke_without_command: bool = Default(False),
        no_args_is_help: bool = Default(False),
        subcommand_metavar: Optional[str] = Default(None),
        chain: bool = Default(False),
        result_callback: Optional[Callable[..., Any]] = Default(None),
        # Command
        context_settings: Optional[Dict[Any, Any]] = Default(None),
        callback: Optional[Callable[..., Any]] = Default(None),
        help: Optional[str] = Default(None),
        epilog: Optional[str] = Default(None),
        short_help: Optional[str] = Default(None),
        options_metavar: str = Default("[OPTIONS]"),
        add_help_option: bool = Default(True),
        hidden: bool = Default(False),
        deprecated: bool = Default(False),
        # Rich settings
        rich_help_panel: Union[str, None] = Default(None),
    ):
        self.typer_instance = typer_instance
        self.name = name
        self.cls = cls
        self.invoke_without_command = invoke_without_command
        self.no_args_is_help = no_args_is_help
        self.subcommand_metavar = subcommand_metavar
        self.chain = chain
        self.result_callback = result_callback
        self.context_settings = context_settings
        self.callback = callback
        self.help = help
        self.epilog = epilog
        self.short_help = short_help
        self.options_metavar = options_metavar
        self.add_help_option = add_help_option
        self.hidden = hidden
        self.deprecated = deprecated
        self.rich_help_panel = rich_help_panel


class ParameterInfo:
    def __init__(
        self,
        *,
        default: Optional[Any] = None,
        param_decls: Optional[Sequence[str]] = None,
        callback: Optional[Callable[..., Any]] = None,
        metavar: Optional[str] = None,
        expose_value: bool = True,
        is_eager: bool = False,
        envvar: Optional[Union[str, List[str]]] = None,
        shell_complete: Optional[
            Callable[
                [click.Context, click.Parameter, str],
                Union[List["click.shell_completion.CompletionItem"], List[str]],
            ]
        ] = None,
        autocompletion: Optional[Callable[..., Any]] = None,
        default_factory: Optional[Callable[[], Any]] = None,
        # Custom type
        parser: Optional[Callable[[str], Any]] = None,
        click_type: Optional[click.ParamType] = None,
        # TyperArgument
        show_default: Union[bool, str] = True,
        show_choices: bool = True,
        show_envvar: bool = True,
        help: Optional[str] = None,
        hidden: bool = False,
        # Choice
        case_sensitive: bool = True,
        # Numbers
        min: Optional[Union[int, float]] = None,
        max: Optional[Union[int, float]] = None,
        clamp: bool = False,
        # DateTime
        formats: Optional[List[str]] = None,
        # File
        mode: Optional[str] = None,
        encoding: Optional[str] = None,
        errors: Optional[str] = "strict",
        lazy: Optional[bool] = None,
        atomic: bool = False,
        # Path
        exists: bool = False,
        file_okay: bool = True,
        dir_okay: bool = True,
        writable: bool = False,
        readable: bool = True,
        resolve_path: bool = False,
        allow_dash: bool = False,
        path_type: Union[None, Type[str], Type[bytes]] = None,
        # Rich settings
        rich_help_panel: Union[str, None] = None,
    ):
        # Check if user has provided multiple custom parsers
        if parser and click_type:
            raise ValueError(
                "Multiple custom type parsers provided. "
                "`parser` and `click_type` may not both be provided."
            )

        self.default = default
        self.param_decls = param_decls
        self.callback = callback
        self.metavar = metavar
        self.expose_value = expose_value
        self.is_eager = is_eager
        self.envvar = envvar
        self.shell_complete = shell_complete
        self.autocompletion = autocompletion
        self.default_factory = default_factory
        # Custom type
        self.parser = parser
        self.click_type = click_type
        # TyperArgument
        self.show_default = show_default
        self.show_choices = show_choices
        self.show_envvar = show_envvar
        self.help = help
        self.hidden = hidden
        # Choice
        self.case_sensitive = case_sensitive
        # Numbers
        self.min = min
        self.max = max
        self.clamp = clamp
        # DateTime
        self.formats = formats
        # File
        self.mode = mode
        self.encoding = encoding
        self.errors = errors
        self.lazy = lazy
        self.atomic = atomic
        # Path
        self.exists = exists
        self.file_okay = file_okay
        self.dir_okay = dir_okay
        self.writable = writable
        self.readable = readable
        self.resolve_path = resolve_path
        self.allow_dash = allow_dash
        self.path_type = path_type
        # Rich settings
        self.rich_help_panel = rich_help_panel


class OptionInfo(ParameterInfo):
    def __init__(
        self,
        *,
        # ParameterInfo
        default: Optional[Any] = None,
        param_decls: Optional[Sequence[str]] = None,
        callback: Optional[Callable[..., Any]] = None,
        metavar: Optional[str] = None,
        expose_value: bool = True,
        is_eager: bool = False,
        envvar: Optional[Union[str, List[str]]] = None,
        shell_complete: Optional[
            Callable[
                [click.Context, click.Parameter, str],
                Union[List["click.shell_completion.CompletionItem"], List[str]],
            ]
        ] = None,
        autocompletion: Optional[Callable[..., Any]] = None,
        default_factory: Optional[Callable[[], Any]] = None,
        # Custom type
        parser: Optional[Callable[[str], Any]] = None,
        click_type: Optional[click.ParamType] = None,
        # Option
        show_default: Union[bool, str] = True,
        prompt: Union[bool, str] = False,
        confirmation_prompt: bool = False,
        prompt_required: bool = True,
        hide_input: bool = False,
        is_flag: Optional[bool] = None,
        flag_value: Optional[Any] = None,
        count: bool = False,
        allow_from_autoenv: bool = True,
        help: Optional[str] = None,
        hidden: bool = False,
        show_choices: bool = True,
        show_envvar: bool = True,
        # Choice
        case_sensitive: bool = True,
        # Numbers
        min: Optional[Union[int, float]] = None,
        max: Optional[Union[int, float]] = None,
        clamp: bool = False,
        # DateTime
        formats: Optional[List[str]] = None,
        # File
        mode: Optional[str] = None,
        encoding: Optional[str] = None,
        errors: Optional[str] = "strict",
        lazy: Optional[bool] = None,
        atomic: bool = False,
        # Path
        exists: bool = False,
        file_okay: bool = True,
        dir_okay: bool = True,
        writable: bool = False,
        readable: bool = True,
        resolve_path: bool = False,
        allow_dash: bool = False,
        path_type: Union[None, Type[str], Type[bytes]] = None,
        # Rich settings
        rich_help_panel: Union[str, None] = None,
    ):
        super().__init__(
            default=default,
            param_decls=param_decls,
            callback=callback,
            metavar=metavar,
            expose_value=expose_value,
            is_eager=is_eager,
            envvar=envvar,
            shell_complete=shell_complete,
            autocompletion=autocompletion,
            default_factory=default_factory,
            # Custom type
            parser=parser,
            click_type=click_type,
            # TyperArgument
            show_default=show_default,
            show_choices=show_choices,
            show_envvar=show_envvar,
            help=help,
            hidden=hidden,
            # Choice
            case_sensitive=case_sensitive,
            # Numbers
            min=min,
            max=max,
            clamp=clamp,
            # DateTime
            formats=formats,
            # File
            mode=mode,
            encoding=encoding,
            errors=errors,
            lazy=lazy,
            atomic=atomic,
            # Path
            exists=exists,
            file_okay=file_okay,
            dir_okay=dir_okay,
            writable=writable,
            readable=readable,
            resolve_path=resolve_path,
            allow_dash=allow_dash,
            path_type=path_type,
            # Rich settings
            rich_help_panel=rich_help_panel,
        )
        self.prompt = prompt
        self.confirmation_prompt = confirmation_prompt
        self.prompt_required = prompt_required
        self.hide_input = hide_input
        self.is_flag = is_flag
        self.flag_value = flag_value
        self.count = count
        self.allow_from_autoenv = allow_from_autoenv


class ArgumentInfo(ParameterInfo):
    def __init__(
        self,
        *,
        # ParameterInfo
        default: Optional[Any] = None,
        param_decls: Optional[Sequence[str]] = None,
        callback: Optional[Callable[..., Any]] = None,
        metavar: Optional[str] = None,
        expose_value: bool = True,
        is_eager: bool = False,
        envvar: Optional[Union[str, List[str]]] = None,
        shell_complete: Optional[
            Callable[
                [click.Context, click.Parameter, str],
                Union[List["click.shell_completion.CompletionItem"], List[str]],
            ]
        ] = None,
        autocompletion: Optional[Callable[..., Any]] = None,
        default_factory: Optional[Callable[[], Any]] = None,
        # Custom type
        parser: Optional[Callable[[str], Any]] = None,
        click_type: Optional[click.ParamType] = None,
        # TyperArgument
        show_default: Union[bool, str] = True,
        show_choices: bool = True,
        show_envvar: bool = True,
        help: Optional[str] = None,
        hidden: bool = False,
        # Choice
        case_sensitive: bool = True,
        # Numbers
        min: Optional[Union[int, float]] = None,
        max: Optional[Union[int, float]] = None,
        clamp: bool = False,
        # DateTime
        formats: Optional[List[str]] = None,
        # File
        mode: Optional[str] = None,
        encoding: Optional[str] = None,
        errors: Optional[str] = "strict",
        lazy: Optional[bool] = None,
        atomic: bool = False,
        # Path
        exists: bool = False,
        file_okay: bool = True,
        dir_okay: bool = True,
        writable: bool = False,
        readable: bool = True,
        resolve_path: bool = False,
        allow_dash: bool = False,
        path_type: Union[None, Type[str], Type[bytes]] = None,
        # Rich settings
        rich_help_panel: Union[str, None] = None,
    ):
        super().__init__(
            default=default,
            param_decls=param_decls,
            callback=callback,
            metavar=metavar,
            expose_value=expose_value,
            is_eager=is_eager,
            envvar=envvar,
            shell_complete=shell_complete,
            autocompletion=autocompletion,
            default_factory=default_factory,
            # Custom type
            parser=parser,
            click_type=click_type,
            # TyperArgument
            show_default=show_default,
            show_choices=show_choices,
            show_envvar=show_envvar,
            help=help,
            hidden=hidden,
            # Choice
            case_sensitive=case_sensitive,
            # Numbers
            min=min,
            max=max,
            clamp=clamp,
            # DateTime
            formats=formats,
            # File
            mode=mode,
            encoding=encoding,
            errors=errors,
            lazy=lazy,
            atomic=atomic,
            # Path
            exists=exists,
            file_okay=file_okay,
            dir_okay=dir_okay,
            writable=writable,
            readable=readable,
            resolve_path=resolve_path,
            allow_dash=allow_dash,
            path_type=path_type,
            # Rich settings
            rich_help_panel=rich_help_panel,
        )


class ParamMeta:
    empty = inspect.Parameter.empty

    def __init__(
        self,
        *,
        name: str,
        default: Any = inspect.Parameter.empty,
        annotation: Any = inspect.Parameter.empty,
    ) -> None:
        self.name = name
        self.default = default
        self.annotation = annotation


class DeveloperExceptionConfig:
    def __init__(
        self,
        *,
        pretty_exceptions_enable: bool = True,
        pretty_exceptions_show_locals: bool = True,
        pretty_exceptions_short: bool = True,
    ) -> None:
        self.pretty_exceptions_enable = pretty_exceptions_enable
        self.pretty_exceptions_show_locals = pretty_exceptions_show_locals
        self.pretty_exceptions_short = pretty_exceptions_short

# === NexusCore/openenv\Lib\site-packages\mpl_toolkits\axes_grid1\inset_locator.py ===
"""
A collection of functions and objects for creating or placing inset axes.
"""

from matplotlib import _api, _docstring
from matplotlib.offsetbox import AnchoredOffsetbox
from matplotlib.patches import Patch, Rectangle
from matplotlib.path import Path
from matplotlib.transforms import Bbox
from matplotlib.transforms import IdentityTransform, TransformedBbox

from . import axes_size as Size
from .parasite_axes import HostAxes


class AnchoredLocatorBase(AnchoredOffsetbox):
    def __init__(self, bbox_to_anchor, offsetbox, loc,
                 borderpad=0.5, bbox_transform=None):
        super().__init__(
            loc, pad=0., child=None, borderpad=borderpad,
            bbox_to_anchor=bbox_to_anchor, bbox_transform=bbox_transform
        )

    def draw(self, renderer):
        raise RuntimeError("No draw method should be called")

    def __call__(self, ax, renderer):
        fig = ax.get_figure(root=False)
        if renderer is None:
            renderer = fig._get_renderer()
        self.axes = ax
        bbox = self.get_window_extent(renderer)
        px, py = self.get_offset(bbox.width, bbox.height, 0, 0, renderer)
        bbox_canvas = Bbox.from_bounds(px, py, bbox.width, bbox.height)
        tr = fig.transSubfigure.inverted()
        return TransformedBbox(bbox_canvas, tr)


class AnchoredSizeLocator(AnchoredLocatorBase):
    def __init__(self, bbox_to_anchor, x_size, y_size, loc,
                 borderpad=0.5, bbox_transform=None):
        super().__init__(
            bbox_to_anchor, None, loc,
            borderpad=borderpad, bbox_transform=bbox_transform
        )

        self.x_size = Size.from_any(x_size)
        self.y_size = Size.from_any(y_size)

    def get_bbox(self, renderer):
        bbox = self.get_bbox_to_anchor()
        dpi = renderer.points_to_pixels(72.)

        r, a = self.x_size.get_size(renderer)
        width = bbox.width * r + a * dpi
        r, a = self.y_size.get_size(renderer)
        height = bbox.height * r + a * dpi

        fontsize = renderer.points_to_pixels(self.prop.get_size_in_points())
        pad = self.pad * fontsize

        return Bbox.from_bounds(0, 0, width, height).padded(pad)


class AnchoredZoomLocator(AnchoredLocatorBase):
    def __init__(self, parent_axes, zoom, loc,
                 borderpad=0.5,
                 bbox_to_anchor=None,
                 bbox_transform=None):
        self.parent_axes = parent_axes
        self.zoom = zoom
        if bbox_to_anchor is None:
            bbox_to_anchor = parent_axes.bbox
        super().__init__(
            bbox_to_anchor, None, loc, borderpad=borderpad,
            bbox_transform=bbox_transform)

    def get_bbox(self, renderer):
        bb = self.parent_axes.transData.transform_bbox(self.axes.viewLim)
        fontsize = renderer.points_to_pixels(self.prop.get_size_in_points())
        pad = self.pad * fontsize
        return (
            Bbox.from_bounds(
                0, 0, abs(bb.width * self.zoom), abs(bb.height * self.zoom))
            .padded(pad))


class BboxPatch(Patch):
    @_docstring.interpd
    def __init__(self, bbox, **kwargs):
        """
        Patch showing the shape bounded by a Bbox.

        Parameters
        ----------
        bbox : `~matplotlib.transforms.Bbox`
            Bbox to use for the extents of this patch.

        **kwargs
            Patch properties. Valid arguments include:

            %(Patch:kwdoc)s
        """
        if "transform" in kwargs:
            raise ValueError("transform should not be set")

        kwargs["transform"] = IdentityTransform()
        super().__init__(**kwargs)
        self.bbox = bbox

    def get_path(self):
        # docstring inherited
        x0, y0, x1, y1 = self.bbox.extents
        return Path._create_closed([(x0, y0), (x1, y0), (x1, y1), (x0, y1)])


class BboxConnector(Patch):
    @staticmethod
    def get_bbox_edge_pos(bbox, loc):
        """
        Return the ``(x, y)`` coordinates of corner *loc* of *bbox*; parameters
        behave as documented for the `.BboxConnector` constructor.
        """
        x0, y0, x1, y1 = bbox.extents
        if loc == 1:
            return x1, y1
        elif loc == 2:
            return x0, y1
        elif loc == 3:
            return x0, y0
        elif loc == 4:
            return x1, y0

    @staticmethod
    def connect_bbox(bbox1, bbox2, loc1, loc2=None):
        """
        Construct a `.Path` connecting corner *loc1* of *bbox1* to corner
        *loc2* of *bbox2*, where parameters behave as documented as for the
        `.BboxConnector` constructor.
        """
        if isinstance(bbox1, Rectangle):
            bbox1 = TransformedBbox(Bbox.unit(), bbox1.get_transform())
        if isinstance(bbox2, Rectangle):
            bbox2 = TransformedBbox(Bbox.unit(), bbox2.get_transform())
        if loc2 is None:
            loc2 = loc1
        x1, y1 = BboxConnector.get_bbox_edge_pos(bbox1, loc1)
        x2, y2 = BboxConnector.get_bbox_edge_pos(bbox2, loc2)
        return Path([[x1, y1], [x2, y2]])

    @_docstring.interpd
    def __init__(self, bbox1, bbox2, loc1, loc2=None, **kwargs):
        """
        Connect two bboxes with a straight line.

        Parameters
        ----------
        bbox1, bbox2 : `~matplotlib.transforms.Bbox`
            Bounding boxes to connect.

        loc1, loc2 : {1, 2, 3, 4}
            Corner of *bbox1* and *bbox2* to draw the line. Valid values are::

                'upper right'  : 1,
                'upper left'   : 2,
                'lower left'   : 3,
                'lower right'  : 4

            *loc2* is optional and defaults to *loc1*.

        **kwargs
            Patch properties for the line drawn. Valid arguments include:

            %(Patch:kwdoc)s
        """
        if "transform" in kwargs:
            raise ValueError("transform should not be set")

        kwargs["transform"] = IdentityTransform()
        kwargs.setdefault(
            "fill", bool({'fc', 'facecolor', 'color'}.intersection(kwargs)))
        super().__init__(**kwargs)
        self.bbox1 = bbox1
        self.bbox2 = bbox2
        self.loc1 = loc1
        self.loc2 = loc2

    def get_path(self):
        # docstring inherited
        return self.connect_bbox(self.bbox1, self.bbox2,
                                 self.loc1, self.loc2)


class BboxConnectorPatch(BboxConnector):
    @_docstring.interpd
    def __init__(self, bbox1, bbox2, loc1a, loc2a, loc1b, loc2b, **kwargs):
        """
        Connect two bboxes with a quadrilateral.

        The quadrilateral is specified by two lines that start and end at
        corners of the bboxes. The four sides of the quadrilateral are defined
        by the two lines given, the line between the two corners specified in
        *bbox1* and the line between the two corners specified in *bbox2*.

        Parameters
        ----------
        bbox1, bbox2 : `~matplotlib.transforms.Bbox`
            Bounding boxes to connect.

        loc1a, loc2a, loc1b, loc2b : {1, 2, 3, 4}
            The first line connects corners *loc1a* of *bbox1* and *loc2a* of
            *bbox2*; the second line connects corners *loc1b* of *bbox1* and
            *loc2b* of *bbox2*.  Valid values are::

                'upper right'  : 1,
                'upper left'   : 2,
                'lower left'   : 3,
                'lower right'  : 4

        **kwargs
            Patch properties for the line drawn:

            %(Patch:kwdoc)s
        """
        if "transform" in kwargs:
            raise ValueError("transform should not be set")
        super().__init__(bbox1, bbox2, loc1a, loc2a, **kwargs)
        self.loc1b = loc1b
        self.loc2b = loc2b

    def get_path(self):
        # docstring inherited
        path1 = self.connect_bbox(self.bbox1, self.bbox2, self.loc1, self.loc2)
        path2 = self.connect_bbox(self.bbox2, self.bbox1,
                                  self.loc2b, self.loc1b)
        path_merged = [*path1.vertices, *path2.vertices, path1.vertices[0]]
        return Path(path_merged)


def _add_inset_axes(parent_axes, axes_class, axes_kwargs, axes_locator):
    """Helper function to add an inset axes and disable navigation in it."""
    if axes_class is None:
        axes_class = HostAxes
    if axes_kwargs is None:
        axes_kwargs = {}
    fig = parent_axes.get_figure(root=False)
    inset_axes = axes_class(
        fig, parent_axes.get_position(),
        **{"navigate": False, **axes_kwargs, "axes_locator": axes_locator})
    return fig.add_axes(inset_axes)


@_docstring.interpd
def inset_axes(parent_axes, width, height, loc='upper right',
               bbox_to_anchor=None, bbox_transform=None,
               axes_class=None, axes_kwargs=None,
               borderpad=0.5):
    """
    Create an inset axes with a given width and height.

    Both sizes used can be specified either in inches or percentage.
    For example,::

        inset_axes(parent_axes, width='40%%', height='30%%', loc='lower left')

    creates in inset axes in the lower left corner of *parent_axes* which spans
    over 30%% in height and 40%% in width of the *parent_axes*. Since the usage
    of `.inset_axes` may become slightly tricky when exceeding such standard
    cases, it is recommended to read :doc:`the examples
    </gallery/axes_grid1/inset_locator_demo>`.

    Notes
    -----
    The meaning of *bbox_to_anchor* and *bbox_to_transform* is interpreted
    differently from that of legend. The value of bbox_to_anchor
    (or the return value of its get_points method; the default is
    *parent_axes.bbox*) is transformed by the bbox_transform (the default
    is Identity transform) and then interpreted as points in the pixel
    coordinate (which is dpi dependent).

    Thus, following three calls are identical and creates an inset axes
    with respect to the *parent_axes*::

       axins = inset_axes(parent_axes, "30%%", "40%%")
       axins = inset_axes(parent_axes, "30%%", "40%%",
                          bbox_to_anchor=parent_axes.bbox)
       axins = inset_axes(parent_axes, "30%%", "40%%",
                          bbox_to_anchor=(0, 0, 1, 1),
                          bbox_transform=parent_axes.transAxes)

    Parameters
    ----------
    parent_axes : `matplotlib.axes.Axes`
        Axes to place the inset axes.

    width, height : float or str
        Size of the inset axes to create. If a float is provided, it is
        the size in inches, e.g. *width=1.3*. If a string is provided, it is
        the size in relative units, e.g. *width='40%%'*. By default, i.e. if
        neither *bbox_to_anchor* nor *bbox_transform* are specified, those
        are relative to the parent_axes. Otherwise, they are to be understood
        relative to the bounding box provided via *bbox_to_anchor*.

    loc : str, default: 'upper right'
        Location to place the inset axes.  Valid locations are
        'upper left', 'upper center', 'upper right',
        'center left', 'center', 'center right',
        'lower left', 'lower center', 'lower right'.
        For backward compatibility, numeric values are accepted as well.
        See the parameter *loc* of `.Legend` for details.

    bbox_to_anchor : tuple or `~matplotlib.transforms.BboxBase`, optional
        Bbox that the inset axes will be anchored to. If None,
        a tuple of (0, 0, 1, 1) is used if *bbox_transform* is set
        to *parent_axes.transAxes* or *parent_axes.figure.transFigure*.
        Otherwise, *parent_axes.bbox* is used. If a tuple, can be either
        [left, bottom, width, height], or [left, bottom].
        If the kwargs *width* and/or *height* are specified in relative units,
        the 2-tuple [left, bottom] cannot be used. Note that,
        unless *bbox_transform* is set, the units of the bounding box
        are interpreted in the pixel coordinate. When using *bbox_to_anchor*
        with tuple, it almost always makes sense to also specify
        a *bbox_transform*. This might often be the axes transform
        *parent_axes.transAxes*.

    bbox_transform : `~matplotlib.transforms.Transform`, optional
        Transformation for the bbox that contains the inset axes.
        If None, a `.transforms.IdentityTransform` is used. The value
        of *bbox_to_anchor* (or the return value of its get_points method)
        is transformed by the *bbox_transform* and then interpreted
        as points in the pixel coordinate (which is dpi dependent).
        You may provide *bbox_to_anchor* in some normalized coordinate,
        and give an appropriate transform (e.g., *parent_axes.transAxes*).

    axes_class : `~matplotlib.axes.Axes` type, default: `.HostAxes`
        The type of the newly created inset axes.

    axes_kwargs : dict, optional
        Keyword arguments to pass to the constructor of the inset axes.
        Valid arguments include:

        %(Axes:kwdoc)s

    borderpad : float, default: 0.5
        Padding between inset axes and the bbox_to_anchor.
        The units are axes font size, i.e. for a default font size of 10 points
        *borderpad = 0.5* is equivalent to a padding of 5 points.

    Returns
    -------
    inset_axes : *axes_class*
        Inset axes object created.
    """

    if (bbox_transform in [parent_axes.transAxes,
                           parent_axes.get_figure(root=False).transFigure]
            and bbox_to_anchor is None):
        _api.warn_external("Using the axes or figure transform requires a "
                           "bounding box in the respective coordinates. "
                           "Using bbox_to_anchor=(0, 0, 1, 1) now.")
        bbox_to_anchor = (0, 0, 1, 1)
    if bbox_to_anchor is None:
        bbox_to_anchor = parent_axes.bbox
    if (isinstance(bbox_to_anchor, tuple) and
            (isinstance(width, str) or isinstance(height, str))):
        if len(bbox_to_anchor) != 4:
            raise ValueError("Using relative units for width or height "
                             "requires to provide a 4-tuple or a "
                             "`Bbox` instance to `bbox_to_anchor.")
    return _add_inset_axes(
        parent_axes, axes_class, axes_kwargs,
        AnchoredSizeLocator(
            bbox_to_anchor, width, height, loc=loc,
            bbox_transform=bbox_transform, borderpad=borderpad))


@_docstring.interpd
def zoomed_inset_axes(parent_axes, zoom, loc='upper right',
                      bbox_to_anchor=None, bbox_transform=None,
                      axes_class=None, axes_kwargs=None,
                      borderpad=0.5):
    """
    Create an anchored inset axes by scaling a parent axes. For usage, also see
    :doc:`the examples </gallery/axes_grid1/inset_locator_demo2>`.

    Parameters
    ----------
    parent_axes : `~matplotlib.axes.Axes`
        Axes to place the inset axes.

    zoom : float
        Scaling factor of the data axes. *zoom* > 1 will enlarge the
        coordinates (i.e., "zoomed in"), while *zoom* < 1 will shrink the
        coordinates (i.e., "zoomed out").

    loc : str, default: 'upper right'
        Location to place the inset axes.  Valid locations are
        'upper left', 'upper center', 'upper right',
        'center left', 'center', 'center right',
        'lower left', 'lower center', 'lower right'.
        For backward compatibility, numeric values are accepted as well.
        See the parameter *loc* of `.Legend` for details.

    bbox_to_anchor : tuple or `~matplotlib.transforms.BboxBase`, optional
        Bbox that the inset axes will be anchored to. If None,
        *parent_axes.bbox* is used. If a tuple, can be either
        [left, bottom, width, height], or [left, bottom].
        If the kwargs *width* and/or *height* are specified in relative units,
        the 2-tuple [left, bottom] cannot be used. Note that
        the units of the bounding box are determined through the transform
        in use. When using *bbox_to_anchor* it almost always makes sense to
        also specify a *bbox_transform*. This might often be the axes transform
        *parent_axes.transAxes*.

    bbox_transform : `~matplotlib.transforms.Transform`, optional
        Transformation for the bbox that contains the inset axes.
        If None, a `.transforms.IdentityTransform` is used (i.e. pixel
        coordinates). This is useful when not providing any argument to
        *bbox_to_anchor*. When using *bbox_to_anchor* it almost always makes
        sense to also specify a *bbox_transform*. This might often be the
        axes transform *parent_axes.transAxes*. Inversely, when specifying
        the axes- or figure-transform here, be aware that not specifying
        *bbox_to_anchor* will use *parent_axes.bbox*, the units of which are
        in display (pixel) coordinates.

    axes_class : `~matplotlib.axes.Axes` type, default: `.HostAxes`
        The type of the newly created inset axes.

    axes_kwargs : dict, optional
        Keyword arguments to pass to the constructor of the inset axes.
        Valid arguments include:

        %(Axes:kwdoc)s

    borderpad : float, default: 0.5
        Padding between inset axes and the bbox_to_anchor.
        The units are axes font size, i.e. for a default font size of 10 points
        *borderpad = 0.5* is equivalent to a padding of 5 points.

    Returns
    -------
    inset_axes : *axes_class*
        Inset axes object created.
    """

    return _add_inset_axes(
        parent_axes, axes_class, axes_kwargs,
        AnchoredZoomLocator(
            parent_axes, zoom=zoom, loc=loc,
            bbox_to_anchor=bbox_to_anchor, bbox_transform=bbox_transform,
            borderpad=borderpad))


class _TransformedBboxWithCallback(TransformedBbox):
    """
    Variant of `.TransformBbox` which calls *callback* before returning points.

    Used by `.mark_inset` to unstale the parent axes' viewlim as needed.
    """

    def __init__(self, *args, callback, **kwargs):
        super().__init__(*args, **kwargs)
        self._callback = callback

    def get_points(self):
        self._callback()
        return super().get_points()


@_docstring.interpd
def mark_inset(parent_axes, inset_axes, loc1, loc2, **kwargs):
    """
    Draw a box to mark the location of an area represented by an inset axes.

    This function draws a box in *parent_axes* at the bounding box of
    *inset_axes*, and shows a connection with the inset axes by drawing lines
    at the corners, giving a "zoomed in" effect.

    Parameters
    ----------
    parent_axes : `~matplotlib.axes.Axes`
        Axes which contains the area of the inset axes.

    inset_axes : `~matplotlib.axes.Axes`
        The inset axes.

    loc1, loc2 : {1, 2, 3, 4}
        Corners to use for connecting the inset axes and the area in the
        parent axes.

    **kwargs
        Patch properties for the lines and box drawn:

        %(Patch:kwdoc)s

    Returns
    -------
    pp : `~matplotlib.patches.Patch`
        The patch drawn to represent the area of the inset axes.

    p1, p2 : `~matplotlib.patches.Patch`
        The patches connecting two corners of the inset axes and its area.
    """
    rect = _TransformedBboxWithCallback(
        inset_axes.viewLim, parent_axes.transData,
        callback=parent_axes._unstale_viewLim)

    kwargs.setdefault("fill", bool({'fc', 'facecolor', 'color'}.intersection(kwargs)))
    pp = BboxPatch(rect, **kwargs)
    parent_axes.add_patch(pp)

    p1 = BboxConnector(inset_axes.bbox, rect, loc1=loc1, **kwargs)
    inset_axes.add_patch(p1)
    p1.set_clip_on(False)
    p2 = BboxConnector(inset_axes.bbox, rect, loc1=loc2, **kwargs)
    inset_axes.add_patch(p2)
    p2.set_clip_on(False)

    return pp, p1, p2

# === NexusCore/openenv\Lib\site-packages\nltk\corpus\reader\propbank.py ===
# Natural Language Toolkit: PropBank Corpus Reader
#
# Copyright (C) 2001-2024 NLTK Project
# Author: Edward Loper <edloper@gmail.com>
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT

import re
from functools import total_ordering
from xml.etree import ElementTree

from nltk.corpus.reader.api import *
from nltk.corpus.reader.util import *
from nltk.internals import raise_unorderable_types
from nltk.tree import Tree


class PropbankCorpusReader(CorpusReader):
    """
    Corpus reader for the propbank corpus, which augments the Penn
    Treebank with information about the predicate argument structure
    of every verb instance.  The corpus consists of two parts: the
    predicate-argument annotations themselves, and a set of "frameset
    files" which define the argument labels used by the annotations,
    on a per-verb basis.  Each "frameset file" contains one or more
    predicates, such as ``'turn'`` or ``'turn_on'``, each of which is
    divided into coarse-grained word senses called "rolesets".  For
    each "roleset", the frameset file provides descriptions of the
    argument roles, along with examples.
    """

    def __init__(
        self,
        root,
        propfile,
        framefiles="",
        verbsfile=None,
        parse_fileid_xform=None,
        parse_corpus=None,
        encoding="utf8",
    ):
        """
        :param root: The root directory for this corpus.
        :param propfile: The name of the file containing the predicate-
            argument annotations (relative to ``root``).
        :param framefiles: A list or regexp specifying the frameset
            fileids for this corpus.
        :param parse_fileid_xform: A transform that should be applied
            to the fileids in this corpus.  This should be a function
            of one argument (a fileid) that returns a string (the new
            fileid).
        :param parse_corpus: The corpus containing the parse trees
            corresponding to this corpus.  These parse trees are
            necessary to resolve the tree pointers used by propbank.
        """
        # If framefiles is specified as a regexp, expand it.
        if isinstance(framefiles, str):
            framefiles = find_corpus_fileids(root, framefiles)
        framefiles = list(framefiles)
        # Initialize the corpus reader.
        CorpusReader.__init__(self, root, [propfile, verbsfile] + framefiles, encoding)

        # Record our frame fileids & prop file.
        self._propfile = propfile
        self._framefiles = framefiles
        self._verbsfile = verbsfile
        self._parse_fileid_xform = parse_fileid_xform
        self._parse_corpus = parse_corpus

    def instances(self, baseform=None):
        """
        :return: a corpus view that acts as a list of
            ``PropBankInstance`` objects, one for each noun in the corpus.
        """
        kwargs = {}
        if baseform is not None:
            kwargs["instance_filter"] = lambda inst: inst.baseform == baseform
        return StreamBackedCorpusView(
            self.abspath(self._propfile),
            lambda stream: self._read_instance_block(stream, **kwargs),
            encoding=self.encoding(self._propfile),
        )

    def lines(self):
        """
        :return: a corpus view that acts as a list of strings, one for
            each line in the predicate-argument annotation file.
        """
        return StreamBackedCorpusView(
            self.abspath(self._propfile),
            read_line_block,
            encoding=self.encoding(self._propfile),
        )

    def roleset(self, roleset_id):
        """
        :return: the xml description for the given roleset.
        """
        baseform = roleset_id.split(".")[0]
        framefile = "frames/%s.xml" % baseform
        if framefile not in self._framefiles:
            raise ValueError("Frameset file for %s not found" % roleset_id)

        # n.b.: The encoding for XML fileids is specified by the file
        # itself; so we ignore self._encoding here.
        with self.abspath(framefile).open() as fp:
            etree = ElementTree.parse(fp).getroot()
        for roleset in etree.findall("predicate/roleset"):
            if roleset.attrib["id"] == roleset_id:
                return roleset
        raise ValueError(f"Roleset {roleset_id} not found in {framefile}")

    def rolesets(self, baseform=None):
        """
        :return: list of xml descriptions for rolesets.
        """
        if baseform is not None:
            framefile = "frames/%s.xml" % baseform
            if framefile not in self._framefiles:
                raise ValueError("Frameset file for %s not found" % baseform)
            framefiles = [framefile]
        else:
            framefiles = self._framefiles

        rsets = []
        for framefile in framefiles:
            # n.b.: The encoding for XML fileids is specified by the file
            # itself; so we ignore self._encoding here.
            with self.abspath(framefile).open() as fp:
                etree = ElementTree.parse(fp).getroot()
            rsets.append(etree.findall("predicate/roleset"))
        return LazyConcatenation(rsets)

    def verbs(self):
        """
        :return: a corpus view that acts as a list of all verb lemmas
            in this corpus (from the verbs.txt file).
        """
        return StreamBackedCorpusView(
            self.abspath(self._verbsfile),
            read_line_block,
            encoding=self.encoding(self._verbsfile),
        )

    def _read_instance_block(self, stream, instance_filter=lambda inst: True):
        block = []

        # Read 100 at a time.
        for i in range(100):
            line = stream.readline().strip()
            if line:
                inst = PropbankInstance.parse(
                    line, self._parse_fileid_xform, self._parse_corpus
                )
                if instance_filter(inst):
                    block.append(inst)

        return block


######################################################################
# { Propbank Instance & related datatypes
######################################################################


class PropbankInstance:
    def __init__(
        self,
        fileid,
        sentnum,
        wordnum,
        tagger,
        roleset,
        inflection,
        predicate,
        arguments,
        parse_corpus=None,
    ):
        self.fileid = fileid
        """The name of the file containing the parse tree for this
        instance's sentence."""

        self.sentnum = sentnum
        """The sentence number of this sentence within ``fileid``.
        Indexing starts from zero."""

        self.wordnum = wordnum
        """The word number of this instance's predicate within its
        containing sentence.  Word numbers are indexed starting from
        zero, and include traces and other empty parse elements."""

        self.tagger = tagger
        """An identifier for the tagger who tagged this instance; or
        ``'gold'`` if this is an adjuticated instance."""

        self.roleset = roleset
        """The name of the roleset used by this instance's predicate.
        Use ``propbank.roleset() <PropbankCorpusReader.roleset>`` to
        look up information about the roleset."""

        self.inflection = inflection
        """A ``PropbankInflection`` object describing the inflection of
        this instance's predicate."""

        self.predicate = predicate
        """A ``PropbankTreePointer`` indicating the position of this
        instance's predicate within its containing sentence."""

        self.arguments = tuple(arguments)
        """A list of tuples (argloc, argid), specifying the location
        and identifier for each of the predicate's argument in the
        containing sentence.  Argument identifiers are strings such as
        ``'ARG0'`` or ``'ARGM-TMP'``.  This list does *not* contain
        the predicate."""

        self.parse_corpus = parse_corpus
        """A corpus reader for the parse trees corresponding to the
        instances in this propbank corpus."""

    @property
    def baseform(self):
        """The baseform of the predicate."""
        return self.roleset.split(".")[0]

    @property
    def sensenumber(self):
        """The sense number of the predicate."""
        return self.roleset.split(".")[1]

    @property
    def predid(self):
        """Identifier of the predicate."""
        return "rel"

    def __repr__(self):
        return "<PropbankInstance: {}, sent {}, word {}>".format(
            self.fileid,
            self.sentnum,
            self.wordnum,
        )

    def __str__(self):
        s = "{} {} {} {} {} {}".format(
            self.fileid,
            self.sentnum,
            self.wordnum,
            self.tagger,
            self.roleset,
            self.inflection,
        )
        items = self.arguments + ((self.predicate, "rel"),)
        for argloc, argid in sorted(items):
            s += f" {argloc}-{argid}"
        return s

    def _get_tree(self):
        if self.parse_corpus is None:
            return None
        if self.fileid not in self.parse_corpus.fileids():
            return None
        return self.parse_corpus.parsed_sents(self.fileid)[self.sentnum]

    tree = property(
        _get_tree,
        doc="""
        The parse tree corresponding to this instance, or None if
        the corresponding tree is not available.""",
    )

    @staticmethod
    def parse(s, parse_fileid_xform=None, parse_corpus=None):
        pieces = s.split()
        if len(pieces) < 7:
            raise ValueError("Badly formatted propbank line: %r" % s)

        # Divide the line into its basic pieces.
        (fileid, sentnum, wordnum, tagger, roleset, inflection) = pieces[:6]
        rel = [p for p in pieces[6:] if p.endswith("-rel")]
        args = [p for p in pieces[6:] if not p.endswith("-rel")]
        if len(rel) != 1:
            raise ValueError("Badly formatted propbank line: %r" % s)

        # Apply the fileid selector, if any.
        if parse_fileid_xform is not None:
            fileid = parse_fileid_xform(fileid)

        # Convert sentence & word numbers to ints.
        sentnum = int(sentnum)
        wordnum = int(wordnum)

        # Parse the inflection
        inflection = PropbankInflection.parse(inflection)

        # Parse the predicate location.
        predicate = PropbankTreePointer.parse(rel[0][:-4])

        # Parse the arguments.
        arguments = []
        for arg in args:
            argloc, argid = arg.split("-", 1)
            arguments.append((PropbankTreePointer.parse(argloc), argid))

        # Put it all together.
        return PropbankInstance(
            fileid,
            sentnum,
            wordnum,
            tagger,
            roleset,
            inflection,
            predicate,
            arguments,
            parse_corpus,
        )


class PropbankPointer:
    """
    A pointer used by propbank to identify one or more constituents in
    a parse tree.  ``PropbankPointer`` is an abstract base class with
    three concrete subclasses:

      - ``PropbankTreePointer`` is used to point to single constituents.
      - ``PropbankSplitTreePointer`` is used to point to 'split'
        constituents, which consist of a sequence of two or more
        ``PropbankTreePointer`` pointers.
      - ``PropbankChainTreePointer`` is used to point to entire trace
        chains in a tree.  It consists of a sequence of pieces, which
        can be ``PropbankTreePointer`` or ``PropbankSplitTreePointer`` pointers.
    """

    def __init__(self):
        if self.__class__ == PropbankPointer:
            raise NotImplementedError()


class PropbankChainTreePointer(PropbankPointer):
    def __init__(self, pieces):
        self.pieces = pieces
        """A list of the pieces that make up this chain.  Elements may
           be either ``PropbankSplitTreePointer`` or
           ``PropbankTreePointer`` pointers."""

    def __str__(self):
        return "*".join("%s" % p for p in self.pieces)

    def __repr__(self):
        return "<PropbankChainTreePointer: %s>" % self

    def select(self, tree):
        if tree is None:
            raise ValueError("Parse tree not available")
        return Tree("*CHAIN*", [p.select(tree) for p in self.pieces])


class PropbankSplitTreePointer(PropbankPointer):
    def __init__(self, pieces):
        self.pieces = pieces
        """A list of the pieces that make up this chain.  Elements are
           all ``PropbankTreePointer`` pointers."""

    def __str__(self):
        return ",".join("%s" % p for p in self.pieces)

    def __repr__(self):
        return "<PropbankSplitTreePointer: %s>" % self

    def select(self, tree):
        if tree is None:
            raise ValueError("Parse tree not available")
        return Tree("*SPLIT*", [p.select(tree) for p in self.pieces])


@total_ordering
class PropbankTreePointer(PropbankPointer):
    """
    wordnum:height*wordnum:height*...
    wordnum:height,

    """

    def __init__(self, wordnum, height):
        self.wordnum = wordnum
        self.height = height

    @staticmethod
    def parse(s):
        # Deal with chains (xx*yy*zz)
        pieces = s.split("*")
        if len(pieces) > 1:
            return PropbankChainTreePointer(
                [PropbankTreePointer.parse(elt) for elt in pieces]
            )

        # Deal with split args (xx,yy,zz)
        pieces = s.split(",")
        if len(pieces) > 1:
            return PropbankSplitTreePointer(
                [PropbankTreePointer.parse(elt) for elt in pieces]
            )

        # Deal with normal pointers.
        pieces = s.split(":")
        if len(pieces) != 2:
            raise ValueError("bad propbank pointer %r" % s)
        return PropbankTreePointer(int(pieces[0]), int(pieces[1]))

    def __str__(self):
        return f"{self.wordnum}:{self.height}"

    def __repr__(self):
        return "PropbankTreePointer(%d, %d)" % (self.wordnum, self.height)

    def __eq__(self, other):
        while isinstance(other, (PropbankChainTreePointer, PropbankSplitTreePointer)):
            other = other.pieces[0]

        if not isinstance(other, PropbankTreePointer):
            return self is other

        return self.wordnum == other.wordnum and self.height == other.height

    def __ne__(self, other):
        return not self == other

    def __lt__(self, other):
        while isinstance(other, (PropbankChainTreePointer, PropbankSplitTreePointer)):
            other = other.pieces[0]

        if not isinstance(other, PropbankTreePointer):
            return id(self) < id(other)

        return (self.wordnum, -self.height) < (other.wordnum, -other.height)

    def select(self, tree):
        if tree is None:
            raise ValueError("Parse tree not available")
        return tree[self.treepos(tree)]

    def treepos(self, tree):
        """
        Convert this pointer to a standard 'tree position' pointer,
        given that it points to the given tree.
        """
        if tree is None:
            raise ValueError("Parse tree not available")
        stack = [tree]
        treepos = []

        wordnum = 0
        while True:
            # tree node:
            if isinstance(stack[-1], Tree):
                # Select the next child.
                if len(treepos) < len(stack):
                    treepos.append(0)
                else:
                    treepos[-1] += 1
                # Update the stack.
                if treepos[-1] < len(stack[-1]):
                    stack.append(stack[-1][treepos[-1]])
                else:
                    # End of node's child list: pop up a level.
                    stack.pop()
                    treepos.pop()
            # word node:
            else:
                if wordnum == self.wordnum:
                    return tuple(treepos[: len(treepos) - self.height - 1])
                else:
                    wordnum += 1
                    stack.pop()


class PropbankInflection:
    # { Inflection Form
    INFINITIVE = "i"
    GERUND = "g"
    PARTICIPLE = "p"
    FINITE = "v"
    # { Inflection Tense
    FUTURE = "f"
    PAST = "p"
    PRESENT = "n"
    # { Inflection Aspect
    PERFECT = "p"
    PROGRESSIVE = "o"
    PERFECT_AND_PROGRESSIVE = "b"
    # { Inflection Person
    THIRD_PERSON = "3"
    # { Inflection Voice
    ACTIVE = "a"
    PASSIVE = "p"
    # { Inflection
    NONE = "-"
    # }

    def __init__(self, form="-", tense="-", aspect="-", person="-", voice="-"):
        self.form = form
        self.tense = tense
        self.aspect = aspect
        self.person = person
        self.voice = voice

    def __str__(self):
        return self.form + self.tense + self.aspect + self.person + self.voice

    def __repr__(self):
        return "<PropbankInflection: %s>" % self

    _VALIDATE = re.compile(r"[igpv\-][fpn\-][pob\-][3\-][ap\-]$")

    @staticmethod
    def parse(s):
        if not isinstance(s, str):
            raise TypeError("expected a string")
        if len(s) != 5 or not PropbankInflection._VALIDATE.match(s):
            raise ValueError("Bad propbank inflection string %r" % s)
        return PropbankInflection(*s)

# === NexusCore/openenv\Lib\site-packages\pip\_vendor\urllib3\contrib\_securetransport\bindings.py ===
"""
This module uses ctypes to bind a whole bunch of functions and constants from
SecureTransport. The goal here is to provide the low-level API to
SecureTransport. These are essentially the C-level functions and constants, and
they're pretty gross to work with.

This code is a bastardised version of the code found in Will Bond's oscrypto
library. An enormous debt is owed to him for blazing this trail for us. For
that reason, this code should be considered to be covered both by urllib3's
license and by oscrypto's:

    Copyright (c) 2015-2016 Will Bond <will@wbond.net>

    Permission is hereby granted, free of charge, to any person obtaining a
    copy of this software and associated documentation files (the "Software"),
    to deal in the Software without restriction, including without limitation
    the rights to use, copy, modify, merge, publish, distribute, sublicense,
    and/or sell copies of the Software, and to permit persons to whom the
    Software is furnished to do so, subject to the following conditions:

    The above copyright notice and this permission notice shall be included in
    all copies or substantial portions of the Software.

    THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
    IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
    FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
    AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
    LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
    FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
    DEALINGS IN THE SOFTWARE.
"""
from __future__ import absolute_import

import platform
from ctypes import (
    CDLL,
    CFUNCTYPE,
    POINTER,
    c_bool,
    c_byte,
    c_char_p,
    c_int32,
    c_long,
    c_size_t,
    c_uint32,
    c_ulong,
    c_void_p,
)
from ctypes.util import find_library

from ...packages.six import raise_from

if platform.system() != "Darwin":
    raise ImportError("Only macOS is supported")

version = platform.mac_ver()[0]
version_info = tuple(map(int, version.split(".")))
if version_info < (10, 8):
    raise OSError(
        "Only OS X 10.8 and newer are supported, not %s.%s"
        % (version_info[0], version_info[1])
    )


def load_cdll(name, macos10_16_path):
    """Loads a CDLL by name, falling back to known path on 10.16+"""
    try:
        # Big Sur is technically 11 but we use 10.16 due to the Big Sur
        # beta being labeled as 10.16.
        if version_info >= (10, 16):
            path = macos10_16_path
        else:
            path = find_library(name)
        if not path:
            raise OSError  # Caught and reraised as 'ImportError'
        return CDLL(path, use_errno=True)
    except OSError:
        raise_from(ImportError("The library %s failed to load" % name), None)


Security = load_cdll(
    "Security", "/System/Library/Frameworks/Security.framework/Security"
)
CoreFoundation = load_cdll(
    "CoreFoundation",
    "/System/Library/Frameworks/CoreFoundation.framework/CoreFoundation",
)


Boolean = c_bool
CFIndex = c_long
CFStringEncoding = c_uint32
CFData = c_void_p
CFString = c_void_p
CFArray = c_void_p
CFMutableArray = c_void_p
CFDictionary = c_void_p
CFError = c_void_p
CFType = c_void_p
CFTypeID = c_ulong

CFTypeRef = POINTER(CFType)
CFAllocatorRef = c_void_p

OSStatus = c_int32

CFDataRef = POINTER(CFData)
CFStringRef = POINTER(CFString)
CFArrayRef = POINTER(CFArray)
CFMutableArrayRef = POINTER(CFMutableArray)
CFDictionaryRef = POINTER(CFDictionary)
CFArrayCallBacks = c_void_p
CFDictionaryKeyCallBacks = c_void_p
CFDictionaryValueCallBacks = c_void_p

SecCertificateRef = POINTER(c_void_p)
SecExternalFormat = c_uint32
SecExternalItemType = c_uint32
SecIdentityRef = POINTER(c_void_p)
SecItemImportExportFlags = c_uint32
SecItemImportExportKeyParameters = c_void_p
SecKeychainRef = POINTER(c_void_p)
SSLProtocol = c_uint32
SSLCipherSuite = c_uint32
SSLContextRef = POINTER(c_void_p)
SecTrustRef = POINTER(c_void_p)
SSLConnectionRef = c_uint32
SecTrustResultType = c_uint32
SecTrustOptionFlags = c_uint32
SSLProtocolSide = c_uint32
SSLConnectionType = c_uint32
SSLSessionOption = c_uint32


try:
    Security.SecItemImport.argtypes = [
        CFDataRef,
        CFStringRef,
        POINTER(SecExternalFormat),
        POINTER(SecExternalItemType),
        SecItemImportExportFlags,
        POINTER(SecItemImportExportKeyParameters),
        SecKeychainRef,
        POINTER(CFArrayRef),
    ]
    Security.SecItemImport.restype = OSStatus

    Security.SecCertificateGetTypeID.argtypes = []
    Security.SecCertificateGetTypeID.restype = CFTypeID

    Security.SecIdentityGetTypeID.argtypes = []
    Security.SecIdentityGetTypeID.restype = CFTypeID

    Security.SecKeyGetTypeID.argtypes = []
    Security.SecKeyGetTypeID.restype = CFTypeID

    Security.SecCertificateCreateWithData.argtypes = [CFAllocatorRef, CFDataRef]
    Security.SecCertificateCreateWithData.restype = SecCertificateRef

    Security.SecCertificateCopyData.argtypes = [SecCertificateRef]
    Security.SecCertificateCopyData.restype = CFDataRef

    Security.SecCopyErrorMessageString.argtypes = [OSStatus, c_void_p]
    Security.SecCopyErrorMessageString.restype = CFStringRef

    Security.SecIdentityCreateWithCertificate.argtypes = [
        CFTypeRef,
        SecCertificateRef,
        POINTER(SecIdentityRef),
    ]
    Security.SecIdentityCreateWithCertificate.restype = OSStatus

    Security.SecKeychainCreate.argtypes = [
        c_char_p,
        c_uint32,
        c_void_p,
        Boolean,
        c_void_p,
        POINTER(SecKeychainRef),
    ]
    Security.SecKeychainCreate.restype = OSStatus

    Security.SecKeychainDelete.argtypes = [SecKeychainRef]
    Security.SecKeychainDelete.restype = OSStatus

    Security.SecPKCS12Import.argtypes = [
        CFDataRef,
        CFDictionaryRef,
        POINTER(CFArrayRef),
    ]
    Security.SecPKCS12Import.restype = OSStatus

    SSLReadFunc = CFUNCTYPE(OSStatus, SSLConnectionRef, c_void_p, POINTER(c_size_t))
    SSLWriteFunc = CFUNCTYPE(
        OSStatus, SSLConnectionRef, POINTER(c_byte), POINTER(c_size_t)
    )

    Security.SSLSetIOFuncs.argtypes = [SSLContextRef, SSLReadFunc, SSLWriteFunc]
    Security.SSLSetIOFuncs.restype = OSStatus

    Security.SSLSetPeerID.argtypes = [SSLContextRef, c_char_p, c_size_t]
    Security.SSLSetPeerID.restype = OSStatus

    Security.SSLSetCertificate.argtypes = [SSLContextRef, CFArrayRef]
    Security.SSLSetCertificate.restype = OSStatus

    Security.SSLSetCertificateAuthorities.argtypes = [SSLContextRef, CFTypeRef, Boolean]
    Security.SSLSetCertificateAuthorities.restype = OSStatus

    Security.SSLSetConnection.argtypes = [SSLContextRef, SSLConnectionRef]
    Security.SSLSetConnection.restype = OSStatus

    Security.SSLSetPeerDomainName.argtypes = [SSLContextRef, c_char_p, c_size_t]
    Security.SSLSetPeerDomainName.restype = OSStatus

    Security.SSLHandshake.argtypes = [SSLContextRef]
    Security.SSLHandshake.restype = OSStatus

    Security.SSLRead.argtypes = [SSLContextRef, c_char_p, c_size_t, POINTER(c_size_t)]
    Security.SSLRead.restype = OSStatus

    Security.SSLWrite.argtypes = [SSLContextRef, c_char_p, c_size_t, POINTER(c_size_t)]
    Security.SSLWrite.restype = OSStatus

    Security.SSLClose.argtypes = [SSLContextRef]
    Security.SSLClose.restype = OSStatus

    Security.SSLGetNumberSupportedCiphers.argtypes = [SSLContextRef, POINTER(c_size_t)]
    Security.SSLGetNumberSupportedCiphers.restype = OSStatus

    Security.SSLGetSupportedCiphers.argtypes = [
        SSLContextRef,
        POINTER(SSLCipherSuite),
        POINTER(c_size_t),
    ]
    Security.SSLGetSupportedCiphers.restype = OSStatus

    Security.SSLSetEnabledCiphers.argtypes = [
        SSLContextRef,
        POINTER(SSLCipherSuite),
        c_size_t,
    ]
    Security.SSLSetEnabledCiphers.restype = OSStatus

    Security.SSLGetNumberEnabledCiphers.argtype = [SSLContextRef, POINTER(c_size_t)]
    Security.SSLGetNumberEnabledCiphers.restype = OSStatus

    Security.SSLGetEnabledCiphers.argtypes = [
        SSLContextRef,
        POINTER(SSLCipherSuite),
        POINTER(c_size_t),
    ]
    Security.SSLGetEnabledCiphers.restype = OSStatus

    Security.SSLGetNegotiatedCipher.argtypes = [SSLContextRef, POINTER(SSLCipherSuite)]
    Security.SSLGetNegotiatedCipher.restype = OSStatus

    Security.SSLGetNegotiatedProtocolVersion.argtypes = [
        SSLContextRef,
        POINTER(SSLProtocol),
    ]
    Security.SSLGetNegotiatedProtocolVersion.restype = OSStatus

    Security.SSLCopyPeerTrust.argtypes = [SSLContextRef, POINTER(SecTrustRef)]
    Security.SSLCopyPeerTrust.restype = OSStatus

    Security.SecTrustSetAnchorCertificates.argtypes = [SecTrustRef, CFArrayRef]
    Security.SecTrustSetAnchorCertificates.restype = OSStatus

    Security.SecTrustSetAnchorCertificatesOnly.argstypes = [SecTrustRef, Boolean]
    Security.SecTrustSetAnchorCertificatesOnly.restype = OSStatus

    Security.SecTrustEvaluate.argtypes = [SecTrustRef, POINTER(SecTrustResultType)]
    Security.SecTrustEvaluate.restype = OSStatus

    Security.SecTrustGetCertificateCount.argtypes = [SecTrustRef]
    Security.SecTrustGetCertificateCount.restype = CFIndex

    Security.SecTrustGetCertificateAtIndex.argtypes = [SecTrustRef, CFIndex]
    Security.SecTrustGetCertificateAtIndex.restype = SecCertificateRef

    Security.SSLCreateContext.argtypes = [
        CFAllocatorRef,
        SSLProtocolSide,
        SSLConnectionType,
    ]
    Security.SSLCreateContext.restype = SSLContextRef

    Security.SSLSetSessionOption.argtypes = [SSLContextRef, SSLSessionOption, Boolean]
    Security.SSLSetSessionOption.restype = OSStatus

    Security.SSLSetProtocolVersionMin.argtypes = [SSLContextRef, SSLProtocol]
    Security.SSLSetProtocolVersionMin.restype = OSStatus

    Security.SSLSetProtocolVersionMax.argtypes = [SSLContextRef, SSLProtocol]
    Security.SSLSetProtocolVersionMax.restype = OSStatus

    try:
        Security.SSLSetALPNProtocols.argtypes = [SSLContextRef, CFArrayRef]
        Security.SSLSetALPNProtocols.restype = OSStatus
    except AttributeError:
        # Supported only in 10.12+
        pass

    Security.SecCopyErrorMessageString.argtypes = [OSStatus, c_void_p]
    Security.SecCopyErrorMessageString.restype = CFStringRef

    Security.SSLReadFunc = SSLReadFunc
    Security.SSLWriteFunc = SSLWriteFunc
    Security.SSLContextRef = SSLContextRef
    Security.SSLProtocol = SSLProtocol
    Security.SSLCipherSuite = SSLCipherSuite
    Security.SecIdentityRef = SecIdentityRef
    Security.SecKeychainRef = SecKeychainRef
    Security.SecTrustRef = SecTrustRef
    Security.SecTrustResultType = SecTrustResultType
    Security.SecExternalFormat = SecExternalFormat
    Security.OSStatus = OSStatus

    Security.kSecImportExportPassphrase = CFStringRef.in_dll(
        Security, "kSecImportExportPassphrase"
    )
    Security.kSecImportItemIdentity = CFStringRef.in_dll(
        Security, "kSecImportItemIdentity"
    )

    # CoreFoundation time!
    CoreFoundation.CFRetain.argtypes = [CFTypeRef]
    CoreFoundation.CFRetain.restype = CFTypeRef

    CoreFoundation.CFRelease.argtypes = [CFTypeRef]
    CoreFoundation.CFRelease.restype = None

    CoreFoundation.CFGetTypeID.argtypes = [CFTypeRef]
    CoreFoundation.CFGetTypeID.restype = CFTypeID

    CoreFoundation.CFStringCreateWithCString.argtypes = [
        CFAllocatorRef,
        c_char_p,
        CFStringEncoding,
    ]
    CoreFoundation.CFStringCreateWithCString.restype = CFStringRef

    CoreFoundation.CFStringGetCStringPtr.argtypes = [CFStringRef, CFStringEncoding]
    CoreFoundation.CFStringGetCStringPtr.restype = c_char_p

    CoreFoundation.CFStringGetCString.argtypes = [
        CFStringRef,
        c_char_p,
        CFIndex,
        CFStringEncoding,
    ]
    CoreFoundation.CFStringGetCString.restype = c_bool

    CoreFoundation.CFDataCreate.argtypes = [CFAllocatorRef, c_char_p, CFIndex]
    CoreFoundation.CFDataCreate.restype = CFDataRef

    CoreFoundation.CFDataGetLength.argtypes = [CFDataRef]
    CoreFoundation.CFDataGetLength.restype = CFIndex

    CoreFoundation.CFDataGetBytePtr.argtypes = [CFDataRef]
    CoreFoundation.CFDataGetBytePtr.restype = c_void_p

    CoreFoundation.CFDictionaryCreate.argtypes = [
        CFAllocatorRef,
        POINTER(CFTypeRef),
        POINTER(CFTypeRef),
        CFIndex,
        CFDictionaryKeyCallBacks,
        CFDictionaryValueCallBacks,
    ]
    CoreFoundation.CFDictionaryCreate.restype = CFDictionaryRef

    CoreFoundation.CFDictionaryGetValue.argtypes = [CFDictionaryRef, CFTypeRef]
    CoreFoundation.CFDictionaryGetValue.restype = CFTypeRef

    CoreFoundation.CFArrayCreate.argtypes = [
        CFAllocatorRef,
        POINTER(CFTypeRef),
        CFIndex,
        CFArrayCallBacks,
    ]
    CoreFoundation.CFArrayCreate.restype = CFArrayRef

    CoreFoundation.CFArrayCreateMutable.argtypes = [
        CFAllocatorRef,
        CFIndex,
        CFArrayCallBacks,
    ]
    CoreFoundation.CFArrayCreateMutable.restype = CFMutableArrayRef

    CoreFoundation.CFArrayAppendValue.argtypes = [CFMutableArrayRef, c_void_p]
    CoreFoundation.CFArrayAppendValue.restype = None

    CoreFoundation.CFArrayGetCount.argtypes = [CFArrayRef]
    CoreFoundation.CFArrayGetCount.restype = CFIndex

    CoreFoundation.CFArrayGetValueAtIndex.argtypes = [CFArrayRef, CFIndex]
    CoreFoundation.CFArrayGetValueAtIndex.restype = c_void_p

    CoreFoundation.kCFAllocatorDefault = CFAllocatorRef.in_dll(
        CoreFoundation, "kCFAllocatorDefault"
    )
    CoreFoundation.kCFTypeArrayCallBacks = c_void_p.in_dll(
        CoreFoundation, "kCFTypeArrayCallBacks"
    )
    CoreFoundation.kCFTypeDictionaryKeyCallBacks = c_void_p.in_dll(
        CoreFoundation, "kCFTypeDictionaryKeyCallBacks"
    )
    CoreFoundation.kCFTypeDictionaryValueCallBacks = c_void_p.in_dll(
        CoreFoundation, "kCFTypeDictionaryValueCallBacks"
    )

    CoreFoundation.CFTypeRef = CFTypeRef
    CoreFoundation.CFArrayRef = CFArrayRef
    CoreFoundation.CFStringRef = CFStringRef
    CoreFoundation.CFDictionaryRef = CFDictionaryRef

except (AttributeError):
    raise ImportError("Error initializing ctypes")


class CFConst(object):
    """
    A class object that acts as essentially a namespace for CoreFoundation
    constants.
    """

    kCFStringEncodingUTF8 = CFStringEncoding(0x08000100)


class SecurityConst(object):
    """
    A class object that acts as essentially a namespace for Security constants.
    """

    kSSLSessionOptionBreakOnServerAuth = 0

    kSSLProtocol2 = 1
    kSSLProtocol3 = 2
    kTLSProtocol1 = 4
    kTLSProtocol11 = 7
    kTLSProtocol12 = 8
    # SecureTransport does not support TLS 1.3 even if there's a constant for it
    kTLSProtocol13 = 10
    kTLSProtocolMaxSupported = 999

    kSSLClientSide = 1
    kSSLStreamType = 0

    kSecFormatPEMSequence = 10

    kSecTrustResultInvalid = 0
    kSecTrustResultProceed = 1
    # This gap is present on purpose: this was kSecTrustResultConfirm, which
    # is deprecated.
    kSecTrustResultDeny = 3
    kSecTrustResultUnspecified = 4
    kSecTrustResultRecoverableTrustFailure = 5
    kSecTrustResultFatalTrustFailure = 6
    kSecTrustResultOtherError = 7

    errSSLProtocol = -9800
    errSSLWouldBlock = -9803
    errSSLClosedGraceful = -9805
    errSSLClosedNoNotify = -9816
    errSSLClosedAbort = -9806

    errSSLXCertChainInvalid = -9807
    errSSLCrypto = -9809
    errSSLInternal = -9810
    errSSLCertExpired = -9814
    errSSLCertNotYetValid = -9815
    errSSLUnknownRootCert = -9812
    errSSLNoRootCert = -9813
    errSSLHostNameMismatch = -9843
    errSSLPeerHandshakeFail = -9824
    errSSLPeerUserCancelled = -9839
    errSSLWeakPeerEphemeralDHKey = -9850
    errSSLServerAuthCompleted = -9841
    errSSLRecordOverflow = -9847

    errSecVerifyFailed = -67808
    errSecNoTrustSettings = -25263
    errSecItemNotFound = -25300
    errSecInvalidTrustSettings = -25262

    # Cipher suites. We only pick the ones our default cipher string allows.
    # Source: https://developer.apple.com/documentation/security/1550981-ssl_cipher_suite_values
    TLS_ECDHE_ECDSA_WITH_AES_256_GCM_SHA384 = 0xC02C
    TLS_ECDHE_RSA_WITH_AES_256_GCM_SHA384 = 0xC030
    TLS_ECDHE_ECDSA_WITH_AES_128_GCM_SHA256 = 0xC02B
    TLS_ECDHE_RSA_WITH_AES_128_GCM_SHA256 = 0xC02F
    TLS_ECDHE_ECDSA_WITH_CHACHA20_POLY1305_SHA256 = 0xCCA9
    TLS_ECDHE_RSA_WITH_CHACHA20_POLY1305_SHA256 = 0xCCA8
    TLS_DHE_RSA_WITH_AES_256_GCM_SHA384 = 0x009F
    TLS_DHE_RSA_WITH_AES_128_GCM_SHA256 = 0x009E
    TLS_ECDHE_ECDSA_WITH_AES_256_CBC_SHA384 = 0xC024
    TLS_ECDHE_RSA_WITH_AES_256_CBC_SHA384 = 0xC028
    TLS_ECDHE_ECDSA_WITH_AES_256_CBC_SHA = 0xC00A
    TLS_ECDHE_RSA_WITH_AES_256_CBC_SHA = 0xC014
    TLS_DHE_RSA_WITH_AES_256_CBC_SHA256 = 0x006B
    TLS_DHE_RSA_WITH_AES_256_CBC_SHA = 0x0039
    TLS_ECDHE_ECDSA_WITH_AES_128_CBC_SHA256 = 0xC023
    TLS_ECDHE_RSA_WITH_AES_128_CBC_SHA256 = 0xC027
    TLS_ECDHE_ECDSA_WITH_AES_128_CBC_SHA = 0xC009
    TLS_ECDHE_RSA_WITH_AES_128_CBC_SHA = 0xC013
    TLS_DHE_RSA_WITH_AES_128_CBC_SHA256 = 0x0067
    TLS_DHE_RSA_WITH_AES_128_CBC_SHA = 0x0033
    TLS_RSA_WITH_AES_256_GCM_SHA384 = 0x009D
    TLS_RSA_WITH_AES_128_GCM_SHA256 = 0x009C
    TLS_RSA_WITH_AES_256_CBC_SHA256 = 0x003D
    TLS_RSA_WITH_AES_128_CBC_SHA256 = 0x003C
    TLS_RSA_WITH_AES_256_CBC_SHA = 0x0035
    TLS_RSA_WITH_AES_128_CBC_SHA = 0x002F
    TLS_AES_128_GCM_SHA256 = 0x1301
    TLS_AES_256_GCM_SHA384 = 0x1302
    TLS_AES_128_CCM_8_SHA256 = 0x1305
    TLS_AES_128_CCM_SHA256 = 0x1304

# === NexusCore/myenv\Lib\site-packages\pip\_vendor\pygments\formatters\latex.py ===
"""
    pygments.formatters.latex
    ~~~~~~~~~~~~~~~~~~~~~~~~~

    Formatter for LaTeX fancyvrb output.

    :copyright: Copyright 2006-2024 by the Pygments team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

from io import StringIO

from pip._vendor.pygments.formatter import Formatter
from pip._vendor.pygments.lexer import Lexer, do_insertions
from pip._vendor.pygments.token import Token, STANDARD_TYPES
from pip._vendor.pygments.util import get_bool_opt, get_int_opt


__all__ = ['LatexFormatter']


def escape_tex(text, commandprefix):
    return text.replace('\\', '\x00'). \
                replace('{', '\x01'). \
                replace('}', '\x02'). \
                replace('\x00', rf'\{commandprefix}Zbs{{}}'). \
                replace('\x01', rf'\{commandprefix}Zob{{}}'). \
                replace('\x02', rf'\{commandprefix}Zcb{{}}'). \
                replace('^', rf'\{commandprefix}Zca{{}}'). \
                replace('_', rf'\{commandprefix}Zus{{}}'). \
                replace('&', rf'\{commandprefix}Zam{{}}'). \
                replace('<', rf'\{commandprefix}Zlt{{}}'). \
                replace('>', rf'\{commandprefix}Zgt{{}}'). \
                replace('#', rf'\{commandprefix}Zsh{{}}'). \
                replace('%', rf'\{commandprefix}Zpc{{}}'). \
                replace('$', rf'\{commandprefix}Zdl{{}}'). \
                replace('-', rf'\{commandprefix}Zhy{{}}'). \
                replace("'", rf'\{commandprefix}Zsq{{}}'). \
                replace('"', rf'\{commandprefix}Zdq{{}}'). \
                replace('~', rf'\{commandprefix}Zti{{}}')


DOC_TEMPLATE = r'''
\documentclass{%(docclass)s}
\usepackage{fancyvrb}
\usepackage{color}
\usepackage[%(encoding)s]{inputenc}
%(preamble)s

%(styledefs)s

\begin{document}

\section*{%(title)s}

%(code)s
\end{document}
'''

## Small explanation of the mess below :)
#
# The previous version of the LaTeX formatter just assigned a command to
# each token type defined in the current style.  That obviously is
# problematic if the highlighted code is produced for a different style
# than the style commands themselves.
#
# This version works much like the HTML formatter which assigns multiple
# CSS classes to each <span> tag, from the most specific to the least
# specific token type, thus falling back to the parent token type if one
# is not defined.  Here, the classes are there too and use the same short
# forms given in token.STANDARD_TYPES.
#
# Highlighted code now only uses one custom command, which by default is
# \PY and selectable by the commandprefix option (and in addition the
# escapes \PYZat, \PYZlb and \PYZrb which haven't been renamed for
# backwards compatibility purposes).
#
# \PY has two arguments: the classes, separated by +, and the text to
# render in that style.  The classes are resolved into the respective
# style commands by magic, which serves to ignore unknown classes.
#
# The magic macros are:
# * \PY@it, \PY@bf, etc. are unconditionally wrapped around the text
#   to render in \PY@do.  Their definition determines the style.
# * \PY@reset resets \PY@it etc. to do nothing.
# * \PY@toks parses the list of classes, using magic inspired by the
#   keyval package (but modified to use plusses instead of commas
#   because fancyvrb redefines commas inside its environments).
# * \PY@tok processes one class, calling the \PY@tok@classname command
#   if it exists.
# * \PY@tok@classname sets the \PY@it etc. to reflect the chosen style
#   for its class.
# * \PY resets the style, parses the classnames and then calls \PY@do.
#
# Tip: to read this code, print it out in substituted form using e.g.
# >>> print STYLE_TEMPLATE % {'cp': 'PY'}

STYLE_TEMPLATE = r'''
\makeatletter
\def\%(cp)s@reset{\let\%(cp)s@it=\relax \let\%(cp)s@bf=\relax%%
    \let\%(cp)s@ul=\relax \let\%(cp)s@tc=\relax%%
    \let\%(cp)s@bc=\relax \let\%(cp)s@ff=\relax}
\def\%(cp)s@tok#1{\csname %(cp)s@tok@#1\endcsname}
\def\%(cp)s@toks#1+{\ifx\relax#1\empty\else%%
    \%(cp)s@tok{#1}\expandafter\%(cp)s@toks\fi}
\def\%(cp)s@do#1{\%(cp)s@bc{\%(cp)s@tc{\%(cp)s@ul{%%
    \%(cp)s@it{\%(cp)s@bf{\%(cp)s@ff{#1}}}}}}}
\def\%(cp)s#1#2{\%(cp)s@reset\%(cp)s@toks#1+\relax+\%(cp)s@do{#2}}

%(styles)s

\def\%(cp)sZbs{\char`\\}
\def\%(cp)sZus{\char`\_}
\def\%(cp)sZob{\char`\{}
\def\%(cp)sZcb{\char`\}}
\def\%(cp)sZca{\char`\^}
\def\%(cp)sZam{\char`\&}
\def\%(cp)sZlt{\char`\<}
\def\%(cp)sZgt{\char`\>}
\def\%(cp)sZsh{\char`\#}
\def\%(cp)sZpc{\char`\%%}
\def\%(cp)sZdl{\char`\$}
\def\%(cp)sZhy{\char`\-}
\def\%(cp)sZsq{\char`\'}
\def\%(cp)sZdq{\char`\"}
\def\%(cp)sZti{\char`\~}
%% for compatibility with earlier versions
\def\%(cp)sZat{@}
\def\%(cp)sZlb{[}
\def\%(cp)sZrb{]}
\makeatother
'''


def _get_ttype_name(ttype):
    fname = STANDARD_TYPES.get(ttype)
    if fname:
        return fname
    aname = ''
    while fname is None:
        aname = ttype[-1] + aname
        ttype = ttype.parent
        fname = STANDARD_TYPES.get(ttype)
    return fname + aname


class LatexFormatter(Formatter):
    r"""
    Format tokens as LaTeX code. This needs the `fancyvrb` and `color`
    standard packages.

    Without the `full` option, code is formatted as one ``Verbatim``
    environment, like this:

    .. sourcecode:: latex

        \begin{Verbatim}[commandchars=\\\{\}]
        \PY{k}{def }\PY{n+nf}{foo}(\PY{n}{bar}):
            \PY{k}{pass}
        \end{Verbatim}

    Wrapping can be disabled using the `nowrap` option.

    The special command used here (``\PY``) and all the other macros it needs
    are output by the `get_style_defs` method.

    With the `full` option, a complete LaTeX document is output, including
    the command definitions in the preamble.

    The `get_style_defs()` method of a `LatexFormatter` returns a string
    containing ``\def`` commands defining the macros needed inside the
    ``Verbatim`` environments.

    Additional options accepted:

    `nowrap`
        If set to ``True``, don't wrap the tokens at all, not even inside a
        ``\begin{Verbatim}`` environment. This disables most other options
        (default: ``False``).

    `style`
        The style to use, can be a string or a Style subclass (default:
        ``'default'``).

    `full`
        Tells the formatter to output a "full" document, i.e. a complete
        self-contained document (default: ``False``).

    `title`
        If `full` is true, the title that should be used to caption the
        document (default: ``''``).

    `docclass`
        If the `full` option is enabled, this is the document class to use
        (default: ``'article'``).

    `preamble`
        If the `full` option is enabled, this can be further preamble commands,
        e.g. ``\usepackage`` (default: ``''``).

    `linenos`
        If set to ``True``, output line numbers (default: ``False``).

    `linenostart`
        The line number for the first line (default: ``1``).

    `linenostep`
        If set to a number n > 1, only every nth line number is printed.

    `verboptions`
        Additional options given to the Verbatim environment (see the *fancyvrb*
        docs for possible values) (default: ``''``).

    `commandprefix`
        The LaTeX commands used to produce colored output are constructed
        using this prefix and some letters (default: ``'PY'``).

        .. versionadded:: 0.7
        .. versionchanged:: 0.10
           The default is now ``'PY'`` instead of ``'C'``.

    `texcomments`
        If set to ``True``, enables LaTeX comment lines.  That is, LaTex markup
        in comment tokens is not escaped so that LaTeX can render it (default:
        ``False``).

        .. versionadded:: 1.2

    `mathescape`
        If set to ``True``, enables LaTeX math mode escape in comments. That
        is, ``'$...$'`` inside a comment will trigger math mode (default:
        ``False``).

        .. versionadded:: 1.2

    `escapeinside`
        If set to a string of length 2, enables escaping to LaTeX. Text
        delimited by these 2 characters is read as LaTeX code and
        typeset accordingly. It has no effect in string literals. It has
        no effect in comments if `texcomments` or `mathescape` is
        set. (default: ``''``).

        .. versionadded:: 2.0

    `envname`
        Allows you to pick an alternative environment name replacing Verbatim.
        The alternate environment still has to support Verbatim's option syntax.
        (default: ``'Verbatim'``).

        .. versionadded:: 2.0
    """
    name = 'LaTeX'
    aliases = ['latex', 'tex']
    filenames = ['*.tex']

    def __init__(self, **options):
        Formatter.__init__(self, **options)
        self.nowrap = get_bool_opt(options, 'nowrap', False)
        self.docclass = options.get('docclass', 'article')
        self.preamble = options.get('preamble', '')
        self.linenos = get_bool_opt(options, 'linenos', False)
        self.linenostart = abs(get_int_opt(options, 'linenostart', 1))
        self.linenostep = abs(get_int_opt(options, 'linenostep', 1))
        self.verboptions = options.get('verboptions', '')
        self.nobackground = get_bool_opt(options, 'nobackground', False)
        self.commandprefix = options.get('commandprefix', 'PY')
        self.texcomments = get_bool_opt(options, 'texcomments', False)
        self.mathescape = get_bool_opt(options, 'mathescape', False)
        self.escapeinside = options.get('escapeinside', '')
        if len(self.escapeinside) == 2:
            self.left = self.escapeinside[0]
            self.right = self.escapeinside[1]
        else:
            self.escapeinside = ''
        self.envname = options.get('envname', 'Verbatim')

        self._create_stylesheet()

    def _create_stylesheet(self):
        t2n = self.ttype2name = {Token: ''}
        c2d = self.cmd2def = {}
        cp = self.commandprefix

        def rgbcolor(col):
            if col:
                return ','.join(['%.2f' % (int(col[i] + col[i + 1], 16) / 255.0)
                                 for i in (0, 2, 4)])
            else:
                return '1,1,1'

        for ttype, ndef in self.style:
            name = _get_ttype_name(ttype)
            cmndef = ''
            if ndef['bold']:
                cmndef += r'\let\$$@bf=\textbf'
            if ndef['italic']:
                cmndef += r'\let\$$@it=\textit'
            if ndef['underline']:
                cmndef += r'\let\$$@ul=\underline'
            if ndef['roman']:
                cmndef += r'\let\$$@ff=\textrm'
            if ndef['sans']:
                cmndef += r'\let\$$@ff=\textsf'
            if ndef['mono']:
                cmndef += r'\let\$$@ff=\textsf'
            if ndef['color']:
                cmndef += (r'\def\$$@tc##1{{\textcolor[rgb]{{{}}}{{##1}}}}'.format(rgbcolor(ndef['color'])))
            if ndef['border']:
                cmndef += (r'\def\$$@bc##1{{{{\setlength{{\fboxsep}}{{\string -\fboxrule}}'
                           r'\fcolorbox[rgb]{{{}}}{{{}}}{{\strut ##1}}}}}}'.format(rgbcolor(ndef['border']),
                            rgbcolor(ndef['bgcolor'])))
            elif ndef['bgcolor']:
                cmndef += (r'\def\$$@bc##1{{{{\setlength{{\fboxsep}}{{0pt}}'
                           r'\colorbox[rgb]{{{}}}{{\strut ##1}}}}}}'.format(rgbcolor(ndef['bgcolor'])))
            if cmndef == '':
                continue
            cmndef = cmndef.replace('$$', cp)
            t2n[ttype] = name
            c2d[name] = cmndef

    def get_style_defs(self, arg=''):
        """
        Return the command sequences needed to define the commands
        used to format text in the verbatim environment. ``arg`` is ignored.
        """
        cp = self.commandprefix
        styles = []
        for name, definition in self.cmd2def.items():
            styles.append(rf'\@namedef{{{cp}@tok@{name}}}{{{definition}}}')
        return STYLE_TEMPLATE % {'cp': self.commandprefix,
                                 'styles': '\n'.join(styles)}

    def format_unencoded(self, tokensource, outfile):
        # TODO: add support for background colors
        t2n = self.ttype2name
        cp = self.commandprefix

        if self.full:
            realoutfile = outfile
            outfile = StringIO()

        if not self.nowrap:
            outfile.write('\\begin{' + self.envname + '}[commandchars=\\\\\\{\\}')
            if self.linenos:
                start, step = self.linenostart, self.linenostep
                outfile.write(',numbers=left' +
                              (start and ',firstnumber=%d' % start or '') +
                              (step and ',stepnumber=%d' % step or ''))
            if self.mathescape or self.texcomments or self.escapeinside:
                outfile.write(',codes={\\catcode`\\$=3\\catcode`\\^=7'
                              '\\catcode`\\_=8\\relax}')
            if self.verboptions:
                outfile.write(',' + self.verboptions)
            outfile.write(']\n')

        for ttype, value in tokensource:
            if ttype in Token.Comment:
                if self.texcomments:
                    # Try to guess comment starting lexeme and escape it ...
                    start = value[0:1]
                    for i in range(1, len(value)):
                        if start[0] != value[i]:
                            break
                        start += value[i]

                    value = value[len(start):]
                    start = escape_tex(start, cp)

                    # ... but do not escape inside comment.
                    value = start + value
                elif self.mathescape:
                    # Only escape parts not inside a math environment.
                    parts = value.split('$')
                    in_math = False
                    for i, part in enumerate(parts):
                        if not in_math:
                            parts[i] = escape_tex(part, cp)
                        in_math = not in_math
                    value = '$'.join(parts)
                elif self.escapeinside:
                    text = value
                    value = ''
                    while text:
                        a, sep1, text = text.partition(self.left)
                        if sep1:
                            b, sep2, text = text.partition(self.right)
                            if sep2:
                                value += escape_tex(a, cp) + b
                            else:
                                value += escape_tex(a + sep1 + b, cp)
                        else:
                            value += escape_tex(a, cp)
                else:
                    value = escape_tex(value, cp)
            elif ttype not in Token.Escape:
                value = escape_tex(value, cp)
            styles = []
            while ttype is not Token:
                try:
                    styles.append(t2n[ttype])
                except KeyError:
                    # not in current style
                    styles.append(_get_ttype_name(ttype))
                ttype = ttype.parent
            styleval = '+'.join(reversed(styles))
            if styleval:
                spl = value.split('\n')
                for line in spl[:-1]:
                    if line:
                        outfile.write(f"\\{cp}{{{styleval}}}{{{line}}}")
                    outfile.write('\n')
                if spl[-1]:
                    outfile.write(f"\\{cp}{{{styleval}}}{{{spl[-1]}}}")
            else:
                outfile.write(value)

        if not self.nowrap:
            outfile.write('\\end{' + self.envname + '}\n')

        if self.full:
            encoding = self.encoding or 'utf8'
            # map known existings encodings from LaTeX distribution
            encoding = {
                'utf_8': 'utf8',
                'latin_1': 'latin1',
                'iso_8859_1': 'latin1',
            }.get(encoding.replace('-', '_'), encoding)
            realoutfile.write(DOC_TEMPLATE %
                dict(docclass  = self.docclass,
                     preamble  = self.preamble,
                     title     = self.title,
                     encoding  = encoding,
                     styledefs = self.get_style_defs(),
                     code      = outfile.getvalue()))


class LatexEmbeddedLexer(Lexer):
    """
    This lexer takes one lexer as argument, the lexer for the language
    being formatted, and the left and right delimiters for escaped text.

    First everything is scanned using the language lexer to obtain
    strings and comments. All other consecutive tokens are merged and
    the resulting text is scanned for escaped segments, which are given
    the Token.Escape type. Finally text that is not escaped is scanned
    again with the language lexer.
    """
    def __init__(self, left, right, lang, **options):
        self.left = left
        self.right = right
        self.lang = lang
        Lexer.__init__(self, **options)

    def get_tokens_unprocessed(self, text):
        # find and remove all the escape tokens (replace with an empty string)
        # this is very similar to DelegatingLexer.get_tokens_unprocessed.
        buffered = ''
        insertions = []
        insertion_buf = []
        for i, t, v in self._find_safe_escape_tokens(text):
            if t is None:
                if insertion_buf:
                    insertions.append((len(buffered), insertion_buf))
                    insertion_buf = []
                buffered += v
            else:
                insertion_buf.append((i, t, v))
        if insertion_buf:
            insertions.append((len(buffered), insertion_buf))
        return do_insertions(insertions,
                             self.lang.get_tokens_unprocessed(buffered))

    def _find_safe_escape_tokens(self, text):
        """ find escape tokens that are not in strings or comments """
        for i, t, v in self._filter_to(
            self.lang.get_tokens_unprocessed(text),
            lambda t: t in Token.Comment or t in Token.String
        ):
            if t is None:
                for i2, t2, v2 in self._find_escape_tokens(v):
                    yield i + i2, t2, v2
            else:
                yield i, None, v

    def _filter_to(self, it, pred):
        """ Keep only the tokens that match `pred`, merge the others together """
        buf = ''
        idx = 0
        for i, t, v in it:
            if pred(t):
                if buf:
                    yield idx, None, buf
                    buf = ''
                yield i, t, v
            else:
                if not buf:
                    idx = i
                buf += v
        if buf:
            yield idx, None, buf

    def _find_escape_tokens(self, text):
        """ Find escape tokens within text, give token=None otherwise """
        index = 0
        while text:
            a, sep1, text = text.partition(self.left)
            if a:
                yield index, None, a
                index += len(a)
            if sep1:
                b, sep2, text = text.partition(self.right)
                if sep2:
                    yield index + len(sep1), Token.Escape, b
                    index += len(sep1) + len(b) + len(sep2)
                else:
                    yield index, Token.Error, sep1
                    index += len(sep1)
                    text = b

# === NexusCore/myenv\Lib\site-packages\pip\_vendor\urllib3\contrib\pyopenssl.py ===
"""
TLS with SNI_-support for Python 2. Follow these instructions if you would
like to verify TLS certificates in Python 2. Note, the default libraries do
*not* do certificate checking; you need to do additional work to validate
certificates yourself.

This needs the following packages installed:

* `pyOpenSSL`_ (tested with 16.0.0)
* `cryptography`_ (minimum 1.3.4, from pyopenssl)
* `idna`_ (minimum 2.0, from cryptography)

However, pyopenssl depends on cryptography, which depends on idna, so while we
use all three directly here we end up having relatively few packages required.

You can install them with the following command:

.. code-block:: bash

    $ python -m pip install pyopenssl cryptography idna

To activate certificate checking, call
:func:`~urllib3.contrib.pyopenssl.inject_into_urllib3` from your Python code
before you begin making HTTP requests. This can be done in a ``sitecustomize``
module, or at any other time before your application begins using ``urllib3``,
like this:

.. code-block:: python

    try:
        import pip._vendor.urllib3.contrib.pyopenssl as pyopenssl
        pyopenssl.inject_into_urllib3()
    except ImportError:
        pass

Now you can use :mod:`urllib3` as you normally would, and it will support SNI
when the required modules are installed.

Activating this module also has the positive side effect of disabling SSL/TLS
compression in Python 2 (see `CRIME attack`_).

.. _sni: https://en.wikipedia.org/wiki/Server_Name_Indication
.. _crime attack: https://en.wikipedia.org/wiki/CRIME_(security_exploit)
.. _pyopenssl: https://www.pyopenssl.org
.. _cryptography: https://cryptography.io
.. _idna: https://github.com/kjd/idna
"""
from __future__ import absolute_import

import OpenSSL.crypto
import OpenSSL.SSL
from cryptography import x509
from cryptography.hazmat.backends.openssl import backend as openssl_backend

try:
    from cryptography.x509 import UnsupportedExtension
except ImportError:
    # UnsupportedExtension is gone in cryptography >= 2.1.0
    class UnsupportedExtension(Exception):
        pass


from io import BytesIO
from socket import error as SocketError
from socket import timeout

try:  # Platform-specific: Python 2
    from socket import _fileobject
except ImportError:  # Platform-specific: Python 3
    _fileobject = None
    from ..packages.backports.makefile import backport_makefile

import logging
import ssl
import sys
import warnings

from .. import util
from ..packages import six
from ..util.ssl_ import PROTOCOL_TLS_CLIENT

warnings.warn(
    "'urllib3.contrib.pyopenssl' module is deprecated and will be removed "
    "in a future release of urllib3 2.x. Read more in this issue: "
    "https://github.com/urllib3/urllib3/issues/2680",
    category=DeprecationWarning,
    stacklevel=2,
)

__all__ = ["inject_into_urllib3", "extract_from_urllib3"]

# SNI always works.
HAS_SNI = True

# Map from urllib3 to PyOpenSSL compatible parameter-values.
_openssl_versions = {
    util.PROTOCOL_TLS: OpenSSL.SSL.SSLv23_METHOD,
    PROTOCOL_TLS_CLIENT: OpenSSL.SSL.SSLv23_METHOD,
    ssl.PROTOCOL_TLSv1: OpenSSL.SSL.TLSv1_METHOD,
}

if hasattr(ssl, "PROTOCOL_SSLv3") and hasattr(OpenSSL.SSL, "SSLv3_METHOD"):
    _openssl_versions[ssl.PROTOCOL_SSLv3] = OpenSSL.SSL.SSLv3_METHOD

if hasattr(ssl, "PROTOCOL_TLSv1_1") and hasattr(OpenSSL.SSL, "TLSv1_1_METHOD"):
    _openssl_versions[ssl.PROTOCOL_TLSv1_1] = OpenSSL.SSL.TLSv1_1_METHOD

if hasattr(ssl, "PROTOCOL_TLSv1_2") and hasattr(OpenSSL.SSL, "TLSv1_2_METHOD"):
    _openssl_versions[ssl.PROTOCOL_TLSv1_2] = OpenSSL.SSL.TLSv1_2_METHOD


_stdlib_to_openssl_verify = {
    ssl.CERT_NONE: OpenSSL.SSL.VERIFY_NONE,
    ssl.CERT_OPTIONAL: OpenSSL.SSL.VERIFY_PEER,
    ssl.CERT_REQUIRED: OpenSSL.SSL.VERIFY_PEER
    + OpenSSL.SSL.VERIFY_FAIL_IF_NO_PEER_CERT,
}
_openssl_to_stdlib_verify = dict((v, k) for k, v in _stdlib_to_openssl_verify.items())

# OpenSSL will only write 16K at a time
SSL_WRITE_BLOCKSIZE = 16384

orig_util_HAS_SNI = util.HAS_SNI
orig_util_SSLContext = util.ssl_.SSLContext


log = logging.getLogger(__name__)


def inject_into_urllib3():
    "Monkey-patch urllib3 with PyOpenSSL-backed SSL-support."

    _validate_dependencies_met()

    util.SSLContext = PyOpenSSLContext
    util.ssl_.SSLContext = PyOpenSSLContext
    util.HAS_SNI = HAS_SNI
    util.ssl_.HAS_SNI = HAS_SNI
    util.IS_PYOPENSSL = True
    util.ssl_.IS_PYOPENSSL = True


def extract_from_urllib3():
    "Undo monkey-patching by :func:`inject_into_urllib3`."

    util.SSLContext = orig_util_SSLContext
    util.ssl_.SSLContext = orig_util_SSLContext
    util.HAS_SNI = orig_util_HAS_SNI
    util.ssl_.HAS_SNI = orig_util_HAS_SNI
    util.IS_PYOPENSSL = False
    util.ssl_.IS_PYOPENSSL = False


def _validate_dependencies_met():
    """
    Verifies that PyOpenSSL's package-level dependencies have been met.
    Throws `ImportError` if they are not met.
    """
    # Method added in `cryptography==1.1`; not available in older versions
    from cryptography.x509.extensions import Extensions

    if getattr(Extensions, "get_extension_for_class", None) is None:
        raise ImportError(
            "'cryptography' module missing required functionality.  "
            "Try upgrading to v1.3.4 or newer."
        )

    # pyOpenSSL 0.14 and above use cryptography for OpenSSL bindings. The _x509
    # attribute is only present on those versions.
    from OpenSSL.crypto import X509

    x509 = X509()
    if getattr(x509, "_x509", None) is None:
        raise ImportError(
            "'pyOpenSSL' module missing required functionality. "
            "Try upgrading to v0.14 or newer."
        )


def _dnsname_to_stdlib(name):
    """
    Converts a dNSName SubjectAlternativeName field to the form used by the
    standard library on the given Python version.

    Cryptography produces a dNSName as a unicode string that was idna-decoded
    from ASCII bytes. We need to idna-encode that string to get it back, and
    then on Python 3 we also need to convert to unicode via UTF-8 (the stdlib
    uses PyUnicode_FromStringAndSize on it, which decodes via UTF-8).

    If the name cannot be idna-encoded then we return None signalling that
    the name given should be skipped.
    """

    def idna_encode(name):
        """
        Borrowed wholesale from the Python Cryptography Project. It turns out
        that we can't just safely call `idna.encode`: it can explode for
        wildcard names. This avoids that problem.
        """
        from pip._vendor import idna

        try:
            for prefix in [u"*.", u"."]:
                if name.startswith(prefix):
                    name = name[len(prefix) :]
                    return prefix.encode("ascii") + idna.encode(name)
            return idna.encode(name)
        except idna.core.IDNAError:
            return None

    # Don't send IPv6 addresses through the IDNA encoder.
    if ":" in name:
        return name

    name = idna_encode(name)
    if name is None:
        return None
    elif sys.version_info >= (3, 0):
        name = name.decode("utf-8")
    return name


def get_subj_alt_name(peer_cert):
    """
    Given an PyOpenSSL certificate, provides all the subject alternative names.
    """
    # Pass the cert to cryptography, which has much better APIs for this.
    if hasattr(peer_cert, "to_cryptography"):
        cert = peer_cert.to_cryptography()
    else:
        der = OpenSSL.crypto.dump_certificate(OpenSSL.crypto.FILETYPE_ASN1, peer_cert)
        cert = x509.load_der_x509_certificate(der, openssl_backend)

    # We want to find the SAN extension. Ask Cryptography to locate it (it's
    # faster than looping in Python)
    try:
        ext = cert.extensions.get_extension_for_class(x509.SubjectAlternativeName).value
    except x509.ExtensionNotFound:
        # No such extension, return the empty list.
        return []
    except (
        x509.DuplicateExtension,
        UnsupportedExtension,
        x509.UnsupportedGeneralNameType,
        UnicodeError,
    ) as e:
        # A problem has been found with the quality of the certificate. Assume
        # no SAN field is present.
        log.warning(
            "A problem was encountered with the certificate that prevented "
            "urllib3 from finding the SubjectAlternativeName field. This can "
            "affect certificate validation. The error was %s",
            e,
        )
        return []

    # We want to return dNSName and iPAddress fields. We need to cast the IPs
    # back to strings because the match_hostname function wants them as
    # strings.
    # Sadly the DNS names need to be idna encoded and then, on Python 3, UTF-8
    # decoded. This is pretty frustrating, but that's what the standard library
    # does with certificates, and so we need to attempt to do the same.
    # We also want to skip over names which cannot be idna encoded.
    names = [
        ("DNS", name)
        for name in map(_dnsname_to_stdlib, ext.get_values_for_type(x509.DNSName))
        if name is not None
    ]
    names.extend(
        ("IP Address", str(name)) for name in ext.get_values_for_type(x509.IPAddress)
    )

    return names


class WrappedSocket(object):
    """API-compatibility wrapper for Python OpenSSL's Connection-class.

    Note: _makefile_refs, _drop() and _reuse() are needed for the garbage
    collector of pypy.
    """

    def __init__(self, connection, socket, suppress_ragged_eofs=True):
        self.connection = connection
        self.socket = socket
        self.suppress_ragged_eofs = suppress_ragged_eofs
        self._makefile_refs = 0
        self._closed = False

    def fileno(self):
        return self.socket.fileno()

    # Copy-pasted from Python 3.5 source code
    def _decref_socketios(self):
        if self._makefile_refs > 0:
            self._makefile_refs -= 1
        if self._closed:
            self.close()

    def recv(self, *args, **kwargs):
        try:
            data = self.connection.recv(*args, **kwargs)
        except OpenSSL.SSL.SysCallError as e:
            if self.suppress_ragged_eofs and e.args == (-1, "Unexpected EOF"):
                return b""
            else:
                raise SocketError(str(e))
        except OpenSSL.SSL.ZeroReturnError:
            if self.connection.get_shutdown() == OpenSSL.SSL.RECEIVED_SHUTDOWN:
                return b""
            else:
                raise
        except OpenSSL.SSL.WantReadError:
            if not util.wait_for_read(self.socket, self.socket.gettimeout()):
                raise timeout("The read operation timed out")
            else:
                return self.recv(*args, **kwargs)

        # TLS 1.3 post-handshake authentication
        except OpenSSL.SSL.Error as e:
            raise ssl.SSLError("read error: %r" % e)
        else:
            return data

    def recv_into(self, *args, **kwargs):
        try:
            return self.connection.recv_into(*args, **kwargs)
        except OpenSSL.SSL.SysCallError as e:
            if self.suppress_ragged_eofs and e.args == (-1, "Unexpected EOF"):
                return 0
            else:
                raise SocketError(str(e))
        except OpenSSL.SSL.ZeroReturnError:
            if self.connection.get_shutdown() == OpenSSL.SSL.RECEIVED_SHUTDOWN:
                return 0
            else:
                raise
        except OpenSSL.SSL.WantReadError:
            if not util.wait_for_read(self.socket, self.socket.gettimeout()):
                raise timeout("The read operation timed out")
            else:
                return self.recv_into(*args, **kwargs)

        # TLS 1.3 post-handshake authentication
        except OpenSSL.SSL.Error as e:
            raise ssl.SSLError("read error: %r" % e)

    def settimeout(self, timeout):
        return self.socket.settimeout(timeout)

    def _send_until_done(self, data):
        while True:
            try:
                return self.connection.send(data)
            except OpenSSL.SSL.WantWriteError:
                if not util.wait_for_write(self.socket, self.socket.gettimeout()):
                    raise timeout()
                continue
            except OpenSSL.SSL.SysCallError as e:
                raise SocketError(str(e))

    def sendall(self, data):
        total_sent = 0
        while total_sent < len(data):
            sent = self._send_until_done(
                data[total_sent : total_sent + SSL_WRITE_BLOCKSIZE]
            )
            total_sent += sent

    def shutdown(self):
        # FIXME rethrow compatible exceptions should we ever use this
        self.connection.shutdown()

    def close(self):
        if self._makefile_refs < 1:
            try:
                self._closed = True
                return self.connection.close()
            except OpenSSL.SSL.Error:
                return
        else:
            self._makefile_refs -= 1

    def getpeercert(self, binary_form=False):
        x509 = self.connection.get_peer_certificate()

        if not x509:
            return x509

        if binary_form:
            return OpenSSL.crypto.dump_certificate(OpenSSL.crypto.FILETYPE_ASN1, x509)

        return {
            "subject": ((("commonName", x509.get_subject().CN),),),
            "subjectAltName": get_subj_alt_name(x509),
        }

    def version(self):
        return self.connection.get_protocol_version_name()

    def _reuse(self):
        self._makefile_refs += 1

    def _drop(self):
        if self._makefile_refs < 1:
            self.close()
        else:
            self._makefile_refs -= 1


if _fileobject:  # Platform-specific: Python 2

    def makefile(self, mode, bufsize=-1):
        self._makefile_refs += 1
        return _fileobject(self, mode, bufsize, close=True)

else:  # Platform-specific: Python 3
    makefile = backport_makefile

WrappedSocket.makefile = makefile


class PyOpenSSLContext(object):
    """
    I am a wrapper class for the PyOpenSSL ``Context`` object. I am responsible
    for translating the interface of the standard library ``SSLContext`` object
    to calls into PyOpenSSL.
    """

    def __init__(self, protocol):
        self.protocol = _openssl_versions[protocol]
        self._ctx = OpenSSL.SSL.Context(self.protocol)
        self._options = 0
        self.check_hostname = False

    @property
    def options(self):
        return self._options

    @options.setter
    def options(self, value):
        self._options = value
        self._ctx.set_options(value)

    @property
    def verify_mode(self):
        return _openssl_to_stdlib_verify[self._ctx.get_verify_mode()]

    @verify_mode.setter
    def verify_mode(self, value):
        self._ctx.set_verify(_stdlib_to_openssl_verify[value], _verify_callback)

    def set_default_verify_paths(self):
        self._ctx.set_default_verify_paths()

    def set_ciphers(self, ciphers):
        if isinstance(ciphers, six.text_type):
            ciphers = ciphers.encode("utf-8")
        self._ctx.set_cipher_list(ciphers)

    def load_verify_locations(self, cafile=None, capath=None, cadata=None):
        if cafile is not None:
            cafile = cafile.encode("utf-8")
        if capath is not None:
            capath = capath.encode("utf-8")
        try:
            self._ctx.load_verify_locations(cafile, capath)
            if cadata is not None:
                self._ctx.load_verify_locations(BytesIO(cadata))
        except OpenSSL.SSL.Error as e:
            raise ssl.SSLError("unable to load trusted certificates: %r" % e)

    def load_cert_chain(self, certfile, keyfile=None, password=None):
        self._ctx.use_certificate_chain_file(certfile)
        if password is not None:
            if not isinstance(password, six.binary_type):
                password = password.encode("utf-8")
            self._ctx.set_passwd_cb(lambda *_: password)
        self._ctx.use_privatekey_file(keyfile or certfile)

    def set_alpn_protocols(self, protocols):
        protocols = [six.ensure_binary(p) for p in protocols]
        return self._ctx.set_alpn_protos(protocols)

    def wrap_socket(
        self,
        sock,
        server_side=False,
        do_handshake_on_connect=True,
        suppress_ragged_eofs=True,
        server_hostname=None,
    ):
        cnx = OpenSSL.SSL.Connection(self._ctx, sock)

        if isinstance(server_hostname, six.text_type):  # Platform-specific: Python 3
            server_hostname = server_hostname.encode("utf-8")

        if server_hostname is not None:
            cnx.set_tlsext_host_name(server_hostname)

        cnx.set_connect_state()

        while True:
            try:
                cnx.do_handshake()
            except OpenSSL.SSL.WantReadError:
                if not util.wait_for_read(sock, sock.gettimeout()):
                    raise timeout("select timed out")
                continue
            except OpenSSL.SSL.Error as e:
                raise ssl.SSLError("bad handshake: %r" % e)
            break

        return WrappedSocket(cnx, sock)


def _verify_callback(cnx, x509, err_no, err_depth, return_code):
    return err_no == 0

# === NexusCore/openenv\Lib\site-packages\httplib2\socks.py ===
"""SocksiPy - Python SOCKS module.

Version 1.00

Copyright 2006 Dan-Haim. All rights reserved.

Redistribution and use in source and binary forms, with or without modification,
are permitted provided that the following conditions are met:
1. Redistributions of source code must retain the above copyright notice, this
   list of conditions and the following disclaimer.
2. Redistributions in binary form must reproduce the above copyright notice,
   this list of conditions and the following disclaimer in the documentation
   and/or other materials provided with the distribution.
3. Neither the name of Dan Haim nor the names of his contributors may be used
   to endorse or promote products derived from this software without specific
   prior written permission.

THIS SOFTWARE IS PROVIDED BY DAN HAIM "AS IS" AND ANY EXPRESS OR IMPLIED
WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF
MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO
EVENT SHALL DAN HAIM OR HIS CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT,
INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA
OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF
LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT
OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMANGE.

This module provides a standard socket-like interface for Python
for tunneling connections through SOCKS proxies.

Minor modifications made by Christopher Gilbert (http://motomastyle.com/) for
use in PyLoris (http://pyloris.sourceforge.net/).

Minor modifications made by Mario Vilas (http://breakingcode.wordpress.com/)
mainly to merge bug fixes found in Sourceforge.
"""

import base64
import socket
import struct
import sys

if getattr(socket, "socket", None) is None:
    raise ImportError("socket.socket missing, proxy support unusable")

PROXY_TYPE_SOCKS4 = 1
PROXY_TYPE_SOCKS5 = 2
PROXY_TYPE_HTTP = 3
PROXY_TYPE_HTTP_NO_TUNNEL = 4

_defaultproxy = None
_orgsocket = socket.socket


class ProxyError(Exception):
    pass


class GeneralProxyError(ProxyError):
    pass


class Socks5AuthError(ProxyError):
    pass


class Socks5Error(ProxyError):
    pass


class Socks4Error(ProxyError):
    pass


class HTTPError(ProxyError):
    pass


_generalerrors = (
    "success",
    "invalid data",
    "not connected",
    "not available",
    "bad proxy type",
    "bad input",
)

_socks5errors = (
    "succeeded",
    "general SOCKS server failure",
    "connection not allowed by ruleset",
    "Network unreachable",
    "Host unreachable",
    "Connection refused",
    "TTL expired",
    "Command not supported",
    "Address type not supported",
    "Unknown error",
)

_socks5autherrors = (
    "succeeded",
    "authentication is required",
    "all offered authentication methods were rejected",
    "unknown username or invalid password",
    "unknown error",
)

_socks4errors = (
    "request granted",
    "request rejected or failed",
    "request rejected because SOCKS server cannot connect to identd on the client",
    "request rejected because the client program and identd report different "
    "user-ids",
    "unknown error",
)


def setdefaultproxy(
    proxytype=None, addr=None, port=None, rdns=True, username=None, password=None
):
    """setdefaultproxy(proxytype, addr[, port[, rdns[, username[, password]]]])
    Sets a default proxy which all further socksocket objects will use,
    unless explicitly changed.
    """
    global _defaultproxy
    _defaultproxy = (proxytype, addr, port, rdns, username, password)


def wrapmodule(module):
    """wrapmodule(module)

    Attempts to replace a module's socket library with a SOCKS socket. Must set
    a default proxy using setdefaultproxy(...) first.
    This will only work on modules that import socket directly into the
    namespace;
    most of the Python Standard Library falls into this category.
    """
    if _defaultproxy != None:
        module.socket.socket = socksocket
    else:
        raise GeneralProxyError((4, "no proxy specified"))


class socksocket(socket.socket):
    """socksocket([family[, type[, proto]]]) -> socket object
    Open a SOCKS enabled socket. The parameters are the same as
    those of the standard socket init. In order for SOCKS to work,
    you must specify family=AF_INET, type=SOCK_STREAM and proto=0.
    """

    def __init__(
        self, family=socket.AF_INET, type=socket.SOCK_STREAM, proto=0, _sock=None
    ):
        _orgsocket.__init__(self, family, type, proto, _sock)
        if _defaultproxy != None:
            self.__proxy = _defaultproxy
        else:
            self.__proxy = (None, None, None, None, None, None)
        self.__proxysockname = None
        self.__proxypeername = None
        self.__httptunnel = True

    def __recvall(self, count):
        """__recvall(count) -> data
        Receive EXACTLY the number of bytes requested from the socket.
        Blocks until the required number of bytes have been received.
        """
        data = self.recv(count)
        while len(data) < count:
            d = self.recv(count - len(data))
            if not d:
                raise GeneralProxyError((0, "connection closed unexpectedly"))
            data = data + d
        return data

    def sendall(self, content, *args):
        """ override socket.socket.sendall method to rewrite the header
        for non-tunneling proxies if needed
        """
        if not self.__httptunnel:
            content = self.__rewriteproxy(content)
        return super(socksocket, self).sendall(content, *args)

    def __rewriteproxy(self, header):
        """ rewrite HTTP request headers to support non-tunneling proxies
        (i.e. those which do not support the CONNECT method).
        This only works for HTTP (not HTTPS) since HTTPS requires tunneling.
        """
        host, endpt = None, None
        hdrs = header.split("\r\n")
        for hdr in hdrs:
            if hdr.lower().startswith("host:"):
                host = hdr
            elif hdr.lower().startswith("get") or hdr.lower().startswith("post"):
                endpt = hdr
        if host and endpt:
            hdrs.remove(host)
            hdrs.remove(endpt)
            host = host.split(" ")[1]
            endpt = endpt.split(" ")
            if self.__proxy[4] != None and self.__proxy[5] != None:
                hdrs.insert(0, self.__getauthheader())
            hdrs.insert(0, "Host: %s" % host)
            hdrs.insert(0, "%s http://%s%s %s" % (endpt[0], host, endpt[1], endpt[2]))
        return "\r\n".join(hdrs)

    def __getauthheader(self):
        auth = self.__proxy[4] + b":" + self.__proxy[5]
        return "Proxy-Authorization: Basic " + base64.b64encode(auth).decode()

    def setproxy(
        self,
        proxytype=None,
        addr=None,
        port=None,
        rdns=True,
        username=None,
        password=None,
        headers=None,
    ):
        """setproxy(proxytype, addr[, port[, rdns[, username[, password]]]])

        Sets the proxy to be used.
        proxytype -    The type of the proxy to be used. Three types
                are supported: PROXY_TYPE_SOCKS4 (including socks4a),
                PROXY_TYPE_SOCKS5 and PROXY_TYPE_HTTP
        addr -        The address of the server (IP or DNS).
        port -        The port of the server. Defaults to 1080 for SOCKS
                servers and 8080 for HTTP proxy servers.
        rdns -        Should DNS queries be preformed on the remote side
                (rather than the local side). The default is True.
                Note: This has no effect with SOCKS4 servers.
        username -    Username to authenticate with to the server.
                The default is no authentication.
        password -    Password to authenticate with to the server.
                Only relevant when username is also provided.
        headers -     Additional or modified headers for the proxy connect
        request.
        """
        self.__proxy = (
            proxytype,
            addr,
            port,
            rdns,
            username.encode() if username else None,
            password.encode() if password else None,
            headers,
        )

    def __negotiatesocks5(self, destaddr, destport):
        """__negotiatesocks5(self,destaddr,destport)
        Negotiates a connection through a SOCKS5 server.
        """
        # First we'll send the authentication packages we support.
        if (self.__proxy[4] != None) and (self.__proxy[5] != None):
            # The username/password details were supplied to the
            # setproxy method so we support the USERNAME/PASSWORD
            # authentication (in addition to the standard none).
            self.sendall(struct.pack("BBBB", 0x05, 0x02, 0x00, 0x02))
        else:
            # No username/password were entered, therefore we
            # only support connections with no authentication.
            self.sendall(struct.pack("BBB", 0x05, 0x01, 0x00))
        # We'll receive the server's response to determine which
        # method was selected
        chosenauth = self.__recvall(2)
        if chosenauth[0:1] != chr(0x05).encode():
            self.close()
            raise GeneralProxyError((1, _generalerrors[1]))
        # Check the chosen authentication method
        if chosenauth[1:2] == chr(0x00).encode():
            # No authentication is required
            pass
        elif chosenauth[1:2] == chr(0x02).encode():
            # Okay, we need to perform a basic username/password
            # authentication.
            packet = bytearray()
            packet.append(0x01)
            packet.append(len(self.__proxy[4]))
            packet.extend(self.__proxy[4])
            packet.append(len(self.__proxy[5]))
            packet.extend(self.__proxy[5])
            self.sendall(packet)
            authstat = self.__recvall(2)
            if authstat[0:1] != chr(0x01).encode():
                # Bad response
                self.close()
                raise GeneralProxyError((1, _generalerrors[1]))
            if authstat[1:2] != chr(0x00).encode():
                # Authentication failed
                self.close()
                raise Socks5AuthError((3, _socks5autherrors[3]))
            # Authentication succeeded
        else:
            # Reaching here is always bad
            self.close()
            if chosenauth[1] == chr(0xFF).encode():
                raise Socks5AuthError((2, _socks5autherrors[2]))
            else:
                raise GeneralProxyError((1, _generalerrors[1]))
        # Now we can request the actual connection
        req = struct.pack("BBB", 0x05, 0x01, 0x00)
        # If the given destination address is an IP address, we'll
        # use the IPv4 address request even if remote resolving was specified.
        try:
            ipaddr = socket.inet_aton(destaddr)
            req = req + chr(0x01).encode() + ipaddr
        except socket.error:
            # Well it's not an IP number,  so it's probably a DNS name.
            if self.__proxy[3]:
                # Resolve remotely
                ipaddr = None
                req = (
                    req
                    + chr(0x03).encode()
                    + chr(len(destaddr)).encode()
                    + destaddr.encode()
                )
            else:
                # Resolve locally
                ipaddr = socket.inet_aton(socket.gethostbyname(destaddr))
                req = req + chr(0x01).encode() + ipaddr
        req = req + struct.pack(">H", destport)
        self.sendall(req)
        # Get the response
        resp = self.__recvall(4)
        if resp[0:1] != chr(0x05).encode():
            self.close()
            raise GeneralProxyError((1, _generalerrors[1]))
        elif resp[1:2] != chr(0x00).encode():
            # Connection failed
            self.close()
            if ord(resp[1:2]) <= 8:
                raise Socks5Error((ord(resp[1:2]), _socks5errors[ord(resp[1:2])]))
            else:
                raise Socks5Error((9, _socks5errors[9]))
        # Get the bound address/port
        elif resp[3:4] == chr(0x01).encode():
            boundaddr = self.__recvall(4)
        elif resp[3:4] == chr(0x03).encode():
            resp = resp + self.recv(1)
            boundaddr = self.__recvall(ord(resp[4:5]))
        else:
            self.close()
            raise GeneralProxyError((1, _generalerrors[1]))
        boundport = struct.unpack(">H", self.__recvall(2))[0]
        self.__proxysockname = (boundaddr, boundport)
        if ipaddr != None:
            self.__proxypeername = (socket.inet_ntoa(ipaddr), destport)
        else:
            self.__proxypeername = (destaddr, destport)

    def getproxysockname(self):
        """getsockname() -> address info
        Returns the bound IP address and port number at the proxy.
        """
        return self.__proxysockname

    def getproxypeername(self):
        """getproxypeername() -> address info
        Returns the IP and port number of the proxy.
        """
        return _orgsocket.getpeername(self)

    def getpeername(self):
        """getpeername() -> address info
        Returns the IP address and port number of the destination
        machine (note: getproxypeername returns the proxy)
        """
        return self.__proxypeername

    def __negotiatesocks4(self, destaddr, destport):
        """__negotiatesocks4(self,destaddr,destport)
        Negotiates a connection through a SOCKS4 server.
        """
        # Check if the destination address provided is an IP address
        rmtrslv = False
        try:
            ipaddr = socket.inet_aton(destaddr)
        except socket.error:
            # It's a DNS name. Check where it should be resolved.
            if self.__proxy[3]:
                ipaddr = struct.pack("BBBB", 0x00, 0x00, 0x00, 0x01)
                rmtrslv = True
            else:
                ipaddr = socket.inet_aton(socket.gethostbyname(destaddr))
        # Construct the request packet
        req = struct.pack(">BBH", 0x04, 0x01, destport) + ipaddr
        # The username parameter is considered userid for SOCKS4
        if self.__proxy[4] != None:
            req = req + self.__proxy[4]
        req = req + chr(0x00).encode()
        # DNS name if remote resolving is required
        # NOTE: This is actually an extension to the SOCKS4 protocol
        # called SOCKS4A and may not be supported in all cases.
        if rmtrslv:
            req = req + destaddr + chr(0x00).encode()
        self.sendall(req)
        # Get the response from the server
        resp = self.__recvall(8)
        if resp[0:1] != chr(0x00).encode():
            # Bad data
            self.close()
            raise GeneralProxyError((1, _generalerrors[1]))
        if resp[1:2] != chr(0x5A).encode():
            # Server returned an error
            self.close()
            if ord(resp[1:2]) in (91, 92, 93):
                self.close()
                raise Socks4Error((ord(resp[1:2]), _socks4errors[ord(resp[1:2]) - 90]))
            else:
                raise Socks4Error((94, _socks4errors[4]))
        # Get the bound address/port
        self.__proxysockname = (
            socket.inet_ntoa(resp[4:]),
            struct.unpack(">H", resp[2:4])[0],
        )
        if rmtrslv != None:
            self.__proxypeername = (socket.inet_ntoa(ipaddr), destport)
        else:
            self.__proxypeername = (destaddr, destport)

    def __negotiatehttp(self, destaddr, destport):
        """__negotiatehttp(self,destaddr,destport)
        Negotiates a connection through an HTTP server.
        """
        # If we need to resolve locally, we do this now
        if not self.__proxy[3]:
            addr = socket.gethostbyname(destaddr)
        else:
            addr = destaddr
        headers = ["CONNECT ", addr, ":", str(destport), " HTTP/1.1\r\n"]
        wrote_host_header = False
        wrote_auth_header = False
        if self.__proxy[6] != None:
            for key, val in self.__proxy[6].iteritems():
                headers += [key, ": ", val, "\r\n"]
                wrote_host_header = key.lower() == "host"
                wrote_auth_header = key.lower() == "proxy-authorization"
        if not wrote_host_header:
            headers += ["Host: ", destaddr, "\r\n"]
        if not wrote_auth_header:
            if self.__proxy[4] != None and self.__proxy[5] != None:
                headers += [self.__getauthheader(), "\r\n"]
        headers.append("\r\n")
        self.sendall("".join(headers).encode())
        # We read the response until we get the string "\r\n\r\n"
        resp = self.recv(1)
        while resp.find("\r\n\r\n".encode()) == -1:
            resp = resp + self.recv(1)
        # We just need the first line to check if the connection
        # was successful
        statusline = resp.splitlines()[0].split(" ".encode(), 2)
        if statusline[0] not in ("HTTP/1.0".encode(), "HTTP/1.1".encode()):
            self.close()
            raise GeneralProxyError((1, _generalerrors[1]))
        try:
            statuscode = int(statusline[1])
        except ValueError:
            self.close()
            raise GeneralProxyError((1, _generalerrors[1]))
        if statuscode != 200:
            self.close()
            raise HTTPError((statuscode, statusline[2]))
        self.__proxysockname = ("0.0.0.0", 0)
        self.__proxypeername = (addr, destport)

    def connect(self, destpair):
        """connect(self, despair)
        Connects to the specified destination through a proxy.
        destpar - A tuple of the IP/DNS address and the port number.
        (identical to socket's connect).
        To select the proxy server use setproxy().
        """
        # Do a minimal input check first
        if (
            (not type(destpair) in (list, tuple))
            or (len(destpair) < 2)
            or (not isinstance(destpair[0], (str, bytes)))
            or (type(destpair[1]) != int)
        ):
            raise GeneralProxyError((5, _generalerrors[5]))
        if self.__proxy[0] == PROXY_TYPE_SOCKS5:
            if self.__proxy[2] != None:
                portnum = self.__proxy[2]
            else:
                portnum = 1080
            _orgsocket.connect(self, (self.__proxy[1], portnum))
            self.__negotiatesocks5(destpair[0], destpair[1])
        elif self.__proxy[0] == PROXY_TYPE_SOCKS4:
            if self.__proxy[2] != None:
                portnum = self.__proxy[2]
            else:
                portnum = 1080
            _orgsocket.connect(self, (self.__proxy[1], portnum))
            self.__negotiatesocks4(destpair[0], destpair[1])
        elif self.__proxy[0] == PROXY_TYPE_HTTP:
            if self.__proxy[2] != None:
                portnum = self.__proxy[2]
            else:
                portnum = 8080
            _orgsocket.connect(self, (self.__proxy[1], portnum))
            self.__negotiatehttp(destpair[0], destpair[1])
        elif self.__proxy[0] == PROXY_TYPE_HTTP_NO_TUNNEL:
            if self.__proxy[2] != None:
                portnum = self.__proxy[2]
            else:
                portnum = 8080
            _orgsocket.connect(self, (self.__proxy[1], portnum))
            if destpair[1] == 443:
                self.__negotiatehttp(destpair[0], destpair[1])
            else:
                self.__httptunnel = False
        elif self.__proxy[0] == None:
            _orgsocket.connect(self, (destpair[0], destpair[1]))
        else:
            raise GeneralProxyError((4, _generalerrors[4]))

# === NexusCore/openenv\Lib\site-packages\fontTools\varLib\mutator.py ===
"""
Instantiate a variation font.  Run, eg:

.. code-block:: sh

    $ fonttools varLib.mutator ./NotoSansArabic-VF.ttf wght=140 wdth=85
"""

from fontTools.misc.fixedTools import floatToFixedToFloat, floatToFixed
from fontTools.misc.roundTools import otRound
from fontTools.pens.boundsPen import BoundsPen
from fontTools.ttLib import TTFont, newTable
from fontTools.ttLib.tables import ttProgram
from fontTools.ttLib.tables._g_l_y_f import (
    GlyphCoordinates,
    flagOverlapSimple,
    OVERLAP_COMPOUND,
)
from fontTools.varLib.models import (
    supportScalar,
    normalizeLocation,
    piecewiseLinearMap,
)
from fontTools.varLib.merger import MutatorMerger
from fontTools.varLib.varStore import VarStoreInstancer
from fontTools.varLib.mvar import MVAR_ENTRIES
from fontTools.varLib.iup import iup_delta
import fontTools.subset.cff
import os.path
import logging
from io import BytesIO


log = logging.getLogger("fontTools.varlib.mutator")

# map 'wdth' axis (1..200) to OS/2.usWidthClass (1..9), rounding to closest
OS2_WIDTH_CLASS_VALUES = {}
percents = [50.0, 62.5, 75.0, 87.5, 100.0, 112.5, 125.0, 150.0, 200.0]
for i, (prev, curr) in enumerate(zip(percents[:-1], percents[1:]), start=1):
    half = (prev + curr) / 2
    OS2_WIDTH_CLASS_VALUES[half] = i


def interpolate_cff2_PrivateDict(topDict, interpolateFromDeltas):
    pd_blend_lists = (
        "BlueValues",
        "OtherBlues",
        "FamilyBlues",
        "FamilyOtherBlues",
        "StemSnapH",
        "StemSnapV",
    )
    pd_blend_values = ("BlueScale", "BlueShift", "BlueFuzz", "StdHW", "StdVW")
    for fontDict in topDict.FDArray:
        pd = fontDict.Private
        vsindex = pd.vsindex if (hasattr(pd, "vsindex")) else 0
        for key, value in pd.rawDict.items():
            if (key in pd_blend_values) and isinstance(value, list):
                delta = interpolateFromDeltas(vsindex, value[1:])
                pd.rawDict[key] = otRound(value[0] + delta)
            elif (key in pd_blend_lists) and isinstance(value[0], list):
                """If any argument in a BlueValues list is a blend list,
                then they all are. The first value of each list is an
                absolute value. The delta tuples are calculated from
                relative master values, hence we need to append all the
                deltas to date to each successive absolute value."""
                delta = 0
                for i, val_list in enumerate(value):
                    delta += otRound(interpolateFromDeltas(vsindex, val_list[1:]))
                    value[i] = val_list[0] + delta


def interpolate_cff2_charstrings(topDict, interpolateFromDeltas, glyphOrder):
    charstrings = topDict.CharStrings
    for gname in glyphOrder:
        # Interpolate charstring
        # e.g replace blend op args with regular args,
        # and use and discard vsindex op.
        charstring = charstrings[gname]
        new_program = []
        vsindex = 0
        last_i = 0
        for i, token in enumerate(charstring.program):
            if token == "vsindex":
                vsindex = charstring.program[i - 1]
                if last_i != 0:
                    new_program.extend(charstring.program[last_i : i - 1])
                last_i = i + 1
            elif token == "blend":
                num_regions = charstring.getNumRegions(vsindex)
                numMasters = 1 + num_regions
                num_args = charstring.program[i - 1]
                # The program list starting at program[i] is now:
                # ..args for following operations
                # num_args values  from the default font
                # num_args tuples, each with numMasters-1 delta values
                # num_blend_args
                # 'blend'
                argi = i - (num_args * numMasters + 1)
                end_args = tuplei = argi + num_args
                while argi < end_args:
                    next_ti = tuplei + num_regions
                    deltas = charstring.program[tuplei:next_ti]
                    delta = interpolateFromDeltas(vsindex, deltas)
                    charstring.program[argi] += otRound(delta)
                    tuplei = next_ti
                    argi += 1
                new_program.extend(charstring.program[last_i:end_args])
                last_i = i + 1
        if last_i != 0:
            new_program.extend(charstring.program[last_i:])
            charstring.program = new_program


def interpolate_cff2_metrics(varfont, topDict, glyphOrder, loc):
    """Unlike TrueType glyphs, neither advance width nor bounding box
    info is stored in a CFF2 charstring. The width data exists only in
    the hmtx and HVAR tables. Since LSB data cannot be interpolated
    reliably from the master LSB values in the hmtx table, we traverse
    the charstring to determine the actual bound box."""

    charstrings = topDict.CharStrings
    boundsPen = BoundsPen(glyphOrder)
    hmtx = varfont["hmtx"]
    hvar_table = None
    if "HVAR" in varfont:
        hvar_table = varfont["HVAR"].table
        fvar = varfont["fvar"]
        varStoreInstancer = VarStoreInstancer(hvar_table.VarStore, fvar.axes, loc)

    for gid, gname in enumerate(glyphOrder):
        entry = list(hmtx[gname])
        # get width delta.
        if hvar_table:
            if hvar_table.AdvWidthMap:
                width_idx = hvar_table.AdvWidthMap.mapping[gname]
            else:
                width_idx = gid
            width_delta = otRound(varStoreInstancer[width_idx])
        else:
            width_delta = 0

        # get LSB.
        boundsPen.init()
        charstring = charstrings[gname]
        charstring.draw(boundsPen)
        if boundsPen.bounds is None:
            # Happens with non-marking glyphs
            lsb_delta = 0
        else:
            lsb = otRound(boundsPen.bounds[0])
            lsb_delta = entry[1] - lsb

        if lsb_delta or width_delta:
            if width_delta:
                entry[0] = max(0, entry[0] + width_delta)
            if lsb_delta:
                entry[1] = lsb
            hmtx[gname] = tuple(entry)


def instantiateVariableFont(varfont, location, inplace=False, overlap=True):
    """Generate a static instance from a variable TTFont and a dictionary
    defining the desired location along the variable font's axes.
    The location values must be specified as user-space coordinates, e.g.:

    .. code-block::

        {'wght': 400, 'wdth': 100}

    By default, a new TTFont object is returned. If ``inplace`` is True, the
    input varfont is modified and reduced to a static font.

    When the overlap parameter is defined as True,
    OVERLAP_SIMPLE and OVERLAP_COMPOUND bits are set to 1.  See
    https://docs.microsoft.com/en-us/typography/opentype/spec/glyf
    """
    if not inplace:
        # make a copy to leave input varfont unmodified
        stream = BytesIO()
        varfont.save(stream)
        stream.seek(0)
        varfont = TTFont(stream)

    fvar = varfont["fvar"]
    axes = {a.axisTag: (a.minValue, a.defaultValue, a.maxValue) for a in fvar.axes}
    loc = normalizeLocation(location, axes)
    if "avar" in varfont:
        maps = varfont["avar"].segments
        loc = {k: piecewiseLinearMap(v, maps[k]) for k, v in loc.items()}
    # Quantize to F2Dot14, to avoid surprise interpolations.
    loc = {k: floatToFixedToFloat(v, 14) for k, v in loc.items()}
    # Location is normalized now
    log.info("Normalized location: %s", loc)

    if "gvar" in varfont:
        log.info("Mutating glyf/gvar tables")
        gvar = varfont["gvar"]
        glyf = varfont["glyf"]
        hMetrics = varfont["hmtx"].metrics
        vMetrics = getattr(varfont.get("vmtx"), "metrics", None)
        # get list of glyph names in gvar sorted by component depth
        glyphnames = sorted(
            gvar.variations.keys(),
            key=lambda name: (
                (
                    glyf[name].getCompositeMaxpValues(glyf).maxComponentDepth
                    if glyf[name].isComposite()
                    else 0
                ),
                name,
            ),
        )
        for glyphname in glyphnames:
            variations = gvar.variations[glyphname]
            coordinates, _ = glyf._getCoordinatesAndControls(
                glyphname, hMetrics, vMetrics
            )
            origCoords, endPts = None, None
            for var in variations:
                scalar = supportScalar(loc, var.axes)
                if not scalar:
                    continue
                delta = var.coordinates
                if None in delta:
                    if origCoords is None:
                        origCoords, g = glyf._getCoordinatesAndControls(
                            glyphname, hMetrics, vMetrics
                        )
                    delta = iup_delta(delta, origCoords, g.endPts)
                coordinates += GlyphCoordinates(delta) * scalar
            glyf._setCoordinates(glyphname, coordinates, hMetrics, vMetrics)
    else:
        glyf = None

    if "DSIG" in varfont:
        del varfont["DSIG"]

    if "cvar" in varfont:
        log.info("Mutating cvt/cvar tables")
        cvar = varfont["cvar"]
        cvt = varfont["cvt "]
        deltas = {}
        for var in cvar.variations:
            scalar = supportScalar(loc, var.axes)
            if not scalar:
                continue
            for i, c in enumerate(var.coordinates):
                if c is not None:
                    deltas[i] = deltas.get(i, 0) + scalar * c
        for i, delta in deltas.items():
            cvt[i] += otRound(delta)

    if "CFF2" in varfont:
        log.info("Mutating CFF2 table")
        glyphOrder = varfont.getGlyphOrder()
        CFF2 = varfont["CFF2"]
        topDict = CFF2.cff.topDictIndex[0]
        vsInstancer = VarStoreInstancer(topDict.VarStore.otVarStore, fvar.axes, loc)
        interpolateFromDeltas = vsInstancer.interpolateFromDeltas
        interpolate_cff2_PrivateDict(topDict, interpolateFromDeltas)
        CFF2.desubroutinize()
        interpolate_cff2_charstrings(topDict, interpolateFromDeltas, glyphOrder)
        interpolate_cff2_metrics(varfont, topDict, glyphOrder, loc)
        del topDict.rawDict["VarStore"]
        del topDict.VarStore

    if "MVAR" in varfont:
        log.info("Mutating MVAR table")
        mvar = varfont["MVAR"].table
        varStoreInstancer = VarStoreInstancer(mvar.VarStore, fvar.axes, loc)
        records = mvar.ValueRecord
        for rec in records:
            mvarTag = rec.ValueTag
            if mvarTag not in MVAR_ENTRIES:
                continue
            tableTag, itemName = MVAR_ENTRIES[mvarTag]
            delta = otRound(varStoreInstancer[rec.VarIdx])
            if not delta:
                continue
            setattr(
                varfont[tableTag],
                itemName,
                getattr(varfont[tableTag], itemName) + delta,
            )

    log.info("Mutating FeatureVariations")
    for tableTag in "GSUB", "GPOS":
        if not tableTag in varfont:
            continue
        table = varfont[tableTag].table
        if not getattr(table, "FeatureVariations", None):
            continue
        variations = table.FeatureVariations
        for record in variations.FeatureVariationRecord:
            applies = True
            for condition in record.ConditionSet.ConditionTable:
                if condition.Format == 1:
                    axisIdx = condition.AxisIndex
                    axisTag = fvar.axes[axisIdx].axisTag
                    Min = condition.FilterRangeMinValue
                    Max = condition.FilterRangeMaxValue
                    v = loc[axisTag]
                    if not (Min <= v <= Max):
                        applies = False
                else:
                    applies = False
                if not applies:
                    break

            if applies:
                assert record.FeatureTableSubstitution.Version == 0x00010000
                for rec in record.FeatureTableSubstitution.SubstitutionRecord:
                    table.FeatureList.FeatureRecord[rec.FeatureIndex].Feature = (
                        rec.Feature
                    )
                break
        del table.FeatureVariations

    if "GDEF" in varfont and varfont["GDEF"].table.Version >= 0x00010003:
        log.info("Mutating GDEF/GPOS/GSUB tables")
        gdef = varfont["GDEF"].table
        instancer = VarStoreInstancer(gdef.VarStore, fvar.axes, loc)

        merger = MutatorMerger(varfont, instancer)
        merger.mergeTables(varfont, [varfont], ["GDEF", "GPOS"])

        # Downgrade GDEF.
        del gdef.VarStore
        gdef.Version = 0x00010002
        if gdef.MarkGlyphSetsDef is None:
            del gdef.MarkGlyphSetsDef
            gdef.Version = 0x00010000

        if not (
            gdef.LigCaretList
            or gdef.MarkAttachClassDef
            or gdef.GlyphClassDef
            or gdef.AttachList
            or (gdef.Version >= 0x00010002 and gdef.MarkGlyphSetsDef)
        ):
            del varfont["GDEF"]

    addidef = False
    if glyf:
        for glyph in glyf.glyphs.values():
            if hasattr(glyph, "program"):
                instructions = glyph.program.getAssembly()
                # If GETVARIATION opcode is used in bytecode of any glyph add IDEF
                addidef = any(op.startswith("GETVARIATION") for op in instructions)
                if addidef:
                    break
        if overlap:
            for glyph_name in glyf.keys():
                glyph = glyf[glyph_name]
                # Set OVERLAP_COMPOUND bit for compound glyphs
                if glyph.isComposite():
                    glyph.components[0].flags |= OVERLAP_COMPOUND
                # Set OVERLAP_SIMPLE bit for simple glyphs
                elif glyph.numberOfContours > 0:
                    glyph.flags[0] |= flagOverlapSimple
    if addidef:
        log.info("Adding IDEF to fpgm table for GETVARIATION opcode")
        asm = []
        if "fpgm" in varfont:
            fpgm = varfont["fpgm"]
            asm = fpgm.program.getAssembly()
        else:
            fpgm = newTable("fpgm")
            fpgm.program = ttProgram.Program()
            varfont["fpgm"] = fpgm
        asm.append("PUSHB[000] 145")
        asm.append("IDEF[ ]")
        args = [str(len(loc))]
        for a in fvar.axes:
            args.append(str(floatToFixed(loc[a.axisTag], 14)))
        asm.append("NPUSHW[ ] " + " ".join(args))
        asm.append("ENDF[ ]")
        fpgm.program.fromAssembly(asm)

        # Change maxp attributes as IDEF is added
        if "maxp" in varfont:
            maxp = varfont["maxp"]
            setattr(
                maxp, "maxInstructionDefs", 1 + getattr(maxp, "maxInstructionDefs", 0)
            )
            setattr(
                maxp,
                "maxStackElements",
                max(len(loc), getattr(maxp, "maxStackElements", 0)),
            )

    if "name" in varfont:
        log.info("Pruning name table")
        exclude = {a.axisNameID for a in fvar.axes}
        for i in fvar.instances:
            exclude.add(i.subfamilyNameID)
            exclude.add(i.postscriptNameID)
        if "ltag" in varfont:
            # Drop the whole 'ltag' table if all its language tags are referenced by
            # name records to be pruned.
            # TODO: prune unused ltag tags and re-enumerate langIDs accordingly
            excludedUnicodeLangIDs = [
                n.langID
                for n in varfont["name"].names
                if n.nameID in exclude and n.platformID == 0 and n.langID != 0xFFFF
            ]
            if set(excludedUnicodeLangIDs) == set(range(len((varfont["ltag"].tags)))):
                del varfont["ltag"]
        varfont["name"].names[:] = [
            n
            for n in varfont["name"].names
            if n.nameID < 256 or n.nameID not in exclude
        ]

    if "wght" in location and "OS/2" in varfont:
        varfont["OS/2"].usWeightClass = otRound(max(1, min(location["wght"], 1000)))
    if "wdth" in location:
        wdth = location["wdth"]
        for percent, widthClass in sorted(OS2_WIDTH_CLASS_VALUES.items()):
            if wdth < percent:
                varfont["OS/2"].usWidthClass = widthClass
                break
        else:
            varfont["OS/2"].usWidthClass = 9
    if "slnt" in location and "post" in varfont:
        varfont["post"].italicAngle = max(-90, min(location["slnt"], 90))

    log.info("Removing variable tables")
    for tag in ("avar", "cvar", "fvar", "gvar", "HVAR", "MVAR", "VVAR", "STAT"):
        if tag in varfont:
            del varfont[tag]

    return varfont


def main(args=None):
    """Instantiate a variation font"""
    from fontTools import configLogger
    import argparse

    parser = argparse.ArgumentParser(
        "fonttools varLib.mutator", description="Instantiate a variable font"
    )
    parser.add_argument("input", metavar="INPUT.ttf", help="Input variable TTF file.")
    parser.add_argument(
        "locargs",
        metavar="AXIS=LOC",
        nargs="*",
        help="List of space separated locations. A location consist in "
        "the name of a variation axis, followed by '=' and a number. E.g.: "
        " wght=700 wdth=80. The default is the location of the base master.",
    )
    parser.add_argument(
        "-o",
        "--output",
        metavar="OUTPUT.ttf",
        default=None,
        help="Output instance TTF file (default: INPUT-instance.ttf).",
    )
    parser.add_argument(
        "--no-recalc-timestamp",
        dest="recalc_timestamp",
        action="store_false",
        help="Don't set the output font's timestamp to the current time.",
    )
    logging_group = parser.add_mutually_exclusive_group(required=False)
    logging_group.add_argument(
        "-v", "--verbose", action="store_true", help="Run more verbosely."
    )
    logging_group.add_argument(
        "-q", "--quiet", action="store_true", help="Turn verbosity off."
    )
    parser.add_argument(
        "--no-overlap",
        dest="overlap",
        action="store_false",
        help="Don't set OVERLAP_SIMPLE/OVERLAP_COMPOUND glyf flags.",
    )
    options = parser.parse_args(args)

    varfilename = options.input
    outfile = (
        os.path.splitext(varfilename)[0] + "-instance.ttf"
        if not options.output
        else options.output
    )
    configLogger(
        level=("DEBUG" if options.verbose else "ERROR" if options.quiet else "INFO")
    )

    loc = {}
    for arg in options.locargs:
        try:
            tag, val = arg.split("=")
            assert len(tag) <= 4
            loc[tag.ljust(4)] = float(val)
        except (ValueError, AssertionError):
            parser.error("invalid location argument format: %r" % arg)
    log.info("Location: %s", loc)

    log.info("Loading variable font")
    varfont = TTFont(varfilename, recalcTimestamp=options.recalc_timestamp)

    instantiateVariableFont(varfont, loc, inplace=True, overlap=options.overlap)

    log.info("Saving instance font %s", outfile)
    varfont.save(outfile)


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        sys.exit(main())
    import doctest

    sys.exit(doctest.testmod().failed)

# === NexusCore/openenv\Lib\site-packages\litellm\llms\vertex_ai\common_utils.py ===
import re
from typing import Any, Dict, List, Literal, Optional, Set, Tuple, Union, get_type_hints

import httpx

import litellm
from litellm import supports_response_schema, supports_system_messages, verbose_logger
from litellm.constants import DEFAULT_MAX_RECURSE_DEPTH
from litellm.litellm_core_utils.prompt_templates.common_utils import unpack_defs
from litellm.llms.base_llm.chat.transformation import BaseLLMException
from litellm.types.llms.vertex_ai import PartType, Schema


class VertexAIError(BaseLLMException):
    def __init__(
        self,
        status_code: int,
        message: str,
        headers: Optional[Union[Dict, httpx.Headers]] = None,
    ):
        super().__init__(message=message, status_code=status_code, headers=headers)


def get_supports_system_message(
    model: str, custom_llm_provider: Literal["vertex_ai", "vertex_ai_beta", "gemini"]
) -> bool:
    try:
        _custom_llm_provider = custom_llm_provider
        if custom_llm_provider == "vertex_ai_beta":
            _custom_llm_provider = "vertex_ai"
        supports_system_message = supports_system_messages(
            model=model, custom_llm_provider=_custom_llm_provider
        )

        # Vertex Models called in the `/gemini` request/response format also support system messages
        if litellm.VertexGeminiConfig._is_model_gemini_spec_model(model):
            supports_system_message = True
    except Exception as e:
        verbose_logger.warning(
            "Unable to identify if system message supported. Defaulting to 'False'. Received error message - {}\nAdd it here - https://github.com/BerriAI/litellm/blob/main/model_prices_and_context_window.json".format(
                str(e)
            )
        )
        supports_system_message = False

    return supports_system_message


def get_supports_response_schema(
    model: str, custom_llm_provider: Literal["vertex_ai", "vertex_ai_beta", "gemini"]
) -> bool:
    _custom_llm_provider = custom_llm_provider
    if custom_llm_provider == "vertex_ai_beta":
        _custom_llm_provider = "vertex_ai"

    _supports_response_schema = supports_response_schema(
        model=model, custom_llm_provider=_custom_llm_provider
    )

    return _supports_response_schema


from typing import Literal, Optional

all_gemini_url_modes = Literal[
    "chat", "embedding", "batch_embedding", "image_generation"
]


def _get_vertex_url(
    mode: all_gemini_url_modes,
    model: str,
    stream: Optional[bool],
    vertex_project: Optional[str],
    vertex_location: Optional[str],
    vertex_api_version: Literal["v1", "v1beta1"],
) -> Tuple[str, str]:
    url: Optional[str] = None
    endpoint: Optional[str] = None

    model = litellm.VertexGeminiConfig.get_model_for_vertex_ai_url(model=model)
    if mode == "chat":
        ### SET RUNTIME ENDPOINT ###
        endpoint = "generateContent"
        if stream is True:
            endpoint = "streamGenerateContent"
            if vertex_location == "global":
                url = f"https://aiplatform.googleapis.com/{vertex_api_version}/projects/{vertex_project}/locations/global/publishers/google/models/{model}:{endpoint}?alt=sse"
            else:
                url = f"https://{vertex_location}-aiplatform.googleapis.com/{vertex_api_version}/projects/{vertex_project}/locations/{vertex_location}/publishers/google/models/{model}:{endpoint}?alt=sse"
        else:
            if vertex_location == "global":
                url = f"https://aiplatform.googleapis.com/{vertex_api_version}/projects/{vertex_project}/locations/global/publishers/google/models/{model}:{endpoint}"
            else:
                url = f"https://{vertex_location}-aiplatform.googleapis.com/{vertex_api_version}/projects/{vertex_project}/locations/{vertex_location}/publishers/google/models/{model}:{endpoint}"

        # if model is only numeric chars then it's a fine tuned gemini model
        # model = 4965075652664360960
        # send to this url: url = f"https://{vertex_location}-aiplatform.googleapis.com/{version}/projects/{vertex_project}/locations/{vertex_location}/endpoints/{model}:{endpoint}"
        if model.isdigit():
            # It's a fine-tuned Gemini model
            url = f"https://{vertex_location}-aiplatform.googleapis.com/{vertex_api_version}/projects/{vertex_project}/locations/{vertex_location}/endpoints/{model}:{endpoint}"
            if stream is True:
                url += "?alt=sse"
    elif mode == "embedding":
        endpoint = "predict"
        url = f"https://{vertex_location}-aiplatform.googleapis.com/v1/projects/{vertex_project}/locations/{vertex_location}/publishers/google/models/{model}:{endpoint}"
        if model.isdigit():
            # https://us-central1-aiplatform.googleapis.com/v1/projects/$PROJECT_ID/locations/us-central1/endpoints/$ENDPOINT_ID:predict
            url = f"https://{vertex_location}-aiplatform.googleapis.com/{vertex_api_version}/projects/{vertex_project}/locations/{vertex_location}/endpoints/{model}:{endpoint}"
    elif mode == "image_generation":
        endpoint = "predict"
        url = f"https://{vertex_location}-aiplatform.googleapis.com/v1/projects/{vertex_project}/locations/{vertex_location}/publishers/google/models/{model}:{endpoint}"
        if model.isdigit():
            url = f"https://{vertex_location}-aiplatform.googleapis.com/{vertex_api_version}/projects/{vertex_project}/locations/{vertex_location}/endpoints/{model}:{endpoint}"
    if not url or not endpoint:
        raise ValueError(f"Unable to get vertex url/endpoint for mode: {mode}")
    return url, endpoint


def _get_gemini_url(
    mode: all_gemini_url_modes,
    model: str,
    stream: Optional[bool],
    gemini_api_key: Optional[str],
) -> Tuple[str, str]:
    _gemini_model_name = "models/{}".format(model)
    if mode == "chat":
        endpoint = "generateContent"
        if stream is True:
            endpoint = "streamGenerateContent"
            url = "https://generativelanguage.googleapis.com/v1beta/{}:{}?key={}&alt=sse".format(
                _gemini_model_name, endpoint, gemini_api_key
            )
        else:
            url = (
                "https://generativelanguage.googleapis.com/v1beta/{}:{}?key={}".format(
                    _gemini_model_name, endpoint, gemini_api_key
                )
            )
    elif mode == "embedding":
        endpoint = "embedContent"
        url = "https://generativelanguage.googleapis.com/v1beta/{}:{}?key={}".format(
            _gemini_model_name, endpoint, gemini_api_key
        )
    elif mode == "batch_embedding":
        endpoint = "batchEmbedContents"
        url = "https://generativelanguage.googleapis.com/v1beta/{}:{}?key={}".format(
            _gemini_model_name, endpoint, gemini_api_key
        )
    elif mode == "image_generation":
        raise ValueError(
            "LiteLLM's `gemini/` route does not support image generation yet. Let us know if you need this feature by opening an issue at https://github.com/BerriAI/litellm/issues"
        )

    return url, endpoint


def _check_text_in_content(parts: List[PartType]) -> bool:
    """
    check that user_content has 'text' parameter.
        - Known Vertex Error: Unable to submit request because it must have a text parameter.
        - 'text' param needs to be len > 0
        - Relevant Issue: https://github.com/BerriAI/litellm/issues/5515
    """
    has_text_param = False
    for part in parts:
        if "text" in part and part.get("text"):
            has_text_param = True

    return has_text_param


def _build_vertex_schema(parameters: dict, add_property_ordering: bool = False):
    """
    This is a modified version of https://github.com/google-gemini/generative-ai-python/blob/8f77cc6ac99937cd3a81299ecf79608b91b06bbb/google/generativeai/types/content_types.py#L419

    Updates the input parameters, removing extraneous fields, adjusting types, unwinding $defs, and adding propertyOrdering if specified, returning the updated parameters.

    Parameters:
        parameters: dict - the json schema to build from
        add_property_ordering: bool - whether to add propertyOrdering to the schema. This is only applicable to schemas for structured outputs. See
          set_schema_property_ordering for more details.
    Returns:
        parameters: dict - the input parameters, modified in place
    """
    # Get valid fields from Schema TypedDict
    valid_schema_fields = set(get_type_hints(Schema).keys())

    defs = parameters.pop("$defs", {})
    # flatten the defs
    for name, value in defs.items():
        unpack_defs(value, defs)
    unpack_defs(parameters, defs)

    # 5. Nullable fields:
    #     * https://github.com/pydantic/pydantic/issues/1270
    #     * https://stackoverflow.com/a/58841311
    #     * https://github.com/pydantic/pydantic/discussions/4872
    convert_anyof_null_to_nullable(parameters)

    # Handle empty items objects
    process_items(parameters)
    add_object_type(parameters)
    # Postprocessing
    # Filter out fields that don't exist in Schema
    parameters = filter_schema_fields(parameters, valid_schema_fields)

    if add_property_ordering:
        set_schema_property_ordering(parameters)

    return parameters


def _filter_anyof_fields(schema_dict: Dict[str, Any]) -> Dict[str, Any]:
    """
    When anyof is present, only keep the anyof field and its contents - otherwise VertexAI will throw an error - https://github.com/BerriAI/litellm/issues/11164
    Filter out other fields in the same dict.

    E.g. {"anyOf": [{"type": "string"}, {"type": "null"}], "default": "test"} -> {"anyOf": [{"type": "string"}, {"type": "null"}]}

    Case 2: If additional metadata is present, try to keep it
    E.g. {"anyOf": [{"type": "string"}, {"type": "null"}], "default": "test", "title": "test"} -> {"anyOf": [{"type": "string", "title": "test"}, {"type": "null", "title": "test"}]}
    """
    title = schema_dict.get("title", None)
    description = schema_dict.get("description", None)

    if isinstance(schema_dict, dict) and schema_dict.get("anyOf"):
        any_of = schema_dict["anyOf"]
        if (
            (title or description)
            and isinstance(any_of, list)
            and all(isinstance(item, dict) for item in any_of)
        ):
            for item in any_of:
                if title:
                    item["title"] = title
                if description:
                    item["description"] = description
            return {"anyOf": any_of}
        else:
            return schema_dict
    return schema_dict


def process_items(schema, depth=0):
    if depth > DEFAULT_MAX_RECURSE_DEPTH:
        raise ValueError(
            f"Max depth of {DEFAULT_MAX_RECURSE_DEPTH} exceeded while processing schema. Please check the schema for excessive nesting."
        )
    if isinstance(schema, dict):
        if "items" in schema and schema["items"] == {}:
            schema["items"] = {"type": "object"}
        for key, value in schema.items():
            if isinstance(value, dict):
                process_items(value, depth + 1)
            elif isinstance(value, list):
                for item in value:
                    if isinstance(item, dict):
                        process_items(item, depth + 1)


def set_schema_property_ordering(
    schema: Dict[str, Any], depth: int = 0
) -> Dict[str, Any]:
    """
    vertex ai and generativeai apis order output of fields alphabetically, unless you specify the order.
    python dicts retain order, so we just use that. Note that this field only applies to structured outputs, and not tools.
    Function tools are not afflicted by the same alphabetical ordering issue, (the order of keys returned seems to be arbitrary, up to the model)
    https://cloud.google.com/vertex-ai/docs/reference/rest/v1/projects.locations.cachedContents#Schema.FIELDS.property_ordering

    Args:
        schema: The schema dictionary to process
        depth: Current recursion depth to prevent infinite loops
    """
    if depth > DEFAULT_MAX_RECURSE_DEPTH:
        raise ValueError(
            f"Max depth of {DEFAULT_MAX_RECURSE_DEPTH} exceeded while processing schema. Please check the schema for excessive nesting."
        )

    if "properties" in schema and isinstance(schema["properties"], dict):
        # retain propertyOrdering as an escape hatch if user already specifies it
        if "propertyOrdering" not in schema:
            schema["propertyOrdering"] = [k for k, v in schema["properties"].items()]
        for k, v in schema["properties"].items():
            set_schema_property_ordering(v, depth + 1)
    if "items" in schema:
        set_schema_property_ordering(schema["items"], depth + 1)
    return schema


def filter_schema_fields(
    schema_dict: Dict[str, Any], valid_fields: Set[str], processed=None
) -> Dict[str, Any]:
    """
    Recursively filter a schema dictionary to keep only valid fields.
    """
    if processed is None:
        processed = set()

    # Handle circular references
    schema_id = id(schema_dict)
    if schema_id in processed:
        return schema_dict
    processed.add(schema_id)

    if not isinstance(schema_dict, dict):
        return schema_dict

    result = {}
    schema_dict = _filter_anyof_fields(schema_dict)
    for key, value in schema_dict.items():
        if key not in valid_fields:
            continue

        if key == "properties" and isinstance(value, dict):
            result[key] = {
                k: filter_schema_fields(v, valid_fields, processed)
                for k, v in value.items()
            }
        elif key == "items" and isinstance(value, dict):
            result[key] = filter_schema_fields(value, valid_fields, processed)
        elif key == "anyOf" and isinstance(value, list):
            result[key] = [
                filter_schema_fields(item, valid_fields, processed) for item in value  # type: ignore
            ]
        else:
            result[key] = value

    return result


def convert_anyof_null_to_nullable(schema, depth=0):
    if depth > DEFAULT_MAX_RECURSE_DEPTH:
        raise ValueError(
            f"Max depth of {DEFAULT_MAX_RECURSE_DEPTH} exceeded while processing schema. Please check the schema for excessive nesting."
        )
    """ Converts null objects within anyOf by removing them and adding nullable to all remaining objects """
    anyof = schema.get("anyOf", None)
    if anyof is not None:
        contains_null = False
        for atype in anyof:
            if atype == {"type": "null"}:
                # remove null type
                anyof.remove(atype)
                contains_null = True
            elif "type" not in atype and len(atype) == 0:
                # Handle empty object case
                atype["type"] = "object"

        if len(anyof) == 0:
            # Edge case: response schema with only null type present is invalid in Vertex AI
            raise ValueError(
                "Invalid input: AnyOf schema with only null type is not supported. "
                "Please provide a non-null type."
            )

        if contains_null:
            # set all types to nullable following guidance found here: https://cloud.google.com/vertex-ai/generative-ai/docs/samples/generativeaionvertexai-gemini-controlled-generation-response-schema-3#generativeaionvertexai_gemini_controlled_generation_response_schema_3-python
            for atype in anyof:
                # Remove items field if type is array and items is empty
                if (
                    atype.get("type") == "array"
                    and "items" in atype
                    and not atype["items"]
                ):
                    atype.pop("items")
                atype["nullable"] = True

    properties = schema.get("properties", None)
    if properties is not None:
        for name, value in properties.items():
            convert_anyof_null_to_nullable(value, depth=depth + 1)

    items = schema.get("items", None)
    if items is not None:
        convert_anyof_null_to_nullable(items, depth=depth + 1)


def add_object_type(schema):
    properties = schema.get("properties", None)
    if properties is not None:
        if "required" in schema and schema["required"] is None:
            schema.pop("required", None)
        schema["type"] = "object"
        for name, value in properties.items():
            add_object_type(value)

    items = schema.get("items", None)
    if items is not None:
        add_object_type(items)


def strip_field(schema, field_name: str):
    schema.pop(field_name, None)

    properties = schema.get("properties", None)
    if properties is not None:
        for name, value in properties.items():
            strip_field(value, field_name)

    items = schema.get("items", None)
    if items is not None:
        strip_field(items, field_name)


def _convert_vertex_datetime_to_openai_datetime(vertex_datetime: str) -> int:
    """
    Converts a Vertex AI datetime string to an OpenAI datetime integer

    vertex_datetime: str = "2024-12-04T21:53:12.120184Z"
    returns: int = 1722729192
    """
    from datetime import datetime

    # Parse the ISO format string to datetime object
    dt = datetime.strptime(vertex_datetime, "%Y-%m-%dT%H:%M:%S.%fZ")
    # Convert to Unix timestamp (seconds since epoch)
    return int(dt.timestamp())


def get_vertex_project_id_from_url(url: str) -> Optional[str]:
    """
    Get the vertex project id from the url

    `https://${LOCATION}-aiplatform.googleapis.com/v1/projects/${PROJECT_ID}/locations/${LOCATION}/publishers/google/models/${MODEL_ID}:streamGenerateContent`
    """
    match = re.search(r"/projects/([^/]+)", url)
    return match.group(1) if match else None


def get_vertex_location_from_url(url: str) -> Optional[str]:
    """
    Get the vertex location from the url

    `https://${LOCATION}-aiplatform.googleapis.com/v1/projects/${PROJECT_ID}/locations/${LOCATION}/publishers/google/models/${MODEL_ID}:streamGenerateContent`
    """
    match = re.search(r"/locations/([^/]+)", url)
    return match.group(1) if match else None


def replace_project_and_location_in_route(
    requested_route: str, vertex_project: str, vertex_location: str
) -> str:
    """
    Replace project and location values in the route with the provided values
    """
    # Replace project and location values while keeping route structure
    modified_route = re.sub(
        r"/projects/[^/]+/locations/[^/]+/",
        f"/projects/{vertex_project}/locations/{vertex_location}/",
        requested_route,
    )
    return modified_route


def construct_target_url(
    base_url: str,
    requested_route: str,
    vertex_location: Optional[str],
    vertex_project: Optional[str],
) -> httpx.URL:
    """
    Allow user to specify their own project id / location.

    If missing, use defaults

    Handle cachedContent scenario - https://github.com/BerriAI/litellm/issues/5460

    Constructed Url:
    POST https://LOCATION-aiplatform.googleapis.com/{version}/projects/PROJECT_ID/locations/LOCATION/cachedContents
    """

    new_base_url = httpx.URL(base_url)
    if "locations" in requested_route:  # contains the target project id + location
        if vertex_project and vertex_location:
            requested_route = replace_project_and_location_in_route(
                requested_route, vertex_project, vertex_location
            )
        return new_base_url.copy_with(path=requested_route)

    """
    - Add endpoint version (e.g. v1beta for cachedContent, v1 for rest)
    - Add default project id
    - Add default location
    """
    vertex_version: Literal["v1", "v1beta1"] = "v1"
    if "cachedContent" in requested_route:
        vertex_version = "v1beta1"

    base_requested_route = "{}/projects/{}/locations/{}".format(
        vertex_version, vertex_project, vertex_location
    )

    updated_requested_route = "/" + base_requested_route + requested_route

    updated_url = new_base_url.copy_with(path=updated_requested_route)
    return updated_url


def is_global_only_vertex_model(model: str) -> bool:
    """
    Check if a model is only available in the global region.

    Args:
        model: The model name to check

    Returns:
        True if the model is only available in global region, False otherwise
    """
    from litellm.utils import get_supported_regions

    supported_regions = get_supported_regions(
        model=model, custom_llm_provider="vertex_ai"
    )
    if supported_regions is None:
        return False
    return "global" in supported_regions

# === NexusCore/openenv\Lib\site-packages\pip\_vendor\pygments\formatters\latex.py ===
"""
    pygments.formatters.latex
    ~~~~~~~~~~~~~~~~~~~~~~~~~

    Formatter for LaTeX fancyvrb output.

    :copyright: Copyright 2006-2024 by the Pygments team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

from io import StringIO

from pip._vendor.pygments.formatter import Formatter
from pip._vendor.pygments.lexer import Lexer, do_insertions
from pip._vendor.pygments.token import Token, STANDARD_TYPES
from pip._vendor.pygments.util import get_bool_opt, get_int_opt


__all__ = ['LatexFormatter']


def escape_tex(text, commandprefix):
    return text.replace('\\', '\x00'). \
                replace('{', '\x01'). \
                replace('}', '\x02'). \
                replace('\x00', rf'\{commandprefix}Zbs{{}}'). \
                replace('\x01', rf'\{commandprefix}Zob{{}}'). \
                replace('\x02', rf'\{commandprefix}Zcb{{}}'). \
                replace('^', rf'\{commandprefix}Zca{{}}'). \
                replace('_', rf'\{commandprefix}Zus{{}}'). \
                replace('&', rf'\{commandprefix}Zam{{}}'). \
                replace('<', rf'\{commandprefix}Zlt{{}}'). \
                replace('>', rf'\{commandprefix}Zgt{{}}'). \
                replace('#', rf'\{commandprefix}Zsh{{}}'). \
                replace('%', rf'\{commandprefix}Zpc{{}}'). \
                replace('$', rf'\{commandprefix}Zdl{{}}'). \
                replace('-', rf'\{commandprefix}Zhy{{}}'). \
                replace("'", rf'\{commandprefix}Zsq{{}}'). \
                replace('"', rf'\{commandprefix}Zdq{{}}'). \
                replace('~', rf'\{commandprefix}Zti{{}}')


DOC_TEMPLATE = r'''
\documentclass{%(docclass)s}
\usepackage{fancyvrb}
\usepackage{color}
\usepackage[%(encoding)s]{inputenc}
%(preamble)s

%(styledefs)s

\begin{document}

\section*{%(title)s}

%(code)s
\end{document}
'''

## Small explanation of the mess below :)
#
# The previous version of the LaTeX formatter just assigned a command to
# each token type defined in the current style.  That obviously is
# problematic if the highlighted code is produced for a different style
# than the style commands themselves.
#
# This version works much like the HTML formatter which assigns multiple
# CSS classes to each <span> tag, from the most specific to the least
# specific token type, thus falling back to the parent token type if one
# is not defined.  Here, the classes are there too and use the same short
# forms given in token.STANDARD_TYPES.
#
# Highlighted code now only uses one custom command, which by default is
# \PY and selectable by the commandprefix option (and in addition the
# escapes \PYZat, \PYZlb and \PYZrb which haven't been renamed for
# backwards compatibility purposes).
#
# \PY has two arguments: the classes, separated by +, and the text to
# render in that style.  The classes are resolved into the respective
# style commands by magic, which serves to ignore unknown classes.
#
# The magic macros are:
# * \PY@it, \PY@bf, etc. are unconditionally wrapped around the text
#   to render in \PY@do.  Their definition determines the style.
# * \PY@reset resets \PY@it etc. to do nothing.
# * \PY@toks parses the list of classes, using magic inspired by the
#   keyval package (but modified to use plusses instead of commas
#   because fancyvrb redefines commas inside its environments).
# * \PY@tok processes one class, calling the \PY@tok@classname command
#   if it exists.
# * \PY@tok@classname sets the \PY@it etc. to reflect the chosen style
#   for its class.
# * \PY resets the style, parses the classnames and then calls \PY@do.
#
# Tip: to read this code, print it out in substituted form using e.g.
# >>> print STYLE_TEMPLATE % {'cp': 'PY'}

STYLE_TEMPLATE = r'''
\makeatletter
\def\%(cp)s@reset{\let\%(cp)s@it=\relax \let\%(cp)s@bf=\relax%%
    \let\%(cp)s@ul=\relax \let\%(cp)s@tc=\relax%%
    \let\%(cp)s@bc=\relax \let\%(cp)s@ff=\relax}
\def\%(cp)s@tok#1{\csname %(cp)s@tok@#1\endcsname}
\def\%(cp)s@toks#1+{\ifx\relax#1\empty\else%%
    \%(cp)s@tok{#1}\expandafter\%(cp)s@toks\fi}
\def\%(cp)s@do#1{\%(cp)s@bc{\%(cp)s@tc{\%(cp)s@ul{%%
    \%(cp)s@it{\%(cp)s@bf{\%(cp)s@ff{#1}}}}}}}
\def\%(cp)s#1#2{\%(cp)s@reset\%(cp)s@toks#1+\relax+\%(cp)s@do{#2}}

%(styles)s

\def\%(cp)sZbs{\char`\\}
\def\%(cp)sZus{\char`\_}
\def\%(cp)sZob{\char`\{}
\def\%(cp)sZcb{\char`\}}
\def\%(cp)sZca{\char`\^}
\def\%(cp)sZam{\char`\&}
\def\%(cp)sZlt{\char`\<}
\def\%(cp)sZgt{\char`\>}
\def\%(cp)sZsh{\char`\#}
\def\%(cp)sZpc{\char`\%%}
\def\%(cp)sZdl{\char`\$}
\def\%(cp)sZhy{\char`\-}
\def\%(cp)sZsq{\char`\'}
\def\%(cp)sZdq{\char`\"}
\def\%(cp)sZti{\char`\~}
%% for compatibility with earlier versions
\def\%(cp)sZat{@}
\def\%(cp)sZlb{[}
\def\%(cp)sZrb{]}
\makeatother
'''


def _get_ttype_name(ttype):
    fname = STANDARD_TYPES.get(ttype)
    if fname:
        return fname
    aname = ''
    while fname is None:
        aname = ttype[-1] + aname
        ttype = ttype.parent
        fname = STANDARD_TYPES.get(ttype)
    return fname + aname


class LatexFormatter(Formatter):
    r"""
    Format tokens as LaTeX code. This needs the `fancyvrb` and `color`
    standard packages.

    Without the `full` option, code is formatted as one ``Verbatim``
    environment, like this:

    .. sourcecode:: latex

        \begin{Verbatim}[commandchars=\\\{\}]
        \PY{k}{def }\PY{n+nf}{foo}(\PY{n}{bar}):
            \PY{k}{pass}
        \end{Verbatim}

    Wrapping can be disabled using the `nowrap` option.

    The special command used here (``\PY``) and all the other macros it needs
    are output by the `get_style_defs` method.

    With the `full` option, a complete LaTeX document is output, including
    the command definitions in the preamble.

    The `get_style_defs()` method of a `LatexFormatter` returns a string
    containing ``\def`` commands defining the macros needed inside the
    ``Verbatim`` environments.

    Additional options accepted:

    `nowrap`
        If set to ``True``, don't wrap the tokens at all, not even inside a
        ``\begin{Verbatim}`` environment. This disables most other options
        (default: ``False``).

    `style`
        The style to use, can be a string or a Style subclass (default:
        ``'default'``).

    `full`
        Tells the formatter to output a "full" document, i.e. a complete
        self-contained document (default: ``False``).

    `title`
        If `full` is true, the title that should be used to caption the
        document (default: ``''``).

    `docclass`
        If the `full` option is enabled, this is the document class to use
        (default: ``'article'``).

    `preamble`
        If the `full` option is enabled, this can be further preamble commands,
        e.g. ``\usepackage`` (default: ``''``).

    `linenos`
        If set to ``True``, output line numbers (default: ``False``).

    `linenostart`
        The line number for the first line (default: ``1``).

    `linenostep`
        If set to a number n > 1, only every nth line number is printed.

    `verboptions`
        Additional options given to the Verbatim environment (see the *fancyvrb*
        docs for possible values) (default: ``''``).

    `commandprefix`
        The LaTeX commands used to produce colored output are constructed
        using this prefix and some letters (default: ``'PY'``).

        .. versionadded:: 0.7
        .. versionchanged:: 0.10
           The default is now ``'PY'`` instead of ``'C'``.

    `texcomments`
        If set to ``True``, enables LaTeX comment lines.  That is, LaTex markup
        in comment tokens is not escaped so that LaTeX can render it (default:
        ``False``).

        .. versionadded:: 1.2

    `mathescape`
        If set to ``True``, enables LaTeX math mode escape in comments. That
        is, ``'$...$'`` inside a comment will trigger math mode (default:
        ``False``).

        .. versionadded:: 1.2

    `escapeinside`
        If set to a string of length 2, enables escaping to LaTeX. Text
        delimited by these 2 characters is read as LaTeX code and
        typeset accordingly. It has no effect in string literals. It has
        no effect in comments if `texcomments` or `mathescape` is
        set. (default: ``''``).

        .. versionadded:: 2.0

    `envname`
        Allows you to pick an alternative environment name replacing Verbatim.
        The alternate environment still has to support Verbatim's option syntax.
        (default: ``'Verbatim'``).

        .. versionadded:: 2.0
    """
    name = 'LaTeX'
    aliases = ['latex', 'tex']
    filenames = ['*.tex']

    def __init__(self, **options):
        Formatter.__init__(self, **options)
        self.nowrap = get_bool_opt(options, 'nowrap', False)
        self.docclass = options.get('docclass', 'article')
        self.preamble = options.get('preamble', '')
        self.linenos = get_bool_opt(options, 'linenos', False)
        self.linenostart = abs(get_int_opt(options, 'linenostart', 1))
        self.linenostep = abs(get_int_opt(options, 'linenostep', 1))
        self.verboptions = options.get('verboptions', '')
        self.nobackground = get_bool_opt(options, 'nobackground', False)
        self.commandprefix = options.get('commandprefix', 'PY')
        self.texcomments = get_bool_opt(options, 'texcomments', False)
        self.mathescape = get_bool_opt(options, 'mathescape', False)
        self.escapeinside = options.get('escapeinside', '')
        if len(self.escapeinside) == 2:
            self.left = self.escapeinside[0]
            self.right = self.escapeinside[1]
        else:
            self.escapeinside = ''
        self.envname = options.get('envname', 'Verbatim')

        self._create_stylesheet()

    def _create_stylesheet(self):
        t2n = self.ttype2name = {Token: ''}
        c2d = self.cmd2def = {}
        cp = self.commandprefix

        def rgbcolor(col):
            if col:
                return ','.join(['%.2f' % (int(col[i] + col[i + 1], 16) / 255.0)
                                 for i in (0, 2, 4)])
            else:
                return '1,1,1'

        for ttype, ndef in self.style:
            name = _get_ttype_name(ttype)
            cmndef = ''
            if ndef['bold']:
                cmndef += r'\let\$$@bf=\textbf'
            if ndef['italic']:
                cmndef += r'\let\$$@it=\textit'
            if ndef['underline']:
                cmndef += r'\let\$$@ul=\underline'
            if ndef['roman']:
                cmndef += r'\let\$$@ff=\textrm'
            if ndef['sans']:
                cmndef += r'\let\$$@ff=\textsf'
            if ndef['mono']:
                cmndef += r'\let\$$@ff=\textsf'
            if ndef['color']:
                cmndef += (r'\def\$$@tc##1{{\textcolor[rgb]{{{}}}{{##1}}}}'.format(rgbcolor(ndef['color'])))
            if ndef['border']:
                cmndef += (r'\def\$$@bc##1{{{{\setlength{{\fboxsep}}{{\string -\fboxrule}}'
                           r'\fcolorbox[rgb]{{{}}}{{{}}}{{\strut ##1}}}}}}'.format(rgbcolor(ndef['border']),
                            rgbcolor(ndef['bgcolor'])))
            elif ndef['bgcolor']:
                cmndef += (r'\def\$$@bc##1{{{{\setlength{{\fboxsep}}{{0pt}}'
                           r'\colorbox[rgb]{{{}}}{{\strut ##1}}}}}}'.format(rgbcolor(ndef['bgcolor'])))
            if cmndef == '':
                continue
            cmndef = cmndef.replace('$$', cp)
            t2n[ttype] = name
            c2d[name] = cmndef

    def get_style_defs(self, arg=''):
        """
        Return the command sequences needed to define the commands
        used to format text in the verbatim environment. ``arg`` is ignored.
        """
        cp = self.commandprefix
        styles = []
        for name, definition in self.cmd2def.items():
            styles.append(rf'\@namedef{{{cp}@tok@{name}}}{{{definition}}}')
        return STYLE_TEMPLATE % {'cp': self.commandprefix,
                                 'styles': '\n'.join(styles)}

    def format_unencoded(self, tokensource, outfile):
        # TODO: add support for background colors
        t2n = self.ttype2name
        cp = self.commandprefix

        if self.full:
            realoutfile = outfile
            outfile = StringIO()

        if not self.nowrap:
            outfile.write('\\begin{' + self.envname + '}[commandchars=\\\\\\{\\}')
            if self.linenos:
                start, step = self.linenostart, self.linenostep
                outfile.write(',numbers=left' +
                              (start and ',firstnumber=%d' % start or '') +
                              (step and ',stepnumber=%d' % step or ''))
            if self.mathescape or self.texcomments or self.escapeinside:
                outfile.write(',codes={\\catcode`\\$=3\\catcode`\\^=7'
                              '\\catcode`\\_=8\\relax}')
            if self.verboptions:
                outfile.write(',' + self.verboptions)
            outfile.write(']\n')

        for ttype, value in tokensource:
            if ttype in Token.Comment:
                if self.texcomments:
                    # Try to guess comment starting lexeme and escape it ...
                    start = value[0:1]
                    for i in range(1, len(value)):
                        if start[0] != value[i]:
                            break
                        start += value[i]

                    value = value[len(start):]
                    start = escape_tex(start, cp)

                    # ... but do not escape inside comment.
                    value = start + value
                elif self.mathescape:
                    # Only escape parts not inside a math environment.
                    parts = value.split('$')
                    in_math = False
                    for i, part in enumerate(parts):
                        if not in_math:
                            parts[i] = escape_tex(part, cp)
                        in_math = not in_math
                    value = '$'.join(parts)
                elif self.escapeinside:
                    text = value
                    value = ''
                    while text:
                        a, sep1, text = text.partition(self.left)
                        if sep1:
                            b, sep2, text = text.partition(self.right)
                            if sep2:
                                value += escape_tex(a, cp) + b
                            else:
                                value += escape_tex(a + sep1 + b, cp)
                        else:
                            value += escape_tex(a, cp)
                else:
                    value = escape_tex(value, cp)
            elif ttype not in Token.Escape:
                value = escape_tex(value, cp)
            styles = []
            while ttype is not Token:
                try:
                    styles.append(t2n[ttype])
                except KeyError:
                    # not in current style
                    styles.append(_get_ttype_name(ttype))
                ttype = ttype.parent
            styleval = '+'.join(reversed(styles))
            if styleval:
                spl = value.split('\n')
                for line in spl[:-1]:
                    if line:
                        outfile.write(f"\\{cp}{{{styleval}}}{{{line}}}")
                    outfile.write('\n')
                if spl[-1]:
                    outfile.write(f"\\{cp}{{{styleval}}}{{{spl[-1]}}}")
            else:
                outfile.write(value)

        if not self.nowrap:
            outfile.write('\\end{' + self.envname + '}\n')

        if self.full:
            encoding = self.encoding or 'utf8'
            # map known existings encodings from LaTeX distribution
            encoding = {
                'utf_8': 'utf8',
                'latin_1': 'latin1',
                'iso_8859_1': 'latin1',
            }.get(encoding.replace('-', '_'), encoding)
            realoutfile.write(DOC_TEMPLATE %
                dict(docclass  = self.docclass,
                     preamble  = self.preamble,
                     title     = self.title,
                     encoding  = encoding,
                     styledefs = self.get_style_defs(),
                     code      = outfile.getvalue()))


class LatexEmbeddedLexer(Lexer):
    """
    This lexer takes one lexer as argument, the lexer for the language
    being formatted, and the left and right delimiters for escaped text.

    First everything is scanned using the language lexer to obtain
    strings and comments. All other consecutive tokens are merged and
    the resulting text is scanned for escaped segments, which are given
    the Token.Escape type. Finally text that is not escaped is scanned
    again with the language lexer.
    """
    def __init__(self, left, right, lang, **options):
        self.left = left
        self.right = right
        self.lang = lang
        Lexer.__init__(self, **options)

    def get_tokens_unprocessed(self, text):
        # find and remove all the escape tokens (replace with an empty string)
        # this is very similar to DelegatingLexer.get_tokens_unprocessed.
        buffered = ''
        insertions = []
        insertion_buf = []
        for i, t, v in self._find_safe_escape_tokens(text):
            if t is None:
                if insertion_buf:
                    insertions.append((len(buffered), insertion_buf))
                    insertion_buf = []
                buffered += v
            else:
                insertion_buf.append((i, t, v))
        if insertion_buf:
            insertions.append((len(buffered), insertion_buf))
        return do_insertions(insertions,
                             self.lang.get_tokens_unprocessed(buffered))

    def _find_safe_escape_tokens(self, text):
        """ find escape tokens that are not in strings or comments """
        for i, t, v in self._filter_to(
            self.lang.get_tokens_unprocessed(text),
            lambda t: t in Token.Comment or t in Token.String
        ):
            if t is None:
                for i2, t2, v2 in self._find_escape_tokens(v):
                    yield i + i2, t2, v2
            else:
                yield i, None, v

    def _filter_to(self, it, pred):
        """ Keep only the tokens that match `pred`, merge the others together """
        buf = ''
        idx = 0
        for i, t, v in it:
            if pred(t):
                if buf:
                    yield idx, None, buf
                    buf = ''
                yield i, t, v
            else:
                if not buf:
                    idx = i
                buf += v
        if buf:
            yield idx, None, buf

    def _find_escape_tokens(self, text):
        """ Find escape tokens within text, give token=None otherwise """
        index = 0
        while text:
            a, sep1, text = text.partition(self.left)
            if a:
                yield index, None, a
                index += len(a)
            if sep1:
                b, sep2, text = text.partition(self.right)
                if sep2:
                    yield index + len(sep1), Token.Escape, b
                    index += len(sep1) + len(b) + len(sep2)
                else:
                    yield index, Token.Error, sep1
                    index += len(sep1)
                    text = b

# === NexusCore/openenv\Lib\site-packages\pip\_vendor\urllib3\contrib\pyopenssl.py ===
"""
TLS with SNI_-support for Python 2. Follow these instructions if you would
like to verify TLS certificates in Python 2. Note, the default libraries do
*not* do certificate checking; you need to do additional work to validate
certificates yourself.

This needs the following packages installed:

* `pyOpenSSL`_ (tested with 16.0.0)
* `cryptography`_ (minimum 1.3.4, from pyopenssl)
* `idna`_ (minimum 2.0, from cryptography)

However, pyopenssl depends on cryptography, which depends on idna, so while we
use all three directly here we end up having relatively few packages required.

You can install them with the following command:

.. code-block:: bash

    $ python -m pip install pyopenssl cryptography idna

To activate certificate checking, call
:func:`~urllib3.contrib.pyopenssl.inject_into_urllib3` from your Python code
before you begin making HTTP requests. This can be done in a ``sitecustomize``
module, or at any other time before your application begins using ``urllib3``,
like this:

.. code-block:: python

    try:
        import pip._vendor.urllib3.contrib.pyopenssl as pyopenssl
        pyopenssl.inject_into_urllib3()
    except ImportError:
        pass

Now you can use :mod:`urllib3` as you normally would, and it will support SNI
when the required modules are installed.

Activating this module also has the positive side effect of disabling SSL/TLS
compression in Python 2 (see `CRIME attack`_).

.. _sni: https://en.wikipedia.org/wiki/Server_Name_Indication
.. _crime attack: https://en.wikipedia.org/wiki/CRIME_(security_exploit)
.. _pyopenssl: https://www.pyopenssl.org
.. _cryptography: https://cryptography.io
.. _idna: https://github.com/kjd/idna
"""
from __future__ import absolute_import

import OpenSSL.crypto
import OpenSSL.SSL
from cryptography import x509
from cryptography.hazmat.backends.openssl import backend as openssl_backend

try:
    from cryptography.x509 import UnsupportedExtension
except ImportError:
    # UnsupportedExtension is gone in cryptography >= 2.1.0
    class UnsupportedExtension(Exception):
        pass


from io import BytesIO
from socket import error as SocketError
from socket import timeout

try:  # Platform-specific: Python 2
    from socket import _fileobject
except ImportError:  # Platform-specific: Python 3
    _fileobject = None
    from ..packages.backports.makefile import backport_makefile

import logging
import ssl
import sys
import warnings

from .. import util
from ..packages import six
from ..util.ssl_ import PROTOCOL_TLS_CLIENT

warnings.warn(
    "'urllib3.contrib.pyopenssl' module is deprecated and will be removed "
    "in a future release of urllib3 2.x. Read more in this issue: "
    "https://github.com/urllib3/urllib3/issues/2680",
    category=DeprecationWarning,
    stacklevel=2,
)

__all__ = ["inject_into_urllib3", "extract_from_urllib3"]

# SNI always works.
HAS_SNI = True

# Map from urllib3 to PyOpenSSL compatible parameter-values.
_openssl_versions = {
    util.PROTOCOL_TLS: OpenSSL.SSL.SSLv23_METHOD,
    PROTOCOL_TLS_CLIENT: OpenSSL.SSL.SSLv23_METHOD,
    ssl.PROTOCOL_TLSv1: OpenSSL.SSL.TLSv1_METHOD,
}

if hasattr(ssl, "PROTOCOL_SSLv3") and hasattr(OpenSSL.SSL, "SSLv3_METHOD"):
    _openssl_versions[ssl.PROTOCOL_SSLv3] = OpenSSL.SSL.SSLv3_METHOD

if hasattr(ssl, "PROTOCOL_TLSv1_1") and hasattr(OpenSSL.SSL, "TLSv1_1_METHOD"):
    _openssl_versions[ssl.PROTOCOL_TLSv1_1] = OpenSSL.SSL.TLSv1_1_METHOD

if hasattr(ssl, "PROTOCOL_TLSv1_2") and hasattr(OpenSSL.SSL, "TLSv1_2_METHOD"):
    _openssl_versions[ssl.PROTOCOL_TLSv1_2] = OpenSSL.SSL.TLSv1_2_METHOD


_stdlib_to_openssl_verify = {
    ssl.CERT_NONE: OpenSSL.SSL.VERIFY_NONE,
    ssl.CERT_OPTIONAL: OpenSSL.SSL.VERIFY_PEER,
    ssl.CERT_REQUIRED: OpenSSL.SSL.VERIFY_PEER
    + OpenSSL.SSL.VERIFY_FAIL_IF_NO_PEER_CERT,
}
_openssl_to_stdlib_verify = dict((v, k) for k, v in _stdlib_to_openssl_verify.items())

# OpenSSL will only write 16K at a time
SSL_WRITE_BLOCKSIZE = 16384

orig_util_HAS_SNI = util.HAS_SNI
orig_util_SSLContext = util.ssl_.SSLContext


log = logging.getLogger(__name__)


def inject_into_urllib3():
    "Monkey-patch urllib3 with PyOpenSSL-backed SSL-support."

    _validate_dependencies_met()

    util.SSLContext = PyOpenSSLContext
    util.ssl_.SSLContext = PyOpenSSLContext
    util.HAS_SNI = HAS_SNI
    util.ssl_.HAS_SNI = HAS_SNI
    util.IS_PYOPENSSL = True
    util.ssl_.IS_PYOPENSSL = True


def extract_from_urllib3():
    "Undo monkey-patching by :func:`inject_into_urllib3`."

    util.SSLContext = orig_util_SSLContext
    util.ssl_.SSLContext = orig_util_SSLContext
    util.HAS_SNI = orig_util_HAS_SNI
    util.ssl_.HAS_SNI = orig_util_HAS_SNI
    util.IS_PYOPENSSL = False
    util.ssl_.IS_PYOPENSSL = False


def _validate_dependencies_met():
    """
    Verifies that PyOpenSSL's package-level dependencies have been met.
    Throws `ImportError` if they are not met.
    """
    # Method added in `cryptography==1.1`; not available in older versions
    from cryptography.x509.extensions import Extensions

    if getattr(Extensions, "get_extension_for_class", None) is None:
        raise ImportError(
            "'cryptography' module missing required functionality.  "
            "Try upgrading to v1.3.4 or newer."
        )

    # pyOpenSSL 0.14 and above use cryptography for OpenSSL bindings. The _x509
    # attribute is only present on those versions.
    from OpenSSL.crypto import X509

    x509 = X509()
    if getattr(x509, "_x509", None) is None:
        raise ImportError(
            "'pyOpenSSL' module missing required functionality. "
            "Try upgrading to v0.14 or newer."
        )


def _dnsname_to_stdlib(name):
    """
    Converts a dNSName SubjectAlternativeName field to the form used by the
    standard library on the given Python version.

    Cryptography produces a dNSName as a unicode string that was idna-decoded
    from ASCII bytes. We need to idna-encode that string to get it back, and
    then on Python 3 we also need to convert to unicode via UTF-8 (the stdlib
    uses PyUnicode_FromStringAndSize on it, which decodes via UTF-8).

    If the name cannot be idna-encoded then we return None signalling that
    the name given should be skipped.
    """

    def idna_encode(name):
        """
        Borrowed wholesale from the Python Cryptography Project. It turns out
        that we can't just safely call `idna.encode`: it can explode for
        wildcard names. This avoids that problem.
        """
        from pip._vendor import idna

        try:
            for prefix in [u"*.", u"."]:
                if name.startswith(prefix):
                    name = name[len(prefix) :]
                    return prefix.encode("ascii") + idna.encode(name)
            return idna.encode(name)
        except idna.core.IDNAError:
            return None

    # Don't send IPv6 addresses through the IDNA encoder.
    if ":" in name:
        return name

    name = idna_encode(name)
    if name is None:
        return None
    elif sys.version_info >= (3, 0):
        name = name.decode("utf-8")
    return name


def get_subj_alt_name(peer_cert):
    """
    Given an PyOpenSSL certificate, provides all the subject alternative names.
    """
    # Pass the cert to cryptography, which has much better APIs for this.
    if hasattr(peer_cert, "to_cryptography"):
        cert = peer_cert.to_cryptography()
    else:
        der = OpenSSL.crypto.dump_certificate(OpenSSL.crypto.FILETYPE_ASN1, peer_cert)
        cert = x509.load_der_x509_certificate(der, openssl_backend)

    # We want to find the SAN extension. Ask Cryptography to locate it (it's
    # faster than looping in Python)
    try:
        ext = cert.extensions.get_extension_for_class(x509.SubjectAlternativeName).value
    except x509.ExtensionNotFound:
        # No such extension, return the empty list.
        return []
    except (
        x509.DuplicateExtension,
        UnsupportedExtension,
        x509.UnsupportedGeneralNameType,
        UnicodeError,
    ) as e:
        # A problem has been found with the quality of the certificate. Assume
        # no SAN field is present.
        log.warning(
            "A problem was encountered with the certificate that prevented "
            "urllib3 from finding the SubjectAlternativeName field. This can "
            "affect certificate validation. The error was %s",
            e,
        )
        return []

    # We want to return dNSName and iPAddress fields. We need to cast the IPs
    # back to strings because the match_hostname function wants them as
    # strings.
    # Sadly the DNS names need to be idna encoded and then, on Python 3, UTF-8
    # decoded. This is pretty frustrating, but that's what the standard library
    # does with certificates, and so we need to attempt to do the same.
    # We also want to skip over names which cannot be idna encoded.
    names = [
        ("DNS", name)
        for name in map(_dnsname_to_stdlib, ext.get_values_for_type(x509.DNSName))
        if name is not None
    ]
    names.extend(
        ("IP Address", str(name)) for name in ext.get_values_for_type(x509.IPAddress)
    )

    return names


class WrappedSocket(object):
    """API-compatibility wrapper for Python OpenSSL's Connection-class.

    Note: _makefile_refs, _drop() and _reuse() are needed for the garbage
    collector of pypy.
    """

    def __init__(self, connection, socket, suppress_ragged_eofs=True):
        self.connection = connection
        self.socket = socket
        self.suppress_ragged_eofs = suppress_ragged_eofs
        self._makefile_refs = 0
        self._closed = False

    def fileno(self):
        return self.socket.fileno()

    # Copy-pasted from Python 3.5 source code
    def _decref_socketios(self):
        if self._makefile_refs > 0:
            self._makefile_refs -= 1
        if self._closed:
            self.close()

    def recv(self, *args, **kwargs):
        try:
            data = self.connection.recv(*args, **kwargs)
        except OpenSSL.SSL.SysCallError as e:
            if self.suppress_ragged_eofs and e.args == (-1, "Unexpected EOF"):
                return b""
            else:
                raise SocketError(str(e))
        except OpenSSL.SSL.ZeroReturnError:
            if self.connection.get_shutdown() == OpenSSL.SSL.RECEIVED_SHUTDOWN:
                return b""
            else:
                raise
        except OpenSSL.SSL.WantReadError:
            if not util.wait_for_read(self.socket, self.socket.gettimeout()):
                raise timeout("The read operation timed out")
            else:
                return self.recv(*args, **kwargs)

        # TLS 1.3 post-handshake authentication
        except OpenSSL.SSL.Error as e:
            raise ssl.SSLError("read error: %r" % e)
        else:
            return data

    def recv_into(self, *args, **kwargs):
        try:
            return self.connection.recv_into(*args, **kwargs)
        except OpenSSL.SSL.SysCallError as e:
            if self.suppress_ragged_eofs and e.args == (-1, "Unexpected EOF"):
                return 0
            else:
                raise SocketError(str(e))
        except OpenSSL.SSL.ZeroReturnError:
            if self.connection.get_shutdown() == OpenSSL.SSL.RECEIVED_SHUTDOWN:
                return 0
            else:
                raise
        except OpenSSL.SSL.WantReadError:
            if not util.wait_for_read(self.socket, self.socket.gettimeout()):
                raise timeout("The read operation timed out")
            else:
                return self.recv_into(*args, **kwargs)

        # TLS 1.3 post-handshake authentication
        except OpenSSL.SSL.Error as e:
            raise ssl.SSLError("read error: %r" % e)

    def settimeout(self, timeout):
        return self.socket.settimeout(timeout)

    def _send_until_done(self, data):
        while True:
            try:
                return self.connection.send(data)
            except OpenSSL.SSL.WantWriteError:
                if not util.wait_for_write(self.socket, self.socket.gettimeout()):
                    raise timeout()
                continue
            except OpenSSL.SSL.SysCallError as e:
                raise SocketError(str(e))

    def sendall(self, data):
        total_sent = 0
        while total_sent < len(data):
            sent = self._send_until_done(
                data[total_sent : total_sent + SSL_WRITE_BLOCKSIZE]
            )
            total_sent += sent

    def shutdown(self):
        # FIXME rethrow compatible exceptions should we ever use this
        self.connection.shutdown()

    def close(self):
        if self._makefile_refs < 1:
            try:
                self._closed = True
                return self.connection.close()
            except OpenSSL.SSL.Error:
                return
        else:
            self._makefile_refs -= 1

    def getpeercert(self, binary_form=False):
        x509 = self.connection.get_peer_certificate()

        if not x509:
            return x509

        if binary_form:
            return OpenSSL.crypto.dump_certificate(OpenSSL.crypto.FILETYPE_ASN1, x509)

        return {
            "subject": ((("commonName", x509.get_subject().CN),),),
            "subjectAltName": get_subj_alt_name(x509),
        }

    def version(self):
        return self.connection.get_protocol_version_name()

    def _reuse(self):
        self._makefile_refs += 1

    def _drop(self):
        if self._makefile_refs < 1:
            self.close()
        else:
            self._makefile_refs -= 1


if _fileobject:  # Platform-specific: Python 2

    def makefile(self, mode, bufsize=-1):
        self._makefile_refs += 1
        return _fileobject(self, mode, bufsize, close=True)

else:  # Platform-specific: Python 3
    makefile = backport_makefile

WrappedSocket.makefile = makefile


class PyOpenSSLContext(object):
    """
    I am a wrapper class for the PyOpenSSL ``Context`` object. I am responsible
    for translating the interface of the standard library ``SSLContext`` object
    to calls into PyOpenSSL.
    """

    def __init__(self, protocol):
        self.protocol = _openssl_versions[protocol]
        self._ctx = OpenSSL.SSL.Context(self.protocol)
        self._options = 0
        self.check_hostname = False

    @property
    def options(self):
        return self._options

    @options.setter
    def options(self, value):
        self._options = value
        self._ctx.set_options(value)

    @property
    def verify_mode(self):
        return _openssl_to_stdlib_verify[self._ctx.get_verify_mode()]

    @verify_mode.setter
    def verify_mode(self, value):
        self._ctx.set_verify(_stdlib_to_openssl_verify[value], _verify_callback)

    def set_default_verify_paths(self):
        self._ctx.set_default_verify_paths()

    def set_ciphers(self, ciphers):
        if isinstance(ciphers, six.text_type):
            ciphers = ciphers.encode("utf-8")
        self._ctx.set_cipher_list(ciphers)

    def load_verify_locations(self, cafile=None, capath=None, cadata=None):
        if cafile is not None:
            cafile = cafile.encode("utf-8")
        if capath is not None:
            capath = capath.encode("utf-8")
        try:
            self._ctx.load_verify_locations(cafile, capath)
            if cadata is not None:
                self._ctx.load_verify_locations(BytesIO(cadata))
        except OpenSSL.SSL.Error as e:
            raise ssl.SSLError("unable to load trusted certificates: %r" % e)

    def load_cert_chain(self, certfile, keyfile=None, password=None):
        self._ctx.use_certificate_chain_file(certfile)
        if password is not None:
            if not isinstance(password, six.binary_type):
                password = password.encode("utf-8")
            self._ctx.set_passwd_cb(lambda *_: password)
        self._ctx.use_privatekey_file(keyfile or certfile)

    def set_alpn_protocols(self, protocols):
        protocols = [six.ensure_binary(p) for p in protocols]
        return self._ctx.set_alpn_protos(protocols)

    def wrap_socket(
        self,
        sock,
        server_side=False,
        do_handshake_on_connect=True,
        suppress_ragged_eofs=True,
        server_hostname=None,
    ):
        cnx = OpenSSL.SSL.Connection(self._ctx, sock)

        if isinstance(server_hostname, six.text_type):  # Platform-specific: Python 3
            server_hostname = server_hostname.encode("utf-8")

        if server_hostname is not None:
            cnx.set_tlsext_host_name(server_hostname)

        cnx.set_connect_state()

        while True:
            try:
                cnx.do_handshake()
            except OpenSSL.SSL.WantReadError:
                if not util.wait_for_read(sock, sock.gettimeout()):
                    raise timeout("select timed out")
                continue
            except OpenSSL.SSL.Error as e:
                raise ssl.SSLError("bad handshake: %r" % e)
            break

        return WrappedSocket(cnx, sock)


def _verify_callback(cnx, x509, err_no, err_depth, return_code):
    return err_no == 0

# === NexusCore/openenv\Lib\site-packages\pygments\formatters\latex.py ===
"""
    pygments.formatters.latex
    ~~~~~~~~~~~~~~~~~~~~~~~~~

    Formatter for LaTeX fancyvrb output.

    :copyright: Copyright 2006-2025 by the Pygments team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

from io import StringIO

from pygments.formatter import Formatter
from pygments.lexer import Lexer, do_insertions
from pygments.token import Token, STANDARD_TYPES
from pygments.util import get_bool_opt, get_int_opt


__all__ = ['LatexFormatter']


def escape_tex(text, commandprefix):
    return text.replace('\\', '\x00'). \
                replace('{', '\x01'). \
                replace('}', '\x02'). \
                replace('\x00', rf'\{commandprefix}Zbs{{}}'). \
                replace('\x01', rf'\{commandprefix}Zob{{}}'). \
                replace('\x02', rf'\{commandprefix}Zcb{{}}'). \
                replace('^', rf'\{commandprefix}Zca{{}}'). \
                replace('_', rf'\{commandprefix}Zus{{}}'). \
                replace('&', rf'\{commandprefix}Zam{{}}'). \
                replace('<', rf'\{commandprefix}Zlt{{}}'). \
                replace('>', rf'\{commandprefix}Zgt{{}}'). \
                replace('#', rf'\{commandprefix}Zsh{{}}'). \
                replace('%', rf'\{commandprefix}Zpc{{}}'). \
                replace('$', rf'\{commandprefix}Zdl{{}}'). \
                replace('-', rf'\{commandprefix}Zhy{{}}'). \
                replace("'", rf'\{commandprefix}Zsq{{}}'). \
                replace('"', rf'\{commandprefix}Zdq{{}}'). \
                replace('~', rf'\{commandprefix}Zti{{}}')


DOC_TEMPLATE = r'''
\documentclass{%(docclass)s}
\usepackage{fancyvrb}
\usepackage{color}
\usepackage[%(encoding)s]{inputenc}
%(preamble)s

%(styledefs)s

\begin{document}

\section*{%(title)s}

%(code)s
\end{document}
'''

## Small explanation of the mess below :)
#
# The previous version of the LaTeX formatter just assigned a command to
# each token type defined in the current style.  That obviously is
# problematic if the highlighted code is produced for a different style
# than the style commands themselves.
#
# This version works much like the HTML formatter which assigns multiple
# CSS classes to each <span> tag, from the most specific to the least
# specific token type, thus falling back to the parent token type if one
# is not defined.  Here, the classes are there too and use the same short
# forms given in token.STANDARD_TYPES.
#
# Highlighted code now only uses one custom command, which by default is
# \PY and selectable by the commandprefix option (and in addition the
# escapes \PYZat, \PYZlb and \PYZrb which haven't been renamed for
# backwards compatibility purposes).
#
# \PY has two arguments: the classes, separated by +, and the text to
# render in that style.  The classes are resolved into the respective
# style commands by magic, which serves to ignore unknown classes.
#
# The magic macros are:
# * \PY@it, \PY@bf, etc. are unconditionally wrapped around the text
#   to render in \PY@do.  Their definition determines the style.
# * \PY@reset resets \PY@it etc. to do nothing.
# * \PY@toks parses the list of classes, using magic inspired by the
#   keyval package (but modified to use plusses instead of commas
#   because fancyvrb redefines commas inside its environments).
# * \PY@tok processes one class, calling the \PY@tok@classname command
#   if it exists.
# * \PY@tok@classname sets the \PY@it etc. to reflect the chosen style
#   for its class.
# * \PY resets the style, parses the classnames and then calls \PY@do.
#
# Tip: to read this code, print it out in substituted form using e.g.
# >>> print STYLE_TEMPLATE % {'cp': 'PY'}

STYLE_TEMPLATE = r'''
\makeatletter
\def\%(cp)s@reset{\let\%(cp)s@it=\relax \let\%(cp)s@bf=\relax%%
    \let\%(cp)s@ul=\relax \let\%(cp)s@tc=\relax%%
    \let\%(cp)s@bc=\relax \let\%(cp)s@ff=\relax}
\def\%(cp)s@tok#1{\csname %(cp)s@tok@#1\endcsname}
\def\%(cp)s@toks#1+{\ifx\relax#1\empty\else%%
    \%(cp)s@tok{#1}\expandafter\%(cp)s@toks\fi}
\def\%(cp)s@do#1{\%(cp)s@bc{\%(cp)s@tc{\%(cp)s@ul{%%
    \%(cp)s@it{\%(cp)s@bf{\%(cp)s@ff{#1}}}}}}}
\def\%(cp)s#1#2{\%(cp)s@reset\%(cp)s@toks#1+\relax+\%(cp)s@do{#2}}

%(styles)s

\def\%(cp)sZbs{\char`\\}
\def\%(cp)sZus{\char`\_}
\def\%(cp)sZob{\char`\{}
\def\%(cp)sZcb{\char`\}}
\def\%(cp)sZca{\char`\^}
\def\%(cp)sZam{\char`\&}
\def\%(cp)sZlt{\char`\<}
\def\%(cp)sZgt{\char`\>}
\def\%(cp)sZsh{\char`\#}
\def\%(cp)sZpc{\char`\%%}
\def\%(cp)sZdl{\char`\$}
\def\%(cp)sZhy{\char`\-}
\def\%(cp)sZsq{\char`\'}
\def\%(cp)sZdq{\char`\"}
\def\%(cp)sZti{\char`\~}
%% for compatibility with earlier versions
\def\%(cp)sZat{@}
\def\%(cp)sZlb{[}
\def\%(cp)sZrb{]}
\makeatother
'''


def _get_ttype_name(ttype):
    fname = STANDARD_TYPES.get(ttype)
    if fname:
        return fname
    aname = ''
    while fname is None:
        aname = ttype[-1] + aname
        ttype = ttype.parent
        fname = STANDARD_TYPES.get(ttype)
    return fname + aname


class LatexFormatter(Formatter):
    r"""
    Format tokens as LaTeX code. This needs the `fancyvrb` and `color`
    standard packages.

    Without the `full` option, code is formatted as one ``Verbatim``
    environment, like this:

    .. sourcecode:: latex

        \begin{Verbatim}[commandchars=\\\{\}]
        \PY{k}{def }\PY{n+nf}{foo}(\PY{n}{bar}):
            \PY{k}{pass}
        \end{Verbatim}

    Wrapping can be disabled using the `nowrap` option.

    The special command used here (``\PY``) and all the other macros it needs
    are output by the `get_style_defs` method.

    With the `full` option, a complete LaTeX document is output, including
    the command definitions in the preamble.

    The `get_style_defs()` method of a `LatexFormatter` returns a string
    containing ``\def`` commands defining the macros needed inside the
    ``Verbatim`` environments.

    Additional options accepted:

    `nowrap`
        If set to ``True``, don't wrap the tokens at all, not even inside a
        ``\begin{Verbatim}`` environment. This disables most other options
        (default: ``False``).

    `style`
        The style to use, can be a string or a Style subclass (default:
        ``'default'``).

    `full`
        Tells the formatter to output a "full" document, i.e. a complete
        self-contained document (default: ``False``).

    `title`
        If `full` is true, the title that should be used to caption the
        document (default: ``''``).

    `docclass`
        If the `full` option is enabled, this is the document class to use
        (default: ``'article'``).

    `preamble`
        If the `full` option is enabled, this can be further preamble commands,
        e.g. ``\usepackage`` (default: ``''``).

    `linenos`
        If set to ``True``, output line numbers (default: ``False``).

    `linenostart`
        The line number for the first line (default: ``1``).

    `linenostep`
        If set to a number n > 1, only every nth line number is printed.

    `verboptions`
        Additional options given to the Verbatim environment (see the *fancyvrb*
        docs for possible values) (default: ``''``).

    `commandprefix`
        The LaTeX commands used to produce colored output are constructed
        using this prefix and some letters (default: ``'PY'``).

        .. versionadded:: 0.7
        .. versionchanged:: 0.10
           The default is now ``'PY'`` instead of ``'C'``.

    `texcomments`
        If set to ``True``, enables LaTeX comment lines.  That is, LaTex markup
        in comment tokens is not escaped so that LaTeX can render it (default:
        ``False``).

        .. versionadded:: 1.2

    `mathescape`
        If set to ``True``, enables LaTeX math mode escape in comments. That
        is, ``'$...$'`` inside a comment will trigger math mode (default:
        ``False``).

        .. versionadded:: 1.2

    `escapeinside`
        If set to a string of length 2, enables escaping to LaTeX. Text
        delimited by these 2 characters is read as LaTeX code and
        typeset accordingly. It has no effect in string literals. It has
        no effect in comments if `texcomments` or `mathescape` is
        set. (default: ``''``).

        .. versionadded:: 2.0

    `envname`
        Allows you to pick an alternative environment name replacing Verbatim.
        The alternate environment still has to support Verbatim's option syntax.
        (default: ``'Verbatim'``).

        .. versionadded:: 2.0
    """
    name = 'LaTeX'
    aliases = ['latex', 'tex']
    filenames = ['*.tex']

    def __init__(self, **options):
        Formatter.__init__(self, **options)
        self.nowrap = get_bool_opt(options, 'nowrap', False)
        self.docclass = options.get('docclass', 'article')
        self.preamble = options.get('preamble', '')
        self.linenos = get_bool_opt(options, 'linenos', False)
        self.linenostart = abs(get_int_opt(options, 'linenostart', 1))
        self.linenostep = abs(get_int_opt(options, 'linenostep', 1))
        self.verboptions = options.get('verboptions', '')
        self.nobackground = get_bool_opt(options, 'nobackground', False)
        self.commandprefix = options.get('commandprefix', 'PY')
        self.texcomments = get_bool_opt(options, 'texcomments', False)
        self.mathescape = get_bool_opt(options, 'mathescape', False)
        self.escapeinside = options.get('escapeinside', '')
        if len(self.escapeinside) == 2:
            self.left = self.escapeinside[0]
            self.right = self.escapeinside[1]
        else:
            self.escapeinside = ''
        self.envname = options.get('envname', 'Verbatim')

        self._create_stylesheet()

    def _create_stylesheet(self):
        t2n = self.ttype2name = {Token: ''}
        c2d = self.cmd2def = {}
        cp = self.commandprefix

        def rgbcolor(col):
            if col:
                return ','.join(['%.2f' % (int(col[i] + col[i + 1], 16) / 255.0)
                                 for i in (0, 2, 4)])
            else:
                return '1,1,1'

        for ttype, ndef in self.style:
            name = _get_ttype_name(ttype)
            cmndef = ''
            if ndef['bold']:
                cmndef += r'\let\$$@bf=\textbf'
            if ndef['italic']:
                cmndef += r'\let\$$@it=\textit'
            if ndef['underline']:
                cmndef += r'\let\$$@ul=\underline'
            if ndef['roman']:
                cmndef += r'\let\$$@ff=\textrm'
            if ndef['sans']:
                cmndef += r'\let\$$@ff=\textsf'
            if ndef['mono']:
                cmndef += r'\let\$$@ff=\textsf'
            if ndef['color']:
                cmndef += (r'\def\$$@tc##1{{\textcolor[rgb]{{{}}}{{##1}}}}'.format(rgbcolor(ndef['color'])))
            if ndef['border']:
                cmndef += (r'\def\$$@bc##1{{{{\setlength{{\fboxsep}}{{\string -\fboxrule}}'
                           r'\fcolorbox[rgb]{{{}}}{{{}}}{{\strut ##1}}}}}}'.format(rgbcolor(ndef['border']),
                            rgbcolor(ndef['bgcolor'])))
            elif ndef['bgcolor']:
                cmndef += (r'\def\$$@bc##1{{{{\setlength{{\fboxsep}}{{0pt}}'
                           r'\colorbox[rgb]{{{}}}{{\strut ##1}}}}}}'.format(rgbcolor(ndef['bgcolor'])))
            if cmndef == '':
                continue
            cmndef = cmndef.replace('$$', cp)
            t2n[ttype] = name
            c2d[name] = cmndef

    def get_style_defs(self, arg=''):
        """
        Return the command sequences needed to define the commands
        used to format text in the verbatim environment. ``arg`` is ignored.
        """
        cp = self.commandprefix
        styles = []
        for name, definition in self.cmd2def.items():
            styles.append(rf'\@namedef{{{cp}@tok@{name}}}{{{definition}}}')
        return STYLE_TEMPLATE % {'cp': self.commandprefix,
                                 'styles': '\n'.join(styles)}

    def format_unencoded(self, tokensource, outfile):
        # TODO: add support for background colors
        t2n = self.ttype2name
        cp = self.commandprefix

        if self.full:
            realoutfile = outfile
            outfile = StringIO()

        if not self.nowrap:
            outfile.write('\\begin{' + self.envname + '}[commandchars=\\\\\\{\\}')
            if self.linenos:
                start, step = self.linenostart, self.linenostep
                outfile.write(',numbers=left' +
                              (start and ',firstnumber=%d' % start or '') +
                              (step and ',stepnumber=%d' % step or ''))
            if self.mathescape or self.texcomments or self.escapeinside:
                outfile.write(',codes={\\catcode`\\$=3\\catcode`\\^=7'
                              '\\catcode`\\_=8\\relax}')
            if self.verboptions:
                outfile.write(',' + self.verboptions)
            outfile.write(']\n')

        for ttype, value in tokensource:
            if ttype in Token.Comment:
                if self.texcomments:
                    # Try to guess comment starting lexeme and escape it ...
                    start = value[0:1]
                    for i in range(1, len(value)):
                        if start[0] != value[i]:
                            break
                        start += value[i]

                    value = value[len(start):]
                    start = escape_tex(start, cp)

                    # ... but do not escape inside comment.
                    value = start + value
                elif self.mathescape:
                    # Only escape parts not inside a math environment.
                    parts = value.split('$')
                    in_math = False
                    for i, part in enumerate(parts):
                        if not in_math:
                            parts[i] = escape_tex(part, cp)
                        in_math = not in_math
                    value = '$'.join(parts)
                elif self.escapeinside:
                    text = value
                    value = ''
                    while text:
                        a, sep1, text = text.partition(self.left)
                        if sep1:
                            b, sep2, text = text.partition(self.right)
                            if sep2:
                                value += escape_tex(a, cp) + b
                            else:
                                value += escape_tex(a + sep1 + b, cp)
                        else:
                            value += escape_tex(a, cp)
                else:
                    value = escape_tex(value, cp)
            elif ttype not in Token.Escape:
                value = escape_tex(value, cp)
            styles = []
            while ttype is not Token:
                try:
                    styles.append(t2n[ttype])
                except KeyError:
                    # not in current style
                    styles.append(_get_ttype_name(ttype))
                ttype = ttype.parent
            styleval = '+'.join(reversed(styles))
            if styleval:
                spl = value.split('\n')
                for line in spl[:-1]:
                    if line:
                        outfile.write(f"\\{cp}{{{styleval}}}{{{line}}}")
                    outfile.write('\n')
                if spl[-1]:
                    outfile.write(f"\\{cp}{{{styleval}}}{{{spl[-1]}}}")
            else:
                outfile.write(value)

        if not self.nowrap:
            outfile.write('\\end{' + self.envname + '}\n')

        if self.full:
            encoding = self.encoding or 'utf8'
            # map known existings encodings from LaTeX distribution
            encoding = {
                'utf_8': 'utf8',
                'latin_1': 'latin1',
                'iso_8859_1': 'latin1',
            }.get(encoding.replace('-', '_'), encoding)
            realoutfile.write(DOC_TEMPLATE %
                dict(docclass  = self.docclass,
                     preamble  = self.preamble,
                     title     = self.title,
                     encoding  = encoding,
                     styledefs = self.get_style_defs(),
                     code      = outfile.getvalue()))


class LatexEmbeddedLexer(Lexer):
    """
    This lexer takes one lexer as argument, the lexer for the language
    being formatted, and the left and right delimiters for escaped text.

    First everything is scanned using the language lexer to obtain
    strings and comments. All other consecutive tokens are merged and
    the resulting text is scanned for escaped segments, which are given
    the Token.Escape type. Finally text that is not escaped is scanned
    again with the language lexer.
    """
    def __init__(self, left, right, lang, **options):
        self.left = left
        self.right = right
        self.lang = lang
        Lexer.__init__(self, **options)

    def get_tokens_unprocessed(self, text):
        # find and remove all the escape tokens (replace with an empty string)
        # this is very similar to DelegatingLexer.get_tokens_unprocessed.
        buffered = ''
        insertions = []
        insertion_buf = []
        for i, t, v in self._find_safe_escape_tokens(text):
            if t is None:
                if insertion_buf:
                    insertions.append((len(buffered), insertion_buf))
                    insertion_buf = []
                buffered += v
            else:
                insertion_buf.append((i, t, v))
        if insertion_buf:
            insertions.append((len(buffered), insertion_buf))
        return do_insertions(insertions,
                             self.lang.get_tokens_unprocessed(buffered))

    def _find_safe_escape_tokens(self, text):
        """ find escape tokens that are not in strings or comments """
        for i, t, v in self._filter_to(
            self.lang.get_tokens_unprocessed(text),
            lambda t: t in Token.Comment or t in Token.String
        ):
            if t is None:
                for i2, t2, v2 in self._find_escape_tokens(v):
                    yield i + i2, t2, v2
            else:
                yield i, None, v

    def _filter_to(self, it, pred):
        """ Keep only the tokens that match `pred`, merge the others together """
        buf = ''
        idx = 0
        for i, t, v in it:
            if pred(t):
                if buf:
                    yield idx, None, buf
                    buf = ''
                yield i, t, v
            else:
                if not buf:
                    idx = i
                buf += v
        if buf:
            yield idx, None, buf

    def _find_escape_tokens(self, text):
        """ Find escape tokens within text, give token=None otherwise """
        index = 0
        while text:
            a, sep1, text = text.partition(self.left)
            if a:
                yield index, None, a
                index += len(a)
            if sep1:
                b, sep2, text = text.partition(self.right)
                if sep2:
                    yield index + len(sep1), Token.Escape, b
                    index += len(sep1) + len(b) + len(sep2)
                else:
                    yield index, Token.Error, sep1
                    index += len(sep1)
                    text = b

# === NexusCore/openenv\Lib\site-packages\pygments\lexers\ruby.py ===
"""
    pygments.lexers.ruby
    ~~~~~~~~~~~~~~~~~~~~

    Lexers for Ruby and related languages.

    :copyright: Copyright 2006-2025 by the Pygments team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

import re

from pygments.lexer import Lexer, RegexLexer, ExtendedRegexLexer, include, \
    bygroups, default, LexerContext, do_insertions, words, line_re
from pygments.token import Text, Comment, Operator, Keyword, Name, String, \
    Number, Punctuation, Error, Generic, Whitespace
from pygments.util import shebang_matches

__all__ = ['RubyLexer', 'RubyConsoleLexer', 'FancyLexer']


RUBY_OPERATORS = (
    '*', '**', '-', '+', '-@', '+@', '/', '%', '&', '|', '^', '`', '~',
    '[]', '[]=', '<<', '>>', '<', '<>', '<=>', '>', '>=', '==', '==='
)


class RubyLexer(ExtendedRegexLexer):
    """
    For Ruby source code.
    """

    name = 'Ruby'
    url = 'http://www.ruby-lang.org'
    aliases = ['ruby', 'rb', 'duby']
    filenames = ['*.rb', '*.rbw', 'Rakefile', '*.rake', '*.gemspec',
                 '*.rbx', '*.duby', 'Gemfile', 'Vagrantfile']
    mimetypes = ['text/x-ruby', 'application/x-ruby']
    version_added = ''

    flags = re.DOTALL | re.MULTILINE

    def heredoc_callback(self, match, ctx):
        # okay, this is the hardest part of parsing Ruby...
        # match: 1 = <<[-~]?, 2 = quote? 3 = name 4 = quote? 5 = rest of line

        start = match.start(1)
        yield start, Operator, match.group(1)        # <<[-~]?
        yield match.start(2), String.Heredoc, match.group(2)   # quote ", ', `
        yield match.start(3), String.Delimiter, match.group(3) # heredoc name
        yield match.start(4), String.Heredoc, match.group(4)   # quote again

        heredocstack = ctx.__dict__.setdefault('heredocstack', [])
        outermost = not bool(heredocstack)
        heredocstack.append((match.group(1) in ('<<-', '<<~'), match.group(3)))

        ctx.pos = match.start(5)
        ctx.end = match.end(5)
        # this may find other heredocs, so limit the recursion depth
        if len(heredocstack) < 100:
            yield from self.get_tokens_unprocessed(context=ctx)
        else:
            yield ctx.pos, String.Heredoc, match.group(5)
        ctx.pos = match.end()

        if outermost:
            # this is the outer heredoc again, now we can process them all
            for tolerant, hdname in heredocstack:
                lines = []
                for match in line_re.finditer(ctx.text, ctx.pos):
                    if tolerant:
                        check = match.group().strip()
                    else:
                        check = match.group().rstrip()
                    if check == hdname:
                        for amatch in lines:
                            yield amatch.start(), String.Heredoc, amatch.group()
                        yield match.start(), String.Delimiter, match.group()
                        ctx.pos = match.end()
                        break
                    else:
                        lines.append(match)
                else:
                    # end of heredoc not found -- error!
                    for amatch in lines:
                        yield amatch.start(), Error, amatch.group()
            ctx.end = len(ctx.text)
            del heredocstack[:]

    def gen_rubystrings_rules():
        def intp_regex_callback(self, match, ctx):
            yield match.start(1), String.Regex, match.group(1)  # begin
            nctx = LexerContext(match.group(3), 0, ['interpolated-regex'])
            for i, t, v in self.get_tokens_unprocessed(context=nctx):
                yield match.start(3)+i, t, v
            yield match.start(4), String.Regex, match.group(4)  # end[mixounse]*
            ctx.pos = match.end()

        def intp_string_callback(self, match, ctx):
            yield match.start(1), String.Other, match.group(1)
            nctx = LexerContext(match.group(3), 0, ['interpolated-string'])
            for i, t, v in self.get_tokens_unprocessed(context=nctx):
                yield match.start(3)+i, t, v
            yield match.start(4), String.Other, match.group(4)  # end
            ctx.pos = match.end()

        states = {}
        states['strings'] = [
            # easy ones
            (r'\:@{0,2}[a-zA-Z_]\w*[!?]?', String.Symbol),
            (words(RUBY_OPERATORS, prefix=r'\:@{0,2}'), String.Symbol),
            (r":'(\\\\|\\[^\\]|[^'\\])*'", String.Symbol),
            (r':"', String.Symbol, 'simple-sym'),
            (r'([a-zA-Z_]\w*)(:)(?!:)',
             bygroups(String.Symbol, Punctuation)),  # Since Ruby 1.9
            (r'"', String.Double, 'simple-string-double'),
            (r"'", String.Single, 'simple-string-single'),
            (r'(?<!\.)`', String.Backtick, 'simple-backtick'),
        ]

        # quoted string and symbol
        for name, ttype, end in ('string-double', String.Double, '"'), \
                                ('string-single', String.Single, "'"),\
                                ('sym', String.Symbol, '"'), \
                                ('backtick', String.Backtick, '`'):
            states['simple-'+name] = [
                include('string-intp-escaped'),
                (rf'[^\\{end}#]+', ttype),
                (r'[\\#]', ttype),
                (end, ttype, '#pop'),
            ]

        # braced quoted strings
        for lbrace, rbrace, bracecc, name in \
                ('\\{', '\\}', '{}', 'cb'), \
                ('\\[', '\\]', '\\[\\]', 'sb'), \
                ('\\(', '\\)', '()', 'pa'), \
                ('<', '>', '<>', 'ab'):
            states[name+'-intp-string'] = [
                (r'\\[\\' + bracecc + ']', String.Other),
                (lbrace, String.Other, '#push'),
                (rbrace, String.Other, '#pop'),
                include('string-intp-escaped'),
                (r'[\\#' + bracecc + ']', String.Other),
                (r'[^\\#' + bracecc + ']+', String.Other),
            ]
            states['strings'].append((r'%[QWx]?' + lbrace, String.Other,
                                      name+'-intp-string'))
            states[name+'-string'] = [
                (r'\\[\\' + bracecc + ']', String.Other),
                (lbrace, String.Other, '#push'),
                (rbrace, String.Other, '#pop'),
                (r'[\\#' + bracecc + ']', String.Other),
                (r'[^\\#' + bracecc + ']+', String.Other),
            ]
            states['strings'].append((r'%[qsw]' + lbrace, String.Other,
                                      name+'-string'))
            states[name+'-regex'] = [
                (r'\\[\\' + bracecc + ']', String.Regex),
                (lbrace, String.Regex, '#push'),
                (rbrace + '[mixounse]*', String.Regex, '#pop'),
                include('string-intp'),
                (r'[\\#' + bracecc + ']', String.Regex),
                (r'[^\\#' + bracecc + ']+', String.Regex),
            ]
            states['strings'].append((r'%r' + lbrace, String.Regex,
                                      name+'-regex'))

        # these must come after %<brace>!
        states['strings'] += [
            # %r regex
            (r'(%r([\W_]))((?:\\\2|(?!\2).)*)(\2[mixounse]*)',
             intp_regex_callback),
            # regular fancy strings with qsw
            (r'%[qsw]([\W_])((?:\\\1|(?!\1).)*)\1', String.Other),
            (r'(%[QWx]([\W_]))((?:\\\2|(?!\2).)*)(\2)',
             intp_string_callback),
            # special forms of fancy strings after operators or
            # in method calls with braces
            (r'(?<=[-+/*%=<>&!^|~,(])(\s*)(%([\t ])(?:(?:\\\3|(?!\3).)*)\3)',
             bygroups(Whitespace, String.Other, None)),
            # and because of fixed width lookbehinds the whole thing a
            # second time for line startings...
            (r'^(\s*)(%([\t ])(?:(?:\\\3|(?!\3).)*)\3)',
             bygroups(Whitespace, String.Other, None)),
            # all regular fancy strings without qsw
            (r'(%([^a-zA-Z0-9\s]))((?:\\\2|(?!\2).)*)(\2)',
             intp_string_callback),
        ]

        return states

    tokens = {
        'root': [
            (r'\A#!.+?$', Comment.Hashbang),
            (r'#.*?$', Comment.Single),
            (r'=begin\s.*?\n=end.*?$', Comment.Multiline),
            # keywords
            (words((
                'BEGIN', 'END', 'alias', 'begin', 'break', 'case', 'defined?',
                'do', 'else', 'elsif', 'end', 'ensure', 'for', 'if', 'in', 'next', 'redo',
                'rescue', 'raise', 'retry', 'return', 'super', 'then', 'undef',
                'unless', 'until', 'when', 'while', 'yield'), suffix=r'\b'),
             Keyword),
            # start of function, class and module names
            (r'(module)(\s+)([a-zA-Z_]\w*'
             r'(?:::[a-zA-Z_]\w*)*)',
             bygroups(Keyword, Whitespace, Name.Namespace)),
            (r'(def)(\s+)', bygroups(Keyword, Whitespace), 'funcname'),
            (r'def(?=[*%&^`~+-/\[<>=])', Keyword, 'funcname'),
            (r'(class)(\s+)', bygroups(Keyword, Whitespace), 'classname'),
            # special methods
            (words((
                'initialize', 'new', 'loop', 'include', 'extend', 'raise', 'attr_reader',
                'attr_writer', 'attr_accessor', 'attr', 'catch', 'throw', 'private',
                'module_function', 'public', 'protected', 'true', 'false', 'nil'),
                suffix=r'\b'),
             Keyword.Pseudo),
            (r'(not|and|or)\b', Operator.Word),
            (words((
                'autoload', 'block_given', 'const_defined', 'eql', 'equal', 'frozen', 'include',
                'instance_of', 'is_a', 'iterator', 'kind_of', 'method_defined', 'nil',
                'private_method_defined', 'protected_method_defined',
                'public_method_defined', 'respond_to', 'tainted'), suffix=r'\?'),
             Name.Builtin),
            (r'(chomp|chop|exit|gsub|sub)!', Name.Builtin),
            (words((
                'Array', 'Float', 'Integer', 'String', '__id__', '__send__', 'abort',
                'ancestors', 'at_exit', 'autoload', 'binding', 'callcc', 'caller',
                'catch', 'chomp', 'chop', 'class_eval', 'class_variables',
                'clone', 'const_defined?', 'const_get', 'const_missing', 'const_set',
                'constants', 'display', 'dup', 'eval', 'exec', 'exit', 'extend', 'fail', 'fork',
                'format', 'freeze', 'getc', 'gets', 'global_variables', 'gsub',
                'hash', 'id', 'included_modules', 'inspect', 'instance_eval',
                'instance_method', 'instance_methods',
                'instance_variable_get', 'instance_variable_set', 'instance_variables',
                'lambda', 'load', 'local_variables', 'loop',
                'method', 'method_missing', 'methods', 'module_eval', 'name',
                'object_id', 'open', 'p', 'print', 'printf', 'private_class_method',
                'private_instance_methods',
                'private_methods', 'proc', 'protected_instance_methods',
                'protected_methods', 'public_class_method',
                'public_instance_methods', 'public_methods',
                'putc', 'puts', 'raise', 'rand', 'readline', 'readlines', 'require',
                'scan', 'select', 'self', 'send', 'set_trace_func', 'singleton_methods', 'sleep',
                'split', 'sprintf', 'srand', 'sub', 'syscall', 'system', 'taint',
                'test', 'throw', 'to_a', 'to_s', 'trace_var', 'trap', 'untaint',
                'untrace_var', 'warn'), prefix=r'(?<!\.)', suffix=r'\b'),
             Name.Builtin),
            (r'__(FILE|LINE)__\b', Name.Builtin.Pseudo),
            # normal heredocs
            (r'(?<!\w)(<<[-~]?)(["`\']?)([a-zA-Z_]\w*)(\2)(.*?\n)',
             heredoc_callback),
            # empty string heredocs
            (r'(<<[-~]?)("|\')()(\2)(.*?\n)', heredoc_callback),
            (r'__END__', Comment.Preproc, 'end-part'),
            # multiline regex (after keywords or assignments)
            (r'(?:^|(?<=[=<>~!:])|'
             r'(?<=(?:\s|;)when\s)|'
             r'(?<=(?:\s|;)or\s)|'
             r'(?<=(?:\s|;)and\s)|'
             r'(?<=\.index\s)|'
             r'(?<=\.scan\s)|'
             r'(?<=\.sub\s)|'
             r'(?<=\.sub!\s)|'
             r'(?<=\.gsub\s)|'
             r'(?<=\.gsub!\s)|'
             r'(?<=\.match\s)|'
             r'(?<=(?:\s|;)if\s)|'
             r'(?<=(?:\s|;)elsif\s)|'
             r'(?<=^when\s)|'
             r'(?<=^index\s)|'
             r'(?<=^scan\s)|'
             r'(?<=^sub\s)|'
             r'(?<=^gsub\s)|'
             r'(?<=^sub!\s)|'
             r'(?<=^gsub!\s)|'
             r'(?<=^match\s)|'
             r'(?<=^if\s)|'
             r'(?<=^elsif\s)'
             r')(\s*)(/)', bygroups(Text, String.Regex), 'multiline-regex'),
            # multiline regex (in method calls or subscripts)
            (r'(?<=\(|,|\[)/', String.Regex, 'multiline-regex'),
            # multiline regex (this time the funny no whitespace rule)
            (r'(\s+)(/)(?![\s=])', bygroups(Whitespace, String.Regex),
             'multiline-regex'),
            # lex numbers and ignore following regular expressions which
            # are division operators in fact (grrrr. i hate that. any
            # better ideas?)
            # since pygments 0.7 we also eat a "?" operator after numbers
            # so that the char operator does not work. Chars are not allowed
            # there so that you can use the ternary operator.
            # stupid example:
            #   x>=0?n[x]:""
            (r'(0_?[0-7]+(?:_[0-7]+)*)(\s*)([/?])?',
             bygroups(Number.Oct, Whitespace, Operator)),
            (r'(0x[0-9A-Fa-f]+(?:_[0-9A-Fa-f]+)*)(\s*)([/?])?',
             bygroups(Number.Hex, Whitespace, Operator)),
            (r'(0b[01]+(?:_[01]+)*)(\s*)([/?])?',
             bygroups(Number.Bin, Whitespace, Operator)),
            (r'([\d]+(?:_\d+)*)(\s*)([/?])?',
             bygroups(Number.Integer, Whitespace, Operator)),
            # Names
            (r'@@[a-zA-Z_]\w*', Name.Variable.Class),
            (r'@[a-zA-Z_]\w*', Name.Variable.Instance),
            (r'\$\w+', Name.Variable.Global),
            (r'\$[!@&`\'+~=/\\,;.<>_*$?:"^-]', Name.Variable.Global),
            (r'\$-[0adFiIlpvw]', Name.Variable.Global),
            (r'::', Operator),
            include('strings'),
            # chars
            (r'\?(\\[MC]-)*'  # modifiers
             r'(\\([\\abefnrstv#"\']|x[a-fA-F0-9]{1,2}|[0-7]{1,3})|\S)'
             r'(?!\w)',
             String.Char),
            (r'[A-Z]\w+', Name.Constant),
            # this is needed because ruby attributes can look
            # like keywords (class) or like this: ` ?!?
            (words(RUBY_OPERATORS, prefix=r'(\.|::)'),
             bygroups(Operator, Name.Operator)),
            (r'(\.|::)([a-zA-Z_]\w*[!?]?|[*%&^`~+\-/\[<>=])',
             bygroups(Operator, Name)),
            (r'[a-zA-Z_]\w*[!?]?', Name),
            (r'(\[|\]|\*\*|<<?|>>?|>=|<=|<=>|=~|={3}|'
             r'!~|&&?|\|\||\.{1,3})', Operator),
            (r'[-+/*%=<>&!^|~]=?', Operator),
            (r'[(){};,/?:\\]', Punctuation),
            (r'\s+', Whitespace)
        ],
        'funcname': [
            (r'\(', Punctuation, 'defexpr'),
            (r'(?:([a-zA-Z_]\w*)(\.))?'  # optional scope name, like "self."
             r'('
                r'[a-zA-Z\u0080-\uffff][a-zA-Z0-9_\u0080-\uffff]*[!?=]?'  # method name
                r'|!=|!~|=~|\*\*?|[-+!~]@?|[/%&|^]|<=>|<[<=]?|>[>=]?|===?'  # or operator override
                r'|\[\]=?'  # or element reference/assignment override
                r'|`'  # or the undocumented backtick override
             r')',
             bygroups(Name.Class, Operator, Name.Function), '#pop'),
            default('#pop')
        ],
        'classname': [
            (r'\(', Punctuation, 'defexpr'),
            (r'<<', Operator, '#pop'),
            (r'[A-Z_]\w*', Name.Class, '#pop'),
            default('#pop')
        ],
        'defexpr': [
            (r'(\))(\.|::)?', bygroups(Punctuation, Operator), '#pop'),
            (r'\(', Operator, '#push'),
            include('root')
        ],
        'in-intp': [
            (r'\{', String.Interpol, '#push'),
            (r'\}', String.Interpol, '#pop'),
            include('root'),
        ],
        'string-intp': [
            (r'#\{', String.Interpol, 'in-intp'),
            (r'#@@?[a-zA-Z_]\w*', String.Interpol),
            (r'#\$[a-zA-Z_]\w*', String.Interpol)
        ],
        'string-intp-escaped': [
            include('string-intp'),
            (r'\\([\\abefnrstv#"\']|x[a-fA-F0-9]{1,2}|[0-7]{1,3})',
             String.Escape)
        ],
        'interpolated-regex': [
            include('string-intp'),
            (r'[\\#]', String.Regex),
            (r'[^\\#]+', String.Regex),
        ],
        'interpolated-string': [
            include('string-intp'),
            (r'[\\#]', String.Other),
            (r'[^\\#]+', String.Other),
        ],
        'multiline-regex': [
            include('string-intp'),
            (r'\\\\', String.Regex),
            (r'\\/', String.Regex),
            (r'[\\#]', String.Regex),
            (r'[^\\/#]+', String.Regex),
            (r'/[mixounse]*', String.Regex, '#pop'),
        ],
        'end-part': [
            (r'.+', Comment.Preproc, '#pop')
        ]
    }
    tokens.update(gen_rubystrings_rules())

    def analyse_text(text):
        return shebang_matches(text, r'ruby(1\.\d)?')


class RubyConsoleLexer(Lexer):
    """
    For Ruby interactive console (**irb**) output.
    """
    name = 'Ruby irb session'
    aliases = ['rbcon', 'irb']
    mimetypes = ['text/x-ruby-shellsession']
    url = 'https://www.ruby-lang.org'
    version_added = ''
    _example = 'rbcon/console'

    _prompt_re = re.compile(r'irb\([a-zA-Z_]\w*\):\d{3}:\d+[>*"\'] '
                            r'|>> |\?> ')

    def get_tokens_unprocessed(self, text):
        rblexer = RubyLexer(**self.options)

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
                    yield from do_insertions(
                        insertions, rblexer.get_tokens_unprocessed(curcode))
                    curcode = ''
                    insertions = []
                yield match.start(), Generic.Output, line
        if curcode:
            yield from do_insertions(
                insertions, rblexer.get_tokens_unprocessed(curcode))


class FancyLexer(RegexLexer):
    """
    Pygments Lexer For Fancy.

    Fancy is a self-hosted, pure object-oriented, dynamic,
    class-based, concurrent general-purpose programming language
    running on Rubinius, the Ruby VM.
    """
    name = 'Fancy'
    url = 'https://github.com/bakkdoor/fancy'
    filenames = ['*.fy', '*.fancypack']
    aliases = ['fancy', 'fy']
    mimetypes = ['text/x-fancysrc']
    version_added = '1.5'

    tokens = {
        # copied from PerlLexer:
        'balanced-regex': [
            (r'/(\\\\|\\[^\\]|[^/\\])*/[egimosx]*', String.Regex, '#pop'),
            (r'!(\\\\|\\[^\\]|[^!\\])*![egimosx]*', String.Regex, '#pop'),
            (r'\\(\\\\|[^\\])*\\[egimosx]*', String.Regex, '#pop'),
            (r'\{(\\\\|\\[^\\]|[^}\\])*\}[egimosx]*', String.Regex, '#pop'),
            (r'<(\\\\|\\[^\\]|[^>\\])*>[egimosx]*', String.Regex, '#pop'),
            (r'\[(\\\\|\\[^\\]|[^\]\\])*\][egimosx]*', String.Regex, '#pop'),
            (r'\((\\\\|\\[^\\]|[^)\\])*\)[egimosx]*', String.Regex, '#pop'),
            (r'@(\\\\|\\[^\\]|[^@\\])*@[egimosx]*', String.Regex, '#pop'),
            (r'%(\\\\|\\[^\\]|[^%\\])*%[egimosx]*', String.Regex, '#pop'),
            (r'\$(\\\\|\\[^\\]|[^$\\])*\$[egimosx]*', String.Regex, '#pop'),
        ],
        'root': [
            (r'\s+', Whitespace),

            # balanced delimiters (copied from PerlLexer):
            (r's\{(\\\\|\\[^\\]|[^}\\])*\}\s*', String.Regex, 'balanced-regex'),
            (r's<(\\\\|\\[^\\]|[^>\\])*>\s*', String.Regex, 'balanced-regex'),
            (r's\[(\\\\|\\[^\\]|[^\]\\])*\]\s*', String.Regex, 'balanced-regex'),
            (r's\((\\\\|\\[^\\]|[^)\\])*\)\s*', String.Regex, 'balanced-regex'),
            (r'm?/(\\\\|\\[^\\]|[^///\n])*/[gcimosx]*', String.Regex),
            (r'm(?=[/!\\{<\[(@%$])', String.Regex, 'balanced-regex'),

            # Comments
            (r'#(.*?)\n', Comment.Single),
            # Symbols
            (r'\'([^\'\s\[\](){}]+|\[\])', String.Symbol),
            # Multi-line DoubleQuotedString
            (r'"""(\\\\|\\[^\\]|[^\\])*?"""', String),
            # DoubleQuotedString
            (r'"(\\\\|\\[^\\]|[^"\\])*"', String),
            # keywords
            (r'(def|class|try|catch|finally|retry|return|return_local|match|'
             r'case|->|=>)\b', Keyword),
            # constants
            (r'(self|super|nil|false|true)\b', Name.Constant),
            (r'[(){};,/?|:\\]', Punctuation),
            # names
            (words((
                'Object', 'Array', 'Hash', 'Directory', 'File', 'Class', 'String',
                'Number', 'Enumerable', 'FancyEnumerable', 'Block', 'TrueClass',
                'NilClass', 'FalseClass', 'Tuple', 'Symbol', 'Stack', 'Set',
                'FancySpec', 'Method', 'Package', 'Range'), suffix=r'\b'),
             Name.Builtin),
            # functions
            (r'[a-zA-Z](\w|[-+?!=*/^><%])*:', Name.Function),
            # operators, must be below functions
            (r'[-+*/~,<>=&!?%^\[\].$]+', Operator),
            (r'[A-Z]\w*', Name.Constant),
            (r'@[a-zA-Z_]\w*', Name.Variable.Instance),
            (r'@@[a-zA-Z_]\w*', Name.Variable.Class),
            ('@@?', Operator),
            (r'[a-zA-Z_]\w*', Name),
            # numbers - / checks are necessary to avoid mismarking regexes,
            # see comment in RubyLexer
            (r'(0[oO]?[0-7]+(?:_[0-7]+)*)(\s*)([/?])?',
             bygroups(Number.Oct, Whitespace, Operator)),
            (r'(0[xX][0-9A-Fa-f]+(?:_[0-9A-Fa-f]+)*)(\s*)([/?])?',
             bygroups(Number.Hex, Whitespace, Operator)),
            (r'(0[bB][01]+(?:_[01]+)*)(\s*)([/?])?',
             bygroups(Number.Bin, Whitespace, Operator)),
            (r'([\d]+(?:_\d+)*)(\s*)([/?])?',
             bygroups(Number.Integer, Whitespace, Operator)),
            (r'\d+([eE][+-]?[0-9]+)|\d+\.\d+([eE][+-]?[0-9]+)?', Number.Float),
            (r'\d+', Number.Integer)
        ]
    }

# === NexusCore/openenv\Lib\site-packages\setuptools\_distutils\util.py ===
"""distutils.util

Miscellaneous utility functions -- anything that doesn't fit into
one of the other *util.py modules.
"""

from __future__ import annotations

import functools
import importlib.util
import os
import pathlib
import re
import string
import subprocess
import sys
import sysconfig
import tempfile
from collections.abc import Callable, Iterable, Mapping
from typing import TYPE_CHECKING, AnyStr

from jaraco.functools import pass_none

from ._log import log
from ._modified import newer
from .errors import DistutilsByteCompileError, DistutilsPlatformError
from .spawn import spawn

if TYPE_CHECKING:
    from typing_extensions import TypeVarTuple, Unpack

    _Ts = TypeVarTuple("_Ts")


def get_host_platform() -> str:
    """
    Return a string that identifies the current platform. Use this
    function to distinguish platform-specific build directories and
    platform-specific built distributions.
    """

    # This function initially exposed platforms as defined in Python 3.9
    # even with older Python versions when distutils was split out.
    # Now it delegates to stdlib sysconfig.

    return sysconfig.get_platform()


def get_platform() -> str:
    if os.name == 'nt':
        TARGET_TO_PLAT = {
            'x86': 'win32',
            'x64': 'win-amd64',
            'arm': 'win-arm32',
            'arm64': 'win-arm64',
        }
        target = os.environ.get('VSCMD_ARG_TGT_ARCH')
        return TARGET_TO_PLAT.get(target) or get_host_platform()
    return get_host_platform()


if sys.platform == 'darwin':
    _syscfg_macosx_ver = None  # cache the version pulled from sysconfig
MACOSX_VERSION_VAR = 'MACOSX_DEPLOYMENT_TARGET'


def _clear_cached_macosx_ver():
    """For testing only. Do not call."""
    global _syscfg_macosx_ver
    _syscfg_macosx_ver = None


def get_macosx_target_ver_from_syscfg():
    """Get the version of macOS latched in the Python interpreter configuration.
    Returns the version as a string or None if can't obtain one. Cached."""
    global _syscfg_macosx_ver
    if _syscfg_macosx_ver is None:
        from distutils import sysconfig

        ver = sysconfig.get_config_var(MACOSX_VERSION_VAR) or ''
        if ver:
            _syscfg_macosx_ver = ver
    return _syscfg_macosx_ver


def get_macosx_target_ver():
    """Return the version of macOS for which we are building.

    The target version defaults to the version in sysconfig latched at time
    the Python interpreter was built, unless overridden by an environment
    variable. If neither source has a value, then None is returned"""

    syscfg_ver = get_macosx_target_ver_from_syscfg()
    env_ver = os.environ.get(MACOSX_VERSION_VAR)

    if env_ver:
        # Validate overridden version against sysconfig version, if have both.
        # Ensure that the deployment target of the build process is not less
        # than 10.3 if the interpreter was built for 10.3 or later.  This
        # ensures extension modules are built with correct compatibility
        # values, specifically LDSHARED which can use
        # '-undefined dynamic_lookup' which only works on >= 10.3.
        if (
            syscfg_ver
            and split_version(syscfg_ver) >= [10, 3]
            and split_version(env_ver) < [10, 3]
        ):
            my_msg = (
                '$' + MACOSX_VERSION_VAR + ' mismatch: '
                f'now "{env_ver}" but "{syscfg_ver}" during configure; '
                'must use 10.3 or later'
            )
            raise DistutilsPlatformError(my_msg)
        return env_ver
    return syscfg_ver


def split_version(s: str) -> list[int]:
    """Convert a dot-separated string into a list of numbers for comparisons"""
    return [int(n) for n in s.split('.')]


@pass_none
def convert_path(pathname: str | os.PathLike[str]) -> str:
    r"""
    Allow for pathlib.Path inputs, coax to a native path string.

    If None is passed, will just pass it through as
    Setuptools relies on this behavior.

    >>> convert_path(None) is None
    True

    Removes empty paths.

    >>> convert_path('foo/./bar').replace('\\', '/')
    'foo/bar'
    """
    return os.fspath(pathlib.PurePath(pathname))


def change_root(
    new_root: AnyStr | os.PathLike[AnyStr], pathname: AnyStr | os.PathLike[AnyStr]
) -> AnyStr:
    """Return 'pathname' with 'new_root' prepended.  If 'pathname' is
    relative, this is equivalent to "os.path.join(new_root,pathname)".
    Otherwise, it requires making 'pathname' relative and then joining the
    two, which is tricky on DOS/Windows and Mac OS.
    """
    if os.name == 'posix':
        if not os.path.isabs(pathname):
            return os.path.join(new_root, pathname)
        else:
            return os.path.join(new_root, pathname[1:])

    elif os.name == 'nt':
        (drive, path) = os.path.splitdrive(pathname)
        if path[0] == os.sep:
            path = path[1:]
        return os.path.join(new_root, path)

    raise DistutilsPlatformError(f"nothing known about platform '{os.name}'")


@functools.lru_cache
def check_environ() -> None:
    """Ensure that 'os.environ' has all the environment variables we
    guarantee that users can use in config files, command-line options,
    etc.  Currently this includes:
      HOME - user's home directory (Unix only)
      PLAT - description of the current platform, including hardware
             and OS (see 'get_platform()')
    """
    if os.name == 'posix' and 'HOME' not in os.environ:
        try:
            import pwd

            os.environ['HOME'] = pwd.getpwuid(os.getuid())[5]
        except (ImportError, KeyError):
            # bpo-10496: if the current user identifier doesn't exist in the
            # password database, do nothing
            pass

    if 'PLAT' not in os.environ:
        os.environ['PLAT'] = get_platform()


def subst_vars(s, local_vars: Mapping[str, object]) -> str:
    """
    Perform variable substitution on 'string'.
    Variables are indicated by format-style braces ("{var}").
    Variable is substituted by the value found in the 'local_vars'
    dictionary or in 'os.environ' if it's not in 'local_vars'.
    'os.environ' is first checked/augmented to guarantee that it contains
    certain values: see 'check_environ()'.  Raise ValueError for any
    variables not found in either 'local_vars' or 'os.environ'.
    """
    check_environ()
    lookup = dict(os.environ)
    lookup.update((name, str(value)) for name, value in local_vars.items())
    try:
        return _subst_compat(s).format_map(lookup)
    except KeyError as var:
        raise ValueError(f"invalid variable {var}")


def _subst_compat(s):
    """
    Replace shell/Perl-style variable substitution with
    format-style. For compatibility.
    """

    def _subst(match):
        return f'{{{match.group(1)}}}'

    repl = re.sub(r'\$([a-zA-Z_][a-zA-Z_0-9]*)', _subst, s)
    if repl != s:
        import warnings

        warnings.warn(
            "shell/Perl-style substitutions are deprecated",
            DeprecationWarning,
        )
    return repl


def grok_environment_error(exc: object, prefix: str = "error: ") -> str:
    # Function kept for backward compatibility.
    # Used to try clever things with EnvironmentErrors,
    # but nowadays str(exception) produces good messages.
    return prefix + str(exc)


# Needed by 'split_quoted()'
_wordchars_re = _squote_re = _dquote_re = None


def _init_regex():
    global _wordchars_re, _squote_re, _dquote_re
    _wordchars_re = re.compile(rf'[^\\\'\"{string.whitespace} ]*')
    _squote_re = re.compile(r"'(?:[^'\\]|\\.)*'")
    _dquote_re = re.compile(r'"(?:[^"\\]|\\.)*"')


def split_quoted(s: str) -> list[str]:
    """Split a string up according to Unix shell-like rules for quotes and
    backslashes.  In short: words are delimited by spaces, as long as those
    spaces are not escaped by a backslash, or inside a quoted string.
    Single and double quotes are equivalent, and the quote characters can
    be backslash-escaped.  The backslash is stripped from any two-character
    escape sequence, leaving only the escaped character.  The quote
    characters are stripped from any quoted string.  Returns a list of
    words.
    """

    # This is a nice algorithm for splitting up a single string, since it
    # doesn't require character-by-character examination.  It was a little
    # bit of a brain-bender to get it working right, though...
    if _wordchars_re is None:
        _init_regex()

    s = s.strip()
    words = []
    pos = 0

    while s:
        m = _wordchars_re.match(s, pos)
        end = m.end()
        if end == len(s):
            words.append(s[:end])
            break

        if s[end] in string.whitespace:
            # unescaped, unquoted whitespace: now
            # we definitely have a word delimiter
            words.append(s[:end])
            s = s[end:].lstrip()
            pos = 0

        elif s[end] == '\\':
            # preserve whatever is being escaped;
            # will become part of the current word
            s = s[:end] + s[end + 1 :]
            pos = end + 1

        else:
            if s[end] == "'":  # slurp singly-quoted string
                m = _squote_re.match(s, end)
            elif s[end] == '"':  # slurp doubly-quoted string
                m = _dquote_re.match(s, end)
            else:
                raise RuntimeError(f"this can't happen (bad char '{s[end]}')")

            if m is None:
                raise ValueError(f"bad string (mismatched {s[end]} quotes?)")

            (beg, end) = m.span()
            s = s[:beg] + s[beg + 1 : end - 1] + s[end:]
            pos = m.end() - 2

        if pos >= len(s):
            words.append(s)
            break

    return words


# split_quoted ()


def execute(
    func: Callable[[Unpack[_Ts]], object],
    args: tuple[Unpack[_Ts]],
    msg: object = None,
    verbose: bool = False,
    dry_run: bool = False,
) -> None:
    """
    Perform some action that affects the outside world (e.g. by
    writing to the filesystem). Such actions are special because they
    are disabled by the 'dry_run' flag. This method handles that
    complication; simply supply the
    function to call and an argument tuple for it (to embody the
    "external action" being performed) and an optional message to
    emit.
    """
    if msg is None:
        msg = f"{func.__name__}{args!r}"
        if msg[-2:] == ',)':  # correct for singleton tuple
            msg = msg[0:-2] + ')'

    log.info(msg)
    if not dry_run:
        func(*args)


def strtobool(val: str) -> bool:
    """Convert a string representation of truth to true (1) or false (0).

    True values are 'y', 'yes', 't', 'true', 'on', and '1'; false values
    are 'n', 'no', 'f', 'false', 'off', and '0'.  Raises ValueError if
    'val' is anything else.
    """
    val = val.lower()
    if val in ('y', 'yes', 't', 'true', 'on', '1'):
        return True
    elif val in ('n', 'no', 'f', 'false', 'off', '0'):
        return False
    else:
        raise ValueError(f"invalid truth value {val!r}")


def byte_compile(  # noqa: C901
    py_files: Iterable[str],
    optimize: int = 0,
    force: bool = False,
    prefix: str | None = None,
    base_dir: str | None = None,
    verbose: bool = True,
    dry_run: bool = False,
    direct: bool | None = None,
) -> None:
    """Byte-compile a collection of Python source files to .pyc
    files in a __pycache__ subdirectory.  'py_files' is a list
    of files to compile; any files that don't end in ".py" are silently
    skipped.  'optimize' must be one of the following:
      0 - don't optimize
      1 - normal optimization (like "python -O")
      2 - extra optimization (like "python -OO")
    If 'force' is true, all files are recompiled regardless of
    timestamps.

    The source filename encoded in each bytecode file defaults to the
    filenames listed in 'py_files'; you can modify these with 'prefix' and
    'basedir'.  'prefix' is a string that will be stripped off of each
    source filename, and 'base_dir' is a directory name that will be
    prepended (after 'prefix' is stripped).  You can supply either or both
    (or neither) of 'prefix' and 'base_dir', as you wish.

    If 'dry_run' is true, doesn't actually do anything that would
    affect the filesystem.

    Byte-compilation is either done directly in this interpreter process
    with the standard py_compile module, or indirectly by writing a
    temporary script and executing it.  Normally, you should let
    'byte_compile()' figure out to use direct compilation or not (see
    the source for details).  The 'direct' flag is used by the script
    generated in indirect mode; unless you know what you're doing, leave
    it set to None.
    """

    # nothing is done if sys.dont_write_bytecode is True
    if sys.dont_write_bytecode:
        raise DistutilsByteCompileError('byte-compiling is disabled.')

    # First, if the caller didn't force us into direct or indirect mode,
    # figure out which mode we should be in.  We take a conservative
    # approach: choose direct mode *only* if the current interpreter is
    # in debug mode and optimize is 0.  If we're not in debug mode (-O
    # or -OO), we don't know which level of optimization this
    # interpreter is running with, so we can't do direct
    # byte-compilation and be certain that it's the right thing.  Thus,
    # always compile indirectly if the current interpreter is in either
    # optimize mode, or if either optimization level was requested by
    # the caller.
    if direct is None:
        direct = __debug__ and optimize == 0

    # "Indirect" byte-compilation: write a temporary script and then
    # run it with the appropriate flags.
    if not direct:
        (script_fd, script_name) = tempfile.mkstemp(".py")
        log.info("writing byte-compilation script '%s'", script_name)
        if not dry_run:
            script = os.fdopen(script_fd, "w", encoding='utf-8')

            with script:
                script.write(
                    """\
from distutils.util import byte_compile
files = [
"""
                )

                # XXX would be nice to write absolute filenames, just for
                # safety's sake (script should be more robust in the face of
                # chdir'ing before running it).  But this requires abspath'ing
                # 'prefix' as well, and that breaks the hack in build_lib's
                # 'byte_compile()' method that carefully tacks on a trailing
                # slash (os.sep really) to make sure the prefix here is "just
                # right".  This whole prefix business is rather delicate -- the
                # problem is that it's really a directory, but I'm treating it
                # as a dumb string, so trailing slashes and so forth matter.

                script.write(",\n".join(map(repr, py_files)) + "]\n")
                script.write(
                    f"""
byte_compile(files, optimize={optimize!r}, force={force!r},
             prefix={prefix!r}, base_dir={base_dir!r},
             verbose={verbose!r}, dry_run=False,
             direct=True)
"""
                )

        cmd = [sys.executable]
        cmd.extend(subprocess._optim_args_from_interpreter_flags())
        cmd.append(script_name)
        spawn(cmd, dry_run=dry_run)
        execute(os.remove, (script_name,), f"removing {script_name}", dry_run=dry_run)

    # "Direct" byte-compilation: use the py_compile module to compile
    # right here, right now.  Note that the script generated in indirect
    # mode simply calls 'byte_compile()' in direct mode, a weird sort of
    # cross-process recursion.  Hey, it works!
    else:
        from py_compile import compile

        for file in py_files:
            if file[-3:] != ".py":
                # This lets us be lazy and not filter filenames in
                # the "install_lib" command.
                continue

            # Terminology from the py_compile module:
            #   cfile - byte-compiled file
            #   dfile - purported source filename (same as 'file' by default)
            if optimize >= 0:
                opt = '' if optimize == 0 else optimize
                cfile = importlib.util.cache_from_source(file, optimization=opt)
            else:
                cfile = importlib.util.cache_from_source(file)
            dfile = file
            if prefix:
                if file[: len(prefix)] != prefix:
                    raise ValueError(
                        f"invalid prefix: filename {file!r} doesn't start with {prefix!r}"
                    )
                dfile = dfile[len(prefix) :]
            if base_dir:
                dfile = os.path.join(base_dir, dfile)

            cfile_base = os.path.basename(cfile)
            if direct:
                if force or newer(file, cfile):
                    log.info("byte-compiling %s to %s", file, cfile_base)
                    if not dry_run:
                        compile(file, cfile, dfile)
                else:
                    log.debug("skipping byte-compilation of %s to %s", file, cfile_base)


def rfc822_escape(header: str) -> str:
    """Return a version of the string escaped for inclusion in an
    RFC-822 header, by ensuring there are 8 spaces space after each newline.
    """
    indent = 8 * " "
    lines = header.splitlines(keepends=True)

    # Emulate the behaviour of `str.split`
    # (the terminal line break in `splitlines` does not result in an extra line):
    ends_in_newline = lines and lines[-1].splitlines()[0] != lines[-1]
    suffix = indent if ends_in_newline else ""

    return indent.join(lines) + suffix


def is_mingw() -> bool:
    """Returns True if the current platform is mingw.

    Python compiled with Mingw-w64 has sys.platform == 'win32' and
    get_platform() starts with 'mingw'.
    """
    return sys.platform == 'win32' and get_platform().startswith('mingw')


def is_freethreaded():
    """Return True if the Python interpreter is built with free threading support."""
    return bool(sysconfig.get_config_var('Py_GIL_DISABLED'))

# === NexusCore/openenv\Lib\site-packages\debugpy\_vendored\pydevd\_pydevd_bundle\pydevd_utils.py ===
from __future__ import nested_scopes
import traceback
import warnings
from _pydev_bundle import pydev_log
from _pydev_bundle._pydev_saved_modules import thread, threading
from _pydev_bundle import _pydev_saved_modules
import signal
import os
import ctypes
from importlib import import_module
from importlib.util import module_from_spec, spec_from_file_location
from urllib.parse import quote  # @UnresolvedImport
import time
import inspect
import sys
from _pydevd_bundle.pydevd_constants import (
    USE_CUSTOM_SYS_CURRENT_FRAMES,
    IS_PYPY,
    SUPPORT_GEVENT,
    GEVENT_SUPPORT_NOT_SET_MSG,
    GENERATED_LEN_ATTR_NAME,
    PYDEVD_WARN_SLOW_RESOLVE_TIMEOUT,
    get_global_debugger,
)


def save_main_module(file, module_name):
    # patch provided by: Scott Schlesier - when script is run, it does not
    # use globals from pydevd:
    # This will prevent the pydevd script from contaminating the namespace for the script to be debugged
    # pretend pydevd is not the main module, and
    # convince the file to be debugged that it was loaded as main
    m = sys.modules[module_name] = sys.modules["__main__"]
    m.__name__ = module_name
    loader = m.__loader__ if hasattr(m, "__loader__") else None
    spec = spec_from_file_location("__main__", file, loader=loader)
    m = module_from_spec(spec)
    sys.modules["__main__"] = m
    return m


def is_current_thread_main_thread():
    if hasattr(threading, "main_thread"):
        return threading.current_thread() is threading.main_thread()
    else:
        return isinstance(threading.current_thread(), threading._MainThread)


def get_main_thread():
    if hasattr(threading, "main_thread"):
        return threading.main_thread()
    else:
        for t in threading.enumerate():
            if isinstance(t, threading._MainThread):
                return t
    return None


def to_number(x):
    if is_string(x):
        try:
            n = float(x)
            return n
        except ValueError:
            pass

        l = x.find("(")
        if l != -1:
            y = x[0 : l - 1]
            # print y
            try:
                n = float(y)
                return n
            except ValueError:
                pass
    return None


def compare_object_attrs_key(x):
    if GENERATED_LEN_ATTR_NAME == x:
        as_number = to_number(x)
        if as_number is None:
            as_number = 99999999
        # len() should appear after other attributes in a list.
        return (1, as_number)
    else:
        return (-1, to_string(x))


def is_string(x):
    return isinstance(x, str)


def to_string(x):
    if isinstance(x, str):
        return x
    else:
        return str(x)


def print_exc():
    if traceback:
        traceback.print_exc()


def quote_smart(s, safe="/"):
    return quote(s, safe)


def get_clsname_for_code(code, frame):
    clsname = None
    if len(code.co_varnames) > 0:
        # We are checking the first argument of the function
        # (`self` or `cls` for methods).
        first_arg_name = code.co_varnames[0]
        if first_arg_name in frame.f_locals:
            first_arg_obj = frame.f_locals[first_arg_name]
            if inspect.isclass(first_arg_obj):  # class method
                first_arg_class = first_arg_obj
            else:  # instance method
                if hasattr(first_arg_obj, "__class__"):
                    first_arg_class = first_arg_obj.__class__
                else:  # old style class, fall back on type
                    first_arg_class = type(first_arg_obj)
            func_name = code.co_name
            if hasattr(first_arg_class, func_name):
                method = getattr(first_arg_class, func_name)
                func_code = None
                if hasattr(method, "func_code"):  # Python2
                    func_code = method.func_code
                elif hasattr(method, "__code__"):  # Python3
                    func_code = method.__code__
                if func_code and func_code == code:
                    clsname = first_arg_class.__name__

    return clsname


def get_non_pydevd_threads():
    threads = threading.enumerate()
    return [t for t in threads if t and not getattr(t, "is_pydev_daemon_thread", False)]


if USE_CUSTOM_SYS_CURRENT_FRAMES and IS_PYPY:
    # On PyPy we can use its fake_frames to get the traceback
    # (instead of the actual real frames that need the tracing to be correct).
    _tid_to_frame_for_dump_threads = sys._current_frames
else:
    from _pydevd_bundle.pydevd_constants import _current_frames as _tid_to_frame_for_dump_threads


def dump_threads(stream=None, show_pydevd_threads=True):
    """
    Helper to dump thread info.
    """
    if stream is None:
        stream = sys.stderr
    thread_id_to_name_and_is_pydevd_thread = {}
    try:
        threading_enumerate = _pydev_saved_modules.pydevd_saved_threading_enumerate
        if threading_enumerate is None:
            threading_enumerate = threading.enumerate

        for t in threading_enumerate():
            is_pydevd_thread = getattr(t, "is_pydev_daemon_thread", False)
            thread_id_to_name_and_is_pydevd_thread[t.ident] = (
                "%s  (daemon: %s, pydevd thread: %s)" % (t.name, t.daemon, is_pydevd_thread),
                is_pydevd_thread,
            )
    except:
        pass

    stream.write("===============================================================================\n")
    stream.write("Threads running\n")
    stream.write("================================= Thread Dump =================================\n")
    stream.flush()

    for thread_id, frame in _tid_to_frame_for_dump_threads().items():
        name, is_pydevd_thread = thread_id_to_name_and_is_pydevd_thread.get(thread_id, (thread_id, False))
        if not show_pydevd_threads and is_pydevd_thread:
            continue

        stream.write("\n-------------------------------------------------------------------------------\n")
        stream.write(" Thread %s" % (name,))
        stream.write("\n\n")

        for i, (filename, lineno, name, line) in enumerate(traceback.extract_stack(frame)):
            stream.write(' File "%s", line %d, in %s\n' % (filename, lineno, name))
            if line:
                stream.write("   %s\n" % (line.strip()))

            if i == 0 and "self" in frame.f_locals:
                stream.write("   self: ")
                try:
                    stream.write(str(frame.f_locals["self"]))
                except:
                    stream.write("Unable to get str of: %s" % (type(frame.f_locals["self"]),))
                stream.write("\n")
        stream.flush()

    stream.write("\n=============================== END Thread Dump ===============================")
    stream.flush()


def _extract_variable_nested_braces(char_iter):
    expression = []
    level = 0
    for c in char_iter:
        if c == "{":
            level += 1
        if c == "}":
            level -= 1
        if level == -1:
            return "".join(expression).strip()
        expression.append(c)
    raise SyntaxError("Unbalanced braces in expression.")


def _extract_expression_list(log_message):
    # Note: not using re because of nested braces.
    expression = []
    expression_vars = []
    char_iter = iter(log_message)
    for c in char_iter:
        if c == "{":
            expression_var = _extract_variable_nested_braces(char_iter)
            if expression_var:
                expression.append("%s")
                expression_vars.append(expression_var)
        else:
            expression.append(c)

    expression = "".join(expression)
    return expression, expression_vars


def convert_dap_log_message_to_expression(log_message):
    try:
        expression, expression_vars = _extract_expression_list(log_message)
    except SyntaxError:
        return repr("Unbalanced braces in: %s" % (log_message))
    if not expression_vars:
        return repr(expression)
    # Note: use '%' to be compatible with Python 2.6.
    return repr(expression) + " % (" + ", ".join(str(x) for x in expression_vars) + ",)"


def notify_about_gevent_if_needed(stream=None):
    """
    When debugging with gevent check that the gevent flag is used if the user uses the gevent
    monkey-patching.

    :return bool:
        Returns True if a message had to be shown to the user and False otherwise.
    """
    stream = stream if stream is not None else sys.stderr
    if not SUPPORT_GEVENT:
        gevent_monkey = sys.modules.get("gevent.monkey")
        if gevent_monkey is not None:
            try:
                saved = gevent_monkey.saved
            except AttributeError:
                pydev_log.exception_once("Error checking for gevent monkey-patching.")
                return False

            if saved:
                # Note: print to stderr as it may deadlock the debugger.
                sys.stderr.write("%s\n" % (GEVENT_SUPPORT_NOT_SET_MSG,))
                return True

    return False


def hasattr_checked(obj, name):
    try:
        getattr(obj, name)
    except:
        # i.e.: Handle any exception, not only AttributeError.
        return False
    else:
        return True


def getattr_checked(obj, name):
    try:
        return getattr(obj, name)
    except:
        # i.e.: Handle any exception, not only AttributeError.
        return None


def dir_checked(obj):
    try:
        return dir(obj)
    except:
        return []


def isinstance_checked(obj, cls):
    try:
        return isinstance(obj, cls)
    except:
        return False


class ScopeRequest(object):
    __slots__ = ["variable_reference", "scope"]

    def __init__(self, variable_reference, scope):
        assert scope in ("globals", "locals")
        self.variable_reference = variable_reference
        self.scope = scope

    def __eq__(self, o):
        if isinstance(o, ScopeRequest):
            return self.variable_reference == o.variable_reference and self.scope == o.scope

        return False

    def __ne__(self, o):
        return not self == o

    def __hash__(self):
        return hash((self.variable_reference, self.scope))


class DAPGrouper(object):
    """
    Note: this is a helper class to group variables on the debug adapter protocol (DAP). For
    the xml protocol the type is just added to each variable and the UI can group/hide it as needed.
    """

    SCOPE_SPECIAL_VARS = "special variables"
    SCOPE_PROTECTED_VARS = "protected variables"
    SCOPE_FUNCTION_VARS = "function variables"
    SCOPE_CLASS_VARS = "class variables"

    SCOPES_SORTED = [
        SCOPE_SPECIAL_VARS,
        SCOPE_PROTECTED_VARS,
        SCOPE_FUNCTION_VARS,
        SCOPE_CLASS_VARS,
    ]

    __slots__ = ["variable_reference", "scope", "contents_debug_adapter_protocol"]

    def __init__(self, scope):
        self.variable_reference = id(self)
        self.scope = scope
        self.contents_debug_adapter_protocol = []

    def get_contents_debug_adapter_protocol(self):
        return self.contents_debug_adapter_protocol[:]

    def __eq__(self, o):
        if isinstance(o, ScopeRequest):
            return self.variable_reference == o.variable_reference and self.scope == o.scope

        return False

    def __ne__(self, o):
        return not self == o

    def __hash__(self):
        return hash((self.variable_reference, self.scope))

    def __repr__(self):
        return ""

    def __str__(self):
        return ""


def interrupt_main_thread(main_thread=None):
    """
    Generates a KeyboardInterrupt in the main thread by sending a Ctrl+C
    or by calling thread.interrupt_main().

    :param main_thread:
        Needed because Jython needs main_thread._thread.interrupt() to be called.

    Note: if unable to send a Ctrl+C, the KeyboardInterrupt will only be raised
    when the next Python instruction is about to be executed (so, it won't interrupt
    a sleep(1000)).
    """
    if main_thread is None:
        main_thread = threading.main_thread()

    pydev_log.debug("Interrupt main thread.")
    called = False
    try:
        if os.name == "posix":
            # On Linux we can't interrupt 0 as in Windows because it's
            # actually owned by a process -- on the good side, signals
            # work much better on Linux!
            os.kill(os.getpid(), signal.SIGINT)
            called = True

        elif os.name == "nt":
            # This generates a Ctrl+C only for the current process and not
            # to the process group!
            # Note: there doesn't seem to be any public documentation for this
            # function (although it seems to be  present from Windows Server 2003 SP1 onwards
            # according to: https://www.geoffchappell.com/studies/windows/win32/kernel32/api/index.htm)
            ctypes.windll.kernel32.CtrlRoutine(0)

            # The code below is deprecated because it actually sends a Ctrl+C
            # to the process group, so, if this was a process created without
            # passing `CREATE_NEW_PROCESS_GROUP` the  signal may be sent to the
            # parent process and to sub-processes too (which is not ideal --
            # for instance, when using pytest-xdist, it'll actually stop the
            # testing, even when called in the subprocess).

            # if hasattr_checked(signal, 'CTRL_C_EVENT'):
            #     os.kill(0, signal.CTRL_C_EVENT)
            # else:
            #     # Python 2.6
            #     ctypes.windll.kernel32.GenerateConsoleCtrlEvent(0, 0)
            called = True

    except:
        # If something went wrong, fallback to interrupting when the next
        # Python instruction is being called.
        pydev_log.exception("Error interrupting main thread (using fallback).")

    if not called:
        try:
            # In this case, we don't really interrupt a sleep() nor IO operations
            # (this makes the KeyboardInterrupt be sent only when the next Python
            # instruction is about to be executed).
            if hasattr(thread, "interrupt_main"):
                thread.interrupt_main()
            else:
                main_thread._thread.interrupt()  # Jython
        except:
            pydev_log.exception("Error on interrupt main thread fallback.")


class Timer(object):
    def __init__(self, min_diff=PYDEVD_WARN_SLOW_RESOLVE_TIMEOUT):
        self.min_diff = min_diff
        self._curr_time = time.time()

    def print_time(self, msg="Elapsed:"):
        old = self._curr_time
        new = self._curr_time = time.time()
        diff = new - old
        if diff >= self.min_diff:
            print("%s: %.2fs" % (msg, diff))

    def _report_slow(self, compute_msg, *args):
        old = self._curr_time
        new = self._curr_time = time.time()
        diff = new - old
        if diff >= self.min_diff:
            py_db = get_global_debugger()
            if py_db is not None:
                msg = compute_msg(diff, *args)
                py_db.writer.add_command(py_db.cmd_factory.make_warning_message(msg))

    def report_if_compute_repr_attr_slow(self, attrs_tab_separated, attr_name, attr_type):
        self._report_slow(self._compute_repr_slow, attrs_tab_separated, attr_name, attr_type)

    def _compute_repr_slow(self, diff, attrs_tab_separated, attr_name, attr_type):
        try:
            attr_type = attr_type.__name__
        except:
            pass
        if attrs_tab_separated:
            return (
                "pydevd warning: Computing repr of %s.%s (%s) was slow (took %.2fs).\n"
                "Customize report timeout by setting the `PYDEVD_WARN_SLOW_RESOLVE_TIMEOUT` environment variable to a higher timeout (default is: %ss)\n"
            ) % (attrs_tab_separated.replace("\t", "."), attr_name, attr_type, diff, PYDEVD_WARN_SLOW_RESOLVE_TIMEOUT)
        else:
            return (
                "pydevd warning: Computing repr of %s (%s) was slow (took %.2fs)\n"
                "Customize report timeout by setting the `PYDEVD_WARN_SLOW_RESOLVE_TIMEOUT` environment variable to a higher timeout (default is: %ss)\n"
            ) % (attr_name, attr_type, diff, PYDEVD_WARN_SLOW_RESOLVE_TIMEOUT)

    def report_if_getting_attr_slow(self, cls, attr_name):
        self._report_slow(self._compute_get_attr_slow, cls, attr_name)

    def _compute_get_attr_slow(self, diff, cls, attr_name):
        try:
            cls = cls.__name__
        except:
            pass
        return (
            "pydevd warning: Getting attribute %s.%s was slow (took %.2fs)\n"
            "Customize report timeout by setting the `PYDEVD_WARN_SLOW_RESOLVE_TIMEOUT` environment variable to a higher timeout (default is: %ss)\n"
        ) % (cls, attr_name, diff, PYDEVD_WARN_SLOW_RESOLVE_TIMEOUT)


def import_attr_from_module(import_with_attr_access):
    if "." not in import_with_attr_access:
        # We need at least one '.' (we don't support just the module import, we need the attribute access too).
        raise ImportError("Unable to import module with attr access: %s" % (import_with_attr_access,))

    module_name, attr_name = import_with_attr_access.rsplit(".", 1)

    while True:
        try:
            mod = import_module(module_name)
        except ImportError:
            if "." not in module_name:
                raise ImportError("Unable to import module with attr access: %s" % (import_with_attr_access,))

            module_name, new_attr_part = module_name.rsplit(".", 1)
            attr_name = new_attr_part + "." + attr_name
        else:
            # Ok, we got the base module, now, get the attribute we need.
            try:
                for attr in attr_name.split("."):
                    mod = getattr(mod, attr)
                return mod
            except:
                raise ImportError("Unable to import module with attr access: %s" % (import_with_attr_access,))

# === NexusCore/openenv\Lib\site-packages\nltk\corpus\reader\api.py ===
# Natural Language Toolkit: API for Corpus Readers
#
# Copyright (C) 2001-2024 NLTK Project
# Author: Steven Bird <stevenbird1@gmail.com>
#         Edward Loper <edloper@gmail.com>
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT

"""
API for corpus readers.
"""

import os
import re
from collections import defaultdict
from itertools import chain

from nltk.corpus.reader.util import *
from nltk.data import FileSystemPathPointer, PathPointer, ZipFilePathPointer


class CorpusReader:
    """
    A base class for "corpus reader" classes, each of which can be
    used to read a specific corpus format.  Each individual corpus
    reader instance is used to read a specific corpus, consisting of
    one or more files under a common root directory.  Each file is
    identified by its ``file identifier``, which is the relative path
    to the file from the root directory.

    A separate subclass is defined for each corpus format.  These
    subclasses define one or more methods that provide 'views' on the
    corpus contents, such as ``words()`` (for a list of words) and
    ``parsed_sents()`` (for a list of parsed sentences).  Called with
    no arguments, these methods will return the contents of the entire
    corpus.  For most corpora, these methods define one or more
    selection arguments, such as ``fileids`` or ``categories``, which can
    be used to select which portion of the corpus should be returned.
    """

    def __init__(self, root, fileids, encoding="utf8", tagset=None):
        """
        :type root: PathPointer or str
        :param root: A path pointer identifying the root directory for
            this corpus.  If a string is specified, then it will be
            converted to a ``PathPointer`` automatically.
        :param fileids: A list of the files that make up this corpus.
            This list can either be specified explicitly, as a list of
            strings; or implicitly, as a regular expression over file
            paths.  The absolute path for each file will be constructed
            by joining the reader's root to each file name.
        :param encoding: The default unicode encoding for the files
            that make up the corpus.  The value of ``encoding`` can be any
            of the following:

            - A string: ``encoding`` is the encoding name for all files.
            - A dictionary: ``encoding[file_id]`` is the encoding
              name for the file whose identifier is ``file_id``.  If
              ``file_id`` is not in ``encoding``, then the file
              contents will be processed using non-unicode byte strings.
            - A list: ``encoding`` should be a list of ``(regexp, encoding)``
              tuples.  The encoding for a file whose identifier is ``file_id``
              will be the ``encoding`` value for the first tuple whose
              ``regexp`` matches the ``file_id``.  If no tuple's ``regexp``
              matches the ``file_id``, the file contents will be processed
              using non-unicode byte strings.
            - None: the file contents of all files will be
              processed using non-unicode byte strings.
        :param tagset: The name of the tagset used by this corpus, to be used
              for normalizing or converting the POS tags returned by the
              ``tagged_...()`` methods.
        """
        # Convert the root to a path pointer, if necessary.
        if isinstance(root, str) and not isinstance(root, PathPointer):
            m = re.match(r"(.*\.zip)/?(.*)$|", root)
            zipfile, zipentry = m.groups()
            if zipfile:
                root = ZipFilePathPointer(zipfile, zipentry)
            else:
                root = FileSystemPathPointer(root)
        elif not isinstance(root, PathPointer):
            raise TypeError("CorpusReader: expected a string or a PathPointer")

        # If `fileids` is a regexp, then expand it.
        if isinstance(fileids, str):
            fileids = find_corpus_fileids(root, fileids)

        self._fileids = fileids
        """A list of the relative paths for the fileids that make up
        this corpus."""

        self._root = root
        """The root directory for this corpus."""

        self._readme = "README"
        self._license = "LICENSE"
        self._citation = "citation.bib"

        # If encoding was specified as a list of regexps, then convert
        # it to a dictionary.
        if isinstance(encoding, list):
            encoding_dict = {}
            for fileid in self._fileids:
                for x in encoding:
                    (regexp, enc) = x
                    if re.match(regexp, fileid):
                        encoding_dict[fileid] = enc
                        break
            encoding = encoding_dict

        self._encoding = encoding
        """The default unicode encoding for the fileids that make up
           this corpus.  If ``encoding`` is None, then the file
           contents are processed using byte strings."""
        self._tagset = tagset

    def __repr__(self):
        if isinstance(self._root, ZipFilePathPointer):
            path = f"{self._root.zipfile.filename}/{self._root.entry}"
        else:
            path = "%s" % self._root.path
        return f"<{self.__class__.__name__} in {path!r}>"

    def ensure_loaded(self):
        """
        Load this corpus (if it has not already been loaded).  This is
        used by LazyCorpusLoader as a simple method that can be used to
        make sure a corpus is loaded -- e.g., in case a user wants to
        do help(some_corpus).
        """
        pass  # no need to actually do anything.

    def readme(self):
        """
        Return the contents of the corpus README file, if it exists.
        """
        with self.open(self._readme) as f:
            return f.read()

    def license(self):
        """
        Return the contents of the corpus LICENSE file, if it exists.
        """
        with self.open(self._license) as f:
            return f.read()

    def citation(self):
        """
        Return the contents of the corpus citation.bib file, if it exists.
        """
        with self.open(self._citation) as f:
            return f.read()

    def fileids(self):
        """
        Return a list of file identifiers for the fileids that make up
        this corpus.
        """
        return self._fileids

    def abspath(self, fileid):
        """
        Return the absolute path for the given file.

        :type fileid: str
        :param fileid: The file identifier for the file whose path
            should be returned.
        :rtype: PathPointer
        """
        return self._root.join(fileid)

    def abspaths(self, fileids=None, include_encoding=False, include_fileid=False):
        """
        Return a list of the absolute paths for all fileids in this corpus;
        or for the given list of fileids, if specified.

        :type fileids: None or str or list
        :param fileids: Specifies the set of fileids for which paths should
            be returned.  Can be None, for all fileids; a list of
            file identifiers, for a specified set of fileids; or a single
            file identifier, for a single file.  Note that the return
            value is always a list of paths, even if ``fileids`` is a
            single file identifier.

        :param include_encoding: If true, then return a list of
            ``(path_pointer, encoding)`` tuples.

        :rtype: list(PathPointer)
        """
        if fileids is None:
            fileids = self._fileids
        elif isinstance(fileids, str):
            fileids = [fileids]

        paths = [self._root.join(f) for f in fileids]

        if include_encoding and include_fileid:
            return list(zip(paths, [self.encoding(f) for f in fileids], fileids))
        elif include_fileid:
            return list(zip(paths, fileids))
        elif include_encoding:
            return list(zip(paths, [self.encoding(f) for f in fileids]))
        else:
            return paths

    def raw(self, fileids=None):
        """
        :param fileids: A list specifying the fileids that should be used.
        :return: the given file(s) as a single string.
        :rtype: str
        """
        if fileids is None:
            fileids = self._fileids
        elif isinstance(fileids, str):
            fileids = [fileids]
        contents = []
        for f in fileids:
            with self.open(f) as fp:
                contents.append(fp.read())
        return concat(contents)

    def open(self, file):
        """
        Return an open stream that can be used to read the given file.
        If the file's encoding is not None, then the stream will
        automatically decode the file's contents into unicode.

        :param file: The file identifier of the file to read.
        """
        encoding = self.encoding(file)
        stream = self._root.join(file).open(encoding)
        return stream

    def encoding(self, file):
        """
        Return the unicode encoding for the given corpus file, if known.
        If the encoding is unknown, or if the given file should be
        processed using byte strings (str), then return None.
        """
        if isinstance(self._encoding, dict):
            return self._encoding.get(file)
        else:
            return self._encoding

    def _get_root(self):
        return self._root

    root = property(
        _get_root,
        doc="""
        The directory where this corpus is stored.

        :type: PathPointer""",
    )


######################################################################
# { Corpora containing categorized items
######################################################################


class CategorizedCorpusReader:
    """
    A mixin class used to aid in the implementation of corpus readers
    for categorized corpora.  This class defines the method
    ``categories()``, which returns a list of the categories for the
    corpus or for a specified set of fileids; and overrides ``fileids()``
    to take a ``categories`` argument, restricting the set of fileids to
    be returned.

    Subclasses are expected to:

      - Call ``__init__()`` to set up the mapping.

      - Override all view methods to accept a ``categories`` parameter,
        which can be used *instead* of the ``fileids`` parameter, to
        select which fileids should be included in the returned view.
    """

    def __init__(self, kwargs):
        """
        Initialize this mapping based on keyword arguments, as
        follows:

          - cat_pattern: A regular expression pattern used to find the
            category for each file identifier.  The pattern will be
            applied to each file identifier, and the first matching
            group will be used as the category label for that file.

          - cat_map: A dictionary, mapping from file identifiers to
            category labels.

          - cat_file: The name of a file that contains the mapping
            from file identifiers to categories.  The argument
            ``cat_delimiter`` can be used to specify a delimiter.

        The corresponding argument will be deleted from ``kwargs``.  If
        more than one argument is specified, an exception will be
        raised.
        """
        self._f2c = None  #: file-to-category mapping
        self._c2f = None  #: category-to-file mapping

        self._pattern = None  #: regexp specifying the mapping
        self._map = None  #: dict specifying the mapping
        self._file = None  #: fileid of file containing the mapping
        self._delimiter = None  #: delimiter for ``self._file``

        if "cat_pattern" in kwargs:
            self._pattern = kwargs["cat_pattern"]
            del kwargs["cat_pattern"]
        elif "cat_map" in kwargs:
            self._map = kwargs["cat_map"]
            del kwargs["cat_map"]
        elif "cat_file" in kwargs:
            self._file = kwargs["cat_file"]
            del kwargs["cat_file"]
            if "cat_delimiter" in kwargs:
                self._delimiter = kwargs["cat_delimiter"]
                del kwargs["cat_delimiter"]
        else:
            raise ValueError(
                "Expected keyword argument cat_pattern or " "cat_map or cat_file."
            )

        if "cat_pattern" in kwargs or "cat_map" in kwargs or "cat_file" in kwargs:
            raise ValueError(
                "Specify exactly one of: cat_pattern, " "cat_map, cat_file."
            )

    def _init(self):
        self._f2c = defaultdict(set)
        self._c2f = defaultdict(set)

        if self._pattern is not None:
            for file_id in self._fileids:
                category = re.match(self._pattern, file_id).group(1)
                self._add(file_id, category)

        elif self._map is not None:
            for file_id, categories in self._map.items():
                for category in categories:
                    self._add(file_id, category)

        elif self._file is not None:
            with self.open(self._file) as f:
                for line in f.readlines():
                    line = line.strip()
                    file_id, categories = line.split(self._delimiter, 1)
                    if file_id not in self.fileids():
                        raise ValueError(
                            "In category mapping file %s: %s "
                            "not found" % (self._file, file_id)
                        )
                    for category in categories.split(self._delimiter):
                        self._add(file_id, category)

    def _add(self, file_id, category):
        self._f2c[file_id].add(category)
        self._c2f[category].add(file_id)

    def categories(self, fileids=None):
        """
        Return a list of the categories that are defined for this corpus,
        or for the file(s) if it is given.
        """
        if self._f2c is None:
            self._init()
        if fileids is None:
            return sorted(self._c2f)
        if isinstance(fileids, str):
            fileids = [fileids]
        return sorted(set.union(*(self._f2c[d] for d in fileids)))

    def fileids(self, categories=None):
        """
        Return a list of file identifiers for the files that make up
        this corpus, or that make up the given category(s) if specified.
        """
        if categories is None:
            return super().fileids()
        elif isinstance(categories, str):
            if self._f2c is None:
                self._init()
            if categories in self._c2f:
                return sorted(self._c2f[categories])
            else:
                raise ValueError("Category %s not found" % categories)
        else:
            if self._f2c is None:
                self._init()
            return sorted(set.union(*(self._c2f[c] for c in categories)))

    def _resolve(self, fileids, categories):
        if fileids is not None and categories is not None:
            raise ValueError("Specify fileids or categories, not both")
        if categories is not None:
            return self.fileids(categories)
        else:
            return fileids

    def raw(self, fileids=None, categories=None):
        return super().raw(self._resolve(fileids, categories))

    def words(self, fileids=None, categories=None):
        return super().words(self._resolve(fileids, categories))

    def sents(self, fileids=None, categories=None):
        return super().sents(self._resolve(fileids, categories))

    def paras(self, fileids=None, categories=None):
        return super().paras(self._resolve(fileids, categories))


######################################################################
# { Treebank readers
######################################################################


# [xx] is it worth it to factor this out?
class SyntaxCorpusReader(CorpusReader):
    """
    An abstract base class for reading corpora consisting of
    syntactically parsed text.  Subclasses should define:

      - ``__init__``, which specifies the location of the corpus
        and a method for detecting the sentence blocks in corpus files.
      - ``_read_block``, which reads a block from the input stream.
      - ``_word``, which takes a block and returns a list of list of words.
      - ``_tag``, which takes a block and returns a list of list of tagged
        words.
      - ``_parse``, which takes a block and returns a list of parsed
        sentences.
    """

    def _parse(self, s):
        raise NotImplementedError()

    def _word(self, s):
        raise NotImplementedError()

    def _tag(self, s):
        raise NotImplementedError()

    def _read_block(self, stream):
        raise NotImplementedError()

    def parsed_sents(self, fileids=None):
        reader = self._read_parsed_sent_block
        return concat(
            [
                StreamBackedCorpusView(fileid, reader, encoding=enc)
                for fileid, enc in self.abspaths(fileids, True)
            ]
        )

    def tagged_sents(self, fileids=None, tagset=None):
        def reader(stream):
            return self._read_tagged_sent_block(stream, tagset)

        return concat(
            [
                StreamBackedCorpusView(fileid, reader, encoding=enc)
                for fileid, enc in self.abspaths(fileids, True)
            ]
        )

    def sents(self, fileids=None):
        reader = self._read_sent_block
        return concat(
            [
                StreamBackedCorpusView(fileid, reader, encoding=enc)
                for fileid, enc in self.abspaths(fileids, True)
            ]
        )

    def tagged_words(self, fileids=None, tagset=None):
        def reader(stream):
            return self._read_tagged_word_block(stream, tagset)

        return concat(
            [
                StreamBackedCorpusView(fileid, reader, encoding=enc)
                for fileid, enc in self.abspaths(fileids, True)
            ]
        )

    def words(self, fileids=None):
        return concat(
            [
                StreamBackedCorpusView(fileid, self._read_word_block, encoding=enc)
                for fileid, enc in self.abspaths(fileids, True)
            ]
        )

    # ------------------------------------------------------------
    # { Block Readers

    def _read_word_block(self, stream):
        return list(chain.from_iterable(self._read_sent_block(stream)))

    def _read_tagged_word_block(self, stream, tagset=None):
        return list(chain.from_iterable(self._read_tagged_sent_block(stream, tagset)))

    def _read_sent_block(self, stream):
        return list(filter(None, [self._word(t) for t in self._read_block(stream)]))

    def _read_tagged_sent_block(self, stream, tagset=None):
        return list(
            filter(None, [self._tag(t, tagset) for t in self._read_block(stream)])
        )

    def _read_parsed_sent_block(self, stream):
        return list(filter(None, [self._parse(t) for t in self._read_block(stream)]))

    # } End of Block Readers
    # ------------------------------------------------------------