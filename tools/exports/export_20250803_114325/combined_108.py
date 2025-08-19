
# === NexusCore/openenv\Lib\site-packages\debugpy\_vendored\pydevd\pydevd_attach_to_process\winappdbg\util.py ===
#!~/.wine/drive_c/Python25/python.exe
# -*- coding: utf-8 -*-

# Copyright (c) 2009-2014, Mario Vilas
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#     * Redistributions of source code must retain the above copyright notice,
#       this list of conditions and the following disclaimer.
#     * Redistributions in binary form must reproduce the above copyright
#       notice,this list of conditions and the following disclaimer in the
#       documentation and/or other materials provided with the distribution.
#     * Neither the name of the copyright holder nor the names of its
#       contributors may be used to endorse or promote products derived from
#       this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

"""
Miscellaneous utility classes and functions.

@group Helpers:
    PathOperations,
    MemoryAddresses,
    CustomAddressIterator,
    DataAddressIterator,
    ImageAddressIterator,
    MappedAddressIterator,
    ExecutableAddressIterator,
    ReadableAddressIterator,
    WriteableAddressIterator,
    ExecutableAndWriteableAddressIterator,
    DebugRegister,
    Regenerator,
    BannerHelpFormatter,
    StaticClass,
    classproperty
"""

__revision__ = "$Id$"

__all__ = [
    # Filename and pathname manipulation
    "PathOperations",
    # Memory address operations
    "MemoryAddresses",
    "CustomAddressIterator",
    "DataAddressIterator",
    "ImageAddressIterator",
    "MappedAddressIterator",
    "ExecutableAddressIterator",
    "ReadableAddressIterator",
    "WriteableAddressIterator",
    "ExecutableAndWriteableAddressIterator",
    # Debug registers manipulation
    "DebugRegister",
    # Miscellaneous
    "Regenerator",
]

import sys
import os
import ctypes
import optparse

from winappdbg import win32
from winappdbg import compat

# ==============================================================================


class classproperty(property):
    """
    Class property method.

    Only works for getting properties, if you set them
    the symbol gets overwritten in the class namespace.

    Inspired on: U{http://stackoverflow.com/a/7864317/426293}
    """

    def __init__(self, fget=None, fset=None, fdel=None, doc=""):
        if fset is not None or fdel is not None:
            raise NotImplementedError()
        super(classproperty, self).__init__(fget=classmethod(fget), doc=doc)

    def __get__(self, cls, owner):
        return self.fget.__get__(None, owner)()


class BannerHelpFormatter(optparse.IndentedHelpFormatter):
    "Just a small tweak to optparse to be able to print a banner."

    def __init__(self, banner, *argv, **argd):
        self.banner = banner
        optparse.IndentedHelpFormatter.__init__(self, *argv, **argd)

    def format_usage(self, usage):
        msg = optparse.IndentedHelpFormatter.format_usage(self, usage)
        return "%s\n%s" % (self.banner, msg)


# See Process.generate_memory_snapshot()
class Regenerator(object):
    """
    Calls a generator and iterates it. When it's finished iterating, the
    generator is called again. This allows you to iterate a generator more
    than once (well, sort of).
    """

    def __init__(self, g_function, *v_args, **d_args):
        """
        @type  g_function: function
        @param g_function: Function that when called returns a generator.

        @type  v_args: tuple
        @param v_args: Variable arguments to pass to the generator function.

        @type  d_args: dict
        @param d_args: Variable arguments to pass to the generator function.
        """
        self.__g_function = g_function
        self.__v_args = v_args
        self.__d_args = d_args
        self.__g_object = None

    def __iter__(self):
        "x.__iter__() <==> iter(x)"
        return self

    def next(self):
        "x.next() -> the next value, or raise StopIteration"
        if self.__g_object is None:
            self.__g_object = self.__g_function(*self.__v_args, **self.__d_args)
        try:
            return self.__g_object.next()
        except StopIteration:
            self.__g_object = None
            raise


class StaticClass(object):
    def __new__(cls, *argv, **argd):
        "Don't try to instance this class, just use the static methods."
        raise NotImplementedError("Cannot instance static class %s" % cls.__name__)


# ==============================================================================


class PathOperations(StaticClass):
    """
    Static methods for filename and pathname manipulation.
    """

    @staticmethod
    def path_is_relative(path):
        """
        @see: L{path_is_absolute}

        @type  path: str
        @param path: Absolute or relative path.

        @rtype:  bool
        @return: C{True} if the path is relative, C{False} if it's absolute.
        """
        return win32.PathIsRelative(path)

    @staticmethod
    def path_is_absolute(path):
        """
        @see: L{path_is_relative}

        @type  path: str
        @param path: Absolute or relative path.

        @rtype:  bool
        @return: C{True} if the path is absolute, C{False} if it's relative.
        """
        return not win32.PathIsRelative(path)

    @staticmethod
    def make_relative(path, current=None):
        """
        @type  path: str
        @param path: Absolute path.

        @type  current: str
        @param current: (Optional) Path to the current directory.

        @rtype:  str
        @return: Relative path.

        @raise WindowsError: It's impossible to make the path relative.
            This happens when the path and the current path are not on the
            same disk drive or network share.
        """
        return win32.PathRelativePathTo(pszFrom=current, pszTo=path)

    @staticmethod
    def make_absolute(path):
        """
        @type  path: str
        @param path: Relative path.

        @rtype:  str
        @return: Absolute path.
        """
        return win32.GetFullPathName(path)[0]

    @staticmethod
    def split_extension(pathname):
        """
        @type  pathname: str
        @param pathname: Absolute path.

        @rtype:  tuple( str, str )
        @return:
            Tuple containing the file and extension components of the filename.
        """
        filepart = win32.PathRemoveExtension(pathname)
        extpart = win32.PathFindExtension(pathname)
        return (filepart, extpart)

    @staticmethod
    def split_filename(pathname):
        """
        @type  pathname: str
        @param pathname: Absolute path.

        @rtype:  tuple( str, str )
        @return: Tuple containing the path to the file and the base filename.
        """
        filepart = win32.PathFindFileName(pathname)
        pathpart = win32.PathRemoveFileSpec(pathname)
        return (pathpart, filepart)

    @staticmethod
    def split_path(path):
        """
        @see: L{join_path}

        @type  path: str
        @param path: Absolute or relative path.

        @rtype:  list( str... )
        @return: List of path components.
        """
        components = list()
        while path:
            next = win32.PathFindNextComponent(path)
            if next:
                prev = path[: -len(next)]
                components.append(prev)
            path = next
        return components

    @staticmethod
    def join_path(*components):
        """
        @see: L{split_path}

        @type  components: tuple( str... )
        @param components: Path components.

        @rtype:  str
        @return: Absolute or relative path.
        """
        if components:
            path = components[0]
            for next in components[1:]:
                path = win32.PathAppend(path, next)
        else:
            path = ""
        return path

    @staticmethod
    def native_to_win32_pathname(name):
        """
        @type  name: str
        @param name: Native (NT) absolute pathname.

        @rtype:  str
        @return: Win32 absolute pathname.
        """
        # XXX TODO
        # There are probably some native paths that
        # won't be converted by this naive approach.
        if name.startswith("\\"):
            if name.startswith("\\??\\"):
                name = name[4:]
            elif name.startswith("\\SystemRoot\\"):
                system_root_path = os.environ["SYSTEMROOT"]
                if system_root_path.endswith("\\"):
                    system_root_path = system_root_path[:-1]
                name = system_root_path + name[11:]
            else:
                for drive_number in compat.xrange(ord("A"), ord("Z") + 1):
                    drive_letter = "%c:" % drive_number
                    try:
                        device_native_path = win32.QueryDosDevice(drive_letter)
                    except WindowsError:
                        e = sys.exc_info()[1]
                        if e.winerror in (win32.ERROR_FILE_NOT_FOUND, win32.ERROR_PATH_NOT_FOUND):
                            continue
                        raise
                    if not device_native_path.endswith("\\"):
                        device_native_path += "\\"
                    if name.startswith(device_native_path):
                        name = drive_letter + "\\" + name[len(device_native_path) :]
                        break
        return name

    @staticmethod
    def pathname_to_filename(pathname):
        """
        Equivalent to: C{PathOperations.split_filename(pathname)[0]}

        @note: This function is preserved for backwards compatibility with
            WinAppDbg 1.4 and earlier. It may be removed in future versions.

        @type  pathname: str
        @param pathname: Absolute path to a file.

        @rtype:  str
        @return: Filename component of the path.
        """
        return win32.PathFindFileName(pathname)


# ==============================================================================


class MemoryAddresses(StaticClass):
    """
    Class to manipulate memory addresses.

    @type pageSize: int
    @cvar pageSize: Page size in bytes. Defaults to 0x1000 but it's
        automatically updated on runtime when importing the module.
    """

    @classproperty
    def pageSize(cls):
        """
        Try to get the pageSize value on runtime.
        """
        try:
            try:
                pageSize = win32.GetSystemInfo().dwPageSize
            except WindowsError:
                pageSize = 0x1000
        except NameError:
            pageSize = 0x1000
        cls.pageSize = pageSize  # now this function won't be called again
        return pageSize

    @classmethod
    def align_address_to_page_start(cls, address):
        """
        Align the given address to the start of the page it occupies.

        @type  address: int
        @param address: Memory address.

        @rtype:  int
        @return: Aligned memory address.
        """
        return address - (address % cls.pageSize)

    @classmethod
    def align_address_to_page_end(cls, address):
        """
        Align the given address to the end of the page it occupies.
        That is, to point to the start of the next page.

        @type  address: int
        @param address: Memory address.

        @rtype:  int
        @return: Aligned memory address.
        """
        return address + cls.pageSize - (address % cls.pageSize)

    @classmethod
    def align_address_range(cls, begin, end):
        """
        Align the given address range to the start and end of the page(s) it occupies.

        @type  begin: int
        @param begin: Memory address of the beginning of the buffer.
            Use C{None} for the first legal address in the address space.

        @type  end: int
        @param end: Memory address of the end of the buffer.
            Use C{None} for the last legal address in the address space.

        @rtype:  tuple( int, int )
        @return: Aligned memory addresses.
        """
        if begin is None:
            begin = 0
        if end is None:
            end = win32.LPVOID(-1).value  # XXX HACK
        if end < begin:
            begin, end = end, begin
        begin = cls.align_address_to_page_start(begin)
        if end != cls.align_address_to_page_start(end):
            end = cls.align_address_to_page_end(end)
        return (begin, end)

    @classmethod
    def get_buffer_size_in_pages(cls, address, size):
        """
        Get the number of pages in use by the given buffer.

        @type  address: int
        @param address: Aligned memory address.

        @type  size: int
        @param size: Buffer size.

        @rtype:  int
        @return: Buffer size in number of pages.
        """
        if size < 0:
            size = -size
            address = address - size
        begin, end = cls.align_address_range(address, address + size)
        # XXX FIXME
        # I think this rounding fails at least for address 0xFFFFFFFF size 1
        return int(float(end - begin) / float(cls.pageSize))

    @staticmethod
    def do_ranges_intersect(begin, end, old_begin, old_end):
        """
        Determine if the two given memory address ranges intersect.

        @type  begin: int
        @param begin: Start address of the first range.

        @type  end: int
        @param end: End address of the first range.

        @type  old_begin: int
        @param old_begin: Start address of the second range.

        @type  old_end: int
        @param old_end: End address of the second range.

        @rtype:  bool
        @return: C{True} if the two ranges intersect, C{False} otherwise.
        """
        return (old_begin <= begin < old_end) or (old_begin < end <= old_end) or (begin <= old_begin < end) or (begin < old_end <= end)


# ==============================================================================


def CustomAddressIterator(memory_map, condition):
    """
    Generator function that iterates through a memory map, filtering memory
    region blocks by any given condition.

    @type  memory_map: list( L{win32.MemoryBasicInformation} )
    @param memory_map: List of memory region information objects.
        Returned by L{Process.get_memory_map}.

    @type  condition: function
    @param condition: Callback function that returns C{True} if the memory
        block should be returned, or C{False} if it should be filtered.

    @rtype:  generator of L{win32.MemoryBasicInformation}
    @return: Generator object to iterate memory blocks.
    """
    for mbi in memory_map:
        if condition(mbi):
            address = mbi.BaseAddress
            max_addr = address + mbi.RegionSize
            while address < max_addr:
                yield address
                address = address + 1


def DataAddressIterator(memory_map):
    """
    Generator function that iterates through a memory map, returning only those
    memory blocks that contain data.

    @type  memory_map: list( L{win32.MemoryBasicInformation} )
    @param memory_map: List of memory region information objects.
        Returned by L{Process.get_memory_map}.

    @rtype:  generator of L{win32.MemoryBasicInformation}
    @return: Generator object to iterate memory blocks.
    """
    return CustomAddressIterator(memory_map, win32.MemoryBasicInformation.has_content)


def ImageAddressIterator(memory_map):
    """
    Generator function that iterates through a memory map, returning only those
    memory blocks that belong to executable images.

    @type  memory_map: list( L{win32.MemoryBasicInformation} )
    @param memory_map: List of memory region information objects.
        Returned by L{Process.get_memory_map}.

    @rtype:  generator of L{win32.MemoryBasicInformation}
    @return: Generator object to iterate memory blocks.
    """
    return CustomAddressIterator(memory_map, win32.MemoryBasicInformation.is_image)


def MappedAddressIterator(memory_map):
    """
    Generator function that iterates through a memory map, returning only those
    memory blocks that belong to memory mapped files.

    @type  memory_map: list( L{win32.MemoryBasicInformation} )
    @param memory_map: List of memory region information objects.
        Returned by L{Process.get_memory_map}.

    @rtype:  generator of L{win32.MemoryBasicInformation}
    @return: Generator object to iterate memory blocks.
    """
    return CustomAddressIterator(memory_map, win32.MemoryBasicInformation.is_mapped)


def ReadableAddressIterator(memory_map):
    """
    Generator function that iterates through a memory map, returning only those
    memory blocks that are readable.

    @type  memory_map: list( L{win32.MemoryBasicInformation} )
    @param memory_map: List of memory region information objects.
        Returned by L{Process.get_memory_map}.

    @rtype:  generator of L{win32.MemoryBasicInformation}
    @return: Generator object to iterate memory blocks.
    """
    return CustomAddressIterator(memory_map, win32.MemoryBasicInformation.is_readable)


def WriteableAddressIterator(memory_map):
    """
    Generator function that iterates through a memory map, returning only those
    memory blocks that are writeable.

    @note: Writeable memory is always readable too.

    @type  memory_map: list( L{win32.MemoryBasicInformation} )
    @param memory_map: List of memory region information objects.
        Returned by L{Process.get_memory_map}.

    @rtype:  generator of L{win32.MemoryBasicInformation}
    @return: Generator object to iterate memory blocks.
    """
    return CustomAddressIterator(memory_map, win32.MemoryBasicInformation.is_writeable)


def ExecutableAddressIterator(memory_map):
    """
    Generator function that iterates through a memory map, returning only those
    memory blocks that are executable.

    @note: Executable memory is always readable too.

    @type  memory_map: list( L{win32.MemoryBasicInformation} )
    @param memory_map: List of memory region information objects.
        Returned by L{Process.get_memory_map}.

    @rtype:  generator of L{win32.MemoryBasicInformation}
    @return: Generator object to iterate memory blocks.
    """
    return CustomAddressIterator(memory_map, win32.MemoryBasicInformation.is_executable)


def ExecutableAndWriteableAddressIterator(memory_map):
    """
    Generator function that iterates through a memory map, returning only those
    memory blocks that are executable and writeable.

    @note: The presence of such pages make memory corruption vulnerabilities
        much easier to exploit.

    @type  memory_map: list( L{win32.MemoryBasicInformation} )
    @param memory_map: List of memory region information objects.
        Returned by L{Process.get_memory_map}.

    @rtype:  generator of L{win32.MemoryBasicInformation}
    @return: Generator object to iterate memory blocks.
    """
    return CustomAddressIterator(memory_map, win32.MemoryBasicInformation.is_executable_and_writeable)


# ==============================================================================
try:
    _registerMask = win32.SIZE_T(-1).value
except TypeError:
    if win32.SIZEOF(win32.SIZE_T) == 4:
        _registerMask = 0xFFFFFFFF
    elif win32.SIZEOF(win32.SIZE_T) == 8:
        _registerMask = 0xFFFFFFFFFFFFFFFF
    else:
        raise


class DebugRegister(StaticClass):
    """
    Class to manipulate debug registers.
    Used by L{HardwareBreakpoint}.

    @group Trigger flags used by HardwareBreakpoint:
        BREAK_ON_EXECUTION, BREAK_ON_WRITE, BREAK_ON_ACCESS, BREAK_ON_IO_ACCESS
    @group Size flags used by HardwareBreakpoint:
        WATCH_BYTE, WATCH_WORD, WATCH_DWORD, WATCH_QWORD
    @group Bitwise masks for Dr7:
        enableMask, disableMask, triggerMask, watchMask, clearMask,
        generalDetectMask
    @group Bitwise masks for Dr6:
        hitMask, hitMaskAll, debugAccessMask, singleStepMask, taskSwitchMask,
        clearDr6Mask, clearHitMask
    @group Debug control MSR definitions:
        DebugCtlMSR, LastBranchRecord, BranchTrapFlag, PinControl,
        LastBranchToIP, LastBranchFromIP,
        LastExceptionToIP, LastExceptionFromIP

    @type BREAK_ON_EXECUTION: int
    @cvar BREAK_ON_EXECUTION: Break on execution.

    @type BREAK_ON_WRITE: int
    @cvar BREAK_ON_WRITE: Break on write.

    @type BREAK_ON_ACCESS: int
    @cvar BREAK_ON_ACCESS: Break on read or write.

    @type BREAK_ON_IO_ACCESS: int
    @cvar BREAK_ON_IO_ACCESS: Break on I/O port access.
        Not supported by any hardware.

    @type WATCH_BYTE: int
    @cvar WATCH_BYTE: Watch a byte.

    @type WATCH_WORD: int
    @cvar WATCH_WORD: Watch a word.

    @type WATCH_DWORD: int
    @cvar WATCH_DWORD: Watch a double word.

    @type WATCH_QWORD: int
    @cvar WATCH_QWORD: Watch one quad word.

    @type enableMask: 4-tuple of integers
    @cvar enableMask:
        Enable bit on C{Dr7} for each slot.
        Works as a bitwise-OR mask.

    @type disableMask: 4-tuple of integers
    @cvar disableMask:
        Mask of the enable bit on C{Dr7} for each slot.
        Works as a bitwise-AND mask.

    @type triggerMask: 4-tuple of 2-tuples of integers
    @cvar triggerMask:
        Trigger bits on C{Dr7} for each trigger flag value.
        Each 2-tuple has the bitwise-OR mask and the bitwise-AND mask.

    @type watchMask: 4-tuple of 2-tuples of integers
    @cvar watchMask:
        Watch bits on C{Dr7} for each watch flag value.
        Each 2-tuple has the bitwise-OR mask and the bitwise-AND mask.

    @type clearMask: 4-tuple of integers
    @cvar clearMask:
        Mask of all important bits on C{Dr7} for each slot.
        Works as a bitwise-AND mask.

    @type generalDetectMask: integer
    @cvar generalDetectMask:
        General detect mode bit. It enables the processor to notify the
        debugger when the debugee is trying to access one of the debug
        registers.

    @type hitMask: 4-tuple of integers
    @cvar hitMask:
        Hit bit on C{Dr6} for each slot.
        Works as a bitwise-AND mask.

    @type hitMaskAll: integer
    @cvar hitMaskAll:
        Bitmask for all hit bits in C{Dr6}. Useful to know if at least one
        hardware breakpoint was hit, or to clear the hit bits only.

    @type clearHitMask: integer
    @cvar clearHitMask:
        Bitmask to clear all the hit bits in C{Dr6}.

    @type debugAccessMask: integer
    @cvar debugAccessMask:
        The debugee tried to access a debug register. Needs bit
        L{generalDetectMask} enabled in C{Dr7}.

    @type singleStepMask: integer
    @cvar singleStepMask:
        A single step exception was raised. Needs the trap flag enabled.

    @type taskSwitchMask: integer
    @cvar taskSwitchMask:
        A task switch has occurred. Needs the TSS T-bit set to 1.

    @type clearDr6Mask: integer
    @cvar clearDr6Mask:
        Bitmask to clear all meaningful bits in C{Dr6}.
    """

    BREAK_ON_EXECUTION = 0
    BREAK_ON_WRITE = 1
    BREAK_ON_ACCESS = 3
    BREAK_ON_IO_ACCESS = 2

    WATCH_BYTE = 0
    WATCH_WORD = 1
    WATCH_DWORD = 3
    WATCH_QWORD = 2

    registerMask = _registerMask

    # ------------------------------------------------------------------------------

    ###########################################################################
    # http://en.wikipedia.org/wiki/Debug_register
    #
    # DR7 - Debug control
    #
    # The low-order eight bits of DR7 (0,2,4,6 and 1,3,5,7) selectively enable
    # the four address breakpoint conditions. There are two levels of enabling:
    # the local (0,2,4,6) and global (1,3,5,7) levels. The local enable bits
    # are automatically reset by the processor at every task switch to avoid
    # unwanted breakpoint conditions in the new task. The global enable bits
    # are not reset by a task switch; therefore, they can be used for
    # conditions that are global to all tasks.
    #
    # Bits 16-17 (DR0), 20-21 (DR1), 24-25 (DR2), 28-29 (DR3), define when
    # breakpoints trigger. Each breakpoint has a two-bit entry that specifies
    # whether they break on execution (00b), data write (01b), data read or
    # write (11b). 10b is defined to mean break on IO read or write but no
    # hardware supports it. Bits 18-19 (DR0), 22-23 (DR1), 26-27 (DR2), 30-31
    # (DR3), define how large area of memory is watched by breakpoints. Again
    # each breakpoint has a two-bit entry that specifies whether they watch
    # one (00b), two (01b), eight (10b) or four (11b) bytes.
    ###########################################################################

    # Dr7 |= enableMask[register]
    enableMask = (
        1 << 0,  # Dr0 (bit 0)
        1 << 2,  # Dr1 (bit 2)
        1 << 4,  # Dr2 (bit 4)
        1 << 6,  # Dr3 (bit 6)
    )

    # Dr7 &= disableMask[register]
    disableMask = tuple([_registerMask ^ x for x in enableMask])  # The registerMask from the class is not there in py3
    try:
        del x  # It's not there in py3
    except:
        pass

    # orMask, andMask = triggerMask[register][trigger]
    # Dr7 = (Dr7 & andMask) | orMask    # to set
    # Dr7 = Dr7 & andMask               # to remove
    triggerMask = (
        # Dr0 (bits 16-17)
        (
            ((0 << 16), (3 << 16) ^ registerMask),  # execute
            ((1 << 16), (3 << 16) ^ registerMask),  # write
            ((2 << 16), (3 << 16) ^ registerMask),  # io read
            ((3 << 16), (3 << 16) ^ registerMask),  # access
        ),
        # Dr1 (bits 20-21)
        (
            ((0 << 20), (3 << 20) ^ registerMask),  # execute
            ((1 << 20), (3 << 20) ^ registerMask),  # write
            ((2 << 20), (3 << 20) ^ registerMask),  # io read
            ((3 << 20), (3 << 20) ^ registerMask),  # access
        ),
        # Dr2 (bits 24-25)
        (
            ((0 << 24), (3 << 24) ^ registerMask),  # execute
            ((1 << 24), (3 << 24) ^ registerMask),  # write
            ((2 << 24), (3 << 24) ^ registerMask),  # io read
            ((3 << 24), (3 << 24) ^ registerMask),  # access
        ),
        # Dr3 (bits 28-29)
        (
            ((0 << 28), (3 << 28) ^ registerMask),  # execute
            ((1 << 28), (3 << 28) ^ registerMask),  # write
            ((2 << 28), (3 << 28) ^ registerMask),  # io read
            ((3 << 28), (3 << 28) ^ registerMask),  # access
        ),
    )

    # orMask, andMask = watchMask[register][watch]
    # Dr7 = (Dr7 & andMask) | orMask    # to set
    # Dr7 = Dr7 & andMask               # to remove
    watchMask = (
        # Dr0 (bits 18-19)
        (
            ((0 << 18), (3 << 18) ^ registerMask),  # byte
            ((1 << 18), (3 << 18) ^ registerMask),  # word
            ((2 << 18), (3 << 18) ^ registerMask),  # qword
            ((3 << 18), (3 << 18) ^ registerMask),  # dword
        ),
        # Dr1 (bits 22-23)
        (
            ((0 << 23), (3 << 23) ^ registerMask),  # byte
            ((1 << 23), (3 << 23) ^ registerMask),  # word
            ((2 << 23), (3 << 23) ^ registerMask),  # qword
            ((3 << 23), (3 << 23) ^ registerMask),  # dword
        ),
        # Dr2 (bits 26-27)
        (
            ((0 << 26), (3 << 26) ^ registerMask),  # byte
            ((1 << 26), (3 << 26) ^ registerMask),  # word
            ((2 << 26), (3 << 26) ^ registerMask),  # qword
            ((3 << 26), (3 << 26) ^ registerMask),  # dword
        ),
        # Dr3 (bits 30-31)
        (
            ((0 << 30), (3 << 31) ^ registerMask),  # byte
            ((1 << 30), (3 << 31) ^ registerMask),  # word
            ((2 << 30), (3 << 31) ^ registerMask),  # qword
            ((3 << 30), (3 << 31) ^ registerMask),  # dword
        ),
    )

    # Dr7 = Dr7 & clearMask[register]
    clearMask = (
        registerMask ^ ((1 << 0) + (3 << 16) + (3 << 18)),  # Dr0
        registerMask ^ ((1 << 2) + (3 << 20) + (3 << 22)),  # Dr1
        registerMask ^ ((1 << 4) + (3 << 24) + (3 << 26)),  # Dr2
        registerMask ^ ((1 << 6) + (3 << 28) + (3 << 30)),  # Dr3
    )

    # Dr7 = Dr7 | generalDetectMask
    generalDetectMask = 1 << 13

    ###########################################################################
    # http://en.wikipedia.org/wiki/Debug_register
    #
    # DR6 - Debug status
    #
    # The debug status register permits the debugger to determine which debug
    # conditions have occurred. When the processor detects an enabled debug
    # exception, it sets the low-order bits of this register (0,1,2,3) before
    # entering the debug exception handler.
    #
    # Note that the bits of DR6 are never cleared by the processor. To avoid
    # any confusion in identifying the next debug exception, the debug handler
    # should move zeros to DR6 immediately before returning.
    ###########################################################################

    # bool(Dr6 & hitMask[register])
    hitMask = (
        (
            1 << 0  # Dr0
        ),
        (
            1 << 1  # Dr1
        ),
        (
            1 << 2  # Dr2
        ),
        (
            1 << 3  # Dr3
        ),
    )

    # bool(Dr6 & anyHitMask)
    hitMaskAll = hitMask[0] | hitMask[1] | hitMask[2] | hitMask[3]

    # Dr6 = Dr6 & clearHitMask
    clearHitMask = registerMask ^ hitMaskAll

    # bool(Dr6 & debugAccessMask)
    debugAccessMask = 1 << 13

    # bool(Dr6 & singleStepMask)
    singleStepMask = 1 << 14

    # bool(Dr6 & taskSwitchMask)
    taskSwitchMask = 1 << 15

    # Dr6 = Dr6 & clearDr6Mask
    clearDr6Mask = registerMask ^ (hitMaskAll | debugAccessMask | singleStepMask | taskSwitchMask)

    # ------------------------------------------------------------------------------

    ###############################################################################
    #
    #    (from the AMD64 manuals)
    #
    #    The fields within the DebugCtlMSR register are:
    #
    #    Last-Branch Record (LBR) - Bit 0, read/write. Software sets this bit to 1
    #    to cause the processor to record the source and target addresses of the
    #    last control transfer taken before a debug exception occurs. The recorded
    #    control transfers include branch instructions, interrupts, and exceptions.
    #
    #    Branch Single Step (BTF) - Bit 1, read/write. Software uses this bit to
    #    change the behavior of the rFLAGS.TF bit. When this bit is cleared to 0,
    #    the rFLAGS.TF bit controls instruction single stepping, (normal behavior).
    #    When this bit is set to 1, the rFLAGS.TF bit controls single stepping on
    #    control transfers. The single-stepped control transfers include branch
    #    instructions, interrupts, and exceptions. Control-transfer single stepping
    #    requires both BTF=1 and rFLAGS.TF=1.
    #
    #    Performance-Monitoring/Breakpoint Pin-Control (PBi) - Bits 5-2, read/write.
    #    Software uses these bits to control the type of information reported by
    #    the four external performance-monitoring/breakpoint pins on the processor.
    #    When a PBi bit is cleared to 0, the corresponding external pin (BPi)
    #    reports performance-monitor information. When a PBi bit is set to 1, the
    #    corresponding external pin (BPi) reports breakpoint information.
    #
    #    All remaining bits in the DebugCtlMSR register are reserved.
    #
    #    Software can enable control-transfer single stepping by setting
    #    DebugCtlMSR.BTF to 1 and rFLAGS.TF to 1. The processor automatically
    #    disables control-transfer single stepping when a debug exception (#DB)
    #    occurs by clearing DebugCtlMSR.BTF to 0. rFLAGS.TF is also cleared when a
    #    #DB exception occurs. Before exiting the debug-exception handler, software
    #    must set both DebugCtlMSR.BTF and rFLAGS.TF to 1 to restart single
    #    stepping.
    #
    ###############################################################################

    DebugCtlMSR = 0x1D9
    LastBranchRecord = 1 << 0
    BranchTrapFlag = 1 << 1
    PinControl = (
        (
            1 << 2  # PB1
        ),
        (
            1 << 3  # PB2
        ),
        (
            1 << 4  # PB3
        ),
        (
            1 << 5  # PB4
        ),
    )

    ###############################################################################
    #
    #    (from the AMD64 manuals)
    #
    #    Control-transfer recording MSRs: LastBranchToIP, LastBranchFromIP,
    #    LastExceptionToIP, and LastExceptionFromIP. These registers are loaded
    #    automatically by the processor when the DebugCtlMSR.LBR bit is set to 1.
    #    These MSRs are read-only.
    #
    #    The processor automatically disables control-transfer recording when a
    #    debug exception (#DB) occurs by clearing DebugCtlMSR.LBR to 0. The
    #    contents of the control-transfer recording MSRs are not altered by the
    #    processor when the #DB occurs. Before exiting the debug-exception handler,
    #    software can set DebugCtlMSR.LBR to 1 to re-enable the recording mechanism.
    #
    ###############################################################################

    LastBranchToIP = 0x1DC
    LastBranchFromIP = 0x1DB
    LastExceptionToIP = 0x1DE
    LastExceptionFromIP = 0x1DD

    # ------------------------------------------------------------------------------

    @classmethod
    def clear_bp(cls, ctx, register):
        """
        Clears a hardware breakpoint.

        @see: find_slot, set_bp

        @type  ctx: dict( str S{->} int )
        @param ctx: Thread context dictionary.

        @type  register: int
        @param register: Slot (debug register) for hardware breakpoint.
        """
        ctx["Dr7"] &= cls.clearMask[register]
        ctx["Dr%d" % register] = 0

    @classmethod
    def set_bp(cls, ctx, register, address, trigger, watch):
        """
        Sets a hardware breakpoint.

        @see: clear_bp, find_slot

        @type  ctx: dict( str S{->} int )
        @param ctx: Thread context dictionary.

        @type  register: int
        @param register: Slot (debug register).

        @type  address: int
        @param address: Memory address.

        @type  trigger: int
        @param trigger: Trigger flag. See L{HardwareBreakpoint.validTriggers}.

        @type  watch: int
        @param watch: Watch flag. See L{HardwareBreakpoint.validWatchSizes}.
        """
        Dr7 = ctx["Dr7"]
        Dr7 |= cls.enableMask[register]
        orMask, andMask = cls.triggerMask[register][trigger]
        Dr7 &= andMask
        Dr7 |= orMask
        orMask, andMask = cls.watchMask[register][watch]
        Dr7 &= andMask
        Dr7 |= orMask
        ctx["Dr7"] = Dr7
        ctx["Dr%d" % register] = address

    @classmethod
    def find_slot(cls, ctx):
        """
        Finds an empty slot to set a hardware breakpoint.

        @see: clear_bp, set_bp

        @type  ctx: dict( str S{->} int )
        @param ctx: Thread context dictionary.

        @rtype:  int
        @return: Slot (debug register) for hardware breakpoint.
        """
        Dr7 = ctx["Dr7"]
        slot = 0
        for m in cls.enableMask:
            if (Dr7 & m) == 0:
                return slot
            slot += 1
        return None

# === NexusCore/openenv\Lib\site-packages\litellm\proxy\pass_through_endpoints\llm_passthrough_endpoints.py ===
"""
What is this?

Provider-specific Pass-Through Endpoints

Use litellm with Anthropic SDK, Vertex AI SDK, Cohere SDK, etc.
"""

import os
from typing import Optional, cast

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import StreamingResponse

import litellm
from litellm._logging import verbose_proxy_logger
from litellm.constants import BEDROCK_AGENT_RUNTIME_PASS_THROUGH_ROUTES
from litellm.llms.vertex_ai.vertex_llm_base import VertexBase
from litellm.proxy._types import *
from litellm.proxy.auth.route_checks import RouteChecks
from litellm.proxy.auth.user_api_key_auth import user_api_key_auth
from litellm.proxy.common_utils.http_parsing_utils import (
    _read_request_body,
    get_form_data,
    get_request_body,
)
from litellm.proxy.pass_through_endpoints.common_utils import get_litellm_virtual_key
from litellm.proxy.pass_through_endpoints.pass_through_endpoints import (
    create_pass_through_route,
)
from litellm.proxy.utils import is_known_model
from litellm.secret_managers.main import get_secret_str

from .passthrough_endpoint_router import PassthroughEndpointRouter

vertex_llm_base = VertexBase()
router = APIRouter()
default_vertex_config = None

passthrough_endpoint_router = PassthroughEndpointRouter()


def create_request_copy(request: Request):
    return {
        "method": request.method,
        "url": str(request.url),
        "headers": dict(request.headers),
        "cookies": request.cookies,
        "query_params": dict(request.query_params),
    }


def is_passthrough_request_using_router_model(
    request_body: dict, llm_router: Optional[litellm.Router]
) -> bool:
    """
    Returns True if the model is in the llm_router model names
    """
    try:
        model = request_body.get("model")
        return is_known_model(model, llm_router)
    except Exception:
        return False


def is_passthrough_request_streaming(request_body: dict) -> bool:
    """
    Returns True if the request is streaming
    """
    return request_body.get("stream", False)


async def llm_passthrough_factory_proxy_route(
    custom_llm_provider: str,
    endpoint: str,
    request: Request,
    fastapi_response: Response,
    user_api_key_dict: UserAPIKeyAuth = Depends(user_api_key_auth),
):
    """
    Factory function for creating pass-through endpoints for LLM providers.
    """
    from litellm.types.utils import LlmProviders
    from litellm.utils import ProviderConfigManager

    provider_config = ProviderConfigManager.get_provider_model_info(
        provider=LlmProviders(custom_llm_provider),
        model=None,
    )
    if provider_config is None:
        raise HTTPException(
            status_code=404, detail=f"Provider {custom_llm_provider} not found"
        )

    base_target_url = provider_config.get_api_base()

    if base_target_url is None:
        raise HTTPException(
            status_code=404, detail=f"Provider {custom_llm_provider} api base not found"
        )

    encoded_endpoint = httpx.URL(endpoint).path

    # Ensure endpoint starts with '/' for proper URL construction
    if not encoded_endpoint.startswith("/"):
        encoded_endpoint = "/" + encoded_endpoint

    # Construct the full target URL using httpx
    base_url = httpx.URL(base_target_url)
    updated_url = base_url.copy_with(path=encoded_endpoint)

    # Add or update query parameters
    provider_api_key = passthrough_endpoint_router.get_credentials(
        custom_llm_provider=custom_llm_provider,
        region_name=None,
    )

    auth_headers = provider_config.validate_environment(
        headers={},
        model="",
        messages=[],
        optional_params={},
        litellm_params={},
        api_key=provider_api_key,
        api_base=base_target_url,
    )

    ## check for streaming
    is_streaming_request = False
    # anthropic is streaming when 'stream' = True is in the body
    if request.method == "POST":
        _request_body = await request.json()
        if _request_body.get("stream"):
            is_streaming_request = True

    ## CREATE PASS-THROUGH
    endpoint_func = create_pass_through_route(
        endpoint=endpoint,
        target=str(updated_url),
        custom_headers=auth_headers,
    )  # dynamically construct pass-through endpoint based on incoming path
    received_value = await endpoint_func(
        request,
        fastapi_response,
        user_api_key_dict,
        stream=is_streaming_request,  # type: ignore
    )

    return received_value


@router.api_route(
    "/gemini/{endpoint:path}",
    methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
    tags=["Google AI Studio Pass-through", "pass-through"],
)
async def gemini_proxy_route(
    endpoint: str,
    request: Request,
    fastapi_response: Response,
):
    """
    [Docs](https://docs.litellm.ai/docs/pass_through/google_ai_studio)
    """
    ## CHECK FOR LITELLM API KEY IN THE QUERY PARAMS - ?..key=LITELLM_API_KEY
    google_ai_studio_api_key = request.query_params.get("key") or request.headers.get(
        "x-goog-api-key"
    )

    user_api_key_dict = await user_api_key_auth(
        request=request, api_key=f"Bearer {google_ai_studio_api_key}"
    )

    base_target_url = "https://generativelanguage.googleapis.com"
    encoded_endpoint = httpx.URL(endpoint).path

    # Ensure endpoint starts with '/' for proper URL construction
    if not encoded_endpoint.startswith("/"):
        encoded_endpoint = "/" + encoded_endpoint

    # Construct the full target URL using httpx
    base_url = httpx.URL(base_target_url)
    updated_url = base_url.copy_with(path=encoded_endpoint)

    # Add or update query parameters
    gemini_api_key: Optional[str] = passthrough_endpoint_router.get_credentials(
        custom_llm_provider="gemini",
        region_name=None,
    )
    if gemini_api_key is None:
        raise Exception(
            "Required 'GEMINI_API_KEY' in environment to make pass-through calls to Google AI Studio."
        )
    # Merge query parameters, giving precedence to those in updated_url
    merged_params = dict(request.query_params)
    merged_params.update({"key": gemini_api_key})

    ## check for streaming
    is_streaming_request = False
    if "stream" in str(updated_url):
        is_streaming_request = True

    ## CREATE PASS-THROUGH
    endpoint_func = create_pass_through_route(
        endpoint=endpoint,
        target=str(updated_url),
    )  # dynamically construct pass-through endpoint based on incoming path
    received_value = await endpoint_func(
        request,
        fastapi_response,
        user_api_key_dict,
        query_params=merged_params,  # type: ignore
        stream=is_streaming_request,  # type: ignore
    )

    return received_value


@router.api_route(
    "/cohere/{endpoint:path}",
    methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
    tags=["Cohere Pass-through", "pass-through"],
)
async def cohere_proxy_route(
    endpoint: str,
    request: Request,
    fastapi_response: Response,
    user_api_key_dict: UserAPIKeyAuth = Depends(user_api_key_auth),
):
    """
    [Docs](https://docs.litellm.ai/docs/pass_through/cohere)
    """
    base_target_url = "https://api.cohere.com"
    encoded_endpoint = httpx.URL(endpoint).path

    # Ensure endpoint starts with '/' for proper URL construction
    if not encoded_endpoint.startswith("/"):
        encoded_endpoint = "/" + encoded_endpoint

    # Construct the full target URL using httpx
    base_url = httpx.URL(base_target_url)
    updated_url = base_url.copy_with(path=encoded_endpoint)

    # Add or update query parameters
    cohere_api_key = passthrough_endpoint_router.get_credentials(
        custom_llm_provider="cohere",
        region_name=None,
    )

    ## check for streaming
    is_streaming_request = False
    if "stream" in str(updated_url):
        is_streaming_request = True

    ## CREATE PASS-THROUGH
    endpoint_func = create_pass_through_route(
        endpoint=endpoint,
        target=str(updated_url),
        custom_headers={"Authorization": "Bearer {}".format(cohere_api_key)},
    )  # dynamically construct pass-through endpoint based on incoming path
    received_value = await endpoint_func(
        request,
        fastapi_response,
        user_api_key_dict,
        stream=is_streaming_request,  # type: ignore
    )

    return received_value


@router.api_route(
    "/vllm/{endpoint:path}",
    methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
    tags=["VLLM Pass-through", "pass-through"],
)
async def vllm_proxy_route(
    endpoint: str,
    request: Request,
    fastapi_response: Response,
    user_api_key_dict: UserAPIKeyAuth = Depends(user_api_key_auth),
):
    """
    [Docs](https://docs.litellm.ai/docs/pass_through/vllm)
    """
    from litellm.proxy.pass_through_endpoints.pass_through_endpoints import (
        HttpPassThroughEndpointHelpers,
    )
    from litellm.proxy.proxy_server import llm_router

    request_body = await get_request_body(request)
    is_router_model = is_passthrough_request_using_router_model(
        request_body, llm_router
    )
    is_streaming_request = is_passthrough_request_streaming(request_body)
    if is_router_model and llm_router:
        result = cast(
            httpx.Response,
            await llm_router.allm_passthrough_route(
                model=request_body.get("model"),
                method=request.method,
                endpoint=endpoint,
                request_query_params=request.query_params,
                request_headers=dict(request.headers),
                stream=request_body.get("stream", False),
                content=None,
                data=None,
                files=None,
                json=request_body
                if request.headers.get("content-type") == "application/json"
                else None,
                params=None,
                headers=None,
                cookies=None,
            ),
        )

        if is_streaming_request:
            return StreamingResponse(
                content=result.aiter_bytes(),
                status_code=result.status_code,
                headers=HttpPassThroughEndpointHelpers.get_response_headers(
                    headers=result.headers,
                    custom_headers=None,
                ),
            )

        content = await result.aread()
        return Response(
            content=content,
            status_code=result.status_code,
            headers=HttpPassThroughEndpointHelpers.get_response_headers(
                headers=result.headers,
                custom_headers=None,
            ),
        )

    return await llm_passthrough_factory_proxy_route(
        endpoint=endpoint,
        request=request,
        fastapi_response=fastapi_response,
        user_api_key_dict=user_api_key_dict,
        custom_llm_provider="vllm",
    )


@router.api_route(
    "/mistral/{endpoint:path}",
    methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
    tags=["Mistral Pass-through", "pass-through"],
)
async def mistral_proxy_route(
    endpoint: str,
    request: Request,
    fastapi_response: Response,
    user_api_key_dict: UserAPIKeyAuth = Depends(user_api_key_auth),
):
    """
    [Docs](https://docs.litellm.ai/docs/anthropic_completion)
    """
    base_target_url = os.getenv("MISTRAL_API_BASE") or "https://api.mistral.ai"
    encoded_endpoint = httpx.URL(endpoint).path

    # Ensure endpoint starts with '/' for proper URL construction
    if not encoded_endpoint.startswith("/"):
        encoded_endpoint = "/" + encoded_endpoint

    # Construct the full target URL using httpx
    base_url = httpx.URL(base_target_url)
    updated_url = base_url.copy_with(path=encoded_endpoint)

    # Add or update query parameters
    mistral_api_key = passthrough_endpoint_router.get_credentials(
        custom_llm_provider="mistral",
        region_name=None,
    )

    ## check for streaming
    is_streaming_request = False
    # anthropic is streaming when 'stream' = True is in the body
    if request.method == "POST":
        _request_body = await request.json()
        if _request_body.get("stream"):
            is_streaming_request = True

    ## CREATE PASS-THROUGH
    endpoint_func = create_pass_through_route(
        endpoint=endpoint,
        target=str(updated_url),
        custom_headers={"Authorization": "Bearer {}".format(mistral_api_key)},
    )  # dynamically construct pass-through endpoint based on incoming path
    received_value = await endpoint_func(
        request,
        fastapi_response,
        user_api_key_dict,
        stream=is_streaming_request,  # type: ignore
    )

    return received_value


async def is_streaming_request_fn(request: Request) -> bool:
    if request.method == "POST":
        content_type = request.headers.get("content-type", None)
        if content_type and "multipart/form-data" in content_type:
            _request_body = await get_form_data(request)
        else:
            _request_body = await _read_request_body(request)
        if _request_body.get("stream"):
            return True
    return False


@router.api_route(
    "/anthropic/{endpoint:path}",
    methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
    tags=["Anthropic Pass-through", "pass-through"],
)
async def anthropic_proxy_route(
    endpoint: str,
    request: Request,
    fastapi_response: Response,
    user_api_key_dict: UserAPIKeyAuth = Depends(user_api_key_auth),
):
    """
    [Docs](https://docs.litellm.ai/docs/anthropic_completion)
    """
    base_target_url = "https://api.anthropic.com"
    encoded_endpoint = httpx.URL(endpoint).path

    # Ensure endpoint starts with '/' for proper URL construction
    if not encoded_endpoint.startswith("/"):
        encoded_endpoint = "/" + encoded_endpoint

    # Construct the full target URL using httpx
    base_url = httpx.URL(base_target_url)
    updated_url = base_url.copy_with(path=encoded_endpoint)

    # Add or update query parameters
    anthropic_api_key = passthrough_endpoint_router.get_credentials(
        custom_llm_provider="anthropic",
        region_name=None,
    )

    ## check for streaming
    is_streaming_request = await is_streaming_request_fn(request)

    ## CREATE PASS-THROUGH
    endpoint_func = create_pass_through_route(
        endpoint=endpoint,
        target=str(updated_url),
        custom_headers={"x-api-key": "{}".format(anthropic_api_key)},
        _forward_headers=True,
    )  # dynamically construct pass-through endpoint based on incoming path
    received_value = await endpoint_func(
        request,
        fastapi_response,
        user_api_key_dict,
        stream=is_streaming_request,  # type: ignore
    )

    return received_value


@router.api_route(
    "/bedrock/{endpoint:path}",
    methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
    tags=["Bedrock Pass-through", "pass-through"],
)
async def bedrock_proxy_route(
    endpoint: str,
    request: Request,
    fastapi_response: Response,
    user_api_key_dict: UserAPIKeyAuth = Depends(user_api_key_auth),
):
    """
    [Docs](https://docs.litellm.ai/docs/pass_through/bedrock)
    """
    create_request_copy(request)

    try:
        from botocore.auth import SigV4Auth
        from botocore.awsrequest import AWSRequest
        from botocore.credentials import Credentials
    except ImportError:
        raise ImportError("Missing boto3 to call bedrock. Run 'pip install boto3'.")

    aws_region_name = litellm.utils.get_secret(secret_name="AWS_REGION_NAME")
    if _is_bedrock_agent_runtime_route(endpoint=endpoint):  # handle bedrock agents
        base_target_url = (
            f"https://bedrock-agent-runtime.{aws_region_name}.amazonaws.com"
        )
    else:
        base_target_url = f"https://bedrock-runtime.{aws_region_name}.amazonaws.com"
    encoded_endpoint = httpx.URL(endpoint).path

    # Ensure endpoint starts with '/' for proper URL construction
    if not encoded_endpoint.startswith("/"):
        encoded_endpoint = "/" + encoded_endpoint

    # Construct the full target URL using httpx
    base_url = httpx.URL(base_target_url)
    updated_url = base_url.copy_with(path=encoded_endpoint)

    # Add or update query parameters
    from litellm.llms.bedrock.chat import BedrockConverseLLM

    credentials: Credentials = BedrockConverseLLM().get_credentials()
    sigv4 = SigV4Auth(credentials, "bedrock", aws_region_name)
    headers = {"Content-Type": "application/json"}
    # Assuming the body contains JSON data, parse it
    try:
        data = await request.json()
    except Exception as e:
        raise HTTPException(status_code=400, detail={"error": e})
    _request = AWSRequest(
        method="POST", url=str(updated_url), data=json.dumps(data), headers=headers
    )
    sigv4.add_auth(_request)
    prepped = _request.prepare()

    ## check for streaming
    is_streaming_request = False
    if "stream" in str(updated_url):
        is_streaming_request = True

    ## CREATE PASS-THROUGH
    endpoint_func = create_pass_through_route(
        endpoint=endpoint,
        target=str(prepped.url),
        custom_headers=prepped.headers,  # type: ignore
    )  # dynamically construct pass-through endpoint based on incoming path
    received_value = await endpoint_func(
        request,
        fastapi_response,
        user_api_key_dict,
        stream=is_streaming_request,  # type: ignore
        custom_body=data,  # type: ignore
        query_params={},  # type: ignore
    )

    return received_value


def _is_bedrock_agent_runtime_route(endpoint: str) -> bool:
    """
    Return True, if the endpoint should be routed to the `bedrock-agent-runtime` endpoint.
    """
    for _route in BEDROCK_AGENT_RUNTIME_PASS_THROUGH_ROUTES:
        if _route in endpoint:
            return True
    return False


@router.api_route(
    "/assemblyai/{endpoint:path}",
    methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
    tags=["AssemblyAI Pass-through", "pass-through"],
)
@router.api_route(
    "/eu.assemblyai/{endpoint:path}",
    methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
    tags=["AssemblyAI EU Pass-through", "pass-through"],
)
async def assemblyai_proxy_route(
    endpoint: str,
    request: Request,
    fastapi_response: Response,
    user_api_key_dict: UserAPIKeyAuth = Depends(user_api_key_auth),
):
    from litellm.proxy.pass_through_endpoints.llm_provider_handlers.assembly_passthrough_logging_handler import (
        AssemblyAIPassthroughLoggingHandler,
    )

    """
    [Docs](https://api.assemblyai.com)
    """
    # Set base URL based on the route
    assembly_region = AssemblyAIPassthroughLoggingHandler._get_assembly_region_from_url(
        url=str(request.url)
    )
    base_target_url = (
        AssemblyAIPassthroughLoggingHandler._get_assembly_base_url_from_region(
            region=assembly_region
        )
    )
    encoded_endpoint = httpx.URL(endpoint).path
    # Ensure endpoint starts with '/' for proper URL construction
    if not encoded_endpoint.startswith("/"):
        encoded_endpoint = "/" + encoded_endpoint

    # Construct the full target URL using httpx
    base_url = httpx.URL(base_target_url)
    updated_url = base_url.copy_with(path=encoded_endpoint)

    # Add or update query parameters
    assemblyai_api_key = passthrough_endpoint_router.get_credentials(
        custom_llm_provider="assemblyai",
        region_name=assembly_region,
    )

    ## check for streaming
    is_streaming_request = False
    # assemblyai is streaming when 'stream' = True is in the body
    if request.method == "POST":
        _request_body = await request.json()
        if _request_body.get("stream"):
            is_streaming_request = True

    ## CREATE PASS-THROUGH
    endpoint_func = create_pass_through_route(
        endpoint=endpoint,
        target=str(updated_url),
        custom_headers={"Authorization": "{}".format(assemblyai_api_key)},
    )  # dynamically construct pass-through endpoint based on incoming path
    received_value = await endpoint_func(
        request=request,
        fastapi_response=fastapi_response,
        user_api_key_dict=user_api_key_dict,
        stream=is_streaming_request,  # type: ignore
    )

    return received_value


@router.api_route(
    "/azure/{endpoint:path}",
    methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
    tags=["Azure Pass-through", "pass-through"],
)
async def azure_proxy_route(
    endpoint: str,
    request: Request,
    fastapi_response: Response,
    user_api_key_dict: UserAPIKeyAuth = Depends(user_api_key_auth),
):
    """
    Call any azure endpoint using the proxy.

    Just use `{PROXY_BASE_URL}/azure/{endpoint:path}`
    """
    base_target_url = get_secret_str(secret_name="AZURE_API_BASE")
    if base_target_url is None:
        raise Exception(
            "Required 'AZURE_API_BASE' in environment to make pass-through calls to Azure."
        )
    # Add or update query parameters
    azure_api_key = passthrough_endpoint_router.get_credentials(
        custom_llm_provider=litellm.LlmProviders.AZURE.value,
        region_name=None,
    )
    if azure_api_key is None:
        raise Exception(
            "Required 'AZURE_API_KEY' in environment to make pass-through calls to Azure."
        )

    return await BaseOpenAIPassThroughHandler._base_openai_pass_through_handler(
        endpoint=endpoint,
        request=request,
        fastapi_response=fastapi_response,
        user_api_key_dict=user_api_key_dict,
        base_target_url=base_target_url,
        api_key=azure_api_key,
        custom_llm_provider=litellm.LlmProviders.AZURE,
    )


from abc import ABC, abstractmethod


class BaseVertexAIPassThroughHandler(ABC):
    @staticmethod
    @abstractmethod
    def get_default_base_target_url(vertex_location: Optional[str]) -> str:
        pass

    @staticmethod
    @abstractmethod
    def update_base_target_url_with_credential_location(
        base_target_url: str, vertex_location: Optional[str]
    ) -> str:
        pass


class VertexAIDiscoveryPassThroughHandler(BaseVertexAIPassThroughHandler):
    @staticmethod
    def get_default_base_target_url(vertex_location: Optional[str]) -> str:
        return "https://discoveryengine.googleapis.com/"

    @staticmethod
    def update_base_target_url_with_credential_location(
        base_target_url: str, vertex_location: Optional[str]
    ) -> str:
        return base_target_url


class VertexAIPassThroughHandler(BaseVertexAIPassThroughHandler):
    @staticmethod
    def get_default_base_target_url(vertex_location: Optional[str]) -> str:
        return get_vertex_base_url(vertex_location)

    @staticmethod
    def update_base_target_url_with_credential_location(
        base_target_url: str, vertex_location: Optional[str]
    ) -> str:
        return get_vertex_base_url(vertex_location)

def get_vertex_base_url(vertex_location: Optional[str]) -> str:
    """
    Returns the base URL for Vertex AI based on the provided location.
    """
    if vertex_location == "global":
        return "https://aiplatform.googleapis.com/"
    return f"https://{vertex_location}-aiplatform.googleapis.com/"

def get_vertex_pass_through_handler(
    call_type: Literal["discovery", "aiplatform"]
) -> BaseVertexAIPassThroughHandler:
    if call_type == "discovery":
        return VertexAIDiscoveryPassThroughHandler()
    elif call_type == "aiplatform":
        return VertexAIPassThroughHandler()
    else:
        raise ValueError(f"Invalid call type: {call_type}")


async def _base_vertex_proxy_route(
    endpoint: str,
    request: Request,
    fastapi_response: Response,
    get_vertex_pass_through_handler: BaseVertexAIPassThroughHandler,
    user_api_key_dict: Optional[UserAPIKeyAuth] = None,
):
    """
    Base function for Vertex AI passthrough routes.
    Handles common logic for all Vertex AI services.

    Default base_target_url is `https://{vertex_location}-aiplatform.googleapis.com/`
    """
    from litellm.llms.vertex_ai.common_utils import (
        construct_target_url,
        get_vertex_location_from_url,
        get_vertex_project_id_from_url,
    )

    encoded_endpoint = httpx.URL(endpoint).path
    verbose_proxy_logger.debug("requested endpoint %s", endpoint)
    headers: dict = {}
    api_key_to_use = get_litellm_virtual_key(request=request)
    user_api_key_dict = await user_api_key_auth(
        request=request,
        api_key=api_key_to_use,
    )

    if user_api_key_dict is None:
        api_key_to_use = get_litellm_virtual_key(request=request)
        user_api_key_dict = await user_api_key_auth(
            request=request,
            api_key=api_key_to_use,
        )

    vertex_project: Optional[str] = get_vertex_project_id_from_url(endpoint)
    vertex_location: Optional[str] = get_vertex_location_from_url(endpoint)
    vertex_credentials = passthrough_endpoint_router.get_vertex_credentials(
        project_id=vertex_project,
        location=vertex_location,
    )

    base_target_url = get_vertex_pass_through_handler.get_default_base_target_url(
        vertex_location
    )

    headers_passed_through = False
    # Use headers from the incoming request if no vertex credentials are found
    if vertex_credentials is None or vertex_credentials.vertex_project is None:
        headers = dict(request.headers) or {}
        headers_passed_through = True
        verbose_proxy_logger.debug(
            "default_vertex_config  not set, incoming request headers %s", headers
        )
        headers.pop("content-length", None)
        headers.pop("host", None)
    else:
        vertex_project = vertex_credentials.vertex_project
        vertex_location = vertex_credentials.vertex_location
        vertex_credentials_str = vertex_credentials.vertex_credentials

        _auth_header, vertex_project = await vertex_llm_base._ensure_access_token_async(
            credentials=vertex_credentials_str,
            project_id=vertex_project,
            custom_llm_provider="vertex_ai_beta",
        )

        auth_header, _ = vertex_llm_base._get_token_and_url(
            model="",
            auth_header=_auth_header,
            gemini_api_key=None,
            vertex_credentials=vertex_credentials_str,
            vertex_project=vertex_project,
            vertex_location=vertex_location,
            stream=False,
            custom_llm_provider="vertex_ai_beta",
            api_base="",
        )

        headers = {
            "Authorization": f"Bearer {auth_header}",
        }

        base_target_url = get_vertex_pass_through_handler.update_base_target_url_with_credential_location(
            base_target_url, vertex_location
        )

    if base_target_url is None:
        base_target_url = get_vertex_base_url(vertex_location)

    request_route = encoded_endpoint
    verbose_proxy_logger.debug("request_route %s", request_route)

    # Ensure endpoint starts with '/' for proper URL construction
    if not encoded_endpoint.startswith("/"):
        encoded_endpoint = "/" + encoded_endpoint

    # Construct the full target URL using httpx
    updated_url = construct_target_url(
        base_url=base_target_url,
        requested_route=encoded_endpoint,
        vertex_location=vertex_location,
        vertex_project=vertex_project,
    )

    verbose_proxy_logger.debug("updated url %s", updated_url)

    ## check for streaming
    target = str(updated_url)
    is_streaming_request = False
    if "stream" in str(updated_url):
        is_streaming_request = True
        target += "?alt=sse"

    ## CREATE PASS-THROUGH
    endpoint_func = create_pass_through_route(
        endpoint=endpoint,
        target=target,
        custom_headers=headers,
    )  # dynamically construct pass-through endpoint based on incoming path

    try:
        received_value = await endpoint_func(
            request,
            fastapi_response,
            user_api_key_dict,
            stream=is_streaming_request,  # type: ignore
        )
    except ProxyException as e:
        if headers_passed_through:
            e.message = f"No credentials found on proxy for project_name={vertex_project} + location={vertex_location}, check `/model/info` for allowed project + region combinations with `use_in_pass_through: true`. Headers were passed through directly but request failed with error: {e.message}"
        raise e

    return received_value


@router.api_route(
    "/vertex_ai/discovery/{endpoint:path}",
    methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
    tags=["Vertex AI Pass-through", "pass-through"],
)
async def vertex_discovery_proxy_route(
    endpoint: str,
    request: Request,
    fastapi_response: Response,
):
    """
    Call any vertex discovery endpoint using the proxy.

    Just use `{PROXY_BASE_URL}/vertex_ai/discovery/{endpoint:path}`

    Target url: `https://discoveryengine.googleapis.com`
    """

    discovery_handler = get_vertex_pass_through_handler(call_type="discovery")
    return await _base_vertex_proxy_route(
        endpoint=endpoint,
        request=request,
        fastapi_response=fastapi_response,
        get_vertex_pass_through_handler=discovery_handler,
    )


@router.api_route(
    "/vertex-ai/{endpoint:path}",
    methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
    tags=["Vertex AI Pass-through", "pass-through"],
    include_in_schema=False,
)
@router.api_route(
    "/vertex_ai/{endpoint:path}",
    methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
    tags=["Vertex AI Pass-through", "pass-through"],
)
async def vertex_proxy_route(
    endpoint: str,
    request: Request,
    fastapi_response: Response,
    user_api_key_dict: UserAPIKeyAuth = Depends(user_api_key_auth),
):
    """
    Call LiteLLM proxy via Vertex AI SDK.

    [Docs](https://docs.litellm.ai/docs/pass_through/vertex_ai)
    """
    ai_platform_handler = get_vertex_pass_through_handler(call_type="aiplatform")

    return await _base_vertex_proxy_route(
        endpoint=endpoint,
        request=request,
        fastapi_response=fastapi_response,
        get_vertex_pass_through_handler=ai_platform_handler,
        user_api_key_dict=user_api_key_dict,
    )


@router.api_route(
    "/openai/{endpoint:path}",
    methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
    tags=["OpenAI Pass-through", "pass-through"],
)
async def openai_proxy_route(
    endpoint: str,
    request: Request,
    fastapi_response: Response,
    user_api_key_dict: UserAPIKeyAuth = Depends(user_api_key_auth),
):
    """
    Simple pass-through for OpenAI. Use this if you want to directly send a request to OpenAI.


    """
    base_target_url = "https://api.openai.com/"
    # Add or update query parameters
    openai_api_key = passthrough_endpoint_router.get_credentials(
        custom_llm_provider=litellm.LlmProviders.OPENAI.value,
        region_name=None,
    )
    if openai_api_key is None:
        raise Exception(
            "Required 'OPENAI_API_KEY' in environment to make pass-through calls to OpenAI."
        )

    return await BaseOpenAIPassThroughHandler._base_openai_pass_through_handler(
        endpoint=endpoint,
        request=request,
        fastapi_response=fastapi_response,
        user_api_key_dict=user_api_key_dict,
        base_target_url=base_target_url,
        api_key=openai_api_key,
        custom_llm_provider=litellm.LlmProviders.OPENAI,
    )


class BaseOpenAIPassThroughHandler:
    @staticmethod
    async def _base_openai_pass_through_handler(
        endpoint: str,
        request: Request,
        fastapi_response: Response,
        user_api_key_dict: UserAPIKeyAuth,
        base_target_url: str,
        api_key: str,
        custom_llm_provider: litellm.LlmProviders,
    ):
        encoded_endpoint = httpx.URL(endpoint).path
        # Ensure endpoint starts with '/' for proper URL construction
        if not encoded_endpoint.startswith("/"):
            encoded_endpoint = "/" + encoded_endpoint

        # Construct the full target URL by properly joining the base URL and endpoint path
        base_url = httpx.URL(base_target_url)
        updated_url = BaseOpenAIPassThroughHandler._join_url_paths(
            base_url=base_url,
            path=encoded_endpoint,
            custom_llm_provider=custom_llm_provider,
        )

        ## check for streaming
        is_streaming_request = False
        if "stream" in str(updated_url):
            is_streaming_request = True

        ## CREATE PASS-THROUGH
        endpoint_func = create_pass_through_route(
            endpoint=endpoint,
            target=str(updated_url),
            custom_headers=BaseOpenAIPassThroughHandler._assemble_headers(
                api_key=api_key, request=request
            ),
        )  # dynamically construct pass-through endpoint based on incoming path
        received_value = await endpoint_func(
            request,
            fastapi_response,
            user_api_key_dict,
            stream=is_streaming_request,  # type: ignore
            query_params=dict(request.query_params),  # type: ignore
        )

        return received_value

    @staticmethod
    def _append_openai_beta_header(headers: dict, request: Request) -> dict:
        """
        Appends the OpenAI-Beta header to the headers if the request is an OpenAI Assistants API request
        """
        if (
            RouteChecks._is_assistants_api_request(request) is True
            and "OpenAI-Beta" not in headers
        ):
            headers["OpenAI-Beta"] = "assistants=v2"
        return headers

    @staticmethod
    def _assemble_headers(api_key: str, request: Request) -> dict:
        base_headers = {
            "authorization": "Bearer {}".format(api_key),
            "api-key": "{}".format(api_key),
        }
        return BaseOpenAIPassThroughHandler._append_openai_beta_header(
            headers=base_headers,
            request=request,
        )

    @staticmethod
    def _join_url_paths(
        base_url: httpx.URL, path: str, custom_llm_provider: litellm.LlmProviders
    ) -> str:
        """
        Properly joins a base URL with a path, preserving any existing path in the base URL.
        """
        # Join paths correctly by removing trailing/leading slashes as needed
        if not base_url.path or base_url.path == "/":
            # If base URL has no path, just use the new path
            joined_path_str = str(base_url.copy_with(path=path))
        else:
            # Otherwise, combine the paths
            base_path = base_url.path.rstrip("/")
            clean_path = path.lstrip("/")
            full_path = f"{base_path}/{clean_path}"
            joined_path_str = str(base_url.copy_with(path=full_path))

        # Apply OpenAI-specific path handling for both branches
        if (
            custom_llm_provider == litellm.LlmProviders.OPENAI
            and "/v1/" not in joined_path_str
        ):
            # Insert v1 after api.openai.com for OpenAI requests
            joined_path_str = joined_path_str.replace(
                "api.openai.com/", "api.openai.com/v1/"
            )

        return joined_path_str

# === NexusCore/openenv\Lib\site-packages\toml\decoder.py ===
import datetime
import io
from os import linesep
import re
import sys

from toml.tz import TomlTz

if sys.version_info < (3,):
    _range = xrange  # noqa: F821
else:
    unicode = str
    _range = range
    basestring = str
    unichr = chr


def _detect_pathlib_path(p):
    if (3, 4) <= sys.version_info:
        import pathlib
        if isinstance(p, pathlib.PurePath):
            return True
    return False


def _ispath(p):
    if isinstance(p, (bytes, basestring)):
        return True
    return _detect_pathlib_path(p)


def _getpath(p):
    if (3, 6) <= sys.version_info:
        import os
        return os.fspath(p)
    if _detect_pathlib_path(p):
        return str(p)
    return p


try:
    FNFError = FileNotFoundError
except NameError:
    FNFError = IOError


TIME_RE = re.compile(r"([0-9]{2}):([0-9]{2}):([0-9]{2})(\.([0-9]{3,6}))?")


class TomlDecodeError(ValueError):
    """Base toml Exception / Error."""

    def __init__(self, msg, doc, pos):
        lineno = doc.count('\n', 0, pos) + 1
        colno = pos - doc.rfind('\n', 0, pos)
        emsg = '{} (line {} column {} char {})'.format(msg, lineno, colno, pos)
        ValueError.__init__(self, emsg)
        self.msg = msg
        self.doc = doc
        self.pos = pos
        self.lineno = lineno
        self.colno = colno


# Matches a TOML number, which allows underscores for readability
_number_with_underscores = re.compile('([0-9])(_([0-9]))*')


class CommentValue(object):
    def __init__(self, val, comment, beginline, _dict):
        self.val = val
        separator = "\n" if beginline else " "
        self.comment = separator + comment
        self._dict = _dict

    def __getitem__(self, key):
        return self.val[key]

    def __setitem__(self, key, value):
        self.val[key] = value

    def dump(self, dump_value_func):
        retstr = dump_value_func(self.val)
        if isinstance(self.val, self._dict):
            return self.comment + "\n" + unicode(retstr)
        else:
            return unicode(retstr) + self.comment


def _strictly_valid_num(n):
    n = n.strip()
    if not n:
        return False
    if n[0] == '_':
        return False
    if n[-1] == '_':
        return False
    if "_." in n or "._" in n:
        return False
    if len(n) == 1:
        return True
    if n[0] == '0' and n[1] not in ['.', 'o', 'b', 'x']:
        return False
    if n[0] == '+' or n[0] == '-':
        n = n[1:]
        if len(n) > 1 and n[0] == '0' and n[1] != '.':
            return False
    if '__' in n:
        return False
    return True


def load(f, _dict=dict, decoder=None):
    """Parses named file or files as toml and returns a dictionary

    Args:
        f: Path to the file to open, array of files to read into single dict
           or a file descriptor
        _dict: (optional) Specifies the class of the returned toml dictionary
        decoder: The decoder to use

    Returns:
        Parsed toml file represented as a dictionary

    Raises:
        TypeError -- When f is invalid type
        TomlDecodeError: Error while decoding toml
        IOError / FileNotFoundError -- When an array with no valid (existing)
        (Python 2 / Python 3)          file paths is passed
    """

    if _ispath(f):
        with io.open(_getpath(f), encoding='utf-8') as ffile:
            return loads(ffile.read(), _dict, decoder)
    elif isinstance(f, list):
        from os import path as op
        from warnings import warn
        if not [path for path in f if op.exists(path)]:
            error_msg = "Load expects a list to contain filenames only."
            error_msg += linesep
            error_msg += ("The list needs to contain the path of at least one "
                          "existing file.")
            raise FNFError(error_msg)
        if decoder is None:
            decoder = TomlDecoder(_dict)
        d = decoder.get_empty_table()
        for l in f:  # noqa: E741
            if op.exists(l):
                d.update(load(l, _dict, decoder))
            else:
                warn("Non-existent filename in list with at least one valid "
                     "filename")
        return d
    else:
        try:
            return loads(f.read(), _dict, decoder)
        except AttributeError:
            raise TypeError("You can only load a file descriptor, filename or "
                            "list")


_groupname_re = re.compile(r'^[A-Za-z0-9_-]+$')


def loads(s, _dict=dict, decoder=None):
    """Parses string as toml

    Args:
        s: String to be parsed
        _dict: (optional) Specifies the class of the returned toml dictionary

    Returns:
        Parsed toml file represented as a dictionary

    Raises:
        TypeError: When a non-string is passed
        TomlDecodeError: Error while decoding toml
    """

    implicitgroups = []
    if decoder is None:
        decoder = TomlDecoder(_dict)
    retval = decoder.get_empty_table()
    currentlevel = retval
    if not isinstance(s, basestring):
        raise TypeError("Expecting something like a string")

    if not isinstance(s, unicode):
        s = s.decode('utf8')

    original = s
    sl = list(s)
    openarr = 0
    openstring = False
    openstrchar = ""
    multilinestr = False
    arrayoftables = False
    beginline = True
    keygroup = False
    dottedkey = False
    keyname = 0
    key = ''
    prev_key = ''
    line_no = 1

    for i, item in enumerate(sl):
        if item == '\r' and sl[i + 1] == '\n':
            sl[i] = ' '
            continue
        if keyname:
            key += item
            if item == '\n':
                raise TomlDecodeError("Key name found without value."
                                      " Reached end of line.", original, i)
            if openstring:
                if item == openstrchar:
                    oddbackslash = False
                    k = 1
                    while i >= k and sl[i - k] == '\\':
                        oddbackslash = not oddbackslash
                        k += 1
                    if not oddbackslash:
                        keyname = 2
                        openstring = False
                        openstrchar = ""
                continue
            elif keyname == 1:
                if item.isspace():
                    keyname = 2
                    continue
                elif item == '.':
                    dottedkey = True
                    continue
                elif item.isalnum() or item == '_' or item == '-':
                    continue
                elif (dottedkey and sl[i - 1] == '.' and
                      (item == '"' or item == "'")):
                    openstring = True
                    openstrchar = item
                    continue
            elif keyname == 2:
                if item.isspace():
                    if dottedkey:
                        nextitem = sl[i + 1]
                        if not nextitem.isspace() and nextitem != '.':
                            keyname = 1
                    continue
                if item == '.':
                    dottedkey = True
                    nextitem = sl[i + 1]
                    if not nextitem.isspace() and nextitem != '.':
                        keyname = 1
                    continue
            if item == '=':
                keyname = 0
                prev_key = key[:-1].rstrip()
                key = ''
                dottedkey = False
            else:
                raise TomlDecodeError("Found invalid character in key name: '" +
                                      item + "'. Try quoting the key name.",
                                      original, i)
        if item == "'" and openstrchar != '"':
            k = 1
            try:
                while sl[i - k] == "'":
                    k += 1
                    if k == 3:
                        break
            except IndexError:
                pass
            if k == 3:
                multilinestr = not multilinestr
                openstring = multilinestr
            else:
                openstring = not openstring
            if openstring:
                openstrchar = "'"
            else:
                openstrchar = ""
        if item == '"' and openstrchar != "'":
            oddbackslash = False
            k = 1
            tripquote = False
            try:
                while sl[i - k] == '"':
                    k += 1
                    if k == 3:
                        tripquote = True
                        break
                if k == 1 or (k == 3 and tripquote):
                    while sl[i - k] == '\\':
                        oddbackslash = not oddbackslash
                        k += 1
            except IndexError:
                pass
            if not oddbackslash:
                if tripquote:
                    multilinestr = not multilinestr
                    openstring = multilinestr
                else:
                    openstring = not openstring
            if openstring:
                openstrchar = '"'
            else:
                openstrchar = ""
        if item == '#' and (not openstring and not keygroup and
                            not arrayoftables):
            j = i
            comment = ""
            try:
                while sl[j] != '\n':
                    comment += s[j]
                    sl[j] = ' '
                    j += 1
            except IndexError:
                break
            if not openarr:
                decoder.preserve_comment(line_no, prev_key, comment, beginline)
        if item == '[' and (not openstring and not keygroup and
                            not arrayoftables):
            if beginline:
                if len(sl) > i + 1 and sl[i + 1] == '[':
                    arrayoftables = True
                else:
                    keygroup = True
            else:
                openarr += 1
        if item == ']' and not openstring:
            if keygroup:
                keygroup = False
            elif arrayoftables:
                if sl[i - 1] == ']':
                    arrayoftables = False
            else:
                openarr -= 1
        if item == '\n':
            if openstring or multilinestr:
                if not multilinestr:
                    raise TomlDecodeError("Unbalanced quotes", original, i)
                if ((sl[i - 1] == "'" or sl[i - 1] == '"') and (
                        sl[i - 2] == sl[i - 1])):
                    sl[i] = sl[i - 1]
                    if sl[i - 3] == sl[i - 1]:
                        sl[i - 3] = ' '
            elif openarr:
                sl[i] = ' '
            else:
                beginline = True
            line_no += 1
        elif beginline and sl[i] != ' ' and sl[i] != '\t':
            beginline = False
            if not keygroup and not arrayoftables:
                if sl[i] == '=':
                    raise TomlDecodeError("Found empty keyname. ", original, i)
                keyname = 1
                key += item
    if keyname:
        raise TomlDecodeError("Key name found without value."
                              " Reached end of file.", original, len(s))
    if openstring:  # reached EOF and have an unterminated string
        raise TomlDecodeError("Unterminated string found."
                              " Reached end of file.", original, len(s))
    s = ''.join(sl)
    s = s.split('\n')
    multikey = None
    multilinestr = ""
    multibackslash = False
    pos = 0
    for idx, line in enumerate(s):
        if idx > 0:
            pos += len(s[idx - 1]) + 1

        decoder.embed_comments(idx, currentlevel)

        if not multilinestr or multibackslash or '\n' not in multilinestr:
            line = line.strip()
        if line == "" and (not multikey or multibackslash):
            continue
        if multikey:
            if multibackslash:
                multilinestr += line
            else:
                multilinestr += line
            multibackslash = False
            closed = False
            if multilinestr[0] == '[':
                closed = line[-1] == ']'
            elif len(line) > 2:
                closed = (line[-1] == multilinestr[0] and
                          line[-2] == multilinestr[0] and
                          line[-3] == multilinestr[0])
            if closed:
                try:
                    value, vtype = decoder.load_value(multilinestr)
                except ValueError as err:
                    raise TomlDecodeError(str(err), original, pos)
                currentlevel[multikey] = value
                multikey = None
                multilinestr = ""
            else:
                k = len(multilinestr) - 1
                while k > -1 and multilinestr[k] == '\\':
                    multibackslash = not multibackslash
                    k -= 1
                if multibackslash:
                    multilinestr = multilinestr[:-1]
                else:
                    multilinestr += "\n"
            continue
        if line[0] == '[':
            arrayoftables = False
            if len(line) == 1:
                raise TomlDecodeError("Opening key group bracket on line by "
                                      "itself.", original, pos)
            if line[1] == '[':
                arrayoftables = True
                line = line[2:]
                splitstr = ']]'
            else:
                line = line[1:]
                splitstr = ']'
            i = 1
            quotesplits = decoder._get_split_on_quotes(line)
            quoted = False
            for quotesplit in quotesplits:
                if not quoted and splitstr in quotesplit:
                    break
                i += quotesplit.count(splitstr)
                quoted = not quoted
            line = line.split(splitstr, i)
            if len(line) < i + 1 or line[-1].strip() != "":
                raise TomlDecodeError("Key group not on a line by itself.",
                                      original, pos)
            groups = splitstr.join(line[:-1]).split('.')
            i = 0
            while i < len(groups):
                groups[i] = groups[i].strip()
                if len(groups[i]) > 0 and (groups[i][0] == '"' or
                                           groups[i][0] == "'"):
                    groupstr = groups[i]
                    j = i + 1
                    while ((not groupstr[0] == groupstr[-1]) or
                           len(groupstr) == 1):
                        j += 1
                        if j > len(groups) + 2:
                            raise TomlDecodeError("Invalid group name '" +
                                                  groupstr + "' Something " +
                                                  "went wrong.", original, pos)
                        groupstr = '.'.join(groups[i:j]).strip()
                    groups[i] = groupstr[1:-1]
                    groups[i + 1:j] = []
                else:
                    if not _groupname_re.match(groups[i]):
                        raise TomlDecodeError("Invalid group name '" +
                                              groups[i] + "'. Try quoting it.",
                                              original, pos)
                i += 1
            currentlevel = retval
            for i in _range(len(groups)):
                group = groups[i]
                if group == "":
                    raise TomlDecodeError("Can't have a keygroup with an empty "
                                          "name", original, pos)
                try:
                    currentlevel[group]
                    if i == len(groups) - 1:
                        if group in implicitgroups:
                            implicitgroups.remove(group)
                            if arrayoftables:
                                raise TomlDecodeError("An implicitly defined "
                                                      "table can't be an array",
                                                      original, pos)
                        elif arrayoftables:
                            currentlevel[group].append(decoder.get_empty_table()
                                                       )
                        else:
                            raise TomlDecodeError("What? " + group +
                                                  " already exists?" +
                                                  str(currentlevel),
                                                  original, pos)
                except TypeError:
                    currentlevel = currentlevel[-1]
                    if group not in currentlevel:
                        currentlevel[group] = decoder.get_empty_table()
                        if i == len(groups) - 1 and arrayoftables:
                            currentlevel[group] = [decoder.get_empty_table()]
                except KeyError:
                    if i != len(groups) - 1:
                        implicitgroups.append(group)
                    currentlevel[group] = decoder.get_empty_table()
                    if i == len(groups) - 1 and arrayoftables:
                        currentlevel[group] = [decoder.get_empty_table()]
                currentlevel = currentlevel[group]
                if arrayoftables:
                    try:
                        currentlevel = currentlevel[-1]
                    except KeyError:
                        pass
        elif line[0] == "{":
            if line[-1] != "}":
                raise TomlDecodeError("Line breaks are not allowed in inline"
                                      "objects", original, pos)
            try:
                decoder.load_inline_object(line, currentlevel, multikey,
                                           multibackslash)
            except ValueError as err:
                raise TomlDecodeError(str(err), original, pos)
        elif "=" in line:
            try:
                ret = decoder.load_line(line, currentlevel, multikey,
                                        multibackslash)
            except ValueError as err:
                raise TomlDecodeError(str(err), original, pos)
            if ret is not None:
                multikey, multilinestr, multibackslash = ret
    return retval


def _load_date(val):
    microsecond = 0
    tz = None
    try:
        if len(val) > 19:
            if val[19] == '.':
                if val[-1].upper() == 'Z':
                    subsecondval = val[20:-1]
                    tzval = "Z"
                else:
                    subsecondvalandtz = val[20:]
                    if '+' in subsecondvalandtz:
                        splitpoint = subsecondvalandtz.index('+')
                        subsecondval = subsecondvalandtz[:splitpoint]
                        tzval = subsecondvalandtz[splitpoint:]
                    elif '-' in subsecondvalandtz:
                        splitpoint = subsecondvalandtz.index('-')
                        subsecondval = subsecondvalandtz[:splitpoint]
                        tzval = subsecondvalandtz[splitpoint:]
                    else:
                        tzval = None
                        subsecondval = subsecondvalandtz
                if tzval is not None:
                    tz = TomlTz(tzval)
                microsecond = int(int(subsecondval) *
                                  (10 ** (6 - len(subsecondval))))
            else:
                tz = TomlTz(val[19:])
    except ValueError:
        tz = None
    if "-" not in val[1:]:
        return None
    try:
        if len(val) == 10:
            d = datetime.date(
                int(val[:4]), int(val[5:7]),
                int(val[8:10]))
        else:
            d = datetime.datetime(
                int(val[:4]), int(val[5:7]),
                int(val[8:10]), int(val[11:13]),
                int(val[14:16]), int(val[17:19]), microsecond, tz)
    except ValueError:
        return None
    return d


def _load_unicode_escapes(v, hexbytes, prefix):
    skip = False
    i = len(v) - 1
    while i > -1 and v[i] == '\\':
        skip = not skip
        i -= 1
    for hx in hexbytes:
        if skip:
            skip = False
            i = len(hx) - 1
            while i > -1 and hx[i] == '\\':
                skip = not skip
                i -= 1
            v += prefix
            v += hx
            continue
        hxb = ""
        i = 0
        hxblen = 4
        if prefix == "\\U":
            hxblen = 8
        hxb = ''.join(hx[i:i + hxblen]).lower()
        if hxb.strip('0123456789abcdef'):
            raise ValueError("Invalid escape sequence: " + hxb)
        if hxb[0] == "d" and hxb[1].strip('01234567'):
            raise ValueError("Invalid escape sequence: " + hxb +
                             ". Only scalar unicode points are allowed.")
        v += unichr(int(hxb, 16))
        v += unicode(hx[len(hxb):])
    return v


# Unescape TOML string values.

# content after the \
_escapes = ['0', 'b', 'f', 'n', 'r', 't', '"']
# What it should be replaced by
_escapedchars = ['\0', '\b', '\f', '\n', '\r', '\t', '\"']
# Used for substitution
_escape_to_escapedchars = dict(zip(_escapes, _escapedchars))


def _unescape(v):
    """Unescape characters in a TOML string."""
    i = 0
    backslash = False
    while i < len(v):
        if backslash:
            backslash = False
            if v[i] in _escapes:
                v = v[:i - 1] + _escape_to_escapedchars[v[i]] + v[i + 1:]
            elif v[i] == '\\':
                v = v[:i - 1] + v[i:]
            elif v[i] == 'u' or v[i] == 'U':
                i += 1
            else:
                raise ValueError("Reserved escape sequence used")
            continue
        elif v[i] == '\\':
            backslash = True
        i += 1
    return v


class InlineTableDict(object):
    """Sentinel subclass of dict for inline tables."""


class TomlDecoder(object):

    def __init__(self, _dict=dict):
        self._dict = _dict

    def get_empty_table(self):
        return self._dict()

    def get_empty_inline_table(self):
        class DynamicInlineTableDict(self._dict, InlineTableDict):
            """Concrete sentinel subclass for inline tables.
            It is a subclass of _dict which is passed in dynamically at load
            time

            It is also a subclass of InlineTableDict
            """

        return DynamicInlineTableDict()

    def load_inline_object(self, line, currentlevel, multikey=False,
                           multibackslash=False):
        candidate_groups = line[1:-1].split(",")
        groups = []
        if len(candidate_groups) == 1 and not candidate_groups[0].strip():
            candidate_groups.pop()
        while len(candidate_groups) > 0:
            candidate_group = candidate_groups.pop(0)
            try:
                _, value = candidate_group.split('=', 1)
            except ValueError:
                raise ValueError("Invalid inline table encountered")
            value = value.strip()
            if ((value[0] == value[-1] and value[0] in ('"', "'")) or (
                    value[0] in '-0123456789' or
                    value in ('true', 'false') or
                    (value[0] == "[" and value[-1] == "]") or
                    (value[0] == '{' and value[-1] == '}'))):
                groups.append(candidate_group)
            elif len(candidate_groups) > 0:
                candidate_groups[0] = (candidate_group + "," +
                                       candidate_groups[0])
            else:
                raise ValueError("Invalid inline table value encountered")
        for group in groups:
            status = self.load_line(group, currentlevel, multikey,
                                    multibackslash)
            if status is not None:
                break

    def _get_split_on_quotes(self, line):
        doublequotesplits = line.split('"')
        quoted = False
        quotesplits = []
        if len(doublequotesplits) > 1 and "'" in doublequotesplits[0]:
            singlequotesplits = doublequotesplits[0].split("'")
            doublequotesplits = doublequotesplits[1:]
            while len(singlequotesplits) % 2 == 0 and len(doublequotesplits):
                singlequotesplits[-1] += '"' + doublequotesplits[0]
                doublequotesplits = doublequotesplits[1:]
                if "'" in singlequotesplits[-1]:
                    singlequotesplits = (singlequotesplits[:-1] +
                                         singlequotesplits[-1].split("'"))
            quotesplits += singlequotesplits
        for doublequotesplit in doublequotesplits:
            if quoted:
                quotesplits.append(doublequotesplit)
            else:
                quotesplits += doublequotesplit.split("'")
                quoted = not quoted
        return quotesplits

    def load_line(self, line, currentlevel, multikey, multibackslash):
        i = 1
        quotesplits = self._get_split_on_quotes(line)
        quoted = False
        for quotesplit in quotesplits:
            if not quoted and '=' in quotesplit:
                break
            i += quotesplit.count('=')
            quoted = not quoted
        pair = line.split('=', i)
        strictly_valid = _strictly_valid_num(pair[-1])
        if _number_with_underscores.match(pair[-1]):
            pair[-1] = pair[-1].replace('_', '')
        while len(pair[-1]) and (pair[-1][0] != ' ' and pair[-1][0] != '\t' and
                                 pair[-1][0] != "'" and pair[-1][0] != '"' and
                                 pair[-1][0] != '[' and pair[-1][0] != '{' and
                                 pair[-1].strip() != 'true' and
                                 pair[-1].strip() != 'false'):
            try:
                float(pair[-1])
                break
            except ValueError:
                pass
            if _load_date(pair[-1]) is not None:
                break
            if TIME_RE.match(pair[-1]):
                break
            i += 1
            prev_val = pair[-1]
            pair = line.split('=', i)
            if prev_val == pair[-1]:
                raise ValueError("Invalid date or number")
            if strictly_valid:
                strictly_valid = _strictly_valid_num(pair[-1])
        pair = ['='.join(pair[:-1]).strip(), pair[-1].strip()]
        if '.' in pair[0]:
            if '"' in pair[0] or "'" in pair[0]:
                quotesplits = self._get_split_on_quotes(pair[0])
                quoted = False
                levels = []
                for quotesplit in quotesplits:
                    if quoted:
                        levels.append(quotesplit)
                    else:
                        levels += [level.strip() for level in
                                   quotesplit.split('.')]
                    quoted = not quoted
            else:
                levels = pair[0].split('.')
            while levels[-1] == "":
                levels = levels[:-1]
            for level in levels[:-1]:
                if level == "":
                    continue
                if level not in currentlevel:
                    currentlevel[level] = self.get_empty_table()
                currentlevel = currentlevel[level]
            pair[0] = levels[-1].strip()
        elif (pair[0][0] == '"' or pair[0][0] == "'") and \
                (pair[0][-1] == pair[0][0]):
            pair[0] = _unescape(pair[0][1:-1])
        k, koffset = self._load_line_multiline_str(pair[1])
        if k > -1:
            while k > -1 and pair[1][k + koffset] == '\\':
                multibackslash = not multibackslash
                k -= 1
            if multibackslash:
                multilinestr = pair[1][:-1]
            else:
                multilinestr = pair[1] + "\n"
            multikey = pair[0]
        else:
            value, vtype = self.load_value(pair[1], strictly_valid)
        try:
            currentlevel[pair[0]]
            raise ValueError("Duplicate keys!")
        except TypeError:
            raise ValueError("Duplicate keys!")
        except KeyError:
            if multikey:
                return multikey, multilinestr, multibackslash
            else:
                currentlevel[pair[0]] = value

    def _load_line_multiline_str(self, p):
        poffset = 0
        if len(p) < 3:
            return -1, poffset
        if p[0] == '[' and (p.strip()[-1] != ']' and
                            self._load_array_isstrarray(p)):
            newp = p[1:].strip().split(',')
            while len(newp) > 1 and newp[-1][0] != '"' and newp[-1][0] != "'":
                newp = newp[:-2] + [newp[-2] + ',' + newp[-1]]
            newp = newp[-1]
            poffset = len(p) - len(newp)
            p = newp
        if p[0] != '"' and p[0] != "'":
            return -1, poffset
        if p[1] != p[0] or p[2] != p[0]:
            return -1, poffset
        if len(p) > 5 and p[-1] == p[0] and p[-2] == p[0] and p[-3] == p[0]:
            return -1, poffset
        return len(p) - 1, poffset

    def load_value(self, v, strictly_valid=True):
        if not v:
            raise ValueError("Empty value is invalid")
        if v == 'true':
            return (True, "bool")
        elif v.lower() == 'true':
            raise ValueError("Only all lowercase booleans allowed")
        elif v == 'false':
            return (False, "bool")
        elif v.lower() == 'false':
            raise ValueError("Only all lowercase booleans allowed")
        elif v[0] == '"' or v[0] == "'":
            quotechar = v[0]
            testv = v[1:].split(quotechar)
            triplequote = False
            triplequotecount = 0
            if len(testv) > 1 and testv[0] == '' and testv[1] == '':
                testv = testv[2:]
                triplequote = True
            closed = False
            for tv in testv:
                if tv == '':
                    if triplequote:
                        triplequotecount += 1
                    else:
                        closed = True
                else:
                    oddbackslash = False
                    try:
                        i = -1
                        j = tv[i]
                        while j == '\\':
                            oddbackslash = not oddbackslash
                            i -= 1
                            j = tv[i]
                    except IndexError:
                        pass
                    if not oddbackslash:
                        if closed:
                            raise ValueError("Found tokens after a closed " +
                                             "string. Invalid TOML.")
                        else:
                            if not triplequote or triplequotecount > 1:
                                closed = True
                            else:
                                triplequotecount = 0
            if quotechar == '"':
                escapeseqs = v.split('\\')[1:]
                backslash = False
                for i in escapeseqs:
                    if i == '':
                        backslash = not backslash
                    else:
                        if i[0] not in _escapes and (i[0] != 'u' and
                                                     i[0] != 'U' and
                                                     not backslash):
                            raise ValueError("Reserved escape sequence used")
                        if backslash:
                            backslash = False
                for prefix in ["\\u", "\\U"]:
                    if prefix in v:
                        hexbytes = v.split(prefix)
                        v = _load_unicode_escapes(hexbytes[0], hexbytes[1:],
                                                  prefix)
                v = _unescape(v)
            if len(v) > 1 and v[1] == quotechar and (len(v) < 3 or
                                                     v[1] == v[2]):
                v = v[2:-2]
            return (v[1:-1], "str")
        elif v[0] == '[':
            return (self.load_array(v), "array")
        elif v[0] == '{':
            inline_object = self.get_empty_inline_table()
            self.load_inline_object(v, inline_object)
            return (inline_object, "inline_object")
        elif TIME_RE.match(v):
            h, m, s, _, ms = TIME_RE.match(v).groups()
            time = datetime.time(int(h), int(m), int(s), int(ms) if ms else 0)
            return (time, "time")
        else:
            parsed_date = _load_date(v)
            if parsed_date is not None:
                return (parsed_date, "date")
            if not strictly_valid:
                raise ValueError("Weirdness with leading zeroes or "
                                 "underscores in your number.")
            itype = "int"
            neg = False
            if v[0] == '-':
                neg = True
                v = v[1:]
            elif v[0] == '+':
                v = v[1:]
            v = v.replace('_', '')
            lowerv = v.lower()
            if '.' in v or ('x' not in v and ('e' in v or 'E' in v)):
                if '.' in v and v.split('.', 1)[1] == '':
                    raise ValueError("This float is missing digits after "
                                     "the point")
                if v[0] not in '0123456789':
                    raise ValueError("This float doesn't have a leading "
                                     "digit")
                v = float(v)
                itype = "float"
            elif len(lowerv) == 3 and (lowerv == 'inf' or lowerv == 'nan'):
                v = float(v)
                itype = "float"
            if itype == "int":
                v = int(v, 0)
            if neg:
                return (0 - v, itype)
            return (v, itype)

    def bounded_string(self, s):
        if len(s) == 0:
            return True
        if s[-1] != s[0]:
            return False
        i = -2
        backslash = False
        while len(s) + i > 0:
            if s[i] == "\\":
                backslash = not backslash
                i -= 1
            else:
                break
        return not backslash

    def _load_array_isstrarray(self, a):
        a = a[1:-1].strip()
        if a != '' and (a[0] == '"' or a[0] == "'"):
            return True
        return False

    def load_array(self, a):
        atype = None
        retval = []
        a = a.strip()
        if '[' not in a[1:-1] or "" != a[1:-1].split('[')[0].strip():
            strarray = self._load_array_isstrarray(a)
            if not a[1:-1].strip().startswith('{'):
                a = a[1:-1].split(',')
            else:
                # a is an inline object, we must find the matching parenthesis
                # to define groups
                new_a = []
                start_group_index = 1
                end_group_index = 2
                open_bracket_count = 1 if a[start_group_index] == '{' else 0
                in_str = False
                while end_group_index < len(a[1:]):
                    if a[end_group_index] == '"' or a[end_group_index] == "'":
                        if in_str:
                            backslash_index = end_group_index - 1
                            while (backslash_index > -1 and
                                   a[backslash_index] == '\\'):
                                in_str = not in_str
                                backslash_index -= 1
                        in_str = not in_str
                    if not in_str and a[end_group_index] == '{':
                        open_bracket_count += 1
                    if in_str or a[end_group_index] != '}':
                        end_group_index += 1
                        continue
                    elif a[end_group_index] == '}' and open_bracket_count > 1:
                        open_bracket_count -= 1
                        end_group_index += 1
                        continue

                    # Increase end_group_index by 1 to get the closing bracket
                    end_group_index += 1

                    new_a.append(a[start_group_index:end_group_index])

                    # The next start index is at least after the closing
                    # bracket, a closing bracket can be followed by a comma
                    # since we are in an array.
                    start_group_index = end_group_index + 1
                    while (start_group_index < len(a[1:]) and
                           a[start_group_index] != '{'):
                        start_group_index += 1
                    end_group_index = start_group_index + 1
                a = new_a
            b = 0
            if strarray:
                while b < len(a) - 1:
                    ab = a[b].strip()
                    while (not self.bounded_string(ab) or
                           (len(ab) > 2 and
                            ab[0] == ab[1] == ab[2] and
                            ab[-2] != ab[0] and
                            ab[-3] != ab[0])):
                        a[b] = a[b] + ',' + a[b + 1]
                        ab = a[b].strip()
                        if b < len(a) - 2:
                            a = a[:b + 1] + a[b + 2:]
                        else:
                            a = a[:b + 1]
                    b += 1
        else:
            al = list(a[1:-1])
            a = []
            openarr = 0
            j = 0
            for i in _range(len(al)):
                if al[i] == '[':
                    openarr += 1
                elif al[i] == ']':
                    openarr -= 1
                elif al[i] == ',' and not openarr:
                    a.append(''.join(al[j:i]))
                    j = i + 1
            a.append(''.join(al[j:]))
        for i in _range(len(a)):
            a[i] = a[i].strip()
            if a[i] != '':
                nval, ntype = self.load_value(a[i])
                if atype:
                    if ntype != atype:
                        raise ValueError("Not a homogeneous array")
                else:
                    atype = ntype
                retval.append(nval)
        return retval

    def preserve_comment(self, line_no, key, comment, beginline):
        pass

    def embed_comments(self, idx, currentlevel):
        pass


class TomlPreserveCommentDecoder(TomlDecoder):

    def __init__(self, _dict=dict):
        self.saved_comments = {}
        super(TomlPreserveCommentDecoder, self).__init__(_dict)

    def preserve_comment(self, line_no, key, comment, beginline):
        self.saved_comments[line_no] = (key, comment, beginline)

    def embed_comments(self, idx, currentlevel):
        if idx not in self.saved_comments:
            return

        key, comment, beginline = self.saved_comments[idx]
        currentlevel[key] = CommentValue(currentlevel[key], comment, beginline,
                                         self._dict)

# === NexusCore/openenv\Lib\site-packages\anthropic\lib\streaming\_prompt_caching_beta_types.py ===
from typing import Union
from typing_extensions import Literal

from ._types import (
    TextEvent,
    InputJsonEvent,
    RawMessageDeltaEvent,
    ContentBlockStopEvent,
    RawContentBlockDeltaEvent,
    RawContentBlockStartEvent,
)
from ...types import RawMessageStopEvent
from ...types.beta.prompt_caching import PromptCachingBetaMessage, RawPromptCachingBetaMessageStartEvent


class MessageStopEvent(RawMessageStopEvent):
    type: Literal["message_stop"]

    message: PromptCachingBetaMessage


PromptCachingBetaMessageStreamEvent = Union[
    RawPromptCachingBetaMessageStartEvent,
    MessageStopEvent,
    # same as non-beta
    TextEvent,
    InputJsonEvent,
    RawMessageDeltaEvent,
    RawContentBlockStartEvent,
    RawContentBlockDeltaEvent,
    ContentBlockStopEvent,
]

# === NexusCore/openenv\Lib\site-packages\IPython\lib\lexers.py ===
# -*- coding: utf-8 -*-
"""
The IPython lexers are now a separate package, ipython-pygments-lexers.

Importing from here is deprecated and may break in the future.
"""
# -----------------------------------------------------------------------------
# Copyright (c) 2013, the IPython Development Team.
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file COPYING.txt, distributed with this software.
# -----------------------------------------------------------------------------

from ipython_pygments_lexers import (
    IPythonLexer,
    IPython3Lexer,
    IPythonPartialTracebackLexer,
    IPythonTracebackLexer,
    IPythonConsoleLexer,
    IPyLexer,
)


__all__ = [
    "IPython3Lexer",
    "IPythonLexer",
    "IPythonPartialTracebackLexer",
    "IPythonTracebackLexer",
    "IPythonConsoleLexer",
    "IPyLexer",
]

# === NexusCore/openenv\Lib\site-packages\numpy\lib\tests\test_array_utils.py ===
import numpy as np
from numpy.lib import array_utils
from numpy.testing import assert_equal


class TestByteBounds:
    def test_byte_bounds(self):
        # pointer difference matches size * itemsize
        # due to contiguity
        a = np.arange(12).reshape(3, 4)
        low, high = array_utils.byte_bounds(a)
        assert_equal(high - low, a.size * a.itemsize)

    def test_unusual_order_positive_stride(self):
        a = np.arange(12).reshape(3, 4)
        b = a.T
        low, high = array_utils.byte_bounds(b)
        assert_equal(high - low, b.size * b.itemsize)

    def test_unusual_order_negative_stride(self):
        a = np.arange(12).reshape(3, 4)
        b = a.T[::-1]
        low, high = array_utils.byte_bounds(b)
        assert_equal(high - low, b.size * b.itemsize)

    def test_strided(self):
        a = np.arange(12)
        b = a[::2]
        low, high = array_utils.byte_bounds(b)
        # the largest pointer address is lost (even numbers only in the
        # stride), and compensate addresses for striding by 2
        assert_equal(high - low, b.size * 2 * b.itemsize - b.itemsize)

# === NexusCore/openenv\Lib\site-packages\pygments\lexers\asm.py ===
"""
    pygments.lexers.asm
    ~~~~~~~~~~~~~~~~~~~

    Lexers for assembly languages.

    :copyright: Copyright 2006-2025 by the Pygments team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

import re

from pygments.lexer import RegexLexer, include, bygroups, using, words, \
    DelegatingLexer, default
from pygments.lexers.c_cpp import CppLexer, CLexer
from pygments.lexers.d import DLexer
from pygments.token import Text, Name, Number, String, Comment, Punctuation, \
    Other, Keyword, Operator, Whitespace

__all__ = ['GasLexer', 'ObjdumpLexer', 'DObjdumpLexer', 'CppObjdumpLexer',
           'CObjdumpLexer', 'HsailLexer', 'LlvmLexer', 'LlvmMirBodyLexer',
           'LlvmMirLexer', 'NasmLexer', 'NasmObjdumpLexer', 'TasmLexer',
           'Ca65Lexer', 'Dasm16Lexer']


class GasLexer(RegexLexer):
    """
    For Gas (AT&T) assembly code.
    """
    name = 'GAS'
    aliases = ['gas', 'asm']
    filenames = ['*.s', '*.S']
    mimetypes = ['text/x-gas']
    url = 'https://www.gnu.org/software/binutils'
    version_added = ''

    #: optional Comment or Whitespace
    string = r'"(\\"|[^"])*"'
    char = r'[\w$.@-]'
    identifier = r'(?:[a-zA-Z$_]' + char + r'*|\.' + char + '+)'
    number = r'(?:0[xX][a-fA-F0-9]+|#?-?\d+)'
    register = '%' + identifier + r'\b'

    tokens = {
        'root': [
            include('whitespace'),
            (identifier + ':', Name.Label),
            (r'\.' + identifier, Name.Attribute, 'directive-args'),
            (r'lock|rep(n?z)?|data\d+', Name.Attribute),
            (identifier, Name.Function, 'instruction-args'),
            (r'[\r\n]+', Text)
        ],
        'directive-args': [
            (identifier, Name.Constant),
            (string, String),
            ('@' + identifier, Name.Attribute),
            (number, Number.Integer),
            (register, Name.Variable),
            (r'[\r\n]+', Whitespace, '#pop'),
            (r'([;#]|//).*?\n', Comment.Single, '#pop'),
            (r'/[*].*?[*]/', Comment.Multiline),
            (r'/[*].*?\n[\w\W]*?[*]/', Comment.Multiline, '#pop'),

            include('punctuation'),
            include('whitespace')
        ],
        'instruction-args': [
            # For objdump-disassembled code, shouldn't occur in
            # actual assembler input
            ('([a-z0-9]+)( )(<)('+identifier+')(>)',
                bygroups(Number.Hex, Text, Punctuation, Name.Constant,
                         Punctuation)),
            ('([a-z0-9]+)( )(<)('+identifier+')([-+])('+number+')(>)',
                bygroups(Number.Hex, Text, Punctuation, Name.Constant,
                         Punctuation, Number.Integer, Punctuation)),

            # Address constants
            (identifier, Name.Constant),
            (number, Number.Integer),
            # Registers
            (register, Name.Variable),
            # Numeric constants
            ('$'+number, Number.Integer),
            (r"$'(.|\\')'", String.Char),
            (r'[\r\n]+', Whitespace, '#pop'),
            (r'([;#]|//).*?\n', Comment.Single, '#pop'),
            (r'/[*].*?[*]/', Comment.Multiline),
            (r'/[*].*?\n[\w\W]*?[*]/', Comment.Multiline, '#pop'),

            include('punctuation'),
            include('whitespace')
        ],
        'whitespace': [
            (r'\n', Whitespace),
            (r'\s+', Whitespace),
            (r'([;#]|//).*?\n', Comment.Single),
            (r'/[*][\w\W]*?[*]/', Comment.Multiline)
        ],
        'punctuation': [
            (r'[-*,.()\[\]!:{}]+', Punctuation)
        ]
    }

    def analyse_text(text):
        if re.search(r'^\.(text|data|section)', text, re.M):
            return True
        elif re.search(r'^\.\w+', text, re.M):
            return 0.1


def _objdump_lexer_tokens(asm_lexer):
    """
    Common objdump lexer tokens to wrap an ASM lexer.
    """
    hex_re = r'[0-9A-Za-z]'
    return {
        'root': [
            # File name & format:
            ('(.*?)(:)( +file format )(.*?)$',
                bygroups(Name.Label, Punctuation, Text, String)),
            # Section header
            ('(Disassembly of section )(.*?)(:)$',
                bygroups(Text, Name.Label, Punctuation)),
            # Function labels
            # (With offset)
            ('('+hex_re+'+)( )(<)(.*?)([-+])(0[xX][A-Za-z0-9]+)(>:)$',
                bygroups(Number.Hex, Whitespace, Punctuation, Name.Function,
                         Punctuation, Number.Hex, Punctuation)),
            # (Without offset)
            ('('+hex_re+'+)( )(<)(.*?)(>:)$',
                bygroups(Number.Hex, Whitespace, Punctuation, Name.Function,
                         Punctuation)),
            # Code line with disassembled instructions
            ('( *)('+hex_re+r'+:)(\t)((?:'+hex_re+hex_re+' )+)( *\t)([a-zA-Z].*?)$',
                bygroups(Whitespace, Name.Label, Whitespace, Number.Hex, Whitespace,
                         using(asm_lexer))),
            # Code line without raw instructions (objdump --no-show-raw-insn)
            ('( *)('+hex_re+r'+:)( *\t)([a-zA-Z].*?)$',
                bygroups(Whitespace, Name.Label, Whitespace,
                         using(asm_lexer))),
            # Code line with ascii
            ('( *)('+hex_re+r'+:)(\t)((?:'+hex_re+hex_re+' )+)( *)(.*?)$',
                bygroups(Whitespace, Name.Label, Whitespace, Number.Hex, Whitespace, String)),
            # Continued code line, only raw opcodes without disassembled
            # instruction
            ('( *)('+hex_re+r'+:)(\t)((?:'+hex_re+hex_re+' )+)$',
                bygroups(Whitespace, Name.Label, Whitespace, Number.Hex)),
            # Skipped a few bytes
            (r'\t\.\.\.$', Text),
            # Relocation line
            # (With offset)
            (r'(\t\t\t)('+hex_re+r'+:)( )([^\t]+)(\t)(.*?)([-+])(0x'+hex_re+'+)$',
                bygroups(Whitespace, Name.Label, Whitespace, Name.Property, Whitespace,
                         Name.Constant, Punctuation, Number.Hex)),
            # (Without offset)
            (r'(\t\t\t)('+hex_re+r'+:)( )([^\t]+)(\t)(.*?)$',
                bygroups(Whitespace, Name.Label, Whitespace, Name.Property, Whitespace,
                         Name.Constant)),
            (r'[^\n]+\n', Other)
        ]
    }


class ObjdumpLexer(RegexLexer):
    """
    For the output of ``objdump -dr``.
    """
    name = 'objdump'
    aliases = ['objdump']
    filenames = ['*.objdump']
    mimetypes = ['text/x-objdump']
    url = 'https://www.gnu.org/software/binutils'
    version_added = ''

    tokens = _objdump_lexer_tokens(GasLexer)


class DObjdumpLexer(DelegatingLexer):
    """
    For the output of ``objdump -Sr`` on compiled D files.
    """
    name = 'd-objdump'
    aliases = ['d-objdump']
    filenames = ['*.d-objdump']
    mimetypes = ['text/x-d-objdump']
    url = 'https://www.gnu.org/software/binutils'
    version_added = ''

    def __init__(self, **options):
        super().__init__(DLexer, ObjdumpLexer, **options)


class CppObjdumpLexer(DelegatingLexer):
    """
    For the output of ``objdump -Sr`` on compiled C++ files.
    """
    name = 'cpp-objdump'
    aliases = ['cpp-objdump', 'c++-objdumb', 'cxx-objdump']
    filenames = ['*.cpp-objdump', '*.c++-objdump', '*.cxx-objdump']
    mimetypes = ['text/x-cpp-objdump']
    url = 'https://www.gnu.org/software/binutils'
    version_added = ''

    def __init__(self, **options):
        super().__init__(CppLexer, ObjdumpLexer, **options)


class CObjdumpLexer(DelegatingLexer):
    """
    For the output of ``objdump -Sr`` on compiled C files.
    """
    name = 'c-objdump'
    aliases = ['c-objdump']
    filenames = ['*.c-objdump']
    mimetypes = ['text/x-c-objdump']
    url = 'https://www.gnu.org/software/binutils'
    version_added = ''


    def __init__(self, **options):
        super().__init__(CLexer, ObjdumpLexer, **options)


class HsailLexer(RegexLexer):
    """
    For HSAIL assembly code.
    """
    name = 'HSAIL'
    aliases = ['hsail', 'hsa']
    filenames = ['*.hsail']
    mimetypes = ['text/x-hsail']
    url = 'https://en.wikipedia.org/wiki/Heterogeneous_System_Architecture#HSA_Intermediate_Layer'
    version_added = '2.2'

    string = r'"[^"]*?"'
    identifier = r'[a-zA-Z_][\w.]*'
    # Registers
    register_number = r'[0-9]+'
    register = r'(\$(c|s|d|q)' + register_number + r')\b'
    # Qualifiers
    alignQual = r'(align\(\d+\))'
    widthQual = r'(width\((\d+|all)\))'
    allocQual = r'(alloc\(agent\))'
    # Instruction Modifiers
    roundingMod = (r'((_ftz)?(_up|_down|_zero|_near))')
    datatypeMod = (r'_('
                   # packedTypes
                   r'u8x4|s8x4|u16x2|s16x2|u8x8|s8x8|u16x4|s16x4|u32x2|s32x2|'
                   r'u8x16|s8x16|u16x8|s16x8|u32x4|s32x4|u64x2|s64x2|'
                   r'f16x2|f16x4|f16x8|f32x2|f32x4|f64x2|'
                   # baseTypes
                   r'u8|s8|u16|s16|u32|s32|u64|s64|'
                   r'b128|b8|b16|b32|b64|b1|'
                   r'f16|f32|f64|'
                   # opaqueType
                   r'roimg|woimg|rwimg|samp|sig32|sig64)')

    # Numeric Constant
    float = r'((\d+\.)|(\d*\.\d+))[eE][+-]?\d+'
    hexfloat = r'0[xX](([0-9a-fA-F]+\.[0-9a-fA-F]*)|([0-9a-fA-F]*\.[0-9a-fA-F]+))[pP][+-]?\d+'
    ieeefloat = r'0((h|H)[0-9a-fA-F]{4}|(f|F)[0-9a-fA-F]{8}|(d|D)[0-9a-fA-F]{16})'

    tokens = {
        'root': [
            include('whitespace'),
            include('comments'),

            (string, String),

            (r'@' + identifier + ':?', Name.Label),

            (register, Name.Variable.Anonymous),

            include('keyword'),

            (r'&' + identifier, Name.Variable.Global),
            (r'%' + identifier, Name.Variable),

            (hexfloat, Number.Hex),
            (r'0[xX][a-fA-F0-9]+', Number.Hex),
            (ieeefloat, Number.Float),
            (float, Number.Float),
            (r'\d+', Number.Integer),

            (r'[=<>{}\[\]()*.,:;!]|x\b', Punctuation)
        ],
        'whitespace': [
            (r'(\n|\s)+', Whitespace),
        ],
        'comments': [
            (r'/\*.*?\*/', Comment.Multiline),
            (r'//.*?\n', Comment.Single),
        ],
        'keyword': [
            # Types
            (r'kernarg' + datatypeMod, Keyword.Type),

            # Regular keywords
            (r'\$(full|base|small|large|default|zero|near)', Keyword),
            (words((
                'module', 'extension', 'pragma', 'prog', 'indirect', 'signature',
                'decl', 'kernel', 'function', 'enablebreakexceptions',
                'enabledetectexceptions', 'maxdynamicgroupsize', 'maxflatgridsize',
                'maxflatworkgroupsize', 'requireddim', 'requiredgridsize',
                'requiredworkgroupsize', 'requirenopartialworkgroups'),
                suffix=r'\b'), Keyword),

            # instructions
            (roundingMod, Keyword),
            (datatypeMod, Keyword),
            (r'_(' + alignQual + '|' + widthQual + ')', Keyword),
            (r'_kernarg', Keyword),
            (r'(nop|imagefence)\b', Keyword),
            (words((
                'cleardetectexcept', 'clock', 'cuid', 'debugtrap', 'dim',
                'getdetectexcept', 'groupbaseptr', 'kernargbaseptr', 'laneid',
                'maxcuid', 'maxwaveid', 'packetid', 'setdetectexcept', 'waveid',
                'workitemflatabsid', 'workitemflatid', 'nullptr', 'abs', 'bitrev',
                'currentworkgroupsize', 'currentworkitemflatid', 'fract', 'ncos',
                'neg', 'nexp2', 'nlog2', 'nrcp', 'nrsqrt', 'nsin', 'nsqrt',
                'gridgroups', 'gridsize', 'not', 'sqrt', 'workgroupid',
                'workgroupsize', 'workitemabsid', 'workitemid', 'ceil', 'floor',
                'rint', 'trunc', 'add', 'bitmask', 'borrow', 'carry', 'copysign',
                'div', 'rem', 'sub', 'shl', 'shr', 'and', 'or', 'xor', 'unpackhi',
                'unpacklo', 'max', 'min', 'fma', 'mad', 'bitextract', 'bitselect',
                'shuffle', 'cmov', 'bitalign', 'bytealign', 'lerp', 'nfma', 'mul',
                'mulhi', 'mul24hi', 'mul24', 'mad24', 'mad24hi', 'bitinsert',
                'combine', 'expand', 'lda', 'mov', 'pack', 'unpack', 'packcvt',
                'unpackcvt', 'sad', 'sementp', 'ftos', 'stof', 'cmp', 'ld', 'st',
                '_eq', '_ne', '_lt', '_le', '_gt', '_ge', '_equ', '_neu', '_ltu',
                '_leu', '_gtu', '_geu', '_num', '_nan', '_seq', '_sne', '_slt',
                '_sle', '_sgt', '_sge', '_snum', '_snan', '_sequ', '_sneu', '_sltu',
                '_sleu', '_sgtu', '_sgeu', 'atomic', '_ld', '_st', '_cas', '_add',
                '_and', '_exch', '_max', '_min', '_or', '_sub', '_wrapdec',
                '_wrapinc', '_xor', 'ret', 'cvt', '_readonly', '_kernarg', '_global',
                'br', 'cbr', 'sbr', '_scacq', '_screl', '_scar', '_rlx', '_wave',
                '_wg', '_agent', '_system', 'ldimage', 'stimage', '_v2', '_v3', '_v4',
                '_1d', '_2d', '_3d', '_1da', '_2da', '_1db', '_2ddepth', '_2dadepth',
                '_width', '_height', '_depth', '_array', '_channelorder',
                '_channeltype', 'querysampler', '_coord', '_filter', '_addressing',
                'barrier', 'wavebarrier', 'initfbar', 'joinfbar', 'waitfbar',
                'arrivefbar', 'leavefbar', 'releasefbar', 'ldf', 'activelaneid',
                'activelanecount', 'activelanemask', 'activelanepermute', 'call',
                'scall', 'icall', 'alloca', 'packetcompletionsig',
                'addqueuewriteindex', 'casqueuewriteindex', 'ldqueuereadindex',
                'stqueuereadindex', 'readonly', 'global', 'private', 'group',
                'spill', 'arg', '_upi', '_downi', '_zeroi', '_neari', '_upi_sat',
                '_downi_sat', '_zeroi_sat', '_neari_sat', '_supi', '_sdowni',
                '_szeroi', '_sneari', '_supi_sat', '_sdowni_sat', '_szeroi_sat',
                '_sneari_sat', '_pp', '_ps', '_sp', '_ss', '_s', '_p', '_pp_sat',
                '_ps_sat', '_sp_sat', '_ss_sat', '_s_sat', '_p_sat')), Keyword),

            # Integer types
            (r'i[1-9]\d*', Keyword)
        ]
    }


class LlvmLexer(RegexLexer):
    """
    For LLVM assembly code.
    """
    name = 'LLVM'
    url = 'https://llvm.org/docs/LangRef.html'
    aliases = ['llvm']
    filenames = ['*.ll']
    mimetypes = ['text/x-llvm']
    version_added = ''

    #: optional Comment or Whitespace
    string = r'"[^"]*?"'
    identifier = r'([-a-zA-Z$._][\w\-$.]*|' + string + ')'
    block_label = r'(' + identifier + r'|(\d+))'

    tokens = {
        'root': [
            include('whitespace'),

            # Before keywords, because keywords are valid label names :(...
            (block_label + r'\s*:', Name.Label),

            include('keyword'),

            (r'%' + identifier, Name.Variable),
            (r'@' + identifier, Name.Variable.Global),
            (r'%\d+', Name.Variable.Anonymous),
            (r'@\d+', Name.Variable.Global),
            (r'#\d+', Name.Variable.Global),
            (r'!' + identifier, Name.Variable),
            (r'!\d+', Name.Variable.Anonymous),
            (r'c?' + string, String),

            (r'0[xX][KLMHR]?[a-fA-F0-9]+', Number),
            (r'-?\d+(?:[.]\d+)?(?:[eE][-+]?\d+(?:[.]\d+)?)?', Number),

            (r'[=<>{}\[\]()*.,!]|x\b', Punctuation)
        ],
        'whitespace': [
            (r'(\n|\s+)+', Whitespace),
            (r';.*?\n', Comment)
        ],
        'keyword': [
            # Regular keywords
            (words((
                'aarch64_sve_vector_pcs', 'aarch64_vector_pcs', 'acq_rel',
                'acquire', 'add', 'addrspace', 'addrspacecast', 'afn', 'alias',
                'aliasee', 'align', 'alignLog2', 'alignstack', 'alloca',
                'allocsize', 'allOnes', 'alwaysinline', 'alwaysInline',
                'amdgpu_cs', 'amdgpu_es', 'amdgpu_gfx', 'amdgpu_gs',
                'amdgpu_hs', 'amdgpu_kernel', 'amdgpu_ls', 'amdgpu_ps',
                'amdgpu_vs', 'and', 'any', 'anyregcc', 'appending', 'arcp',
                'argmemonly', 'args', 'arm_aapcs_vfpcc', 'arm_aapcscc',
                'arm_apcscc', 'ashr', 'asm', 'atomic', 'atomicrmw',
                'attributes', 'available_externally', 'avr_intrcc',
                'avr_signalcc', 'bit', 'bitcast', 'bitMask', 'blockaddress',
                'blockcount', 'br', 'branchFunnel', 'builtin', 'byArg',
                'byref', 'byte', 'byteArray', 'byval', 'c', 'call', 'callbr',
                'callee', 'caller', 'calls', 'canAutoHide', 'catch',
                'catchpad', 'catchret', 'catchswitch', 'cc', 'ccc',
                'cfguard_checkcc', 'cleanup', 'cleanuppad', 'cleanupret',
                'cmpxchg', 'cold', 'coldcc', 'comdat', 'common', 'constant',
                'contract', 'convergent', 'critical', 'cxx_fast_tlscc',
                'datalayout', 'declare', 'default', 'define', 'deplibs',
                'dereferenceable', 'dereferenceable_or_null', 'distinct',
                'dllexport', 'dllimport', 'dso_local', 'dso_local_equivalent',
                'dso_preemptable', 'dsoLocal', 'eq', 'exact', 'exactmatch',
                'extern_weak', 'external', 'externally_initialized',
                'extractelement', 'extractvalue', 'fadd', 'false', 'fast',
                'fastcc', 'fcmp', 'fdiv', 'fence', 'filter', 'flags', 'fmul',
                'fneg', 'fpext', 'fptosi', 'fptoui', 'fptrunc', 'freeze',
                'frem', 'from', 'fsub', 'funcFlags', 'function', 'gc',
                'getelementptr', 'ghccc', 'global', 'guid', 'gv', 'hash',
                'hhvm_ccc', 'hhvmcc', 'hidden', 'hot', 'hotness', 'icmp',
                'ifunc', 'inaccessiblemem_or_argmemonly',
                'inaccessiblememonly', 'inalloca', 'inbounds', 'indir',
                'indirectbr', 'info', 'initialexec', 'inline', 'inlineBits',
                'inlinehint', 'inrange', 'inreg', 'insertelement',
                'insertvalue', 'insts', 'intel_ocl_bicc', 'inteldialect',
                'internal', 'inttoptr', 'invoke', 'jumptable', 'kind',
                'landingpad', 'largest', 'linkage', 'linkonce', 'linkonce_odr',
                'live', 'load', 'local_unnamed_addr', 'localdynamic',
                'localexec', 'lshr', 'max', 'metadata', 'min', 'minsize',
                'module', 'monotonic', 'msp430_intrcc', 'mul', 'mustprogress',
                'musttail', 'naked', 'name', 'nand', 'ne', 'nest', 'ninf',
                'nnan', 'noalias', 'nobuiltin', 'nocallback', 'nocapture',
                'nocf_check', 'noduplicate', 'noduplicates', 'nofree',
                'noimplicitfloat', 'noinline', 'noInline', 'nomerge', 'none',
                'nonlazybind', 'nonnull', 'noprofile', 'norecurse',
                'noRecurse', 'noredzone', 'noreturn', 'nosync', 'notail',
                'notEligibleToImport', 'noundef', 'nounwind', 'nsw',
                'nsz', 'null', 'null_pointer_is_valid', 'nuw', 'oeq', 'offset',
                'oge', 'ogt', 'ole', 'olt', 'one', 'opaque', 'optforfuzzing',
                'optnone', 'optsize', 'or', 'ord', 'param', 'params',
                'partition', 'path', 'personality', 'phi', 'poison',
                'preallocated', 'prefix', 'preserve_allcc', 'preserve_mostcc',
                'private', 'prologue', 'protected', 'ptrtoint', 'ptx_device',
                'ptx_kernel', 'readnone', 'readNone', 'readonly', 'readOnly',
                'reassoc', 'refs', 'relbf', 'release', 'resByArg', 'resume',
                'ret', 'returnDoesNotAlias', 'returned', 'returns_twice',
                'safestack', 'samesize', 'sanitize_address',
                'sanitize_hwaddress', 'sanitize_memory', 'sanitize_memtag',
                'sanitize_thread', 'sdiv', 'section', 'select', 'seq_cst',
                'sext', 'sge', 'sgt', 'shadowcallstack', 'shl',
                'shufflevector', 'sideeffect', 'signext', 'single',
                'singleImpl', 'singleImplName', 'sitofp', 'sizeM1',
                'sizeM1BitWidth', 'sle', 'slt', 'source_filename',
                'speculatable', 'speculative_load_hardening', 'spir_func',
                'spir_kernel', 'splat', 'srem', 'sret', 'ssp', 'sspreq',
                'sspstrong', 'store', 'strictfp', 'sub', 'summaries',
                'summary', 'swiftcc', 'swifterror', 'swiftself', 'switch',
                'syncscope', 'tail', 'tailcc', 'target', 'thread_local', 'to',
                'token', 'triple', 'true', 'trunc', 'type',
                'typeCheckedLoadConstVCalls', 'typeCheckedLoadVCalls',
                'typeid', 'typeidCompatibleVTable', 'typeIdInfo',
                'typeTestAssumeConstVCalls', 'typeTestAssumeVCalls',
                'typeTestRes', 'typeTests', 'udiv', 'ueq', 'uge', 'ugt',
                'uitofp', 'ule', 'ult', 'umax', 'umin', 'undef', 'une',
                'uniformRetVal', 'uniqueRetVal', 'unknown', 'unnamed_addr',
                'uno', 'unordered', 'unreachable', 'unsat', 'unwind', 'urem',
                'uselistorder', 'uselistorder_bb', 'uwtable', 'va_arg',
                'varFlags', 'variable', 'vcall_visibility', 'vFuncId',
                'virtFunc', 'virtualConstProp', 'void', 'volatile', 'vscale',
                'vTableFuncs', 'weak', 'weak_odr', 'webkit_jscc', 'win64cc',
                'within', 'wpdRes', 'wpdResolutions', 'writeonly', 'x',
                'x86_64_sysvcc', 'x86_fastcallcc', 'x86_intrcc', 'x86_mmx',
                'x86_regcallcc', 'x86_stdcallcc', 'x86_thiscallcc',
                'x86_vectorcallcc', 'xchg', 'xor', 'zeroext',
                'zeroinitializer', 'zext', 'immarg', 'willreturn'),
                suffix=r'\b'), Keyword),

            # Types
            (words(('void', 'half', 'bfloat', 'float', 'double', 'fp128',
                    'x86_fp80', 'ppc_fp128', 'label', 'metadata', 'x86_mmx',
                    'x86_amx', 'token', 'ptr')),
                   Keyword.Type),

            # Integer types
            (r'i[1-9]\d*', Keyword.Type)
        ]
    }


class LlvmMirBodyLexer(RegexLexer):
    """
    For LLVM MIR examples without the YAML wrapper.
    """
    name = 'LLVM-MIR Body'
    url = 'https://llvm.org/docs/MIRLangRef.html'
    aliases = ['llvm-mir-body']
    filenames = []
    mimetypes = []
    version_added = '2.6'

    tokens = {
        'root': [
            # Attributes on basic blocks
            (words(('liveins', 'successors'), suffix=':'), Keyword),
            # Basic Block Labels
            (r'bb\.[0-9]+(\.[a-zA-Z0-9_.-]+)?( \(address-taken\))?:', Name.Label),
            (r'bb\.[0-9]+ \(%[a-zA-Z0-9_.-]+\)( \(address-taken\))?:', Name.Label),
            (r'%bb\.[0-9]+(\.\w+)?', Name.Label),
            # Stack references
            (r'%stack\.[0-9]+(\.\w+\.addr)?', Name),
            # Subreg indices
            (r'%subreg\.\w+', Name),
            # Virtual registers
            (r'%[a-zA-Z0-9_]+ *', Name.Variable, 'vreg'),
            # Reference to LLVM-IR global
            include('global'),
            # Reference to Intrinsic
            (r'intrinsic\(\@[a-zA-Z0-9_.]+\)', Name.Variable.Global),
            # Comparison predicates
            (words(('eq', 'ne', 'sgt', 'sge', 'slt', 'sle', 'ugt', 'uge', 'ult',
                    'ule'), prefix=r'intpred\(', suffix=r'\)'), Name.Builtin),
            (words(('oeq', 'one', 'ogt', 'oge', 'olt', 'ole', 'ugt', 'uge',
                    'ult', 'ule'), prefix=r'floatpred\(', suffix=r'\)'),
             Name.Builtin),
            # Physical registers
            (r'\$\w+', String.Single),
            # Assignment operator
            (r'=', Operator),
            # gMIR Opcodes
            (r'(G_ANYEXT|G_[SZ]EXT|G_SEXT_INREG|G_TRUNC|G_IMPLICIT_DEF|G_PHI|'
             r'G_FRAME_INDEX|G_GLOBAL_VALUE|G_INTTOPTR|G_PTRTOINT|G_BITCAST|'
             r'G_CONSTANT|G_FCONSTANT|G_VASTART|G_VAARG|G_CTLZ|G_CTLZ_ZERO_UNDEF|'
             r'G_CTTZ|G_CTTZ_ZERO_UNDEF|G_CTPOP|G_BSWAP|G_BITREVERSE|'
             r'G_ADDRSPACE_CAST|G_BLOCK_ADDR|G_JUMP_TABLE|G_DYN_STACKALLOC|'
             r'G_ADD|G_SUB|G_MUL|G_[SU]DIV|G_[SU]REM|G_AND|G_OR|G_XOR|G_SHL|'
             r'G_[LA]SHR|G_[IF]CMP|G_SELECT|G_GEP|G_PTR_MASK|G_SMIN|G_SMAX|'
             r'G_UMIN|G_UMAX|G_[US]ADDO|G_[US]ADDE|G_[US]SUBO|G_[US]SUBE|'
             r'G_[US]MULO|G_[US]MULH|G_FNEG|G_FPEXT|G_FPTRUNC|G_FPTO[US]I|'
             r'G_[US]ITOFP|G_FABS|G_FCOPYSIGN|G_FCANONICALIZE|G_FMINNUM|'
             r'G_FMAXNUM|G_FMINNUM_IEEE|G_FMAXNUM_IEEE|G_FMINIMUM|G_FMAXIMUM|'
             r'G_FADD|G_FSUB|G_FMUL|G_FMA|G_FMAD|G_FDIV|G_FREM|G_FPOW|G_FEXP|'
             r'G_FEXP2|G_FLOG|G_FLOG2|G_FLOG10|G_FCEIL|G_FCOS|G_FSIN|G_FSQRT|'
             r'G_FFLOOR|G_FRINT|G_FNEARBYINT|G_INTRINSIC_TRUNC|'
             r'G_INTRINSIC_ROUND|G_LOAD|G_[ZS]EXTLOAD|G_INDEXED_LOAD|'
             r'G_INDEXED_[ZS]EXTLOAD|G_STORE|G_INDEXED_STORE|'
             r'G_ATOMIC_CMPXCHG_WITH_SUCCESS|G_ATOMIC_CMPXCHG|'
             r'G_ATOMICRMW_(XCHG|ADD|SUB|AND|NAND|OR|XOR|MAX|MIN|UMAX|UMIN|FADD|'
                           r'FSUB)'
             r'|G_FENCE|G_EXTRACT|G_UNMERGE_VALUES|G_INSERT|G_MERGE_VALUES|'
             r'G_BUILD_VECTOR|G_BUILD_VECTOR_TRUNC|G_CONCAT_VECTORS|'
             r'G_INTRINSIC|G_INTRINSIC_W_SIDE_EFFECTS|G_BR|G_BRCOND|'
             r'G_BRINDIRECT|G_BRJT|G_INSERT_VECTOR_ELT|G_EXTRACT_VECTOR_ELT|'
             r'G_SHUFFLE_VECTOR)\b',
             Name.Builtin),
            # Target independent opcodes
            (r'(COPY|PHI|INSERT_SUBREG|EXTRACT_SUBREG|REG_SEQUENCE)\b',
             Name.Builtin),
            # Flags
            (words(('killed', 'implicit')), Keyword),
            # ConstantInt values
            (r'(i[0-9]+)( +)', bygroups(Keyword.Type, Whitespace), 'constantint'),
            # ConstantFloat values
            (r'(half|float|double) +', Keyword.Type, 'constantfloat'),
            # Bare immediates
            include('integer'),
            # MMO's
            (r'(::)( *)', bygroups(Operator, Whitespace), 'mmo'),
            # MIR Comments
            (r';.*', Comment),
            # If we get here, assume it's a target instruction
            (r'[a-zA-Z0-9_]+', Name),
            # Everything else that isn't highlighted
            (r'[(), \n]+', Text),
        ],
        # The integer constant from a ConstantInt value
        'constantint': [
            include('integer'),
            (r'(?=.)', Text, '#pop'),
        ],
        # The floating point constant from a ConstantFloat value
        'constantfloat': [
            include('float'),
            (r'(?=.)', Text, '#pop'),
        ],
        'vreg': [
            # The bank or class if there is one
            (r'( *)(:(?!:))', bygroups(Whitespace, Keyword), ('#pop', 'vreg_bank_or_class')),
            # The LLT if there is one
            (r'( *)(\()', bygroups(Whitespace, Text), 'vreg_type'),
            (r'(?=.)', Text, '#pop'),
        ],
        'vreg_bank_or_class': [
            # The unassigned bank/class
            (r'( *)(_)', bygroups(Whitespace, Name.Variable.Magic)),
            (r'( *)([a-zA-Z0-9_]+)', bygroups(Whitespace, Name.Variable)),
            # The LLT if there is one
            (r'( *)(\()', bygroups(Whitespace, Text), 'vreg_type'),
            (r'(?=.)', Text, '#pop'),
        ],
        'vreg_type': [
            # Scalar and pointer types
            (r'( *)([sp][0-9]+)', bygroups(Whitespace, Keyword.Type)),
            (r'( *)(<[0-9]+ *x *[sp][0-9]+>)', bygroups(Whitespace, Keyword.Type)),
            (r'\)', Text, '#pop'),
            (r'(?=.)', Text, '#pop'),
        ],
        'mmo': [
            (r'\(', Text),
            (r' +', Whitespace),
            (words(('load', 'store', 'on', 'into', 'from', 'align', 'monotonic',
                    'acquire', 'release', 'acq_rel', 'seq_cst')),
             Keyword),
            # IR references
            (r'%ir\.[a-zA-Z0-9_.-]+', Name),
            (r'%ir-block\.[a-zA-Z0-9_.-]+', Name),
            (r'[-+]', Operator),
            include('integer'),
            include('global'),
            (r',', Punctuation),
            (r'\), \(', Text),
            (r'\)', Text, '#pop'),
        ],
        'integer': [(r'-?[0-9]+', Number.Integer),],
        'float': [(r'-?[0-9]+\.[0-9]+(e[+-][0-9]+)?', Number.Float)],
        'global': [(r'\@[a-zA-Z0-9_.]+', Name.Variable.Global)],
    }


class LlvmMirLexer(RegexLexer):
    """
    Lexer for the overall LLVM MIR document format.

    MIR is a human readable serialization format that's used to represent LLVM's
    machine specific intermediate representation. It allows LLVM's developers to
    see the state of the compilation process at various points, as well as test
    individual pieces of the compiler.
    """
    name = 'LLVM-MIR'
    url = 'https://llvm.org/docs/MIRLangRef.html'
    aliases = ['llvm-mir']
    filenames = ['*.mir']
    version_added = '2.6'

    tokens = {
        'root': [
            # Comments are hashes at the YAML level
            (r'#.*', Comment),
            # Documents starting with | are LLVM-IR
            (r'--- \|$', Keyword, 'llvm_ir'),
            # Other documents are MIR
            (r'---', Keyword, 'llvm_mir'),
            # Consume everything else in one token for efficiency
            (r'[^-#]+|.', Text),
        ],
        'llvm_ir': [
            # Documents end with '...' or '---'
            (r'(\.\.\.|(?=---))', Keyword, '#pop'),
            # Delegate to the LlvmLexer
            (r'((?:.|\n)+?)(?=(\.\.\.|---))', bygroups(using(LlvmLexer))),
        ],
        'llvm_mir': [
            # Comments are hashes at the YAML level
            (r'#.*', Comment),
            # Documents end with '...' or '---'
            (r'(\.\.\.|(?=---))', Keyword, '#pop'),
            # Handle the simple attributes
            (r'name:', Keyword, 'name'),
            (words(('alignment', ),
                   suffix=':'), Keyword, 'number'),
            (words(('legalized', 'regBankSelected', 'tracksRegLiveness',
                    'selected', 'exposesReturnsTwice'),
                   suffix=':'), Keyword, 'boolean'),
            # Handle the attributes don't highlight inside
            (words(('registers', 'stack', 'fixedStack', 'liveins', 'frameInfo',
                    'machineFunctionInfo'),
                   suffix=':'), Keyword),
            # Delegate the body block to the LlvmMirBodyLexer
            (r'body: *\|', Keyword, 'llvm_mir_body'),
            # Consume everything else
            (r'.+', Text),
            (r'\n', Whitespace),
        ],
        'name': [
            (r'[^\n]+', Name),
            default('#pop'),
        ],
        'boolean': [
            (r' *(true|false)', Name.Builtin),
            default('#pop'),
        ],
        'number': [
            (r' *[0-9]+', Number),
            default('#pop'),
        ],
        'llvm_mir_body': [
            # Documents end with '...' or '---'.
            # We have to pop llvm_mir_body and llvm_mir
            (r'(\.\.\.|(?=---))', Keyword, '#pop:2'),
            # Delegate the body block to the LlvmMirBodyLexer
            (r'((?:.|\n)+?)(?=\.\.\.|---)', bygroups(using(LlvmMirBodyLexer))),
            # The '...' is optional. If we didn't already find it then it isn't
            # there. There might be a '---' instead though.
            (r'(?!\.\.\.|---)((?:.|\n)+)', bygroups(using(LlvmMirBodyLexer))),
        ],
    }


class NasmLexer(RegexLexer):
    """
    For Nasm (Intel) assembly code.
    """
    name = 'NASM'
    aliases = ['nasm']
    filenames = ['*.asm', '*.ASM', '*.nasm']
    mimetypes = ['text/x-nasm']
    url = 'https://nasm.us'
    version_added = ''

    # Tasm uses the same file endings, but TASM is not as common as NASM, so
    # we prioritize NASM higher by default
    priority = 1.0

    identifier = r'[a-z$._?][\w$.?#@~]*'
    hexn = r'(?:0x[0-9a-f]+|$0[0-9a-f]*|[0-9]+[0-9a-f]*h)'
    octn = r'[0-7]+q'
    binn = r'[01]+b'
    decn = r'[0-9]+'
    floatn = decn + r'\.e?' + decn
    string = r'"(\\"|[^"\n])*"|' + r"'(\\'|[^'\n])*'|" + r"`(\\`|[^`\n])*`"
    declkw = r'(?:res|d)[bwdqt]|times'
    register = (r'(r[0-9][0-5]?[bwd]?|'
                r'[a-d][lh]|[er]?[a-d]x|[er]?[sb]p|[er]?[sd]i|[c-gs]s|st[0-7]|'
                r'mm[0-7]|cr[0-4]|dr[0-367]|tr[3-7]|k[0-7]|'
                r'[xyz]mm(?:[12][0-9]?|3[01]?|[04-9]))\b')
    wordop = r'seg|wrt|strict|rel|abs'
    type = r'byte|[dq]?word'
    # Directives must be followed by whitespace, otherwise CPU will match
    # cpuid for instance.
    directives = (r'(?:BITS|USE16|USE32|SECTION|SEGMENT|ABSOLUTE|EXTERN|GLOBAL|'
                  r'ORG|ALIGN|STRUC|ENDSTRUC|COMMON|CPU|GROUP|UPPERCASE|IMPORT|'
                  r'EXPORT|LIBRARY|MODULE)(?=\s)')

    flags = re.IGNORECASE | re.MULTILINE
    tokens = {
        'root': [
            (r'^\s*%', Comment.Preproc, 'preproc'),
            include('whitespace'),
            (identifier + ':', Name.Label),
            (rf'({identifier})(\s+)(equ)',
                bygroups(Name.Constant, Whitespace, Keyword.Declaration),
                'instruction-args'),
            (directives, Keyword, 'instruction-args'),
            (declkw, Keyword.Declaration, 'instruction-args'),
            (identifier, Name.Function, 'instruction-args'),
            (r'[\r\n]+', Whitespace)
        ],
        'instruction-args': [
            (string, String),
            (hexn, Number.Hex),
            (octn, Number.Oct),
            (binn, Number.Bin),
            (floatn, Number.Float),
            (decn, Number.Integer),
            include('punctuation'),
            (register, Name.Builtin),
            (identifier, Name.Variable),
            (r'[\r\n]+', Whitespace, '#pop'),
            include('whitespace')
        ],
        'preproc': [
            (r'[^;\n]+', Comment.Preproc),
            (r';.*?\n', Comment.Single, '#pop'),
            (r'\n', Comment.Preproc, '#pop'),
        ],
        'whitespace': [
            (r'\n', Whitespace),
            (r'[ \t]+', Whitespace),
            (r';.*', Comment.Single),
            (r'#.*', Comment.Single)
        ],
        'punctuation': [
            (r'[,{}():\[\]]+', Punctuation),
            (r'[&|^<>+*/%~-]+', Operator),
            (r'[$]+', Keyword.Constant),
            (wordop, Operator.Word),
            (type, Keyword.Type)
        ],
    }

    def analyse_text(text):
        # Probably TASM
        if re.match(r'PROC', text, re.IGNORECASE):
            return False


class NasmObjdumpLexer(ObjdumpLexer):
    """
    For the output of ``objdump -d -M intel``.
    """
    name = 'objdump-nasm'
    aliases = ['objdump-nasm']
    filenames = ['*.objdump-intel']
    mimetypes = ['text/x-nasm-objdump']
    url = 'https://www.gnu.org/software/binutils'
    version_added = '2.0'

    tokens = _objdump_lexer_tokens(NasmLexer)


class TasmLexer(RegexLexer):
    """
    For Tasm (Turbo Assembler) assembly code.
    """
    name = 'TASM'
    aliases = ['tasm']
    filenames = ['*.asm', '*.ASM', '*.tasm']
    mimetypes = ['text/x-tasm']
    url = 'https://en.wikipedia.org/wiki/Turbo_Assembler'
    version_added = ''

    identifier = r'[@a-z$._?][\w$.?#@~]*'
    hexn = r'(?:0x[0-9a-f]+|$0[0-9a-f]*|[0-9]+[0-9a-f]*h)'
    octn = r'[0-7]+q'
    binn = r'[01]+b'
    decn = r'[0-9]+'
    floatn = decn + r'\.e?' + decn
    string = r'"(\\"|[^"\n])*"|' + r"'(\\'|[^'\n])*'|" + r"`(\\`|[^`\n])*`"
    declkw = r'(?:res|d)[bwdqt]|times'
    register = (r'(r[0-9][0-5]?[bwd]|'
                r'[a-d][lh]|[er]?[a-d]x|[er]?[sb]p|[er]?[sd]i|[c-gs]s|st[0-7]|'
                r'mm[0-7]|cr[0-4]|dr[0-367]|tr[3-7])\b')
    wordop = r'seg|wrt|strict'
    type = r'byte|[dq]?word'
    directives = (r'BITS|USE16|USE32|SECTION|SEGMENT|ABSOLUTE|EXTERN|GLOBAL|'
                  r'ORG|ALIGN|STRUC|ENDSTRUC|ENDS|COMMON|CPU|GROUP|UPPERCASE|INCLUDE|'
                  r'EXPORT|LIBRARY|MODULE|PROC|ENDP|USES|ARG|DATASEG|UDATASEG|END|IDEAL|'
                  r'P386|MODEL|ASSUME|CODESEG|SIZE')
    # T[A-Z][a-z] is more of a convention. Lexer should filter out STRUC definitions
    # and then 'add' them to datatype somehow.
    datatype = (r'db|dd|dw|T[A-Z][a-z]+')

    flags = re.IGNORECASE | re.MULTILINE
    tokens = {
        'root': [
            (r'^\s*%', Comment.Preproc, 'preproc'),
            include('whitespace'),
            (identifier + ':', Name.Label),
            (directives, Keyword, 'instruction-args'),
            (rf'({identifier})(\s+)({datatype})',
                bygroups(Name.Constant, Whitespace, Keyword.Declaration),
                'instruction-args'),
            (declkw, Keyword.Declaration, 'instruction-args'),
            (identifier, Name.Function, 'instruction-args'),
            (r'[\r\n]+', Whitespace)
        ],
        'instruction-args': [
            (string, String),
            (hexn, Number.Hex),
            (octn, Number.Oct),
            (binn, Number.Bin),
            (floatn, Number.Float),
            (decn, Number.Integer),
            include('punctuation'),
            (register, Name.Builtin),
            (identifier, Name.Variable),
            # Do not match newline when it's preceded by a backslash
            (r'(\\)(\s*)(;.*)([\r\n])',
             bygroups(Text, Whitespace, Comment.Single, Whitespace)),
            (r'[\r\n]+', Whitespace, '#pop'),
            include('whitespace')
        ],
        'preproc': [
            (r'[^;\n]+', Comment.Preproc),
            (r';.*?\n', Comment.Single, '#pop'),
            (r'\n', Comment.Preproc, '#pop'),
        ],
        'whitespace': [
            (r'[\n\r]', Whitespace),
            (r'(\\)([\n\r])', bygroups(Text, Whitespace)),
            (r'[ \t]+', Whitespace),
            (r';.*', Comment.Single)
        ],
        'punctuation': [
            (r'[,():\[\]]+', Punctuation),
            (r'[&|^<>+*=/%~-]+', Operator),
            (r'[$]+', Keyword.Constant),
            (wordop, Operator.Word),
            (type, Keyword.Type)
        ],
    }

    def analyse_text(text):
        # See above
        if re.match(r'PROC', text, re.I):
            return True


class Ca65Lexer(RegexLexer):
    """
    For ca65 assembler sources.
    """
    name = 'ca65 assembler'
    aliases = ['ca65']
    filenames = ['*.s']
    url = 'https://cc65.github.io'
    version_added = '1.6'

    flags = re.IGNORECASE

    tokens = {
        'root': [
            (r';.*', Comment.Single),
            (r'\s+', Whitespace),
            (r'[a-z_.@$][\w.@$]*:', Name.Label),
            (r'((ld|st)[axy]|(in|de)[cxy]|asl|lsr|ro[lr]|adc|sbc|cmp|cp[xy]'
             r'|cl[cvdi]|se[cdi]|jmp|jsr|bne|beq|bpl|bmi|bvc|bvs|bcc|bcs'
             r'|p[lh][ap]|rt[is]|brk|nop|ta[xy]|t[xy]a|txs|tsx|and|ora|eor'
             r'|bit)\b', Keyword),
            (r'\.\w+', Keyword.Pseudo),
            (r'[-+~*/^&|!<>=]', Operator),
            (r'"[^"\n]*.', String),
            (r"'[^'\n]*.", String.Char),
            (r'\$[0-9a-f]+|[0-9a-f]+h\b', Number.Hex),
            (r'\d+', Number.Integer),
            (r'%[01]+', Number.Bin),
            (r'[#,.:()=\[\]]', Punctuation),
            (r'[a-z_.@$][\w.@$]*', Name),
        ]
    }

    def analyse_text(self, text):
        # comments in GAS start with "#"
        if re.search(r'^\s*;', text, re.MULTILINE):
            return 0.9


class Dasm16Lexer(RegexLexer):
    """
    For DCPU-16 Assembly.
    """
    name = 'DASM16'
    url = 'http://0x10c.com/doc/dcpu-16.txt'
    aliases = ['dasm16']
    filenames = ['*.dasm16', '*.dasm']
    mimetypes = ['text/x-dasm16']
    version_added = '2.4'

    INSTRUCTIONS = [
        'SET',
        'ADD', 'SUB',
        'MUL', 'MLI',
        'DIV', 'DVI',
        'MOD', 'MDI',
        'AND', 'BOR', 'XOR',
        'SHR', 'ASR', 'SHL',
        'IFB', 'IFC', 'IFE', 'IFN', 'IFG', 'IFA', 'IFL', 'IFU',
        'ADX', 'SBX',
        'STI', 'STD',
        'JSR',
        'INT', 'IAG', 'IAS', 'RFI', 'IAQ', 'HWN', 'HWQ', 'HWI',
    ]

    REGISTERS = [
        'A', 'B', 'C',
        'X', 'Y', 'Z',
        'I', 'J',
        'SP', 'PC', 'EX',
        'POP', 'PEEK', 'PUSH'
    ]

    # Regexes yo
    char = r'[a-zA-Z0-9_$@.]'
    identifier = r'(?:[a-zA-Z$_]' + char + r'*|\.' + char + '+)'
    number = r'[+-]?(?:0[xX][a-zA-Z0-9]+|\d+)'
    binary_number = r'0b[01_]+'
    instruction = r'(?i)(' + '|'.join(INSTRUCTIONS) + ')'
    single_char = r"'\\?" + char + "'"
    string = r'"(\\"|[^"])*"'

    def guess_identifier(lexer, match):
        ident = match.group(0)
        klass = Name.Variable if ident.upper() in lexer.REGISTERS else Name.Label
        yield match.start(), klass, ident

    tokens = {
        'root': [
            include('whitespace'),
            (':' + identifier, Name.Label),
            (identifier + ':', Name.Label),
            (instruction, Name.Function, 'instruction-args'),
            (r'\.' + identifier, Name.Function, 'data-args'),
            (r'[\r\n]+', Whitespace)
        ],

        'numeric' : [
            (binary_number, Number.Integer),
            (number, Number.Integer),
            (single_char, String),
        ],

        'arg' : [
            (identifier, guess_identifier),
            include('numeric')
        ],

        'deref' : [
            (r'\+', Punctuation),
            (r'\]', Punctuation, '#pop'),
            include('arg'),
            include('whitespace')
        ],

        'instruction-line' : [
            (r'[\r\n]+', Whitespace, '#pop'),
            (r';.*?$', Comment, '#pop'),
            include('whitespace')
        ],

        'instruction-args': [
            (r',', Punctuation),
            (r'\[', Punctuation, 'deref'),
            include('arg'),
            include('instruction-line')
        ],

        'data-args' : [
            (r',', Punctuation),
            include('numeric'),
            (string, String),
            include('instruction-line')
        ],

        'whitespace': [
            (r'\n', Whitespace),
            (r'\s+', Whitespace),
            (r';.*?\n', Comment)
        ],
    }

# === NexusCore/openenv\Lib\site-packages\jinja2\parser.py ===
"""Parse tokens from the lexer into nodes for the compiler."""

import typing
import typing as t

from . import nodes
from .exceptions import TemplateAssertionError
from .exceptions import TemplateSyntaxError
from .lexer import describe_token
from .lexer import describe_token_expr

if t.TYPE_CHECKING:
    import typing_extensions as te

    from .environment import Environment

_ImportInclude = t.TypeVar("_ImportInclude", nodes.Import, nodes.Include)
_MacroCall = t.TypeVar("_MacroCall", nodes.Macro, nodes.CallBlock)

_statement_keywords = frozenset(
    [
        "for",
        "if",
        "block",
        "extends",
        "print",
        "macro",
        "include",
        "from",
        "import",
        "set",
        "with",
        "autoescape",
    ]
)
_compare_operators = frozenset(["eq", "ne", "lt", "lteq", "gt", "gteq"])

_math_nodes: t.Dict[str, t.Type[nodes.Expr]] = {
    "add": nodes.Add,
    "sub": nodes.Sub,
    "mul": nodes.Mul,
    "div": nodes.Div,
    "floordiv": nodes.FloorDiv,
    "mod": nodes.Mod,
}


class Parser:
    """This is the central parsing class Jinja uses.  It's passed to
    extensions and can be used to parse expressions or statements.
    """

    def __init__(
        self,
        environment: "Environment",
        source: str,
        name: t.Optional[str] = None,
        filename: t.Optional[str] = None,
        state: t.Optional[str] = None,
    ) -> None:
        self.environment = environment
        self.stream = environment._tokenize(source, name, filename, state)
        self.name = name
        self.filename = filename
        self.closed = False
        self.extensions: t.Dict[
            str, t.Callable[[Parser], t.Union[nodes.Node, t.List[nodes.Node]]]
        ] = {}
        for extension in environment.iter_extensions():
            for tag in extension.tags:
                self.extensions[tag] = extension.parse
        self._last_identifier = 0
        self._tag_stack: t.List[str] = []
        self._end_token_stack: t.List[t.Tuple[str, ...]] = []

    def fail(
        self,
        msg: str,
        lineno: t.Optional[int] = None,
        exc: t.Type[TemplateSyntaxError] = TemplateSyntaxError,
    ) -> "te.NoReturn":
        """Convenience method that raises `exc` with the message, passed
        line number or last line number as well as the current name and
        filename.
        """
        if lineno is None:
            lineno = self.stream.current.lineno
        raise exc(msg, lineno, self.name, self.filename)

    def _fail_ut_eof(
        self,
        name: t.Optional[str],
        end_token_stack: t.List[t.Tuple[str, ...]],
        lineno: t.Optional[int],
    ) -> "te.NoReturn":
        expected: t.Set[str] = set()
        for exprs in end_token_stack:
            expected.update(map(describe_token_expr, exprs))
        if end_token_stack:
            currently_looking: t.Optional[str] = " or ".join(
                map(repr, map(describe_token_expr, end_token_stack[-1]))
            )
        else:
            currently_looking = None

        if name is None:
            message = ["Unexpected end of template."]
        else:
            message = [f"Encountered unknown tag {name!r}."]

        if currently_looking:
            if name is not None and name in expected:
                message.append(
                    "You probably made a nesting mistake. Jinja is expecting this tag,"
                    f" but currently looking for {currently_looking}."
                )
            else:
                message.append(
                    f"Jinja was looking for the following tags: {currently_looking}."
                )

        if self._tag_stack:
            message.append(
                "The innermost block that needs to be closed is"
                f" {self._tag_stack[-1]!r}."
            )

        self.fail(" ".join(message), lineno)

    def fail_unknown_tag(
        self, name: str, lineno: t.Optional[int] = None
    ) -> "te.NoReturn":
        """Called if the parser encounters an unknown tag.  Tries to fail
        with a human readable error message that could help to identify
        the problem.
        """
        self._fail_ut_eof(name, self._end_token_stack, lineno)

    def fail_eof(
        self,
        end_tokens: t.Optional[t.Tuple[str, ...]] = None,
        lineno: t.Optional[int] = None,
    ) -> "te.NoReturn":
        """Like fail_unknown_tag but for end of template situations."""
        stack = list(self._end_token_stack)
        if end_tokens is not None:
            stack.append(end_tokens)
        self._fail_ut_eof(None, stack, lineno)

    def is_tuple_end(
        self, extra_end_rules: t.Optional[t.Tuple[str, ...]] = None
    ) -> bool:
        """Are we at the end of a tuple?"""
        if self.stream.current.type in ("variable_end", "block_end", "rparen"):
            return True
        elif extra_end_rules is not None:
            return self.stream.current.test_any(extra_end_rules)  # type: ignore
        return False

    def free_identifier(self, lineno: t.Optional[int] = None) -> nodes.InternalName:
        """Return a new free identifier as :class:`~jinja2.nodes.InternalName`."""
        self._last_identifier += 1
        rv = object.__new__(nodes.InternalName)
        nodes.Node.__init__(rv, f"fi{self._last_identifier}", lineno=lineno)
        return rv

    def parse_statement(self) -> t.Union[nodes.Node, t.List[nodes.Node]]:
        """Parse a single statement."""
        token = self.stream.current
        if token.type != "name":
            self.fail("tag name expected", token.lineno)
        self._tag_stack.append(token.value)
        pop_tag = True
        try:
            if token.value in _statement_keywords:
                f = getattr(self, f"parse_{self.stream.current.value}")
                return f()  # type: ignore
            if token.value == "call":
                return self.parse_call_block()
            if token.value == "filter":
                return self.parse_filter_block()
            ext = self.extensions.get(token.value)
            if ext is not None:
                return ext(self)

            # did not work out, remove the token we pushed by accident
            # from the stack so that the unknown tag fail function can
            # produce a proper error message.
            self._tag_stack.pop()
            pop_tag = False
            self.fail_unknown_tag(token.value, token.lineno)
        finally:
            if pop_tag:
                self._tag_stack.pop()

    def parse_statements(
        self, end_tokens: t.Tuple[str, ...], drop_needle: bool = False
    ) -> t.List[nodes.Node]:
        """Parse multiple statements into a list until one of the end tokens
        is reached.  This is used to parse the body of statements as it also
        parses template data if appropriate.  The parser checks first if the
        current token is a colon and skips it if there is one.  Then it checks
        for the block end and parses until if one of the `end_tokens` is
        reached.  Per default the active token in the stream at the end of
        the call is the matched end token.  If this is not wanted `drop_needle`
        can be set to `True` and the end token is removed.
        """
        # the first token may be a colon for python compatibility
        self.stream.skip_if("colon")

        # in the future it would be possible to add whole code sections
        # by adding some sort of end of statement token and parsing those here.
        self.stream.expect("block_end")
        result = self.subparse(end_tokens)

        # we reached the end of the template too early, the subparser
        # does not check for this, so we do that now
        if self.stream.current.type == "eof":
            self.fail_eof(end_tokens)

        if drop_needle:
            next(self.stream)
        return result

    def parse_set(self) -> t.Union[nodes.Assign, nodes.AssignBlock]:
        """Parse an assign statement."""
        lineno = next(self.stream).lineno
        target = self.parse_assign_target(with_namespace=True)
        if self.stream.skip_if("assign"):
            expr = self.parse_tuple()
            return nodes.Assign(target, expr, lineno=lineno)
        filter_node = self.parse_filter(None)
        body = self.parse_statements(("name:endset",), drop_needle=True)
        return nodes.AssignBlock(target, filter_node, body, lineno=lineno)

    def parse_for(self) -> nodes.For:
        """Parse a for loop."""
        lineno = self.stream.expect("name:for").lineno
        target = self.parse_assign_target(extra_end_rules=("name:in",))
        self.stream.expect("name:in")
        iter = self.parse_tuple(
            with_condexpr=False, extra_end_rules=("name:recursive",)
        )
        test = None
        if self.stream.skip_if("name:if"):
            test = self.parse_expression()
        recursive = self.stream.skip_if("name:recursive")
        body = self.parse_statements(("name:endfor", "name:else"))
        if next(self.stream).value == "endfor":
            else_ = []
        else:
            else_ = self.parse_statements(("name:endfor",), drop_needle=True)
        return nodes.For(target, iter, body, else_, test, recursive, lineno=lineno)

    def parse_if(self) -> nodes.If:
        """Parse an if construct."""
        node = result = nodes.If(lineno=self.stream.expect("name:if").lineno)
        while True:
            node.test = self.parse_tuple(with_condexpr=False)
            node.body = self.parse_statements(("name:elif", "name:else", "name:endif"))
            node.elif_ = []
            node.else_ = []
            token = next(self.stream)
            if token.test("name:elif"):
                node = nodes.If(lineno=self.stream.current.lineno)
                result.elif_.append(node)
                continue
            elif token.test("name:else"):
                result.else_ = self.parse_statements(("name:endif",), drop_needle=True)
            break
        return result

    def parse_with(self) -> nodes.With:
        node = nodes.With(lineno=next(self.stream).lineno)
        targets: t.List[nodes.Expr] = []
        values: t.List[nodes.Expr] = []
        while self.stream.current.type != "block_end":
            if targets:
                self.stream.expect("comma")
            target = self.parse_assign_target()
            target.set_ctx("param")
            targets.append(target)
            self.stream.expect("assign")
            values.append(self.parse_expression())
        node.targets = targets
        node.values = values
        node.body = self.parse_statements(("name:endwith",), drop_needle=True)
        return node

    def parse_autoescape(self) -> nodes.Scope:
        node = nodes.ScopedEvalContextModifier(lineno=next(self.stream).lineno)
        node.options = [nodes.Keyword("autoescape", self.parse_expression())]
        node.body = self.parse_statements(("name:endautoescape",), drop_needle=True)
        return nodes.Scope([node])

    def parse_block(self) -> nodes.Block:
        node = nodes.Block(lineno=next(self.stream).lineno)
        node.name = self.stream.expect("name").value
        node.scoped = self.stream.skip_if("name:scoped")
        node.required = self.stream.skip_if("name:required")

        # common problem people encounter when switching from django
        # to jinja.  we do not support hyphens in block names, so let's
        # raise a nicer error message in that case.
        if self.stream.current.type == "sub":
            self.fail(
                "Block names in Jinja have to be valid Python identifiers and may not"
                " contain hyphens, use an underscore instead."
            )

        node.body = self.parse_statements(("name:endblock",), drop_needle=True)

        # enforce that required blocks only contain whitespace or comments
        # by asserting that the body, if not empty, is just TemplateData nodes
        # with whitespace data
        if node.required:
            for body_node in node.body:
                if not isinstance(body_node, nodes.Output) or any(
                    not isinstance(output_node, nodes.TemplateData)
                    or not output_node.data.isspace()
                    for output_node in body_node.nodes
                ):
                    self.fail("Required blocks can only contain comments or whitespace")

        self.stream.skip_if("name:" + node.name)
        return node

    def parse_extends(self) -> nodes.Extends:
        node = nodes.Extends(lineno=next(self.stream).lineno)
        node.template = self.parse_expression()
        return node

    def parse_import_context(
        self, node: _ImportInclude, default: bool
    ) -> _ImportInclude:
        if self.stream.current.test_any(
            "name:with", "name:without"
        ) and self.stream.look().test("name:context"):
            node.with_context = next(self.stream).value == "with"
            self.stream.skip()
        else:
            node.with_context = default
        return node

    def parse_include(self) -> nodes.Include:
        node = nodes.Include(lineno=next(self.stream).lineno)
        node.template = self.parse_expression()
        if self.stream.current.test("name:ignore") and self.stream.look().test(
            "name:missing"
        ):
            node.ignore_missing = True
            self.stream.skip(2)
        else:
            node.ignore_missing = False
        return self.parse_import_context(node, True)

    def parse_import(self) -> nodes.Import:
        node = nodes.Import(lineno=next(self.stream).lineno)
        node.template = self.parse_expression()
        self.stream.expect("name:as")
        node.target = self.parse_assign_target(name_only=True).name
        return self.parse_import_context(node, False)

    def parse_from(self) -> nodes.FromImport:
        node = nodes.FromImport(lineno=next(self.stream).lineno)
        node.template = self.parse_expression()
        self.stream.expect("name:import")
        node.names = []

        def parse_context() -> bool:
            if self.stream.current.value in {
                "with",
                "without",
            } and self.stream.look().test("name:context"):
                node.with_context = next(self.stream).value == "with"
                self.stream.skip()
                return True
            return False

        while True:
            if node.names:
                self.stream.expect("comma")
            if self.stream.current.type == "name":
                if parse_context():
                    break
                target = self.parse_assign_target(name_only=True)
                if target.name.startswith("_"):
                    self.fail(
                        "names starting with an underline can not be imported",
                        target.lineno,
                        exc=TemplateAssertionError,
                    )
                if self.stream.skip_if("name:as"):
                    alias = self.parse_assign_target(name_only=True)
                    node.names.append((target.name, alias.name))
                else:
                    node.names.append(target.name)
                if parse_context() or self.stream.current.type != "comma":
                    break
            else:
                self.stream.expect("name")
        if not hasattr(node, "with_context"):
            node.with_context = False
        return node

    def parse_signature(self, node: _MacroCall) -> None:
        args = node.args = []
        defaults = node.defaults = []
        self.stream.expect("lparen")
        while self.stream.current.type != "rparen":
            if args:
                self.stream.expect("comma")
            arg = self.parse_assign_target(name_only=True)
            arg.set_ctx("param")
            if self.stream.skip_if("assign"):
                defaults.append(self.parse_expression())
            elif defaults:
                self.fail("non-default argument follows default argument")
            args.append(arg)
        self.stream.expect("rparen")

    def parse_call_block(self) -> nodes.CallBlock:
        node = nodes.CallBlock(lineno=next(self.stream).lineno)
        if self.stream.current.type == "lparen":
            self.parse_signature(node)
        else:
            node.args = []
            node.defaults = []

        call_node = self.parse_expression()
        if not isinstance(call_node, nodes.Call):
            self.fail("expected call", node.lineno)
        node.call = call_node
        node.body = self.parse_statements(("name:endcall",), drop_needle=True)
        return node

    def parse_filter_block(self) -> nodes.FilterBlock:
        node = nodes.FilterBlock(lineno=next(self.stream).lineno)
        node.filter = self.parse_filter(None, start_inline=True)  # type: ignore
        node.body = self.parse_statements(("name:endfilter",), drop_needle=True)
        return node

    def parse_macro(self) -> nodes.Macro:
        node = nodes.Macro(lineno=next(self.stream).lineno)
        node.name = self.parse_assign_target(name_only=True).name
        self.parse_signature(node)
        node.body = self.parse_statements(("name:endmacro",), drop_needle=True)
        return node

    def parse_print(self) -> nodes.Output:
        node = nodes.Output(lineno=next(self.stream).lineno)
        node.nodes = []
        while self.stream.current.type != "block_end":
            if node.nodes:
                self.stream.expect("comma")
            node.nodes.append(self.parse_expression())
        return node

    @typing.overload
    def parse_assign_target(
        self, with_tuple: bool = ..., name_only: "te.Literal[True]" = ...
    ) -> nodes.Name: ...

    @typing.overload
    def parse_assign_target(
        self,
        with_tuple: bool = True,
        name_only: bool = False,
        extra_end_rules: t.Optional[t.Tuple[str, ...]] = None,
        with_namespace: bool = False,
    ) -> t.Union[nodes.NSRef, nodes.Name, nodes.Tuple]: ...

    def parse_assign_target(
        self,
        with_tuple: bool = True,
        name_only: bool = False,
        extra_end_rules: t.Optional[t.Tuple[str, ...]] = None,
        with_namespace: bool = False,
    ) -> t.Union[nodes.NSRef, nodes.Name, nodes.Tuple]:
        """Parse an assignment target.  As Jinja allows assignments to
        tuples, this function can parse all allowed assignment targets.  Per
        default assignments to tuples are parsed, that can be disable however
        by setting `with_tuple` to `False`.  If only assignments to names are
        wanted `name_only` can be set to `True`.  The `extra_end_rules`
        parameter is forwarded to the tuple parsing function.  If
        `with_namespace` is enabled, a namespace assignment may be parsed.
        """
        target: nodes.Expr

        if name_only:
            token = self.stream.expect("name")
            target = nodes.Name(token.value, "store", lineno=token.lineno)
        else:
            if with_tuple:
                target = self.parse_tuple(
                    simplified=True,
                    extra_end_rules=extra_end_rules,
                    with_namespace=with_namespace,
                )
            else:
                target = self.parse_primary(with_namespace=with_namespace)

            target.set_ctx("store")

        if not target.can_assign():
            self.fail(
                f"can't assign to {type(target).__name__.lower()!r}", target.lineno
            )

        return target  # type: ignore

    def parse_expression(self, with_condexpr: bool = True) -> nodes.Expr:
        """Parse an expression.  Per default all expressions are parsed, if
        the optional `with_condexpr` parameter is set to `False` conditional
        expressions are not parsed.
        """
        if with_condexpr:
            return self.parse_condexpr()
        return self.parse_or()

    def parse_condexpr(self) -> nodes.Expr:
        lineno = self.stream.current.lineno
        expr1 = self.parse_or()
        expr3: t.Optional[nodes.Expr]

        while self.stream.skip_if("name:if"):
            expr2 = self.parse_or()
            if self.stream.skip_if("name:else"):
                expr3 = self.parse_condexpr()
            else:
                expr3 = None
            expr1 = nodes.CondExpr(expr2, expr1, expr3, lineno=lineno)
            lineno = self.stream.current.lineno
        return expr1

    def parse_or(self) -> nodes.Expr:
        lineno = self.stream.current.lineno
        left = self.parse_and()
        while self.stream.skip_if("name:or"):
            right = self.parse_and()
            left = nodes.Or(left, right, lineno=lineno)
            lineno = self.stream.current.lineno
        return left

    def parse_and(self) -> nodes.Expr:
        lineno = self.stream.current.lineno
        left = self.parse_not()
        while self.stream.skip_if("name:and"):
            right = self.parse_not()
            left = nodes.And(left, right, lineno=lineno)
            lineno = self.stream.current.lineno
        return left

    def parse_not(self) -> nodes.Expr:
        if self.stream.current.test("name:not"):
            lineno = next(self.stream).lineno
            return nodes.Not(self.parse_not(), lineno=lineno)
        return self.parse_compare()

    def parse_compare(self) -> nodes.Expr:
        lineno = self.stream.current.lineno
        expr = self.parse_math1()
        ops = []
        while True:
            token_type = self.stream.current.type
            if token_type in _compare_operators:
                next(self.stream)
                ops.append(nodes.Operand(token_type, self.parse_math1()))
            elif self.stream.skip_if("name:in"):
                ops.append(nodes.Operand("in", self.parse_math1()))
            elif self.stream.current.test("name:not") and self.stream.look().test(
                "name:in"
            ):
                self.stream.skip(2)
                ops.append(nodes.Operand("notin", self.parse_math1()))
            else:
                break
            lineno = self.stream.current.lineno
        if not ops:
            return expr
        return nodes.Compare(expr, ops, lineno=lineno)

    def parse_math1(self) -> nodes.Expr:
        lineno = self.stream.current.lineno
        left = self.parse_concat()
        while self.stream.current.type in ("add", "sub"):
            cls = _math_nodes[self.stream.current.type]
            next(self.stream)
            right = self.parse_concat()
            left = cls(left, right, lineno=lineno)
            lineno = self.stream.current.lineno
        return left

    def parse_concat(self) -> nodes.Expr:
        lineno = self.stream.current.lineno
        args = [self.parse_math2()]
        while self.stream.current.type == "tilde":
            next(self.stream)
            args.append(self.parse_math2())
        if len(args) == 1:
            return args[0]
        return nodes.Concat(args, lineno=lineno)

    def parse_math2(self) -> nodes.Expr:
        lineno = self.stream.current.lineno
        left = self.parse_pow()
        while self.stream.current.type in ("mul", "div", "floordiv", "mod"):
            cls = _math_nodes[self.stream.current.type]
            next(self.stream)
            right = self.parse_pow()
            left = cls(left, right, lineno=lineno)
            lineno = self.stream.current.lineno
        return left

    def parse_pow(self) -> nodes.Expr:
        lineno = self.stream.current.lineno
        left = self.parse_unary()
        while self.stream.current.type == "pow":
            next(self.stream)
            right = self.parse_unary()
            left = nodes.Pow(left, right, lineno=lineno)
            lineno = self.stream.current.lineno
        return left

    def parse_unary(self, with_filter: bool = True) -> nodes.Expr:
        token_type = self.stream.current.type
        lineno = self.stream.current.lineno
        node: nodes.Expr

        if token_type == "sub":
            next(self.stream)
            node = nodes.Neg(self.parse_unary(False), lineno=lineno)
        elif token_type == "add":
            next(self.stream)
            node = nodes.Pos(self.parse_unary(False), lineno=lineno)
        else:
            node = self.parse_primary()
        node = self.parse_postfix(node)
        if with_filter:
            node = self.parse_filter_expr(node)
        return node

    def parse_primary(self, with_namespace: bool = False) -> nodes.Expr:
        """Parse a name or literal value. If ``with_namespace`` is enabled, also
        parse namespace attr refs, for use in assignments."""
        token = self.stream.current
        node: nodes.Expr
        if token.type == "name":
            next(self.stream)
            if token.value in ("true", "false", "True", "False"):
                node = nodes.Const(token.value in ("true", "True"), lineno=token.lineno)
            elif token.value in ("none", "None"):
                node = nodes.Const(None, lineno=token.lineno)
            elif with_namespace and self.stream.current.type == "dot":
                # If namespace attributes are allowed at this point, and the next
                # token is a dot, produce a namespace reference.
                next(self.stream)
                attr = self.stream.expect("name")
                node = nodes.NSRef(token.value, attr.value, lineno=token.lineno)
            else:
                node = nodes.Name(token.value, "load", lineno=token.lineno)
        elif token.type == "string":
            next(self.stream)
            buf = [token.value]
            lineno = token.lineno
            while self.stream.current.type == "string":
                buf.append(self.stream.current.value)
                next(self.stream)
            node = nodes.Const("".join(buf), lineno=lineno)
        elif token.type in ("integer", "float"):
            next(self.stream)
            node = nodes.Const(token.value, lineno=token.lineno)
        elif token.type == "lparen":
            next(self.stream)
            node = self.parse_tuple(explicit_parentheses=True)
            self.stream.expect("rparen")
        elif token.type == "lbracket":
            node = self.parse_list()
        elif token.type == "lbrace":
            node = self.parse_dict()
        else:
            self.fail(f"unexpected {describe_token(token)!r}", token.lineno)
        return node

    def parse_tuple(
        self,
        simplified: bool = False,
        with_condexpr: bool = True,
        extra_end_rules: t.Optional[t.Tuple[str, ...]] = None,
        explicit_parentheses: bool = False,
        with_namespace: bool = False,
    ) -> t.Union[nodes.Tuple, nodes.Expr]:
        """Works like `parse_expression` but if multiple expressions are
        delimited by a comma a :class:`~jinja2.nodes.Tuple` node is created.
        This method could also return a regular expression instead of a tuple
        if no commas where found.

        The default parsing mode is a full tuple.  If `simplified` is `True`
        only names and literals are parsed; ``with_namespace`` allows namespace
        attr refs as well. The `no_condexpr` parameter is forwarded to
        :meth:`parse_expression`.

        Because tuples do not require delimiters and may end in a bogus comma
        an extra hint is needed that marks the end of a tuple.  For example
        for loops support tuples between `for` and `in`.  In that case the
        `extra_end_rules` is set to ``['name:in']``.

        `explicit_parentheses` is true if the parsing was triggered by an
        expression in parentheses.  This is used to figure out if an empty
        tuple is a valid expression or not.
        """
        lineno = self.stream.current.lineno
        if simplified:

            def parse() -> nodes.Expr:
                return self.parse_primary(with_namespace=with_namespace)

        else:

            def parse() -> nodes.Expr:
                return self.parse_expression(with_condexpr=with_condexpr)

        args: t.List[nodes.Expr] = []
        is_tuple = False

        while True:
            if args:
                self.stream.expect("comma")
            if self.is_tuple_end(extra_end_rules):
                break
            args.append(parse())
            if self.stream.current.type == "comma":
                is_tuple = True
            else:
                break
            lineno = self.stream.current.lineno

        if not is_tuple:
            if args:
                return args[0]

            # if we don't have explicit parentheses, an empty tuple is
            # not a valid expression.  This would mean nothing (literally
            # nothing) in the spot of an expression would be an empty
            # tuple.
            if not explicit_parentheses:
                self.fail(
                    "Expected an expression,"
                    f" got {describe_token(self.stream.current)!r}"
                )

        return nodes.Tuple(args, "load", lineno=lineno)

    def parse_list(self) -> nodes.List:
        token = self.stream.expect("lbracket")
        items: t.List[nodes.Expr] = []
        while self.stream.current.type != "rbracket":
            if items:
                self.stream.expect("comma")
            if self.stream.current.type == "rbracket":
                break
            items.append(self.parse_expression())
        self.stream.expect("rbracket")
        return nodes.List(items, lineno=token.lineno)

    def parse_dict(self) -> nodes.Dict:
        token = self.stream.expect("lbrace")
        items: t.List[nodes.Pair] = []
        while self.stream.current.type != "rbrace":
            if items:
                self.stream.expect("comma")
            if self.stream.current.type == "rbrace":
                break
            key = self.parse_expression()
            self.stream.expect("colon")
            value = self.parse_expression()
            items.append(nodes.Pair(key, value, lineno=key.lineno))
        self.stream.expect("rbrace")
        return nodes.Dict(items, lineno=token.lineno)

    def parse_postfix(self, node: nodes.Expr) -> nodes.Expr:
        while True:
            token_type = self.stream.current.type
            if token_type == "dot" or token_type == "lbracket":
                node = self.parse_subscript(node)
            # calls are valid both after postfix expressions (getattr
            # and getitem) as well as filters and tests
            elif token_type == "lparen":
                node = self.parse_call(node)
            else:
                break
        return node

    def parse_filter_expr(self, node: nodes.Expr) -> nodes.Expr:
        while True:
            token_type = self.stream.current.type
            if token_type == "pipe":
                node = self.parse_filter(node)  # type: ignore
            elif token_type == "name" and self.stream.current.value == "is":
                node = self.parse_test(node)
            # calls are valid both after postfix expressions (getattr
            # and getitem) as well as filters and tests
            elif token_type == "lparen":
                node = self.parse_call(node)
            else:
                break
        return node

    def parse_subscript(
        self, node: nodes.Expr
    ) -> t.Union[nodes.Getattr, nodes.Getitem]:
        token = next(self.stream)
        arg: nodes.Expr

        if token.type == "dot":
            attr_token = self.stream.current
            next(self.stream)
            if attr_token.type == "name":
                return nodes.Getattr(
                    node, attr_token.value, "load", lineno=token.lineno
                )
            elif attr_token.type != "integer":
                self.fail("expected name or number", attr_token.lineno)
            arg = nodes.Const(attr_token.value, lineno=attr_token.lineno)
            return nodes.Getitem(node, arg, "load", lineno=token.lineno)
        if token.type == "lbracket":
            args: t.List[nodes.Expr] = []
            while self.stream.current.type != "rbracket":
                if args:
                    self.stream.expect("comma")
                args.append(self.parse_subscribed())
            self.stream.expect("rbracket")
            if len(args) == 1:
                arg = args[0]
            else:
                arg = nodes.Tuple(args, "load", lineno=token.lineno)
            return nodes.Getitem(node, arg, "load", lineno=token.lineno)
        self.fail("expected subscript expression", token.lineno)

    def parse_subscribed(self) -> nodes.Expr:
        lineno = self.stream.current.lineno
        args: t.List[t.Optional[nodes.Expr]]

        if self.stream.current.type == "colon":
            next(self.stream)
            args = [None]
        else:
            node = self.parse_expression()
            if self.stream.current.type != "colon":
                return node
            next(self.stream)
            args = [node]

        if self.stream.current.type == "colon":
            args.append(None)
        elif self.stream.current.type not in ("rbracket", "comma"):
            args.append(self.parse_expression())
        else:
            args.append(None)

        if self.stream.current.type == "colon":
            next(self.stream)
            if self.stream.current.type not in ("rbracket", "comma"):
                args.append(self.parse_expression())
            else:
                args.append(None)
        else:
            args.append(None)

        return nodes.Slice(lineno=lineno, *args)  # noqa: B026

    def parse_call_args(
        self,
    ) -> t.Tuple[
        t.List[nodes.Expr],
        t.List[nodes.Keyword],
        t.Optional[nodes.Expr],
        t.Optional[nodes.Expr],
    ]:
        token = self.stream.expect("lparen")
        args = []
        kwargs = []
        dyn_args = None
        dyn_kwargs = None
        require_comma = False

        def ensure(expr: bool) -> None:
            if not expr:
                self.fail("invalid syntax for function call expression", token.lineno)

        while self.stream.current.type != "rparen":
            if require_comma:
                self.stream.expect("comma")

                # support for trailing comma
                if self.stream.current.type == "rparen":
                    break

            if self.stream.current.type == "mul":
                ensure(dyn_args is None and dyn_kwargs is None)
                next(self.stream)
                dyn_args = self.parse_expression()
            elif self.stream.current.type == "pow":
                ensure(dyn_kwargs is None)
                next(self.stream)
                dyn_kwargs = self.parse_expression()
            else:
                if (
                    self.stream.current.type == "name"
                    and self.stream.look().type == "assign"
                ):
                    # Parsing a kwarg
                    ensure(dyn_kwargs is None)
                    key = self.stream.current.value
                    self.stream.skip(2)
                    value = self.parse_expression()
                    kwargs.append(nodes.Keyword(key, value, lineno=value.lineno))
                else:
                    # Parsing an arg
                    ensure(dyn_args is None and dyn_kwargs is None and not kwargs)
                    args.append(self.parse_expression())

            require_comma = True

        self.stream.expect("rparen")
        return args, kwargs, dyn_args, dyn_kwargs

    def parse_call(self, node: nodes.Expr) -> nodes.Call:
        # The lparen will be expected in parse_call_args, but the lineno
        # needs to be recorded before the stream is advanced.
        token = self.stream.current
        args, kwargs, dyn_args, dyn_kwargs = self.parse_call_args()
        return nodes.Call(node, args, kwargs, dyn_args, dyn_kwargs, lineno=token.lineno)

    def parse_filter(
        self, node: t.Optional[nodes.Expr], start_inline: bool = False
    ) -> t.Optional[nodes.Expr]:
        while self.stream.current.type == "pipe" or start_inline:
            if not start_inline:
                next(self.stream)
            token = self.stream.expect("name")
            name = token.value
            while self.stream.current.type == "dot":
                next(self.stream)
                name += "." + self.stream.expect("name").value
            if self.stream.current.type == "lparen":
                args, kwargs, dyn_args, dyn_kwargs = self.parse_call_args()
            else:
                args = []
                kwargs = []
                dyn_args = dyn_kwargs = None
            node = nodes.Filter(
                node, name, args, kwargs, dyn_args, dyn_kwargs, lineno=token.lineno
            )
            start_inline = False
        return node

    def parse_test(self, node: nodes.Expr) -> nodes.Expr:
        token = next(self.stream)
        if self.stream.current.test("name:not"):
            next(self.stream)
            negated = True
        else:
            negated = False
        name = self.stream.expect("name").value
        while self.stream.current.type == "dot":
            next(self.stream)
            name += "." + self.stream.expect("name").value
        dyn_args = dyn_kwargs = None
        kwargs: t.List[nodes.Keyword] = []
        if self.stream.current.type == "lparen":
            args, kwargs, dyn_args, dyn_kwargs = self.parse_call_args()
        elif self.stream.current.type in {
            "name",
            "string",
            "integer",
            "float",
            "lparen",
            "lbracket",
            "lbrace",
        } and not self.stream.current.test_any("name:else", "name:or", "name:and"):
            if self.stream.current.test("name:is"):
                self.fail("You cannot chain multiple tests with is")
            arg_node = self.parse_primary()
            arg_node = self.parse_postfix(arg_node)
            args = [arg_node]
        else:
            args = []
        node = nodes.Test(
            node, name, args, kwargs, dyn_args, dyn_kwargs, lineno=token.lineno
        )
        if negated:
            node = nodes.Not(node, lineno=token.lineno)
        return node

    def subparse(
        self, end_tokens: t.Optional[t.Tuple[str, ...]] = None
    ) -> t.List[nodes.Node]:
        body: t.List[nodes.Node] = []
        data_buffer: t.List[nodes.Node] = []
        add_data = data_buffer.append

        if end_tokens is not None:
            self._end_token_stack.append(end_tokens)

        def flush_data() -> None:
            if data_buffer:
                lineno = data_buffer[0].lineno
                body.append(nodes.Output(data_buffer[:], lineno=lineno))
                del data_buffer[:]

        try:
            while self.stream:
                token = self.stream.current
                if token.type == "data":
                    if token.value:
                        add_data(nodes.TemplateData(token.value, lineno=token.lineno))
                    next(self.stream)
                elif token.type == "variable_begin":
                    next(self.stream)
                    add_data(self.parse_tuple(with_condexpr=True))
                    self.stream.expect("variable_end")
                elif token.type == "block_begin":
                    flush_data()
                    next(self.stream)
                    if end_tokens is not None and self.stream.current.test_any(
                        *end_tokens
                    ):
                        return body
                    rv = self.parse_statement()
                    if isinstance(rv, list):
                        body.extend(rv)
                    else:
                        body.append(rv)
                    self.stream.expect("block_end")
                else:
                    raise AssertionError("internal parsing error")

            flush_data()
        finally:
            if end_tokens is not None:
                self._end_token_stack.pop()
        return body

    def parse(self) -> nodes.Template:
        """Parse the whole template into a `Template` node."""
        result = nodes.Template(self.subparse(), lineno=1)
        result.set_environment(self.environment)
        return result

# === NexusCore/openenv\Lib\site-packages\google\ai\generativelanguage_v1beta\services\retriever_service\transports\grpc_asyncio.py ===
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

from google.ai.generativelanguage_v1beta.types import retriever, retriever_service

from .base import DEFAULT_CLIENT_INFO, RetrieverServiceTransport
from .grpc import RetrieverServiceGrpcTransport


class RetrieverServiceGrpcAsyncIOTransport(RetrieverServiceTransport):
    """gRPC AsyncIO backend transport for RetrieverService.

    An API for semantic search over a corpus of user uploaded
    content.

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
    def create_corpus(
        self,
    ) -> Callable[[retriever_service.CreateCorpusRequest], Awaitable[retriever.Corpus]]:
        r"""Return a callable for the create corpus method over gRPC.

        Creates an empty ``Corpus``.

        Returns:
            Callable[[~.CreateCorpusRequest],
                    Awaitable[~.Corpus]]:
                A function that, when called, will call the underlying RPC
                on the server.
        """
        # Generate a "stub function" on-the-fly which will actually make
        # the request.
        # gRPC handles serialization and deserialization, so we just need
        # to pass in the functions for each.
        if "create_corpus" not in self._stubs:
            self._stubs["create_corpus"] = self.grpc_channel.unary_unary(
                "/google.ai.generativelanguage.v1beta.RetrieverService/CreateCorpus",
                request_serializer=retriever_service.CreateCorpusRequest.serialize,
                response_deserializer=retriever.Corpus.deserialize,
            )
        return self._stubs["create_corpus"]

    @property
    def get_corpus(
        self,
    ) -> Callable[[retriever_service.GetCorpusRequest], Awaitable[retriever.Corpus]]:
        r"""Return a callable for the get corpus method over gRPC.

        Gets information about a specific ``Corpus``.

        Returns:
            Callable[[~.GetCorpusRequest],
                    Awaitable[~.Corpus]]:
                A function that, when called, will call the underlying RPC
                on the server.
        """
        # Generate a "stub function" on-the-fly which will actually make
        # the request.
        # gRPC handles serialization and deserialization, so we just need
        # to pass in the functions for each.
        if "get_corpus" not in self._stubs:
            self._stubs["get_corpus"] = self.grpc_channel.unary_unary(
                "/google.ai.generativelanguage.v1beta.RetrieverService/GetCorpus",
                request_serializer=retriever_service.GetCorpusRequest.serialize,
                response_deserializer=retriever.Corpus.deserialize,
            )
        return self._stubs["get_corpus"]

    @property
    def update_corpus(
        self,
    ) -> Callable[[retriever_service.UpdateCorpusRequest], Awaitable[retriever.Corpus]]:
        r"""Return a callable for the update corpus method over gRPC.

        Updates a ``Corpus``.

        Returns:
            Callable[[~.UpdateCorpusRequest],
                    Awaitable[~.Corpus]]:
                A function that, when called, will call the underlying RPC
                on the server.
        """
        # Generate a "stub function" on-the-fly which will actually make
        # the request.
        # gRPC handles serialization and deserialization, so we just need
        # to pass in the functions for each.
        if "update_corpus" not in self._stubs:
            self._stubs["update_corpus"] = self.grpc_channel.unary_unary(
                "/google.ai.generativelanguage.v1beta.RetrieverService/UpdateCorpus",
                request_serializer=retriever_service.UpdateCorpusRequest.serialize,
                response_deserializer=retriever.Corpus.deserialize,
            )
        return self._stubs["update_corpus"]

    @property
    def delete_corpus(
        self,
    ) -> Callable[[retriever_service.DeleteCorpusRequest], Awaitable[empty_pb2.Empty]]:
        r"""Return a callable for the delete corpus method over gRPC.

        Deletes a ``Corpus``.

        Returns:
            Callable[[~.DeleteCorpusRequest],
                    Awaitable[~.Empty]]:
                A function that, when called, will call the underlying RPC
                on the server.
        """
        # Generate a "stub function" on-the-fly which will actually make
        # the request.
        # gRPC handles serialization and deserialization, so we just need
        # to pass in the functions for each.
        if "delete_corpus" not in self._stubs:
            self._stubs["delete_corpus"] = self.grpc_channel.unary_unary(
                "/google.ai.generativelanguage.v1beta.RetrieverService/DeleteCorpus",
                request_serializer=retriever_service.DeleteCorpusRequest.serialize,
                response_deserializer=empty_pb2.Empty.FromString,
            )
        return self._stubs["delete_corpus"]

    @property
    def list_corpora(
        self,
    ) -> Callable[
        [retriever_service.ListCorporaRequest],
        Awaitable[retriever_service.ListCorporaResponse],
    ]:
        r"""Return a callable for the list corpora method over gRPC.

        Lists all ``Corpora`` owned by the user.

        Returns:
            Callable[[~.ListCorporaRequest],
                    Awaitable[~.ListCorporaResponse]]:
                A function that, when called, will call the underlying RPC
                on the server.
        """
        # Generate a "stub function" on-the-fly which will actually make
        # the request.
        # gRPC handles serialization and deserialization, so we just need
        # to pass in the functions for each.
        if "list_corpora" not in self._stubs:
            self._stubs["list_corpora"] = self.grpc_channel.unary_unary(
                "/google.ai.generativelanguage.v1beta.RetrieverService/ListCorpora",
                request_serializer=retriever_service.ListCorporaRequest.serialize,
                response_deserializer=retriever_service.ListCorporaResponse.deserialize,
            )
        return self._stubs["list_corpora"]

    @property
    def query_corpus(
        self,
    ) -> Callable[
        [retriever_service.QueryCorpusRequest],
        Awaitable[retriever_service.QueryCorpusResponse],
    ]:
        r"""Return a callable for the query corpus method over gRPC.

        Performs semantic search over a ``Corpus``.

        Returns:
            Callable[[~.QueryCorpusRequest],
                    Awaitable[~.QueryCorpusResponse]]:
                A function that, when called, will call the underlying RPC
                on the server.
        """
        # Generate a "stub function" on-the-fly which will actually make
        # the request.
        # gRPC handles serialization and deserialization, so we just need
        # to pass in the functions for each.
        if "query_corpus" not in self._stubs:
            self._stubs["query_corpus"] = self.grpc_channel.unary_unary(
                "/google.ai.generativelanguage.v1beta.RetrieverService/QueryCorpus",
                request_serializer=retriever_service.QueryCorpusRequest.serialize,
                response_deserializer=retriever_service.QueryCorpusResponse.deserialize,
            )
        return self._stubs["query_corpus"]

    @property
    def create_document(
        self,
    ) -> Callable[
        [retriever_service.CreateDocumentRequest], Awaitable[retriever.Document]
    ]:
        r"""Return a callable for the create document method over gRPC.

        Creates an empty ``Document``.

        Returns:
            Callable[[~.CreateDocumentRequest],
                    Awaitable[~.Document]]:
                A function that, when called, will call the underlying RPC
                on the server.
        """
        # Generate a "stub function" on-the-fly which will actually make
        # the request.
        # gRPC handles serialization and deserialization, so we just need
        # to pass in the functions for each.
        if "create_document" not in self._stubs:
            self._stubs["create_document"] = self.grpc_channel.unary_unary(
                "/google.ai.generativelanguage.v1beta.RetrieverService/CreateDocument",
                request_serializer=retriever_service.CreateDocumentRequest.serialize,
                response_deserializer=retriever.Document.deserialize,
            )
        return self._stubs["create_document"]

    @property
    def get_document(
        self,
    ) -> Callable[
        [retriever_service.GetDocumentRequest], Awaitable[retriever.Document]
    ]:
        r"""Return a callable for the get document method over gRPC.

        Gets information about a specific ``Document``.

        Returns:
            Callable[[~.GetDocumentRequest],
                    Awaitable[~.Document]]:
                A function that, when called, will call the underlying RPC
                on the server.
        """
        # Generate a "stub function" on-the-fly which will actually make
        # the request.
        # gRPC handles serialization and deserialization, so we just need
        # to pass in the functions for each.
        if "get_document" not in self._stubs:
            self._stubs["get_document"] = self.grpc_channel.unary_unary(
                "/google.ai.generativelanguage.v1beta.RetrieverService/GetDocument",
                request_serializer=retriever_service.GetDocumentRequest.serialize,
                response_deserializer=retriever.Document.deserialize,
            )
        return self._stubs["get_document"]

    @property
    def update_document(
        self,
    ) -> Callable[
        [retriever_service.UpdateDocumentRequest], Awaitable[retriever.Document]
    ]:
        r"""Return a callable for the update document method over gRPC.

        Updates a ``Document``.

        Returns:
            Callable[[~.UpdateDocumentRequest],
                    Awaitable[~.Document]]:
                A function that, when called, will call the underlying RPC
                on the server.
        """
        # Generate a "stub function" on-the-fly which will actually make
        # the request.
        # gRPC handles serialization and deserialization, so we just need
        # to pass in the functions for each.
        if "update_document" not in self._stubs:
            self._stubs["update_document"] = self.grpc_channel.unary_unary(
                "/google.ai.generativelanguage.v1beta.RetrieverService/UpdateDocument",
                request_serializer=retriever_service.UpdateDocumentRequest.serialize,
                response_deserializer=retriever.Document.deserialize,
            )
        return self._stubs["update_document"]

    @property
    def delete_document(
        self,
    ) -> Callable[
        [retriever_service.DeleteDocumentRequest], Awaitable[empty_pb2.Empty]
    ]:
        r"""Return a callable for the delete document method over gRPC.

        Deletes a ``Document``.

        Returns:
            Callable[[~.DeleteDocumentRequest],
                    Awaitable[~.Empty]]:
                A function that, when called, will call the underlying RPC
                on the server.
        """
        # Generate a "stub function" on-the-fly which will actually make
        # the request.
        # gRPC handles serialization and deserialization, so we just need
        # to pass in the functions for each.
        if "delete_document" not in self._stubs:
            self._stubs["delete_document"] = self.grpc_channel.unary_unary(
                "/google.ai.generativelanguage.v1beta.RetrieverService/DeleteDocument",
                request_serializer=retriever_service.DeleteDocumentRequest.serialize,
                response_deserializer=empty_pb2.Empty.FromString,
            )
        return self._stubs["delete_document"]

    @property
    def list_documents(
        self,
    ) -> Callable[
        [retriever_service.ListDocumentsRequest],
        Awaitable[retriever_service.ListDocumentsResponse],
    ]:
        r"""Return a callable for the list documents method over gRPC.

        Lists all ``Document``\ s in a ``Corpus``.

        Returns:
            Callable[[~.ListDocumentsRequest],
                    Awaitable[~.ListDocumentsResponse]]:
                A function that, when called, will call the underlying RPC
                on the server.
        """
        # Generate a "stub function" on-the-fly which will actually make
        # the request.
        # gRPC handles serialization and deserialization, so we just need
        # to pass in the functions for each.
        if "list_documents" not in self._stubs:
            self._stubs["list_documents"] = self.grpc_channel.unary_unary(
                "/google.ai.generativelanguage.v1beta.RetrieverService/ListDocuments",
                request_serializer=retriever_service.ListDocumentsRequest.serialize,
                response_deserializer=retriever_service.ListDocumentsResponse.deserialize,
            )
        return self._stubs["list_documents"]

    @property
    def query_document(
        self,
    ) -> Callable[
        [retriever_service.QueryDocumentRequest],
        Awaitable[retriever_service.QueryDocumentResponse],
    ]:
        r"""Return a callable for the query document method over gRPC.

        Performs semantic search over a ``Document``.

        Returns:
            Callable[[~.QueryDocumentRequest],
                    Awaitable[~.QueryDocumentResponse]]:
                A function that, when called, will call the underlying RPC
                on the server.
        """
        # Generate a "stub function" on-the-fly which will actually make
        # the request.
        # gRPC handles serialization and deserialization, so we just need
        # to pass in the functions for each.
        if "query_document" not in self._stubs:
            self._stubs["query_document"] = self.grpc_channel.unary_unary(
                "/google.ai.generativelanguage.v1beta.RetrieverService/QueryDocument",
                request_serializer=retriever_service.QueryDocumentRequest.serialize,
                response_deserializer=retriever_service.QueryDocumentResponse.deserialize,
            )
        return self._stubs["query_document"]

    @property
    def create_chunk(
        self,
    ) -> Callable[[retriever_service.CreateChunkRequest], Awaitable[retriever.Chunk]]:
        r"""Return a callable for the create chunk method over gRPC.

        Creates a ``Chunk``.

        Returns:
            Callable[[~.CreateChunkRequest],
                    Awaitable[~.Chunk]]:
                A function that, when called, will call the underlying RPC
                on the server.
        """
        # Generate a "stub function" on-the-fly which will actually make
        # the request.
        # gRPC handles serialization and deserialization, so we just need
        # to pass in the functions for each.
        if "create_chunk" not in self._stubs:
            self._stubs["create_chunk"] = self.grpc_channel.unary_unary(
                "/google.ai.generativelanguage.v1beta.RetrieverService/CreateChunk",
                request_serializer=retriever_service.CreateChunkRequest.serialize,
                response_deserializer=retriever.Chunk.deserialize,
            )
        return self._stubs["create_chunk"]

    @property
    def batch_create_chunks(
        self,
    ) -> Callable[
        [retriever_service.BatchCreateChunksRequest],
        Awaitable[retriever_service.BatchCreateChunksResponse],
    ]:
        r"""Return a callable for the batch create chunks method over gRPC.

        Batch create ``Chunk``\ s.

        Returns:
            Callable[[~.BatchCreateChunksRequest],
                    Awaitable[~.BatchCreateChunksResponse]]:
                A function that, when called, will call the underlying RPC
                on the server.
        """
        # Generate a "stub function" on-the-fly which will actually make
        # the request.
        # gRPC handles serialization and deserialization, so we just need
        # to pass in the functions for each.
        if "batch_create_chunks" not in self._stubs:
            self._stubs["batch_create_chunks"] = self.grpc_channel.unary_unary(
                "/google.ai.generativelanguage.v1beta.RetrieverService/BatchCreateChunks",
                request_serializer=retriever_service.BatchCreateChunksRequest.serialize,
                response_deserializer=retriever_service.BatchCreateChunksResponse.deserialize,
            )
        return self._stubs["batch_create_chunks"]

    @property
    def get_chunk(
        self,
    ) -> Callable[[retriever_service.GetChunkRequest], Awaitable[retriever.Chunk]]:
        r"""Return a callable for the get chunk method over gRPC.

        Gets information about a specific ``Chunk``.

        Returns:
            Callable[[~.GetChunkRequest],
                    Awaitable[~.Chunk]]:
                A function that, when called, will call the underlying RPC
                on the server.
        """
        # Generate a "stub function" on-the-fly which will actually make
        # the request.
        # gRPC handles serialization and deserialization, so we just need
        # to pass in the functions for each.
        if "get_chunk" not in self._stubs:
            self._stubs["get_chunk"] = self.grpc_channel.unary_unary(
                "/google.ai.generativelanguage.v1beta.RetrieverService/GetChunk",
                request_serializer=retriever_service.GetChunkRequest.serialize,
                response_deserializer=retriever.Chunk.deserialize,
            )
        return self._stubs["get_chunk"]

    @property
    def update_chunk(
        self,
    ) -> Callable[[retriever_service.UpdateChunkRequest], Awaitable[retriever.Chunk]]:
        r"""Return a callable for the update chunk method over gRPC.

        Updates a ``Chunk``.

        Returns:
            Callable[[~.UpdateChunkRequest],
                    Awaitable[~.Chunk]]:
                A function that, when called, will call the underlying RPC
                on the server.
        """
        # Generate a "stub function" on-the-fly which will actually make
        # the request.
        # gRPC handles serialization and deserialization, so we just need
        # to pass in the functions for each.
        if "update_chunk" not in self._stubs:
            self._stubs["update_chunk"] = self.grpc_channel.unary_unary(
                "/google.ai.generativelanguage.v1beta.RetrieverService/UpdateChunk",
                request_serializer=retriever_service.UpdateChunkRequest.serialize,
                response_deserializer=retriever.Chunk.deserialize,
            )
        return self._stubs["update_chunk"]

    @property
    def batch_update_chunks(
        self,
    ) -> Callable[
        [retriever_service.BatchUpdateChunksRequest],
        Awaitable[retriever_service.BatchUpdateChunksResponse],
    ]:
        r"""Return a callable for the batch update chunks method over gRPC.

        Batch update ``Chunk``\ s.

        Returns:
            Callable[[~.BatchUpdateChunksRequest],
                    Awaitable[~.BatchUpdateChunksResponse]]:
                A function that, when called, will call the underlying RPC
                on the server.
        """
        # Generate a "stub function" on-the-fly which will actually make
        # the request.
        # gRPC handles serialization and deserialization, so we just need
        # to pass in the functions for each.
        if "batch_update_chunks" not in self._stubs:
            self._stubs["batch_update_chunks"] = self.grpc_channel.unary_unary(
                "/google.ai.generativelanguage.v1beta.RetrieverService/BatchUpdateChunks",
                request_serializer=retriever_service.BatchUpdateChunksRequest.serialize,
                response_deserializer=retriever_service.BatchUpdateChunksResponse.deserialize,
            )
        return self._stubs["batch_update_chunks"]

    @property
    def delete_chunk(
        self,
    ) -> Callable[[retriever_service.DeleteChunkRequest], Awaitable[empty_pb2.Empty]]:
        r"""Return a callable for the delete chunk method over gRPC.

        Deletes a ``Chunk``.

        Returns:
            Callable[[~.DeleteChunkRequest],
                    Awaitable[~.Empty]]:
                A function that, when called, will call the underlying RPC
                on the server.
        """
        # Generate a "stub function" on-the-fly which will actually make
        # the request.
        # gRPC handles serialization and deserialization, so we just need
        # to pass in the functions for each.
        if "delete_chunk" not in self._stubs:
            self._stubs["delete_chunk"] = self.grpc_channel.unary_unary(
                "/google.ai.generativelanguage.v1beta.RetrieverService/DeleteChunk",
                request_serializer=retriever_service.DeleteChunkRequest.serialize,
                response_deserializer=empty_pb2.Empty.FromString,
            )
        return self._stubs["delete_chunk"]

    @property
    def batch_delete_chunks(
        self,
    ) -> Callable[
        [retriever_service.BatchDeleteChunksRequest], Awaitable[empty_pb2.Empty]
    ]:
        r"""Return a callable for the batch delete chunks method over gRPC.

        Batch delete ``Chunk``\ s.

        Returns:
            Callable[[~.BatchDeleteChunksRequest],
                    Awaitable[~.Empty]]:
                A function that, when called, will call the underlying RPC
                on the server.
        """
        # Generate a "stub function" on-the-fly which will actually make
        # the request.
        # gRPC handles serialization and deserialization, so we just need
        # to pass in the functions for each.
        if "batch_delete_chunks" not in self._stubs:
            self._stubs["batch_delete_chunks"] = self.grpc_channel.unary_unary(
                "/google.ai.generativelanguage.v1beta.RetrieverService/BatchDeleteChunks",
                request_serializer=retriever_service.BatchDeleteChunksRequest.serialize,
                response_deserializer=empty_pb2.Empty.FromString,
            )
        return self._stubs["batch_delete_chunks"]

    @property
    def list_chunks(
        self,
    ) -> Callable[
        [retriever_service.ListChunksRequest],
        Awaitable[retriever_service.ListChunksResponse],
    ]:
        r"""Return a callable for the list chunks method over gRPC.

        Lists all ``Chunk``\ s in a ``Document``.

        Returns:
            Callable[[~.ListChunksRequest],
                    Awaitable[~.ListChunksResponse]]:
                A function that, when called, will call the underlying RPC
                on the server.
        """
        # Generate a "stub function" on-the-fly which will actually make
        # the request.
        # gRPC handles serialization and deserialization, so we just need
        # to pass in the functions for each.
        if "list_chunks" not in self._stubs:
            self._stubs["list_chunks"] = self.grpc_channel.unary_unary(
                "/google.ai.generativelanguage.v1beta.RetrieverService/ListChunks",
                request_serializer=retriever_service.ListChunksRequest.serialize,
                response_deserializer=retriever_service.ListChunksResponse.deserialize,
            )
        return self._stubs["list_chunks"]

    def _prep_wrapped_messages(self, client_info):
        """Precompute the wrapped methods, overriding the base class method to use async wrappers."""
        self._wrapped_methods = {
            self.create_corpus: gapic_v1.method_async.wrap_method(
                self.create_corpus,
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
            self.get_corpus: gapic_v1.method_async.wrap_method(
                self.get_corpus,
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
            self.update_corpus: gapic_v1.method_async.wrap_method(
                self.update_corpus,
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
            self.delete_corpus: gapic_v1.method_async.wrap_method(
                self.delete_corpus,
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
            self.list_corpora: gapic_v1.method_async.wrap_method(
                self.list_corpora,
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
            self.query_corpus: gapic_v1.method_async.wrap_method(
                self.query_corpus,
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
            self.create_document: gapic_v1.method_async.wrap_method(
                self.create_document,
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
            self.get_document: gapic_v1.method_async.wrap_method(
                self.get_document,
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
            self.update_document: gapic_v1.method_async.wrap_method(
                self.update_document,
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
            self.delete_document: gapic_v1.method_async.wrap_method(
                self.delete_document,
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
            self.list_documents: gapic_v1.method_async.wrap_method(
                self.list_documents,
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
            self.query_document: gapic_v1.method_async.wrap_method(
                self.query_document,
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
            self.create_chunk: gapic_v1.method_async.wrap_method(
                self.create_chunk,
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
            self.batch_create_chunks: gapic_v1.method_async.wrap_method(
                self.batch_create_chunks,
                default_timeout=None,
                client_info=client_info,
            ),
            self.get_chunk: gapic_v1.method_async.wrap_method(
                self.get_chunk,
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
            self.update_chunk: gapic_v1.method_async.wrap_method(
                self.update_chunk,
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
            self.batch_update_chunks: gapic_v1.method_async.wrap_method(
                self.batch_update_chunks,
                default_timeout=None,
                client_info=client_info,
            ),
            self.delete_chunk: gapic_v1.method_async.wrap_method(
                self.delete_chunk,
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
            self.batch_delete_chunks: gapic_v1.method_async.wrap_method(
                self.batch_delete_chunks,
                default_timeout=None,
                client_info=client_info,
            ),
            self.list_chunks: gapic_v1.method_async.wrap_method(
                self.list_chunks,
                default_timeout=None,
                client_info=client_info,
            ),
        }

    def close(self):
        return self.grpc_channel.close()


__all__ = ("RetrieverServiceGrpcAsyncIOTransport",)

# === NexusCore/openenv\Lib\site-packages\aiohttp\http_parser.py ===
import abc
import asyncio
import re
import string
from contextlib import suppress
from enum import IntEnum
from typing import (
    Any,
    ClassVar,
    Final,
    Generic,
    List,
    Literal,
    NamedTuple,
    Optional,
    Pattern,
    Set,
    Tuple,
    Type,
    TypeVar,
    Union,
)

from multidict import CIMultiDict, CIMultiDictProxy, istr
from yarl import URL

from . import hdrs
from .base_protocol import BaseProtocol
from .compression_utils import HAS_BROTLI, BrotliDecompressor, ZLibDecompressor
from .helpers import (
    _EXC_SENTINEL,
    DEBUG,
    EMPTY_BODY_METHODS,
    EMPTY_BODY_STATUS_CODES,
    NO_EXTENSIONS,
    BaseTimerContext,
    set_exception,
)
from .http_exceptions import (
    BadHttpMessage,
    BadHttpMethod,
    BadStatusLine,
    ContentEncodingError,
    ContentLengthError,
    InvalidHeader,
    InvalidURLError,
    LineTooLong,
    TransferEncodingError,
)
from .http_writer import HttpVersion, HttpVersion10
from .streams import EMPTY_PAYLOAD, StreamReader
from .typedefs import RawHeaders

__all__ = (
    "HeadersParser",
    "HttpParser",
    "HttpRequestParser",
    "HttpResponseParser",
    "RawRequestMessage",
    "RawResponseMessage",
)

_SEP = Literal[b"\r\n", b"\n"]

ASCIISET: Final[Set[str]] = set(string.printable)

# See https://www.rfc-editor.org/rfc/rfc9110.html#name-overview
# and https://www.rfc-editor.org/rfc/rfc9110.html#name-tokens
#
#     method = token
#     tchar = "!" / "#" / "$" / "%" / "&" / "'" / "*" / "+" / "-" / "." /
#             "^" / "_" / "`" / "|" / "~" / DIGIT / ALPHA
#     token = 1*tchar
_TCHAR_SPECIALS: Final[str] = re.escape("!#$%&'*+-.^_`|~")
TOKENRE: Final[Pattern[str]] = re.compile(f"[0-9A-Za-z{_TCHAR_SPECIALS}]+")
VERSRE: Final[Pattern[str]] = re.compile(r"HTTP/(\d)\.(\d)", re.ASCII)
DIGITS: Final[Pattern[str]] = re.compile(r"\d+", re.ASCII)
HEXDIGITS: Final[Pattern[bytes]] = re.compile(rb"[0-9a-fA-F]+")


class RawRequestMessage(NamedTuple):
    method: str
    path: str
    version: HttpVersion
    headers: "CIMultiDictProxy[str]"
    raw_headers: RawHeaders
    should_close: bool
    compression: Optional[str]
    upgrade: bool
    chunked: bool
    url: URL


class RawResponseMessage(NamedTuple):
    version: HttpVersion
    code: int
    reason: str
    headers: CIMultiDictProxy[str]
    raw_headers: RawHeaders
    should_close: bool
    compression: Optional[str]
    upgrade: bool
    chunked: bool


_MsgT = TypeVar("_MsgT", RawRequestMessage, RawResponseMessage)


class ParseState(IntEnum):

    PARSE_NONE = 0
    PARSE_LENGTH = 1
    PARSE_CHUNKED = 2
    PARSE_UNTIL_EOF = 3


class ChunkState(IntEnum):
    PARSE_CHUNKED_SIZE = 0
    PARSE_CHUNKED_CHUNK = 1
    PARSE_CHUNKED_CHUNK_EOF = 2
    PARSE_MAYBE_TRAILERS = 3
    PARSE_TRAILERS = 4


class HeadersParser:
    def __init__(
        self,
        max_line_size: int = 8190,
        max_headers: int = 32768,
        max_field_size: int = 8190,
        lax: bool = False,
    ) -> None:
        self.max_line_size = max_line_size
        self.max_headers = max_headers
        self.max_field_size = max_field_size
        self._lax = lax

    def parse_headers(
        self, lines: List[bytes]
    ) -> Tuple["CIMultiDictProxy[str]", RawHeaders]:
        headers: CIMultiDict[str] = CIMultiDict()
        # note: "raw" does not mean inclusion of OWS before/after the field value
        raw_headers = []

        lines_idx = 1
        line = lines[1]
        line_count = len(lines)

        while line:
            # Parse initial header name : value pair.
            try:
                bname, bvalue = line.split(b":", 1)
            except ValueError:
                raise InvalidHeader(line) from None

            if len(bname) == 0:
                raise InvalidHeader(bname)

            # https://www.rfc-editor.org/rfc/rfc9112.html#section-5.1-2
            if {bname[0], bname[-1]} & {32, 9}:  # {" ", "\t"}
                raise InvalidHeader(line)

            bvalue = bvalue.lstrip(b" \t")
            if len(bname) > self.max_field_size:
                raise LineTooLong(
                    "request header name {}".format(
                        bname.decode("utf8", "backslashreplace")
                    ),
                    str(self.max_field_size),
                    str(len(bname)),
                )
            name = bname.decode("utf-8", "surrogateescape")
            if not TOKENRE.fullmatch(name):
                raise InvalidHeader(bname)

            header_length = len(bvalue)

            # next line
            lines_idx += 1
            line = lines[lines_idx]

            # consume continuation lines
            continuation = self._lax and line and line[0] in (32, 9)  # (' ', '\t')

            # Deprecated: https://www.rfc-editor.org/rfc/rfc9112.html#name-obsolete-line-folding
            if continuation:
                bvalue_lst = [bvalue]
                while continuation:
                    header_length += len(line)
                    if header_length > self.max_field_size:
                        raise LineTooLong(
                            "request header field {}".format(
                                bname.decode("utf8", "backslashreplace")
                            ),
                            str(self.max_field_size),
                            str(header_length),
                        )
                    bvalue_lst.append(line)

                    # next line
                    lines_idx += 1
                    if lines_idx < line_count:
                        line = lines[lines_idx]
                        if line:
                            continuation = line[0] in (32, 9)  # (' ', '\t')
                    else:
                        line = b""
                        break
                bvalue = b"".join(bvalue_lst)
            else:
                if header_length > self.max_field_size:
                    raise LineTooLong(
                        "request header field {}".format(
                            bname.decode("utf8", "backslashreplace")
                        ),
                        str(self.max_field_size),
                        str(header_length),
                    )

            bvalue = bvalue.strip(b" \t")
            value = bvalue.decode("utf-8", "surrogateescape")

            # https://www.rfc-editor.org/rfc/rfc9110.html#section-5.5-5
            if "\n" in value or "\r" in value or "\x00" in value:
                raise InvalidHeader(bvalue)

            headers.add(name, value)
            raw_headers.append((bname, bvalue))

        return (CIMultiDictProxy(headers), tuple(raw_headers))


def _is_supported_upgrade(headers: CIMultiDictProxy[str]) -> bool:
    """Check if the upgrade header is supported."""
    return headers.get(hdrs.UPGRADE, "").lower() in {"tcp", "websocket"}


class HttpParser(abc.ABC, Generic[_MsgT]):
    lax: ClassVar[bool] = False

    def __init__(
        self,
        protocol: Optional[BaseProtocol] = None,
        loop: Optional[asyncio.AbstractEventLoop] = None,
        limit: int = 2**16,
        max_line_size: int = 8190,
        max_headers: int = 32768,
        max_field_size: int = 8190,
        timer: Optional[BaseTimerContext] = None,
        code: Optional[int] = None,
        method: Optional[str] = None,
        payload_exception: Optional[Type[BaseException]] = None,
        response_with_body: bool = True,
        read_until_eof: bool = False,
        auto_decompress: bool = True,
    ) -> None:
        self.protocol = protocol
        self.loop = loop
        self.max_line_size = max_line_size
        self.max_headers = max_headers
        self.max_field_size = max_field_size
        self.timer = timer
        self.code = code
        self.method = method
        self.payload_exception = payload_exception
        self.response_with_body = response_with_body
        self.read_until_eof = read_until_eof

        self._lines: List[bytes] = []
        self._tail = b""
        self._upgraded = False
        self._payload = None
        self._payload_parser: Optional[HttpPayloadParser] = None
        self._auto_decompress = auto_decompress
        self._limit = limit
        self._headers_parser = HeadersParser(
            max_line_size, max_headers, max_field_size, self.lax
        )

    @abc.abstractmethod
    def parse_message(self, lines: List[bytes]) -> _MsgT: ...

    @abc.abstractmethod
    def _is_chunked_te(self, te: str) -> bool: ...

    def feed_eof(self) -> Optional[_MsgT]:
        if self._payload_parser is not None:
            self._payload_parser.feed_eof()
            self._payload_parser = None
        else:
            # try to extract partial message
            if self._tail:
                self._lines.append(self._tail)

            if self._lines:
                if self._lines[-1] != "\r\n":
                    self._lines.append(b"")
                with suppress(Exception):
                    return self.parse_message(self._lines)
        return None

    def feed_data(
        self,
        data: bytes,
        SEP: _SEP = b"\r\n",
        EMPTY: bytes = b"",
        CONTENT_LENGTH: istr = hdrs.CONTENT_LENGTH,
        METH_CONNECT: str = hdrs.METH_CONNECT,
        SEC_WEBSOCKET_KEY1: istr = hdrs.SEC_WEBSOCKET_KEY1,
    ) -> Tuple[List[Tuple[_MsgT, StreamReader]], bool, bytes]:

        messages = []

        if self._tail:
            data, self._tail = self._tail + data, b""

        data_len = len(data)
        start_pos = 0
        loop = self.loop

        should_close = False
        while start_pos < data_len:

            # read HTTP message (request/response line + headers), \r\n\r\n
            # and split by lines
            if self._payload_parser is None and not self._upgraded:
                pos = data.find(SEP, start_pos)
                # consume \r\n
                if pos == start_pos and not self._lines:
                    start_pos = pos + len(SEP)
                    continue

                if pos >= start_pos:
                    if should_close:
                        raise BadHttpMessage("Data after `Connection: close`")

                    # line found
                    line = data[start_pos:pos]
                    if SEP == b"\n":  # For lax response parsing
                        line = line.rstrip(b"\r")
                    self._lines.append(line)
                    start_pos = pos + len(SEP)

                    # \r\n\r\n found
                    if self._lines[-1] == EMPTY:
                        try:
                            msg: _MsgT = self.parse_message(self._lines)
                        finally:
                            self._lines.clear()

                        def get_content_length() -> Optional[int]:
                            # payload length
                            length_hdr = msg.headers.get(CONTENT_LENGTH)
                            if length_hdr is None:
                                return None

                            # Shouldn't allow +/- or other number formats.
                            # https://www.rfc-editor.org/rfc/rfc9110#section-8.6-2
                            # msg.headers is already stripped of leading/trailing wsp
                            if not DIGITS.fullmatch(length_hdr):
                                raise InvalidHeader(CONTENT_LENGTH)

                            return int(length_hdr)

                        length = get_content_length()
                        # do not support old websocket spec
                        if SEC_WEBSOCKET_KEY1 in msg.headers:
                            raise InvalidHeader(SEC_WEBSOCKET_KEY1)

                        self._upgraded = msg.upgrade and _is_supported_upgrade(
                            msg.headers
                        )

                        method = getattr(msg, "method", self.method)
                        # code is only present on responses
                        code = getattr(msg, "code", 0)

                        assert self.protocol is not None
                        # calculate payload
                        empty_body = code in EMPTY_BODY_STATUS_CODES or bool(
                            method and method in EMPTY_BODY_METHODS
                        )
                        if not empty_body and (
                            ((length is not None and length > 0) or msg.chunked)
                            and not self._upgraded
                        ):
                            payload = StreamReader(
                                self.protocol,
                                timer=self.timer,
                                loop=loop,
                                limit=self._limit,
                            )
                            payload_parser = HttpPayloadParser(
                                payload,
                                length=length,
                                chunked=msg.chunked,
                                method=method,
                                compression=msg.compression,
                                code=self.code,
                                response_with_body=self.response_with_body,
                                auto_decompress=self._auto_decompress,
                                lax=self.lax,
                            )
                            if not payload_parser.done:
                                self._payload_parser = payload_parser
                        elif method == METH_CONNECT:
                            assert isinstance(msg, RawRequestMessage)
                            payload = StreamReader(
                                self.protocol,
                                timer=self.timer,
                                loop=loop,
                                limit=self._limit,
                            )
                            self._upgraded = True
                            self._payload_parser = HttpPayloadParser(
                                payload,
                                method=msg.method,
                                compression=msg.compression,
                                auto_decompress=self._auto_decompress,
                                lax=self.lax,
                            )
                        elif not empty_body and length is None and self.read_until_eof:
                            payload = StreamReader(
                                self.protocol,
                                timer=self.timer,
                                loop=loop,
                                limit=self._limit,
                            )
                            payload_parser = HttpPayloadParser(
                                payload,
                                length=length,
                                chunked=msg.chunked,
                                method=method,
                                compression=msg.compression,
                                code=self.code,
                                response_with_body=self.response_with_body,
                                auto_decompress=self._auto_decompress,
                                lax=self.lax,
                            )
                            if not payload_parser.done:
                                self._payload_parser = payload_parser
                        else:
                            payload = EMPTY_PAYLOAD

                        messages.append((msg, payload))
                        should_close = msg.should_close
                else:
                    self._tail = data[start_pos:]
                    data = EMPTY
                    break

            # no parser, just store
            elif self._payload_parser is None and self._upgraded:
                assert not self._lines
                break

            # feed payload
            elif data and start_pos < data_len:
                assert not self._lines
                assert self._payload_parser is not None
                try:
                    eof, data = self._payload_parser.feed_data(data[start_pos:], SEP)
                except BaseException as underlying_exc:
                    reraised_exc = underlying_exc
                    if self.payload_exception is not None:
                        reraised_exc = self.payload_exception(str(underlying_exc))

                    set_exception(
                        self._payload_parser.payload,
                        reraised_exc,
                        underlying_exc,
                    )

                    eof = True
                    data = b""

                if eof:
                    start_pos = 0
                    data_len = len(data)
                    self._payload_parser = None
                    continue
            else:
                break

        if data and start_pos < data_len:
            data = data[start_pos:]
        else:
            data = EMPTY

        return messages, self._upgraded, data

    def parse_headers(
        self, lines: List[bytes]
    ) -> Tuple[
        "CIMultiDictProxy[str]", RawHeaders, Optional[bool], Optional[str], bool, bool
    ]:
        """Parses RFC 5322 headers from a stream.

        Line continuations are supported. Returns list of header name
        and value pairs. Header name is in upper case.
        """
        headers, raw_headers = self._headers_parser.parse_headers(lines)
        close_conn = None
        encoding = None
        upgrade = False
        chunked = False

        # https://www.rfc-editor.org/rfc/rfc9110.html#section-5.5-6
        # https://www.rfc-editor.org/rfc/rfc9110.html#name-collected-abnf
        singletons = (
            hdrs.CONTENT_LENGTH,
            hdrs.CONTENT_LOCATION,
            hdrs.CONTENT_RANGE,
            hdrs.CONTENT_TYPE,
            hdrs.ETAG,
            hdrs.HOST,
            hdrs.MAX_FORWARDS,
            hdrs.SERVER,
            hdrs.TRANSFER_ENCODING,
            hdrs.USER_AGENT,
        )
        bad_hdr = next((h for h in singletons if len(headers.getall(h, ())) > 1), None)
        if bad_hdr is not None:
            raise BadHttpMessage(f"Duplicate '{bad_hdr}' header found.")

        # keep-alive
        conn = headers.get(hdrs.CONNECTION)
        if conn:
            v = conn.lower()
            if v == "close":
                close_conn = True
            elif v == "keep-alive":
                close_conn = False
            # https://www.rfc-editor.org/rfc/rfc9110.html#name-101-switching-protocols
            elif v == "upgrade" and headers.get(hdrs.UPGRADE):
                upgrade = True

        # encoding
        enc = headers.get(hdrs.CONTENT_ENCODING)
        if enc:
            enc = enc.lower()
            if enc in ("gzip", "deflate", "br"):
                encoding = enc

        # chunking
        te = headers.get(hdrs.TRANSFER_ENCODING)
        if te is not None:
            if self._is_chunked_te(te):
                chunked = True

            if hdrs.CONTENT_LENGTH in headers:
                raise BadHttpMessage(
                    "Transfer-Encoding can't be present with Content-Length",
                )

        return (headers, raw_headers, close_conn, encoding, upgrade, chunked)

    def set_upgraded(self, val: bool) -> None:
        """Set connection upgraded (to websocket) mode.

        :param bool val: new state.
        """
        self._upgraded = val


class HttpRequestParser(HttpParser[RawRequestMessage]):
    """Read request status line.

    Exception .http_exceptions.BadStatusLine
    could be raised in case of any errors in status line.
    Returns RawRequestMessage.
    """

    def parse_message(self, lines: List[bytes]) -> RawRequestMessage:
        # request line
        line = lines[0].decode("utf-8", "surrogateescape")
        try:
            method, path, version = line.split(" ", maxsplit=2)
        except ValueError:
            raise BadHttpMethod(line) from None

        if len(path) > self.max_line_size:
            raise LineTooLong(
                "Status line is too long", str(self.max_line_size), str(len(path))
            )

        # method
        if not TOKENRE.fullmatch(method):
            raise BadHttpMethod(method)

        # version
        match = VERSRE.fullmatch(version)
        if match is None:
            raise BadStatusLine(line)
        version_o = HttpVersion(int(match.group(1)), int(match.group(2)))

        if method == "CONNECT":
            # authority-form,
            # https://datatracker.ietf.org/doc/html/rfc7230#section-5.3.3
            url = URL.build(authority=path, encoded=True)
        elif path.startswith("/"):
            # origin-form,
            # https://datatracker.ietf.org/doc/html/rfc7230#section-5.3.1
            path_part, _hash_separator, url_fragment = path.partition("#")
            path_part, _question_mark_separator, qs_part = path_part.partition("?")

            # NOTE: `yarl.URL.build()` is used to mimic what the Cython-based
            # NOTE: parser does, otherwise it results into the same
            # NOTE: HTTP Request-Line input producing different
            # NOTE: `yarl.URL()` objects
            url = URL.build(
                path=path_part,
                query_string=qs_part,
                fragment=url_fragment,
                encoded=True,
            )
        elif path == "*" and method == "OPTIONS":
            # asterisk-form,
            url = URL(path, encoded=True)
        else:
            # absolute-form for proxy maybe,
            # https://datatracker.ietf.org/doc/html/rfc7230#section-5.3.2
            url = URL(path, encoded=True)
            if url.scheme == "":
                # not absolute-form
                raise InvalidURLError(
                    path.encode(errors="surrogateescape").decode("latin1")
                )

        # read headers
        (
            headers,
            raw_headers,
            close,
            compression,
            upgrade,
            chunked,
        ) = self.parse_headers(lines)

        if close is None:  # then the headers weren't set in the request
            if version_o <= HttpVersion10:  # HTTP 1.0 must asks to not close
                close = True
            else:  # HTTP 1.1 must ask to close.
                close = False

        return RawRequestMessage(
            method,
            path,
            version_o,
            headers,
            raw_headers,
            close,
            compression,
            upgrade,
            chunked,
            url,
        )

    def _is_chunked_te(self, te: str) -> bool:
        if te.rsplit(",", maxsplit=1)[-1].strip(" \t").lower() == "chunked":
            return True
        # https://www.rfc-editor.org/rfc/rfc9112#section-6.3-2.4.3
        raise BadHttpMessage("Request has invalid `Transfer-Encoding`")


class HttpResponseParser(HttpParser[RawResponseMessage]):
    """Read response status line and headers.

    BadStatusLine could be raised in case of any errors in status line.
    Returns RawResponseMessage.
    """

    # Lax mode should only be enabled on response parser.
    lax = not DEBUG

    def feed_data(
        self,
        data: bytes,
        SEP: Optional[_SEP] = None,
        *args: Any,
        **kwargs: Any,
    ) -> Tuple[List[Tuple[RawResponseMessage, StreamReader]], bool, bytes]:
        if SEP is None:
            SEP = b"\r\n" if DEBUG else b"\n"
        return super().feed_data(data, SEP, *args, **kwargs)

    def parse_message(self, lines: List[bytes]) -> RawResponseMessage:
        line = lines[0].decode("utf-8", "surrogateescape")
        try:
            version, status = line.split(maxsplit=1)
        except ValueError:
            raise BadStatusLine(line) from None

        try:
            status, reason = status.split(maxsplit=1)
        except ValueError:
            status = status.strip()
            reason = ""

        if len(reason) > self.max_line_size:
            raise LineTooLong(
                "Status line is too long", str(self.max_line_size), str(len(reason))
            )

        # version
        match = VERSRE.fullmatch(version)
        if match is None:
            raise BadStatusLine(line)
        version_o = HttpVersion(int(match.group(1)), int(match.group(2)))

        # The status code is a three-digit ASCII number, no padding
        if len(status) != 3 or not DIGITS.fullmatch(status):
            raise BadStatusLine(line)
        status_i = int(status)

        # read headers
        (
            headers,
            raw_headers,
            close,
            compression,
            upgrade,
            chunked,
        ) = self.parse_headers(lines)

        if close is None:
            if version_o <= HttpVersion10:
                close = True
            # https://www.rfc-editor.org/rfc/rfc9112.html#name-message-body-length
            elif 100 <= status_i < 200 or status_i in {204, 304}:
                close = False
            elif hdrs.CONTENT_LENGTH in headers or hdrs.TRANSFER_ENCODING in headers:
                close = False
            else:
                # https://www.rfc-editor.org/rfc/rfc9112.html#section-6.3-2.8
                close = True

        return RawResponseMessage(
            version_o,
            status_i,
            reason.strip(),
            headers,
            raw_headers,
            close,
            compression,
            upgrade,
            chunked,
        )

    def _is_chunked_te(self, te: str) -> bool:
        # https://www.rfc-editor.org/rfc/rfc9112#section-6.3-2.4.2
        return te.rsplit(",", maxsplit=1)[-1].strip(" \t").lower() == "chunked"


class HttpPayloadParser:
    def __init__(
        self,
        payload: StreamReader,
        length: Optional[int] = None,
        chunked: bool = False,
        compression: Optional[str] = None,
        code: Optional[int] = None,
        method: Optional[str] = None,
        response_with_body: bool = True,
        auto_decompress: bool = True,
        lax: bool = False,
    ) -> None:
        self._length = 0
        self._type = ParseState.PARSE_UNTIL_EOF
        self._chunk = ChunkState.PARSE_CHUNKED_SIZE
        self._chunk_size = 0
        self._chunk_tail = b""
        self._auto_decompress = auto_decompress
        self._lax = lax
        self.done = False

        # payload decompression wrapper
        if response_with_body and compression and self._auto_decompress:
            real_payload: Union[StreamReader, DeflateBuffer] = DeflateBuffer(
                payload, compression
            )
        else:
            real_payload = payload

        # payload parser
        if not response_with_body:
            # don't parse payload if it's not expected to be received
            self._type = ParseState.PARSE_NONE
            real_payload.feed_eof()
            self.done = True
        elif chunked:
            self._type = ParseState.PARSE_CHUNKED
        elif length is not None:
            self._type = ParseState.PARSE_LENGTH
            self._length = length
            if self._length == 0:
                real_payload.feed_eof()
                self.done = True

        self.payload = real_payload

    def feed_eof(self) -> None:
        if self._type == ParseState.PARSE_UNTIL_EOF:
            self.payload.feed_eof()
        elif self._type == ParseState.PARSE_LENGTH:
            raise ContentLengthError(
                "Not enough data to satisfy content length header."
            )
        elif self._type == ParseState.PARSE_CHUNKED:
            raise TransferEncodingError(
                "Not enough data to satisfy transfer length header."
            )

    def feed_data(
        self, chunk: bytes, SEP: _SEP = b"\r\n", CHUNK_EXT: bytes = b";"
    ) -> Tuple[bool, bytes]:
        # Read specified amount of bytes
        if self._type == ParseState.PARSE_LENGTH:
            required = self._length
            chunk_len = len(chunk)

            if required >= chunk_len:
                self._length = required - chunk_len
                self.payload.feed_data(chunk, chunk_len)
                if self._length == 0:
                    self.payload.feed_eof()
                    return True, b""
            else:
                self._length = 0
                self.payload.feed_data(chunk[:required], required)
                self.payload.feed_eof()
                return True, chunk[required:]

        # Chunked transfer encoding parser
        elif self._type == ParseState.PARSE_CHUNKED:
            if self._chunk_tail:
                chunk = self._chunk_tail + chunk
                self._chunk_tail = b""

            while chunk:

                # read next chunk size
                if self._chunk == ChunkState.PARSE_CHUNKED_SIZE:
                    pos = chunk.find(SEP)
                    if pos >= 0:
                        i = chunk.find(CHUNK_EXT, 0, pos)
                        if i >= 0:
                            size_b = chunk[:i]  # strip chunk-extensions
                            # Verify no LF in the chunk-extension
                            if b"\n" in (ext := chunk[i:pos]):
                                exc = BadHttpMessage(
                                    f"Unexpected LF in chunk-extension: {ext!r}"
                                )
                                set_exception(self.payload, exc)
                                raise exc
                        else:
                            size_b = chunk[:pos]

                        if self._lax:  # Allow whitespace in lax mode.
                            size_b = size_b.strip()

                        if not re.fullmatch(HEXDIGITS, size_b):
                            exc = TransferEncodingError(
                                chunk[:pos].decode("ascii", "surrogateescape")
                            )
                            set_exception(self.payload, exc)
                            raise exc
                        size = int(bytes(size_b), 16)

                        chunk = chunk[pos + len(SEP) :]
                        if size == 0:  # eof marker
                            self._chunk = ChunkState.PARSE_MAYBE_TRAILERS
                            if self._lax and chunk.startswith(b"\r"):
                                chunk = chunk[1:]
                        else:
                            self._chunk = ChunkState.PARSE_CHUNKED_CHUNK
                            self._chunk_size = size
                            self.payload.begin_http_chunk_receiving()
                    else:
                        self._chunk_tail = chunk
                        return False, b""

                # read chunk and feed buffer
                if self._chunk == ChunkState.PARSE_CHUNKED_CHUNK:
                    required = self._chunk_size
                    chunk_len = len(chunk)

                    if required > chunk_len:
                        self._chunk_size = required - chunk_len
                        self.payload.feed_data(chunk, chunk_len)
                        return False, b""
                    else:
                        self._chunk_size = 0
                        self.payload.feed_data(chunk[:required], required)
                        chunk = chunk[required:]
                        self._chunk = ChunkState.PARSE_CHUNKED_CHUNK_EOF
                        self.payload.end_http_chunk_receiving()

                # toss the CRLF at the end of the chunk
                if self._chunk == ChunkState.PARSE_CHUNKED_CHUNK_EOF:
                    if self._lax and chunk.startswith(b"\r"):
                        chunk = chunk[1:]
                    if chunk[: len(SEP)] == SEP:
                        chunk = chunk[len(SEP) :]
                        self._chunk = ChunkState.PARSE_CHUNKED_SIZE
                    else:
                        self._chunk_tail = chunk
                        return False, b""

                # if stream does not contain trailer, after 0\r\n
                # we should get another \r\n otherwise
                # trailers needs to be skipped until \r\n\r\n
                if self._chunk == ChunkState.PARSE_MAYBE_TRAILERS:
                    head = chunk[: len(SEP)]
                    if head == SEP:
                        # end of stream
                        self.payload.feed_eof()
                        return True, chunk[len(SEP) :]
                    # Both CR and LF, or only LF may not be received yet. It is
                    # expected that CRLF or LF will be shown at the very first
                    # byte next time, otherwise trailers should come. The last
                    # CRLF which marks the end of response might not be
                    # contained in the same TCP segment which delivered the
                    # size indicator.
                    if not head:
                        return False, b""
                    if head == SEP[:1]:
                        self._chunk_tail = head
                        return False, b""
                    self._chunk = ChunkState.PARSE_TRAILERS

                # read and discard trailer up to the CRLF terminator
                if self._chunk == ChunkState.PARSE_TRAILERS:
                    pos = chunk.find(SEP)
                    if pos >= 0:
                        chunk = chunk[pos + len(SEP) :]
                        self._chunk = ChunkState.PARSE_MAYBE_TRAILERS
                    else:
                        self._chunk_tail = chunk
                        return False, b""

        # Read all bytes until eof
        elif self._type == ParseState.PARSE_UNTIL_EOF:
            self.payload.feed_data(chunk, len(chunk))

        return False, b""


class DeflateBuffer:
    """DeflateStream decompress stream and feed data into specified stream."""

    decompressor: Any

    def __init__(self, out: StreamReader, encoding: Optional[str]) -> None:
        self.out = out
        self.size = 0
        self.encoding = encoding
        self._started_decoding = False

        self.decompressor: Union[BrotliDecompressor, ZLibDecompressor]
        if encoding == "br":
            if not HAS_BROTLI:  # pragma: no cover
                raise ContentEncodingError(
                    "Can not decode content-encoding: brotli (br). "
                    "Please install `Brotli`"
                )
            self.decompressor = BrotliDecompressor()
        else:
            self.decompressor = ZLibDecompressor(encoding=encoding)

    def set_exception(
        self,
        exc: BaseException,
        exc_cause: BaseException = _EXC_SENTINEL,
    ) -> None:
        set_exception(self.out, exc, exc_cause)

    def feed_data(self, chunk: bytes, size: int) -> None:
        if not size:
            return

        self.size += size

        # RFC1950
        # bits 0..3 = CM = 0b1000 = 8 = "deflate"
        # bits 4..7 = CINFO = 1..7 = windows size.
        if (
            not self._started_decoding
            and self.encoding == "deflate"
            and chunk[0] & 0xF != 8
        ):
            # Change the decoder to decompress incorrectly compressed data
            # Actually we should issue a warning about non-RFC-compliant data.
            self.decompressor = ZLibDecompressor(
                encoding=self.encoding, suppress_deflate_header=True
            )

        try:
            chunk = self.decompressor.decompress_sync(chunk)
        except Exception:
            raise ContentEncodingError(
                "Can not decode content-encoding: %s" % self.encoding
            )

        self._started_decoding = True

        if chunk:
            self.out.feed_data(chunk, len(chunk))

    def feed_eof(self) -> None:
        chunk = self.decompressor.flush()

        if chunk or self.size > 0:
            self.out.feed_data(chunk, len(chunk))
            if self.encoding == "deflate" and not self.decompressor.eof:
                raise ContentEncodingError("deflate")

        self.out.feed_eof()

    def begin_http_chunk_receiving(self) -> None:
        self.out.begin_http_chunk_receiving()

    def end_http_chunk_receiving(self) -> None:
        self.out.end_http_chunk_receiving()


HttpRequestParserPy = HttpRequestParser
HttpResponseParserPy = HttpResponseParser
RawRequestMessagePy = RawRequestMessage
RawResponseMessagePy = RawResponseMessage

try:
    if not NO_EXTENSIONS:
        from ._http_parser import (  # type: ignore[import-not-found,no-redef]
            HttpRequestParser,
            HttpResponseParser,
            RawRequestMessage,
            RawResponseMessage,
        )

        HttpRequestParserC = HttpRequestParser
        HttpResponseParserC = HttpResponseParser
        RawRequestMessageC = RawRequestMessage
        RawResponseMessageC = RawResponseMessage
except ImportError:  # pragma: no cover
    pass

# === NexusCore/openenv\Lib\site-packages\setuptools\_vendor\more_itertools\recipes.py ===
"""Imported from the recipes section of the itertools documentation.

All functions taken from the recipes section of the itertools library docs
[1]_.
Some backward-compatible usability improvements have been made.

.. [1] http://docs.python.org/library/itertools.html#recipes

"""

import math
import operator

from collections import deque
from collections.abc import Sized
from functools import partial, reduce
from itertools import (
    chain,
    combinations,
    compress,
    count,
    cycle,
    groupby,
    islice,
    product,
    repeat,
    starmap,
    tee,
    zip_longest,
)
from random import randrange, sample, choice
from sys import hexversion

__all__ = [
    'all_equal',
    'batched',
    'before_and_after',
    'consume',
    'convolve',
    'dotproduct',
    'first_true',
    'factor',
    'flatten',
    'grouper',
    'iter_except',
    'iter_index',
    'matmul',
    'ncycles',
    'nth',
    'nth_combination',
    'padnone',
    'pad_none',
    'pairwise',
    'partition',
    'polynomial_eval',
    'polynomial_from_roots',
    'polynomial_derivative',
    'powerset',
    'prepend',
    'quantify',
    'reshape',
    'random_combination_with_replacement',
    'random_combination',
    'random_permutation',
    'random_product',
    'repeatfunc',
    'roundrobin',
    'sieve',
    'sliding_window',
    'subslices',
    'sum_of_squares',
    'tabulate',
    'tail',
    'take',
    'totient',
    'transpose',
    'triplewise',
    'unique',
    'unique_everseen',
    'unique_justseen',
]

_marker = object()


# zip with strict is available for Python 3.10+
try:
    zip(strict=True)
except TypeError:
    _zip_strict = zip
else:
    _zip_strict = partial(zip, strict=True)

# math.sumprod is available for Python 3.12+
_sumprod = getattr(math, 'sumprod', lambda x, y: dotproduct(x, y))


def take(n, iterable):
    """Return first *n* items of the iterable as a list.

        >>> take(3, range(10))
        [0, 1, 2]

    If there are fewer than *n* items in the iterable, all of them are
    returned.

        >>> take(10, range(3))
        [0, 1, 2]

    """
    return list(islice(iterable, n))


def tabulate(function, start=0):
    """Return an iterator over the results of ``func(start)``,
    ``func(start + 1)``, ``func(start + 2)``...

    *func* should be a function that accepts one integer argument.

    If *start* is not specified it defaults to 0. It will be incremented each
    time the iterator is advanced.

        >>> square = lambda x: x ** 2
        >>> iterator = tabulate(square, -3)
        >>> take(4, iterator)
        [9, 4, 1, 0]

    """
    return map(function, count(start))


def tail(n, iterable):
    """Return an iterator over the last *n* items of *iterable*.

    >>> t = tail(3, 'ABCDEFG')
    >>> list(t)
    ['E', 'F', 'G']

    """
    # If the given iterable has a length, then we can use islice to get its
    # final elements. Note that if the iterable is not actually Iterable,
    # either islice or deque will throw a TypeError. This is why we don't
    # check if it is Iterable.
    if isinstance(iterable, Sized):
        yield from islice(iterable, max(0, len(iterable) - n), None)
    else:
        yield from iter(deque(iterable, maxlen=n))


def consume(iterator, n=None):
    """Advance *iterable* by *n* steps. If *n* is ``None``, consume it
    entirely.

    Efficiently exhausts an iterator without returning values. Defaults to
    consuming the whole iterator, but an optional second argument may be
    provided to limit consumption.

        >>> i = (x for x in range(10))
        >>> next(i)
        0
        >>> consume(i, 3)
        >>> next(i)
        4
        >>> consume(i)
        >>> next(i)
        Traceback (most recent call last):
          File "<stdin>", line 1, in <module>
        StopIteration

    If the iterator has fewer items remaining than the provided limit, the
    whole iterator will be consumed.

        >>> i = (x for x in range(3))
        >>> consume(i, 5)
        >>> next(i)
        Traceback (most recent call last):
          File "<stdin>", line 1, in <module>
        StopIteration

    """
    # Use functions that consume iterators at C speed.
    if n is None:
        # feed the entire iterator into a zero-length deque
        deque(iterator, maxlen=0)
    else:
        # advance to the empty slice starting at position n
        next(islice(iterator, n, n), None)


def nth(iterable, n, default=None):
    """Returns the nth item or a default value.

    >>> l = range(10)
    >>> nth(l, 3)
    3
    >>> nth(l, 20, "zebra")
    'zebra'

    """
    return next(islice(iterable, n, None), default)


def all_equal(iterable, key=None):
    """
    Returns ``True`` if all the elements are equal to each other.

        >>> all_equal('aaaa')
        True
        >>> all_equal('aaab')
        False

    A function that accepts a single argument and returns a transformed version
    of each input item can be specified with *key*:

        >>> all_equal('AaaA', key=str.casefold)
        True
        >>> all_equal([1, 2, 3], key=lambda x: x < 10)
        True

    """
    return len(list(islice(groupby(iterable, key), 2))) <= 1


def quantify(iterable, pred=bool):
    """Return the how many times the predicate is true.

    >>> quantify([True, False, True])
    2

    """
    return sum(map(pred, iterable))


def pad_none(iterable):
    """Returns the sequence of elements and then returns ``None`` indefinitely.

        >>> take(5, pad_none(range(3)))
        [0, 1, 2, None, None]

    Useful for emulating the behavior of the built-in :func:`map` function.

    See also :func:`padded`.

    """
    return chain(iterable, repeat(None))


padnone = pad_none


def ncycles(iterable, n):
    """Returns the sequence elements *n* times

    >>> list(ncycles(["a", "b"], 3))
    ['a', 'b', 'a', 'b', 'a', 'b']

    """
    return chain.from_iterable(repeat(tuple(iterable), n))


def dotproduct(vec1, vec2):
    """Returns the dot product of the two iterables.

    >>> dotproduct([10, 10], [20, 20])
    400

    """
    return sum(map(operator.mul, vec1, vec2))


def flatten(listOfLists):
    """Return an iterator flattening one level of nesting in a list of lists.

        >>> list(flatten([[0, 1], [2, 3]]))
        [0, 1, 2, 3]

    See also :func:`collapse`, which can flatten multiple levels of nesting.

    """
    return chain.from_iterable(listOfLists)


def repeatfunc(func, times=None, *args):
    """Call *func* with *args* repeatedly, returning an iterable over the
    results.

    If *times* is specified, the iterable will terminate after that many
    repetitions:

        >>> from operator import add
        >>> times = 4
        >>> args = 3, 5
        >>> list(repeatfunc(add, times, *args))
        [8, 8, 8, 8]

    If *times* is ``None`` the iterable will not terminate:

        >>> from random import randrange
        >>> times = None
        >>> args = 1, 11
        >>> take(6, repeatfunc(randrange, times, *args))  # doctest:+SKIP
        [2, 4, 8, 1, 8, 4]

    """
    if times is None:
        return starmap(func, repeat(args))
    return starmap(func, repeat(args, times))


def _pairwise(iterable):
    """Returns an iterator of paired items, overlapping, from the original

    >>> take(4, pairwise(count()))
    [(0, 1), (1, 2), (2, 3), (3, 4)]

    On Python 3.10 and above, this is an alias for :func:`itertools.pairwise`.

    """
    a, b = tee(iterable)
    next(b, None)
    return zip(a, b)


try:
    from itertools import pairwise as itertools_pairwise
except ImportError:
    pairwise = _pairwise
else:

    def pairwise(iterable):
        return itertools_pairwise(iterable)

    pairwise.__doc__ = _pairwise.__doc__


class UnequalIterablesError(ValueError):
    def __init__(self, details=None):
        msg = 'Iterables have different lengths'
        if details is not None:
            msg += (': index 0 has length {}; index {} has length {}').format(
                *details
            )

        super().__init__(msg)


def _zip_equal_generator(iterables):
    for combo in zip_longest(*iterables, fillvalue=_marker):
        for val in combo:
            if val is _marker:
                raise UnequalIterablesError()
        yield combo


def _zip_equal(*iterables):
    # Check whether the iterables are all the same size.
    try:
        first_size = len(iterables[0])
        for i, it in enumerate(iterables[1:], 1):
            size = len(it)
            if size != first_size:
                raise UnequalIterablesError(details=(first_size, i, size))
        # All sizes are equal, we can use the built-in zip.
        return zip(*iterables)
    # If any one of the iterables didn't have a length, start reading
    # them until one runs out.
    except TypeError:
        return _zip_equal_generator(iterables)


def grouper(iterable, n, incomplete='fill', fillvalue=None):
    """Group elements from *iterable* into fixed-length groups of length *n*.

    >>> list(grouper('ABCDEF', 3))
    [('A', 'B', 'C'), ('D', 'E', 'F')]

    The keyword arguments *incomplete* and *fillvalue* control what happens for
    iterables whose length is not a multiple of *n*.

    When *incomplete* is `'fill'`, the last group will contain instances of
    *fillvalue*.

    >>> list(grouper('ABCDEFG', 3, incomplete='fill', fillvalue='x'))
    [('A', 'B', 'C'), ('D', 'E', 'F'), ('G', 'x', 'x')]

    When *incomplete* is `'ignore'`, the last group will not be emitted.

    >>> list(grouper('ABCDEFG', 3, incomplete='ignore', fillvalue='x'))
    [('A', 'B', 'C'), ('D', 'E', 'F')]

    When *incomplete* is `'strict'`, a subclass of `ValueError` will be raised.

    >>> it = grouper('ABCDEFG', 3, incomplete='strict')
    >>> list(it)  # doctest: +IGNORE_EXCEPTION_DETAIL
    Traceback (most recent call last):
    ...
    UnequalIterablesError

    """
    args = [iter(iterable)] * n
    if incomplete == 'fill':
        return zip_longest(*args, fillvalue=fillvalue)
    if incomplete == 'strict':
        return _zip_equal(*args)
    if incomplete == 'ignore':
        return zip(*args)
    else:
        raise ValueError('Expected fill, strict, or ignore')


def roundrobin(*iterables):
    """Yields an item from each iterable, alternating between them.

        >>> list(roundrobin('ABC', 'D', 'EF'))
        ['A', 'D', 'E', 'B', 'F', 'C']

    This function produces the same output as :func:`interleave_longest`, but
    may perform better for some inputs (in particular when the number of
    iterables is small).

    """
    # Algorithm credited to George Sakkis
    iterators = map(iter, iterables)
    for num_active in range(len(iterables), 0, -1):
        iterators = cycle(islice(iterators, num_active))
        yield from map(next, iterators)


def partition(pred, iterable):
    """
    Returns a 2-tuple of iterables derived from the input iterable.
    The first yields the items that have ``pred(item) == False``.
    The second yields the items that have ``pred(item) == True``.

        >>> is_odd = lambda x: x % 2 != 0
        >>> iterable = range(10)
        >>> even_items, odd_items = partition(is_odd, iterable)
        >>> list(even_items), list(odd_items)
        ([0, 2, 4, 6, 8], [1, 3, 5, 7, 9])

    If *pred* is None, :func:`bool` is used.

        >>> iterable = [0, 1, False, True, '', ' ']
        >>> false_items, true_items = partition(None, iterable)
        >>> list(false_items), list(true_items)
        ([0, False, ''], [1, True, ' '])

    """
    if pred is None:
        pred = bool

    t1, t2, p = tee(iterable, 3)
    p1, p2 = tee(map(pred, p))
    return (compress(t1, map(operator.not_, p1)), compress(t2, p2))


def powerset(iterable):
    """Yields all possible subsets of the iterable.

        >>> list(powerset([1, 2, 3]))
        [(), (1,), (2,), (3,), (1, 2), (1, 3), (2, 3), (1, 2, 3)]

    :func:`powerset` will operate on iterables that aren't :class:`set`
    instances, so repeated elements in the input will produce repeated elements
    in the output.

        >>> seq = [1, 1, 0]
        >>> list(powerset(seq))
        [(), (1,), (1,), (0,), (1, 1), (1, 0), (1, 0), (1, 1, 0)]

    For a variant that efficiently yields actual :class:`set` instances, see
    :func:`powerset_of_sets`.
    """
    s = list(iterable)
    return chain.from_iterable(combinations(s, r) for r in range(len(s) + 1))


def unique_everseen(iterable, key=None):
    """
    Yield unique elements, preserving order.

        >>> list(unique_everseen('AAAABBBCCDAABBB'))
        ['A', 'B', 'C', 'D']
        >>> list(unique_everseen('ABBCcAD', str.lower))
        ['A', 'B', 'C', 'D']

    Sequences with a mix of hashable and unhashable items can be used.
    The function will be slower (i.e., `O(n^2)`) for unhashable items.

    Remember that ``list`` objects are unhashable - you can use the *key*
    parameter to transform the list to a tuple (which is hashable) to
    avoid a slowdown.

        >>> iterable = ([1, 2], [2, 3], [1, 2])
        >>> list(unique_everseen(iterable))  # Slow
        [[1, 2], [2, 3]]
        >>> list(unique_everseen(iterable, key=tuple))  # Faster
        [[1, 2], [2, 3]]

    Similarly, you may want to convert unhashable ``set`` objects with
    ``key=frozenset``. For ``dict`` objects,
    ``key=lambda x: frozenset(x.items())`` can be used.

    """
    seenset = set()
    seenset_add = seenset.add
    seenlist = []
    seenlist_add = seenlist.append
    use_key = key is not None

    for element in iterable:
        k = key(element) if use_key else element
        try:
            if k not in seenset:
                seenset_add(k)
                yield element
        except TypeError:
            if k not in seenlist:
                seenlist_add(k)
                yield element


def unique_justseen(iterable, key=None):
    """Yields elements in order, ignoring serial duplicates

    >>> list(unique_justseen('AAAABBBCCDAABBB'))
    ['A', 'B', 'C', 'D', 'A', 'B']
    >>> list(unique_justseen('ABBCcAD', str.lower))
    ['A', 'B', 'C', 'A', 'D']

    """
    if key is None:
        return map(operator.itemgetter(0), groupby(iterable))

    return map(next, map(operator.itemgetter(1), groupby(iterable, key)))


def unique(iterable, key=None, reverse=False):
    """Yields unique elements in sorted order.

    >>> list(unique([[1, 2], [3, 4], [1, 2]]))
    [[1, 2], [3, 4]]

    *key* and *reverse* are passed to :func:`sorted`.

    >>> list(unique('ABBcCAD', str.casefold))
    ['A', 'B', 'c', 'D']
    >>> list(unique('ABBcCAD', str.casefold, reverse=True))
    ['D', 'c', 'B', 'A']

    The elements in *iterable* need not be hashable, but they must be
    comparable for sorting to work.
    """
    return unique_justseen(sorted(iterable, key=key, reverse=reverse), key=key)


def iter_except(func, exception, first=None):
    """Yields results from a function repeatedly until an exception is raised.

    Converts a call-until-exception interface to an iterator interface.
    Like ``iter(func, sentinel)``, but uses an exception instead of a sentinel
    to end the loop.

        >>> l = [0, 1, 2]
        >>> list(iter_except(l.pop, IndexError))
        [2, 1, 0]

    Multiple exceptions can be specified as a stopping condition:

        >>> l = [1, 2, 3, '...', 4, 5, 6]
        >>> list(iter_except(lambda: 1 + l.pop(), (IndexError, TypeError)))
        [7, 6, 5]
        >>> list(iter_except(lambda: 1 + l.pop(), (IndexError, TypeError)))
        [4, 3, 2]
        >>> list(iter_except(lambda: 1 + l.pop(), (IndexError, TypeError)))
        []

    """
    try:
        if first is not None:
            yield first()
        while 1:
            yield func()
    except exception:
        pass


def first_true(iterable, default=None, pred=None):
    """
    Returns the first true value in the iterable.

    If no true value is found, returns *default*

    If *pred* is not None, returns the first item for which
    ``pred(item) == True`` .

        >>> first_true(range(10))
        1
        >>> first_true(range(10), pred=lambda x: x > 5)
        6
        >>> first_true(range(10), default='missing', pred=lambda x: x > 9)
        'missing'

    """
    return next(filter(pred, iterable), default)


def random_product(*args, repeat=1):
    """Draw an item at random from each of the input iterables.

        >>> random_product('abc', range(4), 'XYZ')  # doctest:+SKIP
        ('c', 3, 'Z')

    If *repeat* is provided as a keyword argument, that many items will be
    drawn from each iterable.

        >>> random_product('abcd', range(4), repeat=2)  # doctest:+SKIP
        ('a', 2, 'd', 3)

    This equivalent to taking a random selection from
    ``itertools.product(*args, **kwarg)``.

    """
    pools = [tuple(pool) for pool in args] * repeat
    return tuple(choice(pool) for pool in pools)


def random_permutation(iterable, r=None):
    """Return a random *r* length permutation of the elements in *iterable*.

    If *r* is not specified or is ``None``, then *r* defaults to the length of
    *iterable*.

        >>> random_permutation(range(5))  # doctest:+SKIP
        (3, 4, 0, 1, 2)

    This equivalent to taking a random selection from
    ``itertools.permutations(iterable, r)``.

    """
    pool = tuple(iterable)
    r = len(pool) if r is None else r
    return tuple(sample(pool, r))


def random_combination(iterable, r):
    """Return a random *r* length subsequence of the elements in *iterable*.

        >>> random_combination(range(5), 3)  # doctest:+SKIP
        (2, 3, 4)

    This equivalent to taking a random selection from
    ``itertools.combinations(iterable, r)``.

    """
    pool = tuple(iterable)
    n = len(pool)
    indices = sorted(sample(range(n), r))
    return tuple(pool[i] for i in indices)


def random_combination_with_replacement(iterable, r):
    """Return a random *r* length subsequence of elements in *iterable*,
    allowing individual elements to be repeated.

        >>> random_combination_with_replacement(range(3), 5) # doctest:+SKIP
        (0, 0, 1, 2, 2)

    This equivalent to taking a random selection from
    ``itertools.combinations_with_replacement(iterable, r)``.

    """
    pool = tuple(iterable)
    n = len(pool)
    indices = sorted(randrange(n) for i in range(r))
    return tuple(pool[i] for i in indices)


def nth_combination(iterable, r, index):
    """Equivalent to ``list(combinations(iterable, r))[index]``.

    The subsequences of *iterable* that are of length *r* can be ordered
    lexicographically. :func:`nth_combination` computes the subsequence at
    sort position *index* directly, without computing the previous
    subsequences.

        >>> nth_combination(range(5), 3, 5)
        (0, 3, 4)

    ``ValueError`` will be raised If *r* is negative or greater than the length
    of *iterable*.
    ``IndexError`` will be raised if the given *index* is invalid.
    """
    pool = tuple(iterable)
    n = len(pool)
    if (r < 0) or (r > n):
        raise ValueError

    c = 1
    k = min(r, n - r)
    for i in range(1, k + 1):
        c = c * (n - k + i) // i

    if index < 0:
        index += c

    if (index < 0) or (index >= c):
        raise IndexError

    result = []
    while r:
        c, n, r = c * r // n, n - 1, r - 1
        while index >= c:
            index -= c
            c, n = c * (n - r) // n, n - 1
        result.append(pool[-1 - n])

    return tuple(result)


def prepend(value, iterator):
    """Yield *value*, followed by the elements in *iterator*.

        >>> value = '0'
        >>> iterator = ['1', '2', '3']
        >>> list(prepend(value, iterator))
        ['0', '1', '2', '3']

    To prepend multiple values, see :func:`itertools.chain`
    or :func:`value_chain`.

    """
    return chain([value], iterator)


def convolve(signal, kernel):
    """Convolve the iterable *signal* with the iterable *kernel*.

        >>> signal = (1, 2, 3, 4, 5)
        >>> kernel = [3, 2, 1]
        >>> list(convolve(signal, kernel))
        [3, 8, 14, 20, 26, 14, 5]

    Note: the input arguments are not interchangeable, as the *kernel*
    is immediately consumed and stored.

    """
    # This implementation intentionally doesn't match the one in the itertools
    # documentation.
    kernel = tuple(kernel)[::-1]
    n = len(kernel)
    window = deque([0], maxlen=n) * n
    for x in chain(signal, repeat(0, n - 1)):
        window.append(x)
        yield _sumprod(kernel, window)


def before_and_after(predicate, it):
    """A variant of :func:`takewhile` that allows complete access to the
    remainder of the iterator.

         >>> it = iter('ABCdEfGhI')
         >>> all_upper, remainder = before_and_after(str.isupper, it)
         >>> ''.join(all_upper)
         'ABC'
         >>> ''.join(remainder) # takewhile() would lose the 'd'
         'dEfGhI'

    Note that the first iterator must be fully consumed before the second
    iterator can generate valid results.
    """
    it = iter(it)
    transition = []

    def true_iterator():
        for elem in it:
            if predicate(elem):
                yield elem
            else:
                transition.append(elem)
                return

    # Note: this is different from itertools recipes to allow nesting
    # before_and_after remainders into before_and_after again. See tests
    # for an example.
    remainder_iterator = chain(transition, it)

    return true_iterator(), remainder_iterator


def triplewise(iterable):
    """Return overlapping triplets from *iterable*.

    >>> list(triplewise('ABCDE'))
    [('A', 'B', 'C'), ('B', 'C', 'D'), ('C', 'D', 'E')]

    """
    for (a, _), (b, c) in pairwise(pairwise(iterable)):
        yield a, b, c


def sliding_window(iterable, n):
    """Return a sliding window of width *n* over *iterable*.

        >>> list(sliding_window(range(6), 4))
        [(0, 1, 2, 3), (1, 2, 3, 4), (2, 3, 4, 5)]

    If *iterable* has fewer than *n* items, then nothing is yielded:

        >>> list(sliding_window(range(3), 4))
        []

    For a variant with more features, see :func:`windowed`.
    """
    it = iter(iterable)
    window = deque(islice(it, n - 1), maxlen=n)
    for x in it:
        window.append(x)
        yield tuple(window)


def subslices(iterable):
    """Return all contiguous non-empty subslices of *iterable*.

        >>> list(subslices('ABC'))
        [['A'], ['A', 'B'], ['A', 'B', 'C'], ['B'], ['B', 'C'], ['C']]

    This is similar to :func:`substrings`, but emits items in a different
    order.
    """
    seq = list(iterable)
    slices = starmap(slice, combinations(range(len(seq) + 1), 2))
    return map(operator.getitem, repeat(seq), slices)


def polynomial_from_roots(roots):
    """Compute a polynomial's coefficients from its roots.

    >>> roots = [5, -4, 3]  # (x - 5) * (x + 4) * (x - 3)
    >>> polynomial_from_roots(roots)  # x^3 - 4 * x^2 - 17 * x + 60
    [1, -4, -17, 60]
    """
    factors = zip(repeat(1), map(operator.neg, roots))
    return list(reduce(convolve, factors, [1]))


def iter_index(iterable, value, start=0, stop=None):
    """Yield the index of each place in *iterable* that *value* occurs,
    beginning with index *start* and ending before index *stop*.


    >>> list(iter_index('AABCADEAF', 'A'))
    [0, 1, 4, 7]
    >>> list(iter_index('AABCADEAF', 'A', 1))  # start index is inclusive
    [1, 4, 7]
    >>> list(iter_index('AABCADEAF', 'A', 1, 7))  # stop index is not inclusive
    [1, 4]

    The behavior for non-scalar *values* matches the built-in Python types.

    >>> list(iter_index('ABCDABCD', 'AB'))
    [0, 4]
    >>> list(iter_index([0, 1, 2, 3, 0, 1, 2, 3], [0, 1]))
    []
    >>> list(iter_index([[0, 1], [2, 3], [0, 1], [2, 3]], [0, 1]))
    [0, 2]

    See :func:`locate` for a more general means of finding the indexes
    associated with particular values.

    """
    seq_index = getattr(iterable, 'index', None)
    if seq_index is None:
        # Slow path for general iterables
        it = islice(iterable, start, stop)
        for i, element in enumerate(it, start):
            if element is value or element == value:
                yield i
    else:
        # Fast path for sequences
        stop = len(iterable) if stop is None else stop
        i = start - 1
        try:
            while True:
                yield (i := seq_index(value, i + 1, stop))
        except ValueError:
            pass


def sieve(n):
    """Yield the primes less than n.

    >>> list(sieve(30))
    [2, 3, 5, 7, 11, 13, 17, 19, 23, 29]
    """
    if n > 2:
        yield 2
    start = 3
    data = bytearray((0, 1)) * (n // 2)
    limit = math.isqrt(n) + 1
    for p in iter_index(data, 1, start, limit):
        yield from iter_index(data, 1, start, p * p)
        data[p * p : n : p + p] = bytes(len(range(p * p, n, p + p)))
        start = p * p
    yield from iter_index(data, 1, start)


def _batched(iterable, n, *, strict=False):
    """Batch data into tuples of length *n*. If the number of items in
    *iterable* is not divisible by *n*:
    * The last batch will be shorter if *strict* is ``False``.
    * :exc:`ValueError` will be raised if *strict* is ``True``.

    >>> list(batched('ABCDEFG', 3))
    [('A', 'B', 'C'), ('D', 'E', 'F'), ('G',)]

    On Python 3.13 and above, this is an alias for :func:`itertools.batched`.
    """
    if n < 1:
        raise ValueError('n must be at least one')
    it = iter(iterable)
    while batch := tuple(islice(it, n)):
        if strict and len(batch) != n:
            raise ValueError('batched(): incomplete batch')
        yield batch


if hexversion >= 0x30D00A2:
    from itertools import batched as itertools_batched

    def batched(iterable, n, *, strict=False):
        return itertools_batched(iterable, n, strict=strict)

else:
    batched = _batched

    batched.__doc__ = _batched.__doc__


def transpose(it):
    """Swap the rows and columns of the input matrix.

    >>> list(transpose([(1, 2, 3), (11, 22, 33)]))
    [(1, 11), (2, 22), (3, 33)]

    The caller should ensure that the dimensions of the input are compatible.
    If the input is empty, no output will be produced.
    """
    return _zip_strict(*it)


def reshape(matrix, cols):
    """Reshape the 2-D input *matrix* to have a column count given by *cols*.

    >>> matrix = [(0, 1), (2, 3), (4, 5)]
    >>> cols = 3
    >>> list(reshape(matrix, cols))
    [(0, 1, 2), (3, 4, 5)]
    """
    return batched(chain.from_iterable(matrix), cols)


def matmul(m1, m2):
    """Multiply two matrices.

    >>> list(matmul([(7, 5), (3, 5)], [(2, 5), (7, 9)]))
    [(49, 80), (41, 60)]

    The caller should ensure that the dimensions of the input matrices are
    compatible with each other.
    """
    n = len(m2[0])
    return batched(starmap(_sumprod, product(m1, transpose(m2))), n)


def factor(n):
    """Yield the prime factors of n.

    >>> list(factor(360))
    [2, 2, 2, 3, 3, 5]
    """
    for prime in sieve(math.isqrt(n) + 1):
        while not n % prime:
            yield prime
            n //= prime
            if n == 1:
                return
    if n > 1:
        yield n


def polynomial_eval(coefficients, x):
    """Evaluate a polynomial at a specific value.

    Example: evaluating x^3 - 4 * x^2 - 17 * x + 60 at x = 2.5:

    >>> coefficients = [1, -4, -17, 60]
    >>> x = 2.5
    >>> polynomial_eval(coefficients, x)
    8.125
    """
    n = len(coefficients)
    if n == 0:
        return x * 0  # coerce zero to the type of x
    powers = map(pow, repeat(x), reversed(range(n)))
    return _sumprod(coefficients, powers)


def sum_of_squares(it):
    """Return the sum of the squares of the input values.

    >>> sum_of_squares([10, 20, 30])
    1400
    """
    return _sumprod(*tee(it))


def polynomial_derivative(coefficients):
    """Compute the first derivative of a polynomial.

    Example: evaluating the derivative of x^3 - 4 * x^2 - 17 * x + 60

    >>> coefficients = [1, -4, -17, 60]
    >>> derivative_coefficients = polynomial_derivative(coefficients)
    >>> derivative_coefficients
    [3, -8, -17]
    """
    n = len(coefficients)
    powers = reversed(range(1, n))
    return list(map(operator.mul, coefficients, powers))


def totient(n):
    """Return the count of natural numbers up to *n* that are coprime with *n*.

    >>> totient(9)
    6
    >>> totient(12)
    4
    """
    # The itertools docs use unique_justseen instead of set; see
    # https://github.com/more-itertools/more-itertools/issues/823
    for p in set(factor(n)):
        n = n // p * (p - 1)

    return n

# === NexusCore/openenv\Lib\site-packages\tornado\template.py ===
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

"""A simple template system that compiles templates to Python code.

Basic usage looks like::

    t = template.Template("<html>{{ myvalue }}</html>")
    print(t.generate(myvalue="XXX"))

`Loader` is a class that loads templates from a root directory and caches
the compiled templates::

    loader = template.Loader("/home/btaylor")
    print(loader.load("test.html").generate(myvalue="XXX"))

We compile all templates to raw Python. Error-reporting is currently... uh,
interesting. Syntax for the templates::

    ### base.html
    <html>
      <head>
        <title>{% block title %}Default title{% end %}</title>
      </head>
      <body>
        <ul>
          {% for student in students %}
            {% block student %}
              <li>{{ escape(student.name) }}</li>
            {% end %}
          {% end %}
        </ul>
      </body>
    </html>

    ### bold.html
    {% extends "base.html" %}

    {% block title %}A bolder title{% end %}

    {% block student %}
      <li><span style="bold">{{ escape(student.name) }}</span></li>
    {% end %}

Unlike most other template systems, we do not put any restrictions on the
expressions you can include in your statements. ``if`` and ``for`` blocks get
translated exactly into Python, so you can do complex expressions like::

   {% for student in [p for p in people if p.student and p.age > 23] %}
     <li>{{ escape(student.name) }}</li>
   {% end %}

Translating directly to Python means you can apply functions to expressions
easily, like the ``escape()`` function in the examples above. You can pass
functions in to your template just like any other variable
(In a `.RequestHandler`, override `.RequestHandler.get_template_namespace`)::

   ### Python code
   def add(x, y):
      return x + y
   template.execute(add=add)

   ### The template
   {{ add(1, 2) }}

We provide the functions `escape() <.xhtml_escape>`, `.url_escape()`,
`.json_encode()`, and `.squeeze()` to all templates by default.

Typical applications do not create `Template` or `Loader` instances by
hand, but instead use the `~.RequestHandler.render` and
`~.RequestHandler.render_string` methods of
`tornado.web.RequestHandler`, which load templates automatically based
on the ``template_path`` `.Application` setting.

Variable names beginning with ``_tt_`` are reserved by the template
system and should not be used by application code.

Syntax Reference
----------------

Template expressions are surrounded by double curly braces: ``{{ ... }}``.
The contents may be any python expression, which will be escaped according
to the current autoescape setting and inserted into the output.  Other
template directives use ``{% %}``.

To comment out a section so that it is omitted from the output, surround it
with ``{# ... #}``.


To include a literal ``{{``, ``{%``, or ``{#`` in the output, escape them as
``{{!``, ``{%!``, and ``{#!``, respectively.


``{% apply *function* %}...{% end %}``
    Applies a function to the output of all template code between ``apply``
    and ``end``::

        {% apply linkify %}{{name}} said: {{message}}{% end %}

    Note that as an implementation detail apply blocks are implemented
    as nested functions and thus may interact strangely with variables
    set via ``{% set %}``, or the use of ``{% break %}`` or ``{% continue %}``
    within loops.

``{% autoescape *function* %}``
    Sets the autoescape mode for the current file.  This does not affect
    other files, even those referenced by ``{% include %}``.  Note that
    autoescaping can also be configured globally, at the `.Application`
    or `Loader`.::

        {% autoescape xhtml_escape %}
        {% autoescape None %}

``{% block *name* %}...{% end %}``
    Indicates a named, replaceable block for use with ``{% extends %}``.
    Blocks in the parent template will be replaced with the contents of
    the same-named block in a child template.::

        <!-- base.html -->
        <title>{% block title %}Default title{% end %}</title>

        <!-- mypage.html -->
        {% extends "base.html" %}
        {% block title %}My page title{% end %}

``{% comment ... %}``
    A comment which will be removed from the template output.  Note that
    there is no ``{% end %}`` tag; the comment goes from the word ``comment``
    to the closing ``%}`` tag.

``{% extends *filename* %}``
    Inherit from another template.  Templates that use ``extends`` should
    contain one or more ``block`` tags to replace content from the parent
    template.  Anything in the child template not contained in a ``block``
    tag will be ignored.  For an example, see the ``{% block %}`` tag.

``{% for *var* in *expr* %}...{% end %}``
    Same as the python ``for`` statement.  ``{% break %}`` and
    ``{% continue %}`` may be used inside the loop.

``{% from *x* import *y* %}``
    Same as the python ``import`` statement.

``{% if *condition* %}...{% elif *condition* %}...{% else %}...{% end %}``
    Conditional statement - outputs the first section whose condition is
    true.  (The ``elif`` and ``else`` sections are optional)

``{% import *module* %}``
    Same as the python ``import`` statement.

``{% include *filename* %}``
    Includes another template file.  The included file can see all the local
    variables as if it were copied directly to the point of the ``include``
    directive (the ``{% autoescape %}`` directive is an exception).
    Alternately, ``{% module Template(filename, **kwargs) %}`` may be used
    to include another template with an isolated namespace.

``{% module *expr* %}``
    Renders a `~tornado.web.UIModule`.  The output of the ``UIModule`` is
    not escaped::

        {% module Template("foo.html", arg=42) %}

    ``UIModules`` are a feature of the `tornado.web.RequestHandler`
    class (and specifically its ``render`` method) and will not work
    when the template system is used on its own in other contexts.

``{% raw *expr* %}``
    Outputs the result of the given expression without autoescaping.

``{% set *x* = *y* %}``
    Sets a local variable.

``{% try %}...{% except %}...{% else %}...{% finally %}...{% end %}``
    Same as the python ``try`` statement.

``{% while *condition* %}... {% end %}``
    Same as the python ``while`` statement.  ``{% break %}`` and
    ``{% continue %}`` may be used inside the loop.

``{% whitespace *mode* %}``
    Sets the whitespace mode for the remainder of the current file
    (or until the next ``{% whitespace %}`` directive). See
    `filter_whitespace` for available options. New in Tornado 4.3.
"""

import datetime
from io import StringIO
import linecache
import os.path
import posixpath
import re
import threading

from tornado import escape
from tornado.log import app_log
from tornado.util import ObjectDict, exec_in, unicode_type

from typing import Any, Union, Callable, List, Dict, Iterable, Optional, TextIO
import typing

if typing.TYPE_CHECKING:
    from typing import Tuple, ContextManager  # noqa: F401

_DEFAULT_AUTOESCAPE = "xhtml_escape"


class _UnsetMarker:
    pass


_UNSET = _UnsetMarker()


def filter_whitespace(mode: str, text: str) -> str:
    """Transform whitespace in ``text`` according to ``mode``.

    Available modes are:

    * ``all``: Return all whitespace unmodified.
    * ``single``: Collapse consecutive whitespace with a single whitespace
      character, preserving newlines.
    * ``oneline``: Collapse all runs of whitespace into a single space
      character, removing all newlines in the process.

    .. versionadded:: 4.3
    """
    if mode == "all":
        return text
    elif mode == "single":
        text = re.sub(r"([\t ]+)", " ", text)
        text = re.sub(r"(\s*\n\s*)", "\n", text)
        return text
    elif mode == "oneline":
        return re.sub(r"(\s+)", " ", text)
    else:
        raise Exception("invalid whitespace mode %s" % mode)


class Template:
    """A compiled template.

    We compile into Python from the given template_string. You can generate
    the template from variables with generate().
    """

    # note that the constructor's signature is not extracted with
    # autodoc because _UNSET looks like garbage.  When changing
    # this signature update website/sphinx/template.rst too.
    def __init__(
        self,
        template_string: Union[str, bytes],
        name: str = "<string>",
        loader: Optional["BaseLoader"] = None,
        compress_whitespace: Union[bool, _UnsetMarker] = _UNSET,
        autoescape: Optional[Union[str, _UnsetMarker]] = _UNSET,
        whitespace: Optional[str] = None,
    ) -> None:
        """Construct a Template.

        :arg str template_string: the contents of the template file.
        :arg str name: the filename from which the template was loaded
            (used for error message).
        :arg tornado.template.BaseLoader loader: the `~tornado.template.BaseLoader` responsible
            for this template, used to resolve ``{% include %}`` and ``{% extend %}`` directives.
        :arg bool compress_whitespace: Deprecated since Tornado 4.3.
            Equivalent to ``whitespace="single"`` if true and
            ``whitespace="all"`` if false.
        :arg str autoescape: The name of a function in the template
            namespace, or ``None`` to disable escaping by default.
        :arg str whitespace: A string specifying treatment of whitespace;
            see `filter_whitespace` for options.

        .. versionchanged:: 4.3
           Added ``whitespace`` parameter; deprecated ``compress_whitespace``.
        """
        self.name = escape.native_str(name)

        if compress_whitespace is not _UNSET:
            # Convert deprecated compress_whitespace (bool) to whitespace (str).
            if whitespace is not None:
                raise Exception("cannot set both whitespace and compress_whitespace")
            whitespace = "single" if compress_whitespace else "all"
        if whitespace is None:
            if loader and loader.whitespace:
                whitespace = loader.whitespace
            else:
                # Whitespace defaults by filename.
                if name.endswith(".html") or name.endswith(".js"):
                    whitespace = "single"
                else:
                    whitespace = "all"
        # Validate the whitespace setting.
        assert whitespace is not None
        filter_whitespace(whitespace, "")

        if not isinstance(autoescape, _UnsetMarker):
            self.autoescape = autoescape  # type: Optional[str]
        elif loader:
            self.autoescape = loader.autoescape
        else:
            self.autoescape = _DEFAULT_AUTOESCAPE

        self.namespace = loader.namespace if loader else {}
        reader = _TemplateReader(name, escape.native_str(template_string), whitespace)
        self.file = _File(self, _parse(reader, self))
        self.code = self._generate_python(loader)
        self.loader = loader
        try:
            # Under python2.5, the fake filename used here must match
            # the module name used in __name__ below.
            # The dont_inherit flag prevents template.py's future imports
            # from being applied to the generated code.
            self.compiled = compile(
                escape.to_unicode(self.code),
                "%s.generated.py" % self.name.replace(".", "_"),
                "exec",
                dont_inherit=True,
            )
        except Exception:
            formatted_code = _format_code(self.code).rstrip()
            app_log.error("%s code:\n%s", self.name, formatted_code)
            raise

    def generate(self, **kwargs: Any) -> bytes:
        """Generate this template with the given arguments."""
        namespace = {
            "escape": escape.xhtml_escape,
            "xhtml_escape": escape.xhtml_escape,
            "url_escape": escape.url_escape,
            "json_encode": escape.json_encode,
            "squeeze": escape.squeeze,
            "linkify": escape.linkify,
            "datetime": datetime,
            "_tt_utf8": escape.utf8,  # for internal use
            "_tt_string_types": (unicode_type, bytes),
            # __name__ and __loader__ allow the traceback mechanism to find
            # the generated source code.
            "__name__": self.name.replace(".", "_"),
            "__loader__": ObjectDict(get_source=lambda name: self.code),
        }
        namespace.update(self.namespace)
        namespace.update(kwargs)
        exec_in(self.compiled, namespace)
        execute = typing.cast(Callable[[], bytes], namespace["_tt_execute"])
        # Clear the traceback module's cache of source data now that
        # we've generated a new template (mainly for this module's
        # unittests, where different tests reuse the same name).
        linecache.clearcache()
        return execute()

    def _generate_python(self, loader: Optional["BaseLoader"]) -> str:
        buffer = StringIO()
        try:
            # named_blocks maps from names to _NamedBlock objects
            named_blocks = {}  # type: Dict[str, _NamedBlock]
            ancestors = self._get_ancestors(loader)
            ancestors.reverse()
            for ancestor in ancestors:
                ancestor.find_named_blocks(loader, named_blocks)
            writer = _CodeWriter(buffer, named_blocks, loader, ancestors[0].template)
            ancestors[0].generate(writer)
            return buffer.getvalue()
        finally:
            buffer.close()

    def _get_ancestors(self, loader: Optional["BaseLoader"]) -> List["_File"]:
        ancestors = [self.file]
        for chunk in self.file.body.chunks:
            if isinstance(chunk, _ExtendsBlock):
                if not loader:
                    raise ParseError(
                        "{% extends %} block found, but no " "template loader"
                    )
                template = loader.load(chunk.name, self.name)
                ancestors.extend(template._get_ancestors(loader))
        return ancestors


class BaseLoader:
    """Base class for template loaders.

    You must use a template loader to use template constructs like
    ``{% extends %}`` and ``{% include %}``. The loader caches all
    templates after they are loaded the first time.
    """

    def __init__(
        self,
        autoescape: Optional[str] = _DEFAULT_AUTOESCAPE,
        namespace: Optional[Dict[str, Any]] = None,
        whitespace: Optional[str] = None,
    ) -> None:
        """Construct a template loader.

        :arg str autoescape: The name of a function in the template
            namespace, such as "xhtml_escape", or ``None`` to disable
            autoescaping by default.
        :arg dict namespace: A dictionary to be added to the default template
            namespace, or ``None``.
        :arg str whitespace: A string specifying default behavior for
            whitespace in templates; see `filter_whitespace` for options.
            Default is "single" for files ending in ".html" and ".js" and
            "all" for other files.

        .. versionchanged:: 4.3
           Added ``whitespace`` parameter.
        """
        self.autoescape = autoescape
        self.namespace = namespace or {}
        self.whitespace = whitespace
        self.templates = {}  # type: Dict[str, Template]
        # self.lock protects self.templates.  It's a reentrant lock
        # because templates may load other templates via `include` or
        # `extends`.  Note that thanks to the GIL this code would be safe
        # even without the lock, but could lead to wasted work as multiple
        # threads tried to compile the same template simultaneously.
        self.lock = threading.RLock()

    def reset(self) -> None:
        """Resets the cache of compiled templates."""
        with self.lock:
            self.templates = {}

    def resolve_path(self, name: str, parent_path: Optional[str] = None) -> str:
        """Converts a possibly-relative path to absolute (used internally)."""
        raise NotImplementedError()

    def load(self, name: str, parent_path: Optional[str] = None) -> Template:
        """Loads a template."""
        name = self.resolve_path(name, parent_path=parent_path)
        with self.lock:
            if name not in self.templates:
                self.templates[name] = self._create_template(name)
            return self.templates[name]

    def _create_template(self, name: str) -> Template:
        raise NotImplementedError()


class Loader(BaseLoader):
    """A template loader that loads from a single root directory."""

    def __init__(self, root_directory: str, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.root = os.path.abspath(root_directory)

    def resolve_path(self, name: str, parent_path: Optional[str] = None) -> str:
        if (
            parent_path
            and not parent_path.startswith("<")
            and not parent_path.startswith("/")
            and not name.startswith("/")
        ):
            current_path = os.path.join(self.root, parent_path)
            file_dir = os.path.dirname(os.path.abspath(current_path))
            relative_path = os.path.abspath(os.path.join(file_dir, name))
            if relative_path.startswith(self.root):
                name = relative_path[len(self.root) + 1 :]
        return name

    def _create_template(self, name: str) -> Template:
        path = os.path.join(self.root, name)
        with open(path, "rb") as f:
            template = Template(f.read(), name=name, loader=self)
            return template


class DictLoader(BaseLoader):
    """A template loader that loads from a dictionary."""

    def __init__(self, dict: Dict[str, str], **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.dict = dict

    def resolve_path(self, name: str, parent_path: Optional[str] = None) -> str:
        if (
            parent_path
            and not parent_path.startswith("<")
            and not parent_path.startswith("/")
            and not name.startswith("/")
        ):
            file_dir = posixpath.dirname(parent_path)
            name = posixpath.normpath(posixpath.join(file_dir, name))
        return name

    def _create_template(self, name: str) -> Template:
        return Template(self.dict[name], name=name, loader=self)


class _Node:
    def each_child(self) -> Iterable["_Node"]:
        return ()

    def generate(self, writer: "_CodeWriter") -> None:
        raise NotImplementedError()

    def find_named_blocks(
        self, loader: Optional[BaseLoader], named_blocks: Dict[str, "_NamedBlock"]
    ) -> None:
        for child in self.each_child():
            child.find_named_blocks(loader, named_blocks)


class _File(_Node):
    def __init__(self, template: Template, body: "_ChunkList") -> None:
        self.template = template
        self.body = body
        self.line = 0

    def generate(self, writer: "_CodeWriter") -> None:
        writer.write_line("def _tt_execute():", self.line)
        with writer.indent():
            writer.write_line("_tt_buffer = []", self.line)
            writer.write_line("_tt_append = _tt_buffer.append", self.line)
            self.body.generate(writer)
            writer.write_line("return _tt_utf8('').join(_tt_buffer)", self.line)

    def each_child(self) -> Iterable["_Node"]:
        return (self.body,)


class _ChunkList(_Node):
    def __init__(self, chunks: List[_Node]) -> None:
        self.chunks = chunks

    def generate(self, writer: "_CodeWriter") -> None:
        for chunk in self.chunks:
            chunk.generate(writer)

    def each_child(self) -> Iterable["_Node"]:
        return self.chunks


class _NamedBlock(_Node):
    def __init__(self, name: str, body: _Node, template: Template, line: int) -> None:
        self.name = name
        self.body = body
        self.template = template
        self.line = line

    def each_child(self) -> Iterable["_Node"]:
        return (self.body,)

    def generate(self, writer: "_CodeWriter") -> None:
        block = writer.named_blocks[self.name]
        with writer.include(block.template, self.line):
            block.body.generate(writer)

    def find_named_blocks(
        self, loader: Optional[BaseLoader], named_blocks: Dict[str, "_NamedBlock"]
    ) -> None:
        named_blocks[self.name] = self
        _Node.find_named_blocks(self, loader, named_blocks)


class _ExtendsBlock(_Node):
    def __init__(self, name: str) -> None:
        self.name = name


class _IncludeBlock(_Node):
    def __init__(self, name: str, reader: "_TemplateReader", line: int) -> None:
        self.name = name
        self.template_name = reader.name
        self.line = line

    def find_named_blocks(
        self, loader: Optional[BaseLoader], named_blocks: Dict[str, _NamedBlock]
    ) -> None:
        assert loader is not None
        included = loader.load(self.name, self.template_name)
        included.file.find_named_blocks(loader, named_blocks)

    def generate(self, writer: "_CodeWriter") -> None:
        assert writer.loader is not None
        included = writer.loader.load(self.name, self.template_name)
        with writer.include(included, self.line):
            included.file.body.generate(writer)


class _ApplyBlock(_Node):
    def __init__(self, method: str, line: int, body: _Node) -> None:
        self.method = method
        self.line = line
        self.body = body

    def each_child(self) -> Iterable["_Node"]:
        return (self.body,)

    def generate(self, writer: "_CodeWriter") -> None:
        method_name = "_tt_apply%d" % writer.apply_counter
        writer.apply_counter += 1
        writer.write_line("def %s():" % method_name, self.line)
        with writer.indent():
            writer.write_line("_tt_buffer = []", self.line)
            writer.write_line("_tt_append = _tt_buffer.append", self.line)
            self.body.generate(writer)
            writer.write_line("return _tt_utf8('').join(_tt_buffer)", self.line)
        writer.write_line(
            f"_tt_append(_tt_utf8({self.method}({method_name}())))", self.line
        )


class _ControlBlock(_Node):
    def __init__(self, statement: str, line: int, body: _Node) -> None:
        self.statement = statement
        self.line = line
        self.body = body

    def each_child(self) -> Iterable[_Node]:
        return (self.body,)

    def generate(self, writer: "_CodeWriter") -> None:
        writer.write_line("%s:" % self.statement, self.line)
        with writer.indent():
            self.body.generate(writer)
            # Just in case the body was empty
            writer.write_line("pass", self.line)


class _IntermediateControlBlock(_Node):
    def __init__(self, statement: str, line: int) -> None:
        self.statement = statement
        self.line = line

    def generate(self, writer: "_CodeWriter") -> None:
        # In case the previous block was empty
        writer.write_line("pass", self.line)
        writer.write_line("%s:" % self.statement, self.line, writer.indent_size() - 1)


class _Statement(_Node):
    def __init__(self, statement: str, line: int) -> None:
        self.statement = statement
        self.line = line

    def generate(self, writer: "_CodeWriter") -> None:
        writer.write_line(self.statement, self.line)


class _Expression(_Node):
    def __init__(self, expression: str, line: int, raw: bool = False) -> None:
        self.expression = expression
        self.line = line
        self.raw = raw

    def generate(self, writer: "_CodeWriter") -> None:
        writer.write_line("_tt_tmp = %s" % self.expression, self.line)
        writer.write_line(
            "if isinstance(_tt_tmp, _tt_string_types):" " _tt_tmp = _tt_utf8(_tt_tmp)",
            self.line,
        )
        writer.write_line("else: _tt_tmp = _tt_utf8(str(_tt_tmp))", self.line)
        if not self.raw and writer.current_template.autoescape is not None:
            # In python3 functions like xhtml_escape return unicode,
            # so we have to convert to utf8 again.
            writer.write_line(
                "_tt_tmp = _tt_utf8(%s(_tt_tmp))" % writer.current_template.autoescape,
                self.line,
            )
        writer.write_line("_tt_append(_tt_tmp)", self.line)


class _Module(_Expression):
    def __init__(self, expression: str, line: int) -> None:
        super().__init__("_tt_modules." + expression, line, raw=True)


class _Text(_Node):
    def __init__(self, value: str, line: int, whitespace: str) -> None:
        self.value = value
        self.line = line
        self.whitespace = whitespace

    def generate(self, writer: "_CodeWriter") -> None:
        value = self.value

        # Compress whitespace if requested, with a crude heuristic to avoid
        # altering preformatted whitespace.
        if "<pre>" not in value:
            value = filter_whitespace(self.whitespace, value)

        if value:
            writer.write_line("_tt_append(%r)" % escape.utf8(value), self.line)


class ParseError(Exception):
    """Raised for template syntax errors.

    ``ParseError`` instances have ``filename`` and ``lineno`` attributes
    indicating the position of the error.

    .. versionchanged:: 4.3
       Added ``filename`` and ``lineno`` attributes.
    """

    def __init__(
        self, message: str, filename: Optional[str] = None, lineno: int = 0
    ) -> None:
        self.message = message
        # The names "filename" and "lineno" are chosen for consistency
        # with python SyntaxError.
        self.filename = filename
        self.lineno = lineno

    def __str__(self) -> str:
        return "%s at %s:%d" % (self.message, self.filename, self.lineno)


class _CodeWriter:
    def __init__(
        self,
        file: TextIO,
        named_blocks: Dict[str, _NamedBlock],
        loader: Optional[BaseLoader],
        current_template: Template,
    ) -> None:
        self.file = file
        self.named_blocks = named_blocks
        self.loader = loader
        self.current_template = current_template
        self.apply_counter = 0
        self.include_stack = []  # type: List[Tuple[Template, int]]
        self._indent = 0

    def indent_size(self) -> int:
        return self._indent

    def indent(self) -> "ContextManager":
        class Indenter:
            def __enter__(_) -> "_CodeWriter":
                self._indent += 1
                return self

            def __exit__(_, *args: Any) -> None:
                assert self._indent > 0
                self._indent -= 1

        return Indenter()

    def include(self, template: Template, line: int) -> "ContextManager":
        self.include_stack.append((self.current_template, line))
        self.current_template = template

        class IncludeTemplate:
            def __enter__(_) -> "_CodeWriter":
                return self

            def __exit__(_, *args: Any) -> None:
                self.current_template = self.include_stack.pop()[0]

        return IncludeTemplate()

    def write_line(
        self, line: str, line_number: int, indent: Optional[int] = None
    ) -> None:
        if indent is None:
            indent = self._indent
        line_comment = "  # %s:%d" % (self.current_template.name, line_number)
        if self.include_stack:
            ancestors = [
                "%s:%d" % (tmpl.name, lineno) for (tmpl, lineno) in self.include_stack
            ]
            line_comment += " (via %s)" % ", ".join(reversed(ancestors))
        print("    " * indent + line + line_comment, file=self.file)


class _TemplateReader:
    def __init__(self, name: str, text: str, whitespace: str) -> None:
        self.name = name
        self.text = text
        self.whitespace = whitespace
        self.line = 1
        self.pos = 0

    def find(self, needle: str, start: int = 0, end: Optional[int] = None) -> int:
        assert start >= 0, start
        pos = self.pos
        start += pos
        if end is None:
            index = self.text.find(needle, start)
        else:
            end += pos
            assert end >= start
            index = self.text.find(needle, start, end)
        if index != -1:
            index -= pos
        return index

    def consume(self, count: Optional[int] = None) -> str:
        if count is None:
            count = len(self.text) - self.pos
        newpos = self.pos + count
        self.line += self.text.count("\n", self.pos, newpos)
        s = self.text[self.pos : newpos]
        self.pos = newpos
        return s

    def remaining(self) -> int:
        return len(self.text) - self.pos

    def __len__(self) -> int:
        return self.remaining()

    def __getitem__(self, key: Union[int, slice]) -> str:
        if isinstance(key, slice):
            size = len(self)
            start, stop, step = key.indices(size)
            if start is None:
                start = self.pos
            else:
                start += self.pos
            if stop is not None:
                stop += self.pos
            return self.text[slice(start, stop, step)]
        elif key < 0:
            return self.text[key]
        else:
            return self.text[self.pos + key]

    def __str__(self) -> str:
        return self.text[self.pos :]

    def raise_parse_error(self, msg: str) -> None:
        raise ParseError(msg, self.name, self.line)


def _format_code(code: str) -> str:
    lines = code.splitlines()
    format = "%%%dd  %%s\n" % len(repr(len(lines) + 1))
    return "".join([format % (i + 1, line) for (i, line) in enumerate(lines)])


def _parse(
    reader: _TemplateReader,
    template: Template,
    in_block: Optional[str] = None,
    in_loop: Optional[str] = None,
) -> _ChunkList:
    body = _ChunkList([])
    while True:
        # Find next template directive
        curly = 0
        while True:
            curly = reader.find("{", curly)
            if curly == -1 or curly + 1 == reader.remaining():
                # EOF
                if in_block:
                    reader.raise_parse_error(
                        "Missing {%% end %%} block for %s" % in_block
                    )
                body.chunks.append(
                    _Text(reader.consume(), reader.line, reader.whitespace)
                )
                return body
            # If the first curly brace is not the start of a special token,
            # start searching from the character after it
            if reader[curly + 1] not in ("{", "%", "#"):
                curly += 1
                continue
            # When there are more than 2 curlies in a row, use the
            # innermost ones.  This is useful when generating languages
            # like latex where curlies are also meaningful
            if (
                curly + 2 < reader.remaining()
                and reader[curly + 1] == "{"
                and reader[curly + 2] == "{"
            ):
                curly += 1
                continue
            break

        # Append any text before the special token
        if curly > 0:
            cons = reader.consume(curly)
            body.chunks.append(_Text(cons, reader.line, reader.whitespace))

        start_brace = reader.consume(2)
        line = reader.line

        # Template directives may be escaped as "{{!" or "{%!".
        # In this case output the braces and consume the "!".
        # This is especially useful in conjunction with jquery templates,
        # which also use double braces.
        if reader.remaining() and reader[0] == "!":
            reader.consume(1)
            body.chunks.append(_Text(start_brace, line, reader.whitespace))
            continue

        # Comment
        if start_brace == "{#":
            end = reader.find("#}")
            if end == -1:
                reader.raise_parse_error("Missing end comment #}")
            contents = reader.consume(end).strip()
            reader.consume(2)
            continue

        # Expression
        if start_brace == "{{":
            end = reader.find("}}")
            if end == -1:
                reader.raise_parse_error("Missing end expression }}")
            contents = reader.consume(end).strip()
            reader.consume(2)
            if not contents:
                reader.raise_parse_error("Empty expression")
            body.chunks.append(_Expression(contents, line))
            continue

        # Block
        assert start_brace == "{%", start_brace
        end = reader.find("%}")
        if end == -1:
            reader.raise_parse_error("Missing end block %}")
        contents = reader.consume(end).strip()
        reader.consume(2)
        if not contents:
            reader.raise_parse_error("Empty block tag ({% %})")

        operator, space, suffix = contents.partition(" ")
        suffix = suffix.strip()

        # Intermediate ("else", "elif", etc) blocks
        intermediate_blocks = {
            "else": {"if", "for", "while", "try"},
            "elif": {"if"},
            "except": {"try"},
            "finally": {"try"},
        }
        allowed_parents = intermediate_blocks.get(operator)
        if allowed_parents is not None:
            if not in_block:
                reader.raise_parse_error(f"{operator} outside {allowed_parents} block")
            if in_block not in allowed_parents:
                reader.raise_parse_error(
                    f"{operator} block cannot be attached to {in_block} block"
                )
            body.chunks.append(_IntermediateControlBlock(contents, line))
            continue

        # End tag
        elif operator == "end":
            if not in_block:
                reader.raise_parse_error("Extra {% end %} block")
            return body

        elif operator in (
            "extends",
            "include",
            "set",
            "import",
            "from",
            "comment",
            "autoescape",
            "whitespace",
            "raw",
            "module",
        ):
            if operator == "comment":
                continue
            if operator == "extends":
                suffix = suffix.strip('"').strip("'")
                if not suffix:
                    reader.raise_parse_error("extends missing file path")
                block = _ExtendsBlock(suffix)  # type: _Node
            elif operator in ("import", "from"):
                if not suffix:
                    reader.raise_parse_error("import missing statement")
                block = _Statement(contents, line)
            elif operator == "include":
                suffix = suffix.strip('"').strip("'")
                if not suffix:
                    reader.raise_parse_error("include missing file path")
                block = _IncludeBlock(suffix, reader, line)
            elif operator == "set":
                if not suffix:
                    reader.raise_parse_error("set missing statement")
                block = _Statement(suffix, line)
            elif operator == "autoescape":
                fn = suffix.strip()  # type: Optional[str]
                if fn == "None":
                    fn = None
                template.autoescape = fn
                continue
            elif operator == "whitespace":
                mode = suffix.strip()
                # Validate the selected mode
                filter_whitespace(mode, "")
                reader.whitespace = mode
                continue
            elif operator == "raw":
                block = _Expression(suffix, line, raw=True)
            elif operator == "module":
                block = _Module(suffix, line)
            body.chunks.append(block)
            continue

        elif operator in ("apply", "block", "try", "if", "for", "while"):
            # parse inner body recursively
            if operator in ("for", "while"):
                block_body = _parse(reader, template, operator, operator)
            elif operator == "apply":
                # apply creates a nested function so syntactically it's not
                # in the loop.
                block_body = _parse(reader, template, operator, None)
            else:
                block_body = _parse(reader, template, operator, in_loop)

            if operator == "apply":
                if not suffix:
                    reader.raise_parse_error("apply missing method name")
                block = _ApplyBlock(suffix, line, block_body)
            elif operator == "block":
                if not suffix:
                    reader.raise_parse_error("block missing name")
                block = _NamedBlock(suffix, block_body, template, line)
            else:
                block = _ControlBlock(contents, line, block_body)
            body.chunks.append(block)
            continue

        elif operator in ("break", "continue"):
            if not in_loop:
                reader.raise_parse_error(
                    "{} outside {} block".format(operator, {"for", "while"})
                )
            body.chunks.append(_Statement(contents, line))
            continue

        else:
            reader.raise_parse_error("unknown operator: %r" % operator)

# === NexusCore/openenv\Lib\site-packages\urllib3\connection.py ===
from __future__ import annotations

import datetime
import http.client
import logging
import os
import re
import socket
import sys
import threading
import typing
import warnings
from http.client import HTTPConnection as _HTTPConnection
from http.client import HTTPException as HTTPException  # noqa: F401
from http.client import ResponseNotReady
from socket import timeout as SocketTimeout

if typing.TYPE_CHECKING:
    from .response import HTTPResponse
    from .util.ssl_ import _TYPE_PEER_CERT_RET_DICT
    from .util.ssltransport import SSLTransport

from ._collections import HTTPHeaderDict
from .http2 import probe as http2_probe
from .util.response import assert_header_parsing
from .util.timeout import _DEFAULT_TIMEOUT, _TYPE_TIMEOUT, Timeout
from .util.util import to_str
from .util.wait import wait_for_read

try:  # Compiled with SSL?
    import ssl

    BaseSSLError = ssl.SSLError
except (ImportError, AttributeError):
    ssl = None  # type: ignore[assignment]

    class BaseSSLError(BaseException):  # type: ignore[no-redef]
        pass


from ._base_connection import _TYPE_BODY
from ._base_connection import ProxyConfig as ProxyConfig
from ._base_connection import _ResponseOptions as _ResponseOptions
from ._version import __version__
from .exceptions import (
    ConnectTimeoutError,
    HeaderParsingError,
    NameResolutionError,
    NewConnectionError,
    ProxyError,
    SystemTimeWarning,
)
from .util import SKIP_HEADER, SKIPPABLE_HEADERS, connection, ssl_
from .util.request import body_to_chunks
from .util.ssl_ import assert_fingerprint as _assert_fingerprint
from .util.ssl_ import (
    create_urllib3_context,
    is_ipaddress,
    resolve_cert_reqs,
    resolve_ssl_version,
    ssl_wrap_socket,
)
from .util.ssl_match_hostname import CertificateError, match_hostname
from .util.url import Url

# Not a no-op, we're adding this to the namespace so it can be imported.
ConnectionError = ConnectionError
BrokenPipeError = BrokenPipeError


log = logging.getLogger(__name__)

port_by_scheme = {"http": 80, "https": 443}

# When it comes time to update this value as a part of regular maintenance
# (ie test_recent_date is failing) update it to ~6 months before the current date.
RECENT_DATE = datetime.date(2023, 6, 1)

_CONTAINS_CONTROL_CHAR_RE = re.compile(r"[^-!#$%&'*+.^_`|~0-9a-zA-Z]")


class HTTPConnection(_HTTPConnection):
    """
    Based on :class:`http.client.HTTPConnection` but provides an extra constructor
    backwards-compatibility layer between older and newer Pythons.

    Additional keyword parameters are used to configure attributes of the connection.
    Accepted parameters include:

    - ``source_address``: Set the source address for the current connection.
    - ``socket_options``: Set specific options on the underlying socket. If not specified, then
      defaults are loaded from ``HTTPConnection.default_socket_options`` which includes disabling
      Nagle's algorithm (sets TCP_NODELAY to 1) unless the connection is behind a proxy.

      For example, if you wish to enable TCP Keep Alive in addition to the defaults,
      you might pass:

      .. code-block:: python

         HTTPConnection.default_socket_options + [
             (socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1),
         ]

      Or you may want to disable the defaults by passing an empty list (e.g., ``[]``).
    """

    default_port: typing.ClassVar[int] = port_by_scheme["http"]  # type: ignore[misc]

    #: Disable Nagle's algorithm by default.
    #: ``[(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)]``
    default_socket_options: typing.ClassVar[connection._TYPE_SOCKET_OPTIONS] = [
        (socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
    ]

    #: Whether this connection verifies the host's certificate.
    is_verified: bool = False

    #: Whether this proxy connection verified the proxy host's certificate.
    # If no proxy is currently connected to the value will be ``None``.
    proxy_is_verified: bool | None = None

    blocksize: int
    source_address: tuple[str, int] | None
    socket_options: connection._TYPE_SOCKET_OPTIONS | None

    _has_connected_to_proxy: bool
    _response_options: _ResponseOptions | None
    _tunnel_host: str | None
    _tunnel_port: int | None
    _tunnel_scheme: str | None

    def __init__(
        self,
        host: str,
        port: int | None = None,
        *,
        timeout: _TYPE_TIMEOUT = _DEFAULT_TIMEOUT,
        source_address: tuple[str, int] | None = None,
        blocksize: int = 16384,
        socket_options: None | (
            connection._TYPE_SOCKET_OPTIONS
        ) = default_socket_options,
        proxy: Url | None = None,
        proxy_config: ProxyConfig | None = None,
    ) -> None:
        super().__init__(
            host=host,
            port=port,
            timeout=Timeout.resolve_default_timeout(timeout),
            source_address=source_address,
            blocksize=blocksize,
        )
        self.socket_options = socket_options
        self.proxy = proxy
        self.proxy_config = proxy_config

        self._has_connected_to_proxy = False
        self._response_options = None
        self._tunnel_host: str | None = None
        self._tunnel_port: int | None = None
        self._tunnel_scheme: str | None = None

    @property
    def host(self) -> str:
        """
        Getter method to remove any trailing dots that indicate the hostname is an FQDN.

        In general, SSL certificates don't include the trailing dot indicating a
        fully-qualified domain name, and thus, they don't validate properly when
        checked against a domain name that includes the dot. In addition, some
        servers may not expect to receive the trailing dot when provided.

        However, the hostname with trailing dot is critical to DNS resolution; doing a
        lookup with the trailing dot will properly only resolve the appropriate FQDN,
        whereas a lookup without a trailing dot will search the system's search domain
        list. Thus, it's important to keep the original host around for use only in
        those cases where it's appropriate (i.e., when doing DNS lookup to establish the
        actual TCP connection across which we're going to send HTTP requests).
        """
        return self._dns_host.rstrip(".")

    @host.setter
    def host(self, value: str) -> None:
        """
        Setter for the `host` property.

        We assume that only urllib3 uses the _dns_host attribute; httplib itself
        only uses `host`, and it seems reasonable that other libraries follow suit.
        """
        self._dns_host = value

    def _new_conn(self) -> socket.socket:
        """Establish a socket connection and set nodelay settings on it.

        :return: New socket connection.
        """
        try:
            sock = connection.create_connection(
                (self._dns_host, self.port),
                self.timeout,
                source_address=self.source_address,
                socket_options=self.socket_options,
            )
        except socket.gaierror as e:
            raise NameResolutionError(self.host, self, e) from e
        except SocketTimeout as e:
            raise ConnectTimeoutError(
                self,
                f"Connection to {self.host} timed out. (connect timeout={self.timeout})",
            ) from e

        except OSError as e:
            raise NewConnectionError(
                self, f"Failed to establish a new connection: {e}"
            ) from e

        sys.audit("http.client.connect", self, self.host, self.port)

        return sock

    def set_tunnel(
        self,
        host: str,
        port: int | None = None,
        headers: typing.Mapping[str, str] | None = None,
        scheme: str = "http",
    ) -> None:
        if scheme not in ("http", "https"):
            raise ValueError(
                f"Invalid proxy scheme for tunneling: {scheme!r}, must be either 'http' or 'https'"
            )
        super().set_tunnel(host, port=port, headers=headers)
        self._tunnel_scheme = scheme

    if sys.version_info < (3, 11, 4):

        def _tunnel(self) -> None:
            _MAXLINE = http.client._MAXLINE  # type: ignore[attr-defined]
            connect = b"CONNECT %s:%d HTTP/1.0\r\n" % (  # type: ignore[str-format]
                self._tunnel_host.encode("ascii"),  # type: ignore[union-attr]
                self._tunnel_port,
            )
            headers = [connect]
            for header, value in self._tunnel_headers.items():  # type: ignore[attr-defined]
                headers.append(f"{header}: {value}\r\n".encode("latin-1"))
            headers.append(b"\r\n")
            # Making a single send() call instead of one per line encourages
            # the host OS to use a more optimal packet size instead of
            # potentially emitting a series of small packets.
            self.send(b"".join(headers))
            del headers

            response = self.response_class(self.sock, method=self._method)  # type: ignore[attr-defined]
            try:
                (version, code, message) = response._read_status()  # type: ignore[attr-defined]

                if code != http.HTTPStatus.OK:
                    self.close()
                    raise OSError(f"Tunnel connection failed: {code} {message.strip()}")
                while True:
                    line = response.fp.readline(_MAXLINE + 1)
                    if len(line) > _MAXLINE:
                        raise http.client.LineTooLong("header line")
                    if not line:
                        # for sites which EOF without sending a trailer
                        break
                    if line in (b"\r\n", b"\n", b""):
                        break

                    if self.debuglevel > 0:
                        print("header:", line.decode())
            finally:
                response.close()

    def connect(self) -> None:
        self.sock = self._new_conn()
        if self._tunnel_host:
            # If we're tunneling it means we're connected to our proxy.
            self._has_connected_to_proxy = True

            # TODO: Fix tunnel so it doesn't depend on self.sock state.
            self._tunnel()

        # If there's a proxy to be connected to we are fully connected.
        # This is set twice (once above and here) due to forwarding proxies
        # not using tunnelling.
        self._has_connected_to_proxy = bool(self.proxy)

        if self._has_connected_to_proxy:
            self.proxy_is_verified = False

    @property
    def is_closed(self) -> bool:
        return self.sock is None

    @property
    def is_connected(self) -> bool:
        if self.sock is None:
            return False
        return not wait_for_read(self.sock, timeout=0.0)

    @property
    def has_connected_to_proxy(self) -> bool:
        return self._has_connected_to_proxy

    @property
    def proxy_is_forwarding(self) -> bool:
        """
        Return True if a forwarding proxy is configured, else return False
        """
        return bool(self.proxy) and self._tunnel_host is None

    @property
    def proxy_is_tunneling(self) -> bool:
        """
        Return True if a tunneling proxy is configured, else return False
        """
        return self._tunnel_host is not None

    def close(self) -> None:
        try:
            super().close()
        finally:
            # Reset all stateful properties so connection
            # can be re-used without leaking prior configs.
            self.sock = None
            self.is_verified = False
            self.proxy_is_verified = None
            self._has_connected_to_proxy = False
            self._response_options = None
            self._tunnel_host = None
            self._tunnel_port = None
            self._tunnel_scheme = None

    def putrequest(
        self,
        method: str,
        url: str,
        skip_host: bool = False,
        skip_accept_encoding: bool = False,
    ) -> None:
        """"""
        # Empty docstring because the indentation of CPython's implementation
        # is broken but we don't want this method in our documentation.
        match = _CONTAINS_CONTROL_CHAR_RE.search(method)
        if match:
            raise ValueError(
                f"Method cannot contain non-token characters {method!r} (found at least {match.group()!r})"
            )

        return super().putrequest(
            method, url, skip_host=skip_host, skip_accept_encoding=skip_accept_encoding
        )

    def putheader(self, header: str, *values: str) -> None:  # type: ignore[override]
        """"""
        if not any(isinstance(v, str) and v == SKIP_HEADER for v in values):
            super().putheader(header, *values)
        elif to_str(header.lower()) not in SKIPPABLE_HEADERS:
            skippable_headers = "', '".join(
                [str.title(header) for header in sorted(SKIPPABLE_HEADERS)]
            )
            raise ValueError(
                f"urllib3.util.SKIP_HEADER only supports '{skippable_headers}'"
            )

    # `request` method's signature intentionally violates LSP.
    # urllib3's API is different from `http.client.HTTPConnection` and the subclassing is only incidental.
    def request(  # type: ignore[override]
        self,
        method: str,
        url: str,
        body: _TYPE_BODY | None = None,
        headers: typing.Mapping[str, str] | None = None,
        *,
        chunked: bool = False,
        preload_content: bool = True,
        decode_content: bool = True,
        enforce_content_length: bool = True,
    ) -> None:
        # Update the inner socket's timeout value to send the request.
        # This only triggers if the connection is re-used.
        if self.sock is not None:
            self.sock.settimeout(self.timeout)

        # Store these values to be fed into the HTTPResponse
        # object later. TODO: Remove this in favor of a real
        # HTTP lifecycle mechanism.

        # We have to store these before we call .request()
        # because sometimes we can still salvage a response
        # off the wire even if we aren't able to completely
        # send the request body.
        self._response_options = _ResponseOptions(
            request_method=method,
            request_url=url,
            preload_content=preload_content,
            decode_content=decode_content,
            enforce_content_length=enforce_content_length,
        )

        if headers is None:
            headers = {}
        header_keys = frozenset(to_str(k.lower()) for k in headers)
        skip_accept_encoding = "accept-encoding" in header_keys
        skip_host = "host" in header_keys
        self.putrequest(
            method, url, skip_accept_encoding=skip_accept_encoding, skip_host=skip_host
        )

        # Transform the body into an iterable of sendall()-able chunks
        # and detect if an explicit Content-Length is doable.
        chunks_and_cl = body_to_chunks(body, method=method, blocksize=self.blocksize)
        chunks = chunks_and_cl.chunks
        content_length = chunks_and_cl.content_length

        # When chunked is explicit set to 'True' we respect that.
        if chunked:
            if "transfer-encoding" not in header_keys:
                self.putheader("Transfer-Encoding", "chunked")
        else:
            # Detect whether a framing mechanism is already in use. If so
            # we respect that value, otherwise we pick chunked vs content-length
            # depending on the type of 'body'.
            if "content-length" in header_keys:
                chunked = False
            elif "transfer-encoding" in header_keys:
                chunked = True

            # Otherwise we go off the recommendation of 'body_to_chunks()'.
            else:
                chunked = False
                if content_length is None:
                    if chunks is not None:
                        chunked = True
                        self.putheader("Transfer-Encoding", "chunked")
                else:
                    self.putheader("Content-Length", str(content_length))

        # Now that framing headers are out of the way we send all the other headers.
        if "user-agent" not in header_keys:
            self.putheader("User-Agent", _get_default_user_agent())
        for header, value in headers.items():
            self.putheader(header, value)
        self.endheaders()

        # If we're given a body we start sending that in chunks.
        if chunks is not None:
            for chunk in chunks:
                # Sending empty chunks isn't allowed for TE: chunked
                # as it indicates the end of the body.
                if not chunk:
                    continue
                if isinstance(chunk, str):
                    chunk = chunk.encode("utf-8")
                if chunked:
                    self.send(b"%x\r\n%b\r\n" % (len(chunk), chunk))
                else:
                    self.send(chunk)

        # Regardless of whether we have a body or not, if we're in
        # chunked mode we want to send an explicit empty chunk.
        if chunked:
            self.send(b"0\r\n\r\n")

    def request_chunked(
        self,
        method: str,
        url: str,
        body: _TYPE_BODY | None = None,
        headers: typing.Mapping[str, str] | None = None,
    ) -> None:
        """
        Alternative to the common request method, which sends the
        body with chunked encoding and not as one block
        """
        warnings.warn(
            "HTTPConnection.request_chunked() is deprecated and will be removed "
            "in urllib3 v2.1.0. Instead use HTTPConnection.request(..., chunked=True).",
            category=DeprecationWarning,
            stacklevel=2,
        )
        self.request(method, url, body=body, headers=headers, chunked=True)

    def getresponse(  # type: ignore[override]
        self,
    ) -> HTTPResponse:
        """
        Get the response from the server.

        If the HTTPConnection is in the correct state, returns an instance of HTTPResponse or of whatever object is returned by the response_class variable.

        If a request has not been sent or if a previous response has not be handled, ResponseNotReady is raised. If the HTTP response indicates that the connection should be closed, then it will be closed before the response is returned. When the connection is closed, the underlying socket is closed.
        """
        # Raise the same error as http.client.HTTPConnection
        if self._response_options is None:
            raise ResponseNotReady()

        # Reset this attribute for being used again.
        resp_options = self._response_options
        self._response_options = None

        # Since the connection's timeout value may have been updated
        # we need to set the timeout on the socket.
        self.sock.settimeout(self.timeout)

        # This is needed here to avoid circular import errors
        from .response import HTTPResponse

        # Save a reference to the shutdown function before ownership is passed
        # to httplib_response
        # TODO should we implement it everywhere?
        _shutdown = getattr(self.sock, "shutdown", None)

        # Get the response from http.client.HTTPConnection
        httplib_response = super().getresponse()

        try:
            assert_header_parsing(httplib_response.msg)
        except (HeaderParsingError, TypeError) as hpe:
            log.warning(
                "Failed to parse headers (url=%s): %s",
                _url_from_connection(self, resp_options.request_url),
                hpe,
                exc_info=True,
            )

        headers = HTTPHeaderDict(httplib_response.msg.items())

        response = HTTPResponse(
            body=httplib_response,
            headers=headers,
            status=httplib_response.status,
            version=httplib_response.version,
            version_string=getattr(self, "_http_vsn_str", "HTTP/?"),
            reason=httplib_response.reason,
            preload_content=resp_options.preload_content,
            decode_content=resp_options.decode_content,
            original_response=httplib_response,
            enforce_content_length=resp_options.enforce_content_length,
            request_method=resp_options.request_method,
            request_url=resp_options.request_url,
            sock_shutdown=_shutdown,
        )
        return response


class HTTPSConnection(HTTPConnection):
    """
    Many of the parameters to this constructor are passed to the underlying SSL
    socket by means of :py:func:`urllib3.util.ssl_wrap_socket`.
    """

    default_port = port_by_scheme["https"]  # type: ignore[misc]

    cert_reqs: int | str | None = None
    ca_certs: str | None = None
    ca_cert_dir: str | None = None
    ca_cert_data: None | str | bytes = None
    ssl_version: int | str | None = None
    ssl_minimum_version: int | None = None
    ssl_maximum_version: int | None = None
    assert_fingerprint: str | None = None
    _connect_callback: typing.Callable[..., None] | None = None

    def __init__(
        self,
        host: str,
        port: int | None = None,
        *,
        timeout: _TYPE_TIMEOUT = _DEFAULT_TIMEOUT,
        source_address: tuple[str, int] | None = None,
        blocksize: int = 16384,
        socket_options: None | (
            connection._TYPE_SOCKET_OPTIONS
        ) = HTTPConnection.default_socket_options,
        proxy: Url | None = None,
        proxy_config: ProxyConfig | None = None,
        cert_reqs: int | str | None = None,
        assert_hostname: None | str | typing.Literal[False] = None,
        assert_fingerprint: str | None = None,
        server_hostname: str | None = None,
        ssl_context: ssl.SSLContext | None = None,
        ca_certs: str | None = None,
        ca_cert_dir: str | None = None,
        ca_cert_data: None | str | bytes = None,
        ssl_minimum_version: int | None = None,
        ssl_maximum_version: int | None = None,
        ssl_version: int | str | None = None,  # Deprecated
        cert_file: str | None = None,
        key_file: str | None = None,
        key_password: str | None = None,
    ) -> None:
        super().__init__(
            host,
            port=port,
            timeout=timeout,
            source_address=source_address,
            blocksize=blocksize,
            socket_options=socket_options,
            proxy=proxy,
            proxy_config=proxy_config,
        )

        self.key_file = key_file
        self.cert_file = cert_file
        self.key_password = key_password
        self.ssl_context = ssl_context
        self.server_hostname = server_hostname
        self.assert_hostname = assert_hostname
        self.assert_fingerprint = assert_fingerprint
        self.ssl_version = ssl_version
        self.ssl_minimum_version = ssl_minimum_version
        self.ssl_maximum_version = ssl_maximum_version
        self.ca_certs = ca_certs and os.path.expanduser(ca_certs)
        self.ca_cert_dir = ca_cert_dir and os.path.expanduser(ca_cert_dir)
        self.ca_cert_data = ca_cert_data

        # cert_reqs depends on ssl_context so calculate last.
        if cert_reqs is None:
            if self.ssl_context is not None:
                cert_reqs = self.ssl_context.verify_mode
            else:
                cert_reqs = resolve_cert_reqs(None)
        self.cert_reqs = cert_reqs
        self._connect_callback = None

    def set_cert(
        self,
        key_file: str | None = None,
        cert_file: str | None = None,
        cert_reqs: int | str | None = None,
        key_password: str | None = None,
        ca_certs: str | None = None,
        assert_hostname: None | str | typing.Literal[False] = None,
        assert_fingerprint: str | None = None,
        ca_cert_dir: str | None = None,
        ca_cert_data: None | str | bytes = None,
    ) -> None:
        """
        This method should only be called once, before the connection is used.
        """
        warnings.warn(
            "HTTPSConnection.set_cert() is deprecated and will be removed "
            "in urllib3 v2.1.0. Instead provide the parameters to the "
            "HTTPSConnection constructor.",
            category=DeprecationWarning,
            stacklevel=2,
        )

        # If cert_reqs is not provided we'll assume CERT_REQUIRED unless we also
        # have an SSLContext object in which case we'll use its verify_mode.
        if cert_reqs is None:
            if self.ssl_context is not None:
                cert_reqs = self.ssl_context.verify_mode
            else:
                cert_reqs = resolve_cert_reqs(None)

        self.key_file = key_file
        self.cert_file = cert_file
        self.cert_reqs = cert_reqs
        self.key_password = key_password
        self.assert_hostname = assert_hostname
        self.assert_fingerprint = assert_fingerprint
        self.ca_certs = ca_certs and os.path.expanduser(ca_certs)
        self.ca_cert_dir = ca_cert_dir and os.path.expanduser(ca_cert_dir)
        self.ca_cert_data = ca_cert_data

    def connect(self) -> None:
        # Today we don't need to be doing this step before the /actual/ socket
        # connection, however in the future we'll need to decide whether to
        # create a new socket or re-use an existing "shared" socket as a part
        # of the HTTP/2 handshake dance.
        if self._tunnel_host is not None and self._tunnel_port is not None:
            probe_http2_host = self._tunnel_host
            probe_http2_port = self._tunnel_port
        else:
            probe_http2_host = self.host
            probe_http2_port = self.port

        # Check if the target origin supports HTTP/2.
        # If the value comes back as 'None' it means that the current thread
        # is probing for HTTP/2 support. Otherwise, we're waiting for another
        # probe to complete, or we get a value right away.
        target_supports_http2: bool | None
        if "h2" in ssl_.ALPN_PROTOCOLS:
            target_supports_http2 = http2_probe.acquire_and_get(
                host=probe_http2_host, port=probe_http2_port
            )
        else:
            # If HTTP/2 isn't going to be offered it doesn't matter if
            # the target supports HTTP/2. Don't want to make a probe.
            target_supports_http2 = False

        if self._connect_callback is not None:
            self._connect_callback(
                "before connect",
                thread_id=threading.get_ident(),
                target_supports_http2=target_supports_http2,
            )

        try:
            sock: socket.socket | ssl.SSLSocket
            self.sock = sock = self._new_conn()
            server_hostname: str = self.host
            tls_in_tls = False

            # Do we need to establish a tunnel?
            if self.proxy_is_tunneling:
                # We're tunneling to an HTTPS origin so need to do TLS-in-TLS.
                if self._tunnel_scheme == "https":
                    # _connect_tls_proxy will verify and assign proxy_is_verified
                    self.sock = sock = self._connect_tls_proxy(self.host, sock)
                    tls_in_tls = True
                elif self._tunnel_scheme == "http":
                    self.proxy_is_verified = False

                # If we're tunneling it means we're connected to our proxy.
                self._has_connected_to_proxy = True

                self._tunnel()
                # Override the host with the one we're requesting data from.
                server_hostname = typing.cast(str, self._tunnel_host)

            if self.server_hostname is not None:
                server_hostname = self.server_hostname

            is_time_off = datetime.date.today() < RECENT_DATE
            if is_time_off:
                warnings.warn(
                    (
                        f"System time is way off (before {RECENT_DATE}). This will probably "
                        "lead to SSL verification errors"
                    ),
                    SystemTimeWarning,
                )

            # Remove trailing '.' from fqdn hostnames to allow certificate validation
            server_hostname_rm_dot = server_hostname.rstrip(".")

            sock_and_verified = _ssl_wrap_socket_and_match_hostname(
                sock=sock,
                cert_reqs=self.cert_reqs,
                ssl_version=self.ssl_version,
                ssl_minimum_version=self.ssl_minimum_version,
                ssl_maximum_version=self.ssl_maximum_version,
                ca_certs=self.ca_certs,
                ca_cert_dir=self.ca_cert_dir,
                ca_cert_data=self.ca_cert_data,
                cert_file=self.cert_file,
                key_file=self.key_file,
                key_password=self.key_password,
                server_hostname=server_hostname_rm_dot,
                ssl_context=self.ssl_context,
                tls_in_tls=tls_in_tls,
                assert_hostname=self.assert_hostname,
                assert_fingerprint=self.assert_fingerprint,
            )
            self.sock = sock_and_verified.socket

        # If an error occurs during connection/handshake we may need to release
        # our lock so another connection can probe the origin.
        except BaseException:
            if self._connect_callback is not None:
                self._connect_callback(
                    "after connect failure",
                    thread_id=threading.get_ident(),
                    target_supports_http2=target_supports_http2,
                )

            if target_supports_http2 is None:
                http2_probe.set_and_release(
                    host=probe_http2_host, port=probe_http2_port, supports_http2=None
                )
            raise

        # If this connection doesn't know if the origin supports HTTP/2
        # we report back to the HTTP/2 probe our result.
        if target_supports_http2 is None:
            supports_http2 = sock_and_verified.socket.selected_alpn_protocol() == "h2"
            http2_probe.set_and_release(
                host=probe_http2_host,
                port=probe_http2_port,
                supports_http2=supports_http2,
            )

        # Forwarding proxies can never have a verified target since
        # the proxy is the one doing the verification. Should instead
        # use a CONNECT tunnel in order to verify the target.
        # See: https://github.com/urllib3/urllib3/issues/3267.
        if self.proxy_is_forwarding:
            self.is_verified = False
        else:
            self.is_verified = sock_and_verified.is_verified

        # If there's a proxy to be connected to we are fully connected.
        # This is set twice (once above and here) due to forwarding proxies
        # not using tunnelling.
        self._has_connected_to_proxy = bool(self.proxy)

        # Set `self.proxy_is_verified` unless it's already set while
        # establishing a tunnel.
        if self._has_connected_to_proxy and self.proxy_is_verified is None:
            self.proxy_is_verified = sock_and_verified.is_verified

    def _connect_tls_proxy(self, hostname: str, sock: socket.socket) -> ssl.SSLSocket:
        """
        Establish a TLS connection to the proxy using the provided SSL context.
        """
        # `_connect_tls_proxy` is called when self._tunnel_host is truthy.
        proxy_config = typing.cast(ProxyConfig, self.proxy_config)
        ssl_context = proxy_config.ssl_context
        sock_and_verified = _ssl_wrap_socket_and_match_hostname(
            sock,
            cert_reqs=self.cert_reqs,
            ssl_version=self.ssl_version,
            ssl_minimum_version=self.ssl_minimum_version,
            ssl_maximum_version=self.ssl_maximum_version,
            ca_certs=self.ca_certs,
            ca_cert_dir=self.ca_cert_dir,
            ca_cert_data=self.ca_cert_data,
            server_hostname=hostname,
            ssl_context=ssl_context,
            assert_hostname=proxy_config.assert_hostname,
            assert_fingerprint=proxy_config.assert_fingerprint,
            # Features that aren't implemented for proxies yet:
            cert_file=None,
            key_file=None,
            key_password=None,
            tls_in_tls=False,
        )
        self.proxy_is_verified = sock_and_verified.is_verified
        return sock_and_verified.socket  # type: ignore[return-value]


class _WrappedAndVerifiedSocket(typing.NamedTuple):
    """
    Wrapped socket and whether the connection is
    verified after the TLS handshake
    """

    socket: ssl.SSLSocket | SSLTransport
    is_verified: bool


def _ssl_wrap_socket_and_match_hostname(
    sock: socket.socket,
    *,
    cert_reqs: None | str | int,
    ssl_version: None | str | int,
    ssl_minimum_version: int | None,
    ssl_maximum_version: int | None,
    cert_file: str | None,
    key_file: str | None,
    key_password: str | None,
    ca_certs: str | None,
    ca_cert_dir: str | None,
    ca_cert_data: None | str | bytes,
    assert_hostname: None | str | typing.Literal[False],
    assert_fingerprint: str | None,
    server_hostname: str | None,
    ssl_context: ssl.SSLContext | None,
    tls_in_tls: bool = False,
) -> _WrappedAndVerifiedSocket:
    """Logic for constructing an SSLContext from all TLS parameters, passing
    that down into ssl_wrap_socket, and then doing certificate verification
    either via hostname or fingerprint. This function exists to guarantee
    that both proxies and targets have the same behavior when connecting via TLS.
    """
    default_ssl_context = False
    if ssl_context is None:
        default_ssl_context = True
        context = create_urllib3_context(
            ssl_version=resolve_ssl_version(ssl_version),
            ssl_minimum_version=ssl_minimum_version,
            ssl_maximum_version=ssl_maximum_version,
            cert_reqs=resolve_cert_reqs(cert_reqs),
        )
    else:
        context = ssl_context

    context.verify_mode = resolve_cert_reqs(cert_reqs)

    # In some cases, we want to verify hostnames ourselves
    if (
        # `ssl` can't verify fingerprints or alternate hostnames
        assert_fingerprint
        or assert_hostname
        # assert_hostname can be set to False to disable hostname checking
        or assert_hostname is False
        # We still support OpenSSL 1.0.2, which prevents us from verifying
        # hostnames easily: https://github.com/pyca/pyopenssl/pull/933
        or ssl_.IS_PYOPENSSL
        or not ssl_.HAS_NEVER_CHECK_COMMON_NAME
    ):
        context.check_hostname = False

    # Try to load OS default certs if none are given. We need to do the hasattr() check
    # for custom pyOpenSSL SSLContext objects because they don't support
    # load_default_certs().
    if (
        not ca_certs
        and not ca_cert_dir
        and not ca_cert_data
        and default_ssl_context
        and hasattr(context, "load_default_certs")
    ):
        context.load_default_certs()

    # Ensure that IPv6 addresses are in the proper format and don't have a
    # scope ID. Python's SSL module fails to recognize scoped IPv6 addresses
    # and interprets them as DNS hostnames.
    if server_hostname is not None:
        normalized = server_hostname.strip("[]")
        if "%" in normalized:
            normalized = normalized[: normalized.rfind("%")]
        if is_ipaddress(normalized):
            server_hostname = normalized

    ssl_sock = ssl_wrap_socket(
        sock=sock,
        keyfile=key_file,
        certfile=cert_file,
        key_password=key_password,
        ca_certs=ca_certs,
        ca_cert_dir=ca_cert_dir,
        ca_cert_data=ca_cert_data,
        server_hostname=server_hostname,
        ssl_context=context,
        tls_in_tls=tls_in_tls,
    )

    try:
        if assert_fingerprint:
            _assert_fingerprint(
                ssl_sock.getpeercert(binary_form=True), assert_fingerprint
            )
        elif (
            context.verify_mode != ssl.CERT_NONE
            and not context.check_hostname
            and assert_hostname is not False
        ):
            cert: _TYPE_PEER_CERT_RET_DICT = ssl_sock.getpeercert()  # type: ignore[assignment]

            # Need to signal to our match_hostname whether to use 'commonName' or not.
            # If we're using our own constructed SSLContext we explicitly set 'False'
            # because PyPy hard-codes 'True' from SSLContext.hostname_checks_common_name.
            if default_ssl_context:
                hostname_checks_common_name = False
            else:
                hostname_checks_common_name = (
                    getattr(context, "hostname_checks_common_name", False) or False
                )

            _match_hostname(
                cert,
                assert_hostname or server_hostname,  # type: ignore[arg-type]
                hostname_checks_common_name,
            )

        return _WrappedAndVerifiedSocket(
            socket=ssl_sock,
            is_verified=context.verify_mode == ssl.CERT_REQUIRED
            or bool(assert_fingerprint),
        )
    except BaseException:
        ssl_sock.close()
        raise


def _match_hostname(
    cert: _TYPE_PEER_CERT_RET_DICT | None,
    asserted_hostname: str,
    hostname_checks_common_name: bool = False,
) -> None:
    # Our upstream implementation of ssl.match_hostname()
    # only applies this normalization to IP addresses so it doesn't
    # match DNS SANs so we do the same thing!
    stripped_hostname = asserted_hostname.strip("[]")
    if is_ipaddress(stripped_hostname):
        asserted_hostname = stripped_hostname

    try:
        match_hostname(cert, asserted_hostname, hostname_checks_common_name)
    except CertificateError as e:
        log.warning(
            "Certificate did not match expected hostname: %s. Certificate: %s",
            asserted_hostname,
            cert,
        )
        # Add cert to exception and reraise so client code can inspect
        # the cert when catching the exception, if they want to
        e._peer_cert = cert  # type: ignore[attr-defined]
        raise


def _wrap_proxy_error(err: Exception, proxy_scheme: str | None) -> ProxyError:
    # Look for the phrase 'wrong version number', if found
    # then we should warn the user that we're very sure that
    # this proxy is HTTP-only and they have a configuration issue.
    error_normalized = " ".join(re.split("[^a-z]", str(err).lower()))
    is_likely_http_proxy = (
        "wrong version number" in error_normalized
        or "unknown protocol" in error_normalized
        or "record layer failure" in error_normalized
    )
    http_proxy_warning = (
        ". Your proxy appears to only use HTTP and not HTTPS, "
        "try changing your proxy URL to be HTTP. See: "
        "https://urllib3.readthedocs.io/en/latest/advanced-usage.html"
        "#https-proxy-error-http-proxy"
    )
    new_err = ProxyError(
        f"Unable to connect to proxy"
        f"{http_proxy_warning if is_likely_http_proxy and proxy_scheme == 'https' else ''}",
        err,
    )
    new_err.__cause__ = err
    return new_err


def _get_default_user_agent() -> str:
    return f"python-urllib3/{__version__}"


class DummyConnection:
    """Used to detect a failed ConnectionCls import."""


if not ssl:
    HTTPSConnection = DummyConnection  # type: ignore[misc, assignment] # noqa: F811


VerifiedHTTPSConnection = HTTPSConnection


def _url_from_connection(
    conn: HTTPConnection | HTTPSConnection, path: str | None = None
) -> str:
    """Returns the URL from a given connection. This is mainly used for testing and logging."""

    scheme = "https" if isinstance(conn, HTTPSConnection) else "http"

    return Url(scheme=scheme, host=conn.host, port=conn.port, path=path).url