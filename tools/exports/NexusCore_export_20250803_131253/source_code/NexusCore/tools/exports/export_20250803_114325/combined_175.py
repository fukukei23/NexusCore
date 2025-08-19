
# === NexusCore/openenv\Lib\site-packages\aiohttp\_websocket\reader_c.py ===
"""Reader for WebSocket protocol versions 13 and 8."""

import asyncio
import builtins
from collections import deque
from typing import Deque, Final, Optional, Set, Tuple, Union

from ..base_protocol import BaseProtocol
from ..compression_utils import ZLibDecompressor
from ..helpers import _EXC_SENTINEL, set_exception
from ..streams import EofStream
from .helpers import UNPACK_CLOSE_CODE, UNPACK_LEN3, websocket_mask
from .models import (
    WS_DEFLATE_TRAILING,
    WebSocketError,
    WSCloseCode,
    WSMessage,
    WSMsgType,
)

ALLOWED_CLOSE_CODES: Final[Set[int]] = {int(i) for i in WSCloseCode}

# States for the reader, used to parse the WebSocket frame
# integer values are used so they can be cythonized
READ_HEADER = 1
READ_PAYLOAD_LENGTH = 2
READ_PAYLOAD_MASK = 3
READ_PAYLOAD = 4

WS_MSG_TYPE_BINARY = WSMsgType.BINARY
WS_MSG_TYPE_TEXT = WSMsgType.TEXT

# WSMsgType values unpacked so they can by cythonized to ints
OP_CODE_NOT_SET = -1
OP_CODE_CONTINUATION = WSMsgType.CONTINUATION.value
OP_CODE_TEXT = WSMsgType.TEXT.value
OP_CODE_BINARY = WSMsgType.BINARY.value
OP_CODE_CLOSE = WSMsgType.CLOSE.value
OP_CODE_PING = WSMsgType.PING.value
OP_CODE_PONG = WSMsgType.PONG.value

EMPTY_FRAME_ERROR = (True, b"")
EMPTY_FRAME = (False, b"")

COMPRESSED_NOT_SET = -1
COMPRESSED_FALSE = 0
COMPRESSED_TRUE = 1

TUPLE_NEW = tuple.__new__

cython_int = int  # Typed to int in Python, but cython with use a signed int in the pxd


class WebSocketDataQueue:
    """WebSocketDataQueue resumes and pauses an underlying stream.

    It is a destination for WebSocket data.
    """

    def __init__(
        self, protocol: BaseProtocol, limit: int, *, loop: asyncio.AbstractEventLoop
    ) -> None:
        self._size = 0
        self._protocol = protocol
        self._limit = limit * 2
        self._loop = loop
        self._eof = False
        self._waiter: Optional[asyncio.Future[None]] = None
        self._exception: Union[BaseException, None] = None
        self._buffer: Deque[Tuple[WSMessage, int]] = deque()
        self._get_buffer = self._buffer.popleft
        self._put_buffer = self._buffer.append

    def is_eof(self) -> bool:
        return self._eof

    def exception(self) -> Optional[BaseException]:
        return self._exception

    def set_exception(
        self,
        exc: BaseException,
        exc_cause: builtins.BaseException = _EXC_SENTINEL,
    ) -> None:
        self._eof = True
        self._exception = exc
        if (waiter := self._waiter) is not None:
            self._waiter = None
            set_exception(waiter, exc, exc_cause)

    def _release_waiter(self) -> None:
        if (waiter := self._waiter) is None:
            return
        self._waiter = None
        if not waiter.done():
            waiter.set_result(None)

    def feed_eof(self) -> None:
        self._eof = True
        self._release_waiter()
        self._exception = None  # Break cyclic references

    def feed_data(self, data: "WSMessage", size: "cython_int") -> None:
        self._size += size
        self._put_buffer((data, size))
        self._release_waiter()
        if self._size > self._limit and not self._protocol._reading_paused:
            self._protocol.pause_reading()

    async def read(self) -> WSMessage:
        if not self._buffer and not self._eof:
            assert not self._waiter
            self._waiter = self._loop.create_future()
            try:
                await self._waiter
            except (asyncio.CancelledError, asyncio.TimeoutError):
                self._waiter = None
                raise
        return self._read_from_buffer()

    def _read_from_buffer(self) -> WSMessage:
        if self._buffer:
            data, size = self._get_buffer()
            self._size -= size
            if self._size < self._limit and self._protocol._reading_paused:
                self._protocol.resume_reading()
            return data
        if self._exception is not None:
            raise self._exception
        raise EofStream


class WebSocketReader:
    def __init__(
        self, queue: WebSocketDataQueue, max_msg_size: int, compress: bool = True
    ) -> None:
        self.queue = queue
        self._max_msg_size = max_msg_size

        self._exc: Optional[Exception] = None
        self._partial = bytearray()
        self._state = READ_HEADER

        self._opcode: int = OP_CODE_NOT_SET
        self._frame_fin = False
        self._frame_opcode: int = OP_CODE_NOT_SET
        self._payload_fragments: list[bytes] = []
        self._frame_payload_len = 0

        self._tail: bytes = b""
        self._has_mask = False
        self._frame_mask: Optional[bytes] = None
        self._payload_bytes_to_read = 0
        self._payload_len_flag = 0
        self._compressed: int = COMPRESSED_NOT_SET
        self._decompressobj: Optional[ZLibDecompressor] = None
        self._compress = compress

    def feed_eof(self) -> None:
        self.queue.feed_eof()

    # data can be bytearray on Windows because proactor event loop uses bytearray
    # and asyncio types this to Union[bytes, bytearray, memoryview] so we need
    # coerce data to bytes if it is not
    def feed_data(
        self, data: Union[bytes, bytearray, memoryview]
    ) -> Tuple[bool, bytes]:
        if type(data) is not bytes:
            data = bytes(data)

        if self._exc is not None:
            return True, data

        try:
            self._feed_data(data)
        except Exception as exc:
            self._exc = exc
            set_exception(self.queue, exc)
            return EMPTY_FRAME_ERROR

        return EMPTY_FRAME

    def _handle_frame(
        self,
        fin: bool,
        opcode: Union[int, cython_int],  # Union intended: Cython pxd uses C int
        payload: Union[bytes, bytearray],
        compressed: Union[int, cython_int],  # Union intended: Cython pxd uses C int
    ) -> None:
        msg: WSMessage
        if opcode in {OP_CODE_TEXT, OP_CODE_BINARY, OP_CODE_CONTINUATION}:
            # load text/binary
            if not fin:
                # got partial frame payload
                if opcode != OP_CODE_CONTINUATION:
                    self._opcode = opcode
                self._partial += payload
                if self._max_msg_size and len(self._partial) >= self._max_msg_size:
                    raise WebSocketError(
                        WSCloseCode.MESSAGE_TOO_BIG,
                        f"Message size {len(self._partial)} "
                        f"exceeds limit {self._max_msg_size}",
                    )
                return

            has_partial = bool(self._partial)
            if opcode == OP_CODE_CONTINUATION:
                if self._opcode == OP_CODE_NOT_SET:
                    raise WebSocketError(
                        WSCloseCode.PROTOCOL_ERROR,
                        "Continuation frame for non started message",
                    )
                opcode = self._opcode
                self._opcode = OP_CODE_NOT_SET
            # previous frame was non finished
            # we should get continuation opcode
            elif has_partial:
                raise WebSocketError(
                    WSCloseCode.PROTOCOL_ERROR,
                    "The opcode in non-fin frame is expected "
                    f"to be zero, got {opcode!r}",
                )

            assembled_payload: Union[bytes, bytearray]
            if has_partial:
                assembled_payload = self._partial + payload
                self._partial.clear()
            else:
                assembled_payload = payload

            if self._max_msg_size and len(assembled_payload) >= self._max_msg_size:
                raise WebSocketError(
                    WSCloseCode.MESSAGE_TOO_BIG,
                    f"Message size {len(assembled_payload)} "
                    f"exceeds limit {self._max_msg_size}",
                )

            # Decompress process must to be done after all packets
            # received.
            if compressed:
                if not self._decompressobj:
                    self._decompressobj = ZLibDecompressor(suppress_deflate_header=True)
                # XXX: It's possible that the zlib backend (isal is known to
                # do this, maybe others too?) will return max_length bytes,
                # but internally buffer more data such that the payload is
                # >max_length, so we return one extra byte and if we're able
                # to do that, then the message is too big.
                payload_merged = self._decompressobj.decompress_sync(
                    assembled_payload + WS_DEFLATE_TRAILING,
                    (
                        self._max_msg_size + 1
                        if self._max_msg_size
                        else self._max_msg_size
                    ),
                )
                if self._max_msg_size and len(payload_merged) > self._max_msg_size:
                    raise WebSocketError(
                        WSCloseCode.MESSAGE_TOO_BIG,
                        f"Decompressed message exceeds size limit {self._max_msg_size}",
                    )
            elif type(assembled_payload) is bytes:
                payload_merged = assembled_payload
            else:
                payload_merged = bytes(assembled_payload)

            if opcode == OP_CODE_TEXT:
                try:
                    text = payload_merged.decode("utf-8")
                except UnicodeDecodeError as exc:
                    raise WebSocketError(
                        WSCloseCode.INVALID_TEXT, "Invalid UTF-8 text message"
                    ) from exc

                # XXX: The Text and Binary messages here can be a performance
                # bottleneck, so we use tuple.__new__ to improve performance.
                # This is not type safe, but many tests should fail in
                # test_client_ws_functional.py if this is wrong.
                self.queue.feed_data(
                    TUPLE_NEW(WSMessage, (WS_MSG_TYPE_TEXT, text, "")),
                    len(payload_merged),
                )
            else:
                self.queue.feed_data(
                    TUPLE_NEW(WSMessage, (WS_MSG_TYPE_BINARY, payload_merged, "")),
                    len(payload_merged),
                )
        elif opcode == OP_CODE_CLOSE:
            if len(payload) >= 2:
                close_code = UNPACK_CLOSE_CODE(payload[:2])[0]
                if close_code < 3000 and close_code not in ALLOWED_CLOSE_CODES:
                    raise WebSocketError(
                        WSCloseCode.PROTOCOL_ERROR,
                        f"Invalid close code: {close_code}",
                    )
                try:
                    close_message = payload[2:].decode("utf-8")
                except UnicodeDecodeError as exc:
                    raise WebSocketError(
                        WSCloseCode.INVALID_TEXT, "Invalid UTF-8 text message"
                    ) from exc
                msg = TUPLE_NEW(WSMessage, (WSMsgType.CLOSE, close_code, close_message))
            elif payload:
                raise WebSocketError(
                    WSCloseCode.PROTOCOL_ERROR,
                    f"Invalid close frame: {fin} {opcode} {payload!r}",
                )
            else:
                msg = TUPLE_NEW(WSMessage, (WSMsgType.CLOSE, 0, ""))

            self.queue.feed_data(msg, 0)
        elif opcode == OP_CODE_PING:
            msg = TUPLE_NEW(WSMessage, (WSMsgType.PING, payload, ""))
            self.queue.feed_data(msg, len(payload))
        elif opcode == OP_CODE_PONG:
            msg = TUPLE_NEW(WSMessage, (WSMsgType.PONG, payload, ""))
            self.queue.feed_data(msg, len(payload))
        else:
            raise WebSocketError(
                WSCloseCode.PROTOCOL_ERROR, f"Unexpected opcode={opcode!r}"
            )

    def _feed_data(self, data: bytes) -> None:
        """Return the next frame from the socket."""
        if self._tail:
            data, self._tail = self._tail + data, b""

        start_pos: int = 0
        data_len = len(data)
        data_cstr = data

        while True:
            # read header
            if self._state == READ_HEADER:
                if data_len - start_pos < 2:
                    break
                first_byte = data_cstr[start_pos]
                second_byte = data_cstr[start_pos + 1]
                start_pos += 2

                fin = (first_byte >> 7) & 1
                rsv1 = (first_byte >> 6) & 1
                rsv2 = (first_byte >> 5) & 1
                rsv3 = (first_byte >> 4) & 1
                opcode = first_byte & 0xF

                # frame-fin = %x0 ; more frames of this message follow
                #           / %x1 ; final frame of this message
                # frame-rsv1 = %x0 ;
                #    1 bit, MUST be 0 unless negotiated otherwise
                # frame-rsv2 = %x0 ;
                #    1 bit, MUST be 0 unless negotiated otherwise
                # frame-rsv3 = %x0 ;
                #    1 bit, MUST be 0 unless negotiated otherwise
                #
                # Remove rsv1 from this test for deflate development
                if rsv2 or rsv3 or (rsv1 and not self._compress):
                    raise WebSocketError(
                        WSCloseCode.PROTOCOL_ERROR,
                        "Received frame with non-zero reserved bits",
                    )

                if opcode > 0x7 and fin == 0:
                    raise WebSocketError(
                        WSCloseCode.PROTOCOL_ERROR,
                        "Received fragmented control frame",
                    )

                has_mask = (second_byte >> 7) & 1
                length = second_byte & 0x7F

                # Control frames MUST have a payload
                # length of 125 bytes or less
                if opcode > 0x7 and length > 125:
                    raise WebSocketError(
                        WSCloseCode.PROTOCOL_ERROR,
                        "Control frame payload cannot be larger than 125 bytes",
                    )

                # Set compress status if last package is FIN
                # OR set compress status if this is first fragment
                # Raise error if not first fragment with rsv1 = 0x1
                if self._frame_fin or self._compressed == COMPRESSED_NOT_SET:
                    self._compressed = COMPRESSED_TRUE if rsv1 else COMPRESSED_FALSE
                elif rsv1:
                    raise WebSocketError(
                        WSCloseCode.PROTOCOL_ERROR,
                        "Received frame with non-zero reserved bits",
                    )

                self._frame_fin = bool(fin)
                self._frame_opcode = opcode
                self._has_mask = bool(has_mask)
                self._payload_len_flag = length
                self._state = READ_PAYLOAD_LENGTH

            # read payload length
            if self._state == READ_PAYLOAD_LENGTH:
                len_flag = self._payload_len_flag
                if len_flag == 126:
                    if data_len - start_pos < 2:
                        break
                    first_byte = data_cstr[start_pos]
                    second_byte = data_cstr[start_pos + 1]
                    start_pos += 2
                    self._payload_bytes_to_read = first_byte << 8 | second_byte
                elif len_flag > 126:
                    if data_len - start_pos < 8:
                        break
                    self._payload_bytes_to_read = UNPACK_LEN3(data, start_pos)[0]
                    start_pos += 8
                else:
                    self._payload_bytes_to_read = len_flag

                self._state = READ_PAYLOAD_MASK if self._has_mask else READ_PAYLOAD

            # read payload mask
            if self._state == READ_PAYLOAD_MASK:
                if data_len - start_pos < 4:
                    break
                self._frame_mask = data_cstr[start_pos : start_pos + 4]
                start_pos += 4
                self._state = READ_PAYLOAD

            if self._state == READ_PAYLOAD:
                chunk_len = data_len - start_pos
                if self._payload_bytes_to_read >= chunk_len:
                    f_end_pos = data_len
                    self._payload_bytes_to_read -= chunk_len
                else:
                    f_end_pos = start_pos + self._payload_bytes_to_read
                    self._payload_bytes_to_read = 0

                had_fragments = self._frame_payload_len
                self._frame_payload_len += f_end_pos - start_pos
                f_start_pos = start_pos
                start_pos = f_end_pos

                if self._payload_bytes_to_read != 0:
                    # If we don't have a complete frame, we need to save the
                    # data for the next call to feed_data.
                    self._payload_fragments.append(data_cstr[f_start_pos:f_end_pos])
                    break

                payload: Union[bytes, bytearray]
                if had_fragments:
                    # We have to join the payload fragments get the payload
                    self._payload_fragments.append(data_cstr[f_start_pos:f_end_pos])
                    if self._has_mask:
                        assert self._frame_mask is not None
                        payload_bytearray = bytearray(b"".join(self._payload_fragments))
                        websocket_mask(self._frame_mask, payload_bytearray)
                        payload = payload_bytearray
                    else:
                        payload = b"".join(self._payload_fragments)
                    self._payload_fragments.clear()
                elif self._has_mask:
                    assert self._frame_mask is not None
                    payload_bytearray = data_cstr[f_start_pos:f_end_pos]  # type: ignore[assignment]
                    if type(payload_bytearray) is not bytearray:  # pragma: no branch
                        # Cython will do the conversion for us
                        # but we need to do it for Python and we
                        # will always get here in Python
                        payload_bytearray = bytearray(payload_bytearray)
                    websocket_mask(self._frame_mask, payload_bytearray)
                    payload = payload_bytearray
                else:
                    payload = data_cstr[f_start_pos:f_end_pos]

                self._handle_frame(
                    self._frame_fin, self._frame_opcode, payload, self._compressed
                )
                self._frame_payload_len = 0
                self._state = READ_HEADER

        # XXX: Cython needs slices to be bounded, so we can't omit the slice end here.
        self._tail = data_cstr[start_pos:data_len] if start_pos < data_len else b""

# === NexusCore/openenv\Lib\site-packages\aiohttp\_websocket\reader_py.py ===
"""Reader for WebSocket protocol versions 13 and 8."""

import asyncio
import builtins
from collections import deque
from typing import Deque, Final, Optional, Set, Tuple, Union

from ..base_protocol import BaseProtocol
from ..compression_utils import ZLibDecompressor
from ..helpers import _EXC_SENTINEL, set_exception
from ..streams import EofStream
from .helpers import UNPACK_CLOSE_CODE, UNPACK_LEN3, websocket_mask
from .models import (
    WS_DEFLATE_TRAILING,
    WebSocketError,
    WSCloseCode,
    WSMessage,
    WSMsgType,
)

ALLOWED_CLOSE_CODES: Final[Set[int]] = {int(i) for i in WSCloseCode}

# States for the reader, used to parse the WebSocket frame
# integer values are used so they can be cythonized
READ_HEADER = 1
READ_PAYLOAD_LENGTH = 2
READ_PAYLOAD_MASK = 3
READ_PAYLOAD = 4

WS_MSG_TYPE_BINARY = WSMsgType.BINARY
WS_MSG_TYPE_TEXT = WSMsgType.TEXT

# WSMsgType values unpacked so they can by cythonized to ints
OP_CODE_NOT_SET = -1
OP_CODE_CONTINUATION = WSMsgType.CONTINUATION.value
OP_CODE_TEXT = WSMsgType.TEXT.value
OP_CODE_BINARY = WSMsgType.BINARY.value
OP_CODE_CLOSE = WSMsgType.CLOSE.value
OP_CODE_PING = WSMsgType.PING.value
OP_CODE_PONG = WSMsgType.PONG.value

EMPTY_FRAME_ERROR = (True, b"")
EMPTY_FRAME = (False, b"")

COMPRESSED_NOT_SET = -1
COMPRESSED_FALSE = 0
COMPRESSED_TRUE = 1

TUPLE_NEW = tuple.__new__

cython_int = int  # Typed to int in Python, but cython with use a signed int in the pxd


class WebSocketDataQueue:
    """WebSocketDataQueue resumes and pauses an underlying stream.

    It is a destination for WebSocket data.
    """

    def __init__(
        self, protocol: BaseProtocol, limit: int, *, loop: asyncio.AbstractEventLoop
    ) -> None:
        self._size = 0
        self._protocol = protocol
        self._limit = limit * 2
        self._loop = loop
        self._eof = False
        self._waiter: Optional[asyncio.Future[None]] = None
        self._exception: Union[BaseException, None] = None
        self._buffer: Deque[Tuple[WSMessage, int]] = deque()
        self._get_buffer = self._buffer.popleft
        self._put_buffer = self._buffer.append

    def is_eof(self) -> bool:
        return self._eof

    def exception(self) -> Optional[BaseException]:
        return self._exception

    def set_exception(
        self,
        exc: BaseException,
        exc_cause: builtins.BaseException = _EXC_SENTINEL,
    ) -> None:
        self._eof = True
        self._exception = exc
        if (waiter := self._waiter) is not None:
            self._waiter = None
            set_exception(waiter, exc, exc_cause)

    def _release_waiter(self) -> None:
        if (waiter := self._waiter) is None:
            return
        self._waiter = None
        if not waiter.done():
            waiter.set_result(None)

    def feed_eof(self) -> None:
        self._eof = True
        self._release_waiter()
        self._exception = None  # Break cyclic references

    def feed_data(self, data: "WSMessage", size: "cython_int") -> None:
        self._size += size
        self._put_buffer((data, size))
        self._release_waiter()
        if self._size > self._limit and not self._protocol._reading_paused:
            self._protocol.pause_reading()

    async def read(self) -> WSMessage:
        if not self._buffer and not self._eof:
            assert not self._waiter
            self._waiter = self._loop.create_future()
            try:
                await self._waiter
            except (asyncio.CancelledError, asyncio.TimeoutError):
                self._waiter = None
                raise
        return self._read_from_buffer()

    def _read_from_buffer(self) -> WSMessage:
        if self._buffer:
            data, size = self._get_buffer()
            self._size -= size
            if self._size < self._limit and self._protocol._reading_paused:
                self._protocol.resume_reading()
            return data
        if self._exception is not None:
            raise self._exception
        raise EofStream


class WebSocketReader:
    def __init__(
        self, queue: WebSocketDataQueue, max_msg_size: int, compress: bool = True
    ) -> None:
        self.queue = queue
        self._max_msg_size = max_msg_size

        self._exc: Optional[Exception] = None
        self._partial = bytearray()
        self._state = READ_HEADER

        self._opcode: int = OP_CODE_NOT_SET
        self._frame_fin = False
        self._frame_opcode: int = OP_CODE_NOT_SET
        self._payload_fragments: list[bytes] = []
        self._frame_payload_len = 0

        self._tail: bytes = b""
        self._has_mask = False
        self._frame_mask: Optional[bytes] = None
        self._payload_bytes_to_read = 0
        self._payload_len_flag = 0
        self._compressed: int = COMPRESSED_NOT_SET
        self._decompressobj: Optional[ZLibDecompressor] = None
        self._compress = compress

    def feed_eof(self) -> None:
        self.queue.feed_eof()

    # data can be bytearray on Windows because proactor event loop uses bytearray
    # and asyncio types this to Union[bytes, bytearray, memoryview] so we need
    # coerce data to bytes if it is not
    def feed_data(
        self, data: Union[bytes, bytearray, memoryview]
    ) -> Tuple[bool, bytes]:
        if type(data) is not bytes:
            data = bytes(data)

        if self._exc is not None:
            return True, data

        try:
            self._feed_data(data)
        except Exception as exc:
            self._exc = exc
            set_exception(self.queue, exc)
            return EMPTY_FRAME_ERROR

        return EMPTY_FRAME

    def _handle_frame(
        self,
        fin: bool,
        opcode: Union[int, cython_int],  # Union intended: Cython pxd uses C int
        payload: Union[bytes, bytearray],
        compressed: Union[int, cython_int],  # Union intended: Cython pxd uses C int
    ) -> None:
        msg: WSMessage
        if opcode in {OP_CODE_TEXT, OP_CODE_BINARY, OP_CODE_CONTINUATION}:
            # load text/binary
            if not fin:
                # got partial frame payload
                if opcode != OP_CODE_CONTINUATION:
                    self._opcode = opcode
                self._partial += payload
                if self._max_msg_size and len(self._partial) >= self._max_msg_size:
                    raise WebSocketError(
                        WSCloseCode.MESSAGE_TOO_BIG,
                        f"Message size {len(self._partial)} "
                        f"exceeds limit {self._max_msg_size}",
                    )
                return

            has_partial = bool(self._partial)
            if opcode == OP_CODE_CONTINUATION:
                if self._opcode == OP_CODE_NOT_SET:
                    raise WebSocketError(
                        WSCloseCode.PROTOCOL_ERROR,
                        "Continuation frame for non started message",
                    )
                opcode = self._opcode
                self._opcode = OP_CODE_NOT_SET
            # previous frame was non finished
            # we should get continuation opcode
            elif has_partial:
                raise WebSocketError(
                    WSCloseCode.PROTOCOL_ERROR,
                    "The opcode in non-fin frame is expected "
                    f"to be zero, got {opcode!r}",
                )

            assembled_payload: Union[bytes, bytearray]
            if has_partial:
                assembled_payload = self._partial + payload
                self._partial.clear()
            else:
                assembled_payload = payload

            if self._max_msg_size and len(assembled_payload) >= self._max_msg_size:
                raise WebSocketError(
                    WSCloseCode.MESSAGE_TOO_BIG,
                    f"Message size {len(assembled_payload)} "
                    f"exceeds limit {self._max_msg_size}",
                )

            # Decompress process must to be done after all packets
            # received.
            if compressed:
                if not self._decompressobj:
                    self._decompressobj = ZLibDecompressor(suppress_deflate_header=True)
                # XXX: It's possible that the zlib backend (isal is known to
                # do this, maybe others too?) will return max_length bytes,
                # but internally buffer more data such that the payload is
                # >max_length, so we return one extra byte and if we're able
                # to do that, then the message is too big.
                payload_merged = self._decompressobj.decompress_sync(
                    assembled_payload + WS_DEFLATE_TRAILING,
                    (
                        self._max_msg_size + 1
                        if self._max_msg_size
                        else self._max_msg_size
                    ),
                )
                if self._max_msg_size and len(payload_merged) > self._max_msg_size:
                    raise WebSocketError(
                        WSCloseCode.MESSAGE_TOO_BIG,
                        f"Decompressed message exceeds size limit {self._max_msg_size}",
                    )
            elif type(assembled_payload) is bytes:
                payload_merged = assembled_payload
            else:
                payload_merged = bytes(assembled_payload)

            if opcode == OP_CODE_TEXT:
                try:
                    text = payload_merged.decode("utf-8")
                except UnicodeDecodeError as exc:
                    raise WebSocketError(
                        WSCloseCode.INVALID_TEXT, "Invalid UTF-8 text message"
                    ) from exc

                # XXX: The Text and Binary messages here can be a performance
                # bottleneck, so we use tuple.__new__ to improve performance.
                # This is not type safe, but many tests should fail in
                # test_client_ws_functional.py if this is wrong.
                self.queue.feed_data(
                    TUPLE_NEW(WSMessage, (WS_MSG_TYPE_TEXT, text, "")),
                    len(payload_merged),
                )
            else:
                self.queue.feed_data(
                    TUPLE_NEW(WSMessage, (WS_MSG_TYPE_BINARY, payload_merged, "")),
                    len(payload_merged),
                )
        elif opcode == OP_CODE_CLOSE:
            if len(payload) >= 2:
                close_code = UNPACK_CLOSE_CODE(payload[:2])[0]
                if close_code < 3000 and close_code not in ALLOWED_CLOSE_CODES:
                    raise WebSocketError(
                        WSCloseCode.PROTOCOL_ERROR,
                        f"Invalid close code: {close_code}",
                    )
                try:
                    close_message = payload[2:].decode("utf-8")
                except UnicodeDecodeError as exc:
                    raise WebSocketError(
                        WSCloseCode.INVALID_TEXT, "Invalid UTF-8 text message"
                    ) from exc
                msg = TUPLE_NEW(WSMessage, (WSMsgType.CLOSE, close_code, close_message))
            elif payload:
                raise WebSocketError(
                    WSCloseCode.PROTOCOL_ERROR,
                    f"Invalid close frame: {fin} {opcode} {payload!r}",
                )
            else:
                msg = TUPLE_NEW(WSMessage, (WSMsgType.CLOSE, 0, ""))

            self.queue.feed_data(msg, 0)
        elif opcode == OP_CODE_PING:
            msg = TUPLE_NEW(WSMessage, (WSMsgType.PING, payload, ""))
            self.queue.feed_data(msg, len(payload))
        elif opcode == OP_CODE_PONG:
            msg = TUPLE_NEW(WSMessage, (WSMsgType.PONG, payload, ""))
            self.queue.feed_data(msg, len(payload))
        else:
            raise WebSocketError(
                WSCloseCode.PROTOCOL_ERROR, f"Unexpected opcode={opcode!r}"
            )

    def _feed_data(self, data: bytes) -> None:
        """Return the next frame from the socket."""
        if self._tail:
            data, self._tail = self._tail + data, b""

        start_pos: int = 0
        data_len = len(data)
        data_cstr = data

        while True:
            # read header
            if self._state == READ_HEADER:
                if data_len - start_pos < 2:
                    break
                first_byte = data_cstr[start_pos]
                second_byte = data_cstr[start_pos + 1]
                start_pos += 2

                fin = (first_byte >> 7) & 1
                rsv1 = (first_byte >> 6) & 1
                rsv2 = (first_byte >> 5) & 1
                rsv3 = (first_byte >> 4) & 1
                opcode = first_byte & 0xF

                # frame-fin = %x0 ; more frames of this message follow
                #           / %x1 ; final frame of this message
                # frame-rsv1 = %x0 ;
                #    1 bit, MUST be 0 unless negotiated otherwise
                # frame-rsv2 = %x0 ;
                #    1 bit, MUST be 0 unless negotiated otherwise
                # frame-rsv3 = %x0 ;
                #    1 bit, MUST be 0 unless negotiated otherwise
                #
                # Remove rsv1 from this test for deflate development
                if rsv2 or rsv3 or (rsv1 and not self._compress):
                    raise WebSocketError(
                        WSCloseCode.PROTOCOL_ERROR,
                        "Received frame with non-zero reserved bits",
                    )

                if opcode > 0x7 and fin == 0:
                    raise WebSocketError(
                        WSCloseCode.PROTOCOL_ERROR,
                        "Received fragmented control frame",
                    )

                has_mask = (second_byte >> 7) & 1
                length = second_byte & 0x7F

                # Control frames MUST have a payload
                # length of 125 bytes or less
                if opcode > 0x7 and length > 125:
                    raise WebSocketError(
                        WSCloseCode.PROTOCOL_ERROR,
                        "Control frame payload cannot be larger than 125 bytes",
                    )

                # Set compress status if last package is FIN
                # OR set compress status if this is first fragment
                # Raise error if not first fragment with rsv1 = 0x1
                if self._frame_fin or self._compressed == COMPRESSED_NOT_SET:
                    self._compressed = COMPRESSED_TRUE if rsv1 else COMPRESSED_FALSE
                elif rsv1:
                    raise WebSocketError(
                        WSCloseCode.PROTOCOL_ERROR,
                        "Received frame with non-zero reserved bits",
                    )

                self._frame_fin = bool(fin)
                self._frame_opcode = opcode
                self._has_mask = bool(has_mask)
                self._payload_len_flag = length
                self._state = READ_PAYLOAD_LENGTH

            # read payload length
            if self._state == READ_PAYLOAD_LENGTH:
                len_flag = self._payload_len_flag
                if len_flag == 126:
                    if data_len - start_pos < 2:
                        break
                    first_byte = data_cstr[start_pos]
                    second_byte = data_cstr[start_pos + 1]
                    start_pos += 2
                    self._payload_bytes_to_read = first_byte << 8 | second_byte
                elif len_flag > 126:
                    if data_len - start_pos < 8:
                        break
                    self._payload_bytes_to_read = UNPACK_LEN3(data, start_pos)[0]
                    start_pos += 8
                else:
                    self._payload_bytes_to_read = len_flag

                self._state = READ_PAYLOAD_MASK if self._has_mask else READ_PAYLOAD

            # read payload mask
            if self._state == READ_PAYLOAD_MASK:
                if data_len - start_pos < 4:
                    break
                self._frame_mask = data_cstr[start_pos : start_pos + 4]
                start_pos += 4
                self._state = READ_PAYLOAD

            if self._state == READ_PAYLOAD:
                chunk_len = data_len - start_pos
                if self._payload_bytes_to_read >= chunk_len:
                    f_end_pos = data_len
                    self._payload_bytes_to_read -= chunk_len
                else:
                    f_end_pos = start_pos + self._payload_bytes_to_read
                    self._payload_bytes_to_read = 0

                had_fragments = self._frame_payload_len
                self._frame_payload_len += f_end_pos - start_pos
                f_start_pos = start_pos
                start_pos = f_end_pos

                if self._payload_bytes_to_read != 0:
                    # If we don't have a complete frame, we need to save the
                    # data for the next call to feed_data.
                    self._payload_fragments.append(data_cstr[f_start_pos:f_end_pos])
                    break

                payload: Union[bytes, bytearray]
                if had_fragments:
                    # We have to join the payload fragments get the payload
                    self._payload_fragments.append(data_cstr[f_start_pos:f_end_pos])
                    if self._has_mask:
                        assert self._frame_mask is not None
                        payload_bytearray = bytearray(b"".join(self._payload_fragments))
                        websocket_mask(self._frame_mask, payload_bytearray)
                        payload = payload_bytearray
                    else:
                        payload = b"".join(self._payload_fragments)
                    self._payload_fragments.clear()
                elif self._has_mask:
                    assert self._frame_mask is not None
                    payload_bytearray = data_cstr[f_start_pos:f_end_pos]  # type: ignore[assignment]
                    if type(payload_bytearray) is not bytearray:  # pragma: no branch
                        # Cython will do the conversion for us
                        # but we need to do it for Python and we
                        # will always get here in Python
                        payload_bytearray = bytearray(payload_bytearray)
                    websocket_mask(self._frame_mask, payload_bytearray)
                    payload = payload_bytearray
                else:
                    payload = data_cstr[f_start_pos:f_end_pos]

                self._handle_frame(
                    self._frame_fin, self._frame_opcode, payload, self._compressed
                )
                self._frame_payload_len = 0
                self._state = READ_HEADER

        # XXX: Cython needs slices to be bounded, so we can't omit the slice end here.
        self._tail = data_cstr[start_pos:data_len] if start_pos < data_len else b""

# === NexusCore/openenv\Lib\site-packages\interpreter\terminal_interface\local_setup.py ===
# Thank you Ty Fiero for making this!

import os
import platform
import subprocess
import sys
import time

import inquirer
import psutil
import requests
import wget


