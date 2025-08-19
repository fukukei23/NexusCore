
# === NexusCore/openenv\Lib\site-packages\litellm\proxy\pass_through_endpoints\llm_provider_handlers\base_passthrough_logging_handler.py ===
import json
from datetime import datetime
from typing import TYPE_CHECKING, Any, List, Optional, Union

import httpx

import litellm
from litellm._logging import verbose_proxy_logger
from litellm.litellm_core_utils.litellm_logging import Logging as LiteLLMLoggingObj
from litellm.litellm_core_utils.litellm_logging import (
    get_standard_logging_object_payload,
)
from litellm.llms.base_llm.chat.transformation import BaseConfig
from litellm.proxy._types import PassThroughEndpointLoggingTypedDict
from litellm.proxy.auth.auth_utils import get_end_user_id_from_request_body
from litellm.types.passthrough_endpoints.pass_through_endpoints import (
    PassthroughStandardLoggingPayload,
)
from litellm.types.utils import LlmProviders, ModelResponse, TextCompletionResponse

if TYPE_CHECKING:
    from ..success_handler import PassThroughEndpointLogging
    from ..types import EndpointType
else:
    PassThroughEndpointLogging = Any
    EndpointType = Any

from abc import ABC, abstractmethod


class BasePassthroughLoggingHandler(ABC):
    @property
    @abstractmethod
    def llm_provider_name(self) -> LlmProviders:
        pass

    @abstractmethod
    def get_provider_config(self, model: str) -> BaseConfig:
        pass

    def passthrough_chat_handler(
        self,
        httpx_response: httpx.Response,
        response_body: dict,
        logging_obj: LiteLLMLoggingObj,
        url_route: str,
        result: str,
        start_time: datetime,
        end_time: datetime,
        cache_hit: bool,
        request_body: dict,
        **kwargs,
    ) -> PassThroughEndpointLoggingTypedDict:
        """
        Transforms LLM response to OpenAI response, generates a standard logging object so downstream logging can be handled
        """
        model = request_body.get("model", response_body.get("model", ""))
        provider_config = self.get_provider_config(model=model)
        litellm_model_response: ModelResponse = provider_config.transform_response(
            raw_response=httpx_response,
            model_response=litellm.ModelResponse(),
            model=model,
            messages=[],
            logging_obj=logging_obj,
            optional_params={},
            api_key="",
            request_data={},
            encoding=litellm.encoding,
            json_mode=False,
            litellm_params={},
        )

        kwargs = self._create_response_logging_payload(
            litellm_model_response=litellm_model_response,
            model=model,
            kwargs=kwargs,
            start_time=start_time,
            end_time=end_time,
            logging_obj=logging_obj,
        )

        return {
            "result": litellm_model_response,
            "kwargs": kwargs,
        }

    def _get_user_from_metadata(
        self,
        passthrough_logging_payload: PassthroughStandardLoggingPayload,
    ) -> Optional[str]:
        request_body = passthrough_logging_payload.get("request_body")
        if request_body:
            return get_end_user_id_from_request_body(request_body)
        return None

    def _create_response_logging_payload(
        self,
        litellm_model_response: Union[ModelResponse, TextCompletionResponse],
        model: str,
        kwargs: dict,
        start_time: datetime,
        end_time: datetime,
        logging_obj: LiteLLMLoggingObj,
    ) -> dict:
        """
        Create the standard logging object for Generic LLM passthrough

        handles streaming and non-streaming responses
        """

        try:
            response_cost = litellm.completion_cost(
                completion_response=litellm_model_response,
                model=model,
            )

            kwargs["response_cost"] = response_cost
            kwargs["model"] = model
            passthrough_logging_payload: Optional[PassthroughStandardLoggingPayload] = (  # type: ignore
                kwargs.get("passthrough_logging_payload")
            )
            if passthrough_logging_payload:
                user = self._get_user_from_metadata(
                    passthrough_logging_payload=passthrough_logging_payload,
                )
                if user:
                    kwargs.setdefault("litellm_params", {})
                    kwargs["litellm_params"].update(
                        {"proxy_server_request": {"body": {"user": user}}}
                    )

            # Make standard logging object for Anthropic
            standard_logging_object = get_standard_logging_object_payload(
                kwargs=kwargs,
                init_response_obj=litellm_model_response,
                start_time=start_time,
                end_time=end_time,
                logging_obj=logging_obj,
                status="success",
            )

            # pretty print standard logging object
            verbose_proxy_logger.debug(
                "standard_logging_object= %s",
                json.dumps(standard_logging_object, indent=4),
            )
            kwargs["standard_logging_object"] = standard_logging_object

            # set litellm_call_id to logging response object
            litellm_model_response.id = logging_obj.litellm_call_id
            litellm_model_response.model = model
            logging_obj.model_call_details["model"] = model
            return kwargs
        except Exception as e:
            verbose_proxy_logger.exception(
                "Error creating LLM passthrough response logging payload: %s", e
            )
            return kwargs

    @abstractmethod
    def _build_complete_streaming_response(
        self,
        all_chunks: List[str],
        litellm_logging_obj: LiteLLMLoggingObj,
        model: str,
    ) -> Optional[Union[ModelResponse, TextCompletionResponse]]:
        """
        Builds complete response from raw chunks

        - Converts str chunks to generic chunks
        - Converts generic chunks to litellm chunks (OpenAI format)
        - Builds complete response from litellm chunks
        """
        pass

    def _handle_logging_llm_collected_chunks(
        self,
        litellm_logging_obj: LiteLLMLoggingObj,
        passthrough_success_handler_obj: PassThroughEndpointLogging,
        url_route: str,
        request_body: dict,
        endpoint_type: EndpointType,
        start_time: datetime,
        all_chunks: List[str],
        end_time: datetime,
    ) -> PassThroughEndpointLoggingTypedDict:
        """
        Takes raw chunks from Anthropic passthrough endpoint and logs them in litellm callbacks

        - Builds complete response from chunks
        - Creates standard logging object
        - Logs in litellm callbacks
        """

        model = request_body.get("model", "")
        complete_streaming_response = self._build_complete_streaming_response(
            all_chunks=all_chunks,
            litellm_logging_obj=litellm_logging_obj,
            model=model,
        )
        if complete_streaming_response is None:
            verbose_proxy_logger.error(
                "Unable to build complete streaming response for Anthropic passthrough endpoint, not logging..."
            )
            return {
                "result": None,
                "kwargs": {},
            }
        kwargs = self._create_response_logging_payload(
            litellm_model_response=complete_streaming_response,
            model=model,
            kwargs={},
            start_time=start_time,
            end_time=end_time,
            logging_obj=litellm_logging_obj,
        )

        return {
            "result": complete_streaming_response,
            "kwargs": kwargs,
        }

# === NexusCore/openenv\Lib\site-packages\nltk\translate\chrf_score.py ===
# Natural Language Toolkit: ChrF score
#
# Copyright (C) 2001-2024 NLTK Project
# Authors: Maja Popovic
# Contributors: Liling Tan, Aleš Tamchyna (Memsource)
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT

""" ChrF score implementation """
import re
from collections import Counter, defaultdict

from nltk.util import ngrams


def sentence_chrf(
    reference, hypothesis, min_len=1, max_len=6, beta=3.0, ignore_whitespace=True
):
    """
    Calculates the sentence level CHRF (Character n-gram F-score) described in
     - Maja Popovic. 2015. CHRF: Character n-gram F-score for Automatic MT Evaluation.
       In Proceedings of the 10th Workshop on Machine Translation.
       https://www.statmt.org/wmt15/pdf/WMT49.pdf
     - Maja Popovic. 2016. CHRF Deconstructed: β Parameters and n-gram Weights.
       In Proceedings of the 1st Conference on Machine Translation.
       https://www.statmt.org/wmt16/pdf/W16-2341.pdf

    This implementation of CHRF only supports a single reference at the moment.

    For details not reported in the paper, consult Maja Popovic's original
    implementation: https://github.com/m-popovic/chrF

    The code should output results equivalent to running CHRF++ with the
    following options: -nw 0 -b 3

    An example from the original BLEU paper
    https://www.aclweb.org/anthology/P02-1040.pdf

        >>> ref1 = str('It is a guide to action that ensures that the military '
        ...            'will forever heed Party commands').split()
        >>> hyp1 = str('It is a guide to action which ensures that the military '
        ...            'always obeys the commands of the party').split()
        >>> hyp2 = str('It is to insure the troops forever hearing the activity '
        ...            'guidebook that party direct').split()
        >>> sentence_chrf(ref1, hyp1) # doctest: +ELLIPSIS
        0.6349...
        >>> sentence_chrf(ref1, hyp2) # doctest: +ELLIPSIS
        0.3330...

    The infamous "the the the ... " example

        >>> ref = 'the cat is on the mat'.split()
        >>> hyp = 'the the the the the the the'.split()
        >>> sentence_chrf(ref, hyp)  # doctest: +ELLIPSIS
        0.1468...

    An example to show that this function allows users to use strings instead of
    tokens, i.e. list(str) as inputs.

        >>> ref1 = str('It is a guide to action that ensures that the military '
        ...            'will forever heed Party commands')
        >>> hyp1 = str('It is a guide to action which ensures that the military '
        ...            'always obeys the commands of the party')
        >>> sentence_chrf(ref1, hyp1) # doctest: +ELLIPSIS
        0.6349...
        >>> type(ref1) == type(hyp1) == str
        True
        >>> sentence_chrf(ref1.split(), hyp1.split()) # doctest: +ELLIPSIS
        0.6349...

    To skip the unigrams and only use 2- to 3-grams:

        >>> sentence_chrf(ref1, hyp1, min_len=2, max_len=3) # doctest: +ELLIPSIS
        0.6617...

    :param references: reference sentence
    :type references: list(str) / str
    :param hypothesis: a hypothesis sentence
    :type hypothesis: list(str) / str
    :param min_len: The minimum order of n-gram this function should extract.
    :type min_len: int
    :param max_len: The maximum order of n-gram this function should extract.
    :type max_len: int
    :param beta: the parameter to assign more importance to recall over precision
    :type beta: float
    :param ignore_whitespace: ignore whitespace characters in scoring
    :type ignore_whitespace: bool
    :return: the sentence level CHRF score.
    :rtype: float
    """
    return corpus_chrf(
        [reference],
        [hypothesis],
        min_len,
        max_len,
        beta=beta,
        ignore_whitespace=ignore_whitespace,
    )


def _preprocess(sent, ignore_whitespace):
    if type(sent) != str:
        # turn list of tokens into a string
        sent = " ".join(sent)

    if ignore_whitespace:
        sent = re.sub(r"\s+", "", sent)
    return sent


def chrf_precision_recall_fscore_support(
    reference, hypothesis, n, beta=3.0, epsilon=1e-16
):
    """
    This function computes the precision, recall and fscore from the ngram
    overlaps. It returns the `support` which is the true positive score.

    By underspecifying the input type, the function will be agnostic as to how
    it computes the ngrams and simply take the whichever element in the list;
    it could be either token or character.

    :param reference: The reference sentence.
    :type reference: list
    :param hypothesis: The hypothesis sentence.
    :type hypothesis: list
    :param n: Extract up to the n-th order ngrams
    :type n: int
    :param beta: The parameter to assign more importance to recall over precision.
    :type beta: float
    :param epsilon: The fallback value if the hypothesis or reference is empty.
    :type epsilon: float
    :return: Returns the precision, recall and f-score and support (true positive).
    :rtype: tuple(float)
    """
    ref_ngrams = Counter(ngrams(reference, n))
    hyp_ngrams = Counter(ngrams(hypothesis, n))

    # calculate the number of ngram matches
    overlap_ngrams = ref_ngrams & hyp_ngrams
    tp = sum(overlap_ngrams.values())  # True positives.
    tpfp = sum(hyp_ngrams.values())  # True positives + False positives.
    tpfn = sum(ref_ngrams.values())  # True positives + False negatives.

    try:
        prec = tp / tpfp  # precision
        rec = tp / tpfn  # recall
        factor = beta**2
        fscore = (1 + factor) * (prec * rec) / (factor * prec + rec)
    except ZeroDivisionError:
        prec = rec = fscore = epsilon
    return prec, rec, fscore, tp


def corpus_chrf(
    references, hypotheses, min_len=1, max_len=6, beta=3.0, ignore_whitespace=True
):
    """
    Calculates the corpus level CHRF (Character n-gram F-score), it is the
    macro-averaged value of the sentence/segment level CHRF score.

    This implementation of CHRF only supports a single reference at the moment.

        >>> ref1 = str('It is a guide to action that ensures that the military '
        ...            'will forever heed Party commands').split()
        >>> ref2 = str('It is the guiding principle which guarantees the military '
        ...            'forces always being under the command of the Party').split()
        >>>
        >>> hyp1 = str('It is a guide to action which ensures that the military '
        ...            'always obeys the commands of the party').split()
        >>> hyp2 = str('It is to insure the troops forever hearing the activity '
        ...            'guidebook that party direct')
        >>> corpus_chrf([ref1, ref2, ref1, ref2], [hyp1, hyp2, hyp2, hyp1]) # doctest: +ELLIPSIS
        0.3910...

    :param references: a corpus of list of reference sentences, w.r.t. hypotheses
    :type references: list(list(str))
    :param hypotheses: a list of hypothesis sentences
    :type hypotheses: list(list(str))
    :param min_len: The minimum order of n-gram this function should extract.
    :type min_len: int
    :param max_len: The maximum order of n-gram this function should extract.
    :type max_len: int
    :param beta: the parameter to assign more importance to recall over precision
    :type beta: float
    :param ignore_whitespace: ignore whitespace characters in scoring
    :type ignore_whitespace: bool
    :return: the sentence level CHRF score.
    :rtype: float
    """

    assert len(references) == len(
        hypotheses
    ), "The number of hypotheses and their references should be the same"
    num_sents = len(hypotheses)

    # Keep f-scores for each n-gram order separate
    ngram_fscores = defaultdict(list)

    # Iterate through each hypothesis and their corresponding references.
    for reference, hypothesis in zip(references, hypotheses):
        # preprocess both reference and hypothesis
        reference = _preprocess(reference, ignore_whitespace)
        hypothesis = _preprocess(hypothesis, ignore_whitespace)

        # Calculate f-scores for each sentence and for each n-gram order
        # separately.
        for n in range(min_len, max_len + 1):
            # Compute the precision, recall, fscore and support.
            prec, rec, fscore, tp = chrf_precision_recall_fscore_support(
                reference, hypothesis, n, beta=beta
            )
            ngram_fscores[n].append(fscore)

    # how many n-gram sizes
    num_ngram_sizes = len(ngram_fscores)

    # sum of f-scores over all sentences for each n-gram order
    total_scores = [sum(fscores) for n, fscores in ngram_fscores.items()]

    # macro-average over n-gram orders and over all sentences
    return (sum(total_scores) / num_ngram_sizes) / num_sents

# === NexusCore/openenv\Lib\site-packages\pip\_vendor\urllib3\util\ssltransport.py ===
import io
import socket
import ssl

from ..exceptions import ProxySchemeUnsupported
from ..packages import six

SSL_BLOCKSIZE = 16384


class SSLTransport:
    """
    The SSLTransport wraps an existing socket and establishes an SSL connection.

    Contrary to Python's implementation of SSLSocket, it allows you to chain
    multiple TLS connections together. It's particularly useful if you need to
    implement TLS within TLS.

    The class supports most of the socket API operations.
    """

    @staticmethod
    def _validate_ssl_context_for_tls_in_tls(ssl_context):
        """
        Raises a ProxySchemeUnsupported if the provided ssl_context can't be used
        for TLS in TLS.

        The only requirement is that the ssl_context provides the 'wrap_bio'
        methods.
        """

        if not hasattr(ssl_context, "wrap_bio"):
            if six.PY2:
                raise ProxySchemeUnsupported(
                    "TLS in TLS requires SSLContext.wrap_bio() which isn't "
                    "supported on Python 2"
                )
            else:
                raise ProxySchemeUnsupported(
                    "TLS in TLS requires SSLContext.wrap_bio() which isn't "
                    "available on non-native SSLContext"
                )

    def __init__(
        self, socket, ssl_context, server_hostname=None, suppress_ragged_eofs=True
    ):
        """
        Create an SSLTransport around socket using the provided ssl_context.
        """
        self.incoming = ssl.MemoryBIO()
        self.outgoing = ssl.MemoryBIO()

        self.suppress_ragged_eofs = suppress_ragged_eofs
        self.socket = socket

        self.sslobj = ssl_context.wrap_bio(
            self.incoming, self.outgoing, server_hostname=server_hostname
        )

        # Perform initial handshake.
        self._ssl_io_loop(self.sslobj.do_handshake)

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()

    def fileno(self):
        return self.socket.fileno()

    def read(self, len=1024, buffer=None):
        return self._wrap_ssl_read(len, buffer)

    def recv(self, len=1024, flags=0):
        if flags != 0:
            raise ValueError("non-zero flags not allowed in calls to recv")
        return self._wrap_ssl_read(len)

    def recv_into(self, buffer, nbytes=None, flags=0):
        if flags != 0:
            raise ValueError("non-zero flags not allowed in calls to recv_into")
        if buffer and (nbytes is None):
            nbytes = len(buffer)
        elif nbytes is None:
            nbytes = 1024
        return self.read(nbytes, buffer)

    def sendall(self, data, flags=0):
        if flags != 0:
            raise ValueError("non-zero flags not allowed in calls to sendall")
        count = 0
        with memoryview(data) as view, view.cast("B") as byte_view:
            amount = len(byte_view)
            while count < amount:
                v = self.send(byte_view[count:])
                count += v

    def send(self, data, flags=0):
        if flags != 0:
            raise ValueError("non-zero flags not allowed in calls to send")
        response = self._ssl_io_loop(self.sslobj.write, data)
        return response

    def makefile(
        self, mode="r", buffering=None, encoding=None, errors=None, newline=None
    ):
        """
        Python's httpclient uses makefile and buffered io when reading HTTP
        messages and we need to support it.

        This is unfortunately a copy and paste of socket.py makefile with small
        changes to point to the socket directly.
        """
        if not set(mode) <= {"r", "w", "b"}:
            raise ValueError("invalid mode %r (only r, w, b allowed)" % (mode,))

        writing = "w" in mode
        reading = "r" in mode or not writing
        assert reading or writing
        binary = "b" in mode
        rawmode = ""
        if reading:
            rawmode += "r"
        if writing:
            rawmode += "w"
        raw = socket.SocketIO(self, rawmode)
        self.socket._io_refs += 1
        if buffering is None:
            buffering = -1
        if buffering < 0:
            buffering = io.DEFAULT_BUFFER_SIZE
        if buffering == 0:
            if not binary:
                raise ValueError("unbuffered streams must be binary")
            return raw
        if reading and writing:
            buffer = io.BufferedRWPair(raw, raw, buffering)
        elif reading:
            buffer = io.BufferedReader(raw, buffering)
        else:
            assert writing
            buffer = io.BufferedWriter(raw, buffering)
        if binary:
            return buffer
        text = io.TextIOWrapper(buffer, encoding, errors, newline)
        text.mode = mode
        return text

    def unwrap(self):
        self._ssl_io_loop(self.sslobj.unwrap)

    def close(self):
        self.socket.close()

    def getpeercert(self, binary_form=False):
        return self.sslobj.getpeercert(binary_form)

    def version(self):
        return self.sslobj.version()

    def cipher(self):
        return self.sslobj.cipher()

    def selected_alpn_protocol(self):
        return self.sslobj.selected_alpn_protocol()

    def selected_npn_protocol(self):
        return self.sslobj.selected_npn_protocol()

    def shared_ciphers(self):
        return self.sslobj.shared_ciphers()

    def compression(self):
        return self.sslobj.compression()

    def settimeout(self, value):
        self.socket.settimeout(value)

    def gettimeout(self):
        return self.socket.gettimeout()

    def _decref_socketios(self):
        self.socket._decref_socketios()

    def _wrap_ssl_read(self, len, buffer=None):
        try:
            return self._ssl_io_loop(self.sslobj.read, len, buffer)
        except ssl.SSLError as e:
            if e.errno == ssl.SSL_ERROR_EOF and self.suppress_ragged_eofs:
                return 0  # eof, return 0.
            else:
                raise

    def _ssl_io_loop(self, func, *args):
        """Performs an I/O loop between incoming/outgoing and the socket."""
        should_loop = True
        ret = None

        while should_loop:
            errno = None
            try:
                ret = func(*args)
            except ssl.SSLError as e:
                if e.errno not in (ssl.SSL_ERROR_WANT_READ, ssl.SSL_ERROR_WANT_WRITE):
                    # WANT_READ, and WANT_WRITE are expected, others are not.
                    raise e
                errno = e.errno

            buf = self.outgoing.read()
            self.socket.sendall(buf)

            if errno is None:
                should_loop = False
            elif errno == ssl.SSL_ERROR_WANT_READ:
                buf = self.socket.recv(SSL_BLOCKSIZE)
                if buf:
                    self.incoming.write(buf)
                else:
                    self.incoming.write_eof()
        return ret

# === NexusCore/openenv\Lib\site-packages\selenium\webdriver\common\virtual_authenticator.py ===
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

import functools
from base64 import urlsafe_b64decode, urlsafe_b64encode
from enum import Enum
from typing import Any, Dict, Optional, Union


class Protocol(str, Enum):
    """Protocol to communicate with the authenticator."""

    CTAP2: str = "ctap2"
    U2F: str = "ctap1/u2f"


class Transport(str, Enum):
    """Transport method to communicate with the authenticator."""

    BLE: str = "ble"
    USB: str = "usb"
    NFC: str = "nfc"
    INTERNAL: str = "internal"


class VirtualAuthenticatorOptions:
    # These are so unnecessary but are now public API so we can't remove them without deprecating first.
    # These should not be class level state in here.
    Protocol = Protocol
    Transport = Transport

    def __init__(
        self,
        protocol: str = Protocol.CTAP2,
        transport: str = Transport.USB,
        has_resident_key: bool = False,
        has_user_verification: bool = False,
        is_user_consenting: bool = True,
        is_user_verified: bool = False,
    ) -> None:
        """Constructor.

        Initialize VirtualAuthenticatorOptions object.
        """

        self.protocol: str = protocol
        self.transport: str = transport
        self.has_resident_key: bool = has_resident_key
        self.has_user_verification: bool = has_user_verification
        self.is_user_consenting: bool = is_user_consenting
        self.is_user_verified: bool = is_user_verified

    def to_dict(self) -> Dict[str, Union[str, bool]]:
        return {
            "protocol": self.protocol,
            "transport": self.transport,
            "hasResidentKey": self.has_resident_key,
            "hasUserVerification": self.has_user_verification,
            "isUserConsenting": self.is_user_consenting,
            "isUserVerified": self.is_user_verified,
        }


class Credential:
    def __init__(
        self,
        credential_id: bytes,
        is_resident_credential: bool,
        rp_id: str,
        user_handle: Optional[bytes],
        private_key: bytes,
        sign_count: int,
    ):
        """Constructor. A credential stored in a virtual authenticator.
        https://w3c.github.io/webauthn/#credential-parameters.

        :Args:
            - credential_id (bytes): Unique base64 encoded string.
            - is_resident_credential (bool): Whether the credential is client-side discoverable.
            - rp_id (str): Relying party identifier.
            - user_handle (bytes): userHandle associated to the credential. Must be Base64 encoded string. Can be None.
            - private_key (bytes): Base64 encoded PKCS#8 private key.
            - sign_count (int): intital value for a signature counter.
        """
        self._id = credential_id
        self._is_resident_credential = is_resident_credential
        self._rp_id = rp_id
        self._user_handle = user_handle
        self._private_key = private_key
        self._sign_count = sign_count

    @property
    def id(self) -> str:
        return urlsafe_b64encode(self._id).decode()

    @property
    def is_resident_credential(self) -> bool:
        return self._is_resident_credential

    @property
    def rp_id(self) -> str:
        return self._rp_id

    @property
    def user_handle(self) -> Optional[str]:
        if self._user_handle:
            return urlsafe_b64encode(self._user_handle).decode()
        return None

    @property
    def private_key(self) -> str:
        return urlsafe_b64encode(self._private_key).decode()

    @property
    def sign_count(self) -> int:
        return self._sign_count

    @classmethod
    def create_non_resident_credential(cls, id: bytes, rp_id: str, private_key: bytes, sign_count: int) -> "Credential":
        """Creates a non-resident (i.e. stateless) credential.

        :Args:
          - id (bytes): Unique base64 encoded string.
          - rp_id (str): Relying party identifier.
          - private_key (bytes): Base64 encoded PKCS
          - sign_count (int): intital value for a signature counter.

        :Returns:
          - Credential: A non-resident credential.
        """
        return cls(id, False, rp_id, None, private_key, sign_count)

    @classmethod
    def create_resident_credential(
        cls, id: bytes, rp_id: str, user_handle: Optional[bytes], private_key: bytes, sign_count: int
    ) -> "Credential":
        """Creates a resident (i.e. stateful) credential.

        :Args:
          - id (bytes): Unique base64 encoded string.
          - rp_id (str): Relying party identifier.
          - user_handle (bytes): userHandle associated to the credential. Must be Base64 encoded string.
          - private_key (bytes): Base64 encoded PKCS
          - sign_count (int): intital value for a signature counter.

        :returns:
          - Credential: A resident credential.
        """
        return cls(id, True, rp_id, user_handle, private_key, sign_count)

    def to_dict(self) -> Dict[str, Any]:
        credential_data = {
            "credentialId": self.id,
            "isResidentCredential": self._is_resident_credential,
            "rpId": self.rp_id,
            "privateKey": self.private_key,
            "signCount": self.sign_count,
        }

        if self.user_handle:
            credential_data["userHandle"] = self.user_handle

        return credential_data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Credential":
        _id = urlsafe_b64decode(f"{data['credentialId']}==")
        is_resident_credential = bool(data["isResidentCredential"])
        rp_id = data.get("rpId", None)
        private_key = urlsafe_b64decode(f"{data['privateKey']}==")
        sign_count = int(data["signCount"])
        user_handle = urlsafe_b64decode(f"{data['userHandle']}==") if data.get("userHandle", None) else None

        return cls(_id, is_resident_credential, rp_id, user_handle, private_key, sign_count)

    def __str__(self) -> str:
        return f"Credential(id={self.id}, is_resident_credential={self.is_resident_credential}, rp_id={self.rp_id},\
            user_handle={self.user_handle}, private_key={self.private_key}, sign_count={self.sign_count})"


def required_chromium_based_browser(func):
    """A decorator to ensure that the client used is a chromium based
    browser."""

    @functools.wraps(func)
    def wrapper(self, *args, **kwargs):
        assert self.caps["browserName"].lower() not in [
            "firefox",
            "safari",
        ], "This only currently works in Chromium based browsers"
        return func(self, *args, **kwargs)

    return wrapper


def required_virtual_authenticator(func):
    """A decorator to ensure that the function is called with a virtual
    authenticator."""

    @functools.wraps(func)
    @required_chromium_based_browser
    def wrapper(self, *args, **kwargs):
        if not self.virtual_authenticator_id:
            raise ValueError("This function requires a virtual authenticator to be set.")
        return func(self, *args, **kwargs)

    return wrapper

# === NexusCore/openenv\Lib\site-packages\PIL\ImageQt.py ===
#
# The Python Imaging Library.
# $Id$
#
# a simple Qt image interface.
#
# history:
# 2006-06-03 fl: created
# 2006-06-04 fl: inherit from QImage instead of wrapping it
# 2006-06-05 fl: removed toimage helper; move string support to ImageQt
# 2013-11-13 fl: add support for Qt5 (aurelien.ballier@cyclonit.com)
#
# Copyright (c) 2006 by Secret Labs AB
# Copyright (c) 2006 by Fredrik Lundh
#
# See the README file for information on usage and redistribution.
#
from __future__ import annotations

import sys
from io import BytesIO
from typing import Any, Callable, Union

from . import Image
from ._util import is_path

TYPE_CHECKING = False
if TYPE_CHECKING:
    import PyQt6
    import PySide6

    from . import ImageFile

    QBuffer: type
    QByteArray = Union[PyQt6.QtCore.QByteArray, PySide6.QtCore.QByteArray]
    QIODevice = Union[PyQt6.QtCore.QIODevice, PySide6.QtCore.QIODevice]
    QImage = Union[PyQt6.QtGui.QImage, PySide6.QtGui.QImage]
    QPixmap = Union[PyQt6.QtGui.QPixmap, PySide6.QtGui.QPixmap]

qt_version: str | None
qt_versions = [
    ["6", "PyQt6"],
    ["side6", "PySide6"],
]

# If a version has already been imported, attempt it first
qt_versions.sort(key=lambda version: version[1] in sys.modules, reverse=True)
for version, qt_module in qt_versions:
    try:
        qRgba: Callable[[int, int, int, int], int]
        if qt_module == "PyQt6":
            from PyQt6.QtCore import QBuffer, QIODevice
            from PyQt6.QtGui import QImage, QPixmap, qRgba
        elif qt_module == "PySide6":
            from PySide6.QtCore import QBuffer, QIODevice
            from PySide6.QtGui import QImage, QPixmap, qRgba
    except (ImportError, RuntimeError):
        continue
    qt_is_installed = True
    qt_version = version
    break
else:
    qt_is_installed = False
    qt_version = None


def rgb(r: int, g: int, b: int, a: int = 255) -> int:
    """(Internal) Turns an RGB color into a Qt compatible color integer."""
    # use qRgb to pack the colors, and then turn the resulting long
    # into a negative integer with the same bitpattern.
    return qRgba(r, g, b, a) & 0xFFFFFFFF


def fromqimage(im: QImage | QPixmap) -> ImageFile.ImageFile:
    """
    :param im: QImage or PIL ImageQt object
    """
    buffer = QBuffer()
    qt_openmode: object
    if qt_version == "6":
        try:
            qt_openmode = getattr(QIODevice, "OpenModeFlag")
        except AttributeError:
            qt_openmode = getattr(QIODevice, "OpenMode")
    else:
        qt_openmode = QIODevice
    buffer.open(getattr(qt_openmode, "ReadWrite"))
    # preserve alpha channel with png
    # otherwise ppm is more friendly with Image.open
    if im.hasAlphaChannel():
        im.save(buffer, "png")
    else:
        im.save(buffer, "ppm")

    b = BytesIO()
    b.write(buffer.data())
    buffer.close()
    b.seek(0)

    return Image.open(b)


def fromqpixmap(im: QPixmap) -> ImageFile.ImageFile:
    return fromqimage(im)


