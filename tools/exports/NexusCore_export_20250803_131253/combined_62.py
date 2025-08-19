
# === NexusCore/tools\exports\export_20250803_114325\combined_66.py ===

# === NexusCore/openenv\Lib\site-packages\debugpy\_vendored\pydevd\pydevd_attach_to_process\winappdbg\event.py ===
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
Event handling module.

@see: U{http://apps.sourceforge.net/trac/winappdbg/wiki/Debugging}

@group Debugging:
    EventHandler, EventSift

@group Debug events:
    EventFactory,
    EventDispatcher,
    Event,
    NoEvent,
    CreateProcessEvent,
    CreateThreadEvent,
    ExitProcessEvent,
    ExitThreadEvent,
    LoadDLLEvent,
    UnloadDLLEvent,
    OutputDebugStringEvent,
    RIPEvent,
    ExceptionEvent

@group Warnings:
    EventCallbackWarning
"""

__revision__ = "$Id$"

__all__ = [
    # Factory of Event objects and all of it's subclasses.
    # Users should not need to instance Event objects directly.
    "EventFactory",
    # Event dispatcher used internally by the Debug class.
    "EventDispatcher",
    # Base classes for user-defined event handlers.
    "EventHandler",
    "EventSift",
    # Warning for uncaught exceptions on event callbacks.
    "EventCallbackWarning",
    # Dummy event object that can be used as a placeholder.
    # It's never returned by the EventFactory.
    "NoEvent",
    # Base class for event objects.
    "Event",
    # Event objects.
    "CreateProcessEvent",
    "CreateThreadEvent",
    "ExitProcessEvent",
    "ExitThreadEvent",
    "LoadDLLEvent",
    "UnloadDLLEvent",
    "OutputDebugStringEvent",
    "RIPEvent",
    "ExceptionEvent",
]

from winappdbg import win32
from winappdbg import compat
from winappdbg.win32 import FileHandle, ProcessHandle, ThreadHandle
from winappdbg.breakpoint import ApiHook
from winappdbg.module import Module
from winappdbg.thread import Thread
from winappdbg.process import Process
from winappdbg.textio import HexDump
from winappdbg.util import StaticClass, PathOperations

import sys
import ctypes
import warnings
import traceback

# ==============================================================================


class EventCallbackWarning(RuntimeWarning):
    """
    This warning is issued when an uncaught exception was raised by a
    user-defined event handler.
    """


# ==============================================================================


class Event(object):
    """
    Event object.

    @type eventMethod: str
    @cvar eventMethod:
        Method name to call when using L{EventHandler} subclasses.
        Used internally.

    @type eventName: str
    @cvar eventName:
        User-friendly name of the event.

    @type eventDescription: str
    @cvar eventDescription:
        User-friendly description of the event.

    @type debug: L{Debug}
    @ivar debug:
        Debug object that received the event.

    @type raw: L{DEBUG_EVENT}
    @ivar raw:
        Raw DEBUG_EVENT structure as used by the Win32 API.

    @type continueStatus: int
    @ivar continueStatus:
        Continue status to pass to L{win32.ContinueDebugEvent}.
    """

    eventMethod = "unknown_event"
    eventName = "Unknown event"
    eventDescription = "A debug event of an unknown type has occured."

    def __init__(self, debug, raw):
        """
        @type  debug: L{Debug}
        @param debug: Debug object that received the event.

        @type  raw: L{DEBUG_EVENT}
        @param raw: Raw DEBUG_EVENT structure as used by the Win32 API.
        """
        self.debug = debug
        self.raw = raw
        self.continueStatus = win32.DBG_EXCEPTION_NOT_HANDLED

    ##    @property
    ##    def debug(self):
    ##        """
    ##        @rtype  debug: L{Debug}
    ##        @return debug:
    ##            Debug object that received the event.
    ##        """
    ##        return self.__debug()

    def get_event_name(self):
        """
        @rtype:  str
        @return: User-friendly name of the event.
        """
        return self.eventName

    def get_event_description(self):
        """
        @rtype:  str
        @return: User-friendly description of the event.
        """
        return self.eventDescription

    def get_event_code(self):
        """
        @rtype:  int
        @return: Debug event code as defined in the Win32 API.
        """
        return self.raw.dwDebugEventCode

    ##    # Compatibility with version 1.0
    ##    # XXX to be removed in version 1.4
    ##    def get_code(self):
    ##        """
    ##        Alias of L{get_event_code} for backwards compatibility
    ##        with WinAppDbg version 1.0.
    ##        Will be phased out in the next version.
    ##
    ##        @rtype:  int
    ##        @return: Debug event code as defined in the Win32 API.
    ##        """
    ##        return self.get_event_code()

    def get_pid(self):
        """
        @see: L{get_process}

        @rtype:  int
        @return: Process global ID where the event occured.
        """
        return self.raw.dwProcessId

    def get_tid(self):
        """
        @see: L{get_thread}

        @rtype:  int
        @return: Thread global ID where the event occured.
        """
        return self.raw.dwThreadId

    def get_process(self):
        """
        @see: L{get_pid}

        @rtype:  L{Process}
        @return: Process where the event occured.
        """
        pid = self.get_pid()
        system = self.debug.system
        if system.has_process(pid):
            process = system.get_process(pid)
        else:
            # XXX HACK
            # The process object was missing for some reason, so make a new one.
            process = Process(pid)
            system._add_process(process)
            ##            process.scan_threads()    # not needed
            process.scan_modules()
        return process

    def get_thread(self):
        """
        @see: L{get_tid}

        @rtype:  L{Thread}
        @return: Thread where the event occured.
        """
        tid = self.get_tid()
        process = self.get_process()
        if process.has_thread(tid):
            thread = process.get_thread(tid)
        else:
            # XXX HACK
            # The thread object was missing for some reason, so make a new one.
            thread = Thread(tid)
            process._add_thread(thread)
        return thread


# ==============================================================================


class NoEvent(Event):
    """
    No event.

    Dummy L{Event} object that can be used as a placeholder when no debug
    event has occured yet. It's never returned by the L{EventFactory}.
    """

    eventMethod = "no_event"
    eventName = "No event"
    eventDescription = "No debug event has occured."

    def __init__(self, debug, raw=None):
        Event.__init__(self, debug, raw)

    def __len__(self):
        """
        Always returns C{0}, so when evaluating the object as a boolean it's
        always C{False}. This prevents L{Debug.cont} from trying to continue
        a dummy event.
        """
        return 0

    def get_event_code(self):
        return -1

    def get_pid(self):
        return -1

    def get_tid(self):
        return -1

    def get_process(self):
        return Process(self.get_pid())

    def get_thread(self):
        return Thread(self.get_tid())


# ==============================================================================


class ExceptionEvent(Event):
    """
    Exception event.

    @type exceptionName: dict( int S{->} str )
    @cvar exceptionName:
        Mapping of exception constants to their names.

    @type exceptionDescription: dict( int S{->} str )
    @cvar exceptionDescription:
        Mapping of exception constants to user-friendly strings.

    @type breakpoint: L{Breakpoint}
    @ivar breakpoint:
        If the exception was caused by one of our breakpoints, this member
        contains a reference to the breakpoint object. Otherwise it's not
        defined. It should only be used from the condition or action callback
        routines, instead of the event handler.

    @type hook: L{Hook}
    @ivar hook:
        If the exception was caused by a function hook, this member contains a
        reference to the hook object. Otherwise it's not defined. It should
        only be used from the hook callback routines, instead of the event
        handler.
    """

    eventName = "Exception event"
    eventDescription = "An exception was raised by the debugee."

    __exceptionMethod = {
        win32.EXCEPTION_ACCESS_VIOLATION: "access_violation",
        win32.EXCEPTION_ARRAY_BOUNDS_EXCEEDED: "array_bounds_exceeded",
        win32.EXCEPTION_BREAKPOINT: "breakpoint",
        win32.EXCEPTION_DATATYPE_MISALIGNMENT: "datatype_misalignment",
        win32.EXCEPTION_FLT_DENORMAL_OPERAND: "float_denormal_operand",
        win32.EXCEPTION_FLT_DIVIDE_BY_ZERO: "float_divide_by_zero",
        win32.EXCEPTION_FLT_INEXACT_RESULT: "float_inexact_result",
        win32.EXCEPTION_FLT_INVALID_OPERATION: "float_invalid_operation",
        win32.EXCEPTION_FLT_OVERFLOW: "float_overflow",
        win32.EXCEPTION_FLT_STACK_CHECK: "float_stack_check",
        win32.EXCEPTION_FLT_UNDERFLOW: "float_underflow",
        win32.EXCEPTION_ILLEGAL_INSTRUCTION: "illegal_instruction",
        win32.EXCEPTION_IN_PAGE_ERROR: "in_page_error",
        win32.EXCEPTION_INT_DIVIDE_BY_ZERO: "integer_divide_by_zero",
        win32.EXCEPTION_INT_OVERFLOW: "integer_overflow",
        win32.EXCEPTION_INVALID_DISPOSITION: "invalid_disposition",
        win32.EXCEPTION_NONCONTINUABLE_EXCEPTION: "noncontinuable_exception",
        win32.EXCEPTION_PRIV_INSTRUCTION: "privileged_instruction",
        win32.EXCEPTION_SINGLE_STEP: "single_step",
        win32.EXCEPTION_STACK_OVERFLOW: "stack_overflow",
        win32.EXCEPTION_GUARD_PAGE: "guard_page",
        win32.EXCEPTION_INVALID_HANDLE: "invalid_handle",
        win32.EXCEPTION_POSSIBLE_DEADLOCK: "possible_deadlock",
        win32.EXCEPTION_WX86_BREAKPOINT: "wow64_breakpoint",
        win32.CONTROL_C_EXIT: "control_c_exit",
        win32.DBG_CONTROL_C: "debug_control_c",
        win32.MS_VC_EXCEPTION: "ms_vc_exception",
    }

    __exceptionName = {
        win32.EXCEPTION_ACCESS_VIOLATION: "EXCEPTION_ACCESS_VIOLATION",
        win32.EXCEPTION_ARRAY_BOUNDS_EXCEEDED: "EXCEPTION_ARRAY_BOUNDS_EXCEEDED",
        win32.EXCEPTION_BREAKPOINT: "EXCEPTION_BREAKPOINT",
        win32.EXCEPTION_DATATYPE_MISALIGNMENT: "EXCEPTION_DATATYPE_MISALIGNMENT",
        win32.EXCEPTION_FLT_DENORMAL_OPERAND: "EXCEPTION_FLT_DENORMAL_OPERAND",
        win32.EXCEPTION_FLT_DIVIDE_BY_ZERO: "EXCEPTION_FLT_DIVIDE_BY_ZERO",
        win32.EXCEPTION_FLT_INEXACT_RESULT: "EXCEPTION_FLT_INEXACT_RESULT",
        win32.EXCEPTION_FLT_INVALID_OPERATION: "EXCEPTION_FLT_INVALID_OPERATION",
        win32.EXCEPTION_FLT_OVERFLOW: "EXCEPTION_FLT_OVERFLOW",
        win32.EXCEPTION_FLT_STACK_CHECK: "EXCEPTION_FLT_STACK_CHECK",
        win32.EXCEPTION_FLT_UNDERFLOW: "EXCEPTION_FLT_UNDERFLOW",
        win32.EXCEPTION_ILLEGAL_INSTRUCTION: "EXCEPTION_ILLEGAL_INSTRUCTION",
        win32.EXCEPTION_IN_PAGE_ERROR: "EXCEPTION_IN_PAGE_ERROR",
        win32.EXCEPTION_INT_DIVIDE_BY_ZERO: "EXCEPTION_INT_DIVIDE_BY_ZERO",
        win32.EXCEPTION_INT_OVERFLOW: "EXCEPTION_INT_OVERFLOW",
        win32.EXCEPTION_INVALID_DISPOSITION: "EXCEPTION_INVALID_DISPOSITION",
        win32.EXCEPTION_NONCONTINUABLE_EXCEPTION: "EXCEPTION_NONCONTINUABLE_EXCEPTION",
        win32.EXCEPTION_PRIV_INSTRUCTION: "EXCEPTION_PRIV_INSTRUCTION",
        win32.EXCEPTION_SINGLE_STEP: "EXCEPTION_SINGLE_STEP",
        win32.EXCEPTION_STACK_OVERFLOW: "EXCEPTION_STACK_OVERFLOW",
        win32.EXCEPTION_GUARD_PAGE: "EXCEPTION_GUARD_PAGE",
        win32.EXCEPTION_INVALID_HANDLE: "EXCEPTION_INVALID_HANDLE",
        win32.EXCEPTION_POSSIBLE_DEADLOCK: "EXCEPTION_POSSIBLE_DEADLOCK",
        win32.EXCEPTION_WX86_BREAKPOINT: "EXCEPTION_WX86_BREAKPOINT",
        win32.CONTROL_C_EXIT: "CONTROL_C_EXIT",
        win32.DBG_CONTROL_C: "DBG_CONTROL_C",
        win32.MS_VC_EXCEPTION: "MS_VC_EXCEPTION",
    }

    __exceptionDescription = {
        win32.EXCEPTION_ACCESS_VIOLATION: "Access violation",
        win32.EXCEPTION_ARRAY_BOUNDS_EXCEEDED: "Array bounds exceeded",
        win32.EXCEPTION_BREAKPOINT: "Breakpoint",
        win32.EXCEPTION_DATATYPE_MISALIGNMENT: "Datatype misalignment",
        win32.EXCEPTION_FLT_DENORMAL_OPERAND: "Float denormal operand",
        win32.EXCEPTION_FLT_DIVIDE_BY_ZERO: "Float divide by zero",
        win32.EXCEPTION_FLT_INEXACT_RESULT: "Float inexact result",
        win32.EXCEPTION_FLT_INVALID_OPERATION: "Float invalid operation",
        win32.EXCEPTION_FLT_OVERFLOW: "Float overflow",
        win32.EXCEPTION_FLT_STACK_CHECK: "Float stack check",
        win32.EXCEPTION_FLT_UNDERFLOW: "Float underflow",
        win32.EXCEPTION_ILLEGAL_INSTRUCTION: "Illegal instruction",
        win32.EXCEPTION_IN_PAGE_ERROR: "In-page error",
        win32.EXCEPTION_INT_DIVIDE_BY_ZERO: "Integer divide by zero",
        win32.EXCEPTION_INT_OVERFLOW: "Integer overflow",
        win32.EXCEPTION_INVALID_DISPOSITION: "Invalid disposition",
        win32.EXCEPTION_NONCONTINUABLE_EXCEPTION: "Noncontinuable exception",
        win32.EXCEPTION_PRIV_INSTRUCTION: "Privileged instruction",
        win32.EXCEPTION_SINGLE_STEP: "Single step event",
        win32.EXCEPTION_STACK_OVERFLOW: "Stack limits overflow",
        win32.EXCEPTION_GUARD_PAGE: "Guard page hit",
        win32.EXCEPTION_INVALID_HANDLE: "Invalid handle",
        win32.EXCEPTION_POSSIBLE_DEADLOCK: "Possible deadlock",
        win32.EXCEPTION_WX86_BREAKPOINT: "WOW64 breakpoint",
        win32.CONTROL_C_EXIT: "Control-C exit",
        win32.DBG_CONTROL_C: "Debug Control-C",
        win32.MS_VC_EXCEPTION: "Microsoft Visual C++ exception",
    }

    @property
    def eventMethod(self):
        return self.__exceptionMethod.get(self.get_exception_code(), "unknown_exception")

    def get_exception_name(self):
        """
        @rtype:  str
        @return: Name of the exception as defined by the Win32 API.
        """
        code = self.get_exception_code()
        unk = HexDump.integer(code)
        return self.__exceptionName.get(code, unk)

    def get_exception_description(self):
        """
        @rtype:  str
        @return: User-friendly name of the exception.
        """
        code = self.get_exception_code()
        description = self.__exceptionDescription.get(code, None)
        if description is None:
            try:
                description = "Exception code %s (%s)"
                description = description % (HexDump.integer(code), ctypes.FormatError(code))
            except OverflowError:
                description = "Exception code %s" % HexDump.integer(code)
        return description

    def is_first_chance(self):
        """
        @rtype:  bool
        @return: C{True} for first chance exceptions, C{False} for last chance.
        """
        return self.raw.u.Exception.dwFirstChance != 0

    def is_last_chance(self):
        """
        @rtype:  bool
        @return: The opposite of L{is_first_chance}.
        """
        return not self.is_first_chance()

    def is_noncontinuable(self):
        """
        @see: U{http://msdn.microsoft.com/en-us/library/aa363082(VS.85).aspx}

        @rtype:  bool
        @return: C{True} if the exception is noncontinuable,
            C{False} otherwise.

            Attempting to continue a noncontinuable exception results in an
            EXCEPTION_NONCONTINUABLE_EXCEPTION exception to be raised.
        """
        return bool(self.raw.u.Exception.ExceptionRecord.ExceptionFlags & win32.EXCEPTION_NONCONTINUABLE)

    def is_continuable(self):
        """
        @rtype:  bool
        @return: The opposite of L{is_noncontinuable}.
        """
        return not self.is_noncontinuable()

    def is_user_defined_exception(self):
        """
        Determines if this is an user-defined exception. User-defined
        exceptions may contain any exception code that is not system reserved.

        Often the exception code is also a valid Win32 error code, but that's
        up to the debugged application.

        @rtype:  bool
        @return: C{True} if the exception is user-defined, C{False} otherwise.
        """
        return self.get_exception_code() & 0x10000000 == 0

    def is_system_defined_exception(self):
        """
        @rtype:  bool
        @return: The opposite of L{is_user_defined_exception}.
        """
        return not self.is_user_defined_exception()

    def get_exception_code(self):
        """
        @rtype:  int
        @return: Exception code as defined by the Win32 API.
        """
        return self.raw.u.Exception.ExceptionRecord.ExceptionCode

    def get_exception_address(self):
        """
        @rtype:  int
        @return: Memory address where the exception occured.
        """
        address = self.raw.u.Exception.ExceptionRecord.ExceptionAddress
        if address is None:
            address = 0
        return address

    def get_exception_information(self, index):
        """
        @type  index: int
        @param index: Index into the exception information block.

        @rtype:  int
        @return: Exception information DWORD.
        """
        if index < 0 or index > win32.EXCEPTION_MAXIMUM_PARAMETERS:
            raise IndexError("Array index out of range: %s" % repr(index))
        info = self.raw.u.Exception.ExceptionRecord.ExceptionInformation
        value = info[index]
        if value is None:
            value = 0
        return value

    def get_exception_information_as_list(self):
        """
        @rtype:  list( int )
        @return: Exception information block.
        """
        info = self.raw.u.Exception.ExceptionRecord.ExceptionInformation
        data = list()
        for index in compat.xrange(0, win32.EXCEPTION_MAXIMUM_PARAMETERS):
            value = info[index]
            if value is None:
                value = 0
            data.append(value)
        return data

    def get_fault_type(self):
        """
        @rtype:  int
        @return: Access violation type.
            Should be one of the following constants:

             - L{win32.EXCEPTION_READ_FAULT}
             - L{win32.EXCEPTION_WRITE_FAULT}
             - L{win32.EXCEPTION_EXECUTE_FAULT}

        @note: This method is only meaningful for access violation exceptions,
            in-page memory error exceptions and guard page exceptions.

        @raise NotImplementedError: Wrong kind of exception.
        """
        if self.get_exception_code() not in (win32.EXCEPTION_ACCESS_VIOLATION, win32.EXCEPTION_IN_PAGE_ERROR, win32.EXCEPTION_GUARD_PAGE):
            msg = "This method is not meaningful for %s."
            raise NotImplementedError(msg % self.get_exception_name())
        return self.get_exception_information(0)

    def get_fault_address(self):
        """
        @rtype:  int
        @return: Access violation memory address.

        @note: This method is only meaningful for access violation exceptions,
            in-page memory error exceptions and guard page exceptions.

        @raise NotImplementedError: Wrong kind of exception.
        """
        if self.get_exception_code() not in (win32.EXCEPTION_ACCESS_VIOLATION, win32.EXCEPTION_IN_PAGE_ERROR, win32.EXCEPTION_GUARD_PAGE):
            msg = "This method is not meaningful for %s."
            raise NotImplementedError(msg % self.get_exception_name())
        return self.get_exception_information(1)

    def get_ntstatus_code(self):
        """
        @rtype:  int
        @return: NTSTATUS status code that caused the exception.

        @note: This method is only meaningful for in-page memory error
            exceptions.

        @raise NotImplementedError: Not an in-page memory error.
        """
        if self.get_exception_code() != win32.EXCEPTION_IN_PAGE_ERROR:
            msg = "This method is only meaningful " "for in-page memory error exceptions."
            raise NotImplementedError(msg)
        return self.get_exception_information(2)

    def is_nested(self):
        """
        @rtype:  bool
        @return: Returns C{True} if there are additional exception records
            associated with this exception. This would mean the exception
            is nested, that is, it was triggered while trying to handle
            at least one previous exception.
        """
        return bool(self.raw.u.Exception.ExceptionRecord.ExceptionRecord)

    def get_raw_exception_record_list(self):
        """
        Traverses the exception record linked list and builds a Python list.

        Nested exception records are received for nested exceptions. This
        happens when an exception is raised in the debugee while trying to
        handle a previous exception.

        @rtype:  list( L{win32.EXCEPTION_RECORD} )
        @return:
            List of raw exception record structures as used by the Win32 API.

            There is always at least one exception record, so the list is
            never empty. All other methods of this class read from the first
            exception record only, that is, the most recent exception.
        """
        # The first EXCEPTION_RECORD is contained in EXCEPTION_DEBUG_INFO.
        # The remaining EXCEPTION_RECORD structures are linked by pointers.
        nested = list()
        record = self.raw.u.Exception
        while True:
            record = record.ExceptionRecord
            if not record:
                break
            nested.append(record)
        return nested

    def get_nested_exceptions(self):
        """
        Traverses the exception record linked list and builds a Python list.

        Nested exception records are received for nested exceptions. This
        happens when an exception is raised in the debugee while trying to
        handle a previous exception.

        @rtype:  list( L{ExceptionEvent} )
        @return:
            List of ExceptionEvent objects representing each exception record
            found in this event.

            There is always at least one exception record, so the list is
            never empty. All other methods of this class read from the first
            exception record only, that is, the most recent exception.
        """
        # The list always begins with ourselves.
        # Just put a reference to "self" as the first element,
        # and start looping from the second exception record.
        nested = [self]
        raw = self.raw
        dwDebugEventCode = raw.dwDebugEventCode
        dwProcessId = raw.dwProcessId
        dwThreadId = raw.dwThreadId
        dwFirstChance = raw.u.Exception.dwFirstChance
        record = raw.u.Exception.ExceptionRecord
        while True:
            record = record.ExceptionRecord
            if not record:
                break
            raw = win32.DEBUG_EVENT()
            raw.dwDebugEventCode = dwDebugEventCode
            raw.dwProcessId = dwProcessId
            raw.dwThreadId = dwThreadId
            raw.u.Exception.ExceptionRecord = record
            raw.u.Exception.dwFirstChance = dwFirstChance
            event = EventFactory.get(self.debug, raw)
            nested.append(event)
        return nested


# ==============================================================================


class CreateThreadEvent(Event):
    """
    Thread creation event.
    """

    eventMethod = "create_thread"
    eventName = "Thread creation event"
    eventDescription = "A new thread has started."

    def get_thread_handle(self):
        """
        @rtype:  L{ThreadHandle}
        @return: Thread handle received from the system.
            Returns C{None} if the handle is not available.
        """
        # The handle doesn't need to be closed.
        # See http://msdn.microsoft.com/en-us/library/ms681423(VS.85).aspx
        hThread = self.raw.u.CreateThread.hThread
        if hThread in (0, win32.NULL, win32.INVALID_HANDLE_VALUE):
            hThread = None
        else:
            hThread = ThreadHandle(hThread, False, win32.THREAD_ALL_ACCESS)
        return hThread

    def get_teb(self):
        """
        @rtype:  int
        @return: Pointer to the TEB.
        """
        return self.raw.u.CreateThread.lpThreadLocalBase

    def get_start_address(self):
        """
        @rtype:  int
        @return: Pointer to the first instruction to execute in this thread.

            Returns C{NULL} when the debugger attached to a process
            and the thread already existed.

            See U{http://msdn.microsoft.com/en-us/library/ms679295(VS.85).aspx}
        """
        return self.raw.u.CreateThread.lpStartAddress


# ==============================================================================


class CreateProcessEvent(Event):
    """
    Process creation event.
    """

    eventMethod = "create_process"
    eventName = "Process creation event"
    eventDescription = "A new process has started."

    def get_file_handle(self):
        """
        @rtype:  L{FileHandle} or None
        @return: File handle to the main module, received from the system.
            Returns C{None} if the handle is not available.
        """
        # This handle DOES need to be closed.
        # Therefore we must cache it so it doesn't
        # get closed after the first call.
        try:
            hFile = self.__hFile
        except AttributeError:
            hFile = self.raw.u.CreateProcessInfo.hFile
            if hFile in (0, win32.NULL, win32.INVALID_HANDLE_VALUE):
                hFile = None
            else:
                hFile = FileHandle(hFile, True)
            self.__hFile = hFile
        return hFile

    def get_process_handle(self):
        """
        @rtype:  L{ProcessHandle}
        @return: Process handle received from the system.
            Returns C{None} if the handle is not available.
        """
        # The handle doesn't need to be closed.
        # See http://msdn.microsoft.com/en-us/library/ms681423(VS.85).aspx
        hProcess = self.raw.u.CreateProcessInfo.hProcess
        if hProcess in (0, win32.NULL, win32.INVALID_HANDLE_VALUE):
            hProcess = None
        else:
            hProcess = ProcessHandle(hProcess, False, win32.PROCESS_ALL_ACCESS)
        return hProcess

    def get_thread_handle(self):
        """
        @rtype:  L{ThreadHandle}
        @return: Thread handle received from the system.
            Returns C{None} if the handle is not available.
        """
        # The handle doesn't need to be closed.
        # See http://msdn.microsoft.com/en-us/library/ms681423(VS.85).aspx
        hThread = self.raw.u.CreateProcessInfo.hThread
        if hThread in (0, win32.NULL, win32.INVALID_HANDLE_VALUE):
            hThread = None
        else:
            hThread = ThreadHandle(hThread, False, win32.THREAD_ALL_ACCESS)
        return hThread

    def get_start_address(self):
        """
        @rtype:  int
        @return: Pointer to the first instruction to execute in this process.

            Returns C{NULL} when the debugger attaches to a process.

            See U{http://msdn.microsoft.com/en-us/library/ms679295(VS.85).aspx}
        """
        return self.raw.u.CreateProcessInfo.lpStartAddress

    def get_image_base(self):
        """
        @rtype:  int
        @return: Base address of the main module.
        @warn: This value is taken from the PE file
            and may be incorrect because of ASLR!
        """
        # TODO try to calculate the real value when ASLR is active.
        return self.raw.u.CreateProcessInfo.lpBaseOfImage

    def get_teb(self):
        """
        @rtype:  int
        @return: Pointer to the TEB.
        """
        return self.raw.u.CreateProcessInfo.lpThreadLocalBase

    def get_debug_info(self):
        """
        @rtype:  str
        @return: Debugging information.
        """
        raw = self.raw.u.CreateProcessInfo
        ptr = raw.lpBaseOfImage + raw.dwDebugInfoFileOffset
        size = raw.nDebugInfoSize
        data = self.get_process().peek(ptr, size)
        if len(data) == size:
            return data
        return None

    def get_filename(self):
        """
        @rtype:  str, None
        @return: This method does it's best to retrieve the filename to
        the main module of the process. However, sometimes that's not
        possible, and C{None} is returned instead.
        """

        # Try to get the filename from the file handle.
        szFilename = None
        hFile = self.get_file_handle()
        if hFile:
            szFilename = hFile.get_filename()
        if not szFilename:
            # Try to get it from CREATE_PROCESS_DEBUG_INFO.lpImageName
            # It's NULL or *NULL most of the times, see MSDN:
            # http://msdn.microsoft.com/en-us/library/ms679286(VS.85).aspx
            aProcess = self.get_process()
            lpRemoteFilenamePtr = self.raw.u.CreateProcessInfo.lpImageName
            if lpRemoteFilenamePtr:
                lpFilename = aProcess.peek_uint(lpRemoteFilenamePtr)
                fUnicode = bool(self.raw.u.CreateProcessInfo.fUnicode)
                szFilename = aProcess.peek_string(lpFilename, fUnicode)

                # XXX TODO
                # Sometimes the filename is relative (ntdll.dll, kernel32.dll).
                # It could be converted to an absolute pathname (SearchPath).

            # Try to get it from Process.get_image_name().
            if not szFilename:
                szFilename = aProcess.get_image_name()

        # Return the filename, or None on error.
        return szFilename

    def get_module_base(self):
        """
        @rtype:  int
        @return: Base address of the main module.
        """
        return self.get_image_base()

    def get_module(self):
        """
        @rtype:  L{Module}
        @return: Main module of the process.
        """
        return self.get_process().get_module(self.get_module_base())


# ==============================================================================


class ExitThreadEvent(Event):
    """
    Thread termination event.
    """

    eventMethod = "exit_thread"
    eventName = "Thread termination event"
    eventDescription = "A thread has finished executing."

    def get_exit_code(self):
        """
        @rtype:  int
        @return: Exit code of the thread.
        """
        return self.raw.u.ExitThread.dwExitCode


# ==============================================================================


class ExitProcessEvent(Event):
    """
    Process termination event.
    """

    eventMethod = "exit_process"
    eventName = "Process termination event"
    eventDescription = "A process has finished executing."

    def get_exit_code(self):
        """
        @rtype:  int
        @return: Exit code of the process.
        """
        return self.raw.u.ExitProcess.dwExitCode

    def get_filename(self):
        """
        @rtype:  None or str
        @return: Filename of the main module.
            C{None} if the filename is unknown.
        """
        return self.get_module().get_filename()

    def get_image_base(self):
        """
        @rtype:  int
        @return: Base address of the main module.
        """
        return self.get_module_base()

    def get_module_base(self):
        """
        @rtype:  int
        @return: Base address of the main module.
        """
        return self.get_module().get_base()

    def get_module(self):
        """
        @rtype:  L{Module}
        @return: Main module of the process.
        """
        return self.get_process().get_main_module()


# ==============================================================================


class LoadDLLEvent(Event):
    """
    Module load event.
    """

    eventMethod = "load_dll"
    eventName = "Module load event"
    eventDescription = "A new DLL library was loaded by the debugee."

    def get_module_base(self):
        """
        @rtype:  int
        @return: Base address for the newly loaded DLL.
        """
        return self.raw.u.LoadDll.lpBaseOfDll

    def get_module(self):
        """
        @rtype:  L{Module}
        @return: Module object for the newly loaded DLL.
        """
        lpBaseOfDll = self.get_module_base()
        aProcess = self.get_process()
        if aProcess.has_module(lpBaseOfDll):
            aModule = aProcess.get_module(lpBaseOfDll)
        else:
            # XXX HACK
            # For some reason the module object is missing, so make a new one.
            aModule = Module(lpBaseOfDll, hFile=self.get_file_handle(), fileName=self.get_filename(), process=aProcess)
            aProcess._add_module(aModule)
        return aModule

    def get_file_handle(self):
        """
        @rtype:  L{FileHandle} or None
        @return: File handle to the newly loaded DLL received from the system.
            Returns C{None} if the handle is not available.
        """
        # This handle DOES need to be closed.
        # Therefore we must cache it so it doesn't
        # get closed after the first call.
        try:
            hFile = self.__hFile
        except AttributeError:
            hFile = self.raw.u.LoadDll.hFile
            if hFile in (0, win32.NULL, win32.INVALID_HANDLE_VALUE):
                hFile = None
            else:
                hFile = FileHandle(hFile, True)
            self.__hFile = hFile
        return hFile

    def get_filename(self):
        """
        @rtype:  str, None
        @return: This method does it's best to retrieve the filename to
        the newly loaded module. However, sometimes that's not
        possible, and C{None} is returned instead.
        """
        szFilename = None

        # Try to get it from LOAD_DLL_DEBUG_INFO.lpImageName
        # It's NULL or *NULL most of the times, see MSDN:
        # http://msdn.microsoft.com/en-us/library/ms679286(VS.85).aspx
        aProcess = self.get_process()
        lpRemoteFilenamePtr = self.raw.u.LoadDll.lpImageName
        if lpRemoteFilenamePtr:
            lpFilename = aProcess.peek_uint(lpRemoteFilenamePtr)
            fUnicode = bool(self.raw.u.LoadDll.fUnicode)
            szFilename = aProcess.peek_string(lpFilename, fUnicode)
            if not szFilename:
                szFilename = None

        # Try to get the filename from the file handle.
        if not szFilename:
            hFile = self.get_file_handle()
            if hFile:
                szFilename = hFile.get_filename()

        # Return the filename, or None on error.
        return szFilename


# ==============================================================================


class UnloadDLLEvent(Event):
    """
    Module unload event.
    """

    eventMethod = "unload_dll"
    eventName = "Module unload event"
    eventDescription = "A DLL library was unloaded by the debugee."

    def get_module_base(self):
        """
        @rtype:  int
        @return: Base address for the recently unloaded DLL.
        """
        return self.raw.u.UnloadDll.lpBaseOfDll

    def get_module(self):
        """
        @rtype:  L{Module}
        @return: Module object for the recently unloaded DLL.
        """
        lpBaseOfDll = self.get_module_base()
        aProcess = self.get_process()
        if aProcess.has_module(lpBaseOfDll):
            aModule = aProcess.get_module(lpBaseOfDll)
        else:
            aModule = Module(lpBaseOfDll, process=aProcess)
            aProcess._add_module(aModule)
        return aModule

    def get_file_handle(self):
        """
        @rtype:  None or L{FileHandle}
        @return: File handle to the recently unloaded DLL.
            Returns C{None} if the handle is not available.
        """
        hFile = self.get_module().hFile
        if hFile in (0, win32.NULL, win32.INVALID_HANDLE_VALUE):
            hFile = None
        return hFile

    def get_filename(self):
        """
        @rtype:  None or str
        @return: Filename of the recently unloaded DLL.
            C{None} if the filename is unknown.
        """
        return self.get_module().get_filename()


# ==============================================================================


class OutputDebugStringEvent(Event):
    """
    Debug string output event.
    """

    eventMethod = "output_string"
    eventName = "Debug string output event"
    eventDescription = "The debugee sent a message to the debugger."

    def get_debug_string(self):
        """
        @rtype:  str, compat.unicode
        @return: String sent by the debugee.
            It may be ANSI or Unicode and may end with a null character.
        """
        return self.get_process().peek_string(
            self.raw.u.DebugString.lpDebugStringData, bool(self.raw.u.DebugString.fUnicode), self.raw.u.DebugString.nDebugStringLength
        )


# ==============================================================================


class RIPEvent(Event):
    """
    RIP event.
    """

    eventMethod = "rip"
    eventName = "RIP event"
    eventDescription = "An error has occured and the process " "can no longer be debugged."

    def get_rip_error(self):
        """
        @rtype:  int
        @return: RIP error code as defined by the Win32 API.
        """
        return self.raw.u.RipInfo.dwError

    def get_rip_type(self):
        """
        @rtype:  int
        @return: RIP type code as defined by the Win32 API.
            May be C{0} or one of the following:
             - L{win32.SLE_ERROR}
             - L{win32.SLE_MINORERROR}
             - L{win32.SLE_WARNING}
        """
        return self.raw.u.RipInfo.dwType


# ==============================================================================


class EventFactory(StaticClass):
    """
    Factory of L{Event} objects.

    @type baseEvent: L{Event}
    @cvar baseEvent:
        Base class for Event objects.
        It's used for unknown event codes.

    @type eventClasses: dict( int S{->} L{Event} )
    @cvar eventClasses:
        Dictionary that maps event codes to L{Event} subclasses.
    """

    baseEvent = Event
    eventClasses = {
        win32.EXCEPTION_DEBUG_EVENT: ExceptionEvent,  # 1
        win32.CREATE_THREAD_DEBUG_EVENT: CreateThreadEvent,  # 2
        win32.CREATE_PROCESS_DEBUG_EVENT: CreateProcessEvent,  # 3
        win32.EXIT_THREAD_DEBUG_EVENT: ExitThreadEvent,  # 4
        win32.EXIT_PROCESS_DEBUG_EVENT: ExitProcessEvent,  # 5
        win32.LOAD_DLL_DEBUG_EVENT: LoadDLLEvent,  # 6
        win32.UNLOAD_DLL_DEBUG_EVENT: UnloadDLLEvent,  # 7
        win32.OUTPUT_DEBUG_STRING_EVENT: OutputDebugStringEvent,  # 8
        win32.RIP_EVENT: RIPEvent,  # 9
    }

    @classmethod
    def get(cls, debug, raw):
        """
        @type  debug: L{Debug}
        @param debug: Debug object that received the event.

        @type  raw: L{DEBUG_EVENT}
        @param raw: Raw DEBUG_EVENT structure as used by the Win32 API.

        @rtype: L{Event}
        @returns: An Event object or one of it's subclasses,
            depending on the event type.
        """
        eventClass = cls.eventClasses.get(raw.dwDebugEventCode, cls.baseEvent)
        return eventClass(debug, raw)


# ==============================================================================


class EventHandler(object):
    """
    Base class for debug event handlers.

    Your program should subclass it to implement it's own event handling.

    The constructor can be overriden as long as you call the superclass
    constructor. The special method L{__call__} B{MUST NOT} be overriden.

    The signature for event handlers is the following::

        def event_handler(self, event):

    Where B{event} is an L{Event} object.

    Each event handler is named after the event they handle.
    This is the list of all valid event handler names:

     - I{event}

       Receives an L{Event} object or an object of any of it's subclasses,
       and handles any event for which no handler was defined.

     - I{unknown_event}

       Receives an L{Event} object or an object of any of it's subclasses,
       and handles any event unknown to the debugging engine. (This is not
       likely to happen unless the Win32 debugging API is changed in future
       versions of Windows).

     - I{exception}

       Receives an L{ExceptionEvent} object and handles any exception for
       which no handler was defined. See above for exception handlers.

     - I{unknown_exception}

       Receives an L{ExceptionEvent} object and handles any exception unknown
       to the debugging engine. This usually happens for C++ exceptions, which
       are not standardized and may change from one compiler to the next.

       Currently we have partial support for C++ exceptions thrown by Microsoft
       compilers.

       Also see: U{RaiseException()
       <http://msdn.microsoft.com/en-us/library/ms680552(VS.85).aspx>}

     - I{create_thread}

       Receives a L{CreateThreadEvent} object.

     - I{create_process}

       Receives a L{CreateProcessEvent} object.

     - I{exit_thread}

       Receives a L{ExitThreadEvent} object.

     - I{exit_process}

       Receives a L{ExitProcessEvent} object.

     - I{load_dll}

       Receives a L{LoadDLLEvent} object.

     - I{unload_dll}

       Receives an L{UnloadDLLEvent} object.

     - I{output_string}

       Receives an L{OutputDebugStringEvent} object.

     - I{rip}

       Receives a L{RIPEvent} object.

    This is the list of all valid exception handler names
    (they all receive an L{ExceptionEvent} object):

     - I{access_violation}
     - I{array_bounds_exceeded}
     - I{breakpoint}
     - I{control_c_exit}
     - I{datatype_misalignment}
     - I{debug_control_c}
     - I{float_denormal_operand}
     - I{float_divide_by_zero}
     - I{float_inexact_result}
     - I{float_invalid_operation}
     - I{float_overflow}
     - I{float_stack_check}
     - I{float_underflow}
     - I{guard_page}
     - I{illegal_instruction}
     - I{in_page_error}
     - I{integer_divide_by_zero}
     - I{integer_overflow}
     - I{invalid_disposition}
     - I{invalid_handle}
     - I{ms_vc_exception}
     - I{noncontinuable_exception}
     - I{possible_deadlock}
     - I{privileged_instruction}
     - I{single_step}
     - I{stack_overflow}
     - I{wow64_breakpoint}



    @type apiHooks: dict( str S{->} list( tuple( str, int ) ) )
    @cvar apiHooks:
        Dictionary that maps module names to lists of
        tuples of ( procedure name, parameter count ).

        All procedures listed here will be hooked for calls from the debugee.
        When this happens, the corresponding event handler can be notified both
        when the procedure is entered and when it's left by the debugee.

        For example, let's hook the LoadLibraryEx() API call.
        This would be the declaration of apiHooks::

            from winappdbg import EventHandler
            from winappdbg.win32 import *

            # (...)

            class MyEventHandler (EventHandler):

                apiHook = {

                    "kernel32.dll" : (

                        #   Procedure name      Signature
                        (   "LoadLibraryEx",    (PVOID, HANDLE, DWORD) ),

                        # (more procedures can go here...)
                    ),

                    # (more libraries can go here...)
                }

                # (your method definitions go here...)

        Note that all pointer types are treated like void pointers, so your
        callback won't get the string or structure pointed to by it, but the
        remote memory address instead. This is so to prevent the ctypes library
        from being "too helpful" and trying to dereference the pointer. To get
        the actual data being pointed to, use one of the L{Process.read}
        methods.

        Now, to intercept calls to LoadLibraryEx define a method like this in
        your event handler class::

            def pre_LoadLibraryEx(self, event, ra, lpFilename, hFile, dwFlags):
                szFilename = event.get_process().peek_string(lpFilename)

                # (...)

        Note that the first parameter is always the L{Event} object, and the
        second parameter is the return address. The third parameter and above
        are the values passed to the hooked function.

        Finally, to intercept returns from calls to LoadLibraryEx define a
        method like this::

            def post_LoadLibraryEx(self, event, retval):
                # (...)

        The first parameter is the L{Event} object and the second is the
        return value from the hooked function.
    """

    # ------------------------------------------------------------------------------

    # Default (empty) API hooks dictionary.
    apiHooks = {}

    def __init__(self):
        """
        Class constructor. Don't forget to call it when subclassing!

        Forgetting to call the superclass constructor is a common mistake when
        you're new to Python. :)

        Example::
            class MyEventHandler (EventHandler):

                # Override the constructor to use an extra argument.
                def __init__(self, myArgument):

                    # Do something with the argument, like keeping it
                    # as an instance variable.
                    self.myVariable = myArgument

                    # Call the superclass constructor.
                    super(MyEventHandler, self).__init__()

                # The rest of your code below...
        """

        # TODO
        # All this does is set up the hooks.
        # This code should be moved to the EventDispatcher class.
        # Then the hooks can be set up at set_event_handler() instead, making
        # this class even simpler. The downside here is deciding where to store
        # the ApiHook objects.

        # Convert the tuples into instances of the ApiHook class.
        # A new dictionary must be instanced, otherwise we could also be
        #  affecting all other instances of the EventHandler.
        apiHooks = dict()
        for lib, hooks in compat.iteritems(self.apiHooks):
            hook_objs = []
            for proc, args in hooks:
                if type(args) in (int, long):
                    h = ApiHook(self, lib, proc, paramCount=args)
                else:
                    h = ApiHook(self, lib, proc, signature=args)
                hook_objs.append(h)
            apiHooks[lib] = hook_objs
        self.__apiHooks = apiHooks

    def __get_hooks_for_dll(self, event):
        """
        Get the requested API hooks for the current DLL.

        Used by L{__hook_dll} and L{__unhook_dll}.
        """
        result = []
        if self.__apiHooks:
            path = event.get_module().get_filename()
            if path:
                lib_name = PathOperations.pathname_to_filename(path).lower()
                for hook_lib, hook_api_list in compat.iteritems(self.__apiHooks):
                    if hook_lib == lib_name:
                        result.extend(hook_api_list)
        return result

    def __hook_dll(self, event):
        """
        Hook the requested API calls (in self.apiHooks).

        This method is called automatically whenever a DLL is loaded.
        """
        debug = event.debug
        pid = event.get_pid()
        for hook_api_stub in self.__get_hooks_for_dll(event):
            hook_api_stub.hook(debug, pid)

    def __unhook_dll(self, event):
        """
        Unhook the requested API calls (in self.apiHooks).

        This method is called automatically whenever a DLL is unloaded.
        """
        debug = event.debug
        pid = event.get_pid()
        for hook_api_stub in self.__get_hooks_for_dll(event):
            hook_api_stub.unhook(debug, pid)

    def __call__(self, event):
        """
        Dispatch debug events.

        @warn: B{Don't override this method!}

        @type  event: L{Event}
        @param event: Event object.
        """
        try:
            code = event.get_event_code()
            if code == win32.LOAD_DLL_DEBUG_EVENT:
                self.__hook_dll(event)
            elif code == win32.UNLOAD_DLL_DEBUG_EVENT:
                self.__unhook_dll(event)
        finally:
            method = EventDispatcher.get_handler_method(self, event)
            if method is not None:
                return method(event)


# ==============================================================================

# TODO
#  * Make it more generic by adding a few more callbacks.
#    That way it will be possible to make a thread sifter too.
#  * This interface feels too much like an antipattern.
#    When apiHooks is deprecated this will have to be reviewed.


class EventSift(EventHandler):
    """
    Event handler that allows you to use customized event handlers for each
    process you're attached to.

    This makes coding the event handlers much easier, because each instance
    will only "know" about one process. So you can code your event handler as
    if only one process was being debugged, but your debugger can attach to
    multiple processes.

    Example::
        from winappdbg import Debug, EventHandler, EventSift

        # This class was written assuming only one process is attached.
        # If you used it directly it would break when attaching to another
        # process, or when a child process is spawned.
        class MyEventHandler (EventHandler):

            def create_process(self, event):
                self.first = True
                self.name = event.get_process().get_filename()
                print "Attached to %s" % self.name

            def breakpoint(self, event):
                if self.first:
                    self.first = False
                    print "First breakpoint reached at %s" % self.name

            def exit_process(self, event):
                print "Detached from %s" % self.name

        # Now when debugging we use the EventSift to be able to work with
        # multiple processes while keeping our code simple. :)
        if __name__ == "__main__":
            handler = EventSift(MyEventHandler)
            #handler = MyEventHandler()  # try uncommenting this line...
            with Debug(handler) as debug:
                debug.execl("calc.exe")
                debug.execl("notepad.exe")
                debug.execl("charmap.exe")
                debug.loop()

    Subclasses of C{EventSift} can prevent specific event types from
    being forwarded by simply defining a method for it. That means your
    subclass can handle some event types globally while letting other types
    be handled on per-process basis. To forward events manually you can
    call C{self.event(event)}.

    Example::
        class MySift (EventSift):

            # Don't forward this event.
            def debug_control_c(self, event):
                pass

            # Handle this event globally without forwarding it.
            def output_string(self, event):
                print "Debug string: %s" % event.get_debug_string()

            # Handle this event globally and then forward it.
            def create_process(self, event):
                print "New process created, PID: %d" % event.get_pid()
                return self.event(event)

            # All other events will be forwarded.

    Note that overriding the C{event} method would cause no events to be
    forwarded at all. To prevent this, call the superclass implementation.

    Example::

        def we_want_to_forward_this_event(event):
            "Use whatever logic you want here..."
            # (...return True or False...)

        class MySift (EventSift):

            def event(self, event):

                # If the event matches some custom criteria...
                if we_want_to_forward_this_event(event):

                    # Forward it.
                    return super(MySift, self).event(event)

                # Otherwise, don't.

    @type cls: class
    @ivar cls:
        Event handler class. There will be one instance of this class
        per debugged process in the L{forward} dictionary.

    @type argv: list
    @ivar argv:
        Positional arguments to pass to the constructor of L{cls}.

    @type argd: list
    @ivar argd:
        Keyword arguments to pass to the constructor of L{cls}.

    @type forward: dict
    @ivar forward:
        Dictionary that maps each debugged process ID to an instance of L{cls}.
    """

    def __init__(self, cls, *argv, **argd):
        """
        Maintains an instance of your event handler for each process being
        debugged, and forwards the events of each process to each corresponding
        instance.

        @warn: If you subclass L{EventSift} and reimplement this method,
            don't forget to call the superclass constructor!

        @see: L{event}

        @type  cls: class
        @param cls: Event handler class. This must be the class itself, not an
            instance! All additional arguments passed to the constructor of
            the event forwarder will be passed on to the constructor of this
            class as well.
        """
        self.cls = cls
        self.argv = argv
        self.argd = argd
        self.forward = dict()
        super(EventSift, self).__init__()

    # XXX HORRIBLE HACK
    # This makes apiHooks work in the inner handlers.
    def __call__(self, event):
        try:
            eventCode = event.get_event_code()
            if eventCode in (win32.LOAD_DLL_DEBUG_EVENT, win32.LOAD_DLL_DEBUG_EVENT):
                pid = event.get_pid()
                handler = self.forward.get(pid, None)
                if handler is None:
                    handler = self.cls(*self.argv, **self.argd)
                self.forward[pid] = handler
                if isinstance(handler, EventHandler):
                    if eventCode == win32.LOAD_DLL_DEBUG_EVENT:
                        handler.__EventHandler_hook_dll(event)
                    else:
                        handler.__EventHandler_unhook_dll(event)
        finally:
            return super(EventSift, self).__call__(event)

    def event(self, event):
        """
        Forwards events to the corresponding instance of your event handler
        for this process.

        If you subclass L{EventSift} and reimplement this method, no event
        will be forwarded at all unless you call the superclass implementation.

        If your filtering is based on the event type, there's a much easier way
        to do it: just implement a handler for it.
        """
        eventCode = event.get_event_code()
        pid = event.get_pid()
        handler = self.forward.get(pid, None)
        if handler is None:
            handler = self.cls(*self.argv, **self.argd)
            if eventCode != win32.EXIT_PROCESS_DEBUG_EVENT:
                self.forward[pid] = handler
        elif eventCode == win32.EXIT_PROCESS_DEBUG_EVENT:
            del self.forward[pid]
        return handler(event)


# ==============================================================================


class EventDispatcher(object):
    """
    Implements debug event dispatching capabilities.

    @group Debugging events:
        get_event_handler, set_event_handler, get_handler_method
    """

    # Maps event code constants to the names of the pre-notify routines.
    # These routines are called BEFORE the user-defined handlers.
    # Unknown codes are ignored.
    __preEventNotifyCallbackName = {
        win32.CREATE_THREAD_DEBUG_EVENT: "_notify_create_thread",
        win32.CREATE_PROCESS_DEBUG_EVENT: "_notify_create_process",
        win32.LOAD_DLL_DEBUG_EVENT: "_notify_load_dll",
    }

    # Maps event code constants to the names of the post-notify routines.
    # These routines are called AFTER the user-defined handlers.
    # Unknown codes are ignored.
    __postEventNotifyCallbackName = {
        win32.EXIT_THREAD_DEBUG_EVENT: "_notify_exit_thread",
        win32.EXIT_PROCESS_DEBUG_EVENT: "_notify_exit_process",
        win32.UNLOAD_DLL_DEBUG_EVENT: "_notify_unload_dll",
        win32.RIP_EVENT: "_notify_rip",
    }

    # Maps exception code constants to the names of the pre-notify routines.
    # These routines are called BEFORE the user-defined handlers.
    # Unknown codes are ignored.
    __preExceptionNotifyCallbackName = {
        win32.EXCEPTION_BREAKPOINT: "_notify_breakpoint",
        win32.EXCEPTION_WX86_BREAKPOINT: "_notify_breakpoint",
        win32.EXCEPTION_SINGLE_STEP: "_notify_single_step",
        win32.EXCEPTION_GUARD_PAGE: "_notify_guard_page",
        win32.DBG_CONTROL_C: "_notify_debug_control_c",
        win32.MS_VC_EXCEPTION: "_notify_ms_vc_exception",
    }

    # Maps exception code constants to the names of the post-notify routines.
    # These routines are called AFTER the user-defined handlers.
    # Unknown codes are ignored.
    __postExceptionNotifyCallbackName = {}

    def __init__(self, eventHandler=None):
        """
        Event dispatcher.

        @type  eventHandler: L{EventHandler}
        @param eventHandler: (Optional) User-defined event handler.

        @raise TypeError: The event handler is of an incorrect type.

        @note: The L{eventHandler} parameter may be any callable Python object
            (for example a function, or an instance method).
            However you'll probably find it more convenient to use an instance
            of a subclass of L{EventHandler} here.
        """
        self.set_event_handler(eventHandler)

    def get_event_handler(self):
        """
        Get the event handler.

        @see: L{set_event_handler}

        @rtype:  L{EventHandler}
        @return: Current event handler object, or C{None}.
        """
        return self.__eventHandler

    def set_event_handler(self, eventHandler):
        """
        Set the event handler.

        @warn: This is normally not needed. Use with care!

        @type  eventHandler: L{EventHandler}
        @param eventHandler: New event handler object, or C{None}.

        @rtype:  L{EventHandler}
        @return: Previous event handler object, or C{None}.

        @raise TypeError: The event handler is of an incorrect type.

        @note: The L{eventHandler} parameter may be any callable Python object
            (for example a function, or an instance method).
            However you'll probably find it more convenient to use an instance
            of a subclass of L{EventHandler} here.
        """
        if eventHandler is not None and not callable(eventHandler):
            raise TypeError("Event handler must be a callable object")
        try:
            wrong_type = issubclass(eventHandler, EventHandler)
        except TypeError:
            wrong_type = False
        if wrong_type:
            classname = str(eventHandler)
            msg = "Event handler must be an instance of class %s"
            msg += "rather than the %s class itself. (Missing parens?)"
            msg = msg % (classname, classname)
            raise TypeError(msg)
        try:
            previous = self.__eventHandler
        except AttributeError:
            previous = None
        self.__eventHandler = eventHandler
        return previous

    @staticmethod
    def get_handler_method(eventHandler, event, fallback=None):
        """
        Retrieves the appropriate callback method from an L{EventHandler}
        instance for the given L{Event} object.

        @type  eventHandler: L{EventHandler}
        @param eventHandler:
            Event handler object whose methods we are examining.

        @type  event: L{Event}
        @param event: Debugging event to be handled.

        @type  fallback: callable
        @param fallback: (Optional) If no suitable method is found in the
            L{EventHandler} instance, return this value.

        @rtype:  callable
        @return: Bound method that will handle the debugging event.
            Returns C{None} if no such method is defined.
        """
        eventCode = event.get_event_code()
        method = getattr(eventHandler, "event", fallback)
        if eventCode == win32.EXCEPTION_DEBUG_EVENT:
            method = getattr(eventHandler, "exception", method)
        method = getattr(eventHandler, event.eventMethod, method)
        return method

    def dispatch(self, event):
        """
        Sends event notifications to the L{Debug} object and
        the L{EventHandler} object provided by the user.

        The L{Debug} object will forward the notifications to it's contained
        snapshot objects (L{System}, L{Process}, L{Thread} and L{Module}) when
        appropriate.

        @warning: This method is called automatically from L{Debug.dispatch}.

        @see: L{Debug.cont}, L{Debug.loop}, L{Debug.wait}

        @type  event: L{Event}
        @param event: Event object passed to L{Debug.dispatch}.

        @raise WindowsError: Raises an exception on error.
        """
        returnValue = None
        bCallHandler = True
        pre_handler = None
        post_handler = None
        eventCode = event.get_event_code()

        # Get the pre and post notification methods for exceptions.
        # If not found, the following steps take care of that.
        if eventCode == win32.EXCEPTION_DEBUG_EVENT:
            exceptionCode = event.get_exception_code()
            pre_name = self.__preExceptionNotifyCallbackName.get(exceptionCode, None)
            post_name = self.__postExceptionNotifyCallbackName.get(exceptionCode, None)
            if pre_name is not None:
                pre_handler = getattr(self, pre_name, None)
            if post_name is not None:
                post_handler = getattr(self, post_name, None)

        # Get the pre notification method for all other events.
        # This includes the exception event if no notify method was found
        # for this exception code.
        if pre_handler is None:
            pre_name = self.__preEventNotifyCallbackName.get(eventCode, None)
            if pre_name is not None:
                pre_handler = getattr(self, pre_name, pre_handler)

        # Get the post notification method for all other events.
        # This includes the exception event if no notify method was found
        # for this exception code.
        if post_handler is None:
            post_name = self.__postEventNotifyCallbackName.get(eventCode, None)
            if post_name is not None:
                post_handler = getattr(self, post_name, post_handler)

        # Call the pre-notify method only if it was defined.
        # If an exception is raised don't call the other methods.
        if pre_handler is not None:
            bCallHandler = pre_handler(event)

        # Call the user-defined event handler only if the pre-notify
        #  method was not defined, or was and it returned True.
        try:
            if bCallHandler and self.__eventHandler is not None:
                try:
                    returnValue = self.__eventHandler(event)
                except Exception:
                    e = sys.exc_info()[1]
                    msg = "Event handler pre-callback %r" " raised an exception: %s"
                    msg = msg % (self.__eventHandler, traceback.format_exc(e))
                    warnings.warn(msg, EventCallbackWarning)
                    returnValue = None

        # Call the post-notify method if defined, even if an exception is
        #  raised by the user-defined event handler.
        finally:
            if post_handler is not None:
                post_handler(event)

        # Return the value from the call to the user-defined event handler.
        # If not defined return None.
        return returnValue

# === NexusCore/openenv\Lib\site-packages\jinja2\filters.py ===
"""Built-in template filters used with the ``|`` operator."""

import math
import random
import re
import typing
import typing as t
from collections import abc
from inspect import getattr_static
from itertools import chain
from itertools import groupby

from markupsafe import escape
from markupsafe import Markup
from markupsafe import soft_str

from .async_utils import async_variant
from .async_utils import auto_aiter
from .async_utils import auto_await
from .async_utils import auto_to_list
from .exceptions import FilterArgumentError
from .runtime import Undefined
from .utils import htmlsafe_json_dumps
from .utils import pass_context
from .utils import pass_environment
from .utils import pass_eval_context
from .utils import pformat
from .utils import url_quote
from .utils import urlize

if t.TYPE_CHECKING:
    import typing_extensions as te

    from .environment import Environment
    from .nodes import EvalContext
    from .runtime import Context
    from .sandbox import SandboxedEnvironment  # noqa: F401

    class HasHTML(te.Protocol):
        def __html__(self) -> str:
            pass


F = t.TypeVar("F", bound=t.Callable[..., t.Any])
K = t.TypeVar("K")
V = t.TypeVar("V")


def ignore_case(value: V) -> V:
    """For use as a postprocessor for :func:`make_attrgetter`. Converts strings
    to lowercase and returns other types as-is."""
    if isinstance(value, str):
        return t.cast(V, value.lower())

    return value


def make_attrgetter(
    environment: "Environment",
    attribute: t.Optional[t.Union[str, int]],
    postprocess: t.Optional[t.Callable[[t.Any], t.Any]] = None,
    default: t.Optional[t.Any] = None,
) -> t.Callable[[t.Any], t.Any]:
    """Returns a callable that looks up the given attribute from a
    passed object with the rules of the environment.  Dots are allowed
    to access attributes of attributes.  Integer parts in paths are
    looked up as integers.
    """
    parts = _prepare_attribute_parts(attribute)

    def attrgetter(item: t.Any) -> t.Any:
        for part in parts:
            item = environment.getitem(item, part)

            if default is not None and isinstance(item, Undefined):
                item = default

        if postprocess is not None:
            item = postprocess(item)

        return item

    return attrgetter


def make_multi_attrgetter(
    environment: "Environment",
    attribute: t.Optional[t.Union[str, int]],
    postprocess: t.Optional[t.Callable[[t.Any], t.Any]] = None,
) -> t.Callable[[t.Any], t.List[t.Any]]:
    """Returns a callable that looks up the given comma separated
    attributes from a passed object with the rules of the environment.
    Dots are allowed to access attributes of each attribute.  Integer
    parts in paths are looked up as integers.

    The value returned by the returned callable is a list of extracted
    attribute values.

    Examples of attribute: "attr1,attr2", "attr1.inner1.0,attr2.inner2.0", etc.
    """
    if isinstance(attribute, str):
        split: t.Sequence[t.Union[str, int, None]] = attribute.split(",")
    else:
        split = [attribute]

    parts = [_prepare_attribute_parts(item) for item in split]

    def attrgetter(item: t.Any) -> t.List[t.Any]:
        items = [None] * len(parts)

        for i, attribute_part in enumerate(parts):
            item_i = item

            for part in attribute_part:
                item_i = environment.getitem(item_i, part)

            if postprocess is not None:
                item_i = postprocess(item_i)

            items[i] = item_i

        return items

    return attrgetter


def _prepare_attribute_parts(
    attr: t.Optional[t.Union[str, int]],
) -> t.List[t.Union[str, int]]:
    if attr is None:
        return []

    if isinstance(attr, str):
        return [int(x) if x.isdigit() else x for x in attr.split(".")]

    return [attr]


def do_forceescape(value: "t.Union[str, HasHTML]") -> Markup:
    """Enforce HTML escaping.  This will probably double escape variables."""
    if hasattr(value, "__html__"):
        value = t.cast("HasHTML", value).__html__()

    return escape(str(value))


def do_urlencode(
    value: t.Union[str, t.Mapping[str, t.Any], t.Iterable[t.Tuple[str, t.Any]]],
) -> str:
    """Quote data for use in a URL path or query using UTF-8.

    Basic wrapper around :func:`urllib.parse.quote` when given a
    string, or :func:`urllib.parse.urlencode` for a dict or iterable.

    :param value: Data to quote. A string will be quoted directly. A
        dict or iterable of ``(key, value)`` pairs will be joined as a
        query string.

    When given a string, "/" is not quoted. HTTP servers treat "/" and
    "%2F" equivalently in paths. If you need quoted slashes, use the
    ``|replace("/", "%2F")`` filter.

    .. versionadded:: 2.7
    """
    if isinstance(value, str) or not isinstance(value, abc.Iterable):
        return url_quote(value)

    if isinstance(value, dict):
        items: t.Iterable[t.Tuple[str, t.Any]] = value.items()
    else:
        items = value  # type: ignore

    return "&".join(
        f"{url_quote(k, for_qs=True)}={url_quote(v, for_qs=True)}" for k, v in items
    )


@pass_eval_context
def do_replace(
    eval_ctx: "EvalContext", s: str, old: str, new: str, count: t.Optional[int] = None
) -> str:
    """Return a copy of the value with all occurrences of a substring
    replaced with a new one. The first argument is the substring
    that should be replaced, the second is the replacement string.
    If the optional third argument ``count`` is given, only the first
    ``count`` occurrences are replaced:

    .. sourcecode:: jinja

        {{ "Hello World"|replace("Hello", "Goodbye") }}
            -> Goodbye World

        {{ "aaaaargh"|replace("a", "d'oh, ", 2) }}
            -> d'oh, d'oh, aaargh
    """
    if count is None:
        count = -1

    if not eval_ctx.autoescape:
        return str(s).replace(str(old), str(new), count)

    if (
        hasattr(old, "__html__")
        or hasattr(new, "__html__")
        and not hasattr(s, "__html__")
    ):
        s = escape(s)
    else:
        s = soft_str(s)

    return s.replace(soft_str(old), soft_str(new), count)


def do_upper(s: str) -> str:
    """Convert a value to uppercase."""
    return soft_str(s).upper()


def do_lower(s: str) -> str:
    """Convert a value to lowercase."""
    return soft_str(s).lower()


def do_items(value: t.Union[t.Mapping[K, V], Undefined]) -> t.Iterator[t.Tuple[K, V]]:
    """Return an iterator over the ``(key, value)`` items of a mapping.

    ``x|items`` is the same as ``x.items()``, except if ``x`` is
    undefined an empty iterator is returned.

    This filter is useful if you expect the template to be rendered with
    an implementation of Jinja in another programming language that does
    not have a ``.items()`` method on its mapping type.

    .. code-block:: html+jinja

        <dl>
        {% for key, value in my_dict|items %}
            <dt>{{ key }}
            <dd>{{ value }}
        {% endfor %}
        </dl>

    .. versionadded:: 3.1
    """
    if isinstance(value, Undefined):
        return

    if not isinstance(value, abc.Mapping):
        raise TypeError("Can only get item pairs from a mapping.")

    yield from value.items()


# Check for characters that would move the parser state from key to value.
# https://html.spec.whatwg.org/#attribute-name-state
_attr_key_re = re.compile(r"[\s/>=]", flags=re.ASCII)


@pass_eval_context
def do_xmlattr(
    eval_ctx: "EvalContext", d: t.Mapping[str, t.Any], autospace: bool = True
) -> str:
    """Create an SGML/XML attribute string based on the items in a dict.

    **Values** that are neither ``none`` nor ``undefined`` are automatically
    escaped, safely allowing untrusted user input.

    User input should not be used as **keys** to this filter. If any key
    contains a space, ``/`` solidus, ``>`` greater-than sign, or ``=`` equals
    sign, this fails with a ``ValueError``. Regardless of this, user input
    should never be used as keys to this filter, or must be separately validated
    first.

    .. sourcecode:: html+jinja

        <ul{{ {'class': 'my_list', 'missing': none,
                'id': 'list-%d'|format(variable)}|xmlattr }}>
        ...
        </ul>

    Results in something like this:

    .. sourcecode:: html

        <ul class="my_list" id="list-42">
        ...
        </ul>

    As you can see it automatically prepends a space in front of the item
    if the filter returned something unless the second parameter is false.

    .. versionchanged:: 3.1.4
        Keys with ``/`` solidus, ``>`` greater-than sign, or ``=`` equals sign
        are not allowed.

    .. versionchanged:: 3.1.3
        Keys with spaces are not allowed.
    """
    items = []

    for key, value in d.items():
        if value is None or isinstance(value, Undefined):
            continue

        if _attr_key_re.search(key) is not None:
            raise ValueError(f"Invalid character in attribute name: {key!r}")

        items.append(f'{escape(key)}="{escape(value)}"')

    rv = " ".join(items)

    if autospace and rv:
        rv = " " + rv

    if eval_ctx.autoescape:
        rv = Markup(rv)

    return rv


def do_capitalize(s: str) -> str:
    """Capitalize a value. The first character will be uppercase, all others
    lowercase.
    """
    return soft_str(s).capitalize()


_word_beginning_split_re = re.compile(r"([-\s({\[<]+)")


def do_title(s: str) -> str:
    """Return a titlecased version of the value. I.e. words will start with
    uppercase letters, all remaining characters are lowercase.
    """
    return "".join(
        [
            item[0].upper() + item[1:].lower()
            for item in _word_beginning_split_re.split(soft_str(s))
            if item
        ]
    )


def do_dictsort(
    value: t.Mapping[K, V],
    case_sensitive: bool = False,
    by: 'te.Literal["key", "value"]' = "key",
    reverse: bool = False,
) -> t.List[t.Tuple[K, V]]:
    """Sort a dict and yield (key, value) pairs. Python dicts may not
    be in the order you want to display them in, so sort them first.

    .. sourcecode:: jinja

        {% for key, value in mydict|dictsort %}
            sort the dict by key, case insensitive

        {% for key, value in mydict|dictsort(reverse=true) %}
            sort the dict by key, case insensitive, reverse order

        {% for key, value in mydict|dictsort(true) %}
            sort the dict by key, case sensitive

        {% for key, value in mydict|dictsort(false, 'value') %}
            sort the dict by value, case insensitive
    """
    if by == "key":
        pos = 0
    elif by == "value":
        pos = 1
    else:
        raise FilterArgumentError('You can only sort by either "key" or "value"')

    def sort_func(item: t.Tuple[t.Any, t.Any]) -> t.Any:
        value = item[pos]

        if not case_sensitive:
            value = ignore_case(value)

        return value

    return sorted(value.items(), key=sort_func, reverse=reverse)


@pass_environment
def do_sort(
    environment: "Environment",
    value: "t.Iterable[V]",
    reverse: bool = False,
    case_sensitive: bool = False,
    attribute: t.Optional[t.Union[str, int]] = None,
) -> "t.List[V]":
    """Sort an iterable using Python's :func:`sorted`.

    .. sourcecode:: jinja

        {% for city in cities|sort %}
            ...
        {% endfor %}

    :param reverse: Sort descending instead of ascending.
    :param case_sensitive: When sorting strings, sort upper and lower
        case separately.
    :param attribute: When sorting objects or dicts, an attribute or
        key to sort by. Can use dot notation like ``"address.city"``.
        Can be a list of attributes like ``"age,name"``.

    The sort is stable, it does not change the relative order of
    elements that compare equal. This makes it is possible to chain
    sorts on different attributes and ordering.

    .. sourcecode:: jinja

        {% for user in users|sort(attribute="name")
            |sort(reverse=true, attribute="age") %}
            ...
        {% endfor %}

    As a shortcut to chaining when the direction is the same for all
    attributes, pass a comma separate list of attributes.

    .. sourcecode:: jinja

        {% for user in users|sort(attribute="age,name") %}
            ...
        {% endfor %}

    .. versionchanged:: 2.11.0
        The ``attribute`` parameter can be a comma separated list of
        attributes, e.g. ``"age,name"``.

    .. versionchanged:: 2.6
       The ``attribute`` parameter was added.
    """
    key_func = make_multi_attrgetter(
        environment, attribute, postprocess=ignore_case if not case_sensitive else None
    )
    return sorted(value, key=key_func, reverse=reverse)


@pass_environment
def sync_do_unique(
    environment: "Environment",
    value: "t.Iterable[V]",
    case_sensitive: bool = False,
    attribute: t.Optional[t.Union[str, int]] = None,
) -> "t.Iterator[V]":
    """Returns a list of unique items from the given iterable.

    .. sourcecode:: jinja

        {{ ['foo', 'bar', 'foobar', 'FooBar']|unique|list }}
            -> ['foo', 'bar', 'foobar']

    The unique items are yielded in the same order as their first occurrence in
    the iterable passed to the filter.

    :param case_sensitive: Treat upper and lower case strings as distinct.
    :param attribute: Filter objects with unique values for this attribute.
    """
    getter = make_attrgetter(
        environment, attribute, postprocess=ignore_case if not case_sensitive else None
    )
    seen = set()

    for item in value:
        key = getter(item)

        if key not in seen:
            seen.add(key)
            yield item


@async_variant(sync_do_unique)  # type: ignore
async def do_unique(
    environment: "Environment",
    value: "t.Union[t.AsyncIterable[V], t.Iterable[V]]",
    case_sensitive: bool = False,
    attribute: t.Optional[t.Union[str, int]] = None,
) -> "t.Iterator[V]":
    return sync_do_unique(
        environment, await auto_to_list(value), case_sensitive, attribute
    )


def _min_or_max(
    environment: "Environment",
    value: "t.Iterable[V]",
    func: "t.Callable[..., V]",
    case_sensitive: bool,
    attribute: t.Optional[t.Union[str, int]],
) -> "t.Union[V, Undefined]":
    it = iter(value)

    try:
        first = next(it)
    except StopIteration:
        return environment.undefined("No aggregated item, sequence was empty.")

    key_func = make_attrgetter(
        environment, attribute, postprocess=ignore_case if not case_sensitive else None
    )
    return func(chain([first], it), key=key_func)


@pass_environment
def do_min(
    environment: "Environment",
    value: "t.Iterable[V]",
    case_sensitive: bool = False,
    attribute: t.Optional[t.Union[str, int]] = None,
) -> "t.Union[V, Undefined]":
    """Return the smallest item from the sequence.

    .. sourcecode:: jinja

        {{ [1, 2, 3]|min }}
            -> 1

    :param case_sensitive: Treat upper and lower case strings as distinct.
    :param attribute: Get the object with the min value of this attribute.
    """
    return _min_or_max(environment, value, min, case_sensitive, attribute)


@pass_environment
def do_max(
    environment: "Environment",
    value: "t.Iterable[V]",
    case_sensitive: bool = False,
    attribute: t.Optional[t.Union[str, int]] = None,
) -> "t.Union[V, Undefined]":
    """Return the largest item from the sequence.

    .. sourcecode:: jinja

        {{ [1, 2, 3]|max }}
            -> 3

    :param case_sensitive: Treat upper and lower case strings as distinct.
    :param attribute: Get the object with the max value of this attribute.
    """
    return _min_or_max(environment, value, max, case_sensitive, attribute)


def do_default(
    value: V,
    default_value: V = "",  # type: ignore
    boolean: bool = False,
) -> V:
    """If the value is undefined it will return the passed default value,
    otherwise the value of the variable:

    .. sourcecode:: jinja

        {{ my_variable|default('my_variable is not defined') }}

    This will output the value of ``my_variable`` if the variable was
    defined, otherwise ``'my_variable is not defined'``. If you want
    to use default with variables that evaluate to false you have to
    set the second parameter to `true`:

    .. sourcecode:: jinja

        {{ ''|default('the string was empty', true) }}

    .. versionchanged:: 2.11
       It's now possible to configure the :class:`~jinja2.Environment` with
       :class:`~jinja2.ChainableUndefined` to make the `default` filter work
       on nested elements and attributes that may contain undefined values
       in the chain without getting an :exc:`~jinja2.UndefinedError`.
    """
    if isinstance(value, Undefined) or (boolean and not value):
        return default_value

    return value


@pass_eval_context
def sync_do_join(
    eval_ctx: "EvalContext",
    value: t.Iterable[t.Any],
    d: str = "",
    attribute: t.Optional[t.Union[str, int]] = None,
) -> str:
    """Return a string which is the concatenation of the strings in the
    sequence. The separator between elements is an empty string per
    default, you can define it with the optional parameter:

    .. sourcecode:: jinja

        {{ [1, 2, 3]|join('|') }}
            -> 1|2|3

        {{ [1, 2, 3]|join }}
            -> 123

    It is also possible to join certain attributes of an object:

    .. sourcecode:: jinja

        {{ users|join(', ', attribute='username') }}

    .. versionadded:: 2.6
       The `attribute` parameter was added.
    """
    if attribute is not None:
        value = map(make_attrgetter(eval_ctx.environment, attribute), value)

    # no automatic escaping?  joining is a lot easier then
    if not eval_ctx.autoescape:
        return str(d).join(map(str, value))

    # if the delimiter doesn't have an html representation we check
    # if any of the items has.  If yes we do a coercion to Markup
    if not hasattr(d, "__html__"):
        value = list(value)
        do_escape = False

        for idx, item in enumerate(value):
            if hasattr(item, "__html__"):
                do_escape = True
            else:
                value[idx] = str(item)

        if do_escape:
            d = escape(d)
        else:
            d = str(d)

        return d.join(value)

    # no html involved, to normal joining
    return soft_str(d).join(map(soft_str, value))


@async_variant(sync_do_join)  # type: ignore
async def do_join(
    eval_ctx: "EvalContext",
    value: t.Union[t.AsyncIterable[t.Any], t.Iterable[t.Any]],
    d: str = "",
    attribute: t.Optional[t.Union[str, int]] = None,
) -> str:
    return sync_do_join(eval_ctx, await auto_to_list(value), d, attribute)


def do_center(value: str, width: int = 80) -> str:
    """Centers the value in a field of a given width."""
    return soft_str(value).center(width)


@pass_environment
def sync_do_first(
    environment: "Environment", seq: "t.Iterable[V]"
) -> "t.Union[V, Undefined]":
    """Return the first item of a sequence."""
    try:
        return next(iter(seq))
    except StopIteration:
        return environment.undefined("No first item, sequence was empty.")


@async_variant(sync_do_first)  # type: ignore
async def do_first(
    environment: "Environment", seq: "t.Union[t.AsyncIterable[V], t.Iterable[V]]"
) -> "t.Union[V, Undefined]":
    try:
        return await auto_aiter(seq).__anext__()
    except StopAsyncIteration:
        return environment.undefined("No first item, sequence was empty.")


@pass_environment
def do_last(
    environment: "Environment", seq: "t.Reversible[V]"
) -> "t.Union[V, Undefined]":
    """Return the last item of a sequence.

    Note: Does not work with generators. You may want to explicitly
    convert it to a list:

    .. sourcecode:: jinja

        {{ data | selectattr('name', '==', 'Jinja') | list | last }}
    """
    try:
        return next(iter(reversed(seq)))
    except StopIteration:
        return environment.undefined("No last item, sequence was empty.")


# No async do_last, it may not be safe in async mode.


@pass_context
def do_random(context: "Context", seq: "t.Sequence[V]") -> "t.Union[V, Undefined]":
    """Return a random item from the sequence."""
    try:
        return random.choice(seq)
    except IndexError:
        return context.environment.undefined("No random item, sequence was empty.")


def do_filesizeformat(value: t.Union[str, float, int], binary: bool = False) -> str:
    """Format the value like a 'human-readable' file size (i.e. 13 kB,
    4.1 MB, 102 Bytes, etc).  Per default decimal prefixes are used (Mega,
    Giga, etc.), if the second parameter is set to `True` the binary
    prefixes are used (Mebi, Gibi).
    """
    bytes = float(value)
    base = 1024 if binary else 1000
    prefixes = [
        ("KiB" if binary else "kB"),
        ("MiB" if binary else "MB"),
        ("GiB" if binary else "GB"),
        ("TiB" if binary else "TB"),
        ("PiB" if binary else "PB"),
        ("EiB" if binary else "EB"),
        ("ZiB" if binary else "ZB"),
        ("YiB" if binary else "YB"),
    ]

    if bytes == 1:
        return "1 Byte"
    elif bytes < base:
        return f"{int(bytes)} Bytes"
    else:
        for i, prefix in enumerate(prefixes):
            unit = base ** (i + 2)

            if bytes < unit:
                return f"{base * bytes / unit:.1f} {prefix}"

        return f"{base * bytes / unit:.1f} {prefix}"


def do_pprint(value: t.Any) -> str:
    """Pretty print a variable. Useful for debugging."""
    return pformat(value)


_uri_scheme_re = re.compile(r"^([\w.+-]{2,}:(/){0,2})$")


@pass_eval_context
def do_urlize(
    eval_ctx: "EvalContext",
    value: str,
    trim_url_limit: t.Optional[int] = None,
    nofollow: bool = False,
    target: t.Optional[str] = None,
    rel: t.Optional[str] = None,
    extra_schemes: t.Optional[t.Iterable[str]] = None,
) -> str:
    """Convert URLs in text into clickable links.

    This may not recognize links in some situations. Usually, a more
    comprehensive formatter, such as a Markdown library, is a better
    choice.

    Works on ``http://``, ``https://``, ``www.``, ``mailto:``, and email
    addresses. Links with trailing punctuation (periods, commas, closing
    parentheses) and leading punctuation (opening parentheses) are
    recognized excluding the punctuation. Email addresses that include
    header fields are not recognized (for example,
    ``mailto:address@example.com?cc=copy@example.com``).

    :param value: Original text containing URLs to link.
    :param trim_url_limit: Shorten displayed URL values to this length.
    :param nofollow: Add the ``rel=nofollow`` attribute to links.
    :param target: Add the ``target`` attribute to links.
    :param rel: Add the ``rel`` attribute to links.
    :param extra_schemes: Recognize URLs that start with these schemes
        in addition to the default behavior. Defaults to
        ``env.policies["urlize.extra_schemes"]``, which defaults to no
        extra schemes.

    .. versionchanged:: 3.0
        The ``extra_schemes`` parameter was added.

    .. versionchanged:: 3.0
        Generate ``https://`` links for URLs without a scheme.

    .. versionchanged:: 3.0
        The parsing rules were updated. Recognize email addresses with
        or without the ``mailto:`` scheme. Validate IP addresses. Ignore
        parentheses and brackets in more cases.

    .. versionchanged:: 2.8
       The ``target`` parameter was added.
    """
    policies = eval_ctx.environment.policies
    rel_parts = set((rel or "").split())

    if nofollow:
        rel_parts.add("nofollow")

    rel_parts.update((policies["urlize.rel"] or "").split())
    rel = " ".join(sorted(rel_parts)) or None

    if target is None:
        target = policies["urlize.target"]

    if extra_schemes is None:
        extra_schemes = policies["urlize.extra_schemes"] or ()

    for scheme in extra_schemes:
        if _uri_scheme_re.fullmatch(scheme) is None:
            raise FilterArgumentError(f"{scheme!r} is not a valid URI scheme prefix.")

    rv = urlize(
        value,
        trim_url_limit=trim_url_limit,
        rel=rel,
        target=target,
        extra_schemes=extra_schemes,
    )

    if eval_ctx.autoescape:
        rv = Markup(rv)

    return rv


def do_indent(
    s: str, width: t.Union[int, str] = 4, first: bool = False, blank: bool = False
) -> str:
    """Return a copy of the string with each line indented by 4 spaces. The
    first line and blank lines are not indented by default.

    :param width: Number of spaces, or a string, to indent by.
    :param first: Don't skip indenting the first line.
    :param blank: Don't skip indenting empty lines.

    .. versionchanged:: 3.0
        ``width`` can be a string.

    .. versionchanged:: 2.10
        Blank lines are not indented by default.

        Rename the ``indentfirst`` argument to ``first``.
    """
    if isinstance(width, str):
        indention = width
    else:
        indention = " " * width

    newline = "\n"

    if isinstance(s, Markup):
        indention = Markup(indention)
        newline = Markup(newline)

    s += newline  # this quirk is necessary for splitlines method

    if blank:
        rv = (newline + indention).join(s.splitlines())
    else:
        lines = s.splitlines()
        rv = lines.pop(0)

        if lines:
            rv += newline + newline.join(
                indention + line if line else line for line in lines
            )

    if first:
        rv = indention + rv

    return rv


@pass_environment
def do_truncate(
    env: "Environment",
    s: str,
    length: int = 255,
    killwords: bool = False,
    end: str = "...",
    leeway: t.Optional[int] = None,
) -> str:
    """Return a truncated copy of the string. The length is specified
    with the first parameter which defaults to ``255``. If the second
    parameter is ``true`` the filter will cut the text at length. Otherwise
    it will discard the last word. If the text was in fact
    truncated it will append an ellipsis sign (``"..."``). If you want a
    different ellipsis sign than ``"..."`` you can specify it using the
    third parameter. Strings that only exceed the length by the tolerance
    margin given in the fourth parameter will not be truncated.

    .. sourcecode:: jinja

        {{ "foo bar baz qux"|truncate(9) }}
            -> "foo..."
        {{ "foo bar baz qux"|truncate(9, True) }}
            -> "foo ba..."
        {{ "foo bar baz qux"|truncate(11) }}
            -> "foo bar baz qux"
        {{ "foo bar baz qux"|truncate(11, False, '...', 0) }}
            -> "foo bar..."

    The default leeway on newer Jinja versions is 5 and was 0 before but
    can be reconfigured globally.
    """
    if leeway is None:
        leeway = env.policies["truncate.leeway"]

    assert length >= len(end), f"expected length >= {len(end)}, got {length}"
    assert leeway >= 0, f"expected leeway >= 0, got {leeway}"

    if len(s) <= length + leeway:
        return s

    if killwords:
        return s[: length - len(end)] + end

    result = s[: length - len(end)].rsplit(" ", 1)[0]
    return result + end


@pass_environment
def do_wordwrap(
    environment: "Environment",
    s: str,
    width: int = 79,
    break_long_words: bool = True,
    wrapstring: t.Optional[str] = None,
    break_on_hyphens: bool = True,
) -> str:
    """Wrap a string to the given width. Existing newlines are treated
    as paragraphs to be wrapped separately.

    :param s: Original text to wrap.
    :param width: Maximum length of wrapped lines.
    :param break_long_words: If a word is longer than ``width``, break
        it across lines.
    :param break_on_hyphens: If a word contains hyphens, it may be split
        across lines.
    :param wrapstring: String to join each wrapped line. Defaults to
        :attr:`Environment.newline_sequence`.

    .. versionchanged:: 2.11
        Existing newlines are treated as paragraphs wrapped separately.

    .. versionchanged:: 2.11
        Added the ``break_on_hyphens`` parameter.

    .. versionchanged:: 2.7
        Added the ``wrapstring`` parameter.
    """
    import textwrap

    if wrapstring is None:
        wrapstring = environment.newline_sequence

    # textwrap.wrap doesn't consider existing newlines when wrapping.
    # If the string has a newline before width, wrap will still insert
    # a newline at width, resulting in a short line. Instead, split and
    # wrap each paragraph individually.
    return wrapstring.join(
        [
            wrapstring.join(
                textwrap.wrap(
                    line,
                    width=width,
                    expand_tabs=False,
                    replace_whitespace=False,
                    break_long_words=break_long_words,
                    break_on_hyphens=break_on_hyphens,
                )
            )
            for line in s.splitlines()
        ]
    )


_word_re = re.compile(r"\w+")


def do_wordcount(s: str) -> int:
    """Count the words in that string."""
    return len(_word_re.findall(soft_str(s)))


def do_int(value: t.Any, default: int = 0, base: int = 10) -> int:
    """Convert the value into an integer. If the
    conversion doesn't work it will return ``0``. You can
    override this default using the first parameter. You
    can also override the default base (10) in the second
    parameter, which handles input with prefixes such as
    0b, 0o and 0x for bases 2, 8 and 16 respectively.
    The base is ignored for decimal numbers and non-string values.
    """
    try:
        if isinstance(value, str):
            return int(value, base)

        return int(value)
    except (TypeError, ValueError):
        # this quirk is necessary so that "42.23"|int gives 42.
        try:
            return int(float(value))
        except (TypeError, ValueError, OverflowError):
            return default


def do_float(value: t.Any, default: float = 0.0) -> float:
    """Convert the value into a floating point number. If the
    conversion doesn't work it will return ``0.0``. You can
    override this default using the first parameter.
    """
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def do_format(value: str, *args: t.Any, **kwargs: t.Any) -> str:
    """Apply the given values to a `printf-style`_ format string, like
    ``string % values``.

    .. sourcecode:: jinja

        {{ "%s, %s!"|format(greeting, name) }}
        Hello, World!

    In most cases it should be more convenient and efficient to use the
    ``%`` operator or :meth:`str.format`.

    .. code-block:: text

        {{ "%s, %s!" % (greeting, name) }}
        {{ "{}, {}!".format(greeting, name) }}

    .. _printf-style: https://docs.python.org/library/stdtypes.html
        #printf-style-string-formatting
    """
    if args and kwargs:
        raise FilterArgumentError(
            "can't handle positional and keyword arguments at the same time"
        )

    return soft_str(value) % (kwargs or args)


def do_trim(value: str, chars: t.Optional[str] = None) -> str:
    """Strip leading and trailing characters, by default whitespace."""
    return soft_str(value).strip(chars)


def do_striptags(value: "t.Union[str, HasHTML]") -> str:
    """Strip SGML/XML tags and replace adjacent whitespace by one space."""
    if hasattr(value, "__html__"):
        value = t.cast("HasHTML", value).__html__()

    return Markup(str(value)).striptags()


def sync_do_slice(
    value: "t.Collection[V]", slices: int, fill_with: "t.Optional[V]" = None
) -> "t.Iterator[t.List[V]]":
    """Slice an iterator and return a list of lists containing
    those items. Useful if you want to create a div containing
    three ul tags that represent columns:

    .. sourcecode:: html+jinja

        <div class="columnwrapper">
          {%- for column in items|slice(3) %}
            <ul class="column-{{ loop.index }}">
            {%- for item in column %}
              <li>{{ item }}</li>
            {%- endfor %}
            </ul>
          {%- endfor %}
        </div>

    If you pass it a second argument it's used to fill missing
    values on the last iteration.
    """
    seq = list(value)
    length = len(seq)
    items_per_slice = length // slices
    slices_with_extra = length % slices
    offset = 0

    for slice_number in range(slices):
        start = offset + slice_number * items_per_slice

        if slice_number < slices_with_extra:
            offset += 1

        end = offset + (slice_number + 1) * items_per_slice
        tmp = seq[start:end]

        if fill_with is not None and slice_number >= slices_with_extra:
            tmp.append(fill_with)

        yield tmp


@async_variant(sync_do_slice)  # type: ignore
async def do_slice(
    value: "t.Union[t.AsyncIterable[V], t.Iterable[V]]",
    slices: int,
    fill_with: t.Optional[t.Any] = None,
) -> "t.Iterator[t.List[V]]":
    return sync_do_slice(await auto_to_list(value), slices, fill_with)


def do_batch(
    value: "t.Iterable[V]", linecount: int, fill_with: "t.Optional[V]" = None
) -> "t.Iterator[t.List[V]]":
    """
    A filter that batches items. It works pretty much like `slice`
    just the other way round. It returns a list of lists with the
    given number of items. If you provide a second parameter this
    is used to fill up missing items. See this example:

    .. sourcecode:: html+jinja

        <table>
        {%- for row in items|batch(3, '&nbsp;') %}
          <tr>
          {%- for column in row %}
            <td>{{ column }}</td>
          {%- endfor %}
          </tr>
        {%- endfor %}
        </table>
    """
    tmp: t.List[V] = []

    for item in value:
        if len(tmp) == linecount:
            yield tmp
            tmp = []

        tmp.append(item)

    if tmp:
        if fill_with is not None and len(tmp) < linecount:
            tmp += [fill_with] * (linecount - len(tmp))

        yield tmp


def do_round(
    value: float,
    precision: int = 0,
    method: 'te.Literal["common", "ceil", "floor"]' = "common",
) -> float:
    """Round the number to a given precision. The first
    parameter specifies the precision (default is ``0``), the
    second the rounding method:

    - ``'common'`` rounds either up or down
    - ``'ceil'`` always rounds up
    - ``'floor'`` always rounds down

    If you don't specify a method ``'common'`` is used.

    .. sourcecode:: jinja

        {{ 42.55|round }}
            -> 43.0
        {{ 42.55|round(1, 'floor') }}
            -> 42.5

    Note that even if rounded to 0 precision, a float is returned.  If
    you need a real integer, pipe it through `int`:

    .. sourcecode:: jinja

        {{ 42.55|round|int }}
            -> 43
    """
    if method not in {"common", "ceil", "floor"}:
        raise FilterArgumentError("method must be common, ceil or floor")

    if method == "common":
        return round(value, precision)

    func = getattr(math, method)
    return t.cast(float, func(value * (10**precision)) / (10**precision))


class _GroupTuple(t.NamedTuple):
    grouper: t.Any
    list: t.List[t.Any]

    # Use the regular tuple repr to hide this subclass if users print
    # out the value during debugging.
    def __repr__(self) -> str:
        return tuple.__repr__(self)

    def __str__(self) -> str:
        return tuple.__str__(self)


@pass_environment
def sync_do_groupby(
    environment: "Environment",
    value: "t.Iterable[V]",
    attribute: t.Union[str, int],
    default: t.Optional[t.Any] = None,
    case_sensitive: bool = False,
) -> "t.List[_GroupTuple]":
    """Group a sequence of objects by an attribute using Python's
    :func:`itertools.groupby`. The attribute can use dot notation for
    nested access, like ``"address.city"``. Unlike Python's ``groupby``,
    the values are sorted first so only one group is returned for each
    unique value.

    For example, a list of ``User`` objects with a ``city`` attribute
    can be rendered in groups. In this example, ``grouper`` refers to
    the ``city`` value of the group.

    .. sourcecode:: html+jinja

        <ul>{% for city, items in users|groupby("city") %}
          <li>{{ city }}
            <ul>{% for user in items %}
              <li>{{ user.name }}
            {% endfor %}</ul>
          </li>
        {% endfor %}</ul>

    ``groupby`` yields namedtuples of ``(grouper, list)``, which
    can be used instead of the tuple unpacking above. ``grouper`` is the
    value of the attribute, and ``list`` is the items with that value.

    .. sourcecode:: html+jinja

        <ul>{% for group in users|groupby("city") %}
          <li>{{ group.grouper }}: {{ group.list|join(", ") }}
        {% endfor %}</ul>

    You can specify a ``default`` value to use if an object in the list
    does not have the given attribute.

    .. sourcecode:: jinja

        <ul>{% for city, items in users|groupby("city", default="NY") %}
          <li>{{ city }}: {{ items|map(attribute="name")|join(", ") }}</li>
        {% endfor %}</ul>

    Like the :func:`~jinja-filters.sort` filter, sorting and grouping is
    case-insensitive by default. The ``key`` for each group will have
    the case of the first item in that group of values. For example, if
    a list of users has cities ``["CA", "NY", "ca"]``, the "CA" group
    will have two values. This can be disabled by passing
    ``case_sensitive=True``.

    .. versionchanged:: 3.1
        Added the ``case_sensitive`` parameter. Sorting and grouping is
        case-insensitive by default, matching other filters that do
        comparisons.

    .. versionchanged:: 3.0
        Added the ``default`` parameter.

    .. versionchanged:: 2.6
        The attribute supports dot notation for nested access.
    """
    expr = make_attrgetter(
        environment,
        attribute,
        postprocess=ignore_case if not case_sensitive else None,
        default=default,
    )
    out = [
        _GroupTuple(key, list(values))
        for key, values in groupby(sorted(value, key=expr), expr)
    ]

    if not case_sensitive:
        # Return the real key from the first value instead of the lowercase key.
        output_expr = make_attrgetter(environment, attribute, default=default)
        out = [_GroupTuple(output_expr(values[0]), values) for _, values in out]

    return out


@async_variant(sync_do_groupby)  # type: ignore
async def do_groupby(
    environment: "Environment",
    value: "t.Union[t.AsyncIterable[V], t.Iterable[V]]",
    attribute: t.Union[str, int],
    default: t.Optional[t.Any] = None,
    case_sensitive: bool = False,
) -> "t.List[_GroupTuple]":
    expr = make_attrgetter(
        environment,
        attribute,
        postprocess=ignore_case if not case_sensitive else None,
        default=default,
    )
    out = [
        _GroupTuple(key, await auto_to_list(values))
        for key, values in groupby(sorted(await auto_to_list(value), key=expr), expr)
    ]

    if not case_sensitive:
        # Return the real key from the first value instead of the lowercase key.
        output_expr = make_attrgetter(environment, attribute, default=default)
        out = [_GroupTuple(output_expr(values[0]), values) for _, values in out]

    return out


@pass_environment
def sync_do_sum(
    environment: "Environment",
    iterable: "t.Iterable[V]",
    attribute: t.Optional[t.Union[str, int]] = None,
    start: V = 0,  # type: ignore
) -> V:
    """Returns the sum of a sequence of numbers plus the value of parameter
    'start' (which defaults to 0).  When the sequence is empty it returns
    start.

    It is also possible to sum up only certain attributes:

    .. sourcecode:: jinja

        Total: {{ items|sum(attribute='price') }}

    .. versionchanged:: 2.6
       The ``attribute`` parameter was added to allow summing up over
       attributes.  Also the ``start`` parameter was moved on to the right.
    """
    if attribute is not None:
        iterable = map(make_attrgetter(environment, attribute), iterable)

    return sum(iterable, start)  # type: ignore[no-any-return, call-overload]


@async_variant(sync_do_sum)  # type: ignore
async def do_sum(
    environment: "Environment",
    iterable: "t.Union[t.AsyncIterable[V], t.Iterable[V]]",
    attribute: t.Optional[t.Union[str, int]] = None,
    start: V = 0,  # type: ignore
) -> V:
    rv = start

    if attribute is not None:
        func = make_attrgetter(environment, attribute)
    else:

        def func(x: V) -> V:
            return x

    async for item in auto_aiter(iterable):
        rv += func(item)

    return rv


def sync_do_list(value: "t.Iterable[V]") -> "t.List[V]":
    """Convert the value into a list.  If it was a string the returned list
    will be a list of characters.
    """
    return list(value)


@async_variant(sync_do_list)  # type: ignore
async def do_list(value: "t.Union[t.AsyncIterable[V], t.Iterable[V]]") -> "t.List[V]":
    return await auto_to_list(value)


def do_mark_safe(value: str) -> Markup:
    """Mark the value as safe which means that in an environment with automatic
    escaping enabled this variable will not be escaped.
    """
    return Markup(value)


def do_mark_unsafe(value: str) -> str:
    """Mark a value as unsafe.  This is the reverse operation for :func:`safe`."""
    return str(value)


@typing.overload
def do_reverse(value: str) -> str: ...


@typing.overload
def do_reverse(value: "t.Iterable[V]") -> "t.Iterable[V]": ...


def do_reverse(value: t.Union[str, t.Iterable[V]]) -> t.Union[str, t.Iterable[V]]:
    """Reverse the object or return an iterator that iterates over it the other
    way round.
    """
    if isinstance(value, str):
        return value[::-1]

    try:
        return reversed(value)  # type: ignore
    except TypeError:
        try:
            rv = list(value)
            rv.reverse()
            return rv
        except TypeError as e:
            raise FilterArgumentError("argument must be iterable") from e


@pass_environment
def do_attr(
    environment: "Environment", obj: t.Any, name: str
) -> t.Union[Undefined, t.Any]:
    """Get an attribute of an object. ``foo|attr("bar")`` works like
    ``foo.bar``, but returns undefined instead of falling back to ``foo["bar"]``
    if the attribute doesn't exist.

    See :ref:`Notes on subscriptions <notes-on-subscriptions>` for more details.
    """
    # Environment.getattr will fall back to obj[name] if obj.name doesn't exist.
    # But we want to call env.getattr to get behavior such as sandboxing.
    # Determine if the attr exists first, so we know the fallback won't trigger.
    try:
        # This avoids executing properties/descriptors, but misses __getattr__
        # and __getattribute__ dynamic attrs.
        getattr_static(obj, name)
    except AttributeError:
        # This finds dynamic attrs, and we know it's not a descriptor at this point.
        if not hasattr(obj, name):
            return environment.undefined(obj=obj, name=name)

    return environment.getattr(obj, name)


@typing.overload
def sync_do_map(
    context: "Context",
    value: t.Iterable[t.Any],
    name: str,
    *args: t.Any,
    **kwargs: t.Any,
) -> t.Iterable[t.Any]: ...


@typing.overload
def sync_do_map(
    context: "Context",
    value: t.Iterable[t.Any],
    *,
    attribute: str = ...,
    default: t.Optional[t.Any] = None,
) -> t.Iterable[t.Any]: ...


@pass_context
def sync_do_map(
    context: "Context", value: t.Iterable[t.Any], *args: t.Any, **kwargs: t.Any
) -> t.Iterable[t.Any]:
    """Applies a filter on a sequence of objects or looks up an attribute.
    This is useful when dealing with lists of objects but you are really
    only interested in a certain value of it.

    The basic usage is mapping on an attribute.  Imagine you have a list
    of users but you are only interested in a list of usernames:

    .. sourcecode:: jinja

        Users on this page: {{ users|map(attribute='username')|join(', ') }}

    You can specify a ``default`` value to use if an object in the list
    does not have the given attribute.

    .. sourcecode:: jinja

        {{ users|map(attribute="username", default="Anonymous")|join(", ") }}

    Alternatively you can let it invoke a filter by passing the name of the
    filter and the arguments afterwards.  A good example would be applying a
    text conversion filter on a sequence:

    .. sourcecode:: jinja

        Users on this page: {{ titles|map('lower')|join(', ') }}

    Similar to a generator comprehension such as:

    .. code-block:: python

        (u.username for u in users)
        (getattr(u, "username", "Anonymous") for u in users)
        (do_lower(x) for x in titles)

    .. versionchanged:: 2.11.0
        Added the ``default`` parameter.

    .. versionadded:: 2.7
    """
    if value:
        func = prepare_map(context, args, kwargs)

        for item in value:
            yield func(item)


@typing.overload
def do_map(
    context: "Context",
    value: t.Union[t.AsyncIterable[t.Any], t.Iterable[t.Any]],
    name: str,
    *args: t.Any,
    **kwargs: t.Any,
) -> t.Iterable[t.Any]: ...


@typing.overload
def do_map(
    context: "Context",
    value: t.Union[t.AsyncIterable[t.Any], t.Iterable[t.Any]],
    *,
    attribute: str = ...,
    default: t.Optional[t.Any] = None,
) -> t.Iterable[t.Any]: ...


@async_variant(sync_do_map)  # type: ignore
async def do_map(
    context: "Context",
    value: t.Union[t.AsyncIterable[t.Any], t.Iterable[t.Any]],
    *args: t.Any,
    **kwargs: t.Any,
) -> t.AsyncIterable[t.Any]:
    if value:
        func = prepare_map(context, args, kwargs)

        async for item in auto_aiter(value):
            yield await auto_await(func(item))


@pass_context
def sync_do_select(
    context: "Context", value: "t.Iterable[V]", *args: t.Any, **kwargs: t.Any
) -> "t.Iterator[V]":
    """Filters a sequence of objects by applying a test to each object,
    and only selecting the objects with the test succeeding.

    If no test is specified, each object will be evaluated as a boolean.

    Example usage:

    .. sourcecode:: jinja

        {{ numbers|select("odd") }}
        {{ numbers|select("odd") }}
        {{ numbers|select("divisibleby", 3) }}
        {{ numbers|select("lessthan", 42) }}
        {{ strings|select("equalto", "mystring") }}

    Similar to a generator comprehension such as:

    .. code-block:: python

        (n for n in numbers if test_odd(n))
        (n for n in numbers if test_divisibleby(n, 3))

    .. versionadded:: 2.7
    """
    return select_or_reject(context, value, args, kwargs, lambda x: x, False)


@async_variant(sync_do_select)  # type: ignore
async def do_select(
    context: "Context",
    value: "t.Union[t.AsyncIterable[V], t.Iterable[V]]",
    *args: t.Any,
    **kwargs: t.Any,
) -> "t.AsyncIterator[V]":
    return async_select_or_reject(context, value, args, kwargs, lambda x: x, False)


@pass_context
def sync_do_reject(
    context: "Context", value: "t.Iterable[V]", *args: t.Any, **kwargs: t.Any
) -> "t.Iterator[V]":
    """Filters a sequence of objects by applying a test to each object,
    and rejecting the objects with the test succeeding.

    If no test is specified, each object will be evaluated as a boolean.

    Example usage:

    .. sourcecode:: jinja

        {{ numbers|reject("odd") }}

    Similar to a generator comprehension such as:

    .. code-block:: python

        (n for n in numbers if not test_odd(n))

    .. versionadded:: 2.7
    """
    return select_or_reject(context, value, args, kwargs, lambda x: not x, False)


@async_variant(sync_do_reject)  # type: ignore
async def do_reject(
    context: "Context",
    value: "t.Union[t.AsyncIterable[V], t.Iterable[V]]",
    *args: t.Any,
    **kwargs: t.Any,
) -> "t.AsyncIterator[V]":
    return async_select_or_reject(context, value, args, kwargs, lambda x: not x, False)


@pass_context
def sync_do_selectattr(
    context: "Context", value: "t.Iterable[V]", *args: t.Any, **kwargs: t.Any
) -> "t.Iterator[V]":
    """Filters a sequence of objects by applying a test to the specified
    attribute of each object, and only selecting the objects with the
    test succeeding.

    If no test is specified, the attribute's value will be evaluated as
    a boolean.

    Example usage:

    .. sourcecode:: jinja

        {{ users|selectattr("is_active") }}
        {{ users|selectattr("email", "none") }}

    Similar to a generator comprehension such as:

    .. code-block:: python

        (user for user in users if user.is_active)
        (user for user in users if test_none(user.email))

    .. versionadded:: 2.7
    """
    return select_or_reject(context, value, args, kwargs, lambda x: x, True)


@async_variant(sync_do_selectattr)  # type: ignore
async def do_selectattr(
    context: "Context",
    value: "t.Union[t.AsyncIterable[V], t.Iterable[V]]",
    *args: t.Any,
    **kwargs: t.Any,
) -> "t.AsyncIterator[V]":
    return async_select_or_reject(context, value, args, kwargs, lambda x: x, True)


@pass_context
def sync_do_rejectattr(
    context: "Context", value: "t.Iterable[V]", *args: t.Any, **kwargs: t.Any
) -> "t.Iterator[V]":
    """Filters a sequence of objects by applying a test to the specified
    attribute of each object, and rejecting the objects with the test
    succeeding.

    If no test is specified, the attribute's value will be evaluated as
    a boolean.

    .. sourcecode:: jinja

        {{ users|rejectattr("is_active") }}
        {{ users|rejectattr("email", "none") }}

    Similar to a generator comprehension such as:

    .. code-block:: python

        (user for user in users if not user.is_active)
        (user for user in users if not test_none(user.email))

    .. versionadded:: 2.7
    """
    return select_or_reject(context, value, args, kwargs, lambda x: not x, True)


@async_variant(sync_do_rejectattr)  # type: ignore
async def do_rejectattr(
    context: "Context",
    value: "t.Union[t.AsyncIterable[V], t.Iterable[V]]",
    *args: t.Any,
    **kwargs: t.Any,
) -> "t.AsyncIterator[V]":
    return async_select_or_reject(context, value, args, kwargs, lambda x: not x, True)


@pass_eval_context
def do_tojson(
    eval_ctx: "EvalContext", value: t.Any, indent: t.Optional[int] = None
) -> Markup:
    """Serialize an object to a string of JSON, and mark it safe to
    render in HTML. This filter is only for use in HTML documents.

    The returned string is safe to render in HTML documents and
    ``<script>`` tags. The exception is in HTML attributes that are
    double quoted; either use single quotes or the ``|forceescape``
    filter.

    :param value: The object to serialize to JSON.
    :param indent: The ``indent`` parameter passed to ``dumps``, for
        pretty-printing the value.

    .. versionadded:: 2.9
    """
    policies = eval_ctx.environment.policies
    dumps = policies["json.dumps_function"]
    kwargs = policies["json.dumps_kwargs"]

    if indent is not None:
        kwargs = kwargs.copy()
        kwargs["indent"] = indent

    return htmlsafe_json_dumps(value, dumps=dumps, **kwargs)


def prepare_map(
    context: "Context", args: t.Tuple[t.Any, ...], kwargs: t.Dict[str, t.Any]
) -> t.Callable[[t.Any], t.Any]:
    if not args and "attribute" in kwargs:
        attribute = kwargs.pop("attribute")
        default = kwargs.pop("default", None)

        if kwargs:
            raise FilterArgumentError(
                f"Unexpected keyword argument {next(iter(kwargs))!r}"
            )

        func = make_attrgetter(context.environment, attribute, default=default)
    else:
        try:
            name = args[0]
            args = args[1:]
        except LookupError:
            raise FilterArgumentError("map requires a filter argument") from None

        def func(item: t.Any) -> t.Any:
            return context.environment.call_filter(
                name, item, args, kwargs, context=context
            )

    return func


def prepare_select_or_reject(
    context: "Context",
    args: t.Tuple[t.Any, ...],
    kwargs: t.Dict[str, t.Any],
    modfunc: t.Callable[[t.Any], t.Any],
    lookup_attr: bool,
) -> t.Callable[[t.Any], t.Any]:
    if lookup_attr:
        try:
            attr = args[0]
        except LookupError:
            raise FilterArgumentError("Missing parameter for attribute name") from None

        transfunc = make_attrgetter(context.environment, attr)
        off = 1
    else:
        off = 0

        def transfunc(x: V) -> V:
            return x

    try:
        name = args[off]
        args = args[1 + off :]

        def func(item: t.Any) -> t.Any:
            return context.environment.call_test(name, item, args, kwargs, context)

    except LookupError:
        func = bool  # type: ignore

    return lambda item: modfunc(func(transfunc(item)))


def select_or_reject(
    context: "Context",
    value: "t.Iterable[V]",
    args: t.Tuple[t.Any, ...],
    kwargs: t.Dict[str, t.Any],
    modfunc: t.Callable[[t.Any], t.Any],
    lookup_attr: bool,
) -> "t.Iterator[V]":
    if value:
        func = prepare_select_or_reject(context, args, kwargs, modfunc, lookup_attr)

        for item in value:
            if func(item):
                yield item


async def async_select_or_reject(
    context: "Context",
    value: "t.Union[t.AsyncIterable[V], t.Iterable[V]]",
    args: t.Tuple[t.Any, ...],
    kwargs: t.Dict[str, t.Any],
    modfunc: t.Callable[[t.Any], t.Any],
    lookup_attr: bool,
) -> "t.AsyncIterator[V]":
    if value:
        func = prepare_select_or_reject(context, args, kwargs, modfunc, lookup_attr)

        async for item in auto_aiter(value):
            if func(item):
                yield item


FILTERS = {
    "abs": abs,
    "attr": do_attr,
    "batch": do_batch,
    "capitalize": do_capitalize,
    "center": do_center,
    "count": len,
    "d": do_default,
    "default": do_default,
    "dictsort": do_dictsort,
    "e": escape,
    "escape": escape,
    "filesizeformat": do_filesizeformat,
    "first": do_first,
    "float": do_float,
    "forceescape": do_forceescape,
    "format": do_format,
    "groupby": do_groupby,
    "indent": do_indent,
    "int": do_int,
    "join": do_join,
    "last": do_last,
    "length": len,
    "list": do_list,
    "lower": do_lower,
    "items": do_items,
    "map": do_map,
    "min": do_min,
    "max": do_max,
    "pprint": do_pprint,
    "random": do_random,
    "reject": do_reject,
    "rejectattr": do_rejectattr,
    "replace": do_replace,
    "reverse": do_reverse,
    "round": do_round,
    "safe": do_mark_safe,
    "select": do_select,
    "selectattr": do_selectattr,
    "slice": do_slice,
    "sort": do_sort,
    "string": soft_str,
    "striptags": do_striptags,
    "sum": do_sum,
    "title": do_title,
    "trim": do_trim,
    "truncate": do_truncate,
    "unique": do_unique,
    "upper": do_upper,
    "urlencode": do_urlencode,
    "urlize": do_urlize,
    "wordcount": do_wordcount,
    "wordwrap": do_wordwrap,
    "xmlattr": do_xmlattr,
    "tojson": do_tojson,
}

# === NexusCore/openenv\Lib\site-packages\matplotlib\artist.py ===
from collections import namedtuple
import contextlib
from functools import cache, reduce, wraps
import inspect
from inspect import Signature, Parameter
import logging
from numbers import Number, Real
import operator
import re
import warnings

import numpy as np

import matplotlib as mpl
from . import _api, cbook
from .path import Path
from .transforms import (BboxBase, Bbox, IdentityTransform, Transform, TransformedBbox,
                         TransformedPatchPath, TransformedPath)

_log = logging.getLogger(__name__)


def _prevent_rasterization(draw):
    # We assume that by default artists are not allowed to rasterize (unless
    # its draw method is explicitly decorated). If it is being drawn after a
    # rasterized artist and it has reached a raster_depth of 0, we stop
    # rasterization so that it does not affect the behavior of normal artist
    # (e.g., change in dpi).

    @wraps(draw)
    def draw_wrapper(artist, renderer, *args, **kwargs):
        if renderer._raster_depth == 0 and renderer._rasterizing:
            # Only stop when we are not in a rasterized parent
            # and something has been rasterized since last stop.
            renderer.stop_rasterizing()
            renderer._rasterizing = False

        return draw(artist, renderer, *args, **kwargs)

    draw_wrapper._supports_rasterization = False
    return draw_wrapper


def allow_rasterization(draw):
    """
    Decorator for Artist.draw method. Provides routines
    that run before and after the draw call. The before and after functions
    are useful for changing artist-dependent renderer attributes or making
    other setup function calls, such as starting and flushing a mixed-mode
    renderer.
    """

    @wraps(draw)
    def draw_wrapper(artist, renderer):
        try:
            if artist.get_rasterized():
                if renderer._raster_depth == 0 and not renderer._rasterizing:
                    renderer.start_rasterizing()
                    renderer._rasterizing = True
                renderer._raster_depth += 1
            else:
                if renderer._raster_depth == 0 and renderer._rasterizing:
                    # Only stop when we are not in a rasterized parent
                    # and something has be rasterized since last stop
                    renderer.stop_rasterizing()
                    renderer._rasterizing = False

            if artist.get_agg_filter() is not None:
                renderer.start_filter()

            return draw(artist, renderer)
        finally:
            if artist.get_agg_filter() is not None:
                renderer.stop_filter(artist.get_agg_filter())
            if artist.get_rasterized():
                renderer._raster_depth -= 1
            if (renderer._rasterizing and (fig := artist.get_figure(root=True)) and
                    fig.suppressComposite):
                # restart rasterizing to prevent merging
                renderer.stop_rasterizing()
                renderer.start_rasterizing()

    draw_wrapper._supports_rasterization = True
    return draw_wrapper


def _finalize_rasterization(draw):
    """
    Decorator for Artist.draw method. Needed on the outermost artist, i.e.
    Figure, to finish up if the render is still in rasterized mode.
    """
    @wraps(draw)
    def draw_wrapper(artist, renderer, *args, **kwargs):
        result = draw(artist, renderer, *args, **kwargs)
        if renderer._rasterizing:
            renderer.stop_rasterizing()
            renderer._rasterizing = False
        return result
    return draw_wrapper


def _stale_axes_callback(self, val):
    if self.axes:
        self.axes.stale = val


_XYPair = namedtuple("_XYPair", "x y")


class _Unset:
    def __repr__(self):
        return "<UNSET>"
_UNSET = _Unset()


class Artist:
    """
    Abstract base class for objects that render into a FigureCanvas.

    Typically, all visible elements in a figure are subclasses of Artist.
    """

    zorder = 0

    def __init_subclass__(cls):

        # Decorate draw() method so that all artists are able to stop
        # rastrization when necessary. If the artist's draw method is already
        # decorated (has a `_supports_rasterization` attribute), it won't be
        # decorated.

        if not hasattr(cls.draw, "_supports_rasterization"):
            cls.draw = _prevent_rasterization(cls.draw)

        # Inject custom set() methods into the subclass with signature and
        # docstring based on the subclasses' properties.

        if not hasattr(cls.set, '_autogenerated_signature'):
            # Don't overwrite cls.set if the subclass or one of its parents
            # has defined a set method set itself.
            # If there was no explicit definition, cls.set is inherited from
            # the hierarchy of auto-generated set methods, which hold the
            # flag _autogenerated_signature.
            return

        cls.set = lambda self, **kwargs: Artist.set(self, **kwargs)
        cls.set.__name__ = "set"
        cls.set.__qualname__ = f"{cls.__qualname__}.set"
        cls._update_set_signature_and_docstring()

    _PROPERTIES_EXCLUDED_FROM_SET = [
        'navigate_mode',  # not a user-facing function
        'figure',         # changing the figure is such a profound operation
                          # that we don't want this in set()
        '3d_properties',  # cannot be used as a keyword due to leading digit
    ]

    @classmethod
    def _update_set_signature_and_docstring(cls):
        """
        Update the signature of the set function to list all properties
        as keyword arguments.

        Property aliases are not listed in the signature for brevity, but
        are still accepted as keyword arguments.
        """
        cls.set.__signature__ = Signature(
            [Parameter("self", Parameter.POSITIONAL_OR_KEYWORD),
             *[Parameter(prop, Parameter.KEYWORD_ONLY, default=_UNSET)
               for prop in ArtistInspector(cls).get_setters()
               if prop not in Artist._PROPERTIES_EXCLUDED_FROM_SET]])
        cls.set._autogenerated_signature = True

        cls.set.__doc__ = (
            "Set multiple properties at once.\n\n"
            "Supported properties are\n\n"
            + kwdoc(cls))

    def __init__(self):
        self._stale = True
        self.stale_callback = None
        self._axes = None
        self._parent_figure = None

        self._transform = None
        self._transformSet = False
        self._visible = True
        self._animated = False
        self._alpha = None
        self.clipbox = None
        self._clippath = None
        self._clipon = True
        self._label = ''
        self._picker = None
        self._rasterized = False
        self._agg_filter = None
        # Normally, artist classes need to be queried for mouseover info if and
        # only if they override get_cursor_data.
        self._mouseover = type(self).get_cursor_data != Artist.get_cursor_data
        self._callbacks = cbook.CallbackRegistry(signals=["pchanged"])
        try:
            self.axes = None
        except AttributeError:
            # Handle self.axes as a read-only property, as in Figure.
            pass
        self._remove_method = None
        self._url = None
        self._gid = None
        self._snap = None
        self._sketch = mpl.rcParams['path.sketch']
        self._path_effects = mpl.rcParams['path.effects']
        self._sticky_edges = _XYPair([], [])
        self._in_layout = True

    def __getstate__(self):
        d = self.__dict__.copy()
        d['stale_callback'] = None
        return d

    def remove(self):
        """
        Remove the artist from the figure if possible.

        The effect will not be visible until the figure is redrawn, e.g.,
        with `.FigureCanvasBase.draw_idle`.  Call `~.axes.Axes.relim` to
        update the Axes limits if desired.

        Note: `~.axes.Axes.relim` will not see collections even if the
        collection was added to the Axes with *autolim* = True.

        Note: there is no support for removing the artist's legend entry.
        """

        # There is no method to set the callback.  Instead, the parent should
        # set the _remove_method attribute directly.  This would be a
        # protected attribute if Python supported that sort of thing.  The
        # callback has one parameter, which is the child to be removed.
        if self._remove_method is not None:
            self._remove_method(self)
            # clear stale callback
            self.stale_callback = None
            _ax_flag = False
            if hasattr(self, 'axes') and self.axes:
                # remove from the mouse hit list
                self.axes._mouseover_set.discard(self)
                self.axes.stale = True
                self.axes = None  # decouple the artist from the Axes
                _ax_flag = True

            if (fig := self.get_figure(root=False)) is not None:
                if not _ax_flag:
                    fig.stale = True
                self._parent_figure = None

        else:
            raise NotImplementedError('cannot remove artist')
        # TODO: the fix for the collections relim problem is to move the
        # limits calculation into the artist itself, including the property of
        # whether or not the artist should affect the limits.  Then there will
        # be no distinction between axes.add_line, axes.add_patch, etc.
        # TODO: add legend support

    def have_units(self):
        """Return whether units are set on any axis."""
        ax = self.axes
        return ax and any(axis.have_units() for axis in ax._axis_map.values())

    def convert_xunits(self, x):
        """
        Convert *x* using the unit type of the xaxis.

        If the artist is not contained in an Axes or if the xaxis does not
        have units, *x* itself is returned.
        """
        ax = getattr(self, 'axes', None)
        if ax is None or ax.xaxis is None:
            return x
        return ax.xaxis.convert_units(x)

    def convert_yunits(self, y):
        """
        Convert *y* using the unit type of the yaxis.

        If the artist is not contained in an Axes or if the yaxis does not
        have units, *y* itself is returned.
        """
        ax = getattr(self, 'axes', None)
        if ax is None or ax.yaxis is None:
            return y
        return ax.yaxis.convert_units(y)

    @property
    def axes(self):
        """The `~.axes.Axes` instance the artist resides in, or *None*."""
        return self._axes

    @axes.setter
    def axes(self, new_axes):
        if (new_axes is not None and self._axes is not None
                and new_axes != self._axes):
            raise ValueError("Can not reset the Axes. You are probably trying to reuse "
                             "an artist in more than one Axes which is not supported")
        self._axes = new_axes
        if new_axes is not None and new_axes is not self:
            self.stale_callback = _stale_axes_callback

    @property
    def stale(self):
        """
        Whether the artist is 'stale' and needs to be re-drawn for the output
        to match the internal state of the artist.
        """
        return self._stale

    @stale.setter
    def stale(self, val):
        self._stale = val

        # if the artist is animated it does not take normal part in the
        # draw stack and is not expected to be drawn as part of the normal
        # draw loop (when not saving) so do not propagate this change
        if self._animated:
            return

        if val and self.stale_callback is not None:
            self.stale_callback(self, val)

    def get_window_extent(self, renderer=None):
        """
        Get the artist's bounding box in display space.

        The bounding box' width and height are nonnegative.

        Subclasses should override for inclusion in the bounding box
        "tight" calculation. Default is to return an empty bounding
        box at 0, 0.

        Be careful when using this function, the results will not update
        if the artist window extent of the artist changes.  The extent
        can change due to any changes in the transform stack, such as
        changing the Axes limits, the figure size, or the canvas used
        (as is done when saving a figure).  This can lead to unexpected
        behavior where interactive figures will look fine on the screen,
        but will save incorrectly.
        """
        return Bbox([[0, 0], [0, 0]])

    def get_tightbbox(self, renderer=None):
        """
        Like `.Artist.get_window_extent`, but includes any clipping.

        Parameters
        ----------
        renderer : `~matplotlib.backend_bases.RendererBase` subclass, optional
            renderer that will be used to draw the figures (i.e.
            ``fig.canvas.get_renderer()``)

        Returns
        -------
        `.Bbox` or None
            The enclosing bounding box (in figure pixel coordinates).
            Returns None if clipping results in no intersection.
        """
        bbox = self.get_window_extent(renderer)
        if self.get_clip_on():
            clip_box = self.get_clip_box()
            if clip_box is not None:
                bbox = Bbox.intersection(bbox, clip_box)
            clip_path = self.get_clip_path()
            if clip_path is not None and bbox is not None:
                clip_path = clip_path.get_fully_transformed_path()
                bbox = Bbox.intersection(bbox, clip_path.get_extents())
        return bbox

    def add_callback(self, func):
        """
        Add a callback function that will be called whenever one of the
        `.Artist`'s properties changes.

        Parameters
        ----------
        func : callable
            The callback function. It must have the signature::

                def func(artist: Artist) -> Any

            where *artist* is the calling `.Artist`. Return values may exist
            but are ignored.

        Returns
        -------
        int
            The observer id associated with the callback. This id can be
            used for removing the callback with `.remove_callback` later.

        See Also
        --------
        remove_callback
        """
        # Wrapping func in a lambda ensures it can be connected multiple times
        # and never gets weakref-gc'ed.
        return self._callbacks.connect("pchanged", lambda: func(self))

    def remove_callback(self, oid):
        """
        Remove a callback based on its observer id.

        See Also
        --------
        add_callback
        """
        self._callbacks.disconnect(oid)

    def pchanged(self):
        """
        Call all of the registered callbacks.

        This function is triggered internally when a property is changed.

        See Also
        --------
        add_callback
        remove_callback
        """
        self._callbacks.process("pchanged")

    def is_transform_set(self):
        """
        Return whether the Artist has an explicitly set transform.

        This is *True* after `.set_transform` has been called.
        """
        return self._transformSet

    def set_transform(self, t):
        """
        Set the artist transform.

        Parameters
        ----------
        t : `~matplotlib.transforms.Transform`
        """
        self._transform = t
        self._transformSet = True
        self.pchanged()
        self.stale = True

    def get_transform(self):
        """Return the `.Transform` instance used by this artist."""
        if self._transform is None:
            self._transform = IdentityTransform()
        elif (not isinstance(self._transform, Transform)
              and hasattr(self._transform, '_as_mpl_transform')):
            self._transform = self._transform._as_mpl_transform(self.axes)
        return self._transform

    def get_children(self):
        r"""Return a list of the child `.Artist`\s of this `.Artist`."""
        return []

    def _different_canvas(self, event):
        """
        Check whether an *event* occurred on a canvas other that this artist's canvas.

        If this method returns True, the event definitely occurred on a different
        canvas; if it returns False, either it occurred on the same canvas, or we may
        not have enough information to know.

        Subclasses should start their definition of `contains` as follows::

            if self._different_canvas(mouseevent):
                return False, {}
            # subclass-specific implementation follows
        """
        return (getattr(event, "canvas", None) is not None
                and (fig := self.get_figure(root=True)) is not None
                and event.canvas is not fig.canvas)

    def contains(self, mouseevent):
        """
        Test whether the artist contains the mouse event.

        Parameters
        ----------
        mouseevent : `~matplotlib.backend_bases.MouseEvent`

        Returns
        -------
        contains : bool
            Whether any values are within the radius.
        details : dict
            An artist-specific dictionary of details of the event context,
            such as which points are contained in the pick radius. See the
            individual Artist subclasses for details.
        """
        _log.warning("%r needs 'contains' method", self.__class__.__name__)
        return False, {}

    def pickable(self):
        """
        Return whether the artist is pickable.

        See Also
        --------
        .Artist.set_picker, .Artist.get_picker, .Artist.pick
        """
        return self.get_figure(root=False) is not None and self._picker is not None

    def pick(self, mouseevent):
        """
        Process a pick event.

        Each child artist will fire a pick event if *mouseevent* is over
        the artist and the artist has picker set.

        See Also
        --------
        .Artist.set_picker, .Artist.get_picker, .Artist.pickable
        """
        from .backend_bases import PickEvent  # Circular import.
        # Pick self
        if self.pickable():
            picker = self.get_picker()
            if callable(picker):
                inside, prop = picker(self, mouseevent)
            else:
                inside, prop = self.contains(mouseevent)
            if inside:
                PickEvent("pick_event", self.get_figure(root=True).canvas,
                          mouseevent, self, **prop)._process()

        # Pick children
        for a in self.get_children():
            # make sure the event happened in the same Axes
            ax = getattr(a, 'axes', None)
            if (isinstance(a, mpl.figure.SubFigure)
                    or mouseevent.inaxes is None or ax is None
                    or mouseevent.inaxes == ax):
                # we need to check if mouseevent.inaxes is None
                # because some objects associated with an Axes (e.g., a
                # tick label) can be outside the bounding box of the
                # Axes and inaxes will be None
                # also check that ax is None so that it traverse objects
                # which do not have an axes property but children might
                a.pick(mouseevent)

    def set_picker(self, picker):
        """
        Define the picking behavior of the artist.

        Parameters
        ----------
        picker : None or bool or float or callable
            This can be one of the following:

            - *None*: Picking is disabled for this artist (default).

            - A boolean: If *True* then picking will be enabled and the
              artist will fire a pick event if the mouse event is over
              the artist.

            - A float: If picker is a number it is interpreted as an
              epsilon tolerance in points and the artist will fire
              off an event if its data is within epsilon of the mouse
              event.  For some artists like lines and patch collections,
              the artist may provide additional data to the pick event
              that is generated, e.g., the indices of the data within
              epsilon of the pick event

            - A function: If picker is callable, it is a user supplied
              function which determines whether the artist is hit by the
              mouse event::

                hit, props = picker(artist, mouseevent)

              to determine the hit test.  if the mouse event is over the
              artist, return *hit=True* and props is a dictionary of
              properties you want added to the PickEvent attributes.
        """
        self._picker = picker

    def get_picker(self):
        """
        Return the picking behavior of the artist.

        The possible values are described in `.Artist.set_picker`.

        See Also
        --------
        .Artist.set_picker, .Artist.pickable, .Artist.pick
        """
        return self._picker

    def get_url(self):
        """Return the url."""
        return self._url

    def set_url(self, url):
        """
        Set the url for the artist.

        Parameters
        ----------
        url : str
        """
        self._url = url

    def get_gid(self):
        """Return the group id."""
        return self._gid

    def set_gid(self, gid):
        """
        Set the (group) id for the artist.

        Parameters
        ----------
        gid : str
        """
        self._gid = gid

    def get_snap(self):
        """
        Return the snap setting.

        See `.set_snap` for details.
        """
        if mpl.rcParams['path.snap']:
            return self._snap
        else:
            return False

    def set_snap(self, snap):
        """
        Set the snapping behavior.

        Snapping aligns positions with the pixel grid, which results in
        clearer images. For example, if a black line of 1px width was
        defined at a position in between two pixels, the resulting image
        would contain the interpolated value of that line in the pixel grid,
        which would be a grey value on both adjacent pixel positions. In
        contrast, snapping will move the line to the nearest integer pixel
        value, so that the resulting image will really contain a 1px wide
        black line.

        Snapping is currently only supported by the Agg and MacOSX backends.

        Parameters
        ----------
        snap : bool or None
            Possible values:

            - *True*: Snap vertices to the nearest pixel center.
            - *False*: Do not modify vertex positions.
            - *None*: (auto) If the path contains only rectilinear line
              segments, round to the nearest pixel center.
        """
        self._snap = snap
        self.stale = True

    def get_sketch_params(self):
        """
        Return the sketch parameters for the artist.

        Returns
        -------
        tuple or None

            A 3-tuple with the following elements:

            - *scale*: The amplitude of the wiggle perpendicular to the
              source line.
            - *length*: The length of the wiggle along the line.
            - *randomness*: The scale factor by which the length is
              shrunken or expanded.

            Returns *None* if no sketch parameters were set.
        """
        return self._sketch

    def set_sketch_params(self, scale=None, length=None, randomness=None):
        """
        Set the sketch parameters.

        Parameters
        ----------
        scale : float, optional
            The amplitude of the wiggle perpendicular to the source
            line, in pixels.  If scale is `None`, or not provided, no
            sketch filter will be provided.
        length : float, optional
             The length of the wiggle along the line, in pixels
             (default 128.0)
        randomness : float, optional
            The scale factor by which the length is shrunken or
            expanded (default 16.0)

            The PGF backend uses this argument as an RNG seed and not as
            described above. Using the same seed yields the same random shape.

            .. ACCEPTS: (scale: float, length: float, randomness: float)
        """
        if scale is None:
            self._sketch = None
        else:
            self._sketch = (scale, length or 128.0, randomness or 16.0)
        self.stale = True

    def set_path_effects(self, path_effects):
        """
        Set the path effects.

        Parameters
        ----------
        path_effects : list of `.AbstractPathEffect`
        """
        self._path_effects = path_effects
        self.stale = True

    def get_path_effects(self):
        return self._path_effects

    def get_figure(self, root=False):
        """
        Return the `.Figure` or `.SubFigure` instance the artist belongs to.

        Parameters
        ----------
        root : bool, default=False
            If False, return the (Sub)Figure this artist is on.  If True,
            return the root Figure for a nested tree of SubFigures.
        """
        if root and self._parent_figure is not None:
            return self._parent_figure.get_figure(root=True)

        return self._parent_figure

    def set_figure(self, fig):
        """
        Set the `.Figure` or `.SubFigure` instance the artist belongs to.

        Parameters
        ----------
        fig : `~matplotlib.figure.Figure` or `~matplotlib.figure.SubFigure`
        """
        # if this is a no-op just return
        if self._parent_figure is fig:
            return
        # if we currently have a figure (the case of both `self.figure`
        # and *fig* being none is taken care of above) we then user is
        # trying to change the figure an artist is associated with which
        # is not allowed for the same reason as adding the same instance
        # to more than one Axes
        if self._parent_figure is not None:
            raise RuntimeError("Can not put single artist in "
                               "more than one figure")
        self._parent_figure = fig
        if self._parent_figure and self._parent_figure is not self:
            self.pchanged()
        self.stale = True

    figure = property(get_figure, set_figure,
                      doc=("The (Sub)Figure that the artist is on.  For more "
                           "control, use the `get_figure` method."))

    def set_clip_box(self, clipbox):
        """
        Set the artist's clip `.Bbox`.

        Parameters
        ----------
        clipbox : `~matplotlib.transforms.BboxBase` or None
            Will typically be created from a `.TransformedBbox`. For instance,
            ``TransformedBbox(Bbox([[0, 0], [1, 1]]), ax.transAxes)`` is the default
            clipping for an artist added to an Axes.

        """
        _api.check_isinstance((BboxBase, None), clipbox=clipbox)
        if clipbox != self.clipbox:
            self.clipbox = clipbox
            self.pchanged()
            self.stale = True

    def set_clip_path(self, path, transform=None):
        """
        Set the artist's clip path.

        Parameters
        ----------
        path : `~matplotlib.patches.Patch` or `.Path` or `.TransformedPath` or None
            The clip path. If given a `.Path`, *transform* must be provided as
            well. If *None*, a previously set clip path is removed.
        transform : `~matplotlib.transforms.Transform`, optional
            Only used if *path* is a `.Path`, in which case the given `.Path`
            is converted to a `.TransformedPath` using *transform*.

        Notes
        -----
        For efficiency, if *path* is a `.Rectangle` this method will set the
        clipping box to the corresponding rectangle and set the clipping path
        to ``None``.

        For technical reasons (support of `~.Artist.set`), a tuple
        (*path*, *transform*) is also accepted as a single positional
        parameter.

        .. ACCEPTS: Patch or (Path, Transform) or None
        """
        from matplotlib.patches import Patch, Rectangle

        success = False
        if transform is None:
            if isinstance(path, Rectangle):
                self.clipbox = TransformedBbox(Bbox.unit(),
                                               path.get_transform())
                self._clippath = None
                success = True
            elif isinstance(path, Patch):
                self._clippath = TransformedPatchPath(path)
                success = True
            elif isinstance(path, tuple):
                path, transform = path

        if path is None:
            self._clippath = None
            success = True
        elif isinstance(path, Path):
            self._clippath = TransformedPath(path, transform)
            success = True
        elif isinstance(path, TransformedPatchPath):
            self._clippath = path
            success = True
        elif isinstance(path, TransformedPath):
            self._clippath = path
            success = True

        if not success:
            raise TypeError(
                "Invalid arguments to set_clip_path, of type "
                f"{type(path).__name__} and {type(transform).__name__}")
        # This may result in the callbacks being hit twice, but guarantees they
        # will be hit at least once.
        self.pchanged()
        self.stale = True

    def get_alpha(self):
        """
        Return the alpha value used for blending - not supported on all
        backends.
        """
        return self._alpha

    def get_visible(self):
        """Return the visibility."""
        return self._visible

    def get_animated(self):
        """Return whether the artist is animated."""
        return self._animated

    def get_in_layout(self):
        """
        Return boolean flag, ``True`` if artist is included in layout
        calculations.

        E.g. :ref:`constrainedlayout_guide`,
        `.Figure.tight_layout()`, and
        ``fig.savefig(fname, bbox_inches='tight')``.
        """
        return self._in_layout

    def _fully_clipped_to_axes(self):
        """
        Return a boolean flag, ``True`` if the artist is clipped to the Axes
        and can thus be skipped in layout calculations. Requires `get_clip_on`
        is True, one of `clip_box` or `clip_path` is set, ``clip_box.extents``
        is equivalent to ``ax.bbox.extents`` (if set), and ``clip_path._patch``
        is equivalent to ``ax.patch`` (if set).
        """
        # Note that ``clip_path.get_fully_transformed_path().get_extents()``
        # cannot be directly compared to ``axes.bbox.extents`` because the
        # extents may be undefined (i.e. equivalent to ``Bbox.null()``)
        # before the associated artist is drawn, and this method is meant
        # to determine whether ``axes.get_tightbbox()`` may bypass drawing
        clip_box = self.get_clip_box()
        clip_path = self.get_clip_path()
        return (self.axes is not None
                and self.get_clip_on()
                and (clip_box is not None or clip_path is not None)
                and (clip_box is None
                     or np.all(clip_box.extents == self.axes.bbox.extents))
                and (clip_path is None
                     or isinstance(clip_path, TransformedPatchPath)
                     and clip_path._patch is self.axes.patch))

    def get_clip_on(self):
        """Return whether the artist uses clipping."""
        return self._clipon

    def get_clip_box(self):
        """Return the clipbox."""
        return self.clipbox

    def get_clip_path(self):
        """Return the clip path."""
        return self._clippath

    def get_transformed_clip_path_and_affine(self):
        """
        Return the clip path with the non-affine part of its
        transformation applied, and the remaining affine part of its
        transformation.
        """
        if self._clippath is not None:
            return self._clippath.get_transformed_path_and_affine()
        return None, None

    def set_clip_on(self, b):
        """
        Set whether the artist uses clipping.

        When False, artists will be visible outside the Axes which
        can lead to unexpected results.

        Parameters
        ----------
        b : bool
        """
        self._clipon = b
        # This may result in the callbacks being hit twice, but ensures they
        # are hit at least once
        self.pchanged()
        self.stale = True

    def _set_gc_clip(self, gc):
        """Set the clip properly for the gc."""
        if self._clipon:
            if self.clipbox is not None:
                gc.set_clip_rectangle(self.clipbox)
            gc.set_clip_path(self._clippath)
        else:
            gc.set_clip_rectangle(None)
            gc.set_clip_path(None)

    def get_rasterized(self):
        """Return whether the artist is to be rasterized."""
        return self._rasterized

    def set_rasterized(self, rasterized):
        """
        Force rasterized (bitmap) drawing for vector graphics output.

        Rasterized drawing is not supported by all artists. If you try to
        enable this on an artist that does not support it, the command has no
        effect and a warning will be issued.

        This setting is ignored for pixel-based output.

        See also :doc:`/gallery/misc/rasterization_demo`.

        Parameters
        ----------
        rasterized : bool
        """
        supports_rasterization = getattr(self.draw,
                                         "_supports_rasterization", False)
        if rasterized and not supports_rasterization:
            _api.warn_external(f"Rasterization of '{self}' will be ignored")

        self._rasterized = rasterized

    def get_agg_filter(self):
        """Return filter function to be used for agg filter."""
        return self._agg_filter

    def set_agg_filter(self, filter_func):
        """
        Set the agg filter.

        Parameters
        ----------
        filter_func : callable
            A filter function, which takes a (m, n, depth) float array
            and a dpi value, and returns a (m, n, depth) array and two
            offsets from the bottom left corner of the image

            .. ACCEPTS: a filter function, which takes a (m, n, 3) float array
                and a dpi value, and returns a (m, n, 3) array and two offsets
                from the bottom left corner of the image
        """
        self._agg_filter = filter_func
        self.stale = True

    def draw(self, renderer):
        """
        Draw the Artist (and its children) using the given renderer.

        This has no effect if the artist is not visible (`.Artist.get_visible`
        returns False).

        Parameters
        ----------
        renderer : `~matplotlib.backend_bases.RendererBase` subclass.

        Notes
        -----
        This method is overridden in the Artist subclasses.
        """
        if not self.get_visible():
            return
        self.stale = False

    def set_alpha(self, alpha):
        """
        Set the alpha value used for blending - not supported on all backends.

        Parameters
        ----------
        alpha : float or None
            *alpha* must be within the 0-1 range, inclusive.
        """
        if alpha is not None and not isinstance(alpha, Real):
            raise TypeError(
                f'alpha must be numeric or None, not {type(alpha)}')
        if alpha is not None and not (0 <= alpha <= 1):
            raise ValueError(f'alpha ({alpha}) is outside 0-1 range')
        if alpha != self._alpha:
            self._alpha = alpha
            self.pchanged()
            self.stale = True

    def _set_alpha_for_array(self, alpha):
        """
        Set the alpha value used for blending - not supported on all backends.

        Parameters
        ----------
        alpha : array-like or float or None
            All values must be within the 0-1 range, inclusive.
            Masked values and nans are not supported.
        """
        if isinstance(alpha, str):
            raise TypeError("alpha must be numeric or None, not a string")
        if not np.iterable(alpha):
            Artist.set_alpha(self, alpha)
            return
        alpha = np.asarray(alpha)
        if not (0 <= alpha.min() and alpha.max() <= 1):
            raise ValueError('alpha must be between 0 and 1, inclusive, '
                             f'but min is {alpha.min()}, max is {alpha.max()}')
        self._alpha = alpha
        self.pchanged()
        self.stale = True

    def set_visible(self, b):
        """
        Set the artist's visibility.

        Parameters
        ----------
        b : bool
        """
        if b != self._visible:
            self._visible = b
            self.pchanged()
            self.stale = True

    def set_animated(self, b):
        """
        Set whether the artist is intended to be used in an animation.

        If True, the artist is excluded from regular drawing of the figure.
        You have to call `.Figure.draw_artist` / `.Axes.draw_artist`
        explicitly on the artist. This approach is used to speed up animations
        using blitting.

        See also `matplotlib.animation` and
        :ref:`blitting`.

        Parameters
        ----------
        b : bool
        """
        if self._animated != b:
            self._animated = b
            self.pchanged()

    def set_in_layout(self, in_layout):
        """
        Set if artist is to be included in layout calculations,
        E.g. :ref:`constrainedlayout_guide`,
        `.Figure.tight_layout()`, and
        ``fig.savefig(fname, bbox_inches='tight')``.

        Parameters
        ----------
        in_layout : bool
        """
        self._in_layout = in_layout

    def get_label(self):
        """Return the label used for this artist in the legend."""
        return self._label

    def set_label(self, s):
        """
        Set a label that will be displayed in the legend.

        Parameters
        ----------
        s : object
            *s* will be converted to a string by calling `str`.
        """
        label = str(s) if s is not None else None
        if label != self._label:
            self._label = label
            self.pchanged()
            self.stale = True

    def get_zorder(self):
        """Return the artist's zorder."""
        return self.zorder

    def set_zorder(self, level):
        """
        Set the zorder for the artist.  Artists with lower zorder
        values are drawn first.

        Parameters
        ----------
        level : float
        """
        if level is None:
            level = self.__class__.zorder
        if level != self.zorder:
            self.zorder = level
            self.pchanged()
            self.stale = True

    @property
    def sticky_edges(self):
        """
        ``x`` and ``y`` sticky edge lists for autoscaling.

        When performing autoscaling, if a data limit coincides with a value in
        the corresponding sticky_edges list, then no margin will be added--the
        view limit "sticks" to the edge. A typical use case is histograms,
        where one usually expects no margin on the bottom edge (0) of the
        histogram.

        Moreover, margin expansion "bumps" against sticky edges and cannot
        cross them.  For example, if the upper data limit is 1.0, the upper
        view limit computed by simple margin application is 1.2, but there is a
        sticky edge at 1.1, then the actual upper view limit will be 1.1.

        This attribute cannot be assigned to; however, the ``x`` and ``y``
        lists can be modified in place as needed.

        Examples
        --------
        >>> artist.sticky_edges.x[:] = (xmin, xmax)
        >>> artist.sticky_edges.y[:] = (ymin, ymax)

        """
        return self._sticky_edges

    def update_from(self, other):
        """Copy properties from *other* to *self*."""
        self._transform = other._transform
        self._transformSet = other._transformSet
        self._visible = other._visible
        self._alpha = other._alpha
        self.clipbox = other.clipbox
        self._clipon = other._clipon
        self._clippath = other._clippath
        self._label = other._label
        self._sketch = other._sketch
        self._path_effects = other._path_effects
        self.sticky_edges.x[:] = other.sticky_edges.x.copy()
        self.sticky_edges.y[:] = other.sticky_edges.y.copy()
        self.pchanged()
        self.stale = True

    def properties(self):
        """Return a dictionary of all the properties of the artist."""
        return ArtistInspector(self).properties()

    def _update_props(self, props, errfmt):
        """
        Helper for `.Artist.set` and `.Artist.update`.

        *errfmt* is used to generate error messages for invalid property
        names; it gets formatted with ``type(self)`` for "{cls}" and the
        property name for "{prop_name}".
        """
        ret = []
        with cbook._setattr_cm(self, eventson=False):
            for k, v in props.items():
                # Allow attributes we want to be able to update through
                # art.update, art.set, setp.
                if k == "axes":
                    ret.append(setattr(self, k, v))
                else:
                    func = getattr(self, f"set_{k}", None)
                    if not callable(func):
                        raise AttributeError(
                            errfmt.format(cls=type(self), prop_name=k),
                            name=k)
                    ret.append(func(v))
        if ret:
            self.pchanged()
            self.stale = True
        return ret

    def update(self, props):
        """
        Update this artist's properties from the dict *props*.

        Parameters
        ----------
        props : dict
        """
        return self._update_props(
            props, "{cls.__name__!r} object has no property {prop_name!r}")

    def _internal_update(self, kwargs):
        """
        Update artist properties without prenormalizing them, but generating
        errors as if calling `set`.

        The lack of prenormalization is to maintain backcompatibility.
        """
        return self._update_props(
            kwargs, "{cls.__name__}.set() got an unexpected keyword argument "
            "{prop_name!r}")

    def set(self, **kwargs):
        # docstring and signature are auto-generated via
        # Artist._update_set_signature_and_docstring() at the end of the
        # module.
        return self._internal_update(cbook.normalize_kwargs(kwargs, self))

    @contextlib.contextmanager
    def _cm_set(self, **kwargs):
        """
        `.Artist.set` context-manager that restores original values at exit.
        """
        orig_vals = {k: getattr(self, f"get_{k}")() for k in kwargs}
        try:
            self.set(**kwargs)
            yield
        finally:
            self.set(**orig_vals)

    def findobj(self, match=None, include_self=True):
        """
        Find artist objects.

        Recursively find all `.Artist` instances contained in the artist.

        Parameters
        ----------
        match
            A filter criterion for the matches. This can be

            - *None*: Return all objects contained in artist.
            - A function with signature ``def match(artist: Artist) -> bool``.
              The result will only contain artists for which the function
              returns *True*.
            - A class instance: e.g., `.Line2D`. The result will only contain
              artists of this class or its subclasses (``isinstance`` check).

        include_self : bool
            Include *self* in the list to be checked for a match.

        Returns
        -------
        list of `.Artist`

        """
        if match is None:  # always return True
            def matchfunc(x):
                return True
        elif isinstance(match, type) and issubclass(match, Artist):
            def matchfunc(x):
                return isinstance(x, match)
        elif callable(match):
            matchfunc = match
        else:
            raise ValueError('match must be None, a matplotlib.artist.Artist '
                             'subclass, or a callable')

        artists = reduce(operator.iadd,
                         [c.findobj(matchfunc) for c in self.get_children()], [])
        if include_self and matchfunc(self):
            artists.append(self)
        return artists

    def get_cursor_data(self, event):
        """
        Return the cursor data for a given event.

        .. note::
            This method is intended to be overridden by artist subclasses.
            As an end-user of Matplotlib you will most likely not call this
            method yourself.

        Cursor data can be used by Artists to provide additional context
        information for a given event. The default implementation just returns
        *None*.

        Subclasses can override the method and return arbitrary data. However,
        when doing so, they must ensure that `.format_cursor_data` can convert
        the data to a string representation.

        The only current use case is displaying the z-value of an `.AxesImage`
        in the status bar of a plot window, while moving the mouse.

        Parameters
        ----------
        event : `~matplotlib.backend_bases.MouseEvent`

        See Also
        --------
        format_cursor_data

        """
        return None

    def format_cursor_data(self, data):
        """
        Return a string representation of *data*.

        .. note::
            This method is intended to be overridden by artist subclasses.
            As an end-user of Matplotlib you will most likely not call this
            method yourself.

        The default implementation converts ints and floats and arrays of ints
        and floats into a comma-separated string enclosed in square brackets,
        unless the artist has an associated colorbar, in which case scalar
        values are formatted using the colorbar's formatter.

        See Also
        --------
        get_cursor_data
        """
        if np.ndim(data) == 0 and hasattr(self, "_format_cursor_data_override"):
            # workaround for ScalarMappable to be able to define its own
            # format_cursor_data(). See ScalarMappable._format_cursor_data_override
            # for details.
            return self._format_cursor_data_override(data)
        else:
            try:
                data[0]
            except (TypeError, IndexError):
                data = [data]
            data_str = ', '.join(f'{item:0.3g}' for item in data
                                 if isinstance(item, Number))
            return "[" + data_str + "]"

    def get_mouseover(self):
        """
        Return whether this artist is queried for custom context information
        when the mouse cursor moves over it.
        """
        return self._mouseover

    def set_mouseover(self, mouseover):
        """
        Set whether this artist is queried for custom context information when
        the mouse cursor moves over it.

        Parameters
        ----------
        mouseover : bool

        See Also
        --------
        get_cursor_data
        .ToolCursorPosition
        .NavigationToolbar2
        """
        self._mouseover = bool(mouseover)
        ax = self.axes
        if ax:
            if self._mouseover:
                ax._mouseover_set.add(self)
            else:
                ax._mouseover_set.discard(self)

    mouseover = property(get_mouseover, set_mouseover)  # backcompat.


def _get_tightbbox_for_layout_only(obj, *args, **kwargs):
    """
    Matplotlib's `.Axes.get_tightbbox` and `.Axis.get_tightbbox` support a
    *for_layout_only* kwarg; this helper tries to use the kwarg but skips it
    when encountering third-party subclasses that do not support it.
    """
    try:
        return obj.get_tightbbox(*args, **{**kwargs, "for_layout_only": True})
    except TypeError:
        return obj.get_tightbbox(*args, **kwargs)


class ArtistInspector:
    """
    A helper class to inspect an `~matplotlib.artist.Artist` and return
    information about its settable properties and their current values.
    """

    def __init__(self, o):
        r"""
        Initialize the artist inspector with an `Artist` or an iterable of
        `Artist`\s.  If an iterable is used, we assume it is a homogeneous
        sequence (all `Artist`\s are of the same type) and it is your
        responsibility to make sure this is so.
        """
        if not isinstance(o, Artist):
            if np.iterable(o):
                o = list(o)
                if len(o):
                    o = o[0]

        self.oorig = o
        if not isinstance(o, type):
            o = type(o)
        self.o = o

        self.aliasd = self.get_aliases()

    def get_aliases(self):
        """
        Get a dict mapping property fullnames to sets of aliases for each alias
        in the :class:`~matplotlib.artist.ArtistInspector`.

        e.g., for lines::

          {'markerfacecolor': {'mfc'},
           'linewidth'      : {'lw'},
          }
        """
        names = [name for name in dir(self.o)
                 if name.startswith(('set_', 'get_'))
                    and callable(getattr(self.o, name))]
        aliases = {}
        for name in names:
            func = getattr(self.o, name)
            if not self.is_alias(func):
                continue
            propname = re.search(f"`({name[:4]}.*)`",  # get_.*/set_.*
                                 inspect.getdoc(func)).group(1)
            aliases.setdefault(propname[4:], set()).add(name[4:])
        return aliases

    _get_valid_values_regex = re.compile(
        r"\n\s*(?:\.\.\s+)?ACCEPTS:\s*((?:.|\n)*?)(?:$|(?:\n\n))"
    )

    def get_valid_values(self, attr):
        """
        Get the legal arguments for the setter associated with *attr*.

        This is done by querying the docstring of the setter for a line that
        begins with "ACCEPTS:" or ".. ACCEPTS:", and then by looking for a
        numpydoc-style documentation for the setter's first argument.
        """

        name = 'set_%s' % attr
        if not hasattr(self.o, name):
            raise AttributeError(f'{self.o} has no function {name}')
        func = getattr(self.o, name)

        if hasattr(func, '_kwarg_doc'):
            return func._kwarg_doc

        docstring = inspect.getdoc(func)
        if docstring is None:
            return 'unknown'

        if docstring.startswith('Alias for '):
            return None

        match = self._get_valid_values_regex.search(docstring)
        if match is not None:
            return re.sub("\n *", " ", match.group(1))

        # Much faster than list(inspect.signature(func).parameters)[1],
        # although barely relevant wrt. matplotlib's total import time.
        param_name = func.__code__.co_varnames[1]
        # We could set the presence * based on whether the parameter is a
        # varargs (it can't be a varkwargs) but it's not really worth it.
        match = re.search(fr"(?m)^ *\*?{param_name} : (.+)", docstring)
        if match:
            return match.group(1)

        return 'unknown'

    def _replace_path(self, source_class):
        """
        Changes the full path to the public API path that is used
        in sphinx. This is needed for links to work.
        """
        replace_dict = {'_base._AxesBase': 'Axes',
                        '_axes.Axes': 'Axes'}
        for key, value in replace_dict.items():
            source_class = source_class.replace(key, value)
        return source_class

    def get_setters(self):
        """
        Get the attribute strings with setters for object.

        For example, for a line, return ``['markerfacecolor', 'linewidth',
        ....]``.
        """
        setters = []
        for name in dir(self.o):
            if not name.startswith('set_'):
                continue
            func = getattr(self.o, name)
            if (not callable(func)
                    or self.number_of_parameters(func) < 2
                    or self.is_alias(func)):
                continue
            setters.append(name[4:])
        return setters

    @staticmethod
    @cache
    def number_of_parameters(func):
        """Return number of parameters of the callable *func*."""
        return len(inspect.signature(func).parameters)

    @staticmethod
    @cache
    def is_alias(method):
        """
        Return whether the object *method* is an alias for another method.
        """

        ds = inspect.getdoc(method)
        if ds is None:
            return False

        return ds.startswith('Alias for ')

    def aliased_name(self, s):
        """
        Return 'PROPNAME or alias' if *s* has an alias, else return 'PROPNAME'.

        For example, for the line markerfacecolor property, which has an
        alias, return 'markerfacecolor or mfc' and for the transform
        property, which does not, return 'transform'.
        """
        aliases = ''.join(' or %s' % x for x in sorted(self.aliasd.get(s, [])))
        return s + aliases

    _NOT_LINKABLE = {
        # A set of property setter methods that are not available in our
        # current docs. This is a workaround used to prevent trying to link
        # these setters which would lead to "target reference not found"
        # warnings during doc build.
        'matplotlib.image._ImageBase.set_alpha',
        'matplotlib.image._ImageBase.set_array',
        'matplotlib.image._ImageBase.set_data',
        'matplotlib.image._ImageBase.set_filternorm',
        'matplotlib.image._ImageBase.set_filterrad',
        'matplotlib.image._ImageBase.set_interpolation',
        'matplotlib.image._ImageBase.set_interpolation_stage',
        'matplotlib.image._ImageBase.set_resample',
        'matplotlib.text._AnnotationBase.set_annotation_clip',
    }

    def aliased_name_rest(self, s, target):
        """
        Return 'PROPNAME or alias' if *s* has an alias, else return 'PROPNAME',
        formatted for reST.

        For example, for the line markerfacecolor property, which has an
        alias, return 'markerfacecolor or mfc' and for the transform
        property, which does not, return 'transform'.
        """
        # workaround to prevent "reference target not found"
        if target in self._NOT_LINKABLE:
            return f'``{s}``'

        aliases = ''.join(
            f' or :meth:`{a} <{target}>`' for a in sorted(self.aliasd.get(s, [])))
        return f':meth:`{s} <{target}>`{aliases}'

    def pprint_setters(self, prop=None, leadingspace=2):
        """
        If *prop* is *None*, return a list of strings of all settable
        properties and their valid values.

        If *prop* is not *None*, it is a valid property name and that
        property will be returned as a string of property : valid
        values.
        """
        if leadingspace:
            pad = ' ' * leadingspace
        else:
            pad = ''
        if prop is not None:
            accepts = self.get_valid_values(prop)
            return f'{pad}{prop}: {accepts}'

        lines = []
        for prop in sorted(self.get_setters()):
            accepts = self.get_valid_values(prop)
            name = self.aliased_name(prop)
            lines.append(f'{pad}{name}: {accepts}')
        return lines

    def pprint_setters_rest(self, prop=None, leadingspace=4):
        """
        If *prop* is *None*, return a list of reST-formatted strings of all
        settable properties and their valid values.

        If *prop* is not *None*, it is a valid property name and that
        property will be returned as a string of "property : valid"
        values.
        """
        if leadingspace:
            pad = ' ' * leadingspace
        else:
            pad = ''
        if prop is not None:
            accepts = self.get_valid_values(prop)
            return f'{pad}{prop}: {accepts}'

        prop_and_qualnames = []
        for prop in sorted(self.get_setters()):
            # Find the parent method which actually provides the docstring.
            for cls in self.o.__mro__:
                method = getattr(cls, f"set_{prop}", None)
                if method and method.__doc__ is not None:
                    break
            else:  # No docstring available.
                method = getattr(self.o, f"set_{prop}")
            prop_and_qualnames.append(
                (prop, f"{method.__module__}.{method.__qualname__}"))

        names = [self.aliased_name_rest(prop, target)
                 .replace('_base._AxesBase', 'Axes')
                 .replace('_axes.Axes', 'Axes')
                 for prop, target in prop_and_qualnames]
        accepts = [self.get_valid_values(prop)
                   for prop, _ in prop_and_qualnames]

        col0_len = max(len(n) for n in names)
        col1_len = max(len(a) for a in accepts)
        table_formatstr = pad + '   ' + '=' * col0_len + '   ' + '=' * col1_len

        return [
            '',
            pad + '.. table::',
            pad + '   :class: property-table',
            '',
            table_formatstr,
            pad + '   ' + 'Property'.ljust(col0_len)
            + '   ' + 'Description'.ljust(col1_len),
            table_formatstr,
            *[pad + '   ' + n.ljust(col0_len) + '   ' + a.ljust(col1_len)
              for n, a in zip(names, accepts)],
            table_formatstr,
            '',
        ]

    def properties(self):
        """Return a dictionary mapping property name -> value."""
        o = self.oorig
        getters = [name for name in dir(o)
                   if name.startswith('get_') and callable(getattr(o, name))]
        getters.sort()
        d = {}
        for name in getters:
            func = getattr(o, name)
            if self.is_alias(func):
                continue
            try:
                with warnings.catch_warnings():
                    warnings.simplefilter('ignore')
                    val = func()
            except Exception:
                continue
            else:
                d[name[4:]] = val
        return d

    def pprint_getters(self):
        """Return the getters and actual values as list of strings."""
        lines = []
        for name, val in sorted(self.properties().items()):
            if getattr(val, 'shape', ()) != () and len(val) > 6:
                s = str(val[:6]) + '...'
            else:
                s = str(val)
            s = s.replace('\n', ' ')
            if len(s) > 50:
                s = s[:50] + '...'
            name = self.aliased_name(name)
            lines.append(f'    {name} = {s}')
        return lines


def getp(obj, property=None):
    """
    Return the value of an `.Artist`'s *property*, or print all of them.

    Parameters
    ----------
    obj : `~matplotlib.artist.Artist`
        The queried artist; e.g., a `.Line2D`, a `.Text`, or an `~.axes.Axes`.

    property : str or None, default: None
        If *property* is 'somename', this function returns
        ``obj.get_somename()``.

        If it's None (or unset), it *prints* all gettable properties from
        *obj*.  Many properties have aliases for shorter typing, e.g. 'lw' is
        an alias for 'linewidth'.  In the output, aliases and full property
        names will be listed as:

          property or alias = value

        e.g.:

          linewidth or lw = 2

    See Also
    --------
    setp
    """
    if property is None:
        insp = ArtistInspector(obj)
        ret = insp.pprint_getters()
        print('\n'.join(ret))
        return
    return getattr(obj, 'get_' + property)()

# alias
get = getp


def setp(obj, *args, file=None, **kwargs):
    """
    Set one or more properties on an `.Artist`, or list allowed values.

    Parameters
    ----------
    obj : `~matplotlib.artist.Artist` or list of `.Artist`
        The artist(s) whose properties are being set or queried.  When setting
        properties, all artists are affected; when querying the allowed values,
        only the first instance in the sequence is queried.

        For example, two lines can be made thicker and red with a single call:

        >>> x = arange(0, 1, 0.01)
        >>> lines = plot(x, sin(2*pi*x), x, sin(4*pi*x))
        >>> setp(lines, linewidth=2, color='r')

    file : file-like, default: `sys.stdout`
        Where `setp` writes its output when asked to list allowed values.

        >>> with open('output.log') as file:
        ...     setp(line, file=file)

        The default, ``None``, means `sys.stdout`.

    *args, **kwargs
        The properties to set.  The following combinations are supported:

        - Set the linestyle of a line to be dashed:

          >>> line, = plot([1, 2, 3])
          >>> setp(line, linestyle='--')

        - Set multiple properties at once:

          >>> setp(line, linewidth=2, color='r')

        - List allowed values for a line's linestyle:

          >>> setp(line, 'linestyle')
          linestyle: {'-', '--', '-.', ':', '', (offset, on-off-seq), ...}

        - List all properties that can be set, and their allowed values:

          >>> setp(line)
          agg_filter: a filter function, ...
          [long output listing omitted]

        `setp` also supports MATLAB style string/value pairs.  For example, the
        following are equivalent:

        >>> setp(lines, 'linewidth', 2, 'color', 'r')  # MATLAB style
        >>> setp(lines, linewidth=2, color='r')        # Python style

    See Also
    --------
    getp
    """

    if isinstance(obj, Artist):
        objs = [obj]
    else:
        objs = list(cbook.flatten(obj))

    if not objs:
        return

    insp = ArtistInspector(objs[0])

    if not kwargs and len(args) < 2:
        if args:
            print(insp.pprint_setters(prop=args[0]), file=file)
        else:
            print('\n'.join(insp.pprint_setters()), file=file)
        return

    if len(args) % 2:
        raise ValueError('The set args must be string, value pairs')

    funcvals = dict(zip(args[::2], args[1::2]))
    ret = [o.update(funcvals) for o in objs] + [o.set(**kwargs) for o in objs]
    return list(cbook.flatten(ret))


def kwdoc(artist):
    r"""
    Inspect an `~matplotlib.artist.Artist` class (using `.ArtistInspector`) and
    return information about its settable properties and their current values.

    Parameters
    ----------
    artist : `~matplotlib.artist.Artist` or an iterable of `Artist`\s

    Returns
    -------
    str
        The settable properties of *artist*, as plain text if
        :rc:`docstring.hardcopy` is False and as a rst table (intended for
        use in Sphinx) if it is True.
    """
    ai = ArtistInspector(artist)
    return ('\n'.join(ai.pprint_setters_rest(leadingspace=4))
            if mpl.rcParams['docstring.hardcopy'] else
            'Properties:\n' + '\n'.join(ai.pprint_setters(leadingspace=4)))

# We defer this to the end of them module, because it needs ArtistInspector
# to be defined.
Artist._update_set_signature_and_docstring()

# === NexusCore/openenv\Lib\site-packages\anthropic\resources\beta\messages\messages.py ===
# File generated from our OpenAPI spec by Stainless. See CONTRIBUTING.md for details.

from __future__ import annotations

from typing import List, Union, Iterable
from typing_extensions import Literal, overload

import httpx

from .... import _legacy_response
from .batches import (
    Batches,
    AsyncBatches,
    BatchesWithRawResponse,
    AsyncBatchesWithRawResponse,
    BatchesWithStreamingResponse,
    AsyncBatchesWithStreamingResponse,
)
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
from ....types.beta import message_create_params
from ...._base_client import make_request_options
from ....types.model_param import ModelParam
from ....types.beta.beta_message import BetaMessage
from ....types.anthropic_beta_param import AnthropicBetaParam
from ....types.beta.beta_message_param import BetaMessageParam
from ....types.beta.beta_metadata_param import BetaMetadataParam
from ....types.beta.beta_text_block_param import BetaTextBlockParam
from ....types.beta.beta_tool_union_param import BetaToolUnionParam
from ....types.beta.beta_tool_choice_param import BetaToolChoiceParam
from ....types.beta.beta_raw_message_stream_event import BetaRawMessageStreamEvent

__all__ = ["Messages", "AsyncMessages"]


class Messages(SyncAPIResource):
    @cached_property
    def batches(self) -> Batches:
        return Batches(self._client)

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
        messages: Iterable[BetaMessageParam],
        model: ModelParam,
        metadata: BetaMetadataParam | NotGiven = NOT_GIVEN,
        stop_sequences: List[str] | NotGiven = NOT_GIVEN,
        stream: Literal[False] | NotGiven = NOT_GIVEN,
        system: Union[str, Iterable[BetaTextBlockParam]] | NotGiven = NOT_GIVEN,
        temperature: float | NotGiven = NOT_GIVEN,
        tool_choice: BetaToolChoiceParam | NotGiven = NOT_GIVEN,
        tools: Iterable[BetaToolUnionParam] | NotGiven = NOT_GIVEN,
        top_k: int | NotGiven = NOT_GIVEN,
        top_p: float | NotGiven = NOT_GIVEN,
        betas: List[AnthropicBetaParam] | NotGiven = NOT_GIVEN,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> BetaMessage:
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
        messages: Iterable[BetaMessageParam],
        model: ModelParam,
        stream: Literal[True],
        metadata: BetaMetadataParam | NotGiven = NOT_GIVEN,
        stop_sequences: List[str] | NotGiven = NOT_GIVEN,
        system: Union[str, Iterable[BetaTextBlockParam]] | NotGiven = NOT_GIVEN,
        temperature: float | NotGiven = NOT_GIVEN,
        tool_choice: BetaToolChoiceParam | NotGiven = NOT_GIVEN,
        tools: Iterable[BetaToolUnionParam] | NotGiven = NOT_GIVEN,
        top_k: int | NotGiven = NOT_GIVEN,
        top_p: float | NotGiven = NOT_GIVEN,
        betas: List[AnthropicBetaParam] | NotGiven = NOT_GIVEN,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> Stream[BetaRawMessageStreamEvent]:
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
        messages: Iterable[BetaMessageParam],
        model: ModelParam,
        stream: bool,
        metadata: BetaMetadataParam | NotGiven = NOT_GIVEN,
        stop_sequences: List[str] | NotGiven = NOT_GIVEN,
        system: Union[str, Iterable[BetaTextBlockParam]] | NotGiven = NOT_GIVEN,
        temperature: float | NotGiven = NOT_GIVEN,
        tool_choice: BetaToolChoiceParam | NotGiven = NOT_GIVEN,
        tools: Iterable[BetaToolUnionParam] | NotGiven = NOT_GIVEN,
        top_k: int | NotGiven = NOT_GIVEN,
        top_p: float | NotGiven = NOT_GIVEN,
        betas: List[AnthropicBetaParam] | NotGiven = NOT_GIVEN,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> BetaMessage | Stream[BetaRawMessageStreamEvent]:
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
        messages: Iterable[BetaMessageParam],
        model: ModelParam,
        metadata: BetaMetadataParam | NotGiven = NOT_GIVEN,
        stop_sequences: List[str] | NotGiven = NOT_GIVEN,
        stream: Literal[False] | Literal[True] | NotGiven = NOT_GIVEN,
        system: Union[str, Iterable[BetaTextBlockParam]] | NotGiven = NOT_GIVEN,
        temperature: float | NotGiven = NOT_GIVEN,
        tool_choice: BetaToolChoiceParam | NotGiven = NOT_GIVEN,
        tools: Iterable[BetaToolUnionParam] | NotGiven = NOT_GIVEN,
        top_k: int | NotGiven = NOT_GIVEN,
        top_p: float | NotGiven = NOT_GIVEN,
        betas: List[AnthropicBetaParam] | NotGiven = NOT_GIVEN,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> BetaMessage | Stream[BetaRawMessageStreamEvent]:
        if not is_given(timeout) and self._client.timeout == DEFAULT_TIMEOUT:
            timeout = 600
        extra_headers = {
            **strip_not_given({"anthropic-beta": ",".join(str(e) for e in betas) if is_given(betas) else NOT_GIVEN}),
            **(extra_headers or {}),
        }
        return self._post(
            "/v1/messages?beta=true",
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
            cast_to=BetaMessage,
            stream=stream or False,
            stream_cls=Stream[BetaRawMessageStreamEvent],
        )


class AsyncMessages(AsyncAPIResource):
    @cached_property
    def batches(self) -> AsyncBatches:
        return AsyncBatches(self._client)

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
        messages: Iterable[BetaMessageParam],
        model: ModelParam,
        metadata: BetaMetadataParam | NotGiven = NOT_GIVEN,
        stop_sequences: List[str] | NotGiven = NOT_GIVEN,
        stream: Literal[False] | NotGiven = NOT_GIVEN,
        system: Union[str, Iterable[BetaTextBlockParam]] | NotGiven = NOT_GIVEN,
        temperature: float | NotGiven = NOT_GIVEN,
        tool_choice: BetaToolChoiceParam | NotGiven = NOT_GIVEN,
        tools: Iterable[BetaToolUnionParam] | NotGiven = NOT_GIVEN,
        top_k: int | NotGiven = NOT_GIVEN,
        top_p: float | NotGiven = NOT_GIVEN,
        betas: List[AnthropicBetaParam] | NotGiven = NOT_GIVEN,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> BetaMessage:
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
        messages: Iterable[BetaMessageParam],
        model: ModelParam,
        stream: Literal[True],
        metadata: BetaMetadataParam | NotGiven = NOT_GIVEN,
        stop_sequences: List[str] | NotGiven = NOT_GIVEN,
        system: Union[str, Iterable[BetaTextBlockParam]] | NotGiven = NOT_GIVEN,
        temperature: float | NotGiven = NOT_GIVEN,
        tool_choice: BetaToolChoiceParam | NotGiven = NOT_GIVEN,
        tools: Iterable[BetaToolUnionParam] | NotGiven = NOT_GIVEN,
        top_k: int | NotGiven = NOT_GIVEN,
        top_p: float | NotGiven = NOT_GIVEN,
        betas: List[AnthropicBetaParam] | NotGiven = NOT_GIVEN,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> AsyncStream[BetaRawMessageStreamEvent]:
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
        messages: Iterable[BetaMessageParam],
        model: ModelParam,
        stream: bool,
        metadata: BetaMetadataParam | NotGiven = NOT_GIVEN,
        stop_sequences: List[str] | NotGiven = NOT_GIVEN,
        system: Union[str, Iterable[BetaTextBlockParam]] | NotGiven = NOT_GIVEN,
        temperature: float | NotGiven = NOT_GIVEN,
        tool_choice: BetaToolChoiceParam | NotGiven = NOT_GIVEN,
        tools: Iterable[BetaToolUnionParam] | NotGiven = NOT_GIVEN,
        top_k: int | NotGiven = NOT_GIVEN,
        top_p: float | NotGiven = NOT_GIVEN,
        betas: List[AnthropicBetaParam] | NotGiven = NOT_GIVEN,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> BetaMessage | AsyncStream[BetaRawMessageStreamEvent]:
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
        messages: Iterable[BetaMessageParam],
        model: ModelParam,
        metadata: BetaMetadataParam | NotGiven = NOT_GIVEN,
        stop_sequences: List[str] | NotGiven = NOT_GIVEN,
        stream: Literal[False] | Literal[True] | NotGiven = NOT_GIVEN,
        system: Union[str, Iterable[BetaTextBlockParam]] | NotGiven = NOT_GIVEN,
        temperature: float | NotGiven = NOT_GIVEN,
        tool_choice: BetaToolChoiceParam | NotGiven = NOT_GIVEN,
        tools: Iterable[BetaToolUnionParam] | NotGiven = NOT_GIVEN,
        top_k: int | NotGiven = NOT_GIVEN,
        top_p: float | NotGiven = NOT_GIVEN,
        betas: List[AnthropicBetaParam] | NotGiven = NOT_GIVEN,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> BetaMessage | AsyncStream[BetaRawMessageStreamEvent]:
        if not is_given(timeout) and self._client.timeout == DEFAULT_TIMEOUT:
            timeout = 600
        extra_headers = {
            **strip_not_given({"anthropic-beta": ",".join(str(e) for e in betas) if is_given(betas) else NOT_GIVEN}),
            **(extra_headers or {}),
        }
        return await self._post(
            "/v1/messages?beta=true",
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
            cast_to=BetaMessage,
            stream=stream or False,
            stream_cls=AsyncStream[BetaRawMessageStreamEvent],
        )


class MessagesWithRawResponse:
    def __init__(self, messages: Messages) -> None:
        self._messages = messages

        self.create = _legacy_response.to_raw_response_wrapper(
            messages.create,
        )

    @cached_property
    def batches(self) -> BatchesWithRawResponse:
        return BatchesWithRawResponse(self._messages.batches)


class AsyncMessagesWithRawResponse:
    def __init__(self, messages: AsyncMessages) -> None:
        self._messages = messages

        self.create = _legacy_response.async_to_raw_response_wrapper(
            messages.create,
        )

    @cached_property
    def batches(self) -> AsyncBatchesWithRawResponse:
        return AsyncBatchesWithRawResponse(self._messages.batches)


class MessagesWithStreamingResponse:
    def __init__(self, messages: Messages) -> None:
        self._messages = messages

        self.create = to_streamed_response_wrapper(
            messages.create,
        )

    @cached_property
    def batches(self) -> BatchesWithStreamingResponse:
        return BatchesWithStreamingResponse(self._messages.batches)


class AsyncMessagesWithStreamingResponse:
    def __init__(self, messages: AsyncMessages) -> None:
        self._messages = messages

        self.create = async_to_streamed_response_wrapper(
            messages.create,
        )

    @cached_property
    def batches(self) -> AsyncBatchesWithStreamingResponse:
        return AsyncBatchesWithStreamingResponse(self._messages.batches)

# === NexusCore/openenv\Lib\site-packages\dateutil\tz\tz.py ===
# -*- coding: utf-8 -*-
"""
This module offers timezone implementations subclassing the abstract
:py:class:`datetime.tzinfo` type. There are classes to handle tzfile format
files (usually are in :file:`/etc/localtime`, :file:`/usr/share/zoneinfo`,
etc), TZ environment string (in all known formats), given ranges (with help
from relative deltas), local machine timezone, fixed offset timezone, and UTC
timezone.
"""
import datetime
import struct
import time
import sys
import os
import bisect
import weakref
from collections import OrderedDict

import six
from six import string_types
from six.moves import _thread
from ._common import tzname_in_python2, _tzinfo
from ._common import tzrangebase, enfold
from ._common import _validate_fromutc_inputs

from ._factories import _TzSingleton, _TzOffsetFactory
from ._factories import _TzStrFactory
try:
    from .win import tzwin, tzwinlocal
except ImportError:
    tzwin = tzwinlocal = None

# For warning about rounding tzinfo
from warnings import warn

ZERO = datetime.timedelta(0)
EPOCH = datetime.datetime(1970, 1, 1, 0, 0)
EPOCHORDINAL = EPOCH.toordinal()


@six.add_metaclass(_TzSingleton)
class tzutc(datetime.tzinfo):
    """
    This is a tzinfo object that represents the UTC time zone.

    **Examples:**

    .. doctest::

        >>> from datetime import *
        >>> from dateutil.tz import *

        >>> datetime.now()
        datetime.datetime(2003, 9, 27, 9, 40, 1, 521290)

        >>> datetime.now(tzutc())
        datetime.datetime(2003, 9, 27, 12, 40, 12, 156379, tzinfo=tzutc())

        >>> datetime.now(tzutc()).tzname()
        'UTC'

    .. versionchanged:: 2.7.0
        ``tzutc()`` is now a singleton, so the result of ``tzutc()`` will
        always return the same object.

        .. doctest::

            >>> from dateutil.tz import tzutc, UTC
            >>> tzutc() is tzutc()
            True
            >>> tzutc() is UTC
            True
    """
    def utcoffset(self, dt):
        return ZERO

    def dst(self, dt):
        return ZERO

    @tzname_in_python2
    def tzname(self, dt):
        return "UTC"

    def is_ambiguous(self, dt):
        """
        Whether or not the "wall time" of a given datetime is ambiguous in this
        zone.

        :param dt:
            A :py:class:`datetime.datetime`, naive or time zone aware.


        :return:
            Returns ``True`` if ambiguous, ``False`` otherwise.

        .. versionadded:: 2.6.0
        """
        return False

    @_validate_fromutc_inputs
    def fromutc(self, dt):
        """
        Fast track version of fromutc() returns the original ``dt`` object for
        any valid :py:class:`datetime.datetime` object.
        """
        return dt

    def __eq__(self, other):
        if not isinstance(other, (tzutc, tzoffset)):
            return NotImplemented

        return (isinstance(other, tzutc) or
                (isinstance(other, tzoffset) and other._offset == ZERO))

    __hash__ = None

    def __ne__(self, other):
        return not (self == other)

    def __repr__(self):
        return "%s()" % self.__class__.__name__

    __reduce__ = object.__reduce__


#: Convenience constant providing a :class:`tzutc()` instance
#:
#: .. versionadded:: 2.7.0
UTC = tzutc()


@six.add_metaclass(_TzOffsetFactory)
class tzoffset(datetime.tzinfo):
    """
    A simple class for representing a fixed offset from UTC.

    :param name:
        The timezone name, to be returned when ``tzname()`` is called.
    :param offset:
        The time zone offset in seconds, or (since version 2.6.0, represented
        as a :py:class:`datetime.timedelta` object).
    """
    def __init__(self, name, offset):
        self._name = name

        try:
            # Allow a timedelta
            offset = offset.total_seconds()
        except (TypeError, AttributeError):
            pass

        self._offset = datetime.timedelta(seconds=_get_supported_offset(offset))

    def utcoffset(self, dt):
        return self._offset

    def dst(self, dt):
        return ZERO

    @tzname_in_python2
    def tzname(self, dt):
        return self._name

    @_validate_fromutc_inputs
    def fromutc(self, dt):
        return dt + self._offset

    def is_ambiguous(self, dt):
        """
        Whether or not the "wall time" of a given datetime is ambiguous in this
        zone.

        :param dt:
            A :py:class:`datetime.datetime`, naive or time zone aware.
        :return:
            Returns ``True`` if ambiguous, ``False`` otherwise.

        .. versionadded:: 2.6.0
        """
        return False

    def __eq__(self, other):
        if not isinstance(other, tzoffset):
            return NotImplemented

        return self._offset == other._offset

    __hash__ = None

    def __ne__(self, other):
        return not (self == other)

    def __repr__(self):
        return "%s(%s, %s)" % (self.__class__.__name__,
                               repr(self._name),
                               int(self._offset.total_seconds()))

    __reduce__ = object.__reduce__


class tzlocal(_tzinfo):
    """
    A :class:`tzinfo` subclass built around the ``time`` timezone functions.
    """
    def __init__(self):
        super(tzlocal, self).__init__()

        self._std_offset = datetime.timedelta(seconds=-time.timezone)
        if time.daylight:
            self._dst_offset = datetime.timedelta(seconds=-time.altzone)
        else:
            self._dst_offset = self._std_offset

        self._dst_saved = self._dst_offset - self._std_offset
        self._hasdst = bool(self._dst_saved)
        self._tznames = tuple(time.tzname)

    def utcoffset(self, dt):
        if dt is None and self._hasdst:
            return None

        if self._isdst(dt):
            return self._dst_offset
        else:
            return self._std_offset

    def dst(self, dt):
        if dt is None and self._hasdst:
            return None

        if self._isdst(dt):
            return self._dst_offset - self._std_offset
        else:
            return ZERO

    @tzname_in_python2
    def tzname(self, dt):
        return self._tznames[self._isdst(dt)]

    def is_ambiguous(self, dt):
        """
        Whether or not the "wall time" of a given datetime is ambiguous in this
        zone.

        :param dt:
            A :py:class:`datetime.datetime`, naive or time zone aware.


        :return:
            Returns ``True`` if ambiguous, ``False`` otherwise.

        .. versionadded:: 2.6.0
        """
        naive_dst = self._naive_is_dst(dt)
        return (not naive_dst and
                (naive_dst != self._naive_is_dst(dt - self._dst_saved)))

    def _naive_is_dst(self, dt):
        timestamp = _datetime_to_timestamp(dt)
        return time.localtime(timestamp + time.timezone).tm_isdst

    def _isdst(self, dt, fold_naive=True):
        # We can't use mktime here. It is unstable when deciding if
        # the hour near to a change is DST or not.
        #
        # timestamp = time.mktime((dt.year, dt.month, dt.day, dt.hour,
        #                         dt.minute, dt.second, dt.weekday(), 0, -1))
        # return time.localtime(timestamp).tm_isdst
        #
        # The code above yields the following result:
        #
        # >>> import tz, datetime
        # >>> t = tz.tzlocal()
        # >>> datetime.datetime(2003,2,15,23,tzinfo=t).tzname()
        # 'BRDT'
        # >>> datetime.datetime(2003,2,16,0,tzinfo=t).tzname()
        # 'BRST'
        # >>> datetime.datetime(2003,2,15,23,tzinfo=t).tzname()
        # 'BRST'
        # >>> datetime.datetime(2003,2,15,22,tzinfo=t).tzname()
        # 'BRDT'
        # >>> datetime.datetime(2003,2,15,23,tzinfo=t).tzname()
        # 'BRDT'
        #
        # Here is a more stable implementation:
        #
        if not self._hasdst:
            return False

        # Check for ambiguous times:
        dstval = self._naive_is_dst(dt)
        fold = getattr(dt, 'fold', None)

        if self.is_ambiguous(dt):
            if fold is not None:
                return not self._fold(dt)
            else:
                return True

        return dstval

    def __eq__(self, other):
        if isinstance(other, tzlocal):
            return (self._std_offset == other._std_offset and
                    self._dst_offset == other._dst_offset)
        elif isinstance(other, tzutc):
            return (not self._hasdst and
                    self._tznames[0] in {'UTC', 'GMT'} and
                    self._std_offset == ZERO)
        elif isinstance(other, tzoffset):
            return (not self._hasdst and
                    self._tznames[0] == other._name and
                    self._std_offset == other._offset)
        else:
            return NotImplemented

    __hash__ = None

    def __ne__(self, other):
        return not (self == other)

    def __repr__(self):
        return "%s()" % self.__class__.__name__

    __reduce__ = object.__reduce__


class _ttinfo(object):
    __slots__ = ["offset", "delta", "isdst", "abbr",
                 "isstd", "isgmt", "dstoffset"]

    def __init__(self):
        for attr in self.__slots__:
            setattr(self, attr, None)

    def __repr__(self):
        l = []
        for attr in self.__slots__:
            value = getattr(self, attr)
            if value is not None:
                l.append("%s=%s" % (attr, repr(value)))
        return "%s(%s)" % (self.__class__.__name__, ", ".join(l))

    def __eq__(self, other):
        if not isinstance(other, _ttinfo):
            return NotImplemented

        return (self.offset == other.offset and
                self.delta == other.delta and
                self.isdst == other.isdst and
                self.abbr == other.abbr and
                self.isstd == other.isstd and
                self.isgmt == other.isgmt and
                self.dstoffset == other.dstoffset)

    __hash__ = None

    def __ne__(self, other):
        return not (self == other)

    def __getstate__(self):
        state = {}
        for name in self.__slots__:
            state[name] = getattr(self, name, None)
        return state

    def __setstate__(self, state):
        for name in self.__slots__:
            if name in state:
                setattr(self, name, state[name])


class _tzfile(object):
    """
    Lightweight class for holding the relevant transition and time zone
    information read from binary tzfiles.
    """
    attrs = ['trans_list', 'trans_list_utc', 'trans_idx', 'ttinfo_list',
             'ttinfo_std', 'ttinfo_dst', 'ttinfo_before', 'ttinfo_first']

    def __init__(self, **kwargs):
        for attr in self.attrs:
            setattr(self, attr, kwargs.get(attr, None))


class tzfile(_tzinfo):
    """
    This is a ``tzinfo`` subclass that allows one to use the ``tzfile(5)``
    format timezone files to extract current and historical zone information.

    :param fileobj:
        This can be an opened file stream or a file name that the time zone
        information can be read from.

    :param filename:
        This is an optional parameter specifying the source of the time zone
        information in the event that ``fileobj`` is a file object. If omitted
        and ``fileobj`` is a file stream, this parameter will be set either to
        ``fileobj``'s ``name`` attribute or to ``repr(fileobj)``.

    See `Sources for Time Zone and Daylight Saving Time Data
    <https://data.iana.org/time-zones/tz-link.html>`_ for more information.
    Time zone files can be compiled from the `IANA Time Zone database files
    <https://www.iana.org/time-zones>`_ with the `zic time zone compiler
    <https://www.freebsd.org/cgi/man.cgi?query=zic&sektion=8>`_

    .. note::

        Only construct a ``tzfile`` directly if you have a specific timezone
        file on disk that you want to read into a Python ``tzinfo`` object.
        If you want to get a ``tzfile`` representing a specific IANA zone,
        (e.g. ``'America/New_York'``), you should call
        :func:`dateutil.tz.gettz` with the zone identifier.


    **Examples:**

    Using the US Eastern time zone as an example, we can see that a ``tzfile``
    provides time zone information for the standard Daylight Saving offsets:

    .. testsetup:: tzfile

        from dateutil.tz import gettz
        from datetime import datetime

    .. doctest:: tzfile

        >>> NYC = gettz('America/New_York')
        >>> NYC
        tzfile('/usr/share/zoneinfo/America/New_York')

        >>> print(datetime(2016, 1, 3, tzinfo=NYC))     # EST
        2016-01-03 00:00:00-05:00

        >>> print(datetime(2016, 7, 7, tzinfo=NYC))     # EDT
        2016-07-07 00:00:00-04:00


    The ``tzfile`` structure contains a fully history of the time zone,
    so historical dates will also have the right offsets. For example, before
    the adoption of the UTC standards, New York used local solar  mean time:

    .. doctest:: tzfile

       >>> print(datetime(1901, 4, 12, tzinfo=NYC))    # LMT
       1901-04-12 00:00:00-04:56

    And during World War II, New York was on "Eastern War Time", which was a
    state of permanent daylight saving time:

    .. doctest:: tzfile

        >>> print(datetime(1944, 2, 7, tzinfo=NYC))    # EWT
        1944-02-07 00:00:00-04:00

    """

    def __init__(self, fileobj, filename=None):
        super(tzfile, self).__init__()

        file_opened_here = False
        if isinstance(fileobj, string_types):
            self._filename = fileobj
            fileobj = open(fileobj, 'rb')
            file_opened_here = True
        elif filename is not None:
            self._filename = filename
        elif hasattr(fileobj, "name"):
            self._filename = fileobj.name
        else:
            self._filename = repr(fileobj)

        if fileobj is not None:
            if not file_opened_here:
                fileobj = _nullcontext(fileobj)

            with fileobj as file_stream:
                tzobj = self._read_tzfile(file_stream)

            self._set_tzdata(tzobj)

    def _set_tzdata(self, tzobj):
        """ Set the time zone data of this object from a _tzfile object """
        # Copy the relevant attributes over as private attributes
        for attr in _tzfile.attrs:
            setattr(self, '_' + attr, getattr(tzobj, attr))

    def _read_tzfile(self, fileobj):
        out = _tzfile()

        # From tzfile(5):
        #
        # The time zone information files used by tzset(3)
        # begin with the magic characters "TZif" to identify
        # them as time zone information files, followed by
        # sixteen bytes reserved for future use, followed by
        # six four-byte values of type long, written in a
        # ``standard'' byte order (the high-order  byte
        # of the value is written first).
        if fileobj.read(4).decode() != "TZif":
            raise ValueError("magic not found")

        fileobj.read(16)

        (
            # The number of UTC/local indicators stored in the file.
            ttisgmtcnt,

            # The number of standard/wall indicators stored in the file.
            ttisstdcnt,

            # The number of leap seconds for which data is
            # stored in the file.
            leapcnt,

            # The number of "transition times" for which data
            # is stored in the file.
            timecnt,

            # The number of "local time types" for which data
            # is stored in the file (must not be zero).
            typecnt,

            # The  number  of  characters  of "time zone
            # abbreviation strings" stored in the file.
            charcnt,

        ) = struct.unpack(">6l", fileobj.read(24))

        # The above header is followed by tzh_timecnt four-byte
        # values  of  type long,  sorted  in ascending order.
        # These values are written in ``standard'' byte order.
        # Each is used as a transition time (as  returned  by
        # time(2)) at which the rules for computing local time
        # change.

        if timecnt:
            out.trans_list_utc = list(struct.unpack(">%dl" % timecnt,
                                                    fileobj.read(timecnt*4)))
        else:
            out.trans_list_utc = []

        # Next come tzh_timecnt one-byte values of type unsigned
        # char; each one tells which of the different types of
        # ``local time'' types described in the file is associated
        # with the same-indexed transition time. These values
        # serve as indices into an array of ttinfo structures that
        # appears next in the file.

        if timecnt:
            out.trans_idx = struct.unpack(">%dB" % timecnt,
                                          fileobj.read(timecnt))
        else:
            out.trans_idx = []

        # Each ttinfo structure is written as a four-byte value
        # for tt_gmtoff  of  type long,  in  a  standard  byte
        # order, followed  by a one-byte value for tt_isdst
        # and a one-byte  value  for  tt_abbrind.   In  each
        # structure, tt_gmtoff  gives  the  number  of
        # seconds to be added to UTC, tt_isdst tells whether
        # tm_isdst should be set by  localtime(3),  and
        # tt_abbrind serves  as an index into the array of
        # time zone abbreviation characters that follow the
        # ttinfo structure(s) in the file.

        ttinfo = []

        for i in range(typecnt):
            ttinfo.append(struct.unpack(">lbb", fileobj.read(6)))

        abbr = fileobj.read(charcnt).decode()

        # Then there are tzh_leapcnt pairs of four-byte
        # values, written in  standard byte  order;  the
        # first  value  of  each pair gives the time (as
        # returned by time(2)) at which a leap second
        # occurs;  the  second  gives the  total  number of
        # leap seconds to be applied after the given time.
        # The pairs of values are sorted in ascending order
        # by time.

        # Not used, for now (but seek for correct file position)
        if leapcnt:
            fileobj.seek(leapcnt * 8, os.SEEK_CUR)

        # Then there are tzh_ttisstdcnt standard/wall
        # indicators, each stored as a one-byte value;
        # they tell whether the transition times associated
        # with local time types were specified as standard
        # time or wall clock time, and are used when
        # a time zone file is used in handling POSIX-style
        # time zone environment variables.

        if ttisstdcnt:
            isstd = struct.unpack(">%db" % ttisstdcnt,
                                  fileobj.read(ttisstdcnt))

        # Finally, there are tzh_ttisgmtcnt UTC/local
        # indicators, each stored as a one-byte value;
        # they tell whether the transition times associated
        # with local time types were specified as UTC or
        # local time, and are used when a time zone file
        # is used in handling POSIX-style time zone envi-
        # ronment variables.

        if ttisgmtcnt:
            isgmt = struct.unpack(">%db" % ttisgmtcnt,
                                  fileobj.read(ttisgmtcnt))

        # Build ttinfo list
        out.ttinfo_list = []
        for i in range(typecnt):
            gmtoff, isdst, abbrind = ttinfo[i]
            gmtoff = _get_supported_offset(gmtoff)
            tti = _ttinfo()
            tti.offset = gmtoff
            tti.dstoffset = datetime.timedelta(0)
            tti.delta = datetime.timedelta(seconds=gmtoff)
            tti.isdst = isdst
            tti.abbr = abbr[abbrind:abbr.find('\x00', abbrind)]
            tti.isstd = (ttisstdcnt > i and isstd[i] != 0)
            tti.isgmt = (ttisgmtcnt > i and isgmt[i] != 0)
            out.ttinfo_list.append(tti)

        # Replace ttinfo indexes for ttinfo objects.
        out.trans_idx = [out.ttinfo_list[idx] for idx in out.trans_idx]

        # Set standard, dst, and before ttinfos. before will be
        # used when a given time is before any transitions,
        # and will be set to the first non-dst ttinfo, or to
        # the first dst, if all of them are dst.
        out.ttinfo_std = None
        out.ttinfo_dst = None
        out.ttinfo_before = None
        if out.ttinfo_list:
            if not out.trans_list_utc:
                out.ttinfo_std = out.ttinfo_first = out.ttinfo_list[0]
            else:
                for i in range(timecnt-1, -1, -1):
                    tti = out.trans_idx[i]
                    if not out.ttinfo_std and not tti.isdst:
                        out.ttinfo_std = tti
                    elif not out.ttinfo_dst and tti.isdst:
                        out.ttinfo_dst = tti

                    if out.ttinfo_std and out.ttinfo_dst:
                        break
                else:
                    if out.ttinfo_dst and not out.ttinfo_std:
                        out.ttinfo_std = out.ttinfo_dst

                for tti in out.ttinfo_list:
                    if not tti.isdst:
                        out.ttinfo_before = tti
                        break
                else:
                    out.ttinfo_before = out.ttinfo_list[0]

        # Now fix transition times to become relative to wall time.
        #
        # I'm not sure about this. In my tests, the tz source file
        # is setup to wall time, and in the binary file isstd and
        # isgmt are off, so it should be in wall time. OTOH, it's
        # always in gmt time. Let me know if you have comments
        # about this.
        lastdst = None
        lastoffset = None
        lastdstoffset = None
        lastbaseoffset = None
        out.trans_list = []

        for i, tti in enumerate(out.trans_idx):
            offset = tti.offset
            dstoffset = 0

            if lastdst is not None:
                if tti.isdst:
                    if not lastdst:
                        dstoffset = offset - lastoffset

                    if not dstoffset and lastdstoffset:
                        dstoffset = lastdstoffset

                    tti.dstoffset = datetime.timedelta(seconds=dstoffset)
                    lastdstoffset = dstoffset

            # If a time zone changes its base offset during a DST transition,
            # then you need to adjust by the previous base offset to get the
            # transition time in local time. Otherwise you use the current
            # base offset. Ideally, I would have some mathematical proof of
            # why this is true, but I haven't really thought about it enough.
            baseoffset = offset - dstoffset
            adjustment = baseoffset
            if (lastbaseoffset is not None and baseoffset != lastbaseoffset
                    and tti.isdst != lastdst):
                # The base DST has changed
                adjustment = lastbaseoffset

            lastdst = tti.isdst
            lastoffset = offset
            lastbaseoffset = baseoffset

            out.trans_list.append(out.trans_list_utc[i] + adjustment)

        out.trans_idx = tuple(out.trans_idx)
        out.trans_list = tuple(out.trans_list)
        out.trans_list_utc = tuple(out.trans_list_utc)

        return out

    def _find_last_transition(self, dt, in_utc=False):
        # If there's no list, there are no transitions to find
        if not self._trans_list:
            return None

        timestamp = _datetime_to_timestamp(dt)

        # Find where the timestamp fits in the transition list - if the
        # timestamp is a transition time, it's part of the "after" period.
        trans_list = self._trans_list_utc if in_utc else self._trans_list
        idx = bisect.bisect_right(trans_list, timestamp)

        # We want to know when the previous transition was, so subtract off 1
        return idx - 1

    def _get_ttinfo(self, idx):
        # For no list or after the last transition, default to _ttinfo_std
        if idx is None or (idx + 1) >= len(self._trans_list):
            return self._ttinfo_std

        # If there is a list and the time is before it, return _ttinfo_before
        if idx < 0:
            return self._ttinfo_before

        return self._trans_idx[idx]

    def _find_ttinfo(self, dt):
        idx = self._resolve_ambiguous_time(dt)

        return self._get_ttinfo(idx)

    def fromutc(self, dt):
        """
        The ``tzfile`` implementation of :py:func:`datetime.tzinfo.fromutc`.

        :param dt:
            A :py:class:`datetime.datetime` object.

        :raises TypeError:
            Raised if ``dt`` is not a :py:class:`datetime.datetime` object.

        :raises ValueError:
            Raised if this is called with a ``dt`` which does not have this
            ``tzinfo`` attached.

        :return:
            Returns a :py:class:`datetime.datetime` object representing the
            wall time in ``self``'s time zone.
        """
        # These isinstance checks are in datetime.tzinfo, so we'll preserve
        # them, even if we don't care about duck typing.
        if not isinstance(dt, datetime.datetime):
            raise TypeError("fromutc() requires a datetime argument")

        if dt.tzinfo is not self:
            raise ValueError("dt.tzinfo is not self")

        # First treat UTC as wall time and get the transition we're in.
        idx = self._find_last_transition(dt, in_utc=True)
        tti = self._get_ttinfo(idx)

        dt_out = dt + datetime.timedelta(seconds=tti.offset)

        fold = self.is_ambiguous(dt_out, idx=idx)

        return enfold(dt_out, fold=int(fold))

    def is_ambiguous(self, dt, idx=None):
        """
        Whether or not the "wall time" of a given datetime is ambiguous in this
        zone.

        :param dt:
            A :py:class:`datetime.datetime`, naive or time zone aware.


        :return:
            Returns ``True`` if ambiguous, ``False`` otherwise.

        .. versionadded:: 2.6.0
        """
        if idx is None:
            idx = self._find_last_transition(dt)

        # Calculate the difference in offsets from current to previous
        timestamp = _datetime_to_timestamp(dt)
        tti = self._get_ttinfo(idx)

        if idx is None or idx <= 0:
            return False

        od = self._get_ttinfo(idx - 1).offset - tti.offset
        tt = self._trans_list[idx]          # Transition time

        return timestamp < tt + od

    def _resolve_ambiguous_time(self, dt):
        idx = self._find_last_transition(dt)

        # If we have no transitions, return the index
        _fold = self._fold(dt)
        if idx is None or idx == 0:
            return idx

        # If it's ambiguous and we're in a fold, shift to a different index.
        idx_offset = int(not _fold and self.is_ambiguous(dt, idx))

        return idx - idx_offset

    def utcoffset(self, dt):
        if dt is None:
            return None

        if not self._ttinfo_std:
            return ZERO

        return self._find_ttinfo(dt).delta

    def dst(self, dt):
        if dt is None:
            return None

        if not self._ttinfo_dst:
            return ZERO

        tti = self._find_ttinfo(dt)

        if not tti.isdst:
            return ZERO

        # The documentation says that utcoffset()-dst() must
        # be constant for every dt.
        return tti.dstoffset

    @tzname_in_python2
    def tzname(self, dt):
        if not self._ttinfo_std or dt is None:
            return None
        return self._find_ttinfo(dt).abbr

    def __eq__(self, other):
        if not isinstance(other, tzfile):
            return NotImplemented
        return (self._trans_list == other._trans_list and
                self._trans_idx == other._trans_idx and
                self._ttinfo_list == other._ttinfo_list)

    __hash__ = None

    def __ne__(self, other):
        return not (self == other)

    def __repr__(self):
        return "%s(%s)" % (self.__class__.__name__, repr(self._filename))

    def __reduce__(self):
        return self.__reduce_ex__(None)

    def __reduce_ex__(self, protocol):
        return (self.__class__, (None, self._filename), self.__dict__)


class tzrange(tzrangebase):
    """
    The ``tzrange`` object is a time zone specified by a set of offsets and
    abbreviations, equivalent to the way the ``TZ`` variable can be specified
    in POSIX-like systems, but using Python delta objects to specify DST
    start, end and offsets.

    :param stdabbr:
        The abbreviation for standard time (e.g. ``'EST'``).

    :param stdoffset:
        An integer or :class:`datetime.timedelta` object or equivalent
        specifying the base offset from UTC.

        If unspecified, +00:00 is used.

    :param dstabbr:
        The abbreviation for DST / "Summer" time (e.g. ``'EDT'``).

        If specified, with no other DST information, DST is assumed to occur
        and the default behavior or ``dstoffset``, ``start`` and ``end`` is
        used. If unspecified and no other DST information is specified, it
        is assumed that this zone has no DST.

        If this is unspecified and other DST information is *is* specified,
        DST occurs in the zone but the time zone abbreviation is left
        unchanged.

    :param dstoffset:
        A an integer or :class:`datetime.timedelta` object or equivalent
        specifying the UTC offset during DST. If unspecified and any other DST
        information is specified, it is assumed to be the STD offset +1 hour.

    :param start:
        A :class:`relativedelta.relativedelta` object or equivalent specifying
        the time and time of year that daylight savings time starts. To
        specify, for example, that DST starts at 2AM on the 2nd Sunday in
        March, pass:

            ``relativedelta(hours=2, month=3, day=1, weekday=SU(+2))``

        If unspecified and any other DST information is specified, the default
        value is 2 AM on the first Sunday in April.

    :param end:
        A :class:`relativedelta.relativedelta` object or equivalent
        representing the time and time of year that daylight savings time
        ends, with the same specification method as in ``start``. One note is
        that this should point to the first time in the *standard* zone, so if
        a transition occurs at 2AM in the DST zone and the clocks are set back
        1 hour to 1AM, set the ``hours`` parameter to +1.


    **Examples:**

    .. testsetup:: tzrange

        from dateutil.tz import tzrange, tzstr

    .. doctest:: tzrange

        >>> tzstr('EST5EDT') == tzrange("EST", -18000, "EDT")
        True

        >>> from dateutil.relativedelta import *
        >>> range1 = tzrange("EST", -18000, "EDT")
        >>> range2 = tzrange("EST", -18000, "EDT", -14400,
        ...                  relativedelta(hours=+2, month=4, day=1,
        ...                                weekday=SU(+1)),
        ...                  relativedelta(hours=+1, month=10, day=31,
        ...                                weekday=SU(-1)))
        >>> tzstr('EST5EDT') == range1 == range2
        True

    """
    def __init__(self, stdabbr, stdoffset=None,
                 dstabbr=None, dstoffset=None,
                 start=None, end=None):

        global relativedelta
        from dateutil import relativedelta

        self._std_abbr = stdabbr
        self._dst_abbr = dstabbr

        try:
            stdoffset = stdoffset.total_seconds()
        except (TypeError, AttributeError):
            pass

        try:
            dstoffset = dstoffset.total_seconds()
        except (TypeError, AttributeError):
            pass

        if stdoffset is not None:
            self._std_offset = datetime.timedelta(seconds=stdoffset)
        else:
            self._std_offset = ZERO

        if dstoffset is not None:
            self._dst_offset = datetime.timedelta(seconds=dstoffset)
        elif dstabbr and stdoffset is not None:
            self._dst_offset = self._std_offset + datetime.timedelta(hours=+1)
        else:
            self._dst_offset = ZERO

        if dstabbr and start is None:
            self._start_delta = relativedelta.relativedelta(
                hours=+2, month=4, day=1, weekday=relativedelta.SU(+1))
        else:
            self._start_delta = start

        if dstabbr and end is None:
            self._end_delta = relativedelta.relativedelta(
                hours=+1, month=10, day=31, weekday=relativedelta.SU(-1))
        else:
            self._end_delta = end

        self._dst_base_offset_ = self._dst_offset - self._std_offset
        self.hasdst = bool(self._start_delta)

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

        base_year = datetime.datetime(year, 1, 1)

        start = base_year + self._start_delta
        end = base_year + self._end_delta

        return (start, end)

    def __eq__(self, other):
        if not isinstance(other, tzrange):
            return NotImplemented

        return (self._std_abbr == other._std_abbr and
                self._dst_abbr == other._dst_abbr and
                self._std_offset == other._std_offset and
                self._dst_offset == other._dst_offset and
                self._start_delta == other._start_delta and
                self._end_delta == other._end_delta)

    @property
    def _dst_base_offset(self):
        return self._dst_base_offset_


@six.add_metaclass(_TzStrFactory)
class tzstr(tzrange):
    """
    ``tzstr`` objects are time zone objects specified by a time-zone string as
    it would be passed to a ``TZ`` variable on POSIX-style systems (see
    the `GNU C Library: TZ Variable`_ for more details).

    There is one notable exception, which is that POSIX-style time zones use an
    inverted offset format, so normally ``GMT+3`` would be parsed as an offset
    3 hours *behind* GMT. The ``tzstr`` time zone object will parse this as an
    offset 3 hours *ahead* of GMT. If you would like to maintain the POSIX
    behavior, pass a ``True`` value to ``posix_offset``.

    The :class:`tzrange` object provides the same functionality, but is
    specified using :class:`relativedelta.relativedelta` objects. rather than
    strings.

    :param s:
        A time zone string in ``TZ`` variable format. This can be a
        :class:`bytes` (2.x: :class:`str`), :class:`str` (2.x:
        :class:`unicode`) or a stream emitting unicode characters
        (e.g. :class:`StringIO`).

    :param posix_offset:
        Optional. If set to ``True``, interpret strings such as ``GMT+3`` or
        ``UTC+3`` as being 3 hours *behind* UTC rather than ahead, per the
        POSIX standard.

    .. caution::

        Prior to version 2.7.0, this function also supported time zones
        in the format:

            * ``EST5EDT,4,0,6,7200,10,0,26,7200,3600``
            * ``EST5EDT,4,1,0,7200,10,-1,0,7200,3600``

        This format is non-standard and has been deprecated; this function
        will raise a :class:`DeprecatedTZFormatWarning` until
        support is removed in a future version.

    .. _`GNU C Library: TZ Variable`:
        https://www.gnu.org/software/libc/manual/html_node/TZ-Variable.html
    """
    def __init__(self, s, posix_offset=False):
        global parser
        from dateutil.parser import _parser as parser

        self._s = s

        res = parser._parsetz(s)
        if res is None or res.any_unused_tokens:
            raise ValueError("unknown string format")

        # Here we break the compatibility with the TZ variable handling.
        # GMT-3 actually *means* the timezone -3.
        if res.stdabbr in ("GMT", "UTC") and not posix_offset:
            res.stdoffset *= -1

        # We must initialize it first, since _delta() needs
        # _std_offset and _dst_offset set. Use False in start/end
        # to avoid building it two times.
        tzrange.__init__(self, res.stdabbr, res.stdoffset,
                         res.dstabbr, res.dstoffset,
                         start=False, end=False)

        if not res.dstabbr:
            self._start_delta = None
            self._end_delta = None
        else:
            self._start_delta = self._delta(res.start)
            if self._start_delta:
                self._end_delta = self._delta(res.end, isend=1)

        self.hasdst = bool(self._start_delta)

    def _delta(self, x, isend=0):
        from dateutil import relativedelta
        kwargs = {}
        if x.month is not None:
            kwargs["month"] = x.month
            if x.weekday is not None:
                kwargs["weekday"] = relativedelta.weekday(x.weekday, x.week)
                if x.week > 0:
                    kwargs["day"] = 1
                else:
                    kwargs["day"] = 31
            elif x.day:
                kwargs["day"] = x.day
        elif x.yday is not None:
            kwargs["yearday"] = x.yday
        elif x.jyday is not None:
            kwargs["nlyearday"] = x.jyday
        if not kwargs:
            # Default is to start on first sunday of april, and end
            # on last sunday of october.
            if not isend:
                kwargs["month"] = 4
                kwargs["day"] = 1
                kwargs["weekday"] = relativedelta.SU(+1)
            else:
                kwargs["month"] = 10
                kwargs["day"] = 31
                kwargs["weekday"] = relativedelta.SU(-1)
        if x.time is not None:
            kwargs["seconds"] = x.time
        else:
            # Default is 2AM.
            kwargs["seconds"] = 7200
        if isend:
            # Convert to standard time, to follow the documented way
            # of working with the extra hour. See the documentation
            # of the tzinfo class.
            delta = self._dst_offset - self._std_offset
            kwargs["seconds"] -= delta.seconds + delta.days * 86400
        return relativedelta.relativedelta(**kwargs)

    def __repr__(self):
        return "%s(%s)" % (self.__class__.__name__, repr(self._s))


class _tzicalvtzcomp(object):
    def __init__(self, tzoffsetfrom, tzoffsetto, isdst,
                 tzname=None, rrule=None):
        self.tzoffsetfrom = datetime.timedelta(seconds=tzoffsetfrom)
        self.tzoffsetto = datetime.timedelta(seconds=tzoffsetto)
        self.tzoffsetdiff = self.tzoffsetto - self.tzoffsetfrom
        self.isdst = isdst
        self.tzname = tzname
        self.rrule = rrule


class _tzicalvtz(_tzinfo):
    def __init__(self, tzid, comps=[]):
        super(_tzicalvtz, self).__init__()

        self._tzid = tzid
        self._comps = comps
        self._cachedate = []
        self._cachecomp = []
        self._cache_lock = _thread.allocate_lock()

    def _find_comp(self, dt):
        if len(self._comps) == 1:
            return self._comps[0]

        dt = dt.replace(tzinfo=None)

        try:
            with self._cache_lock:
                return self._cachecomp[self._cachedate.index(
                    (dt, self._fold(dt)))]
        except ValueError:
            pass

        lastcompdt = None
        lastcomp = None

        for comp in self._comps:
            compdt = self._find_compdt(comp, dt)

            if compdt and (not lastcompdt or lastcompdt < compdt):
                lastcompdt = compdt
                lastcomp = comp

        if not lastcomp:
            # RFC says nothing about what to do when a given
            # time is before the first onset date. We'll look for the
            # first standard component, or the first component, if
            # none is found.
            for comp in self._comps:
                if not comp.isdst:
                    lastcomp = comp
                    break
            else:
                lastcomp = comp[0]

        with self._cache_lock:
            self._cachedate.insert(0, (dt, self._fold(dt)))
            self._cachecomp.insert(0, lastcomp)

            if len(self._cachedate) > 10:
                self._cachedate.pop()
                self._cachecomp.pop()

        return lastcomp

    def _find_compdt(self, comp, dt):
        if comp.tzoffsetdiff < ZERO and self._fold(dt):
            dt -= comp.tzoffsetdiff

        compdt = comp.rrule.before(dt, inc=True)

        return compdt

    def utcoffset(self, dt):
        if dt is None:
            return None

        return self._find_comp(dt).tzoffsetto

    def dst(self, dt):
        comp = self._find_comp(dt)
        if comp.isdst:
            return comp.tzoffsetdiff
        else:
            return ZERO

    @tzname_in_python2
    def tzname(self, dt):
        return self._find_comp(dt).tzname

    def __repr__(self):
        return "<tzicalvtz %s>" % repr(self._tzid)

    __reduce__ = object.__reduce__


class tzical(object):
    """
    This object is designed to parse an iCalendar-style ``VTIMEZONE`` structure
    as set out in `RFC 5545`_ Section 4.6.5 into one or more `tzinfo` objects.

    :param `fileobj`:
        A file or stream in iCalendar format, which should be UTF-8 encoded
        with CRLF endings.

    .. _`RFC 5545`: https://tools.ietf.org/html/rfc5545
    """
    def __init__(self, fileobj):
        global rrule
        from dateutil import rrule

        if isinstance(fileobj, string_types):
            self._s = fileobj
            # ical should be encoded in UTF-8 with CRLF
            fileobj = open(fileobj, 'r')
        else:
            self._s = getattr(fileobj, 'name', repr(fileobj))
            fileobj = _nullcontext(fileobj)

        self._vtz = {}

        with fileobj as fobj:
            self._parse_rfc(fobj.read())

    def keys(self):
        """
        Retrieves the available time zones as a list.
        """
        return list(self._vtz.keys())

    def get(self, tzid=None):
        """
        Retrieve a :py:class:`datetime.tzinfo` object by its ``tzid``.

        :param tzid:
            If there is exactly one time zone available, omitting ``tzid``
            or passing :py:const:`None` value returns it. Otherwise a valid
            key (which can be retrieved from :func:`keys`) is required.

        :raises ValueError:
            Raised if ``tzid`` is not specified but there are either more
            or fewer than 1 zone defined.

        :returns:
            Returns either a :py:class:`datetime.tzinfo` object representing
            the relevant time zone or :py:const:`None` if the ``tzid`` was
            not found.
        """
        if tzid is None:
            if len(self._vtz) == 0:
                raise ValueError("no timezones defined")
            elif len(self._vtz) > 1:
                raise ValueError("more than one timezone available")
            tzid = next(iter(self._vtz))

        return self._vtz.get(tzid)

    def _parse_offset(self, s):
        s = s.strip()
        if not s:
            raise ValueError("empty offset")
        if s[0] in ('+', '-'):
            signal = (-1, +1)[s[0] == '+']
            s = s[1:]
        else:
            signal = +1
        if len(s) == 4:
            return (int(s[:2]) * 3600 + int(s[2:]) * 60) * signal
        elif len(s) == 6:
            return (int(s[:2]) * 3600 + int(s[2:4]) * 60 + int(s[4:])) * signal
        else:
            raise ValueError("invalid offset: " + s)

    def _parse_rfc(self, s):
        lines = s.splitlines()
        if not lines:
            raise ValueError("empty string")

        # Unfold
        i = 0
        while i < len(lines):
            line = lines[i].rstrip()
            if not line:
                del lines[i]
            elif i > 0 and line[0] == " ":
                lines[i-1] += line[1:]
                del lines[i]
            else:
                i += 1

        tzid = None
        comps = []
        invtz = False
        comptype = None
        for line in lines:
            if not line:
                continue
            name, value = line.split(':', 1)
            parms = name.split(';')
            if not parms:
                raise ValueError("empty property name")
            name = parms[0].upper()
            parms = parms[1:]
            if invtz:
                if name == "BEGIN":
                    if value in ("STANDARD", "DAYLIGHT"):
                        # Process component
                        pass
                    else:
                        raise ValueError("unknown component: "+value)
                    comptype = value
                    founddtstart = False
                    tzoffsetfrom = None
                    tzoffsetto = None
                    rrulelines = []
                    tzname = None
                elif name == "END":
                    if value == "VTIMEZONE":
                        if comptype:
                            raise ValueError("component not closed: "+comptype)
                        if not tzid:
                            raise ValueError("mandatory TZID not found")
                        if not comps:
                            raise ValueError(
                                "at least one component is needed")
                        # Process vtimezone
                        self._vtz[tzid] = _tzicalvtz(tzid, comps)
                        invtz = False
                    elif value == comptype:
                        if not founddtstart:
                            raise ValueError("mandatory DTSTART not found")
                        if tzoffsetfrom is None:
                            raise ValueError(
                                "mandatory TZOFFSETFROM not found")
                        if tzoffsetto is None:
                            raise ValueError(
                                "mandatory TZOFFSETFROM not found")
                        # Process component
                        rr = None
                        if rrulelines:
                            rr = rrule.rrulestr("\n".join(rrulelines),
                                                compatible=True,
                                                ignoretz=True,
                                                cache=True)
                        comp = _tzicalvtzcomp(tzoffsetfrom, tzoffsetto,
                                              (comptype == "DAYLIGHT"),
                                              tzname, rr)
                        comps.append(comp)
                        comptype = None
                    else:
                        raise ValueError("invalid component end: "+value)
                elif comptype:
                    if name == "DTSTART":
                        # DTSTART in VTIMEZONE takes a subset of valid RRULE
                        # values under RFC 5545.
                        for parm in parms:
                            if parm != 'VALUE=DATE-TIME':
                                msg = ('Unsupported DTSTART param in ' +
                                       'VTIMEZONE: ' + parm)
                                raise ValueError(msg)
                        rrulelines.append(line)
                        founddtstart = True
                    elif name in ("RRULE", "RDATE", "EXRULE", "EXDATE"):
                        rrulelines.append(line)
                    elif name == "TZOFFSETFROM":
                        if parms:
                            raise ValueError(
                                "unsupported %s parm: %s " % (name, parms[0]))
                        tzoffsetfrom = self._parse_offset(value)
                    elif name == "TZOFFSETTO":
                        if parms:
                            raise ValueError(
                                "unsupported TZOFFSETTO parm: "+parms[0])
                        tzoffsetto = self._parse_offset(value)
                    elif name == "TZNAME":
                        if parms:
                            raise ValueError(
                                "unsupported TZNAME parm: "+parms[0])
                        tzname = value
                    elif name == "COMMENT":
                        pass
                    else:
                        raise ValueError("unsupported property: "+name)
                else:
                    if name == "TZID":
                        if parms:
                            raise ValueError(
                                "unsupported TZID parm: "+parms[0])
                        tzid = value
                    elif name in ("TZURL", "LAST-MODIFIED", "COMMENT"):
                        pass
                    else:
                        raise ValueError("unsupported property: "+name)
            elif name == "BEGIN" and value == "VTIMEZONE":
                tzid = None
                comps = []
                invtz = True

    def __repr__(self):
        return "%s(%s)" % (self.__class__.__name__, repr(self._s))


if sys.platform != "win32":
    TZFILES = ["/etc/localtime", "localtime"]
    TZPATHS = ["/usr/share/zoneinfo",
               "/usr/lib/zoneinfo",
               "/usr/share/lib/zoneinfo",
               "/etc/zoneinfo"]
else:
    TZFILES = []
    TZPATHS = []


def __get_gettz():
    tzlocal_classes = (tzlocal,)
    if tzwinlocal is not None:
        tzlocal_classes += (tzwinlocal,)

    class GettzFunc(object):
        """
        Retrieve a time zone object from a string representation

        This function is intended to retrieve the :py:class:`tzinfo` subclass
        that best represents the time zone that would be used if a POSIX
        `TZ variable`_ were set to the same value.

        If no argument or an empty string is passed to ``gettz``, local time
        is returned:

        .. code-block:: python3

            >>> gettz()
            tzfile('/etc/localtime')

        This function is also the preferred way to map IANA tz database keys
        to :class:`tzfile` objects:

        .. code-block:: python3

            >>> gettz('Pacific/Kiritimati')
            tzfile('/usr/share/zoneinfo/Pacific/Kiritimati')

        On Windows, the standard is extended to include the Windows-specific
        zone names provided by the operating system:

        .. code-block:: python3

            >>> gettz('Egypt Standard Time')
            tzwin('Egypt Standard Time')

        Passing a GNU ``TZ`` style string time zone specification returns a
        :class:`tzstr` object:

        .. code-block:: python3

            >>> gettz('AEST-10AEDT-11,M10.1.0/2,M4.1.0/3')
            tzstr('AEST-10AEDT-11,M10.1.0/2,M4.1.0/3')

        :param name:
            A time zone name (IANA, or, on Windows, Windows keys), location of
            a ``tzfile(5)`` zoneinfo file or ``TZ`` variable style time zone
            specifier. An empty string, no argument or ``None`` is interpreted
            as local time.

        :return:
            Returns an instance of one of ``dateutil``'s :py:class:`tzinfo`
            subclasses.

        .. versionchanged:: 2.7.0

            After version 2.7.0, any two calls to ``gettz`` using the same
            input strings will return the same object:

            .. code-block:: python3

                >>> tz.gettz('America/Chicago') is tz.gettz('America/Chicago')
                True

            In addition to improving performance, this ensures that
            `"same zone" semantics`_ are used for datetimes in the same zone.


        .. _`TZ variable`:
            https://www.gnu.org/software/libc/manual/html_node/TZ-Variable.html

        .. _`"same zone" semantics`:
            https://blog.ganssle.io/articles/2018/02/aware-datetime-arithmetic.html
        """
        def __init__(self):

            self.__instances = weakref.WeakValueDictionary()
            self.__strong_cache_size = 8
            self.__strong_cache = OrderedDict()
            self._cache_lock = _thread.allocate_lock()

        def __call__(self, name=None):
            with self._cache_lock:
                rv = self.__instances.get(name, None)

                if rv is None:
                    rv = self.nocache(name=name)
                    if not (name is None
                            or isinstance(rv, tzlocal_classes)
                            or rv is None):
                        # tzlocal is slightly more complicated than the other
                        # time zone providers because it depends on environment
                        # at construction time, so don't cache that.
                        #
                        # We also cannot store weak references to None, so we
                        # will also not store that.
                        self.__instances[name] = rv
                    else:
                        # No need for strong caching, return immediately
                        return rv

                self.__strong_cache[name] = self.__strong_cache.pop(name, rv)

                if len(self.__strong_cache) > self.__strong_cache_size:
                    self.__strong_cache.popitem(last=False)

            return rv

        def set_cache_size(self, size):
            with self._cache_lock:
                self.__strong_cache_size = size
                while len(self.__strong_cache) > size:
                    self.__strong_cache.popitem(last=False)

        def cache_clear(self):
            with self._cache_lock:
                self.__instances = weakref.WeakValueDictionary()
                self.__strong_cache.clear()

        @staticmethod
        def nocache(name=None):
            """A non-cached version of gettz"""
            tz = None
            if not name:
                try:
                    name = os.environ["TZ"]
                except KeyError:
                    pass
            if name is None or name in ("", ":"):
                for filepath in TZFILES:
                    if not os.path.isabs(filepath):
                        filename = filepath
                        for path in TZPATHS:
                            filepath = os.path.join(path, filename)
                            if os.path.isfile(filepath):
                                break
                        else:
                            continue
                    if os.path.isfile(filepath):
                        try:
                            tz = tzfile(filepath)
                            break
                        except (IOError, OSError, ValueError):
                            pass
                else:
                    tz = tzlocal()
            else:
                try:
                    if name.startswith(":"):
                        name = name[1:]
                except TypeError as e:
                    if isinstance(name, bytes):
                        new_msg = "gettz argument should be str, not bytes"
                        six.raise_from(TypeError(new_msg), e)
                    else:
                        raise
                if os.path.isabs(name):
                    if os.path.isfile(name):
                        tz = tzfile(name)
                    else:
                        tz = None
                else:
                    for path in TZPATHS:
                        filepath = os.path.join(path, name)
                        if not os.path.isfile(filepath):
                            filepath = filepath.replace(' ', '_')
                            if not os.path.isfile(filepath):
                                continue
                        try:
                            tz = tzfile(filepath)
                            break
                        except (IOError, OSError, ValueError):
                            pass
                    else:
                        tz = None
                        if tzwin is not None:
                            try:
                                tz = tzwin(name)
                            except (WindowsError, UnicodeEncodeError):
                                # UnicodeEncodeError is for Python 2.7 compat
                                tz = None

                        if not tz:
                            from dateutil.zoneinfo import get_zonefile_instance
                            tz = get_zonefile_instance().get(name)

                        if not tz:
                            for c in name:
                                # name is not a tzstr unless it has at least
                                # one offset. For short values of "name", an
                                # explicit for loop seems to be the fastest way
                                # To determine if a string contains a digit
                                if c in "0123456789":
                                    try:
                                        tz = tzstr(name)
                                    except ValueError:
                                        pass
                                    break
                            else:
                                if name in ("GMT", "UTC"):
                                    tz = UTC
                                elif name in time.tzname:
                                    tz = tzlocal()
            return tz

    return GettzFunc()


gettz = __get_gettz()
del __get_gettz


def datetime_exists(dt, tz=None):
    """
    Given a datetime and a time zone, determine whether or not a given datetime
    would fall in a gap.

    :param dt:
        A :class:`datetime.datetime` (whose time zone will be ignored if ``tz``
        is provided.)

    :param tz:
        A :class:`datetime.tzinfo` with support for the ``fold`` attribute. If
        ``None`` or not provided, the datetime's own time zone will be used.

    :return:
        Returns a boolean value whether or not the "wall time" exists in
        ``tz``.

    .. versionadded:: 2.7.0
    """
    if tz is None:
        if dt.tzinfo is None:
            raise ValueError('Datetime is naive and no time zone provided.')
        tz = dt.tzinfo

    dt = dt.replace(tzinfo=None)

    # This is essentially a test of whether or not the datetime can survive
    # a round trip to UTC.
    dt_rt = dt.replace(tzinfo=tz).astimezone(UTC).astimezone(tz)
    dt_rt = dt_rt.replace(tzinfo=None)

    return dt == dt_rt


def datetime_ambiguous(dt, tz=None):
    """
    Given a datetime and a time zone, determine whether or not a given datetime
    is ambiguous (i.e if there are two times differentiated only by their DST
    status).

    :param dt:
        A :class:`datetime.datetime` (whose time zone will be ignored if ``tz``
        is provided.)

    :param tz:
        A :class:`datetime.tzinfo` with support for the ``fold`` attribute. If
        ``None`` or not provided, the datetime's own time zone will be used.

    :return:
        Returns a boolean value whether or not the "wall time" is ambiguous in
        ``tz``.

    .. versionadded:: 2.6.0
    """
    if tz is None:
        if dt.tzinfo is None:
            raise ValueError('Datetime is naive and no time zone provided.')

        tz = dt.tzinfo

    # If a time zone defines its own "is_ambiguous" function, we'll use that.
    is_ambiguous_fn = getattr(tz, 'is_ambiguous', None)
    if is_ambiguous_fn is not None:
        try:
            return tz.is_ambiguous(dt)
        except Exception:
            pass

    # If it doesn't come out and tell us it's ambiguous, we'll just check if
    # the fold attribute has any effect on this particular date and time.
    dt = dt.replace(tzinfo=tz)
    wall_0 = enfold(dt, fold=0)
    wall_1 = enfold(dt, fold=1)

    same_offset = wall_0.utcoffset() == wall_1.utcoffset()
    same_dst = wall_0.dst() == wall_1.dst()

    return not (same_offset and same_dst)


def resolve_imaginary(dt):
    """
    Given a datetime that may be imaginary, return an existing datetime.

    This function assumes that an imaginary datetime represents what the
    wall time would be in a zone had the offset transition not occurred, so
    it will always fall forward by the transition's change in offset.

    .. doctest::

        >>> from dateutil import tz
        >>> from datetime import datetime
        >>> NYC = tz.gettz('America/New_York')
        >>> print(tz.resolve_imaginary(datetime(2017, 3, 12, 2, 30, tzinfo=NYC)))
        2017-03-12 03:30:00-04:00

        >>> KIR = tz.gettz('Pacific/Kiritimati')
        >>> print(tz.resolve_imaginary(datetime(1995, 1, 1, 12, 30, tzinfo=KIR)))
        1995-01-02 12:30:00+14:00

    As a note, :func:`datetime.astimezone` is guaranteed to produce a valid,
    existing datetime, so a round-trip to and from UTC is sufficient to get
    an extant datetime, however, this generally "falls back" to an earlier time
    rather than falling forward to the STD side (though no guarantees are made
    about this behavior).

    :param dt:
        A :class:`datetime.datetime` which may or may not exist.

    :return:
        Returns an existing :class:`datetime.datetime`. If ``dt`` was not
        imaginary, the datetime returned is guaranteed to be the same object
        passed to the function.

    .. versionadded:: 2.7.0
    """
    if dt.tzinfo is not None and not datetime_exists(dt):

        curr_offset = (dt + datetime.timedelta(hours=24)).utcoffset()
        old_offset = (dt - datetime.timedelta(hours=24)).utcoffset()

        dt += curr_offset - old_offset

    return dt


def _datetime_to_timestamp(dt):
    """
    Convert a :class:`datetime.datetime` object to an epoch timestamp in
    seconds since January 1, 1970, ignoring the time zone.
    """
    return (dt.replace(tzinfo=None) - EPOCH).total_seconds()


if sys.version_info >= (3, 6):
    def _get_supported_offset(second_offset):
        return second_offset
else:
    def _get_supported_offset(second_offset):
        # For python pre-3.6, round to full-minutes if that's not the case.
        # Python's datetime doesn't accept sub-minute timezones. Check
        # http://python.org/sf/1447945 or https://bugs.python.org/issue5288
        # for some information.
        old_offset = second_offset
        calculated_offset = 60 * ((second_offset + 30) // 60)
        return calculated_offset


try:
    # Python 3.7 feature
    from contextlib import nullcontext as _nullcontext
except ImportError:
    class _nullcontext(object):
        """
        Class for wrapping contexts so that they are passed through in a
        with statement.
        """
        def __init__(self, context):
            self.context = context

        def __enter__(self):
            return self.context

        def __exit__(*args, **kwargs):
            pass

# vim:ts=4:sw=4:et

# === NexusCore/openenv\Lib\site-packages\debugpy\_vendored\pydevd\pydevd_attach_to_process\winappdbg\textio.py ===
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
Functions for text input, logging or text output.

@group Helpers:
    HexDump,
    HexInput,
    HexOutput,
    Color,
    Table,
    Logger
    DebugLog
    CrashDump
"""

__revision__ = "$Id$"

__all__ = [
    "HexDump",
    "HexInput",
    "HexOutput",
    "Color",
    "Table",
    "CrashDump",
    "DebugLog",
    "Logger",
]

import sys
from winappdbg import win32
from winappdbg import compat
from winappdbg.util import StaticClass

import re
import time
import struct
import traceback

# ------------------------------------------------------------------------------


class HexInput(StaticClass):
    """
    Static functions for user input parsing.
    The counterparts for each method are in the L{HexOutput} class.
    """

    @staticmethod
    def integer(token):
        """
        Convert numeric strings into integers.

        @type  token: str
        @param token: String to parse.

        @rtype:  int
        @return: Parsed integer value.
        """
        token = token.strip()
        neg = False
        if token.startswith(compat.b("-")):
            token = token[1:]
            neg = True
        if token.startswith(compat.b("0x")):
            result = int(token, 16)  # hexadecimal
        elif token.startswith(compat.b("0b")):
            result = int(token[2:], 2)  # binary
        elif token.startswith(compat.b("0o")):
            result = int(token, 8)  # octal
        else:
            try:
                result = int(token)  # decimal
            except ValueError:
                result = int(token, 16)  # hexadecimal (no "0x" prefix)
        if neg:
            result = -result
        return result

    @staticmethod
    def address(token):
        """
        Convert numeric strings into memory addresses.

        @type  token: str
        @param token: String to parse.

        @rtype:  int
        @return: Parsed integer value.
        """
        return int(token, 16)

    @staticmethod
    def hexadecimal(token):
        """
        Convert a strip of hexadecimal numbers into binary data.

        @type  token: str
        @param token: String to parse.

        @rtype:  str
        @return: Parsed string value.
        """
        token = "".join([c for c in token if c.isalnum()])
        if len(token) % 2 != 0:
            raise ValueError("Missing characters in hex data")
        data = ""
        for i in compat.xrange(0, len(token), 2):
            x = token[i : i + 2]
            d = int(x, 16)
            s = struct.pack("<B", d)
            data += s
        return data

    @staticmethod
    def pattern(token):
        """
        Convert an hexadecimal search pattern into a POSIX regular expression.

        For example, the following pattern::

            "B8 0? ?0 ?? ??"

        Would match the following data::

            "B8 0D F0 AD BA"    # mov eax, 0xBAADF00D

        @type  token: str
        @param token: String to parse.

        @rtype:  str
        @return: Parsed string value.
        """
        token = "".join([c for c in token if c == "?" or c.isalnum()])
        if len(token) % 2 != 0:
            raise ValueError("Missing characters in hex data")
        regexp = ""
        for i in compat.xrange(0, len(token), 2):
            x = token[i : i + 2]
            if x == "??":
                regexp += "."
            elif x[0] == "?":
                f = "\\x%%.1x%s" % x[1]
                x = "".join([f % c for c in compat.xrange(0, 0x10)])
                regexp = "%s[%s]" % (regexp, x)
            elif x[1] == "?":
                f = "\\x%s%%.1x" % x[0]
                x = "".join([f % c for c in compat.xrange(0, 0x10)])
                regexp = "%s[%s]" % (regexp, x)
            else:
                regexp = "%s\\x%s" % (regexp, x)
        return regexp

    @staticmethod
    def is_pattern(token):
        """
        Determine if the given argument is a valid hexadecimal pattern to be
        used with L{pattern}.

        @type  token: str
        @param token: String to parse.

        @rtype:  bool
        @return:
            C{True} if it's a valid hexadecimal pattern, C{False} otherwise.
        """
        return re.match(r"^(?:[\?A-Fa-f0-9][\?A-Fa-f0-9]\s*)+$", token)

    @classmethod
    def integer_list_file(cls, filename):
        """
        Read a list of integers from a file.

        The file format is:

         - # anywhere in the line begins a comment
         - leading and trailing spaces are ignored
         - empty lines are ignored
         - integers can be specified as:
            - decimal numbers ("100" is 100)
            - hexadecimal numbers ("0x100" is 256)
            - binary numbers ("0b100" is 4)
            - octal numbers ("0100" is 64)

        @type  filename: str
        @param filename: Name of the file to read.

        @rtype:  list( int )
        @return: List of integers read from the file.
        """
        count = 0
        result = list()
        fd = open(filename, "r")
        for line in fd:
            count = count + 1
            if "#" in line:
                line = line[: line.find("#")]
            line = line.strip()
            if line:
                try:
                    value = cls.integer(line)
                except ValueError:
                    e = sys.exc_info()[1]
                    msg = "Error in line %d of %s: %s"
                    msg = msg % (count, filename, str(e))
                    raise ValueError(msg)
                result.append(value)
        return result

    @classmethod
    def string_list_file(cls, filename):
        """
        Read a list of string values from a file.

        The file format is:

         - # anywhere in the line begins a comment
         - leading and trailing spaces are ignored
         - empty lines are ignored
         - strings cannot span over a single line

        @type  filename: str
        @param filename: Name of the file to read.

        @rtype:  list
        @return: List of integers and strings read from the file.
        """
        count = 0
        result = list()
        fd = open(filename, "r")
        for line in fd:
            count = count + 1
            if "#" in line:
                line = line[: line.find("#")]
            line = line.strip()
            if line:
                result.append(line)
        return result

    @classmethod
    def mixed_list_file(cls, filename):
        """
        Read a list of mixed values from a file.

        The file format is:

         - # anywhere in the line begins a comment
         - leading and trailing spaces are ignored
         - empty lines are ignored
         - strings cannot span over a single line
         - integers can be specified as:
            - decimal numbers ("100" is 100)
            - hexadecimal numbers ("0x100" is 256)
            - binary numbers ("0b100" is 4)
            - octal numbers ("0100" is 64)

        @type  filename: str
        @param filename: Name of the file to read.

        @rtype:  list
        @return: List of integers and strings read from the file.
        """
        count = 0
        result = list()
        fd = open(filename, "r")
        for line in fd:
            count = count + 1
            if "#" in line:
                line = line[: line.find("#")]
            line = line.strip()
            if line:
                try:
                    value = cls.integer(line)
                except ValueError:
                    value = line
                result.append(value)
        return result


# ------------------------------------------------------------------------------


class HexOutput(StaticClass):
    """
    Static functions for user output parsing.
    The counterparts for each method are in the L{HexInput} class.

    @type integer_size: int
    @cvar integer_size: Default size in characters of an outputted integer.
        This value is platform dependent.

    @type address_size: int
    @cvar address_size: Default Number of bits of the target architecture.
        This value is platform dependent.
    """

    integer_size = (win32.SIZEOF(win32.DWORD) * 2) + 2
    address_size = (win32.SIZEOF(win32.SIZE_T) * 2) + 2

    @classmethod
    def integer(cls, integer, bits=None):
        """
        @type  integer: int
        @param integer: Integer.

        @type  bits: int
        @param bits:
            (Optional) Number of bits of the target architecture.
            The default is platform dependent. See: L{HexOutput.integer_size}

        @rtype:  str
        @return: Text output.
        """
        if bits is None:
            integer_size = cls.integer_size
        else:
            integer_size = (bits / 4) + 2
        if integer >= 0:
            return ("0x%%.%dx" % (integer_size - 2)) % integer
        return ("-0x%%.%dx" % (integer_size - 2)) % -integer

    @classmethod
    def address(cls, address, bits=None):
        """
        @type  address: int
        @param address: Memory address.

        @type  bits: int
        @param bits:
            (Optional) Number of bits of the target architecture.
            The default is platform dependent. See: L{HexOutput.address_size}

        @rtype:  str
        @return: Text output.
        """
        if bits is None:
            address_size = cls.address_size
            bits = win32.bits
        else:
            address_size = (bits / 4) + 2
        if address < 0:
            address = ((2**bits) - 1) ^ ~address
        return ("0x%%.%dx" % (address_size - 2)) % address

    @staticmethod
    def hexadecimal(data):
        """
        Convert binary data to a string of hexadecimal numbers.

        @type  data: str
        @param data: Binary data.

        @rtype:  str
        @return: Hexadecimal representation.
        """
        return HexDump.hexadecimal(data, separator="")

    @classmethod
    def integer_list_file(cls, filename, values, bits=None):
        """
        Write a list of integers to a file.
        If a file of the same name exists, it's contents are replaced.

        See L{HexInput.integer_list_file} for a description of the file format.

        @type  filename: str
        @param filename: Name of the file to write.

        @type  values: list( int )
        @param values: List of integers to write to the file.

        @type  bits: int
        @param bits:
            (Optional) Number of bits of the target architecture.
            The default is platform dependent. See: L{HexOutput.integer_size}
        """
        fd = open(filename, "w")
        for integer in values:
            print >> fd, cls.integer(integer, bits)
        fd.close()

    @classmethod
    def string_list_file(cls, filename, values):
        """
        Write a list of strings to a file.
        If a file of the same name exists, it's contents are replaced.

        See L{HexInput.string_list_file} for a description of the file format.

        @type  filename: str
        @param filename: Name of the file to write.

        @type  values: list( int )
        @param values: List of strings to write to the file.
        """
        fd = open(filename, "w")
        for string in values:
            print >> fd, string
        fd.close()

    @classmethod
    def mixed_list_file(cls, filename, values, bits):
        """
        Write a list of mixed values to a file.
        If a file of the same name exists, it's contents are replaced.

        See L{HexInput.mixed_list_file} for a description of the file format.

        @type  filename: str
        @param filename: Name of the file to write.

        @type  values: list( int )
        @param values: List of mixed values to write to the file.

        @type  bits: int
        @param bits:
            (Optional) Number of bits of the target architecture.
            The default is platform dependent. See: L{HexOutput.integer_size}
        """
        fd = open(filename, "w")
        for original in values:
            try:
                parsed = cls.integer(original, bits)
            except TypeError:
                parsed = repr(original)
            print >> fd, parsed
        fd.close()


# ------------------------------------------------------------------------------


class HexDump(StaticClass):
    """
    Static functions for hexadecimal dumps.

    @type integer_size: int
    @cvar integer_size: Size in characters of an outputted integer.
        This value is platform dependent.

    @type address_size: int
    @cvar address_size: Size in characters of an outputted address.
        This value is platform dependent.
    """

    integer_size = win32.SIZEOF(win32.DWORD) * 2
    address_size = win32.SIZEOF(win32.SIZE_T) * 2

    @classmethod
    def integer(cls, integer, bits=None):
        """
        @type  integer: int
        @param integer: Integer.

        @type  bits: int
        @param bits:
            (Optional) Number of bits of the target architecture.
            The default is platform dependent. See: L{HexDump.integer_size}

        @rtype:  str
        @return: Text output.
        """
        if bits is None:
            integer_size = cls.integer_size
        else:
            integer_size = bits / 4
        return ("%%.%dX" % integer_size) % integer

    @classmethod
    def address(cls, address, bits=None):
        """
        @type  address: int
        @param address: Memory address.

        @type  bits: int
        @param bits:
            (Optional) Number of bits of the target architecture.
            The default is platform dependent. See: L{HexDump.address_size}

        @rtype:  str
        @return: Text output.
        """
        if bits is None:
            address_size = cls.address_size
            bits = win32.bits
        else:
            address_size = bits / 4
        if address < 0:
            address = ((2**bits) - 1) ^ ~address
        return ("%%.%dX" % address_size) % address

    @staticmethod
    def printable(data):
        """
        Replace unprintable characters with dots.

        @type  data: str
        @param data: Binary data.

        @rtype:  str
        @return: Printable text.
        """
        result = ""
        for c in data:
            if 32 < ord(c) < 128:
                result += c
            else:
                result += "."
        return result

    @staticmethod
    def hexadecimal(data, separator=""):
        """
        Convert binary data to a string of hexadecimal numbers.

        @type  data: str
        @param data: Binary data.

        @type  separator: str
        @param separator:
            Separator between the hexadecimal representation of each character.

        @rtype:  str
        @return: Hexadecimal representation.
        """
        return separator.join(["%.2x" % ord(c) for c in data])

    @staticmethod
    def hexa_word(data, separator=" "):
        """
        Convert binary data to a string of hexadecimal WORDs.

        @type  data: str
        @param data: Binary data.

        @type  separator: str
        @param separator:
            Separator between the hexadecimal representation of each WORD.

        @rtype:  str
        @return: Hexadecimal representation.
        """
        if len(data) & 1 != 0:
            data += "\0"
        return separator.join(["%.4x" % struct.unpack("<H", data[i : i + 2])[0] for i in compat.xrange(0, len(data), 2)])

    @staticmethod
    def hexa_dword(data, separator=" "):
        """
        Convert binary data to a string of hexadecimal DWORDs.

        @type  data: str
        @param data: Binary data.

        @type  separator: str
        @param separator:
            Separator between the hexadecimal representation of each DWORD.

        @rtype:  str
        @return: Hexadecimal representation.
        """
        if len(data) & 3 != 0:
            data += "\0" * (4 - (len(data) & 3))
        return separator.join(["%.8x" % struct.unpack("<L", data[i : i + 4])[0] for i in compat.xrange(0, len(data), 4)])

    @staticmethod
    def hexa_qword(data, separator=" "):
        """
        Convert binary data to a string of hexadecimal QWORDs.

        @type  data: str
        @param data: Binary data.

        @type  separator: str
        @param separator:
            Separator between the hexadecimal representation of each QWORD.

        @rtype:  str
        @return: Hexadecimal representation.
        """
        if len(data) & 7 != 0:
            data += "\0" * (8 - (len(data) & 7))
        return separator.join(["%.16x" % struct.unpack("<Q", data[i : i + 8])[0] for i in compat.xrange(0, len(data), 8)])

    @classmethod
    def hexline(cls, data, separator=" ", width=None):
        """
        Dump a line of hexadecimal numbers from binary data.

        @type  data: str
        @param data: Binary data.

        @type  separator: str
        @param separator:
            Separator between the hexadecimal representation of each character.

        @type  width: int
        @param width:
            (Optional) Maximum number of characters to convert per text line.
            This value is also used for padding.

        @rtype:  str
        @return: Multiline output text.
        """
        if width is None:
            fmt = "%s  %s"
        else:
            fmt = "%%-%ds  %%-%ds" % ((len(separator) + 2) * width - 1, width)
        return fmt % (cls.hexadecimal(data, separator), cls.printable(data))

    @classmethod
    def hexblock(cls, data, address=None, bits=None, separator=" ", width=8):
        """
        Dump a block of hexadecimal numbers from binary data.
        Also show a printable text version of the data.

        @type  data: str
        @param data: Binary data.

        @type  address: str
        @param address: Memory address where the data was read from.

        @type  bits: int
        @param bits:
            (Optional) Number of bits of the target architecture.
            The default is platform dependent. See: L{HexDump.address_size}

        @type  separator: str
        @param separator:
            Separator between the hexadecimal representation of each character.

        @type  width: int
        @param width:
            (Optional) Maximum number of characters to convert per text line.

        @rtype:  str
        @return: Multiline output text.
        """
        return cls.hexblock_cb(cls.hexline, data, address, bits, width, cb_kwargs={"width": width, "separator": separator})

    @classmethod
    def hexblock_cb(cls, callback, data, address=None, bits=None, width=16, cb_args=(), cb_kwargs={}):
        """
        Dump a block of binary data using a callback function to convert each
        line of text.

        @type  callback: function
        @param callback: Callback function to convert each line of data.

        @type  data: str
        @param data: Binary data.

        @type  address: str
        @param address:
            (Optional) Memory address where the data was read from.

        @type  bits: int
        @param bits:
            (Optional) Number of bits of the target architecture.
            The default is platform dependent. See: L{HexDump.address_size}

        @type  cb_args: str
        @param cb_args:
            (Optional) Arguments to pass to the callback function.

        @type  cb_kwargs: str
        @param cb_kwargs:
            (Optional) Keyword arguments to pass to the callback function.

        @type  width: int
        @param width:
            (Optional) Maximum number of bytes to convert per text line.

        @rtype:  str
        @return: Multiline output text.
        """
        result = ""
        if address is None:
            for i in compat.xrange(0, len(data), width):
                result = "%s%s\n" % (result, callback(data[i : i + width], *cb_args, **cb_kwargs))
        else:
            for i in compat.xrange(0, len(data), width):
                result = "%s%s: %s\n" % (result, cls.address(address, bits), callback(data[i : i + width], *cb_args, **cb_kwargs))
                address += width
        return result

    @classmethod
    def hexblock_byte(cls, data, address=None, bits=None, separator=" ", width=16):
        """
        Dump a block of hexadecimal BYTEs from binary data.

        @type  data: str
        @param data: Binary data.

        @type  address: str
        @param address: Memory address where the data was read from.

        @type  bits: int
        @param bits:
            (Optional) Number of bits of the target architecture.
            The default is platform dependent. See: L{HexDump.address_size}

        @type  separator: str
        @param separator:
            Separator between the hexadecimal representation of each BYTE.

        @type  width: int
        @param width:
            (Optional) Maximum number of BYTEs to convert per text line.

        @rtype:  str
        @return: Multiline output text.
        """
        return cls.hexblock_cb(cls.hexadecimal, data, address, bits, width, cb_kwargs={"separator": separator})

    @classmethod
    def hexblock_word(cls, data, address=None, bits=None, separator=" ", width=8):
        """
        Dump a block of hexadecimal WORDs from binary data.

        @type  data: str
        @param data: Binary data.

        @type  address: str
        @param address: Memory address where the data was read from.

        @type  bits: int
        @param bits:
            (Optional) Number of bits of the target architecture.
            The default is platform dependent. See: L{HexDump.address_size}

        @type  separator: str
        @param separator:
            Separator between the hexadecimal representation of each WORD.

        @type  width: int
        @param width:
            (Optional) Maximum number of WORDs to convert per text line.

        @rtype:  str
        @return: Multiline output text.
        """
        return cls.hexblock_cb(cls.hexa_word, data, address, bits, width * 2, cb_kwargs={"separator": separator})

    @classmethod
    def hexblock_dword(cls, data, address=None, bits=None, separator=" ", width=4):
        """
        Dump a block of hexadecimal DWORDs from binary data.

        @type  data: str
        @param data: Binary data.

        @type  address: str
        @param address: Memory address where the data was read from.

        @type  bits: int
        @param bits:
            (Optional) Number of bits of the target architecture.
            The default is platform dependent. See: L{HexDump.address_size}

        @type  separator: str
        @param separator:
            Separator between the hexadecimal representation of each DWORD.

        @type  width: int
        @param width:
            (Optional) Maximum number of DWORDs to convert per text line.

        @rtype:  str
        @return: Multiline output text.
        """
        return cls.hexblock_cb(cls.hexa_dword, data, address, bits, width * 4, cb_kwargs={"separator": separator})

    @classmethod
    def hexblock_qword(cls, data, address=None, bits=None, separator=" ", width=2):
        """
        Dump a block of hexadecimal QWORDs from binary data.

        @type  data: str
        @param data: Binary data.

        @type  address: str
        @param address: Memory address where the data was read from.

        @type  bits: int
        @param bits:
            (Optional) Number of bits of the target architecture.
            The default is platform dependent. See: L{HexDump.address_size}

        @type  separator: str
        @param separator:
            Separator between the hexadecimal representation of each QWORD.

        @type  width: int
        @param width:
            (Optional) Maximum number of QWORDs to convert per text line.

        @rtype:  str
        @return: Multiline output text.
        """
        return cls.hexblock_cb(cls.hexa_qword, data, address, bits, width * 8, cb_kwargs={"separator": separator})


# ------------------------------------------------------------------------------

# TODO: implement an ANSI parser to simplify using colors


class Color(object):
    """
    Colored console output.
    """

    @staticmethod
    def _get_text_attributes():
        return win32.GetConsoleScreenBufferInfo().wAttributes

    @staticmethod
    def _set_text_attributes(wAttributes):
        win32.SetConsoleTextAttribute(wAttributes=wAttributes)

    # --------------------------------------------------------------------------

    @classmethod
    def can_use_colors(cls):
        """
        Determine if we can use colors.

        Colored output only works when the output is a real console, and fails
        when redirected to a file or pipe. Call this method before issuing a
        call to any other method of this class to make sure it's actually
        possible to use colors.

        @rtype:  bool
        @return: C{True} if it's possible to output text with color,
            C{False} otherwise.
        """
        try:
            cls._get_text_attributes()
            return True
        except Exception:
            return False

    @classmethod
    def reset(cls):
        "Reset the colors to the default values."
        cls._set_text_attributes(win32.FOREGROUND_GREY)

    # --------------------------------------------------------------------------

    # @classmethod
    # def underscore(cls, on = True):
    #    wAttributes = cls._get_text_attributes()
    #    if on:
    #        wAttributes |=  win32.COMMON_LVB_UNDERSCORE
    #    else:
    #        wAttributes &= ~win32.COMMON_LVB_UNDERSCORE
    #    cls._set_text_attributes(wAttributes)

    # --------------------------------------------------------------------------

    @classmethod
    def default(cls):
        "Make the current foreground color the default."
        wAttributes = cls._get_text_attributes()
        wAttributes &= ~win32.FOREGROUND_MASK
        wAttributes |= win32.FOREGROUND_GREY
        wAttributes &= ~win32.FOREGROUND_INTENSITY
        cls._set_text_attributes(wAttributes)

    @classmethod
    def light(cls):
        "Make the current foreground color light."
        wAttributes = cls._get_text_attributes()
        wAttributes |= win32.FOREGROUND_INTENSITY
        cls._set_text_attributes(wAttributes)

    @classmethod
    def dark(cls):
        "Make the current foreground color dark."
        wAttributes = cls._get_text_attributes()
        wAttributes &= ~win32.FOREGROUND_INTENSITY
        cls._set_text_attributes(wAttributes)

    @classmethod
    def black(cls):
        "Make the text foreground color black."
        wAttributes = cls._get_text_attributes()
        wAttributes &= ~win32.FOREGROUND_MASK
        # wAttributes |=  win32.FOREGROUND_BLACK
        cls._set_text_attributes(wAttributes)

    @classmethod
    def white(cls):
        "Make the text foreground color white."
        wAttributes = cls._get_text_attributes()
        wAttributes &= ~win32.FOREGROUND_MASK
        wAttributes |= win32.FOREGROUND_GREY
        cls._set_text_attributes(wAttributes)

    @classmethod
    def red(cls):
        "Make the text foreground color red."
        wAttributes = cls._get_text_attributes()
        wAttributes &= ~win32.FOREGROUND_MASK
        wAttributes |= win32.FOREGROUND_RED
        cls._set_text_attributes(wAttributes)

    @classmethod
    def green(cls):
        "Make the text foreground color green."
        wAttributes = cls._get_text_attributes()
        wAttributes &= ~win32.FOREGROUND_MASK
        wAttributes |= win32.FOREGROUND_GREEN
        cls._set_text_attributes(wAttributes)

    @classmethod
    def blue(cls):
        "Make the text foreground color blue."
        wAttributes = cls._get_text_attributes()
        wAttributes &= ~win32.FOREGROUND_MASK
        wAttributes |= win32.FOREGROUND_BLUE
        cls._set_text_attributes(wAttributes)

    @classmethod
    def cyan(cls):
        "Make the text foreground color cyan."
        wAttributes = cls._get_text_attributes()
        wAttributes &= ~win32.FOREGROUND_MASK
        wAttributes |= win32.FOREGROUND_CYAN
        cls._set_text_attributes(wAttributes)

    @classmethod
    def magenta(cls):
        "Make the text foreground color magenta."
        wAttributes = cls._get_text_attributes()
        wAttributes &= ~win32.FOREGROUND_MASK
        wAttributes |= win32.FOREGROUND_MAGENTA
        cls._set_text_attributes(wAttributes)

    @classmethod
    def yellow(cls):
        "Make the text foreground color yellow."
        wAttributes = cls._get_text_attributes()
        wAttributes &= ~win32.FOREGROUND_MASK
        wAttributes |= win32.FOREGROUND_YELLOW
        cls._set_text_attributes(wAttributes)

    # --------------------------------------------------------------------------

    @classmethod
    def bk_default(cls):
        "Make the current background color the default."
        wAttributes = cls._get_text_attributes()
        wAttributes &= ~win32.BACKGROUND_MASK
        # wAttributes |= win32.BACKGROUND_BLACK
        wAttributes &= ~win32.BACKGROUND_INTENSITY
        cls._set_text_attributes(wAttributes)

    @classmethod
    def bk_light(cls):
        "Make the current background color light."
        wAttributes = cls._get_text_attributes()
        wAttributes |= win32.BACKGROUND_INTENSITY
        cls._set_text_attributes(wAttributes)

    @classmethod
    def bk_dark(cls):
        "Make the current background color dark."
        wAttributes = cls._get_text_attributes()
        wAttributes &= ~win32.BACKGROUND_INTENSITY
        cls._set_text_attributes(wAttributes)

    @classmethod
    def bk_black(cls):
        "Make the text background color black."
        wAttributes = cls._get_text_attributes()
        wAttributes &= ~win32.BACKGROUND_MASK
        # wAttributes |= win32.BACKGROUND_BLACK
        cls._set_text_attributes(wAttributes)

    @classmethod
    def bk_white(cls):
        "Make the text background color white."
        wAttributes = cls._get_text_attributes()
        wAttributes &= ~win32.BACKGROUND_MASK
        wAttributes |= win32.BACKGROUND_GREY
        cls._set_text_attributes(wAttributes)

    @classmethod
    def bk_red(cls):
        "Make the text background color red."
        wAttributes = cls._get_text_attributes()
        wAttributes &= ~win32.BACKGROUND_MASK
        wAttributes |= win32.BACKGROUND_RED
        cls._set_text_attributes(wAttributes)

    @classmethod
    def bk_green(cls):
        "Make the text background color green."
        wAttributes = cls._get_text_attributes()
        wAttributes &= ~win32.BACKGROUND_MASK
        wAttributes |= win32.BACKGROUND_GREEN
        cls._set_text_attributes(wAttributes)

    @classmethod
    def bk_blue(cls):
        "Make the text background color blue."
        wAttributes = cls._get_text_attributes()
        wAttributes &= ~win32.BACKGROUND_MASK
        wAttributes |= win32.BACKGROUND_BLUE
        cls._set_text_attributes(wAttributes)

    @classmethod
    def bk_cyan(cls):
        "Make the text background color cyan."
        wAttributes = cls._get_text_attributes()
        wAttributes &= ~win32.BACKGROUND_MASK
        wAttributes |= win32.BACKGROUND_CYAN
        cls._set_text_attributes(wAttributes)

    @classmethod
    def bk_magenta(cls):
        "Make the text background color magenta."
        wAttributes = cls._get_text_attributes()
        wAttributes &= ~win32.BACKGROUND_MASK
        wAttributes |= win32.BACKGROUND_MAGENTA
        cls._set_text_attributes(wAttributes)

    @classmethod
    def bk_yellow(cls):
        "Make the text background color yellow."
        wAttributes = cls._get_text_attributes()
        wAttributes &= ~win32.BACKGROUND_MASK
        wAttributes |= win32.BACKGROUND_YELLOW
        cls._set_text_attributes(wAttributes)


# ------------------------------------------------------------------------------

# TODO: another class for ASCII boxes


class Table(object):
    """
    Text based table. The number of columns and the width of each column
    is automatically calculated.
    """

    def __init__(self, sep=" "):
        """
        @type  sep: str
        @param sep: Separator between cells in each row.
        """
        self.__cols = list()
        self.__width = list()
        self.__sep = sep

    def addRow(self, *row):
        """
        Add a row to the table. All items are converted to strings.

        @type    row: tuple
        @keyword row: Each argument is a cell in the table.
        """
        row = [str(item) for item in row]
        len_row = [len(item) for item in row]
        width = self.__width
        len_old = len(width)
        len_new = len(row)
        known = min(len_old, len_new)
        missing = len_new - len_old
        if missing > 0:
            width.extend(len_row[-missing:])
        elif missing < 0:
            len_row.extend([0] * (-missing))
        self.__width = [max(width[i], len_row[i]) for i in compat.xrange(len(len_row))]
        self.__cols.append(row)

    def justify(self, column, direction):
        """
        Make the text in a column left or right justified.

        @type  column: int
        @param column: Index of the column.

        @type  direction: int
        @param direction:
            C{-1} to justify left,
            C{1} to justify right.

        @raise IndexError: Bad column index.
        @raise ValueError: Bad direction value.
        """
        if direction == -1:
            self.__width[column] = abs(self.__width[column])
        elif direction == 1:
            self.__width[column] = -abs(self.__width[column])
        else:
            raise ValueError("Bad direction value.")

    def getWidth(self):
        """
        Get the width of the text output for the table.

        @rtype:  int
        @return: Width in characters for the text output,
            including the newline character.
        """
        width = 0
        if self.__width:
            width = sum(abs(x) for x in self.__width)
            width = width + len(self.__width) * len(self.__sep) + 1
        return width

    def getOutput(self):
        """
        Get the text output for the table.

        @rtype:  str
        @return: Text output.
        """
        return "%s\n" % "\n".join(self.yieldOutput())

    def yieldOutput(self):
        """
        Generate the text output for the table.

        @rtype:  generator of str
        @return: Text output.
        """
        width = self.__width
        if width:
            num_cols = len(width)
            fmt = ["%%%ds" % -w for w in width]
            if width[-1] > 0:
                fmt[-1] = "%s"
            fmt = self.__sep.join(fmt)
            for row in self.__cols:
                row.extend([""] * (num_cols - len(row)))
                yield fmt % tuple(row)

    def show(self):
        """
        Print the text output for the table.
        """
        print(self.getOutput())


# ------------------------------------------------------------------------------


class CrashDump(StaticClass):
    """
    Static functions for crash dumps.

    @type reg_template: str
    @cvar reg_template: Template for the L{dump_registers} method.
    """

    # Templates for the dump_registers method.
    reg_template = {
        win32.ARCH_I386: (
            "eax=%(Eax).8x ebx=%(Ebx).8x ecx=%(Ecx).8x edx=%(Edx).8x esi=%(Esi).8x edi=%(Edi).8x\n"
            "eip=%(Eip).8x esp=%(Esp).8x ebp=%(Ebp).8x %(efl_dump)s\n"
            "cs=%(SegCs).4x  ss=%(SegSs).4x  ds=%(SegDs).4x  es=%(SegEs).4x  fs=%(SegFs).4x  gs=%(SegGs).4x             efl=%(EFlags).8x\n"
        ),
        win32.ARCH_AMD64: (
            "rax=%(Rax).16x rbx=%(Rbx).16x rcx=%(Rcx).16x\n"
            "rdx=%(Rdx).16x rsi=%(Rsi).16x rdi=%(Rdi).16x\n"
            "rip=%(Rip).16x rsp=%(Rsp).16x rbp=%(Rbp).16x\n"
            " r8=%(R8).16x  r9=%(R9).16x r10=%(R10).16x\n"
            "r11=%(R11).16x r12=%(R12).16x r13=%(R13).16x\n"
            "r14=%(R14).16x r15=%(R15).16x\n"
            "%(efl_dump)s\n"
            "cs=%(SegCs).4x  ss=%(SegSs).4x  ds=%(SegDs).4x  es=%(SegEs).4x  fs=%(SegFs).4x  gs=%(SegGs).4x             efl=%(EFlags).8x\n"
        ),
    }

    @staticmethod
    def dump_flags(efl):
        """
        Dump the x86 processor flags.
        The output mimics that of the WinDBG debugger.
        Used by L{dump_registers}.

        @type  efl: int
        @param efl: Value of the eFlags register.

        @rtype:  str
        @return: Text suitable for logging.
        """
        if efl is None:
            return ""
        efl_dump = "iopl=%1d" % ((efl & 0x3000) >> 12)
        if efl & 0x100000:
            efl_dump += " vip"
        else:
            efl_dump += "    "
        if efl & 0x80000:
            efl_dump += " vif"
        else:
            efl_dump += "    "
        # 0x20000 ???
        if efl & 0x800:
            efl_dump += " ov"  # Overflow
        else:
            efl_dump += " no"  # No overflow
        if efl & 0x400:
            efl_dump += " dn"  # Downwards
        else:
            efl_dump += " up"  # Upwards
        if efl & 0x200:
            efl_dump += " ei"  # Enable interrupts
        else:
            efl_dump += " di"  # Disable interrupts
        # 0x100 trap flag
        if efl & 0x80:
            efl_dump += " ng"  # Negative
        else:
            efl_dump += " pl"  # Positive
        if efl & 0x40:
            efl_dump += " zr"  # Zero
        else:
            efl_dump += " nz"  # Nonzero
        if efl & 0x10:
            efl_dump += " ac"  # Auxiliary carry
        else:
            efl_dump += " na"  # No auxiliary carry
        # 0x8 ???
        if efl & 0x4:
            efl_dump += " pe"  # Parity odd
        else:
            efl_dump += " po"  # Parity even
        # 0x2 ???
        if efl & 0x1:
            efl_dump += " cy"  # Carry
        else:
            efl_dump += " nc"  # No carry
        return efl_dump

    @classmethod
    def dump_registers(cls, registers, arch=None):
        """
        Dump the x86/x64 processor register values.
        The output mimics that of the WinDBG debugger.

        @type  registers: dict( str S{->} int )
        @param registers: Dictionary mapping register names to their values.

        @type  arch: str
        @param arch: Architecture of the machine whose registers were dumped.
            Defaults to the current architecture.
            Currently only the following architectures are supported:
             - L{win32.ARCH_I386}
             - L{win32.ARCH_AMD64}

        @rtype:  str
        @return: Text suitable for logging.
        """
        if registers is None:
            return ""
        if arch is None:
            if "Eax" in registers:
                arch = win32.ARCH_I386
            elif "Rax" in registers:
                arch = win32.ARCH_AMD64
            else:
                arch = "Unknown"
        if arch not in cls.reg_template:
            msg = "Don't know how to dump the registers for architecture: %s"
            raise NotImplementedError(msg % arch)
        registers = registers.copy()
        registers["efl_dump"] = cls.dump_flags(registers["EFlags"])
        return cls.reg_template[arch] % registers

    @staticmethod
    def dump_registers_peek(registers, data, separator=" ", width=16):
        """
        Dump data pointed to by the given registers, if any.

        @type  registers: dict( str S{->} int )
        @param registers: Dictionary mapping register names to their values.
            This value is returned by L{Thread.get_context}.

        @type  data: dict( str S{->} str )
        @param data: Dictionary mapping register names to the data they point to.
            This value is returned by L{Thread.peek_pointers_in_registers}.

        @rtype:  str
        @return: Text suitable for logging.
        """
        if None in (registers, data):
            return ""
        names = compat.keys(data)
        names.sort()
        result = ""
        for reg_name in names:
            tag = reg_name.lower()
            dumped = HexDump.hexline(data[reg_name], separator, width)
            result += "%s -> %s\n" % (tag, dumped)
        return result

    @staticmethod
    def dump_data_peek(data, base=0, separator=" ", width=16, bits=None):
        """
        Dump data from pointers guessed within the given binary data.

        @type  data: str
        @param data: Dictionary mapping offsets to the data they point to.

        @type  base: int
        @param base: Base offset.

        @type  bits: int
        @param bits:
            (Optional) Number of bits of the target architecture.
            The default is platform dependent. See: L{HexDump.address_size}

        @rtype:  str
        @return: Text suitable for logging.
        """
        if data is None:
            return ""
        pointers = compat.keys(data)
        pointers.sort()
        result = ""
        for offset in pointers:
            dumped = HexDump.hexline(data[offset], separator, width)
            address = HexDump.address(base + offset, bits)
            result += "%s -> %s\n" % (address, dumped)
        return result

    @staticmethod
    def dump_stack_peek(data, separator=" ", width=16, arch=None):
        """
        Dump data from pointers guessed within the given stack dump.

        @type  data: str
        @param data: Dictionary mapping stack offsets to the data they point to.

        @type  separator: str
        @param separator:
            Separator between the hexadecimal representation of each character.

        @type  width: int
        @param width:
            (Optional) Maximum number of characters to convert per text line.
            This value is also used for padding.

        @type  arch: str
        @param arch: Architecture of the machine whose registers were dumped.
            Defaults to the current architecture.

        @rtype:  str
        @return: Text suitable for logging.
        """
        if data is None:
            return ""
        if arch is None:
            arch = win32.arch
        pointers = compat.keys(data)
        pointers.sort()
        result = ""
        if pointers:
            if arch == win32.ARCH_I386:
                spreg = "esp"
            elif arch == win32.ARCH_AMD64:
                spreg = "rsp"
            else:
                spreg = "STACK"  # just a generic tag
            tag_fmt = "[%s+0x%%.%dx]" % (spreg, len("%x" % pointers[-1]))
            for offset in pointers:
                dumped = HexDump.hexline(data[offset], separator, width)
                tag = tag_fmt % offset
                result += "%s -> %s\n" % (tag, dumped)
        return result

    @staticmethod
    def dump_stack_trace(stack_trace, bits=None):
        """
        Dump a stack trace, as returned by L{Thread.get_stack_trace} with the
        C{bUseLabels} parameter set to C{False}.

        @type  stack_trace: list( int, int, str )
        @param stack_trace: Stack trace as a list of tuples of
            ( return address, frame pointer, module filename )

        @type  bits: int
        @param bits:
            (Optional) Number of bits of the target architecture.
            The default is platform dependent. See: L{HexDump.address_size}

        @rtype:  str
        @return: Text suitable for logging.
        """
        if not stack_trace:
            return ""
        table = Table()
        table.addRow("Frame", "Origin", "Module")
        for fp, ra, mod in stack_trace:
            fp_d = HexDump.address(fp, bits)
            ra_d = HexDump.address(ra, bits)
            table.addRow(fp_d, ra_d, mod)
        return table.getOutput()

    @staticmethod
    def dump_stack_trace_with_labels(stack_trace, bits=None):
        """
        Dump a stack trace,
        as returned by L{Thread.get_stack_trace_with_labels}.

        @type  stack_trace: list( int, int, str )
        @param stack_trace: Stack trace as a list of tuples of
            ( return address, frame pointer, module filename )

        @type  bits: int
        @param bits:
            (Optional) Number of bits of the target architecture.
            The default is platform dependent. See: L{HexDump.address_size}

        @rtype:  str
        @return: Text suitable for logging.
        """
        if not stack_trace:
            return ""
        table = Table()
        table.addRow("Frame", "Origin")
        for fp, label in stack_trace:
            table.addRow(HexDump.address(fp, bits), label)
        return table.getOutput()

    # TODO
    # + Instead of a star when EIP points to, it would be better to show
    # any register value (or other values like the exception address) that
    # points to a location in the dissassembled code.
    # + It'd be very useful to show some labels here.
    # + It'd be very useful to show register contents for code at EIP
    @staticmethod
    def dump_code(disassembly, pc=None, bLowercase=True, bits=None):
        """
        Dump a disassembly. Optionally mark where the program counter is.

        @type  disassembly: list of tuple( int, int, str, str )
        @param disassembly: Disassembly dump as returned by
            L{Process.disassemble} or L{Thread.disassemble_around_pc}.

        @type  pc: int
        @param pc: (Optional) Program counter.

        @type  bLowercase: bool
        @param bLowercase: (Optional) If C{True} convert the code to lowercase.

        @type  bits: int
        @param bits:
            (Optional) Number of bits of the target architecture.
            The default is platform dependent. See: L{HexDump.address_size}

        @rtype:  str
        @return: Text suitable for logging.
        """
        if not disassembly:
            return ""
        table = Table(sep=" | ")
        for addr, size, code, dump in disassembly:
            if bLowercase:
                code = code.lower()
            if addr == pc:
                addr = " * %s" % HexDump.address(addr, bits)
            else:
                addr = "   %s" % HexDump.address(addr, bits)
            table.addRow(addr, dump, code)
        table.justify(1, 1)
        return table.getOutput()

    @staticmethod
    def dump_code_line(disassembly_line, bShowAddress=True, bShowDump=True, bLowercase=True, dwDumpWidth=None, dwCodeWidth=None, bits=None):
        """
        Dump a single line of code. To dump a block of code use L{dump_code}.

        @type  disassembly_line: tuple( int, int, str, str )
        @param disassembly_line: Single item of the list returned by
            L{Process.disassemble} or L{Thread.disassemble_around_pc}.

        @type  bShowAddress: bool
        @param bShowAddress: (Optional) If C{True} show the memory address.

        @type  bShowDump: bool
        @param bShowDump: (Optional) If C{True} show the hexadecimal dump.

        @type  bLowercase: bool
        @param bLowercase: (Optional) If C{True} convert the code to lowercase.

        @type  dwDumpWidth: int or None
        @param dwDumpWidth: (Optional) Width in characters of the hex dump.

        @type  dwCodeWidth: int or None
        @param dwCodeWidth: (Optional) Width in characters of the code.

        @type  bits: int
        @param bits:
            (Optional) Number of bits of the target architecture.
            The default is platform dependent. See: L{HexDump.address_size}

        @rtype:  str
        @return: Text suitable for logging.
        """
        if bits is None:
            address_size = HexDump.address_size
        else:
            address_size = bits / 4
        (addr, size, code, dump) = disassembly_line
        dump = dump.replace(" ", "")
        result = list()
        fmt = ""
        if bShowAddress:
            result.append(HexDump.address(addr, bits))
            fmt += "%%%ds:" % address_size
        if bShowDump:
            result.append(dump)
            if dwDumpWidth:
                fmt += " %%-%ds" % dwDumpWidth
            else:
                fmt += " %s"
        if bLowercase:
            code = code.lower()
        result.append(code)
        if dwCodeWidth:
            fmt += " %%-%ds" % dwCodeWidth
        else:
            fmt += " %s"
        return fmt % tuple(result)

    @staticmethod
    def dump_memory_map(memoryMap, mappedFilenames=None, bits=None):
        """
        Dump the memory map of a process. Optionally show the filenames for
        memory mapped files as well.

        @type  memoryMap: list( L{win32.MemoryBasicInformation} )
        @param memoryMap: Memory map returned by L{Process.get_memory_map}.

        @type  mappedFilenames: dict( int S{->} str )
        @param mappedFilenames: (Optional) Memory mapped filenames
            returned by L{Process.get_mapped_filenames}.

        @type  bits: int
        @param bits:
            (Optional) Number of bits of the target architecture.
            The default is platform dependent. See: L{HexDump.address_size}

        @rtype:  str
        @return: Text suitable for logging.
        """
        if not memoryMap:
            return ""

        table = Table()
        if mappedFilenames:
            table.addRow("Address", "Size", "State", "Access", "Type", "File")
        else:
            table.addRow("Address", "Size", "State", "Access", "Type")

        # For each memory block in the map...
        for mbi in memoryMap:
            # Address and size of memory block.
            BaseAddress = HexDump.address(mbi.BaseAddress, bits)
            RegionSize = HexDump.address(mbi.RegionSize, bits)

            # State (free or allocated).
            mbiState = mbi.State
            if mbiState == win32.MEM_RESERVE:
                State = "Reserved"
            elif mbiState == win32.MEM_COMMIT:
                State = "Commited"
            elif mbiState == win32.MEM_FREE:
                State = "Free"
            else:
                State = "Unknown"

            # Page protection bits (R/W/X/G).
            if mbiState != win32.MEM_COMMIT:
                Protect = ""
            else:
                mbiProtect = mbi.Protect
                if mbiProtect & win32.PAGE_NOACCESS:
                    Protect = "--- "
                elif mbiProtect & win32.PAGE_READONLY:
                    Protect = "R-- "
                elif mbiProtect & win32.PAGE_READWRITE:
                    Protect = "RW- "
                elif mbiProtect & win32.PAGE_WRITECOPY:
                    Protect = "RC- "
                elif mbiProtect & win32.PAGE_EXECUTE:
                    Protect = "--X "
                elif mbiProtect & win32.PAGE_EXECUTE_READ:
                    Protect = "R-X "
                elif mbiProtect & win32.PAGE_EXECUTE_READWRITE:
                    Protect = "RWX "
                elif mbiProtect & win32.PAGE_EXECUTE_WRITECOPY:
                    Protect = "RCX "
                else:
                    Protect = "??? "
                if mbiProtect & win32.PAGE_GUARD:
                    Protect += "G"
                else:
                    Protect += "-"
                if mbiProtect & win32.PAGE_NOCACHE:
                    Protect += "N"
                else:
                    Protect += "-"
                if mbiProtect & win32.PAGE_WRITECOMBINE:
                    Protect += "W"
                else:
                    Protect += "-"

            # Type (file mapping, executable image, or private memory).
            mbiType = mbi.Type
            if mbiType == win32.MEM_IMAGE:
                Type = "Image"
            elif mbiType == win32.MEM_MAPPED:
                Type = "Mapped"
            elif mbiType == win32.MEM_PRIVATE:
                Type = "Private"
            elif mbiType == 0:
                Type = ""
            else:
                Type = "Unknown"

            # Output a row in the table.
            if mappedFilenames:
                FileName = mappedFilenames.get(mbi.BaseAddress, "")
                table.addRow(BaseAddress, RegionSize, State, Protect, Type, FileName)
            else:
                table.addRow(BaseAddress, RegionSize, State, Protect, Type)

        # Return the table output.
        return table.getOutput()


# ------------------------------------------------------------------------------


class DebugLog(StaticClass):
    "Static functions for debug logging."

    @staticmethod
    def log_text(text):
        """
        Log lines of text, inserting a timestamp.

        @type  text: str
        @param text: Text to log.

        @rtype:  str
        @return: Log line.
        """
        if text.endswith("\n"):
            text = text[: -len("\n")]
        # text  = text.replace('\n', '\n\t\t')           # text CSV
        ltime = time.strftime("%X")
        msecs = (time.time() % 1) * 1000
        return "[%s.%04d] %s" % (ltime, msecs, text)
        # return '[%s.%04d]\t%s' % (ltime, msecs, text)  # text CSV

    @classmethod
    def log_event(cls, event, text=None):
        """
        Log lines of text associated with a debug event.

        @type  event: L{Event}
        @param event: Event object.

        @type  text: str
        @param text: (Optional) Text to log. If no text is provided the default
            is to show a description of the event itself.

        @rtype:  str
        @return: Log line.
        """
        if not text:
            if event.get_event_code() == win32.EXCEPTION_DEBUG_EVENT:
                what = event.get_exception_description()
                if event.is_first_chance():
                    what = "%s (first chance)" % what
                else:
                    what = "%s (second chance)" % what
                try:
                    address = event.get_fault_address()
                except NotImplementedError:
                    address = event.get_exception_address()
            else:
                what = event.get_event_name()
                address = event.get_thread().get_pc()
            process = event.get_process()
            label = process.get_label_at_address(address)
            address = HexDump.address(address, process.get_bits())
            if label:
                where = "%s (%s)" % (address, label)
            else:
                where = address
            text = "%s at %s" % (what, where)
        text = "pid %d tid %d: %s" % (event.get_pid(), event.get_tid(), text)
        # text = 'pid %d tid %d:\t%s' % (event.get_pid(), event.get_tid(), text)     # text CSV
        return cls.log_text(text)


# ------------------------------------------------------------------------------


class Logger(object):
    """
    Logs text to standard output and/or a text file.

    @type logfile: str or None
    @ivar logfile: Append messages to this text file.

    @type verbose: bool
    @ivar verbose: C{True} to print messages to standard output.

    @type fd: file
    @ivar fd: File object where log messages are printed to.
        C{None} if no log file is used.
    """

    def __init__(self, logfile=None, verbose=True):
        """
        @type  logfile: str or None
        @param logfile: Append messages to this text file.

        @type  verbose: bool
        @param verbose: C{True} to print messages to standard output.
        """
        self.verbose = verbose
        self.logfile = logfile
        if self.logfile:
            self.fd = open(self.logfile, "a+")

    def __logfile_error(self, e):
        """
        Shows an error message to standard error
        if the log file can't be written to.

        Used internally.

        @type  e: Exception
        @param e: Exception raised when trying to write to the log file.
        """
        from sys import stderr

        msg = "Warning, error writing log file %s: %s\n"
        msg = msg % (self.logfile, str(e))
        stderr.write(DebugLog.log_text(msg))
        self.logfile = None
        self.fd = None

    def __do_log(self, text):
        """
        Writes the given text verbatim into the log file (if any)
        and/or standard input (if the verbose flag is turned on).

        Used internally.

        @type  text: str
        @param text: Text to print.
        """
        if isinstance(text, compat.unicode):
            text = text.encode("cp1252")
        if self.verbose:
            print(text)
        if self.logfile:
            try:
                self.fd.writelines("%s\n" % text)
            except IOError:
                e = sys.exc_info()[1]
                self.__logfile_error(e)

    def log_text(self, text):
        """
        Log lines of text, inserting a timestamp.

        @type  text: str
        @param text: Text to log.
        """
        self.__do_log(DebugLog.log_text(text))

    def log_event(self, event, text=None):
        """
        Log lines of text associated with a debug event.

        @type  event: L{Event}
        @param event: Event object.

        @type  text: str
        @param text: (Optional) Text to log. If no text is provided the default
            is to show a description of the event itself.
        """
        self.__do_log(DebugLog.log_event(event, text))

    def log_exc(self):
        """
        Log lines of text associated with the last Python exception.
        """
        self.__do_log("Exception raised: %s" % traceback.format_exc())

    def is_enabled(self):
        """
        Determines if the logger will actually print anything when the log_*
        methods are called.

        This may save some processing if the log text requires a lengthy
        calculation to prepare. If no log file is set and stdout logging
        is disabled, there's no point in preparing a log text that won't
        be shown to anyone.

        @rtype:  bool
        @return: C{True} if a log file was set and/or standard output logging
            is enabled, or C{False} otherwise.
        """
        return self.verbose or self.logfile