def local_setup(interpreter, provider=None, model=None):
    def download_model(models_dir, models, interpreter):
        # Get RAM and disk information
        total_ram = psutil.virtual_memory().total / (
            1024 * 1024 * 1024
        )  # Convert bytes to GB
        free_disk_space = psutil.disk_usage("/").free / (
            1024 * 1024 * 1024
        )  # Convert bytes to GB

        # Display the users hardware specs
        interpreter.display_message(
            f"Your machine has `{total_ram:.2f}GB` of RAM, and `{free_disk_space:.2f}GB` of free storage space."
        )

        if total_ram < 10:
            interpreter.display_message(
                f"\nYour computer realistically can only run smaller models less than 4GB, Phi-2 might be the best model for your computer.\n"
            )
        elif 10 <= total_ram < 30:
            interpreter.display_message(
                f"\nYour computer could handle a mid-sized model (4-10GB), Mistral-7B might be the best model for your computer.\n"
            )
        else:
            interpreter.display_message(
                f"\nYour computer should have enough RAM to run any model below.\n"
            )

        interpreter.display_message(
            f"In general, the larger the model, the better the performance, but choose a model that best fits your computer's hardware. \nOnly models you have the storage space to download are shown:\n"
        )

        try:
            model_list = [
                {
                    "name": "Llama-3.1-8B-Instruct",
                    "file_name": "Meta-Llama-3-8B-Instruct.Q4_K_M.llamafile",
                    "size": 4.95,
                    "url": "https://huggingface.co/Mozilla/Meta-Llama-3.1-8B-Instruct-llamafile/resolve/main/Meta-Llama-3.1-8B-Instruct.Q4_K_M.llamafile?download=true",
                },
                {
                    "name": "Gemma-2-9b",
                    "file_name": "gemma-2-9b-it.Q4_K_M.llamafile",
                    "size": 5.79,
                    "url": "https://huggingface.co/jartine/gemma-2-9b-it-llamafile/resolve/main/gemma-2-9b-it.Q4_K_M.llamafile?download=true",
                },
                {
                    "name": "Phi-3-mini",
                    "file_name": "Phi-3-mini-4k-instruct.Q4_K_M.llamafile",
                    "size": 2.42,
                    "url": "https://huggingface.co/Mozilla/Phi-3-mini-4k-instruct-llamafile/resolve/main/Phi-3-mini-4k-instruct.Q4_K_M.llamafile?download=true",
                },
                {
                    "name": "Moondream2 (vision)",
                    "file_name": "moondream2-q5km-050824.llamafile",
                    "size": 1.98,
                    "url": "https://huggingface.co/cjpais/moondream2-llamafile/resolve/main/moondream2-q5km-050824.llamafile?download=true",
                },
                {
                    "name": "Mistral-7B-Instruct",
                    "file_name": "Mistral-7B-Instruct-v0.3.Q4_K_M.llamafile",
                    "size": 4.40,
                    "url": "https://huggingface.co/Mozilla/Mistral-7B-Instruct-v0.3-llamafile/resolve/main/Mistral-7B-Instruct-v0.3.Q4_K_M.llamafile?download=true",
                },
                {
                    "name": "Gemma-2-27b",
                    "file_name": "gemma-2-27b-it.Q4_K_M.llamafile",
                    "size": 16.7,
                    "url": "https://huggingface.co/jartine/gemma-2-27b-it-llamafile/resolve/main/gemma-2-27b-it.Q4_K_M.llamafile?download=true",
                },
                {
                    "name": "TinyLlama-1.1B",
                    "file_name": "TinyLlama-1.1B-Chat-v1.0.Q4_K_M.llamafile",
                    "size": 0.70,
                    "url": "https://huggingface.co/Mozilla/TinyLlama-1.1B-Chat-v1.0-llamafile/resolve/main/TinyLlama-1.1B-Chat-v1.0.Q4_K_M.llamafile?download=true",
                },
                {
                    "name": "Rocket-3B",
                    "file_name": "rocket-3b.Q4_K_M.llamafile",
                    "size": 1.74,
                    "url": "https://huggingface.co/Mozilla/rocket-3B-llamafile/resolve/main/rocket-3b.Q4_K_M.llamafile?download=true",
                },
                {
                    "name": "LLaVA 1.5 (vision)",
                    "file_name": "llava-v1.5-7b-q4.llamafile",
                    "size": 4.29,
                    "url": "https://huggingface.co/Mozilla/llava-v1.5-7b-llamafile/resolve/main/llava-v1.5-7b-q4.llamafile?download=true",
                },
                {
                    "name": "WizardCoder-Python-13B",
                    "file_name": "wizardcoder-python-13b.llamafile",
                    "size": 7.33,
                    "url": "https://huggingface.co/jartine/wizardcoder-13b-python/resolve/main/wizardcoder-python-13b.llamafile?download=true",
                },
                {
                    "name": "WizardCoder-Python-34B",
                    "file_name": "wizardcoder-python-34b-v1.0.Q4_K_M.llamafile",
                    "size": 20.22,
                    "url": "https://huggingface.co/Mozilla/WizardCoder-Python-34B-V1.0-llamafile/resolve/main/wizardcoder-python-34b-v1.0.Q4_K_M.llamafile?download=true",
                },
                {
                    "name": "Mixtral-8x7B-Instruct",
                    "file_name": "mixtral-8x7b-instruct-v0.1.Q5_K_M.llamafile",
                    "size": 30.03,
                    "url": "https://huggingface.co/jartine/Mixtral-8x7B-Instruct-v0.1-llamafile/resolve/main/mixtral-8x7b-instruct-v0.1.Q5_K_M.llamafile?download=true",
                },
            ]

            # Filter models based on available disk space and RAM
            filtered_models = [
                model
                for model in model_list
                if model["size"] <= free_disk_space and model["file_name"] not in models
            ]
            if filtered_models:
                time.sleep(1)

                # Prompt the user to select a model
                model_choices = [
                    f"{model['name']} ({model['size']:.2f}GB)"
                    for model in filtered_models
                ]
                questions = [
                    inquirer.List(
                        "model",
                        message="Select a model to download:",
                        choices=model_choices,
                    )
                ]
                answers = inquirer.prompt(questions)

                if answers == None:
                    exit()

                # Get the selected model
                selected_model = next(
                    model
                    for model in filtered_models
                    if f"{model['name']} ({model['size']}GB)" == answers["model"]
                )

                # Download the selected model
                model_url = selected_model["url"]
                # Extract the basename and remove query parameters
                filename = os.path.basename(model_url).split("?")[0]
                model_path = os.path.join(models_dir, filename)

                # time.sleep(0.3)

                print(f"\nDownloading {selected_model['name']}...\n")
                wget.download(model_url, model_path)

                # Make the model executable if not on Windows
                if platform.system() != "Windows":
                    subprocess.run(["chmod", "+x", model_path], check=True)

                print(f"\nModel '{selected_model['name']}' downloaded successfully.\n")

                interpreter.display_message(
                    "To view or delete downloaded local models, run `interpreter --local_models`\n\n"
                )

                return model_path
            else:
                print(
                    "\nYour computer does not have enough storage to download any local LLMs.\n"
                )
                return None
        except Exception as e:
            print(e)
            print(
                "\nAn error occurred while trying to download the model. Please try again or use a different local model provider.\n"
            )
            return None

    # START OF LOCAL MODEL PROVIDER LOGIC
    interpreter.display_message(
        "\n**Open Interpreter** supports multiple local model providers.\n"
    )

    # Define the choices for local models
    choices = [
        "Ollama",
        "Llamafile",
        "LM Studio",
        "Jan",
    ]

    # Use inquirer to let the user select an option
    questions = [
        inquirer.List(
            "model",
            message="Select a provider",
            choices=choices,
        ),
    ]
    answers = inquirer.prompt(questions)

    if answers == None:
        exit()

    selected_model = answers["model"]

    if selected_model == "LM Studio":
        interpreter.display_message(
            """
    To use Open Interpreter with **LM Studio**, you will need to run **LM Studio** in the background.

    1. Download **LM Studio** from [https://lmstudio.ai/](https://lmstudio.ai/), then start it.
    2. Select a language model then click **Download**.
    3. Click the **<->** button on the left (below the chat button).
    4. Select your model at the top, then click **Start Server**.


    Once the server is running, you can begin your conversation below.

    """
        )
        interpreter.llm.supports_functions = False
        interpreter.llm.api_base = "http://localhost:1234/v1"
        interpreter.llm.api_key = "dummy"

    elif selected_model == "Ollama":
        try:
            # List out all downloaded ollama models. Will fail if ollama isn't installed
            result = subprocess.run(
                ["ollama", "list"], capture_output=True, text=True, check=True
            )
            lines = result.stdout.split("\n")

            names = [
                line.split()[0].replace(":latest", "")
                for line in lines
                if line.strip()
                and not line.startswith("failed")
                and not line.startswith("NAME")
            ]  # Extract names, trim out ":latest", skip header

            # Models whose name contain one of these keywords will be moved to the front of the list
            priority_models = ["llama3", "codestral"]
            priority_models_found = []
            for word in priority_models:
                models_to_move = [
                    name for name in names if word.lower() in name.lower()
                ]
                priority_models_found.extend(models_to_move)
            names = [
                name
                for name in names
                if not any(word.lower() in name.lower() for word in priority_models)
            ]
            names = priority_models_found + names

            for model in ["llama3.1", "phi3", "mistral-nemo", "gemma2", "codestral"]:
                if model not in names:
                    names.append("↓ Download " + model)

            names.append("Browse Models ↗")

            # Create a new inquirer selection from the names
            name_question = [
                inquirer.List(
                    "name",
                    message="Select a model",
                    choices=names,
                ),
            ]
            name_answer = inquirer.prompt(name_question)

            if name_answer == None:
                exit()

            selected_name = name_answer["name"]

            if "↓ Download " in selected_name:
                model = selected_name.split(" ")[-1]
                interpreter.display_message(f"\nDownloading {model}...\n")
                subprocess.run(["ollama", "pull", model], check=True)
            elif "Browse Models ↗" in selected_name:
                interpreter.display_message(
                    "Opening [ollama.com/library](ollama.com/library)."
                )
                import webbrowser

                webbrowser.open("https://ollama.com/library")
                exit()
            else:
                model = selected_name.strip()

            # Set the model to the selected model
            interpreter.llm.model = f"ollama/{model}"

            # Send a ping, which will actually load the model

            old_max_tokens = interpreter.llm.max_tokens
            old_context_window = interpreter.llm.context_window
            interpreter.llm.max_tokens = 1
            interpreter.llm.context_window = 100

            interpreter.computer.ai.chat("ping")

            interpreter.llm.max_tokens = old_max_tokens
            interpreter.llm.context_window = old_context_window

            interpreter.display_message(f"> Model set to `{model}`")

        # If Ollama is not installed or not recognized as a command, prompt the user to download Ollama and try again
        except (subprocess.CalledProcessError, FileNotFoundError) as e:
            print("Ollama is not installed or not recognized as a command.")
            time.sleep(1)
            interpreter.display_message(
                f"\nPlease visit [https://ollama.com/](https://ollama.com/) to download Ollama and try again.\n"
            )
            time.sleep(2)
            sys.exit(1)

    elif selected_model == "Jan":
        interpreter.display_message(
            """
    To use Open Interpreter with **Jan**, you will need to run **Jan** in the background.

    1. Download **Jan** from [https://jan.ai/](https://jan.ai/), then start it.
    2. Select a language model from the "Hub" tab, then click **Download**.
    3. Copy the ID of the model and enter it below.
    3. Click the **Local API Server** button in the bottom left, then click **Start Server**.


    Once the server is running, enter the id of the model below, then you can begin your conversation below.

    """
        )
        interpreter.llm.api_base = "http://localhost:1337/v1"
        # time.sleep(1)

        # Send a GET request to the Jan API to get the list of models
        response = requests.get(f"{interpreter.llm.api_base}/models")
        models = response.json()["data"]

        # Extract the model ids from the response
        model_ids = [model["id"] for model in models]
        model_ids.insert(0, ">> Type Custom Model ID")

        # Prompt the user to select a model from the list
        model_name_question = [
            inquirer.List(
                "jan_model_name",
                message="Select the model you have running on Jan",
                choices=model_ids,
            ),
        ]
        model_name_answer = inquirer.prompt(model_name_question)

        if model_name_answer == None:
            exit()

        jan_model_name = model_name_answer["jan_model_name"]
        if jan_model_name == ">> Type Custom Model ID":
            jan_model_name = input("Enter the custom model ID: ")

        interpreter.llm.model = jan_model_name
        interpreter.llm.api_key = "dummy"
        interpreter.display_message(f"\nUsing Jan model: `{jan_model_name}` \n")
        # time.sleep(1)

    elif selected_model == "Llamafile":
        if platform.system() == "Darwin":  # Check if the system is MacOS
            result = subprocess.run(
                ["xcode-select", "-p"], stdout=subprocess.PIPE, stderr=subprocess.STDOUT
            )
            if result.returncode != 0:
                interpreter.display_message(
                    "To use Llamafile, Open Interpreter requires Mac users to have Xcode installed. You can install Xcode from https://developer.apple.com/xcode/ .\n\nAlternatively, you can use `LM Studio`, `Jan.ai`, or `Ollama` to manage local language models. Learn more at https://docs.openinterpreter.com/guides/running-locally ."
                )
                time.sleep(3)
                raise Exception(
                    "Xcode is not installed. Please install Xcode and try again."
                )

        # Define the path to the models directory
        models_dir = os.path.join(interpreter.get_oi_dir(), "models")

        # Check and create the models directory if it doesn't exist
        if not os.path.exists(models_dir):
            os.makedirs(models_dir)

        # Check if there are any models in the models folder
        models = [f for f in os.listdir(models_dir) if f.endswith(".llamafile")]

        if not models:
            print(
                "\nNo models currently downloaded. Please select a new model to download.\n"
            )
            model_path = download_model(models_dir, models, interpreter)
        else:
            # Prompt the user to select a downloaded model or download a new one
            model_choices = models + ["↓ Download new model"]
            questions = [
                inquirer.List(
                    "model",
                    message="Select a model",
                    choices=model_choices,
                )
            ]
            answers = inquirer.prompt(questions)

            if answers == None:
                exit()

            if answers["model"] == "↓ Download new model":
                model_path = download_model(models_dir, models, interpreter)
            else:
                model_path = os.path.join(models_dir, answers["model"])

            if model_path:
                try:
                    # Run the selected model and hide its output
                    process = subprocess.Popen(
                        f'"{model_path}" ' + " ".join(["--nobrowser", "-ngl", "9999"]),
                        shell=True,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.STDOUT,
                        text=True,
                    )

                    for line in process.stdout:
                        if "llama server listening at " in line:
                            break  # Exit the loop once the server is ready
                except Exception as e:
                    process.kill()  # Force kill if not terminated after timeout
                    print(e)
                    print("Model process terminated.")

        # Set flags for Llamafile to work with interpreter
        interpreter.llm.model = "openai/local"
        interpreter.llm.api_key = "dummy"
        interpreter.llm.temperature = 0
        interpreter.llm.api_base = "http://localhost:8080/v1"
        interpreter.llm.supports_functions = False

        model_name = model_path.split("/")[-1]
        interpreter.display_message(f"> Model set to `{model_name}`")

    user_ram = psutil.virtual_memory().total / (
        1024 * 1024 * 1024
    )  # Convert bytes to GB
    # Set context window and max tokens for all local models based on the users available RAM
    if user_ram and user_ram > 9:
        interpreter.llm.max_tokens = 1200
        interpreter.llm.context_window = 8000
    else:
        interpreter.llm.max_tokens = 1000
        interpreter.llm.context_window = 3000

    # Display intro message
    if interpreter.auto_run == False:
        interpreter.display_message(
            "**Open Interpreter** will require approval before running code."
            + "\n\nUse `interpreter -y` to bypass this."
            + "\n\nPress `CTRL-C` to exit.\n"
        )

    return interpreter

# === NexusCore/openenv\Lib\site-packages\nltk\metrics\association.py ===
# Natural Language Toolkit: Ngram Association Measures
#
# Copyright (C) 2001-2024 NLTK Project
# Author: Joel Nothman <jnothman@student.usyd.edu.au>
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT

"""
Provides scoring functions for a number of association measures through a
generic, abstract implementation in ``NgramAssocMeasures``, and n-specific
``BigramAssocMeasures`` and ``TrigramAssocMeasures``.
"""

import math as _math
from abc import ABCMeta, abstractmethod
from functools import reduce

_log2 = lambda x: _math.log2(x)
_ln = _math.log

_product = lambda s: reduce(lambda x, y: x * y, s)

_SMALL = 1e-20

try:
    from scipy.stats import fisher_exact
except ImportError:

    def fisher_exact(*_args, **_kwargs):
        raise NotImplementedError


### Indices to marginals arguments:

NGRAM = 0
"""Marginals index for the ngram count"""

UNIGRAMS = -2
"""Marginals index for a tuple of each unigram count"""

TOTAL = -1
"""Marginals index for the number of words in the data"""


class NgramAssocMeasures(metaclass=ABCMeta):
    """
    An abstract class defining a collection of generic association measures.
    Each public method returns a score, taking the following arguments::

        score_fn(count_of_ngram,
                 (count_of_n-1gram_1, ..., count_of_n-1gram_j),
                 (count_of_n-2gram_1, ..., count_of_n-2gram_k),
                 ...,
                 (count_of_1gram_1, ..., count_of_1gram_n),
                 count_of_total_words)

    See ``BigramAssocMeasures`` and ``TrigramAssocMeasures``

    Inheriting classes should define a property _n, and a method _contingency
    which calculates contingency values from marginals in order for all
    association measures defined here to be usable.
    """

    _n = 0

    @staticmethod
    @abstractmethod
    def _contingency(*marginals):
        """Calculates values of a contingency table from marginal values."""
        raise NotImplementedError(
            "The contingency table is not available" "in the general ngram case"
        )

    @staticmethod
    @abstractmethod
    def _marginals(*contingency):
        """Calculates values of contingency table marginals from its values."""
        raise NotImplementedError(
            "The contingency table is not available" "in the general ngram case"
        )

    @classmethod
    def _expected_values(cls, cont):
        """Calculates expected values for a contingency table."""
        n_all = sum(cont)
        bits = [1 << i for i in range(cls._n)]

        # For each contingency table cell
        for i in range(len(cont)):
            # Yield the expected value
            yield (
                _product(
                    sum(cont[x] for x in range(2**cls._n) if (x & j) == (i & j))
                    for j in bits
                )
                / (n_all ** (cls._n - 1))
            )

    @staticmethod
    def raw_freq(*marginals):
        """Scores ngrams by their frequency"""
        return marginals[NGRAM] / marginals[TOTAL]

    @classmethod
    def student_t(cls, *marginals):
        """Scores ngrams using Student's t test with independence hypothesis
        for unigrams, as in Manning and Schutze 5.3.1.
        """
        return (
            marginals[NGRAM]
            - _product(marginals[UNIGRAMS]) / (marginals[TOTAL] ** (cls._n - 1))
        ) / (marginals[NGRAM] + _SMALL) ** 0.5

    @classmethod
    def chi_sq(cls, *marginals):
        """Scores ngrams using Pearson's chi-square as in Manning and Schutze
        5.3.3.
        """
        cont = cls._contingency(*marginals)
        exps = cls._expected_values(cont)
        return sum((obs - exp) ** 2 / (exp + _SMALL) for obs, exp in zip(cont, exps))

    @staticmethod
    def mi_like(*marginals, **kwargs):
        """Scores ngrams using a variant of mutual information. The keyword
        argument power sets an exponent (default 3) for the numerator. No
        logarithm of the result is calculated.
        """
        return marginals[NGRAM] ** kwargs.get("power", 3) / _product(
            marginals[UNIGRAMS]
        )

    @classmethod
    def pmi(cls, *marginals):
        """Scores ngrams by pointwise mutual information, as in Manning and
        Schutze 5.4.
        """
        return _log2(marginals[NGRAM] * marginals[TOTAL] ** (cls._n - 1)) - _log2(
            _product(marginals[UNIGRAMS])
        )

    @classmethod
    def likelihood_ratio(cls, *marginals):
        """Scores ngrams using likelihood ratios as in Manning and Schutze 5.3.4."""
        cont = cls._contingency(*marginals)
        return 2 * sum(
            obs * _ln(obs / (exp + _SMALL) + _SMALL)
            for obs, exp in zip(cont, cls._expected_values(cont))
        )

    @classmethod
    def poisson_stirling(cls, *marginals):
        """Scores ngrams using the Poisson-Stirling measure."""
        exp = _product(marginals[UNIGRAMS]) / (marginals[TOTAL] ** (cls._n - 1))
        return marginals[NGRAM] * (_log2(marginals[NGRAM] / exp) - 1)

    @classmethod
    def jaccard(cls, *marginals):
        """Scores ngrams using the Jaccard index."""
        cont = cls._contingency(*marginals)
        return cont[0] / sum(cont[:-1])


class BigramAssocMeasures(NgramAssocMeasures):
    """
    A collection of bigram association measures. Each association measure
    is provided as a function with three arguments::

        bigram_score_fn(n_ii, (n_ix, n_xi), n_xx)

    The arguments constitute the marginals of a contingency table, counting
    the occurrences of particular events in a corpus. The letter i in the
    suffix refers to the appearance of the word in question, while x indicates
    the appearance of any word. Thus, for example:

    - n_ii counts ``(w1, w2)``, i.e. the bigram being scored
    - n_ix counts ``(w1, *)``
    - n_xi counts ``(*, w2)``
    - n_xx counts ``(*, *)``, i.e. any bigram

    This may be shown with respect to a contingency table::

                w1    ~w1
             ------ ------
         w2 | n_ii | n_oi | = n_xi
             ------ ------
        ~w2 | n_io | n_oo |
             ------ ------
             = n_ix        TOTAL = n_xx
    """

    _n = 2

    @staticmethod
    def _contingency(n_ii, n_ix_xi_tuple, n_xx):
        """Calculates values of a bigram contingency table from marginal values."""
        (n_ix, n_xi) = n_ix_xi_tuple
        n_oi = n_xi - n_ii
        n_io = n_ix - n_ii
        return (n_ii, n_oi, n_io, n_xx - n_ii - n_oi - n_io)

    @staticmethod
    def _marginals(n_ii, n_oi, n_io, n_oo):
        """Calculates values of contingency table marginals from its values."""
        return (n_ii, (n_oi + n_ii, n_io + n_ii), n_oo + n_oi + n_io + n_ii)

    @staticmethod
    def _expected_values(cont):
        """Calculates expected values for a contingency table."""
        n_xx = sum(cont)
        # For each contingency table cell
        for i in range(4):
            yield (cont[i] + cont[i ^ 1]) * (cont[i] + cont[i ^ 2]) / n_xx

    @classmethod
    def phi_sq(cls, *marginals):
        """Scores bigrams using phi-square, the square of the Pearson correlation
        coefficient.
        """
        n_ii, n_io, n_oi, n_oo = cls._contingency(*marginals)

        return (n_ii * n_oo - n_io * n_oi) ** 2 / (
            (n_ii + n_io) * (n_ii + n_oi) * (n_io + n_oo) * (n_oi + n_oo)
        )

    @classmethod
    def chi_sq(cls, n_ii, n_ix_xi_tuple, n_xx):
        """Scores bigrams using chi-square, i.e. phi-sq multiplied by the number
        of bigrams, as in Manning and Schutze 5.3.3.
        """
        (n_ix, n_xi) = n_ix_xi_tuple
        return n_xx * cls.phi_sq(n_ii, (n_ix, n_xi), n_xx)

    @classmethod
    def fisher(cls, *marginals):
        """Scores bigrams using Fisher's Exact Test (Pedersen 1996).  Less
        sensitive to small counts than PMI or Chi Sq, but also more expensive
        to compute. Requires scipy.
        """

        n_ii, n_io, n_oi, n_oo = cls._contingency(*marginals)

        (odds, pvalue) = fisher_exact([[n_ii, n_io], [n_oi, n_oo]], alternative="less")
        return pvalue

    @staticmethod
    def dice(n_ii, n_ix_xi_tuple, n_xx):
        """Scores bigrams using Dice's coefficient."""
        (n_ix, n_xi) = n_ix_xi_tuple
        return 2 * n_ii / (n_ix + n_xi)


class TrigramAssocMeasures(NgramAssocMeasures):
    """
    A collection of trigram association measures. Each association measure
    is provided as a function with four arguments::

        trigram_score_fn(n_iii,
                         (n_iix, n_ixi, n_xii),
                         (n_ixx, n_xix, n_xxi),
                         n_xxx)

    The arguments constitute the marginals of a contingency table, counting
    the occurrences of particular events in a corpus. The letter i in the
    suffix refers to the appearance of the word in question, while x indicates
    the appearance of any word. Thus, for example:

    - n_iii counts ``(w1, w2, w3)``, i.e. the trigram being scored
    - n_ixx counts ``(w1, *, *)``
    - n_xxx counts ``(*, *, *)``, i.e. any trigram
    """

    _n = 3

    @staticmethod
    def _contingency(n_iii, n_iix_tuple, n_ixx_tuple, n_xxx):
        """Calculates values of a trigram contingency table (or cube) from
        marginal values.
        >>> TrigramAssocMeasures._contingency(1, (1, 1, 1), (1, 73, 1), 2000)
        (1, 0, 0, 0, 0, 72, 0, 1927)
        """
        (n_iix, n_ixi, n_xii) = n_iix_tuple
        (n_ixx, n_xix, n_xxi) = n_ixx_tuple
        n_oii = n_xii - n_iii
        n_ioi = n_ixi - n_iii
        n_iio = n_iix - n_iii
        n_ooi = n_xxi - n_iii - n_oii - n_ioi
        n_oio = n_xix - n_iii - n_oii - n_iio
        n_ioo = n_ixx - n_iii - n_ioi - n_iio
        n_ooo = n_xxx - n_iii - n_oii - n_ioi - n_iio - n_ooi - n_oio - n_ioo

        return (n_iii, n_oii, n_ioi, n_ooi, n_iio, n_oio, n_ioo, n_ooo)

    @staticmethod
    def _marginals(*contingency):
        """Calculates values of contingency table marginals from its values.
        >>> TrigramAssocMeasures._marginals(1, 0, 0, 0, 0, 72, 0, 1927)
        (1, (1, 1, 1), (1, 73, 1), 2000)
        """
        n_iii, n_oii, n_ioi, n_ooi, n_iio, n_oio, n_ioo, n_ooo = contingency
        return (
            n_iii,
            (n_iii + n_iio, n_iii + n_ioi, n_iii + n_oii),
            (
                n_iii + n_ioi + n_iio + n_ioo,
                n_iii + n_oii + n_iio + n_oio,
                n_iii + n_oii + n_ioi + n_ooi,
            ),
            sum(contingency),
        )


class QuadgramAssocMeasures(NgramAssocMeasures):
    """
    A collection of quadgram association measures. Each association measure
    is provided as a function with five arguments::

        trigram_score_fn(n_iiii,
                        (n_iiix, n_iixi, n_ixii, n_xiii),
                        (n_iixx, n_ixix, n_ixxi, n_xixi, n_xxii, n_xiix),
                        (n_ixxx, n_xixx, n_xxix, n_xxxi),
                        n_all)

    The arguments constitute the marginals of a contingency table, counting
    the occurrences of particular events in a corpus. The letter i in the
    suffix refers to the appearance of the word in question, while x indicates
    the appearance of any word. Thus, for example:

    - n_iiii counts ``(w1, w2, w3, w4)``, i.e. the quadgram being scored
    - n_ixxi counts ``(w1, *, *, w4)``
    - n_xxxx counts ``(*, *, *, *)``, i.e. any quadgram
    """

    _n = 4

    @staticmethod
    def _contingency(n_iiii, n_iiix_tuple, n_iixx_tuple, n_ixxx_tuple, n_xxxx):
        """Calculates values of a quadgram contingency table from
        marginal values.
        """
        (n_iiix, n_iixi, n_ixii, n_xiii) = n_iiix_tuple
        (n_iixx, n_ixix, n_ixxi, n_xixi, n_xxii, n_xiix) = n_iixx_tuple
        (n_ixxx, n_xixx, n_xxix, n_xxxi) = n_ixxx_tuple
        n_oiii = n_xiii - n_iiii
        n_ioii = n_ixii - n_iiii
        n_iioi = n_iixi - n_iiii
        n_ooii = n_xxii - n_iiii - n_oiii - n_ioii
        n_oioi = n_xixi - n_iiii - n_oiii - n_iioi
        n_iooi = n_ixxi - n_iiii - n_ioii - n_iioi
        n_oooi = n_xxxi - n_iiii - n_oiii - n_ioii - n_iioi - n_ooii - n_iooi - n_oioi
        n_iiio = n_iiix - n_iiii
        n_oiio = n_xiix - n_iiii - n_oiii - n_iiio
        n_ioio = n_ixix - n_iiii - n_ioii - n_iiio
        n_ooio = n_xxix - n_iiii - n_oiii - n_ioii - n_iiio - n_ooii - n_ioio - n_oiio
        n_iioo = n_iixx - n_iiii - n_iioi - n_iiio
        n_oioo = n_xixx - n_iiii - n_oiii - n_iioi - n_iiio - n_oioi - n_oiio - n_iioo
        n_iooo = n_ixxx - n_iiii - n_ioii - n_iioi - n_iiio - n_iooi - n_iioo - n_ioio
        n_oooo = (
            n_xxxx
            - n_iiii
            - n_oiii
            - n_ioii
            - n_iioi
            - n_ooii
            - n_oioi
            - n_iooi
            - n_oooi
            - n_iiio
            - n_oiio
            - n_ioio
            - n_ooio
            - n_iioo
            - n_oioo
            - n_iooo
        )

        return (
            n_iiii,
            n_oiii,
            n_ioii,
            n_ooii,
            n_iioi,
            n_oioi,
            n_iooi,
            n_oooi,
            n_iiio,
            n_oiio,
            n_ioio,
            n_ooio,
            n_iioo,
            n_oioo,
            n_iooo,
            n_oooo,
        )

    @staticmethod
    def _marginals(*contingency):
        """Calculates values of contingency table marginals from its values.
        QuadgramAssocMeasures._marginals(1, 0, 2, 46, 552, 825, 2577, 34967, 1, 0, 2, 48, 7250, 9031, 28585, 356653)
        (1, (2, 553, 3, 1), (7804, 6, 3132, 1378, 49, 2), (38970, 17660, 100, 38970), 440540)
        """
        (
            n_iiii,
            n_oiii,
            n_ioii,
            n_ooii,
            n_iioi,
            n_oioi,
            n_iooi,
            n_oooi,
            n_iiio,
            n_oiio,
            n_ioio,
            n_ooio,
            n_iioo,
            n_oioo,
            n_iooo,
            n_oooo,
        ) = contingency

        n_iiix = n_iiii + n_iiio
        n_iixi = n_iiii + n_iioi
        n_ixii = n_iiii + n_ioii
        n_xiii = n_iiii + n_oiii

        n_iixx = n_iiii + n_iioi + n_iiio + n_iioo
        n_ixix = n_iiii + n_ioii + n_iiio + n_ioio
        n_ixxi = n_iiii + n_ioii + n_iioi + n_iooi
        n_xixi = n_iiii + n_oiii + n_iioi + n_oioi
        n_xxii = n_iiii + n_oiii + n_ioii + n_ooii
        n_xiix = n_iiii + n_oiii + n_iiio + n_oiio

        n_ixxx = n_iiii + n_ioii + n_iioi + n_iiio + n_iooi + n_iioo + n_ioio + n_iooo
        n_xixx = n_iiii + n_oiii + n_iioi + n_iiio + n_oioi + n_oiio + n_iioo + n_oioo
        n_xxix = n_iiii + n_oiii + n_ioii + n_iiio + n_ooii + n_ioio + n_oiio + n_ooio
        n_xxxi = n_iiii + n_oiii + n_ioii + n_iioi + n_ooii + n_iooi + n_oioi + n_oooi

        n_all = sum(contingency)

        return (
            n_iiii,
            (n_iiix, n_iixi, n_ixii, n_xiii),
            (n_iixx, n_ixix, n_ixxi, n_xixi, n_xxii, n_xiix),
            (n_ixxx, n_xixx, n_xxix, n_xxxi),
            n_all,
        )


class ContingencyMeasures:
    """Wraps NgramAssocMeasures classes such that the arguments of association
    measures are contingency table values rather than marginals.
    """

    def __init__(self, measures):
        """Constructs a ContingencyMeasures given a NgramAssocMeasures class"""
        self.__class__.__name__ = "Contingency" + measures.__class__.__name__
        for k in dir(measures):
            if k.startswith("__"):
                continue
            v = getattr(measures, k)
            if not k.startswith("_"):
                v = self._make_contingency_fn(measures, v)
            setattr(self, k, v)

    @staticmethod
    def _make_contingency_fn(measures, old_fn):
        """From an association measure function, produces a new function which
        accepts contingency table values as its arguments.
        """

        def res(*contingency):
            return old_fn(*measures._marginals(*contingency))

        res.__doc__ = old_fn.__doc__
        res.__name__ = old_fn.__name__
        return res

# === NexusCore/openenv\Lib\site-packages\fontTools\designspaceLib\split.py ===
"""Allows building all the variable fonts of a DesignSpace version 5 by
splitting the document into interpolable sub-space, then into each VF.
"""

from __future__ import annotations

import itertools
import logging
import math
from typing import Any, Callable, Dict, Iterator, List, Tuple, cast

from fontTools.designspaceLib import (
    AxisDescriptor,
    AxisMappingDescriptor,
    DesignSpaceDocument,
    DiscreteAxisDescriptor,
    InstanceDescriptor,
    RuleDescriptor,
    SimpleLocationDict,
    SourceDescriptor,
    VariableFontDescriptor,
)
from fontTools.designspaceLib.statNames import StatNames, getStatNames
from fontTools.designspaceLib.types import (
    ConditionSet,
    Range,
    Region,
    getVFUserRegion,
    locationInRegion,
    regionInRegion,
    userRegionToDesignRegion,
)

LOGGER = logging.getLogger(__name__)

MakeInstanceFilenameCallable = Callable[
    [DesignSpaceDocument, InstanceDescriptor, StatNames], str
]


def defaultMakeInstanceFilename(
    doc: DesignSpaceDocument, instance: InstanceDescriptor, statNames: StatNames
) -> str:
    """Default callable to synthesize an instance filename
    when makeNames=True, for instances that don't specify an instance name
    in the designspace. This part of the name generation can be overriden
    because it's not specified by the STAT table.
    """
    familyName = instance.familyName or statNames.familyNames.get("en")
    styleName = instance.styleName or statNames.styleNames.get("en")
    return f"{familyName}-{styleName}.ttf"


def splitInterpolable(
    doc: DesignSpaceDocument,
    makeNames: bool = True,
    expandLocations: bool = True,
    makeInstanceFilename: MakeInstanceFilenameCallable = defaultMakeInstanceFilename,
) -> Iterator[Tuple[SimpleLocationDict, DesignSpaceDocument]]:
    """Split the given DS5 into several interpolable sub-designspaces.
    There are as many interpolable sub-spaces as there are combinations of
    discrete axis values.

    E.g. with axes:
        - italic (discrete) Upright or Italic
        - style (discrete) Sans or Serif
        - weight (continuous) 100 to 900

    There are 4 sub-spaces in which the Weight axis should interpolate:
    (Upright, Sans), (Upright, Serif), (Italic, Sans) and (Italic, Serif).

    The sub-designspaces still include the full axis definitions and STAT data,
    but the rules, sources, variable fonts, instances are trimmed down to only
    keep what falls within the interpolable sub-space.

    Args:
      - ``makeNames``: Whether to compute the instance family and style
        names using the STAT data.
      - ``expandLocations``: Whether to turn all locations into "full"
        locations, including implicit default axis values where missing.
      - ``makeInstanceFilename``: Callable to synthesize an instance filename
        when makeNames=True, for instances that don't specify an instance name
        in the designspace. This part of the name generation can be overridden
        because it's not specified by the STAT table.

    .. versionadded:: 5.0
    """
    discreteAxes = []
    interpolableUserRegion: Region = {}
    for axis in doc.axes:
        if hasattr(axis, "values"):
            # Mypy doesn't support narrowing union types via hasattr()
            # TODO(Python 3.10): use TypeGuard
            # https://mypy.readthedocs.io/en/stable/type_narrowing.html
            axis = cast(DiscreteAxisDescriptor, axis)
            discreteAxes.append(axis)
        else:
            axis = cast(AxisDescriptor, axis)
            interpolableUserRegion[axis.name] = Range(
                axis.minimum,
                axis.maximum,
                axis.default,
            )
    valueCombinations = itertools.product(*[axis.values for axis in discreteAxes])
    for values in valueCombinations:
        discreteUserLocation = {
            discreteAxis.name: value
            for discreteAxis, value in zip(discreteAxes, values)
        }
        subDoc = _extractSubSpace(
            doc,
            {**interpolableUserRegion, **discreteUserLocation},
            keepVFs=True,
            makeNames=makeNames,
            expandLocations=expandLocations,
            makeInstanceFilename=makeInstanceFilename,
        )
        yield discreteUserLocation, subDoc


def splitVariableFonts(
    doc: DesignSpaceDocument,
    makeNames: bool = False,
    expandLocations: bool = False,
    makeInstanceFilename: MakeInstanceFilenameCallable = defaultMakeInstanceFilename,
) -> Iterator[Tuple[str, DesignSpaceDocument]]:
    """Convert each variable font listed in this document into a standalone
    designspace. This can be used to compile all the variable fonts from a
    format 5 designspace using tools that can only deal with 1 VF at a time.

    Args:
      - ``makeNames``: Whether to compute the instance family and style
        names using the STAT data.
      - ``expandLocations``: Whether to turn all locations into "full"
        locations, including implicit default axis values where missing.
      - ``makeInstanceFilename``: Callable to synthesize an instance filename
        when makeNames=True, for instances that don't specify an instance name
        in the designspace. This part of the name generation can be overridden
        because it's not specified by the STAT table.

    .. versionadded:: 5.0
    """
    # Make one DesignspaceDoc v5 for each variable font
    for vf in doc.getVariableFonts():
        vfUserRegion = getVFUserRegion(doc, vf)
        vfDoc = _extractSubSpace(
            doc,
            vfUserRegion,
            keepVFs=False,
            makeNames=makeNames,
            expandLocations=expandLocations,
            makeInstanceFilename=makeInstanceFilename,
        )
        vfDoc.lib = {**vfDoc.lib, **vf.lib}
        yield vf.name, vfDoc


def convert5to4(
    doc: DesignSpaceDocument,
) -> Dict[str, DesignSpaceDocument]:
    """Convert each variable font listed in this document into a standalone
    format 4 designspace. This can be used to compile all the variable fonts
    from a format 5 designspace using tools that only know about format 4.

    .. versionadded:: 5.0
    """
    vfs = {}
    for _location, subDoc in splitInterpolable(doc):
        for vfName, vfDoc in splitVariableFonts(subDoc):
            vfDoc.formatVersion = "4.1"
            vfs[vfName] = vfDoc
    return vfs


def _extractSubSpace(
    doc: DesignSpaceDocument,
    userRegion: Region,
    *,
    keepVFs: bool,
    makeNames: bool,
    expandLocations: bool,
    makeInstanceFilename: MakeInstanceFilenameCallable,
) -> DesignSpaceDocument:
    subDoc = DesignSpaceDocument()
    # Don't include STAT info
    # FIXME: (Jany) let's think about it. Not include = OK because the point of
    # the splitting is to build VFs and we'll use the STAT data of the full
    # document to generate the STAT of the VFs, so "no need" to have STAT data
    # in sub-docs. Counterpoint: what if someone wants to split this DS for
    # other purposes?  Maybe for that it would be useful to also subset the STAT
    # data?
    # subDoc.elidedFallbackName = doc.elidedFallbackName

    def maybeExpandDesignLocation(object):
        if expandLocations:
            return object.getFullDesignLocation(doc)
        else:
            return object.designLocation

    for axis in doc.axes:
        range = userRegion[axis.name]
        if isinstance(range, Range) and hasattr(axis, "minimum"):
            # Mypy doesn't support narrowing union types via hasattr()
            # TODO(Python 3.10): use TypeGuard
            # https://mypy.readthedocs.io/en/stable/type_narrowing.html
            axis = cast(AxisDescriptor, axis)
            subDoc.addAxis(
                AxisDescriptor(
                    # Same info
                    tag=axis.tag,
                    name=axis.name,
                    labelNames=axis.labelNames,
                    hidden=axis.hidden,
                    # Subset range
                    minimum=max(range.minimum, axis.minimum),
                    default=range.default or axis.default,
                    maximum=min(range.maximum, axis.maximum),
                    map=[
                        (user, design)
                        for user, design in axis.map
                        if range.minimum <= user <= range.maximum
                    ],
                    # Don't include STAT info
                    axisOrdering=None,
                    axisLabels=None,
                )
            )

    subDoc.axisMappings = mappings = []
    subDocAxes = {axis.name for axis in subDoc.axes}
    for mapping in doc.axisMappings:
        if not all(axis in subDocAxes for axis in mapping.inputLocation.keys()):
            continue
        if not all(axis in subDocAxes for axis in mapping.outputLocation.keys()):
            LOGGER.error(
                "In axis mapping from input %s, some output axes are not in the variable-font: %s",
                mapping.inputLocation,
                mapping.outputLocation,
            )
            continue

        mappingAxes = set()
        mappingAxes.update(mapping.inputLocation.keys())
        mappingAxes.update(mapping.outputLocation.keys())
        for axis in doc.axes:
            if axis.name not in mappingAxes:
                continue
            range = userRegion[axis.name]
            if (
                range.minimum != axis.minimum
                or (range.default is not None and range.default != axis.default)
                or range.maximum != axis.maximum
            ):
                LOGGER.error(
                    "Limiting axis ranges used in <mapping> elements not supported: %s",
                    axis.name,
                )
                continue

        mappings.append(
            AxisMappingDescriptor(
                inputLocation=mapping.inputLocation,
                outputLocation=mapping.outputLocation,
            )
        )

    # Don't include STAT info
    # subDoc.locationLabels = doc.locationLabels

    # Rules: subset them based on conditions
    designRegion = userRegionToDesignRegion(doc, userRegion)
    subDoc.rules = _subsetRulesBasedOnConditions(doc.rules, designRegion)
    subDoc.rulesProcessingLast = doc.rulesProcessingLast

    # Sources: keep only the ones that fall within the kept axis ranges
    for source in doc.sources:
        if not locationInRegion(doc.map_backward(source.designLocation), userRegion):
            continue

        subDoc.addSource(
            SourceDescriptor(
                filename=source.filename,
                path=source.path,
                font=source.font,
                name=source.name,
                designLocation=_filterLocation(
                    userRegion, maybeExpandDesignLocation(source)
                ),
                layerName=source.layerName,
                familyName=source.familyName,
                styleName=source.styleName,
                muteKerning=source.muteKerning,
                muteInfo=source.muteInfo,
                mutedGlyphNames=source.mutedGlyphNames,
            )
        )

    # Copy family name translations from the old default source to the new default
    vfDefault = subDoc.findDefault()
    oldDefault = doc.findDefault()
    if vfDefault is not None and oldDefault is not None:
        vfDefault.localisedFamilyName = oldDefault.localisedFamilyName

    # Variable fonts: keep only the ones that fall within the kept axis ranges
    if keepVFs:
        # Note: call getVariableFont() to make the implicit VFs explicit
        for vf in doc.getVariableFonts():
            vfUserRegion = getVFUserRegion(doc, vf)
            if regionInRegion(vfUserRegion, userRegion):
                subDoc.addVariableFont(
                    VariableFontDescriptor(
                        name=vf.name,
                        filename=vf.filename,
                        axisSubsets=[
                            axisSubset
                            for axisSubset in vf.axisSubsets
                            if isinstance(userRegion[axisSubset.name], Range)
                        ],
                        lib=vf.lib,
                    )
                )

    # Instances: same as Sources + compute missing names
    for instance in doc.instances:
        if not locationInRegion(instance.getFullUserLocation(doc), userRegion):
            continue

        if makeNames:
            statNames = getStatNames(doc, instance.getFullUserLocation(doc))
            familyName = instance.familyName or statNames.familyNames.get("en")
            styleName = instance.styleName or statNames.styleNames.get("en")
            subDoc.addInstance(
                InstanceDescriptor(
                    filename=instance.filename
                    or makeInstanceFilename(doc, instance, statNames),
                    path=instance.path,
                    font=instance.font,
                    name=instance.name or f"{familyName} {styleName}",
                    userLocation={} if expandLocations else instance.userLocation,
                    designLocation=_filterLocation(
                        userRegion, maybeExpandDesignLocation(instance)
                    ),
                    familyName=familyName,
                    styleName=styleName,
                    postScriptFontName=instance.postScriptFontName
                    or statNames.postScriptFontName,
                    styleMapFamilyName=instance.styleMapFamilyName
                    or statNames.styleMapFamilyNames.get("en"),
                    styleMapStyleName=instance.styleMapStyleName
                    or statNames.styleMapStyleName,
                    localisedFamilyName=instance.localisedFamilyName
                    or statNames.familyNames,
                    localisedStyleName=instance.localisedStyleName
                    or statNames.styleNames,
                    localisedStyleMapFamilyName=instance.localisedStyleMapFamilyName
                    or statNames.styleMapFamilyNames,
                    localisedStyleMapStyleName=instance.localisedStyleMapStyleName
                    or {},
                    lib=instance.lib,
                )
            )
        else:
            subDoc.addInstance(
                InstanceDescriptor(
                    filename=instance.filename,
                    path=instance.path,
                    font=instance.font,
                    name=instance.name,
                    userLocation={} if expandLocations else instance.userLocation,
                    designLocation=_filterLocation(
                        userRegion, maybeExpandDesignLocation(instance)
                    ),
                    familyName=instance.familyName,
                    styleName=instance.styleName,
                    postScriptFontName=instance.postScriptFontName,
                    styleMapFamilyName=instance.styleMapFamilyName,
                    styleMapStyleName=instance.styleMapStyleName,
                    localisedFamilyName=instance.localisedFamilyName,
                    localisedStyleName=instance.localisedStyleName,
                    localisedStyleMapFamilyName=instance.localisedStyleMapFamilyName,
                    localisedStyleMapStyleName=instance.localisedStyleMapStyleName,
                    lib=instance.lib,
                )
            )

    subDoc.lib = doc.lib

    return subDoc