def align8to32(bytes: bytes, width: int, mode: str) -> bytes:
    """
    converts each scanline of data from 8 bit to 32 bit aligned
    """

    bits_per_pixel = {"1": 1, "L": 8, "P": 8, "I;16": 16}[mode]

    # calculate bytes per line and the extra padding if needed
    bits_per_line = bits_per_pixel * width
    full_bytes_per_line, remaining_bits_per_line = divmod(bits_per_line, 8)
    bytes_per_line = full_bytes_per_line + (1 if remaining_bits_per_line else 0)

    extra_padding = -bytes_per_line % 4

    # already 32 bit aligned by luck
    if not extra_padding:
        return bytes

    new_data = [
        bytes[i * bytes_per_line : (i + 1) * bytes_per_line] + b"\x00" * extra_padding
        for i in range(len(bytes) // bytes_per_line)
    ]

    return b"".join(new_data)


def _toqclass_helper(im: Image.Image | str | QByteArray) -> dict[str, Any]:
    data = None
    colortable = None
    exclusive_fp = False

    # handle filename, if given instead of image name
    if hasattr(im, "toUtf8"):
        # FIXME - is this really the best way to do this?
        im = str(im.toUtf8(), "utf-8")
    if is_path(im):
        im = Image.open(im)
        exclusive_fp = True
    assert isinstance(im, Image.Image)

    qt_format = getattr(QImage, "Format") if qt_version == "6" else QImage
    if im.mode == "1":
        format = getattr(qt_format, "Format_Mono")
    elif im.mode == "L":
        format = getattr(qt_format, "Format_Indexed8")
        colortable = [rgb(i, i, i) for i in range(256)]
    elif im.mode == "P":
        format = getattr(qt_format, "Format_Indexed8")
        palette = im.getpalette()
        assert palette is not None
        colortable = [rgb(*palette[i : i + 3]) for i in range(0, len(palette), 3)]
    elif im.mode == "RGB":
        # Populate the 4th channel with 255
        im = im.convert("RGBA")

        data = im.tobytes("raw", "BGRA")
        format = getattr(qt_format, "Format_RGB32")
    elif im.mode == "RGBA":
        data = im.tobytes("raw", "BGRA")
        format = getattr(qt_format, "Format_ARGB32")
    elif im.mode == "I;16":
        im = im.point(lambda i: i * 256)

        format = getattr(qt_format, "Format_Grayscale16")
    else:
        if exclusive_fp:
            im.close()
        msg = f"unsupported image mode {repr(im.mode)}"
        raise ValueError(msg)

    size = im.size
    __data = data or align8to32(im.tobytes(), size[0], im.mode)
    if exclusive_fp:
        im.close()
    return {"data": __data, "size": size, "format": format, "colortable": colortable}


if qt_is_installed:

    class ImageQt(QImage):  # type: ignore[misc]
        def __init__(self, im: Image.Image | str | QByteArray) -> None:
            """
            An PIL image wrapper for Qt.  This is a subclass of PyQt's QImage
            class.

            :param im: A PIL Image object, or a file name (given either as
                Python string or a PyQt string object).
            """
            im_data = _toqclass_helper(im)
            # must keep a reference, or Qt will crash!
            # All QImage constructors that take data operate on an existing
            # buffer, so this buffer has to hang on for the life of the image.
            # Fixes https://github.com/python-pillow/Pillow/issues/1370
            self.__data = im_data["data"]
            super().__init__(
                self.__data,
                im_data["size"][0],
                im_data["size"][1],
                im_data["format"],
            )
            if im_data["colortable"]:
                self.setColorTable(im_data["colortable"])


def toqimage(im: Image.Image | str | QByteArray) -> ImageQt:
    return ImageQt(im)


def toqpixmap(im: Image.Image | str | QByteArray) -> QPixmap:
    qimage = toqimage(im)
    pixmap = getattr(QPixmap, "fromImage")(qimage)
    if qt_version == "6":
        pixmap.detach()
    return pixmap

# === NexusCore/openenv\Lib\site-packages\debugpy\_vendored\pydevd\_pydev_bundle\pydev_monkey_qt.py ===
from __future__ import nested_scopes

from _pydev_bundle._pydev_saved_modules import threading
import os
from _pydev_bundle import pydev_log


def set_trace_in_qt():
    from _pydevd_bundle.pydevd_comm import get_global_debugger

    py_db = get_global_debugger()
    if py_db is not None:
        threading.current_thread()  # Create the dummy thread for qt.
        py_db.enable_tracing()


_patched_qt = False


def patch_qt(qt_support_mode):
    """
    This method patches qt (PySide2, PySide, PyQt4, PyQt5) so that we have hooks to set the tracing for QThread.
    """
    if not qt_support_mode:
        return

    if qt_support_mode is True or qt_support_mode == "True":
        # do not break backward compatibility
        qt_support_mode = "auto"

    if qt_support_mode == "auto":
        qt_support_mode = os.getenv("PYDEVD_PYQT_MODE", "auto")

    # Avoid patching more than once
    global _patched_qt
    if _patched_qt:
        return

    pydev_log.debug("Qt support mode: %s", qt_support_mode)

    _patched_qt = True

    if qt_support_mode == "auto":
        patch_qt_on_import = None
        try:
            import PySide2  # @UnresolvedImport @UnusedImport

            qt_support_mode = "pyside2"
        except:
            try:
                import Pyside  # @UnresolvedImport @UnusedImport

                qt_support_mode = "pyside"
            except:
                try:
                    import PyQt5  # @UnresolvedImport @UnusedImport

                    qt_support_mode = "pyqt5"
                except:
                    try:
                        import PyQt4  # @UnresolvedImport @UnusedImport

                        qt_support_mode = "pyqt4"
                    except:
                        return

    if qt_support_mode == "pyside2":
        try:
            import PySide2.QtCore  # @UnresolvedImport

            _internal_patch_qt(PySide2.QtCore, qt_support_mode)
        except:
            return

    elif qt_support_mode == "pyside":
        try:
            import PySide.QtCore  # @UnresolvedImport

            _internal_patch_qt(PySide.QtCore, qt_support_mode)
        except:
            return

    elif qt_support_mode == "pyqt5":
        try:
            import PyQt5.QtCore  # @UnresolvedImport

            _internal_patch_qt(PyQt5.QtCore)
        except:
            return

    elif qt_support_mode == "pyqt4":
        # Ok, we have an issue here:
        # PyDev-452: Selecting PyQT API version using sip.setapi fails in debug mode
        # http://pyqt.sourceforge.net/Docs/PyQt4/incompatible_apis.html
        # Mostly, if the user uses a different API version (i.e.: v2 instead of v1),
        # that has to be done before importing PyQt4 modules (PySide/PyQt5 don't have this issue
        # as they only implements v2).
        patch_qt_on_import = "PyQt4"

        def get_qt_core_module():
            import PyQt4.QtCore  # @UnresolvedImport

            return PyQt4.QtCore

        _patch_import_to_patch_pyqt_on_import(patch_qt_on_import, get_qt_core_module)

    else:
        raise ValueError("Unexpected qt support mode: %s" % (qt_support_mode,))


def _patch_import_to_patch_pyqt_on_import(patch_qt_on_import, get_qt_core_module):
    # I don't like this approach very much as we have to patch __import__, but I like even less
    # asking the user to configure something in the client side...
    # So, our approach is to patch PyQt4 right before the user tries to import it (at which
    # point he should've set the sip api version properly already anyways).

    pydev_log.debug("Setting up Qt post-import monkeypatch.")

    dotted = patch_qt_on_import + "."
    original_import = __import__

    from _pydev_bundle._pydev_sys_patch import patch_sys_module, patch_reload, cancel_patches_in_sys_module

    patch_sys_module()
    patch_reload()

    def patched_import(name, *args, **kwargs):
        if patch_qt_on_import == name or name.startswith(dotted):
            builtins.__import__ = original_import
            cancel_patches_in_sys_module()
            _internal_patch_qt(get_qt_core_module())  # Patch it only when the user would import the qt module
        return original_import(name, *args, **kwargs)

    import builtins  # Py3

    builtins.__import__ = patched_import


def _internal_patch_qt(QtCore, qt_support_mode="auto"):
    pydev_log.debug("Patching Qt: %s", QtCore)

    _original_thread_init = QtCore.QThread.__init__
    _original_runnable_init = QtCore.QRunnable.__init__
    _original_QThread = QtCore.QThread

    class FuncWrapper:
        def __init__(self, original):
            self._original = original

        def __call__(self, *args, **kwargs):
            set_trace_in_qt()
            return self._original(*args, **kwargs)

    class StartedSignalWrapper(QtCore.QObject):  # Wrapper for the QThread.started signal
        try:
            _signal = QtCore.Signal()  # @UndefinedVariable
        except:
            _signal = QtCore.pyqtSignal()  # @UndefinedVariable

        def __init__(self, thread, original_started):
            QtCore.QObject.__init__(self)
            self.thread = thread
            self.original_started = original_started
            if qt_support_mode in ("pyside", "pyside2"):
                self._signal = original_started
            else:
                self._signal.connect(self._on_call)
                self.original_started.connect(self._signal)

        def connect(self, func, *args, **kwargs):
            if qt_support_mode in ("pyside", "pyside2"):
                return self._signal.connect(FuncWrapper(func), *args, **kwargs)
            else:
                return self._signal.connect(func, *args, **kwargs)

        def disconnect(self, *args, **kwargs):
            return self._signal.disconnect(*args, **kwargs)

        def emit(self, *args, **kwargs):
            return self._signal.emit(*args, **kwargs)

        def _on_call(self, *args, **kwargs):
            set_trace_in_qt()

    class ThreadWrapper(QtCore.QThread):  # Wrapper for QThread
        def __init__(self, *args, **kwargs):
            _original_thread_init(self, *args, **kwargs)

            # In PyQt5 the program hangs when we try to call original run method of QThread class.
            # So we need to distinguish instances of QThread class and instances of QThread inheritors.
            if self.__class__.run == _original_QThread.run:
                self.run = self._exec_run
            else:
                self._original_run = self.run
                self.run = self._new_run
            self._original_started = self.started
            self.started = StartedSignalWrapper(self, self.started)

        def _exec_run(self):
            set_trace_in_qt()
            self.exec_()
            return None

        def _new_run(self):
            set_trace_in_qt()
            return self._original_run()

    class RunnableWrapper(QtCore.QRunnable):  # Wrapper for QRunnable
        def __init__(self, *args, **kwargs):
            _original_runnable_init(self, *args, **kwargs)

            self._original_run = self.run
            self.run = self._new_run

        def _new_run(self):
            set_trace_in_qt()
            return self._original_run()

    QtCore.QThread = ThreadWrapper
    QtCore.QRunnable = RunnableWrapper

# === NexusCore/openenv\Lib\site-packages\google\ai\generativelanguage_v1beta\types\permission_service.py ===
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

from google.protobuf import field_mask_pb2  # type: ignore
import proto  # type: ignore

from google.ai.generativelanguage_v1beta.types import permission as gag_permission

__protobuf__ = proto.module(
    package="google.ai.generativelanguage.v1beta",
    manifest={
        "CreatePermissionRequest",
        "GetPermissionRequest",
        "ListPermissionsRequest",
        "ListPermissionsResponse",
        "UpdatePermissionRequest",
        "DeletePermissionRequest",
        "TransferOwnershipRequest",
        "TransferOwnershipResponse",
    },
)


class CreatePermissionRequest(proto.Message):
    r"""Request to create a ``Permission``.

    Attributes:
        parent (str):
            Required. The parent resource of the ``Permission``.
            Formats: ``tunedModels/{tuned_model}`` ``corpora/{corpus}``
        permission (google.ai.generativelanguage_v1beta.types.Permission):
            Required. The permission to create.
    """

    parent: str = proto.Field(
        proto.STRING,
        number=1,
    )
    permission: gag_permission.Permission = proto.Field(
        proto.MESSAGE,
        number=2,
        message=gag_permission.Permission,
    )


class GetPermissionRequest(proto.Message):
    r"""Request for getting information about a specific ``Permission``.

    Attributes:
        name (str):
            Required. The resource name of the permission.

            Formats:
            ``tunedModels/{tuned_model}/permissions/{permission}``
            ``corpora/{corpus}/permissions/{permission}``
    """

    name: str = proto.Field(
        proto.STRING,
        number=1,
    )


class ListPermissionsRequest(proto.Message):
    r"""Request for listing permissions.

    Attributes:
        parent (str):
            Required. The parent resource of the permissions. Formats:
            ``tunedModels/{tuned_model}`` ``corpora/{corpus}``
        page_size (int):
            Optional. The maximum number of ``Permission``\ s to return
            (per page). The service may return fewer permissions.

            If unspecified, at most 10 permissions will be returned.
            This method returns at most 1000 permissions per page, even
            if you pass larger page_size.
        page_token (str):
            Optional. A page token, received from a previous
            ``ListPermissions`` call.

            Provide the ``page_token`` returned by one request as an
            argument to the next request to retrieve the next page.

            When paginating, all other parameters provided to
            ``ListPermissions`` must match the call that provided the
            page token.
    """

    parent: str = proto.Field(
        proto.STRING,
        number=1,
    )
    page_size: int = proto.Field(
        proto.INT32,
        number=2,
    )
    page_token: str = proto.Field(
        proto.STRING,
        number=3,
    )


class ListPermissionsResponse(proto.Message):
    r"""Response from ``ListPermissions`` containing a paginated list of
    permissions.

    Attributes:
        permissions (MutableSequence[google.ai.generativelanguage_v1beta.types.Permission]):
            Returned permissions.
        next_page_token (str):
            A token, which can be sent as ``page_token`` to retrieve the
            next page.

            If this field is omitted, there are no more pages.
    """

    @property
    def raw_page(self):
        return self

    permissions: MutableSequence[gag_permission.Permission] = proto.RepeatedField(
        proto.MESSAGE,
        number=1,
        message=gag_permission.Permission,
    )
    next_page_token: str = proto.Field(
        proto.STRING,
        number=2,
    )


class UpdatePermissionRequest(proto.Message):
    r"""Request to update the ``Permission``.

    Attributes:
        permission (google.ai.generativelanguage_v1beta.types.Permission):
            Required. The permission to update.

            The permission's ``name`` field is used to identify the
            permission to update.
        update_mask (google.protobuf.field_mask_pb2.FieldMask):
            Required. The list of fields to update. Accepted ones:

            -  role (``Permission.role`` field)
    """

    permission: gag_permission.Permission = proto.Field(
        proto.MESSAGE,
        number=1,
        message=gag_permission.Permission,
    )
    update_mask: field_mask_pb2.FieldMask = proto.Field(
        proto.MESSAGE,
        number=2,
        message=field_mask_pb2.FieldMask,
    )


class DeletePermissionRequest(proto.Message):
    r"""Request to delete the ``Permission``.

    Attributes:
        name (str):
            Required. The resource name of the permission. Formats:
            ``tunedModels/{tuned_model}/permissions/{permission}``
            ``corpora/{corpus}/permissions/{permission}``
    """

    name: str = proto.Field(
        proto.STRING,
        number=1,
    )


class TransferOwnershipRequest(proto.Message):
    r"""Request to transfer the ownership of the tuned model.

    Attributes:
        name (str):
            Required. The resource name of the tuned model to transfer
            ownership.

            Format: ``tunedModels/my-model-id``
        email_address (str):
            Required. The email address of the user to
            whom the tuned model is being transferred to.
    """

    name: str = proto.Field(
        proto.STRING,
        number=1,
    )
    email_address: str = proto.Field(
        proto.STRING,
        number=2,
    )


class TransferOwnershipResponse(proto.Message):
    r"""Response from ``TransferOwnership``."""


__all__ = tuple(sorted(__protobuf__.manifest))

# === NexusCore/openenv\Lib\site-packages\jedi\inference\star_args.py ===
"""
This module is responsible for inferring *args and **kwargs for signatures.

This means for example in this case::

    def foo(a, b, c): ...

    def bar(*args):
        return foo(1, *args)

The signature here for bar should be `bar(b, c)` instead of bar(*args).
"""
from inspect import Parameter

from parso import tree

from jedi.inference.utils import to_list
from jedi.inference.names import ParamNameWrapper
from jedi.inference.helpers import is_big_annoying_library


def _iter_nodes_for_param(param_name):
    from parso.python.tree import search_ancestor
    from jedi.inference.arguments import TreeArguments

    execution_context = param_name.parent_context
    # Walk up the parso tree to get the FunctionNode we want. We use the parso
    # tree rather than going via the execution context so that we're agnostic of
    # the specific scope we're evaluating within (i.e: module or function,
    # etc.).
    function_node = tree.search_ancestor(param_name.tree_name, 'funcdef', 'lambdef')
    module_node = function_node.get_root_node()
    start = function_node.children[-1].start_pos
    end = function_node.children[-1].end_pos
    for name in module_node.get_used_names().get(param_name.string_name):
        if start <= name.start_pos < end:
            # Is used in the function
            argument = name.parent
            if argument.type == 'argument' \
                    and argument.children[0] == '*' * param_name.star_count:
                trailer = search_ancestor(argument, 'trailer')
                if trailer is not None:  # Make sure we're in a function
                    context = execution_context.create_context(trailer)
                    if _goes_to_param_name(param_name, context, name):
                        values = _to_callables(context, trailer)

                        args = TreeArguments.create_cached(
                            execution_context.inference_state,
                            context=context,
                            argument_node=trailer.children[1],
                            trailer=trailer,
                        )
                        for c in values:
                            yield c, args


def _goes_to_param_name(param_name, context, potential_name):
    if potential_name.type != 'name':
        return False
    from jedi.inference.names import TreeNameDefinition
    found = TreeNameDefinition(context, potential_name).goto()
    return any(param_name.parent_context == p.parent_context
               and param_name.start_pos == p.start_pos
               for p in found)


def _to_callables(context, trailer):
    from jedi.inference.syntax_tree import infer_trailer

    atom_expr = trailer.parent
    index = atom_expr.children[0] == 'await'
    # Infer atom first
    values = context.infer_node(atom_expr.children[index])
    for trailer2 in atom_expr.children[index + 1:]:
        if trailer == trailer2:
            break
        values = infer_trailer(context, values, trailer2)
    return values


def _remove_given_params(arguments, param_names):
    count = 0
    used_keys = set()
    for key, _ in arguments.unpack():
        if key is None:
            count += 1
        else:
            used_keys.add(key)

    for p in param_names:
        if count and p.maybe_positional_argument():
            count -= 1
            continue
        if p.string_name in used_keys and p.maybe_keyword_argument():
            continue
        yield p


@to_list
def process_params(param_names, star_count=3):  # default means both * and **
    if param_names:
        if is_big_annoying_library(param_names[0].parent_context):
            # At first this feature can look innocent, but it does a lot of
            # type inference in some cases, so we just ditch it.
            yield from param_names
            return

    used_names = set()
    arg_callables = []
    kwarg_callables = []

    kw_only_names = []
    kwarg_names = []
    arg_names = []
    original_arg_name = None
    original_kwarg_name = None
    for p in param_names:
        kind = p.get_kind()
        if kind == Parameter.VAR_POSITIONAL:
            if star_count & 1:
                arg_callables = _iter_nodes_for_param(p)
                original_arg_name = p
        elif p.get_kind() == Parameter.VAR_KEYWORD:
            if star_count & 2:
                kwarg_callables = list(_iter_nodes_for_param(p))
                original_kwarg_name = p
        elif kind == Parameter.KEYWORD_ONLY:
            if star_count & 2:
                kw_only_names.append(p)
        elif kind == Parameter.POSITIONAL_ONLY:
            if star_count & 1:
                yield p
        else:
            if star_count == 1:
                yield ParamNameFixedKind(p, Parameter.POSITIONAL_ONLY)
            elif star_count == 2:
                kw_only_names.append(ParamNameFixedKind(p, Parameter.KEYWORD_ONLY))
            else:
                used_names.add(p.string_name)
                yield p

    # First process *args
    longest_param_names = ()
    found_arg_signature = False
    found_kwarg_signature = False
    for func_and_argument in arg_callables:
        func, arguments = func_and_argument
        new_star_count = star_count
        if func_and_argument in kwarg_callables:
            kwarg_callables.remove(func_and_argument)
        else:
            new_star_count = 1

        for signature in func.get_signatures():
            found_arg_signature = True
            if new_star_count == 3:
                found_kwarg_signature = True
            args_for_this_func = []
            for p in process_params(
                    list(_remove_given_params(
                        arguments,
                        signature.get_param_names(resolve_stars=False)
                    )), new_star_count):
                if p.get_kind() == Parameter.VAR_KEYWORD:
                    kwarg_names.append(p)
                elif p.get_kind() == Parameter.VAR_POSITIONAL:
                    arg_names.append(p)
                elif p.get_kind() == Parameter.KEYWORD_ONLY:
                    kw_only_names.append(p)
                else:
                    args_for_this_func.append(p)
            if len(args_for_this_func) > len(longest_param_names):
                longest_param_names = args_for_this_func

    for p in longest_param_names:
        if star_count == 1 and p.get_kind() != Parameter.VAR_POSITIONAL:
            yield ParamNameFixedKind(p, Parameter.POSITIONAL_ONLY)
        else:
            if p.get_kind() == Parameter.POSITIONAL_OR_KEYWORD:
                used_names.add(p.string_name)
            yield p

    if not found_arg_signature and original_arg_name is not None:
        yield original_arg_name
    elif arg_names:
        yield arg_names[0]

    # Then process **kwargs
    for func, arguments in kwarg_callables:
        for signature in func.get_signatures():
            found_kwarg_signature = True
            for p in process_params(
                    list(_remove_given_params(
                        arguments,
                        signature.get_param_names(resolve_stars=False)
                    )), star_count=2):
                if p.get_kind() == Parameter.VAR_KEYWORD:
                    kwarg_names.append(p)
                elif p.get_kind() == Parameter.KEYWORD_ONLY:
                    kw_only_names.append(p)

    for p in kw_only_names:
        if p.string_name in used_names:
            continue
        yield p
        used_names.add(p.string_name)

    if not found_kwarg_signature and original_kwarg_name is not None:
        yield original_kwarg_name
    elif kwarg_names:
        yield kwarg_names[0]


class ParamNameFixedKind(ParamNameWrapper):
    def __init__(self, param_name, new_kind):
        super().__init__(param_name)
        self._new_kind = new_kind

    def get_kind(self):
        return self._new_kind

# === NexusCore/openenv\Lib\site-packages\litellm\proxy\common_utils\html_forms\ui_login.py ===
import os

url_to_redirect_to = os.getenv("PROXY_BASE_URL", "")
server_root_path = os.getenv("SERVER_ROOT_PATH", "")
if server_root_path != "":
    url_to_redirect_to += server_root_path
url_to_redirect_to += "/login"
html_form = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>LiteLLM Login</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            background-color: #f8fafc;
            margin: 0;
            padding: 20px;
            display: flex;
            justify-content: center;
            align-items: center;
            min-height: 100vh;
            color: #333;
        }}

        form {{
            background-color: #fff;
            padding: 40px;
            border-radius: 8px;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
            width: 450px;
            max-width: 100%;
        }}
        
        .logo-container {{
            text-align: center;
            margin-bottom: 30px;
        }}
        
        .logo {{
            font-size: 24px;
            font-weight: 600;
            color: #1e293b;
        }}
        
        h2 {{
            margin: 0 0 10px;
            color: #1e293b;
            font-size: 28px;
            font-weight: 600;
            text-align: center;
        }}
        
        .subtitle {{
            color: #64748b;
            margin: 0 0 20px;
            font-size: 16px;
            text-align: center;
        }}

        .info-box {{
            background-color: #f1f5f9;
            border-radius: 6px;
            padding: 20px;
            margin-bottom: 30px;
            border-left: 4px solid #2563eb;
        }}
        
        .info-header {{
            display: flex;
            align-items: center;
            margin-bottom: 12px;
            color: #1e40af;
            font-weight: 600;
            font-size: 16px;
        }}
        
        .info-header svg {{
            margin-right: 8px;
        }}
        
        .info-box p {{
            color: #475569;
            margin: 8px 0;
            line-height: 1.5;
            font-size: 14px;
        }}

        label {{
            display: block;
            margin-bottom: 8px;
            font-weight: 500;
            color: #334155;
            font-size: 14px;
        }}
        
        .required {{
            color: #dc2626;
            margin-left: 2px;
        }}

        input[type="text"],
        input[type="password"] {{
            width: 100%;
            padding: 10px 14px;
            margin-bottom: 20px;
            box-sizing: border-box;
            border: 1px solid #e2e8f0;
            border-radius: 6px;
            font-size: 15px;
            color: #1e293b;
            background-color: #fff;
            transition: border-color 0.2s, box-shadow 0.2s;
        }}
        
        input[type="text"]:focus,
        input[type="password"]:focus {{
            outline: none;
            border-color: #3b82f6;
            box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.2);
        }}

        .toggle-password {{
            display: flex;
            align-items: center;
            margin-top: -15px;
            margin-bottom: 20px;
        }}
        
        .toggle-password input {{
            margin-right: 6px;
        }}

        input[type="submit"] {{
            background-color: #6466E9;
            color: #fff;
            cursor: pointer;
            font-weight: 500;
            border: none;
            padding: 10px 16px;
            transition: background-color 0.2s;
            border-radius: 6px;
            margin-top: 10px;
            font-size: 14px;
            width: 100%;
        }}

        input[type="submit"]:hover {{
            background-color: #4138C2;
        }}
        
        a {{
            color: #3b82f6;
            text-decoration: none;
        }}

        a:hover {{
            text-decoration: underline;
        }}
        
        code {{
            background-color: #f1f5f9;
            padding: 2px 4px;
            border-radius: 4px;
            font-family: monospace;
            font-size: 13px;
            color: #334155;
        }}
        
        .help-text {{
            color: #64748b;
            font-size: 14px;
            margin-top: -12px;
            margin-bottom: 20px;
        }}
    </style>
</head>
<body>
    <form action="{url_to_redirect_to}" method="post">
        <div class="logo-container">
            <div class="logo">
                🚅 LiteLLM
            </div>
        </div>
        <h2>Login</h2>
        <p class="subtitle">Access your LiteLLM Admin UI.</p>
        <div class="info-box">
            <div class="info-header">
                <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <circle cx="12" cy="12" r="10"></circle>
                    <line x1="12" y1="16" x2="12" y2="12"></line>
                    <line x1="12" y1="8" x2="12.01" y2="8"></line>
                </svg>
                Default Credentials
            </div>
            <p>By default, Username is <code>admin</code> and Password is your set LiteLLM Proxy <code>MASTER_KEY</code>.</p>
            <p>Need to set UI credentials or SSO? <a href="https://docs.litellm.ai/docs/proxy/ui" target="_blank">Check the documentation</a>.</p>
        </div>
        <label for="username">Username<span class="required">*</span></label>
        <input type="text" id="username" name="username" required placeholder="Enter your username" autocomplete="username">
        
        <label for="password">Password<span class="required">*</span></label>
        <input type="password" id="password" name="password" required placeholder="Enter your password" autocomplete="current-password">
        <div class="toggle-password">
            <input type="checkbox" id="show-password" onclick="togglePasswordVisibility()">
            <label for="show-password">Show password</label>
        </div>
        <input type="submit" value="Login">
    </form>
    <script>
        function togglePasswordVisibility() {{
            var passwordField = document.getElementById("password");
            passwordField.type = passwordField.type === "password" ? "text" : "password";
        }}
    </script>
</body>
</html>
"""

# === NexusCore/openenv\Lib\site-packages\nltk\tokenize\regexp.py ===
# Natural Language Toolkit: Tokenizers
#
# Copyright (C) 2001-2024 NLTK Project
# Author: Edward Loper <edloper@gmail.com>
#         Steven Bird <stevenbird1@gmail.com>
#         Trevor Cohn <tacohn@csse.unimelb.edu.au>
# URL: <https://www.nltk.org>
# For license information, see LICENSE.TXT

r"""
Regular-Expression Tokenizers

A ``RegexpTokenizer`` splits a string into substrings using a regular expression.
For example, the following tokenizer forms tokens out of alphabetic sequences,
money expressions, and any other non-whitespace sequences:

    >>> from nltk.tokenize import RegexpTokenizer
    >>> s = "Good muffins cost $3.88\nin New York.  Please buy me\ntwo of them.\n\nThanks."
    >>> tokenizer = RegexpTokenizer(r'\w+|\$[\d\.]+|\S+')
    >>> tokenizer.tokenize(s) # doctest: +NORMALIZE_WHITESPACE
    ['Good', 'muffins', 'cost', '$3.88', 'in', 'New', 'York', '.',
    'Please', 'buy', 'me', 'two', 'of', 'them', '.', 'Thanks', '.']

A ``RegexpTokenizer`` can use its regexp to match delimiters instead:

    >>> tokenizer = RegexpTokenizer(r'\s+', gaps=True)
    >>> tokenizer.tokenize(s) # doctest: +NORMALIZE_WHITESPACE
    ['Good', 'muffins', 'cost', '$3.88', 'in', 'New', 'York.',
    'Please', 'buy', 'me', 'two', 'of', 'them.', 'Thanks.']

Note that empty tokens are not returned when the delimiter appears at
the start or end of the string.

The material between the tokens is discarded.  For example,
the following tokenizer selects just the capitalized words:

    >>> capword_tokenizer = RegexpTokenizer(r'[A-Z]\w+')
    >>> capword_tokenizer.tokenize(s)
    ['Good', 'New', 'York', 'Please', 'Thanks']

This module contains several subclasses of ``RegexpTokenizer``
that use pre-defined regular expressions.

    >>> from nltk.tokenize import BlanklineTokenizer
    >>> # Uses '\s*\n\s*\n\s*':
    >>> BlanklineTokenizer().tokenize(s) # doctest: +NORMALIZE_WHITESPACE
    ['Good muffins cost $3.88\nin New York.  Please buy me\ntwo of them.',
    'Thanks.']

All of the regular expression tokenizers are also available as functions:

    >>> from nltk.tokenize import regexp_tokenize, wordpunct_tokenize, blankline_tokenize
    >>> regexp_tokenize(s, pattern=r'\w+|\$[\d\.]+|\S+') # doctest: +NORMALIZE_WHITESPACE
    ['Good', 'muffins', 'cost', '$3.88', 'in', 'New', 'York', '.',
    'Please', 'buy', 'me', 'two', 'of', 'them', '.', 'Thanks', '.']
    >>> wordpunct_tokenize(s) # doctest: +NORMALIZE_WHITESPACE
    ['Good', 'muffins', 'cost', '$', '3', '.', '88', 'in', 'New', 'York',
     '.', 'Please', 'buy', 'me', 'two', 'of', 'them', '.', 'Thanks', '.']
    >>> blankline_tokenize(s)
    ['Good muffins cost $3.88\nin New York.  Please buy me\ntwo of them.', 'Thanks.']

Caution: The function ``regexp_tokenize()`` takes the text as its
first argument, and the regular expression pattern as its second
argument.  This differs from the conventions used by Python's
``re`` functions, where the pattern is always the first argument.
(This is for consistency with the other NLTK tokenizers.)
"""

import re

from nltk.tokenize.api import TokenizerI
from nltk.tokenize.util import regexp_span_tokenize


class RegexpTokenizer(TokenizerI):
    r"""
    A tokenizer that splits a string using a regular expression, which
    matches either the tokens or the separators between tokens.

        >>> tokenizer = RegexpTokenizer(r'\w+|\$[\d\.]+|\S+')

    :type pattern: str
    :param pattern: The pattern used to build this tokenizer.
        (This pattern must not contain capturing parentheses;
        Use non-capturing parentheses, e.g. (?:...), instead)
    :type gaps: bool
    :param gaps: True if this tokenizer's pattern should be used
        to find separators between tokens; False if this
        tokenizer's pattern should be used to find the tokens
        themselves.
    :type discard_empty: bool
    :param discard_empty: True if any empty tokens `''`
        generated by the tokenizer should be discarded.  Empty
        tokens can only be generated if `_gaps == True`.
    :type flags: int
    :param flags: The regexp flags used to compile this
        tokenizer's pattern.  By default, the following flags are
        used: `re.UNICODE | re.MULTILINE | re.DOTALL`.

    """

    def __init__(
        self,
        pattern,
        gaps=False,
        discard_empty=True,
        flags=re.UNICODE | re.MULTILINE | re.DOTALL,
    ):
        # If they gave us a regexp object, extract the pattern.
        pattern = getattr(pattern, "pattern", pattern)

        self._pattern = pattern
        self._gaps = gaps
        self._discard_empty = discard_empty
        self._flags = flags
        self._regexp = None

    def _check_regexp(self):
        if self._regexp is None:
            self._regexp = re.compile(self._pattern, self._flags)

    def tokenize(self, text):
        self._check_regexp()
        # If our regexp matches gaps, use re.split:
        if self._gaps:
            if self._discard_empty:
                return [tok for tok in self._regexp.split(text) if tok]
            else:
                return self._regexp.split(text)

        # If our regexp matches tokens, use re.findall:
        else:
            return self._regexp.findall(text)

    def span_tokenize(self, text):
        self._check_regexp()

        if self._gaps:
            for left, right in regexp_span_tokenize(text, self._regexp):
                if not (self._discard_empty and left == right):
                    yield left, right
        else:
            for m in re.finditer(self._regexp, text):
                yield m.span()

    def __repr__(self):
        return "{}(pattern={!r}, gaps={!r}, discard_empty={!r}, flags={!r})".format(
            self.__class__.__name__,
            self._pattern,
            self._gaps,
            self._discard_empty,
            self._flags,
        )


class WhitespaceTokenizer(RegexpTokenizer):
    r"""
    Tokenize a string on whitespace (space, tab, newline).
    In general, users should use the string ``split()`` method instead.

        >>> from nltk.tokenize import WhitespaceTokenizer
        >>> s = "Good muffins cost $3.88\nin New York.  Please buy me\ntwo of them.\n\nThanks."
        >>> WhitespaceTokenizer().tokenize(s) # doctest: +NORMALIZE_WHITESPACE
        ['Good', 'muffins', 'cost', '$3.88', 'in', 'New', 'York.',
        'Please', 'buy', 'me', 'two', 'of', 'them.', 'Thanks.']
    """

    def __init__(self):
        RegexpTokenizer.__init__(self, r"\s+", gaps=True)


class BlanklineTokenizer(RegexpTokenizer):
    """
    Tokenize a string, treating any sequence of blank lines as a delimiter.
    Blank lines are defined as lines containing no characters, except for
    space or tab characters.
    """

    def __init__(self):
        RegexpTokenizer.__init__(self, r"\s*\n\s*\n\s*", gaps=True)


class WordPunctTokenizer(RegexpTokenizer):
    r"""
    Tokenize a text into a sequence of alphabetic and
    non-alphabetic characters, using the regexp ``\w+|[^\w\s]+``.

        >>> from nltk.tokenize import WordPunctTokenizer
        >>> s = "Good muffins cost $3.88\nin New York.  Please buy me\ntwo of them.\n\nThanks."
        >>> WordPunctTokenizer().tokenize(s) # doctest: +NORMALIZE_WHITESPACE
        ['Good', 'muffins', 'cost', '$', '3', '.', '88', 'in', 'New', 'York',
        '.', 'Please', 'buy', 'me', 'two', 'of', 'them', '.', 'Thanks', '.']
    """

    def __init__(self):
        RegexpTokenizer.__init__(self, r"\w+|[^\w\s]+")


######################################################################
# { Tokenization Functions
######################################################################


def regexp_tokenize(
    text,
    pattern,
    gaps=False,
    discard_empty=True,
    flags=re.UNICODE | re.MULTILINE | re.DOTALL,
):
    """
    Return a tokenized copy of *text*.  See :class:`.RegexpTokenizer`
    for descriptions of the arguments.
    """
    tokenizer = RegexpTokenizer(pattern, gaps, discard_empty, flags)
    return tokenizer.tokenize(text)


blankline_tokenize = BlanklineTokenizer().tokenize
wordpunct_tokenize = WordPunctTokenizer().tokenize

# === NexusCore/openenv\Lib\site-packages\prompt_toolkit\layout\dimension.py ===
"""
Layout dimensions are used to give the minimum, maximum and preferred
dimensions for containers and controls.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Callable, Union

__all__ = [
    "Dimension",
    "D",
    "sum_layout_dimensions",
    "max_layout_dimensions",
    "AnyDimension",
    "to_dimension",
    "is_dimension",
]

if TYPE_CHECKING:
    from typing_extensions import TypeGuard


class Dimension:
    """
    Specified dimension (width/height) of a user control or window.

    The layout engine tries to honor the preferred size. If that is not
    possible, because the terminal is larger or smaller, it tries to keep in
    between min and max.

    :param min: Minimum size.
    :param max: Maximum size.
    :param weight: For a VSplit/HSplit, the actual size will be determined
                   by taking the proportion of weights from all the children.
                   E.g. When there are two children, one with a weight of 1,
                   and the other with a weight of 2, the second will always be
                   twice as big as the first, if the min/max values allow it.
    :param preferred: Preferred size.
    """

    def __init__(
        self,
        min: int | None = None,
        max: int | None = None,
        weight: int | None = None,
        preferred: int | None = None,
    ) -> None:
        if weight is not None:
            assert weight >= 0  # Also cannot be a float.

        assert min is None or min >= 0
        assert max is None or max >= 0
        assert preferred is None or preferred >= 0

        self.min_specified = min is not None
        self.max_specified = max is not None
        self.preferred_specified = preferred is not None
        self.weight_specified = weight is not None

        if min is None:
            min = 0  # Smallest possible value.
        if max is None:  # 0-values are allowed, so use "is None"
            max = 1000**10  # Something huge.
        if preferred is None:
            preferred = min
        if weight is None:
            weight = 1

        self.min = min
        self.max = max
        self.preferred = preferred
        self.weight = weight

        # Don't allow situations where max < min. (This would be a bug.)
        if max < min:
            raise ValueError("Invalid Dimension: max < min.")

        # Make sure that the 'preferred' size is always in the min..max range.
        if self.preferred < self.min:
            self.preferred = self.min

        if self.preferred > self.max:
            self.preferred = self.max

    @classmethod
    def exact(cls, amount: int) -> Dimension:
        """
        Return a :class:`.Dimension` with an exact size. (min, max and
        preferred set to ``amount``).
        """
        return cls(min=amount, max=amount, preferred=amount)

    @classmethod
    def zero(cls) -> Dimension:
        """
        Create a dimension that represents a zero size. (Used for 'invisible'
        controls.)
        """
        return cls.exact(amount=0)

    def is_zero(self) -> bool:
        "True if this `Dimension` represents a zero size."
        return self.preferred == 0 or self.max == 0

    def __repr__(self) -> str:
        fields = []
        if self.min_specified:
            fields.append(f"min={self.min!r}")
        if self.max_specified:
            fields.append(f"max={self.max!r}")
        if self.preferred_specified:
            fields.append(f"preferred={self.preferred!r}")
        if self.weight_specified:
            fields.append(f"weight={self.weight!r}")

        return "Dimension({})".format(", ".join(fields))


def sum_layout_dimensions(dimensions: list[Dimension]) -> Dimension:
    """
    Sum a list of :class:`.Dimension` instances.
    """
    min = sum(d.min for d in dimensions)
    max = sum(d.max for d in dimensions)
    preferred = sum(d.preferred for d in dimensions)

    return Dimension(min=min, max=max, preferred=preferred)


def max_layout_dimensions(dimensions: list[Dimension]) -> Dimension:
    """
    Take the maximum of a list of :class:`.Dimension` instances.
    Used when we have a HSplit/VSplit, and we want to get the best width/height.)
    """
    if not len(dimensions):
        return Dimension.zero()

    # If all dimensions are size zero. Return zero.
    # (This is important for HSplit/VSplit, to report the right values to their
    # parent when all children are invisible.)
    if all(d.is_zero() for d in dimensions):
        return dimensions[0]

    # Ignore empty dimensions. (They should not reduce the size of others.)
    dimensions = [d for d in dimensions if not d.is_zero()]

    if dimensions:
        # Take the highest minimum dimension.
        min_ = max(d.min for d in dimensions)

        # For the maximum, we would prefer not to go larger than then smallest
        # 'max' value, unless other dimensions have a bigger preferred value.
        # This seems to work best:
        #  - We don't want that a widget with a small height in a VSplit would
        #    shrink other widgets in the split.
        # If it doesn't work well enough, then it's up to the UI designer to
        # explicitly pass dimensions.
        max_ = min(d.max for d in dimensions)
        max_ = max(max_, max(d.preferred for d in dimensions))

        # Make sure that min>=max. In some scenarios, when certain min..max
        # ranges don't have any overlap, we can end up in such an impossible
        # situation. In that case, give priority to the max value.
        # E.g. taking (1..5) and (8..9) would return (8..5). Instead take (8..8).
        if min_ > max_:
            max_ = min_

        preferred = max(d.preferred for d in dimensions)

        return Dimension(min=min_, max=max_, preferred=preferred)
    else:
        return Dimension()


# Anything that can be converted to a dimension.
AnyDimension = Union[
    None,  # None is a valid dimension that will fit anything.
    int,
    Dimension,
    # Callable[[], 'AnyDimension']  # Recursive definition not supported by mypy.
    Callable[[], Any],
]


def to_dimension(value: AnyDimension) -> Dimension:
    """
    Turn the given object into a `Dimension` object.
    """
    if value is None:
        return Dimension()
    if isinstance(value, int):
        return Dimension.exact(value)
    if isinstance(value, Dimension):
        return value
    if callable(value):
        return to_dimension(value())

    raise ValueError("Not an integer or Dimension object.")


def is_dimension(value: object) -> TypeGuard[AnyDimension]:
    """
    Test whether the given value could be a valid dimension.
    (For usage in an assertion. It's not guaranteed in case of a callable.)
    """
    if value is None:
        return True
    if callable(value):
        return True  # Assume it's a callable that doesn't take arguments.
    if isinstance(value, (int, Dimension)):
        return True
    return False


# Common alias.
D = Dimension

# For backward-compatibility.
LayoutDimension = Dimension

# === NexusCore/openenv\Lib\site-packages\selenium\webdriver\common\devtools\v135\dom_storage.py ===
# DO NOT EDIT THIS FILE!
#
# This file is generated from the CDP specification. If you need to make
# changes, edit the generator and regenerate all of the modules.
#
# CDP domain: DOMStorage (experimental)
from __future__ import annotations
from .util import event_class, T_JSON_DICT
from dataclasses import dataclass
import enum
import typing

class SerializedStorageKey(str):
    def to_json(self) -> str:
        return self

    @classmethod
    def from_json(cls, json: str) -> SerializedStorageKey:
        return cls(json)

    def __repr__(self):
        return 'SerializedStorageKey({})'.format(super().__repr__())


@dataclass
class StorageId:
    '''
    DOM Storage identifier.
    '''
    #: Whether the storage is local storage (not session storage).
    is_local_storage: bool

    #: Security origin for the storage.
    security_origin: typing.Optional[str] = None

    #: Represents a key by which DOM Storage keys its CachedStorageAreas
    storage_key: typing.Optional[SerializedStorageKey] = None

    def to_json(self):
        json = dict()
        json['isLocalStorage'] = self.is_local_storage
        if self.security_origin is not None:
            json['securityOrigin'] = self.security_origin
        if self.storage_key is not None:
            json['storageKey'] = self.storage_key.to_json()
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            is_local_storage=bool(json['isLocalStorage']),
            security_origin=str(json['securityOrigin']) if 'securityOrigin' in json else None,
            storage_key=SerializedStorageKey.from_json(json['storageKey']) if 'storageKey' in json else None,
        )


