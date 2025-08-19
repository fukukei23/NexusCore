
# === NexusCore/tools\exports\export_20250803_114325\combined_182.py ===

# === NexusCore/openenv\Lib\site-packages\zmq\ssh\tunnel.py ===
"""Basic ssh tunnel utilities, and convenience functions for tunneling
zeromq connections.
"""

# Copyright (C) 2010-2011  IPython Development Team
# Copyright (C) 2011- PyZMQ Developers
#
# Redistributed from IPython under the terms of the BSD License.

import atexit
import os
import re
import signal
import socket
import sys
import warnings
from getpass import getpass, getuser
from multiprocessing import Process

try:
    with warnings.catch_warnings():
        warnings.simplefilter('ignore', DeprecationWarning)
        import paramiko

        SSHException = paramiko.ssh_exception.SSHException
except ImportError:
    paramiko = None  # type: ignore

    class SSHException(Exception):  # type: ignore
        pass

else:
    from .forward import forward_tunnel

try:
    import pexpect
except ImportError:
    pexpect = None


class MaxRetryExceeded(Exception):
    pass


def select_random_ports(n):
    """Select and return n random ports that are available."""
    ports = []
    sockets = []
    for i in range(n):
        sock = socket.socket()
        sock.bind(('', 0))
        ports.append(sock.getsockname()[1])
        sockets.append(sock)
    for sock in sockets:
        sock.close()
    return ports


# -----------------------------------------------------------------------------
# Check for passwordless login
# -----------------------------------------------------------------------------
_password_pat = re.compile(rb'pass(word|phrase)', re.IGNORECASE)


def try_passwordless_ssh(server, keyfile, paramiko=None):
    """Attempt to make an ssh connection without a password.
    This is mainly used for requiring password input only once
    when many tunnels may be connected to the same server.

    If paramiko is None, the default for the platform is chosen.
    """
    if paramiko is None:
        paramiko = sys.platform == 'win32'
    if not paramiko:
        f = _try_passwordless_openssh
    else:
        f = _try_passwordless_paramiko
    return f(server, keyfile)


def _try_passwordless_openssh(server, keyfile):
    """Try passwordless login with shell ssh command."""
    if pexpect is None:
        raise ImportError("pexpect unavailable, use paramiko")
    cmd = 'ssh -f ' + server
    if keyfile:
        cmd += ' -i ' + keyfile
    cmd += ' exit'

    # pop SSH_ASKPASS from env
    env = os.environ.copy()
    env.pop('SSH_ASKPASS', None)

    ssh_newkey = 'Are you sure you want to continue connecting'
    p = pexpect.spawn(cmd, env=env)

    MAX_RETRY = 10

    for _ in range(MAX_RETRY):
        try:
            i = p.expect([ssh_newkey, _password_pat], timeout=0.1)
            if i == 0:
                raise SSHException(
                    'The authenticity of the host can\'t be established.'
                )
        except pexpect.TIMEOUT:
            continue
        except pexpect.EOF:
            return True
        else:
            return False

    raise MaxRetryExceeded(f"Failed after {MAX_RETRY} attempts")


def _try_passwordless_paramiko(server, keyfile):
    """Try passwordless login with paramiko."""
    if paramiko is None:
        msg = "Paramiko unavailable, "
        if sys.platform == 'win32':
            msg += "Paramiko is required for ssh tunneled connections on Windows."
        else:
            msg += "use OpenSSH."
        raise ImportError(msg)
    username, server, port = _split_server(server)
    client = paramiko.SSHClient()
    known_hosts = os.path.expanduser("~/.ssh/known_hosts")
    try:
        client.load_host_keys(known_hosts)
    except FileNotFoundError:
        pass

    policy_name = os.environ.get("PYZMQ_PARAMIKO_HOST_KEY_POLICY", None)
    if policy_name:
        policy = getattr(paramiko, f"{policy_name}Policy")
        client.set_missing_host_key_policy(policy())
    try:
        client.connect(
            server, port, username=username, key_filename=keyfile, look_for_keys=True
        )
    except paramiko.AuthenticationException:
        return False
    else:
        client.close()
        return True


def tunnel_connection(
    socket, addr, server, keyfile=None, password=None, paramiko=None, timeout=60
):
    """Connect a socket to an address via an ssh tunnel.

    This is a wrapper for socket.connect(addr), when addr is not accessible
    from the local machine.  It simply creates an ssh tunnel using the remaining args,
    and calls socket.connect('tcp://localhost:lport') where lport is the randomly
    selected local port of the tunnel.

    """
    new_url, tunnel = open_tunnel(
        addr,
        server,
        keyfile=keyfile,
        password=password,
        paramiko=paramiko,
        timeout=timeout,
    )
    socket.connect(new_url)
    return tunnel


def open_tunnel(addr, server, keyfile=None, password=None, paramiko=None, timeout=60):
    """Open a tunneled connection from a 0MQ url.

    For use inside tunnel_connection.

    Returns
    -------

    (url, tunnel) : (str, object)
        The 0MQ url that has been forwarded, and the tunnel object
    """

    lport = select_random_ports(1)[0]
    transport, addr = addr.split('://')
    ip, rport = addr.split(':')
    rport = int(rport)
    if paramiko is None:
        paramiko = sys.platform == 'win32'
    if paramiko:
        tunnelf = paramiko_tunnel
    else:
        tunnelf = openssh_tunnel

    tunnel = tunnelf(
        lport,
        rport,
        server,
        remoteip=ip,
        keyfile=keyfile,
        password=password,
        timeout=timeout,
    )
    return f'tcp://127.0.0.1:{lport}', tunnel


def openssh_tunnel(
    lport, rport, server, remoteip='127.0.0.1', keyfile=None, password=None, timeout=60
):
    """Create an ssh tunnel using command-line ssh that connects port lport
    on this machine to localhost:rport on server.  The tunnel
    will automatically close when not in use, remaining open
    for a minimum of timeout seconds for an initial connection.

    This creates a tunnel redirecting `localhost:lport` to `remoteip:rport`,
    as seen from `server`.

    keyfile and password may be specified, but ssh config is checked for defaults.

    Parameters
    ----------

    lport : int
        local port for connecting to the tunnel from this machine.
    rport : int
        port on the remote machine to connect to.
    server : str
        The ssh server to connect to. The full ssh server string will be parsed.
        user@server:port
    remoteip : str [Default: 127.0.0.1]
        The remote ip, specifying the destination of the tunnel.
        Default is localhost, which means that the tunnel would redirect
        localhost:lport on this machine to localhost:rport on the *server*.

    keyfile : str; path to private key file
        This specifies a key to be used in ssh login, default None.
        Regular default ssh keys will be used without specifying this argument.
    password : str;
        Your ssh password to the ssh server. Note that if this is left None,
        you will be prompted for it if passwordless key based login is unavailable.
    timeout : int [default: 60]
        The time (in seconds) after which no activity will result in the tunnel
        closing.  This prevents orphaned tunnels from running forever.
    """
    if pexpect is None:
        raise ImportError("pexpect unavailable, use paramiko_tunnel")
    ssh = "ssh "
    if keyfile:
        ssh += "-i " + keyfile

    if ':' in server:
        server, port = server.split(':')
        ssh += f" -p {port}"

    cmd = f"{ssh} -O check {server}"
    (output, exitstatus) = pexpect.run(cmd, withexitstatus=True)
    if not exitstatus:
        pid = int(output[output.find(b"(pid=") + 5 : output.find(b")")])
        cmd = f"{ssh} -O forward -L 127.0.0.1:{lport}:{remoteip}:{rport} {server}"
        (output, exitstatus) = pexpect.run(cmd, withexitstatus=True)
        if not exitstatus:
            atexit.register(_stop_tunnel, cmd.replace("-O forward", "-O cancel", 1))
            return pid
    cmd = f"{ssh} -f -S none -L 127.0.0.1:{lport}:{remoteip}:{rport} {server} sleep {timeout}"

    # pop SSH_ASKPASS from env
    env = os.environ.copy()
    env.pop('SSH_ASKPASS', None)

    ssh_newkey = 'Are you sure you want to continue connecting'
    tunnel = pexpect.spawn(cmd, env=env)
    failed = False
    MAX_RETRY = 10
    for _ in range(MAX_RETRY):
        try:
            i = tunnel.expect([ssh_newkey, _password_pat], timeout=0.1)
            if i == 0:
                raise SSHException(
                    'The authenticity of the host can\'t be established.'
                )
        except pexpect.TIMEOUT:
            continue
        except pexpect.EOF:
            if tunnel.exitstatus:
                print(tunnel.exitstatus)
                print(tunnel.before)
                print(tunnel.after)
                raise RuntimeError(f"tunnel '{cmd}' failed to start")
            else:
                return tunnel.pid
        else:
            if failed:
                print("Password rejected, try again")
                password = None
            if password is None:
                password = getpass(f"{server}'s password: ")
            tunnel.sendline(password)
            failed = True
    raise MaxRetryExceeded(f"Failed after {MAX_RETRY} attempts")


def _stop_tunnel(cmd):
    pexpect.run(cmd)


def _split_server(server):
    if '@' in server:
        username, server = server.split('@', 1)
    else:
        username = getuser()
    if ':' in server:
        server, port = server.split(':')
        port = int(port)
    else:
        port = 22
    return username, server, port


def paramiko_tunnel(
    lport, rport, server, remoteip='127.0.0.1', keyfile=None, password=None, timeout=60
):
    """launch a tunner with paramiko in a subprocess. This should only be used
    when shell ssh is unavailable (e.g. Windows).

    This creates a tunnel redirecting `localhost:lport` to `remoteip:rport`,
    as seen from `server`.

    If you are familiar with ssh tunnels, this creates the tunnel:

    ssh server -L localhost:lport:remoteip:rport

    keyfile and password may be specified, but ssh config is checked for defaults.


    Parameters
    ----------

    lport : int
        local port for connecting to the tunnel from this machine.
    rport : int
        port on the remote machine to connect to.
    server : str
        The ssh server to connect to. The full ssh server string will be parsed.
        user@server:port
    remoteip : str [Default: 127.0.0.1]
        The remote ip, specifying the destination of the tunnel.
        Default is localhost, which means that the tunnel would redirect
        localhost:lport on this machine to localhost:rport on the *server*.

    keyfile : str; path to private key file
        This specifies a key to be used in ssh login, default None.
        Regular default ssh keys will be used without specifying this argument.
    password : str;
        Your ssh password to the ssh server. Note that if this is left None,
        you will be prompted for it if passwordless key based login is unavailable.
    timeout : int [default: 60]
        The time (in seconds) after which no activity will result in the tunnel
        closing.  This prevents orphaned tunnels from running forever.

    """
    if paramiko is None:
        raise ImportError("Paramiko not available")

    if password is None:
        if not _try_passwordless_paramiko(server, keyfile):
            password = getpass(f"{server}'s password: ")

    p = Process(
        target=_paramiko_tunnel,
        args=(lport, rport, server, remoteip),
        kwargs=dict(keyfile=keyfile, password=password),
    )
    p.daemon = True
    p.start()
    return p


def _paramiko_tunnel(lport, rport, server, remoteip, keyfile=None, password=None):
    """Function for actually starting a paramiko tunnel, to be passed
    to multiprocessing.Process(target=this), and not called directly.
    """
    username, server, port = _split_server(server)
    client = paramiko.SSHClient()
    client.load_system_host_keys()
    client.set_missing_host_key_policy(paramiko.WarningPolicy())

    try:
        client.connect(
            server,
            port,
            username=username,
            key_filename=keyfile,
            look_for_keys=True,
            password=password,
        )
    #    except paramiko.AuthenticationException:
    #        if password is None:
    #            password = getpass("%s@%s's password: "%(username, server))
    #            client.connect(server, port, username=username, password=password)
    #        else:
    #            raise
    except Exception as e:
        print(f'*** Failed to connect to {server}:{port}: {e!r}')
        sys.exit(1)

    # Don't let SIGINT kill the tunnel subprocess
    signal.signal(signal.SIGINT, signal.SIG_IGN)

    try:
        forward_tunnel(lport, remoteip, rport, client.get_transport())
    except KeyboardInterrupt:
        print('SIGINT: Port forwarding stopped cleanly')
        sys.exit(0)
    except Exception as e:
        print(f"Port forwarding stopped uncleanly: {e}")
        sys.exit(255)


if sys.platform == 'win32':
    ssh_tunnel = paramiko_tunnel
else:
    ssh_tunnel = openssh_tunnel


__all__ = [
    'tunnel_connection',
    'ssh_tunnel',
    'openssh_tunnel',
    'paramiko_tunnel',
    'try_passwordless_ssh',
]

# === NexusCore/openenv\Lib\site-packages\googleapiclient\model.py ===
# Copyright 2014 Google Inc. All Rights Reserved.
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

"""Model objects for requests and responses.

Each API may support one or more serializations, such
as JSON, Atom, etc. The model classes are responsible
for converting between the wire format and the Python
object representation.
"""
from __future__ import absolute_import

__author__ = "jcgregorio@google.com (Joe Gregorio)"

import json
import logging
import platform
import urllib
import warnings

from googleapiclient import version as googleapiclient_version
from googleapiclient.errors import HttpError

try:
    from google.api_core.version_header import API_VERSION_METADATA_KEY

    HAS_API_VERSION = True
except ImportError:
    HAS_API_VERSION = False

_LIBRARY_VERSION = googleapiclient_version.__version__
_PY_VERSION = platform.python_version()

LOGGER = logging.getLogger(__name__)

dump_request_response = False


def _abstract():
    raise NotImplementedError("You need to override this function")


class Model(object):
    """Model base class.

    All Model classes should implement this interface.
    The Model serializes and de-serializes between a wire
    format such as JSON and a Python object representation.
    """

    def request(self, headers, path_params, query_params, body_value):
        """Updates outgoing requests with a serialized body.

        Args:
          headers: dict, request headers
          path_params: dict, parameters that appear in the request path
          query_params: dict, parameters that appear in the query
          body_value: object, the request body as a Python object, which must be
                      serializable.
        Returns:
          A tuple of (headers, path_params, query, body)

          headers: dict, request headers
          path_params: dict, parameters that appear in the request path
          query: string, query part of the request URI
          body: string, the body serialized in the desired wire format.
        """
        _abstract()

    def response(self, resp, content):
        """Convert the response wire format into a Python object.

        Args:
          resp: httplib2.Response, the HTTP response headers and status
          content: string, the body of the HTTP response

        Returns:
          The body de-serialized as a Python object.

        Raises:
          googleapiclient.errors.HttpError if a non 2xx response is received.
        """
        _abstract()


class BaseModel(Model):
    """Base model class.

    Subclasses should provide implementations for the "serialize" and
    "deserialize" methods, as well as values for the following class attributes.

    Attributes:
      accept: The value to use for the HTTP Accept header.
      content_type: The value to use for the HTTP Content-type header.
      no_content_response: The value to return when deserializing a 204 "No
          Content" response.
      alt_param: The value to supply as the "alt" query parameter for requests.
    """

    accept = None
    content_type = None
    no_content_response = None
    alt_param = None

    def _log_request(self, headers, path_params, query, body):
        """Logs debugging information about the request if requested."""
        if dump_request_response:
            LOGGER.info("--request-start--")
            LOGGER.info("-headers-start-")
            for h, v in headers.items():
                LOGGER.info("%s: %s", h, v)
            LOGGER.info("-headers-end-")
            LOGGER.info("-path-parameters-start-")
            for h, v in path_params.items():
                LOGGER.info("%s: %s", h, v)
            LOGGER.info("-path-parameters-end-")
            LOGGER.info("body: %s", body)
            LOGGER.info("query: %s", query)
            LOGGER.info("--request-end--")

    def request(self, headers, path_params, query_params, body_value, api_version=None):
        """Updates outgoing requests with a serialized body.

        Args:
          headers: dict, request headers
          path_params: dict, parameters that appear in the request path
          query_params: dict, parameters that appear in the query
          body_value: object, the request body as a Python object, which must be
              serializable by json.
          api_version: str, The precise API version represented by this request,
              which will result in an API Version header being sent along with the
              HTTP request.
        Returns:
          A tuple of (headers, path_params, query, body)

          headers: dict, request headers
          path_params: dict, parameters that appear in the request path
          query: string, query part of the request URI
          body: string, the body serialized as JSON
        """
        query = self._build_query(query_params)
        headers["accept"] = self.accept
        headers["accept-encoding"] = "gzip, deflate"
        if "user-agent" in headers:
            headers["user-agent"] += " "
        else:
            headers["user-agent"] = ""
        headers["user-agent"] += "(gzip)"
        if "x-goog-api-client" in headers:
            headers["x-goog-api-client"] += " "
        else:
            headers["x-goog-api-client"] = ""
        headers["x-goog-api-client"] += "gdcl/%s gl-python/%s" % (
            _LIBRARY_VERSION,
            _PY_VERSION,
        )

        if api_version and HAS_API_VERSION:
            headers[API_VERSION_METADATA_KEY] = api_version
        elif api_version:
            warnings.warn(
                "The `api_version` argument is ignored as a newer version of "
                "`google-api-core` is required to use this feature."
                "Please upgrade `google-api-core` to 2.19.0 or newer."
            )

        if body_value is not None:
            headers["content-type"] = self.content_type
            body_value = self.serialize(body_value)
        self._log_request(headers, path_params, query, body_value)
        return (headers, path_params, query, body_value)

    def _build_query(self, params):
        """Builds a query string.

        Args:
          params: dict, the query parameters

        Returns:
          The query parameters properly encoded into an HTTP URI query string.
        """
        if self.alt_param is not None:
            params.update({"alt": self.alt_param})
        astuples = []
        for key, value in params.items():
            if type(value) == type([]):
                for x in value:
                    x = x.encode("utf-8")
                    astuples.append((key, x))
            else:
                if isinstance(value, str) and callable(value.encode):
                    value = value.encode("utf-8")
                astuples.append((key, value))
        return "?" + urllib.parse.urlencode(astuples)

    def _log_response(self, resp, content):
        """Logs debugging information about the response if requested."""
        if dump_request_response:
            LOGGER.info("--response-start--")
            for h, v in resp.items():
                LOGGER.info("%s: %s", h, v)
            if content:
                LOGGER.info(content)
            LOGGER.info("--response-end--")

    def response(self, resp, content):
        """Convert the response wire format into a Python object.

        Args:
          resp: httplib2.Response, the HTTP response headers and status
          content: string, the body of the HTTP response

        Returns:
          The body de-serialized as a Python object.

        Raises:
          googleapiclient.errors.HttpError if a non 2xx response is received.
        """
        self._log_response(resp, content)
        # Error handling is TBD, for example, do we retry
        # for some operation/error combinations?
        if resp.status < 300:
            if resp.status == 204:
                # A 204: No Content response should be treated differently
                # to all the other success states
                return self.no_content_response
            return self.deserialize(content)
        else:
            LOGGER.debug("Content from bad request was: %r" % content)
            raise HttpError(resp, content)

    def serialize(self, body_value):
        """Perform the actual Python object serialization.

        Args:
          body_value: object, the request body as a Python object.

        Returns:
          string, the body in serialized form.
        """
        _abstract()

    def deserialize(self, content):
        """Perform the actual deserialization from response string to Python
        object.

        Args:
          content: string, the body of the HTTP response

        Returns:
          The body de-serialized as a Python object.
        """
        _abstract()


class JsonModel(BaseModel):
    """Model class for JSON.

    Serializes and de-serializes between JSON and the Python
    object representation of HTTP request and response bodies.
    """

    accept = "application/json"
    content_type = "application/json"
    alt_param = "json"

    def __init__(self, data_wrapper=False):
        """Construct a JsonModel.

        Args:
          data_wrapper: boolean, wrap requests and responses in a data wrapper
        """
        self._data_wrapper = data_wrapper

    def serialize(self, body_value):
        if (
            isinstance(body_value, dict)
            and "data" not in body_value
            and self._data_wrapper
        ):
            body_value = {"data": body_value}
        return json.dumps(body_value)

    def deserialize(self, content):
        try:
            content = content.decode("utf-8")
        except AttributeError:
            pass
        try:
            body = json.loads(content)
        except json.decoder.JSONDecodeError:
            body = content
        else:
            if self._data_wrapper and "data" in body:
                body = body["data"]
        return body

    @property
    def no_content_response(self):
        return {}


class RawModel(JsonModel):
    """Model class for requests that don't return JSON.

    Serializes and de-serializes between JSON and the Python
    object representation of HTTP request, and returns the raw bytes
    of the response body.
    """

    accept = "*/*"
    content_type = "application/json"
    alt_param = None

    def deserialize(self, content):
        return content

    @property
    def no_content_response(self):
        return ""


class MediaModel(JsonModel):
    """Model class for requests that return Media.

    Serializes and de-serializes between JSON and the Python
    object representation of HTTP request, and returns the raw bytes
    of the response body.
    """

    accept = "*/*"
    content_type = "application/json"
    alt_param = "media"

    def deserialize(self, content):
        return content

    @property
    def no_content_response(self):
        return ""


class ProtocolBufferModel(BaseModel):
    """Model class for protocol buffers.

    Serializes and de-serializes the binary protocol buffer sent in the HTTP
    request and response bodies.
    """

    accept = "application/x-protobuf"
    content_type = "application/x-protobuf"
    alt_param = "proto"

    def __init__(self, protocol_buffer):
        """Constructs a ProtocolBufferModel.

        The serialized protocol buffer returned in an HTTP response will be
        de-serialized using the given protocol buffer class.

        Args:
          protocol_buffer: The protocol buffer class used to de-serialize a
          response from the API.
        """
        self._protocol_buffer = protocol_buffer

    def serialize(self, body_value):
        return body_value.SerializeToString()

    def deserialize(self, content):
        return self._protocol_buffer.FromString(content)

    @property
    def no_content_response(self):
        return self._protocol_buffer()


def makepatch(original, modified):
    """Create a patch object.

    Some methods support PATCH, an efficient way to send updates to a resource.
    This method allows the easy construction of patch bodies by looking at the
    differences between a resource before and after it was modified.

    Args:
      original: object, the original deserialized resource
      modified: object, the modified deserialized resource
    Returns:
      An object that contains only the changes from original to modified, in a
      form suitable to pass to a PATCH method.

    Example usage:
      item = service.activities().get(postid=postid, userid=userid).execute()
      original = copy.deepcopy(item)
      item['object']['content'] = 'This is updated.'
      service.activities.patch(postid=postid, userid=userid,
        body=makepatch(original, item)).execute()
    """
    patch = {}
    for key, original_value in original.items():
        modified_value = modified.get(key, None)
        if modified_value is None:
            # Use None to signal that the element is deleted
            patch[key] = None
        elif original_value != modified_value:
            if type(original_value) == type({}):
                # Recursively descend objects
                patch[key] = makepatch(original_value, modified_value)
            else:
                # In the case of simple types or arrays we just replace
                patch[key] = modified_value
        else:
            # Don't add anything to patch if there's no change
            pass
    for key in modified:
        if key not in original:
            patch[key] = modified[key]

    return patch

# === NexusCore/openenv\Lib\site-packages\google\auth\pluggable.py ===
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

"""Pluggable Credentials.
Pluggable Credentials are initialized using external_account arguments which
are typically loaded from third-party executables. Unlike other
credentials that can be initialized with a list of explicit arguments, secrets
or credentials, external account clients use the environment and hints/guidelines
provided by the external_account JSON file to retrieve credentials and exchange
them for Google access tokens.

Example credential_source for pluggable credential:
{
    "executable": {
        "command": "/path/to/get/credentials.sh --arg1=value1 --arg2=value2",
        "timeout_millis": 5000,
        "output_file": "/path/to/generated/cached/credentials"
    }
}
"""

try:
    from collections.abc import Mapping
# Python 2.7 compatibility
except ImportError:  # pragma: NO COVER
    from collections import Mapping  # type: ignore
import json
import os
import subprocess
import sys
import time

from google.auth import _helpers
from google.auth import exceptions
from google.auth import external_account

# The max supported executable spec version.
EXECUTABLE_SUPPORTED_MAX_VERSION = 1

EXECUTABLE_TIMEOUT_MILLIS_DEFAULT = 30 * 1000  # 30 seconds
EXECUTABLE_TIMEOUT_MILLIS_LOWER_BOUND = 5 * 1000  # 5 seconds
EXECUTABLE_TIMEOUT_MILLIS_UPPER_BOUND = 120 * 1000  # 2 minutes

EXECUTABLE_INTERACTIVE_TIMEOUT_MILLIS_LOWER_BOUND = 30 * 1000  # 30 seconds
EXECUTABLE_INTERACTIVE_TIMEOUT_MILLIS_UPPER_BOUND = 30 * 60 * 1000  # 30 minutes


class Credentials(external_account.Credentials):
    """External account credentials sourced from executables."""

    def __init__(
        self,
        audience,
        subject_token_type,
        token_url,
        credential_source,
        *args,
        **kwargs
    ):
        """Instantiates an external account credentials object from a executables.

        Args:
            audience (str): The STS audience field.
            subject_token_type (str): The subject token type.
            token_url (str): The STS endpoint URL.
            credential_source (Mapping): The credential source dictionary used to
                provide instructions on how to retrieve external credential to be
                exchanged for Google access tokens.

                Example credential_source for pluggable credential:

                    {
                        "executable": {
                            "command": "/path/to/get/credentials.sh --arg1=value1 --arg2=value2",
                            "timeout_millis": 5000,
                            "output_file": "/path/to/generated/cached/credentials"
                        }
                    }
            args (List): Optional positional arguments passed into the underlying :meth:`~external_account.Credentials.__init__` method.
            kwargs (Mapping): Optional keyword arguments passed into the underlying :meth:`~external_account.Credentials.__init__` method.

        Raises:
            google.auth.exceptions.RefreshError: If an error is encountered during
                access token retrieval logic.
            google.auth.exceptions.InvalidValue: For invalid parameters.
            google.auth.exceptions.MalformedError: For invalid parameters.

        .. note:: Typically one of the helper constructors
            :meth:`from_file` or
            :meth:`from_info` are used instead of calling the constructor directly.
        """

        self.interactive = kwargs.pop("interactive", False)
        super(Credentials, self).__init__(
            audience=audience,
            subject_token_type=subject_token_type,
            token_url=token_url,
            credential_source=credential_source,
            *args,
            **kwargs
        )
        if not isinstance(credential_source, Mapping):
            self._credential_source_executable = None
            raise exceptions.MalformedError(
                "Missing credential_source. The credential_source is not a dict."
            )
        self._credential_source_executable = credential_source.get("executable")
        if not self._credential_source_executable:
            raise exceptions.MalformedError(
                "Missing credential_source. An 'executable' must be provided."
            )
        self._credential_source_executable_command = self._credential_source_executable.get(
            "command"
        )
        self._credential_source_executable_timeout_millis = self._credential_source_executable.get(
            "timeout_millis"
        )
        self._credential_source_executable_interactive_timeout_millis = self._credential_source_executable.get(
            "interactive_timeout_millis"
        )
        self._credential_source_executable_output_file = self._credential_source_executable.get(
            "output_file"
        )

        # Dummy value. This variable is only used via injection, not exposed to ctor
        self._tokeninfo_username = ""

        if not self._credential_source_executable_command:
            raise exceptions.MalformedError(
                "Missing command field. Executable command must be provided."
            )
        if not self._credential_source_executable_timeout_millis:
            self._credential_source_executable_timeout_millis = (
                EXECUTABLE_TIMEOUT_MILLIS_DEFAULT
            )
        elif (
            self._credential_source_executable_timeout_millis
            < EXECUTABLE_TIMEOUT_MILLIS_LOWER_BOUND
            or self._credential_source_executable_timeout_millis
            > EXECUTABLE_TIMEOUT_MILLIS_UPPER_BOUND
        ):
            raise exceptions.InvalidValue("Timeout must be between 5 and 120 seconds.")

        if self._credential_source_executable_interactive_timeout_millis:
            if (
                self._credential_source_executable_interactive_timeout_millis
                < EXECUTABLE_INTERACTIVE_TIMEOUT_MILLIS_LOWER_BOUND
                or self._credential_source_executable_interactive_timeout_millis
                > EXECUTABLE_INTERACTIVE_TIMEOUT_MILLIS_UPPER_BOUND
            ):
                raise exceptions.InvalidValue(
                    "Interactive timeout must be between 30 seconds and 30 minutes."
                )

    @_helpers.copy_docstring(external_account.Credentials)
    def retrieve_subject_token(self, request):
        self._validate_running_mode()

        # Check output file.
        if self._credential_source_executable_output_file is not None:
            try:
                with open(
                    self._credential_source_executable_output_file, encoding="utf-8"
                ) as output_file:
                    response = json.load(output_file)
            except Exception:
                pass
            else:
                try:
                    # If the cached response is expired, _parse_subject_token will raise an error which will be ignored and we will call the executable again.
                    subject_token = self._parse_subject_token(response)
                    if (
                        "expiration_time" not in response
                    ):  # Always treat missing expiration_time as expired and proceed to executable run.
                        raise exceptions.RefreshError
                except (exceptions.MalformedError, exceptions.InvalidValue):
                    raise
                except exceptions.RefreshError:
                    pass
                else:
                    return subject_token

        if not _helpers.is_python_3():
            raise exceptions.RefreshError(
                "Pluggable auth is only supported for python 3.7+"
            )

        # Inject env vars.
        env = os.environ.copy()
        self._inject_env_variables(env)
        env["GOOGLE_EXTERNAL_ACCOUNT_REVOKE"] = "0"

        # Run executable.
        exe_timeout = (
            self._credential_source_executable_interactive_timeout_millis / 1000
            if self.interactive
            else self._credential_source_executable_timeout_millis / 1000
        )
        exe_stdin = sys.stdin if self.interactive else None
        exe_stdout = sys.stdout if self.interactive else subprocess.PIPE
        exe_stderr = sys.stdout if self.interactive else subprocess.STDOUT

        result = subprocess.run(
            self._credential_source_executable_command.split(),
            timeout=exe_timeout,
            stdin=exe_stdin,
            stdout=exe_stdout,
            stderr=exe_stderr,
            env=env,
        )
        if result.returncode != 0:
            raise exceptions.RefreshError(
                "Executable exited with non-zero return code {}. Error: {}".format(
                    result.returncode, result.stdout
                )
            )

        # Handle executable output.
        response = json.loads(result.stdout.decode("utf-8")) if result.stdout else None
        if not response and self._credential_source_executable_output_file is not None:
            response = json.load(
                open(self._credential_source_executable_output_file, encoding="utf-8")
            )

        subject_token = self._parse_subject_token(response)
        return subject_token

    def revoke(self, request):
        """Revokes the subject token using the credential_source object.

        Args:
            request (google.auth.transport.Request): A callable used to make
                HTTP requests.
        Raises:
            google.auth.exceptions.RefreshError: If the executable revocation
                not properly executed.

        """
        if not self.interactive:
            raise exceptions.InvalidValue(
                "Revoke is only enabled under interactive mode."
            )
        self._validate_running_mode()

        if not _helpers.is_python_3():
            raise exceptions.RefreshError(
                "Pluggable auth is only supported for python 3.7+"
            )

        # Inject variables
        env = os.environ.copy()
        self._inject_env_variables(env)
        env["GOOGLE_EXTERNAL_ACCOUNT_REVOKE"] = "1"

        # Run executable
        result = subprocess.run(
            self._credential_source_executable_command.split(),
            timeout=self._credential_source_executable_interactive_timeout_millis
            / 1000,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            env=env,
        )

        if result.returncode != 0:
            raise exceptions.RefreshError(
                "Auth revoke failed on executable. Exit with non-zero return code {}. Error: {}".format(
                    result.returncode, result.stdout
                )
            )

        response = json.loads(result.stdout.decode("utf-8"))
        self._validate_revoke_response(response)

    @property
    def external_account_id(self):
        """Returns the external account identifier.

        When service account impersonation is used the identifier is the service
        account email.

        Without service account impersonation, this returns None, unless it is
        being used by the Google Cloud CLI which populates this field.
        """

        return self.service_account_email or self._tokeninfo_username

    @classmethod
    def from_info(cls, info, **kwargs):
        """Creates a Pluggable Credentials instance from parsed external account info.

        Args:
            info (Mapping[str, str]): The Pluggable external account info in Google
                format.
            kwargs: Additional arguments to pass to the constructor.

        Returns:
            google.auth.pluggable.Credentials: The constructed
                credentials.

        Raises:
            google.auth.exceptions.InvalidValue: For invalid parameters.
            google.auth.exceptions.MalformedError: For invalid parameters.
        """
        return super(Credentials, cls).from_info(info, **kwargs)

    @classmethod
    def from_file(cls, filename, **kwargs):
        """Creates an Pluggable Credentials instance from an external account json file.

        Args:
            filename (str): The path to the Pluggable external account json file.
            kwargs: Additional arguments to pass to the constructor.

        Returns:
            google.auth.pluggable.Credentials: The constructed
                credentials.
        """
        return super(Credentials, cls).from_file(filename, **kwargs)

    def _inject_env_variables(self, env):
        env["GOOGLE_EXTERNAL_ACCOUNT_AUDIENCE"] = self._audience
        env["GOOGLE_EXTERNAL_ACCOUNT_TOKEN_TYPE"] = self._subject_token_type
        env["GOOGLE_EXTERNAL_ACCOUNT_ID"] = self.external_account_id
        env["GOOGLE_EXTERNAL_ACCOUNT_INTERACTIVE"] = "1" if self.interactive else "0"

        if self._service_account_impersonation_url is not None:
            env[
                "GOOGLE_EXTERNAL_ACCOUNT_IMPERSONATED_EMAIL"
            ] = self.service_account_email
        if self._credential_source_executable_output_file is not None:
            env[
                "GOOGLE_EXTERNAL_ACCOUNT_OUTPUT_FILE"
            ] = self._credential_source_executable_output_file

    def _parse_subject_token(self, response):
        self._validate_response_schema(response)
        if not response["success"]:
            if "code" not in response or "message" not in response:
                raise exceptions.MalformedError(
                    "Error code and message fields are required in the response."
                )
            raise exceptions.RefreshError(
                "Executable returned unsuccessful response: code: {}, message: {}.".format(
                    response["code"], response["message"]
                )
            )
        if "expiration_time" in response and response["expiration_time"] < time.time():
            raise exceptions.RefreshError(
                "The token returned by the executable is expired."
            )
        if "token_type" not in response:
            raise exceptions.MalformedError(
                "The executable response is missing the token_type field."
            )
        if (
            response["token_type"] == "urn:ietf:params:oauth:token-type:jwt"
            or response["token_type"] == "urn:ietf:params:oauth:token-type:id_token"
        ):  # OIDC
            return response["id_token"]
        elif response["token_type"] == "urn:ietf:params:oauth:token-type:saml2":  # SAML
            return response["saml_response"]
        else:
            raise exceptions.RefreshError("Executable returned unsupported token type.")

    def _validate_revoke_response(self, response):
        self._validate_response_schema(response)
        if not response["success"]:
            raise exceptions.RefreshError("Revoke failed with unsuccessful response.")

    def _validate_response_schema(self, response):
        if "version" not in response:
            raise exceptions.MalformedError(
                "The executable response is missing the version field."
            )
        if response["version"] > EXECUTABLE_SUPPORTED_MAX_VERSION:
            raise exceptions.RefreshError(
                "Executable returned unsupported version {}.".format(
                    response["version"]
                )
            )

        if "success" not in response:
            raise exceptions.MalformedError(
                "The executable response is missing the success field."
            )

    def _validate_running_mode(self):
        env_allow_executables = os.environ.get(
            "GOOGLE_EXTERNAL_ACCOUNT_ALLOW_EXECUTABLES"
        )
        if env_allow_executables != "1":
            raise exceptions.MalformedError(
                "Executables need to be explicitly allowed (set GOOGLE_EXTERNAL_ACCOUNT_ALLOW_EXECUTABLES to '1') to run."
            )

        if self.interactive and not self._credential_source_executable_output_file:
            raise exceptions.MalformedError(
                "An output_file must be specified in the credential configuration for interactive mode."
            )

        if (
            self.interactive
            and not self._credential_source_executable_interactive_timeout_millis
        ):
            raise exceptions.InvalidOperation(
                "Interactive mode cannot run without an interactive timeout."
            )

        if self.interactive and not self.is_workforce_pool:
            raise exceptions.InvalidValue(
                "Interactive mode is only enabled for workforce pool."
            )

    def _create_default_metrics_options(self):
        metrics_options = super(Credentials, self)._create_default_metrics_options()
        metrics_options["source"] = "executable"
        return metrics_options

# === NexusCore/openenv\Lib\site-packages\google\ai\generativelanguage_v1beta3\types\text_service.py ===
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
from __future__ import annotations

from typing import MutableMapping, MutableSequence

import proto  # type: ignore

from google.ai.generativelanguage_v1beta3.types import citation, safety

__protobuf__ = proto.module(
    package="google.ai.generativelanguage.v1beta3",
    manifest={
        "GenerateTextRequest",
        "GenerateTextResponse",
        "TextPrompt",
        "TextCompletion",
        "EmbedTextRequest",
        "EmbedTextResponse",
        "BatchEmbedTextRequest",
        "BatchEmbedTextResponse",
        "Embedding",
        "CountTextTokensRequest",
        "CountTextTokensResponse",
    },
)


class GenerateTextRequest(proto.Message):
    r"""Request to generate a text completion response from the
    model.


    .. _oneof: https://proto-plus-python.readthedocs.io/en/stable/fields.html#oneofs-mutually-exclusive-fields

    Attributes:
        model (str):
            Required. The name of the ``Model`` or ``TunedModel`` to use
            for generating the completion. Examples:
            models/text-bison-001 tunedModels/sentence-translator-u3b7m
        prompt (google.ai.generativelanguage_v1beta3.types.TextPrompt):
            Required. The free-form input text given to
            the model as a prompt.
            Given a prompt, the model will generate a
            TextCompletion response it predicts as the
            completion of the input text.
        temperature (float):
            Optional. Controls the randomness of the output. Note: The
            default value varies by model, see the ``Model.temperature``
            attribute of the ``Model`` returned the ``getModel``
            function.

            Values can range from [0.0,1.0], inclusive. A value closer
            to 1.0 will produce responses that are more varied and
            creative, while a value closer to 0.0 will typically result
            in more straightforward responses from the model.

            This field is a member of `oneof`_ ``_temperature``.
        candidate_count (int):
            Optional. Number of generated responses to return.

            This value must be between [1, 8], inclusive. If unset, this
            will default to 1.

            This field is a member of `oneof`_ ``_candidate_count``.
        max_output_tokens (int):
            Optional. The maximum number of tokens to include in a
            candidate.

            If unset, this will default to output_token_limit specified
            in the ``Model`` specification.

            This field is a member of `oneof`_ ``_max_output_tokens``.
        top_p (float):
            Optional. The maximum cumulative probability of tokens to
            consider when sampling.

            The model uses combined Top-k and nucleus sampling.

            Tokens are sorted based on their assigned probabilities so
            that only the most likely tokens are considered. Top-k
            sampling directly limits the maximum number of tokens to
            consider, while Nucleus sampling limits number of tokens
            based on the cumulative probability.

            Note: The default value varies by model, see the
            ``Model.top_p`` attribute of the ``Model`` returned the
            ``getModel`` function.

            This field is a member of `oneof`_ ``_top_p``.
        top_k (int):
            Optional. The maximum number of tokens to consider when
            sampling.

            The model uses combined Top-k and nucleus sampling.

            Top-k sampling considers the set of ``top_k`` most probable
            tokens. Defaults to 40.

            Note: The default value varies by model, see the
            ``Model.top_k`` attribute of the ``Model`` returned the
            ``getModel`` function.

            This field is a member of `oneof`_ ``_top_k``.
        safety_settings (MutableSequence[google.ai.generativelanguage_v1beta3.types.SafetySetting]):
            A list of unique ``SafetySetting`` instances for blocking
            unsafe content.

            that will be enforced on the ``GenerateTextRequest.prompt``
            and ``GenerateTextResponse.candidates``. There should not be
            more than one setting for each ``SafetyCategory`` type. The
            API will block any prompts and responses that fail to meet
            the thresholds set by these settings. This list overrides
            the default settings for each ``SafetyCategory`` specified
            in the safety_settings. If there is no ``SafetySetting`` for
            a given ``SafetyCategory`` provided in the list, the API
            will use the default safety setting for that category.
        stop_sequences (MutableSequence[str]):
            The set of character sequences (up to 5) that
            will stop output generation. If specified, the
            API will stop at the first appearance of a stop
            sequence. The stop sequence will not be included
            as part of the response.
    """

    model: str = proto.Field(
        proto.STRING,
        number=1,
    )
    prompt: "TextPrompt" = proto.Field(
        proto.MESSAGE,
        number=2,
        message="TextPrompt",
    )
    temperature: float = proto.Field(
        proto.FLOAT,
        number=3,
        optional=True,
    )
    candidate_count: int = proto.Field(
        proto.INT32,
        number=4,
        optional=True,
    )
    max_output_tokens: int = proto.Field(
        proto.INT32,
        number=5,
        optional=True,
    )
    top_p: float = proto.Field(
        proto.FLOAT,
        number=6,
        optional=True,
    )
    top_k: int = proto.Field(
        proto.INT32,
        number=7,
        optional=True,
    )
    safety_settings: MutableSequence[safety.SafetySetting] = proto.RepeatedField(
        proto.MESSAGE,
        number=8,
        message=safety.SafetySetting,
    )
    stop_sequences: MutableSequence[str] = proto.RepeatedField(
        proto.STRING,
        number=9,
    )


class GenerateTextResponse(proto.Message):
    r"""The response from the model, including candidate completions.

    Attributes:
        candidates (MutableSequence[google.ai.generativelanguage_v1beta3.types.TextCompletion]):
            Candidate responses from the model.
        filters (MutableSequence[google.ai.generativelanguage_v1beta3.types.ContentFilter]):
            A set of content filtering metadata for the prompt and
            response text.

            This indicates which ``SafetyCategory``\ (s) blocked a
            candidate from this response, the lowest ``HarmProbability``
            that triggered a block, and the HarmThreshold setting for
            that category. This indicates the smallest change to the
            ``SafetySettings`` that would be necessary to unblock at
            least 1 response.

            The blocking is configured by the ``SafetySettings`` in the
            request (or the default ``SafetySettings`` of the API).
        safety_feedback (MutableSequence[google.ai.generativelanguage_v1beta3.types.SafetyFeedback]):
            Returns any safety feedback related to
            content filtering.
    """

    candidates: MutableSequence["TextCompletion"] = proto.RepeatedField(
        proto.MESSAGE,
        number=1,
        message="TextCompletion",
    )
    filters: MutableSequence[safety.ContentFilter] = proto.RepeatedField(
        proto.MESSAGE,
        number=3,
        message=safety.ContentFilter,
    )
    safety_feedback: MutableSequence[safety.SafetyFeedback] = proto.RepeatedField(
        proto.MESSAGE,
        number=4,
        message=safety.SafetyFeedback,
    )


class TextPrompt(proto.Message):
    r"""Text given to the model as a prompt.

    The Model will use this TextPrompt to Generate a text
    completion.

    Attributes:
        text (str):
            Required. The prompt text.
    """

    text: str = proto.Field(
        proto.STRING,
        number=1,
    )


class TextCompletion(proto.Message):
    r"""Output text returned from a model.

    .. _oneof: https://proto-plus-python.readthedocs.io/en/stable/fields.html#oneofs-mutually-exclusive-fields

    Attributes:
        output (str):
            Output only. The generated text returned from
            the model.
        safety_ratings (MutableSequence[google.ai.generativelanguage_v1beta3.types.SafetyRating]):
            Ratings for the safety of a response.

            There is at most one rating per category.
        citation_metadata (google.ai.generativelanguage_v1beta3.types.CitationMetadata):
            Output only. Citation information for model-generated
            ``output`` in this ``TextCompletion``.

            This field may be populated with attribution information for
            any text included in the ``output``.

            This field is a member of `oneof`_ ``_citation_metadata``.
    """

    output: str = proto.Field(
        proto.STRING,
        number=1,
    )
    safety_ratings: MutableSequence[safety.SafetyRating] = proto.RepeatedField(
        proto.MESSAGE,
        number=2,
        message=safety.SafetyRating,
    )
    citation_metadata: citation.CitationMetadata = proto.Field(
        proto.MESSAGE,
        number=3,
        optional=True,
        message=citation.CitationMetadata,
    )


class EmbedTextRequest(proto.Message):
    r"""Request to get a text embedding from the model.

    Attributes:
        model (str):
            Required. The model name to use with the
            format model=models/{model}.
        text (str):
            Required. The free-form input text that the
            model will turn into an embedding.
    """

    model: str = proto.Field(
        proto.STRING,
        number=1,
    )
    text: str = proto.Field(
        proto.STRING,
        number=2,
    )


class EmbedTextResponse(proto.Message):
    r"""The response to a EmbedTextRequest.

    .. _oneof: https://proto-plus-python.readthedocs.io/en/stable/fields.html#oneofs-mutually-exclusive-fields

    Attributes:
        embedding (google.ai.generativelanguage_v1beta3.types.Embedding):
            Output only. The embedding generated from the
            input text.

            This field is a member of `oneof`_ ``_embedding``.
    """

    embedding: "Embedding" = proto.Field(
        proto.MESSAGE,
        number=1,
        optional=True,
        message="Embedding",
    )


class BatchEmbedTextRequest(proto.Message):
    r"""Batch request to get a text embedding from the model.

    Attributes:
        model (str):
            Required. The name of the ``Model`` to use for generating
            the embedding. Examples: models/embedding-gecko-001
        texts (MutableSequence[str]):
            Required. The free-form input texts that the
            model will turn into an embedding.  The current
            limit is 100 texts, over which an error will be
            thrown.
    """

    model: str = proto.Field(
        proto.STRING,
        number=1,
    )
    texts: MutableSequence[str] = proto.RepeatedField(
        proto.STRING,
        number=2,
    )


class BatchEmbedTextResponse(proto.Message):
    r"""The response to a EmbedTextRequest.

    Attributes:
        embeddings (MutableSequence[google.ai.generativelanguage_v1beta3.types.Embedding]):
            Output only. The embeddings generated from
            the input text.
    """

    embeddings: MutableSequence["Embedding"] = proto.RepeatedField(
        proto.MESSAGE,
        number=1,
        message="Embedding",
    )


class Embedding(proto.Message):
    r"""A list of floats representing the embedding.

    Attributes:
        value (MutableSequence[float]):
            The embedding values.
    """

    value: MutableSequence[float] = proto.RepeatedField(
        proto.FLOAT,
        number=1,
    )


class CountTextTokensRequest(proto.Message):
    r"""Counts the number of tokens in the ``prompt`` sent to a model.

    Models may tokenize text differently, so each model may return a
    different ``token_count``.

    Attributes:
        model (str):
            Required. The model's resource name. This serves as an ID
            for the Model to use.

            This name should match a model name returned by the
            ``ListModels`` method.

            Format: ``models/{model}``
        prompt (google.ai.generativelanguage_v1beta3.types.TextPrompt):
            Required. The free-form input text given to
            the model as a prompt.
    """

    model: str = proto.Field(
        proto.STRING,
        number=1,
    )
    prompt: "TextPrompt" = proto.Field(
        proto.MESSAGE,
        number=2,
        message="TextPrompt",
    )


class CountTextTokensResponse(proto.Message):
    r"""A response from ``CountTextTokens``.

    It returns the model's ``token_count`` for the ``prompt``.

    Attributes:
        token_count (int):
            The number of tokens that the ``model`` tokenizes the
            ``prompt`` into.

            Always non-negative.
    """

    token_count: int = proto.Field(
        proto.INT32,
        number=1,
    )


__all__ = tuple(sorted(__protobuf__.manifest))

# === NexusCore/openenv\Lib\site-packages\aiohttp\client_ws.py ===
"""WebSocket client for asyncio."""

import asyncio
import sys
from types import TracebackType
from typing import Any, Optional, Type, cast

import attr

from ._websocket.reader import WebSocketDataQueue
from .client_exceptions import ClientError, ServerTimeoutError, WSMessageTypeError
from .client_reqrep import ClientResponse
from .helpers import calculate_timeout_when, set_result
from .http import (
    WS_CLOSED_MESSAGE,
    WS_CLOSING_MESSAGE,
    WebSocketError,
    WSCloseCode,
    WSMessage,
    WSMsgType,
)
from .http_websocket import _INTERNAL_RECEIVE_TYPES, WebSocketWriter
from .streams import EofStream
from .typedefs import (
    DEFAULT_JSON_DECODER,
    DEFAULT_JSON_ENCODER,
    JSONDecoder,
    JSONEncoder,
)

if sys.version_info >= (3, 11):
    import asyncio as async_timeout
else:
    import async_timeout


@attr.s(frozen=True, slots=True)
class ClientWSTimeout:
    ws_receive = attr.ib(type=Optional[float], default=None)
    ws_close = attr.ib(type=Optional[float], default=None)


DEFAULT_WS_CLIENT_TIMEOUT = ClientWSTimeout(ws_receive=None, ws_close=10.0)


class ClientWebSocketResponse:
    def __init__(
        self,
        reader: WebSocketDataQueue,
        writer: WebSocketWriter,
        protocol: Optional[str],
        response: ClientResponse,
        timeout: ClientWSTimeout,
        autoclose: bool,
        autoping: bool,
        loop: asyncio.AbstractEventLoop,
        *,
        heartbeat: Optional[float] = None,
        compress: int = 0,
        client_notakeover: bool = False,
    ) -> None:
        self._response = response
        self._conn = response.connection

        self._writer = writer
        self._reader = reader
        self._protocol = protocol
        self._closed = False
        self._closing = False
        self._close_code: Optional[int] = None
        self._timeout = timeout
        self._autoclose = autoclose
        self._autoping = autoping
        self._heartbeat = heartbeat
        self._heartbeat_cb: Optional[asyncio.TimerHandle] = None
        self._heartbeat_when: float = 0.0
        if heartbeat is not None:
            self._pong_heartbeat = heartbeat / 2.0
        self._pong_response_cb: Optional[asyncio.TimerHandle] = None
        self._loop = loop
        self._waiting: bool = False
        self._close_wait: Optional[asyncio.Future[None]] = None
        self._exception: Optional[BaseException] = None
        self._compress = compress
        self._client_notakeover = client_notakeover
        self._ping_task: Optional[asyncio.Task[None]] = None

        self._reset_heartbeat()

    def _cancel_heartbeat(self) -> None:
        self._cancel_pong_response_cb()
        if self._heartbeat_cb is not None:
            self._heartbeat_cb.cancel()
            self._heartbeat_cb = None
        if self._ping_task is not None:
            self._ping_task.cancel()
            self._ping_task = None

    def _cancel_pong_response_cb(self) -> None:
        if self._pong_response_cb is not None:
            self._pong_response_cb.cancel()
            self._pong_response_cb = None

    def _reset_heartbeat(self) -> None:
        if self._heartbeat is None:
            return
        self._cancel_pong_response_cb()
        loop = self._loop
        assert loop is not None
        conn = self._conn
        timeout_ceil_threshold = (
            conn._connector._timeout_ceil_threshold if conn is not None else 5
        )
        now = loop.time()
        when = calculate_timeout_when(now, self._heartbeat, timeout_ceil_threshold)
        self._heartbeat_when = when
        if self._heartbeat_cb is None:
            # We do not cancel the previous heartbeat_cb here because
            # it generates a significant amount of TimerHandle churn
            # which causes asyncio to rebuild the heap frequently.
            # Instead _send_heartbeat() will reschedule the next
            # heartbeat if it fires too early.
            self._heartbeat_cb = loop.call_at(when, self._send_heartbeat)

    def _send_heartbeat(self) -> None:
        self._heartbeat_cb = None
        loop = self._loop
        now = loop.time()
        if now < self._heartbeat_when:
            # Heartbeat fired too early, reschedule
            self._heartbeat_cb = loop.call_at(
                self._heartbeat_when, self._send_heartbeat
            )
            return

        conn = self._conn
        timeout_ceil_threshold = (
            conn._connector._timeout_ceil_threshold if conn is not None else 5
        )
        when = calculate_timeout_when(now, self._pong_heartbeat, timeout_ceil_threshold)
        self._cancel_pong_response_cb()
        self._pong_response_cb = loop.call_at(when, self._pong_not_received)

        coro = self._writer.send_frame(b"", WSMsgType.PING)
        if sys.version_info >= (3, 12):
            # Optimization for Python 3.12, try to send the ping
            # immediately to avoid having to schedule
            # the task on the event loop.
            ping_task = asyncio.Task(coro, loop=loop, eager_start=True)
        else:
            ping_task = loop.create_task(coro)

        if not ping_task.done():
            self._ping_task = ping_task
            ping_task.add_done_callback(self._ping_task_done)
        else:
            self._ping_task_done(ping_task)

    def _ping_task_done(self, task: "asyncio.Task[None]") -> None:
        """Callback for when the ping task completes."""
        if not task.cancelled() and (exc := task.exception()):
            self._handle_ping_pong_exception(exc)
        self._ping_task = None

    def _pong_not_received(self) -> None:
        self._handle_ping_pong_exception(
            ServerTimeoutError(f"No PONG received after {self._pong_heartbeat} seconds")
        )

    def _handle_ping_pong_exception(self, exc: BaseException) -> None:
        """Handle exceptions raised during ping/pong processing."""
        if self._closed:
            return
        self._set_closed()
        self._close_code = WSCloseCode.ABNORMAL_CLOSURE
        self._exception = exc
        self._response.close()
        if self._waiting and not self._closing:
            self._reader.feed_data(WSMessage(WSMsgType.ERROR, exc, None), 0)

    def _set_closed(self) -> None:
        """Set the connection to closed.

        Cancel any heartbeat timers and set the closed flag.
        """
        self._closed = True
        self._cancel_heartbeat()

    def _set_closing(self) -> None:
        """Set the connection to closing.

        Cancel any heartbeat timers and set the closing flag.
        """
        self._closing = True
        self._cancel_heartbeat()

    @property
    def closed(self) -> bool:
        return self._closed

    @property
    def close_code(self) -> Optional[int]:
        return self._close_code

    @property
    def protocol(self) -> Optional[str]:
        return self._protocol

    @property
    def compress(self) -> int:
        return self._compress

    @property
    def client_notakeover(self) -> bool:
        return self._client_notakeover

    def get_extra_info(self, name: str, default: Any = None) -> Any:
        """extra info from connection transport"""
        conn = self._response.connection
        if conn is None:
            return default
        transport = conn.transport
        if transport is None:
            return default
        return transport.get_extra_info(name, default)

    def exception(self) -> Optional[BaseException]:
        return self._exception

    async def ping(self, message: bytes = b"") -> None:
        await self._writer.send_frame(message, WSMsgType.PING)

    async def pong(self, message: bytes = b"") -> None:
        await self._writer.send_frame(message, WSMsgType.PONG)

    async def send_frame(
        self, message: bytes, opcode: WSMsgType, compress: Optional[int] = None
    ) -> None:
        """Send a frame over the websocket."""
        await self._writer.send_frame(message, opcode, compress)

    async def send_str(self, data: str, compress: Optional[int] = None) -> None:
        if not isinstance(data, str):
            raise TypeError("data argument must be str (%r)" % type(data))
        await self._writer.send_frame(
            data.encode("utf-8"), WSMsgType.TEXT, compress=compress
        )

    async def send_bytes(self, data: bytes, compress: Optional[int] = None) -> None:
        if not isinstance(data, (bytes, bytearray, memoryview)):
            raise TypeError("data argument must be byte-ish (%r)" % type(data))
        await self._writer.send_frame(data, WSMsgType.BINARY, compress=compress)

    async def send_json(
        self,
        data: Any,
        compress: Optional[int] = None,
        *,
        dumps: JSONEncoder = DEFAULT_JSON_ENCODER,
    ) -> None:
        await self.send_str(dumps(data), compress=compress)

    async def close(self, *, code: int = WSCloseCode.OK, message: bytes = b"") -> bool:
        # we need to break `receive()` cycle first,
        # `close()` may be called from different task
        if self._waiting and not self._closing:
            assert self._loop is not None
            self._close_wait = self._loop.create_future()
            self._set_closing()
            self._reader.feed_data(WS_CLOSING_MESSAGE, 0)
            await self._close_wait

        if self._closed:
            return False

        self._set_closed()
        try:
            await self._writer.close(code, message)
        except asyncio.CancelledError:
            self._close_code = WSCloseCode.ABNORMAL_CLOSURE
            self._response.close()
            raise
        except Exception as exc:
            self._close_code = WSCloseCode.ABNORMAL_CLOSURE
            self._exception = exc
            self._response.close()
            return True

        if self._close_code:
            self._response.close()
            return True

        while True:
            try:
                async with async_timeout.timeout(self._timeout.ws_close):
                    msg = await self._reader.read()
            except asyncio.CancelledError:
                self._close_code = WSCloseCode.ABNORMAL_CLOSURE
                self._response.close()
                raise
            except Exception as exc:
                self._close_code = WSCloseCode.ABNORMAL_CLOSURE
                self._exception = exc
                self._response.close()
                return True

            if msg.type is WSMsgType.CLOSE:
                self._close_code = msg.data
                self._response.close()
                return True

    async def receive(self, timeout: Optional[float] = None) -> WSMessage:
        receive_timeout = timeout or self._timeout.ws_receive

        while True:
            if self._waiting:
                raise RuntimeError("Concurrent call to receive() is not allowed")

            if self._closed:
                return WS_CLOSED_MESSAGE
            elif self._closing:
                await self.close()
                return WS_CLOSED_MESSAGE

            try:
                self._waiting = True
                try:
                    if receive_timeout:
                        # Entering the context manager and creating
                        # Timeout() object can take almost 50% of the
                        # run time in this loop so we avoid it if
                        # there is no read timeout.
                        async with async_timeout.timeout(receive_timeout):
                            msg = await self._reader.read()
                    else:
                        msg = await self._reader.read()
                    self._reset_heartbeat()
                finally:
                    self._waiting = False
                    if self._close_wait:
                        set_result(self._close_wait, None)
            except (asyncio.CancelledError, asyncio.TimeoutError):
                self._close_code = WSCloseCode.ABNORMAL_CLOSURE
                raise
            except EofStream:
                self._close_code = WSCloseCode.OK
                await self.close()
                return WSMessage(WSMsgType.CLOSED, None, None)
            except ClientError:
                # Likely ServerDisconnectedError when connection is lost
                self._set_closed()
                self._close_code = WSCloseCode.ABNORMAL_CLOSURE
                return WS_CLOSED_MESSAGE
            except WebSocketError as exc:
                self._close_code = exc.code
                await self.close(code=exc.code)
                return WSMessage(WSMsgType.ERROR, exc, None)
            except Exception as exc:
                self._exception = exc
                self._set_closing()
                self._close_code = WSCloseCode.ABNORMAL_CLOSURE
                await self.close()
                return WSMessage(WSMsgType.ERROR, exc, None)

            if msg.type not in _INTERNAL_RECEIVE_TYPES:
                # If its not a close/closing/ping/pong message
                # we can return it immediately
                return msg

            if msg.type is WSMsgType.CLOSE:
                self._set_closing()
                self._close_code = msg.data
                if not self._closed and self._autoclose:
                    await self.close()
            elif msg.type is WSMsgType.CLOSING:
                self._set_closing()
            elif msg.type is WSMsgType.PING and self._autoping:
                await self.pong(msg.data)
                continue
            elif msg.type is WSMsgType.PONG and self._autoping:
                continue

            return msg

    async def receive_str(self, *, timeout: Optional[float] = None) -> str:
        msg = await self.receive(timeout)
        if msg.type is not WSMsgType.TEXT:
            raise WSMessageTypeError(
                f"Received message {msg.type}:{msg.data!r} is not WSMsgType.TEXT"
            )
        return cast(str, msg.data)

    async def receive_bytes(self, *, timeout: Optional[float] = None) -> bytes:
        msg = await self.receive(timeout)
        if msg.type is not WSMsgType.BINARY:
            raise WSMessageTypeError(
                f"Received message {msg.type}:{msg.data!r} is not WSMsgType.BINARY"
            )
        return cast(bytes, msg.data)

    async def receive_json(
        self,
        *,
        loads: JSONDecoder = DEFAULT_JSON_DECODER,
        timeout: Optional[float] = None,
    ) -> Any:
        data = await self.receive_str(timeout=timeout)
        return loads(data)

    def __aiter__(self) -> "ClientWebSocketResponse":
        return self

    async def __anext__(self) -> WSMessage:
        msg = await self.receive()
        if msg.type in (WSMsgType.CLOSE, WSMsgType.CLOSING, WSMsgType.CLOSED):
            raise StopAsyncIteration
        return msg

    async def __aenter__(self) -> "ClientWebSocketResponse":
        return self

    async def __aexit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[TracebackType],
    ) -> None:
        await self.close()

# === NexusCore/openenv\Lib\site-packages\google\ai\generativelanguage_v1beta\services\cache_service\transports\grpc_asyncio.py ===
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
from typing import Awaitable, Callable, Dict, Optional, Sequence, Tuple, Union
import warnings

from google.api_core import exceptions as core_exceptions
from google.api_core import gapic_v1, grpc_helpers_async
from google.api_core import retry_async as retries
from google.auth import credentials as ga_credentials  # type: ignore
from google.auth.transport.grpc import SslCredentials  # type: ignore
from google.longrunning import operations_pb2  # type: ignore
from google.protobuf import empty_pb2  # type: ignore
import grpc  # type: ignore
from grpc.experimental import aio  # type: ignore

from google.ai.generativelanguage_v1beta.types import (
    cached_content as gag_cached_content,
)
from google.ai.generativelanguage_v1beta.types import cache_service
from google.ai.generativelanguage_v1beta.types import cached_content

from .base import DEFAULT_CLIENT_INFO, CacheServiceTransport
from .grpc import CacheServiceGrpcTransport


class CacheServiceGrpcAsyncIOTransport(CacheServiceTransport):
    """gRPC AsyncIO backend transport for CacheService.

    API for managing cache of content (CachedContent resources)
    that can be used in GenerativeService requests. This way
    generate content requests can benefit from preprocessing work
    being done earlier, possibly lowering their computational cost.
    It is intended to be used with large contexts.

    This class defines the same methods as the primary client, so the
    primary client can load the underlying transport implementation
    and call it.

    It sends protocol buffers over the wire using gRPC (which is built on
    top of HTTP/2); the ``grpcio`` package must be installed.
    """

    _grpc_channel: aio.Channel
    _stubs: Dict[str, Callable] = {}

    @classmethod
    def create_channel(
        cls,
        host: str = "generativelanguage.googleapis.com",
        credentials: Optional[ga_credentials.Credentials] = None,
        credentials_file: Optional[str] = None,
        scopes: Optional[Sequence[str]] = None,
        quota_project_id: Optional[str] = None,
        **kwargs,
    ) -> aio.Channel:
        """Create and return a gRPC AsyncIO channel object.
        Args:
            host (Optional[str]): The host for the channel to use.
            credentials (Optional[~.Credentials]): The
                authorization credentials to attach to requests. These
                credentials identify this application to the service. If
                none are specified, the client will attempt to ascertain
                the credentials from the environment.
            credentials_file (Optional[str]): A file with credentials that can
                be loaded with :func:`google.auth.load_credentials_from_file`.
            scopes (Optional[Sequence[str]]): A optional list of scopes needed for this
                service. These are only used when credentials are not specified and
                are passed to :func:`google.auth.default`.
            quota_project_id (Optional[str]): An optional project to use for billing
                and quota.
            kwargs (Optional[dict]): Keyword arguments, which are passed to the
                channel creation.
        Returns:
            aio.Channel: A gRPC AsyncIO channel object.
        """

        return grpc_helpers_async.create_channel(
            host,
            credentials=credentials,
            credentials_file=credentials_file,
            quota_project_id=quota_project_id,
            default_scopes=cls.AUTH_SCOPES,
            scopes=scopes,
            default_host=cls.DEFAULT_HOST,
            **kwargs,
        )

    def __init__(
        self,
        *,
        host: str = "generativelanguage.googleapis.com",
        credentials: Optional[ga_credentials.Credentials] = None,
        credentials_file: Optional[str] = None,
        scopes: Optional[Sequence[str]] = None,
        channel: Optional[Union[aio.Channel, Callable[..., aio.Channel]]] = None,
        api_mtls_endpoint: Optional[str] = None,
        client_cert_source: Optional[Callable[[], Tuple[bytes, bytes]]] = None,
        ssl_channel_credentials: Optional[grpc.ChannelCredentials] = None,
        client_cert_source_for_mtls: Optional[Callable[[], Tuple[bytes, bytes]]] = None,
        quota_project_id: Optional[str] = None,
        client_info: gapic_v1.client_info.ClientInfo = DEFAULT_CLIENT_INFO,
        always_use_jwt_access: Optional[bool] = False,
        api_audience: Optional[str] = None,
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
                This argument is ignored if a ``channel`` instance is provided.
            credentials_file (Optional[str]): A file with credentials that can
                be loaded with :func:`google.auth.load_credentials_from_file`.
                This argument is ignored if a ``channel`` instance is provided.
            scopes (Optional[Sequence[str]]): A optional list of scopes needed for this
                service. These are only used when credentials are not specified and
                are passed to :func:`google.auth.default`.
            channel (Optional[Union[aio.Channel, Callable[..., aio.Channel]]]):
                A ``Channel`` instance through which to make calls, or a Callable
                that constructs and returns one. If set to None, ``self.create_channel``
                is used to create the channel. If a Callable is given, it will be called
                with the same arguments as used in ``self.create_channel``.
            api_mtls_endpoint (Optional[str]): Deprecated. The mutual TLS endpoint.
                If provided, it overrides the ``host`` argument and tries to create
                a mutual TLS channel with client SSL credentials from
                ``client_cert_source`` or application default SSL credentials.
            client_cert_source (Optional[Callable[[], Tuple[bytes, bytes]]]):
                Deprecated. A callback to provide client SSL certificate bytes and
                private key bytes, both in PEM format. It is ignored if
                ``api_mtls_endpoint`` is None.
            ssl_channel_credentials (grpc.ChannelCredentials): SSL credentials
                for the grpc channel. It is ignored if a ``channel`` instance is provided.
            client_cert_source_for_mtls (Optional[Callable[[], Tuple[bytes, bytes]]]):
                A callback to provide client certificate bytes and private key bytes,
                both in PEM format. It is used to configure a mutual TLS channel. It is
                ignored if a ``channel`` instance or ``ssl_channel_credentials`` is provided.
            quota_project_id (Optional[str]): An optional project to use for billing
                and quota.
            client_info (google.api_core.gapic_v1.client_info.ClientInfo):
                The client info used to send a user-agent string along with
                API requests. If ``None``, then default info will be used.
                Generally, you only need to set this if you're developing
                your own client library.
            always_use_jwt_access (Optional[bool]): Whether self signed JWT should
                be used for service account credentials.

        Raises:
            google.auth.exceptions.MutualTlsChannelError: If mutual TLS transport
              creation failed for any reason.
          google.api_core.exceptions.DuplicateCredentialArgs: If both ``credentials``
              and ``credentials_file`` are passed.
        """
        self._grpc_channel = None
        self._ssl_channel_credentials = ssl_channel_credentials
        self._stubs: Dict[str, Callable] = {}

        if api_mtls_endpoint:
            warnings.warn("api_mtls_endpoint is deprecated", DeprecationWarning)
        if client_cert_source:
            warnings.warn("client_cert_source is deprecated", DeprecationWarning)

        if isinstance(channel, aio.Channel):
            # Ignore credentials if a channel was passed.
            credentials = False
            # If a channel was explicitly provided, set it.
            self._grpc_channel = channel
            self._ssl_channel_credentials = None
        else:
            if api_mtls_endpoint:
                host = api_mtls_endpoint

                # Create SSL credentials with client_cert_source or application
                # default SSL credentials.
                if client_cert_source:
                    cert, key = client_cert_source()
                    self._ssl_channel_credentials = grpc.ssl_channel_credentials(
                        certificate_chain=cert, private_key=key
                    )
                else:
                    self._ssl_channel_credentials = SslCredentials().ssl_credentials

            else:
                if client_cert_source_for_mtls and not ssl_channel_credentials:
                    cert, key = client_cert_source_for_mtls()
                    self._ssl_channel_credentials = grpc.ssl_channel_credentials(
                        certificate_chain=cert, private_key=key
                    )

        # The base transport sets the host, credentials and scopes
        super().__init__(
            host=host,
            credentials=credentials,
            credentials_file=credentials_file,
            scopes=scopes,
            quota_project_id=quota_project_id,
            client_info=client_info,
            always_use_jwt_access=always_use_jwt_access,
            api_audience=api_audience,
        )

        if not self._grpc_channel:
            # initialize with the provided callable or the default channel
            channel_init = channel or type(self).create_channel
            self._grpc_channel = channel_init(
                self._host,
                # use the credentials which are saved
                credentials=self._credentials,
                # Set ``credentials_file`` to ``None`` here as
                # the credentials that we saved earlier should be used.
                credentials_file=None,
                scopes=self._scopes,
                ssl_credentials=self._ssl_channel_credentials,
                quota_project_id=quota_project_id,
                options=[
                    ("grpc.max_send_message_length", -1),
                    ("grpc.max_receive_message_length", -1),
                ],
            )

        # Wrap messages. This must be done after self._grpc_channel exists
        self._prep_wrapped_messages(client_info)

    @property
    def grpc_channel(self) -> aio.Channel:
        """Create the channel designed to connect to this service.

        This property caches on the instance; repeated calls return
        the same channel.
        """
        # Return the channel from cache.
        return self._grpc_channel

    @property
    def list_cached_contents(
        self,
    ) -> Callable[
        [cache_service.ListCachedContentsRequest],
        Awaitable[cache_service.ListCachedContentsResponse],
    ]:
        r"""Return a callable for the list cached contents method over gRPC.

        Lists CachedContents.

        Returns:
            Callable[[~.ListCachedContentsRequest],
                    Awaitable[~.ListCachedContentsResponse]]:
                A function that, when called, will call the underlying RPC
                on the server.
        """
        # Generate a "stub function" on-the-fly which will actually make
        # the request.
        # gRPC handles serialization and deserialization, so we just need
        # to pass in the functions for each.
        if "list_cached_contents" not in self._stubs:
            self._stubs["list_cached_contents"] = self.grpc_channel.unary_unary(
                "/google.ai.generativelanguage.v1beta.CacheService/ListCachedContents",
                request_serializer=cache_service.ListCachedContentsRequest.serialize,
                response_deserializer=cache_service.ListCachedContentsResponse.deserialize,
            )
        return self._stubs["list_cached_contents"]

    @property
    def create_cached_content(
        self,
    ) -> Callable[
        [cache_service.CreateCachedContentRequest],
        Awaitable[gag_cached_content.CachedContent],
    ]:
        r"""Return a callable for the create cached content method over gRPC.

        Creates CachedContent resource.

        Returns:
            Callable[[~.CreateCachedContentRequest],
                    Awaitable[~.CachedContent]]:
                A function that, when called, will call the underlying RPC
                on the server.
        """
        # Generate a "stub function" on-the-fly which will actually make
        # the request.
        # gRPC handles serialization and deserialization, so we just need
        # to pass in the functions for each.
        if "create_cached_content" not in self._stubs:
            self._stubs["create_cached_content"] = self.grpc_channel.unary_unary(
                "/google.ai.generativelanguage.v1beta.CacheService/CreateCachedContent",
                request_serializer=cache_service.CreateCachedContentRequest.serialize,
                response_deserializer=gag_cached_content.CachedContent.deserialize,
            )
        return self._stubs["create_cached_content"]

    @property
    def get_cached_content(
        self,
    ) -> Callable[
        [cache_service.GetCachedContentRequest], Awaitable[cached_content.CachedContent]
    ]:
        r"""Return a callable for the get cached content method over gRPC.

        Reads CachedContent resource.

        Returns:
            Callable[[~.GetCachedContentRequest],
                    Awaitable[~.CachedContent]]:
                A function that, when called, will call the underlying RPC
                on the server.
        """
        # Generate a "stub function" on-the-fly which will actually make
        # the request.
        # gRPC handles serialization and deserialization, so we just need
        # to pass in the functions for each.
        if "get_cached_content" not in self._stubs:
            self._stubs["get_cached_content"] = self.grpc_channel.unary_unary(
                "/google.ai.generativelanguage.v1beta.CacheService/GetCachedContent",
                request_serializer=cache_service.GetCachedContentRequest.serialize,
                response_deserializer=cached_content.CachedContent.deserialize,
            )
        return self._stubs["get_cached_content"]

    @property
    def update_cached_content(
        self,
    ) -> Callable[
        [cache_service.UpdateCachedContentRequest],
        Awaitable[gag_cached_content.CachedContent],
    ]:
        r"""Return a callable for the update cached content method over gRPC.

        Updates CachedContent resource (only expiration is
        updatable).

        Returns:
            Callable[[~.UpdateCachedContentRequest],
                    Awaitable[~.CachedContent]]:
                A function that, when called, will call the underlying RPC
                on the server.
        """
        # Generate a "stub function" on-the-fly which will actually make
        # the request.
        # gRPC handles serialization and deserialization, so we just need
        # to pass in the functions for each.
        if "update_cached_content" not in self._stubs:
            self._stubs["update_cached_content"] = self.grpc_channel.unary_unary(
                "/google.ai.generativelanguage.v1beta.CacheService/UpdateCachedContent",
                request_serializer=cache_service.UpdateCachedContentRequest.serialize,
                response_deserializer=gag_cached_content.CachedContent.deserialize,
            )
        return self._stubs["update_cached_content"]

    @property
    def delete_cached_content(
        self,
    ) -> Callable[
        [cache_service.DeleteCachedContentRequest], Awaitable[empty_pb2.Empty]
    ]:
        r"""Return a callable for the delete cached content method over gRPC.

        Deletes CachedContent resource.

        Returns:
            Callable[[~.DeleteCachedContentRequest],
                    Awaitable[~.Empty]]:
                A function that, when called, will call the underlying RPC
                on the server.
        """
        # Generate a "stub function" on-the-fly which will actually make
        # the request.
        # gRPC handles serialization and deserialization, so we just need
        # to pass in the functions for each.
        if "delete_cached_content" not in self._stubs:
            self._stubs["delete_cached_content"] = self.grpc_channel.unary_unary(
                "/google.ai.generativelanguage.v1beta.CacheService/DeleteCachedContent",
                request_serializer=cache_service.DeleteCachedContentRequest.serialize,
                response_deserializer=empty_pb2.Empty.FromString,
            )
        return self._stubs["delete_cached_content"]

    def _prep_wrapped_messages(self, client_info):
        """Precompute the wrapped methods, overriding the base class method to use async wrappers."""
        self._wrapped_methods = {
            self.list_cached_contents: gapic_v1.method_async.wrap_method(
                self.list_cached_contents,
                default_timeout=None,
                client_info=client_info,
            ),
            self.create_cached_content: gapic_v1.method_async.wrap_method(
                self.create_cached_content,
                default_timeout=None,
                client_info=client_info,
            ),
            self.get_cached_content: gapic_v1.method_async.wrap_method(
                self.get_cached_content,
                default_timeout=None,
                client_info=client_info,
            ),
            self.update_cached_content: gapic_v1.method_async.wrap_method(
                self.update_cached_content,
                default_timeout=None,
                client_info=client_info,
            ),
            self.delete_cached_content: gapic_v1.method_async.wrap_method(
                self.delete_cached_content,
                default_timeout=None,
                client_info=client_info,
            ),
        }

    def close(self):
        return self.grpc_channel.close()


__all__ = ("CacheServiceGrpcAsyncIOTransport",)

# === NexusCore/openenv\Lib\site-packages\prompt_toolkit\contrib\telnet\server.py ===
"""
Telnet server.
"""

from __future__ import annotations

import asyncio
import contextvars
import socket
from asyncio import get_running_loop
from typing import Any, Callable, Coroutine, TextIO, cast

from prompt_toolkit.application.current import create_app_session, get_app
from prompt_toolkit.application.run_in_terminal import run_in_terminal
from prompt_toolkit.data_structures import Size
from prompt_toolkit.formatted_text import AnyFormattedText, to_formatted_text
from prompt_toolkit.input import PipeInput, create_pipe_input
from prompt_toolkit.output.vt100 import Vt100_Output
from prompt_toolkit.renderer import print_formatted_text as print_formatted_text
from prompt_toolkit.styles import BaseStyle, DummyStyle

from .log import logger
from .protocol import (
    DO,
    ECHO,
    IAC,
    LINEMODE,
    MODE,
    NAWS,
    SB,
    SE,
    SEND,
    SUPPRESS_GO_AHEAD,
    TTYPE,
    WILL,
    TelnetProtocolParser,
)

__all__ = [
    "TelnetServer",
]


def int2byte(number: int) -> bytes:
    return bytes((number,))


def _initialize_telnet(connection: socket.socket) -> None:
    logger.info("Initializing telnet connection")

    # Iac Do Linemode
    connection.send(IAC + DO + LINEMODE)

    # Suppress Go Ahead. (This seems important for Putty to do correct echoing.)
    # This will allow bi-directional operation.
    connection.send(IAC + WILL + SUPPRESS_GO_AHEAD)

    # Iac sb
    connection.send(IAC + SB + LINEMODE + MODE + int2byte(0) + IAC + SE)

    # IAC Will Echo
    connection.send(IAC + WILL + ECHO)

    # Negotiate window size
    connection.send(IAC + DO + NAWS)

    # Negotiate terminal type
    # Assume the client will accept the negotiation with `IAC +  WILL + TTYPE`
    connection.send(IAC + DO + TTYPE)

    # We can then select the first terminal type supported by the client,
    # which is generally the best type the client supports
    # The client should reply with a `IAC + SB  + TTYPE + IS + ttype + IAC + SE`
    connection.send(IAC + SB + TTYPE + SEND + IAC + SE)


class _ConnectionStdout:
    """
    Wrapper around socket which provides `write` and `flush` methods for the
    Vt100_Output output.
    """

    def __init__(self, connection: socket.socket, encoding: str) -> None:
        self._encoding = encoding
        self._connection = connection
        self._errors = "strict"
        self._buffer: list[bytes] = []
        self._closed = False

    def write(self, data: str) -> None:
        data = data.replace("\n", "\r\n")
        self._buffer.append(data.encode(self._encoding, errors=self._errors))
        self.flush()

    def isatty(self) -> bool:
        return True

    def flush(self) -> None:
        try:
            if not self._closed:
                self._connection.send(b"".join(self._buffer))
        except OSError as e:
            logger.warning(f"Couldn't send data over socket: {e}")

        self._buffer = []

    def close(self) -> None:
        self._closed = True

    @property
    def encoding(self) -> str:
        return self._encoding

    @property
    def errors(self) -> str:
        return self._errors


class TelnetConnection:
    """
    Class that represents one Telnet connection.
    """

    def __init__(
        self,
        conn: socket.socket,
        addr: tuple[str, int],
        interact: Callable[[TelnetConnection], Coroutine[Any, Any, None]],
        server: TelnetServer,
        encoding: str,
        style: BaseStyle | None,
        vt100_input: PipeInput,
        enable_cpr: bool = True,
    ) -> None:
        self.conn = conn
        self.addr = addr
        self.interact = interact
        self.server = server
        self.encoding = encoding
        self.style = style
        self._closed = False
        self._ready = asyncio.Event()
        self.vt100_input = vt100_input
        self.enable_cpr = enable_cpr
        self.vt100_output: Vt100_Output | None = None

        # Create "Output" object.
        self.size = Size(rows=40, columns=79)

        # Initialize.
        _initialize_telnet(conn)

        # Create output.
        def get_size() -> Size:
            return self.size

        self.stdout = cast(TextIO, _ConnectionStdout(conn, encoding=encoding))

        def data_received(data: bytes) -> None:
            """TelnetProtocolParser 'data_received' callback"""
            self.vt100_input.send_bytes(data)

        def size_received(rows: int, columns: int) -> None:
            """TelnetProtocolParser 'size_received' callback"""
            self.size = Size(rows=rows, columns=columns)
            if self.vt100_output is not None and self.context:
                self.context.run(lambda: get_app()._on_resize())

        def ttype_received(ttype: str) -> None:
            """TelnetProtocolParser 'ttype_received' callback"""
            self.vt100_output = Vt100_Output(
                self.stdout, get_size, term=ttype, enable_cpr=enable_cpr
            )
            self._ready.set()

        self.parser = TelnetProtocolParser(data_received, size_received, ttype_received)
        self.context: contextvars.Context | None = None

    async def run_application(self) -> None:
        """
        Run application.
        """

        def handle_incoming_data() -> None:
            data = self.conn.recv(1024)
            if data:
                self.feed(data)
            else:
                # Connection closed by client.
                logger.info("Connection closed by client. {!r} {!r}".format(*self.addr))
                self.close()

        # Add reader.
        loop = get_running_loop()
        loop.add_reader(self.conn, handle_incoming_data)

        try:
            # Wait for v100_output to be properly instantiated
            await self._ready.wait()
            with create_app_session(input=self.vt100_input, output=self.vt100_output):
                self.context = contextvars.copy_context()
                await self.interact(self)
        finally:
            self.close()

    def feed(self, data: bytes) -> None:
        """
        Handler for incoming data. (Called by TelnetServer.)
        """
        self.parser.feed(data)

    def close(self) -> None:
        """
        Closed by client.
        """
        if not self._closed:
            self._closed = True

            self.vt100_input.close()
            get_running_loop().remove_reader(self.conn)
            self.conn.close()
            self.stdout.close()

    def send(self, formatted_text: AnyFormattedText) -> None:
        """
        Send text to the client.
        """
        if self.vt100_output is None:
            return
        formatted_text = to_formatted_text(formatted_text)
        print_formatted_text(
            self.vt100_output, formatted_text, self.style or DummyStyle()
        )

    def send_above_prompt(self, formatted_text: AnyFormattedText) -> None:
        """
        Send text to the client.
        This is asynchronous, returns a `Future`.
        """
        formatted_text = to_formatted_text(formatted_text)
        return self._run_in_terminal(lambda: self.send(formatted_text))

    def _run_in_terminal(self, func: Callable[[], None]) -> None:
        # Make sure that when an application was active for this connection,
        # that we print the text above the application.
        if self.context:
            self.context.run(run_in_terminal, func)  # type: ignore
        else:
            raise RuntimeError("Called _run_in_terminal outside `run_application`.")

    def erase_screen(self) -> None:
        """
        Erase the screen and move the cursor to the top.
        """
        if self.vt100_output is None:
            return
        self.vt100_output.erase_screen()
        self.vt100_output.cursor_goto(0, 0)
        self.vt100_output.flush()


async def _dummy_interact(connection: TelnetConnection) -> None:
    pass


class TelnetServer:
    """
    Telnet server implementation.

    Example::

        async def interact(connection):
            connection.send("Welcome")
            session = PromptSession()
            result = await session.prompt_async(message="Say something: ")
            connection.send(f"You said: {result}\n")

        async def main():
            server = TelnetServer(interact=interact, port=2323)
            await server.run()
    """

    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 23,
        interact: Callable[
            [TelnetConnection], Coroutine[Any, Any, None]
        ] = _dummy_interact,
        encoding: str = "utf-8",
        style: BaseStyle | None = None,
        enable_cpr: bool = True,
    ) -> None:
        self.host = host
        self.port = port
        self.interact = interact
        self.encoding = encoding
        self.style = style
        self.enable_cpr = enable_cpr

        self._run_task: asyncio.Task[None] | None = None
        self._application_tasks: list[asyncio.Task[None]] = []

        self.connections: set[TelnetConnection] = set()

    @classmethod
    def _create_socket(cls, host: str, port: int) -> socket.socket:
        # Create and bind socket
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind((host, port))

        s.listen(4)
        return s

    async def run(self, ready_cb: Callable[[], None] | None = None) -> None:
        """
        Run the telnet server, until this gets cancelled.

        :param ready_cb: Callback that will be called at the point that we're
            actually listening.
        """
        socket = self._create_socket(self.host, self.port)
        logger.info(
            "Listening for telnet connections on %s port %r", self.host, self.port
        )

        get_running_loop().add_reader(socket, lambda: self._accept(socket))

        if ready_cb:
            ready_cb()

        try:
            # Run forever, until cancelled.
            await asyncio.Future()
        finally:
            get_running_loop().remove_reader(socket)
            socket.close()

            # Wait for all applications to finish.
            for t in self._application_tasks:
                t.cancel()

            # (This is similar to
            # `Application.cancel_and_wait_for_background_tasks`. We wait for the
            # background tasks to complete, but don't propagate exceptions, because
            # we can't use `ExceptionGroup` yet.)
            if len(self._application_tasks) > 0:
                await asyncio.wait(
                    self._application_tasks,
                    timeout=None,
                    return_when=asyncio.ALL_COMPLETED,
                )

    def start(self) -> None:
        """
        Deprecated: Use `.run()` instead.

        Start the telnet server (stop by calling and awaiting `stop()`).
        """
        if self._run_task is not None:
            # Already running.
            return

        self._run_task = get_running_loop().create_task(self.run())

    async def stop(self) -> None:
        """
        Deprecated: Use `.run()` instead.

        Stop a telnet server that was started using `.start()` and wait for the
        cancellation to complete.
        """
        if self._run_task is not None:
            self._run_task.cancel()
            try:
                await self._run_task
            except asyncio.CancelledError:
                pass

    def _accept(self, listen_socket: socket.socket) -> None:
        """
        Accept new incoming connection.
        """
        conn, addr = listen_socket.accept()
        logger.info("New connection %r %r", *addr)

        # Run application for this connection.
        async def run() -> None:
            try:
                with create_pipe_input() as vt100_input:
                    connection = TelnetConnection(
                        conn,
                        addr,
                        self.interact,
                        self,
                        encoding=self.encoding,
                        style=self.style,
                        vt100_input=vt100_input,
                        enable_cpr=self.enable_cpr,
                    )
                    self.connections.add(connection)

                    logger.info("Starting interaction %r %r", *addr)
                    try:
                        await connection.run_application()
                    finally:
                        self.connections.remove(connection)
                        logger.info("Stopping interaction %r %r", *addr)
            except EOFError:
                # Happens either when the connection is closed by the client
                # (e.g., when the user types 'control-]', then 'quit' in the
                # telnet client) or when the user types control-d in a prompt
                # and this is not handled by the interact function.
                logger.info("Unhandled EOFError in telnet application.")
            except KeyboardInterrupt:
                # Unhandled control-c propagated by a prompt.
                logger.info("Unhandled KeyboardInterrupt in telnet application.")
            except BaseException as e:
                print(f"Got {type(e).__name__}", e)
                import traceback

                traceback.print_exc()
            finally:
                self._application_tasks.remove(task)

        task = get_running_loop().create_task(run())
        self._application_tasks.append(task)

# === NexusCore/openenv\Lib\site-packages\google\api_core\iam.py ===
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
"""Non-API-specific IAM policy definitions

For allowed roles / permissions, see:
https://cloud.google.com/iam/docs/understanding-roles

Example usage:

.. code-block:: python

   # ``get_iam_policy`` returns a :class:'~google.api_core.iam.Policy`.
   policy = resource.get_iam_policy(requested_policy_version=3)

   phred = "user:phred@example.com"
   admin_group = "group:admins@groups.example.com"
   account = "serviceAccount:account-1234@accounts.example.com"

   policy.version = 3
   policy.bindings = [
       {
           "role": "roles/owner",
           "members": {phred, admin_group, account}
       },
       {
           "role": "roles/editor",
           "members": {"allAuthenticatedUsers"}
       },
       {
           "role": "roles/viewer",
           "members": {"allUsers"}
           "condition": {
               "title": "request_time",
               "description": "Requests made before 2021-01-01T00:00:00Z",
               "expression": "request.time < timestamp(\"2021-01-01T00:00:00Z\")"
           }
       }
   ]

   resource.set_iam_policy(policy)
"""

import collections
import collections.abc
import operator
import warnings

# Generic IAM roles

OWNER_ROLE = "roles/owner"
"""Generic role implying all rights to an object."""

EDITOR_ROLE = "roles/editor"
"""Generic role implying rights to modify an object."""

VIEWER_ROLE = "roles/viewer"
"""Generic role implying rights to access an object."""

_ASSIGNMENT_DEPRECATED_MSG = """\
Assigning to '{}' is deprecated. Use the `policy.bindings` property to modify bindings instead."""

_DICT_ACCESS_MSG = """\
Dict access is not supported on policies with version > 1 or with conditional bindings."""


class InvalidOperationException(Exception):
    """Raised when trying to use Policy class as a dict."""

    pass


class Policy(collections.abc.MutableMapping):
    """IAM Policy

    Args:
        etag (Optional[str]): ETag used to identify a unique of the policy
        version (Optional[int]): The syntax schema version of the policy.

    Note:
        Using conditions in bindings requires the policy's version to be set
        to `3` or greater, depending on the versions that are currently supported.

        Accessing the policy using dict operations will raise InvalidOperationException
        when the policy's version is set to 3.

        Use the policy.bindings getter/setter to retrieve and modify the policy's bindings.

    See:
        IAM Policy https://cloud.google.com/iam/reference/rest/v1/Policy
        Policy versions https://cloud.google.com/iam/docs/policies#versions
        Conditions overview https://cloud.google.com/iam/docs/conditions-overview.
    """

    _OWNER_ROLES = (OWNER_ROLE,)
    """Roles mapped onto our ``owners`` attribute."""

    _EDITOR_ROLES = (EDITOR_ROLE,)
    """Roles mapped onto our ``editors`` attribute."""

    _VIEWER_ROLES = (VIEWER_ROLE,)
    """Roles mapped onto our ``viewers`` attribute."""

    def __init__(self, etag=None, version=None):
        self.etag = etag
        self.version = version
        self._bindings = []

    def __iter__(self):
        self.__check_version__()
        # Exclude bindings with no members
        return (binding["role"] for binding in self._bindings if binding["members"])

    def __len__(self):
        self.__check_version__()
        # Exclude bindings with no members
        return len(list(self.__iter__()))

    def __getitem__(self, key):
        self.__check_version__()
        for b in self._bindings:
            if b["role"] == key:
                return b["members"]
        # If the binding does not yet exist, create one
        # NOTE: This will create bindings with no members
        # which are ignored by __iter__ and __len__
        new_binding = {"role": key, "members": set()}
        self._bindings.append(new_binding)
        return new_binding["members"]

    def __setitem__(self, key, value):
        self.__check_version__()
        value = set(value)
        for binding in self._bindings:
            if binding["role"] == key:
                binding["members"] = value
                return
        self._bindings.append({"role": key, "members": value})

    def __delitem__(self, key):
        self.__check_version__()
        for b in self._bindings:
            if b["role"] == key:
                self._bindings.remove(b)
                return
        raise KeyError(key)

    def __check_version__(self):
        """Raise InvalidOperationException if version is greater than 1 or policy contains conditions."""
        raise_version = self.version is not None and self.version > 1

        if raise_version or self._contains_conditions():
            raise InvalidOperationException(_DICT_ACCESS_MSG)

    def _contains_conditions(self):
        for b in self._bindings:
            if b.get("condition") is not None:
                return True
        return False

    @property
    def bindings(self):
        """The policy's list of bindings.

        A binding is specified by a dictionary with keys:

        * role (str): Role that is assigned to `members`.

        * members (:obj:`set` of str): Specifies the identities associated to this binding.

        * condition (:obj:`dict` of str:str): Specifies a condition under which this binding will apply.

          * title (str): Title for the condition.

          * description (:obj:str, optional): Description of the condition.

          * expression: A CEL expression.

        Type:
           :obj:`list` of :obj:`dict`

        See:
           Policy versions https://cloud.google.com/iam/docs/policies#versions
           Conditions overview https://cloud.google.com/iam/docs/conditions-overview.

        Example:

        .. code-block:: python

           USER = "user:phred@example.com"
           ADMIN_GROUP = "group:admins@groups.example.com"
           SERVICE_ACCOUNT = "serviceAccount:account-1234@accounts.example.com"
           CONDITION = {
               "title": "request_time",
               "description": "Requests made before 2021-01-01T00:00:00Z", # Optional
               "expression": "request.time < timestamp(\"2021-01-01T00:00:00Z\")"
           }

           # Set policy's version to 3 before setting bindings containing conditions.
           policy.version = 3

           policy.bindings = [
               {
                   "role": "roles/viewer",
                   "members": {USER, ADMIN_GROUP, SERVICE_ACCOUNT},
                   "condition": CONDITION
               },
               ...
           ]
        """
        return self._bindings

    @bindings.setter
    def bindings(self, bindings):
        self._bindings = bindings

    @property
    def owners(self):
        """Legacy access to owner role.

        Raise InvalidOperationException if version is greater than 1 or policy contains conditions.

        DEPRECATED:  use `policy.bindings` to access bindings instead.
        """
        result = set()
        for role in self._OWNER_ROLES:
            for member in self.get(role, ()):
                result.add(member)
        return frozenset(result)

    @owners.setter
    def owners(self, value):
        """Update owners.

        Raise InvalidOperationException if version is greater than 1 or policy contains conditions.

        DEPRECATED:  use `policy.bindings` to access bindings instead.
        """
        warnings.warn(
            _ASSIGNMENT_DEPRECATED_MSG.format("owners", OWNER_ROLE), DeprecationWarning
        )
        self[OWNER_ROLE] = value

    @property
    def editors(self):
        """Legacy access to editor role.

        Raise InvalidOperationException if version is greater than 1 or policy contains conditions.

        DEPRECATED:  use `policy.bindings` to access bindings instead.
        """
        result = set()
        for role in self._EDITOR_ROLES:
            for member in self.get(role, ()):
                result.add(member)
        return frozenset(result)

    @editors.setter
    def editors(self, value):
        """Update editors.

        Raise InvalidOperationException if version is greater than 1 or policy contains conditions.

        DEPRECATED:  use `policy.bindings` to modify bindings instead.
        """
        warnings.warn(
            _ASSIGNMENT_DEPRECATED_MSG.format("editors", EDITOR_ROLE),
            DeprecationWarning,
        )
        self[EDITOR_ROLE] = value

    @property
    def viewers(self):
        """Legacy access to viewer role.

        Raise InvalidOperationException if version is greater than 1 or policy contains conditions.

        DEPRECATED:  use `policy.bindings` to modify bindings instead.
        """
        result = set()
        for role in self._VIEWER_ROLES:
            for member in self.get(role, ()):
                result.add(member)
        return frozenset(result)

    @viewers.setter
    def viewers(self, value):
        """Update viewers.

        Raise InvalidOperationException if version is greater than 1 or policy contains conditions.

        DEPRECATED:  use `policy.bindings` to modify bindings instead.
        """
        warnings.warn(
            _ASSIGNMENT_DEPRECATED_MSG.format("viewers", VIEWER_ROLE),
            DeprecationWarning,
        )
        self[VIEWER_ROLE] = value

    @staticmethod
    def user(email):
        """Factory method for a user member.

        Args:
            email (str): E-mail for this particular user.

        Returns:
            str: A member string corresponding to the given user.
        """
        return "user:%s" % (email,)

    @staticmethod
    def service_account(email):
        """Factory method for a service account member.

        Args:
            email (str): E-mail for this particular service account.

        Returns:
            str: A member string corresponding to the given service account.

        """
        return "serviceAccount:%s" % (email,)

    @staticmethod
    def group(email):
        """Factory method for a group member.

        Args:
            email (str): An id or e-mail for this particular group.

        Returns:
            str: A member string corresponding to the given group.
        """
        return "group:%s" % (email,)

    @staticmethod
    def domain(domain):
        """Factory method for a domain member.

        Args:
            domain (str): The domain for this member.

        Returns:
            str: A member string corresponding to the given domain.
        """
        return "domain:%s" % (domain,)

    @staticmethod
    def all_users():
        """Factory method for a member representing all users.

        Returns:
            str: A member string representing all users.
        """
        return "allUsers"

    @staticmethod
    def authenticated_users():
        """Factory method for a member representing all authenticated users.

        Returns:
            str: A member string representing all authenticated users.
        """
        return "allAuthenticatedUsers"

    @classmethod
    def from_api_repr(cls, resource):
        """Factory: create a policy from a JSON resource.

        Args:
            resource (dict): policy resource returned by ``getIamPolicy`` API.

        Returns:
            :class:`Policy`: the parsed policy
        """
        version = resource.get("version")
        etag = resource.get("etag")
        policy = cls(etag, version)
        policy.bindings = resource.get("bindings", [])

        for binding in policy.bindings:
            binding["members"] = set(binding.get("members", ()))

        return policy

    def to_api_repr(self):
        """Render a JSON policy resource.

        Returns:
            dict: a resource to be passed to the ``setIamPolicy`` API.
        """
        resource = {}

        if self.etag is not None:
            resource["etag"] = self.etag

        if self.version is not None:
            resource["version"] = self.version

        if self._bindings and len(self._bindings) > 0:
            bindings = []
            for binding in self._bindings:
                members = binding.get("members")
                if members:
                    new_binding = {"role": binding["role"], "members": sorted(members)}
                    condition = binding.get("condition")
                    if condition:
                        new_binding["condition"] = condition
                    bindings.append(new_binding)

            if bindings:
                # Sort bindings by role
                key = operator.itemgetter("role")
                resource["bindings"] = sorted(bindings, key=key)

        return resource

# === NexusCore/openenv\Lib\site-packages\google\ai\generativelanguage_v1beta\services\text_service\transports\grpc_asyncio.py ===
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
from typing import Awaitable, Callable, Dict, Optional, Sequence, Tuple, Union
import warnings

from google.api_core import exceptions as core_exceptions
from google.api_core import gapic_v1, grpc_helpers_async
from google.api_core import retry_async as retries
from google.auth import credentials as ga_credentials  # type: ignore
from google.auth.transport.grpc import SslCredentials  # type: ignore
from google.longrunning import operations_pb2  # type: ignore
import grpc  # type: ignore
from grpc.experimental import aio  # type: ignore

from google.ai.generativelanguage_v1beta.types import text_service

from .base import DEFAULT_CLIENT_INFO, TextServiceTransport
from .grpc import TextServiceGrpcTransport


class TextServiceGrpcAsyncIOTransport(TextServiceTransport):
    """gRPC AsyncIO backend transport for TextService.

    API for using Generative Language Models (GLMs) trained to
    generate text.
    Also known as Large Language Models (LLM)s, these generate text
    given an input prompt from the user.

    This class defines the same methods as the primary client, so the
    primary client can load the underlying transport implementation
    and call it.

    It sends protocol buffers over the wire using gRPC (which is built on
    top of HTTP/2); the ``grpcio`` package must be installed.
    """

    _grpc_channel: aio.Channel
    _stubs: Dict[str, Callable] = {}

    @classmethod
    def create_channel(
        cls,
        host: str = "generativelanguage.googleapis.com",
        credentials: Optional[ga_credentials.Credentials] = None,
        credentials_file: Optional[str] = None,
        scopes: Optional[Sequence[str]] = None,
        quota_project_id: Optional[str] = None,
        **kwargs,
    ) -> aio.Channel:
        """Create and return a gRPC AsyncIO channel object.
        Args:
            host (Optional[str]): The host for the channel to use.
            credentials (Optional[~.Credentials]): The
                authorization credentials to attach to requests. These
                credentials identify this application to the service. If
                none are specified, the client will attempt to ascertain
                the credentials from the environment.
            credentials_file (Optional[str]): A file with credentials that can
                be loaded with :func:`google.auth.load_credentials_from_file`.
            scopes (Optional[Sequence[str]]): A optional list of scopes needed for this
                service. These are only used when credentials are not specified and
                are passed to :func:`google.auth.default`.
            quota_project_id (Optional[str]): An optional project to use for billing
                and quota.
            kwargs (Optional[dict]): Keyword arguments, which are passed to the
                channel creation.
        Returns:
            aio.Channel: A gRPC AsyncIO channel object.
        """

        return grpc_helpers_async.create_channel(
            host,
            credentials=credentials,
            credentials_file=credentials_file,
            quota_project_id=quota_project_id,
            default_scopes=cls.AUTH_SCOPES,
            scopes=scopes,
            default_host=cls.DEFAULT_HOST,
            **kwargs,
        )

    def __init__(
        self,
        *,
        host: str = "generativelanguage.googleapis.com",
        credentials: Optional[ga_credentials.Credentials] = None,
        credentials_file: Optional[str] = None,
        scopes: Optional[Sequence[str]] = None,
        channel: Optional[Union[aio.Channel, Callable[..., aio.Channel]]] = None,
        api_mtls_endpoint: Optional[str] = None,
        client_cert_source: Optional[Callable[[], Tuple[bytes, bytes]]] = None,
        ssl_channel_credentials: Optional[grpc.ChannelCredentials] = None,
        client_cert_source_for_mtls: Optional[Callable[[], Tuple[bytes, bytes]]] = None,
        quota_project_id: Optional[str] = None,
        client_info: gapic_v1.client_info.ClientInfo = DEFAULT_CLIENT_INFO,
        always_use_jwt_access: Optional[bool] = False,
        api_audience: Optional[str] = None,
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
                This argument is ignored if a ``channel`` instance is provided.
            credentials_file (Optional[str]): A file with credentials that can
                be loaded with :func:`google.auth.load_credentials_from_file`.
                This argument is ignored if a ``channel`` instance is provided.
            scopes (Optional[Sequence[str]]): A optional list of scopes needed for this
                service. These are only used when credentials are not specified and
                are passed to :func:`google.auth.default`.
            channel (Optional[Union[aio.Channel, Callable[..., aio.Channel]]]):
                A ``Channel`` instance through which to make calls, or a Callable
                that constructs and returns one. If set to None, ``self.create_channel``
                is used to create the channel. If a Callable is given, it will be called
                with the same arguments as used in ``self.create_channel``.
            api_mtls_endpoint (Optional[str]): Deprecated. The mutual TLS endpoint.
                If provided, it overrides the ``host`` argument and tries to create
                a mutual TLS channel with client SSL credentials from
                ``client_cert_source`` or application default SSL credentials.
            client_cert_source (Optional[Callable[[], Tuple[bytes, bytes]]]):
                Deprecated. A callback to provide client SSL certificate bytes and
                private key bytes, both in PEM format. It is ignored if
                ``api_mtls_endpoint`` is None.
            ssl_channel_credentials (grpc.ChannelCredentials): SSL credentials
                for the grpc channel. It is ignored if a ``channel`` instance is provided.
            client_cert_source_for_mtls (Optional[Callable[[], Tuple[bytes, bytes]]]):
                A callback to provide client certificate bytes and private key bytes,
                both in PEM format. It is used to configure a mutual TLS channel. It is
                ignored if a ``channel`` instance or ``ssl_channel_credentials`` is provided.
            quota_project_id (Optional[str]): An optional project to use for billing
                and quota.
            client_info (google.api_core.gapic_v1.client_info.ClientInfo):
                The client info used to send a user-agent string along with
                API requests. If ``None``, then default info will be used.
                Generally, you only need to set this if you're developing
                your own client library.
            always_use_jwt_access (Optional[bool]): Whether self signed JWT should
                be used for service account credentials.

        Raises:
            google.auth.exceptions.MutualTlsChannelError: If mutual TLS transport
              creation failed for any reason.
          google.api_core.exceptions.DuplicateCredentialArgs: If both ``credentials``
              and ``credentials_file`` are passed.
        """
        self._grpc_channel = None
        self._ssl_channel_credentials = ssl_channel_credentials
        self._stubs: Dict[str, Callable] = {}

        if api_mtls_endpoint:
            warnings.warn("api_mtls_endpoint is deprecated", DeprecationWarning)
        if client_cert_source:
            warnings.warn("client_cert_source is deprecated", DeprecationWarning)

        if isinstance(channel, aio.Channel):
            # Ignore credentials if a channel was passed.
            credentials = False
            # If a channel was explicitly provided, set it.
            self._grpc_channel = channel
            self._ssl_channel_credentials = None
        else:
            if api_mtls_endpoint:
                host = api_mtls_endpoint

                # Create SSL credentials with client_cert_source or application
                # default SSL credentials.
                if client_cert_source:
                    cert, key = client_cert_source()
                    self._ssl_channel_credentials = grpc.ssl_channel_credentials(
                        certificate_chain=cert, private_key=key
                    )
                else:
                    self._ssl_channel_credentials = SslCredentials().ssl_credentials

            else:
                if client_cert_source_for_mtls and not ssl_channel_credentials:
                    cert, key = client_cert_source_for_mtls()
                    self._ssl_channel_credentials = grpc.ssl_channel_credentials(
                        certificate_chain=cert, private_key=key
                    )

        # The base transport sets the host, credentials and scopes
        super().__init__(
            host=host,
            credentials=credentials,
            credentials_file=credentials_file,
            scopes=scopes,
            quota_project_id=quota_project_id,
            client_info=client_info,
            always_use_jwt_access=always_use_jwt_access,
            api_audience=api_audience,
        )

        if not self._grpc_channel:
            # initialize with the provided callable or the default channel
            channel_init = channel or type(self).create_channel
            self._grpc_channel = channel_init(
                self._host,
                # use the credentials which are saved
                credentials=self._credentials,
                # Set ``credentials_file`` to ``None`` here as
                # the credentials that we saved earlier should be used.
                credentials_file=None,
                scopes=self._scopes,
                ssl_credentials=self._ssl_channel_credentials,
                quota_project_id=quota_project_id,
                options=[
                    ("grpc.max_send_message_length", -1),
                    ("grpc.max_receive_message_length", -1),
                ],
            )

        # Wrap messages. This must be done after self._grpc_channel exists
        self._prep_wrapped_messages(client_info)

    @property
    def grpc_channel(self) -> aio.Channel:
        """Create the channel designed to connect to this service.

        This property caches on the instance; repeated calls return
        the same channel.
        """
        # Return the channel from cache.
        return self._grpc_channel

    @property
    def generate_text(
        self,
    ) -> Callable[
        [text_service.GenerateTextRequest], Awaitable[text_service.GenerateTextResponse]
    ]:
        r"""Return a callable for the generate text method over gRPC.

        Generates a response from the model given an input
        message.

        Returns:
            Callable[[~.GenerateTextRequest],
                    Awaitable[~.GenerateTextResponse]]:
                A function that, when called, will call the underlying RPC
                on the server.
        """
        # Generate a "stub function" on-the-fly which will actually make
        # the request.
        # gRPC handles serialization and deserialization, so we just need
        # to pass in the functions for each.
        if "generate_text" not in self._stubs:
            self._stubs["generate_text"] = self.grpc_channel.unary_unary(
                "/google.ai.generativelanguage.v1beta.TextService/GenerateText",
                request_serializer=text_service.GenerateTextRequest.serialize,
                response_deserializer=text_service.GenerateTextResponse.deserialize,
            )
        return self._stubs["generate_text"]

    @property
    def embed_text(
        self,
    ) -> Callable[
        [text_service.EmbedTextRequest], Awaitable[text_service.EmbedTextResponse]
    ]:
        r"""Return a callable for the embed text method over gRPC.

        Generates an embedding from the model given an input
        message.

        Returns:
            Callable[[~.EmbedTextRequest],
                    Awaitable[~.EmbedTextResponse]]:
                A function that, when called, will call the underlying RPC
                on the server.
        """
        # Generate a "stub function" on-the-fly which will actually make
        # the request.
        # gRPC handles serialization and deserialization, so we just need
        # to pass in the functions for each.
        if "embed_text" not in self._stubs:
            self._stubs["embed_text"] = self.grpc_channel.unary_unary(
                "/google.ai.generativelanguage.v1beta.TextService/EmbedText",
                request_serializer=text_service.EmbedTextRequest.serialize,
                response_deserializer=text_service.EmbedTextResponse.deserialize,
            )
        return self._stubs["embed_text"]

    @property
    def batch_embed_text(
        self,
    ) -> Callable[
        [text_service.BatchEmbedTextRequest],
        Awaitable[text_service.BatchEmbedTextResponse],
    ]:
        r"""Return a callable for the batch embed text method over gRPC.

        Generates multiple embeddings from the model given
        input text in a synchronous call.

        Returns:
            Callable[[~.BatchEmbedTextRequest],
                    Awaitable[~.BatchEmbedTextResponse]]:
                A function that, when called, will call the underlying RPC
                on the server.
        """
        # Generate a "stub function" on-the-fly which will actually make
        # the request.
        # gRPC handles serialization and deserialization, so we just need
        # to pass in the functions for each.
        if "batch_embed_text" not in self._stubs:
            self._stubs["batch_embed_text"] = self.grpc_channel.unary_unary(
                "/google.ai.generativelanguage.v1beta.TextService/BatchEmbedText",
                request_serializer=text_service.BatchEmbedTextRequest.serialize,
                response_deserializer=text_service.BatchEmbedTextResponse.deserialize,
            )
        return self._stubs["batch_embed_text"]

    @property
    def count_text_tokens(
        self,
    ) -> Callable[
        [text_service.CountTextTokensRequest],
        Awaitable[text_service.CountTextTokensResponse],
    ]:
        r"""Return a callable for the count text tokens method over gRPC.

        Runs a model's tokenizer on a text and returns the
        token count.

        Returns:
            Callable[[~.CountTextTokensRequest],
                    Awaitable[~.CountTextTokensResponse]]:
                A function that, when called, will call the underlying RPC
                on the server.
        """
        # Generate a "stub function" on-the-fly which will actually make
        # the request.
        # gRPC handles serialization and deserialization, so we just need
        # to pass in the functions for each.
        if "count_text_tokens" not in self._stubs:
            self._stubs["count_text_tokens"] = self.grpc_channel.unary_unary(
                "/google.ai.generativelanguage.v1beta.TextService/CountTextTokens",
                request_serializer=text_service.CountTextTokensRequest.serialize,
                response_deserializer=text_service.CountTextTokensResponse.deserialize,
            )
        return self._stubs["count_text_tokens"]

    def _prep_wrapped_messages(self, client_info):
        """Precompute the wrapped methods, overriding the base class method to use async wrappers."""
        self._wrapped_methods = {
            self.generate_text: gapic_v1.method_async.wrap_method(
                self.generate_text,
                default_retry=retries.AsyncRetry(
                    initial=1.0,
                    maximum=10.0,
                    multiplier=1.3,
                    predicate=retries.if_exception_type(
                        core_exceptions.ServiceUnavailable,
                    ),
                    deadline=60.0,
                ),
                default_timeout=60.0,
                client_info=client_info,
            ),
            self.embed_text: gapic_v1.method_async.wrap_method(
                self.embed_text,
                default_retry=retries.AsyncRetry(
                    initial=1.0,
                    maximum=10.0,
                    multiplier=1.3,
                    predicate=retries.if_exception_type(
                        core_exceptions.ServiceUnavailable,
                    ),
                    deadline=60.0,
                ),
                default_timeout=60.0,
                client_info=client_info,
            ),
            self.batch_embed_text: gapic_v1.method_async.wrap_method(
                self.batch_embed_text,
                default_retry=retries.AsyncRetry(
                    initial=1.0,
                    maximum=10.0,
                    multiplier=1.3,
                    predicate=retries.if_exception_type(
                        core_exceptions.ServiceUnavailable,
                    ),
                    deadline=60.0,
                ),
                default_timeout=60.0,
                client_info=client_info,
            ),
            self.count_text_tokens: gapic_v1.method_async.wrap_method(
                self.count_text_tokens,
                default_retry=retries.AsyncRetry(
                    initial=1.0,
                    maximum=10.0,
                    multiplier=1.3,
                    predicate=retries.if_exception_type(
                        core_exceptions.ServiceUnavailable,
                    ),
                    deadline=60.0,
                ),
                default_timeout=60.0,
                client_info=client_info,
            ),
        }

    def close(self):
        return self.grpc_channel.close()


__all__ = ("TextServiceGrpcAsyncIOTransport",)

# === NexusCore/openenv\Lib\site-packages\pygments\lexers\foxpro.py ===
"""
    pygments.lexers.foxpro
    ~~~~~~~~~~~~~~~~~~~~~~

    Simple lexer for Microsoft Visual FoxPro source code.

    :copyright: Copyright 2006-2025 by the Pygments team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

import re

from pygments.lexer import RegexLexer
from pygments.token import Punctuation, Text, Comment, Operator, Keyword, \
    Name, String

__all__ = ['FoxProLexer']


class FoxProLexer(RegexLexer):
    """Lexer for Microsoft Visual FoxPro language.

    FoxPro syntax allows to shorten all keywords and function names
    to 4 characters.  Shortened forms are not recognized by this lexer.
    """

    name = 'FoxPro'
    aliases = ['foxpro', 'vfp', 'clipper', 'xbase']
    filenames = ['*.PRG', '*.prg']
    version_added = '1.6'
    mimetype = []
    url = 'https://learn.microsoft.com/en-us/previous-versions/visualstudio/foxpro'

    flags = re.IGNORECASE | re.MULTILINE

    tokens = {
        'root': [
            (r';\s*\n', Punctuation),  # consume newline
            (r'(^|\n)\s*', Text, 'newline'),

            # Square brackets may be used for array indices
            # and for string literal.  Look for arrays
            # before matching string literals.
            (r'(?<=\w)\[[0-9, ]+\]', Text),
            (r'\'[^\'\n]*\'|"[^"\n]*"|\[[^]*]\]', String),
            (r'(^\s*\*|&&|&amp;&amp;).*?\n', Comment.Single),

            (r'(ABS|ACLASS|ACOPY|ACOS|ADATABASES|ADBOBJECTS|ADDBS|'
             r'ADDPROPERTY|ADEL|ADIR|ADLLS|ADOCKSTATE|AELEMENT|AERROR|'
             r'AEVENTS|AFIELDS|AFONT|AGETCLASS|AGETFILEVERSION|AINS|'
             r'AINSTANCE|ALANGUAGE|ALEN|ALIAS|ALINES|ALLTRIM|'
             r'AMEMBERS|AMOUSEOBJ|ANETRESOURCES|APRINTERS|APROCINFO|'
             r'ASC|ASCAN|ASELOBJ|ASESSIONS|ASIN|ASORT|ASQLHANDLES|'
             r'ASTACKINFO|ASUBSCRIPT|AT|AT_C|ATAGINFO|ATAN|ATC|ATCC|'
             r'ATCLINE|ATLINE|ATN2|AUSED|AVCXCLASSES|BAR|BARCOUNT|'
             r'BARPROMPT|BETWEEN|BINDEVENT|BINTOC|BITAND|BITCLEAR|'
             r'BITLSHIFT|BITNOT|BITOR|BITRSHIFT|BITSET|BITTEST|BITXOR|'
             r'BOF|CANDIDATE|CAPSLOCK|CAST|CDOW|CDX|CEILING|CHR|CHRSAW|'
             r'CHRTRAN|CHRTRANC|CLEARRESULTSET|CMONTH|CNTBAR|CNTPAD|COL|'
             r'COM|Functions|COMARRAY|COMCLASSINFO|COMPOBJ|COMPROP|'
             r'COMRETURNERROR|COS|CPCONVERT|CPCURRENT|CPDBF|CREATEBINARY|'
             r'CREATEOBJECT|CREATEOBJECTEX|CREATEOFFLINE|CTOBIN|CTOD|'
             r'CTOT|CURDIR|CURSORGETPROP|CURSORSETPROP|CURSORTOXML|'
             r'CURVAL|DATE|DATETIME|DAY|DBC|DBF|DBGETPROP|DBSETPROP|'
             r'DBUSED|DDEAbortTrans|DDEAdvise|DDEEnabled|DDEExecute|'
             r'DDEInitiate|DDELastError|DDEPoke|DDERequest|DDESetOption|'
             r'DDESetService|DDESetTopic|DDETerminate|DEFAULTEXT|'
             r'DELETED|DESCENDING|DIFFERENCE|DIRECTORY|DISKSPACE|'
             r'DisplayPath|DMY|DODEFAULT|DOW|DRIVETYPE|DROPOFFLINE|'
             r'DTOC|DTOR|DTOS|DTOT|EDITSOURCE|EMPTY|EOF|ERROR|EVAL(UATE)?|'
             r'EVENTHANDLER|EVL|EXECSCRIPT|EXP|FCHSIZE|FCLOSE|FCOUNT|'
             r'FCREATE|FDATE|FEOF|FERROR|FFLUSH|FGETS|FIELD|FILE|'
             r'FILETOSTR|FILTER|FKLABEL|FKMAX|FLDLIST|FLOCK|FLOOR|'
             r'FONTMETRIC|FOPEN|FOR|FORCEEXT|FORCEPATH|FOUND|FPUTS|'
             r'FREAD|FSEEK|FSIZE|FTIME|FULLPATH|FV|FWRITE|'
             r'GETAUTOINCVALUE|GETBAR|GETCOLOR|GETCP|GETDIR|GETENV|'
             r'GETFILE|GETFLDSTATE|GETFONT|GETINTERFACE|'
             r'GETNEXTMODIFIED|GETOBJECT|GETPAD|GETPEM|GETPICT|'
             r'GETPRINTER|GETRESULTSET|GETWORDCOUNT|GETWORDNUM|'
             r'GETCURSORADAPTER|GOMONTH|HEADER|HOME|HOUR|ICASE|'
             r'IDXCOLLATE|IIF|IMESTATUS|INDBC|INDEXSEEK|INKEY|INLIST|'
             r'INPUTBOX|INSMODE|INT|ISALPHA|ISBLANK|ISCOLOR|ISDIGIT|'
             r'ISEXCLUSIVE|ISFLOCKED|ISLEADBYTE|ISLOWER|ISMEMOFETCHED|'
             r'ISMOUSE|ISNULL|ISPEN|ISREADONLY|ISRLOCKED|'
             r'ISTRANSACTABLE|ISUPPER|JUSTDRIVE|JUSTEXT|JUSTFNAME|'
             r'JUSTPATH|JUSTSTEM|KEY|KEYMATCH|LASTKEY|LEFT|LEFTC|LEN|'
             r'LENC|LIKE|LIKEC|LINENO|LOADPICTURE|LOCFILE|LOCK|LOG|'
             r'LOG10|LOOKUP|LOWER|LTRIM|LUPDATE|MAKETRANSACTABLE|MAX|'
             r'MCOL|MDOWN|MDX|MDY|MEMLINES|MEMORY|MENU|MESSAGE|'
             r'MESSAGEBOX|MIN|MINUTE|MLINE|MOD|MONTH|MRKBAR|MRKPAD|'
             r'MROW|MTON|MWINDOW|NDX|NEWOBJECT|NORMALIZE|NTOM|NUMLOCK|'
             r'NVL|OBJNUM|OBJTOCLIENT|OBJVAR|OCCURS|OEMTOANSI|OLDVAL|'
             r'ON|ORDER|OS|PAD|PADL|PARAMETERS|PAYMENT|PCOL|PCOUNT|'
             r'PEMSTATUS|PI|POPUP|PRIMARY|PRINTSTATUS|PRMBAR|PRMPAD|'
             r'PROGRAM|PROMPT|PROPER|PROW|PRTINFO|PUTFILE|PV|QUARTER|'
             r'RAISEEVENT|RAND|RAT|RATC|RATLINE|RDLEVEL|READKEY|RECCOUNT|'
             r'RECNO|RECSIZE|REFRESH|RELATION|REPLICATE|REQUERY|RGB|'
             r'RGBSCHEME|RIGHT|RIGHTC|RLOCK|ROUND|ROW|RTOD|RTRIM|'
             r'SAVEPICTURE|SCHEME|SCOLS|SEC|SECONDS|SEEK|SELECT|SET|'
             r'SETFLDSTATE|SETRESULTSET|SIGN|SIN|SKPBAR|SKPPAD|SOUNDEX|'
             r'SPACE|SQLCANCEL|SQLCOLUMNS|SQLCOMMIT|SQLCONNECT|'
             r'SQLDISCONNECT|SQLEXEC|SQLGETPROP|SQLIDLEDISCONNECT|'
             r'SQLMORERESULTS|SQLPREPARE|SQLROLLBACK|SQLSETPROP|'
             r'SQLSTRINGCONNECT|SQLTABLES|SQRT|SROWS|STR|STRCONV|'
             r'STREXTRACT|STRTOFILE|STRTRAN|STUFF|STUFFC|SUBSTR|'
             r'SUBSTRC|SYS|SYSMETRIC|TABLEREVERT|TABLEUPDATE|TAG|'
             r'TAGCOUNT|TAGNO|TAN|TARGET|TEXTMERGE|TIME|TRANSFORM|'
             r'TRIM|TTOC|TTOD|TXNLEVEL|TXTWIDTH|TYPE|UNBINDEVENTS|'
             r'UNIQUE|UPDATED|UPPER|USED|VAL|VARREAD|VARTYPE|VERSION|'
             r'WBORDER|WCHILD|WCOLS|WDOCKABLE|WEEK|WEXIST|WFONT|WLAST|'
             r'WLCOL|WLROW|WMAXIMUM|WMINIMUM|WONTOP|WOUTPUT|WPARENT|'
             r'WREAD|WROWS|WTITLE|WVISIBLE|XMLTOCURSOR|XMLUPDATEGRAM|'
             r'YEAR)(?=\s*\()', Name.Function),

            (r'_ALIGNMENT|_ASCIICOLS|_ASCIIROWS|_ASSIST|_BEAUTIFY|_BOX|'
             r'_BROWSER|_BUILDER|_CALCMEM|_CALCVALUE|_CLIPTEXT|_CONVERTER|'
             r'_COVERAGE|_CUROBJ|_DBLCLICK|_DIARYDATE|_DOS|_FOXDOC|_FOXREF|'
             r'_GALLERY|_GENGRAPH|_GENHTML|_GENMENU|_GENPD|_GENSCRN|'
             r'_GENXTAB|_GETEXPR|_INCLUDE|_INCSEEK|_INDENT|_LMARGIN|_MAC|'
             r'_MENUDESIGNER|_MLINE|_PADVANCE|_PAGENO|_PAGETOTAL|_PBPAGE|'
             r'_PCOLNO|_PCOPIES|_PDRIVER|_PDSETUP|_PECODE|_PEJECT|_PEPAGE|'
             r'_PLENGTH|_PLINENO|_PLOFFSET|_PPITCH|_PQUALITY|_PRETEXT|'
             r'_PSCODE|_PSPACING|_PWAIT|_RMARGIN|_REPORTBUILDER|'
             r'_REPORTOUTPUT|_REPORTPREVIEW|_SAMPLES|_SCCTEXT|_SCREEN|'
             r'_SHELL|_SPELLCHK|_STARTUP|_TABS|_TALLY|_TASKPANE|_TEXT|'
             r'_THROTTLE|_TOOLBOX|_TOOLTIPTIMEOUT|_TRANSPORT|_TRIGGERLEVEL|'
             r'_UNIX|_VFP|_WINDOWS|_WIZARD|_WRAP', Keyword.Pseudo),

            (r'THISFORMSET|THISFORM|THIS', Name.Builtin),

            (r'Application|CheckBox|Collection|Column|ComboBox|'
             r'CommandButton|CommandGroup|Container|Control|CursorAdapter|'
             r'Cursor|Custom|DataEnvironment|DataObject|EditBox|'
             r'Empty|Exception|Fields|Files|File|FormSet|Form|FoxCode|'
             r'Grid|Header|Hyperlink|Image|Label|Line|ListBox|Objects|'
             r'OptionButton|OptionGroup|PageFrame|Page|ProjectHook|Projects|'
             r'Project|Relation|ReportListener|Separator|Servers|Server|'
             r'Session|Shape|Spinner|Tables|TextBox|Timer|ToolBar|'
             r'XMLAdapter|XMLField|XMLTable', Name.Class),

            (r'm\.[a-z_]\w*', Name.Variable),
            (r'\.(F|T|AND|OR|NOT|NULL)\.|\b(AND|OR|NOT|NULL)\b', Operator.Word),

            (r'\.(ActiveColumn|ActiveControl|ActiveForm|ActivePage|'
             r'ActiveProject|ActiveRow|AddLineFeeds|ADOCodePage|Alias|'
             r'Alignment|Align|AllowAddNew|AllowAutoColumnFit|'
             r'AllowCellSelection|AllowDelete|AllowHeaderSizing|'
             r'AllowInsert|AllowModalMessages|AllowOutput|AllowRowSizing|'
             r'AllowSimultaneousFetch|AllowTabs|AllowUpdate|'
             r'AlwaysOnBottom|AlwaysOnTop|Anchor|Application|'
             r'AutoActivate|AutoCenter|AutoCloseTables|AutoComplete|'
             r'AutoCompSource|AutoCompTable|AutoHideScrollBar|'
             r'AutoIncrement|AutoOpenTables|AutoRelease|AutoSize|'
             r'AutoVerbMenu|AutoYield|BackColor|ForeColor|BackStyle|'
             r'BaseClass|BatchUpdateCount|BindControls|BorderColor|'
             r'BorderStyle|BorderWidth|BoundColumn|BoundTo|Bound|'
             r'BreakOnError|BufferModeOverride|BufferMode|'
             r'BuildDateTime|ButtonCount|Buttons|Cancel|Caption|'
             r'Centered|Century|ChildAlias|ChildOrder|ChildTable|'
             r'ClassLibrary|Class|ClipControls|Closable|CLSID|CodePage|'
             r'ColorScheme|ColorSource|ColumnCount|ColumnLines|'
             r'ColumnOrder|Columns|ColumnWidths|CommandClauses|'
             r'Comment|CompareMemo|ConflictCheckCmd|ConflictCheckType|'
             r'ContinuousScroll|ControlBox|ControlCount|Controls|'
             r'ControlSource|ConversionFunc|Count|CurrentControl|'
             r'CurrentDataSession|CurrentPass|CurrentX|CurrentY|'
             r'CursorSchema|CursorSource|CursorStatus|Curvature|'
             r'Database|DataSessionID|DataSession|DataSourceType|'
             r'DataSource|DataType|DateFormat|DateMark|Debug|'
             r'DeclareXMLPrefix|DEClassLibrary|DEClass|DefaultFilePath|'
             r'Default|DefOLELCID|DeleteCmdDataSourceType|DeleteCmdDataSource|'
             r'DeleteCmd|DeleteMark|Description|Desktop|'
             r'Details|DisabledBackColor|DisabledForeColor|'
             r'DisabledItemBackColor|DisabledItemForeColor|'
             r'DisabledPicture|DisableEncode|DisplayCount|'
             r'DisplayValue|Dockable|Docked|DockPosition|'
             r'DocumentFile|DownPicture|DragIcon|DragMode|DrawMode|'
             r'DrawStyle|DrawWidth|DynamicAlignment|DynamicBackColor|'
             r'DynamicForeColor|DynamicCurrentControl|DynamicFontBold|'
             r'DynamicFontItalic|DynamicFontStrikethru|'
             r'DynamicFontUnderline|DynamicFontName|DynamicFontOutline|'
             r'DynamicFontShadow|DynamicFontSize|DynamicInputMask|'
             r'DynamicLineHeight|EditorOptions|Enabled|'
             r'EnableHyperlinks|Encrypted|ErrorNo|Exclude|Exclusive|'
             r'FetchAsNeeded|FetchMemoCmdList|FetchMemoDataSourceType|'
             r'FetchMemoDataSource|FetchMemo|FetchSize|'
             r'FileClassLibrary|FileClass|FillColor|FillStyle|Filter|'
             r'FirstElement|FirstNestedTable|Flags|FontBold|FontItalic|'
             r'FontStrikethru|FontUnderline|FontCharSet|FontCondense|'
             r'FontExtend|FontName|FontOutline|FontShadow|FontSize|'
             r'ForceCloseTag|Format|FormCount|FormattedOutput|Forms|'
             r'FractionDigits|FRXDataSession|FullName|GDIPlusGraphics|'
             r'GridLineColor|GridLines|GridLineWidth|HalfHeightCaption|'
             r'HeaderClassLibrary|HeaderClass|HeaderHeight|Height|'
             r'HelpContextID|HideSelection|HighlightBackColor|'
             r'HighlightForeColor|HighlightStyle|HighlightRowLineWidth|'
             r'HighlightRow|Highlight|HomeDir|Hours|HostName|'
             r'HScrollSmallChange|hWnd|Icon|IncrementalSearch|Increment|'
             r'InitialSelectedAlias|InputMask|InsertCmdDataSourceType|'
             r'InsertCmdDataSource|InsertCmdRefreshCmd|'
             r'InsertCmdRefreshFieldList|InsertCmdRefreshKeyFieldList|'
             r'InsertCmd|Instancing|IntegralHeight|'
             r'Interval|IMEMode|IsAttribute|IsBase64|IsBinary|IsNull|'
             r'IsDiffGram|IsLoaded|ItemBackColor,|ItemData|ItemIDData|'
             r'ItemTips|IXMLDOMElement|KeyboardHighValue|KeyboardLowValue|'
             r'Keyfield|KeyFieldList|KeyPreview|KeySort|LanguageOptions|'
             r'LeftColumn|Left|LineContents|LineNo|LineSlant|LinkMaster|'
             r'ListCount|ListenerType|ListIndex|ListItemID|ListItem|'
             r'List|LockColumnsLeft|LockColumns|LockScreen|MacDesktop|'
             r'MainFile|MapN19_4ToCurrency|MapBinary|MapVarchar|Margin|'
             r'MaxButton|MaxHeight|MaxLeft|MaxLength|MaxRecords|MaxTop|'
             r'MaxWidth|MDIForm|MemberClassLibrary|MemberClass|'
             r'MemoWindow|Message|MinButton|MinHeight|MinWidth|'
             r'MouseIcon|MousePointer|Movable|MoverBars|MultiSelect|'
             r'Name|NestedInto|NewIndex|NewItemID|NextSiblingTable|'
             r'NoCpTrans|NoDataOnLoad|NoData|NullDisplay|'
             r'NumberOfElements|Object|OLEClass|OLEDragMode|'
             r'OLEDragPicture|OLEDropEffects|OLEDropHasData|'
             r'OLEDropMode|OLEDropTextInsertion|OLELCID|'
             r'OLERequestPendingTimeout|OLEServerBusyRaiseError|'
             r'OLEServerBusyTimeout|OLETypeAllowed|OneToMany|'
             r'OpenViews|OpenWindow|Optimize|OrderDirection|Order|'
             r'OutputPageCount|OutputType|PageCount|PageHeight|'
             r'PageNo|PageOrder|Pages|PageTotal|PageWidth|'
             r'PanelLink|Panel|ParentAlias|ParentClass|ParentTable|'
             r'Parent|Partition|PasswordChar|PictureMargin|'
             r'PicturePosition|PictureSpacing|PictureSelectionDisplay|'
             r'PictureVal|Picture|Prepared|'
             r'PolyPoints|PreserveWhiteSpace|PreviewContainer|'
             r'PrintJobName|Procedure|PROCESSID|ProgID|ProjectHookClass|'
             r'ProjectHookLibrary|ProjectHook|QuietMode|'
             r'ReadCycle|ReadLock|ReadMouse|ReadObject|ReadOnly|'
             r'ReadSave|ReadTimeout|RecordMark|RecordSourceType|'
             r'RecordSource|RefreshAlias|'
             r'RefreshCmdDataSourceType|RefreshCmdDataSource|RefreshCmd|'
             r'RefreshIgnoreFieldList|RefreshTimeStamp|RelationalExpr|'
             r'RelativeColumn|RelativeRow|ReleaseType|Resizable|'
             r'RespectCursorCP|RespectNesting|RightToLeft|RotateFlip|'
             r'Rotation|RowColChange|RowHeight|RowSourceType|'
             r'RowSource|ScaleMode|SCCProvider|SCCStatus|ScrollBars|'
             r'Seconds|SelectCmd|SelectedID|'
             r'SelectedItemBackColor|SelectedItemForeColor|Selected|'
             r'SelectionNamespaces|SelectOnEntry|SelLength|SelStart|'
             r'SelText|SendGDIPlusImage|SendUpdates|ServerClassLibrary|'
             r'ServerClass|ServerHelpFile|ServerName|'
             r'ServerProject|ShowTips|ShowInTaskbar|ShowWindow|'
             r'Sizable|SizeBox|SOM|Sorted|Sparse|SpecialEffect|'
             r'SpinnerHighValue|SpinnerLowValue|SplitBar|StackLevel|'
             r'StartMode|StatusBarText|StatusBar|Stretch|StrictDateEntry|'
             r'Style|TabIndex|Tables|TabOrientation|Tabs|TabStop|'
             r'TabStretch|TabStyle|Tag|TerminateRead|Text|Themes|'
             r'ThreadID|TimestampFieldList|TitleBar|ToolTipText|'
             r'TopIndex|TopItemID|Top|TwoPassProcess|TypeLibCLSID|'
             r'TypeLibDesc|TypeLibName|Type|Unicode|UpdatableFieldList|'
             r'UpdateCmdDataSourceType|UpdateCmdDataSource|'
             r'UpdateCmdRefreshCmd|UpdateCmdRefreshFieldList|'
             r'UpdateCmdRefreshKeyFieldList|UpdateCmd|'
             r'UpdateGramSchemaLocation|UpdateGram|UpdateNameList|UpdateType|'
             r'UseCodePage|UseCursorSchema|UseDeDataSource|UseMemoSize|'
             r'UserValue|UseTransactions|UTF8Encoded|Value|VersionComments|'
             r'VersionCompany|VersionCopyright|VersionDescription|'
             r'VersionNumber|VersionProduct|VersionTrademarks|Version|'
             r'VFPXMLProgID|ViewPortHeight|ViewPortLeft|'
             r'ViewPortTop|ViewPortWidth|VScrollSmallChange|View|Visible|'
             r'VisualEffect|WhatsThisButton|WhatsThisHelpID|WhatsThisHelp|'
             r'WhereType|Width|WindowList|WindowState|WindowType|WordWrap|'
             r'WrapCharInCDATA|WrapInCDATA|WrapMemoInCDATA|XMLAdapter|'
             r'XMLConstraints|XMLNameIsXPath|XMLNamespace|XMLName|'
             r'XMLPrefix|XMLSchemaLocation|XMLTable|XMLType|'
             r'XSDfractionDigits|XSDmaxLength|XSDtotalDigits|'
             r'XSDtype|ZoomBox)', Name.Attribute),

            (r'\.(ActivateCell|AddColumn|AddItem|AddListItem|AddObject|'
             r'AddProperty|AddTableSchema|AddToSCC|Add|'
             r'ApplyDiffgram|Attach|AutoFit|AutoOpen|Box|Build|'
             r'CancelReport|ChangesToCursor|CheckIn|CheckOut|Circle|'
             r'CleanUp|ClearData|ClearStatus|Clear|CloneObject|CloseTables|'
             r'Close|Cls|CursorAttach|CursorDetach|CursorFill|'
             r'CursorRefresh|DataToClip|DelayedMemoFetch|DeleteColumn|'
             r'Dock|DoMessage|DoScroll|DoStatus|DoVerb|Drag|Draw|Eval|'
             r'GetData|GetDockState|GetFormat|GetKey|GetLatestVersion|'
             r'GetPageHeight|GetPageWidth|Help|Hide|IncludePageInOutput|'
             r'IndexToItemID|ItemIDToIndex|Item|LoadXML|Line|Modify|'
             r'MoveItem|Move|Nest|OLEDrag|OnPreviewClose|OutputPage|'
             r'Point|Print|PSet|Quit|ReadExpression|ReadMethod|'
             r'RecordRefresh|Refresh|ReleaseXML|Release|RemoveFromSCC|'
             r'RemoveItem|RemoveListItem|RemoveObject|Remove|'
             r'Render|Requery|RequestData|ResetToDefault|Reset|Run|'
             r'SaveAsClass|SaveAs|SetAll|SetData|SetFocus|SetFormat|'
             r'SetMain|SetVar|SetViewPort|ShowWhatsThis|Show|'
             r'SupportsListenerType|TextHeight|TextWidth|ToCursor|'
             r'ToXML|UndoCheckOut|Unnest|UpdateStatus|WhatsThisMode|'
             r'WriteExpression|WriteMethod|ZOrder)', Name.Function),

            (r'\.(Activate|AdjustObjectSize|AfterBand|AfterBuild|'
             r'AfterCloseTables|AfterCursorAttach|AfterCursorClose|'
             r'AfterCursorDetach|AfterCursorFill|AfterCursorRefresh|'
             r'AfterCursorUpdate|AfterDelete|AfterInsert|'
             r'AfterRecordRefresh|AfterUpdate|AfterDock|AfterReport|'
             r'AfterRowColChange|BeforeBand|BeforeCursorAttach|'
             r'BeforeCursorClose|BeforeCursorDetach|BeforeCursorFill|'
             r'BeforeCursorRefresh|BeforeCursorUpdate|BeforeDelete|'
             r'BeforeInsert|BeforeDock|BeforeOpenTables|'
             r'BeforeRecordRefresh|BeforeReport|BeforeRowColChange|'
             r'BeforeUpdate|Click|dbc_Activate|dbc_AfterAddTable|'
             r'dbc_AfterAppendProc|dbc_AfterCloseTable|dbc_AfterCopyProc|'
             r'dbc_AfterCreateConnection|dbc_AfterCreateOffline|'
             r'dbc_AfterCreateTable|dbc_AfterCreateView|dbc_AfterDBGetProp|'
             r'dbc_AfterDBSetProp|dbc_AfterDeleteConnection|'
             r'dbc_AfterDropOffline|dbc_AfterDropTable|'
             r'dbc_AfterModifyConnection|dbc_AfterModifyProc|'
             r'dbc_AfterModifyTable|dbc_AfterModifyView|dbc_AfterOpenTable|'
             r'dbc_AfterRemoveTable|dbc_AfterRenameConnection|'
             r'dbc_AfterRenameTable|dbc_AfterRenameView|'
             r'dbc_AfterValidateData|dbc_BeforeAddTable|'
             r'dbc_BeforeAppendProc|dbc_BeforeCloseTable|'
             r'dbc_BeforeCopyProc|dbc_BeforeCreateConnection|'
             r'dbc_BeforeCreateOffline|dbc_BeforeCreateTable|'
             r'dbc_BeforeCreateView|dbc_BeforeDBGetProp|'
             r'dbc_BeforeDBSetProp|dbc_BeforeDeleteConnection|'
             r'dbc_BeforeDropOffline|dbc_BeforeDropTable|'
             r'dbc_BeforeModifyConnection|dbc_BeforeModifyProc|'
             r'dbc_BeforeModifyTable|dbc_BeforeModifyView|'
             r'dbc_BeforeOpenTable|dbc_BeforeRemoveTable|'
             r'dbc_BeforeRenameConnection|dbc_BeforeRenameTable|'
             r'dbc_BeforeRenameView|dbc_BeforeValidateData|'
             r'dbc_CloseData|dbc_Deactivate|dbc_ModifyData|dbc_OpenData|'
             r'dbc_PackData|DblClick|Deactivate|Deleted|Destroy|DoCmd|'
             r'DownClick|DragDrop|DragOver|DropDown|ErrorMessage|Error|'
             r'EvaluateContents|GotFocus|Init|InteractiveChange|KeyPress|'
             r'LoadReport|Load|LostFocus|Message|MiddleClick|MouseDown|'
             r'MouseEnter|MouseLeave|MouseMove|MouseUp|MouseWheel|Moved|'
             r'OLECompleteDrag|OLEDragOver|OLEGiveFeedback|OLESetData|'
             r'OLEStartDrag|OnMoveItem|Paint|ProgrammaticChange|'
             r'QueryAddFile|QueryModifyFile|QueryNewFile|QueryRemoveFile|'
             r'QueryRunFile|QueryUnload|RangeHigh|RangeLow|ReadActivate|'
             r'ReadDeactivate|ReadShow|ReadValid|ReadWhen|Resize|'
             r'RightClick|SCCInit|SCCDestroy|Scrolled|Timer|UIEnable|'
             r'UnDock|UnloadReport|Unload|UpClick|Valid|When)', Name.Function),

            (r'\s+', Text),
            # everything else is not colored
            (r'.', Text),
        ],
        'newline': [
            (r'\*.*?$', Comment.Single, '#pop'),
            (r'(ACCEPT|ACTIVATE\s*MENU|ACTIVATE\s*POPUP|ACTIVATE\s*SCREEN|'
             r'ACTIVATE\s*WINDOW|APPEND|APPEND\s*FROM|APPEND\s*FROM\s*ARRAY|'
             r'APPEND\s*GENERAL|APPEND\s*MEMO|ASSIST|AVERAGE|BLANK|BROWSE|'
             r'BUILD\s*APP|BUILD\s*EXE|BUILD\s*PROJECT|CALCULATE|CALL|'
             r'CANCEL|CHANGE|CLEAR|CLOSE|CLOSE\s*MEMO|COMPILE|CONTINUE|'
             r'COPY\s*FILE|COPY\s*INDEXES|COPY\s*MEMO|COPY\s*STRUCTURE|'
             r'COPY\s*STRUCTURE\s*EXTENDED|COPY\s*TAG|COPY\s*TO|'
             r'COPY\s*TO\s*ARRAY|COUNT|CREATE|CREATE\s*COLOR\s*SET|'
             r'CREATE\s*CURSOR|CREATE\s*FROM|CREATE\s*LABEL|CREATE\s*MENU|'
             r'CREATE\s*PROJECT|CREATE\s*QUERY|CREATE\s*REPORT|'
             r'CREATE\s*SCREEN|CREATE\s*TABLE|CREATE\s*VIEW|DDE|'
             r'DEACTIVATE\s*MENU|DEACTIVATE\s*POPUP|DEACTIVATE\s*WINDOW|'
             r'DECLARE|DEFINE\s*BAR|DEFINE\s*BOX|DEFINE\s*MENU|'
             r'DEFINE\s*PAD|DEFINE\s*POPUP|DEFINE\s*WINDOW|DELETE|'
             r'DELETE\s*FILE|DELETE\s*TAG|DIMENSION|DIRECTORY|DISPLAY|'
             r'DISPLAY\s*FILES|DISPLAY\s*MEMORY|DISPLAY\s*STATUS|'
             r'DISPLAY\s*STRUCTURE|DO|EDIT|EJECT|EJECT\s*PAGE|ERASE|'
             r'EXIT|EXPORT|EXTERNAL|FILER|FIND|FLUSH|FUNCTION|GATHER|'
             r'GETEXPR|GO|GOTO|HELP|HIDE\s*MENU|HIDE\s*POPUP|'
             r'HIDE\s*WINDOW|IMPORT|INDEX|INPUT|INSERT|JOIN|KEYBOARD|'
             r'LABEL|LIST|LOAD|LOCATE|LOOP|MENU|MENU\s*TO|MODIFY\s*COMMAND|'
             r'MODIFY\s*FILE|MODIFY\s*GENERAL|MODIFY\s*LABEL|MODIFY\s*MEMO|'
             r'MODIFY\s*MENU|MODIFY\s*PROJECT|MODIFY\s*QUERY|'
             r'MODIFY\s*REPORT|MODIFY\s*SCREEN|MODIFY\s*STRUCTURE|'
             r'MODIFY\s*WINDOW|MOVE\s*POPUP|MOVE\s*WINDOW|NOTE|'
             r'ON\s*APLABOUT|ON\s*BAR|ON\s*ERROR|ON\s*ESCAPE|'
             r'ON\s*EXIT\s*BAR|ON\s*EXIT\s*MENU|ON\s*EXIT\s*PAD|'
             r'ON\s*EXIT\s*POPUP|ON\s*KEY|ON\s*KEY\s*=|ON\s*KEY\s*LABEL|'
             r'ON\s*MACHELP|ON\s*PAD|ON\s*PAGE|ON\s*READERROR|'
             r'ON\s*SELECTION\s*BAR|ON\s*SELECTION\s*MENU|'
             r'ON\s*SELECTION\s*PAD|ON\s*SELECTION\s*POPUP|ON\s*SHUTDOWN|'
             r'PACK|PARAMETERS|PLAY\s*MACRO|POP\s*KEY|POP\s*MENU|'
             r'POP\s*POPUP|PRIVATE|PROCEDURE|PUBLIC|PUSH\s*KEY|'
             r'PUSH\s*MENU|PUSH\s*POPUP|QUIT|READ|READ\s*MENU|RECALL|'
             r'REINDEX|RELEASE|RELEASE\s*MODULE|RENAME|REPLACE|'
             r'REPLACE\s*FROM\s*ARRAY|REPORT|RESTORE\s*FROM|'
             r'RESTORE\s*MACROS|RESTORE\s*SCREEN|RESTORE\s*WINDOW|'
             r'RESUME|RETRY|RETURN|RUN|RUN\s*\/N"|RUNSCRIPT|'
             r'SAVE\s*MACROS|SAVE\s*SCREEN|SAVE\s*TO|SAVE\s*WINDOWS|'
             r'SCATTER|SCROLL|SEEK|SELECT|SET|SET\s*ALTERNATE|'
             r'SET\s*ANSI|SET\s*APLABOUT|SET\s*AUTOSAVE|SET\s*BELL|'
             r'SET\s*BLINK|SET\s*BLOCKSIZE|SET\s*BORDER|SET\s*BRSTATUS|'
             r'SET\s*CARRY|SET\s*CENTURY|SET\s*CLEAR|SET\s*CLOCK|'
             r'SET\s*COLLATE|SET\s*COLOR\s*OF|SET\s*COLOR\s*OF\s*SCHEME|'
             r'SET\s*COLOR\s*SET|SET\s*COLOR\s*TO|SET\s*COMPATIBLE|'
             r'SET\s*CONFIRM|SET\s*CONSOLE|SET\s*CURRENCY|SET\s*CURSOR|'
             r'SET\s*DATE|SET\s*DEBUG|SET\s*DECIMALS|SET\s*DEFAULT|'
             r'SET\s*DELETED|SET\s*DELIMITERS|SET\s*DEVELOPMENT|'
             r'SET\s*DEVICE|SET\s*DISPLAY|SET\s*DOHISTORY|SET\s*ECHO|'
             r'SET\s*ESCAPE|SET\s*EXACT|SET\s*EXCLUSIVE|SET\s*FIELDS|'
             r'SET\s*FILTER|SET\s*FIXED|SET\s*FORMAT|SET\s*FULLPATH|'
             r'SET\s*FUNCTION|SET\s*HEADINGS|SET\s*HELP|SET\s*HELPFILTER|'
             r'SET\s*HOURS|SET\s*INDEX|SET\s*INTENSITY|SET\s*KEY|'
             r'SET\s*KEYCOMP|SET\s*LIBRARY|SET\s*LOCK|SET\s*LOGERRORS|'
             r'SET\s*MACDESKTOP|SET\s*MACHELP|SET\s*MACKEY|SET\s*MARGIN|'
             r'SET\s*MARK\s*OF|SET\s*MARK\s*TO|SET\s*MEMOWIDTH|'
             r'SET\s*MESSAGE|SET\s*MOUSE|SET\s*MULTILOCKS|SET\s*NEAR|'
             r'SET\s*NOCPTRANS|SET\s*NOTIFY|SET\s*ODOMETER|SET\s*OPTIMIZE|'
             r'SET\s*ORDER|SET\s*PALETTE|SET\s*PATH|SET\s*PDSETUP|'
             r'SET\s*POINT|SET\s*PRINTER|SET\s*PROCEDURE|SET\s*READBORDER|'
             r'SET\s*REFRESH|SET\s*RELATION|SET\s*RELATION\s*OFF|'
             r'SET\s*REPROCESS|SET\s*RESOURCE|SET\s*SAFETY|SET\s*SCOREBOARD|'
             r'SET\s*SEPARATOR|SET\s*SHADOWS|SET\s*SKIP|SET\s*SKIP\s*OF|'
             r'SET\s*SPACE|SET\s*STATUS|SET\s*STATUS\s*BAR|SET\s*STEP|'
             r'SET\s*STICKY|SET\s*SYSMENU|SET\s*TALK|SET\s*TEXTMERGE|'
             r'SET\s*TEXTMERGE\s*DELIMITERS|SET\s*TOPIC|SET\s*TRBETWEEN|'
             r'SET\s*TYPEAHEAD|SET\s*UDFPARMS|SET\s*UNIQUE|SET\s*VIEW|'
             r'SET\s*VOLUME|SET\s*WINDOW\s*OF\s*MEMO|SET\s*XCMDFILE|'
             r'SHOW\s*GET|SHOW\s*GETS|SHOW\s*MENU|SHOW\s*OBJECT|'
             r'SHOW\s*POPUP|SHOW\s*WINDOW|SIZE\s*POPUP|SKIP|SORT|'
             r'STORE|SUM|SUSPEND|TOTAL|TYPE|UNLOCK|UPDATE|USE|WAIT|'
             r'ZAP|ZOOM\s*WINDOW|DO\s*CASE|CASE|OTHERWISE|ENDCASE|'
             r'DO\s*WHILE|ENDDO|FOR|ENDFOR|NEXT|IF|ELSE|ENDIF|PRINTJOB|'
             r'ENDPRINTJOB|SCAN|ENDSCAN|TEXT|ENDTEXT|=)',
                Keyword.Reserved, '#pop'),
            (r'#\s*(IF|ELIF|ELSE|ENDIF|DEFINE|IFDEF|IFNDEF|INCLUDE)',
                Comment.Preproc, '#pop'),
            (r'(m\.)?[a-z_]\w*', Name.Variable, '#pop'),
            (r'.', Text, '#pop'),
        ],
    }

# === NexusCore/openenv\Lib\site-packages\litellm\llms\bedrock\common_utils.py ===
"""
Common utilities used across bedrock chat/embedding/image generation
"""

import os
from typing import List, Literal, Optional, Union

import httpx

import litellm
from litellm.llms.base_llm.base_utils import BaseLLMModelInfo
from litellm.llms.base_llm.chat.transformation import BaseLLMException
from litellm.secret_managers.main import get_secret


class BedrockError(BaseLLMException):
    pass


class AmazonBedrockGlobalConfig:
    def __init__(self):
        pass

    def get_mapped_special_auth_params(self) -> dict:
        """
        Mapping of common auth params across bedrock/vertex/azure/watsonx
        """
        return {"region_name": "aws_region_name"}

    def map_special_auth_params(self, non_default_params: dict, optional_params: dict):
        mapped_params = self.get_mapped_special_auth_params()
        for param, value in non_default_params.items():
            if param in mapped_params:
                optional_params[mapped_params[param]] = value
        return optional_params

    def get_all_regions(self) -> List[str]:
        return (
            self.get_us_regions()
            + self.get_eu_regions()
            + self.get_ap_regions()
            + self.get_ca_regions()
            + self.get_sa_regions()
        )

    def get_ap_regions(self) -> List[str]:
        """
        Source: https://www.aws-services.info/bedrock.html
        """
        return [
            "ap-northeast-1",  # Asia Pacific (Tokyo)
            "ap-northeast-2",  # Asia Pacific (Seoul)
            "ap-northeast-3",  # Asia Pacific (Osaka)
            "ap-south-1",  # Asia Pacific (Mumbai)
            "ap-south-2",  # Asia Pacific (Hyderabad)
            "ap-southeast-1",  # Asia Pacific (Singapore)
            "ap-southeast-2",  # Asia Pacific (Sydney)
        ]

    def get_sa_regions(self) -> List[str]:
        return ["sa-east-1"]

    def get_eu_regions(self) -> List[str]:
        """
        Source: https://www.aws-services.info/bedrock.html
        """
        return [
            "eu-west-1",  # Europe (Ireland)
            "eu-west-2",  # Europe (London)
            "eu-west-3",  # Europe (Paris)
            "eu-central-1",  # Europe (Frankfurt)
            "eu-central-2",  # Europe (Zurich)
            "eu-south-1",  # Europe (Milan)
            "eu-south-2",  # Europe (Spain)
            "eu-north-1",  # Europe (Stockholm)
        ]

    def get_ca_regions(self) -> List[str]:
        return ["ca-central-1"]

    def get_us_regions(self) -> List[str]:
        """
        Source: https://www.aws-services.info/bedrock.html
        """
        return [
            "us-east-1",  # US East (N. Virginia)
            "us-east-2",  # US East (Ohio)
            "us-west-1",  # US West (N. California)
            "us-west-2",  # US West (Oregon)
            "us-gov-east-1",  # AWS GovCloud (US-East)
            "us-gov-west-1",  # AWS GovCloud (US-West)
        ]


def add_custom_header(headers):
    """Closure to capture the headers and add them."""

    def callback(request, **kwargs):
        """Actual callback function that Boto3 will call."""
        for header_name, header_value in headers.items():
            request.headers.add_header(header_name, header_value)

    return callback


def init_bedrock_client(
    region_name=None,
    aws_access_key_id: Optional[str] = None,
    aws_secret_access_key: Optional[str] = None,
    aws_region_name: Optional[str] = None,
    aws_bedrock_runtime_endpoint: Optional[str] = None,
    aws_session_name: Optional[str] = None,
    aws_profile_name: Optional[str] = None,
    aws_role_name: Optional[str] = None,
    aws_web_identity_token: Optional[str] = None,
    extra_headers: Optional[dict] = None,
    timeout: Optional[Union[float, httpx.Timeout]] = None,
):
    # check for custom AWS_REGION_NAME and use it if not passed to init_bedrock_client
    litellm_aws_region_name = get_secret("AWS_REGION_NAME", None)
    standard_aws_region_name = get_secret("AWS_REGION", None)
    ## CHECK IS  'os.environ/' passed in
    # Define the list of parameters to check
    params_to_check = [
        aws_access_key_id,
        aws_secret_access_key,
        aws_region_name,
        aws_bedrock_runtime_endpoint,
        aws_session_name,
        aws_profile_name,
        aws_role_name,
        aws_web_identity_token,
    ]

    # Iterate over parameters and update if needed
    for i, param in enumerate(params_to_check):
        if param and param.startswith("os.environ/"):
            params_to_check[i] = get_secret(param)  # type: ignore
    # Assign updated values back to parameters
    (
        aws_access_key_id,
        aws_secret_access_key,
        aws_region_name,
        aws_bedrock_runtime_endpoint,
        aws_session_name,
        aws_profile_name,
        aws_role_name,
        aws_web_identity_token,
    ) = params_to_check

    # SSL certificates (a.k.a CA bundle) used to verify the identity of requested hosts.
    ssl_verify = os.getenv("SSL_VERIFY", litellm.ssl_verify)

    ### SET REGION NAME
    if region_name:
        pass
    elif aws_region_name:
        region_name = aws_region_name
    elif litellm_aws_region_name:
        region_name = litellm_aws_region_name
    elif standard_aws_region_name:
        region_name = standard_aws_region_name
    else:
        raise BedrockError(
            message="AWS region not set: set AWS_REGION_NAME or AWS_REGION env variable or in .env file",
            status_code=401,
        )

    # check for custom AWS_BEDROCK_RUNTIME_ENDPOINT and use it if not passed to init_bedrock_client
    env_aws_bedrock_runtime_endpoint = get_secret("AWS_BEDROCK_RUNTIME_ENDPOINT")
    if aws_bedrock_runtime_endpoint:
        endpoint_url = aws_bedrock_runtime_endpoint
    elif env_aws_bedrock_runtime_endpoint:
        endpoint_url = env_aws_bedrock_runtime_endpoint
    else:
        endpoint_url = f"https://bedrock-runtime.{region_name}.amazonaws.com"

    import boto3

    if isinstance(timeout, float):
        config = boto3.session.Config(connect_timeout=timeout, read_timeout=timeout)  # type: ignore
    elif isinstance(timeout, httpx.Timeout):
        config = boto3.session.Config(  # type: ignore
            connect_timeout=timeout.connect, read_timeout=timeout.read
        )
    else:
        config = boto3.session.Config()  # type: ignore

    ### CHECK STS ###
    if (
        aws_web_identity_token is not None
        and aws_role_name is not None
        and aws_session_name is not None
    ):
        oidc_token = get_secret(aws_web_identity_token)

        if oidc_token is None:
            raise BedrockError(
                message="OIDC token could not be retrieved from secret manager.",
                status_code=401,
            )

        sts_client = boto3.client("sts")

        # https://docs.aws.amazon.com/STS/latest/APIReference/API_AssumeRoleWithWebIdentity.html
        # https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/sts/client/assume_role_with_web_identity.html
        sts_response = sts_client.assume_role_with_web_identity(
            RoleArn=aws_role_name,
            RoleSessionName=aws_session_name,
            WebIdentityToken=oidc_token,
            DurationSeconds=3600,
        )

        client = boto3.client(
            service_name="bedrock-runtime",
            aws_access_key_id=sts_response["Credentials"]["AccessKeyId"],
            aws_secret_access_key=sts_response["Credentials"]["SecretAccessKey"],
            aws_session_token=sts_response["Credentials"]["SessionToken"],
            region_name=region_name,
            endpoint_url=endpoint_url,
            config=config,
            verify=ssl_verify,
        )
    elif aws_role_name is not None and aws_session_name is not None:
        # use sts if role name passed in
        sts_client = boto3.client(
            "sts",
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key,
        )

        sts_response = sts_client.assume_role(
            RoleArn=aws_role_name, RoleSessionName=aws_session_name
        )

        client = boto3.client(
            service_name="bedrock-runtime",
            aws_access_key_id=sts_response["Credentials"]["AccessKeyId"],
            aws_secret_access_key=sts_response["Credentials"]["SecretAccessKey"],
            aws_session_token=sts_response["Credentials"]["SessionToken"],
            region_name=region_name,
            endpoint_url=endpoint_url,
            config=config,
            verify=ssl_verify,
        )
    elif aws_access_key_id is not None:
        # uses auth params passed to completion
        # aws_access_key_id is not None, assume user is trying to auth using litellm.completion

        client = boto3.client(
            service_name="bedrock-runtime",
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key,
            region_name=region_name,
            endpoint_url=endpoint_url,
            config=config,
            verify=ssl_verify,
        )
    elif aws_profile_name is not None:
        # uses auth values from AWS profile usually stored in ~/.aws/credentials

        client = boto3.Session(profile_name=aws_profile_name).client(
            service_name="bedrock-runtime",
            region_name=region_name,
            endpoint_url=endpoint_url,
            config=config,
            verify=ssl_verify,
        )
    else:
        # aws_access_key_id is None, assume user is trying to auth using env variables
        # boto3 automatically reads env variables

        client = boto3.client(
            service_name="bedrock-runtime",
            region_name=region_name,
            endpoint_url=endpoint_url,
            config=config,
            verify=ssl_verify,
        )
    if extra_headers:
        client.meta.events.register(
            "before-sign.bedrock-runtime.*", add_custom_header(extra_headers)
        )

    return client


class ModelResponseIterator:
    def __init__(self, model_response):
        self.model_response = model_response
        self.is_done = False

    # Sync iterator
    def __iter__(self):
        return self

    def __next__(self):
        if self.is_done:
            raise StopIteration
        self.is_done = True
        return self.model_response

    # Async iterator
    def __aiter__(self):
        return self

    async def __anext__(self):
        if self.is_done:
            raise StopAsyncIteration
        self.is_done = True
        return self.model_response


def get_bedrock_tool_name(response_tool_name: str) -> str:
    """
    If litellm formatted the input tool name, we need to convert it back to the original name.

    Args:
        response_tool_name (str): The name of the tool as received from the response.

    Returns:
        str: The original name of the tool.
    """

    if response_tool_name in litellm.bedrock_tool_name_mappings.cache_dict:
        response_tool_name = litellm.bedrock_tool_name_mappings.cache_dict[
            response_tool_name
        ]
    return response_tool_name


class BedrockModelInfo(BaseLLMModelInfo):
    global_config = AmazonBedrockGlobalConfig()
    all_global_regions = global_config.get_all_regions()

    @staticmethod
    def extract_model_name_from_arn(model: str) -> str:
        """
        Extract the model name from an AWS Bedrock ARN.
        Returns the string after the last '/' if 'arn' is in the input string.

        Args:
            arn (str): The ARN string to parse

        Returns:
            str: The extracted model name if 'arn' is in the string,
                otherwise returns the original string
        """
        if "arn" in model.lower():
            return model.split("/")[-1]
        return model

    @staticmethod
    def get_non_litellm_routing_model_name(model: str) -> str:
        if model.startswith("bedrock/"):
            model = model.split("/", 1)[1]

        if model.startswith("converse/"):
            model = model.split("/", 1)[1]

        if model.startswith("invoke/"):
            model = model.split("/", 1)[1]

        return model

    @staticmethod
    def get_base_model(model: str) -> str:
        """
        Get the base model from the given model name.

        Handle model names like - "us.meta.llama3-2-11b-instruct-v1:0" -> "meta.llama3-2-11b-instruct-v1"
        AND "meta.llama3-2-11b-instruct-v1:0" -> "meta.llama3-2-11b-instruct-v1"
        """

        model = BedrockModelInfo.get_non_litellm_routing_model_name(model=model)
        model = BedrockModelInfo.extract_model_name_from_arn(model)

        potential_region = model.split(".", 1)[0]

        alt_potential_region = model.split("/", 1)[
            0
        ]  # in model cost map we store regional information like `/us-west-2/bedrock-model`

        if (
            potential_region
            in BedrockModelInfo._supported_cross_region_inference_region()
        ):
            return model.split(".", 1)[1]
        elif (
            alt_potential_region in BedrockModelInfo.all_global_regions
            and len(model.split("/", 1)) > 1
        ):
            return model.split("/", 1)[1]

        return model

    @staticmethod
    def _supported_cross_region_inference_region() -> List[str]:
        """
        Abbreviations of regions AWS Bedrock supports for cross region inference
        """
        return ["us", "eu", "apac"]

    @staticmethod
    def get_bedrock_route(
        model: str,
    ) -> Literal["converse", "invoke", "converse_like", "agent"]:
        """
        Get the bedrock route for the given model.
        """
        base_model = BedrockModelInfo.get_base_model(model)
        alt_model = BedrockModelInfo.get_non_litellm_routing_model_name(model=model)
        if "invoke/" in model:
            return "invoke"
        elif "converse_like" in model:
            return "converse_like"
        elif "converse/" in model:
            return "converse"
        elif "agent/" in model:
            return "agent"
        elif (
            base_model in litellm.bedrock_converse_models
            or alt_model in litellm.bedrock_converse_models
        ):
            return "converse"
        return "invoke"

# === NexusCore/openenv\Lib\site-packages\openai\resources\beta\realtime\sessions.py ===
# File generated from our OpenAPI spec by Stainless. See CONTRIBUTING.md for details.

from __future__ import annotations

from typing import List, Union, Iterable
from typing_extensions import Literal

import httpx

from .... import _legacy_response
from ...._types import NOT_GIVEN, Body, Query, Headers, NotGiven
from ...._utils import maybe_transform, async_maybe_transform
from ...._compat import cached_property
from ...._resource import SyncAPIResource, AsyncAPIResource
from ...._response import to_streamed_response_wrapper, async_to_streamed_response_wrapper
from ...._base_client import make_request_options
from ....types.beta.realtime import session_create_params
from ....types.beta.realtime.session_create_response import SessionCreateResponse

__all__ = ["Sessions", "AsyncSessions"]


class Sessions(SyncAPIResource):
    @cached_property
    def with_raw_response(self) -> SessionsWithRawResponse:
        """
        This property can be used as a prefix for any HTTP method call to return
        the raw response object instead of the parsed content.

        For more information, see https://www.github.com/openai/openai-python#accessing-raw-response-data-eg-headers
        """
        return SessionsWithRawResponse(self)

    @cached_property
    def with_streaming_response(self) -> SessionsWithStreamingResponse:
        """
        An alternative to `.with_raw_response` that doesn't eagerly read the response body.

        For more information, see https://www.github.com/openai/openai-python#with_streaming_response
        """
        return SessionsWithStreamingResponse(self)

    def create(
        self,
        *,
        client_secret: session_create_params.ClientSecret | NotGiven = NOT_GIVEN,
        input_audio_format: Literal["pcm16", "g711_ulaw", "g711_alaw"] | NotGiven = NOT_GIVEN,
        input_audio_noise_reduction: session_create_params.InputAudioNoiseReduction | NotGiven = NOT_GIVEN,
        input_audio_transcription: session_create_params.InputAudioTranscription | NotGiven = NOT_GIVEN,
        instructions: str | NotGiven = NOT_GIVEN,
        max_response_output_tokens: Union[int, Literal["inf"]] | NotGiven = NOT_GIVEN,
        modalities: List[Literal["text", "audio"]] | NotGiven = NOT_GIVEN,
        model: Literal[
            "gpt-4o-realtime-preview",
            "gpt-4o-realtime-preview-2024-10-01",
            "gpt-4o-realtime-preview-2024-12-17",
            "gpt-4o-realtime-preview-2025-06-03",
            "gpt-4o-mini-realtime-preview",
            "gpt-4o-mini-realtime-preview-2024-12-17",
        ]
        | NotGiven = NOT_GIVEN,
        output_audio_format: Literal["pcm16", "g711_ulaw", "g711_alaw"] | NotGiven = NOT_GIVEN,
        speed: float | NotGiven = NOT_GIVEN,
        temperature: float | NotGiven = NOT_GIVEN,
        tool_choice: str | NotGiven = NOT_GIVEN,
        tools: Iterable[session_create_params.Tool] | NotGiven = NOT_GIVEN,
        tracing: session_create_params.Tracing | NotGiven = NOT_GIVEN,
        turn_detection: session_create_params.TurnDetection | NotGiven = NOT_GIVEN,
        voice: Union[
            str, Literal["alloy", "ash", "ballad", "coral", "echo", "fable", "onyx", "nova", "sage", "shimmer", "verse"]
        ]
        | NotGiven = NOT_GIVEN,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> SessionCreateResponse:
        """
        Create an ephemeral API token for use in client-side applications with the
        Realtime API. Can be configured with the same session parameters as the
        `session.update` client event.

        It responds with a session object, plus a `client_secret` key which contains a
        usable ephemeral API token that can be used to authenticate browser clients for
        the Realtime API.

        Args:
          client_secret: Configuration options for the generated client secret.

          input_audio_format: The format of input audio. Options are `pcm16`, `g711_ulaw`, or `g711_alaw`. For
              `pcm16`, input audio must be 16-bit PCM at a 24kHz sample rate, single channel
              (mono), and little-endian byte order.

          input_audio_noise_reduction: Configuration for input audio noise reduction. This can be set to `null` to turn
              off. Noise reduction filters audio added to the input audio buffer before it is
              sent to VAD and the model. Filtering the audio can improve VAD and turn
              detection accuracy (reducing false positives) and model performance by improving
              perception of the input audio.

          input_audio_transcription: Configuration for input audio transcription, defaults to off and can be set to
              `null` to turn off once on. Input audio transcription is not native to the
              model, since the model consumes audio directly. Transcription runs
              asynchronously through
              [the /audio/transcriptions endpoint](https://platform.openai.com/docs/api-reference/audio/createTranscription)
              and should be treated as guidance of input audio content rather than precisely
              what the model heard. The client can optionally set the language and prompt for
              transcription, these offer additional guidance to the transcription service.

          instructions: The default system instructions (i.e. system message) prepended to model calls.
              This field allows the client to guide the model on desired responses. The model
              can be instructed on response content and format, (e.g. "be extremely succinct",
              "act friendly", "here are examples of good responses") and on audio behavior
              (e.g. "talk quickly", "inject emotion into your voice", "laugh frequently"). The
              instructions are not guaranteed to be followed by the model, but they provide
              guidance to the model on the desired behavior.

              Note that the server sets default instructions which will be used if this field
              is not set and are visible in the `session.created` event at the start of the
              session.

          max_response_output_tokens: Maximum number of output tokens for a single assistant response, inclusive of
              tool calls. Provide an integer between 1 and 4096 to limit output tokens, or
              `inf` for the maximum available tokens for a given model. Defaults to `inf`.

          modalities: The set of modalities the model can respond with. To disable audio, set this to
              ["text"].

          model: The Realtime model used for this session.

          output_audio_format: The format of output audio. Options are `pcm16`, `g711_ulaw`, or `g711_alaw`.
              For `pcm16`, output audio is sampled at a rate of 24kHz.

          speed: The speed of the model's spoken response. 1.0 is the default speed. 0.25 is the
              minimum speed. 1.5 is the maximum speed. This value can only be changed in
              between model turns, not while a response is in progress.

          temperature: Sampling temperature for the model, limited to [0.6, 1.2]. For audio models a
              temperature of 0.8 is highly recommended for best performance.

          tool_choice: How the model chooses tools. Options are `auto`, `none`, `required`, or specify
              a function.

          tools: Tools (functions) available to the model.

          tracing: Configuration options for tracing. Set to null to disable tracing. Once tracing
              is enabled for a session, the configuration cannot be modified.

              `auto` will create a trace for the session with default values for the workflow
              name, group id, and metadata.

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

          voice: The voice the model uses to respond. Voice cannot be changed during the session
              once the model has responded with audio at least once. Current voice options are
              `alloy`, `ash`, `ballad`, `coral`, `echo`, `fable`, `onyx`, `nova`, `sage`,
              `shimmer`, and `verse`.

          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request, in seconds
        """
        extra_headers = {"OpenAI-Beta": "assistants=v2", **(extra_headers or {})}
        return self._post(
            "/realtime/sessions",
            body=maybe_transform(
                {
                    "client_secret": client_secret,
                    "input_audio_format": input_audio_format,
                    "input_audio_noise_reduction": input_audio_noise_reduction,
                    "input_audio_transcription": input_audio_transcription,
                    "instructions": instructions,
                    "max_response_output_tokens": max_response_output_tokens,
                    "modalities": modalities,
                    "model": model,
                    "output_audio_format": output_audio_format,
                    "speed": speed,
                    "temperature": temperature,
                    "tool_choice": tool_choice,
                    "tools": tools,
                    "tracing": tracing,
                    "turn_detection": turn_detection,
                    "voice": voice,
                },
                session_create_params.SessionCreateParams,
            ),
            options=make_request_options(
                extra_headers=extra_headers, extra_query=extra_query, extra_body=extra_body, timeout=timeout
            ),
            cast_to=SessionCreateResponse,
        )


class AsyncSessions(AsyncAPIResource):
    @cached_property
    def with_raw_response(self) -> AsyncSessionsWithRawResponse:
        """
        This property can be used as a prefix for any HTTP method call to return
        the raw response object instead of the parsed content.

        For more information, see https://www.github.com/openai/openai-python#accessing-raw-response-data-eg-headers
        """
        return AsyncSessionsWithRawResponse(self)

    @cached_property
    def with_streaming_response(self) -> AsyncSessionsWithStreamingResponse:
        """
        An alternative to `.with_raw_response` that doesn't eagerly read the response body.

        For more information, see https://www.github.com/openai/openai-python#with_streaming_response
        """
        return AsyncSessionsWithStreamingResponse(self)

    async def create(
        self,
        *,
        client_secret: session_create_params.ClientSecret | NotGiven = NOT_GIVEN,
        input_audio_format: Literal["pcm16", "g711_ulaw", "g711_alaw"] | NotGiven = NOT_GIVEN,
        input_audio_noise_reduction: session_create_params.InputAudioNoiseReduction | NotGiven = NOT_GIVEN,
        input_audio_transcription: session_create_params.InputAudioTranscription | NotGiven = NOT_GIVEN,
        instructions: str | NotGiven = NOT_GIVEN,
        max_response_output_tokens: Union[int, Literal["inf"]] | NotGiven = NOT_GIVEN,
        modalities: List[Literal["text", "audio"]] | NotGiven = NOT_GIVEN,
        model: Literal[
            "gpt-4o-realtime-preview",
            "gpt-4o-realtime-preview-2024-10-01",
            "gpt-4o-realtime-preview-2024-12-17",
            "gpt-4o-realtime-preview-2025-06-03",
            "gpt-4o-mini-realtime-preview",
            "gpt-4o-mini-realtime-preview-2024-12-17",
        ]
        | NotGiven = NOT_GIVEN,
        output_audio_format: Literal["pcm16", "g711_ulaw", "g711_alaw"] | NotGiven = NOT_GIVEN,
        speed: float | NotGiven = NOT_GIVEN,
        temperature: float | NotGiven = NOT_GIVEN,
        tool_choice: str | NotGiven = NOT_GIVEN,
        tools: Iterable[session_create_params.Tool] | NotGiven = NOT_GIVEN,
        tracing: session_create_params.Tracing | NotGiven = NOT_GIVEN,
        turn_detection: session_create_params.TurnDetection | NotGiven = NOT_GIVEN,
        voice: Union[
            str, Literal["alloy", "ash", "ballad", "coral", "echo", "fable", "onyx", "nova", "sage", "shimmer", "verse"]
        ]
        | NotGiven = NOT_GIVEN,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> SessionCreateResponse:
        """
        Create an ephemeral API token for use in client-side applications with the
        Realtime API. Can be configured with the same session parameters as the
        `session.update` client event.

        It responds with a session object, plus a `client_secret` key which contains a
        usable ephemeral API token that can be used to authenticate browser clients for
        the Realtime API.

        Args:
          client_secret: Configuration options for the generated client secret.

          input_audio_format: The format of input audio. Options are `pcm16`, `g711_ulaw`, or `g711_alaw`. For
              `pcm16`, input audio must be 16-bit PCM at a 24kHz sample rate, single channel
              (mono), and little-endian byte order.

          input_audio_noise_reduction: Configuration for input audio noise reduction. This can be set to `null` to turn
              off. Noise reduction filters audio added to the input audio buffer before it is
              sent to VAD and the model. Filtering the audio can improve VAD and turn
              detection accuracy (reducing false positives) and model performance by improving
              perception of the input audio.

          input_audio_transcription: Configuration for input audio transcription, defaults to off and can be set to
              `null` to turn off once on. Input audio transcription is not native to the
              model, since the model consumes audio directly. Transcription runs
              asynchronously through
              [the /audio/transcriptions endpoint](https://platform.openai.com/docs/api-reference/audio/createTranscription)
              and should be treated as guidance of input audio content rather than precisely
              what the model heard. The client can optionally set the language and prompt for
              transcription, these offer additional guidance to the transcription service.

          instructions: The default system instructions (i.e. system message) prepended to model calls.
              This field allows the client to guide the model on desired responses. The model
              can be instructed on response content and format, (e.g. "be extremely succinct",
              "act friendly", "here are examples of good responses") and on audio behavior
              (e.g. "talk quickly", "inject emotion into your voice", "laugh frequently"). The
              instructions are not guaranteed to be followed by the model, but they provide
              guidance to the model on the desired behavior.

              Note that the server sets default instructions which will be used if this field
              is not set and are visible in the `session.created` event at the start of the
              session.

          max_response_output_tokens: Maximum number of output tokens for a single assistant response, inclusive of
              tool calls. Provide an integer between 1 and 4096 to limit output tokens, or
              `inf` for the maximum available tokens for a given model. Defaults to `inf`.

          modalities: The set of modalities the model can respond with. To disable audio, set this to
              ["text"].

          model: The Realtime model used for this session.

          output_audio_format: The format of output audio. Options are `pcm16`, `g711_ulaw`, or `g711_alaw`.
              For `pcm16`, output audio is sampled at a rate of 24kHz.

          speed: The speed of the model's spoken response. 1.0 is the default speed. 0.25 is the
              minimum speed. 1.5 is the maximum speed. This value can only be changed in
              between model turns, not while a response is in progress.

          temperature: Sampling temperature for the model, limited to [0.6, 1.2]. For audio models a
              temperature of 0.8 is highly recommended for best performance.

          tool_choice: How the model chooses tools. Options are `auto`, `none`, `required`, or specify
              a function.

          tools: Tools (functions) available to the model.

          tracing: Configuration options for tracing. Set to null to disable tracing. Once tracing
              is enabled for a session, the configuration cannot be modified.

              `auto` will create a trace for the session with default values for the workflow
              name, group id, and metadata.

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

          voice: The voice the model uses to respond. Voice cannot be changed during the session
              once the model has responded with audio at least once. Current voice options are
              `alloy`, `ash`, `ballad`, `coral`, `echo`, `fable`, `onyx`, `nova`, `sage`,
              `shimmer`, and `verse`.

          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request, in seconds
        """
        extra_headers = {"OpenAI-Beta": "assistants=v2", **(extra_headers or {})}
        return await self._post(
            "/realtime/sessions",
            body=await async_maybe_transform(
                {
                    "client_secret": client_secret,
                    "input_audio_format": input_audio_format,
                    "input_audio_noise_reduction": input_audio_noise_reduction,
                    "input_audio_transcription": input_audio_transcription,
                    "instructions": instructions,
                    "max_response_output_tokens": max_response_output_tokens,
                    "modalities": modalities,
                    "model": model,
                    "output_audio_format": output_audio_format,
                    "speed": speed,
                    "temperature": temperature,
                    "tool_choice": tool_choice,
                    "tools": tools,
                    "tracing": tracing,
                    "turn_detection": turn_detection,
                    "voice": voice,
                },
                session_create_params.SessionCreateParams,
            ),
            options=make_request_options(
                extra_headers=extra_headers, extra_query=extra_query, extra_body=extra_body, timeout=timeout
            ),
            cast_to=SessionCreateResponse,
        )


class SessionsWithRawResponse:
    def __init__(self, sessions: Sessions) -> None:
        self._sessions = sessions

        self.create = _legacy_response.to_raw_response_wrapper(
            sessions.create,
        )


class AsyncSessionsWithRawResponse:
    def __init__(self, sessions: AsyncSessions) -> None:
        self._sessions = sessions

        self.create = _legacy_response.async_to_raw_response_wrapper(
            sessions.create,
        )


class SessionsWithStreamingResponse:
    def __init__(self, sessions: Sessions) -> None:
        self._sessions = sessions

        self.create = to_streamed_response_wrapper(
            sessions.create,
        )


class AsyncSessionsWithStreamingResponse:
    def __init__(self, sessions: AsyncSessions) -> None:
        self._sessions = sessions

        self.create = async_to_streamed_response_wrapper(
            sessions.create,
        )

# === NexusCore/openenv\Lib\site-packages\selenium\webdriver\common\devtools\v136\bluetooth_emulation.py ===
# DO NOT EDIT THIS FILE!
#
# This file is generated from the CDP specification. If you need to make
# changes, edit the generator and regenerate all of the modules.
#
# CDP domain: BluetoothEmulation (experimental)
from __future__ import annotations
from .util import event_class, T_JSON_DICT
from dataclasses import dataclass
import enum
import typing

class CentralState(enum.Enum):
    '''
    Indicates the various states of Central.
    '''
    ABSENT = "absent"
    POWERED_OFF = "powered-off"
    POWERED_ON = "powered-on"

    def to_json(self):
        return self.value

    @classmethod
    def from_json(cls, json):
        return cls(json)


class GATTOperationType(enum.Enum):
    '''
    Indicates the various types of GATT event.
    '''
    CONNECTION = "connection"
    DISCOVERY = "discovery"

    def to_json(self):
        return self.value

    @classmethod
    def from_json(cls, json):
        return cls(json)


@dataclass
class ManufacturerData:
    '''
    Stores the manufacturer data
    '''
    #: Company identifier
    #: https://bitbucket.org/bluetooth-SIG/public/src/main/assigned_numbers/company_identifiers/company_identifiers.yaml
    #: https://usb.org/developers
    key: int

    #: Manufacturer-specific data
    data: str

    def to_json(self):
        json = dict()
        json['key'] = self.key
        json['data'] = self.data
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            key=int(json['key']),
            data=str(json['data']),
        )


@dataclass
class ScanRecord:
    '''
    Stores the byte data of the advertisement packet sent by a Bluetooth device.
    '''
    name: typing.Optional[str] = None

    uuids: typing.Optional[typing.List[str]] = None

    #: Stores the external appearance description of the device.
    appearance: typing.Optional[int] = None

    #: Stores the transmission power of a broadcasting device.
    tx_power: typing.Optional[int] = None

    #: Key is the company identifier and the value is an array of bytes of
    #: manufacturer specific data.
    manufacturer_data: typing.Optional[typing.List[ManufacturerData]] = None

    def to_json(self):
        json = dict()
        if self.name is not None:
            json['name'] = self.name
        if self.uuids is not None:
            json['uuids'] = [i for i in self.uuids]
        if self.appearance is not None:
            json['appearance'] = self.appearance
        if self.tx_power is not None:
            json['txPower'] = self.tx_power
        if self.manufacturer_data is not None:
            json['manufacturerData'] = [i.to_json() for i in self.manufacturer_data]
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            name=str(json['name']) if 'name' in json else None,
            uuids=[str(i) for i in json['uuids']] if 'uuids' in json else None,
            appearance=int(json['appearance']) if 'appearance' in json else None,
            tx_power=int(json['txPower']) if 'txPower' in json else None,
            manufacturer_data=[ManufacturerData.from_json(i) for i in json['manufacturerData']] if 'manufacturerData' in json else None,
        )


@dataclass
class ScanEntry:
    '''
    Stores the advertisement packet information that is sent by a Bluetooth device.
    '''
    device_address: str

    rssi: int

    scan_record: ScanRecord

    def to_json(self):
        json = dict()
        json['deviceAddress'] = self.device_address
        json['rssi'] = self.rssi
        json['scanRecord'] = self.scan_record.to_json()
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            device_address=str(json['deviceAddress']),
            rssi=int(json['rssi']),
            scan_record=ScanRecord.from_json(json['scanRecord']),
        )


@dataclass
class CharacteristicProperties:
    '''
    Describes the properties of a characteristic. This follows Bluetooth Core
    Specification BT 4.2 Vol 3 Part G 3.3.1. Characteristic Properties.
    '''
    broadcast: typing.Optional[bool] = None

    read: typing.Optional[bool] = None

    write_without_response: typing.Optional[bool] = None

    write: typing.Optional[bool] = None

    notify: typing.Optional[bool] = None

    indicate: typing.Optional[bool] = None

    authenticated_signed_writes: typing.Optional[bool] = None

    extended_properties: typing.Optional[bool] = None

    def to_json(self):
        json = dict()
        if self.broadcast is not None:
            json['broadcast'] = self.broadcast
        if self.read is not None:
            json['read'] = self.read
        if self.write_without_response is not None:
            json['writeWithoutResponse'] = self.write_without_response
        if self.write is not None:
            json['write'] = self.write
        if self.notify is not None:
            json['notify'] = self.notify
        if self.indicate is not None:
            json['indicate'] = self.indicate
        if self.authenticated_signed_writes is not None:
            json['authenticatedSignedWrites'] = self.authenticated_signed_writes
        if self.extended_properties is not None:
            json['extendedProperties'] = self.extended_properties
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            broadcast=bool(json['broadcast']) if 'broadcast' in json else None,
            read=bool(json['read']) if 'read' in json else None,
            write_without_response=bool(json['writeWithoutResponse']) if 'writeWithoutResponse' in json else None,
            write=bool(json['write']) if 'write' in json else None,
            notify=bool(json['notify']) if 'notify' in json else None,
            indicate=bool(json['indicate']) if 'indicate' in json else None,
            authenticated_signed_writes=bool(json['authenticatedSignedWrites']) if 'authenticatedSignedWrites' in json else None,
            extended_properties=bool(json['extendedProperties']) if 'extendedProperties' in json else None,
        )


def enable(
        state: CentralState,
        le_supported: bool
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Enable the BluetoothEmulation domain.

    :param state: State of the simulated central.
    :param le_supported: If the simulated central supports low-energy.
    '''
    params: T_JSON_DICT = dict()
    params['state'] = state.to_json()
    params['leSupported'] = le_supported
    cmd_dict: T_JSON_DICT = {
        'method': 'BluetoothEmulation.enable',
        'params': params,
    }
    json = yield cmd_dict


def set_simulated_central_state(
        state: CentralState
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Set the state of the simulated central.

    :param state: State of the simulated central.
    '''
    params: T_JSON_DICT = dict()
    params['state'] = state.to_json()
    cmd_dict: T_JSON_DICT = {
        'method': 'BluetoothEmulation.setSimulatedCentralState',
        'params': params,
    }
    json = yield cmd_dict


def disable() -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Disable the BluetoothEmulation domain.
    '''
    cmd_dict: T_JSON_DICT = {
        'method': 'BluetoothEmulation.disable',
    }
    json = yield cmd_dict


def simulate_preconnected_peripheral(
        address: str,
        name: str,
        manufacturer_data: typing.List[ManufacturerData],
        known_service_uuids: typing.List[str]
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Simulates a peripheral with ``address``, ``name`` and ``knownServiceUuids``
    that has already been connected to the system.

    :param address:
    :param name:
    :param manufacturer_data:
    :param known_service_uuids:
    '''
    params: T_JSON_DICT = dict()
    params['address'] = address
    params['name'] = name
    params['manufacturerData'] = [i.to_json() for i in manufacturer_data]
    params['knownServiceUuids'] = [i for i in known_service_uuids]
    cmd_dict: T_JSON_DICT = {
        'method': 'BluetoothEmulation.simulatePreconnectedPeripheral',
        'params': params,
    }
    json = yield cmd_dict


def simulate_advertisement(
        entry: ScanEntry
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Simulates an advertisement packet described in ``entry`` being received by
    the central.

    :param entry:
    '''
    params: T_JSON_DICT = dict()
    params['entry'] = entry.to_json()
    cmd_dict: T_JSON_DICT = {
        'method': 'BluetoothEmulation.simulateAdvertisement',
        'params': params,
    }
    json = yield cmd_dict


def simulate_gatt_operation_response(
        address: str,
        type_: GATTOperationType,
        code: int
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Simulates the response code from the peripheral with ``address`` for a
    GATT operation of ``type``. The ``code`` value follows the HCI Error Codes from
    Bluetooth Core Specification Vol 2 Part D 1.3 List Of Error Codes.

    :param address:
    :param type_:
    :param code:
    '''
    params: T_JSON_DICT = dict()
    params['address'] = address
    params['type'] = type_.to_json()
    params['code'] = code
    cmd_dict: T_JSON_DICT = {
        'method': 'BluetoothEmulation.simulateGATTOperationResponse',
        'params': params,
    }
    json = yield cmd_dict


def add_service(
        address: str,
        service_uuid: str
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,str]:
    '''
    Adds a service with ``serviceUuid`` to the peripheral with ``address``.

    :param address:
    :param service_uuid:
    :returns: An identifier that uniquely represents this service.
    '''
    params: T_JSON_DICT = dict()
    params['address'] = address
    params['serviceUuid'] = service_uuid
    cmd_dict: T_JSON_DICT = {
        'method': 'BluetoothEmulation.addService',
        'params': params,
    }
    json = yield cmd_dict
    return str(json['serviceId'])


def remove_service(
        address: str,
        service_id: str
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Removes the service respresented by ``serviceId`` from the peripheral with
    ``address``.

    :param address:
    :param service_id:
    '''
    params: T_JSON_DICT = dict()
    params['address'] = address
    params['serviceId'] = service_id
    cmd_dict: T_JSON_DICT = {
        'method': 'BluetoothEmulation.removeService',
        'params': params,
    }
    json = yield cmd_dict


def add_characteristic(
        address: str,
        service_id: str,
        characteristic_uuid: str,
        properties: CharacteristicProperties
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,str]:
    '''
    Adds a characteristic with ``characteristicUuid`` and ``properties`` to the
    service represented by ``serviceId`` in the peripheral with ``address``.

    :param address:
    :param service_id:
    :param characteristic_uuid:
    :param properties:
    :returns: An identifier that uniquely represents this characteristic.
    '''
    params: T_JSON_DICT = dict()
    params['address'] = address
    params['serviceId'] = service_id
    params['characteristicUuid'] = characteristic_uuid
    params['properties'] = properties.to_json()
    cmd_dict: T_JSON_DICT = {
        'method': 'BluetoothEmulation.addCharacteristic',
        'params': params,
    }
    json = yield cmd_dict
    return str(json['characteristicId'])


def remove_characteristic(
        address: str,
        service_id: str,
        characteristic_id: str
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Removes the characteristic respresented by ``characteristicId`` from the
    service respresented by ``serviceId`` in the peripheral with ``address``.

    :param address:
    :param service_id:
    :param characteristic_id:
    '''
    params: T_JSON_DICT = dict()
    params['address'] = address
    params['serviceId'] = service_id
    params['characteristicId'] = characteristic_id
    cmd_dict: T_JSON_DICT = {
        'method': 'BluetoothEmulation.removeCharacteristic',
        'params': params,
    }
    json = yield cmd_dict


@event_class('BluetoothEmulation.gattOperationReceived')
@dataclass
class GattOperationReceived:
    '''
    Event for when a GATT operation of ``type`` to the peripheral with ``address``
    happened.
    '''
    address: str
    type_: GATTOperationType

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> GattOperationReceived:
        return cls(
            address=str(json['address']),
            type_=GATTOperationType.from_json(json['type'])
        )

# === NexusCore/openenv\Lib\site-packages\huggingface_hub\fastai_utils.py ===
import json
import os
from pathlib import Path
from pickle import DEFAULT_PROTOCOL, PicklingError
from typing import Any, Dict, List, Optional, Union

from packaging import version

from huggingface_hub import constants, snapshot_download
from huggingface_hub.hf_api import HfApi
from huggingface_hub.utils import (
    SoftTemporaryDirectory,
    get_fastai_version,
    get_fastcore_version,
    get_python_version,
)

from .utils import logging, validate_hf_hub_args
from .utils._runtime import _PY_VERSION  # noqa: F401 # for backward compatibility...


logger = logging.get_logger(__name__)


def _check_fastai_fastcore_versions(
    fastai_min_version: str = "2.4",
    fastcore_min_version: str = "1.3.27",
):
    """
    Checks that the installed fastai and fastcore versions are compatible for pickle serialization.

    Args:
        fastai_min_version (`str`, *optional*):
            The minimum fastai version supported.
        fastcore_min_version (`str`, *optional*):
            The minimum fastcore version supported.

    <Tip>
    Raises the following error:

        - [`ImportError`](https://docs.python.org/3/library/exceptions.html#ImportError)
          if the fastai or fastcore libraries are not available or are of an invalid version.

    </Tip>
    """

    if (get_fastcore_version() or get_fastai_version()) == "N/A":
        raise ImportError(
            f"fastai>={fastai_min_version} and fastcore>={fastcore_min_version} are"
            f" required. Currently using fastai=={get_fastai_version()} and"
            f" fastcore=={get_fastcore_version()}."
        )

    current_fastai_version = version.Version(get_fastai_version())
    current_fastcore_version = version.Version(get_fastcore_version())

    if current_fastai_version < version.Version(fastai_min_version):
        raise ImportError(
            "`push_to_hub_fastai` and `from_pretrained_fastai` require a"
            f" fastai>={fastai_min_version} version, but you are using fastai version"
            f" {get_fastai_version()} which is incompatible. Upgrade with `pip install"
            " fastai==2.5.6`."
        )

    if current_fastcore_version < version.Version(fastcore_min_version):
        raise ImportError(
            "`push_to_hub_fastai` and `from_pretrained_fastai` require a"
            f" fastcore>={fastcore_min_version} version, but you are using fastcore"
            f" version {get_fastcore_version()} which is incompatible. Upgrade with"
            " `pip install fastcore==1.3.27`."
        )


def _check_fastai_fastcore_pyproject_versions(
    storage_folder: str,
    fastai_min_version: str = "2.4",
    fastcore_min_version: str = "1.3.27",
):
    """
    Checks that the `pyproject.toml` file in the directory `storage_folder` has fastai and fastcore versions
    that are compatible with `from_pretrained_fastai` and `push_to_hub_fastai`. If `pyproject.toml` does not exist
    or does not contain versions for fastai and fastcore, then it logs a warning.

    Args:
        storage_folder (`str`):
            Folder to look for the `pyproject.toml` file.
        fastai_min_version (`str`, *optional*):
            The minimum fastai version supported.
        fastcore_min_version (`str`, *optional*):
            The minimum fastcore version supported.

    <Tip>
    Raises the following errors:

        - [`ImportError`](https://docs.python.org/3/library/exceptions.html#ImportError)
          if the `toml` module is not installed.
        - [`ImportError`](https://docs.python.org/3/library/exceptions.html#ImportError)
          if the `pyproject.toml` indicates a lower than minimum supported version of fastai or fastcore.

    </Tip>
    """

    try:
        import toml
    except ModuleNotFoundError:
        raise ImportError(
            "`push_to_hub_fastai` and `from_pretrained_fastai` require the toml module."
            " Install it with `pip install toml`."
        )

    # Checks that a `pyproject.toml`, with `build-system` and `requires` sections, exists in the repository. If so, get a list of required packages.
    if not os.path.isfile(f"{storage_folder}/pyproject.toml"):
        logger.warning(
            "There is no `pyproject.toml` in the repository that contains the fastai"
            " `Learner`. The `pyproject.toml` would allow us to verify that your fastai"
            " and fastcore versions are compatible with those of the model you want to"
            " load."
        )
        return
    pyproject_toml = toml.load(f"{storage_folder}/pyproject.toml")

    if "build-system" not in pyproject_toml.keys():
        logger.warning(
            "There is no `build-system` section in the pyproject.toml of the repository"
            " that contains the fastai `Learner`. The `build-system` would allow us to"
            " verify that your fastai and fastcore versions are compatible with those"
            " of the model you want to load."
        )
        return
    build_system_toml = pyproject_toml["build-system"]

    if "requires" not in build_system_toml.keys():
        logger.warning(
            "There is no `requires` section in the pyproject.toml of the repository"
            " that contains the fastai `Learner`. The `requires` would allow us to"
            " verify that your fastai and fastcore versions are compatible with those"
            " of the model you want to load."
        )
        return
    package_versions = build_system_toml["requires"]

    # Extracts contains fastai and fastcore versions from `pyproject.toml` if available.
    # If the package is specified but not the version (e.g. "fastai" instead of "fastai=2.4"), the default versions are the highest.
    fastai_packages = [pck for pck in package_versions if pck.startswith("fastai")]
    if len(fastai_packages) == 0:
        logger.warning("The repository does not have a fastai version specified in the `pyproject.toml`.")
    # fastai_version is an empty string if not specified
    else:
        fastai_version = str(fastai_packages[0]).partition("=")[2]
        if fastai_version != "" and version.Version(fastai_version) < version.Version(fastai_min_version):
            raise ImportError(
                "`from_pretrained_fastai` requires"
                f" fastai>={fastai_min_version} version but the model to load uses"
                f" {fastai_version} which is incompatible."
            )

    fastcore_packages = [pck for pck in package_versions if pck.startswith("fastcore")]
    if len(fastcore_packages) == 0:
        logger.warning("The repository does not have a fastcore version specified in the `pyproject.toml`.")
    # fastcore_version is an empty string if not specified
    else:
        fastcore_version = str(fastcore_packages[0]).partition("=")[2]
        if fastcore_version != "" and version.Version(fastcore_version) < version.Version(fastcore_min_version):
            raise ImportError(
                "`from_pretrained_fastai` requires"
                f" fastcore>={fastcore_min_version} version, but you are using fastcore"
                f" version {fastcore_version} which is incompatible."
            )


README_TEMPLATE = """---
tags:
- fastai
---

# Amazing!

🥳 Congratulations on hosting your fastai model on the Hugging Face Hub!

# Some next steps
1. Fill out this model card with more information (see the template below and the [documentation here](https://huggingface.co/docs/hub/model-repos))!

2. Create a demo in Gradio or Streamlit using 🤗 Spaces ([documentation here](https://huggingface.co/docs/hub/spaces)).

3. Join the fastai community on the [Fastai Discord](https://discord.com/invite/YKrxeNn)!

Greetings fellow fastlearner 🤝! Don't forget to delete this content from your model card.


---


# Model card

## Model description
More information needed

## Intended uses & limitations
More information needed

## Training and evaluation data
More information needed
"""

PYPROJECT_TEMPLATE = f"""[build-system]
requires = ["setuptools>=40.8.0", "wheel", "python={get_python_version()}", "fastai={get_fastai_version()}", "fastcore={get_fastcore_version()}"]
build-backend = "setuptools.build_meta:__legacy__"
"""


def _create_model_card(repo_dir: Path):
    """
    Creates a model card for the repository.

    Args:
        repo_dir (`Path`):
            Directory where model card is created.
    """
    readme_path = repo_dir / "README.md"

    if not readme_path.exists():
        with readme_path.open("w", encoding="utf-8") as f:
            f.write(README_TEMPLATE)


def _create_model_pyproject(repo_dir: Path):
    """
    Creates a `pyproject.toml` for the repository.

    Args:
        repo_dir (`Path`):
            Directory where `pyproject.toml` is created.
    """
    pyproject_path = repo_dir / "pyproject.toml"

    if not pyproject_path.exists():
        with pyproject_path.open("w", encoding="utf-8") as f:
            f.write(PYPROJECT_TEMPLATE)


def _save_pretrained_fastai(
    learner,
    save_directory: Union[str, Path],
    config: Optional[Dict[str, Any]] = None,
):
    """
    Saves a fastai learner to `save_directory` in pickle format using the default pickle protocol for the version of python used.

    Args:
        learner (`Learner`):
            The `fastai.Learner` you'd like to save.
        save_directory (`str` or `Path`):
            Specific directory in which you want to save the fastai learner.
        config (`dict`, *optional*):
            Configuration object. Will be uploaded as a .json file. Example: 'https://huggingface.co/espejelomar/fastai-pet-breeds-classification/blob/main/config.json'.

    <Tip>

    Raises the following error:

        - [`RuntimeError`](https://docs.python.org/3/library/exceptions.html#RuntimeError)
          if the config file provided is not a dictionary.

    </Tip>
    """
    _check_fastai_fastcore_versions()

    os.makedirs(save_directory, exist_ok=True)

    # if the user provides config then we update it with the fastai and fastcore versions in CONFIG_TEMPLATE.
    if config is not None:
        if not isinstance(config, dict):
            raise RuntimeError(f"Provided config should be a dict. Got: '{type(config)}'")
        path = os.path.join(save_directory, constants.CONFIG_NAME)
        with open(path, "w") as f:
            json.dump(config, f)

    _create_model_card(Path(save_directory))
    _create_model_pyproject(Path(save_directory))

    # learner.export saves the model in `self.path`.
    learner.path = Path(save_directory)
    os.makedirs(save_directory, exist_ok=True)
    try:
        learner.export(
            fname="model.pkl",
            pickle_protocol=DEFAULT_PROTOCOL,
        )
    except PicklingError:
        raise PicklingError(
            "You are using a lambda function, i.e., an anonymous function. `pickle`"
            " cannot pickle function objects and requires that all functions have"
            " names. One possible solution is to name the function."
        )


@validate_hf_hub_args
def from_pretrained_fastai(
    repo_id: str,
    revision: Optional[str] = None,
):
    """
    Load pretrained fastai model from the Hub or from a local directory.

    Args:
        repo_id (`str`):
            The location where the pickled fastai.Learner is. It can be either of the two:
                - Hosted on the Hugging Face Hub. E.g.: 'espejelomar/fatai-pet-breeds-classification' or 'distilgpt2'.
                  You can add a `revision` by appending `@` at the end of `repo_id`. E.g.: `dbmdz/bert-base-german-cased@main`.
                  Revision is the specific model version to use. Since we use a git-based system for storing models and other
                  artifacts on the Hugging Face Hub, it can be a branch name, a tag name, or a commit id.
                - Hosted locally. `repo_id` would be a directory containing the pickle and a pyproject.toml
                  indicating the fastai and fastcore versions used to build the `fastai.Learner`. E.g.: `./my_model_directory/`.
        revision (`str`, *optional*):
            Revision at which the repo's files are downloaded. See documentation of `snapshot_download`.

    Returns:
        The `fastai.Learner` model in the `repo_id` repo.
    """
    _check_fastai_fastcore_versions()

    # Load the `repo_id` repo.
    # `snapshot_download` returns the folder where the model was stored.
    # `cache_dir` will be the default '/root/.cache/huggingface/hub'
    if not os.path.isdir(repo_id):
        storage_folder = snapshot_download(
            repo_id=repo_id,
            revision=revision,
            library_name="fastai",
            library_version=get_fastai_version(),
        )
    else:
        storage_folder = repo_id

    _check_fastai_fastcore_pyproject_versions(storage_folder)

    from fastai.learner import load_learner  # type: ignore

    return load_learner(os.path.join(storage_folder, "model.pkl"))


@validate_hf_hub_args
def push_to_hub_fastai(
    learner,
    *,
    repo_id: str,
    commit_message: str = "Push FastAI model using huggingface_hub.",
    private: Optional[bool] = None,
    token: Optional[str] = None,
    config: Optional[dict] = None,
    branch: Optional[str] = None,
    create_pr: Optional[bool] = None,
    allow_patterns: Optional[Union[List[str], str]] = None,
    ignore_patterns: Optional[Union[List[str], str]] = None,
    delete_patterns: Optional[Union[List[str], str]] = None,
    api_endpoint: Optional[str] = None,
):
    """
    Upload learner checkpoint files to the Hub.

    Use `allow_patterns` and `ignore_patterns` to precisely filter which files should be pushed to the hub. Use
    `delete_patterns` to delete existing remote files in the same commit. See [`upload_folder`] reference for more
    details.

    Args:
        learner (`Learner`):
            The `fastai.Learner' you'd like to push to the Hub.
        repo_id (`str`):
            The repository id for your model in Hub in the format of "namespace/repo_name". The namespace can be your individual account or an organization to which you have write access (for example, 'stanfordnlp/stanza-de').
        commit_message (`str`, *optional*):
            Message to commit while pushing. Will default to :obj:`"add model"`.
        private (`bool`, *optional*):
            Whether or not the repository created should be private.
            If `None` (default), will default to been public except if the organization's default is private.
        token (`str`, *optional*):
            The Hugging Face account token to use as HTTP bearer authorization for remote files. If :obj:`None`, the token will be asked by a prompt.
        config (`dict`, *optional*):
            Configuration object to be saved alongside the model weights.
        branch (`str`, *optional*):
            The git branch on which to push the model. This defaults to
            the default branch as specified in your repository, which
            defaults to `"main"`.
        create_pr (`boolean`, *optional*):
            Whether or not to create a Pull Request from `branch` with that commit.
            Defaults to `False`.
        api_endpoint (`str`, *optional*):
            The API endpoint to use when pushing the model to the hub.
        allow_patterns (`List[str]` or `str`, *optional*):
            If provided, only files matching at least one pattern are pushed.
        ignore_patterns (`List[str]` or `str`, *optional*):
            If provided, files matching any of the patterns are not pushed.
        delete_patterns (`List[str]` or `str`, *optional*):
            If provided, remote files matching any of the patterns will be deleted from the repo.

    Returns:
        The url of the commit of your model in the given repository.

    <Tip>

    Raises the following error:

        - [`ValueError`](https://docs.python.org/3/library/exceptions.html#ValueError)
          if the user is not log on to the Hugging Face Hub.

    </Tip>
    """
    _check_fastai_fastcore_versions()
    api = HfApi(endpoint=api_endpoint)
    repo_id = api.create_repo(repo_id=repo_id, token=token, private=private, exist_ok=True).repo_id

    # Push the files to the repo in a single commit
    with SoftTemporaryDirectory() as tmp:
        saved_path = Path(tmp) / repo_id
        _save_pretrained_fastai(learner, saved_path, config=config)
        return api.upload_folder(
            repo_id=repo_id,
            token=token,
            folder_path=saved_path,
            commit_message=commit_message,
            revision=branch,
            create_pr=create_pr,
            allow_patterns=allow_patterns,
            ignore_patterns=ignore_patterns,
            delete_patterns=delete_patterns,
        )

# === NexusCore/openenv\Lib\site-packages\litellm\llms\codestral\completion\handler.py ===
# What is this?
## handler file for TextCompletionCodestral Integration - https://codestral.com/

import json
from functools import partial
from typing import Callable, List, Optional, Union

import httpx  # type: ignore

import litellm
from litellm.litellm_core_utils.litellm_logging import Logging as LiteLLMLogging
from litellm.litellm_core_utils.logging_utils import track_llm_api_timing
from litellm.litellm_core_utils.prompt_templates.factory import (
    custom_prompt,
    prompt_factory,
)
from litellm.llms.custom_httpx.http_handler import (
    AsyncHTTPHandler,
    get_async_httpx_client,
)
from litellm.types.utils import TextChoices
from litellm.utils import CustomStreamWrapper, TextCompletionResponse


class TextCompletionCodestralError(Exception):
    def __init__(
        self,
        status_code,
        message,
        request: Optional[httpx.Request] = None,
        response: Optional[httpx.Response] = None,
    ):
        self.status_code = status_code
        self.message = message
        if request is not None:
            self.request = request
        else:
            self.request = httpx.Request(
                method="POST",
                url="https://docs.codestral.com/user-guide/inference/rest_api",
            )
        if response is not None:
            self.response = response
        else:
            self.response = httpx.Response(
                status_code=status_code, request=self.request
            )
        super().__init__(
            self.message
        )  # Call the base class constructor with the parameters it needs


async def make_call(
    client: AsyncHTTPHandler,
    api_base: str,
    headers: dict,
    data: str,
    model: str,
    messages: list,
    logging_obj,
):
    response = await client.post(api_base, headers=headers, data=data, stream=True)

    if response.status_code != 200:
        raise TextCompletionCodestralError(
            status_code=response.status_code, message=response.text
        )

    completion_stream = response.aiter_lines()
    # LOGGING
    logging_obj.post_call(
        input=messages,
        api_key="",
        original_response=completion_stream,  # Pass the completion stream for logging
        additional_args={"complete_input_dict": data},
    )

    return completion_stream


class CodestralTextCompletion:
    def __init__(self) -> None:
        super().__init__()

    def _validate_environment(
        self,
        api_key: Optional[str],
        user_headers: dict,
    ) -> dict:
        if api_key is None:
            raise ValueError(
                "Missing CODESTRAL_API_Key - Please add CODESTRAL_API_Key to your environment variables"
            )
        headers = {
            "content-type": "application/json",
            "Authorization": "Bearer {}".format(api_key),
        }
        if user_headers is not None and isinstance(user_headers, dict):
            headers = {**headers, **user_headers}
        return headers

    def output_parser(self, generated_text: str):
        """
        Parse the output text to remove any special characters. In our current approach we just check for ChatML tokens.

        Initial issue that prompted this - https://github.com/BerriAI/litellm/issues/763
        """
        chat_template_tokens = [
            "<|assistant|>",
            "<|system|>",
            "<|user|>",
            "<s>",
            "</s>",
        ]
        for token in chat_template_tokens:
            if generated_text.strip().startswith(token):
                generated_text = generated_text.replace(token, "", 1)
            if generated_text.endswith(token):
                generated_text = generated_text[::-1].replace(token[::-1], "", 1)[::-1]
        return generated_text

    def process_text_completion_response(
        self,
        model: str,
        response: httpx.Response,
        model_response: TextCompletionResponse,
        stream: bool,
        logging_obj: LiteLLMLogging,
        optional_params: dict,
        api_key: str,
        data: Union[dict, str],
        messages: list,
        print_verbose,
        encoding,
    ) -> TextCompletionResponse:
        ## LOGGING
        logging_obj.post_call(
            input=messages,
            api_key=api_key,
            original_response=response.text,
            additional_args={"complete_input_dict": data},
        )
        print_verbose(f"codestral api: raw model_response: {response.text}")
        ## RESPONSE OBJECT
        if response.status_code != 200:
            raise TextCompletionCodestralError(
                message=str(response.text),
                status_code=response.status_code,
            )
        try:
            completion_response = response.json()
        except Exception:
            raise TextCompletionCodestralError(message=response.text, status_code=422)

        _original_choices = completion_response.get("choices", [])
        _choices: List[TextChoices] = []
        for choice in _original_choices:
            # This is what 1 choice looks like from codestral API
            # {
            #     "index": 0,
            #     "message": {
            #     "role": "assistant",
            #     "content": "\n assert is_odd(1)\n assert",
            #     "tool_calls": null
            #     },
            #     "finish_reason": "length",
            #     "logprobs": null
            #     }
            _finish_reason = None
            _index = 0
            _text = None
            _logprobs = None

            _choice_message = choice.get("message", {})
            _choice = litellm.utils.TextChoices(
                finish_reason=choice.get("finish_reason"),
                index=choice.get("index"),
                text=_choice_message.get("content"),
                logprobs=choice.get("logprobs"),
            )

            _choices.append(_choice)

        _response = litellm.TextCompletionResponse(
            id=completion_response.get("id"),
            choices=_choices,
            created=completion_response.get("created"),
            model=completion_response.get("model"),
            usage=completion_response.get("usage"),
            stream=False,
            object=completion_response.get("object"),
        )
        return _response

    def completion(
        self,
        model: str,
        messages: list,
        api_base: str,
        custom_prompt_dict: dict,
        model_response: TextCompletionResponse,
        print_verbose: Callable,
        encoding,
        api_key: str,
        logging_obj,
        optional_params: dict,
        timeout: Union[float, httpx.Timeout],
        acompletion=None,
        litellm_params=None,
        logger_fn=None,
        headers: dict = {},
    ) -> Union[TextCompletionResponse, CustomStreamWrapper]:
        headers = self._validate_environment(api_key, headers)

        if optional_params.pop("custom_endpoint", None) is True:
            completion_url = api_base
        else:
            completion_url = (
                api_base or "https://codestral.mistral.ai/v1/fim/completions"
            )

        if model in custom_prompt_dict:
            # check if the model has a registered custom prompt
            model_prompt_details = custom_prompt_dict[model]
            prompt = custom_prompt(
                role_dict=model_prompt_details["roles"],
                initial_prompt_value=model_prompt_details["initial_prompt_value"],
                final_prompt_value=model_prompt_details["final_prompt_value"],
                messages=messages,
            )
        else:
            prompt = prompt_factory(model=model, messages=messages)

        ## Load Config
        config = litellm.CodestralTextCompletionConfig.get_config()
        for k, v in config.items():
            if (
                k not in optional_params
            ):  # completion(top_k=3) > anthropic_config(top_k=3) <- allows for dynamic variables to be passed in
                optional_params[k] = v

        stream = optional_params.pop("stream", False)

        data = {
            "model": model,
            "prompt": prompt,
            **optional_params,
        }
        input_text = prompt
        ## LOGGING
        logging_obj.pre_call(
            input=input_text,
            api_key=api_key,
            additional_args={
                "complete_input_dict": data,
                "headers": headers,
                "api_base": completion_url,
                "acompletion": acompletion,
            },
        )
        ## COMPLETION CALL
        if acompletion is True:
            ### ASYNC STREAMING
            if stream is True:
                return self.async_streaming(
                    model=model,
                    messages=messages,
                    data=data,
                    api_base=completion_url,
                    model_response=model_response,
                    print_verbose=print_verbose,
                    encoding=encoding,
                    api_key=api_key,
                    logging_obj=logging_obj,
                    optional_params=optional_params,
                    litellm_params=litellm_params,
                    logger_fn=logger_fn,
                    headers=headers,
                    timeout=timeout,
                )  # type: ignore
            else:
                ### ASYNC COMPLETION
                return self.async_completion(
                    model=model,
                    messages=messages,
                    data=data,
                    api_base=completion_url,
                    model_response=model_response,
                    print_verbose=print_verbose,
                    encoding=encoding,
                    api_key=api_key,
                    logging_obj=logging_obj,
                    optional_params=optional_params,
                    stream=False,
                    litellm_params=litellm_params,
                    logger_fn=logger_fn,
                    headers=headers,
                    timeout=timeout,
                )  # type: ignore

        ### SYNC STREAMING
        if stream is True:
            response = litellm.module_level_client.post(
                completion_url,
                headers=headers,
                data=json.dumps(data),
                stream=stream,
            )
            _response = CustomStreamWrapper(
                response.iter_lines(),
                model,
                custom_llm_provider="codestral",
                logging_obj=logging_obj,
            )
            return _response
        ### SYNC COMPLETION
        else:
            response = litellm.module_level_client.post(
                url=completion_url,
                headers=headers,
                data=json.dumps(data),
            )
        return self.process_text_completion_response(
            model=model,
            response=response,
            model_response=model_response,
            stream=optional_params.get("stream", False),
            logging_obj=logging_obj,  # type: ignore
            optional_params=optional_params,
            api_key=api_key,
            data=data,
            messages=messages,
            print_verbose=print_verbose,
            encoding=encoding,
        )

    @track_llm_api_timing()
    async def async_completion(
        self,
        model: str,
        messages: list,
        api_base: str,
        model_response: TextCompletionResponse,
        print_verbose: Callable,
        encoding,
        api_key,
        logging_obj,
        stream,
        data: dict,
        optional_params: dict,
        timeout: Union[float, httpx.Timeout],
        litellm_params=None,
        logger_fn=None,
        headers={},
    ) -> TextCompletionResponse:
        async_handler = get_async_httpx_client(
            llm_provider=litellm.LlmProviders.TEXT_COMPLETION_CODESTRAL,
            params={"timeout": timeout},
        )
        try:
            response = await async_handler.post(
                api_base, headers=headers, data=json.dumps(data)
            )
        except httpx.HTTPStatusError as e:
            raise TextCompletionCodestralError(
                status_code=e.response.status_code,
                message="HTTPStatusError - {}".format(e.response.text),
            )
        except Exception as e:
            raise TextCompletionCodestralError(
                status_code=500, message="{}".format(str(e))
            )  # don't use verbose_logger.exception, if exception is raised
        return self.process_text_completion_response(
            model=model,
            response=response,
            model_response=model_response,
            stream=stream,
            logging_obj=logging_obj,
            api_key=api_key,
            data=data,
            messages=messages,
            print_verbose=print_verbose,
            optional_params=optional_params,
            encoding=encoding,
        )

    @track_llm_api_timing()
    async def async_streaming(
        self,
        model: str,
        messages: list,
        api_base: str,
        model_response: TextCompletionResponse,
        print_verbose: Callable,
        encoding,
        api_key,
        logging_obj,
        data: dict,
        timeout: Union[float, httpx.Timeout],
        optional_params=None,
        litellm_params=None,
        logger_fn=None,
        headers={},
    ) -> CustomStreamWrapper:
        data["stream"] = True

        streamwrapper = CustomStreamWrapper(
            completion_stream=None,
            make_call=partial(
                make_call,
                api_base=api_base,
                headers=headers,
                data=json.dumps(data),
                model=model,
                messages=messages,
                logging_obj=logging_obj,
            ),
            model=model,
            custom_llm_provider="text-completion-codestral",
            logging_obj=logging_obj,
        )
        return streamwrapper

    def embedding(self, *args, **kwargs):
        pass

# === NexusCore/openenv\Lib\site-packages\litellm\llms\huggingface\embedding\handler.py ===
import json
import os
from typing import Any, Callable, Dict, List, Literal, Optional, Union, get_args

import httpx

import litellm
from litellm.litellm_core_utils.litellm_logging import Logging as LiteLLMLoggingObj
from litellm.llms.custom_httpx.http_handler import (
    AsyncHTTPHandler,
    HTTPHandler,
    get_async_httpx_client,
)
from litellm.types.utils import EmbeddingResponse

from ...base import BaseLLM
from ..common_utils import HuggingFaceError
from .transformation import HuggingFaceEmbeddingConfig

config = HuggingFaceEmbeddingConfig()

HF_HUB_URL = "https://huggingface.co"

hf_tasks_embeddings = Literal[  # pipeline tags + hf tei endpoints - https://huggingface.github.io/text-embeddings-inference/#/
    "sentence-similarity", "feature-extraction", "rerank", "embed", "similarity"
]


def get_hf_task_embedding_for_model(
    model: str, task_type: Optional[str], api_base: str
) -> Optional[str]:
    if task_type is not None:
        if task_type in get_args(hf_tasks_embeddings):
            return task_type
        else:
            raise Exception(
                "Invalid task_type={}. Expected one of={}".format(
                    task_type, hf_tasks_embeddings
                )
            )
    http_client = HTTPHandler(concurrent_limit=1)

    model_info = http_client.get(url=f"{api_base}/api/models/{model}")

    model_info_dict = model_info.json()

    pipeline_tag: Optional[str] = model_info_dict.get("pipeline_tag", None)

    return pipeline_tag


async def async_get_hf_task_embedding_for_model(
    model: str, task_type: Optional[str], api_base: str
) -> Optional[str]:
    if task_type is not None:
        if task_type in get_args(hf_tasks_embeddings):
            return task_type
        else:
            raise Exception(
                "Invalid task_type={}. Expected one of={}".format(
                    task_type, hf_tasks_embeddings
                )
            )
    http_client = get_async_httpx_client(
        llm_provider=litellm.LlmProviders.HUGGINGFACE,
    )

    model_info = await http_client.get(url=f"{api_base}/api/models/{model}")

    model_info_dict = model_info.json()

    pipeline_tag: Optional[str] = model_info_dict.get("pipeline_tag", None)

    return pipeline_tag


class HuggingFaceEmbedding(BaseLLM):
    _client_session: Optional[httpx.Client] = None
    _aclient_session: Optional[httpx.AsyncClient] = None

    def __init__(self) -> None:
        super().__init__()

    def _transform_input_on_pipeline_tag(
        self, input: List, pipeline_tag: Optional[str]
    ) -> dict:
        if pipeline_tag is None:
            return {"inputs": input}
        if pipeline_tag == "sentence-similarity" or pipeline_tag == "similarity":
            if len(input) < 2:
                raise HuggingFaceError(
                    status_code=400,
                    message="sentence-similarity requires 2+ sentences",
                )
            return {"inputs": {"source_sentence": input[0], "sentences": input[1:]}}
        elif pipeline_tag == "rerank":
            if len(input) < 2:
                raise HuggingFaceError(
                    status_code=400,
                    message="reranker requires 2+ sentences",
                )
            return {"inputs": {"query": input[0], "texts": input[1:]}}
        return {"inputs": input}  # default to feature-extraction pipeline tag

    async def _async_transform_input(
        self,
        model: str,
        task_type: Optional[str],
        embed_url: str,
        input: List,
        optional_params: dict,
    ) -> dict:
        hf_task = await async_get_hf_task_embedding_for_model(
            model=model, task_type=task_type, api_base=HF_HUB_URL
        )

        data = self._transform_input_on_pipeline_tag(input=input, pipeline_tag=hf_task)

        if len(optional_params.keys()) > 0:
            data["options"] = optional_params

        return data

    def _process_optional_params(self, data: dict, optional_params: dict) -> dict:
        special_options_keys = config.get_special_options_params()
        special_parameters_keys = [
            "min_length",
            "max_length",
            "top_k",
            "top_p",
            "temperature",
            "repetition_penalty",
            "max_time",
        ]

        for k, v in optional_params.items():
            if k in special_options_keys:
                data.setdefault("options", {})
                data["options"][k] = v
            elif k in special_parameters_keys:
                data.setdefault("parameters", {})
                data["parameters"][k] = v
            else:
                data[k] = v

        return data

    def _transform_input(
        self,
        input: List,
        model: str,
        call_type: Literal["sync", "async"],
        optional_params: dict,
        embed_url: str,
    ) -> dict:
        data: Dict = {}

        ## TRANSFORMATION ##
        if "sentence-transformers" in model:
            if len(input) == 0:
                raise HuggingFaceError(
                    status_code=400,
                    message="sentence transformers requires 2+ sentences",
                )
            data = {"inputs": {"source_sentence": input[0], "sentences": input[1:]}}
        else:
            data = {"inputs": input}

            task_type = optional_params.pop("input_type", None)

            if call_type == "sync":
                hf_task = get_hf_task_embedding_for_model(
                    model=model, task_type=task_type, api_base=HF_HUB_URL
                )
            elif call_type == "async":
                return self._async_transform_input(
                    model=model, task_type=task_type, embed_url=embed_url, input=input
                )  # type: ignore

            data = self._transform_input_on_pipeline_tag(
                input=input, pipeline_tag=hf_task
            )

        if len(optional_params.keys()) > 0:
            data = self._process_optional_params(
                data=data, optional_params=optional_params
            )

        return data

    def _process_embedding_response(
        self,
        embeddings: dict,
        model_response: EmbeddingResponse,
        model: str,
        input: List,
        encoding: Any,
    ) -> EmbeddingResponse:
        output_data = []
        if "similarities" in embeddings:
            for idx, embedding in embeddings["similarities"]:
                output_data.append(
                    {
                        "object": "embedding",
                        "index": idx,
                        "embedding": embedding,  # flatten list returned from hf
                    }
                )
        else:
            for idx, embedding in enumerate(embeddings):
                if isinstance(embedding, float):
                    output_data.append(
                        {
                            "object": "embedding",
                            "index": idx,
                            "embedding": embedding,  # flatten list returned from hf
                        }
                    )
                elif isinstance(embedding, list) and isinstance(embedding[0], float):
                    output_data.append(
                        {
                            "object": "embedding",
                            "index": idx,
                            "embedding": embedding,  # flatten list returned from hf
                        }
                    )
                else:
                    output_data.append(
                        {
                            "object": "embedding",
                            "index": idx,
                            "embedding": embedding[0][
                                0
                            ],  # flatten list returned from hf
                        }
                    )
        model_response.object = "list"
        model_response.data = output_data
        model_response.model = model
        input_tokens = 0
        for text in input:
            input_tokens += len(encoding.encode(text))

        setattr(
            model_response,
            "usage",
            litellm.Usage(
                prompt_tokens=input_tokens,
                completion_tokens=input_tokens,
                total_tokens=input_tokens,
                prompt_tokens_details=None,
                completion_tokens_details=None,
            ),
        )
        return model_response

    async def aembedding(
        self,
        model: str,
        input: list,
        model_response: litellm.utils.EmbeddingResponse,
        timeout: Union[float, httpx.Timeout],
        logging_obj: LiteLLMLoggingObj,
        optional_params: dict,
        api_base: str,
        api_key: Optional[str],
        headers: dict,
        encoding: Callable,
        client: Optional[AsyncHTTPHandler] = None,
    ):
        ## TRANSFORMATION ##
        data = self._transform_input(
            input=input,
            model=model,
            call_type="sync",
            optional_params=optional_params,
            embed_url=api_base,
        )

        ## LOGGING
        logging_obj.pre_call(
            input=input,
            api_key=api_key,
            additional_args={
                "complete_input_dict": data,
                "headers": headers,
                "api_base": api_base,
            },
        )
        ## COMPLETION CALL
        if client is None:
            client = get_async_httpx_client(
                llm_provider=litellm.LlmProviders.HUGGINGFACE,
            )

        response = await client.post(api_base, headers=headers, data=json.dumps(data))

        ## LOGGING
        logging_obj.post_call(
            input=input,
            api_key=api_key,
            additional_args={"complete_input_dict": data},
            original_response=response,
        )

        embeddings = response.json()

        if "error" in embeddings:
            raise HuggingFaceError(status_code=500, message=embeddings["error"])

        ## PROCESS RESPONSE ##
        return self._process_embedding_response(
            embeddings=embeddings,
            model_response=model_response,
            model=model,
            input=input,
            encoding=encoding,
        )

    def embedding(
        self,
        model: str,
        input: list,
        model_response: EmbeddingResponse,
        optional_params: dict,
        litellm_params: dict,
        logging_obj: LiteLLMLoggingObj,
        encoding: Callable,
        api_key: Optional[str] = None,
        api_base: Optional[str] = None,
        timeout: Union[float, httpx.Timeout] = httpx.Timeout(None),
        aembedding: Optional[bool] = None,
        client: Optional[Union[HTTPHandler, AsyncHTTPHandler]] = None,
        headers={},
    ) -> EmbeddingResponse:
        super().embedding()
        headers = config.validate_environment(
            api_key=api_key,
            headers=headers,
            model=model,
            optional_params=optional_params,
            messages=[],
            litellm_params=litellm_params,
        )
        task_type = optional_params.get("input_type", None)
        task = get_hf_task_embedding_for_model(
            model=model, task_type=task_type, api_base=HF_HUB_URL
        )
        # print_verbose(f"{model}, {task}")
        embed_url = ""
        if "https" in model:
            embed_url = model
        elif api_base:
            embed_url = api_base
        elif "HF_API_BASE" in os.environ:
            embed_url = os.getenv("HF_API_BASE", "")
        elif "HUGGINGFACE_API_BASE" in os.environ:
            embed_url = os.getenv("HUGGINGFACE_API_BASE", "")
        else:
            embed_url = (
                f"https://router.huggingface.co/hf-inference/pipeline/{task}/{model}"
            )

        ## ROUTING ##
        if aembedding is True:
            return self.aembedding(
                input=input,
                model_response=model_response,
                timeout=timeout,
                logging_obj=logging_obj,
                headers=headers,
                api_base=embed_url,  # type: ignore
                api_key=api_key,
                client=client if isinstance(client, AsyncHTTPHandler) else None,
                model=model,
                optional_params=optional_params,
                encoding=encoding,
            )

        ## TRANSFORMATION ##

        data = self._transform_input(
            input=input,
            model=model,
            call_type="sync",
            optional_params=optional_params,
            embed_url=embed_url,
        )

        ## LOGGING
        logging_obj.pre_call(
            input=input,
            api_key=api_key,
            additional_args={
                "complete_input_dict": data,
                "headers": headers,
                "api_base": embed_url,
            },
        )
        ## COMPLETION CALL
        if client is None or not isinstance(client, HTTPHandler):
            client = HTTPHandler(concurrent_limit=1)
        response = client.post(embed_url, headers=headers, data=json.dumps(data))

        ## LOGGING
        logging_obj.post_call(
            input=input,
            api_key=api_key,
            additional_args={"complete_input_dict": data},
            original_response=response,
        )

        embeddings = response.json()

        if "error" in embeddings:
            raise HuggingFaceError(status_code=500, message=embeddings["error"])

        ## PROCESS RESPONSE ##
        return self._process_embedding_response(
            embeddings=embeddings,
            model_response=model_response,
            model=model,
            input=input,
            encoding=encoding,
        )

# === NexusCore/openenv\Lib\site-packages\fontTools\misc\arrayTools.py ===
"""Routines for calculating bounding boxes, point in rectangle calculations and
so on.
"""

from fontTools.misc.roundTools import otRound
from fontTools.misc.vector import Vector as _Vector
import math
import warnings


def calcBounds(array):
    """Calculate the bounding rectangle of a 2D points array.

    Args:
        array: A sequence of 2D tuples.

    Returns:
        A four-item tuple representing the bounding rectangle ``(xMin, yMin, xMax, yMax)``.
    """
    if not array:
        return 0, 0, 0, 0
    xs = [x for x, y in array]
    ys = [y for x, y in array]
    return min(xs), min(ys), max(xs), max(ys)


def calcIntBounds(array, round=otRound):
    """Calculate the integer bounding rectangle of a 2D points array.

    Values are rounded to closest integer towards ``+Infinity`` using the
    :func:`fontTools.misc.fixedTools.otRound` function by default, unless
    an optional ``round`` function is passed.

    Args:
        array: A sequence of 2D tuples.
        round: A rounding function of type ``f(x: float) -> int``.

    Returns:
        A four-item tuple of integers representing the bounding rectangle:
        ``(xMin, yMin, xMax, yMax)``.
    """
    return tuple(round(v) for v in calcBounds(array))


def updateBounds(bounds, p, min=min, max=max):
    """Add a point to a bounding rectangle.

    Args:
        bounds: A bounding rectangle expressed as a tuple
            ``(xMin, yMin, xMax, yMax), or None``.
        p: A 2D tuple representing a point.
        min,max: functions to compute the minimum and maximum.

    Returns:
        The updated bounding rectangle ``(xMin, yMin, xMax, yMax)``.
    """
    (x, y) = p
    if bounds is None:
        return x, y, x, y
    xMin, yMin, xMax, yMax = bounds
    return min(xMin, x), min(yMin, y), max(xMax, x), max(yMax, y)


def pointInRect(p, rect):
    """Test if a point is inside a bounding rectangle.

    Args:
        p: A 2D tuple representing a point.
        rect: A bounding rectangle expressed as a tuple
            ``(xMin, yMin, xMax, yMax)``.

    Returns:
        ``True`` if the point is inside the rectangle, ``False`` otherwise.
    """
    (x, y) = p
    xMin, yMin, xMax, yMax = rect
    return (xMin <= x <= xMax) and (yMin <= y <= yMax)


def pointsInRect(array, rect):
    """Determine which points are inside a bounding rectangle.

    Args:
        array: A sequence of 2D tuples.
        rect: A bounding rectangle expressed as a tuple
            ``(xMin, yMin, xMax, yMax)``.

    Returns:
        A list containing the points inside the rectangle.
    """
    if len(array) < 1:
        return []
    xMin, yMin, xMax, yMax = rect
    return [(xMin <= x <= xMax) and (yMin <= y <= yMax) for x, y in array]


def vectorLength(vector):
    """Calculate the length of the given vector.

    Args:
        vector: A 2D tuple.

    Returns:
        The Euclidean length of the vector.
    """
    x, y = vector
    return math.sqrt(x**2 + y**2)


def asInt16(array):
    """Round a list of floats to 16-bit signed integers.

    Args:
        array: List of float values.

    Returns:
        A list of rounded integers.
    """
    return [int(math.floor(i + 0.5)) for i in array]


def normRect(rect):
    """Normalize a bounding box rectangle.

    This function "turns the rectangle the right way up", so that the following
    holds::

        xMin <= xMax and yMin <= yMax

    Args:
        rect: A bounding rectangle expressed as a tuple
            ``(xMin, yMin, xMax, yMax)``.

    Returns:
        A normalized bounding rectangle.
    """
    (xMin, yMin, xMax, yMax) = rect
    return min(xMin, xMax), min(yMin, yMax), max(xMin, xMax), max(yMin, yMax)


def scaleRect(rect, x, y):
    """Scale a bounding box rectangle.

    Args:
        rect: A bounding rectangle expressed as a tuple
            ``(xMin, yMin, xMax, yMax)``.
        x: Factor to scale the rectangle along the X axis.
        Y: Factor to scale the rectangle along the Y axis.

    Returns:
        A scaled bounding rectangle.
    """
    (xMin, yMin, xMax, yMax) = rect
    return xMin * x, yMin * y, xMax * x, yMax * y


def offsetRect(rect, dx, dy):
    """Offset a bounding box rectangle.

    Args:
        rect: A bounding rectangle expressed as a tuple
            ``(xMin, yMin, xMax, yMax)``.
        dx: Amount to offset the rectangle along the X axis.
        dY: Amount to offset the rectangle along the Y axis.

    Returns:
        An offset bounding rectangle.
    """
    (xMin, yMin, xMax, yMax) = rect
    return xMin + dx, yMin + dy, xMax + dx, yMax + dy


def insetRect(rect, dx, dy):
    """Inset a bounding box rectangle on all sides.

    Args:
        rect: A bounding rectangle expressed as a tuple
            ``(xMin, yMin, xMax, yMax)``.
        dx: Amount to inset the rectangle along the X axis.
        dY: Amount to inset the rectangle along the Y axis.

    Returns:
        An inset bounding rectangle.
    """
    (xMin, yMin, xMax, yMax) = rect
    return xMin + dx, yMin + dy, xMax - dx, yMax - dy


def sectRect(rect1, rect2):
    """Test for rectangle-rectangle intersection.

    Args:
        rect1: First bounding rectangle, expressed as tuples
            ``(xMin, yMin, xMax, yMax)``.
        rect2: Second bounding rectangle.

    Returns:
        A boolean and a rectangle.
        If the input rectangles intersect, returns ``True`` and the intersecting
        rectangle. Returns ``False`` and ``(0, 0, 0, 0)`` if the input
        rectangles don't intersect.
    """
    (xMin1, yMin1, xMax1, yMax1) = rect1
    (xMin2, yMin2, xMax2, yMax2) = rect2
    xMin, yMin, xMax, yMax = (
        max(xMin1, xMin2),
        max(yMin1, yMin2),
        min(xMax1, xMax2),
        min(yMax1, yMax2),
    )
    if xMin >= xMax or yMin >= yMax:
        return False, (0, 0, 0, 0)
    return True, (xMin, yMin, xMax, yMax)


def unionRect(rect1, rect2):
    """Determine union of bounding rectangles.

    Args:
        rect1: First bounding rectangle, expressed as tuples
            ``(xMin, yMin, xMax, yMax)``.
        rect2: Second bounding rectangle.

    Returns:
        The smallest rectangle in which both input rectangles are fully
        enclosed.
    """
    (xMin1, yMin1, xMax1, yMax1) = rect1
    (xMin2, yMin2, xMax2, yMax2) = rect2
    xMin, yMin, xMax, yMax = (
        min(xMin1, xMin2),
        min(yMin1, yMin2),
        max(xMax1, xMax2),
        max(yMax1, yMax2),
    )
    return (xMin, yMin, xMax, yMax)


def rectCenter(rect):
    """Determine rectangle center.

    Args:
        rect: Bounding rectangle, expressed as tuples
            ``(xMin, yMin, xMax, yMax)``.

    Returns:
        A 2D tuple representing the point at the center of the rectangle.
    """
    (xMin, yMin, xMax, yMax) = rect
    return (xMin + xMax) / 2, (yMin + yMax) / 2


def rectArea(rect):
    """Determine rectangle area.

    Args:
        rect: Bounding rectangle, expressed as tuples
            ``(xMin, yMin, xMax, yMax)``.

    Returns:
        The area of the rectangle.
    """
    (xMin, yMin, xMax, yMax) = rect
    return (yMax - yMin) * (xMax - xMin)


def intRect(rect):
    """Round a rectangle to integer values.

    Guarantees that the resulting rectangle is NOT smaller than the original.

    Args:
        rect: Bounding rectangle, expressed as tuples
            ``(xMin, yMin, xMax, yMax)``.

    Returns:
        A rounded bounding rectangle.
    """
    (xMin, yMin, xMax, yMax) = rect
    xMin = int(math.floor(xMin))
    yMin = int(math.floor(yMin))
    xMax = int(math.ceil(xMax))
    yMax = int(math.ceil(yMax))
    return (xMin, yMin, xMax, yMax)


def quantizeRect(rect, factor=1):
    """
    >>> bounds = (72.3, -218.4, 1201.3, 919.1)
    >>> quantizeRect(bounds)
    (72, -219, 1202, 920)
    >>> quantizeRect(bounds, factor=10)
    (70, -220, 1210, 920)
    >>> quantizeRect(bounds, factor=100)
    (0, -300, 1300, 1000)
    """
    if factor < 1:
        raise ValueError(f"Expected quantization factor >= 1, found: {factor!r}")
    xMin, yMin, xMax, yMax = normRect(rect)
    return (
        int(math.floor(xMin / factor) * factor),
        int(math.floor(yMin / factor) * factor),
        int(math.ceil(xMax / factor) * factor),
        int(math.ceil(yMax / factor) * factor),
    )


class Vector(_Vector):
    def __init__(self, *args, **kwargs):
        warnings.warn(
            "fontTools.misc.arrayTools.Vector has been deprecated, please use "
            "fontTools.misc.vector.Vector instead.",
            DeprecationWarning,
        )


def pairwise(iterable, reverse=False):
    """Iterate over current and next items in iterable.

    Args:
        iterable: An iterable
        reverse: If true, iterate in reverse order.

    Returns:
        A iterable yielding two elements per iteration.

    Example:

        >>> tuple(pairwise([]))
        ()
        >>> tuple(pairwise([], reverse=True))
        ()
        >>> tuple(pairwise([0]))
        ((0, 0),)
        >>> tuple(pairwise([0], reverse=True))
        ((0, 0),)
        >>> tuple(pairwise([0, 1]))
        ((0, 1), (1, 0))
        >>> tuple(pairwise([0, 1], reverse=True))
        ((1, 0), (0, 1))
        >>> tuple(pairwise([0, 1, 2]))
        ((0, 1), (1, 2), (2, 0))
        >>> tuple(pairwise([0, 1, 2], reverse=True))
        ((2, 1), (1, 0), (0, 2))
        >>> tuple(pairwise(['a', 'b', 'c', 'd']))
        (('a', 'b'), ('b', 'c'), ('c', 'd'), ('d', 'a'))
        >>> tuple(pairwise(['a', 'b', 'c', 'd'], reverse=True))
        (('d', 'c'), ('c', 'b'), ('b', 'a'), ('a', 'd'))
    """
    if not iterable:
        return
    if reverse:
        it = reversed(iterable)
    else:
        it = iter(iterable)
    first = next(it, None)
    a = first
    for b in it:
        yield (a, b)
        a = b
    yield (a, first)


def _test():
    """
    >>> import math
    >>> calcBounds([])
    (0, 0, 0, 0)
    >>> calcBounds([(0, 40), (0, 100), (50, 50), (80, 10)])
    (0, 10, 80, 100)
    >>> updateBounds((0, 0, 0, 0), (100, 100))
    (0, 0, 100, 100)
    >>> pointInRect((50, 50), (0, 0, 100, 100))
    True
    >>> pointInRect((0, 0), (0, 0, 100, 100))
    True
    >>> pointInRect((100, 100), (0, 0, 100, 100))
    True
    >>> not pointInRect((101, 100), (0, 0, 100, 100))
    True
    >>> list(pointsInRect([(50, 50), (0, 0), (100, 100), (101, 100)], (0, 0, 100, 100)))
    [True, True, True, False]
    >>> vectorLength((3, 4))
    5.0
    >>> vectorLength((1, 1)) == math.sqrt(2)
    True
    >>> list(asInt16([0, 0.1, 0.5, 0.9]))
    [0, 0, 1, 1]
    >>> normRect((0, 10, 100, 200))
    (0, 10, 100, 200)
    >>> normRect((100, 200, 0, 10))
    (0, 10, 100, 200)
    >>> scaleRect((10, 20, 50, 150), 1.5, 2)
    (15.0, 40, 75.0, 300)
    >>> offsetRect((10, 20, 30, 40), 5, 6)
    (15, 26, 35, 46)
    >>> insetRect((10, 20, 50, 60), 5, 10)
    (15, 30, 45, 50)
    >>> insetRect((10, 20, 50, 60), -5, -10)
    (5, 10, 55, 70)
    >>> intersects, rect = sectRect((0, 10, 20, 30), (0, 40, 20, 50))
    >>> not intersects
    True
    >>> intersects, rect = sectRect((0, 10, 20, 30), (5, 20, 35, 50))
    >>> intersects
    1
    >>> rect
    (5, 20, 20, 30)
    >>> unionRect((0, 10, 20, 30), (0, 40, 20, 50))
    (0, 10, 20, 50)
    >>> rectCenter((0, 0, 100, 200))
    (50.0, 100.0)
    >>> rectCenter((0, 0, 100, 199.0))
    (50.0, 99.5)
    >>> intRect((0.9, 2.9, 3.1, 4.1))
    (0, 2, 4, 5)
    """


if __name__ == "__main__":
    import sys
    import doctest

    sys.exit(doctest.testmod().failed)

# === NexusCore/openenv\Lib\site-packages\IPython\external\qt_loaders.py ===
"""
This module contains factory functions that attempt
to return Qt submodules from the various python Qt bindings.

It also protects against double-importing Qt with different
bindings, which is unstable and likely to crash

This is used primarily by qt and qt_for_kernel, and shouldn't
be accessed directly from the outside
"""

import importlib.abc
import sys
import os
import types
from functools import partial, lru_cache
import operator

# ### Available APIs.
# Qt6
QT_API_PYQT6 = "pyqt6"
QT_API_PYSIDE6 = "pyside6"

# Qt5
QT_API_PYQT5 = 'pyqt5'
QT_API_PYSIDE2 = 'pyside2'

# Qt4
# NOTE: Here for legacy matplotlib compatibility, but not really supported on the IPython side.
QT_API_PYQT = "pyqt"  # Force version 2
QT_API_PYQTv1 = "pyqtv1"  # Force version 2
QT_API_PYSIDE = "pyside"

QT_API_PYQT_DEFAULT = "pyqtdefault"  # use system default for version 1 vs. 2

api_to_module = {
    # Qt6
    QT_API_PYQT6: "PyQt6",
    QT_API_PYSIDE6: "PySide6",
    # Qt5
    QT_API_PYQT5: "PyQt5",
    QT_API_PYSIDE2: "PySide2",
    # Qt4
    QT_API_PYSIDE: "PySide",
    QT_API_PYQT: "PyQt4",
    QT_API_PYQTv1: "PyQt4",
    # default
    QT_API_PYQT_DEFAULT: "PyQt6",
}


class ImportDenier(importlib.abc.MetaPathFinder):
    """Import Hook that will guard against bad Qt imports
    once IPython commits to a specific binding
    """

    def __init__(self):
        self.__forbidden = set()

    def forbid(self, module_name):
        sys.modules.pop(module_name, None)
        self.__forbidden.add(module_name)

    def find_spec(self, fullname, path, target=None):
        if path:
            return
        if fullname in self.__forbidden:
            raise ImportError(
                """
    Importing %s disabled by IPython, which has
    already imported an Incompatible QT Binding: %s
    """
                % (fullname, loaded_api())
            )


ID = ImportDenier()
sys.meta_path.insert(0, ID)


def commit_api(api):
    """Commit to a particular API, and trigger ImportErrors on subsequent
    dangerous imports"""
    modules = set(api_to_module.values())

    modules.remove(api_to_module[api])
    for mod in modules:
        ID.forbid(mod)


def loaded_api():
    """Return which API is loaded, if any

    If this returns anything besides None,
    importing any other Qt binding is unsafe.

    Returns
    -------
    None, 'pyside6', 'pyqt6', 'pyside2', 'pyside', 'pyqt', 'pyqt5', 'pyqtv1'
    """
    if sys.modules.get("PyQt6.QtCore"):
        return QT_API_PYQT6
    elif sys.modules.get("PySide6.QtCore"):
        return QT_API_PYSIDE6
    elif sys.modules.get("PyQt5.QtCore"):
        return QT_API_PYQT5
    elif sys.modules.get("PySide2.QtCore"):
        return QT_API_PYSIDE2
    elif sys.modules.get("PyQt4.QtCore"):
        if qtapi_version() == 2:
            return QT_API_PYQT
        else:
            return QT_API_PYQTv1
    elif sys.modules.get("PySide.QtCore"):
        return QT_API_PYSIDE

    return None


def has_binding(api):
    """Safely check for PyQt4/5, PySide or PySide2, without importing submodules

    Parameters
    ----------
    api : str [ 'pyqtv1' | 'pyqt' | 'pyqt5' | 'pyside' | 'pyside2' | 'pyqtdefault']
        Which module to check for

    Returns
    -------
    True if the relevant module appears to be importable
    """
    module_name = api_to_module[api]
    from importlib.util import find_spec

    required = ['QtCore', 'QtGui', 'QtSvg']
    if api in (QT_API_PYQT5, QT_API_PYSIDE2, QT_API_PYQT6, QT_API_PYSIDE6):
        # QT5 requires QtWidgets too
        required.append('QtWidgets')

    for submod in required:
        try:
            spec = find_spec('%s.%s' % (module_name, submod))
        except ImportError:
            # Package (e.g. PyQt5) not found
            return False
        else:
            if spec is None:
                # Submodule (e.g. PyQt5.QtCore) not found
                return False

    if api == QT_API_PYSIDE:
        # We can also safely check PySide version
        import PySide

        return PySide.__version_info__ >= (1, 0, 3)

    return True


def qtapi_version():
    """Return which QString API has been set, if any

    Returns
    -------
    The QString API version (1 or 2), or None if not set
    """
    try:
        import sip
    except ImportError:
        # as of PyQt5 5.11, sip is no longer available as a top-level
        # module and needs to be imported from the PyQt5 namespace
        try:
            from PyQt5 import sip
        except ImportError:
            return
    try:
        return sip.getapi('QString')
    except ValueError:
        return


def can_import(api):
    """Safely query whether an API is importable, without importing it"""
    if not has_binding(api):
        return False

    current = loaded_api()
    if api == QT_API_PYQT_DEFAULT:
        return current in [QT_API_PYQT6, None]
    else:
        return current in [api, None]


def import_pyqt4(version=2):
    """
    Import PyQt4

    Parameters
    ----------
    version : 1, 2, or None
        Which QString/QVariant API to use. Set to None to use the system
        default
    ImportErrors raised within this function are non-recoverable
    """
    # The new-style string API (version=2) automatically
    # converts QStrings to Unicode Python strings. Also, automatically unpacks
    # QVariants to their underlying objects.
    import sip

    if version is not None:
        sip.setapi('QString', version)
        sip.setapi('QVariant', version)

    from PyQt4 import QtGui, QtCore, QtSvg

    if QtCore.PYQT_VERSION < 0x040700:
        raise ImportError("IPython requires PyQt4 >= 4.7, found %s" %
                          QtCore.PYQT_VERSION_STR)

    # Alias PyQt-specific functions for PySide compatibility.
    QtCore.Signal = QtCore.pyqtSignal
    QtCore.Slot = QtCore.pyqtSlot

    # query for the API version (in case version == None)
    version = sip.getapi('QString')
    api = QT_API_PYQTv1 if version == 1 else QT_API_PYQT
    return QtCore, QtGui, QtSvg, api


def import_pyqt5():
    """
    Import PyQt5

    ImportErrors raised within this function are non-recoverable
    """

    from PyQt5 import QtCore, QtSvg, QtWidgets, QtGui

    # Alias PyQt-specific functions for PySide compatibility.
    QtCore.Signal = QtCore.pyqtSignal
    QtCore.Slot = QtCore.pyqtSlot

    # Join QtGui and QtWidgets for Qt4 compatibility.
    QtGuiCompat = types.ModuleType('QtGuiCompat')
    QtGuiCompat.__dict__.update(QtGui.__dict__)
    QtGuiCompat.__dict__.update(QtWidgets.__dict__)

    api = QT_API_PYQT5
    return QtCore, QtGuiCompat, QtSvg, api


def import_pyqt6():
    """
    Import PyQt6

    ImportErrors raised within this function are non-recoverable
    """

    from PyQt6 import QtCore, QtSvg, QtWidgets, QtGui

    # Alias PyQt-specific functions for PySide compatibility.
    QtCore.Signal = QtCore.pyqtSignal
    QtCore.Slot = QtCore.pyqtSlot

    # Join QtGui and QtWidgets for Qt4 compatibility.
    QtGuiCompat = types.ModuleType("QtGuiCompat")
    QtGuiCompat.__dict__.update(QtGui.__dict__)
    QtGuiCompat.__dict__.update(QtWidgets.__dict__)

    api = QT_API_PYQT6
    return QtCore, QtGuiCompat, QtSvg, api


def import_pyside():
    """
    Import PySide

    ImportErrors raised within this function are non-recoverable
    """
    from PySide import QtGui, QtCore, QtSvg
    return QtCore, QtGui, QtSvg, QT_API_PYSIDE

def import_pyside2():
    """
    Import PySide2

    ImportErrors raised within this function are non-recoverable
    """
    from PySide2 import QtGui, QtCore, QtSvg, QtWidgets, QtPrintSupport

    # Join QtGui and QtWidgets for Qt4 compatibility.
    QtGuiCompat = types.ModuleType('QtGuiCompat')
    QtGuiCompat.__dict__.update(QtGui.__dict__)
    QtGuiCompat.__dict__.update(QtWidgets.__dict__)
    QtGuiCompat.__dict__.update(QtPrintSupport.__dict__)

    return QtCore, QtGuiCompat, QtSvg, QT_API_PYSIDE2


def import_pyside6():
    """
    Import PySide6

    ImportErrors raised within this function are non-recoverable
    """

    def get_attrs(module):
        return {
            name: getattr(module, name)
            for name in dir(module)
            if not name.startswith("_")
        }

    from PySide6 import QtGui, QtCore, QtSvg, QtWidgets, QtPrintSupport

    # Join QtGui and QtWidgets for Qt4 compatibility.
    QtGuiCompat = types.ModuleType("QtGuiCompat")
    QtGuiCompat.__dict__.update(QtGui.__dict__)
    if QtCore.__version_info__ < (6, 7):
        QtGuiCompat.__dict__.update(QtWidgets.__dict__)
        QtGuiCompat.__dict__.update(QtPrintSupport.__dict__)
    else:
        QtGuiCompat.__dict__.update(get_attrs(QtWidgets))
        QtGuiCompat.__dict__.update(get_attrs(QtPrintSupport))

    return QtCore, QtGuiCompat, QtSvg, QT_API_PYSIDE6


def load_qt(api_options):
    """
    Attempt to import Qt, given a preference list
    of permissible bindings

    It is safe to call this function multiple times.

    Parameters
    ----------
    api_options : List of strings
        The order of APIs to try. Valid items are 'pyside', 'pyside2',
        'pyqt', 'pyqt5', 'pyqtv1' and 'pyqtdefault'

    Returns
    -------
    A tuple of QtCore, QtGui, QtSvg, QT_API
    The first three are the Qt modules. The last is the
    string indicating which module was loaded.

    Raises
    ------
    ImportError, if it isn't possible to import any requested
    bindings (either because they aren't installed, or because
    an incompatible library has already been installed)
    """
    loaders = {
        # Qt6
        QT_API_PYQT6: import_pyqt6,
        QT_API_PYSIDE6: import_pyside6,
        # Qt5
        QT_API_PYQT5: import_pyqt5,
        QT_API_PYSIDE2: import_pyside2,
        # Qt4
        QT_API_PYSIDE: import_pyside,
        QT_API_PYQT: import_pyqt4,
        QT_API_PYQTv1: partial(import_pyqt4, version=1),
        # default
        QT_API_PYQT_DEFAULT: import_pyqt6,
    }

    for api in api_options:

        if api not in loaders:
            raise RuntimeError(
                "Invalid Qt API %r, valid values are: %s" %
                (api, ", ".join(["%r" % k for k in loaders.keys()])))

        if not can_import(api):
            continue

        #cannot safely recover from an ImportError during this
        result = loaders[api]()
        api = result[-1]  # changed if api = QT_API_PYQT_DEFAULT
        commit_api(api)
        return result
    else:
        # Clear the environment variable since it doesn't work.
        if "QT_API" in os.environ:
            del os.environ["QT_API"]

        raise ImportError(
            """
    Could not load requested Qt binding. Please ensure that
    PyQt4 >= 4.7, PyQt5, PyQt6, PySide >= 1.0.3, PySide2, or
    PySide6 is available, and only one is imported per session.

    Currently-imported Qt library:                              %r
    PyQt5 available (requires QtCore, QtGui, QtSvg, QtWidgets): %s
    PyQt6 available (requires QtCore, QtGui, QtSvg, QtWidgets): %s
    PySide2 installed:                                          %s
    PySide6 installed:                                          %s
    Tried to load:                                              %r
    """
            % (
                loaded_api(),
                has_binding(QT_API_PYQT5),
                has_binding(QT_API_PYQT6),
                has_binding(QT_API_PYSIDE2),
                has_binding(QT_API_PYSIDE6),
                api_options,
            )
        )


def enum_factory(QT_API, QtCore):
    """Construct an enum helper to account for PyQt5 <-> PyQt6 changes."""

    @lru_cache(None)
    def _enum(name):
        # foo.bar.Enum.Entry (PyQt6) <=> foo.bar.Entry (non-PyQt6).
        return operator.attrgetter(
            name if QT_API == QT_API_PYQT6 else name.rpartition(".")[0]
        )(sys.modules[QtCore.__package__])

    return _enum

# === NexusCore/openenv\Lib\site-packages\tornado\queues.py ===
# Copyright 2015 The Tornado Authors
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

"""Asynchronous queues for coroutines. These classes are very similar
to those provided in the standard library's `asyncio package
<https://docs.python.org/3/library/asyncio-queue.html>`_.

.. warning::

   Unlike the standard library's `queue` module, the classes defined here
   are *not* thread-safe. To use these queues from another thread,
   use `.IOLoop.add_callback` to transfer control to the `.IOLoop` thread
   before calling any queue methods.

"""

import collections
import datetime
import heapq

from tornado import gen, ioloop
from tornado.concurrent import Future, future_set_result_unless_cancelled
from tornado.locks import Event

from typing import Union, TypeVar, Generic, Awaitable, Optional
import typing

if typing.TYPE_CHECKING:
    from typing import Deque, Tuple, Any  # noqa: F401

_T = TypeVar("_T")

__all__ = ["Queue", "PriorityQueue", "LifoQueue", "QueueFull", "QueueEmpty"]


class QueueEmpty(Exception):
    """Raised by `.Queue.get_nowait` when the queue has no items."""

    pass


class QueueFull(Exception):
    """Raised by `.Queue.put_nowait` when a queue is at its maximum size."""

    pass


def _set_timeout(
    future: Future, timeout: Union[None, float, datetime.timedelta]
) -> None:
    if timeout:

        def on_timeout() -> None:
            if not future.done():
                future.set_exception(gen.TimeoutError())

        io_loop = ioloop.IOLoop.current()
        timeout_handle = io_loop.add_timeout(timeout, on_timeout)
        future.add_done_callback(lambda _: io_loop.remove_timeout(timeout_handle))


class _QueueIterator(Generic[_T]):
    def __init__(self, q: "Queue[_T]") -> None:
        self.q = q

    def __anext__(self) -> Awaitable[_T]:
        return self.q.get()


class Queue(Generic[_T]):
    """Coordinate producer and consumer coroutines.

    If maxsize is 0 (the default) the queue size is unbounded.

    .. testcode::

        import asyncio
        from tornado.ioloop import IOLoop
        from tornado.queues import Queue

        q = Queue(maxsize=2)

        async def consumer():
            async for item in q:
                try:
                    print('Doing work on %s' % item)
                    await asyncio.sleep(0.01)
                finally:
                    q.task_done()

        async def producer():
            for item in range(5):
                await q.put(item)
                print('Put %s' % item)

        async def main():
            # Start consumer without waiting (since it never finishes).
            IOLoop.current().spawn_callback(consumer)
            await producer()     # Wait for producer to put all tasks.
            await q.join()       # Wait for consumer to finish all tasks.
            print('Done')

        asyncio.run(main())

    .. testoutput::

        Put 0
        Put 1
        Doing work on 0
        Put 2
        Doing work on 1
        Put 3
        Doing work on 2
        Put 4
        Doing work on 3
        Doing work on 4
        Done


    In versions of Python without native coroutines (before 3.5),
    ``consumer()`` could be written as::

        @gen.coroutine
        def consumer():
            while True:
                item = yield q.get()
                try:
                    print('Doing work on %s' % item)
                    yield gen.sleep(0.01)
                finally:
                    q.task_done()

    .. versionchanged:: 4.3
       Added ``async for`` support in Python 3.5.

    """

    # Exact type depends on subclass. Could be another generic
    # parameter and use protocols to be more precise here.
    _queue = None  # type: Any

    def __init__(self, maxsize: int = 0) -> None:
        if maxsize is None:
            raise TypeError("maxsize can't be None")

        if maxsize < 0:
            raise ValueError("maxsize can't be negative")

        self._maxsize = maxsize
        self._init()
        self._getters = collections.deque([])  # type: Deque[Future[_T]]
        self._putters = collections.deque([])  # type: Deque[Tuple[_T, Future[None]]]
        self._unfinished_tasks = 0
        self._finished = Event()
        self._finished.set()

    @property
    def maxsize(self) -> int:
        """Number of items allowed in the queue."""
        return self._maxsize

    def qsize(self) -> int:
        """Number of items in the queue."""
        return len(self._queue)

    def empty(self) -> bool:
        return not self._queue

    def full(self) -> bool:
        if self.maxsize == 0:
            return False
        else:
            return self.qsize() >= self.maxsize

    def put(
        self, item: _T, timeout: Optional[Union[float, datetime.timedelta]] = None
    ) -> "Future[None]":
        """Put an item into the queue, perhaps waiting until there is room.

        Returns a Future, which raises `tornado.util.TimeoutError` after a
        timeout.

        ``timeout`` may be a number denoting a time (on the same
        scale as `tornado.ioloop.IOLoop.time`, normally `time.time`), or a
        `datetime.timedelta` object for a deadline relative to the
        current time.
        """
        future = Future()  # type: Future[None]
        try:
            self.put_nowait(item)
        except QueueFull:
            self._putters.append((item, future))
            _set_timeout(future, timeout)
        else:
            future.set_result(None)
        return future

    def put_nowait(self, item: _T) -> None:
        """Put an item into the queue without blocking.

        If no free slot is immediately available, raise `QueueFull`.
        """
        self._consume_expired()
        if self._getters:
            assert self.empty(), "queue non-empty, why are getters waiting?"
            getter = self._getters.popleft()
            self.__put_internal(item)
            future_set_result_unless_cancelled(getter, self._get())
        elif self.full():
            raise QueueFull
        else:
            self.__put_internal(item)

    def get(
        self, timeout: Optional[Union[float, datetime.timedelta]] = None
    ) -> Awaitable[_T]:
        """Remove and return an item from the queue.

        Returns an awaitable which resolves once an item is available, or raises
        `tornado.util.TimeoutError` after a timeout.

        ``timeout`` may be a number denoting a time (on the same
        scale as `tornado.ioloop.IOLoop.time`, normally `time.time`), or a
        `datetime.timedelta` object for a deadline relative to the
        current time.

        .. note::

           The ``timeout`` argument of this method differs from that
           of the standard library's `queue.Queue.get`. That method
           interprets numeric values as relative timeouts; this one
           interprets them as absolute deadlines and requires
           ``timedelta`` objects for relative timeouts (consistent
           with other timeouts in Tornado).

        """
        future = Future()  # type: Future[_T]
        try:
            future.set_result(self.get_nowait())
        except QueueEmpty:
            self._getters.append(future)
            _set_timeout(future, timeout)
        return future

    def get_nowait(self) -> _T:
        """Remove and return an item from the queue without blocking.

        Return an item if one is immediately available, else raise
        `QueueEmpty`.
        """
        self._consume_expired()
        if self._putters:
            assert self.full(), "queue not full, why are putters waiting?"
            item, putter = self._putters.popleft()
            self.__put_internal(item)
            future_set_result_unless_cancelled(putter, None)
            return self._get()
        elif self.qsize():
            return self._get()
        else:
            raise QueueEmpty

    def task_done(self) -> None:
        """Indicate that a formerly enqueued task is complete.

        Used by queue consumers. For each `.get` used to fetch a task, a
        subsequent call to `.task_done` tells the queue that the processing
        on the task is complete.

        If a `.join` is blocking, it resumes when all items have been
        processed; that is, when every `.put` is matched by a `.task_done`.

        Raises `ValueError` if called more times than `.put`.
        """
        if self._unfinished_tasks <= 0:
            raise ValueError("task_done() called too many times")
        self._unfinished_tasks -= 1
        if self._unfinished_tasks == 0:
            self._finished.set()

    def join(
        self, timeout: Optional[Union[float, datetime.timedelta]] = None
    ) -> Awaitable[None]:
        """Block until all items in the queue are processed.

        Returns an awaitable, which raises `tornado.util.TimeoutError` after a
        timeout.
        """
        return self._finished.wait(timeout)

    def __aiter__(self) -> _QueueIterator[_T]:
        return _QueueIterator(self)

    # These three are overridable in subclasses.
    def _init(self) -> None:
        self._queue = collections.deque()

    def _get(self) -> _T:
        return self._queue.popleft()

    def _put(self, item: _T) -> None:
        self._queue.append(item)

    # End of the overridable methods.

    def __put_internal(self, item: _T) -> None:
        self._unfinished_tasks += 1
        self._finished.clear()
        self._put(item)

    def _consume_expired(self) -> None:
        # Remove timed-out waiters.
        while self._putters and self._putters[0][1].done():
            self._putters.popleft()

        while self._getters and self._getters[0].done():
            self._getters.popleft()

    def __repr__(self) -> str:
        return f"<{type(self).__name__} at {hex(id(self))} {self._format()}>"

    def __str__(self) -> str:
        return f"<{type(self).__name__} {self._format()}>"

    def _format(self) -> str:
        result = f"maxsize={self.maxsize!r}"
        if getattr(self, "_queue", None):
            result += " queue=%r" % self._queue
        if self._getters:
            result += " getters[%s]" % len(self._getters)
        if self._putters:
            result += " putters[%s]" % len(self._putters)
        if self._unfinished_tasks:
            result += " tasks=%s" % self._unfinished_tasks
        return result


class PriorityQueue(Queue):
    """A `.Queue` that retrieves entries in priority order, lowest first.

    Entries are typically tuples like ``(priority number, data)``.

    .. testcode::

        import asyncio
        from tornado.queues import PriorityQueue

        async def main():
            q = PriorityQueue()
            q.put((1, 'medium-priority item'))
            q.put((0, 'high-priority item'))
            q.put((10, 'low-priority item'))

            print(await q.get())
            print(await q.get())
            print(await q.get())

        asyncio.run(main())

    .. testoutput::

        (0, 'high-priority item')
        (1, 'medium-priority item')
        (10, 'low-priority item')
    """

    def _init(self) -> None:
        self._queue = []

    def _put(self, item: _T) -> None:
        heapq.heappush(self._queue, item)

    def _get(self) -> _T:  # type: ignore[type-var]
        return heapq.heappop(self._queue)


class LifoQueue(Queue):
    """A `.Queue` that retrieves the most recently put items first.

    .. testcode::

        import asyncio
        from tornado.queues import LifoQueue

        async def main():
            q = LifoQueue()
            q.put(3)
            q.put(2)
            q.put(1)

            print(await q.get())
            print(await q.get())
            print(await q.get())

        asyncio.run(main())

    .. testoutput::

        1
        2
        3
    """

    def _init(self) -> None:
        self._queue = []

    def _put(self, item: _T) -> None:
        self._queue.append(item)

    def _get(self) -> _T:  # type: ignore[type-var]
        return self._queue.pop()

# === NexusCore/openenv\Lib\site-packages\trio\_util.py ===
# Little utilities we use internally
from __future__ import annotations

import collections.abc
import inspect
import signal
from abc import ABCMeta
from collections.abc import Awaitable, Callable, Sequence
from functools import update_wrapper
from typing import (
    TYPE_CHECKING,
    Any,
    Generic,
    NoReturn,
    TypeVar,
    final as std_final,
)

from sniffio import thread_local as sniffio_loop

import trio

# Explicit "Any" is not allowed
CallT = TypeVar("CallT", bound=Callable[..., Any])  # type: ignore[explicit-any]
T = TypeVar("T")
RetT = TypeVar("RetT")

if TYPE_CHECKING:
    import sys
    from types import AsyncGeneratorType, TracebackType

    from typing_extensions import ParamSpec, Self, TypeVarTuple, Unpack

    if sys.version_info < (3, 11):
        from exceptiongroup import BaseExceptionGroup

    ArgsT = ParamSpec("ArgsT")
    PosArgsT = TypeVarTuple("PosArgsT")


# See: #461 as to why this is needed.
# The gist is that threading.main_thread() has the capability to lie to us
# if somebody else edits the threading ident cache to replace the main
# thread; causing threading.current_thread() to return a _DummyThread,
# causing the C-c check to fail, and so on.
# Trying to use signal out of the main thread will fail, so we can then
# reliably check if this is the main thread without relying on a
# potentially modified threading.
def is_main_thread() -> bool:
    """Attempt to reliably check if we are in the main thread."""
    try:
        signal.signal(signal.SIGINT, signal.getsignal(signal.SIGINT))
        return True
    except (TypeError, ValueError):
        return False


######
# Call the function and get the coroutine object, while giving helpful
# errors for common mistakes. Returns coroutine object.
######
def coroutine_or_error(
    async_fn: Callable[[Unpack[PosArgsT]], Awaitable[RetT]],
    *args: Unpack[PosArgsT],
) -> collections.abc.Coroutine[object, NoReturn, RetT]:
    def _return_value_looks_like_wrong_library(value: object) -> bool:
        # Returned by legacy @asyncio.coroutine functions, which includes
        # a surprising proportion of asyncio builtins.
        if isinstance(value, collections.abc.Generator):
            return True
        # The protocol for detecting an asyncio Future-like object
        if getattr(value, "_asyncio_future_blocking", None) is not None:
            return True
        # This janky check catches tornado Futures and twisted Deferreds.
        # By the time we're calling this function, we already know
        # something has gone wrong, so a heuristic is pretty safe.
        return value.__class__.__name__ in ("Future", "Deferred")

    # Make sure a sync-fn-that-returns-coroutine still sees itself as being
    # in trio context
    prev_loop, sniffio_loop.name = sniffio_loop.name, "trio"

    try:
        coro = async_fn(*args)

    except TypeError:
        # Give good error for: nursery.start_soon(trio.sleep(1))
        if isinstance(async_fn, collections.abc.Coroutine):
            # explicitly close coroutine to avoid RuntimeWarning
            async_fn.close()

            raise TypeError(
                "Trio was expecting an async function, but instead it got "
                f"a coroutine object {async_fn!r}\n"
                "\n"
                "Probably you did something like:\n"
                "\n"
                f"  trio.run({async_fn.__name__}(...))            # incorrect!\n"
                f"  nursery.start_soon({async_fn.__name__}(...))  # incorrect!\n"
                "\n"
                "Instead, you want (notice the parentheses!):\n"
                "\n"
                f"  trio.run({async_fn.__name__}, ...)            # correct!\n"
                f"  nursery.start_soon({async_fn.__name__}, ...)  # correct!",
            ) from None

        # Give good error for: nursery.start_soon(future)
        if _return_value_looks_like_wrong_library(async_fn):
            raise TypeError(
                "Trio was expecting an async function, but instead it got "
                f"{async_fn!r} – are you trying to use a library written for "
                "asyncio/twisted/tornado or similar? That won't work "
                "without some sort of compatibility shim.",
            ) from None

        raise

    finally:
        sniffio_loop.name = prev_loop

    # We can't check iscoroutinefunction(async_fn), because that will fail
    # for things like functools.partial objects wrapping an async
    # function. So we have to just call it and then check whether the
    # return value is a coroutine object.
    # Note: will not be necessary on python>=3.8, see https://bugs.python.org/issue34890
    # TODO: python3.7 support is now dropped, so the above can be addressed.
    if not isinstance(coro, collections.abc.Coroutine):
        # Give good error for: nursery.start_soon(func_returning_future)
        if _return_value_looks_like_wrong_library(coro):
            raise TypeError(
                f"Trio got unexpected {coro!r} – are you trying to use a "
                "library written for asyncio/twisted/tornado or similar? "
                "That won't work without some sort of compatibility shim.",
            )

        if inspect.isasyncgen(coro):
            raise TypeError(
                "start_soon expected an async function but got an async "
                f"generator {coro!r}",
            )

        # Give good error for: nursery.start_soon(some_sync_fn)
        raise TypeError(
            "Trio expected an async function, but {!r} appears to be "
            "synchronous".format(getattr(async_fn, "__qualname__", async_fn)),
        )

    return coro


class ConflictDetector:
    """Detect when two tasks are about to perform operations that would
    conflict.

    Use as a synchronous context manager; if two tasks enter it at the same
    time then the second one raises an error. You can use it when there are
    two pieces of code that *would* collide and need a lock if they ever were
    called at the same time, but that should never happen.

    We use this in particular for things like, making sure that two different
    tasks don't call sendall simultaneously on the same stream.

    """

    def __init__(self, msg: str) -> None:
        self._msg = msg
        self._held = False

    def __enter__(self) -> None:
        if self._held:
            raise trio.BusyResourceError(self._msg)
        else:
            self._held = True

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self._held = False


def async_wraps(  # type: ignore[explicit-any]
    cls: type[object],
    wrapped_cls: type[object],
    attr_name: str,
) -> Callable[[CallT], CallT]:
    """Similar to wraps, but for async wrappers of non-async functions."""

    def decorator(func: CallT) -> CallT:  # type: ignore[explicit-any]
        func.__name__ = attr_name
        func.__qualname__ = f"{cls.__qualname__}.{attr_name}"

        func.__doc__ = f"Like :meth:`~{wrapped_cls.__module__}.{wrapped_cls.__qualname__}.{attr_name}`, but async."

        return func

    return decorator


def fixup_module_metadata(
    module_name: str,
    namespace: collections.abc.Mapping[str, object],
) -> None:
    seen_ids: set[int] = set()

    def fix_one(qualname: str, name: str, obj: object) -> None:
        # avoid infinite recursion (relevant when using
        # typing.Generic, for example)
        if id(obj) in seen_ids:
            return
        seen_ids.add(id(obj))

        mod = getattr(obj, "__module__", None)
        if mod is not None and mod.startswith("trio."):
            obj.__module__ = module_name
            # Modules, unlike everything else in Python, put fully-qualified
            # names into their __name__ attribute. We check for "." to avoid
            # rewriting these.
            if hasattr(obj, "__name__") and "." not in obj.__name__:
                obj.__name__ = name
                if hasattr(obj, "__qualname__"):
                    obj.__qualname__ = qualname
            if isinstance(obj, type):
                for attr_name, attr_value in obj.__dict__.items():
                    fix_one(objname + "." + attr_name, attr_name, attr_value)

    for objname, obj in namespace.items():
        if not objname.startswith("_"):  # ignore private attributes
            fix_one(objname, objname, obj)


# We need ParamSpec to type this "properly", but that requires a runtime typing_extensions import
# to use as a class base. This is only used at runtime and isn't correct for type checkers anyway,
# so don't bother.
class generic_function(Generic[RetT]):
    """Decorator that makes a function indexable, to communicate
    non-inferable generic type parameters to a static type checker.

    If you write::

        @generic_function
        def open_memory_channel(max_buffer_size: int) -> Tuple[
            SendChannel[T], ReceiveChannel[T]
        ]: ...

    it is valid at runtime to say ``open_memory_channel[bytes](5)``.
    This behaves identically to ``open_memory_channel(5)`` at runtime,
    and currently won't type-check without a mypy plugin or clever stubs,
    but at least it becomes possible to write those.
    """

    def __init__(  # type: ignore[explicit-any]
        self,
        fn: Callable[..., RetT],
    ) -> None:
        update_wrapper(self, fn)
        self._fn = fn

    def __call__(self, *args: object, **kwargs: object) -> RetT:
        return self._fn(*args, **kwargs)

    def __getitem__(self, subscript: object) -> Self:
        return self


def _init_final_cls(cls: type[object]) -> NoReturn:
    """Raises an exception when a final class is subclassed."""
    raise TypeError(f"{cls.__module__}.{cls.__qualname__} does not support subclassing")


def _final_impl(decorated: type[T]) -> type[T]:
    """Decorator that enforces a class to be final (i.e., subclass not allowed).

    If a class uses this metaclass like this::

        @final
        class SomeClass:
            pass

    The metaclass will ensure that no subclass can be created.

    Raises
    ------
    - TypeError if a subclass is created
    """
    # Override the method blindly. We're always going to raise, so it doesn't
    # matter what the original did (if anything).
    decorated.__init_subclass__ = classmethod(_init_final_cls)  # type: ignore[assignment]
    # Apply the typing decorator, in 3.11+ it adds a __final__ marker attribute.
    return std_final(decorated)


if TYPE_CHECKING:
    from typing import final
else:
    final = _final_impl


@final  # No subclassing of NoPublicConstructor itself.
class NoPublicConstructor(ABCMeta):
    """Metaclass that ensures a private constructor.

    If a class uses this metaclass like this::

        @final
        class SomeClass(metaclass=NoPublicConstructor):
            pass

    The metaclass will ensure that no instance can be initialized. This should always be
    used with @final.

    If you try to instantiate your class (SomeClass()), a TypeError will be thrown. Use
    _create() instead in the class's implementation.

    Raises
    ------
    - TypeError if an instance is created.
    """

    def __call__(cls, *args: object, **kwargs: object) -> None:
        raise TypeError(
            f"{cls.__module__}.{cls.__qualname__} has no public constructor",
        )

    def _create(cls: type[T], *args: object, **kwargs: object) -> T:
        return super().__call__(*args, **kwargs)  # type: ignore


def name_asyncgen(agen: AsyncGeneratorType[object, NoReturn]) -> str:
    """Return the fully-qualified name of the async generator function
    that produced the async generator iterator *agen*.
    """
    if not hasattr(agen, "ag_code"):  # pragma: no cover
        return repr(agen)
    try:
        module = agen.ag_frame.f_globals["__name__"]
    except (AttributeError, KeyError):
        module = f"<{agen.ag_code.co_filename}>"
    try:
        qualname = agen.__qualname__
    except AttributeError:
        qualname = agen.ag_code.co_name
    return f"{module}.{qualname}"


# work around a pyright error
if TYPE_CHECKING:
    Fn = TypeVar("Fn", bound=Callable[..., object])  # type: ignore[explicit-any]

    def wraps(  # type: ignore[explicit-any]
        wrapped: Callable[..., object],
        assigned: Sequence[str] = ...,
        updated: Sequence[str] = ...,
    ) -> Callable[[Fn], Fn]: ...

else:
    from functools import wraps  # noqa: F401  # this is re-exported


def raise_saving_context(exc: BaseException) -> NoReturn:
    """This helper allows re-raising an exception without __context__ being set."""
    # cause does not need special handling, we simply avoid using `raise .. from ..`
    # __suppress_context__ also does not need handling, it's only set if modifying cause
    __tracebackhide__ = True
    context = exc.__context__
    try:
        raise exc
    finally:
        exc.__context__ = context
        del exc, context


class MultipleExceptionError(Exception):
    """Raised by raise_single_exception_from_group if encountering multiple
    non-cancelled exceptions."""


def raise_single_exception_from_group(
    eg: BaseExceptionGroup[BaseException],
) -> NoReturn:
    """This function takes an exception group that is assumed to have at most
    one non-cancelled exception, which it reraises as a standalone exception.

    This exception may be an exceptiongroup itself, in which case it will not be unwrapped.

    If a :exc:`KeyboardInterrupt` is encountered, a new KeyboardInterrupt is immediately
    raised with the entire group as cause.

    If the group only contains :exc:`Cancelled` it reraises the first one encountered.

    It will retain context and cause of the contained exception, and entirely discard
    the cause/context of the group(s).

    If multiple non-cancelled exceptions are encountered, it raises
    :exc:`AssertionError`.
    """
    # immediately bail out if there's any KI or SystemExit
    for e in eg.exceptions:
        if isinstance(e, (KeyboardInterrupt, SystemExit)):
            raise type(e) from eg

    cancelled_exception: trio.Cancelled | None = None
    noncancelled_exception: BaseException | None = None

    for e in eg.exceptions:
        if isinstance(e, trio.Cancelled):
            if cancelled_exception is None:
                cancelled_exception = e
        elif noncancelled_exception is None:
            noncancelled_exception = e
        else:
            raise MultipleExceptionError(
                "Attempted to unwrap exceptiongroup with multiple non-cancelled exceptions. This is often caused by a bug in the caller."
            ) from eg

    if noncancelled_exception is not None:
        raise_saving_context(noncancelled_exception)

    assert cancelled_exception is not None, "group can't be empty"
    raise_saving_context(cancelled_exception)

# === NexusCore/openenv\Lib\site-packages\huggingface_hub\inference\_common.py ===
# coding=utf-8
# Copyright 2023-present, the HuggingFace Inc. team.
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
"""Contains utilities used by both the sync and async inference clients."""

import base64
import io
import json
import logging
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import (
    TYPE_CHECKING,
    Any,
    AsyncIterable,
    BinaryIO,
    ContextManager,
    Dict,
    Generator,
    Iterable,
    List,
    Literal,
    NoReturn,
    Optional,
    Union,
    overload,
)

from requests import HTTPError

from huggingface_hub.errors import (
    GenerationError,
    IncompleteGenerationError,
    OverloadedError,
    TextGenerationError,
    UnknownError,
    ValidationError,
)

from ..utils import get_session, is_aiohttp_available, is_numpy_available, is_pillow_available
from ._generated.types import ChatCompletionStreamOutput, TextGenerationStreamOutput


if TYPE_CHECKING:
    from aiohttp import ClientResponse, ClientSession
    from PIL.Image import Image

# TYPES
UrlT = str
PathT = Union[str, Path]
BinaryT = Union[bytes, BinaryIO]
ContentT = Union[BinaryT, PathT, UrlT]

# Use to set a Accept: image/png header
TASKS_EXPECTING_IMAGES = {"text-to-image", "image-to-image"}

logger = logging.getLogger(__name__)


@dataclass
class RequestParameters:
    url: str
    task: str
    model: Optional[str]
    json: Optional[Union[str, Dict, List]]
    data: Optional[ContentT]
    headers: Dict[str, Any]


# Add dataclass for ModelStatus. We use this dataclass in get_model_status function.
@dataclass
class ModelStatus:
    """
    This Dataclass represents the model status in the HF Inference API.

    Args:
        loaded (`bool`):
            If the model is currently loaded into HF's Inference API. Models
            are loaded on-demand, leading to the user's first request taking longer.
            If a model is loaded, you can be assured that it is in a healthy state.
        state (`str`):
            The current state of the model. This can be 'Loaded', 'Loadable', 'TooBig'.
            If a model's state is 'Loadable', it's not too big and has a supported
            backend. Loadable models are automatically loaded when the user first
            requests inference on the endpoint. This means it is transparent for the
            user to load a model, except that the first call takes longer to complete.
        compute_type (`Dict`):
            Information about the compute resource the model is using or will use, such as 'gpu' type and number of
            replicas.
        framework (`str`):
            The name of the framework that the model was built with, such as 'transformers'
            or 'text-generation-inference'.
    """

    loaded: bool
    state: str
    compute_type: Dict
    framework: str


## IMPORT UTILS


def _import_aiohttp():
    # Make sure `aiohttp` is installed on the machine.
    if not is_aiohttp_available():
        raise ImportError("Please install aiohttp to use `AsyncInferenceClient` (`pip install aiohttp`).")
    import aiohttp

    return aiohttp


def _import_numpy():
    """Make sure `numpy` is installed on the machine."""
    if not is_numpy_available():
        raise ImportError("Please install numpy to use deal with embeddings (`pip install numpy`).")
    import numpy

    return numpy


def _import_pil_image():
    """Make sure `PIL` is installed on the machine."""
    if not is_pillow_available():
        raise ImportError(
            "Please install Pillow to use deal with images (`pip install Pillow`). If you don't want the image to be"
            " post-processed, use `client.post(...)` and get the raw response from the server."
        )
    from PIL import Image

    return Image


## ENCODING / DECODING UTILS


@overload
def _open_as_binary(
    content: ContentT,
) -> ContextManager[BinaryT]: ...  # means "if input is not None, output is not None"


@overload
def _open_as_binary(
    content: Literal[None],
) -> ContextManager[Literal[None]]: ...  # means "if input is None, output is None"


@contextmanager  # type: ignore
def _open_as_binary(content: Optional[ContentT]) -> Generator[Optional[BinaryT], None, None]:
    """Open `content` as a binary file, either from a URL, a local path, or raw bytes.

    Do nothing if `content` is None,

    TODO: handle a PIL.Image as input
    TODO: handle base64 as input
    """
    # If content is a string => must be either a URL or a path
    if isinstance(content, str):
        if content.startswith("https://") or content.startswith("http://"):
            logger.debug(f"Downloading content from {content}")
            yield get_session().get(content).content  # TODO: retrieve as stream and pipe to post request ?
            return
        content = Path(content)
        if not content.exists():
            raise FileNotFoundError(
                f"File not found at {content}. If `data` is a string, it must either be a URL or a path to a local"
                " file. To pass raw content, please encode it as bytes first."
            )

    # If content is a Path => open it
    if isinstance(content, Path):
        logger.debug(f"Opening content from {content}")
        with content.open("rb") as f:
            yield f
    else:
        # Otherwise: already a file-like object or None
        yield content


def _b64_encode(content: ContentT) -> str:
    """Encode a raw file (image, audio) into base64. Can be bytes, an opened file, a path or a URL."""
    with _open_as_binary(content) as data:
        data_as_bytes = data if isinstance(data, bytes) else data.read()
        return base64.b64encode(data_as_bytes).decode()


def _b64_to_image(encoded_image: str) -> "Image":
    """Parse a base64-encoded string into a PIL Image."""
    Image = _import_pil_image()
    return Image.open(io.BytesIO(base64.b64decode(encoded_image)))


def _bytes_to_list(content: bytes) -> List:
    """Parse bytes from a Response object into a Python list.

    Expects the response body to be JSON-encoded data.

    NOTE: This is exactly the same implementation as `_bytes_to_dict` and will not complain if the returned data is a
    dictionary. The only advantage of having both is to help the user (and mypy) understand what kind of data to expect.
    """
    return json.loads(content.decode())


def _bytes_to_dict(content: bytes) -> Dict:
    """Parse bytes from a Response object into a Python dictionary.

    Expects the response body to be JSON-encoded data.

    NOTE: This is exactly the same implementation as `_bytes_to_list` and will not complain if the returned data is a
    list. The only advantage of having both is to help the user (and mypy) understand what kind of data to expect.
    """
    return json.loads(content.decode())


def _bytes_to_image(content: bytes) -> "Image":
    """Parse bytes from a Response object into a PIL Image.

    Expects the response body to be raw bytes. To deal with b64 encoded images, use `_b64_to_image` instead.
    """
    Image = _import_pil_image()
    return Image.open(io.BytesIO(content))


def _as_dict(response: Union[bytes, Dict]) -> Dict:
    return json.loads(response) if isinstance(response, bytes) else response


## PAYLOAD UTILS


## STREAMING UTILS


def _stream_text_generation_response(
    bytes_output_as_lines: Iterable[bytes], details: bool
) -> Union[Iterable[str], Iterable[TextGenerationStreamOutput]]:
    """Used in `InferenceClient.text_generation`."""
    # Parse ServerSentEvents
    for byte_payload in bytes_output_as_lines:
        try:
            output = _format_text_generation_stream_output(byte_payload, details)
        except StopIteration:
            break
        if output is not None:
            yield output


async def _async_stream_text_generation_response(
    bytes_output_as_lines: AsyncIterable[bytes], details: bool
) -> Union[AsyncIterable[str], AsyncIterable[TextGenerationStreamOutput]]:
    """Used in `AsyncInferenceClient.text_generation`."""
    # Parse ServerSentEvents
    async for byte_payload in bytes_output_as_lines:
        try:
            output = _format_text_generation_stream_output(byte_payload, details)
        except StopIteration:
            break
        if output is not None:
            yield output


def _format_text_generation_stream_output(
    byte_payload: bytes, details: bool
) -> Optional[Union[str, TextGenerationStreamOutput]]:
    if not byte_payload.startswith(b"data:"):
        return None  # empty line

    if byte_payload.strip() == b"data: [DONE]":
        raise StopIteration("[DONE] signal received.")

    # Decode payload
    payload = byte_payload.decode("utf-8")
    json_payload = json.loads(payload.lstrip("data:").rstrip("/n"))

    # Either an error as being returned
    if json_payload.get("error") is not None:
        raise _parse_text_generation_error(json_payload["error"], json_payload.get("error_type"))

    # Or parse token payload
    output = TextGenerationStreamOutput.parse_obj_as_instance(json_payload)
    return output.token.text if not details else output


def _stream_chat_completion_response(
    bytes_lines: Iterable[bytes],
) -> Iterable[ChatCompletionStreamOutput]:
    """Used in `InferenceClient.chat_completion` if model is served with TGI."""
    for item in bytes_lines:
        try:
            output = _format_chat_completion_stream_output(item)
        except StopIteration:
            break
        if output is not None:
            yield output


async def _async_stream_chat_completion_response(
    bytes_lines: AsyncIterable[bytes],
) -> AsyncIterable[ChatCompletionStreamOutput]:
    """Used in `AsyncInferenceClient.chat_completion`."""
    async for item in bytes_lines:
        try:
            output = _format_chat_completion_stream_output(item)
        except StopIteration:
            break
        if output is not None:
            yield output


def _format_chat_completion_stream_output(
    byte_payload: bytes,
) -> Optional[ChatCompletionStreamOutput]:
    if not byte_payload.startswith(b"data:"):
        return None  # empty line

    if byte_payload.strip() == b"data: [DONE]":
        raise StopIteration("[DONE] signal received.")

    # Decode payload
    payload = byte_payload.decode("utf-8")
    json_payload = json.loads(payload.lstrip("data:").rstrip("/n"))

    # Either an error as being returned
    if json_payload.get("error") is not None:
        raise _parse_text_generation_error(json_payload["error"], json_payload.get("error_type"))

    # Or parse token payload
    return ChatCompletionStreamOutput.parse_obj_as_instance(json_payload)


async def _async_yield_from(client: "ClientSession", response: "ClientResponse") -> AsyncIterable[bytes]:
    async for byte_payload in response.content:
        yield byte_payload.strip()
    await client.close()


# "TGI servers" are servers running with the `text-generation-inference` backend.
# This backend is the go-to solution to run large language models at scale. However,
# for some smaller models (e.g. "gpt2") the default `transformers` + `api-inference`
# solution is still in use.
#
# Both approaches have very similar APIs, but not exactly the same. What we do first in
# the `text_generation` method is to assume the model is served via TGI. If we realize
# it's not the case (i.e. we receive an HTTP 400 Bad Request), we fallback to the
# default API with a warning message. When that's the case, We remember the unsupported
# attributes for this model in the `_UNSUPPORTED_TEXT_GENERATION_KWARGS` global variable.
#
# In addition, TGI servers have a built-in API route for chat-completion, which is not
# available on the default API. We use this route to provide a more consistent behavior
# when available.
#
# For more details, see https://github.com/huggingface/text-generation-inference and
# https://huggingface.co/docs/api-inference/detailed_parameters#text-generation-task.

_UNSUPPORTED_TEXT_GENERATION_KWARGS: Dict[Optional[str], List[str]] = {}


def _set_unsupported_text_generation_kwargs(model: Optional[str], unsupported_kwargs: List[str]) -> None:
    _UNSUPPORTED_TEXT_GENERATION_KWARGS.setdefault(model, []).extend(unsupported_kwargs)


def _get_unsupported_text_generation_kwargs(model: Optional[str]) -> List[str]:
    return _UNSUPPORTED_TEXT_GENERATION_KWARGS.get(model, [])


# TEXT GENERATION ERRORS
# ----------------------
# Text-generation errors are parsed separately to handle as much as possible the errors returned by the text generation
# inference project (https://github.com/huggingface/text-generation-inference).
# ----------------------


def raise_text_generation_error(http_error: HTTPError) -> NoReturn:
    """
    Try to parse text-generation-inference error message and raise HTTPError in any case.

    Args:
        error (`HTTPError`):
            The HTTPError that have been raised.
    """
    # Try to parse a Text Generation Inference error

    try:
        # Hacky way to retrieve payload in case of aiohttp error
        payload = getattr(http_error, "response_error_payload", None) or http_error.response.json()
        error = payload.get("error")
        error_type = payload.get("error_type")
    except Exception:  # no payload
        raise http_error

    # If error_type => more information than `hf_raise_for_status`
    if error_type is not None:
        exception = _parse_text_generation_error(error, error_type)
        raise exception from http_error

    # Otherwise, fallback to default error
    raise http_error


def _parse_text_generation_error(error: Optional[str], error_type: Optional[str]) -> TextGenerationError:
    if error_type == "generation":
        return GenerationError(error)  # type: ignore
    if error_type == "incomplete_generation":
        return IncompleteGenerationError(error)  # type: ignore
    if error_type == "overloaded":
        return OverloadedError(error)  # type: ignore
    if error_type == "validation":
        return ValidationError(error)  # type: ignore
    return UnknownError(error)  # type: ignore

# === NexusCore/openenv\Lib\site-packages\litellm\proxy\db\db_transaction_queue\redis_update_buffer.py ===
"""
Handles buffering database `UPDATE` transactions in Redis before committing them to the database

This is to prevent deadlocks and improve reliability
"""

import asyncio
import json
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Union, cast

from litellm._logging import verbose_proxy_logger
from litellm.caching import RedisCache
from litellm.constants import (
    MAX_REDIS_BUFFER_DEQUEUE_COUNT,
    REDIS_DAILY_SPEND_UPDATE_BUFFER_KEY,
    REDIS_DAILY_TAG_SPEND_UPDATE_BUFFER_KEY,
    REDIS_DAILY_TEAM_SPEND_UPDATE_BUFFER_KEY,
    REDIS_UPDATE_BUFFER_KEY,
)
from litellm.litellm_core_utils.safe_json_dumps import safe_dumps
from litellm.proxy._types import (
    DailyTagSpendTransaction,
    DailyTeamSpendTransaction,
    DailyUserSpendTransaction,
    DBSpendUpdateTransactions,
)
from litellm.proxy.db.db_transaction_queue.base_update_queue import service_logger_obj
from litellm.proxy.db.db_transaction_queue.daily_spend_update_queue import (
    DailySpendUpdateQueue,
)
from litellm.proxy.db.db_transaction_queue.spend_update_queue import SpendUpdateQueue
from litellm.secret_managers.main import str_to_bool
from litellm.types.services import ServiceTypes

if TYPE_CHECKING:
    from litellm.proxy.utils import PrismaClient
else:
    PrismaClient = Any


class RedisUpdateBuffer:
    """
    Handles buffering database `UPDATE` transactions in Redis before committing them to the database

    This is to prevent deadlocks and improve reliability
    """

    def __init__(
        self,
        redis_cache: Optional[RedisCache] = None,
    ):
        self.redis_cache = redis_cache

    @staticmethod
    def _should_commit_spend_updates_to_redis() -> bool:
        """
        Checks if the Pod should commit spend updates to Redis

        This setting enables buffering database transactions in Redis
        to improve reliability and reduce database contention
        """
        from litellm.proxy.proxy_server import general_settings

        _use_redis_transaction_buffer: Optional[Union[bool, str]] = (
            general_settings.get("use_redis_transaction_buffer", False)
        )
        if isinstance(_use_redis_transaction_buffer, str):
            _use_redis_transaction_buffer = str_to_bool(_use_redis_transaction_buffer)
        if _use_redis_transaction_buffer is None:
            return False
        return _use_redis_transaction_buffer

    async def _store_transactions_in_redis(
        self,
        transactions: Any,
        redis_key: str,
        service_type: ServiceTypes,
    ) -> None:
        """
        Helper method to store transactions in Redis and emit an event

        Args:
            transactions: The transactions to store
            redis_key: The Redis key to store under
            service_type: The service type for event emission
        """
        if transactions is None or len(transactions) == 0:
            return

        list_of_transactions = [safe_dumps(transactions)]
        if self.redis_cache is None:
            return
        current_redis_buffer_size = await self.redis_cache.async_rpush(
            key=redis_key,
            values=list_of_transactions,
        )
        await self._emit_new_item_added_to_redis_buffer_event(
            queue_size=current_redis_buffer_size,
            service=service_type,
        )

    async def store_in_memory_spend_updates_in_redis(
        self,
        spend_update_queue: SpendUpdateQueue,
        daily_spend_update_queue: DailySpendUpdateQueue,
        daily_team_spend_update_queue: DailySpendUpdateQueue,
        daily_tag_spend_update_queue: DailySpendUpdateQueue,
    ):
        """
        Stores the in-memory spend updates to Redis

        Stores the following in memory data structures in Redis:
            - SpendUpdateQueue - Key, User, Team, TeamMember, Org, EndUser Spend updates
            - DailySpendUpdateQueue - Daily Spend updates Aggregate view

        For SpendUpdateQueue:
            Each transaction is a dict stored as following:
            - key is the entity id
            - value is the spend amount

                ```
                Redis List:
                key_list_transactions:
                [
                    "0929880201": 1.2,
                    "0929880202": 0.01,
                    "0929880203": 0.001,
                ]
                ```

        For DailySpendUpdateQueue:
            Each transaction is a Dict[str, DailyUserSpendTransaction] stored as following:
            - key is the daily_transaction_key
            - value is the DailyUserSpendTransaction

                ```
                Redis List:
                daily_spend_update_transactions:
                [
                    {
                        "user_keyhash_1_model_1": {
                            "spend": 1.2,
                            "prompt_tokens": 1000,
                            "completion_tokens": 1000,
                            "api_requests": 1000,
                            "successful_requests": 1000,
                        },

                    }
                ]
                ```
        """
        if self.redis_cache is None:
            verbose_proxy_logger.debug(
                "redis_cache is None, skipping store_in_memory_spend_updates_in_redis"
            )
            return

        # Get all transactions
        db_spend_update_transactions = (
            await spend_update_queue.flush_and_get_aggregated_db_spend_update_transactions()
        )
        daily_spend_update_transactions = (
            await daily_spend_update_queue.flush_and_get_aggregated_daily_spend_update_transactions()
        )
        daily_team_spend_update_transactions = (
            await daily_team_spend_update_queue.flush_and_get_aggregated_daily_spend_update_transactions()
        )
        daily_tag_spend_update_transactions = (
            await daily_tag_spend_update_queue.flush_and_get_aggregated_daily_spend_update_transactions()
        )

        verbose_proxy_logger.debug(
            "ALL DB SPEND UPDATE TRANSACTIONS: %s", db_spend_update_transactions
        )
        verbose_proxy_logger.debug(
            "ALL DAILY SPEND UPDATE TRANSACTIONS: %s", daily_spend_update_transactions
        )

        await self._store_transactions_in_redis(
            transactions=db_spend_update_transactions,
            redis_key=REDIS_UPDATE_BUFFER_KEY,
            service_type=ServiceTypes.REDIS_SPEND_UPDATE_QUEUE,
        )

        await self._store_transactions_in_redis(
            transactions=daily_spend_update_transactions,
            redis_key=REDIS_DAILY_SPEND_UPDATE_BUFFER_KEY,
            service_type=ServiceTypes.REDIS_DAILY_SPEND_UPDATE_QUEUE,
        )

        await self._store_transactions_in_redis(
            transactions=daily_team_spend_update_transactions,
            redis_key=REDIS_DAILY_TEAM_SPEND_UPDATE_BUFFER_KEY,
            service_type=ServiceTypes.REDIS_DAILY_TEAM_SPEND_UPDATE_QUEUE,
        )

        await self._store_transactions_in_redis(
            transactions=daily_tag_spend_update_transactions,
            redis_key=REDIS_DAILY_TAG_SPEND_UPDATE_BUFFER_KEY,
            service_type=ServiceTypes.REDIS_DAILY_TAG_SPEND_UPDATE_QUEUE,
        )

    @staticmethod
    def _number_of_transactions_to_store_in_redis(
        db_spend_update_transactions: DBSpendUpdateTransactions,
    ) -> int:
        """
        Gets the number of transactions to store in Redis
        """
        num_transactions = 0
        for v in db_spend_update_transactions.values():
            if isinstance(v, dict):
                num_transactions += len(v)
        return num_transactions

    @staticmethod
    def _remove_prefix_from_keys(data: Dict[str, Any], prefix: str) -> Dict[str, Any]:
        """
        Removes the specified prefix from the keys of a dictionary.
        """
        return {key.replace(prefix, "", 1): value for key, value in data.items()}

    async def get_all_update_transactions_from_redis_buffer(
        self,
    ) -> Optional[DBSpendUpdateTransactions]:
        """
        Gets all the update transactions from Redis

        On Redis we store a list of transactions as a JSON string

        eg.
            [
                DBSpendUpdateTransactions(
                    user_list_transactions={
                        "user_id_1": 1.2,
                        "user_id_2": 0.01,
                    },
                    end_user_list_transactions={},
                    key_list_transactions={
                        "0929880201": 1.2,
                        "0929880202": 0.01,
                    },
                    team_list_transactions={},
                    team_member_list_transactions={},
                    org_list_transactions={},
                ),
                DBSpendUpdateTransactions(
                    user_list_transactions={
                        "user_id_3": 1.2,
                        "user_id_4": 0.01,
                    },
                    end_user_list_transactions={},
                    key_list_transactions={
                        "key_id_1": 1.2,
                        "key_id_2": 0.01,
                    },
                    team_list_transactions={},
                    team_member_list_transactions={},
                    org_list_transactions={},
            ]
        """
        if self.redis_cache is None:
            return None
        list_of_transactions = await self.redis_cache.async_lpop(
            key=REDIS_UPDATE_BUFFER_KEY,
            count=MAX_REDIS_BUFFER_DEQUEUE_COUNT,
        )
        if list_of_transactions is None:
            return None

        # Parse the list of transactions from JSON strings
        parsed_transactions = self._parse_list_of_transactions(list_of_transactions)

        # If there are no transactions, return None
        if len(parsed_transactions) == 0:
            return None

        # Combine all transactions into a single transaction
        combined_transaction = self._combine_list_of_transactions(parsed_transactions)

        return combined_transaction

    async def get_all_daily_spend_update_transactions_from_redis_buffer(
        self,
    ) -> Optional[Dict[str, DailyUserSpendTransaction]]:
        """
        Gets all the daily spend update transactions from Redis
        """
        if self.redis_cache is None:
            return None
        list_of_transactions = await self.redis_cache.async_lpop(
            key=REDIS_DAILY_SPEND_UPDATE_BUFFER_KEY,
            count=MAX_REDIS_BUFFER_DEQUEUE_COUNT,
        )
        if list_of_transactions is None:
            return None
        list_of_daily_spend_update_transactions = [
            json.loads(transaction) for transaction in list_of_transactions
        ]
        return cast(
            Dict[str, DailyUserSpendTransaction],
            DailySpendUpdateQueue.get_aggregated_daily_spend_update_transactions(
                list_of_daily_spend_update_transactions
            ),
        )

    async def get_all_daily_team_spend_update_transactions_from_redis_buffer(
        self,
    ) -> Optional[Dict[str, DailyTeamSpendTransaction]]:
        """
        Gets all the daily team spend update transactions from Redis
        """
        if self.redis_cache is None:
            return None
        list_of_transactions = await self.redis_cache.async_lpop(
            key=REDIS_DAILY_TEAM_SPEND_UPDATE_BUFFER_KEY,
            count=MAX_REDIS_BUFFER_DEQUEUE_COUNT,
        )
        if list_of_transactions is None:
            return None
        list_of_daily_spend_update_transactions = [
            json.loads(transaction) for transaction in list_of_transactions
        ]
        return cast(
            Dict[str, DailyTeamSpendTransaction],
            DailySpendUpdateQueue.get_aggregated_daily_spend_update_transactions(
                list_of_daily_spend_update_transactions
            ),
        )

    async def get_all_daily_tag_spend_update_transactions_from_redis_buffer(
        self,
    ) -> Optional[Dict[str, DailyTagSpendTransaction]]:
        """
        Gets all the daily tag spend update transactions from Redis
        """
        if self.redis_cache is None:
            return None
        list_of_transactions = await self.redis_cache.async_lpop(
            key=REDIS_DAILY_TAG_SPEND_UPDATE_BUFFER_KEY,
            count=MAX_REDIS_BUFFER_DEQUEUE_COUNT,
        )
        if list_of_transactions is None:
            return None
        list_of_daily_spend_update_transactions = [
            json.loads(transaction) for transaction in list_of_transactions
        ]
        return cast(
            Dict[str, DailyTagSpendTransaction],
            DailySpendUpdateQueue.get_aggregated_daily_spend_update_transactions(
                list_of_daily_spend_update_transactions
            ),
        )

    @staticmethod
    def _parse_list_of_transactions(
        list_of_transactions: Union[Any, List[Any]],
    ) -> List[DBSpendUpdateTransactions]:
        """
        Parses the list of transactions from Redis
        """
        if isinstance(list_of_transactions, list):
            return [json.loads(transaction) for transaction in list_of_transactions]
        else:
            return [json.loads(list_of_transactions)]

    @staticmethod
    def _combine_list_of_transactions(
        list_of_transactions: List[DBSpendUpdateTransactions],
    ) -> DBSpendUpdateTransactions:
        """
        Combines the list of transactions into a single DBSpendUpdateTransactions object
        """
        # Initialize a new combined transaction object with empty dictionaries
        combined_transaction = DBSpendUpdateTransactions(
            user_list_transactions={},
            end_user_list_transactions={},
            key_list_transactions={},
            team_list_transactions={},
            team_member_list_transactions={},
            org_list_transactions={},
        )

        # Define the transaction fields to process
        transaction_fields = [
            "user_list_transactions",
            "end_user_list_transactions",
            "key_list_transactions",
            "team_list_transactions",
            "team_member_list_transactions",
            "org_list_transactions",
        ]

        # Loop through each transaction and combine the values
        for transaction in list_of_transactions:
            # Process each field type
            for field in transaction_fields:
                if transaction.get(field):
                    for entity_id, amount in transaction[field].items():  # type: ignore
                        combined_transaction[field][entity_id] = (  # type: ignore
                            combined_transaction[field].get(entity_id, 0) + amount  # type: ignore
                        )

        return combined_transaction

    async def _emit_new_item_added_to_redis_buffer_event(
        self,
        service: ServiceTypes,
        queue_size: int,
    ):
        asyncio.create_task(
            service_logger_obj.async_service_success_hook(
                service=service,
                duration=0,
                call_type="_emit_new_item_added_to_queue_event",
                event_metadata={
                    "gauge_labels": service,
                    "gauge_value": queue_size,
                },
            )
        )

# === NexusCore/openenv\Lib\site-packages\setuptools\_distutils\compilers\C\unix.py ===
"""distutils.unixccompiler

Contains the UnixCCompiler class, a subclass of CCompiler that handles
the "typical" Unix-style command-line C compiler:
  * macros defined with -Dname[=value]
  * macros undefined with -Uname
  * include search directories specified with -Idir
  * libraries specified with -lllib
  * library search directories specified with -Ldir
  * compile handled by 'cc' (or similar) executable with -c option:
    compiles .c to .o
  * link static library handled by 'ar' command (possibly with 'ranlib')
  * link shared library handled by 'cc -shared'
"""

from __future__ import annotations

import itertools
import os
import re
import shlex
import sys
from collections.abc import Iterable

from ... import sysconfig
from ..._log import log
from ..._macos_compat import compiler_fixup
from ..._modified import newer
from ...compat import consolidate_linker_args
from ...errors import DistutilsExecError
from . import base
from .base import _Macro, gen_lib_options, gen_preprocess_options
from .errors import (
    CompileError,
    LibError,
    LinkError,
)

# XXX Things not currently handled:
#   * optimization/debug/warning flags; we just use whatever's in Python's
#     Makefile and live with it.  Is this adequate?  If not, we might
#     have to have a bunch of subclasses GNUCCompiler, SGICCompiler,
#     SunCCompiler, and I suspect down that road lies madness.
#   * even if we don't know a warning flag from an optimization flag,
#     we need some way for outsiders to feed preprocessor/compiler/linker
#     flags in to us -- eg. a sysadmin might want to mandate certain flags
#     via a site config file, or a user might want to set something for
#     compiling this module distribution only via the setup.py command
#     line, whatever.  As long as these options come from something on the
#     current system, they can be as system-dependent as they like, and we
#     should just happily stuff them into the preprocessor/compiler/linker
#     options and carry on.


def _split_env(cmd):
    """
    For macOS, split command into 'env' portion (if any)
    and the rest of the linker command.

    >>> _split_env(['a', 'b', 'c'])
    ([], ['a', 'b', 'c'])
    >>> _split_env(['/usr/bin/env', 'A=3', 'gcc'])
    (['/usr/bin/env', 'A=3'], ['gcc'])
    """
    pivot = 0
    if os.path.basename(cmd[0]) == "env":
        pivot = 1
        while '=' in cmd[pivot]:
            pivot += 1
    return cmd[:pivot], cmd[pivot:]


def _split_aix(cmd):
    """
    AIX platforms prefix the compiler with the ld_so_aix
    script, so split that from the linker command.

    >>> _split_aix(['a', 'b', 'c'])
    ([], ['a', 'b', 'c'])
    >>> _split_aix(['/bin/foo/ld_so_aix', 'gcc'])
    (['/bin/foo/ld_so_aix'], ['gcc'])
    """
    pivot = os.path.basename(cmd[0]) == 'ld_so_aix'
    return cmd[:pivot], cmd[pivot:]


def _linker_params(linker_cmd, compiler_cmd):
    """
    The linker command usually begins with the compiler
    command (possibly multiple elements), followed by zero or more
    params for shared library building.

    If the LDSHARED env variable overrides the linker command,
    however, the commands may not match.

    Return the best guess of the linker parameters by stripping
    the linker command. If the compiler command does not
    match the linker command, assume the linker command is
    just the first element.

    >>> _linker_params('gcc foo bar'.split(), ['gcc'])
    ['foo', 'bar']
    >>> _linker_params('gcc foo bar'.split(), ['other'])
    ['foo', 'bar']
    >>> _linker_params('ccache gcc foo bar'.split(), 'ccache gcc'.split())
    ['foo', 'bar']
    >>> _linker_params(['gcc'], ['gcc'])
    []
    """
    c_len = len(compiler_cmd)
    pivot = c_len if linker_cmd[:c_len] == compiler_cmd else 1
    return linker_cmd[pivot:]


class Compiler(base.Compiler):
    compiler_type = 'unix'

    # These are used by CCompiler in two places: the constructor sets
    # instance attributes 'preprocessor', 'compiler', etc. from them, and
    # 'set_executable()' allows any of these to be set.  The defaults here
    # are pretty generic; they will probably have to be set by an outsider
    # (eg. using information discovered by the sysconfig about building
    # Python extensions).
    executables = {
        'preprocessor': None,
        'compiler': ["cc"],
        'compiler_so': ["cc"],
        'compiler_cxx': ["c++"],
        'compiler_so_cxx': ["c++"],
        'linker_so': ["cc", "-shared"],
        'linker_so_cxx': ["c++", "-shared"],
        'linker_exe': ["cc"],
        'linker_exe_cxx': ["c++", "-shared"],
        'archiver': ["ar", "-cr"],
        'ranlib': None,
    }

    if sys.platform[:6] == "darwin":
        executables['ranlib'] = ["ranlib"]

    # Needed for the filename generation methods provided by the base
    # class, CCompiler.  NB. whoever instantiates/uses a particular
    # UnixCCompiler instance should set 'shared_lib_ext' -- we set a
    # reasonable common default here, but it's not necessarily used on all
    # Unices!

    src_extensions = [".c", ".C", ".cc", ".cxx", ".cpp", ".m"]
    obj_extension = ".o"
    static_lib_extension = ".a"
    shared_lib_extension = ".so"
    dylib_lib_extension = ".dylib"
    xcode_stub_lib_extension = ".tbd"
    static_lib_format = shared_lib_format = dylib_lib_format = "lib%s%s"
    xcode_stub_lib_format = dylib_lib_format
    if sys.platform == "cygwin":
        exe_extension = ".exe"
        shared_lib_extension = ".dll.a"
        dylib_lib_extension = ".dll"
        dylib_lib_format = "cyg%s%s"

    def _fix_lib_args(self, libraries, library_dirs, runtime_library_dirs):
        """Remove standard library path from rpath"""
        libraries, library_dirs, runtime_library_dirs = super()._fix_lib_args(
            libraries, library_dirs, runtime_library_dirs
        )
        libdir = sysconfig.get_config_var('LIBDIR')
        if (
            runtime_library_dirs
            and libdir.startswith("/usr/lib")
            and (libdir in runtime_library_dirs)
        ):
            runtime_library_dirs.remove(libdir)
        return libraries, library_dirs, runtime_library_dirs

    def preprocess(
        self,
        source: str | os.PathLike[str],
        output_file: str | os.PathLike[str] | None = None,
        macros: list[_Macro] | None = None,
        include_dirs: list[str] | tuple[str, ...] | None = None,
        extra_preargs: list[str] | None = None,
        extra_postargs: Iterable[str] | None = None,
    ):
        fixed_args = self._fix_compile_args(None, macros, include_dirs)
        ignore, macros, include_dirs = fixed_args
        pp_opts = gen_preprocess_options(macros, include_dirs)
        pp_args = self.preprocessor + pp_opts
        if output_file:
            pp_args.extend(['-o', output_file])
        if extra_preargs:
            pp_args[:0] = extra_preargs
        if extra_postargs:
            pp_args.extend(extra_postargs)
        pp_args.append(source)

        # reasons to preprocess:
        # - force is indicated
        # - output is directed to stdout
        # - source file is newer than the target
        preprocess = self.force or output_file is None or newer(source, output_file)
        if not preprocess:
            return

        if output_file:
            self.mkpath(os.path.dirname(output_file))

        try:
            self.spawn(pp_args)
        except DistutilsExecError as msg:
            raise CompileError(msg)

    def _compile(self, obj, src, ext, cc_args, extra_postargs, pp_opts):
        compiler_so = compiler_fixup(self.compiler_so, cc_args + extra_postargs)
        compiler_so_cxx = compiler_fixup(self.compiler_so_cxx, cc_args + extra_postargs)
        try:
            if self.detect_language(src) == 'c++':
                self.spawn(
                    compiler_so_cxx + cc_args + [src, '-o', obj] + extra_postargs
                )
            else:
                self.spawn(compiler_so + cc_args + [src, '-o', obj] + extra_postargs)
        except DistutilsExecError as msg:
            raise CompileError(msg)

    def create_static_lib(
        self, objects, output_libname, output_dir=None, debug=False, target_lang=None
    ):
        objects, output_dir = self._fix_object_args(objects, output_dir)

        output_filename = self.library_filename(output_libname, output_dir=output_dir)

        if self._need_link(objects, output_filename):
            self.mkpath(os.path.dirname(output_filename))
            self.spawn(self.archiver + [output_filename] + objects + self.objects)

            # Not many Unices required ranlib anymore -- SunOS 4.x is, I
            # think the only major Unix that does.  Maybe we need some
            # platform intelligence here to skip ranlib if it's not
            # needed -- or maybe Python's configure script took care of
            # it for us, hence the check for leading colon.
            if self.ranlib:
                try:
                    self.spawn(self.ranlib + [output_filename])
                except DistutilsExecError as msg:
                    raise LibError(msg)
        else:
            log.debug("skipping %s (up-to-date)", output_filename)

    def link(
        self,
        target_desc,
        objects: list[str] | tuple[str, ...],
        output_filename,
        output_dir: str | None = None,
        libraries: list[str] | tuple[str, ...] | None = None,
        library_dirs: list[str] | tuple[str, ...] | None = None,
        runtime_library_dirs: list[str] | tuple[str, ...] | None = None,
        export_symbols=None,
        debug=False,
        extra_preargs=None,
        extra_postargs=None,
        build_temp=None,
        target_lang=None,
    ):
        objects, output_dir = self._fix_object_args(objects, output_dir)
        fixed_args = self._fix_lib_args(libraries, library_dirs, runtime_library_dirs)
        libraries, library_dirs, runtime_library_dirs = fixed_args

        lib_opts = gen_lib_options(self, library_dirs, runtime_library_dirs, libraries)
        if not isinstance(output_dir, (str, type(None))):
            raise TypeError("'output_dir' must be a string or None")
        if output_dir is not None:
            output_filename = os.path.join(output_dir, output_filename)

        if self._need_link(objects, output_filename):
            ld_args = objects + self.objects + lib_opts + ['-o', output_filename]
            if debug:
                ld_args[:0] = ['-g']
            if extra_preargs:
                ld_args[:0] = extra_preargs
            if extra_postargs:
                ld_args.extend(extra_postargs)
            self.mkpath(os.path.dirname(output_filename))
            try:
                # Select a linker based on context: linker_exe when
                # building an executable or linker_so (with shared options)
                # when building a shared library.
                building_exe = target_desc == base.Compiler.EXECUTABLE
                target_cxx = target_lang == "c++"
                linker = (
                    (self.linker_exe_cxx if target_cxx else self.linker_exe)
                    if building_exe
                    else (self.linker_so_cxx if target_cxx else self.linker_so)
                )[:]

                if target_cxx and self.compiler_cxx:
                    env, linker_ne = _split_env(linker)
                    aix, linker_na = _split_aix(linker_ne)
                    _, compiler_cxx_ne = _split_env(self.compiler_cxx)
                    _, linker_exe_ne = _split_env(self.linker_exe_cxx)

                    params = _linker_params(linker_na, linker_exe_ne)
                    linker = env + aix + compiler_cxx_ne + params

                linker = compiler_fixup(linker, ld_args)

                self.spawn(linker + ld_args)
            except DistutilsExecError as msg:
                raise LinkError(msg)
        else:
            log.debug("skipping %s (up-to-date)", output_filename)

    # -- Miscellaneous methods -----------------------------------------
    # These are all used by the 'gen_lib_options() function, in
    # ccompiler.py.

    def library_dir_option(self, dir):
        return "-L" + dir

    def _is_gcc(self):
        cc_var = sysconfig.get_config_var("CC")
        compiler = os.path.basename(shlex.split(cc_var)[0])
        return "gcc" in compiler or "g++" in compiler

    def runtime_library_dir_option(self, dir: str) -> str | list[str]:  # type: ignore[override] # Fixed in pypa/distutils#339
        # XXX Hackish, at the very least.  See Python bug #445902:
        # https://bugs.python.org/issue445902
        # Linkers on different platforms need different options to
        # specify that directories need to be added to the list of
        # directories searched for dependencies when a dynamic library
        # is sought.  GCC on GNU systems (Linux, FreeBSD, ...) has to
        # be told to pass the -R option through to the linker, whereas
        # other compilers and gcc on other systems just know this.
        # Other compilers may need something slightly different.  At
        # this time, there's no way to determine this information from
        # the configuration data stored in the Python installation, so
        # we use this hack.
        if sys.platform[:6] == "darwin":
            from distutils.util import get_macosx_target_ver, split_version

            macosx_target_ver = get_macosx_target_ver()
            if macosx_target_ver and split_version(macosx_target_ver) >= [10, 5]:
                return "-Wl,-rpath," + dir
            else:  # no support for -rpath on earlier macOS versions
                return "-L" + dir
        elif sys.platform[:7] == "freebsd":
            return "-Wl,-rpath=" + dir
        elif sys.platform[:5] == "hp-ux":
            return [
                "-Wl,+s" if self._is_gcc() else "+s",
                "-L" + dir,
            ]

        # For all compilers, `-Wl` is the presumed way to pass a
        # compiler option to the linker
        if sysconfig.get_config_var("GNULD") == "yes":
            return consolidate_linker_args([
                # Force RUNPATH instead of RPATH
                "-Wl,--enable-new-dtags",
                "-Wl,-rpath," + dir,
            ])
        else:
            return "-Wl,-R" + dir

    def library_option(self, lib):
        return "-l" + lib

    @staticmethod
    def _library_root(dir):
        """
        macOS users can specify an alternate SDK using'-isysroot'.
        Calculate the SDK root if it is specified.

        Note that, as of Xcode 7, Apple SDKs may contain textual stub
        libraries with .tbd extensions rather than the normal .dylib
        shared libraries installed in /.  The Apple compiler tool
        chain handles this transparently but it can cause problems
        for programs that are being built with an SDK and searching
        for specific libraries.  Callers of find_library_file need to
        keep in mind that the base filename of the returned SDK library
        file might have a different extension from that of the library
        file installed on the running system, for example:
          /Applications/Xcode.app/Contents/Developer/Platforms/
              MacOSX.platform/Developer/SDKs/MacOSX10.11.sdk/
              usr/lib/libedit.tbd
        vs
          /usr/lib/libedit.dylib
        """
        cflags = sysconfig.get_config_var('CFLAGS')
        match = re.search(r'-isysroot\s*(\S+)', cflags)

        apply_root = (
            sys.platform == 'darwin'
            and match
            and (
                dir.startswith('/System/')
                or (dir.startswith('/usr/') and not dir.startswith('/usr/local/'))
            )
        )

        return os.path.join(match.group(1), dir[1:]) if apply_root else dir

    def find_library_file(self, dirs, lib, debug=False):
        """
        Second-guess the linker with not much hard
        data to go on: GCC seems to prefer the shared library, so
        assume that *all* Unix C compilers do,
        ignoring even GCC's "-static" option.
        """
        lib_names = (
            self.library_filename(lib, lib_type=type)
            for type in 'dylib xcode_stub shared static'.split()
        )

        roots = map(self._library_root, dirs)

        searched = itertools.starmap(os.path.join, itertools.product(roots, lib_names))

        found = filter(os.path.exists, searched)

        # Return None if it could not be found in any dir.
        return next(found, None)

# === NexusCore/openenv\Lib\site-packages\aiohttp\client_exceptions.py ===
"""HTTP related errors."""

import asyncio
import warnings
from typing import TYPE_CHECKING, Optional, Tuple, Union

from multidict import MultiMapping

from .typedefs import StrOrURL

if TYPE_CHECKING:
    import ssl

    SSLContext = ssl.SSLContext
else:
    try:
        import ssl

        SSLContext = ssl.SSLContext
    except ImportError:  # pragma: no cover
        ssl = SSLContext = None  # type: ignore[assignment]

if TYPE_CHECKING:
    from .client_reqrep import ClientResponse, ConnectionKey, Fingerprint, RequestInfo
    from .http_parser import RawResponseMessage
else:
    RequestInfo = ClientResponse = ConnectionKey = RawResponseMessage = None

__all__ = (
    "ClientError",
    "ClientConnectionError",
    "ClientConnectionResetError",
    "ClientOSError",
    "ClientConnectorError",
    "ClientProxyConnectionError",
    "ClientSSLError",
    "ClientConnectorDNSError",
    "ClientConnectorSSLError",
    "ClientConnectorCertificateError",
    "ConnectionTimeoutError",
    "SocketTimeoutError",
    "ServerConnectionError",
    "ServerTimeoutError",
    "ServerDisconnectedError",
    "ServerFingerprintMismatch",
    "ClientResponseError",
    "ClientHttpProxyError",
    "WSServerHandshakeError",
    "ContentTypeError",
    "ClientPayloadError",
    "InvalidURL",
    "InvalidUrlClientError",
    "RedirectClientError",
    "NonHttpUrlClientError",
    "InvalidUrlRedirectClientError",
    "NonHttpUrlRedirectClientError",
    "WSMessageTypeError",
)


class ClientError(Exception):
    """Base class for client connection errors."""


class ClientResponseError(ClientError):
    """Base class for exceptions that occur after getting a response.

    request_info: An instance of RequestInfo.
    history: A sequence of responses, if redirects occurred.
    status: HTTP status code.
    message: Error message.
    headers: Response headers.
    """

    def __init__(
        self,
        request_info: RequestInfo,
        history: Tuple[ClientResponse, ...],
        *,
        code: Optional[int] = None,
        status: Optional[int] = None,
        message: str = "",
        headers: Optional[MultiMapping[str]] = None,
    ) -> None:
        self.request_info = request_info
        if code is not None:
            if status is not None:
                raise ValueError(
                    "Both code and status arguments are provided; "
                    "code is deprecated, use status instead"
                )
            warnings.warn(
                "code argument is deprecated, use status instead",
                DeprecationWarning,
                stacklevel=2,
            )
        if status is not None:
            self.status = status
        elif code is not None:
            self.status = code
        else:
            self.status = 0
        self.message = message
        self.headers = headers
        self.history = history
        self.args = (request_info, history)

    def __str__(self) -> str:
        return "{}, message={!r}, url={!r}".format(
            self.status,
            self.message,
            str(self.request_info.real_url),
        )

    def __repr__(self) -> str:
        args = f"{self.request_info!r}, {self.history!r}"
        if self.status != 0:
            args += f", status={self.status!r}"
        if self.message != "":
            args += f", message={self.message!r}"
        if self.headers is not None:
            args += f", headers={self.headers!r}"
        return f"{type(self).__name__}({args})"

    @property
    def code(self) -> int:
        warnings.warn(
            "code property is deprecated, use status instead",
            DeprecationWarning,
            stacklevel=2,
        )
        return self.status

    @code.setter
    def code(self, value: int) -> None:
        warnings.warn(
            "code property is deprecated, use status instead",
            DeprecationWarning,
            stacklevel=2,
        )
        self.status = value


class ContentTypeError(ClientResponseError):
    """ContentType found is not valid."""


class WSServerHandshakeError(ClientResponseError):
    """websocket server handshake error."""


class ClientHttpProxyError(ClientResponseError):
    """HTTP proxy error.

    Raised in :class:`aiohttp.connector.TCPConnector` if
    proxy responds with status other than ``200 OK``
    on ``CONNECT`` request.
    """


class TooManyRedirects(ClientResponseError):
    """Client was redirected too many times."""


class ClientConnectionError(ClientError):
    """Base class for client socket errors."""


class ClientConnectionResetError(ClientConnectionError, ConnectionResetError):
    """ConnectionResetError"""


class ClientOSError(ClientConnectionError, OSError):
    """OSError error."""


class ClientConnectorError(ClientOSError):
    """Client connector error.

    Raised in :class:`aiohttp.connector.TCPConnector` if
        a connection can not be established.
    """

    def __init__(self, connection_key: ConnectionKey, os_error: OSError) -> None:
        self._conn_key = connection_key
        self._os_error = os_error
        super().__init__(os_error.errno, os_error.strerror)
        self.args = (connection_key, os_error)

    @property
    def os_error(self) -> OSError:
        return self._os_error

    @property
    def host(self) -> str:
        return self._conn_key.host

    @property
    def port(self) -> Optional[int]:
        return self._conn_key.port

    @property
    def ssl(self) -> Union[SSLContext, bool, "Fingerprint"]:
        return self._conn_key.ssl

    def __str__(self) -> str:
        return "Cannot connect to host {0.host}:{0.port} ssl:{1} [{2}]".format(
            self, "default" if self.ssl is True else self.ssl, self.strerror
        )

    # OSError.__reduce__ does too much black magick
    __reduce__ = BaseException.__reduce__


class ClientConnectorDNSError(ClientConnectorError):
    """DNS resolution failed during client connection.

    Raised in :class:`aiohttp.connector.TCPConnector` if
        DNS resolution fails.
    """


class ClientProxyConnectionError(ClientConnectorError):
    """Proxy connection error.

    Raised in :class:`aiohttp.connector.TCPConnector` if
        connection to proxy can not be established.
    """


class UnixClientConnectorError(ClientConnectorError):
    """Unix connector error.

    Raised in :py:class:`aiohttp.connector.UnixConnector`
    if connection to unix socket can not be established.
    """

    def __init__(
        self, path: str, connection_key: ConnectionKey, os_error: OSError
    ) -> None:
        self._path = path
        super().__init__(connection_key, os_error)

    @property
    def path(self) -> str:
        return self._path

    def __str__(self) -> str:
        return "Cannot connect to unix socket {0.path} ssl:{1} [{2}]".format(
            self, "default" if self.ssl is True else self.ssl, self.strerror
        )


class ServerConnectionError(ClientConnectionError):
    """Server connection errors."""


class ServerDisconnectedError(ServerConnectionError):
    """Server disconnected."""

    def __init__(self, message: Union[RawResponseMessage, str, None] = None) -> None:
        if message is None:
            message = "Server disconnected"

        self.args = (message,)
        self.message = message


class ServerTimeoutError(ServerConnectionError, asyncio.TimeoutError):
    """Server timeout error."""


class ConnectionTimeoutError(ServerTimeoutError):
    """Connection timeout error."""


class SocketTimeoutError(ServerTimeoutError):
    """Socket timeout error."""


class ServerFingerprintMismatch(ServerConnectionError):
    """SSL certificate does not match expected fingerprint."""

    def __init__(self, expected: bytes, got: bytes, host: str, port: int) -> None:
        self.expected = expected
        self.got = got
        self.host = host
        self.port = port
        self.args = (expected, got, host, port)

    def __repr__(self) -> str:
        return "<{} expected={!r} got={!r} host={!r} port={!r}>".format(
            self.__class__.__name__, self.expected, self.got, self.host, self.port
        )


class ClientPayloadError(ClientError):
    """Response payload error."""


class InvalidURL(ClientError, ValueError):
    """Invalid URL.

    URL used for fetching is malformed, e.g. it doesn't contains host
    part.
    """

    # Derive from ValueError for backward compatibility

    def __init__(self, url: StrOrURL, description: Union[str, None] = None) -> None:
        # The type of url is not yarl.URL because the exception can be raised
        # on URL(url) call
        self._url = url
        self._description = description

        if description:
            super().__init__(url, description)
        else:
            super().__init__(url)

    @property
    def url(self) -> StrOrURL:
        return self._url

    @property
    def description(self) -> "str | None":
        return self._description

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} {self}>"

    def __str__(self) -> str:
        if self._description:
            return f"{self._url} - {self._description}"
        return str(self._url)


class InvalidUrlClientError(InvalidURL):
    """Invalid URL client error."""


class RedirectClientError(ClientError):
    """Client redirect error."""


class NonHttpUrlClientError(ClientError):
    """Non http URL client error."""


class InvalidUrlRedirectClientError(InvalidUrlClientError, RedirectClientError):
    """Invalid URL redirect client error."""


class NonHttpUrlRedirectClientError(NonHttpUrlClientError, RedirectClientError):
    """Non http URL redirect client error."""


class ClientSSLError(ClientConnectorError):
    """Base error for ssl.*Errors."""


if ssl is not None:
    cert_errors = (ssl.CertificateError,)
    cert_errors_bases = (
        ClientSSLError,
        ssl.CertificateError,
    )

    ssl_errors = (ssl.SSLError,)
    ssl_error_bases = (ClientSSLError, ssl.SSLError)
else:  # pragma: no cover
    cert_errors = tuple()
    cert_errors_bases = (
        ClientSSLError,
        ValueError,
    )

    ssl_errors = tuple()
    ssl_error_bases = (ClientSSLError,)


class ClientConnectorSSLError(*ssl_error_bases):  # type: ignore[misc]
    """Response ssl error."""


class ClientConnectorCertificateError(*cert_errors_bases):  # type: ignore[misc]
    """Response certificate error."""

    def __init__(
        self, connection_key: ConnectionKey, certificate_error: Exception
    ) -> None:
        self._conn_key = connection_key
        self._certificate_error = certificate_error
        self.args = (connection_key, certificate_error)

    @property
    def certificate_error(self) -> Exception:
        return self._certificate_error

    @property
    def host(self) -> str:
        return self._conn_key.host

    @property
    def port(self) -> Optional[int]:
        return self._conn_key.port

    @property
    def ssl(self) -> bool:
        return self._conn_key.is_ssl

    def __str__(self) -> str:
        return (
            "Cannot connect to host {0.host}:{0.port} ssl:{0.ssl} "
            "[{0.certificate_error.__class__.__name__}: "
            "{0.certificate_error.args}]".format(self)
        )


class WSMessageTypeError(TypeError):
    """WebSocket message type is not valid."""