def _conditionSetFrom(conditionSet: List[Dict[str, Any]]) -> ConditionSet:
    c: Dict[str, Range] = {}
    for condition in conditionSet:
        minimum, maximum = condition.get("minimum"), condition.get("maximum")
        c[condition["name"]] = Range(
            minimum if minimum is not None else -math.inf,
            maximum if maximum is not None else math.inf,
        )
    return c


def _subsetRulesBasedOnConditions(
    rules: List[RuleDescriptor], designRegion: Region
) -> List[RuleDescriptor]:
    # What rules to keep:
    #  - Keep the rule if any conditionset is relevant.
    #  - A conditionset is relevant if all conditions are relevant or it is empty.
    #  - A condition is relevant if
    #    - axis is point (C-AP),
    #       - and point in condition's range (C-AP-in)
    #            (in this case remove the condition because it's always true)
    #       - else (C-AP-out) whole conditionset can be discarded (condition false
    #         => conditionset false)
    #    - axis is range (C-AR),
    #       - (C-AR-all) and axis range fully contained in condition range: we can
    #         scrap the condition because it's always true
    #       - (C-AR-inter) and intersection(axis range, condition range) not empty:
    #         keep the condition with the smaller range (= intersection)
    #       - (C-AR-none) else, whole conditionset can be discarded
    newRules: List[RuleDescriptor] = []
    for rule in rules:
        newRule: RuleDescriptor = RuleDescriptor(
            name=rule.name, conditionSets=[], subs=rule.subs
        )
        for conditionset in rule.conditionSets:
            cs = _conditionSetFrom(conditionset)
            newConditionset: List[Dict[str, Any]] = []
            discardConditionset = False
            for selectionName, selectionValue in designRegion.items():
                # TODO: Ensure that all(key in conditionset for key in region.keys())?
                if selectionName not in cs:
                    # raise Exception("Selection has different axes than the rules")
                    continue
                if isinstance(selectionValue, (float, int)):  # is point
                    # Case C-AP-in
                    if selectionValue in cs[selectionName]:
                        pass  # always matches, conditionset can stay empty for this one.
                    # Case C-AP-out
                    else:
                        discardConditionset = True
                else:  # is range
                    # Case C-AR-all
                    if selectionValue in cs[selectionName]:
                        pass  # always matches, conditionset can stay empty for this one.
                    else:
                        intersection = cs[selectionName].intersection(selectionValue)
                        # Case C-AR-inter
                        if intersection is not None:
                            newConditionset.append(
                                {
                                    "name": selectionName,
                                    "minimum": intersection.minimum,
                                    "maximum": intersection.maximum,
                                }
                            )
                        # Case C-AR-none
                        else:
                            discardConditionset = True
            if not discardConditionset:
                newRule.conditionSets.append(newConditionset)
        if newRule.conditionSets:
            newRules.append(newRule)

    return newRules


def _filterLocation(
    userRegion: Region,
    location: Dict[str, float],
) -> Dict[str, float]:
    return {
        name: value
        for name, value in location.items()
        if name in userRegion and isinstance(userRegion[name], Range)
    }

# === NexusCore/openenv\Lib\site-packages\fontTools\pens\basePen.py ===
"""fontTools.pens.basePen.py -- Tools and base classes to build pen objects.

The Pen Protocol

A Pen is a kind of object that standardizes the way how to "draw" outlines:
it is a middle man between an outline and a drawing. In other words:
it is an abstraction for drawing outlines, making sure that outline objects
don't need to know the details about how and where they're being drawn, and
that drawings don't need to know the details of how outlines are stored.

The most basic pattern is this::

	outline.draw(pen)  # 'outline' draws itself onto 'pen'

Pens can be used to render outlines to the screen, but also to construct
new outlines. Eg. an outline object can be both a drawable object (it has a
draw() method) as well as a pen itself: you *build* an outline using pen
methods.

The AbstractPen class defines the Pen protocol. It implements almost
nothing (only no-op closePath() and endPath() methods), but is useful
for documentation purposes. Subclassing it basically tells the reader:
"this class implements the Pen protocol.". An examples of an AbstractPen
subclass is :py:class:`fontTools.pens.transformPen.TransformPen`.

The BasePen class is a base implementation useful for pens that actually
draw (for example a pen renders outlines using a native graphics engine).
BasePen contains a lot of base functionality, making it very easy to build
a pen that fully conforms to the pen protocol. Note that if you subclass
BasePen, you *don't* override moveTo(), lineTo(), etc., but _moveTo(),
_lineTo(), etc. See the BasePen doc string for details. Examples of
BasePen subclasses are fontTools.pens.boundsPen.BoundsPen and
fontTools.pens.cocoaPen.CocoaPen.

Coordinates are usually expressed as (x, y) tuples, but generally any
sequence of length 2 will do.
"""

from typing import Tuple, Dict

from fontTools.misc.loggingTools import LogMixin
from fontTools.misc.transform import DecomposedTransform, Identity

__all__ = [
    "AbstractPen",
    "NullPen",
    "BasePen",
    "PenError",
    "decomposeSuperBezierSegment",
    "decomposeQuadraticSegment",
]


class PenError(Exception):
    """Represents an error during penning."""


class OpenContourError(PenError):
    pass


class AbstractPen:
    def moveTo(self, pt: Tuple[float, float]) -> None:
        """Begin a new sub path, set the current point to 'pt'. You must
        end each sub path with a call to pen.closePath() or pen.endPath().
        """
        raise NotImplementedError

    def lineTo(self, pt: Tuple[float, float]) -> None:
        """Draw a straight line from the current point to 'pt'."""
        raise NotImplementedError

    def curveTo(self, *points: Tuple[float, float]) -> None:
        """Draw a cubic bezier with an arbitrary number of control points.

        The last point specified is on-curve, all others are off-curve
        (control) points. If the number of control points is > 2, the
        segment is split into multiple bezier segments. This works
        like this:

        Let n be the number of control points (which is the number of
        arguments to this call minus 1). If n==2, a plain vanilla cubic
        bezier is drawn. If n==1, we fall back to a quadratic segment and
        if n==0 we draw a straight line. It gets interesting when n>2:
        n-1 PostScript-style cubic segments will be drawn as if it were
        one curve. See decomposeSuperBezierSegment().

        The conversion algorithm used for n>2 is inspired by NURB
        splines, and is conceptually equivalent to the TrueType "implied
        points" principle. See also decomposeQuadraticSegment().
        """
        raise NotImplementedError

    def qCurveTo(self, *points: Tuple[float, float]) -> None:
        """Draw a whole string of quadratic curve segments.

        The last point specified is on-curve, all others are off-curve
        points.

        This method implements TrueType-style curves, breaking up curves
        using 'implied points': between each two consequtive off-curve points,
        there is one implied point exactly in the middle between them. See
        also decomposeQuadraticSegment().

        The last argument (normally the on-curve point) may be None.
        This is to support contours that have NO on-curve points (a rarely
        seen feature of TrueType outlines).
        """
        raise NotImplementedError

    def closePath(self) -> None:
        """Close the current sub path. You must call either pen.closePath()
        or pen.endPath() after each sub path.
        """
        pass

    def endPath(self) -> None:
        """End the current sub path, but don't close it. You must call
        either pen.closePath() or pen.endPath() after each sub path.
        """
        pass

    def addComponent(
        self,
        glyphName: str,
        transformation: Tuple[float, float, float, float, float, float],
    ) -> None:
        """Add a sub glyph. The 'transformation' argument must be a 6-tuple
        containing an affine transformation, or a Transform object from the
        fontTools.misc.transform module. More precisely: it should be a
        sequence containing 6 numbers.
        """
        raise NotImplementedError

    def addVarComponent(
        self,
        glyphName: str,
        transformation: DecomposedTransform,
        location: Dict[str, float],
    ) -> None:
        """Add a VarComponent sub glyph. The 'transformation' argument
        must be a DecomposedTransform from the fontTools.misc.transform module,
        and the 'location' argument must be a dictionary mapping axis tags
        to their locations.
        """
        # GlyphSet decomposes for us
        raise AttributeError


class NullPen(AbstractPen):
    """A pen that does nothing."""

    def moveTo(self, pt):
        pass

    def lineTo(self, pt):
        pass

    def curveTo(self, *points):
        pass

    def qCurveTo(self, *points):
        pass

    def closePath(self):
        pass

    def endPath(self):
        pass

    def addComponent(self, glyphName, transformation):
        pass

    def addVarComponent(self, glyphName, transformation, location):
        pass


class LoggingPen(LogMixin, AbstractPen):
    """A pen with a ``log`` property (see fontTools.misc.loggingTools.LogMixin)"""

    pass


class MissingComponentError(KeyError):
    """Indicates a component pointing to a non-existent glyph in the glyphset."""


class DecomposingPen(LoggingPen):
    """Implements a 'addComponent' method that decomposes components
    (i.e. draws them onto self as simple contours).
    It can also be used as a mixin class (e.g. see ContourRecordingPen).

    You must override moveTo, lineTo, curveTo and qCurveTo. You may
    additionally override closePath, endPath and addComponent.

    By default a warning message is logged when a base glyph is missing;
    set the class variable ``skipMissingComponents`` to False if you want
    all instances of a sub-class to raise a :class:`MissingComponentError`
    exception by default.
    """

    skipMissingComponents = True
    # alias error for convenience
    MissingComponentError = MissingComponentError

    def __init__(
        self,
        glyphSet,
        *args,
        skipMissingComponents=None,
        reverseFlipped=False,
        **kwargs,
    ):
        """Takes a 'glyphSet' argument (dict), in which the glyphs that are referenced
        as components are looked up by their name.

        If the optional 'reverseFlipped' argument is True, components whose transformation
        matrix has a negative determinant will be decomposed with a reversed path direction
        to compensate for the flip.

        The optional 'skipMissingComponents' argument can be set to True/False to
        override the homonymous class attribute for a given pen instance.
        """
        super(DecomposingPen, self).__init__(*args, **kwargs)
        self.glyphSet = glyphSet
        self.skipMissingComponents = (
            self.__class__.skipMissingComponents
            if skipMissingComponents is None
            else skipMissingComponents
        )
        self.reverseFlipped = reverseFlipped

    def addComponent(self, glyphName, transformation):
        """Transform the points of the base glyph and draw it onto self."""
        from fontTools.pens.transformPen import TransformPen

        try:
            glyph = self.glyphSet[glyphName]
        except KeyError:
            if not self.skipMissingComponents:
                raise MissingComponentError(glyphName)
            self.log.warning("glyph '%s' is missing from glyphSet; skipped" % glyphName)
        else:
            pen = self
            if transformation != Identity:
                pen = TransformPen(pen, transformation)
            if self.reverseFlipped:
                # if the transformation has a negative determinant, it will
                # reverse the contour direction of the component
                a, b, c, d = transformation[:4]
                det = a * d - b * c
                if det < 0:
                    from fontTools.pens.reverseContourPen import ReverseContourPen

                    pen = ReverseContourPen(pen)
            glyph.draw(pen)

    def addVarComponent(self, glyphName, transformation, location):
        # GlyphSet decomposes for us
        raise AttributeError


class BasePen(DecomposingPen):
    """Base class for drawing pens. You must override _moveTo, _lineTo and
    _curveToOne. You may additionally override _closePath, _endPath,
    addComponent, addVarComponent, and/or _qCurveToOne. You should not
    override any other methods.
    """

    def __init__(self, glyphSet=None):
        super(BasePen, self).__init__(glyphSet)
        self.__currentPoint = None

    # must override

    def _moveTo(self, pt):
        raise NotImplementedError

    def _lineTo(self, pt):
        raise NotImplementedError

    def _curveToOne(self, pt1, pt2, pt3):
        raise NotImplementedError

    # may override

    def _closePath(self):
        pass

    def _endPath(self):
        pass

    def _qCurveToOne(self, pt1, pt2):
        """This method implements the basic quadratic curve type. The
        default implementation delegates the work to the cubic curve
        function. Optionally override with a native implementation.
        """
        pt0x, pt0y = self.__currentPoint
        pt1x, pt1y = pt1
        pt2x, pt2y = pt2
        mid1x = pt0x + 0.66666666666666667 * (pt1x - pt0x)
        mid1y = pt0y + 0.66666666666666667 * (pt1y - pt0y)
        mid2x = pt2x + 0.66666666666666667 * (pt1x - pt2x)
        mid2y = pt2y + 0.66666666666666667 * (pt1y - pt2y)
        self._curveToOne((mid1x, mid1y), (mid2x, mid2y), pt2)

    # don't override

    def _getCurrentPoint(self):
        """Return the current point. This is not part of the public
        interface, yet is useful for subclasses.
        """
        return self.__currentPoint

    def closePath(self):
        self._closePath()
        self.__currentPoint = None

    def endPath(self):
        self._endPath()
        self.__currentPoint = None

    def moveTo(self, pt):
        self._moveTo(pt)
        self.__currentPoint = pt

    def lineTo(self, pt):
        self._lineTo(pt)
        self.__currentPoint = pt

    def curveTo(self, *points):
        n = len(points) - 1  # 'n' is the number of control points
        assert n >= 0
        if n == 2:
            # The common case, we have exactly two BCP's, so this is a standard
            # cubic bezier. Even though decomposeSuperBezierSegment() handles
            # this case just fine, we special-case it anyway since it's so
            # common.
            self._curveToOne(*points)
            self.__currentPoint = points[-1]
        elif n > 2:
            # n is the number of control points; split curve into n-1 cubic
            # bezier segments. The algorithm used here is inspired by NURB
            # splines and the TrueType "implied point" principle, and ensures
            # the smoothest possible connection between two curve segments,
            # with no disruption in the curvature. It is practical since it
            # allows one to construct multiple bezier segments with a much
            # smaller amount of points.
            _curveToOne = self._curveToOne
            for pt1, pt2, pt3 in decomposeSuperBezierSegment(points):
                _curveToOne(pt1, pt2, pt3)
                self.__currentPoint = pt3
        elif n == 1:
            self.qCurveTo(*points)
        elif n == 0:
            self.lineTo(points[0])
        else:
            raise AssertionError("can't get there from here")

    def qCurveTo(self, *points):
        n = len(points) - 1  # 'n' is the number of control points
        assert n >= 0
        if points[-1] is None:
            # Special case for TrueType quadratics: it is possible to
            # define a contour with NO on-curve points. BasePen supports
            # this by allowing the final argument (the expected on-curve
            # point) to be None. We simulate the feature by making the implied
            # on-curve point between the last and the first off-curve points
            # explicit.
            x, y = points[-2]  # last off-curve point
            nx, ny = points[0]  # first off-curve point
            impliedStartPoint = (0.5 * (x + nx), 0.5 * (y + ny))
            self.__currentPoint = impliedStartPoint
            self._moveTo(impliedStartPoint)
            points = points[:-1] + (impliedStartPoint,)
        if n > 0:
            # Split the string of points into discrete quadratic curve
            # segments. Between any two consecutive off-curve points
            # there's an implied on-curve point exactly in the middle.
            # This is where the segment splits.
            _qCurveToOne = self._qCurveToOne
            for pt1, pt2 in decomposeQuadraticSegment(points):
                _qCurveToOne(pt1, pt2)
                self.__currentPoint = pt2
        else:
            self.lineTo(points[0])


def decomposeSuperBezierSegment(points):
    """Split the SuperBezier described by 'points' into a list of regular
    bezier segments. The 'points' argument must be a sequence with length
    3 or greater, containing (x, y) coordinates. The last point is the
    destination on-curve point, the rest of the points are off-curve points.
    The start point should not be supplied.

    This function returns a list of (pt1, pt2, pt3) tuples, which each
    specify a regular curveto-style bezier segment.
    """
    n = len(points) - 1
    assert n > 1
    bezierSegments = []
    pt1, pt2, pt3 = points[0], None, None
    for i in range(2, n + 1):
        # calculate points in between control points.
        nDivisions = min(i, 3, n - i + 2)
        for j in range(1, nDivisions):
            factor = j / nDivisions
            temp1 = points[i - 1]
            temp2 = points[i - 2]
            temp = (
                temp2[0] + factor * (temp1[0] - temp2[0]),
                temp2[1] + factor * (temp1[1] - temp2[1]),
            )
            if pt2 is None:
                pt2 = temp
            else:
                pt3 = (0.5 * (pt2[0] + temp[0]), 0.5 * (pt2[1] + temp[1]))
                bezierSegments.append((pt1, pt2, pt3))
                pt1, pt2, pt3 = temp, None, None
    bezierSegments.append((pt1, points[-2], points[-1]))
    return bezierSegments


def decomposeQuadraticSegment(points):
    """Split the quadratic curve segment described by 'points' into a list
    of "atomic" quadratic segments. The 'points' argument must be a sequence
    with length 2 or greater, containing (x, y) coordinates. The last point
    is the destination on-curve point, the rest of the points are off-curve
    points. The start point should not be supplied.

    This function returns a list of (pt1, pt2) tuples, which each specify a
    plain quadratic bezier segment.
    """
    n = len(points) - 1
    assert n > 0
    quadSegments = []
    for i in range(n - 1):
        x, y = points[i]
        nx, ny = points[i + 1]
        impliedPt = (0.5 * (x + nx), 0.5 * (y + ny))
        quadSegments.append((points[i], impliedPt))
    quadSegments.append((points[-2], points[-1]))
    return quadSegments


class _TestPen(BasePen):
    """Test class that prints PostScript to stdout."""

    def _moveTo(self, pt):
        print("%s %s moveto" % (pt[0], pt[1]))

    def _lineTo(self, pt):
        print("%s %s lineto" % (pt[0], pt[1]))

    def _curveToOne(self, bcp1, bcp2, pt):
        print(
            "%s %s %s %s %s %s curveto"
            % (bcp1[0], bcp1[1], bcp2[0], bcp2[1], pt[0], pt[1])
        )

    def _closePath(self):
        print("closepath")


if __name__ == "__main__":
    pen = _TestPen(None)
    pen.moveTo((0, 0))
    pen.lineTo((0, 100))
    pen.curveTo((50, 75), (60, 50), (50, 25), (0, 0))
    pen.closePath()

    pen = _TestPen(None)
    # testing the "no on-curve point" scenario
    pen.qCurveTo((0, 0), (0, 100), (100, 100), (100, 0), None)
    pen.closePath()

# === NexusCore/openenv\Lib\site-packages\aiohttp\client_middleware_digest_auth.py ===
"""
Digest authentication middleware for aiohttp client.

This middleware implements HTTP Digest Authentication according to RFC 7616,
providing a more secure alternative to Basic Authentication. It supports all
standard hash algorithms including MD5, SHA, SHA-256, SHA-512 and their session
variants, as well as both 'auth' and 'auth-int' quality of protection (qop) options.
"""

import hashlib
import os
import re
import time
from typing import (
    Callable,
    Dict,
    Final,
    FrozenSet,
    List,
    Literal,
    Tuple,
    TypedDict,
    Union,
)

from yarl import URL

from . import hdrs
from .client_exceptions import ClientError
from .client_middlewares import ClientHandlerType
from .client_reqrep import ClientRequest, ClientResponse
from .payload import Payload


class DigestAuthChallenge(TypedDict, total=False):
    realm: str
    nonce: str
    qop: str
    algorithm: str
    opaque: str
    domain: str
    stale: str


DigestFunctions: Dict[str, Callable[[bytes], "hashlib._Hash"]] = {
    "MD5": hashlib.md5,
    "MD5-SESS": hashlib.md5,
    "SHA": hashlib.sha1,
    "SHA-SESS": hashlib.sha1,
    "SHA256": hashlib.sha256,
    "SHA256-SESS": hashlib.sha256,
    "SHA-256": hashlib.sha256,
    "SHA-256-SESS": hashlib.sha256,
    "SHA512": hashlib.sha512,
    "SHA512-SESS": hashlib.sha512,
    "SHA-512": hashlib.sha512,
    "SHA-512-SESS": hashlib.sha512,
}


# Compile the regex pattern once at module level for performance
_HEADER_PAIRS_PATTERN = re.compile(
    r'(\w+)\s*=\s*(?:"((?:[^"\\]|\\.)*)"|([^\s,]+))'
    # |    |  | | |  |    |      |    |  ||     |
    # +----|--|-|-|--|----|------|----|--||-----|--> alphanumeric key
    #      +--|-|-|--|----|------|----|--||-----|--> maybe whitespace
    #         | | |  |    |      |    |  ||     |
    #         +-|-|--|----|------|----|--||-----|--> = (delimiter)
    #           +-|--|----|------|----|--||-----|--> maybe whitespace
    #             |  |    |      |    |  ||     |
    #             +--|----|------|----|--||-----|--> group quoted or unquoted
    #                |    |      |    |  ||     |
    #                +----|------|----|--||-----|--> if quoted...
    #                     +------|----|--||-----|--> anything but " or \
    #                            +----|--||-----|--> escaped characters allowed
    #                                 +--||-----|--> or can be empty string
    #                                    ||     |
    #                                    +|-----|--> if unquoted...
    #                                     +-----|--> anything but , or <space>
    #                                           +--> at least one char req'd
)


# RFC 7616: Challenge parameters to extract
CHALLENGE_FIELDS: Final[
    Tuple[
        Literal["realm", "nonce", "qop", "algorithm", "opaque", "domain", "stale"], ...
    ]
] = (
    "realm",
    "nonce",
    "qop",
    "algorithm",
    "opaque",
    "domain",
    "stale",
)

# Supported digest authentication algorithms
# Use a tuple of sorted keys for predictable documentation and error messages
SUPPORTED_ALGORITHMS: Final[Tuple[str, ...]] = tuple(sorted(DigestFunctions.keys()))

# RFC 7616: Fields that require quoting in the Digest auth header
# These fields must be enclosed in double quotes in the Authorization header.
# Algorithm, qop, and nc are never quoted per RFC specifications.
# This frozen set is used by the template-based header construction to
# automatically determine which fields need quotes.
QUOTED_AUTH_FIELDS: Final[FrozenSet[str]] = frozenset(
    {"username", "realm", "nonce", "uri", "response", "opaque", "cnonce"}
)


def escape_quotes(value: str) -> str:
    """Escape double quotes for HTTP header values."""
    return value.replace('"', '\\"')


def unescape_quotes(value: str) -> str:
    """Unescape double quotes in HTTP header values."""
    return value.replace('\\"', '"')


def parse_header_pairs(header: str) -> Dict[str, str]:
    """
    Parse key-value pairs from WWW-Authenticate or similar HTTP headers.

    This function handles the complex format of WWW-Authenticate header values,
    supporting both quoted and unquoted values, proper handling of commas in
    quoted values, and whitespace variations per RFC 7616.

    Examples of supported formats:
      - key1="value1", key2=value2
      - key1 = "value1" , key2="value, with, commas"
      - key1=value1,key2="value2"
      - realm="example.com", nonce="12345", qop="auth"

    Args:
        header: The header value string to parse

    Returns:
        Dictionary mapping parameter names to their values
    """
    return {
        stripped_key: unescape_quotes(quoted_val) if quoted_val else unquoted_val
        for key, quoted_val, unquoted_val in _HEADER_PAIRS_PATTERN.findall(header)
        if (stripped_key := key.strip())
    }


class DigestAuthMiddleware:
    """
    HTTP digest authentication middleware for aiohttp client.

    This middleware intercepts 401 Unauthorized responses containing a Digest
    authentication challenge, calculates the appropriate digest credentials,
    and automatically retries the request with the proper Authorization header.

    Features:
    - Handles all aspects of Digest authentication handshake automatically
    - Supports all standard hash algorithms:
      - MD5, MD5-SESS
      - SHA, SHA-SESS
      - SHA256, SHA256-SESS, SHA-256, SHA-256-SESS
      - SHA512, SHA512-SESS, SHA-512, SHA-512-SESS
    - Supports 'auth' and 'auth-int' quality of protection modes
    - Properly handles quoted strings and parameter parsing
    - Includes replay attack protection with client nonce count tracking
    - Supports preemptive authentication per RFC 7616 Section 3.6

    Standards compliance:
    - RFC 7616: HTTP Digest Access Authentication (primary reference)
    - RFC 2617: HTTP Authentication (deprecated by RFC 7616)
    - RFC 1945: Section 11.1 (username restrictions)

    Implementation notes:
    The core digest calculation is inspired by the implementation in
    https://github.com/requests/requests/blob/v2.18.4/requests/auth.py
    with added support for modern digest auth features and error handling.
    """

    def __init__(
        self,
        login: str,
        password: str,
        preemptive: bool = True,
    ) -> None:
        if login is None:
            raise ValueError("None is not allowed as login value")

        if password is None:
            raise ValueError("None is not allowed as password value")

        if ":" in login:
            raise ValueError('A ":" is not allowed in username (RFC 1945#section-11.1)')

        self._login_str: Final[str] = login
        self._login_bytes: Final[bytes] = login.encode("utf-8")
        self._password_bytes: Final[bytes] = password.encode("utf-8")

        self._last_nonce_bytes = b""
        self._nonce_count = 0
        self._challenge: DigestAuthChallenge = {}
        self._preemptive: bool = preemptive
        # Set of URLs defining the protection space
        self._protection_space: List[str] = []

    async def _encode(
        self, method: str, url: URL, body: Union[Payload, Literal[b""]]
    ) -> str:
        """
        Build digest authorization header for the current challenge.

        Args:
            method: The HTTP method (GET, POST, etc.)
            url: The request URL
            body: The request body (used for qop=auth-int)

        Returns:
            A fully formatted Digest authorization header string

        Raises:
            ClientError: If the challenge is missing required parameters or
                         contains unsupported values

        """
        challenge = self._challenge
        if "realm" not in challenge:
            raise ClientError(
                "Malformed Digest auth challenge: Missing 'realm' parameter"
            )

        if "nonce" not in challenge:
            raise ClientError(
                "Malformed Digest auth challenge: Missing 'nonce' parameter"
            )

        # Empty realm values are allowed per RFC 7616 (SHOULD, not MUST, contain host name)
        realm = challenge["realm"]
        nonce = challenge["nonce"]

        # Empty nonce values are not allowed as they are security-critical for replay protection
        if not nonce:
            raise ClientError(
                "Security issue: Digest auth challenge contains empty 'nonce' value"
            )

        qop_raw = challenge.get("qop", "")
        algorithm = challenge.get("algorithm", "MD5").upper()
        opaque = challenge.get("opaque", "")

        # Convert string values to bytes once
        nonce_bytes = nonce.encode("utf-8")
        realm_bytes = realm.encode("utf-8")
        path = URL(url).path_qs

        # Process QoP
        qop = ""
        qop_bytes = b""
        if qop_raw:
            valid_qops = {"auth", "auth-int"}.intersection(
                {q.strip() for q in qop_raw.split(",") if q.strip()}
            )
            if not valid_qops:
                raise ClientError(
                    f"Digest auth error: Unsupported Quality of Protection (qop) value(s): {qop_raw}"
                )

            qop = "auth-int" if "auth-int" in valid_qops else "auth"
            qop_bytes = qop.encode("utf-8")

        if algorithm not in DigestFunctions:
            raise ClientError(
                f"Digest auth error: Unsupported hash algorithm: {algorithm}. "
                f"Supported algorithms: {', '.join(SUPPORTED_ALGORITHMS)}"
            )
        hash_fn: Final = DigestFunctions[algorithm]

        def H(x: bytes) -> bytes:
            """RFC 7616 Section 3: Hash function H(data) = hex(hash(data))."""
            return hash_fn(x).hexdigest().encode()

        def KD(s: bytes, d: bytes) -> bytes:
            """RFC 7616 Section 3: KD(secret, data) = H(concat(secret, ":", data))."""
            return H(b":".join((s, d)))

        # Calculate A1 and A2
        A1 = b":".join((self._login_bytes, realm_bytes, self._password_bytes))
        A2 = f"{method.upper()}:{path}".encode()
        if qop == "auth-int":
            if isinstance(body, Payload):  # will always be empty bytes unless Payload
                entity_bytes = await body.as_bytes()  # Get bytes from Payload
            else:
                entity_bytes = body
            entity_hash = H(entity_bytes)
            A2 = b":".join((A2, entity_hash))

        HA1 = H(A1)
        HA2 = H(A2)

        # Nonce count handling
        if nonce_bytes == self._last_nonce_bytes:
            self._nonce_count += 1
        else:
            self._nonce_count = 1

        self._last_nonce_bytes = nonce_bytes
        ncvalue = f"{self._nonce_count:08x}"
        ncvalue_bytes = ncvalue.encode("utf-8")

        # Generate client nonce
        cnonce = hashlib.sha1(
            b"".join(
                [
                    str(self._nonce_count).encode("utf-8"),
                    nonce_bytes,
                    time.ctime().encode("utf-8"),
                    os.urandom(8),
                ]
            )
        ).hexdigest()[:16]
        cnonce_bytes = cnonce.encode("utf-8")

        # Special handling for session-based algorithms
        if algorithm.upper().endswith("-SESS"):
            HA1 = H(b":".join((HA1, nonce_bytes, cnonce_bytes)))

        # Calculate the response digest
        if qop:
            noncebit = b":".join(
                (nonce_bytes, ncvalue_bytes, cnonce_bytes, qop_bytes, HA2)
            )
            response_digest = KD(HA1, noncebit)
        else:
            response_digest = KD(HA1, b":".join((nonce_bytes, HA2)))

        # Define a dict mapping of header fields to their values
        # Group fields into always-present, optional, and qop-dependent
        header_fields = {
            # Always present fields
            "username": escape_quotes(self._login_str),
            "realm": escape_quotes(realm),
            "nonce": escape_quotes(nonce),
            "uri": path,
            "response": response_digest.decode(),
            "algorithm": algorithm,
        }

        # Optional fields
        if opaque:
            header_fields["opaque"] = escape_quotes(opaque)

        # QoP-dependent fields
        if qop:
            header_fields["qop"] = qop
            header_fields["nc"] = ncvalue
            header_fields["cnonce"] = cnonce

        # Build header using templates for each field type
        pairs: List[str] = []
        for field, value in header_fields.items():
            if field in QUOTED_AUTH_FIELDS:
                pairs.append(f'{field}="{value}"')
            else:
                pairs.append(f"{field}={value}")

        return f"Digest {', '.join(pairs)}"

    def _in_protection_space(self, url: URL) -> bool:
        """
        Check if the given URL is within the current protection space.

        According to RFC 7616, a URI is in the protection space if any URI
        in the protection space is a prefix of it (after both have been made absolute).
        """
        request_str = str(url)
        for space_str in self._protection_space:
            # Check if request starts with space URL
            if not request_str.startswith(space_str):
                continue
            # Exact match or space ends with / (proper directory prefix)
            if len(request_str) == len(space_str) or space_str[-1] == "/":
                return True
            # Check next char is / to ensure proper path boundary
            if request_str[len(space_str)] == "/":
                return True
        return False

    def _authenticate(self, response: ClientResponse) -> bool:
        """
        Takes the given response and tries digest-auth, if needed.

        Returns true if the original request must be resent.
        """
        if response.status != 401:
            return False

        auth_header = response.headers.get("www-authenticate", "")
        if not auth_header:
            return False  # No authentication header present

        method, sep, headers = auth_header.partition(" ")
        if not sep:
            # No space found in www-authenticate header
            return False  # Malformed auth header, missing scheme separator

        if method.lower() != "digest":
            # Not a digest auth challenge (could be Basic, Bearer, etc.)
            return False

        if not headers:
            # We have a digest scheme but no parameters
            return False  # Malformed digest header, missing parameters

        # We have a digest auth header with content
        if not (header_pairs := parse_header_pairs(headers)):
            # Failed to parse any key-value pairs
            return False  # Malformed digest header, no valid parameters

        # Extract challenge parameters
        self._challenge = {}
        for field in CHALLENGE_FIELDS:
            if value := header_pairs.get(field):
                self._challenge[field] = value

        # Update protection space based on domain parameter or default to origin
        origin = response.url.origin()

        if domain := self._challenge.get("domain"):
            # Parse space-separated list of URIs
            self._protection_space = []
            for uri in domain.split():
                # Remove quotes if present
                uri = uri.strip('"')
                if uri.startswith("/"):
                    # Path-absolute, relative to origin
                    self._protection_space.append(str(origin.join(URL(uri))))
                else:
                    # Absolute URI
                    self._protection_space.append(str(URL(uri)))
        else:
            # No domain specified, protection space is entire origin
            self._protection_space = [str(origin)]

        # Return True only if we found at least one challenge parameter
        return bool(self._challenge)

    async def __call__(
        self, request: ClientRequest, handler: ClientHandlerType
    ) -> ClientResponse:
        """Run the digest auth middleware."""
        response = None
        for retry_count in range(2):
            # Apply authorization header if:
            # 1. This is a retry after 401 (retry_count > 0), OR
            # 2. Preemptive auth is enabled AND we have a challenge AND the URL is in protection space
            if retry_count > 0 or (
                self._preemptive
                and self._challenge
                and self._in_protection_space(request.url)
            ):
                request.headers[hdrs.AUTHORIZATION] = await self._encode(
                    request.method, request.url, request.body
                )

            # Send the request
            response = await handler(request)

            # Check if we need to authenticate
            if not self._authenticate(response):
                break

        # At this point, response is guaranteed to be defined
        assert response is not None
        return response

# === NexusCore/openenv\Lib\site-packages\huggingface_hub\commands\delete_cache.py ===
# coding=utf-8
# Copyright 2022-present, the HuggingFace Inc. team.
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
"""Contains command to delete some revisions from the HF cache directory.

Usage:
    huggingface-cli delete-cache
    huggingface-cli delete-cache --disable-tui
    huggingface-cli delete-cache --dir ~/.cache/huggingface/hub
    huggingface-cli delete-cache --sort=size

NOTE:
    This command is based on `InquirerPy` to build the multiselect menu in the terminal.
    This dependency has to be installed with `pip install huggingface_hub[cli]`. Since
    we want to avoid as much as possible cross-platform issues, I chose a library that
    is built on top of `python-prompt-toolkit` which seems to be a reference in terminal
    GUI (actively maintained on both Unix and Windows, 7.9k stars).

    For the moment, the TUI feature is in beta.

    See:
    - https://github.com/kazhala/InquirerPy
    - https://inquirerpy.readthedocs.io/en/latest/
    - https://github.com/prompt-toolkit/python-prompt-toolkit

    Other solutions could have been:
    - `simple_term_menu`: would be good as well for our use case but some issues suggest
      that Windows is less supported.
      See: https://github.com/IngoMeyer441/simple-term-menu
    - `PyInquirer`: very similar to `InquirerPy` but older and not maintained anymore.
      In particular, no support of Python3.10.
      See: https://github.com/CITGuru/PyInquirer
    - `pick` (or `pickpack`): easy to use and flexible but built on top of Python's
      standard library `curses` that is specific to Unix (not implemented on Windows).
      See https://github.com/wong2/pick and https://github.com/anafvana/pickpack.
    - `inquirer`: lot of traction (700 stars) but explicitly states "experimental
      support of Windows". Not built on top of `python-prompt-toolkit`.
      See https://github.com/magmax/python-inquirer

TODO: add support for `huggingface-cli delete-cache aaaaaa bbbbbb cccccc (...)` ?
TODO: add "--keep-last" arg to delete revisions that are not on `main` ref
TODO: add "--filter" arg to filter repositories by name ?
TODO: add "--limit" arg to limit to X repos ?
TODO: add "-y" arg for immediate deletion ?
See discussions in https://github.com/huggingface/huggingface_hub/issues/1025.
"""

import os
from argparse import Namespace, _SubParsersAction
from functools import wraps
from tempfile import mkstemp
from typing import Any, Callable, Iterable, List, Literal, Optional, Union

from ..utils import CachedRepoInfo, CachedRevisionInfo, HFCacheInfo, scan_cache_dir
from . import BaseHuggingfaceCLICommand
from ._cli_utils import ANSI


try:
    from InquirerPy import inquirer
    from InquirerPy.base.control import Choice
    from InquirerPy.separator import Separator

    _inquirer_py_available = True
except ImportError:
    _inquirer_py_available = False

SortingOption_T = Literal["alphabetical", "lastUpdated", "lastUsed", "size"]


def require_inquirer_py(fn: Callable) -> Callable:
    """Decorator to flag methods that require `InquirerPy`."""

    # TODO: refactor this + imports in a unified pattern across codebase
    @wraps(fn)
    def _inner(*args, **kwargs):
        if not _inquirer_py_available:
            raise ImportError(
                "The `delete-cache` command requires extra dependencies to work with"
                " the TUI.\nPlease run `pip install huggingface_hub[cli]` to install"
                " them.\nOtherwise, disable TUI using the `--disable-tui` flag."
            )

        return fn(*args, **kwargs)

    return _inner


# Possibility for the user to cancel deletion
_CANCEL_DELETION_STR = "CANCEL_DELETION"