class Item(list):
    '''
    DOM Storage item.
    '''
    def to_json(self) -> typing.List[str]:
        return self

    @classmethod
    def from_json(cls, json: typing.List[str]) -> Item:
        return cls(json)

    def __repr__(self):
        return 'Item({})'.format(super().__repr__())


def clear(
        storage_id: StorageId
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    :param storage_id:
    '''
    params: T_JSON_DICT = dict()
    params['storageId'] = storage_id.to_json()
    cmd_dict: T_JSON_DICT = {
        'method': 'DOMStorage.clear',
        'params': params,
    }
    json = yield cmd_dict


def disable() -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Disables storage tracking, prevents storage events from being sent to the client.
    '''
    cmd_dict: T_JSON_DICT = {
        'method': 'DOMStorage.disable',
    }
    json = yield cmd_dict


def enable() -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Enables storage tracking, storage events will now be delivered to the client.
    '''
    cmd_dict: T_JSON_DICT = {
        'method': 'DOMStorage.enable',
    }
    json = yield cmd_dict


def get_dom_storage_items(
        storage_id: StorageId
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,typing.List[Item]]:
    '''
    :param storage_id:
    :returns: 
    '''
    params: T_JSON_DICT = dict()
    params['storageId'] = storage_id.to_json()
    cmd_dict: T_JSON_DICT = {
        'method': 'DOMStorage.getDOMStorageItems',
        'params': params,
    }
    json = yield cmd_dict
    return [Item.from_json(i) for i in json['entries']]


def remove_dom_storage_item(
        storage_id: StorageId,
        key: str
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    :param storage_id:
    :param key:
    '''
    params: T_JSON_DICT = dict()
    params['storageId'] = storage_id.to_json()
    params['key'] = key
    cmd_dict: T_JSON_DICT = {
        'method': 'DOMStorage.removeDOMStorageItem',
        'params': params,
    }
    json = yield cmd_dict


def set_dom_storage_item(
        storage_id: StorageId,
        key: str,
        value: str
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    :param storage_id:
    :param key:
    :param value:
    '''
    params: T_JSON_DICT = dict()
    params['storageId'] = storage_id.to_json()
    params['key'] = key
    params['value'] = value
    cmd_dict: T_JSON_DICT = {
        'method': 'DOMStorage.setDOMStorageItem',
        'params': params,
    }
    json = yield cmd_dict


@event_class('DOMStorage.domStorageItemAdded')
@dataclass
class DomStorageItemAdded:
    storage_id: StorageId
    key: str
    new_value: str

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> DomStorageItemAdded:
        return cls(
            storage_id=StorageId.from_json(json['storageId']),
            key=str(json['key']),
            new_value=str(json['newValue'])
        )


@event_class('DOMStorage.domStorageItemRemoved')
@dataclass
class DomStorageItemRemoved:
    storage_id: StorageId
    key: str

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> DomStorageItemRemoved:
        return cls(
            storage_id=StorageId.from_json(json['storageId']),
            key=str(json['key'])
        )


@event_class('DOMStorage.domStorageItemUpdated')
@dataclass
class DomStorageItemUpdated:
    storage_id: StorageId
    key: str
    old_value: str
    new_value: str

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> DomStorageItemUpdated:
        return cls(
            storage_id=StorageId.from_json(json['storageId']),
            key=str(json['key']),
            old_value=str(json['oldValue']),
            new_value=str(json['newValue'])
        )


@event_class('DOMStorage.domStorageItemsCleared')
@dataclass
class DomStorageItemsCleared:
    storage_id: StorageId

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> DomStorageItemsCleared:
        return cls(
            storage_id=StorageId.from_json(json['storageId'])
        )

# === NexusCore/openenv\Lib\site-packages\selenium\webdriver\common\devtools\v136\dom_storage.py ===
# DO NOT EDIT THIS FILE!
#
# This file is generated from the CDP specification. If you need to make
# changes, edit the generator and regenerate all of the modules.
#
# CDP domain: DOMStorage (experimental)
from __future__ import annotations
from .util import event_class, T_JSON_DICT
from dataclasses import dataclass
import enum
import typing

class SerializedStorageKey(str):
    def to_json(self) -> str:
        return self

    @classmethod
    def from_json(cls, json: str) -> SerializedStorageKey:
        return cls(json)

    def __repr__(self):
        return 'SerializedStorageKey({})'.format(super().__repr__())


@dataclass
class StorageId:
    '''
    DOM Storage identifier.
    '''
    #: Whether the storage is local storage (not session storage).
    is_local_storage: bool

    #: Security origin for the storage.
    security_origin: typing.Optional[str] = None

    #: Represents a key by which DOM Storage keys its CachedStorageAreas
    storage_key: typing.Optional[SerializedStorageKey] = None

    def to_json(self):
        json = dict()
        json['isLocalStorage'] = self.is_local_storage
        if self.security_origin is not None:
            json['securityOrigin'] = self.security_origin
        if self.storage_key is not None:
            json['storageKey'] = self.storage_key.to_json()
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            is_local_storage=bool(json['isLocalStorage']),
            security_origin=str(json['securityOrigin']) if 'securityOrigin' in json else None,
            storage_key=SerializedStorageKey.from_json(json['storageKey']) if 'storageKey' in json else None,
        )


class Item(list):
    '''
    DOM Storage item.
    '''
    def to_json(self) -> typing.List[str]:
        return self

    @classmethod
    def from_json(cls, json: typing.List[str]) -> Item:
        return cls(json)

    def __repr__(self):
        return 'Item({})'.format(super().__repr__())


def clear(
        storage_id: StorageId
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    :param storage_id:
    '''
    params: T_JSON_DICT = dict()
    params['storageId'] = storage_id.to_json()
    cmd_dict: T_JSON_DICT = {
        'method': 'DOMStorage.clear',
        'params': params,
    }
    json = yield cmd_dict


def disable() -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Disables storage tracking, prevents storage events from being sent to the client.
    '''
    cmd_dict: T_JSON_DICT = {
        'method': 'DOMStorage.disable',
    }
    json = yield cmd_dict


def enable() -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Enables storage tracking, storage events will now be delivered to the client.
    '''
    cmd_dict: T_JSON_DICT = {
        'method': 'DOMStorage.enable',
    }
    json = yield cmd_dict


def get_dom_storage_items(
        storage_id: StorageId
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,typing.List[Item]]:
    '''
    :param storage_id:
    :returns: 
    '''
    params: T_JSON_DICT = dict()
    params['storageId'] = storage_id.to_json()
    cmd_dict: T_JSON_DICT = {
        'method': 'DOMStorage.getDOMStorageItems',
        'params': params,
    }
    json = yield cmd_dict
    return [Item.from_json(i) for i in json['entries']]


def remove_dom_storage_item(
        storage_id: StorageId,
        key: str
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    :param storage_id:
    :param key:
    '''
    params: T_JSON_DICT = dict()
    params['storageId'] = storage_id.to_json()
    params['key'] = key
    cmd_dict: T_JSON_DICT = {
        'method': 'DOMStorage.removeDOMStorageItem',
        'params': params,
    }
    json = yield cmd_dict


def set_dom_storage_item(
        storage_id: StorageId,
        key: str,
        value: str
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    :param storage_id:
    :param key:
    :param value:
    '''
    params: T_JSON_DICT = dict()
    params['storageId'] = storage_id.to_json()
    params['key'] = key
    params['value'] = value
    cmd_dict: T_JSON_DICT = {
        'method': 'DOMStorage.setDOMStorageItem',
        'params': params,
    }
    json = yield cmd_dict


@event_class('DOMStorage.domStorageItemAdded')
@dataclass
class DomStorageItemAdded:
    storage_id: StorageId
    key: str
    new_value: str

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> DomStorageItemAdded:
        return cls(
            storage_id=StorageId.from_json(json['storageId']),
            key=str(json['key']),
            new_value=str(json['newValue'])
        )


@event_class('DOMStorage.domStorageItemRemoved')
@dataclass
class DomStorageItemRemoved:
    storage_id: StorageId
    key: str

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> DomStorageItemRemoved:
        return cls(
            storage_id=StorageId.from_json(json['storageId']),
            key=str(json['key'])
        )


@event_class('DOMStorage.domStorageItemUpdated')
@dataclass
class DomStorageItemUpdated:
    storage_id: StorageId
    key: str
    old_value: str
    new_value: str

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> DomStorageItemUpdated:
        return cls(
            storage_id=StorageId.from_json(json['storageId']),
            key=str(json['key']),
            old_value=str(json['oldValue']),
            new_value=str(json['newValue'])
        )


@event_class('DOMStorage.domStorageItemsCleared')
@dataclass
class DomStorageItemsCleared:
    storage_id: StorageId

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> DomStorageItemsCleared:
        return cls(
            storage_id=StorageId.from_json(json['storageId'])
        )

# === NexusCore/openenv\Lib\site-packages\selenium\webdriver\common\devtools\v137\dom_storage.py ===
# DO NOT EDIT THIS FILE!
#
# This file is generated from the CDP specification. If you need to make
# changes, edit the generator and regenerate all of the modules.
#
# CDP domain: DOMStorage (experimental)
from __future__ import annotations
from .util import event_class, T_JSON_DICT
from dataclasses import dataclass
import enum
import typing

class SerializedStorageKey(str):
    def to_json(self) -> str:
        return self

    @classmethod
    def from_json(cls, json: str) -> SerializedStorageKey:
        return cls(json)

    def __repr__(self):
        return 'SerializedStorageKey({})'.format(super().__repr__())


@dataclass
class StorageId:
    '''
    DOM Storage identifier.
    '''
    #: Whether the storage is local storage (not session storage).
    is_local_storage: bool

    #: Security origin for the storage.
    security_origin: typing.Optional[str] = None

    #: Represents a key by which DOM Storage keys its CachedStorageAreas
    storage_key: typing.Optional[SerializedStorageKey] = None

    def to_json(self):
        json = dict()
        json['isLocalStorage'] = self.is_local_storage
        if self.security_origin is not None:
            json['securityOrigin'] = self.security_origin
        if self.storage_key is not None:
            json['storageKey'] = self.storage_key.to_json()
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            is_local_storage=bool(json['isLocalStorage']),
            security_origin=str(json['securityOrigin']) if 'securityOrigin' in json else None,
            storage_key=SerializedStorageKey.from_json(json['storageKey']) if 'storageKey' in json else None,
        )


class Item(list):
    '''
    DOM Storage item.
    '''
    def to_json(self) -> typing.List[str]:
        return self

    @classmethod
    def from_json(cls, json: typing.List[str]) -> Item:
        return cls(json)

    def __repr__(self):
        return 'Item({})'.format(super().__repr__())


def clear(
        storage_id: StorageId
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    :param storage_id:
    '''
    params: T_JSON_DICT = dict()
    params['storageId'] = storage_id.to_json()
    cmd_dict: T_JSON_DICT = {
        'method': 'DOMStorage.clear',
        'params': params,
    }
    json = yield cmd_dict


def disable() -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Disables storage tracking, prevents storage events from being sent to the client.
    '''
    cmd_dict: T_JSON_DICT = {
        'method': 'DOMStorage.disable',
    }
    json = yield cmd_dict


def enable() -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Enables storage tracking, storage events will now be delivered to the client.
    '''
    cmd_dict: T_JSON_DICT = {
        'method': 'DOMStorage.enable',
    }
    json = yield cmd_dict


def get_dom_storage_items(
        storage_id: StorageId
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,typing.List[Item]]:
    '''
    :param storage_id:
    :returns: 
    '''
    params: T_JSON_DICT = dict()
    params['storageId'] = storage_id.to_json()
    cmd_dict: T_JSON_DICT = {
        'method': 'DOMStorage.getDOMStorageItems',
        'params': params,
    }
    json = yield cmd_dict
    return [Item.from_json(i) for i in json['entries']]


def remove_dom_storage_item(
        storage_id: StorageId,
        key: str
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    :param storage_id:
    :param key:
    '''
    params: T_JSON_DICT = dict()
    params['storageId'] = storage_id.to_json()
    params['key'] = key
    cmd_dict: T_JSON_DICT = {
        'method': 'DOMStorage.removeDOMStorageItem',
        'params': params,
    }
    json = yield cmd_dict


def set_dom_storage_item(
        storage_id: StorageId,
        key: str,
        value: str
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    :param storage_id:
    :param key:
    :param value:
    '''
    params: T_JSON_DICT = dict()
    params['storageId'] = storage_id.to_json()
    params['key'] = key
    params['value'] = value
    cmd_dict: T_JSON_DICT = {
        'method': 'DOMStorage.setDOMStorageItem',
        'params': params,
    }
    json = yield cmd_dict


@event_class('DOMStorage.domStorageItemAdded')
@dataclass
class DomStorageItemAdded:
    storage_id: StorageId
    key: str
    new_value: str

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> DomStorageItemAdded:
        return cls(
            storage_id=StorageId.from_json(json['storageId']),
            key=str(json['key']),
            new_value=str(json['newValue'])
        )


@event_class('DOMStorage.domStorageItemRemoved')
@dataclass
class DomStorageItemRemoved:
    storage_id: StorageId
    key: str

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> DomStorageItemRemoved:
        return cls(
            storage_id=StorageId.from_json(json['storageId']),
            key=str(json['key'])
        )


@event_class('DOMStorage.domStorageItemUpdated')
@dataclass
class DomStorageItemUpdated:
    storage_id: StorageId
    key: str
    old_value: str
    new_value: str

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> DomStorageItemUpdated:
        return cls(
            storage_id=StorageId.from_json(json['storageId']),
            key=str(json['key']),
            old_value=str(json['oldValue']),
            new_value=str(json['newValue'])
        )


@event_class('DOMStorage.domStorageItemsCleared')
@dataclass
class DomStorageItemsCleared:
    storage_id: StorageId

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> DomStorageItemsCleared:
        return cls(
            storage_id=StorageId.from_json(json['storageId'])
        )

# === NexusCore/openenv\Lib\site-packages\traitlets\config\argcomplete_config.py ===
"""Helper utilities for integrating argcomplete with traitlets"""

# Copyright (c) IPython Development Team.
# Distributed under the terms of the Modified BSD License.
from __future__ import annotations

import argparse
import os
import typing as t

try:
    import argcomplete
    from argcomplete import CompletionFinder  # type:ignore[attr-defined]
except ImportError:
    # This module and its utility methods are written to not crash even
    # if argcomplete is not installed.
    class StubModule:
        def __getattr__(self, attr: str) -> t.Any:
            if not attr.startswith("__"):
                raise ModuleNotFoundError("No module named 'argcomplete'")
            raise AttributeError(f"argcomplete stub module has no attribute '{attr}'")

    argcomplete = StubModule()  # type:ignore[assignment]
    CompletionFinder = object  # type:ignore[assignment, misc]


def get_argcomplete_cwords() -> t.Optional[t.List[str]]:
    """Get current words prior to completion point

    This is normally done in the `argcomplete.CompletionFinder` constructor,
    but is exposed here to allow `traitlets` to follow dynamic code-paths such
    as determining whether to evaluate a subcommand.
    """
    if "_ARGCOMPLETE" not in os.environ:
        return None

    comp_line = os.environ["COMP_LINE"]
    comp_point = int(os.environ["COMP_POINT"])
    # argcomplete.debug("splitting COMP_LINE for:", comp_line, comp_point)
    comp_words: t.List[str]
    try:
        (
            cword_prequote,
            cword_prefix,
            cword_suffix,
            comp_words,
            last_wordbreak_pos,
        ) = argcomplete.split_line(comp_line, comp_point)  # type:ignore[attr-defined,no-untyped-call]
    except ModuleNotFoundError:
        return None

    # _ARGCOMPLETE is set by the shell script to tell us where comp_words
    # should start, based on what we're completing.
    # 1: <script> [args]
    # 2: python <script> [args]
    # 3: python -m <module> [args]
    start = int(os.environ["_ARGCOMPLETE"]) - 1
    comp_words = comp_words[start:]

    # argcomplete.debug("prequote=", cword_prequote, "prefix=", cword_prefix, "suffix=", cword_suffix, "words=", comp_words, "last=", last_wordbreak_pos)
    return comp_words  # noqa: RET504


def increment_argcomplete_index() -> None:
    """Assumes ``$_ARGCOMPLETE`` is set and `argcomplete` is importable

    Increment the index pointed to by ``$_ARGCOMPLETE``, which is used to
    determine which word `argcomplete` should start evaluating the command-line.
    This may be useful to "inform" `argcomplete` that we have already evaluated
    the first word as a subcommand.
    """
    try:
        os.environ["_ARGCOMPLETE"] = str(int(os.environ["_ARGCOMPLETE"]) + 1)
    except Exception:
        try:
            argcomplete.debug("Unable to increment $_ARGCOMPLETE", os.environ["_ARGCOMPLETE"])  # type:ignore[attr-defined,no-untyped-call]
        except (KeyError, ModuleNotFoundError):
            pass


class ExtendedCompletionFinder(CompletionFinder):
    """An extension of CompletionFinder which dynamically completes class-trait based options

    This finder adds a few functionalities:

    1. When completing options, it will add ``--Class.`` to the list of completions, for each
    class in `Application.classes` that could complete the current option.
    2. If it detects that we are currently trying to complete an option related to ``--Class.``,
    it will add the corresponding config traits of Class to the `ArgumentParser` instance,
    so that the traits' completers can be used.
    3. If there are any subcommands, they are added as completions for the first word

    Note that we are avoiding adding all config traits of all classes to the `ArgumentParser`,
    which would be easier but would add more runtime overhead and would also make completions
    appear more spammy.

    These changes do require using the internals of `argcomplete.CompletionFinder`.
    """

    _parser: argparse.ArgumentParser
    config_classes: t.List[t.Any] = []  # Configurables
    subcommands: t.List[str] = []

    def match_class_completions(self, cword_prefix: str) -> t.List[t.Tuple[t.Any, str]]:
        """Match the word to be completed against our Configurable classes

        Check if cword_prefix could potentially match against --{class}. for any class
        in Application.classes.
        """
        class_completions = [(cls, f"--{cls.__name__}.") for cls in self.config_classes]
        matched_completions = class_completions
        if "." in cword_prefix:
            cword_prefix = cword_prefix[: cword_prefix.index(".") + 1]
            matched_completions = [(cls, c) for (cls, c) in class_completions if c == cword_prefix]
        elif len(cword_prefix) > 0:
            matched_completions = [
                (cls, c) for (cls, c) in class_completions if c.startswith(cword_prefix)
            ]
        return matched_completions

    def inject_class_to_parser(self, cls: t.Any) -> None:
        """Add dummy arguments to our ArgumentParser for the traits of this class

        The argparse-based loader currently does not actually add any class traits to
        the constructed ArgumentParser, only the flags & aliaes. In order to work nicely
        with argcomplete's completers functionality, this method adds dummy arguments
        of the form --Class.trait to the ArgumentParser instance.

        This method should be called selectively to reduce runtime overhead and to avoid
        spamming options across all of Application.classes.
        """
        try:
            for traitname, trait in cls.class_traits(config=True).items():
                completer = trait.metadata.get("argcompleter") or getattr(
                    trait, "argcompleter", None
                )
                multiplicity = trait.metadata.get("multiplicity")
                self._parser.add_argument(  # type: ignore[attr-defined]
                    f"--{cls.__name__}.{traitname}",
                    type=str,
                    help=trait.help,
                    nargs=multiplicity,
                    # metavar=traitname,
                ).completer = completer
                # argcomplete.debug(f"added --{cls.__name__}.{traitname}")
        except AttributeError:
            pass

    def _get_completions(
        self, comp_words: t.List[str], cword_prefix: str, *args: t.Any
    ) -> t.List[str]:
        """Overridden to dynamically append --Class.trait arguments if appropriate

        Warning:
            This does not (currently) support completions of the form
            --Class1.Class2.<...>.trait, although this is valid for traitlets.
            Part of the reason is that we don't currently have a way to identify
            which classes may be used with Class1 as a parent.

        Warning:
            This is an internal method in CompletionFinder and so the API might
            be subject to drift.
        """
        # Try to identify if we are completing something related to --Class. for
        # a known Class, if we are then add the Class config traits to our ArgumentParser.
        prefix_chars = self._parser.prefix_chars
        is_option = len(cword_prefix) > 0 and cword_prefix[0] in prefix_chars
        if is_option:
            # If we are currently completing an option, check if it could
            # match with any of the --Class. completions. If there's exactly
            # one matched class, then expand out the --Class.trait options.
            matched_completions = self.match_class_completions(cword_prefix)
            if len(matched_completions) == 1:
                matched_cls = matched_completions[0][0]
                self.inject_class_to_parser(matched_cls)
        elif len(comp_words) > 0 and "." in comp_words[-1] and not is_option:
            # If not an option, perform a hacky check to see if we are completing
            # an argument for an already present --Class.trait option. Search backwards
            # for last option (based on last word starting with prefix_chars), and see
            # if it is of the form --Class.trait. Note that if multiplicity="+", these
            # arguments might conflict with positional arguments.
            for prev_word in comp_words[::-1]:
                if len(prev_word) > 0 and prev_word[0] in prefix_chars:
                    matched_completions = self.match_class_completions(prev_word)
                    if matched_completions:
                        matched_cls = matched_completions[0][0]
                        self.inject_class_to_parser(matched_cls)
                    break

        completions: t.List[str]
        completions = super()._get_completions(comp_words, cword_prefix, *args)  # type:ignore[no-untyped-call]

        # For subcommand-handling: it is difficult to get this to work
        # using argparse subparsers, because the ArgumentParser accepts
        # arbitrary extra_args, which ends up masking subparsers.
        # Instead, check if comp_words only consists of the script,
        # if so check if any subcommands start with cword_prefix.
        if self.subcommands and len(comp_words) == 1:
            argcomplete.debug("Adding subcommands for", cword_prefix)  # type:ignore[attr-defined,no-untyped-call]
            completions.extend(subc for subc in self.subcommands if subc.startswith(cword_prefix))

        return completions

    def _get_option_completions(
        self, parser: argparse.ArgumentParser, cword_prefix: str
    ) -> t.List[str]:
        """Overridden to add --Class. completions when appropriate"""
        completions: t.List[str]
        completions = super()._get_option_completions(parser, cword_prefix)  # type:ignore[no-untyped-call]
        if cword_prefix.endswith("."):
            return completions

        matched_completions = self.match_class_completions(cword_prefix)
        if len(matched_completions) > 1:
            completions.extend(opt for cls, opt in matched_completions)
        # If there is exactly one match, we would expect it to have already
        # been handled by the options dynamically added in _get_completions().
        # However, maybe there's an edge cases missed here, for example if the
        # matched class has no configurable traits.
        return completions

# === NexusCore/openenv\Lib\site-packages\nest_asyncio.py ===
"""Patch asyncio to allow nested event loops."""

import asyncio
import asyncio.events as events
import os
import sys
import threading
from contextlib import contextmanager, suppress
from heapq import heappop


def apply(loop=None):
    """Patch asyncio to make its event loop reentrant."""
    _patch_asyncio()
    _patch_policy()
    _patch_tornado()

    loop = loop or asyncio.get_event_loop()
    _patch_loop(loop)


def _patch_asyncio():
    """Patch asyncio module to use pure Python tasks and futures."""

    def run(main, *, debug=False):
        loop = asyncio.get_event_loop()
        loop.set_debug(debug)
        task = asyncio.ensure_future(main)
        try:
            return loop.run_until_complete(task)
        finally:
            if not task.done():
                task.cancel()
                with suppress(asyncio.CancelledError):
                    loop.run_until_complete(task)

    def _get_event_loop(stacklevel=3):
        loop = events._get_running_loop()
        if loop is None:
            loop = events.get_event_loop_policy().get_event_loop()
        return loop

    # Use module level _current_tasks, all_tasks and patch run method.
    if hasattr(asyncio, '_nest_patched'):
        return
    if sys.version_info >= (3, 6, 0):
        asyncio.Task = asyncio.tasks._CTask = asyncio.tasks.Task = \
            asyncio.tasks._PyTask
        asyncio.Future = asyncio.futures._CFuture = asyncio.futures.Future = \
            asyncio.futures._PyFuture
    if sys.version_info < (3, 7, 0):
        asyncio.tasks._current_tasks = asyncio.tasks.Task._current_tasks
        asyncio.all_tasks = asyncio.tasks.Task.all_tasks
    if sys.version_info >= (3, 9, 0):
        events._get_event_loop = events.get_event_loop = \
            asyncio.get_event_loop = _get_event_loop
    asyncio.run = run
    asyncio._nest_patched = True


def _patch_policy():
    """Patch the policy to always return a patched loop."""

    def get_event_loop(self):
        if self._local._loop is None:
            loop = self.new_event_loop()
            _patch_loop(loop)
            self.set_event_loop(loop)
        return self._local._loop

    policy = events.get_event_loop_policy()
    policy.__class__.get_event_loop = get_event_loop


def _patch_loop(loop):
    """Patch loop to make it reentrant."""

    def run_forever(self):
        with manage_run(self), manage_asyncgens(self):
            while True:
                self._run_once()
                if self._stopping:
                    break
        self._stopping = False

    def run_until_complete(self, future):
        with manage_run(self):
            f = asyncio.ensure_future(future, loop=self)
            if f is not future:
                f._log_destroy_pending = False
            while not f.done():
                self._run_once()
                if self._stopping:
                    break
            if not f.done():
                raise RuntimeError(
                    'Event loop stopped before Future completed.')
            return f.result()

    def _run_once(self):
        """
        Simplified re-implementation of asyncio's _run_once that
        runs handles as they become ready.
        """
        ready = self._ready
        scheduled = self._scheduled
        while scheduled and scheduled[0]._cancelled:
            heappop(scheduled)

        timeout = (
            0 if ready or self._stopping
            else min(max(
                scheduled[0]._when - self.time(), 0), 86400) if scheduled
            else None)
        event_list = self._selector.select(timeout)
        self._process_events(event_list)

        end_time = self.time() + self._clock_resolution
        while scheduled and scheduled[0]._when < end_time:
            handle = heappop(scheduled)
            ready.append(handle)

        for _ in range(len(ready)):
            if not ready:
                break
            handle = ready.popleft()
            if not handle._cancelled:
                # preempt the current task so that that checks in
                # Task.__step do not raise
                curr_task = curr_tasks.pop(self, None)

                try:
                    handle._run()
                finally:
                    # restore the current task
                    if curr_task is not None:
                        curr_tasks[self] = curr_task

        handle = None

    @contextmanager
    def manage_run(self):
        """Set up the loop for running."""
        self._check_closed()
        old_thread_id = self._thread_id
        old_running_loop = events._get_running_loop()
        try:
            self._thread_id = threading.get_ident()
            events._set_running_loop(self)
            self._num_runs_pending += 1
            if self._is_proactorloop:
                if self._self_reading_future is None:
                    self.call_soon(self._loop_self_reading)
            yield
        finally:
            self._thread_id = old_thread_id
            events._set_running_loop(old_running_loop)
            self._num_runs_pending -= 1
            if self._is_proactorloop:
                if (self._num_runs_pending == 0
                        and self._self_reading_future is not None):
                    ov = self._self_reading_future._ov
                    self._self_reading_future.cancel()
                    if ov is not None:
                        self._proactor._unregister(ov)
                    self._self_reading_future = None

    @contextmanager
    def manage_asyncgens(self):
        if not hasattr(sys, 'get_asyncgen_hooks'):
            # Python version is too old.
            return
        old_agen_hooks = sys.get_asyncgen_hooks()
        try:
            self._set_coroutine_origin_tracking(self._debug)
            if self._asyncgens is not None:
                sys.set_asyncgen_hooks(
                    firstiter=self._asyncgen_firstiter_hook,
                    finalizer=self._asyncgen_finalizer_hook)
            yield
        finally:
            self._set_coroutine_origin_tracking(False)
            if self._asyncgens is not None:
                sys.set_asyncgen_hooks(*old_agen_hooks)

    def _check_running(self):
        """Do not throw exception if loop is already running."""
        pass

    if hasattr(loop, '_nest_patched'):
        return
    if not isinstance(loop, asyncio.BaseEventLoop):
        raise ValueError('Can\'t patch loop of type %s' % type(loop))
    cls = loop.__class__
    cls.run_forever = run_forever
    cls.run_until_complete = run_until_complete
    cls._run_once = _run_once
    cls._check_running = _check_running
    cls._check_runnung = _check_running  # typo in Python 3.7 source
    cls._num_runs_pending = 1 if loop.is_running() else 0
    cls._is_proactorloop = (
        os.name == 'nt' and issubclass(cls, asyncio.ProactorEventLoop))
    if sys.version_info < (3, 7, 0):
        cls._set_coroutine_origin_tracking = cls._set_coroutine_wrapper
    curr_tasks = asyncio.tasks._current_tasks \
        if sys.version_info >= (3, 7, 0) else asyncio.Task._current_tasks
    cls._nest_patched = True


def _patch_tornado():
    """
    If tornado is imported before nest_asyncio, make tornado aware of
    the pure-Python asyncio Future.
    """
    if 'tornado' in sys.modules:
        import tornado.concurrent as tc  # type: ignore
        tc.Future = asyncio.Future
        if asyncio.Future not in tc.FUTURES:
            tc.FUTURES += (asyncio.Future,)

# === NexusCore/openenv\Lib\site-packages\anthropic\_compat.py ===
from __future__ import annotations

from typing import TYPE_CHECKING, Any, Union, Generic, TypeVar, Callable, cast, overload
from datetime import date, datetime
from typing_extensions import Self

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
    exclude: IncEx = None,
    exclude_unset: bool = False,
    exclude_defaults: bool = False,
    warnings: bool = True,
) -> dict[str, Any]:
    if PYDANTIC_V2:
        return model.model_dump(
            exclude=exclude,
            exclude_unset=exclude_unset,
            exclude_defaults=exclude_defaults,
            warnings=warnings,
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
    try:
        from functools import cached_property as cached_property
    except ImportError:
        from cached_property import cached_property as cached_property

    typed_cached_property = cached_property

# === NexusCore/openenv\Lib\site-packages\anthropic\_types.py ===
from __future__ import annotations

from os import PathLike
from typing import (
    IO,
    TYPE_CHECKING,
    Any,
    Dict,
    List,
    Type,
    Tuple,
    Union,
    Mapping,
    TypeVar,
    Callable,
    Optional,
    Sequence,
)
from typing_extensions import Literal, Protocol, TypeAlias, TypedDict, override, runtime_checkable

import httpx
import pydantic
from httpx import URL, Proxy, Timeout, Response, BaseTransport, AsyncBaseTransport

if TYPE_CHECKING:
    from ._models import BaseModel
    from ._response import APIResponse, AsyncAPIResponse
    from ._legacy_response import HttpxBinaryResponseContent

Transport = BaseTransport
AsyncTransport = AsyncBaseTransport
Query = Mapping[str, object]
Body = object
AnyMapping = Mapping[str, object]
ModelT = TypeVar("ModelT", bound=pydantic.BaseModel)
_T = TypeVar("_T")


# Approximates httpx internal ProxiesTypes and RequestFiles types
# while adding support for `PathLike` instances
ProxiesDict = Dict["str | URL", Union[None, str, URL, Proxy]]
ProxiesTypes = Union[str, Proxy, ProxiesDict]
if TYPE_CHECKING:
    Base64FileInput = Union[IO[bytes], PathLike[str]]
    FileContent = Union[IO[bytes], bytes, PathLike[str]]
else:
    Base64FileInput = Union[IO[bytes], PathLike]
    FileContent = Union[IO[bytes], bytes, PathLike]  # PathLike is not subscriptable in Python 3.8.
FileTypes = Union[
    # file (or bytes)
    FileContent,
    # (filename, file (or bytes))
    Tuple[Optional[str], FileContent],
    # (filename, file (or bytes), content_type)
    Tuple[Optional[str], FileContent, Optional[str]],
    # (filename, file (or bytes), content_type, headers)
    Tuple[Optional[str], FileContent, Optional[str], Mapping[str, str]],
]
RequestFiles = Union[Mapping[str, FileTypes], Sequence[Tuple[str, FileTypes]]]

# duplicate of the above but without our custom file support
HttpxFileContent = Union[IO[bytes], bytes]
HttpxFileTypes = Union[
    # file (or bytes)
    HttpxFileContent,
    # (filename, file (or bytes))
    Tuple[Optional[str], HttpxFileContent],
    # (filename, file (or bytes), content_type)
    Tuple[Optional[str], HttpxFileContent, Optional[str]],
    # (filename, file (or bytes), content_type, headers)
    Tuple[Optional[str], HttpxFileContent, Optional[str], Mapping[str, str]],
]
HttpxRequestFiles = Union[Mapping[str, HttpxFileTypes], Sequence[Tuple[str, HttpxFileTypes]]]

# Workaround to support (cast_to: Type[ResponseT]) -> ResponseT
# where ResponseT includes `None`. In order to support directly
# passing `None`, overloads would have to be defined for every
# method that uses `ResponseT` which would lead to an unacceptable
# amount of code duplication and make it unreadable. See _base_client.py
# for example usage.
#
# This unfortunately means that you will either have
# to import this type and pass it explicitly:
#
# from anthropic import NoneType
# client.get('/foo', cast_to=NoneType)
#
# or build it yourself:
#
# client.get('/foo', cast_to=type(None))
if TYPE_CHECKING:
    NoneType: Type[None]
else:
    NoneType = type(None)


class RequestOptions(TypedDict, total=False):
    headers: Headers
    max_retries: int
    timeout: float | Timeout | None
    params: Query
    extra_json: AnyMapping
    idempotency_key: str


# Sentinel class used until PEP 0661 is accepted
class NotGiven:
    """
    A sentinel singleton class used to distinguish omitted keyword arguments
    from those passed in with the value None (which may have different behavior).

    For example:

    ```py
    def get(timeout: Union[int, NotGiven, None] = NotGiven()) -> Response: ...


    get(timeout=1)  # 1s timeout
    get(timeout=None)  # No timeout
    get()  # Default timeout behavior, which may not be statically known at the method definition.
    ```
    """

    def __bool__(self) -> Literal[False]:
        return False

    @override
    def __repr__(self) -> str:
        return "NOT_GIVEN"


NotGivenOr = Union[_T, NotGiven]
NOT_GIVEN = NotGiven()


class Omit:
    """In certain situations you need to be able to represent a case where a default value has
    to be explicitly removed and `None` is not an appropriate substitute, for example:

    ```py
    # as the default `Content-Type` header is `application/json` that will be sent
    client.post("/upload/files", files={"file": b"my raw file content"})

    # you can't explicitly override the header as it has to be dynamically generated
    # to look something like: 'multipart/form-data; boundary=0d8382fcf5f8c3be01ca2e11002d2983'
    client.post(..., headers={"Content-Type": "multipart/form-data"})

    # instead you can remove the default `application/json` header by passing Omit
    client.post(..., headers={"Content-Type": Omit()})
    ```
    """

    def __bool__(self) -> Literal[False]:
        return False


@runtime_checkable
class ModelBuilderProtocol(Protocol):
    @classmethod
    def build(
        cls: type[_T],
        *,
        response: Response,
        data: object,
    ) -> _T: ...


Headers = Mapping[str, Union[str, Omit]]


class HeadersLikeProtocol(Protocol):
    def get(self, __key: str) -> str | None: ...


HeadersLike = Union[Headers, HeadersLikeProtocol]

ResponseT = TypeVar(
    "ResponseT",
    bound=Union[
        object,
        str,
        None,
        "BaseModel",
        List[Any],
        Dict[str, Any],
        Response,
        ModelBuilderProtocol,
        "APIResponse[Any]",
        "AsyncAPIResponse[Any]",
        "HttpxBinaryResponseContent",
    ],
)

StrBytesIntFloat = Union[str, bytes, int, float]

# Note: copied from Pydantic
# https://github.com/pydantic/pydantic/blob/32ea570bf96e84234d2992e1ddf40ab8a565925a/pydantic/main.py#L49
IncEx: TypeAlias = "set[int] | set[str] | dict[int, Any] | dict[str, Any] | None"

PostParser = Callable[[Any], Any]


@runtime_checkable
class InheritsGeneric(Protocol):
    """Represents a type that has inherited from `Generic`

    The `__orig_bases__` property can be used to determine the resolved
    type variable for a given base class.
    """

    __orig_bases__: tuple[_GenericAlias]


class _GenericAlias(Protocol):
    __origin__: type[object]


class HttpxSendArgs(TypedDict, total=False):
    auth: httpx.Auth

# === NexusCore/openenv\Lib\site-packages\pyparsing\actions.py ===
# actions.py
from __future__ import annotations

from typing import Union, Callable, Any

from .exceptions import ParseException
from .util import col, replaced_by_pep8
from .results import ParseResults


ParseAction = Union[
    Callable[[], Any],
    Callable[[ParseResults], Any],
    Callable[[int, ParseResults], Any],
    Callable[[str, int, ParseResults], Any],
]


class OnlyOnce:
    """
    Wrapper for parse actions, to ensure they are only called once.
    Note: parse action signature must include all 3 arguments.
    """

    def __init__(self, method_call: Callable[[str, int, ParseResults], Any]) -> None:
        from .core import _trim_arity

        self.callable = _trim_arity(method_call)
        self.called = False

    def __call__(self, s: str, l: int, t: ParseResults) -> ParseResults:
        if not self.called:
            results = self.callable(s, l, t)
            self.called = True
            return results
        raise ParseException(s, l, "OnlyOnce obj called multiple times w/out reset")

    def reset(self):
        """
        Allow the associated parse action to be called once more.
        """

        self.called = False


def match_only_at_col(n: int) -> ParseAction:
    """
    Helper method for defining parse actions that require matching at
    a specific column in the input text.
    """

    def verify_col(strg: str, locn: int, toks: ParseResults) -> None:
        if col(locn, strg) != n:
            raise ParseException(strg, locn, f"matched token not at column {n}")

    return verify_col


def replace_with(repl_str: str) -> ParseAction:
    """
    Helper method for common parse actions that simply return
    a literal value.  Especially useful when used with
    :class:`transform_string<ParserElement.transform_string>` ().

    Example::

        num = Word(nums).set_parse_action(lambda toks: int(toks[0]))
        na = one_of("N/A NA").set_parse_action(replace_with(math.nan))
        term = na | num

        term[1, ...].parse_string("324 234 N/A 234") # -> [324, 234, nan, 234]
    """
    return lambda s, l, t: [repl_str]


def remove_quotes(s: str, l: int, t: ParseResults) -> Any:
    """
    Helper parse action for removing quotation marks from parsed
    quoted strings.

    Example::

        # by default, quotation marks are included in parsed results
        quoted_string.parse_string("'Now is the Winter of our Discontent'") # -> ["'Now is the Winter of our Discontent'"]

        # use remove_quotes to strip quotation marks from parsed results
        quoted_string.set_parse_action(remove_quotes)
        quoted_string.parse_string("'Now is the Winter of our Discontent'") # -> ["Now is the Winter of our Discontent"]
    """
    return t[0][1:-1]


def with_attribute(*args: tuple[str, str], **attr_dict) -> ParseAction:
    """
    Helper to create a validating parse action to be used with start
    tags created with :class:`make_xml_tags` or
    :class:`make_html_tags`. Use ``with_attribute`` to qualify
    a starting tag with a required attribute value, to avoid false
    matches on common tags such as ``<TD>`` or ``<DIV>``.

    Call ``with_attribute`` with a series of attribute names and
    values. Specify the list of filter attributes names and values as:

    - keyword arguments, as in ``(align="right")``, or
    - as an explicit dict with ``**`` operator, when an attribute
      name is also a Python reserved word, as in ``**{"class":"Customer", "align":"right"}``
    - a list of name-value tuples, as in ``(("ns1:class", "Customer"), ("ns2:align", "right"))``

    For attribute names with a namespace prefix, you must use the second
    form.  Attribute names are matched insensitive to upper/lower case.

    If just testing for ``class`` (with or without a namespace), use
    :class:`with_class`.

    To verify that the attribute exists, but without specifying a value,
    pass ``with_attribute.ANY_VALUE`` as the value.

    Example::

        html = '''
            <div>
            Some text
            <div type="grid">1 4 0 1 0</div>
            <div type="graph">1,3 2,3 1,1</div>
            <div>this has no type</div>
            </div>
        '''
        div,div_end = make_html_tags("div")

        # only match div tag having a type attribute with value "grid"
        div_grid = div().set_parse_action(with_attribute(type="grid"))
        grid_expr = div_grid + SkipTo(div | div_end)("body")
        for grid_header in grid_expr.search_string(html):
            print(grid_header.body)

        # construct a match with any div tag having a type attribute, regardless of the value
        div_any_type = div().set_parse_action(with_attribute(type=with_attribute.ANY_VALUE))
        div_expr = div_any_type + SkipTo(div | div_end)("body")
        for div_header in div_expr.search_string(html):
            print(div_header.body)

    prints::

        1 4 0 1 0

        1 4 0 1 0
        1,3 2,3 1,1
    """
    attrs_list: list[tuple[str, str]] = []
    if args:
        attrs_list.extend(args)
    else:
        attrs_list.extend(attr_dict.items())

    def pa(s: str, l: int, tokens: ParseResults) -> None:
        for attrName, attrValue in attrs_list:
            if attrName not in tokens:
                raise ParseException(s, l, "no matching attribute " + attrName)
            if attrValue != with_attribute.ANY_VALUE and tokens[attrName] != attrValue:  # type: ignore [attr-defined]
                raise ParseException(
                    s,
                    l,
                    f"attribute {attrName!r} has value {tokens[attrName]!r}, must be {attrValue!r}",
                )

    return pa


with_attribute.ANY_VALUE = object()  # type: ignore [attr-defined]


def with_class(classname: str, namespace: str = "") -> ParseAction:
    """
    Simplified version of :class:`with_attribute` when
    matching on a div class - made difficult because ``class`` is
    a reserved word in Python.

    Example::

        html = '''
            <div>
            Some text
            <div class="grid">1 4 0 1 0</div>
            <div class="graph">1,3 2,3 1,1</div>
            <div>this &lt;div&gt; has no class</div>
            </div>

        '''
        div,div_end = make_html_tags("div")
        div_grid = div().set_parse_action(with_class("grid"))

        grid_expr = div_grid + SkipTo(div | div_end)("body")
        for grid_header in grid_expr.search_string(html):
            print(grid_header.body)

        div_any_type = div().set_parse_action(with_class(withAttribute.ANY_VALUE))
        div_expr = div_any_type + SkipTo(div | div_end)("body")
        for div_header in div_expr.search_string(html):
            print(div_header.body)

    prints::

        1 4 0 1 0

        1 4 0 1 0
        1,3 2,3 1,1
    """
    classattr = f"{namespace}:class" if namespace else "class"
    return with_attribute(**{classattr: classname})


# Compatibility synonyms
# fmt: off
replaceWith = replaced_by_pep8("replaceWith", replace_with)
removeQuotes = replaced_by_pep8("removeQuotes", remove_quotes)
withAttribute = replaced_by_pep8("withAttribute", with_attribute)
withClass = replaced_by_pep8("withClass", with_class)
matchOnlyAtCol = replaced_by_pep8("matchOnlyAtCol", match_only_at_col)
# fmt: on

# === NexusCore/openenv\Lib\site-packages\setuptools\archive_util.py ===
"""Utilities for extracting common archive formats"""

import contextlib
import os
import posixpath
import shutil
import tarfile
import zipfile

from ._path import ensure_directory

from distutils.errors import DistutilsError

__all__ = [
    "unpack_archive",
    "unpack_zipfile",
    "unpack_tarfile",
    "default_filter",
    "UnrecognizedFormat",
    "extraction_drivers",
    "unpack_directory",
]


class UnrecognizedFormat(DistutilsError):
    """Couldn't recognize the archive type"""


def default_filter(src, dst):
    """The default progress/filter callback; returns True for all files"""
    return dst


def unpack_archive(
    filename, extract_dir, progress_filter=default_filter, drivers=None
) -> None:
    """Unpack `filename` to `extract_dir`, or raise ``UnrecognizedFormat``

    `progress_filter` is a function taking two arguments: a source path
    internal to the archive ('/'-separated), and a filesystem path where it
    will be extracted.  The callback must return the desired extract path
    (which may be the same as the one passed in), or else ``None`` to skip
    that file or directory.  The callback can thus be used to report on the
    progress of the extraction, as well as to filter the items extracted or
    alter their extraction paths.

    `drivers`, if supplied, must be a non-empty sequence of functions with the
    same signature as this function (minus the `drivers` argument), that raise
    ``UnrecognizedFormat`` if they do not support extracting the designated
    archive type.  The `drivers` are tried in sequence until one is found that
    does not raise an error, or until all are exhausted (in which case
    ``UnrecognizedFormat`` is raised).  If you do not supply a sequence of
    drivers, the module's ``extraction_drivers`` constant will be used, which
    means that ``unpack_zipfile`` and ``unpack_tarfile`` will be tried, in that
    order.
    """
    for driver in drivers or extraction_drivers:
        try:
            driver(filename, extract_dir, progress_filter)
        except UnrecognizedFormat:
            continue
        else:
            return
    else:
        raise UnrecognizedFormat(f"Not a recognized archive type: {filename}")


def unpack_directory(filename, extract_dir, progress_filter=default_filter) -> None:
    """ "Unpack" a directory, using the same interface as for archives

    Raises ``UnrecognizedFormat`` if `filename` is not a directory
    """
    if not os.path.isdir(filename):
        raise UnrecognizedFormat(f"{filename} is not a directory")

    paths = {
        filename: ('', extract_dir),
    }
    for base, dirs, files in os.walk(filename):
        src, dst = paths[base]
        for d in dirs:
            paths[os.path.join(base, d)] = src + d + '/', os.path.join(dst, d)
        for f in files:
            target = os.path.join(dst, f)
            target = progress_filter(src + f, target)
            if not target:
                # skip non-files
                continue
            ensure_directory(target)
            f = os.path.join(base, f)
            shutil.copyfile(f, target)
            shutil.copystat(f, target)


def unpack_zipfile(filename, extract_dir, progress_filter=default_filter) -> None:
    """Unpack zip `filename` to `extract_dir`

    Raises ``UnrecognizedFormat`` if `filename` is not a zipfile (as determined
    by ``zipfile.is_zipfile()``).  See ``unpack_archive()`` for an explanation
    of the `progress_filter` argument.
    """

    if not zipfile.is_zipfile(filename):
        raise UnrecognizedFormat(f"{filename} is not a zip file")

    with zipfile.ZipFile(filename) as z:
        _unpack_zipfile_obj(z, extract_dir, progress_filter)


def _unpack_zipfile_obj(zipfile_obj, extract_dir, progress_filter=default_filter):
    """Internal/private API used by other parts of setuptools.
    Similar to ``unpack_zipfile``, but receives an already opened :obj:`zipfile.ZipFile`
    object instead of a filename.
    """
    for info in zipfile_obj.infolist():
        name = info.filename

        # don't extract absolute paths or ones with .. in them
        if name.startswith('/') or '..' in name.split('/'):
            continue

        target = os.path.join(extract_dir, *name.split('/'))
        target = progress_filter(name, target)
        if not target:
            continue
        if name.endswith('/'):
            # directory
            ensure_directory(target)
        else:
            # file
            ensure_directory(target)
            data = zipfile_obj.read(info.filename)
            with open(target, 'wb') as f:
                f.write(data)
        unix_attributes = info.external_attr >> 16
        if unix_attributes:
            os.chmod(target, unix_attributes)


def _resolve_tar_file_or_dir(tar_obj, tar_member_obj):
    """Resolve any links and extract link targets as normal files."""
    while tar_member_obj is not None and (
        tar_member_obj.islnk() or tar_member_obj.issym()
    ):
        linkpath = tar_member_obj.linkname
        if tar_member_obj.issym():
            base = posixpath.dirname(tar_member_obj.name)
            linkpath = posixpath.join(base, linkpath)
            linkpath = posixpath.normpath(linkpath)
        tar_member_obj = tar_obj._getmember(linkpath)

    is_file_or_dir = tar_member_obj is not None and (
        tar_member_obj.isfile() or tar_member_obj.isdir()
    )
    if is_file_or_dir:
        return tar_member_obj

    raise LookupError('Got unknown file type')


def _iter_open_tar(tar_obj, extract_dir, progress_filter):
    """Emit member-destination pairs from a tar archive."""
    # don't do any chowning!
    tar_obj.chown = lambda *args: None

    with contextlib.closing(tar_obj):
        for member in tar_obj:
            name = member.name
            # don't extract absolute paths or ones with .. in them
            if name.startswith('/') or '..' in name.split('/'):
                continue

            prelim_dst = os.path.join(extract_dir, *name.split('/'))

            try:
                member = _resolve_tar_file_or_dir(tar_obj, member)
            except LookupError:
                continue

            final_dst = progress_filter(name, prelim_dst)
            if not final_dst:
                continue

            if final_dst.endswith(os.sep):
                final_dst = final_dst[:-1]

            yield member, final_dst


def unpack_tarfile(filename, extract_dir, progress_filter=default_filter) -> bool:
    """Unpack tar/tar.gz/tar.bz2 `filename` to `extract_dir`

    Raises ``UnrecognizedFormat`` if `filename` is not a tarfile (as determined
    by ``tarfile.open()``).  See ``unpack_archive()`` for an explanation
    of the `progress_filter` argument.
    """
    try:
        tarobj = tarfile.open(filename)
    except tarfile.TarError as e:
        raise UnrecognizedFormat(
            f"{filename} is not a compressed or uncompressed tar file"
        ) from e

    for member, final_dst in _iter_open_tar(
        tarobj,
        extract_dir,
        progress_filter,
    ):
        try:
            # XXX Ugh
            tarobj._extract_member(member, final_dst)
        except tarfile.ExtractError:
            # chown/chmod/mkfifo/mknode/makedev failed
            pass

    return True


extraction_drivers = unpack_directory, unpack_zipfile, unpack_tarfile

# === NexusCore/openenv\Lib\site-packages\fontTools\varLib\errors.py ===
import textwrap


class VarLibError(Exception):
    """Base exception for the varLib module."""


class VarLibValidationError(VarLibError):
    """Raised when input data is invalid from varLib's point of view."""


class VarLibMergeError(VarLibError):
    """Raised when input data cannot be merged into a variable font."""

    def __init__(self, merger=None, **kwargs):
        self.merger = merger
        if not kwargs:
            kwargs = {}
        if "stack" in kwargs:
            self.stack = kwargs["stack"]
            del kwargs["stack"]
        else:
            self.stack = []
        self.cause = kwargs

    @property
    def reason(self):
        return self.__doc__

    def _master_name(self, ix):
        if self.merger is not None:
            ttf = self.merger.ttfs[ix]
            if "name" in ttf and ttf["name"].getBestFullName():
                return ttf["name"].getBestFullName()
            elif hasattr(ttf.reader, "file") and hasattr(ttf.reader.file, "name"):
                return ttf.reader.file.name
        return f"master number {ix}"

    @property
    def offender(self):
        if "expected" in self.cause and "got" in self.cause:
            index = [x == self.cause["expected"] for x in self.cause["got"]].index(
                False
            )
            master_name = self._master_name(index)
            if "location" in self.cause:
                master_name = f"{master_name} ({self.cause['location']})"
            return index, master_name
        return None, None

    @property
    def details(self):
        if "expected" in self.cause and "got" in self.cause:
            offender_index, offender = self.offender
            got = self.cause["got"][offender_index]
            return f"Expected to see {self.stack[0]}=={self.cause['expected']!r}, instead saw {got!r}\n"
        return ""

    def __str__(self):
        offender_index, offender = self.offender
        location = ""
        if offender:
            location = f"\n\nThe problem is likely to be in {offender}:\n"
        context = "".join(reversed(self.stack))
        basic = textwrap.fill(
            f"Couldn't merge the fonts, because {self.reason}. "
            f"This happened while performing the following operation: {context}",
            width=78,
        )
        return "\n\n" + basic + location + self.details


class ShouldBeConstant(VarLibMergeError):
    """some values were different, but should have been the same"""

    @property
    def details(self):
        basic_message = super().details

        if self.stack[0] != ".FeatureCount" or self.merger is None:
            return basic_message

        assert self.stack[0] == ".FeatureCount"
        offender_index, _ = self.offender
        bad_ttf = self.merger.ttfs[offender_index]
        good_ttf = next(
            ttf
            for ttf in self.merger.ttfs
            if self.stack[-1] in ttf
            and ttf[self.stack[-1]].table.FeatureList.FeatureCount
            == self.cause["expected"]
        )

        good_features = [
            x.FeatureTag
            for x in good_ttf[self.stack[-1]].table.FeatureList.FeatureRecord
        ]
        bad_features = [
            x.FeatureTag
            for x in bad_ttf[self.stack[-1]].table.FeatureList.FeatureRecord
        ]
        return basic_message + (
            "\nIncompatible features between masters.\n"
            f"Expected: {', '.join(good_features)}.\n"
            f"Got: {', '.join(bad_features)}.\n"
        )


class FoundANone(VarLibMergeError):
    """one of the values in a list was empty when it shouldn't have been"""

    @property
    def offender(self):
        index = [x is None for x in self.cause["got"]].index(True)
        return index, self._master_name(index)

    @property
    def details(self):
        cause, stack = self.cause, self.stack
        return f"{stack[0]}=={cause['got']}\n"


class NotANone(VarLibMergeError):
    """one of the values in a list was not empty when it should have been"""

    @property
    def offender(self):
        index = [x is not None for x in self.cause["got"]].index(True)
        return index, self._master_name(index)

    @property
    def details(self):
        cause, stack = self.cause, self.stack
        return f"{stack[0]}=={cause['got']}\n"


class MismatchedTypes(VarLibMergeError):
    """data had inconsistent types"""


class LengthsDiffer(VarLibMergeError):
    """a list of objects had inconsistent lengths"""


class KeysDiffer(VarLibMergeError):
    """a list of objects had different keys"""


class InconsistentGlyphOrder(VarLibMergeError):
    """the glyph order was inconsistent between masters"""


class InconsistentExtensions(VarLibMergeError):
    """the masters use extension lookups in inconsistent ways"""


class UnsupportedFormat(VarLibMergeError):
    """an OpenType subtable (%s) had a format I didn't expect"""

    def __init__(self, merger=None, **kwargs):
        super().__init__(merger, **kwargs)
        if not self.stack:
            self.stack = [".Format"]

    @property
    def reason(self):
        s = self.__doc__ % self.cause["subtable"]
        if "value" in self.cause:
            s += f" ({self.cause['value']!r})"
        return s


class InconsistentFormats(UnsupportedFormat):
    """an OpenType subtable (%s) had inconsistent formats between masters"""


class VarLibCFFMergeError(VarLibError):
    pass


class VarLibCFFDictMergeError(VarLibCFFMergeError):
    """Raised when a CFF PrivateDict cannot be merged."""

    def __init__(self, key, value, values):
        error_msg = (
            f"For the Private Dict key '{key}', the default font value list:"
            f"\n\t{value}\nhad a different number of values than a region font:"
        )
        for region_value in values:
            error_msg += f"\n\t{region_value}"
        self.args = (error_msg,)


class VarLibCFFPointTypeMergeError(VarLibCFFMergeError):
    """Raised when a CFF glyph cannot be merged because of point type differences."""

    def __init__(self, point_type, pt_index, m_index, default_type, glyph_name):
        error_msg = (
            f"Glyph '{glyph_name}': '{point_type}' at point index {pt_index} in "
            f"master index {m_index} differs from the default font point type "
            f"'{default_type}'"
        )
        self.args = (error_msg,)


class VarLibCFFHintTypeMergeError(VarLibCFFMergeError):
    """Raised when a CFF glyph cannot be merged because of hint type differences."""

    def __init__(self, hint_type, cmd_index, m_index, default_type, glyph_name):
        error_msg = (
            f"Glyph '{glyph_name}': '{hint_type}' at index {cmd_index} in "
            f"master index {m_index} differs from the default font hint type "
            f"'{default_type}'"
        )
        self.args = (error_msg,)


class VariationModelError(VarLibError):
    """Raised when a variation model is faulty."""

# === NexusCore/openenv\Lib\site-packages\grpc\framework\foundation\future.py ===
# Copyright 2015 gRPC authors.
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
"""A Future interface.

Python doesn't have a Future interface in its standard library. In the absence
of such a standard, three separate, incompatible implementations
(concurrent.futures.Future, ndb.Future, and asyncio.Future) have appeared. This
interface attempts to be as compatible as possible with
concurrent.futures.Future. From ndb.Future it adopts a traceback-object accessor
method.

Unlike the concrete and implemented Future classes listed above, the Future
class defined in this module is an entirely abstract interface that anyone may
implement and use.

The one known incompatibility between this interface and the interface of
concurrent.futures.Future is that this interface defines its own CancelledError
and TimeoutError exceptions rather than raising the implementation-private
concurrent.futures._base.CancelledError and the
built-in-but-only-in-3.3-and-later TimeoutError.
"""

import abc


class TimeoutError(Exception):
    """Indicates that a particular call timed out."""


class CancelledError(Exception):
    """Indicates that the computation underlying a Future was cancelled."""


class Future(abc.ABC):
    """A representation of a computation in another control flow.

    Computations represented by a Future may be yet to be begun, may be ongoing,
    or may have already completed.
    """

    # NOTE(nathaniel): This isn't the return type that I would want to have if it
    # were up to me. Were this interface being written from scratch, the return
    # type of this method would probably be a sum type like:
    #
    # NOT_COMMENCED
    # COMMENCED_AND_NOT_COMPLETED
    # PARTIAL_RESULT<Partial_Result_Type>
    # COMPLETED<Result_Type>
    # UNCANCELLABLE
    # NOT_IMMEDIATELY_DETERMINABLE
    @abc.abstractmethod
    def cancel(self):
        """Attempts to cancel the computation.

        This method does not block.

        Returns:
          True if the computation has not yet begun, will not be allowed to take
            place, and determination of both was possible without blocking. False
            under all other circumstances including but not limited to the
            computation's already having begun, the computation's already having
            finished, and the computation's having been scheduled for execution on a
            remote system for which a determination of whether or not it commenced
            before being cancelled cannot be made without blocking.
        """
        raise NotImplementedError()

    # NOTE(nathaniel): Here too this isn't the return type that I'd want this
    # method to have if it were up to me. I think I'd go with another sum type
    # like:
    #
    # NOT_CANCELLED (this object's cancel method hasn't been called)
    # NOT_COMMENCED
    # COMMENCED_AND_NOT_COMPLETED
    # PARTIAL_RESULT<Partial_Result_Type>
    # COMPLETED<Result_Type>
    # UNCANCELLABLE
    # NOT_IMMEDIATELY_DETERMINABLE
    #
    # Notice how giving the cancel method the right semantics obviates most
    # reasons for this method to exist.
    @abc.abstractmethod
    def cancelled(self):
        """Describes whether the computation was cancelled.

        This method does not block.

        Returns:
          True if the computation was cancelled any time before its result became
            immediately available. False under all other circumstances including but
            not limited to this object's cancel method not having been called and
            the computation's result having become immediately available.
        """
        raise NotImplementedError()

    @abc.abstractmethod
    def running(self):
        """Describes whether the computation is taking place.

        This method does not block.

        Returns:
          True if the computation is scheduled to take place in the future or is
            taking place now, or False if the computation took place in the past or
            was cancelled.
        """
        raise NotImplementedError()

    # NOTE(nathaniel): These aren't quite the semantics I'd like here either. I
    # would rather this only returned True in cases in which the underlying
    # computation completed successfully. A computation's having been cancelled
    # conflicts with considering that computation "done".
    @abc.abstractmethod
    def done(self):
        """Describes whether the computation has taken place.

        This method does not block.

        Returns:
          True if the computation is known to have either completed or have been
            unscheduled or interrupted. False if the computation may possibly be
            executing or scheduled to execute later.
        """
        raise NotImplementedError()

    @abc.abstractmethod
    def result(self, timeout=None):
        """Accesses the outcome of the computation or raises its exception.

        This method may return immediately or may block.

        Args:
          timeout: The length of time in seconds to wait for the computation to
            finish or be cancelled, or None if this method should block until the
            computation has finished or is cancelled no matter how long that takes.

        Returns:
          The return value of the computation.

        Raises:
          TimeoutError: If a timeout value is passed and the computation does not
            terminate within the allotted time.
          CancelledError: If the computation was cancelled.
          Exception: If the computation raised an exception, this call will raise
            the same exception.
        """
        raise NotImplementedError()

    @abc.abstractmethod
    def exception(self, timeout=None):
        """Return the exception raised by the computation.

        This method may return immediately or may block.

        Args:
          timeout: The length of time in seconds to wait for the computation to
            terminate or be cancelled, or None if this method should block until
            the computation is terminated or is cancelled no matter how long that
            takes.

        Returns:
          The exception raised by the computation, or None if the computation did
            not raise an exception.

        Raises:
          TimeoutError: If a timeout value is passed and the computation does not
            terminate within the allotted time.
          CancelledError: If the computation was cancelled.
        """
        raise NotImplementedError()

    @abc.abstractmethod
    def traceback(self, timeout=None):
        """Access the traceback of the exception raised by the computation.

        This method may return immediately or may block.

        Args:
          timeout: The length of time in seconds to wait for the computation to
            terminate or be cancelled, or None if this method should block until
            the computation is terminated or is cancelled no matter how long that
            takes.

        Returns:
          The traceback of the exception raised by the computation, or None if the
            computation did not raise an exception.

        Raises:
          TimeoutError: If a timeout value is passed and the computation does not
            terminate within the allotted time.
          CancelledError: If the computation was cancelled.
        """
        raise NotImplementedError()

    @abc.abstractmethod
    def add_done_callback(self, fn):
        """Adds a function to be called at completion of the computation.

        The callback will be passed this Future object describing the outcome of
        the computation.

        If the computation has already completed, the callback will be called
        immediately.

        Args:
          fn: A callable taking this Future object as its single parameter.
        """
        raise NotImplementedError()

# === NexusCore/openenv\Lib\site-packages\IPython\utils\_process_common.py ===
"""Common utilities for the various process_* implementations.

This file is only meant to be imported by the platform-specific implementations
of subprocess utilities, and it contains tools that are common to all of them.
"""

#-----------------------------------------------------------------------------
#  Copyright (C) 2010-2011  The IPython Development Team
#
#  Distributed under the terms of the BSD License.  The full license is in
#  the file COPYING, distributed as part of this software.
#-----------------------------------------------------------------------------

#-----------------------------------------------------------------------------
# Imports
#-----------------------------------------------------------------------------
import os
import shlex
import subprocess
import sys
from typing import IO, Any, Callable, List, Union

from IPython.utils import py3compat

#-----------------------------------------------------------------------------
# Function definitions
#-----------------------------------------------------------------------------

def read_no_interrupt(stream: IO[Any]) -> bytes:
    """Read from a pipe ignoring EINTR errors.

    This is necessary because when reading from pipes with GUI event loops
    running in the background, often interrupts are raised that stop the
    command from completing."""
    import errno

    try:
        return stream.read()
    except IOError as err:
        if err.errno != errno.EINTR:
            raise


def process_handler(
    cmd: Union[str, List[str]],
    callback: Callable[[subprocess.Popen], int | str | bytes],
    stderr=subprocess.PIPE,
) -> int | str | bytes:
    """Open a command in a shell subprocess and execute a callback.

    This function provides common scaffolding for creating subprocess.Popen()
    calls.  It creates a Popen object and then calls the callback with it.

    Parameters
    ----------
    cmd : str or list
        A command to be executed by the system, using :class:`subprocess.Popen`.
        If a string is passed, it will be run in the system shell. If a list is
        passed, it will be used directly as arguments.
    callback : callable
        A one-argument function that will be called with the Popen object.
    stderr : file descriptor number, optional
        By default this is set to ``subprocess.PIPE``, but you can also pass the
        value ``subprocess.STDOUT`` to force the subprocess' stderr to go into
        the same file descriptor as its stdout.  This is useful to read stdout
        and stderr combined in the order they are generated.

    Returns
    -------
    The return value of the provided callback is returned.
    """
    sys.stdout.flush()
    sys.stderr.flush()
    # On win32, close_fds can't be true when using pipes for stdin/out/err
    if sys.platform == "win32" and stderr != subprocess.PIPE:
        close_fds = False
    else:
        close_fds = True
    # Determine if cmd should be run with system shell.
    shell = isinstance(cmd, str)
    # On POSIX systems run shell commands with user-preferred shell.
    executable = None
    if shell and os.name == 'posix' and 'SHELL' in os.environ:
        executable = os.environ['SHELL']
    p = subprocess.Popen(cmd, shell=shell,
                         executable=executable,
                         stdin=subprocess.PIPE,
                         stdout=subprocess.PIPE,
                         stderr=stderr,
                         close_fds=close_fds)

    try:
        out = callback(p)
    except KeyboardInterrupt:
        print('^C')
        sys.stdout.flush()
        sys.stderr.flush()
        out = None
    finally:
        # Make really sure that we don't leave processes behind, in case the
        # call above raises an exception
        # We start by assuming the subprocess finished (to avoid NameErrors
        # later depending on the path taken)
        if p.returncode is None:
            try:
                p.terminate()
                p.poll()
            except OSError:
                pass
        # One last try on our way out
        if p.returncode is None:
            try:
                p.kill()
            except OSError:
                pass

    return out


def getoutput(cmd):
    """Run a command and return its stdout/stderr as a string.

    Parameters
    ----------
    cmd : str or list
        A command to be executed in the system shell.

    Returns
    -------
    output : str
        A string containing the combination of stdout and stderr from the
    subprocess, in whatever order the subprocess originally wrote to its
    file descriptors (so the order of the information in this string is the
    correct order as would be seen if running the command in a terminal).
    """
    out = process_handler(cmd, lambda p: p.communicate()[0], subprocess.STDOUT)
    if out is None:
        return ''
    assert isinstance(out, bytes)
    return py3compat.decode(out)


def getoutputerror(cmd):
    """Return (standard output, standard error) of executing cmd in a shell.

    Accepts the same arguments as os.system().

    Parameters
    ----------
    cmd : str or list
        A command to be executed in the system shell.

    Returns
    -------
    stdout : str
    stderr : str
    """
    return get_output_error_code(cmd)[:2]

def get_output_error_code(cmd):
    """Return (standard output, standard error, return code) of executing cmd
    in a shell.

    Accepts the same arguments as os.system().

    Parameters
    ----------
    cmd : str or list
        A command to be executed in the system shell.

    Returns
    -------
    stdout : str
    stderr : str
    returncode: int
    """

    out_err, p = process_handler(cmd, lambda p: (p.communicate(), p))
    if out_err is None:
        return '', '', p.returncode
    out, err = out_err
    return py3compat.decode(out), py3compat.decode(err), p.returncode

def arg_split(s, posix=False, strict=True):
    """Split a command line's arguments in a shell-like manner.

    This is a modified version of the standard library's shlex.split()
    function, but with a default of posix=False for splitting, so that quotes
    in inputs are respected.

    if strict=False, then any errors shlex.split would raise will result in the
    unparsed remainder being the last element of the list, rather than raising.
    This is because we sometimes use arg_split to parse things other than
    command-line args.
    """

    lex = shlex.shlex(s, posix=posix)
    lex.whitespace_split = True
    # Extract tokens, ensuring that things like leaving open quotes
    # does not cause this to raise.  This is important, because we
    # sometimes pass Python source through this (e.g. %timeit f(" ")),
    # and it shouldn't raise an exception.
    # It may be a bad idea to parse things that are not command-line args
    # through this function, but we do, so let's be safe about it.
    lex.commenters='' #fix for GH-1269
    tokens = []
    while True:
        try:
            tokens.append(next(lex))
        except StopIteration:
            break
        except ValueError:
            if strict:
                raise
            # couldn't parse, get remaining blob as last token
            tokens.append(lex.token)
            break

    return tokens

# === NexusCore/openenv\Lib\site-packages\IPython\terminal\pt_inputhooks\wx.py ===
"""Enable wxPython to be used interactively in prompt_toolkit
"""

import sys
import signal
import time
from timeit import default_timer as clock
import wx


def ignore_keyboardinterrupts(func):
    """Decorator which causes KeyboardInterrupt exceptions to be ignored during
    execution of the decorated function.

    This is used by the inputhook functions to handle the event where the user
    presses CTRL+C while IPython is idle, and the inputhook loop is running. In
    this case, we want to ignore interrupts.
    """
    def wrapper(*args, **kwargs):
        try:
            func(*args, **kwargs)
        except KeyboardInterrupt:
            pass
    return wrapper


@ignore_keyboardinterrupts
def inputhook_wx1(context):
    """Run the wx event loop by processing pending events only.

    This approach seems to work, but its performance is not great as it
    relies on having PyOS_InputHook called regularly.
    """
    app = wx.GetApp()
    if app is not None:
        assert wx.Thread_IsMain()

        # Make a temporary event loop and process system events until
        # there are no more waiting, then allow idle events (which
        # will also deal with pending or posted wx events.)
        evtloop = wx.EventLoop()
        ea = wx.EventLoopActivator(evtloop)
        while evtloop.Pending():
            evtloop.Dispatch()
        app.ProcessIdle()
        del ea
    return 0


class EventLoopTimer(wx.Timer):

    def __init__(self, func):
        self.func = func
        wx.Timer.__init__(self)

    def Notify(self):
        self.func()


class EventLoopRunner:

    def Run(self, time, input_is_ready):
        self.input_is_ready = input_is_ready
        self.evtloop = wx.EventLoop()
        self.timer = EventLoopTimer(self.check_stdin)
        self.timer.Start(time)
        self.evtloop.Run()

    def check_stdin(self):
        if self.input_is_ready():
            self.timer.Stop()
            self.evtloop.Exit()


@ignore_keyboardinterrupts
def inputhook_wx2(context):
    """Run the wx event loop, polling for stdin.

    This version runs the wx eventloop for an undetermined amount of time,
    during which it periodically checks to see if anything is ready on
    stdin.  If anything is ready on stdin, the event loop exits.

    The argument to elr.Run controls how often the event loop looks at stdin.
    This determines the responsiveness at the keyboard.  A setting of 1000
    enables a user to type at most 1 char per second.  I have found that a
    setting of 10 gives good keyboard response.  We can shorten it further,
    but eventually performance would suffer from calling select/kbhit too
    often.
    """
    app = wx.GetApp()
    if app is not None:
        assert wx.Thread_IsMain()
        elr = EventLoopRunner()
        # As this time is made shorter, keyboard response improves, but idle
        # CPU load goes up.  10 ms seems like a good compromise.
        elr.Run(time=10,  # CHANGE time here to control polling interval
                input_is_ready=context.input_is_ready)
    return 0


@ignore_keyboardinterrupts
def inputhook_wx3(context):
    """Run the wx event loop by processing pending events only.

    This is like inputhook_wx1, but it keeps processing pending events
    until stdin is ready.  After processing all pending events, a call to
    time.sleep is inserted.  This is needed, otherwise, CPU usage is at 100%.
    This sleep time should be tuned though for best performance.
    """
    app = wx.GetApp()
    if app is not None:
        assert wx.Thread_IsMain()

        # The import of wx on Linux sets the handler for signal.SIGINT
        # to 0.  This is a bug in wx or gtk.  We fix by just setting it
        # back to the Python default.
        if not callable(signal.getsignal(signal.SIGINT)):
            signal.signal(signal.SIGINT, signal.default_int_handler)

        evtloop = wx.EventLoop()
        ea = wx.EventLoopActivator(evtloop)
        t = clock()
        while not context.input_is_ready():
            while evtloop.Pending():
                t = clock()
                evtloop.Dispatch()
            app.ProcessIdle()
            # We need to sleep at this point to keep the idle CPU load
            # low.  However, if sleep to long, GUI response is poor.  As
            # a compromise, we watch how often GUI events are being processed
            # and switch between a short and long sleep time.  Here are some
            # stats useful in helping to tune this.
            # time    CPU load
            # 0.001   13%
            # 0.005   3%
            # 0.01    1.5%
            # 0.05    0.5%
            used_time = clock() - t
            if used_time > 10.0:
                # print('Sleep for 1 s')  # dbg
                time.sleep(1.0)
            elif used_time > 0.1:
                # Few GUI events coming in, so we can sleep longer
                # print('Sleep for 0.05 s')  # dbg
                time.sleep(0.05)
            else:
                # Many GUI events coming in, so sleep only very little
                time.sleep(0.001)
        del ea
    return 0


@ignore_keyboardinterrupts
def inputhook_wxphoenix(context):
    """Run the wx event loop until the user provides more input.

    This input hook is suitable for use with wxPython >= 4 (a.k.a. Phoenix).

    It uses the same approach to that used in
    ipykernel.eventloops.loop_wx. The wx.MainLoop is executed, and a wx.Timer
    is used to periodically poll the context for input. As soon as input is
    ready, the wx.MainLoop is stopped.
    """

    app = wx.GetApp()

    if app is None:
        return

    if context.input_is_ready():
        return

    assert wx.IsMainThread()

    # Wx uses milliseconds
    poll_interval = 100

    # Use a wx.Timer to periodically check whether input is ready - as soon as
    # it is, we exit the main loop
    timer = wx.Timer()

    def poll(ev):
        if context.input_is_ready():
            timer.Stop()
            app.ExitMainLoop()

    timer.Start(poll_interval)
    timer.Bind(wx.EVT_TIMER, poll)

    # The import of wx on Linux sets the handler for signal.SIGINT to 0.  This
    # is a bug in wx or gtk.  We fix by just setting it back to the Python
    # default.
    if not callable(signal.getsignal(signal.SIGINT)):
        signal.signal(signal.SIGINT, signal.default_int_handler)

    # The SetExitOnFrameDelete call allows us to run the wx mainloop without
    # having a frame open.
    app.SetExitOnFrameDelete(False)
    app.MainLoop()


# Get the major wx version number to figure out what input hook we should use.
major_version = 3

try:
    major_version = int(wx.__version__[0])
except Exception:
    pass

# Use the phoenix hook on all platforms for wxpython >= 4
if major_version >= 4:
    inputhook = inputhook_wxphoenix
# On OSX, evtloop.Pending() always returns True, regardless of there being
# any events pending. As such we can't use implementations 1 or 3 of the
# inputhook as those depend on a pending/dispatch loop.
elif sys.platform == 'darwin':
    inputhook = inputhook_wx2
else:
    inputhook = inputhook_wx3

# === NexusCore/openenv\Lib\site-packages\mpl_toolkits\mplot3d\proj3d.py ===
"""
Various transforms used for by the 3D code
"""

import numpy as np

from matplotlib import _api


def world_transformation(xmin, xmax,
                         ymin, ymax,
                         zmin, zmax, pb_aspect=None):
    """
    Produce a matrix that scales homogeneous coords in the specified ranges
    to [0, 1], or [0, pb_aspect[i]] if the plotbox aspect ratio is specified.
    """
    dx = xmax - xmin
    dy = ymax - ymin
    dz = zmax - zmin
    if pb_aspect is not None:
        ax, ay, az = pb_aspect
        dx /= ax
        dy /= ay
        dz /= az

    return np.array([[1/dx,    0,    0, -xmin/dx],
                     [   0, 1/dy,    0, -ymin/dy],
                     [   0,    0, 1/dz, -zmin/dz],
                     [   0,    0,    0,        1]])


def _rotation_about_vector(v, angle):
    """
    Produce a rotation matrix for an angle in radians about a vector.
    """
    vx, vy, vz = v / np.linalg.norm(v)
    s = np.sin(angle)
    c = np.cos(angle)
    t = 2*np.sin(angle/2)**2  # more numerically stable than t = 1-c

    R = np.array([
        [t*vx*vx + c,    t*vx*vy - vz*s, t*vx*vz + vy*s],
        [t*vy*vx + vz*s, t*vy*vy + c,    t*vy*vz - vx*s],
        [t*vz*vx - vy*s, t*vz*vy + vx*s, t*vz*vz + c]])

    return R


def _view_axes(E, R, V, roll):
    """
    Get the unit viewing axes in data coordinates.

    Parameters
    ----------
    E : 3-element numpy array
        The coordinates of the eye/camera.
    R : 3-element numpy array
        The coordinates of the center of the view box.
    V : 3-element numpy array
        Unit vector in the direction of the vertical axis.
    roll : float
        The roll angle in radians.

    Returns
    -------
    u : 3-element numpy array
        Unit vector pointing towards the right of the screen.
    v : 3-element numpy array
        Unit vector pointing towards the top of the screen.
    w : 3-element numpy array
        Unit vector pointing out of the screen.
    """
    w = (E - R)
    w = w/np.linalg.norm(w)
    u = np.cross(V, w)
    u = u/np.linalg.norm(u)
    v = np.cross(w, u)  # Will be a unit vector

    # Save some computation for the default roll=0
    if roll != 0:
        # A positive rotation of the camera is a negative rotation of the world
        Rroll = _rotation_about_vector(w, -roll)
        u = np.dot(Rroll, u)
        v = np.dot(Rroll, v)
    return u, v, w


def _view_transformation_uvw(u, v, w, E):
    """
    Return the view transformation matrix.

    Parameters
    ----------
    u : 3-element numpy array
        Unit vector pointing towards the right of the screen.
    v : 3-element numpy array
        Unit vector pointing towards the top of the screen.
    w : 3-element numpy array
        Unit vector pointing out of the screen.
    E : 3-element numpy array
        The coordinates of the eye/camera.
    """
    Mr = np.eye(4)
    Mt = np.eye(4)
    Mr[:3, :3] = [u, v, w]
    Mt[:3, -1] = -E
    M = np.dot(Mr, Mt)
    return M


def _persp_transformation(zfront, zback, focal_length):
    e = focal_length
    a = 1  # aspect ratio
    b = (zfront+zback)/(zfront-zback)
    c = -2*(zfront*zback)/(zfront-zback)
    proj_matrix = np.array([[e,   0,  0, 0],
                            [0, e/a,  0, 0],
                            [0,   0,  b, c],
                            [0,   0, -1, 0]])
    return proj_matrix


def _ortho_transformation(zfront, zback):
    # note: w component in the resulting vector will be (zback-zfront), not 1
    a = -(zfront + zback)
    b = -(zfront - zback)
    proj_matrix = np.array([[2, 0,  0, 0],
                            [0, 2,  0, 0],
                            [0, 0, -2, 0],
                            [0, 0,  a, b]])
    return proj_matrix


def _proj_transform_vec(vec, M):
    vecw = np.dot(M, vec.data)
    w = vecw[3]
    txs, tys, tzs = vecw[0]/w, vecw[1]/w, vecw[2]/w
    if np.ma.isMA(vec[0]):  # we check each to protect for scalars
        txs = np.ma.array(txs, mask=vec[0].mask)
    if np.ma.isMA(vec[1]):
        tys = np.ma.array(tys, mask=vec[1].mask)
    if np.ma.isMA(vec[2]):
        tzs = np.ma.array(tzs, mask=vec[2].mask)
    return txs, tys, tzs


def _proj_transform_vec_clip(vec, M, focal_length):
    vecw = np.dot(M, vec.data)
    w = vecw[3]
    txs, tys, tzs = vecw[0] / w, vecw[1] / w, vecw[2] / w
    if np.isinf(focal_length):  # don't clip orthographic projection
        tis = np.ones(txs.shape, dtype=bool)
    else:
        tis = (-1 <= txs) & (txs <= 1) & (-1 <= tys) & (tys <= 1) & (tzs <= 0)
    if np.ma.isMA(vec[0]):
        tis = tis & ~vec[0].mask
    if np.ma.isMA(vec[1]):
        tis = tis & ~vec[1].mask
    if np.ma.isMA(vec[2]):
        tis = tis & ~vec[2].mask

    txs = np.ma.masked_array(txs, ~tis)
    tys = np.ma.masked_array(tys, ~tis)
    tzs = np.ma.masked_array(tzs, ~tis)
    return txs, tys, tzs, tis


def inv_transform(xs, ys, zs, invM):
    """
    Transform the points by the inverse of the projection matrix, *invM*.
    """
    vec = _vec_pad_ones(xs, ys, zs)
    vecr = np.dot(invM, vec)
    if vecr.shape == (4,):
        vecr = vecr.reshape((4, 1))
    for i in range(vecr.shape[1]):
        if vecr[3][i] != 0:
            vecr[:, i] = vecr[:, i] / vecr[3][i]
    return vecr[0], vecr[1], vecr[2]


def _vec_pad_ones(xs, ys, zs):
    if np.ma.isMA(xs) or np.ma.isMA(ys) or np.ma.isMA(zs):
        return np.ma.array([xs, ys, zs, np.ones_like(xs)])
    else:
        return np.array([xs, ys, zs, np.ones_like(xs)])


def proj_transform(xs, ys, zs, M):
    """
    Transform the points by the projection matrix *M*.
    """
    vec = _vec_pad_ones(xs, ys, zs)
    return _proj_transform_vec(vec, M)


@_api.deprecated("3.10")
def proj_transform_clip(xs, ys, zs, M):
    return _proj_transform_clip(xs, ys, zs, M, focal_length=np.inf)


def _proj_transform_clip(xs, ys, zs, M, focal_length):
    """
    Transform the points by the projection matrix
    and return the clipping result
    returns txs, tys, tzs, tis
    """
    vec = _vec_pad_ones(xs, ys, zs)
    return _proj_transform_vec_clip(vec, M, focal_length)


def _proj_points(points, M):
    return np.column_stack(_proj_trans_points(points, M))


def _proj_trans_points(points, M):
    points = np.asanyarray(points)
    xs, ys, zs = points[:, 0], points[:, 1], points[:, 2]
    return proj_transform(xs, ys, zs, M)

# === NexusCore/openenv\Lib\site-packages\nltk\cluster\em.py ===
# Natural Language Toolkit: Expectation Maximization Clusterer
#
# Copyright (C) 2001-2024 NLTK Project
# Author: Trevor Cohn <tacohn@cs.mu.oz.au>
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT

try:
    import numpy
except ImportError:
    pass

from nltk.cluster.util import VectorSpaceClusterer


class EMClusterer(VectorSpaceClusterer):
    """
    The Gaussian EM clusterer models the vectors as being produced by
    a mixture of k Gaussian sources. The parameters of these sources
    (prior probability, mean and covariance matrix) are then found to
    maximise the likelihood of the given data. This is done with the
    expectation maximisation algorithm. It starts with k arbitrarily
    chosen means, priors and covariance matrices. It then calculates
    the membership probabilities for each vector in each of the
    clusters; this is the 'E' step. The cluster parameters are then
    updated in the 'M' step using the maximum likelihood estimate from
    the cluster membership probabilities. This process continues until
    the likelihood of the data does not significantly increase.
    """

    def __init__(
        self,
        initial_means,
        priors=None,
        covariance_matrices=None,
        conv_threshold=1e-6,
        bias=0.1,
        normalise=False,
        svd_dimensions=None,
    ):
        """
        Creates an EM clusterer with the given starting parameters,
        convergence threshold and vector mangling parameters.

        :param  initial_means: the means of the gaussian cluster centers
        :type   initial_means: [seq of] numpy array or seq of SparseArray
        :param  priors: the prior probability for each cluster
        :type   priors: numpy array or seq of float
        :param  covariance_matrices: the covariance matrix for each cluster
        :type   covariance_matrices: [seq of] numpy array
        :param  conv_threshold: maximum change in likelihood before deemed
                    convergent
        :type   conv_threshold: int or float
        :param  bias: variance bias used to ensure non-singular covariance
                      matrices
        :type   bias: float
        :param  normalise:  should vectors be normalised to length 1
        :type   normalise:  boolean
        :param  svd_dimensions: number of dimensions to use in reducing vector
                               dimensionsionality with SVD
        :type   svd_dimensions: int
        """
        VectorSpaceClusterer.__init__(self, normalise, svd_dimensions)
        self._means = numpy.array(initial_means, numpy.float64)
        self._num_clusters = len(initial_means)
        self._conv_threshold = conv_threshold
        self._covariance_matrices = covariance_matrices
        self._priors = priors
        self._bias = bias

    def num_clusters(self):
        return self._num_clusters

    def cluster_vectorspace(self, vectors, trace=False):
        assert len(vectors) > 0

        # set the parameters to initial values
        dimensions = len(vectors[0])
        means = self._means
        priors = self._priors
        if not priors:
            priors = self._priors = (
                numpy.ones(self._num_clusters, numpy.float64) / self._num_clusters
            )
        covariances = self._covariance_matrices
        if not covariances:
            covariances = self._covariance_matrices = [
                numpy.identity(dimensions, numpy.float64)
                for i in range(self._num_clusters)
            ]

        # do the E and M steps until the likelihood plateaus
        lastl = self._loglikelihood(vectors, priors, means, covariances)
        converged = False

        while not converged:
            if trace:
                print("iteration; loglikelihood", lastl)
            # E-step, calculate hidden variables, h[i,j]
            h = numpy.zeros((len(vectors), self._num_clusters), numpy.float64)
            for i in range(len(vectors)):
                for j in range(self._num_clusters):
                    h[i, j] = priors[j] * self._gaussian(
                        means[j], covariances[j], vectors[i]
                    )
                h[i, :] /= sum(h[i, :])

            # M-step, update parameters - cvm, p, mean
            for j in range(self._num_clusters):
                covariance_before = covariances[j]
                new_covariance = numpy.zeros((dimensions, dimensions), numpy.float64)
                new_mean = numpy.zeros(dimensions, numpy.float64)
                sum_hj = 0.0
                for i in range(len(vectors)):
                    delta = vectors[i] - means[j]
                    new_covariance += h[i, j] * numpy.multiply.outer(delta, delta)
                    sum_hj += h[i, j]
                    new_mean += h[i, j] * vectors[i]
                covariances[j] = new_covariance / sum_hj
                means[j] = new_mean / sum_hj
                priors[j] = sum_hj / len(vectors)

                # bias term to stop covariance matrix being singular
                covariances[j] += self._bias * numpy.identity(dimensions, numpy.float64)

            # calculate likelihood - FIXME: may be broken
            l = self._loglikelihood(vectors, priors, means, covariances)

            # check for convergence
            if abs(lastl - l) < self._conv_threshold:
                converged = True
            lastl = l

    def classify_vectorspace(self, vector):
        best = None
        for j in range(self._num_clusters):
            p = self._priors[j] * self._gaussian(
                self._means[j], self._covariance_matrices[j], vector
            )
            if not best or p > best[0]:
                best = (p, j)
        return best[1]

    def likelihood_vectorspace(self, vector, cluster):
        cid = self.cluster_names().index(cluster)
        return self._priors[cluster] * self._gaussian(
            self._means[cluster], self._covariance_matrices[cluster], vector
        )

    def _gaussian(self, mean, cvm, x):
        m = len(mean)
        assert cvm.shape == (m, m), "bad sized covariance matrix, %s" % str(cvm.shape)
        try:
            det = numpy.linalg.det(cvm)
            inv = numpy.linalg.inv(cvm)
            a = det**-0.5 * (2 * numpy.pi) ** (-m / 2.0)
            dx = x - mean
            print(dx, inv)
            b = -0.5 * numpy.dot(numpy.dot(dx, inv), dx)
            return a * numpy.exp(b)
        except OverflowError:
            # happens when the exponent is negative infinity - i.e. b = 0
            # i.e. the inverse of cvm is huge (cvm is almost zero)
            return 0

    def _loglikelihood(self, vectors, priors, means, covariances):
        llh = 0.0
        for vector in vectors:
            p = 0
            for j in range(len(priors)):
                p += priors[j] * self._gaussian(means[j], covariances[j], vector)
            llh += numpy.log(p)
        return llh

    def __repr__(self):
        return "<EMClusterer means=%s>" % list(self._means)


def demo():
    """
    Non-interactive demonstration of the clusterers with simple 2-D data.
    """

    from nltk import cluster

    # example from figure 14.10, page 519, Manning and Schutze

    vectors = [numpy.array(f) for f in [[0.5, 0.5], [1.5, 0.5], [1, 3]]]
    means = [[4, 2], [4, 2.01]]

    clusterer = cluster.EMClusterer(means, bias=0.1)
    clusters = clusterer.cluster(vectors, True, trace=True)

    print("Clustered:", vectors)
    print("As:       ", clusters)
    print()

    for c in range(2):
        print("Cluster:", c)
        print("Prior:  ", clusterer._priors[c])
        print("Mean:   ", clusterer._means[c])
        print("Covar:  ", clusterer._covariance_matrices[c])
        print()

    # classify a new vector
    vector = numpy.array([2, 2])
    print("classify(%s):" % vector, end=" ")
    print(clusterer.classify(vector))

    # show the classification probabilities
    vector = numpy.array([2, 2])
    print("classification_probdist(%s):" % vector)
    pdist = clusterer.classification_probdist(vector)
    for sample in pdist.samples():
        print(f"{sample} => {pdist.prob(sample) * 100:.0f}%")


if __name__ == "__main__":
    demo()

# === NexusCore/openenv\Lib\site-packages\win32comext\authorization\demos\EditServiceSecurity.py ===
r"""
Implements a permissions editor for services.
Service can be specified as plain name for local machine,
or as a remote service of the form \\machinename\service
"""

import os

import pythoncom
import win32com.server.policy
import win32con
import win32security
import win32service
from win32com.authorization import authorization

SERVICE_GENERIC_EXECUTE = (
    win32service.SERVICE_START
    | win32service.SERVICE_STOP
    | win32service.SERVICE_PAUSE_CONTINUE
    | win32service.SERVICE_USER_DEFINED_CONTROL
)
SERVICE_GENERIC_READ = (
    win32service.SERVICE_QUERY_CONFIG
    | win32service.SERVICE_QUERY_STATUS
    | win32service.SERVICE_INTERROGATE
    | win32service.SERVICE_ENUMERATE_DEPENDENTS
)
SERVICE_GENERIC_WRITE = win32service.SERVICE_CHANGE_CONFIG

from ntsecuritycon import (
    READ_CONTROL,
    SI_ACCESS_GENERAL,
    SI_ACCESS_SPECIFIC,
    SI_ADVANCED,
    SI_EDIT_ALL,
    SI_PAGE_TITLE,
    SI_RESET,
    WRITE_DAC,
    WRITE_OWNER,
)
from pythoncom import IID_NULL


class ServiceSecurity(win32com.server.policy.DesignatedWrapPolicy):
    _com_interfaces_ = [authorization.IID_ISecurityInformation]
    _public_methods_ = [
        "GetObjectInformation",
        "GetSecurity",
        "SetSecurity",
        "GetAccessRights",
        "GetInheritTypes",
        "MapGeneric",
        "PropertySheetPageCallback",
    ]

    def __init__(self, ServiceName):
        self.ServiceName = ServiceName
        self._wrap_(self)

    def GetObjectInformation(self):
        """Identifies object whose security will be modified, and determines options available
        to the end user"""
        flags = SI_ADVANCED | SI_EDIT_ALL | SI_PAGE_TITLE | SI_RESET
        hinstance = 0  ## handle to module containing string resources
        servername = ""  ## name of authenticating server if not local machine

        ## service name can contain remote machine name of the form \\Server\ServiceName
        objectname = os.path.split(self.ServiceName)[1]
        pagetitle = "Service Permissions for " + self.ServiceName
        objecttype = IID_NULL
        return flags, hinstance, servername, objectname, pagetitle, objecttype

    def GetSecurity(self, requestedinfo, bdefault):
        """Requests the existing permissions for object"""
        if bdefault:
            return win32security.SECURITY_DESCRIPTOR()
        else:
            return win32security.GetNamedSecurityInfo(
                self.ServiceName, win32security.SE_SERVICE, requestedinfo
            )

    def SetSecurity(self, requestedinfo, sd):
        """Applies permissions to the object"""
        owner = sd.GetSecurityDescriptorOwner()
        group = sd.GetSecurityDescriptorGroup()
        dacl = sd.GetSecurityDescriptorDacl()
        sacl = sd.GetSecurityDescriptorSacl()
        win32security.SetNamedSecurityInfo(
            self.ServiceName,
            win32security.SE_SERVICE,
            requestedinfo,
            owner,
            group,
            dacl,
            sacl,
        )

    def GetAccessRights(self, objecttype, flags):
        """Returns a tuple of (AccessRights, DefaultAccess), where AccessRights is a sequence of tuples representing
        SI_ACCESS structs, containing (guid, access mask, Name, flags). DefaultAccess indicates which of the
        AccessRights will be used initially when a new ACE is added (zero based).
        Flags can contain SI_ACCESS_SPECIFIC,SI_ACCESS_GENERAL,SI_ACCESS_CONTAINER,SI_ACCESS_PROPERTY,
              CONTAINER_INHERIT_ACE,INHERIT_ONLY_ACE,OBJECT_INHERIT_ACE
        """
        ## input flags: SI_ADVANCED,SI_EDIT_AUDITS,SI_EDIT_PROPERTIES indicating which property sheet is requesting the rights
        if (objecttype is not None) and (objecttype != IID_NULL):
            ## Not relevent for services
            raise NotImplementedError("Object type is not supported")

        ## ???? for some reason, the DACL for a service will not retain ACCESS_SYSTEM_SECURITY in an ACE ????
        ## (IID_NULL, win32con.ACCESS_SYSTEM_SECURITY, 'View/change audit settings', SI_ACCESS_SPECIFIC),

        accessrights = [
            (
                IID_NULL,
                win32service.SERVICE_ALL_ACCESS,
                "Full control",
                SI_ACCESS_GENERAL,
            ),
            (IID_NULL, SERVICE_GENERIC_READ, "Generic read", SI_ACCESS_GENERAL),
            (IID_NULL, SERVICE_GENERIC_WRITE, "Generic write", SI_ACCESS_GENERAL),
            (
                IID_NULL,
                SERVICE_GENERIC_EXECUTE,
                "Start/Stop/Pause service",
                SI_ACCESS_GENERAL,
            ),
            (IID_NULL, READ_CONTROL, "Read Permissions", SI_ACCESS_GENERAL),
            (IID_NULL, WRITE_DAC, "Change permissions", SI_ACCESS_GENERAL),
            (IID_NULL, WRITE_OWNER, "Change owner", SI_ACCESS_GENERAL),
            (IID_NULL, win32con.DELETE, "Delete service", SI_ACCESS_GENERAL),
            (IID_NULL, win32service.SERVICE_START, "Start service", SI_ACCESS_SPECIFIC),
            (IID_NULL, win32service.SERVICE_STOP, "Stop service", SI_ACCESS_SPECIFIC),
            (
                IID_NULL,
                win32service.SERVICE_PAUSE_CONTINUE,
                "Pause/unpause service",
                SI_ACCESS_SPECIFIC,
            ),
            (
                IID_NULL,
                win32service.SERVICE_USER_DEFINED_CONTROL,
                "Execute user defined operations",
                SI_ACCESS_SPECIFIC,
            ),
            (
                IID_NULL,
                win32service.SERVICE_QUERY_CONFIG,
                "Read configuration",
                SI_ACCESS_SPECIFIC,
            ),
            (
                IID_NULL,
                win32service.SERVICE_CHANGE_CONFIG,
                "Change configuration",
                SI_ACCESS_SPECIFIC,
            ),
            (
                IID_NULL,
                win32service.SERVICE_ENUMERATE_DEPENDENTS,
                "List dependent services",
                SI_ACCESS_SPECIFIC,
            ),
            (
                IID_NULL,
                win32service.SERVICE_QUERY_STATUS,
                "Query status",
                SI_ACCESS_SPECIFIC,
            ),
            (
                IID_NULL,
                win32service.SERVICE_INTERROGATE,
                "Query status (immediate)",
                SI_ACCESS_SPECIFIC,
            ),
        ]
        return (accessrights, 0)

    def MapGeneric(self, guid, aceflags, mask):
        """Converts generic access rights to specific rights."""
        return win32security.MapGenericMask(
            mask,
            (
                SERVICE_GENERIC_READ,
                SERVICE_GENERIC_WRITE,
                SERVICE_GENERIC_EXECUTE,
                win32service.SERVICE_ALL_ACCESS,
            ),
        )

    def GetInheritTypes(self):
        """Specifies which types of ACE inheritance are supported.
        Services don't use any inheritance
        """
        return ((IID_NULL, 0, "Only current object"),)

    def PropertySheetPageCallback(self, hwnd, msg, pagetype):
        """Invoked each time a property sheet page is created or destroyed."""
        ## page types from SI_PAGE_TYPE enum: SI_PAGE_PERM SI_PAGE_ADVPERM SI_PAGE_AUDIT SI_PAGE_OWNER
        ## msg: PSPCB_CREATE, PSPCB_RELEASE, PSPCB_SI_INITDIALOG
        return None

    def EditSecurity(self, owner_hwnd=0):
        """Creates an ACL editor dialog based on parameters returned by interface methods"""
        isi = pythoncom.WrapObject(
            self, authorization.IID_ISecurityInformation, pythoncom.IID_IUnknown
        )
        authorization.EditSecurity(owner_hwnd, isi)


if __name__ == "__main__":
    # Find the first service on local machine and edit its permissions
    scm = win32service.OpenSCManager(
        None, None, win32service.SC_MANAGER_ENUMERATE_SERVICE
    )
    svcs = win32service.EnumServicesStatus(scm)
    win32service.CloseServiceHandle(scm)
    si = ServiceSecurity(svcs[0][0])
    si.EditSecurity()

# === NexusCore/openenv\Lib\site-packages\anyio\to_interpreter.py ===
from __future__ import annotations

import atexit
import os
import pickle
import sys
from collections import deque
from collections.abc import Callable
from textwrap import dedent
from typing import Any, Final, TypeVar

from . import current_time, to_thread
from ._core._exceptions import BrokenWorkerIntepreter
from ._core._synchronization import CapacityLimiter
from .lowlevel import RunVar

if sys.version_info >= (3, 11):
    from typing import TypeVarTuple, Unpack
else:
    from typing_extensions import TypeVarTuple, Unpack

UNBOUND: Final = 2  # I have no clue how this works, but it was used in the stdlib
FMT_UNPICKLED: Final = 0
FMT_PICKLED: Final = 1
DEFAULT_CPU_COUNT: Final = 8  # this is just an arbitrarily selected value
MAX_WORKER_IDLE_TIME = (
    30  # seconds a subinterpreter can be idle before becoming eligible for pruning
)

T_Retval = TypeVar("T_Retval")
PosArgsT = TypeVarTuple("PosArgsT")

_idle_workers = RunVar[deque["Worker"]]("_available_workers")
_default_interpreter_limiter = RunVar[CapacityLimiter]("_default_interpreter_limiter")


class Worker:
    _run_func = compile(
        dedent("""
        import _interpqueues as queues
        import _interpreters as interpreters
        from pickle import loads, dumps, HIGHEST_PROTOCOL

        item = queues.get(queue_id)[0]
        try:
            func, args = loads(item)
            retval = func(*args)
        except BaseException as exc:
            is_exception = True
            retval = exc
        else:
            is_exception = False

        try:
            queues.put(queue_id, (retval, is_exception), FMT_UNPICKLED, UNBOUND)
        except interpreters.NotShareableError:
            retval = dumps(retval, HIGHEST_PROTOCOL)
            queues.put(queue_id, (retval, is_exception), FMT_PICKLED, UNBOUND)
        """),
        "<string>",
        "exec",
    )

    last_used: float = 0

    _initialized: bool = False
    _interpreter_id: int
    _queue_id: int

    def initialize(self) -> None:
        import _interpqueues as queues
        import _interpreters as interpreters

        self._interpreter_id = interpreters.create()
        self._queue_id = queues.create(2, FMT_UNPICKLED, UNBOUND)
        self._initialized = True
        interpreters.set___main___attrs(
            self._interpreter_id,
            {
                "queue_id": self._queue_id,
                "FMT_PICKLED": FMT_PICKLED,
                "FMT_UNPICKLED": FMT_UNPICKLED,
                "UNBOUND": UNBOUND,
            },
        )

    def destroy(self) -> None:
        import _interpqueues as queues
        import _interpreters as interpreters

        if self._initialized:
            interpreters.destroy(self._interpreter_id)
            queues.destroy(self._queue_id)

    def _call(
        self,
        func: Callable[..., T_Retval],
        args: tuple[Any],
    ) -> tuple[Any, bool]:
        import _interpqueues as queues
        import _interpreters as interpreters

        if not self._initialized:
            self.initialize()

        payload = pickle.dumps((func, args), pickle.HIGHEST_PROTOCOL)
        queues.put(self._queue_id, payload, FMT_PICKLED, UNBOUND)

        res: Any
        is_exception: bool
        if exc_info := interpreters.exec(self._interpreter_id, self._run_func):
            raise BrokenWorkerIntepreter(exc_info)

        (res, is_exception), fmt = queues.get(self._queue_id)[:2]
        if fmt == FMT_PICKLED:
            res = pickle.loads(res)

        return res, is_exception

    async def call(
        self,
        func: Callable[..., T_Retval],
        args: tuple[Any],
        limiter: CapacityLimiter,
    ) -> T_Retval:
        result, is_exception = await to_thread.run_sync(
            self._call,
            func,
            args,
            limiter=limiter,
        )
        if is_exception:
            raise result

        return result


def _stop_workers(workers: deque[Worker]) -> None:
    for worker in workers:
        worker.destroy()

    workers.clear()


async def run_sync(
    func: Callable[[Unpack[PosArgsT]], T_Retval],
    *args: Unpack[PosArgsT],
    limiter: CapacityLimiter | None = None,
) -> T_Retval:
    """
    Call the given function with the given arguments in a subinterpreter.

    If the ``cancellable`` option is enabled and the task waiting for its completion is
    cancelled, the call will still run its course but its return value (or any raised
    exception) will be ignored.

    .. warning:: This feature is **experimental**. The upstream interpreter API has not
        yet been finalized or thoroughly tested, so don't rely on this for anything
        mission critical.

    :param func: a callable
    :param args: positional arguments for the callable
    :param limiter: capacity limiter to use to limit the total amount of subinterpreters
        running (if omitted, the default limiter is used)
    :return: the result of the call
    :raises BrokenWorkerIntepreter: if there's an internal error in a subinterpreter

    """
    if sys.version_info <= (3, 13):
        raise RuntimeError("subinterpreters require at least Python 3.13")

    if limiter is None:
        limiter = current_default_interpreter_limiter()

    try:
        idle_workers = _idle_workers.get()
    except LookupError:
        idle_workers = deque()
        _idle_workers.set(idle_workers)
        atexit.register(_stop_workers, idle_workers)

    async with limiter:
        try:
            worker = idle_workers.pop()
        except IndexError:
            worker = Worker()

    try:
        return await worker.call(func, args, limiter)
    finally:
        # Prune workers that have been idle for too long
        now = current_time()
        while idle_workers:
            if now - idle_workers[0].last_used <= MAX_WORKER_IDLE_TIME:
                break

            await to_thread.run_sync(idle_workers.popleft().destroy, limiter=limiter)

        worker.last_used = current_time()
        idle_workers.append(worker)


def current_default_interpreter_limiter() -> CapacityLimiter:
    """
    Return the capacity limiter that is used by default to limit the number of
    concurrently running subinterpreters.

    Defaults to the number of CPU cores.

    :return: a capacity limiter object

    """
    try:
        return _default_interpreter_limiter.get()
    except LookupError:
        limiter = CapacityLimiter(os.cpu_count() or DEFAULT_CPU_COUNT)
        _default_interpreter_limiter.set(limiter)
        return limiter

# === NexusCore/openenv\Lib\site-packages\send2trash\plat_other.py ===
# Copyright 2017 Virgil Dupras

# This software is licensed under the "BSD" License as described in the "LICENSE" file,
# which should be included with this package. The terms are also available at
# http://www.hardcoded.net/licenses/bsd_license

# This is a reimplementation of plat_other.py with reference to the
# freedesktop.org trash specification:
#   [1] http://www.freedesktop.org/wiki/Specifications/trash-spec
#   [2] http://www.ramendik.ru/docs/trashspec.html
# See also:
#   [3] http://standards.freedesktop.org/basedir-spec/basedir-spec-latest.html
#
# For external volumes this implementation will raise an exception if it can't
# find or create the user's trash directory.

from __future__ import unicode_literals

import errno
import sys
import os
import shutil
import os.path as op
from datetime import datetime
import stat

try:
    from urllib.parse import quote
except ImportError:
    # Python 2
    from urllib import quote

from send2trash.compat import text_type, environb
from send2trash.util import preprocess_paths
from send2trash.exceptions import TrashPermissionError

try:
    fsencode = os.fsencode  # Python 3
    fsdecode = os.fsdecode
except AttributeError:

    def fsencode(u):  # Python 2
        return u.encode(sys.getfilesystemencoding())

    def fsdecode(b):
        return b.decode(sys.getfilesystemencoding())

    # The Python 3 versions are a bit smarter, handling surrogate escapes,
    # but these should work in most cases.

FILES_DIR = b"files"
INFO_DIR = b"info"
INFO_SUFFIX = b".trashinfo"

# Default of ~/.local/share [3]
XDG_DATA_HOME = op.expanduser(environb.get(b"XDG_DATA_HOME", b"~/.local/share"))
HOMETRASH_B = op.join(XDG_DATA_HOME, b"Trash")
HOMETRASH = fsdecode(HOMETRASH_B)

uid = os.getuid()
TOPDIR_TRASH = b".Trash"
TOPDIR_FALLBACK = b".Trash-" + text_type(uid).encode("ascii")


def is_parent(parent, path):
    path = op.realpath(path)  # In case it's a symlink
    if isinstance(path, text_type):
        path = fsencode(path)
    parent = op.realpath(parent)
    if isinstance(parent, text_type):
        parent = fsencode(parent)
    return path.startswith(parent)


def format_date(date):
    return date.strftime("%Y-%m-%dT%H:%M:%S")


def info_for(src, topdir):
    # ...it MUST not include a ".." directory, and for files not "under" that
    # directory, absolute pathnames must be used. [2]
    if topdir is None or not is_parent(topdir, src):
        src = op.abspath(src)
    else:
        src = op.relpath(src, topdir)

    info = "[Trash Info]\n"
    info += "Path=" + quote(src) + "\n"
    info += "DeletionDate=" + format_date(datetime.now()) + "\n"
    return info


def check_create(dir):
    # use 0700 for paths [3]
    if not op.exists(dir):
        os.makedirs(dir, 0o700)


def trash_move(src, dst, topdir=None, cross_dev=False):
    filename = op.basename(src)
    filespath = op.join(dst, FILES_DIR)
    infopath = op.join(dst, INFO_DIR)
    base_name, ext = op.splitext(filename)

    counter = 0
    destname = filename
    while op.exists(op.join(filespath, destname)) or op.exists(op.join(infopath, destname + INFO_SUFFIX)):
        counter += 1
        destname = base_name + b" " + text_type(counter).encode("ascii") + ext

    check_create(filespath)
    check_create(infopath)

    with open(op.join(infopath, destname + INFO_SUFFIX), "w") as f:
        f.write(info_for(src, topdir))
    destpath = op.join(filespath, destname)
    if cross_dev:
        shutil.move(fsdecode(src), fsdecode(destpath))
    else:
        os.rename(src, destpath)


def find_mount_point(path):
    # Even if something's wrong, "/" is a mount point, so the loop will exit.
    # Use realpath in case it's a symlink
    path = op.realpath(path)  # Required to avoid infinite loop
    while not op.ismount(path):  # Note ismount() does not always detect mounts
        path = op.split(path)[0]
    return path


def find_ext_volume_global_trash(volume_root):
    # from [2] Trash directories (1) check for a .Trash dir with the right
    # permissions set.
    trash_dir = op.join(volume_root, TOPDIR_TRASH)
    if not op.exists(trash_dir):
        return None

    mode = os.lstat(trash_dir).st_mode
    # vol/.Trash must be a directory, cannot be a symlink, and must have the
    # sticky bit set.
    if not op.isdir(trash_dir) or op.islink(trash_dir) or not (mode & stat.S_ISVTX):
        return None

    trash_dir = op.join(trash_dir, text_type(uid).encode("ascii"))
    try:
        check_create(trash_dir)
    except OSError:
        return None
    return trash_dir


def find_ext_volume_fallback_trash(volume_root):
    # from [2] Trash directories (1) create a .Trash-$uid dir.
    trash_dir = op.join(volume_root, TOPDIR_FALLBACK)
    # Try to make the directory, if we lack permission, raise TrashPermissionError
    try:
        check_create(trash_dir)
    except OSError as e:
        if e.errno == errno.EACCES:
            raise TrashPermissionError(e.filename)
        raise
    return trash_dir


def find_ext_volume_trash(volume_root):
    trash_dir = find_ext_volume_global_trash(volume_root)
    if trash_dir is None:
        trash_dir = find_ext_volume_fallback_trash(volume_root)
    return trash_dir


# Pull this out so it's easy to stub (to avoid stubbing lstat itself)
def get_dev(path):
    return os.lstat(path).st_dev


def send2trash(paths):
    paths = preprocess_paths(paths)
    for path in paths:
        if isinstance(path, text_type):
            path_b = fsencode(path)
        elif isinstance(path, bytes):
            path_b = path
        else:
            raise TypeError("str, bytes or PathLike expected, not %r" % type(path))

        if not op.exists(path_b):
            raise OSError(errno.ENOENT, "File not found: %s" % path)
        # ...should check whether the user has the necessary permissions to delete
        # it, before starting the trashing operation itself. [2]
        if not os.access(path_b, os.W_OK):
            raise OSError(errno.EACCES, "Permission denied: %s" % path)

        path_dev = get_dev(path_b)
        # If XDG_DATA_HOME or HOMETRASH do not yet exist we need to stat the
        # home directory, and these paths will be created further on if needed.
        trash_dev = get_dev(op.expanduser(b"~"))

        # if the file to be trashed is on the same device as HOMETRASH we
        # want to move it there.
        if path_dev == trash_dev:
            topdir = XDG_DATA_HOME
            dest_trash = HOMETRASH_B
        else:
            topdir = find_mount_point(path_b)
            trash_dev = get_dev(topdir)
            if trash_dev != path_dev:
                raise OSError("Couldn't find mount point for %s" % path)
            dest_trash = find_ext_volume_trash(topdir)
        try:
            trash_move(path_b, dest_trash, topdir)
        except OSError as error:
            # Cross link errors default back to HOMETRASH
            if error.errno == errno.EXDEV:
                trash_move(path_b, HOMETRASH_B, XDG_DATA_HOME, cross_dev=True)
            else:
                raise

# === NexusCore/openenv\Lib\site-packages\google\ai\generativelanguage_v1beta3\types\permission_service.py ===
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

from google.protobuf import field_mask_pb2  # type: ignore
import proto  # type: ignore

from google.ai.generativelanguage_v1beta3.types import permission as gag_permission

__protobuf__ = proto.module(
    package="google.ai.generativelanguage.v1beta3",
    manifest={
        "CreatePermissionRequest",
        "GetPermissionRequest",
        "ListPermissionsRequest",
        "ListPermissionsResponse",
        "UpdatePermissionRequest",
        "DeletePermissionRequest",
        "TransferOwnershipRequest",
        "TransferOwnershipResponse",
    },
)


class CreatePermissionRequest(proto.Message):
    r"""Request to create a ``Permission``.

    Attributes:
        parent (str):
            Required. The parent resource of the ``Permission``. Format:
            tunedModels/{tuned_model}
        permission (google.ai.generativelanguage_v1beta3.types.Permission):
            Required. The permission to create.
    """

    parent: str = proto.Field(
        proto.STRING,
        number=1,
    )
    permission: gag_permission.Permission = proto.Field(
        proto.MESSAGE,
        number=2,
        message=gag_permission.Permission,
    )


class GetPermissionRequest(proto.Message):
    r"""Request for getting information about a specific ``Permission``.

    Attributes:
        name (str):
            Required. The resource name of the permission.

            Format:
            ``tunedModels/{tuned_model}permissions/{permission}``
    """

    name: str = proto.Field(
        proto.STRING,
        number=1,
    )


class ListPermissionsRequest(proto.Message):
    r"""Request for listing permissions.

    Attributes:
        parent (str):
            Required. The parent resource of the permissions. Format:
            tunedModels/{tuned_model}
        page_size (int):
            Optional. The maximum number of ``Permission``\ s to return
            (per page). The service may return fewer permissions.

            If unspecified, at most 10 permissions will be returned.
            This method returns at most 1000 permissions per page, even
            if you pass larger page_size.
        page_token (str):
            Optional. A page token, received from a previous
            ``ListPermissions`` call.

            Provide the ``page_token`` returned by one request as an
            argument to the next request to retrieve the next page.

            When paginating, all other parameters provided to
            ``ListPermissions`` must match the call that provided the
            page token.
    """

    parent: str = proto.Field(
        proto.STRING,
        number=1,
    )
    page_size: int = proto.Field(
        proto.INT32,
        number=2,
    )
    page_token: str = proto.Field(
        proto.STRING,
        number=3,
    )


class ListPermissionsResponse(proto.Message):
    r"""Response from ``ListPermissions`` containing a paginated list of
    permissions.

    Attributes:
        permissions (MutableSequence[google.ai.generativelanguage_v1beta3.types.Permission]):
            Returned permissions.
        next_page_token (str):
            A token, which can be sent as ``page_token`` to retrieve the
            next page.

            If this field is omitted, there are no more pages.
    """

    @property
    def raw_page(self):
        return self

    permissions: MutableSequence[gag_permission.Permission] = proto.RepeatedField(
        proto.MESSAGE,
        number=1,
        message=gag_permission.Permission,
    )
    next_page_token: str = proto.Field(
        proto.STRING,
        number=2,
    )


class UpdatePermissionRequest(proto.Message):
    r"""Request to update the ``Permission``.

    Attributes:
        permission (google.ai.generativelanguage_v1beta3.types.Permission):
            Required. The permission to update.

            The permission's ``name`` field is used to identify the
            permission to update.
        update_mask (google.protobuf.field_mask_pb2.FieldMask):
            Required. The list of fields to update. Accepted ones:

            -  role (``Permission.role`` field)
    """

    permission: gag_permission.Permission = proto.Field(
        proto.MESSAGE,
        number=1,
        message=gag_permission.Permission,
    )
    update_mask: field_mask_pb2.FieldMask = proto.Field(
        proto.MESSAGE,
        number=2,
        message=field_mask_pb2.FieldMask,
    )


class DeletePermissionRequest(proto.Message):
    r"""Request to delete the ``Permission``.

    Attributes:
        name (str):
            Required. The resource name of the permission. Format:
            ``tunedModels/{tuned_model}/permissions/{permission}``
    """

    name: str = proto.Field(
        proto.STRING,
        number=1,
    )


class TransferOwnershipRequest(proto.Message):
    r"""Request to transfer the ownership of the tuned model.

    Attributes:
        name (str):
            Required. The resource name of the tuned model to transfer
            ownership .

            Format: ``tunedModels/my-model-id``
        email_address (str):
            Required. The email address of the user to
            whom the tuned model is being transferred to.
    """

    name: str = proto.Field(
        proto.STRING,
        number=1,
    )
    email_address: str = proto.Field(
        proto.STRING,
        number=2,
    )


class TransferOwnershipResponse(proto.Message):
    r"""Response from ``TransferOwnership``."""


__all__ = tuple(sorted(__protobuf__.manifest))

# === NexusCore/openenv\Lib\site-packages\isapi\samples\advanced.py ===
# This extension demonstrates some advanced features of the Python ISAPI
# framework.
# We demonstrate:
# * Reloading your Python module without shutting down IIS (eg, when your
#   .py implementation file changes.)
# * Custom command-line handling - both additional options and commands.
# * Using a query string - any part of the URL after a '?' is assumed to
#   be "variable names" separated by '&' - we will print the values of
#   these server variables.
# * If the tail portion of the URL is "ReportUnhealthy", IIS will be
#   notified we are unhealthy via a HSE_REQ_REPORT_UNHEALTHY request.
#   Whether this is acted upon depends on if the IIS health-checking
#   tools are installed, but you should always see the reason written
#   to the Windows event log - see the IIS documentation for more.

import os
import stat
import sys

from isapi import isapicon
from isapi.simple import SimpleExtension

if hasattr(sys, "isapidllhandle"):
    import win32traceutil

# Notes on reloading
# If your HttpFilterProc or HttpExtensionProc functions raises
# 'isapi.InternalReloadException', the framework will not treat it
# as an error but instead will terminate your extension, reload your
# extension module, re-initialize the instance, and re-issue the request.
# The Initialize functions are called with None as their param.  The
# return code from the terminate function is ignored.
#
# This is all the framework does to help you.  It is up to your code
# when you raise this exception.  This sample uses a Win32 "find
# notification".  Whenever windows tells us one of the files in the
# directory has changed, we check if the time of our source-file has
# changed, and set a flag.  Next imcoming request, we check the flag and
# raise the special exception if set.
#
# The end result is that the module is automatically reloaded whenever
# the source-file changes - you need take no further action to see your
# changes reflected in the running server.

# The framework only reloads your module - if you have libraries you
# depend on and also want reloaded, you must arrange for this yourself.
# One way of doing this would be to special case the import of these
# modules.  Eg:
# --
# try:
#    my_module = reload(my_module) # module already imported - reload it
# except NameError:
#    import my_module # first time around - import it.
# --
# When your module is imported for the first time, the NameError will
# be raised, and the module imported.  When the ISAPI framework reloads
# your module, the existing module will avoid the NameError, and allow
# you to reload that module.

import threading

import win32con
import win32event
import win32file
import winerror

from isapi import InternalReloadException

try:
    reload_counter += 1  # type: ignore[used-before-def]
except NameError:
    reload_counter = 0


# A watcher thread that checks for __file__ changing.
# When it detects it, it simply sets "change_detected" to true.
class ReloadWatcherThread(threading.Thread):
    def __init__(self):
        self.change_detected = False
        self.filename = __file__
        if self.filename.endswith("c") or self.filename.endswith("o"):
            self.filename = self.filename[:-1]
        self.handle = win32file.FindFirstChangeNotification(
            os.path.dirname(self.filename),
            False,  # watch tree?
            win32con.FILE_NOTIFY_CHANGE_LAST_WRITE,
        )
        threading.Thread.__init__(self)

    def run(self):
        last_time = os.stat(self.filename)[stat.ST_MTIME]
        while 1:
            try:
                rc = win32event.WaitForSingleObject(self.handle, win32event.INFINITE)
                win32file.FindNextChangeNotification(self.handle)
            except win32event.error as details:
                # handle closed - thread should terminate.
                if details.winerror != winerror.ERROR_INVALID_HANDLE:
                    raise
                break
            this_time = os.stat(self.filename)[stat.ST_MTIME]
            if this_time != last_time:
                print("Detected file change - flagging for reload.")
                self.change_detected = True
                last_time = this_time

    def stop(self):
        win32file.FindCloseChangeNotification(self.handle)


# The ISAPI extension - handles requests in our virtual dir, and sends the
# response to the client.
class Extension(SimpleExtension):
    "Python advanced sample Extension"

    def __init__(self):
        self.reload_watcher = ReloadWatcherThread()
        self.reload_watcher.start()

    def HttpExtensionProc(self, ecb):
        # NOTE: If you use a ThreadPoolExtension, you must still perform
        # this check in HttpExtensionProc - raising the exception from
        # The "Dispatch" method will just cause the exception to be
        # rendered to the browser.
        if self.reload_watcher.change_detected:
            print("Doing reload")
            raise InternalReloadException

        url = ecb.GetServerVariable("UNICODE_URL")
        if url.endswith("ReportUnhealthy"):
            ecb.ReportUnhealthy("I'm a little sick")

        ecb.SendResponseHeaders("200 OK", "Content-Type: text/html\r\n\r\n", 0)
        print("<HTML><BODY>", file=ecb)

        qs = ecb.GetServerVariable("QUERY_STRING")
        if qs:
            queries = qs.split("&")
            print("<PRE>", file=ecb)
            for q in queries:
                val = ecb.GetServerVariable(q, "&lt;no such variable&gt;")
                print(f"{q}={val!r}", file=ecb)
            print("</PRE><P/>", file=ecb)

        print("This module has been imported", file=ecb)
        print("%d times" % (reload_counter,), file=ecb)
        print("</BODY></HTML>", file=ecb)
        ecb.close()
        return isapicon.HSE_STATUS_SUCCESS

    def TerminateExtension(self, status):
        self.reload_watcher.stop()


# The entry points for the ISAPI extension.
def __ExtensionFactory__():
    return Extension()


# Our special command line customization.
# Pre-install hook for our virtual directory.
def PreInstallDirectory(params, options):
    # If the user used our special '--description' option,
    # then we override our default.
    if options.description:
        params.Description = options.description


# Post install hook for our entire script
def PostInstall(params, options):
    print()
    print("The sample has been installed.")
    print("Point your browser to /AdvancedPythonSample")
    print("If you modify the source file and reload the page,")
    print("you should see the reload counter increment")


# Handler for our custom 'status' argument.
def status_handler(options, log, arg):
    "Query the status of something"
    print("Everything seems to be fine!")


custom_arg_handlers = {"status": status_handler}

if __name__ == "__main__":
    # If run from the command-line, install ourselves.
    from isapi.install import *

    params = ISAPIParameters(PostInstall=PostInstall)
    # Setup the virtual directories - this is a list of directories our
    # extension uses - in this case only 1.
    # Each extension has a "script map" - this is the mapping of ISAPI
    # extensions.
    sm = [ScriptMapParams(Extension="*", Flags=0)]
    vd = VirtualDirParameters(
        Name="AdvancedPythonSample",
        Description=Extension.__doc__,
        ScriptMaps=sm,
        ScriptMapUpdate="replace",
        # specify the pre-install hook.
        PreInstall=PreInstallDirectory,
    )
    params.VirtualDirs = [vd]
    # Setup our custom option parser.
    from optparse import OptionParser

    parser = OptionParser("")  # blank usage, so isapi sets it.
    parser.add_option(
        "",
        "--description",
        action="store",
        help="custom description to use for the virtual directory",
    )

    HandleCommandLine(
        params, opt_parser=parser, custom_arg_handlers=custom_arg_handlers
    )

# === NexusCore/openenv\Lib\site-packages\litellm\litellm_core_utils\realtime_streaming.py ===
import asyncio
import concurrent.futures
import json
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Union

import litellm
from litellm._logging import verbose_logger
from litellm.llms.base_llm.realtime.transformation import BaseRealtimeConfig
from litellm.types.llms.openai import (
    OpenAIRealtimeEvents,
    OpenAIRealtimeOutputItemDone,
    OpenAIRealtimeResponseDelta,
    OpenAIRealtimeStreamResponseBaseObject,
    OpenAIRealtimeStreamSessionEvents,
)
from litellm.types.realtime import ALL_DELTA_TYPES

from .litellm_logging import Logging as LiteLLMLogging

if TYPE_CHECKING:
    from websockets.asyncio.client import ClientConnection

    CLIENT_CONNECTION_CLASS = ClientConnection
else:
    CLIENT_CONNECTION_CLASS = Any

# Create a thread pool with a maximum of 10 threads
executor = concurrent.futures.ThreadPoolExecutor(max_workers=10)

DefaultLoggedRealTimeEventTypes = [
    "session.created",
    "response.create",
    "response.done",
]


class RealTimeStreaming:
    def __init__(
        self,
        websocket: Any,
        backend_ws: CLIENT_CONNECTION_CLASS,
        logging_obj: LiteLLMLogging,
        provider_config: Optional[BaseRealtimeConfig] = None,
        model: str = "",
    ):
        self.websocket = websocket
        self.backend_ws = backend_ws
        self.logging_obj = logging_obj
        self.messages: List[OpenAIRealtimeEvents] = []
        self.input_message: Dict = {}

        _logged_real_time_event_types = litellm.logged_real_time_event_types

        if _logged_real_time_event_types is None:
            _logged_real_time_event_types = DefaultLoggedRealTimeEventTypes
        self.logged_real_time_event_types = _logged_real_time_event_types
        self.provider_config = provider_config
        self.model = model
        self.current_delta_chunks: Optional[List[OpenAIRealtimeResponseDelta]] = None
        self.current_output_item_id: Optional[str] = None
        self.current_response_id: Optional[str] = None
        self.current_conversation_id: Optional[str] = None
        self.current_item_chunks: Optional[List[OpenAIRealtimeOutputItemDone]] = None
        self.current_delta_type: Optional[ALL_DELTA_TYPES] = None
        self.session_configuration_request: Optional[str] = None

    def _should_store_message(
        self,
        message_obj: Union[dict, OpenAIRealtimeEvents],
    ) -> bool:
        _msg_type = message_obj["type"] if "type" in message_obj else None
        if self.logged_real_time_event_types == "*":
            return True
        if _msg_type and _msg_type in self.logged_real_time_event_types:
            return True
        return False

    def store_message(self, message: Union[str, bytes, OpenAIRealtimeEvents]):
        """Store message in list"""
        if isinstance(message, bytes):
            message = message.decode("utf-8")
        if isinstance(message, dict):
            message_obj = message
        else:
            message_obj = json.loads(message)
        try:
            if (
                not isinstance(message, dict)
                or message_obj.get("type") == "session.created"
                or message_obj.get("type") == "session.updated"
            ):
                message_obj = OpenAIRealtimeStreamSessionEvents(**message_obj)  # type: ignore
            elif not isinstance(message, dict):
                message_obj = OpenAIRealtimeStreamResponseBaseObject(**message_obj)  # type: ignore
        except Exception as e:
            verbose_logger.debug(f"Error parsing message for logging: {e}")
            raise e
        if self._should_store_message(message_obj):
            self.messages.append(message_obj)

    def store_input(self, message: dict):
        """Store input message"""
        self.input_message = message
        if self.logging_obj:
            self.logging_obj.pre_call(input=message, api_key="")

    async def log_messages(self):
        """Log messages in list"""
        if self.logging_obj:
            ## ASYNC LOGGING
            # Create an event loop for the new thread
            asyncio.create_task(self.logging_obj.async_success_handler(self.messages))
            ## SYNC LOGGING
            executor.submit(self.logging_obj.success_handler(self.messages))

    async def backend_to_client_send_messages(self):
        import websockets

        try:
            while True:
                try:
                    raw_response = await self.backend_ws.recv(
                        decode=False
                    )  # improves performance
                except TypeError:
                    raw_response = await self.backend_ws.recv()  # type: ignore[assignment]

                if self.provider_config:
                    returned_object = self.provider_config.transform_realtime_response(
                        raw_response,
                        self.model,
                        self.logging_obj,
                        realtime_response_transform_input={
                            "session_configuration_request": self.session_configuration_request,
                            "current_output_item_id": self.current_output_item_id,
                            "current_response_id": self.current_response_id,
                            "current_delta_chunks": self.current_delta_chunks,
                            "current_conversation_id": self.current_conversation_id,
                            "current_item_chunks": self.current_item_chunks,
                            "current_delta_type": self.current_delta_type,
                        },
                    )

                    transformed_response = returned_object["response"]
                    self.current_output_item_id = returned_object[
                        "current_output_item_id"
                    ]
                    self.current_response_id = returned_object["current_response_id"]
                    self.current_delta_chunks = returned_object["current_delta_chunks"]
                    self.current_conversation_id = returned_object[
                        "current_conversation_id"
                    ]
                    self.current_item_chunks = returned_object["current_item_chunks"]
                    self.current_delta_type = returned_object["current_delta_type"]
                    self.session_configuration_request = returned_object[
                        "session_configuration_request"
                    ]
                    if isinstance(transformed_response, list):
                        for event in transformed_response:
                            event_str = json.dumps(event)
                            ## LOGGING
                            self.store_message(event_str)
                            await self.websocket.send_text(event_str)
                    else:
                        event_str = json.dumps(transformed_response)
                        ## LOGGING
                        self.store_message(event_str)
                        await self.websocket.send_text(event_str)

                else:
                    ## LOGGING
                    self.store_message(raw_response)
                    await self.websocket.send_text(raw_response)

        except websockets.exceptions.ConnectionClosed as e:  # type: ignore
            verbose_logger.exception(
                f"Connection closed in backend to client send messages - {e}"
            )
        except Exception as e:
            verbose_logger.exception(f"Error in backend to client send messages: {e}")
        finally:
            await self.log_messages()

    async def client_ack_messages(self):
        try:
            while True:
                message = await self.websocket.receive_text()

                ## LOGGING
                self.store_input(message=message)
                ## FORWARD TO BACKEND
                if self.provider_config:
                    message = self.provider_config.transform_realtime_request(
                        message, self.model
                    )

                    for msg in message:
                        await self.backend_ws.send(msg)
                else:
                    await self.backend_ws.send(message)

        except Exception as e:
            verbose_logger.debug(f"Error in client ack messages: {e}")

    async def bidirectional_forward(self):
        forward_task = asyncio.create_task(self.backend_to_client_send_messages())
        try:
            await self.client_ack_messages()
        except self.websocket.exceptions.ConnectionClosed:  # type: ignore
            verbose_logger.debug("Connection closed")
            forward_task.cancel()
        finally:
            if not forward_task.done():
                forward_task.cancel()
                try:
                    await forward_task
                except asyncio.CancelledError:
                    pass

# === NexusCore/openenv\Lib\site-packages\litellm\llms\base_llm\base_model_iterator.py ===
import json
from abc import abstractmethod
from typing import List, Optional, Union, cast

import litellm
from litellm.types.utils import (
    Choices,
    Delta,
    GenericStreamingChunk,
    ModelResponse,
    ModelResponseStream,
    StreamingChoices,
)


class BaseModelResponseIterator:
    def __init__(
        self, streaming_response, sync_stream: bool, json_mode: Optional[bool] = False
    ):
        self.streaming_response = streaming_response
        self.response_iterator = self.streaming_response
        self.json_mode = json_mode

    def chunk_parser(
        self, chunk: dict
    ) -> Union[GenericStreamingChunk, ModelResponseStream]:
        return GenericStreamingChunk(
            text="",
            is_finished=False,
            finish_reason="",
            usage=None,
            index=0,
            tool_use=None,
        )

    # Sync iterator
    def __iter__(self):
        return self

    @staticmethod
    def _string_to_dict_parser(str_line: str) -> Optional[dict]:
        stripped_json_chunk: Optional[dict] = None
        stripped_chunk = litellm.CustomStreamWrapper._strip_sse_data_from_chunk(
            str_line
        )
        try:
            if stripped_chunk is not None:
                stripped_json_chunk = json.loads(stripped_chunk)
            else:
                stripped_json_chunk = None
        except json.JSONDecodeError:
            stripped_json_chunk = None
        return stripped_json_chunk

    def _handle_string_chunk(
        self, str_line: str
    ) -> Union[GenericStreamingChunk, ModelResponseStream]:
        # chunk is a str at this point
        stripped_json_chunk = BaseModelResponseIterator._string_to_dict_parser(
            str_line=str_line
        )
        if "[DONE]" in str_line:
            return GenericStreamingChunk(
                text="",
                is_finished=True,
                finish_reason="stop",
                usage=None,
                index=0,
                tool_use=None,
            )
        elif stripped_json_chunk:
            return self.chunk_parser(chunk=stripped_json_chunk)
        else:
            return GenericStreamingChunk(
                text="",
                is_finished=False,
                finish_reason="",
                usage=None,
                index=0,
                tool_use=None,
            )

    def __next__(self):
        try:
            chunk = self.response_iterator.__next__()
        except StopIteration:
            raise StopIteration
        except ValueError as e:
            raise RuntimeError(f"Error receiving chunk from stream: {e}")

        try:
            str_line = chunk
            if isinstance(chunk, bytes):  # Handle binary data
                str_line = chunk.decode("utf-8")  # Convert bytes to string
                index = str_line.find("data:")
                if index != -1:
                    str_line = str_line[index:]
            # chunk is a str at this point
            return self._handle_string_chunk(str_line=str_line)
        except StopIteration:
            raise StopIteration
        except ValueError as e:
            raise RuntimeError(f"Error parsing chunk: {e},\nReceived chunk: {chunk}")

    # Async iterator
    def __aiter__(self):
        self.async_response_iterator = self.streaming_response.__aiter__()
        return self

    async def __anext__(self):
        try:
            chunk = await self.async_response_iterator.__anext__()

        except StopAsyncIteration:
            raise StopAsyncIteration
        except ValueError as e:
            raise RuntimeError(f"Error receiving chunk from stream: {e}")

        try:
            str_line = chunk
            if isinstance(chunk, bytes):  # Handle binary data
                str_line = chunk.decode("utf-8")  # Convert bytes to string
                index = str_line.find("data:")
                if index != -1:
                    str_line = str_line[index:]

            # chunk is a str at this point
            chunk = self._handle_string_chunk(str_line=str_line)

            return chunk
        except StopAsyncIteration:
            raise StopAsyncIteration
        except ValueError as e:
            raise RuntimeError(f"Error parsing chunk: {e},\nReceived chunk: {chunk}")


class MockResponseIterator:  # for returning ai21 streaming responses
    def __init__(
        self, model_response: ModelResponse, json_mode: Optional[bool] = False
    ):
        self.model_response = model_response
        self.json_mode = json_mode
        self.is_done = False

    # Sync iterator
    def __iter__(self):
        return self

    def _chunk_parser(self, chunk_data: ModelResponse) -> ModelResponseStream:
        try:
            streaming_choices: List[StreamingChoices] = []
            for choice in chunk_data.choices:
                streaming_choices.append(
                    StreamingChoices(
                        index=choice.index,
                        delta=Delta(
                            **cast(Choices, choice).message.model_dump(),
                        ),
                        finish_reason=choice.finish_reason,
                    )
                )
            processed_chunk = ModelResponseStream(
                id=chunk_data.id,
                object="chat.completion",
                created=chunk_data.created,
                model=chunk_data.model,
                choices=streaming_choices,
            )
            return processed_chunk
        except Exception as e:
            raise ValueError(f"Failed to decode chunk: {chunk_data}. Error: {e}")

    def __next__(self):
        if self.is_done:
            raise StopIteration
        self.is_done = True
        return self._chunk_parser(self.model_response)

    # Async iterator
    def __aiter__(self):
        return self

    async def __anext__(self):
        if self.is_done:
            raise StopAsyncIteration
        self.is_done = True
        return self._chunk_parser(self.model_response)


class FakeStreamResponseIterator:
    def __init__(self, model_response, json_mode: Optional[bool] = False):
        self.model_response = model_response
        self.json_mode = json_mode
        self.is_done = False

    # Sync iterator
    def __iter__(self):
        return self

    @abstractmethod
    def chunk_parser(self, chunk: dict) -> GenericStreamingChunk:
        pass

    def __next__(self):
        if self.is_done:
            raise StopIteration
        self.is_done = True
        return self.chunk_parser(self.model_response)

    # Async iterator
    def __aiter__(self):
        return self

    async def __anext__(self):
        if self.is_done:
            raise StopAsyncIteration
        self.is_done = True
        return self.chunk_parser(self.model_response)

# === NexusCore/openenv\Lib\site-packages\litellm\llms\cloudflare\chat\transformation.py ===
import json
import time
from typing import AsyncIterator, Iterator, List, Optional, Union

import httpx

import litellm
from litellm.llms.base_llm.base_model_iterator import BaseModelResponseIterator
from litellm.llms.base_llm.chat.transformation import (
    BaseConfig,
    BaseLLMException,
    LiteLLMLoggingObj,
)
from litellm.secret_managers.main import get_secret_str
from litellm.types.llms.openai import AllMessageValues
from litellm.types.utils import (
    ChatCompletionToolCallChunk,
    ChatCompletionUsageBlock,
    GenericStreamingChunk,
    ModelResponse,
    Usage,
)


class CloudflareError(BaseLLMException):
    def __init__(self, status_code, message):
        self.status_code = status_code
        self.message = message
        self.request = httpx.Request(method="POST", url="https://api.cloudflare.com")
        self.response = httpx.Response(status_code=status_code, request=self.request)
        super().__init__(
            status_code=status_code,
            message=message,
            request=self.request,
            response=self.response,
        )  # Call the base class constructor with the parameters it needs


class CloudflareChatConfig(BaseConfig):
    max_tokens: Optional[int] = None
    stream: Optional[bool] = None

    def __init__(
        self,
        max_tokens: Optional[int] = None,
        stream: Optional[bool] = None,
    ) -> None:
        locals_ = locals().copy()
        for key, value in locals_.items():
            if key != "self" and value is not None:
                setattr(self.__class__, key, value)

    @classmethod
    def get_config(cls):
        return super().get_config()

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
        if api_key is None:
            raise ValueError(
                "Missing CloudflareError API Key - A call is being made to cloudflare but no key is set either in the environment variables or via params"
            )
        headers = {
            "accept": "application/json",
            "content-type": "apbplication/json",
            "Authorization": "Bearer " + api_key,
        }
        return headers

    def get_complete_url(
        self,
        api_base: Optional[str],
        api_key: Optional[str],
        model: str,
        optional_params: dict,
        litellm_params: dict,
        stream: Optional[bool] = None,
    ) -> str:
        if api_base is None:
            account_id = get_secret_str("CLOUDFLARE_ACCOUNT_ID")
            api_base = (
                f"https://api.cloudflare.com/client/v4/accounts/{account_id}/ai/run/"
            )
        return api_base + model

    def get_supported_openai_params(self, model: str) -> List[str]:
        return [
            "stream",
            "max_tokens",
        ]

    def map_openai_params(
        self,
        non_default_params: dict,
        optional_params: dict,
        model: str,
        drop_params: bool,
    ) -> dict:
        supported_openai_params = self.get_supported_openai_params(model=model)
        for param, value in non_default_params.items():
            if param == "max_completion_tokens":
                optional_params["max_tokens"] = value
            elif param in supported_openai_params:
                optional_params[param] = value
        return optional_params

    def transform_request(
        self,
        model: str,
        messages: List[AllMessageValues],
        optional_params: dict,
        litellm_params: dict,
        headers: dict,
    ) -> dict:
        config = litellm.CloudflareChatConfig.get_config()
        for k, v in config.items():
            if k not in optional_params:
                optional_params[k] = v

        data = {
            "messages": messages,
            **optional_params,
        }
        return data

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
        encoding: str,
        api_key: Optional[str] = None,
        json_mode: Optional[bool] = None,
    ) -> ModelResponse:
        completion_response = raw_response.json()

        model_response.choices[0].message.content = completion_response["result"][  # type: ignore
            "response"
        ]

        prompt_tokens = litellm.utils.get_token_count(messages=messages, model=model)
        completion_tokens = len(
            encoding.encode(model_response["choices"][0]["message"].get("content", ""))
        )

        model_response.created = int(time.time())
        model_response.model = "cloudflare/" + model
        usage = Usage(
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=prompt_tokens + completion_tokens,
        )
        setattr(model_response, "usage", usage)
        return model_response

    def get_error_class(
        self, error_message: str, status_code: int, headers: Union[dict, httpx.Headers]
    ) -> BaseLLMException:
        return CloudflareError(
            status_code=status_code,
            message=error_message,
        )

    def get_model_response_iterator(
        self,
        streaming_response: Union[Iterator[str], AsyncIterator[str], ModelResponse],
        sync_stream: bool,
        json_mode: Optional[bool] = False,
    ):
        return CloudflareChatResponseIterator(
            streaming_response=streaming_response,
            sync_stream=sync_stream,
            json_mode=json_mode,
        )


class CloudflareChatResponseIterator(BaseModelResponseIterator):
    def chunk_parser(self, chunk: dict) -> GenericStreamingChunk:
        try:
            text = ""
            tool_use: Optional[ChatCompletionToolCallChunk] = None
            is_finished = False
            finish_reason = ""
            usage: Optional[ChatCompletionUsageBlock] = None
            provider_specific_fields = None

            index = int(chunk.get("index", 0))

            if "response" in chunk:
                text = chunk["response"]

            returned_chunk = GenericStreamingChunk(
                text=text,
                tool_use=tool_use,
                is_finished=is_finished,
                finish_reason=finish_reason,
                usage=usage,
                index=index,
                provider_specific_fields=provider_specific_fields,
            )

            return returned_chunk

        except json.JSONDecodeError:
            raise ValueError(f"Failed to decode JSON from chunk: {chunk}")

# === NexusCore/openenv\Lib\site-packages\litellm\proxy\pass_through_endpoints\llm_provider_handlers\anthropic_passthrough_logging_handler.py ===
import json
from datetime import datetime
from typing import TYPE_CHECKING, Any, List, Optional, Union

import httpx

import litellm
from litellm._logging import verbose_proxy_logger
from litellm.litellm_core_utils.litellm_logging import Logging as LiteLLMLoggingObj
from litellm.llms.anthropic import get_anthropic_config
from litellm.llms.anthropic.chat.handler import (
    ModelResponseIterator as AnthropicModelResponseIterator,
)
from litellm.proxy._types import PassThroughEndpointLoggingTypedDict
from litellm.proxy.auth.auth_utils import get_end_user_id_from_request_body
from litellm.types.passthrough_endpoints.pass_through_endpoints import (
    PassthroughStandardLoggingPayload,
)
from litellm.types.utils import ModelResponse, TextCompletionResponse

if TYPE_CHECKING:
    from ..success_handler import PassThroughEndpointLogging
    from ..types import EndpointType
else:
    PassThroughEndpointLogging = Any
    EndpointType = Any


class AnthropicPassthroughLoggingHandler:
    @staticmethod
    def anthropic_passthrough_handler(
        httpx_response: httpx.Response,
        response_body: dict,
        logging_obj: LiteLLMLoggingObj,
        url_route: str,
        result: str,
        start_time: datetime,
        end_time: datetime,
        cache_hit: bool,
        **kwargs,
    ) -> PassThroughEndpointLoggingTypedDict:
        """
        Transforms Anthropic response to OpenAI response, generates a standard logging object so downstream logging can be handled
        """
        model = response_body.get("model", "")
        anthropic_config = get_anthropic_config(url_route)
        litellm_model_response: ModelResponse = anthropic_config().transform_response(
            raw_response=httpx_response,
            model_response=litellm.ModelResponse(),
            model=model,
            messages=[],
            logging_obj=logging_obj,
            optional_params={},
            api_key="",
            request_data={},
            encoding=litellm.encoding,
            json_mode=False,
            litellm_params={},
        )

        kwargs = AnthropicPassthroughLoggingHandler._create_anthropic_response_logging_payload(
            litellm_model_response=litellm_model_response,
            model=model,
            kwargs=kwargs,
            start_time=start_time,
            end_time=end_time,
            logging_obj=logging_obj,
        )

        return {
            "result": litellm_model_response,
            "kwargs": kwargs,
        }

    @staticmethod
    def _get_user_from_metadata(
        passthrough_logging_payload: PassthroughStandardLoggingPayload,
    ) -> Optional[str]:
        request_body = passthrough_logging_payload.get("request_body")
        if request_body:
            return get_end_user_id_from_request_body(request_body)
        return None

    @staticmethod
    def _create_anthropic_response_logging_payload(
        litellm_model_response: Union[ModelResponse, TextCompletionResponse],
        model: str,
        kwargs: dict,
        start_time: datetime,
        end_time: datetime,
        logging_obj: LiteLLMLoggingObj,
    ):
        """
        Create the standard logging object for Anthropic passthrough

        handles streaming and non-streaming responses
        """
        try:
            response_cost = litellm.completion_cost(
                completion_response=litellm_model_response,
                model=model,
            )
            kwargs["response_cost"] = response_cost
            kwargs["model"] = model
            passthrough_logging_payload: Optional[PassthroughStandardLoggingPayload] = (  # type: ignore
                kwargs.get("passthrough_logging_payload")
            )
            if passthrough_logging_payload:
                user = AnthropicPassthroughLoggingHandler._get_user_from_metadata(
                    passthrough_logging_payload=passthrough_logging_payload,
                )
                if user:
                    kwargs.setdefault("litellm_params", {})
                    kwargs["litellm_params"].update(
                        {"proxy_server_request": {"body": {"user": user}}}
                    )

            # pretty print standard logging object
            verbose_proxy_logger.debug(
                "kwargs= %s",
                json.dumps(kwargs, indent=4, default=str),
            )

            # set litellm_call_id to logging response object
            litellm_model_response.id = logging_obj.litellm_call_id
            litellm_model_response.model = model
            logging_obj.model_call_details["model"] = model
            logging_obj.model_call_details["custom_llm_provider"] = (
                litellm.LlmProviders.ANTHROPIC.value
            )
            return kwargs
        except Exception as e:
            verbose_proxy_logger.exception(
                "Error creating Anthropic response logging payload: %s", e
            )
            return kwargs

    @staticmethod
    def _handle_logging_anthropic_collected_chunks(
        litellm_logging_obj: LiteLLMLoggingObj,
        passthrough_success_handler_obj: PassThroughEndpointLogging,
        url_route: str,
        request_body: dict,
        endpoint_type: EndpointType,
        start_time: datetime,
        all_chunks: List[str],
        end_time: datetime,
    ) -> PassThroughEndpointLoggingTypedDict:
        """
        Takes raw chunks from Anthropic passthrough endpoint and logs them in litellm callbacks

        - Builds complete response from chunks
        - Creates standard logging object
        - Logs in litellm callbacks
        """

        model = request_body.get("model", "")
        complete_streaming_response = (
            AnthropicPassthroughLoggingHandler._build_complete_streaming_response(
                all_chunks=all_chunks,
                litellm_logging_obj=litellm_logging_obj,
                model=model,
            )
        )
        if complete_streaming_response is None:
            verbose_proxy_logger.error(
                "Unable to build complete streaming response for Anthropic passthrough endpoint, not logging..."
            )
            return {
                "result": None,
                "kwargs": {},
            }
        kwargs = AnthropicPassthroughLoggingHandler._create_anthropic_response_logging_payload(
            litellm_model_response=complete_streaming_response,
            model=model,
            kwargs={},
            start_time=start_time,
            end_time=end_time,
            logging_obj=litellm_logging_obj,
        )

        return {
            "result": complete_streaming_response,
            "kwargs": kwargs,
        }

    @staticmethod
    def _build_complete_streaming_response(
        all_chunks: List[str],
        litellm_logging_obj: LiteLLMLoggingObj,
        model: str,
    ) -> Optional[Union[ModelResponse, TextCompletionResponse]]:
        """
        Builds complete response from raw Anthropic chunks

        - Converts str chunks to generic chunks
        - Converts generic chunks to litellm chunks (OpenAI format)
        - Builds complete response from litellm chunks
        """
        anthropic_model_response_iterator = AnthropicModelResponseIterator(
            streaming_response=None,
            sync_stream=False,
        )
        all_openai_chunks = []
        for _chunk_str in all_chunks:
            try:
                transformed_openai_chunk = anthropic_model_response_iterator.convert_str_chunk_to_generic_chunk(
                    chunk=_chunk_str
                )
                if transformed_openai_chunk is not None:
                    all_openai_chunks.append(transformed_openai_chunk)

            except (StopIteration, StopAsyncIteration):
                break
        complete_streaming_response = litellm.stream_chunk_builder(
            chunks=all_openai_chunks
        )
        return complete_streaming_response

# === NexusCore/openenv\Lib\site-packages\nltk\lm\vocabulary.py ===
# Natural Language Toolkit
#
# Copyright (C) 2001-2024 NLTK Project
# Author: Ilia Kurenkov <ilia.kurenkov@gmail.com>
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT
"""Language Model Vocabulary"""

import sys
from collections import Counter
from collections.abc import Iterable
from functools import singledispatch
from itertools import chain


@singledispatch
def _dispatched_lookup(words, vocab):
    raise TypeError(f"Unsupported type for looking up in vocabulary: {type(words)}")


@_dispatched_lookup.register(Iterable)
def _(words, vocab):
    """Look up a sequence of words in the vocabulary.

    Returns an iterator over looked up words.

    """
    return tuple(_dispatched_lookup(w, vocab) for w in words)


@_dispatched_lookup.register(str)
def _string_lookup(word, vocab):
    """Looks up one word in the vocabulary."""
    return word if word in vocab else vocab.unk_label


class Vocabulary:
    """Stores language model vocabulary.

    Satisfies two common language modeling requirements for a vocabulary:

    - When checking membership and calculating its size, filters items
      by comparing their counts to a cutoff value.
    - Adds a special "unknown" token which unseen words are mapped to.

    >>> words = ['a', 'c', '-', 'd', 'c', 'a', 'b', 'r', 'a', 'c', 'd']
    >>> from nltk.lm import Vocabulary
    >>> vocab = Vocabulary(words, unk_cutoff=2)

    Tokens with counts greater than or equal to the cutoff value will
    be considered part of the vocabulary.

    >>> vocab['c']
    3
    >>> 'c' in vocab
    True
    >>> vocab['d']
    2
    >>> 'd' in vocab
    True

    Tokens with frequency counts less than the cutoff value will be considered not
    part of the vocabulary even though their entries in the count dictionary are
    preserved.

    >>> vocab['b']
    1
    >>> 'b' in vocab
    False
    >>> vocab['aliens']
    0
    >>> 'aliens' in vocab
    False

    Keeping the count entries for seen words allows us to change the cutoff value
    without having to recalculate the counts.

    >>> vocab2 = Vocabulary(vocab.counts, unk_cutoff=1)
    >>> "b" in vocab2
    True

    The cutoff value influences not only membership checking but also the result of
    getting the size of the vocabulary using the built-in `len`.
    Note that while the number of keys in the vocabulary's counter stays the same,
    the items in the vocabulary differ depending on the cutoff.
    We use `sorted` to demonstrate because it keeps the order consistent.

    >>> sorted(vocab2.counts)
    ['-', 'a', 'b', 'c', 'd', 'r']
    >>> sorted(vocab2)
    ['-', '<UNK>', 'a', 'b', 'c', 'd', 'r']
    >>> sorted(vocab.counts)
    ['-', 'a', 'b', 'c', 'd', 'r']
    >>> sorted(vocab)
    ['<UNK>', 'a', 'c', 'd']

    In addition to items it gets populated with, the vocabulary stores a special
    token that stands in for so-called "unknown" items. By default it's "<UNK>".

    >>> "<UNK>" in vocab
    True

    We can look up words in a vocabulary using its `lookup` method.
    "Unseen" words (with counts less than cutoff) are looked up as the unknown label.
    If given one word (a string) as an input, this method will return a string.

    >>> vocab.lookup("a")
    'a'
    >>> vocab.lookup("aliens")
    '<UNK>'

    If given a sequence, it will return an tuple of the looked up words.

    >>> vocab.lookup(["p", 'a', 'r', 'd', 'b', 'c'])
    ('<UNK>', 'a', '<UNK>', 'd', '<UNK>', 'c')

    It's possible to update the counts after the vocabulary has been created.
    In general, the interface is the same as that of `collections.Counter`.

    >>> vocab['b']
    1
    >>> vocab.update(["b", "b", "c"])
    >>> vocab['b']
    3
    """

    def __init__(self, counts=None, unk_cutoff=1, unk_label="<UNK>"):
        """Create a new Vocabulary.

        :param counts: Optional iterable or `collections.Counter` instance to
                       pre-seed the Vocabulary. In case it is iterable, counts
                       are calculated.
        :param int unk_cutoff: Words that occur less frequently than this value
                               are not considered part of the vocabulary.
        :param unk_label: Label for marking words not part of vocabulary.

        """
        self.unk_label = unk_label
        if unk_cutoff < 1:
            raise ValueError(f"Cutoff value cannot be less than 1. Got: {unk_cutoff}")
        self._cutoff = unk_cutoff

        self.counts = Counter()
        self.update(counts if counts is not None else "")

    @property
    def cutoff(self):
        """Cutoff value.

        Items with count below this value are not considered part of vocabulary.

        """
        return self._cutoff

    def update(self, *counter_args, **counter_kwargs):
        """Update vocabulary counts.

        Wraps `collections.Counter.update` method.

        """
        self.counts.update(*counter_args, **counter_kwargs)
        self._len = sum(1 for _ in self)

    def lookup(self, words):
        """Look up one or more words in the vocabulary.

        If passed one word as a string will return that word or `self.unk_label`.
        Otherwise will assume it was passed a sequence of words, will try to look
        each of them up and return an iterator over the looked up words.

        :param words: Word(s) to look up.
        :type words: Iterable(str) or str
        :rtype: generator(str) or str
        :raises: TypeError for types other than strings or iterables

        >>> from nltk.lm import Vocabulary
        >>> vocab = Vocabulary(["a", "b", "c", "a", "b"], unk_cutoff=2)
        >>> vocab.lookup("a")
        'a'
        >>> vocab.lookup("aliens")
        '<UNK>'
        >>> vocab.lookup(["a", "b", "c", ["x", "b"]])
        ('a', 'b', '<UNK>', ('<UNK>', 'b'))

        """
        return _dispatched_lookup(words, self)

    def __getitem__(self, item):
        return self._cutoff if item == self.unk_label else self.counts[item]

    def __contains__(self, item):
        """Only consider items with counts GE to cutoff as being in the
        vocabulary."""
        return self[item] >= self.cutoff

    def __iter__(self):
        """Building on membership check define how to iterate over
        vocabulary."""
        return chain(
            (item for item in self.counts if item in self),
            [self.unk_label] if self.counts else [],
        )

    def __len__(self):
        """Computing size of vocabulary reflects the cutoff."""
        return self._len

    def __eq__(self, other):
        return (
            self.unk_label == other.unk_label
            and self.cutoff == other.cutoff
            and self.counts == other.counts
        )

    def __str__(self):
        return "<{} with cutoff={} unk_label='{}' and {} items>".format(
            self.__class__.__name__, self.cutoff, self.unk_label, len(self)
        )

# === NexusCore/openenv\Lib\site-packages\nltk\corpus\reader\bcp47.py ===
# Natural Language Toolkit: BCP-47 language tags
#
# Copyright (C) 2022-2023 NLTK Project
# Author: Eric Kafe <kafe.eric@gmail.com>
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT

import re
from warnings import warn
from xml.etree import ElementTree as et

from nltk.corpus.reader import CorpusReader


class BCP47CorpusReader(CorpusReader):
    """
    Parse BCP-47 composite language tags

    Supports all the main subtags, and the 'u-sd' extension:

    >>> from nltk.corpus import bcp47
    >>> bcp47.name('oc-gascon-u-sd-fr64')
    'Occitan (post 1500): Gascon: Pyrénées-Atlantiques'

    Can load a conversion table to Wikidata Q-codes:
    >>> bcp47.load_wiki_q()
    >>> bcp47.wiki_q['en-GI-spanglis']
    'Q79388'

    """

    def __init__(self, root, fileids):
        """Read the BCP-47 database"""
        super().__init__(root, fileids)
        self.langcode = {}
        with self.open("iana/language-subtag-registry.txt") as fp:
            self.db = self.data_dict(fp.read().split("%%\n"))
        with self.open("cldr/common-subdivisions-en.xml") as fp:
            self.subdiv = self.subdiv_dict(
                et.parse(fp).iterfind("localeDisplayNames/subdivisions/subdivision")
            )
        self.morphology()

    def load_wiki_q(self):
        """Load conversion table to Wikidata Q-codes (only if needed)"""
        with self.open("cldr/tools-cldr-rdf-external-entityToCode.tsv") as fp:
            self.wiki_q = self.wiki_dict(fp.read().strip().split("\n")[1:])

    def wiki_dict(self, lines):
        """Convert Wikidata list of Q-codes to a BCP-47 dictionary"""
        return {
            pair[1]: pair[0].split("/")[-1]
            for pair in [line.strip().split("\t") for line in lines]
        }

    def subdiv_dict(self, subdivs):
        """Convert the CLDR subdivisions list to a dictionary"""
        return {sub.attrib["type"]: sub.text for sub in subdivs}

    def morphology(self):
        self.casing = {
            "language": str.lower,
            "extlang": str.lower,
            "script": str.title,
            "region": str.upper,
            "variant": str.lower,
        }
        dig = "[0-9]"
        low = "[a-z]"
        up = "[A-Z]"
        alnum = "[a-zA-Z0-9]"
        self.format = {
            "language": re.compile(f"{low*3}?"),
            "extlang": re.compile(f"{low*3}"),
            "script": re.compile(f"{up}{low*3}"),
            "region": re.compile(f"({up*2})|({dig*3})"),
            "variant": re.compile(f"{alnum*4}{(alnum+'?')*4}"),
            "singleton": re.compile(f"{low}"),
        }

    def data_dict(self, records):
        """Convert the BCP-47 language subtag registry to a dictionary"""
        self.version = records[0].replace("File-Date:", "").strip()
        dic = {}
        dic["deprecated"] = {}
        for label in [
            "language",
            "extlang",
            "script",
            "region",
            "variant",
            "redundant",
            "grandfathered",
        ]:
            dic["deprecated"][label] = {}
        for record in records[1:]:
            fields = [field.split(": ") for field in record.strip().split("\n")]
            typ = fields[0][1]
            tag = fields[1][1]
            if typ not in dic:
                dic[typ] = {}
            subfields = {}
            for field in fields[2:]:
                if len(field) == 2:
                    [key, val] = field
                    if key not in subfields:
                        subfields[key] = [val]
                    else:  # multiple value
                        subfields[key].append(val)
                else:  # multiline field
                    subfields[key][-1] += " " + field[0].strip()
                if (
                    "Deprecated" not in record
                    and typ == "language"
                    and key == "Description"
                ):
                    self.langcode[subfields[key][-1]] = tag
            for key in subfields:
                if len(subfields[key]) == 1:  # single value
                    subfields[key] = subfields[key][0]
            if "Deprecated" in record:
                dic["deprecated"][typ][tag] = subfields
            else:
                dic[typ][tag] = subfields
        return dic

    def val2str(self, val):
        """Return only first value"""
        if type(val) == list:
            #            val = "/".join(val) # Concatenate all values
            val = val[0]
        return val

    def lang2str(self, lg_record):
        """Concatenate subtag values"""
        name = f"{lg_record['language']}"
        for label in ["extlang", "script", "region", "variant", "extension"]:
            if label in lg_record:
                name += f": {lg_record[label]}"
        return name

    def parse_tag(self, tag):
        """Convert a BCP-47 tag to a dictionary of labelled subtags"""
        subtags = tag.split("-")
        lang = {}
        labels = ["language", "extlang", "script", "region", "variant", "variant"]
        while subtags and labels:
            subtag = subtags.pop(0)
            found = False
            while labels:
                label = labels.pop(0)
                subtag = self.casing[label](subtag)
                if self.format[label].fullmatch(subtag):
                    if subtag in self.db[label]:
                        found = True
                        valstr = self.val2str(self.db[label][subtag]["Description"])
                        if label == "variant" and label in lang:
                            lang[label] += ": " + valstr
                        else:
                            lang[label] = valstr
                        break
                    elif subtag in self.db["deprecated"][label]:
                        found = True
                        note = f"The {subtag!r} {label} code is deprecated"
                        if "Preferred-Value" in self.db["deprecated"][label][subtag]:
                            prefer = self.db["deprecated"][label][subtag][
                                "Preferred-Value"
                            ]
                            note += f"', prefer '{self.val2str(prefer)}'"
                        lang[label] = self.val2str(
                            self.db["deprecated"][label][subtag]["Description"]
                        )
                        warn(note)
                        break
            if not found:
                if subtag == "u" and subtags[0] == "sd":  # CLDR regional subdivisions
                    sd = subtags[1]
                    if sd in self.subdiv:
                        ext = self.subdiv[sd]
                    else:
                        ext = f"<Unknown subdivision: {ext}>"
                else:  # other extension subtags are not supported yet
                    ext = f"{subtag}{''.join(['-'+ext for ext in subtags])}".lower()
                    if not self.format["singleton"].fullmatch(subtag):
                        ext = f"<Invalid extension: {ext}>"
                        warn(ext)
                lang["extension"] = ext
                subtags = []
        return lang

    def name(self, tag):
        """
        Convert a BCP-47 tag to a colon-separated string of subtag names

        >>> from nltk.corpus import bcp47
        >>> bcp47.name('ca-Latn-ES-valencia')
        'Catalan: Latin: Spain: Valencian'

        """
        for label in ["redundant", "grandfathered"]:
            val = None
            if tag in self.db[label]:
                val = f"{self.db[label][tag]['Description']}"
                note = f"The {tag!r} code is {label}"
            elif tag in self.db["deprecated"][label]:
                val = f"{self.db['deprecated'][label][tag]['Description']}"
                note = f"The {tag!r} code is {label} and deprecated"
                if "Preferred-Value" in self.db["deprecated"][label][tag]:
                    prefer = self.db["deprecated"][label][tag]["Preferred-Value"]
                    note += f", prefer {self.val2str(prefer)!r}"
            if val:
                warn(note)
                return val
        try:
            return self.lang2str(self.parse_tag(tag))
        except:
            warn(f"Tag {tag!r} was not recognized")
            return None

# === NexusCore/openenv\Lib\site-packages\huggingface_hub\inference_api.py ===
import io
from typing import Any, Dict, List, Optional, Union

from . import constants
from .hf_api import HfApi
from .utils import build_hf_headers, get_session, is_pillow_available, logging, validate_hf_hub_args
from .utils._deprecation import _deprecate_method


logger = logging.get_logger(__name__)


ALL_TASKS = [
    # NLP
    "text-classification",
    "token-classification",
    "table-question-answering",
    "question-answering",
    "zero-shot-classification",
    "translation",
    "summarization",
    "conversational",
    "feature-extraction",
    "text-generation",
    "text2text-generation",
    "fill-mask",
    "sentence-similarity",
    # Audio
    "text-to-speech",
    "automatic-speech-recognition",
    "audio-to-audio",
    "audio-classification",
    "voice-activity-detection",
    # Computer vision
    "image-classification",
    "object-detection",
    "image-segmentation",
    "text-to-image",
    "image-to-image",
    # Others
    "tabular-classification",
    "tabular-regression",
]


class InferenceApi:
    """Client to configure requests and make calls to the HuggingFace Inference API.

    Example:

    ```python
    >>> from huggingface_hub.inference_api import InferenceApi

    >>> # Mask-fill example
    >>> inference = InferenceApi("bert-base-uncased")
    >>> inference(inputs="The goal of life is [MASK].")
    [{'sequence': 'the goal of life is life.', 'score': 0.10933292657136917, 'token': 2166, 'token_str': 'life'}]

    >>> # Question Answering example
    >>> inference = InferenceApi("deepset/roberta-base-squad2")
    >>> inputs = {
    ...     "question": "What's my name?",
    ...     "context": "My name is Clara and I live in Berkeley.",
    ... }
    >>> inference(inputs)
    {'score': 0.9326569437980652, 'start': 11, 'end': 16, 'answer': 'Clara'}

    >>> # Zero-shot example
    >>> inference = InferenceApi("typeform/distilbert-base-uncased-mnli")
    >>> inputs = "Hi, I recently bought a device from your company but it is not working as advertised and I would like to get reimbursed!"
    >>> params = {"candidate_labels": ["refund", "legal", "faq"]}
    >>> inference(inputs, params)
    {'sequence': 'Hi, I recently bought a device from your company but it is not working as advertised and I would like to get reimbursed!', 'labels': ['refund', 'faq', 'legal'], 'scores': [0.9378499388694763, 0.04914155602455139, 0.013008488342165947]}

    >>> # Overriding configured task
    >>> inference = InferenceApi("bert-base-uncased", task="feature-extraction")

    >>> # Text-to-image
    >>> inference = InferenceApi("stabilityai/stable-diffusion-2-1")
    >>> inference("cat")
    <PIL.PngImagePlugin.PngImageFile image (...)>

    >>> # Return as raw response to parse the output yourself
    >>> inference = InferenceApi("mio/amadeus")
    >>> response = inference("hello world", raw_response=True)
    >>> response.headers
    {"Content-Type": "audio/flac", ...}
    >>> response.content # raw bytes from server
    b'(...)'
    ```
    """

    @validate_hf_hub_args
    @_deprecate_method(
        version="1.0",
        message=(
            "`InferenceApi` client is deprecated in favor of the more feature-complete `InferenceClient`. Check out"
            " this guide to learn how to convert your script to use it:"
            " https://huggingface.co/docs/huggingface_hub/guides/inference#legacy-inferenceapi-client."
        ),
    )
    def __init__(
        self,
        repo_id: str,
        task: Optional[str] = None,
        token: Optional[str] = None,
        gpu: bool = False,
    ):
        """Inits headers and API call information.

        Args:
            repo_id (``str``):
                Id of repository (e.g. `user/bert-base-uncased`).
            task (``str``, `optional`, defaults ``None``):
                Whether to force a task instead of using task specified in the
                repository.
            token (`str`, `optional`):
                The API token to use as HTTP bearer authorization. This is not
                the authentication token. You can find the token in
                https://huggingface.co/settings/token. Alternatively, you can
                find both your organizations and personal API tokens using
                `HfApi().whoami(token)`.
            gpu (`bool`, `optional`, defaults `False`):
                Whether to use GPU instead of CPU for inference(requires Startup
                plan at least).
        """
        self.options = {"wait_for_model": True, "use_gpu": gpu}
        self.headers = build_hf_headers(token=token)

        # Configure task
        model_info = HfApi(token=token).model_info(repo_id=repo_id)
        if not model_info.pipeline_tag and not task:
            raise ValueError(
                "Task not specified in the repository. Please add it to the model card"
                " using pipeline_tag"
                " (https://huggingface.co/docs#how-is-a-models-type-of-inference-api-and-widget-determined)"
            )

        if task and task != model_info.pipeline_tag:
            if task not in ALL_TASKS:
                raise ValueError(f"Invalid task {task}. Make sure it's valid.")

            logger.warning(
                "You're using a different task than the one specified in the"
                " repository. Be sure to know what you're doing :)"
            )
            self.task = task
        else:
            assert model_info.pipeline_tag is not None, "Pipeline tag cannot be None"
            self.task = model_info.pipeline_tag

        self.api_url = f"{constants.INFERENCE_ENDPOINT}/pipeline/{self.task}/{repo_id}"

    def __repr__(self):
        # Do not add headers to repr to avoid leaking token.
        return f"InferenceAPI(api_url='{self.api_url}', task='{self.task}', options={self.options})"

    def __call__(
        self,
        inputs: Optional[Union[str, Dict, List[str], List[List[str]]]] = None,
        params: Optional[Dict] = None,
        data: Optional[bytes] = None,
        raw_response: bool = False,
    ) -> Any:
        """Make a call to the Inference API.

        Args:
            inputs (`str` or `Dict` or `List[str]` or `List[List[str]]`, *optional*):
                Inputs for the prediction.
            params (`Dict`, *optional*):
                Additional parameters for the models. Will be sent as `parameters` in the
                payload.
            data (`bytes`, *optional*):
                Bytes content of the request. In this case, leave `inputs` and `params` empty.
            raw_response (`bool`, defaults to `False`):
                If `True`, the raw `Response` object is returned. You can parse its content
                as preferred. By default, the content is parsed into a more practical format
                (json dictionary or PIL Image for example).
        """
        # Build payload
        payload: Dict[str, Any] = {
            "options": self.options,
        }
        if inputs:
            payload["inputs"] = inputs
        if params:
            payload["parameters"] = params

        # Make API call
        response = get_session().post(self.api_url, headers=self.headers, json=payload, data=data)

        # Let the user handle the response
        if raw_response:
            return response

        # By default, parse the response for the user.
        content_type = response.headers.get("Content-Type") or ""
        if content_type.startswith("image"):
            if not is_pillow_available():
                raise ImportError(
                    f"Task '{self.task}' returned as image but Pillow is not installed."
                    " Please install it (`pip install Pillow`) or pass"
                    " `raw_response=True` to get the raw `Response` object and parse"
                    " the image by yourself."
                )

            from PIL import Image

            return Image.open(io.BytesIO(response.content))
        elif content_type == "application/json":
            return response.json()
        else:
            raise NotImplementedError(
                f"{content_type} output type is not implemented yet. You can pass"
                " `raw_response=True` to get the raw `Response` object and parse the"
                " output by yourself."
            )

# === NexusCore/openenv\Lib\site-packages\PIL\PalmImagePlugin.py ===
#
# The Python Imaging Library.
# $Id$
#

##
# Image plugin for Palm pixmap images (output only).
##
from __future__ import annotations

from typing import IO

from . import Image, ImageFile
from ._binary import o8
from ._binary import o16be as o16b

# fmt: off
_Palm8BitColormapValues = (
    (255, 255, 255), (255, 204, 255), (255, 153, 255), (255, 102, 255),
    (255,  51, 255), (255,   0, 255), (255, 255, 204), (255, 204, 204),
    (255, 153, 204), (255, 102, 204), (255,  51, 204), (255,   0, 204),
    (255, 255, 153), (255, 204, 153), (255, 153, 153), (255, 102, 153),
    (255,  51, 153), (255,   0, 153), (204, 255, 255), (204, 204, 255),
    (204, 153, 255), (204, 102, 255), (204,  51, 255), (204,   0, 255),
    (204, 255, 204), (204, 204, 204), (204, 153, 204), (204, 102, 204),
    (204,  51, 204), (204,   0, 204), (204, 255, 153), (204, 204, 153),
    (204, 153, 153), (204, 102, 153), (204,  51, 153), (204,   0, 153),
    (153, 255, 255), (153, 204, 255), (153, 153, 255), (153, 102, 255),
    (153,  51, 255), (153,   0, 255), (153, 255, 204), (153, 204, 204),
    (153, 153, 204), (153, 102, 204), (153,  51, 204), (153,   0, 204),
    (153, 255, 153), (153, 204, 153), (153, 153, 153), (153, 102, 153),
    (153,  51, 153), (153,   0, 153), (102, 255, 255), (102, 204, 255),
    (102, 153, 255), (102, 102, 255), (102,  51, 255), (102,   0, 255),
    (102, 255, 204), (102, 204, 204), (102, 153, 204), (102, 102, 204),
    (102,  51, 204), (102,   0, 204), (102, 255, 153), (102, 204, 153),
    (102, 153, 153), (102, 102, 153), (102,  51, 153), (102,   0, 153),
    (51,  255, 255), (51,  204, 255), (51,  153, 255), (51,  102, 255),
    (51,   51, 255), (51,    0, 255), (51,  255, 204), (51,  204, 204),
    (51,  153, 204), (51,  102, 204), (51,   51, 204), (51,    0, 204),
    (51,  255, 153), (51,  204, 153), (51,  153, 153), (51,  102, 153),
    (51,   51, 153), (51,    0, 153), (0,   255, 255), (0,   204, 255),
    (0,   153, 255), (0,   102, 255), (0,    51, 255), (0,     0, 255),
    (0,   255, 204), (0,   204, 204), (0,   153, 204), (0,   102, 204),
    (0,    51, 204), (0,     0, 204), (0,   255, 153), (0,   204, 153),
    (0,   153, 153), (0,   102, 153), (0,    51, 153), (0,     0, 153),
    (255, 255, 102), (255, 204, 102), (255, 153, 102), (255, 102, 102),
    (255,  51, 102), (255,   0, 102), (255, 255,  51), (255, 204,  51),
    (255, 153,  51), (255, 102,  51), (255,  51,  51), (255,   0,  51),
    (255, 255,   0), (255, 204,   0), (255, 153,   0), (255, 102,   0),
    (255,  51,   0), (255,   0,   0), (204, 255, 102), (204, 204, 102),
    (204, 153, 102), (204, 102, 102), (204,  51, 102), (204,   0, 102),
    (204, 255,  51), (204, 204,  51), (204, 153,  51), (204, 102,  51),
    (204,  51,  51), (204,   0,  51), (204, 255,   0), (204, 204,   0),
    (204, 153,   0), (204, 102,   0), (204,  51,   0), (204,   0,   0),
    (153, 255, 102), (153, 204, 102), (153, 153, 102), (153, 102, 102),
    (153,  51, 102), (153,   0, 102), (153, 255,  51), (153, 204,  51),
    (153, 153,  51), (153, 102,  51), (153,  51,  51), (153,   0,  51),
    (153, 255,   0), (153, 204,   0), (153, 153,   0), (153, 102,   0),
    (153,  51,   0), (153,   0,   0), (102, 255, 102), (102, 204, 102),
    (102, 153, 102), (102, 102, 102), (102,  51, 102), (102,   0, 102),
    (102, 255,  51), (102, 204,  51), (102, 153,  51), (102, 102,  51),
    (102,  51,  51), (102,   0,  51), (102, 255,   0), (102, 204,   0),
    (102, 153,   0), (102, 102,   0), (102,  51,   0), (102,   0,   0),
    (51,  255, 102), (51,  204, 102), (51,  153, 102), (51,  102, 102),
    (51,   51, 102), (51,    0, 102), (51,  255,  51), (51,  204,  51),
    (51,  153,  51), (51,  102,  51), (51,   51,  51), (51,    0,  51),
    (51,  255,   0), (51,  204,   0), (51,  153,   0), (51,  102,   0),
    (51,   51,   0), (51,    0,   0), (0,   255, 102), (0,   204, 102),
    (0,   153, 102), (0,   102, 102), (0,    51, 102), (0,     0, 102),
    (0,   255,  51), (0,   204,  51), (0,   153,  51), (0,   102,  51),
    (0,    51,  51), (0,     0,  51), (0,   255,   0), (0,   204,   0),
    (0,   153,   0), (0,   102,   0), (0,    51,   0), (17,   17,  17),
    (34,   34,  34), (68,   68,  68), (85,   85,  85), (119, 119, 119),
    (136, 136, 136), (170, 170, 170), (187, 187, 187), (221, 221, 221),
    (238, 238, 238), (192, 192, 192), (128,   0,   0), (128,   0, 128),
    (0,   128,   0), (0,   128, 128), (0,     0,   0), (0,     0,   0),
    (0,     0,   0), (0,     0,   0), (0,     0,   0), (0,     0,   0),
    (0,     0,   0), (0,     0,   0), (0,     0,   0), (0,     0,   0),
    (0,     0,   0), (0,     0,   0), (0,     0,   0), (0,     0,   0),
    (0,     0,   0), (0,     0,   0), (0,     0,   0), (0,     0,   0),
    (0,     0,   0), (0,     0,   0), (0,     0,   0), (0,     0,   0),
    (0,     0,   0), (0,     0,   0), (0,     0,   0), (0,     0,   0))
# fmt: on


# so build a prototype image to be used for palette resampling
def build_prototype_image() -> Image.Image:
    image = Image.new("L", (1, len(_Palm8BitColormapValues)))
    image.putdata(list(range(len(_Palm8BitColormapValues))))
    palettedata: tuple[int, ...] = ()
    for colormapValue in _Palm8BitColormapValues:
        palettedata += colormapValue
    palettedata += (0, 0, 0) * (256 - len(_Palm8BitColormapValues))
    image.putpalette(palettedata)
    return image


Palm8BitColormapImage = build_prototype_image()

# OK, we now have in Palm8BitColormapImage,
# a "P"-mode image with the right palette
#
# --------------------------------------------------------------------

_FLAGS = {"custom-colormap": 0x4000, "is-compressed": 0x8000, "has-transparent": 0x2000}

_COMPRESSION_TYPES = {"none": 0xFF, "rle": 0x01, "scanline": 0x00}


#
# --------------------------------------------------------------------

##
# (Internal) Image save plugin for the Palm format.


def _save(im: Image.Image, fp: IO[bytes], filename: str | bytes) -> None:
    if im.mode == "P":
        rawmode = "P"
        bpp = 8
        version = 1

    elif im.mode == "L":
        if im.encoderinfo.get("bpp") in (1, 2, 4):
            # this is 8-bit grayscale, so we shift it to get the high-order bits,
            # and invert it because
            # Palm does grayscale from white (0) to black (1)
            bpp = im.encoderinfo["bpp"]
            maxval = (1 << bpp) - 1
            shift = 8 - bpp
            im = im.point(lambda x: maxval - (x >> shift))
        elif im.info.get("bpp") in (1, 2, 4):
            # here we assume that even though the inherent mode is 8-bit grayscale,
            # only the lower bpp bits are significant.
            # We invert them to match the Palm.
            bpp = im.info["bpp"]
            maxval = (1 << bpp) - 1
            im = im.point(lambda x: maxval - (x & maxval))
        else:
            msg = f"cannot write mode {im.mode} as Palm"
            raise OSError(msg)

        # we ignore the palette here
        im._mode = "P"
        rawmode = f"P;{bpp}"
        version = 1

    elif im.mode == "1":
        # monochrome -- write it inverted, as is the Palm standard
        rawmode = "1;I"
        bpp = 1
        version = 0

    else:
        msg = f"cannot write mode {im.mode} as Palm"
        raise OSError(msg)

    #
    # make sure image data is available
    im.load()

    # write header

    cols = im.size[0]
    rows = im.size[1]

    rowbytes = int((cols + (16 // bpp - 1)) / (16 // bpp)) * 2
    transparent_index = 0
    compression_type = _COMPRESSION_TYPES["none"]

    flags = 0
    if im.mode == "P":
        flags |= _FLAGS["custom-colormap"]
        colormap = im.im.getpalette()
        colors = len(colormap) // 3
        colormapsize = 4 * colors + 2
    else:
        colormapsize = 0

    if "offset" in im.info:
        offset = (rowbytes * rows + 16 + 3 + colormapsize) // 4
    else:
        offset = 0

    fp.write(o16b(cols) + o16b(rows) + o16b(rowbytes) + o16b(flags))
    fp.write(o8(bpp))
    fp.write(o8(version))
    fp.write(o16b(offset))
    fp.write(o8(transparent_index))
    fp.write(o8(compression_type))
    fp.write(o16b(0))  # reserved by Palm

    # now write colormap if necessary

    if colormapsize:
        fp.write(o16b(colors))
        for i in range(colors):
            fp.write(o8(i))
            fp.write(colormap[3 * i : 3 * i + 3])

    # now convert data to raw form
    ImageFile._save(
        im, fp, [ImageFile._Tile("raw", (0, 0) + im.size, 0, (rawmode, rowbytes, 1))]
    )

    if hasattr(fp, "flush"):
        fp.flush()


#
# --------------------------------------------------------------------

Image.register_save("Palm", _save)

Image.register_extension("Palm", ".palm")

Image.register_mime("Palm", "image/palm")

# === NexusCore/openenv\Lib\site-packages\html2image\browsers\chrome_cdp.py ===
from .browser import CDPBrowser
from .search_utils import find_chrome

import os
import subprocess

import requests
import json
from websocket import create_connection
import base64

import websocket
# websocket.enableTrace(True) 


class ChromeCDP(CDPBrowser):

    def __init__(
        self, executable=None, flags=None,
        print_command=False, cdp_port=9222,
        disable_logging=False,
    ):
        self.executable = executable
        if not flags:
            # for some reason, default-background-color prevents
            # the browser from running
            self.flags = [
                '--hide-scrollbars',
            ]
        else:
            self.flags = [flags] if isinstance(flags, str) else flags

        self.print_command = print_command
        self.cdp_port = cdp_port
        self._disable_logging = disable_logging

        self._ws = None  # Websocket connection
        self.proc = None  # Headless browser Popen object

        self.__id = 0

    @property
    def executable(self):
        return self._executable

    @executable.setter
    def executable(self, value):
        self._executable = find_chrome(value)

    @property
    def disable_logging(self):
        return self._disable_logging
    
    @disable_logging.setter
    def disable_logging(self, value):
        self._disable_logging = value

    @property
    def ws(self):

        if not self._ws:
            print(f'----------- http://localhost:{self.cdp_port}/json/version')
            r = requests.get(f'http://localhost:{self.cdp_port}/json')  # TODO use page websocket instead of browser one
            print(f'{r.json()}')
            print(f'Using ws url= {r.json()[0]["webSocketDebuggerUrl"]}')
            self._ws = create_connection(r.json()[0]['webSocketDebuggerUrl'])
            print('Successfully connected to ws.')
        return self._ws

    @property
    def _id(self):
        self.__id += 1
        return self.__id

    def cdp_send(self, method, **params):
        """
        """
        print(f'cdp_send: {method} {params}')
        return self.ws.send(
            json.dumps({
                'id': self._id,
                'method': method,
                'params': params,
            })
        )

    def screenshot(
        self,
        input,
        output_path,
        output_file='screenshot.png',
        size=(1920, 1080),
    ):
        """
        """
        # Useful documentation about the Chrome DevTools Protocol:
        # https://chromedevtools.github.io/devtools-protocol/

        # "Enabling" the page allows to receive the Page.loadEventFired event
        self.cdp_send('Page.enable')

        self.cdp_send('Page.navigate', url=input)

        print('wait for page to load')

        # Wait for page to load entirely
        while True:
            message = json.loads(self.ws.recv())
            method = message.get('method')
            print(f'{method}')
            if method == 'Page.loadEventFired':
                break
        
        print('page disable')
        self.cdp_send('Page.disable')

        self.cdp_send(
            'Emulation.setDeviceMetricsOverride',
            width=size[0],
            height=size[1],
            deviceScaleFactor=0,  # 0 disables the override
            mobile=False,
        )

        print('send Page.captureScreenshot')

        self.cdp_send(
            'Page.captureScreenshot',
            # captureBeyondViewport=True,
            # clip={
            #     'width': size[0],
            #     'height': size[1],
            #     'x': 500,
            #     'y': 200,
            #     'scale': 4
            # }
        )

        print('writing to file..')

        # get screenshot data when ready,
        # while potentially skipping unneeded messages
        while True:
            message = json.loads(self.ws.recv())
            # todo capture and display errors ?
            if 'result' in message and 'data' in message['result']:
                # retrive base64 encoded image data
                img_data = message['result']['data']
                break

        # Decode and write image data to file
        with open(os.path.join(output_path, output_file), 'wb') as f:
            f.write(base64.b64decode(img_data))

    def get_page_infos(self):
        """
        """
        self.cdp_send('Page.getLayoutMetrics')

        while True:
            message = json.loads(self.ws.recv())
            print(f'{message}')
            if 'result' in message and 'layoutViewport' in message['result']:
                return message['result']

    def print_pdf(self):
        # TODO : Page.printToPDF
        pass

    def __enter__(self):
        """
        """
        if not self.disable_logging:
            print(
                'Starting headless Chrome with '
                f'--remote-debugging-port={self.cdp_port}.'
            )

        self.flags.append('--remote-allow-origins=*')

        command = [
            f'{self.executable}',
            '--window-size=1920,1080',
            f'--remote-debugging-port={self.cdp_port}',
            '--headless=new',
            '--no-first-run',
            '--no-default-browser-check',
            *self.flags,
        ]

        # if self.print_command:
        if True:
            print(' '.join(command))

        self.proc = subprocess.Popen(command, shell=True)

    def __exit__(self, *exc):
        """
        """
        if self.disable_logging:
            print(f'Closing headless Chrome instance on port {self.cdp_port}.')

        # check if the process is still running
        if self.proc.poll() is None:
            # ensure that it is properly killed
            try:
                self.cdp_send('Browser.close')
                self.ws.close()
                print('(TODO) Closed CDP and WebSocket connections properly.')
            except Exception:
                print('Could not properly close the CDP and WebSocket connections.')
            
            try:
                self.proc.terminate()
                print('Closed Chrome properly.')
            except Exception:
                print('Could not properly kill Chrome.')

# === NexusCore/openenv\Lib\site-packages\litellm\integrations\weights_biases.py ===
imported_openAIResponse = True
try:
    import io
    import logging
    import sys
    from typing import Any, Dict, List, Optional, TypeVar

    from wandb.sdk.data_types import trace_tree

    if sys.version_info >= (3, 8):
        from typing import Literal, Protocol
    else:
        from typing_extensions import Literal, Protocol

    logger = logging.getLogger(__name__)

    K = TypeVar("K", bound=str)
    V = TypeVar("V")

    class OpenAIResponse(Protocol[K, V]):  # type: ignore
        # contains a (known) object attribute
        object: Literal["chat.completion", "edit", "text_completion"]

        def __getitem__(self, key: K) -> V:
            ...  # noqa

        def get(self, key: K, default: Optional[V] = None) -> Optional[V]:  # noqa
            ...  # pragma: no cover

    class OpenAIRequestResponseResolver:
        def __call__(
            self,
            request: Dict[str, Any],
            response: OpenAIResponse,
            time_elapsed: float,
        ) -> Optional[trace_tree.WBTraceTree]:
            try:
                if response["object"] == "edit":
                    return self._resolve_edit(request, response, time_elapsed)
                elif response["object"] == "text_completion":
                    return self._resolve_completion(request, response, time_elapsed)
                elif response["object"] == "chat.completion":
                    return self._resolve_chat_completion(
                        request, response, time_elapsed
                    )
                else:
                    logger.info(f"Unknown OpenAI response object: {response['object']}")
            except Exception as e:
                logger.warning(f"Failed to resolve request/response: {e}")
            return None

        @staticmethod
        def results_to_trace_tree(
            request: Dict[str, Any],
            response: OpenAIResponse,
            results: List[trace_tree.Result],
            time_elapsed: float,
        ) -> trace_tree.WBTraceTree:
            """Converts the request, response, and results into a trace tree.

            params:
                request: The request dictionary
                response: The response object
                results: A list of results object
                time_elapsed: The time elapsed in seconds
            returns:
                A wandb trace tree object.
            """
            start_time_ms = int(round(response["created"] * 1000))
            end_time_ms = start_time_ms + int(round(time_elapsed * 1000))
            span = trace_tree.Span(
                name=f"{response.get('model', 'openai')}_{response['object']}_{response.get('created')}",
                attributes=dict(response),  # type: ignore
                start_time_ms=start_time_ms,
                end_time_ms=end_time_ms,
                span_kind=trace_tree.SpanKind.LLM,
                results=results,
            )
            model_obj = {"request": request, "response": response, "_kind": "openai"}
            return trace_tree.WBTraceTree(root_span=span, model_dict=model_obj)

        def _resolve_edit(
            self,
            request: Dict[str, Any],
            response: OpenAIResponse,
            time_elapsed: float,
        ) -> trace_tree.WBTraceTree:
            """Resolves the request and response objects for `openai.Edit`."""
            request_str = (
                f"\n\n**Instruction**: {request['instruction']}\n\n"
                f"**Input**: {request['input']}\n"
            )
            choices = [
                f"\n\n**Edited**: {choice['text']}\n" for choice in response["choices"]
            ]

            return self._request_response_result_to_trace(
                request=request,
                response=response,
                request_str=request_str,
                choices=choices,
                time_elapsed=time_elapsed,
            )

        def _resolve_completion(
            self,
            request: Dict[str, Any],
            response: OpenAIResponse,
            time_elapsed: float,
        ) -> trace_tree.WBTraceTree:
            """Resolves the request and response objects for `openai.Completion`."""
            request_str = f"\n\n**Prompt**: {request['prompt']}\n"
            choices = [
                f"\n\n**Completion**: {choice['text']}\n"
                for choice in response["choices"]
            ]

            return self._request_response_result_to_trace(
                request=request,
                response=response,
                request_str=request_str,
                choices=choices,
                time_elapsed=time_elapsed,
            )

        def _resolve_chat_completion(
            self,
            request: Dict[str, Any],
            response: OpenAIResponse,
            time_elapsed: float,
        ) -> trace_tree.WBTraceTree:
            """Resolves the request and response objects for `openai.Completion`."""
            prompt = io.StringIO()
            for message in request["messages"]:
                prompt.write(f"\n\n**{message['role']}**: {message['content']}\n")
            request_str = prompt.getvalue()

            choices = [
                f"\n\n**{choice['message']['role']}**: {choice['message']['content']}\n"
                for choice in response["choices"]
            ]

            return self._request_response_result_to_trace(
                request=request,
                response=response,
                request_str=request_str,
                choices=choices,
                time_elapsed=time_elapsed,
            )

        def _request_response_result_to_trace(
            self,
            request: Dict[str, Any],
            response: OpenAIResponse,
            request_str: str,
            choices: List[str],
            time_elapsed: float,
        ) -> trace_tree.WBTraceTree:
            """Resolves the request and response objects for `openai.Completion`."""
            results = [
                trace_tree.Result(
                    inputs={"request": request_str},
                    outputs={"response": choice},
                )
                for choice in choices
            ]
            trace = self.results_to_trace_tree(request, response, results, time_elapsed)
            return trace

except Exception:
    imported_openAIResponse = False


#### What this does ####
#    On success, logs events to Langfuse
import traceback


class WeightsBiasesLogger:
    # Class variables or attributes
    def __init__(self):
        try:
            pass
        except Exception:
            raise Exception(
                "\033[91m wandb not installed, try running 'pip install wandb' to fix this error\033[0m"
            )
        if imported_openAIResponse is False:
            raise Exception(
                "\033[91m wandb not installed, try running 'pip install wandb' to fix this error\033[0m"
            )
        self.resolver = OpenAIRequestResponseResolver()

    def log_event(self, kwargs, response_obj, start_time, end_time, print_verbose):
        # Method definition
        import wandb

        try:
            print_verbose(f"W&B Logging - Enters logging function for model {kwargs}")
            run = wandb.init()
            print_verbose(response_obj)

            trace = self.resolver(
                kwargs, response_obj, (end_time - start_time).total_seconds()
            )

            if trace is not None and run is not None:
                run.log({"trace": trace})

            if run is not None:
                run.finish()
                print_verbose(
                    f"W&B Logging Logging - final response object: {response_obj}"
                )
        except Exception:
            print_verbose(f"W&B Logging Layer Error - {traceback.format_exc()}")
            pass

# === NexusCore/openenv\Lib\site-packages\setuptools\command\sdist.py ===
from __future__ import annotations

import contextlib
import os
import re
from itertools import chain
from typing import ClassVar

from .._importlib import metadata
from ..dist import Distribution
from .build import _ORIGINAL_SUBCOMMANDS

import distutils.command.sdist as orig
from distutils import log

_default_revctrl = list


def walk_revctrl(dirname=''):
    """Find all files under revision control"""
    for ep in metadata.entry_points(group='setuptools.file_finders'):
        yield from ep.load()(dirname)


class sdist(orig.sdist):
    """Smart sdist that finds anything supported by revision control"""

    user_options = [
        ('formats=', None, "formats for source distribution (comma-separated list)"),
        (
            'keep-temp',
            'k',
            "keep the distribution tree around after creating archive file(s)",
        ),
        (
            'dist-dir=',
            'd',
            "directory to put the source distribution archive(s) in [default: dist]",
        ),
        (
            'owner=',
            'u',
            "Owner name used when creating a tar file [default: current user]",
        ),
        (
            'group=',
            'g',
            "Group name used when creating a tar file [default: current group]",
        ),
    ]

    distribution: Distribution  # override distutils.dist.Distribution with setuptools.dist.Distribution
    negative_opt: ClassVar[dict[str, str]] = {}

    README_EXTENSIONS = ['', '.rst', '.txt', '.md']
    READMES = tuple(f'README{ext}' for ext in README_EXTENSIONS)

    def run(self) -> None:
        self.run_command('egg_info')
        ei_cmd = self.get_finalized_command('egg_info')
        self.filelist = ei_cmd.filelist
        self.filelist.append(os.path.join(ei_cmd.egg_info, 'SOURCES.txt'))
        self.check_readme()

        # Run sub commands
        for cmd_name in self.get_sub_commands():
            self.run_command(cmd_name)

        self.make_distribution()

        dist_files = getattr(self.distribution, 'dist_files', [])
        for file in self.archive_files:
            data = ('sdist', '', file)
            if data not in dist_files:
                dist_files.append(data)

    def initialize_options(self) -> None:
        orig.sdist.initialize_options(self)

    def make_distribution(self) -> None:
        """
        Workaround for #516
        """
        with self._remove_os_link():
            orig.sdist.make_distribution(self)

    @staticmethod
    @contextlib.contextmanager
    def _remove_os_link():
        """
        In a context, remove and restore os.link if it exists
        """

        class NoValue:
            pass

        orig_val = getattr(os, 'link', NoValue)
        try:
            del os.link
        except Exception:
            pass
        try:
            yield
        finally:
            if orig_val is not NoValue:
                os.link = orig_val

    def add_defaults(self) -> None:
        super().add_defaults()
        self._add_defaults_build_sub_commands()

    def _add_defaults_optional(self):
        super()._add_defaults_optional()
        if os.path.isfile('pyproject.toml'):
            self.filelist.append('pyproject.toml')

    def _add_defaults_python(self):
        """getting python files"""
        if self.distribution.has_pure_modules():
            build_py = self.get_finalized_command('build_py')
            self.filelist.extend(build_py.get_source_files())
            self._add_data_files(self._safe_data_files(build_py))

    def _add_defaults_build_sub_commands(self):
        build = self.get_finalized_command("build")
        missing_cmds = set(build.get_sub_commands()) - _ORIGINAL_SUBCOMMANDS
        # ^-- the original built-in sub-commands are already handled by default.
        cmds = (self.get_finalized_command(c) for c in missing_cmds)
        files = (c.get_source_files() for c in cmds if hasattr(c, "get_source_files"))
        self.filelist.extend(chain.from_iterable(files))

    def _safe_data_files(self, build_py):
        """
        Since the ``sdist`` class is also used to compute the MANIFEST
        (via :obj:`setuptools.command.egg_info.manifest_maker`),
        there might be recursion problems when trying to obtain the list of
        data_files and ``include_package_data=True`` (which in turn depends on
        the files included in the MANIFEST).

        To avoid that, ``manifest_maker`` should be able to overwrite this
        method and avoid recursive attempts to build/analyze the MANIFEST.
        """
        return build_py.data_files

    def _add_data_files(self, data_files):
        """
        Add data files as found in build_py.data_files.
        """
        self.filelist.extend(
            os.path.join(src_dir, name)
            for _, src_dir, _, filenames in data_files
            for name in filenames
        )

    def _add_defaults_data_files(self):
        try:
            super()._add_defaults_data_files()
        except TypeError:
            log.warn("data_files contains unexpected objects")

    def prune_file_list(self) -> None:
        super().prune_file_list()
        # Prevent accidental inclusion of test-related cache dirs at the project root
        sep = re.escape(os.sep)
        self.filelist.exclude_pattern(r"^(\.tox|\.nox|\.venv)" + sep, is_regex=True)

    def check_readme(self) -> None:
        for f in self.READMES:
            if os.path.exists(f):
                return
        else:
            self.warn(
                "standard file not found: should have one of " + ', '.join(self.READMES)
            )

    def make_release_tree(self, base_dir, files) -> None:
        orig.sdist.make_release_tree(self, base_dir, files)

        # Save any egg_info command line options used to create this sdist
        dest = os.path.join(base_dir, 'setup.cfg')
        if hasattr(os, 'link') and os.path.exists(dest):
            # unlink and re-copy, since it might be hard-linked, and
            # we don't want to change the source version
            os.unlink(dest)
            self.copy_file('setup.cfg', dest)

        self.get_finalized_command('egg_info').save_version_info(dest)

    def _manifest_is_not_generated(self):
        # check for special comment used in 2.7.1 and higher
        if not os.path.isfile(self.manifest):
            return False

        with open(self.manifest, 'rb') as fp:
            first_line = fp.readline()
        return first_line != b'# file GENERATED by distutils, do NOT edit\n'

    def read_manifest(self):
        """Read the manifest file (named by 'self.manifest') and use it to
        fill in 'self.filelist', the list of files to include in the source
        distribution.
        """
        log.info("reading manifest file '%s'", self.manifest)
        manifest = open(self.manifest, 'rb')
        for bytes_line in manifest:
            # The manifest must contain UTF-8. See #303.
            try:
                line = bytes_line.decode('UTF-8')
            except UnicodeDecodeError:
                log.warn(f"{line!r} not UTF-8 decodable -- skipping")
                continue
            # ignore comments and blank lines
            line = line.strip()
            if line.startswith('#') or not line:
                continue
            self.filelist.append(line)
        manifest.close()

# === NexusCore/openenv\Lib\site-packages\starlette\middleware\base.py ===
from __future__ import annotations

import typing

import anyio
from anyio.abc import ObjectReceiveStream, ObjectSendStream

from starlette._utils import collapse_excgroups
from starlette.background import BackgroundTask
from starlette.requests import ClientDisconnect, Request
from starlette.responses import ContentStream, Response, StreamingResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send

RequestResponseEndpoint = typing.Callable[[Request], typing.Awaitable[Response]]
DispatchFunction = typing.Callable[
    [Request, RequestResponseEndpoint], typing.Awaitable[Response]
]
T = typing.TypeVar("T")


class _CachedRequest(Request):
    """
    If the user calls Request.body() from their dispatch function
    we cache the entire request body in memory and pass that to downstream middlewares,
    but if they call Request.stream() then all we do is send an
    empty body so that downstream things don't hang forever.
    """

    def __init__(self, scope: Scope, receive: Receive):
        super().__init__(scope, receive)
        self._wrapped_rcv_disconnected = False
        self._wrapped_rcv_consumed = False
        self._wrapped_rc_stream = self.stream()

    async def wrapped_receive(self) -> Message:
        # wrapped_rcv state 1: disconnected
        if self._wrapped_rcv_disconnected:
            # we've already sent a disconnect to the downstream app
            # we don't need to wait to get another one
            # (although most ASGI servers will just keep sending it)
            return {"type": "http.disconnect"}
        # wrapped_rcv state 1: consumed but not yet disconnected
        if self._wrapped_rcv_consumed:
            # since the downstream app has consumed us all that is left
            # is to send it a disconnect
            if self._is_disconnected:
                # the middleware has already seen the disconnect
                # since we know the client is disconnected no need to wait
                # for the message
                self._wrapped_rcv_disconnected = True
                return {"type": "http.disconnect"}
            # we don't know yet if the client is disconnected or not
            # so we'll wait until we get that message
            msg = await self.receive()
            if msg["type"] != "http.disconnect":  # pragma: no cover
                # at this point a disconnect is all that we should be receiving
                # if we get something else, things went wrong somewhere
                raise RuntimeError(f"Unexpected message received: {msg['type']}")
            return msg

        # wrapped_rcv state 3: not yet consumed
        if getattr(self, "_body", None) is not None:
            # body() was called, we return it even if the client disconnected
            self._wrapped_rcv_consumed = True
            return {
                "type": "http.request",
                "body": self._body,
                "more_body": False,
            }
        elif self._stream_consumed:
            # stream() was called to completion
            # return an empty body so that downstream apps don't hang
            # waiting for a disconnect
            self._wrapped_rcv_consumed = True
            return {
                "type": "http.request",
                "body": b"",
                "more_body": False,
            }
        else:
            # body() was never called and stream() wasn't consumed
            try:
                stream = self.stream()
                chunk = await stream.__anext__()
                self._wrapped_rcv_consumed = self._stream_consumed
                return {
                    "type": "http.request",
                    "body": chunk,
                    "more_body": not self._stream_consumed,
                }
            except ClientDisconnect:
                self._wrapped_rcv_disconnected = True
                return {"type": "http.disconnect"}


class BaseHTTPMiddleware:
    def __init__(self, app: ASGIApp, dispatch: DispatchFunction | None = None) -> None:
        self.app = app
        self.dispatch_func = self.dispatch if dispatch is None else dispatch

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request = _CachedRequest(scope, receive)
        wrapped_receive = request.wrapped_receive
        response_sent = anyio.Event()

        async def call_next(request: Request) -> Response:
            app_exc: Exception | None = None
            send_stream: ObjectSendStream[typing.MutableMapping[str, typing.Any]]
            recv_stream: ObjectReceiveStream[typing.MutableMapping[str, typing.Any]]
            send_stream, recv_stream = anyio.create_memory_object_stream()

            async def receive_or_disconnect() -> Message:
                if response_sent.is_set():
                    return {"type": "http.disconnect"}

                async with anyio.create_task_group() as task_group:

                    async def wrap(func: typing.Callable[[], typing.Awaitable[T]]) -> T:
                        result = await func()
                        task_group.cancel_scope.cancel()
                        return result

                    task_group.start_soon(wrap, response_sent.wait)
                    message = await wrap(wrapped_receive)

                if response_sent.is_set():
                    return {"type": "http.disconnect"}

                return message

            async def close_recv_stream_on_response_sent() -> None:
                await response_sent.wait()
                recv_stream.close()

            async def send_no_error(message: Message) -> None:
                try:
                    await send_stream.send(message)
                except anyio.BrokenResourceError:
                    # recv_stream has been closed, i.e. response_sent has been set.
                    return

            async def coro() -> None:
                nonlocal app_exc

                async with send_stream:
                    try:
                        await self.app(scope, receive_or_disconnect, send_no_error)
                    except Exception as exc:
                        app_exc = exc

            task_group.start_soon(close_recv_stream_on_response_sent)
            task_group.start_soon(coro)

            try:
                message = await recv_stream.receive()
                info = message.get("info", None)
                if message["type"] == "http.response.debug" and info is not None:
                    message = await recv_stream.receive()
            except anyio.EndOfStream:
                if app_exc is not None:
                    raise app_exc
                raise RuntimeError("No response returned.")

            assert message["type"] == "http.response.start"

            async def body_stream() -> typing.AsyncGenerator[bytes, None]:
                async with recv_stream:
                    async for message in recv_stream:
                        assert message["type"] == "http.response.body"
                        body = message.get("body", b"")
                        if body:
                            yield body
                        if not message.get("more_body", False):
                            break

                if app_exc is not None:
                    raise app_exc

            response = _StreamingResponse(
                status_code=message["status"], content=body_stream(), info=info
            )
            response.raw_headers = message["headers"]
            return response

        with collapse_excgroups():
            async with anyio.create_task_group() as task_group:
                response = await self.dispatch_func(request, call_next)
                await response(scope, wrapped_receive, send)
                response_sent.set()

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        raise NotImplementedError()  # pragma: no cover


class _StreamingResponse(StreamingResponse):
    def __init__(
        self,
        content: ContentStream,
        status_code: int = 200,
        headers: typing.Mapping[str, str] | None = None,
        media_type: str | None = None,
        background: BackgroundTask | None = None,
        info: typing.Mapping[str, typing.Any] | None = None,
    ) -> None:
        self._info = info
        super().__init__(content, status_code, headers, media_type, background)

    async def stream_response(self, send: Send) -> None:
        if self._info:
            await send({"type": "http.response.debug", "info": self._info})
        return await super().stream_response(send)

# === NexusCore/openenv\Lib\site-packages\tornado\test\circlerefs_test.py ===
"""Test script to find circular references.

Circular references are not leaks per se, because they will eventually
be GC'd. However, on CPython, they prevent the reference-counting fast
path from being used and instead rely on the slower full GC. This
increases memory footprint and CPU overhead, so we try to eliminate
circular references created by normal operation.
"""

import asyncio
import contextlib
import gc
import io
import sys
import traceback
import types
import typing
import unittest

import tornado
from tornado import web, gen, httpclient
from tornado.test.util import skipNotCPython


def find_circular_references(garbage):
    """Find circular references in a list of objects.

    The garbage list contains objects that participate in a cycle,
    but also the larger set of objects kept alive by that cycle.
    This function finds subsets of those objects that make up
    the cycle(s).
    """

    def inner(level):
        for item in level:
            item_id = id(item)
            if item_id not in garbage_ids:
                continue
            if item_id in visited_ids:
                continue
            if item_id in stack_ids:
                candidate = stack[stack.index(item) :]
                candidate.append(item)
                found.append(candidate)
                continue

            stack.append(item)
            stack_ids.add(item_id)
            inner(gc.get_referents(item))
            stack.pop()
            stack_ids.remove(item_id)
            visited_ids.add(item_id)

    found: typing.List[object] = []
    stack = []
    stack_ids = set()
    garbage_ids = set(map(id, garbage))
    visited_ids = set()

    inner(garbage)
    return found


@contextlib.contextmanager
def assert_no_cycle_garbage():
    """Raise AssertionError if the wrapped code creates garbage with cycles."""
    gc.disable()
    gc.collect()
    gc.set_debug(gc.DEBUG_STATS | gc.DEBUG_SAVEALL)
    yield
    try:
        # We have DEBUG_STATS on which causes gc.collect to write to stderr.
        # Capture the output instead of spamming the logs on passing runs.
        f = io.StringIO()
        old_stderr = sys.stderr
        sys.stderr = f
        try:
            gc.collect()
        finally:
            sys.stderr = old_stderr
        garbage = gc.garbage[:]
        # Must clear gc.garbage (the same object, not just replacing it with a
        # new list) to avoid warnings at shutdown.
        gc.garbage[:] = []
        if len(garbage) == 0:
            return
        for circular in find_circular_references(garbage):
            f.write("\n==========\n Circular \n==========")
            for item in circular:
                f.write(f"\n    {repr(item)}")
            for item in circular:
                if isinstance(item, types.FrameType):
                    f.write(f"\nLocals: {item.f_locals}")
                    f.write(f"\nTraceback: {repr(item)}")
                    traceback.print_stack(item)
        del garbage
        raise AssertionError(f.getvalue())
    finally:
        gc.set_debug(0)
        gc.enable()


# GC behavior is cpython-specific
@skipNotCPython
class CircleRefsTest(unittest.TestCase):
    def test_known_leak(self):
        # Construct a known leak scenario to make sure the test harness works.
        class C:
            def __init__(self, name):
                self.name = name
                self.a: typing.Optional[C] = None
                self.b: typing.Optional[C] = None
                self.c: typing.Optional[C] = None

            def __repr__(self):
                return f"name={self.name}"

        with self.assertRaises(AssertionError) as cm:
            with assert_no_cycle_garbage():
                # a and b form a reference cycle. c is not part of the cycle,
                # but it cannot be GC'd while a and b are alive.
                a = C("a")
                b = C("b")
                c = C("c")
                a.b = b
                a.c = c
                b.a = a
                b.c = c
                del a, b
        self.assertIn("Circular", str(cm.exception))
        # Leading spaces ensure we only catch these at the beginning of a line, meaning they are a
        # cycle participant and not simply the contents of a locals dict or similar container. (This
        # depends on the formatting above which isn't ideal but this test evolved from a
        # command-line script) Note that the behavior here changed in python 3.11; in newer pythons
        # locals are handled a bit differently and the test passes without the spaces.
        self.assertIn("    name=a", str(cm.exception))
        self.assertIn("    name=b", str(cm.exception))
        self.assertNotIn("    name=c", str(cm.exception))

    async def run_handler(self, handler_class):
        app = web.Application(
            [
                (r"/", handler_class),
            ]
        )
        socket, port = tornado.testing.bind_unused_port()
        server = tornado.httpserver.HTTPServer(app)
        server.add_socket(socket)

        client = httpclient.AsyncHTTPClient()
        with assert_no_cycle_garbage():
            # Only the fetch (and the corresponding server-side handler)
            # are being tested for cycles. In particular, the Application
            # object has internal cycles (as of this writing) which we don't
            # care to fix since in real world usage the Application object
            # is effectively a global singleton.
            await client.fetch(f"http://127.0.0.1:{port}/")
        client.close()
        server.stop()
        socket.close()

    def test_sync_handler(self):
        class Handler(web.RequestHandler):
            def get(self):
                self.write("ok\n")

        asyncio.run(self.run_handler(Handler))

    def test_finish_exception_handler(self):
        class Handler(web.RequestHandler):
            def get(self):
                raise web.Finish("ok\n")

        asyncio.run(self.run_handler(Handler))

    def test_coro_handler(self):
        class Handler(web.RequestHandler):
            @gen.coroutine
            def get(self):
                yield asyncio.sleep(0.01)
                self.write("ok\n")

        asyncio.run(self.run_handler(Handler))

    def test_async_handler(self):
        class Handler(web.RequestHandler):
            async def get(self):
                await asyncio.sleep(0.01)
                self.write("ok\n")

        asyncio.run(self.run_handler(Handler))

    def test_run_on_executor(self):
        # From https://github.com/tornadoweb/tornado/issues/2620
        #
        # When this test was introduced it found cycles in IOLoop.add_future
        # and tornado.concurrent.chain_future.
        import concurrent.futures

        with concurrent.futures.ThreadPoolExecutor(1) as thread_pool:

            class Factory:
                executor = thread_pool

                @tornado.concurrent.run_on_executor
                def run(self):
                    return None

            factory = Factory()

            async def main():
                # The cycle is not reported on the first call. It's not clear why.
                for i in range(2):
                    await factory.run()

            with assert_no_cycle_garbage():
                asyncio.run(main())

# === NexusCore/myenv\Lib\site-packages\pip\_vendor\urllib3\contrib\socks.py ===
# -*- coding: utf-8 -*-
"""
This module contains provisional support for SOCKS proxies from within
urllib3. This module supports SOCKS4, SOCKS4A (an extension of SOCKS4), and
SOCKS5. To enable its functionality, either install PySocks or install this
module with the ``socks`` extra.

The SOCKS implementation supports the full range of urllib3 features. It also
supports the following SOCKS features:

- SOCKS4A (``proxy_url='socks4a://...``)
- SOCKS4 (``proxy_url='socks4://...``)
- SOCKS5 with remote DNS (``proxy_url='socks5h://...``)
- SOCKS5 with local DNS (``proxy_url='socks5://...``)
- Usernames and passwords for the SOCKS proxy

.. note::
   It is recommended to use ``socks5h://`` or ``socks4a://`` schemes in
   your ``proxy_url`` to ensure that DNS resolution is done from the remote
   server instead of client-side when connecting to a domain name.

SOCKS4 supports IPv4 and domain names with the SOCKS4A extension. SOCKS5
supports IPv4, IPv6, and domain names.

When connecting to a SOCKS4 proxy the ``username`` portion of the ``proxy_url``
will be sent as the ``userid`` section of the SOCKS request:

.. code-block:: python

    proxy_url="socks4a://<userid>@proxy-host"

When connecting to a SOCKS5 proxy the ``username`` and ``password`` portion
of the ``proxy_url`` will be sent as the username/password to authenticate
with the proxy:

.. code-block:: python

    proxy_url="socks5h://<username>:<password>@proxy-host"

"""
from __future__ import absolute_import

try:
    import socks
except ImportError:
    import warnings

    from ..exceptions import DependencyWarning

    warnings.warn(
        (
            "SOCKS support in urllib3 requires the installation of optional "
            "dependencies: specifically, PySocks.  For more information, see "
            "https://urllib3.readthedocs.io/en/1.26.x/contrib.html#socks-proxies"
        ),
        DependencyWarning,
    )
    raise

from socket import error as SocketError
from socket import timeout as SocketTimeout

from ..connection import HTTPConnection, HTTPSConnection
from ..connectionpool import HTTPConnectionPool, HTTPSConnectionPool
from ..exceptions import ConnectTimeoutError, NewConnectionError
from ..poolmanager import PoolManager
from ..util.url import parse_url

try:
    import ssl
except ImportError:
    ssl = None


class SOCKSConnection(HTTPConnection):
    """
    A plain-text HTTP connection that connects via a SOCKS proxy.
    """

    def __init__(self, *args, **kwargs):
        self._socks_options = kwargs.pop("_socks_options")
        super(SOCKSConnection, self).__init__(*args, **kwargs)

    def _new_conn(self):
        """
        Establish a new connection via the SOCKS proxy.
        """
        extra_kw = {}
        if self.source_address:
            extra_kw["source_address"] = self.source_address

        if self.socket_options:
            extra_kw["socket_options"] = self.socket_options

        try:
            conn = socks.create_connection(
                (self.host, self.port),
                proxy_type=self._socks_options["socks_version"],
                proxy_addr=self._socks_options["proxy_host"],
                proxy_port=self._socks_options["proxy_port"],
                proxy_username=self._socks_options["username"],
                proxy_password=self._socks_options["password"],
                proxy_rdns=self._socks_options["rdns"],
                timeout=self.timeout,
                **extra_kw
            )

        except SocketTimeout:
            raise ConnectTimeoutError(
                self,
                "Connection to %s timed out. (connect timeout=%s)"
                % (self.host, self.timeout),
            )

        except socks.ProxyError as e:
            # This is fragile as hell, but it seems to be the only way to raise
            # useful errors here.
            if e.socket_err:
                error = e.socket_err
                if isinstance(error, SocketTimeout):
                    raise ConnectTimeoutError(
                        self,
                        "Connection to %s timed out. (connect timeout=%s)"
                        % (self.host, self.timeout),
                    )
                else:
                    raise NewConnectionError(
                        self, "Failed to establish a new connection: %s" % error
                    )
            else:
                raise NewConnectionError(
                    self, "Failed to establish a new connection: %s" % e
                )

        except SocketError as e:  # Defensive: PySocks should catch all these.
            raise NewConnectionError(
                self, "Failed to establish a new connection: %s" % e
            )

        return conn


# We don't need to duplicate the Verified/Unverified distinction from
# urllib3/connection.py here because the HTTPSConnection will already have been
# correctly set to either the Verified or Unverified form by that module. This
# means the SOCKSHTTPSConnection will automatically be the correct type.
class SOCKSHTTPSConnection(SOCKSConnection, HTTPSConnection):
    pass


class SOCKSHTTPConnectionPool(HTTPConnectionPool):
    ConnectionCls = SOCKSConnection


class SOCKSHTTPSConnectionPool(HTTPSConnectionPool):
    ConnectionCls = SOCKSHTTPSConnection


class SOCKSProxyManager(PoolManager):
    """
    A version of the urllib3 ProxyManager that routes connections via the
    defined SOCKS proxy.
    """

    pool_classes_by_scheme = {
        "http": SOCKSHTTPConnectionPool,
        "https": SOCKSHTTPSConnectionPool,
    }

    def __init__(
        self,
        proxy_url,
        username=None,
        password=None,
        num_pools=10,
        headers=None,
        **connection_pool_kw
    ):
        parsed = parse_url(proxy_url)

        if username is None and password is None and parsed.auth is not None:
            split = parsed.auth.split(":")
            if len(split) == 2:
                username, password = split
        if parsed.scheme == "socks5":
            socks_version = socks.PROXY_TYPE_SOCKS5
            rdns = False
        elif parsed.scheme == "socks5h":
            socks_version = socks.PROXY_TYPE_SOCKS5
            rdns = True
        elif parsed.scheme == "socks4":
            socks_version = socks.PROXY_TYPE_SOCKS4
            rdns = False
        elif parsed.scheme == "socks4a":
            socks_version = socks.PROXY_TYPE_SOCKS4
            rdns = True
        else:
            raise ValueError("Unable to determine SOCKS version from %s" % proxy_url)

        self.proxy_url = proxy_url

        socks_options = {
            "socks_version": socks_version,
            "proxy_host": parsed.host,
            "proxy_port": parsed.port,
            "username": username,
            "password": password,
            "rdns": rdns,
        }
        connection_pool_kw["_socks_options"] = socks_options

        super(SOCKSProxyManager, self).__init__(
            num_pools, headers, **connection_pool_kw
        )

        self.pool_classes_by_scheme = SOCKSProxyManager.pool_classes_by_scheme

# === NexusCore/openenv\Lib\site-packages\aiohttp\web_log.py ===
import datetime
import functools
import logging
import os
import re
import time as time_mod
from collections import namedtuple
from typing import Any, Callable, Dict, Iterable, List, Tuple  # noqa

from .abc import AbstractAccessLogger
from .web_request import BaseRequest
from .web_response import StreamResponse

KeyMethod = namedtuple("KeyMethod", "key method")


class AccessLogger(AbstractAccessLogger):
    """Helper object to log access.

    Usage:
        log = logging.getLogger("spam")
        log_format = "%a %{User-Agent}i"
        access_logger = AccessLogger(log, log_format)
        access_logger.log(request, response, time)

    Format:
        %%  The percent sign
        %a  Remote IP-address (IP-address of proxy if using reverse proxy)
        %t  Time when the request was started to process
        %P  The process ID of the child that serviced the request
        %r  First line of request
        %s  Response status code
        %b  Size of response in bytes, including HTTP headers
        %T  Time taken to serve the request, in seconds
        %Tf Time taken to serve the request, in seconds with floating fraction
            in .06f format
        %D  Time taken to serve the request, in microseconds
        %{FOO}i  request.headers['FOO']
        %{FOO}o  response.headers['FOO']
        %{FOO}e  os.environ['FOO']

    """

    LOG_FORMAT_MAP = {
        "a": "remote_address",
        "t": "request_start_time",
        "P": "process_id",
        "r": "first_request_line",
        "s": "response_status",
        "b": "response_size",
        "T": "request_time",
        "Tf": "request_time_frac",
        "D": "request_time_micro",
        "i": "request_header",
        "o": "response_header",
    }

    LOG_FORMAT = '%a %t "%r" %s %b "%{Referer}i" "%{User-Agent}i"'
    FORMAT_RE = re.compile(r"%(\{([A-Za-z0-9\-_]+)\}([ioe])|[atPrsbOD]|Tf?)")
    CLEANUP_RE = re.compile(r"(%[^s])")
    _FORMAT_CACHE: Dict[str, Tuple[str, List[KeyMethod]]] = {}

    def __init__(self, logger: logging.Logger, log_format: str = LOG_FORMAT) -> None:
        """Initialise the logger.

        logger is a logger object to be used for logging.
        log_format is a string with apache compatible log format description.

        """
        super().__init__(logger, log_format=log_format)

        _compiled_format = AccessLogger._FORMAT_CACHE.get(log_format)
        if not _compiled_format:
            _compiled_format = self.compile_format(log_format)
            AccessLogger._FORMAT_CACHE[log_format] = _compiled_format

        self._log_format, self._methods = _compiled_format

    def compile_format(self, log_format: str) -> Tuple[str, List[KeyMethod]]:
        """Translate log_format into form usable by modulo formatting

        All known atoms will be replaced with %s
        Also methods for formatting of those atoms will be added to
        _methods in appropriate order

        For example we have log_format = "%a %t"
        This format will be translated to "%s %s"
        Also contents of _methods will be
        [self._format_a, self._format_t]
        These method will be called and results will be passed
        to translated string format.

        Each _format_* method receive 'args' which is list of arguments
        given to self.log

        Exceptions are _format_e, _format_i and _format_o methods which
        also receive key name (by functools.partial)

        """
        # list of (key, method) tuples, we don't use an OrderedDict as users
        # can repeat the same key more than once
        methods = list()

        for atom in self.FORMAT_RE.findall(log_format):
            if atom[1] == "":
                format_key1 = self.LOG_FORMAT_MAP[atom[0]]
                m = getattr(AccessLogger, "_format_%s" % atom[0])
                key_method = KeyMethod(format_key1, m)
            else:
                format_key2 = (self.LOG_FORMAT_MAP[atom[2]], atom[1])
                m = getattr(AccessLogger, "_format_%s" % atom[2])
                key_method = KeyMethod(format_key2, functools.partial(m, atom[1]))

            methods.append(key_method)

        log_format = self.FORMAT_RE.sub(r"%s", log_format)
        log_format = self.CLEANUP_RE.sub(r"%\1", log_format)
        return log_format, methods

    @staticmethod
    def _format_i(
        key: str, request: BaseRequest, response: StreamResponse, time: float
    ) -> str:
        if request is None:
            return "(no headers)"

        # suboptimal, make istr(key) once
        return request.headers.get(key, "-")

    @staticmethod
    def _format_o(
        key: str, request: BaseRequest, response: StreamResponse, time: float
    ) -> str:
        # suboptimal, make istr(key) once
        return response.headers.get(key, "-")

    @staticmethod
    def _format_a(request: BaseRequest, response: StreamResponse, time: float) -> str:
        if request is None:
            return "-"
        ip = request.remote
        return ip if ip is not None else "-"

    @staticmethod
    def _format_t(request: BaseRequest, response: StreamResponse, time: float) -> str:
        tz = datetime.timezone(datetime.timedelta(seconds=-time_mod.timezone))
        now = datetime.datetime.now(tz)
        start_time = now - datetime.timedelta(seconds=time)
        return start_time.strftime("[%d/%b/%Y:%H:%M:%S %z]")

    @staticmethod
    def _format_P(request: BaseRequest, response: StreamResponse, time: float) -> str:
        return "<%s>" % os.getpid()

    @staticmethod
    def _format_r(request: BaseRequest, response: StreamResponse, time: float) -> str:
        if request is None:
            return "-"
        return "{} {} HTTP/{}.{}".format(
            request.method,
            request.path_qs,
            request.version.major,
            request.version.minor,
        )

    @staticmethod
    def _format_s(request: BaseRequest, response: StreamResponse, time: float) -> int:
        return response.status

    @staticmethod
    def _format_b(request: BaseRequest, response: StreamResponse, time: float) -> int:
        return response.body_length

    @staticmethod
    def _format_T(request: BaseRequest, response: StreamResponse, time: float) -> str:
        return str(round(time))

    @staticmethod
    def _format_Tf(request: BaseRequest, response: StreamResponse, time: float) -> str:
        return "%06f" % time

    @staticmethod
    def _format_D(request: BaseRequest, response: StreamResponse, time: float) -> str:
        return str(round(time * 1000000))

    def _format_line(
        self, request: BaseRequest, response: StreamResponse, time: float
    ) -> Iterable[Tuple[str, Callable[[BaseRequest, StreamResponse, float], str]]]:
        return [(key, method(request, response, time)) for key, method in self._methods]

    @property
    def enabled(self) -> bool:
        """Check if logger is enabled."""
        # Avoid formatting the log line if it will not be emitted.
        return self.logger.isEnabledFor(logging.INFO)

    def log(self, request: BaseRequest, response: StreamResponse, time: float) -> None:
        try:
            fmt_info = self._format_line(request, response, time)

            values = list()
            extra = dict()
            for key, value in fmt_info:
                values.append(value)

                if key.__class__ is str:
                    extra[key] = value
                else:
                    k1, k2 = key  # type: ignore[misc]
                    dct = extra.get(k1, {})  # type: ignore[var-annotated,has-type]
                    dct[k2] = value  # type: ignore[index,has-type]
                    extra[k1] = dct  # type: ignore[has-type,assignment]

            self.logger.info(self._log_format % tuple(values), extra=extra)
        except Exception:
            self.logger.exception("Error in logging")