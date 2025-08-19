
# === NexusCore/tools\exports\export_20250803_114325\combined_142.py ===

# === NexusCore/openenv\Lib\site-packages\gitdb\stream.py ===
# Copyright (C) 2010, 2011 Sebastian Thiel (byronimo@gmail.com) and contributors
#
# This module is part of GitDB and is released under
# the New BSD License: https://opensource.org/license/bsd-3-clause/

from io import BytesIO

import mmap
import os
import sys
import zlib

from gitdb.fun import (
    msb_size,
    stream_copy,
    apply_delta_data,
    connect_deltas,
    delta_types
)

from gitdb.util import (
    allocate_memory,
    LazyMixin,
    make_sha,
    write,
    close,
)

from gitdb.const import NULL_BYTE, BYTE_SPACE
from gitdb.utils.encoding import force_bytes

has_perf_mod = False
try:
    from gitdb_speedups._perf import apply_delta as c_apply_delta
    has_perf_mod = True
except ImportError:
    pass

__all__ = ('DecompressMemMapReader', 'FDCompressedSha1Writer', 'DeltaApplyReader',
           'Sha1Writer', 'FlexibleSha1Writer', 'ZippedStoreShaWriter', 'FDCompressedSha1Writer',
           'FDStream', 'NullStream')


#{ RO Streams

class DecompressMemMapReader(LazyMixin):

    """Reads data in chunks from a memory map and decompresses it. The client sees
    only the uncompressed data, respective file-like read calls are handling on-demand
    buffered decompression accordingly

    A constraint on the total size of bytes is activated, simulating
    a logical file within a possibly larger physical memory area

    To read efficiently, you clearly don't want to read individual bytes, instead,
    read a few kilobytes at least.

    **Note:** The chunk-size should be carefully selected as it will involve quite a bit
        of string copying due to the way the zlib is implemented. Its very wasteful,
        hence we try to find a good tradeoff between allocation time and number of
        times we actually allocate. An own zlib implementation would be good here
        to better support streamed reading - it would only need to keep the mmap
        and decompress it into chunks, that's all ... """
    __slots__ = ('_m', '_zip', '_buf', '_buflen', '_br', '_cws', '_cwe', '_s', '_close',
                 '_cbr', '_phi')

    max_read_size = 512 * 1024        # currently unused

    def __init__(self, m, close_on_deletion, size=None):
        """Initialize with mmap for stream reading
        :param m: must be content data - use new if you have object data and no size"""
        self._m = m
        self._zip = zlib.decompressobj()
        self._buf = None                        # buffer of decompressed bytes
        self._buflen = 0                        # length of bytes in buffer
        if size is not None:
            self._s = size                      # size of uncompressed data to read in total
        self._br = 0                            # num uncompressed bytes read
        self._cws = 0                           # start byte of compression window
        self._cwe = 0                           # end byte of compression window
        self._cbr = 0                           # number of compressed bytes read
        self._phi = False                       # is True if we parsed the header info
        self._close = close_on_deletion         # close the memmap on deletion ?

    def _set_cache_(self, attr):
        assert attr == '_s'
        # only happens for size, which is a marker to indicate we still
        # have to parse the header from the stream
        self._parse_header_info()

    def __del__(self):
        self.close()

    def _parse_header_info(self):
        """If this stream contains object data, parse the header info and skip the
        stream to a point where each read will yield object content

        :return: parsed type_string, size"""
        # read header
        # should really be enough, cgit uses 8192 I believe
        # And for good reason !! This needs to be that high for the header to be read correctly in all cases
        maxb = 8192
        self._s = maxb
        hdr = self.read(maxb)
        hdrend = hdr.find(NULL_BYTE)
        typ, size = hdr[:hdrend].split(BYTE_SPACE)
        size = int(size)
        self._s = size

        # adjust internal state to match actual header length that we ignore
        # The buffer will be depleted first on future reads
        self._br = 0
        hdrend += 1
        self._buf = BytesIO(hdr[hdrend:])
        self._buflen = len(hdr) - hdrend

        self._phi = True

        return typ, size

    #{ Interface

    @classmethod
    def new(self, m, close_on_deletion=False):
        """Create a new DecompressMemMapReader instance for acting as a read-only stream
        This method parses the object header from m and returns the parsed
        type and size, as well as the created stream instance.

        :param m: memory map on which to operate. It must be object data ( header + contents )
        :param close_on_deletion: if True, the memory map will be closed once we are
            being deleted"""
        inst = DecompressMemMapReader(m, close_on_deletion, 0)
        typ, size = inst._parse_header_info()
        return typ, size, inst

    def data(self):
        """:return: random access compatible data we are working on"""
        return self._m

    def close(self):
        """Close our underlying stream of compressed bytes if this was allowed during initialization
        :return: True if we closed the underlying stream
        :note: can be called safely
        """
        if self._close:
            if hasattr(self._m, 'close'):
                self._m.close()
            self._close = False
        # END handle resource freeing

    def compressed_bytes_read(self):
        """
        :return: number of compressed bytes read. This includes the bytes it
            took to decompress the header ( if there was one )"""
        # ABSTRACT: When decompressing a byte stream, it can be that the first
        # x bytes which were requested match the first x bytes in the loosely
        # compressed datastream. This is the worst-case assumption that the reader
        # does, it assumes that it will get at least X bytes from X compressed bytes
        # in call cases.
        # The caveat is that the object, according to our known uncompressed size,
        # is already complete, but there are still some bytes left in the compressed
        # stream that contribute to the amount of compressed bytes.
        # How can we know that we are truly done, and have read all bytes we need
        # to read ?
        # Without help, we cannot know, as we need to obtain the status of the
        # decompression. If it is not finished, we need to decompress more data
        # until it is finished, to yield the actual number of compressed bytes
        # belonging to the decompressed object
        # We are using a custom zlib module for this, if its not present,
        # we try to put in additional bytes up for decompression if feasible
        # and check for the unused_data.

        # Only scrub the stream forward if we are officially done with the
        # bytes we were to have.
        if self._br == self._s and not self._zip.unused_data:
            # manipulate the bytes-read to allow our own read method to continue
            # but keep the window at its current position
            self._br = 0
            if hasattr(self._zip, 'status'):
                while self._zip.status == zlib.Z_OK:
                    self.read(mmap.PAGESIZE)
                # END scrub-loop custom zlib
            else:
                # pass in additional pages, until we have unused data
                while not self._zip.unused_data and self._cbr != len(self._m):
                    self.read(mmap.PAGESIZE)
                # END scrub-loop default zlib
            # END handle stream scrubbing

            # reset bytes read, just to be sure
            self._br = self._s
        # END handle stream scrubbing

        # unused data ends up in the unconsumed tail, which was removed
        # from the count already
        return self._cbr

    #} END interface

    def seek(self, offset, whence=getattr(os, 'SEEK_SET', 0)):
        """Allows to reset the stream to restart reading
        :raise ValueError: If offset and whence are not 0"""
        if offset != 0 or whence != getattr(os, 'SEEK_SET', 0):
            raise ValueError("Can only seek to position 0")
        # END handle offset

        self._zip = zlib.decompressobj()
        self._br = self._cws = self._cwe = self._cbr = 0
        if self._phi:
            self._phi = False
            del(self._s)        # trigger header parsing on first access
        # END skip header

    def read(self, size=-1):
        if size < 1:
            size = self._s - self._br
        else:
            size = min(size, self._s - self._br)
        # END clamp size

        if size == 0:
            return b''
        # END handle depletion

        # deplete the buffer, then just continue using the decompress object
        # which has an own buffer. We just need this to transparently parse the
        # header from the zlib stream
        dat = b''
        if self._buf:
            if self._buflen >= size:
                # have enough data
                dat = self._buf.read(size)
                self._buflen -= size
                self._br += size
                return dat
            else:
                dat = self._buf.read()      # ouch, duplicates data
                size -= self._buflen
                self._br += self._buflen

                self._buflen = 0
                self._buf = None
            # END handle buffer len
        # END handle buffer

        # decompress some data
        # Abstract: zlib needs to operate on chunks of our memory map ( which may
        # be large ), as it will otherwise and always fill in the 'unconsumed_tail'
        # attribute which possible reads our whole map to the end, forcing
        # everything to be read from disk even though just a portion was requested.
        # As this would be a nogo, we workaround it by passing only chunks of data,
        # moving the window into the memory map along as we decompress, which keeps
        # the tail smaller than our chunk-size. This causes 'only' the chunk to be
        # copied once, and another copy of a part of it when it creates the unconsumed
        # tail. We have to use it to hand in the appropriate amount of bytes during
        # the next read.
        tail = self._zip.unconsumed_tail
        if tail:
            # move the window, make it as large as size demands. For code-clarity,
            # we just take the chunk from our map again instead of reusing the unconsumed
            # tail. The latter one would safe some memory copying, but we could end up
            # with not getting enough data uncompressed, so we had to sort that out as well.
            # Now we just assume the worst case, hence the data is uncompressed and the window
            # needs to be as large as the uncompressed bytes we want to read.
            self._cws = self._cwe - len(tail)
            self._cwe = self._cws + size
        else:
            cws = self._cws
            self._cws = self._cwe
            self._cwe = cws + size
        # END handle tail

        # if window is too small, make it larger so zip can decompress something
        if self._cwe - self._cws < 8:
            self._cwe = self._cws + 8
        # END adjust winsize

        # takes a slice, but doesn't copy the data, it says ...
        indata = self._m[self._cws:self._cwe]

        # get the actual window end to be sure we don't use it for computations
        self._cwe = self._cws + len(indata)
        dcompdat = self._zip.decompress(indata, size)
        # update the amount of compressed bytes read
        # We feed possibly overlapping chunks, which is why the unconsumed tail
        # has to be taken into consideration, as well as the unused data
        # if we hit the end of the stream
        # NOTE: Behavior changed in PY2.7 onward, which requires special handling to make the tests work properly.
        # They are thorough, and I assume it is truly working.
        # Why is this logic as convoluted as it is ? Please look at the table in
        # https://github.com/gitpython-developers/gitdb/issues/19 to learn about the test-results.
        # Basically, on py2.6, you want to use branch 1, whereas on all other python version, the second branch
        # will be the one that works.
        # However, the zlib VERSIONs as well as the platform check is used to further match the entries in the
        # table in the github issue. This is it ... it was the only way I could make this work everywhere.
        # IT's CERTAINLY GOING TO BITE US IN THE FUTURE ... .
        if getattr(zlib, 'ZLIB_RUNTIME_VERSION', zlib.ZLIB_VERSION) in ('1.2.7', '1.2.5') and not sys.platform == 'darwin':
            unused_datalen = len(self._zip.unconsumed_tail)
        else:
            unused_datalen = len(self._zip.unconsumed_tail) + len(self._zip.unused_data)
        # # end handle very special case ...

        self._cbr += len(indata) - unused_datalen
        self._br += len(dcompdat)

        if dat:
            dcompdat = dat + dcompdat
        # END prepend our cached data

        # it can happen, depending on the compression, that we get less bytes
        # than ordered as it needs the final portion of the data as well.
        # Recursively resolve that.
        # Note: dcompdat can be empty even though we still appear to have bytes
        # to read, if we are called by compressed_bytes_read - it manipulates
        # us to empty the stream
        if dcompdat and (len(dcompdat) - len(dat)) < size and self._br < self._s:
            dcompdat += self.read(size - len(dcompdat))
        # END handle special case
        return dcompdat


class DeltaApplyReader(LazyMixin):

    """A reader which dynamically applies pack deltas to a base object, keeping the
    memory demands to a minimum.

    The size of the final object is only obtainable once all deltas have been
    applied, unless it is retrieved from a pack index.

    The uncompressed Delta has the following layout (MSB being a most significant
    bit encoded dynamic size):

    * MSB Source Size - the size of the base against which the delta was created
    * MSB Target Size - the size of the resulting data after the delta was applied
    * A list of one byte commands (cmd) which are followed by a specific protocol:

     * cmd & 0x80 - copy delta_data[offset:offset+size]

      * Followed by an encoded offset into the delta data
      * Followed by an encoded size of the chunk to copy

     *  cmd & 0x7f - insert

      * insert cmd bytes from the delta buffer into the output stream

     * cmd == 0 - invalid operation ( or error in delta stream )
    """
    __slots__ = (
        "_bstream",             # base stream to which to apply the deltas
        "_dstreams",            # tuple of delta stream readers
        "_mm_target",           # memory map of the delta-applied data
        "_size",                # actual number of bytes in _mm_target
        "_br"                   # number of bytes read
    )

    #{ Configuration
    k_max_memory_move = 250 * 1000 * 1000
    #} END configuration

    def __init__(self, stream_list):
        """Initialize this instance with a list of streams, the first stream being
        the delta to apply on top of all following deltas, the last stream being the
        base object onto which to apply the deltas"""
        assert len(stream_list) > 1, "Need at least one delta and one base stream"

        self._bstream = stream_list[-1]
        self._dstreams = tuple(stream_list[:-1])
        self._br = 0

    def _set_cache_too_slow_without_c(self, attr):
        # the direct algorithm is fastest and most direct if there is only one
        # delta. Also, the extra overhead might not be worth it for items smaller
        # than X - definitely the case in python, every function call costs
        # huge amounts of time
        # if len(self._dstreams) * self._bstream.size < self.k_max_memory_move:
        if len(self._dstreams) == 1:
            return self._set_cache_brute_(attr)

        # Aggregate all deltas into one delta in reverse order. Hence we take
        # the last delta, and reverse-merge its ancestor delta, until we receive
        # the final delta data stream.
        dcl = connect_deltas(self._dstreams)

        # call len directly, as the (optional) c version doesn't implement the sequence
        # protocol
        if dcl.rbound() == 0:
            self._size = 0
            self._mm_target = allocate_memory(0)
            return
        # END handle empty list

        self._size = dcl.rbound()
        self._mm_target = allocate_memory(self._size)

        bbuf = allocate_memory(self._bstream.size)
        stream_copy(self._bstream.read, bbuf.write, self._bstream.size, 256 * mmap.PAGESIZE)

        # APPLY CHUNKS
        write = self._mm_target.write
        dcl.apply(bbuf, write)

        self._mm_target.seek(0)

    def _set_cache_brute_(self, attr):
        """If we are here, we apply the actual deltas"""
        # TODO: There should be a special case if there is only one stream
        # Then the default-git algorithm should perform a tad faster, as the
        # delta is not peaked into, causing less overhead.
        buffer_info_list = list()
        max_target_size = 0
        for dstream in self._dstreams:
            buf = dstream.read(512)         # read the header information + X
            offset, src_size = msb_size(buf)
            offset, target_size = msb_size(buf, offset)
            buffer_info_list.append((buf[offset:], offset, src_size, target_size))
            max_target_size = max(max_target_size, target_size)
        # END for each delta stream

        # sanity check - the first delta to apply should have the same source
        # size as our actual base stream
        base_size = self._bstream.size
        target_size = max_target_size

        # if we have more than 1 delta to apply, we will swap buffers, hence we must
        # assure that all buffers we use are large enough to hold all the results
        if len(self._dstreams) > 1:
            base_size = target_size = max(base_size, max_target_size)
        # END adjust buffer sizes

        # Allocate private memory map big enough to hold the first base buffer
        # We need random access to it
        bbuf = allocate_memory(base_size)
        stream_copy(self._bstream.read, bbuf.write, base_size, 256 * mmap.PAGESIZE)

        # allocate memory map large enough for the largest (intermediate) target
        # We will use it as scratch space for all delta ops. If the final
        # target buffer is smaller than our allocated space, we just use parts
        # of it upon return.
        tbuf = allocate_memory(target_size)

        # for each delta to apply, memory map the decompressed delta and
        # work on the op-codes to reconstruct everything.
        # For the actual copying, we use a seek and write pattern of buffer
        # slices.
        final_target_size = None
        for (dbuf, offset, src_size, target_size), dstream in zip(reversed(buffer_info_list), reversed(self._dstreams)):
            # allocate a buffer to hold all delta data - fill in the data for
            # fast access. We do this as we know that reading individual bytes
            # from our stream would be slower than necessary ( although possible )
            # The dbuf buffer contains commands after the first two MSB sizes, the
            # offset specifies the amount of bytes read to get the sizes.
            ddata = allocate_memory(dstream.size - offset)
            ddata.write(dbuf)
            # read the rest from the stream. The size we give is larger than necessary
            stream_copy(dstream.read, ddata.write, dstream.size, 256 * mmap.PAGESIZE)

            #######################################################################
            if 'c_apply_delta' in globals():
                c_apply_delta(bbuf, ddata, tbuf)
            else:
                apply_delta_data(bbuf, src_size, ddata, len(ddata), tbuf.write)
            #######################################################################

            # finally, swap out source and target buffers. The target is now the
            # base for the next delta to apply
            bbuf, tbuf = tbuf, bbuf
            bbuf.seek(0)
            tbuf.seek(0)
            final_target_size = target_size
        # END for each delta to apply

        # its already seeked to 0, constrain it to the actual size
        # NOTE: in the end of the loop, it swaps buffers, hence our target buffer
        # is not tbuf, but bbuf !
        self._mm_target = bbuf
        self._size = final_target_size

    #{ Configuration
    if not has_perf_mod:
        _set_cache_ = _set_cache_brute_
    else:
        _set_cache_ = _set_cache_too_slow_without_c

    #} END configuration

    def read(self, count=0):
        bl = self._size - self._br      # bytes left
        if count < 1 or count > bl:
            count = bl
        # NOTE: we could check for certain size limits, and possibly
        # return buffers instead of strings to prevent byte copying
        data = self._mm_target.read(count)
        self._br += len(data)
        return data

    def seek(self, offset, whence=getattr(os, 'SEEK_SET', 0)):
        """Allows to reset the stream to restart reading

        :raise ValueError: If offset and whence are not 0"""
        if offset != 0 or whence != getattr(os, 'SEEK_SET', 0):
            raise ValueError("Can only seek to position 0")
        # END handle offset
        self._br = 0
        self._mm_target.seek(0)

    #{ Interface

    @classmethod
    def new(cls, stream_list):
        """
        Convert the given list of streams into a stream which resolves deltas
        when reading from it.

        :param stream_list: two or more stream objects, first stream is a Delta
            to the object that you want to resolve, followed by N additional delta
            streams. The list's last stream must be a non-delta stream.

        :return: Non-Delta OPackStream object whose stream can be used to obtain
            the decompressed resolved data
        :raise ValueError: if the stream list cannot be handled"""
        if len(stream_list) < 2:
            raise ValueError("Need at least two streams")
        # END single object special handling

        if stream_list[-1].type_id in delta_types:
            raise ValueError(
                "Cannot resolve deltas if there is no base object stream, last one was type: %s" % stream_list[-1].type)
        # END check stream
        return cls(stream_list)

    #} END interface

    #{ OInfo like Interface

    @property
    def type(self):
        return self._bstream.type

    @property
    def type_id(self):
        return self._bstream.type_id

    @property
    def size(self):
        """:return: number of uncompressed bytes in the stream"""
        return self._size

    #} END oinfo like interface


#} END RO streams


#{ W Streams

class Sha1Writer:

    """Simple stream writer which produces a sha whenever you like as it degests
    everything it is supposed to write"""
    __slots__ = "sha1"

    def __init__(self):
        self.sha1 = make_sha()

    #{ Stream Interface

    def write(self, data):
        """:raise IOError: If not all bytes could be written
        :param data: byte object
        :return: length of incoming data"""

        self.sha1.update(data)

        return len(data)

    # END stream interface

    #{ Interface

    def sha(self, as_hex=False):
        """:return: sha so far
        :param as_hex: if True, sha will be hex-encoded, binary otherwise"""
        if as_hex:
            return self.sha1.hexdigest()
        return self.sha1.digest()

    #} END interface


class FlexibleSha1Writer(Sha1Writer):

    """Writer producing a sha1 while passing on the written bytes to the given
    write function"""
    __slots__ = 'writer'

    def __init__(self, writer):
        Sha1Writer.__init__(self)
        self.writer = writer

    def write(self, data):
        Sha1Writer.write(self, data)
        self.writer(data)


class ZippedStoreShaWriter(Sha1Writer):

    """Remembers everything someone writes to it and generates a sha"""
    __slots__ = ('buf', 'zip')

    def __init__(self):
        Sha1Writer.__init__(self)
        self.buf = BytesIO()
        self.zip = zlib.compressobj(zlib.Z_BEST_SPEED)

    def __getattr__(self, attr):
        return getattr(self.buf, attr)

    def write(self, data):
        alen = Sha1Writer.write(self, data)
        self.buf.write(self.zip.compress(data))

        return alen

    def close(self):
        self.buf.write(self.zip.flush())

    def seek(self, offset, whence=getattr(os, 'SEEK_SET', 0)):
        """Seeking currently only supports to rewind written data
        Multiple writes are not supported"""
        if offset != 0 or whence != getattr(os, 'SEEK_SET', 0):
            raise ValueError("Can only seek to position 0")
        # END handle offset
        self.buf.seek(0)

    def getvalue(self):
        """:return: string value from the current stream position to the end"""
        return self.buf.getvalue()


class FDCompressedSha1Writer(Sha1Writer):

    """Digests data written to it, making the sha available, then compress the
    data and write it to the file descriptor

    **Note:** operates on raw file descriptors
    **Note:** for this to work, you have to use the close-method of this instance"""
    __slots__ = ("fd", "sha1", "zip")

    # default exception
    exc = IOError("Failed to write all bytes to filedescriptor")

    def __init__(self, fd):
        super().__init__()
        self.fd = fd
        self.zip = zlib.compressobj(zlib.Z_BEST_SPEED)

    #{ Stream Interface

    def write(self, data):
        """:raise IOError: If not all bytes could be written
        :return: length of incoming data"""
        self.sha1.update(data)
        cdata = self.zip.compress(data)
        bytes_written = write(self.fd, cdata)

        if bytes_written != len(cdata):
            raise self.exc

        return len(data)

    def close(self):
        remainder = self.zip.flush()
        if write(self.fd, remainder) != len(remainder):
            raise self.exc
        return close(self.fd)

    #} END stream interface


class FDStream:

    """A simple wrapper providing the most basic functions on a file descriptor
    with the fileobject interface. Cannot use os.fdopen as the resulting stream
    takes ownership"""
    __slots__ = ("_fd", '_pos')

    def __init__(self, fd):
        self._fd = fd
        self._pos = 0

    def write(self, data):
        self._pos += len(data)
        os.write(self._fd, data)

    def read(self, count=0):
        if count == 0:
            count = os.path.getsize(self._filepath)
        # END handle read everything

        bytes = os.read(self._fd, count)
        self._pos += len(bytes)
        return bytes

    def fileno(self):
        return self._fd

    def tell(self):
        return self._pos

    def close(self):
        close(self._fd)


class NullStream:

    """A stream that does nothing but providing a stream interface.
    Use it like /dev/null"""
    __slots__ = tuple()

    def read(self, size=0):
        return ''

    def close(self):
        pass

    def write(self, data):
        return len(data)


#} END W streams

# === NexusCore/openenv\Lib\site-packages\nltk\langnames.py ===
# Natural Language Toolkit: Language Codes
#
# Copyright (C) 2022-2023 NLTK Project
# Author: Eric Kafe <kafe.eric@gmail.com>
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT
#
# iso639-3 language codes (C) https://iso639-3.sil.org/

"""
Translate between language names and language codes.

The iso639-3 language codes were downloaded from the registration authority at
https://iso639-3.sil.org/

The iso639-3 codeset is evolving, so retired language codes are kept in the
"iso639retired" dictionary, which is used as fallback by the wrapper functions
"langname" and "langcode", in order to support the lookup of retired codes.

The "langcode" function returns the current iso639-3 code if there is one,
and falls back to the retired code otherwise. As specified by BCP-47,
it returns the shortest (2-letter) code by default, but 3-letter codes
are also available:

    >>> import nltk.langnames as lgn
    >>> lgn.langname('fri')          #'fri' is a retired code
    'Western Frisian'

    The current code is different from the retired one:
    >>> lgn.langcode('Western Frisian')
    'fy'

    >>> lgn.langcode('Western Frisian', typ = 3)
    'fry'

"""

import re
from warnings import warn

from nltk.corpus import bcp47

codepattern = re.compile("[a-z][a-z][a-z]?")


def langname(tag, typ="full"):
    """
    Convert a composite BCP-47 tag to a language name

    >>> from nltk.langnames import langname
    >>> langname('ca-Latn-ES-valencia')
    'Catalan: Latin: Spain: Valencian'

    >>> langname('ca-Latn-ES-valencia', typ="short")
    'Catalan'
    """
    tags = tag.split("-")
    code = tags[0].lower()
    if codepattern.fullmatch(code):
        if code in iso639retired:  # retired codes
            return iso639retired[code]
        elif code in iso639short:  # 3-letter codes
            code2 = iso639short[code]  # convert to 2-letter code
            warn(f"Shortening {code!r} to {code2!r}", stacklevel=2)
            tag = "-".join([code2] + tags[1:])
        name = bcp47.name(tag)  # parse according to BCP-47
        if typ == "full":
            return name  # include all subtags
        elif name:
            return name.split(":")[0]  # only the language subtag
    else:
        warn(f"Could not find code in {code!r}", stacklevel=2)


def langcode(name, typ=2):
    """
    Convert language name to iso639-3 language code. Returns the short 2-letter
    code by default, if one is available, and the 3-letter code otherwise:

    >>> from nltk.langnames import langcode
    >>> langcode('Modern Greek (1453-)')
    'el'

    Specify 'typ=3' to get the 3-letter code:

    >>> langcode('Modern Greek (1453-)', typ=3)
    'ell'
    """
    if name in bcp47.langcode:
        code = bcp47.langcode[name]
        if typ == 3 and code in iso639long:
            code = iso639long[code]  # convert to 3-letter code
        return code
    elif name in iso639code_retired:
        return iso639code_retired[name]
    else:
        warn(f"Could not find language in {name!r}", stacklevel=2)


# =======================================================================
# Translate betwwen Wikidata Q-codes and BCP-47 codes or names
# .......................................................................


def tag2q(tag):
    """
    Convert BCP-47 tag to Wikidata Q-code

    >>> tag2q('nds-u-sd-demv')
    'Q4289225'
    """
    return bcp47.wiki_q[tag]


def q2tag(qcode):
    """
    Convert Wikidata Q-code to BCP-47 tag

    >>> q2tag('Q4289225')
    'nds-u-sd-demv'
    """
    return wiki_bcp47[qcode]


def q2name(qcode, typ="full"):
    """
    Convert Wikidata Q-code to BCP-47 (full or short) language name

    >>> q2name('Q4289225')
    'Low German: Mecklenburg-Vorpommern'

    >>> q2name('Q4289225', "short")
    'Low German'
    """
    return langname(q2tag(qcode), typ)


def lang2q(name):
    """
    Convert simple language name to Wikidata Q-code

    >>> lang2q('Low German')
    'Q25433'
    """
    return tag2q(langcode(name))


# ======================================================================
# Data dictionaries
# ......................................................................


def inverse_dict(dic):
    """Return inverse mapping, but only if it is bijective"""
    if len(dic.keys()) == len(set(dic.values())):
        return {val: key for (key, val) in dic.items()}
    else:
        warn("This dictionary has no bijective inverse mapping.")


bcp47.load_wiki_q()  # Wikidata conversion table needs to be loaded explicitly
wiki_bcp47 = inverse_dict(bcp47.wiki_q)

iso639short = {
    "aar": "aa",
    "abk": "ab",
    "afr": "af",
    "aka": "ak",
    "amh": "am",
    "ara": "ar",
    "arg": "an",
    "asm": "as",
    "ava": "av",
    "ave": "ae",
    "aym": "ay",
    "aze": "az",
    "bak": "ba",
    "bam": "bm",
    "bel": "be",
    "ben": "bn",
    "bis": "bi",
    "bod": "bo",
    "bos": "bs",
    "bre": "br",
    "bul": "bg",
    "cat": "ca",
    "ces": "cs",
    "cha": "ch",
    "che": "ce",
    "chu": "cu",
    "chv": "cv",
    "cor": "kw",
    "cos": "co",
    "cre": "cr",
    "cym": "cy",
    "dan": "da",
    "deu": "de",
    "div": "dv",
    "dzo": "dz",
    "ell": "el",
    "eng": "en",
    "epo": "eo",
    "est": "et",
    "eus": "eu",
    "ewe": "ee",
    "fao": "fo",
    "fas": "fa",
    "fij": "fj",
    "fin": "fi",
    "fra": "fr",
    "fry": "fy",
    "ful": "ff",
    "gla": "gd",
    "gle": "ga",
    "glg": "gl",
    "glv": "gv",
    "grn": "gn",
    "guj": "gu",
    "hat": "ht",
    "hau": "ha",
    "hbs": "sh",
    "heb": "he",
    "her": "hz",
    "hin": "hi",
    "hmo": "ho",
    "hrv": "hr",
    "hun": "hu",
    "hye": "hy",
    "ibo": "ig",
    "ido": "io",
    "iii": "ii",
    "iku": "iu",
    "ile": "ie",
    "ina": "ia",
    "ind": "id",
    "ipk": "ik",
    "isl": "is",
    "ita": "it",
    "jav": "jv",
    "jpn": "ja",
    "kal": "kl",
    "kan": "kn",
    "kas": "ks",
    "kat": "ka",
    "kau": "kr",
    "kaz": "kk",
    "khm": "km",
    "kik": "ki",
    "kin": "rw",
    "kir": "ky",
    "kom": "kv",
    "kon": "kg",
    "kor": "ko",
    "kua": "kj",
    "kur": "ku",
    "lao": "lo",
    "lat": "la",
    "lav": "lv",
    "lim": "li",
    "lin": "ln",
    "lit": "lt",
    "ltz": "lb",
    "lub": "lu",
    "lug": "lg",
    "mah": "mh",
    "mal": "ml",
    "mar": "mr",
    "mkd": "mk",
    "mlg": "mg",
    "mlt": "mt",
    "mon": "mn",
    "mri": "mi",
    "msa": "ms",
    "mya": "my",
    "nau": "na",
    "nav": "nv",
    "nbl": "nr",
    "nde": "nd",
    "ndo": "ng",
    "nep": "ne",
    "nld": "nl",
    "nno": "nn",
    "nob": "nb",
    "nor": "no",
    "nya": "ny",
    "oci": "oc",
    "oji": "oj",
    "ori": "or",
    "orm": "om",
    "oss": "os",
    "pan": "pa",
    "pli": "pi",
    "pol": "pl",
    "por": "pt",
    "pus": "ps",
    "que": "qu",
    "roh": "rm",
    "ron": "ro",
    "run": "rn",
    "rus": "ru",
    "sag": "sg",
    "san": "sa",
    "sin": "si",
    "slk": "sk",
    "slv": "sl",
    "sme": "se",
    "smo": "sm",
    "sna": "sn",
    "snd": "sd",
    "som": "so",
    "sot": "st",
    "spa": "es",
    "sqi": "sq",
    "srd": "sc",
    "srp": "sr",
    "ssw": "ss",
    "sun": "su",
    "swa": "sw",
    "swe": "sv",
    "tah": "ty",
    "tam": "ta",
    "tat": "tt",
    "tel": "te",
    "tgk": "tg",
    "tgl": "tl",
    "tha": "th",
    "tir": "ti",
    "ton": "to",
    "tsn": "tn",
    "tso": "ts",
    "tuk": "tk",
    "tur": "tr",
    "twi": "tw",
    "uig": "ug",
    "ukr": "uk",
    "urd": "ur",
    "uzb": "uz",
    "ven": "ve",
    "vie": "vi",
    "vol": "vo",
    "wln": "wa",
    "wol": "wo",
    "xho": "xh",
    "yid": "yi",
    "yor": "yo",
    "zha": "za",
    "zho": "zh",
    "zul": "zu",
}


iso639retired = {
    "fri": "Western Frisian",
    "auv": "Auvergnat",
    "gsc": "Gascon",
    "lms": "Limousin",
    "lnc": "Languedocien",
    "prv": "Provençal",
    "amd": "Amapá Creole",
    "bgh": "Bogan",
    "bnh": "Banawá",
    "bvs": "Belgian Sign Language",
    "ccy": "Southern Zhuang",
    "cit": "Chittagonian",
    "flm": "Falam Chin",
    "jap": "Jaruára",
    "kob": "Kohoroxitari",
    "mob": "Moinba",
    "mzf": "Aiku",
    "nhj": "Tlalitzlipa Nahuatl",
    "nhs": "Southeastern Puebla Nahuatl",
    "occ": "Occidental",
    "tmx": "Tomyang",
    "tot": "Patla-Chicontla Totonac",
    "xmi": "Miarrã",
    "yib": "Yinglish",
    "ztc": "Lachirioag Zapotec",
    "atf": "Atuence",
    "bqe": "Navarro-Labourdin Basque",
    "bsz": "Souletin Basque",
    "aex": "Amerax",
    "ahe": "Ahe",
    "aiz": "Aari",
    "akn": "Amikoana",
    "arf": "Arafundi",
    "azr": "Adzera",
    "bcx": "Pamona",
    "bii": "Bisu",
    "bke": "Bengkulu",
    "blu": "Hmong Njua",
    "boc": "Bakung Kenyah",
    "bsd": "Sarawak Bisaya",
    "bwv": "Bahau River Kenyah",
    "bxt": "Buxinhua",
    "byu": "Buyang",
    "ccx": "Northern Zhuang",
    "cru": "Carútana",
    "dat": "Darang Deng",
    "dyk": "Land Dayak",
    "eni": "Enim",
    "fiz": "Izere",
    "gen": "Geman Deng",
    "ggh": "Garreh-Ajuran",
    "itu": "Itutang",
    "kds": "Lahu Shi",
    "knh": "Kayan River Kenyah",
    "krg": "North Korowai",
    "krq": "Krui",
    "kxg": "Katingan",
    "lmt": "Lematang",
    "lnt": "Lintang",
    "lod": "Berawan",
    "mbg": "Northern Nambikuára",
    "mdo": "Southwest Gbaya",
    "mhv": "Arakanese",
    "miv": "Mimi",
    "mqd": "Madang",
    "nky": "Khiamniungan Naga",
    "nxj": "Nyadu",
    "ogn": "Ogan",
    "ork": "Orokaiva",
    "paj": "Ipeka-Tapuia",
    "pec": "Southern Pesisir",
    "pen": "Penesak",
    "plm": "Palembang",
    "poj": "Lower Pokomo",
    "pun": "Pubian",
    "rae": "Ranau",
    "rjb": "Rajbanshi",
    "rws": "Rawas",
    "sdd": "Semendo",
    "sdi": "Sindang Kelingi",
    "skl": "Selako",
    "slb": "Kahumamahon Saluan",
    "srj": "Serawai",
    "suf": "Tarpia",
    "suh": "Suba",
    "suu": "Sungkai",
    "szk": "Sizaki",
    "tle": "Southern Marakwet",
    "tnj": "Tanjong",
    "ttx": "Tutong 1",
    "ubm": "Upper Baram Kenyah",
    "vky": "Kayu Agung",
    "vmo": "Muko-Muko",
    "wre": "Ware",
    "xah": "Kahayan",
    "xkm": "Mahakam Kenyah",
    "xuf": "Kunfal",
    "yio": "Dayao Yi",
    "ymj": "Muji Yi",
    "ypl": "Pula Yi",
    "ypw": "Puwa Yi",
    "ywm": "Wumeng Yi",
    "yym": "Yuanjiang-Mojiang Yi",
    "mly": "Malay (individual language)",
    "muw": "Mundari",
    "xst": "Silt'e",
    "ope": "Old Persian",
    "scc": "Serbian",
    "scr": "Croatian",
    "xsk": "Sakan",
    "mol": "Moldavian",
    "aay": "Aariya",
    "acc": "Cubulco Achí",
    "cbm": "Yepocapa Southwestern Cakchiquel",
    "chs": "Chumash",
    "ckc": "Northern Cakchiquel",
    "ckd": "South Central Cakchiquel",
    "cke": "Eastern Cakchiquel",
    "ckf": "Southern Cakchiquel",
    "cki": "Santa María De Jesús Cakchiquel",
    "ckj": "Santo Domingo Xenacoj Cakchiquel",
    "ckk": "Acatenango Southwestern Cakchiquel",
    "ckw": "Western Cakchiquel",
    "cnm": "Ixtatán Chuj",
    "cti": "Tila Chol",
    "cun": "Cunén Quiché",
    "eml": "Emiliano-Romagnolo",
    "eur": "Europanto",
    "gmo": "Gamo-Gofa-Dawro",
    "hsf": "Southeastern Huastec",
    "hva": "San Luís Potosí Huastec",
    "ixi": "Nebaj Ixil",
    "ixj": "Chajul Ixil",
    "jai": "Western Jacalteco",
    "mms": "Southern Mam",
    "mpf": "Tajumulco Mam",
    "mtz": "Tacanec",
    "mvc": "Central Mam",
    "mvj": "Todos Santos Cuchumatán Mam",
    "poa": "Eastern Pokomam",
    "pob": "Western Pokomchí",
    "pou": "Southern Pokomam",
    "ppv": "Papavô",
    "quj": "Joyabaj Quiché",
    "qut": "West Central Quiché",
    "quu": "Eastern Quiché",
    "qxi": "San Andrés Quiché",
    "sic": "Malinguat",
    "stc": "Santa Cruz",
    "tlz": "Toala'",
    "tzb": "Bachajón Tzeltal",
    "tzc": "Chamula Tzotzil",
    "tze": "Chenalhó Tzotzil",
    "tzs": "San Andrés Larrainzar Tzotzil",
    "tzt": "Western Tzutujil",
    "tzu": "Huixtán Tzotzil",
    "tzz": "Zinacantán Tzotzil",
    "vlr": "Vatrata",
    "yus": "Chan Santa Cruz Maya",
    "nfg": "Nyeng",
    "nfk": "Shakara",
    "agp": "Paranan",
    "bhk": "Albay Bicolano",
    "bkb": "Finallig",
    "btb": "Beti (Cameroon)",
    "cjr": "Chorotega",
    "cmk": "Chimakum",
    "drh": "Darkhat",
    "drw": "Darwazi",
    "gav": "Gabutamon",
    "mof": "Mohegan-Montauk-Narragansett",
    "mst": "Cataelano Mandaya",
    "myt": "Sangab Mandaya",
    "rmr": "Caló",
    "sgl": "Sanglechi-Ishkashimi",
    "sul": "Surigaonon",
    "sum": "Sumo-Mayangna",
    "tnf": "Tangshewi",
    "wgw": "Wagawaga",
    "ayx": "Ayi (China)",
    "bjq": "Southern Betsimisaraka Malagasy",
    "dha": "Dhanwar (India)",
    "dkl": "Kolum So Dogon",
    "mja": "Mahei",
    "nbf": "Naxi",
    "noo": "Nootka",
    "tie": "Tingal",
    "tkk": "Takpa",
    "baz": "Tunen",
    "bjd": "Bandjigali",
    "ccq": "Chaungtha",
    "cka": "Khumi Awa Chin",
    "dap": "Nisi (India)",
    "dwl": "Walo Kumbe Dogon",
    "elp": "Elpaputih",
    "gbc": "Garawa",
    "gio": "Gelao",
    "hrr": "Horuru",
    "ibi": "Ibilo",
    "jar": "Jarawa (Nigeria)",
    "kdv": "Kado",
    "kgh": "Upper Tanudan Kalinga",
    "kpp": "Paku Karen",
    "kzh": "Kenuzi-Dongola",
    "lcq": "Luhu",
    "mgx": "Omati",
    "nln": "Durango Nahuatl",
    "pbz": "Palu",
    "pgy": "Pongyong",
    "sca": "Sansu",
    "tlw": "South Wemale",
    "unp": "Worora",
    "wiw": "Wirangu",
    "ybd": "Yangbye",
    "yen": "Yendang",
    "yma": "Yamphe",
    "daf": "Dan",
    "djl": "Djiwarli",
    "ggr": "Aghu Tharnggalu",
    "ilw": "Talur",
    "izi": "Izi-Ezaa-Ikwo-Mgbo",
    "meg": "Mea",
    "mld": "Malakhel",
    "mnt": "Maykulan",
    "mwd": "Mudbura",
    "myq": "Forest Maninka",
    "nbx": "Ngura",
    "nlr": "Ngarla",
    "pcr": "Panang",
    "ppr": "Piru",
    "tgg": "Tangga",
    "wit": "Wintu",
    "xia": "Xiandao",
    "yiy": "Yir Yoront",
    "yos": "Yos",
    "emo": "Emok",
    "ggm": "Gugu Mini",
    "leg": "Lengua",
    "lmm": "Lamam",
    "mhh": "Maskoy Pidgin",
    "puz": "Purum Naga",
    "sap": "Sanapaná",
    "yuu": "Yugh",
    "aam": "Aramanik",
    "adp": "Adap",
    "aue": "ǂKxʼauǁʼein",
    "bmy": "Bemba (Democratic Republic of Congo)",
    "bxx": "Borna (Democratic Republic of Congo)",
    "byy": "Buya",
    "dzd": "Daza",
    "gfx": "Mangetti Dune ǃXung",
    "gti": "Gbati-ri",
    "ime": "Imeraguen",
    "kbf": "Kakauhua",
    "koj": "Sara Dunjo",
    "kwq": "Kwak",
    "kxe": "Kakihum",
    "lii": "Lingkhim",
    "mwj": "Maligo",
    "nnx": "Ngong",
    "oun": "ǃOǃung",
    "pmu": "Mirpur Panjabi",
    "sgo": "Songa",
    "thx": "The",
    "tsf": "Southwestern Tamang",
    "uok": "Uokha",
    "xsj": "Subi",
    "yds": "Yiddish Sign Language",
    "ymt": "Mator-Taygi-Karagas",
    "ynh": "Yangho",
    "bgm": "Baga Mboteni",
    "btl": "Bhatola",
    "cbe": "Chipiajes",
    "cbh": "Cagua",
    "coy": "Coyaima",
    "cqu": "Chilean Quechua",
    "cum": "Cumeral",
    "duj": "Dhuwal",
    "ggn": "Eastern Gurung",
    "ggo": "Southern Gondi",
    "guv": "Gey",
    "iap": "Iapama",
    "ill": "Iranun",
    "kgc": "Kasseng",
    "kox": "Coxima",
    "ktr": "Kota Marudu Tinagas",
    "kvs": "Kunggara",
    "kzj": "Coastal Kadazan",
    "kzt": "Tambunan Dusun",
    "nad": "Nijadali",
    "nts": "Natagaimas",
    "ome": "Omejes",
    "pmc": "Palumata",
    "pod": "Ponares",
    "ppa": "Pao",
    "pry": "Pray 3",
    "rna": "Runa",
    "svr": "Savara",
    "tdu": "Tempasuk Dusun",
    "thc": "Tai Hang Tong",
    "tid": "Tidong",
    "tmp": "Tai Mène",
    "tne": "Tinoc Kallahan",
    "toe": "Tomedes",
    "xba": "Kamba (Brazil)",
    "xbx": "Kabixí",
    "xip": "Xipináwa",
    "xkh": "Karahawyana",
    "yri": "Yarí",
    "jeg": "Jeng",
    "kgd": "Kataang",
    "krm": "Krim",
    "prb": "Lua'",
    "puk": "Pu Ko",
    "rie": "Rien",
    "rsi": "Rennellese Sign Language",
    "skk": "Sok",
    "snh": "Shinabo",
    "lsg": "Lyons Sign Language",
    "mwx": "Mediak",
    "mwy": "Mosiro",
    "ncp": "Ndaktup",
    "ais": "Nataoran Amis",
    "asd": "Asas",
    "dit": "Dirari",
    "dud": "Hun-Saare",
    "lba": "Lui",
    "llo": "Khlor",
    "myd": "Maramba",
    "myi": "Mina (India)",
    "nns": "Ningye",
    "aoh": "Arma",
    "ayy": "Tayabas Ayta",
    "bbz": "Babalia Creole Arabic",
    "bpb": "Barbacoas",
    "cca": "Cauca",
    "cdg": "Chamari",
    "dgu": "Degaru",
    "drr": "Dororo",
    "ekc": "Eastern Karnic",
    "gli": "Guliguli",
    "kjf": "Khalaj",
    "kxl": "Nepali Kurux",
    "kxu": "Kui (India)",
    "lmz": "Lumbee",
    "nxu": "Narau",
    "plp": "Palpa",
    "sdm": "Semandang",
    "tbb": "Tapeba",
    "xrq": "Karranga",
    "xtz": "Tasmanian",
    "zir": "Ziriya",
    "thw": "Thudam",
    "bic": "Bikaru",
    "bij": "Vaghat-Ya-Bijim-Legeri",
    "blg": "Balau",
    "gji": "Geji",
    "mvm": "Muya",
    "ngo": "Ngoni",
    "pat": "Papitalai",
    "vki": "Ija-Zuba",
    "wra": "Warapu",
    "ajt": "Judeo-Tunisian Arabic",
    "cug": "Chungmboko",
    "lak": "Laka (Nigeria)",
    "lno": "Lango (South Sudan)",
    "pii": "Pini",
    "smd": "Sama",
    "snb": "Sebuyau",
    "uun": "Kulon-Pazeh",
    "wrd": "Warduji",
    "wya": "Wyandot",
}


iso639long = inverse_dict(iso639short)

iso639code_retired = inverse_dict(iso639retired)

# === NexusCore/openenv\Lib\site-packages\tornado\routing.py ===
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

"""Flexible routing implementation.

Tornado routes HTTP requests to appropriate handlers using `Router`
class implementations. The `tornado.web.Application` class is a
`Router` implementation and may be used directly, or the classes in
this module may be used for additional flexibility. The `RuleRouter`
class can match on more criteria than `.Application`, or the `Router`
interface can be subclassed for maximum customization.

`Router` interface extends `~.httputil.HTTPServerConnectionDelegate`
to provide additional routing capabilities. This also means that any
`Router` implementation can be used directly as a ``request_callback``
for `~.httpserver.HTTPServer` constructor.

`Router` subclass must implement a ``find_handler`` method to provide
a suitable `~.httputil.HTTPMessageDelegate` instance to handle the
request:

.. code-block:: python

    class CustomRouter(Router):
        def find_handler(self, request, **kwargs):
            # some routing logic providing a suitable HTTPMessageDelegate instance
            return MessageDelegate(request.connection)

    class MessageDelegate(HTTPMessageDelegate):
        def __init__(self, connection):
            self.connection = connection

        def finish(self):
            self.connection.write_headers(
                ResponseStartLine("HTTP/1.1", 200, "OK"),
                HTTPHeaders({"Content-Length": "2"}),
                b"OK")
            self.connection.finish()

    router = CustomRouter()
    server = HTTPServer(router)

The main responsibility of `Router` implementation is to provide a
mapping from a request to `~.httputil.HTTPMessageDelegate` instance
that will handle this request. In the example above we can see that
routing is possible even without instantiating an `~.web.Application`.

For routing to `~.web.RequestHandler` implementations we need an
`~.web.Application` instance. `~.web.Application.get_handler_delegate`
provides a convenient way to create `~.httputil.HTTPMessageDelegate`
for a given request and `~.web.RequestHandler`.

Here is a simple example of how we can we route to
`~.web.RequestHandler` subclasses by HTTP method:

.. code-block:: python

    resources = {}

    class GetResource(RequestHandler):
        def get(self, path):
            if path not in resources:
                raise HTTPError(404)

            self.finish(resources[path])

    class PostResource(RequestHandler):
        def post(self, path):
            resources[path] = self.request.body

    class HTTPMethodRouter(Router):
        def __init__(self, app):
            self.app = app

        def find_handler(self, request, **kwargs):
            handler = GetResource if request.method == "GET" else PostResource
            return self.app.get_handler_delegate(request, handler, path_args=[request.path])

    router = HTTPMethodRouter(Application())
    server = HTTPServer(router)

`ReversibleRouter` interface adds the ability to distinguish between
the routes and reverse them to the original urls using route's name
and additional arguments. `~.web.Application` is itself an
implementation of `ReversibleRouter` class.

`RuleRouter` and `ReversibleRuleRouter` are implementations of
`Router` and `ReversibleRouter` interfaces and can be used for
creating rule-based routing configurations.

Rules are instances of `Rule` class. They contain a `Matcher`, which
provides the logic for determining whether the rule is a match for a
particular request and a target, which can be one of the following.

1) An instance of `~.httputil.HTTPServerConnectionDelegate`:

.. code-block:: python

    router = RuleRouter([
        Rule(PathMatches("/handler"), ConnectionDelegate()),
        # ... more rules
    ])

    class ConnectionDelegate(HTTPServerConnectionDelegate):
        def start_request(self, server_conn, request_conn):
            return MessageDelegate(request_conn)

2) A callable accepting a single argument of `~.httputil.HTTPServerRequest` type:

.. code-block:: python

    router = RuleRouter([
        Rule(PathMatches("/callable"), request_callable)
    ])

    def request_callable(request):
        request.write(b"HTTP/1.1 200 OK\\r\\nContent-Length: 2\\r\\n\\r\\nOK")
        request.finish()

3) Another `Router` instance:

.. code-block:: python

    router = RuleRouter([
        Rule(PathMatches("/router.*"), CustomRouter())
    ])

Of course a nested `RuleRouter` or a `~.web.Application` is allowed:

.. code-block:: python

    router = RuleRouter([
        Rule(HostMatches("example.com"), RuleRouter([
            Rule(PathMatches("/app1/.*"), Application([(r"/app1/handler", Handler)])),
        ]))
    ])

    server = HTTPServer(router)

In the example below `RuleRouter` is used to route between applications:

.. code-block:: python

    app1 = Application([
        (r"/app1/handler", Handler1),
        # other handlers ...
    ])

    app2 = Application([
        (r"/app2/handler", Handler2),
        # other handlers ...
    ])

    router = RuleRouter([
        Rule(PathMatches("/app1.*"), app1),
        Rule(PathMatches("/app2.*"), app2)
    ])

    server = HTTPServer(router)

For more information on application-level routing see docs for `~.web.Application`.

.. versionadded:: 4.5

"""

import re
from functools import partial

from tornado import httputil
from tornado.httpserver import _CallableAdapter
from tornado.escape import url_escape, url_unescape, utf8
from tornado.log import app_log
from tornado.util import basestring_type, import_object, re_unescape, unicode_type

from typing import (
    Any,
    Union,
    Optional,
    Awaitable,
    List,
    Dict,
    Pattern,
    Tuple,
    overload,
    Sequence,
)


class Router(httputil.HTTPServerConnectionDelegate):
    """Abstract router interface."""

    def find_handler(
        self, request: httputil.HTTPServerRequest, **kwargs: Any
    ) -> Optional[httputil.HTTPMessageDelegate]:
        """Must be implemented to return an appropriate instance of `~.httputil.HTTPMessageDelegate`
        that can serve the request.
        Routing implementations may pass additional kwargs to extend the routing logic.

        :arg httputil.HTTPServerRequest request: current HTTP request.
        :arg kwargs: additional keyword arguments passed by routing implementation.
        :returns: an instance of `~.httputil.HTTPMessageDelegate` that will be used to
            process the request.
        """
        raise NotImplementedError()

    def start_request(
        self, server_conn: object, request_conn: httputil.HTTPConnection
    ) -> httputil.HTTPMessageDelegate:
        return _RoutingDelegate(self, server_conn, request_conn)


class ReversibleRouter(Router):
    """Abstract router interface for routers that can handle named routes
    and support reversing them to original urls.
    """

    def reverse_url(self, name: str, *args: Any) -> Optional[str]:
        """Returns url string for a given route name and arguments
        or ``None`` if no match is found.

        :arg str name: route name.
        :arg args: url parameters.
        :returns: parametrized url string for a given route name (or ``None``).
        """
        raise NotImplementedError()


class _RoutingDelegate(httputil.HTTPMessageDelegate):
    def __init__(
        self, router: Router, server_conn: object, request_conn: httputil.HTTPConnection
    ) -> None:
        self.server_conn = server_conn
        self.request_conn = request_conn
        self.delegate = None  # type: Optional[httputil.HTTPMessageDelegate]
        self.router = router  # type: Router

    def headers_received(
        self,
        start_line: Union[httputil.RequestStartLine, httputil.ResponseStartLine],
        headers: httputil.HTTPHeaders,
    ) -> Optional[Awaitable[None]]:
        assert isinstance(start_line, httputil.RequestStartLine)
        request = httputil.HTTPServerRequest(
            connection=self.request_conn,
            server_connection=self.server_conn,
            start_line=start_line,
            headers=headers,
        )

        self.delegate = self.router.find_handler(request)
        if self.delegate is None:
            app_log.debug(
                "Delegate for %s %s request not found",
                start_line.method,
                start_line.path,
            )
            self.delegate = _DefaultMessageDelegate(self.request_conn)

        return self.delegate.headers_received(start_line, headers)

    def data_received(self, chunk: bytes) -> Optional[Awaitable[None]]:
        assert self.delegate is not None
        return self.delegate.data_received(chunk)

    def finish(self) -> None:
        assert self.delegate is not None
        self.delegate.finish()

    def on_connection_close(self) -> None:
        assert self.delegate is not None
        self.delegate.on_connection_close()


class _DefaultMessageDelegate(httputil.HTTPMessageDelegate):
    def __init__(self, connection: httputil.HTTPConnection) -> None:
        self.connection = connection

    def finish(self) -> None:
        self.connection.write_headers(
            httputil.ResponseStartLine("HTTP/1.1", 404, "Not Found"),
            httputil.HTTPHeaders(),
        )
        self.connection.finish()


# _RuleList can either contain pre-constructed Rules or a sequence of
# arguments to be passed to the Rule constructor.
_RuleList = Sequence[
    Union[
        "Rule",
        List[Any],  # Can't do detailed typechecking of lists.
        Tuple[Union[str, "Matcher"], Any],
        Tuple[Union[str, "Matcher"], Any, Dict[str, Any]],
        Tuple[Union[str, "Matcher"], Any, Dict[str, Any], str],
    ]
]


class RuleRouter(Router):
    """Rule-based router implementation."""

    def __init__(self, rules: Optional[_RuleList] = None) -> None:
        """Constructs a router from an ordered list of rules::

            RuleRouter([
                Rule(PathMatches("/handler"), Target),
                # ... more rules
            ])

        You can also omit explicit `Rule` constructor and use tuples of arguments::

            RuleRouter([
                (PathMatches("/handler"), Target),
            ])

        `PathMatches` is a default matcher, so the example above can be simplified::

            RuleRouter([
                ("/handler", Target),
            ])

        In the examples above, ``Target`` can be a nested `Router` instance, an instance of
        `~.httputil.HTTPServerConnectionDelegate` or an old-style callable,
        accepting a request argument.

        :arg rules: a list of `Rule` instances or tuples of `Rule`
            constructor arguments.
        """
        self.rules = []  # type: List[Rule]
        if rules:
            self.add_rules(rules)

    def add_rules(self, rules: _RuleList) -> None:
        """Appends new rules to the router.

        :arg rules: a list of Rule instances (or tuples of arguments, which are
            passed to Rule constructor).
        """
        for rule in rules:
            if isinstance(rule, (tuple, list)):
                assert len(rule) in (2, 3, 4)
                if isinstance(rule[0], basestring_type):
                    rule = Rule(PathMatches(rule[0]), *rule[1:])
                else:
                    rule = Rule(*rule)

            self.rules.append(self.process_rule(rule))

    def process_rule(self, rule: "Rule") -> "Rule":
        """Override this method for additional preprocessing of each rule.

        :arg Rule rule: a rule to be processed.
        :returns: the same or modified Rule instance.
        """
        return rule

    def find_handler(
        self, request: httputil.HTTPServerRequest, **kwargs: Any
    ) -> Optional[httputil.HTTPMessageDelegate]:
        for rule in self.rules:
            target_params = rule.matcher.match(request)
            if target_params is not None:
                if rule.target_kwargs:
                    target_params["target_kwargs"] = rule.target_kwargs

                delegate = self.get_target_delegate(
                    rule.target, request, **target_params
                )

                if delegate is not None:
                    return delegate

        return None

    def get_target_delegate(
        self, target: Any, request: httputil.HTTPServerRequest, **target_params: Any
    ) -> Optional[httputil.HTTPMessageDelegate]:
        """Returns an instance of `~.httputil.HTTPMessageDelegate` for a
        Rule's target. This method is called by `~.find_handler` and can be
        extended to provide additional target types.

        :arg target: a Rule's target.
        :arg httputil.HTTPServerRequest request: current request.
        :arg target_params: additional parameters that can be useful
            for `~.httputil.HTTPMessageDelegate` creation.
        """
        if isinstance(target, Router):
            return target.find_handler(request, **target_params)

        elif isinstance(target, httputil.HTTPServerConnectionDelegate):
            assert request.connection is not None
            return target.start_request(request.server_connection, request.connection)

        elif callable(target):
            assert request.connection is not None
            return _CallableAdapter(
                partial(target, **target_params), request.connection
            )

        return None


class ReversibleRuleRouter(ReversibleRouter, RuleRouter):
    """A rule-based router that implements ``reverse_url`` method.

    Each rule added to this router may have a ``name`` attribute that can be
    used to reconstruct an original uri. The actual reconstruction takes place
    in a rule's matcher (see `Matcher.reverse`).
    """

    def __init__(self, rules: Optional[_RuleList] = None) -> None:
        self.named_rules = {}  # type: Dict[str, Any]
        super().__init__(rules)

    def process_rule(self, rule: "Rule") -> "Rule":
        rule = super().process_rule(rule)

        if rule.name:
            if rule.name in self.named_rules:
                app_log.warning(
                    "Multiple handlers named %s; replacing previous value", rule.name
                )
            self.named_rules[rule.name] = rule

        return rule

    def reverse_url(self, name: str, *args: Any) -> Optional[str]:
        if name in self.named_rules:
            return self.named_rules[name].matcher.reverse(*args)

        for rule in self.rules:
            if isinstance(rule.target, ReversibleRouter):
                reversed_url = rule.target.reverse_url(name, *args)
                if reversed_url is not None:
                    return reversed_url

        return None


class Rule:
    """A routing rule."""

    def __init__(
        self,
        matcher: "Matcher",
        target: Any,
        target_kwargs: Optional[Dict[str, Any]] = None,
        name: Optional[str] = None,
    ) -> None:
        """Constructs a Rule instance.

        :arg Matcher matcher: a `Matcher` instance used for determining
            whether the rule should be considered a match for a specific
            request.
        :arg target: a Rule's target (typically a ``RequestHandler`` or
            `~.httputil.HTTPServerConnectionDelegate` subclass or even a nested `Router`,
            depending on routing implementation).
        :arg dict target_kwargs: a dict of parameters that can be useful
            at the moment of target instantiation (for example, ``status_code``
            for a ``RequestHandler`` subclass). They end up in
            ``target_params['target_kwargs']`` of `RuleRouter.get_target_delegate`
            method.
        :arg str name: the name of the rule that can be used to find it
            in `ReversibleRouter.reverse_url` implementation.
        """
        if isinstance(target, str):
            # import the Module and instantiate the class
            # Must be a fully qualified name (module.ClassName)
            target = import_object(target)

        self.matcher = matcher  # type: Matcher
        self.target = target
        self.target_kwargs = target_kwargs if target_kwargs else {}
        self.name = name

    def reverse(self, *args: Any) -> Optional[str]:
        return self.matcher.reverse(*args)

    def __repr__(self) -> str:
        return "{}({!r}, {}, kwargs={!r}, name={!r})".format(
            self.__class__.__name__,
            self.matcher,
            self.target,
            self.target_kwargs,
            self.name,
        )


class Matcher:
    """Represents a matcher for request features."""

    def match(self, request: httputil.HTTPServerRequest) -> Optional[Dict[str, Any]]:
        """Matches current instance against the request.

        :arg httputil.HTTPServerRequest request: current HTTP request
        :returns: a dict of parameters to be passed to the target handler
            (for example, ``handler_kwargs``, ``path_args``, ``path_kwargs``
            can be passed for proper `~.web.RequestHandler` instantiation).
            An empty dict is a valid (and common) return value to indicate a match
            when the argument-passing features are not used.
            ``None`` must be returned to indicate that there is no match."""
        raise NotImplementedError()

    def reverse(self, *args: Any) -> Optional[str]:
        """Reconstructs full url from matcher instance and additional arguments."""
        return None


class AnyMatches(Matcher):
    """Matches any request."""

    def match(self, request: httputil.HTTPServerRequest) -> Optional[Dict[str, Any]]:
        return {}


class HostMatches(Matcher):
    """Matches requests from hosts specified by ``host_pattern`` regex."""

    def __init__(self, host_pattern: Union[str, Pattern]) -> None:
        if isinstance(host_pattern, basestring_type):
            if not host_pattern.endswith("$"):
                host_pattern += "$"
            self.host_pattern = re.compile(host_pattern)
        else:
            self.host_pattern = host_pattern

    def match(self, request: httputil.HTTPServerRequest) -> Optional[Dict[str, Any]]:
        if self.host_pattern.match(request.host_name):
            return {}

        return None


class DefaultHostMatches(Matcher):
    """Matches requests from host that is equal to application's default_host.
    Always returns no match if ``X-Real-Ip`` header is present.
    """

    def __init__(self, application: Any, host_pattern: Pattern) -> None:
        self.application = application
        self.host_pattern = host_pattern

    def match(self, request: httputil.HTTPServerRequest) -> Optional[Dict[str, Any]]:
        # Look for default host if not behind load balancer (for debugging)
        if "X-Real-Ip" not in request.headers:
            if self.host_pattern.match(self.application.default_host):
                return {}
        return None


class PathMatches(Matcher):
    """Matches requests with paths specified by ``path_pattern`` regex."""

    def __init__(self, path_pattern: Union[str, Pattern]) -> None:
        if isinstance(path_pattern, basestring_type):
            if not path_pattern.endswith("$"):
                path_pattern += "$"
            self.regex = re.compile(path_pattern)
        else:
            self.regex = path_pattern

        assert len(self.regex.groupindex) in (0, self.regex.groups), (
            "groups in url regexes must either be all named or all "
            "positional: %r" % self.regex.pattern
        )

        self._path, self._group_count = self._find_groups()

    def match(self, request: httputil.HTTPServerRequest) -> Optional[Dict[str, Any]]:
        match = self.regex.match(request.path)
        if match is None:
            return None
        if not self.regex.groups:
            return {}

        path_args = []  # type: List[bytes]
        path_kwargs = {}  # type: Dict[str, bytes]

        # Pass matched groups to the handler.  Since
        # match.groups() includes both named and
        # unnamed groups, we want to use either groups
        # or groupdict but not both.
        if self.regex.groupindex:
            path_kwargs = {
                str(k): _unquote_or_none(v) for (k, v) in match.groupdict().items()
            }
        else:
            path_args = [_unquote_or_none(s) for s in match.groups()]

        return dict(path_args=path_args, path_kwargs=path_kwargs)

    def reverse(self, *args: Any) -> Optional[str]:
        if self._path is None:
            raise ValueError("Cannot reverse url regex " + self.regex.pattern)
        assert len(args) == self._group_count, (
            "required number of arguments " "not found"
        )
        if not len(args):
            return self._path
        converted_args = []
        for a in args:
            if not isinstance(a, (unicode_type, bytes)):
                a = str(a)
            converted_args.append(url_escape(utf8(a), plus=False))
        return self._path % tuple(converted_args)

    def _find_groups(self) -> Tuple[Optional[str], Optional[int]]:
        """Returns a tuple (reverse string, group count) for a url.

        For example: Given the url pattern /([0-9]{4})/([a-z-]+)/, this method
        would return ('/%s/%s/', 2).
        """
        pattern = self.regex.pattern
        if pattern.startswith("^"):
            pattern = pattern[1:]
        if pattern.endswith("$"):
            pattern = pattern[:-1]

        if self.regex.groups != pattern.count("("):
            # The pattern is too complicated for our simplistic matching,
            # so we can't support reversing it.
            return None, None

        pieces = []
        for fragment in pattern.split("("):
            if ")" in fragment:
                paren_loc = fragment.index(")")
                if paren_loc >= 0:
                    try:
                        unescaped_fragment = re_unescape(fragment[paren_loc + 1 :])
                    except ValueError:
                        # If we can't unescape part of it, we can't
                        # reverse this url.
                        return (None, None)
                    pieces.append("%s" + unescaped_fragment)
            else:
                try:
                    unescaped_fragment = re_unescape(fragment)
                except ValueError:
                    # If we can't unescape part of it, we can't
                    # reverse this url.
                    return (None, None)
                pieces.append(unescaped_fragment)

        return "".join(pieces), self.regex.groups


class URLSpec(Rule):
    """Specifies mappings between URLs and handlers.

    .. versionchanged: 4.5
       `URLSpec` is now a subclass of a `Rule` with `PathMatches` matcher and is preserved for
       backwards compatibility.
    """

    def __init__(
        self,
        pattern: Union[str, Pattern],
        handler: Any,
        kwargs: Optional[Dict[str, Any]] = None,
        name: Optional[str] = None,
    ) -> None:
        """Parameters:

        * ``pattern``: Regular expression to be matched. Any capturing
          groups in the regex will be passed in to the handler's
          get/post/etc methods as arguments (by keyword if named, by
          position if unnamed. Named and unnamed capturing groups
          may not be mixed in the same rule).

        * ``handler``: `~.web.RequestHandler` subclass to be invoked.

        * ``kwargs`` (optional): A dictionary of additional arguments
          to be passed to the handler's constructor.

        * ``name`` (optional): A name for this handler.  Used by
          `~.web.Application.reverse_url`.

        """
        matcher = PathMatches(pattern)
        super().__init__(matcher, handler, kwargs, name)

        self.regex = matcher.regex
        self.handler_class = self.target
        self.kwargs = kwargs

    def __repr__(self) -> str:
        return "{}({!r}, {}, kwargs={!r}, name={!r})".format(
            self.__class__.__name__,
            self.regex.pattern,
            self.handler_class,
            self.kwargs,
            self.name,
        )


@overload
def _unquote_or_none(s: str) -> bytes:
    pass


@overload  # noqa: F811
def _unquote_or_none(s: None) -> None:
    pass


def _unquote_or_none(s: Optional[str]) -> Optional[bytes]:  # noqa: F811
    """None-safe wrapper around url_unescape to handle unmatched optional
    groups correctly.

    Note that args are passed as bytes so the handler can decide what
    encoding to use.
    """
    if s is None:
        return s
    return url_unescape(s, encoding=None, plus=False)

# === NexusCore/openenv\Lib\site-packages\aiohttp\streams.py ===
import asyncio
import collections
import warnings
from typing import (
    Awaitable,
    Callable,
    Deque,
    Final,
    Generic,
    List,
    Optional,
    Tuple,
    TypeVar,
)

from .base_protocol import BaseProtocol
from .helpers import (
    _EXC_SENTINEL,
    BaseTimerContext,
    TimerNoop,
    set_exception,
    set_result,
)
from .log import internal_logger

__all__ = (
    "EMPTY_PAYLOAD",
    "EofStream",
    "StreamReader",
    "DataQueue",
)

_T = TypeVar("_T")


class EofStream(Exception):
    """eof stream indication."""


class AsyncStreamIterator(Generic[_T]):

    __slots__ = ("read_func",)

    def __init__(self, read_func: Callable[[], Awaitable[_T]]) -> None:
        self.read_func = read_func

    def __aiter__(self) -> "AsyncStreamIterator[_T]":
        return self

    async def __anext__(self) -> _T:
        try:
            rv = await self.read_func()
        except EofStream:
            raise StopAsyncIteration
        if rv == b"":
            raise StopAsyncIteration
        return rv


class ChunkTupleAsyncStreamIterator:

    __slots__ = ("_stream",)

    def __init__(self, stream: "StreamReader") -> None:
        self._stream = stream

    def __aiter__(self) -> "ChunkTupleAsyncStreamIterator":
        return self

    async def __anext__(self) -> Tuple[bytes, bool]:
        rv = await self._stream.readchunk()
        if rv == (b"", False):
            raise StopAsyncIteration
        return rv


class AsyncStreamReaderMixin:

    __slots__ = ()

    def __aiter__(self) -> AsyncStreamIterator[bytes]:
        return AsyncStreamIterator(self.readline)  # type: ignore[attr-defined]

    def iter_chunked(self, n: int) -> AsyncStreamIterator[bytes]:
        """Returns an asynchronous iterator that yields chunks of size n."""
        return AsyncStreamIterator(lambda: self.read(n))  # type: ignore[attr-defined]

    def iter_any(self) -> AsyncStreamIterator[bytes]:
        """Yield all available data as soon as it is received."""
        return AsyncStreamIterator(self.readany)  # type: ignore[attr-defined]

    def iter_chunks(self) -> ChunkTupleAsyncStreamIterator:
        """Yield chunks of data as they are received by the server.

        The yielded objects are tuples
        of (bytes, bool) as returned by the StreamReader.readchunk method.
        """
        return ChunkTupleAsyncStreamIterator(self)  # type: ignore[arg-type]


class StreamReader(AsyncStreamReaderMixin):
    """An enhancement of asyncio.StreamReader.

    Supports asynchronous iteration by line, chunk or as available::

        async for line in reader:
            ...
        async for chunk in reader.iter_chunked(1024):
            ...
        async for slice in reader.iter_any():
            ...

    """

    __slots__ = (
        "_protocol",
        "_low_water",
        "_high_water",
        "_loop",
        "_size",
        "_cursor",
        "_http_chunk_splits",
        "_buffer",
        "_buffer_offset",
        "_eof",
        "_waiter",
        "_eof_waiter",
        "_exception",
        "_timer",
        "_eof_callbacks",
        "_eof_counter",
        "total_bytes",
    )

    def __init__(
        self,
        protocol: BaseProtocol,
        limit: int,
        *,
        timer: Optional[BaseTimerContext] = None,
        loop: Optional[asyncio.AbstractEventLoop] = None,
    ) -> None:
        self._protocol = protocol
        self._low_water = limit
        self._high_water = limit * 2
        if loop is None:
            loop = asyncio.get_event_loop()
        self._loop = loop
        self._size = 0
        self._cursor = 0
        self._http_chunk_splits: Optional[List[int]] = None
        self._buffer: Deque[bytes] = collections.deque()
        self._buffer_offset = 0
        self._eof = False
        self._waiter: Optional[asyncio.Future[None]] = None
        self._eof_waiter: Optional[asyncio.Future[None]] = None
        self._exception: Optional[BaseException] = None
        self._timer = TimerNoop() if timer is None else timer
        self._eof_callbacks: List[Callable[[], None]] = []
        self._eof_counter = 0
        self.total_bytes = 0

    def __repr__(self) -> str:
        info = [self.__class__.__name__]
        if self._size:
            info.append("%d bytes" % self._size)
        if self._eof:
            info.append("eof")
        if self._low_water != 2**16:  # default limit
            info.append("low=%d high=%d" % (self._low_water, self._high_water))
        if self._waiter:
            info.append("w=%r" % self._waiter)
        if self._exception:
            info.append("e=%r" % self._exception)
        return "<%s>" % " ".join(info)

    def get_read_buffer_limits(self) -> Tuple[int, int]:
        return (self._low_water, self._high_water)

    def exception(self) -> Optional[BaseException]:
        return self._exception

    def set_exception(
        self,
        exc: BaseException,
        exc_cause: BaseException = _EXC_SENTINEL,
    ) -> None:
        self._exception = exc
        self._eof_callbacks.clear()

        waiter = self._waiter
        if waiter is not None:
            self._waiter = None
            set_exception(waiter, exc, exc_cause)

        waiter = self._eof_waiter
        if waiter is not None:
            self._eof_waiter = None
            set_exception(waiter, exc, exc_cause)

    def on_eof(self, callback: Callable[[], None]) -> None:
        if self._eof:
            try:
                callback()
            except Exception:
                internal_logger.exception("Exception in eof callback")
        else:
            self._eof_callbacks.append(callback)

    def feed_eof(self) -> None:
        self._eof = True

        waiter = self._waiter
        if waiter is not None:
            self._waiter = None
            set_result(waiter, None)

        waiter = self._eof_waiter
        if waiter is not None:
            self._eof_waiter = None
            set_result(waiter, None)

        if self._protocol._reading_paused:
            self._protocol.resume_reading()

        for cb in self._eof_callbacks:
            try:
                cb()
            except Exception:
                internal_logger.exception("Exception in eof callback")

        self._eof_callbacks.clear()

    def is_eof(self) -> bool:
        """Return True if  'feed_eof' was called."""
        return self._eof

    def at_eof(self) -> bool:
        """Return True if the buffer is empty and 'feed_eof' was called."""
        return self._eof and not self._buffer

    async def wait_eof(self) -> None:
        if self._eof:
            return

        assert self._eof_waiter is None
        self._eof_waiter = self._loop.create_future()
        try:
            await self._eof_waiter
        finally:
            self._eof_waiter = None

    def unread_data(self, data: bytes) -> None:
        """rollback reading some data from stream, inserting it to buffer head."""
        warnings.warn(
            "unread_data() is deprecated "
            "and will be removed in future releases (#3260)",
            DeprecationWarning,
            stacklevel=2,
        )
        if not data:
            return

        if self._buffer_offset:
            self._buffer[0] = self._buffer[0][self._buffer_offset :]
            self._buffer_offset = 0
        self._size += len(data)
        self._cursor -= len(data)
        self._buffer.appendleft(data)
        self._eof_counter = 0

    # TODO: size is ignored, remove the param later
    def feed_data(self, data: bytes, size: int = 0) -> None:
        assert not self._eof, "feed_data after feed_eof"

        if not data:
            return

        data_len = len(data)
        self._size += data_len
        self._buffer.append(data)
        self.total_bytes += data_len

        waiter = self._waiter
        if waiter is not None:
            self._waiter = None
            set_result(waiter, None)

        if self._size > self._high_water and not self._protocol._reading_paused:
            self._protocol.pause_reading()

    def begin_http_chunk_receiving(self) -> None:
        if self._http_chunk_splits is None:
            if self.total_bytes:
                raise RuntimeError(
                    "Called begin_http_chunk_receiving when some data was already fed"
                )
            self._http_chunk_splits = []

    def end_http_chunk_receiving(self) -> None:
        if self._http_chunk_splits is None:
            raise RuntimeError(
                "Called end_chunk_receiving without calling "
                "begin_chunk_receiving first"
            )

        # self._http_chunk_splits contains logical byte offsets from start of
        # the body transfer. Each offset is the offset of the end of a chunk.
        # "Logical" means bytes, accessible for a user.
        # If no chunks containing logical data were received, current position
        # is difinitely zero.
        pos = self._http_chunk_splits[-1] if self._http_chunk_splits else 0

        if self.total_bytes == pos:
            # We should not add empty chunks here. So we check for that.
            # Note, when chunked + gzip is used, we can receive a chunk
            # of compressed data, but that data may not be enough for gzip FSM
            # to yield any uncompressed data. That's why current position may
            # not change after receiving a chunk.
            return

        self._http_chunk_splits.append(self.total_bytes)

        # wake up readchunk when end of http chunk received
        waiter = self._waiter
        if waiter is not None:
            self._waiter = None
            set_result(waiter, None)

    async def _wait(self, func_name: str) -> None:
        if not self._protocol.connected:
            raise RuntimeError("Connection closed.")

        # StreamReader uses a future to link the protocol feed_data() method
        # to a read coroutine. Running two read coroutines at the same time
        # would have an unexpected behaviour. It would not possible to know
        # which coroutine would get the next data.
        if self._waiter is not None:
            raise RuntimeError(
                "%s() called while another coroutine is "
                "already waiting for incoming data" % func_name
            )

        waiter = self._waiter = self._loop.create_future()
        try:
            with self._timer:
                await waiter
        finally:
            self._waiter = None

    async def readline(self) -> bytes:
        return await self.readuntil()

    async def readuntil(self, separator: bytes = b"\n") -> bytes:
        seplen = len(separator)
        if seplen == 0:
            raise ValueError("Separator should be at least one-byte string")

        if self._exception is not None:
            raise self._exception

        chunk = b""
        chunk_size = 0
        not_enough = True

        while not_enough:
            while self._buffer and not_enough:
                offset = self._buffer_offset
                ichar = self._buffer[0].find(separator, offset) + 1
                # Read from current offset to found separator or to the end.
                data = self._read_nowait_chunk(
                    ichar - offset + seplen - 1 if ichar else -1
                )
                chunk += data
                chunk_size += len(data)
                if ichar:
                    not_enough = False

                if chunk_size > self._high_water:
                    raise ValueError("Chunk too big")

            if self._eof:
                break

            if not_enough:
                await self._wait("readuntil")

        return chunk

    async def read(self, n: int = -1) -> bytes:
        if self._exception is not None:
            raise self._exception

        # migration problem; with DataQueue you have to catch
        # EofStream exception, so common way is to run payload.read() inside
        # infinite loop. what can cause real infinite loop with StreamReader
        # lets keep this code one major release.
        if __debug__:
            if self._eof and not self._buffer:
                self._eof_counter = getattr(self, "_eof_counter", 0) + 1
                if self._eof_counter > 5:
                    internal_logger.warning(
                        "Multiple access to StreamReader in eof state, "
                        "might be infinite loop.",
                        stack_info=True,
                    )

        if not n:
            return b""

        if n < 0:
            # This used to just loop creating a new waiter hoping to
            # collect everything in self._buffer, but that would
            # deadlock if the subprocess sends more than self.limit
            # bytes.  So just call self.readany() until EOF.
            blocks = []
            while True:
                block = await self.readany()
                if not block:
                    break
                blocks.append(block)
            return b"".join(blocks)

        # TODO: should be `if` instead of `while`
        # because waiter maybe triggered on chunk end,
        # without feeding any data
        while not self._buffer and not self._eof:
            await self._wait("read")

        return self._read_nowait(n)

    async def readany(self) -> bytes:
        if self._exception is not None:
            raise self._exception

        # TODO: should be `if` instead of `while`
        # because waiter maybe triggered on chunk end,
        # without feeding any data
        while not self._buffer and not self._eof:
            await self._wait("readany")

        return self._read_nowait(-1)

    async def readchunk(self) -> Tuple[bytes, bool]:
        """Returns a tuple of (data, end_of_http_chunk).

        When chunked transfer
        encoding is used, end_of_http_chunk is a boolean indicating if the end
        of the data corresponds to the end of a HTTP chunk , otherwise it is
        always False.
        """
        while True:
            if self._exception is not None:
                raise self._exception

            while self._http_chunk_splits:
                pos = self._http_chunk_splits.pop(0)
                if pos == self._cursor:
                    return (b"", True)
                if pos > self._cursor:
                    return (self._read_nowait(pos - self._cursor), True)
                internal_logger.warning(
                    "Skipping HTTP chunk end due to data "
                    "consumption beyond chunk boundary"
                )

            if self._buffer:
                return (self._read_nowait_chunk(-1), False)
                # return (self._read_nowait(-1), False)

            if self._eof:
                # Special case for signifying EOF.
                # (b'', True) is not a final return value actually.
                return (b"", False)

            await self._wait("readchunk")

    async def readexactly(self, n: int) -> bytes:
        if self._exception is not None:
            raise self._exception

        blocks: List[bytes] = []
        while n > 0:
            block = await self.read(n)
            if not block:
                partial = b"".join(blocks)
                raise asyncio.IncompleteReadError(partial, len(partial) + n)
            blocks.append(block)
            n -= len(block)

        return b"".join(blocks)

    def read_nowait(self, n: int = -1) -> bytes:
        # default was changed to be consistent with .read(-1)
        #
        # I believe the most users don't know about the method and
        # they are not affected.
        if self._exception is not None:
            raise self._exception

        if self._waiter and not self._waiter.done():
            raise RuntimeError(
                "Called while some coroutine is waiting for incoming data."
            )

        return self._read_nowait(n)

    def _read_nowait_chunk(self, n: int) -> bytes:
        first_buffer = self._buffer[0]
        offset = self._buffer_offset
        if n != -1 and len(first_buffer) - offset > n:
            data = first_buffer[offset : offset + n]
            self._buffer_offset += n

        elif offset:
            self._buffer.popleft()
            data = first_buffer[offset:]
            self._buffer_offset = 0

        else:
            data = self._buffer.popleft()

        data_len = len(data)
        self._size -= data_len
        self._cursor += data_len

        chunk_splits = self._http_chunk_splits
        # Prevent memory leak: drop useless chunk splits
        while chunk_splits and chunk_splits[0] < self._cursor:
            chunk_splits.pop(0)

        if self._size < self._low_water and self._protocol._reading_paused:
            self._protocol.resume_reading()
        return data

    def _read_nowait(self, n: int) -> bytes:
        """Read not more than n bytes, or whole buffer if n == -1"""
        self._timer.assert_timeout()

        chunks = []
        while self._buffer:
            chunk = self._read_nowait_chunk(n)
            chunks.append(chunk)
            if n != -1:
                n -= len(chunk)
                if n == 0:
                    break

        return b"".join(chunks) if chunks else b""


class EmptyStreamReader(StreamReader):  # lgtm [py/missing-call-to-init]

    __slots__ = ("_read_eof_chunk",)

    def __init__(self) -> None:
        self._read_eof_chunk = False
        self.total_bytes = 0

    def __repr__(self) -> str:
        return "<%s>" % self.__class__.__name__

    def exception(self) -> Optional[BaseException]:
        return None

    def set_exception(
        self,
        exc: BaseException,
        exc_cause: BaseException = _EXC_SENTINEL,
    ) -> None:
        pass

    def on_eof(self, callback: Callable[[], None]) -> None:
        try:
            callback()
        except Exception:
            internal_logger.exception("Exception in eof callback")

    def feed_eof(self) -> None:
        pass

    def is_eof(self) -> bool:
        return True

    def at_eof(self) -> bool:
        return True

    async def wait_eof(self) -> None:
        return

    def feed_data(self, data: bytes, n: int = 0) -> None:
        pass

    async def readline(self) -> bytes:
        return b""

    async def read(self, n: int = -1) -> bytes:
        return b""

    # TODO add async def readuntil

    async def readany(self) -> bytes:
        return b""

    async def readchunk(self) -> Tuple[bytes, bool]:
        if not self._read_eof_chunk:
            self._read_eof_chunk = True
            return (b"", False)

        return (b"", True)

    async def readexactly(self, n: int) -> bytes:
        raise asyncio.IncompleteReadError(b"", n)

    def read_nowait(self, n: int = -1) -> bytes:
        return b""


EMPTY_PAYLOAD: Final[StreamReader] = EmptyStreamReader()


class DataQueue(Generic[_T]):
    """DataQueue is a general-purpose blocking queue with one reader."""

    def __init__(self, loop: asyncio.AbstractEventLoop) -> None:
        self._loop = loop
        self._eof = False
        self._waiter: Optional[asyncio.Future[None]] = None
        self._exception: Optional[BaseException] = None
        self._buffer: Deque[Tuple[_T, int]] = collections.deque()

    def __len__(self) -> int:
        return len(self._buffer)

    def is_eof(self) -> bool:
        return self._eof

    def at_eof(self) -> bool:
        return self._eof and not self._buffer

    def exception(self) -> Optional[BaseException]:
        return self._exception

    def set_exception(
        self,
        exc: BaseException,
        exc_cause: BaseException = _EXC_SENTINEL,
    ) -> None:
        self._eof = True
        self._exception = exc
        if (waiter := self._waiter) is not None:
            self._waiter = None
            set_exception(waiter, exc, exc_cause)

    def feed_data(self, data: _T, size: int = 0) -> None:
        self._buffer.append((data, size))
        if (waiter := self._waiter) is not None:
            self._waiter = None
            set_result(waiter, None)

    def feed_eof(self) -> None:
        self._eof = True
        if (waiter := self._waiter) is not None:
            self._waiter = None
            set_result(waiter, None)

    async def read(self) -> _T:
        if not self._buffer and not self._eof:
            assert not self._waiter
            self._waiter = self._loop.create_future()
            try:
                await self._waiter
            except (asyncio.CancelledError, asyncio.TimeoutError):
                self._waiter = None
                raise
        if self._buffer:
            data, _ = self._buffer.popleft()
            return data
        if self._exception is not None:
            raise self._exception
        raise EofStream

    def __aiter__(self) -> AsyncStreamIterator[_T]:
        return AsyncStreamIterator(self.read)


class FlowControlDataQueue(DataQueue[_T]):
    """FlowControlDataQueue resumes and pauses an underlying stream.

    It is a destination for parsed data.

    This class is deprecated and will be removed in version 4.0.
    """

    def __init__(
        self, protocol: BaseProtocol, limit: int, *, loop: asyncio.AbstractEventLoop
    ) -> None:
        super().__init__(loop=loop)
        self._size = 0
        self._protocol = protocol
        self._limit = limit * 2

    def feed_data(self, data: _T, size: int = 0) -> None:
        super().feed_data(data, size)
        self._size += size

        if self._size > self._limit and not self._protocol._reading_paused:
            self._protocol.pause_reading()

    async def read(self) -> _T:
        if not self._buffer and not self._eof:
            assert not self._waiter
            self._waiter = self._loop.create_future()
            try:
                await self._waiter
            except (asyncio.CancelledError, asyncio.TimeoutError):
                self._waiter = None
                raise
        if self._buffer:
            data, size = self._buffer.popleft()
            self._size -= size
            if self._size < self._limit and self._protocol._reading_paused:
                self._protocol.resume_reading()
            return data
        if self._exception is not None:
            raise self._exception
        raise EofStream

# === NexusCore/openenv\Lib\site-packages\pydantic\type_adapter.py ===
"""Type adapter specification."""

from __future__ import annotations as _annotations

import sys
from collections.abc import Callable, Iterable
from dataclasses import is_dataclass
from types import FrameType
from typing import (
    Any,
    Generic,
    Literal,
    TypeVar,
    cast,
    final,
    overload,
)

from pydantic_core import CoreSchema, SchemaSerializer, SchemaValidator, Some
from typing_extensions import ParamSpec, is_typeddict

from pydantic.errors import PydanticUserError
from pydantic.main import BaseModel, IncEx

from ._internal import _config, _generate_schema, _mock_val_ser, _namespace_utils, _repr, _typing_extra, _utils
from .config import ConfigDict
from .errors import PydanticUndefinedAnnotation
from .json_schema import (
    DEFAULT_REF_TEMPLATE,
    GenerateJsonSchema,
    JsonSchemaKeyT,
    JsonSchemaMode,
    JsonSchemaValue,
)
from .plugin._schema_validator import PluggableSchemaValidator, create_schema_validator

T = TypeVar('T')
R = TypeVar('R')
P = ParamSpec('P')
TypeAdapterT = TypeVar('TypeAdapterT', bound='TypeAdapter')


def _getattr_no_parents(obj: Any, attribute: str) -> Any:
    """Returns the attribute value without attempting to look up attributes from parent types."""
    if hasattr(obj, '__dict__'):
        try:
            return obj.__dict__[attribute]
        except KeyError:
            pass

    slots = getattr(obj, '__slots__', None)
    if slots is not None and attribute in slots:
        return getattr(obj, attribute)
    else:
        raise AttributeError(attribute)


def _type_has_config(type_: Any) -> bool:
    """Returns whether the type has config."""
    type_ = _typing_extra.annotated_type(type_) or type_
    try:
        return issubclass(type_, BaseModel) or is_dataclass(type_) or is_typeddict(type_)
    except TypeError:
        # type is not a class
        return False


@final
class TypeAdapter(Generic[T]):
    """!!! abstract "Usage Documentation"
        [`TypeAdapter`](../concepts/type_adapter.md)

    Type adapters provide a flexible way to perform validation and serialization based on a Python type.

    A `TypeAdapter` instance exposes some of the functionality from `BaseModel` instance methods
    for types that do not have such methods (such as dataclasses, primitive types, and more).

    **Note:** `TypeAdapter` instances are not types, and cannot be used as type annotations for fields.

    Args:
        type: The type associated with the `TypeAdapter`.
        config: Configuration for the `TypeAdapter`, should be a dictionary conforming to
            [`ConfigDict`][pydantic.config.ConfigDict].

            !!! note
                You cannot provide a configuration when instantiating a `TypeAdapter` if the type you're using
                has its own config that cannot be overridden (ex: `BaseModel`, `TypedDict`, and `dataclass`). A
                [`type-adapter-config-unused`](../errors/usage_errors.md#type-adapter-config-unused) error will
                be raised in this case.
        _parent_depth: Depth at which to search for the [parent frame][frame-objects]. This frame is used when
            resolving forward annotations during schema building, by looking for the globals and locals of this
            frame. Defaults to 2, which will result in the frame where the `TypeAdapter` was instantiated.

            !!! note
                This parameter is named with an underscore to suggest its private nature and discourage use.
                It may be deprecated in a minor version, so we only recommend using it if you're comfortable
                with potential change in behavior/support. It's default value is 2 because internally,
                the `TypeAdapter` class makes another call to fetch the frame.
        module: The module that passes to plugin if provided.

    Attributes:
        core_schema: The core schema for the type.
        validator: The schema validator for the type.
        serializer: The schema serializer for the type.
        pydantic_complete: Whether the core schema for the type is successfully built.

    ??? tip "Compatibility with `mypy`"
        Depending on the type used, `mypy` might raise an error when instantiating a `TypeAdapter`. As a workaround, you can explicitly
        annotate your variable:

        ```py
        from typing import Union

        from pydantic import TypeAdapter

        ta: TypeAdapter[Union[str, int]] = TypeAdapter(Union[str, int])  # type: ignore[arg-type]
        ```

    ??? info "Namespace management nuances and implementation details"

        Here, we collect some notes on namespace management, and subtle differences from `BaseModel`:

        `BaseModel` uses its own `__module__` to find out where it was defined
        and then looks for symbols to resolve forward references in those globals.
        On the other hand, `TypeAdapter` can be initialized with arbitrary objects,
        which may not be types and thus do not have a `__module__` available.
        So instead we look at the globals in our parent stack frame.

        It is expected that the `ns_resolver` passed to this function will have the correct
        namespace for the type we're adapting. See the source code for `TypeAdapter.__init__`
        and `TypeAdapter.rebuild` for various ways to construct this namespace.

        This works for the case where this function is called in a module that
        has the target of forward references in its scope, but
        does not always work for more complex cases.

        For example, take the following:

        ```python {title="a.py"}
        IntList = list[int]
        OuterDict = dict[str, 'IntList']
        ```

        ```python {test="skip" title="b.py"}
        from a import OuterDict

        from pydantic import TypeAdapter

        IntList = int  # replaces the symbol the forward reference is looking for
        v = TypeAdapter(OuterDict)
        v({'x': 1})  # should fail but doesn't
        ```

        If `OuterDict` were a `BaseModel`, this would work because it would resolve
        the forward reference within the `a.py` namespace.
        But `TypeAdapter(OuterDict)` can't determine what module `OuterDict` came from.

        In other words, the assumption that _all_ forward references exist in the
        module we are being called from is not technically always true.
        Although most of the time it is and it works fine for recursive models and such,
        `BaseModel`'s behavior isn't perfect either and _can_ break in similar ways,
        so there is no right or wrong between the two.

        But at the very least this behavior is _subtly_ different from `BaseModel`'s.
    """

    core_schema: CoreSchema
    validator: SchemaValidator | PluggableSchemaValidator
    serializer: SchemaSerializer
    pydantic_complete: bool

    @overload
    def __init__(
        self,
        type: type[T],
        *,
        config: ConfigDict | None = ...,
        _parent_depth: int = ...,
        module: str | None = ...,
    ) -> None: ...

    # This second overload is for unsupported special forms (such as Annotated, Union, etc.)
    # Currently there is no way to type this correctly
    # See https://github.com/python/typing/pull/1618
    @overload
    def __init__(
        self,
        type: Any,
        *,
        config: ConfigDict | None = ...,
        _parent_depth: int = ...,
        module: str | None = ...,
    ) -> None: ...

    def __init__(
        self,
        type: Any,
        *,
        config: ConfigDict | None = None,
        _parent_depth: int = 2,
        module: str | None = None,
    ) -> None:
        if _type_has_config(type) and config is not None:
            raise PydanticUserError(
                'Cannot use `config` when the type is a BaseModel, dataclass or TypedDict.'
                ' These types can have their own config and setting the config via the `config`'
                ' parameter to TypeAdapter will not override it, thus the `config` you passed to'
                ' TypeAdapter becomes meaningless, which is probably not what you want.',
                code='type-adapter-config-unused',
            )

        self._type = type
        self._config = config
        self._parent_depth = _parent_depth
        self.pydantic_complete = False

        parent_frame = self._fetch_parent_frame()
        if parent_frame is not None:
            globalns = parent_frame.f_globals
            # Do not provide a local ns if the type adapter happens to be instantiated at the module level:
            localns = parent_frame.f_locals if parent_frame.f_locals is not globalns else {}
        else:
            globalns = {}
            localns = {}

        self._module_name = module or cast(str, globalns.get('__name__', ''))
        self._init_core_attrs(
            ns_resolver=_namespace_utils.NsResolver(
                namespaces_tuple=_namespace_utils.NamespacesTuple(locals=localns, globals=globalns),
                parent_namespace=localns,
            ),
            force=False,
        )

    def _fetch_parent_frame(self) -> FrameType | None:
        frame = sys._getframe(self._parent_depth)
        if frame.f_globals.get('__name__') == 'typing':
            # Because `TypeAdapter` is generic, explicitly parametrizing the class results
            # in a `typing._GenericAlias` instance, which proxies instantiation calls to the
            # "real" `TypeAdapter` class and thus adding an extra frame to the call. To avoid
            # pulling anything from the `typing` module, use the correct frame (the one before):
            return frame.f_back

        return frame

    def _init_core_attrs(
        self, ns_resolver: _namespace_utils.NsResolver, force: bool, raise_errors: bool = False
    ) -> bool:
        """Initialize the core schema, validator, and serializer for the type.

        Args:
            ns_resolver: The namespace resolver to use when building the core schema for the adapted type.
            force: Whether to force the construction of the core schema, validator, and serializer.
                If `force` is set to `False` and `_defer_build` is `True`, the core schema, validator, and serializer will be set to mocks.
            raise_errors: Whether to raise errors if initializing any of the core attrs fails.

        Returns:
            `True` if the core schema, validator, and serializer were successfully initialized, otherwise `False`.

        Raises:
            PydanticUndefinedAnnotation: If `PydanticUndefinedAnnotation` occurs in`__get_pydantic_core_schema__`
                and `raise_errors=True`.
        """
        if not force and self._defer_build:
            _mock_val_ser.set_type_adapter_mocks(self)
            self.pydantic_complete = False
            return False

        try:
            self.core_schema = _getattr_no_parents(self._type, '__pydantic_core_schema__')
            self.validator = _getattr_no_parents(self._type, '__pydantic_validator__')
            self.serializer = _getattr_no_parents(self._type, '__pydantic_serializer__')

            # TODO: we don't go through the rebuild logic here directly because we don't want
            # to repeat all of the namespace fetching logic that we've already done
            # so we simply skip to the block below that does the actual schema generation
            if (
                isinstance(self.core_schema, _mock_val_ser.MockCoreSchema)
                or isinstance(self.validator, _mock_val_ser.MockValSer)
                or isinstance(self.serializer, _mock_val_ser.MockValSer)
            ):
                raise AttributeError()
        except AttributeError:
            config_wrapper = _config.ConfigWrapper(self._config)

            schema_generator = _generate_schema.GenerateSchema(config_wrapper, ns_resolver=ns_resolver)

            try:
                core_schema = schema_generator.generate_schema(self._type)
            except PydanticUndefinedAnnotation:
                if raise_errors:
                    raise
                _mock_val_ser.set_type_adapter_mocks(self)
                return False

            try:
                self.core_schema = schema_generator.clean_schema(core_schema)
            except _generate_schema.InvalidSchemaError:
                _mock_val_ser.set_type_adapter_mocks(self)
                return False

            core_config = config_wrapper.core_config(None)

            self.validator = create_schema_validator(
                schema=self.core_schema,
                schema_type=self._type,
                schema_type_module=self._module_name,
                schema_type_name=str(self._type),
                schema_kind='TypeAdapter',
                config=core_config,
                plugin_settings=config_wrapper.plugin_settings,
            )
            self.serializer = SchemaSerializer(self.core_schema, core_config)

        self.pydantic_complete = True
        return True

    @property
    def _defer_build(self) -> bool:
        config = self._config if self._config is not None else self._model_config
        if config:
            return config.get('defer_build') is True
        return False

    @property
    def _model_config(self) -> ConfigDict | None:
        type_: Any = _typing_extra.annotated_type(self._type) or self._type  # Eg FastAPI heavily uses Annotated
        if _utils.lenient_issubclass(type_, BaseModel):
            return type_.model_config
        return getattr(type_, '__pydantic_config__', None)

    def __repr__(self) -> str:
        return f'TypeAdapter({_repr.display_as_type(self._type)})'

    def rebuild(
        self,
        *,
        force: bool = False,
        raise_errors: bool = True,
        _parent_namespace_depth: int = 2,
        _types_namespace: _namespace_utils.MappingNamespace | None = None,
    ) -> bool | None:
        """Try to rebuild the pydantic-core schema for the adapter's type.

        This may be necessary when one of the annotations is a ForwardRef which could not be resolved during
        the initial attempt to build the schema, and automatic rebuilding fails.

        Args:
            force: Whether to force the rebuilding of the type adapter's schema, defaults to `False`.
            raise_errors: Whether to raise errors, defaults to `True`.
            _parent_namespace_depth: Depth at which to search for the [parent frame][frame-objects]. This
                frame is used when resolving forward annotations during schema rebuilding, by looking for
                the locals of this frame. Defaults to 2, which will result in the frame where the method
                was called.
            _types_namespace: An explicit types namespace to use, instead of using the local namespace
                from the parent frame. Defaults to `None`.

        Returns:
            Returns `None` if the schema is already "complete" and rebuilding was not required.
            If rebuilding _was_ required, returns `True` if rebuilding was successful, otherwise `False`.
        """
        if not force and self.pydantic_complete:
            return None

        if _types_namespace is not None:
            rebuild_ns = _types_namespace
        elif _parent_namespace_depth > 0:
            rebuild_ns = _typing_extra.parent_frame_namespace(parent_depth=_parent_namespace_depth, force=True) or {}
        else:
            rebuild_ns = {}

        # we have to manually fetch globals here because there's no type on the stack of the NsResolver
        # and so we skip the globalns = get_module_ns_of(typ) call that would normally happen
        globalns = sys._getframe(max(_parent_namespace_depth - 1, 1)).f_globals
        ns_resolver = _namespace_utils.NsResolver(
            namespaces_tuple=_namespace_utils.NamespacesTuple(locals=rebuild_ns, globals=globalns),
            parent_namespace=rebuild_ns,
        )
        return self._init_core_attrs(ns_resolver=ns_resolver, force=True, raise_errors=raise_errors)

    def validate_python(
        self,
        object: Any,
        /,
        *,
        strict: bool | None = None,
        from_attributes: bool | None = None,
        context: dict[str, Any] | None = None,
        experimental_allow_partial: bool | Literal['off', 'on', 'trailing-strings'] = False,
        by_alias: bool | None = None,
        by_name: bool | None = None,
    ) -> T:
        """Validate a Python object against the model.

        Args:
            object: The Python object to validate against the model.
            strict: Whether to strictly check types.
            from_attributes: Whether to extract data from object attributes.
            context: Additional context to pass to the validator.
            experimental_allow_partial: **Experimental** whether to enable
                [partial validation](../concepts/experimental.md#partial-validation), e.g. to process streams.
                * False / 'off': Default behavior, no partial validation.
                * True / 'on': Enable partial validation.
                * 'trailing-strings': Enable partial validation and allow trailing strings in the input.
            by_alias: Whether to use the field's alias when validating against the provided input data.
            by_name: Whether to use the field's name when validating against the provided input data.

        !!! note
            When using `TypeAdapter` with a Pydantic `dataclass`, the use of the `from_attributes`
            argument is not supported.

        Returns:
            The validated object.
        """
        if by_alias is False and by_name is not True:
            raise PydanticUserError(
                'At least one of `by_alias` or `by_name` must be set to True.',
                code='validate-by-alias-and-name-false',
            )

        return self.validator.validate_python(
            object,
            strict=strict,
            from_attributes=from_attributes,
            context=context,
            allow_partial=experimental_allow_partial,
            by_alias=by_alias,
            by_name=by_name,
        )

    def validate_json(
        self,
        data: str | bytes | bytearray,
        /,
        *,
        strict: bool | None = None,
        context: dict[str, Any] | None = None,
        experimental_allow_partial: bool | Literal['off', 'on', 'trailing-strings'] = False,
        by_alias: bool | None = None,
        by_name: bool | None = None,
    ) -> T:
        """!!! abstract "Usage Documentation"
            [JSON Parsing](../concepts/json.md#json-parsing)

        Validate a JSON string or bytes against the model.

        Args:
            data: The JSON data to validate against the model.
            strict: Whether to strictly check types.
            context: Additional context to use during validation.
            experimental_allow_partial: **Experimental** whether to enable
                [partial validation](../concepts/experimental.md#partial-validation), e.g. to process streams.
                * False / 'off': Default behavior, no partial validation.
                * True / 'on': Enable partial validation.
                * 'trailing-strings': Enable partial validation and allow trailing strings in the input.
            by_alias: Whether to use the field's alias when validating against the provided input data.
            by_name: Whether to use the field's name when validating against the provided input data.

        Returns:
            The validated object.
        """
        if by_alias is False and by_name is not True:
            raise PydanticUserError(
                'At least one of `by_alias` or `by_name` must be set to True.',
                code='validate-by-alias-and-name-false',
            )

        return self.validator.validate_json(
            data,
            strict=strict,
            context=context,
            allow_partial=experimental_allow_partial,
            by_alias=by_alias,
            by_name=by_name,
        )

    def validate_strings(
        self,
        obj: Any,
        /,
        *,
        strict: bool | None = None,
        context: dict[str, Any] | None = None,
        experimental_allow_partial: bool | Literal['off', 'on', 'trailing-strings'] = False,
        by_alias: bool | None = None,
        by_name: bool | None = None,
    ) -> T:
        """Validate object contains string data against the model.

        Args:
            obj: The object contains string data to validate.
            strict: Whether to strictly check types.
            context: Additional context to use during validation.
            experimental_allow_partial: **Experimental** whether to enable
                [partial validation](../concepts/experimental.md#partial-validation), e.g. to process streams.
                * False / 'off': Default behavior, no partial validation.
                * True / 'on': Enable partial validation.
                * 'trailing-strings': Enable partial validation and allow trailing strings in the input.
            by_alias: Whether to use the field's alias when validating against the provided input data.
            by_name: Whether to use the field's name when validating against the provided input data.

        Returns:
            The validated object.
        """
        if by_alias is False and by_name is not True:
            raise PydanticUserError(
                'At least one of `by_alias` or `by_name` must be set to True.',
                code='validate-by-alias-and-name-false',
            )

        return self.validator.validate_strings(
            obj,
            strict=strict,
            context=context,
            allow_partial=experimental_allow_partial,
            by_alias=by_alias,
            by_name=by_name,
        )

    def get_default_value(self, *, strict: bool | None = None, context: dict[str, Any] | None = None) -> Some[T] | None:
        """Get the default value for the wrapped type.

        Args:
            strict: Whether to strictly check types.
            context: Additional context to pass to the validator.

        Returns:
            The default value wrapped in a `Some` if there is one or None if not.
        """
        return self.validator.get_default_value(strict=strict, context=context)

    def dump_python(
        self,
        instance: T,
        /,
        *,
        mode: Literal['json', 'python'] = 'python',
        include: IncEx | None = None,
        exclude: IncEx | None = None,
        by_alias: bool | None = None,
        exclude_unset: bool = False,
        exclude_defaults: bool = False,
        exclude_none: bool = False,
        round_trip: bool = False,
        warnings: bool | Literal['none', 'warn', 'error'] = True,
        fallback: Callable[[Any], Any] | None = None,
        serialize_as_any: bool = False,
        context: dict[str, Any] | None = None,
    ) -> Any:
        """Dump an instance of the adapted type to a Python object.

        Args:
            instance: The Python object to serialize.
            mode: The output format.
            include: Fields to include in the output.
            exclude: Fields to exclude from the output.
            by_alias: Whether to use alias names for field names.
            exclude_unset: Whether to exclude unset fields.
            exclude_defaults: Whether to exclude fields with default values.
            exclude_none: Whether to exclude fields with None values.
            round_trip: Whether to output the serialized data in a way that is compatible with deserialization.
            warnings: How to handle serialization errors. False/"none" ignores them, True/"warn" logs errors,
                "error" raises a [`PydanticSerializationError`][pydantic_core.PydanticSerializationError].
            fallback: A function to call when an unknown value is encountered. If not provided,
                a [`PydanticSerializationError`][pydantic_core.PydanticSerializationError] error is raised.
            serialize_as_any: Whether to serialize fields with duck-typing serialization behavior.
            context: Additional context to pass to the serializer.

        Returns:
            The serialized object.
        """
        return self.serializer.to_python(
            instance,
            mode=mode,
            by_alias=by_alias,
            include=include,
            exclude=exclude,
            exclude_unset=exclude_unset,
            exclude_defaults=exclude_defaults,
            exclude_none=exclude_none,
            round_trip=round_trip,
            warnings=warnings,
            fallback=fallback,
            serialize_as_any=serialize_as_any,
            context=context,
        )

    def dump_json(
        self,
        instance: T,
        /,
        *,
        indent: int | None = None,
        include: IncEx | None = None,
        exclude: IncEx | None = None,
        by_alias: bool | None = None,
        exclude_unset: bool = False,
        exclude_defaults: bool = False,
        exclude_none: bool = False,
        round_trip: bool = False,
        warnings: bool | Literal['none', 'warn', 'error'] = True,
        fallback: Callable[[Any], Any] | None = None,
        serialize_as_any: bool = False,
        context: dict[str, Any] | None = None,
    ) -> bytes:
        """!!! abstract "Usage Documentation"
            [JSON Serialization](../concepts/json.md#json-serialization)

        Serialize an instance of the adapted type to JSON.

        Args:
            instance: The instance to be serialized.
            indent: Number of spaces for JSON indentation.
            include: Fields to include.
            exclude: Fields to exclude.
            by_alias: Whether to use alias names for field names.
            exclude_unset: Whether to exclude unset fields.
            exclude_defaults: Whether to exclude fields with default values.
            exclude_none: Whether to exclude fields with a value of `None`.
            round_trip: Whether to serialize and deserialize the instance to ensure round-tripping.
            warnings: How to handle serialization errors. False/"none" ignores them, True/"warn" logs errors,
                "error" raises a [`PydanticSerializationError`][pydantic_core.PydanticSerializationError].
            fallback: A function to call when an unknown value is encountered. If not provided,
                a [`PydanticSerializationError`][pydantic_core.PydanticSerializationError] error is raised.
            serialize_as_any: Whether to serialize fields with duck-typing serialization behavior.
            context: Additional context to pass to the serializer.

        Returns:
            The JSON representation of the given instance as bytes.
        """
        return self.serializer.to_json(
            instance,
            indent=indent,
            include=include,
            exclude=exclude,
            by_alias=by_alias,
            exclude_unset=exclude_unset,
            exclude_defaults=exclude_defaults,
            exclude_none=exclude_none,
            round_trip=round_trip,
            warnings=warnings,
            fallback=fallback,
            serialize_as_any=serialize_as_any,
            context=context,
        )

    def json_schema(
        self,
        *,
        by_alias: bool = True,
        ref_template: str = DEFAULT_REF_TEMPLATE,
        schema_generator: type[GenerateJsonSchema] = GenerateJsonSchema,
        mode: JsonSchemaMode = 'validation',
    ) -> dict[str, Any]:
        """Generate a JSON schema for the adapted type.

        Args:
            by_alias: Whether to use alias names for field names.
            ref_template: The format string used for generating $ref strings.
            schema_generator: The generator class used for creating the schema.
            mode: The mode to use for schema generation.

        Returns:
            The JSON schema for the model as a dictionary.
        """
        schema_generator_instance = schema_generator(by_alias=by_alias, ref_template=ref_template)
        if isinstance(self.core_schema, _mock_val_ser.MockCoreSchema):
            self.core_schema.rebuild()
            assert not isinstance(self.core_schema, _mock_val_ser.MockCoreSchema), 'this is a bug! please report it'
        return schema_generator_instance.generate(self.core_schema, mode=mode)

    @staticmethod
    def json_schemas(
        inputs: Iterable[tuple[JsonSchemaKeyT, JsonSchemaMode, TypeAdapter[Any]]],
        /,
        *,
        by_alias: bool = True,
        title: str | None = None,
        description: str | None = None,
        ref_template: str = DEFAULT_REF_TEMPLATE,
        schema_generator: type[GenerateJsonSchema] = GenerateJsonSchema,
    ) -> tuple[dict[tuple[JsonSchemaKeyT, JsonSchemaMode], JsonSchemaValue], JsonSchemaValue]:
        """Generate a JSON schema including definitions from multiple type adapters.

        Args:
            inputs: Inputs to schema generation. The first two items will form the keys of the (first)
                output mapping; the type adapters will provide the core schemas that get converted into
                definitions in the output JSON schema.
            by_alias: Whether to use alias names.
            title: The title for the schema.
            description: The description for the schema.
            ref_template: The format string used for generating $ref strings.
            schema_generator: The generator class used for creating the schema.

        Returns:
            A tuple where:

                - The first element is a dictionary whose keys are tuples of JSON schema key type and JSON mode, and
                    whose values are the JSON schema corresponding to that pair of inputs. (These schemas may have
                    JsonRef references to definitions that are defined in the second returned element.)
                - The second element is a JSON schema containing all definitions referenced in the first returned
                    element, along with the optional title and description keys.

        """
        schema_generator_instance = schema_generator(by_alias=by_alias, ref_template=ref_template)

        inputs_ = []
        for key, mode, adapter in inputs:
            # This is the same pattern we follow for model json schemas - we attempt a core schema rebuild if we detect a mock
            if isinstance(adapter.core_schema, _mock_val_ser.MockCoreSchema):
                adapter.core_schema.rebuild()
                assert not isinstance(adapter.core_schema, _mock_val_ser.MockCoreSchema), (
                    'this is a bug! please report it'
                )
            inputs_.append((key, mode, adapter.core_schema))

        json_schemas_map, definitions = schema_generator_instance.generate_definitions(inputs_)

        json_schema: dict[str, Any] = {}
        if definitions:
            json_schema['$defs'] = definitions
        if title:
            json_schema['title'] = title
        if description:
            json_schema['description'] = description

        return json_schemas_map, json_schema

# === NexusCore/openenv\Lib\site-packages\jupyter_client\connect.py ===
"""Utilities for connecting to jupyter kernels

The :class:`ConnectionFileMixin` class in this module encapsulates the logic
related to writing and reading connections files.
"""
# Copyright (c) Jupyter Development Team.
# Distributed under the terms of the Modified BSD License.
from __future__ import annotations

import errno
import glob
import json
import os
import socket
import stat
import tempfile
import warnings
from getpass import getpass
from typing import TYPE_CHECKING, Any, Dict, Union, cast

import zmq
from jupyter_core.paths import jupyter_data_dir, jupyter_runtime_dir, secure_write
from traitlets import Bool, CaselessStrEnum, Instance, Integer, Type, Unicode, observe
from traitlets.config import LoggingConfigurable, SingletonConfigurable

from .localinterfaces import localhost
from .utils import _filefind

if TYPE_CHECKING:
    from jupyter_client import BlockingKernelClient

    from .session import Session

# Define custom type for kernel connection info
KernelConnectionInfo = Dict[str, Union[int, str, bytes]]


def write_connection_file(
    fname: str | None = None,
    shell_port: int = 0,
    iopub_port: int = 0,
    stdin_port: int = 0,
    hb_port: int = 0,
    control_port: int = 0,
    ip: str = "",
    key: bytes = b"",
    transport: str = "tcp",
    signature_scheme: str = "hmac-sha256",
    kernel_name: str = "",
    **kwargs: Any,
) -> tuple[str, KernelConnectionInfo]:
    """Generates a JSON config file, including the selection of random ports.

    Parameters
    ----------

    fname : unicode
        The path to the file to write

    shell_port : int, optional
        The port to use for ROUTER (shell) channel.

    iopub_port : int, optional
        The port to use for the SUB channel.

    stdin_port : int, optional
        The port to use for the ROUTER (raw input) channel.

    control_port : int, optional
        The port to use for the ROUTER (control) channel.

    hb_port : int, optional
        The port to use for the heartbeat REP channel.

    ip  : str, optional
        The ip address the kernel will bind to.

    key : str, optional
        The Session key used for message authentication.

    signature_scheme : str, optional
        The scheme used for message authentication.
        This has the form 'digest-hash', where 'digest'
        is the scheme used for digests, and 'hash' is the name of the hash function
        used by the digest scheme.
        Currently, 'hmac' is the only supported digest scheme,
        and 'sha256' is the default hash function.

    kernel_name : str, optional
        The name of the kernel currently connected to.
    """
    if not ip:
        ip = localhost()
    # default to temporary connector file
    if not fname:
        fd, fname = tempfile.mkstemp(".json")
        os.close(fd)

    # Find open ports as necessary.

    ports: list[int] = []
    sockets: list[socket.socket] = []
    ports_needed = (
        int(shell_port <= 0)
        + int(iopub_port <= 0)
        + int(stdin_port <= 0)
        + int(control_port <= 0)
        + int(hb_port <= 0)
    )
    if transport == "tcp":
        for _ in range(ports_needed):
            sock = socket.socket()
            # struct.pack('ii', (0,0)) is 8 null bytes
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_LINGER, b"\0" * 8)
            sock.bind((ip, 0))
            sockets.append(sock)
        for sock in sockets:
            port = sock.getsockname()[1]
            sock.close()
            ports.append(port)
    else:
        N = 1
        for _ in range(ports_needed):
            while os.path.exists(f"{ip}-{N!s}"):
                N += 1
            ports.append(N)
            N += 1
    if shell_port <= 0:
        shell_port = ports.pop(0)
    if iopub_port <= 0:
        iopub_port = ports.pop(0)
    if stdin_port <= 0:
        stdin_port = ports.pop(0)
    if control_port <= 0:
        control_port = ports.pop(0)
    if hb_port <= 0:
        hb_port = ports.pop(0)

    cfg: KernelConnectionInfo = {
        "shell_port": shell_port,
        "iopub_port": iopub_port,
        "stdin_port": stdin_port,
        "control_port": control_port,
        "hb_port": hb_port,
    }
    cfg["ip"] = ip
    cfg["key"] = key.decode()
    cfg["transport"] = transport
    cfg["signature_scheme"] = signature_scheme
    cfg["kernel_name"] = kernel_name
    cfg.update(kwargs)

    # Only ever write this file as user read/writeable
    # This would otherwise introduce a vulnerability as a file has secrets
    # which would let others execute arbitrary code as you
    with secure_write(fname) as f:
        f.write(json.dumps(cfg, indent=2))

    if hasattr(stat, "S_ISVTX"):
        # set the sticky bit on the parent directory of the file
        # to ensure only owner can remove it
        runtime_dir = os.path.dirname(fname)
        if runtime_dir:
            permissions = os.stat(runtime_dir).st_mode
            new_permissions = permissions | stat.S_ISVTX
            if new_permissions != permissions:
                try:
                    os.chmod(runtime_dir, new_permissions)
                except OSError as e:
                    if e.errno == errno.EPERM:
                        # suppress permission errors setting sticky bit on runtime_dir,
                        # which we may not own.
                        pass
    return fname, cfg


def find_connection_file(
    filename: str = "kernel-*.json",
    path: str | list[str] | None = None,
    profile: str | None = None,
) -> str:
    """find a connection file, and return its absolute path.

    The current working directory and optional search path
    will be searched for the file if it is not given by absolute path.

    If the argument does not match an existing file, it will be interpreted as a
    fileglob, and the matching file in the profile's security dir with
    the latest access time will be used.

    Parameters
    ----------
    filename : str
        The connection file or fileglob to search for.
    path : str or list of strs[optional]
        Paths in which to search for connection files.

    Returns
    -------
    str : The absolute path of the connection file.
    """
    if profile is not None:
        warnings.warn(
            "Jupyter has no profiles. profile=%s has been ignored." % profile, stacklevel=2
        )
    if path is None:
        path = [".", jupyter_runtime_dir()]
    if isinstance(path, str):
        path = [path]

    try:
        # first, try explicit name
        return _filefind(filename, path)
    except OSError:
        pass

    # not found by full name

    if "*" in filename:
        # given as a glob already
        pat = filename
    else:
        # accept any substring match
        pat = "*%s*" % filename

    matches = []
    for p in path:
        matches.extend(glob.glob(os.path.join(p, pat)))

    matches = [os.path.abspath(m) for m in matches]
    if not matches:
        msg = f"Could not find {filename!r} in {path!r}"
        raise OSError(msg)
    elif len(matches) == 1:
        return matches[0]
    else:
        # get most recent match, by access time:
        return sorted(matches, key=lambda f: os.stat(f).st_atime)[-1]


def tunnel_to_kernel(
    connection_info: str | KernelConnectionInfo,
    sshserver: str,
    sshkey: str | None = None,
) -> tuple[Any, ...]:
    """tunnel connections to a kernel via ssh

    This will open five SSH tunnels from localhost on this machine to the
    ports associated with the kernel.  They can be either direct
    localhost-localhost tunnels, or if an intermediate server is necessary,
    the kernel must be listening on a public IP.

    Parameters
    ----------
    connection_info : dict or str (path)
        Either a connection dict, or the path to a JSON connection file
    sshserver : str
        The ssh sever to use to tunnel to the kernel. Can be a full
        `user@server:port` string. ssh config aliases are respected.
    sshkey : str [optional]
        Path to file containing ssh key to use for authentication.
        Only necessary if your ssh config does not already associate
        a keyfile with the host.

    Returns
    -------

    (shell, iopub, stdin, hb, control) : ints
        The five ports on localhost that have been forwarded to the kernel.
    """
    from .ssh import tunnel

    if isinstance(connection_info, str):
        # it's a path, unpack it
        with open(connection_info) as f:
            connection_info = json.loads(f.read())

    cf = cast(Dict[str, Any], connection_info)

    lports = tunnel.select_random_ports(5)
    rports = (
        cf["shell_port"],
        cf["iopub_port"],
        cf["stdin_port"],
        cf["hb_port"],
        cf["control_port"],
    )

    remote_ip = cf["ip"]

    if tunnel.try_passwordless_ssh(sshserver, sshkey):
        password: bool | str = False
    else:
        password = getpass("SSH Password for %s: " % sshserver)

    for lp, rp in zip(lports, rports):
        tunnel.ssh_tunnel(lp, rp, sshserver, remote_ip, sshkey, password)

    return tuple(lports)


# -----------------------------------------------------------------------------
# Mixin for classes that work with connection files
# -----------------------------------------------------------------------------

channel_socket_types = {
    "hb": zmq.REQ,
    "shell": zmq.DEALER,
    "iopub": zmq.SUB,
    "stdin": zmq.DEALER,
    "control": zmq.DEALER,
}

port_names = ["%s_port" % channel for channel in ("shell", "stdin", "iopub", "hb", "control")]


class ConnectionFileMixin(LoggingConfigurable):
    """Mixin for configurable classes that work with connection files"""

    data_dir: str | Unicode = Unicode()

    def _data_dir_default(self) -> str:
        return jupyter_data_dir()

    # The addresses for the communication channels
    connection_file = Unicode(
        "",
        config=True,
        help="""JSON file in which to store connection info [default: kernel-<pid>.json]

    This file will contain the IP, ports, and authentication key needed to connect
    clients to this kernel. By default, this file will be created in the security dir
    of the current profile, but can be specified by absolute path.
    """,
    )
    _connection_file_written = Bool(False)

    transport = CaselessStrEnum(["tcp", "ipc"], default_value="tcp", config=True)
    kernel_name: str | Unicode = Unicode()

    context = Instance(zmq.Context)

    ip = Unicode(
        config=True,
        help="""Set the kernel\'s IP address [default localhost].
        If the IP address is something other than localhost, then
        Consoles on other machines will be able to connect
        to the Kernel, so be careful!""",
    )

    def _ip_default(self) -> str:
        if self.transport == "ipc":
            if self.connection_file:
                return os.path.splitext(self.connection_file)[0] + "-ipc"
            else:
                return "kernel-ipc"
        else:
            return localhost()

    @observe("ip")
    def _ip_changed(self, change: Any) -> None:
        if change["new"] == "*":
            self.ip = "0.0.0.0"  # noqa

    # protected traits

    hb_port = Integer(0, config=True, help="set the heartbeat port [default: random]")
    shell_port = Integer(0, config=True, help="set the shell (ROUTER) port [default: random]")
    iopub_port = Integer(0, config=True, help="set the iopub (PUB) port [default: random]")
    stdin_port = Integer(0, config=True, help="set the stdin (ROUTER) port [default: random]")
    control_port = Integer(0, config=True, help="set the control (ROUTER) port [default: random]")

    # names of the ports with random assignment
    _random_port_names: list[str] | None = None

    @property
    def ports(self) -> list[int]:
        return [getattr(self, name) for name in port_names]

    # The Session to use for communication with the kernel.
    session = Instance("jupyter_client.session.Session")

    def _session_default(self) -> Session:
        from .session import Session

        return Session(parent=self)

    # --------------------------------------------------------------------------
    # Connection and ipc file management
    # --------------------------------------------------------------------------

    def get_connection_info(self, session: bool = False) -> KernelConnectionInfo:
        """Return the connection info as a dict

        Parameters
        ----------
        session : bool [default: False]
            If True, return our session object will be included in the connection info.
            If False (default), the configuration parameters of our session object will be included,
            rather than the session object itself.

        Returns
        -------
        connect_info : dict
            dictionary of connection information.
        """
        info = {
            "transport": self.transport,
            "ip": self.ip,
            "shell_port": self.shell_port,
            "iopub_port": self.iopub_port,
            "stdin_port": self.stdin_port,
            "hb_port": self.hb_port,
            "control_port": self.control_port,
        }
        if session:
            # add *clone* of my session,
            # so that state such as digest_history is not shared.
            info["session"] = self.session.clone()
        else:
            # add session info
            info.update(
                {
                    "signature_scheme": self.session.signature_scheme,
                    "key": self.session.key,
                }
            )
        return info

    # factory for blocking clients
    blocking_class = Type(klass=object, default_value="jupyter_client.BlockingKernelClient")

    def blocking_client(self) -> BlockingKernelClient:
        """Make a blocking client connected to my kernel"""
        info = self.get_connection_info()
        bc = self.blocking_class(parent=self)  # type:ignore[operator]
        bc.load_connection_info(info)
        return bc

    def cleanup_connection_file(self) -> None:
        """Cleanup connection file *if we wrote it*

        Will not raise if the connection file was already removed somehow.
        """
        if self._connection_file_written:
            # cleanup connection files on full shutdown of kernel we started
            self._connection_file_written = False
            try:
                os.remove(self.connection_file)
            except (OSError, AttributeError):
                pass

    def cleanup_ipc_files(self) -> None:
        """Cleanup ipc files if we wrote them."""
        if self.transport != "ipc":
            return
        for port in self.ports:
            ipcfile = "%s-%i" % (self.ip, port)
            try:
                os.remove(ipcfile)
            except OSError:
                pass

    def _record_random_port_names(self) -> None:
        """Records which of the ports are randomly assigned.

        Records on first invocation, if the transport is tcp.
        Does nothing on later invocations."""

        if self.transport != "tcp":
            return
        if self._random_port_names is not None:
            return

        self._random_port_names = []
        for name in port_names:
            if getattr(self, name) <= 0:
                self._random_port_names.append(name)

    def cleanup_random_ports(self) -> None:
        """Forgets randomly assigned port numbers and cleans up the connection file.

        Does nothing if no port numbers have been randomly assigned.
        In particular, does nothing unless the transport is tcp.
        """

        if not self._random_port_names:
            return

        for name in self._random_port_names:
            setattr(self, name, 0)

        self.cleanup_connection_file()

    def write_connection_file(self, **kwargs: Any) -> None:
        """Write connection info to JSON dict in self.connection_file."""
        if self._connection_file_written and os.path.exists(self.connection_file):
            return

        self.connection_file, cfg = write_connection_file(
            self.connection_file,
            transport=self.transport,
            ip=self.ip,
            key=self.session.key,
            stdin_port=self.stdin_port,
            iopub_port=self.iopub_port,
            shell_port=self.shell_port,
            hb_port=self.hb_port,
            control_port=self.control_port,
            signature_scheme=self.session.signature_scheme,
            kernel_name=self.kernel_name,
            **kwargs,
        )
        # write_connection_file also sets default ports:
        self._record_random_port_names()
        for name in port_names:
            setattr(self, name, cfg[name])

        self._connection_file_written = True

    def load_connection_file(self, connection_file: str | None = None) -> None:
        """Load connection info from JSON dict in self.connection_file.

        Parameters
        ----------
        connection_file: unicode, optional
            Path to connection file to load.
            If unspecified, use self.connection_file
        """
        if connection_file is None:
            connection_file = self.connection_file
        self.log.debug("Loading connection file %s", connection_file)
        with open(connection_file) as f:
            info = json.load(f)
        self.load_connection_info(info)

    def load_connection_info(self, info: KernelConnectionInfo) -> None:
        """Load connection info from a dict containing connection info.

        Typically this data comes from a connection file
        and is called by load_connection_file.

        Parameters
        ----------
        info: dict
            Dictionary containing connection_info.
            See the connection_file spec for details.
        """
        self.transport = info.get("transport", self.transport)
        self.ip = info.get("ip", self._ip_default())  # type:ignore[assignment]

        self._record_random_port_names()
        for name in port_names:
            if getattr(self, name) == 0 and name in info:
                # not overridden by config or cl_args
                setattr(self, name, info[name])

        if "key" in info:
            key = info["key"]
            if isinstance(key, str):
                key = key.encode()
            assert isinstance(key, bytes)

            self.session.key = key
        if "signature_scheme" in info:
            self.session.signature_scheme = info["signature_scheme"]

    def _reconcile_connection_info(self, info: KernelConnectionInfo) -> None:
        """Reconciles the connection information returned from the Provisioner.

        Because some provisioners (like derivations of LocalProvisioner) may have already
        written the connection file, this method needs to ensure that, if the connection
        file exists, its contents match that of what was returned by the provisioner.  If
        the file does exist and its contents do not match, the file will be replaced with
        the provisioner information (which is considered the truth).

        If the file does not exist, the connection information in 'info' is loaded into the
        KernelManager and written to the file.
        """
        # Prevent over-writing a file that has already been written with the same
        # info.  This is to prevent a race condition where the process has
        # already been launched but has not yet read the connection file - as is
        # the case with LocalProvisioners.
        file_exists: bool = False
        if os.path.exists(self.connection_file):
            with open(self.connection_file) as f:
                file_info = json.load(f)
            # Prior to the following comparison, we need to adjust the value of "key" to
            # be bytes, otherwise the comparison below will fail.
            file_info["key"] = file_info["key"].encode()
            if not self._equal_connections(info, file_info):
                os.remove(self.connection_file)  # Contents mismatch - remove the file
                self._connection_file_written = False
            else:
                file_exists = True

        if not file_exists:
            # Load the connection info and write out file, clearing existing
            # port-based attributes so they will be reloaded
            for name in port_names:
                setattr(self, name, 0)
            self.load_connection_info(info)
            self.write_connection_file()

        # Ensure what is in KernelManager is what we expect.
        km_info = self.get_connection_info()
        if not self._equal_connections(info, km_info):
            msg = (
                "KernelManager's connection information already exists and does not match "
                "the expected values returned from provisioner!"
            )
            raise ValueError(msg)

    @staticmethod
    def _equal_connections(conn1: KernelConnectionInfo, conn2: KernelConnectionInfo) -> bool:
        """Compares pertinent keys of connection info data. Returns True if equivalent, False otherwise."""

        pertinent_keys = [
            "key",
            "ip",
            "stdin_port",
            "iopub_port",
            "shell_port",
            "control_port",
            "hb_port",
            "transport",
            "signature_scheme",
        ]

        return all(conn1.get(key) == conn2.get(key) for key in pertinent_keys)

    # --------------------------------------------------------------------------
    # Creating connected sockets
    # --------------------------------------------------------------------------

    def _make_url(self, channel: str) -> str:
        """Make a ZeroMQ URL for a given channel."""
        transport = self.transport
        ip = self.ip
        port = getattr(self, "%s_port" % channel)

        if transport == "tcp":
            return "tcp://%s:%i" % (ip, port)
        else:
            return f"{transport}://{ip}-{port}"

    def _create_connected_socket(
        self, channel: str, identity: bytes | None = None
    ) -> zmq.sugar.socket.Socket:
        """Create a zmq Socket and connect it to the kernel."""
        url = self._make_url(channel)
        socket_type = channel_socket_types[channel]
        self.log.debug("Connecting to: %s", url)
        sock = self.context.socket(socket_type)
        # set linger to 1s to prevent hangs at exit
        sock.linger = 1000
        if identity:
            sock.identity = identity
        sock.connect(url)
        return sock

    def connect_iopub(self, identity: bytes | None = None) -> zmq.sugar.socket.Socket:
        """return zmq Socket connected to the IOPub channel"""
        sock = self._create_connected_socket("iopub", identity=identity)
        sock.setsockopt(zmq.SUBSCRIBE, b"")
        return sock

    def connect_shell(self, identity: bytes | None = None) -> zmq.sugar.socket.Socket:
        """return zmq Socket connected to the Shell channel"""
        return self._create_connected_socket("shell", identity=identity)

    def connect_stdin(self, identity: bytes | None = None) -> zmq.sugar.socket.Socket:
        """return zmq Socket connected to the StdIn channel"""
        return self._create_connected_socket("stdin", identity=identity)

    def connect_hb(self, identity: bytes | None = None) -> zmq.sugar.socket.Socket:
        """return zmq Socket connected to the Heartbeat channel"""
        return self._create_connected_socket("hb", identity=identity)

    def connect_control(self, identity: bytes | None = None) -> zmq.sugar.socket.Socket:
        """return zmq Socket connected to the Control channel"""
        return self._create_connected_socket("control", identity=identity)


class LocalPortCache(SingletonConfigurable):
    """
    Used to keep track of local ports in order to prevent race conditions that
    can occur between port acquisition and usage by the kernel.  All locally-
    provisioned kernels should use this mechanism to limit the possibility of
    race conditions.  Note that this does not preclude other applications from
    acquiring a cached but unused port, thereby re-introducing the issue this
    class is attempting to resolve (minimize).
    See: https://github.com/jupyter/jupyter_client/issues/487
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.currently_used_ports: set[int] = set()

    def find_available_port(self, ip: str) -> int:
        while True:
            tmp_sock = socket.socket()
            tmp_sock.setsockopt(socket.SOL_SOCKET, socket.SO_LINGER, b"\0" * 8)
            tmp_sock.bind((ip, 0))
            port = tmp_sock.getsockname()[1]
            tmp_sock.close()

            # This is a workaround for https://github.com/jupyter/jupyter_client/issues/487
            # We prevent two kernels to have the same ports.
            if port not in self.currently_used_ports:
                self.currently_used_ports.add(port)
                return port

    def return_port(self, port: int) -> None:
        if port in self.currently_used_ports:  # Tolerate uncached ports
            self.currently_used_ports.remove(port)


__all__ = [
    "write_connection_file",
    "find_connection_file",
    "tunnel_to_kernel",
    "KernelConnectionInfo",
    "LocalPortCache",
]

# === NexusCore/openenv\Lib\site-packages\litellm\litellm_core_utils\llm_response_utils\convert_dict_to_response.py ===
import asyncio
import json
import re
import time
import traceback
import uuid
from typing import Dict, Iterable, List, Literal, Optional, Tuple, Union

import litellm
from litellm._logging import verbose_logger
from litellm.constants import RESPONSE_FORMAT_TOOL_NAME
from litellm.types.llms.databricks import DatabricksTool
from litellm.types.llms.openai import (
    ChatCompletionThinkingBlock,
    OpenAIModerationResponse,
)
from litellm.types.utils import (
    ChatCompletionDeltaToolCall,
    ChatCompletionMessageToolCall,
    ChatCompletionRedactedThinkingBlock,
    Choices,
    Delta,
    EmbeddingResponse,
    Function,
    HiddenParams,
    ImageResponse,
)
from litellm.types.utils import Logprobs as TextCompletionLogprobs
from litellm.types.utils import (
    Message,
    ModelResponse,
    RerankResponse,
    StreamingChoices,
    TextChoices,
    TextCompletionResponse,
    TranscriptionResponse,
    Usage,
)

from .get_headers import get_response_headers


def convert_tool_call_to_json_mode(
    tool_calls: List[ChatCompletionMessageToolCall],
    convert_tool_call_to_json_mode: bool,
) -> Tuple[Optional[Message], Optional[str]]:
    if _should_convert_tool_call_to_json_mode(
        tool_calls=tool_calls,
        convert_tool_call_to_json_mode=convert_tool_call_to_json_mode,
    ):
        # to support 'json_schema' logic on older models
        json_mode_content_str: Optional[str] = tool_calls[0]["function"].get(
            "arguments"
        )
        if json_mode_content_str is not None:
            message = litellm.Message(content=json_mode_content_str)
            finish_reason = "stop"
            return message, finish_reason
    return None, None


async def convert_to_streaming_response_async(response_object: Optional[dict] = None):
    """
    Asynchronously converts a response object to a streaming response.

    Args:
        response_object (Optional[dict]): The response object to be converted. Defaults to None.

    Raises:
        Exception: If the response object is None.

    Yields:
        ModelResponse: The converted streaming response object.

    Returns:
        None
    """
    if response_object is None:
        raise Exception("Error in response object format")

    model_response_object = ModelResponse(stream=True)

    if model_response_object is None:
        raise Exception("Error in response creating model response object")

    choice_list = []

    for idx, choice in enumerate(response_object["choices"]):
        if (
            choice["message"].get("tool_calls", None) is not None
            and isinstance(choice["message"]["tool_calls"], list)
            and len(choice["message"]["tool_calls"]) > 0
            and isinstance(choice["message"]["tool_calls"][0], dict)
        ):
            pydantic_tool_calls = []
            for index, t in enumerate(choice["message"]["tool_calls"]):
                if "index" not in t:
                    t["index"] = index
                pydantic_tool_calls.append(ChatCompletionDeltaToolCall(**t))
            choice["message"]["tool_calls"] = pydantic_tool_calls
        delta = Delta(
            content=choice["message"].get("content", None),
            role=choice["message"]["role"],
            function_call=choice["message"].get("function_call", None),
            tool_calls=choice["message"].get("tool_calls", None),
        )
        finish_reason = choice.get("finish_reason", None)

        if finish_reason is None:
            finish_reason = choice.get("finish_details")

        logprobs = choice.get("logprobs", None)

        choice = StreamingChoices(
            finish_reason=finish_reason, index=idx, delta=delta, logprobs=logprobs
        )
        choice_list.append(choice)

    model_response_object.choices = choice_list

    if "usage" in response_object and response_object["usage"] is not None:
        setattr(
            model_response_object,
            "usage",
            Usage(
                completion_tokens=response_object["usage"].get("completion_tokens", 0),
                prompt_tokens=response_object["usage"].get("prompt_tokens", 0),
                total_tokens=response_object["usage"].get("total_tokens", 0),
            ),
        )

    if "id" in response_object:
        model_response_object.id = response_object["id"]

    if "created" in response_object:
        model_response_object.created = response_object["created"]

    if "system_fingerprint" in response_object:
        model_response_object.system_fingerprint = response_object["system_fingerprint"]

    if "model" in response_object:
        model_response_object.model = response_object["model"]

    yield model_response_object
    await asyncio.sleep(0)


def convert_to_streaming_response(response_object: Optional[dict] = None):
    # used for yielding Cache hits when stream == True
    if response_object is None:
        raise Exception("Error in response object format")

    model_response_object = ModelResponse(stream=True)
    choice_list = []
    for idx, choice in enumerate(response_object["choices"]):
        delta = Delta(**choice["message"])
        finish_reason = choice.get("finish_reason", None)
        if finish_reason is None:
            # gpt-4 vision can return 'finish_reason' or 'finish_details'
            finish_reason = choice.get("finish_details")
        logprobs = choice.get("logprobs", None)
        enhancements = choice.get("enhancements", None)
        choice = StreamingChoices(
            finish_reason=finish_reason,
            index=idx,
            delta=delta,
            logprobs=logprobs,
            enhancements=enhancements,
        )

        choice_list.append(choice)
    model_response_object.choices = choice_list

    if "usage" in response_object and response_object["usage"] is not None:
        setattr(model_response_object, "usage", Usage())
        model_response_object.usage.completion_tokens = response_object["usage"].get("completion_tokens", 0)  # type: ignore
        model_response_object.usage.prompt_tokens = response_object["usage"].get("prompt_tokens", 0)  # type: ignore
        model_response_object.usage.total_tokens = response_object["usage"].get("total_tokens", 0)  # type: ignore

    if "id" in response_object:
        model_response_object.id = response_object["id"]

    if "created" in response_object:
        model_response_object.created = response_object["created"]

    if "system_fingerprint" in response_object:
        model_response_object.system_fingerprint = response_object["system_fingerprint"]

    if "model" in response_object:
        model_response_object.model = response_object["model"]
    yield model_response_object


from collections import defaultdict


def _handle_invalid_parallel_tool_calls(
    tool_calls: List[ChatCompletionMessageToolCall],
):
    """
    Handle hallucinated parallel tool call from openai - https://community.openai.com/t/model-tries-to-call-unknown-function-multi-tool-use-parallel/490653

    Code modified from: https://github.com/phdowling/openai_multi_tool_use_parallel_patch/blob/main/openai_multi_tool_use_parallel_patch.py
    """

    if tool_calls is None:
        return
    try:
        replacements: Dict[int, List[ChatCompletionMessageToolCall]] = defaultdict(list)
        for i, tool_call in enumerate(tool_calls):
            current_function = tool_call.function.name
            function_args = json.loads(tool_call.function.arguments)
            if current_function == "multi_tool_use.parallel":
                verbose_logger.debug(
                    "OpenAI did a weird pseudo-multi-tool-use call, fixing call structure.."
                )
                for _fake_i, _fake_tool_use in enumerate(function_args["tool_uses"]):
                    _function_args = _fake_tool_use["parameters"]
                    _current_function = _fake_tool_use["recipient_name"]
                    if _current_function.startswith("functions."):
                        _current_function = _current_function[len("functions.") :]

                    fixed_tc = ChatCompletionMessageToolCall(
                        id=f"{tool_call.id}_{_fake_i}",
                        type="function",
                        function=Function(
                            name=_current_function, arguments=json.dumps(_function_args)
                        ),
                    )
                    replacements[i].append(fixed_tc)

        shift = 0
        for i, replacement in replacements.items():
            tool_calls[:] = (
                tool_calls[: i + shift] + replacement + tool_calls[i + shift + 1 :]
            )
            shift += len(replacement)

        return tool_calls
    except json.JSONDecodeError:
        # if there is a JSONDecodeError, return the original tool_calls
        return tool_calls


def _parse_content_for_reasoning(
    message_text: Optional[str],
) -> Tuple[Optional[str], Optional[str]]:
    """
    Parse the content for reasoning

    Returns:
    - reasoning_content: The content of the reasoning
    - content: The content of the message
    """
    if not message_text:
        return None, message_text

    reasoning_match = re.match(
        r"<(?:think|thinking)>(.*?)</(?:think|thinking)>(.*)", message_text, re.DOTALL
    )

    if reasoning_match:
        return reasoning_match.group(1), reasoning_match.group(2)

    return None, message_text


def _extract_reasoning_content(message: dict) -> Tuple[Optional[str], Optional[str]]:
    """
    Extract reasoning content and main content from a message.

    Args:
        message (dict): The message dictionary that may contain reasoning_content

    Returns:
        tuple[Optional[str], Optional[str]]: A tuple of (reasoning_content, content)
    """
    message_content = message.get("content")
    if "reasoning_content" in message:
        return message["reasoning_content"], message["content"]
    elif "reasoning" in message:
        return message["reasoning"], message["content"]
    elif isinstance(message_content, str):
        return _parse_content_for_reasoning(message_content)
    return None, message_content


class LiteLLMResponseObjectHandler:
    @staticmethod
    def convert_to_image_response(
        response_object: dict,
        model_response_object: Optional[ImageResponse] = None,
        hidden_params: Optional[dict] = None,
    ) -> ImageResponse:
        response_object.update({"hidden_params": hidden_params})

        # Handle gpt-image-1 usage field with None values
        if "usage" in response_object and response_object["usage"] is not None:
            usage = response_object["usage"]
            # Check if usage fields are None and provide defaults
            if usage.get("input_tokens") is None:
                usage["input_tokens"] = 0
            if usage.get("output_tokens") is None:
                usage["output_tokens"] = 0
            if usage.get("total_tokens") is None:
                usage["total_tokens"] = usage["input_tokens"] + usage["output_tokens"]
            if usage.get("input_tokens_details") is None:
                usage["input_tokens_details"] = {
                    "image_tokens": 0,
                    "text_tokens": 0,
                }

        if model_response_object is None:
            model_response_object = ImageResponse(**response_object)
            return model_response_object
        else:
            model_response_dict = model_response_object.model_dump()

            model_response_dict.update(response_object)
            model_response_object = ImageResponse(**model_response_dict)
            return model_response_object

    @staticmethod
    def convert_to_moderation_response(
        response_object: dict,
    ) -> OpenAIModerationResponse:
        return OpenAIModerationResponse(**response_object)

    @staticmethod
    def convert_chat_to_text_completion(
        response: ModelResponse,
        text_completion_response: TextCompletionResponse,
        custom_llm_provider: Optional[str] = None,
    ) -> TextCompletionResponse:
        """
        Converts a chat completion response to a text completion response format.

        Note: This is used for huggingface. For OpenAI / Azure Text the providers files directly return TextCompletionResponse which we then send to user

        Args:
            response (ModelResponse): The chat completion response to convert

        Returns:
            TextCompletionResponse: The converted text completion response

        Example:
            chat_response = completion(model="gpt-3.5-turbo", messages=[{"role": "user", "content": "Hi"}])
            text_response = convert_chat_to_text_completion(chat_response)
        """
        transformed_logprobs = LiteLLMResponseObjectHandler._convert_provider_response_logprobs_to_text_completion_logprobs(
            response=response,
            custom_llm_provider=custom_llm_provider,
        )

        text_completion_response["id"] = response.get("id", None)
        text_completion_response["object"] = "text_completion"
        text_completion_response["created"] = response.get("created", None)
        text_completion_response["model"] = response.get("model", None)
        choices_list: List[TextChoices] = []

        # Convert each choice to TextChoices
        for choice in response["choices"]:
            text_choices = TextChoices()
            text_choices["text"] = choice["message"]["content"]
            text_choices["index"] = choice["index"]
            text_choices["logprobs"] = transformed_logprobs
            text_choices["finish_reason"] = choice["finish_reason"]
            choices_list.append(text_choices)

        text_completion_response["choices"] = choices_list
        text_completion_response["usage"] = response.get("usage", None)
        text_completion_response._hidden_params = HiddenParams(
            **response._hidden_params
        )
        return text_completion_response

    @staticmethod
    def _convert_provider_response_logprobs_to_text_completion_logprobs(
        response: ModelResponse,
        custom_llm_provider: Optional[str] = None,
    ) -> Optional[TextCompletionLogprobs]:
        """
        Convert logprobs from provider to OpenAI.Completion() format

        Only supported for HF TGI models
        """
        transformed_logprobs: Optional[TextCompletionLogprobs] = None

        return transformed_logprobs


def _should_convert_tool_call_to_json_mode(
    tool_calls: Optional[
        Union[List[ChatCompletionMessageToolCall], List[DatabricksTool]]
    ] = None,
    convert_tool_call_to_json_mode: Optional[bool] = None,
) -> bool:
    """
    Determine if tool calls should be converted to JSON mode
    """
    if (
        convert_tool_call_to_json_mode
        and tool_calls is not None
        and len(tool_calls) == 1
        and tool_calls[0]["function"]["name"] == RESPONSE_FORMAT_TOOL_NAME
    ):
        return True
    return False


def convert_to_model_response_object(  # noqa: PLR0915
    response_object: Optional[dict] = None,
    model_response_object: Optional[
        Union[
            ModelResponse,
            EmbeddingResponse,
            ImageResponse,
            TranscriptionResponse,
            RerankResponse,
        ]
    ] = None,
    response_type: Literal[
        "completion", "embedding", "image_generation", "audio_transcription", "rerank"
    ] = "completion",
    stream=False,
    start_time=None,
    end_time=None,
    hidden_params: Optional[dict] = None,
    _response_headers: Optional[dict] = None,
    convert_tool_call_to_json_mode: Optional[
        bool
    ] = None,  # used for supporting 'json_schema' on older models
):
    received_args = locals()
    additional_headers = get_response_headers(_response_headers)

    if hidden_params is None:
        hidden_params = {}
    hidden_params["additional_headers"] = additional_headers

    ### CHECK IF ERROR IN RESPONSE ### - openrouter returns these in the dictionary
    if (
        response_object is not None
        and "error" in response_object
        and response_object["error"] is not None
    ):
        error_args = {"status_code": 422, "message": "Error in response object"}
        if isinstance(response_object["error"], dict):
            if "code" in response_object["error"]:
                error_args["status_code"] = response_object["error"]["code"]
            if "message" in response_object["error"]:
                if isinstance(response_object["error"]["message"], dict):
                    message_str = json.dumps(response_object["error"]["message"])
                else:
                    message_str = str(response_object["error"]["message"])
                error_args["message"] = message_str
        raised_exception = Exception()
        setattr(raised_exception, "status_code", error_args["status_code"])
        setattr(raised_exception, "message", error_args["message"])
        raise raised_exception

    try:
        if response_type == "completion" and (
            model_response_object is None
            or isinstance(model_response_object, ModelResponse)
        ):
            if response_object is None or model_response_object is None:
                raise Exception("Error in response object format")
            if stream is True:
                # for returning cached responses, we need to yield a generator
                return convert_to_streaming_response(response_object=response_object)
            choice_list = []

            assert response_object["choices"] is not None and isinstance(
                response_object["choices"], Iterable
            )

            for idx, choice in enumerate(response_object["choices"]):
                ## HANDLE JSON MODE - anthropic returns single function call]
                tool_calls = choice["message"].get("tool_calls", None)
                if tool_calls is not None:
                    _openai_tool_calls = []
                    for _tc in tool_calls:
                        _openai_tc = ChatCompletionMessageToolCall(**_tc)
                        _openai_tool_calls.append(_openai_tc)
                    fixed_tool_calls = _handle_invalid_parallel_tool_calls(
                        _openai_tool_calls
                    )

                    if fixed_tool_calls is not None:
                        tool_calls = fixed_tool_calls

                message: Optional[Message] = None
                finish_reason: Optional[str] = None
                if _should_convert_tool_call_to_json_mode(
                    tool_calls=tool_calls,
                    convert_tool_call_to_json_mode=convert_tool_call_to_json_mode,
                ):
                    # to support 'json_schema' logic on older models
                    json_mode_content_str: Optional[str] = tool_calls[0][
                        "function"
                    ].get("arguments")
                    if json_mode_content_str is not None:
                        message = litellm.Message(content=json_mode_content_str)
                        finish_reason = "stop"
                if message is None:
                    provider_specific_fields = {}
                    message_keys = Message.model_fields.keys()
                    for field in choice["message"].keys():
                        if field not in message_keys:
                            provider_specific_fields[field] = choice["message"][field]

                    # Handle reasoning models that display `reasoning_content` within `content`
                    reasoning_content, content = _extract_reasoning_content(
                        choice["message"]
                    )

                    # Handle thinking models that display `thinking_blocks` within `content`
                    thinking_blocks: Optional[
                        List[
                            Union[
                                ChatCompletionThinkingBlock,
                                ChatCompletionRedactedThinkingBlock,
                            ]
                        ]
                    ] = None
                    if "thinking_blocks" in choice["message"]:
                        thinking_blocks = choice["message"]["thinking_blocks"]
                        provider_specific_fields["thinking_blocks"] = thinking_blocks

                    if reasoning_content:
                        provider_specific_fields[
                            "reasoning_content"
                        ] = reasoning_content

                    message = Message(
                        content=content,
                        role=choice["message"]["role"] or "assistant",
                        function_call=choice["message"].get("function_call", None),
                        tool_calls=tool_calls,
                        audio=choice["message"].get("audio", None),
                        provider_specific_fields=provider_specific_fields,
                        reasoning_content=reasoning_content,
                        thinking_blocks=thinking_blocks,
                        annotations=choice["message"].get("annotations", None),
                    )
                    finish_reason = choice.get("finish_reason", None)
                if finish_reason is None:
                    # gpt-4 vision can return 'finish_reason' or 'finish_details'
                    finish_reason = choice.get("finish_details") or "stop"
                if (
                    finish_reason == "stop"
                    and message.tool_calls
                    and len(message.tool_calls) > 0
                ):
                    finish_reason = "tool_calls"

                ## PROVIDER SPECIFIC FIELDS ##
                provider_specific_fields = {}
                for field in choice.keys():
                    if field not in Choices.model_fields.keys():
                        provider_specific_fields[field] = choice[field]

                logprobs = choice.get("logprobs", None)
                enhancements = choice.get("enhancements", None)
                choice = Choices(
                    finish_reason=finish_reason,
                    index=idx,
                    message=message,
                    logprobs=logprobs,
                    enhancements=enhancements,
                    provider_specific_fields=provider_specific_fields,
                )
                choice_list.append(choice)
            model_response_object.choices = choice_list

            if "usage" in response_object and response_object["usage"] is not None:
                usage_object = litellm.Usage(**response_object["usage"])
                setattr(model_response_object, "usage", usage_object)
            if "created" in response_object:
                model_response_object.created = response_object["created"] or int(
                    time.time()
                )

            if "id" in response_object:
                model_response_object.id = response_object["id"] or str(uuid.uuid4())

            if "system_fingerprint" in response_object:
                model_response_object.system_fingerprint = response_object[
                    "system_fingerprint"
                ]

            if "model" in response_object:
                if model_response_object.model is None:
                    model_response_object.model = response_object["model"]
                elif (
                    "/" in model_response_object.model
                    and response_object["model"] is not None
                ):
                    openai_compatible_provider = model_response_object.model.split("/")[
                        0
                    ]
                    model_response_object.model = (
                        openai_compatible_provider + "/" + response_object["model"]
                    )

            if start_time is not None and end_time is not None:
                if isinstance(start_time, type(end_time)):
                    model_response_object._response_ms = (  # type: ignore
                        end_time - start_time
                    ).total_seconds() * 1000

            if hidden_params is not None:
                if model_response_object._hidden_params is None:
                    model_response_object._hidden_params = {}
                model_response_object._hidden_params.update(hidden_params)

            if _response_headers is not None:
                model_response_object._response_headers = _response_headers

            special_keys = list(litellm.ModelResponse.model_fields.keys())
            special_keys.append("usage")
            for k, v in response_object.items():
                if k not in special_keys:
                    setattr(model_response_object, k, v)

            return model_response_object
        elif response_type == "embedding" and (
            model_response_object is None
            or isinstance(model_response_object, EmbeddingResponse)
        ):
            if response_object is None:
                raise Exception("Error in response object format")

            if model_response_object is None:
                model_response_object = EmbeddingResponse()

            if "model" in response_object:
                model_response_object.model = response_object["model"]

            if "object" in response_object:
                model_response_object.object = response_object["object"]

            model_response_object.data = response_object["data"]

            if "usage" in response_object and response_object["usage"] is not None:
                model_response_object.usage.completion_tokens = response_object["usage"].get("completion_tokens", 0)  # type: ignore
                model_response_object.usage.prompt_tokens = response_object["usage"].get("prompt_tokens", 0)  # type: ignore
                model_response_object.usage.total_tokens = response_object["usage"].get("total_tokens", 0)  # type: ignore

            if start_time is not None and end_time is not None:
                model_response_object._response_ms = (  # type: ignore
                    end_time - start_time
                ).total_seconds() * 1000  # return response latency in ms like openai

            if hidden_params is not None:
                model_response_object._hidden_params = hidden_params

            if _response_headers is not None:
                model_response_object._response_headers = _response_headers

            return model_response_object
        elif response_type == "image_generation" and (
            model_response_object is None
            or isinstance(model_response_object, ImageResponse)
        ):
            if response_object is None:
                raise Exception("Error in response object format")

            return LiteLLMResponseObjectHandler.convert_to_image_response(
                response_object=response_object,
                model_response_object=model_response_object,
                hidden_params=hidden_params,
            )

        elif response_type == "audio_transcription" and (
            model_response_object is None
            or isinstance(model_response_object, TranscriptionResponse)
        ):
            if response_object is None:
                raise Exception("Error in response object format")

            if model_response_object is None:
                model_response_object = TranscriptionResponse()

            if "text" in response_object:
                model_response_object.text = response_object["text"]

            optional_keys = ["language", "task", "duration", "words", "segments"]
            for key in optional_keys:  # not guaranteed to be in response
                if key in response_object:
                    setattr(model_response_object, key, response_object[key])

            if hidden_params is not None:
                model_response_object._hidden_params = hidden_params

            if _response_headers is not None:
                model_response_object._response_headers = _response_headers

            return model_response_object
        elif response_type == "rerank" and (
            model_response_object is None
            or isinstance(model_response_object, RerankResponse)
        ):
            if response_object is None:
                raise Exception("Error in response object format")

            if model_response_object is None:
                model_response_object = RerankResponse(**response_object)
                return model_response_object

            if "id" in response_object:
                model_response_object.id = response_object["id"]

            if "meta" in response_object:
                model_response_object.meta = response_object["meta"]

            if "results" in response_object:
                model_response_object.results = response_object["results"]

            return model_response_object
    except Exception:
        raise Exception(
            f"Invalid response object {traceback.format_exc()}\n\nreceived_args={received_args}"
        )

# === NexusCore/openenv\Lib\site-packages\adodbapi\apibase.py ===
"""adodbapi.apibase - A python DB API 2.0 (PEP 249) interface to Microsoft ADO

Copyright (C) 2002 Henrik Ekelund, version 2.1 by Vernon Cole
* https://sourceforge.net/projects/pywin32
* https://sourceforge.net/projects/adodbapi
"""

from __future__ import annotations

import datetime
import decimal
import numbers
import sys
import time
from collections.abc import Callable, Iterable, Mapping

# noinspection PyUnresolvedReferences
from . import ado_consts as adc

verbose = False  # debugging flag


# ------- Error handlers ------
def standardErrorHandler(connection, cursor, errorclass, errorvalue):
    err = (errorclass, errorvalue)
    try:
        connection.messages.append(err)
    except:
        pass
    if cursor is not None:
        try:
            cursor.messages.append(err)
        except:
            pass
    raise errorclass(errorvalue)


class Error(Exception):
    pass  # Exception that is the base class of all other error
    # exceptions. You can use this to catch all errors with one
    # single 'except' statement. Warnings are not considered
    # errors and thus should not use this class as base. It must
    # be a subclass of the Python StandardError (defined in the
    # module exceptions).


class Warning(Exception):
    pass


class InterfaceError(Error):
    pass


class DatabaseError(Error):
    pass


class InternalError(DatabaseError):
    pass


class OperationalError(DatabaseError):
    pass


class ProgrammingError(DatabaseError):
    pass


class IntegrityError(DatabaseError):
    pass


class DataError(DatabaseError):
    pass


class NotSupportedError(DatabaseError):
    pass


class FetchFailedError(OperationalError):
    """
    Error is used by RawStoredProcedureQuerySet to determine when a fetch
    failed due to a connection being closed or there is no record set
    returned. (Non-standard, added especially for django)
    """

    pass


# # # # # ----- Type Objects and Constructors ----- # # # # #
# Many databases need to have the input in a particular format for binding to an operation's input parameters.
# For example, if an input is destined for a DATE column, then it must be bound to the database in a particular
# string format. Similar problems exist for "Row ID" columns or large binary items (e.g. blobs or RAW columns).
# This presents problems for Python since the parameters to the executeXXX() method are untyped.
# When the database module sees a Python string object, it doesn't know if it should be bound as a simple CHAR
# column, as a raw BINARY item, or as a DATE.
#
# To overcome this problem, a module must provide the constructors defined below to create objects that can
# hold special values. When passed to the cursor methods, the module can then detect the proper type of
# the input parameter and bind it accordingly.

# A Cursor Object's description attribute returns information about each of the result columns of a query.
# The type_code must compare equal to one of Type Objects defined below. Type Objects may be equal to more than
# one type code (e.g. DATETIME could be equal to the type codes for date, time and timestamp columns;
# see the Implementation Hints below for details).

# SQL NULL values are represented by the Python None singleton on input and output.

# Note: Usage of Unix ticks for database interfacing can cause troubles because of the limited date range they cover.


# def Date(year,month,day):
#     "This function constructs an object holding a date value. "
#     return dateconverter.date(year,month,day)  #dateconverter.Date(year,month,day)
#
# def Time(hour,minute,second):
#     "This function constructs an object holding a time value. "
#     return dateconverter.time(hour, minute, second) # dateconverter.Time(hour,minute,second)
#
# def Timestamp(year,month,day,hour,minute,second):
#     "This function constructs an object holding a time stamp value. "
#     return dateconverter.datetime(year,month,day,hour,minute,second)
#
# def DateFromTicks(ticks):
#     """This function constructs an object holding a date value from the given ticks value
#     (number of seconds since the epoch; see the documentation of the standard Python time module for details). """
#     return Date(*time.gmtime(ticks)[:3])
#
# def TimeFromTicks(ticks):
#     """This function constructs an object holding a time value from the given ticks value
#     (number of seconds since the epoch; see the documentation of the standard Python time module for details). """
#     return Time(*time.gmtime(ticks)[3:6])
#
# def TimestampFromTicks(ticks):
#     """This function constructs an object holding a time stamp value from the given
#     ticks value (number of seconds since the epoch;
#     see the documentation of the standard Python time module for details). """
#     return Timestamp(*time.gmtime(ticks)[:6])
#
# def Binary(aString):
#     """This function constructs an object capable of holding a binary (long) string value. """
#     b = bytes(aString)
#     return b
# -----     Time converters ----------------------------------------------
class TimeConverter:  # this is a generic time converter skeleton
    def __init__(self):  # the details will be filled in by instances
        self._ordinal_1899_12_31 = datetime.date(1899, 12, 31).toordinal() - 1
        # Use cls.types to compare if an input parameter is a datetime
        self.types = {
            # Dynamically get the types as the methods may be overriden
            type(self.Date(2000, 1, 1)),
            type(self.Time(12, 1, 1)),
            type(self.Timestamp(2000, 1, 1, 12, 1, 1)),
            datetime.datetime,
            datetime.time,
            datetime.date,
        }

    def COMDate(self, obj):
        """Returns a ComDate from a date-time"""
        try:  # most likely a datetime
            tt = obj.timetuple()

            try:
                ms = obj.microsecond
            except:
                ms = 0
            return self.ComDateFromTuple(tt, ms)
        except:  # might be a tuple
            try:
                return self.ComDateFromTuple(obj)
            except:
                raise ValueError(f'Cannot convert "{obj!r}" to COMdate.')

    def ComDateFromTuple(self, t, microseconds=0):
        d = datetime.date(t[0], t[1], t[2])
        integerPart = d.toordinal() - self._ordinal_1899_12_31
        ms = (t[3] * 3600 + t[4] * 60 + t[5]) * 1000000 + microseconds
        fractPart = float(ms) / 86400000000.0
        return integerPart + fractPart

    def DateObjectFromCOMDate(self, comDate):
        "Returns an object of the wanted type from a ComDate"
        raise NotImplementedError  # "Abstract class"

    def Date(self, year, month, day):
        "This function constructs an object holding a date value."
        raise NotImplementedError  # "Abstract class"

    def Time(self, hour, minute, second):
        "This function constructs an object holding a time value."
        raise NotImplementedError  # "Abstract class"

    def Timestamp(self, year, month, day, hour, minute, second):
        "This function constructs an object holding a time stamp value."
        raise NotImplementedError  # "Abstract class"
        # all purpose date to ISO format converter

    def DateObjectToIsoFormatString(self, obj):
        "This function should return a string in the format 'YYYY-MM-dd HH:MM:SS:ms' (ms optional)"
        try:  # most likely, a datetime.datetime
            s = obj.isoformat(" ")
        except (TypeError, AttributeError):
            if isinstance(obj, datetime.date):
                s = obj.isoformat() + " 00:00:00"  # return exact midnight
            else:
                try:  # but may be time.struct_time
                    s = time.strftime("%Y-%m-%d %H:%M:%S", obj)
                except:
                    raise ValueError(f'Cannot convert "{obj!r}" to isoformat')
        return s


class pythonDateTimeConverter(TimeConverter):  # standard since Python 2.3
    def __init__(self):
        TimeConverter.__init__(self)

    def DateObjectFromCOMDate(self, comDate):
        if isinstance(comDate, datetime.datetime):
            odn = comDate.toordinal()
            tim = comDate.time()
            new = datetime.datetime.combine(datetime.datetime.fromordinal(odn), tim)
            return new
            # return comDate.replace(tzinfo=None) # make non aware
        else:
            fComDate = float(comDate)  # ComDate is number of days since 1899-12-31
        integerPart = int(fComDate)
        floatpart = fComDate - integerPart
        ##if floatpart == 0.0:
        ##    return datetime.date.fromordinal(integerPart + self._ordinal_1899_12_31)
        dte = datetime.datetime.fromordinal(
            integerPart + self._ordinal_1899_12_31
        ) + datetime.timedelta(milliseconds=floatpart * 86400000)
        # millisecondsperday=86400000 # 24*60*60*1000
        return dte

    def Date(self, year, month, day):
        return datetime.date(year, month, day)

    def Time(self, hour, minute, second):
        return datetime.time(hour, minute, second)

    def Timestamp(self, year, month, day, hour, minute, second):
        return datetime.datetime(year, month, day, hour, minute, second)


class pythonTimeConverter(TimeConverter):  # the old, ?nix type date and time
    def __init__(self):  # caution: this Class gets confised by timezones and DST
        TimeConverter.__init__(self)
        self.types.add(time.struct_time)

    def DateObjectFromCOMDate(self, comDate):
        "Returns ticks since 1970"
        if isinstance(comDate, datetime.datetime):
            return comDate.timetuple()
        else:
            fcomDate = float(comDate)
        secondsperday = 86400  # 24*60*60
        # ComDate is number of days since 1899-12-31, gmtime epoch is 1970-1-1 = 25569 days
        t = time.gmtime(secondsperday * (fcomDate - 25569.0))
        return t  # year,month,day,hour,minute,second,weekday,julianday,daylightsaving=t

    def Date(self, year, month, day):
        return self.Timestamp(year, month, day, 0, 0, 0)

    def Time(self, hour, minute, second):
        return time.gmtime((hour * 60 + minute) * 60 + second)

    def Timestamp(self, year, month, day, hour, minute, second):
        return time.localtime(
            time.mktime((year, month, day, hour, minute, second, 0, 0, -1))
        )


base_dateconverter = pythonDateTimeConverter()

# ------ DB API required module attributes ---------------------
threadsafety = 1  # TODO -- find out whether this module is actually BETTER than 1.

apilevel = "2.0"  # String constant stating the supported DB API level.

paramstyle = "qmark"  # the default parameter style

# ------ control for an extension which may become part of DB API 3.0 ---
accepted_paramstyles = ("qmark", "named", "format", "pyformat", "dynamic")

# ------------------------------------------------------------------------------------------
# define similar types for generic conversion routines
adoIntegerTypes = (
    adc.adInteger,
    adc.adSmallInt,
    adc.adTinyInt,
    adc.adUnsignedInt,
    adc.adUnsignedSmallInt,
    adc.adUnsignedTinyInt,
    adc.adBoolean,
    adc.adError,
)  # max 32 bits
adoRowIdTypes = (adc.adChapter,)  # v2.1 Rose
adoLongTypes = (adc.adBigInt, adc.adFileTime, adc.adUnsignedBigInt)
adoExactNumericTypes = (
    adc.adDecimal,
    adc.adNumeric,
    adc.adVarNumeric,
    adc.adCurrency,
)  # v2.3 Cole
adoApproximateNumericTypes = (adc.adDouble, adc.adSingle)  # v2.1 Cole
adoStringTypes = (
    adc.adBSTR,
    adc.adChar,
    adc.adLongVarChar,
    adc.adLongVarWChar,
    adc.adVarChar,
    adc.adVarWChar,
    adc.adWChar,
)
adoBinaryTypes = (adc.adBinary, adc.adLongVarBinary, adc.adVarBinary)
adoDateTimeTypes = (adc.adDBTime, adc.adDBTimeStamp, adc.adDate, adc.adDBDate)
adoRemainingTypes = (
    adc.adEmpty,
    adc.adIDispatch,
    adc.adIUnknown,
    adc.adPropVariant,
    adc.adArray,
    adc.adUserDefined,
    adc.adVariant,
    adc.adGUID,
)


# this class is a trick to determine whether a type is a member of a related group of types. see PEP notes
class DBAPITypeObject:
    def __init__(self, valuesTuple):
        self.values = frozenset(valuesTuple)

    def __eq__(self, other):
        return other in self.values

    def __ne__(self, other):
        return other not in self.values


"""This type object is used to describe columns in a database that are string-based (e.g. CHAR). """
STRING = DBAPITypeObject(adoStringTypes)

"""This type object is used to describe (long) binary columns in a database (e.g. LONG, RAW, BLOBs). """
BINARY = DBAPITypeObject(adoBinaryTypes)

"""This type object is used to describe numeric columns in a database. """
NUMBER = DBAPITypeObject(
    adoIntegerTypes + adoLongTypes + adoExactNumericTypes + adoApproximateNumericTypes
)

"""This type object is used to describe date/time columns in a database. """

DATETIME = DBAPITypeObject(adoDateTimeTypes)
"""This type object is used to describe the "Row ID" column in a database. """
ROWID = DBAPITypeObject(adoRowIdTypes)

OTHER = DBAPITypeObject(adoRemainingTypes)

# ------- utilities for translating python data types to ADO data types ---------------------------------
typeMap = {
    memoryview: adc.adVarBinary,
    float: adc.adDouble,
    type(None): adc.adEmpty,
    str: adc.adBSTR,
    bool: adc.adBoolean,  # v2.1 Cole
    decimal.Decimal: adc.adDecimal,
    int: adc.adBigInt,
    bytes: adc.adVarBinary,
}


def pyTypeToADOType(d):
    tp = type(d)
    try:
        return typeMap[tp]
    except KeyError:  #   The type was not defined in the pre-computed Type table
        from . import dateconverter

        # maybe it is one of our supported Date/Time types
        if tp in dateconverter.types:
            return adc.adDate
        #  otherwise, attempt to discern the type by probing the data object itself -- to handle duck typing
        if isinstance(d, str):
            return adc.adBSTR
        if isinstance(d, numbers.Integral):
            return adc.adBigInt
        if isinstance(d, numbers.Real):
            return adc.adDouble
        raise DataError(f'cannot convert "{d!r}" (type={tp}) to ADO')


# # # # # # # # # # # # - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
# functions to convert database values to Python objects
# ------------------------------------------------------------------------
# variant type : function converting variant to Python value
def variantConvertDate(v):
    from . import dateconverter  # this function only called when adodbapi is running

    return dateconverter.DateObjectFromCOMDate(v)


def cvtString(variant):  # use to get old action of adodbapi v1 if desired
    return str(variant)


def cvtDecimal(variant):  # better name
    return _convertNumberWithCulture(variant, decimal.Decimal)


def cvtNumeric(variant):  # older name - don't break old code
    return cvtDecimal(variant)


def cvtFloat(variant):
    return _convertNumberWithCulture(variant, float)


def _convertNumberWithCulture(variant, f):
    try:
        return f(variant)
    except (ValueError, TypeError, decimal.InvalidOperation):
        try:
            europeVsUS = str(variant).replace(",", ".")
            return f(europeVsUS)
        except (ValueError, TypeError, decimal.InvalidOperation):
            pass


def cvtInt(variant):
    return int(variant)


def cvtLong(variant):  # only important in old versions where long and int differ
    return int(variant)


def cvtBuffer(variant):
    return bytes(variant)


def cvtUnicode(variant):
    return str(variant)


def identity(x):
    return x


def cvtUnusual(variant):
    if verbose > 1:
        sys.stderr.write(f"Conversion called for Unusual data={variant!r}\n")
    return variant  # cannot find conversion function -- just give the data to the user


def convert_to_python(variant, func):  # convert DB value into Python value
    if variant is None:
        return None
    return func(variant)  # call the appropriate conversion function


class MultiMap(dict[int, Callable[[object], object]]):
    # builds a dictionary from {(iterable,of,keys) : function}
    """A dictionary of ado.type : function
    -- but you can set multiple items by passing an iterable of keys"""

    # useful for defining conversion functions for groups of similar data types.
    def __init__(self, aDict: Mapping[Iterable[int] | int, Callable[[object], object]]):
        for k, v in aDict.items():
            self[k] = v  # we must call __setitem__

    def __setitem__(
        self, adoType: Iterable[int] | int, cvtFn: Callable[[object], object]
    ):
        "set a single item, or a whole iterable of items"
        if isinstance(adoType, Iterable):
            # user passed us an iterable, set them individually
            for type in adoType:
                dict.__setitem__(self, type, cvtFn)
        else:
            dict.__setitem__(self, adoType, cvtFn)


# initialize variantConversions dictionary used to convert SQL to Python
# this is the dictionary of default conversion functions, built by the class above.
# this becomes a class attribute for the Connection, and that attribute is used
# to build the list of column conversion functions for the Cursor
variantConversions = MultiMap(
    {
        adoDateTimeTypes: variantConvertDate,
        adoApproximateNumericTypes: cvtFloat,
        adoExactNumericTypes: cvtDecimal,  # use to force decimal rather than unicode
        adoLongTypes: cvtLong,
        adoIntegerTypes: cvtInt,
        adoRowIdTypes: cvtInt,
        adoStringTypes: identity,
        adoBinaryTypes: cvtBuffer,
        adoRemainingTypes: cvtUnusual,
    }
)

# # # # # classes to emulate the result of cursor.fetchxxx() as a sequence of sequences # # # # #
# "an ENUM of how my low level records are laid out"
RS_WIN_32, RS_ARRAY, RS_REMOTE = list(range(1, 4))


class SQLrow:  # a single database row
    # class to emulate a sequence, so that a column may be retrieved by either number or name
    def __init__(self, rows, index):  # "rows" is an _SQLrows object, index is which row
        self.rows = rows  # parent 'fetch' container object
        self.index = index  # my row number within parent

    def __getattr__(self, name):  # used for row.columnName type of value access
        try:
            return self._getValue(self.rows.columnNames[name.lower()])
        except KeyError:
            raise AttributeError('Unknown column name "{}"'.format(name))

    def _getValue(self, key):  # key must be an integer
        if (
            self.rows.recordset_format == RS_ARRAY
        ):  # retrieve from two-dimensional array
            v = self.rows.ado_results[key, self.index]
        elif self.rows.recordset_format == RS_REMOTE:
            v = self.rows.ado_results[self.index][key]
        else:  # pywin32 - retrieve from tuple of tuples
            v = self.rows.ado_results[key][self.index]
        if self.rows.converters is NotImplemented:
            return v
        return convert_to_python(v, self.rows.converters[key])

    def __len__(self):
        return self.rows.numberOfColumns

    def __getitem__(self, key):  # used for row[key] type of value access
        if isinstance(key, int):  # normal row[1] designation
            try:
                return self._getValue(key)
            except IndexError:
                raise
        if isinstance(key, slice):
            indices = key.indices(self.rows.numberOfColumns)
            vl = [self._getValue(i) for i in range(*indices)]
            return tuple(vl)
        try:
            return self._getValue(
                self.rows.columnNames[key.lower()]
            )  # extension row[columnName] designation
        except (KeyError, TypeError):
            er, st, tr = sys.exc_info()
            raise er(f'No such key as "{key!r}" in {self!r}').with_traceback(tr)

    def __iter__(self):
        return iter(self.__next__())

    def __next__(self):
        for n in range(self.rows.numberOfColumns):
            yield self._getValue(n)

    def __repr__(self):  # create a human readable representation
        taglist = sorted(list(self.rows.columnNames.items()), key=lambda x: x[1])
        s = "<SQLrow={"
        for name, i in taglist:
            s += f"{name}:{self._getValue(i)!r}, "
        return s[:-2] + "}>"

    def __str__(self):  # create a pretty human readable representation
        return str(
            tuple(str(self._getValue(i)) for i in range(self.rows.numberOfColumns))
        )

    # TO-DO implement pickling an SQLrow directly
    # def __getstate__(self): return self.__dict__
    # def __setstate__(self, d): self.__dict__.update(d)
    # which basically tell pickle to treat your class just like a normal one,
    # taking self.__dict__ as representing the whole of the instance state,
    #  despite the existence of the __getattr__.
    # # # #


class SQLrows:
    # class to emulate a sequence for multiple rows using a container object
    def __init__(self, ado_results, numberOfRows, cursor):
        self.ado_results = ado_results  # raw result of SQL get
        try:
            self.recordset_format = cursor.recordset_format
            self.numberOfColumns = cursor.numberOfColumns
            self.converters = cursor.converters
            self.columnNames = cursor.columnNames
        except AttributeError:
            self.recordset_format = RS_ARRAY
            self.numberOfColumns = 0
            self.converters = []
            self.columnNames = {}
        self.numberOfRows = numberOfRows

    def __len__(self):
        return self.numberOfRows

    def __getitem__(self, item):  # used for row or row,column access
        if not self.ado_results:
            return []
        if isinstance(item, slice):  # will return a list of row objects
            indices = item.indices(self.numberOfRows)
            return [SQLrow(self, k) for k in range(*indices)]
        elif isinstance(item, tuple) and len(item) == 2:
            # d = some_rowsObject[i,j] will return a datum from a two-dimension address
            i, j = item
            if not isinstance(j, int):
                try:
                    j = self.columnNames[j.lower()]  # convert named column to numeric
                except KeyError:
                    raise KeyError(f"adodbapi: no such column name as {j!r}")
            if self.recordset_format == RS_ARRAY:  # retrieve from two-dimensional array
                v = self.ado_results[j, i]
            elif self.recordset_format == RS_REMOTE:
                v = self.ado_results[i][j]
            else:  # pywin32 - retrieve from tuple of tuples
                v = self.ado_results[j][i]
            if self.converters is NotImplemented:
                return v
            return convert_to_python(v, self.converters[j])
        else:
            row = SQLrow(self, item)  # new row descriptor
            return row

    def __iter__(self):
        return iter(self.__next__())

    def __next__(self):
        for n in range(self.numberOfRows):
            row = SQLrow(self, n)
            yield row
            # # # # #

    # # # # # functions to re-format SQL requests to other paramstyle requirements # # # # # # # # # #


def changeNamedToQmark(
    op,
):  # convert from 'named' paramstyle to ADO required '?'mark parameters
    outOp = ""
    outparms = []
    chunks = op.split(
        "'"
    )  # quote all literals -- odd numbered list results are literals.
    inQuotes = False
    for chunk in chunks:
        if inQuotes:  # this is inside a quote
            if chunk == "":  # double apostrophe to quote one apostrophe
                outOp = outOp[:-1]  # so take one away
            else:
                outOp += "'" + chunk + "'"  # else pass the quoted string as is.
        else:  # is SQL code -- look for a :namedParameter
            while chunk:  # some SQL string remains
                sp = chunk.split(":", 1)
                outOp += sp[0]  # concat the part up to the :
                s = ""
                try:
                    chunk = sp[1]
                except IndexError:
                    chunk = None
                if chunk:  # there was a parameter - parse it out
                    i = 0
                    c = chunk[0]
                    while c.isalnum() or c == "_":
                        i += 1
                        try:
                            c = chunk[i]
                        except IndexError:
                            break
                    s = chunk[:i]
                    chunk = chunk[i:]
                if s:
                    outparms.append(s)  # list the parameters in order
                    outOp += "?"  # put in the Qmark
        inQuotes = not inQuotes
    return outOp, outparms


def changeFormatToQmark(
    op,
):  # convert from 'format' paramstyle to ADO required '?'mark parameters
    outOp = ""
    outparams = []
    chunks = op.split(
        "'"
    )  # quote all literals -- odd numbered list results are literals.
    inQuotes = False
    for chunk in chunks:
        if inQuotes:
            if (
                outOp != "" and chunk == ""
            ):  # he used a double apostrophe to quote one apostrophe
                outOp = outOp[:-1]  # so take one away
            else:
                outOp += "'" + chunk + "'"  # else pass the quoted string as is.
        else:  # is SQL code -- look for a %s parameter
            if "%(" in chunk:  # ugh! pyformat!
                while chunk:  # some SQL string remains
                    sp = chunk.split("%(", 1)
                    outOp += sp[0]  # concat the part up to the %
                    if len(sp) > 1:
                        try:
                            s, chunk = sp[1].split(")s", 1)  # find the ')s'
                        except ValueError:
                            raise ProgrammingError(
                                'Pyformat SQL has incorrect format near "%s"' % chunk
                            )
                        outparams.append(s)
                        outOp += "?"  # put in the Qmark
                    else:
                        chunk = None
            else:  # proper '%s' format
                sp = chunk.split("%s")  # make each %s
                outOp += "?".join(sp)  # into ?
        inQuotes = not inQuotes  # every other chunk is a quoted string
    return outOp, outparams

# === NexusCore/openenv\Lib\site-packages\litellm\llms\openai\chat\gpt_transformation.py ===
"""
Support for gpt model family 
"""

from typing import (
    TYPE_CHECKING,
    Any,
    AsyncIterator,
    Coroutine,
    Iterator,
    List,
    Literal,
    Optional,
    Union,
    cast,
    overload,
)

import httpx

import litellm
from litellm.litellm_core_utils.llm_response_utils.convert_dict_to_response import (
    _extract_reasoning_content,
    _handle_invalid_parallel_tool_calls,
    _should_convert_tool_call_to_json_mode,
)
from litellm.litellm_core_utils.prompt_templates.common_utils import get_tool_call_names
from litellm.litellm_core_utils.prompt_templates.image_handling import (
    async_convert_url_to_base64,
    convert_url_to_base64,
)
from litellm.llms.base_llm.base_model_iterator import BaseModelResponseIterator
from litellm.llms.base_llm.base_utils import BaseLLMModelInfo
from litellm.llms.base_llm.chat.transformation import BaseConfig, BaseLLMException
from litellm.secret_managers.main import get_secret_str
from litellm.types.llms.openai import (
    AllMessageValues,
    ChatCompletionFileObject,
    ChatCompletionFileObjectFile,
    ChatCompletionImageObject,
    ChatCompletionImageUrlObject,
    OpenAIChatCompletionChoices,
    OpenAIMessageContentListBlock,
)
from litellm.types.utils import (
    ChatCompletionMessageToolCall,
    Choices,
    Function,
    Message,
    ModelResponse,
    ModelResponseStream,
)
from litellm.utils import convert_to_model_response_object

from ..common_utils import OpenAIError

if TYPE_CHECKING:
    from litellm.litellm_core_utils.litellm_logging import Logging as _LiteLLMLoggingObj

    LiteLLMLoggingObj = _LiteLLMLoggingObj
else:
    LiteLLMLoggingObj = Any


class OpenAIGPTConfig(BaseLLMModelInfo, BaseConfig):
    """
    Reference: https://platform.openai.com/docs/api-reference/chat/create

    The class `OpenAIConfig` provides configuration for the OpenAI's Chat API interface. Below are the parameters:

    - `frequency_penalty` (number or null): Defaults to 0. Allows a value between -2.0 and 2.0. Positive values penalize new tokens based on their existing frequency in the text so far, thereby minimizing repetition.

    - `function_call` (string or object): This optional parameter controls how the model calls functions.

    - `functions` (array): An optional parameter. It is a list of functions for which the model may generate JSON inputs.

    - `logit_bias` (map): This optional parameter modifies the likelihood of specified tokens appearing in the completion.

    - `max_tokens` (integer or null): This optional parameter helps to set the maximum number of tokens to generate in the chat completion.

    - `n` (integer or null): This optional parameter helps to set how many chat completion choices to generate for each input message.

    - `presence_penalty` (number or null): Defaults to 0. It penalizes new tokens based on if they appear in the text so far, hence increasing the model's likelihood to talk about new topics.

    - `stop` (string / array / null): Specifies up to 4 sequences where the API will stop generating further tokens.

    - `temperature` (number or null): Defines the sampling temperature to use, varying between 0 and 2.

    - `top_p` (number or null): An alternative to sampling with temperature, used for nucleus sampling.
    """

    # Add a class variable to track if this is the base class
    _is_base_class = True

    frequency_penalty: Optional[int] = None
    function_call: Optional[Union[str, dict]] = None
    functions: Optional[list] = None
    logit_bias: Optional[dict] = None
    max_tokens: Optional[int] = None
    n: Optional[int] = None
    presence_penalty: Optional[int] = None
    stop: Optional[Union[str, list]] = None
    temperature: Optional[int] = None
    top_p: Optional[int] = None
    response_format: Optional[dict] = None

    def __init__(
        self,
        frequency_penalty: Optional[int] = None,
        function_call: Optional[Union[str, dict]] = None,
        functions: Optional[list] = None,
        logit_bias: Optional[dict] = None,
        max_tokens: Optional[int] = None,
        n: Optional[int] = None,
        presence_penalty: Optional[int] = None,
        stop: Optional[Union[str, list]] = None,
        temperature: Optional[int] = None,
        top_p: Optional[int] = None,
        response_format: Optional[dict] = None,
    ) -> None:
        locals_ = locals().copy()
        for key, value in locals_.items():
            if key != "self" and value is not None:
                setattr(self.__class__, key, value)

        self.__class__._is_base_class = False

    @classmethod
    def get_config(cls):
        return super().get_config()

    def get_supported_openai_params(self, model: str) -> list:
        base_params = [
            "frequency_penalty",
            "logit_bias",
            "logprobs",
            "top_logprobs",
            "max_tokens",
            "max_completion_tokens",
            "modalities",
            "prediction",
            "n",
            "presence_penalty",
            "seed",
            "stop",
            "stream",
            "stream_options",
            "temperature",
            "top_p",
            "tools",
            "tool_choice",
            "function_call",
            "functions",
            "max_retries",
            "extra_headers",
            "parallel_tool_calls",
            "audio",
            "web_search_options",
        ]  # works across all models

        model_specific_params = []
        if (
            model != "gpt-3.5-turbo-16k" and model != "gpt-4"
        ):  # gpt-4 does not support 'response_format'
            model_specific_params.append("response_format")

        if (
            model in litellm.open_ai_chat_completion_models
        ) or model in litellm.open_ai_text_completion_models:
            model_specific_params.append(
                "user"
            )  # user is not a param supported by all openai-compatible endpoints - e.g. azure ai
        return base_params + model_specific_params

    def _map_openai_params(
        self,
        non_default_params: dict,
        optional_params: dict,
        model: str,
        drop_params: bool,
    ) -> dict:
        """
        If any supported_openai_params are in non_default_params, add them to optional_params, so they are use in API call

        Args:
            non_default_params (dict): Non-default parameters to filter.
            optional_params (dict): Optional parameters to update.
            model (str): Model name for parameter support check.

        Returns:
            dict: Updated optional_params with supported non-default parameters.
        """
        supported_openai_params = self.get_supported_openai_params(model)
        for param, value in non_default_params.items():
            if param in supported_openai_params:
                optional_params[param] = value
        return optional_params

    def map_openai_params(
        self,
        non_default_params: dict,
        optional_params: dict,
        model: str,
        drop_params: bool,
    ) -> dict:
        return self._map_openai_params(
            non_default_params=non_default_params,
            optional_params=optional_params,
            model=model,
            drop_params=drop_params,
        )

    def contains_pdf_url(self, content_item: ChatCompletionFileObjectFile) -> bool:
        potential_pdf_url_starts = ["https://", "http://", "www."]
        file_id = content_item.get("file_id")
        if file_id and any(
            file_id.startswith(start) for start in potential_pdf_url_starts
        ):
            return True
        return False

    def _handle_pdf_url(
        self, content_item: ChatCompletionFileObjectFile
    ) -> ChatCompletionFileObjectFile:
        content_copy = content_item.copy()
        file_id = content_copy.get("file_id")
        if file_id is not None:
            base64_data = convert_url_to_base64(file_id)
            content_copy["file_data"] = base64_data
            content_copy["filename"] = "my_file.pdf"
            content_copy.pop("file_id")
        return content_copy

    async def _async_handle_pdf_url(
        self, content_item: ChatCompletionFileObjectFile
    ) -> ChatCompletionFileObjectFile:
        file_id = content_item.get("file_id")
        if file_id is not None:  # check for file id being url done in _handle_pdf_url
            base64_data = await async_convert_url_to_base64(file_id)
            content_item["file_data"] = base64_data
            content_item["filename"] = "my_file.pdf"
            content_item.pop("file_id")
        return content_item

    def _common_file_data_check(
        self, content_item: ChatCompletionFileObjectFile
    ) -> ChatCompletionFileObjectFile:
        file_data = content_item.get("file_data")
        filename = content_item.get("filename")
        if file_data is not None and filename is None:
            content_item["filename"] = "my_file.pdf"
        return content_item

    def _apply_common_transform_content_item(
        self,
        content_item: OpenAIMessageContentListBlock,
    ) -> OpenAIMessageContentListBlock:
        litellm_specific_params = {"format"}
        if content_item.get("type") == "image_url":
            content_item = cast(ChatCompletionImageObject, content_item)
            if isinstance(content_item["image_url"], str):
                content_item["image_url"] = {
                    "url": content_item["image_url"],
                }
            elif isinstance(content_item["image_url"], dict):
                new_image_url_obj = ChatCompletionImageUrlObject(
                    **{  # type: ignore
                        k: v
                        for k, v in content_item["image_url"].items()
                        if k not in litellm_specific_params
                    }
                )
                content_item["image_url"] = new_image_url_obj
        elif content_item.get("type") == "file":
            content_item = cast(ChatCompletionFileObject, content_item)
            file_obj = content_item["file"]
            new_file_obj = ChatCompletionFileObjectFile(
                **{  # type: ignore
                    k: v
                    for k, v in file_obj.items()
                    if k not in litellm_specific_params
                }
            )
            content_item["file"] = new_file_obj

        return content_item

    def _transform_content_item(
        self,
        content_item: OpenAIMessageContentListBlock,
    ) -> OpenAIMessageContentListBlock:
        content_item = self._apply_common_transform_content_item(content_item)
        content_item_type = content_item.get("type")
        potential_file_obj = content_item.get("file")
        if content_item_type == "file" and potential_file_obj:
            file_obj = cast(ChatCompletionFileObjectFile, potential_file_obj)
            content_item_typed = cast(ChatCompletionFileObject, content_item)
            if self.contains_pdf_url(file_obj):
                file_obj = self._handle_pdf_url(file_obj)
            file_obj = self._common_file_data_check(file_obj)
            content_item_typed["file"] = file_obj
            content_item = content_item_typed
        return content_item

    async def _async_transform_content_item(
        self, content_item: OpenAIMessageContentListBlock, is_async: bool = False
    ) -> OpenAIMessageContentListBlock:
        content_item = self._apply_common_transform_content_item(content_item)
        content_item_type = content_item.get("type")
        potential_file_obj = content_item.get("file")
        if content_item_type == "file" and potential_file_obj:
            file_obj = cast(ChatCompletionFileObjectFile, potential_file_obj)
            content_item_typed = cast(ChatCompletionFileObject, content_item)
            if self.contains_pdf_url(file_obj):
                file_obj = await self._async_handle_pdf_url(file_obj)
            file_obj = self._common_file_data_check(file_obj)
            content_item_typed["file"] = file_obj
            content_item = content_item_typed
        return content_item

    @overload
    def _transform_messages(
        self, messages: List[AllMessageValues], model: str, is_async: Literal[True]
    ) -> Coroutine[Any, Any, List[AllMessageValues]]:
        ...

    @overload
    def _transform_messages(
        self,
        messages: List[AllMessageValues],
        model: str,
        is_async: Literal[False] = False,
    ) -> List[AllMessageValues]:
        ...

    def _transform_messages(
        self, messages: List[AllMessageValues], model: str, is_async: bool = False
    ) -> Union[List[AllMessageValues], Coroutine[Any, Any, List[AllMessageValues]]]:
        """OpenAI no longer supports image_url as a string, so we need to convert it to a dict"""

        async def _async_transform():
            for message in messages:
                message_content = message.get("content")
                message_role = message.get("role")
                if (
                    message_role == "user"
                    and message_content
                    and isinstance(message_content, list)
                ):
                    message_content_types = cast(
                        List[OpenAIMessageContentListBlock], message_content
                    )
                    for i, content_item in enumerate(message_content_types):
                        message_content_types[
                            i
                        ] = await self._async_transform_content_item(
                            cast(OpenAIMessageContentListBlock, content_item),
                        )
            return messages

        if is_async:
            return _async_transform()
        else:
            for message in messages:
                message_content = message.get("content")
                message_role = message.get("role")
                if (
                    message_role == "user"
                    and message_content
                    and isinstance(message_content, list)
                ):
                    message_content_types = cast(
                        List[OpenAIMessageContentListBlock], message_content
                    )
                    for i, content_item in enumerate(message_content):
                        message_content_types[i] = self._transform_content_item(
                            cast(OpenAIMessageContentListBlock, content_item)
                        )
            return messages

    def transform_request(
        self,
        model: str,
        messages: List[AllMessageValues],
        optional_params: dict,
        litellm_params: dict,
        headers: dict,
    ) -> dict:
        """
        Transform the overall request to be sent to the API.

        Returns:
            dict: The transformed request. Sent as the body of the API call.
        """
        messages = self._transform_messages(messages=messages, model=model)
        return {
            "model": model,
            "messages": messages,
            **optional_params,
        }

    async def async_transform_request(
        self,
        model: str,
        messages: List[AllMessageValues],
        optional_params: dict,
        litellm_params: dict,
        headers: dict,
    ) -> dict:
        transformed_messages = await self._transform_messages(
            messages=messages, model=model, is_async=True
        )

        if self.__class__._is_base_class:
            return {
                "model": model,
                "messages": transformed_messages,
                **optional_params,
            }
        else:
            ## allow for any object specific behaviour to be handled
            return self.transform_request(
                model, messages, optional_params, litellm_params, headers
            )

    def _passed_in_tools(self, optional_params: dict) -> bool:
        return optional_params.get("tools", None) is not None

    def _check_and_fix_if_content_is_tool_call(
        self, content: str, optional_params: dict
    ) -> Optional[ChatCompletionMessageToolCall]:
        """
        Check if the content is a tool call
        """
        import json

        if not self._passed_in_tools(optional_params):
            return None
        tool_call_names = get_tool_call_names(optional_params.get("tools", []))
        try:
            json_content = json.loads(content)
            if (
                json_content.get("type") == "function"
                and json_content.get("name") in tool_call_names
            ):
                return ChatCompletionMessageToolCall(
                    function=Function(
                        name=json_content.get("name"),
                        arguments=json_content.get("arguments"),
                    )
                )
        except Exception:
            return None

        return None

    def _get_finish_reason(self, message: Message, received_finish_reason: str) -> str:
        if message.tool_calls is not None:
            return "tool_calls"
        else:
            return received_finish_reason

    def _transform_choices(
        self,
        choices: List[OpenAIChatCompletionChoices],
        json_mode: Optional[bool] = None,
        optional_params: Optional[dict] = None,
    ) -> List[Choices]:
        transformed_choices = []

        for choice in choices:
            ## HANDLE JSON MODE - anthropic returns single function call]
            tool_calls = choice["message"].get("tool_calls", None)
            new_tool_calls: Optional[List[ChatCompletionMessageToolCall]] = None
            message_content = choice["message"].get("content", None)
            if tool_calls is not None:
                _openai_tool_calls = []
                for _tc in tool_calls:
                    _openai_tc = ChatCompletionMessageToolCall(**_tc)  # type: ignore
                    _openai_tool_calls.append(_openai_tc)
                fixed_tool_calls = _handle_invalid_parallel_tool_calls(
                    _openai_tool_calls
                )

                if fixed_tool_calls is not None:
                    new_tool_calls = fixed_tool_calls
            elif (
                optional_params is not None
                and message_content
                and isinstance(message_content, str)
            ):
                new_tool_call = self._check_and_fix_if_content_is_tool_call(
                    message_content, optional_params
                )
                if new_tool_call is not None:
                    choice["message"]["content"] = None  # remove the content
                    new_tool_calls = [new_tool_call]

            translated_message: Optional[Message] = None
            finish_reason: Optional[str] = None
            if new_tool_calls and _should_convert_tool_call_to_json_mode(
                tool_calls=new_tool_calls,
                convert_tool_call_to_json_mode=json_mode,
            ):
                # to support response_format on claude models
                json_mode_content_str: Optional[str] = (
                    str(new_tool_calls[0]["function"].get("arguments", "")) or None
                )
                if json_mode_content_str is not None:
                    translated_message = Message(content=json_mode_content_str)
                    finish_reason = "stop"

            if translated_message is None:
                ## get the reasoning content
                (
                    reasoning_content,
                    content_str,
                ) = _extract_reasoning_content(cast(dict, choice["message"]))

                translated_message = Message(
                    role="assistant",
                    content=content_str,
                    reasoning_content=reasoning_content,
                    thinking_blocks=None,
                    tool_calls=new_tool_calls,
                )

            if finish_reason is None:
                finish_reason = choice["finish_reason"]

            translated_choice = Choices(
                finish_reason=finish_reason,
                index=choice["index"],
                message=translated_message,
                logprobs=None,
                enhancements=None,
            )

            translated_choice.finish_reason = self._get_finish_reason(
                translated_message, choice["finish_reason"]
            )
            transformed_choices.append(translated_choice)

        return transformed_choices

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
        """
        Transform the response from the API.

        Returns:
            dict: The transformed response.
        """

        ## LOGGING
        logging_obj.post_call(
            input=messages,
            api_key=api_key,
            original_response=raw_response.text,
            additional_args={"complete_input_dict": request_data},
        )

        ## RESPONSE OBJECT
        try:
            completion_response = raw_response.json()
        except Exception as e:
            response_headers = getattr(raw_response, "headers", None)
            raise OpenAIError(
                message="Unable to get json response - {}, Original Response: {}".format(
                    str(e), raw_response.text
                ),
                status_code=raw_response.status_code,
                headers=response_headers,
            )
        raw_response_headers = dict(raw_response.headers)
        final_response_obj = convert_to_model_response_object(
            response_object=completion_response,
            model_response_object=model_response,
            hidden_params={"headers": raw_response_headers},
            _response_headers=raw_response_headers,
        )

        return cast(ModelResponse, final_response_obj)

    def get_error_class(
        self, error_message: str, status_code: int, headers: Union[dict, httpx.Headers]
    ) -> BaseLLMException:
        return OpenAIError(
            status_code=status_code,
            message=error_message,
            headers=cast(httpx.Headers, headers),
        )

    def get_complete_url(
        self,
        api_base: Optional[str],
        api_key: Optional[str],
        model: str,
        optional_params: dict,
        litellm_params: dict,
        stream: Optional[bool] = None,
    ) -> str:
        """
        Get the complete URL for the API call.

        Returns:
            str: The complete URL for the API call.
        """
        if api_base is None:
            api_base = "https://api.openai.com"
        endpoint = "chat/completions"

        # Remove trailing slash from api_base if present
        api_base = api_base.rstrip("/")

        # Check if endpoint is already in the api_base
        if endpoint in api_base:
            return api_base

        return f"{api_base}/{endpoint}"

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
        if api_key is not None:
            headers["Authorization"] = f"Bearer {api_key}"

        # Ensure Content-Type is set to application/json
        if "content-type" not in headers and "Content-Type" not in headers:
            headers["Content-Type"] = "application/json"

        return headers

    def get_models(
        self, api_key: Optional[str] = None, api_base: Optional[str] = None
    ) -> List[str]:
        """
        Calls OpenAI's `/v1/models` endpoint and returns the list of models.
        """

        if api_base is None:
            api_base = "https://api.openai.com"
        if api_key is None:
            api_key = get_secret_str("OPENAI_API_KEY")

        response = litellm.module_level_client.get(
            url=f"{api_base}/v1/models",
            headers={"Authorization": f"Bearer {api_key}"},
        )

        if response.status_code != 200:
            raise Exception(f"Failed to get models: {response.text}")

        models = response.json()["data"]
        return [model["id"] for model in models]

    @staticmethod
    def get_api_key(api_key: Optional[str] = None) -> Optional[str]:
        return (
            api_key
            or litellm.api_key
            or litellm.openai_key
            or get_secret_str("OPENAI_API_KEY")
        )

    @staticmethod
    def get_api_base(api_base: Optional[str] = None) -> Optional[str]:
        return (
            api_base
            or litellm.api_base
            or get_secret_str("OPENAI_BASE_URL")
            or get_secret_str("OPENAI_API_BASE")
            or "https://api.openai.com/v1"
        )

    @staticmethod
    def get_base_model(model: Optional[str] = None) -> Optional[str]:
        return model

    def get_model_response_iterator(
        self,
        streaming_response: Union[Iterator[str], AsyncIterator[str], ModelResponse],
        sync_stream: bool,
        json_mode: Optional[bool] = False,
    ) -> Any:
        return OpenAIChatCompletionStreamingHandler(
            streaming_response=streaming_response,
            sync_stream=sync_stream,
            json_mode=json_mode,
        )


class OpenAIChatCompletionStreamingHandler(BaseModelResponseIterator):
    def chunk_parser(self, chunk: dict) -> ModelResponseStream:
        try:
            return ModelResponseStream(
                id=chunk["id"],
                object="chat.completion.chunk",
                created=chunk["created"],
                model=chunk["model"],
                choices=chunk["choices"],
            )
        except Exception as e:
            raise e

# === NexusCore/myenv\Lib\site-packages\pip\_vendor\requests\adapters.py ===
"""
requests.adapters
~~~~~~~~~~~~~~~~~

This module contains the transport adapters that Requests uses to define
and maintain connections.
"""

import os.path
import socket  # noqa: F401
import typing
import warnings

from pip._vendor.urllib3.exceptions import ClosedPoolError, ConnectTimeoutError
from pip._vendor.urllib3.exceptions import HTTPError as _HTTPError
from pip._vendor.urllib3.exceptions import InvalidHeader as _InvalidHeader
from pip._vendor.urllib3.exceptions import (
    LocationValueError,
    MaxRetryError,
    NewConnectionError,
    ProtocolError,
)
from pip._vendor.urllib3.exceptions import ProxyError as _ProxyError
from pip._vendor.urllib3.exceptions import ReadTimeoutError, ResponseError
from pip._vendor.urllib3.exceptions import SSLError as _SSLError
from pip._vendor.urllib3.poolmanager import PoolManager, proxy_from_url
from pip._vendor.urllib3.util import Timeout as TimeoutSauce
from pip._vendor.urllib3.util import parse_url
from pip._vendor.urllib3.util.retry import Retry
from pip._vendor.urllib3.util.ssl_ import create_urllib3_context

from .auth import _basic_auth_str
from .compat import basestring, urlparse
from .cookies import extract_cookies_to_jar
from .exceptions import (
    ConnectionError,
    ConnectTimeout,
    InvalidHeader,
    InvalidProxyURL,
    InvalidSchema,
    InvalidURL,
    ProxyError,
    ReadTimeout,
    RetryError,
    SSLError,
)
from .models import Response
from .structures import CaseInsensitiveDict
from .utils import (
    DEFAULT_CA_BUNDLE_PATH,
    extract_zipped_paths,
    get_auth_from_url,
    get_encoding_from_headers,
    prepend_scheme_if_needed,
    select_proxy,
    urldefragauth,
)

try:
    from pip._vendor.urllib3.contrib.socks import SOCKSProxyManager
except ImportError:

    def SOCKSProxyManager(*args, **kwargs):
        raise InvalidSchema("Missing dependencies for SOCKS support.")


if typing.TYPE_CHECKING:
    from .models import PreparedRequest


DEFAULT_POOLBLOCK = False
DEFAULT_POOLSIZE = 10
DEFAULT_RETRIES = 0
DEFAULT_POOL_TIMEOUT = None


try:
    import ssl  # noqa: F401

    _preloaded_ssl_context = create_urllib3_context()
    _preloaded_ssl_context.load_verify_locations(
        extract_zipped_paths(DEFAULT_CA_BUNDLE_PATH)
    )
except ImportError:
    # Bypass default SSLContext creation when Python
    # interpreter isn't built with the ssl module.
    _preloaded_ssl_context = None


def _urllib3_request_context(
    request: "PreparedRequest",
    verify: "bool | str | None",
    client_cert: "typing.Tuple[str, str] | str | None",
    poolmanager: "PoolManager",
) -> "(typing.Dict[str, typing.Any], typing.Dict[str, typing.Any])":
    host_params = {}
    pool_kwargs = {}
    parsed_request_url = urlparse(request.url)
    scheme = parsed_request_url.scheme.lower()
    port = parsed_request_url.port

    # Determine if we have and should use our default SSLContext
    # to optimize performance on standard requests.
    poolmanager_kwargs = getattr(poolmanager, "connection_pool_kw", {})
    has_poolmanager_ssl_context = poolmanager_kwargs.get("ssl_context")
    should_use_default_ssl_context = (
        _preloaded_ssl_context is not None and not has_poolmanager_ssl_context
    )

    cert_reqs = "CERT_REQUIRED"
    if verify is False:
        cert_reqs = "CERT_NONE"
    elif verify is True and should_use_default_ssl_context:
        pool_kwargs["ssl_context"] = _preloaded_ssl_context
    elif isinstance(verify, str):
        if not os.path.isdir(verify):
            pool_kwargs["ca_certs"] = verify
        else:
            pool_kwargs["ca_cert_dir"] = verify
    pool_kwargs["cert_reqs"] = cert_reqs
    if client_cert is not None:
        if isinstance(client_cert, tuple) and len(client_cert) == 2:
            pool_kwargs["cert_file"] = client_cert[0]
            pool_kwargs["key_file"] = client_cert[1]
        else:
            # According to our docs, we allow users to specify just the client
            # cert path
            pool_kwargs["cert_file"] = client_cert
    host_params = {
        "scheme": scheme,
        "host": parsed_request_url.hostname,
        "port": port,
    }
    return host_params, pool_kwargs


class BaseAdapter:
    """The Base Transport Adapter"""

    def __init__(self):
        super().__init__()

    def send(
        self, request, stream=False, timeout=None, verify=True, cert=None, proxies=None
    ):
        """Sends PreparedRequest object. Returns Response object.

        :param request: The :class:`PreparedRequest <PreparedRequest>` being sent.
        :param stream: (optional) Whether to stream the request content.
        :param timeout: (optional) How long to wait for the server to send
            data before giving up, as a float, or a :ref:`(connect timeout,
            read timeout) <timeouts>` tuple.
        :type timeout: float or tuple
        :param verify: (optional) Either a boolean, in which case it controls whether we verify
            the server's TLS certificate, or a string, in which case it must be a path
            to a CA bundle to use
        :param cert: (optional) Any user-provided SSL certificate to be trusted.
        :param proxies: (optional) The proxies dictionary to apply to the request.
        """
        raise NotImplementedError

    def close(self):
        """Cleans up adapter specific items."""
        raise NotImplementedError


class HTTPAdapter(BaseAdapter):
    """The built-in HTTP Adapter for urllib3.

    Provides a general-case interface for Requests sessions to contact HTTP and
    HTTPS urls by implementing the Transport Adapter interface. This class will
    usually be created by the :class:`Session <Session>` class under the
    covers.

    :param pool_connections: The number of urllib3 connection pools to cache.
    :param pool_maxsize: The maximum number of connections to save in the pool.
    :param max_retries: The maximum number of retries each connection
        should attempt. Note, this applies only to failed DNS lookups, socket
        connections and connection timeouts, never to requests where data has
        made it to the server. By default, Requests does not retry failed
        connections. If you need granular control over the conditions under
        which we retry a request, import urllib3's ``Retry`` class and pass
        that instead.
    :param pool_block: Whether the connection pool should block for connections.

    Usage::

      >>> import requests
      >>> s = requests.Session()
      >>> a = requests.adapters.HTTPAdapter(max_retries=3)
      >>> s.mount('http://', a)
    """

    __attrs__ = [
        "max_retries",
        "config",
        "_pool_connections",
        "_pool_maxsize",
        "_pool_block",
    ]

    def __init__(
        self,
        pool_connections=DEFAULT_POOLSIZE,
        pool_maxsize=DEFAULT_POOLSIZE,
        max_retries=DEFAULT_RETRIES,
        pool_block=DEFAULT_POOLBLOCK,
    ):
        if max_retries == DEFAULT_RETRIES:
            self.max_retries = Retry(0, read=False)
        else:
            self.max_retries = Retry.from_int(max_retries)
        self.config = {}
        self.proxy_manager = {}

        super().__init__()

        self._pool_connections = pool_connections
        self._pool_maxsize = pool_maxsize
        self._pool_block = pool_block

        self.init_poolmanager(pool_connections, pool_maxsize, block=pool_block)

    def __getstate__(self):
        return {attr: getattr(self, attr, None) for attr in self.__attrs__}

    def __setstate__(self, state):
        # Can't handle by adding 'proxy_manager' to self.__attrs__ because
        # self.poolmanager uses a lambda function, which isn't pickleable.
        self.proxy_manager = {}
        self.config = {}

        for attr, value in state.items():
            setattr(self, attr, value)

        self.init_poolmanager(
            self._pool_connections, self._pool_maxsize, block=self._pool_block
        )

    def init_poolmanager(
        self, connections, maxsize, block=DEFAULT_POOLBLOCK, **pool_kwargs
    ):
        """Initializes a urllib3 PoolManager.

        This method should not be called from user code, and is only
        exposed for use when subclassing the
        :class:`HTTPAdapter <requests.adapters.HTTPAdapter>`.

        :param connections: The number of urllib3 connection pools to cache.
        :param maxsize: The maximum number of connections to save in the pool.
        :param block: Block when no free connections are available.
        :param pool_kwargs: Extra keyword arguments used to initialize the Pool Manager.
        """
        # save these values for pickling
        self._pool_connections = connections
        self._pool_maxsize = maxsize
        self._pool_block = block

        self.poolmanager = PoolManager(
            num_pools=connections,
            maxsize=maxsize,
            block=block,
            **pool_kwargs,
        )

    def proxy_manager_for(self, proxy, **proxy_kwargs):
        """Return urllib3 ProxyManager for the given proxy.

        This method should not be called from user code, and is only
        exposed for use when subclassing the
        :class:`HTTPAdapter <requests.adapters.HTTPAdapter>`.

        :param proxy: The proxy to return a urllib3 ProxyManager for.
        :param proxy_kwargs: Extra keyword arguments used to configure the Proxy Manager.
        :returns: ProxyManager
        :rtype: urllib3.ProxyManager
        """
        if proxy in self.proxy_manager:
            manager = self.proxy_manager[proxy]
        elif proxy.lower().startswith("socks"):
            username, password = get_auth_from_url(proxy)
            manager = self.proxy_manager[proxy] = SOCKSProxyManager(
                proxy,
                username=username,
                password=password,
                num_pools=self._pool_connections,
                maxsize=self._pool_maxsize,
                block=self._pool_block,
                **proxy_kwargs,
            )
        else:
            proxy_headers = self.proxy_headers(proxy)
            manager = self.proxy_manager[proxy] = proxy_from_url(
                proxy,
                proxy_headers=proxy_headers,
                num_pools=self._pool_connections,
                maxsize=self._pool_maxsize,
                block=self._pool_block,
                **proxy_kwargs,
            )

        return manager

    def cert_verify(self, conn, url, verify, cert):
        """Verify a SSL certificate. This method should not be called from user
        code, and is only exposed for use when subclassing the
        :class:`HTTPAdapter <requests.adapters.HTTPAdapter>`.

        :param conn: The urllib3 connection object associated with the cert.
        :param url: The requested URL.
        :param verify: Either a boolean, in which case it controls whether we verify
            the server's TLS certificate, or a string, in which case it must be a path
            to a CA bundle to use
        :param cert: The SSL certificate to verify.
        """
        if url.lower().startswith("https") and verify:
            conn.cert_reqs = "CERT_REQUIRED"

            # Only load the CA certificates if 'verify' is a string indicating the CA bundle to use.
            # Otherwise, if verify is a boolean, we don't load anything since
            # the connection will be using a context with the default certificates already loaded,
            # and this avoids a call to the slow load_verify_locations()
            if verify is not True:
                # `verify` must be a str with a path then
                cert_loc = verify

                if not os.path.exists(cert_loc):
                    raise OSError(
                        f"Could not find a suitable TLS CA certificate bundle, "
                        f"invalid path: {cert_loc}"
                    )

                if not os.path.isdir(cert_loc):
                    conn.ca_certs = cert_loc
                else:
                    conn.ca_cert_dir = cert_loc
        else:
            conn.cert_reqs = "CERT_NONE"
            conn.ca_certs = None
            conn.ca_cert_dir = None

        if cert:
            if not isinstance(cert, basestring):
                conn.cert_file = cert[0]
                conn.key_file = cert[1]
            else:
                conn.cert_file = cert
                conn.key_file = None
            if conn.cert_file and not os.path.exists(conn.cert_file):
                raise OSError(
                    f"Could not find the TLS certificate file, "
                    f"invalid path: {conn.cert_file}"
                )
            if conn.key_file and not os.path.exists(conn.key_file):
                raise OSError(
                    f"Could not find the TLS key file, invalid path: {conn.key_file}"
                )

    def build_response(self, req, resp):
        """Builds a :class:`Response <requests.Response>` object from a urllib3
        response. This should not be called from user code, and is only exposed
        for use when subclassing the
        :class:`HTTPAdapter <requests.adapters.HTTPAdapter>`

        :param req: The :class:`PreparedRequest <PreparedRequest>` used to generate the response.
        :param resp: The urllib3 response object.
        :rtype: requests.Response
        """
        response = Response()

        # Fallback to None if there's no status_code, for whatever reason.
        response.status_code = getattr(resp, "status", None)

        # Make headers case-insensitive.
        response.headers = CaseInsensitiveDict(getattr(resp, "headers", {}))

        # Set encoding.
        response.encoding = get_encoding_from_headers(response.headers)
        response.raw = resp
        response.reason = response.raw.reason

        if isinstance(req.url, bytes):
            response.url = req.url.decode("utf-8")
        else:
            response.url = req.url

        # Add new cookies from the server.
        extract_cookies_to_jar(response.cookies, req, resp)

        # Give the Response some context.
        response.request = req
        response.connection = self

        return response

    def build_connection_pool_key_attributes(self, request, verify, cert=None):
        """Build the PoolKey attributes used by urllib3 to return a connection.

        This looks at the PreparedRequest, the user-specified verify value,
        and the value of the cert parameter to determine what PoolKey values
        to use to select a connection from a given urllib3 Connection Pool.

        The SSL related pool key arguments are not consistently set. As of
        this writing, use the following to determine what keys may be in that
        dictionary:

        * If ``verify`` is ``True``, ``"ssl_context"`` will be set and will be the
          default Requests SSL Context
        * If ``verify`` is ``False``, ``"ssl_context"`` will not be set but
          ``"cert_reqs"`` will be set
        * If ``verify`` is a string, (i.e., it is a user-specified trust bundle)
          ``"ca_certs"`` will be set if the string is not a directory recognized
          by :py:func:`os.path.isdir`, otherwise ``"ca_certs_dir"`` will be
          set.
        * If ``"cert"`` is specified, ``"cert_file"`` will always be set. If
          ``"cert"`` is a tuple with a second item, ``"key_file"`` will also
          be present

        To override these settings, one may subclass this class, call this
        method and use the above logic to change parameters as desired. For
        example, if one wishes to use a custom :py:class:`ssl.SSLContext` one
        must both set ``"ssl_context"`` and based on what else they require,
        alter the other keys to ensure the desired behaviour.

        :param request:
            The PreparedReqest being sent over the connection.
        :type request:
            :class:`~requests.models.PreparedRequest`
        :param verify:
            Either a boolean, in which case it controls whether
            we verify the server's TLS certificate, or a string, in which case it
            must be a path to a CA bundle to use.
        :param cert:
            (optional) Any user-provided SSL certificate for client
            authentication (a.k.a., mTLS). This may be a string (i.e., just
            the path to a file which holds both certificate and key) or a
            tuple of length 2 with the certificate file path and key file
            path.
        :returns:
            A tuple of two dictionaries. The first is the "host parameters"
            portion of the Pool Key including scheme, hostname, and port. The
            second is a dictionary of SSLContext related parameters.
        """
        return _urllib3_request_context(request, verify, cert, self.poolmanager)

    def get_connection_with_tls_context(self, request, verify, proxies=None, cert=None):
        """Returns a urllib3 connection for the given request and TLS settings.
        This should not be called from user code, and is only exposed for use
        when subclassing the :class:`HTTPAdapter <requests.adapters.HTTPAdapter>`.

        :param request:
            The :class:`PreparedRequest <PreparedRequest>` object to be sent
            over the connection.
        :param verify:
            Either a boolean, in which case it controls whether we verify the
            server's TLS certificate, or a string, in which case it must be a
            path to a CA bundle to use.
        :param proxies:
            (optional) The proxies dictionary to apply to the request.
        :param cert:
            (optional) Any user-provided SSL certificate to be used for client
            authentication (a.k.a., mTLS).
        :rtype:
            urllib3.ConnectionPool
        """
        proxy = select_proxy(request.url, proxies)
        try:
            host_params, pool_kwargs = self.build_connection_pool_key_attributes(
                request,
                verify,
                cert,
            )
        except ValueError as e:
            raise InvalidURL(e, request=request)
        if proxy:
            proxy = prepend_scheme_if_needed(proxy, "http")
            proxy_url = parse_url(proxy)
            if not proxy_url.host:
                raise InvalidProxyURL(
                    "Please check proxy URL. It is malformed "
                    "and could be missing the host."
                )
            proxy_manager = self.proxy_manager_for(proxy)
            conn = proxy_manager.connection_from_host(
                **host_params, pool_kwargs=pool_kwargs
            )
        else:
            # Only scheme should be lower case
            conn = self.poolmanager.connection_from_host(
                **host_params, pool_kwargs=pool_kwargs
            )

        return conn

    def get_connection(self, url, proxies=None):
        """DEPRECATED: Users should move to `get_connection_with_tls_context`
        for all subclasses of HTTPAdapter using Requests>=2.32.2.

        Returns a urllib3 connection for the given URL. This should not be
        called from user code, and is only exposed for use when subclassing the
        :class:`HTTPAdapter <requests.adapters.HTTPAdapter>`.

        :param url: The URL to connect to.
        :param proxies: (optional) A Requests-style dictionary of proxies used on this request.
        :rtype: urllib3.ConnectionPool
        """
        warnings.warn(
            (
                "`get_connection` has been deprecated in favor of "
                "`get_connection_with_tls_context`. Custom HTTPAdapter subclasses "
                "will need to migrate for Requests>=2.32.2. Please see "
                "https://github.com/psf/requests/pull/6710 for more details."
            ),
            DeprecationWarning,
        )
        proxy = select_proxy(url, proxies)

        if proxy:
            proxy = prepend_scheme_if_needed(proxy, "http")
            proxy_url = parse_url(proxy)
            if not proxy_url.host:
                raise InvalidProxyURL(
                    "Please check proxy URL. It is malformed "
                    "and could be missing the host."
                )
            proxy_manager = self.proxy_manager_for(proxy)
            conn = proxy_manager.connection_from_url(url)
        else:
            # Only scheme should be lower case
            parsed = urlparse(url)
            url = parsed.geturl()
            conn = self.poolmanager.connection_from_url(url)

        return conn

    def close(self):
        """Disposes of any internal state.

        Currently, this closes the PoolManager and any active ProxyManager,
        which closes any pooled connections.
        """
        self.poolmanager.clear()
        for proxy in self.proxy_manager.values():
            proxy.clear()

    def request_url(self, request, proxies):
        """Obtain the url to use when making the final request.

        If the message is being sent through a HTTP proxy, the full URL has to
        be used. Otherwise, we should only use the path portion of the URL.

        This should not be called from user code, and is only exposed for use
        when subclassing the
        :class:`HTTPAdapter <requests.adapters.HTTPAdapter>`.

        :param request: The :class:`PreparedRequest <PreparedRequest>` being sent.
        :param proxies: A dictionary of schemes or schemes and hosts to proxy URLs.
        :rtype: str
        """
        proxy = select_proxy(request.url, proxies)
        scheme = urlparse(request.url).scheme

        is_proxied_http_request = proxy and scheme != "https"
        using_socks_proxy = False
        if proxy:
            proxy_scheme = urlparse(proxy).scheme.lower()
            using_socks_proxy = proxy_scheme.startswith("socks")

        url = request.path_url
        if url.startswith("//"):  # Don't confuse urllib3
            url = f"/{url.lstrip('/')}"

        if is_proxied_http_request and not using_socks_proxy:
            url = urldefragauth(request.url)

        return url

    def add_headers(self, request, **kwargs):
        """Add any headers needed by the connection. As of v2.0 this does
        nothing by default, but is left for overriding by users that subclass
        the :class:`HTTPAdapter <requests.adapters.HTTPAdapter>`.

        This should not be called from user code, and is only exposed for use
        when subclassing the
        :class:`HTTPAdapter <requests.adapters.HTTPAdapter>`.

        :param request: The :class:`PreparedRequest <PreparedRequest>` to add headers to.
        :param kwargs: The keyword arguments from the call to send().
        """
        pass

    def proxy_headers(self, proxy):
        """Returns a dictionary of the headers to add to any request sent
        through a proxy. This works with urllib3 magic to ensure that they are
        correctly sent to the proxy, rather than in a tunnelled request if
        CONNECT is being used.

        This should not be called from user code, and is only exposed for use
        when subclassing the
        :class:`HTTPAdapter <requests.adapters.HTTPAdapter>`.

        :param proxy: The url of the proxy being used for this request.
        :rtype: dict
        """
        headers = {}
        username, password = get_auth_from_url(proxy)

        if username:
            headers["Proxy-Authorization"] = _basic_auth_str(username, password)

        return headers

    def send(
        self, request, stream=False, timeout=None, verify=True, cert=None, proxies=None
    ):
        """Sends PreparedRequest object. Returns Response object.

        :param request: The :class:`PreparedRequest <PreparedRequest>` being sent.
        :param stream: (optional) Whether to stream the request content.
        :param timeout: (optional) How long to wait for the server to send
            data before giving up, as a float, or a :ref:`(connect timeout,
            read timeout) <timeouts>` tuple.
        :type timeout: float or tuple or urllib3 Timeout object
        :param verify: (optional) Either a boolean, in which case it controls whether
            we verify the server's TLS certificate, or a string, in which case it
            must be a path to a CA bundle to use
        :param cert: (optional) Any user-provided SSL certificate to be trusted.
        :param proxies: (optional) The proxies dictionary to apply to the request.
        :rtype: requests.Response
        """

        try:
            conn = self.get_connection_with_tls_context(
                request, verify, proxies=proxies, cert=cert
            )
        except LocationValueError as e:
            raise InvalidURL(e, request=request)

        self.cert_verify(conn, request.url, verify, cert)
        url = self.request_url(request, proxies)
        self.add_headers(
            request,
            stream=stream,
            timeout=timeout,
            verify=verify,
            cert=cert,
            proxies=proxies,
        )

        chunked = not (request.body is None or "Content-Length" in request.headers)

        if isinstance(timeout, tuple):
            try:
                connect, read = timeout
                timeout = TimeoutSauce(connect=connect, read=read)
            except ValueError:
                raise ValueError(
                    f"Invalid timeout {timeout}. Pass a (connect, read) timeout tuple, "
                    f"or a single float to set both timeouts to the same value."
                )
        elif isinstance(timeout, TimeoutSauce):
            pass
        else:
            timeout = TimeoutSauce(connect=timeout, read=timeout)

        try:
            resp = conn.urlopen(
                method=request.method,
                url=url,
                body=request.body,
                headers=request.headers,
                redirect=False,
                assert_same_host=False,
                preload_content=False,
                decode_content=False,
                retries=self.max_retries,
                timeout=timeout,
                chunked=chunked,
            )

        except (ProtocolError, OSError) as err:
            raise ConnectionError(err, request=request)

        except MaxRetryError as e:
            if isinstance(e.reason, ConnectTimeoutError):
                # TODO: Remove this in 3.0.0: see #2811
                if not isinstance(e.reason, NewConnectionError):
                    raise ConnectTimeout(e, request=request)

            if isinstance(e.reason, ResponseError):
                raise RetryError(e, request=request)

            if isinstance(e.reason, _ProxyError):
                raise ProxyError(e, request=request)

            if isinstance(e.reason, _SSLError):
                # This branch is for urllib3 v1.22 and later.
                raise SSLError(e, request=request)

            raise ConnectionError(e, request=request)

        except ClosedPoolError as e:
            raise ConnectionError(e, request=request)

        except _ProxyError as e:
            raise ProxyError(e)

        except (_SSLError, _HTTPError) as e:
            if isinstance(e, _SSLError):
                # This branch is for urllib3 versions earlier than v1.22
                raise SSLError(e, request=request)
            elif isinstance(e, ReadTimeoutError):
                raise ReadTimeout(e, request=request)
            elif isinstance(e, _InvalidHeader):
                raise InvalidHeader(e, request=request)
            else:
                raise

        return self.build_response(request, resp)

# === NexusCore/openenv\Lib\site-packages\requests\adapters.py ===
"""
requests.adapters
~~~~~~~~~~~~~~~~~

This module contains the transport adapters that Requests uses to define
and maintain connections.
"""

import os.path
import socket  # noqa: F401
import typing
import warnings

from urllib3.exceptions import ClosedPoolError, ConnectTimeoutError
from urllib3.exceptions import HTTPError as _HTTPError
from urllib3.exceptions import InvalidHeader as _InvalidHeader
from urllib3.exceptions import (
    LocationValueError,
    MaxRetryError,
    NewConnectionError,
    ProtocolError,
)
from urllib3.exceptions import ProxyError as _ProxyError
from urllib3.exceptions import ReadTimeoutError, ResponseError
from urllib3.exceptions import SSLError as _SSLError
from urllib3.poolmanager import PoolManager, proxy_from_url
from urllib3.util import Timeout as TimeoutSauce
from urllib3.util import parse_url
from urllib3.util.retry import Retry
from urllib3.util.ssl_ import create_urllib3_context

from .auth import _basic_auth_str
from .compat import basestring, urlparse
from .cookies import extract_cookies_to_jar
from .exceptions import (
    ConnectionError,
    ConnectTimeout,
    InvalidHeader,
    InvalidProxyURL,
    InvalidSchema,
    InvalidURL,
    ProxyError,
    ReadTimeout,
    RetryError,
    SSLError,
)
from .models import Response
from .structures import CaseInsensitiveDict
from .utils import (
    DEFAULT_CA_BUNDLE_PATH,
    extract_zipped_paths,
    get_auth_from_url,
    get_encoding_from_headers,
    prepend_scheme_if_needed,
    select_proxy,
    urldefragauth,
)

try:
    from urllib3.contrib.socks import SOCKSProxyManager
except ImportError:

    def SOCKSProxyManager(*args, **kwargs):
        raise InvalidSchema("Missing dependencies for SOCKS support.")


if typing.TYPE_CHECKING:
    from .models import PreparedRequest


DEFAULT_POOLBLOCK = False
DEFAULT_POOLSIZE = 10
DEFAULT_RETRIES = 0
DEFAULT_POOL_TIMEOUT = None


try:
    import ssl  # noqa: F401

    _preloaded_ssl_context = create_urllib3_context()
    _preloaded_ssl_context.load_verify_locations(
        extract_zipped_paths(DEFAULT_CA_BUNDLE_PATH)
    )
except ImportError:
    # Bypass default SSLContext creation when Python
    # interpreter isn't built with the ssl module.
    _preloaded_ssl_context = None


def _urllib3_request_context(
    request: "PreparedRequest",
    verify: "bool | str | None",
    client_cert: "typing.Tuple[str, str] | str | None",
    poolmanager: "PoolManager",
) -> "(typing.Dict[str, typing.Any], typing.Dict[str, typing.Any])":
    host_params = {}
    pool_kwargs = {}
    parsed_request_url = urlparse(request.url)
    scheme = parsed_request_url.scheme.lower()
    port = parsed_request_url.port

    # Determine if we have and should use our default SSLContext
    # to optimize performance on standard requests.
    poolmanager_kwargs = getattr(poolmanager, "connection_pool_kw", {})
    has_poolmanager_ssl_context = poolmanager_kwargs.get("ssl_context")
    should_use_default_ssl_context = (
        _preloaded_ssl_context is not None and not has_poolmanager_ssl_context
    )

    cert_reqs = "CERT_REQUIRED"
    if verify is False:
        cert_reqs = "CERT_NONE"
    elif verify is True and should_use_default_ssl_context:
        pool_kwargs["ssl_context"] = _preloaded_ssl_context
    elif isinstance(verify, str):
        if not os.path.isdir(verify):
            pool_kwargs["ca_certs"] = verify
        else:
            pool_kwargs["ca_cert_dir"] = verify
    pool_kwargs["cert_reqs"] = cert_reqs
    if client_cert is not None:
        if isinstance(client_cert, tuple) and len(client_cert) == 2:
            pool_kwargs["cert_file"] = client_cert[0]
            pool_kwargs["key_file"] = client_cert[1]
        else:
            # According to our docs, we allow users to specify just the client
            # cert path
            pool_kwargs["cert_file"] = client_cert
    host_params = {
        "scheme": scheme,
        "host": parsed_request_url.hostname,
        "port": port,
    }
    return host_params, pool_kwargs


class BaseAdapter:
    """The Base Transport Adapter"""

    def __init__(self):
        super().__init__()

    def send(
        self, request, stream=False, timeout=None, verify=True, cert=None, proxies=None
    ):
        """Sends PreparedRequest object. Returns Response object.

        :param request: The :class:`PreparedRequest <PreparedRequest>` being sent.
        :param stream: (optional) Whether to stream the request content.
        :param timeout: (optional) How long to wait for the server to send
            data before giving up, as a float, or a :ref:`(connect timeout,
            read timeout) <timeouts>` tuple.
        :type timeout: float or tuple
        :param verify: (optional) Either a boolean, in which case it controls whether we verify
            the server's TLS certificate, or a string, in which case it must be a path
            to a CA bundle to use
        :param cert: (optional) Any user-provided SSL certificate to be trusted.
        :param proxies: (optional) The proxies dictionary to apply to the request.
        """
        raise NotImplementedError

    def close(self):
        """Cleans up adapter specific items."""
        raise NotImplementedError


class HTTPAdapter(BaseAdapter):
    """The built-in HTTP Adapter for urllib3.

    Provides a general-case interface for Requests sessions to contact HTTP and
    HTTPS urls by implementing the Transport Adapter interface. This class will
    usually be created by the :class:`Session <Session>` class under the
    covers.

    :param pool_connections: The number of urllib3 connection pools to cache.
    :param pool_maxsize: The maximum number of connections to save in the pool.
    :param max_retries: The maximum number of retries each connection
        should attempt. Note, this applies only to failed DNS lookups, socket
        connections and connection timeouts, never to requests where data has
        made it to the server. By default, Requests does not retry failed
        connections. If you need granular control over the conditions under
        which we retry a request, import urllib3's ``Retry`` class and pass
        that instead.
    :param pool_block: Whether the connection pool should block for connections.

    Usage::

      >>> import requests
      >>> s = requests.Session()
      >>> a = requests.adapters.HTTPAdapter(max_retries=3)
      >>> s.mount('http://', a)
    """

    __attrs__ = [
        "max_retries",
        "config",
        "_pool_connections",
        "_pool_maxsize",
        "_pool_block",
    ]

    def __init__(
        self,
        pool_connections=DEFAULT_POOLSIZE,
        pool_maxsize=DEFAULT_POOLSIZE,
        max_retries=DEFAULT_RETRIES,
        pool_block=DEFAULT_POOLBLOCK,
    ):
        if max_retries == DEFAULT_RETRIES:
            self.max_retries = Retry(0, read=False)
        else:
            self.max_retries = Retry.from_int(max_retries)
        self.config = {}
        self.proxy_manager = {}

        super().__init__()

        self._pool_connections = pool_connections
        self._pool_maxsize = pool_maxsize
        self._pool_block = pool_block

        self.init_poolmanager(pool_connections, pool_maxsize, block=pool_block)

    def __getstate__(self):
        return {attr: getattr(self, attr, None) for attr in self.__attrs__}

    def __setstate__(self, state):
        # Can't handle by adding 'proxy_manager' to self.__attrs__ because
        # self.poolmanager uses a lambda function, which isn't pickleable.
        self.proxy_manager = {}
        self.config = {}

        for attr, value in state.items():
            setattr(self, attr, value)

        self.init_poolmanager(
            self._pool_connections, self._pool_maxsize, block=self._pool_block
        )

    def init_poolmanager(
        self, connections, maxsize, block=DEFAULT_POOLBLOCK, **pool_kwargs
    ):
        """Initializes a urllib3 PoolManager.

        This method should not be called from user code, and is only
        exposed for use when subclassing the
        :class:`HTTPAdapter <requests.adapters.HTTPAdapter>`.

        :param connections: The number of urllib3 connection pools to cache.
        :param maxsize: The maximum number of connections to save in the pool.
        :param block: Block when no free connections are available.
        :param pool_kwargs: Extra keyword arguments used to initialize the Pool Manager.
        """
        # save these values for pickling
        self._pool_connections = connections
        self._pool_maxsize = maxsize
        self._pool_block = block

        self.poolmanager = PoolManager(
            num_pools=connections,
            maxsize=maxsize,
            block=block,
            **pool_kwargs,
        )

    def proxy_manager_for(self, proxy, **proxy_kwargs):
        """Return urllib3 ProxyManager for the given proxy.

        This method should not be called from user code, and is only
        exposed for use when subclassing the
        :class:`HTTPAdapter <requests.adapters.HTTPAdapter>`.

        :param proxy: The proxy to return a urllib3 ProxyManager for.
        :param proxy_kwargs: Extra keyword arguments used to configure the Proxy Manager.
        :returns: ProxyManager
        :rtype: urllib3.ProxyManager
        """
        if proxy in self.proxy_manager:
            manager = self.proxy_manager[proxy]
        elif proxy.lower().startswith("socks"):
            username, password = get_auth_from_url(proxy)
            manager = self.proxy_manager[proxy] = SOCKSProxyManager(
                proxy,
                username=username,
                password=password,
                num_pools=self._pool_connections,
                maxsize=self._pool_maxsize,
                block=self._pool_block,
                **proxy_kwargs,
            )
        else:
            proxy_headers = self.proxy_headers(proxy)
            manager = self.proxy_manager[proxy] = proxy_from_url(
                proxy,
                proxy_headers=proxy_headers,
                num_pools=self._pool_connections,
                maxsize=self._pool_maxsize,
                block=self._pool_block,
                **proxy_kwargs,
            )

        return manager

    def cert_verify(self, conn, url, verify, cert):
        """Verify a SSL certificate. This method should not be called from user
        code, and is only exposed for use when subclassing the
        :class:`HTTPAdapter <requests.adapters.HTTPAdapter>`.

        :param conn: The urllib3 connection object associated with the cert.
        :param url: The requested URL.
        :param verify: Either a boolean, in which case it controls whether we verify
            the server's TLS certificate, or a string, in which case it must be a path
            to a CA bundle to use
        :param cert: The SSL certificate to verify.
        """
        if url.lower().startswith("https") and verify:
            conn.cert_reqs = "CERT_REQUIRED"

            # Only load the CA certificates if 'verify' is a string indicating the CA bundle to use.
            # Otherwise, if verify is a boolean, we don't load anything since
            # the connection will be using a context with the default certificates already loaded,
            # and this avoids a call to the slow load_verify_locations()
            if verify is not True:
                # `verify` must be a str with a path then
                cert_loc = verify

                if not os.path.exists(cert_loc):
                    raise OSError(
                        f"Could not find a suitable TLS CA certificate bundle, "
                        f"invalid path: {cert_loc}"
                    )

                if not os.path.isdir(cert_loc):
                    conn.ca_certs = cert_loc
                else:
                    conn.ca_cert_dir = cert_loc
        else:
            conn.cert_reqs = "CERT_NONE"
            conn.ca_certs = None
            conn.ca_cert_dir = None

        if cert:
            if not isinstance(cert, basestring):
                conn.cert_file = cert[0]
                conn.key_file = cert[1]
            else:
                conn.cert_file = cert
                conn.key_file = None
            if conn.cert_file and not os.path.exists(conn.cert_file):
                raise OSError(
                    f"Could not find the TLS certificate file, "
                    f"invalid path: {conn.cert_file}"
                )
            if conn.key_file and not os.path.exists(conn.key_file):
                raise OSError(
                    f"Could not find the TLS key file, invalid path: {conn.key_file}"
                )

    def build_response(self, req, resp):
        """Builds a :class:`Response <requests.Response>` object from a urllib3
        response. This should not be called from user code, and is only exposed
        for use when subclassing the
        :class:`HTTPAdapter <requests.adapters.HTTPAdapter>`

        :param req: The :class:`PreparedRequest <PreparedRequest>` used to generate the response.
        :param resp: The urllib3 response object.
        :rtype: requests.Response
        """
        response = Response()

        # Fallback to None if there's no status_code, for whatever reason.
        response.status_code = getattr(resp, "status", None)

        # Make headers case-insensitive.
        response.headers = CaseInsensitiveDict(getattr(resp, "headers", {}))

        # Set encoding.
        response.encoding = get_encoding_from_headers(response.headers)
        response.raw = resp
        response.reason = response.raw.reason

        if isinstance(req.url, bytes):
            response.url = req.url.decode("utf-8")
        else:
            response.url = req.url

        # Add new cookies from the server.
        extract_cookies_to_jar(response.cookies, req, resp)

        # Give the Response some context.
        response.request = req
        response.connection = self

        return response

    def build_connection_pool_key_attributes(self, request, verify, cert=None):
        """Build the PoolKey attributes used by urllib3 to return a connection.

        This looks at the PreparedRequest, the user-specified verify value,
        and the value of the cert parameter to determine what PoolKey values
        to use to select a connection from a given urllib3 Connection Pool.

        The SSL related pool key arguments are not consistently set. As of
        this writing, use the following to determine what keys may be in that
        dictionary:

        * If ``verify`` is ``True``, ``"ssl_context"`` will be set and will be the
          default Requests SSL Context
        * If ``verify`` is ``False``, ``"ssl_context"`` will not be set but
          ``"cert_reqs"`` will be set
        * If ``verify`` is a string, (i.e., it is a user-specified trust bundle)
          ``"ca_certs"`` will be set if the string is not a directory recognized
          by :py:func:`os.path.isdir`, otherwise ``"ca_certs_dir"`` will be
          set.
        * If ``"cert"`` is specified, ``"cert_file"`` will always be set. If
          ``"cert"`` is a tuple with a second item, ``"key_file"`` will also
          be present

        To override these settings, one may subclass this class, call this
        method and use the above logic to change parameters as desired. For
        example, if one wishes to use a custom :py:class:`ssl.SSLContext` one
        must both set ``"ssl_context"`` and based on what else they require,
        alter the other keys to ensure the desired behaviour.

        :param request:
            The PreparedReqest being sent over the connection.
        :type request:
            :class:`~requests.models.PreparedRequest`
        :param verify:
            Either a boolean, in which case it controls whether
            we verify the server's TLS certificate, or a string, in which case it
            must be a path to a CA bundle to use.
        :param cert:
            (optional) Any user-provided SSL certificate for client
            authentication (a.k.a., mTLS). This may be a string (i.e., just
            the path to a file which holds both certificate and key) or a
            tuple of length 2 with the certificate file path and key file
            path.
        :returns:
            A tuple of two dictionaries. The first is the "host parameters"
            portion of the Pool Key including scheme, hostname, and port. The
            second is a dictionary of SSLContext related parameters.
        """
        return _urllib3_request_context(request, verify, cert, self.poolmanager)

    def get_connection_with_tls_context(self, request, verify, proxies=None, cert=None):
        """Returns a urllib3 connection for the given request and TLS settings.
        This should not be called from user code, and is only exposed for use
        when subclassing the :class:`HTTPAdapter <requests.adapters.HTTPAdapter>`.

        :param request:
            The :class:`PreparedRequest <PreparedRequest>` object to be sent
            over the connection.
        :param verify:
            Either a boolean, in which case it controls whether we verify the
            server's TLS certificate, or a string, in which case it must be a
            path to a CA bundle to use.
        :param proxies:
            (optional) The proxies dictionary to apply to the request.
        :param cert:
            (optional) Any user-provided SSL certificate to be used for client
            authentication (a.k.a., mTLS).
        :rtype:
            urllib3.ConnectionPool
        """
        proxy = select_proxy(request.url, proxies)
        try:
            host_params, pool_kwargs = self.build_connection_pool_key_attributes(
                request,
                verify,
                cert,
            )
        except ValueError as e:
            raise InvalidURL(e, request=request)
        if proxy:
            proxy = prepend_scheme_if_needed(proxy, "http")
            proxy_url = parse_url(proxy)
            if not proxy_url.host:
                raise InvalidProxyURL(
                    "Please check proxy URL. It is malformed "
                    "and could be missing the host."
                )
            proxy_manager = self.proxy_manager_for(proxy)
            conn = proxy_manager.connection_from_host(
                **host_params, pool_kwargs=pool_kwargs
            )
        else:
            # Only scheme should be lower case
            conn = self.poolmanager.connection_from_host(
                **host_params, pool_kwargs=pool_kwargs
            )

        return conn

    def get_connection(self, url, proxies=None):
        """DEPRECATED: Users should move to `get_connection_with_tls_context`
        for all subclasses of HTTPAdapter using Requests>=2.32.2.

        Returns a urllib3 connection for the given URL. This should not be
        called from user code, and is only exposed for use when subclassing the
        :class:`HTTPAdapter <requests.adapters.HTTPAdapter>`.

        :param url: The URL to connect to.
        :param proxies: (optional) A Requests-style dictionary of proxies used on this request.
        :rtype: urllib3.ConnectionPool
        """
        warnings.warn(
            (
                "`get_connection` has been deprecated in favor of "
                "`get_connection_with_tls_context`. Custom HTTPAdapter subclasses "
                "will need to migrate for Requests>=2.32.2. Please see "
                "https://github.com/psf/requests/pull/6710 for more details."
            ),
            DeprecationWarning,
        )
        proxy = select_proxy(url, proxies)

        if proxy:
            proxy = prepend_scheme_if_needed(proxy, "http")
            proxy_url = parse_url(proxy)
            if not proxy_url.host:
                raise InvalidProxyURL(
                    "Please check proxy URL. It is malformed "
                    "and could be missing the host."
                )
            proxy_manager = self.proxy_manager_for(proxy)
            conn = proxy_manager.connection_from_url(url)
        else:
            # Only scheme should be lower case
            parsed = urlparse(url)
            url = parsed.geturl()
            conn = self.poolmanager.connection_from_url(url)

        return conn

    def close(self):
        """Disposes of any internal state.

        Currently, this closes the PoolManager and any active ProxyManager,
        which closes any pooled connections.
        """
        self.poolmanager.clear()
        for proxy in self.proxy_manager.values():
            proxy.clear()

    def request_url(self, request, proxies):
        """Obtain the url to use when making the final request.

        If the message is being sent through a HTTP proxy, the full URL has to
        be used. Otherwise, we should only use the path portion of the URL.

        This should not be called from user code, and is only exposed for use
        when subclassing the
        :class:`HTTPAdapter <requests.adapters.HTTPAdapter>`.

        :param request: The :class:`PreparedRequest <PreparedRequest>` being sent.
        :param proxies: A dictionary of schemes or schemes and hosts to proxy URLs.
        :rtype: str
        """
        proxy = select_proxy(request.url, proxies)
        scheme = urlparse(request.url).scheme

        is_proxied_http_request = proxy and scheme != "https"
        using_socks_proxy = False
        if proxy:
            proxy_scheme = urlparse(proxy).scheme.lower()
            using_socks_proxy = proxy_scheme.startswith("socks")

        url = request.path_url
        if url.startswith("//"):  # Don't confuse urllib3
            url = f"/{url.lstrip('/')}"

        if is_proxied_http_request and not using_socks_proxy:
            url = urldefragauth(request.url)

        return url

    def add_headers(self, request, **kwargs):
        """Add any headers needed by the connection. As of v2.0 this does
        nothing by default, but is left for overriding by users that subclass
        the :class:`HTTPAdapter <requests.adapters.HTTPAdapter>`.

        This should not be called from user code, and is only exposed for use
        when subclassing the
        :class:`HTTPAdapter <requests.adapters.HTTPAdapter>`.

        :param request: The :class:`PreparedRequest <PreparedRequest>` to add headers to.
        :param kwargs: The keyword arguments from the call to send().
        """
        pass

    def proxy_headers(self, proxy):
        """Returns a dictionary of the headers to add to any request sent
        through a proxy. This works with urllib3 magic to ensure that they are
        correctly sent to the proxy, rather than in a tunnelled request if
        CONNECT is being used.

        This should not be called from user code, and is only exposed for use
        when subclassing the
        :class:`HTTPAdapter <requests.adapters.HTTPAdapter>`.

        :param proxy: The url of the proxy being used for this request.
        :rtype: dict
        """
        headers = {}
        username, password = get_auth_from_url(proxy)

        if username:
            headers["Proxy-Authorization"] = _basic_auth_str(username, password)

        return headers

    def send(
        self, request, stream=False, timeout=None, verify=True, cert=None, proxies=None
    ):
        """Sends PreparedRequest object. Returns Response object.

        :param request: The :class:`PreparedRequest <PreparedRequest>` being sent.
        :param stream: (optional) Whether to stream the request content.
        :param timeout: (optional) How long to wait for the server to send
            data before giving up, as a float, or a :ref:`(connect timeout,
            read timeout) <timeouts>` tuple.
        :type timeout: float or tuple or urllib3 Timeout object
        :param verify: (optional) Either a boolean, in which case it controls whether
            we verify the server's TLS certificate, or a string, in which case it
            must be a path to a CA bundle to use
        :param cert: (optional) Any user-provided SSL certificate to be trusted.
        :param proxies: (optional) The proxies dictionary to apply to the request.
        :rtype: requests.Response
        """

        try:
            conn = self.get_connection_with_tls_context(
                request, verify, proxies=proxies, cert=cert
            )
        except LocationValueError as e:
            raise InvalidURL(e, request=request)

        self.cert_verify(conn, request.url, verify, cert)
        url = self.request_url(request, proxies)
        self.add_headers(
            request,
            stream=stream,
            timeout=timeout,
            verify=verify,
            cert=cert,
            proxies=proxies,
        )

        chunked = not (request.body is None or "Content-Length" in request.headers)

        if isinstance(timeout, tuple):
            try:
                connect, read = timeout
                timeout = TimeoutSauce(connect=connect, read=read)
            except ValueError:
                raise ValueError(
                    f"Invalid timeout {timeout}. Pass a (connect, read) timeout tuple, "
                    f"or a single float to set both timeouts to the same value."
                )
        elif isinstance(timeout, TimeoutSauce):
            pass
        else:
            timeout = TimeoutSauce(connect=timeout, read=timeout)

        try:
            resp = conn.urlopen(
                method=request.method,
                url=url,
                body=request.body,
                headers=request.headers,
                redirect=False,
                assert_same_host=False,
                preload_content=False,
                decode_content=False,
                retries=self.max_retries,
                timeout=timeout,
                chunked=chunked,
            )

        except (ProtocolError, OSError) as err:
            raise ConnectionError(err, request=request)

        except MaxRetryError as e:
            if isinstance(e.reason, ConnectTimeoutError):
                # TODO: Remove this in 3.0.0: see #2811
                if not isinstance(e.reason, NewConnectionError):
                    raise ConnectTimeout(e, request=request)

            if isinstance(e.reason, ResponseError):
                raise RetryError(e, request=request)

            if isinstance(e.reason, _ProxyError):
                raise ProxyError(e, request=request)

            if isinstance(e.reason, _SSLError):
                # This branch is for urllib3 v1.22 and later.
                raise SSLError(e, request=request)

            raise ConnectionError(e, request=request)

        except ClosedPoolError as e:
            raise ConnectionError(e, request=request)

        except _ProxyError as e:
            raise ProxyError(e)

        except (_SSLError, _HTTPError) as e:
            if isinstance(e, _SSLError):
                # This branch is for urllib3 versions earlier than v1.22
                raise SSLError(e, request=request)
            elif isinstance(e, ReadTimeoutError):
                raise ReadTimeout(e, request=request)
            elif isinstance(e, _InvalidHeader):
                raise InvalidHeader(e, request=request)
            else:
                raise

        return self.build_response(request, resp)

# === NexusCore/openenv\Lib\site-packages\pip\_vendor\requests\adapters.py ===
"""
requests.adapters
~~~~~~~~~~~~~~~~~

This module contains the transport adapters that Requests uses to define
and maintain connections.
"""

import os.path
import socket  # noqa: F401
import typing
import warnings

from pip._vendor.urllib3.exceptions import ClosedPoolError, ConnectTimeoutError
from pip._vendor.urllib3.exceptions import HTTPError as _HTTPError
from pip._vendor.urllib3.exceptions import InvalidHeader as _InvalidHeader
from pip._vendor.urllib3.exceptions import (
    LocationValueError,
    MaxRetryError,
    NewConnectionError,
    ProtocolError,
)
from pip._vendor.urllib3.exceptions import ProxyError as _ProxyError
from pip._vendor.urllib3.exceptions import ReadTimeoutError, ResponseError
from pip._vendor.urllib3.exceptions import SSLError as _SSLError
from pip._vendor.urllib3.poolmanager import PoolManager, proxy_from_url
from pip._vendor.urllib3.util import Timeout as TimeoutSauce
from pip._vendor.urllib3.util import parse_url
from pip._vendor.urllib3.util.retry import Retry
from pip._vendor.urllib3.util.ssl_ import create_urllib3_context

from .auth import _basic_auth_str
from .compat import basestring, urlparse
from .cookies import extract_cookies_to_jar
from .exceptions import (
    ConnectionError,
    ConnectTimeout,
    InvalidHeader,
    InvalidProxyURL,
    InvalidSchema,
    InvalidURL,
    ProxyError,
    ReadTimeout,
    RetryError,
    SSLError,
)
from .models import Response
from .structures import CaseInsensitiveDict
from .utils import (
    DEFAULT_CA_BUNDLE_PATH,
    extract_zipped_paths,
    get_auth_from_url,
    get_encoding_from_headers,
    prepend_scheme_if_needed,
    select_proxy,
    urldefragauth,
)

try:
    from pip._vendor.urllib3.contrib.socks import SOCKSProxyManager
except ImportError:

    def SOCKSProxyManager(*args, **kwargs):
        raise InvalidSchema("Missing dependencies for SOCKS support.")


if typing.TYPE_CHECKING:
    from .models import PreparedRequest


DEFAULT_POOLBLOCK = False
DEFAULT_POOLSIZE = 10
DEFAULT_RETRIES = 0
DEFAULT_POOL_TIMEOUT = None


try:
    import ssl  # noqa: F401

    _preloaded_ssl_context = create_urllib3_context()
    _preloaded_ssl_context.load_verify_locations(
        extract_zipped_paths(DEFAULT_CA_BUNDLE_PATH)
    )
except ImportError:
    # Bypass default SSLContext creation when Python
    # interpreter isn't built with the ssl module.
    _preloaded_ssl_context = None


def _urllib3_request_context(
    request: "PreparedRequest",
    verify: "bool | str | None",
    client_cert: "typing.Tuple[str, str] | str | None",
    poolmanager: "PoolManager",
) -> "(typing.Dict[str, typing.Any], typing.Dict[str, typing.Any])":
    host_params = {}
    pool_kwargs = {}
    parsed_request_url = urlparse(request.url)
    scheme = parsed_request_url.scheme.lower()
    port = parsed_request_url.port

    # Determine if we have and should use our default SSLContext
    # to optimize performance on standard requests.
    poolmanager_kwargs = getattr(poolmanager, "connection_pool_kw", {})
    has_poolmanager_ssl_context = poolmanager_kwargs.get("ssl_context")
    should_use_default_ssl_context = (
        _preloaded_ssl_context is not None and not has_poolmanager_ssl_context
    )

    cert_reqs = "CERT_REQUIRED"
    if verify is False:
        cert_reqs = "CERT_NONE"
    elif verify is True and should_use_default_ssl_context:
        pool_kwargs["ssl_context"] = _preloaded_ssl_context
    elif isinstance(verify, str):
        if not os.path.isdir(verify):
            pool_kwargs["ca_certs"] = verify
        else:
            pool_kwargs["ca_cert_dir"] = verify
    pool_kwargs["cert_reqs"] = cert_reqs
    if client_cert is not None:
        if isinstance(client_cert, tuple) and len(client_cert) == 2:
            pool_kwargs["cert_file"] = client_cert[0]
            pool_kwargs["key_file"] = client_cert[1]
        else:
            # According to our docs, we allow users to specify just the client
            # cert path
            pool_kwargs["cert_file"] = client_cert
    host_params = {
        "scheme": scheme,
        "host": parsed_request_url.hostname,
        "port": port,
    }
    return host_params, pool_kwargs


class BaseAdapter:
    """The Base Transport Adapter"""

    def __init__(self):
        super().__init__()

    def send(
        self, request, stream=False, timeout=None, verify=True, cert=None, proxies=None
    ):
        """Sends PreparedRequest object. Returns Response object.

        :param request: The :class:`PreparedRequest <PreparedRequest>` being sent.
        :param stream: (optional) Whether to stream the request content.
        :param timeout: (optional) How long to wait for the server to send
            data before giving up, as a float, or a :ref:`(connect timeout,
            read timeout) <timeouts>` tuple.
        :type timeout: float or tuple
        :param verify: (optional) Either a boolean, in which case it controls whether we verify
            the server's TLS certificate, or a string, in which case it must be a path
            to a CA bundle to use
        :param cert: (optional) Any user-provided SSL certificate to be trusted.
        :param proxies: (optional) The proxies dictionary to apply to the request.
        """
        raise NotImplementedError

    def close(self):
        """Cleans up adapter specific items."""
        raise NotImplementedError


class HTTPAdapter(BaseAdapter):
    """The built-in HTTP Adapter for urllib3.

    Provides a general-case interface for Requests sessions to contact HTTP and
    HTTPS urls by implementing the Transport Adapter interface. This class will
    usually be created by the :class:`Session <Session>` class under the
    covers.

    :param pool_connections: The number of urllib3 connection pools to cache.
    :param pool_maxsize: The maximum number of connections to save in the pool.
    :param max_retries: The maximum number of retries each connection
        should attempt. Note, this applies only to failed DNS lookups, socket
        connections and connection timeouts, never to requests where data has
        made it to the server. By default, Requests does not retry failed
        connections. If you need granular control over the conditions under
        which we retry a request, import urllib3's ``Retry`` class and pass
        that instead.
    :param pool_block: Whether the connection pool should block for connections.

    Usage::

      >>> import requests
      >>> s = requests.Session()
      >>> a = requests.adapters.HTTPAdapter(max_retries=3)
      >>> s.mount('http://', a)
    """

    __attrs__ = [
        "max_retries",
        "config",
        "_pool_connections",
        "_pool_maxsize",
        "_pool_block",
    ]

    def __init__(
        self,
        pool_connections=DEFAULT_POOLSIZE,
        pool_maxsize=DEFAULT_POOLSIZE,
        max_retries=DEFAULT_RETRIES,
        pool_block=DEFAULT_POOLBLOCK,
    ):
        if max_retries == DEFAULT_RETRIES:
            self.max_retries = Retry(0, read=False)
        else:
            self.max_retries = Retry.from_int(max_retries)
        self.config = {}
        self.proxy_manager = {}

        super().__init__()

        self._pool_connections = pool_connections
        self._pool_maxsize = pool_maxsize
        self._pool_block = pool_block

        self.init_poolmanager(pool_connections, pool_maxsize, block=pool_block)

    def __getstate__(self):
        return {attr: getattr(self, attr, None) for attr in self.__attrs__}

    def __setstate__(self, state):
        # Can't handle by adding 'proxy_manager' to self.__attrs__ because
        # self.poolmanager uses a lambda function, which isn't pickleable.
        self.proxy_manager = {}
        self.config = {}

        for attr, value in state.items():
            setattr(self, attr, value)

        self.init_poolmanager(
            self._pool_connections, self._pool_maxsize, block=self._pool_block
        )

    def init_poolmanager(
        self, connections, maxsize, block=DEFAULT_POOLBLOCK, **pool_kwargs
    ):
        """Initializes a urllib3 PoolManager.

        This method should not be called from user code, and is only
        exposed for use when subclassing the
        :class:`HTTPAdapter <requests.adapters.HTTPAdapter>`.

        :param connections: The number of urllib3 connection pools to cache.
        :param maxsize: The maximum number of connections to save in the pool.
        :param block: Block when no free connections are available.
        :param pool_kwargs: Extra keyword arguments used to initialize the Pool Manager.
        """
        # save these values for pickling
        self._pool_connections = connections
        self._pool_maxsize = maxsize
        self._pool_block = block

        self.poolmanager = PoolManager(
            num_pools=connections,
            maxsize=maxsize,
            block=block,
            **pool_kwargs,
        )

    def proxy_manager_for(self, proxy, **proxy_kwargs):
        """Return urllib3 ProxyManager for the given proxy.

        This method should not be called from user code, and is only
        exposed for use when subclassing the
        :class:`HTTPAdapter <requests.adapters.HTTPAdapter>`.

        :param proxy: The proxy to return a urllib3 ProxyManager for.
        :param proxy_kwargs: Extra keyword arguments used to configure the Proxy Manager.
        :returns: ProxyManager
        :rtype: urllib3.ProxyManager
        """
        if proxy in self.proxy_manager:
            manager = self.proxy_manager[proxy]
        elif proxy.lower().startswith("socks"):
            username, password = get_auth_from_url(proxy)
            manager = self.proxy_manager[proxy] = SOCKSProxyManager(
                proxy,
                username=username,
                password=password,
                num_pools=self._pool_connections,
                maxsize=self._pool_maxsize,
                block=self._pool_block,
                **proxy_kwargs,
            )
        else:
            proxy_headers = self.proxy_headers(proxy)
            manager = self.proxy_manager[proxy] = proxy_from_url(
                proxy,
                proxy_headers=proxy_headers,
                num_pools=self._pool_connections,
                maxsize=self._pool_maxsize,
                block=self._pool_block,
                **proxy_kwargs,
            )

        return manager

    def cert_verify(self, conn, url, verify, cert):
        """Verify a SSL certificate. This method should not be called from user
        code, and is only exposed for use when subclassing the
        :class:`HTTPAdapter <requests.adapters.HTTPAdapter>`.

        :param conn: The urllib3 connection object associated with the cert.
        :param url: The requested URL.
        :param verify: Either a boolean, in which case it controls whether we verify
            the server's TLS certificate, or a string, in which case it must be a path
            to a CA bundle to use
        :param cert: The SSL certificate to verify.
        """
        if url.lower().startswith("https") and verify:
            conn.cert_reqs = "CERT_REQUIRED"

            # Only load the CA certificates if 'verify' is a string indicating the CA bundle to use.
            # Otherwise, if verify is a boolean, we don't load anything since
            # the connection will be using a context with the default certificates already loaded,
            # and this avoids a call to the slow load_verify_locations()
            if verify is not True:
                # `verify` must be a str with a path then
                cert_loc = verify

                if not os.path.exists(cert_loc):
                    raise OSError(
                        f"Could not find a suitable TLS CA certificate bundle, "
                        f"invalid path: {cert_loc}"
                    )

                if not os.path.isdir(cert_loc):
                    conn.ca_certs = cert_loc
                else:
                    conn.ca_cert_dir = cert_loc
        else:
            conn.cert_reqs = "CERT_NONE"
            conn.ca_certs = None
            conn.ca_cert_dir = None

        if cert:
            if not isinstance(cert, basestring):
                conn.cert_file = cert[0]
                conn.key_file = cert[1]
            else:
                conn.cert_file = cert
                conn.key_file = None
            if conn.cert_file and not os.path.exists(conn.cert_file):
                raise OSError(
                    f"Could not find the TLS certificate file, "
                    f"invalid path: {conn.cert_file}"
                )
            if conn.key_file and not os.path.exists(conn.key_file):
                raise OSError(
                    f"Could not find the TLS key file, invalid path: {conn.key_file}"
                )

    def build_response(self, req, resp):
        """Builds a :class:`Response <requests.Response>` object from a urllib3
        response. This should not be called from user code, and is only exposed
        for use when subclassing the
        :class:`HTTPAdapter <requests.adapters.HTTPAdapter>`

        :param req: The :class:`PreparedRequest <PreparedRequest>` used to generate the response.
        :param resp: The urllib3 response object.
        :rtype: requests.Response
        """
        response = Response()

        # Fallback to None if there's no status_code, for whatever reason.
        response.status_code = getattr(resp, "status", None)

        # Make headers case-insensitive.
        response.headers = CaseInsensitiveDict(getattr(resp, "headers", {}))

        # Set encoding.
        response.encoding = get_encoding_from_headers(response.headers)
        response.raw = resp
        response.reason = response.raw.reason

        if isinstance(req.url, bytes):
            response.url = req.url.decode("utf-8")
        else:
            response.url = req.url

        # Add new cookies from the server.
        extract_cookies_to_jar(response.cookies, req, resp)

        # Give the Response some context.
        response.request = req
        response.connection = self

        return response

    def build_connection_pool_key_attributes(self, request, verify, cert=None):
        """Build the PoolKey attributes used by urllib3 to return a connection.

        This looks at the PreparedRequest, the user-specified verify value,
        and the value of the cert parameter to determine what PoolKey values
        to use to select a connection from a given urllib3 Connection Pool.

        The SSL related pool key arguments are not consistently set. As of
        this writing, use the following to determine what keys may be in that
        dictionary:

        * If ``verify`` is ``True``, ``"ssl_context"`` will be set and will be the
          default Requests SSL Context
        * If ``verify`` is ``False``, ``"ssl_context"`` will not be set but
          ``"cert_reqs"`` will be set
        * If ``verify`` is a string, (i.e., it is a user-specified trust bundle)
          ``"ca_certs"`` will be set if the string is not a directory recognized
          by :py:func:`os.path.isdir`, otherwise ``"ca_certs_dir"`` will be
          set.
        * If ``"cert"`` is specified, ``"cert_file"`` will always be set. If
          ``"cert"`` is a tuple with a second item, ``"key_file"`` will also
          be present

        To override these settings, one may subclass this class, call this
        method and use the above logic to change parameters as desired. For
        example, if one wishes to use a custom :py:class:`ssl.SSLContext` one
        must both set ``"ssl_context"`` and based on what else they require,
        alter the other keys to ensure the desired behaviour.

        :param request:
            The PreparedReqest being sent over the connection.
        :type request:
            :class:`~requests.models.PreparedRequest`
        :param verify:
            Either a boolean, in which case it controls whether
            we verify the server's TLS certificate, or a string, in which case it
            must be a path to a CA bundle to use.
        :param cert:
            (optional) Any user-provided SSL certificate for client
            authentication (a.k.a., mTLS). This may be a string (i.e., just
            the path to a file which holds both certificate and key) or a
            tuple of length 2 with the certificate file path and key file
            path.
        :returns:
            A tuple of two dictionaries. The first is the "host parameters"
            portion of the Pool Key including scheme, hostname, and port. The
            second is a dictionary of SSLContext related parameters.
        """
        return _urllib3_request_context(request, verify, cert, self.poolmanager)

    def get_connection_with_tls_context(self, request, verify, proxies=None, cert=None):
        """Returns a urllib3 connection for the given request and TLS settings.
        This should not be called from user code, and is only exposed for use
        when subclassing the :class:`HTTPAdapter <requests.adapters.HTTPAdapter>`.

        :param request:
            The :class:`PreparedRequest <PreparedRequest>` object to be sent
            over the connection.
        :param verify:
            Either a boolean, in which case it controls whether we verify the
            server's TLS certificate, or a string, in which case it must be a
            path to a CA bundle to use.
        :param proxies:
            (optional) The proxies dictionary to apply to the request.
        :param cert:
            (optional) Any user-provided SSL certificate to be used for client
            authentication (a.k.a., mTLS).
        :rtype:
            urllib3.ConnectionPool
        """
        proxy = select_proxy(request.url, proxies)
        try:
            host_params, pool_kwargs = self.build_connection_pool_key_attributes(
                request,
                verify,
                cert,
            )
        except ValueError as e:
            raise InvalidURL(e, request=request)
        if proxy:
            proxy = prepend_scheme_if_needed(proxy, "http")
            proxy_url = parse_url(proxy)
            if not proxy_url.host:
                raise InvalidProxyURL(
                    "Please check proxy URL. It is malformed "
                    "and could be missing the host."
                )
            proxy_manager = self.proxy_manager_for(proxy)
            conn = proxy_manager.connection_from_host(
                **host_params, pool_kwargs=pool_kwargs
            )
        else:
            # Only scheme should be lower case
            conn = self.poolmanager.connection_from_host(
                **host_params, pool_kwargs=pool_kwargs
            )

        return conn

    def get_connection(self, url, proxies=None):
        """DEPRECATED: Users should move to `get_connection_with_tls_context`
        for all subclasses of HTTPAdapter using Requests>=2.32.2.

        Returns a urllib3 connection for the given URL. This should not be
        called from user code, and is only exposed for use when subclassing the
        :class:`HTTPAdapter <requests.adapters.HTTPAdapter>`.

        :param url: The URL to connect to.
        :param proxies: (optional) A Requests-style dictionary of proxies used on this request.
        :rtype: urllib3.ConnectionPool
        """
        warnings.warn(
            (
                "`get_connection` has been deprecated in favor of "
                "`get_connection_with_tls_context`. Custom HTTPAdapter subclasses "
                "will need to migrate for Requests>=2.32.2. Please see "
                "https://github.com/psf/requests/pull/6710 for more details."
            ),
            DeprecationWarning,
        )
        proxy = select_proxy(url, proxies)

        if proxy:
            proxy = prepend_scheme_if_needed(proxy, "http")
            proxy_url = parse_url(proxy)
            if not proxy_url.host:
                raise InvalidProxyURL(
                    "Please check proxy URL. It is malformed "
                    "and could be missing the host."
                )
            proxy_manager = self.proxy_manager_for(proxy)
            conn = proxy_manager.connection_from_url(url)
        else:
            # Only scheme should be lower case
            parsed = urlparse(url)
            url = parsed.geturl()
            conn = self.poolmanager.connection_from_url(url)

        return conn

    def close(self):
        """Disposes of any internal state.

        Currently, this closes the PoolManager and any active ProxyManager,
        which closes any pooled connections.
        """
        self.poolmanager.clear()
        for proxy in self.proxy_manager.values():
            proxy.clear()

    def request_url(self, request, proxies):
        """Obtain the url to use when making the final request.

        If the message is being sent through a HTTP proxy, the full URL has to
        be used. Otherwise, we should only use the path portion of the URL.

        This should not be called from user code, and is only exposed for use
        when subclassing the
        :class:`HTTPAdapter <requests.adapters.HTTPAdapter>`.

        :param request: The :class:`PreparedRequest <PreparedRequest>` being sent.
        :param proxies: A dictionary of schemes or schemes and hosts to proxy URLs.
        :rtype: str
        """
        proxy = select_proxy(request.url, proxies)
        scheme = urlparse(request.url).scheme

        is_proxied_http_request = proxy and scheme != "https"
        using_socks_proxy = False
        if proxy:
            proxy_scheme = urlparse(proxy).scheme.lower()
            using_socks_proxy = proxy_scheme.startswith("socks")

        url = request.path_url
        if url.startswith("//"):  # Don't confuse urllib3
            url = f"/{url.lstrip('/')}"

        if is_proxied_http_request and not using_socks_proxy:
            url = urldefragauth(request.url)

        return url

    def add_headers(self, request, **kwargs):
        """Add any headers needed by the connection. As of v2.0 this does
        nothing by default, but is left for overriding by users that subclass
        the :class:`HTTPAdapter <requests.adapters.HTTPAdapter>`.

        This should not be called from user code, and is only exposed for use
        when subclassing the
        :class:`HTTPAdapter <requests.adapters.HTTPAdapter>`.

        :param request: The :class:`PreparedRequest <PreparedRequest>` to add headers to.
        :param kwargs: The keyword arguments from the call to send().
        """
        pass

    def proxy_headers(self, proxy):
        """Returns a dictionary of the headers to add to any request sent
        through a proxy. This works with urllib3 magic to ensure that they are
        correctly sent to the proxy, rather than in a tunnelled request if
        CONNECT is being used.

        This should not be called from user code, and is only exposed for use
        when subclassing the
        :class:`HTTPAdapter <requests.adapters.HTTPAdapter>`.

        :param proxy: The url of the proxy being used for this request.
        :rtype: dict
        """
        headers = {}
        username, password = get_auth_from_url(proxy)

        if username:
            headers["Proxy-Authorization"] = _basic_auth_str(username, password)

        return headers

    def send(
        self, request, stream=False, timeout=None, verify=True, cert=None, proxies=None
    ):
        """Sends PreparedRequest object. Returns Response object.

        :param request: The :class:`PreparedRequest <PreparedRequest>` being sent.
        :param stream: (optional) Whether to stream the request content.
        :param timeout: (optional) How long to wait for the server to send
            data before giving up, as a float, or a :ref:`(connect timeout,
            read timeout) <timeouts>` tuple.
        :type timeout: float or tuple or urllib3 Timeout object
        :param verify: (optional) Either a boolean, in which case it controls whether
            we verify the server's TLS certificate, or a string, in which case it
            must be a path to a CA bundle to use
        :param cert: (optional) Any user-provided SSL certificate to be trusted.
        :param proxies: (optional) The proxies dictionary to apply to the request.
        :rtype: requests.Response
        """

        try:
            conn = self.get_connection_with_tls_context(
                request, verify, proxies=proxies, cert=cert
            )
        except LocationValueError as e:
            raise InvalidURL(e, request=request)

        self.cert_verify(conn, request.url, verify, cert)
        url = self.request_url(request, proxies)
        self.add_headers(
            request,
            stream=stream,
            timeout=timeout,
            verify=verify,
            cert=cert,
            proxies=proxies,
        )

        chunked = not (request.body is None or "Content-Length" in request.headers)

        if isinstance(timeout, tuple):
            try:
                connect, read = timeout
                timeout = TimeoutSauce(connect=connect, read=read)
            except ValueError:
                raise ValueError(
                    f"Invalid timeout {timeout}. Pass a (connect, read) timeout tuple, "
                    f"or a single float to set both timeouts to the same value."
                )
        elif isinstance(timeout, TimeoutSauce):
            pass
        else:
            timeout = TimeoutSauce(connect=timeout, read=timeout)

        try:
            resp = conn.urlopen(
                method=request.method,
                url=url,
                body=request.body,
                headers=request.headers,
                redirect=False,
                assert_same_host=False,
                preload_content=False,
                decode_content=False,
                retries=self.max_retries,
                timeout=timeout,
                chunked=chunked,
            )

        except (ProtocolError, OSError) as err:
            raise ConnectionError(err, request=request)

        except MaxRetryError as e:
            if isinstance(e.reason, ConnectTimeoutError):
                # TODO: Remove this in 3.0.0: see #2811
                if not isinstance(e.reason, NewConnectionError):
                    raise ConnectTimeout(e, request=request)

            if isinstance(e.reason, ResponseError):
                raise RetryError(e, request=request)

            if isinstance(e.reason, _ProxyError):
                raise ProxyError(e, request=request)

            if isinstance(e.reason, _SSLError):
                # This branch is for urllib3 v1.22 and later.
                raise SSLError(e, request=request)

            raise ConnectionError(e, request=request)

        except ClosedPoolError as e:
            raise ConnectionError(e, request=request)

        except _ProxyError as e:
            raise ProxyError(e)

        except (_SSLError, _HTTPError) as e:
            if isinstance(e, _SSLError):
                # This branch is for urllib3 versions earlier than v1.22
                raise SSLError(e, request=request)
            elif isinstance(e, ReadTimeoutError):
                raise ReadTimeout(e, request=request)
            elif isinstance(e, _InvalidHeader):
                raise InvalidHeader(e, request=request)
            else:
                raise

        return self.build_response(request, resp)

# === NexusCore/openenv\Lib\site-packages\fontTools\ttLib\tables\E_B_L_C_.py ===
from fontTools.misc import sstruct
from . import DefaultTable
from fontTools.misc.textTools import bytesjoin, safeEval
from .BitmapGlyphMetrics import (
    BigGlyphMetrics,
    bigGlyphMetricsFormat,
    SmallGlyphMetrics,
    smallGlyphMetricsFormat,
)
import struct
import itertools
from collections import deque
import logging


log = logging.getLogger(__name__)

eblcHeaderFormat = """
	> # big endian
	version:  16.16F
	numSizes: I
"""
# The table format string is split to handle sbitLineMetrics simply.
bitmapSizeTableFormatPart1 = """
	> # big endian
	indexSubTableArrayOffset: I
	indexTablesSize:          I
	numberOfIndexSubTables:   I
	colorRef:                 I
"""
# The compound type for hori and vert.
sbitLineMetricsFormat = """
	> # big endian
	ascender:              b
	descender:             b
	widthMax:              B
	caretSlopeNumerator:   b
	caretSlopeDenominator: b
	caretOffset:           b
	minOriginSB:           b
	minAdvanceSB:          b
	maxBeforeBL:           b
	minAfterBL:            b
	pad1:                  b
	pad2:                  b
"""
# hori and vert go between the two parts.
bitmapSizeTableFormatPart2 = """
	> # big endian
	startGlyphIndex: H
	endGlyphIndex:   H
	ppemX:           B
	ppemY:           B
	bitDepth:        B
	flags:           b
"""

indexSubTableArrayFormat = ">HHL"
indexSubTableArraySize = struct.calcsize(indexSubTableArrayFormat)

indexSubHeaderFormat = ">HHL"
indexSubHeaderSize = struct.calcsize(indexSubHeaderFormat)

codeOffsetPairFormat = ">HH"
codeOffsetPairSize = struct.calcsize(codeOffsetPairFormat)


class table_E_B_L_C_(DefaultTable.DefaultTable):
    """Embedded Bitmap Location table

    The ``EBLC`` table contains the locations of monochrome or grayscale
    bitmaps for glyphs. It must be used in concert with the ``EBDT`` table.

    See also https://learn.microsoft.com/en-us/typography/opentype/spec/eblc
    """

    dependencies = ["EBDT"]

    # This method can be overridden in subclasses to support new formats
    # without changing the other implementation. Also can be used as a
    # convenience method for coverting a font file to an alternative format.
    def getIndexFormatClass(self, indexFormat):
        return eblc_sub_table_classes[indexFormat]

    def decompile(self, data, ttFont):
        # Save the original data because offsets are from the start of the table.
        origData = data
        i = 0

        dummy = sstruct.unpack(eblcHeaderFormat, data[:8], self)
        i += 8

        self.strikes = []
        for curStrikeIndex in range(self.numSizes):
            curStrike = Strike()
            self.strikes.append(curStrike)
            curTable = curStrike.bitmapSizeTable
            dummy = sstruct.unpack2(
                bitmapSizeTableFormatPart1, data[i : i + 16], curTable
            )
            i += 16
            for metric in ("hori", "vert"):
                metricObj = SbitLineMetrics()
                vars(curTable)[metric] = metricObj
                dummy = sstruct.unpack2(
                    sbitLineMetricsFormat, data[i : i + 12], metricObj
                )
                i += 12
            dummy = sstruct.unpack(
                bitmapSizeTableFormatPart2, data[i : i + 8], curTable
            )
            i += 8

        for curStrike in self.strikes:
            curTable = curStrike.bitmapSizeTable
            for subtableIndex in range(curTable.numberOfIndexSubTables):
                i = (
                    curTable.indexSubTableArrayOffset
                    + subtableIndex * indexSubTableArraySize
                )

                tup = struct.unpack(
                    indexSubTableArrayFormat, data[i : i + indexSubTableArraySize]
                )
                (firstGlyphIndex, lastGlyphIndex, additionalOffsetToIndexSubtable) = tup
                i = curTable.indexSubTableArrayOffset + additionalOffsetToIndexSubtable

                tup = struct.unpack(
                    indexSubHeaderFormat, data[i : i + indexSubHeaderSize]
                )
                (indexFormat, imageFormat, imageDataOffset) = tup

                indexFormatClass = self.getIndexFormatClass(indexFormat)
                indexSubTable = indexFormatClass(data[i + indexSubHeaderSize :], ttFont)
                indexSubTable.firstGlyphIndex = firstGlyphIndex
                indexSubTable.lastGlyphIndex = lastGlyphIndex
                indexSubTable.additionalOffsetToIndexSubtable = (
                    additionalOffsetToIndexSubtable
                )
                indexSubTable.indexFormat = indexFormat
                indexSubTable.imageFormat = imageFormat
                indexSubTable.imageDataOffset = imageDataOffset
                indexSubTable.decompile()  # https://github.com/fonttools/fonttools/issues/317
                curStrike.indexSubTables.append(indexSubTable)

    def compile(self, ttFont):
        dataList = []
        self.numSizes = len(self.strikes)
        dataList.append(sstruct.pack(eblcHeaderFormat, self))

        # Data size of the header + bitmapSizeTable needs to be calculated
        # in order to form offsets. This value will hold the size of the data
        # in dataList after all the data is consolidated in dataList.
        dataSize = len(dataList[0])

        # The table will be structured in the following order:
        # (0) header
        # (1) Each bitmapSizeTable [1 ... self.numSizes]
        # (2) Alternate between indexSubTableArray and indexSubTable
        #     for each bitmapSizeTable present.
        #
        # The issue is maintaining the proper offsets when table information
        # gets moved around. All offsets and size information must be recalculated
        # when building the table to allow editing within ttLib and also allow easy
        # import/export to and from XML. All of this offset information is lost
        # when exporting to XML so everything must be calculated fresh so importing
        # from XML will work cleanly. Only byte offset and size information is
        # calculated fresh. Count information like numberOfIndexSubTables is
        # checked through assertions. If the information in this table was not
        # touched or was changed properly then these types of values should match.
        #
        # The table will be rebuilt the following way:
        # (0) Precompute the size of all the bitmapSizeTables. This is needed to
        #     compute the offsets properly.
        # (1) For each bitmapSizeTable compute the indexSubTable and
        #    	indexSubTableArray pair. The indexSubTable must be computed first
        #     so that the offset information in indexSubTableArray can be
        #     calculated. Update the data size after each pairing.
        # (2) Build each bitmapSizeTable.
        # (3) Consolidate all the data into the main dataList in the correct order.

        for _ in self.strikes:
            dataSize += sstruct.calcsize(bitmapSizeTableFormatPart1)
            dataSize += len(("hori", "vert")) * sstruct.calcsize(sbitLineMetricsFormat)
            dataSize += sstruct.calcsize(bitmapSizeTableFormatPart2)

        indexSubTablePairDataList = []
        for curStrike in self.strikes:
            curTable = curStrike.bitmapSizeTable
            curTable.numberOfIndexSubTables = len(curStrike.indexSubTables)
            curTable.indexSubTableArrayOffset = dataSize

            # Precompute the size of the indexSubTableArray. This information
            # is important for correctly calculating the new value for
            # additionalOffsetToIndexSubtable.
            sizeOfSubTableArray = (
                curTable.numberOfIndexSubTables * indexSubTableArraySize
            )
            lowerBound = dataSize
            dataSize += sizeOfSubTableArray
            upperBound = dataSize

            indexSubTableDataList = []
            for indexSubTable in curStrike.indexSubTables:
                indexSubTable.additionalOffsetToIndexSubtable = (
                    dataSize - curTable.indexSubTableArrayOffset
                )
                glyphIds = list(map(ttFont.getGlyphID, indexSubTable.names))
                indexSubTable.firstGlyphIndex = min(glyphIds)
                indexSubTable.lastGlyphIndex = max(glyphIds)
                data = indexSubTable.compile(ttFont)
                indexSubTableDataList.append(data)
                dataSize += len(data)
            curTable.startGlyphIndex = min(
                ist.firstGlyphIndex for ist in curStrike.indexSubTables
            )
            curTable.endGlyphIndex = max(
                ist.lastGlyphIndex for ist in curStrike.indexSubTables
            )

            for i in curStrike.indexSubTables:
                data = struct.pack(
                    indexSubHeaderFormat,
                    i.firstGlyphIndex,
                    i.lastGlyphIndex,
                    i.additionalOffsetToIndexSubtable,
                )
                indexSubTablePairDataList.append(data)
            indexSubTablePairDataList.extend(indexSubTableDataList)
            curTable.indexTablesSize = dataSize - curTable.indexSubTableArrayOffset

        for curStrike in self.strikes:
            curTable = curStrike.bitmapSizeTable
            data = sstruct.pack(bitmapSizeTableFormatPart1, curTable)
            dataList.append(data)
            for metric in ("hori", "vert"):
                metricObj = vars(curTable)[metric]
                data = sstruct.pack(sbitLineMetricsFormat, metricObj)
                dataList.append(data)
            data = sstruct.pack(bitmapSizeTableFormatPart2, curTable)
            dataList.append(data)
        dataList.extend(indexSubTablePairDataList)

        return bytesjoin(dataList)

    def toXML(self, writer, ttFont):
        writer.simpletag("header", [("version", self.version)])
        writer.newline()
        for curIndex, curStrike in enumerate(self.strikes):
            curStrike.toXML(curIndex, writer, ttFont)

    def fromXML(self, name, attrs, content, ttFont):
        if name == "header":
            self.version = safeEval(attrs["version"])
        elif name == "strike":
            if not hasattr(self, "strikes"):
                self.strikes = []
            strikeIndex = safeEval(attrs["index"])
            curStrike = Strike()
            curStrike.fromXML(name, attrs, content, ttFont, self)

            # Grow the strike array to the appropriate size. The XML format
            # allows for the strike index value to be out of order.
            if strikeIndex >= len(self.strikes):
                self.strikes += [None] * (strikeIndex + 1 - len(self.strikes))
            assert self.strikes[strikeIndex] is None, "Duplicate strike EBLC indices."
            self.strikes[strikeIndex] = curStrike


class Strike(object):
    def __init__(self):
        self.bitmapSizeTable = BitmapSizeTable()
        self.indexSubTables = []

    def toXML(self, strikeIndex, writer, ttFont):
        writer.begintag("strike", [("index", strikeIndex)])
        writer.newline()
        self.bitmapSizeTable.toXML(writer, ttFont)
        writer.comment(
            "GlyphIds are written but not read. The firstGlyphIndex and\nlastGlyphIndex values will be recalculated by the compiler."
        )
        writer.newline()
        for indexSubTable in self.indexSubTables:
            indexSubTable.toXML(writer, ttFont)
        writer.endtag("strike")
        writer.newline()

    def fromXML(self, name, attrs, content, ttFont, locator):
        for element in content:
            if not isinstance(element, tuple):
                continue
            name, attrs, content = element
            if name == "bitmapSizeTable":
                self.bitmapSizeTable.fromXML(name, attrs, content, ttFont)
            elif name.startswith(_indexSubTableSubclassPrefix):
                indexFormat = safeEval(name[len(_indexSubTableSubclassPrefix) :])
                indexFormatClass = locator.getIndexFormatClass(indexFormat)
                indexSubTable = indexFormatClass(None, None)
                indexSubTable.indexFormat = indexFormat
                indexSubTable.fromXML(name, attrs, content, ttFont)
                self.indexSubTables.append(indexSubTable)


class BitmapSizeTable(object):
    # Returns all the simple metric names that bitmap size table
    # cares about in terms of XML creation.
    def _getXMLMetricNames(self):
        dataNames = sstruct.getformat(bitmapSizeTableFormatPart1)[1]
        dataNames = {**dataNames, **sstruct.getformat(bitmapSizeTableFormatPart2)[1]}
        # Skip the first 3 data names because they are byte offsets and counts.
        return list(dataNames.keys())[3:]

    def toXML(self, writer, ttFont):
        writer.begintag("bitmapSizeTable")
        writer.newline()
        for metric in ("hori", "vert"):
            getattr(self, metric).toXML(metric, writer, ttFont)
        for metricName in self._getXMLMetricNames():
            writer.simpletag(metricName, value=getattr(self, metricName))
            writer.newline()
        writer.endtag("bitmapSizeTable")
        writer.newline()

    def fromXML(self, name, attrs, content, ttFont):
        # Create a lookup for all the simple names that make sense to
        # bitmap size table. Only read the information from these names.
        dataNames = set(self._getXMLMetricNames())
        for element in content:
            if not isinstance(element, tuple):
                continue
            name, attrs, content = element
            if name == "sbitLineMetrics":
                direction = attrs["direction"]
                assert direction in (
                    "hori",
                    "vert",
                ), "SbitLineMetrics direction specified invalid."
                metricObj = SbitLineMetrics()
                metricObj.fromXML(name, attrs, content, ttFont)
                vars(self)[direction] = metricObj
            elif name in dataNames:
                vars(self)[name] = safeEval(attrs["value"])
            else:
                log.warning("unknown name '%s' being ignored in BitmapSizeTable.", name)


class SbitLineMetrics(object):
    def toXML(self, name, writer, ttFont):
        writer.begintag("sbitLineMetrics", [("direction", name)])
        writer.newline()
        for metricName in sstruct.getformat(sbitLineMetricsFormat)[1]:
            writer.simpletag(metricName, value=getattr(self, metricName))
            writer.newline()
        writer.endtag("sbitLineMetrics")
        writer.newline()

    def fromXML(self, name, attrs, content, ttFont):
        metricNames = set(sstruct.getformat(sbitLineMetricsFormat)[1])
        for element in content:
            if not isinstance(element, tuple):
                continue
            name, attrs, content = element
            if name in metricNames:
                vars(self)[name] = safeEval(attrs["value"])


# Important information about the naming scheme. Used for identifying subtables.
_indexSubTableSubclassPrefix = "eblc_index_sub_table_"


class EblcIndexSubTable(object):
    def __init__(self, data, ttFont):
        self.data = data
        self.ttFont = ttFont
        # TODO Currently non-lazy decompiling doesn't work for this class...
        # if not ttFont.lazy:
        # 	self.decompile()
        # 	del self.data, self.ttFont

    def __getattr__(self, attr):
        # Allow lazy decompile.
        if attr[:2] == "__":
            raise AttributeError(attr)
        if attr == "data":
            raise AttributeError(attr)
        self.decompile()
        return getattr(self, attr)

    def ensureDecompiled(self, recurse=False):
        if hasattr(self, "data"):
            self.decompile()

    # This method just takes care of the indexSubHeader. Implementing subclasses
    # should call it to compile the indexSubHeader and then continue compiling
    # the remainder of their unique format.
    def compile(self, ttFont):
        return struct.pack(
            indexSubHeaderFormat,
            self.indexFormat,
            self.imageFormat,
            self.imageDataOffset,
        )

    # Creates the XML for bitmap glyphs. Each index sub table basically makes
    # the same XML except for specific metric information that is written
    # out via a method call that a subclass implements optionally.
    def toXML(self, writer, ttFont):
        writer.begintag(
            self.__class__.__name__,
            [
                ("imageFormat", self.imageFormat),
                ("firstGlyphIndex", self.firstGlyphIndex),
                ("lastGlyphIndex", self.lastGlyphIndex),
            ],
        )
        writer.newline()
        self.writeMetrics(writer, ttFont)
        # Write out the names as thats all thats needed to rebuild etc.
        # For font debugging of consecutive formats the ids are also written.
        # The ids are not read when moving from the XML format.
        glyphIds = map(ttFont.getGlyphID, self.names)
        for glyphName, glyphId in zip(self.names, glyphIds):
            writer.simpletag("glyphLoc", name=glyphName, id=glyphId)
            writer.newline()
        writer.endtag(self.__class__.__name__)
        writer.newline()

    def fromXML(self, name, attrs, content, ttFont):
        # Read all the attributes. Even though the glyph indices are
        # recalculated, they are still read in case there needs to
        # be an immediate export of the data.
        self.imageFormat = safeEval(attrs["imageFormat"])
        self.firstGlyphIndex = safeEval(attrs["firstGlyphIndex"])
        self.lastGlyphIndex = safeEval(attrs["lastGlyphIndex"])

        self.readMetrics(name, attrs, content, ttFont)

        self.names = []
        for element in content:
            if not isinstance(element, tuple):
                continue
            name, attrs, content = element
            if name == "glyphLoc":
                self.names.append(attrs["name"])

    # A helper method that writes the metrics for the index sub table. It also
    # is responsible for writing the image size for fixed size data since fixed
    # size is not recalculated on compile. Default behavior is to do nothing.
    def writeMetrics(self, writer, ttFont):
        pass

    # A helper method that is the inverse of writeMetrics.
    def readMetrics(self, name, attrs, content, ttFont):
        pass

    # This method is for fixed glyph data sizes. There are formats where
    # the glyph data is fixed but are actually composite glyphs. To handle
    # this the font spec in indexSubTable makes the data the size of the
    # fixed size by padding the component arrays. This function abstracts
    # out this padding process. Input is data unpadded. Output is data
    # padded only in fixed formats. Default behavior is to return the data.
    def padBitmapData(self, data):
        return data

    # Remove any of the glyph locations and names that are flagged as skipped.
    # This only occurs in formats {1,3}.
    def removeSkipGlyphs(self):
        # Determines if a name, location pair is a valid data location.
        # Skip glyphs are marked when the size is equal to zero.
        def isValidLocation(args):
            (name, (startByte, endByte)) = args
            return startByte < endByte

        # Remove all skip glyphs.
        dataPairs = list(filter(isValidLocation, zip(self.names, self.locations)))
        self.names, self.locations = list(map(list, zip(*dataPairs)))


# A closure for creating a custom mixin. This is done because formats 1 and 3
# are very similar. The only difference between them is the size per offset
# value. Code put in here should handle both cases generally.
def _createOffsetArrayIndexSubTableMixin(formatStringForDataType):
    # Prep the data size for the offset array data format.
    dataFormat = ">" + formatStringForDataType
    offsetDataSize = struct.calcsize(dataFormat)

    class OffsetArrayIndexSubTableMixin(object):
        def decompile(self):
            numGlyphs = self.lastGlyphIndex - self.firstGlyphIndex + 1
            indexingOffsets = [
                glyphIndex * offsetDataSize for glyphIndex in range(numGlyphs + 2)
            ]
            indexingLocations = zip(indexingOffsets, indexingOffsets[1:])
            offsetArray = [
                struct.unpack(dataFormat, self.data[slice(*loc)])[0]
                for loc in indexingLocations
            ]

            glyphIds = list(range(self.firstGlyphIndex, self.lastGlyphIndex + 1))
            modifiedOffsets = [offset + self.imageDataOffset for offset in offsetArray]
            self.locations = list(zip(modifiedOffsets, modifiedOffsets[1:]))

            self.names = list(map(self.ttFont.getGlyphName, glyphIds))
            self.removeSkipGlyphs()
            del self.data, self.ttFont

        def compile(self, ttFont):
            # First make sure that all the data lines up properly. Formats 1 and 3
            # must have all its data lined up consecutively. If not this will fail.
            for curLoc, nxtLoc in zip(self.locations, self.locations[1:]):
                assert (
                    curLoc[1] == nxtLoc[0]
                ), "Data must be consecutive in indexSubTable offset formats"

            glyphIds = list(map(ttFont.getGlyphID, self.names))
            # Make sure that all ids are sorted strictly increasing.
            assert all(glyphIds[i] < glyphIds[i + 1] for i in range(len(glyphIds) - 1))

            # Run a simple algorithm to add skip glyphs to the data locations at
            # the places where an id is not present.
            idQueue = deque(glyphIds)
            locQueue = deque(self.locations)
            allGlyphIds = list(range(self.firstGlyphIndex, self.lastGlyphIndex + 1))
            allLocations = []
            for curId in allGlyphIds:
                if curId != idQueue[0]:
                    allLocations.append((locQueue[0][0], locQueue[0][0]))
                else:
                    idQueue.popleft()
                    allLocations.append(locQueue.popleft())

            # Now that all the locations are collected, pack them appropriately into
            # offsets. This is the form where offset[i] is the location and
            # offset[i+1]-offset[i] is the size of the data location.
            offsets = list(allLocations[0]) + [loc[1] for loc in allLocations[1:]]
            # Image data offset must be less than or equal to the minimum of locations.
            # This offset may change the value for round tripping but is safer and
            # allows imageDataOffset to not be required to be in the XML version.
            self.imageDataOffset = min(offsets)
            offsetArray = [offset - self.imageDataOffset for offset in offsets]

            dataList = [EblcIndexSubTable.compile(self, ttFont)]
            dataList += [
                struct.pack(dataFormat, offsetValue) for offsetValue in offsetArray
            ]
            # Take care of any padding issues. Only occurs in format 3.
            if offsetDataSize * len(offsetArray) % 4 != 0:
                dataList.append(struct.pack(dataFormat, 0))
            return bytesjoin(dataList)

    return OffsetArrayIndexSubTableMixin


# A Mixin for functionality shared between the different kinds
# of fixed sized data handling. Both kinds have big metrics so
# that kind of special processing is also handled in this mixin.
class FixedSizeIndexSubTableMixin(object):
    def writeMetrics(self, writer, ttFont):
        writer.simpletag("imageSize", value=self.imageSize)
        writer.newline()
        self.metrics.toXML(writer, ttFont)

    def readMetrics(self, name, attrs, content, ttFont):
        for element in content:
            if not isinstance(element, tuple):
                continue
            name, attrs, content = element
            if name == "imageSize":
                self.imageSize = safeEval(attrs["value"])
            elif name == BigGlyphMetrics.__name__:
                self.metrics = BigGlyphMetrics()
                self.metrics.fromXML(name, attrs, content, ttFont)
            elif name == SmallGlyphMetrics.__name__:
                log.warning(
                    "SmallGlyphMetrics being ignored in format %d.", self.indexFormat
                )

    def padBitmapData(self, data):
        # Make sure that the data isn't bigger than the fixed size.
        assert len(data) <= self.imageSize, (
            "Data in indexSubTable format %d must be less than the fixed size."
            % self.indexFormat
        )
        # Pad the data so that it matches the fixed size.
        pad = (self.imageSize - len(data)) * b"\0"
        return data + pad


class eblc_index_sub_table_1(
    _createOffsetArrayIndexSubTableMixin("L"), EblcIndexSubTable
):
    pass


class eblc_index_sub_table_2(FixedSizeIndexSubTableMixin, EblcIndexSubTable):
    def decompile(self):
        (self.imageSize,) = struct.unpack(">L", self.data[:4])
        self.metrics = BigGlyphMetrics()
        sstruct.unpack2(bigGlyphMetricsFormat, self.data[4:], self.metrics)
        glyphIds = list(range(self.firstGlyphIndex, self.lastGlyphIndex + 1))
        offsets = [
            self.imageSize * i + self.imageDataOffset for i in range(len(glyphIds) + 1)
        ]
        self.locations = list(zip(offsets, offsets[1:]))
        self.names = list(map(self.ttFont.getGlyphName, glyphIds))
        del self.data, self.ttFont

    def compile(self, ttFont):
        glyphIds = list(map(ttFont.getGlyphID, self.names))
        # Make sure all the ids are consecutive. This is required by Format 2.
        assert glyphIds == list(
            range(self.firstGlyphIndex, self.lastGlyphIndex + 1)
        ), "Format 2 ids must be consecutive."
        self.imageDataOffset = min(next(iter(zip(*self.locations))))

        dataList = [EblcIndexSubTable.compile(self, ttFont)]
        dataList.append(struct.pack(">L", self.imageSize))
        dataList.append(sstruct.pack(bigGlyphMetricsFormat, self.metrics))
        return bytesjoin(dataList)


class eblc_index_sub_table_3(
    _createOffsetArrayIndexSubTableMixin("H"), EblcIndexSubTable
):
    pass


class eblc_index_sub_table_4(EblcIndexSubTable):
    def decompile(self):
        (numGlyphs,) = struct.unpack(">L", self.data[:4])
        data = self.data[4:]
        indexingOffsets = [
            glyphIndex * codeOffsetPairSize for glyphIndex in range(numGlyphs + 2)
        ]
        indexingLocations = zip(indexingOffsets, indexingOffsets[1:])
        glyphArray = [
            struct.unpack(codeOffsetPairFormat, data[slice(*loc)])
            for loc in indexingLocations
        ]
        glyphIds, offsets = list(map(list, zip(*glyphArray)))
        # There are one too many glyph ids. Get rid of the last one.
        glyphIds.pop()

        offsets = [offset + self.imageDataOffset for offset in offsets]
        self.locations = list(zip(offsets, offsets[1:]))
        self.names = list(map(self.ttFont.getGlyphName, glyphIds))
        del self.data, self.ttFont

    def compile(self, ttFont):
        # First make sure that all the data lines up properly. Format 4
        # must have all its data lined up consecutively. If not this will fail.
        for curLoc, nxtLoc in zip(self.locations, self.locations[1:]):
            assert (
                curLoc[1] == nxtLoc[0]
            ), "Data must be consecutive in indexSubTable format 4"

        offsets = list(self.locations[0]) + [loc[1] for loc in self.locations[1:]]
        # Image data offset must be less than or equal to the minimum of locations.
        # Resetting this offset may change the value for round tripping but is safer
        # and allows imageDataOffset to not be required to be in the XML version.
        self.imageDataOffset = min(offsets)
        offsets = [offset - self.imageDataOffset for offset in offsets]
        glyphIds = list(map(ttFont.getGlyphID, self.names))
        # Create an iterator over the ids plus a padding value.
        idsPlusPad = list(itertools.chain(glyphIds, [0]))

        dataList = [EblcIndexSubTable.compile(self, ttFont)]
        dataList.append(struct.pack(">L", len(glyphIds)))
        tmp = [
            struct.pack(codeOffsetPairFormat, *cop) for cop in zip(idsPlusPad, offsets)
        ]
        dataList += tmp
        data = bytesjoin(dataList)
        return data


class eblc_index_sub_table_5(FixedSizeIndexSubTableMixin, EblcIndexSubTable):
    def decompile(self):
        self.origDataLen = 0
        (self.imageSize,) = struct.unpack(">L", self.data[:4])
        data = self.data[4:]
        self.metrics, data = sstruct.unpack2(
            bigGlyphMetricsFormat, data, BigGlyphMetrics()
        )
        (numGlyphs,) = struct.unpack(">L", data[:4])
        data = data[4:]
        glyphIds = [
            struct.unpack(">H", data[2 * i : 2 * (i + 1)])[0] for i in range(numGlyphs)
        ]

        offsets = [
            self.imageSize * i + self.imageDataOffset for i in range(len(glyphIds) + 1)
        ]
        self.locations = list(zip(offsets, offsets[1:]))
        self.names = list(map(self.ttFont.getGlyphName, glyphIds))
        del self.data, self.ttFont

    def compile(self, ttFont):
        self.imageDataOffset = min(next(iter(zip(*self.locations))))
        dataList = [EblcIndexSubTable.compile(self, ttFont)]
        dataList.append(struct.pack(">L", self.imageSize))
        dataList.append(sstruct.pack(bigGlyphMetricsFormat, self.metrics))
        glyphIds = list(map(ttFont.getGlyphID, self.names))
        dataList.append(struct.pack(">L", len(glyphIds)))
        dataList += [struct.pack(">H", curId) for curId in glyphIds]
        if len(glyphIds) % 2 == 1:
            dataList.append(struct.pack(">H", 0))
        return bytesjoin(dataList)


# Dictionary of indexFormat to the class representing that format.
eblc_sub_table_classes = {
    1: eblc_index_sub_table_1,
    2: eblc_index_sub_table_2,
    3: eblc_index_sub_table_3,
    4: eblc_index_sub_table_4,
    5: eblc_index_sub_table_5,
}

# === NexusCore/openenv\Lib\site-packages\openai\resources\beta\threads\messages.py ===
# File generated from our OpenAPI spec by Stainless. See CONTRIBUTING.md for details.

from __future__ import annotations

import typing_extensions
from typing import Union, Iterable, Optional
from typing_extensions import Literal

import httpx

from .... import _legacy_response
from ...._types import NOT_GIVEN, Body, Query, Headers, NotGiven
from ...._utils import maybe_transform, async_maybe_transform
from ...._compat import cached_property
from ...._resource import SyncAPIResource, AsyncAPIResource
from ...._response import to_streamed_response_wrapper, async_to_streamed_response_wrapper
from ....pagination import SyncCursorPage, AsyncCursorPage
from ...._base_client import (
    AsyncPaginator,
    make_request_options,
)
from ....types.beta.threads import message_list_params, message_create_params, message_update_params
from ....types.beta.threads.message import Message
from ....types.shared_params.metadata import Metadata
from ....types.beta.threads.message_deleted import MessageDeleted
from ....types.beta.threads.message_content_part_param import MessageContentPartParam

__all__ = ["Messages", "AsyncMessages"]


class Messages(SyncAPIResource):
    @cached_property
    def with_raw_response(self) -> MessagesWithRawResponse:
        """
        This property can be used as a prefix for any HTTP method call to return
        the raw response object instead of the parsed content.

        For more information, see https://www.github.com/openai/openai-python#accessing-raw-response-data-eg-headers
        """
        return MessagesWithRawResponse(self)

    @cached_property
    def with_streaming_response(self) -> MessagesWithStreamingResponse:
        """
        An alternative to `.with_raw_response` that doesn't eagerly read the response body.

        For more information, see https://www.github.com/openai/openai-python#with_streaming_response
        """
        return MessagesWithStreamingResponse(self)

    @typing_extensions.deprecated("The Assistants API is deprecated in favor of the Responses API")
    def create(
        self,
        thread_id: str,
        *,
        content: Union[str, Iterable[MessageContentPartParam]],
        role: Literal["user", "assistant"],
        attachments: Optional[Iterable[message_create_params.Attachment]] | NotGiven = NOT_GIVEN,
        metadata: Optional[Metadata] | NotGiven = NOT_GIVEN,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> Message:
        """
        Create a message.

        Args:
          content: The text contents of the message.

          role:
              The role of the entity that is creating the message. Allowed values include:

              - `user`: Indicates the message is sent by an actual user and should be used in
                most cases to represent user-generated messages.
              - `assistant`: Indicates the message is generated by the assistant. Use this
                value to insert messages from the assistant into the conversation.

          attachments: A list of files attached to the message, and the tools they should be added to.

          metadata: Set of 16 key-value pairs that can be attached to an object. This can be useful
              for storing additional information about the object in a structured format, and
              querying for objects via API or the dashboard.

              Keys are strings with a maximum length of 64 characters. Values are strings with
              a maximum length of 512 characters.

          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request, in seconds
        """
        if not thread_id:
            raise ValueError(f"Expected a non-empty value for `thread_id` but received {thread_id!r}")
        extra_headers = {"OpenAI-Beta": "assistants=v2", **(extra_headers or {})}
        return self._post(
            f"/threads/{thread_id}/messages",
            body=maybe_transform(
                {
                    "content": content,
                    "role": role,
                    "attachments": attachments,
                    "metadata": metadata,
                },
                message_create_params.MessageCreateParams,
            ),
            options=make_request_options(
                extra_headers=extra_headers, extra_query=extra_query, extra_body=extra_body, timeout=timeout
            ),
            cast_to=Message,
        )

    @typing_extensions.deprecated("The Assistants API is deprecated in favor of the Responses API")
    def retrieve(
        self,
        message_id: str,
        *,
        thread_id: str,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> Message:
        """
        Retrieve a message.

        Args:
          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request, in seconds
        """
        if not thread_id:
            raise ValueError(f"Expected a non-empty value for `thread_id` but received {thread_id!r}")
        if not message_id:
            raise ValueError(f"Expected a non-empty value for `message_id` but received {message_id!r}")
        extra_headers = {"OpenAI-Beta": "assistants=v2", **(extra_headers or {})}
        return self._get(
            f"/threads/{thread_id}/messages/{message_id}",
            options=make_request_options(
                extra_headers=extra_headers, extra_query=extra_query, extra_body=extra_body, timeout=timeout
            ),
            cast_to=Message,
        )

    @typing_extensions.deprecated("The Assistants API is deprecated in favor of the Responses API")
    def update(
        self,
        message_id: str,
        *,
        thread_id: str,
        metadata: Optional[Metadata] | NotGiven = NOT_GIVEN,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> Message:
        """
        Modifies a message.

        Args:
          metadata: Set of 16 key-value pairs that can be attached to an object. This can be useful
              for storing additional information about the object in a structured format, and
              querying for objects via API or the dashboard.

              Keys are strings with a maximum length of 64 characters. Values are strings with
              a maximum length of 512 characters.

          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request, in seconds
        """
        if not thread_id:
            raise ValueError(f"Expected a non-empty value for `thread_id` but received {thread_id!r}")
        if not message_id:
            raise ValueError(f"Expected a non-empty value for `message_id` but received {message_id!r}")
        extra_headers = {"OpenAI-Beta": "assistants=v2", **(extra_headers or {})}
        return self._post(
            f"/threads/{thread_id}/messages/{message_id}",
            body=maybe_transform({"metadata": metadata}, message_update_params.MessageUpdateParams),
            options=make_request_options(
                extra_headers=extra_headers, extra_query=extra_query, extra_body=extra_body, timeout=timeout
            ),
            cast_to=Message,
        )

    @typing_extensions.deprecated("The Assistants API is deprecated in favor of the Responses API")
    def list(
        self,
        thread_id: str,
        *,
        after: str | NotGiven = NOT_GIVEN,
        before: str | NotGiven = NOT_GIVEN,
        limit: int | NotGiven = NOT_GIVEN,
        order: Literal["asc", "desc"] | NotGiven = NOT_GIVEN,
        run_id: str | NotGiven = NOT_GIVEN,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> SyncCursorPage[Message]:
        """
        Returns a list of messages for a given thread.

        Args:
          after: A cursor for use in pagination. `after` is an object ID that defines your place
              in the list. For instance, if you make a list request and receive 100 objects,
              ending with obj_foo, your subsequent call can include after=obj_foo in order to
              fetch the next page of the list.

          before: A cursor for use in pagination. `before` is an object ID that defines your place
              in the list. For instance, if you make a list request and receive 100 objects,
              starting with obj_foo, your subsequent call can include before=obj_foo in order
              to fetch the previous page of the list.

          limit: A limit on the number of objects to be returned. Limit can range between 1 and
              100, and the default is 20.

          order: Sort order by the `created_at` timestamp of the objects. `asc` for ascending
              order and `desc` for descending order.

          run_id: Filter messages by the run ID that generated them.

          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request, in seconds
        """
        if not thread_id:
            raise ValueError(f"Expected a non-empty value for `thread_id` but received {thread_id!r}")
        extra_headers = {"OpenAI-Beta": "assistants=v2", **(extra_headers or {})}
        return self._get_api_list(
            f"/threads/{thread_id}/messages",
            page=SyncCursorPage[Message],
            options=make_request_options(
                extra_headers=extra_headers,
                extra_query=extra_query,
                extra_body=extra_body,
                timeout=timeout,
                query=maybe_transform(
                    {
                        "after": after,
                        "before": before,
                        "limit": limit,
                        "order": order,
                        "run_id": run_id,
                    },
                    message_list_params.MessageListParams,
                ),
            ),
            model=Message,
        )

    @typing_extensions.deprecated("The Assistants API is deprecated in favor of the Responses API")
    def delete(
        self,
        message_id: str,
        *,
        thread_id: str,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> MessageDeleted:
        """
        Deletes a message.

        Args:
          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request, in seconds
        """
        if not thread_id:
            raise ValueError(f"Expected a non-empty value for `thread_id` but received {thread_id!r}")
        if not message_id:
            raise ValueError(f"Expected a non-empty value for `message_id` but received {message_id!r}")
        extra_headers = {"OpenAI-Beta": "assistants=v2", **(extra_headers or {})}
        return self._delete(
            f"/threads/{thread_id}/messages/{message_id}",
            options=make_request_options(
                extra_headers=extra_headers, extra_query=extra_query, extra_body=extra_body, timeout=timeout
            ),
            cast_to=MessageDeleted,
        )


class AsyncMessages(AsyncAPIResource):
    @cached_property
    def with_raw_response(self) -> AsyncMessagesWithRawResponse:
        """
        This property can be used as a prefix for any HTTP method call to return
        the raw response object instead of the parsed content.

        For more information, see https://www.github.com/openai/openai-python#accessing-raw-response-data-eg-headers
        """
        return AsyncMessagesWithRawResponse(self)

    @cached_property
    def with_streaming_response(self) -> AsyncMessagesWithStreamingResponse:
        """
        An alternative to `.with_raw_response` that doesn't eagerly read the response body.

        For more information, see https://www.github.com/openai/openai-python#with_streaming_response
        """
        return AsyncMessagesWithStreamingResponse(self)

    @typing_extensions.deprecated("The Assistants API is deprecated in favor of the Responses API")
    async def create(
        self,
        thread_id: str,
        *,
        content: Union[str, Iterable[MessageContentPartParam]],
        role: Literal["user", "assistant"],
        attachments: Optional[Iterable[message_create_params.Attachment]] | NotGiven = NOT_GIVEN,
        metadata: Optional[Metadata] | NotGiven = NOT_GIVEN,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> Message:
        """
        Create a message.

        Args:
          content: The text contents of the message.

          role:
              The role of the entity that is creating the message. Allowed values include:

              - `user`: Indicates the message is sent by an actual user and should be used in
                most cases to represent user-generated messages.
              - `assistant`: Indicates the message is generated by the assistant. Use this
                value to insert messages from the assistant into the conversation.

          attachments: A list of files attached to the message, and the tools they should be added to.

          metadata: Set of 16 key-value pairs that can be attached to an object. This can be useful
              for storing additional information about the object in a structured format, and
              querying for objects via API or the dashboard.

              Keys are strings with a maximum length of 64 characters. Values are strings with
              a maximum length of 512 characters.

          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request, in seconds
        """
        if not thread_id:
            raise ValueError(f"Expected a non-empty value for `thread_id` but received {thread_id!r}")
        extra_headers = {"OpenAI-Beta": "assistants=v2", **(extra_headers or {})}
        return await self._post(
            f"/threads/{thread_id}/messages",
            body=await async_maybe_transform(
                {
                    "content": content,
                    "role": role,
                    "attachments": attachments,
                    "metadata": metadata,
                },
                message_create_params.MessageCreateParams,
            ),
            options=make_request_options(
                extra_headers=extra_headers, extra_query=extra_query, extra_body=extra_body, timeout=timeout
            ),
            cast_to=Message,
        )

    @typing_extensions.deprecated("The Assistants API is deprecated in favor of the Responses API")
    async def retrieve(
        self,
        message_id: str,
        *,
        thread_id: str,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> Message:
        """
        Retrieve a message.

        Args:
          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request, in seconds
        """
        if not thread_id:
            raise ValueError(f"Expected a non-empty value for `thread_id` but received {thread_id!r}")
        if not message_id:
            raise ValueError(f"Expected a non-empty value for `message_id` but received {message_id!r}")
        extra_headers = {"OpenAI-Beta": "assistants=v2", **(extra_headers or {})}
        return await self._get(
            f"/threads/{thread_id}/messages/{message_id}",
            options=make_request_options(
                extra_headers=extra_headers, extra_query=extra_query, extra_body=extra_body, timeout=timeout
            ),
            cast_to=Message,
        )

    @typing_extensions.deprecated("The Assistants API is deprecated in favor of the Responses API")
    async def update(
        self,
        message_id: str,
        *,
        thread_id: str,
        metadata: Optional[Metadata] | NotGiven = NOT_GIVEN,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> Message:
        """
        Modifies a message.

        Args:
          metadata: Set of 16 key-value pairs that can be attached to an object. This can be useful
              for storing additional information about the object in a structured format, and
              querying for objects via API or the dashboard.

              Keys are strings with a maximum length of 64 characters. Values are strings with
              a maximum length of 512 characters.

          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request, in seconds
        """
        if not thread_id:
            raise ValueError(f"Expected a non-empty value for `thread_id` but received {thread_id!r}")
        if not message_id:
            raise ValueError(f"Expected a non-empty value for `message_id` but received {message_id!r}")
        extra_headers = {"OpenAI-Beta": "assistants=v2", **(extra_headers or {})}
        return await self._post(
            f"/threads/{thread_id}/messages/{message_id}",
            body=await async_maybe_transform({"metadata": metadata}, message_update_params.MessageUpdateParams),
            options=make_request_options(
                extra_headers=extra_headers, extra_query=extra_query, extra_body=extra_body, timeout=timeout
            ),
            cast_to=Message,
        )

    @typing_extensions.deprecated("The Assistants API is deprecated in favor of the Responses API")
    def list(
        self,
        thread_id: str,
        *,
        after: str | NotGiven = NOT_GIVEN,
        before: str | NotGiven = NOT_GIVEN,
        limit: int | NotGiven = NOT_GIVEN,
        order: Literal["asc", "desc"] | NotGiven = NOT_GIVEN,
        run_id: str | NotGiven = NOT_GIVEN,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> AsyncPaginator[Message, AsyncCursorPage[Message]]:
        """
        Returns a list of messages for a given thread.

        Args:
          after: A cursor for use in pagination. `after` is an object ID that defines your place
              in the list. For instance, if you make a list request and receive 100 objects,
              ending with obj_foo, your subsequent call can include after=obj_foo in order to
              fetch the next page of the list.

          before: A cursor for use in pagination. `before` is an object ID that defines your place
              in the list. For instance, if you make a list request and receive 100 objects,
              starting with obj_foo, your subsequent call can include before=obj_foo in order
              to fetch the previous page of the list.

          limit: A limit on the number of objects to be returned. Limit can range between 1 and
              100, and the default is 20.

          order: Sort order by the `created_at` timestamp of the objects. `asc` for ascending
              order and `desc` for descending order.

          run_id: Filter messages by the run ID that generated them.

          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request, in seconds
        """
        if not thread_id:
            raise ValueError(f"Expected a non-empty value for `thread_id` but received {thread_id!r}")
        extra_headers = {"OpenAI-Beta": "assistants=v2", **(extra_headers or {})}
        return self._get_api_list(
            f"/threads/{thread_id}/messages",
            page=AsyncCursorPage[Message],
            options=make_request_options(
                extra_headers=extra_headers,
                extra_query=extra_query,
                extra_body=extra_body,
                timeout=timeout,
                query=maybe_transform(
                    {
                        "after": after,
                        "before": before,
                        "limit": limit,
                        "order": order,
                        "run_id": run_id,
                    },
                    message_list_params.MessageListParams,
                ),
            ),
            model=Message,
        )

    @typing_extensions.deprecated("The Assistants API is deprecated in favor of the Responses API")
    async def delete(
        self,
        message_id: str,
        *,
        thread_id: str,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> MessageDeleted:
        """
        Deletes a message.

        Args:
          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request, in seconds
        """
        if not thread_id:
            raise ValueError(f"Expected a non-empty value for `thread_id` but received {thread_id!r}")
        if not message_id:
            raise ValueError(f"Expected a non-empty value for `message_id` but received {message_id!r}")
        extra_headers = {"OpenAI-Beta": "assistants=v2", **(extra_headers or {})}
        return await self._delete(
            f"/threads/{thread_id}/messages/{message_id}",
            options=make_request_options(
                extra_headers=extra_headers, extra_query=extra_query, extra_body=extra_body, timeout=timeout
            ),
            cast_to=MessageDeleted,
        )


class MessagesWithRawResponse:
    def __init__(self, messages: Messages) -> None:
        self._messages = messages

        self.create = (  # pyright: ignore[reportDeprecated]
            _legacy_response.to_raw_response_wrapper(
                messages.create  # pyright: ignore[reportDeprecated],
            )
        )
        self.retrieve = (  # pyright: ignore[reportDeprecated]
            _legacy_response.to_raw_response_wrapper(
                messages.retrieve  # pyright: ignore[reportDeprecated],
            )
        )
        self.update = (  # pyright: ignore[reportDeprecated]
            _legacy_response.to_raw_response_wrapper(
                messages.update  # pyright: ignore[reportDeprecated],
            )
        )
        self.list = (  # pyright: ignore[reportDeprecated]
            _legacy_response.to_raw_response_wrapper(
                messages.list  # pyright: ignore[reportDeprecated],
            )
        )
        self.delete = (  # pyright: ignore[reportDeprecated]
            _legacy_response.to_raw_response_wrapper(
                messages.delete  # pyright: ignore[reportDeprecated],
            )
        )


class AsyncMessagesWithRawResponse:
    def __init__(self, messages: AsyncMessages) -> None:
        self._messages = messages

        self.create = (  # pyright: ignore[reportDeprecated]
            _legacy_response.async_to_raw_response_wrapper(
                messages.create  # pyright: ignore[reportDeprecated],
            )
        )
        self.retrieve = (  # pyright: ignore[reportDeprecated]
            _legacy_response.async_to_raw_response_wrapper(
                messages.retrieve  # pyright: ignore[reportDeprecated],
            )
        )
        self.update = (  # pyright: ignore[reportDeprecated]
            _legacy_response.async_to_raw_response_wrapper(
                messages.update  # pyright: ignore[reportDeprecated],
            )
        )
        self.list = (  # pyright: ignore[reportDeprecated]
            _legacy_response.async_to_raw_response_wrapper(
                messages.list  # pyright: ignore[reportDeprecated],
            )
        )
        self.delete = (  # pyright: ignore[reportDeprecated]
            _legacy_response.async_to_raw_response_wrapper(
                messages.delete  # pyright: ignore[reportDeprecated],
            )
        )


class MessagesWithStreamingResponse:
    def __init__(self, messages: Messages) -> None:
        self._messages = messages

        self.create = (  # pyright: ignore[reportDeprecated]
            to_streamed_response_wrapper(
                messages.create  # pyright: ignore[reportDeprecated],
            )
        )
        self.retrieve = (  # pyright: ignore[reportDeprecated]
            to_streamed_response_wrapper(
                messages.retrieve  # pyright: ignore[reportDeprecated],
            )
        )
        self.update = (  # pyright: ignore[reportDeprecated]
            to_streamed_response_wrapper(
                messages.update  # pyright: ignore[reportDeprecated],
            )
        )
        self.list = (  # pyright: ignore[reportDeprecated]
            to_streamed_response_wrapper(
                messages.list  # pyright: ignore[reportDeprecated],
            )
        )
        self.delete = (  # pyright: ignore[reportDeprecated]
            to_streamed_response_wrapper(
                messages.delete  # pyright: ignore[reportDeprecated],
            )
        )


class AsyncMessagesWithStreamingResponse:
    def __init__(self, messages: AsyncMessages) -> None:
        self._messages = messages

        self.create = (  # pyright: ignore[reportDeprecated]
            async_to_streamed_response_wrapper(
                messages.create  # pyright: ignore[reportDeprecated],
            )
        )
        self.retrieve = (  # pyright: ignore[reportDeprecated]
            async_to_streamed_response_wrapper(
                messages.retrieve  # pyright: ignore[reportDeprecated],
            )
        )
        self.update = (  # pyright: ignore[reportDeprecated]
            async_to_streamed_response_wrapper(
                messages.update  # pyright: ignore[reportDeprecated],
            )
        )
        self.list = (  # pyright: ignore[reportDeprecated]
            async_to_streamed_response_wrapper(
                messages.list  # pyright: ignore[reportDeprecated],
            )
        )
        self.delete = (  # pyright: ignore[reportDeprecated]
            async_to_streamed_response_wrapper(
                messages.delete  # pyright: ignore[reportDeprecated],
            )
        )