class DeleteCacheCommand(BaseHuggingfaceCLICommand):
    @staticmethod
    def register_subcommand(parser: _SubParsersAction):
        delete_cache_parser = parser.add_parser("delete-cache", help="Delete revisions from the cache directory.")

        delete_cache_parser.add_argument(
            "--dir",
            type=str,
            default=None,
            help="cache directory (optional). Default to the default HuggingFace cache.",
        )

        delete_cache_parser.add_argument(
            "--disable-tui",
            action="store_true",
            help=(
                "Disable Terminal User Interface (TUI) mode. Useful if your"
                " platform/terminal doesn't support the multiselect menu."
            ),
        )

        delete_cache_parser.add_argument(
            "--sort",
            nargs="?",
            choices=["alphabetical", "lastUpdated", "lastUsed", "size"],
            help=(
                "Sort repositories by the specified criteria. Options: "
                "'alphabetical' (A-Z), "
                "'lastUpdated' (newest first), "
                "'lastUsed' (most recent first), "
                "'size' (largest first)."
            ),
        )

        delete_cache_parser.set_defaults(func=DeleteCacheCommand)

    def __init__(self, args: Namespace) -> None:
        self.cache_dir: Optional[str] = args.dir
        self.disable_tui: bool = args.disable_tui
        self.sort_by: Optional[SortingOption_T] = args.sort

    def run(self):
        """Run `delete-cache` command with or without TUI."""
        # Scan cache directory
        hf_cache_info = scan_cache_dir(self.cache_dir)

        # Manual review from the user
        if self.disable_tui:
            selected_hashes = _manual_review_no_tui(hf_cache_info, preselected=[], sort_by=self.sort_by)
        else:
            selected_hashes = _manual_review_tui(hf_cache_info, preselected=[], sort_by=self.sort_by)

        # If deletion is not cancelled
        if len(selected_hashes) > 0 and _CANCEL_DELETION_STR not in selected_hashes:
            confirm_message = _get_expectations_str(hf_cache_info, selected_hashes) + " Confirm deletion ?"

            # Confirm deletion
            if self.disable_tui:
                confirmed = _ask_for_confirmation_no_tui(confirm_message)
            else:
                confirmed = _ask_for_confirmation_tui(confirm_message)

            # Deletion is confirmed
            if confirmed:
                strategy = hf_cache_info.delete_revisions(*selected_hashes)
                print("Start deletion.")
                strategy.execute()
                print(
                    f"Done. Deleted {len(strategy.repos)} repo(s) and"
                    f" {len(strategy.snapshots)} revision(s) for a total of"
                    f" {strategy.expected_freed_size_str}."
                )
                return

        # Deletion is cancelled
        print("Deletion is cancelled. Do nothing.")


def _get_repo_sorting_key(repo: CachedRepoInfo, sort_by: Optional[SortingOption_T] = None):
    if sort_by == "alphabetical":
        return (repo.repo_type, repo.repo_id.lower())  # by type then name
    elif sort_by == "lastUpdated":
        return -max(rev.last_modified for rev in repo.revisions)  # newest first
    elif sort_by == "lastUsed":
        return -repo.last_accessed  # most recently used first
    elif sort_by == "size":
        return -repo.size_on_disk  # largest first
    else:
        return (repo.repo_type, repo.repo_id)  # default stable order


@require_inquirer_py
def _manual_review_tui(
    hf_cache_info: HFCacheInfo,
    preselected: List[str],
    sort_by: Optional[SortingOption_T] = None,
) -> List[str]:
    """Ask the user for a manual review of the revisions to delete.

    Displays a multi-select menu in the terminal (TUI).
    """
    # Define multiselect list
    choices = _get_tui_choices_from_scan(
        repos=hf_cache_info.repos,
        preselected=preselected,
        sort_by=sort_by,
    )
    checkbox = inquirer.checkbox(
        message="Select revisions to delete:",
        choices=choices,  # List of revisions with some pre-selection
        cycle=False,  # No loop between top and bottom
        height=100,  # Large list if possible
        # We use the instruction to display to the user the expected effect of the
        # deletion.
        instruction=_get_expectations_str(
            hf_cache_info,
            selected_hashes=[c.value for c in choices if isinstance(c, Choice) and c.enabled],
        ),
        # We use the long instruction to should keybindings instructions to the user
        long_instruction="Press <space> to select, <enter> to validate and <ctrl+c> to quit without modification.",
        # Message that is displayed once the user validates its selection.
        transformer=lambda result: f"{len(result)} revision(s) selected.",
    )

    # Add a callback to update the information line when a revision is
    # selected/unselected
    def _update_expectations(_) -> None:
        # Hacky way to dynamically set an instruction message to the checkbox when
        # a revision hash is selected/unselected.
        checkbox._instruction = _get_expectations_str(
            hf_cache_info,
            selected_hashes=[choice["value"] for choice in checkbox.content_control.choices if choice["enabled"]],
        )

    checkbox.kb_func_lookup["toggle"].append({"func": _update_expectations})

    # Finally display the form to the user.
    try:
        return checkbox.execute()
    except KeyboardInterrupt:
        return []  # Quit without deletion


@require_inquirer_py
def _ask_for_confirmation_tui(message: str, default: bool = True) -> bool:
    """Ask for confirmation using Inquirer."""
    return inquirer.confirm(message, default=default).execute()


def _get_tui_choices_from_scan(
    repos: Iterable[CachedRepoInfo],
    preselected: List[str],
    sort_by: Optional[SortingOption_T] = None,
) -> List:
    """Build a list of choices from the scanned repos.

    Args:
        repos (*Iterable[`CachedRepoInfo`]*):
            List of scanned repos on which we want to delete revisions.
        preselected (*List[`str`]*):
            List of revision hashes that will be preselected.
        sort_by (*Optional[SortingOption_T]*):
            Sorting direction. Choices: "alphabetical", "lastUpdated", "lastUsed", "size".

    Return:
        The list of choices to pass to `inquirer.checkbox`.
    """
    choices: List[Union[Choice, Separator]] = []

    # First choice is to cancel the deletion
    choices.append(
        Choice(
            _CANCEL_DELETION_STR,
            name="None of the following (if selected, nothing will be deleted).",
            enabled=False,
        )
    )

    # Sort repos based on specified criteria
    sorted_repos = sorted(repos, key=lambda repo: _get_repo_sorting_key(repo, sort_by))

    for repo in sorted_repos:
        # Repo as separator
        choices.append(
            Separator(
                f"\n{repo.repo_type.capitalize()} {repo.repo_id} ({repo.size_on_disk_str},"
                f" used {repo.last_accessed_str})"
            )
        )
        for revision in sorted(repo.revisions, key=_revision_sorting_order):
            # Revision as choice
            choices.append(
                Choice(
                    revision.commit_hash,
                    name=(
                        f"{revision.commit_hash[:8]}:"
                        f" {', '.join(sorted(revision.refs)) or '(detached)'} #"
                        f" modified {revision.last_modified_str}"
                    ),
                    enabled=revision.commit_hash in preselected,
                )
            )

    # Return choices
    return choices


def _manual_review_no_tui(
    hf_cache_info: HFCacheInfo,
    preselected: List[str],
    sort_by: Optional[SortingOption_T] = None,
) -> List[str]:
    """Ask the user for a manual review of the revisions to delete.

    Used when TUI is disabled. Manual review happens in a separate tmp file that the
    user can manually edit.
    """
    # 1. Generate temporary file with delete commands.
    fd, tmp_path = mkstemp(suffix=".txt")  # suffix to make it easier to find by editors
    os.close(fd)

    lines = []

    sorted_repos = sorted(hf_cache_info.repos, key=lambda repo: _get_repo_sorting_key(repo, sort_by))

    for repo in sorted_repos:
        lines.append(
            f"\n# {repo.repo_type.capitalize()} {repo.repo_id} ({repo.size_on_disk_str},"
            f" used {repo.last_accessed_str})"
        )
        for revision in sorted(repo.revisions, key=_revision_sorting_order):
            lines.append(
                # Deselect by prepending a '#'
                f"{'' if revision.commit_hash in preselected else '#'}   "
                f" {revision.commit_hash} # Refs:"
                # Print `refs` as comment on same line
                f" {', '.join(sorted(revision.refs)) or '(detached)'} # modified"
                # Print `last_modified` as comment on same line
                f" {revision.last_modified_str}"
            )

    with open(tmp_path, "w") as f:
        f.write(_MANUAL_REVIEW_NO_TUI_INSTRUCTIONS)
        f.write("\n".join(lines))

    # 2. Prompt instructions to user.
    instructions = f"""
    TUI is disabled. In order to select which revisions you want to delete, please edit
    the following file using the text editor of your choice. Instructions for manual
    editing are located at the beginning of the file. Edit the file, save it and confirm
    to continue.
    File to edit: {ANSI.bold(tmp_path)}
    """
    print("\n".join(line.strip() for line in instructions.strip().split("\n")))

    # 3. Wait for user confirmation.
    while True:
        selected_hashes = _read_manual_review_tmp_file(tmp_path)
        if _ask_for_confirmation_no_tui(
            _get_expectations_str(hf_cache_info, selected_hashes) + " Continue ?",
            default=False,
        ):
            break

    # 4. Return selected_hashes sorted to maintain stable order
    os.remove(tmp_path)
    return sorted(selected_hashes)  # Sort to maintain stable order


def _ask_for_confirmation_no_tui(message: str, default: bool = True) -> bool:
    """Ask for confirmation using pure-python."""
    YES = ("y", "yes", "1")
    NO = ("n", "no", "0")
    DEFAULT = ""
    ALL = YES + NO + (DEFAULT,)
    full_message = message + (" (Y/n) " if default else " (y/N) ")
    while True:
        answer = input(full_message).lower()
        if answer == DEFAULT:
            return default
        if answer in YES:
            return True
        if answer in NO:
            return False
        print(f"Invalid input. Must be one of {ALL}")


def _get_expectations_str(hf_cache_info: HFCacheInfo, selected_hashes: List[str]) -> str:
    """Format a string to display to the user how much space would be saved.

    Example:
    ```
    >>> _get_expectations_str(hf_cache_info, selected_hashes)
    '7 revisions selected counting for 4.3G.'
    ```
    """
    if _CANCEL_DELETION_STR in selected_hashes:
        return "Nothing will be deleted."
    strategy = hf_cache_info.delete_revisions(*selected_hashes)
    return f"{len(selected_hashes)} revisions selected counting for {strategy.expected_freed_size_str}."


def _read_manual_review_tmp_file(tmp_path: str) -> List[str]:
    """Read the manually reviewed instruction file and return a list of revision hash.

    Example:
        ```txt
        # This is the tmp file content
        ###

        # Commented out line
        123456789 # revision hash

        # Something else
        #      a_newer_hash # 2 days ago
            an_older_hash # 3 days ago
        ```

        ```py
        >>> _read_manual_review_tmp_file(tmp_path)
        ['123456789', 'an_older_hash']
        ```
    """
    with open(tmp_path) as f:
        content = f.read()

    # Split lines
    lines = [line.strip() for line in content.split("\n")]

    # Filter commented lines
    selected_lines = [line for line in lines if not line.startswith("#")]

    # Select only before comment
    selected_hashes = [line.split("#")[0].strip() for line in selected_lines]

    # Return revision hashes
    return [hash for hash in selected_hashes if len(hash) > 0]


_MANUAL_REVIEW_NO_TUI_INSTRUCTIONS = f"""
# INSTRUCTIONS
# ------------
# This is a temporary file created by running `huggingface-cli delete-cache` with the
# `--disable-tui` option. It contains a set of revisions that can be deleted from your
# local cache directory.
#
# Please manually review the revisions you want to delete:
#   - Revision hashes can be commented out with '#'.
#   - Only non-commented revisions in this file will be deleted.
#   - Revision hashes that are removed from this file are ignored as well.
#   - If `{_CANCEL_DELETION_STR}` line is uncommented, the all cache deletion is cancelled and
#     no changes will be applied.
#
# Once you've manually reviewed this file, please confirm deletion in the terminal. This
# file will be automatically removed once done.
# ------------

# KILL SWITCH
# ------------
# Un-comment following line to completely cancel the deletion process
# {_CANCEL_DELETION_STR}
# ------------

# REVISIONS
# ------------
""".strip()


def _revision_sorting_order(revision: CachedRevisionInfo) -> Any:
    # Sort by last modified (oldest first)
    return revision.last_modified

# === NexusCore/openenv\Lib\site-packages\jedi\inference\gradual\annotation.py ===
"""
PEP 0484 ( https://www.python.org/dev/peps/pep-0484/ ) describes type hints
through function annotations. There is a strong suggestion in this document
that only the type of type hinting defined in PEP0484 should be allowed
as annotations in future python versions.
"""

import re
from inspect import Parameter

from parso import ParserSyntaxError, parse

from jedi.inference.cache import inference_state_method_cache
from jedi.inference.base_value import ValueSet, NO_VALUES
from jedi.inference.gradual.base import DefineGenericBaseClass, GenericClass
from jedi.inference.gradual.generics import TupleGenericManager
from jedi.inference.gradual.type_var import TypeVar
from jedi.inference.helpers import is_string
from jedi.inference.compiled import builtin_from_name
from jedi.inference.param import get_executed_param_names
from jedi import debug
from jedi import parser_utils


def infer_annotation(context, annotation):
    """
    Inferes an annotation node. This means that it inferes the part of
    `int` here:

        foo: int = 3

    Also checks for forward references (strings)
    """
    value_set = context.infer_node(annotation)
    if len(value_set) != 1:
        debug.warning("Inferred typing index %s should lead to 1 object, "
                      " not %s" % (annotation, value_set))
        return value_set

    inferred_value = list(value_set)[0]
    if is_string(inferred_value):
        result = _get_forward_reference_node(context, inferred_value.get_safe_value())
        if result is not None:
            return context.infer_node(result)
    return value_set


def _infer_annotation_string(context, string, index=None):
    node = _get_forward_reference_node(context, string)
    if node is None:
        return NO_VALUES

    value_set = context.infer_node(node)
    if index is not None:
        value_set = value_set.filter(
            lambda value: (
                value.array_type == 'tuple'
                and len(list(value.py__iter__())) >= index
            )
        ).py__simple_getitem__(index)
    return value_set


def _get_forward_reference_node(context, string):
    try:
        new_node = context.inference_state.grammar.parse(
            string,
            start_symbol='eval_input',
            error_recovery=False
        )
    except ParserSyntaxError:
        debug.warning('Annotation not parsed: %s' % string)
        return None
    else:
        module = context.tree_node.get_root_node()
        parser_utils.move(new_node, module.end_pos[0])
        new_node.parent = context.tree_node
        return new_node


def _split_comment_param_declaration(decl_text):
    """
    Split decl_text on commas, but group generic expressions
    together.

    For example, given "foo, Bar[baz, biz]" we return
    ['foo', 'Bar[baz, biz]'].

    """
    try:
        node = parse(decl_text, error_recovery=False).children[0]
    except ParserSyntaxError:
        debug.warning('Comment annotation is not valid Python: %s' % decl_text)
        return []

    if node.type in ['name', 'atom_expr', 'power']:
        return [node.get_code().strip()]

    params = []
    try:
        children = node.children
    except AttributeError:
        return []
    else:
        for child in children:
            if child.type in ['name', 'atom_expr', 'power']:
                params.append(child.get_code().strip())

    return params


@inference_state_method_cache()
def infer_param(function_value, param, ignore_stars=False):
    values = _infer_param(function_value, param)
    if ignore_stars or not values:
        return values
    inference_state = function_value.inference_state
    if param.star_count == 1:
        tuple_ = builtin_from_name(inference_state, 'tuple')
        return ValueSet([GenericClass(
            tuple_,
            TupleGenericManager((values,)),
        )])
    elif param.star_count == 2:
        dct = builtin_from_name(inference_state, 'dict')
        generics = (
            ValueSet([builtin_from_name(inference_state, 'str')]),
            values
        )
        return ValueSet([GenericClass(
            dct,
            TupleGenericManager(generics),
        )])
    return values


def _infer_param(function_value, param):
    """
    Infers the type of a function parameter, using type annotations.
    """
    annotation = param.annotation
    if annotation is None:
        # If no Python 3-style annotation, look for a comment annotation.
        # Identify parameters to function in the same sequence as they would
        # appear in a type comment.
        all_params = [child for child in param.parent.children
                      if child.type == 'param']

        node = param.parent.parent
        comment = parser_utils.get_following_comment_same_line(node)
        if comment is None:
            return NO_VALUES

        match = re.match(r"^#\s*type:\s*\(([^#]*)\)\s*->", comment)
        if not match:
            return NO_VALUES
        params_comments = _split_comment_param_declaration(match.group(1))

        # Find the specific param being investigated
        index = all_params.index(param)
        # If the number of parameters doesn't match length of type comment,
        # ignore first parameter (assume it's self).
        if len(params_comments) != len(all_params):
            debug.warning(
                "Comments length != Params length %s %s",
                params_comments, all_params
            )
        if function_value.is_bound_method():
            if index == 0:
                # Assume it's self, which is already handled
                return NO_VALUES
            index -= 1
        if index >= len(params_comments):
            return NO_VALUES

        param_comment = params_comments[index]
        return _infer_annotation_string(
            function_value.get_default_param_context(),
            param_comment
        )
    # Annotations are like default params and resolve in the same way.
    context = function_value.get_default_param_context()
    return infer_annotation(context, annotation)


def py__annotations__(funcdef):
    dct = {}
    for function_param in funcdef.get_params():
        param_annotation = function_param.annotation
        if param_annotation is not None:
            dct[function_param.name.value] = param_annotation

    return_annotation = funcdef.annotation
    if return_annotation:
        dct['return'] = return_annotation
    return dct


def resolve_forward_references(context, all_annotations):
    def resolve(node):
        if node is None or node.type != 'string':
            return node

        node = _get_forward_reference_node(
            context,
            context.inference_state.compiled_subprocess.safe_literal_eval(
                node.value,
            ),
        )

        if node is None:
            # There was a string, but it's not a valid annotation
            return None

        # The forward reference tree has an additional root node ('eval_input')
        # that we don't want. Extract the node we do want, that is equivalent to
        # the nodes returned by `py__annotations__` for a non-quoted node.
        node = node.children[0]

        return node

    return {name: resolve(node) for name, node in all_annotations.items()}


@inference_state_method_cache()
def infer_return_types(function, arguments):
    """
    Infers the type of a function's return value,
    according to type annotations.
    """
    context = function.get_default_param_context()
    all_annotations = resolve_forward_references(
        context,
        py__annotations__(function.tree_node),
    )
    annotation = all_annotations.get("return", None)
    if annotation is None:
        # If there is no Python 3-type annotation, look for an annotation
        # comment.
        node = function.tree_node
        comment = parser_utils.get_following_comment_same_line(node)
        if comment is None:
            return NO_VALUES

        match = re.match(r"^#\s*type:\s*\([^#]*\)\s*->\s*([^#]*)", comment)
        if not match:
            return NO_VALUES

        return _infer_annotation_string(
            context,
            match.group(1).strip()
        ).execute_annotation()

    unknown_type_vars = find_unknown_type_vars(context, annotation)
    annotation_values = infer_annotation(context, annotation)
    if not unknown_type_vars:
        return annotation_values.execute_annotation()

    type_var_dict = infer_type_vars_for_execution(function, arguments, all_annotations)

    return ValueSet.from_sets(
        ann.define_generics(type_var_dict)
        if isinstance(ann, (DefineGenericBaseClass, TypeVar)) else ValueSet({ann})
        for ann in annotation_values
    ).execute_annotation()


def infer_type_vars_for_execution(function, arguments, annotation_dict):
    """
    Some functions use type vars that are not defined by the class, but rather
    only defined in the function. See for example `iter`. In those cases we
    want to:

    1. Search for undefined type vars.
    2. Infer type vars with the execution state we have.
    3. Return the union of all type vars that have been found.
    """
    context = function.get_default_param_context()

    annotation_variable_results = {}
    executed_param_names = get_executed_param_names(function, arguments)
    for executed_param_name in executed_param_names:
        try:
            annotation_node = annotation_dict[executed_param_name.string_name]
        except KeyError:
            continue

        annotation_variables = find_unknown_type_vars(context, annotation_node)
        if annotation_variables:
            # Infer unknown type var
            annotation_value_set = context.infer_node(annotation_node)
            kind = executed_param_name.get_kind()
            actual_value_set = executed_param_name.infer()
            if kind is Parameter.VAR_POSITIONAL:
                actual_value_set = actual_value_set.merge_types_of_iterate()
            elif kind is Parameter.VAR_KEYWORD:
                # TODO _dict_values is not public.
                actual_value_set = actual_value_set.try_merge('_dict_values')
            merge_type_var_dicts(
                annotation_variable_results,
                annotation_value_set.infer_type_vars(actual_value_set),
            )
    return annotation_variable_results


def infer_return_for_callable(arguments, param_values, result_values):
    all_type_vars = {}
    for pv in param_values:
        if pv.array_type == 'list':
            type_var_dict = _infer_type_vars_for_callable(arguments, pv.py__iter__())
            all_type_vars.update(type_var_dict)

    return ValueSet.from_sets(
        v.define_generics(all_type_vars)
        if isinstance(v, (DefineGenericBaseClass, TypeVar))
        else ValueSet({v})
        for v in result_values
    ).execute_annotation()


def _infer_type_vars_for_callable(arguments, lazy_params):
    """
    Infers type vars for the Calllable class:

        def x() -> Callable[[Callable[..., _T]], _T]: ...
    """
    annotation_variable_results = {}
    for (_, lazy_value), lazy_callable_param in zip(arguments.unpack(), lazy_params):
        callable_param_values = lazy_callable_param.infer()
        # Infer unknown type var
        actual_value_set = lazy_value.infer()
        merge_type_var_dicts(
            annotation_variable_results,
            callable_param_values.infer_type_vars(actual_value_set),
        )
    return annotation_variable_results


def merge_type_var_dicts(base_dict, new_dict):
    for type_var_name, values in new_dict.items():
        if values:
            try:
                base_dict[type_var_name] |= values
            except KeyError:
                base_dict[type_var_name] = values


def merge_pairwise_generics(annotation_value, annotated_argument_class):
    """
    Match up the generic parameters from the given argument class to the
    target annotation.

    This walks the generic parameters immediately within the annotation and
    argument's type, in order to determine the concrete values of the
    annotation's parameters for the current case.

    For example, given the following code:

        def values(mapping: Mapping[K, V]) -> List[V]: ...

        for val in values({1: 'a'}):
            val

    Then this function should be given representations of `Mapping[K, V]`
    and `Mapping[int, str]`, so that it can determine that `K` is `int and
    `V` is `str`.

    Note that it is responsibility of the caller to traverse the MRO of the
    argument type as needed in order to find the type matching the
    annotation (in this case finding `Mapping[int, str]` as a parent of
    `Dict[int, str]`).

    Parameters
    ----------

    `annotation_value`: represents the annotation to infer the concrete
        parameter types of.

    `annotated_argument_class`: represents the annotated class of the
        argument being passed to the object annotated by `annotation_value`.
    """

    type_var_dict = {}

    if not isinstance(annotated_argument_class, DefineGenericBaseClass):
        return type_var_dict

    annotation_generics = annotation_value.get_generics()
    actual_generics = annotated_argument_class.get_generics()

    for annotation_generics_set, actual_generic_set in zip(annotation_generics, actual_generics):
        merge_type_var_dicts(
            type_var_dict,
            annotation_generics_set.infer_type_vars(actual_generic_set.execute_annotation()),
        )

    return type_var_dict


def find_type_from_comment_hint_for(context, node, name):
    return _find_type_from_comment_hint(context, node, node.children[1], name)


def find_type_from_comment_hint_with(context, node, name):
    if len(node.children) > 4:
        # In case there are multiple with_items, we do not want a type hint for
        # now.
        return []
    assert len(node.children[1].children) == 3, \
        "Can only be here when children[1] is 'foo() as f'"
    varlist = node.children[1].children[2]
    return _find_type_from_comment_hint(context, node, varlist, name)


def find_type_from_comment_hint_assign(context, node, name):
    return _find_type_from_comment_hint(context, node, node.children[0], name)


def _find_type_from_comment_hint(context, node, varlist, name):
    index = None
    if varlist.type in ("testlist_star_expr", "exprlist", "testlist"):
        # something like "a, b = 1, 2"
        index = 0
        for child in varlist.children:
            if child == name:
                break
            if child.type == "operator":
                continue
            index += 1
        else:
            return []

    comment = parser_utils.get_following_comment_same_line(node)
    if comment is None:
        return []
    match = re.match(r"^#\s*type:\s*([^#]*)", comment)
    if match is None:
        return []
    return _infer_annotation_string(
        context, match.group(1).strip(), index
    ).execute_annotation()


def find_unknown_type_vars(context, node):
    def check_node(node):
        if node.type in ('atom_expr', 'power'):
            trailer = node.children[-1]
            if trailer.type == 'trailer' and trailer.children[0] == '[':
                for subscript_node in _unpack_subscriptlist(trailer.children[1]):
                    check_node(subscript_node)
        else:
            found[:] = _filter_type_vars(context.infer_node(node), found)

    found = []  # We're not using a set, because the order matters.
    check_node(node)
    return found


def _filter_type_vars(value_set, found=()):
    new_found = list(found)
    for type_var in value_set:
        if isinstance(type_var, TypeVar) and type_var not in found:
            new_found.append(type_var)
    return new_found


def _unpack_subscriptlist(subscriptlist):
    if subscriptlist.type == 'subscriptlist':
        for subscript in subscriptlist.children[::2]:
            if subscript.type != 'subscript':
                yield subscript
    else:
        if subscriptlist.type != 'subscript':
            yield subscriptlist

# === NexusCore/openenv\Lib\site-packages\nltk\tokenize\texttiling.py ===
# Natural Language Toolkit: TextTiling
#
# Copyright (C) 2001-2024 NLTK Project
# Author: George Boutsioukis
#
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT

import math
import re

try:
    import numpy
except ImportError:
    pass

from nltk.tokenize.api import TokenizerI

BLOCK_COMPARISON, VOCABULARY_INTRODUCTION = 0, 1
LC, HC = 0, 1
DEFAULT_SMOOTHING = [0]


