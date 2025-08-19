
# === NexusCore/openenv\Lib\site-packages\pip\_vendor\urllib3\contrib\securetransport.py ===
"""
SecureTranport support for urllib3 via ctypes.

This makes platform-native TLS available to urllib3 users on macOS without the
use of a compiler. This is an important feature because the Python Package
Index is moving to become a TLSv1.2-or-higher server, and the default OpenSSL
that ships with macOS is not capable of doing TLSv1.2. The only way to resolve
this is to give macOS users an alternative solution to the problem, and that
solution is to use SecureTransport.

We use ctypes here because this solution must not require a compiler. That's
because pip is not allowed to require a compiler either.

This is not intended to be a seriously long-term solution to this problem.
The hope is that PEP 543 will eventually solve this issue for us, at which
point we can retire this contrib module. But in the short term, we need to
solve the impending tire fire that is Python on Mac without this kind of
contrib module. So...here we are.

To use this module, simply import and inject it::

    import pip._vendor.urllib3.contrib.securetransport as securetransport
    securetransport.inject_into_urllib3()

Happy TLSing!

This code is a bastardised version of the code found in Will Bond's oscrypto
library. An enormous debt is owed to him for blazing this trail for us. For
that reason, this code should be considered to be covered both by urllib3's
license and by oscrypto's:

.. code-block::

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

import contextlib
import ctypes
import errno
import os.path
import shutil
import socket
import ssl
import struct
import threading
import weakref

from .. import util
from ..packages import six
from ..util.ssl_ import PROTOCOL_TLS_CLIENT
from ._securetransport.bindings import CoreFoundation, Security, SecurityConst
from ._securetransport.low_level import (
    _assert_no_error,
    _build_tls_unknown_ca_alert,
    _cert_array_from_pem,
    _create_cfstring_array,
    _load_client_cert_chain,
    _temporary_keychain,
)

try:  # Platform-specific: Python 2
    from socket import _fileobject
except ImportError:  # Platform-specific: Python 3
    _fileobject = None
    from ..packages.backports.makefile import backport_makefile

__all__ = ["inject_into_urllib3", "extract_from_urllib3"]

# SNI always works
HAS_SNI = True

orig_util_HAS_SNI = util.HAS_SNI
orig_util_SSLContext = util.ssl_.SSLContext

# This dictionary is used by the read callback to obtain a handle to the
# calling wrapped socket. This is a pretty silly approach, but for now it'll
# do. I feel like I should be able to smuggle a handle to the wrapped socket
# directly in the SSLConnectionRef, but for now this approach will work I
# guess.
#
# We need to lock around this structure for inserts, but we don't do it for
# reads/writes in the callbacks. The reasoning here goes as follows:
#
#    1. It is not possible to call into the callbacks before the dictionary is
#       populated, so once in the callback the id must be in the dictionary.
#    2. The callbacks don't mutate the dictionary, they only read from it, and
#       so cannot conflict with any of the insertions.
#
# This is good: if we had to lock in the callbacks we'd drastically slow down
# the performance of this code.
_connection_refs = weakref.WeakValueDictionary()
_connection_ref_lock = threading.Lock()

# Limit writes to 16kB. This is OpenSSL's limit, but we'll cargo-cult it over
# for no better reason than we need *a* limit, and this one is right there.
SSL_WRITE_BLOCKSIZE = 16384

# This is our equivalent of util.ssl_.DEFAULT_CIPHERS, but expanded out to
# individual cipher suites. We need to do this because this is how
# SecureTransport wants them.
CIPHER_SUITES = [
    SecurityConst.TLS_ECDHE_ECDSA_WITH_AES_256_GCM_SHA384,
    SecurityConst.TLS_ECDHE_ECDSA_WITH_AES_128_GCM_SHA256,
    SecurityConst.TLS_ECDHE_RSA_WITH_AES_256_GCM_SHA384,
    SecurityConst.TLS_ECDHE_RSA_WITH_AES_128_GCM_SHA256,
    SecurityConst.TLS_ECDHE_ECDSA_WITH_CHACHA20_POLY1305_SHA256,
    SecurityConst.TLS_ECDHE_RSA_WITH_CHACHA20_POLY1305_SHA256,
    SecurityConst.TLS_DHE_RSA_WITH_AES_256_GCM_SHA384,
    SecurityConst.TLS_DHE_RSA_WITH_AES_128_GCM_SHA256,
    SecurityConst.TLS_ECDHE_ECDSA_WITH_AES_256_CBC_SHA384,
    SecurityConst.TLS_ECDHE_ECDSA_WITH_AES_256_CBC_SHA,
    SecurityConst.TLS_ECDHE_ECDSA_WITH_AES_128_CBC_SHA256,
    SecurityConst.TLS_ECDHE_ECDSA_WITH_AES_128_CBC_SHA,
    SecurityConst.TLS_ECDHE_RSA_WITH_AES_256_CBC_SHA384,
    SecurityConst.TLS_ECDHE_RSA_WITH_AES_256_CBC_SHA,
    SecurityConst.TLS_ECDHE_RSA_WITH_AES_128_CBC_SHA256,
    SecurityConst.TLS_ECDHE_RSA_WITH_AES_128_CBC_SHA,
    SecurityConst.TLS_DHE_RSA_WITH_AES_256_CBC_SHA256,
    SecurityConst.TLS_DHE_RSA_WITH_AES_256_CBC_SHA,
    SecurityConst.TLS_DHE_RSA_WITH_AES_128_CBC_SHA256,
    SecurityConst.TLS_DHE_RSA_WITH_AES_128_CBC_SHA,
    SecurityConst.TLS_AES_256_GCM_SHA384,
    SecurityConst.TLS_AES_128_GCM_SHA256,
    SecurityConst.TLS_RSA_WITH_AES_256_GCM_SHA384,
    SecurityConst.TLS_RSA_WITH_AES_128_GCM_SHA256,
    SecurityConst.TLS_AES_128_CCM_8_SHA256,
    SecurityConst.TLS_AES_128_CCM_SHA256,
    SecurityConst.TLS_RSA_WITH_AES_256_CBC_SHA256,
    SecurityConst.TLS_RSA_WITH_AES_128_CBC_SHA256,
    SecurityConst.TLS_RSA_WITH_AES_256_CBC_SHA,
    SecurityConst.TLS_RSA_WITH_AES_128_CBC_SHA,
]

# Basically this is simple: for PROTOCOL_SSLv23 we turn it into a low of
# TLSv1 and a high of TLSv1.2. For everything else, we pin to that version.
# TLSv1 to 1.2 are supported on macOS 10.8+
_protocol_to_min_max = {
    util.PROTOCOL_TLS: (SecurityConst.kTLSProtocol1, SecurityConst.kTLSProtocol12),
    PROTOCOL_TLS_CLIENT: (SecurityConst.kTLSProtocol1, SecurityConst.kTLSProtocol12),
}

if hasattr(ssl, "PROTOCOL_SSLv2"):
    _protocol_to_min_max[ssl.PROTOCOL_SSLv2] = (
        SecurityConst.kSSLProtocol2,
        SecurityConst.kSSLProtocol2,
    )
if hasattr(ssl, "PROTOCOL_SSLv3"):
    _protocol_to_min_max[ssl.PROTOCOL_SSLv3] = (
        SecurityConst.kSSLProtocol3,
        SecurityConst.kSSLProtocol3,
    )
if hasattr(ssl, "PROTOCOL_TLSv1"):
    _protocol_to_min_max[ssl.PROTOCOL_TLSv1] = (
        SecurityConst.kTLSProtocol1,
        SecurityConst.kTLSProtocol1,
    )
if hasattr(ssl, "PROTOCOL_TLSv1_1"):
    _protocol_to_min_max[ssl.PROTOCOL_TLSv1_1] = (
        SecurityConst.kTLSProtocol11,
        SecurityConst.kTLSProtocol11,
    )
if hasattr(ssl, "PROTOCOL_TLSv1_2"):
    _protocol_to_min_max[ssl.PROTOCOL_TLSv1_2] = (
        SecurityConst.kTLSProtocol12,
        SecurityConst.kTLSProtocol12,
    )


def inject_into_urllib3():
    """
    Monkey-patch urllib3 with SecureTransport-backed SSL-support.
    """
    util.SSLContext = SecureTransportContext
    util.ssl_.SSLContext = SecureTransportContext
    util.HAS_SNI = HAS_SNI
    util.ssl_.HAS_SNI = HAS_SNI
    util.IS_SECURETRANSPORT = True
    util.ssl_.IS_SECURETRANSPORT = True


def extract_from_urllib3():
    """
    Undo monkey-patching by :func:`inject_into_urllib3`.
    """
    util.SSLContext = orig_util_SSLContext
    util.ssl_.SSLContext = orig_util_SSLContext
    util.HAS_SNI = orig_util_HAS_SNI
    util.ssl_.HAS_SNI = orig_util_HAS_SNI
    util.IS_SECURETRANSPORT = False
    util.ssl_.IS_SECURETRANSPORT = False


def _read_callback(connection_id, data_buffer, data_length_pointer):
    """
    SecureTransport read callback. This is called by ST to request that data
    be returned from the socket.
    """
    wrapped_socket = None
    try:
        wrapped_socket = _connection_refs.get(connection_id)
        if wrapped_socket is None:
            return SecurityConst.errSSLInternal
        base_socket = wrapped_socket.socket

        requested_length = data_length_pointer[0]

        timeout = wrapped_socket.gettimeout()
        error = None
        read_count = 0

        try:
            while read_count < requested_length:
                if timeout is None or timeout >= 0:
                    if not util.wait_for_read(base_socket, timeout):
                        raise socket.error(errno.EAGAIN, "timed out")

                remaining = requested_length - read_count
                buffer = (ctypes.c_char * remaining).from_address(
                    data_buffer + read_count
                )
                chunk_size = base_socket.recv_into(buffer, remaining)
                read_count += chunk_size
                if not chunk_size:
                    if not read_count:
                        return SecurityConst.errSSLClosedGraceful
                    break
        except (socket.error) as e:
            error = e.errno

            if error is not None and error != errno.EAGAIN:
                data_length_pointer[0] = read_count
                if error == errno.ECONNRESET or error == errno.EPIPE:
                    return SecurityConst.errSSLClosedAbort
                raise

        data_length_pointer[0] = read_count

        if read_count != requested_length:
            return SecurityConst.errSSLWouldBlock

        return 0
    except Exception as e:
        if wrapped_socket is not None:
            wrapped_socket._exception = e
        return SecurityConst.errSSLInternal


def _write_callback(connection_id, data_buffer, data_length_pointer):
    """
    SecureTransport write callback. This is called by ST to request that data
    actually be sent on the network.
    """
    wrapped_socket = None
    try:
        wrapped_socket = _connection_refs.get(connection_id)
        if wrapped_socket is None:
            return SecurityConst.errSSLInternal
        base_socket = wrapped_socket.socket

        bytes_to_write = data_length_pointer[0]
        data = ctypes.string_at(data_buffer, bytes_to_write)

        timeout = wrapped_socket.gettimeout()
        error = None
        sent = 0

        try:
            while sent < bytes_to_write:
                if timeout is None or timeout >= 0:
                    if not util.wait_for_write(base_socket, timeout):
                        raise socket.error(errno.EAGAIN, "timed out")
                chunk_sent = base_socket.send(data)
                sent += chunk_sent

                # This has some needless copying here, but I'm not sure there's
                # much value in optimising this data path.
                data = data[chunk_sent:]
        except (socket.error) as e:
            error = e.errno

            if error is not None and error != errno.EAGAIN:
                data_length_pointer[0] = sent
                if error == errno.ECONNRESET or error == errno.EPIPE:
                    return SecurityConst.errSSLClosedAbort
                raise

        data_length_pointer[0] = sent

        if sent != bytes_to_write:
            return SecurityConst.errSSLWouldBlock

        return 0
    except Exception as e:
        if wrapped_socket is not None:
            wrapped_socket._exception = e
        return SecurityConst.errSSLInternal


# We need to keep these two objects references alive: if they get GC'd while
# in use then SecureTransport could attempt to call a function that is in freed
# memory. That would be...uh...bad. Yeah, that's the word. Bad.
_read_callback_pointer = Security.SSLReadFunc(_read_callback)
_write_callback_pointer = Security.SSLWriteFunc(_write_callback)


class WrappedSocket(object):
    """
    API-compatibility wrapper for Python's OpenSSL wrapped socket object.

    Note: _makefile_refs, _drop(), and _reuse() are needed for the garbage
    collector of PyPy.
    """

    def __init__(self, socket):
        self.socket = socket
        self.context = None
        self._makefile_refs = 0
        self._closed = False
        self._exception = None
        self._keychain = None
        self._keychain_dir = None
        self._client_cert_chain = None

        # We save off the previously-configured timeout and then set it to
        # zero. This is done because we use select and friends to handle the
        # timeouts, but if we leave the timeout set on the lower socket then
        # Python will "kindly" call select on that socket again for us. Avoid
        # that by forcing the timeout to zero.
        self._timeout = self.socket.gettimeout()
        self.socket.settimeout(0)

    @contextlib.contextmanager
    def _raise_on_error(self):
        """
        A context manager that can be used to wrap calls that do I/O from
        SecureTransport. If any of the I/O callbacks hit an exception, this
        context manager will correctly propagate the exception after the fact.
        This avoids silently swallowing those exceptions.

        It also correctly forces the socket closed.
        """
        self._exception = None

        # We explicitly don't catch around this yield because in the unlikely
        # event that an exception was hit in the block we don't want to swallow
        # it.
        yield
        if self._exception is not None:
            exception, self._exception = self._exception, None
            self.close()
            raise exception

    def _set_ciphers(self):
        """
        Sets up the allowed ciphers. By default this matches the set in
        util.ssl_.DEFAULT_CIPHERS, at least as supported by macOS. This is done
        custom and doesn't allow changing at this time, mostly because parsing
        OpenSSL cipher strings is going to be a freaking nightmare.
        """
        ciphers = (Security.SSLCipherSuite * len(CIPHER_SUITES))(*CIPHER_SUITES)
        result = Security.SSLSetEnabledCiphers(
            self.context, ciphers, len(CIPHER_SUITES)
        )
        _assert_no_error(result)

    def _set_alpn_protocols(self, protocols):
        """
        Sets up the ALPN protocols on the context.
        """
        if not protocols:
            return
        protocols_arr = _create_cfstring_array(protocols)
        try:
            result = Security.SSLSetALPNProtocols(self.context, protocols_arr)
            _assert_no_error(result)
        finally:
            CoreFoundation.CFRelease(protocols_arr)

    def _custom_validate(self, verify, trust_bundle):
        """
        Called when we have set custom validation. We do this in two cases:
        first, when cert validation is entirely disabled; and second, when
        using a custom trust DB.
        Raises an SSLError if the connection is not trusted.
        """
        # If we disabled cert validation, just say: cool.
        if not verify:
            return

        successes = (
            SecurityConst.kSecTrustResultUnspecified,
            SecurityConst.kSecTrustResultProceed,
        )
        try:
            trust_result = self._evaluate_trust(trust_bundle)
            if trust_result in successes:
                return
            reason = "error code: %d" % (trust_result,)
        except Exception as e:
            # Do not trust on error
            reason = "exception: %r" % (e,)

        # SecureTransport does not send an alert nor shuts down the connection.
        rec = _build_tls_unknown_ca_alert(self.version())
        self.socket.sendall(rec)
        # close the connection immediately
        # l_onoff = 1, activate linger
        # l_linger = 0, linger for 0 seoncds
        opts = struct.pack("ii", 1, 0)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_LINGER, opts)
        self.close()
        raise ssl.SSLError("certificate verify failed, %s" % reason)

    def _evaluate_trust(self, trust_bundle):
        # We want data in memory, so load it up.
        if os.path.isfile(trust_bundle):
            with open(trust_bundle, "rb") as f:
                trust_bundle = f.read()

        cert_array = None
        trust = Security.SecTrustRef()

        try:
            # Get a CFArray that contains the certs we want.
            cert_array = _cert_array_from_pem(trust_bundle)

            # Ok, now the hard part. We want to get the SecTrustRef that ST has
            # created for this connection, shove our CAs into it, tell ST to
            # ignore everything else it knows, and then ask if it can build a
            # chain. This is a buuuunch of code.
            result = Security.SSLCopyPeerTrust(self.context, ctypes.byref(trust))
            _assert_no_error(result)
            if not trust:
                raise ssl.SSLError("Failed to copy trust reference")

            result = Security.SecTrustSetAnchorCertificates(trust, cert_array)
            _assert_no_error(result)

            result = Security.SecTrustSetAnchorCertificatesOnly(trust, True)
            _assert_no_error(result)

            trust_result = Security.SecTrustResultType()
            result = Security.SecTrustEvaluate(trust, ctypes.byref(trust_result))
            _assert_no_error(result)
        finally:
            if trust:
                CoreFoundation.CFRelease(trust)

            if cert_array is not None:
                CoreFoundation.CFRelease(cert_array)

        return trust_result.value

    def handshake(
        self,
        server_hostname,
        verify,
        trust_bundle,
        min_version,
        max_version,
        client_cert,
        client_key,
        client_key_passphrase,
        alpn_protocols,
    ):
        """
        Actually performs the TLS handshake. This is run automatically by
        wrapped socket, and shouldn't be needed in user code.
        """
        # First, we do the initial bits of connection setup. We need to create
        # a context, set its I/O funcs, and set the connection reference.
        self.context = Security.SSLCreateContext(
            None, SecurityConst.kSSLClientSide, SecurityConst.kSSLStreamType
        )
        result = Security.SSLSetIOFuncs(
            self.context, _read_callback_pointer, _write_callback_pointer
        )
        _assert_no_error(result)

        # Here we need to compute the handle to use. We do this by taking the
        # id of self modulo 2**31 - 1. If this is already in the dictionary, we
        # just keep incrementing by one until we find a free space.
        with _connection_ref_lock:
            handle = id(self) % 2147483647
            while handle in _connection_refs:
                handle = (handle + 1) % 2147483647
            _connection_refs[handle] = self

        result = Security.SSLSetConnection(self.context, handle)
        _assert_no_error(result)

        # If we have a server hostname, we should set that too.
        if server_hostname:
            if not isinstance(server_hostname, bytes):
                server_hostname = server_hostname.encode("utf-8")

            result = Security.SSLSetPeerDomainName(
                self.context, server_hostname, len(server_hostname)
            )
            _assert_no_error(result)

        # Setup the ciphers.
        self._set_ciphers()

        # Setup the ALPN protocols.
        self._set_alpn_protocols(alpn_protocols)

        # Set the minimum and maximum TLS versions.
        result = Security.SSLSetProtocolVersionMin(self.context, min_version)
        _assert_no_error(result)

        result = Security.SSLSetProtocolVersionMax(self.context, max_version)
        _assert_no_error(result)

        # If there's a trust DB, we need to use it. We do that by telling
        # SecureTransport to break on server auth. We also do that if we don't
        # want to validate the certs at all: we just won't actually do any
        # authing in that case.
        if not verify or trust_bundle is not None:
            result = Security.SSLSetSessionOption(
                self.context, SecurityConst.kSSLSessionOptionBreakOnServerAuth, True
            )
            _assert_no_error(result)

        # If there's a client cert, we need to use it.
        if client_cert:
            self._keychain, self._keychain_dir = _temporary_keychain()
            self._client_cert_chain = _load_client_cert_chain(
                self._keychain, client_cert, client_key
            )
            result = Security.SSLSetCertificate(self.context, self._client_cert_chain)
            _assert_no_error(result)

        while True:
            with self._raise_on_error():
                result = Security.SSLHandshake(self.context)

                if result == SecurityConst.errSSLWouldBlock:
                    raise socket.timeout("handshake timed out")
                elif result == SecurityConst.errSSLServerAuthCompleted:
                    self._custom_validate(verify, trust_bundle)
                    continue
                else:
                    _assert_no_error(result)
                    break

    def fileno(self):
        return self.socket.fileno()

    # Copy-pasted from Python 3.5 source code
    def _decref_socketios(self):
        if self._makefile_refs > 0:
            self._makefile_refs -= 1
        if self._closed:
            self.close()

    def recv(self, bufsiz):
        buffer = ctypes.create_string_buffer(bufsiz)
        bytes_read = self.recv_into(buffer, bufsiz)
        data = buffer[:bytes_read]
        return data

    def recv_into(self, buffer, nbytes=None):
        # Read short on EOF.
        if self._closed:
            return 0

        if nbytes is None:
            nbytes = len(buffer)

        buffer = (ctypes.c_char * nbytes).from_buffer(buffer)
        processed_bytes = ctypes.c_size_t(0)

        with self._raise_on_error():
            result = Security.SSLRead(
                self.context, buffer, nbytes, ctypes.byref(processed_bytes)
            )

        # There are some result codes that we want to treat as "not always
        # errors". Specifically, those are errSSLWouldBlock,
        # errSSLClosedGraceful, and errSSLClosedNoNotify.
        if result == SecurityConst.errSSLWouldBlock:
            # If we didn't process any bytes, then this was just a time out.
            # However, we can get errSSLWouldBlock in situations when we *did*
            # read some data, and in those cases we should just read "short"
            # and return.
            if processed_bytes.value == 0:
                # Timed out, no data read.
                raise socket.timeout("recv timed out")
        elif result in (
            SecurityConst.errSSLClosedGraceful,
            SecurityConst.errSSLClosedNoNotify,
        ):
            # The remote peer has closed this connection. We should do so as
            # well. Note that we don't actually return here because in
            # principle this could actually be fired along with return data.
            # It's unlikely though.
            self.close()
        else:
            _assert_no_error(result)

        # Ok, we read and probably succeeded. We should return whatever data
        # was actually read.
        return processed_bytes.value

    def settimeout(self, timeout):
        self._timeout = timeout

    def gettimeout(self):
        return self._timeout

    def send(self, data):
        processed_bytes = ctypes.c_size_t(0)

        with self._raise_on_error():
            result = Security.SSLWrite(
                self.context, data, len(data), ctypes.byref(processed_bytes)
            )

        if result == SecurityConst.errSSLWouldBlock and processed_bytes.value == 0:
            # Timed out
            raise socket.timeout("send timed out")
        else:
            _assert_no_error(result)

        # We sent, and probably succeeded. Tell them how much we sent.
        return processed_bytes.value

    def sendall(self, data):
        total_sent = 0
        while total_sent < len(data):
            sent = self.send(data[total_sent : total_sent + SSL_WRITE_BLOCKSIZE])
            total_sent += sent

    def shutdown(self):
        with self._raise_on_error():
            Security.SSLClose(self.context)

    def close(self):
        # TODO: should I do clean shutdown here? Do I have to?
        if self._makefile_refs < 1:
            self._closed = True
            if self.context:
                CoreFoundation.CFRelease(self.context)
                self.context = None
            if self._client_cert_chain:
                CoreFoundation.CFRelease(self._client_cert_chain)
                self._client_cert_chain = None
            if self._keychain:
                Security.SecKeychainDelete(self._keychain)
                CoreFoundation.CFRelease(self._keychain)
                shutil.rmtree(self._keychain_dir)
                self._keychain = self._keychain_dir = None
            return self.socket.close()
        else:
            self._makefile_refs -= 1

    def getpeercert(self, binary_form=False):
        # Urgh, annoying.
        #
        # Here's how we do this:
        #
        # 1. Call SSLCopyPeerTrust to get hold of the trust object for this
        #    connection.
        # 2. Call SecTrustGetCertificateAtIndex for index 0 to get the leaf.
        # 3. To get the CN, call SecCertificateCopyCommonName and process that
        #    string so that it's of the appropriate type.
        # 4. To get the SAN, we need to do something a bit more complex:
        #    a. Call SecCertificateCopyValues to get the data, requesting
        #       kSecOIDSubjectAltName.
        #    b. Mess about with this dictionary to try to get the SANs out.
        #
        # This is gross. Really gross. It's going to be a few hundred LoC extra
        # just to repeat something that SecureTransport can *already do*. So my
        # operating assumption at this time is that what we want to do is
        # instead to just flag to urllib3 that it shouldn't do its own hostname
        # validation when using SecureTransport.
        if not binary_form:
            raise ValueError("SecureTransport only supports dumping binary certs")
        trust = Security.SecTrustRef()
        certdata = None
        der_bytes = None

        try:
            # Grab the trust store.
            result = Security.SSLCopyPeerTrust(self.context, ctypes.byref(trust))
            _assert_no_error(result)
            if not trust:
                # Probably we haven't done the handshake yet. No biggie.
                return None

            cert_count = Security.SecTrustGetCertificateCount(trust)
            if not cert_count:
                # Also a case that might happen if we haven't handshaked.
                # Handshook? Handshaken?
                return None

            leaf = Security.SecTrustGetCertificateAtIndex(trust, 0)
            assert leaf

            # Ok, now we want the DER bytes.
            certdata = Security.SecCertificateCopyData(leaf)
            assert certdata

            data_length = CoreFoundation.CFDataGetLength(certdata)
            data_buffer = CoreFoundation.CFDataGetBytePtr(certdata)
            der_bytes = ctypes.string_at(data_buffer, data_length)
        finally:
            if certdata:
                CoreFoundation.CFRelease(certdata)
            if trust:
                CoreFoundation.CFRelease(trust)

        return der_bytes

    def version(self):
        protocol = Security.SSLProtocol()
        result = Security.SSLGetNegotiatedProtocolVersion(
            self.context, ctypes.byref(protocol)
        )
        _assert_no_error(result)
        if protocol.value == SecurityConst.kTLSProtocol13:
            raise ssl.SSLError("SecureTransport does not support TLS 1.3")
        elif protocol.value == SecurityConst.kTLSProtocol12:
            return "TLSv1.2"
        elif protocol.value == SecurityConst.kTLSProtocol11:
            return "TLSv1.1"
        elif protocol.value == SecurityConst.kTLSProtocol1:
            return "TLSv1"
        elif protocol.value == SecurityConst.kSSLProtocol3:
            return "SSLv3"
        elif protocol.value == SecurityConst.kSSLProtocol2:
            return "SSLv2"
        else:
            raise ssl.SSLError("Unknown TLS version: %r" % protocol)

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

    def makefile(self, mode="r", buffering=None, *args, **kwargs):
        # We disable buffering with SecureTransport because it conflicts with
        # the buffering that ST does internally (see issue #1153 for more).
        buffering = 0
        return backport_makefile(self, mode, buffering, *args, **kwargs)


WrappedSocket.makefile = makefile


class SecureTransportContext(object):
    """
    I am a wrapper class for the SecureTransport library, to translate the
    interface of the standard library ``SSLContext`` object to calls into
    SecureTransport.
    """

    def __init__(self, protocol):
        self._min_version, self._max_version = _protocol_to_min_max[protocol]
        self._options = 0
        self._verify = False
        self._trust_bundle = None
        self._client_cert = None
        self._client_key = None
        self._client_key_passphrase = None
        self._alpn_protocols = None

    @property
    def check_hostname(self):
        """
        SecureTransport cannot have its hostname checking disabled. For more,
        see the comment on getpeercert() in this file.
        """
        return True

    @check_hostname.setter
    def check_hostname(self, value):
        """
        SecureTransport cannot have its hostname checking disabled. For more,
        see the comment on getpeercert() in this file.
        """
        pass

    @property
    def options(self):
        # TODO: Well, crap.
        #
        # So this is the bit of the code that is the most likely to cause us
        # trouble. Essentially we need to enumerate all of the SSL options that
        # users might want to use and try to see if we can sensibly translate
        # them, or whether we should just ignore them.
        return self._options

    @options.setter
    def options(self, value):
        # TODO: Update in line with above.
        self._options = value

    @property
    def verify_mode(self):
        return ssl.CERT_REQUIRED if self._verify else ssl.CERT_NONE

    @verify_mode.setter
    def verify_mode(self, value):
        self._verify = True if value == ssl.CERT_REQUIRED else False

    def set_default_verify_paths(self):
        # So, this has to do something a bit weird. Specifically, what it does
        # is nothing.
        #
        # This means that, if we had previously had load_verify_locations
        # called, this does not undo that. We need to do that because it turns
        # out that the rest of the urllib3 code will attempt to load the
        # default verify paths if it hasn't been told about any paths, even if
        # the context itself was sometime earlier. We resolve that by just
        # ignoring it.
        pass

    def load_default_certs(self):
        return self.set_default_verify_paths()

    def set_ciphers(self, ciphers):
        # For now, we just require the default cipher string.
        if ciphers != util.ssl_.DEFAULT_CIPHERS:
            raise ValueError("SecureTransport doesn't support custom cipher strings")

    def load_verify_locations(self, cafile=None, capath=None, cadata=None):
        # OK, we only really support cadata and cafile.
        if capath is not None:
            raise ValueError("SecureTransport does not support cert directories")

        # Raise if cafile does not exist.
        if cafile is not None:
            with open(cafile):
                pass

        self._trust_bundle = cafile or cadata

    def load_cert_chain(self, certfile, keyfile=None, password=None):
        self._client_cert = certfile
        self._client_key = keyfile
        self._client_cert_passphrase = password

    def set_alpn_protocols(self, protocols):
        """
        Sets the ALPN protocols that will later be set on the context.

        Raises a NotImplementedError if ALPN is not supported.
        """
        if not hasattr(Security, "SSLSetALPNProtocols"):
            raise NotImplementedError(
                "SecureTransport supports ALPN only in macOS 10.12+"
            )
        self._alpn_protocols = [six.ensure_binary(p) for p in protocols]

    def wrap_socket(
        self,
        sock,
        server_side=False,
        do_handshake_on_connect=True,
        suppress_ragged_eofs=True,
        server_hostname=None,
    ):
        # So, what do we do here? Firstly, we assert some properties. This is a
        # stripped down shim, so there is some functionality we don't support.
        # See PEP 543 for the real deal.
        assert not server_side
        assert do_handshake_on_connect
        assert suppress_ragged_eofs

        # Ok, we're good to go. Now we want to create the wrapped socket object
        # and store it in the appropriate place.
        wrapped_socket = WrappedSocket(sock)

        # Now we can handshake
        wrapped_socket.handshake(
            server_hostname,
            self._verify,
            self._trust_bundle,
            self._min_version,
            self._max_version,
            self._client_cert,
            self._client_key,
            self._client_key_passphrase,
            self._alpn_protocols,
        )
        return wrapped_socket

# === NexusCore/openenv\Lib\site-packages\openai\resources\fine_tuning\jobs\jobs.py ===
# File generated from our OpenAPI spec by Stainless. See CONTRIBUTING.md for details.

from __future__ import annotations

from typing import Dict, Union, Iterable, Optional
from typing_extensions import Literal

import httpx

from .... import _legacy_response
from ...._types import NOT_GIVEN, Body, Query, Headers, NotGiven
from ...._utils import maybe_transform, async_maybe_transform
from ...._compat import cached_property
from .checkpoints import (
    Checkpoints,
    AsyncCheckpoints,
    CheckpointsWithRawResponse,
    AsyncCheckpointsWithRawResponse,
    CheckpointsWithStreamingResponse,
    AsyncCheckpointsWithStreamingResponse,
)
from ...._resource import SyncAPIResource, AsyncAPIResource
from ...._response import to_streamed_response_wrapper, async_to_streamed_response_wrapper
from ....pagination import SyncCursorPage, AsyncCursorPage
from ...._base_client import (
    AsyncPaginator,
    make_request_options,
)
from ....types.fine_tuning import job_list_params, job_create_params, job_list_events_params
from ....types.shared_params.metadata import Metadata
from ....types.fine_tuning.fine_tuning_job import FineTuningJob
from ....types.fine_tuning.fine_tuning_job_event import FineTuningJobEvent

__all__ = ["Jobs", "AsyncJobs"]


class Jobs(SyncAPIResource):
    @cached_property
    def checkpoints(self) -> Checkpoints:
        return Checkpoints(self._client)

    @cached_property
    def with_raw_response(self) -> JobsWithRawResponse:
        """
        This property can be used as a prefix for any HTTP method call to return
        the raw response object instead of the parsed content.

        For more information, see https://www.github.com/openai/openai-python#accessing-raw-response-data-eg-headers
        """
        return JobsWithRawResponse(self)

    @cached_property
    def with_streaming_response(self) -> JobsWithStreamingResponse:
        """
        An alternative to `.with_raw_response` that doesn't eagerly read the response body.

        For more information, see https://www.github.com/openai/openai-python#with_streaming_response
        """
        return JobsWithStreamingResponse(self)

    def create(
        self,
        *,
        model: Union[str, Literal["babbage-002", "davinci-002", "gpt-3.5-turbo", "gpt-4o-mini"]],
        training_file: str,
        hyperparameters: job_create_params.Hyperparameters | NotGiven = NOT_GIVEN,
        integrations: Optional[Iterable[job_create_params.Integration]] | NotGiven = NOT_GIVEN,
        metadata: Optional[Metadata] | NotGiven = NOT_GIVEN,
        method: job_create_params.Method | NotGiven = NOT_GIVEN,
        seed: Optional[int] | NotGiven = NOT_GIVEN,
        suffix: Optional[str] | NotGiven = NOT_GIVEN,
        validation_file: Optional[str] | NotGiven = NOT_GIVEN,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> FineTuningJob:
        """
        Creates a fine-tuning job which begins the process of creating a new model from
        a given dataset.

        Response includes details of the enqueued job including job status and the name
        of the fine-tuned models once complete.

        [Learn more about fine-tuning](https://platform.openai.com/docs/guides/model-optimization)

        Args:
          model: The name of the model to fine-tune. You can select one of the
              [supported models](https://platform.openai.com/docs/guides/fine-tuning#which-models-can-be-fine-tuned).

          training_file: The ID of an uploaded file that contains training data.

              See [upload file](https://platform.openai.com/docs/api-reference/files/create)
              for how to upload a file.

              Your dataset must be formatted as a JSONL file. Additionally, you must upload
              your file with the purpose `fine-tune`.

              The contents of the file should differ depending on if the model uses the
              [chat](https://platform.openai.com/docs/api-reference/fine-tuning/chat-input),
              [completions](https://platform.openai.com/docs/api-reference/fine-tuning/completions-input)
              format, or if the fine-tuning method uses the
              [preference](https://platform.openai.com/docs/api-reference/fine-tuning/preference-input)
              format.

              See the
              [fine-tuning guide](https://platform.openai.com/docs/guides/model-optimization)
              for more details.

          hyperparameters: The hyperparameters used for the fine-tuning job. This value is now deprecated
              in favor of `method`, and should be passed in under the `method` parameter.

          integrations: A list of integrations to enable for your fine-tuning job.

          metadata: Set of 16 key-value pairs that can be attached to an object. This can be useful
              for storing additional information about the object in a structured format, and
              querying for objects via API or the dashboard.

              Keys are strings with a maximum length of 64 characters. Values are strings with
              a maximum length of 512 characters.

          method: The method used for fine-tuning.

          seed: The seed controls the reproducibility of the job. Passing in the same seed and
              job parameters should produce the same results, but may differ in rare cases. If
              a seed is not specified, one will be generated for you.

          suffix: A string of up to 64 characters that will be added to your fine-tuned model
              name.

              For example, a `suffix` of "custom-model-name" would produce a model name like
              `ft:gpt-4o-mini:openai:custom-model-name:7p4lURel`.

          validation_file: The ID of an uploaded file that contains validation data.

              If you provide this file, the data is used to generate validation metrics
              periodically during fine-tuning. These metrics can be viewed in the fine-tuning
              results file. The same data should not be present in both train and validation
              files.

              Your dataset must be formatted as a JSONL file. You must upload your file with
              the purpose `fine-tune`.

              See the
              [fine-tuning guide](https://platform.openai.com/docs/guides/model-optimization)
              for more details.

          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request, in seconds
        """
        return self._post(
            "/fine_tuning/jobs",
            body=maybe_transform(
                {
                    "model": model,
                    "training_file": training_file,
                    "hyperparameters": hyperparameters,
                    "integrations": integrations,
                    "metadata": metadata,
                    "method": method,
                    "seed": seed,
                    "suffix": suffix,
                    "validation_file": validation_file,
                },
                job_create_params.JobCreateParams,
            ),
            options=make_request_options(
                extra_headers=extra_headers, extra_query=extra_query, extra_body=extra_body, timeout=timeout
            ),
            cast_to=FineTuningJob,
        )

    def retrieve(
        self,
        fine_tuning_job_id: str,
        *,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> FineTuningJob:
        """
        Get info about a fine-tuning job.

        [Learn more about fine-tuning](https://platform.openai.com/docs/guides/model-optimization)

        Args:
          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request, in seconds
        """
        if not fine_tuning_job_id:
            raise ValueError(f"Expected a non-empty value for `fine_tuning_job_id` but received {fine_tuning_job_id!r}")
        return self._get(
            f"/fine_tuning/jobs/{fine_tuning_job_id}",
            options=make_request_options(
                extra_headers=extra_headers, extra_query=extra_query, extra_body=extra_body, timeout=timeout
            ),
            cast_to=FineTuningJob,
        )

    def list(
        self,
        *,
        after: str | NotGiven = NOT_GIVEN,
        limit: int | NotGiven = NOT_GIVEN,
        metadata: Optional[Dict[str, str]] | NotGiven = NOT_GIVEN,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> SyncCursorPage[FineTuningJob]:
        """
        List your organization's fine-tuning jobs

        Args:
          after: Identifier for the last job from the previous pagination request.

          limit: Number of fine-tuning jobs to retrieve.

          metadata: Optional metadata filter. To filter, use the syntax `metadata[k]=v`.
              Alternatively, set `metadata=null` to indicate no metadata.

          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request, in seconds
        """
        return self._get_api_list(
            "/fine_tuning/jobs",
            page=SyncCursorPage[FineTuningJob],
            options=make_request_options(
                extra_headers=extra_headers,
                extra_query=extra_query,
                extra_body=extra_body,
                timeout=timeout,
                query=maybe_transform(
                    {
                        "after": after,
                        "limit": limit,
                        "metadata": metadata,
                    },
                    job_list_params.JobListParams,
                ),
            ),
            model=FineTuningJob,
        )

    def cancel(
        self,
        fine_tuning_job_id: str,
        *,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> FineTuningJob:
        """
        Immediately cancel a fine-tune job.

        Args:
          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request, in seconds
        """
        if not fine_tuning_job_id:
            raise ValueError(f"Expected a non-empty value for `fine_tuning_job_id` but received {fine_tuning_job_id!r}")
        return self._post(
            f"/fine_tuning/jobs/{fine_tuning_job_id}/cancel",
            options=make_request_options(
                extra_headers=extra_headers, extra_query=extra_query, extra_body=extra_body, timeout=timeout
            ),
            cast_to=FineTuningJob,
        )

    def list_events(
        self,
        fine_tuning_job_id: str,
        *,
        after: str | NotGiven = NOT_GIVEN,
        limit: int | NotGiven = NOT_GIVEN,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> SyncCursorPage[FineTuningJobEvent]:
        """
        Get status updates for a fine-tuning job.

        Args:
          after: Identifier for the last event from the previous pagination request.

          limit: Number of events to retrieve.

          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request, in seconds
        """
        if not fine_tuning_job_id:
            raise ValueError(f"Expected a non-empty value for `fine_tuning_job_id` but received {fine_tuning_job_id!r}")
        return self._get_api_list(
            f"/fine_tuning/jobs/{fine_tuning_job_id}/events",
            page=SyncCursorPage[FineTuningJobEvent],
            options=make_request_options(
                extra_headers=extra_headers,
                extra_query=extra_query,
                extra_body=extra_body,
                timeout=timeout,
                query=maybe_transform(
                    {
                        "after": after,
                        "limit": limit,
                    },
                    job_list_events_params.JobListEventsParams,
                ),
            ),
            model=FineTuningJobEvent,
        )

    def pause(
        self,
        fine_tuning_job_id: str,
        *,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> FineTuningJob:
        """
        Pause a fine-tune job.

        Args:
          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request, in seconds
        """
        if not fine_tuning_job_id:
            raise ValueError(f"Expected a non-empty value for `fine_tuning_job_id` but received {fine_tuning_job_id!r}")
        return self._post(
            f"/fine_tuning/jobs/{fine_tuning_job_id}/pause",
            options=make_request_options(
                extra_headers=extra_headers, extra_query=extra_query, extra_body=extra_body, timeout=timeout
            ),
            cast_to=FineTuningJob,
        )

    def resume(
        self,
        fine_tuning_job_id: str,
        *,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> FineTuningJob:
        """
        Resume a fine-tune job.

        Args:
          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request, in seconds
        """
        if not fine_tuning_job_id:
            raise ValueError(f"Expected a non-empty value for `fine_tuning_job_id` but received {fine_tuning_job_id!r}")
        return self._post(
            f"/fine_tuning/jobs/{fine_tuning_job_id}/resume",
            options=make_request_options(
                extra_headers=extra_headers, extra_query=extra_query, extra_body=extra_body, timeout=timeout
            ),
            cast_to=FineTuningJob,
        )


class AsyncJobs(AsyncAPIResource):
    @cached_property
    def checkpoints(self) -> AsyncCheckpoints:
        return AsyncCheckpoints(self._client)

    @cached_property
    def with_raw_response(self) -> AsyncJobsWithRawResponse:
        """
        This property can be used as a prefix for any HTTP method call to return
        the raw response object instead of the parsed content.

        For more information, see https://www.github.com/openai/openai-python#accessing-raw-response-data-eg-headers
        """
        return AsyncJobsWithRawResponse(self)

    @cached_property
    def with_streaming_response(self) -> AsyncJobsWithStreamingResponse:
        """
        An alternative to `.with_raw_response` that doesn't eagerly read the response body.

        For more information, see https://www.github.com/openai/openai-python#with_streaming_response
        """
        return AsyncJobsWithStreamingResponse(self)

    async def create(
        self,
        *,
        model: Union[str, Literal["babbage-002", "davinci-002", "gpt-3.5-turbo", "gpt-4o-mini"]],
        training_file: str,
        hyperparameters: job_create_params.Hyperparameters | NotGiven = NOT_GIVEN,
        integrations: Optional[Iterable[job_create_params.Integration]] | NotGiven = NOT_GIVEN,
        metadata: Optional[Metadata] | NotGiven = NOT_GIVEN,
        method: job_create_params.Method | NotGiven = NOT_GIVEN,
        seed: Optional[int] | NotGiven = NOT_GIVEN,
        suffix: Optional[str] | NotGiven = NOT_GIVEN,
        validation_file: Optional[str] | NotGiven = NOT_GIVEN,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> FineTuningJob:
        """
        Creates a fine-tuning job which begins the process of creating a new model from
        a given dataset.

        Response includes details of the enqueued job including job status and the name
        of the fine-tuned models once complete.

        [Learn more about fine-tuning](https://platform.openai.com/docs/guides/model-optimization)

        Args:
          model: The name of the model to fine-tune. You can select one of the
              [supported models](https://platform.openai.com/docs/guides/fine-tuning#which-models-can-be-fine-tuned).

          training_file: The ID of an uploaded file that contains training data.

              See [upload file](https://platform.openai.com/docs/api-reference/files/create)
              for how to upload a file.

              Your dataset must be formatted as a JSONL file. Additionally, you must upload
              your file with the purpose `fine-tune`.

              The contents of the file should differ depending on if the model uses the
              [chat](https://platform.openai.com/docs/api-reference/fine-tuning/chat-input),
              [completions](https://platform.openai.com/docs/api-reference/fine-tuning/completions-input)
              format, or if the fine-tuning method uses the
              [preference](https://platform.openai.com/docs/api-reference/fine-tuning/preference-input)
              format.

              See the
              [fine-tuning guide](https://platform.openai.com/docs/guides/model-optimization)
              for more details.

          hyperparameters: The hyperparameters used for the fine-tuning job. This value is now deprecated
              in favor of `method`, and should be passed in under the `method` parameter.

          integrations: A list of integrations to enable for your fine-tuning job.

          metadata: Set of 16 key-value pairs that can be attached to an object. This can be useful
              for storing additional information about the object in a structured format, and
              querying for objects via API or the dashboard.

              Keys are strings with a maximum length of 64 characters. Values are strings with
              a maximum length of 512 characters.

          method: The method used for fine-tuning.

          seed: The seed controls the reproducibility of the job. Passing in the same seed and
              job parameters should produce the same results, but may differ in rare cases. If
              a seed is not specified, one will be generated for you.

          suffix: A string of up to 64 characters that will be added to your fine-tuned model
              name.

              For example, a `suffix` of "custom-model-name" would produce a model name like
              `ft:gpt-4o-mini:openai:custom-model-name:7p4lURel`.

          validation_file: The ID of an uploaded file that contains validation data.

              If you provide this file, the data is used to generate validation metrics
              periodically during fine-tuning. These metrics can be viewed in the fine-tuning
              results file. The same data should not be present in both train and validation
              files.

              Your dataset must be formatted as a JSONL file. You must upload your file with
              the purpose `fine-tune`.

              See the
              [fine-tuning guide](https://platform.openai.com/docs/guides/model-optimization)
              for more details.

          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request, in seconds
        """
        return await self._post(
            "/fine_tuning/jobs",
            body=await async_maybe_transform(
                {
                    "model": model,
                    "training_file": training_file,
                    "hyperparameters": hyperparameters,
                    "integrations": integrations,
                    "metadata": metadata,
                    "method": method,
                    "seed": seed,
                    "suffix": suffix,
                    "validation_file": validation_file,
                },
                job_create_params.JobCreateParams,
            ),
            options=make_request_options(
                extra_headers=extra_headers, extra_query=extra_query, extra_body=extra_body, timeout=timeout
            ),
            cast_to=FineTuningJob,
        )

    async def retrieve(
        self,
        fine_tuning_job_id: str,
        *,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> FineTuningJob:
        """
        Get info about a fine-tuning job.

        [Learn more about fine-tuning](https://platform.openai.com/docs/guides/model-optimization)

        Args:
          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request, in seconds
        """
        if not fine_tuning_job_id:
            raise ValueError(f"Expected a non-empty value for `fine_tuning_job_id` but received {fine_tuning_job_id!r}")
        return await self._get(
            f"/fine_tuning/jobs/{fine_tuning_job_id}",
            options=make_request_options(
                extra_headers=extra_headers, extra_query=extra_query, extra_body=extra_body, timeout=timeout
            ),
            cast_to=FineTuningJob,
        )

    def list(
        self,
        *,
        after: str | NotGiven = NOT_GIVEN,
        limit: int | NotGiven = NOT_GIVEN,
        metadata: Optional[Dict[str, str]] | NotGiven = NOT_GIVEN,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> AsyncPaginator[FineTuningJob, AsyncCursorPage[FineTuningJob]]:
        """
        List your organization's fine-tuning jobs

        Args:
          after: Identifier for the last job from the previous pagination request.

          limit: Number of fine-tuning jobs to retrieve.

          metadata: Optional metadata filter. To filter, use the syntax `metadata[k]=v`.
              Alternatively, set `metadata=null` to indicate no metadata.

          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request, in seconds
        """
        return self._get_api_list(
            "/fine_tuning/jobs",
            page=AsyncCursorPage[FineTuningJob],
            options=make_request_options(
                extra_headers=extra_headers,
                extra_query=extra_query,
                extra_body=extra_body,
                timeout=timeout,
                query=maybe_transform(
                    {
                        "after": after,
                        "limit": limit,
                        "metadata": metadata,
                    },
                    job_list_params.JobListParams,
                ),
            ),
            model=FineTuningJob,
        )

    async def cancel(
        self,
        fine_tuning_job_id: str,
        *,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> FineTuningJob:
        """
        Immediately cancel a fine-tune job.

        Args:
          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request, in seconds
        """
        if not fine_tuning_job_id:
            raise ValueError(f"Expected a non-empty value for `fine_tuning_job_id` but received {fine_tuning_job_id!r}")
        return await self._post(
            f"/fine_tuning/jobs/{fine_tuning_job_id}/cancel",
            options=make_request_options(
                extra_headers=extra_headers, extra_query=extra_query, extra_body=extra_body, timeout=timeout
            ),
            cast_to=FineTuningJob,
        )

    def list_events(
        self,
        fine_tuning_job_id: str,
        *,
        after: str | NotGiven = NOT_GIVEN,
        limit: int | NotGiven = NOT_GIVEN,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> AsyncPaginator[FineTuningJobEvent, AsyncCursorPage[FineTuningJobEvent]]:
        """
        Get status updates for a fine-tuning job.

        Args:
          after: Identifier for the last event from the previous pagination request.

          limit: Number of events to retrieve.

          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request, in seconds
        """
        if not fine_tuning_job_id:
            raise ValueError(f"Expected a non-empty value for `fine_tuning_job_id` but received {fine_tuning_job_id!r}")
        return self._get_api_list(
            f"/fine_tuning/jobs/{fine_tuning_job_id}/events",
            page=AsyncCursorPage[FineTuningJobEvent],
            options=make_request_options(
                extra_headers=extra_headers,
                extra_query=extra_query,
                extra_body=extra_body,
                timeout=timeout,
                query=maybe_transform(
                    {
                        "after": after,
                        "limit": limit,
                    },
                    job_list_events_params.JobListEventsParams,
                ),
            ),
            model=FineTuningJobEvent,
        )

    async def pause(
        self,
        fine_tuning_job_id: str,
        *,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> FineTuningJob:
        """
        Pause a fine-tune job.

        Args:
          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request, in seconds
        """
        if not fine_tuning_job_id:
            raise ValueError(f"Expected a non-empty value for `fine_tuning_job_id` but received {fine_tuning_job_id!r}")
        return await self._post(
            f"/fine_tuning/jobs/{fine_tuning_job_id}/pause",
            options=make_request_options(
                extra_headers=extra_headers, extra_query=extra_query, extra_body=extra_body, timeout=timeout
            ),
            cast_to=FineTuningJob,
        )

    async def resume(
        self,
        fine_tuning_job_id: str,
        *,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> FineTuningJob:
        """
        Resume a fine-tune job.

        Args:
          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request, in seconds
        """
        if not fine_tuning_job_id:
            raise ValueError(f"Expected a non-empty value for `fine_tuning_job_id` but received {fine_tuning_job_id!r}")
        return await self._post(
            f"/fine_tuning/jobs/{fine_tuning_job_id}/resume",
            options=make_request_options(
                extra_headers=extra_headers, extra_query=extra_query, extra_body=extra_body, timeout=timeout
            ),
            cast_to=FineTuningJob,
        )


class JobsWithRawResponse:
    def __init__(self, jobs: Jobs) -> None:
        self._jobs = jobs

        self.create = _legacy_response.to_raw_response_wrapper(
            jobs.create,
        )
        self.retrieve = _legacy_response.to_raw_response_wrapper(
            jobs.retrieve,
        )
        self.list = _legacy_response.to_raw_response_wrapper(
            jobs.list,
        )
        self.cancel = _legacy_response.to_raw_response_wrapper(
            jobs.cancel,
        )
        self.list_events = _legacy_response.to_raw_response_wrapper(
            jobs.list_events,
        )
        self.pause = _legacy_response.to_raw_response_wrapper(
            jobs.pause,
        )
        self.resume = _legacy_response.to_raw_response_wrapper(
            jobs.resume,
        )

    @cached_property
    def checkpoints(self) -> CheckpointsWithRawResponse:
        return CheckpointsWithRawResponse(self._jobs.checkpoints)


class AsyncJobsWithRawResponse:
    def __init__(self, jobs: AsyncJobs) -> None:
        self._jobs = jobs

        self.create = _legacy_response.async_to_raw_response_wrapper(
            jobs.create,
        )
        self.retrieve = _legacy_response.async_to_raw_response_wrapper(
            jobs.retrieve,
        )
        self.list = _legacy_response.async_to_raw_response_wrapper(
            jobs.list,
        )
        self.cancel = _legacy_response.async_to_raw_response_wrapper(
            jobs.cancel,
        )
        self.list_events = _legacy_response.async_to_raw_response_wrapper(
            jobs.list_events,
        )
        self.pause = _legacy_response.async_to_raw_response_wrapper(
            jobs.pause,
        )
        self.resume = _legacy_response.async_to_raw_response_wrapper(
            jobs.resume,
        )

    @cached_property
    def checkpoints(self) -> AsyncCheckpointsWithRawResponse:
        return AsyncCheckpointsWithRawResponse(self._jobs.checkpoints)


class JobsWithStreamingResponse:
    def __init__(self, jobs: Jobs) -> None:
        self._jobs = jobs

        self.create = to_streamed_response_wrapper(
            jobs.create,
        )
        self.retrieve = to_streamed_response_wrapper(
            jobs.retrieve,
        )
        self.list = to_streamed_response_wrapper(
            jobs.list,
        )
        self.cancel = to_streamed_response_wrapper(
            jobs.cancel,
        )
        self.list_events = to_streamed_response_wrapper(
            jobs.list_events,
        )
        self.pause = to_streamed_response_wrapper(
            jobs.pause,
        )
        self.resume = to_streamed_response_wrapper(
            jobs.resume,
        )

    @cached_property
    def checkpoints(self) -> CheckpointsWithStreamingResponse:
        return CheckpointsWithStreamingResponse(self._jobs.checkpoints)


class AsyncJobsWithStreamingResponse:
    def __init__(self, jobs: AsyncJobs) -> None:
        self._jobs = jobs

        self.create = async_to_streamed_response_wrapper(
            jobs.create,
        )
        self.retrieve = async_to_streamed_response_wrapper(
            jobs.retrieve,
        )
        self.list = async_to_streamed_response_wrapper(
            jobs.list,
        )
        self.cancel = async_to_streamed_response_wrapper(
            jobs.cancel,
        )
        self.list_events = async_to_streamed_response_wrapper(
            jobs.list_events,
        )
        self.pause = async_to_streamed_response_wrapper(
            jobs.pause,
        )
        self.resume = async_to_streamed_response_wrapper(
            jobs.resume,
        )

    @cached_property
    def checkpoints(self) -> AsyncCheckpointsWithStreamingResponse:
        return AsyncCheckpointsWithStreamingResponse(self._jobs.checkpoints)

# === NexusCore/openenv\Lib\site-packages\pygments\lexers\_googlesql_builtins.py ===
"""
    pygments.lexers._googlesql_builtins
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    Autogenerated data files for the GoogleSQL lexer.

    :copyright: Copyright 2006-2025 by the Pygments team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

constants = [
    'FALSE',
    'NULL',
    'TRUE',
    'UNKNOWN',
]

# Everything below this line is auto-generated from the GoogleSQL source code.
# ----------------------------------------------------------------------------

functionnames = [
    'ABS',
    'ACOS',
    'ACOSH',
    'AEAD.DECRYPT_BYTES',
    'AEAD.DECRYPT_STRING',
    'AEAD.ENCRYPT',
    'AEAD.ENVELOPE_DECRYPT_BYTES',
    'AEAD.ENVELOPE_DECRYPT_STRING',
    'AEAD.ENVELOPE_ENCRYPT',
    'ALL_DIFFERENT',
    'ANON_AVG',
    'ANON_COUNT',
    'ANON_COUNT',
    'ANON_PERCENTILE_CONT',
    'ANON_QUANTILES',
    'ANON_STDDEV_POP',
    'ANON_SUM',
    'ANON_VAR_POP',
    'ANY_VALUE',
    'APPROX_COSINE_DISTANCE',
    'APPROX_COUNT_DISTINCT',
    'APPROX_DOT_PRODUCT',
    'APPROX_EUCLIDEAN_DISTANCE',
    'APPROX_QUANTILES',
    'APPROX_TOP_COUNT',
    'APPROX_TOP_SUM',
    'ARRAY[KEY()]',
    'ARRAY[SAFE_KEY()]',
    'ARRAY_AGG',
    'ARRAY_AVG',
    'ARRAY_CONCAT',
    'ARRAY_CONCAT_AGG',
    'ARRAY_FILTER',
    'ARRAY_FIND',
    'ARRAY_FIND_ALL',
    'ARRAY_FIRST',
    'ARRAY_FIRST_N',
    'ARRAY_INCLUDES',
    'ARRAY_INCLUDES_ALL',
    'ARRAY_INCLUDES_ANY',
    'ARRAY_IS_DISTINCT',
    'ARRAY_LAST',
    'ARRAY_LAST_N',
    'ARRAY_LENGTH',
    'ARRAY_MAX',
    'ARRAY_MIN',
    'ARRAY_OFFSET',
    'ARRAY_OFFSETS',
    'ARRAY_REMOVE_FIRST_N',
    'ARRAY_REMOVE_LAST_N',
    'ARRAY_REVERSE',
    'ARRAY_SLICE',
    'ARRAY_SUM',
    'ARRAY_TO_STRING',
    'ARRAY_TRANSFORM',
    'ARRAY_ZIP',
    'ASCII',
    'ASIN',
    'ASINH',
    'ATAN',
    'ATAN2',
    'ATANH',
    'AVG',
    'BIT_AND',
    'BIT_COUNT',
    'BIT_OR',
    'BIT_XOR',
    'BOOL',
    'BOOL_ARRAY',
    'BYTE_LENGTH',
    'CASE',
    'CAST',
    'CBRT',
    'CEIL',
    'CEILING',
    'CHARACTER_LENGTH',
    'CHAR_LENGTH',
    'CHR',
    'COALESCE',
    'CODE_POINTS_TO_BYTES',
    'CODE_POINTS_TO_STRING',
    'COLLATE',
    'CONCAT',
    'CORR',
    'COS',
    'COSH',
    'COSINE_DISTANCE',
    'COT',
    'COTH',
    'COUNT',
    'COUNT(*)',
    'COUNTIF',
    'COVAR_POP',
    'COVAR_SAMP',
    'CSC',
    'CSCH',
    'CUME_DIST',
    'CURRENT_DATE',
    'CURRENT_DATETIME',
    'CURRENT_TIME',
    'CURRENT_TIMESTAMP',
    'D3A_COUNT.EXTRACT',
    'D3A_COUNT.INIT',
    'D3A_COUNT.MERGE',
    'D3A_COUNT.MERGE_PARTIAL',
    'D3A_COUNT.TO_HLL',
    'DATE',
    'DATETIME',
    'DATETIME_ADD',
    'DATETIME_BUCKET',
    'DATETIME_DIFF',
    'DATETIME_SUB',
    'DATETIME_TRUNC',
    'DATE_ADD',
    'DATE_BUCKET',
    'DATE_DIFF',
    'DATE_FROM_UNIX_DATE',
    'DATE_SUB',
    'DATE_TRUNC',
    'DENSE_RANK',
    'DESTINATION_NODE_ID',
    'DETERMINISTIC_DECRYPT_BYTES',
    'DETERMINISTIC_DECRYPT_STRING',
    'DETERMINISTIC_ENCRYPT',
    'DIV',
    'DOT_PRODUCT',
    'EDGES',
    'EDIT_DISTANCE',
    'ELEMENTWISE_AVG',
    'ELEMENTWISE_SUM',
    'ELEMENT_DEFINITION_NAME',
    'ELEMENT_ID',
    'ENDS_WITH',
    'ENUM_VALUE_DESCRIPTOR_PROTO',
    'ERROR',
    'EUCLIDEAN_DISTANCE',
    'EXP',
    'EXTRACT',
    'EXTRACT_FOR_DP_APPROX_COUNT_DISTINCT',
    'FARM_FINGERPRINT',
    'FILTER_FIELDS',
    'FIRST_VALUE',
    'FLATTEN',
    'FLOAT32',
    'FLOAT32_ARRAY',
    'FLOAT64',
    'FLOAT64_ARRAY',
    'FLOOR',
    'FORMAT',
    'FORMAT_DATE',
    'FORMAT_DATETIME',
    'FORMAT_TIME',
    'FORMAT_TIMESTAMP',
    'FROM_BASE32',
    'FROM_BASE64',
    'FROM_HEX',
    'GENERATE_ARRAY',
    'GENERATE_DATE_ARRAY',
    'GENERATE_RANGE_ARRAY',
    'GENERATE_TIMESTAMP_ARRAY',
    'GENERATE_UUID',
    'GREATEST',
    'GROUPING',
    'HLL_COUNT.EXTRACT',
    'HLL_COUNT.INIT',
    'HLL_COUNT.MERGE',
    'HLL_COUNT.MERGE_PARTIAL',
    'IEEE_DIVIDE',
    'IF',
    'IFERROR',
    'IFNULL',
    'IN UNNEST',
    'INITCAP',
    'INIT_FOR_DP_APPROX_COUNT_DISTINCT',
    'INSTR',
    'INT64',
    'INT64_ARRAY',
    'IS DESTINATION OF',
    'IS DISTINCT FROM',
    'IS NOT DISTINCT FROM',
    'IS SOURCE OF',
    'ISERROR',
    'IS_ACYCLIC',
    'IS_INF',
    'IS_NAN',
    'IS_SIMPLE',
    'IS_TRAIL',
    'JSON_ARRAY',
    'JSON_ARRAY_APPEND',
    'JSON_ARRAY_INSERT',
    'JSON_CONTAINS',
    'JSON_EXTRACT',
    'JSON_EXTRACT_ARRAY',
    'JSON_EXTRACT_SCALAR',
    'JSON_EXTRACT_STRING_ARRAY',
    'JSON_KEYS',
    'JSON_OBJECT',
    'JSON_QUERY',
    'JSON_QUERY_ARRAY',
    'JSON_REMOVE',
    'JSON_SET',
    'JSON_STRIP_NULLS',
    'JSON_TYPE',
    'JSON_VALUE',
    'JSON_VALUE_ARRAY',
    'JUSTIFY_DAYS',
    'JUSTIFY_HOURS',
    'JUSTIFY_INTERVAL',
    'KEYS.ADD_KEY_FROM_RAW_BYTES',
    'KEYS.KEYSET_CHAIN',
    'KEYS.KEYSET_FROM_JSON',
    'KEYS.KEYSET_LENGTH',
    'KEYS.KEYSET_TO_JSON',
    'KEYS.NEW_KEYSET',
    'KEYS.NEW_WRAPPED_KEYSET',
    'KEYS.REWRAP_KEYSET',
    'KEYS.ROTATE_KEYSET',
    'KEYS.ROTATE_WRAPPED_KEYSET',
    'KLL_QUANTILES.EXTRACT_FLOAT64',
    'KLL_QUANTILES.EXTRACT_INT64',
    'KLL_QUANTILES.EXTRACT_POINT_FLOAT64',
    'KLL_QUANTILES.EXTRACT_POINT_INT64',
    'KLL_QUANTILES.INIT_FLOAT64',
    'KLL_QUANTILES.INIT_INT64',
    'KLL_QUANTILES.MERGE_FLOAT64',
    'KLL_QUANTILES.MERGE_INT64',
    'KLL_QUANTILES.MERGE_PARTIAL',
    'KLL_QUANTILES.MERGE_POINT_FLOAT64',
    'KLL_QUANTILES.MERGE_POINT_INT64',
    'L1_NORM',
    'L2_NORM',
    'LABELS',
    'LAG',
    'LAST_DAY',
    'LAST_VALUE',
    'LAX_BOOL',
    'LAX_BOOL_ARRAY',
    'LAX_FLOAT32',
    'LAX_FLOAT32_ARRAY',
    'LAX_FLOAT64',
    'LAX_FLOAT64_ARRAY',
    'LAX_INT64',
    'LAX_INT64_ARRAY',
    'LAX_STRING',
    'LAX_STRING_ARRAY',
    'LEAD',
    'LEAST',
    'LEFT',
    'LENGTH',
    'LIKE ALL',
    'LIKE ALL UNNEST',
    'LIKE ANY',
    'LIKE ANY UNNEST',
    'LN',
    'LOG',
    'LOG10',
    'LOGICAL_AND',
    'LOGICAL_OR',
    'LOWER',
    'LPAD',
    'LTRIM',
    'MAKE_INTERVAL',
    'MANHATTAN_DISTANCE',
    'MAP_CARDINALITY',
    'MAP_CONTAINS_KEY',
    'MAP_DELETE',
    'MAP_EMPTY',
    'MAP_ENTRIES_SORTED',
    'MAP_ENTRIES_UNSORTED',
    'MAP_FILTER',
    'MAP_FROM_ARRAY',
    'MAP_GET',
    'MAP_INSERT',
    'MAP_INSERT_OR_REPLACE',
    'MAP_KEYS_SORTED',
    'MAP_KEYS_UNSORTED',
    'MAP_REPLACE',
    'MAP_VALUES_SORTED',
    'MAP_VALUES_SORTED_BY_KEY',
    'MAP_VALUES_UNSORTED',
    'MAX',
    'MD5',
    'MERGE_PARTIAL_FOR_DP_APPROX_COUNT_DISTINCT',
    'MIN',
    'MOD',
    'NET.HOST',
    'NET.IPV4_FROM_INT64',
    'NET.IPV4_TO_INT64',
    'NET.IP_FROM_STRING',
    'NET.IP_NET_MASK',
    'NET.IP_TO_STRING',
    'NET.IP_TRUNC',
    'NET.PUBLIC_SUFFIX',
    'NET.REG_DOMAIN',
    'NET.SAFE_IP_FROM_STRING',
    'NEW_UUID',
    'NODES',
    'NORMALIZE',
    'NORMALIZE_AND_CASEFOLD',
    'NOT LIKE ALL',
    'NOT LIKE ALL UNNEST',
    'NOT LIKE ANY',
    'NOT LIKE ANY UNNEST',
    'NTH_VALUE',
    'NTILE',
    'NULLIF',
    'NULLIFERROR',
    'NULLIFZERO',
    'OCTET_LENGTH',
    'OFFSET',
    'ORDINAL',
    'PARSE_BIGNUMERIC',
    'PARSE_DATE',
    'PARSE_DATETIME',
    'PARSE_JSON',
    'PARSE_NUMERIC',
    'PARSE_TIME',
    'PARSE_TIMESTAMP',
    'PATH',
    'PATH_FIRST',
    'PATH_LAST',
    'PATH_LENGTH',
    'PERCENTILE_CONT',
    'PERCENTILE_DISC',
    'PERCENT_RANK',
    'PI',
    'PIVOT',
    'PI_BIGNUMERIC',
    'PI_NUMERIC',
    'POW',
    'POWER',
    'PROPERTY_EXISTS',
    'PROPERTY_NAMES',
    'PROTO_MAP_CONTAINS_KEY',
    'PROTO_MODIFY_MAP',
    'RAND',
    'RANGE',
    'RANGE_BUCKET',
    'RANGE_CONTAINS',
    'RANGE_END',
    'RANGE_INTERSECT',
    'RANGE_IS_END_UNBOUNDED',
    'RANGE_IS_START_UNBOUNDED',
    'RANGE_OVERLAPS',
    'RANGE_START',
    'RANK',
    'REGEXP_CONTAINS',
    'REGEXP_EXTRACT',
    'REGEXP_EXTRACT_ALL',
    'REGEXP_INSTR',
    'REGEXP_REPLACE',
    'REGEXP_SUBSTR',
    'REPEAT',
    'REPLACE',
    'REVERSE',
    'RIGHT',
    'ROUND',
    'ROW_NUMBER',
    'RPAD',
    'RTRIM',
    'S2_CELLIDFROMPOINT',
    'S2_COVERINGCELLIDS',
    'SAFE_ADD',
    'SAFE_CONVERT_BYTES_TO_STRING',
    'SAFE_DIVIDE',
    'SAFE_MULTIPLY',
    'SAFE_NEGATE',
    'SAFE_OFFSET',
    'SAFE_ORDINAL',
    'SAFE_SUBTRACT',
    'SAFE_TO_JSON',
    'SAME',
    'SEC',
    'SECH',
    'SESSION_USER',
    'SHA1',
    'SHA256',
    'SHA512',
    'SIGN',
    'SIN',
    'SINH',
    'SOUNDEX',
    'SOURCE_NODE_ID',
    'SPLIT',
    'SPLIT_SUBSTR',
    'SQRT',
    'STARTS_WITH',
    'STDDEV',
    'STDDEV_POP',
    'STDDEV_SAMP',
    'STRING',
    'STRING_AGG',
    'STRING_ARRAY',
    'STRPOS',
    'ST_ANGLE',
    'ST_AREA',
    'ST_ASBINARY',
    'ST_ASGEOJSON',
    'ST_ASKML',
    'ST_ASTEXT',
    'ST_AZIMUTH',
    'ST_BOUNDARY',
    'ST_BOUNDINGBOX',
    'ST_BUFFER',
    'ST_BUFFERWITHTOLERANCE',
    'ST_CENTROID',
    'ST_CENTROID_AGG',
    'ST_CLOSESTPOINT',
    'ST_CLUSTERDBSCAN',
    'ST_CONTAINS',
    'ST_CONVEXHULL',
    'ST_COVEREDBY',
    'ST_COVERS',
    'ST_DIFFERENCE',
    'ST_DIMENSION',
    'ST_DISJOINT',
    'ST_DISTANCE',
    'ST_DUMP',
    'ST_DUMPPOINTS',
    'ST_DWITHIN',
    'ST_ENDPOINT',
    'ST_EQUALS',
    'ST_EXTENT',
    'ST_EXTERIORRING',
    'ST_GEOGFROM',
    'ST_GEOGFROMGEOJSON',
    'ST_GEOGFROMKML',
    'ST_GEOGFROMTEXT',
    'ST_GEOGFROMWKB',
    'ST_GEOGPOINT',
    'ST_GEOGPOINTFROMGEOHASH',
    'ST_GEOHASH',
    'ST_GEOMETRYTYPE',
    'ST_HAUSDORFFDISTANCE',
    'ST_HAUSDORFFDWITHIN',
    'ST_INTERIORRINGS',
    'ST_INTERSECTION',
    'ST_INTERSECTS',
    'ST_INTERSECTSBOX',
    'ST_ISCLOSED',
    'ST_ISCOLLECTION',
    'ST_ISEMPTY',
    'ST_ISRING',
    'ST_LENGTH',
    'ST_LINEINTERPOLATEPOINT',
    'ST_LINELOCATEPOINT',
    'ST_LINESUBSTRING',
    'ST_MAKELINE',
    'ST_MAKEPOLYGON',
    'ST_MAKEPOLYGONORIENTED',
    'ST_MAXDISTANCE',
    'ST_NEAREST_NEIGHBORS',
    'ST_NPOINTS',
    'ST_NUMGEOMETRIES',
    'ST_NUMPOINTS',
    'ST_PERIMETER',
    'ST_POINTN',
    'ST_SIMPLIFY',
    'ST_SNAPTOGRID',
    'ST_STARTPOINT',
    'ST_TOUCHES',
    'ST_UNARYUNION',
    'ST_UNION',
    'ST_UNION_AGG',
    'ST_WITHIN',
    'ST_X',
    'ST_Y',
    'SUBSTR',
    'SUBSTRING',
    'SUM',
    'TAN',
    'TANH',
    'TIME',
    'TIMESTAMP',
    'TIMESTAMP_ADD',
    'TIMESTAMP_BUCKET',
    'TIMESTAMP_DIFF',
    'TIMESTAMP_FROM_UNIX_MICROS',
    'TIMESTAMP_FROM_UNIX_MILLIS',
    'TIMESTAMP_FROM_UNIX_SECONDS',
    'TIMESTAMP_MICROS',
    'TIMESTAMP_MILLIS',
    'TIMESTAMP_SECONDS',
    'TIMESTAMP_SUB',
    'TIMESTAMP_TRUNC',
    'TIME_ADD',
    'TIME_DIFF',
    'TIME_SUB',
    'TIME_TRUNC',
    'TO_BASE32',
    'TO_BASE64',
    'TO_CODE_POINTS',
    'TO_HEX',
    'TO_JSON',
    'TO_JSON_STRING',
    'TRANSLATE',
    'TRIM',
    'TRUNC',
    'TYPEOF',
    'UNICODE',
    'UNIX_DATE',
    'UNIX_MICROS',
    'UNIX_MILLIS',
    'UNIX_SECONDS',
    'UNNEST',
    'UNPIVOT',
    'UPPER',
    'VARIANCE',
    'VAR_POP',
    'VAR_SAMP',
    'ZEROIFNULL',
]

keywords = [
    'ABORT',
    'ACCESS',
    'ACTION',
    'ACYCLIC',
    'ADD',
    'AFTER',
    'AGGREGATE',
    'ALL',
    'ALTER',
    'ALWAYS',
    'ANALYZE',
    'AND',
    'ANY',
    'APPROX',
    'ARE',
    'AS',
    'ASC',
    'ASCENDING',
    'ASSERT',
    'ASSERT_ROWS_MODIFIED',
    'AT',
    'BATCH',
    'BEGIN',
    'BETWEEN',
    'BIGDECIMAL',
    'BREAK',
    'BY',
    'CALL',
    'CASCADE',
    'CASE',
    'CAST',
    'CHECK',
    'CLAMPED',
    'CLONE',
    'CLUSTER',
    'COLLATE',
    'COLUMN',
    'COLUMNS',
    'COMMIT',
    'CONFLICT',
    'CONNECTION',
    'CONSTANT',
    'CONSTRAINT',
    'CONTAINS',
    'CONTINUE',
    'COPY',
    'CORRESPONDING',
    'CREATE',
    'CROSS',
    'CUBE',
    'CURRENT',
    'CYCLE',
    'DATA',
    'DATABASE',
    'DAY',
    'DAYOFWEEK',
    'DAYOFYEAR',
    'DECIMAL',
    'DECLARE',
    'DEFAULT',
    'DEFINE',
    'DEFINER',
    'DELETE',
    'DELETION',
    'DEPTH',
    'DESC',
    'DESCENDING',
    'DESCRIBE',
    'DESCRIPTOR',
    'DESTINATION',
    'DETERMINISTIC',
    'DISTINCT',
    'DO',
    'DROP',
    'EDGE',
    'ELSE',
    'ELSEIF',
    'END',
    'ENFORCED',
    'ERROR',
    'ESCAPE',
    'EXCEPT',
    'EXCEPTION',
    'EXCLUDE',
    'EXECUTE',
    'EXISTS',
    'EXPLAIN',
    'EXPORT',
    'EXTEND',
    'EXTERNAL',
    'EXTRACT',
    'FALSE',
    'FETCH',
    'FIELD',
    'FILES',
    'FILL',
    'FILTER',
    'FIRST',
    'FOLLOWING',
    'FOR',
    'FOREIGN',
    'FORK',
    'FORMAT',
    'FRIDAY',
    'FROM',
    'FULL',
    'FUNCTION',
    'GENERATED',
    'GRANT',
    'GRAPH',
    'GRAPH_TABLE',
    'GROUP',
    'GROUPING',
    'GROUPS',
    'GROUP_ROWS',
    'HAS',
    'HASH',
    'HAVING',
    'HIDDEN',
    'HOUR',
    'IDENTITY',
    'IF',
    'IGNORE',
    'IMMEDIATE',
    'IMMUTABLE',
    'IMPORT',
    'IN',
    'INCLUDE',
    'INCREMENT',
    'INDEX',
    'INNER',
    'INOUT',
    'INPUT',
    'INSERT',
    'INTERLEAVE',
    'INTERSECT',
    'INTO',
    'INVOKER',
    'IS',
    'ISOLATION',
    'ISOWEEK ',
    'ISOYEAR',
    'ITERATE',
    'JOIN',
    'KEY',
    'LABEL',
    'LABELED',
    'LANGUAGE',
    'LAST',
    'LATERAL',
    'LEAVE',
    'LEFT',
    'LET',
    'LEVEL',
    'LIKE',
    'LIMIT',
    'LOAD',
    'LOG',
    'LOOKUP',
    'LOOP',
    'MACRO',
    'MATCH',
    'MATCHED',
    'MATCH_RECOGNIZE',
    'MATERIALIZED',
    'MAX',
    'MAXVALUE',
    'MEASURES',
    'MERGE',
    'MESSAGE',
    'METADATA',
    'MICROSECOND',
    'MILLISECOND',
    'MIN',
    'MINUTE',
    'MINVALUE',
    'MODEL',
    'MODULE',
    'MONDAY',
    'MONTH',
    'NAME',
    'NANOSECOND',
    'NATURAL',
    'NEW',
    'NEXT',
    'NO',
    'NODE',
    'NOT',
    'NOTHING',
    'NULL',
    'NULLS',
    'NULL_FILTERED',
    'OF',
    'OFFSET',
    'ON',
    'ONEOF_CASE',
    'ONLY',
    'OPTIONAL',
    'OPTIONS',
    'OR',
    'ORDER',
    'OUT',
    'OUTER',
    'OUTPUT',
    'OVER',
    'OVERWRITE',
    'PARENT',
    'PARTITION',
    'PARTITIONS',
    'PAST',
    'PATH',
    'PATHS',
    'PATTERN',
    'PERCENT',
    'PIVOT',
    'POLICIES',
    'POLICY',
    'PRECEDING',
    'PRIMARY',
    'PRIVATE',
    'PRIVILEGE',
    'PRIVILEGES',
    'PROCEDURE',
    'PROJECT',
    'PROPERTIES',
    'PROPERTY',
    'PUBLIC',
    'QUALIFY',
    'QUARTER',
    'RAISE',
    'RAW',
    'READ',
    'RECURSIVE',
    'REFERENCES',
    'REMOTE',
    'REMOVE',
    'RENAME',
    'REPEAT',
    'REPEATABLE',
    'REPLACE',
    'REPLACE_FIELDS',
    'REPLICA',
    'REPORT',
    'RESPECT',
    'RESTRICT',
    'RESTRICTION',
    'RETURN',
    'RETURNS',
    'REVOKE',
    'RIGHT',
    'ROLLBACK',
    'ROLLUP',
    'ROW',
    'ROWS',
    'RUN',
    'SAFE_CAST',
    'SATURDAY',
    'SCHEMA',
    'SEARCH',
    'SECOND ',
    'SECURITY',
    'SELECT',
    'SEQUENCE',
    'SET',
    'SETS',
    'SHORTEST',
    'SHOW',
    'SIMPLE',
    'SKIP',
    'SNAPSHOT',
    'SOME',
    'SOURCE',
    'SQL',
    'STABLE',
    'START',
    'STATIC_DESCRIBE',
    'STORED',
    'STORING',
    'STRICT',
    'SUNDAY',
    'SYSTEM',
    'SYSTEM_TIME',
    'TABLE',
    'TABLES',
    'TABLESAMPLE',
    'TARGET',
    'TEMP',
    'TEMPORARY',
    'THEN',
    'THURSDAY',
    'TO',
    'TRAIL',
    'TRANSACTION',
    'TRANSFORM',
    'TREAT',
    'TRUE',
    'TRUNCATE',
    'TUESDAY',
    'TYPE',
    'UNBOUNDED',
    'UNDROP',
    'UNION',
    'UNIQUE',
    'UNKNOWN',
    'UNNEST',
    'UNPIVOT',
    'UNTIL',
    'UPDATE',
    'USING',
    'VALUE',
    'VALUES',
    'VECTOR',
    'VIEW',
    'VIEWS',
    'VOLATILE',
    'WALK',
    'WEDNESDAY',
    'WEEK',
    'WEIGHT',
    'WHEN',
    'WHERE',
    'WHILE',
    'WINDOW',
    'WITH',
    'WITHIN',
    'WRITE',
    'YEAR',
    'ZONE',
]

operators = [
    '!=',
    '&',
    '*',
    '+',
    '-',
    '/',
    '<',
    '<<',
    '<=',
    '=',
    '>',
    '>=',
    '>>',
    '^',
    '|',
    '||',
    '~',
]

types = [
    'ARRAY',
    'BIGNUMERIC',
    'BOOL',
    'BYTES',
    'DATE',
    'DATETIME',
    'DOUBLE',
    'ENUM',
    'EXTENDED',
    'FLOAT',
    'GEOGRAPHY',
    'GRAPH_ELEMENT',
    'GRAPH_PATH',
    'INT32',
    'INT64',
    'INTERVAL',
    'JSON',
    'MAP',
    'MEASURE',
    'NUMERIC',
    'PROTO',
    'RANGE',
    'STRING',
    'STRUCT',
    'TIME',
    'TIMESTAMP',
    'TIMESTAMP_PICOS',
    'TOKENLIST',
    'UINT32',
    'UINT64',
    'UUID',
]

# === NexusCore/openenv\Lib\site-packages\win32com\test\testPyComTest.py ===
# NOTE - Still seems to be a leak here somewhere
# gateway count doesn't hit zero.  Hence the print statements!

import sys

sys.coinit_flags = 0  # Must be free-threaded!
import datetime
import decimal
import os
import time

import pythoncom
import pywintypes
import win32com
import win32com.client.connect
import win32com.test.util
import win32timezone
import winerror
from win32com.client import (
    VARIANT,
    CastTo,
    DispatchBaseClass,
    Record,
    constants,
    register_record_class,
)

importMsg = "**** PyCOMTest is not installed ***\n  PyCOMTest is a Python test specific COM client and server.\n  It is likely this server is not installed on this machine\n  To install the server, you must get the win32com sources\n  and build it using MS Visual C++"

# This test uses a Python implemented COM server - ensure correctly registered.
win32com.test.util.RegisterPythonServer(
    os.path.join(os.path.dirname(__file__), "..", "servers", "test_pycomtest.py"),
    "Python.Test.PyCOMTest",
)

from win32com.client import gencache

try:
    gencache.EnsureModule("{6BCDCB60-5605-11D0-AE5F-CADD4C000000}", 0, 1, 1)
except pythoncom.com_error:
    print("The PyCOMTest module can not be located or generated.")
    print(importMsg)
    raise RuntimeError(importMsg)

# We had a bg where RegisterInterfaces would fail if gencache had
# already been run - exercise that here
from win32com import universal

universal.RegisterInterfaces("{6BCDCB60-5605-11D0-AE5F-CADD4C000000}", 0, 1, 1)

verbose = 0


# Subclasses of pythoncom.com_record.
# Registration is performed in 'TestGenerated'.
class TestStruct1(pythoncom.com_record):
    __slots__ = ()
    TLBID = "{6BCDCB60-5605-11D0-AE5F-CADD4C000000}"
    MJVER = 1
    MNVER = 1
    LCID = 0
    GUID = "{7A4CE6A7-7959-4E85-A3C0-B41442FF0F67}"


class TestStruct2(pythoncom.com_record):
    __slots__ = ()
    TLBID = "{6BCDCB60-5605-11D0-AE5F-CADD4C000000}"
    MJVER = 1
    MNVER = 1
    LCID = 0
    GUID = "{78F0EA07-B7CF-42EA-A251-A4C6269F76AF}"


# We don't need to stick with the struct name in the TypeLibrry for the subclass name.
# The following class has the same GUID as TestStruct2 from the TypeLibrary.
class ArrayOfStructsTestStruct(pythoncom.com_record):
    __slots__ = ()
    TLBID = "{6BCDCB60-5605-11D0-AE5F-CADD4C000000}"
    MJVER = 1
    MNVER = 1
    LCID = 0
    GUID = "{78F0EA07-B7CF-42EA-A251-A4C6269F76AF}"


class NotInTypeLibraryTestStruct(pythoncom.com_record):
    __slots__ = ()
    TLBID = "{6BCDCB60-5605-11D0-AE5F-CADD4C000000}"
    MJVER = 1
    MNVER = 1
    LCID = 0
    GUID = "{79BB6AC3-12DE-4AC5-88AC-225C29A58043}"


def check_get_set(func, arg):
    got = func(arg)
    assert got == arg, f"{func} failed - expected {arg!r}, got {got!r}"


def check_get_set_raises(exc, func, arg):
    try:
        got = func(arg)
    except exc as e:
        pass  # what we expect!
    else:
        raise AssertionError(
            f"{func} with arg {arg!r} didn't raise {exc} - returned {got!r}"
        )


def progress(*args):
    if verbose:
        for arg in args:
            print(arg, end=" ")
        print()


def TestApplyResult(fn, args, result):
    try:
        fnName = str(fn).split()[1]
    except:
        fnName = str(fn)
    progress("Testing ", fnName)
    pref = "function " + fnName
    rc = fn(*args)
    assert rc == result, f"{pref} failed - result not {result!r} but {rc!r}"


def TestConstant(constName, pyConst):
    try:
        comConst = getattr(constants, constName)
    except:
        raise AssertionError(f"Constant {constName} missing")
    assert (
        comConst == pyConst
    ), f"Constant value wrong for {constName} - got {comConst}, wanted {pyConst}"


# Simple handler class.  This demo only fires one event.
class RandomEventHandler:
    def _Init(self):
        self.fireds = {}

    def OnFire(self, no):
        try:
            self.fireds[no] += 1
        except KeyError:
            self.fireds[no] = 0

    def OnFireWithNamedParams(self, no, a_bool, out1, out2):
        # This test exists mainly to help with an old bug, where named
        # params would come in reverse.
        Missing = pythoncom.Missing
        if no is not Missing:
            # We know our impl called 'OnFire' with the same ID
            assert no in self.fireds
            assert no + 1 == out1, "expecting 'out1' param to be ID+1"
            assert no + 2 == out2, "expecting 'out2' param to be ID+2"
        # The middle must be a boolean.
        assert a_bool is Missing or isinstance(a_bool, bool), "middle param not a bool"
        return out1 + 2, out2 + 2

    def _DumpFireds(self):
        if not self.fireds:
            print("ERROR: Nothing was received!")
        for firedId, no in self.fireds.items():
            progress("ID %d fired %d times" % (firedId, no))


# Test everything which can be tested using both the "dynamic" and "generated"
# COM objects (or when there are very subtle differences)
def TestCommon(o, is_generated):
    progress("Getting counter")
    counter = o.GetSimpleCounter()
    TestCounter(counter, is_generated)

    progress("Checking default args")
    rc = o.TestOptionals()
    assert rc[:-1] == ("def", 0, 1) and abs(rc[-1] - 3.14) <= 0.01, (
        "Did not get the optional values correctly",
        rc,
    )
    rc = o.TestOptionals("Hi", 2, 3, 1.1)
    assert rc[:-1] == ("Hi", 2, 3) and abs(rc[-1] - 1.1) <= 0.01, (
        "Did not get the specified optional values correctly",
        rc,
    )
    rc = o.TestOptionals2(0)
    assert rc == (0, "", 1), ("Did not get the optional2 values correctly", rc)
    rc = o.TestOptionals2(1.1, "Hi", 2)
    assert rc[1:] == ("Hi", 2) and abs(rc[0] - 1.1) <= 0.01, (
        "Did not get the specified optional2 values correctly",
        rc,
    )

    progress("Checking getting/passing IUnknown")
    check_get_set(o.GetSetUnknown, o)
    progress("Checking getting/passing IDispatch")
    # This might be called with either the interface or the CoClass - but these
    # functions always return from the interface.
    expected_class = o.__class__
    # CoClass instances have `default_interface`
    expected_class = getattr(expected_class, "default_interface", expected_class)
    assert isinstance(
        o.GetSetDispatch(o), expected_class
    ), f"GetSetDispatch failed: {o.GetSetDispatch(o)!r}"
    progress("Checking getting/passing IDispatch of known type")
    expected_class = o.__class__
    expected_class = getattr(expected_class, "default_interface", expected_class)
    assert o.GetSetInterface(o).__class__ == expected_class, "GetSetDispatch failed"

    progress("Checking misc args")
    check_get_set(o.GetSetVariant, 4)
    check_get_set(o.GetSetVariant, "foo")
    check_get_set(o.GetSetVariant, o)

    # signed/unsigned.
    check_get_set(o.GetSetInt, 0)
    check_get_set(o.GetSetInt, -1)
    check_get_set(o.GetSetInt, 1)

    check_get_set(o.GetSetUnsignedInt, 0)
    check_get_set(o.GetSetUnsignedInt, 1)
    check_get_set(o.GetSetUnsignedInt, 0x80000000)
    # -1 is a special case - we accept a negative int (silently converting to unsigned)
    # but when getting it back we convert it to a long.
    assert o.GetSetUnsignedInt(-1) == 0xFFFFFFFF, "unsigned -1 failed"

    check_get_set(o.GetSetLong, 0)
    check_get_set(o.GetSetLong, -1)
    check_get_set(o.GetSetLong, 1)

    check_get_set(o.GetSetUnsignedLong, 0)
    check_get_set(o.GetSetUnsignedLong, 1)
    check_get_set(o.GetSetUnsignedLong, 0x80000000)
    # -1 is a special case - see above.
    assert o.GetSetUnsignedLong(-1) == 0xFFFFFFFF, "unsigned -1 failed"

    # We want to explicitly test > 32 bits.
    # 'maxsize+1' is no good on 64bit platforms as it's 65 bits!
    big = 2147483647
    for l in big, big + 1, 1 << 65:
        check_get_set(o.GetSetVariant, l)

    progress("Checking structs")
    r = o.GetStruct()
    assert r.int_value == 99 and str(r.str_value) == "Hello from C++"
    assert o.DoubleString("foo") == "foofoo"

    progress("Checking var args")
    o.SetVarArgs("Hi", "There", "From", "Python", 1)
    assert o.GetLastVarArgs() == (
        "Hi",
        "There",
        "From",
        "Python",
        1,
    ), f"VarArgs failed -{o.GetLastVarArgs()}"

    progress("Checking arrays")
    l = []
    TestApplyResult(o.SetVariantSafeArray, (l,), len(l))
    l = [1, 2, 3, 4]
    TestApplyResult(o.SetVariantSafeArray, (l,), len(l))
    TestApplyResult(
        o.CheckVariantSafeArray,
        (
            (
                1,
                2,
                3,
                4,
            ),
        ),
        1,
    )

    # and binary
    TestApplyResult(o.SetBinSafeArray, (memoryview(b"foo\0bar"),), 7)

    progress("Checking properties")
    o.LongProp = 3
    assert (
        o.LongProp == o.IntProp == 3
    ), f"Property value wrong - got {o.LongProp}/{o.IntProp}"
    o.LongProp = o.IntProp = -3
    assert (
        o.LongProp == o.IntProp == -3
    ), f"Property value wrong - got {o.LongProp}/{o.IntProp}"
    # This number fits in an unsigned long.  Attempting to set it to a normal
    # long will involve overflow, which is to be expected. But we do
    # expect it to work in a property explicitly a VT_UI4.
    check = 3 * 10**9
    o.ULongProp = check
    assert (
        o.ULongProp == check
    ), f"Property value wrong - got {o.ULongProp} (expected {check})"
    TestApplyResult(o.Test, ("Unused", 99), 1)  # A bool function
    TestApplyResult(o.Test, ("Unused", -1), 1)  # A bool function
    TestApplyResult(o.Test, ("Unused", True), 1)  # A bool function
    TestApplyResult(o.Test, ("Unused", 0), 0)
    TestApplyResult(o.Test, ("Unused", False), 0)

    assert o.DoubleString("foo") == "foofoo"

    TestConstant("ULongTest1", 0xFFFFFFFF)
    TestConstant("ULongTest2", 0x7FFFFFFF)
    TestConstant("LongTest1", -0x7FFFFFFF)
    TestConstant("LongTest2", 0x7FFFFFFF)
    TestConstant("UCharTest", 255)
    TestConstant("CharTest", -1)
    # 'Hello World', but the 'r' is the "Registered" sign (\xae)
    TestConstant("StringTest", "Hello Wo\xaeld")

    progress("Checking dates and times")
    # For now *all* times passed must be tz-aware.
    now = win32timezone.now()
    # but conversion to and from a VARIANT loses sub-second...
    now = now.replace(microsecond=0)
    later = now + datetime.timedelta(seconds=1)
    TestApplyResult(o.EarliestDate, (now, later), now)

    # The below used to fail with `ValueError: microsecond must be in 0..999999` - see #1655
    # https://planetcalc.com/7027/ says that float is: Sun, 25 Mar 1951 7:23:49 am
    assert o.MakeDate(18712.308206013888) == datetime.datetime.fromisoformat(
        "1951-03-25 07:23:49+00:00"
    )

    progress("Checking currency")
    # currency.
    pythoncom.__future_currency__ = 1
    assert o.CurrencyProp == 0, f"Expecting 0, got {o.CurrencyProp!r}"
    for val in ("1234.5678", "1234.56", "1234"):
        o.CurrencyProp = decimal.Decimal(val)
        assert o.CurrencyProp == decimal.Decimal(val), f"{val} got {o.CurrencyProp!r}"
    v1 = decimal.Decimal("1234.5678")
    TestApplyResult(o.DoubleCurrency, (v1,), v1 * 2)

    v2 = decimal.Decimal("9012.3456")
    TestApplyResult(o.AddCurrencies, (v1, v2), v1 + v2)

    TestTrickyTypesWithVariants(o, is_generated)
    progress("Checking win32com.client.VARIANT")
    TestPyVariant(o, is_generated)


def TestTrickyTypesWithVariants(o, is_generated):
    # Test tricky stuff with type handling and generally only works with
    # "generated" support but can be worked around using VARIANT.
    if is_generated:
        got = o.TestByRefVariant(2)
    else:
        v = VARIANT(pythoncom.VT_BYREF | pythoncom.VT_VARIANT, 2)
        o.TestByRefVariant(v)
        got = v.value
    assert got == 4, "TestByRefVariant failed"

    if is_generated:
        got = o.TestByRefString("Foo")
    else:
        v = VARIANT(pythoncom.VT_BYREF | pythoncom.VT_BSTR, "Foo")
        o.TestByRefString(v)
        got = v.value
    assert got == "FooFoo", "TestByRefString failed"

    # check we can pass ints as a VT_UI1
    vals = [1, 2, 3, 4]
    if is_generated:
        arg = vals
    else:
        arg = VARIANT(pythoncom.VT_ARRAY | pythoncom.VT_UI1, vals)
    TestApplyResult(o.SetBinSafeArray, (arg,), len(vals))

    # safearrays of doubles and floats
    vals = [0, 1.1, 2.2, 3.3]
    if is_generated:
        arg = vals
    else:
        arg = VARIANT(pythoncom.VT_ARRAY | pythoncom.VT_R8, vals)
    TestApplyResult(o.SetDoubleSafeArray, (arg,), len(vals))

    if is_generated:
        arg = vals
    else:
        arg = VARIANT(pythoncom.VT_ARRAY | pythoncom.VT_R4, vals)
    TestApplyResult(o.SetFloatSafeArray, (arg,), len(vals))

    vals = [1.1, 2.2, 3.3, 4.4]
    expected = (1.1 * 2, 2.2 * 2, 3.3 * 2, 4.4 * 2)
    if is_generated:
        TestApplyResult(o.ChangeDoubleSafeArray, (vals,), expected)
    else:
        arg = VARIANT(pythoncom.VT_BYREF | pythoncom.VT_ARRAY | pythoncom.VT_R8, vals)
        o.ChangeDoubleSafeArray(arg)
        assert arg.value == expected, "ChangeDoubleSafeArray got the wrong value"

    if is_generated:
        got = o.DoubleInOutString("foo")
    else:
        v = VARIANT(pythoncom.VT_BYREF | pythoncom.VT_BSTR, "foo")
        o.DoubleInOutString(v)
        got = v.value
    assert got == "foofoo", got

    val = decimal.Decimal("1234.5678")
    if is_generated:
        got = o.DoubleCurrencyByVal(val)
    else:
        v = VARIANT(pythoncom.VT_BYREF | pythoncom.VT_CY, val)
        o.DoubleCurrencyByVal(v)
        got = v.value
    assert got == val * 2


def TestDynamic():
    progress("Testing Dynamic")
    import win32com.client.dynamic

    o = win32com.client.dynamic.DumbDispatch("PyCOMTest.PyCOMTest")
    TestCommon(o, False)

    counter = win32com.client.dynamic.DumbDispatch("PyCOMTest.SimpleCounter")
    TestCounter(counter, False)

    # Dynamic doesn't know this should be an int, so we get a COM
    # TypeMismatch error.
    try:
        check_get_set_raises(ValueError, o.GetSetInt, "foo")
        raise AssertionError("no exception raised")
    except pythoncom.com_error as exc:
        if exc.hresult != winerror.DISP_E_TYPEMISMATCH:
            raise

    arg1 = VARIANT(pythoncom.VT_R4 | pythoncom.VT_BYREF, 2.0)
    arg2 = VARIANT(pythoncom.VT_BOOL | pythoncom.VT_BYREF, True)
    arg3 = VARIANT(pythoncom.VT_I4 | pythoncom.VT_BYREF, 4)
    o.TestInOut(arg1, arg2, arg3)
    assert arg1.value == 4.0, arg1
    assert arg2.value == False
    assert arg3.value == 8

    # damn - props with params don't work for dynamic objects :(
    # o.SetParamProp(0, 1)
    # assert o.ParamProp(0) == 1, o.paramProp(0)


def TestStructByref(o, r):
    progress("Checking struct byref as [ in, out ] parameter")
    mod_r = o.ModifyStruct(r)
    # If 'TestStruct1' was registered as an instantiable subclass
    # of pythoncom.com_record, the return value should have this type.
    if isinstance(r, TestStruct1):
        assert type(mod_r) is TestStruct1
    else:
        assert type(mod_r) is pythoncom.com_record
    # We expect the input value to stay unchanged
    assert r.int_value == 99 and str(r.str_value) == "Hello from C++"
    # and the return value to reflect the modifications performed on the COM server side
    assert (
        mod_r.int_value == 100
        and str(mod_r.str_value) == "Nothing is as constant as change"
    )


def TestArrayOfStructs(o, test_rec):
    progress("Testing struct with SAFEARRAY(VT_RECORD) fields.")
    rec_list = []
    for i in range(3):
        # If 'ArrayOfStructsTestStruct' and 'TestStruct1' were registered as instantiable
        # subclasses of pythoncom.com_record, we expect to work with these types.
        if isinstance(test_rec, ArrayOfStructsTestStruct):
            rec = TestStruct1()
            assert type(rec) is TestStruct1
        else:
            rec = Record("TestStruct1", o)
            assert type(rec) is pythoncom.com_record
        rec.str_value = "This is record number"
        rec.int_value = i + 1
        rec_list.append(rec)
    test_rec.array_of_records = rec_list
    test_rec.rec_count = i + 1
    assert o.VerifyArrayOfStructs(test_rec)


def TestGenerated():
    # Create an instance of the server.
    from win32com.client.gencache import EnsureDispatch

    o = EnsureDispatch("PyCOMTest.PyCOMTest")
    TestCommon(o, True)

    counter = EnsureDispatch("PyCOMTest.SimpleCounter")
    TestCounter(counter, True)

    # This dance lets us get a CoClass even though it's not explicitly registered.
    # This is `CoPyComTest`
    from win32com.client.CLSIDToClass import GetClass

    coclass_o = GetClass("{8EE0C520-5605-11D0-AE5F-CADD4C000000}")()
    TestCommon(coclass_o, True)

    # Test the regression reported in #1753
    assert bool(coclass_o)

    # This is `CoSimpleCounter` and the counter tests should work.
    coclass = GetClass("{B88DD310-BAE8-11D0-AE86-76F2C1000000}")()
    TestCounter(coclass, True)

    # Test plain pythoncom.com_record structs.
    progress("Testing baseclass pythoncom.com_record structs.")
    r = o.GetStruct()
    assert type(r) is pythoncom.com_record
    TestStructByref(o, r)
    test_rec = Record("TestStruct2", o)
    assert type(test_rec) is pythoncom.com_record
    TestArrayOfStructs(o, test_rec)

    progress("Testing registration of pythoncom.com_record subclasses.")
    # Instantiating a pythoncom.com_record subclass, which has proper GUID attributes,
    # does raise a TypeError, as long as we have not registered it.
    try:
        r_sub = TestStruct1()
    except TypeError:
        pass
    except Exception as e:
        raise AssertionError from e
    else:
        raise AssertionError
    # Register the subclasses in pythoncom.
    register_record_class(TestStruct1)
    register_record_class(ArrayOfStructsTestStruct)
    # Now the type of the instance is the registered subclass.
    r_sub = TestStruct1()
    assert type(r_sub) is TestStruct1
    # Now also the 'Record' factory function returns an instance of the registered subtype.
    r_sub = Record("TestStruct1", o)
    assert type(r_sub) is TestStruct1
    # It should not be possible to register multiple classes with the same GUID, e.g.
    # 'TestStruct2' has the same GUID class attribute value as 'ArrayOfStructsTestStruct'.
    check_get_set_raises(ValueError, register_record_class, TestStruct2)
    # Also registering a class with a GUID that is not in the TypeLibrary should fail.
    check_get_set_raises(TypeError, register_record_class, NotInTypeLibraryTestStruct)

    # Perform the 'Byref' and 'ArrayOfStruct tests using the registered subclasses.
    progress("Testing subclasses of pythoncom.com_record.")
    r = o.GetStruct()
    # After 'TestStruct1' was registered as an instantiable subclass
    # of pythoncom.com_record, the return value should have this type.
    assert type(r) is TestStruct1
    TestStructByref(o, r)
    test_rec = ArrayOfStructsTestStruct()
    assert type(test_rec) is ArrayOfStructsTestStruct
    TestArrayOfStructs(o, test_rec)

    # Test initialization of registered pythoncom.com_record subclasses.
    progress("Testing initialization of pythoncom.com_record subclasses.")
    buf = o.GetStruct().__reduce__()[1][5]
    test_rec = TestStruct1(buf)
    assert test_rec.int_value == 99 and str(test_rec.str_value) == "Hello from C++"

    # XXX - this is failing in dynamic tests, but should work fine.
    i1, i2 = o.GetMultipleInterfaces()
    # Yay - is now an instance returned!
    assert isinstance(i1, DispatchBaseClass) and isinstance(
        i2, DispatchBaseClass
    ), f"GetMultipleInterfaces did not return instances - got '{i1}', '{i2}'"
    del i1
    del i2

    # Generated knows to only pass a 32bit int, so should fail.
    check_get_set_raises(OverflowError, o.GetSetInt, 0x80000000)
    check_get_set_raises(OverflowError, o.GetSetLong, 0x80000000)

    # Generated knows this should be an int, so raises ValueError
    check_get_set_raises(ValueError, o.GetSetInt, "foo")
    check_get_set_raises(ValueError, o.GetSetLong, "foo")

    # Pass some non-sequence objects to our array decoder, and watch it fail.
    try:
        o.SetVariantSafeArray("foo")
        raise AssertionError("Expected a type error")
    except TypeError:
        pass
    try:
        o.SetVariantSafeArray(666)
        raise AssertionError("Expected a type error")
    except TypeError:
        pass

    o.GetSimpleSafeArray(None)
    TestApplyResult(o.GetSimpleSafeArray, (None,), tuple(range(10)))
    resultCheck = tuple(range(5)), tuple(range(10)), tuple(range(20))
    TestApplyResult(o.GetSafeArrays, (None, None, None), resultCheck)

    l = []
    TestApplyResult(o.SetIntSafeArray, (l,), len(l))
    l = [1, 2, 3, 4]
    TestApplyResult(o.SetIntSafeArray, (l,), len(l))
    ll = [1, 2, 3, 0x100000000]
    TestApplyResult(o.SetLongLongSafeArray, (ll,), len(ll))
    TestApplyResult(o.SetULongLongSafeArray, (ll,), len(ll))

    # Tell the server to do what it does!
    TestApplyResult(o.Test2, (constants.Attr2,), constants.Attr2)
    TestApplyResult(o.Test3, (constants.Attr2,), constants.Attr2)
    TestApplyResult(o.Test4, (constants.Attr2,), constants.Attr2)
    TestApplyResult(o.Test5, (constants.Attr2,), constants.Attr2)

    TestApplyResult(o.Test6, (constants.WideAttr1,), constants.WideAttr1)
    TestApplyResult(o.Test6, (constants.WideAttr2,), constants.WideAttr2)
    TestApplyResult(o.Test6, (constants.WideAttr3,), constants.WideAttr3)
    TestApplyResult(o.Test6, (constants.WideAttr4,), constants.WideAttr4)
    TestApplyResult(o.Test6, (constants.WideAttr5,), constants.WideAttr5)

    TestApplyResult(o.TestInOut, (2.0, True, 4), (4.0, False, 8))

    o.SetParamProp(0, 1)
    assert o.ParamProp(0) == 1, o.paramProp(0)

    # Make sure CastTo works - even though it is only casting it to itself!
    o2 = CastTo(o, "IPyCOMTest")
    assert o == o2, "CastTo should have returned the same object"

    # Do the connection point thing...
    # Create a connection object.
    progress("Testing connection points")
    o2 = win32com.client.DispatchWithEvents(o, RandomEventHandler)
    TestEvents(o2, o2)
    # and a plain "WithEvents".
    handler = win32com.client.WithEvents(o, RandomEventHandler)
    TestEvents(o, handler)
    progress("Finished generated .py test.")


def TestEvents(o, handler):
    sessions = []
    handler._Init()
    try:
        for i in range(3):
            session = o.Start()
            sessions.append(session)
        time.sleep(0.5)
    finally:
        # Stop the servers
        for session in sessions:
            o.Stop(session)
        handler._DumpFireds()
        handler.close()


def _TestPyVariant(o, is_generated, val, checker=None):
    if is_generated:
        vt, got = o.GetVariantAndType(val)
    else:
        # Gotta supply all 3 args with the last 2 being explicit variants to
        # get the byref behaviour.
        var_vt = VARIANT(pythoncom.VT_UI2 | pythoncom.VT_BYREF, 0)
        var_result = VARIANT(pythoncom.VT_VARIANT | pythoncom.VT_BYREF, 0)
        o.GetVariantAndType(val, var_vt, var_result)
        vt = var_vt.value
        got = var_result.value
    if checker is not None:
        checker(got)
        return
    # default checking.
    assert vt == val.varianttype, (vt, val.varianttype)
    # Handle our safe-array test - if the passed value is a list of variants,
    # compare against the actual values.
    if isinstance(val.value, (tuple, list)):
        check = [v.value if isinstance(v, VARIANT) else v for v in val.value]
        # pythoncom always returns arrays as tuples.
        got = list(got)
    else:
        check = val.value
    assert type(check) == type(got), (type(check), type(got))
    assert check == got, (check, got)


def _TestPyVariantFails(o, is_generated, val, exc):
    try:
        _TestPyVariant(o, is_generated, val)
        raise AssertionError(f"Setting {val!r} didn't raise {exc}")
    except exc:
        pass


def TestPyVariant(o, is_generated):
    _TestPyVariant(o, is_generated, VARIANT(pythoncom.VT_UI1, 1))
    _TestPyVariant(
        o, is_generated, VARIANT(pythoncom.VT_ARRAY | pythoncom.VT_UI4, [1, 2, 3])
    )
    _TestPyVariant(o, is_generated, VARIANT(pythoncom.VT_BSTR, "hello"))
    _TestPyVariant(
        o,
        is_generated,
        VARIANT(pythoncom.VT_ARRAY | pythoncom.VT_BSTR, ["hello", "there"]),
    )

    def check_dispatch(got):
        assert isinstance(got._oleobj_, pythoncom.TypeIIDs[pythoncom.IID_IDispatch])

    _TestPyVariant(o, is_generated, VARIANT(pythoncom.VT_DISPATCH, o), check_dispatch)
    _TestPyVariant(
        o, is_generated, VARIANT(pythoncom.VT_ARRAY | pythoncom.VT_DISPATCH, [o])
    )
    # an array of variants each with a specific type.
    v = VARIANT(
        pythoncom.VT_ARRAY | pythoncom.VT_VARIANT,
        [
            VARIANT(pythoncom.VT_UI4, 1),
            VARIANT(pythoncom.VT_UI4, 2),
            VARIANT(pythoncom.VT_UI4, 3),
        ],
    )
    _TestPyVariant(o, is_generated, v)

    # and failures
    _TestPyVariantFails(o, is_generated, VARIANT(pythoncom.VT_UI1, "foo"), ValueError)


def TestCounter(counter, bIsGenerated):
    # Test random access into container
    progress(f"Testing counter {counter!r}")
    import random

    for i in range(50):
        num = int(random.random() * len(counter))
        try:
            # XXX - this appears broken by commit 08a14d4deb374eaa06378509cf44078ad467b9dc -
            # We shouldn't need to do generated differently than dynamic.
            if bIsGenerated:
                ret = counter.Item(num + 1)
            else:
                ret = counter[num]
            assert (
                ret == num + 1
            ), f"Random access into element {num} failed - return was {ret!r}"
        except IndexError:
            raise AssertionError(f"** IndexError accessing collection element {num}")

    num = 0
    if bIsGenerated:
        counter.SetTestProperty(1)
        counter.TestProperty = 1  # Note this has a second, default arg.
        counter.SetTestProperty(1, 2)
        assert counter.TestPropertyWithDef == 0, "Unexpected property set value!"
        assert counter.TestPropertyNoDef(1) == 1, "Unexpected property set value!"
    else:
        pass
        # counter.TestProperty = 1

    counter.LBound = 1
    counter.UBound = 10
    if counter.LBound != 1 or counter.UBound != 10:
        print("** Error - counter did not keep its properties")

    if bIsGenerated:
        bounds = counter.GetBounds()
        assert (
            bounds[0] == 1 and bounds[1] == 10
        ), "** Error - counter did not give the same properties back"
        counter.SetBounds(bounds[0], bounds[1])

    for item in counter:
        num += 1
    assert num == len(
        counter
    ), "*** Length of counter and loop iterations don't match ***"
    assert num == 10, "*** Unexpected number of loop iterations ***"

    try:
        counter = iter(counter)._iter_.Clone()  # Test Clone() and enum directly
    except AttributeError:
        # *sob* - sometimes this is a real iterator and sometimes not :/
        progress("Finished testing counter (but skipped the iterator stuff")
        return
    counter.Reset()
    num = 0
    for item in counter:
        num += 1
    assert num == 10, f"*** Unexpected number of loop iterations - got {num} ***"
    progress("Finished testing counter")


def TestLocalVTable(ob):
    # Python doesn't fully implement this interface.
    assert ob.DoubleString("foo") == "foofoo", "couldn't foofoo"


###############################
##
## Some vtable tests of the interface
##
def TestVTable(clsctx=pythoncom.CLSCTX_ALL):
    # Any vtable interfaces marked as dual *should* be able to be
    # correctly implemented as IDispatch.
    ob = win32com.client.Dispatch("Python.Test.PyCOMTest")
    TestLocalVTable(ob)
    # Now test it via vtable - use some C++ code to help here as Python can't do it directly yet.
    tester = win32com.client.Dispatch("PyCOMTest.PyCOMTest")
    testee = pythoncom.CoCreateInstance(
        "Python.Test.PyCOMTest", None, clsctx, pythoncom.IID_IUnknown
    )
    # check we fail gracefully with None passed.
    try:
        tester.TestMyInterface(None)
    except pythoncom.com_error as details:
        pass
    # and a real object.
    tester.TestMyInterface(testee)


def TestVTable2():
    # We once crashed creating our object with the native interface as
    # the first IID specified.  We must do it _after_ the tests, so that
    # Python has already had the gateway registered from last run.
    ob = win32com.client.Dispatch("Python.Test.PyCOMTest")
    iid = pythoncom.InterfaceNames["IPyCOMTest"]
    clsid = "Python.Test.PyCOMTest"
    clsctx = pythoncom.CLSCTX_SERVER
    try:
        testee = pythoncom.CoCreateInstance(clsid, None, clsctx, iid)
    except TypeError:
        # Python can't actually _use_ this interface yet, so this is
        # "expected".  Any COM error is not.
        pass


def TestVTableMI():
    clsctx = pythoncom.CLSCTX_SERVER
    ob = pythoncom.CoCreateInstance(
        "Python.Test.PyCOMTestMI", None, clsctx, pythoncom.IID_IUnknown
    )
    # This inherits from IStream.
    ob.QueryInterface(pythoncom.IID_IStream)
    # This implements IStorage, specifying the IID as a string
    ob.QueryInterface(pythoncom.IID_IStorage)
    # IDispatch should always work
    ob.QueryInterface(pythoncom.IID_IDispatch)

    iid = pythoncom.InterfaceNames["IPyCOMTest"]
    try:
        ob.QueryInterface(iid)
    except TypeError:
        # Python can't actually _use_ this interface yet, so this is
        # "expected".  Any COM error is not.
        pass


def TestQueryInterface(long_lived_server=0, iterations=5):
    tester = win32com.client.Dispatch("PyCOMTest.PyCOMTest")
    if long_lived_server:
        # Create a local server
        t0 = win32com.client.Dispatch(
            "Python.Test.PyCOMTest", clsctx=pythoncom.CLSCTX_LOCAL_SERVER
        )
    # Request custom interfaces a number of times
    prompt = [
        "Testing QueryInterface without long-lived local-server #%d of %d...",
        "Testing QueryInterface with long-lived local-server #%d of %d...",
    ]

    for i in range(iterations):
        progress(prompt[long_lived_server != 0] % (i + 1, iterations))
        tester.TestQueryInterface()


class Tester(win32com.test.util.TestCase):
    def testVTableInProc(self):
        # We used to crash running this the second time - do it a few times
        for i in range(3):
            progress("Testing VTables in-process #%d..." % (i + 1))
            TestVTable(pythoncom.CLSCTX_INPROC_SERVER)

    def testVTableLocalServer(self):
        for i in range(3):
            progress("Testing VTables out-of-process #%d..." % (i + 1))
            TestVTable(pythoncom.CLSCTX_LOCAL_SERVER)

    def testVTable2(self):
        for i in range(3):
            TestVTable2()

    def testVTableMI(self):
        for i in range(3):
            TestVTableMI()

    def testMultiQueryInterface(self):
        TestQueryInterface(0, 6)
        # When we use the custom interface in the presence of a long-lived
        # local server, i.e. a local server that is already running when
        # we request an instance of our COM object, and remains afterwards,
        # then after repeated requests to create an instance of our object
        # the custom interface disappears -- i.e. QueryInterface fails with
        # E_NOINTERFACE. Set the upper range of the following test to 2 to
        # pass this test, i.e. TestQueryInterface(1,2)
        TestQueryInterface(1, 6)

    def testDynamic(self):
        TestDynamic()

    def testGenerated(self):
        TestGenerated()


if __name__ == "__main__":
    # XXX - todo - Complete hack to crank threading support.
    # Should NOT be necessary
    def NullThreadFunc():
        pass

    import _thread

    _thread.start_new(NullThreadFunc, ())

    if "-v" in sys.argv:
        verbose = 1

    win32com.test.util.testmain()

# === NexusCore/openenv\Lib\site-packages\aiohttp\web_request.py ===
import asyncio
import datetime
import io
import re
import socket
import string
import tempfile
import types
import warnings
from types import MappingProxyType
from typing import (
    TYPE_CHECKING,
    Any,
    Dict,
    Final,
    Iterator,
    Mapping,
    MutableMapping,
    Optional,
    Pattern,
    Tuple,
    Union,
    cast,
)
from urllib.parse import parse_qsl

import attr
from multidict import (
    CIMultiDict,
    CIMultiDictProxy,
    MultiDict,
    MultiDictProxy,
    MultiMapping,
)
from yarl import URL

from . import hdrs
from ._cookie_helpers import parse_cookie_header
from .abc import AbstractStreamWriter
from .helpers import (
    _SENTINEL,
    DEBUG,
    ETAG_ANY,
    LIST_QUOTED_ETAG_RE,
    ChainMapProxy,
    ETag,
    HeadersMixin,
    parse_http_date,
    reify,
    sentinel,
    set_exception,
)
from .http_parser import RawRequestMessage
from .http_writer import HttpVersion
from .multipart import BodyPartReader, MultipartReader
from .streams import EmptyStreamReader, StreamReader
from .typedefs import (
    DEFAULT_JSON_DECODER,
    JSONDecoder,
    LooseHeaders,
    RawHeaders,
    StrOrURL,
)
from .web_exceptions import HTTPRequestEntityTooLarge
from .web_response import StreamResponse

__all__ = ("BaseRequest", "FileField", "Request")


if TYPE_CHECKING:
    from .web_app import Application
    from .web_protocol import RequestHandler
    from .web_urldispatcher import UrlMappingMatchInfo


@attr.s(auto_attribs=True, frozen=True, slots=True)
class FileField:
    name: str
    filename: str
    file: io.BufferedReader
    content_type: str
    headers: CIMultiDictProxy[str]


_TCHAR: Final[str] = string.digits + string.ascii_letters + r"!#$%&'*+.^_`|~-"
# '-' at the end to prevent interpretation as range in a char class

_TOKEN: Final[str] = rf"[{_TCHAR}]+"

_QDTEXT: Final[str] = r"[{}]".format(
    r"".join(chr(c) for c in (0x09, 0x20, 0x21) + tuple(range(0x23, 0x7F)))
)
# qdtext includes 0x5C to escape 0x5D ('\]')
# qdtext excludes obs-text (because obsoleted, and encoding not specified)

_QUOTED_PAIR: Final[str] = r"\\[\t !-~]"

_QUOTED_STRING: Final[str] = r'"(?:{quoted_pair}|{qdtext})*"'.format(
    qdtext=_QDTEXT, quoted_pair=_QUOTED_PAIR
)

_FORWARDED_PAIR: Final[str] = (
    r"({token})=({token}|{quoted_string})(:\d{{1,4}})?".format(
        token=_TOKEN, quoted_string=_QUOTED_STRING
    )
)

_QUOTED_PAIR_REPLACE_RE: Final[Pattern[str]] = re.compile(r"\\([\t !-~])")
# same pattern as _QUOTED_PAIR but contains a capture group

_FORWARDED_PAIR_RE: Final[Pattern[str]] = re.compile(_FORWARDED_PAIR)

############################################################
# HTTP Request
############################################################


class BaseRequest(MutableMapping[str, Any], HeadersMixin):

    POST_METHODS = {
        hdrs.METH_PATCH,
        hdrs.METH_POST,
        hdrs.METH_PUT,
        hdrs.METH_TRACE,
        hdrs.METH_DELETE,
    }

    ATTRS = HeadersMixin.ATTRS | frozenset(
        [
            "_message",
            "_protocol",
            "_payload_writer",
            "_payload",
            "_headers",
            "_method",
            "_version",
            "_rel_url",
            "_post",
            "_read_bytes",
            "_state",
            "_cache",
            "_task",
            "_client_max_size",
            "_loop",
            "_transport_sslcontext",
            "_transport_peername",
        ]
    )
    _post: Optional[MultiDictProxy[Union[str, bytes, FileField]]] = None
    _read_bytes: Optional[bytes] = None

    def __init__(
        self,
        message: RawRequestMessage,
        payload: StreamReader,
        protocol: "RequestHandler",
        payload_writer: AbstractStreamWriter,
        task: "asyncio.Task[None]",
        loop: asyncio.AbstractEventLoop,
        *,
        client_max_size: int = 1024**2,
        state: Optional[Dict[str, Any]] = None,
        scheme: Optional[str] = None,
        host: Optional[str] = None,
        remote: Optional[str] = None,
    ) -> None:
        self._message = message
        self._protocol = protocol
        self._payload_writer = payload_writer

        self._payload = payload
        self._headers: CIMultiDictProxy[str] = message.headers
        self._method = message.method
        self._version = message.version
        self._cache: Dict[str, Any] = {}
        url = message.url
        if url.absolute:
            if scheme is not None:
                url = url.with_scheme(scheme)
            if host is not None:
                url = url.with_host(host)
            # absolute URL is given,
            # override auto-calculating url, host, and scheme
            # all other properties should be good
            self._cache["url"] = url
            self._cache["host"] = url.host
            self._cache["scheme"] = url.scheme
            self._rel_url = url.relative()
        else:
            self._rel_url = url
            if scheme is not None:
                self._cache["scheme"] = scheme
            if host is not None:
                self._cache["host"] = host

        self._state = {} if state is None else state
        self._task = task
        self._client_max_size = client_max_size
        self._loop = loop

        self._transport_sslcontext = protocol.ssl_context
        self._transport_peername = protocol.peername

        if remote is not None:
            self._cache["remote"] = remote

    def clone(
        self,
        *,
        method: Union[str, _SENTINEL] = sentinel,
        rel_url: Union[StrOrURL, _SENTINEL] = sentinel,
        headers: Union[LooseHeaders, _SENTINEL] = sentinel,
        scheme: Union[str, _SENTINEL] = sentinel,
        host: Union[str, _SENTINEL] = sentinel,
        remote: Union[str, _SENTINEL] = sentinel,
        client_max_size: Union[int, _SENTINEL] = sentinel,
    ) -> "BaseRequest":
        """Clone itself with replacement some attributes.

        Creates and returns a new instance of Request object. If no parameters
        are given, an exact copy is returned. If a parameter is not passed, it
        will reuse the one from the current request object.
        """
        if self._read_bytes:
            raise RuntimeError("Cannot clone request after reading its content")

        dct: Dict[str, Any] = {}
        if method is not sentinel:
            dct["method"] = method
        if rel_url is not sentinel:
            new_url: URL = URL(rel_url)
            dct["url"] = new_url
            dct["path"] = str(new_url)
        if headers is not sentinel:
            # a copy semantic
            dct["headers"] = CIMultiDictProxy(CIMultiDict(headers))
            dct["raw_headers"] = tuple(
                (k.encode("utf-8"), v.encode("utf-8"))
                for k, v in dct["headers"].items()
            )

        message = self._message._replace(**dct)

        kwargs = {}
        if scheme is not sentinel:
            kwargs["scheme"] = scheme
        if host is not sentinel:
            kwargs["host"] = host
        if remote is not sentinel:
            kwargs["remote"] = remote
        if client_max_size is sentinel:
            client_max_size = self._client_max_size

        return self.__class__(
            message,
            self._payload,
            self._protocol,
            self._payload_writer,
            self._task,
            self._loop,
            client_max_size=client_max_size,
            state=self._state.copy(),
            **kwargs,
        )

    @property
    def task(self) -> "asyncio.Task[None]":
        return self._task

    @property
    def protocol(self) -> "RequestHandler":
        return self._protocol

    @property
    def transport(self) -> Optional[asyncio.Transport]:
        if self._protocol is None:
            return None
        return self._protocol.transport

    @property
    def writer(self) -> AbstractStreamWriter:
        return self._payload_writer

    @property
    def client_max_size(self) -> int:
        return self._client_max_size

    @reify
    def message(self) -> RawRequestMessage:
        warnings.warn("Request.message is deprecated", DeprecationWarning, stacklevel=3)
        return self._message

    @reify
    def rel_url(self) -> URL:
        return self._rel_url

    @reify
    def loop(self) -> asyncio.AbstractEventLoop:
        warnings.warn(
            "request.loop property is deprecated", DeprecationWarning, stacklevel=2
        )
        return self._loop

    # MutableMapping API

    def __getitem__(self, key: str) -> Any:
        return self._state[key]

    def __setitem__(self, key: str, value: Any) -> None:
        self._state[key] = value

    def __delitem__(self, key: str) -> None:
        del self._state[key]

    def __len__(self) -> int:
        return len(self._state)

    def __iter__(self) -> Iterator[str]:
        return iter(self._state)

    ########

    @reify
    def secure(self) -> bool:
        """A bool indicating if the request is handled with SSL."""
        return self.scheme == "https"

    @reify
    def forwarded(self) -> Tuple[Mapping[str, str], ...]:
        """A tuple containing all parsed Forwarded header(s).

        Makes an effort to parse Forwarded headers as specified by RFC 7239:

        - It adds one (immutable) dictionary per Forwarded 'field-value', ie
          per proxy. The element corresponds to the data in the Forwarded
          field-value added by the first proxy encountered by the client. Each
          subsequent item corresponds to those added by later proxies.
        - It checks that every value has valid syntax in general as specified
          in section 4: either a 'token' or a 'quoted-string'.
        - It un-escapes found escape sequences.
        - It does NOT validate 'by' and 'for' contents as specified in section
          6.
        - It does NOT validate 'host' contents (Host ABNF).
        - It does NOT validate 'proto' contents for valid URI scheme names.

        Returns a tuple containing one or more immutable dicts
        """
        elems = []
        for field_value in self._message.headers.getall(hdrs.FORWARDED, ()):
            length = len(field_value)
            pos = 0
            need_separator = False
            elem: Dict[str, str] = {}
            elems.append(types.MappingProxyType(elem))
            while 0 <= pos < length:
                match = _FORWARDED_PAIR_RE.match(field_value, pos)
                if match is not None:  # got a valid forwarded-pair
                    if need_separator:
                        # bad syntax here, skip to next comma
                        pos = field_value.find(",", pos)
                    else:
                        name, value, port = match.groups()
                        if value[0] == '"':
                            # quoted string: remove quotes and unescape
                            value = _QUOTED_PAIR_REPLACE_RE.sub(r"\1", value[1:-1])
                        if port:
                            value += port
                        elem[name.lower()] = value
                        pos += len(match.group(0))
                        need_separator = True
                elif field_value[pos] == ",":  # next forwarded-element
                    need_separator = False
                    elem = {}
                    elems.append(types.MappingProxyType(elem))
                    pos += 1
                elif field_value[pos] == ";":  # next forwarded-pair
                    need_separator = False
                    pos += 1
                elif field_value[pos] in " \t":
                    # Allow whitespace even between forwarded-pairs, though
                    # RFC 7239 doesn't. This simplifies code and is in line
                    # with Postel's law.
                    pos += 1
                else:
                    # bad syntax here, skip to next comma
                    pos = field_value.find(",", pos)
        return tuple(elems)

    @reify
    def scheme(self) -> str:
        """A string representing the scheme of the request.

        Hostname is resolved in this order:

        - overridden value by .clone(scheme=new_scheme) call.
        - type of connection to peer: HTTPS if socket is SSL, HTTP otherwise.

        'http' or 'https'.
        """
        if self._transport_sslcontext:
            return "https"
        else:
            return "http"

    @reify
    def method(self) -> str:
        """Read only property for getting HTTP method.

        The value is upper-cased str like 'GET', 'POST', 'PUT' etc.
        """
        return self._method

    @reify
    def version(self) -> HttpVersion:
        """Read only property for getting HTTP version of request.

        Returns aiohttp.protocol.HttpVersion instance.
        """
        return self._version

    @reify
    def host(self) -> str:
        """Hostname of the request.

        Hostname is resolved in this order:

        - overridden value by .clone(host=new_host) call.
        - HOST HTTP header
        - socket.getfqdn() value

        For example, 'example.com' or 'localhost:8080'.

        For historical reasons, the port number may be included.
        """
        host = self._message.headers.get(hdrs.HOST)
        if host is not None:
            return host
        return socket.getfqdn()

    @reify
    def remote(self) -> Optional[str]:
        """Remote IP of client initiated HTTP request.

        The IP is resolved in this order:

        - overridden value by .clone(remote=new_remote) call.
        - peername of opened socket
        """
        if self._transport_peername is None:
            return None
        if isinstance(self._transport_peername, (list, tuple)):
            return str(self._transport_peername[0])
        return str(self._transport_peername)

    @reify
    def url(self) -> URL:
        """The full URL of the request."""
        # authority is used here because it may include the port number
        # and we want yarl to parse it correctly
        return URL.build(scheme=self.scheme, authority=self.host).join(self._rel_url)

    @reify
    def path(self) -> str:
        """The URL including *PATH INFO* without the host or scheme.

        E.g., ``/app/blog``
        """
        return self._rel_url.path

    @reify
    def path_qs(self) -> str:
        """The URL including PATH_INFO and the query string.

        E.g, /app/blog?id=10
        """
        return str(self._rel_url)

    @reify
    def raw_path(self) -> str:
        """The URL including raw *PATH INFO* without the host or scheme.

        Warning, the path is unquoted and may contains non valid URL characters

        E.g., ``/my%2Fpath%7Cwith%21some%25strange%24characters``
        """
        return self._message.path

    @reify
    def query(self) -> "MultiMapping[str]":
        """A multidict with all the variables in the query string."""
        return self._rel_url.query

    @reify
    def query_string(self) -> str:
        """The query string in the URL.

        E.g., id=10
        """
        return self._rel_url.query_string

    @reify
    def headers(self) -> CIMultiDictProxy[str]:
        """A case-insensitive multidict proxy with all headers."""
        return self._headers

    @reify
    def raw_headers(self) -> RawHeaders:
        """A sequence of pairs for all headers."""
        return self._message.raw_headers

    @reify
    def if_modified_since(self) -> Optional[datetime.datetime]:
        """The value of If-Modified-Since HTTP header, or None.

        This header is represented as a `datetime` object.
        """
        return parse_http_date(self.headers.get(hdrs.IF_MODIFIED_SINCE))

    @reify
    def if_unmodified_since(self) -> Optional[datetime.datetime]:
        """The value of If-Unmodified-Since HTTP header, or None.

        This header is represented as a `datetime` object.
        """
        return parse_http_date(self.headers.get(hdrs.IF_UNMODIFIED_SINCE))

    @staticmethod
    def _etag_values(etag_header: str) -> Iterator[ETag]:
        """Extract `ETag` objects from raw header."""
        if etag_header == ETAG_ANY:
            yield ETag(
                is_weak=False,
                value=ETAG_ANY,
            )
        else:
            for match in LIST_QUOTED_ETAG_RE.finditer(etag_header):
                is_weak, value, garbage = match.group(2, 3, 4)
                # Any symbol captured by 4th group means
                # that the following sequence is invalid.
                if garbage:
                    break

                yield ETag(
                    is_weak=bool(is_weak),
                    value=value,
                )

    @classmethod
    def _if_match_or_none_impl(
        cls, header_value: Optional[str]
    ) -> Optional[Tuple[ETag, ...]]:
        if not header_value:
            return None

        return tuple(cls._etag_values(header_value))

    @reify
    def if_match(self) -> Optional[Tuple[ETag, ...]]:
        """The value of If-Match HTTP header, or None.

        This header is represented as a `tuple` of `ETag` objects.
        """
        return self._if_match_or_none_impl(self.headers.get(hdrs.IF_MATCH))

    @reify
    def if_none_match(self) -> Optional[Tuple[ETag, ...]]:
        """The value of If-None-Match HTTP header, or None.

        This header is represented as a `tuple` of `ETag` objects.
        """
        return self._if_match_or_none_impl(self.headers.get(hdrs.IF_NONE_MATCH))

    @reify
    def if_range(self) -> Optional[datetime.datetime]:
        """The value of If-Range HTTP header, or None.

        This header is represented as a `datetime` object.
        """
        return parse_http_date(self.headers.get(hdrs.IF_RANGE))

    @reify
    def keep_alive(self) -> bool:
        """Is keepalive enabled by client?"""
        return not self._message.should_close

    @reify
    def cookies(self) -> Mapping[str, str]:
        """Return request cookies.

        A read-only dictionary-like object.
        """
        # Use parse_cookie_header for RFC 6265 compliant Cookie header parsing
        # that accepts special characters in cookie names (fixes #2683)
        parsed = parse_cookie_header(self.headers.get(hdrs.COOKIE, ""))
        # Extract values from Morsel objects
        return MappingProxyType({name: morsel.value for name, morsel in parsed})

    @reify
    def http_range(self) -> slice:
        """The content of Range HTTP header.

        Return a slice instance.

        """
        rng = self._headers.get(hdrs.RANGE)
        start, end = None, None
        if rng is not None:
            try:
                pattern = r"^bytes=(\d*)-(\d*)$"
                start, end = re.findall(pattern, rng)[0]
            except IndexError:  # pattern was not found in header
                raise ValueError("range not in acceptable format")

            end = int(end) if end else None
            start = int(start) if start else None

            if start is None and end is not None:
                # end with no start is to return tail of content
                start = -end
                end = None

            if start is not None and end is not None:
                # end is inclusive in range header, exclusive for slice
                end += 1

                if start >= end:
                    raise ValueError("start cannot be after end")

            if start is end is None:  # No valid range supplied
                raise ValueError("No start or end of range specified")

        return slice(start, end, 1)

    @reify
    def content(self) -> StreamReader:
        """Return raw payload stream."""
        return self._payload

    @property
    def has_body(self) -> bool:
        """Return True if request's HTTP BODY can be read, False otherwise."""
        warnings.warn(
            "Deprecated, use .can_read_body #2005", DeprecationWarning, stacklevel=2
        )
        return not self._payload.at_eof()

    @property
    def can_read_body(self) -> bool:
        """Return True if request's HTTP BODY can be read, False otherwise."""
        return not self._payload.at_eof()

    @reify
    def body_exists(self) -> bool:
        """Return True if request has HTTP BODY, False otherwise."""
        return type(self._payload) is not EmptyStreamReader

    async def release(self) -> None:
        """Release request.

        Eat unread part of HTTP BODY if present.
        """
        while not self._payload.at_eof():
            await self._payload.readany()

    async def read(self) -> bytes:
        """Read request body if present.

        Returns bytes object with full request content.
        """
        if self._read_bytes is None:
            body = bytearray()
            while True:
                chunk = await self._payload.readany()
                body.extend(chunk)
                if self._client_max_size:
                    body_size = len(body)
                    if body_size >= self._client_max_size:
                        raise HTTPRequestEntityTooLarge(
                            max_size=self._client_max_size, actual_size=body_size
                        )
                if not chunk:
                    break
            self._read_bytes = bytes(body)
        return self._read_bytes

    async def text(self) -> str:
        """Return BODY as text using encoding from .charset."""
        bytes_body = await self.read()
        encoding = self.charset or "utf-8"
        return bytes_body.decode(encoding)

    async def json(self, *, loads: JSONDecoder = DEFAULT_JSON_DECODER) -> Any:
        """Return BODY as JSON."""
        body = await self.text()
        return loads(body)

    async def multipart(self) -> MultipartReader:
        """Return async iterator to process BODY as multipart."""
        return MultipartReader(self._headers, self._payload)

    async def post(self) -> "MultiDictProxy[Union[str, bytes, FileField]]":
        """Return POST parameters."""
        if self._post is not None:
            return self._post
        if self._method not in self.POST_METHODS:
            self._post = MultiDictProxy(MultiDict())
            return self._post

        content_type = self.content_type
        if content_type not in (
            "",
            "application/x-www-form-urlencoded",
            "multipart/form-data",
        ):
            self._post = MultiDictProxy(MultiDict())
            return self._post

        out: MultiDict[Union[str, bytes, FileField]] = MultiDict()

        if content_type == "multipart/form-data":
            multipart = await self.multipart()
            max_size = self._client_max_size

            field = await multipart.next()
            while field is not None:
                size = 0
                field_ct = field.headers.get(hdrs.CONTENT_TYPE)

                if isinstance(field, BodyPartReader):
                    assert field.name is not None

                    # Note that according to RFC 7578, the Content-Type header
                    # is optional, even for files, so we can't assume it's
                    # present.
                    # https://tools.ietf.org/html/rfc7578#section-4.4
                    if field.filename:
                        # store file in temp file
                        tmp = await self._loop.run_in_executor(
                            None, tempfile.TemporaryFile
                        )
                        chunk = await field.read_chunk(size=2**16)
                        while chunk:
                            chunk = field.decode(chunk)
                            await self._loop.run_in_executor(None, tmp.write, chunk)
                            size += len(chunk)
                            if 0 < max_size < size:
                                await self._loop.run_in_executor(None, tmp.close)
                                raise HTTPRequestEntityTooLarge(
                                    max_size=max_size, actual_size=size
                                )
                            chunk = await field.read_chunk(size=2**16)
                        await self._loop.run_in_executor(None, tmp.seek, 0)

                        if field_ct is None:
                            field_ct = "application/octet-stream"

                        ff = FileField(
                            field.name,
                            field.filename,
                            cast(io.BufferedReader, tmp),
                            field_ct,
                            field.headers,
                        )
                        out.add(field.name, ff)
                    else:
                        # deal with ordinary data
                        value = await field.read(decode=True)
                        if field_ct is None or field_ct.startswith("text/"):
                            charset = field.get_charset(default="utf-8")
                            out.add(field.name, value.decode(charset))
                        else:
                            out.add(field.name, value)
                        size += len(value)
                        if 0 < max_size < size:
                            raise HTTPRequestEntityTooLarge(
                                max_size=max_size, actual_size=size
                            )
                else:
                    raise ValueError(
                        "To decode nested multipart you need to use custom reader",
                    )

                field = await multipart.next()
        else:
            data = await self.read()
            if data:
                charset = self.charset or "utf-8"
                out.extend(
                    parse_qsl(
                        data.rstrip().decode(charset),
                        keep_blank_values=True,
                        encoding=charset,
                    )
                )

        self._post = MultiDictProxy(out)
        return self._post

    def get_extra_info(self, name: str, default: Any = None) -> Any:
        """Extra info from protocol transport"""
        protocol = self._protocol
        if protocol is None:
            return default

        transport = protocol.transport
        if transport is None:
            return default

        return transport.get_extra_info(name, default)

    def __repr__(self) -> str:
        ascii_encodable_path = self.path.encode("ascii", "backslashreplace").decode(
            "ascii"
        )
        return "<{} {} {} >".format(
            self.__class__.__name__, self._method, ascii_encodable_path
        )

    def __eq__(self, other: object) -> bool:
        return id(self) == id(other)

    def __bool__(self) -> bool:
        return True

    async def _prepare_hook(self, response: StreamResponse) -> None:
        return

    def _cancel(self, exc: BaseException) -> None:
        set_exception(self._payload, exc)

    def _finish(self) -> None:
        if self._post is None or self.content_type != "multipart/form-data":
            return

        # NOTE: Release file descriptors for the
        # NOTE: `tempfile.Temporaryfile`-created `_io.BufferedRandom`
        # NOTE: instances of files sent within multipart request body
        # NOTE: via HTTP POST request.
        for file_name, file_field_object in self._post.items():
            if isinstance(file_field_object, FileField):
                file_field_object.file.close()


class Request(BaseRequest):

    ATTRS = BaseRequest.ATTRS | frozenset(["_match_info"])

    _match_info: Optional["UrlMappingMatchInfo"] = None

    if DEBUG:

        def __setattr__(self, name: str, val: Any) -> None:
            if name not in self.ATTRS:
                warnings.warn(
                    "Setting custom {}.{} attribute "
                    "is discouraged".format(self.__class__.__name__, name),
                    DeprecationWarning,
                    stacklevel=2,
                )
            super().__setattr__(name, val)

    def clone(
        self,
        *,
        method: Union[str, _SENTINEL] = sentinel,
        rel_url: Union[StrOrURL, _SENTINEL] = sentinel,
        headers: Union[LooseHeaders, _SENTINEL] = sentinel,
        scheme: Union[str, _SENTINEL] = sentinel,
        host: Union[str, _SENTINEL] = sentinel,
        remote: Union[str, _SENTINEL] = sentinel,
        client_max_size: Union[int, _SENTINEL] = sentinel,
    ) -> "Request":
        ret = super().clone(
            method=method,
            rel_url=rel_url,
            headers=headers,
            scheme=scheme,
            host=host,
            remote=remote,
            client_max_size=client_max_size,
        )
        new_ret = cast(Request, ret)
        new_ret._match_info = self._match_info
        return new_ret

    @reify
    def match_info(self) -> "UrlMappingMatchInfo":
        """Result of route resolving."""
        match_info = self._match_info
        assert match_info is not None
        return match_info

    @property
    def app(self) -> "Application":
        """Application instance."""
        match_info = self._match_info
        assert match_info is not None
        return match_info.current_app

    @property
    def config_dict(self) -> ChainMapProxy:
        match_info = self._match_info
        assert match_info is not None
        lst = match_info.apps
        app = self.app
        idx = lst.index(app)
        sublist = list(reversed(lst[: idx + 1]))
        return ChainMapProxy(sublist)

    async def _prepare_hook(self, response: StreamResponse) -> None:
        match_info = self._match_info
        if match_info is None:
            return
        for app in match_info._apps:
            if on_response_prepare := app.on_response_prepare:
                await on_response_prepare.send(self, response)

# === NexusCore/openenv\Lib\site-packages\huggingface_hub\_commit_api.py ===
"""
Type definitions and utilities for the `create_commit` API
"""

import base64
import io
import math
import os
import warnings
from collections import defaultdict
from contextlib import contextmanager
from dataclasses import dataclass, field
from itertools import groupby
from pathlib import Path, PurePosixPath
from typing import TYPE_CHECKING, Any, BinaryIO, Dict, Iterable, Iterator, List, Literal, Optional, Tuple, Union

from tqdm.contrib.concurrent import thread_map

from . import constants
from .errors import EntryNotFoundError, HfHubHTTPError, XetAuthorizationError, XetRefreshTokenError
from .file_download import hf_hub_url
from .lfs import UploadInfo, lfs_upload, post_lfs_batch_info
from .utils import (
    FORBIDDEN_FOLDERS,
    XetTokenType,
    chunk_iterable,
    fetch_xet_connection_info_from_repo_info,
    get_session,
    hf_raise_for_status,
    logging,
    sha,
    tqdm_stream_file,
    validate_hf_hub_args,
)
from .utils import tqdm as hf_tqdm
from .utils.tqdm import _get_progress_bar_context


if TYPE_CHECKING:
    from .hf_api import RepoFile


logger = logging.get_logger(__name__)


UploadMode = Literal["lfs", "regular"]

# Max is 1,000 per request on the Hub for HfApi.get_paths_info
# Otherwise we get:
# HfHubHTTPError: 413 Client Error: Payload Too Large for url: https://huggingface.co/api/datasets/xxx (Request ID: xxx)\n\ntoo many parameters
# See https://github.com/huggingface/huggingface_hub/issues/1503
FETCH_LFS_BATCH_SIZE = 500

UPLOAD_BATCH_MAX_NUM_FILES = 256


@dataclass
class CommitOperationDelete:
    """
    Data structure holding necessary info to delete a file or a folder from a repository
    on the Hub.

    Args:
        path_in_repo (`str`):
            Relative filepath in the repo, for example: `"checkpoints/1fec34a/weights.bin"`
            for a file or `"checkpoints/1fec34a/"` for a folder.
        is_folder (`bool` or `Literal["auto"]`, *optional*)
            Whether the Delete Operation applies to a folder or not. If "auto", the path
            type (file or folder) is guessed automatically by looking if path ends with
            a "/" (folder) or not (file). To explicitly set the path type, you can set
            `is_folder=True` or `is_folder=False`.
    """

    path_in_repo: str
    is_folder: Union[bool, Literal["auto"]] = "auto"

    def __post_init__(self):
        self.path_in_repo = _validate_path_in_repo(self.path_in_repo)

        if self.is_folder == "auto":
            self.is_folder = self.path_in_repo.endswith("/")
        if not isinstance(self.is_folder, bool):
            raise ValueError(
                f"Wrong value for `is_folder`. Must be one of [`True`, `False`, `'auto'`]. Got '{self.is_folder}'."
            )


@dataclass
class CommitOperationCopy:
    """
    Data structure holding necessary info to copy a file in a repository on the Hub.

    Limitations:
      - Only LFS files can be copied. To copy a regular file, you need to download it locally and re-upload it
      - Cross-repository copies are not supported.

    Note: you can combine a [`CommitOperationCopy`] and a [`CommitOperationDelete`] to rename an LFS file on the Hub.

    Args:
        src_path_in_repo (`str`):
            Relative filepath in the repo of the file to be copied, e.g. `"checkpoints/1fec34a/weights.bin"`.
        path_in_repo (`str`):
            Relative filepath in the repo where to copy the file, e.g. `"checkpoints/1fec34a/weights_copy.bin"`.
        src_revision (`str`, *optional*):
            The git revision of the file to be copied. Can be any valid git revision.
            Default to the target commit revision.
    """

    src_path_in_repo: str
    path_in_repo: str
    src_revision: Optional[str] = None
    # set to the OID of the file to be copied if it has already been uploaded
    # useful to determine if a commit will be empty or not.
    _src_oid: Optional[str] = None
    # set to the OID of the file to copy to if it has already been uploaded
    # useful to determine if a commit will be empty or not.
    _dest_oid: Optional[str] = None

    def __post_init__(self):
        self.src_path_in_repo = _validate_path_in_repo(self.src_path_in_repo)
        self.path_in_repo = _validate_path_in_repo(self.path_in_repo)


@dataclass
class CommitOperationAdd:
    """
    Data structure holding necessary info to upload a file to a repository on the Hub.

    Args:
        path_in_repo (`str`):
            Relative filepath in the repo, for example: `"checkpoints/1fec34a/weights.bin"`
        path_or_fileobj (`str`, `Path`, `bytes`, or `BinaryIO`):
            Either:
            - a path to a local file (as `str` or `pathlib.Path`) to upload
            - a buffer of bytes (`bytes`) holding the content of the file to upload
            - a "file object" (subclass of `io.BufferedIOBase`), typically obtained
                with `open(path, "rb")`. It must support `seek()` and `tell()` methods.

    Raises:
        [`ValueError`](https://docs.python.org/3/library/exceptions.html#ValueError)
            If `path_or_fileobj` is not one of `str`, `Path`, `bytes` or `io.BufferedIOBase`.
        [`ValueError`](https://docs.python.org/3/library/exceptions.html#ValueError)
            If `path_or_fileobj` is a `str` or `Path` but not a path to an existing file.
        [`ValueError`](https://docs.python.org/3/library/exceptions.html#ValueError)
            If `path_or_fileobj` is a `io.BufferedIOBase` but it doesn't support both
            `seek()` and `tell()`.
    """

    path_in_repo: str
    path_or_fileobj: Union[str, Path, bytes, BinaryIO]
    upload_info: UploadInfo = field(init=False, repr=False)

    # Internal attributes

    # set to "lfs" or "regular" once known
    _upload_mode: Optional[UploadMode] = field(init=False, repr=False, default=None)

    # set to True if .gitignore rules prevent the file from being uploaded as LFS
    # (server-side check)
    _should_ignore: Optional[bool] = field(init=False, repr=False, default=None)

    # set to the remote OID of the file if it has already been uploaded
    # useful to determine if a commit will be empty or not
    _remote_oid: Optional[str] = field(init=False, repr=False, default=None)

    # set to True once the file has been uploaded as LFS
    _is_uploaded: bool = field(init=False, repr=False, default=False)

    # set to True once the file has been committed
    _is_committed: bool = field(init=False, repr=False, default=False)

    def __post_init__(self) -> None:
        """Validates `path_or_fileobj` and compute `upload_info`."""
        self.path_in_repo = _validate_path_in_repo(self.path_in_repo)

        # Validate `path_or_fileobj` value
        if isinstance(self.path_or_fileobj, Path):
            self.path_or_fileobj = str(self.path_or_fileobj)
        if isinstance(self.path_or_fileobj, str):
            path_or_fileobj = os.path.normpath(os.path.expanduser(self.path_or_fileobj))
            if not os.path.isfile(path_or_fileobj):
                raise ValueError(f"Provided path: '{path_or_fileobj}' is not a file on the local file system")
        elif not isinstance(self.path_or_fileobj, (io.BufferedIOBase, bytes)):
            # ^^ Inspired from: https://stackoverflow.com/questions/44584829/how-to-determine-if-file-is-opened-in-binary-or-text-mode
            raise ValueError(
                "path_or_fileobj must be either an instance of str, bytes or"
                " io.BufferedIOBase. If you passed a file-like object, make sure it is"
                " in binary mode."
            )
        if isinstance(self.path_or_fileobj, io.BufferedIOBase):
            try:
                self.path_or_fileobj.tell()
                self.path_or_fileobj.seek(0, os.SEEK_CUR)
            except (OSError, AttributeError) as exc:
                raise ValueError(
                    "path_or_fileobj is a file-like object but does not implement seek() and tell()"
                ) from exc

        # Compute "upload_info" attribute
        if isinstance(self.path_or_fileobj, str):
            self.upload_info = UploadInfo.from_path(self.path_or_fileobj)
        elif isinstance(self.path_or_fileobj, bytes):
            self.upload_info = UploadInfo.from_bytes(self.path_or_fileobj)
        else:
            self.upload_info = UploadInfo.from_fileobj(self.path_or_fileobj)

    @contextmanager
    def as_file(self, with_tqdm: bool = False) -> Iterator[BinaryIO]:
        """
        A context manager that yields a file-like object allowing to read the underlying
        data behind `path_or_fileobj`.

        Args:
            with_tqdm (`bool`, *optional*, defaults to `False`):
                If True, iterating over the file object will display a progress bar. Only
                works if the file-like object is a path to a file. Pure bytes and buffers
                are not supported.

        Example:

        ```python
        >>> operation = CommitOperationAdd(
        ...        path_in_repo="remote/dir/weights.h5",
        ...        path_or_fileobj="./local/weights.h5",
        ... )
        CommitOperationAdd(path_in_repo='remote/dir/weights.h5', path_or_fileobj='./local/weights.h5')

        >>> with operation.as_file() as file:
        ...     content = file.read()

        >>> with operation.as_file(with_tqdm=True) as file:
        ...     while True:
        ...         data = file.read(1024)
        ...         if not data:
        ...              break
        config.json: 100%|█████████████████████████| 8.19k/8.19k [00:02<00:00, 3.72kB/s]

        >>> with operation.as_file(with_tqdm=True) as file:
        ...     requests.put(..., data=file)
        config.json: 100%|█████████████████████████| 8.19k/8.19k [00:02<00:00, 3.72kB/s]
        ```
        """
        if isinstance(self.path_or_fileobj, str) or isinstance(self.path_or_fileobj, Path):
            if with_tqdm:
                with tqdm_stream_file(self.path_or_fileobj) as file:
                    yield file
            else:
                with open(self.path_or_fileobj, "rb") as file:
                    yield file
        elif isinstance(self.path_or_fileobj, bytes):
            yield io.BytesIO(self.path_or_fileobj)
        elif isinstance(self.path_or_fileobj, io.BufferedIOBase):
            prev_pos = self.path_or_fileobj.tell()
            yield self.path_or_fileobj
            self.path_or_fileobj.seek(prev_pos, io.SEEK_SET)

    def b64content(self) -> bytes:
        """
        The base64-encoded content of `path_or_fileobj`

        Returns: `bytes`
        """
        with self.as_file() as file:
            return base64.b64encode(file.read())

    @property
    def _local_oid(self) -> Optional[str]:
        """Return the OID of the local file.

        This OID is then compared to `self._remote_oid` to check if the file has changed compared to the remote one.
        If the file did not change, we won't upload it again to prevent empty commits.

        For LFS files, the OID corresponds to the SHA256 of the file content (used a LFS ref).
        For regular files, the OID corresponds to the SHA1 of the file content.
        Note: this is slightly different to git OID computation since the oid of an LFS file is usually the git-SHA1 of the
              pointer file content (not the actual file content). However, using the SHA256 is enough to detect changes
              and more convenient client-side.
        """
        if self._upload_mode is None:
            return None
        elif self._upload_mode == "lfs":
            return self.upload_info.sha256.hex()
        else:
            # Regular file => compute sha1
            # => no need to read by chunk since the file is guaranteed to be <=5MB.
            with self.as_file() as file:
                return sha.git_hash(file.read())


def _validate_path_in_repo(path_in_repo: str) -> str:
    # Validate `path_in_repo` value to prevent a server-side issue
    if path_in_repo.startswith("/"):
        path_in_repo = path_in_repo[1:]
    if path_in_repo == "." or path_in_repo == ".." or path_in_repo.startswith("../"):
        raise ValueError(f"Invalid `path_in_repo` in CommitOperation: '{path_in_repo}'")
    if path_in_repo.startswith("./"):
        path_in_repo = path_in_repo[2:]
    for forbidden in FORBIDDEN_FOLDERS:
        if any(part == forbidden for part in path_in_repo.split("/")):
            raise ValueError(
                f"Invalid `path_in_repo` in CommitOperation: cannot update files under a '{forbidden}/' folder (path:"
                f" '{path_in_repo}')."
            )
    return path_in_repo


CommitOperation = Union[CommitOperationAdd, CommitOperationCopy, CommitOperationDelete]


def _warn_on_overwriting_operations(operations: List[CommitOperation]) -> None:
    """
    Warn user when a list of operations is expected to overwrite itself in a single
    commit.

    Rules:
    - If a filepath is updated by multiple `CommitOperationAdd` operations, a warning
      message is triggered.
    - If a filepath is updated at least once by a `CommitOperationAdd` and then deleted
      by a `CommitOperationDelete`, a warning is triggered.
    - If a `CommitOperationDelete` deletes a filepath that is then updated by a
      `CommitOperationAdd`, no warning is triggered. This is usually useless (no need to
      delete before upload) but can happen if a user deletes an entire folder and then
      add new files to it.
    """
    nb_additions_per_path: Dict[str, int] = defaultdict(int)
    for operation in operations:
        path_in_repo = operation.path_in_repo
        if isinstance(operation, CommitOperationAdd):
            if nb_additions_per_path[path_in_repo] > 0:
                warnings.warn(
                    "About to update multiple times the same file in the same commit:"
                    f" '{path_in_repo}'. This can cause undesired inconsistencies in"
                    " your repo."
                )
            nb_additions_per_path[path_in_repo] += 1
            for parent in PurePosixPath(path_in_repo).parents:
                # Also keep track of number of updated files per folder
                # => warns if deleting a folder overwrite some contained files
                nb_additions_per_path[str(parent)] += 1
        if isinstance(operation, CommitOperationDelete):
            if nb_additions_per_path[str(PurePosixPath(path_in_repo))] > 0:
                if operation.is_folder:
                    warnings.warn(
                        "About to delete a folder containing files that have just been"
                        f" updated within the same commit: '{path_in_repo}'. This can"
                        " cause undesired inconsistencies in your repo."
                    )
                else:
                    warnings.warn(
                        "About to delete a file that have just been updated within the"
                        f" same commit: '{path_in_repo}'. This can cause undesired"
                        " inconsistencies in your repo."
                    )


@validate_hf_hub_args
def _upload_lfs_files(
    *,
    additions: List[CommitOperationAdd],
    repo_type: str,
    repo_id: str,
    headers: Dict[str, str],
    endpoint: Optional[str] = None,
    num_threads: int = 5,
    revision: Optional[str] = None,
):
    """
    Uploads the content of `additions` to the Hub using the large file storage protocol.

    Relevant external documentation:
        - LFS Batch API: https://github.com/git-lfs/git-lfs/blob/main/docs/api/batch.md

    Args:
        additions (`List` of `CommitOperationAdd`):
            The files to be uploaded
        repo_type (`str`):
            Type of the repo to upload to: `"model"`, `"dataset"` or `"space"`.
        repo_id (`str`):
            A namespace (user or an organization) and a repo name separated
            by a `/`.
        headers (`Dict[str, str]`):
            Headers to use for the request, including authorization headers and user agent.
        num_threads (`int`, *optional*):
            The number of concurrent threads to use when uploading. Defaults to 5.
        revision (`str`, *optional*):
            The git revision to upload to.

    Raises:
        [`EnvironmentError`](https://docs.python.org/3/library/exceptions.html#EnvironmentError)
            If an upload failed for any reason
        [`ValueError`](https://docs.python.org/3/library/exceptions.html#ValueError)
            If the server returns malformed responses
        [`HTTPError`](https://requests.readthedocs.io/en/latest/api/#requests.HTTPError)
            If the LFS batch endpoint returned an HTTP error.
    """
    # Step 1: retrieve upload instructions from the LFS batch endpoint.
    #         Upload instructions are retrieved by chunk of 256 files to avoid reaching
    #         the payload limit.
    batch_actions: List[Dict] = []
    for chunk in chunk_iterable(additions, chunk_size=UPLOAD_BATCH_MAX_NUM_FILES):
        batch_actions_chunk, batch_errors_chunk = post_lfs_batch_info(
            upload_infos=[op.upload_info for op in chunk],
            repo_id=repo_id,
            repo_type=repo_type,
            revision=revision,
            endpoint=endpoint,
            headers=headers,
            token=None,  # already passed in 'headers'
        )

        # If at least 1 error, we do not retrieve information for other chunks
        if batch_errors_chunk:
            message = "\n".join(
                [
                    f"Encountered error for file with OID {err.get('oid')}: `{err.get('error', {}).get('message')}"
                    for err in batch_errors_chunk
                ]
            )
            raise ValueError(f"LFS batch endpoint returned errors:\n{message}")

        batch_actions += batch_actions_chunk
    oid2addop = {add_op.upload_info.sha256.hex(): add_op for add_op in additions}

    # Step 2: ignore files that have already been uploaded
    filtered_actions = []
    for action in batch_actions:
        if action.get("actions") is None:
            logger.debug(
                f"Content of file {oid2addop[action['oid']].path_in_repo} is already"
                " present upstream - skipping upload."
            )
        else:
            filtered_actions.append(action)

    if len(filtered_actions) == 0:
        logger.debug("No LFS files to upload.")
        return

    # Step 3: upload files concurrently according to these instructions
    def _wrapped_lfs_upload(batch_action) -> None:
        try:
            operation = oid2addop[batch_action["oid"]]
            lfs_upload(operation=operation, lfs_batch_action=batch_action, headers=headers, endpoint=endpoint)
        except Exception as exc:
            raise RuntimeError(f"Error while uploading '{operation.path_in_repo}' to the Hub.") from exc

    if constants.HF_HUB_ENABLE_HF_TRANSFER:
        logger.debug(f"Uploading {len(filtered_actions)} LFS files to the Hub using `hf_transfer`.")
        for action in hf_tqdm(filtered_actions, name="huggingface_hub.lfs_upload"):
            _wrapped_lfs_upload(action)
    elif len(filtered_actions) == 1:
        logger.debug("Uploading 1 LFS file to the Hub")
        _wrapped_lfs_upload(filtered_actions[0])
    else:
        logger.debug(
            f"Uploading {len(filtered_actions)} LFS files to the Hub using up to {num_threads} threads concurrently"
        )
        thread_map(
            _wrapped_lfs_upload,
            filtered_actions,
            desc=f"Upload {len(filtered_actions)} LFS files",
            max_workers=num_threads,
            tqdm_class=hf_tqdm,
        )


@validate_hf_hub_args
def _upload_xet_files(
    *,
    additions: List[CommitOperationAdd],
    repo_type: str,
    repo_id: str,
    headers: Dict[str, str],
    endpoint: Optional[str] = None,
    revision: Optional[str] = None,
    create_pr: Optional[bool] = None,
):
    """
    Uploads the content of `additions` to the Hub using the xet storage protocol.
    This chunks the files and deduplicates the chunks before uploading them to xetcas storage.

    Args:
        additions (`List` of `CommitOperationAdd`):
            The files to be uploaded.
        repo_type (`str`):
            Type of the repo to upload to: `"model"`, `"dataset"` or `"space"`.
        repo_id (`str`):
            A namespace (user or an organization) and a repo name separated
            by a `/`.
        headers (`Dict[str, str]`):
            Headers to use for the request, including authorization headers and user agent.
        endpoint: (`str`, *optional*):
            The endpoint to use for the xetcas service. Defaults to `constants.ENDPOINT`.
        revision (`str`, *optional*):
            The git revision to upload to.
        create_pr (`bool`, *optional*):
            Whether or not to create a Pull Request with that commit.

    Raises:
        [`EnvironmentError`](https://docs.python.org/3/library/exceptions.html#EnvironmentError)
            If an upload failed for any reason.
        [`ValueError`](https://docs.python.org/3/library/exceptions.html#ValueError)
            If the server returns malformed responses or if the user is unauthorized to upload to xet storage.
        [`HTTPError`](https://requests.readthedocs.io/en/latest/api/#requests.HTTPError)
            If the LFS batch endpoint returned an HTTP error.

    **How it works:**
        The file download system uses Xet storage, which is a content-addressable storage system that breaks files into chunks
            for efficient storage and transfer.

        `hf_xet.upload_files` manages uploading files by:
            - Taking a list of file paths to upload
            - Breaking files into smaller chunks for efficient storage
            - Avoiding duplicate storage by recognizing identical chunks across files
            - Connecting to a storage server (CAS server) that manages these chunks

        The upload process works like this:
        1. Create a local folder at ~/.cache/huggingface/xet/chunk-cache to store file chunks for reuse.
        2. Process files in parallel (up to 8 files at once):
            2.1. Read the file content.
            2.2. Split the file content into smaller chunks based on content patterns: each chunk gets a unique ID based on what's in it.
            2.3. For each chunk:
                - Check if it already exists in storage.
                - Skip uploading chunks that already exist.
            2.4. Group chunks into larger blocks for efficient transfer.
            2.5. Upload these blocks to the storage server.
            2.6. Create and upload information about how the file is structured.
        3. Return reference files that contain information about the uploaded files, which can be used later to download them.
    """
    if len(additions) == 0:
        return
    # at this point, we know that hf_xet is installed
    from hf_xet import upload_bytes, upload_files

    try:
        xet_connection_info = fetch_xet_connection_info_from_repo_info(
            token_type=XetTokenType.WRITE,
            repo_id=repo_id,
            repo_type=repo_type,
            revision=revision,
            headers=headers,
            endpoint=endpoint,
            params={"create_pr": "1"} if create_pr else None,
        )
    except HfHubHTTPError as e:
        if e.response.status_code == 401:
            raise XetAuthorizationError(
                f"You are unauthorized to upload to xet storage for {repo_type}/{repo_id}. "
                f"Please check that you have configured your access token with write access to the repo."
            ) from e
        raise

    xet_endpoint = xet_connection_info.endpoint
    access_token_info = (xet_connection_info.access_token, xet_connection_info.expiration_unix_epoch)

    def token_refresher() -> Tuple[str, int]:
        new_xet_connection = fetch_xet_connection_info_from_repo_info(
            token_type=XetTokenType.WRITE,
            repo_id=repo_id,
            repo_type=repo_type,
            revision=revision,
            headers=headers,
            endpoint=endpoint,
            params={"create_pr": "1"} if create_pr else None,
        )
        if new_xet_connection is None:
            raise XetRefreshTokenError("Failed to refresh xet token")
        return new_xet_connection.access_token, new_xet_connection.expiration_unix_epoch

    num_chunks = math.ceil(len(additions) / UPLOAD_BATCH_MAX_NUM_FILES)
    num_chunks_num_digits = int(math.log10(num_chunks)) + 1
    for i, chunk in enumerate(chunk_iterable(additions, chunk_size=UPLOAD_BATCH_MAX_NUM_FILES)):
        _chunk = [op for op in chunk]

        bytes_ops = [op for op in _chunk if isinstance(op.path_or_fileobj, bytes)]
        paths_ops = [op for op in _chunk if isinstance(op.path_or_fileobj, (str, Path))]
        expected_size = sum(op.upload_info.size for op in bytes_ops + paths_ops)

        if num_chunks > 1:
            description = f"Uploading Batch [{str(i + 1).zfill(num_chunks_num_digits)}/{num_chunks}]..."
        else:
            description = "Uploading..."
        progress_cm = _get_progress_bar_context(
            desc=description,
            total=expected_size,
            initial=0,
            unit="B",
            unit_scale=True,
            name="huggingface_hub.xet_put",
            log_level=logger.getEffectiveLevel(),
        )
        with progress_cm as progress:

            def update_progress(increment: int):
                progress.update(increment)

            if len(paths_ops) > 0:
                upload_files(
                    [str(op.path_or_fileobj) for op in paths_ops],
                    xet_endpoint,
                    access_token_info,
                    token_refresher,
                    update_progress,
                    repo_type,
                )
            if len(bytes_ops) > 0:
                upload_bytes(
                    [op.path_or_fileobj for op in bytes_ops],
                    xet_endpoint,
                    access_token_info,
                    token_refresher,
                    update_progress,
                    repo_type,
                )
    return


def _validate_preupload_info(preupload_info: dict):
    files = preupload_info.get("files")
    if not isinstance(files, list):
        raise ValueError("preupload_info is improperly formatted")
    for file_info in files:
        if not (
            isinstance(file_info, dict)
            and isinstance(file_info.get("path"), str)
            and isinstance(file_info.get("uploadMode"), str)
            and (file_info["uploadMode"] in ("lfs", "regular"))
        ):
            raise ValueError("preupload_info is improperly formatted:")
    return preupload_info


@validate_hf_hub_args
def _fetch_upload_modes(
    additions: Iterable[CommitOperationAdd],
    repo_type: str,
    repo_id: str,
    headers: Dict[str, str],
    revision: str,
    endpoint: Optional[str] = None,
    create_pr: bool = False,
    gitignore_content: Optional[str] = None,
) -> None:
    """
    Requests the Hub "preupload" endpoint to determine whether each input file should be uploaded as a regular git blob,
    as a git LFS blob, or as a XET file. Input `additions` are mutated in-place with the upload mode.

    Args:
        additions (`Iterable` of :class:`CommitOperationAdd`):
            Iterable of :class:`CommitOperationAdd` describing the files to
            upload to the Hub.
        repo_type (`str`):
            Type of the repo to upload to: `"model"`, `"dataset"` or `"space"`.
        repo_id (`str`):
            A namespace (user or an organization) and a repo name separated
            by a `/`.
        headers (`Dict[str, str]`):
            Headers to use for the request, including authorization headers and user agent.
        revision (`str`):
            The git revision to upload the files to. Can be any valid git revision.
        gitignore_content (`str`, *optional*):
            The content of the `.gitignore` file to know which files should be ignored. The order of priority
            is to first check if `gitignore_content` is passed, then check if the `.gitignore` file is present
            in the list of files to commit and finally default to the `.gitignore` file already hosted on the Hub
            (if any).
    Raises:
        [`~utils.HfHubHTTPError`]
            If the Hub API returned an error.
        [`ValueError`](https://docs.python.org/3/library/exceptions.html#ValueError)
            If the Hub API response is improperly formatted.
    """
    endpoint = endpoint if endpoint is not None else constants.ENDPOINT

    # Fetch upload mode (LFS or regular) chunk by chunk.
    upload_modes: Dict[str, UploadMode] = {}
    should_ignore_info: Dict[str, bool] = {}
    oid_info: Dict[str, Optional[str]] = {}

    for chunk in chunk_iterable(additions, 256):
        payload: Dict = {
            "files": [
                {
                    "path": op.path_in_repo,
                    "sample": base64.b64encode(op.upload_info.sample).decode("ascii"),
                    "size": op.upload_info.size,
                }
                for op in chunk
            ]
        }
        if gitignore_content is not None:
            payload["gitIgnore"] = gitignore_content

        resp = get_session().post(
            f"{endpoint}/api/{repo_type}s/{repo_id}/preupload/{revision}",
            json=payload,
            headers=headers,
            params={"create_pr": "1"} if create_pr else None,
        )
        hf_raise_for_status(resp)
        preupload_info = _validate_preupload_info(resp.json())
        upload_modes.update(**{file["path"]: file["uploadMode"] for file in preupload_info["files"]})
        should_ignore_info.update(**{file["path"]: file["shouldIgnore"] for file in preupload_info["files"]})
        oid_info.update(**{file["path"]: file.get("oid") for file in preupload_info["files"]})

    # Set upload mode for each addition operation
    for addition in additions:
        addition._upload_mode = upload_modes[addition.path_in_repo]
        addition._should_ignore = should_ignore_info[addition.path_in_repo]
        addition._remote_oid = oid_info[addition.path_in_repo]

    # Empty files cannot be uploaded as LFS (S3 would fail with a 501 Not Implemented)
    # => empty files are uploaded as "regular" to still allow users to commit them.
    for addition in additions:
        if addition.upload_info.size == 0:
            addition._upload_mode = "regular"


@validate_hf_hub_args
def _fetch_files_to_copy(
    copies: Iterable[CommitOperationCopy],
    repo_type: str,
    repo_id: str,
    headers: Dict[str, str],
    revision: str,
    endpoint: Optional[str] = None,
) -> Dict[Tuple[str, Optional[str]], Union["RepoFile", bytes]]:
    """
    Fetch information about the files to copy.

    For LFS files, we only need their metadata (file size and sha256) while for regular files
    we need to download the raw content from the Hub.

    Args:
        copies (`Iterable` of :class:`CommitOperationCopy`):
            Iterable of :class:`CommitOperationCopy` describing the files to
            copy on the Hub.
        repo_type (`str`):
            Type of the repo to upload to: `"model"`, `"dataset"` or `"space"`.
        repo_id (`str`):
            A namespace (user or an organization) and a repo name separated
            by a `/`.
        headers (`Dict[str, str]`):
            Headers to use for the request, including authorization headers and user agent.
        revision (`str`):
            The git revision to upload the files to. Can be any valid git revision.

    Returns: `Dict[Tuple[str, Optional[str]], Union[RepoFile, bytes]]]`
        Key is the file path and revision of the file to copy.
        Value is the raw content as bytes (for regular files) or the file information as a RepoFile (for LFS files).

    Raises:
        [`~utils.HfHubHTTPError`]
            If the Hub API returned an error.
        [`ValueError`](https://docs.python.org/3/library/exceptions.html#ValueError)
            If the Hub API response is improperly formatted.
    """
    from .hf_api import HfApi, RepoFolder

    hf_api = HfApi(endpoint=endpoint, headers=headers)
    files_to_copy: Dict[Tuple[str, Optional[str]], Union["RepoFile", bytes]] = {}
    # Store (path, revision) -> oid mapping
    oid_info: Dict[Tuple[str, Optional[str]], Optional[str]] = {}
    # 1. Fetch OIDs for destination paths in batches.
    dest_paths = [op.path_in_repo for op in copies]
    for offset in range(0, len(dest_paths), FETCH_LFS_BATCH_SIZE):
        dest_repo_files = hf_api.get_paths_info(
            repo_id=repo_id,
            paths=dest_paths[offset : offset + FETCH_LFS_BATCH_SIZE],
            revision=revision,
            repo_type=repo_type,
        )
        for file in dest_repo_files:
            if not isinstance(file, RepoFolder):
                oid_info[(file.path, revision)] = file.blob_id

    # 2. Group by source revision and fetch source file info in batches.
    for src_revision, operations in groupby(copies, key=lambda op: op.src_revision):
        operations = list(operations)  # type: ignore
        src_paths = [op.src_path_in_repo for op in operations]
        for offset in range(0, len(src_paths), FETCH_LFS_BATCH_SIZE):
            src_repo_files = hf_api.get_paths_info(
                repo_id=repo_id,
                paths=src_paths[offset : offset + FETCH_LFS_BATCH_SIZE],
                revision=src_revision or revision,
                repo_type=repo_type,
            )

            for src_repo_file in src_repo_files:
                if isinstance(src_repo_file, RepoFolder):
                    raise NotImplementedError("Copying a folder is not implemented.")
                oid_info[(src_repo_file.path, src_revision)] = src_repo_file.blob_id
                # If it's an LFS file, store the RepoFile object. Otherwise, download raw bytes.
                if src_repo_file.lfs:
                    files_to_copy[(src_repo_file.path, src_revision)] = src_repo_file
                else:
                    # TODO: (optimization) download regular files to copy concurrently
                    url = hf_hub_url(
                        endpoint=endpoint,
                        repo_type=repo_type,
                        repo_id=repo_id,
                        revision=src_revision or revision,
                        filename=src_repo_file.path,
                    )
                    response = get_session().get(url, headers=headers)
                    hf_raise_for_status(response)
                    files_to_copy[(src_repo_file.path, src_revision)] = response.content
        # 3. Ensure all operations found a corresponding file in the Hub
        #  and track src/dest OIDs for each operation.
        for operation in operations:
            if (operation.src_path_in_repo, src_revision) not in files_to_copy:
                raise EntryNotFoundError(
                    f"Cannot copy {operation.src_path_in_repo} at revision "
                    f"{src_revision or revision}: file is missing on repo."
                )
            operation._src_oid = oid_info.get((operation.src_path_in_repo, operation.src_revision))
            operation._dest_oid = oid_info.get((operation.path_in_repo, revision))
    return files_to_copy


def _prepare_commit_payload(
    operations: Iterable[CommitOperation],
    files_to_copy: Dict[Tuple[str, Optional[str]], Union["RepoFile", bytes]],
    commit_message: str,
    commit_description: Optional[str] = None,
    parent_commit: Optional[str] = None,
) -> Iterable[Dict[str, Any]]:
    """
    Builds the payload to POST to the `/commit` API of the Hub.

    Payload is returned as an iterator so that it can be streamed as a ndjson in the
    POST request.

    For more information, see:
        - https://github.com/huggingface/huggingface_hub/issues/1085#issuecomment-1265208073
        - http://ndjson.org/
    """
    commit_description = commit_description if commit_description is not None else ""

    # 1. Send a header item with the commit metadata
    header_value = {"summary": commit_message, "description": commit_description}
    if parent_commit is not None:
        header_value["parentCommit"] = parent_commit
    yield {"key": "header", "value": header_value}

    nb_ignored_files = 0

    # 2. Send operations, one per line
    for operation in operations:
        # Skip ignored files
        if isinstance(operation, CommitOperationAdd) and operation._should_ignore:
            logger.debug(f"Skipping file '{operation.path_in_repo}' in commit (ignored by gitignore file).")
            nb_ignored_files += 1
            continue

        # 2.a. Case adding a regular file
        if isinstance(operation, CommitOperationAdd) and operation._upload_mode == "regular":
            yield {
                "key": "file",
                "value": {
                    "content": operation.b64content().decode(),
                    "path": operation.path_in_repo,
                    "encoding": "base64",
                },
            }
        # 2.b. Case adding an LFS file
        elif isinstance(operation, CommitOperationAdd) and operation._upload_mode == "lfs":
            yield {
                "key": "lfsFile",
                "value": {
                    "path": operation.path_in_repo,
                    "algo": "sha256",
                    "oid": operation.upload_info.sha256.hex(),
                    "size": operation.upload_info.size,
                },
            }
        # 2.c. Case deleting a file or folder
        elif isinstance(operation, CommitOperationDelete):
            yield {
                "key": "deletedFolder" if operation.is_folder else "deletedFile",
                "value": {"path": operation.path_in_repo},
            }
        # 2.d. Case copying a file or folder
        elif isinstance(operation, CommitOperationCopy):
            file_to_copy = files_to_copy[(operation.src_path_in_repo, operation.src_revision)]
            if isinstance(file_to_copy, bytes):
                yield {
                    "key": "file",
                    "value": {
                        "content": base64.b64encode(file_to_copy).decode(),
                        "path": operation.path_in_repo,
                        "encoding": "base64",
                    },
                }
            elif file_to_copy.lfs:
                yield {
                    "key": "lfsFile",
                    "value": {
                        "path": operation.path_in_repo,
                        "algo": "sha256",
                        "oid": file_to_copy.lfs.sha256,
                    },
                }
            else:
                raise ValueError(
                    "Malformed files_to_copy (should be raw file content as bytes or RepoFile objects with LFS info."
                )
        # 2.e. Never expected to happen
        else:
            raise ValueError(
                f"Unknown operation to commit. Operation: {operation}. Upload mode:"
                f" {getattr(operation, '_upload_mode', None)}"
            )

    if nb_ignored_files > 0:
        logger.info(f"Skipped {nb_ignored_files} file(s) in commit (ignored by gitignore file).")

# === NexusCore/openenv\Lib\site-packages\matplotlib\mlab.py ===
"""
Numerical Python functions written for compatibility with MATLAB
commands with the same names. Most numerical Python functions can be found in
the `NumPy`_ and `SciPy`_ libraries. What remains here is code for performing
spectral computations and kernel density estimations.

.. _NumPy: https://numpy.org
.. _SciPy: https://www.scipy.org

Spectral functions
------------------

`cohere`
    Coherence (normalized cross spectral density)

`csd`
    Cross spectral density using Welch's average periodogram

`detrend`
    Remove the mean or best fit line from an array

`psd`
    Power spectral density using Welch's average periodogram

`specgram`
    Spectrogram (spectrum over segments of time)

`complex_spectrum`
    Return the complex-valued frequency spectrum of a signal

`magnitude_spectrum`
    Return the magnitude of the frequency spectrum of a signal

`angle_spectrum`
    Return the angle (wrapped phase) of the frequency spectrum of a signal

`phase_spectrum`
    Return the phase (unwrapped angle) of the frequency spectrum of a signal

`detrend_mean`
    Remove the mean from a line.

`detrend_linear`
    Remove the best fit line from a line.

`detrend_none`
    Return the original line.
"""

import functools
from numbers import Number

import numpy as np

from matplotlib import _api, _docstring, cbook


def window_hanning(x):
    """
    Return *x* times the Hanning (or Hann) window of len(*x*).

    See Also
    --------
    window_none : Another window algorithm.
    """
    return np.hanning(len(x))*x


def window_none(x):
    """
    No window function; simply return *x*.

    See Also
    --------
    window_hanning : Another window algorithm.
    """
    return x


def detrend(x, key=None, axis=None):
    """
    Return *x* with its trend removed.

    Parameters
    ----------
    x : array or sequence
        Array or sequence containing the data.

    key : {'default', 'constant', 'mean', 'linear', 'none'} or function
        The detrending algorithm to use. 'default', 'mean', and 'constant' are
        the same as `detrend_mean`. 'linear' is the same as `detrend_linear`.
        'none' is the same as `detrend_none`. The default is 'mean'. See the
        corresponding functions for more details regarding the algorithms. Can
        also be a function that carries out the detrend operation.

    axis : int
        The axis along which to do the detrending.

    See Also
    --------
    detrend_mean : Implementation of the 'mean' algorithm.
    detrend_linear : Implementation of the 'linear' algorithm.
    detrend_none : Implementation of the 'none' algorithm.
    """
    if key is None or key in ['constant', 'mean', 'default']:
        return detrend(x, key=detrend_mean, axis=axis)
    elif key == 'linear':
        return detrend(x, key=detrend_linear, axis=axis)
    elif key == 'none':
        return detrend(x, key=detrend_none, axis=axis)
    elif callable(key):
        x = np.asarray(x)
        if axis is not None and axis + 1 > x.ndim:
            raise ValueError(f'axis(={axis}) out of bounds')
        if (axis is None and x.ndim == 0) or (not axis and x.ndim == 1):
            return key(x)
        # try to use the 'axis' argument if the function supports it,
        # otherwise use apply_along_axis to do it
        try:
            return key(x, axis=axis)
        except TypeError:
            return np.apply_along_axis(key, axis=axis, arr=x)
    else:
        raise ValueError(
            f"Unknown value for key: {key!r}, must be one of: 'default', "
            f"'constant', 'mean', 'linear', or a function")


def detrend_mean(x, axis=None):
    """
    Return *x* minus the mean(*x*).

    Parameters
    ----------
    x : array or sequence
        Array or sequence containing the data
        Can have any dimensionality

    axis : int
        The axis along which to take the mean.  See `numpy.mean` for a
        description of this argument.

    See Also
    --------
    detrend_linear : Another detrend algorithm.
    detrend_none : Another detrend algorithm.
    detrend : A wrapper around all the detrend algorithms.
    """
    x = np.asarray(x)

    if axis is not None and axis+1 > x.ndim:
        raise ValueError('axis(=%s) out of bounds' % axis)

    return x - x.mean(axis, keepdims=True)


def detrend_none(x, axis=None):
    """
    Return *x*: no detrending.

    Parameters
    ----------
    x : any object
        An object containing the data

    axis : int
        This parameter is ignored.
        It is included for compatibility with detrend_mean

    See Also
    --------
    detrend_mean : Another detrend algorithm.
    detrend_linear : Another detrend algorithm.
    detrend : A wrapper around all the detrend algorithms.
    """
    return x


def detrend_linear(y):
    """
    Return *x* minus best fit line; 'linear' detrending.

    Parameters
    ----------
    y : 0-D or 1-D array or sequence
        Array or sequence containing the data

    See Also
    --------
    detrend_mean : Another detrend algorithm.
    detrend_none : Another detrend algorithm.
    detrend : A wrapper around all the detrend algorithms.
    """
    # This is faster than an algorithm based on linalg.lstsq.
    y = np.asarray(y)

    if y.ndim > 1:
        raise ValueError('y cannot have ndim > 1')

    # short-circuit 0-D array.
    if not y.ndim:
        return np.array(0., dtype=y.dtype)

    x = np.arange(y.size, dtype=float)

    C = np.cov(x, y, bias=1)
    b = C[0, 1]/C[0, 0]

    a = y.mean() - b*x.mean()
    return y - (b*x + a)


def _spectral_helper(x, y=None, NFFT=None, Fs=None, detrend_func=None,
                     window=None, noverlap=None, pad_to=None,
                     sides=None, scale_by_freq=None, mode=None):
    """
    Private helper implementing the common parts between the psd, csd,
    spectrogram and complex, magnitude, angle, and phase spectrums.
    """
    if y is None:
        # if y is None use x for y
        same_data = True
    else:
        # The checks for if y is x are so that we can use the same function to
        # implement the core of psd(), csd(), and spectrogram() without doing
        # extra calculations.  We return the unaveraged Pxy, freqs, and t.
        same_data = y is x

    if Fs is None:
        Fs = 2
    if noverlap is None:
        noverlap = 0
    if detrend_func is None:
        detrend_func = detrend_none
    if window is None:
        window = window_hanning

    # if NFFT is set to None use the whole signal
    if NFFT is None:
        NFFT = 256

    if noverlap >= NFFT:
        raise ValueError('noverlap must be less than NFFT')

    if mode is None or mode == 'default':
        mode = 'psd'
    _api.check_in_list(
        ['default', 'psd', 'complex', 'magnitude', 'angle', 'phase'],
        mode=mode)

    if not same_data and mode != 'psd':
        raise ValueError("x and y must be equal if mode is not 'psd'")

    # Make sure we're dealing with a numpy array. If y and x were the same
    # object to start with, keep them that way
    x = np.asarray(x)
    if not same_data:
        y = np.asarray(y)

    if sides is None or sides == 'default':
        if np.iscomplexobj(x):
            sides = 'twosided'
        else:
            sides = 'onesided'
    _api.check_in_list(['default', 'onesided', 'twosided'], sides=sides)

    # zero pad x and y up to NFFT if they are shorter than NFFT
    if len(x) < NFFT:
        n = len(x)
        x = np.resize(x, NFFT)
        x[n:] = 0

    if not same_data and len(y) < NFFT:
        n = len(y)
        y = np.resize(y, NFFT)
        y[n:] = 0

    if pad_to is None:
        pad_to = NFFT

    if mode != 'psd':
        scale_by_freq = False
    elif scale_by_freq is None:
        scale_by_freq = True

    # For real x, ignore the negative frequencies unless told otherwise
    if sides == 'twosided':
        numFreqs = pad_to
        if pad_to % 2:
            freqcenter = (pad_to - 1)//2 + 1
        else:
            freqcenter = pad_to//2
        scaling_factor = 1.
    elif sides == 'onesided':
        if pad_to % 2:
            numFreqs = (pad_to + 1)//2
        else:
            numFreqs = pad_to//2 + 1
        scaling_factor = 2.

    if not np.iterable(window):
        window = window(np.ones(NFFT, x.dtype))
    if len(window) != NFFT:
        raise ValueError(
            "The window length must match the data's first dimension")

    result = np.lib.stride_tricks.sliding_window_view(
        x, NFFT, axis=0)[::NFFT - noverlap].T
    result = detrend(result, detrend_func, axis=0)
    result = result * window.reshape((-1, 1))
    result = np.fft.fft(result, n=pad_to, axis=0)[:numFreqs, :]
    freqs = np.fft.fftfreq(pad_to, 1/Fs)[:numFreqs]

    if not same_data:
        # if same_data is False, mode must be 'psd'
        resultY = np.lib.stride_tricks.sliding_window_view(
            y, NFFT, axis=0)[::NFFT - noverlap].T
        resultY = detrend(resultY, detrend_func, axis=0)
        resultY = resultY * window.reshape((-1, 1))
        resultY = np.fft.fft(resultY, n=pad_to, axis=0)[:numFreqs, :]
        result = np.conj(result) * resultY
    elif mode == 'psd':
        result = np.conj(result) * result
    elif mode == 'magnitude':
        result = np.abs(result) / window.sum()
    elif mode == 'angle' or mode == 'phase':
        # we unwrap the phase later to handle the onesided vs. twosided case
        result = np.angle(result)
    elif mode == 'complex':
        result /= window.sum()

    if mode == 'psd':

        # Also include scaling factors for one-sided densities and dividing by
        # the sampling frequency, if desired. Scale everything, except the DC
        # component and the NFFT/2 component:

        # if we have a even number of frequencies, don't scale NFFT/2
        if not NFFT % 2:
            slc = slice(1, -1, None)
        # if we have an odd number, just don't scale DC
        else:
            slc = slice(1, None, None)

        result[slc] *= scaling_factor

        # MATLAB divides by the sampling frequency so that density function
        # has units of dB/Hz and can be integrated by the plotted frequency
        # values. Perform the same scaling here.
        if scale_by_freq:
            result /= Fs
            # Scale the spectrum by the norm of the window to compensate for
            # windowing loss; see Bendat & Piersol Sec 11.5.2.
            result /= (window**2).sum()
        else:
            # In this case, preserve power in the segment, not amplitude
            result /= window.sum()**2

    t = np.arange(NFFT/2, len(x) - NFFT/2 + 1, NFFT - noverlap)/Fs

    if sides == 'twosided':
        # center the frequency range at zero
        freqs = np.roll(freqs, -freqcenter, axis=0)
        result = np.roll(result, -freqcenter, axis=0)
    elif not pad_to % 2:
        # get the last value correctly, it is negative otherwise
        freqs[-1] *= -1

    # we unwrap the phase here to handle the onesided vs. twosided case
    if mode == 'phase':
        result = np.unwrap(result, axis=0)

    return result, freqs, t


def _single_spectrum_helper(
        mode, x, Fs=None, window=None, pad_to=None, sides=None):
    """
    Private helper implementing the commonality between the complex, magnitude,
    angle, and phase spectrums.
    """
    _api.check_in_list(['complex', 'magnitude', 'angle', 'phase'], mode=mode)

    if pad_to is None:
        pad_to = len(x)

    spec, freqs, _ = _spectral_helper(x=x, y=None, NFFT=len(x), Fs=Fs,
                                      detrend_func=detrend_none, window=window,
                                      noverlap=0, pad_to=pad_to,
                                      sides=sides,
                                      scale_by_freq=False,
                                      mode=mode)
    if mode != 'complex':
        spec = spec.real

    if spec.ndim == 2 and spec.shape[1] == 1:
        spec = spec[:, 0]

    return spec, freqs


# Split out these keyword docs so that they can be used elsewhere
_docstring.interpd.register(
    Spectral="""\
Fs : float, default: 2
    The sampling frequency (samples per time unit).  It is used to calculate
    the Fourier frequencies, *freqs*, in cycles per time unit.

window : callable or ndarray, default: `.window_hanning`
    A function or a vector of length *NFFT*.  To create window vectors see
    `.window_hanning`, `.window_none`, `numpy.blackman`, `numpy.hamming`,
    `numpy.bartlett`, `scipy.signal`, `scipy.signal.get_window`, etc.  If a
    function is passed as the argument, it must take a data segment as an
    argument and return the windowed version of the segment.

sides : {'default', 'onesided', 'twosided'}, optional
    Which sides of the spectrum to return. 'default' is one-sided for real
    data and two-sided for complex data. 'onesided' forces the return of a
    one-sided spectrum, while 'twosided' forces two-sided.""",

    Single_Spectrum="""\
pad_to : int, optional
    The number of points to which the data segment is padded when performing
    the FFT.  While not increasing the actual resolution of the spectrum (the
    minimum distance between resolvable peaks), this can give more points in
    the plot, allowing for more detail. This corresponds to the *n* parameter
    in the call to `~numpy.fft.fft`.  The default is None, which sets *pad_to*
    equal to the length of the input signal (i.e. no padding).""",

    PSD="""\
pad_to : int, optional
    The number of points to which the data segment is padded when performing
    the FFT.  This can be different from *NFFT*, which specifies the number
    of data points used.  While not increasing the actual resolution of the
    spectrum (the minimum distance between resolvable peaks), this can give
    more points in the plot, allowing for more detail. This corresponds to
    the *n* parameter in the call to `~numpy.fft.fft`. The default is None,
    which sets *pad_to* equal to *NFFT*

NFFT : int, default: 256
    The number of data points used in each block for the FFT.  A power 2 is
    most efficient.  This should *NOT* be used to get zero padding, or the
    scaling of the result will be incorrect; use *pad_to* for this instead.

detrend : {'none', 'mean', 'linear'} or callable, default: 'none'
    The function applied to each segment before fft-ing, designed to remove
    the mean or linear trend.  Unlike in MATLAB, where the *detrend* parameter
    is a vector, in Matplotlib it is a function.  The :mod:`~matplotlib.mlab`
    module defines `.detrend_none`, `.detrend_mean`, and `.detrend_linear`,
    but you can use a custom function as well.  You can also use a string to
    choose one of the functions: 'none' calls `.detrend_none`. 'mean' calls
    `.detrend_mean`. 'linear' calls `.detrend_linear`.

scale_by_freq : bool, default: True
    Whether the resulting density values should be scaled by the scaling
    frequency, which gives density in units of 1/Hz.  This allows for
    integration over the returned frequency values.  The default is True for
    MATLAB compatibility.""")


@_docstring.interpd
def psd(x, NFFT=None, Fs=None, detrend=None, window=None,
        noverlap=None, pad_to=None, sides=None, scale_by_freq=None):
    r"""
    Compute the power spectral density.

    The power spectral density :math:`P_{xx}` by Welch's average
    periodogram method.  The vector *x* is divided into *NFFT* length
    segments.  Each segment is detrended by function *detrend* and
    windowed by function *window*.  *noverlap* gives the length of
    the overlap between segments.  The :math:`|\mathrm{fft}(i)|^2`
    of each segment :math:`i` are averaged to compute :math:`P_{xx}`.

    If len(*x*) < *NFFT*, it will be zero padded to *NFFT*.

    Parameters
    ----------
    x : 1-D array or sequence
        Array or sequence containing the data

    %(Spectral)s

    %(PSD)s

    noverlap : int, default: 0 (no overlap)
        The number of points of overlap between segments.

    Returns
    -------
    Pxx : 1-D array
        The values for the power spectrum :math:`P_{xx}` (real valued)

    freqs : 1-D array
        The frequencies corresponding to the elements in *Pxx*

    References
    ----------
    Bendat & Piersol -- Random Data: Analysis and Measurement Procedures, John
    Wiley & Sons (1986)

    See Also
    --------
    specgram
        `specgram` differs in the default overlap; in not returning the mean of
        the segment periodograms; and in returning the times of the segments.

    magnitude_spectrum : returns the magnitude spectrum.

    csd : returns the spectral density between two signals.
    """
    Pxx, freqs = csd(x=x, y=None, NFFT=NFFT, Fs=Fs, detrend=detrend,
                     window=window, noverlap=noverlap, pad_to=pad_to,
                     sides=sides, scale_by_freq=scale_by_freq)
    return Pxx.real, freqs


@_docstring.interpd
def csd(x, y, NFFT=None, Fs=None, detrend=None, window=None,
        noverlap=None, pad_to=None, sides=None, scale_by_freq=None):
    """
    Compute the cross-spectral density.

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
        Arrays or sequences containing the data

    %(Spectral)s

    %(PSD)s

    noverlap : int, default: 0 (no overlap)
        The number of points of overlap between segments.

    Returns
    -------
    Pxy : 1-D array
        The values for the cross spectrum :math:`P_{xy}` before scaling (real
        valued)

    freqs : 1-D array
        The frequencies corresponding to the elements in *Pxy*

    References
    ----------
    Bendat & Piersol -- Random Data: Analysis and Measurement Procedures, John
    Wiley & Sons (1986)

    See Also
    --------
    psd : equivalent to setting ``y = x``.
    """
    if NFFT is None:
        NFFT = 256
    Pxy, freqs, _ = _spectral_helper(x=x, y=y, NFFT=NFFT, Fs=Fs,
                                     detrend_func=detrend, window=window,
                                     noverlap=noverlap, pad_to=pad_to,
                                     sides=sides, scale_by_freq=scale_by_freq,
                                     mode='psd')

    if Pxy.ndim == 2:
        if Pxy.shape[1] > 1:
            Pxy = Pxy.mean(axis=1)
        else:
            Pxy = Pxy[:, 0]
    return Pxy, freqs


_single_spectrum_docs = """\
Compute the {quantity} of *x*.
Data is padded to a length of *pad_to* and the windowing function *window* is
applied to the signal.

Parameters
----------
x : 1-D array or sequence
    Array or sequence containing the data

{Spectral}

{Single_Spectrum}

Returns
-------
spectrum : 1-D array
    The {quantity}.
freqs : 1-D array
    The frequencies corresponding to the elements in *spectrum*.

See Also
--------
psd
    Returns the power spectral density.
complex_spectrum
    Returns the complex-valued frequency spectrum.
magnitude_spectrum
    Returns the absolute value of the `complex_spectrum`.
angle_spectrum
    Returns the angle of the `complex_spectrum`.
phase_spectrum
    Returns the phase (unwrapped angle) of the `complex_spectrum`.
specgram
    Can return the complex spectrum of segments within the signal.
"""


complex_spectrum = functools.partial(_single_spectrum_helper, "complex")
complex_spectrum.__doc__ = _single_spectrum_docs.format(
    quantity="complex-valued frequency spectrum",
    **_docstring.interpd.params)
magnitude_spectrum = functools.partial(_single_spectrum_helper, "magnitude")
magnitude_spectrum.__doc__ = _single_spectrum_docs.format(
    quantity="magnitude (absolute value) of the frequency spectrum",
    **_docstring.interpd.params)
angle_spectrum = functools.partial(_single_spectrum_helper, "angle")
angle_spectrum.__doc__ = _single_spectrum_docs.format(
    quantity="angle of the frequency spectrum (wrapped phase spectrum)",
    **_docstring.interpd.params)
phase_spectrum = functools.partial(_single_spectrum_helper, "phase")
phase_spectrum.__doc__ = _single_spectrum_docs.format(
    quantity="phase of the frequency spectrum (unwrapped phase spectrum)",
    **_docstring.interpd.params)


@_docstring.interpd
def specgram(x, NFFT=None, Fs=None, detrend=None, window=None,
             noverlap=None, pad_to=None, sides=None, scale_by_freq=None,
             mode=None):
    """
    Compute a spectrogram.

    Compute and plot a spectrogram of data in *x*.  Data are split into
    *NFFT* length segments and the spectrum of each section is
    computed.  The windowing function *window* is applied to each
    segment, and the amount of overlap of each segment is
    specified with *noverlap*.

    Parameters
    ----------
    x : array-like
        1-D array or sequence.

    %(Spectral)s

    %(PSD)s

    noverlap : int, default: 128
        The number of points of overlap between blocks.
    mode : str, default: 'psd'
        What sort of spectrum to use:
            'psd'
                Returns the power spectral density.
            'complex'
                Returns the complex-valued frequency spectrum.
            'magnitude'
                Returns the magnitude spectrum.
            'angle'
                Returns the phase spectrum without unwrapping.
            'phase'
                Returns the phase spectrum with unwrapping.

    Returns
    -------
    spectrum : array-like
        2D array, columns are the periodograms of successive segments.

    freqs : array-like
        1-D array, frequencies corresponding to the rows in *spectrum*.

    t : array-like
        1-D array, the times corresponding to midpoints of segments
        (i.e the columns in *spectrum*).

    See Also
    --------
    psd : differs in the overlap and in the return values.
    complex_spectrum : similar, but with complex valued frequencies.
    magnitude_spectrum : similar single segment when *mode* is 'magnitude'.
    angle_spectrum : similar to single segment when *mode* is 'angle'.
    phase_spectrum : similar to single segment when *mode* is 'phase'.

    Notes
    -----
    *detrend* and *scale_by_freq* only apply when *mode* is set to 'psd'.

    """
    if noverlap is None:
        noverlap = 128  # default in _spectral_helper() is noverlap = 0
    if NFFT is None:
        NFFT = 256  # same default as in _spectral_helper()
    if len(x) <= NFFT:
        _api.warn_external("Only one segment is calculated since parameter "
                           f"NFFT (={NFFT}) >= signal length (={len(x)}).")

    spec, freqs, t = _spectral_helper(x=x, y=None, NFFT=NFFT, Fs=Fs,
                                      detrend_func=detrend, window=window,
                                      noverlap=noverlap, pad_to=pad_to,
                                      sides=sides,
                                      scale_by_freq=scale_by_freq,
                                      mode=mode)

    if mode != 'complex':
        spec = spec.real  # Needed since helper implements generically

    return spec, freqs, t


@_docstring.interpd
def cohere(x, y, NFFT=256, Fs=2, detrend=detrend_none, window=window_hanning,
           noverlap=0, pad_to=None, sides='default', scale_by_freq=None):
    r"""
    The coherence between *x* and *y*.  Coherence is the normalized
    cross spectral density:

    .. math::

        C_{xy} = \frac{|P_{xy}|^2}{P_{xx}P_{yy}}

    Parameters
    ----------
    x, y
        Array or sequence containing the data

    %(Spectral)s

    %(PSD)s

    noverlap : int, default: 0 (no overlap)
        The number of points of overlap between segments.

    Returns
    -------
    Cxy : 1-D array
        The coherence vector.
    freqs : 1-D array
            The frequencies for the elements in *Cxy*.

    See Also
    --------
    :func:`psd`, :func:`csd` :
        For information about the methods used to compute :math:`P_{xy}`,
        :math:`P_{xx}` and :math:`P_{yy}`.
    """
    if len(x) < 2 * NFFT:
        raise ValueError(
            "Coherence is calculated by averaging over *NFFT* length "
            "segments.  Your signal is too short for your choice of *NFFT*.")
    Pxx, f = psd(x, NFFT, Fs, detrend, window, noverlap, pad_to, sides,
                 scale_by_freq)
    Pyy, f = psd(y, NFFT, Fs, detrend, window, noverlap, pad_to, sides,
                 scale_by_freq)
    Pxy, f = csd(x, y, NFFT, Fs, detrend, window, noverlap, pad_to, sides,
                 scale_by_freq)
    Cxy = np.abs(Pxy) ** 2 / (Pxx * Pyy)
    return Cxy, f


class GaussianKDE:
    """
    Representation of a kernel-density estimate using Gaussian kernels.

    Parameters
    ----------
    dataset : array-like
        Datapoints to estimate from. In case of univariate data this is a 1-D
        array, otherwise a 2D array with shape (# of dims, # of data).
    bw_method : {'scott', 'silverman'} or float or callable, optional
        The method used to calculate the estimator bandwidth.  If a
        float, this will be used directly as `kde.factor`.  If a
        callable, it should take a `GaussianKDE` instance as only
        parameter and return a float. If None (default), 'scott' is used.

    Attributes
    ----------
    dataset : ndarray
        The dataset passed to the constructor.
    dim : int
        Number of dimensions.
    num_dp : int
        Number of datapoints.
    factor : float
        The bandwidth factor, obtained from `kde.covariance_factor`, with which
        the covariance matrix is multiplied.
    covariance : ndarray
        The covariance matrix of *dataset*, scaled by the calculated bandwidth
        (`kde.factor`).
    inv_cov : ndarray
        The inverse of *covariance*.

    Methods
    -------
    kde.evaluate(points) : ndarray
        Evaluate the estimated pdf on a provided set of points.
    kde(points) : ndarray
        Same as kde.evaluate(points)
    """

    # This implementation with minor modification was too good to pass up.
    # from scipy: https://github.com/scipy/scipy/blob/master/scipy/stats/kde.py

    def __init__(self, dataset, bw_method=None):
        self.dataset = np.atleast_2d(dataset)
        if not np.array(self.dataset).size > 1:
            raise ValueError("`dataset` input should have multiple elements.")

        self.dim, self.num_dp = np.array(self.dataset).shape

        if bw_method is None:
            pass
        elif cbook._str_equal(bw_method, 'scott'):
            self.covariance_factor = self.scotts_factor
        elif cbook._str_equal(bw_method, 'silverman'):
            self.covariance_factor = self.silverman_factor
        elif isinstance(bw_method, Number):
            self._bw_method = 'use constant'
            self.covariance_factor = lambda: bw_method
        elif callable(bw_method):
            self._bw_method = bw_method
            self.covariance_factor = lambda: self._bw_method(self)
        else:
            raise ValueError("`bw_method` should be 'scott', 'silverman', a "
                             "scalar or a callable")

        # Computes the covariance matrix for each Gaussian kernel using
        # covariance_factor().

        self.factor = self.covariance_factor()
        # Cache covariance and inverse covariance of the data
        if not hasattr(self, '_data_inv_cov'):
            self.data_covariance = np.atleast_2d(
                np.cov(
                    self.dataset,
                    rowvar=1,
                    bias=False))
            self.data_inv_cov = np.linalg.inv(self.data_covariance)

        self.covariance = self.data_covariance * self.factor ** 2
        self.inv_cov = self.data_inv_cov / self.factor ** 2
        self.norm_factor = (np.sqrt(np.linalg.det(2 * np.pi * self.covariance))
                            * self.num_dp)

    def scotts_factor(self):
        return np.power(self.num_dp, -1. / (self.dim + 4))

    def silverman_factor(self):
        return np.power(
            self.num_dp * (self.dim + 2.0) / 4.0, -1. / (self.dim + 4))

    #  Default method to calculate bandwidth, can be overwritten by subclass
    covariance_factor = scotts_factor

    def evaluate(self, points):
        """
        Evaluate the estimated pdf on a set of points.

        Parameters
        ----------
        points : (# of dimensions, # of points)-array
            Alternatively, a (# of dimensions,) vector can be passed in and
            treated as a single point.

        Returns
        -------
        (# of points,)-array
            The values at each point.

        Raises
        ------
        ValueError : if the dimensionality of the input points is different
                     than the dimensionality of the KDE.

        """
        points = np.atleast_2d(points)

        dim, num_m = np.array(points).shape
        if dim != self.dim:
            raise ValueError(f"points have dimension {dim}, dataset has "
                             f"dimension {self.dim}")

        result = np.zeros(num_m)

        if num_m >= self.num_dp:
            # there are more points than data, so loop over data
            for i in range(self.num_dp):
                diff = self.dataset[:, i, np.newaxis] - points
                tdiff = np.dot(self.inv_cov, diff)
                energy = np.sum(diff * tdiff, axis=0) / 2.0
                result = result + np.exp(-energy)
        else:
            # loop over points
            for i in range(num_m):
                diff = self.dataset - points[:, i, np.newaxis]
                tdiff = np.dot(self.inv_cov, diff)
                energy = np.sum(diff * tdiff, axis=0) / 2.0
                result[i] = np.sum(np.exp(-energy), axis=0)

        result = result / self.norm_factor

        return result

    __call__ = evaluate

# === NexusCore/openenv\Lib\site-packages\fontTools\voltLib\voltToFea.py ===
"""\
MS VOLT ``.vtp`` to AFDKO ``.fea`` OpenType Layout converter.

Usage
-----

To convert a VTP project file:


.. code-block:: sh

    $ fonttools voltLib.voltToFea input.vtp output.fea

It is also possible convert font files with `TSIV` table (as saved from Volt),
in this case the glyph names used in the Volt project will be mapped to the
actual glyph names in the font files when written to the feature file:

.. code-block:: sh

    $ fonttools voltLib.voltToFea input.ttf output.fea

The ``--quiet`` option can be used to suppress warnings.

The ``--traceback`` can be used to get Python traceback in case of exceptions,
instead of suppressing the traceback.


Limitations
-----------

* Not all VOLT features are supported, the script will error if it it
  encounters something it does not understand. Please report an issue if this
  happens.
* AFDKO feature file syntax for mark positioning is awkward and does not allow
  setting the mark coverage. It also defines mark anchors globally, as a result
  some mark positioning lookups might cover many marks than what was in the VOLT
  file. This should not be an issue in practice, but if it is then the only way
  is to modify the VOLT file or the generated feature file manually to use unique
  mark anchors for each lookup.
* VOLT allows subtable breaks in any lookup type, but AFDKO feature file
  implementations vary in their support; currently AFDKO’s makeOTF supports
  subtable breaks in pair positioning lookups only, while FontTools’ feaLib
  support it for most substitution lookups and only some positioning lookups.
"""

import logging
import re
from io import StringIO
from graphlib import TopologicalSorter

from fontTools.feaLib import ast
from fontTools.ttLib import TTFont, TTLibError
from fontTools.voltLib import ast as VAst
from fontTools.voltLib.parser import Parser as VoltParser

log = logging.getLogger("fontTools.voltLib.voltToFea")

TABLES = ["GDEF", "GSUB", "GPOS"]


def _flatten_group(group):
    ret = []
    if isinstance(group, (tuple, list)):
        for item in group:
            ret.extend(_flatten_group(item))
    elif hasattr(group, "enum"):
        ret.extend(_flatten_group(group.enum))
    else:
        ret.append(group)
    return ret


# Topologically sort of group definitions to ensure that all groups are defined
# before they are referenced. This is necessary because FEA requires it but
# VOLT does not, see below.
def sort_groups(groups):
    group_map = {group.name.lower(): group for group in groups}
    graph = {
        group.name.lower(): [
            x.group.lower()
            for x in _flatten_group(group)
            if isinstance(x, VAst.GroupName)
        ]
        for group in groups
    }
    sorter = TopologicalSorter(graph)
    return [group_map[name] for name in sorter.static_order()]


class Lookup(ast.LookupBlock):
    def __init__(self, name, use_extension=False, location=None):
        super().__init__(name, use_extension, location)
        self.chained = []


class VoltToFea:
    _NOT_LOOKUP_NAME_RE = re.compile(r"[^A-Za-z_0-9.]")
    _NOT_CLASS_NAME_RE = re.compile(r"[^A-Za-z_0-9.\-]")

    def __init__(self, file_or_path, font=None):
        if isinstance(file_or_path, VAst.VoltFile):
            self._doc, self._file_or_path = file_or_path, None
        else:
            self._doc, self._file_or_path = None, file_or_path
        self._font = font

        self._glyph_map = {}
        self._glyph_order = None

        self._gdef = {}
        self._glyphclasses = {}
        self._features = {}
        self._lookups = {}

        self._marks = set()
        self._ligatures = {}

        self._markclasses = {}
        self._anchors = {}

        self._settings = {}

        self._lookup_names = {}
        self._class_names = {}

    def _lookupName(self, name):
        if name not in self._lookup_names:
            res = self._NOT_LOOKUP_NAME_RE.sub("_", name)
            while res in self._lookup_names.values():
                res += "_"
            self._lookup_names[name] = res
        return self._lookup_names[name]

    def _className(self, name):
        if name not in self._class_names:
            res = self._NOT_CLASS_NAME_RE.sub("_", name)
            while res in self._class_names.values():
                res += "_"
            self._class_names[name] = res
        return self._class_names[name]

    def _collectStatements(self, doc, tables, ignore_unsupported_settings=False):
        # Collect glyph difinitions first, as we need them to map VOLT glyph names to font glyph name.
        for statement in doc.statements:
            if isinstance(statement, VAst.GlyphDefinition):
                self._glyphDefinition(statement)

        # Collect and sort group definitions first, to make sure a group
        # definition that references other groups comes after them since VOLT
        # does not enforce such ordering, and feature file require it.
        groups = [s for s in doc.statements if isinstance(s, VAst.GroupDefinition)]
        for group in sort_groups(groups):
            self._groupDefinition(group)

        for statement in doc.statements:
            if isinstance(statement, VAst.AnchorDefinition):
                if "GPOS" in tables:
                    self._anchorDefinition(statement)
            elif isinstance(statement, VAst.SettingDefinition):
                self._settingDefinition(statement, ignore_unsupported_settings)
            elif isinstance(statement, (VAst.GlyphDefinition, VAst.GroupDefinition)):
                pass  # Handled above
            elif isinstance(statement, VAst.ScriptDefinition):
                self._scriptDefinition(statement)
            elif not isinstance(statement, VAst.LookupDefinition):
                raise NotImplementedError(statement)

        # Lookup definitions need to be handled last as they reference glyph
        # and mark classes that might be defined after them.
        for statement in doc.statements:
            if isinstance(statement, VAst.LookupDefinition):
                if statement.pos and "GPOS" not in tables:
                    continue
                if statement.sub and "GSUB" not in tables:
                    continue
                self._lookupDefinition(statement)

    def _buildFeatureFile(self, tables):
        doc = ast.FeatureFile()
        statements = doc.statements

        if self._glyphclasses:
            statements.append(ast.Comment("# Glyph classes"))
            statements.extend(self._glyphclasses.values())

        if self._markclasses:
            statements.append(ast.Comment("\n# Mark classes"))
            statements.extend(c[1] for c in sorted(self._markclasses.items()))

        if self._lookups:
            statements.append(ast.Comment("\n# Lookups"))
            for lookup in self._lookups.values():
                statements.extend(lookup.chained)
                statements.append(lookup)

        # Prune features
        features = self._features.copy()
        for feature_tag in features:
            scripts = features[feature_tag]
            for script_tag in scripts:
                langs = scripts[script_tag]
                for language_tag in langs:
                    langs[language_tag] = [
                        l for l in langs[language_tag] if l.lower() in self._lookups
                    ]
                scripts[script_tag] = {t: l for t, l in langs.items() if l}
            features[feature_tag] = {t: s for t, s in scripts.items() if s}
        features = {t: f for t, f in features.items() if f}

        if features:
            statements.append(ast.Comment("# Features"))
            for feature_tag, scripts in features.items():
                feature = ast.FeatureBlock(feature_tag)
                script_tags = sorted(scripts, key=lambda k: 0 if k == "DFLT" else 1)
                if feature_tag == "aalt" and len(script_tags) > 1:
                    log.warning(
                        "FEA syntax does not allow script statements in 'aalt' feature, "
                        "so only lookups from the first script will be included."
                    )
                    script_tags = script_tags[:1]
                for script_tag in script_tags:
                    if feature_tag != "aalt":
                        feature.statements.append(ast.ScriptStatement(script_tag))
                    language_tags = sorted(
                        scripts[script_tag],
                        key=lambda k: 0 if k == "dflt" else 1,
                    )
                    if feature_tag == "aalt" and len(language_tags) > 1:
                        log.warning(
                            "FEA syntax does not allow language statements in 'aalt' feature, "
                            "so only lookups from the first language will be included."
                        )
                        language_tags = language_tags[:1]
                    for language_tag in language_tags:
                        if feature_tag != "aalt":
                            include_default = True if language_tag == "dflt" else False
                            feature.statements.append(
                                ast.LanguageStatement(
                                    language_tag.ljust(4),
                                    include_default=include_default,
                                )
                            )
                        for name in scripts[script_tag][language_tag]:
                            lookup = self._lookups[name.lower()]
                            lookupref = ast.LookupReferenceStatement(lookup)
                            feature.statements.append(lookupref)
                statements.append(feature)

        if self._gdef and "GDEF" in tables:
            classes = []
            for name in ("BASE", "MARK", "LIGATURE", "COMPONENT"):
                if name in self._gdef:
                    classname = "GDEF_" + name.lower()
                    glyphclass = ast.GlyphClassDefinition(classname, self._gdef[name])
                    statements.append(glyphclass)
                    classes.append(ast.GlyphClassName(glyphclass))
                else:
                    classes.append(None)

            gdef = ast.TableBlock("GDEF")
            gdef.statements.append(ast.GlyphClassDefStatement(*classes))
            statements.append(gdef)

        return doc

    def convert(self, tables=None, ignore_unsupported_settings=False):
        if self._doc is None:
            self._doc = VoltParser(self._file_or_path).parse()
        doc = self._doc

        if tables is None:
            tables = TABLES
        if self._font is not None:
            self._glyph_order = self._font.getGlyphOrder()

        self._collectStatements(doc, tables, ignore_unsupported_settings)
        fea = self._buildFeatureFile(tables)
        return fea.asFea()

    def _glyphName(self, glyph):
        try:
            name = glyph.glyph
        except AttributeError:
            name = glyph
        return ast.GlyphName(self._glyph_map.get(name, name))

    def _groupName(self, group):
        try:
            name = group.group
        except AttributeError:
            name = group
        return ast.GlyphClassName(self._glyphclasses[name.lower()])

    def _glyphSet(self, item):
        return [
            (self._glyphName(x) if isinstance(x, (str, VAst.GlyphName)) else x)
            for x in item.glyphSet()
        ]

    def _coverage(self, coverage, flatten=False):
        items = []
        for item in coverage:
            if isinstance(item, VAst.GlyphName):
                items.append(self._glyphName(item))
            elif isinstance(item, VAst.GroupName):
                items.append(self._groupName(item))
            elif isinstance(item, VAst.Enum):
                item = self._coverage(item.enum, flatten=True)
                if flatten:
                    items.extend(item)
                else:
                    items.append(ast.GlyphClass(item))
            elif isinstance(item, VAst.Range):
                item = self._glyphSet(item)
                if flatten:
                    items.extend(item)
                else:
                    items.append(ast.GlyphClass(item))
            else:
                raise NotImplementedError(item)
        return items

    def _context(self, context):
        out = []
        for item in context:
            coverage = self._coverage(item, flatten=True)
            if len(coverage) > 1:
                coverage = ast.GlyphClass(coverage)
            else:
                coverage = coverage[0]
            out.append(coverage)
        return out

    def _groupDefinition(self, group):
        name = self._className(group.name)
        glyphs = self._coverage(group.enum.enum, flatten=True)
        glyphclass = ast.GlyphClass(glyphs)
        classdef = ast.GlyphClassDefinition(name, glyphclass)
        self._glyphclasses[group.name.lower()] = classdef

    def _glyphDefinition(self, glyph):
        try:
            self._glyph_map[glyph.name] = self._glyph_order[glyph.id]
        except TypeError:
            pass

        if glyph.type in ("BASE", "MARK", "LIGATURE", "COMPONENT"):
            if glyph.type not in self._gdef:
                self._gdef[glyph.type] = ast.GlyphClass()
            self._gdef[glyph.type].glyphs.append(self._glyphName(glyph.name))

        if glyph.type == "MARK":
            self._marks.add(glyph.name)
        elif glyph.type == "LIGATURE":
            self._ligatures[glyph.name] = glyph.components

    def _scriptDefinition(self, script):
        stag = script.tag
        for lang in script.langs:
            ltag = lang.tag
            for feature in lang.features:
                lookups = {l.split("\\")[0]: True for l in feature.lookups}
                ftag = feature.tag
                if ftag not in self._features:
                    self._features[ftag] = {}
                if stag not in self._features[ftag]:
                    self._features[ftag][stag] = {}
                assert ltag not in self._features[ftag][stag]
                self._features[ftag][stag][ltag] = lookups.keys()

    def _settingDefinition(self, setting, ignore_unsupported=False):
        if setting.name.startswith("COMPILER_"):
            self._settings[setting.name] = setting.value
        elif not ignore_unsupported:
            log.warning(f"Unsupported setting ignored: {setting.name}")

    def _adjustment(self, adjustment):
        adv, dx, dy, adv_adjust_by, dx_adjust_by, dy_adjust_by = adjustment

        adv_device = adv_adjust_by and adv_adjust_by.items() or None
        dx_device = dx_adjust_by and dx_adjust_by.items() or None
        dy_device = dy_adjust_by and dy_adjust_by.items() or None

        return ast.ValueRecord(
            xPlacement=dx,
            yPlacement=dy,
            xAdvance=adv,
            xPlaDevice=dx_device,
            yPlaDevice=dy_device,
            xAdvDevice=adv_device,
        )

    def _anchor(self, adjustment):
        adv, dx, dy, adv_adjust_by, dx_adjust_by, dy_adjust_by = adjustment

        assert not adv_adjust_by
        dx_device = dx_adjust_by and dx_adjust_by.items() or None
        dy_device = dy_adjust_by and dy_adjust_by.items() or None

        return ast.Anchor(
            dx or 0,
            dy or 0,
            xDeviceTable=dx_device or None,
            yDeviceTable=dy_device or None,
        )

    def _anchorDefinition(self, anchordef):
        anchorname = anchordef.name
        glyphname = anchordef.glyph_name
        anchor = self._anchor(anchordef.pos)

        if glyphname not in self._anchors:
            self._anchors[glyphname] = {}
        if anchorname.startswith("MARK_"):
            anchorname = anchorname[:5] + anchorname[5:].lower()
        else:
            anchorname = anchorname.lower()
        if anchorname not in self._anchors[glyphname]:
            self._anchors[glyphname][anchorname] = {}
        self._anchors[glyphname][anchorname][anchordef.component] = anchor

    def _gposLookup(self, lookup, fealookup):
        statements = fealookup.statements

        pos = lookup.pos
        if isinstance(pos, VAst.PositionAdjustPairDefinition):
            for (idx1, idx2), (pos1, pos2) in pos.adjust_pair.items():
                coverage_1 = pos.coverages_1[idx1 - 1]
                coverage_2 = pos.coverages_2[idx2 - 1]

                # If not both are groups, use “enum pos” otherwise makeotf will
                # fail.
                enumerated = False
                for item in coverage_1 + coverage_2:
                    if not isinstance(item, VAst.GroupName):
                        enumerated = True

                glyphs1 = self._coverage(coverage_1)
                glyphs2 = self._coverage(coverage_2)
                record1 = self._adjustment(pos1)
                record2 = self._adjustment(pos2)
                assert len(glyphs1) == 1
                assert len(glyphs2) == 1
                statements.append(
                    ast.PairPosStatement(
                        glyphs1[0], record1, glyphs2[0], record2, enumerated=enumerated
                    )
                )
        elif isinstance(pos, VAst.PositionAdjustSingleDefinition):
            for a, b in pos.adjust_single:
                glyphs = self._coverage(a)
                record = self._adjustment(b)
                assert len(glyphs) == 1
                statements.append(
                    ast.SinglePosStatement([(glyphs[0], record)], [], [], False)
                )
        elif isinstance(pos, VAst.PositionAttachDefinition):
            anchors = {}
            allmarks = set()
            for coverage, anchorname in pos.coverage_to:
                # In feature files mark classes are global, but in VOLT they
                # are defined per-lookup. If we output mark class definitions
                # for all marks that use a given anchor, we might end up with a
                # mark used in two different classes in the same lookup, which
                # is causes feature file compilation error.
                # At the expense of uglier feature code, we make the mark class
                # name by appending the current lookup name not the anchor
                # name, and output mark class definitions only for marks used
                # in this lookup.
                classname = self._className(f"{anchorname}.{lookup.name}")
                markclass = ast.MarkClass(classname)

                # Anchor names are case-insensitive in VOLT
                anchorname = anchorname.lower()

                # We might still end in marks used in two different anchor
                # classes, so we filter out already used marks.
                marks = set()
                for mark in coverage:
                    marks.update(mark.glyphSet())
                if not marks.isdisjoint(allmarks):
                    marks.difference_update(allmarks)
                    if not marks:
                        continue
                allmarks.update(marks)

                for glyphname in marks:
                    glyph = self._glyphName(glyphname)
                    anchor = self._anchors[glyphname][f"MARK_{anchorname}"][1]
                    markdef = ast.MarkClassDefinition(markclass, anchor, glyph)
                    self._markclasses[(glyphname, classname)] = markdef

                for base in pos.coverage:
                    for name in base.glyphSet():
                        if name not in anchors:
                            anchors[name] = []
                        if (anchorname, classname) not in anchors[name]:
                            anchors[name].append((anchorname, classname))

            is_ligature = all(n in self._ligatures for n in anchors)
            is_mark = all(n in self._marks for n in anchors)
            for name in anchors:
                components = 1
                if is_ligature:
                    components = self._ligatures[name]

                marks = [[] for _ in range(components)]
                for mark, classname in anchors[name]:
                    markclass = ast.MarkClass(classname)
                    for component in range(1, components + 1):
                        if component in self._anchors[name][mark]:
                            anchor = self._anchors[name][mark][component]
                            marks[component - 1].append((anchor, markclass))

                base = self._glyphName(name)
                if is_mark:
                    mark = ast.MarkMarkPosStatement(base, marks[0])
                elif is_ligature:
                    mark = ast.MarkLigPosStatement(base, marks)
                else:
                    mark = ast.MarkBasePosStatement(base, marks[0])
                statements.append(mark)
        elif isinstance(pos, VAst.PositionAttachCursiveDefinition):
            # Collect enter and exit glyphs
            enter_coverage = []
            for coverage in pos.coverages_enter:
                for base in coverage:
                    for name in base.glyphSet():
                        enter_coverage.append(name)
            exit_coverage = []
            for coverage in pos.coverages_exit:
                for base in coverage:
                    for name in base.glyphSet():
                        exit_coverage.append(name)

            # Write enter anchors, also check if the glyph has exit anchor and
            # write it, too.
            for name in enter_coverage:
                glyph = self._glyphName(name)
                entry = self._anchors[name]["entry"][1]
                exit = None
                if name in exit_coverage:
                    exit = self._anchors[name]["exit"][1]
                    exit_coverage.pop(exit_coverage.index(name))
                statements.append(ast.CursivePosStatement(glyph, entry, exit))

            # Write any remaining exit anchors.
            for name in exit_coverage:
                glyph = self._glyphName(name)
                exit = self._anchors[name]["exit"][1]
                statements.append(ast.CursivePosStatement(glyph, None, exit))
        else:
            raise NotImplementedError(pos)

    def _gposContextLookup(self, lookup, prefix, suffix, ignore, fealookup, chained):
        statements = fealookup.statements

        pos = lookup.pos
        if isinstance(pos, VAst.PositionAdjustPairDefinition):
            for (idx1, idx2), (pos1, pos2) in pos.adjust_pair.items():
                glyphs1 = self._coverage(pos.coverages_1[idx1 - 1])
                glyphs2 = self._coverage(pos.coverages_2[idx2 - 1])
                assert len(glyphs1) == 1
                assert len(glyphs2) == 1
                glyphs = (glyphs1[0], glyphs2[0])

                if ignore:
                    statement = ast.IgnorePosStatement([(prefix, glyphs, suffix)])
                else:
                    statement = ast.ChainContextPosStatement(
                        prefix, glyphs, suffix, [chained, chained]
                    )
                statements.append(statement)
        elif isinstance(pos, VAst.PositionAdjustSingleDefinition):
            glyphs = [ast.GlyphClass()]
            for a, _ in pos.adjust_single:
                glyphs[0].extend(self._coverage(a, flatten=True))

            if ignore:
                statement = ast.IgnorePosStatement([(prefix, glyphs, suffix)])
            else:
                statement = ast.ChainContextPosStatement(
                    prefix, glyphs, suffix, [chained]
                )
            statements.append(statement)
        elif isinstance(pos, VAst.PositionAttachDefinition):
            glyphs = [ast.GlyphClass()]
            for coverage, _ in pos.coverage_to:
                glyphs[0].extend(self._coverage(coverage, flatten=True))

            if ignore:
                statement = ast.IgnorePosStatement([(prefix, glyphs, suffix)])
            else:
                statement = ast.ChainContextPosStatement(
                    prefix, glyphs, suffix, [chained]
                )
            statements.append(statement)
        else:
            raise NotImplementedError(pos)

    def _gsubLookup(self, lookup, fealookup):
        statements = fealookup.statements

        sub = lookup.sub

        # Alternate substitutions are represented by adding multiple
        # substitutions for the same glyph, so we need to collect them into one
        # to many mapping.
        if isinstance(sub, VAst.SubstitutionAlternateDefinition):
            alternates = {}
            for key, val in sub.mapping.items():
                if not key or not val:
                    path, line, column = sub.location
                    log.warning(f"{path}:{line}:{column}: Ignoring empty substitution")
                    continue
                glyphs = self._coverage(key)
                replacements = self._coverage(val)
                assert len(glyphs) == 1
                for src_glyph, repl_glyph in zip(
                    glyphs[0].glyphSet(), replacements[0].glyphSet()
                ):
                    alternates.setdefault(str(self._glyphName(src_glyph)), []).append(
                        str(self._glyphName(repl_glyph))
                    )

            for glyph, replacements in alternates.items():
                statement = ast.AlternateSubstStatement(
                    [], glyph, [], ast.GlyphClass(replacements)
                )
                statements.append(statement)
            return

        for key, val in sub.mapping.items():
            if not key or not val:
                path, line, column = sub.location
                log.warning(f"{path}:{line}:{column}: Ignoring empty substitution")
                continue
            glyphs = self._coverage(key)
            replacements = self._coverage(val)
            if isinstance(sub, VAst.SubstitutionSingleDefinition):
                assert len(glyphs) == 1
                assert len(replacements) == 1
                statements.append(
                    ast.SingleSubstStatement(glyphs, replacements, [], [], False)
                )
            elif isinstance(sub, VAst.SubstitutionReverseChainingSingleDefinition):
                # This is handled in gsubContextLookup()
                pass
            elif isinstance(sub, VAst.SubstitutionMultipleDefinition):
                assert len(glyphs) == 1
                statements.append(
                    ast.MultipleSubstStatement([], glyphs[0], [], replacements)
                )
            elif isinstance(sub, VAst.SubstitutionLigatureDefinition):
                assert len(replacements) == 1
                statement = ast.LigatureSubstStatement(
                    [], glyphs, [], replacements[0], False
                )

                # If any of the input glyphs is a group, we need to
                # explode the substitution into multiple ligature substitutions
                # since feature file syntax does not support classes in
                # ligature substitutions.
                n = max(len(x.glyphSet()) for x in glyphs)
                if n > 1:
                    # All input should either be groups of the same length or single glyphs
                    assert all(len(x.glyphSet()) in (n, 1) for x in glyphs)
                    glyphs = [x.glyphSet() for x in glyphs]
                    glyphs = [([x[0]] * n if len(x) == 1 else x) for x in glyphs]

                    # In this case ligature replacements must be a group of the same length
                    # as the input groups, or a single glyph. VOLT
                    # allows the replacement glyphs to be longer and truncates them.
                    # So well allow that and zip() below will do the truncation
                    # for us.
                    replacement = replacements[0].glyphSet()
                    if len(replacement) == 1:
                        replacement = [replacement[0]] * n
                    assert len(replacement) >= n

                    # Add the unexploded statement commented out for reference.
                    statements.append(ast.Comment(f"# {statement}"))

                    for zipped in zip(*glyphs, replacement):
                        zipped = [self._glyphName(x) for x in zipped]
                        statements.append(
                            ast.LigatureSubstStatement(
                                [], zipped[:-1], [], zipped[-1], False
                            )
                        )
                else:
                    statements.append(statement)
            else:
                raise NotImplementedError(sub)

    def _gsubContextLookup(self, lookup, prefix, suffix, ignore, fealookup, chained):
        statements = fealookup.statements

        sub = lookup.sub

        if isinstance(sub, VAst.SubstitutionReverseChainingSingleDefinition):
            # Reverse substitutions is a special case, it can’t use chained lookups.
            for key, val in sub.mapping.items():
                if not key or not val:
                    path, line, column = sub.location
                    log.warning(f"{path}:{line}:{column}: Ignoring empty substitution")
                    continue
                glyphs = self._coverage(key)
                replacements = self._coverage(val)
                statements.append(
                    ast.ReverseChainSingleSubstStatement(
                        prefix, suffix, glyphs, replacements
                    )
                )
            fealookup.chained = []
            return

        if not isinstance(
            sub,
            (
                VAst.SubstitutionSingleDefinition,
                VAst.SubstitutionMultipleDefinition,
                VAst.SubstitutionLigatureDefinition,
                VAst.SubstitutionAlternateDefinition,
            ),
        ):
            raise NotImplementedError(type(sub))

        glyphs = []
        for key, val in sub.mapping.items():
            if not key or not val:
                path, line, column = sub.location
                log.warning(f"{path}:{line}:{column}: Ignoring empty substitution")
                continue
            glyphs.extend(self._coverage(key, flatten=True))

        if len(glyphs) > 1:
            glyphs = [ast.GlyphClass(glyphs)]
        if ignore:
            statements.append(ast.IgnoreSubstStatement([(prefix, glyphs, suffix)]))
        else:
            statements.append(
                ast.ChainContextSubstStatement(prefix, glyphs, suffix, [chained])
            )

    def _lookupDefinition(self, lookup):
        mark_attachement = None
        mark_filtering = None

        flags = 0
        if lookup.direction == "RTL":
            flags |= 1
        if not lookup.process_base:
            flags |= 2
        # FIXME: Does VOLT support this?
        # if not lookup.process_ligatures:
        #     flags |= 4
        if not lookup.process_marks:
            flags |= 8
        elif isinstance(lookup.process_marks, str):
            mark_attachement = self._groupName(lookup.process_marks)
        elif lookup.mark_glyph_set is not None:
            mark_filtering = self._groupName(lookup.mark_glyph_set)

        lookupflags = None
        if flags or mark_attachement is not None or mark_filtering is not None:
            lookupflags = ast.LookupFlagStatement(
                flags, mark_attachement, mark_filtering
            )

        use_extension = False
        if self._settings.get("COMPILER_USEEXTENSIONLOOKUPS"):
            use_extension = True

        if "\\" in lookup.name:
            # Merge sub lookups as subtables (lookups named “base\sub”),
            # makeotf/feaLib will issue a warning and ignore the subtable
            # statement if it is not a pairpos lookup, though.
            name = lookup.name.split("\\")[0]
            if name.lower() not in self._lookups:
                fealookup = Lookup(
                    self._lookupName(name),
                    use_extension=use_extension,
                )
                if lookupflags is not None:
                    fealookup.statements.append(lookupflags)
                fealookup.statements.append(ast.Comment("# " + lookup.name))
            else:
                fealookup = self._lookups[name.lower()]
                fealookup.statements.append(ast.SubtableStatement())
                fealookup.statements.append(ast.Comment("# " + lookup.name))
            self._lookups[name.lower()] = fealookup
        else:
            fealookup = Lookup(
                self._lookupName(lookup.name),
                use_extension=use_extension,
            )
            if lookupflags is not None:
                fealookup.statements.append(lookupflags)
            self._lookups[lookup.name.lower()] = fealookup

        if lookup.comments is not None:
            fealookup.statements.append(ast.Comment("# " + lookup.comments))

        contexts = []
        for context in lookup.context:
            prefix = self._context(context.left)
            suffix = self._context(context.right)
            ignore = context.ex_or_in == "EXCEPT_CONTEXT"
            contexts.append([prefix, suffix, ignore])
            # It seems that VOLT will create contextual substitution using
            # only the input if there is no other contexts in this lookup.
            if ignore and len(lookup.context) == 1:
                contexts.append([[], [], False])

        if contexts:
            chained = ast.LookupBlock(
                self._lookupName(lookup.name + " chained"),
                use_extension=use_extension,
            )
            fealookup.chained.append(chained)
            if lookup.sub is not None:
                self._gsubLookup(lookup, chained)
            elif lookup.pos is not None:
                self._gposLookup(lookup, chained)
            for prefix, suffix, ignore in contexts:
                if lookup.sub is not None:
                    self._gsubContextLookup(
                        lookup, prefix, suffix, ignore, fealookup, chained
                    )
                elif lookup.pos is not None:
                    self._gposContextLookup(
                        lookup, prefix, suffix, ignore, fealookup, chained
                    )
        else:
            if lookup.sub is not None:
                self._gsubLookup(lookup, fealookup)
            elif lookup.pos is not None:
                self._gposLookup(lookup, fealookup)


def main(args=None):
    """Convert MS VOLT to AFDKO feature files."""

    import argparse
    from pathlib import Path

    from fontTools import configLogger

    parser = argparse.ArgumentParser(
        "fonttools voltLib.voltToFea", description=main.__doc__
    )
    parser.add_argument(
        "input", metavar="INPUT", type=Path, help="input font/VTP file to process"
    )
    parser.add_argument(
        "featurefile", metavar="OUTPUT", type=Path, help="output feature file"
    )
    parser.add_argument(
        "-t",
        "--table",
        action="append",
        choices=TABLES,
        dest="tables",
        help="List of tables to write, by default all tables are written",
    )
    parser.add_argument(
        "-q", "--quiet", action="store_true", help="Suppress non-error messages"
    )
    parser.add_argument(
        "--traceback", action="store_true", help="Don’t catch exceptions"
    )

    options = parser.parse_args(args)

    configLogger(level=("ERROR" if options.quiet else "INFO"))

    file_or_path = options.input
    font = None
    try:
        font = TTFont(file_or_path)
        if "TSIV" in font:
            file_or_path = StringIO(font["TSIV"].data.decode("utf-8"))
        else:
            log.error('"TSIV" table is missing, font was not saved from VOLT?')
            return 1
    except TTLibError:
        pass

    converter = VoltToFea(file_or_path, font)
    try:
        fea = converter.convert(options.tables)
    except NotImplementedError as e:
        if options.traceback:
            raise
        location = getattr(e.args[0], "location", None)
        message = f'"{e}" is not supported'
        if location:
            path, line, column = location
            log.error(f"{path}:{line}:{column}: {message}")
        else:
            log.error(message)
        return 1
    with open(options.featurefile, "w") as feafile:
        feafile.write(fea)


if __name__ == "__main__":
    import sys

    sys.exit(main())

# === NexusCore/openenv\Lib\site-packages\git\objects\commit.py ===
# Copyright (C) 2008, 2009 Michael Trier (mtrier@gmail.com) and contributors
#
# This module is part of GitPython and is released under the
# 3-Clause BSD License: https://opensource.org/license/bsd-3-clause/

__all__ = ["Commit"]

from collections import defaultdict
import datetime
from io import BytesIO
import logging
import os
import re
from subprocess import Popen, PIPE
import sys
from time import altzone, daylight, localtime, time, timezone
import warnings

from gitdb import IStream

from git.cmd import Git
from git.diff import Diffable
from git.util import Actor, Stats, finalize_process, hex_to_bin

from . import base
from .tree import Tree
from .util import (
    Serializable,
    TraversableIterableObj,
    altz_to_utctz_str,
    from_timestamp,
    parse_actor_and_date,
    parse_date,
)

# typing ------------------------------------------------------------------

from typing import (
    Any,
    Dict,
    IO,
    Iterator,
    List,
    Sequence,
    Tuple,
    TYPE_CHECKING,
    Union,
    cast,
)

if sys.version_info >= (3, 8):
    from typing import Literal
else:
    from typing_extensions import Literal

from git.types import PathLike

if TYPE_CHECKING:
    from git.refs import SymbolicReference
    from git.repo import Repo

# ------------------------------------------------------------------------

_logger = logging.getLogger(__name__)


class Commit(base.Object, TraversableIterableObj, Diffable, Serializable):
    """Wraps a git commit object.

    See :manpage:`gitglossary(7)` on "commit object":
    https://git-scm.com/docs/gitglossary#def_commit_object

    :note:
        This class will act lazily on some of its attributes and will query the value on
        demand only if it involves calling the git binary.
    """

    # ENVIRONMENT VARIABLES
    # Read when creating new commits.
    env_author_date = "GIT_AUTHOR_DATE"
    env_committer_date = "GIT_COMMITTER_DATE"

    # CONFIGURATION KEYS
    conf_encoding = "i18n.commitencoding"

    # INVARIANTS
    default_encoding = "UTF-8"

    type: Literal["commit"] = "commit"

    __slots__ = (
        "tree",
        "author",
        "authored_date",
        "author_tz_offset",
        "committer",
        "committed_date",
        "committer_tz_offset",
        "message",
        "parents",
        "encoding",
        "gpgsig",
    )

    _id_attribute_ = "hexsha"

    parents: Sequence["Commit"]

    def __init__(
        self,
        repo: "Repo",
        binsha: bytes,
        tree: Union[Tree, None] = None,
        author: Union[Actor, None] = None,
        authored_date: Union[int, None] = None,
        author_tz_offset: Union[None, float] = None,
        committer: Union[Actor, None] = None,
        committed_date: Union[int, None] = None,
        committer_tz_offset: Union[None, float] = None,
        message: Union[str, bytes, None] = None,
        parents: Union[Sequence["Commit"], None] = None,
        encoding: Union[str, None] = None,
        gpgsig: Union[str, None] = None,
    ) -> None:
        """Instantiate a new :class:`Commit`. All keyword arguments taking ``None`` as
        default will be implicitly set on first query.

        :param binsha:
            20 byte sha1.

        :param tree:
            A :class:`~git.objects.tree.Tree` object.

        :param author:
            The author :class:`~git.util.Actor` object.

        :param authored_date: int_seconds_since_epoch
            The authored DateTime - use :func:`time.gmtime` to convert it into a
            different format.

        :param author_tz_offset: int_seconds_west_of_utc
            The timezone that the `authored_date` is in.

        :param committer:
            The committer string, as an :class:`~git.util.Actor` object.

        :param committed_date: int_seconds_since_epoch
            The committed DateTime - use :func:`time.gmtime` to convert it into a
            different format.

        :param committer_tz_offset: int_seconds_west_of_utc
            The timezone that the `committed_date` is in.

        :param message: string
            The commit message.

        :param encoding: string
            Encoding of the message, defaults to UTF-8.

        :param parents:
            List or tuple of :class:`Commit` objects which are our parent(s) in the
            commit dependency graph.

        :return:
            :class:`Commit`

        :note:
            Timezone information is in the same format and in the same sign as what
            :func:`time.altzone` returns. The sign is inverted compared to git's UTC
            timezone.
        """
        super().__init__(repo, binsha)
        self.binsha = binsha
        if tree is not None:
            assert isinstance(tree, Tree), "Tree needs to be a Tree instance, was %s" % type(tree)
        if tree is not None:
            self.tree = tree
        if author is not None:
            self.author = author
        if authored_date is not None:
            self.authored_date = authored_date
        if author_tz_offset is not None:
            self.author_tz_offset = author_tz_offset
        if committer is not None:
            self.committer = committer
        if committed_date is not None:
            self.committed_date = committed_date
        if committer_tz_offset is not None:
            self.committer_tz_offset = committer_tz_offset
        if message is not None:
            self.message = message
        if parents is not None:
            self.parents = parents
        if encoding is not None:
            self.encoding = encoding
        if gpgsig is not None:
            self.gpgsig = gpgsig

    @classmethod
    def _get_intermediate_items(cls, commit: "Commit") -> Tuple["Commit", ...]:
        return tuple(commit.parents)

    @classmethod
    def _calculate_sha_(cls, repo: "Repo", commit: "Commit") -> bytes:
        """Calculate the sha of a commit.

        :param repo:
            :class:`~git.repo.base.Repo` object the commit should be part of.

        :param commit:
            :class:`Commit` object for which to generate the sha.
        """

        stream = BytesIO()
        commit._serialize(stream)
        streamlen = stream.tell()
        stream.seek(0)

        istream = repo.odb.store(IStream(cls.type, streamlen, stream))
        return istream.binsha

    def replace(self, **kwargs: Any) -> "Commit":
        """Create new commit object from an existing commit object.

        Any values provided as keyword arguments will replace the corresponding
        attribute in the new object.
        """

        attrs = {k: getattr(self, k) for k in self.__slots__}

        for attrname in kwargs:
            if attrname not in self.__slots__:
                raise ValueError("invalid attribute name")

        attrs.update(kwargs)
        new_commit = self.__class__(self.repo, self.NULL_BIN_SHA, **attrs)
        new_commit.binsha = self._calculate_sha_(self.repo, new_commit)

        return new_commit

    def _set_cache_(self, attr: str) -> None:
        if attr in Commit.__slots__:
            # Read the data in a chunk, its faster - then provide a file wrapper.
            _binsha, _typename, self.size, stream = self.repo.odb.stream(self.binsha)
            self._deserialize(BytesIO(stream.read()))
        else:
            super()._set_cache_(attr)
        # END handle attrs

    @property
    def authored_datetime(self) -> datetime.datetime:
        return from_timestamp(self.authored_date, self.author_tz_offset)

    @property
    def committed_datetime(self) -> datetime.datetime:
        return from_timestamp(self.committed_date, self.committer_tz_offset)

    @property
    def summary(self) -> Union[str, bytes]:
        """:return: First line of the commit message"""
        if isinstance(self.message, str):
            return self.message.split("\n", 1)[0]
        else:
            return self.message.split(b"\n", 1)[0]

    def count(self, paths: Union[PathLike, Sequence[PathLike]] = "", **kwargs: Any) -> int:
        """Count the number of commits reachable from this commit.

        :param paths:
            An optional path or a list of paths restricting the return value to commits
            actually containing the paths.

        :param kwargs:
            Additional options to be passed to :manpage:`git-rev-list(1)`. They must not
            alter the output style of the command, or parsing will yield incorrect
            results.

        :return:
            An int defining the number of reachable commits
        """
        # Yes, it makes a difference whether empty paths are given or not in our case as
        # the empty paths version will ignore merge commits for some reason.
        if paths:
            return len(self.repo.git.rev_list(self.hexsha, "--", paths, **kwargs).splitlines())
        return len(self.repo.git.rev_list(self.hexsha, **kwargs).splitlines())

    @property
    def name_rev(self) -> str:
        """
        :return:
            String describing the commits hex sha based on the closest
            `~git.refs.reference.Reference`.

        :note:
            Mostly useful for UI purposes.
        """
        return self.repo.git.name_rev(self)

    @classmethod
    def iter_items(
        cls,
        repo: "Repo",
        rev: Union[str, "Commit", "SymbolicReference"],
        paths: Union[PathLike, Sequence[PathLike]] = "",
        **kwargs: Any,
    ) -> Iterator["Commit"]:
        R"""Find all commits matching the given criteria.

        :param repo:
            The :class:`~git.repo.base.Repo`.

        :param rev:
            Revision specifier. See :manpage:`git-rev-parse(1)` for viable options.

        :param paths:
            An optional path or list of paths. If set only :class:`Commit`\s that
            include the path or paths will be considered.

        :param kwargs:
            Optional keyword arguments to :manpage:`git-rev-list(1)` where:

            * ``max_count`` is the maximum number of commits to fetch.
            * ``skip`` is the number of commits to skip.
            * ``since`` selects all commits since some date, e.g. ``"1970-01-01"``.

        :return:
            Iterator yielding :class:`Commit` items.
        """
        if "pretty" in kwargs:
            raise ValueError("--pretty cannot be used as parsing expects single sha's only")
        # END handle pretty

        # Use -- in all cases, to prevent possibility of ambiguous arguments.
        # See https://github.com/gitpython-developers/GitPython/issues/264.

        args_list: List[PathLike] = ["--"]

        if paths:
            paths_tup: Tuple[PathLike, ...]
            if isinstance(paths, (str, os.PathLike)):
                paths_tup = (paths,)
            else:
                paths_tup = tuple(paths)

            args_list.extend(paths_tup)
        # END if paths

        proc = repo.git.rev_list(rev, args_list, as_process=True, **kwargs)
        return cls._iter_from_process_or_stream(repo, proc)

    def iter_parents(self, paths: Union[PathLike, Sequence[PathLike]] = "", **kwargs: Any) -> Iterator["Commit"]:
        R"""Iterate _all_ parents of this commit.

        :param paths:
            Optional path or list of paths limiting the :class:`Commit`\s to those that
            contain at least one of the paths.

        :param kwargs:
            All arguments allowed by :manpage:`git-rev-list(1)`.

        :return:
            Iterator yielding :class:`Commit` objects which are parents of ``self``
        """
        # skip ourselves
        skip = kwargs.get("skip", 1)
        if skip == 0:  # skip ourselves
            skip = 1
        kwargs["skip"] = skip

        return self.iter_items(self.repo, self, paths, **kwargs)

    @property
    def stats(self) -> Stats:
        """Create a git stat from changes between this commit and its first parent
        or from all changes done if this is the very first commit.

        :return:
            :class:`Stats`
        """

        def process_lines(lines: List[str]) -> str:
            text = ""
            for file_info, line in zip(lines, lines[len(lines) // 2 :]):
                change_type = file_info.split("\t")[0][-1]
                (insertions, deletions, filename) = line.split("\t")
                text += "%s\t%s\t%s\t%s\n" % (change_type, insertions, deletions, filename)
            return text

        if not self.parents:
            lines = self.repo.git.diff_tree(
                self.hexsha, "--", numstat=True, no_renames=True, root=True, raw=True
            ).splitlines()[1:]
            text = process_lines(lines)
        else:
            lines = self.repo.git.diff(
                self.parents[0].hexsha, self.hexsha, "--", numstat=True, no_renames=True, raw=True
            ).splitlines()
            text = process_lines(lines)
        return Stats._list_from_string(self.repo, text)

    @property
    def trailers(self) -> Dict[str, str]:
        """Deprecated. Get the trailers of the message as a dictionary.

        :note:
            This property is deprecated, please use either :attr:`trailers_list` or
            :attr:`trailers_dict`.

        :return:
            Dictionary containing whitespace stripped trailer information.
            Only contains the latest instance of each trailer key.
        """
        warnings.warn(
            "Commit.trailers is deprecated, use Commit.trailers_list or Commit.trailers_dict instead",
            DeprecationWarning,
            stacklevel=2,
        )
        return {k: v[0] for k, v in self.trailers_dict.items()}

    @property
    def trailers_list(self) -> List[Tuple[str, str]]:
        """Get the trailers of the message as a list.

        Git messages can contain trailer information that are similar to :rfc:`822`
        e-mail headers. See :manpage:`git-interpret-trailers(1)`.

        This function calls ``git interpret-trailers --parse`` onto the message to
        extract the trailer information, returns the raw trailer data as a list.

        Valid message with trailer::

            Subject line

            some body information

            another information

            key1: value1.1
            key1: value1.2
            key2 :    value 2 with inner spaces

        Returned list will look like this::

            [
                ("key1", "value1.1"),
                ("key1", "value1.2"),
                ("key2", "value 2 with inner spaces"),
            ]

        :return:
            List containing key-value tuples of whitespace stripped trailer information.
        """
        cmd = ["git", "interpret-trailers", "--parse"]
        proc: Git.AutoInterrupt = self.repo.git.execute(  # type: ignore[call-overload]
            cmd,
            as_process=True,
            istream=PIPE,
        )
        trailer: str = proc.communicate(str(self.message).encode())[0].decode("utf8")
        trailer = trailer.strip()

        if not trailer:
            return []

        trailer_list = []
        for t in trailer.split("\n"):
            key, val = t.split(":", 1)
            trailer_list.append((key.strip(), val.strip()))

        return trailer_list

    @property
    def trailers_dict(self) -> Dict[str, List[str]]:
        """Get the trailers of the message as a dictionary.

        Git messages can contain trailer information that are similar to :rfc:`822`
        e-mail headers. See :manpage:`git-interpret-trailers(1)`.

        This function calls ``git interpret-trailers --parse`` onto the message to
        extract the trailer information. The key value pairs are stripped of leading and
        trailing whitespaces before they get saved into a dictionary.

        Valid message with trailer::

            Subject line

            some body information

            another information

            key1: value1.1
            key1: value1.2
            key2 :    value 2 with inner spaces

        Returned dictionary will look like this::

            {
                "key1": ["value1.1", "value1.2"],
                "key2": ["value 2 with inner spaces"],
            }


        :return:
            Dictionary containing whitespace stripped trailer information, mapping
            trailer keys to a list of their corresponding values.
        """
        d = defaultdict(list)
        for key, val in self.trailers_list:
            d[key].append(val)
        return dict(d)

    @classmethod
    def _iter_from_process_or_stream(cls, repo: "Repo", proc_or_stream: Union[Popen, IO]) -> Iterator["Commit"]:
        """Parse out commit information into a list of :class:`Commit` objects.

        We expect one line per commit, and parse the actual commit information directly
        from our lighting fast object database.

        :param proc:
            :manpage:`git-rev-list(1)` process instance - one sha per line.

        :return:
            Iterator supplying :class:`Commit` objects
        """

        # def is_proc(inp) -> TypeGuard[Popen]:
        #     return hasattr(proc_or_stream, 'wait') and not hasattr(proc_or_stream, 'readline')

        # def is_stream(inp) -> TypeGuard[IO]:
        #     return hasattr(proc_or_stream, 'readline')

        if hasattr(proc_or_stream, "wait"):
            proc_or_stream = cast(Popen, proc_or_stream)
            if proc_or_stream.stdout is not None:
                stream = proc_or_stream.stdout
        elif hasattr(proc_or_stream, "readline"):
            proc_or_stream = cast(IO, proc_or_stream)  # type: ignore[redundant-cast]
            stream = proc_or_stream

        readline = stream.readline
        while True:
            line = readline()
            if not line:
                break
            hexsha = line.strip()
            if len(hexsha) > 40:
                # Split additional information, as returned by bisect for instance.
                hexsha, _ = line.split(None, 1)
            # END handle extra info

            assert len(hexsha) == 40, "Invalid line: %s" % hexsha
            yield cls(repo, hex_to_bin(hexsha))
        # END for each line in stream

        # TODO: Review this - it seems process handling got a bit out of control due to
        # many developers trying to fix the open file handles issue.
        if hasattr(proc_or_stream, "wait"):
            proc_or_stream = cast(Popen, proc_or_stream)
            finalize_process(proc_or_stream)

    @classmethod
    def create_from_tree(
        cls,
        repo: "Repo",
        tree: Union[Tree, str],
        message: str,
        parent_commits: Union[None, List["Commit"]] = None,
        head: bool = False,
        author: Union[None, Actor] = None,
        committer: Union[None, Actor] = None,
        author_date: Union[None, str, datetime.datetime] = None,
        commit_date: Union[None, str, datetime.datetime] = None,
    ) -> "Commit":
        """Commit the given tree, creating a :class:`Commit` object.

        :param repo:
            :class:`~git.repo.base.Repo` object the commit should be part of.

        :param tree:
            :class:`~git.objects.tree.Tree` object or hex or bin sha.
            The tree of the new commit.

        :param message:
            Commit message. It may be an empty string if no message is provided. It will
            be converted to a string, in any case.

        :param parent_commits:
            Optional :class:`Commit` objects to use as parents for the new commit. If
            empty list, the commit will have no parents at all and become a root commit.
            If ``None``, the current head commit will be the parent of the new commit
            object.

        :param head:
            If ``True``, the HEAD will be advanced to the new commit automatically.
            Otherwise the HEAD will remain pointing on the previous commit. This could
            lead to undesired results when diffing files.

        :param author:
            The name of the author, optional.
            If unset, the repository configuration is used to obtain this value.

        :param committer:
            The name of the committer, optional.
            If unset, the repository configuration is used to obtain this value.

        :param author_date:
            The timestamp for the author field.

        :param commit_date:
            The timestamp for the committer field.

        :return:
            :class:`Commit` object representing the new commit.

        :note:
            Additional information about the committer and author are taken from the
            environment or from the git configuration. See :manpage:`git-commit-tree(1)`
            for more information.
        """
        if parent_commits is None:
            try:
                parent_commits = [repo.head.commit]
            except ValueError:
                # Empty repositories have no head commit.
                parent_commits = []
            # END handle parent commits
        else:
            for p in parent_commits:
                if not isinstance(p, cls):
                    raise ValueError(f"Parent commit '{p!r}' must be of type {cls}")
            # END check parent commit types
        # END if parent commits are unset

        # Retrieve all additional information, create a commit object, and serialize it.
        # Generally:
        # * Environment variables override configuration values.
        # * Sensible defaults are set according to the git documentation.

        # COMMITTER AND AUTHOR INFO
        cr = repo.config_reader()
        env = os.environ

        committer = committer or Actor.committer(cr)
        author = author or Actor.author(cr)

        # PARSE THE DATES
        unix_time = int(time())
        is_dst = daylight and localtime().tm_isdst > 0
        offset = altzone if is_dst else timezone

        author_date_str = env.get(cls.env_author_date, "")
        if author_date:
            author_time, author_offset = parse_date(author_date)
        elif author_date_str:
            author_time, author_offset = parse_date(author_date_str)
        else:
            author_time, author_offset = unix_time, offset
        # END set author time

        committer_date_str = env.get(cls.env_committer_date, "")
        if commit_date:
            committer_time, committer_offset = parse_date(commit_date)
        elif committer_date_str:
            committer_time, committer_offset = parse_date(committer_date_str)
        else:
            committer_time, committer_offset = unix_time, offset
        # END set committer time

        # Assume UTF-8 encoding.
        enc_section, enc_option = cls.conf_encoding.split(".")
        conf_encoding = cr.get_value(enc_section, enc_option, cls.default_encoding)
        if not isinstance(conf_encoding, str):
            raise TypeError("conf_encoding could not be coerced to str")

        # If the tree is no object, make sure we create one - otherwise the created
        # commit object is invalid.
        if isinstance(tree, str):
            tree = repo.tree(tree)
        # END tree conversion

        # CREATE NEW COMMIT
        new_commit = cls(
            repo,
            cls.NULL_BIN_SHA,
            tree,
            author,
            author_time,
            author_offset,
            committer,
            committer_time,
            committer_offset,
            message,
            parent_commits,
            conf_encoding,
        )

        new_commit.binsha = cls._calculate_sha_(repo, new_commit)

        if head:
            # Need late import here, importing git at the very beginning throws as
            # well...
            import git.refs

            try:
                repo.head.set_commit(new_commit, logmsg=message)
            except ValueError:
                # head is not yet set to the ref our HEAD points to.
                # Happens on first commit.
                master = git.refs.Head.create(
                    repo,
                    repo.head.ref,
                    new_commit,
                    logmsg="commit (initial): %s" % message,
                )
                repo.head.set_reference(master, logmsg="commit: Switching to %s" % master)
            # END handle empty repositories
        # END advance head handling

        return new_commit

    # { Serializable Implementation

    def _serialize(self, stream: BytesIO) -> "Commit":
        write = stream.write
        write(("tree %s\n" % self.tree).encode("ascii"))
        for p in self.parents:
            write(("parent %s\n" % p).encode("ascii"))

        a = self.author
        aname = a.name
        c = self.committer
        fmt = "%s %s <%s> %s %s\n"
        write(
            (
                fmt
                % (
                    "author",
                    aname,
                    a.email,
                    self.authored_date,
                    altz_to_utctz_str(self.author_tz_offset),
                )
            ).encode(self.encoding)
        )

        # Encode committer.
        aname = c.name
        write(
            (
                fmt
                % (
                    "committer",
                    aname,
                    c.email,
                    self.committed_date,
                    altz_to_utctz_str(self.committer_tz_offset),
                )
            ).encode(self.encoding)
        )

        if self.encoding != self.default_encoding:
            write(("encoding %s\n" % self.encoding).encode("ascii"))

        try:
            if self.__getattribute__("gpgsig"):
                write(b"gpgsig")
                for sigline in self.gpgsig.rstrip("\n").split("\n"):
                    write((" " + sigline + "\n").encode("ascii"))
        except AttributeError:
            pass

        write(b"\n")

        # Write plain bytes, be sure its encoded according to our encoding.
        if isinstance(self.message, str):
            write(self.message.encode(self.encoding))
        else:
            write(self.message)
        # END handle encoding
        return self

    def _deserialize(self, stream: BytesIO) -> "Commit":
        readline = stream.readline
        self.tree = Tree(self.repo, hex_to_bin(readline().split()[1]), Tree.tree_id << 12, "")

        self.parents = []
        next_line = None
        while True:
            parent_line = readline()
            if not parent_line.startswith(b"parent"):
                next_line = parent_line
                break
            # END abort reading parents
            self.parents.append(type(self)(self.repo, hex_to_bin(parent_line.split()[-1].decode("ascii"))))
        # END for each parent line
        self.parents = tuple(self.parents)

        # We don't know actual author encoding before we have parsed it, so keep the
        # lines around.
        author_line = next_line
        committer_line = readline()

        # We might run into one or more mergetag blocks, skip those for now.
        next_line = readline()
        while next_line.startswith(b"mergetag "):
            next_line = readline()
            while next_line.startswith(b" "):
                next_line = readline()
        # END skip mergetags

        # Now we can have the encoding line, or an empty line followed by the optional
        # message.
        self.encoding = self.default_encoding
        self.gpgsig = ""

        # Read headers.
        enc = next_line
        buf = enc.strip()
        while buf:
            if buf[0:10] == b"encoding ":
                self.encoding = buf[buf.find(b" ") + 1 :].decode(self.encoding, "ignore")
            elif buf[0:7] == b"gpgsig ":
                sig = buf[buf.find(b" ") + 1 :] + b"\n"
                is_next_header = False
                while True:
                    sigbuf = readline()
                    if not sigbuf:
                        break
                    if sigbuf[0:1] != b" ":
                        buf = sigbuf.strip()
                        is_next_header = True
                        break
                    sig += sigbuf[1:]
                # END read all signature
                self.gpgsig = sig.rstrip(b"\n").decode(self.encoding, "ignore")
                if is_next_header:
                    continue
            buf = readline().strip()

        # Decode the author's name.
        try:
            (
                self.author,
                self.authored_date,
                self.author_tz_offset,
            ) = parse_actor_and_date(author_line.decode(self.encoding, "replace"))
        except UnicodeDecodeError:
            _logger.error(
                "Failed to decode author line '%s' using encoding %s",
                author_line,
                self.encoding,
                exc_info=True,
            )

        try:
            (
                self.committer,
                self.committed_date,
                self.committer_tz_offset,
            ) = parse_actor_and_date(committer_line.decode(self.encoding, "replace"))
        except UnicodeDecodeError:
            _logger.error(
                "Failed to decode committer line '%s' using encoding %s",
                committer_line,
                self.encoding,
                exc_info=True,
            )
        # END handle author's encoding

        # A stream from our data simply gives us the plain message.
        # The end of our message stream is marked with a newline that we strip.
        self.message = stream.read()
        try:
            self.message = self.message.decode(self.encoding, "replace")
        except UnicodeDecodeError:
            _logger.error(
                "Failed to decode message '%s' using encoding %s",
                self.message,
                self.encoding,
                exc_info=True,
            )
        # END exception handling

        return self

    # } END serializable implementation

    @property
    def co_authors(self) -> List[Actor]:
        """Search the commit message for any co-authors of this commit.

        Details on co-authors:
        https://github.blog/2018-01-29-commit-together-with-co-authors/

        :return:
            List of co-authors for this commit (as :class:`~git.util.Actor` objects).
        """
        co_authors = []

        if self.message:
            results = re.findall(
                r"^Co-authored-by: (.*) <(.*?)>$",
                self.message,
                re.MULTILINE,
            )
            for author in results:
                co_authors.append(Actor(*author))

        return co_authors

# === NexusCore/openenv\Lib\site-packages\matplotlib\markers.py ===
r"""
Functions to handle markers; used by the marker functionality of
`~matplotlib.axes.Axes.plot`, `~matplotlib.axes.Axes.scatter`, and
`~matplotlib.axes.Axes.errorbar`.

All possible markers are defined here:

============================== ====== =========================================
marker                         symbol description
============================== ====== =========================================
``"."``                        |m00|  point
``","``                        |m01|  pixel
``"o"``                        |m02|  circle
``"v"``                        |m03|  triangle_down
``"^"``                        |m04|  triangle_up
``"<"``                        |m05|  triangle_left
``">"``                        |m06|  triangle_right
``"1"``                        |m07|  tri_down
``"2"``                        |m08|  tri_up
``"3"``                        |m09|  tri_left
``"4"``                        |m10|  tri_right
``"8"``                        |m11|  octagon
``"s"``                        |m12|  square
``"p"``                        |m13|  pentagon
``"P"``                        |m23|  plus (filled)
``"*"``                        |m14|  star
``"h"``                        |m15|  hexagon1
``"H"``                        |m16|  hexagon2
``"+"``                        |m17|  plus
``"x"``                        |m18|  x
``"X"``                        |m24|  x (filled)
``"D"``                        |m19|  diamond
``"d"``                        |m20|  thin_diamond
``"|"``                        |m21|  vline
``"_"``                        |m22|  hline
``0`` (``TICKLEFT``)           |m25|  tickleft
``1`` (``TICKRIGHT``)          |m26|  tickright
``2`` (``TICKUP``)             |m27|  tickup
``3`` (``TICKDOWN``)           |m28|  tickdown
``4`` (``CARETLEFT``)          |m29|  caretleft
``5`` (``CARETRIGHT``)         |m30|  caretright
``6`` (``CARETUP``)            |m31|  caretup
``7`` (``CARETDOWN``)          |m32|  caretdown
``8`` (``CARETLEFTBASE``)      |m33|  caretleft (centered at base)
``9`` (``CARETRIGHTBASE``)     |m34|  caretright (centered at base)
``10`` (``CARETUPBASE``)       |m35|  caretup (centered at base)
``11`` (``CARETDOWNBASE``)     |m36|  caretdown (centered at base)
``"none"`` or ``"None"``              nothing
``" "`` or  ``""``                    nothing
``"$...$"``                    |m37|  Render the string using mathtext.
                                      E.g ``"$f$"`` for marker showing the
                                      letter ``f``.
``verts``                             A list of (x, y) pairs used for Path
                                      vertices. The center of the marker is
                                      located at (0, 0) and the size is
                                      normalized, such that the created path
                                      is encapsulated inside the unit cell.
``path``                              A `~matplotlib.path.Path` instance.
``(numsides, 0, angle)``              A regular polygon with ``numsides``
                                      sides, rotated by ``angle``.
``(numsides, 1, angle)``              A star-like symbol with ``numsides``
                                      sides, rotated by ``angle``.
``(numsides, 2, angle)``              An asterisk with ``numsides`` sides,
                                      rotated by ``angle``.
============================== ====== =========================================

Note that special symbols can be defined via the
:ref:`STIX math font <mathtext>`,
e.g. ``"$\u266B$"``. For an overview over the STIX font symbols refer to the
`STIX font table <http://www.stixfonts.org/allGlyphs.html>`_.
Also see the :doc:`/gallery/text_labels_and_annotations/stix_fonts_demo`.

Integer numbers from ``0`` to ``11`` create lines and triangles. Those are
equally accessible via capitalized variables, like ``CARETDOWNBASE``.
Hence the following are equivalent::

    plt.plot([1, 2, 3], marker=11)
    plt.plot([1, 2, 3], marker=matplotlib.markers.CARETDOWNBASE)

Markers join and cap styles can be customized by creating a new instance of
MarkerStyle.
A MarkerStyle can also have a custom `~matplotlib.transforms.Transform`
allowing it to be arbitrarily rotated or offset.

Examples showing the use of markers:

* :doc:`/gallery/lines_bars_and_markers/marker_reference`
* :doc:`/gallery/lines_bars_and_markers/scatter_star_poly`
* :doc:`/gallery/lines_bars_and_markers/multivariate_marker_plot`

.. |m00| image:: /_static/markers/m00.png
.. |m01| image:: /_static/markers/m01.png
.. |m02| image:: /_static/markers/m02.png
.. |m03| image:: /_static/markers/m03.png
.. |m04| image:: /_static/markers/m04.png
.. |m05| image:: /_static/markers/m05.png
.. |m06| image:: /_static/markers/m06.png
.. |m07| image:: /_static/markers/m07.png
.. |m08| image:: /_static/markers/m08.png
.. |m09| image:: /_static/markers/m09.png
.. |m10| image:: /_static/markers/m10.png
.. |m11| image:: /_static/markers/m11.png
.. |m12| image:: /_static/markers/m12.png
.. |m13| image:: /_static/markers/m13.png
.. |m14| image:: /_static/markers/m14.png
.. |m15| image:: /_static/markers/m15.png
.. |m16| image:: /_static/markers/m16.png
.. |m17| image:: /_static/markers/m17.png
.. |m18| image:: /_static/markers/m18.png
.. |m19| image:: /_static/markers/m19.png
.. |m20| image:: /_static/markers/m20.png
.. |m21| image:: /_static/markers/m21.png
.. |m22| image:: /_static/markers/m22.png
.. |m23| image:: /_static/markers/m23.png
.. |m24| image:: /_static/markers/m24.png
.. |m25| image:: /_static/markers/m25.png
.. |m26| image:: /_static/markers/m26.png
.. |m27| image:: /_static/markers/m27.png
.. |m28| image:: /_static/markers/m28.png
.. |m29| image:: /_static/markers/m29.png
.. |m30| image:: /_static/markers/m30.png
.. |m31| image:: /_static/markers/m31.png
.. |m32| image:: /_static/markers/m32.png
.. |m33| image:: /_static/markers/m33.png
.. |m34| image:: /_static/markers/m34.png
.. |m35| image:: /_static/markers/m35.png
.. |m36| image:: /_static/markers/m36.png
.. |m37| image:: /_static/markers/m37.png
"""
import copy

from collections.abc import Sized

import numpy as np

import matplotlib as mpl
from . import _api, cbook
from .path import Path
from .transforms import IdentityTransform, Affine2D
from ._enums import JoinStyle, CapStyle

# special-purpose marker identifiers:
(TICKLEFT, TICKRIGHT, TICKUP, TICKDOWN,
 CARETLEFT, CARETRIGHT, CARETUP, CARETDOWN,
 CARETLEFTBASE, CARETRIGHTBASE, CARETUPBASE, CARETDOWNBASE) = range(12)

_empty_path = Path(np.empty((0, 2)))


class MarkerStyle:
    """
    A class representing marker types.

    Instances are immutable. If you need to change anything, create a new
    instance.

    Attributes
    ----------
    markers : dict
        All known markers.
    filled_markers : tuple
        All known filled markers. This is a subset of *markers*.
    fillstyles : tuple
        The supported fillstyles.
    """

    markers = {
        '.': 'point',
        ',': 'pixel',
        'o': 'circle',
        'v': 'triangle_down',
        '^': 'triangle_up',
        '<': 'triangle_left',
        '>': 'triangle_right',
        '1': 'tri_down',
        '2': 'tri_up',
        '3': 'tri_left',
        '4': 'tri_right',
        '8': 'octagon',
        's': 'square',
        'p': 'pentagon',
        '*': 'star',
        'h': 'hexagon1',
        'H': 'hexagon2',
        '+': 'plus',
        'x': 'x',
        'D': 'diamond',
        'd': 'thin_diamond',
        '|': 'vline',
        '_': 'hline',
        'P': 'plus_filled',
        'X': 'x_filled',
        TICKLEFT: 'tickleft',
        TICKRIGHT: 'tickright',
        TICKUP: 'tickup',
        TICKDOWN: 'tickdown',
        CARETLEFT: 'caretleft',
        CARETRIGHT: 'caretright',
        CARETUP: 'caretup',
        CARETDOWN: 'caretdown',
        CARETLEFTBASE: 'caretleftbase',
        CARETRIGHTBASE: 'caretrightbase',
        CARETUPBASE: 'caretupbase',
        CARETDOWNBASE: 'caretdownbase',
        "None": 'nothing',
        "none": 'nothing',
        ' ': 'nothing',
        '': 'nothing'
    }

    # Just used for informational purposes.  is_filled()
    # is calculated in the _set_* functions.
    filled_markers = (
        '.', 'o', 'v', '^', '<', '>', '8', 's', 'p', '*', 'h', 'H', 'D', 'd',
        'P', 'X')

    fillstyles = ('full', 'left', 'right', 'bottom', 'top', 'none')
    _half_fillstyles = ('left', 'right', 'bottom', 'top')

    def __init__(self, marker,
                 fillstyle=None, transform=None, capstyle=None, joinstyle=None):
        """
        Parameters
        ----------
        marker : str, array-like, Path, MarkerStyle
            - Another instance of `MarkerStyle` copies the details of that *marker*.
            - For other possible marker values, see the module docstring
              `matplotlib.markers`.

        fillstyle : str, default: :rc:`markers.fillstyle`
            One of 'full', 'left', 'right', 'bottom', 'top', 'none'.

        transform : `~matplotlib.transforms.Transform`, optional
            Transform that will be combined with the native transform of the
            marker.

        capstyle : `.CapStyle` or %(CapStyle)s, optional
            Cap style that will override the default cap style of the marker.

        joinstyle : `.JoinStyle` or %(JoinStyle)s, optional
            Join style that will override the default join style of the marker.
        """
        self._marker_function = None
        self._user_transform = transform
        self._user_capstyle = CapStyle(capstyle) if capstyle is not None else None
        self._user_joinstyle = JoinStyle(joinstyle) if joinstyle is not None else None
        self._set_fillstyle(fillstyle)
        self._set_marker(marker)

    def _recache(self):
        if self._marker_function is None:
            return
        self._path = _empty_path
        self._transform = IdentityTransform()
        self._alt_path = None
        self._alt_transform = None
        self._snap_threshold = None
        self._joinstyle = JoinStyle.round
        self._capstyle = self._user_capstyle or CapStyle.butt
        # Initial guess: Assume the marker is filled unless the fillstyle is
        # set to 'none'. The marker function will override this for unfilled
        # markers.
        self._filled = self._fillstyle != 'none'
        self._marker_function()

    def __bool__(self):
        return bool(len(self._path.vertices))

    def is_filled(self):
        return self._filled

    def get_fillstyle(self):
        return self._fillstyle

    def _set_fillstyle(self, fillstyle):
        """
        Set the fillstyle.

        Parameters
        ----------
        fillstyle : {'full', 'left', 'right', 'bottom', 'top', 'none'}
            The part of the marker surface that is colored with
            markerfacecolor.
        """
        if fillstyle is None:
            fillstyle = mpl.rcParams['markers.fillstyle']
        _api.check_in_list(self.fillstyles, fillstyle=fillstyle)
        self._fillstyle = fillstyle

    def get_joinstyle(self):
        return self._joinstyle.name

    def get_capstyle(self):
        return self._capstyle.name

    def get_marker(self):
        return self._marker

    def _set_marker(self, marker):
        """
        Set the marker.

        Parameters
        ----------
        marker : str, array-like, Path, MarkerStyle
            - Another instance of `MarkerStyle` copies the details of that *marker*.
            - For other possible marker values see the module docstring
              `matplotlib.markers`.
        """
        if isinstance(marker, str) and cbook.is_math_text(marker):
            self._marker_function = self._set_mathtext_path
        elif isinstance(marker, (int, str)) and marker in self.markers:
            self._marker_function = getattr(self, '_set_' + self.markers[marker])
        elif (isinstance(marker, np.ndarray) and marker.ndim == 2 and
                marker.shape[1] == 2):
            self._marker_function = self._set_vertices
        elif isinstance(marker, Path):
            self._marker_function = self._set_path_marker
        elif (isinstance(marker, Sized) and len(marker) in (2, 3) and
                marker[1] in (0, 1, 2)):
            self._marker_function = self._set_tuple_marker
        elif isinstance(marker, MarkerStyle):
            self.__dict__ = copy.deepcopy(marker.__dict__)
        else:
            try:
                Path(marker)
                self._marker_function = self._set_vertices
            except ValueError as err:
                raise ValueError(
                    f'Unrecognized marker style {marker!r}') from err

        if not isinstance(marker, MarkerStyle):
            self._marker = marker
            self._recache()

    def get_path(self):
        """
        Return a `.Path` for the primary part of the marker.

        For unfilled markers this is the whole marker, for filled markers,
        this is the area to be drawn with *markerfacecolor*.
        """
        return self._path

    def get_transform(self):
        """
        Return the transform to be applied to the `.Path` from
        `MarkerStyle.get_path()`.
        """
        if self._user_transform is None:
            return self._transform.frozen()
        else:
            return (self._transform + self._user_transform).frozen()

    def get_alt_path(self):
        """
        Return a `.Path` for the alternate part of the marker.

        For unfilled markers, this is *None*; for filled markers, this is the
        area to be drawn with *markerfacecoloralt*.
        """
        return self._alt_path

    def get_alt_transform(self):
        """
        Return the transform to be applied to the `.Path` from
        `MarkerStyle.get_alt_path()`.
        """
        if self._user_transform is None:
            return self._alt_transform.frozen()
        else:
            return (self._alt_transform + self._user_transform).frozen()

    def get_snap_threshold(self):
        return self._snap_threshold

    def get_user_transform(self):
        """Return user supplied part of marker transform."""
        if self._user_transform is not None:
            return self._user_transform.frozen()

    def transformed(self, transform):
        """
        Return a new version of this marker with the transform applied.

        Parameters
        ----------
        transform : `~matplotlib.transforms.Affine2D`
            Transform will be combined with current user supplied transform.
        """
        new_marker = MarkerStyle(self)
        if new_marker._user_transform is not None:
            new_marker._user_transform += transform
        else:
            new_marker._user_transform = transform
        return new_marker

    def rotated(self, *, deg=None, rad=None):
        """
        Return a new version of this marker rotated by specified angle.

        Parameters
        ----------
        deg : float, optional
            Rotation angle in degrees.

        rad : float, optional
            Rotation angle in radians.

        .. note:: You must specify exactly one of deg or rad.
        """
        if deg is None and rad is None:
            raise ValueError('One of deg or rad is required')
        if deg is not None and rad is not None:
            raise ValueError('Only one of deg and rad can be supplied')
        new_marker = MarkerStyle(self)
        if new_marker._user_transform is None:
            new_marker._user_transform = Affine2D()

        if deg is not None:
            new_marker._user_transform.rotate_deg(deg)
        if rad is not None:
            new_marker._user_transform.rotate(rad)

        return new_marker

    def scaled(self, sx, sy=None):
        """
        Return new marker scaled by specified scale factors.

        If *sy* is not given, the same scale is applied in both the *x*- and
        *y*-directions.

        Parameters
        ----------
        sx : float
            *X*-direction scaling factor.
        sy : float, optional
            *Y*-direction scaling factor.
        """
        if sy is None:
            sy = sx

        new_marker = MarkerStyle(self)
        _transform = new_marker._user_transform or Affine2D()
        new_marker._user_transform = _transform.scale(sx, sy)
        return new_marker

    def _set_nothing(self):
        self._filled = False

    def _set_custom_marker(self, path):
        rescale = np.max(np.abs(path.vertices))  # max of x's and y's.
        self._transform = Affine2D().scale(0.5 / rescale)
        self._path = path

    def _set_path_marker(self):
        self._set_custom_marker(self._marker)

    def _set_vertices(self):
        self._set_custom_marker(Path(self._marker))

    def _set_tuple_marker(self):
        marker = self._marker
        if len(marker) == 2:
            numsides, rotation = marker[0], 0.0
        elif len(marker) == 3:
            numsides, rotation = marker[0], marker[2]
        symstyle = marker[1]
        if symstyle == 0:
            self._path = Path.unit_regular_polygon(numsides)
            self._joinstyle = self._user_joinstyle or JoinStyle.miter
        elif symstyle == 1:
            self._path = Path.unit_regular_star(numsides)
            self._joinstyle = self._user_joinstyle or JoinStyle.bevel
        elif symstyle == 2:
            self._path = Path.unit_regular_asterisk(numsides)
            self._filled = False
            self._joinstyle = self._user_joinstyle or JoinStyle.bevel
        else:
            raise ValueError(f"Unexpected tuple marker: {marker}")
        self._transform = Affine2D().scale(0.5).rotate_deg(rotation)

    def _set_mathtext_path(self):
        """
        Draw mathtext markers '$...$' using `.TextPath` object.

        Submitted by tcb
        """
        from matplotlib.text import TextPath

        # again, the properties could be initialised just once outside
        # this function
        text = TextPath(xy=(0, 0), s=self.get_marker(),
                        usetex=mpl.rcParams['text.usetex'])
        if len(text.vertices) == 0:
            return

        bbox = text.get_extents()
        max_dim = max(bbox.width, bbox.height)
        self._transform = (
            Affine2D()
            .translate(-bbox.xmin + 0.5 * -bbox.width, -bbox.ymin + 0.5 * -bbox.height)
            .scale(1.0 / max_dim))
        self._path = text
        self._snap = False

    def _half_fill(self):
        return self.get_fillstyle() in self._half_fillstyles

    def _set_circle(self, size=1.0):
        self._transform = Affine2D().scale(0.5 * size)
        self._snap_threshold = np.inf
        if not self._half_fill():
            self._path = Path.unit_circle()
        else:
            self._path = self._alt_path = Path.unit_circle_righthalf()
            fs = self.get_fillstyle()
            self._transform.rotate_deg(
                {'right': 0, 'top': 90, 'left': 180, 'bottom': 270}[fs])
            self._alt_transform = self._transform.frozen().rotate_deg(180.)

    def _set_point(self):
        self._set_circle(size=0.5)

    def _set_pixel(self):
        self._path = Path.unit_rectangle()
        # Ideally, you'd want -0.5, -0.5 here, but then the snapping
        # algorithm in the Agg backend will round this to a 2x2
        # rectangle from (-1, -1) to (1, 1).  By offsetting it
        # slightly, we can force it to be (0, 0) to (1, 1), which both
        # makes it only be a single pixel and places it correctly
        # aligned to 1-width stroking (i.e. the ticks).  This hack is
        # the best of a number of bad alternatives, mainly because the
        # backends are not aware of what marker is actually being used
        # beyond just its path data.
        self._transform = Affine2D().translate(-0.49999, -0.49999)
        self._snap_threshold = None

    _triangle_path = Path._create_closed([[0, 1], [-1, -1], [1, -1]])
    # Going down halfway looks to small.  Golden ratio is too far.
    _triangle_path_u = Path._create_closed([[0, 1], [-3/5, -1/5], [3/5, -1/5]])
    _triangle_path_d = Path._create_closed(
        [[-3/5, -1/5], [3/5, -1/5], [1, -1], [-1, -1]])
    _triangle_path_l = Path._create_closed([[0, 1], [0, -1], [-1, -1]])
    _triangle_path_r = Path._create_closed([[0, 1], [0, -1], [1, -1]])

    def _set_triangle(self, rot, skip):
        self._transform = Affine2D().scale(0.5).rotate_deg(rot)
        self._snap_threshold = 5.0

        if not self._half_fill():
            self._path = self._triangle_path
        else:
            mpaths = [self._triangle_path_u,
                      self._triangle_path_l,
                      self._triangle_path_d,
                      self._triangle_path_r]

            fs = self.get_fillstyle()
            if fs == 'top':
                self._path = mpaths[(0 + skip) % 4]
                self._alt_path = mpaths[(2 + skip) % 4]
            elif fs == 'bottom':
                self._path = mpaths[(2 + skip) % 4]
                self._alt_path = mpaths[(0 + skip) % 4]
            elif fs == 'left':
                self._path = mpaths[(1 + skip) % 4]
                self._alt_path = mpaths[(3 + skip) % 4]
            else:
                self._path = mpaths[(3 + skip) % 4]
                self._alt_path = mpaths[(1 + skip) % 4]

            self._alt_transform = self._transform

        self._joinstyle = self._user_joinstyle or JoinStyle.miter

    def _set_triangle_up(self):
        return self._set_triangle(0.0, 0)

    def _set_triangle_down(self):
        return self._set_triangle(180.0, 2)

    def _set_triangle_left(self):
        return self._set_triangle(90.0, 3)

    def _set_triangle_right(self):
        return self._set_triangle(270.0, 1)

    def _set_square(self):
        self._transform = Affine2D().translate(-0.5, -0.5)
        self._snap_threshold = 2.0
        if not self._half_fill():
            self._path = Path.unit_rectangle()
        else:
            # Build a bottom filled square out of two rectangles, one filled.
            self._path = Path([[0.0, 0.0], [1.0, 0.0], [1.0, 0.5],
                               [0.0, 0.5], [0.0, 0.0]])
            self._alt_path = Path([[0.0, 0.5], [1.0, 0.5], [1.0, 1.0],
                                   [0.0, 1.0], [0.0, 0.5]])
            fs = self.get_fillstyle()
            rotate = {'bottom': 0, 'right': 90, 'top': 180, 'left': 270}[fs]
            self._transform.rotate_deg(rotate)
            self._alt_transform = self._transform

        self._joinstyle = self._user_joinstyle or JoinStyle.miter

    def _set_diamond(self):
        self._transform = Affine2D().translate(-0.5, -0.5).rotate_deg(45)
        self._snap_threshold = 5.0
        if not self._half_fill():
            self._path = Path.unit_rectangle()
        else:
            self._path = Path([[0, 0], [1, 0], [1, 1], [0, 0]])
            self._alt_path = Path([[0, 0], [0, 1], [1, 1], [0, 0]])
            fs = self.get_fillstyle()
            rotate = {'right': 0, 'top': 90, 'left': 180, 'bottom': 270}[fs]
            self._transform.rotate_deg(rotate)
            self._alt_transform = self._transform
        self._joinstyle = self._user_joinstyle or JoinStyle.miter

    def _set_thin_diamond(self):
        self._set_diamond()
        self._transform.scale(0.6, 1.0)

    def _set_pentagon(self):
        self._transform = Affine2D().scale(0.5)
        self._snap_threshold = 5.0

        polypath = Path.unit_regular_polygon(5)

        if not self._half_fill():
            self._path = polypath
        else:
            verts = polypath.vertices
            y = (1 + np.sqrt(5)) / 4.
            top = Path(verts[[0, 1, 4, 0]])
            bottom = Path(verts[[1, 2, 3, 4, 1]])
            left = Path([verts[0], verts[1], verts[2], [0, -y], verts[0]])
            right = Path([verts[0], verts[4], verts[3], [0, -y], verts[0]])
            self._path, self._alt_path = {
                'top': (top, bottom), 'bottom': (bottom, top),
                'left': (left, right), 'right': (right, left),
            }[self.get_fillstyle()]
            self._alt_transform = self._transform

        self._joinstyle = self._user_joinstyle or JoinStyle.miter

    def _set_star(self):
        self._transform = Affine2D().scale(0.5)
        self._snap_threshold = 5.0

        polypath = Path.unit_regular_star(5, innerCircle=0.381966)

        if not self._half_fill():
            self._path = polypath
        else:
            verts = polypath.vertices
            top = Path(np.concatenate([verts[0:4], verts[7:10], verts[0:1]]))
            bottom = Path(np.concatenate([verts[3:8], verts[3:4]]))
            left = Path(np.concatenate([verts[0:6], verts[0:1]]))
            right = Path(np.concatenate([verts[0:1], verts[5:10], verts[0:1]]))
            self._path, self._alt_path = {
                'top': (top, bottom), 'bottom': (bottom, top),
                'left': (left, right), 'right': (right, left),
            }[self.get_fillstyle()]
            self._alt_transform = self._transform

        self._joinstyle = self._user_joinstyle or JoinStyle.bevel

    def _set_hexagon1(self):
        self._transform = Affine2D().scale(0.5)
        self._snap_threshold = None

        polypath = Path.unit_regular_polygon(6)

        if not self._half_fill():
            self._path = polypath
        else:
            verts = polypath.vertices
            # not drawing inside lines
            x = np.abs(np.cos(5 * np.pi / 6.))
            top = Path(np.concatenate([[(-x, 0)], verts[[1, 0, 5]], [(x, 0)]]))
            bottom = Path(np.concatenate([[(-x, 0)], verts[2:5], [(x, 0)]]))
            left = Path(verts[0:4])
            right = Path(verts[[0, 5, 4, 3]])
            self._path, self._alt_path = {
                'top': (top, bottom), 'bottom': (bottom, top),
                'left': (left, right), 'right': (right, left),
            }[self.get_fillstyle()]
            self._alt_transform = self._transform

        self._joinstyle = self._user_joinstyle or JoinStyle.miter

    def _set_hexagon2(self):
        self._transform = Affine2D().scale(0.5).rotate_deg(30)
        self._snap_threshold = None

        polypath = Path.unit_regular_polygon(6)

        if not self._half_fill():
            self._path = polypath
        else:
            verts = polypath.vertices
            # not drawing inside lines
            x, y = np.sqrt(3) / 4, 3 / 4.
            top = Path(verts[[1, 0, 5, 4, 1]])
            bottom = Path(verts[1:5])
            left = Path(np.concatenate([
                [(x, y)], verts[:3], [(-x, -y), (x, y)]]))
            right = Path(np.concatenate([
                [(x, y)], verts[5:2:-1], [(-x, -y)]]))
            self._path, self._alt_path = {
                'top': (top, bottom), 'bottom': (bottom, top),
                'left': (left, right), 'right': (right, left),
            }[self.get_fillstyle()]
            self._alt_transform = self._transform

        self._joinstyle = self._user_joinstyle or JoinStyle.miter

    def _set_octagon(self):
        self._transform = Affine2D().scale(0.5)
        self._snap_threshold = 5.0

        polypath = Path.unit_regular_polygon(8)

        if not self._half_fill():
            self._transform.rotate_deg(22.5)
            self._path = polypath
        else:
            x = np.sqrt(2.) / 4.
            self._path = self._alt_path = Path(
                [[0, -1], [0, 1], [-x, 1], [-1, x],
                 [-1, -x], [-x, -1], [0, -1]])
            fs = self.get_fillstyle()
            self._transform.rotate_deg(
                {'left': 0, 'bottom': 90, 'right': 180, 'top': 270}[fs])
            self._alt_transform = self._transform.frozen().rotate_deg(180.0)

        self._joinstyle = self._user_joinstyle or JoinStyle.miter

    _line_marker_path = Path([[0.0, -1.0], [0.0, 1.0]])

    def _set_vline(self):
        self._transform = Affine2D().scale(0.5)
        self._snap_threshold = 1.0
        self._filled = False
        self._path = self._line_marker_path

    def _set_hline(self):
        self._set_vline()
        self._transform = self._transform.rotate_deg(90)

    _tickhoriz_path = Path([[0.0, 0.0], [1.0, 0.0]])

    def _set_tickleft(self):
        self._transform = Affine2D().scale(-1.0, 1.0)
        self._snap_threshold = 1.0
        self._filled = False
        self._path = self._tickhoriz_path

    def _set_tickright(self):
        self._transform = Affine2D().scale(1.0, 1.0)
        self._snap_threshold = 1.0
        self._filled = False
        self._path = self._tickhoriz_path

    _tickvert_path = Path([[-0.0, 0.0], [-0.0, 1.0]])

    def _set_tickup(self):
        self._transform = Affine2D().scale(1.0, 1.0)
        self._snap_threshold = 1.0
        self._filled = False
        self._path = self._tickvert_path

    def _set_tickdown(self):
        self._transform = Affine2D().scale(1.0, -1.0)
        self._snap_threshold = 1.0
        self._filled = False
        self._path = self._tickvert_path

    _tri_path = Path([[0.0, 0.0], [0.0, -1.0],
                      [0.0, 0.0], [0.8, 0.5],
                      [0.0, 0.0], [-0.8, 0.5]],
                     [Path.MOVETO, Path.LINETO,
                      Path.MOVETO, Path.LINETO,
                      Path.MOVETO, Path.LINETO])

    def _set_tri_down(self):
        self._transform = Affine2D().scale(0.5)
        self._snap_threshold = 5.0
        self._filled = False
        self._path = self._tri_path

    def _set_tri_up(self):
        self._set_tri_down()
        self._transform = self._transform.rotate_deg(180)

    def _set_tri_left(self):
        self._set_tri_down()
        self._transform = self._transform.rotate_deg(270)

    def _set_tri_right(self):
        self._set_tri_down()
        self._transform = self._transform.rotate_deg(90)

    _caret_path = Path([[-1.0, 1.5], [0.0, 0.0], [1.0, 1.5]])

    def _set_caretdown(self):
        self._transform = Affine2D().scale(0.5)
        self._snap_threshold = 3.0
        self._filled = False
        self._path = self._caret_path
        self._joinstyle = self._user_joinstyle or JoinStyle.miter

    def _set_caretup(self):
        self._set_caretdown()
        self._transform = self._transform.rotate_deg(180)

    def _set_caretleft(self):
        self._set_caretdown()
        self._transform = self._transform.rotate_deg(270)

    def _set_caretright(self):
        self._set_caretdown()
        self._transform = self._transform.rotate_deg(90)

    _caret_path_base = Path([[-1.0, 0.0], [0.0, -1.5], [1.0, 0]])

    def _set_caretdownbase(self):
        self._set_caretdown()
        self._path = self._caret_path_base

    def _set_caretupbase(self):
        self._set_caretdownbase()
        self._transform = self._transform.rotate_deg(180)

    def _set_caretleftbase(self):
        self._set_caretdownbase()
        self._transform = self._transform.rotate_deg(270)

    def _set_caretrightbase(self):
        self._set_caretdownbase()
        self._transform = self._transform.rotate_deg(90)

    _plus_path = Path([[-1.0, 0.0], [1.0, 0.0],
                       [0.0, -1.0], [0.0, 1.0]],
                      [Path.MOVETO, Path.LINETO,
                       Path.MOVETO, Path.LINETO])

    def _set_plus(self):
        self._transform = Affine2D().scale(0.5)
        self._snap_threshold = 1.0
        self._filled = False
        self._path = self._plus_path

    _x_path = Path([[-1.0, -1.0], [1.0, 1.0],
                    [-1.0, 1.0], [1.0, -1.0]],
                   [Path.MOVETO, Path.LINETO,
                    Path.MOVETO, Path.LINETO])

    def _set_x(self):
        self._transform = Affine2D().scale(0.5)
        self._snap_threshold = 3.0
        self._filled = False
        self._path = self._x_path

    _plus_filled_path = Path._create_closed(np.array([
        (-1, -3), (+1, -3), (+1, -1), (+3, -1), (+3, +1), (+1, +1),
        (+1, +3), (-1, +3), (-1, +1), (-3, +1), (-3, -1), (-1, -1)]) / 6)
    _plus_filled_path_t = Path._create_closed(np.array([
        (+3, 0), (+3, +1), (+1, +1), (+1, +3),
        (-1, +3), (-1, +1), (-3, +1), (-3, 0)]) / 6)

    def _set_plus_filled(self):
        self._transform = Affine2D()
        self._snap_threshold = 5.0
        self._joinstyle = self._user_joinstyle or JoinStyle.miter
        if not self._half_fill():
            self._path = self._plus_filled_path
        else:
            # Rotate top half path to support all partitions
            self._path = self._alt_path = self._plus_filled_path_t
            fs = self.get_fillstyle()
            self._transform.rotate_deg(
                {'top': 0, 'left': 90, 'bottom': 180, 'right': 270}[fs])
            self._alt_transform = self._transform.frozen().rotate_deg(180)

    _x_filled_path = Path._create_closed(np.array([
        (-1, -2), (0, -1), (+1, -2), (+2, -1), (+1, 0), (+2, +1),
        (+1, +2), (0, +1), (-1, +2), (-2, +1), (-1, 0), (-2, -1)]) / 4)
    _x_filled_path_t = Path._create_closed(np.array([
        (+1, 0), (+2, +1), (+1, +2), (0, +1),
        (-1, +2), (-2, +1), (-1, 0)]) / 4)

    def _set_x_filled(self):
        self._transform = Affine2D()
        self._snap_threshold = 5.0
        self._joinstyle = self._user_joinstyle or JoinStyle.miter
        if not self._half_fill():
            self._path = self._x_filled_path
        else:
            # Rotate top half path to support all partitions
            self._path = self._alt_path = self._x_filled_path_t
            fs = self.get_fillstyle()
            self._transform.rotate_deg(
                {'top': 0, 'left': 90, 'bottom': 180, 'right': 270}[fs])
            self._alt_transform = self._transform.frozen().rotate_deg(180)

# === NexusCore/openenv\Lib\site-packages\IPython\core\guarded_eval.py ===
from copy import copy
from inspect import isclass, signature, Signature
from typing import (
    Annotated,
    AnyStr,
    Callable,
    Literal,
    NamedTuple,
    NewType,
    Optional,
    Protocol,
    Sequence,
    TypeGuard,
    Union,
    get_args,
    get_origin,
    is_typeddict,
)
import ast
import builtins
import collections
import operator
import sys
from functools import cached_property
from dataclasses import dataclass, field
from types import MethodDescriptorType, ModuleType

from IPython.utils.decorators import undoc


from typing import Self, LiteralString

if sys.version_info < (3, 12):
    from typing_extensions import TypeAliasType
else:
    from typing import TypeAliasType


@undoc
class HasGetItem(Protocol):
    def __getitem__(self, key) -> None: ...


@undoc
class InstancesHaveGetItem(Protocol):
    def __call__(self, *args, **kwargs) -> HasGetItem: ...


@undoc
class HasGetAttr(Protocol):
    def __getattr__(self, key) -> None: ...


@undoc
class DoesNotHaveGetAttr(Protocol):
    pass


# By default `__getattr__` is not explicitly implemented on most objects
MayHaveGetattr = Union[HasGetAttr, DoesNotHaveGetAttr]


def _unbind_method(func: Callable) -> Union[Callable, None]:
    """Get unbound method for given bound method.

    Returns None if cannot get unbound method, or method is already unbound.
    """
    owner = getattr(func, "__self__", None)
    owner_class = type(owner)
    name = getattr(func, "__name__", None)
    instance_dict_overrides = getattr(owner, "__dict__", None)
    if (
        owner is not None
        and name
        and (
            not instance_dict_overrides
            or (instance_dict_overrides and name not in instance_dict_overrides)
        )
    ):
        return getattr(owner_class, name)
    return None


@undoc
@dataclass
class EvaluationPolicy:
    """Definition of evaluation policy."""

    allow_locals_access: bool = False
    allow_globals_access: bool = False
    allow_item_access: bool = False
    allow_attr_access: bool = False
    allow_builtins_access: bool = False
    allow_all_operations: bool = False
    allow_any_calls: bool = False
    allow_auto_import: bool = False
    allowed_calls: set[Callable] = field(default_factory=set)

    def can_get_item(self, value, item):
        return self.allow_item_access

    def can_get_attr(self, value, attr):
        return self.allow_attr_access

    def can_operate(self, dunders: tuple[str, ...], a, b=None):
        if self.allow_all_operations:
            return True

    def can_call(self, func):
        if self.allow_any_calls:
            return True

        if func in self.allowed_calls:
            return True

        owner_method = _unbind_method(func)

        if owner_method and owner_method in self.allowed_calls:
            return True


def _get_external(module_name: str, access_path: Sequence[str]):
    """Get value from external module given a dotted access path.

    Raises:
    * `KeyError` if module is removed not found, and
    * `AttributeError` if access path does not match an exported object
    """
    member_type = sys.modules[module_name]
    for attr in access_path:
        member_type = getattr(member_type, attr)
    return member_type


def _has_original_dunder_external(
    value,
    module_name: str,
    access_path: Sequence[str],
    method_name: str,
):
    if module_name not in sys.modules:
        # LBYLB as it is faster
        return False
    try:
        member_type = _get_external(module_name, access_path)
        value_type = type(value)
        if type(value) == member_type:
            return True
        if method_name == "__getattribute__":
            # we have to short-circuit here due to an unresolved issue in
            # `isinstance` implementation: https://bugs.python.org/issue32683
            return False
        if isinstance(value, member_type):
            method = getattr(value_type, method_name, None)
            member_method = getattr(member_type, method_name, None)
            if member_method == method:
                return True
    except (AttributeError, KeyError):
        return False


def _has_original_dunder(
    value, allowed_types, allowed_methods, allowed_external, method_name
):
    # note: Python ignores `__getattr__`/`__getitem__` on instances,
    # we only need to check at class level
    value_type = type(value)

    # strict type check passes → no need to check method
    if value_type in allowed_types:
        return True

    method = getattr(value_type, method_name, None)

    if method is None:
        return None

    if method in allowed_methods:
        return True

    for module_name, *access_path in allowed_external:
        if _has_original_dunder_external(value, module_name, access_path, method_name):
            return True

    return False


@undoc
@dataclass
class SelectivePolicy(EvaluationPolicy):
    allowed_getitem: set[InstancesHaveGetItem] = field(default_factory=set)
    allowed_getitem_external: set[tuple[str, ...]] = field(default_factory=set)

    allowed_getattr: set[MayHaveGetattr] = field(default_factory=set)
    allowed_getattr_external: set[tuple[str, ...]] = field(default_factory=set)

    allowed_operations: set = field(default_factory=set)
    allowed_operations_external: set[tuple[str, ...]] = field(default_factory=set)

    _operation_methods_cache: dict[str, set[Callable]] = field(
        default_factory=dict, init=False
    )

    def can_get_attr(self, value, attr):
        has_original_attribute = _has_original_dunder(
            value,
            allowed_types=self.allowed_getattr,
            allowed_methods=self._getattribute_methods,
            allowed_external=self.allowed_getattr_external,
            method_name="__getattribute__",
        )
        has_original_attr = _has_original_dunder(
            value,
            allowed_types=self.allowed_getattr,
            allowed_methods=self._getattr_methods,
            allowed_external=self.allowed_getattr_external,
            method_name="__getattr__",
        )

        accept = False

        # Many objects do not have `__getattr__`, this is fine.
        if has_original_attr is None and has_original_attribute:
            accept = True
        else:
            # Accept objects without modifications to `__getattr__` and `__getattribute__`
            accept = has_original_attr and has_original_attribute

        if accept:
            # We still need to check for overridden properties.

            value_class = type(value)
            if not hasattr(value_class, attr):
                return True

            class_attr_val = getattr(value_class, attr)
            is_property = isinstance(class_attr_val, property)

            if not is_property:
                return True

            # Properties in allowed types are ok (although we do not include any
            # properties in our default allow list currently).
            if type(value) in self.allowed_getattr:
                return True  # pragma: no cover

            # Properties in subclasses of allowed types may be ok if not changed
            for module_name, *access_path in self.allowed_getattr_external:
                try:
                    external_class = _get_external(module_name, access_path)
                    external_class_attr_val = getattr(external_class, attr)
                except (KeyError, AttributeError):
                    return False  # pragma: no cover
                return class_attr_val == external_class_attr_val

        return False

    def can_get_item(self, value, item):
        """Allow accessing `__getiitem__` of allow-listed instances unless it was not modified."""
        return _has_original_dunder(
            value,
            allowed_types=self.allowed_getitem,
            allowed_methods=self._getitem_methods,
            allowed_external=self.allowed_getitem_external,
            method_name="__getitem__",
        )

    def can_operate(self, dunders: tuple[str, ...], a, b=None):
        objects = [a]
        if b is not None:
            objects.append(b)
        return all(
            [
                _has_original_dunder(
                    obj,
                    allowed_types=self.allowed_operations,
                    allowed_methods=self._operator_dunder_methods(dunder),
                    allowed_external=self.allowed_operations_external,
                    method_name=dunder,
                )
                for dunder in dunders
                for obj in objects
            ]
        )

    def _operator_dunder_methods(self, dunder: str) -> set[Callable]:
        if dunder not in self._operation_methods_cache:
            self._operation_methods_cache[dunder] = self._safe_get_methods(
                self.allowed_operations, dunder
            )
        return self._operation_methods_cache[dunder]

    @cached_property
    def _getitem_methods(self) -> set[Callable]:
        return self._safe_get_methods(self.allowed_getitem, "__getitem__")

    @cached_property
    def _getattr_methods(self) -> set[Callable]:
        return self._safe_get_methods(self.allowed_getattr, "__getattr__")

    @cached_property
    def _getattribute_methods(self) -> set[Callable]:
        return self._safe_get_methods(self.allowed_getattr, "__getattribute__")

    def _safe_get_methods(self, classes, name) -> set[Callable]:
        return {
            method
            for class_ in classes
            for method in [getattr(class_, name, None)]
            if method
        }


class _DummyNamedTuple(NamedTuple):
    """Used internally to retrieve methods of named tuple instance."""


class EvaluationContext(NamedTuple):
    #: Local namespace
    locals: dict
    #: Global namespace
    globals: dict
    #: Evaluation policy identifier
    evaluation: Literal["forbidden", "minimal", "limited", "unsafe", "dangerous"] = (
        "forbidden"
    )
    #: Whether the evaluation of code takes place inside of a subscript.
    #: Useful for evaluating ``:-1, 'col'`` in ``df[:-1, 'col']``.
    in_subscript: bool = False
    #: Auto import method
    auto_import: Callable[list[str], ModuleType] | None = None
    #: Overrides for evaluation policy
    policy_overrides: dict = {}


class _IdentitySubscript:
    """Returns the key itself when item is requested via subscript."""

    def __getitem__(self, key):
        return key


IDENTITY_SUBSCRIPT = _IdentitySubscript()
SUBSCRIPT_MARKER = "__SUBSCRIPT_SENTINEL__"
UNKNOWN_SIGNATURE = Signature()
NOT_EVALUATED = object()


class GuardRejection(Exception):
    """Exception raised when guard rejects evaluation attempt."""

    pass


def guarded_eval(code: str, context: EvaluationContext):
    """Evaluate provided code in the evaluation context.

    If evaluation policy given by context is set to ``forbidden``
    no evaluation will be performed; if it is set to ``dangerous``
    standard :func:`eval` will be used; finally, for any other,
    policy :func:`eval_node` will be called on parsed AST.
    """
    locals_ = context.locals

    if context.evaluation == "forbidden":
        raise GuardRejection("Forbidden mode")

    # note: not using `ast.literal_eval` as it does not implement
    # getitem at all, for example it fails on simple `[0][1]`

    if context.in_subscript:
        # syntactic sugar for ellipsis (:) is only available in subscripts
        # so we need to trick the ast parser into thinking that we have
        # a subscript, but we need to be able to later recognise that we did
        # it so we can ignore the actual __getitem__ operation
        if not code:
            return tuple()
        locals_ = locals_.copy()
        locals_[SUBSCRIPT_MARKER] = IDENTITY_SUBSCRIPT
        code = SUBSCRIPT_MARKER + "[" + code + "]"
        context = EvaluationContext(**{**context._asdict(), **{"locals": locals_}})

    if context.evaluation == "dangerous":
        return eval(code, context.globals, context.locals)

    expression = ast.parse(code, mode="eval")

    return eval_node(expression, context)


BINARY_OP_DUNDERS: dict[type[ast.operator], tuple[str]] = {
    ast.Add: ("__add__",),
    ast.Sub: ("__sub__",),
    ast.Mult: ("__mul__",),
    ast.Div: ("__truediv__",),
    ast.FloorDiv: ("__floordiv__",),
    ast.Mod: ("__mod__",),
    ast.Pow: ("__pow__",),
    ast.LShift: ("__lshift__",),
    ast.RShift: ("__rshift__",),
    ast.BitOr: ("__or__",),
    ast.BitXor: ("__xor__",),
    ast.BitAnd: ("__and__",),
    ast.MatMult: ("__matmul__",),
}

COMP_OP_DUNDERS: dict[type[ast.cmpop], tuple[str, ...]] = {
    ast.Eq: ("__eq__",),
    ast.NotEq: ("__ne__", "__eq__"),
    ast.Lt: ("__lt__", "__gt__"),
    ast.LtE: ("__le__", "__ge__"),
    ast.Gt: ("__gt__", "__lt__"),
    ast.GtE: ("__ge__", "__le__"),
    ast.In: ("__contains__",),
    # Note: ast.Is, ast.IsNot, ast.NotIn are handled specially
}

UNARY_OP_DUNDERS: dict[type[ast.unaryop], tuple[str, ...]] = {
    ast.USub: ("__neg__",),
    ast.UAdd: ("__pos__",),
    # we have to check both __inv__ and __invert__!
    ast.Invert: ("__invert__", "__inv__"),
    ast.Not: ("__not__",),
}


class ImpersonatingDuck:
    """A dummy class used to create objects of other classes without calling their ``__init__``"""

    # no-op: override __class__ to impersonate


class _Duck:
    """A dummy class used to create objects pretending to have given attributes"""

    def __init__(self, attributes: Optional[dict] = None, items: Optional[dict] = None):
        self.attributes = attributes or {}
        self.items = items or {}

    def __getattr__(self, attr: str):
        return self.attributes[attr]

    def __hasattr__(self, attr: str):
        return attr in self.attributes

    def __dir__(self):
        return [*dir(super), *self.attributes]

    def __getitem__(self, key: str):
        return self.items[key]

    def __hasitem__(self, key: str):
        return self.items[key]

    def _ipython_key_completions_(self):
        return self.items.keys()


def _find_dunder(node_op, dunders) -> Union[tuple[str, ...], None]:
    dunder = None
    for op, candidate_dunder in dunders.items():
        if isinstance(node_op, op):
            dunder = candidate_dunder
    return dunder


def get_policy(context: EvaluationContext) -> EvaluationPolicy:
    policy = copy(EVALUATION_POLICIES[context.evaluation])

    for key, value in context.policy_overrides.items():
        if hasattr(policy, key):
            setattr(policy, key, value)
        else:
            print(f"Incorrect policy override key: {key}")
    return policy


def eval_node(node: Union[ast.AST, None], context: EvaluationContext):
    """Evaluate AST node in provided context.

    Applies evaluation restrictions defined in the context. Currently does not support evaluation of functions with keyword arguments.

    Does not evaluate actions that always have side effects:

    - class definitions (``class sth: ...``)
    - function definitions (``def sth: ...``)
    - variable assignments (``x = 1``)
    - augmented assignments (``x += 1``)
    - deletions (``del x``)

    Does not evaluate operations which do not return values:

    - assertions (``assert x``)
    - pass (``pass``)
    - imports (``import x``)
    - control flow:

        - conditionals (``if x:``) except for ternary IfExp (``a if x else b``)
        - loops (``for`` and ``while``)
        - exception handling

    The purpose of this function is to guard against unwanted side-effects;
    it does not give guarantees on protection from malicious code execution.
    """
    policy = get_policy(context)

    if node is None:
        return None
    if isinstance(node, ast.Expression):
        return eval_node(node.body, context)
    if isinstance(node, ast.BinOp):
        left = eval_node(node.left, context)
        right = eval_node(node.right, context)
        dunders = _find_dunder(node.op, BINARY_OP_DUNDERS)
        if dunders:
            if policy.can_operate(dunders, left, right):
                return getattr(left, dunders[0])(right)
            else:
                raise GuardRejection(
                    f"Operation (`{dunders}`) for",
                    type(left),
                    f"not allowed in {context.evaluation} mode",
                )
    if isinstance(node, ast.Compare):
        left = eval_node(node.left, context)
        all_true = True
        negate = False
        for op, right in zip(node.ops, node.comparators):
            right = eval_node(right, context)
            dunder = None
            dunders = _find_dunder(op, COMP_OP_DUNDERS)
            if not dunders:
                if isinstance(op, ast.NotIn):
                    dunders = COMP_OP_DUNDERS[ast.In]
                    negate = True
                if isinstance(op, ast.Is):
                    dunder = "is_"
                if isinstance(op, ast.IsNot):
                    dunder = "is_"
                    negate = True
            if not dunder and dunders:
                dunder = dunders[0]
            if dunder:
                a, b = (right, left) if dunder == "__contains__" else (left, right)
                if dunder == "is_" or dunders and policy.can_operate(dunders, a, b):
                    result = getattr(operator, dunder)(a, b)
                    if negate:
                        result = not result
                    if not result:
                        all_true = False
                    left = right
                else:
                    raise GuardRejection(
                        f"Comparison (`{dunder}`) for",
                        type(left),
                        f"not allowed in {context.evaluation} mode",
                    )
            else:
                raise ValueError(
                    f"Comparison `{dunder}` not supported"
                )  # pragma: no cover
        return all_true
    if isinstance(node, ast.Constant):
        return node.value
    if isinstance(node, ast.Tuple):
        return tuple(eval_node(e, context) for e in node.elts)
    if isinstance(node, ast.List):
        return [eval_node(e, context) for e in node.elts]
    if isinstance(node, ast.Set):
        return {eval_node(e, context) for e in node.elts}
    if isinstance(node, ast.Dict):
        return dict(
            zip(
                [eval_node(k, context) for k in node.keys],
                [eval_node(v, context) for v in node.values],
            )
        )
    if isinstance(node, ast.Slice):
        return slice(
            eval_node(node.lower, context),
            eval_node(node.upper, context),
            eval_node(node.step, context),
        )
    if isinstance(node, ast.UnaryOp):
        value = eval_node(node.operand, context)
        dunders = _find_dunder(node.op, UNARY_OP_DUNDERS)
        if dunders:
            if policy.can_operate(dunders, value):
                return getattr(value, dunders[0])()
            else:
                raise GuardRejection(
                    f"Operation (`{dunders}`) for",
                    type(value),
                    f"not allowed in {context.evaluation} mode",
                )
    if isinstance(node, ast.Subscript):
        value = eval_node(node.value, context)
        slice_ = eval_node(node.slice, context)
        if policy.can_get_item(value, slice_):
            return value[slice_]
        raise GuardRejection(
            "Subscript access (`__getitem__`) for",
            type(value),  # not joined to avoid calling `repr`
            f" not allowed in {context.evaluation} mode",
        )
    if isinstance(node, ast.Name):
        return _eval_node_name(node.id, context)
    if isinstance(node, ast.Attribute):
        value = eval_node(node.value, context)
        if policy.can_get_attr(value, node.attr):
            return getattr(value, node.attr)
        raise GuardRejection(
            "Attribute access (`__getattr__`) for",
            type(value),  # not joined to avoid calling `repr`
            f"not allowed in {context.evaluation} mode",
        )
    if isinstance(node, ast.IfExp):
        test = eval_node(node.test, context)
        if test:
            return eval_node(node.body, context)
        else:
            return eval_node(node.orelse, context)
    if isinstance(node, ast.Call):
        func = eval_node(node.func, context)
        if policy.can_call(func) and not node.keywords:
            args = [eval_node(arg, context) for arg in node.args]
            return func(*args)
        if isclass(func):
            # this code path gets entered when calling class e.g. `MyClass()`
            # or `my_instance.__class__()` - in both cases `func` is `MyClass`.
            # Should return `MyClass` if `__new__` is not overridden,
            # otherwise whatever `__new__` return type is.
            overridden_return_type = _eval_return_type(func.__new__, node, context)
            if overridden_return_type is not NOT_EVALUATED:
                return overridden_return_type
            return _create_duck_for_heap_type(func)
        else:
            return_type = _eval_return_type(func, node, context)
            if return_type is not NOT_EVALUATED:
                return return_type
        raise GuardRejection(
            "Call for",
            func,  # not joined to avoid calling `repr`
            f"not allowed in {context.evaluation} mode",
        )
    raise ValueError("Unhandled node", ast.dump(node))


def _eval_return_type(func: Callable, node: ast.Call, context: EvaluationContext):
    """Evaluate return type of a given callable function.

    Returns the built-in type, a duck or NOT_EVALUATED sentinel.
    """
    try:
        sig = signature(func)
    except ValueError:
        sig = UNKNOWN_SIGNATURE
    # if annotation was not stringized, or it was stringized
    # but resolved by signature call we know the return type
    not_empty = sig.return_annotation is not Signature.empty
    if not_empty:
        return _resolve_annotation(sig.return_annotation, sig, func, node, context)
    return NOT_EVALUATED


def _resolve_annotation(
    annotation,
    sig: Signature,
    func: Callable,
    node: ast.Call,
    context: EvaluationContext,
):
    """Resolve annotation created by user with `typing` module and custom objects."""
    annotation = (
        _eval_node_name(annotation, context)
        if isinstance(annotation, str)
        else annotation
    )
    origin = get_origin(annotation)
    if annotation is Self and hasattr(func, "__self__"):
        return func.__self__
    elif origin is Literal:
        type_args = get_args(annotation)
        if len(type_args) == 1:
            return type_args[0]
    elif annotation is LiteralString:
        return ""
    elif annotation is AnyStr:
        index = None
        for i, (key, value) in enumerate(sig.parameters.items()):
            if value.annotation is AnyStr:
                index = i
                break
        if index is not None and index < len(node.args):
            return eval_node(node.args[index], context)
    elif origin is TypeGuard:
        return False
    elif origin is Union:
        attributes = [
            attr
            for type_arg in get_args(annotation)
            for attr in dir(_resolve_annotation(type_arg, sig, func, node, context))
        ]
        return _Duck(attributes=dict.fromkeys(attributes))
    elif is_typeddict(annotation):
        return _Duck(
            attributes=dict.fromkeys(dir(dict())),
            items={
                k: _resolve_annotation(v, sig, func, node, context)
                for k, v in annotation.__annotations__.items()
            },
        )
    elif hasattr(annotation, "_is_protocol"):
        return _Duck(attributes=dict.fromkeys(dir(annotation)))
    elif origin is Annotated:
        type_arg = get_args(annotation)[0]
        return _resolve_annotation(type_arg, sig, func, node, context)
    elif isinstance(annotation, NewType):
        return _eval_or_create_duck(annotation.__supertype__, node, context)
    elif isinstance(annotation, TypeAliasType):
        return _eval_or_create_duck(annotation.__value__, node, context)
    else:
        return _eval_or_create_duck(annotation, node, context)


def _eval_node_name(node_id: str, context: EvaluationContext):
    policy = get_policy(context)
    if policy.allow_locals_access and node_id in context.locals:
        return context.locals[node_id]
    if policy.allow_globals_access and node_id in context.globals:
        return context.globals[node_id]
    if policy.allow_builtins_access and hasattr(builtins, node_id):
        # note: do not use __builtins__, it is implementation detail of cPython
        return getattr(builtins, node_id)
    if policy.allow_auto_import and context.auto_import:
        return context.auto_import(node_id)
    if not policy.allow_globals_access and not policy.allow_locals_access:
        raise GuardRejection(
            f"Namespace access not allowed in {context.evaluation} mode"
        )
    else:
        raise NameError(f"{node_id} not found in locals, globals, nor builtins")


def _eval_or_create_duck(duck_type, node: ast.Call, context: EvaluationContext):
    policy = get_policy(context)
    # if allow-listed builtin is on type annotation, instantiate it
    if policy.can_call(duck_type) and not node.keywords:
        args = [eval_node(arg, context) for arg in node.args]
        return duck_type(*args)
    # if custom class is in type annotation, mock it
    return _create_duck_for_heap_type(duck_type)


def _create_duck_for_heap_type(duck_type):
    """Create an imitation of an object of a given type (a duck).

    Returns the duck or NOT_EVALUATED sentinel if duck could not be created.
    """
    duck = ImpersonatingDuck()
    try:
        # this only works for heap types, not builtins
        duck.__class__ = duck_type
        return duck
    except TypeError:
        pass
    return NOT_EVALUATED


SUPPORTED_EXTERNAL_GETITEM = {
    ("pandas", "core", "indexing", "_iLocIndexer"),
    ("pandas", "core", "indexing", "_LocIndexer"),
    ("pandas", "DataFrame"),
    ("pandas", "Series"),
    ("numpy", "ndarray"),
    ("numpy", "void"),
}


BUILTIN_GETITEM: set[InstancesHaveGetItem] = {
    dict,
    str,  # type: ignore[arg-type]
    bytes,  # type: ignore[arg-type]
    list,
    tuple,
    collections.defaultdict,
    collections.deque,
    collections.OrderedDict,
    collections.ChainMap,
    collections.UserDict,
    collections.UserList,
    collections.UserString,  # type: ignore[arg-type]
    _DummyNamedTuple,
    _IdentitySubscript,
}


def _list_methods(cls, source=None):
    """For use on immutable objects or with methods returning a copy"""
    return [getattr(cls, k) for k in (source if source else dir(cls))]


dict_non_mutating_methods = ("copy", "keys", "values", "items")
list_non_mutating_methods = ("copy", "index", "count")
set_non_mutating_methods = set(dir(set)) & set(dir(frozenset))


dict_keys: type[collections.abc.KeysView] = type({}.keys())

NUMERICS = {int, float, complex}

ALLOWED_CALLS = {
    bytes,
    *_list_methods(bytes),
    dict,
    *_list_methods(dict, dict_non_mutating_methods),
    dict_keys.isdisjoint,
    list,
    *_list_methods(list, list_non_mutating_methods),
    set,
    *_list_methods(set, set_non_mutating_methods),
    frozenset,
    *_list_methods(frozenset),
    range,
    str,
    *_list_methods(str),
    tuple,
    *_list_methods(tuple),
    *NUMERICS,
    *[method for numeric_cls in NUMERICS for method in _list_methods(numeric_cls)],
    collections.deque,
    *_list_methods(collections.deque, list_non_mutating_methods),
    collections.defaultdict,
    *_list_methods(collections.defaultdict, dict_non_mutating_methods),
    collections.OrderedDict,
    *_list_methods(collections.OrderedDict, dict_non_mutating_methods),
    collections.UserDict,
    *_list_methods(collections.UserDict, dict_non_mutating_methods),
    collections.UserList,
    *_list_methods(collections.UserList, list_non_mutating_methods),
    collections.UserString,
    *_list_methods(collections.UserString, dir(str)),
    collections.Counter,
    *_list_methods(collections.Counter, dict_non_mutating_methods),
    collections.Counter.elements,
    collections.Counter.most_common,
}

BUILTIN_GETATTR: set[MayHaveGetattr] = {
    *BUILTIN_GETITEM,
    set,
    frozenset,
    object,
    type,  # `type` handles a lot of generic cases, e.g. numbers as in `int.real`.
    *NUMERICS,
    dict_keys,
    MethodDescriptorType,
    ModuleType,
}


BUILTIN_OPERATIONS = {*BUILTIN_GETATTR}

EVALUATION_POLICIES = {
    "minimal": EvaluationPolicy(
        allow_builtins_access=True,
        allow_locals_access=False,
        allow_globals_access=False,
        allow_item_access=False,
        allow_attr_access=False,
        allowed_calls=set(),
        allow_any_calls=False,
        allow_all_operations=False,
    ),
    "limited": SelectivePolicy(
        allowed_getitem=BUILTIN_GETITEM,
        allowed_getitem_external=SUPPORTED_EXTERNAL_GETITEM,
        allowed_getattr=BUILTIN_GETATTR,
        allowed_getattr_external={
            # pandas Series/Frame implements custom `__getattr__`
            ("pandas", "DataFrame"),
            ("pandas", "Series"),
        },
        allowed_operations=BUILTIN_OPERATIONS,
        allow_builtins_access=True,
        allow_locals_access=True,
        allow_globals_access=True,
        allowed_calls=ALLOWED_CALLS,
    ),
    "unsafe": EvaluationPolicy(
        allow_builtins_access=True,
        allow_locals_access=True,
        allow_globals_access=True,
        allow_attr_access=True,
        allow_item_access=True,
        allow_any_calls=True,
        allow_all_operations=True,
    ),
}


__all__ = [
    "guarded_eval",
    "eval_node",
    "GuardRejection",
    "EvaluationContext",
    "_unbind_method",
]