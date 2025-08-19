
# === NexusCore/openenv\Lib\site-packages\debugpy\_vendored\pydevd\pydevd_attach_to_process\winappdbg\module.py ===
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
Module instrumentation.

@group Instrumentation:
    Module

@group Warnings:
    DebugSymbolsWarning
"""

from __future__ import with_statement

__revision__ = "$Id$"

__all__ = ["Module", "DebugSymbolsWarning"]

import sys
from winappdbg import win32
from winappdbg import compat
from winappdbg.textio import HexInput, HexDump
from winappdbg.util import PathOperations

# delayed imports
Process = None

import os
import warnings
import traceback

# ==============================================================================


class DebugSymbolsWarning(UserWarning):
    """
    This warning is issued if the support for debug symbols
    isn't working properly.
    """


# ==============================================================================


class Module(object):
    """
    Interface to a DLL library loaded in the context of another process.

    @group Properties:
        get_base, get_filename, get_name, get_size, get_entry_point,
        get_process, set_process, get_pid,
        get_handle, set_handle, open_handle, close_handle

    @group Labels:
        get_label, get_label_at_address, is_address_here,
        resolve, resolve_label, match_name

    @group Symbols:
        load_symbols, unload_symbols, get_symbols, iter_symbols,
        resolve_symbol, get_symbol_at_address

    @group Modules snapshot:
        clear

    @type unknown: str
    @cvar unknown: Suggested tag for unknown modules.

    @type lpBaseOfDll: int
    @ivar lpBaseOfDll: Base of DLL module.
        Use L{get_base} instead.

    @type hFile: L{FileHandle}
    @ivar hFile: Handle to the module file.
        Use L{get_handle} instead.

    @type fileName: str
    @ivar fileName: Module filename.
        Use L{get_filename} instead.

    @type SizeOfImage: int
    @ivar SizeOfImage: Size of the module.
        Use L{get_size} instead.

    @type EntryPoint: int
    @ivar EntryPoint: Entry point of the module.
        Use L{get_entry_point} instead.

    @type process: L{Process}
    @ivar process: Process where the module is loaded.
        Use the L{get_process} method instead.
    """

    unknown = "<unknown>"

    class _SymbolEnumerator(object):
        """
        Internally used by L{Module} to enumerate symbols in a module.
        """

        def __init__(self, undecorate=False):
            self.symbols = list()
            self.undecorate = undecorate

        def __call__(self, SymbolName, SymbolAddress, SymbolSize, UserContext):
            """
            Callback that receives symbols and stores them in a Python list.
            """
            if self.undecorate:
                try:
                    SymbolName = win32.UnDecorateSymbolName(SymbolName)
                except Exception:
                    pass  # not all symbols are decorated!
            self.symbols.append((SymbolName, SymbolAddress, SymbolSize))
            return win32.TRUE

    def __init__(self, lpBaseOfDll, hFile=None, fileName=None, SizeOfImage=None, EntryPoint=None, process=None):
        """
        @type  lpBaseOfDll: str
        @param lpBaseOfDll: Base address of the module.

        @type  hFile: L{FileHandle}
        @param hFile: (Optional) Handle to the module file.

        @type  fileName: str
        @param fileName: (Optional) Module filename.

        @type  SizeOfImage: int
        @param SizeOfImage: (Optional) Size of the module.

        @type  EntryPoint: int
        @param EntryPoint: (Optional) Entry point of the module.

        @type  process: L{Process}
        @param process: (Optional) Process where the module is loaded.
        """
        self.lpBaseOfDll = lpBaseOfDll
        self.fileName = fileName
        self.SizeOfImage = SizeOfImage
        self.EntryPoint = EntryPoint

        self.__symbols = list()

        self.set_handle(hFile)
        self.set_process(process)

    # Not really sure if it's a good idea...
    ##    def __eq__(self, aModule):
    ##        """
    ##        Compare two Module objects. The comparison is made using the process
    ##        IDs and the module bases.
    ##
    ##        @type  aModule: L{Module}
    ##        @param aModule: Another Module object.
    ##
    ##        @rtype:  bool
    ##        @return: C{True} if the two process IDs and module bases are equal,
    ##            C{False} otherwise.
    ##        """
    ##        return isinstance(aModule, Module)           and \
    ##               self.get_pid() == aModule.get_pid()   and \
    ##               self.get_base() == aModule.get_base()

    def get_handle(self):
        """
        @rtype:  L{Handle}
        @return: File handle.
            Returns C{None} if unknown.
        """
        # no way to guess!
        return self.__hFile

    def set_handle(self, hFile):
        """
        @type  hFile: L{Handle}
        @param hFile: File handle. Use C{None} to clear.
        """
        if hFile == win32.INVALID_HANDLE_VALUE:
            hFile = None
        self.__hFile = hFile

    hFile = property(get_handle, set_handle, doc="")

    def get_process(self):
        """
        @rtype:  L{Process}
        @return: Parent Process object.
            Returns C{None} if unknown.
        """
        # no way to guess!
        return self.__process

    def set_process(self, process=None):
        """
        Manually set the parent process. Use with care!

        @type  process: L{Process}
        @param process: (Optional) Process object. Use C{None} for no process.
        """
        if process is None:
            self.__process = None
        else:
            global Process  # delayed import
            if Process is None:
                from winappdbg.process import Process
            if not isinstance(process, Process):
                msg = "Parent process must be a Process instance, "
                msg += "got %s instead" % type(process)
                raise TypeError(msg)
            self.__process = process

    process = property(get_process, set_process, doc="")

    def get_pid(self):
        """
        @rtype:  int or None
        @return: Parent process global ID.
            Returns C{None} on error.
        """
        process = self.get_process()
        if process is not None:
            return process.get_pid()

    def get_base(self):
        """
        @rtype:  int or None
        @return: Base address of the module.
            Returns C{None} if unknown.
        """
        return self.lpBaseOfDll

    def get_size(self):
        """
        @rtype:  int or None
        @return: Base size of the module.
            Returns C{None} if unknown.
        """
        if not self.SizeOfImage:
            self.__get_size_and_entry_point()
        return self.SizeOfImage

    def get_entry_point(self):
        """
        @rtype:  int or None
        @return: Entry point of the module.
            Returns C{None} if unknown.
        """
        if not self.EntryPoint:
            self.__get_size_and_entry_point()
        return self.EntryPoint

    def __get_size_and_entry_point(self):
        "Get the size and entry point of the module using the Win32 API."
        process = self.get_process()
        if process:
            try:
                handle = process.get_handle(win32.PROCESS_VM_READ | win32.PROCESS_QUERY_INFORMATION)
                base = self.get_base()
                mi = win32.GetModuleInformation(handle, base)
                self.SizeOfImage = mi.SizeOfImage
                self.EntryPoint = mi.EntryPoint
            except WindowsError:
                e = sys.exc_info()[1]
                warnings.warn("Cannot get size and entry point of module %s, reason: %s" % (self.get_name(), e.strerror), RuntimeWarning)

    def get_filename(self):
        """
        @rtype:  str or None
        @return: Module filename.
            Returns C{None} if unknown.
        """
        if self.fileName is None:
            if self.hFile not in (None, win32.INVALID_HANDLE_VALUE):
                fileName = self.hFile.get_filename()
                if fileName:
                    fileName = PathOperations.native_to_win32_pathname(fileName)
                    self.fileName = fileName
        return self.fileName

    def __filename_to_modname(self, pathname):
        """
        @type  pathname: str
        @param pathname: Pathname to a module.

        @rtype:  str
        @return: Module name.
        """
        filename = PathOperations.pathname_to_filename(pathname)
        if filename:
            filename = filename.lower()
            filepart, extpart = PathOperations.split_extension(filename)
            if filepart and extpart:
                modName = filepart
            else:
                modName = filename
        else:
            modName = pathname
        return modName

    def get_name(self):
        """
        @rtype:  str
        @return: Module name, as used in labels.

        @warning: Names are B{NOT} guaranteed to be unique.

            If you need unique identification for a loaded module,
            use the base address instead.

        @see: L{get_label}
        """
        pathname = self.get_filename()
        if pathname:
            modName = self.__filename_to_modname(pathname)
            if isinstance(modName, compat.unicode):
                try:
                    modName = modName.encode("cp1252")
                except UnicodeEncodeError:
                    e = sys.exc_info()[1]
                    warnings.warn(str(e))
        else:
            modName = "0x%x" % self.get_base()
        return modName

    def match_name(self, name):
        """
        @rtype:  bool
        @return:
            C{True} if the given name could refer to this module.
            It may not be exactly the same returned by L{get_name}.
        """

        # If the given name is exactly our name, return True.
        # Comparison is case insensitive.
        my_name = self.get_name().lower()
        if name.lower() == my_name:
            return True

        # If the given name is a base address, compare it with ours.
        try:
            base = HexInput.integer(name)
        except ValueError:
            base = None
        if base is not None and base == self.get_base():
            return True

        # If the given name is a filename, convert it to a module name.
        # Then compare it with ours, case insensitive.
        modName = self.__filename_to_modname(name)
        if modName.lower() == my_name:
            return True

        # No match.
        return False

    # ------------------------------------------------------------------------------

    def open_handle(self):
        """
        Opens a new handle to the module.

        The new handle is stored in the L{hFile} property.
        """

        if not self.get_filename():
            msg = "Cannot retrieve filename for module at %s"
            msg = msg % HexDump.address(self.get_base())
            raise Exception(msg)

        hFile = win32.CreateFile(self.get_filename(), dwShareMode=win32.FILE_SHARE_READ, dwCreationDisposition=win32.OPEN_EXISTING)

        # In case hFile was set to an actual handle value instead of a Handle
        # object. This shouldn't happen unless the user tinkered with hFile.
        if not hasattr(self.hFile, "__del__"):
            self.close_handle()

        self.hFile = hFile

    def close_handle(self):
        """
        Closes the handle to the module.

        @note: Normally you don't need to call this method. All handles
            created by I{WinAppDbg} are automatically closed when the garbage
            collector claims them. So unless you've been tinkering with it,
            setting L{hFile} to C{None} should be enough.
        """
        try:
            if hasattr(self.hFile, "close"):
                self.hFile.close()
            elif self.hFile not in (None, win32.INVALID_HANDLE_VALUE):
                win32.CloseHandle(self.hFile)
        finally:
            self.hFile = None

    def get_handle(self):
        """
        @rtype:  L{FileHandle}
        @return: Handle to the module file.
        """
        if self.hFile in (None, win32.INVALID_HANDLE_VALUE):
            self.open_handle()
        return self.hFile

    def clear(self):
        """
        Clears the resources held by this object.
        """
        try:
            self.set_process(None)
        finally:
            self.close_handle()

    # ------------------------------------------------------------------------------

    # XXX FIXME
    # I've been told sometimes the debugging symbols APIs don't correctly
    # handle redirected exports (for example ws2_32!recv).
    # I haven't been able to reproduce the bug yet.
    def load_symbols(self):
        """
        Loads the debugging symbols for a module.
        Automatically called by L{get_symbols}.
        """
        if win32.PROCESS_ALL_ACCESS == win32.PROCESS_ALL_ACCESS_VISTA:
            dwAccess = win32.PROCESS_QUERY_LIMITED_INFORMATION
        else:
            dwAccess = win32.PROCESS_QUERY_INFORMATION
        hProcess = self.get_process().get_handle(dwAccess)
        hFile = self.hFile
        BaseOfDll = self.get_base()
        SizeOfDll = self.get_size()
        Enumerator = self._SymbolEnumerator()
        try:
            win32.SymInitialize(hProcess)
            SymOptions = win32.SymGetOptions()
            SymOptions |= (
                win32.SYMOPT_ALLOW_ZERO_ADDRESS
                | win32.SYMOPT_CASE_INSENSITIVE
                | win32.SYMOPT_FAVOR_COMPRESSED
                | win32.SYMOPT_INCLUDE_32BIT_MODULES
                | win32.SYMOPT_UNDNAME
            )
            SymOptions &= ~(win32.SYMOPT_LOAD_LINES | win32.SYMOPT_NO_IMAGE_SEARCH | win32.SYMOPT_NO_CPP | win32.SYMOPT_IGNORE_NT_SYMPATH)
            win32.SymSetOptions(SymOptions)
            try:
                win32.SymSetOptions(SymOptions | win32.SYMOPT_ALLOW_ABSOLUTE_SYMBOLS)
            except WindowsError:
                pass
            try:
                try:
                    success = win32.SymLoadModule64(hProcess, hFile, None, None, BaseOfDll, SizeOfDll)
                except WindowsError:
                    success = 0
                if not success:
                    ImageName = self.get_filename()
                    success = win32.SymLoadModule64(hProcess, None, ImageName, None, BaseOfDll, SizeOfDll)
                if success:
                    try:
                        win32.SymEnumerateSymbols64(hProcess, BaseOfDll, Enumerator)
                    finally:
                        win32.SymUnloadModule64(hProcess, BaseOfDll)
            finally:
                win32.SymCleanup(hProcess)
        except WindowsError:
            e = sys.exc_info()[1]
            msg = "Cannot load debug symbols for process ID %d, reason:\n%s"
            msg = msg % (self.get_pid(), traceback.format_exc(e))
            warnings.warn(msg, DebugSymbolsWarning)
        self.__symbols = Enumerator.symbols

    def unload_symbols(self):
        """
        Unloads the debugging symbols for a module.
        """
        self.__symbols = list()

    def get_symbols(self):
        """
        Returns the debugging symbols for a module.
        The symbols are automatically loaded when needed.

        @rtype:  list of tuple( str, int, int )
        @return: List of symbols.
            Each symbol is represented by a tuple that contains:
                - Symbol name
                - Symbol memory address
                - Symbol size in bytes
        """
        if not self.__symbols:
            self.load_symbols()
        return list(self.__symbols)

    def iter_symbols(self):
        """
        Returns an iterator for the debugging symbols in a module,
        in no particular order.
        The symbols are automatically loaded when needed.

        @rtype:  iterator of tuple( str, int, int )
        @return: Iterator of symbols.
            Each symbol is represented by a tuple that contains:
                - Symbol name
                - Symbol memory address
                - Symbol size in bytes
        """
        if not self.__symbols:
            self.load_symbols()
        return self.__symbols.__iter__()

    def resolve_symbol(self, symbol, bCaseSensitive=False):
        """
        Resolves a debugging symbol's address.

        @type  symbol: str
        @param symbol: Name of the symbol to resolve.

        @type  bCaseSensitive: bool
        @param bCaseSensitive: C{True} for case sensitive matches,
            C{False} for case insensitive.

        @rtype:  int or None
        @return: Memory address of symbol. C{None} if not found.
        """
        if bCaseSensitive:
            for SymbolName, SymbolAddress, SymbolSize in self.iter_symbols():
                if symbol == SymbolName:
                    return SymbolAddress
            for SymbolName, SymbolAddress, SymbolSize in self.iter_symbols():
                try:
                    SymbolName = win32.UnDecorateSymbolName(SymbolName)
                except Exception:
                    continue
                if symbol == SymbolName:
                    return SymbolAddress
        else:
            symbol = symbol.lower()
            for SymbolName, SymbolAddress, SymbolSize in self.iter_symbols():
                if symbol == SymbolName.lower():
                    return SymbolAddress
            for SymbolName, SymbolAddress, SymbolSize in self.iter_symbols():
                try:
                    SymbolName = win32.UnDecorateSymbolName(SymbolName)
                except Exception:
                    continue
                if symbol == SymbolName.lower():
                    return SymbolAddress

    def get_symbol_at_address(self, address):
        """
        Tries to find the closest matching symbol for the given address.

        @type  address: int
        @param address: Memory address to query.

        @rtype: None or tuple( str, int, int )
        @return: Returns a tuple consisting of:
             - Name
             - Address
             - Size (in bytes)
            Returns C{None} if no symbol could be matched.
        """
        found = None
        for SymbolName, SymbolAddress, SymbolSize in self.iter_symbols():
            if SymbolAddress > address:
                continue
            if SymbolAddress + SymbolSize > address:
                if not found or found[1] < SymbolAddress:
                    found = (SymbolName, SymbolAddress, SymbolSize)
        return found

    # ------------------------------------------------------------------------------

    def get_label(self, function=None, offset=None):
        """
        Retrieves the label for the given function of this module or the module
        base address if no function name is given.

        @type  function: str
        @param function: (Optional) Exported function name.

        @type  offset: int
        @param offset: (Optional) Offset from the module base address.

        @rtype:  str
        @return: Label for the module base address, plus the offset if given.
        """
        return _ModuleContainer.parse_label(self.get_name(), function, offset)

    def get_label_at_address(self, address, offset=None):
        """
        Creates a label from the given memory address.

        If the address belongs to the module, the label is made relative to
        it's base address.

        @type  address: int
        @param address: Memory address.

        @type  offset: None or int
        @param offset: (Optional) Offset value.

        @rtype:  str
        @return: Label pointing to the given address.
        """

        # Add the offset to the address.
        if offset:
            address = address + offset

        # Make the label relative to the base address if no match is found.
        module = self.get_name()
        function = None
        offset = address - self.get_base()

        # Make the label relative to the entrypoint if no other match is found.
        # Skip if the entry point is unknown.
        start = self.get_entry_point()
        if start and start <= address:
            function = "start"
            offset = address - start

        # Enumerate exported functions and debug symbols,
        # then find the closest match, if possible.
        try:
            symbol = self.get_symbol_at_address(address)
            if symbol:
                (SymbolName, SymbolAddress, SymbolSize) = symbol
                new_offset = address - SymbolAddress
                if new_offset <= offset:
                    function = SymbolName
                    offset = new_offset
        except WindowsError:
            pass

        # Parse the label and return it.
        return _ModuleContainer.parse_label(module, function, offset)

    def is_address_here(self, address):
        """
        Tries to determine if the given address belongs to this module.

        @type  address: int
        @param address: Memory address.

        @rtype:  bool or None
        @return: C{True} if the address belongs to the module,
            C{False} if it doesn't,
            and C{None} if it can't be determined.
        """
        base = self.get_base()
        size = self.get_size()
        if base and size:
            return base <= address < (base + size)
        return None

    def resolve(self, function):
        """
        Resolves a function exported by this module.

        @type  function: str or int
        @param function:
            str: Name of the function.
            int: Ordinal of the function.

        @rtype:  int
        @return: Memory address of the exported function in the process.
            Returns None on error.
        """

        # Unknown DLL filename, there's nothing we can do.
        filename = self.get_filename()
        if not filename:
            return None

        # If the DLL is already mapped locally, resolve the function.
        try:
            hlib = win32.GetModuleHandle(filename)
            address = win32.GetProcAddress(hlib, function)
        except WindowsError:
            # Load the DLL locally, resolve the function and unload it.
            try:
                hlib = win32.LoadLibraryEx(filename, win32.DONT_RESOLVE_DLL_REFERENCES)
                try:
                    address = win32.GetProcAddress(hlib, function)
                finally:
                    win32.FreeLibrary(hlib)
            except WindowsError:
                return None

        # A NULL pointer means the function was not found.
        if address in (None, 0):
            return None

        # Compensate for DLL base relocations locally and remotely.
        return address - hlib + self.lpBaseOfDll

    def resolve_label(self, label):
        """
        Resolves a label for this module only. If the label refers to another
        module, an exception is raised.

        @type  label: str
        @param label: Label to resolve.

        @rtype:  int
        @return: Memory address pointed to by the label.

        @raise ValueError: The label is malformed or impossible to resolve.
        @raise RuntimeError: Cannot resolve the module or function.
        """

        # Split the label into it's components.
        # Use the fuzzy mode whenever possible.
        aProcess = self.get_process()
        if aProcess is not None:
            (module, procedure, offset) = aProcess.split_label(label)
        else:
            (module, procedure, offset) = _ModuleContainer.split_label(label)

        # If a module name is given that doesn't match ours,
        # raise an exception.
        if module and not self.match_name(module):
            raise RuntimeError("Label does not belong to this module")

        # Resolve the procedure if given.
        if procedure:
            address = self.resolve(procedure)
            if address is None:
                # If it's a debug symbol, use the symbol.
                address = self.resolve_symbol(procedure)

                # If it's the keyword "start" use the entry point.
                if address is None and procedure == "start":
                    address = self.get_entry_point()

                # The procedure was not found.
                if address is None:
                    if not module:
                        module = self.get_name()
                    msg = "Can't find procedure %s in module %s"
                    raise RuntimeError(msg % (procedure, module))

        # If no procedure is given use the base address of the module.
        else:
            address = self.get_base()

        # Add the offset if given and return the resolved address.
        if offset:
            address = address + offset
        return address


# ==============================================================================

# TODO
# An alternative approach to the toolhelp32 snapshots: parsing the PEB and
# fetching the list of loaded modules from there. That would solve the problem
# of toolhelp32 not working when the process hasn't finished initializing.
# See: http://pferrie.host22.com/misc/lowlevel3.htm


class _ModuleContainer(object):
    """
    Encapsulates the capability to contain Module objects.

    @note: Labels are an approximated way of referencing memory locations
        across different executions of the same process, or different processes
        with common modules. They are not meant to be perfectly unique, and
        some errors may occur when multiple modules with the same name are
        loaded, or when module filenames can't be retrieved.

    @group Modules snapshot:
        scan_modules,
        get_module, get_module_bases, get_module_count,
        get_module_at_address, get_module_by_name,
        has_module, iter_modules, iter_module_addresses,
        clear_modules

    @group Labels:
        parse_label, split_label, sanitize_label, resolve_label,
        resolve_label_components, get_label_at_address, split_label_strict,
        split_label_fuzzy

    @group Symbols:
        load_symbols, unload_symbols, get_symbols, iter_symbols,
        resolve_symbol, get_symbol_at_address

    @group Debugging:
        is_system_defined_breakpoint, get_system_breakpoint,
        get_user_breakpoint, get_breakin_breakpoint,
        get_wow64_system_breakpoint, get_wow64_user_breakpoint,
        get_wow64_breakin_breakpoint, get_break_on_error_ptr
    """

    def __init__(self):
        self.__moduleDict = dict()
        self.__system_breakpoints = dict()

        # Replace split_label with the fuzzy version on object instances.
        self.split_label = self.__use_fuzzy_mode

    def __initialize_snapshot(self):
        """
        Private method to automatically initialize the snapshot
        when you try to use it without calling any of the scan_*
        methods first. You don't need to call this yourself.
        """
        if not self.__moduleDict:
            try:
                self.scan_modules()
            except WindowsError:
                pass

    def __contains__(self, anObject):
        """
        @type  anObject: L{Module}, int
        @param anObject:
            - C{Module}: Module object to look for.
            - C{int}: Base address of the DLL to look for.

        @rtype:  bool
        @return: C{True} if the snapshot contains
            a L{Module} object with the same base address.
        """
        if isinstance(anObject, Module):
            anObject = anObject.lpBaseOfDll
        return self.has_module(anObject)

    def __iter__(self):
        """
        @see:    L{iter_modules}
        @rtype:  dictionary-valueiterator
        @return: Iterator of L{Module} objects in this snapshot.
        """
        return self.iter_modules()

    def __len__(self):
        """
        @see:    L{get_module_count}
        @rtype:  int
        @return: Count of L{Module} objects in this snapshot.
        """
        return self.get_module_count()

    def has_module(self, lpBaseOfDll):
        """
        @type  lpBaseOfDll: int
        @param lpBaseOfDll: Base address of the DLL to look for.

        @rtype:  bool
        @return: C{True} if the snapshot contains a
            L{Module} object with the given base address.
        """
        self.__initialize_snapshot()
        return lpBaseOfDll in self.__moduleDict

    def get_module(self, lpBaseOfDll):
        """
        @type  lpBaseOfDll: int
        @param lpBaseOfDll: Base address of the DLL to look for.

        @rtype:  L{Module}
        @return: Module object with the given base address.
        """
        self.__initialize_snapshot()
        if lpBaseOfDll not in self.__moduleDict:
            msg = "Unknown DLL base address %s"
            msg = msg % HexDump.address(lpBaseOfDll)
            raise KeyError(msg)
        return self.__moduleDict[lpBaseOfDll]

    def iter_module_addresses(self):
        """
        @see:    L{iter_modules}
        @rtype:  dictionary-keyiterator
        @return: Iterator of DLL base addresses in this snapshot.
        """
        self.__initialize_snapshot()
        return compat.iterkeys(self.__moduleDict)

    def iter_modules(self):
        """
        @see:    L{iter_module_addresses}
        @rtype:  dictionary-valueiterator
        @return: Iterator of L{Module} objects in this snapshot.
        """
        self.__initialize_snapshot()
        return compat.itervalues(self.__moduleDict)

    def get_module_bases(self):
        """
        @see:    L{iter_module_addresses}
        @rtype:  list( int... )
        @return: List of DLL base addresses in this snapshot.
        """
        self.__initialize_snapshot()
        return compat.keys(self.__moduleDict)

    def get_module_count(self):
        """
        @rtype:  int
        @return: Count of L{Module} objects in this snapshot.
        """
        self.__initialize_snapshot()
        return len(self.__moduleDict)

    # ------------------------------------------------------------------------------

    def get_module_by_name(self, modName):
        """
        @type  modName: int
        @param modName:
            Name of the module to look for, as returned by L{Module.get_name}.
            If two or more modules with the same name are loaded, only one
            of the matching modules is returned.

            You can also pass a full pathname to the DLL file.
            This works correctly even if two modules with the same name
            are loaded from different paths.

        @rtype:  L{Module}
        @return: C{Module} object that best matches the given name.
            Returns C{None} if no C{Module} can be found.
        """

        # Convert modName to lowercase.
        # This helps make case insensitive string comparisons.
        modName = modName.lower()

        # modName is an absolute pathname.
        if PathOperations.path_is_absolute(modName):
            for lib in self.iter_modules():
                if modName == lib.get_filename().lower():
                    return lib
            return None  # Stop trying to match the name.

        # Get all the module names.
        # This prevents having to iterate through the module list
        #  more than once.
        modDict = [(lib.get_name(), lib) for lib in self.iter_modules()]
        modDict = dict(modDict)

        # modName is a base filename.
        if modName in modDict:
            return modDict[modName]

        # modName is a base filename without extension.
        filepart, extpart = PathOperations.split_extension(modName)
        if filepart and extpart:
            if filepart in modDict:
                return modDict[filepart]

        # modName is a base address.
        try:
            baseAddress = HexInput.integer(modName)
        except ValueError:
            return None
        if self.has_module(baseAddress):
            return self.get_module(baseAddress)

        # Module not found.
        return None

    def get_module_at_address(self, address):
        """
        @type  address: int
        @param address: Memory address to query.

        @rtype:  L{Module}
        @return: C{Module} object that best matches the given address.
            Returns C{None} if no C{Module} can be found.
        """
        bases = self.get_module_bases()
        bases.sort()
        bases.append(long(0x10000000000000000))  # max. 64 bit address + 1
        if address >= bases[0]:
            i = 0
            max_i = len(bases) - 1
            while i < max_i:
                begin, end = bases[i : i + 2]
                if begin <= address < end:
                    module = self.get_module(begin)
                    here = module.is_address_here(address)
                    if here is False:
                        break
                    else:  # True or None
                        return module
                i = i + 1
        return None

    # XXX this method musn't end up calling __initialize_snapshot by accident!
    def scan_modules(self):
        """
        Populates the snapshot with loaded modules.
        """

        # The module filenames may be spoofed by malware,
        # since this information resides in usermode space.
        # See: http://www.ragestorm.net/blogs/?p=163

        # Ignore special process IDs.
        # PID 0: System Idle Process. Also has a special meaning to the
        #        toolhelp APIs (current process).
        # PID 4: System Integrity Group. See this forum post for more info:
        #        http://tinyurl.com/ycza8jo
        #        (points to social.technet.microsoft.com)
        #        Only on XP and above
        # PID 8: System (?) only in Windows 2000 and below AFAIK.
        #        It's probably the same as PID 4 in XP and above.
        dwProcessId = self.get_pid()
        if dwProcessId in (0, 4, 8):
            return

        # It would seem easier to clear the snapshot first.
        # But then all open handles would be closed.
        found_bases = set()
        with win32.CreateToolhelp32Snapshot(win32.TH32CS_SNAPMODULE, dwProcessId) as hSnapshot:
            me = win32.Module32First(hSnapshot)
            while me is not None:
                lpBaseAddress = me.modBaseAddr
                fileName = me.szExePath  # full pathname
                if not fileName:
                    fileName = me.szModule  # filename only
                    if not fileName:
                        fileName = None
                else:
                    fileName = PathOperations.native_to_win32_pathname(fileName)
                found_bases.add(lpBaseAddress)
                ##                if not self.has_module(lpBaseAddress): # XXX triggers a scan
                if lpBaseAddress not in self.__moduleDict:
                    aModule = Module(lpBaseAddress, fileName=fileName, SizeOfImage=me.modBaseSize, process=self)
                    self._add_module(aModule)
                else:
                    aModule = self.get_module(lpBaseAddress)
                    if not aModule.fileName:
                        aModule.fileName = fileName
                    if not aModule.SizeOfImage:
                        aModule.SizeOfImage = me.modBaseSize
                    if not aModule.process:
                        aModule.process = self
                me = win32.Module32Next(hSnapshot)
        ##        for base in self.get_module_bases(): # XXX triggers a scan
        for base in compat.keys(self.__moduleDict):
            if base not in found_bases:
                self._del_module(base)

    def clear_modules(self):
        """
        Clears the modules snapshot.
        """
        for aModule in compat.itervalues(self.__moduleDict):
            aModule.clear()
        self.__moduleDict = dict()

    # ------------------------------------------------------------------------------

    @staticmethod
    def parse_label(module=None, function=None, offset=None):
        """
        Creates a label from a module and a function name, plus an offset.

        @warning: This method only creates the label, it doesn't make sure the
            label actually points to a valid memory location.

        @type  module: None or str
        @param module: (Optional) Module name.

        @type  function: None, str or int
        @param function: (Optional) Function name or ordinal.

        @type  offset: None or int
        @param offset: (Optional) Offset value.

            If C{function} is specified, offset from the function.

            If C{function} is C{None}, offset from the module.

        @rtype:  str
        @return:
            Label representing the given function in the given module.

        @raise ValueError:
            The module or function name contain invalid characters.
        """

        # TODO
        # Invalid characters should be escaped or filtered.

        # Convert ordinals to strings.
        try:
            function = "#0x%x" % function
        except TypeError:
            pass

        # Validate the parameters.
        if module is not None and ("!" in module or "+" in module):
            raise ValueError("Invalid module name: %s" % module)
        if function is not None and ("!" in function or "+" in function):
            raise ValueError("Invalid function name: %s" % function)

        # Parse the label.
        if module:
            if function:
                if offset:
                    label = "%s!%s+0x%x" % (module, function, offset)
                else:
                    label = "%s!%s" % (module, function)
            else:
                if offset:
                    ##                    label = "%s+0x%x!" % (module, offset)
                    label = "%s!0x%x" % (module, offset)
                else:
                    label = "%s!" % module
        else:
            if function:
                if offset:
                    label = "!%s+0x%x" % (function, offset)
                else:
                    label = "!%s" % function
            else:
                if offset:
                    label = "0x%x" % offset
                else:
                    label = "0x0"

        return label

    @staticmethod
    def split_label_strict(label):
        """
        Splits a label created with L{parse_label}.

        To parse labels with a less strict syntax, use the L{split_label_fuzzy}
        method instead.

        @warning: This method only parses the label, it doesn't make sure the
            label actually points to a valid memory location.

        @type  label: str
        @param label: Label to split.

        @rtype:  tuple( str or None, str or int or None, int or None )
        @return: Tuple containing the C{module} name,
            the C{function} name or ordinal, and the C{offset} value.

            If the label doesn't specify a module,
            then C{module} is C{None}.

            If the label doesn't specify a function,
            then C{function} is C{None}.

            If the label doesn't specify an offset,
            then C{offset} is C{0}.

        @raise ValueError: The label is malformed.
        """
        module = function = None
        offset = 0

        # Special case: None
        if not label:
            label = "0x0"
        else:
            # Remove all blanks.
            label = label.replace(" ", "")
            label = label.replace("\t", "")
            label = label.replace("\r", "")
            label = label.replace("\n", "")

            # Special case: empty label.
            if not label:
                label = "0x0"

        # * ! *
        if "!" in label:
            try:
                module, function = label.split("!")
            except ValueError:
                raise ValueError("Malformed label: %s" % label)

            # module ! function
            if function:
                if "+" in module:
                    raise ValueError("Malformed label: %s" % label)

                # module ! function + offset
                if "+" in function:
                    try:
                        function, offset = function.split("+")
                    except ValueError:
                        raise ValueError("Malformed label: %s" % label)
                    try:
                        offset = HexInput.integer(offset)
                    except ValueError:
                        raise ValueError("Malformed label: %s" % label)
                else:
                    # module ! offset
                    try:
                        offset = HexInput.integer(function)
                        function = None
                    except ValueError:
                        pass
            else:
                # module + offset !
                if "+" in module:
                    try:
                        module, offset = module.split("+")
                    except ValueError:
                        raise ValueError("Malformed label: %s" % label)
                    try:
                        offset = HexInput.integer(offset)
                    except ValueError:
                        raise ValueError("Malformed label: %s" % label)

                else:
                    # module !
                    try:
                        offset = HexInput.integer(module)
                        module = None

                    # offset !
                    except ValueError:
                        pass

            if not module:
                module = None
            if not function:
                function = None

        # *
        else:
            # offset
            try:
                offset = HexInput.integer(label)

            # # ordinal
            except ValueError:
                if label.startswith("#"):
                    function = label
                    try:
                        HexInput.integer(function[1:])

                    # module?
                    # function?
                    except ValueError:
                        raise ValueError("Ambiguous label: %s" % label)

                # module?
                # function?
                else:
                    raise ValueError("Ambiguous label: %s" % label)

        # Convert function ordinal strings into integers.
        if function and function.startswith("#"):
            try:
                function = HexInput.integer(function[1:])
            except ValueError:
                pass

        # Convert null offsets to None.
        if not offset:
            offset = None

        return (module, function, offset)

    def split_label_fuzzy(self, label):
        """
        Splits a label entered as user input.

        It's more flexible in it's syntax parsing than the L{split_label_strict}
        method, as it allows the exclamation mark (B{C{!}}) to be omitted. The
        ambiguity is resolved by searching the modules in the snapshot to guess
        if a label refers to a module or a function. It also tries to rebuild
        labels when they contain hardcoded addresses.

        @warning: This method only parses the label, it doesn't make sure the
            label actually points to a valid memory location.

        @type  label: str
        @param label: Label to split.

        @rtype:  tuple( str or None, str or int or None, int or None )
        @return: Tuple containing the C{module} name,
            the C{function} name or ordinal, and the C{offset} value.

            If the label doesn't specify a module,
            then C{module} is C{None}.

            If the label doesn't specify a function,
            then C{function} is C{None}.

            If the label doesn't specify an offset,
            then C{offset} is C{0}.

        @raise ValueError: The label is malformed.
        """
        module = function = None
        offset = 0

        # Special case: None
        if not label:
            label = compat.b("0x0")
        else:
            # Remove all blanks.
            label = label.replace(compat.b(" "), compat.b(""))
            label = label.replace(compat.b("\t"), compat.b(""))
            label = label.replace(compat.b("\r"), compat.b(""))
            label = label.replace(compat.b("\n"), compat.b(""))

            # Special case: empty label.
            if not label:
                label = compat.b("0x0")

        # If an exclamation sign is present, we know we can parse it strictly.
        if compat.b("!") in label:
            return self.split_label_strict(label)

        ##        # Try to parse it strictly, on error do it the fuzzy way.
        ##        try:
        ##            return self.split_label(label)
        ##        except ValueError:
        ##            pass

        # * + offset
        if compat.b("+") in label:
            try:
                prefix, offset = label.split(compat.b("+"))
            except ValueError:
                raise ValueError("Malformed label: %s" % label)
            try:
                offset = HexInput.integer(offset)
            except ValueError:
                raise ValueError("Malformed label: %s" % label)
            label = prefix

        # This parses both filenames and base addresses.
        modobj = self.get_module_by_name(label)
        if modobj:
            # module
            # module + offset
            module = modobj.get_name()

        else:
            # TODO
            # If 0xAAAAAAAA + 0xBBBBBBBB is given,
            # A is interpreted as a module base address,
            # and B as an offset.
            # If that fails, it'd be good to add A+B and try to
            # use the nearest loaded module.

            # offset
            # base address + offset (when no module has that base address)
            try:
                address = HexInput.integer(label)

                if offset:
                    # If 0xAAAAAAAA + 0xBBBBBBBB is given,
                    # A is interpreted as a module base address,
                    # and B as an offset.
                    # If that fails, we get here, meaning no module was found
                    # at A. Then add up A+B and work with that as a hardcoded
                    # address.
                    offset = address + offset
                else:
                    # If the label is a hardcoded address, we get here.
                    offset = address

                # If only a hardcoded address is given,
                # rebuild the label using get_label_at_address.
                # Then parse it again, but this time strictly,
                # both because there is no need for fuzzy syntax and
                # to prevent an infinite recursion if there's a bug here.
                try:
                    new_label = self.get_label_at_address(offset)
                    module, function, offset = self.split_label_strict(new_label)
                except ValueError:
                    pass

            # function
            # function + offset
            except ValueError:
                function = label

        # Convert function ordinal strings into integers.
        if function and function.startswith(compat.b("#")):
            try:
                function = HexInput.integer(function[1:])
            except ValueError:
                pass

        # Convert null offsets to None.
        if not offset:
            offset = None

        return (module, function, offset)

    @classmethod
    def split_label(cls, label):
        """
        Splits a label into it's C{module}, C{function} and C{offset}
        components, as used in L{parse_label}.

        When called as a static method, the strict syntax mode is used::

            winappdbg.Process.split_label( "kernel32!CreateFileA" )

        When called as an instance method, the fuzzy syntax mode is used::

            aProcessInstance.split_label( "CreateFileA" )

        @see: L{split_label_strict}, L{split_label_fuzzy}

        @type  label: str
        @param label: Label to split.

        @rtype:  tuple( str or None, str or int or None, int or None )
        @return:
            Tuple containing the C{module} name,
            the C{function} name or ordinal, and the C{offset} value.

            If the label doesn't specify a module,
            then C{module} is C{None}.

            If the label doesn't specify a function,
            then C{function} is C{None}.

            If the label doesn't specify an offset,
            then C{offset} is C{0}.

        @raise ValueError: The label is malformed.
        """

        # XXX
        # Docstring indentation was removed so epydoc doesn't complain
        # when parsing the docs for __use_fuzzy_mode().

        # This function is overwritten by __init__
        # so here is the static implementation only.
        return cls.split_label_strict(label)

    # The split_label method is replaced with this function by __init__.
    def __use_fuzzy_mode(self, label):
        "@see: L{split_label}"
        return self.split_label_fuzzy(label)

    ##    __use_fuzzy_mode.__doc__ = split_label.__doc__

    def sanitize_label(self, label):
        """
        Converts a label taken from user input into a well-formed label.

        @type  label: str
        @param label: Label taken from user input.

        @rtype:  str
        @return: Sanitized label.
        """
        (module, function, offset) = self.split_label_fuzzy(label)
        label = self.parse_label(module, function, offset)
        return label

    def resolve_label(self, label):
        """
        Resolve the memory address of the given label.

        @note:
            If multiple modules with the same name are loaded,
            the label may be resolved at any of them. For a more precise
            way to resolve functions use the base address to get the L{Module}
            object (see L{Process.get_module}) and then call L{Module.resolve}.

            If no module name is specified in the label, the function may be
            resolved in any loaded module. If you want to resolve all functions
            with that name in all processes, call L{Process.iter_modules} to
            iterate through all loaded modules, and then try to resolve the
            function in each one of them using L{Module.resolve}.

        @type  label: str
        @param label: Label to resolve.

        @rtype:  int
        @return: Memory address pointed to by the label.

        @raise ValueError: The label is malformed or impossible to resolve.
        @raise RuntimeError: Cannot resolve the module or function.
        """

        # Split the label into module, function and offset components.
        module, function, offset = self.split_label_fuzzy(label)

        # Resolve the components into a memory address.
        address = self.resolve_label_components(module, function, offset)

        # Return the memory address.
        return address

    def resolve_label_components(self, module=None, function=None, offset=None):
        """
        Resolve the memory address of the given module, function and/or offset.

        @note:
            If multiple modules with the same name are loaded,
            the label may be resolved at any of them. For a more precise
            way to resolve functions use the base address to get the L{Module}
            object (see L{Process.get_module}) and then call L{Module.resolve}.

            If no module name is specified in the label, the function may be
            resolved in any loaded module. If you want to resolve all functions
            with that name in all processes, call L{Process.iter_modules} to
            iterate through all loaded modules, and then try to resolve the
            function in each one of them using L{Module.resolve}.

        @type  module: None or str
        @param module: (Optional) Module name.

        @type  function: None, str or int
        @param function: (Optional) Function name or ordinal.

        @type  offset: None or int
        @param offset: (Optional) Offset value.

            If C{function} is specified, offset from the function.

            If C{function} is C{None}, offset from the module.

        @rtype:  int
        @return: Memory address pointed to by the label.

        @raise ValueError: The label is malformed or impossible to resolve.
        @raise RuntimeError: Cannot resolve the module or function.
        """
        # Default address if no module or function are given.
        # An offset may be added later.
        address = 0

        # Resolve the module.
        # If the module is not found, check for the special symbol "main".
        if module:
            modobj = self.get_module_by_name(module)
            if not modobj:
                if module == "main":
                    modobj = self.get_main_module()
                else:
                    raise RuntimeError("Module %r not found" % module)

            # Resolve the exported function or debugging symbol.
            # If all else fails, check for the special symbol "start".
            if function:
                address = modobj.resolve(function)
                if address is None:
                    address = modobj.resolve_symbol(function)
                    if address is None:
                        if function == "start":
                            address = modobj.get_entry_point()
                        if address is None:
                            msg = "Symbol %r not found in module %s"
                            raise RuntimeError(msg % (function, module))

            # No function, use the base address.
            else:
                address = modobj.get_base()

        # Resolve the function in any module.
        # If all else fails, check for the special symbols "main" and "start".
        elif function:
            for modobj in self.iter_modules():
                address = modobj.resolve(function)
                if address is not None:
                    break
            if address is None:
                if function == "start":
                    modobj = self.get_main_module()
                    address = modobj.get_entry_point()
                elif function == "main":
                    modobj = self.get_main_module()
                    address = modobj.get_base()
                else:
                    msg = "Function %r not found in any module" % function
                    raise RuntimeError(msg)

        # Return the address plus the offset.
        if offset:
            address = address + offset
        return address

    def get_label_at_address(self, address, offset=None):
        """
        Creates a label from the given memory address.

        @warning: This method uses the name of the nearest currently loaded
            module. If that module is unloaded later, the label becomes
            impossible to resolve.

        @type  address: int
        @param address: Memory address.

        @type  offset: None or int
        @param offset: (Optional) Offset value.

        @rtype:  str
        @return: Label pointing to the given address.
        """
        if offset:
            address = address + offset
        modobj = self.get_module_at_address(address)
        if modobj:
            label = modobj.get_label_at_address(address)
        else:
            label = self.parse_label(None, None, address)
        return label

    # ------------------------------------------------------------------------------

    # The memory addresses of system breakpoints are be cached, since they're
    # all in system libraries it's not likely they'll ever change their address
    # during the lifetime of the process... I don't suppose a program could
    # happily unload ntdll.dll and survive.
    def __get_system_breakpoint(self, label):
        try:
            return self.__system_breakpoints[label]
        except KeyError:
            try:
                address = self.resolve_label(label)
            except Exception:
                return None
            self.__system_breakpoints[label] = address
            return address

    # It's in kernel32 in Windows Server 2003, in ntdll since Windows Vista.
    # It can only be resolved if we have the debug symbols.
    def get_break_on_error_ptr(self):
        """
        @rtype: int
        @return:
            If present, returns the address of the C{g_dwLastErrorToBreakOn}
            global variable for this process. If not, returns C{None}.
        """
        address = self.__get_system_breakpoint("ntdll!g_dwLastErrorToBreakOn")
        if not address:
            address = self.__get_system_breakpoint("kernel32!g_dwLastErrorToBreakOn")
            # cheat a little :)
            self.__system_breakpoints["ntdll!g_dwLastErrorToBreakOn"] = address
        return address

    def is_system_defined_breakpoint(self, address):
        """
        @type  address: int
        @param address: Memory address.

        @rtype:  bool
        @return: C{True} if the given address points to a system defined
            breakpoint. System defined breakpoints are hardcoded into
            system libraries.
        """
        if address:
            module = self.get_module_at_address(address)
            if module:
                return module.match_name("ntdll") or module.match_name("kernel32")
        return False

    # FIXME
    # In Wine, the system breakpoint seems to be somewhere in kernel32.
    def get_system_breakpoint(self):
        """
        @rtype:  int or None
        @return: Memory address of the system breakpoint
            within the process address space.
            Returns C{None} on error.
        """
        return self.__get_system_breakpoint("ntdll!DbgBreakPoint")

    # I don't know when this breakpoint is actually used...
    def get_user_breakpoint(self):
        """
        @rtype:  int or None
        @return: Memory address of the user breakpoint
            within the process address space.
            Returns C{None} on error.
        """
        return self.__get_system_breakpoint("ntdll!DbgUserBreakPoint")

    # On some platforms, this breakpoint can only be resolved
    # when the debugging symbols for ntdll.dll are loaded.
    def get_breakin_breakpoint(self):
        """
        @rtype:  int or None
        @return: Memory address of the remote breakin breakpoint
            within the process address space.
            Returns C{None} on error.
        """
        return self.__get_system_breakpoint("ntdll!DbgUiRemoteBreakin")

    # Equivalent of ntdll!DbgBreakPoint in Wow64.
    def get_wow64_system_breakpoint(self):
        """
        @rtype:  int or None
        @return: Memory address of the Wow64 system breakpoint
            within the process address space.
            Returns C{None} on error.
        """
        return self.__get_system_breakpoint("ntdll32!DbgBreakPoint")

    # Equivalent of ntdll!DbgUserBreakPoint in Wow64.
    def get_wow64_user_breakpoint(self):
        """
        @rtype:  int or None
        @return: Memory address of the Wow64 user breakpoint
            within the process address space.
            Returns C{None} on error.
        """
        return self.__get_system_breakpoint("ntdll32!DbgUserBreakPoint")

    # Equivalent of ntdll!DbgUiRemoteBreakin in Wow64.
    def get_wow64_breakin_breakpoint(self):
        """
        @rtype:  int or None
        @return: Memory address of the Wow64 remote breakin breakpoint
            within the process address space.
            Returns C{None} on error.
        """
        return self.__get_system_breakpoint("ntdll32!DbgUiRemoteBreakin")

    # ------------------------------------------------------------------------------

    def load_symbols(self):
        """
        Loads the debugging symbols for all modules in this snapshot.
        Automatically called by L{get_symbols}.
        """
        for aModule in self.iter_modules():
            aModule.load_symbols()

    def unload_symbols(self):
        """
        Unloads the debugging symbols for all modules in this snapshot.
        """
        for aModule in self.iter_modules():
            aModule.unload_symbols()

    def get_symbols(self):
        """
        Returns the debugging symbols for all modules in this snapshot.
        The symbols are automatically loaded when needed.

        @rtype:  list of tuple( str, int, int )
        @return: List of symbols.
            Each symbol is represented by a tuple that contains:
                - Symbol name
                - Symbol memory address
                - Symbol size in bytes
        """
        symbols = list()
        for aModule in self.iter_modules():
            for symbol in aModule.iter_symbols():
                symbols.append(symbol)
        return symbols

    def iter_symbols(self):
        """
        Returns an iterator for the debugging symbols in all modules in this
        snapshot, in no particular order.
        The symbols are automatically loaded when needed.

        @rtype:  iterator of tuple( str, int, int )
        @return: Iterator of symbols.
            Each symbol is represented by a tuple that contains:
                - Symbol name
                - Symbol memory address
                - Symbol size in bytes
        """
        for aModule in self.iter_modules():
            for symbol in aModule.iter_symbols():
                yield symbol

    def resolve_symbol(self, symbol, bCaseSensitive=False):
        """
        Resolves a debugging symbol's address.

        @type  symbol: str
        @param symbol: Name of the symbol to resolve.

        @type  bCaseSensitive: bool
        @param bCaseSensitive: C{True} for case sensitive matches,
            C{False} for case insensitive.

        @rtype:  int or None
        @return: Memory address of symbol. C{None} if not found.
        """
        if bCaseSensitive:
            for SymbolName, SymbolAddress, SymbolSize in self.iter_symbols():
                if symbol == SymbolName:
                    return SymbolAddress
        else:
            symbol = symbol.lower()
            for SymbolName, SymbolAddress, SymbolSize in self.iter_symbols():
                if symbol == SymbolName.lower():
                    return SymbolAddress

    def get_symbol_at_address(self, address):
        """
        Tries to find the closest matching symbol for the given address.

        @type  address: int
        @param address: Memory address to query.

        @rtype: None or tuple( str, int, int )
        @return: Returns a tuple consisting of:
             - Name
             - Address
             - Size (in bytes)
            Returns C{None} if no symbol could be matched.
        """
        # Any module may have symbols pointing anywhere in memory, so there's
        # no easy way to optimize this. I guess we're stuck with brute force.
        found = None
        for SymbolName, SymbolAddress, SymbolSize in self.iter_symbols():
            if SymbolAddress > address:
                continue

            if SymbolAddress == address:
                found = (SymbolName, SymbolAddress, SymbolSize)
                break

            if SymbolAddress < address:
                if found and (address - found[1]) < (address - SymbolAddress):
                    continue
                else:
                    found = (SymbolName, SymbolAddress, SymbolSize)
        return found

    # ------------------------------------------------------------------------------

    # XXX _notify_* methods should not trigger a scan

    def _add_module(self, aModule):
        """
        Private method to add a module object to the snapshot.

        @type  aModule: L{Module}
        @param aModule: Module object.
        """
        ##        if not isinstance(aModule, Module):
        ##            if hasattr(aModule, '__class__'):
        ##                typename = aModule.__class__.__name__
        ##            else:
        ##                typename = str(type(aModule))
        ##            msg = "Expected Module, got %s instead" % typename
        ##            raise TypeError(msg)
        lpBaseOfDll = aModule.get_base()
        ##        if lpBaseOfDll in self.__moduleDict:
        ##            msg = "Module already exists: %d" % lpBaseOfDll
        ##            raise KeyError(msg)
        aModule.set_process(self)
        self.__moduleDict[lpBaseOfDll] = aModule

    def _del_module(self, lpBaseOfDll):
        """
        Private method to remove a module object from the snapshot.

        @type  lpBaseOfDll: int
        @param lpBaseOfDll: Module base address.
        """
        try:
            aModule = self.__moduleDict[lpBaseOfDll]
            del self.__moduleDict[lpBaseOfDll]
        except KeyError:
            aModule = None
            msg = "Unknown base address %d" % HexDump.address(lpBaseOfDll)
            warnings.warn(msg, RuntimeWarning)
        if aModule:
            aModule.clear()  # remove circular references

    def __add_loaded_module(self, event):
        """
        Private method to automatically add new module objects from debug events.

        @type  event: L{Event}
        @param event: Event object.
        """
        lpBaseOfDll = event.get_module_base()
        hFile = event.get_file_handle()
        ##        if not self.has_module(lpBaseOfDll):  # XXX this would trigger a scan
        if lpBaseOfDll not in self.__moduleDict:
            fileName = event.get_filename()
            if not fileName:
                fileName = None
            if hasattr(event, "get_start_address"):
                EntryPoint = event.get_start_address()
            else:
                EntryPoint = None
            aModule = Module(lpBaseOfDll, hFile, fileName=fileName, EntryPoint=EntryPoint, process=self)
            self._add_module(aModule)
        else:
            aModule = self.get_module(lpBaseOfDll)
            if not aModule.hFile and hFile not in (None, 0, win32.INVALID_HANDLE_VALUE):
                aModule.hFile = hFile
            if not aModule.process:
                aModule.process = self
            if aModule.EntryPoint is None and hasattr(event, "get_start_address"):
                aModule.EntryPoint = event.get_start_address()
            if not aModule.fileName:
                fileName = event.get_filename()
                if fileName:
                    aModule.fileName = fileName

    def _notify_create_process(self, event):
        """
        Notify the load of the main module.

        This is done automatically by the L{Debug} class, you shouldn't need
        to call it yourself.

        @type  event: L{CreateProcessEvent}
        @param event: Create process event.

        @rtype:  bool
        @return: C{True} to call the user-defined handle, C{False} otherwise.
        """
        self.__add_loaded_module(event)
        return True

    def _notify_load_dll(self, event):
        """
        Notify the load of a new module.

        This is done automatically by the L{Debug} class, you shouldn't need
        to call it yourself.

        @type  event: L{LoadDLLEvent}
        @param event: Load DLL event.

        @rtype:  bool
        @return: C{True} to call the user-defined handle, C{False} otherwise.
        """
        self.__add_loaded_module(event)
        return True

    def _notify_unload_dll(self, event):
        """
        Notify the release of a loaded module.

        This is done automatically by the L{Debug} class, you shouldn't need
        to call it yourself.

        @type  event: L{UnloadDLLEvent}
        @param event: Unload DLL event.

        @rtype:  bool
        @return: C{True} to call the user-defined handle, C{False} otherwise.
        """
        lpBaseOfDll = event.get_module_base()
        ##        if self.has_module(lpBaseOfDll):  # XXX this would trigger a scan
        if lpBaseOfDll in self.__moduleDict:
            self._del_module(lpBaseOfDll)
        return True

# === NexusCore/openenv\Lib\site-packages\debugpy\_vendored\pydevd\_pydevd_sys_monitoring\_pydevd_sys_monitoring.py ===
# Copyright: Brainwy Software
#
# License: EPL

from collections import namedtuple
import dis
import os
import re
import sys
from _pydev_bundle._pydev_saved_modules import threading
from types import CodeType, FrameType
from typing import Dict, Optional, Tuple, Any
from os.path import basename, splitext

from _pydev_bundle import pydev_log
from _pydevd_bundle import pydevd_dont_trace
from _pydevd_bundle.pydevd_constants import (
    IS_PY313_OR_GREATER,
    GlobalDebuggerHolder,
    ForkSafeLock,
    PYDEVD_IPYTHON_CONTEXT,
    EXCEPTION_TYPE_USER_UNHANDLED,
    RETURN_VALUES_DICT,
    PYTHON_SUSPEND,
)
from pydevd_file_utils import (
    NORM_PATHS_AND_BASE_CONTAINER,
    get_abs_path_real_path_and_base_from_file,
    get_abs_path_real_path_and_base_from_frame,
)
from _pydevd_bundle.pydevd_trace_dispatch import should_stop_on_exception, handle_exception
from _pydevd_bundle.pydevd_constants import EXCEPTION_TYPE_HANDLED
from _pydevd_bundle.pydevd_trace_dispatch import is_unhandled_exception
from _pydevd_bundle.pydevd_breakpoints import stop_on_unhandled_exception
from _pydevd_bundle.pydevd_utils import get_clsname_for_code

# fmt: off
# IFDEF CYTHON
# import cython
# from _pydevd_bundle.pydevd_cython cimport set_additional_thread_info, any_thread_stepping, PyDBAdditionalThreadInfo
# ELSE
from _pydevd_bundle.pydevd_additional_thread_info import set_additional_thread_info, any_thread_stepping, PyDBAdditionalThreadInfo
# ENDIF
# fmt: on

try:
    from _pydevd_bundle.pydevd_bytecode_utils import get_smart_step_into_variant_from_frame_offset
except ImportError:

    def get_smart_step_into_variant_from_frame_offset(*args, **kwargs):
        return None


if hasattr(sys, "monitoring"):
    DEBUGGER_ID = sys.monitoring.DEBUGGER_ID
    monitor = sys.monitoring

_thread_local_info = threading.local()
_get_ident = threading.get_ident
_thread_active = threading._active  # noqa

CMD_STEP_INTO: int = 107
CMD_STEP_OVER: int = 108
CMD_STEP_INTO_MY_CODE: int = 144
CMD_STEP_INTO_COROUTINE: int = 206
CMD_SMART_STEP_INTO: int = 128
can_skip: bool = True
CMD_STEP_RETURN: int = 109
CMD_STEP_OVER_MY_CODE: int = 159
CMD_STEP_RETURN_MY_CODE: int = 160
CMD_SET_BREAK: int = 111
CMD_SET_FUNCTION_BREAK: int = 208
STATE_RUN: int = 1
STATE_SUSPEND: int = 2

IGNORE_EXCEPTION_TAG = re.compile("[^#]*#.*@IgnoreException")
DEBUG_START = ("pydevd.py", "run")
DEBUG_START_PY3K = ("_pydev_execfile.py", "execfile")
TRACE_PROPERTY = "pydevd_traceproperty.py"

_global_notify_skipped_step_in = False
_global_notify_skipped_step_in_lock = ForkSafeLock()


# fmt: off
# IFDEF CYTHON
# cdef _notify_skipped_step_in_because_of_filters(py_db, frame):
# ELSE
def _notify_skipped_step_in_because_of_filters(py_db, frame):
# ENDIF
# fmt: on
    global _global_notify_skipped_step_in

    with _global_notify_skipped_step_in_lock:
        if _global_notify_skipped_step_in:
            # Check with lock in place (callers should actually have checked
            # before without the lock in place due to performance).
            return
        _global_notify_skipped_step_in = True
        py_db.notify_skipped_step_in_because_of_filters(frame)


# Easy for cython: always get the one at level 0 as that's the caller frame
# (on Python we have to control the depth to get the first user frame).
# fmt: off
# IFDEF CYTHON
# @cython.cfunc
# def _getframe(depth=0):
#     return sys._getframe()
# ELSE
_getframe = sys._getframe
# ENDIF
# fmt: on


# fmt: off
# IFDEF CYTHON
# cdef _get_bootstrap_frame(depth):
# ELSE
def _get_bootstrap_frame(depth: int) -> Tuple[Optional[FrameType], bool]:
# ENDIF
# fmt: on
    try:
        return _thread_local_info.f_bootstrap, _thread_local_info.is_bootstrap_frame_internal
    except:
        frame = _getframe(depth)
        f_bootstrap = frame
        # print('called at', f_bootstrap.f_code.co_name, f_bootstrap.f_code.co_filename, f_bootstrap.f_code.co_firstlineno)
        is_bootstrap_frame_internal = False
        while f_bootstrap is not None:
            filename = f_bootstrap.f_code.co_filename
            name = splitext(basename(filename))[0]

            if name == "threading":
                if f_bootstrap.f_code.co_name in ("__bootstrap", "_bootstrap"):
                    # We need __bootstrap_inner, not __bootstrap.
                    return None, False

                elif f_bootstrap.f_code.co_name in ("__bootstrap_inner", "_bootstrap_inner", "is_alive"):
                    # Note: be careful not to use threading.current_thread to avoid creating a dummy thread.
                    is_bootstrap_frame_internal = True
                    break

            elif name == "pydev_monkey":
                if f_bootstrap.f_code.co_name == "__call__":
                    is_bootstrap_frame_internal = True
                    break

            elif name == "pydevd":
                if f_bootstrap.f_code.co_name in ("run", "main"):
                    # We need to get to _exec
                    return None, False

                if f_bootstrap.f_code.co_name == "_exec":
                    is_bootstrap_frame_internal = True
                    break

            elif f_bootstrap.f_back is None:
                break

            f_bootstrap = f_bootstrap.f_back

        if f_bootstrap is not None:
            _thread_local_info.is_bootstrap_frame_internal = is_bootstrap_frame_internal
            _thread_local_info.f_bootstrap = f_bootstrap
            return _thread_local_info.f_bootstrap, _thread_local_info.is_bootstrap_frame_internal

        return f_bootstrap, is_bootstrap_frame_internal


# fmt: off
# IFDEF CYTHON
# cdef _get_unhandled_exception_frame(exc, int depth):
# ELSE
def _get_unhandled_exception_frame(exc, depth: int) -> Optional[FrameType]:
# ENDIF
# fmt: on
    try:
        # Unhandled frame has to be from the same exception.
        if _thread_local_info.f_unhandled_exc is exc:
            return _thread_local_info.f_unhandled_frame
        else:
            del _thread_local_info.f_unhandled_frame
            del _thread_local_info.f_unhandled_exc
            raise AttributeError('Not the same exception')
    except:
        f_unhandled = _getframe(depth)

        while f_unhandled is not None and f_unhandled.f_back is not None:
            f_back = f_unhandled.f_back
            filename = f_back.f_code.co_filename
            name = splitext(basename(filename))[0]

            # When the back frame is the bootstrap (or if we have no back
            # frame) then use this frame as the one to track.
            if name == "threading":
                if f_back.f_code.co_name in ("__bootstrap", "_bootstrap", "__bootstrap_inner", "_bootstrap_inner", "run"):
                    break

            elif name == "pydev_monkey":
                if f_back.f_code.co_name == "__call__":
                    break

            elif name == "pydevd":
                if f_back.f_code.co_name in ("_exec", "run", "main"):
                    break

            elif name == "pydevd_runpy":
                if f_back.f_code.co_name.startswith(("run", "_run")):
                    break

            elif name == "<frozen runpy>":
                if f_back.f_code.co_name.startswith(("run", "_run")):
                    break

            elif name == "runpy":
                if f_back.f_code.co_name.startswith(("run", "_run")):
                    break

            f_unhandled = f_back

        if f_unhandled is not None:
            _thread_local_info.f_unhandled_frame = f_unhandled
            _thread_local_info.f_unhandled_exc = exc
            return _thread_local_info.f_unhandled_frame

        return f_unhandled


# fmt: off
# IFDEF CYTHON
# cdef class ThreadInfo:
#     cdef unsigned long thread_ident
#     cdef PyDBAdditionalThreadInfo additional_info
#     thread: threading.Thread
#     trace: bool
#     _use_is_stopped: bool
# ELSE
class ThreadInfo:
    additional_info: PyDBAdditionalThreadInfo
    thread_ident: int
    thread: threading.Thread
    trace: bool
# ENDIF
# fmt: on

    # fmt: off
    # IFDEF CYTHON
    # def __init__(self, thread, unsigned long thread_ident, bint trace, PyDBAdditionalThreadInfo additional_info):
    # ELSE
    def __init__(self, thread: threading.Thread, thread_ident: int, trace: bool, additional_info: PyDBAdditionalThreadInfo):
    # ENDIF
    # fmt: on
        self.thread = thread
        self.thread_ident = thread_ident
        self.additional_info = additional_info
        self.trace = trace
        self._use_is_stopped = hasattr(thread, '_is_stopped')
        
    # fmt: off
    # IFDEF CYTHON
    # cdef bint is_thread_alive(self):
    # ELSE
    def is_thread_alive(self):
    # ENDIF
    # fmt: on
        if self._use_is_stopped:
            return not self.thread._is_stopped
        else:
            return not self.thread._handle.is_done()


class _DeleteDummyThreadOnDel:
    """
    Helper class to remove a dummy thread from threading._active on __del__.
    """

    def __init__(self, dummy_thread):
        self._dummy_thread = dummy_thread
        self._tident = dummy_thread.ident
        # Put the thread on a thread local variable so that when
        # the related thread finishes this instance is collected.
        #
        # Note: no other references to this instance may be created.
        # If any client code creates a reference to this instance,
        # the related _DummyThread will be kept forever!
        _thread_local_info._track_dummy_thread_ref = self

    def __del__(self):
        with threading._active_limbo_lock:
            if _thread_active.get(self._tident) is self._dummy_thread:
                _thread_active.pop(self._tident, None)


# fmt: off
# IFDEF CYTHON
# cdef _create_thread_info(depth):
#     cdef unsigned long thread_ident
# ELSE
def _create_thread_info(depth):
# ENDIF
# fmt: on
    # Don't call threading.currentThread because if we're too early in the process
    # we may create a dummy thread.
    thread_ident = _get_ident()

    f_bootstrap_frame, is_bootstrap_frame_internal = _get_bootstrap_frame(depth + 1)
    if f_bootstrap_frame is None:
        return None  # Case for threading when it's still in bootstrap or early in pydevd.

    if is_bootstrap_frame_internal:
        t = None
        if f_bootstrap_frame.f_code.co_name in ("__bootstrap_inner", "_bootstrap_inner", "is_alive"):
            # Note: be careful not to use threading.current_thread to avoid creating a dummy thread.
            t = f_bootstrap_frame.f_locals.get("self")
            if not isinstance(t, threading.Thread):
                t = None

        elif f_bootstrap_frame.f_code.co_name in ("_exec", "__call__"):
            # Note: be careful not to use threading.current_thread to avoid creating a dummy thread.
            t = f_bootstrap_frame.f_locals.get("t")
            if not isinstance(t, threading.Thread):
                t = None

    else:
        # This means that the first frame is not in threading nor in pydevd.
        # In practice this means it's some unmanaged thread, so, creating
        # a dummy thread is ok in this use-case.
        t = threading.current_thread()

    if t is None:
        t = _thread_active.get(thread_ident)

    if isinstance(t, threading._DummyThread) and not IS_PY313_OR_GREATER:
        _thread_local_info._ref = _DeleteDummyThreadOnDel(t)

    if t is None:
        return None

    if getattr(t, "is_pydev_daemon_thread", False):
        return ThreadInfo(t, thread_ident, False, None)
    else:
        try:
            additional_info = t.additional_info
            if additional_info is None:
                raise AttributeError()
        except:
            additional_info = set_additional_thread_info(t)
        return ThreadInfo(t, thread_ident, True, additional_info)


# fmt: off
# IFDEF CYTHON
# cdef class FuncCodeInfo:
#     cdef str co_filename
#     cdef str canonical_normalized_filename
#     cdef str abs_path_filename
#     cdef bint always_skip_code
#     cdef bint breakpoint_found
#     cdef bint function_breakpoint_found
#     cdef bint plugin_line_breakpoint_found
#     cdef bint plugin_call_breakpoint_found
#     cdef bint plugin_line_stepping
#     cdef bint plugin_call_stepping
#     cdef bint plugin_return_stepping
#     cdef int pydb_mtime
#     cdef dict bp_line_to_breakpoint
#     cdef object function_breakpoint
#     cdef bint always_filtered_out
#     cdef bint filtered_out_force_checked
#     cdef object try_except_container_obj
#     cdef object code_obj
#     cdef str co_name
# ELSE
class FuncCodeInfo:

# ENDIF
# fmt: on
    def __init__(self):
        self.co_filename: str = ""
        self.canonical_normalized_filename: str = ""
        self.abs_path_filename: str = ""

        # These is never seen and we never stop, even if it's a callback coming
        # from user code (these are completely invisible to the debugging tracing).
        self.always_skip_code: bool = False

        self.breakpoint_found: bool = False
        self.function_breakpoint_found: bool = False

        # A plugin can choose whether to stop on function calls or line events.
        self.plugin_line_breakpoint_found: bool = False
        self.plugin_call_breakpoint_found: bool = False

        self.plugin_line_stepping: bool = False
        self.plugin_call_stepping: bool = False
        self.plugin_return_stepping: bool = False

        # When pydb_mtime != PyDb.mtime the validity of breakpoints have
        # to be re-evaluated (if invalid a new FuncCodeInfo must be created and
        # tracing can't be disabled for the related frames).
        self.pydb_mtime: int = -1

        self.bp_line_to_breakpoint: Dict[int, Any] = {}
        self.function_breakpoint = None

        # This means some file is globally filtered out during debugging. Note
        # that we may still need to pause in it (in a step return to user code,
        # we may need to track this one).
        self.always_filtered_out: bool = False

        # This should be used to filter code in a CMD_STEP_INTO_MY_CODE
        # (and other XXX_MY_CODE variants).
        self.filtered_out_force_checked: bool = False

        self.try_except_container_obj: Optional[_TryExceptContainerObj] = None
        self.code_obj: CodeType = None
        self.co_name: str = ""

    def get_line_of_offset(self, offset):
        for start, end, line in self.code_obj.co_lines():
            if start is not None and end is not None and line is not None:
                if offset >= start and offset <= end:
                    return line
        return -1


# fmt: off
# IFDEF CYTHON
# cdef _get_thread_info(bint create, int depth):
# ELSE
def _get_thread_info(create: bool, depth: int) -> Optional[ThreadInfo]:
# ENDIF
# fmt: on
    """
    Provides thread-related info.

    May return None if the thread is still not active.
    """
    try:
        # Note: changing to a `dict[thread.ident] = thread_info` had almost no
        # effect in the performance.
        return _thread_local_info.thread_info
    except:
        if not create:
            return None
        thread_info = _create_thread_info(depth + 1)
        if thread_info is None:
            return None

        _thread_local_info.thread_info = thread_info
        return _thread_local_info.thread_info


# fmt: off
# IFDEF CYTHON
# cdef class _CodeLineInfo:
#     cdef dict line_to_offset
#     cdef int first_line
#     cdef int last_line
# ELSE
class _CodeLineInfo:
    line_to_offset: Dict[int, Any]
    first_line: int
    last_line: int
# ENDIF
# fmt: on

    # fmt: off
    # IFDEF CYTHON
    # def __init__(self, dict line_to_offset, int first_line, int last_line):
    #     self.line_to_offset = line_to_offset
    #     self.first_line = first_line
    #     self.last_line = last_line
    # ELSE
    def __init__(self, line_to_offset, first_line, last_line):
        self.line_to_offset = line_to_offset
        self.first_line = first_line
        self.last_line = last_line

    # ENDIF
    # fmt: on

# Note: this method has a version in cython too
# fmt: off
# IFDEF CYTHON
# cdef _CodeLineInfo _get_code_line_info(code_obj, _cache={}):
# ELSE
def _get_code_line_info(code_obj, _cache={}) -> _CodeLineInfo:
# ENDIF
# fmt: on
    try:
        return _cache[code_obj]
    except:
        line_to_offset = {}
        first_line = None
        last_line = None

        for offset, line in dis.findlinestarts(code_obj):
            if line is not None:
                line_to_offset[line] = offset

        if len(line_to_offset):
            first_line = min(line_to_offset)
            last_line = max(line_to_offset)
        ret = _CodeLineInfo(line_to_offset, first_line, last_line)
        _cache[code_obj] = ret
        return ret


_code_to_func_code_info_cache: Dict[CodeType, "FuncCodeInfo"] = {}


# fmt: off
# IFDEF CYTHON
# cpdef FuncCodeInfo _get_func_code_info(code_obj, frame_or_depth):
#     cdef FuncCodeInfo func_code_info
# ELSE
def _get_func_code_info(code_obj, frame_or_depth) -> FuncCodeInfo:
# ENDIF
# fmt: on
    """
    Provides code-object related info.

    Note that it contains informations on the breakpoints for a given function.
    If breakpoints change a new FuncCodeInfo instance will be created.

    Note that this can be called by any thread.
    """
    py_db = GlobalDebuggerHolder.global_dbg
    if py_db is None:
        return None

    func_code_info = _code_to_func_code_info_cache.get(code_obj)
    if func_code_info is not None:
        if func_code_info.pydb_mtime == py_db.mtime:
            # if DEBUG:
            # print('_get_func_code_info: matched mtime', key, code_obj)
            return func_code_info

    # fmt: off
    # IFDEF CYTHON
    # cdef dict cache_file_type
    # cdef tuple cache_file_type_key
    # cdef PyCodeObject * code
    # cdef str co_filename
    # cdef str co_name
    # code = <PyCodeObject *> code_obj
    # co_filename = <str> code.co_filename
    # co_name = <str> code.co_name
    # ELSE
    cache_file_type: dict
    cache_file_type_key: tuple
    code = code_obj
    co_filename: str = code.co_filename
    co_name: str = code.co_name
    # ENDIF
    # fmt: on

    # print('_get_func_code_info: new (mtime did not match)', key, code_obj)

    func_code_info = FuncCodeInfo()
    func_code_info.code_obj = code_obj
    code_line_info = _get_code_line_info(code_obj)
    line_to_offset = code_line_info.line_to_offset
    func_code_info.pydb_mtime = py_db.mtime

    func_code_info.co_filename = co_filename
    func_code_info.co_name = co_name

    # Compute whether to always skip this.
    try:
        abs_path_real_path_and_base = NORM_PATHS_AND_BASE_CONTAINER[co_filename]
    except:
        abs_path_real_path_and_base = get_abs_path_real_path_and_base_from_file(co_filename)

    func_code_info.abs_path_filename = abs_path_real_path_and_base[0]
    func_code_info.canonical_normalized_filename = abs_path_real_path_and_base[1]

    frame = None
    cache_file_type = py_db.get_cache_file_type()
    # Note: this cache key must be the same from PyDB.get_file_type() -- see it for comments
    # on the cache.
    cache_file_type_key = (code.co_firstlineno, abs_path_real_path_and_base[0], code_obj)
    try:
        file_type = cache_file_type[cache_file_type_key]  # Make it faster
    except:
        if frame is None:
            if frame_or_depth.__class__ == int:
                frame = _getframe(frame_or_depth + 1)
            else:
                frame = frame_or_depth
            assert frame.f_code is code_obj, "%s != %s" % (frame.f_code, code_obj)

        file_type = py_db.get_file_type(frame, abs_path_real_path_and_base)  # we don't want to debug anything related to pydevd

    if file_type is not None:
        func_code_info.always_skip_code = True
        func_code_info.always_filtered_out = True
        _code_to_func_code_info_cache[code_obj] = func_code_info
        return func_code_info

    # still not set, check for dont trace comments.
    if pydevd_dont_trace.should_trace_hook is not None:
        # I.e.: cache the result skip (no need to evaluate the same frame multiple times).
        # Note that on a code reload, we won't re-evaluate this because in practice, the frame.f_code
        # Which will be handled by this frame is read-only, so, we can cache it safely.
        if not pydevd_dont_trace.should_trace_hook(code_obj, func_code_info.abs_path_filename):
            if frame is None:
                if frame_or_depth.__class__ == int:
                    frame = _getframe(frame_or_depth + 1)
                else:
                    frame = frame_or_depth
            assert frame.f_code is code_obj

            func_code_info.always_filtered_out = True
            _code_to_func_code_info_cache[code_obj] = func_code_info
            return func_code_info

    if frame is None:
        if frame_or_depth.__class__ == int:
            frame = _getframe(frame_or_depth + 1)
        else:
            frame = frame_or_depth
        assert frame.f_code is code_obj

    func_code_info.filtered_out_force_checked = py_db.apply_files_filter(frame, func_code_info.abs_path_filename, True)

    if py_db.is_files_filter_enabled:
        func_code_info.always_filtered_out = py_db.apply_files_filter(frame, func_code_info.abs_path_filename, False)
        if func_code_info.always_filtered_out:
            _code_to_func_code_info_cache[code_obj] = func_code_info
            return func_code_info

    else:
        func_code_info.always_filtered_out = False

    # Handle regular breakpoints
    breakpoints: dict = py_db.breakpoints.get(func_code_info.canonical_normalized_filename)
    function_breakpoint: object = py_db.function_breakpoint_name_to_breakpoint.get(func_code_info.co_name)
    # print('\n---')
    # print(py_db.breakpoints)
    # print(func_code_info.canonical_normalized_filename)
    # print(py_db.breakpoints.get(func_code_info.canonical_normalized_filename))
    if function_breakpoint:
        # Go directly into tracing mode
        func_code_info.function_breakpoint_found = True
        func_code_info.function_breakpoint = function_breakpoint

    if breakpoints:
        # if DEBUG:
        #    print('found breakpoints', code_obj_py.co_name, breakpoints)

        bp_line_to_breakpoint = {}

        for breakpoint_line, bp in breakpoints.items():
            if breakpoint_line in line_to_offset:
                bp_line_to_breakpoint[breakpoint_line] = bp

        func_code_info.breakpoint_found = bool(bp_line_to_breakpoint)
        func_code_info.bp_line_to_breakpoint = bp_line_to_breakpoint

    if py_db.plugin:
        plugin_manager = py_db.plugin
        is_tracked_frame = plugin_manager.is_tracked_frame(frame)

        if is_tracked_frame:
            if py_db.has_plugin_line_breaks:
                required_events_breakpoint = plugin_manager.required_events_breakpoint()
                func_code_info.plugin_line_breakpoint_found = "line" in required_events_breakpoint
                func_code_info.plugin_call_breakpoint_found = "call" in required_events_breakpoint

            required_events_stepping = plugin_manager.required_events_stepping()
            func_code_info.plugin_line_stepping: bool = "line" in required_events_stepping
            func_code_info.plugin_call_stepping: bool = "call" in required_events_stepping
            func_code_info.plugin_return_stepping: bool = "return" in required_events_stepping

    _code_to_func_code_info_cache[code_obj] = func_code_info
    return func_code_info


# fmt: off
# IFDEF CYTHON
# cdef _enable_line_tracing(code):
# ELSE
def _enable_line_tracing(code):
# ENDIF
# fmt: on
    # print('enable line tracing', code)
    _ensure_monitoring()
    events = monitor.get_local_events(DEBUGGER_ID, code)
    monitor.set_local_events(DEBUGGER_ID, code, events | monitor.events.LINE | monitor.events.JUMP)


# fmt: off
# IFDEF CYTHON
# cdef _enable_return_tracing(code):
# ELSE
def _enable_return_tracing(code):
# ENDIF
# fmt: on
    # print('enable return tracing', code)
    _ensure_monitoring()
    events = monitor.get_local_events(DEBUGGER_ID, code)
    monitor.set_local_events(DEBUGGER_ID, code, events | monitor.events.PY_RETURN)


# fmt: off
# IFDEF CYTHON
# cpdef disable_code_tracing(code):
# ELSE
def disable_code_tracing(code):
# ENDIF
# fmt: on
    _ensure_monitoring()
    monitor.set_local_events(DEBUGGER_ID, code, 0)


# fmt: off
# IFDEF CYTHON
# cpdef enable_code_tracing(unsigned long thread_ident, code, frame):
# ELSE
def enable_code_tracing(thread_ident: Optional[int], code, frame) -> bool:
# ENDIF
# fmt: on
    """
    Note: this must enable code tracing for the given code/frame.

    The frame can be from any thread!

    :return: Whether code tracing was added in this function to the given code.
    """
    # DEBUG = False  # 'my_code.py' in code.co_filename or 'other.py' in code.co_filename
    # if DEBUG:
    #     print('==== enable code tracing', code.co_filename[-30:], code.co_name)
    py_db: object = GlobalDebuggerHolder.global_dbg
    if py_db is None or py_db.pydb_disposed:
        return False

    func_code_info: FuncCodeInfo = _get_func_code_info(code, frame)
    if func_code_info.always_skip_code:
        # if DEBUG:
        #     print('disable (always skip)')
        return False

    try:
        thread = threading._active.get(thread_ident)
        if thread is None:
            return False
        additional_info = set_additional_thread_info(thread)
    except:
        # Cannot set based on stepping
        return False

    return _enable_code_tracing(py_db, additional_info, func_code_info, code, frame, False)


# fmt: off
# IFDEF CYTHON
# cdef bint _enable_code_tracing(py_db, PyDBAdditionalThreadInfo additional_info, FuncCodeInfo func_code_info, code, frame, bint warn_on_filtered_out):
#     cdef int step_cmd
#     cdef bint is_stepping
#     cdef bint code_tracing_added
# ELSE
def _enable_code_tracing(py_db, additional_info, func_code_info: FuncCodeInfo, code, frame, warn_on_filtered_out) -> bool:
# ENDIF
# fmt: on
    """
    :return: Whether code tracing was added in this function to the given code.
    """
    # DEBUG = False  # 'my_code.py' in code.co_filename or 'other.py' in code.co_filename
    step_cmd = additional_info.pydev_step_cmd
    is_stepping = step_cmd != -1
    code_tracing_added = False

    if func_code_info.always_filtered_out:
        # if DEBUG:
        #     print('disable (always filtered out)')
        if (
            warn_on_filtered_out
            and is_stepping
            and additional_info.pydev_original_step_cmd in (CMD_STEP_INTO, CMD_STEP_INTO_MY_CODE)
            and not _global_notify_skipped_step_in
        ):
            _notify_skipped_step_in_because_of_filters(py_db, frame)

        if is_stepping:
            # Tracing may be needed for return value
            _enable_step_tracing(py_db, code, step_cmd, additional_info, frame)
            code_tracing_added = True
        return code_tracing_added

    if func_code_info.breakpoint_found or func_code_info.plugin_line_breakpoint_found:
        _enable_line_tracing(code)
        code_tracing_added = True

    if is_stepping:
        _enable_step_tracing(py_db, code, step_cmd, additional_info, frame)
        code_tracing_added = True

    return code_tracing_added


# fmt: off
# IFDEF CYTHON
# cdef _enable_step_tracing(py_db, code, step_cmd, PyDBAdditionalThreadInfo info, frame):
# ELSE
def _enable_step_tracing(py_db, code, step_cmd, info, frame):
# ENDIF
# fmt: on
    if step_cmd in (CMD_STEP_INTO, CMD_STEP_INTO_MY_CODE, CMD_STEP_INTO_COROUTINE, CMD_SMART_STEP_INTO):
        # Stepping (must have line/return tracing enabled).
        _enable_line_tracing(code)
        _enable_return_tracing(code)

    elif step_cmd in (CMD_STEP_RETURN, CMD_STEP_RETURN_MY_CODE) and _is_same_frame(info, info.pydev_step_stop, frame):
        _enable_return_tracing(code)

    elif step_cmd in (CMD_STEP_OVER, CMD_STEP_OVER_MY_CODE):
        if _is_same_frame(info, info.pydev_step_stop, frame):
            _enable_line_tracing(code)

            # Wee need to enable return tracing because if we have a return during a step over
            # we need to stop too.
            _enable_return_tracing(code)
        elif py_db.show_return_values and _is_same_frame(info, info.pydev_step_stop, frame.f_back):
            # Show return values on step over.
            _enable_return_tracing(code)


# fmt: off
# IFDEF CYTHON
# cdef class _TryExceptContainerObj:
#     cdef list try_except_infos
# ELSE
class _TryExceptContainerObj:
# ENDIF
# fmt: on
    """
    A dumb container object just to contain the try..except info when needed. Meant to be
    persistent among multiple PyDBFrames to the same code object.
    """

    # fmt: off
    # IFDEF CYTHON
    # def __init__(self, list try_except_infos):
    #     self.try_except_infos = try_except_infos
    # ELSE
    def __init__(self, try_except_infos):
        self.try_except_infos = try_except_infos

    # ENDIF
    # fmt: on


# fmt: off
# IFDEF CYTHON
# cdef _unwind_event(code, instruction, exc):
#     cdef ThreadInfo thread_info
#     cdef FuncCodeInfo func_code_info
# ELSE
def _unwind_event(code, instruction, exc):
# ENDIF
# fmt: on
    try:
        thread_info = _thread_local_info.thread_info
    except:
        thread_info = _get_thread_info(True, 1)
        if thread_info is None:
            return

    py_db: object = GlobalDebuggerHolder.global_dbg
    if py_db is None or py_db.pydb_disposed:
        return

    if not thread_info.trace or not thread_info.is_thread_alive():
        # For thread-related stuff we can't disable the code tracing because other
        # threads may still want it...
        return

    func_code_info: FuncCodeInfo = _get_func_code_info(code, 1)
    if func_code_info.always_skip_code:
        return

    # print('_unwind_event', code, exc)
    frame = _getframe(1)
    arg = (type(exc), exc, exc.__traceback__)

    has_caught_exception_breakpoint_in_pydb = (
        py_db.break_on_caught_exceptions or py_db.break_on_user_uncaught_exceptions or py_db.has_plugin_exception_breaks
    )

    if has_caught_exception_breakpoint_in_pydb:
        _should_stop, frame, user_uncaught_exc_info = should_stop_on_exception(
            py_db, thread_info.additional_info, frame, thread_info.thread, arg, None, is_unwind=True
        )
        if user_uncaught_exc_info:
            # TODO: Check: this may no longer be needed as in the unwind we know it's
            # an exception bubbling up (wait for all tests to pass to check it).
            if func_code_info.try_except_container_obj is None:
                container_obj = _TryExceptContainerObj(py_db.collect_try_except_info(frame.f_code))
                func_code_info.try_except_container_obj = container_obj

            is_unhandled = is_unhandled_exception(
                func_code_info.try_except_container_obj, py_db, frame, user_uncaught_exc_info[1], user_uncaught_exc_info[2]
            )

            if is_unhandled:
                handle_exception(py_db, thread_info.thread, frame, user_uncaught_exc_info[0], EXCEPTION_TYPE_USER_UNHANDLED)
                return

    break_on_uncaught_exceptions = py_db.break_on_uncaught_exceptions
    if break_on_uncaught_exceptions:
        if frame is _get_unhandled_exception_frame(exc, 1):
            stop_on_unhandled_exception(py_db, thread_info.thread, thread_info.additional_info, arg)
            return


# fmt: off
# IFDEF CYTHON
# cdef _raise_event(code, instruction, exc):
#     cdef ThreadInfo thread_info
#     cdef FuncCodeInfo func_code_info
# ELSE
def _raise_event(code, instruction, exc):
# ENDIF
# fmt: on
    """
    The way this should work is the following: when the user is using
    pydevd to do the launch and we're on a managed stack, we should consider
    unhandled only if it gets into a pydevd. If it's a thread, if it stops
    inside the threading and if it's an unmanaged thread (i.e.: QThread)
    then stop if it doesn't have a back frame.

    Note: unlike other events, this one is global and not per-code (so,
    it cannot be individually enabled/disabled for a given code object).
    """
    try:
        thread_info = _thread_local_info.thread_info
    except:
        thread_info = _get_thread_info(True, 1)
        if thread_info is None:
            return
        
    py_db: object = GlobalDebuggerHolder.global_dbg
    if py_db is None or py_db.pydb_disposed:
        return

    if not thread_info.trace or not thread_info.is_thread_alive():
        # For thread-related stuff we can't disable the code tracing because other
        # threads may still want it...
        return

    func_code_info: FuncCodeInfo = _get_func_code_info(code, 1)
    if func_code_info.always_skip_code:
        return

    frame = _getframe(1)
    arg = (type(exc), exc, exc.__traceback__)

    # Compute the previous exception info (if any). We use it to check if the exception
    # should be stopped
    prev_exc_info = _thread_local_info._user_uncaught_exc_info if hasattr(_thread_local_info, "_user_uncaught_exc_info") else None
    should_stop, frame, _user_uncaught_exc_info = should_stop_on_exception(
        py_db, thread_info.additional_info, frame, thread_info.thread, arg, prev_exc_info
    )

    # Save the current exception info for the next raise event.
    _thread_local_info._user_uncaught_exc_info = _user_uncaught_exc_info

    # print('!!!! should_stop (in raise)', should_stop)
    if should_stop:
        handle_exception(py_db, thread_info.thread, frame, arg, EXCEPTION_TYPE_HANDLED)


# fmt: off
# IFDEF CYTHON
# cdef str get_func_name(frame):
#     cdef str func_name
# ELSE
def get_func_name(frame):
# ENDIF
# fmt: on
    code_obj = frame.f_code
    func_name = code_obj.co_name
    try:
        cls_name = get_clsname_for_code(code_obj, frame)
        if cls_name is not None:
            return "%s.%s" % (cls_name, func_name)
        else:
            return func_name
    except:
        pydev_log.exception()
        return func_name


# fmt: off
# IFDEF CYTHON
# cdef _show_return_values(frame, arg):
# ELSE
def _show_return_values(frame, arg):
# ENDIF
# fmt: on
    try:
        try:
            f_locals_back = getattr(frame.f_back, "f_locals", None)
            if f_locals_back is not None:
                return_values_dict = f_locals_back.get(RETURN_VALUES_DICT, None)
                if return_values_dict is None:
                    return_values_dict = {}
                    f_locals_back[RETURN_VALUES_DICT] = return_values_dict
                name = get_func_name(frame)
                return_values_dict[name] = arg
        except:
            pydev_log.exception()
    finally:
        f_locals_back = None


# fmt: off
# IFDEF CYTHON
# cdef _remove_return_values(py_db, frame):
# ELSE
def _remove_return_values(py_db, frame):
# ENDIF
# fmt: on
    try:
        try:
            # Showing return values was turned off, we should remove them from locals dict.
            # The values can be in the current frame or in the back one
            frame.f_locals.pop(RETURN_VALUES_DICT, None)

            f_locals_back = getattr(frame.f_back, "f_locals", None)
            if f_locals_back is not None:
                f_locals_back.pop(RETURN_VALUES_DICT, None)
        except:
            pydev_log.exception()
    finally:
        f_locals_back = None


# fmt: off
# IFDEF CYTHON
# cdef _return_event(code, instruction, retval):
#     cdef ThreadInfo thread_info
#     cdef FuncCodeInfo func_code_info
#     cdef PyDBAdditionalThreadInfo info
#     cdef int step_cmd
# ELSE
def _return_event(code, instruction, retval):
# ENDIF
# fmt: on
    try:
        thread_info = _thread_local_info.thread_info
    except:
        thread_info = _get_thread_info(True, 1)
        if thread_info is None:
            return

    py_db: object = GlobalDebuggerHolder.global_dbg
    if py_db is None or py_db.pydb_disposed:
        return monitor.DISABLE

    if not thread_info.trace or not thread_info.is_thread_alive():
        # For thread-related stuff we can't disable the code tracing because other
        # threads may still want it...
        return

    func_code_info: FuncCodeInfo = _get_func_code_info(code, 1)
    if func_code_info.always_skip_code:
        return monitor.DISABLE

    info = thread_info.additional_info

    # We know the frame depth.
    frame = _getframe(1)

    step_cmd = info.pydev_step_cmd
    if step_cmd == -1:
        return

    if info.suspend_type != PYTHON_SUSPEND:
        # Plugin stepping
        if func_code_info.plugin_return_stepping:
            _plugin_stepping(py_db, step_cmd, "return", frame, thread_info)
        return
    
    if info.pydev_state == STATE_SUSPEND:
        # We're already suspended, don't handle any more events on this thread.
        _do_wait_suspend(py_db, thread_info, frame, "return", None)
        return
    
    # Python line stepping
    stop_frame = info.pydev_step_stop
    if step_cmd in (CMD_STEP_INTO, CMD_STEP_INTO_MY_CODE, CMD_STEP_INTO_COROUTINE):
        force_check_project_scope = step_cmd == CMD_STEP_INTO_MY_CODE
        if frame.f_back is not None and not info.pydev_use_scoped_step_frame:
            back_func_code_info = _get_func_code_info(frame.f_back.f_code, frame.f_back)
            if (
                # Not filtered out.
                not back_func_code_info.always_skip_code
                and not back_func_code_info.always_filtered_out
                and not (force_check_project_scope and back_func_code_info.filtered_out_force_checked)
                # Prevent stopping in a return to the same location we were initially
                # (i.e.: double-stop at the same place due to some filtering).
                and info.step_in_initial_location != (frame.f_back, frame.f_back.f_lineno)
            ):
                if py_db.show_return_values:
                    _show_return_values(frame, retval)

                _stop_on_return(py_db, thread_info, info, step_cmd, frame, retval)
                return

    if step_cmd in (CMD_STEP_RETURN, CMD_STEP_RETURN_MY_CODE) and _is_same_frame(info, stop_frame, frame):
        if py_db.show_return_values:
            _show_return_values(frame, retval)

        _stop_on_return(py_db, thread_info, info, step_cmd, frame, retval)
        return

    elif (
        step_cmd in (CMD_STEP_OVER, CMD_STEP_OVER_MY_CODE)
        and not info.pydev_use_scoped_step_frame
        and _is_same_frame(info, stop_frame, frame)
    ):
        # This isn't in the sys.settrace version: on a step over, if we return and the return is valid, show
        # as a step return instead of going back to step into mode (but if the back frame is not valid, then
        # go to step into mode).
        f_back = frame.f_back
        if f_back is not None:
            back_func_code_info = _get_func_code_info(f_back.f_code, 2)
            force_check_project_scope = step_cmd == CMD_STEP_OVER_MY_CODE

            if (
                back_func_code_info is not None
                and not back_func_code_info.always_skip_code
                and not back_func_code_info.always_filtered_out
                and not (force_check_project_scope and back_func_code_info.filtered_out_force_checked)
            ):
                if py_db.show_return_values:
                    _show_return_values(frame, retval)

                _stop_on_return(py_db, thread_info, info, step_cmd, frame, retval)
                return

    elif step_cmd == CMD_SMART_STEP_INTO:
        if _is_same_frame(info, stop_frame, frame):
            # We're exiting the smart step into initial frame (so, we probably didn't find our target).
            if py_db.show_return_values:
                _show_return_values(frame, retval)

            _stop_on_return(py_db, thread_info, info, step_cmd, frame, retval)
            return

    if py_db.show_return_values:
        if (
            (
                info.pydev_step_cmd in (CMD_STEP_OVER, CMD_STEP_OVER_MY_CODE, CMD_SMART_STEP_INTO)
                and (_is_same_frame(info, stop_frame, frame.f_back))
            )
            or (info.pydev_step_cmd in (CMD_STEP_RETURN, CMD_STEP_RETURN_MY_CODE) and (info, _is_same_frame(info, stop_frame, frame)))
            or (info.pydev_step_cmd in (CMD_STEP_INTO, CMD_STEP_INTO_COROUTINE))
            or (
                info.pydev_step_cmd == CMD_STEP_INTO_MY_CODE
                and frame.f_back is not None
                and not py_db.apply_files_filter(frame.f_back, frame.f_back.f_code.co_filename, True)
            )
        ):
            _show_return_values(frame, retval)

    if step_cmd in (CMD_STEP_OVER, CMD_STEP_RETURN, CMD_STEP_OVER_MY_CODE, CMD_STEP_RETURN_MY_CODE, CMD_SMART_STEP_INTO):
        # If we are in single step mode and something causes us to exit the current frame, we need to make sure we break
        # eventually.  Force the step mode to step into and the step stop frame to None.
        # I.e.: F6 in the end of a function should stop in the next possible position (instead of forcing the user
        # to make a step in or step over at that location).
        # Note: this is especially troublesome when we're skipping code with the
        # @DontTrace comment.
        stop_frame = info.pydev_step_stop
        if stop_frame is frame and not info.pydev_use_scoped_step_frame:
            if step_cmd in (CMD_STEP_OVER, CMD_STEP_RETURN, CMD_SMART_STEP_INTO):
                info.pydev_step_cmd = CMD_STEP_INTO
            else:
                info.pydev_step_cmd = CMD_STEP_INTO_MY_CODE
            info.pydev_step_stop = None
            _enable_code_tracing_for_frame_and_parents(thread_info, stop_frame.f_back)
            if py_db.show_return_values:
                _show_return_values(frame, retval)


# fmt: off
# IFDEF CYTHON
# cdef _enable_code_tracing_for_frame_and_parents(ThreadInfo thread_info, frame):
#     cdef FuncCodeInfo func_code_info
# ELSE
def _enable_code_tracing_for_frame_and_parents(thread_info, frame):
# ENDIF
# fmt: on
    py_db: object = GlobalDebuggerHolder.global_dbg
    if py_db is None or py_db.pydb_disposed:
        return

    while frame is not None:
        func_code_info: FuncCodeInfo = _get_func_code_info(frame.f_code, frame)
        if func_code_info.always_skip_code:
            frame = frame.f_back
            continue

        _enable_code_tracing(py_db, thread_info.additional_info, func_code_info, frame.f_code, frame, False)
        frame = frame.f_back


# fmt: off
# IFDEF CYTHON
# cdef _stop_on_return(py_db, ThreadInfo thread_info, PyDBAdditionalThreadInfo info, int step_cmd, frame, retval):
# ELSE
def _stop_on_return(py_db, thread_info, info, step_cmd, frame, retval):
# ENDIF
# fmt: on
    back = frame.f_back
    if back is not None:
        # When we get to the pydevd run function, the debugging has actually finished for the main thread
        # (note that it can still go on for other threads, but for this one, we just make it finish)
        # So, just setting it to None should be OK
        back_absolute_filename, _, base = get_abs_path_real_path_and_base_from_frame(back)
        if (base, back.f_code.co_name) in (DEBUG_START, DEBUG_START_PY3K):
            back = None

        elif base == TRACE_PROPERTY:
            # We dont want to trace the return event of pydevd_traceproperty (custom property for debugging)
            # if we're in a return, we want it to appear to the user in the previous frame!
            return

        elif pydevd_dont_trace.should_trace_hook is not None:
            if not pydevd_dont_trace.should_trace_hook(back.f_code, back_absolute_filename):
                # In this case, we'll have to skip the previous one because it shouldn't be traced.
                # Also, we have to reset the tracing, because if the parent's parent (or some
                # other parent) has to be traced and it's not currently, we wouldn't stop where
                # we should anymore (so, a step in/over/return may not stop anywhere if no parent is traced).
                # Related test: _debugger_case17a.py
                py_db.set_trace_for_frame_and_parents(thread_info.thread_ident, back)
                return

    if back is not None:
        # if we're in a return, we want it to appear to the user in the previous frame!
        py_db.set_suspend(thread_info.thread, step_cmd, original_step_cmd=info.pydev_original_step_cmd)
        _do_wait_suspend(py_db, thread_info, back, "return", retval)
    else:
        # in jython we may not have a back frame
        info.pydev_step_stop = None
        info.pydev_original_step_cmd = -1
        info.pydev_step_cmd = -1
        info.pydev_state = STATE_RUN
        info.update_stepping_info()


# fmt: off
# IFDEF CYTHON
# cdef _stop_on_breakpoint(py_db, ThreadInfo thread_info, int stop_reason, bp, frame, new_frame, bint stop, bint stop_on_plugin_breakpoint, str bp_type):
#     cdef PyDBAdditionalThreadInfo additional_info
# ELSE
def _stop_on_breakpoint(
    py_db, thread_info: ThreadInfo, stop_reason: int, bp, frame, new_frame, stop: bool, stop_on_plugin_breakpoint: bool, bp_type: str
):
# ENDIF
# fmt: on
    """
    :param bp: the breakpoint hit (additional conditions will be checked now).
    :param frame: the actual frame
    :param new_frame: either the actual frame or the frame provided by the plugins.
    :param stop: whether we should do a regular line breakpoint.
    :param stop_on_plugin_breakpoint: whether we should stop in a plugin breakpoint.

    :return:
        True if the breakpoint was suspended inside this function and False otherwise.
        Note that even if False is returned, it's still possible
    """
    additional_info = thread_info.additional_info
    # ok, hit breakpoint, now, we have to discover if it is a conditional breakpoint
    # lets do the conditional stuff here
    if bp.expression is not None:
        # If it has an expression, it's always handled even if we don't stop.
        py_db.handle_breakpoint_expression(bp, additional_info, new_frame)

    if stop or stop_on_plugin_breakpoint:
        if bp.has_condition:
            eval_result = py_db.handle_breakpoint_condition(additional_info, bp, new_frame)
            if not eval_result:
                stop = False
                stop_on_plugin_breakpoint = False

    # Handle logpoint (on a logpoint we should never stop).
    if (stop or stop_on_plugin_breakpoint) and bp.is_logpoint:
        stop = False
        stop_on_plugin_breakpoint = False

        if additional_info.pydev_message is not None and len(additional_info.pydev_message) > 0:
            cmd = py_db.cmd_factory.make_io_message(additional_info.pydev_message + os.linesep, "1")
            py_db.writer.add_command(cmd)

    if stop:
        py_db.set_suspend(
            thread_info.thread,
            stop_reason,
            suspend_other_threads=bp and bp.suspend_policy == "ALL",
        )
        # print('suspend on breakpoint...')
        _do_wait_suspend(py_db, thread_info, frame, "line", None)
        return True

    elif stop_on_plugin_breakpoint:
        stop_at_frame = py_db.plugin.suspend(py_db, thread_info.thread, frame, bp_type)
        if stop_at_frame and thread_info.additional_info.pydev_state == STATE_SUSPEND:
            _do_wait_suspend(py_db, thread_info, stop_at_frame, "line", None)
        return

    return False


# fmt: off
# IFDEF CYTHON
# cdef _plugin_stepping(py_db, int step_cmd, event, frame, ThreadInfo thread_info):
#     cdef bint stop
#     cdef dict stop_info
# ELSE
def _plugin_stepping(py_db, step_cmd, event, frame, thread_info):
# ENDIF
# fmt: on
    plugin_manager = py_db.plugin
    # Step return makes no sense for plugins (I guess?!?), so, just handle as step into.
    if step_cmd in (CMD_STEP_INTO, CMD_STEP_INTO_MY_CODE, CMD_STEP_INTO_COROUTINE, CMD_SMART_STEP_INTO) or step_cmd in (
        CMD_STEP_RETURN,
        CMD_STEP_RETURN_MY_CODE,
    ):
        stop_info = {}
        stop = False
        result = plugin_manager.cmd_step_into(py_db, frame, event, thread_info.additional_info, thread_info.thread, stop_info, stop)
        if result:
            stop, plugin_stop = result
            if plugin_stop:
                plugin_manager.stop(py_db, frame, event, thread_info.thread, stop_info, None, step_cmd)
                return

    elif step_cmd in (CMD_STEP_OVER, CMD_STEP_OVER_MY_CODE):
        if plugin_manager is not None:
            stop_info = {}
            stop = False
            result = plugin_manager.cmd_step_over(py_db, frame, event, thread_info.additional_info, thread_info.thread, stop_info, stop)
            if result:
                stop, plugin_stop = result
                if plugin_stop:
                    plugin_manager.stop(py_db, frame, event, thread_info.thread, stop_info, None, step_cmd)
                    return


# fmt: off
# IFDEF CYTHON
# cdef _jump_event(code, int from_offset, int to_offset):
#     cdef ThreadInfo thread_info
#     cdef FuncCodeInfo func_code_info
#     cdef int from_line
#     cdef int to_line
# ELSE
def _jump_event(code, from_offset, to_offset):
# ENDIF
# fmt: on
    # A bunch of things have to be repeated especially because in the sys.monitoring
    # everything is global, yet, when we start tracing something for stepping that
    # needs to be per-thread.
    try:
        thread_info = _thread_local_info.thread_info
    except:
        thread_info = _get_thread_info(True, 1)
        if thread_info is None:
            return

    py_db: object = GlobalDebuggerHolder.global_dbg
    if py_db is None or py_db.pydb_disposed:
        return monitor.DISABLE

    # If we get another jump event, remove the extra check for the line event
    if hasattr(_thread_local_info, "f_disable_next_line_if_match"):
        del _thread_local_info.f_disable_next_line_if_match

    if not thread_info.trace or not thread_info.is_thread_alive():
        # For thread-related stuff we can't disable the code tracing because other
        # threads may still want it...
        return

    func_code_info: FuncCodeInfo = _get_func_code_info(code, 1)
    if func_code_info.always_skip_code or func_code_info.always_filtered_out:
        return monitor.DISABLE

    # Same logic as "sys_trace_jump_func" in https://github.com/python/cpython/blob/main/Python/legacy_tracing.c

    # Ignore forward jump.
    # print('jump event', code.co_name, 'from offset', from_offset, 'to offset', to_offset)
    if to_offset > from_offset:
        return monitor.DISABLE

    from_line = func_code_info.get_line_of_offset(from_offset or 0)
    to_line = func_code_info.get_line_of_offset(to_offset or 0)

    if from_line != to_line:
        # I.e.: use case: "yield from [j for j in a if j % 2 == 0]"
        return monitor.DISABLE

    # We know the frame depth.
    frame = _getframe(1)

    # Disable the next line event as we're jumping to a line. The line event will be redundant.
    _thread_local_info.f_disable_next_line_if_match = (func_code_info.co_filename, frame.f_lineno)
    # pydev_log.debug('_jump_event', code.co_name, 'from line', from_line, 'to line', frame.f_lineno)

    return _internal_line_event(func_code_info, frame, frame.f_lineno)


# fmt: off
# IFDEF CYTHON
# cdef _line_event(code, int line):
#     cdef ThreadInfo thread_info
#     cdef FuncCodeInfo func_code_info
# ELSE
def _line_event(code, line):
# ENDIF
# fmt: on

    # A bunch of things have to be repeated especially because in the sys.monitoring
    # everything is global, yet, when we start tracing something for stepping that
    # needs to be per-thread.
    try:
        thread_info = _thread_local_info.thread_info
    except:
        thread_info = _get_thread_info(True, 1)
        if thread_info is None:
            return

    py_db: object = GlobalDebuggerHolder.global_dbg
    if py_db is None or py_db.pydb_disposed:
        return monitor.DISABLE

    # If we get another line event, remove the extra check for the line event
    if hasattr(_thread_local_info, "f_disable_next_line_if_match"):
        (co_filename, line_to_skip) = _thread_local_info.f_disable_next_line_if_match
        del _thread_local_info.f_disable_next_line_if_match
        if line_to_skip is line and co_filename == code.co_filename:
            # The last jump already jumped to this line and we haven't had any
            # line events or jumps since then. We don't want to consider this line twice
            # pydev_log.debug('_line_event skipped', line)
            return

    if not thread_info.trace or not thread_info.is_thread_alive():
        # For thread-related stuff we can't disable the code tracing because other
        # threads may still want it...
        return
    
    func_code_info: FuncCodeInfo = _get_func_code_info(code, 1)
    if func_code_info.always_skip_code or func_code_info.always_filtered_out:
        return monitor.DISABLE

    # pydev_log.debug('_line_event', code.co_name, line)

    # We know the frame depth.
    frame = _getframe(1)
    return _internal_line_event(func_code_info, frame, line)


# fmt: off
# IFDEF CYTHON
# cdef _internal_line_event(FuncCodeInfo func_code_info, frame, int line):
#     cdef ThreadInfo thread_info
#     cdef PyDBAdditionalThreadInfo info
#     cdef int step_cmd
#     cdef bint stop
#     cdef bint stop_on_plugin_breakpoint
#     cdef int stop_reason
#     cdef bint force_check_project_scope
# ELSE
def _internal_line_event(func_code_info, frame, line):
# ENDIF
# fmt: on
    py_db: object = GlobalDebuggerHolder.global_dbg
    thread_info = _thread_local_info.thread_info
    info = thread_info.additional_info

    step_cmd = info.pydev_step_cmd

    # print('line event', info, id(info), thread_info.thread.name)
    # print('line event', info.pydev_state, line, threading.current_thread(), code)
    # If we reached here, it was not filtered out.

    if func_code_info.breakpoint_found:
        bp = None
        stop = False
        stop_on_plugin_breakpoint = False

        stop_info = {}
        stop_reason = CMD_SET_BREAK
        bp_type = None

        bp = func_code_info.bp_line_to_breakpoint.get(line)
        if bp is not None:
            new_frame = frame
            stop = True

        if bp:
            if _stop_on_breakpoint(py_db, thread_info, stop_reason, bp, frame, new_frame, stop, stop_on_plugin_breakpoint, "python-line"):
                return

    if func_code_info.plugin_line_breakpoint_found:
        result = py_db.plugin.get_breakpoint(py_db, frame, "line", info)
        if result:
            stop_reason = CMD_SET_BREAK
            stop = False
            stop_on_plugin_breakpoint = True
            bp, new_frame, bp_type = result
            _stop_on_breakpoint(py_db, thread_info, stop_reason, bp, frame, new_frame, stop, stop_on_plugin_breakpoint, bp_type)
            return

    if info.pydev_state == STATE_SUSPEND:
        # Note: it's possible that it was suspended with a pause (and we'd stop here too).
        # print('suspend (pause)...')
        _do_wait_suspend(py_db, thread_info, frame, "line", None)
        return

    # Ok, did not suspend due to a breakpoint, let's see if we're stepping.
    stop_frame = info.pydev_step_stop
    if step_cmd == -1:
        if func_code_info.breakpoint_found or func_code_info.plugin_line_breakpoint_found or any_thread_stepping():
            return None

        return monitor.DISABLE

    if info.suspend_type != PYTHON_SUSPEND:
        # Plugin stepping
        if func_code_info.plugin_line_stepping:
            _plugin_stepping(py_db, step_cmd, "line", frame, thread_info)
        return

    # Python stepping now
    if step_cmd in (CMD_STEP_INTO, CMD_STEP_INTO_MY_CODE, CMD_STEP_INTO_COROUTINE):
        force_check_project_scope = step_cmd == CMD_STEP_INTO_MY_CODE
        if not info.pydev_use_scoped_step_frame:
            if func_code_info.always_filtered_out or (force_check_project_scope and func_code_info.filtered_out_force_checked):
                return

            py_db.set_suspend(thread_info.thread, step_cmd, original_step_cmd=info.pydev_original_step_cmd)
            _do_wait_suspend(py_db, thread_info, frame, "line", None)
            return
        else:
            # Make sure we check the filtering inside ipython calls too...
            if func_code_info.always_filtered_out or (force_check_project_scope and func_code_info.filtered_out_force_checked):
                return

            stop = False
            # We can only stop inside the ipython call.
            filename = frame.f_code.co_filename
            if filename.endswith(".pyc"):
                filename = filename[:-1]

            if not filename.endswith(PYDEVD_IPYTHON_CONTEXT[0]):
                f = frame.f_back
                while f is not None:
                    if f.f_code.co_name == PYDEVD_IPYTHON_CONTEXT[1]:
                        f2 = f.f_back
                        if f2 is not None and f2.f_code.co_name == PYDEVD_IPYTHON_CONTEXT[2]:
                            pydev_log.debug("Stop inside ipython call")
                            py_db.set_suspend(thread_info.thread, step_cmd, original_step_cmd=info.pydev_original_step_cmd)
                            thread_info.additional_info.trace_suspend_type = "sys_monitor"
                            _do_wait_suspend(py_db, thread_info, frame, "line", None)
                            break
                    f = f.f_back

                del f

        # In scoped mode if step in didn't work in this context it won't work
        # afterwards anyways.
        return

    elif step_cmd in (CMD_STEP_OVER, CMD_STEP_OVER_MY_CODE):
        # Note: when dealing with a step over my code it's the same as a step over (the
        # difference is that when we return from a frame in one we go to regular step
        # into and in the other we go to a step into my code).
        if _is_same_frame(info, stop_frame, frame):
            py_db.set_suspend(thread_info.thread, step_cmd, original_step_cmd=info.pydev_original_step_cmd)
            _do_wait_suspend(py_db, thread_info, frame, "line", None)
            return

    elif step_cmd == CMD_SMART_STEP_INTO:
        stop = False
        back = frame.f_back
        if _is_same_frame(info, stop_frame, back):
            if info.pydev_smart_child_offset != -1:
                # i.e.: in this case, we're not interested in the pause in the parent, rather
                # we're interested in the pause in the child (when the parent is at the proper place).
                stop = False

            else:
                pydev_smart_parent_offset = info.pydev_smart_parent_offset

                pydev_smart_step_into_variants = info.pydev_smart_step_into_variants
                if pydev_smart_parent_offset >= 0 and pydev_smart_step_into_variants:
                    # Preferred mode (when the smart step into variants are available
                    # and the offset is set).
                    stop = get_smart_step_into_variant_from_frame_offset(
                        back.f_lasti, pydev_smart_step_into_variants
                    ) is get_smart_step_into_variant_from_frame_offset(pydev_smart_parent_offset, pydev_smart_step_into_variants)

                else:
                    # Only the name/line is available, so, check that.
                    curr_func_name = frame.f_code.co_name

                    # global context is set with an empty name
                    if curr_func_name in ("?", "<module>") or curr_func_name is None:
                        curr_func_name = ""
                    if curr_func_name == info.pydev_func_name and stop_frame.f_lineno == info.pydev_next_line:
                        stop = True

            if not stop:
                # In smart step into, if we didn't hit it in this frame once, that'll
                # not be the case next time either, so, disable tracing for this frame.
                return

        elif back is not None and _is_same_frame(info, stop_frame, back.f_back):
            # Ok, we have to track 2 stops at this point, the parent and the child offset.
            # This happens when handling a step into which targets a function inside a list comprehension
            # or generator (in which case an intermediary frame is created due to an internal function call).
            pydev_smart_parent_offset = info.pydev_smart_parent_offset
            pydev_smart_child_offset = info.pydev_smart_child_offset
            # print('matched back frame', pydev_smart_parent_offset, pydev_smart_child_offset)
            # print('parent f_lasti', back.f_back.f_lasti)
            # print('child f_lasti', back.f_lasti)
            stop = False
            if pydev_smart_child_offset >= 0 and pydev_smart_child_offset >= 0:
                pydev_smart_step_into_variants = info.pydev_smart_step_into_variants

                if pydev_smart_parent_offset >= 0 and pydev_smart_step_into_variants:
                    # Note that we don't really check the parent offset, only the offset of
                    # the child (because this is a generator, the parent may have moved forward
                    # already -- and that's ok, so, we just check that the parent frame
                    # matches in this case).
                    smart_step_into_variant = get_smart_step_into_variant_from_frame_offset(
                        pydev_smart_parent_offset, pydev_smart_step_into_variants
                    )
                    # print('matched parent offset', pydev_smart_parent_offset)
                    # Ok, now, check the child variant
                    children_variants = smart_step_into_variant.children_variants
                    stop = children_variants and (
                        get_smart_step_into_variant_from_frame_offset(back.f_lasti, children_variants)
                        is get_smart_step_into_variant_from_frame_offset(pydev_smart_child_offset, children_variants)
                    )
                    # print('stop at child', stop)

            if not stop:
                # In smart step into, if we didn't hit it in this frame once, that'll
                # not be the case next time either, so, disable tracing for this frame.
                return

        if stop:
            py_db.set_suspend(thread_info.thread, step_cmd, original_step_cmd=info.pydev_original_step_cmd)
            _do_wait_suspend(py_db, thread_info, frame, "line", None)
            return


# fmt: off
# IFDEF CYTHON
# cdef _start_method_event(code, instruction_offset):
#     cdef ThreadInfo thread_info
#     cdef FuncCodeInfo func_code_info
#     cdef bint stop
#     cdef int stop_reason
#     cdef bint stop_on_plugin_breakpoint
#     cdef PyDBAdditionalThreadInfo info
#     cdef int step_cmd
#     cdef bint code_tracing_added
# ELSE
def _start_method_event(code, instruction_offset):
# ENDIF
# fmt: on
    try:
        thread_info = _thread_local_info.thread_info
    except:
        thread_info = _get_thread_info(True, 1)
        if thread_info is None:
            return

    py_db: object = GlobalDebuggerHolder.global_dbg
    if py_db is None or py_db.pydb_disposed:
        return monitor.DISABLE

    if not thread_info.trace or not thread_info.is_thread_alive():
        # For thread-related stuff we can't disable the code tracing because other
        # threads may still want it...
        return

    frame = _getframe(1)
    func_code_info = _get_func_code_info(code, frame)
    if func_code_info.always_skip_code:
        # if DEBUG:
        #     print('disable (always skip)')
        return monitor.DISABLE

    keep_enabled: bool = _enable_code_tracing(py_db, thread_info.additional_info, func_code_info, code, frame, True)

    if func_code_info.function_breakpoint_found:
        bp = func_code_info.function_breakpoint
        stop = True
        new_frame = frame
        stop_reason = CMD_SET_FUNCTION_BREAK
        stop_on_plugin_breakpoint = False

        _stop_on_breakpoint(py_db, thread_info, stop_reason, bp, frame, new_frame, stop, stop_on_plugin_breakpoint, "python-function")
        return

    if py_db.plugin:
        plugin_manager = py_db.plugin

        # Check breaking on breakpoints in a 'call'
        info = thread_info.additional_info
        if func_code_info.plugin_call_breakpoint_found:
            result = plugin_manager.get_breakpoint(py_db, frame, "call", info)
            if result:
                stop_reason = CMD_SET_BREAK
                stop = False
                stop_on_plugin_breakpoint = True
                bp, new_frame, bp_type = result
                _stop_on_breakpoint(py_db, thread_info, stop_reason, bp, frame, new_frame, stop, stop_on_plugin_breakpoint, bp_type)
                return

            keep_enabled = True

        # Check breaking on line stepping in a 'call'
        step_cmd = info.pydev_step_cmd
        if step_cmd != -1 and func_code_info.plugin_call_stepping and info.suspend_type != PYTHON_SUSPEND:
            _plugin_stepping(py_db, step_cmd, "call", frame, thread_info)
            return

    if keep_enabled or any_thread_stepping():
        return None

    return monitor.DISABLE


# fmt: off
# IFDEF CYTHON
# cpdef _ensure_monitoring():
# ELSE
def _ensure_monitoring():
# ENDIF
# fmt: on
    DEBUGGER_ID = monitor.DEBUGGER_ID
    if not monitor.get_tool(DEBUGGER_ID):
        monitor.use_tool_id(DEBUGGER_ID, "pydevd")
        update_monitor_events()
        restart_events()


# fmt: off
# IFDEF CYTHON
# cpdef start_monitoring(bint all_threads=False):
#     cdef ThreadInfo thread_info
# ELSE
def start_monitoring(all_threads=False):
# ENDIF
# fmt: on
    if all_threads:
        # print('start monitoring, all_threads=', all_threads)
        DEBUGGER_ID = monitor.DEBUGGER_ID
        if not monitor.get_tool(DEBUGGER_ID):
            monitor.use_tool_id(DEBUGGER_ID, "pydevd")
            update_monitor_events()
            restart_events()
    else:
        try:
            thread_info = _thread_local_info.thread_info
        except:
            # code=None means we can already get the threading.current_thread.
            thread_info = _get_thread_info(True, 1)
            if thread_info is None:
                # print('start monitoring, thread=', None)
                return
        # print('start monitoring, thread=', thread_info.thread)
        thread_info.trace = True


# fmt: off
# IFDEF CYTHON
# cpdef stop_monitoring(all_threads=False):
#     cdef ThreadInfo thread_info
# ELSE
def stop_monitoring(all_threads=False):
# ENDIF
# fmt: on
    if all_threads:
        # print('stop monitoring, all_threads=', all_threads)
        if monitor.get_tool(monitor.DEBUGGER_ID) == "pydevd":
            monitor.set_events(monitor.DEBUGGER_ID, 0)
            monitor.register_callback(DEBUGGER_ID, monitor.events.PY_START, None)
            monitor.register_callback(DEBUGGER_ID, monitor.events.PY_RESUME, None)
            monitor.register_callback(DEBUGGER_ID, monitor.events.LINE, None)
            monitor.register_callback(DEBUGGER_ID, monitor.events.JUMP, None)
            monitor.register_callback(DEBUGGER_ID, monitor.events.PY_RETURN, None)
            monitor.register_callback(DEBUGGER_ID, monitor.events.RAISE, None)
            monitor.free_tool_id(monitor.DEBUGGER_ID)
    else:
        try:
            thread_info = _thread_local_info.thread_info
        except:
            thread_info = _get_thread_info(False, 1)
            if thread_info is None:
                return
        # print('stop monitoring, thread=', thread_info.thread)
        thread_info.trace = False


def update_monitor_events(suspend_requested: Optional[bool]=None) -> None:
    """
    This should be called when breakpoints change.

    :param suspend: means the user requested threads to be suspended
    """
    if monitor.get_tool(monitor.DEBUGGER_ID) != "pydevd":
        # It is still not initialized.
        return

    # When breakpoints change we need to update what we want to track based
    # on the breakpoints.
    py_db = GlobalDebuggerHolder.global_dbg
    if py_db is None:
        return

    if suspend_requested is None:
        suspend_requested = False

        for t in threading.enumerate():
            if getattr(t, "pydev_do_not_trace", False):
                continue
            try:
                additional_info = t.additional_info
                if additional_info is None:
                    # i.e.: if we don't have it then it makes no sense to check if it was suspended or is stepping
                    continue
            except AttributeError:
                continue
            if additional_info.pydev_step_cmd != -1 or additional_info.pydev_state == 2:
                suspend_requested = True
                break

    required_events = 0

    has_caught_exception_breakpoint_in_pydb = (
        py_db.break_on_caught_exceptions or py_db.break_on_user_uncaught_exceptions or py_db.has_plugin_exception_breaks
    )

    break_on_uncaught_exceptions = py_db.break_on_uncaught_exceptions

    if has_caught_exception_breakpoint_in_pydb:
        required_events |= monitor.events.RAISE | monitor.events.PY_UNWIND
        # print('track RAISE')
        monitor.register_callback(DEBUGGER_ID, monitor.events.RAISE, _raise_event)
        monitor.register_callback(DEBUGGER_ID, monitor.events.PY_UNWIND, _unwind_event)
    else:
        if break_on_uncaught_exceptions:
            required_events |= monitor.events.PY_UNWIND
            monitor.register_callback(DEBUGGER_ID, monitor.events.PY_UNWIND, _unwind_event)
        else:
            monitor.register_callback(DEBUGGER_ID, monitor.events.RAISE, None)
            monitor.register_callback(DEBUGGER_ID, monitor.events.PY_UNWIND, None)

    has_breaks = py_db.has_plugin_line_breaks
    if not has_breaks:
        if py_db.function_breakpoint_name_to_breakpoint:
            has_breaks = True
        else:
            file_to_line_to_breakpoints = py_db.breakpoints
            for line_to_breakpoints in file_to_line_to_breakpoints.values():
                if line_to_breakpoints:
                    has_breaks = True
                    break

    if has_breaks or suspend_requested:
        # print('track PY_START|PY_RESUME, suspend_requested=', suspend_requested)
        required_events |= monitor.events.PY_START | monitor.events.PY_RESUME

        monitor.register_callback(DEBUGGER_ID, monitor.events.PY_START, _start_method_event)
        # monitor.register_callback(DEBUGGER_ID, monitor.events.PY_RESUME, _resume_method_event)
        monitor.register_callback(DEBUGGER_ID, monitor.events.LINE, _line_event)
        if not IS_PY313_OR_GREATER:
            # In Python 3.13+ jump_events aren't necessary as we have a line_event for every
            # jump location. 
            monitor.register_callback(DEBUGGER_ID, monitor.events.JUMP, _jump_event)
        monitor.register_callback(DEBUGGER_ID, monitor.events.PY_RETURN, _return_event)

    else:
        monitor.register_callback(DEBUGGER_ID, monitor.events.PY_START, None)
        monitor.register_callback(DEBUGGER_ID, monitor.events.PY_RESUME, None)
        monitor.register_callback(DEBUGGER_ID, monitor.events.LINE, None)
        monitor.register_callback(DEBUGGER_ID, monitor.events.JUMP, None)
        monitor.register_callback(DEBUGGER_ID, monitor.events.PY_RETURN, None)

    monitor.set_events(DEBUGGER_ID, required_events)


def restart_events() -> None:
    # Note: if breakpoints change, update_monitor_events usually needs to be
    # called first, then the line event tracing must be set for existing frames
    # and then this function must be called at the end.
    monitor.restart_events()


# fmt: off
# IFDEF CYTHON
# cdef _is_same_frame(PyDBAdditionalThreadInfo info, target_frame, current_frame):
# ELSE
def _is_same_frame(info, target_frame, current_frame):
# ENDIF
# fmt: on
    if target_frame is current_frame:
        return True

    if info.pydev_use_scoped_step_frame:
        # If using scoped step we don't check the target, we just need to check
        # if the current matches the same heuristic where the target was defined.
        if target_frame is not None and current_frame is not None:
            if target_frame.f_code.co_filename == current_frame.f_code.co_filename:
                # The co_name may be different (it may include the line number), but
                # the filename must still be the same.
                f = current_frame.f_back
                if f is not None and f.f_code.co_name == PYDEVD_IPYTHON_CONTEXT[1]:
                    f = f.f_back
                    if f is not None and f.f_code.co_name == PYDEVD_IPYTHON_CONTEXT[2]:
                        return True

    return False


# fmt: off
# IFDEF CYTHON
# def _do_wait_suspend(py_db, ThreadInfo thread_info, frame, event, arg):
# ELSE
def _do_wait_suspend(py_db, thread_info, frame, event, arg):
# ENDIF
# fmt: on
    thread_info.additional_info.trace_suspend_type = "sys_monitor"
    py_db.do_wait_suspend(thread_info.thread, frame, event, arg)

# This can be used to diagnose exceptions inside of the debugger itself.
#
# import types
# import functools
#
#
# def safe_func(method):
#
#     @functools.wraps(method)
#     def new_method(*args, **kwargs):
#         try:
#             return method(*args, **kwargs)
#         except:
#             import traceback;traceback.print_exc()
#             raise
#
#     return new_method
#
#
# for name, obj in list(globals().items()):
#     if name.endswith('_event'):
#         if isinstance(obj, types.FunctionType):
#             globals()[name] = safe_func(obj)
#
#
# def _getframe(depth):
#     return sys._getframe(depth + 1)

# === NexusCore/openenv\Lib\site-packages\googleapiclient\http.py ===
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

"""Classes to encapsulate a single HTTP request.

The classes implement a command pattern, with every
object supporting an execute() method that does the
actual HTTP request.
"""
from __future__ import absolute_import

__author__ = "jcgregorio@google.com (Joe Gregorio)"

import copy
import http.client as http_client
import io
import json
import logging
import mimetypes
import os
import random
import socket
import time
import urllib
import uuid

import httplib2

# TODO(issue 221): Remove this conditional import jibbajabba.
try:
    import ssl
except ImportError:
    _ssl_SSLError = object()
else:
    _ssl_SSLError = ssl.SSLError

from email.generator import Generator
from email.mime.multipart import MIMEMultipart
from email.mime.nonmultipart import MIMENonMultipart
from email.parser import FeedParser

from googleapiclient import _auth
from googleapiclient import _helpers as util
from googleapiclient.errors import (
    BatchError,
    HttpError,
    InvalidChunkSizeError,
    ResumableUploadError,
    UnexpectedBodyError,
    UnexpectedMethodError,
)
from googleapiclient.model import JsonModel

LOGGER = logging.getLogger(__name__)

DEFAULT_CHUNK_SIZE = 100 * 1024 * 1024

MAX_URI_LENGTH = 2048

MAX_BATCH_LIMIT = 1000

_TOO_MANY_REQUESTS = 429

DEFAULT_HTTP_TIMEOUT_SEC = 60

_LEGACY_BATCH_URI = "https://www.googleapis.com/batch"


def _should_retry_response(resp_status, content):
    """Determines whether a response should be retried.

    Args:
      resp_status: The response status received.
      content: The response content body.

    Returns:
      True if the response should be retried, otherwise False.
    """
    reason = None

    # Retry on 5xx errors.
    if resp_status >= 500:
        return True

    # Retry on 429 errors.
    if resp_status == _TOO_MANY_REQUESTS:
        return True

    # For 403 errors, we have to check for the `reason` in the response to
    # determine if we should retry.
    if resp_status == http_client.FORBIDDEN:
        # If there's no details about the 403 type, don't retry.
        if not content:
            return False

        # Content is in JSON format.
        try:
            data = json.loads(content.decode("utf-8"))
            if isinstance(data, dict):
                # There are many variations of the error json so we need
                # to determine the keyword which has the error detail. Make sure
                # that the order of the keywords below isn't changed as it can
                # break user code. If the "errors" key exists, we must use that
                # first.
                # See Issue #1243
                # https://github.com/googleapis/google-api-python-client/issues/1243
                error_detail_keyword = next(
                    (
                        kw
                        for kw in ["errors", "status", "message"]
                        if kw in data["error"]
                    ),
                    "",
                )

                if error_detail_keyword:
                    reason = data["error"][error_detail_keyword]

                    if isinstance(reason, list) and len(reason) > 0:
                        reason = reason[0]
                        if "reason" in reason:
                            reason = reason["reason"]
            else:
                reason = data[0]["error"]["errors"]["reason"]
        except (UnicodeDecodeError, ValueError, KeyError):
            LOGGER.warning("Invalid JSON content from response: %s", content)
            return False

        LOGGER.warning('Encountered 403 Forbidden with reason "%s"', reason)

        # Only retry on rate limit related failures.
        if reason in ("userRateLimitExceeded", "rateLimitExceeded"):
            return True

    # Everything else is a success or non-retriable so break.
    return False


def _retry_request(
    http, num_retries, req_type, sleep, rand, uri, method, *args, **kwargs
):
    """Retries an HTTP request multiple times while handling errors.

    If after all retries the request still fails, last error is either returned as
    return value (for HTTP 5xx errors) or thrown (for ssl.SSLError).

    Args:
      http: Http object to be used to execute request.
      num_retries: Maximum number of retries.
      req_type: Type of the request (used for logging retries).
      sleep, rand: Functions to sleep for random time between retries.
      uri: URI to be requested.
      method: HTTP method to be used.
      args, kwargs: Additional arguments passed to http.request.

    Returns:
      resp, content - Response from the http request (may be HTTP 5xx).
    """
    resp = None
    content = None
    exception = None
    for retry_num in range(num_retries + 1):
        if retry_num > 0:
            # Sleep before retrying.
            sleep_time = rand() * 2**retry_num
            LOGGER.warning(
                "Sleeping %.2f seconds before retry %d of %d for %s: %s %s, after %s",
                sleep_time,
                retry_num,
                num_retries,
                req_type,
                method,
                uri,
                resp.status if resp else exception,
            )
            sleep(sleep_time)

        try:
            exception = None
            resp, content = http.request(uri, method, *args, **kwargs)
        # Retry on SSL errors and socket timeout errors.
        except _ssl_SSLError as ssl_error:
            exception = ssl_error
        except socket.timeout as socket_timeout:
            # Needs to be before socket.error as it's a subclass of OSError
            # socket.timeout has no errorcode
            exception = socket_timeout
        except ConnectionError as connection_error:
            # Needs to be before socket.error as it's a subclass of OSError
            exception = connection_error
        except OSError as socket_error:
            # errno's contents differ by platform, so we have to match by name.
            # Some of these same errors may have been caught above, e.g. ECONNRESET *should* be
            # raised as a ConnectionError, but some libraries will raise it as a socket.error
            # with an errno corresponding to ECONNRESET
            if socket.errno.errorcode.get(socket_error.errno) not in {
                "WSAETIMEDOUT",
                "ETIMEDOUT",
                "EPIPE",
                "ECONNABORTED",
                "ECONNREFUSED",
                "ECONNRESET",
            }:
                raise
            exception = socket_error
        except httplib2.ServerNotFoundError as server_not_found_error:
            exception = server_not_found_error

        if exception:
            if retry_num == num_retries:
                raise exception
            else:
                continue

        if not _should_retry_response(resp.status, content):
            break

    return resp, content


class MediaUploadProgress(object):
    """Status of a resumable upload."""

    def __init__(self, resumable_progress, total_size):
        """Constructor.

        Args:
          resumable_progress: int, bytes sent so far.
          total_size: int, total bytes in complete upload, or None if the total
            upload size isn't known ahead of time.
        """
        self.resumable_progress = resumable_progress
        self.total_size = total_size

    def progress(self):
        """Percent of upload completed, as a float.

        Returns:
          the percentage complete as a float, returning 0.0 if the total size of
          the upload is unknown.
        """
        if self.total_size is not None and self.total_size != 0:
            return float(self.resumable_progress) / float(self.total_size)
        else:
            return 0.0


class MediaDownloadProgress(object):
    """Status of a resumable download."""

    def __init__(self, resumable_progress, total_size):
        """Constructor.

        Args:
          resumable_progress: int, bytes received so far.
          total_size: int, total bytes in complete download.
        """
        self.resumable_progress = resumable_progress
        self.total_size = total_size

    def progress(self):
        """Percent of download completed, as a float.

        Returns:
          the percentage complete as a float, returning 0.0 if the total size of
          the download is unknown.
        """
        if self.total_size is not None and self.total_size != 0:
            return float(self.resumable_progress) / float(self.total_size)
        else:
            return 0.0


class MediaUpload(object):
    """Describes a media object to upload.

    Base class that defines the interface of MediaUpload subclasses.

    Note that subclasses of MediaUpload may allow you to control the chunksize
    when uploading a media object. It is important to keep the size of the chunk
    as large as possible to keep the upload efficient. Other factors may influence
    the size of the chunk you use, particularly if you are working in an
    environment where individual HTTP requests may have a hardcoded time limit,
    such as under certain classes of requests under Google App Engine.

    Streams are io.Base compatible objects that support seek(). Some MediaUpload
    subclasses support using streams directly to upload data. Support for
    streaming may be indicated by a MediaUpload sub-class and if appropriate for a
    platform that stream will be used for uploading the media object. The support
    for streaming is indicated by has_stream() returning True. The stream() method
    should return an io.Base object that supports seek(). On platforms where the
    underlying httplib module supports streaming, for example Python 2.6 and
    later, the stream will be passed into the http library which will result in
    less memory being used and possibly faster uploads.

    If you need to upload media that can't be uploaded using any of the existing
    MediaUpload sub-class then you can sub-class MediaUpload for your particular
    needs.
    """

    def chunksize(self):
        """Chunk size for resumable uploads.

        Returns:
          Chunk size in bytes.
        """
        raise NotImplementedError()

    def mimetype(self):
        """Mime type of the body.

        Returns:
          Mime type.
        """
        return "application/octet-stream"

    def size(self):
        """Size of upload.

        Returns:
          Size of the body, or None of the size is unknown.
        """
        return None

    def resumable(self):
        """Whether this upload is resumable.

        Returns:
          True if resumable upload or False.
        """
        return False

    def getbytes(self, begin, end):
        """Get bytes from the media.

        Args:
          begin: int, offset from beginning of file.
          length: int, number of bytes to read, starting at begin.

        Returns:
          A string of bytes read. May be shorter than length if EOF was reached
          first.
        """
        raise NotImplementedError()

    def has_stream(self):
        """Does the underlying upload support a streaming interface.

        Streaming means it is an io.IOBase subclass that supports seek, i.e.
        seekable() returns True.

        Returns:
          True if the call to stream() will return an instance of a seekable io.Base
          subclass.
        """
        return False

    def stream(self):
        """A stream interface to the data being uploaded.

        Returns:
          The returned value is an io.IOBase subclass that supports seek, i.e.
          seekable() returns True.
        """
        raise NotImplementedError()

    @util.positional(1)
    def _to_json(self, strip=None):
        """Utility function for creating a JSON representation of a MediaUpload.

        Args:
          strip: array, An array of names of members to not include in the JSON.

        Returns:
           string, a JSON representation of this instance, suitable to pass to
           from_json().
        """
        t = type(self)
        d = copy.copy(self.__dict__)
        if strip is not None:
            for member in strip:
                del d[member]
        d["_class"] = t.__name__
        d["_module"] = t.__module__
        return json.dumps(d)

    def to_json(self):
        """Create a JSON representation of an instance of MediaUpload.

        Returns:
           string, a JSON representation of this instance, suitable to pass to
           from_json().
        """
        return self._to_json()

    @classmethod
    def new_from_json(cls, s):
        """Utility class method to instantiate a MediaUpload subclass from a JSON
        representation produced by to_json().

        Args:
          s: string, JSON from to_json().

        Returns:
          An instance of the subclass of MediaUpload that was serialized with
          to_json().
        """
        data = json.loads(s)
        # Find and call the right classmethod from_json() to restore the object.
        module = data["_module"]
        m = __import__(module, fromlist=module.split(".")[:-1])
        kls = getattr(m, data["_class"])
        from_json = getattr(kls, "from_json")
        return from_json(s)


class MediaIoBaseUpload(MediaUpload):
    """A MediaUpload for a io.Base objects.

    Note that the Python file object is compatible with io.Base and can be used
    with this class also.

      fh = BytesIO('...Some data to upload...')
      media = MediaIoBaseUpload(fh, mimetype='image/png',
        chunksize=1024*1024, resumable=True)
      farm.animals().insert(
          id='cow',
          name='cow.png',
          media_body=media).execute()

    Depending on the platform you are working on, you may pass -1 as the
    chunksize, which indicates that the entire file should be uploaded in a single
    request. If the underlying platform supports streams, such as Python 2.6 or
    later, then this can be very efficient as it avoids multiple connections, and
    also avoids loading the entire file into memory before sending it. Note that
    Google App Engine has a 5MB limit on request size, so you should never set
    your chunksize larger than 5MB, or to -1.
    """

    @util.positional(3)
    def __init__(self, fd, mimetype, chunksize=DEFAULT_CHUNK_SIZE, resumable=False):
        """Constructor.

        Args:
          fd: io.Base or file object, The source of the bytes to upload. MUST be
            opened in blocking mode, do not use streams opened in non-blocking mode.
            The given stream must be seekable, that is, it must be able to call
            seek() on fd.
          mimetype: string, Mime-type of the file.
          chunksize: int, File will be uploaded in chunks of this many bytes. Only
            used if resumable=True. Pass in a value of -1 if the file is to be
            uploaded as a single chunk. Note that Google App Engine has a 5MB limit
            on request size, so you should never set your chunksize larger than 5MB,
            or to -1.
          resumable: bool, True if this is a resumable upload. False means upload
            in a single request.
        """
        super(MediaIoBaseUpload, self).__init__()
        self._fd = fd
        self._mimetype = mimetype
        if not (chunksize == -1 or chunksize > 0):
            raise InvalidChunkSizeError()
        self._chunksize = chunksize
        self._resumable = resumable

        self._fd.seek(0, os.SEEK_END)
        self._size = self._fd.tell()

    def chunksize(self):
        """Chunk size for resumable uploads.

        Returns:
          Chunk size in bytes.
        """
        return self._chunksize

    def mimetype(self):
        """Mime type of the body.

        Returns:
          Mime type.
        """
        return self._mimetype

    def size(self):
        """Size of upload.

        Returns:
          Size of the body, or None of the size is unknown.
        """
        return self._size

    def resumable(self):
        """Whether this upload is resumable.

        Returns:
          True if resumable upload or False.
        """
        return self._resumable

    def getbytes(self, begin, length):
        """Get bytes from the media.

        Args:
          begin: int, offset from beginning of file.
          length: int, number of bytes to read, starting at begin.

        Returns:
          A string of bytes read. May be shorted than length if EOF was reached
          first.
        """
        self._fd.seek(begin)
        return self._fd.read(length)

    def has_stream(self):
        """Does the underlying upload support a streaming interface.

        Streaming means it is an io.IOBase subclass that supports seek, i.e.
        seekable() returns True.

        Returns:
          True if the call to stream() will return an instance of a seekable io.Base
          subclass.
        """
        return True

    def stream(self):
        """A stream interface to the data being uploaded.

        Returns:
          The returned value is an io.IOBase subclass that supports seek, i.e.
          seekable() returns True.
        """
        return self._fd

    def to_json(self):
        """This upload type is not serializable."""
        raise NotImplementedError("MediaIoBaseUpload is not serializable.")


class MediaFileUpload(MediaIoBaseUpload):
    """A MediaUpload for a file.

    Construct a MediaFileUpload and pass as the media_body parameter of the
    method. For example, if we had a service that allowed uploading images:

      media = MediaFileUpload('cow.png', mimetype='image/png',
        chunksize=1024*1024, resumable=True)
      farm.animals().insert(
          id='cow',
          name='cow.png',
          media_body=media).execute()

    Depending on the platform you are working on, you may pass -1 as the
    chunksize, which indicates that the entire file should be uploaded in a single
    request. If the underlying platform supports streams, such as Python 2.6 or
    later, then this can be very efficient as it avoids multiple connections, and
    also avoids loading the entire file into memory before sending it. Note that
    Google App Engine has a 5MB limit on request size, so you should never set
    your chunksize larger than 5MB, or to -1.
    """

    @util.positional(2)
    def __init__(
        self, filename, mimetype=None, chunksize=DEFAULT_CHUNK_SIZE, resumable=False
    ):
        """Constructor.

        Args:
          filename: string, Name of the file.
          mimetype: string, Mime-type of the file. If None then a mime-type will be
            guessed from the file extension.
          chunksize: int, File will be uploaded in chunks of this many bytes. Only
            used if resumable=True. Pass in a value of -1 if the file is to be
            uploaded in a single chunk. Note that Google App Engine has a 5MB limit
            on request size, so you should never set your chunksize larger than 5MB,
            or to -1.
          resumable: bool, True if this is a resumable upload. False means upload
            in a single request.
        """
        self._fd = None
        self._filename = filename
        self._fd = open(self._filename, "rb")
        if mimetype is None:
            # No mimetype provided, make a guess.
            mimetype, _ = mimetypes.guess_type(filename)
            if mimetype is None:
                # Guess failed, use octet-stream.
                mimetype = "application/octet-stream"
        super(MediaFileUpload, self).__init__(
            self._fd, mimetype, chunksize=chunksize, resumable=resumable
        )

    def __del__(self):
        if self._fd:
            self._fd.close()

    def to_json(self):
        """Creating a JSON representation of an instance of MediaFileUpload.

        Returns:
           string, a JSON representation of this instance, suitable to pass to
           from_json().
        """
        return self._to_json(strip=["_fd"])

    @staticmethod
    def from_json(s):
        d = json.loads(s)
        return MediaFileUpload(
            d["_filename"],
            mimetype=d["_mimetype"],
            chunksize=d["_chunksize"],
            resumable=d["_resumable"],
        )


class MediaInMemoryUpload(MediaIoBaseUpload):
    """MediaUpload for a chunk of bytes.

    DEPRECATED: Use MediaIoBaseUpload with either io.TextIOBase or io.StringIO for
    the stream.
    """

    @util.positional(2)
    def __init__(
        self,
        body,
        mimetype="application/octet-stream",
        chunksize=DEFAULT_CHUNK_SIZE,
        resumable=False,
    ):
        """Create a new MediaInMemoryUpload.

        DEPRECATED: Use MediaIoBaseUpload with either io.TextIOBase or io.StringIO for
        the stream.

        Args:
          body: string, Bytes of body content.
          mimetype: string, Mime-type of the file or default of
            'application/octet-stream'.
          chunksize: int, File will be uploaded in chunks of this many bytes. Only
            used if resumable=True.
          resumable: bool, True if this is a resumable upload. False means upload
            in a single request.
        """
        fd = io.BytesIO(body)
        super(MediaInMemoryUpload, self).__init__(
            fd, mimetype, chunksize=chunksize, resumable=resumable
        )


class MediaIoBaseDownload(object):
    """ "Download media resources.

    Note that the Python file object is compatible with io.Base and can be used
    with this class also.


    Example:
      request = farms.animals().get_media(id='cow')
      fh = io.FileIO('cow.png', mode='wb')
      downloader = MediaIoBaseDownload(fh, request, chunksize=1024*1024)

      done = False
      while done is False:
        status, done = downloader.next_chunk()
        if status:
          print "Download %d%%." % int(status.progress() * 100)
      print "Download Complete!"
    """

    @util.positional(3)
    def __init__(self, fd, request, chunksize=DEFAULT_CHUNK_SIZE):
        """Constructor.

        Args:
          fd: io.Base or file object, The stream in which to write the downloaded
            bytes.
          request: googleapiclient.http.HttpRequest, the media request to perform in
            chunks.
          chunksize: int, File will be downloaded in chunks of this many bytes.
        """
        self._fd = fd
        self._request = request
        self._uri = request.uri
        self._chunksize = chunksize
        self._progress = 0
        self._total_size = None
        self._done = False

        # Stubs for testing.
        self._sleep = time.sleep
        self._rand = random.random

        self._headers = {}
        for k, v in request.headers.items():
            # allow users to supply custom headers by setting them on the request
            # but strip out the ones that are set by default on requests generated by
            # API methods like Drive's files().get(fileId=...)
            if not k.lower() in ("accept", "accept-encoding", "user-agent"):
                self._headers[k] = v

    @util.positional(1)
    def next_chunk(self, num_retries=0):
        """Get the next chunk of the download.

        Args:
          num_retries: Integer, number of times to retry with randomized
                exponential backoff. If all retries fail, the raised HttpError
                represents the last request. If zero (default), we attempt the
                request only once.

        Returns:
          (status, done): (MediaDownloadProgress, boolean)
             The value of 'done' will be True when the media has been fully
             downloaded or the total size of the media is unknown.

        Raises:
          googleapiclient.errors.HttpError if the response was not a 2xx.
          httplib2.HttpLib2Error if a transport error has occurred.
        """
        headers = self._headers.copy()
        headers["range"] = "bytes=%d-%d" % (
            self._progress,
            self._progress + self._chunksize - 1,
        )
        http = self._request.http

        resp, content = _retry_request(
            http,
            num_retries,
            "media download",
            self._sleep,
            self._rand,
            self._uri,
            "GET",
            headers=headers,
        )

        if resp.status in [200, 206]:
            if "content-location" in resp and resp["content-location"] != self._uri:
                self._uri = resp["content-location"]
            self._progress += len(content)
            self._fd.write(content)

            if "content-range" in resp:
                content_range = resp["content-range"]
                length = content_range.rsplit("/", 1)[1]
                self._total_size = int(length)
            elif "content-length" in resp:
                self._total_size = int(resp["content-length"])

            if self._total_size is None or self._progress == self._total_size:
                self._done = True
            return MediaDownloadProgress(self._progress, self._total_size), self._done
        elif resp.status == 416:
            # 416 is Range Not Satisfiable
            # This typically occurs with a zero byte file
            content_range = resp["content-range"]
            length = content_range.rsplit("/", 1)[1]
            self._total_size = int(length)
            if self._total_size == 0:
                self._done = True
                return (
                    MediaDownloadProgress(self._progress, self._total_size),
                    self._done,
                )
        raise HttpError(resp, content, uri=self._uri)


class _StreamSlice(object):
    """Truncated stream.

    Takes a stream and presents a stream that is a slice of the original stream.
    This is used when uploading media in chunks. In later versions of Python a
    stream can be passed to httplib in place of the string of data to send. The
    problem is that httplib just blindly reads to the end of the stream. This
    wrapper presents a virtual stream that only reads to the end of the chunk.
    """

    def __init__(self, stream, begin, chunksize):
        """Constructor.

        Args:
          stream: (io.Base, file object), the stream to wrap.
          begin: int, the seek position the chunk begins at.
          chunksize: int, the size of the chunk.
        """
        self._stream = stream
        self._begin = begin
        self._chunksize = chunksize
        self._stream.seek(begin)

    def read(self, n=-1):
        """Read n bytes.

        Args:
          n, int, the number of bytes to read.

        Returns:
          A string of length 'n', or less if EOF is reached.
        """
        # The data left available to read sits in [cur, end)
        cur = self._stream.tell()
        end = self._begin + self._chunksize
        if n == -1 or cur + n > end:
            n = end - cur
        return self._stream.read(n)


class HttpRequest(object):
    """Encapsulates a single HTTP request."""

    @util.positional(4)
    def __init__(
        self,
        http,
        postproc,
        uri,
        method="GET",
        body=None,
        headers=None,
        methodId=None,
        resumable=None,
    ):
        """Constructor for an HttpRequest.

        Args:
          http: httplib2.Http, the transport object to use to make a request
          postproc: callable, called on the HTTP response and content to transform
                    it into a data object before returning, or raising an exception
                    on an error.
          uri: string, the absolute URI to send the request to
          method: string, the HTTP method to use
          body: string, the request body of the HTTP request,
          headers: dict, the HTTP request headers
          methodId: string, a unique identifier for the API method being called.
          resumable: MediaUpload, None if this is not a resumbale request.
        """
        self.uri = uri
        self.method = method
        self.body = body
        self.headers = headers or {}
        self.methodId = methodId
        self.http = http
        self.postproc = postproc
        self.resumable = resumable
        self.response_callbacks = []
        self._in_error_state = False

        # The size of the non-media part of the request.
        self.body_size = len(self.body or "")

        # The resumable URI to send chunks to.
        self.resumable_uri = None

        # The bytes that have been uploaded.
        self.resumable_progress = 0

        # Stubs for testing.
        self._rand = random.random
        self._sleep = time.sleep

    @util.positional(1)
    def execute(self, http=None, num_retries=0):
        """Execute the request.

        Args:
          http: httplib2.Http, an http object to be used in place of the
                one the HttpRequest request object was constructed with.
          num_retries: Integer, number of times to retry with randomized
                exponential backoff. If all retries fail, the raised HttpError
                represents the last request. If zero (default), we attempt the
                request only once.

        Returns:
          A deserialized object model of the response body as determined
          by the postproc.

        Raises:
          googleapiclient.errors.HttpError if the response was not a 2xx.
          httplib2.HttpLib2Error if a transport error has occurred.
        """
        if http is None:
            http = self.http

        if self.resumable:
            body = None
            while body is None:
                _, body = self.next_chunk(http=http, num_retries=num_retries)
            return body

        # Non-resumable case.

        if "content-length" not in self.headers:
            self.headers["content-length"] = str(self.body_size)
        # If the request URI is too long then turn it into a POST request.
        # Assume that a GET request never contains a request body.
        if len(self.uri) > MAX_URI_LENGTH and self.method == "GET":
            self.method = "POST"
            self.headers["x-http-method-override"] = "GET"
            self.headers["content-type"] = "application/x-www-form-urlencoded"
            parsed = urllib.parse.urlparse(self.uri)
            self.uri = urllib.parse.urlunparse(
                (parsed.scheme, parsed.netloc, parsed.path, parsed.params, None, None)
            )
            self.body = parsed.query
            self.headers["content-length"] = str(len(self.body))

        # Handle retries for server-side errors.
        resp, content = _retry_request(
            http,
            num_retries,
            "request",
            self._sleep,
            self._rand,
            str(self.uri),
            method=str(self.method),
            body=self.body,
            headers=self.headers,
        )

        for callback in self.response_callbacks:
            callback(resp)
        if resp.status >= 300:
            raise HttpError(resp, content, uri=self.uri)
        return self.postproc(resp, content)

    @util.positional(2)
    def add_response_callback(self, cb):
        """add_response_headers_callback

        Args:
          cb: Callback to be called on receiving the response headers, of signature:

          def cb(resp):
            # Where resp is an instance of httplib2.Response
        """
        self.response_callbacks.append(cb)

    @util.positional(1)
    def next_chunk(self, http=None, num_retries=0):
        """Execute the next step of a resumable upload.

        Can only be used if the method being executed supports media uploads and
        the MediaUpload object passed in was flagged as using resumable upload.

        Example:

          media = MediaFileUpload('cow.png', mimetype='image/png',
                                  chunksize=1000, resumable=True)
          request = farm.animals().insert(
              id='cow',
              name='cow.png',
              media_body=media)

          response = None
          while response is None:
            status, response = request.next_chunk()
            if status:
              print "Upload %d%% complete." % int(status.progress() * 100)


        Args:
          http: httplib2.Http, an http object to be used in place of the
                one the HttpRequest request object was constructed with.
          num_retries: Integer, number of times to retry with randomized
                exponential backoff. If all retries fail, the raised HttpError
                represents the last request. If zero (default), we attempt the
                request only once.

        Returns:
          (status, body): (ResumableMediaStatus, object)
             The body will be None until the resumable media is fully uploaded.

        Raises:
          googleapiclient.errors.HttpError if the response was not a 2xx.
          httplib2.HttpLib2Error if a transport error has occurred.
        """
        if http is None:
            http = self.http

        if self.resumable.size() is None:
            size = "*"
        else:
            size = str(self.resumable.size())

        if self.resumable_uri is None:
            start_headers = copy.copy(self.headers)
            start_headers["X-Upload-Content-Type"] = self.resumable.mimetype()
            if size != "*":
                start_headers["X-Upload-Content-Length"] = size
            start_headers["content-length"] = str(self.body_size)

            resp, content = _retry_request(
                http,
                num_retries,
                "resumable URI request",
                self._sleep,
                self._rand,
                self.uri,
                method=self.method,
                body=self.body,
                headers=start_headers,
            )

            if resp.status == 200 and "location" in resp:
                self.resumable_uri = resp["location"]
            else:
                raise ResumableUploadError(resp, content)
        elif self._in_error_state:
            # If we are in an error state then query the server for current state of
            # the upload by sending an empty PUT and reading the 'range' header in
            # the response.
            headers = {"Content-Range": "bytes */%s" % size, "content-length": "0"}
            resp, content = http.request(self.resumable_uri, "PUT", headers=headers)
            status, body = self._process_response(resp, content)
            if body:
                # The upload was complete.
                return (status, body)

        if self.resumable.has_stream():
            data = self.resumable.stream()
            if self.resumable.chunksize() == -1:
                data.seek(self.resumable_progress)
                chunk_end = self.resumable.size() - self.resumable_progress - 1
            else:
                # Doing chunking with a stream, so wrap a slice of the stream.
                data = _StreamSlice(
                    data, self.resumable_progress, self.resumable.chunksize()
                )
                chunk_end = min(
                    self.resumable_progress + self.resumable.chunksize() - 1,
                    self.resumable.size() - 1,
                )
        else:
            data = self.resumable.getbytes(
                self.resumable_progress, self.resumable.chunksize()
            )

            # A short read implies that we are at EOF, so finish the upload.
            if len(data) < self.resumable.chunksize():
                size = str(self.resumable_progress + len(data))

            chunk_end = self.resumable_progress + len(data) - 1

        headers = {
            # Must set the content-length header here because httplib can't
            # calculate the size when working with _StreamSlice.
            "Content-Length": str(chunk_end - self.resumable_progress + 1),
        }

        # An empty file results in chunk_end = -1 and size = 0
        # sending "bytes 0--1/0" results in an invalid request
        # Only add header "Content-Range" if chunk_end != -1
        if chunk_end != -1:
            headers["Content-Range"] = "bytes %d-%d/%s" % (
                self.resumable_progress,
                chunk_end,
                size,
            )

        for retry_num in range(num_retries + 1):
            if retry_num > 0:
                self._sleep(self._rand() * 2**retry_num)
                LOGGER.warning(
                    "Retry #%d for media upload: %s %s, following status: %d"
                    % (retry_num, self.method, self.uri, resp.status)
                )

            try:
                resp, content = http.request(
                    self.resumable_uri, method="PUT", body=data, headers=headers
                )
            except:
                self._in_error_state = True
                raise
            if not _should_retry_response(resp.status, content):
                break

        return self._process_response(resp, content)

    def _process_response(self, resp, content):
        """Process the response from a single chunk upload.

        Args:
          resp: httplib2.Response, the response object.
          content: string, the content of the response.

        Returns:
          (status, body): (ResumableMediaStatus, object)
             The body will be None until the resumable media is fully uploaded.

        Raises:
          googleapiclient.errors.HttpError if the response was not a 2xx or a 308.
        """
        if resp.status in [200, 201]:
            self._in_error_state = False
            return None, self.postproc(resp, content)
        elif resp.status == 308:
            self._in_error_state = False
            # A "308 Resume Incomplete" indicates we are not done.
            try:
                self.resumable_progress = int(resp["range"].split("-")[1]) + 1
            except KeyError:
                # If resp doesn't contain range header, resumable progress is 0
                self.resumable_progress = 0
            if "location" in resp:
                self.resumable_uri = resp["location"]
        else:
            self._in_error_state = True
            raise HttpError(resp, content, uri=self.uri)

        return (
            MediaUploadProgress(self.resumable_progress, self.resumable.size()),
            None,
        )

    def to_json(self):
        """Returns a JSON representation of the HttpRequest."""
        d = copy.copy(self.__dict__)
        if d["resumable"] is not None:
            d["resumable"] = self.resumable.to_json()
        del d["http"]
        del d["postproc"]
        del d["_sleep"]
        del d["_rand"]

        return json.dumps(d)

    @staticmethod
    def from_json(s, http, postproc):
        """Returns an HttpRequest populated with info from a JSON object."""
        d = json.loads(s)
        if d["resumable"] is not None:
            d["resumable"] = MediaUpload.new_from_json(d["resumable"])
        return HttpRequest(
            http,
            postproc,
            uri=d["uri"],
            method=d["method"],
            body=d["body"],
            headers=d["headers"],
            methodId=d["methodId"],
            resumable=d["resumable"],
        )

    @staticmethod
    def null_postproc(resp, contents):
        return resp, contents


class BatchHttpRequest(object):
    """Batches multiple HttpRequest objects into a single HTTP request.

    Example:
      from googleapiclient.http import BatchHttpRequest

      def list_animals(request_id, response, exception):
        \"\"\"Do something with the animals list response.\"\"\"
        if exception is not None:
          # Do something with the exception.
          pass
        else:
          # Do something with the response.
          pass

      def list_farmers(request_id, response, exception):
        \"\"\"Do something with the farmers list response.\"\"\"
        if exception is not None:
          # Do something with the exception.
          pass
        else:
          # Do something with the response.
          pass

      service = build('farm', 'v2')

      batch = BatchHttpRequest()

      batch.add(service.animals().list(), list_animals)
      batch.add(service.farmers().list(), list_farmers)
      batch.execute(http=http)
    """

    @util.positional(1)
    def __init__(self, callback=None, batch_uri=None):
        """Constructor for a BatchHttpRequest.

        Args:
          callback: callable, A callback to be called for each response, of the
            form callback(id, response, exception). The first parameter is the
            request id, and the second is the deserialized response object. The
            third is an googleapiclient.errors.HttpError exception object if an HTTP error
            occurred while processing the request, or None if no error occurred.
          batch_uri: string, URI to send batch requests to.
        """
        if batch_uri is None:
            batch_uri = _LEGACY_BATCH_URI

        if batch_uri == _LEGACY_BATCH_URI:
            LOGGER.warning(
                "You have constructed a BatchHttpRequest using the legacy batch "
                "endpoint %s. This endpoint will be turned down on August 12, 2020. "
                "Please provide the API-specific endpoint or use "
                "service.new_batch_http_request(). For more details see "
                "https://developers.googleblog.com/2018/03/discontinuing-support-for-json-rpc-and.html"
                "and https://developers.google.com/api-client-library/python/guide/batch.",
                _LEGACY_BATCH_URI,
            )
        self._batch_uri = batch_uri

        # Global callback to be called for each individual response in the batch.
        self._callback = callback

        # A map from id to request.
        self._requests = {}

        # A map from id to callback.
        self._callbacks = {}

        # List of request ids, in the order in which they were added.
        self._order = []

        # The last auto generated id.
        self._last_auto_id = 0

        # Unique ID on which to base the Content-ID headers.
        self._base_id = None

        # A map from request id to (httplib2.Response, content) response pairs
        self._responses = {}

        # A map of id(Credentials) that have been refreshed.
        self._refreshed_credentials = {}

    def _refresh_and_apply_credentials(self, request, http):
        """Refresh the credentials and apply to the request.

        Args:
          request: HttpRequest, the request.
          http: httplib2.Http, the global http object for the batch.
        """
        # For the credentials to refresh, but only once per refresh_token
        # If there is no http per the request then refresh the http passed in
        # via execute()
        creds = None
        request_credentials = False

        if request.http is not None:
            creds = _auth.get_credentials_from_http(request.http)
            request_credentials = True

        if creds is None and http is not None:
            creds = _auth.get_credentials_from_http(http)

        if creds is not None:
            if id(creds) not in self._refreshed_credentials:
                _auth.refresh_credentials(creds)
                self._refreshed_credentials[id(creds)] = 1

        # Only apply the credentials if we are using the http object passed in,
        # otherwise apply() will get called during _serialize_request().
        if request.http is None or not request_credentials:
            _auth.apply_credentials(creds, request.headers)

    def _id_to_header(self, id_):
        """Convert an id to a Content-ID header value.

        Args:
          id_: string, identifier of individual request.

        Returns:
          A Content-ID header with the id_ encoded into it. A UUID is prepended to
          the value because Content-ID headers are supposed to be universally
          unique.
        """
        if self._base_id is None:
            self._base_id = uuid.uuid4()

        # NB: we intentionally leave whitespace between base/id and '+', so RFC2822
        # line folding works properly on Python 3; see
        # https://github.com/googleapis/google-api-python-client/issues/164
        return "<%s + %s>" % (self._base_id, urllib.parse.quote(id_))

    def _header_to_id(self, header):
        """Convert a Content-ID header value to an id.

        Presumes the Content-ID header conforms to the format that _id_to_header()
        returns.

        Args:
          header: string, Content-ID header value.

        Returns:
          The extracted id value.

        Raises:
          BatchError if the header is not in the expected format.
        """
        if header[0] != "<" or header[-1] != ">":
            raise BatchError("Invalid value for Content-ID: %s" % header)
        if "+" not in header:
            raise BatchError("Invalid value for Content-ID: %s" % header)
        base, id_ = header[1:-1].split(" + ", 1)

        return urllib.parse.unquote(id_)

    def _serialize_request(self, request):
        """Convert an HttpRequest object into a string.

        Args:
          request: HttpRequest, the request to serialize.

        Returns:
          The request as a string in application/http format.
        """
        # Construct status line
        parsed = urllib.parse.urlparse(request.uri)
        request_line = urllib.parse.urlunparse(
            ("", "", parsed.path, parsed.params, parsed.query, "")
        )
        status_line = request.method + " " + request_line + " HTTP/1.1\n"
        major, minor = request.headers.get("content-type", "application/json").split(
            "/"
        )
        msg = MIMENonMultipart(major, minor)
        headers = request.headers.copy()

        if request.http is not None:
            credentials = _auth.get_credentials_from_http(request.http)
            if credentials is not None:
                _auth.apply_credentials(credentials, headers)

        # MIMENonMultipart adds its own Content-Type header.
        if "content-type" in headers:
            del headers["content-type"]

        for key, value in headers.items():
            msg[key] = value
        msg["Host"] = parsed.netloc
        msg.set_unixfrom(None)

        if request.body is not None:
            msg.set_payload(request.body)
            msg["content-length"] = str(len(request.body))

        # Serialize the mime message.
        fp = io.StringIO()
        # maxheaderlen=0 means don't line wrap headers.
        g = Generator(fp, maxheaderlen=0)
        g.flatten(msg, unixfrom=False)
        body = fp.getvalue()

        return status_line + body

    def _deserialize_response(self, payload):
        """Convert string into httplib2 response and content.

        Args:
          payload: string, headers and body as a string.

        Returns:
          A pair (resp, content), such as would be returned from httplib2.request.
        """
        # Strip off the status line
        status_line, payload = payload.split("\n", 1)
        protocol, status, reason = status_line.split(" ", 2)

        # Parse the rest of the response
        parser = FeedParser()
        parser.feed(payload)
        msg = parser.close()
        msg["status"] = status

        # Create httplib2.Response from the parsed headers.
        resp = httplib2.Response(msg)
        resp.reason = reason
        resp.version = int(protocol.split("/", 1)[1].replace(".", ""))

        content = payload.split("\r\n\r\n", 1)[1]

        return resp, content

    def _new_id(self):
        """Create a new id.

        Auto incrementing number that avoids conflicts with ids already used.

        Returns:
           string, a new unique id.
        """
        self._last_auto_id += 1
        while str(self._last_auto_id) in self._requests:
            self._last_auto_id += 1
        return str(self._last_auto_id)

    @util.positional(2)
    def add(self, request, callback=None, request_id=None):
        """Add a new request.

        Every callback added will be paired with a unique id, the request_id. That
        unique id will be passed back to the callback when the response comes back
        from the server. The default behavior is to have the library generate it's
        own unique id. If the caller passes in a request_id then they must ensure
        uniqueness for each request_id, and if they are not an exception is
        raised. Callers should either supply all request_ids or never supply a
        request id, to avoid such an error.

        Args:
          request: HttpRequest, Request to add to the batch.
          callback: callable, A callback to be called for this response, of the
            form callback(id, response, exception). The first parameter is the
            request id, and the second is the deserialized response object. The
            third is an googleapiclient.errors.HttpError exception object if an HTTP error
            occurred while processing the request, or None if no errors occurred.
          request_id: string, A unique id for the request. The id will be passed
            to the callback with the response.

        Returns:
          None

        Raises:
          BatchError if a media request is added to a batch.
          KeyError is the request_id is not unique.
        """

        if len(self._order) >= MAX_BATCH_LIMIT:
            raise BatchError(
                "Exceeded the maximum calls(%d) in a single batch request."
                % MAX_BATCH_LIMIT
            )
        if request_id is None:
            request_id = self._new_id()
        if request.resumable is not None:
            raise BatchError("Media requests cannot be used in a batch request.")
        if request_id in self._requests:
            raise KeyError("A request with this ID already exists: %s" % request_id)
        self._requests[request_id] = request
        self._callbacks[request_id] = callback
        self._order.append(request_id)

    def _execute(self, http, order, requests):
        """Serialize batch request, send to server, process response.

        Args:
          http: httplib2.Http, an http object to be used to make the request with.
          order: list, list of request ids in the order they were added to the
            batch.
          requests: list, list of request objects to send.

        Raises:
          httplib2.HttpLib2Error if a transport error has occurred.
          googleapiclient.errors.BatchError if the response is the wrong format.
        """
        message = MIMEMultipart("mixed")
        # Message should not write out it's own headers.
        setattr(message, "_write_headers", lambda self: None)

        # Add all the individual requests.
        for request_id in order:
            request = requests[request_id]

            msg = MIMENonMultipart("application", "http")
            msg["Content-Transfer-Encoding"] = "binary"
            msg["Content-ID"] = self._id_to_header(request_id)

            body = self._serialize_request(request)
            msg.set_payload(body)
            message.attach(msg)

        # encode the body: note that we can't use `as_string`, because
        # it plays games with `From ` lines.
        fp = io.StringIO()
        g = Generator(fp, mangle_from_=False)
        g.flatten(message, unixfrom=False)
        body = fp.getvalue()

        headers = {}
        headers["content-type"] = (
            "multipart/mixed; " 'boundary="%s"'
        ) % message.get_boundary()

        resp, content = http.request(
            self._batch_uri, method="POST", body=body, headers=headers
        )

        if resp.status >= 300:
            raise HttpError(resp, content, uri=self._batch_uri)

        # Prepend with a content-type header so FeedParser can handle it.
        header = "content-type: %s\r\n\r\n" % resp["content-type"]
        # PY3's FeedParser only accepts unicode. So we should decode content
        # here, and encode each payload again.
        content = content.decode("utf-8")
        for_parser = header + content

        parser = FeedParser()
        parser.feed(for_parser)
        mime_response = parser.close()

        if not mime_response.is_multipart():
            raise BatchError(
                "Response not in multipart/mixed format.", resp=resp, content=content
            )

        for part in mime_response.get_payload():
            request_id = self._header_to_id(part["Content-ID"])
            response, content = self._deserialize_response(part.get_payload())
            # We encode content here to emulate normal http response.
            if isinstance(content, str):
                content = content.encode("utf-8")
            self._responses[request_id] = (response, content)

    @util.positional(1)
    def execute(self, http=None):
        """Execute all the requests as a single batched HTTP request.

        Args:
          http: httplib2.Http, an http object to be used in place of the one the
            HttpRequest request object was constructed with. If one isn't supplied
            then use a http object from the requests in this batch.

        Returns:
          None

        Raises:
          httplib2.HttpLib2Error if a transport error has occurred.
          googleapiclient.errors.BatchError if the response is the wrong format.
        """
        # If we have no requests return
        if len(self._order) == 0:
            return None

        # If http is not supplied use the first valid one given in the requests.
        if http is None:
            for request_id in self._order:
                request = self._requests[request_id]
                if request is not None:
                    http = request.http
                    break

        if http is None:
            raise ValueError("Missing a valid http object.")

        # Special case for OAuth2Credentials-style objects which have not yet been
        # refreshed with an initial access_token.
        creds = _auth.get_credentials_from_http(http)
        if creds is not None:
            if not _auth.is_valid(creds):
                LOGGER.info("Attempting refresh to obtain initial access_token")
                _auth.refresh_credentials(creds)

        self._execute(http, self._order, self._requests)

        # Loop over all the requests and check for 401s. For each 401 request the
        # credentials should be refreshed and then sent again in a separate batch.
        redo_requests = {}
        redo_order = []

        for request_id in self._order:
            resp, content = self._responses[request_id]
            if resp["status"] == "401":
                redo_order.append(request_id)
                request = self._requests[request_id]
                self._refresh_and_apply_credentials(request, http)
                redo_requests[request_id] = request

        if redo_requests:
            self._execute(http, redo_order, redo_requests)

        # Now process all callbacks that are erroring, and raise an exception for
        # ones that return a non-2xx response? Or add extra parameter to callback
        # that contains an HttpError?

        for request_id in self._order:
            resp, content = self._responses[request_id]

            request = self._requests[request_id]
            callback = self._callbacks[request_id]

            response = None
            exception = None
            try:
                if resp.status >= 300:
                    raise HttpError(resp, content, uri=request.uri)
                response = request.postproc(resp, content)
            except HttpError as e:
                exception = e

            if callback is not None:
                callback(request_id, response, exception)
            if self._callback is not None:
                self._callback(request_id, response, exception)


class HttpRequestMock(object):
    """Mock of HttpRequest.

    Do not construct directly, instead use RequestMockBuilder.
    """

    def __init__(self, resp, content, postproc):
        """Constructor for HttpRequestMock

        Args:
          resp: httplib2.Response, the response to emulate coming from the request
          content: string, the response body
          postproc: callable, the post processing function usually supplied by
                    the model class. See model.JsonModel.response() as an example.
        """
        self.resp = resp
        self.content = content
        self.postproc = postproc
        if resp is None:
            self.resp = httplib2.Response({"status": 200, "reason": "OK"})
        if "reason" in self.resp:
            self.resp.reason = self.resp["reason"]

    def execute(self, http=None):
        """Execute the request.

        Same behavior as HttpRequest.execute(), but the response is
        mocked and not really from an HTTP request/response.
        """
        return self.postproc(self.resp, self.content)


class RequestMockBuilder(object):
    """A simple mock of HttpRequest

    Pass in a dictionary to the constructor that maps request methodIds to
    tuples of (httplib2.Response, content, opt_expected_body) that should be
    returned when that method is called. None may also be passed in for the
    httplib2.Response, in which case a 200 OK response will be generated.
    If an opt_expected_body (str or dict) is provided, it will be compared to
    the body and UnexpectedBodyError will be raised on inequality.

    Example:
      response = '{"data": {"id": "tag:google.c...'
      requestBuilder = RequestMockBuilder(
        {
          'plus.activities.get': (None, response),
        }
      )
      googleapiclient.discovery.build("plus", "v1", requestBuilder=requestBuilder)

    Methods that you do not supply a response for will return a
    200 OK with an empty string as the response content or raise an excpetion
    if check_unexpected is set to True. The methodId is taken from the rpcName
    in the discovery document.

    For more details see the project wiki.
    """

    def __init__(self, responses, check_unexpected=False):
        """Constructor for RequestMockBuilder

        The constructed object should be a callable object
        that can replace the class HttpResponse.

        responses - A dictionary that maps methodIds into tuples
                    of (httplib2.Response, content). The methodId
                    comes from the 'rpcName' field in the discovery
                    document.
        check_unexpected - A boolean setting whether or not UnexpectedMethodError
                           should be raised on unsupplied method.
        """
        self.responses = responses
        self.check_unexpected = check_unexpected

    def __call__(
        self,
        http,
        postproc,
        uri,
        method="GET",
        body=None,
        headers=None,
        methodId=None,
        resumable=None,
    ):
        """Implements the callable interface that discovery.build() expects
        of requestBuilder, which is to build an object compatible with
        HttpRequest.execute(). See that method for the description of the
        parameters and the expected response.
        """
        if methodId in self.responses:
            response = self.responses[methodId]
            resp, content = response[:2]
            if len(response) > 2:
                # Test the body against the supplied expected_body.
                expected_body = response[2]
                if bool(expected_body) != bool(body):
                    # Not expecting a body and provided one
                    # or expecting a body and not provided one.
                    raise UnexpectedBodyError(expected_body, body)
                if isinstance(expected_body, str):
                    expected_body = json.loads(expected_body)
                body = json.loads(body)
                if body != expected_body:
                    raise UnexpectedBodyError(expected_body, body)
            return HttpRequestMock(resp, content, postproc)
        elif self.check_unexpected:
            raise UnexpectedMethodError(methodId=methodId)
        else:
            model = JsonModel(False)
            return HttpRequestMock(None, "{}", model.response)


class HttpMock(object):
    """Mock of httplib2.Http"""

    def __init__(self, filename=None, headers=None):
        """
        Args:
          filename: string, absolute filename to read response from
          headers: dict, header to return with response
        """
        if headers is None:
            headers = {"status": "200"}
        if filename:
            with open(filename, "rb") as f:
                self.data = f.read()
        else:
            self.data = None
        self.response_headers = headers
        self.headers = None
        self.uri = None
        self.method = None
        self.body = None
        self.headers = None

    def request(
        self,
        uri,
        method="GET",
        body=None,
        headers=None,
        redirections=1,
        connection_type=None,
    ):
        self.uri = uri
        self.method = method
        self.body = body
        self.headers = headers
        return httplib2.Response(self.response_headers), self.data

    def close(self):
        return None


class HttpMockSequence(object):
    """Mock of httplib2.Http

    Mocks a sequence of calls to request returning different responses for each
    call. Create an instance initialized with the desired response headers
    and content and then use as if an httplib2.Http instance.

      http = HttpMockSequence([
        ({'status': '401'}, ''),
        ({'status': '200'}, '{"access_token":"1/3w","expires_in":3600}'),
        ({'status': '200'}, 'echo_request_headers'),
        ])
      resp, content = http.request("http://examples.com")

    There are special values you can pass in for content to trigger
    behavours that are helpful in testing.

    'echo_request_headers' means return the request headers in the response body
    'echo_request_headers_as_json' means return the request headers in
       the response body
    'echo_request_body' means return the request body in the response body
    'echo_request_uri' means return the request uri in the response body
    """

    def __init__(self, iterable):
        """
        Args:
          iterable: iterable, a sequence of pairs of (headers, body)
        """
        self._iterable = iterable
        self.follow_redirects = True
        self.request_sequence = list()

    def request(
        self,
        uri,
        method="GET",
        body=None,
        headers=None,
        redirections=1,
        connection_type=None,
    ):
        # Remember the request so after the fact this mock can be examined
        self.request_sequence.append((uri, method, body, headers))
        resp, content = self._iterable.pop(0)
        if isinstance(content, str):
            content = content.encode("utf-8")

        if content == b"echo_request_headers":
            content = headers
        elif content == b"echo_request_headers_as_json":
            content = json.dumps(headers)
        elif content == b"echo_request_body":
            if hasattr(body, "read"):
                content = body.read()
            else:
                content = body
        elif content == b"echo_request_uri":
            content = uri
        if isinstance(content, str):
            content = content.encode("utf-8")
        return httplib2.Response(resp), content


def set_user_agent(http, user_agent):
    """Set the user-agent on every request.

    Args:
       http - An instance of httplib2.Http
           or something that acts like it.
       user_agent: string, the value for the user-agent header.

    Returns:
       A modified instance of http that was passed in.

    Example:

      h = httplib2.Http()
      h = set_user_agent(h, "my-app-name/6.0")

    Most of the time the user-agent will be set doing auth, this is for the rare
    cases where you are accessing an unauthenticated endpoint.
    """
    request_orig = http.request

    # The closure that will replace 'httplib2.Http.request'.
    def new_request(
        uri,
        method="GET",
        body=None,
        headers=None,
        redirections=httplib2.DEFAULT_MAX_REDIRECTS,
        connection_type=None,
    ):
        """Modify the request headers to add the user-agent."""
        if headers is None:
            headers = {}
        if "user-agent" in headers:
            headers["user-agent"] = user_agent + " " + headers["user-agent"]
        else:
            headers["user-agent"] = user_agent
        resp, content = request_orig(
            uri,
            method=method,
            body=body,
            headers=headers,
            redirections=redirections,
            connection_type=connection_type,
        )
        return resp, content

    http.request = new_request
    return http


def tunnel_patch(http):
    """Tunnel PATCH requests over POST.
    Args:
       http - An instance of httplib2.Http
           or something that acts like it.

    Returns:
       A modified instance of http that was passed in.

    Example:

      h = httplib2.Http()
      h = tunnel_patch(h, "my-app-name/6.0")

    Useful if you are running on a platform that doesn't support PATCH.
    Apply this last if you are using OAuth 1.0, as changing the method
    will result in a different signature.
    """
    request_orig = http.request

    # The closure that will replace 'httplib2.Http.request'.
    def new_request(
        uri,
        method="GET",
        body=None,
        headers=None,
        redirections=httplib2.DEFAULT_MAX_REDIRECTS,
        connection_type=None,
    ):
        """Modify the request headers to add the user-agent."""
        if headers is None:
            headers = {}
        if method == "PATCH":
            if "oauth_token" in headers.get("authorization", ""):
                LOGGER.warning(
                    "OAuth 1.0 request made with Credentials after tunnel_patch."
                )
            headers["x-http-method-override"] = "PATCH"
            method = "POST"
        resp, content = request_orig(
            uri,
            method=method,
            body=body,
            headers=headers,
            redirections=redirections,
            connection_type=connection_type,
        )
        return resp, content

    http.request = new_request
    return http


def build_http():
    """Builds httplib2.Http object

    Returns:
    A httplib2.Http object, which is used to make http requests, and which has timeout set by default.
    To override default timeout call

      socket.setdefaulttimeout(timeout_in_sec)

    before interacting with this method.
    """
    if socket.getdefaulttimeout() is not None:
        http_timeout = socket.getdefaulttimeout()
    else:
        http_timeout = DEFAULT_HTTP_TIMEOUT_SEC
    http = httplib2.Http(timeout=http_timeout)
    # 308's are used by several Google APIs (Drive, YouTube)
    # for Resumable Uploads rather than Permanent Redirects.
    # This asks httplib2 to exclude 308s from the status codes
    # it treats as redirects
    try:
        http.redirect_codes = http.redirect_codes - {308}
    except AttributeError:
        # Apache Beam tests depend on this library and cannot
        # currently upgrade their httplib2 version
        # http.redirect_codes does not exist in previous versions
        # of httplib2, so pass
        pass

    return http

# === NexusCore/openenv\Lib\site-packages\anthropic\resources\beta\prompt_caching\messages.py ===
# File generated from our OpenAPI spec by Stainless. See CONTRIBUTING.md for details.

from __future__ import annotations

from typing import List, Union, Iterable
from functools import partial
from itertools import chain
from typing_extensions import Literal, overload

import httpx

from .... import _legacy_response
from ...._types import NOT_GIVEN, Body, Query, Headers, NotGiven
from ...._utils import (
    is_given,
    required_args,
    maybe_transform,
    strip_not_given,
    async_maybe_transform,
)
from ...._compat import cached_property
from ...._resource import SyncAPIResource, AsyncAPIResource
from ...._response import to_streamed_response_wrapper, async_to_streamed_response_wrapper
from ...._constants import DEFAULT_TIMEOUT
from ...._streaming import Stream, AsyncStream
from ...._base_client import make_request_options
from ....lib.streaming import PromptCachingBetaMessageStreamManager, AsyncPromptCachingBetaMessageStreamManager
from ....types.model_param import ModelParam
from ....types.metadata_param import MetadataParam
from ....types.tool_choice_param import ToolChoiceParam
from ....types.beta.prompt_caching import message_create_params
from ....types.anthropic_beta_param import AnthropicBetaParam
from ....types.beta.prompt_caching.prompt_caching_beta_message import PromptCachingBetaMessage
from ....types.beta.prompt_caching.prompt_caching_beta_tool_param import PromptCachingBetaToolParam
from ....types.beta.prompt_caching.prompt_caching_beta_message_param import PromptCachingBetaMessageParam
from ....types.beta.prompt_caching.prompt_caching_beta_text_block_param import PromptCachingBetaTextBlockParam
from ....types.beta.prompt_caching.raw_prompt_caching_beta_message_stream_event import (
    RawPromptCachingBetaMessageStreamEvent,
)

__all__ = ["Messages", "AsyncMessages"]


class Messages(SyncAPIResource):
    @cached_property
    def with_raw_response(self) -> MessagesWithRawResponse:
        """
        This property can be used as a prefix for any HTTP method call to return the
        the raw response object instead of the parsed content.

        For more information, see https://www.github.com/anthropics/anthropic-sdk-python#accessing-raw-response-data-eg-headers
        """
        return MessagesWithRawResponse(self)

    @cached_property
    def with_streaming_response(self) -> MessagesWithStreamingResponse:
        """
        An alternative to `.with_raw_response` that doesn't eagerly read the response body.

        For more information, see https://www.github.com/anthropics/anthropic-sdk-python#with_streaming_response
        """
        return MessagesWithStreamingResponse(self)

    @overload
    def create(
        self,
        *,
        max_tokens: int,
        messages: Iterable[PromptCachingBetaMessageParam],
        model: ModelParam,
        metadata: MetadataParam | NotGiven = NOT_GIVEN,
        stop_sequences: List[str] | NotGiven = NOT_GIVEN,
        stream: Literal[False] | NotGiven = NOT_GIVEN,
        system: Union[str, Iterable[PromptCachingBetaTextBlockParam]] | NotGiven = NOT_GIVEN,
        temperature: float | NotGiven = NOT_GIVEN,
        tool_choice: ToolChoiceParam | NotGiven = NOT_GIVEN,
        tools: Iterable[PromptCachingBetaToolParam] | NotGiven = NOT_GIVEN,
        top_k: int | NotGiven = NOT_GIVEN,
        top_p: float | NotGiven = NOT_GIVEN,
        betas: List[AnthropicBetaParam] | NotGiven = NOT_GIVEN,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> PromptCachingBetaMessage:
        """
        Send a structured list of input messages with text and/or image content, and the
        model will generate the next message in the conversation.

        The Messages API can be used for either single queries or stateless multi-turn
        conversations.

        Args:
          max_tokens: The maximum number of tokens to generate before stopping.

              Note that our models may stop _before_ reaching this maximum. This parameter
              only specifies the absolute maximum number of tokens to generate.

              Different models have different maximum values for this parameter. See
              [models](https://docs.anthropic.com/en/docs/models-overview) for details.

          messages: Input messages.

              Our models are trained to operate on alternating `user` and `assistant`
              conversational turns. When creating a new `Message`, you specify the prior
              conversational turns with the `messages` parameter, and the model then generates
              the next `Message` in the conversation. Consecutive `user` or `assistant` turns
              in your request will be combined into a single turn.

              Each input message must be an object with a `role` and `content`. You can
              specify a single `user`-role message, or you can include multiple `user` and
              `assistant` messages.

              If the final message uses the `assistant` role, the response content will
              continue immediately from the content in that message. This can be used to
              constrain part of the model's response.

              Example with a single `user` message:

              ```json
              [{ "role": "user", "content": "Hello, Claude" }]
              ```

              Example with multiple conversational turns:

              ```json
              [
                { "role": "user", "content": "Hello there." },
                { "role": "assistant", "content": "Hi, I'm Claude. How can I help you?" },
                { "role": "user", "content": "Can you explain LLMs in plain English?" }
              ]
              ```

              Example with a partially-filled response from Claude:

              ```json
              [
                {
                  "role": "user",
                  "content": "What's the Greek name for Sun? (A) Sol (B) Helios (C) Sun"
                },
                { "role": "assistant", "content": "The best answer is (" }
              ]
              ```

              Each input message `content` may be either a single `string` or an array of
              content blocks, where each block has a specific `type`. Using a `string` for
              `content` is shorthand for an array of one content block of type `"text"`. The
              following input messages are equivalent:

              ```json
              { "role": "user", "content": "Hello, Claude" }
              ```

              ```json
              { "role": "user", "content": [{ "type": "text", "text": "Hello, Claude" }] }
              ```

              Starting with Claude 3 models, you can also send image content blocks:

              ```json
              {
                "role": "user",
                "content": [
                  {
                    "type": "image",
                    "source": {
                      "type": "base64",
                      "media_type": "image/jpeg",
                      "data": "/9j/4AAQSkZJRg..."
                    }
                  },
                  { "type": "text", "text": "What is in this image?" }
                ]
              }
              ```

              We currently support the `base64` source type for images, and the `image/jpeg`,
              `image/png`, `image/gif`, and `image/webp` media types.

              See [examples](https://docs.anthropic.com/en/api/messages-examples#vision) for
              more input examples.

              Note that if you want to include a
              [system prompt](https://docs.anthropic.com/en/docs/system-prompts), you can use
              the top-level `system` parameter — there is no `"system"` role for input
              messages in the Messages API.

          model: The model that will complete your prompt.\n\nSee
              [models](https://docs.anthropic.com/en/docs/models-overview) for additional
              details and options.

          metadata: An object describing metadata about the request.

          stop_sequences: Custom text sequences that will cause the model to stop generating.

              Our models will normally stop when they have naturally completed their turn,
              which will result in a response `stop_reason` of `"end_turn"`.

              If you want the model to stop generating when it encounters custom strings of
              text, you can use the `stop_sequences` parameter. If the model encounters one of
              the custom sequences, the response `stop_reason` value will be `"stop_sequence"`
              and the response `stop_sequence` value will contain the matched stop sequence.

          stream: Whether to incrementally stream the response using server-sent events.

              See [streaming](https://docs.anthropic.com/en/api/messages-streaming) for
              details.

          system: System prompt.

              A system prompt is a way of providing context and instructions to Claude, such
              as specifying a particular goal or role. See our
              [guide to system prompts](https://docs.anthropic.com/en/docs/system-prompts).

          temperature: Amount of randomness injected into the response.

              Defaults to `1.0`. Ranges from `0.0` to `1.0`. Use `temperature` closer to `0.0`
              for analytical / multiple choice, and closer to `1.0` for creative and
              generative tasks.

              Note that even with `temperature` of `0.0`, the results will not be fully
              deterministic.

          tool_choice: How the model should use the provided tools. The model can use a specific tool,
              any available tool, or decide by itself.

          tools: Definitions of tools that the model may use.

              If you include `tools` in your API request, the model may return `tool_use`
              content blocks that represent the model's use of those tools. You can then run
              those tools using the tool input generated by the model and then optionally
              return results back to the model using `tool_result` content blocks.

              Each tool definition includes:

              - `name`: Name of the tool.
              - `description`: Optional, but strongly-recommended description of the tool.
              - `input_schema`: [JSON schema](https://json-schema.org/) for the tool `input`
                shape that the model will produce in `tool_use` output content blocks.

              For example, if you defined `tools` as:

              ```json
              [
                {
                  "name": "get_stock_price",
                  "description": "Get the current stock price for a given ticker symbol.",
                  "input_schema": {
                    "type": "object",
                    "properties": {
                      "ticker": {
                        "type": "string",
                        "description": "The stock ticker symbol, e.g. AAPL for Apple Inc."
                      }
                    },
                    "required": ["ticker"]
                  }
                }
              ]
              ```

              And then asked the model "What's the S&P 500 at today?", the model might produce
              `tool_use` content blocks in the response like this:

              ```json
              [
                {
                  "type": "tool_use",
                  "id": "toolu_01D7FLrfh4GYq7yT1ULFeyMV",
                  "name": "get_stock_price",
                  "input": { "ticker": "^GSPC" }
                }
              ]
              ```

              You might then run your `get_stock_price` tool with `{"ticker": "^GSPC"}` as an
              input, and return the following back to the model in a subsequent `user`
              message:

              ```json
              [
                {
                  "type": "tool_result",
                  "tool_use_id": "toolu_01D7FLrfh4GYq7yT1ULFeyMV",
                  "content": "259.75 USD"
                }
              ]
              ```

              Tools can be used for workflows that include running client-side tools and
              functions, or more generally whenever you want the model to produce a particular
              JSON structure of output.

              See our [guide](https://docs.anthropic.com/en/docs/tool-use) for more details.

          top_k: Only sample from the top K options for each subsequent token.

              Used to remove "long tail" low probability responses.
              [Learn more technical details here](https://towardsdatascience.com/how-to-sample-from-language-models-682bceb97277).

              Recommended for advanced use cases only. You usually only need to use
              `temperature`.

          top_p: Use nucleus sampling.

              In nucleus sampling, we compute the cumulative distribution over all the options
              for each subsequent token in decreasing probability order and cut it off once it
              reaches a particular probability specified by `top_p`. You should either alter
              `temperature` or `top_p`, but not both.

              Recommended for advanced use cases only. You usually only need to use
              `temperature`.

          betas: Optional header to specify the beta version(s) you want to use.

          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request, in seconds
        """
        ...

    @overload
    def create(
        self,
        *,
        max_tokens: int,
        messages: Iterable[PromptCachingBetaMessageParam],
        model: ModelParam,
        stream: Literal[True],
        metadata: MetadataParam | NotGiven = NOT_GIVEN,
        stop_sequences: List[str] | NotGiven = NOT_GIVEN,
        system: Union[str, Iterable[PromptCachingBetaTextBlockParam]] | NotGiven = NOT_GIVEN,
        temperature: float | NotGiven = NOT_GIVEN,
        tool_choice: ToolChoiceParam | NotGiven = NOT_GIVEN,
        tools: Iterable[PromptCachingBetaToolParam] | NotGiven = NOT_GIVEN,
        top_k: int | NotGiven = NOT_GIVEN,
        top_p: float | NotGiven = NOT_GIVEN,
        betas: List[AnthropicBetaParam] | NotGiven = NOT_GIVEN,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> Stream[RawPromptCachingBetaMessageStreamEvent]:
        """
        Send a structured list of input messages with text and/or image content, and the
        model will generate the next message in the conversation.

        The Messages API can be used for either single queries or stateless multi-turn
        conversations.

        Args:
          max_tokens: The maximum number of tokens to generate before stopping.

              Note that our models may stop _before_ reaching this maximum. This parameter
              only specifies the absolute maximum number of tokens to generate.

              Different models have different maximum values for this parameter. See
              [models](https://docs.anthropic.com/en/docs/models-overview) for details.

          messages: Input messages.

              Our models are trained to operate on alternating `user` and `assistant`
              conversational turns. When creating a new `Message`, you specify the prior
              conversational turns with the `messages` parameter, and the model then generates
              the next `Message` in the conversation. Consecutive `user` or `assistant` turns
              in your request will be combined into a single turn.

              Each input message must be an object with a `role` and `content`. You can
              specify a single `user`-role message, or you can include multiple `user` and
              `assistant` messages.

              If the final message uses the `assistant` role, the response content will
              continue immediately from the content in that message. This can be used to
              constrain part of the model's response.

              Example with a single `user` message:

              ```json
              [{ "role": "user", "content": "Hello, Claude" }]
              ```

              Example with multiple conversational turns:

              ```json
              [
                { "role": "user", "content": "Hello there." },
                { "role": "assistant", "content": "Hi, I'm Claude. How can I help you?" },
                { "role": "user", "content": "Can you explain LLMs in plain English?" }
              ]
              ```

              Example with a partially-filled response from Claude:

              ```json
              [
                {
                  "role": "user",
                  "content": "What's the Greek name for Sun? (A) Sol (B) Helios (C) Sun"
                },
                { "role": "assistant", "content": "The best answer is (" }
              ]
              ```

              Each input message `content` may be either a single `string` or an array of
              content blocks, where each block has a specific `type`. Using a `string` for
              `content` is shorthand for an array of one content block of type `"text"`. The
              following input messages are equivalent:

              ```json
              { "role": "user", "content": "Hello, Claude" }
              ```

              ```json
              { "role": "user", "content": [{ "type": "text", "text": "Hello, Claude" }] }
              ```

              Starting with Claude 3 models, you can also send image content blocks:

              ```json
              {
                "role": "user",
                "content": [
                  {
                    "type": "image",
                    "source": {
                      "type": "base64",
                      "media_type": "image/jpeg",
                      "data": "/9j/4AAQSkZJRg..."
                    }
                  },
                  { "type": "text", "text": "What is in this image?" }
                ]
              }
              ```

              We currently support the `base64` source type for images, and the `image/jpeg`,
              `image/png`, `image/gif`, and `image/webp` media types.

              See [examples](https://docs.anthropic.com/en/api/messages-examples#vision) for
              more input examples.

              Note that if you want to include a
              [system prompt](https://docs.anthropic.com/en/docs/system-prompts), you can use
              the top-level `system` parameter — there is no `"system"` role for input
              messages in the Messages API.

          model: The model that will complete your prompt.\n\nSee
              [models](https://docs.anthropic.com/en/docs/models-overview) for additional
              details and options.

          stream: Whether to incrementally stream the response using server-sent events.

              See [streaming](https://docs.anthropic.com/en/api/messages-streaming) for
              details.

          metadata: An object describing metadata about the request.

          stop_sequences: Custom text sequences that will cause the model to stop generating.

              Our models will normally stop when they have naturally completed their turn,
              which will result in a response `stop_reason` of `"end_turn"`.

              If you want the model to stop generating when it encounters custom strings of
              text, you can use the `stop_sequences` parameter. If the model encounters one of
              the custom sequences, the response `stop_reason` value will be `"stop_sequence"`
              and the response `stop_sequence` value will contain the matched stop sequence.

          system: System prompt.

              A system prompt is a way of providing context and instructions to Claude, such
              as specifying a particular goal or role. See our
              [guide to system prompts](https://docs.anthropic.com/en/docs/system-prompts).

          temperature: Amount of randomness injected into the response.

              Defaults to `1.0`. Ranges from `0.0` to `1.0`. Use `temperature` closer to `0.0`
              for analytical / multiple choice, and closer to `1.0` for creative and
              generative tasks.

              Note that even with `temperature` of `0.0`, the results will not be fully
              deterministic.

          tool_choice: How the model should use the provided tools. The model can use a specific tool,
              any available tool, or decide by itself.

          tools: Definitions of tools that the model may use.

              If you include `tools` in your API request, the model may return `tool_use`
              content blocks that represent the model's use of those tools. You can then run
              those tools using the tool input generated by the model and then optionally
              return results back to the model using `tool_result` content blocks.

              Each tool definition includes:

              - `name`: Name of the tool.
              - `description`: Optional, but strongly-recommended description of the tool.
              - `input_schema`: [JSON schema](https://json-schema.org/) for the tool `input`
                shape that the model will produce in `tool_use` output content blocks.

              For example, if you defined `tools` as:

              ```json
              [
                {
                  "name": "get_stock_price",
                  "description": "Get the current stock price for a given ticker symbol.",
                  "input_schema": {
                    "type": "object",
                    "properties": {
                      "ticker": {
                        "type": "string",
                        "description": "The stock ticker symbol, e.g. AAPL for Apple Inc."
                      }
                    },
                    "required": ["ticker"]
                  }
                }
              ]
              ```

              And then asked the model "What's the S&P 500 at today?", the model might produce
              `tool_use` content blocks in the response like this:

              ```json
              [
                {
                  "type": "tool_use",
                  "id": "toolu_01D7FLrfh4GYq7yT1ULFeyMV",
                  "name": "get_stock_price",
                  "input": { "ticker": "^GSPC" }
                }
              ]
              ```

              You might then run your `get_stock_price` tool with `{"ticker": "^GSPC"}` as an
              input, and return the following back to the model in a subsequent `user`
              message:

              ```json
              [
                {
                  "type": "tool_result",
                  "tool_use_id": "toolu_01D7FLrfh4GYq7yT1ULFeyMV",
                  "content": "259.75 USD"
                }
              ]
              ```

              Tools can be used for workflows that include running client-side tools and
              functions, or more generally whenever you want the model to produce a particular
              JSON structure of output.

              See our [guide](https://docs.anthropic.com/en/docs/tool-use) for more details.

          top_k: Only sample from the top K options for each subsequent token.

              Used to remove "long tail" low probability responses.
              [Learn more technical details here](https://towardsdatascience.com/how-to-sample-from-language-models-682bceb97277).

              Recommended for advanced use cases only. You usually only need to use
              `temperature`.

          top_p: Use nucleus sampling.

              In nucleus sampling, we compute the cumulative distribution over all the options
              for each subsequent token in decreasing probability order and cut it off once it
              reaches a particular probability specified by `top_p`. You should either alter
              `temperature` or `top_p`, but not both.

              Recommended for advanced use cases only. You usually only need to use
              `temperature`.

          betas: Optional header to specify the beta version(s) you want to use.

          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request, in seconds
        """
        ...

    @overload
    def create(
        self,
        *,
        max_tokens: int,
        messages: Iterable[PromptCachingBetaMessageParam],
        model: ModelParam,
        stream: bool,
        metadata: MetadataParam | NotGiven = NOT_GIVEN,
        stop_sequences: List[str] | NotGiven = NOT_GIVEN,
        system: Union[str, Iterable[PromptCachingBetaTextBlockParam]] | NotGiven = NOT_GIVEN,
        temperature: float | NotGiven = NOT_GIVEN,
        tool_choice: ToolChoiceParam | NotGiven = NOT_GIVEN,
        tools: Iterable[PromptCachingBetaToolParam] | NotGiven = NOT_GIVEN,
        top_k: int | NotGiven = NOT_GIVEN,
        top_p: float | NotGiven = NOT_GIVEN,
        betas: List[AnthropicBetaParam] | NotGiven = NOT_GIVEN,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> PromptCachingBetaMessage | Stream[RawPromptCachingBetaMessageStreamEvent]:
        """
        Send a structured list of input messages with text and/or image content, and the
        model will generate the next message in the conversation.

        The Messages API can be used for either single queries or stateless multi-turn
        conversations.

        Args:
          max_tokens: The maximum number of tokens to generate before stopping.

              Note that our models may stop _before_ reaching this maximum. This parameter
              only specifies the absolute maximum number of tokens to generate.

              Different models have different maximum values for this parameter. See
              [models](https://docs.anthropic.com/en/docs/models-overview) for details.

          messages: Input messages.

              Our models are trained to operate on alternating `user` and `assistant`
              conversational turns. When creating a new `Message`, you specify the prior
              conversational turns with the `messages` parameter, and the model then generates
              the next `Message` in the conversation. Consecutive `user` or `assistant` turns
              in your request will be combined into a single turn.

              Each input message must be an object with a `role` and `content`. You can
              specify a single `user`-role message, or you can include multiple `user` and
              `assistant` messages.

              If the final message uses the `assistant` role, the response content will
              continue immediately from the content in that message. This can be used to
              constrain part of the model's response.

              Example with a single `user` message:

              ```json
              [{ "role": "user", "content": "Hello, Claude" }]
              ```

              Example with multiple conversational turns:

              ```json
              [
                { "role": "user", "content": "Hello there." },
                { "role": "assistant", "content": "Hi, I'm Claude. How can I help you?" },
                { "role": "user", "content": "Can you explain LLMs in plain English?" }
              ]
              ```

              Example with a partially-filled response from Claude:

              ```json
              [
                {
                  "role": "user",
                  "content": "What's the Greek name for Sun? (A) Sol (B) Helios (C) Sun"
                },
                { "role": "assistant", "content": "The best answer is (" }
              ]
              ```

              Each input message `content` may be either a single `string` or an array of
              content blocks, where each block has a specific `type`. Using a `string` for
              `content` is shorthand for an array of one content block of type `"text"`. The
              following input messages are equivalent:

              ```json
              { "role": "user", "content": "Hello, Claude" }
              ```

              ```json
              { "role": "user", "content": [{ "type": "text", "text": "Hello, Claude" }] }
              ```

              Starting with Claude 3 models, you can also send image content blocks:

              ```json
              {
                "role": "user",
                "content": [
                  {
                    "type": "image",
                    "source": {
                      "type": "base64",
                      "media_type": "image/jpeg",
                      "data": "/9j/4AAQSkZJRg..."
                    }
                  },
                  { "type": "text", "text": "What is in this image?" }
                ]
              }
              ```

              We currently support the `base64` source type for images, and the `image/jpeg`,
              `image/png`, `image/gif`, and `image/webp` media types.

              See [examples](https://docs.anthropic.com/en/api/messages-examples#vision) for
              more input examples.

              Note that if you want to include a
              [system prompt](https://docs.anthropic.com/en/docs/system-prompts), you can use
              the top-level `system` parameter — there is no `"system"` role for input
              messages in the Messages API.

          model: The model that will complete your prompt.\n\nSee
              [models](https://docs.anthropic.com/en/docs/models-overview) for additional
              details and options.

          stream: Whether to incrementally stream the response using server-sent events.

              See [streaming](https://docs.anthropic.com/en/api/messages-streaming) for
              details.

          metadata: An object describing metadata about the request.

          stop_sequences: Custom text sequences that will cause the model to stop generating.

              Our models will normally stop when they have naturally completed their turn,
              which will result in a response `stop_reason` of `"end_turn"`.

              If you want the model to stop generating when it encounters custom strings of
              text, you can use the `stop_sequences` parameter. If the model encounters one of
              the custom sequences, the response `stop_reason` value will be `"stop_sequence"`
              and the response `stop_sequence` value will contain the matched stop sequence.

          system: System prompt.

              A system prompt is a way of providing context and instructions to Claude, such
              as specifying a particular goal or role. See our
              [guide to system prompts](https://docs.anthropic.com/en/docs/system-prompts).

          temperature: Amount of randomness injected into the response.

              Defaults to `1.0`. Ranges from `0.0` to `1.0`. Use `temperature` closer to `0.0`
              for analytical / multiple choice, and closer to `1.0` for creative and
              generative tasks.

              Note that even with `temperature` of `0.0`, the results will not be fully
              deterministic.

          tool_choice: How the model should use the provided tools. The model can use a specific tool,
              any available tool, or decide by itself.

          tools: Definitions of tools that the model may use.

              If you include `tools` in your API request, the model may return `tool_use`
              content blocks that represent the model's use of those tools. You can then run
              those tools using the tool input generated by the model and then optionally
              return results back to the model using `tool_result` content blocks.

              Each tool definition includes:

              - `name`: Name of the tool.
              - `description`: Optional, but strongly-recommended description of the tool.
              - `input_schema`: [JSON schema](https://json-schema.org/) for the tool `input`
                shape that the model will produce in `tool_use` output content blocks.

              For example, if you defined `tools` as:

              ```json
              [
                {
                  "name": "get_stock_price",
                  "description": "Get the current stock price for a given ticker symbol.",
                  "input_schema": {
                    "type": "object",
                    "properties": {
                      "ticker": {
                        "type": "string",
                        "description": "The stock ticker symbol, e.g. AAPL for Apple Inc."
                      }
                    },
                    "required": ["ticker"]
                  }
                }
              ]
              ```

              And then asked the model "What's the S&P 500 at today?", the model might produce
              `tool_use` content blocks in the response like this:

              ```json
              [
                {
                  "type": "tool_use",
                  "id": "toolu_01D7FLrfh4GYq7yT1ULFeyMV",
                  "name": "get_stock_price",
                  "input": { "ticker": "^GSPC" }
                }
              ]
              ```

              You might then run your `get_stock_price` tool with `{"ticker": "^GSPC"}` as an
              input, and return the following back to the model in a subsequent `user`
              message:

              ```json
              [
                {
                  "type": "tool_result",
                  "tool_use_id": "toolu_01D7FLrfh4GYq7yT1ULFeyMV",
                  "content": "259.75 USD"
                }
              ]
              ```

              Tools can be used for workflows that include running client-side tools and
              functions, or more generally whenever you want the model to produce a particular
              JSON structure of output.

              See our [guide](https://docs.anthropic.com/en/docs/tool-use) for more details.

          top_k: Only sample from the top K options for each subsequent token.

              Used to remove "long tail" low probability responses.
              [Learn more technical details here](https://towardsdatascience.com/how-to-sample-from-language-models-682bceb97277).

              Recommended for advanced use cases only. You usually only need to use
              `temperature`.

          top_p: Use nucleus sampling.

              In nucleus sampling, we compute the cumulative distribution over all the options
              for each subsequent token in decreasing probability order and cut it off once it
              reaches a particular probability specified by `top_p`. You should either alter
              `temperature` or `top_p`, but not both.

              Recommended for advanced use cases only. You usually only need to use
              `temperature`.

          betas: Optional header to specify the beta version(s) you want to use.

          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request, in seconds
        """
        ...

    @required_args(["max_tokens", "messages", "model"], ["max_tokens", "messages", "model", "stream"])
    def create(
        self,
        *,
        max_tokens: int,
        messages: Iterable[PromptCachingBetaMessageParam],
        model: ModelParam,
        metadata: MetadataParam | NotGiven = NOT_GIVEN,
        stop_sequences: List[str] | NotGiven = NOT_GIVEN,
        stream: Literal[False] | Literal[True] | NotGiven = NOT_GIVEN,
        system: Union[str, Iterable[PromptCachingBetaTextBlockParam]] | NotGiven = NOT_GIVEN,
        temperature: float | NotGiven = NOT_GIVEN,
        tool_choice: ToolChoiceParam | NotGiven = NOT_GIVEN,
        tools: Iterable[PromptCachingBetaToolParam] | NotGiven = NOT_GIVEN,
        top_k: int | NotGiven = NOT_GIVEN,
        top_p: float | NotGiven = NOT_GIVEN,
        betas: List[AnthropicBetaParam] | NotGiven = NOT_GIVEN,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> PromptCachingBetaMessage | Stream[RawPromptCachingBetaMessageStreamEvent]:
        if not is_given(timeout) and self._client.timeout == DEFAULT_TIMEOUT:
            timeout = 600
        extra_headers = {
            **strip_not_given(
                {
                    "anthropic-beta": ",".join(chain((str(e) for e in betas), ["prompt-caching-2024-07-31"]))
                    if is_given(betas)
                    else NOT_GIVEN
                }
            ),
            **(extra_headers or {}),
        }
        extra_headers = {"anthropic-beta": "prompt-caching-2024-07-31", **(extra_headers or {})}
        return self._post(
            "/v1/messages?beta=prompt_caching",
            body=maybe_transform(
                {
                    "max_tokens": max_tokens,
                    "messages": messages,
                    "model": model,
                    "metadata": metadata,
                    "stop_sequences": stop_sequences,
                    "stream": stream,
                    "system": system,
                    "temperature": temperature,
                    "tool_choice": tool_choice,
                    "tools": tools,
                    "top_k": top_k,
                    "top_p": top_p,
                },
                message_create_params.MessageCreateParams,
            ),
            options=make_request_options(
                extra_headers=extra_headers, extra_query=extra_query, extra_body=extra_body, timeout=timeout
            ),
            cast_to=PromptCachingBetaMessage,
            stream=stream or False,
            stream_cls=Stream[RawPromptCachingBetaMessageStreamEvent],
        )

    def stream(
        self,
        *,
        max_tokens: int,
        messages: Iterable[PromptCachingBetaMessageParam],
        model: ModelParam,
        metadata: message_create_params.Metadata | NotGiven = NOT_GIVEN,
        stop_sequences: List[str] | NotGiven = NOT_GIVEN,
        system: Union[str, Iterable[PromptCachingBetaTextBlockParam]] | NotGiven = NOT_GIVEN,
        temperature: float | NotGiven = NOT_GIVEN,
        tool_choice: message_create_params.ToolChoice | NotGiven = NOT_GIVEN,
        tools: Iterable[PromptCachingBetaToolParam] | NotGiven = NOT_GIVEN,
        top_k: int | NotGiven = NOT_GIVEN,
        top_p: float | NotGiven = NOT_GIVEN,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> PromptCachingBetaMessageStreamManager:
        """Create a Message stream"""
        if not is_given(timeout) and self._client.timeout == DEFAULT_TIMEOUT:
            timeout = 600

        extra_headers = {
            "anthropic-beta": "prompt-caching-2024-07-31",
            "X-Stainless-Stream-Helper": "beta.prompt_caching.messages",
            **(extra_headers or {}),
        }
        request = partial(
            self._post,
            "/v1/messages?beta=prompt_caching",
            body=maybe_transform(
                {
                    "max_tokens": max_tokens,
                    "messages": messages,
                    "model": model,
                    "metadata": metadata,
                    "stop_sequences": stop_sequences,
                    "stream": True,
                    "system": system,
                    "temperature": temperature,
                    "tool_choice": tool_choice,
                    "tools": tools,
                    "top_k": top_k,
                    "top_p": top_p,
                },
                message_create_params.MessageCreateParams,
            ),
            options=make_request_options(
                extra_headers=extra_headers, extra_query=extra_query, extra_body=extra_body, timeout=timeout
            ),
            cast_to=PromptCachingBetaMessage,
            stream=True,
            stream_cls=Stream[RawPromptCachingBetaMessageStreamEvent],
        )
        return PromptCachingBetaMessageStreamManager(request)


class AsyncMessages(AsyncAPIResource):
    @cached_property
    def with_raw_response(self) -> AsyncMessagesWithRawResponse:
        """
        This property can be used as a prefix for any HTTP method call to return the
        the raw response object instead of the parsed content.

        For more information, see https://www.github.com/anthropics/anthropic-sdk-python#accessing-raw-response-data-eg-headers
        """
        return AsyncMessagesWithRawResponse(self)

    @cached_property
    def with_streaming_response(self) -> AsyncMessagesWithStreamingResponse:
        """
        An alternative to `.with_raw_response` that doesn't eagerly read the response body.

        For more information, see https://www.github.com/anthropics/anthropic-sdk-python#with_streaming_response
        """
        return AsyncMessagesWithStreamingResponse(self)

    @overload
    async def create(
        self,
        *,
        max_tokens: int,
        messages: Iterable[PromptCachingBetaMessageParam],
        model: ModelParam,
        metadata: MetadataParam | NotGiven = NOT_GIVEN,
        stop_sequences: List[str] | NotGiven = NOT_GIVEN,
        stream: Literal[False] | NotGiven = NOT_GIVEN,
        system: Union[str, Iterable[PromptCachingBetaTextBlockParam]] | NotGiven = NOT_GIVEN,
        temperature: float | NotGiven = NOT_GIVEN,
        tool_choice: ToolChoiceParam | NotGiven = NOT_GIVEN,
        tools: Iterable[PromptCachingBetaToolParam] | NotGiven = NOT_GIVEN,
        top_k: int | NotGiven = NOT_GIVEN,
        top_p: float | NotGiven = NOT_GIVEN,
        betas: List[AnthropicBetaParam] | NotGiven = NOT_GIVEN,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> PromptCachingBetaMessage:
        """
        Send a structured list of input messages with text and/or image content, and the
        model will generate the next message in the conversation.

        The Messages API can be used for either single queries or stateless multi-turn
        conversations.

        Args:
          max_tokens: The maximum number of tokens to generate before stopping.

              Note that our models may stop _before_ reaching this maximum. This parameter
              only specifies the absolute maximum number of tokens to generate.

              Different models have different maximum values for this parameter. See
              [models](https://docs.anthropic.com/en/docs/models-overview) for details.

          messages: Input messages.

              Our models are trained to operate on alternating `user` and `assistant`
              conversational turns. When creating a new `Message`, you specify the prior
              conversational turns with the `messages` parameter, and the model then generates
              the next `Message` in the conversation. Consecutive `user` or `assistant` turns
              in your request will be combined into a single turn.

              Each input message must be an object with a `role` and `content`. You can
              specify a single `user`-role message, or you can include multiple `user` and
              `assistant` messages.

              If the final message uses the `assistant` role, the response content will
              continue immediately from the content in that message. This can be used to
              constrain part of the model's response.

              Example with a single `user` message:

              ```json
              [{ "role": "user", "content": "Hello, Claude" }]
              ```

              Example with multiple conversational turns:

              ```json
              [
                { "role": "user", "content": "Hello there." },
                { "role": "assistant", "content": "Hi, I'm Claude. How can I help you?" },
                { "role": "user", "content": "Can you explain LLMs in plain English?" }
              ]
              ```

              Example with a partially-filled response from Claude:

              ```json
              [
                {
                  "role": "user",
                  "content": "What's the Greek name for Sun? (A) Sol (B) Helios (C) Sun"
                },
                { "role": "assistant", "content": "The best answer is (" }
              ]
              ```

              Each input message `content` may be either a single `string` or an array of
              content blocks, where each block has a specific `type`. Using a `string` for
              `content` is shorthand for an array of one content block of type `"text"`. The
              following input messages are equivalent:

              ```json
              { "role": "user", "content": "Hello, Claude" }
              ```

              ```json
              { "role": "user", "content": [{ "type": "text", "text": "Hello, Claude" }] }
              ```

              Starting with Claude 3 models, you can also send image content blocks:

              ```json
              {
                "role": "user",
                "content": [
                  {
                    "type": "image",
                    "source": {
                      "type": "base64",
                      "media_type": "image/jpeg",
                      "data": "/9j/4AAQSkZJRg..."
                    }
                  },
                  { "type": "text", "text": "What is in this image?" }
                ]
              }
              ```

              We currently support the `base64` source type for images, and the `image/jpeg`,
              `image/png`, `image/gif`, and `image/webp` media types.

              See [examples](https://docs.anthropic.com/en/api/messages-examples#vision) for
              more input examples.

              Note that if you want to include a
              [system prompt](https://docs.anthropic.com/en/docs/system-prompts), you can use
              the top-level `system` parameter — there is no `"system"` role for input
              messages in the Messages API.

          model: The model that will complete your prompt.\n\nSee
              [models](https://docs.anthropic.com/en/docs/models-overview) for additional
              details and options.

          metadata: An object describing metadata about the request.

          stop_sequences: Custom text sequences that will cause the model to stop generating.

              Our models will normally stop when they have naturally completed their turn,
              which will result in a response `stop_reason` of `"end_turn"`.

              If you want the model to stop generating when it encounters custom strings of
              text, you can use the `stop_sequences` parameter. If the model encounters one of
              the custom sequences, the response `stop_reason` value will be `"stop_sequence"`
              and the response `stop_sequence` value will contain the matched stop sequence.

          stream: Whether to incrementally stream the response using server-sent events.

              See [streaming](https://docs.anthropic.com/en/api/messages-streaming) for
              details.

          system: System prompt.

              A system prompt is a way of providing context and instructions to Claude, such
              as specifying a particular goal or role. See our
              [guide to system prompts](https://docs.anthropic.com/en/docs/system-prompts).

          temperature: Amount of randomness injected into the response.

              Defaults to `1.0`. Ranges from `0.0` to `1.0`. Use `temperature` closer to `0.0`
              for analytical / multiple choice, and closer to `1.0` for creative and
              generative tasks.

              Note that even with `temperature` of `0.0`, the results will not be fully
              deterministic.

          tool_choice: How the model should use the provided tools. The model can use a specific tool,
              any available tool, or decide by itself.

          tools: Definitions of tools that the model may use.

              If you include `tools` in your API request, the model may return `tool_use`
              content blocks that represent the model's use of those tools. You can then run
              those tools using the tool input generated by the model and then optionally
              return results back to the model using `tool_result` content blocks.

              Each tool definition includes:

              - `name`: Name of the tool.
              - `description`: Optional, but strongly-recommended description of the tool.
              - `input_schema`: [JSON schema](https://json-schema.org/) for the tool `input`
                shape that the model will produce in `tool_use` output content blocks.

              For example, if you defined `tools` as:

              ```json
              [
                {
                  "name": "get_stock_price",
                  "description": "Get the current stock price for a given ticker symbol.",
                  "input_schema": {
                    "type": "object",
                    "properties": {
                      "ticker": {
                        "type": "string",
                        "description": "The stock ticker symbol, e.g. AAPL for Apple Inc."
                      }
                    },
                    "required": ["ticker"]
                  }
                }
              ]
              ```

              And then asked the model "What's the S&P 500 at today?", the model might produce
              `tool_use` content blocks in the response like this:

              ```json
              [
                {
                  "type": "tool_use",
                  "id": "toolu_01D7FLrfh4GYq7yT1ULFeyMV",
                  "name": "get_stock_price",
                  "input": { "ticker": "^GSPC" }
                }
              ]
              ```

              You might then run your `get_stock_price` tool with `{"ticker": "^GSPC"}` as an
              input, and return the following back to the model in a subsequent `user`
              message:

              ```json
              [
                {
                  "type": "tool_result",
                  "tool_use_id": "toolu_01D7FLrfh4GYq7yT1ULFeyMV",
                  "content": "259.75 USD"
                }
              ]
              ```

              Tools can be used for workflows that include running client-side tools and
              functions, or more generally whenever you want the model to produce a particular
              JSON structure of output.

              See our [guide](https://docs.anthropic.com/en/docs/tool-use) for more details.

          top_k: Only sample from the top K options for each subsequent token.

              Used to remove "long tail" low probability responses.
              [Learn more technical details here](https://towardsdatascience.com/how-to-sample-from-language-models-682bceb97277).

              Recommended for advanced use cases only. You usually only need to use
              `temperature`.

          top_p: Use nucleus sampling.

              In nucleus sampling, we compute the cumulative distribution over all the options
              for each subsequent token in decreasing probability order and cut it off once it
              reaches a particular probability specified by `top_p`. You should either alter
              `temperature` or `top_p`, but not both.

              Recommended for advanced use cases only. You usually only need to use
              `temperature`.

          betas: Optional header to specify the beta version(s) you want to use.

          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request, in seconds
        """
        ...

    @overload
    async def create(
        self,
        *,
        max_tokens: int,
        messages: Iterable[PromptCachingBetaMessageParam],
        model: ModelParam,
        stream: Literal[True],
        metadata: MetadataParam | NotGiven = NOT_GIVEN,
        stop_sequences: List[str] | NotGiven = NOT_GIVEN,
        system: Union[str, Iterable[PromptCachingBetaTextBlockParam]] | NotGiven = NOT_GIVEN,
        temperature: float | NotGiven = NOT_GIVEN,
        tool_choice: ToolChoiceParam | NotGiven = NOT_GIVEN,
        tools: Iterable[PromptCachingBetaToolParam] | NotGiven = NOT_GIVEN,
        top_k: int | NotGiven = NOT_GIVEN,
        top_p: float | NotGiven = NOT_GIVEN,
        betas: List[AnthropicBetaParam] | NotGiven = NOT_GIVEN,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> AsyncStream[RawPromptCachingBetaMessageStreamEvent]:
        """
        Send a structured list of input messages with text and/or image content, and the
        model will generate the next message in the conversation.

        The Messages API can be used for either single queries or stateless multi-turn
        conversations.

        Args:
          max_tokens: The maximum number of tokens to generate before stopping.

              Note that our models may stop _before_ reaching this maximum. This parameter
              only specifies the absolute maximum number of tokens to generate.

              Different models have different maximum values for this parameter. See
              [models](https://docs.anthropic.com/en/docs/models-overview) for details.

          messages: Input messages.

              Our models are trained to operate on alternating `user` and `assistant`
              conversational turns. When creating a new `Message`, you specify the prior
              conversational turns with the `messages` parameter, and the model then generates
              the next `Message` in the conversation. Consecutive `user` or `assistant` turns
              in your request will be combined into a single turn.

              Each input message must be an object with a `role` and `content`. You can
              specify a single `user`-role message, or you can include multiple `user` and
              `assistant` messages.

              If the final message uses the `assistant` role, the response content will
              continue immediately from the content in that message. This can be used to
              constrain part of the model's response.

              Example with a single `user` message:

              ```json
              [{ "role": "user", "content": "Hello, Claude" }]
              ```

              Example with multiple conversational turns:

              ```json
              [
                { "role": "user", "content": "Hello there." },
                { "role": "assistant", "content": "Hi, I'm Claude. How can I help you?" },
                { "role": "user", "content": "Can you explain LLMs in plain English?" }
              ]
              ```

              Example with a partially-filled response from Claude:

              ```json
              [
                {
                  "role": "user",
                  "content": "What's the Greek name for Sun? (A) Sol (B) Helios (C) Sun"
                },
                { "role": "assistant", "content": "The best answer is (" }
              ]
              ```

              Each input message `content` may be either a single `string` or an array of
              content blocks, where each block has a specific `type`. Using a `string` for
              `content` is shorthand for an array of one content block of type `"text"`. The
              following input messages are equivalent:

              ```json
              { "role": "user", "content": "Hello, Claude" }
              ```

              ```json
              { "role": "user", "content": [{ "type": "text", "text": "Hello, Claude" }] }
              ```

              Starting with Claude 3 models, you can also send image content blocks:

              ```json
              {
                "role": "user",
                "content": [
                  {
                    "type": "image",
                    "source": {
                      "type": "base64",
                      "media_type": "image/jpeg",
                      "data": "/9j/4AAQSkZJRg..."
                    }
                  },
                  { "type": "text", "text": "What is in this image?" }
                ]
              }
              ```

              We currently support the `base64` source type for images, and the `image/jpeg`,
              `image/png`, `image/gif`, and `image/webp` media types.

              See [examples](https://docs.anthropic.com/en/api/messages-examples#vision) for
              more input examples.

              Note that if you want to include a
              [system prompt](https://docs.anthropic.com/en/docs/system-prompts), you can use
              the top-level `system` parameter — there is no `"system"` role for input
              messages in the Messages API.

          model: The model that will complete your prompt.\n\nSee
              [models](https://docs.anthropic.com/en/docs/models-overview) for additional
              details and options.

          stream: Whether to incrementally stream the response using server-sent events.

              See [streaming](https://docs.anthropic.com/en/api/messages-streaming) for
              details.

          metadata: An object describing metadata about the request.

          stop_sequences: Custom text sequences that will cause the model to stop generating.

              Our models will normally stop when they have naturally completed their turn,
              which will result in a response `stop_reason` of `"end_turn"`.

              If you want the model to stop generating when it encounters custom strings of
              text, you can use the `stop_sequences` parameter. If the model encounters one of
              the custom sequences, the response `stop_reason` value will be `"stop_sequence"`
              and the response `stop_sequence` value will contain the matched stop sequence.

          system: System prompt.

              A system prompt is a way of providing context and instructions to Claude, such
              as specifying a particular goal or role. See our
              [guide to system prompts](https://docs.anthropic.com/en/docs/system-prompts).

          temperature: Amount of randomness injected into the response.

              Defaults to `1.0`. Ranges from `0.0` to `1.0`. Use `temperature` closer to `0.0`
              for analytical / multiple choice, and closer to `1.0` for creative and
              generative tasks.

              Note that even with `temperature` of `0.0`, the results will not be fully
              deterministic.

          tool_choice: How the model should use the provided tools. The model can use a specific tool,
              any available tool, or decide by itself.

          tools: Definitions of tools that the model may use.

              If you include `tools` in your API request, the model may return `tool_use`
              content blocks that represent the model's use of those tools. You can then run
              those tools using the tool input generated by the model and then optionally
              return results back to the model using `tool_result` content blocks.

              Each tool definition includes:

              - `name`: Name of the tool.
              - `description`: Optional, but strongly-recommended description of the tool.
              - `input_schema`: [JSON schema](https://json-schema.org/) for the tool `input`
                shape that the model will produce in `tool_use` output content blocks.

              For example, if you defined `tools` as:

              ```json
              [
                {
                  "name": "get_stock_price",
                  "description": "Get the current stock price for a given ticker symbol.",
                  "input_schema": {
                    "type": "object",
                    "properties": {
                      "ticker": {
                        "type": "string",
                        "description": "The stock ticker symbol, e.g. AAPL for Apple Inc."
                      }
                    },
                    "required": ["ticker"]
                  }
                }
              ]
              ```

              And then asked the model "What's the S&P 500 at today?", the model might produce
              `tool_use` content blocks in the response like this:

              ```json
              [
                {
                  "type": "tool_use",
                  "id": "toolu_01D7FLrfh4GYq7yT1ULFeyMV",
                  "name": "get_stock_price",
                  "input": { "ticker": "^GSPC" }
                }
              ]
              ```

              You might then run your `get_stock_price` tool with `{"ticker": "^GSPC"}` as an
              input, and return the following back to the model in a subsequent `user`
              message:

              ```json
              [
                {
                  "type": "tool_result",
                  "tool_use_id": "toolu_01D7FLrfh4GYq7yT1ULFeyMV",
                  "content": "259.75 USD"
                }
              ]
              ```

              Tools can be used for workflows that include running client-side tools and
              functions, or more generally whenever you want the model to produce a particular
              JSON structure of output.

              See our [guide](https://docs.anthropic.com/en/docs/tool-use) for more details.

          top_k: Only sample from the top K options for each subsequent token.

              Used to remove "long tail" low probability responses.
              [Learn more technical details here](https://towardsdatascience.com/how-to-sample-from-language-models-682bceb97277).

              Recommended for advanced use cases only. You usually only need to use
              `temperature`.

          top_p: Use nucleus sampling.

              In nucleus sampling, we compute the cumulative distribution over all the options
              for each subsequent token in decreasing probability order and cut it off once it
              reaches a particular probability specified by `top_p`. You should either alter
              `temperature` or `top_p`, but not both.

              Recommended for advanced use cases only. You usually only need to use
              `temperature`.

          betas: Optional header to specify the beta version(s) you want to use.

          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request, in seconds
        """
        ...

    @overload
    async def create(
        self,
        *,
        max_tokens: int,
        messages: Iterable[PromptCachingBetaMessageParam],
        model: ModelParam,
        stream: bool,
        metadata: MetadataParam | NotGiven = NOT_GIVEN,
        stop_sequences: List[str] | NotGiven = NOT_GIVEN,
        system: Union[str, Iterable[PromptCachingBetaTextBlockParam]] | NotGiven = NOT_GIVEN,
        temperature: float | NotGiven = NOT_GIVEN,
        tool_choice: ToolChoiceParam | NotGiven = NOT_GIVEN,
        tools: Iterable[PromptCachingBetaToolParam] | NotGiven = NOT_GIVEN,
        top_k: int | NotGiven = NOT_GIVEN,
        top_p: float | NotGiven = NOT_GIVEN,
        betas: List[AnthropicBetaParam] | NotGiven = NOT_GIVEN,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> PromptCachingBetaMessage | AsyncStream[RawPromptCachingBetaMessageStreamEvent]:
        """
        Send a structured list of input messages with text and/or image content, and the
        model will generate the next message in the conversation.

        The Messages API can be used for either single queries or stateless multi-turn
        conversations.

        Args:
          max_tokens: The maximum number of tokens to generate before stopping.

              Note that our models may stop _before_ reaching this maximum. This parameter
              only specifies the absolute maximum number of tokens to generate.

              Different models have different maximum values for this parameter. See
              [models](https://docs.anthropic.com/en/docs/models-overview) for details.

          messages: Input messages.

              Our models are trained to operate on alternating `user` and `assistant`
              conversational turns. When creating a new `Message`, you specify the prior
              conversational turns with the `messages` parameter, and the model then generates
              the next `Message` in the conversation. Consecutive `user` or `assistant` turns
              in your request will be combined into a single turn.

              Each input message must be an object with a `role` and `content`. You can
              specify a single `user`-role message, or you can include multiple `user` and
              `assistant` messages.

              If the final message uses the `assistant` role, the response content will
              continue immediately from the content in that message. This can be used to
              constrain part of the model's response.

              Example with a single `user` message:

              ```json
              [{ "role": "user", "content": "Hello, Claude" }]
              ```

              Example with multiple conversational turns:

              ```json
              [
                { "role": "user", "content": "Hello there." },
                { "role": "assistant", "content": "Hi, I'm Claude. How can I help you?" },
                { "role": "user", "content": "Can you explain LLMs in plain English?" }
              ]
              ```

              Example with a partially-filled response from Claude:

              ```json
              [
                {
                  "role": "user",
                  "content": "What's the Greek name for Sun? (A) Sol (B) Helios (C) Sun"
                },
                { "role": "assistant", "content": "The best answer is (" }
              ]
              ```

              Each input message `content` may be either a single `string` or an array of
              content blocks, where each block has a specific `type`. Using a `string` for
              `content` is shorthand for an array of one content block of type `"text"`. The
              following input messages are equivalent:

              ```json
              { "role": "user", "content": "Hello, Claude" }
              ```

              ```json
              { "role": "user", "content": [{ "type": "text", "text": "Hello, Claude" }] }
              ```

              Starting with Claude 3 models, you can also send image content blocks:

              ```json
              {
                "role": "user",
                "content": [
                  {
                    "type": "image",
                    "source": {
                      "type": "base64",
                      "media_type": "image/jpeg",
                      "data": "/9j/4AAQSkZJRg..."
                    }
                  },
                  { "type": "text", "text": "What is in this image?" }
                ]
              }
              ```

              We currently support the `base64` source type for images, and the `image/jpeg`,
              `image/png`, `image/gif`, and `image/webp` media types.

              See [examples](https://docs.anthropic.com/en/api/messages-examples#vision) for
              more input examples.

              Note that if you want to include a
              [system prompt](https://docs.anthropic.com/en/docs/system-prompts), you can use
              the top-level `system` parameter — there is no `"system"` role for input
              messages in the Messages API.

          model: The model that will complete your prompt.\n\nSee
              [models](https://docs.anthropic.com/en/docs/models-overview) for additional
              details and options.

          stream: Whether to incrementally stream the response using server-sent events.

              See [streaming](https://docs.anthropic.com/en/api/messages-streaming) for
              details.

          metadata: An object describing metadata about the request.

          stop_sequences: Custom text sequences that will cause the model to stop generating.

              Our models will normally stop when they have naturally completed their turn,
              which will result in a response `stop_reason` of `"end_turn"`.

              If you want the model to stop generating when it encounters custom strings of
              text, you can use the `stop_sequences` parameter. If the model encounters one of
              the custom sequences, the response `stop_reason` value will be `"stop_sequence"`
              and the response `stop_sequence` value will contain the matched stop sequence.

          system: System prompt.

              A system prompt is a way of providing context and instructions to Claude, such
              as specifying a particular goal or role. See our
              [guide to system prompts](https://docs.anthropic.com/en/docs/system-prompts).

          temperature: Amount of randomness injected into the response.

              Defaults to `1.0`. Ranges from `0.0` to `1.0`. Use `temperature` closer to `0.0`
              for analytical / multiple choice, and closer to `1.0` for creative and
              generative tasks.

              Note that even with `temperature` of `0.0`, the results will not be fully
              deterministic.

          tool_choice: How the model should use the provided tools. The model can use a specific tool,
              any available tool, or decide by itself.

          tools: Definitions of tools that the model may use.

              If you include `tools` in your API request, the model may return `tool_use`
              content blocks that represent the model's use of those tools. You can then run
              those tools using the tool input generated by the model and then optionally
              return results back to the model using `tool_result` content blocks.

              Each tool definition includes:

              - `name`: Name of the tool.
              - `description`: Optional, but strongly-recommended description of the tool.
              - `input_schema`: [JSON schema](https://json-schema.org/) for the tool `input`
                shape that the model will produce in `tool_use` output content blocks.

              For example, if you defined `tools` as:

              ```json
              [
                {
                  "name": "get_stock_price",
                  "description": "Get the current stock price for a given ticker symbol.",
                  "input_schema": {
                    "type": "object",
                    "properties": {
                      "ticker": {
                        "type": "string",
                        "description": "The stock ticker symbol, e.g. AAPL for Apple Inc."
                      }
                    },
                    "required": ["ticker"]
                  }
                }
              ]
              ```

              And then asked the model "What's the S&P 500 at today?", the model might produce
              `tool_use` content blocks in the response like this:

              ```json
              [
                {
                  "type": "tool_use",
                  "id": "toolu_01D7FLrfh4GYq7yT1ULFeyMV",
                  "name": "get_stock_price",
                  "input": { "ticker": "^GSPC" }
                }
              ]
              ```

              You might then run your `get_stock_price` tool with `{"ticker": "^GSPC"}` as an
              input, and return the following back to the model in a subsequent `user`
              message:

              ```json
              [
                {
                  "type": "tool_result",
                  "tool_use_id": "toolu_01D7FLrfh4GYq7yT1ULFeyMV",
                  "content": "259.75 USD"
                }
              ]
              ```

              Tools can be used for workflows that include running client-side tools and
              functions, or more generally whenever you want the model to produce a particular
              JSON structure of output.

              See our [guide](https://docs.anthropic.com/en/docs/tool-use) for more details.

          top_k: Only sample from the top K options for each subsequent token.

              Used to remove "long tail" low probability responses.
              [Learn more technical details here](https://towardsdatascience.com/how-to-sample-from-language-models-682bceb97277).

              Recommended for advanced use cases only. You usually only need to use
              `temperature`.

          top_p: Use nucleus sampling.

              In nucleus sampling, we compute the cumulative distribution over all the options
              for each subsequent token in decreasing probability order and cut it off once it
              reaches a particular probability specified by `top_p`. You should either alter
              `temperature` or `top_p`, but not both.

              Recommended for advanced use cases only. You usually only need to use
              `temperature`.

          betas: Optional header to specify the beta version(s) you want to use.

          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request, in seconds
        """
        ...

    @required_args(["max_tokens", "messages", "model"], ["max_tokens", "messages", "model", "stream"])
    async def create(
        self,
        *,
        max_tokens: int,
        messages: Iterable[PromptCachingBetaMessageParam],
        model: ModelParam,
        metadata: MetadataParam | NotGiven = NOT_GIVEN,
        stop_sequences: List[str] | NotGiven = NOT_GIVEN,
        stream: Literal[False] | Literal[True] | NotGiven = NOT_GIVEN,
        system: Union[str, Iterable[PromptCachingBetaTextBlockParam]] | NotGiven = NOT_GIVEN,
        temperature: float | NotGiven = NOT_GIVEN,
        tool_choice: ToolChoiceParam | NotGiven = NOT_GIVEN,
        tools: Iterable[PromptCachingBetaToolParam] | NotGiven = NOT_GIVEN,
        top_k: int | NotGiven = NOT_GIVEN,
        top_p: float | NotGiven = NOT_GIVEN,
        betas: List[AnthropicBetaParam] | NotGiven = NOT_GIVEN,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> PromptCachingBetaMessage | AsyncStream[RawPromptCachingBetaMessageStreamEvent]:
        if not is_given(timeout) and self._client.timeout == DEFAULT_TIMEOUT:
            timeout = 600
        extra_headers = {
            **strip_not_given(
                {
                    "anthropic-beta": ",".join(chain((str(e) for e in betas), ["prompt-caching-2024-07-31"]))
                    if is_given(betas)
                    else NOT_GIVEN
                }
            ),
            **(extra_headers or {}),
        }
        extra_headers = {"anthropic-beta": "prompt-caching-2024-07-31", **(extra_headers or {})}
        return await self._post(
            "/v1/messages?beta=prompt_caching",
            body=await async_maybe_transform(
                {
                    "max_tokens": max_tokens,
                    "messages": messages,
                    "model": model,
                    "metadata": metadata,
                    "stop_sequences": stop_sequences,
                    "stream": stream,
                    "system": system,
                    "temperature": temperature,
                    "tool_choice": tool_choice,
                    "tools": tools,
                    "top_k": top_k,
                    "top_p": top_p,
                },
                message_create_params.MessageCreateParams,
            ),
            options=make_request_options(
                extra_headers=extra_headers, extra_query=extra_query, extra_body=extra_body, timeout=timeout
            ),
            cast_to=PromptCachingBetaMessage,
            stream=stream or False,
            stream_cls=AsyncStream[RawPromptCachingBetaMessageStreamEvent],
        )

    def stream(
        self,
        *,
        max_tokens: int,
        messages: Iterable[PromptCachingBetaMessageParam],
        model: ModelParam,
        metadata: message_create_params.Metadata | NotGiven = NOT_GIVEN,
        stop_sequences: List[str] | NotGiven = NOT_GIVEN,
        system: Union[str, Iterable[PromptCachingBetaTextBlockParam]] | NotGiven = NOT_GIVEN,
        temperature: float | NotGiven = NOT_GIVEN,
        tool_choice: message_create_params.ToolChoice | NotGiven = NOT_GIVEN,
        tools: Iterable[PromptCachingBetaToolParam] | NotGiven = NOT_GIVEN,
        top_k: int | NotGiven = NOT_GIVEN,
        top_p: float | NotGiven = NOT_GIVEN,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> AsyncPromptCachingBetaMessageStreamManager:
        """Create a Message stream"""
        if not is_given(timeout) and self._client.timeout == DEFAULT_TIMEOUT:
            timeout = 600

        extra_headers = {
            "anthropic-beta": "prompt-caching-2024-07-31",
            "X-Stainless-Stream-Helper": "beta.prompt_caching.messages",
            **(extra_headers or {}),
        }
        request = self._post(
            "/v1/messages?beta=prompt_caching",
            body=maybe_transform(
                {
                    "max_tokens": max_tokens,
                    "messages": messages,
                    "model": model,
                    "metadata": metadata,
                    "stop_sequences": stop_sequences,
                    "stream": True,
                    "system": system,
                    "temperature": temperature,
                    "tool_choice": tool_choice,
                    "tools": tools,
                    "top_k": top_k,
                    "top_p": top_p,
                },
                message_create_params.MessageCreateParams,
            ),
            options=make_request_options(
                extra_headers=extra_headers, extra_query=extra_query, extra_body=extra_body, timeout=timeout
            ),
            cast_to=PromptCachingBetaMessage,
            stream=True,
            stream_cls=AsyncStream[RawPromptCachingBetaMessageStreamEvent],
        )
        return AsyncPromptCachingBetaMessageStreamManager(request)


class MessagesWithRawResponse:
    def __init__(self, messages: Messages) -> None:
        self._messages = messages

        self.create = _legacy_response.to_raw_response_wrapper(
            messages.create,
        )


class AsyncMessagesWithRawResponse:
    def __init__(self, messages: AsyncMessages) -> None:
        self._messages = messages

        self.create = _legacy_response.async_to_raw_response_wrapper(
            messages.create,
        )


class MessagesWithStreamingResponse:
    def __init__(self, messages: Messages) -> None:
        self._messages = messages

        self.create = to_streamed_response_wrapper(
            messages.create,
        )


class AsyncMessagesWithStreamingResponse:
    def __init__(self, messages: AsyncMessages) -> None:
        self._messages = messages

        self.create = async_to_streamed_response_wrapper(
            messages.create,
        )

# === NexusCore/openenv\Lib\site-packages\pycparser\c_parser.py ===
#------------------------------------------------------------------------------
# pycparser: c_parser.py
#
# CParser class: Parser and AST builder for the C language
#
# Eli Bendersky [https://eli.thegreenplace.net/]
# License: BSD
#------------------------------------------------------------------------------
from .ply import yacc

from . import c_ast
from .c_lexer import CLexer
from .plyparser import PLYParser, ParseError, parameterized, template
from .ast_transforms import fix_switch_cases, fix_atomic_specifiers


@template
class CParser(PLYParser):
    def __init__(
            self,
            lex_optimize=True,
            lexer=CLexer,
            lextab='pycparser.lextab',
            yacc_optimize=True,
            yacctab='pycparser.yacctab',
            yacc_debug=False,
            taboutputdir=''):
        """ Create a new CParser.

            Some arguments for controlling the debug/optimization
            level of the parser are provided. The defaults are
            tuned for release/performance mode.
            The simple rules for using them are:
            *) When tweaking CParser/CLexer, set these to False
            *) When releasing a stable parser, set to True

            lex_optimize:
                Set to False when you're modifying the lexer.
                Otherwise, changes in the lexer won't be used, if
                some lextab.py file exists.
                When releasing with a stable lexer, set to True
                to save the re-generation of the lexer table on
                each run.

            lexer:
                Set this parameter to define the lexer to use if
                you're not using the default CLexer.

            lextab:
                Points to the lex table that's used for optimized
                mode. Only if you're modifying the lexer and want
                some tests to avoid re-generating the table, make
                this point to a local lex table file (that's been
                earlier generated with lex_optimize=True)

            yacc_optimize:
                Set to False when you're modifying the parser.
                Otherwise, changes in the parser won't be used, if
                some parsetab.py file exists.
                When releasing with a stable parser, set to True
                to save the re-generation of the parser table on
                each run.

            yacctab:
                Points to the yacc table that's used for optimized
                mode. Only if you're modifying the parser, make
                this point to a local yacc table file

            yacc_debug:
                Generate a parser.out file that explains how yacc
                built the parsing table from the grammar.

            taboutputdir:
                Set this parameter to control the location of generated
                lextab and yacctab files.
        """
        self.clex = lexer(
            error_func=self._lex_error_func,
            on_lbrace_func=self._lex_on_lbrace_func,
            on_rbrace_func=self._lex_on_rbrace_func,
            type_lookup_func=self._lex_type_lookup_func)

        self.clex.build(
            optimize=lex_optimize,
            lextab=lextab,
            outputdir=taboutputdir)
        self.tokens = self.clex.tokens

        rules_with_opt = [
            'abstract_declarator',
            'assignment_expression',
            'declaration_list',
            'declaration_specifiers_no_type',
            'designation',
            'expression',
            'identifier_list',
            'init_declarator_list',
            'id_init_declarator_list',
            'initializer_list',
            'parameter_type_list',
            'block_item_list',
            'type_qualifier_list',
            'struct_declarator_list'
        ]

        for rule in rules_with_opt:
            self._create_opt_rule(rule)

        self.cparser = yacc.yacc(
            module=self,
            start='translation_unit_or_empty',
            debug=yacc_debug,
            optimize=yacc_optimize,
            tabmodule=yacctab,
            outputdir=taboutputdir)

        # Stack of scopes for keeping track of symbols. _scope_stack[-1] is
        # the current (topmost) scope. Each scope is a dictionary that
        # specifies whether a name is a type. If _scope_stack[n][name] is
        # True, 'name' is currently a type in the scope. If it's False,
        # 'name' is used in the scope but not as a type (for instance, if we
        # saw: int name;
        # If 'name' is not a key in _scope_stack[n] then 'name' was not defined
        # in this scope at all.
        self._scope_stack = [dict()]

        # Keeps track of the last token given to yacc (the lookahead token)
        self._last_yielded_token = None

    def parse(self, text, filename='', debug=False):
        """ Parses C code and returns an AST.

            text:
                A string containing the C source code

            filename:
                Name of the file being parsed (for meaningful
                error messages)

            debug:
                Debug flag to YACC
        """
        self.clex.filename = filename
        self.clex.reset_lineno()
        self._scope_stack = [dict()]
        self._last_yielded_token = None
        return self.cparser.parse(
                input=text,
                lexer=self.clex,
                debug=debug)

    ######################--   PRIVATE   --######################

    def _push_scope(self):
        self._scope_stack.append(dict())

    def _pop_scope(self):
        assert len(self._scope_stack) > 1
        self._scope_stack.pop()

    def _add_typedef_name(self, name, coord):
        """ Add a new typedef name (ie a TYPEID) to the current scope
        """
        if not self._scope_stack[-1].get(name, True):
            self._parse_error(
                "Typedef %r previously declared as non-typedef "
                "in this scope" % name, coord)
        self._scope_stack[-1][name] = True

    def _add_identifier(self, name, coord):
        """ Add a new object, function, or enum member name (ie an ID) to the
            current scope
        """
        if self._scope_stack[-1].get(name, False):
            self._parse_error(
                "Non-typedef %r previously declared as typedef "
                "in this scope" % name, coord)
        self._scope_stack[-1][name] = False

    def _is_type_in_scope(self, name):
        """ Is *name* a typedef-name in the current scope?
        """
        for scope in reversed(self._scope_stack):
            # If name is an identifier in this scope it shadows typedefs in
            # higher scopes.
            in_scope = scope.get(name)
            if in_scope is not None: return in_scope
        return False

    def _lex_error_func(self, msg, line, column):
        self._parse_error(msg, self._coord(line, column))

    def _lex_on_lbrace_func(self):
        self._push_scope()

    def _lex_on_rbrace_func(self):
        self._pop_scope()

    def _lex_type_lookup_func(self, name):
        """ Looks up types that were previously defined with
            typedef.
            Passed to the lexer for recognizing identifiers that
            are types.
        """
        is_type = self._is_type_in_scope(name)
        return is_type

    def _get_yacc_lookahead_token(self):
        """ We need access to yacc's lookahead token in certain cases.
            This is the last token yacc requested from the lexer, so we
            ask the lexer.
        """
        return self.clex.last_token

    # To understand what's going on here, read sections A.8.5 and
    # A.8.6 of K&R2 very carefully.
    #
    # A C type consists of a basic type declaration, with a list
    # of modifiers. For example:
    #
    # int *c[5];
    #
    # The basic declaration here is 'int c', and the pointer and
    # the array are the modifiers.
    #
    # Basic declarations are represented by TypeDecl (from module c_ast) and the
    # modifiers are FuncDecl, PtrDecl and ArrayDecl.
    #
    # The standard states that whenever a new modifier is parsed, it should be
    # added to the end of the list of modifiers. For example:
    #
    # K&R2 A.8.6.2: Array Declarators
    #
    # In a declaration T D where D has the form
    #   D1 [constant-expression-opt]
    # and the type of the identifier in the declaration T D1 is
    # "type-modifier T", the type of the
    # identifier of D is "type-modifier array of T"
    #
    # This is what this method does. The declarator it receives
    # can be a list of declarators ending with TypeDecl. It
    # tacks the modifier to the end of this list, just before
    # the TypeDecl.
    #
    # Additionally, the modifier may be a list itself. This is
    # useful for pointers, that can come as a chain from the rule
    # p_pointer. In this case, the whole modifier list is spliced
    # into the new location.
    def _type_modify_decl(self, decl, modifier):
        """ Tacks a type modifier on a declarator, and returns
            the modified declarator.

            Note: the declarator and modifier may be modified
        """
        #~ print '****'
        #~ decl.show(offset=3)
        #~ modifier.show(offset=3)
        #~ print '****'

        modifier_head = modifier
        modifier_tail = modifier

        # The modifier may be a nested list. Reach its tail.
        while modifier_tail.type:
            modifier_tail = modifier_tail.type

        # If the decl is a basic type, just tack the modifier onto it.
        if isinstance(decl, c_ast.TypeDecl):
            modifier_tail.type = decl
            return modifier
        else:
            # Otherwise, the decl is a list of modifiers. Reach
            # its tail and splice the modifier onto the tail,
            # pointing to the underlying basic type.
            decl_tail = decl

            while not isinstance(decl_tail.type, c_ast.TypeDecl):
                decl_tail = decl_tail.type

            modifier_tail.type = decl_tail.type
            decl_tail.type = modifier_head
            return decl

    # Due to the order in which declarators are constructed,
    # they have to be fixed in order to look like a normal AST.
    #
    # When a declaration arrives from syntax construction, it has
    # these problems:
    # * The innermost TypeDecl has no type (because the basic
    #   type is only known at the uppermost declaration level)
    # * The declaration has no variable name, since that is saved
    #   in the innermost TypeDecl
    # * The typename of the declaration is a list of type
    #   specifiers, and not a node. Here, basic identifier types
    #   should be separated from more complex types like enums
    #   and structs.
    #
    # This method fixes these problems.
    def _fix_decl_name_type(self, decl, typename):
        """ Fixes a declaration. Modifies decl.
        """
        # Reach the underlying basic type
        #
        type = decl
        while not isinstance(type, c_ast.TypeDecl):
            type = type.type

        decl.name = type.declname
        type.quals = decl.quals[:]

        # The typename is a list of types. If any type in this
        # list isn't an IdentifierType, it must be the only
        # type in the list (it's illegal to declare "int enum ..")
        # If all the types are basic, they're collected in the
        # IdentifierType holder.
        for tn in typename:
            if not isinstance(tn, c_ast.IdentifierType):
                if len(typename) > 1:
                    self._parse_error(
                        "Invalid multiple types specified", tn.coord)
                else:
                    type.type = tn
                    return decl

        if not typename:
            # Functions default to returning int
            #
            if not isinstance(decl.type, c_ast.FuncDecl):
                self._parse_error(
                        "Missing type in declaration", decl.coord)
            type.type = c_ast.IdentifierType(
                    ['int'],
                    coord=decl.coord)
        else:
            # At this point, we know that typename is a list of IdentifierType
            # nodes. Concatenate all the names into a single list.
            #
            type.type = c_ast.IdentifierType(
                [name for id in typename for name in id.names],
                coord=typename[0].coord)
        return decl

    def _add_declaration_specifier(self, declspec, newspec, kind, append=False):
        """ Declaration specifiers are represented by a dictionary
            with the entries:
            * qual: a list of type qualifiers
            * storage: a list of storage type qualifiers
            * type: a list of type specifiers
            * function: a list of function specifiers
            * alignment: a list of alignment specifiers

            This method is given a declaration specifier, and a
            new specifier of a given kind.
            If `append` is True, the new specifier is added to the end of
            the specifiers list, otherwise it's added at the beginning.
            Returns the declaration specifier, with the new
            specifier incorporated.
        """
        spec = declspec or dict(qual=[], storage=[], type=[], function=[], alignment=[])

        if append:
            spec[kind].append(newspec)
        else:
            spec[kind].insert(0, newspec)

        return spec

    def _build_declarations(self, spec, decls, typedef_namespace=False):
        """ Builds a list of declarations all sharing the given specifiers.
            If typedef_namespace is true, each declared name is added
            to the "typedef namespace", which also includes objects,
            functions, and enum constants.
        """
        is_typedef = 'typedef' in spec['storage']
        declarations = []

        # Bit-fields are allowed to be unnamed.
        if decls[0].get('bitsize') is not None:
            pass

        # When redeclaring typedef names as identifiers in inner scopes, a
        # problem can occur where the identifier gets grouped into
        # spec['type'], leaving decl as None.  This can only occur for the
        # first declarator.
        elif decls[0]['decl'] is None:
            if len(spec['type']) < 2 or len(spec['type'][-1].names) != 1 or \
                    not self._is_type_in_scope(spec['type'][-1].names[0]):
                coord = '?'
                for t in spec['type']:
                    if hasattr(t, 'coord'):
                        coord = t.coord
                        break
                self._parse_error('Invalid declaration', coord)

            # Make this look as if it came from "direct_declarator:ID"
            decls[0]['decl'] = c_ast.TypeDecl(
                declname=spec['type'][-1].names[0],
                type=None,
                quals=None,
                align=spec['alignment'],
                coord=spec['type'][-1].coord)
            # Remove the "new" type's name from the end of spec['type']
            del spec['type'][-1]

        # A similar problem can occur where the declaration ends up looking
        # like an abstract declarator.  Give it a name if this is the case.
        elif not isinstance(decls[0]['decl'], (
                c_ast.Enum, c_ast.Struct, c_ast.Union, c_ast.IdentifierType)):
            decls_0_tail = decls[0]['decl']
            while not isinstance(decls_0_tail, c_ast.TypeDecl):
                decls_0_tail = decls_0_tail.type
            if decls_0_tail.declname is None:
                decls_0_tail.declname = spec['type'][-1].names[0]
                del spec['type'][-1]

        for decl in decls:
            assert decl['decl'] is not None
            if is_typedef:
                declaration = c_ast.Typedef(
                    name=None,
                    quals=spec['qual'],
                    storage=spec['storage'],
                    type=decl['decl'],
                    coord=decl['decl'].coord)
            else:
                declaration = c_ast.Decl(
                    name=None,
                    quals=spec['qual'],
                    align=spec['alignment'],
                    storage=spec['storage'],
                    funcspec=spec['function'],
                    type=decl['decl'],
                    init=decl.get('init'),
                    bitsize=decl.get('bitsize'),
                    coord=decl['decl'].coord)

            if isinstance(declaration.type, (
                    c_ast.Enum, c_ast.Struct, c_ast.Union,
                    c_ast.IdentifierType)):
                fixed_decl = declaration
            else:
                fixed_decl = self._fix_decl_name_type(declaration, spec['type'])

            # Add the type name defined by typedef to a
            # symbol table (for usage in the lexer)
            if typedef_namespace:
                if is_typedef:
                    self._add_typedef_name(fixed_decl.name, fixed_decl.coord)
                else:
                    self._add_identifier(fixed_decl.name, fixed_decl.coord)

            fixed_decl = fix_atomic_specifiers(fixed_decl)
            declarations.append(fixed_decl)

        return declarations

    def _build_function_definition(self, spec, decl, param_decls, body):
        """ Builds a function definition.
        """
        if 'typedef' in spec['storage']:
            self._parse_error("Invalid typedef", decl.coord)

        declaration = self._build_declarations(
            spec=spec,
            decls=[dict(decl=decl, init=None)],
            typedef_namespace=True)[0]

        return c_ast.FuncDef(
            decl=declaration,
            param_decls=param_decls,
            body=body,
            coord=decl.coord)

    def _select_struct_union_class(self, token):
        """ Given a token (either STRUCT or UNION), selects the
            appropriate AST class.
        """
        if token == 'struct':
            return c_ast.Struct
        else:
            return c_ast.Union

    ##
    ## Precedence and associativity of operators
    ##
    # If this changes, c_generator.CGenerator.precedence_map needs to change as
    # well
    precedence = (
        ('left', 'LOR'),
        ('left', 'LAND'),
        ('left', 'OR'),
        ('left', 'XOR'),
        ('left', 'AND'),
        ('left', 'EQ', 'NE'),
        ('left', 'GT', 'GE', 'LT', 'LE'),
        ('left', 'RSHIFT', 'LSHIFT'),
        ('left', 'PLUS', 'MINUS'),
        ('left', 'TIMES', 'DIVIDE', 'MOD')
    )

    ##
    ## Grammar productions
    ## Implementation of the BNF defined in K&R2 A.13
    ##

    # Wrapper around a translation unit, to allow for empty input.
    # Not strictly part of the C99 Grammar, but useful in practice.
    def p_translation_unit_or_empty(self, p):
        """ translation_unit_or_empty   : translation_unit
                                        | empty
        """
        if p[1] is None:
            p[0] = c_ast.FileAST([])
        else:
            p[0] = c_ast.FileAST(p[1])

    def p_translation_unit_1(self, p):
        """ translation_unit    : external_declaration
        """
        # Note: external_declaration is already a list
        p[0] = p[1]

    def p_translation_unit_2(self, p):
        """ translation_unit    : translation_unit external_declaration
        """
        p[1].extend(p[2])
        p[0] = p[1]

    # Declarations always come as lists (because they can be
    # several in one line), so we wrap the function definition
    # into a list as well, to make the return value of
    # external_declaration homogeneous.
    def p_external_declaration_1(self, p):
        """ external_declaration    : function_definition
        """
        p[0] = [p[1]]

    def p_external_declaration_2(self, p):
        """ external_declaration    : declaration
        """
        p[0] = p[1]

    def p_external_declaration_3(self, p):
        """ external_declaration    : pp_directive
                                    | pppragma_directive
        """
        p[0] = [p[1]]

    def p_external_declaration_4(self, p):
        """ external_declaration    : SEMI
        """
        p[0] = []

    def p_external_declaration_5(self, p):
        """ external_declaration    : static_assert
        """
        p[0] = p[1]

    def p_static_assert_declaration(self, p):
        """ static_assert           : _STATIC_ASSERT LPAREN constant_expression COMMA unified_string_literal RPAREN
                                    | _STATIC_ASSERT LPAREN constant_expression RPAREN
        """
        if len(p) == 5:
            p[0] = [c_ast.StaticAssert(p[3], None, self._token_coord(p, 1))]
        else:
            p[0] = [c_ast.StaticAssert(p[3], p[5], self._token_coord(p, 1))]

    def p_pp_directive(self, p):
        """ pp_directive  : PPHASH
        """
        self._parse_error('Directives not supported yet',
                          self._token_coord(p, 1))

    # This encompasses two types of C99-compatible pragmas:
    # - The #pragma directive:
    #       # pragma character_sequence
    # - The _Pragma unary operator:
    #       _Pragma ( " string_literal " )
    def p_pppragma_directive(self, p):
        """ pppragma_directive      : PPPRAGMA
                                    | PPPRAGMA PPPRAGMASTR
                                    | _PRAGMA LPAREN unified_string_literal RPAREN
        """
        if len(p) == 5:
            p[0] = c_ast.Pragma(p[3], self._token_coord(p, 2))
        elif len(p) == 3:
            p[0] = c_ast.Pragma(p[2], self._token_coord(p, 2))
        else:
            p[0] = c_ast.Pragma("", self._token_coord(p, 1))

    def p_pppragma_directive_list(self, p):
        """ pppragma_directive_list : pppragma_directive
                                    | pppragma_directive_list pppragma_directive
        """
        p[0] = [p[1]] if len(p) == 2 else p[1] + [p[2]]

    # In function definitions, the declarator can be followed by
    # a declaration list, for old "K&R style" function definitios.
    def p_function_definition_1(self, p):
        """ function_definition : id_declarator declaration_list_opt compound_statement
        """
        # no declaration specifiers - 'int' becomes the default type
        spec = dict(
            qual=[],
            alignment=[],
            storage=[],
            type=[c_ast.IdentifierType(['int'],
                                       coord=self._token_coord(p, 1))],
            function=[])

        p[0] = self._build_function_definition(
            spec=spec,
            decl=p[1],
            param_decls=p[2],
            body=p[3])

    def p_function_definition_2(self, p):
        """ function_definition : declaration_specifiers id_declarator declaration_list_opt compound_statement
        """
        spec = p[1]

        p[0] = self._build_function_definition(
            spec=spec,
            decl=p[2],
            param_decls=p[3],
            body=p[4])

    # Note, according to C18 A.2.2 6.7.10 static_assert-declaration _Static_assert
    # is a declaration, not a statement. We additionally recognise it as a statement
    # to fix parsing of _Static_assert inside the functions.
    #
    def p_statement(self, p):
        """ statement   : labeled_statement
                        | expression_statement
                        | compound_statement
                        | selection_statement
                        | iteration_statement
                        | jump_statement
                        | pppragma_directive
                        | static_assert
        """
        p[0] = p[1]

    # A pragma is generally considered a decorator rather than an actual
    # statement. Still, for the purposes of analyzing an abstract syntax tree of
    # C code, pragma's should not be ignored and were previously treated as a
    # statement. This presents a problem for constructs that take a statement
    # such as labeled_statements, selection_statements, and
    # iteration_statements, causing a misleading structure in the AST. For
    # example, consider the following C code.
    #
    #   for (int i = 0; i < 3; i++)
    #       #pragma omp critical
    #       sum += 1;
    #
    # This code will compile and execute "sum += 1;" as the body of the for
    # loop. Previous implementations of PyCParser would render the AST for this
    # block of code as follows:
    #
    #   For:
    #     DeclList:
    #       Decl: i, [], [], []
    #         TypeDecl: i, []
    #           IdentifierType: ['int']
    #         Constant: int, 0
    #     BinaryOp: <
    #       ID: i
    #       Constant: int, 3
    #     UnaryOp: p++
    #       ID: i
    #     Pragma: omp critical
    #   Assignment: +=
    #     ID: sum
    #     Constant: int, 1
    #
    # This AST misleadingly takes the Pragma as the body of the loop and the
    # assignment then becomes a sibling of the loop.
    #
    # To solve edge cases like these, the pragmacomp_or_statement rule groups
    # a pragma and its following statement (which would otherwise be orphaned)
    # using a compound block, effectively turning the above code into:
    #
    #   for (int i = 0; i < 3; i++) {
    #       #pragma omp critical
    #       sum += 1;
    #   }
    def p_pragmacomp_or_statement(self, p):
        """ pragmacomp_or_statement     : pppragma_directive_list statement
                                        | statement
        """
        if len(p) == 3:
            p[0] = c_ast.Compound(
                block_items=p[1]+[p[2]],
                coord=self._token_coord(p, 1))
        else:
            p[0] = p[1]

    # In C, declarations can come several in a line:
    #   int x, *px, romulo = 5;
    #
    # However, for the AST, we will split them to separate Decl
    # nodes.
    #
    # This rule splits its declarations and always returns a list
    # of Decl nodes, even if it's one element long.
    #
    def p_decl_body(self, p):
        """ decl_body : declaration_specifiers init_declarator_list_opt
                      | declaration_specifiers_no_type id_init_declarator_list_opt
        """
        spec = p[1]

        # p[2] (init_declarator_list_opt) is either a list or None
        #
        if p[2] is None:
            # By the standard, you must have at least one declarator unless
            # declaring a structure tag, a union tag, or the members of an
            # enumeration.
            #
            ty = spec['type']
            s_u_or_e = (c_ast.Struct, c_ast.Union, c_ast.Enum)
            if len(ty) == 1 and isinstance(ty[0], s_u_or_e):
                decls = [c_ast.Decl(
                    name=None,
                    quals=spec['qual'],
                    align=spec['alignment'],
                    storage=spec['storage'],
                    funcspec=spec['function'],
                    type=ty[0],
                    init=None,
                    bitsize=None,
                    coord=ty[0].coord)]

            # However, this case can also occur on redeclared identifiers in
            # an inner scope.  The trouble is that the redeclared type's name
            # gets grouped into declaration_specifiers; _build_declarations
            # compensates for this.
            #
            else:
                decls = self._build_declarations(
                    spec=spec,
                    decls=[dict(decl=None, init=None)],
                    typedef_namespace=True)

        else:
            decls = self._build_declarations(
                spec=spec,
                decls=p[2],
                typedef_namespace=True)

        p[0] = decls

    # The declaration has been split to a decl_body sub-rule and
    # SEMI, because having them in a single rule created a problem
    # for defining typedefs.
    #
    # If a typedef line was directly followed by a line using the
    # type defined with the typedef, the type would not be
    # recognized. This is because to reduce the declaration rule,
    # the parser's lookahead asked for the token after SEMI, which
    # was the type from the next line, and the lexer had no chance
    # to see the updated type symbol table.
    #
    # Splitting solves this problem, because after seeing SEMI,
    # the parser reduces decl_body, which actually adds the new
    # type into the table to be seen by the lexer before the next
    # line is reached.
    def p_declaration(self, p):
        """ declaration : decl_body SEMI
        """
        p[0] = p[1]

    # Since each declaration is a list of declarations, this
    # rule will combine all the declarations and return a single
    # list
    #
    def p_declaration_list(self, p):
        """ declaration_list    : declaration
                                | declaration_list declaration
        """
        p[0] = p[1] if len(p) == 2 else p[1] + p[2]

    # To know when declaration-specifiers end and declarators begin,
    # we require declaration-specifiers to have at least one
    # type-specifier, and disallow typedef-names after we've seen any
    # type-specifier. These are both required by the spec.
    #
    def p_declaration_specifiers_no_type_1(self, p):
        """ declaration_specifiers_no_type  : type_qualifier declaration_specifiers_no_type_opt
        """
        p[0] = self._add_declaration_specifier(p[2], p[1], 'qual')

    def p_declaration_specifiers_no_type_2(self, p):
        """ declaration_specifiers_no_type  : storage_class_specifier declaration_specifiers_no_type_opt
        """
        p[0] = self._add_declaration_specifier(p[2], p[1], 'storage')

    def p_declaration_specifiers_no_type_3(self, p):
        """ declaration_specifiers_no_type  : function_specifier declaration_specifiers_no_type_opt
        """
        p[0] = self._add_declaration_specifier(p[2], p[1], 'function')

    # Without this, `typedef _Atomic(T) U` will parse incorrectly because the
    # _Atomic qualifier will match, instead of the specifier.
    def p_declaration_specifiers_no_type_4(self, p):
        """ declaration_specifiers_no_type  : atomic_specifier declaration_specifiers_no_type_opt
        """
        p[0] = self._add_declaration_specifier(p[2], p[1], 'type')

    def p_declaration_specifiers_no_type_5(self, p):
        """ declaration_specifiers_no_type  : alignment_specifier declaration_specifiers_no_type_opt
        """
        p[0] = self._add_declaration_specifier(p[2], p[1], 'alignment')

    def p_declaration_specifiers_1(self, p):
        """ declaration_specifiers  : declaration_specifiers type_qualifier
        """
        p[0] = self._add_declaration_specifier(p[1], p[2], 'qual', append=True)

    def p_declaration_specifiers_2(self, p):
        """ declaration_specifiers  : declaration_specifiers storage_class_specifier
        """
        p[0] = self._add_declaration_specifier(p[1], p[2], 'storage', append=True)

    def p_declaration_specifiers_3(self, p):
        """ declaration_specifiers  : declaration_specifiers function_specifier
        """
        p[0] = self._add_declaration_specifier(p[1], p[2], 'function', append=True)

    def p_declaration_specifiers_4(self, p):
        """ declaration_specifiers  : declaration_specifiers type_specifier_no_typeid
        """
        p[0] = self._add_declaration_specifier(p[1], p[2], 'type', append=True)

    def p_declaration_specifiers_5(self, p):
        """ declaration_specifiers  : type_specifier
        """
        p[0] = self._add_declaration_specifier(None, p[1], 'type')

    def p_declaration_specifiers_6(self, p):
        """ declaration_specifiers  : declaration_specifiers_no_type type_specifier
        """
        p[0] = self._add_declaration_specifier(p[1], p[2], 'type', append=True)

    def p_declaration_specifiers_7(self, p):
        """ declaration_specifiers  : declaration_specifiers alignment_specifier
        """
        p[0] = self._add_declaration_specifier(p[1], p[2], 'alignment', append=True)

    def p_storage_class_specifier(self, p):
        """ storage_class_specifier : AUTO
                                    | REGISTER
                                    | STATIC
                                    | EXTERN
                                    | TYPEDEF
                                    | _THREAD_LOCAL
        """
        p[0] = p[1]

    def p_function_specifier(self, p):
        """ function_specifier  : INLINE
                                | _NORETURN
        """
        p[0] = p[1]

    def p_type_specifier_no_typeid(self, p):
        """ type_specifier_no_typeid  : VOID
                                      | _BOOL
                                      | CHAR
                                      | SHORT
                                      | INT
                                      | LONG
                                      | FLOAT
                                      | DOUBLE
                                      | _COMPLEX
                                      | SIGNED
                                      | UNSIGNED
                                      | __INT128
        """
        p[0] = c_ast.IdentifierType([p[1]], coord=self._token_coord(p, 1))

    def p_type_specifier(self, p):
        """ type_specifier  : typedef_name
                            | enum_specifier
                            | struct_or_union_specifier
                            | type_specifier_no_typeid
                            | atomic_specifier
        """
        p[0] = p[1]

    # See section 6.7.2.4 of the C11 standard.
    def p_atomic_specifier(self, p):
        """ atomic_specifier  : _ATOMIC LPAREN type_name RPAREN
        """
        typ = p[3]
        typ.quals.append('_Atomic')
        p[0] = typ

    def p_type_qualifier(self, p):
        """ type_qualifier  : CONST
                            | RESTRICT
                            | VOLATILE
                            | _ATOMIC
        """
        p[0] = p[1]

    def p_init_declarator_list(self, p):
        """ init_declarator_list    : init_declarator
                                    | init_declarator_list COMMA init_declarator
        """
        p[0] = p[1] + [p[3]] if len(p) == 4 else [p[1]]

    # Returns a {decl=<declarator> : init=<initializer>} dictionary
    # If there's no initializer, uses None
    #
    def p_init_declarator(self, p):
        """ init_declarator : declarator
                            | declarator EQUALS initializer
        """
        p[0] = dict(decl=p[1], init=(p[3] if len(p) > 2 else None))

    def p_id_init_declarator_list(self, p):
        """ id_init_declarator_list    : id_init_declarator
                                       | id_init_declarator_list COMMA init_declarator
        """
        p[0] = p[1] + [p[3]] if len(p) == 4 else [p[1]]

    def p_id_init_declarator(self, p):
        """ id_init_declarator : id_declarator
                               | id_declarator EQUALS initializer
        """
        p[0] = dict(decl=p[1], init=(p[3] if len(p) > 2 else None))

    # Require at least one type specifier in a specifier-qualifier-list
    #
    def p_specifier_qualifier_list_1(self, p):
        """ specifier_qualifier_list    : specifier_qualifier_list type_specifier_no_typeid
        """
        p[0] = self._add_declaration_specifier(p[1], p[2], 'type', append=True)

    def p_specifier_qualifier_list_2(self, p):
        """ specifier_qualifier_list    : specifier_qualifier_list type_qualifier
        """
        p[0] = self._add_declaration_specifier(p[1], p[2], 'qual', append=True)

    def p_specifier_qualifier_list_3(self, p):
        """ specifier_qualifier_list  : type_specifier
        """
        p[0] = self._add_declaration_specifier(None, p[1], 'type')

    def p_specifier_qualifier_list_4(self, p):
        """ specifier_qualifier_list  : type_qualifier_list type_specifier
        """
        p[0] = dict(qual=p[1], alignment=[], storage=[], type=[p[2]], function=[])

    def p_specifier_qualifier_list_5(self, p):
        """ specifier_qualifier_list  : alignment_specifier
        """
        p[0] = dict(qual=[], alignment=[p[1]], storage=[], type=[], function=[])

    def p_specifier_qualifier_list_6(self, p):
        """ specifier_qualifier_list  : specifier_qualifier_list alignment_specifier
        """
        p[0] = self._add_declaration_specifier(p[1], p[2], 'alignment')

    # TYPEID is allowed here (and in other struct/enum related tag names), because
    # struct/enum tags reside in their own namespace and can be named the same as types
    #
    def p_struct_or_union_specifier_1(self, p):
        """ struct_or_union_specifier   : struct_or_union ID
                                        | struct_or_union TYPEID
        """
        klass = self._select_struct_union_class(p[1])
        # None means no list of members
        p[0] = klass(
            name=p[2],
            decls=None,
            coord=self._token_coord(p, 2))

    def p_struct_or_union_specifier_2(self, p):
        """ struct_or_union_specifier : struct_or_union brace_open struct_declaration_list brace_close
                                      | struct_or_union brace_open brace_close
        """
        klass = self._select_struct_union_class(p[1])
        if len(p) == 4:
            # Empty sequence means an empty list of members
            p[0] = klass(
                name=None,
                decls=[],
                coord=self._token_coord(p, 2))
        else:
            p[0] = klass(
                name=None,
                decls=p[3],
                coord=self._token_coord(p, 2))


    def p_struct_or_union_specifier_3(self, p):
        """ struct_or_union_specifier   : struct_or_union ID brace_open struct_declaration_list brace_close
                                        | struct_or_union ID brace_open brace_close
                                        | struct_or_union TYPEID brace_open struct_declaration_list brace_close
                                        | struct_or_union TYPEID brace_open brace_close
        """
        klass = self._select_struct_union_class(p[1])
        if len(p) == 5:
            # Empty sequence means an empty list of members
            p[0] = klass(
                name=p[2],
                decls=[],
                coord=self._token_coord(p, 2))
        else:
            p[0] = klass(
                name=p[2],
                decls=p[4],
                coord=self._token_coord(p, 2))

    def p_struct_or_union(self, p):
        """ struct_or_union : STRUCT
                            | UNION
        """
        p[0] = p[1]

    # Combine all declarations into a single list
    #
    def p_struct_declaration_list(self, p):
        """ struct_declaration_list     : struct_declaration
                                        | struct_declaration_list struct_declaration
        """
        if len(p) == 2:
            p[0] = p[1] or []
        else:
            p[0] = p[1] + (p[2] or [])

    def p_struct_declaration_1(self, p):
        """ struct_declaration : specifier_qualifier_list struct_declarator_list_opt SEMI
        """
        spec = p[1]
        assert 'typedef' not in spec['storage']

        if p[2] is not None:
            decls = self._build_declarations(
                spec=spec,
                decls=p[2])

        elif len(spec['type']) == 1:
            # Anonymous struct/union, gcc extension, C1x feature.
            # Although the standard only allows structs/unions here, I see no
            # reason to disallow other types since some compilers have typedefs
            # here, and pycparser isn't about rejecting all invalid code.
            #
            node = spec['type'][0]
            if isinstance(node, c_ast.Node):
                decl_type = node
            else:
                decl_type = c_ast.IdentifierType(node)

            decls = self._build_declarations(
                spec=spec,
                decls=[dict(decl=decl_type)])

        else:
            # Structure/union members can have the same names as typedefs.
            # The trouble is that the member's name gets grouped into
            # specifier_qualifier_list; _build_declarations compensates.
            #
            decls = self._build_declarations(
                spec=spec,
                decls=[dict(decl=None, init=None)])

        p[0] = decls

    def p_struct_declaration_2(self, p):
        """ struct_declaration : SEMI
        """
        p[0] = None

    def p_struct_declaration_3(self, p):
        """ struct_declaration : pppragma_directive
        """
        p[0] = [p[1]]

    def p_struct_declarator_list(self, p):
        """ struct_declarator_list  : struct_declarator
                                    | struct_declarator_list COMMA struct_declarator
        """
        p[0] = p[1] + [p[3]] if len(p) == 4 else [p[1]]

    # struct_declarator passes up a dict with the keys: decl (for
    # the underlying declarator) and bitsize (for the bitsize)
    #
    def p_struct_declarator_1(self, p):
        """ struct_declarator : declarator
        """
        p[0] = {'decl': p[1], 'bitsize': None}

    def p_struct_declarator_2(self, p):
        """ struct_declarator   : declarator COLON constant_expression
                                | COLON constant_expression
        """
        if len(p) > 3:
            p[0] = {'decl': p[1], 'bitsize': p[3]}
        else:
            p[0] = {'decl': c_ast.TypeDecl(None, None, None, None), 'bitsize': p[2]}

    def p_enum_specifier_1(self, p):
        """ enum_specifier  : ENUM ID
                            | ENUM TYPEID
        """
        p[0] = c_ast.Enum(p[2], None, self._token_coord(p, 1))

    def p_enum_specifier_2(self, p):
        """ enum_specifier  : ENUM brace_open enumerator_list brace_close
        """
        p[0] = c_ast.Enum(None, p[3], self._token_coord(p, 1))

    def p_enum_specifier_3(self, p):
        """ enum_specifier  : ENUM ID brace_open enumerator_list brace_close
                            | ENUM TYPEID brace_open enumerator_list brace_close
        """
        p[0] = c_ast.Enum(p[2], p[4], self._token_coord(p, 1))

    def p_enumerator_list(self, p):
        """ enumerator_list : enumerator
                            | enumerator_list COMMA
                            | enumerator_list COMMA enumerator
        """
        if len(p) == 2:
            p[0] = c_ast.EnumeratorList([p[1]], p[1].coord)
        elif len(p) == 3:
            p[0] = p[1]
        else:
            p[1].enumerators.append(p[3])
            p[0] = p[1]

    def p_alignment_specifier(self, p):
        """ alignment_specifier  : _ALIGNAS LPAREN type_name RPAREN
                                 | _ALIGNAS LPAREN constant_expression RPAREN
        """
        p[0] = c_ast.Alignas(p[3], self._token_coord(p, 1))

    def p_enumerator(self, p):
        """ enumerator  : ID
                        | ID EQUALS constant_expression
        """
        if len(p) == 2:
            enumerator = c_ast.Enumerator(
                        p[1], None,
                        self._token_coord(p, 1))
        else:
            enumerator = c_ast.Enumerator(
                        p[1], p[3],
                        self._token_coord(p, 1))
        self._add_identifier(enumerator.name, enumerator.coord)

        p[0] = enumerator

    def p_declarator(self, p):
        """ declarator  : id_declarator
                        | typeid_declarator
        """
        p[0] = p[1]

    @parameterized(('id', 'ID'), ('typeid', 'TYPEID'), ('typeid_noparen', 'TYPEID'))
    def p_xxx_declarator_1(self, p):
        """ xxx_declarator  : direct_xxx_declarator
        """
        p[0] = p[1]

    @parameterized(('id', 'ID'), ('typeid', 'TYPEID'), ('typeid_noparen', 'TYPEID'))
    def p_xxx_declarator_2(self, p):
        """ xxx_declarator  : pointer direct_xxx_declarator
        """
        p[0] = self._type_modify_decl(p[2], p[1])

    @parameterized(('id', 'ID'), ('typeid', 'TYPEID'), ('typeid_noparen', 'TYPEID'))
    def p_direct_xxx_declarator_1(self, p):
        """ direct_xxx_declarator   : yyy
        """
        p[0] = c_ast.TypeDecl(
            declname=p[1],
            type=None,
            quals=None,
            align=None,
            coord=self._token_coord(p, 1))

    @parameterized(('id', 'ID'), ('typeid', 'TYPEID'))
    def p_direct_xxx_declarator_2(self, p):
        """ direct_xxx_declarator   : LPAREN xxx_declarator RPAREN
        """
        p[0] = p[2]

    @parameterized(('id', 'ID'), ('typeid', 'TYPEID'), ('typeid_noparen', 'TYPEID'))
    def p_direct_xxx_declarator_3(self, p):
        """ direct_xxx_declarator   : direct_xxx_declarator LBRACKET type_qualifier_list_opt assignment_expression_opt RBRACKET
        """
        quals = (p[3] if len(p) > 5 else []) or []
        # Accept dimension qualifiers
        # Per C99 6.7.5.3 p7
        arr = c_ast.ArrayDecl(
            type=None,
            dim=p[4] if len(p) > 5 else p[3],
            dim_quals=quals,
            coord=p[1].coord)

        p[0] = self._type_modify_decl(decl=p[1], modifier=arr)

    @parameterized(('id', 'ID'), ('typeid', 'TYPEID'), ('typeid_noparen', 'TYPEID'))
    def p_direct_xxx_declarator_4(self, p):
        """ direct_xxx_declarator   : direct_xxx_declarator LBRACKET STATIC type_qualifier_list_opt assignment_expression RBRACKET
                                    | direct_xxx_declarator LBRACKET type_qualifier_list STATIC assignment_expression RBRACKET
        """
        # Using slice notation for PLY objects doesn't work in Python 3 for the
        # version of PLY embedded with pycparser; see PLY Google Code issue 30.
        # Work around that here by listing the two elements separately.
        listed_quals = [item if isinstance(item, list) else [item]
            for item in [p[3],p[4]]]
        dim_quals = [qual for sublist in listed_quals for qual in sublist
            if qual is not None]
        arr = c_ast.ArrayDecl(
            type=None,
            dim=p[5],
            dim_quals=dim_quals,
            coord=p[1].coord)

        p[0] = self._type_modify_decl(decl=p[1], modifier=arr)

    # Special for VLAs
    #
    @parameterized(('id', 'ID'), ('typeid', 'TYPEID'), ('typeid_noparen', 'TYPEID'))
    def p_direct_xxx_declarator_5(self, p):
        """ direct_xxx_declarator   : direct_xxx_declarator LBRACKET type_qualifier_list_opt TIMES RBRACKET
        """
        arr = c_ast.ArrayDecl(
            type=None,
            dim=c_ast.ID(p[4], self._token_coord(p, 4)),
            dim_quals=p[3] if p[3] is not None else [],
            coord=p[1].coord)

        p[0] = self._type_modify_decl(decl=p[1], modifier=arr)

    @parameterized(('id', 'ID'), ('typeid', 'TYPEID'), ('typeid_noparen', 'TYPEID'))
    def p_direct_xxx_declarator_6(self, p):
        """ direct_xxx_declarator   : direct_xxx_declarator LPAREN parameter_type_list RPAREN
                                    | direct_xxx_declarator LPAREN identifier_list_opt RPAREN
        """
        func = c_ast.FuncDecl(
            args=p[3],
            type=None,
            coord=p[1].coord)

        # To see why _get_yacc_lookahead_token is needed, consider:
        #   typedef char TT;
        #   void foo(int TT) { TT = 10; }
        # Outside the function, TT is a typedef, but inside (starting and
        # ending with the braces) it's a parameter.  The trouble begins with
        # yacc's lookahead token.  We don't know if we're declaring or
        # defining a function until we see LBRACE, but if we wait for yacc to
        # trigger a rule on that token, then TT will have already been read
        # and incorrectly interpreted as TYPEID.  We need to add the
        # parameters to the scope the moment the lexer sees LBRACE.
        #
        if self._get_yacc_lookahead_token().type == "LBRACE":
            if func.args is not None:
                for param in func.args.params:
                    if isinstance(param, c_ast.EllipsisParam): break
                    self._add_identifier(param.name, param.coord)

        p[0] = self._type_modify_decl(decl=p[1], modifier=func)

    def p_pointer(self, p):
        """ pointer : TIMES type_qualifier_list_opt
                    | TIMES type_qualifier_list_opt pointer
        """
        coord = self._token_coord(p, 1)
        # Pointer decls nest from inside out. This is important when different
        # levels have different qualifiers. For example:
        #
        #  char * const * p;
        #
        # Means "pointer to const pointer to char"
        #
        # While:
        #
        #  char ** const p;
        #
        # Means "const pointer to pointer to char"
        #
        # So when we construct PtrDecl nestings, the leftmost pointer goes in
        # as the most nested type.
        nested_type = c_ast.PtrDecl(quals=p[2] or [], type=None, coord=coord)
        if len(p) > 3:
            tail_type = p[3]
            while tail_type.type is not None:
                tail_type = tail_type.type
            tail_type.type = nested_type
            p[0] = p[3]
        else:
            p[0] = nested_type

    def p_type_qualifier_list(self, p):
        """ type_qualifier_list : type_qualifier
                                | type_qualifier_list type_qualifier
        """
        p[0] = [p[1]] if len(p) == 2 else p[1] + [p[2]]

    def p_parameter_type_list(self, p):
        """ parameter_type_list : parameter_list
                                | parameter_list COMMA ELLIPSIS
        """
        if len(p) > 2:
            p[1].params.append(c_ast.EllipsisParam(self._token_coord(p, 3)))

        p[0] = p[1]

    def p_parameter_list(self, p):
        """ parameter_list  : parameter_declaration
                            | parameter_list COMMA parameter_declaration
        """
        if len(p) == 2: # single parameter
            p[0] = c_ast.ParamList([p[1]], p[1].coord)
        else:
            p[1].params.append(p[3])
            p[0] = p[1]

    # From ISO/IEC 9899:TC2, 6.7.5.3.11:
    # "If, in a parameter declaration, an identifier can be treated either
    #  as a typedef name or as a parameter name, it shall be taken as a
    #  typedef name."
    #
    # Inside a parameter declaration, once we've reduced declaration specifiers,
    # if we shift in an LPAREN and see a TYPEID, it could be either an abstract
    # declarator or a declarator nested inside parens. This rule tells us to
    # always treat it as an abstract declarator. Therefore, we only accept
    # `id_declarator`s and `typeid_noparen_declarator`s.
    def p_parameter_declaration_1(self, p):
        """ parameter_declaration   : declaration_specifiers id_declarator
                                    | declaration_specifiers typeid_noparen_declarator
        """
        spec = p[1]
        if not spec['type']:
            spec['type'] = [c_ast.IdentifierType(['int'],
                coord=self._token_coord(p, 1))]
        p[0] = self._build_declarations(
            spec=spec,
            decls=[dict(decl=p[2])])[0]

    def p_parameter_declaration_2(self, p):
        """ parameter_declaration   : declaration_specifiers abstract_declarator_opt
        """
        spec = p[1]
        if not spec['type']:
            spec['type'] = [c_ast.IdentifierType(['int'],
                coord=self._token_coord(p, 1))]

        # Parameters can have the same names as typedefs.  The trouble is that
        # the parameter's name gets grouped into declaration_specifiers, making
        # it look like an old-style declaration; compensate.
        #
        if len(spec['type']) > 1 and len(spec['type'][-1].names) == 1 and \
                self._is_type_in_scope(spec['type'][-1].names[0]):
            decl = self._build_declarations(
                    spec=spec,
                    decls=[dict(decl=p[2], init=None)])[0]

        # This truly is an old-style parameter declaration
        #
        else:
            decl = c_ast.Typename(
                name='',
                quals=spec['qual'],
                align=None,
                type=p[2] or c_ast.TypeDecl(None, None, None, None),
                coord=self._token_coord(p, 2))
            typename = spec['type']
            decl = self._fix_decl_name_type(decl, typename)

        p[0] = decl

    def p_identifier_list(self, p):
        """ identifier_list : identifier
                            | identifier_list COMMA identifier
        """
        if len(p) == 2: # single parameter
            p[0] = c_ast.ParamList([p[1]], p[1].coord)
        else:
            p[1].params.append(p[3])
            p[0] = p[1]

    def p_initializer_1(self, p):
        """ initializer : assignment_expression
        """
        p[0] = p[1]

    def p_initializer_2(self, p):
        """ initializer : brace_open initializer_list_opt brace_close
                        | brace_open initializer_list COMMA brace_close
        """
        if p[2] is None:
            p[0] = c_ast.InitList([], self._token_coord(p, 1))
        else:
            p[0] = p[2]

    def p_initializer_list(self, p):
        """ initializer_list    : designation_opt initializer
                                | initializer_list COMMA designation_opt initializer
        """
        if len(p) == 3: # single initializer
            init = p[2] if p[1] is None else c_ast.NamedInitializer(p[1], p[2])
            p[0] = c_ast.InitList([init], p[2].coord)
        else:
            init = p[4] if p[3] is None else c_ast.NamedInitializer(p[3], p[4])
            p[1].exprs.append(init)
            p[0] = p[1]

    def p_designation(self, p):
        """ designation : designator_list EQUALS
        """
        p[0] = p[1]

    # Designators are represented as a list of nodes, in the order in which
    # they're written in the code.
    #
    def p_designator_list(self, p):
        """ designator_list : designator
                            | designator_list designator
        """
        p[0] = [p[1]] if len(p) == 2 else p[1] + [p[2]]

    def p_designator(self, p):
        """ designator  : LBRACKET constant_expression RBRACKET
                        | PERIOD identifier
        """
        p[0] = p[2]

    def p_type_name(self, p):
        """ type_name   : specifier_qualifier_list abstract_declarator_opt
        """
        typename = c_ast.Typename(
            name='',
            quals=p[1]['qual'][:],
            align=None,
            type=p[2] or c_ast.TypeDecl(None, None, None, None),
            coord=self._token_coord(p, 2))

        p[0] = self._fix_decl_name_type(typename, p[1]['type'])

    def p_abstract_declarator_1(self, p):
        """ abstract_declarator     : pointer
        """
        dummytype = c_ast.TypeDecl(None, None, None, None)
        p[0] = self._type_modify_decl(
            decl=dummytype,
            modifier=p[1])

    def p_abstract_declarator_2(self, p):
        """ abstract_declarator     : pointer direct_abstract_declarator
        """
        p[0] = self._type_modify_decl(p[2], p[1])

    def p_abstract_declarator_3(self, p):
        """ abstract_declarator     : direct_abstract_declarator
        """
        p[0] = p[1]

    # Creating and using direct_abstract_declarator_opt here
    # instead of listing both direct_abstract_declarator and the
    # lack of it in the beginning of _1 and _2 caused two
    # shift/reduce errors.
    #
    def p_direct_abstract_declarator_1(self, p):
        """ direct_abstract_declarator  : LPAREN abstract_declarator RPAREN """
        p[0] = p[2]

    def p_direct_abstract_declarator_2(self, p):
        """ direct_abstract_declarator  : direct_abstract_declarator LBRACKET assignment_expression_opt RBRACKET
        """
        arr = c_ast.ArrayDecl(
            type=None,
            dim=p[3],
            dim_quals=[],
            coord=p[1].coord)

        p[0] = self._type_modify_decl(decl=p[1], modifier=arr)

    def p_direct_abstract_declarator_3(self, p):
        """ direct_abstract_declarator  : LBRACKET type_qualifier_list_opt assignment_expression_opt RBRACKET
        """
        quals = (p[2] if len(p) > 4 else []) or []
        p[0] = c_ast.ArrayDecl(
            type=c_ast.TypeDecl(None, None, None, None),
            dim=p[3] if len(p) > 4 else p[2],
            dim_quals=quals,
            coord=self._token_coord(p, 1))

    def p_direct_abstract_declarator_4(self, p):
        """ direct_abstract_declarator  : direct_abstract_declarator LBRACKET TIMES RBRACKET
        """
        arr = c_ast.ArrayDecl(
            type=None,
            dim=c_ast.ID(p[3], self._token_coord(p, 3)),
            dim_quals=[],
            coord=p[1].coord)

        p[0] = self._type_modify_decl(decl=p[1], modifier=arr)

    def p_direct_abstract_declarator_5(self, p):
        """ direct_abstract_declarator  : LBRACKET TIMES RBRACKET
        """
        p[0] = c_ast.ArrayDecl(
            type=c_ast.TypeDecl(None, None, None, None),
            dim=c_ast.ID(p[3], self._token_coord(p, 3)),
            dim_quals=[],
            coord=self._token_coord(p, 1))

    def p_direct_abstract_declarator_6(self, p):
        """ direct_abstract_declarator  : direct_abstract_declarator LPAREN parameter_type_list_opt RPAREN
        """
        func = c_ast.FuncDecl(
            args=p[3],
            type=None,
            coord=p[1].coord)

        p[0] = self._type_modify_decl(decl=p[1], modifier=func)

    def p_direct_abstract_declarator_7(self, p):
        """ direct_abstract_declarator  : LPAREN parameter_type_list_opt RPAREN
        """
        p[0] = c_ast.FuncDecl(
            args=p[2],
            type=c_ast.TypeDecl(None, None, None, None),
            coord=self._token_coord(p, 1))

    # declaration is a list, statement isn't. To make it consistent, block_item
    # will always be a list
    #
    def p_block_item(self, p):
        """ block_item  : declaration
                        | statement
        """
        p[0] = p[1] if isinstance(p[1], list) else [p[1]]

    # Since we made block_item a list, this just combines lists
    #
    def p_block_item_list(self, p):
        """ block_item_list : block_item
                            | block_item_list block_item
        """
        # Empty block items (plain ';') produce [None], so ignore them
        p[0] = p[1] if (len(p) == 2 or p[2] == [None]) else p[1] + p[2]

    def p_compound_statement_1(self, p):
        """ compound_statement : brace_open block_item_list_opt brace_close """
        p[0] = c_ast.Compound(
            block_items=p[2],
            coord=self._token_coord(p, 1))

    def p_labeled_statement_1(self, p):
        """ labeled_statement : ID COLON pragmacomp_or_statement """
        p[0] = c_ast.Label(p[1], p[3], self._token_coord(p, 1))

    def p_labeled_statement_2(self, p):
        """ labeled_statement : CASE constant_expression COLON pragmacomp_or_statement """
        p[0] = c_ast.Case(p[2], [p[4]], self._token_coord(p, 1))

    def p_labeled_statement_3(self, p):
        """ labeled_statement : DEFAULT COLON pragmacomp_or_statement """
        p[0] = c_ast.Default([p[3]], self._token_coord(p, 1))

    def p_selection_statement_1(self, p):
        """ selection_statement : IF LPAREN expression RPAREN pragmacomp_or_statement """
        p[0] = c_ast.If(p[3], p[5], None, self._token_coord(p, 1))

    def p_selection_statement_2(self, p):
        """ selection_statement : IF LPAREN expression RPAREN statement ELSE pragmacomp_or_statement """
        p[0] = c_ast.If(p[3], p[5], p[7], self._token_coord(p, 1))

    def p_selection_statement_3(self, p):
        """ selection_statement : SWITCH LPAREN expression RPAREN pragmacomp_or_statement """
        p[0] = fix_switch_cases(
                c_ast.Switch(p[3], p[5], self._token_coord(p, 1)))

    def p_iteration_statement_1(self, p):
        """ iteration_statement : WHILE LPAREN expression RPAREN pragmacomp_or_statement """
        p[0] = c_ast.While(p[3], p[5], self._token_coord(p, 1))

    def p_iteration_statement_2(self, p):
        """ iteration_statement : DO pragmacomp_or_statement WHILE LPAREN expression RPAREN SEMI """
        p[0] = c_ast.DoWhile(p[5], p[2], self._token_coord(p, 1))

    def p_iteration_statement_3(self, p):
        """ iteration_statement : FOR LPAREN expression_opt SEMI expression_opt SEMI expression_opt RPAREN pragmacomp_or_statement """
        p[0] = c_ast.For(p[3], p[5], p[7], p[9], self._token_coord(p, 1))

    def p_iteration_statement_4(self, p):
        """ iteration_statement : FOR LPAREN declaration expression_opt SEMI expression_opt RPAREN pragmacomp_or_statement """
        p[0] = c_ast.For(c_ast.DeclList(p[3], self._token_coord(p, 1)),
                         p[4], p[6], p[8], self._token_coord(p, 1))

    def p_jump_statement_1(self, p):
        """ jump_statement  : GOTO ID SEMI """
        p[0] = c_ast.Goto(p[2], self._token_coord(p, 1))

    def p_jump_statement_2(self, p):
        """ jump_statement  : BREAK SEMI """
        p[0] = c_ast.Break(self._token_coord(p, 1))

    def p_jump_statement_3(self, p):
        """ jump_statement  : CONTINUE SEMI """
        p[0] = c_ast.Continue(self._token_coord(p, 1))

    def p_jump_statement_4(self, p):
        """ jump_statement  : RETURN expression SEMI
                            | RETURN SEMI
        """
        p[0] = c_ast.Return(p[2] if len(p) == 4 else None, self._token_coord(p, 1))

    def p_expression_statement(self, p):
        """ expression_statement : expression_opt SEMI """
        if p[1] is None:
            p[0] = c_ast.EmptyStatement(self._token_coord(p, 2))
        else:
            p[0] = p[1]

    def p_expression(self, p):
        """ expression  : assignment_expression
                        | expression COMMA assignment_expression
        """
        if len(p) == 2:
            p[0] = p[1]
        else:
            if not isinstance(p[1], c_ast.ExprList):
                p[1] = c_ast.ExprList([p[1]], p[1].coord)

            p[1].exprs.append(p[3])
            p[0] = p[1]

    def p_parenthesized_compound_expression(self, p):
        """ assignment_expression : LPAREN compound_statement RPAREN """
        p[0] = p[2]

    def p_typedef_name(self, p):
        """ typedef_name : TYPEID """
        p[0] = c_ast.IdentifierType([p[1]], coord=self._token_coord(p, 1))

    def p_assignment_expression(self, p):
        """ assignment_expression   : conditional_expression
                                    | unary_expression assignment_operator assignment_expression
        """
        if len(p) == 2:
            p[0] = p[1]
        else:
            p[0] = c_ast.Assignment(p[2], p[1], p[3], p[1].coord)

    # K&R2 defines these as many separate rules, to encode
    # precedence and associativity. Why work hard ? I'll just use
    # the built in precedence/associativity specification feature
    # of PLY. (see precedence declaration above)
    #
    def p_assignment_operator(self, p):
        """ assignment_operator : EQUALS
                                | XOREQUAL
                                | TIMESEQUAL
                                | DIVEQUAL
                                | MODEQUAL
                                | PLUSEQUAL
                                | MINUSEQUAL
                                | LSHIFTEQUAL
                                | RSHIFTEQUAL
                                | ANDEQUAL
                                | OREQUAL
        """
        p[0] = p[1]

    def p_constant_expression(self, p):
        """ constant_expression : conditional_expression """
        p[0] = p[1]

    def p_conditional_expression(self, p):
        """ conditional_expression  : binary_expression
                                    | binary_expression CONDOP expression COLON conditional_expression
        """
        if len(p) == 2:
            p[0] = p[1]
        else:
            p[0] = c_ast.TernaryOp(p[1], p[3], p[5], p[1].coord)

    def p_binary_expression(self, p):
        """ binary_expression   : cast_expression
                                | binary_expression TIMES binary_expression
                                | binary_expression DIVIDE binary_expression
                                | binary_expression MOD binary_expression
                                | binary_expression PLUS binary_expression
                                | binary_expression MINUS binary_expression
                                | binary_expression RSHIFT binary_expression
                                | binary_expression LSHIFT binary_expression
                                | binary_expression LT binary_expression
                                | binary_expression LE binary_expression
                                | binary_expression GE binary_expression
                                | binary_expression GT binary_expression
                                | binary_expression EQ binary_expression
                                | binary_expression NE binary_expression
                                | binary_expression AND binary_expression
                                | binary_expression OR binary_expression
                                | binary_expression XOR binary_expression
                                | binary_expression LAND binary_expression
                                | binary_expression LOR binary_expression
        """
        if len(p) == 2:
            p[0] = p[1]
        else:
            p[0] = c_ast.BinaryOp(p[2], p[1], p[3], p[1].coord)

    def p_cast_expression_1(self, p):
        """ cast_expression : unary_expression """
        p[0] = p[1]

    def p_cast_expression_2(self, p):
        """ cast_expression : LPAREN type_name RPAREN cast_expression """
        p[0] = c_ast.Cast(p[2], p[4], self._token_coord(p, 1))

    def p_unary_expression_1(self, p):
        """ unary_expression    : postfix_expression """
        p[0] = p[1]

    def p_unary_expression_2(self, p):
        """ unary_expression    : PLUSPLUS unary_expression
                                | MINUSMINUS unary_expression
                                | unary_operator cast_expression
        """
        p[0] = c_ast.UnaryOp(p[1], p[2], p[2].coord)

    def p_unary_expression_3(self, p):
        """ unary_expression    : SIZEOF unary_expression
                                | SIZEOF LPAREN type_name RPAREN
                                | _ALIGNOF LPAREN type_name RPAREN
        """
        p[0] = c_ast.UnaryOp(
            p[1],
            p[2] if len(p) == 3 else p[3],
            self._token_coord(p, 1))

    def p_unary_operator(self, p):
        """ unary_operator  : AND
                            | TIMES
                            | PLUS
                            | MINUS
                            | NOT
                            | LNOT
        """
        p[0] = p[1]

    def p_postfix_expression_1(self, p):
        """ postfix_expression  : primary_expression """
        p[0] = p[1]

    def p_postfix_expression_2(self, p):
        """ postfix_expression  : postfix_expression LBRACKET expression RBRACKET """
        p[0] = c_ast.ArrayRef(p[1], p[3], p[1].coord)

    def p_postfix_expression_3(self, p):
        """ postfix_expression  : postfix_expression LPAREN argument_expression_list RPAREN
                                | postfix_expression LPAREN RPAREN
        """
        p[0] = c_ast.FuncCall(p[1], p[3] if len(p) == 5 else None, p[1].coord)

    def p_postfix_expression_4(self, p):
        """ postfix_expression  : postfix_expression PERIOD ID
                                | postfix_expression PERIOD TYPEID
                                | postfix_expression ARROW ID
                                | postfix_expression ARROW TYPEID
        """
        field = c_ast.ID(p[3], self._token_coord(p, 3))
        p[0] = c_ast.StructRef(p[1], p[2], field, p[1].coord)

    def p_postfix_expression_5(self, p):
        """ postfix_expression  : postfix_expression PLUSPLUS
                                | postfix_expression MINUSMINUS
        """
        p[0] = c_ast.UnaryOp('p' + p[2], p[1], p[1].coord)

    def p_postfix_expression_6(self, p):
        """ postfix_expression  : LPAREN type_name RPAREN brace_open initializer_list brace_close
                                | LPAREN type_name RPAREN brace_open initializer_list COMMA brace_close
        """
        p[0] = c_ast.CompoundLiteral(p[2], p[5])

    def p_primary_expression_1(self, p):
        """ primary_expression  : identifier """
        p[0] = p[1]

    def p_primary_expression_2(self, p):
        """ primary_expression  : constant """
        p[0] = p[1]

    def p_primary_expression_3(self, p):
        """ primary_expression  : unified_string_literal
                                | unified_wstring_literal
        """
        p[0] = p[1]

    def p_primary_expression_4(self, p):
        """ primary_expression  : LPAREN expression RPAREN """
        p[0] = p[2]

    def p_primary_expression_5(self, p):
        """ primary_expression  : OFFSETOF LPAREN type_name COMMA offsetof_member_designator RPAREN
        """
        coord = self._token_coord(p, 1)
        p[0] = c_ast.FuncCall(c_ast.ID(p[1], coord),
                              c_ast.ExprList([p[3], p[5]], coord),
                              coord)

    def p_offsetof_member_designator(self, p):
        """ offsetof_member_designator : identifier
                                         | offsetof_member_designator PERIOD identifier
                                         | offsetof_member_designator LBRACKET expression RBRACKET
        """
        if len(p) == 2:
            p[0] = p[1]
        elif len(p) == 4:
            p[0] = c_ast.StructRef(p[1], p[2], p[3], p[1].coord)
        elif len(p) == 5:
            p[0] = c_ast.ArrayRef(p[1], p[3], p[1].coord)
        else:
            raise NotImplementedError("Unexpected parsing state. len(p): %u" % len(p))

    def p_argument_expression_list(self, p):
        """ argument_expression_list    : assignment_expression
                                        | argument_expression_list COMMA assignment_expression
        """
        if len(p) == 2: # single expr
            p[0] = c_ast.ExprList([p[1]], p[1].coord)
        else:
            p[1].exprs.append(p[3])
            p[0] = p[1]

    def p_identifier(self, p):
        """ identifier  : ID """
        p[0] = c_ast.ID(p[1], self._token_coord(p, 1))

    def p_constant_1(self, p):
        """ constant    : INT_CONST_DEC
                        | INT_CONST_OCT
                        | INT_CONST_HEX
                        | INT_CONST_BIN
                        | INT_CONST_CHAR
        """
        uCount = 0
        lCount = 0
        for x in p[1][-3:]:
            if x in ('l', 'L'):
                lCount += 1
            elif x in ('u', 'U'):
                uCount += 1
        t = ''
        if uCount > 1:
             raise ValueError('Constant cannot have more than one u/U suffix.')
        elif lCount > 2:
             raise ValueError('Constant cannot have more than two l/L suffix.')
        prefix = 'unsigned ' * uCount + 'long ' * lCount
        p[0] = c_ast.Constant(
            prefix + 'int', p[1], self._token_coord(p, 1))

    def p_constant_2(self, p):
        """ constant    : FLOAT_CONST
                        | HEX_FLOAT_CONST
        """
        if 'x' in p[1].lower():
            t = 'float'
        else:
            if p[1][-1] in ('f', 'F'):
                t = 'float'
            elif p[1][-1] in ('l', 'L'):
                t = 'long double'
            else:
                t = 'double'

        p[0] = c_ast.Constant(
            t, p[1], self._token_coord(p, 1))

    def p_constant_3(self, p):
        """ constant    : CHAR_CONST
                        | WCHAR_CONST
                        | U8CHAR_CONST
                        | U16CHAR_CONST
                        | U32CHAR_CONST
        """
        p[0] = c_ast.Constant(
            'char', p[1], self._token_coord(p, 1))

    # The "unified" string and wstring literal rules are for supporting
    # concatenation of adjacent string literals.
    # I.e. "hello " "world" is seen by the C compiler as a single string literal
    # with the value "hello world"
    #
    def p_unified_string_literal(self, p):
        """ unified_string_literal  : STRING_LITERAL
                                    | unified_string_literal STRING_LITERAL
        """
        if len(p) == 2: # single literal
            p[0] = c_ast.Constant(
                'string', p[1], self._token_coord(p, 1))
        else:
            p[1].value = p[1].value[:-1] + p[2][1:]
            p[0] = p[1]

    def p_unified_wstring_literal(self, p):
        """ unified_wstring_literal : WSTRING_LITERAL
                                    | U8STRING_LITERAL
                                    | U16STRING_LITERAL
                                    | U32STRING_LITERAL
                                    | unified_wstring_literal WSTRING_LITERAL
                                    | unified_wstring_literal U8STRING_LITERAL
                                    | unified_wstring_literal U16STRING_LITERAL
                                    | unified_wstring_literal U32STRING_LITERAL
        """
        if len(p) == 2: # single literal
            p[0] = c_ast.Constant(
                'string', p[1], self._token_coord(p, 1))
        else:
            p[1].value = p[1].value.rstrip()[:-1] + p[2][2:]
            p[0] = p[1]

    def p_brace_open(self, p):
        """ brace_open  :   LBRACE
        """
        p[0] = p[1]
        p.set_lineno(0, p.lineno(1))

    def p_brace_close(self, p):
        """ brace_close :   RBRACE
        """
        p[0] = p[1]
        p.set_lineno(0, p.lineno(1))

    def p_empty(self, p):
        'empty : '
        p[0] = None

    def p_error(self, p):
        # If error recovery is added here in the future, make sure
        # _get_yacc_lookahead_token still works!
        #
        if p:
            self._parse_error(
                'before: %s' % p.value,
                self._coord(lineno=p.lineno,
                            column=self.clex.find_tok_column(p)))
        else:
            self._parse_error('At end of input', self.clex.filename)

# === NexusCore/openenv\Lib\site-packages\fontTools\varLib\instancer\__init__.py ===
""" Partially instantiate a variable font.

The module exports an `instantiateVariableFont` function and CLI that allow to
create full instances (i.e. static fonts) from variable fonts, as well as "partial"
variable fonts that only contain a subset of the original variation space.

For example, if you wish to pin the width axis to a given location while also
restricting the weight axis to 400..700 range, you can do:

.. code-block:: sh

    $ fonttools varLib.instancer ./NotoSans-VF.ttf wdth=85 wght=400:700

See `fonttools varLib.instancer --help` for more info on the CLI options.

The module's entry point is the `instantiateVariableFont` function, which takes
a TTFont object and a dict specifying either axis coodinates or (min, max) ranges,
and returns a new TTFont representing either a partial VF, or full instance if all
the VF axes were given an explicit coordinate.

E.g. here's how to pin the wght axis at a given location in a wght+wdth variable
font, keeping only the deltas associated with the wdth axis:
.. code-block:: pycon

    >>>
    >> from fontTools import ttLib
    >> from fontTools.varLib import instancer
    >> varfont = ttLib.TTFont("path/to/MyVariableFont.ttf")
    >> [a.axisTag for a in varfont["fvar"].axes]  # the varfont's current axes
    ['wght', 'wdth']
    >> partial = instancer.instantiateVariableFont(varfont, {"wght": 300})
    >> [a.axisTag for a in partial["fvar"].axes]  # axes left after pinning 'wght'
    ['wdth']

If the input location specifies all the axes, the resulting instance is no longer
'variable' (same as using fontools varLib.mutator):
.. code-block:: pycon

    >>>    
    >> instance = instancer.instantiateVariableFont(
    ...     varfont, {"wght": 700, "wdth": 67.5}
    ... )
    >> "fvar" not in instance
    True

If one just want to drop an axis at the default location, without knowing in
advance what the default value for that axis is, one can pass a `None` value:
.. code-block:: pycon

    >>>
    >> instance = instancer.instantiateVariableFont(varfont, {"wght": None})
    >> len(varfont["fvar"].axes)
    1

From the console script, this is equivalent to passing `wght=drop` as input.

This module is similar to fontTools.varLib.mutator, which it's intended to supersede.
Note that, unlike varLib.mutator, when an axis is not mentioned in the input
location, the varLib.instancer will keep the axis and the corresponding deltas,
whereas mutator implicitly drops the axis at its default coordinate.

The module supports all the following "levels" of instancing, which can of
course be combined:

L1
    dropping one or more axes while leaving the default tables unmodified;
    .. code-block:: pycon

        >>>
        >> font = instancer.instantiateVariableFont(varfont, {"wght": None})

L2
    dropping one or more axes while pinning them at non-default locations;
    .. code-block:: pycon
    
        >>>
        >> font = instancer.instantiateVariableFont(varfont, {"wght": 700})

L3
    restricting the range of variation of one or more axes, by setting either
    a new minimum or maximum, potentially -- though not necessarily -- dropping
    entire regions of variations that fall completely outside this new range.
    .. code-block:: pycon
    
        >>>
        >> font = instancer.instantiateVariableFont(varfont, {"wght": (100, 300)})

L4
    moving the default location of an axis, by specifying (min,defalt,max) values:
    .. code-block:: pycon
    
        >>>
        >> font = instancer.instantiateVariableFont(varfont, {"wght": (100, 300, 700)})

Currently only TrueType-flavored variable fonts (i.e. containing 'glyf' table)
are supported, but support for CFF2 variable fonts will be added soon.

The discussion and implementation of these features are tracked at
https://github.com/fonttools/fonttools/issues/1537
"""

from fontTools.misc.fixedTools import (
    floatToFixedToFloat,
    strToFixedToFloat,
    otRound,
)
from fontTools.varLib.models import normalizeValue, piecewiseLinearMap
from fontTools.ttLib import TTFont, newTable
from fontTools.ttLib.tables.TupleVariation import TupleVariation
from fontTools.ttLib.tables import _g_l_y_f
from fontTools import varLib

# we import the `subset` module because we use the `prune_lookups` method on the GSUB
# table class, and that method is only defined dynamically upon importing `subset`
from fontTools import subset  # noqa: F401
from fontTools.cffLib import privateDictOperators2
from fontTools.cffLib.specializer import (
    programToCommands,
    commandsToProgram,
    specializeCommands,
    generalizeCommands,
)
from fontTools.varLib import builder
from fontTools.varLib.mvar import MVAR_ENTRIES
from fontTools.varLib.merger import MutatorMerger
from fontTools.varLib.instancer import names
from .featureVars import instantiateFeatureVariations
from fontTools.misc.cliTools import makeOutputFileName
from fontTools.varLib.instancer import solver
from fontTools.ttLib.tables.otTables import VarComponentFlags
import collections
import dataclasses
from contextlib import contextmanager
from copy import deepcopy
from enum import IntEnum
import logging
import os
import re
from typing import Dict, Iterable, Mapping, Optional, Sequence, Tuple, Union
import warnings


log = logging.getLogger("fontTools.varLib.instancer")


def AxisRange(minimum, maximum):
    warnings.warn(
        "AxisRange is deprecated; use AxisTriple instead",
        DeprecationWarning,
        stacklevel=2,
    )
    return AxisTriple(minimum, None, maximum)


def NormalizedAxisRange(minimum, maximum):
    warnings.warn(
        "NormalizedAxisRange is deprecated; use AxisTriple instead",
        DeprecationWarning,
        stacklevel=2,
    )
    return NormalizedAxisTriple(minimum, None, maximum)


@dataclasses.dataclass(frozen=True, order=True, repr=False)
class AxisTriple(Sequence):
    """A triple of (min, default, max) axis values.

    Any of the values can be None, in which case the limitRangeAndPopulateDefaults()
    method can be used to fill in the missing values based on the fvar axis values.
    """

    minimum: Optional[float]
    default: Optional[float]
    maximum: Optional[float]

    def __post_init__(self):
        if self.default is None and self.minimum == self.maximum:
            object.__setattr__(self, "default", self.minimum)
        if (
            (
                self.minimum is not None
                and self.default is not None
                and self.minimum > self.default
            )
            or (
                self.default is not None
                and self.maximum is not None
                and self.default > self.maximum
            )
            or (
                self.minimum is not None
                and self.maximum is not None
                and self.minimum > self.maximum
            )
        ):
            raise ValueError(
                f"{type(self).__name__} minimum ({self.minimum}), default ({self.default}), maximum ({self.maximum}) must be in sorted order"
            )

    def __getitem__(self, i):
        fields = dataclasses.fields(self)
        return getattr(self, fields[i].name)

    def __len__(self):
        return len(dataclasses.fields(self))

    def _replace(self, **kwargs):
        return dataclasses.replace(self, **kwargs)

    def __repr__(self):
        return (
            f"({', '.join(format(v, 'g') if v is not None else 'None' for v in self)})"
        )

    @classmethod
    def expand(
        cls,
        v: Union[
            "AxisTriple",
            float,  # pin axis at single value, same as min==default==max
            Tuple[float, float],  # (min, max), restrict axis and keep default
            Tuple[float, float, float],  # (min, default, max)
        ],
    ) -> "AxisTriple":
        """Convert a single value or a tuple into an AxisTriple.

        If the input is a single value, it is interpreted as a pin at that value.
        If the input is a tuple, it is interpreted as (min, max) or (min, default, max).
        """
        if isinstance(v, cls):
            return v
        if isinstance(v, (int, float)):
            return cls(v, v, v)
        try:
            n = len(v)
        except TypeError as e:
            raise ValueError(
                f"expected float, 2- or 3-tuple of floats; got {type(v)}: {v!r}"
            ) from e
        default = None
        if n == 2:
            minimum, maximum = v
        elif n >= 3:
            return cls(*v)
        else:
            raise ValueError(f"expected sequence of 2 or 3; got {n}: {v!r}")
        return cls(minimum, default, maximum)

    def limitRangeAndPopulateDefaults(self, fvarTriple) -> "AxisTriple":
        """Return a new AxisTriple with the default value filled in.

        Set default to fvar axis default if the latter is within the min/max range,
        otherwise set default to the min or max value, whichever is closer to the
        fvar axis default.
        If the default value is already set, return self.
        """
        minimum = self.minimum
        if minimum is None:
            minimum = fvarTriple[0]
        default = self.default
        if default is None:
            default = fvarTriple[1]
        maximum = self.maximum
        if maximum is None:
            maximum = fvarTriple[2]

        minimum = max(minimum, fvarTriple[0])
        maximum = max(maximum, fvarTriple[0])
        minimum = min(minimum, fvarTriple[2])
        maximum = min(maximum, fvarTriple[2])
        default = max(minimum, min(maximum, default))

        return AxisTriple(minimum, default, maximum)


@dataclasses.dataclass(frozen=True, order=True, repr=False)
class NormalizedAxisTriple(AxisTriple):
    """A triple of (min, default, max) normalized axis values."""

    minimum: float
    default: float
    maximum: float

    def __post_init__(self):
        if self.default is None:
            object.__setattr__(self, "default", max(self.minimum, min(self.maximum, 0)))
        if not (-1.0 <= self.minimum <= self.default <= self.maximum <= 1.0):
            raise ValueError(
                "Normalized axis values not in -1..+1 range; got "
                f"minimum={self.minimum:g}, default={self.default:g}, maximum={self.maximum:g})"
            )


@dataclasses.dataclass(frozen=True, order=True, repr=False)
class NormalizedAxisTripleAndDistances(AxisTriple):
    """A triple of (min, default, max) normalized axis values,
    with distances between min and default, and default and max,
    in the *pre-normalized* space."""

    minimum: float
    default: float
    maximum: float
    distanceNegative: Optional[float] = 1
    distancePositive: Optional[float] = 1

    def __post_init__(self):
        if self.default is None:
            object.__setattr__(self, "default", max(self.minimum, min(self.maximum, 0)))
        if not (-1.0 <= self.minimum <= self.default <= self.maximum <= 1.0):
            raise ValueError(
                "Normalized axis values not in -1..+1 range; got "
                f"minimum={self.minimum:g}, default={self.default:g}, maximum={self.maximum:g})"
            )

    def reverse_negate(self):
        v = self
        return self.__class__(-v[2], -v[1], -v[0], v[4], v[3])

    def renormalizeValue(self, v, extrapolate=True):
        """Renormalizes a normalized value v to the range of this axis,
        considering the pre-normalized distances as well as the new
        axis limits."""

        lower, default, upper, distanceNegative, distancePositive = self
        assert lower <= default <= upper

        if not extrapolate:
            v = max(lower, min(upper, v))

        if v == default:
            return 0

        if default < 0:
            return -self.reverse_negate().renormalizeValue(-v, extrapolate=extrapolate)

        # default >= 0 and v != default

        if v > default:
            return (v - default) / (upper - default)

        # v < default

        if lower >= 0:
            return (v - default) / (default - lower)

        # lower < 0 and v < default

        totalDistance = distanceNegative * -lower + distancePositive * default

        if v >= 0:
            vDistance = (default - v) * distancePositive
        else:
            vDistance = -v * distanceNegative + distancePositive * default

        return -vDistance / totalDistance


class _BaseAxisLimits(Mapping[str, AxisTriple]):
    def __getitem__(self, key: str) -> AxisTriple:
        return self._data[key]

    def __iter__(self) -> Iterable[str]:
        return iter(self._data)

    def __len__(self) -> int:
        return len(self._data)

    def __repr__(self) -> str:
        return f"{type(self).__name__}({self._data!r})"

    def __str__(self) -> str:
        return str(self._data)

    def defaultLocation(self) -> Dict[str, float]:
        """Return a dict of default axis values."""
        return {k: v.default for k, v in self.items()}

    def pinnedLocation(self) -> Dict[str, float]:
        """Return a location dict with only the pinned axes."""
        return {k: v.default for k, v in self.items() if v.minimum == v.maximum}


class AxisLimits(_BaseAxisLimits):
    """Maps axis tags (str) to AxisTriple values."""

    def __init__(self, *args, **kwargs):
        self._data = data = {}
        for k, v in dict(*args, **kwargs).items():
            if v is None:
                # will be filled in by limitAxesAndPopulateDefaults
                data[k] = v
            else:
                try:
                    triple = AxisTriple.expand(v)
                except ValueError as e:
                    raise ValueError(f"Invalid axis limits for {k!r}: {v!r}") from e
                data[k] = triple

    def limitAxesAndPopulateDefaults(self, varfont) -> "AxisLimits":
        """Return a new AxisLimits with defaults filled in from fvar table.

        If all axis limits already have defaults, return self.
        """
        fvar = varfont["fvar"]
        fvarTriples = {
            a.axisTag: (a.minValue, a.defaultValue, a.maxValue) for a in fvar.axes
        }
        newLimits = {}
        for axisTag, triple in self.items():
            fvarTriple = fvarTriples[axisTag]
            default = fvarTriple[1]
            if triple is None:
                newLimits[axisTag] = AxisTriple(default, default, default)
            else:
                newLimits[axisTag] = triple.limitRangeAndPopulateDefaults(fvarTriple)
        return type(self)(newLimits)

    def normalize(self, varfont, usingAvar=True) -> "NormalizedAxisLimits":
        """Return a new NormalizedAxisLimits with normalized -1..0..+1 values.

        If usingAvar is True, the avar table is used to warp the default normalization.
        """
        fvar = varfont["fvar"]
        badLimits = set(self.keys()).difference(a.axisTag for a in fvar.axes)
        if badLimits:
            raise ValueError("Cannot limit: {} not present in fvar".format(badLimits))

        axes = {
            a.axisTag: (a.minValue, a.defaultValue, a.maxValue)
            for a in fvar.axes
            if a.axisTag in self
        }

        avarSegments = {}
        if usingAvar and "avar" in varfont:
            avarSegments = varfont["avar"].segments

        normalizedLimits = {}

        for axis_tag, triple in axes.items():
            distanceNegative = triple[1] - triple[0]
            distancePositive = triple[2] - triple[1]

            if self[axis_tag] is None:
                normalizedLimits[axis_tag] = NormalizedAxisTripleAndDistances(
                    0, 0, 0, distanceNegative, distancePositive
                )
                continue

            minV, defaultV, maxV = self[axis_tag]

            if defaultV is None:
                defaultV = triple[1]

            avarMapping = avarSegments.get(axis_tag, None)
            normalizedLimits[axis_tag] = NormalizedAxisTripleAndDistances(
                *(normalize(v, triple, avarMapping) for v in (minV, defaultV, maxV)),
                distanceNegative,
                distancePositive,
            )

        return NormalizedAxisLimits(normalizedLimits)


class NormalizedAxisLimits(_BaseAxisLimits):
    """Maps axis tags (str) to NormalizedAxisTriple values."""

    def __init__(self, *args, **kwargs):
        self._data = data = {}
        for k, v in dict(*args, **kwargs).items():
            try:
                triple = NormalizedAxisTripleAndDistances.expand(v)
            except ValueError as e:
                raise ValueError(f"Invalid axis limits for {k!r}: {v!r}") from e
            data[k] = triple


class OverlapMode(IntEnum):
    KEEP_AND_DONT_SET_FLAGS = 0
    KEEP_AND_SET_FLAGS = 1
    REMOVE = 2
    REMOVE_AND_IGNORE_ERRORS = 3


def instantiateVARC(varfont, axisLimits):
    log.info("Instantiating VARC tables")

    # TODO(behdad) My confidence in this function is rather low;
    # It needs more testing. Specially with partial-instancing,
    # I don't think it currently works.

    varc = varfont["VARC"].table
    fvarAxes = varfont["fvar"].axes if "fvar" in varfont else []

    location = axisLimits.pinnedLocation()
    axisMap = [i for i, axis in enumerate(fvarAxes) if axis.axisTag not in location]
    reverseAxisMap = {i: j for j, i in enumerate(axisMap)}

    if varc.AxisIndicesList:
        axisIndicesList = varc.AxisIndicesList.Item
        for i, axisIndices in enumerate(axisIndicesList):
            if any(fvarAxes[j].axisTag in axisLimits for j in axisIndices):
                raise NotImplementedError(
                    "Instancing across VarComponent axes is not supported."
                )
            axisIndicesList[i] = [reverseAxisMap[j] for j in axisIndices]

    store = varc.MultiVarStore
    if store:
        for region in store.SparseVarRegionList.Region:
            newRegionAxis = []
            for regionRecord in region.SparseVarRegionAxis:
                tag = fvarAxes[regionRecord.AxisIndex].axisTag
                if tag in axisLimits:
                    raise NotImplementedError(
                        "Instancing across VarComponent axes is not supported."
                    )
                regionRecord.AxisIndex = reverseAxisMap[regionRecord.AxisIndex]


def instantiateTupleVariationStore(
    variations, axisLimits, origCoords=None, endPts=None
):
    """Instantiate TupleVariation list at the given location, or limit axes' min/max.

    The 'variations' list of TupleVariation objects is modified in-place.
    The 'axisLimits' (dict) maps axis tags (str) to NormalizedAxisTriple namedtuples
    specifying (minimum, default, maximum) in the -1,0,+1 normalized space. Pinned axes
    have minimum == default == maximum.

    A 'full' instance (i.e. static font) is produced when all the axes are pinned to
    single coordinates; a 'partial' instance (i.e. a less variable font) is produced
    when some of the axes are omitted, or restricted with a new range.

    Tuples that do not participate are kept as they are. Those that have 0 influence
    at the given location are removed from the variation store.
    Those that are fully instantiated (i.e. all their axes are being pinned) are also
    removed from the variation store, their scaled deltas accummulated and returned, so
    that they can be added by the caller to the default instance's coordinates.
    Tuples that are only partially instantiated (i.e. not all the axes that they
    participate in are being pinned) are kept in the store, and their deltas multiplied
    by the scalar support of the axes to be pinned at the desired location.

    Args:
        variations: List[TupleVariation] from either 'gvar' or 'cvar'.
        axisLimits: NormalizedAxisLimits: map from axis tags to (min, default, max)
            normalized coordinates for the full or partial instance.
        origCoords: GlyphCoordinates: default instance's coordinates for computing 'gvar'
            inferred points (cf. table__g_l_y_f._getCoordinatesAndControls).
        endPts: List[int]: indices of contour end points, for inferring 'gvar' deltas.

    Returns:
        List[float]: the overall delta adjustment after applicable deltas were summed.
    """

    newVariations = changeTupleVariationsAxisLimits(variations, axisLimits)

    mergedVariations = collections.OrderedDict()
    for var in newVariations:
        # compute inferred deltas only for gvar ('origCoords' is None for cvar)
        if origCoords is not None:
            var.calcInferredDeltas(origCoords, endPts)

        # merge TupleVariations with overlapping "tents"
        axes = frozenset(var.axes.items())
        if axes in mergedVariations:
            mergedVariations[axes] += var
        else:
            mergedVariations[axes] = var

    # drop TupleVariation if all axes have been pinned (var.axes.items() is empty);
    # its deltas will be added to the default instance's coordinates
    defaultVar = mergedVariations.pop(frozenset(), None)

    for var in mergedVariations.values():
        var.roundDeltas()
    variations[:] = list(mergedVariations.values())

    return defaultVar.coordinates if defaultVar is not None else []


def changeTupleVariationsAxisLimits(variations, axisLimits):
    for axisTag, axisLimit in sorted(axisLimits.items()):
        newVariations = []
        for var in variations:
            newVariations.extend(changeTupleVariationAxisLimit(var, axisTag, axisLimit))
        variations = newVariations
    return variations


def changeTupleVariationAxisLimit(var, axisTag, axisLimit):
    assert isinstance(axisLimit, NormalizedAxisTripleAndDistances)

    # Skip when current axis is missing or peaks at 0 (i.e. doesn't participate)
    lower, peak, upper = var.axes.get(axisTag, (-1, 0, 1))
    if peak == 0:
        # explicitly defined, no-op axes can be omitted
        # https://github.com/fonttools/fonttools/issues/3453
        if axisTag in var.axes:
            del var.axes[axisTag]
        return [var]
    # Drop if the var 'tent' isn't well-formed
    if not (lower <= peak <= upper) or (lower < 0 and upper > 0):
        return []

    if axisTag not in var.axes:
        return [var]

    tent = var.axes[axisTag]

    solutions = solver.rebaseTent(tent, axisLimit)

    out = []
    for scalar, tent in solutions:
        newVar = (
            TupleVariation(var.axes, var.coordinates) if len(solutions) > 1 else var
        )
        if tent is None:
            newVar.axes.pop(axisTag)
        else:
            assert tent[1] != 0, tent
            newVar.axes[axisTag] = tent
        newVar *= scalar
        out.append(newVar)

    return out


def instantiateCFF2(
    varfont,
    axisLimits,
    *,
    round=round,
    specialize=True,
    generalize=False,
    downgrade=False,
):
    # The algorithm here is rather simple:
    #
    # Take all blend operations and store their deltas in the (otherwise empty)
    # CFF2 VarStore. Then, instantiate the VarStore with the given axis limits,
    # and read back the new deltas. This is done for both the CharStrings and
    # the Private dicts.
    #
    # Then prune unused things and possibly drop the VarStore if it's empty.
    # In which case, downgrade to CFF table if requested.

    log.info("Instantiating CFF2 table")

    fvarAxes = varfont["fvar"].axes

    cff = varfont["CFF2"].cff
    topDict = cff.topDictIndex[0]
    varStore = topDict.VarStore.otVarStore
    if not varStore:
        if downgrade:
            from fontTools.cffLib.CFF2ToCFF import convertCFF2ToCFF

            convertCFF2ToCFF(varfont)
        return

    cff.desubroutinize()

    def getNumRegions(vsindex):
        return varStore.VarData[vsindex if vsindex is not None else 0].VarRegionCount

    charStrings = topDict.CharStrings.values()

    # Gather all unique private dicts
    uniquePrivateDicts = set()
    privateDicts = []
    for fd in topDict.FDArray:
        if fd.Private not in uniquePrivateDicts:
            uniquePrivateDicts.add(fd.Private)
            privateDicts.append(fd.Private)

    allCommands = []
    allCommandPrivates = []
    for cs in charStrings:
        assert cs.private.vstore.otVarStore is varStore  # Or in many places!!
        commands = programToCommands(cs.program, getNumRegions=getNumRegions)
        if generalize:
            commands = generalizeCommands(commands)
        if specialize:
            commands = specializeCommands(commands, generalizeFirst=not generalize)
        allCommands.append(commands)
        allCommandPrivates.append(cs.private)

    def storeBlendsToVarStore(arg):
        if not isinstance(arg, list):
            return

        if any(isinstance(subarg, list) for subarg in arg[:-1]):
            raise NotImplementedError("Nested blend lists not supported (yet)")

        count = arg[-1]
        assert (len(arg) - 1) % count == 0
        nRegions = (len(arg) - 1) // count - 1
        assert nRegions == getNumRegions(vsindex)
        for i in range(count, len(arg) - 1, nRegions):
            deltas = arg[i : i + nRegions]
            assert len(deltas) == nRegions
            varData = varStore.VarData[vsindex]
            varData.Item.append(deltas)
            varData.ItemCount += 1

    def fetchBlendsFromVarStore(arg):
        if not isinstance(arg, list):
            return [arg]

        if any(isinstance(subarg, list) for subarg in arg[:-1]):
            raise NotImplementedError("Nested blend lists not supported (yet)")

        count = arg[-1]
        assert (len(arg) - 1) % count == 0
        numRegions = getNumRegions(vsindex)
        newDefaults = []
        newDeltas = []
        for i in range(count):
            defaultValue = arg[i]

            major = vsindex
            minor = varDataCursor[major]
            varDataCursor[major] += 1

            varIdx = (major << 16) + minor

            defaultValue += round(defaultDeltas[varIdx])
            newDefaults.append(defaultValue)

            varData = varStore.VarData[major]
            deltas = varData.Item[minor]
            assert len(deltas) == numRegions
            newDeltas.extend(deltas)

        if not numRegions:
            return newDefaults  # No deltas, just return the defaults

        return [newDefaults + newDeltas + [count]]

    # Check VarData's are empty
    for varData in varStore.VarData:
        assert varData.Item == []
        assert varData.ItemCount == 0

    # Add charstring blend lists to VarStore so we can instantiate them
    for commands, private in zip(allCommands, allCommandPrivates):
        vsindex = getattr(private, "vsindex", 0)
        for command in commands:
            if command[0] == "vsindex":
                vsindex = command[1][0]
                continue
            for arg in command[1]:
                storeBlendsToVarStore(arg)

    # Add private blend lists to VarStore so we can instantiate values
    for opcode, name, arg_type, default, converter in privateDictOperators2:
        if arg_type not in ("number", "delta", "array"):
            continue

        vsindex = 0
        for private in privateDicts:
            if not hasattr(private, name):
                continue
            values = getattr(private, name)

            # This is safe here since "vsindex" is the first in the privateDictOperators2
            if name == "vsindex":
                vsindex = values[0]
                continue

            if arg_type == "number":
                values = [values]

            for value in values:
                if not isinstance(value, list):
                    continue

                assert len(value) % (getNumRegions(vsindex) + 1) == 0
                count = len(value) // (getNumRegions(vsindex) + 1)
                storeBlendsToVarStore(value + [count])

    # Instantiate VarStore
    defaultDeltas = instantiateItemVariationStore(varStore, fvarAxes, axisLimits)

    # Read back new charstring blends from the instantiated VarStore
    varDataCursor = [0] * len(varStore.VarData)
    for commands, private in zip(allCommands, allCommandPrivates):
        vsindex = getattr(private, "vsindex", 0)
        for command in commands:
            if command[0] == "vsindex":
                vsindex = command[1][0]
                continue
            newArgs = []
            for arg in command[1]:
                newArgs.extend(fetchBlendsFromVarStore(arg))
            command[1][:] = newArgs

    # Read back new private blends from the instantiated VarStore
    for opcode, name, arg_type, default, converter in privateDictOperators2:
        if arg_type not in ("number", "delta", "array"):
            continue

        vsindex = 0
        for private in privateDicts:
            if not hasattr(private, name):
                continue

            # This is safe here since "vsindex" is the first in the privateDictOperators2
            if name == "vsindex":
                vsindex = values[0]
                continue

            values = getattr(private, name)
            if arg_type == "number":
                values = [values]

            newValues = []
            for value in values:
                if not isinstance(value, list):
                    newValues.append(value)
                    continue

                value.append(1)
                value = fetchBlendsFromVarStore(value)
                newValues.extend(v[:-1] if isinstance(v, list) else v for v in value)

            if arg_type == "number":
                newValues = newValues[0]

            setattr(private, name, newValues)

    # Empty out the VarStore
    for i, varData in enumerate(varStore.VarData):
        assert varDataCursor[i] == varData.ItemCount, (
            varDataCursor[i],
            varData.ItemCount,
        )
        varData.Item = []
        varData.ItemCount = 0

    # Remove vsindex commands that are no longer needed, collect those that are.
    usedVsindex = set()
    for commands in allCommands:
        if any(isinstance(arg, list) for command in commands for arg in command[1]):
            vsindex = 0
            for command in commands:
                if command[0] == "vsindex":
                    vsindex = command[1][0]
                    continue
                if any(isinstance(arg, list) for arg in command[1]):
                    usedVsindex.add(vsindex)
        else:
            commands[:] = [command for command in commands if command[0] != "vsindex"]

    # Remove unused VarData and update vsindex values
    vsindexMapping = {v: i for i, v in enumerate(sorted(usedVsindex))}
    varStore.VarData = [
        varData for i, varData in enumerate(varStore.VarData) if i in usedVsindex
    ]
    varStore.VarDataCount = len(varStore.VarData)
    for commands in allCommands:
        for command in commands:
            if command[0] == "vsindex":
                command[1][0] = vsindexMapping[command[1][0]]

    # Remove initial vsindex commands that are implied
    for commands in allCommands:
        if commands and commands[0] == ("vsindex", [0]):
            commands.pop(0)

    # Ship the charstrings!
    for cs, commands in zip(charStrings, allCommands):
        cs.program = commandsToProgram(commands)

    # Remove empty VarStore
    if not varStore.VarData:
        if "VarStore" in topDict.rawDict:
            del topDict.rawDict["VarStore"]
        del topDict.VarStore
        del topDict.CharStrings.varStore
        for private in privateDicts:
            del private.vstore

        if downgrade:
            from fontTools.cffLib.CFF2ToCFF import convertCFF2ToCFF

            convertCFF2ToCFF(varfont)


def _instantiateGvarGlyph(
    glyphname, glyf, gvar, hMetrics, vMetrics, axisLimits, optimize=True
):
    coordinates, ctrl = glyf._getCoordinatesAndControls(glyphname, hMetrics, vMetrics)
    endPts = ctrl.endPts

    # Not every glyph may have variations
    tupleVarStore = gvar.variations.get(glyphname)

    if tupleVarStore:
        defaultDeltas = instantiateTupleVariationStore(
            tupleVarStore, axisLimits, coordinates, endPts
        )

        if defaultDeltas:
            coordinates += _g_l_y_f.GlyphCoordinates(defaultDeltas)

    # _setCoordinates also sets the hmtx/vmtx advance widths and sidebearings from
    # the four phantom points and glyph bounding boxes.
    # We call it unconditionally even if a glyph has no variations or no deltas are
    # applied at this location, in case the glyph's xMin and in turn its sidebearing
    # have changed. E.g. a composite glyph has no deltas for the component's (x, y)
    # offset nor for the 4 phantom points (e.g. it's monospaced). Thus its entry in
    # gvar table is empty; however, the composite's base glyph may have deltas
    # applied, hence the composite's bbox and left/top sidebearings may need updating
    # in the instanced font.
    glyf._setCoordinates(glyphname, coordinates, hMetrics, vMetrics)

    if not tupleVarStore:
        if glyphname in gvar.variations:
            del gvar.variations[glyphname]
        return

    if optimize:
        # IUP semantics depend on point equality, and so round prior to
        # optimization to ensure that comparisons that happen now will be the
        # same as those that happen at render time. This is especially needed
        # when floating point deltas have been applied to the default position.
        #     See https://github.com/fonttools/fonttools/issues/3634
        # Rounding must happen only after calculating glyf metrics above, to
        # preserve backwards compatibility.
        #     See 0010a3cd9aa25f84a3a6250dafb119743d32aa40
        coordinates.toInt()

        isComposite = glyf[glyphname].isComposite()

        for var in tupleVarStore:
            var.optimize(coordinates, endPts, isComposite=isComposite)


def instantiateGvarGlyph(varfont, glyphname, axisLimits, optimize=True):
    """Remove?
    https://github.com/fonttools/fonttools/pull/2266"""
    gvar = varfont["gvar"]
    glyf = varfont["glyf"]
    hMetrics = varfont["hmtx"].metrics
    vMetrics = getattr(varfont.get("vmtx"), "metrics", None)
    _instantiateGvarGlyph(
        glyphname, glyf, gvar, hMetrics, vMetrics, axisLimits, optimize=optimize
    )


def instantiateGvar(varfont, axisLimits, optimize=True):
    log.info("Instantiating glyf/gvar tables")

    gvar = varfont["gvar"]
    glyf = varfont["glyf"]
    hMetrics = varfont["hmtx"].metrics
    vMetrics = getattr(varfont.get("vmtx"), "metrics", None)
    # Get list of glyph names sorted by component depth.
    # If a composite glyph is processed before its base glyph, the bounds may
    # be calculated incorrectly because deltas haven't been applied to the
    # base glyph yet.
    glyphnames = sorted(
        glyf.glyphOrder,
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
        _instantiateGvarGlyph(
            glyphname, glyf, gvar, hMetrics, vMetrics, axisLimits, optimize=optimize
        )

    if not gvar.variations:
        del varfont["gvar"]


def setCvarDeltas(cvt, deltas):
    for i, delta in enumerate(deltas):
        if delta:
            cvt[i] += otRound(delta)


def instantiateCvar(varfont, axisLimits):
    log.info("Instantiating cvt/cvar tables")

    cvar = varfont["cvar"]

    defaultDeltas = instantiateTupleVariationStore(cvar.variations, axisLimits)

    if defaultDeltas:
        setCvarDeltas(varfont["cvt "], defaultDeltas)

    if not cvar.variations:
        del varfont["cvar"]


def setMvarDeltas(varfont, deltas):
    mvar = varfont["MVAR"].table
    records = mvar.ValueRecord
    for rec in records:
        mvarTag = rec.ValueTag
        if mvarTag not in MVAR_ENTRIES:
            continue
        tableTag, itemName = MVAR_ENTRIES[mvarTag]
        delta = deltas[rec.VarIdx]
        if delta != 0:
            setattr(
                varfont[tableTag],
                itemName,
                getattr(varfont[tableTag], itemName) + otRound(delta),
            )


@contextmanager
def verticalMetricsKeptInSync(varfont):
    """Ensure hhea vertical metrics stay in sync with OS/2 ones after instancing.

    When applying MVAR deltas to the OS/2 table, if the ascender, descender and
    line gap change but they were the same as the respective hhea metrics in the
    original font, this context manager ensures that hhea metrcs also get updated
    accordingly.
    The MVAR spec only has tags for the OS/2 metrics, but it is common in fonts
    to have the hhea metrics be equal to those for compat reasons.

    https://learn.microsoft.com/en-us/typography/opentype/spec/mvar
    https://googlefonts.github.io/gf-guide/metrics.html#7-hhea-and-typo-metrics-should-be-equal
    https://github.com/fonttools/fonttools/issues/3297
    """
    current_os2_vmetrics = [
        getattr(varfont["OS/2"], attr)
        for attr in ("sTypoAscender", "sTypoDescender", "sTypoLineGap")
    ]
    metrics_are_synced = current_os2_vmetrics == [
        getattr(varfont["hhea"], attr) for attr in ("ascender", "descender", "lineGap")
    ]

    yield metrics_are_synced

    if metrics_are_synced:
        new_os2_vmetrics = [
            getattr(varfont["OS/2"], attr)
            for attr in ("sTypoAscender", "sTypoDescender", "sTypoLineGap")
        ]
        if current_os2_vmetrics != new_os2_vmetrics:
            for attr, value in zip(
                ("ascender", "descender", "lineGap"), new_os2_vmetrics
            ):
                setattr(varfont["hhea"], attr, value)


def instantiateMVAR(varfont, axisLimits):
    log.info("Instantiating MVAR table")

    mvar = varfont["MVAR"].table
    fvarAxes = varfont["fvar"].axes
    varStore = mvar.VarStore
    defaultDeltas = instantiateItemVariationStore(varStore, fvarAxes, axisLimits)

    with verticalMetricsKeptInSync(varfont):
        setMvarDeltas(varfont, defaultDeltas)

    if varStore.VarRegionList.Region:
        varIndexMapping = varStore.optimize()
        for rec in mvar.ValueRecord:
            rec.VarIdx = varIndexMapping[rec.VarIdx]
    else:
        del varfont["MVAR"]


def _remapVarIdxMap(table, attrName, varIndexMapping, glyphOrder):
    oldMapping = getattr(table, attrName).mapping
    newMapping = [varIndexMapping[oldMapping[glyphName]] for glyphName in glyphOrder]
    setattr(table, attrName, builder.buildVarIdxMap(newMapping, glyphOrder))


# TODO(anthrotype) Add support for HVAR/VVAR in CFF2
def _instantiateVHVAR(varfont, axisLimits, tableFields, *, round=round):
    location = axisLimits.pinnedLocation()
    tableTag = tableFields.tableTag
    fvarAxes = varfont["fvar"].axes

    log.info("Instantiating %s table", tableTag)
    vhvar = varfont[tableTag].table
    varStore = vhvar.VarStore

    if "glyf" in varfont:
        # Deltas from gvar table have already been applied to the hmtx/vmtx. For full
        # instances (i.e. all axes pinned), we can simply drop HVAR/VVAR and return
        if set(location).issuperset(axis.axisTag for axis in fvarAxes):
            log.info("Dropping %s table", tableTag)
            del varfont[tableTag]
            return

    defaultDeltas = instantiateItemVariationStore(varStore, fvarAxes, axisLimits)

    if "glyf" not in varfont:
        # CFF2 fonts need hmtx/vmtx updated here. For glyf fonts, the instantiateGvar
        # function already updated the hmtx/vmtx from phantom points. Maybe remove
        # that and do it here for both CFF2 and glyf fonts?
        #
        # Specially, if a font has glyf but not gvar, the hmtx/vmtx will not have been
        # updated by instantiateGvar. Though one can call that a faulty font.
        metricsTag = "vmtx" if tableTag == "VVAR" else "hmtx"
        if metricsTag in varfont:
            advMapping = getattr(vhvar, tableFields.advMapping)
            metricsTable = varfont[metricsTag]
            metrics = metricsTable.metrics
            for glyphName, (advanceWidth, sb) in metrics.items():
                if advMapping:
                    varIdx = advMapping.mapping[glyphName]
                else:
                    varIdx = varfont.getGlyphID(glyphName)
                metrics[glyphName] = (advanceWidth + round(defaultDeltas[varIdx]), sb)

            if (
                tableTag == "VVAR"
                and getattr(vhvar, tableFields.vOrigMapping) is not None
            ):
                log.warning(
                    "VORG table not yet updated to reflect changes in VVAR table"
                )

            # For full instances (i.e. all axes pinned), we can simply drop HVAR/VVAR and return
            if set(location).issuperset(axis.axisTag for axis in fvarAxes):
                log.info("Dropping %s table", tableTag)
                del varfont[tableTag]
                return

    if varStore.VarRegionList.Region:
        # Only re-optimize VarStore if the HVAR/VVAR already uses indirect AdvWidthMap
        # or AdvHeightMap. If a direct, implicit glyphID->VariationIndex mapping is
        # used for advances, skip re-optimizing and maintain original VariationIndex.
        if getattr(vhvar, tableFields.advMapping):
            varIndexMapping = varStore.optimize(use_NO_VARIATION_INDEX=False)
            glyphOrder = varfont.getGlyphOrder()
            _remapVarIdxMap(vhvar, tableFields.advMapping, varIndexMapping, glyphOrder)
            if getattr(vhvar, tableFields.sb1):  # left or top sidebearings
                _remapVarIdxMap(vhvar, tableFields.sb1, varIndexMapping, glyphOrder)
            if getattr(vhvar, tableFields.sb2):  # right or bottom sidebearings
                _remapVarIdxMap(vhvar, tableFields.sb2, varIndexMapping, glyphOrder)
            if tableTag == "VVAR" and getattr(vhvar, tableFields.vOrigMapping):
                _remapVarIdxMap(
                    vhvar, tableFields.vOrigMapping, varIndexMapping, glyphOrder
                )


def instantiateHVAR(varfont, axisLimits):
    return _instantiateVHVAR(varfont, axisLimits, varLib.HVAR_FIELDS)


def instantiateVVAR(varfont, axisLimits):
    return _instantiateVHVAR(varfont, axisLimits, varLib.VVAR_FIELDS)


class _TupleVarStoreAdapter(object):
    def __init__(self, regions, axisOrder, tupleVarData, itemCounts):
        self.regions = regions
        self.axisOrder = axisOrder
        self.tupleVarData = tupleVarData
        self.itemCounts = itemCounts

    @classmethod
    def fromItemVarStore(cls, itemVarStore, fvarAxes):
        axisOrder = [axis.axisTag for axis in fvarAxes]
        regions = [
            region.get_support(fvarAxes) for region in itemVarStore.VarRegionList.Region
        ]
        tupleVarData = []
        itemCounts = []
        for varData in itemVarStore.VarData:
            variations = []
            varDataRegions = (regions[i] for i in varData.VarRegionIndex)
            for axes, coordinates in zip(varDataRegions, zip(*varData.Item)):
                variations.append(TupleVariation(axes, list(coordinates)))
            tupleVarData.append(variations)
            itemCounts.append(varData.ItemCount)
        return cls(regions, axisOrder, tupleVarData, itemCounts)

    def rebuildRegions(self):
        # Collect the set of all unique region axes from the current TupleVariations.
        # We use an OrderedDict to de-duplicate regions while keeping the order.
        uniqueRegions = collections.OrderedDict.fromkeys(
            (
                frozenset(var.axes.items())
                for variations in self.tupleVarData
                for var in variations
            )
        )
        # Maintain the original order for the regions that pre-existed, appending
        # the new regions at the end of the region list.
        newRegions = []
        for region in self.regions:
            regionAxes = frozenset(region.items())
            if regionAxes in uniqueRegions:
                newRegions.append(region)
                del uniqueRegions[regionAxes]
        if uniqueRegions:
            newRegions.extend(dict(region) for region in uniqueRegions)
        self.regions = newRegions

    def instantiate(self, axisLimits):
        defaultDeltaArray = []
        for variations, itemCount in zip(self.tupleVarData, self.itemCounts):
            defaultDeltas = instantiateTupleVariationStore(variations, axisLimits)
            if not defaultDeltas:
                defaultDeltas = [0] * itemCount
            defaultDeltaArray.append(defaultDeltas)

        # rebuild regions whose axes were dropped or limited
        self.rebuildRegions()

        pinnedAxes = set(axisLimits.pinnedLocation())
        self.axisOrder = [
            axisTag for axisTag in self.axisOrder if axisTag not in pinnedAxes
        ]

        return defaultDeltaArray

    def asItemVarStore(self):
        regionOrder = [frozenset(axes.items()) for axes in self.regions]
        varDatas = []
        for variations, itemCount in zip(self.tupleVarData, self.itemCounts):
            if variations:
                assert len(variations[0].coordinates) == itemCount
                varRegionIndices = [
                    regionOrder.index(frozenset(var.axes.items())) for var in variations
                ]
                varDataItems = list(zip(*(var.coordinates for var in variations)))
                varDatas.append(
                    builder.buildVarData(varRegionIndices, varDataItems, optimize=False)
                )
            else:
                varDatas.append(
                    builder.buildVarData([], [[] for _ in range(itemCount)])
                )
        regionList = builder.buildVarRegionList(self.regions, self.axisOrder)
        itemVarStore = builder.buildVarStore(regionList, varDatas)
        # remove unused regions from VarRegionList
        itemVarStore.prune_regions()
        return itemVarStore


def instantiateItemVariationStore(itemVarStore, fvarAxes, axisLimits):
    """Compute deltas at partial location, and update varStore in-place.

    Remove regions in which all axes were instanced, or fall outside the new axis
    limits. Scale the deltas of the remaining regions where only some of the axes
    were instanced.

    The number of VarData subtables, and the number of items within each, are
    not modified, in order to keep the existing VariationIndex valid.
    One may call VarStore.optimize() method after this to further optimize those.

    Args:
        varStore: An otTables.VarStore object (Item Variation Store)
        fvarAxes: list of fvar's Axis objects
        axisLimits: NormalizedAxisLimits: mapping axis tags to normalized
            min/default/max axis coordinates. May not specify coordinates/ranges for
            all the fvar axes.

    Returns:
        defaultDeltas: to be added to the default instance, of type dict of floats
            keyed by VariationIndex compound values: i.e. (outer << 16) + inner.
    """
    tupleVarStore = _TupleVarStoreAdapter.fromItemVarStore(itemVarStore, fvarAxes)
    defaultDeltaArray = tupleVarStore.instantiate(axisLimits)
    newItemVarStore = tupleVarStore.asItemVarStore()

    itemVarStore.VarRegionList = newItemVarStore.VarRegionList
    if not hasattr(itemVarStore, "VarDataCount"):  # Happens fromXML
        itemVarStore.VarDataCount = len(newItemVarStore.VarData)
    assert itemVarStore.VarDataCount == newItemVarStore.VarDataCount
    itemVarStore.VarData = newItemVarStore.VarData

    defaultDeltas = {
        ((major << 16) + minor): delta
        for major, deltas in enumerate(defaultDeltaArray)
        for minor, delta in enumerate(deltas)
    }
    defaultDeltas[itemVarStore.NO_VARIATION_INDEX] = 0
    return defaultDeltas


def instantiateOTL(varfont, axisLimits):
    # TODO(anthrotype) Support partial instancing of JSTF and BASE tables

    if (
        "GDEF" not in varfont
        or varfont["GDEF"].table.Version < 0x00010003
        or not varfont["GDEF"].table.VarStore
    ):
        return

    if "GPOS" in varfont:
        msg = "Instantiating GDEF and GPOS tables"
    else:
        msg = "Instantiating GDEF table"
    log.info(msg)

    gdef = varfont["GDEF"].table
    varStore = gdef.VarStore
    fvarAxes = varfont["fvar"].axes

    defaultDeltas = instantiateItemVariationStore(varStore, fvarAxes, axisLimits)

    # When VF are built, big lookups may overflow and be broken into multiple
    # subtables. MutatorMerger (which inherits from AligningMerger) reattaches
    # them upon instancing, in case they can now fit a single subtable (if not,
    # they will be split again upon compilation).
    # This 'merger' also works as a 'visitor' that traverses the OTL tables and
    # calls specific methods when instances of a given type are found.
    # Specifically, it adds default deltas to GPOS Anchors/ValueRecords and GDEF
    # LigatureCarets, and optionally deletes all VariationIndex tables if the
    # VarStore is fully instanced.
    merger = MutatorMerger(
        varfont, defaultDeltas, deleteVariations=(not varStore.VarRegionList.Region)
    )
    merger.mergeTables(varfont, [varfont], ["GDEF", "GPOS"])

    if varStore.VarRegionList.Region:
        varIndexMapping = varStore.optimize()
        gdef.remap_device_varidxes(varIndexMapping)
        if "GPOS" in varfont:
            varfont["GPOS"].table.remap_device_varidxes(varIndexMapping)
    else:
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


def _isValidAvarSegmentMap(axisTag, segmentMap):
    if not segmentMap:
        return True
    if not {(-1.0, -1.0), (0, 0), (1.0, 1.0)}.issubset(segmentMap.items()):
        log.warning(
            f"Invalid avar SegmentMap record for axis '{axisTag}': does not "
            "include all required value maps {-1.0: -1.0, 0: 0, 1.0: 1.0}"
        )
        return False
    previousValue = None
    for fromCoord, toCoord in sorted(segmentMap.items()):
        if previousValue is not None and previousValue > toCoord:
            log.warning(
                f"Invalid avar AxisValueMap({fromCoord}, {toCoord}) record "
                f"for axis '{axisTag}': the toCoordinate value must be >= to "
                f"the toCoordinate value of the preceding record ({previousValue})."
            )
            return False
        previousValue = toCoord
    return True


def instantiateAvar(varfont, axisLimits):
    # 'axisLimits' dict must contain user-space (non-normalized) coordinates.

    avar = varfont["avar"]
    if getattr(avar, "majorVersion", 1) >= 2 and avar.table.VarStore:
        raise NotImplementedError("avar table with VarStore is not supported")

    segments = avar.segments

    # drop table if we instantiate all the axes
    pinnedAxes = set(axisLimits.pinnedLocation())
    if pinnedAxes.issuperset(segments):
        log.info("Dropping avar table")
        del varfont["avar"]
        return

    log.info("Instantiating avar table")
    for axis in pinnedAxes:
        if axis in segments:
            del segments[axis]

    # First compute the default normalization for axisLimits coordinates: i.e.
    # min = -1.0, default = 0, max = +1.0, and in between values interpolated linearly,
    # without using the avar table's mappings.
    # Then, for each SegmentMap, if we are restricting its axis, compute the new
    # mappings by dividing the key/value pairs by the desired new min/max values,
    # dropping any mappings that fall outside the restricted range.
    # The keys ('fromCoord') are specified in default normalized coordinate space,
    # whereas the values ('toCoord') are "mapped forward" using the SegmentMap.
    normalizedRanges = axisLimits.normalize(varfont, usingAvar=False)
    newSegments = {}
    for axisTag, mapping in segments.items():
        if not _isValidAvarSegmentMap(axisTag, mapping):
            continue
        if mapping and axisTag in normalizedRanges:
            axisRange = normalizedRanges[axisTag]
            mappedMin = floatToFixedToFloat(
                piecewiseLinearMap(axisRange.minimum, mapping), 14
            )
            mappedDef = floatToFixedToFloat(
                piecewiseLinearMap(axisRange.default, mapping), 14
            )
            mappedMax = floatToFixedToFloat(
                piecewiseLinearMap(axisRange.maximum, mapping), 14
            )
            mappedAxisLimit = NormalizedAxisTripleAndDistances(
                mappedMin,
                mappedDef,
                mappedMax,
                axisRange.distanceNegative,
                axisRange.distancePositive,
            )
            newMapping = {}
            for fromCoord, toCoord in mapping.items():
                if fromCoord < axisRange.minimum or fromCoord > axisRange.maximum:
                    continue
                fromCoord = axisRange.renormalizeValue(fromCoord)

                assert mappedMin <= toCoord <= mappedMax
                toCoord = mappedAxisLimit.renormalizeValue(toCoord)

                fromCoord = floatToFixedToFloat(fromCoord, 14)
                toCoord = floatToFixedToFloat(toCoord, 14)
                newMapping[fromCoord] = toCoord
            newMapping.update({-1.0: -1.0, 0.0: 0.0, 1.0: 1.0})
            newSegments[axisTag] = newMapping
        else:
            newSegments[axisTag] = mapping
    avar.segments = newSegments


def isInstanceWithinAxisRanges(location, axisRanges):
    for axisTag, coord in location.items():
        if axisTag in axisRanges:
            axisRange = axisRanges[axisTag]
            if coord < axisRange.minimum or coord > axisRange.maximum:
                return False
    return True


def instantiateFvar(varfont, axisLimits):
    # 'axisLimits' dict must contain user-space (non-normalized) coordinates

    location = axisLimits.pinnedLocation()

    fvar = varfont["fvar"]

    # drop table if we instantiate all the axes
    if set(location).issuperset(axis.axisTag for axis in fvar.axes):
        log.info("Dropping fvar table")
        del varfont["fvar"]
        return

    log.info("Instantiating fvar table")

    axes = []
    for axis in fvar.axes:
        axisTag = axis.axisTag
        if axisTag in location:
            continue
        if axisTag in axisLimits:
            triple = axisLimits[axisTag]
            if triple.default is None:
                triple = (triple.minimum, axis.defaultValue, triple.maximum)
            axis.minValue, axis.defaultValue, axis.maxValue = triple
        axes.append(axis)
    fvar.axes = axes

    # only keep NamedInstances whose coordinates == pinned axis location
    instances = []
    for instance in fvar.instances:
        if any(instance.coordinates[axis] != value for axis, value in location.items()):
            continue
        for axisTag in location:
            del instance.coordinates[axisTag]
        if not isInstanceWithinAxisRanges(instance.coordinates, axisLimits):
            continue
        instances.append(instance)
    fvar.instances = instances


def instantiateSTAT(varfont, axisLimits):
    # 'axisLimits' dict must contain user-space (non-normalized) coordinates

    stat = varfont["STAT"].table
    if not stat.DesignAxisRecord or not (
        stat.AxisValueArray and stat.AxisValueArray.AxisValue
    ):
        return  # STAT table empty, nothing to do

    log.info("Instantiating STAT table")
    newAxisValueTables = axisValuesFromAxisLimits(stat, axisLimits)
    stat.AxisValueCount = len(newAxisValueTables)
    if stat.AxisValueCount:
        stat.AxisValueArray.AxisValue = newAxisValueTables
    else:
        stat.AxisValueArray = None


def axisValuesFromAxisLimits(stat, axisLimits):
    def isAxisValueOutsideLimits(axisTag, axisValue):
        if axisTag in axisLimits:
            triple = axisLimits[axisTag]
            if axisValue < triple.minimum or axisValue > triple.maximum:
                return True
        return False

    # only keep AxisValues whose axis is not pinned nor restricted, or is pinned at the
    # exact (nominal) value, or is restricted but the value is within the new range
    designAxes = stat.DesignAxisRecord.Axis
    newAxisValueTables = []
    for axisValueTable in stat.AxisValueArray.AxisValue:
        axisValueFormat = axisValueTable.Format
        if axisValueFormat in (1, 2, 3):
            axisTag = designAxes[axisValueTable.AxisIndex].AxisTag
            if axisValueFormat == 2:
                axisValue = axisValueTable.NominalValue
            else:
                axisValue = axisValueTable.Value
            if isAxisValueOutsideLimits(axisTag, axisValue):
                continue
        elif axisValueFormat == 4:
            # drop 'non-analytic' AxisValue if _any_ AxisValueRecord doesn't match
            # the pinned location or is outside range
            dropAxisValueTable = False
            for rec in axisValueTable.AxisValueRecord:
                axisTag = designAxes[rec.AxisIndex].AxisTag
                axisValue = rec.Value
                if isAxisValueOutsideLimits(axisTag, axisValue):
                    dropAxisValueTable = True
                    break
            if dropAxisValueTable:
                continue
        else:
            log.warning("Unknown AxisValue table format (%s); ignored", axisValueFormat)
        newAxisValueTables.append(axisValueTable)
    return newAxisValueTables


def setMacOverlapFlags(glyfTable):
    flagOverlapCompound = _g_l_y_f.OVERLAP_COMPOUND
    flagOverlapSimple = _g_l_y_f.flagOverlapSimple
    for glyphName in glyfTable.keys():
        glyph = glyfTable[glyphName]
        # Set OVERLAP_COMPOUND bit for compound glyphs
        if glyph.isComposite():
            glyph.components[0].flags |= flagOverlapCompound
        # Set OVERLAP_SIMPLE bit for simple glyphs
        elif glyph.numberOfContours > 0:
            glyph.flags[0] |= flagOverlapSimple


def normalize(value, triple, avarMapping):
    value = normalizeValue(value, triple)
    if avarMapping:
        value = piecewiseLinearMap(value, avarMapping)
    # Quantize to F2Dot14, to avoid surprise interpolations.
    return floatToFixedToFloat(value, 14)


def sanityCheckVariableTables(varfont):
    if "fvar" not in varfont:
        raise ValueError("Missing required table fvar")
    if "gvar" in varfont:
        if "glyf" not in varfont:
            raise ValueError("Can't have gvar without glyf")


def instantiateVariableFont(
    varfont,
    axisLimits,
    inplace=False,
    optimize=True,
    overlap=OverlapMode.KEEP_AND_SET_FLAGS,
    updateFontNames=False,
    *,
    downgradeCFF2=False,
):
    """Instantiate variable font, either fully or partially.

    Depending on whether the `axisLimits` dictionary references all or some of the
    input varfont's axes, the output font will either be a full instance (static
    font) or a variable font with possibly less variation data.

    Args:
        varfont: a TTFont instance, which must contain at least an 'fvar' table.
        axisLimits: a dict keyed by axis tags (str) containing the coordinates (float)
            along one or more axes where the desired instance will be located.
            If the value is `None`, the default coordinate as per 'fvar' table for
            that axis is used.
            The limit values can also be (min, max) tuples for restricting an
            axis's variation range. The default axis value must be included in
            the new range.
        inplace (bool): whether to modify input TTFont object in-place instead of
            returning a distinct object.
        optimize (bool): if False, do not perform IUP-delta optimization on the
            remaining 'gvar' table's deltas. Possibly faster, and might work around
            rendering issues in some buggy environments, at the cost of a slightly
            larger file size.
        overlap (OverlapMode): variable fonts usually contain overlapping contours, and
            some font rendering engines on Apple platforms require that the
            `OVERLAP_SIMPLE` and `OVERLAP_COMPOUND` flags in the 'glyf' table be set to
            force rendering using a non-zero fill rule. Thus we always set these flags
            on all glyphs to maximise cross-compatibility of the generated instance.
            You can disable this by passing OverlapMode.KEEP_AND_DONT_SET_FLAGS.
            If you want to remove the overlaps altogether and merge overlapping
            contours and components, you can pass OverlapMode.REMOVE (or
            REMOVE_AND_IGNORE_ERRORS to not hard-fail on tricky glyphs). Note that this
            requires the skia-pathops package (available to pip install).
            The overlap parameter only has effect when generating full static instances.
        updateFontNames (bool): if True, update the instantiated font's name table using
            the Axis Value Tables from the STAT table. The name table and the style bits
            in the head and OS/2 table will be updated so they conform to the R/I/B/BI
            model. If the STAT table is missing or an Axis Value table is missing for
            a given axis coordinate, a ValueError will be raised.
        downgradeCFF2 (bool): if True, downgrade the CFF2 table to CFF table when possible
            ie. full instancing of all axes. This is useful for compatibility with older
            software that does not support CFF2. Defaults to False. Note that this
            operation also removes overlaps within glyph shapes, as CFF does not support
            overlaps but CFF2 does.
    """
    # 'overlap' used to be bool and is now enum; for backward compat keep accepting bool
    overlap = OverlapMode(int(overlap))

    sanityCheckVariableTables(varfont)

    axisLimits = AxisLimits(axisLimits).limitAxesAndPopulateDefaults(varfont)

    log.info("Restricted limits: %s", axisLimits)

    normalizedLimits = axisLimits.normalize(varfont)

    log.info("Normalized limits: %s", normalizedLimits)

    if not inplace:
        varfont = deepcopy(varfont)

    if "DSIG" in varfont:
        del varfont["DSIG"]

    if updateFontNames:
        log.info("Updating name table")
        names.updateNameTable(varfont, axisLimits)

    if "VARC" in varfont:
        instantiateVARC(varfont, normalizedLimits)

    if "CFF2" in varfont:
        instantiateCFF2(varfont, normalizedLimits, downgrade=downgradeCFF2)

    if "gvar" in varfont:
        instantiateGvar(varfont, normalizedLimits, optimize=optimize)

    if "cvar" in varfont:
        instantiateCvar(varfont, normalizedLimits)

    if "MVAR" in varfont:
        instantiateMVAR(varfont, normalizedLimits)

    if "HVAR" in varfont:
        instantiateHVAR(varfont, normalizedLimits)

    if "VVAR" in varfont:
        instantiateVVAR(varfont, normalizedLimits)

    instantiateOTL(varfont, normalizedLimits)

    instantiateFeatureVariations(varfont, normalizedLimits)

    if "avar" in varfont:
        instantiateAvar(varfont, axisLimits)

    with names.pruningUnusedNames(varfont):
        if "STAT" in varfont:
            instantiateSTAT(varfont, axisLimits)

        instantiateFvar(varfont, axisLimits)

    if "fvar" not in varfont:
        if "glyf" in varfont:
            if overlap == OverlapMode.KEEP_AND_SET_FLAGS:
                setMacOverlapFlags(varfont["glyf"])
            elif overlap in (OverlapMode.REMOVE, OverlapMode.REMOVE_AND_IGNORE_ERRORS):
                from fontTools.ttLib.removeOverlaps import removeOverlaps

                log.info("Removing overlaps from glyf table")
                removeOverlaps(
                    varfont,
                    ignoreErrors=(overlap == OverlapMode.REMOVE_AND_IGNORE_ERRORS),
                )

    if "OS/2" in varfont:
        varfont["OS/2"].recalcAvgCharWidth(varfont)

    varLib.set_default_weight_width_slant(
        varfont, location=axisLimits.defaultLocation()
    )

    if updateFontNames:
        # Set Regular/Italic/Bold/Bold Italic bits as appropriate, after the
        # name table has been updated.
        setRibbiBits(varfont)

    return varfont


def setRibbiBits(font):
    """Set the `head.macStyle` and `OS/2.fsSelection` style bits
    appropriately."""

    english_ribbi_style = font["name"].getName(names.NameID.SUBFAMILY_NAME, 3, 1, 0x409)
    if english_ribbi_style is None:
        return

    styleMapStyleName = english_ribbi_style.toStr().lower()
    if styleMapStyleName not in {"regular", "bold", "italic", "bold italic"}:
        return

    if styleMapStyleName == "bold":
        font["head"].macStyle = 0b01
    elif styleMapStyleName == "bold italic":
        font["head"].macStyle = 0b11
    elif styleMapStyleName == "italic":
        font["head"].macStyle = 0b10

    selection = font["OS/2"].fsSelection
    # First clear...
    selection &= ~(1 << 0)
    selection &= ~(1 << 5)
    selection &= ~(1 << 6)
    # ...then re-set the bits.
    if styleMapStyleName == "regular":
        selection |= 1 << 6
    elif styleMapStyleName == "bold":
        selection |= 1 << 5
    elif styleMapStyleName == "italic":
        selection |= 1 << 0
    elif styleMapStyleName == "bold italic":
        selection |= 1 << 0
        selection |= 1 << 5
    font["OS/2"].fsSelection = selection


def parseLimits(limits: Iterable[str]) -> Dict[str, Optional[AxisTriple]]:
    result = {}
    for limitString in limits:
        match = re.match(
            r"^(\w{1,4})=(?:(drop)|(?:([^:]*)(?:[:]([^:]*))?(?:[:]([^:]*))?))$",
            limitString,
        )
        if not match:
            raise ValueError("invalid location format: %r" % limitString)
        tag = match.group(1).ljust(4)

        if match.group(2):  # 'drop'
            result[tag] = None
            continue

        triple = match.group(3, 4, 5)

        if triple[1] is None:  # "value" syntax
            triple = (triple[0], triple[0], triple[0])
        elif triple[2] is None:  # "min:max" syntax
            triple = (triple[0], None, triple[1])

        triple = tuple(float(v) if v else None for v in triple)

        result[tag] = AxisTriple(*triple)

    return result


def parseArgs(args):
    """Parse argv.

    Returns:
        3-tuple (infile, axisLimits, options)
        axisLimits is either a Dict[str, Optional[float]], for pinning variation axes
        to specific coordinates along those axes (with `None` as a placeholder for an
        axis' default value); or a Dict[str, Tuple(float, float)], meaning limit this
        axis to min/max range.
        Axes locations are in user-space coordinates, as defined in the "fvar" table.
    """
    from fontTools import configLogger
    import argparse

    parser = argparse.ArgumentParser(
        "fonttools varLib.instancer",
        description="Partially instantiate a variable font",
    )
    parser.add_argument("input", metavar="INPUT.ttf", help="Input variable TTF file.")
    parser.add_argument(
        "locargs",
        metavar="AXIS=LOC",
        nargs="*",
        help="List of space separated locations. A location consists of "
        "the tag of a variation axis, followed by '=' and the literal, "
        "string 'drop', or colon-separated list of one to three values, "
        "each of which is the empty string, or a number. "
        "E.g.: wdth=100 or wght=75.0:125.0 or wght=100:400:700 or wght=:500: "
        "or wght=drop",
    )
    parser.add_argument(
        "-o",
        "--output",
        metavar="OUTPUT.ttf",
        default=None,
        help="Output instance TTF file (default: INPUT-instance.ttf).",
    )
    parser.add_argument(
        "--no-optimize",
        dest="optimize",
        action="store_false",
        help="Don't perform IUP optimization on the remaining gvar TupleVariations",
    )
    parser.add_argument(
        "--no-overlap-flag",
        dest="overlap",
        action="store_false",
        help="Don't set OVERLAP_SIMPLE/OVERLAP_COMPOUND glyf flags (only applicable "
        "when generating a full instance)",
    )
    parser.add_argument(
        "--remove-overlaps",
        dest="remove_overlaps",
        action="store_true",
        help="Merge overlapping contours and components (only applicable "
        "when generating a full instance). Requires skia-pathops",
    )
    parser.add_argument(
        "--ignore-overlap-errors",
        dest="ignore_overlap_errors",
        action="store_true",
        help="Don't crash if the remove-overlaps operation fails for some glyphs.",
    )
    parser.add_argument(
        "--update-name-table",
        action="store_true",
        help="Update the instantiated font's `name` table. Input font must have "
        "a STAT table with Axis Value Tables",
    )
    parser.add_argument(
        "--downgrade-cff2",
        action="store_true",
        help="If all axes are pinned, downgrade CFF2 to CFF table format",
    )
    parser.add_argument(
        "--no-recalc-timestamp",
        dest="recalc_timestamp",
        action="store_false",
        help="Don't set the output font's timestamp to the current time.",
    )
    parser.add_argument(
        "--no-recalc-bounds",
        dest="recalc_bounds",
        action="store_false",
        help="Don't recalculate font bounding boxes",
    )
    loggingGroup = parser.add_mutually_exclusive_group(required=False)
    loggingGroup.add_argument(
        "-v", "--verbose", action="store_true", help="Run more verbosely."
    )
    loggingGroup.add_argument(
        "-q", "--quiet", action="store_true", help="Turn verbosity off."
    )
    options = parser.parse_args(args)

    if options.remove_overlaps:
        if options.ignore_overlap_errors:
            options.overlap = OverlapMode.REMOVE_AND_IGNORE_ERRORS
        else:
            options.overlap = OverlapMode.REMOVE
    else:
        options.overlap = OverlapMode(int(options.overlap))

    infile = options.input
    if not os.path.isfile(infile):
        parser.error("No such file '{}'".format(infile))

    configLogger(
        level=("DEBUG" if options.verbose else "ERROR" if options.quiet else "INFO")
    )

    try:
        axisLimits = parseLimits(options.locargs)
    except ValueError as e:
        parser.error(str(e))

    if len(axisLimits) != len(options.locargs):
        parser.error("Specified multiple limits for the same axis")

    return (infile, axisLimits, options)


def main(args=None):
    """Partially instantiate a variable font"""
    infile, axisLimits, options = parseArgs(args)
    log.info("Restricting axes: %s", axisLimits)

    log.info("Loading variable font")
    varfont = TTFont(
        infile,
        recalcTimestamp=options.recalc_timestamp,
        recalcBBoxes=options.recalc_bounds,
    )

    isFullInstance = {
        axisTag
        for axisTag, limit in axisLimits.items()
        if limit is None or limit[0] == limit[2]
    }.issuperset(axis.axisTag for axis in varfont["fvar"].axes)

    instantiateVariableFont(
        varfont,
        axisLimits,
        inplace=True,
        optimize=options.optimize,
        overlap=options.overlap,
        updateFontNames=options.update_name_table,
        downgradeCFF2=options.downgrade_cff2,
    )

    suffix = "-instance" if isFullInstance else "-partial"
    outfile = (
        makeOutputFileName(infile, overWrite=True, suffix=suffix)
        if not options.output
        else options.output
    )

    log.info(
        "Saving %s font %s",
        "instance" if isFullInstance else "partial variable",
        outfile,
    )
    varfont.save(outfile)