class TextTilingTokenizer(TokenizerI):
    """Tokenize a document into topical sections using the TextTiling algorithm.
    This algorithm detects subtopic shifts based on the analysis of lexical
    co-occurrence patterns.

    The process starts by tokenizing the text into pseudosentences of
    a fixed size w. Then, depending on the method used, similarity
    scores are assigned at sentence gaps. The algorithm proceeds by
    detecting the peak differences between these scores and marking
    them as boundaries. The boundaries are normalized to the closest
    paragraph break and the segmented text is returned.

    :param w: Pseudosentence size
    :type w: int
    :param k: Size (in sentences) of the block used in the block comparison method
    :type k: int
    :param similarity_method: The method used for determining similarity scores:
       `BLOCK_COMPARISON` (default) or `VOCABULARY_INTRODUCTION`.
    :type similarity_method: constant
    :param stopwords: A list of stopwords that are filtered out (defaults to NLTK's stopwords corpus)
    :type stopwords: list(str)
    :param smoothing_method: The method used for smoothing the score plot:
      `DEFAULT_SMOOTHING` (default)
    :type smoothing_method: constant
    :param smoothing_width: The width of the window used by the smoothing method
    :type smoothing_width: int
    :param smoothing_rounds: The number of smoothing passes
    :type smoothing_rounds: int
    :param cutoff_policy: The policy used to determine the number of boundaries:
      `HC` (default) or `LC`
    :type cutoff_policy: constant

    >>> from nltk.corpus import brown
    >>> tt = TextTilingTokenizer(demo_mode=True)
    >>> text = brown.raw()[:4000]
    >>> s, ss, d, b = tt.tokenize(text)
    >>> b
    [0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0, 0]
    """

    def __init__(
        self,
        w=20,
        k=10,
        similarity_method=BLOCK_COMPARISON,
        stopwords=None,
        smoothing_method=DEFAULT_SMOOTHING,
        smoothing_width=2,
        smoothing_rounds=1,
        cutoff_policy=HC,
        demo_mode=False,
    ):
        if stopwords is None:
            from nltk.corpus import stopwords

            stopwords = stopwords.words("english")
        self.__dict__.update(locals())
        del self.__dict__["self"]

    def tokenize(self, text):
        """Return a tokenized copy of *text*, where each "token" represents
        a separate topic."""

        lowercase_text = text.lower()
        paragraph_breaks = self._mark_paragraph_breaks(text)
        text_length = len(lowercase_text)

        # Tokenization step starts here

        # Remove punctuation
        nopunct_text = "".join(
            c for c in lowercase_text if re.match(r"[a-z\-' \n\t]", c)
        )
        nopunct_par_breaks = self._mark_paragraph_breaks(nopunct_text)

        tokseqs = self._divide_to_tokensequences(nopunct_text)

        # The morphological stemming step mentioned in the TextTile
        # paper is not implemented.  A comment in the original C
        # implementation states that it offers no benefit to the
        # process. It might be interesting to test the existing
        # stemmers though.
        # words = _stem_words(words)

        # Filter stopwords
        for ts in tokseqs:
            ts.wrdindex_list = [
                wi for wi in ts.wrdindex_list if wi[0] not in self.stopwords
            ]

        token_table = self._create_token_table(tokseqs, nopunct_par_breaks)
        # End of the Tokenization step

        # Lexical score determination
        if self.similarity_method == BLOCK_COMPARISON:
            gap_scores = self._block_comparison(tokseqs, token_table)
        elif self.similarity_method == VOCABULARY_INTRODUCTION:
            raise NotImplementedError("Vocabulary introduction not implemented")
        else:
            raise ValueError(
                f"Similarity method {self.similarity_method} not recognized"
            )

        if self.smoothing_method == DEFAULT_SMOOTHING:
            smooth_scores = self._smooth_scores(gap_scores)
        else:
            raise ValueError(f"Smoothing method {self.smoothing_method} not recognized")
        # End of Lexical score Determination

        # Boundary identification
        depth_scores = self._depth_scores(smooth_scores)
        segment_boundaries = self._identify_boundaries(depth_scores)

        normalized_boundaries = self._normalize_boundaries(
            text, segment_boundaries, paragraph_breaks
        )
        # End of Boundary Identification
        segmented_text = []
        prevb = 0

        for b in normalized_boundaries:
            if b == 0:
                continue
            segmented_text.append(text[prevb:b])
            prevb = b

        if prevb < text_length:  # append any text that may be remaining
            segmented_text.append(text[prevb:])

        if not segmented_text:
            segmented_text = [text]

        if self.demo_mode:
            return gap_scores, smooth_scores, depth_scores, segment_boundaries
        return segmented_text

    def _block_comparison(self, tokseqs, token_table):
        """Implements the block comparison method"""

        def blk_frq(tok, block):
            ts_occs = filter(lambda o: o[0] in block, token_table[tok].ts_occurences)
            freq = sum(tsocc[1] for tsocc in ts_occs)
            return freq

        gap_scores = []
        numgaps = len(tokseqs) - 1

        for curr_gap in range(numgaps):
            score_dividend, score_divisor_b1, score_divisor_b2 = 0.0, 0.0, 0.0
            score = 0.0
            # adjust window size for boundary conditions
            if curr_gap < self.k - 1:
                window_size = curr_gap + 1
            elif curr_gap > numgaps - self.k:
                window_size = numgaps - curr_gap
            else:
                window_size = self.k

            b1 = [ts.index for ts in tokseqs[curr_gap - window_size + 1 : curr_gap + 1]]
            b2 = [ts.index for ts in tokseqs[curr_gap + 1 : curr_gap + window_size + 1]]

            for t in token_table:
                score_dividend += blk_frq(t, b1) * blk_frq(t, b2)
                score_divisor_b1 += blk_frq(t, b1) ** 2
                score_divisor_b2 += blk_frq(t, b2) ** 2
            try:
                score = score_dividend / math.sqrt(score_divisor_b1 * score_divisor_b2)
            except ZeroDivisionError:
                pass  # score += 0.0

            gap_scores.append(score)

        return gap_scores

    def _smooth_scores(self, gap_scores):
        "Wraps the smooth function from the SciPy Cookbook"
        return list(
            smooth(numpy.array(gap_scores[:]), window_len=self.smoothing_width + 1)
        )

    def _mark_paragraph_breaks(self, text):
        """Identifies indented text or line breaks as the beginning of
        paragraphs"""
        MIN_PARAGRAPH = 100
        pattern = re.compile("[ \t\r\f\v]*\n[ \t\r\f\v]*\n[ \t\r\f\v]*")
        matches = pattern.finditer(text)

        last_break = 0
        pbreaks = [0]
        for pb in matches:
            if pb.start() - last_break < MIN_PARAGRAPH:
                continue
            else:
                pbreaks.append(pb.start())
                last_break = pb.start()

        return pbreaks

    def _divide_to_tokensequences(self, text):
        "Divides the text into pseudosentences of fixed size"
        w = self.w
        wrdindex_list = []
        matches = re.finditer(r"\w+", text)
        for match in matches:
            wrdindex_list.append((match.group(), match.start()))
        return [
            TokenSequence(i / w, wrdindex_list[i : i + w])
            for i in range(0, len(wrdindex_list), w)
        ]

    def _create_token_table(self, token_sequences, par_breaks):
        "Creates a table of TokenTableFields"
        token_table = {}
        current_par = 0
        current_tok_seq = 0
        pb_iter = par_breaks.__iter__()
        current_par_break = next(pb_iter)
        if current_par_break == 0:
            try:
                current_par_break = next(pb_iter)  # skip break at 0
            except StopIteration as e:
                raise ValueError(
                    "No paragraph breaks were found(text too short perhaps?)"
                ) from e
        for ts in token_sequences:
            for word, index in ts.wrdindex_list:
                try:
                    while index > current_par_break:
                        current_par_break = next(pb_iter)
                        current_par += 1
                except StopIteration:
                    # hit bottom
                    pass

                if word in token_table:
                    token_table[word].total_count += 1

                    if token_table[word].last_par != current_par:
                        token_table[word].last_par = current_par
                        token_table[word].par_count += 1

                    if token_table[word].last_tok_seq != current_tok_seq:
                        token_table[word].last_tok_seq = current_tok_seq
                        token_table[word].ts_occurences.append([current_tok_seq, 1])
                    else:
                        token_table[word].ts_occurences[-1][1] += 1
                else:  # new word
                    token_table[word] = TokenTableField(
                        first_pos=index,
                        ts_occurences=[[current_tok_seq, 1]],
                        total_count=1,
                        par_count=1,
                        last_par=current_par,
                        last_tok_seq=current_tok_seq,
                    )

            current_tok_seq += 1

        return token_table

    def _identify_boundaries(self, depth_scores):
        """Identifies boundaries at the peaks of similarity score
        differences"""

        boundaries = [0 for x in depth_scores]

        avg = sum(depth_scores) / len(depth_scores)
        stdev = numpy.std(depth_scores)

        if self.cutoff_policy == LC:
            cutoff = avg - stdev
        else:
            cutoff = avg - stdev / 2.0

        depth_tuples = sorted(zip(depth_scores, range(len(depth_scores))))
        depth_tuples.reverse()
        hp = list(filter(lambda x: x[0] > cutoff, depth_tuples))

        for dt in hp:
            boundaries[dt[1]] = 1
            for dt2 in hp:  # undo if there is a boundary close already
                if (
                    dt[1] != dt2[1]
                    and abs(dt2[1] - dt[1]) < 4
                    and boundaries[dt2[1]] == 1
                ):
                    boundaries[dt[1]] = 0
        return boundaries

    def _depth_scores(self, scores):
        """Calculates the depth of each gap, i.e. the average difference
        between the left and right peaks and the gap's score"""

        depth_scores = [0 for x in scores]
        # clip boundaries: this holds on the rule of thumb(my thumb)
        # that a section shouldn't be smaller than at least 2
        # pseudosentences for small texts and around 5 for larger ones.

        clip = min(max(len(scores) // 10, 2), 5)
        index = clip

        for gapscore in scores[clip:-clip]:
            lpeak = gapscore
            for score in scores[index::-1]:
                if score >= lpeak:
                    lpeak = score
                else:
                    break
            rpeak = gapscore
            for score in scores[index:]:
                if score >= rpeak:
                    rpeak = score
                else:
                    break
            depth_scores[index] = lpeak + rpeak - 2 * gapscore
            index += 1

        return depth_scores

    def _normalize_boundaries(self, text, boundaries, paragraph_breaks):
        """Normalize the boundaries identified to the original text's
        paragraph breaks"""

        norm_boundaries = []
        char_count, word_count, gaps_seen = 0, 0, 0
        seen_word = False

        for char in text:
            char_count += 1
            if char in " \t\n" and seen_word:
                seen_word = False
                word_count += 1
            if char not in " \t\n" and not seen_word:
                seen_word = True
            if gaps_seen < len(boundaries) and word_count > (
                max(gaps_seen * self.w, self.w)
            ):
                if boundaries[gaps_seen] == 1:
                    # find closest paragraph break
                    best_fit = len(text)
                    for br in paragraph_breaks:
                        if best_fit > abs(br - char_count):
                            best_fit = abs(br - char_count)
                            bestbr = br
                        else:
                            break
                    if bestbr not in norm_boundaries:  # avoid duplicates
                        norm_boundaries.append(bestbr)
                gaps_seen += 1

        return norm_boundaries


class TokenTableField:
    """A field in the token table holding parameters for each token,
    used later in the process"""

    def __init__(
        self,
        first_pos,
        ts_occurences,
        total_count=1,
        par_count=1,
        last_par=0,
        last_tok_seq=None,
    ):
        self.__dict__.update(locals())
        del self.__dict__["self"]


class TokenSequence:
    "A token list with its original length and its index"

    def __init__(self, index, wrdindex_list, original_length=None):
        original_length = original_length or len(wrdindex_list)
        self.__dict__.update(locals())
        del self.__dict__["self"]


# Pasted from the SciPy cookbook: https://www.scipy.org/Cookbook/SignalSmooth
def smooth(x, window_len=11, window="flat"):
    """smooth the data using a window with requested size.

    This method is based on the convolution of a scaled window with the signal.
    The signal is prepared by introducing reflected copies of the signal
    (with the window size) in both ends so that transient parts are minimized
    in the beginning and end part of the output signal.

    :param x: the input signal
    :param window_len: the dimension of the smoothing window; should be an odd integer
    :param window: the type of window from 'flat', 'hanning', 'hamming', 'bartlett', 'blackman'
        flat window will produce a moving average smoothing.

    :return: the smoothed signal

    example::

        t=linspace(-2,2,0.1)
        x=sin(t)+randn(len(t))*0.1
        y=smooth(x)

    :see also: numpy.hanning, numpy.hamming, numpy.bartlett, numpy.blackman, numpy.convolve,
        scipy.signal.lfilter

    TODO: the window parameter could be the window itself if an array instead of a string
    """

    if x.ndim != 1:
        raise ValueError("smooth only accepts 1 dimension arrays.")

    if x.size < window_len:
        raise ValueError("Input vector needs to be bigger than window size.")

    if window_len < 3:
        return x

    if window not in ["flat", "hanning", "hamming", "bartlett", "blackman"]:
        raise ValueError(
            "Window is on of 'flat', 'hanning', 'hamming', 'bartlett', 'blackman'"
        )

    s = numpy.r_[2 * x[0] - x[window_len:1:-1], x, 2 * x[-1] - x[-1:-window_len:-1]]

    # print(len(s))
    if window == "flat":  # moving average
        w = numpy.ones(window_len, "d")
    else:
        w = eval("numpy." + window + "(window_len)")

    y = numpy.convolve(w / w.sum(), s, mode="same")

    return y[window_len - 1 : -window_len + 1]


def demo(text=None):
    from matplotlib import pylab

    from nltk.corpus import brown

    tt = TextTilingTokenizer(demo_mode=True)
    if text is None:
        text = brown.raw()[:10000]
    s, ss, d, b = tt.tokenize(text)
    pylab.xlabel("Sentence Gap index")
    pylab.ylabel("Gap Scores")
    pylab.plot(range(len(s)), s, label="Gap Scores")
    pylab.plot(range(len(ss)), ss, label="Smoothed Gap scores")
    pylab.plot(range(len(d)), d, label="Depth scores")
    pylab.stem(range(len(b)), b)
    pylab.legend()
    pylab.show()

# === NexusCore/openenv\Lib\site-packages\scripts\wtf.py ===
from yaspin import yaspin

# Start spinner
spinner = yaspin()
spinner.start()

import os
import platform
import re
import subprocess
import sys
import time

import platformdirs
import pyperclip
import yaml

try:
    from pynput.keyboard import Controller, Key
except ImportError:
    spinner.stop()
    print("Please run `pip install pynput` to use the `wtf` command.")
    exit()

# Don't let litellm go online here, this slows it down
os.environ["LITELLM_LOCAL_MODEL_COST_MAP"] = "True"
import litellm

# Define system messages
SYSTEM_MESSAGE = f"""
You are a fast, efficient terminal assistant. Your task is to:

1. Scan the provided terminal history.
2. Identify the most recent error or issue.
3. Take a deep breath, and thoughtfully, carefully determine the most likely solution or debugging step.
4. Respond with a VERY brief explanation followed by a markdown code block containing a shell command to address the issue.

Rules:
- Provide a single shell command in your code block, using line continuation characters (\\ for Unix-like systems, ^ for Windows) for multiline commands.
- Ensure the entire command is on one logical line, requiring the user to press enter only once to execute.
- If multiple steps are needed, explain the process briefly, then provide only the first command or a combined command using && or ;.
- Keep any explanatory text extremely brief and concise.
- Place explanatory text before the code block.
- NEVER USE COMMENTS IN YOUR CODE.
- Construct the command with proper escaping: e.g. use sed with correctly escaped quotes to ensure the shell interprets the command correctly. This involves:
	•	Using double quotes around the sed expression to handle single quotes within the command.
	•	Combining single and double quotes to properly escape characters within the shell command.
- If previous commands attempted to fix the issue and failed, learn from them by proposing a DIFFERENT command.
- Focus on the most recent error, ignoring earlier unrelated commands. If the user included a message at the end, focus on helping them.
- If you need more information to confidently fix the problem, ask the user to run wtf again in a moment, then write a command like grep to learn more about the problem.
- The error may be as simple as a spelling error, or as complex as requiring tests to be run, or code to be find-and-replaced.
- Prioritize speed and conciseness in your response. Don't use markdown headings. Don't say more than a sentence or two. Be incredibly concise.

User's System: {platform.system()}
CWD: {os.getcwd()}
{"Shell: " + os.environ.get('SHELL') if os.environ.get('SHELL') else ''}

"""

CUSTOM_MESSAGE_SYSTEM_MESSAGE = f"""

You are a fast, efficient AI assistant for terminal and coding tasks. When summoned, you will:

1. Review the provided terminal history (which may or may not be relevant) and final user query.
2. Determine the most appropriate solution or debugging step to resolve the user's final query.
3. Respond with a brief explanation and a single shell command in a markdown code block.

Rules:
- Provide one logical command (use \ or ^ for multiline).
- Keep explanations concise and place them before the code block.
- Use proper command escaping (e.g., sed with correct quotes).
- Avoid comments in the code block.
- If more info is needed, provide a command to gather it (e.g., grep).
- Focus on the user's FINAL query and ADDRESS NOTHING ELSE, using terminal history for context if relevant.
- For multi-step solutions, explain briefly and provide the first or combined command.
- Prioritize addressing the user's specific request (at the END, after "wtf") efficiently.

User's System: {platform.system()}
CWD: {os.getcwd()}
{"Shell: " + os.environ.get('SHELL') if os.environ.get('SHELL') else ''}

"""

LOCAL_SYSTEM_MESSAGE = f"""
You're a fast AI assistant for terminal issues. You must:

1. Scan terminal history
2. Identify latest error
3. Determine best solution
4. Reply with brief explanation + single shell command in markdown

Rules:
- One logical command (use \ or ^ for multiline)
- Explain briefly, then provide command
- No comments in code
- Proper escaping (e.g., sed with correct quotes)
- If unsure, get more info with a command like grep
- Prioritize speed and conciseness

Example response:

We need to fix the file permissions on config.yml.
```bash
chmod 644 config.yml
```

User's System: {platform.system()}
CWD: {os.getcwd()}
{"Shell: " + os.environ.get('SHELL') if os.environ.get('SHELL') else ''}

Now, it's your turn:
"""


def main():
    ### GET OPTIONAL CUSTOM MESSAGE

    custom_message = None
    if len(sys.argv) > 1:
        custom_message = "wtf " + " ".join(sys.argv[1:])

    ### GET TERMINAL HISTORY

    keyboard = Controller()
    history = None

    ## SELECT ALL AND COPY METHOD

    if True:
        # Save clipboard
        clipboard = pyperclip.paste()

        # Select all text
        shortcut_key = Key.cmd if platform.system() == "Darwin" else Key.ctrl
        with keyboard.pressed(shortcut_key):
            keyboard.press("a")
            keyboard.release("a")

        # Copy selected text
        with keyboard.pressed(shortcut_key):
            keyboard.press("c")
            keyboard.release("c")

        # Deselect
        keyboard.press(Key.backspace)
        keyboard.release(Key.backspace)

        # Wait for the clipboard to update
        time.sleep(0.1)

        # Get terminal history from clipboard
        history = pyperclip.paste()

        # Reset clipboard to stored one
        pyperclip.copy(clipboard)

    ## OCR SCREENSHOT METHOD

    if not history:
        try:
            import pytesseract
            from PIL import ImageGrab

            # Get active window coordinates using platform-specific methods
            platform_name = platform.system()
            if platform_name == "Windows":
                import win32gui

                window = win32gui.GetForegroundWindow()
                left, top, right, bottom = win32gui.GetWindowRect(window)
            elif platform_name == "Darwin":
                from Quartz import (
                    CGWindowListCopyWindowInfo,
                    kCGNullWindowID,
                    kCGWindowListOptionOnScreenOnly,
                )

                window_info = CGWindowListCopyWindowInfo(
                    kCGWindowListOptionOnScreenOnly, kCGNullWindowID
                )
                for window in window_info:
                    if window["kCGWindowLayer"] == 0:
                        window_geometry = window["kCGWindowBounds"]
                        left = window_geometry["X"]
                        top = window_geometry["Y"]
                        right = int(left + window_geometry["Width"])
                        bottom = int(top + window_geometry["Height"])
                        break
            else:  # Assume it's a Linux-based system
                root = subprocess.Popen(
                    ["xprop", "-root", "_NET_ACTIVE_WINDOW"], stdout=subprocess.PIPE
                )
                stdout, stderr = root.communicate()
                m = re.search(b"^_NET_ACTIVE_WINDOW.* ([\\w]+)$", stdout)
                if m is not None:
                    window_id = m.group(1)
                    window = subprocess.Popen(
                        ["xwininfo", "-id", window_id], stdout=subprocess.PIPE
                    )
                    stdout, stderr = window.communicate()
                    match = re.search(
                        rb"Absolute upper-left X:\s*(\d+).*Absolute upper-left Y:\s*(\d+).*Width:\s*(\d+).*Height:\s*(\d+)",
                        stdout,
                        re.DOTALL,
                    )
                    if match is not None:
                        left, top, width, height = map(int, match.groups())
                        right = left + width
                        bottom = top + height

            # spinner.stop()
            # print("\nPermission to capture terminal commands via screenshot -> OCR?")
            # permission = input("(y/n) > ")
            # print("")
            # if permission.lower() != 'y':
            #     print("Exiting...")
            #     exit()
            # spinner.start()

            # Take screenshot of the active window
            screenshot = ImageGrab.grab(
                bbox=(int(left), int(top), int(right), int(bottom))
            )

            # OCR the screenshot to get the text
            text = pytesseract.image_to_string(screenshot)

            history = text

            if "wtf" in history:
                last_wtf_index = history.rindex("wtf")
                history = history[:last_wtf_index]
        except ImportError:
            spinner.stop()
            print(
                "To use OCR to capture terminal output (recommended) run `pip install pytesseract` or `pip3 install pytesseract`."
            )
            spinner.start()

    ## TERMINAL HISTORY METHOD

    if not history:
        try:
            shell = os.environ.get("SHELL", "/bin/bash")
            command = [shell, "-ic", "fc -ln -10"]  # Get just the last command

            output = subprocess.check_output(command, stderr=subprocess.STDOUT).decode(
                "utf-8"
            )

            # Split the output into lines
            lines = output.strip().split("\n")

            # Filter out lines that look like the "saving session" message
            history = [
                line
                for line in lines
                if not line.startswith("...")
                and "saving" not in line
                and "Saving session..." not in line
            ]
            history = [l.strip() for l in history if l.strip()][-10:]

            # Split the history into individual commands

            # Get the last command
            last_command = history[-1]
            spinner.start()
            print(
                f"\nRunning the last command again to collect its output: {last_command}\n"
            )
            spinner.stop()
            # Run the last command and collect its output
            try:
                last_command_output = subprocess.check_output(
                    last_command, shell=True, stderr=subprocess.STDOUT
                ).decode("utf-8")
            except subprocess.CalledProcessError as e:
                last_command_output = e.output.decode("utf-8")
            except Exception as e:
                last_command_output = str(e)

            # Format the history
            history = "The user tried to run the following commands:\n" + "\n".join(
                history
            )
            history += f"\nThe last command, {last_command}, resulted in this output:\n{last_command_output}"

        except Exception as e:
            raise
            print(
                "Failed to retrieve and run the last command from terminal history. Exiting."
            )
            return

    # Trim history
    history = history[-9000:].strip()

    # Remove any trailing spinner commands
    spinner_commands = [
        "⠴",
        "⠦",
        "⠇",
        "⠉",
        "⠙",
        "⠸",
        "⠼",
        "⠤",
        "⠴",
        "⠂",
        "⠄",
        "⠈",
        "⠐",
        "⠠",
    ]
    for command in spinner_commands:
        if history.endswith(command):
            history = history[: -len(command)].strip()
            break

    if "wtf" in history:
        last_wtf_index = history.rindex("wtf")
        history = history[:last_wtf_index]

    ### GET ERROR CONTEXT

    # Regex pattern to extract filename and line number
    pattern = r'File "([^"]+)", line (\d+)'
    matches = re.findall(pattern, history)

    # Only keep the last X matches
    matches = matches[-1:]  # Just the last match, change -1 to get more

    # Function to get specified lines from a file
    def get_lines_from_file(filename, line_number):
        lines = []
        try:
            with open(filename, "r") as file:
                all_lines = file.readlines()
                start_line = max(0, line_number - 3)  # Preceding lines
                end_line = min(len(all_lines), line_number + 2)  # Following lines
                for i in range(start_line, end_line + 1):
                    lines.append(f"Line {i+1}: " + all_lines[i].rstrip())
        except Exception as e:
            lines.append(f"Error reading file: {e}")
        return lines

    # Create the dictionary with filename, line number, and text
    result = []
    for match in matches:
        filename, line_number = match
        line_number = int(line_number)
        lines = get_lines_from_file(filename, line_number)
        result.append({"filename": filename, "text": "\n".join(lines)})

    if result != []:
        history = "Terminal: " + history

    # Add context
    for entry in result:
        history = f"""File: {entry["filename"]}\n{entry["text"]}\n\n""" + history

    ### PREPARE FOR LLM

    # Get LLM model from profile
    default_profile_path = os.path.join(
        platformdirs.user_config_dir("open-interpreter"), "profiles", "default.yaml"
    )

    try:
        with open(default_profile_path, "r") as file:
            profile = yaml.safe_load(file)
            wtf_model = profile.get("wtf", {}).get("model")
            if wtf_model:
                model = wtf_model
            else:
                model = profile.get("llm", {}).get("model", "gpt-4o-mini")
    except:
        model = "gpt-4o-mini"

    # If they're using a local model (improve this heuristic) use the LOCAL_SYSTEM_MESSAGE
    if "ollama" in model or "llama" in model:
        system_message = LOCAL_SYSTEM_MESSAGE
    else:
        system_message = SYSTEM_MESSAGE

    # If they passed in a custom message, use the CUSTOM_MESSAGE_SYSTEM_MESSAGE
    if custom_message:
        system_message = CUSTOM_MESSAGE_SYSTEM_MESSAGE
        user_message = (
            "Answer THIS question by telling me what code to run:"
            + custom_message
            + "\nMy terminal history, which may or may not be relevant, is this:\n---\n"
            + history
            + "\n---\nPlease now answer THIS question by telling me what code to run: "
            + custom_message
        )
    else:
        user_message = (
            history.strip()
            + "\n\nPlease help me resolve the final error above by telling me what code to run in a markdown code block."
        )

    # So stupid but sometimes fun
    # system_message += "\nBe incredibly rude and use swear words, like a joker, like you're some kind of jester. You can say 'Fuck' and 'Fucking'. This is for adults. Be funny. USE ALL LOWER CASE. Act like you're an aggreived pair programmer to the idiot that got themselves in this situation."

    messages = [
        {"role": "system", "content": system_message.strip()},
        {"role": "user", "content": user_message.strip()},
    ]

    # DEBUGGING: PRINT MESSAGES

    # print("---")
    # import pprint
    # pprint.pprint(messages)
    # print("---")
    # time.sleep(100)

    ### PARSE LLM RESPONSE

    in_code = False
    backtick_count = 0
    language_buffer = ""
    started = False

    for chunk in litellm.completion(
        model=model, messages=messages, temperature=0, stream=True
    ):
        if not started:
            started = True
            spinner.stop()
            print("")

        content = chunk.choices[0].delta.content
        if content:
            for char in content:
                if char == "`":
                    backtick_count += 1
                    if backtick_count == 3:
                        in_code = not in_code
                        backtick_count = 0
                        language_buffer = ""
                        if not in_code:  # We've just exited a code block
                            time.sleep(0.1)
                            print("\n")
                            return  # Exit after typing the command
                        else:  # Entered code block
                            print("Press `enter` to run: ", end="", flush=True)
                elif in_code:
                    if language_buffer is not None:
                        if char.isalnum():
                            language_buffer += char
                        elif char.isspace():
                            language_buffer = None
                    elif char not in ["\n", "\\"]:
                        keyboard.type(char)
                else:
                    if backtick_count:
                        print("`" * backtick_count, end="", flush=True)
                        backtick_count = 0

                    # if "\n" in char:
                    #     char.replace("\n", "\n    ")

                    print(char, end="", flush=True)

                    backtick_count = 0


if __name__ == "__main__":
    main()

# === NexusCore/openenv\Lib\site-packages\litellm\llms\predibase\chat\handler.py ===
# What is this?
## Controller file for Predibase Integration - https://predibase.com/

import json
import os
import time
from functools import partial
from typing import Callable, Optional, Union

import httpx  # type: ignore

import litellm
import litellm.litellm_core_utils
import litellm.litellm_core_utils.litellm_logging
from litellm.litellm_core_utils.core_helpers import map_finish_reason
from litellm.litellm_core_utils.prompt_templates.factory import (
    custom_prompt,
    prompt_factory,
)
from litellm.llms.custom_httpx.http_handler import (
    AsyncHTTPHandler,
    get_async_httpx_client,
)
from litellm.types.utils import LiteLLMLoggingBaseClass
from litellm.utils import Choices, CustomStreamWrapper, Message, ModelResponse, Usage

from ..common_utils import PredibaseError


async def make_call(
    client: AsyncHTTPHandler,
    api_base: str,
    headers: dict,
    data: str,
    model: str,
    messages: list,
    logging_obj,
    timeout: Optional[Union[float, httpx.Timeout]],
):
    response = await client.post(
        api_base, headers=headers, data=data, stream=True, timeout=timeout
    )

    if response.status_code != 200:
        raise PredibaseError(status_code=response.status_code, message=response.text)

    completion_stream = response.aiter_lines()
    # LOGGING
    logging_obj.post_call(
        input=messages,
        api_key="",
        original_response=completion_stream,  # Pass the completion stream for logging
        additional_args={"complete_input_dict": data},
    )

    return completion_stream


class PredibaseChatCompletion:
    def __init__(self) -> None:
        super().__init__()

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

    def process_response(  # noqa: PLR0915
        self,
        model: str,
        response: httpx.Response,
        model_response: ModelResponse,
        stream: bool,
        logging_obj: LiteLLMLoggingBaseClass,
        optional_params: dict,
        api_key: str,
        data: Union[dict, str],
        messages: list,
        print_verbose,
        encoding,
    ) -> ModelResponse:
        ## LOGGING
        logging_obj.post_call(
            input=messages,
            api_key=api_key,
            original_response=response.text,
            additional_args={"complete_input_dict": data},
        )
        print_verbose(f"raw model_response: {response.text}")
        ## RESPONSE OBJECT
        try:
            completion_response = response.json()
        except Exception:
            raise PredibaseError(message=response.text, status_code=422)
        if "error" in completion_response:
            raise PredibaseError(
                message=str(completion_response["error"]),
                status_code=response.status_code,
            )
        else:
            if not isinstance(completion_response, dict):
                raise PredibaseError(
                    status_code=422,
                    message=f"'completion_response' is not a dictionary - {completion_response}",
                )
            elif "generated_text" not in completion_response:
                raise PredibaseError(
                    status_code=422,
                    message=f"'generated_text' is not a key response dictionary - {completion_response}",
                )
            if len(completion_response["generated_text"]) > 0:
                model_response.choices[0].message.content = self.output_parser(  # type: ignore
                    completion_response["generated_text"]
                )
            ## GETTING LOGPROBS + FINISH REASON
            if (
                "details" in completion_response
                and "tokens" in completion_response["details"]
            ):
                model_response.choices[0].finish_reason = map_finish_reason(
                    completion_response["details"]["finish_reason"]
                )
                sum_logprob = 0
                for token in completion_response["details"]["tokens"]:
                    if token["logprob"] is not None:
                        sum_logprob += token["logprob"]
                setattr(
                    model_response.choices[0].message,  # type: ignore
                    "_logprob",
                    sum_logprob,  # [TODO] move this to using the actual logprobs
                )
            if "best_of" in optional_params and optional_params["best_of"] > 1:
                if (
                    "details" in completion_response
                    and "best_of_sequences" in completion_response["details"]
                ):
                    choices_list = []
                    for idx, item in enumerate(
                        completion_response["details"]["best_of_sequences"]
                    ):
                        sum_logprob = 0
                        for token in item["tokens"]:
                            if token["logprob"] is not None:
                                sum_logprob += token["logprob"]
                        if len(item["generated_text"]) > 0:
                            message_obj = Message(
                                content=self.output_parser(item["generated_text"]),
                                logprobs=sum_logprob,
                            )
                        else:
                            message_obj = Message(content=None)
                        choice_obj = Choices(
                            finish_reason=map_finish_reason(item["finish_reason"]),
                            index=idx + 1,
                            message=message_obj,
                        )
                        choices_list.append(choice_obj)
                    model_response.choices.extend(choices_list)

        ## CALCULATING USAGE
        prompt_tokens = 0
        try:
            prompt_tokens = litellm.token_counter(messages=messages)
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
                )  ##[TODO] use a model-specific tokenizer
            except Exception:
                # this should remain non blocking we should not block a response returning if calculating usage fails
                pass
        else:
            completion_tokens = 0

        total_tokens = prompt_tokens + completion_tokens

        model_response.created = int(time.time())
        model_response.model = model
        usage = Usage(
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
        )
        model_response.usage = usage  # type: ignore

        ## RESPONSE HEADERS
        predibase_headers = response.headers
        response_headers = {}
        for k, v in predibase_headers.items():
            if k.startswith("x-"):
                response_headers["llm_provider-{}".format(k)] = v

        model_response._hidden_params["additional_headers"] = response_headers

        return model_response

    def completion(
        self,
        model: str,
        messages: list,
        api_base: str,
        custom_prompt_dict: dict,
        model_response: ModelResponse,
        print_verbose: Callable,
        encoding,
        api_key: str,
        logging_obj,
        optional_params: dict,
        litellm_params: dict,
        tenant_id: str,
        timeout: Union[float, httpx.Timeout],
        acompletion=None,
        logger_fn=None,
        headers: dict = {},
    ) -> Union[ModelResponse, CustomStreamWrapper]:
        headers = litellm.PredibaseConfig().validate_environment(
            api_key=api_key,
            headers=headers,
            messages=messages,
            optional_params=optional_params,
            model=model,
            litellm_params=litellm_params,
        )
        completion_url = ""
        input_text = ""
        base_url = "https://serving.app.predibase.com"

        if "https" in model:
            completion_url = model
        elif api_base:
            base_url = api_base
        elif "PREDIBASE_API_BASE" in os.environ:
            base_url = os.getenv("PREDIBASE_API_BASE", "")

        completion_url = f"{base_url}/{tenant_id}/deployments/v2/llms/{model}"

        if optional_params.get("stream", False) is True:
            completion_url += "/generate_stream"
        else:
            completion_url += "/generate"

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
        config = litellm.PredibaseConfig.get_config()
        for k, v in config.items():
            if (
                k not in optional_params
            ):  # completion(top_k=3) > anthropic_config(top_k=3) <- allows for dynamic variables to be passed in
                optional_params[k] = v

        stream = optional_params.pop("stream", False)

        data = {
            "inputs": prompt,
            "parameters": optional_params,
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
                timeout=timeout,  # type: ignore
            )
            _response = CustomStreamWrapper(
                response.iter_lines(),
                model,
                custom_llm_provider="predibase",
                logging_obj=logging_obj,
            )
            return _response
        ### SYNC COMPLETION
        else:
            response = litellm.module_level_client.post(
                url=completion_url,
                headers=headers,
                data=json.dumps(data),
                timeout=timeout,  # type: ignore
            )
        return self.process_response(
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

    async def async_completion(
        self,
        model: str,
        messages: list,
        api_base: str,
        model_response: ModelResponse,
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
    ) -> ModelResponse:
        async_handler = get_async_httpx_client(
            llm_provider=litellm.LlmProviders.PREDIBASE,
            params={"timeout": timeout},
        )
        try:
            response = await async_handler.post(
                api_base, headers=headers, data=json.dumps(data)
            )
        except httpx.HTTPStatusError as e:
            raise PredibaseError(
                status_code=e.response.status_code,
                message="HTTPStatusError - received status_code={}, error_message={}".format(
                    e.response.status_code, e.response.text
                ),
            )
        except Exception as e:
            for exception in litellm.LITELLM_EXCEPTION_TYPES:
                if isinstance(e, exception):
                    raise e
            raise PredibaseError(
                status_code=500, message="{}".format(str(e))
            )  # don't use verbose_logger.exception, if exception is raised
        return self.process_response(
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

    async def async_streaming(
        self,
        model: str,
        messages: list,
        api_base: str,
        model_response: ModelResponse,
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
                timeout=timeout,
            ),
            model=model,
            custom_llm_provider="predibase",
            logging_obj=logging_obj,
        )
        return streamwrapper

    def embedding(self, *args, **kwargs):
        pass

# === NexusCore/openenv\Lib\site-packages\setuptools\_distutils\fancy_getopt.py ===
"""distutils.fancy_getopt

Wrapper around the standard getopt module that provides the following
additional features:
  * short and long options are tied together
  * options have help strings, so fancy_getopt could potentially
    create a complete usage summary
  * options set attributes of a passed-in object
"""

from __future__ import annotations

import getopt
import re
import string
import sys
from collections.abc import Sequence
from typing import Any

from .errors import DistutilsArgError, DistutilsGetoptError

# Much like command_re in distutils.core, this is close to but not quite
# the same as a Python NAME -- except, in the spirit of most GNU
# utilities, we use '-' in place of '_'.  (The spirit of LISP lives on!)
# The similarities to NAME are again not a coincidence...
longopt_pat = r'[a-zA-Z](?:[a-zA-Z0-9-]*)'
longopt_re = re.compile(rf'^{longopt_pat}$')

# For recognizing "negative alias" options, eg. "quiet=!verbose"
neg_alias_re = re.compile(f"^({longopt_pat})=!({longopt_pat})$")

# This is used to translate long options to legitimate Python identifiers
# (for use as attributes of some object).
longopt_xlate = str.maketrans('-', '_')


class FancyGetopt:
    """Wrapper around the standard 'getopt()' module that provides some
    handy extra functionality:
      * short and long options are tied together
      * options have help strings, and help text can be assembled
        from them
      * options set attributes of a passed-in object
      * boolean options can have "negative aliases" -- eg. if
        --quiet is the "negative alias" of --verbose, then "--quiet"
        on the command line sets 'verbose' to false
    """

    def __init__(self, option_table=None):
        # The option table is (currently) a list of tuples.  The
        # tuples may have 3 or four values:
        #   (long_option, short_option, help_string [, repeatable])
        # if an option takes an argument, its long_option should have '='
        # appended; short_option should just be a single character, no ':'
        # in any case.  If a long_option doesn't have a corresponding
        # short_option, short_option should be None.  All option tuples
        # must have long options.
        self.option_table = option_table

        # 'option_index' maps long option names to entries in the option
        # table (ie. those 3-tuples).
        self.option_index = {}
        if self.option_table:
            self._build_index()

        # 'alias' records (duh) alias options; {'foo': 'bar'} means
        # --foo is an alias for --bar
        self.alias = {}

        # 'negative_alias' keeps track of options that are the boolean
        # opposite of some other option
        self.negative_alias = {}

        # These keep track of the information in the option table.  We
        # don't actually populate these structures until we're ready to
        # parse the command-line, since the 'option_table' passed in here
        # isn't necessarily the final word.
        self.short_opts = []
        self.long_opts = []
        self.short2long = {}
        self.attr_name = {}
        self.takes_arg = {}

        # And 'option_order' is filled up in 'getopt()'; it records the
        # original order of options (and their values) on the command-line,
        # but expands short options, converts aliases, etc.
        self.option_order = []

    def _build_index(self):
        self.option_index.clear()
        for option in self.option_table:
            self.option_index[option[0]] = option

    def set_option_table(self, option_table):
        self.option_table = option_table
        self._build_index()

    def add_option(self, long_option, short_option=None, help_string=None):
        if long_option in self.option_index:
            raise DistutilsGetoptError(
                f"option conflict: already an option '{long_option}'"
            )
        else:
            option = (long_option, short_option, help_string)
            self.option_table.append(option)
            self.option_index[long_option] = option

    def has_option(self, long_option):
        """Return true if the option table for this parser has an
        option with long name 'long_option'."""
        return long_option in self.option_index

    def get_attr_name(self, long_option):
        """Translate long option name 'long_option' to the form it
        has as an attribute of some object: ie., translate hyphens
        to underscores."""
        return long_option.translate(longopt_xlate)

    def _check_alias_dict(self, aliases, what):
        assert isinstance(aliases, dict)
        for alias, opt in aliases.items():
            if alias not in self.option_index:
                raise DistutilsGetoptError(
                    f"invalid {what} '{alias}': option '{alias}' not defined"
                )
            if opt not in self.option_index:
                raise DistutilsGetoptError(
                    f"invalid {what} '{alias}': aliased option '{opt}' not defined"
                )

    def set_aliases(self, alias):
        """Set the aliases for this option parser."""
        self._check_alias_dict(alias, "alias")
        self.alias = alias

    def set_negative_aliases(self, negative_alias):
        """Set the negative aliases for this option parser.
        'negative_alias' should be a dictionary mapping option names to
        option names, both the key and value must already be defined
        in the option table."""
        self._check_alias_dict(negative_alias, "negative alias")
        self.negative_alias = negative_alias

    def _grok_option_table(self):  # noqa: C901
        """Populate the various data structures that keep tabs on the
        option table.  Called by 'getopt()' before it can do anything
        worthwhile.
        """
        self.long_opts = []
        self.short_opts = []
        self.short2long.clear()
        self.repeat = {}

        for option in self.option_table:
            if len(option) == 3:
                long, short, help = option
                repeat = 0
            elif len(option) == 4:
                long, short, help, repeat = option
            else:
                # the option table is part of the code, so simply
                # assert that it is correct
                raise ValueError(f"invalid option tuple: {option!r}")

            # Type- and value-check the option names
            if not isinstance(long, str) or len(long) < 2:
                raise DistutilsGetoptError(
                    f"invalid long option '{long}': must be a string of length >= 2"
                )

            if not ((short is None) or (isinstance(short, str) and len(short) == 1)):
                raise DistutilsGetoptError(
                    f"invalid short option '{short}': must a single character or None"
                )

            self.repeat[long] = repeat
            self.long_opts.append(long)

            if long[-1] == '=':  # option takes an argument?
                if short:
                    short = short + ':'
                long = long[0:-1]
                self.takes_arg[long] = True
            else:
                # Is option is a "negative alias" for some other option (eg.
                # "quiet" == "!verbose")?
                alias_to = self.negative_alias.get(long)
                if alias_to is not None:
                    if self.takes_arg[alias_to]:
                        raise DistutilsGetoptError(
                            f"invalid negative alias '{long}': "
                            f"aliased option '{alias_to}' takes a value"
                        )

                    self.long_opts[-1] = long  # XXX redundant?!
                self.takes_arg[long] = False

            # If this is an alias option, make sure its "takes arg" flag is
            # the same as the option it's aliased to.
            alias_to = self.alias.get(long)
            if alias_to is not None:
                if self.takes_arg[long] != self.takes_arg[alias_to]:
                    raise DistutilsGetoptError(
                        f"invalid alias '{long}': inconsistent with "
                        f"aliased option '{alias_to}' (one of them takes a value, "
                        "the other doesn't"
                    )

            # Now enforce some bondage on the long option name, so we can
            # later translate it to an attribute name on some object.  Have
            # to do this a bit late to make sure we've removed any trailing
            # '='.
            if not longopt_re.match(long):
                raise DistutilsGetoptError(
                    f"invalid long option name '{long}' "
                    "(must be letters, numbers, hyphens only"
                )

            self.attr_name[long] = self.get_attr_name(long)
            if short:
                self.short_opts.append(short)
                self.short2long[short[0]] = long

    def getopt(self, args: Sequence[str] | None = None, object=None):  # noqa: C901
        """Parse command-line options in args. Store as attributes on object.

        If 'args' is None or not supplied, uses 'sys.argv[1:]'.  If
        'object' is None or not supplied, creates a new OptionDummy
        object, stores option values there, and returns a tuple (args,
        object).  If 'object' is supplied, it is modified in place and
        'getopt()' just returns 'args'; in both cases, the returned
        'args' is a modified copy of the passed-in 'args' list, which
        is left untouched.
        """
        if args is None:
            args = sys.argv[1:]
        if object is None:
            object = OptionDummy()
            created_object = True
        else:
            created_object = False

        self._grok_option_table()

        short_opts = ' '.join(self.short_opts)
        try:
            opts, args = getopt.getopt(args, short_opts, self.long_opts)
        except getopt.error as msg:
            raise DistutilsArgError(msg)

        for opt, val in opts:
            if len(opt) == 2 and opt[0] == '-':  # it's a short option
                opt = self.short2long[opt[1]]
            else:
                assert len(opt) > 2 and opt[:2] == '--'
                opt = opt[2:]

            alias = self.alias.get(opt)
            if alias:
                opt = alias

            if not self.takes_arg[opt]:  # boolean option?
                assert val == '', "boolean option can't have value"
                alias = self.negative_alias.get(opt)
                if alias:
                    opt = alias
                    val = 0
                else:
                    val = 1

            attr = self.attr_name[opt]
            # The only repeating option at the moment is 'verbose'.
            # It has a negative option -q quiet, which should set verbose = False.
            if val and self.repeat.get(attr) is not None:
                val = getattr(object, attr, 0) + 1
            setattr(object, attr, val)
            self.option_order.append((opt, val))

        # for opts
        if created_object:
            return args, object
        else:
            return args

    def get_option_order(self):
        """Returns the list of (option, value) tuples processed by the
        previous run of 'getopt()'.  Raises RuntimeError if
        'getopt()' hasn't been called yet.
        """
        if self.option_order is None:
            raise RuntimeError("'getopt()' hasn't been called yet")
        else:
            return self.option_order

    def generate_help(self, header=None):  # noqa: C901
        """Generate help text (a list of strings, one per suggested line of
        output) from the option table for this FancyGetopt object.
        """
        # Blithely assume the option table is good: probably wouldn't call
        # 'generate_help()' unless you've already called 'getopt()'.

        # First pass: determine maximum length of long option names
        max_opt = 0
        for option in self.option_table:
            long = option[0]
            short = option[1]
            ell = len(long)
            if long[-1] == '=':
                ell = ell - 1
            if short is not None:
                ell = ell + 5  # " (-x)" where short == 'x'
            if ell > max_opt:
                max_opt = ell

        opt_width = max_opt + 2 + 2 + 2  # room for indent + dashes + gutter

        # Typical help block looks like this:
        #   --foo       controls foonabulation
        # Help block for longest option looks like this:
        #   --flimflam  set the flim-flam level
        # and with wrapped text:
        #   --flimflam  set the flim-flam level (must be between
        #               0 and 100, except on Tuesdays)
        # Options with short names will have the short name shown (but
        # it doesn't contribute to max_opt):
        #   --foo (-f)  controls foonabulation
        # If adding the short option would make the left column too wide,
        # we push the explanation off to the next line
        #   --flimflam (-l)
        #               set the flim-flam level
        # Important parameters:
        #   - 2 spaces before option block start lines
        #   - 2 dashes for each long option name
        #   - min. 2 spaces between option and explanation (gutter)
        #   - 5 characters (incl. space) for short option name

        # Now generate lines of help text.  (If 80 columns were good enough
        # for Jesus, then 78 columns are good enough for me!)
        line_width = 78
        text_width = line_width - opt_width
        big_indent = ' ' * opt_width
        if header:
            lines = [header]
        else:
            lines = ['Option summary:']

        for option in self.option_table:
            long, short, help = option[:3]
            text = wrap_text(help, text_width)
            if long[-1] == '=':
                long = long[0:-1]

            # Case 1: no short option at all (makes life easy)
            if short is None:
                if text:
                    lines.append(f"  --{long:<{max_opt}}  {text[0]}")
                else:
                    lines.append(f"  --{long:<{max_opt}}")

            # Case 2: we have a short option, so we have to include it
            # just after the long option
            else:
                opt_names = f"{long} (-{short})"
                if text:
                    lines.append(f"  --{opt_names:<{max_opt}}  {text[0]}")
                else:
                    lines.append(f"  --{opt_names:<{max_opt}}")

            for ell in text[1:]:
                lines.append(big_indent + ell)
        return lines

    def print_help(self, header=None, file=None):
        if file is None:
            file = sys.stdout
        for line in self.generate_help(header):
            file.write(line + "\n")


def fancy_getopt(options, negative_opt, object, args: Sequence[str] | None):
    parser = FancyGetopt(options)
    parser.set_negative_aliases(negative_opt)
    return parser.getopt(args, object)


WS_TRANS = {ord(_wschar): ' ' for _wschar in string.whitespace}


def wrap_text(text, width):
    """wrap_text(text : string, width : int) -> [string]

    Split 'text' into multiple lines of no more than 'width' characters
    each, and return the list of strings that results.
    """
    if text is None:
        return []
    if len(text) <= width:
        return [text]

    text = text.expandtabs()
    text = text.translate(WS_TRANS)
    chunks = re.split(r'( +|-+)', text)
    chunks = [ch for ch in chunks if ch]  # ' - ' results in empty strings
    lines = []

    while chunks:
        cur_line = []  # list of chunks (to-be-joined)
        cur_len = 0  # length of current line

        while chunks:
            ell = len(chunks[0])
            if cur_len + ell <= width:  # can squeeze (at least) this chunk in
                cur_line.append(chunks[0])
                del chunks[0]
                cur_len = cur_len + ell
            else:  # this line is full
                # drop last chunk if all space
                if cur_line and cur_line[-1][0] == ' ':
                    del cur_line[-1]
                break

        if chunks:  # any chunks left to process?
            # if the current line is still empty, then we had a single
            # chunk that's too big too fit on a line -- so we break
            # down and break it up at the line width
            if cur_len == 0:
                cur_line.append(chunks[0][0:width])
                chunks[0] = chunks[0][width:]

            # all-whitespace chunks at the end of a line can be discarded
            # (and we know from the re.split above that if a chunk has
            # *any* whitespace, it is *all* whitespace)
            if chunks[0][0] == ' ':
                del chunks[0]

        # and store this line in the list-of-all-lines -- as a single
        # string, of course!
        lines.append(''.join(cur_line))

    return lines


def translate_longopt(opt):
    """Convert a long option name to a valid Python identifier by
    changing "-" to "_".
    """
    return opt.translate(longopt_xlate)


class OptionDummy:
    """Dummy class just used as a place to hold command-line option
    values as instance attributes."""

    def __init__(self, options: Sequence[Any] = []):
        """Create a new OptionDummy instance.  The attributes listed in
        'options' will be initialized to None."""
        for opt in options:
            setattr(self, opt, None)


if __name__ == "__main__":
    text = """\
Tra-la-la, supercalifragilisticexpialidocious.
How *do* you spell that odd word, anyways?
(Someone ask Mary -- she'll know [or she'll
say, "How should I know?"].)"""

    for w in (10, 20, 30, 40):
        print(f"width: {w}")
        print("\n".join(wrap_text(text, w)))
        print()

# === NexusCore/openenv\Lib\site-packages\aiohttp\tracing.py ===
from types import SimpleNamespace
from typing import TYPE_CHECKING, Awaitable, Mapping, Optional, Protocol, Type, TypeVar

import attr
from aiosignal import Signal
from multidict import CIMultiDict
from yarl import URL

from .client_reqrep import ClientResponse

if TYPE_CHECKING:
    from .client import ClientSession

    _ParamT_contra = TypeVar("_ParamT_contra", contravariant=True)

    class _SignalCallback(Protocol[_ParamT_contra]):
        def __call__(
            self,
            __client_session: ClientSession,
            __trace_config_ctx: SimpleNamespace,
            __params: _ParamT_contra,
        ) -> Awaitable[None]: ...


__all__ = (
    "TraceConfig",
    "TraceRequestStartParams",
    "TraceRequestEndParams",
    "TraceRequestExceptionParams",
    "TraceConnectionQueuedStartParams",
    "TraceConnectionQueuedEndParams",
    "TraceConnectionCreateStartParams",
    "TraceConnectionCreateEndParams",
    "TraceConnectionReuseconnParams",
    "TraceDnsResolveHostStartParams",
    "TraceDnsResolveHostEndParams",
    "TraceDnsCacheHitParams",
    "TraceDnsCacheMissParams",
    "TraceRequestRedirectParams",
    "TraceRequestChunkSentParams",
    "TraceResponseChunkReceivedParams",
    "TraceRequestHeadersSentParams",
)


class TraceConfig:
    """First-class used to trace requests launched via ClientSession objects."""

    def __init__(
        self, trace_config_ctx_factory: Type[SimpleNamespace] = SimpleNamespace
    ) -> None:
        self._on_request_start: Signal[_SignalCallback[TraceRequestStartParams]] = (
            Signal(self)
        )
        self._on_request_chunk_sent: Signal[
            _SignalCallback[TraceRequestChunkSentParams]
        ] = Signal(self)
        self._on_response_chunk_received: Signal[
            _SignalCallback[TraceResponseChunkReceivedParams]
        ] = Signal(self)
        self._on_request_end: Signal[_SignalCallback[TraceRequestEndParams]] = Signal(
            self
        )
        self._on_request_exception: Signal[
            _SignalCallback[TraceRequestExceptionParams]
        ] = Signal(self)
        self._on_request_redirect: Signal[
            _SignalCallback[TraceRequestRedirectParams]
        ] = Signal(self)
        self._on_connection_queued_start: Signal[
            _SignalCallback[TraceConnectionQueuedStartParams]
        ] = Signal(self)
        self._on_connection_queued_end: Signal[
            _SignalCallback[TraceConnectionQueuedEndParams]
        ] = Signal(self)
        self._on_connection_create_start: Signal[
            _SignalCallback[TraceConnectionCreateStartParams]
        ] = Signal(self)
        self._on_connection_create_end: Signal[
            _SignalCallback[TraceConnectionCreateEndParams]
        ] = Signal(self)
        self._on_connection_reuseconn: Signal[
            _SignalCallback[TraceConnectionReuseconnParams]
        ] = Signal(self)
        self._on_dns_resolvehost_start: Signal[
            _SignalCallback[TraceDnsResolveHostStartParams]
        ] = Signal(self)
        self._on_dns_resolvehost_end: Signal[
            _SignalCallback[TraceDnsResolveHostEndParams]
        ] = Signal(self)
        self._on_dns_cache_hit: Signal[_SignalCallback[TraceDnsCacheHitParams]] = (
            Signal(self)
        )
        self._on_dns_cache_miss: Signal[_SignalCallback[TraceDnsCacheMissParams]] = (
            Signal(self)
        )
        self._on_request_headers_sent: Signal[
            _SignalCallback[TraceRequestHeadersSentParams]
        ] = Signal(self)

        self._trace_config_ctx_factory = trace_config_ctx_factory

    def trace_config_ctx(
        self, trace_request_ctx: Optional[Mapping[str, str]] = None
    ) -> SimpleNamespace:
        """Return a new trace_config_ctx instance"""
        return self._trace_config_ctx_factory(trace_request_ctx=trace_request_ctx)

    def freeze(self) -> None:
        self._on_request_start.freeze()
        self._on_request_chunk_sent.freeze()
        self._on_response_chunk_received.freeze()
        self._on_request_end.freeze()
        self._on_request_exception.freeze()
        self._on_request_redirect.freeze()
        self._on_connection_queued_start.freeze()
        self._on_connection_queued_end.freeze()
        self._on_connection_create_start.freeze()
        self._on_connection_create_end.freeze()
        self._on_connection_reuseconn.freeze()
        self._on_dns_resolvehost_start.freeze()
        self._on_dns_resolvehost_end.freeze()
        self._on_dns_cache_hit.freeze()
        self._on_dns_cache_miss.freeze()
        self._on_request_headers_sent.freeze()

    @property
    def on_request_start(self) -> "Signal[_SignalCallback[TraceRequestStartParams]]":
        return self._on_request_start

    @property
    def on_request_chunk_sent(
        self,
    ) -> "Signal[_SignalCallback[TraceRequestChunkSentParams]]":
        return self._on_request_chunk_sent

    @property
    def on_response_chunk_received(
        self,
    ) -> "Signal[_SignalCallback[TraceResponseChunkReceivedParams]]":
        return self._on_response_chunk_received

    @property
    def on_request_end(self) -> "Signal[_SignalCallback[TraceRequestEndParams]]":
        return self._on_request_end

    @property
    def on_request_exception(
        self,
    ) -> "Signal[_SignalCallback[TraceRequestExceptionParams]]":
        return self._on_request_exception

    @property
    def on_request_redirect(
        self,
    ) -> "Signal[_SignalCallback[TraceRequestRedirectParams]]":
        return self._on_request_redirect

    @property
    def on_connection_queued_start(
        self,
    ) -> "Signal[_SignalCallback[TraceConnectionQueuedStartParams]]":
        return self._on_connection_queued_start

    @property
    def on_connection_queued_end(
        self,
    ) -> "Signal[_SignalCallback[TraceConnectionQueuedEndParams]]":
        return self._on_connection_queued_end

    @property
    def on_connection_create_start(
        self,
    ) -> "Signal[_SignalCallback[TraceConnectionCreateStartParams]]":
        return self._on_connection_create_start

    @property
    def on_connection_create_end(
        self,
    ) -> "Signal[_SignalCallback[TraceConnectionCreateEndParams]]":
        return self._on_connection_create_end

    @property
    def on_connection_reuseconn(
        self,
    ) -> "Signal[_SignalCallback[TraceConnectionReuseconnParams]]":
        return self._on_connection_reuseconn

    @property
    def on_dns_resolvehost_start(
        self,
    ) -> "Signal[_SignalCallback[TraceDnsResolveHostStartParams]]":
        return self._on_dns_resolvehost_start

    @property
    def on_dns_resolvehost_end(
        self,
    ) -> "Signal[_SignalCallback[TraceDnsResolveHostEndParams]]":
        return self._on_dns_resolvehost_end

    @property
    def on_dns_cache_hit(self) -> "Signal[_SignalCallback[TraceDnsCacheHitParams]]":
        return self._on_dns_cache_hit

    @property
    def on_dns_cache_miss(self) -> "Signal[_SignalCallback[TraceDnsCacheMissParams]]":
        return self._on_dns_cache_miss

    @property
    def on_request_headers_sent(
        self,
    ) -> "Signal[_SignalCallback[TraceRequestHeadersSentParams]]":
        return self._on_request_headers_sent


@attr.s(auto_attribs=True, frozen=True, slots=True)
class TraceRequestStartParams:
    """Parameters sent by the `on_request_start` signal"""

    method: str
    url: URL
    headers: "CIMultiDict[str]"


@attr.s(auto_attribs=True, frozen=True, slots=True)
class TraceRequestChunkSentParams:
    """Parameters sent by the `on_request_chunk_sent` signal"""

    method: str
    url: URL
    chunk: bytes


@attr.s(auto_attribs=True, frozen=True, slots=True)
class TraceResponseChunkReceivedParams:
    """Parameters sent by the `on_response_chunk_received` signal"""

    method: str
    url: URL
    chunk: bytes


@attr.s(auto_attribs=True, frozen=True, slots=True)
class TraceRequestEndParams:
    """Parameters sent by the `on_request_end` signal"""

    method: str
    url: URL
    headers: "CIMultiDict[str]"
    response: ClientResponse


@attr.s(auto_attribs=True, frozen=True, slots=True)
class TraceRequestExceptionParams:
    """Parameters sent by the `on_request_exception` signal"""

    method: str
    url: URL
    headers: "CIMultiDict[str]"
    exception: BaseException


@attr.s(auto_attribs=True, frozen=True, slots=True)
class TraceRequestRedirectParams:
    """Parameters sent by the `on_request_redirect` signal"""

    method: str
    url: URL
    headers: "CIMultiDict[str]"
    response: ClientResponse


@attr.s(auto_attribs=True, frozen=True, slots=True)
class TraceConnectionQueuedStartParams:
    """Parameters sent by the `on_connection_queued_start` signal"""


@attr.s(auto_attribs=True, frozen=True, slots=True)
class TraceConnectionQueuedEndParams:
    """Parameters sent by the `on_connection_queued_end` signal"""


@attr.s(auto_attribs=True, frozen=True, slots=True)
class TraceConnectionCreateStartParams:
    """Parameters sent by the `on_connection_create_start` signal"""


@attr.s(auto_attribs=True, frozen=True, slots=True)
class TraceConnectionCreateEndParams:
    """Parameters sent by the `on_connection_create_end` signal"""


@attr.s(auto_attribs=True, frozen=True, slots=True)
class TraceConnectionReuseconnParams:
    """Parameters sent by the `on_connection_reuseconn` signal"""


@attr.s(auto_attribs=True, frozen=True, slots=True)
class TraceDnsResolveHostStartParams:
    """Parameters sent by the `on_dns_resolvehost_start` signal"""

    host: str


@attr.s(auto_attribs=True, frozen=True, slots=True)
class TraceDnsResolveHostEndParams:
    """Parameters sent by the `on_dns_resolvehost_end` signal"""

    host: str


@attr.s(auto_attribs=True, frozen=True, slots=True)
class TraceDnsCacheHitParams:
    """Parameters sent by the `on_dns_cache_hit` signal"""

    host: str


@attr.s(auto_attribs=True, frozen=True, slots=True)
class TraceDnsCacheMissParams:
    """Parameters sent by the `on_dns_cache_miss` signal"""

    host: str


@attr.s(auto_attribs=True, frozen=True, slots=True)
class TraceRequestHeadersSentParams:
    """Parameters sent by the `on_request_headers_sent` signal"""

    method: str
    url: URL
    headers: "CIMultiDict[str]"


class Trace:
    """Internal dependency holder class.

    Used to keep together the main dependencies used
    at the moment of send a signal.
    """

    def __init__(
        self,
        session: "ClientSession",
        trace_config: TraceConfig,
        trace_config_ctx: SimpleNamespace,
    ) -> None:
        self._trace_config = trace_config
        self._trace_config_ctx = trace_config_ctx
        self._session = session

    async def send_request_start(
        self, method: str, url: URL, headers: "CIMultiDict[str]"
    ) -> None:
        return await self._trace_config.on_request_start.send(
            self._session,
            self._trace_config_ctx,
            TraceRequestStartParams(method, url, headers),
        )

    async def send_request_chunk_sent(
        self, method: str, url: URL, chunk: bytes
    ) -> None:
        return await self._trace_config.on_request_chunk_sent.send(
            self._session,
            self._trace_config_ctx,
            TraceRequestChunkSentParams(method, url, chunk),
        )

    async def send_response_chunk_received(
        self, method: str, url: URL, chunk: bytes
    ) -> None:
        return await self._trace_config.on_response_chunk_received.send(
            self._session,
            self._trace_config_ctx,
            TraceResponseChunkReceivedParams(method, url, chunk),
        )

    async def send_request_end(
        self,
        method: str,
        url: URL,
        headers: "CIMultiDict[str]",
        response: ClientResponse,
    ) -> None:
        return await self._trace_config.on_request_end.send(
            self._session,
            self._trace_config_ctx,
            TraceRequestEndParams(method, url, headers, response),
        )

    async def send_request_exception(
        self,
        method: str,
        url: URL,
        headers: "CIMultiDict[str]",
        exception: BaseException,
    ) -> None:
        return await self._trace_config.on_request_exception.send(
            self._session,
            self._trace_config_ctx,
            TraceRequestExceptionParams(method, url, headers, exception),
        )

    async def send_request_redirect(
        self,
        method: str,
        url: URL,
        headers: "CIMultiDict[str]",
        response: ClientResponse,
    ) -> None:
        return await self._trace_config._on_request_redirect.send(
            self._session,
            self._trace_config_ctx,
            TraceRequestRedirectParams(method, url, headers, response),
        )

    async def send_connection_queued_start(self) -> None:
        return await self._trace_config.on_connection_queued_start.send(
            self._session, self._trace_config_ctx, TraceConnectionQueuedStartParams()
        )

    async def send_connection_queued_end(self) -> None:
        return await self._trace_config.on_connection_queued_end.send(
            self._session, self._trace_config_ctx, TraceConnectionQueuedEndParams()
        )

    async def send_connection_create_start(self) -> None:
        return await self._trace_config.on_connection_create_start.send(
            self._session, self._trace_config_ctx, TraceConnectionCreateStartParams()
        )

    async def send_connection_create_end(self) -> None:
        return await self._trace_config.on_connection_create_end.send(
            self._session, self._trace_config_ctx, TraceConnectionCreateEndParams()
        )

    async def send_connection_reuseconn(self) -> None:
        return await self._trace_config.on_connection_reuseconn.send(
            self._session, self._trace_config_ctx, TraceConnectionReuseconnParams()
        )

    async def send_dns_resolvehost_start(self, host: str) -> None:
        return await self._trace_config.on_dns_resolvehost_start.send(
            self._session, self._trace_config_ctx, TraceDnsResolveHostStartParams(host)
        )

    async def send_dns_resolvehost_end(self, host: str) -> None:
        return await self._trace_config.on_dns_resolvehost_end.send(
            self._session, self._trace_config_ctx, TraceDnsResolveHostEndParams(host)
        )

    async def send_dns_cache_hit(self, host: str) -> None:
        return await self._trace_config.on_dns_cache_hit.send(
            self._session, self._trace_config_ctx, TraceDnsCacheHitParams(host)
        )

    async def send_dns_cache_miss(self, host: str) -> None:
        return await self._trace_config.on_dns_cache_miss.send(
            self._session, self._trace_config_ctx, TraceDnsCacheMissParams(host)
        )

    async def send_request_headers(
        self, method: str, url: URL, headers: "CIMultiDict[str]"
    ) -> None:
        return await self._trace_config._on_request_headers_sent.send(
            self._session,
            self._trace_config_ctx,
            TraceRequestHeadersSentParams(method, url, headers),
        )

# === NexusCore/openenv\Lib\site-packages\setuptools\command\build_ext.py ===
from __future__ import annotations

import itertools
import os
import sys
import textwrap
from collections.abc import Iterator
from importlib.machinery import EXTENSION_SUFFIXES
from importlib.util import cache_from_source as _compiled_file_name
from pathlib import Path
from typing import TYPE_CHECKING

from setuptools.dist import Distribution
from setuptools.errors import BaseError
from setuptools.extension import Extension, Library

from distutils import log
from distutils.ccompiler import new_compiler
from distutils.sysconfig import customize_compiler, get_config_var

if TYPE_CHECKING:
    # Cython not installed on CI tests, causing _build_ext to be `Any`
    from distutils.command.build_ext import build_ext as _build_ext
else:
    try:
        # Attempt to use Cython for building extensions, if available
        from Cython.Distutils.build_ext import build_ext as _build_ext

        # Additionally, assert that the compiler module will load
        # also. Ref #1229.
        __import__('Cython.Compiler.Main')
    except ImportError:
        from distutils.command.build_ext import build_ext as _build_ext

# make sure _config_vars is initialized
get_config_var("LDSHARED")
# Not publicly exposed in typeshed distutils stubs, but this is done on purpose
# See https://github.com/pypa/setuptools/pull/4228#issuecomment-1959856400
from distutils.sysconfig import _config_vars as _CONFIG_VARS  # noqa: E402


def _customize_compiler_for_shlib(compiler):
    if sys.platform == "darwin":
        # building .dylib requires additional compiler flags on OSX; here we
        # temporarily substitute the pyconfig.h variables so that distutils'
        # 'customize_compiler' uses them before we build the shared libraries.
        tmp = _CONFIG_VARS.copy()
        try:
            # XXX Help!  I don't have any idea whether these are right...
            _CONFIG_VARS['LDSHARED'] = (
                "gcc -Wl,-x -dynamiclib -undefined dynamic_lookup"
            )
            _CONFIG_VARS['CCSHARED'] = " -dynamiclib"
            _CONFIG_VARS['SO'] = ".dylib"
            customize_compiler(compiler)
        finally:
            _CONFIG_VARS.clear()
            _CONFIG_VARS.update(tmp)
    else:
        customize_compiler(compiler)


have_rtld = False
use_stubs = False
libtype = 'shared'

if sys.platform == "darwin":
    use_stubs = True
elif os.name != 'nt':
    try:
        import dl  # type: ignore[import-not-found] # https://github.com/python/mypy/issues/13002

        use_stubs = have_rtld = hasattr(dl, 'RTLD_NOW')
    except ImportError:
        pass


def get_abi3_suffix():
    """Return the file extension for an abi3-compliant Extension()"""
    for suffix in EXTENSION_SUFFIXES:
        if '.abi3' in suffix:  # Unix
            return suffix
        elif suffix == '.pyd':  # Windows
            return suffix
    return None


class build_ext(_build_ext):
    distribution: Distribution  # override distutils.dist.Distribution with setuptools.dist.Distribution
    editable_mode = False
    inplace = False

    def run(self):
        """Build extensions in build directory, then copy if --inplace"""
        old_inplace, self.inplace = self.inplace, False
        _build_ext.run(self)
        self.inplace = old_inplace
        if old_inplace:
            self.copy_extensions_to_source()

    def _get_inplace_equivalent(self, build_py, ext: Extension) -> tuple[str, str]:
        fullname = self.get_ext_fullname(ext.name)
        filename = self.get_ext_filename(fullname)
        modpath = fullname.split('.')
        package = '.'.join(modpath[:-1])
        package_dir = build_py.get_package_dir(package)
        inplace_file = os.path.join(package_dir, os.path.basename(filename))
        regular_file = os.path.join(self.build_lib, filename)
        return (inplace_file, regular_file)

    def copy_extensions_to_source(self) -> None:
        build_py = self.get_finalized_command('build_py')
        for ext in self.extensions:
            inplace_file, regular_file = self._get_inplace_equivalent(build_py, ext)

            # Always copy, even if source is older than destination, to ensure
            # that the right extensions for the current Python/platform are
            # used.
            if os.path.exists(regular_file) or not ext.optional:
                self.copy_file(regular_file, inplace_file, level=self.verbose)

            if ext._needs_stub:
                inplace_stub = self._get_equivalent_stub(ext, inplace_file)
                self._write_stub_file(inplace_stub, ext, compile=True)
                # Always compile stub and remove the original (leave the cache behind)
                # (this behaviour was observed in previous iterations of the code)

    def _get_equivalent_stub(self, ext: Extension, output_file: str) -> str:
        dir_ = os.path.dirname(output_file)
        _, _, name = ext.name.rpartition(".")
        return f"{os.path.join(dir_, name)}.py"

    def _get_output_mapping(self) -> Iterator[tuple[str, str]]:
        if not self.inplace:
            return

        build_py = self.get_finalized_command('build_py')
        opt = self.get_finalized_command('install_lib').optimize or ""

        for ext in self.extensions:
            inplace_file, regular_file = self._get_inplace_equivalent(build_py, ext)
            yield (regular_file, inplace_file)

            if ext._needs_stub:
                # This version of `build_ext` always builds artifacts in another dir,
                # when "inplace=True" is given it just copies them back.
                # This is done in the `copy_extensions_to_source` function, which
                # always compile stub files via `_compile_and_remove_stub`.
                # At the end of the process, a `.pyc` stub file is created without the
                # corresponding `.py`.

                inplace_stub = self._get_equivalent_stub(ext, inplace_file)
                regular_stub = self._get_equivalent_stub(ext, regular_file)
                inplace_cache = _compiled_file_name(inplace_stub, optimization=opt)
                output_cache = _compiled_file_name(regular_stub, optimization=opt)
                yield (output_cache, inplace_cache)

    def get_ext_filename(self, fullname: str) -> str:
        so_ext = os.getenv('SETUPTOOLS_EXT_SUFFIX')
        if so_ext:
            filename = os.path.join(*fullname.split('.')) + so_ext
        else:
            filename = _build_ext.get_ext_filename(self, fullname)
            ext_suffix = get_config_var('EXT_SUFFIX')
            if not isinstance(ext_suffix, str):
                raise OSError(
                    "Configuration variable EXT_SUFFIX not found for this platform "
                    "and environment variable SETUPTOOLS_EXT_SUFFIX is missing"
                )
            so_ext = ext_suffix

        if fullname in self.ext_map:
            ext = self.ext_map[fullname]
            abi3_suffix = get_abi3_suffix()
            if ext.py_limited_api and abi3_suffix:  # Use abi3
                filename = filename[: -len(so_ext)] + abi3_suffix
            if isinstance(ext, Library):
                fn, ext = os.path.splitext(filename)
                return self.shlib_compiler.library_filename(fn, libtype)
            elif use_stubs and ext._links_to_dynamic:
                d, fn = os.path.split(filename)
                return os.path.join(d, 'dl-' + fn)
        return filename

    def initialize_options(self):
        _build_ext.initialize_options(self)
        self.shlib_compiler = None
        self.shlibs = []
        self.ext_map = {}
        self.editable_mode = False

    def finalize_options(self) -> None:
        _build_ext.finalize_options(self)
        self.extensions = self.extensions or []
        self.check_extensions_list(self.extensions)
        self.shlibs = [ext for ext in self.extensions if isinstance(ext, Library)]
        if self.shlibs:
            self.setup_shlib_compiler()
        for ext in self.extensions:
            ext._full_name = self.get_ext_fullname(ext.name)
        for ext in self.extensions:
            fullname = ext._full_name
            self.ext_map[fullname] = ext

            # distutils 3.1 will also ask for module names
            # XXX what to do with conflicts?
            self.ext_map[fullname.split('.')[-1]] = ext

            ltd = self.shlibs and self.links_to_dynamic(ext) or False
            ns = ltd and use_stubs and not isinstance(ext, Library)
            ext._links_to_dynamic = ltd
            ext._needs_stub = ns
            filename = ext._file_name = self.get_ext_filename(fullname)
            libdir = os.path.dirname(os.path.join(self.build_lib, filename))
            if ltd and libdir not in ext.library_dirs:
                ext.library_dirs.append(libdir)
            if ltd and use_stubs and os.curdir not in ext.runtime_library_dirs:
                ext.runtime_library_dirs.append(os.curdir)

        if self.editable_mode:
            self.inplace = True

    def setup_shlib_compiler(self):
        compiler = self.shlib_compiler = new_compiler(
            compiler=self.compiler, dry_run=self.dry_run, force=self.force
        )
        _customize_compiler_for_shlib(compiler)

        if self.include_dirs is not None:
            compiler.set_include_dirs(self.include_dirs)
        if self.define is not None:
            # 'define' option is a list of (name,value) tuples
            for name, value in self.define:
                compiler.define_macro(name, value)
        if self.undef is not None:
            for macro in self.undef:
                compiler.undefine_macro(macro)
        if self.libraries is not None:
            compiler.set_libraries(self.libraries)
        if self.library_dirs is not None:
            compiler.set_library_dirs(self.library_dirs)
        if self.rpath is not None:
            compiler.set_runtime_library_dirs(self.rpath)
        if self.link_objects is not None:
            compiler.set_link_objects(self.link_objects)

        # hack so distutils' build_extension() builds a library instead
        compiler.link_shared_object = link_shared_object.__get__(compiler)  # type: ignore[method-assign]

    def get_export_symbols(self, ext):
        if isinstance(ext, Library):
            return ext.export_symbols
        return _build_ext.get_export_symbols(self, ext)

    def build_extension(self, ext) -> None:
        ext._convert_pyx_sources_to_lang()
        _compiler = self.compiler
        try:
            if isinstance(ext, Library):
                self.compiler = self.shlib_compiler
            _build_ext.build_extension(self, ext)
            if ext._needs_stub:
                build_lib = self.get_finalized_command('build_py').build_lib
                self.write_stub(build_lib, ext)
        finally:
            self.compiler = _compiler

    def links_to_dynamic(self, ext):
        """Return true if 'ext' links to a dynamic lib in the same package"""
        # XXX this should check to ensure the lib is actually being built
        # XXX as dynamic, and not just using a locally-found version or a
        # XXX static-compiled version
        libnames = dict.fromkeys([lib._full_name for lib in self.shlibs])
        pkg = '.'.join(ext._full_name.split('.')[:-1] + [''])
        return any(pkg + libname in libnames for libname in ext.libraries)

    def get_source_files(self) -> list[str]:
        return [*_build_ext.get_source_files(self), *self._get_internal_depends()]

    def _get_internal_depends(self) -> Iterator[str]:
        """Yield ``ext.depends`` that are contained by the project directory"""
        project_root = Path(self.distribution.src_root or os.curdir).resolve()
        depends = (dep for ext in self.extensions for dep in ext.depends)

        def skip(orig_path: str, reason: str) -> None:
            log.info(
                "dependency %s won't be automatically "
                "included in the manifest: the path %s",
                orig_path,
                reason,
            )

        for dep in depends:
            path = Path(dep)

            if path.is_absolute():
                skip(dep, "must be relative")
                continue

            if ".." in path.parts:
                skip(dep, "can't have `..` segments")
                continue

            try:
                resolved = (project_root / path).resolve(strict=True)
            except OSError:
                skip(dep, "doesn't exist")
                continue

            try:
                resolved.relative_to(project_root)
            except ValueError:
                skip(dep, "must be inside the project root")
                continue

            yield path.as_posix()

    def get_outputs(self) -> list[str]:
        if self.inplace:
            return list(self.get_output_mapping().keys())
        return sorted(_build_ext.get_outputs(self) + self.__get_stubs_outputs())

    def get_output_mapping(self) -> dict[str, str]:
        """See :class:`setuptools.commands.build.SubCommand`"""
        mapping = self._get_output_mapping()
        return dict(sorted(mapping, key=lambda x: x[0]))

    def __get_stubs_outputs(self):
        # assemble the base name for each extension that needs a stub
        ns_ext_bases = (
            os.path.join(self.build_lib, *ext._full_name.split('.'))
            for ext in self.extensions
            if ext._needs_stub
        )
        # pair each base with the extension
        pairs = itertools.product(ns_ext_bases, self.__get_output_extensions())
        return list(base + fnext for base, fnext in pairs)

    def __get_output_extensions(self):
        yield '.py'
        yield '.pyc'
        if self.get_finalized_command('build_py').optimize:
            yield '.pyo'

    def write_stub(self, output_dir, ext, compile=False) -> None:
        stub_file = os.path.join(output_dir, *ext._full_name.split('.')) + '.py'
        self._write_stub_file(stub_file, ext, compile)

    def _write_stub_file(self, stub_file: str, ext: Extension, compile=False):
        log.info("writing stub loader for %s to %s", ext._full_name, stub_file)
        if compile and os.path.exists(stub_file):
            raise BaseError(stub_file + " already exists! Please delete.")
        if not self.dry_run:
            with open(stub_file, 'w', encoding="utf-8") as f:
                content = (
                    textwrap.dedent(f"""
                    def __bootstrap__():
                       global __bootstrap__, __file__, __loader__
                       import sys, os, importlib.resources as irs, importlib.util
                    #rtld   import dl
                       with irs.files(__name__).joinpath(
                         {os.path.basename(ext._file_name)!r}) as __file__:
                          del __bootstrap__
                          if '__loader__' in globals():
                              del __loader__
                    #rtld      old_flags = sys.getdlopenflags()
                          old_dir = os.getcwd()
                          try:
                            os.chdir(os.path.dirname(__file__))
                    #rtld        sys.setdlopenflags(dl.RTLD_NOW)
                            spec = importlib.util.spec_from_file_location(
                                       __name__, __file__)
                            mod = importlib.util.module_from_spec(spec)
                            spec.loader.exec_module(mod)
                          finally:
                    #rtld        sys.setdlopenflags(old_flags)
                            os.chdir(old_dir)
                    __bootstrap__()
                    """)
                    .lstrip()
                    .replace('#rtld', '#rtld' * (not have_rtld))
                )
                f.write(content)
        if compile:
            self._compile_and_remove_stub(stub_file)

    def _compile_and_remove_stub(self, stub_file: str):
        from distutils.util import byte_compile

        byte_compile([stub_file], optimize=0, force=True, dry_run=self.dry_run)
        optimize = self.get_finalized_command('install_lib').optimize
        if optimize > 0:
            byte_compile(
                [stub_file],
                optimize=optimize,
                force=True,
                dry_run=self.dry_run,
            )
        if os.path.exists(stub_file) and not self.dry_run:
            os.unlink(stub_file)


if use_stubs or os.name == 'nt':
    # Build shared libraries
    #
    def link_shared_object(
        self,
        objects,
        output_libname,
        output_dir=None,
        libraries=None,
        library_dirs=None,
        runtime_library_dirs=None,
        export_symbols=None,
        debug: bool = False,
        extra_preargs=None,
        extra_postargs=None,
        build_temp=None,
        target_lang=None,
    ) -> None:
        self.link(
            self.SHARED_LIBRARY,
            objects,
            output_libname,
            output_dir,
            libraries,
            library_dirs,
            runtime_library_dirs,
            export_symbols,
            debug,
            extra_preargs,
            extra_postargs,
            build_temp,
            target_lang,
        )

else:
    # Build static libraries everywhere else
    libtype = 'static'

    def link_shared_object(
        self,
        objects,
        output_libname,
        output_dir=None,
        libraries=None,
        library_dirs=None,
        runtime_library_dirs=None,
        export_symbols=None,
        debug: bool = False,
        extra_preargs=None,
        extra_postargs=None,
        build_temp=None,
        target_lang=None,
    ) -> None:
        # XXX we need to either disallow these attrs on Library instances,
        # or warn/abort here if set, or something...
        # libraries=None, library_dirs=None, runtime_library_dirs=None,
        # export_symbols=None, extra_preargs=None, extra_postargs=None,
        # build_temp=None

        assert output_dir is None  # distutils build_ext doesn't pass this
        output_dir, filename = os.path.split(output_libname)
        basename, _ext = os.path.splitext(filename)
        if self.library_filename("x").startswith('lib'):
            # strip 'lib' prefix; this is kludgy if some platform uses
            # a different prefix
            basename = basename[3:]

        self.create_static_lib(objects, basename, output_dir, debug, target_lang)

# === NexusCore/openenv\Lib\site-packages\pyasn1_modules\rfc3125.py ===
#
# This file is part of pyasn1-modules software.
#
# Created by Russ Housley with assistance from asn1ate v.0.6.0.
#
# Copyright (c) 2019, Vigil Security, LLC
# License: http://snmplabs.com/pyasn1/license.html
#
# Electronic Signature Policies
#
# ASN.1 source from:
# https://www.rfc-editor.org/rfc/rfc3125.txt
# https://www.rfc-editor.org/errata/eid5901
# https://www.rfc-editor.org/errata/eid5902
#

from pyasn1.type import constraint
from pyasn1.type import namedtype
from pyasn1.type import namedval
from pyasn1.type import tag
from pyasn1.type import useful
from pyasn1.type import univ

from pyasn1_modules import rfc5280

MAX = float('inf')


# Imports from RFC 5280

AlgorithmIdentifier = rfc5280.AlgorithmIdentifier

Attribute = rfc5280.Attribute

AttributeType = rfc5280.AttributeType

AttributeTypeAndValue = rfc5280.AttributeTypeAndValue

AttributeValue = rfc5280.AttributeValue

Certificate = rfc5280.Certificate

CertificateList = rfc5280.CertificateList

DirectoryString = rfc5280.DirectoryString

GeneralName = rfc5280.GeneralName

GeneralNames = rfc5280.GeneralNames

Name = rfc5280.Name

PolicyInformation = rfc5280.PolicyInformation


# Electronic Signature Policies

class CertPolicyId(univ.ObjectIdentifier):
    pass


class AcceptablePolicySet(univ.SequenceOf):
    componentType = CertPolicyId()


class SignPolExtn(univ.Sequence):
    componentType = namedtype.NamedTypes(
        namedtype.NamedType('extnID', univ.ObjectIdentifier()),
        namedtype.NamedType('extnValue', univ.OctetString())
    )


class SignPolExtensions(univ.SequenceOf):
    componentType = SignPolExtn()


class AlgAndLength(univ.Sequence):
    componentType = namedtype.NamedTypes(
        namedtype.NamedType('algID', univ.ObjectIdentifier()),
        namedtype.OptionalNamedType('minKeyLength', univ.Integer()),
        namedtype.OptionalNamedType('other', SignPolExtensions())
    )


class AlgorithmConstraints(univ.SequenceOf):
    componentType = AlgAndLength()


class AlgorithmConstraintSet(univ.Sequence):
    componentType = namedtype.NamedTypes(
        namedtype.OptionalNamedType('signerAlgorithmConstraints',
            AlgorithmConstraints().subtype(explicitTag=tag.Tag(
                tag.tagClassContext, tag.tagFormatSimple, 0))),
        namedtype.OptionalNamedType('eeCertAlgorithmConstraints',
            AlgorithmConstraints().subtype(explicitTag=tag.Tag(
                tag.tagClassContext, tag.tagFormatSimple, 1))),
        namedtype.OptionalNamedType('caCertAlgorithmConstraints',
            AlgorithmConstraints().subtype(explicitTag=tag.Tag(
                tag.tagClassContext, tag.tagFormatSimple, 2))),
        namedtype.OptionalNamedType('aaCertAlgorithmConstraints',
            AlgorithmConstraints().subtype(explicitTag=tag.Tag(
                tag.tagClassContext, tag.tagFormatSimple, 3))),
        namedtype.OptionalNamedType('tsaCertAlgorithmConstraints',
            AlgorithmConstraints().subtype(explicitTag=tag.Tag(
                tag.tagClassContext, tag.tagFormatSimple, 4)))
    )


class AttributeValueConstraints(univ.SequenceOf):
    componentType = AttributeTypeAndValue()


class AttributeTypeConstraints(univ.SequenceOf):
    componentType = AttributeType()


class AttributeConstraints(univ.Sequence):
    componentType = namedtype.NamedTypes(
        namedtype.OptionalNamedType('attributeTypeConstarints',
            AttributeTypeConstraints().subtype(explicitTag=tag.Tag(
                tag.tagClassContext, tag.tagFormatSimple, 0))),
        namedtype.OptionalNamedType('attributeValueConstarints',
            AttributeValueConstraints().subtype(explicitTag=tag.Tag(
                tag.tagClassContext, tag.tagFormatSimple, 1)))
    )


class HowCertAttribute(univ.Enumerated):
    namedValues = namedval.NamedValues(
        ('claimedAttribute', 0),
        ('certifiedAttribtes', 1),
        ('either', 2)
    )


class SkipCerts(univ.Integer):
    subtypeSpec = constraint.ValueRangeConstraint(0, MAX)


class PolicyConstraints(univ.Sequence):
    componentType = namedtype.NamedTypes(
        namedtype.OptionalNamedType('requireExplicitPolicy',
            SkipCerts().subtype(explicitTag=tag.Tag(
                tag.tagClassContext, tag.tagFormatSimple, 0))),
        namedtype.OptionalNamedType('inhibitPolicyMapping',
            SkipCerts().subtype(explicitTag=tag.Tag(
                tag.tagClassContext, tag.tagFormatSimple, 1)))
    )


class BaseDistance(univ.Integer):
    subtypeSpec = constraint.ValueRangeConstraint(0, MAX)


class GeneralSubtree(univ.Sequence):
    componentType = namedtype.NamedTypes(
        namedtype.NamedType('base', GeneralName()),
        namedtype.DefaultedNamedType('minimum',
            BaseDistance().subtype(explicitTag=tag.Tag(
                tag.tagClassContext, tag.tagFormatSimple, 0)).subtype(
                    value=0)),
        namedtype.OptionalNamedType('maximum',
            BaseDistance().subtype(explicitTag=tag.Tag(
                tag.tagClassContext, tag.tagFormatSimple, 1)))
    )


class GeneralSubtrees(univ.SequenceOf):
    componentType = GeneralSubtree()
    subtypeSpec = constraint.ValueSizeConstraint(1, MAX)


class NameConstraints(univ.Sequence):
    componentType = namedtype.NamedTypes(
        namedtype.OptionalNamedType('permittedSubtrees',
            GeneralSubtrees().subtype(explicitTag=tag.Tag(
                tag.tagClassContext, tag.tagFormatSimple, 0))),
        namedtype.OptionalNamedType('excludedSubtrees',
            GeneralSubtrees().subtype(explicitTag=tag.Tag(
                tag.tagClassContext, tag.tagFormatSimple, 1)))
    )


class PathLenConstraint(univ.Integer):
    subtypeSpec = constraint.ValueRangeConstraint(0, MAX)


class CertificateTrustPoint(univ.Sequence):
    componentType = namedtype.NamedTypes(
        namedtype.NamedType('trustpoint', Certificate()),
        namedtype.OptionalNamedType('pathLenConstraint',
            PathLenConstraint().subtype(explicitTag=tag.Tag(
                tag.tagClassContext, tag.tagFormatSimple, 0))),
        namedtype.OptionalNamedType('acceptablePolicySet',
            AcceptablePolicySet().subtype(explicitTag=tag.Tag(
                tag.tagClassContext, tag.tagFormatSimple, 1))),
        namedtype.OptionalNamedType('nameConstraints',
            NameConstraints().subtype(explicitTag=tag.Tag(
                tag.tagClassContext, tag.tagFormatConstructed, 2))),
        namedtype.OptionalNamedType('policyConstraints',
            PolicyConstraints().subtype(explicitTag=tag.Tag(
                tag.tagClassContext, tag.tagFormatConstructed, 3)))
    )


class CertificateTrustTrees(univ.SequenceOf):
    componentType = CertificateTrustPoint()


class EnuRevReq(univ.Enumerated):
    namedValues = namedval.NamedValues(
        ('clrCheck', 0),
        ('ocspCheck', 1),
        ('bothCheck', 2),
        ('eitherCheck', 3),
        ('noCheck', 4),
        ('other', 5)
    )


class RevReq(univ.Sequence):
    componentType = namedtype.NamedTypes(
        namedtype.NamedType('enuRevReq', EnuRevReq()),
        namedtype.OptionalNamedType('exRevReq', SignPolExtensions())
    )


class CertRevReq(univ.Sequence):
    componentType = namedtype.NamedTypes(
        namedtype.NamedType('endCertRevReq', RevReq()),
        namedtype.NamedType('caCerts',
            RevReq().subtype(explicitTag=tag.Tag(
                tag.tagClassContext, tag.tagFormatConstructed, 0)))
    )


class AttributeTrustCondition(univ.Sequence):
    componentType = namedtype.NamedTypes(
        namedtype.NamedType('attributeMandated', univ.Boolean()),
        namedtype.NamedType('howCertAttribute', HowCertAttribute()),
        namedtype.OptionalNamedType('attrCertificateTrustTrees',
            CertificateTrustTrees().subtype(explicitTag=tag.Tag(
                tag.tagClassContext, tag.tagFormatSimple, 0))),
        namedtype.OptionalNamedType('attrRevReq',
            CertRevReq().subtype(explicitTag=tag.Tag(
                tag.tagClassContext, tag.tagFormatConstructed, 1))),
        namedtype.OptionalNamedType('attributeConstraints',
            AttributeConstraints().subtype(explicitTag=tag.Tag(
                tag.tagClassContext, tag.tagFormatConstructed, 2)))
    )


class CMSAttrs(univ.SequenceOf):
    componentType = univ.ObjectIdentifier()


class CertInfoReq(univ.Enumerated):
    namedValues = namedval.NamedValues(
        ('none', 0),
        ('signerOnly', 1),
        ('fullPath', 2)
    )


class CertRefReq(univ.Enumerated):
    namedValues = namedval.NamedValues(
        ('signerOnly', 1),
        ('fullPath', 2)
    )


class DeltaTime(univ.Sequence):
    componentType = namedtype.NamedTypes(
        namedtype.NamedType('deltaSeconds', univ.Integer()),
        namedtype.NamedType('deltaMinutes', univ.Integer()),
        namedtype.NamedType('deltaHours', univ.Integer()),
        namedtype.NamedType('deltaDays', univ.Integer())
    )


class TimestampTrustCondition(univ.Sequence):
    componentType = namedtype.NamedTypes(
        namedtype.OptionalNamedType('ttsCertificateTrustTrees',
            CertificateTrustTrees().subtype(explicitTag=tag.Tag(
                tag.tagClassContext, tag.tagFormatSimple, 0))),
        namedtype.OptionalNamedType('ttsRevReq',
            CertRevReq().subtype(explicitTag=tag.Tag(
                tag.tagClassContext, tag.tagFormatConstructed, 1))),
        namedtype.OptionalNamedType('ttsNameConstraints',
            NameConstraints().subtype(explicitTag=tag.Tag(
                tag.tagClassContext, tag.tagFormatConstructed, 2))),
        namedtype.OptionalNamedType('cautionPeriod',
            DeltaTime().subtype(explicitTag=tag.Tag(
                tag.tagClassContext, tag.tagFormatConstructed, 3))),
        namedtype.OptionalNamedType('signatureTimestampDelay',
            DeltaTime().subtype(explicitTag=tag.Tag(
                tag.tagClassContext, tag.tagFormatConstructed, 4)))
    )


class SignerRules(univ.Sequence):
    componentType = namedtype.NamedTypes(
        namedtype.OptionalNamedType('externalSignedData', univ.Boolean()),
        namedtype.NamedType('mandatedSignedAttr', CMSAttrs()),
        namedtype.NamedType('mandatedUnsignedAttr', CMSAttrs()),
        namedtype.DefaultedNamedType('mandatedCertificateRef',
            CertRefReq().subtype(explicitTag=tag.Tag(
                tag.tagClassContext, tag.tagFormatSimple, 0)).subtype(
                    value='signerOnly')),
        namedtype.DefaultedNamedType('mandatedCertificateInfo',
            CertInfoReq().subtype(explicitTag=tag.Tag(
                tag.tagClassContext, tag.tagFormatSimple, 1)).subtype(
                    value='none')),
        namedtype.OptionalNamedType('signPolExtensions',
            SignPolExtensions().subtype(explicitTag=tag.Tag(
                 tag.tagClassContext, tag.tagFormatSimple, 2)))
    )


class MandatedUnsignedAttr(CMSAttrs):
    pass


class VerifierRules(univ.Sequence):
    componentType = namedtype.NamedTypes(
        namedtype.NamedType('mandatedUnsignedAttr', MandatedUnsignedAttr()),
        namedtype.OptionalNamedType('signPolExtensions', SignPolExtensions())
    )


class SignerAndVerifierRules(univ.Sequence):
    componentType = namedtype.NamedTypes(
        namedtype.NamedType('signerRules', SignerRules()),
        namedtype.NamedType('verifierRules', VerifierRules())
    )


class SigningCertTrustCondition(univ.Sequence):
    componentType = namedtype.NamedTypes(
        namedtype.NamedType('signerTrustTrees', CertificateTrustTrees()),
        namedtype.NamedType('signerRevReq', CertRevReq())
    )


class CommitmentTypeIdentifier(univ.ObjectIdentifier):
    pass


class FieldOfApplication(DirectoryString):
    pass


class CommitmentType(univ.Sequence):
    componentType = namedtype.NamedTypes(
        namedtype.NamedType('identifier', CommitmentTypeIdentifier()),
        namedtype.OptionalNamedType('fieldOfApplication',
            FieldOfApplication().subtype(explicitTag=tag.Tag(
                tag.tagClassContext, tag.tagFormatSimple, 0))),
        namedtype.OptionalNamedType('semantics',
            DirectoryString().subtype(explicitTag=tag.Tag(
                tag.tagClassContext, tag.tagFormatSimple, 1)))
    )


class SelectedCommitmentTypes(univ.SequenceOf):
    componentType = univ.Choice(componentType=namedtype.NamedTypes(
        namedtype.NamedType('empty', univ.Null()),
        namedtype.NamedType('recognizedCommitmentType', CommitmentType())
    ))


class CommitmentRule(univ.Sequence):
    componentType = namedtype.NamedTypes(
        namedtype.NamedType('selCommitmentTypes', SelectedCommitmentTypes()),
        namedtype.OptionalNamedType('signerAndVeriferRules',
            SignerAndVerifierRules().subtype(explicitTag=tag.Tag(
                tag.tagClassContext, tag.tagFormatConstructed, 0))),
        namedtype.OptionalNamedType('signingCertTrustCondition',
            SigningCertTrustCondition().subtype(explicitTag=tag.Tag(
                tag.tagClassContext, tag.tagFormatConstructed, 1))),
        namedtype.OptionalNamedType('timeStampTrustCondition',
            TimestampTrustCondition().subtype(explicitTag=tag.Tag(
                tag.tagClassContext, tag.tagFormatConstructed, 2))),
        namedtype.OptionalNamedType('attributeTrustCondition',
            AttributeTrustCondition().subtype(explicitTag=tag.Tag(
                tag.tagClassContext, tag.tagFormatConstructed, 3))),
        namedtype.OptionalNamedType('algorithmConstraintSet',
            AlgorithmConstraintSet().subtype(explicitTag=tag.Tag(
                tag.tagClassContext, tag.tagFormatConstructed, 4))),
        namedtype.OptionalNamedType('signPolExtensions',
            SignPolExtensions().subtype(explicitTag=tag.Tag(
                tag.tagClassContext, tag.tagFormatSimple, 5)))
    )


class CommitmentRules(univ.SequenceOf):
    componentType = CommitmentRule()


class CommonRules(univ.Sequence):
    componentType = namedtype.NamedTypes(
        namedtype.OptionalNamedType('signerAndVeriferRules',
            SignerAndVerifierRules().subtype(explicitTag=tag.Tag(
                tag.tagClassContext, tag.tagFormatConstructed, 0))),
        namedtype.OptionalNamedType('signingCertTrustCondition',
            SigningCertTrustCondition().subtype(explicitTag=tag.Tag(
                tag.tagClassContext, tag.tagFormatConstructed, 1))),
        namedtype.OptionalNamedType('timeStampTrustCondition',
            TimestampTrustCondition().subtype(explicitTag=tag.Tag(
                tag.tagClassContext, tag.tagFormatConstructed, 2))),
        namedtype.OptionalNamedType('attributeTrustCondition',
            AttributeTrustCondition().subtype(explicitTag=tag.Tag(
                tag.tagClassContext, tag.tagFormatConstructed, 3))),
        namedtype.OptionalNamedType('algorithmConstraintSet',
            AlgorithmConstraintSet().subtype(explicitTag=tag.Tag(
                tag.tagClassContext, tag.tagFormatConstructed, 4))),
        namedtype.OptionalNamedType('signPolExtensions',
            SignPolExtensions().subtype(explicitTag=tag.Tag(
                tag.tagClassContext, tag.tagFormatSimple, 5)))
    )


class PolicyIssuerName(GeneralNames):
    pass


class SignPolicyHash(univ.OctetString):
    pass


class SignPolicyId(univ.ObjectIdentifier):
    pass


class SigningPeriod(univ.Sequence):
    componentType = namedtype.NamedTypes(
        namedtype.NamedType('notBefore', useful.GeneralizedTime()),
        namedtype.OptionalNamedType('notAfter', useful.GeneralizedTime())
    )


class SignatureValidationPolicy(univ.Sequence):
    componentType = namedtype.NamedTypes(
        namedtype.NamedType('signingPeriod', SigningPeriod()),
        namedtype.NamedType('commonRules', CommonRules()),
        namedtype.NamedType('commitmentRules', CommitmentRules()),
        namedtype.OptionalNamedType('signPolExtensions', SignPolExtensions())
    )


class SignPolicyInfo(univ.Sequence):
    componentType = namedtype.NamedTypes(
        namedtype.NamedType('signPolicyIdentifier', SignPolicyId()),
        namedtype.NamedType('dateOfIssue', useful.GeneralizedTime()),
        namedtype.NamedType('policyIssuerName', PolicyIssuerName()),
        namedtype.NamedType('fieldOfApplication', FieldOfApplication()),
        namedtype.NamedType('signatureValidationPolicy', SignatureValidationPolicy()),
        namedtype.OptionalNamedType('signPolExtensions', SignPolExtensions())
    )


class SignaturePolicy(univ.Sequence):
    componentType = namedtype.NamedTypes(
        namedtype.NamedType('signPolicyHashAlg', AlgorithmIdentifier()),
        namedtype.NamedType('signPolicyInfo', SignPolicyInfo()),
        namedtype.OptionalNamedType('signPolicyHash', SignPolicyHash())
    )



# === NexusCore/openenv\Lib\site-packages\pyasn1_modules\rfc6031.py ===
#
# This file is part of pyasn1-modules software.
#
# Created by Russ Housley with assistance from asn1ate v.0.6.0.
#
# Copyright (c) 2019, Vigil Security, LLC
# License: http://snmplabs.com/pyasn1/license.html
#
# CMS Symmetric Key Package Content Type
#
# ASN.1 source from:
# https://www.rfc-editor.org/rfc/rfc6031.txt
#

from pyasn1.type import char
from pyasn1.type import constraint
from pyasn1.type import namedtype
from pyasn1.type import namedval
from pyasn1.type import opentype
from pyasn1.type import tag
from pyasn1.type import univ
from pyasn1.type import useful

from pyasn1_modules import rfc5652
from pyasn1_modules import rfc6019


def _OID(*components):
    output = []
    for x in tuple(components):
        if isinstance(x, univ.ObjectIdentifier):
            output.extend(list(x))
        else:
            output.append(int(x))
    return univ.ObjectIdentifier(output)


MAX = float('inf')

id_pskc = univ.ObjectIdentifier('1.2.840.113549.1.9.16.12')


# Symmetric Key Package Attributes

id_pskc_manufacturer = _OID(id_pskc, 1)

class at_pskc_manufacturer(char.UTF8String):
    pass


id_pskc_serialNo = _OID(id_pskc, 2)

class at_pskc_serialNo(char.UTF8String):
    pass


id_pskc_model = _OID(id_pskc, 3)

class at_pskc_model(char.UTF8String):
    pass


id_pskc_issueNo = _OID(id_pskc, 4)

class at_pskc_issueNo(char.UTF8String):
    pass


id_pskc_deviceBinding = _OID(id_pskc, 5)

class at_pskc_deviceBinding(char.UTF8String):
    pass


id_pskc_deviceStartDate = _OID(id_pskc, 6)

class at_pskc_deviceStartDate(useful.GeneralizedTime):
    pass


id_pskc_deviceExpiryDate = _OID(id_pskc, 7)

class at_pskc_deviceExpiryDate(useful.GeneralizedTime):
    pass


id_pskc_moduleId = _OID(id_pskc, 8)

class at_pskc_moduleId(char.UTF8String):
    pass


id_pskc_deviceUserId = _OID(id_pskc, 26)

class at_pskc_deviceUserId(char.UTF8String):
    pass


# Symmetric Key Attributes

id_pskc_keyId = _OID(id_pskc, 9)

class at_pskc_keyUserId(char.UTF8String):
    pass


id_pskc_algorithm = _OID(id_pskc, 10)

class at_pskc_algorithm(char.UTF8String):
    pass


id_pskc_issuer = _OID(id_pskc, 11)

class at_pskc_issuer(char.UTF8String):
    pass


id_pskc_keyProfileId = _OID(id_pskc, 12)

class at_pskc_keyProfileId(char.UTF8String):
    pass


id_pskc_keyReference = _OID(id_pskc, 13)

class at_pskc_keyReference(char.UTF8String):
    pass


id_pskc_friendlyName = _OID(id_pskc, 14)

class FriendlyName(univ.Sequence):
    pass

FriendlyName.componentType = namedtype.NamedTypes(
    namedtype.NamedType('friendlyName', char.UTF8String()),
    namedtype.OptionalNamedType('friendlyNameLangTag', char.UTF8String())
)

class at_pskc_friendlyName(FriendlyName):
    pass


id_pskc_algorithmParameters = _OID(id_pskc, 15)

class Encoding(char.UTF8String):
    pass

Encoding.namedValues = namedval.NamedValues(
    ('dec',   "DECIMAL"),
    ('hex',   "HEXADECIMAL"),
    ('alpha', "ALPHANUMERIC"),
    ('b64',   "BASE64"),
    ('bin',   "BINARY")
)

Encoding.subtypeSpec = constraint.SingleValueConstraint(
    "DECIMAL", "HEXADECIMAL", "ALPHANUMERIC", "BASE64", "BINARY" )

class ChallengeFormat(univ.Sequence):
    pass

ChallengeFormat.componentType = namedtype.NamedTypes(
    namedtype.NamedType('encoding', Encoding()),
    namedtype.DefaultedNamedType('checkDigit',
        univ.Boolean().subtype(value=0)),
    namedtype.NamedType('min', univ.Integer().subtype(
        subtypeSpec=constraint.ValueRangeConstraint(0, MAX))),
    namedtype.NamedType('max', univ.Integer().subtype(
        subtypeSpec=constraint.ValueRangeConstraint(0, MAX)))
)

class ResponseFormat(univ.Sequence):
    pass

ResponseFormat.componentType = namedtype.NamedTypes(
    namedtype.NamedType('encoding', Encoding()),
    namedtype.NamedType('length', univ.Integer().subtype(
        subtypeSpec=constraint.ValueRangeConstraint(0, MAX))),
    namedtype.DefaultedNamedType('checkDigit',
        univ.Boolean().subtype(value=0))
)

class PSKCAlgorithmParameters(univ.Choice):
    pass

PSKCAlgorithmParameters.componentType = namedtype.NamedTypes(
    namedtype.NamedType('suite', char.UTF8String()),
    namedtype.NamedType('challengeFormat', ChallengeFormat().subtype(
        implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatConstructed, 0))),
    namedtype.NamedType('responseFormat', ResponseFormat().subtype(
        implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatConstructed, 1)))
)

class at_pskc_algorithmParameters(PSKCAlgorithmParameters):
    pass


id_pskc_counter = _OID(id_pskc, 16)

class at_pskc_counter(univ.Integer):
    pass

at_pskc_counter.subtypeSpec = constraint.ValueRangeConstraint(0, MAX)


id_pskc_time = _OID(id_pskc, 17)

class at_pskc_time(rfc6019.BinaryTime):
    pass


id_pskc_timeInterval = _OID(id_pskc, 18)

class at_pskc_timeInterval(univ.Integer):
    pass

at_pskc_timeInterval.subtypeSpec = constraint.ValueRangeConstraint(0, MAX)


id_pskc_timeDrift = _OID(id_pskc, 19)

class at_pskc_timeDrift(univ.Integer):
    pass

at_pskc_timeDrift.subtypeSpec = constraint.ValueRangeConstraint(0, MAX)


id_pskc_valueMAC = _OID(id_pskc, 20)

class ValueMac(univ.Sequence):
    pass

ValueMac.componentType = namedtype.NamedTypes(
    namedtype.NamedType('macAlgorithm', char.UTF8String()),
    namedtype.NamedType('mac', char.UTF8String())
)

class at_pskc_valueMAC(ValueMac):
    pass


id_pskc_keyUserId = _OID(id_pskc, 27)

class at_pskc_keyId(char.UTF8String):
    pass


id_pskc_keyStartDate = _OID(id_pskc, 21)

class at_pskc_keyStartDate(useful.GeneralizedTime):
    pass


id_pskc_keyExpiryDate = _OID(id_pskc, 22)

class at_pskc_keyExpiryDate(useful.GeneralizedTime):
    pass


id_pskc_numberOfTransactions = _OID(id_pskc, 23)

class at_pskc_numberOfTransactions(univ.Integer):
    pass
    
at_pskc_numberOfTransactions.subtypeSpec = constraint.ValueRangeConstraint(0, MAX)


id_pskc_keyUsages = _OID(id_pskc, 24)

class PSKCKeyUsage(char.UTF8String):
    pass

PSKCKeyUsage.namedValues = namedval.NamedValues(
    ('otp',       "OTP"),
    ('cr',        "CR"),
    ('encrypt',   "Encrypt"),
    ('integrity', "Integrity"),
    ('verify',    "Verify"),
    ('unlock',    "Unlock"),
    ('decrypt',   "Decrypt"),
    ('keywrap',   "KeyWrap"),
    ('unwrap',    "Unwrap"),
    ('derive',    "Derive"),
    ('generate',  "Generate")
)

PSKCKeyUsage.subtypeSpec = constraint.SingleValueConstraint(
    "OTP", "CR", "Encrypt", "Integrity", "Verify", "Unlock",
    "Decrypt", "KeyWrap", "Unwrap", "Derive", "Generate" )

class PSKCKeyUsages(univ.SequenceOf):
    pass

PSKCKeyUsages.componentType = PSKCKeyUsage()

class at_pskc_keyUsage(PSKCKeyUsages):
    pass


id_pskc_pinPolicy = _OID(id_pskc, 25)

class PINUsageMode(char.UTF8String):
    pass

PINUsageMode.namedValues = namedval.NamedValues(
    ("local",       "Local"),
    ("prepend",     "Prepend"),
    ("append",      "Append"),
    ("algorithmic", "Algorithmic")
)

PINUsageMode.subtypeSpec = constraint.SingleValueConstraint(
    "Local", "Prepend", "Append", "Algorithmic" )

class PINPolicy(univ.Sequence):
    pass

PINPolicy.componentType = namedtype.NamedTypes(
    namedtype.OptionalNamedType('pinKeyId', char.UTF8String().subtype(
        implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 0))),
    namedtype.NamedType('pinUsageMode', PINUsageMode().subtype(
        implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 1))),
    namedtype.OptionalNamedType('maxFailedAttempts', univ.Integer().subtype(
        subtypeSpec=constraint.ValueRangeConstraint(0, MAX)).subtype(
        implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 2))),
    namedtype.OptionalNamedType('minLength', univ.Integer().subtype(
        subtypeSpec=constraint.ValueRangeConstraint(0, MAX)).subtype(
        implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 3))),
    namedtype.OptionalNamedType('maxLength', univ.Integer().subtype(
        subtypeSpec=constraint.ValueRangeConstraint(0, MAX)).subtype(
        implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 4))),
    namedtype.OptionalNamedType('pinEncoding', Encoding().subtype(
        implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 5)))
)

class at_pskc_pinPolicy(PINPolicy):
    pass


# Map of Symmetric Key Package Attribute OIDs to Attributes

sKeyPkgAttributesMap = {
     id_pskc_manufacturer: at_pskc_manufacturer(),
     id_pskc_serialNo: at_pskc_serialNo(),
     id_pskc_model: at_pskc_model(),
     id_pskc_issueNo: at_pskc_issueNo(),
     id_pskc_deviceBinding: at_pskc_deviceBinding(),
     id_pskc_deviceStartDate: at_pskc_deviceStartDate(),
     id_pskc_deviceExpiryDate: at_pskc_deviceExpiryDate(),
     id_pskc_moduleId: at_pskc_moduleId(),
     id_pskc_deviceUserId: at_pskc_deviceUserId(),
}


# Map of Symmetric Key Attribute OIDs to Attributes

sKeyAttributesMap = {
     id_pskc_keyId: at_pskc_keyId(),
     id_pskc_algorithm: at_pskc_algorithm(),
     id_pskc_issuer: at_pskc_issuer(),
     id_pskc_keyProfileId: at_pskc_keyProfileId(),
     id_pskc_keyReference: at_pskc_keyReference(),
     id_pskc_friendlyName: at_pskc_friendlyName(),
     id_pskc_algorithmParameters: at_pskc_algorithmParameters(),
     id_pskc_counter: at_pskc_counter(),
     id_pskc_time: at_pskc_time(),
     id_pskc_timeInterval: at_pskc_timeInterval(),
     id_pskc_timeDrift: at_pskc_timeDrift(),
     id_pskc_valueMAC: at_pskc_valueMAC(),
     id_pskc_keyUserId: at_pskc_keyUserId(),
     id_pskc_keyStartDate: at_pskc_keyStartDate(),
     id_pskc_keyExpiryDate: at_pskc_keyExpiryDate(),
     id_pskc_numberOfTransactions: at_pskc_numberOfTransactions(),
     id_pskc_keyUsages: at_pskc_keyUsage(),
     id_pskc_pinPolicy: at_pskc_pinPolicy(),
}


# This definition replaces Attribute() from rfc5652.py; it is the same except
# that opentype is added with sKeyPkgAttributesMap and sKeyAttributesMap

class AttributeType(univ.ObjectIdentifier):
    pass


class AttributeValue(univ.Any):
    pass


class SKeyAttribute(univ.Sequence):
    pass

SKeyAttribute.componentType = namedtype.NamedTypes(
    namedtype.NamedType('attrType', AttributeType()),
    namedtype.NamedType('attrValues',
        univ.SetOf(componentType=AttributeValue()),
        openType=opentype.OpenType('attrType', sKeyAttributesMap)
    )
)


class SKeyPkgAttribute(univ.Sequence):
    pass

SKeyPkgAttribute.componentType = namedtype.NamedTypes(
    namedtype.NamedType('attrType', AttributeType()),
    namedtype.NamedType('attrValues',
        univ.SetOf(componentType=AttributeValue()),
        openType=opentype.OpenType('attrType', sKeyPkgAttributesMap)
    )
)


# Symmetric Key Package Content Type

id_ct_KP_sKeyPackage = univ.ObjectIdentifier('1.2.840.113549.1.9.16.1.25')


class KeyPkgVersion(univ.Integer):
    pass

KeyPkgVersion.namedValues = namedval.NamedValues(
    ('v1', 1)
)


class OneSymmetricKey(univ.Sequence):
    pass

OneSymmetricKey.componentType = namedtype.NamedTypes(
    namedtype.OptionalNamedType('sKeyAttrs',
        univ.SequenceOf(componentType=SKeyAttribute()).subtype(
            subtypeSpec=constraint.ValueSizeConstraint(1, MAX))),
    namedtype.OptionalNamedType('sKey', univ.OctetString())
)

OneSymmetricKey.sizeSpec = univ.Sequence.sizeSpec + constraint.ValueSizeConstraint(1, 2)


class SymmetricKeys(univ.SequenceOf):
    pass

SymmetricKeys.componentType = OneSymmetricKey()
SymmetricKeys.subtypeSpec=constraint.ValueSizeConstraint(1, MAX)


class SymmetricKeyPackage(univ.Sequence):
    pass

SymmetricKeyPackage.componentType = namedtype.NamedTypes(
    namedtype.DefaultedNamedType('version', KeyPkgVersion().subtype(value='v1')),
    namedtype.OptionalNamedType('sKeyPkgAttrs',
        univ.SequenceOf(componentType=SKeyPkgAttribute()).subtype(
            subtypeSpec=constraint.ValueSizeConstraint(1, MAX),
            implicitTag=tag.Tag(tag.tagClassContext, tag.tagFormatSimple, 0))),
    namedtype.NamedType('sKeys', SymmetricKeys())
)


# Map of Content Type OIDs to Content Types are
# added to the ones that are in rfc5652.py

_cmsContentTypesMapUpdate = {
    id_ct_KP_sKeyPackage: SymmetricKeyPackage(),
}

rfc5652.cmsContentTypesMap.update(_cmsContentTypesMapUpdate)

# === NexusCore/openenv\Lib\site-packages\pyreadline3\console\ironpython_console.py ===
# -*- coding: utf-8 -*-
# *****************************************************************************
#       Copyright (C) 2003-2006 Gary Bishop.
#       Copyright (C) 2006-2020 Jorgen Stenarson. <jorgen.stenarson@bostream.nu>
#       Copyright (C) 2020 Bassem Girgis. <brgirgis@gmail.com>
#
#  Distributed under the terms of the BSD License.  The full license is in
#  the file COPYING, distributed as part of this software.
# *****************************************************************************


import os
import re

import IronPythonConsole
import System
from pyreadline3.console.ansi import AnsiState
from pyreadline3.keysyms import (
    make_keyinfo,
    make_KeyPress,
    make_KeyPress_from_keydescr,
    make_keysym,
)
from pyreadline3.logger import log

from .event import Event

"""Cursor control and color for the .NET console.
"""

#
# Ironpython requires a patch to work do:
#
# In file PythonCommandLine.cs patch line:
#    class PythonCommandLine
#    {

# to:
#    public class PythonCommandLine
#    {
#
#
#
# primitive debug printing that won't interfere with the screen

import sys

import clr

clr.AddReferenceToFileAndPath(sys.executable)


color = System.ConsoleColor

ansicolor = {
    "0;30": color.Black,
    "0;31": color.DarkRed,
    "0;32": color.DarkGreen,
    "0;33": color.DarkYellow,
    "0;34": color.DarkBlue,
    "0;35": color.DarkMagenta,
    "0;36": color.DarkCyan,
    "0;37": color.DarkGray,
    "1;30": color.Gray,
    "1;31": color.Red,
    "1;32": color.Green,
    "1;33": color.Yellow,
    "1;34": color.Blue,
    "1;35": color.Magenta,
    "1;36": color.Cyan,
    "1;37": color.White,
}

winattr = {
    "black": 0,
    "darkgray": 0 + 8,
    "darkred": 4,
    "red": 4 + 8,
    "darkgreen": 2,
    "green": 2 + 8,
    "darkyellow": 6,
    "yellow": 6 + 8,
    "darkblue": 1,
    "blue": 1 + 8,
    "darkmagenta": 5,
    "magenta": 5 + 8,
    "darkcyan": 3,
    "cyan": 3 + 8,
    "gray": 7,
    "white": 7 + 8,
}


class Console(object):
    """Console driver for Windows."""

    def __init__(self, newbuffer=0):
        """Initialize the Console object.

        newbuffer=1 will allocate a new buffer so the old content will be restored
        on exit.
        """
        self.serial = 0
        self.attr = System.Console.ForegroundColor
        self.saveattr = winattr[str(System.Console.ForegroundColor).lower()]
        self.savebg = System.Console.BackgroundColor
        log("initial attr=%s" % self.attr)

    def _get(self):
        top = System.Console.WindowTop
        log("WindowTop:%s" % top)
        return top

    def _set(self, value):
        top = System.Console.WindowTop
        log("Set WindowTop:old:%s,new:%s" % (top, value))

    WindowTop = property(_get, _set)
    del _get, _set

    def __del__(self):
        """Cleanup the console when finished."""
        # I don't think this ever gets called
        pass

    def pos(self, x=None, y=None):
        """Move or query the window cursor."""
        if x is not None:
            System.Console.CursorLeft = x
        else:
            x = System.Console.CursorLeft
        if y is not None:
            System.Console.CursorTop = y
        else:
            y = System.Console.CursorTop
        return x, y

    def home(self):
        """Move to home."""
        self.pos(0, 0)

    # Map ANSI color escape sequences into Windows Console Attributes

    terminal_escape = re.compile("(\001?\033\\[[0-9;]*m\002?)")
    escape_parts = re.compile("\001?\033\\[([0-9;]*)m\002?")

    # This pattern should match all characters that change the cursor position differently
    # than a normal character.
    motion_char_re = re.compile("([\n\r\t\010\007])")

    def write_scrolling(self, text, attr=None):
        """write text at current cursor position while watching for scrolling.

        If the window scrolls because you are at the bottom of the screen
        buffer, all positions that you are storing will be shifted by the
        scroll amount. For example, I remember the cursor position of the
        prompt so that I can redraw the line but if the window scrolls,
        the remembered position is off.

        This variant of write tries to keep track of the cursor position
        so that it will know when the screen buffer is scrolled. It
        returns the number of lines that the buffer scrolled.

        """
        x, y = self.pos()
        w, h = self.size()
        scroll = 0  # the result

        # split the string into ordinary characters and funny characters
        chunks = self.motion_char_re.split(text)
        for chunk in chunks:
            n = self.write_color(chunk, attr)
            if len(chunk) == 1:  # the funny characters will be alone
                if chunk[0] == "\n":  # newline
                    x = 0
                    y += 1
                elif chunk[0] == "\r":  # carriage return
                    x = 0
                elif chunk[0] == "\t":  # tab
                    x = 8 * (int(x / 8) + 1)
                    if x > w:  # newline
                        x -= w
                        y += 1
                elif chunk[0] == "\007":  # bell
                    pass
                elif chunk[0] == "\010":
                    x -= 1
                    if x < 0:
                        y -= 1  # backed up 1 line
                else:  # ordinary character
                    x += 1
                if x == w:  # wrap
                    x = 0
                    y += 1
                if y == h:  # scroll
                    scroll += 1
                    y = h - 1
            else:  # chunk of ordinary characters
                x += n
                l = int(x / w)  # lines we advanced
                x = x % w  # new x value
                y += l
                if y >= h:  # scroll
                    scroll += y - h + 1
                    y = h - 1
        return scroll

    trtable = {
        0: color.Black,
        4: color.DarkRed,
        2: color.DarkGreen,
        6: color.DarkYellow,
        1: color.DarkBlue,
        5: color.DarkMagenta,
        3: color.DarkCyan,
        7: color.Gray,
        8: color.DarkGray,
        4 + 8: color.Red,
        2 + 8: color.Green,
        6 + 8: color.Yellow,
        1 + 8: color.Blue,
        5 + 8: color.Magenta,
        3 + 8: color.Cyan,
        7 + 8: color.White,
    }

    def write_color(self, text, attr=None):
        """write text at current cursor position and interpret color escapes.

        return the number of characters written.
        """
        log('write_color("%s", %s)' % (text, attr))
        chunks = self.terminal_escape.split(text)
        log("chunks=%s" % repr(chunks))
        bg = self.savebg
        n = 0  # count the characters we actually write, omitting the escapes
        if attr is None:  # use attribute from initial console
            attr = self.attr
        try:
            fg = self.trtable[(0x000F & attr)]
            bg = self.trtable[(0x00F0 & attr) >> 4]
        except TypeError:
            fg = attr

        for chunk in chunks:
            m = self.escape_parts.match(chunk)
            if m:
                log(m.group(1))
                attr = ansicolor.get(m.group(1), self.attr)
            n += len(chunk)
            System.Console.ForegroundColor = fg
            System.Console.BackgroundColor = bg
            System.Console.Write(chunk)
        return n

    def write_plain(self, text, attr=None):
        """write text at current cursor position."""
        log('write("%s", %s)' % (text, attr))
        if attr is None:
            attr = self.attr
        n = c_int(0)
        self.SetConsoleTextAttribute(self.hout, attr)
        self.WriteConsoleA(self.hout, text, len(text), byref(n), None)
        return len(text)

    if "EMACS" in os.environ:

        def write_color(self, text, attr=None):
            junk = c_int(0)
            self.WriteFile(self.hout, text, len(text), byref(junk), None)
            return len(text)

        write_plain = write_color

    # make this class look like a file object
    def write(self, text):
        log('write("%s")' % text)
        return self.write_color(text)

    # write = write_scrolling

    def isatty(self):
        return True

    def flush(self):
        pass

    def page(self, attr=None, fill=" "):
        """Fill the entire screen."""
        System.Console.Clear()

    def text(self, x, y, text, attr=None):
        """Write text at the given position."""
        self.pos(x, y)
        self.write_color(text, attr)

    def clear_to_end_of_window(self):
        oldtop = self.WindowTop
        lastline = self.WindowTop + System.Console.WindowHeight
        pos = self.pos()
        w, h = self.size()
        length = w - pos[0] + min((lastline - pos[1] - 1), 5) * w - 1
        self.write_color(length * " ")
        self.pos(*pos)
        self.WindowTop = oldtop

    def rectangle(self, rect, attr=None, fill=" "):
        """Fill Rectangle."""
        oldtop = self.WindowTop
        oldpos = self.pos()
        # raise NotImplementedError
        x0, y0, x1, y1 = rect
        if attr is None:
            attr = self.attr
        if fill:
            rowfill = fill[:1] * abs(x1 - x0)
        else:
            rowfill = " " * abs(x1 - x0)
        for y in range(y0, y1):
            System.Console.SetCursorPosition(x0, y)
            self.write_color(rowfill, attr)
        self.pos(*oldpos)

    def scroll(self, rect, dx, dy, attr=None, fill=" "):
        """Scroll a rectangle."""
        raise NotImplementedError

    def scroll_window(self, lines):
        """Scroll the window by the indicated number of lines."""
        top = self.WindowTop + lines
        if top < 0:
            top = 0
        if top + System.Console.WindowHeight > System.Console.BufferHeight:
            top = System.Console.BufferHeight
        self.WindowTop = top

    def getkeypress(self):
        """Return next key press event from the queue, ignoring others."""
        ck = System.ConsoleKey
        while True:
            e = System.Console.ReadKey(True)
            if e.Key == System.ConsoleKey.PageDown:  # PageDown
                self.scroll_window(12)
            elif e.Key == System.ConsoleKey.PageUp:  # PageUp
                self.scroll_window(-12)
            elif str(e.KeyChar) == "\000":  # Drop deadkeys
                log("Deadkey: %s" % e)
                return event(self, e)
            else:
                return event(self, e)

    def title(self, txt=None):
        """Set/get title."""
        if txt:
            System.Console.Title = txt
        else:
            return System.Console.Title

    def size(self, width=None, height=None):
        """Set/get window size."""
        sc = System.Console
        if width is not None and height is not None:
            sc.BufferWidth, sc.BufferHeight = width, height
        else:
            return sc.BufferWidth, sc.BufferHeight

        if width is not None and height is not None:
            sc.WindowWidth, sc.WindowHeight = width, height
        else:
            return sc.WindowWidth - 1, sc.WindowHeight - 1

    def cursor(self, visible=True, size=None):
        """Set cursor on or off."""
        System.Console.CursorVisible = visible

    def bell(self):
        System.Console.Beep()

    def next_serial(self):
        """Get next event serial number."""
        self.serial += 1
        return self.serial


class event(Event):
    """Represent events from the console."""

    def __init__(self, console, input):
        """Initialize an event from the Windows input structure."""
        self.type = "??"
        self.serial = console.next_serial()
        self.width = 0
        self.height = 0
        self.x = 0
        self.y = 0
        self.char = str(input.KeyChar)
        self.keycode = input.Key
        self.state = input.Modifiers
        log("%s,%s,%s" % (input.Modifiers, input.Key, input.KeyChar))
        self.type = "KeyRelease"
        self.keysym = make_keysym(self.keycode)
        self.keyinfo = make_KeyPress(self.char, self.state, self.keycode)


def make_event_from_keydescr(keydescr):
    def input():
        return 1

    input.KeyChar = "a"
    input.Key = System.ConsoleKey.A
    input.Modifiers = System.ConsoleModifiers.Shift
    input.next_serial = input
    e = event(input, input)
    del input.next_serial
    keyinfo = make_KeyPress_from_keydescr(keydescr)
    e.keyinfo = keyinfo
    return e


CTRL_C_EVENT = make_event_from_keydescr("Control-c")


def install_readline(hook):
    def hook_wrap():
        try:
            res = hook()
        except KeyboardInterrupt as x:  # this exception does not seem to be caught
            res = ""
        except EOFError:
            return None
        if res[-1:] == "\n":
            return res[:-1]
        else:
            return res

    class IronPythonWrapper(IronPythonConsole.IConsole):
        def ReadLine(self, autoIndentSize):
            return hook_wrap()

        def Write(self, text, style):
            System.Console.Write(text)

        def WriteLine(self, text, style):
            System.Console.WriteLine(text)

    IronPythonConsole.PythonCommandLine.MyConsole = IronPythonWrapper()


if __name__ == "__main__":
    import sys
    import time

    c = Console(0)
    sys.stdout = c
    sys.stderr = c
    c.page()
    c.pos(5, 10)
    c.write("hi there")
    c.title("Testing console")
    #    c.bell()
    print()
    print("size", c.size())
    print("  some printed output")
    for i in range(10):
        e = c.getkeypress()
        print(e.Key, chr(e.KeyChar), ord(e.KeyChar), e.Modifiers)
    del c

    System.Console.Clear()

# === NexusCore/openenv\Lib\site-packages\urllib3\util\url.py ===
from __future__ import annotations

import re
import typing

from ..exceptions import LocationParseError
from .util import to_str

# We only want to normalize urls with an HTTP(S) scheme.
# urllib3 infers URLs without a scheme (None) to be http.
_NORMALIZABLE_SCHEMES = ("http", "https", None)

# Almost all of these patterns were derived from the
# 'rfc3986' module: https://github.com/python-hyper/rfc3986
_PERCENT_RE = re.compile(r"%[a-fA-F0-9]{2}")
_SCHEME_RE = re.compile(r"^(?:[a-zA-Z][a-zA-Z0-9+-]*:|/)")
_URI_RE = re.compile(
    r"^(?:([a-zA-Z][a-zA-Z0-9+.-]*):)?"
    r"(?://([^\\/?#]*))?"
    r"([^?#]*)"
    r"(?:\?([^#]*))?"
    r"(?:#(.*))?$",
    re.UNICODE | re.DOTALL,
)

_IPV4_PAT = r"(?:[0-9]{1,3}\.){3}[0-9]{1,3}"
_HEX_PAT = "[0-9A-Fa-f]{1,4}"
_LS32_PAT = "(?:{hex}:{hex}|{ipv4})".format(hex=_HEX_PAT, ipv4=_IPV4_PAT)
_subs = {"hex": _HEX_PAT, "ls32": _LS32_PAT}
_variations = [
    #                            6( h16 ":" ) ls32
    "(?:%(hex)s:){6}%(ls32)s",
    #                       "::" 5( h16 ":" ) ls32
    "::(?:%(hex)s:){5}%(ls32)s",
    # [               h16 ] "::" 4( h16 ":" ) ls32
    "(?:%(hex)s)?::(?:%(hex)s:){4}%(ls32)s",
    # [ *1( h16 ":" ) h16 ] "::" 3( h16 ":" ) ls32
    "(?:(?:%(hex)s:)?%(hex)s)?::(?:%(hex)s:){3}%(ls32)s",
    # [ *2( h16 ":" ) h16 ] "::" 2( h16 ":" ) ls32
    "(?:(?:%(hex)s:){0,2}%(hex)s)?::(?:%(hex)s:){2}%(ls32)s",
    # [ *3( h16 ":" ) h16 ] "::"    h16 ":"   ls32
    "(?:(?:%(hex)s:){0,3}%(hex)s)?::%(hex)s:%(ls32)s",
    # [ *4( h16 ":" ) h16 ] "::"              ls32
    "(?:(?:%(hex)s:){0,4}%(hex)s)?::%(ls32)s",
    # [ *5( h16 ":" ) h16 ] "::"              h16
    "(?:(?:%(hex)s:){0,5}%(hex)s)?::%(hex)s",
    # [ *6( h16 ":" ) h16 ] "::"
    "(?:(?:%(hex)s:){0,6}%(hex)s)?::",
]

_UNRESERVED_PAT = r"ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789._\-~"
_IPV6_PAT = "(?:" + "|".join([x % _subs for x in _variations]) + ")"
_ZONE_ID_PAT = "(?:%25|%)(?:[" + _UNRESERVED_PAT + "]|%[a-fA-F0-9]{2})+"
_IPV6_ADDRZ_PAT = r"\[" + _IPV6_PAT + r"(?:" + _ZONE_ID_PAT + r")?\]"
_REG_NAME_PAT = r"(?:[^\[\]%:/?#]|%[a-fA-F0-9]{2})*"
_TARGET_RE = re.compile(r"^(/[^?#]*)(?:\?([^#]*))?(?:#.*)?$")

_IPV4_RE = re.compile("^" + _IPV4_PAT + "$")
_IPV6_RE = re.compile("^" + _IPV6_PAT + "$")
_IPV6_ADDRZ_RE = re.compile("^" + _IPV6_ADDRZ_PAT + "$")
_BRACELESS_IPV6_ADDRZ_RE = re.compile("^" + _IPV6_ADDRZ_PAT[2:-2] + "$")
_ZONE_ID_RE = re.compile("(" + _ZONE_ID_PAT + r")\]$")

_HOST_PORT_PAT = ("^(%s|%s|%s)(?::0*?(|0|[1-9][0-9]{0,4}))?$") % (
    _REG_NAME_PAT,
    _IPV4_PAT,
    _IPV6_ADDRZ_PAT,
)
_HOST_PORT_RE = re.compile(_HOST_PORT_PAT, re.UNICODE | re.DOTALL)

_UNRESERVED_CHARS = set(
    "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789._-~"
)
_SUB_DELIM_CHARS = set("!$&'()*+,;=")
_USERINFO_CHARS = _UNRESERVED_CHARS | _SUB_DELIM_CHARS | {":"}
_PATH_CHARS = _USERINFO_CHARS | {"@", "/"}
_QUERY_CHARS = _FRAGMENT_CHARS = _PATH_CHARS | {"?"}


class Url(
    typing.NamedTuple(
        "Url",
        [
            ("scheme", typing.Optional[str]),
            ("auth", typing.Optional[str]),
            ("host", typing.Optional[str]),
            ("port", typing.Optional[int]),
            ("path", typing.Optional[str]),
            ("query", typing.Optional[str]),
            ("fragment", typing.Optional[str]),
        ],
    )
):
    """
    Data structure for representing an HTTP URL. Used as a return value for
    :func:`parse_url`. Both the scheme and host are normalized as they are
    both case-insensitive according to RFC 3986.
    """

    def __new__(  # type: ignore[no-untyped-def]
        cls,
        scheme: str | None = None,
        auth: str | None = None,
        host: str | None = None,
        port: int | None = None,
        path: str | None = None,
        query: str | None = None,
        fragment: str | None = None,
    ):
        if path and not path.startswith("/"):
            path = "/" + path
        if scheme is not None:
            scheme = scheme.lower()
        return super().__new__(cls, scheme, auth, host, port, path, query, fragment)

    @property
    def hostname(self) -> str | None:
        """For backwards-compatibility with urlparse. We're nice like that."""
        return self.host

    @property
    def request_uri(self) -> str:
        """Absolute path including the query string."""
        uri = self.path or "/"

        if self.query is not None:
            uri += "?" + self.query

        return uri

    @property
    def authority(self) -> str | None:
        """
        Authority component as defined in RFC 3986 3.2.
        This includes userinfo (auth), host and port.

        i.e.
            userinfo@host:port
        """
        userinfo = self.auth
        netloc = self.netloc
        if netloc is None or userinfo is None:
            return netloc
        else:
            return f"{userinfo}@{netloc}"

    @property
    def netloc(self) -> str | None:
        """
        Network location including host and port.

        If you need the equivalent of urllib.parse's ``netloc``,
        use the ``authority`` property instead.
        """
        if self.host is None:
            return None
        if self.port:
            return f"{self.host}:{self.port}"
        return self.host

    @property
    def url(self) -> str:
        """
        Convert self into a url

        This function should more or less round-trip with :func:`.parse_url`. The
        returned url may not be exactly the same as the url inputted to
        :func:`.parse_url`, but it should be equivalent by the RFC (e.g., urls
        with a blank port will have : removed).

        Example:

        .. code-block:: python

            import urllib3

            U = urllib3.util.parse_url("https://google.com/mail/")

            print(U.url)
            # "https://google.com/mail/"

            print( urllib3.util.Url("https", "username:password",
                                    "host.com", 80, "/path", "query", "fragment"
                                    ).url
                )
            # "https://username:password@host.com:80/path?query#fragment"
        """
        scheme, auth, host, port, path, query, fragment = self
        url = ""

        # We use "is not None" we want things to happen with empty strings (or 0 port)
        if scheme is not None:
            url += scheme + "://"
        if auth is not None:
            url += auth + "@"
        if host is not None:
            url += host
        if port is not None:
            url += ":" + str(port)
        if path is not None:
            url += path
        if query is not None:
            url += "?" + query
        if fragment is not None:
            url += "#" + fragment

        return url

    def __str__(self) -> str:
        return self.url


@typing.overload
def _encode_invalid_chars(
    component: str, allowed_chars: typing.Container[str]
) -> str:  # Abstract
    ...


@typing.overload
def _encode_invalid_chars(
    component: None, allowed_chars: typing.Container[str]
) -> None:  # Abstract
    ...


def _encode_invalid_chars(
    component: str | None, allowed_chars: typing.Container[str]
) -> str | None:
    """Percent-encodes a URI component without reapplying
    onto an already percent-encoded component.
    """
    if component is None:
        return component

    component = to_str(component)

    # Normalize existing percent-encoded bytes.
    # Try to see if the component we're encoding is already percent-encoded
    # so we can skip all '%' characters but still encode all others.
    component, percent_encodings = _PERCENT_RE.subn(
        lambda match: match.group(0).upper(), component
    )

    uri_bytes = component.encode("utf-8", "surrogatepass")
    is_percent_encoded = percent_encodings == uri_bytes.count(b"%")
    encoded_component = bytearray()

    for i in range(0, len(uri_bytes)):
        # Will return a single character bytestring
        byte = uri_bytes[i : i + 1]
        byte_ord = ord(byte)
        if (is_percent_encoded and byte == b"%") or (
            byte_ord < 128 and byte.decode() in allowed_chars
        ):
            encoded_component += byte
            continue
        encoded_component.extend(b"%" + (hex(byte_ord)[2:].encode().zfill(2).upper()))

    return encoded_component.decode()


def _remove_path_dot_segments(path: str) -> str:
    # See http://tools.ietf.org/html/rfc3986#section-5.2.4 for pseudo-code
    segments = path.split("/")  # Turn the path into a list of segments
    output = []  # Initialize the variable to use to store output

    for segment in segments:
        # '.' is the current directory, so ignore it, it is superfluous
        if segment == ".":
            continue
        # Anything other than '..', should be appended to the output
        if segment != "..":
            output.append(segment)
        # In this case segment == '..', if we can, we should pop the last
        # element
        elif output:
            output.pop()

    # If the path starts with '/' and the output is empty or the first string
    # is non-empty
    if path.startswith("/") and (not output or output[0]):
        output.insert(0, "")

    # If the path starts with '/.' or '/..' ensure we add one more empty
    # string to add a trailing '/'
    if path.endswith(("/.", "/..")):
        output.append("")

    return "/".join(output)


@typing.overload
def _normalize_host(host: None, scheme: str | None) -> None: ...


@typing.overload
def _normalize_host(host: str, scheme: str | None) -> str: ...


def _normalize_host(host: str | None, scheme: str | None) -> str | None:
    if host:
        if scheme in _NORMALIZABLE_SCHEMES:
            is_ipv6 = _IPV6_ADDRZ_RE.match(host)
            if is_ipv6:
                # IPv6 hosts of the form 'a::b%zone' are encoded in a URL as
                # such per RFC 6874: 'a::b%25zone'. Unquote the ZoneID
                # separator as necessary to return a valid RFC 4007 scoped IP.
                match = _ZONE_ID_RE.search(host)
                if match:
                    start, end = match.span(1)
                    zone_id = host[start:end]

                    if zone_id.startswith("%25") and zone_id != "%25":
                        zone_id = zone_id[3:]
                    else:
                        zone_id = zone_id[1:]
                    zone_id = _encode_invalid_chars(zone_id, _UNRESERVED_CHARS)
                    return f"{host[:start].lower()}%{zone_id}{host[end:]}"
                else:
                    return host.lower()
            elif not _IPV4_RE.match(host):
                return to_str(
                    b".".join([_idna_encode(label) for label in host.split(".")]),
                    "ascii",
                )
    return host


def _idna_encode(name: str) -> bytes:
    if not name.isascii():
        try:
            import idna
        except ImportError:
            raise LocationParseError(
                "Unable to parse URL without the 'idna' module"
            ) from None

        try:
            return idna.encode(name.lower(), strict=True, std3_rules=True)
        except idna.IDNAError:
            raise LocationParseError(
                f"Name '{name}' is not a valid IDNA label"
            ) from None

    return name.lower().encode("ascii")


def _encode_target(target: str) -> str:
    """Percent-encodes a request target so that there are no invalid characters

    Pre-condition for this function is that 'target' must start with '/'.
    If that is the case then _TARGET_RE will always produce a match.
    """
    match = _TARGET_RE.match(target)
    if not match:  # Defensive:
        raise LocationParseError(f"{target!r} is not a valid request URI")

    path, query = match.groups()
    encoded_target = _encode_invalid_chars(path, _PATH_CHARS)
    if query is not None:
        query = _encode_invalid_chars(query, _QUERY_CHARS)
        encoded_target += "?" + query
    return encoded_target


def parse_url(url: str) -> Url:
    """
    Given a url, return a parsed :class:`.Url` namedtuple. Best-effort is
    performed to parse incomplete urls. Fields not provided will be None.
    This parser is RFC 3986 and RFC 6874 compliant.

    The parser logic and helper functions are based heavily on
    work done in the ``rfc3986`` module.

    :param str url: URL to parse into a :class:`.Url` namedtuple.

    Partly backwards-compatible with :mod:`urllib.parse`.

    Example:

    .. code-block:: python

        import urllib3

        print( urllib3.util.parse_url('http://google.com/mail/'))
        # Url(scheme='http', host='google.com', port=None, path='/mail/', ...)

        print( urllib3.util.parse_url('google.com:80'))
        # Url(scheme=None, host='google.com', port=80, path=None, ...)

        print( urllib3.util.parse_url('/foo?bar'))
        # Url(scheme=None, host=None, port=None, path='/foo', query='bar', ...)
    """
    if not url:
        # Empty
        return Url()

    source_url = url
    if not _SCHEME_RE.search(url):
        url = "//" + url

    scheme: str | None
    authority: str | None
    auth: str | None
    host: str | None
    port: str | None
    port_int: int | None
    path: str | None
    query: str | None
    fragment: str | None

    try:
        scheme, authority, path, query, fragment = _URI_RE.match(url).groups()  # type: ignore[union-attr]
        normalize_uri = scheme is None or scheme.lower() in _NORMALIZABLE_SCHEMES

        if scheme:
            scheme = scheme.lower()

        if authority:
            auth, _, host_port = authority.rpartition("@")
            auth = auth or None
            host, port = _HOST_PORT_RE.match(host_port).groups()  # type: ignore[union-attr]
            if auth and normalize_uri:
                auth = _encode_invalid_chars(auth, _USERINFO_CHARS)
            if port == "":
                port = None
        else:
            auth, host, port = None, None, None

        if port is not None:
            port_int = int(port)
            if not (0 <= port_int <= 65535):
                raise LocationParseError(url)
        else:
            port_int = None

        host = _normalize_host(host, scheme)

        if normalize_uri and path:
            path = _remove_path_dot_segments(path)
            path = _encode_invalid_chars(path, _PATH_CHARS)
        if normalize_uri and query:
            query = _encode_invalid_chars(query, _QUERY_CHARS)
        if normalize_uri and fragment:
            fragment = _encode_invalid_chars(fragment, _FRAGMENT_CHARS)

    except (ValueError, AttributeError) as e:
        raise LocationParseError(source_url) from e

    # For the sake of backwards compatibility we put empty
    # string values for path if there are any defined values
    # beyond the path in the URL.
    # TODO: Remove this when we break backwards compatibility.
    if not path:
        if query is not None or fragment is not None:
            path = ""
        else:
            path = None

    return Url(
        scheme=scheme,
        auth=auth,
        host=host,
        port=port_int,
        path=path,
        query=query,
        fragment=fragment,
    )

# === NexusCore/openenv\Lib\site-packages\attr\_funcs.py ===
# SPDX-License-Identifier: MIT


import copy

from ._compat import PY_3_9_PLUS, get_generic_base
from ._make import _OBJ_SETATTR, NOTHING, fields
from .exceptions import AttrsAttributeNotFoundError


def asdict(
    inst,
    recurse=True,
    filter=None,
    dict_factory=dict,
    retain_collection_types=False,
    value_serializer=None,
):
    """
    Return the *attrs* attribute values of *inst* as a dict.

    Optionally recurse into other *attrs*-decorated classes.

    Args:
        inst: Instance of an *attrs*-decorated class.

        recurse (bool): Recurse into classes that are also *attrs*-decorated.

        filter (~typing.Callable):
            A callable whose return code determines whether an attribute or
            element is included (`True`) or dropped (`False`).  Is called with
            the `attrs.Attribute` as the first argument and the value as the
            second argument.

        dict_factory (~typing.Callable):
            A callable to produce dictionaries from.  For example, to produce
            ordered dictionaries instead of normal Python dictionaries, pass in
            ``collections.OrderedDict``.

        retain_collection_types (bool):
            Do not convert to `list` when encountering an attribute whose type
            is `tuple` or `set`.  Only meaningful if *recurse* is `True`.

        value_serializer (typing.Callable | None):
            A hook that is called for every attribute or dict key/value.  It
            receives the current instance, field and value and must return the
            (updated) value.  The hook is run *after* the optional *filter* has
            been applied.

    Returns:
        Return type of *dict_factory*.

    Raises:
        attrs.exceptions.NotAnAttrsClassError:
            If *cls* is not an *attrs* class.

    ..  versionadded:: 16.0.0 *dict_factory*
    ..  versionadded:: 16.1.0 *retain_collection_types*
    ..  versionadded:: 20.3.0 *value_serializer*
    ..  versionadded:: 21.3.0
        If a dict has a collection for a key, it is serialized as a tuple.
    """
    attrs = fields(inst.__class__)
    rv = dict_factory()
    for a in attrs:
        v = getattr(inst, a.name)
        if filter is not None and not filter(a, v):
            continue

        if value_serializer is not None:
            v = value_serializer(inst, a, v)

        if recurse is True:
            if has(v.__class__):
                rv[a.name] = asdict(
                    v,
                    recurse=True,
                    filter=filter,
                    dict_factory=dict_factory,
                    retain_collection_types=retain_collection_types,
                    value_serializer=value_serializer,
                )
            elif isinstance(v, (tuple, list, set, frozenset)):
                cf = v.__class__ if retain_collection_types is True else list
                items = [
                    _asdict_anything(
                        i,
                        is_key=False,
                        filter=filter,
                        dict_factory=dict_factory,
                        retain_collection_types=retain_collection_types,
                        value_serializer=value_serializer,
                    )
                    for i in v
                ]
                try:
                    rv[a.name] = cf(items)
                except TypeError:
                    if not issubclass(cf, tuple):
                        raise
                    # Workaround for TypeError: cf.__new__() missing 1 required
                    # positional argument (which appears, for a namedturle)
                    rv[a.name] = cf(*items)
            elif isinstance(v, dict):
                df = dict_factory
                rv[a.name] = df(
                    (
                        _asdict_anything(
                            kk,
                            is_key=True,
                            filter=filter,
                            dict_factory=df,
                            retain_collection_types=retain_collection_types,
                            value_serializer=value_serializer,
                        ),
                        _asdict_anything(
                            vv,
                            is_key=False,
                            filter=filter,
                            dict_factory=df,
                            retain_collection_types=retain_collection_types,
                            value_serializer=value_serializer,
                        ),
                    )
                    for kk, vv in v.items()
                )
            else:
                rv[a.name] = v
        else:
            rv[a.name] = v
    return rv


def _asdict_anything(
    val,
    is_key,
    filter,
    dict_factory,
    retain_collection_types,
    value_serializer,
):
    """
    ``asdict`` only works on attrs instances, this works on anything.
    """
    if getattr(val.__class__, "__attrs_attrs__", None) is not None:
        # Attrs class.
        rv = asdict(
            val,
            recurse=True,
            filter=filter,
            dict_factory=dict_factory,
            retain_collection_types=retain_collection_types,
            value_serializer=value_serializer,
        )
    elif isinstance(val, (tuple, list, set, frozenset)):
        if retain_collection_types is True:
            cf = val.__class__
        elif is_key:
            cf = tuple
        else:
            cf = list

        rv = cf(
            [
                _asdict_anything(
                    i,
                    is_key=False,
                    filter=filter,
                    dict_factory=dict_factory,
                    retain_collection_types=retain_collection_types,
                    value_serializer=value_serializer,
                )
                for i in val
            ]
        )
    elif isinstance(val, dict):
        df = dict_factory
        rv = df(
            (
                _asdict_anything(
                    kk,
                    is_key=True,
                    filter=filter,
                    dict_factory=df,
                    retain_collection_types=retain_collection_types,
                    value_serializer=value_serializer,
                ),
                _asdict_anything(
                    vv,
                    is_key=False,
                    filter=filter,
                    dict_factory=df,
                    retain_collection_types=retain_collection_types,
                    value_serializer=value_serializer,
                ),
            )
            for kk, vv in val.items()
        )
    else:
        rv = val
        if value_serializer is not None:
            rv = value_serializer(None, None, rv)

    return rv


def astuple(
    inst,
    recurse=True,
    filter=None,
    tuple_factory=tuple,
    retain_collection_types=False,
):
    """
    Return the *attrs* attribute values of *inst* as a tuple.

    Optionally recurse into other *attrs*-decorated classes.

    Args:
        inst: Instance of an *attrs*-decorated class.

        recurse (bool):
            Recurse into classes that are also *attrs*-decorated.

        filter (~typing.Callable):
            A callable whose return code determines whether an attribute or
            element is included (`True`) or dropped (`False`).  Is called with
            the `attrs.Attribute` as the first argument and the value as the
            second argument.

        tuple_factory (~typing.Callable):
            A callable to produce tuples from. For example, to produce lists
            instead of tuples.

        retain_collection_types (bool):
            Do not convert to `list` or `dict` when encountering an attribute
            which type is `tuple`, `dict` or `set`. Only meaningful if
            *recurse* is `True`.

    Returns:
        Return type of *tuple_factory*

    Raises:
        attrs.exceptions.NotAnAttrsClassError:
            If *cls* is not an *attrs* class.

    ..  versionadded:: 16.2.0
    """
    attrs = fields(inst.__class__)
    rv = []
    retain = retain_collection_types  # Very long. :/
    for a in attrs:
        v = getattr(inst, a.name)
        if filter is not None and not filter(a, v):
            continue
        if recurse is True:
            if has(v.__class__):
                rv.append(
                    astuple(
                        v,
                        recurse=True,
                        filter=filter,
                        tuple_factory=tuple_factory,
                        retain_collection_types=retain,
                    )
                )
            elif isinstance(v, (tuple, list, set, frozenset)):
                cf = v.__class__ if retain is True else list
                items = [
                    (
                        astuple(
                            j,
                            recurse=True,
                            filter=filter,
                            tuple_factory=tuple_factory,
                            retain_collection_types=retain,
                        )
                        if has(j.__class__)
                        else j
                    )
                    for j in v
                ]
                try:
                    rv.append(cf(items))
                except TypeError:
                    if not issubclass(cf, tuple):
                        raise
                    # Workaround for TypeError: cf.__new__() missing 1 required
                    # positional argument (which appears, for a namedturle)
                    rv.append(cf(*items))
            elif isinstance(v, dict):
                df = v.__class__ if retain is True else dict
                rv.append(
                    df(
                        (
                            (
                                astuple(
                                    kk,
                                    tuple_factory=tuple_factory,
                                    retain_collection_types=retain,
                                )
                                if has(kk.__class__)
                                else kk
                            ),
                            (
                                astuple(
                                    vv,
                                    tuple_factory=tuple_factory,
                                    retain_collection_types=retain,
                                )
                                if has(vv.__class__)
                                else vv
                            ),
                        )
                        for kk, vv in v.items()
                    )
                )
            else:
                rv.append(v)
        else:
            rv.append(v)

    return rv if tuple_factory is list else tuple_factory(rv)


def has(cls):
    """
    Check whether *cls* is a class with *attrs* attributes.

    Args:
        cls (type): Class to introspect.

    Raises:
        TypeError: If *cls* is not a class.

    Returns:
        bool:
    """
    attrs = getattr(cls, "__attrs_attrs__", None)
    if attrs is not None:
        return True

    # No attrs, maybe it's a specialized generic (A[str])?
    generic_base = get_generic_base(cls)
    if generic_base is not None:
        generic_attrs = getattr(generic_base, "__attrs_attrs__", None)
        if generic_attrs is not None:
            # Stick it on here for speed next time.
            cls.__attrs_attrs__ = generic_attrs
        return generic_attrs is not None
    return False


def assoc(inst, **changes):
    """
    Copy *inst* and apply *changes*.

    This is different from `evolve` that applies the changes to the arguments
    that create the new instance.

    `evolve`'s behavior is preferable, but there are `edge cases`_ where it
    doesn't work. Therefore `assoc` is deprecated, but will not be removed.

    .. _`edge cases`: https://github.com/python-attrs/attrs/issues/251

    Args:
        inst: Instance of a class with *attrs* attributes.

        changes: Keyword changes in the new copy.

    Returns:
        A copy of inst with *changes* incorporated.

    Raises:
        attrs.exceptions.AttrsAttributeNotFoundError:
            If *attr_name* couldn't be found on *cls*.

        attrs.exceptions.NotAnAttrsClassError:
            If *cls* is not an *attrs* class.

    ..  deprecated:: 17.1.0
        Use `attrs.evolve` instead if you can. This function will not be
        removed du to the slightly different approach compared to
        `attrs.evolve`, though.
    """
    new = copy.copy(inst)
    attrs = fields(inst.__class__)
    for k, v in changes.items():
        a = getattr(attrs, k, NOTHING)
        if a is NOTHING:
            msg = f"{k} is not an attrs attribute on {new.__class__}."
            raise AttrsAttributeNotFoundError(msg)
        _OBJ_SETATTR(new, k, v)
    return new


def resolve_types(
    cls, globalns=None, localns=None, attribs=None, include_extras=True
):
    """
    Resolve any strings and forward annotations in type annotations.

    This is only required if you need concrete types in :class:`Attribute`'s
    *type* field. In other words, you don't need to resolve your types if you
    only use them for static type checking.

    With no arguments, names will be looked up in the module in which the class
    was created. If this is not what you want, for example, if the name only
    exists inside a method, you may pass *globalns* or *localns* to specify
    other dictionaries in which to look up these names. See the docs of
    `typing.get_type_hints` for more details.

    Args:
        cls (type): Class to resolve.

        globalns (dict | None): Dictionary containing global variables.

        localns (dict | None): Dictionary containing local variables.

        attribs (list | None):
            List of attribs for the given class. This is necessary when calling
            from inside a ``field_transformer`` since *cls* is not an *attrs*
            class yet.

        include_extras (bool):
            Resolve more accurately, if possible. Pass ``include_extras`` to
            ``typing.get_hints``, if supported by the typing module. On
            supported Python versions (3.9+), this resolves the types more
            accurately.

    Raises:
        TypeError: If *cls* is not a class.

        attrs.exceptions.NotAnAttrsClassError:
            If *cls* is not an *attrs* class and you didn't pass any attribs.

        NameError: If types cannot be resolved because of missing variables.

    Returns:
        *cls* so you can use this function also as a class decorator. Please
        note that you have to apply it **after** `attrs.define`. That means the
        decorator has to come in the line **before** `attrs.define`.

    ..  versionadded:: 20.1.0
    ..  versionadded:: 21.1.0 *attribs*
    ..  versionadded:: 23.1.0 *include_extras*
    """
    # Since calling get_type_hints is expensive we cache whether we've
    # done it already.
    if getattr(cls, "__attrs_types_resolved__", None) != cls:
        import typing

        kwargs = {"globalns": globalns, "localns": localns}

        if PY_3_9_PLUS:
            kwargs["include_extras"] = include_extras

        hints = typing.get_type_hints(cls, **kwargs)
        for field in fields(cls) if attribs is None else attribs:
            if field.name in hints:
                # Since fields have been frozen we must work around it.
                _OBJ_SETATTR(field, "type", hints[field.name])
        # We store the class we resolved so that subclasses know they haven't
        # been resolved.
        cls.__attrs_types_resolved__ = cls

    # Return the class so you can use it as a decorator too.
    return cls

# === NexusCore/openenv\Lib\site-packages\typer\params.py ===
from typing import TYPE_CHECKING, Any, Callable, List, Optional, Type, Union, overload

import click

from .models import ArgumentInfo, OptionInfo

if TYPE_CHECKING:  # pragma: no cover
    import click.shell_completion


# Overload for Option created with custom type 'parser'
@overload
def Option(
    # Parameter
    default: Optional[Any] = ...,
    *param_decls: str,
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
) -> Any:
    ...


# Overload for Option created with custom type 'click_type'
@overload
def Option(
    # Parameter
    default: Optional[Any] = ...,
    *param_decls: str,
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
) -> Any:
    ...


def Option(
    # Parameter
    default: Optional[Any] = ...,
    *param_decls: str,
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
) -> Any:
    return OptionInfo(
        # Parameter
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
        # Option
        show_default=show_default,
        prompt=prompt,
        confirmation_prompt=confirmation_prompt,
        prompt_required=prompt_required,
        hide_input=hide_input,
        is_flag=is_flag,
        flag_value=flag_value,
        count=count,
        allow_from_autoenv=allow_from_autoenv,
        help=help,
        hidden=hidden,
        show_choices=show_choices,
        show_envvar=show_envvar,
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


# Overload for Argument created with custom type 'parser'
@overload
def Argument(
    # Parameter
    default: Optional[Any] = ...,
    *,
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
) -> Any:
    ...


# Overload for Argument created with custom type 'click_type'
@overload
def Argument(
    # Parameter
    default: Optional[Any] = ...,
    *,
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
) -> Any:
    ...


def Argument(
    # Parameter
    default: Optional[Any] = ...,
    *,
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
) -> Any:
    return ArgumentInfo(
        # Parameter
        default=default,
        # Arguments can only have one param declaration
        # it will be generated from the param name
        param_decls=None,
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

# === NexusCore/openenv\Lib\site-packages\fsspec\implementations\dbfs.py ===
import base64
import urllib

import requests
import requests.exceptions
from requests.adapters import HTTPAdapter, Retry

from fsspec import AbstractFileSystem
from fsspec.spec import AbstractBufferedFile


class DatabricksException(Exception):
    """
    Helper class for exceptions raised in this module.
    """

    def __init__(self, error_code, message, details=None):
        """Create a new DatabricksException"""
        super().__init__(message)

        self.error_code = error_code
        self.message = message
        self.details = details


class DatabricksFileSystem(AbstractFileSystem):
    """
    Get access to the Databricks filesystem implementation over HTTP.
    Can be used inside and outside of a databricks cluster.
    """

    def __init__(self, instance, token, **kwargs):
        """
        Create a new DatabricksFileSystem.

        Parameters
        ----------
        instance: str
            The instance URL of the databricks cluster.
            For example for an Azure databricks cluster, this
            has the form adb-<some-number>.<two digits>.azuredatabricks.net.
        token: str
            Your personal token. Find out more
            here: https://docs.databricks.com/dev-tools/api/latest/authentication.html
        """
        self.instance = instance
        self.token = token
        self.session = requests.Session()
        self.retries = Retry(
            total=10,
            backoff_factor=0.05,
            status_forcelist=[408, 429, 500, 502, 503, 504],
        )

        self.session.mount("https://", HTTPAdapter(max_retries=self.retries))
        self.session.headers.update({"Authorization": f"Bearer {self.token}"})

        super().__init__(**kwargs)

    def ls(self, path, detail=True, **kwargs):
        """
        List the contents of the given path.

        Parameters
        ----------
        path: str
            Absolute path
        detail: bool
            Return not only the list of filenames,
            but also additional information on file sizes
            and types.
        """
        out = self._ls_from_cache(path)
        if not out:
            try:
                r = self._send_to_api(
                    method="get", endpoint="list", json={"path": path}
                )
            except DatabricksException as e:
                if e.error_code == "RESOURCE_DOES_NOT_EXIST":
                    raise FileNotFoundError(e.message) from e

                raise
            files = r.get("files", [])
            out = [
                {
                    "name": o["path"],
                    "type": "directory" if o["is_dir"] else "file",
                    "size": o["file_size"],
                }
                for o in files
            ]
            self.dircache[path] = out

        if detail:
            return out
        return [o["name"] for o in out]

    def makedirs(self, path, exist_ok=True):
        """
        Create a given absolute path and all of its parents.

        Parameters
        ----------
        path: str
            Absolute path to create
        exist_ok: bool
            If false, checks if the folder
            exists before creating it (and raises an
            Exception if this is the case)
        """
        if not exist_ok:
            try:
                # If the following succeeds, the path is already present
                self._send_to_api(
                    method="get", endpoint="get-status", json={"path": path}
                )
                raise FileExistsError(f"Path {path} already exists")
            except DatabricksException as e:
                if e.error_code == "RESOURCE_DOES_NOT_EXIST":
                    pass

        try:
            self._send_to_api(method="post", endpoint="mkdirs", json={"path": path})
        except DatabricksException as e:
            if e.error_code == "RESOURCE_ALREADY_EXISTS":
                raise FileExistsError(e.message) from e

            raise
        self.invalidate_cache(self._parent(path))

    def mkdir(self, path, create_parents=True, **kwargs):
        """
        Create a given absolute path and all of its parents.

        Parameters
        ----------
        path: str
            Absolute path to create
        create_parents: bool
            Whether to create all parents or not.
            "False" is not implemented so far.
        """
        if not create_parents:
            raise NotImplementedError

        self.mkdirs(path, **kwargs)

    def rm(self, path, recursive=False, **kwargs):
        """
        Remove the file or folder at the given absolute path.

        Parameters
        ----------
        path: str
            Absolute path what to remove
        recursive: bool
            Recursively delete all files in a folder.
        """
        try:
            self._send_to_api(
                method="post",
                endpoint="delete",
                json={"path": path, "recursive": recursive},
            )
        except DatabricksException as e:
            # This is not really an exception, it just means
            # not everything was deleted so far
            if e.error_code == "PARTIAL_DELETE":
                self.rm(path=path, recursive=recursive)
            elif e.error_code == "IO_ERROR":
                # Using the same exception as the os module would use here
                raise OSError(e.message) from e

            raise
        self.invalidate_cache(self._parent(path))

    def mv(
        self, source_path, destination_path, recursive=False, maxdepth=None, **kwargs
    ):
        """
        Move a source to a destination path.

        A note from the original [databricks API manual]
        (https://docs.databricks.com/dev-tools/api/latest/dbfs.html#move).

        When moving a large number of files the API call will time out after
        approximately 60s, potentially resulting in partially moved data.
        Therefore, for operations that move more than 10k files, we strongly
        discourage using the DBFS REST API.

        Parameters
        ----------
        source_path: str
            From where to move (absolute path)
        destination_path: str
            To where to move (absolute path)
        recursive: bool
            Not implemented to far.
        maxdepth:
            Not implemented to far.
        """
        if recursive:
            raise NotImplementedError
        if maxdepth:
            raise NotImplementedError

        try:
            self._send_to_api(
                method="post",
                endpoint="move",
                json={"source_path": source_path, "destination_path": destination_path},
            )
        except DatabricksException as e:
            if e.error_code == "RESOURCE_DOES_NOT_EXIST":
                raise FileNotFoundError(e.message) from e
            elif e.error_code == "RESOURCE_ALREADY_EXISTS":
                raise FileExistsError(e.message) from e

            raise
        self.invalidate_cache(self._parent(source_path))
        self.invalidate_cache(self._parent(destination_path))

    def _open(self, path, mode="rb", block_size="default", **kwargs):
        """
        Overwrite the base class method to make sure to create a DBFile.
        All arguments are copied from the base method.

        Only the default blocksize is allowed.
        """
        return DatabricksFile(self, path, mode=mode, block_size=block_size, **kwargs)

    def _send_to_api(self, method, endpoint, json):
        """
        Send the given json to the DBFS API
        using a get or post request (specified by the argument `method`).

        Parameters
        ----------
        method: str
            Which http method to use for communication; "get" or "post".
        endpoint: str
            Where to send the request to (last part of the API URL)
        json: dict
            Dictionary of information to send
        """
        if method == "post":
            session_call = self.session.post
        elif method == "get":
            session_call = self.session.get
        else:
            raise ValueError(f"Do not understand method {method}")

        url = urllib.parse.urljoin(f"https://{self.instance}/api/2.0/dbfs/", endpoint)

        r = session_call(url, json=json)

        # The DBFS API will return a json, also in case of an exception.
        # We want to preserve this information as good as possible.
        try:
            r.raise_for_status()
        except requests.HTTPError as e:
            # try to extract json error message
            # if that fails, fall back to the original exception
            try:
                exception_json = e.response.json()
            except Exception:
                raise e from None

            raise DatabricksException(**exception_json) from e

        return r.json()

    def _create_handle(self, path, overwrite=True):
        """
        Internal function to create a handle, which can be used to
        write blocks of a file to DBFS.
        A handle has a unique identifier which needs to be passed
        whenever written during this transaction.
        The handle is active for 10 minutes - after that a new
        write transaction needs to be created.
        Make sure to close the handle after you are finished.

        Parameters
        ----------
        path: str
            Absolute path for this file.
        overwrite: bool
            If a file already exist at this location, either overwrite
            it or raise an exception.
        """
        try:
            r = self._send_to_api(
                method="post",
                endpoint="create",
                json={"path": path, "overwrite": overwrite},
            )
            return r["handle"]
        except DatabricksException as e:
            if e.error_code == "RESOURCE_ALREADY_EXISTS":
                raise FileExistsError(e.message) from e

            raise

    def _close_handle(self, handle):
        """
        Close a handle, which was opened by :func:`_create_handle`.

        Parameters
        ----------
        handle: str
            Which handle to close.
        """
        try:
            self._send_to_api(method="post", endpoint="close", json={"handle": handle})
        except DatabricksException as e:
            if e.error_code == "RESOURCE_DOES_NOT_EXIST":
                raise FileNotFoundError(e.message) from e

            raise

    def _add_data(self, handle, data):
        """
        Upload data to an already opened file handle
        (opened by :func:`_create_handle`).
        The maximal allowed data size is 1MB after
        conversion to base64.
        Remember to close the handle when you are finished.

        Parameters
        ----------
        handle: str
            Which handle to upload data to.
        data: bytes
            Block of data to add to the handle.
        """
        data = base64.b64encode(data).decode()
        try:
            self._send_to_api(
                method="post",
                endpoint="add-block",
                json={"handle": handle, "data": data},
            )
        except DatabricksException as e:
            if e.error_code == "RESOURCE_DOES_NOT_EXIST":
                raise FileNotFoundError(e.message) from e
            elif e.error_code == "MAX_BLOCK_SIZE_EXCEEDED":
                raise ValueError(e.message) from e

            raise

    def _get_data(self, path, start, end):
        """
        Download data in bytes from a given absolute path in a block
        from [start, start+length].
        The maximum number of allowed bytes to read is 1MB.

        Parameters
        ----------
        path: str
            Absolute path to download data from
        start: int
            Start position of the block
        end: int
            End position of the block
        """
        try:
            r = self._send_to_api(
                method="get",
                endpoint="read",
                json={"path": path, "offset": start, "length": end - start},
            )
            return base64.b64decode(r["data"])
        except DatabricksException as e:
            if e.error_code == "RESOURCE_DOES_NOT_EXIST":
                raise FileNotFoundError(e.message) from e
            elif e.error_code in ["INVALID_PARAMETER_VALUE", "MAX_READ_SIZE_EXCEEDED"]:
                raise ValueError(e.message) from e

            raise

    def invalidate_cache(self, path=None):
        if path is None:
            self.dircache.clear()
        else:
            self.dircache.pop(path, None)
        super().invalidate_cache(path)


class DatabricksFile(AbstractBufferedFile):
    """
    Helper class for files referenced in the DatabricksFileSystem.
    """

    DEFAULT_BLOCK_SIZE = 1 * 2**20  # only allowed block size

    def __init__(
        self,
        fs,
        path,
        mode="rb",
        block_size="default",
        autocommit=True,
        cache_type="readahead",
        cache_options=None,
        **kwargs,
    ):
        """
        Create a new instance of the DatabricksFile.

        The blocksize needs to be the default one.
        """
        if block_size is None or block_size == "default":
            block_size = self.DEFAULT_BLOCK_SIZE

        assert block_size == self.DEFAULT_BLOCK_SIZE, (
            f"Only the default block size is allowed, not {block_size}"
        )

        super().__init__(
            fs,
            path,
            mode=mode,
            block_size=block_size,
            autocommit=autocommit,
            cache_type=cache_type,
            cache_options=cache_options or {},
            **kwargs,
        )

    def _initiate_upload(self):
        """Internal function to start a file upload"""
        self.handle = self.fs._create_handle(self.path)

    def _upload_chunk(self, final=False):
        """Internal function to add a chunk of data to a started upload"""
        self.buffer.seek(0)
        data = self.buffer.getvalue()

        data_chunks = [
            data[start:end] for start, end in self._to_sized_blocks(len(data))
        ]

        for data_chunk in data_chunks:
            self.fs._add_data(handle=self.handle, data=data_chunk)

        if final:
            self.fs._close_handle(handle=self.handle)
            return True

    def _fetch_range(self, start, end):
        """Internal function to download a block of data"""
        return_buffer = b""
        length = end - start
        for chunk_start, chunk_end in self._to_sized_blocks(length, start):
            return_buffer += self.fs._get_data(
                path=self.path, start=chunk_start, end=chunk_end
            )

        return return_buffer

    def _to_sized_blocks(self, length, start=0):
        """Helper function to split a range from 0 to total_length into bloksizes"""
        end = start + length
        for data_chunk in range(start, end, self.blocksize):
            data_start = data_chunk
            data_end = min(end, data_chunk + self.blocksize)
            yield data_start, data_end