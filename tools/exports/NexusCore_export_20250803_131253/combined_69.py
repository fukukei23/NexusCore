
# === NexusCore/tools\exports\export_20250803_114325\combined_35.py ===

# === NexusCore/openenv\Lib\site-packages\debugpy\_vendored\pydevd\pydevd_attach_to_process\winappdbg\win32\advapi32.py ===
#!/usr/bin/env python
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
Wrapper for advapi32.dll in ctypes.
"""

__revision__ = "$Id$"

from winappdbg.win32.defines import *
from winappdbg.win32.kernel32 import *

# XXX TODO
# + add transacted registry operations

# ==============================================================================
# This is used later on to calculate the list of exported symbols.
_all = None
_all = set(vars().keys())
# ==============================================================================

# --- Constants ----------------------------------------------------------------

# Privilege constants
SE_ASSIGNPRIMARYTOKEN_NAME = "SeAssignPrimaryTokenPrivilege"
SE_AUDIT_NAME = "SeAuditPrivilege"
SE_BACKUP_NAME = "SeBackupPrivilege"
SE_CHANGE_NOTIFY_NAME = "SeChangeNotifyPrivilege"
SE_CREATE_GLOBAL_NAME = "SeCreateGlobalPrivilege"
SE_CREATE_PAGEFILE_NAME = "SeCreatePagefilePrivilege"
SE_CREATE_PERMANENT_NAME = "SeCreatePermanentPrivilege"
SE_CREATE_SYMBOLIC_LINK_NAME = "SeCreateSymbolicLinkPrivilege"
SE_CREATE_TOKEN_NAME = "SeCreateTokenPrivilege"
SE_DEBUG_NAME = "SeDebugPrivilege"
SE_ENABLE_DELEGATION_NAME = "SeEnableDelegationPrivilege"
SE_IMPERSONATE_NAME = "SeImpersonatePrivilege"
SE_INC_BASE_PRIORITY_NAME = "SeIncreaseBasePriorityPrivilege"
SE_INCREASE_QUOTA_NAME = "SeIncreaseQuotaPrivilege"
SE_INC_WORKING_SET_NAME = "SeIncreaseWorkingSetPrivilege"
SE_LOAD_DRIVER_NAME = "SeLoadDriverPrivilege"
SE_LOCK_MEMORY_NAME = "SeLockMemoryPrivilege"
SE_MACHINE_ACCOUNT_NAME = "SeMachineAccountPrivilege"
SE_MANAGE_VOLUME_NAME = "SeManageVolumePrivilege"
SE_PROF_SINGLE_PROCESS_NAME = "SeProfileSingleProcessPrivilege"
SE_RELABEL_NAME = "SeRelabelPrivilege"
SE_REMOTE_SHUTDOWN_NAME = "SeRemoteShutdownPrivilege"
SE_RESTORE_NAME = "SeRestorePrivilege"
SE_SECURITY_NAME = "SeSecurityPrivilege"
SE_SHUTDOWN_NAME = "SeShutdownPrivilege"
SE_SYNC_AGENT_NAME = "SeSyncAgentPrivilege"
SE_SYSTEM_ENVIRONMENT_NAME = "SeSystemEnvironmentPrivilege"
SE_SYSTEM_PROFILE_NAME = "SeSystemProfilePrivilege"
SE_SYSTEMTIME_NAME = "SeSystemtimePrivilege"
SE_TAKE_OWNERSHIP_NAME = "SeTakeOwnershipPrivilege"
SE_TCB_NAME = "SeTcbPrivilege"
SE_TIME_ZONE_NAME = "SeTimeZonePrivilege"
SE_TRUSTED_CREDMAN_ACCESS_NAME = "SeTrustedCredManAccessPrivilege"
SE_UNDOCK_NAME = "SeUndockPrivilege"
SE_UNSOLICITED_INPUT_NAME = "SeUnsolicitedInputPrivilege"

SE_PRIVILEGE_ENABLED_BY_DEFAULT = 0x00000001
SE_PRIVILEGE_ENABLED = 0x00000002
SE_PRIVILEGE_REMOVED = 0x00000004
SE_PRIVILEGE_USED_FOR_ACCESS = 0x80000000

TOKEN_ADJUST_PRIVILEGES = 0x00000020

LOGON_WITH_PROFILE = 0x00000001
LOGON_NETCREDENTIALS_ONLY = 0x00000002

# Token access rights
TOKEN_ASSIGN_PRIMARY = 0x0001
TOKEN_DUPLICATE = 0x0002
TOKEN_IMPERSONATE = 0x0004
TOKEN_QUERY = 0x0008
TOKEN_QUERY_SOURCE = 0x0010
TOKEN_ADJUST_PRIVILEGES = 0x0020
TOKEN_ADJUST_GROUPS = 0x0040
TOKEN_ADJUST_DEFAULT = 0x0080
TOKEN_ADJUST_SESSIONID = 0x0100
TOKEN_READ = STANDARD_RIGHTS_READ | TOKEN_QUERY
TOKEN_ALL_ACCESS = (
    STANDARD_RIGHTS_REQUIRED
    | TOKEN_ASSIGN_PRIMARY
    | TOKEN_DUPLICATE
    | TOKEN_IMPERSONATE
    | TOKEN_QUERY
    | TOKEN_QUERY_SOURCE
    | TOKEN_ADJUST_PRIVILEGES
    | TOKEN_ADJUST_GROUPS
    | TOKEN_ADJUST_DEFAULT
    | TOKEN_ADJUST_SESSIONID
)

# Predefined HKEY values
HKEY_CLASSES_ROOT = 0x80000000
HKEY_CURRENT_USER = 0x80000001
HKEY_LOCAL_MACHINE = 0x80000002
HKEY_USERS = 0x80000003
HKEY_PERFORMANCE_DATA = 0x80000004
HKEY_CURRENT_CONFIG = 0x80000005

# Registry access rights
KEY_ALL_ACCESS = 0xF003F
KEY_CREATE_LINK = 0x0020
KEY_CREATE_SUB_KEY = 0x0004
KEY_ENUMERATE_SUB_KEYS = 0x0008
KEY_EXECUTE = 0x20019
KEY_NOTIFY = 0x0010
KEY_QUERY_VALUE = 0x0001
KEY_READ = 0x20019
KEY_SET_VALUE = 0x0002
KEY_WOW64_32KEY = 0x0200
KEY_WOW64_64KEY = 0x0100
KEY_WRITE = 0x20006

# Registry value types
REG_NONE = 0
REG_SZ = 1
REG_EXPAND_SZ = 2
REG_BINARY = 3
REG_DWORD = 4
REG_DWORD_LITTLE_ENDIAN = REG_DWORD
REG_DWORD_BIG_ENDIAN = 5
REG_LINK = 6
REG_MULTI_SZ = 7
REG_RESOURCE_LIST = 8
REG_FULL_RESOURCE_DESCRIPTOR = 9
REG_RESOURCE_REQUIREMENTS_LIST = 10
REG_QWORD = 11
REG_QWORD_LITTLE_ENDIAN = REG_QWORD

# --- TOKEN_PRIVILEGE structure ------------------------------------------------


# typedef struct _LUID {
#   DWORD LowPart;
#   LONG HighPart;
# } LUID,
#  *PLUID;
class LUID(Structure):
    _fields_ = [
        ("LowPart", DWORD),
        ("HighPart", LONG),
    ]


PLUID = POINTER(LUID)


# typedef struct _LUID_AND_ATTRIBUTES {
#   LUID Luid;
#   DWORD Attributes;
# } LUID_AND_ATTRIBUTES,
#  *PLUID_AND_ATTRIBUTES;
class LUID_AND_ATTRIBUTES(Structure):
    _fields_ = [
        ("Luid", LUID),
        ("Attributes", DWORD),
    ]


# typedef struct _TOKEN_PRIVILEGES {
#   DWORD PrivilegeCount;
#   LUID_AND_ATTRIBUTES Privileges[ANYSIZE_ARRAY];
# } TOKEN_PRIVILEGES,
#  *PTOKEN_PRIVILEGES;
class TOKEN_PRIVILEGES(Structure):
    _fields_ = [
        ("PrivilegeCount", DWORD),
        ##        ("Privileges",      LUID_AND_ATTRIBUTES * ANYSIZE_ARRAY),
        ("Privileges", LUID_AND_ATTRIBUTES),
    ]
    # See comments on AdjustTokenPrivileges about this structure


PTOKEN_PRIVILEGES = POINTER(TOKEN_PRIVILEGES)

# --- GetTokenInformation enums and structures ---------------------------------

# typedef enum _TOKEN_INFORMATION_CLASS {
#   TokenUser                              = 1,
#   TokenGroups,
#   TokenPrivileges,
#   TokenOwner,
#   TokenPrimaryGroup,
#   TokenDefaultDacl,
#   TokenSource,
#   TokenType,
#   TokenImpersonationLevel,
#   TokenStatistics,
#   TokenRestrictedSids,
#   TokenSessionId,
#   TokenGroupsAndPrivileges,
#   TokenSessionReference,
#   TokenSandBoxInert,
#   TokenAuditPolicy,
#   TokenOrigin,
#   TokenElevationType,
#   TokenLinkedToken,
#   TokenElevation,
#   TokenHasRestrictions,
#   TokenAccessInformation,
#   TokenVirtualizationAllowed,
#   TokenVirtualizationEnabled,
#   TokenIntegrityLevel,
#   TokenUIAccess,
#   TokenMandatoryPolicy,
#   TokenLogonSid,
#   TokenIsAppContainer,
#   TokenCapabilities,
#   TokenAppContainerSid,
#   TokenAppContainerNumber,
#   TokenUserClaimAttributes,
#   TokenDeviceClaimAttributes,
#   TokenRestrictedUserClaimAttributes,
#   TokenRestrictedDeviceClaimAttributes,
#   TokenDeviceGroups,
#   TokenRestrictedDeviceGroups,
#   TokenSecurityAttributes,
#   TokenIsRestricted,
#   MaxTokenInfoClass
# } TOKEN_INFORMATION_CLASS, *PTOKEN_INFORMATION_CLASS;

TOKEN_INFORMATION_CLASS = ctypes.c_int

TokenUser = 1
TokenGroups = 2
TokenPrivileges = 3
TokenOwner = 4
TokenPrimaryGroup = 5
TokenDefaultDacl = 6
TokenSource = 7
TokenType = 8
TokenImpersonationLevel = 9
TokenStatistics = 10
TokenRestrictedSids = 11
TokenSessionId = 12
TokenGroupsAndPrivileges = 13
TokenSessionReference = 14
TokenSandBoxInert = 15
TokenAuditPolicy = 16
TokenOrigin = 17
TokenElevationType = 18
TokenLinkedToken = 19
TokenElevation = 20
TokenHasRestrictions = 21
TokenAccessInformation = 22
TokenVirtualizationAllowed = 23
TokenVirtualizationEnabled = 24
TokenIntegrityLevel = 25
TokenUIAccess = 26
TokenMandatoryPolicy = 27
TokenLogonSid = 28
TokenIsAppContainer = 29
TokenCapabilities = 30
TokenAppContainerSid = 31
TokenAppContainerNumber = 32
TokenUserClaimAttributes = 33
TokenDeviceClaimAttributes = 34
TokenRestrictedUserClaimAttributes = 35
TokenRestrictedDeviceClaimAttributes = 36
TokenDeviceGroups = 37
TokenRestrictedDeviceGroups = 38
TokenSecurityAttributes = 39
TokenIsRestricted = 40
MaxTokenInfoClass = 41

# typedef enum tagTOKEN_TYPE {
#   TokenPrimary         = 1,
#   TokenImpersonation
# } TOKEN_TYPE, *PTOKEN_TYPE;

TOKEN_TYPE = ctypes.c_int
PTOKEN_TYPE = POINTER(TOKEN_TYPE)

TokenPrimary = 1
TokenImpersonation = 2

# typedef enum  {
#   TokenElevationTypeDefault   = 1,
#   TokenElevationTypeFull,
#   TokenElevationTypeLimited
# } TOKEN_ELEVATION_TYPE , *PTOKEN_ELEVATION_TYPE;

TokenElevationTypeDefault = 1
TokenElevationTypeFull = 2
TokenElevationTypeLimited = 3

TOKEN_ELEVATION_TYPE = ctypes.c_int
PTOKEN_ELEVATION_TYPE = POINTER(TOKEN_ELEVATION_TYPE)

# typedef enum _SECURITY_IMPERSONATION_LEVEL {
#   SecurityAnonymous,
#   SecurityIdentification,
#   SecurityImpersonation,
#   SecurityDelegation
# } SECURITY_IMPERSONATION_LEVEL, *PSECURITY_IMPERSONATION_LEVEL;

SecurityAnonymous = 0
SecurityIdentification = 1
SecurityImpersonation = 2
SecurityDelegation = 3

SECURITY_IMPERSONATION_LEVEL = ctypes.c_int
PSECURITY_IMPERSONATION_LEVEL = POINTER(SECURITY_IMPERSONATION_LEVEL)


# typedef struct _SID_AND_ATTRIBUTES {
#   PSID  Sid;
#   DWORD Attributes;
# } SID_AND_ATTRIBUTES, *PSID_AND_ATTRIBUTES;
class SID_AND_ATTRIBUTES(Structure):
    _fields_ = [
        ("Sid", PSID),
        ("Attributes", DWORD),
    ]


PSID_AND_ATTRIBUTES = POINTER(SID_AND_ATTRIBUTES)


# typedef struct _TOKEN_USER {
#   SID_AND_ATTRIBUTES User;
# } TOKEN_USER, *PTOKEN_USER;
class TOKEN_USER(Structure):
    _fields_ = [
        ("User", SID_AND_ATTRIBUTES),
    ]


PTOKEN_USER = POINTER(TOKEN_USER)


# typedef struct _TOKEN_MANDATORY_LABEL {
#   SID_AND_ATTRIBUTES Label;
# } TOKEN_MANDATORY_LABEL, *PTOKEN_MANDATORY_LABEL;
class TOKEN_MANDATORY_LABEL(Structure):
    _fields_ = [
        ("Label", SID_AND_ATTRIBUTES),
    ]


PTOKEN_MANDATORY_LABEL = POINTER(TOKEN_MANDATORY_LABEL)


# typedef struct _TOKEN_OWNER {
#   PSID Owner;
# } TOKEN_OWNER, *PTOKEN_OWNER;
class TOKEN_OWNER(Structure):
    _fields_ = [
        ("Owner", PSID),
    ]


PTOKEN_OWNER = POINTER(TOKEN_OWNER)


# typedef struct _TOKEN_PRIMARY_GROUP {
#   PSID PrimaryGroup;
# } TOKEN_PRIMARY_GROUP, *PTOKEN_PRIMARY_GROUP;
class TOKEN_PRIMARY_GROUP(Structure):
    _fields_ = [
        ("PrimaryGroup", PSID),
    ]


PTOKEN_PRIMARY_GROUP = POINTER(TOKEN_PRIMARY_GROUP)


# typedef struct _TOKEN_APPCONTAINER_INFORMATION {
#   	PSID TokenAppContainer;
# } TOKEN_APPCONTAINER_INFORMATION, *PTOKEN_APPCONTAINER_INFORMATION;
class TOKEN_APPCONTAINER_INFORMATION(Structure):
    _fields_ = [
        ("TokenAppContainer", PSID),
    ]


PTOKEN_APPCONTAINER_INFORMATION = POINTER(TOKEN_APPCONTAINER_INFORMATION)


# typedef struct _TOKEN_ORIGIN {
#   LUID OriginatingLogonSession;
# } TOKEN_ORIGIN, *PTOKEN_ORIGIN;
class TOKEN_ORIGIN(Structure):
    _fields_ = [
        ("OriginatingLogonSession", LUID),
    ]


PTOKEN_ORIGIN = POINTER(TOKEN_ORIGIN)


# typedef struct _TOKEN_LINKED_TOKEN {
#   HANDLE LinkedToken;
# } TOKEN_LINKED_TOKEN, *PTOKEN_LINKED_TOKEN;
class TOKEN_LINKED_TOKEN(Structure):
    _fields_ = [
        ("LinkedToken", HANDLE),
    ]


PTOKEN_LINKED_TOKEN = POINTER(TOKEN_LINKED_TOKEN)


# typedef struct _TOKEN_STATISTICS {
#   LUID                         TokenId;
#   LUID                         AuthenticationId;
#   LARGE_INTEGER                ExpirationTime;
#   TOKEN_TYPE                   TokenType;
#   SECURITY_IMPERSONATION_LEVEL ImpersonationLevel;
#   DWORD                        DynamicCharged;
#   DWORD                        DynamicAvailable;
#   DWORD                        GroupCount;
#   DWORD                        PrivilegeCount;
#   LUID                         ModifiedId;
# } TOKEN_STATISTICS, *PTOKEN_STATISTICS;
class TOKEN_STATISTICS(Structure):
    _fields_ = [
        ("TokenId", LUID),
        ("AuthenticationId", LUID),
        ("ExpirationTime", LONGLONG),  # LARGE_INTEGER
        ("TokenType", TOKEN_TYPE),
        ("ImpersonationLevel", SECURITY_IMPERSONATION_LEVEL),
        ("DynamicCharged", DWORD),
        ("DynamicAvailable", DWORD),
        ("GroupCount", DWORD),
        ("PrivilegeCount", DWORD),
        ("ModifiedId", LUID),
    ]


PTOKEN_STATISTICS = POINTER(TOKEN_STATISTICS)

# --- SID_NAME_USE enum --------------------------------------------------------

# typedef enum _SID_NAME_USE {
#   SidTypeUser             = 1,
#   SidTypeGroup,
#   SidTypeDomain,
#   SidTypeAlias,
#   SidTypeWellKnownGroup,
#   SidTypeDeletedAccount,
#   SidTypeInvalid,
#   SidTypeUnknown,
#   SidTypeComputer,
#   SidTypeLabel
# } SID_NAME_USE, *PSID_NAME_USE;

SidTypeUser = 1
SidTypeGroup = 2
SidTypeDomain = 3
SidTypeAlias = 4
SidTypeWellKnownGroup = 5
SidTypeDeletedAccount = 6
SidTypeInvalid = 7
SidTypeUnknown = 8
SidTypeComputer = 9
SidTypeLabel = 10

# --- WAITCHAIN_NODE_INFO structure and types ----------------------------------

WCT_MAX_NODE_COUNT = 16
WCT_OBJNAME_LENGTH = 128
WCT_ASYNC_OPEN_FLAG = 1
WCTP_OPEN_ALL_FLAGS = WCT_ASYNC_OPEN_FLAG
WCT_OUT_OF_PROC_FLAG = 1
WCT_OUT_OF_PROC_COM_FLAG = 2
WCT_OUT_OF_PROC_CS_FLAG = 4
WCTP_GETINFO_ALL_FLAGS = WCT_OUT_OF_PROC_FLAG | WCT_OUT_OF_PROC_COM_FLAG | WCT_OUT_OF_PROC_CS_FLAG

HWCT = LPVOID

# typedef enum _WCT_OBJECT_TYPE
# {
#     WctCriticalSectionType = 1,
#     WctSendMessageType,
#     WctMutexType,
#     WctAlpcType,
#     WctComType,
#     WctThreadWaitType,
#     WctProcessWaitType,
#     WctThreadType,
#     WctComActivationType,
#     WctUnknownType,
#     WctMaxType
# } WCT_OBJECT_TYPE;

WCT_OBJECT_TYPE = DWORD

WctCriticalSectionType = 1
WctSendMessageType = 2
WctMutexType = 3
WctAlpcType = 4
WctComType = 5
WctThreadWaitType = 6
WctProcessWaitType = 7
WctThreadType = 8
WctComActivationType = 9
WctUnknownType = 10
WctMaxType = 11

# typedef enum _WCT_OBJECT_STATUS
# {
#     WctStatusNoAccess = 1,            // ACCESS_DENIED for this object
#     WctStatusRunning,                 // Thread status
#     WctStatusBlocked,                 // Thread status
#     WctStatusPidOnly,                 // Thread status
#     WctStatusPidOnlyRpcss,            // Thread status
#     WctStatusOwned,                   // Dispatcher object status
#     WctStatusNotOwned,                // Dispatcher object status
#     WctStatusAbandoned,               // Dispatcher object status
#     WctStatusUnknown,                 // All objects
#     WctStatusError,                   // All objects
#     WctStatusMax
# } WCT_OBJECT_STATUS;

WCT_OBJECT_STATUS = DWORD

WctStatusNoAccess = 1  # ACCESS_DENIED for this object
WctStatusRunning = 2  # Thread status
WctStatusBlocked = 3  # Thread status
WctStatusPidOnly = 4  # Thread status
WctStatusPidOnlyRpcss = 5  # Thread status
WctStatusOwned = 6  # Dispatcher object status
WctStatusNotOwned = 7  # Dispatcher object status
WctStatusAbandoned = 8  # Dispatcher object status
WctStatusUnknown = 9  # All objects
WctStatusError = 10  # All objects
WctStatusMax = 11

# typedef struct _WAITCHAIN_NODE_INFO {
#   WCT_OBJECT_TYPE   ObjectType;
#   WCT_OBJECT_STATUS ObjectStatus;
#   union {
#     struct {
#       WCHAR ObjectName[WCT_OBJNAME_LENGTH];
#       LARGE_INTEGER Timeout;
#       BOOL Alertable;
#     } LockObject;
#     struct {
#       DWORD ProcessId;
#       DWORD ThreadId;
#       DWORD WaitTime;
#       DWORD ContextSwitches;
#     } ThreadObject;
#   } ;
# }WAITCHAIN_NODE_INFO, *PWAITCHAIN_NODE_INFO;


class _WAITCHAIN_NODE_INFO_STRUCT_1(Structure):
    _fields_ = [
        ("ObjectName", WCHAR * WCT_OBJNAME_LENGTH),
        ("Timeout", LONGLONG),  # LARGE_INTEGER
        ("Alertable", BOOL),
    ]


class _WAITCHAIN_NODE_INFO_STRUCT_2(Structure):
    _fields_ = [
        ("ProcessId", DWORD),
        ("ThreadId", DWORD),
        ("WaitTime", DWORD),
        ("ContextSwitches", DWORD),
    ]


class _WAITCHAIN_NODE_INFO_UNION(Union):
    _fields_ = [
        ("LockObject", _WAITCHAIN_NODE_INFO_STRUCT_1),
        ("ThreadObject", _WAITCHAIN_NODE_INFO_STRUCT_2),
    ]


class WAITCHAIN_NODE_INFO(Structure):
    _fields_ = [
        ("ObjectType", WCT_OBJECT_TYPE),
        ("ObjectStatus", WCT_OBJECT_STATUS),
        ("u", _WAITCHAIN_NODE_INFO_UNION),
    ]


PWAITCHAIN_NODE_INFO = POINTER(WAITCHAIN_NODE_INFO)


class WaitChainNodeInfo(object):
    """
    Represents a node in the wait chain.

    It's a wrapper on the L{WAITCHAIN_NODE_INFO} structure.

    The following members are defined only
    if the node is of L{WctThreadType} type:
     - C{ProcessId}
     - C{ThreadId}
     - C{WaitTime}
     - C{ContextSwitches}

    @see: L{GetThreadWaitChain}

    @type ObjectName: unicode
    @ivar ObjectName: Object name. May be an empty string.

    @type ObjectType: int
    @ivar ObjectType: Object type.
        Should be one of the following values:
         - L{WctCriticalSectionType}
         - L{WctSendMessageType}
         - L{WctMutexType}
         - L{WctAlpcType}
         - L{WctComType}
         - L{WctThreadWaitType}
         - L{WctProcessWaitType}
         - L{WctThreadType}
         - L{WctComActivationType}
         - L{WctUnknownType}

    @type ObjectStatus: int
    @ivar ObjectStatus: Wait status.
        Should be one of the following values:
         - L{WctStatusNoAccess} I{(ACCESS_DENIED for this object)}
         - L{WctStatusRunning} I{(Thread status)}
         - L{WctStatusBlocked} I{(Thread status)}
         - L{WctStatusPidOnly} I{(Thread status)}
         - L{WctStatusPidOnlyRpcss} I{(Thread status)}
         - L{WctStatusOwned} I{(Dispatcher object status)}
         - L{WctStatusNotOwned} I{(Dispatcher object status)}
         - L{WctStatusAbandoned} I{(Dispatcher object status)}
         - L{WctStatusUnknown} I{(All objects)}
         - L{WctStatusError} I{(All objects)}

    @type ProcessId: int
    @ivar ProcessId: Process global ID.

    @type ThreadId: int
    @ivar ThreadId: Thread global ID.

    @type WaitTime: int
    @ivar WaitTime: Wait time.

    @type ContextSwitches: int
    @ivar ContextSwitches: Number of context switches.
    """

    # @type Timeout: int
    # @ivar Timeout: Currently not documented in MSDN.
    #
    # @type Alertable: bool
    # @ivar Alertable: Currently not documented in MSDN.

    # TODO: __repr__

    def __init__(self, aStructure):
        self.ObjectType = aStructure.ObjectType
        self.ObjectStatus = aStructure.ObjectStatus
        if self.ObjectType == WctThreadType:
            self.ProcessId = aStructure.u.ThreadObject.ProcessId
            self.ThreadId = aStructure.u.ThreadObject.ThreadId
            self.WaitTime = aStructure.u.ThreadObject.WaitTime
            self.ContextSwitches = aStructure.u.ThreadObject.ContextSwitches
            self.ObjectName = ""
        else:
            self.ObjectName = aStructure.u.LockObject.ObjectName.value
            # self.Timeout = aStructure.u.LockObject.Timeout
            # self.Alertable = bool(aStructure.u.LockObject.Alertable)


class ThreadWaitChainSessionHandle(Handle):
    """
    Thread wait chain session handle.

    Returned by L{OpenThreadWaitChainSession}.

    @see: L{Handle}
    """

    def __init__(self, aHandle=None):
        """
        @type  aHandle: int
        @param aHandle: Win32 handle value.
        """
        super(ThreadWaitChainSessionHandle, self).__init__(aHandle, bOwnership=True)

    def _close(self):
        if self.value is None:
            raise ValueError("Handle was already closed!")
        CloseThreadWaitChainSession(self.value)

    def dup(self):
        raise NotImplementedError()

    def wait(self, dwMilliseconds=None):
        raise NotImplementedError()

    @property
    def inherit(self):
        return False

    @property
    def protectFromClose(self):
        return False


# --- Privilege dropping -------------------------------------------------------

SAFER_LEVEL_HANDLE = HANDLE

SAFER_SCOPEID_MACHINE = 1
SAFER_SCOPEID_USER = 2

SAFER_LEVEL_OPEN = 1

SAFER_LEVELID_DISALLOWED = 0x00000
SAFER_LEVELID_UNTRUSTED = 0x01000
SAFER_LEVELID_CONSTRAINED = 0x10000
SAFER_LEVELID_NORMALUSER = 0x20000
SAFER_LEVELID_FULLYTRUSTED = 0x40000

SAFER_POLICY_INFO_CLASS = DWORD
SaferPolicyLevelList = 1
SaferPolicyEnableTransparentEnforcement = 2
SaferPolicyDefaultLevel = 3
SaferPolicyEvaluateUserScope = 4
SaferPolicyScopeFlags = 5

SAFER_TOKEN_NULL_IF_EQUAL = 1
SAFER_TOKEN_COMPARE_ONLY = 2
SAFER_TOKEN_MAKE_INERT = 4
SAFER_TOKEN_WANT_FLAGS = 8
SAFER_TOKEN_MASK = 15

# --- Service Control Manager types, constants and structures ------------------

SC_HANDLE = HANDLE

SERVICES_ACTIVE_DATABASEW = "ServicesActive"
SERVICES_FAILED_DATABASEW = "ServicesFailed"

SERVICES_ACTIVE_DATABASEA = "ServicesActive"
SERVICES_FAILED_DATABASEA = "ServicesFailed"

SC_GROUP_IDENTIFIERW = "+"
SC_GROUP_IDENTIFIERA = "+"

SERVICE_NO_CHANGE = 0xFFFFFFFF

# enum SC_STATUS_TYPE
SC_STATUS_TYPE = ctypes.c_int
SC_STATUS_PROCESS_INFO = 0

# enum SC_ENUM_TYPE
SC_ENUM_TYPE = ctypes.c_int
SC_ENUM_PROCESS_INFO = 0

# Access rights
# http://msdn.microsoft.com/en-us/library/windows/desktop/ms685981(v=vs.85).aspx

SERVICE_ALL_ACCESS = 0xF01FF
SERVICE_QUERY_CONFIG = 0x0001
SERVICE_CHANGE_CONFIG = 0x0002
SERVICE_QUERY_STATUS = 0x0004
SERVICE_ENUMERATE_DEPENDENTS = 0x0008
SERVICE_START = 0x0010
SERVICE_STOP = 0x0020
SERVICE_PAUSE_CONTINUE = 0x0040
SERVICE_INTERROGATE = 0x0080
SERVICE_USER_DEFINED_CONTROL = 0x0100

SC_MANAGER_ALL_ACCESS = 0xF003F
SC_MANAGER_CONNECT = 0x0001
SC_MANAGER_CREATE_SERVICE = 0x0002
SC_MANAGER_ENUMERATE_SERVICE = 0x0004
SC_MANAGER_LOCK = 0x0008
SC_MANAGER_QUERY_LOCK_STATUS = 0x0010
SC_MANAGER_MODIFY_BOOT_CONFIG = 0x0020

# CreateService() service start type
SERVICE_BOOT_START = 0x00000000
SERVICE_SYSTEM_START = 0x00000001
SERVICE_AUTO_START = 0x00000002
SERVICE_DEMAND_START = 0x00000003
SERVICE_DISABLED = 0x00000004

# CreateService() error control flags
SERVICE_ERROR_IGNORE = 0x00000000
SERVICE_ERROR_NORMAL = 0x00000001
SERVICE_ERROR_SEVERE = 0x00000002
SERVICE_ERROR_CRITICAL = 0x00000003

# EnumServicesStatusEx() service state filters
SERVICE_ACTIVE = 1
SERVICE_INACTIVE = 2
SERVICE_STATE_ALL = 3

# SERVICE_STATUS_PROCESS.dwServiceType
SERVICE_KERNEL_DRIVER = 0x00000001
SERVICE_FILE_SYSTEM_DRIVER = 0x00000002
SERVICE_ADAPTER = 0x00000004
SERVICE_RECOGNIZER_DRIVER = 0x00000008
SERVICE_WIN32_OWN_PROCESS = 0x00000010
SERVICE_WIN32_SHARE_PROCESS = 0x00000020
SERVICE_INTERACTIVE_PROCESS = 0x00000100

# EnumServicesStatusEx() service type filters (in addition to actual types)
SERVICE_DRIVER = 0x0000000B  # SERVICE_KERNEL_DRIVER and SERVICE_FILE_SYSTEM_DRIVER
SERVICE_WIN32 = 0x00000030  # SERVICE_WIN32_OWN_PROCESS and SERVICE_WIN32_SHARE_PROCESS

# SERVICE_STATUS_PROCESS.dwCurrentState
SERVICE_STOPPED = 0x00000001
SERVICE_START_PENDING = 0x00000002
SERVICE_STOP_PENDING = 0x00000003
SERVICE_RUNNING = 0x00000004
SERVICE_CONTINUE_PENDING = 0x00000005
SERVICE_PAUSE_PENDING = 0x00000006
SERVICE_PAUSED = 0x00000007

# SERVICE_STATUS_PROCESS.dwControlsAccepted
SERVICE_ACCEPT_STOP = 0x00000001
SERVICE_ACCEPT_PAUSE_CONTINUE = 0x00000002
SERVICE_ACCEPT_SHUTDOWN = 0x00000004
SERVICE_ACCEPT_PARAMCHANGE = 0x00000008
SERVICE_ACCEPT_NETBINDCHANGE = 0x00000010
SERVICE_ACCEPT_HARDWAREPROFILECHANGE = 0x00000020
SERVICE_ACCEPT_POWEREVENT = 0x00000040
SERVICE_ACCEPT_SESSIONCHANGE = 0x00000080
SERVICE_ACCEPT_PRESHUTDOWN = 0x00000100

# SERVICE_STATUS_PROCESS.dwServiceFlags
SERVICE_RUNS_IN_SYSTEM_PROCESS = 0x00000001

# Service control flags
SERVICE_CONTROL_STOP = 0x00000001
SERVICE_CONTROL_PAUSE = 0x00000002
SERVICE_CONTROL_CONTINUE = 0x00000003
SERVICE_CONTROL_INTERROGATE = 0x00000004
SERVICE_CONTROL_SHUTDOWN = 0x00000005
SERVICE_CONTROL_PARAMCHANGE = 0x00000006
SERVICE_CONTROL_NETBINDADD = 0x00000007
SERVICE_CONTROL_NETBINDREMOVE = 0x00000008
SERVICE_CONTROL_NETBINDENABLE = 0x00000009
SERVICE_CONTROL_NETBINDDISABLE = 0x0000000A
SERVICE_CONTROL_DEVICEEVENT = 0x0000000B
SERVICE_CONTROL_HARDWAREPROFILECHANGE = 0x0000000C
SERVICE_CONTROL_POWEREVENT = 0x0000000D
SERVICE_CONTROL_SESSIONCHANGE = 0x0000000E

# Service control accepted bitmasks
SERVICE_ACCEPT_STOP = 0x00000001
SERVICE_ACCEPT_PAUSE_CONTINUE = 0x00000002
SERVICE_ACCEPT_SHUTDOWN = 0x00000004
SERVICE_ACCEPT_PARAMCHANGE = 0x00000008
SERVICE_ACCEPT_NETBINDCHANGE = 0x00000010
SERVICE_ACCEPT_HARDWAREPROFILECHANGE = 0x00000020
SERVICE_ACCEPT_POWEREVENT = 0x00000040
SERVICE_ACCEPT_SESSIONCHANGE = 0x00000080
SERVICE_ACCEPT_PRESHUTDOWN = 0x00000100
SERVICE_ACCEPT_TIMECHANGE = 0x00000200
SERVICE_ACCEPT_TRIGGEREVENT = 0x00000400
SERVICE_ACCEPT_USERMODEREBOOT = 0x00000800

# enum SC_ACTION_TYPE
SC_ACTION_NONE = 0
SC_ACTION_RESTART = 1
SC_ACTION_REBOOT = 2
SC_ACTION_RUN_COMMAND = 3

# QueryServiceConfig2
SERVICE_CONFIG_DESCRIPTION = 1
SERVICE_CONFIG_FAILURE_ACTIONS = 2


# typedef struct _SERVICE_STATUS {
#   DWORD dwServiceType;
#   DWORD dwCurrentState;
#   DWORD dwControlsAccepted;
#   DWORD dwWin32ExitCode;
#   DWORD dwServiceSpecificExitCode;
#   DWORD dwCheckPoint;
#   DWORD dwWaitHint;
# } SERVICE_STATUS, *LPSERVICE_STATUS;
class SERVICE_STATUS(Structure):
    _fields_ = [
        ("dwServiceType", DWORD),
        ("dwCurrentState", DWORD),
        ("dwControlsAccepted", DWORD),
        ("dwWin32ExitCode", DWORD),
        ("dwServiceSpecificExitCode", DWORD),
        ("dwCheckPoint", DWORD),
        ("dwWaitHint", DWORD),
    ]


LPSERVICE_STATUS = POINTER(SERVICE_STATUS)


# typedef struct _SERVICE_STATUS_PROCESS {
#   DWORD dwServiceType;
#   DWORD dwCurrentState;
#   DWORD dwControlsAccepted;
#   DWORD dwWin32ExitCode;
#   DWORD dwServiceSpecificExitCode;
#   DWORD dwCheckPoint;
#   DWORD dwWaitHint;
#   DWORD dwProcessId;
#   DWORD dwServiceFlags;
# } SERVICE_STATUS_PROCESS, *LPSERVICE_STATUS_PROCESS;
class SERVICE_STATUS_PROCESS(Structure):
    _fields_ = SERVICE_STATUS._fields_ + [
        ("dwProcessId", DWORD),
        ("dwServiceFlags", DWORD),
    ]


LPSERVICE_STATUS_PROCESS = POINTER(SERVICE_STATUS_PROCESS)


# typedef struct _ENUM_SERVICE_STATUS {
#   LPTSTR         lpServiceName;
#   LPTSTR         lpDisplayName;
#   SERVICE_STATUS ServiceStatus;
# } ENUM_SERVICE_STATUS, *LPENUM_SERVICE_STATUS;
class ENUM_SERVICE_STATUSA(Structure):
    _fields_ = [
        ("lpServiceName", LPSTR),
        ("lpDisplayName", LPSTR),
        ("ServiceStatus", SERVICE_STATUS),
    ]


class ENUM_SERVICE_STATUSW(Structure):
    _fields_ = [
        ("lpServiceName", LPWSTR),
        ("lpDisplayName", LPWSTR),
        ("ServiceStatus", SERVICE_STATUS),
    ]


LPENUM_SERVICE_STATUSA = POINTER(ENUM_SERVICE_STATUSA)
LPENUM_SERVICE_STATUSW = POINTER(ENUM_SERVICE_STATUSW)


# typedef struct _ENUM_SERVICE_STATUS_PROCESS {
#   LPTSTR                 lpServiceName;
#   LPTSTR                 lpDisplayName;
#   SERVICE_STATUS_PROCESS ServiceStatusProcess;
# } ENUM_SERVICE_STATUS_PROCESS, *LPENUM_SERVICE_STATUS_PROCESS;
class ENUM_SERVICE_STATUS_PROCESSA(Structure):
    _fields_ = [
        ("lpServiceName", LPSTR),
        ("lpDisplayName", LPSTR),
        ("ServiceStatusProcess", SERVICE_STATUS_PROCESS),
    ]


class ENUM_SERVICE_STATUS_PROCESSW(Structure):
    _fields_ = [
        ("lpServiceName", LPWSTR),
        ("lpDisplayName", LPWSTR),
        ("ServiceStatusProcess", SERVICE_STATUS_PROCESS),
    ]


LPENUM_SERVICE_STATUS_PROCESSA = POINTER(ENUM_SERVICE_STATUS_PROCESSA)
LPENUM_SERVICE_STATUS_PROCESSW = POINTER(ENUM_SERVICE_STATUS_PROCESSW)


class ServiceStatus(object):
    """
    Wrapper for the L{SERVICE_STATUS} structure.
    """

    def __init__(self, raw):
        """
        @type  raw: L{SERVICE_STATUS}
        @param raw: Raw structure for this service status data.
        """
        self.ServiceType = raw.dwServiceType
        self.CurrentState = raw.dwCurrentState
        self.ControlsAccepted = raw.dwControlsAccepted
        self.Win32ExitCode = raw.dwWin32ExitCode
        self.ServiceSpecificExitCode = raw.dwServiceSpecificExitCode
        self.CheckPoint = raw.dwCheckPoint
        self.WaitHint = raw.dwWaitHint


class ServiceStatusProcess(object):
    """
    Wrapper for the L{SERVICE_STATUS_PROCESS} structure.
    """

    def __init__(self, raw):
        """
        @type  raw: L{SERVICE_STATUS_PROCESS}
        @param raw: Raw structure for this service status data.
        """
        self.ServiceType = raw.dwServiceType
        self.CurrentState = raw.dwCurrentState
        self.ControlsAccepted = raw.dwControlsAccepted
        self.Win32ExitCode = raw.dwWin32ExitCode
        self.ServiceSpecificExitCode = raw.dwServiceSpecificExitCode
        self.CheckPoint = raw.dwCheckPoint
        self.WaitHint = raw.dwWaitHint
        self.ProcessId = raw.dwProcessId
        self.ServiceFlags = raw.dwServiceFlags


class ServiceStatusEntry(object):
    """
    Service status entry returned by L{EnumServicesStatus}.
    """

    def __init__(self, raw):
        """
        @type  raw: L{ENUM_SERVICE_STATUSA} or L{ENUM_SERVICE_STATUSW}
        @param raw: Raw structure for this service status entry.
        """
        self.ServiceName = raw.lpServiceName
        self.DisplayName = raw.lpDisplayName
        self.ServiceType = raw.ServiceStatus.dwServiceType
        self.CurrentState = raw.ServiceStatus.dwCurrentState
        self.ControlsAccepted = raw.ServiceStatus.dwControlsAccepted
        self.Win32ExitCode = raw.ServiceStatus.dwWin32ExitCode
        self.ServiceSpecificExitCode = raw.ServiceStatus.dwServiceSpecificExitCode
        self.CheckPoint = raw.ServiceStatus.dwCheckPoint
        self.WaitHint = raw.ServiceStatus.dwWaitHint

    def __str__(self):
        output = []
        if self.ServiceType & SERVICE_INTERACTIVE_PROCESS:
            output.append("Interactive service")
        else:
            output.append("Service")
        if self.DisplayName:
            output.append('"%s" (%s)' % (self.DisplayName, self.ServiceName))
        else:
            output.append('"%s"' % self.ServiceName)
        if self.CurrentState == SERVICE_CONTINUE_PENDING:
            output.append("is about to continue.")
        elif self.CurrentState == SERVICE_PAUSE_PENDING:
            output.append("is pausing.")
        elif self.CurrentState == SERVICE_PAUSED:
            output.append("is paused.")
        elif self.CurrentState == SERVICE_RUNNING:
            output.append("is running.")
        elif self.CurrentState == SERVICE_START_PENDING:
            output.append("is starting.")
        elif self.CurrentState == SERVICE_STOP_PENDING:
            output.append("is stopping.")
        elif self.CurrentState == SERVICE_STOPPED:
            output.append("is stopped.")
        return " ".join(output)


class ServiceStatusProcessEntry(object):
    """
    Service status entry returned by L{EnumServicesStatusEx}.
    """

    def __init__(self, raw):
        """
        @type  raw: L{ENUM_SERVICE_STATUS_PROCESSA} or L{ENUM_SERVICE_STATUS_PROCESSW}
        @param raw: Raw structure for this service status entry.
        """
        self.ServiceName = raw.lpServiceName
        self.DisplayName = raw.lpDisplayName
        self.ServiceType = raw.ServiceStatusProcess.dwServiceType
        self.CurrentState = raw.ServiceStatusProcess.dwCurrentState
        self.ControlsAccepted = raw.ServiceStatusProcess.dwControlsAccepted
        self.Win32ExitCode = raw.ServiceStatusProcess.dwWin32ExitCode
        self.ServiceSpecificExitCode = raw.ServiceStatusProcess.dwServiceSpecificExitCode
        self.CheckPoint = raw.ServiceStatusProcess.dwCheckPoint
        self.WaitHint = raw.ServiceStatusProcess.dwWaitHint
        self.ProcessId = raw.ServiceStatusProcess.dwProcessId
        self.ServiceFlags = raw.ServiceStatusProcess.dwServiceFlags

    def __str__(self):
        output = []
        if self.ServiceType & SERVICE_INTERACTIVE_PROCESS:
            output.append("Interactive service ")
        else:
            output.append("Service ")
        if self.DisplayName:
            output.append('"%s" (%s)' % (self.DisplayName, self.ServiceName))
        else:
            output.append('"%s"' % self.ServiceName)
        if self.CurrentState == SERVICE_CONTINUE_PENDING:
            output.append(" is about to continue")
        elif self.CurrentState == SERVICE_PAUSE_PENDING:
            output.append(" is pausing")
        elif self.CurrentState == SERVICE_PAUSED:
            output.append(" is paused")
        elif self.CurrentState == SERVICE_RUNNING:
            output.append(" is running")
        elif self.CurrentState == SERVICE_START_PENDING:
            output.append(" is starting")
        elif self.CurrentState == SERVICE_STOP_PENDING:
            output.append(" is stopping")
        elif self.CurrentState == SERVICE_STOPPED:
            output.append(" is stopped")
        if self.ProcessId:
            output.append(" at process %d" % self.ProcessId)
        output.append(".")
        return "".join(output)


# --- Handle wrappers ----------------------------------------------------------


# XXX maybe add functions related to the tokens here?
class TokenHandle(Handle):
    """
    Access token handle.

    @see: L{Handle}
    """

    pass


class RegistryKeyHandle(UserModeHandle):
    """
    Registry key handle.
    """

    _TYPE = HKEY

    def _close(self):
        RegCloseKey(self.value)


class SaferLevelHandle(UserModeHandle):
    """
    Safer level handle.

    @see: U{http://msdn.microsoft.com/en-us/library/ms722425(VS.85).aspx}
    """

    _TYPE = SAFER_LEVEL_HANDLE

    def _close(self):
        SaferCloseLevel(self.value)


class ServiceHandle(UserModeHandle):
    """
    Service handle.

    @see: U{http://msdn.microsoft.com/en-us/library/windows/desktop/ms684330(v=vs.85).aspx}
    """

    _TYPE = SC_HANDLE

    def _close(self):
        CloseServiceHandle(self.value)


class ServiceControlManagerHandle(UserModeHandle):
    """
    Service Control Manager (SCM) handle.

    @see: U{http://msdn.microsoft.com/en-us/library/windows/desktop/ms684323(v=vs.85).aspx}
    """

    _TYPE = SC_HANDLE

    def _close(self):
        CloseServiceHandle(self.value)


# --- advapi32.dll -------------------------------------------------------------


# BOOL WINAPI GetUserName(
#   __out    LPTSTR lpBuffer,
#   __inout  LPDWORD lpnSize
# );
def GetUserNameA():
    _GetUserNameA = windll.advapi32.GetUserNameA
    _GetUserNameA.argtypes = [LPSTR, LPDWORD]
    _GetUserNameA.restype = bool

    nSize = DWORD(0)
    _GetUserNameA(None, byref(nSize))
    error = GetLastError()
    if error != ERROR_INSUFFICIENT_BUFFER:
        raise ctypes.WinError(error)
    lpBuffer = ctypes.create_string_buffer("", nSize.value + 1)
    success = _GetUserNameA(lpBuffer, byref(nSize))
    if not success:
        raise ctypes.WinError()
    return lpBuffer.value


def GetUserNameW():
    _GetUserNameW = windll.advapi32.GetUserNameW
    _GetUserNameW.argtypes = [LPWSTR, LPDWORD]
    _GetUserNameW.restype = bool

    nSize = DWORD(0)
    _GetUserNameW(None, byref(nSize))
    error = GetLastError()
    if error != ERROR_INSUFFICIENT_BUFFER:
        raise ctypes.WinError(error)
    lpBuffer = ctypes.create_unicode_buffer("", nSize.value + 1)
    success = _GetUserNameW(lpBuffer, byref(nSize))
    if not success:
        raise ctypes.WinError()
    return lpBuffer.value


GetUserName = DefaultStringType(GetUserNameA, GetUserNameW)

# BOOL WINAPI LookupAccountName(
#   __in_opt   LPCTSTR lpSystemName,
#   __in       LPCTSTR lpAccountName,
#   __out_opt  PSID Sid,
#   __inout    LPDWORD cbSid,
#   __out_opt  LPTSTR ReferencedDomainName,
#   __inout    LPDWORD cchReferencedDomainName,
#   __out      PSID_NAME_USE peUse
# );

# XXX TO DO


# BOOL WINAPI LookupAccountSid(
#   __in_opt   LPCTSTR lpSystemName,
#   __in       PSID lpSid,
#   __out_opt  LPTSTR lpName,
#   __inout    LPDWORD cchName,
#   __out_opt  LPTSTR lpReferencedDomainName,
#   __inout    LPDWORD cchReferencedDomainName,
#   __out      PSID_NAME_USE peUse
# );
def LookupAccountSidA(lpSystemName, lpSid):
    _LookupAccountSidA = windll.advapi32.LookupAccountSidA
    _LookupAccountSidA.argtypes = [LPSTR, PSID, LPSTR, LPDWORD, LPSTR, LPDWORD, LPDWORD]
    _LookupAccountSidA.restype = bool

    cchName = DWORD(0)
    cchReferencedDomainName = DWORD(0)
    peUse = DWORD(0)
    _LookupAccountSidA(lpSystemName, lpSid, None, byref(cchName), None, byref(cchReferencedDomainName), byref(peUse))
    error = GetLastError()
    if error != ERROR_INSUFFICIENT_BUFFER:
        raise ctypes.WinError(error)
    lpName = ctypes.create_string_buffer("", cchName + 1)
    lpReferencedDomainName = ctypes.create_string_buffer("", cchReferencedDomainName + 1)
    success = _LookupAccountSidA(
        lpSystemName, lpSid, lpName, byref(cchName), lpReferencedDomainName, byref(cchReferencedDomainName), byref(peUse)
    )
    if not success:
        raise ctypes.WinError()
    return lpName.value, lpReferencedDomainName.value, peUse.value


def LookupAccountSidW(lpSystemName, lpSid):
    _LookupAccountSidW = windll.advapi32.LookupAccountSidA
    _LookupAccountSidW.argtypes = [LPSTR, PSID, LPWSTR, LPDWORD, LPWSTR, LPDWORD, LPDWORD]
    _LookupAccountSidW.restype = bool

    cchName = DWORD(0)
    cchReferencedDomainName = DWORD(0)
    peUse = DWORD(0)
    _LookupAccountSidW(lpSystemName, lpSid, None, byref(cchName), None, byref(cchReferencedDomainName), byref(peUse))
    error = GetLastError()
    if error != ERROR_INSUFFICIENT_BUFFER:
        raise ctypes.WinError(error)
    lpName = ctypes.create_unicode_buffer("", cchName + 1)
    lpReferencedDomainName = ctypes.create_unicode_buffer("", cchReferencedDomainName + 1)
    success = _LookupAccountSidW(
        lpSystemName, lpSid, lpName, byref(cchName), lpReferencedDomainName, byref(cchReferencedDomainName), byref(peUse)
    )
    if not success:
        raise ctypes.WinError()
    return lpName.value, lpReferencedDomainName.value, peUse.value


LookupAccountSid = GuessStringType(LookupAccountSidA, LookupAccountSidW)


# BOOL ConvertSidToStringSid(
#   __in   PSID Sid,
#   __out  LPTSTR *StringSid
# );
def ConvertSidToStringSidA(Sid):
    _ConvertSidToStringSidA = windll.advapi32.ConvertSidToStringSidA
    _ConvertSidToStringSidA.argtypes = [PSID, LPSTR]
    _ConvertSidToStringSidA.restype = bool
    _ConvertSidToStringSidA.errcheck = RaiseIfZero

    pStringSid = LPSTR()
    _ConvertSidToStringSidA(Sid, byref(pStringSid))
    try:
        StringSid = pStringSid.value
    finally:
        LocalFree(pStringSid)
    return StringSid


def ConvertSidToStringSidW(Sid):
    _ConvertSidToStringSidW = windll.advapi32.ConvertSidToStringSidW
    _ConvertSidToStringSidW.argtypes = [PSID, LPWSTR]
    _ConvertSidToStringSidW.restype = bool
    _ConvertSidToStringSidW.errcheck = RaiseIfZero

    pStringSid = LPWSTR()
    _ConvertSidToStringSidW(Sid, byref(pStringSid))
    try:
        StringSid = pStringSid.value
    finally:
        LocalFree(pStringSid)
    return StringSid


ConvertSidToStringSid = DefaultStringType(ConvertSidToStringSidA, ConvertSidToStringSidW)


# BOOL WINAPI ConvertStringSidToSid(
#   __in   LPCTSTR StringSid,
#   __out  PSID *Sid
# );
def ConvertStringSidToSidA(StringSid):
    _ConvertStringSidToSidA = windll.advapi32.ConvertStringSidToSidA
    _ConvertStringSidToSidA.argtypes = [LPSTR, PVOID]
    _ConvertStringSidToSidA.restype = bool
    _ConvertStringSidToSidA.errcheck = RaiseIfZero

    Sid = PVOID()
    _ConvertStringSidToSidA(StringSid, ctypes.pointer(Sid))
    return Sid.value


def ConvertStringSidToSidW(StringSid):
    _ConvertStringSidToSidW = windll.advapi32.ConvertStringSidToSidW
    _ConvertStringSidToSidW.argtypes = [LPWSTR, PVOID]
    _ConvertStringSidToSidW.restype = bool
    _ConvertStringSidToSidW.errcheck = RaiseIfZero

    Sid = PVOID()
    _ConvertStringSidToSidW(StringSid, ctypes.pointer(Sid))
    return Sid.value


ConvertStringSidToSid = GuessStringType(ConvertStringSidToSidA, ConvertStringSidToSidW)


# BOOL WINAPI IsValidSid(
#   __in  PSID pSid
# );
def IsValidSid(pSid):
    _IsValidSid = windll.advapi32.IsValidSid
    _IsValidSid.argtypes = [PSID]
    _IsValidSid.restype = bool
    return _IsValidSid(pSid)


# BOOL WINAPI EqualSid(
#   __in  PSID pSid1,
#   __in  PSID pSid2
# );
def EqualSid(pSid1, pSid2):
    _EqualSid = windll.advapi32.EqualSid
    _EqualSid.argtypes = [PSID, PSID]
    _EqualSid.restype = bool
    return _EqualSid(pSid1, pSid2)


# DWORD WINAPI GetLengthSid(
#   __in  PSID pSid
# );
def GetLengthSid(pSid):
    _GetLengthSid = windll.advapi32.GetLengthSid
    _GetLengthSid.argtypes = [PSID]
    _GetLengthSid.restype = DWORD
    return _GetLengthSid(pSid)


# BOOL WINAPI CopySid(
#   __in   DWORD nDestinationSidLength,
#   __out  PSID pDestinationSid,
#   __in   PSID pSourceSid
# );
def CopySid(pSourceSid):
    _CopySid = windll.advapi32.CopySid
    _CopySid.argtypes = [DWORD, PVOID, PSID]
    _CopySid.restype = bool
    _CopySid.errcheck = RaiseIfZero

    nDestinationSidLength = GetLengthSid(pSourceSid)
    DestinationSid = ctypes.create_string_buffer("", nDestinationSidLength)
    pDestinationSid = ctypes.cast(ctypes.pointer(DestinationSid), PVOID)
    _CopySid(nDestinationSidLength, pDestinationSid, pSourceSid)
    return ctypes.cast(pDestinationSid, PSID)


# PVOID WINAPI FreeSid(
#   __in  PSID pSid
# );
def FreeSid(pSid):
    _FreeSid = windll.advapi32.FreeSid
    _FreeSid.argtypes = [PSID]
    _FreeSid.restype = PSID
    _FreeSid.errcheck = RaiseIfNotZero
    _FreeSid(pSid)


# BOOL WINAPI OpenProcessToken(
#   __in   HANDLE ProcessHandle,
#   __in   DWORD DesiredAccess,
#   __out  PHANDLE TokenHandle
# );
def OpenProcessToken(ProcessHandle, DesiredAccess=TOKEN_ALL_ACCESS):
    _OpenProcessToken = windll.advapi32.OpenProcessToken
    _OpenProcessToken.argtypes = [HANDLE, DWORD, PHANDLE]
    _OpenProcessToken.restype = bool
    _OpenProcessToken.errcheck = RaiseIfZero

    NewTokenHandle = HANDLE(INVALID_HANDLE_VALUE)
    _OpenProcessToken(ProcessHandle, DesiredAccess, byref(NewTokenHandle))
    return TokenHandle(NewTokenHandle.value)


# BOOL WINAPI OpenThreadToken(
#   __in   HANDLE ThreadHandle,
#   __in   DWORD DesiredAccess,
#   __in   BOOL OpenAsSelf,
#   __out  PHANDLE TokenHandle
# );
def OpenThreadToken(ThreadHandle, DesiredAccess, OpenAsSelf=True):
    _OpenThreadToken = windll.advapi32.OpenThreadToken
    _OpenThreadToken.argtypes = [HANDLE, DWORD, BOOL, PHANDLE]
    _OpenThreadToken.restype = bool
    _OpenThreadToken.errcheck = RaiseIfZero

    NewTokenHandle = HANDLE(INVALID_HANDLE_VALUE)
    _OpenThreadToken(ThreadHandle, DesiredAccess, OpenAsSelf, byref(NewTokenHandle))
    return TokenHandle(NewTokenHandle.value)


# BOOL WINAPI DuplicateToken(
#   _In_   HANDLE ExistingTokenHandle,
#   _In_   SECURITY_IMPERSONATION_LEVEL ImpersonationLevel,
#   _Out_  PHANDLE DuplicateTokenHandle
# );
def DuplicateToken(ExistingTokenHandle, ImpersonationLevel=SecurityImpersonation):
    _DuplicateToken = windll.advapi32.DuplicateToken
    _DuplicateToken.argtypes = [HANDLE, SECURITY_IMPERSONATION_LEVEL, PHANDLE]
    _DuplicateToken.restype = bool
    _DuplicateToken.errcheck = RaiseIfZero

    DuplicateTokenHandle = HANDLE(INVALID_HANDLE_VALUE)
    _DuplicateToken(ExistingTokenHandle, ImpersonationLevel, byref(DuplicateTokenHandle))
    return TokenHandle(DuplicateTokenHandle.value)


# BOOL WINAPI DuplicateTokenEx(
#   _In_      HANDLE hExistingToken,
#   _In_      DWORD dwDesiredAccess,
#   _In_opt_  LPSECURITY_ATTRIBUTES lpTokenAttributes,
#   _In_      SECURITY_IMPERSONATION_LEVEL ImpersonationLevel,
#   _In_      TOKEN_TYPE TokenType,
#   _Out_     PHANDLE phNewToken
# );
def DuplicateTokenEx(
    hExistingToken,
    dwDesiredAccess=TOKEN_ALL_ACCESS,
    lpTokenAttributes=None,
    ImpersonationLevel=SecurityImpersonation,
    TokenType=TokenPrimary,
):
    _DuplicateTokenEx = windll.advapi32.DuplicateTokenEx
    _DuplicateTokenEx.argtypes = [HANDLE, DWORD, LPSECURITY_ATTRIBUTES, SECURITY_IMPERSONATION_LEVEL, TOKEN_TYPE, PHANDLE]
    _DuplicateTokenEx.restype = bool
    _DuplicateTokenEx.errcheck = RaiseIfZero

    DuplicateTokenHandle = HANDLE(INVALID_HANDLE_VALUE)
    _DuplicateTokenEx(hExistingToken, dwDesiredAccess, lpTokenAttributes, ImpersonationLevel, TokenType, byref(DuplicateTokenHandle))
    return TokenHandle(DuplicateTokenHandle.value)


# BOOL WINAPI IsTokenRestricted(
#   __in  HANDLE TokenHandle
# );
def IsTokenRestricted(hTokenHandle):
    _IsTokenRestricted = windll.advapi32.IsTokenRestricted
    _IsTokenRestricted.argtypes = [HANDLE]
    _IsTokenRestricted.restype = bool
    _IsTokenRestricted.errcheck = RaiseIfNotErrorSuccess

    SetLastError(ERROR_SUCCESS)
    return _IsTokenRestricted(hTokenHandle)


# BOOL WINAPI LookupPrivilegeValue(
#   __in_opt  LPCTSTR lpSystemName,
#   __in      LPCTSTR lpName,
#   __out     PLUID lpLuid
# );
def LookupPrivilegeValueA(lpSystemName, lpName):
    _LookupPrivilegeValueA = windll.advapi32.LookupPrivilegeValueA
    _LookupPrivilegeValueA.argtypes = [LPSTR, LPSTR, PLUID]
    _LookupPrivilegeValueA.restype = bool
    _LookupPrivilegeValueA.errcheck = RaiseIfZero

    lpLuid = LUID()
    if not lpSystemName:
        lpSystemName = None
    _LookupPrivilegeValueA(lpSystemName, lpName, byref(lpLuid))
    return lpLuid


def LookupPrivilegeValueW(lpSystemName, lpName):
    _LookupPrivilegeValueW = windll.advapi32.LookupPrivilegeValueW
    _LookupPrivilegeValueW.argtypes = [LPWSTR, LPWSTR, PLUID]
    _LookupPrivilegeValueW.restype = bool
    _LookupPrivilegeValueW.errcheck = RaiseIfZero

    lpLuid = LUID()
    if not lpSystemName:
        lpSystemName = None
    _LookupPrivilegeValueW(lpSystemName, lpName, byref(lpLuid))
    return lpLuid


LookupPrivilegeValue = GuessStringType(LookupPrivilegeValueA, LookupPrivilegeValueW)

# BOOL WINAPI LookupPrivilegeName(
#   __in_opt   LPCTSTR lpSystemName,
#   __in       PLUID lpLuid,
#   __out_opt  LPTSTR lpName,
#   __inout    LPDWORD cchName
# );


def LookupPrivilegeNameA(lpSystemName, lpLuid):
    _LookupPrivilegeNameA = windll.advapi32.LookupPrivilegeNameA
    _LookupPrivilegeNameA.argtypes = [LPSTR, PLUID, LPSTR, LPDWORD]
    _LookupPrivilegeNameA.restype = bool
    _LookupPrivilegeNameA.errcheck = RaiseIfZero

    cchName = DWORD(0)
    _LookupPrivilegeNameA(lpSystemName, byref(lpLuid), NULL, byref(cchName))
    lpName = ctypes.create_string_buffer("", cchName.value)
    _LookupPrivilegeNameA(lpSystemName, byref(lpLuid), byref(lpName), byref(cchName))
    return lpName.value


def LookupPrivilegeNameW(lpSystemName, lpLuid):
    _LookupPrivilegeNameW = windll.advapi32.LookupPrivilegeNameW
    _LookupPrivilegeNameW.argtypes = [LPWSTR, PLUID, LPWSTR, LPDWORD]
    _LookupPrivilegeNameW.restype = bool
    _LookupPrivilegeNameW.errcheck = RaiseIfZero

    cchName = DWORD(0)
    _LookupPrivilegeNameW(lpSystemName, byref(lpLuid), NULL, byref(cchName))
    lpName = ctypes.create_unicode_buffer("", cchName.value)
    _LookupPrivilegeNameW(lpSystemName, byref(lpLuid), byref(lpName), byref(cchName))
    return lpName.value


LookupPrivilegeName = GuessStringType(LookupPrivilegeNameA, LookupPrivilegeNameW)


# BOOL WINAPI AdjustTokenPrivileges(
#   __in       HANDLE TokenHandle,
#   __in       BOOL DisableAllPrivileges,
#   __in_opt   PTOKEN_PRIVILEGES NewState,
#   __in       DWORD BufferLength,
#   __out_opt  PTOKEN_PRIVILEGES PreviousState,
#   __out_opt  PDWORD ReturnLength
# );
def AdjustTokenPrivileges(TokenHandle, NewState=()):
    _AdjustTokenPrivileges = windll.advapi32.AdjustTokenPrivileges
    _AdjustTokenPrivileges.argtypes = [HANDLE, BOOL, LPVOID, DWORD, LPVOID, LPVOID]
    _AdjustTokenPrivileges.restype = bool
    _AdjustTokenPrivileges.errcheck = RaiseIfZero
    #
    # I don't know how to allocate variable sized structures in ctypes :(
    # so this hack will work by using always TOKEN_PRIVILEGES of one element
    # and calling the API many times. This also means the PreviousState
    # parameter won't be supported yet as it's too much hassle. In a future
    # version I look forward to implementing this function correctly.
    #
    if not NewState:
        _AdjustTokenPrivileges(TokenHandle, TRUE, NULL, 0, NULL, NULL)
    else:
        success = True
        for privilege, enabled in NewState:
            if not isinstance(privilege, LUID):
                privilege = LookupPrivilegeValue(NULL, privilege)
            if enabled == True:
                flags = SE_PRIVILEGE_ENABLED
            elif enabled == False:
                flags = SE_PRIVILEGE_REMOVED
            elif enabled == None:
                flags = 0
            else:
                flags = enabled
            laa = LUID_AND_ATTRIBUTES(privilege, flags)
            tp = TOKEN_PRIVILEGES(1, laa)
            _AdjustTokenPrivileges(TokenHandle, FALSE, byref(tp), sizeof(tp), NULL, NULL)


# BOOL WINAPI GetTokenInformation(
#   __in       HANDLE TokenHandle,
#   __in       TOKEN_INFORMATION_CLASS TokenInformationClass,
#   __out_opt  LPVOID TokenInformation,
#   __in       DWORD TokenInformationLength,
#   __out      PDWORD ReturnLength
# );
def GetTokenInformation(hTokenHandle, TokenInformationClass):
    if TokenInformationClass <= 0 or TokenInformationClass > MaxTokenInfoClass:
        raise ValueError("Invalid value for TokenInformationClass (%i)" % TokenInformationClass)

    # User SID.
    if TokenInformationClass == TokenUser:
        TokenInformation = TOKEN_USER()
        _internal_GetTokenInformation(hTokenHandle, TokenInformationClass, TokenInformation)
        return TokenInformation.User.Sid.value

    # Owner SID.
    if TokenInformationClass == TokenOwner:
        TokenInformation = TOKEN_OWNER()
        _internal_GetTokenInformation(hTokenHandle, TokenInformationClass, TokenInformation)
        return TokenInformation.Owner.value

    # Primary group SID.
    if TokenInformationClass == TokenOwner:
        TokenInformation = TOKEN_PRIMARY_GROUP()
        _internal_GetTokenInformation(hTokenHandle, TokenInformationClass, TokenInformation)
        return TokenInformation.PrimaryGroup.value

    # App container SID.
    if TokenInformationClass == TokenAppContainerSid:
        TokenInformation = TOKEN_APPCONTAINER_INFORMATION()
        _internal_GetTokenInformation(hTokenHandle, TokenInformationClass, TokenInformation)
        return TokenInformation.TokenAppContainer.value

    # Integrity level SID.
    if TokenInformationClass == TokenIntegrityLevel:
        TokenInformation = TOKEN_MANDATORY_LABEL()
        _internal_GetTokenInformation(hTokenHandle, TokenInformationClass, TokenInformation)
        return TokenInformation.Label.Sid.value, TokenInformation.Label.Attributes

    # Logon session LUID.
    if TokenInformationClass == TokenOrigin:
        TokenInformation = TOKEN_ORIGIN()
        _internal_GetTokenInformation(hTokenHandle, TokenInformationClass, TokenInformation)
        return TokenInformation.OriginatingLogonSession

    # Primary or impersonation token.
    if TokenInformationClass == TokenType:
        TokenInformation = TOKEN_TYPE(0)
        _internal_GetTokenInformation(hTokenHandle, TokenInformationClass, TokenInformation)
        return TokenInformation.value

    # Elevated token.
    if TokenInformationClass == TokenElevation:
        TokenInformation = TOKEN_ELEVATION(0)
        _internal_GetTokenInformation(hTokenHandle, TokenInformationClass, TokenInformation)
        return TokenInformation.value

    # Security impersonation level.
    if TokenInformationClass == TokenElevation:
        TokenInformation = SECURITY_IMPERSONATION_LEVEL(0)
        _internal_GetTokenInformation(hTokenHandle, TokenInformationClass, TokenInformation)
        return TokenInformation.value

    # Session ID and other DWORD values.
    if TokenInformationClass in (TokenSessionId, TokenAppContainerNumber):
        TokenInformation = DWORD(0)
        _internal_GetTokenInformation(hTokenHandle, TokenInformationClass, TokenInformation)
        return TokenInformation.value

    # Various boolean flags.
    if TokenInformationClass in (
        TokenSandBoxInert,
        TokenHasRestrictions,
        TokenUIAccess,
        TokenVirtualizationAllowed,
        TokenVirtualizationEnabled,
    ):
        TokenInformation = DWORD(0)
        _internal_GetTokenInformation(hTokenHandle, TokenInformationClass, TokenInformation)
        return bool(TokenInformation.value)

    # Linked token.
    if TokenInformationClass == TokenLinkedToken:
        TokenInformation = TOKEN_LINKED_TOKEN(0)
        _internal_GetTokenInformation(hTokenHandle, TokenInformationClass, TokenInformation)
        return TokenHandle(TokenInformation.LinkedToken.value, bOwnership=True)

    # Token statistics.
    if TokenInformationClass == TokenStatistics:
        TokenInformation = TOKEN_STATISTICS()
        _internal_GetTokenInformation(hTokenHandle, TokenInformationClass, TokenInformation)
        return TokenInformation  # TODO add a class wrapper?

    # Currently unsupported flags.
    raise NotImplementedError("TokenInformationClass(%i) not yet supported!" % TokenInformationClass)


def _internal_GetTokenInformation(hTokenHandle, TokenInformationClass, TokenInformation):
    _GetTokenInformation = windll.advapi32.GetTokenInformation
    _GetTokenInformation.argtypes = [HANDLE, TOKEN_INFORMATION_CLASS, LPVOID, DWORD, PDWORD]
    _GetTokenInformation.restype = bool
    _GetTokenInformation.errcheck = RaiseIfZero

    ReturnLength = DWORD(0)
    TokenInformationLength = SIZEOF(TokenInformation)
    _GetTokenInformation(hTokenHandle, TokenInformationClass, byref(TokenInformation), TokenInformationLength, byref(ReturnLength))
    if ReturnLength.value != TokenInformationLength:
        raise ctypes.WinError(ERROR_INSUFFICIENT_BUFFER)
    return TokenInformation


# BOOL WINAPI SetTokenInformation(
#   __in  HANDLE TokenHandle,
#   __in  TOKEN_INFORMATION_CLASS TokenInformationClass,
#   __in  LPVOID TokenInformation,
#   __in  DWORD TokenInformationLength
# );

# XXX TODO


# BOOL WINAPI CreateProcessWithLogonW(
#   __in         LPCWSTR lpUsername,
#   __in_opt     LPCWSTR lpDomain,
#   __in         LPCWSTR lpPassword,
#   __in         DWORD dwLogonFlags,
#   __in_opt     LPCWSTR lpApplicationName,
#   __inout_opt  LPWSTR lpCommandLine,
#   __in         DWORD dwCreationFlags,
#   __in_opt     LPVOID lpEnvironment,
#   __in_opt     LPCWSTR lpCurrentDirectory,
#   __in         LPSTARTUPINFOW lpStartupInfo,
#   __out        LPPROCESS_INFORMATION lpProcessInfo
# );
def CreateProcessWithLogonW(
    lpUsername=None,
    lpDomain=None,
    lpPassword=None,
    dwLogonFlags=0,
    lpApplicationName=None,
    lpCommandLine=None,
    dwCreationFlags=0,
    lpEnvironment=None,
    lpCurrentDirectory=None,
    lpStartupInfo=None,
):
    _CreateProcessWithLogonW = windll.advapi32.CreateProcessWithLogonW
    _CreateProcessWithLogonW.argtypes = [
        LPWSTR,
        LPWSTR,
        LPWSTR,
        DWORD,
        LPWSTR,
        LPWSTR,
        DWORD,
        LPVOID,
        LPWSTR,
        LPVOID,
        LPPROCESS_INFORMATION,
    ]
    _CreateProcessWithLogonW.restype = bool
    _CreateProcessWithLogonW.errcheck = RaiseIfZero

    if not lpUsername:
        lpUsername = None
    if not lpDomain:
        lpDomain = None
    if not lpPassword:
        lpPassword = None
    if not lpApplicationName:
        lpApplicationName = None
    if not lpCommandLine:
        lpCommandLine = None
    else:
        lpCommandLine = ctypes.create_unicode_buffer(lpCommandLine, max(MAX_PATH, len(lpCommandLine)))
    if not lpEnvironment:
        lpEnvironment = None
    else:
        lpEnvironment = ctypes.create_unicode_buffer(lpEnvironment)
    if not lpCurrentDirectory:
        lpCurrentDirectory = None
    if not lpStartupInfo:
        lpStartupInfo = STARTUPINFOW()
        lpStartupInfo.cb = sizeof(STARTUPINFOW)
        lpStartupInfo.lpReserved = 0
        lpStartupInfo.lpDesktop = 0
        lpStartupInfo.lpTitle = 0
        lpStartupInfo.dwFlags = 0
        lpStartupInfo.cbReserved2 = 0
        lpStartupInfo.lpReserved2 = 0
    lpProcessInformation = PROCESS_INFORMATION()
    lpProcessInformation.hProcess = INVALID_HANDLE_VALUE
    lpProcessInformation.hThread = INVALID_HANDLE_VALUE
    lpProcessInformation.dwProcessId = 0
    lpProcessInformation.dwThreadId = 0
    _CreateProcessWithLogonW(
        lpUsername,
        lpDomain,
        lpPassword,
        dwLogonFlags,
        lpApplicationName,
        lpCommandLine,
        dwCreationFlags,
        lpEnvironment,
        lpCurrentDirectory,
        byref(lpStartupInfo),
        byref(lpProcessInformation),
    )
    return ProcessInformation(lpProcessInformation)


CreateProcessWithLogonA = MakeANSIVersion(CreateProcessWithLogonW)
CreateProcessWithLogon = DefaultStringType(CreateProcessWithLogonA, CreateProcessWithLogonW)


# BOOL WINAPI CreateProcessWithTokenW(
#   __in         HANDLE hToken,
#   __in         DWORD dwLogonFlags,
#   __in_opt     LPCWSTR lpApplicationName,
#   __inout_opt  LPWSTR lpCommandLine,
#   __in         DWORD dwCreationFlags,
#   __in_opt     LPVOID lpEnvironment,
#   __in_opt     LPCWSTR lpCurrentDirectory,
#   __in         LPSTARTUPINFOW lpStartupInfo,
#   __out        LPPROCESS_INFORMATION lpProcessInfo
# );
def CreateProcessWithTokenW(
    hToken=None,
    dwLogonFlags=0,
    lpApplicationName=None,
    lpCommandLine=None,
    dwCreationFlags=0,
    lpEnvironment=None,
    lpCurrentDirectory=None,
    lpStartupInfo=None,
):
    _CreateProcessWithTokenW = windll.advapi32.CreateProcessWithTokenW
    _CreateProcessWithTokenW.argtypes = [HANDLE, DWORD, LPWSTR, LPWSTR, DWORD, LPVOID, LPWSTR, LPVOID, LPPROCESS_INFORMATION]
    _CreateProcessWithTokenW.restype = bool
    _CreateProcessWithTokenW.errcheck = RaiseIfZero

    if not hToken:
        hToken = None
    if not lpApplicationName:
        lpApplicationName = None
    if not lpCommandLine:
        lpCommandLine = None
    else:
        lpCommandLine = ctypes.create_unicode_buffer(lpCommandLine, max(MAX_PATH, len(lpCommandLine)))
    if not lpEnvironment:
        lpEnvironment = None
    else:
        lpEnvironment = ctypes.create_unicode_buffer(lpEnvironment)
    if not lpCurrentDirectory:
        lpCurrentDirectory = None
    if not lpStartupInfo:
        lpStartupInfo = STARTUPINFOW()
        lpStartupInfo.cb = sizeof(STARTUPINFOW)
        lpStartupInfo.lpReserved = 0
        lpStartupInfo.lpDesktop = 0
        lpStartupInfo.lpTitle = 0
        lpStartupInfo.dwFlags = 0
        lpStartupInfo.cbReserved2 = 0
        lpStartupInfo.lpReserved2 = 0
    lpProcessInformation = PROCESS_INFORMATION()
    lpProcessInformation.hProcess = INVALID_HANDLE_VALUE
    lpProcessInformation.hThread = INVALID_HANDLE_VALUE
    lpProcessInformation.dwProcessId = 0
    lpProcessInformation.dwThreadId = 0
    _CreateProcessWithTokenW(
        hToken,
        dwLogonFlags,
        lpApplicationName,
        lpCommandLine,
        dwCreationFlags,
        lpEnvironment,
        lpCurrentDirectory,
        byref(lpStartupInfo),
        byref(lpProcessInformation),
    )
    return ProcessInformation(lpProcessInformation)


CreateProcessWithTokenA = MakeANSIVersion(CreateProcessWithTokenW)
CreateProcessWithToken = DefaultStringType(CreateProcessWithTokenA, CreateProcessWithTokenW)


# BOOL WINAPI CreateProcessAsUser(
#   __in_opt     HANDLE hToken,
#   __in_opt     LPCTSTR lpApplicationName,
#   __inout_opt  LPTSTR lpCommandLine,
#   __in_opt     LPSECURITY_ATTRIBUTES lpProcessAttributes,
#   __in_opt     LPSECURITY_ATTRIBUTES lpThreadAttributes,
#   __in         BOOL bInheritHandles,
#   __in         DWORD dwCreationFlags,
#   __in_opt     LPVOID lpEnvironment,
#   __in_opt     LPCTSTR lpCurrentDirectory,
#   __in         LPSTARTUPINFO lpStartupInfo,
#   __out        LPPROCESS_INFORMATION lpProcessInformation
# );
def CreateProcessAsUserA(
    hToken=None,
    lpApplicationName=None,
    lpCommandLine=None,
    lpProcessAttributes=None,
    lpThreadAttributes=None,
    bInheritHandles=False,
    dwCreationFlags=0,
    lpEnvironment=None,
    lpCurrentDirectory=None,
    lpStartupInfo=None,
):
    _CreateProcessAsUserA = windll.advapi32.CreateProcessAsUserA
    _CreateProcessAsUserA.argtypes = [
        HANDLE,
        LPSTR,
        LPSTR,
        LPSECURITY_ATTRIBUTES,
        LPSECURITY_ATTRIBUTES,
        BOOL,
        DWORD,
        LPVOID,
        LPSTR,
        LPVOID,
        LPPROCESS_INFORMATION,
    ]
    _CreateProcessAsUserA.restype = bool
    _CreateProcessAsUserA.errcheck = RaiseIfZero

    if not lpApplicationName:
        lpApplicationName = None
    if not lpCommandLine:
        lpCommandLine = None
    else:
        lpCommandLine = ctypes.create_string_buffer(lpCommandLine, max(MAX_PATH, len(lpCommandLine)))
    if not lpEnvironment:
        lpEnvironment = None
    else:
        lpEnvironment = ctypes.create_string_buffer(lpEnvironment)
    if not lpCurrentDirectory:
        lpCurrentDirectory = None
    if not lpProcessAttributes:
        lpProcessAttributes = None
    else:
        lpProcessAttributes = byref(lpProcessAttributes)
    if not lpThreadAttributes:
        lpThreadAttributes = None
    else:
        lpThreadAttributes = byref(lpThreadAttributes)
    if not lpStartupInfo:
        lpStartupInfo = STARTUPINFO()
        lpStartupInfo.cb = sizeof(STARTUPINFO)
        lpStartupInfo.lpReserved = 0
        lpStartupInfo.lpDesktop = 0
        lpStartupInfo.lpTitle = 0
        lpStartupInfo.dwFlags = 0
        lpStartupInfo.cbReserved2 = 0
        lpStartupInfo.lpReserved2 = 0
    lpProcessInformation = PROCESS_INFORMATION()
    lpProcessInformation.hProcess = INVALID_HANDLE_VALUE
    lpProcessInformation.hThread = INVALID_HANDLE_VALUE
    lpProcessInformation.dwProcessId = 0
    lpProcessInformation.dwThreadId = 0
    _CreateProcessAsUserA(
        hToken,
        lpApplicationName,
        lpCommandLine,
        lpProcessAttributes,
        lpThreadAttributes,
        bool(bInheritHandles),
        dwCreationFlags,
        lpEnvironment,
        lpCurrentDirectory,
        byref(lpStartupInfo),
        byref(lpProcessInformation),
    )
    return ProcessInformation(lpProcessInformation)


def CreateProcessAsUserW(
    hToken=None,
    lpApplicationName=None,
    lpCommandLine=None,
    lpProcessAttributes=None,
    lpThreadAttributes=None,
    bInheritHandles=False,
    dwCreationFlags=0,
    lpEnvironment=None,
    lpCurrentDirectory=None,
    lpStartupInfo=None,
):
    _CreateProcessAsUserW = windll.advapi32.CreateProcessAsUserW
    _CreateProcessAsUserW.argtypes = [
        HANDLE,
        LPWSTR,
        LPWSTR,
        LPSECURITY_ATTRIBUTES,
        LPSECURITY_ATTRIBUTES,
        BOOL,
        DWORD,
        LPVOID,
        LPWSTR,
        LPVOID,
        LPPROCESS_INFORMATION,
    ]
    _CreateProcessAsUserW.restype = bool
    _CreateProcessAsUserW.errcheck = RaiseIfZero

    if not lpApplicationName:
        lpApplicationName = None
    if not lpCommandLine:
        lpCommandLine = None
    else:
        lpCommandLine = ctypes.create_unicode_buffer(lpCommandLine, max(MAX_PATH, len(lpCommandLine)))
    if not lpEnvironment:
        lpEnvironment = None
    else:
        lpEnvironment = ctypes.create_unicode_buffer(lpEnvironment)
    if not lpCurrentDirectory:
        lpCurrentDirectory = None
    if not lpProcessAttributes:
        lpProcessAttributes = None
    else:
        lpProcessAttributes = byref(lpProcessAttributes)
    if not lpThreadAttributes:
        lpThreadAttributes = None
    else:
        lpThreadAttributes = byref(lpThreadAttributes)
    if not lpStartupInfo:
        lpStartupInfo = STARTUPINFO()
        lpStartupInfo.cb = sizeof(STARTUPINFO)
        lpStartupInfo.lpReserved = 0
        lpStartupInfo.lpDesktop = 0
        lpStartupInfo.lpTitle = 0
        lpStartupInfo.dwFlags = 0
        lpStartupInfo.cbReserved2 = 0
        lpStartupInfo.lpReserved2 = 0
    lpProcessInformation = PROCESS_INFORMATION()
    lpProcessInformation.hProcess = INVALID_HANDLE_VALUE
    lpProcessInformation.hThread = INVALID_HANDLE_VALUE
    lpProcessInformation.dwProcessId = 0
    lpProcessInformation.dwThreadId = 0
    _CreateProcessAsUserW(
        hToken,
        lpApplicationName,
        lpCommandLine,
        lpProcessAttributes,
        lpThreadAttributes,
        bool(bInheritHandles),
        dwCreationFlags,
        lpEnvironment,
        lpCurrentDirectory,
        byref(lpStartupInfo),
        byref(lpProcessInformation),
    )
    return ProcessInformation(lpProcessInformation)


CreateProcessAsUser = GuessStringType(CreateProcessAsUserA, CreateProcessAsUserW)

# VOID CALLBACK WaitChainCallback(
#     HWCT WctHandle,
#     DWORD_PTR Context,
#     DWORD CallbackStatus,
#     LPDWORD NodeCount,
#     PWAITCHAIN_NODE_INFO NodeInfoArray,
#     LPBOOL IsCycle
# );
PWAITCHAINCALLBACK = WINFUNCTYPE(HWCT, DWORD_PTR, DWORD, LPDWORD, PWAITCHAIN_NODE_INFO, LPBOOL)


# HWCT WINAPI OpenThreadWaitChainSession(
#   __in      DWORD Flags,
#   __in_opt  PWAITCHAINCALLBACK callback
# );
def OpenThreadWaitChainSession(Flags=0, callback=None):
    _OpenThreadWaitChainSession = windll.advapi32.OpenThreadWaitChainSession
    _OpenThreadWaitChainSession.argtypes = [DWORD, PVOID]
    _OpenThreadWaitChainSession.restype = HWCT
    _OpenThreadWaitChainSession.errcheck = RaiseIfZero

    if callback is not None:
        callback = PWAITCHAINCALLBACK(callback)
    aHandle = _OpenThreadWaitChainSession(Flags, callback)
    return ThreadWaitChainSessionHandle(aHandle)


# BOOL WINAPI GetThreadWaitChain(
#   _In_      HWCT WctHandle,
#   _In_opt_  DWORD_PTR Context,
#   _In_      DWORD Flags,
#   _In_      DWORD ThreadId,
#   _Inout_   LPDWORD NodeCount,
#   _Out_     PWAITCHAIN_NODE_INFO NodeInfoArray,
#   _Out_     LPBOOL IsCycle
# );
def GetThreadWaitChain(WctHandle, Context=None, Flags=WCTP_GETINFO_ALL_FLAGS, ThreadId=-1, NodeCount=WCT_MAX_NODE_COUNT):
    _GetThreadWaitChain = windll.advapi32.GetThreadWaitChain
    _GetThreadWaitChain.argtypes = [HWCT, LPDWORD, DWORD, DWORD, LPDWORD, PWAITCHAIN_NODE_INFO, LPBOOL]
    _GetThreadWaitChain.restype = bool
    _GetThreadWaitChain.errcheck = RaiseIfZero

    dwNodeCount = DWORD(NodeCount)
    NodeInfoArray = (WAITCHAIN_NODE_INFO * NodeCount)()
    IsCycle = BOOL(0)
    _GetThreadWaitChain(
        WctHandle,
        Context,
        Flags,
        ThreadId,
        byref(dwNodeCount),
        ctypes.cast(ctypes.pointer(NodeInfoArray), PWAITCHAIN_NODE_INFO),
        byref(IsCycle),
    )
    while dwNodeCount.value > NodeCount:
        NodeCount = dwNodeCount.value
        NodeInfoArray = (WAITCHAIN_NODE_INFO * NodeCount)()
        _GetThreadWaitChain(
            WctHandle,
            Context,
            Flags,
            ThreadId,
            byref(dwNodeCount),
            ctypes.cast(ctypes.pointer(NodeInfoArray), PWAITCHAIN_NODE_INFO),
            byref(IsCycle),
        )
    return ([WaitChainNodeInfo(NodeInfoArray[index]) for index in compat.xrange(dwNodeCount.value)], bool(IsCycle.value))


# VOID WINAPI CloseThreadWaitChainSession(
#   __in  HWCT WctHandle
# );
def CloseThreadWaitChainSession(WctHandle):
    _CloseThreadWaitChainSession = windll.advapi32.CloseThreadWaitChainSession
    _CloseThreadWaitChainSession.argtypes = [HWCT]
    _CloseThreadWaitChainSession(WctHandle)


# BOOL WINAPI SaferCreateLevel(
#   __in        DWORD dwScopeId,
#   __in        DWORD dwLevelId,
#   __in        DWORD OpenFlags,
#   __out       SAFER_LEVEL_HANDLE *pLevelHandle,
#   __reserved  LPVOID lpReserved
# );
def SaferCreateLevel(dwScopeId=SAFER_SCOPEID_USER, dwLevelId=SAFER_LEVELID_NORMALUSER, OpenFlags=0):
    _SaferCreateLevel = windll.advapi32.SaferCreateLevel
    _SaferCreateLevel.argtypes = [DWORD, DWORD, DWORD, POINTER(SAFER_LEVEL_HANDLE), LPVOID]
    _SaferCreateLevel.restype = BOOL
    _SaferCreateLevel.errcheck = RaiseIfZero

    hLevelHandle = SAFER_LEVEL_HANDLE(INVALID_HANDLE_VALUE)
    _SaferCreateLevel(dwScopeId, dwLevelId, OpenFlags, byref(hLevelHandle), None)
    return SaferLevelHandle(hLevelHandle.value)


# BOOL WINAPI SaferIdentifyLevel(
#   __in        DWORD dwNumProperties,
#   __in_opt    PSAFER_CODE_PROPERTIES pCodeProperties,
#   __out       SAFER_LEVEL_HANDLE *pLevelHandle,
#   __reserved  LPVOID lpReserved
# );

# XXX TODO


# BOOL WINAPI SaferComputeTokenFromLevel(
#   __in         SAFER_LEVEL_HANDLE LevelHandle,
#   __in_opt     HANDLE InAccessToken,
#   __out        PHANDLE OutAccessToken,
#   __in         DWORD dwFlags,
#   __inout_opt  LPVOID lpReserved
# );
def SaferComputeTokenFromLevel(LevelHandle, InAccessToken=None, dwFlags=0):
    _SaferComputeTokenFromLevel = windll.advapi32.SaferComputeTokenFromLevel
    _SaferComputeTokenFromLevel.argtypes = [SAFER_LEVEL_HANDLE, HANDLE, PHANDLE, DWORD, LPDWORD]
    _SaferComputeTokenFromLevel.restype = BOOL
    _SaferComputeTokenFromLevel.errcheck = RaiseIfZero

    OutAccessToken = HANDLE(INVALID_HANDLE_VALUE)
    lpReserved = DWORD(0)
    _SaferComputeTokenFromLevel(LevelHandle, InAccessToken, byref(OutAccessToken), dwFlags, byref(lpReserved))
    return TokenHandle(OutAccessToken.value), lpReserved.value


# BOOL WINAPI SaferCloseLevel(
#   __in  SAFER_LEVEL_HANDLE hLevelHandle
# );
def SaferCloseLevel(hLevelHandle):
    _SaferCloseLevel = windll.advapi32.SaferCloseLevel
    _SaferCloseLevel.argtypes = [SAFER_LEVEL_HANDLE]
    _SaferCloseLevel.restype = BOOL
    _SaferCloseLevel.errcheck = RaiseIfZero

    if hasattr(hLevelHandle, "value"):
        _SaferCloseLevel(hLevelHandle.value)
    else:
        _SaferCloseLevel(hLevelHandle)


# BOOL SaferiIsExecutableFileType(
#   __in  LPCWSTR szFullPath,
#   __in  BOOLEAN bFromShellExecute
# );
def SaferiIsExecutableFileType(szFullPath, bFromShellExecute=False):
    _SaferiIsExecutableFileType = windll.advapi32.SaferiIsExecutableFileType
    _SaferiIsExecutableFileType.argtypes = [LPWSTR, BOOLEAN]
    _SaferiIsExecutableFileType.restype = BOOL
    _SaferiIsExecutableFileType.errcheck = RaiseIfLastError

    SetLastError(ERROR_SUCCESS)
    return bool(_SaferiIsExecutableFileType(compat.unicode(szFullPath), bFromShellExecute))


# useful alias since I'm likely to misspell it :P
SaferIsExecutableFileType = SaferiIsExecutableFileType

# ------------------------------------------------------------------------------


# LONG WINAPI RegCloseKey(
#   __in  HKEY hKey
# );
def RegCloseKey(hKey):
    if hasattr(hKey, "value"):
        value = hKey.value
    else:
        value = hKey

    if value in (HKEY_CLASSES_ROOT, HKEY_CURRENT_USER, HKEY_LOCAL_MACHINE, HKEY_USERS, HKEY_PERFORMANCE_DATA, HKEY_CURRENT_CONFIG):
        return

    _RegCloseKey = windll.advapi32.RegCloseKey
    _RegCloseKey.argtypes = [HKEY]
    _RegCloseKey.restype = LONG
    _RegCloseKey.errcheck = RaiseIfNotErrorSuccess
    _RegCloseKey(hKey)


# LONG WINAPI RegConnectRegistry(
#   __in_opt  LPCTSTR lpMachineName,
#   __in      HKEY hKey,
#   __out     PHKEY phkResult
# );
def RegConnectRegistryA(lpMachineName=None, hKey=HKEY_LOCAL_MACHINE):
    _RegConnectRegistryA = windll.advapi32.RegConnectRegistryA
    _RegConnectRegistryA.argtypes = [LPSTR, HKEY, PHKEY]
    _RegConnectRegistryA.restype = LONG
    _RegConnectRegistryA.errcheck = RaiseIfNotErrorSuccess

    hkResult = HKEY(INVALID_HANDLE_VALUE)
    _RegConnectRegistryA(lpMachineName, hKey, byref(hkResult))
    return RegistryKeyHandle(hkResult.value)


def RegConnectRegistryW(lpMachineName=None, hKey=HKEY_LOCAL_MACHINE):
    _RegConnectRegistryW = windll.advapi32.RegConnectRegistryW
    _RegConnectRegistryW.argtypes = [LPWSTR, HKEY, PHKEY]
    _RegConnectRegistryW.restype = LONG
    _RegConnectRegistryW.errcheck = RaiseIfNotErrorSuccess

    hkResult = HKEY(INVALID_HANDLE_VALUE)
    _RegConnectRegistryW(lpMachineName, hKey, byref(hkResult))
    return RegistryKeyHandle(hkResult.value)


RegConnectRegistry = GuessStringType(RegConnectRegistryA, RegConnectRegistryW)


# LONG WINAPI RegCreateKey(
#   __in      HKEY hKey,
#   __in_opt  LPCTSTR lpSubKey,
#   __out     PHKEY phkResult
# );
def RegCreateKeyA(hKey=HKEY_LOCAL_MACHINE, lpSubKey=None):
    _RegCreateKeyA = windll.advapi32.RegCreateKeyA
    _RegCreateKeyA.argtypes = [HKEY, LPSTR, PHKEY]
    _RegCreateKeyA.restype = LONG
    _RegCreateKeyA.errcheck = RaiseIfNotErrorSuccess

    hkResult = HKEY(INVALID_HANDLE_VALUE)
    _RegCreateKeyA(hKey, lpSubKey, byref(hkResult))
    return RegistryKeyHandle(hkResult.value)


def RegCreateKeyW(hKey=HKEY_LOCAL_MACHINE, lpSubKey=None):
    _RegCreateKeyW = windll.advapi32.RegCreateKeyW
    _RegCreateKeyW.argtypes = [HKEY, LPWSTR, PHKEY]
    _RegCreateKeyW.restype = LONG
    _RegCreateKeyW.errcheck = RaiseIfNotErrorSuccess

    hkResult = HKEY(INVALID_HANDLE_VALUE)
    _RegCreateKeyW(hKey, lpSubKey, byref(hkResult))
    return RegistryKeyHandle(hkResult.value)


RegCreateKey = GuessStringType(RegCreateKeyA, RegCreateKeyW)

# LONG WINAPI RegCreateKeyEx(
#   __in        HKEY hKey,
#   __in        LPCTSTR lpSubKey,
#   __reserved  DWORD Reserved,
#   __in_opt    LPTSTR lpClass,
#   __in        DWORD dwOptions,
#   __in        REGSAM samDesired,
#   __in_opt    LPSECURITY_ATTRIBUTES lpSecurityAttributes,
#   __out       PHKEY phkResult,
#   __out_opt   LPDWORD lpdwDisposition
# );

# XXX TODO


# LONG WINAPI RegOpenKey(
#   __in      HKEY hKey,
#   __in_opt  LPCTSTR lpSubKey,
#   __out     PHKEY phkResult
# );
def RegOpenKeyA(hKey=HKEY_LOCAL_MACHINE, lpSubKey=None):
    _RegOpenKeyA = windll.advapi32.RegOpenKeyA
    _RegOpenKeyA.argtypes = [HKEY, LPSTR, PHKEY]
    _RegOpenKeyA.restype = LONG
    _RegOpenKeyA.errcheck = RaiseIfNotErrorSuccess

    hkResult = HKEY(INVALID_HANDLE_VALUE)
    _RegOpenKeyA(hKey, lpSubKey, byref(hkResult))
    return RegistryKeyHandle(hkResult.value)


def RegOpenKeyW(hKey=HKEY_LOCAL_MACHINE, lpSubKey=None):
    _RegOpenKeyW = windll.advapi32.RegOpenKeyW
    _RegOpenKeyW.argtypes = [HKEY, LPWSTR, PHKEY]
    _RegOpenKeyW.restype = LONG
    _RegOpenKeyW.errcheck = RaiseIfNotErrorSuccess

    hkResult = HKEY(INVALID_HANDLE_VALUE)
    _RegOpenKeyW(hKey, lpSubKey, byref(hkResult))
    return RegistryKeyHandle(hkResult.value)


RegOpenKey = GuessStringType(RegOpenKeyA, RegOpenKeyW)


# LONG WINAPI RegOpenKeyEx(
#   __in        HKEY hKey,
#   __in_opt    LPCTSTR lpSubKey,
#   __reserved  DWORD ulOptions,
#   __in        REGSAM samDesired,
#   __out       PHKEY phkResult
# );
def RegOpenKeyExA(hKey=HKEY_LOCAL_MACHINE, lpSubKey=None, samDesired=KEY_ALL_ACCESS):
    _RegOpenKeyExA = windll.advapi32.RegOpenKeyExA
    _RegOpenKeyExA.argtypes = [HKEY, LPSTR, DWORD, REGSAM, PHKEY]
    _RegOpenKeyExA.restype = LONG
    _RegOpenKeyExA.errcheck = RaiseIfNotErrorSuccess

    hkResult = HKEY(INVALID_HANDLE_VALUE)
    _RegOpenKeyExA(hKey, lpSubKey, 0, samDesired, byref(hkResult))
    return RegistryKeyHandle(hkResult.value)


def RegOpenKeyExW(hKey=HKEY_LOCAL_MACHINE, lpSubKey=None, samDesired=KEY_ALL_ACCESS):
    _RegOpenKeyExW = windll.advapi32.RegOpenKeyExW
    _RegOpenKeyExW.argtypes = [HKEY, LPWSTR, DWORD, REGSAM, PHKEY]
    _RegOpenKeyExW.restype = LONG
    _RegOpenKeyExW.errcheck = RaiseIfNotErrorSuccess

    hkResult = HKEY(INVALID_HANDLE_VALUE)
    _RegOpenKeyExW(hKey, lpSubKey, 0, samDesired, byref(hkResult))
    return RegistryKeyHandle(hkResult.value)


RegOpenKeyEx = GuessStringType(RegOpenKeyExA, RegOpenKeyExW)


# LONG WINAPI RegOpenCurrentUser(
#   __in   REGSAM samDesired,
#   __out  PHKEY phkResult
# );
def RegOpenCurrentUser(samDesired=KEY_ALL_ACCESS):
    _RegOpenCurrentUser = windll.advapi32.RegOpenCurrentUser
    _RegOpenCurrentUser.argtypes = [REGSAM, PHKEY]
    _RegOpenCurrentUser.restype = LONG
    _RegOpenCurrentUser.errcheck = RaiseIfNotErrorSuccess

    hkResult = HKEY(INVALID_HANDLE_VALUE)
    _RegOpenCurrentUser(samDesired, byref(hkResult))
    return RegistryKeyHandle(hkResult.value)


# LONG WINAPI RegOpenUserClassesRoot(
#   __in        HANDLE hToken,
#   __reserved  DWORD dwOptions,
#   __in        REGSAM samDesired,
#   __out       PHKEY phkResult
# );
def RegOpenUserClassesRoot(hToken, samDesired=KEY_ALL_ACCESS):
    _RegOpenUserClassesRoot = windll.advapi32.RegOpenUserClassesRoot
    _RegOpenUserClassesRoot.argtypes = [HANDLE, DWORD, REGSAM, PHKEY]
    _RegOpenUserClassesRoot.restype = LONG
    _RegOpenUserClassesRoot.errcheck = RaiseIfNotErrorSuccess

    hkResult = HKEY(INVALID_HANDLE_VALUE)
    _RegOpenUserClassesRoot(hToken, 0, samDesired, byref(hkResult))
    return RegistryKeyHandle(hkResult.value)


# LONG WINAPI RegQueryValue(
#   __in         HKEY hKey,
#   __in_opt     LPCTSTR lpSubKey,
#   __out_opt    LPTSTR lpValue,
#   __inout_opt  PLONG lpcbValue
# );
def RegQueryValueA(hKey, lpSubKey=None):
    _RegQueryValueA = windll.advapi32.RegQueryValueA
    _RegQueryValueA.argtypes = [HKEY, LPSTR, LPVOID, PLONG]
    _RegQueryValueA.restype = LONG
    _RegQueryValueA.errcheck = RaiseIfNotErrorSuccess

    cbValue = LONG(0)
    _RegQueryValueA(hKey, lpSubKey, None, byref(cbValue))
    lpValue = ctypes.create_string_buffer(cbValue.value)
    _RegQueryValueA(hKey, lpSubKey, lpValue, byref(cbValue))
    return lpValue.value


def RegQueryValueW(hKey, lpSubKey=None):
    _RegQueryValueW = windll.advapi32.RegQueryValueW
    _RegQueryValueW.argtypes = [HKEY, LPWSTR, LPVOID, PLONG]
    _RegQueryValueW.restype = LONG
    _RegQueryValueW.errcheck = RaiseIfNotErrorSuccess

    cbValue = LONG(0)
    _RegQueryValueW(hKey, lpSubKey, None, byref(cbValue))
    lpValue = ctypes.create_unicode_buffer(cbValue.value * sizeof(WCHAR))
    _RegQueryValueW(hKey, lpSubKey, lpValue, byref(cbValue))
    return lpValue.value


RegQueryValue = GuessStringType(RegQueryValueA, RegQueryValueW)


# LONG WINAPI RegQueryValueEx(
#   __in         HKEY hKey,
#   __in_opt     LPCTSTR lpValueName,
#   __reserved   LPDWORD lpReserved,
#   __out_opt    LPDWORD lpType,
#   __out_opt    LPBYTE lpData,
#   __inout_opt  LPDWORD lpcbData
# );
def _internal_RegQueryValueEx(ansi, hKey, lpValueName=None, bGetData=True):
    _RegQueryValueEx = _caller_RegQueryValueEx(ansi)

    cbData = DWORD(0)
    dwType = DWORD(-1)
    _RegQueryValueEx(hKey, lpValueName, None, byref(dwType), None, byref(cbData))
    Type = dwType.value

    if not bGetData:
        return cbData.value, Type

    if Type in (REG_DWORD, REG_DWORD_BIG_ENDIAN):  # REG_DWORD_LITTLE_ENDIAN
        if cbData.value != 4:
            raise ValueError("REG_DWORD value of size %d" % cbData.value)
        dwData = DWORD(0)
        _RegQueryValueEx(hKey, lpValueName, None, None, byref(dwData), byref(cbData))
        return dwData.value, Type

    if Type == REG_QWORD:  # REG_QWORD_LITTLE_ENDIAN
        if cbData.value != 8:
            raise ValueError("REG_QWORD value of size %d" % cbData.value)
        qwData = QWORD(long(0))
        _RegQueryValueEx(hKey, lpValueName, None, None, byref(qwData), byref(cbData))
        return qwData.value, Type

    if Type in (REG_SZ, REG_EXPAND_SZ):
        if ansi:
            szData = ctypes.create_string_buffer(cbData.value)
        else:
            szData = ctypes.create_unicode_buffer(cbData.value)
        _RegQueryValueEx(hKey, lpValueName, None, None, byref(szData), byref(cbData))
        return szData.value, Type

    if Type == REG_MULTI_SZ:
        if ansi:
            szData = ctypes.create_string_buffer(cbData.value)
        else:
            szData = ctypes.create_unicode_buffer(cbData.value)
        _RegQueryValueEx(hKey, lpValueName, None, None, byref(szData), byref(cbData))
        Data = szData[:]
        if ansi:
            aData = Data.split("\0")
        else:
            aData = Data.split("\0")
        aData = [token for token in aData if token]
        return aData, Type

    if Type == REG_LINK:
        szData = ctypes.create_unicode_buffer(cbData.value)
        _RegQueryValueEx(hKey, lpValueName, None, None, byref(szData), byref(cbData))
        return szData.value, Type

    # REG_BINARY, REG_NONE, and any future types
    szData = ctypes.create_string_buffer(cbData.value)
    _RegQueryValueEx(hKey, lpValueName, None, None, byref(szData), byref(cbData))
    return szData.raw, Type


def _caller_RegQueryValueEx(ansi):
    if ansi:
        _RegQueryValueEx = windll.advapi32.RegQueryValueExA
        _RegQueryValueEx.argtypes = [HKEY, LPSTR, LPVOID, PDWORD, LPVOID, PDWORD]
    else:
        _RegQueryValueEx = windll.advapi32.RegQueryValueExW
        _RegQueryValueEx.argtypes = [HKEY, LPWSTR, LPVOID, PDWORD, LPVOID, PDWORD]
    _RegQueryValueEx.restype = LONG
    _RegQueryValueEx.errcheck = RaiseIfNotErrorSuccess
    return _RegQueryValueEx


# see _internal_RegQueryValueEx
def RegQueryValueExA(hKey, lpValueName=None, bGetData=True):
    return _internal_RegQueryValueEx(True, hKey, lpValueName, bGetData)


# see _internal_RegQueryValueEx
def RegQueryValueExW(hKey, lpValueName=None, bGetData=True):
    return _internal_RegQueryValueEx(False, hKey, lpValueName, bGetData)


RegQueryValueEx = GuessStringType(RegQueryValueExA, RegQueryValueExW)


# LONG WINAPI RegSetValueEx(
#   __in        HKEY hKey,
#   __in_opt    LPCTSTR lpValueName,
#   __reserved  DWORD Reserved,
#   __in        DWORD dwType,
#   __in_opt    const BYTE *lpData,
#   __in        DWORD cbData
# );
def RegSetValueEx(hKey, lpValueName=None, lpData=None, dwType=None):
    # Determine which version of the API to use, ANSI or Widechar.
    if lpValueName is None:
        if isinstance(lpData, GuessStringType.t_ansi):
            ansi = True
        elif isinstance(lpData, GuessStringType.t_unicode):
            ansi = False
        else:
            ansi = GuessStringType.t_ansi == GuessStringType.t_default
    elif isinstance(lpValueName, GuessStringType.t_ansi):
        ansi = True
    elif isinstance(lpValueName, GuessStringType.t_unicode):
        ansi = False
    else:
        raise TypeError("String expected, got %s instead" % type(lpValueName))

    # Autodetect the type when not given.
    # TODO: improve detection of DWORD and QWORD by seeing if the value "fits".
    if dwType is None:
        if lpValueName is None:
            dwType = REG_SZ
        elif lpData is None:
            dwType = REG_NONE
        elif isinstance(lpData, GuessStringType.t_ansi):
            dwType = REG_SZ
        elif isinstance(lpData, GuessStringType.t_unicode):
            dwType = REG_SZ
        elif isinstance(lpData, int):
            dwType = REG_DWORD
        elif isinstance(lpData, long):
            dwType = REG_QWORD
        else:
            dwType = REG_BINARY

    # Load the ctypes caller.
    if ansi:
        _RegSetValueEx = windll.advapi32.RegSetValueExA
        _RegSetValueEx.argtypes = [HKEY, LPSTR, DWORD, DWORD, LPVOID, DWORD]
    else:
        _RegSetValueEx = windll.advapi32.RegSetValueExW
        _RegSetValueEx.argtypes = [HKEY, LPWSTR, DWORD, DWORD, LPVOID, DWORD]
    _RegSetValueEx.restype = LONG
    _RegSetValueEx.errcheck = RaiseIfNotErrorSuccess

    # Convert the arguments so ctypes can understand them.
    if lpData is None:
        DataRef = None
        DataSize = 0
    else:
        if dwType in (REG_DWORD, REG_DWORD_BIG_ENDIAN):  # REG_DWORD_LITTLE_ENDIAN
            Data = DWORD(lpData)
        elif dwType == REG_QWORD:  # REG_QWORD_LITTLE_ENDIAN
            Data = QWORD(lpData)
        elif dwType in (REG_SZ, REG_EXPAND_SZ):
            if ansi:
                Data = ctypes.create_string_buffer(lpData)
            else:
                Data = ctypes.create_unicode_buffer(lpData)
        elif dwType == REG_MULTI_SZ:
            if ansi:
                Data = ctypes.create_string_buffer("\0".join(lpData) + "\0\0")
            else:
                Data = ctypes.create_unicode_buffer("\0".join(lpData) + "\0\0")
        elif dwType == REG_LINK:
            Data = ctypes.create_unicode_buffer(lpData)
        else:
            Data = ctypes.create_string_buffer(lpData)
        DataRef = byref(Data)
        DataSize = sizeof(Data)

    # Call the API with the converted arguments.
    _RegSetValueEx(hKey, lpValueName, 0, dwType, DataRef, DataSize)


# No "GuessStringType" here since detection is done inside.
RegSetValueExA = RegSetValueExW = RegSetValueEx


# LONG WINAPI RegEnumKey(
#   __in   HKEY hKey,
#   __in   DWORD dwIndex,
#   __out  LPTSTR lpName,
#   __in   DWORD cchName
# );
def RegEnumKeyA(hKey, dwIndex):
    _RegEnumKeyA = windll.advapi32.RegEnumKeyA
    _RegEnumKeyA.argtypes = [HKEY, DWORD, LPSTR, DWORD]
    _RegEnumKeyA.restype = LONG

    cchName = 1024
    while True:
        lpName = ctypes.create_string_buffer(cchName)
        errcode = _RegEnumKeyA(hKey, dwIndex, lpName, cchName)
        if errcode != ERROR_MORE_DATA:
            break
        cchName = cchName + 1024
        if cchName > 65536:
            raise ctypes.WinError(errcode)
    if errcode == ERROR_NO_MORE_ITEMS:
        return None
    if errcode != ERROR_SUCCESS:
        raise ctypes.WinError(errcode)
    return lpName.value


def RegEnumKeyW(hKey, dwIndex):
    _RegEnumKeyW = windll.advapi32.RegEnumKeyW
    _RegEnumKeyW.argtypes = [HKEY, DWORD, LPWSTR, DWORD]
    _RegEnumKeyW.restype = LONG

    cchName = 512
    while True:
        lpName = ctypes.create_unicode_buffer(cchName)
        errcode = _RegEnumKeyW(hKey, dwIndex, lpName, cchName * 2)
        if errcode != ERROR_MORE_DATA:
            break
        cchName = cchName + 512
        if cchName > 32768:
            raise ctypes.WinError(errcode)
    if errcode == ERROR_NO_MORE_ITEMS:
        return None
    if errcode != ERROR_SUCCESS:
        raise ctypes.WinError(errcode)
    return lpName.value


RegEnumKey = DefaultStringType(RegEnumKeyA, RegEnumKeyW)

# LONG WINAPI RegEnumKeyEx(
#   __in         HKEY hKey,
#   __in         DWORD dwIndex,
#   __out        LPTSTR lpName,
#   __inout      LPDWORD lpcName,
#   __reserved   LPDWORD lpReserved,
#   __inout      LPTSTR lpClass,
#   __inout_opt  LPDWORD lpcClass,
#   __out_opt    PFILETIME lpftLastWriteTime
# );

# XXX TODO


# LONG WINAPI RegEnumValue(
#   __in         HKEY hKey,
#   __in         DWORD dwIndex,
#   __out        LPTSTR lpValueName,
#   __inout      LPDWORD lpcchValueName,
#   __reserved   LPDWORD lpReserved,
#   __out_opt    LPDWORD lpType,
#   __out_opt    LPBYTE lpData,
#   __inout_opt  LPDWORD lpcbData
# );
def _internal_RegEnumValue(ansi, hKey, dwIndex, bGetData=True):
    if ansi:
        _RegEnumValue = windll.advapi32.RegEnumValueA
        _RegEnumValue.argtypes = [HKEY, DWORD, LPSTR, LPDWORD, LPVOID, LPDWORD, LPVOID, LPDWORD]
    else:
        _RegEnumValue = windll.advapi32.RegEnumValueW
        _RegEnumValue.argtypes = [HKEY, DWORD, LPWSTR, LPDWORD, LPVOID, LPDWORD, LPVOID, LPDWORD]
    _RegEnumValue.restype = LONG

    cchValueName = DWORD(1024)
    dwType = DWORD(-1)
    lpcchValueName = byref(cchValueName)
    lpType = byref(dwType)
    if ansi:
        lpValueName = ctypes.create_string_buffer(cchValueName.value)
    else:
        lpValueName = ctypes.create_unicode_buffer(cchValueName.value)
    if bGetData:
        cbData = DWORD(0)
        lpcbData = byref(cbData)
    else:
        lpcbData = None
    lpData = None
    errcode = _RegEnumValue(hKey, dwIndex, lpValueName, lpcchValueName, None, lpType, lpData, lpcbData)

    if errcode == ERROR_MORE_DATA or (bGetData and errcode == ERROR_SUCCESS):
        if ansi:
            cchValueName.value = cchValueName.value + sizeof(CHAR)
            lpValueName = ctypes.create_string_buffer(cchValueName.value)
        else:
            cchValueName.value = cchValueName.value + sizeof(WCHAR)
            lpValueName = ctypes.create_unicode_buffer(cchValueName.value)

        if bGetData:
            Type = dwType.value

            if Type in (REG_DWORD, REG_DWORD_BIG_ENDIAN):  # REG_DWORD_LITTLE_ENDIAN
                if cbData.value != sizeof(DWORD):
                    raise ValueError("REG_DWORD value of size %d" % cbData.value)
                Data = DWORD(0)

            elif Type == REG_QWORD:  # REG_QWORD_LITTLE_ENDIAN
                if cbData.value != sizeof(QWORD):
                    raise ValueError("REG_QWORD value of size %d" % cbData.value)
                Data = QWORD(long(0))

            elif Type in (REG_SZ, REG_EXPAND_SZ, REG_MULTI_SZ):
                if ansi:
                    Data = ctypes.create_string_buffer(cbData.value)
                else:
                    Data = ctypes.create_unicode_buffer(cbData.value)

            elif Type == REG_LINK:
                Data = ctypes.create_unicode_buffer(cbData.value)

            else:  # REG_BINARY, REG_NONE, and any future types
                Data = ctypes.create_string_buffer(cbData.value)

            lpData = byref(Data)

        errcode = _RegEnumValue(hKey, dwIndex, lpValueName, lpcchValueName, None, lpType, lpData, lpcbData)

    if errcode == ERROR_NO_MORE_ITEMS:
        return None
    # if errcode  != ERROR_SUCCESS:
    #    raise ctypes.WinError(errcode)

    if not bGetData:
        return lpValueName.value, dwType.value

    if Type in (
        REG_DWORD,
        REG_DWORD_BIG_ENDIAN,
        REG_QWORD,
        REG_SZ,
        REG_EXPAND_SZ,
        REG_LINK,
    ):  # REG_DWORD_LITTLE_ENDIAN, REG_QWORD_LITTLE_ENDIAN
        return lpValueName.value, dwType.value, Data.value

    if Type == REG_MULTI_SZ:
        sData = Data[:]
        del Data
        if ansi:
            aData = sData.split("\0")
        else:
            aData = sData.split("\0")
        aData = [token for token in aData if token]
        return lpValueName.value, dwType.value, aData

    # REG_BINARY, REG_NONE, and any future types
    return lpValueName.value, dwType.value, Data.raw


def RegEnumValueA(hKey, dwIndex, bGetData=True):
    return _internal_RegEnumValue(True, hKey, dwIndex, bGetData)


def RegEnumValueW(hKey, dwIndex, bGetData=True):
    return _internal_RegEnumValue(False, hKey, dwIndex, bGetData)


RegEnumValue = DefaultStringType(RegEnumValueA, RegEnumValueW)

# XXX TODO

# LONG WINAPI RegSetKeyValue(
#   __in      HKEY hKey,
#   __in_opt  LPCTSTR lpSubKey,
#   __in_opt  LPCTSTR lpValueName,
#   __in      DWORD dwType,
#   __in_opt  LPCVOID lpData,
#   __in      DWORD cbData
# );

# XXX TODO

# LONG WINAPI RegQueryMultipleValues(
#   __in         HKEY hKey,
#   __out        PVALENT val_list,
#   __in         DWORD num_vals,
#   __out_opt    LPTSTR lpValueBuf,
#   __inout_opt  LPDWORD ldwTotsize
# );

# XXX TODO


# LONG WINAPI RegDeleteValue(
#   __in      HKEY hKey,
#   __in_opt  LPCTSTR lpValueName
# );
def RegDeleteValueA(hKeySrc, lpValueName=None):
    _RegDeleteValueA = windll.advapi32.RegDeleteValueA
    _RegDeleteValueA.argtypes = [HKEY, LPSTR]
    _RegDeleteValueA.restype = LONG
    _RegDeleteValueA.errcheck = RaiseIfNotErrorSuccess
    _RegDeleteValueA(hKeySrc, lpValueName)


def RegDeleteValueW(hKeySrc, lpValueName=None):
    _RegDeleteValueW = windll.advapi32.RegDeleteValueW
    _RegDeleteValueW.argtypes = [HKEY, LPWSTR]
    _RegDeleteValueW.restype = LONG
    _RegDeleteValueW.errcheck = RaiseIfNotErrorSuccess
    _RegDeleteValueW(hKeySrc, lpValueName)


RegDeleteValue = GuessStringType(RegDeleteValueA, RegDeleteValueW)


# LONG WINAPI RegDeleteKeyValue(
#   __in      HKEY hKey,
#   __in_opt  LPCTSTR lpSubKey,
#   __in_opt  LPCTSTR lpValueName
# );
def RegDeleteKeyValueA(hKeySrc, lpSubKey=None, lpValueName=None):
    _RegDeleteKeyValueA = windll.advapi32.RegDeleteKeyValueA
    _RegDeleteKeyValueA.argtypes = [HKEY, LPSTR, LPSTR]
    _RegDeleteKeyValueA.restype = LONG
    _RegDeleteKeyValueA.errcheck = RaiseIfNotErrorSuccess
    _RegDeleteKeyValueA(hKeySrc, lpSubKey, lpValueName)


def RegDeleteKeyValueW(hKeySrc, lpSubKey=None, lpValueName=None):
    _RegDeleteKeyValueW = windll.advapi32.RegDeleteKeyValueW
    _RegDeleteKeyValueW.argtypes = [HKEY, LPWSTR, LPWSTR]
    _RegDeleteKeyValueW.restype = LONG
    _RegDeleteKeyValueW.errcheck = RaiseIfNotErrorSuccess
    _RegDeleteKeyValueW(hKeySrc, lpSubKey, lpValueName)


RegDeleteKeyValue = GuessStringType(RegDeleteKeyValueA, RegDeleteKeyValueW)


# LONG WINAPI RegDeleteKey(
#   __in  HKEY hKey,
#   __in  LPCTSTR lpSubKey
# );
def RegDeleteKeyA(hKeySrc, lpSubKey=None):
    _RegDeleteKeyA = windll.advapi32.RegDeleteKeyA
    _RegDeleteKeyA.argtypes = [HKEY, LPSTR]
    _RegDeleteKeyA.restype = LONG
    _RegDeleteKeyA.errcheck = RaiseIfNotErrorSuccess
    _RegDeleteKeyA(hKeySrc, lpSubKey)


def RegDeleteKeyW(hKeySrc, lpSubKey=None):
    _RegDeleteKeyW = windll.advapi32.RegDeleteKeyW
    _RegDeleteKeyW.argtypes = [HKEY, LPWSTR]
    _RegDeleteKeyW.restype = LONG
    _RegDeleteKeyW.errcheck = RaiseIfNotErrorSuccess
    _RegDeleteKeyW(hKeySrc, lpSubKey)


RegDeleteKey = GuessStringType(RegDeleteKeyA, RegDeleteKeyW)

# LONG WINAPI RegDeleteKeyEx(
#   __in        HKEY hKey,
#   __in        LPCTSTR lpSubKey,
#   __in        REGSAM samDesired,
#   __reserved  DWORD Reserved
# );


def RegDeleteKeyExA(hKeySrc, lpSubKey=None, samDesired=KEY_WOW64_32KEY):
    _RegDeleteKeyExA = windll.advapi32.RegDeleteKeyExA
    _RegDeleteKeyExA.argtypes = [HKEY, LPSTR, REGSAM, DWORD]
    _RegDeleteKeyExA.restype = LONG
    _RegDeleteKeyExA.errcheck = RaiseIfNotErrorSuccess
    _RegDeleteKeyExA(hKeySrc, lpSubKey, samDesired, 0)


def RegDeleteKeyExW(hKeySrc, lpSubKey=None, samDesired=KEY_WOW64_32KEY):
    _RegDeleteKeyExW = windll.advapi32.RegDeleteKeyExW
    _RegDeleteKeyExW.argtypes = [HKEY, LPWSTR, REGSAM, DWORD]
    _RegDeleteKeyExW.restype = LONG
    _RegDeleteKeyExW.errcheck = RaiseIfNotErrorSuccess
    _RegDeleteKeyExW(hKeySrc, lpSubKey, samDesired, 0)


RegDeleteKeyEx = GuessStringType(RegDeleteKeyExA, RegDeleteKeyExW)


# LONG WINAPI RegCopyTree(
#   __in      HKEY hKeySrc,
#   __in_opt  LPCTSTR lpSubKey,
#   __in      HKEY hKeyDest
# );
def RegCopyTreeA(hKeySrc, lpSubKey, hKeyDest):
    _RegCopyTreeA = windll.advapi32.RegCopyTreeA
    _RegCopyTreeA.argtypes = [HKEY, LPSTR, HKEY]
    _RegCopyTreeA.restype = LONG
    _RegCopyTreeA.errcheck = RaiseIfNotErrorSuccess
    _RegCopyTreeA(hKeySrc, lpSubKey, hKeyDest)


def RegCopyTreeW(hKeySrc, lpSubKey, hKeyDest):
    _RegCopyTreeW = windll.advapi32.RegCopyTreeW
    _RegCopyTreeW.argtypes = [HKEY, LPWSTR, HKEY]
    _RegCopyTreeW.restype = LONG
    _RegCopyTreeW.errcheck = RaiseIfNotErrorSuccess
    _RegCopyTreeW(hKeySrc, lpSubKey, hKeyDest)


RegCopyTree = GuessStringType(RegCopyTreeA, RegCopyTreeW)


# LONG WINAPI RegDeleteTree(
#   __in      HKEY hKey,
#   __in_opt  LPCTSTR lpSubKey
# );
def RegDeleteTreeA(hKey, lpSubKey=None):
    _RegDeleteTreeA = windll.advapi32.RegDeleteTreeA
    _RegDeleteTreeA.argtypes = [HKEY, LPWSTR]
    _RegDeleteTreeA.restype = LONG
    _RegDeleteTreeA.errcheck = RaiseIfNotErrorSuccess
    _RegDeleteTreeA(hKey, lpSubKey)


def RegDeleteTreeW(hKey, lpSubKey=None):
    _RegDeleteTreeW = windll.advapi32.RegDeleteTreeW
    _RegDeleteTreeW.argtypes = [HKEY, LPWSTR]
    _RegDeleteTreeW.restype = LONG
    _RegDeleteTreeW.errcheck = RaiseIfNotErrorSuccess
    _RegDeleteTreeW(hKey, lpSubKey)


RegDeleteTree = GuessStringType(RegDeleteTreeA, RegDeleteTreeW)


# LONG WINAPI RegFlushKey(
#   __in  HKEY hKey
# );
def RegFlushKey(hKey):
    _RegFlushKey = windll.advapi32.RegFlushKey
    _RegFlushKey.argtypes = [HKEY]
    _RegFlushKey.restype = LONG
    _RegFlushKey.errcheck = RaiseIfNotErrorSuccess
    _RegFlushKey(hKey)


# LONG WINAPI RegLoadMUIString(
#   _In_       HKEY hKey,
#   _In_opt_   LPCTSTR pszValue,
#   _Out_opt_  LPTSTR pszOutBuf,
#   _In_       DWORD cbOutBuf,
#   _Out_opt_  LPDWORD pcbData,
#   _In_       DWORD Flags,
#   _In_opt_   LPCTSTR pszDirectory
# );

# TO DO

# ------------------------------------------------------------------------------


# BOOL WINAPI CloseServiceHandle(
#   _In_  SC_HANDLE hSCObject
# );
def CloseServiceHandle(hSCObject):
    _CloseServiceHandle = windll.advapi32.CloseServiceHandle
    _CloseServiceHandle.argtypes = [SC_HANDLE]
    _CloseServiceHandle.restype = bool
    _CloseServiceHandle.errcheck = RaiseIfZero

    if isinstance(hSCObject, Handle):
        # Prevents the handle from being closed without notifying the Handle object.
        hSCObject.close()
    else:
        _CloseServiceHandle(hSCObject)


# SC_HANDLE WINAPI OpenSCManager(
#   _In_opt_  LPCTSTR lpMachineName,
#   _In_opt_  LPCTSTR lpDatabaseName,
#   _In_      DWORD dwDesiredAccess
# );
def OpenSCManagerA(lpMachineName=None, lpDatabaseName=None, dwDesiredAccess=SC_MANAGER_ALL_ACCESS):
    _OpenSCManagerA = windll.advapi32.OpenSCManagerA
    _OpenSCManagerA.argtypes = [LPSTR, LPSTR, DWORD]
    _OpenSCManagerA.restype = SC_HANDLE
    _OpenSCManagerA.errcheck = RaiseIfZero

    hSCObject = _OpenSCManagerA(lpMachineName, lpDatabaseName, dwDesiredAccess)
    return ServiceControlManagerHandle(hSCObject)


def OpenSCManagerW(lpMachineName=None, lpDatabaseName=None, dwDesiredAccess=SC_MANAGER_ALL_ACCESS):
    _OpenSCManagerW = windll.advapi32.OpenSCManagerW
    _OpenSCManagerW.argtypes = [LPWSTR, LPWSTR, DWORD]
    _OpenSCManagerW.restype = SC_HANDLE
    _OpenSCManagerW.errcheck = RaiseIfZero

    hSCObject = _OpenSCManagerA(lpMachineName, lpDatabaseName, dwDesiredAccess)
    return ServiceControlManagerHandle(hSCObject)


OpenSCManager = GuessStringType(OpenSCManagerA, OpenSCManagerW)


# SC_HANDLE WINAPI OpenService(
#   _In_  SC_HANDLE hSCManager,
#   _In_  LPCTSTR lpServiceName,
#   _In_  DWORD dwDesiredAccess
# );
def OpenServiceA(hSCManager, lpServiceName, dwDesiredAccess=SERVICE_ALL_ACCESS):
    _OpenServiceA = windll.advapi32.OpenServiceA
    _OpenServiceA.argtypes = [SC_HANDLE, LPSTR, DWORD]
    _OpenServiceA.restype = SC_HANDLE
    _OpenServiceA.errcheck = RaiseIfZero
    return ServiceHandle(_OpenServiceA(hSCManager, lpServiceName, dwDesiredAccess))


def OpenServiceW(hSCManager, lpServiceName, dwDesiredAccess=SERVICE_ALL_ACCESS):
    _OpenServiceW = windll.advapi32.OpenServiceW
    _OpenServiceW.argtypes = [SC_HANDLE, LPWSTR, DWORD]
    _OpenServiceW.restype = SC_HANDLE
    _OpenServiceW.errcheck = RaiseIfZero
    return ServiceHandle(_OpenServiceW(hSCManager, lpServiceName, dwDesiredAccess))


OpenService = GuessStringType(OpenServiceA, OpenServiceW)


# SC_HANDLE WINAPI CreateService(
#   _In_       SC_HANDLE hSCManager,
#   _In_       LPCTSTR lpServiceName,
#   _In_opt_   LPCTSTR lpDisplayName,
#   _In_       DWORD dwDesiredAccess,
#   _In_       DWORD dwServiceType,
#   _In_       DWORD dwStartType,
#   _In_       DWORD dwErrorControl,
#   _In_opt_   LPCTSTR lpBinaryPathName,
#   _In_opt_   LPCTSTR lpLoadOrderGroup,
#   _Out_opt_  LPDWORD lpdwTagId,
#   _In_opt_   LPCTSTR lpDependencies,
#   _In_opt_   LPCTSTR lpServiceStartName,
#   _In_opt_   LPCTSTR lpPassword
# );
def CreateServiceA(
    hSCManager,
    lpServiceName,
    lpDisplayName=None,
    dwDesiredAccess=SERVICE_ALL_ACCESS,
    dwServiceType=SERVICE_WIN32_OWN_PROCESS,
    dwStartType=SERVICE_DEMAND_START,
    dwErrorControl=SERVICE_ERROR_NORMAL,
    lpBinaryPathName=None,
    lpLoadOrderGroup=None,
    lpDependencies=None,
    lpServiceStartName=None,
    lpPassword=None,
):
    _CreateServiceA = windll.advapi32.CreateServiceA
    _CreateServiceA.argtypes = [SC_HANDLE, LPSTR, LPSTR, DWORD, DWORD, DWORD, DWORD, LPSTR, LPSTR, LPDWORD, LPSTR, LPSTR, LPSTR]
    _CreateServiceA.restype = SC_HANDLE
    _CreateServiceA.errcheck = RaiseIfZero

    dwTagId = DWORD(0)
    hService = _CreateServiceA(
        hSCManager,
        lpServiceName,
        dwDesiredAccess,
        dwServiceType,
        dwStartType,
        dwErrorControl,
        lpBinaryPathName,
        lpLoadOrderGroup,
        byref(dwTagId),
        lpDependencies,
        lpServiceStartName,
        lpPassword,
    )
    return ServiceHandle(hService), dwTagId.value


def CreateServiceW(
    hSCManager,
    lpServiceName,
    lpDisplayName=None,
    dwDesiredAccess=SERVICE_ALL_ACCESS,
    dwServiceType=SERVICE_WIN32_OWN_PROCESS,
    dwStartType=SERVICE_DEMAND_START,
    dwErrorControl=SERVICE_ERROR_NORMAL,
    lpBinaryPathName=None,
    lpLoadOrderGroup=None,
    lpDependencies=None,
    lpServiceStartName=None,
    lpPassword=None,
):
    _CreateServiceW = windll.advapi32.CreateServiceW
    _CreateServiceW.argtypes = [SC_HANDLE, LPWSTR, LPWSTR, DWORD, DWORD, DWORD, DWORD, LPWSTR, LPWSTR, LPDWORD, LPWSTR, LPWSTR, LPWSTR]
    _CreateServiceW.restype = SC_HANDLE
    _CreateServiceW.errcheck = RaiseIfZero

    dwTagId = DWORD(0)
    hService = _CreateServiceW(
        hSCManager,
        lpServiceName,
        dwDesiredAccess,
        dwServiceType,
        dwStartType,
        dwErrorControl,
        lpBinaryPathName,
        lpLoadOrderGroup,
        byref(dwTagId),
        lpDependencies,
        lpServiceStartName,
        lpPassword,
    )
    return ServiceHandle(hService), dwTagId.value


CreateService = GuessStringType(CreateServiceA, CreateServiceW)


# BOOL WINAPI DeleteService(
#   _In_  SC_HANDLE hService
# );
def DeleteService(hService):
    _DeleteService = windll.advapi32.DeleteService
    _DeleteService.argtypes = [SC_HANDLE]
    _DeleteService.restype = bool
    _DeleteService.errcheck = RaiseIfZero
    _DeleteService(hService)


# BOOL WINAPI GetServiceKeyName(
#   _In_       SC_HANDLE hSCManager,
#   _In_       LPCTSTR lpDisplayName,
#   _Out_opt_  LPTSTR lpServiceName,
#   _Inout_    LPDWORD lpcchBuffer
# );
def GetServiceKeyNameA(hSCManager, lpDisplayName):
    _GetServiceKeyNameA = windll.advapi32.GetServiceKeyNameA
    _GetServiceKeyNameA.argtypes = [SC_HANDLE, LPSTR, LPSTR, LPDWORD]
    _GetServiceKeyNameA.restype = bool

    cchBuffer = DWORD(0)
    _GetServiceKeyNameA(hSCManager, lpDisplayName, None, byref(cchBuffer))
    if cchBuffer.value == 0:
        raise ctypes.WinError()
    lpServiceName = ctypes.create_string_buffer(cchBuffer.value + 1)
    cchBuffer.value = sizeof(lpServiceName)
    success = _GetServiceKeyNameA(hSCManager, lpDisplayName, lpServiceName, byref(cchBuffer))
    if not success:
        raise ctypes.WinError()
    return lpServiceName.value


def GetServiceKeyNameW(hSCManager, lpDisplayName):
    _GetServiceKeyNameW = windll.advapi32.GetServiceKeyNameW
    _GetServiceKeyNameW.argtypes = [SC_HANDLE, LPWSTR, LPWSTR, LPDWORD]
    _GetServiceKeyNameW.restype = bool

    cchBuffer = DWORD(0)
    _GetServiceKeyNameW(hSCManager, lpDisplayName, None, byref(cchBuffer))
    if cchBuffer.value == 0:
        raise ctypes.WinError()
    lpServiceName = ctypes.create_unicode_buffer(cchBuffer.value + 2)
    cchBuffer.value = sizeof(lpServiceName)
    success = _GetServiceKeyNameW(hSCManager, lpDisplayName, lpServiceName, byref(cchBuffer))
    if not success:
        raise ctypes.WinError()
    return lpServiceName.value


GetServiceKeyName = GuessStringType(GetServiceKeyNameA, GetServiceKeyNameW)


# BOOL WINAPI GetServiceDisplayName(
#   _In_       SC_HANDLE hSCManager,
#   _In_       LPCTSTR lpServiceName,
#   _Out_opt_  LPTSTR lpDisplayName,
#   _Inout_    LPDWORD lpcchBuffer
# );
def GetServiceDisplayNameA(hSCManager, lpServiceName):
    _GetServiceDisplayNameA = windll.advapi32.GetServiceDisplayNameA
    _GetServiceDisplayNameA.argtypes = [SC_HANDLE, LPSTR, LPSTR, LPDWORD]
    _GetServiceDisplayNameA.restype = bool

    cchBuffer = DWORD(0)
    _GetServiceDisplayNameA(hSCManager, lpServiceName, None, byref(cchBuffer))
    if cchBuffer.value == 0:
        raise ctypes.WinError()
    lpDisplayName = ctypes.create_string_buffer(cchBuffer.value + 1)
    cchBuffer.value = sizeof(lpDisplayName)
    success = _GetServiceDisplayNameA(hSCManager, lpServiceName, lpDisplayName, byref(cchBuffer))
    if not success:
        raise ctypes.WinError()
    return lpDisplayName.value


def GetServiceDisplayNameW(hSCManager, lpServiceName):
    _GetServiceDisplayNameW = windll.advapi32.GetServiceDisplayNameW
    _GetServiceDisplayNameW.argtypes = [SC_HANDLE, LPWSTR, LPWSTR, LPDWORD]
    _GetServiceDisplayNameW.restype = bool

    cchBuffer = DWORD(0)
    _GetServiceDisplayNameW(hSCManager, lpServiceName, None, byref(cchBuffer))
    if cchBuffer.value == 0:
        raise ctypes.WinError()
    lpDisplayName = ctypes.create_unicode_buffer(cchBuffer.value + 2)
    cchBuffer.value = sizeof(lpDisplayName)
    success = _GetServiceDisplayNameW(hSCManager, lpServiceName, lpDisplayName, byref(cchBuffer))
    if not success:
        raise ctypes.WinError()
    return lpDisplayName.value


GetServiceDisplayName = GuessStringType(GetServiceDisplayNameA, GetServiceDisplayNameW)

# BOOL WINAPI QueryServiceConfig(
#   _In_       SC_HANDLE hService,
#   _Out_opt_  LPQUERY_SERVICE_CONFIG lpServiceConfig,
#   _In_       DWORD cbBufSize,
#   _Out_      LPDWORD pcbBytesNeeded
# );

# TO DO

# BOOL WINAPI QueryServiceConfig2(
#   _In_       SC_HANDLE hService,
#   _In_       DWORD dwInfoLevel,
#   _Out_opt_  LPBYTE lpBuffer,
#   _In_       DWORD cbBufSize,
#   _Out_      LPDWORD pcbBytesNeeded
# );

# TO DO

# BOOL WINAPI ChangeServiceConfig(
#   _In_       SC_HANDLE hService,
#   _In_       DWORD dwServiceType,
#   _In_       DWORD dwStartType,
#   _In_       DWORD dwErrorControl,
#   _In_opt_   LPCTSTR lpBinaryPathName,
#   _In_opt_   LPCTSTR lpLoadOrderGroup,
#   _Out_opt_  LPDWORD lpdwTagId,
#   _In_opt_   LPCTSTR lpDependencies,
#   _In_opt_   LPCTSTR lpServiceStartName,
#   _In_opt_   LPCTSTR lpPassword,
#   _In_opt_   LPCTSTR lpDisplayName
# );

# TO DO

# BOOL WINAPI ChangeServiceConfig2(
#   _In_      SC_HANDLE hService,
#   _In_      DWORD dwInfoLevel,
#   _In_opt_  LPVOID lpInfo
# );

# TO DO


# BOOL WINAPI StartService(
#   _In_      SC_HANDLE hService,
#   _In_      DWORD dwNumServiceArgs,
#   _In_opt_  LPCTSTR *lpServiceArgVectors
# );
def StartServiceA(hService, ServiceArgVectors=None):
    _StartServiceA = windll.advapi32.StartServiceA
    _StartServiceA.argtypes = [SC_HANDLE, DWORD, LPVOID]
    _StartServiceA.restype = bool
    _StartServiceA.errcheck = RaiseIfZero

    if ServiceArgVectors:
        dwNumServiceArgs = len(ServiceArgVectors)
        CServiceArgVectors = (LPSTR * dwNumServiceArgs)(*ServiceArgVectors)
        lpServiceArgVectors = ctypes.pointer(CServiceArgVectors)
    else:
        dwNumServiceArgs = 0
        lpServiceArgVectors = None
    _StartServiceA(hService, dwNumServiceArgs, lpServiceArgVectors)


def StartServiceW(hService, ServiceArgVectors=None):
    _StartServiceW = windll.advapi32.StartServiceW
    _StartServiceW.argtypes = [SC_HANDLE, DWORD, LPVOID]
    _StartServiceW.restype = bool
    _StartServiceW.errcheck = RaiseIfZero

    if ServiceArgVectors:
        dwNumServiceArgs = len(ServiceArgVectors)
        CServiceArgVectors = (LPWSTR * dwNumServiceArgs)(*ServiceArgVectors)
        lpServiceArgVectors = ctypes.pointer(CServiceArgVectors)
    else:
        dwNumServiceArgs = 0
        lpServiceArgVectors = None
    _StartServiceW(hService, dwNumServiceArgs, lpServiceArgVectors)


StartService = GuessStringType(StartServiceA, StartServiceW)


# BOOL WINAPI ControlService(
#   _In_   SC_HANDLE hService,
#   _In_   DWORD dwControl,
#   _Out_  LPSERVICE_STATUS lpServiceStatus
# );
def ControlService(hService, dwControl):
    _ControlService = windll.advapi32.ControlService
    _ControlService.argtypes = [SC_HANDLE, DWORD, LPSERVICE_STATUS]
    _ControlService.restype = bool
    _ControlService.errcheck = RaiseIfZero

    rawServiceStatus = SERVICE_STATUS()
    _ControlService(hService, dwControl, byref(rawServiceStatus))
    return ServiceStatus(rawServiceStatus)


# BOOL WINAPI ControlServiceEx(
#   _In_     SC_HANDLE hService,
#   _In_     DWORD dwControl,
#   _In_     DWORD dwInfoLevel,
#   _Inout_  PVOID pControlParams
# );

# TO DO

# DWORD WINAPI NotifyServiceStatusChange(
#   _In_  SC_HANDLE hService,
#   _In_  DWORD dwNotifyMask,
#   _In_  PSERVICE_NOTIFY pNotifyBuffer
# );

# TO DO


# BOOL WINAPI QueryServiceStatus(
#   _In_   SC_HANDLE hService,
#   _Out_  LPSERVICE_STATUS lpServiceStatus
# );
def QueryServiceStatus(hService):
    _QueryServiceStatus = windll.advapi32.QueryServiceStatus
    _QueryServiceStatus.argtypes = [SC_HANDLE, LPSERVICE_STATUS]
    _QueryServiceStatus.restype = bool
    _QueryServiceStatus.errcheck = RaiseIfZero

    rawServiceStatus = SERVICE_STATUS()
    _QueryServiceStatus(hService, byref(rawServiceStatus))
    return ServiceStatus(rawServiceStatus)


# BOOL WINAPI QueryServiceStatusEx(
#   _In_       SC_HANDLE hService,
#   _In_       SC_STATUS_TYPE InfoLevel,
#   _Out_opt_  LPBYTE lpBuffer,
#   _In_       DWORD cbBufSize,
#   _Out_      LPDWORD pcbBytesNeeded
# );
def QueryServiceStatusEx(hService, InfoLevel=SC_STATUS_PROCESS_INFO):
    if InfoLevel != SC_STATUS_PROCESS_INFO:
        raise NotImplementedError()

    _QueryServiceStatusEx = windll.advapi32.QueryServiceStatusEx
    _QueryServiceStatusEx.argtypes = [SC_HANDLE, SC_STATUS_TYPE, LPVOID, DWORD, LPDWORD]
    _QueryServiceStatusEx.restype = bool
    _QueryServiceStatusEx.errcheck = RaiseIfZero

    lpBuffer = SERVICE_STATUS_PROCESS()
    cbBytesNeeded = DWORD(sizeof(lpBuffer))
    _QueryServiceStatusEx(hService, InfoLevel, byref(lpBuffer), sizeof(lpBuffer), byref(cbBytesNeeded))
    return ServiceStatusProcess(lpBuffer)


# BOOL WINAPI EnumServicesStatus(
#   _In_         SC_HANDLE hSCManager,
#   _In_         DWORD dwServiceType,
#   _In_         DWORD dwServiceState,
#   _Out_opt_    LPENUM_SERVICE_STATUS lpServices,
#   _In_         DWORD cbBufSize,
#   _Out_        LPDWORD pcbBytesNeeded,
#   _Out_        LPDWORD lpServicesReturned,
#   _Inout_opt_  LPDWORD lpResumeHandle
# );
def EnumServicesStatusA(hSCManager, dwServiceType=SERVICE_DRIVER | SERVICE_WIN32, dwServiceState=SERVICE_STATE_ALL):
    _EnumServicesStatusA = windll.advapi32.EnumServicesStatusA
    _EnumServicesStatusA.argtypes = [SC_HANDLE, DWORD, DWORD, LPVOID, DWORD, LPDWORD, LPDWORD, LPDWORD]
    _EnumServicesStatusA.restype = bool

    cbBytesNeeded = DWORD(0)
    ServicesReturned = DWORD(0)
    ResumeHandle = DWORD(0)

    _EnumServicesStatusA(
        hSCManager, dwServiceType, dwServiceState, None, 0, byref(cbBytesNeeded), byref(ServicesReturned), byref(ResumeHandle)
    )

    Services = []
    success = False
    while GetLastError() == ERROR_MORE_DATA:
        if cbBytesNeeded.value < sizeof(ENUM_SERVICE_STATUSA):
            break
        ServicesBuffer = ctypes.create_string_buffer("", cbBytesNeeded.value)
        success = _EnumServicesStatusA(
            hSCManager,
            dwServiceType,
            dwServiceState,
            byref(ServicesBuffer),
            sizeof(ServicesBuffer),
            byref(cbBytesNeeded),
            byref(ServicesReturned),
            byref(ResumeHandle),
        )
        if sizeof(ServicesBuffer) < (sizeof(ENUM_SERVICE_STATUSA) * ServicesReturned.value):
            raise ctypes.WinError()
        lpServicesArray = ctypes.cast(ctypes.cast(ctypes.pointer(ServicesBuffer), ctypes.c_void_p), LPENUM_SERVICE_STATUSA)
        for index in compat.xrange(0, ServicesReturned.value):
            Services.append(ServiceStatusEntry(lpServicesArray[index]))
        if success:
            break
    if not success:
        raise ctypes.WinError()

    return Services


def EnumServicesStatusW(hSCManager, dwServiceType=SERVICE_DRIVER | SERVICE_WIN32, dwServiceState=SERVICE_STATE_ALL):
    _EnumServicesStatusW = windll.advapi32.EnumServicesStatusW
    _EnumServicesStatusW.argtypes = [SC_HANDLE, DWORD, DWORD, LPVOID, DWORD, LPDWORD, LPDWORD, LPDWORD]
    _EnumServicesStatusW.restype = bool

    cbBytesNeeded = DWORD(0)
    ServicesReturned = DWORD(0)
    ResumeHandle = DWORD(0)

    _EnumServicesStatusW(
        hSCManager, dwServiceType, dwServiceState, None, 0, byref(cbBytesNeeded), byref(ServicesReturned), byref(ResumeHandle)
    )

    Services = []
    success = False
    while GetLastError() == ERROR_MORE_DATA:
        if cbBytesNeeded.value < sizeof(ENUM_SERVICE_STATUSW):
            break
        ServicesBuffer = ctypes.create_string_buffer("", cbBytesNeeded.value)
        success = _EnumServicesStatusW(
            hSCManager,
            dwServiceType,
            dwServiceState,
            byref(ServicesBuffer),
            sizeof(ServicesBuffer),
            byref(cbBytesNeeded),
            byref(ServicesReturned),
            byref(ResumeHandle),
        )
        if sizeof(ServicesBuffer) < (sizeof(ENUM_SERVICE_STATUSW) * ServicesReturned.value):
            raise ctypes.WinError()
        lpServicesArray = ctypes.cast(ctypes.cast(ctypes.pointer(ServicesBuffer), ctypes.c_void_p), LPENUM_SERVICE_STATUSW)
        for index in compat.xrange(0, ServicesReturned.value):
            Services.append(ServiceStatusEntry(lpServicesArray[index]))
        if success:
            break
    if not success:
        raise ctypes.WinError()

    return Services


EnumServicesStatus = DefaultStringType(EnumServicesStatusA, EnumServicesStatusW)


# BOOL WINAPI EnumServicesStatusEx(
#   _In_         SC_HANDLE hSCManager,
#   _In_         SC_ENUM_TYPE InfoLevel,
#   _In_         DWORD dwServiceType,
#   _In_         DWORD dwServiceState,
#   _Out_opt_    LPBYTE lpServices,
#   _In_         DWORD cbBufSize,
#   _Out_        LPDWORD pcbBytesNeeded,
#   _Out_        LPDWORD lpServicesReturned,
#   _Inout_opt_  LPDWORD lpResumeHandle,
#   _In_opt_     LPCTSTR pszGroupName
# );
def EnumServicesStatusExA(
    hSCManager,
    InfoLevel=SC_ENUM_PROCESS_INFO,
    dwServiceType=SERVICE_DRIVER | SERVICE_WIN32,
    dwServiceState=SERVICE_STATE_ALL,
    pszGroupName=None,
):
    if InfoLevel != SC_ENUM_PROCESS_INFO:
        raise NotImplementedError()

    _EnumServicesStatusExA = windll.advapi32.EnumServicesStatusExA
    _EnumServicesStatusExA.argtypes = [SC_HANDLE, SC_ENUM_TYPE, DWORD, DWORD, LPVOID, DWORD, LPDWORD, LPDWORD, LPDWORD, LPSTR]
    _EnumServicesStatusExA.restype = bool

    cbBytesNeeded = DWORD(0)
    ServicesReturned = DWORD(0)
    ResumeHandle = DWORD(0)

    _EnumServicesStatusExA(
        hSCManager,
        InfoLevel,
        dwServiceType,
        dwServiceState,
        None,
        0,
        byref(cbBytesNeeded),
        byref(ServicesReturned),
        byref(ResumeHandle),
        pszGroupName,
    )

    Services = []
    success = False
    while GetLastError() == ERROR_MORE_DATA:
        if cbBytesNeeded.value < sizeof(ENUM_SERVICE_STATUS_PROCESSA):
            break
        ServicesBuffer = ctypes.create_string_buffer("", cbBytesNeeded.value)
        success = _EnumServicesStatusExA(
            hSCManager,
            InfoLevel,
            dwServiceType,
            dwServiceState,
            byref(ServicesBuffer),
            sizeof(ServicesBuffer),
            byref(cbBytesNeeded),
            byref(ServicesReturned),
            byref(ResumeHandle),
            pszGroupName,
        )
        if sizeof(ServicesBuffer) < (sizeof(ENUM_SERVICE_STATUS_PROCESSA) * ServicesReturned.value):
            raise ctypes.WinError()
        lpServicesArray = ctypes.cast(ctypes.cast(ctypes.pointer(ServicesBuffer), ctypes.c_void_p), LPENUM_SERVICE_STATUS_PROCESSA)
        for index in compat.xrange(0, ServicesReturned.value):
            Services.append(ServiceStatusProcessEntry(lpServicesArray[index]))
        if success:
            break
    if not success:
        raise ctypes.WinError()

    return Services


def EnumServicesStatusExW(
    hSCManager,
    InfoLevel=SC_ENUM_PROCESS_INFO,
    dwServiceType=SERVICE_DRIVER | SERVICE_WIN32,
    dwServiceState=SERVICE_STATE_ALL,
    pszGroupName=None,
):
    _EnumServicesStatusExW = windll.advapi32.EnumServicesStatusExW
    _EnumServicesStatusExW.argtypes = [SC_HANDLE, SC_ENUM_TYPE, DWORD, DWORD, LPVOID, DWORD, LPDWORD, LPDWORD, LPDWORD, LPWSTR]
    _EnumServicesStatusExW.restype = bool

    if InfoLevel != SC_ENUM_PROCESS_INFO:
        raise NotImplementedError()

    cbBytesNeeded = DWORD(0)
    ServicesReturned = DWORD(0)
    ResumeHandle = DWORD(0)

    _EnumServicesStatusExW(
        hSCManager,
        InfoLevel,
        dwServiceType,
        dwServiceState,
        None,
        0,
        byref(cbBytesNeeded),
        byref(ServicesReturned),
        byref(ResumeHandle),
        pszGroupName,
    )

    Services = []
    success = False
    while GetLastError() == ERROR_MORE_DATA:
        if cbBytesNeeded.value < sizeof(ENUM_SERVICE_STATUS_PROCESSW):
            break
        ServicesBuffer = ctypes.create_string_buffer("", cbBytesNeeded.value)
        success = _EnumServicesStatusExW(
            hSCManager,
            InfoLevel,
            dwServiceType,
            dwServiceState,
            byref(ServicesBuffer),
            sizeof(ServicesBuffer),
            byref(cbBytesNeeded),
            byref(ServicesReturned),
            byref(ResumeHandle),
            pszGroupName,
        )
        if sizeof(ServicesBuffer) < (sizeof(ENUM_SERVICE_STATUS_PROCESSW) * ServicesReturned.value):
            raise ctypes.WinError()
        lpServicesArray = ctypes.cast(ctypes.cast(ctypes.pointer(ServicesBuffer), ctypes.c_void_p), LPENUM_SERVICE_STATUS_PROCESSW)
        for index in compat.xrange(0, ServicesReturned.value):
            Services.append(ServiceStatusProcessEntry(lpServicesArray[index]))
        if success:
            break
    if not success:
        raise ctypes.WinError()

    return Services


EnumServicesStatusEx = DefaultStringType(EnumServicesStatusExA, EnumServicesStatusExW)

# BOOL WINAPI EnumDependentServices(
#   _In_       SC_HANDLE hService,
#   _In_       DWORD dwServiceState,
#   _Out_opt_  LPENUM_SERVICE_STATUS lpServices,
#   _In_       DWORD cbBufSize,
#   _Out_      LPDWORD pcbBytesNeeded,
#   _Out_      LPDWORD lpServicesReturned
# );

# TO DO

# ==============================================================================
# This calculates the list of exported symbols.
_all = set(vars().keys()).difference(_all)
__all__ = [_x for _x in _all if not _x.startswith("_")]
__all__.sort()
# ==============================================================================

# === NexusCore/openenv\Lib\site-packages\numpy\linalg\_linalg.py ===
"""Lite version of scipy.linalg.

Notes
-----
This module is a lite version of the linalg.py module in SciPy which
contains high-level Python interface to the LAPACK library.  The lite
version only accesses the following LAPACK functions: dgesv, zgesv,
dgeev, zgeev, dgesdd, zgesdd, dgelsd, zgelsd, dsyevd, zheevd, dgetrf,
zgetrf, dpotrf, zpotrf, dgeqrf, zgeqrf, zungqr, dorgqr.
"""

__all__ = ['matrix_power', 'solve', 'tensorsolve', 'tensorinv', 'inv',
           'cholesky', 'eigvals', 'eigvalsh', 'pinv', 'slogdet', 'det',
           'svd', 'svdvals', 'eig', 'eigh', 'lstsq', 'norm', 'qr', 'cond',
           'matrix_rank', 'LinAlgError', 'multi_dot', 'trace', 'diagonal',
           'cross', 'outer', 'tensordot', 'matmul', 'matrix_transpose',
           'matrix_norm', 'vector_norm', 'vecdot']

import functools
import operator
import warnings
from typing import Any, NamedTuple

from numpy._core import (
    abs,
    add,
    all,
    amax,
    amin,
    argsort,
    array,
    asanyarray,
    asarray,
    atleast_2d,
    cdouble,
    complexfloating,
    count_nonzero,
    csingle,
    divide,
    dot,
    double,
    empty,
    empty_like,
    errstate,
    finfo,
    inexact,
    inf,
    intc,
    intp,
    isfinite,
    isnan,
    moveaxis,
    multiply,
    newaxis,
    object_,
    overrides,
    prod,
    reciprocal,
    sign,
    single,
    sort,
    sqrt,
    sum,
    swapaxes,
    zeros,
)
from numpy._core import (
    cross as _core_cross,
)
from numpy._core import (
    diagonal as _core_diagonal,
)
from numpy._core import (
    matmul as _core_matmul,
)
from numpy._core import (
    matrix_transpose as _core_matrix_transpose,
)
from numpy._core import (
    outer as _core_outer,
)
from numpy._core import (
    tensordot as _core_tensordot,
)
from numpy._core import (
    trace as _core_trace,
)
from numpy._core import (
    transpose as _core_transpose,
)
from numpy._core import (
    vecdot as _core_vecdot,
)
from numpy._globals import _NoValue
from numpy._typing import NDArray
from numpy._utils import set_module
from numpy.lib._twodim_base_impl import eye, triu
from numpy.lib.array_utils import normalize_axis_index, normalize_axis_tuple
from numpy.linalg import _umath_linalg


class EigResult(NamedTuple):
    eigenvalues: NDArray[Any]
    eigenvectors: NDArray[Any]

class EighResult(NamedTuple):
    eigenvalues: NDArray[Any]
    eigenvectors: NDArray[Any]

class QRResult(NamedTuple):
    Q: NDArray[Any]
    R: NDArray[Any]

class SlogdetResult(NamedTuple):
    sign: NDArray[Any]
    logabsdet: NDArray[Any]

class SVDResult(NamedTuple):
    U: NDArray[Any]
    S: NDArray[Any]
    Vh: NDArray[Any]


array_function_dispatch = functools.partial(
    overrides.array_function_dispatch, module='numpy.linalg'
)


fortran_int = intc


@set_module('numpy.linalg')
class LinAlgError(ValueError):
    """
    Generic Python-exception-derived object raised by linalg functions.

    General purpose exception class, derived from Python's ValueError
    class, programmatically raised in linalg functions when a Linear
    Algebra-related condition would prevent further correct execution of the
    function.

    Parameters
    ----------
    None

    Examples
    --------
    >>> from numpy import linalg as LA
    >>> LA.inv(np.zeros((2,2)))
    Traceback (most recent call last):
      File "<stdin>", line 1, in <module>
      File "...linalg.py", line 350,
        in inv return wrap(solve(a, identity(a.shape[0], dtype=a.dtype)))
      File "...linalg.py", line 249,
        in solve
        raise LinAlgError('Singular matrix')
    numpy.linalg.LinAlgError: Singular matrix

    """


def _raise_linalgerror_singular(err, flag):
    raise LinAlgError("Singular matrix")

def _raise_linalgerror_nonposdef(err, flag):
    raise LinAlgError("Matrix is not positive definite")

def _raise_linalgerror_eigenvalues_nonconvergence(err, flag):
    raise LinAlgError("Eigenvalues did not converge")

def _raise_linalgerror_svd_nonconvergence(err, flag):
    raise LinAlgError("SVD did not converge")

def _raise_linalgerror_lstsq(err, flag):
    raise LinAlgError("SVD did not converge in Linear Least Squares")

def _raise_linalgerror_qr(err, flag):
    raise LinAlgError("Incorrect argument found while performing "
                      "QR factorization")


def _makearray(a):
    new = asarray(a)
    wrap = getattr(a, "__array_wrap__", new.__array_wrap__)
    return new, wrap

def isComplexType(t):
    return issubclass(t, complexfloating)


_real_types_map = {single: single,
                   double: double,
                   csingle: single,
                   cdouble: double}

_complex_types_map = {single: csingle,
                      double: cdouble,
                      csingle: csingle,
                      cdouble: cdouble}

def _realType(t, default=double):
    return _real_types_map.get(t, default)

def _complexType(t, default=cdouble):
    return _complex_types_map.get(t, default)

def _commonType(*arrays):
    # in lite version, use higher precision (always double or cdouble)
    result_type = single
    is_complex = False
    for a in arrays:
        type_ = a.dtype.type
        if issubclass(type_, inexact):
            if isComplexType(type_):
                is_complex = True
            rt = _realType(type_, default=None)
            if rt is double:
                result_type = double
            elif rt is None:
                # unsupported inexact scalar
                raise TypeError(f"array type {a.dtype.name} is unsupported in linalg")
        else:
            result_type = double
    if is_complex:
        result_type = _complex_types_map[result_type]
        return cdouble, result_type
    else:
        return double, result_type


def _to_native_byte_order(*arrays):
    ret = []
    for arr in arrays:
        if arr.dtype.byteorder not in ('=', '|'):
            ret.append(asarray(arr, dtype=arr.dtype.newbyteorder('=')))
        else:
            ret.append(arr)
    if len(ret) == 1:
        return ret[0]
    else:
        return ret


def _assert_2d(*arrays):
    for a in arrays:
        if a.ndim != 2:
            raise LinAlgError('%d-dimensional array given. Array must be '
                    'two-dimensional' % a.ndim)

def _assert_stacked_2d(*arrays):
    for a in arrays:
        if a.ndim < 2:
            raise LinAlgError('%d-dimensional array given. Array must be '
                    'at least two-dimensional' % a.ndim)

def _assert_stacked_square(*arrays):
    for a in arrays:
        try:
            m, n = a.shape[-2:]
        except ValueError:
            raise LinAlgError('%d-dimensional array given. Array must be '
                    'at least two-dimensional' % a.ndim)
        if m != n:
            raise LinAlgError('Last 2 dimensions of the array must be square')

def _assert_finite(*arrays):
    for a in arrays:
        if not isfinite(a).all():
            raise LinAlgError("Array must not contain infs or NaNs")

def _is_empty_2d(arr):
    # check size first for efficiency
    return arr.size == 0 and prod(arr.shape[-2:]) == 0


def transpose(a):
    """
    Transpose each matrix in a stack of matrices.

    Unlike np.transpose, this only swaps the last two axes, rather than all of
    them

    Parameters
    ----------
    a : (...,M,N) array_like

    Returns
    -------
    aT : (...,N,M) ndarray
    """
    return swapaxes(a, -1, -2)

# Linear equations

def _tensorsolve_dispatcher(a, b, axes=None):
    return (a, b)


@array_function_dispatch(_tensorsolve_dispatcher)
def tensorsolve(a, b, axes=None):
    """
    Solve the tensor equation ``a x = b`` for x.

    It is assumed that all indices of `x` are summed over in the product,
    together with the rightmost indices of `a`, as is done in, for example,
    ``tensordot(a, x, axes=x.ndim)``.

    Parameters
    ----------
    a : array_like
        Coefficient tensor, of shape ``b.shape + Q``. `Q`, a tuple, equals
        the shape of that sub-tensor of `a` consisting of the appropriate
        number of its rightmost indices, and must be such that
        ``prod(Q) == prod(b.shape)`` (in which sense `a` is said to be
        'square').
    b : array_like
        Right-hand tensor, which can be of any shape.
    axes : tuple of ints, optional
        Axes in `a` to reorder to the right, before inversion.
        If None (default), no reordering is done.

    Returns
    -------
    x : ndarray, shape Q

    Raises
    ------
    LinAlgError
        If `a` is singular or not 'square' (in the above sense).

    See Also
    --------
    numpy.tensordot, tensorinv, numpy.einsum

    Examples
    --------
    >>> import numpy as np
    >>> a = np.eye(2*3*4)
    >>> a.shape = (2*3, 4, 2, 3, 4)
    >>> rng = np.random.default_rng()
    >>> b = rng.normal(size=(2*3, 4))
    >>> x = np.linalg.tensorsolve(a, b)
    >>> x.shape
    (2, 3, 4)
    >>> np.allclose(np.tensordot(a, x, axes=3), b)
    True

    """
    a, wrap = _makearray(a)
    b = asarray(b)
    an = a.ndim

    if axes is not None:
        allaxes = list(range(an))
        for k in axes:
            allaxes.remove(k)
            allaxes.insert(an, k)
        a = a.transpose(allaxes)

    oldshape = a.shape[-(an - b.ndim):]
    prod = 1
    for k in oldshape:
        prod *= k

    if a.size != prod ** 2:
        raise LinAlgError(
            "Input arrays must satisfy the requirement \
            prod(a.shape[b.ndim:]) == prod(a.shape[:b.ndim])"
        )

    a = a.reshape(prod, prod)
    b = b.ravel()
    res = wrap(solve(a, b))
    res.shape = oldshape
    return res


def _solve_dispatcher(a, b):
    return (a, b)


@array_function_dispatch(_solve_dispatcher)
def solve(a, b):
    """
    Solve a linear matrix equation, or system of linear scalar equations.

    Computes the "exact" solution, `x`, of the well-determined, i.e., full
    rank, linear matrix equation `ax = b`.

    Parameters
    ----------
    a : (..., M, M) array_like
        Coefficient matrix.
    b : {(M,), (..., M, K)}, array_like
        Ordinate or "dependent variable" values.

    Returns
    -------
    x : {(..., M,), (..., M, K)} ndarray
        Solution to the system a x = b.  Returned shape is (..., M) if b is
        shape (M,) and (..., M, K) if b is (..., M, K), where the "..." part is
        broadcasted between a and b.

    Raises
    ------
    LinAlgError
        If `a` is singular or not square.

    See Also
    --------
    scipy.linalg.solve : Similar function in SciPy.

    Notes
    -----
    Broadcasting rules apply, see the `numpy.linalg` documentation for
    details.

    The solutions are computed using LAPACK routine ``_gesv``.

    `a` must be square and of full-rank, i.e., all rows (or, equivalently,
    columns) must be linearly independent; if either is not true, use
    `lstsq` for the least-squares best "solution" of the
    system/equation.

    .. versionchanged:: 2.0

       The b array is only treated as a shape (M,) column vector if it is
       exactly 1-dimensional. In all other instances it is treated as a stack
       of (M, K) matrices. Previously b would be treated as a stack of (M,)
       vectors if b.ndim was equal to a.ndim - 1.

    References
    ----------
    .. [1] G. Strang, *Linear Algebra and Its Applications*, 2nd Ed., Orlando,
           FL, Academic Press, Inc., 1980, pg. 22.

    Examples
    --------
    Solve the system of equations:
    ``x0 + 2 * x1 = 1`` and
    ``3 * x0 + 5 * x1 = 2``:

    >>> import numpy as np
    >>> a = np.array([[1, 2], [3, 5]])
    >>> b = np.array([1, 2])
    >>> x = np.linalg.solve(a, b)
    >>> x
    array([-1.,  1.])

    Check that the solution is correct:

    >>> np.allclose(np.dot(a, x), b)
    True

    """
    a, _ = _makearray(a)
    _assert_stacked_square(a)
    b, wrap = _makearray(b)
    t, result_t = _commonType(a, b)

    # We use the b = (..., M,) logic, only if the number of extra dimensions
    # match exactly
    if b.ndim == 1:
        gufunc = _umath_linalg.solve1
    else:
        gufunc = _umath_linalg.solve

    signature = 'DD->D' if isComplexType(t) else 'dd->d'
    with errstate(call=_raise_linalgerror_singular, invalid='call',
                  over='ignore', divide='ignore', under='ignore'):
        r = gufunc(a, b, signature=signature)

    return wrap(r.astype(result_t, copy=False))


def _tensorinv_dispatcher(a, ind=None):
    return (a,)


@array_function_dispatch(_tensorinv_dispatcher)
def tensorinv(a, ind=2):
    """
    Compute the 'inverse' of an N-dimensional array.

    The result is an inverse for `a` relative to the tensordot operation
    ``tensordot(a, b, ind)``, i. e., up to floating-point accuracy,
    ``tensordot(tensorinv(a), a, ind)`` is the "identity" tensor for the
    tensordot operation.

    Parameters
    ----------
    a : array_like
        Tensor to 'invert'. Its shape must be 'square', i. e.,
        ``prod(a.shape[:ind]) == prod(a.shape[ind:])``.
    ind : int, optional
        Number of first indices that are involved in the inverse sum.
        Must be a positive integer, default is 2.

    Returns
    -------
    b : ndarray
        `a`'s tensordot inverse, shape ``a.shape[ind:] + a.shape[:ind]``.

    Raises
    ------
    LinAlgError
        If `a` is singular or not 'square' (in the above sense).

    See Also
    --------
    numpy.tensordot, tensorsolve

    Examples
    --------
    >>> import numpy as np
    >>> a = np.eye(4*6)
    >>> a.shape = (4, 6, 8, 3)
    >>> ainv = np.linalg.tensorinv(a, ind=2)
    >>> ainv.shape
    (8, 3, 4, 6)
    >>> rng = np.random.default_rng()
    >>> b = rng.normal(size=(4, 6))
    >>> np.allclose(np.tensordot(ainv, b), np.linalg.tensorsolve(a, b))
    True

    >>> a = np.eye(4*6)
    >>> a.shape = (24, 8, 3)
    >>> ainv = np.linalg.tensorinv(a, ind=1)
    >>> ainv.shape
    (8, 3, 24)
    >>> rng = np.random.default_rng()
    >>> b = rng.normal(size=24)
    >>> np.allclose(np.tensordot(ainv, b, 1), np.linalg.tensorsolve(a, b))
    True

    """
    a = asarray(a)
    oldshape = a.shape
    prod = 1
    if ind > 0:
        invshape = oldshape[ind:] + oldshape[:ind]
        for k in oldshape[ind:]:
            prod *= k
    else:
        raise ValueError("Invalid ind argument.")
    a = a.reshape(prod, -1)
    ia = inv(a)
    return ia.reshape(*invshape)


# Matrix inversion

def _unary_dispatcher(a):
    return (a,)


@array_function_dispatch(_unary_dispatcher)
def inv(a):
    """
    Compute the inverse of a matrix.

    Given a square matrix `a`, return the matrix `ainv` satisfying
    ``a @ ainv = ainv @ a = eye(a.shape[0])``.

    Parameters
    ----------
    a : (..., M, M) array_like
        Matrix to be inverted.

    Returns
    -------
    ainv : (..., M, M) ndarray or matrix
        Inverse of the matrix `a`.

    Raises
    ------
    LinAlgError
        If `a` is not square or inversion fails.

    See Also
    --------
    scipy.linalg.inv : Similar function in SciPy.
    numpy.linalg.cond : Compute the condition number of a matrix.
    numpy.linalg.svd : Compute the singular value decomposition of a matrix.

    Notes
    -----
    Broadcasting rules apply, see the `numpy.linalg` documentation for
    details.

    If `a` is detected to be singular, a `LinAlgError` is raised. If `a` is
    ill-conditioned, a `LinAlgError` may or may not be raised, and results may
    be inaccurate due to floating-point errors.

    References
    ----------
    .. [1] Wikipedia, "Condition number",
           https://en.wikipedia.org/wiki/Condition_number

    Examples
    --------
    >>> import numpy as np
    >>> from numpy.linalg import inv
    >>> a = np.array([[1., 2.], [3., 4.]])
    >>> ainv = inv(a)
    >>> np.allclose(a @ ainv, np.eye(2))
    True
    >>> np.allclose(ainv @ a, np.eye(2))
    True

    If a is a matrix object, then the return value is a matrix as well:

    >>> ainv = inv(np.matrix(a))
    >>> ainv
    matrix([[-2. ,  1. ],
            [ 1.5, -0.5]])

    Inverses of several matrices can be computed at once:

    >>> a = np.array([[[1., 2.], [3., 4.]], [[1, 3], [3, 5]]])
    >>> inv(a)
    array([[[-2.  ,  1.  ],
            [ 1.5 , -0.5 ]],
           [[-1.25,  0.75],
            [ 0.75, -0.25]]])

    If a matrix is close to singular, the computed inverse may not satisfy
    ``a @ ainv = ainv @ a = eye(a.shape[0])`` even if a `LinAlgError`
    is not raised:

    >>> a = np.array([[2,4,6],[2,0,2],[6,8,14]])
    >>> inv(a)  # No errors raised
    array([[-1.12589991e+15, -5.62949953e+14,  5.62949953e+14],
       [-1.12589991e+15, -5.62949953e+14,  5.62949953e+14],
       [ 1.12589991e+15,  5.62949953e+14, -5.62949953e+14]])
    >>> a @ inv(a)
    array([[ 0.   , -0.5  ,  0.   ],  # may vary
           [-0.5  ,  0.625,  0.25 ],
           [ 0.   ,  0.   ,  1.   ]])

    To detect ill-conditioned matrices, you can use `numpy.linalg.cond` to
    compute its *condition number* [1]_. The larger the condition number, the
    more ill-conditioned the matrix is. As a rule of thumb, if the condition
    number ``cond(a) = 10**k``, then you may lose up to ``k`` digits of
    accuracy on top of what would be lost to the numerical method due to loss
    of precision from arithmetic methods.

    >>> from numpy.linalg import cond
    >>> cond(a)
    np.float64(8.659885634118668e+17)  # may vary

    It is also possible to detect ill-conditioning by inspecting the matrix's
    singular values directly. The ratio between the largest and the smallest
    singular value is the condition number:

    >>> from numpy.linalg import svd
    >>> sigma = svd(a, compute_uv=False)  # Do not compute singular vectors
    >>> sigma.max()/sigma.min()
    8.659885634118668e+17  # may vary

    """
    a, wrap = _makearray(a)
    _assert_stacked_square(a)
    t, result_t = _commonType(a)

    signature = 'D->D' if isComplexType(t) else 'd->d'
    with errstate(call=_raise_linalgerror_singular, invalid='call',
                  over='ignore', divide='ignore', under='ignore'):
        ainv = _umath_linalg.inv(a, signature=signature)
    return wrap(ainv.astype(result_t, copy=False))


def _matrix_power_dispatcher(a, n):
    return (a,)


@array_function_dispatch(_matrix_power_dispatcher)
def matrix_power(a, n):
    """
    Raise a square matrix to the (integer) power `n`.

    For positive integers `n`, the power is computed by repeated matrix
    squarings and matrix multiplications. If ``n == 0``, the identity matrix
    of the same shape as M is returned. If ``n < 0``, the inverse
    is computed and then raised to the ``abs(n)``.

    .. note:: Stacks of object matrices are not currently supported.

    Parameters
    ----------
    a : (..., M, M) array_like
        Matrix to be "powered".
    n : int
        The exponent can be any integer or long integer, positive,
        negative, or zero.

    Returns
    -------
    a**n : (..., M, M) ndarray or matrix object
        The return value is the same shape and type as `M`;
        if the exponent is positive or zero then the type of the
        elements is the same as those of `M`. If the exponent is
        negative the elements are floating-point.

    Raises
    ------
    LinAlgError
        For matrices that are not square or that (for negative powers) cannot
        be inverted numerically.

    Examples
    --------
    >>> import numpy as np
    >>> from numpy.linalg import matrix_power
    >>> i = np.array([[0, 1], [-1, 0]]) # matrix equiv. of the imaginary unit
    >>> matrix_power(i, 3) # should = -i
    array([[ 0, -1],
           [ 1,  0]])
    >>> matrix_power(i, 0)
    array([[1, 0],
           [0, 1]])
    >>> matrix_power(i, -3) # should = 1/(-i) = i, but w/ f.p. elements
    array([[ 0.,  1.],
           [-1.,  0.]])

    Somewhat more sophisticated example

    >>> q = np.zeros((4, 4))
    >>> q[0:2, 0:2] = -i
    >>> q[2:4, 2:4] = i
    >>> q # one of the three quaternion units not equal to 1
    array([[ 0., -1.,  0.,  0.],
           [ 1.,  0.,  0.,  0.],
           [ 0.,  0.,  0.,  1.],
           [ 0.,  0., -1.,  0.]])
    >>> matrix_power(q, 2) # = -np.eye(4)
    array([[-1.,  0.,  0.,  0.],
           [ 0., -1.,  0.,  0.],
           [ 0.,  0., -1.,  0.],
           [ 0.,  0.,  0., -1.]])

    """
    a = asanyarray(a)
    _assert_stacked_square(a)

    try:
        n = operator.index(n)
    except TypeError as e:
        raise TypeError("exponent must be an integer") from e

    # Fall back on dot for object arrays. Object arrays are not supported by
    # the current implementation of matmul using einsum
    if a.dtype != object:
        fmatmul = matmul
    elif a.ndim == 2:
        fmatmul = dot
    else:
        raise NotImplementedError(
            "matrix_power not supported for stacks of object arrays")

    if n == 0:
        a = empty_like(a)
        a[...] = eye(a.shape[-2], dtype=a.dtype)
        return a

    elif n < 0:
        a = inv(a)
        n = abs(n)

    # short-cuts.
    if n == 1:
        return a

    elif n == 2:
        return fmatmul(a, a)

    elif n == 3:
        return fmatmul(fmatmul(a, a), a)

    # Use binary decomposition to reduce the number of matrix multiplications.
    # Here, we iterate over the bits of n, from LSB to MSB, raise `a` to
    # increasing powers of 2, and multiply into the result as needed.
    z = result = None
    while n > 0:
        z = a if z is None else fmatmul(z, z)
        n, bit = divmod(n, 2)
        if bit:
            result = z if result is None else fmatmul(result, z)

    return result


# Cholesky decomposition

def _cholesky_dispatcher(a, /, *, upper=None):
    return (a,)


@array_function_dispatch(_cholesky_dispatcher)
def cholesky(a, /, *, upper=False):
    """
    Cholesky decomposition.

    Return the lower or upper Cholesky decomposition, ``L * L.H`` or
    ``U.H * U``, of the square matrix ``a``, where ``L`` is lower-triangular,
    ``U`` is upper-triangular, and ``.H`` is the conjugate transpose operator
    (which is the ordinary transpose if ``a`` is real-valued). ``a`` must be
    Hermitian (symmetric if real-valued) and positive-definite. No checking is
    performed to verify whether ``a`` is Hermitian or not. In addition, only
    the lower or upper-triangular and diagonal elements of ``a`` are used.
    Only ``L`` or ``U`` is actually returned.

    Parameters
    ----------
    a : (..., M, M) array_like
        Hermitian (symmetric if all elements are real), positive-definite
        input matrix.
    upper : bool
        If ``True``, the result must be the upper-triangular Cholesky factor.
        If ``False``, the result must be the lower-triangular Cholesky factor.
        Default: ``False``.

    Returns
    -------
    L : (..., M, M) array_like
        Lower or upper-triangular Cholesky factor of `a`. Returns a matrix
        object if `a` is a matrix object.

    Raises
    ------
    LinAlgError
       If the decomposition fails, for example, if `a` is not
       positive-definite.

    See Also
    --------
    scipy.linalg.cholesky : Similar function in SciPy.
    scipy.linalg.cholesky_banded : Cholesky decompose a banded Hermitian
                                   positive-definite matrix.
    scipy.linalg.cho_factor : Cholesky decomposition of a matrix, to use in
                              `scipy.linalg.cho_solve`.

    Notes
    -----
    Broadcasting rules apply, see the `numpy.linalg` documentation for
    details.

    The Cholesky decomposition is often used as a fast way of solving

    .. math:: A \\mathbf{x} = \\mathbf{b}

    (when `A` is both Hermitian/symmetric and positive-definite).

    First, we solve for :math:`\\mathbf{y}` in

    .. math:: L \\mathbf{y} = \\mathbf{b},

    and then for :math:`\\mathbf{x}` in

    .. math:: L^{H} \\mathbf{x} = \\mathbf{y}.

    Examples
    --------
    >>> import numpy as np
    >>> A = np.array([[1,-2j],[2j,5]])
    >>> A
    array([[ 1.+0.j, -0.-2.j],
           [ 0.+2.j,  5.+0.j]])
    >>> L = np.linalg.cholesky(A)
    >>> L
    array([[1.+0.j, 0.+0.j],
           [0.+2.j, 1.+0.j]])
    >>> np.dot(L, L.T.conj()) # verify that L * L.H = A
    array([[1.+0.j, 0.-2.j],
           [0.+2.j, 5.+0.j]])
    >>> A = [[1,-2j],[2j,5]] # what happens if A is only array_like?
    >>> np.linalg.cholesky(A) # an ndarray object is returned
    array([[1.+0.j, 0.+0.j],
           [0.+2.j, 1.+0.j]])
    >>> # But a matrix object is returned if A is a matrix object
    >>> np.linalg.cholesky(np.matrix(A))
    matrix([[ 1.+0.j,  0.+0.j],
            [ 0.+2.j,  1.+0.j]])
    >>> # The upper-triangular Cholesky factor can also be obtained.
    >>> np.linalg.cholesky(A, upper=True)
    array([[1.-0.j, 0.-2.j],
           [0.-0.j, 1.-0.j]])

    """
    gufunc = _umath_linalg.cholesky_up if upper else _umath_linalg.cholesky_lo
    a, wrap = _makearray(a)
    _assert_stacked_square(a)
    t, result_t = _commonType(a)
    signature = 'D->D' if isComplexType(t) else 'd->d'
    with errstate(call=_raise_linalgerror_nonposdef, invalid='call',
                  over='ignore', divide='ignore', under='ignore'):
        r = gufunc(a, signature=signature)
    return wrap(r.astype(result_t, copy=False))


# outer product


def _outer_dispatcher(x1, x2):
    return (x1, x2)


@array_function_dispatch(_outer_dispatcher)
def outer(x1, x2, /):
    """
    Compute the outer product of two vectors.

    This function is Array API compatible. Compared to ``np.outer``
    it accepts 1-dimensional inputs only.

    Parameters
    ----------
    x1 : (M,) array_like
        One-dimensional input array of size ``N``.
        Must have a numeric data type.
    x2 : (N,) array_like
        One-dimensional input array of size ``M``.
        Must have a numeric data type.

    Returns
    -------
    out : (M, N) ndarray
        ``out[i, j] = a[i] * b[j]``

    See also
    --------
    outer

    Examples
    --------
    Make a (*very* coarse) grid for computing a Mandelbrot set:

    >>> rl = np.linalg.outer(np.ones((5,)), np.linspace(-2, 2, 5))
    >>> rl
    array([[-2., -1.,  0.,  1.,  2.],
           [-2., -1.,  0.,  1.,  2.],
           [-2., -1.,  0.,  1.,  2.],
           [-2., -1.,  0.,  1.,  2.],
           [-2., -1.,  0.,  1.,  2.]])
    >>> im = np.linalg.outer(1j*np.linspace(2, -2, 5), np.ones((5,)))
    >>> im
    array([[0.+2.j, 0.+2.j, 0.+2.j, 0.+2.j, 0.+2.j],
           [0.+1.j, 0.+1.j, 0.+1.j, 0.+1.j, 0.+1.j],
           [0.+0.j, 0.+0.j, 0.+0.j, 0.+0.j, 0.+0.j],
           [0.-1.j, 0.-1.j, 0.-1.j, 0.-1.j, 0.-1.j],
           [0.-2.j, 0.-2.j, 0.-2.j, 0.-2.j, 0.-2.j]])
    >>> grid = rl + im
    >>> grid
    array([[-2.+2.j, -1.+2.j,  0.+2.j,  1.+2.j,  2.+2.j],
           [-2.+1.j, -1.+1.j,  0.+1.j,  1.+1.j,  2.+1.j],
           [-2.+0.j, -1.+0.j,  0.+0.j,  1.+0.j,  2.+0.j],
           [-2.-1.j, -1.-1.j,  0.-1.j,  1.-1.j,  2.-1.j],
           [-2.-2.j, -1.-2.j,  0.-2.j,  1.-2.j,  2.-2.j]])

    An example using a "vector" of letters:

    >>> x = np.array(['a', 'b', 'c'], dtype=object)
    >>> np.linalg.outer(x, [1, 2, 3])
    array([['a', 'aa', 'aaa'],
           ['b', 'bb', 'bbb'],
           ['c', 'cc', 'ccc']], dtype=object)

    """
    x1 = asanyarray(x1)
    x2 = asanyarray(x2)
    if x1.ndim != 1 or x2.ndim != 1:
        raise ValueError(
            "Input arrays must be one-dimensional, but they are "
            f"{x1.ndim=} and {x2.ndim=}."
        )
    return _core_outer(x1, x2, out=None)


# QR decomposition


def _qr_dispatcher(a, mode=None):
    return (a,)


@array_function_dispatch(_qr_dispatcher)
def qr(a, mode='reduced'):
    """
    Compute the qr factorization of a matrix.

    Factor the matrix `a` as *qr*, where `q` is orthonormal and `r` is
    upper-triangular.

    Parameters
    ----------
    a : array_like, shape (..., M, N)
        An array-like object with the dimensionality of at least 2.
    mode : {'reduced', 'complete', 'r', 'raw'}, optional, default: 'reduced'
        If K = min(M, N), then

        * 'reduced'  : returns Q, R with dimensions (..., M, K), (..., K, N)
        * 'complete' : returns Q, R with dimensions (..., M, M), (..., M, N)
        * 'r'        : returns R only with dimensions (..., K, N)
        * 'raw'      : returns h, tau with dimensions (..., N, M), (..., K,)

        The options 'reduced', 'complete, and 'raw' are new in numpy 1.8,
        see the notes for more information. The default is 'reduced', and to
        maintain backward compatibility with earlier versions of numpy both
        it and the old default 'full' can be omitted. Note that array h
        returned in 'raw' mode is transposed for calling Fortran. The
        'economic' mode is deprecated.  The modes 'full' and 'economic' may
        be passed using only the first letter for backwards compatibility,
        but all others must be spelled out. See the Notes for more
        explanation.


    Returns
    -------
    When mode is 'reduced' or 'complete', the result will be a namedtuple with
    the attributes `Q` and `R`.

    Q : ndarray of float or complex, optional
        A matrix with orthonormal columns. When mode = 'complete' the
        result is an orthogonal/unitary matrix depending on whether or not
        a is real/complex. The determinant may be either +/- 1 in that
        case. In case the number of dimensions in the input array is
        greater than 2 then a stack of the matrices with above properties
        is returned.
    R : ndarray of float or complex, optional
        The upper-triangular matrix or a stack of upper-triangular
        matrices if the number of dimensions in the input array is greater
        than 2.
    (h, tau) : ndarrays of np.double or np.cdouble, optional
        The array h contains the Householder reflectors that generate q
        along with r. The tau array contains scaling factors for the
        reflectors. In the deprecated  'economic' mode only h is returned.

    Raises
    ------
    LinAlgError
        If factoring fails.

    See Also
    --------
    scipy.linalg.qr : Similar function in SciPy.
    scipy.linalg.rq : Compute RQ decomposition of a matrix.

    Notes
    -----
    This is an interface to the LAPACK routines ``dgeqrf``, ``zgeqrf``,
    ``dorgqr``, and ``zungqr``.

    For more information on the qr factorization, see for example:
    https://en.wikipedia.org/wiki/QR_factorization

    Subclasses of `ndarray` are preserved except for the 'raw' mode. So if
    `a` is of type `matrix`, all the return values will be matrices too.

    New 'reduced', 'complete', and 'raw' options for mode were added in
    NumPy 1.8.0 and the old option 'full' was made an alias of 'reduced'.  In
    addition the options 'full' and 'economic' were deprecated.  Because
    'full' was the previous default and 'reduced' is the new default,
    backward compatibility can be maintained by letting `mode` default.
    The 'raw' option was added so that LAPACK routines that can multiply
    arrays by q using the Householder reflectors can be used. Note that in
    this case the returned arrays are of type np.double or np.cdouble and
    the h array is transposed to be FORTRAN compatible.  No routines using
    the 'raw' return are currently exposed by numpy, but some are available
    in lapack_lite and just await the necessary work.

    Examples
    --------
    >>> import numpy as np
    >>> rng = np.random.default_rng()
    >>> a = rng.normal(size=(9, 6))
    >>> Q, R = np.linalg.qr(a)
    >>> np.allclose(a, np.dot(Q, R))  # a does equal QR
    True
    >>> R2 = np.linalg.qr(a, mode='r')
    >>> np.allclose(R, R2)  # mode='r' returns the same R as mode='full'
    True
    >>> a = np.random.normal(size=(3, 2, 2)) # Stack of 2 x 2 matrices as input
    >>> Q, R = np.linalg.qr(a)
    >>> Q.shape
    (3, 2, 2)
    >>> R.shape
    (3, 2, 2)
    >>> np.allclose(a, np.matmul(Q, R))
    True

    Example illustrating a common use of `qr`: solving of least squares
    problems

    What are the least-squares-best `m` and `y0` in ``y = y0 + mx`` for
    the following data: {(0,1), (1,0), (1,2), (2,1)}. (Graph the points
    and you'll see that it should be y0 = 0, m = 1.)  The answer is provided
    by solving the over-determined matrix equation ``Ax = b``, where::

      A = array([[0, 1], [1, 1], [1, 1], [2, 1]])
      x = array([[y0], [m]])
      b = array([[1], [0], [2], [1]])

    If A = QR such that Q is orthonormal (which is always possible via
    Gram-Schmidt), then ``x = inv(R) * (Q.T) * b``.  (In numpy practice,
    however, we simply use `lstsq`.)

    >>> A = np.array([[0, 1], [1, 1], [1, 1], [2, 1]])
    >>> A
    array([[0, 1],
           [1, 1],
           [1, 1],
           [2, 1]])
    >>> b = np.array([1, 2, 2, 3])
    >>> Q, R = np.linalg.qr(A)
    >>> p = np.dot(Q.T, b)
    >>> np.dot(np.linalg.inv(R), p)
    array([  1.,   1.])

    """
    if mode not in ('reduced', 'complete', 'r', 'raw'):
        if mode in ('f', 'full'):
            # 2013-04-01, 1.8
            msg = (
                "The 'full' option is deprecated in favor of 'reduced'.\n"
                "For backward compatibility let mode default."
            )
            warnings.warn(msg, DeprecationWarning, stacklevel=2)
            mode = 'reduced'
        elif mode in ('e', 'economic'):
            # 2013-04-01, 1.8
            msg = "The 'economic' option is deprecated."
            warnings.warn(msg, DeprecationWarning, stacklevel=2)
            mode = 'economic'
        else:
            raise ValueError(f"Unrecognized mode '{mode}'")

    a, wrap = _makearray(a)
    _assert_stacked_2d(a)
    m, n = a.shape[-2:]
    t, result_t = _commonType(a)
    a = a.astype(t, copy=True)
    a = _to_native_byte_order(a)
    mn = min(m, n)

    signature = 'D->D' if isComplexType(t) else 'd->d'
    with errstate(call=_raise_linalgerror_qr, invalid='call',
                  over='ignore', divide='ignore', under='ignore'):
        tau = _umath_linalg.qr_r_raw(a, signature=signature)

    # handle modes that don't return q
    if mode == 'r':
        r = triu(a[..., :mn, :])
        r = r.astype(result_t, copy=False)
        return wrap(r)

    if mode == 'raw':
        q = transpose(a)
        q = q.astype(result_t, copy=False)
        tau = tau.astype(result_t, copy=False)
        return wrap(q), tau

    if mode == 'economic':
        a = a.astype(result_t, copy=False)
        return wrap(a)

    # mc is the number of columns in the resulting q
    # matrix. If the mode is complete then it is
    # same as number of rows, and if the mode is reduced,
    # then it is the minimum of number of rows and columns.
    if mode == 'complete' and m > n:
        mc = m
        gufunc = _umath_linalg.qr_complete
    else:
        mc = mn
        gufunc = _umath_linalg.qr_reduced

    signature = 'DD->D' if isComplexType(t) else 'dd->d'
    with errstate(call=_raise_linalgerror_qr, invalid='call',
                  over='ignore', divide='ignore', under='ignore'):
        q = gufunc(a, tau, signature=signature)
    r = triu(a[..., :mc, :])

    q = q.astype(result_t, copy=False)
    r = r.astype(result_t, copy=False)

    return QRResult(wrap(q), wrap(r))

# Eigenvalues


@array_function_dispatch(_unary_dispatcher)
def eigvals(a):
    """
    Compute the eigenvalues of a general matrix.

    Main difference between `eigvals` and `eig`: the eigenvectors aren't
    returned.

    Parameters
    ----------
    a : (..., M, M) array_like
        A complex- or real-valued matrix whose eigenvalues will be computed.

    Returns
    -------
    w : (..., M,) ndarray
        The eigenvalues, each repeated according to its multiplicity.
        They are not necessarily ordered, nor are they necessarily
        real for real matrices.

    Raises
    ------
    LinAlgError
        If the eigenvalue computation does not converge.

    See Also
    --------
    eig : eigenvalues and right eigenvectors of general arrays
    eigvalsh : eigenvalues of real symmetric or complex Hermitian
               (conjugate symmetric) arrays.
    eigh : eigenvalues and eigenvectors of real symmetric or complex
           Hermitian (conjugate symmetric) arrays.
    scipy.linalg.eigvals : Similar function in SciPy.

    Notes
    -----
    Broadcasting rules apply, see the `numpy.linalg` documentation for
    details.

    This is implemented using the ``_geev`` LAPACK routines which compute
    the eigenvalues and eigenvectors of general square arrays.

    Examples
    --------
    Illustration, using the fact that the eigenvalues of a diagonal matrix
    are its diagonal elements, that multiplying a matrix on the left
    by an orthogonal matrix, `Q`, and on the right by `Q.T` (the transpose
    of `Q`), preserves the eigenvalues of the "middle" matrix. In other words,
    if `Q` is orthogonal, then ``Q * A * Q.T`` has the same eigenvalues as
    ``A``:

    >>> import numpy as np
    >>> from numpy import linalg as LA
    >>> x = np.random.random()
    >>> Q = np.array([[np.cos(x), -np.sin(x)], [np.sin(x), np.cos(x)]])
    >>> LA.norm(Q[0, :]), LA.norm(Q[1, :]), np.dot(Q[0, :],Q[1, :])
    (1.0, 1.0, 0.0)

    Now multiply a diagonal matrix by ``Q`` on one side and
    by ``Q.T`` on the other:

    >>> D = np.diag((-1,1))
    >>> LA.eigvals(D)
    array([-1.,  1.])
    >>> A = np.dot(Q, D)
    >>> A = np.dot(A, Q.T)
    >>> LA.eigvals(A)
    array([ 1., -1.]) # random

    """
    a, wrap = _makearray(a)
    _assert_stacked_square(a)
    _assert_finite(a)
    t, result_t = _commonType(a)

    signature = 'D->D' if isComplexType(t) else 'd->D'
    with errstate(call=_raise_linalgerror_eigenvalues_nonconvergence,
                  invalid='call', over='ignore', divide='ignore',
                  under='ignore'):
        w = _umath_linalg.eigvals(a, signature=signature)

    if not isComplexType(t):
        if all(w.imag == 0):
            w = w.real
            result_t = _realType(result_t)
        else:
            result_t = _complexType(result_t)

    return w.astype(result_t, copy=False)


def _eigvalsh_dispatcher(a, UPLO=None):
    return (a,)


@array_function_dispatch(_eigvalsh_dispatcher)
def eigvalsh(a, UPLO='L'):
    """
    Compute the eigenvalues of a complex Hermitian or real symmetric matrix.

    Main difference from eigh: the eigenvectors are not computed.

    Parameters
    ----------
    a : (..., M, M) array_like
        A complex- or real-valued matrix whose eigenvalues are to be
        computed.
    UPLO : {'L', 'U'}, optional
        Specifies whether the calculation is done with the lower triangular
        part of `a` ('L', default) or the upper triangular part ('U').
        Irrespective of this value only the real parts of the diagonal will
        be considered in the computation to preserve the notion of a Hermitian
        matrix. It therefore follows that the imaginary part of the diagonal
        will always be treated as zero.

    Returns
    -------
    w : (..., M,) ndarray
        The eigenvalues in ascending order, each repeated according to
        its multiplicity.

    Raises
    ------
    LinAlgError
        If the eigenvalue computation does not converge.

    See Also
    --------
    eigh : eigenvalues and eigenvectors of real symmetric or complex Hermitian
           (conjugate symmetric) arrays.
    eigvals : eigenvalues of general real or complex arrays.
    eig : eigenvalues and right eigenvectors of general real or complex
          arrays.
    scipy.linalg.eigvalsh : Similar function in SciPy.

    Notes
    -----
    Broadcasting rules apply, see the `numpy.linalg` documentation for
    details.

    The eigenvalues are computed using LAPACK routines ``_syevd``, ``_heevd``.

    Examples
    --------
    >>> import numpy as np
    >>> from numpy import linalg as LA
    >>> a = np.array([[1, -2j], [2j, 5]])
    >>> LA.eigvalsh(a)
    array([ 0.17157288,  5.82842712]) # may vary

    >>> # demonstrate the treatment of the imaginary part of the diagonal
    >>> a = np.array([[5+2j, 9-2j], [0+2j, 2-1j]])
    >>> a
    array([[5.+2.j, 9.-2.j],
           [0.+2.j, 2.-1.j]])
    >>> # with UPLO='L' this is numerically equivalent to using LA.eigvals()
    >>> # with:
    >>> b = np.array([[5.+0.j, 0.-2.j], [0.+2.j, 2.-0.j]])
    >>> b
    array([[5.+0.j, 0.-2.j],
           [0.+2.j, 2.+0.j]])
    >>> wa = LA.eigvalsh(a)
    >>> wb = LA.eigvals(b)
    >>> wa
    array([1., 6.])
    >>> wb
    array([6.+0.j, 1.+0.j])

    """
    UPLO = UPLO.upper()
    if UPLO not in ('L', 'U'):
        raise ValueError("UPLO argument must be 'L' or 'U'")

    if UPLO == 'L':
        gufunc = _umath_linalg.eigvalsh_lo
    else:
        gufunc = _umath_linalg.eigvalsh_up

    a, wrap = _makearray(a)
    _assert_stacked_square(a)
    t, result_t = _commonType(a)
    signature = 'D->d' if isComplexType(t) else 'd->d'
    with errstate(call=_raise_linalgerror_eigenvalues_nonconvergence,
                  invalid='call', over='ignore', divide='ignore',
                  under='ignore'):
        w = gufunc(a, signature=signature)
    return w.astype(_realType(result_t), copy=False)


# Eigenvectors


@array_function_dispatch(_unary_dispatcher)
def eig(a):
    """
    Compute the eigenvalues and right eigenvectors of a square array.

    Parameters
    ----------
    a : (..., M, M) array
        Matrices for which the eigenvalues and right eigenvectors will
        be computed

    Returns
    -------
    A namedtuple with the following attributes:

    eigenvalues : (..., M) array
        The eigenvalues, each repeated according to its multiplicity.
        The eigenvalues are not necessarily ordered. The resulting
        array will be of complex type, unless the imaginary part is
        zero in which case it will be cast to a real type. When `a`
        is real the resulting eigenvalues will be real (0 imaginary
        part) or occur in conjugate pairs

    eigenvectors : (..., M, M) array
        The normalized (unit "length") eigenvectors, such that the
        column ``eigenvectors[:,i]`` is the eigenvector corresponding to the
        eigenvalue ``eigenvalues[i]``.

    Raises
    ------
    LinAlgError
        If the eigenvalue computation does not converge.

    See Also
    --------
    eigvals : eigenvalues of a non-symmetric array.
    eigh : eigenvalues and eigenvectors of a real symmetric or complex
           Hermitian (conjugate symmetric) array.
    eigvalsh : eigenvalues of a real symmetric or complex Hermitian
               (conjugate symmetric) array.
    scipy.linalg.eig : Similar function in SciPy that also solves the
                       generalized eigenvalue problem.
    scipy.linalg.schur : Best choice for unitary and other non-Hermitian
                         normal matrices.

    Notes
    -----
    Broadcasting rules apply, see the `numpy.linalg` documentation for
    details.

    This is implemented using the ``_geev`` LAPACK routines which compute
    the eigenvalues and eigenvectors of general square arrays.

    The number `w` is an eigenvalue of `a` if there exists a vector `v` such
    that ``a @ v = w * v``. Thus, the arrays `a`, `eigenvalues`, and
    `eigenvectors` satisfy the equations ``a @ eigenvectors[:,i] =
    eigenvalues[i] * eigenvectors[:,i]`` for :math:`i \\in \\{0,...,M-1\\}`.

    The array `eigenvectors` may not be of maximum rank, that is, some of the
    columns may be linearly dependent, although round-off error may obscure
    that fact. If the eigenvalues are all different, then theoretically the
    eigenvectors are linearly independent and `a` can be diagonalized by a
    similarity transformation using `eigenvectors`, i.e, ``inv(eigenvectors) @
    a @ eigenvectors`` is diagonal.

    For non-Hermitian normal matrices the SciPy function `scipy.linalg.schur`
    is preferred because the matrix `eigenvectors` is guaranteed to be
    unitary, which is not the case when using `eig`. The Schur factorization
    produces an upper triangular matrix rather than a diagonal matrix, but for
    normal matrices only the diagonal of the upper triangular matrix is
    needed, the rest is roundoff error.

    Finally, it is emphasized that `eigenvectors` consists of the *right* (as
    in right-hand side) eigenvectors of `a`. A vector `y` satisfying ``y.T @ a
    = z * y.T`` for some number `z` is called a *left* eigenvector of `a`,
    and, in general, the left and right eigenvectors of a matrix are not
    necessarily the (perhaps conjugate) transposes of each other.

    References
    ----------
    G. Strang, *Linear Algebra and Its Applications*, 2nd Ed., Orlando, FL,
    Academic Press, Inc., 1980, Various pp.

    Examples
    --------
    >>> import numpy as np
    >>> from numpy import linalg as LA

    (Almost) trivial example with real eigenvalues and eigenvectors.

    >>> eigenvalues, eigenvectors = LA.eig(np.diag((1, 2, 3)))
    >>> eigenvalues
    array([1., 2., 3.])
    >>> eigenvectors
    array([[1., 0., 0.],
           [0., 1., 0.],
           [0., 0., 1.]])

    Real matrix possessing complex eigenvalues and eigenvectors;
    note that the eigenvalues are complex conjugates of each other.

    >>> eigenvalues, eigenvectors = LA.eig(np.array([[1, -1], [1, 1]]))
    >>> eigenvalues
    array([1.+1.j, 1.-1.j])
    >>> eigenvectors
    array([[0.70710678+0.j        , 0.70710678-0.j        ],
           [0.        -0.70710678j, 0.        +0.70710678j]])

    Complex-valued matrix with real eigenvalues (but complex-valued
    eigenvectors); note that ``a.conj().T == a``, i.e., `a` is Hermitian.

    >>> a = np.array([[1, 1j], [-1j, 1]])
    >>> eigenvalues, eigenvectors = LA.eig(a)
    >>> eigenvalues
    array([2.+0.j, 0.+0.j])
    >>> eigenvectors
    array([[ 0.        +0.70710678j,  0.70710678+0.j        ], # may vary
           [ 0.70710678+0.j        , -0.        +0.70710678j]])

    Be careful about round-off error!

    >>> a = np.array([[1 + 1e-9, 0], [0, 1 - 1e-9]])
    >>> # Theor. eigenvalues are 1 +/- 1e-9
    >>> eigenvalues, eigenvectors = LA.eig(a)
    >>> eigenvalues
    array([1., 1.])
    >>> eigenvectors
    array([[1., 0.],
           [0., 1.]])

    """
    a, wrap = _makearray(a)
    _assert_stacked_square(a)
    _assert_finite(a)
    t, result_t = _commonType(a)

    signature = 'D->DD' if isComplexType(t) else 'd->DD'
    with errstate(call=_raise_linalgerror_eigenvalues_nonconvergence,
                  invalid='call', over='ignore', divide='ignore',
                  under='ignore'):
        w, vt = _umath_linalg.eig(a, signature=signature)

    if not isComplexType(t) and all(w.imag == 0.0):
        w = w.real
        vt = vt.real
        result_t = _realType(result_t)
    else:
        result_t = _complexType(result_t)

    vt = vt.astype(result_t, copy=False)
    return EigResult(w.astype(result_t, copy=False), wrap(vt))


@array_function_dispatch(_eigvalsh_dispatcher)
def eigh(a, UPLO='L'):
    """
    Return the eigenvalues and eigenvectors of a complex Hermitian
    (conjugate symmetric) or a real symmetric matrix.

    Returns two objects, a 1-D array containing the eigenvalues of `a`, and
    a 2-D square array or matrix (depending on the input type) of the
    corresponding eigenvectors (in columns).

    Parameters
    ----------
    a : (..., M, M) array
        Hermitian or real symmetric matrices whose eigenvalues and
        eigenvectors are to be computed.
    UPLO : {'L', 'U'}, optional
        Specifies whether the calculation is done with the lower triangular
        part of `a` ('L', default) or the upper triangular part ('U').
        Irrespective of this value only the real parts of the diagonal will
        be considered in the computation to preserve the notion of a Hermitian
        matrix. It therefore follows that the imaginary part of the diagonal
        will always be treated as zero.

    Returns
    -------
    A namedtuple with the following attributes:

    eigenvalues : (..., M) ndarray
        The eigenvalues in ascending order, each repeated according to
        its multiplicity.
    eigenvectors : {(..., M, M) ndarray, (..., M, M) matrix}
        The column ``eigenvectors[:, i]`` is the normalized eigenvector
        corresponding to the eigenvalue ``eigenvalues[i]``.  Will return a
        matrix object if `a` is a matrix object.

    Raises
    ------
    LinAlgError
        If the eigenvalue computation does not converge.

    See Also
    --------
    eigvalsh : eigenvalues of real symmetric or complex Hermitian
               (conjugate symmetric) arrays.
    eig : eigenvalues and right eigenvectors for non-symmetric arrays.
    eigvals : eigenvalues of non-symmetric arrays.
    scipy.linalg.eigh : Similar function in SciPy (but also solves the
                        generalized eigenvalue problem).

    Notes
    -----
    Broadcasting rules apply, see the `numpy.linalg` documentation for
    details.

    The eigenvalues/eigenvectors are computed using LAPACK routines ``_syevd``,
    ``_heevd``.

    The eigenvalues of real symmetric or complex Hermitian matrices are always
    real. [1]_ The array `eigenvalues` of (column) eigenvectors is unitary and
    `a`, `eigenvalues`, and `eigenvectors` satisfy the equations ``dot(a,
    eigenvectors[:, i]) = eigenvalues[i] * eigenvectors[:, i]``.

    References
    ----------
    .. [1] G. Strang, *Linear Algebra and Its Applications*, 2nd Ed., Orlando,
           FL, Academic Press, Inc., 1980, pg. 222.

    Examples
    --------
    >>> import numpy as np
    >>> from numpy import linalg as LA
    >>> a = np.array([[1, -2j], [2j, 5]])
    >>> a
    array([[ 1.+0.j, -0.-2.j],
           [ 0.+2.j,  5.+0.j]])
    >>> eigenvalues, eigenvectors = LA.eigh(a)
    >>> eigenvalues
    array([0.17157288, 5.82842712])
    >>> eigenvectors
    array([[-0.92387953+0.j        , -0.38268343+0.j        ], # may vary
           [ 0.        +0.38268343j,  0.        -0.92387953j]])

    >>> (np.dot(a, eigenvectors[:, 0]) -
    ... eigenvalues[0] * eigenvectors[:, 0])  # verify 1st eigenval/vec pair
    array([5.55111512e-17+0.0000000e+00j, 0.00000000e+00+1.2490009e-16j])
    >>> (np.dot(a, eigenvectors[:, 1]) -
    ... eigenvalues[1] * eigenvectors[:, 1])  # verify 2nd eigenval/vec pair
    array([0.+0.j, 0.+0.j])

    >>> A = np.matrix(a) # what happens if input is a matrix object
    >>> A
    matrix([[ 1.+0.j, -0.-2.j],
            [ 0.+2.j,  5.+0.j]])
    >>> eigenvalues, eigenvectors = LA.eigh(A)
    >>> eigenvalues
    array([0.17157288, 5.82842712])
    >>> eigenvectors
    matrix([[-0.92387953+0.j        , -0.38268343+0.j        ], # may vary
            [ 0.        +0.38268343j,  0.        -0.92387953j]])

    >>> # demonstrate the treatment of the imaginary part of the diagonal
    >>> a = np.array([[5+2j, 9-2j], [0+2j, 2-1j]])
    >>> a
    array([[5.+2.j, 9.-2.j],
           [0.+2.j, 2.-1.j]])
    >>> # with UPLO='L' this is numerically equivalent to using LA.eig() with:
    >>> b = np.array([[5.+0.j, 0.-2.j], [0.+2.j, 2.-0.j]])
    >>> b
    array([[5.+0.j, 0.-2.j],
           [0.+2.j, 2.+0.j]])
    >>> wa, va = LA.eigh(a)
    >>> wb, vb = LA.eig(b)
    >>> wa
    array([1., 6.])
    >>> wb
    array([6.+0.j, 1.+0.j])
    >>> va
    array([[-0.4472136 +0.j        , -0.89442719+0.j        ], # may vary
           [ 0.        +0.89442719j,  0.        -0.4472136j ]])
    >>> vb
    array([[ 0.89442719+0.j       , -0.        +0.4472136j],
           [-0.        +0.4472136j,  0.89442719+0.j       ]])

    """
    UPLO = UPLO.upper()
    if UPLO not in ('L', 'U'):
        raise ValueError("UPLO argument must be 'L' or 'U'")

    a, wrap = _makearray(a)
    _assert_stacked_square(a)
    t, result_t = _commonType(a)

    if UPLO == 'L':
        gufunc = _umath_linalg.eigh_lo
    else:
        gufunc = _umath_linalg.eigh_up

    signature = 'D->dD' if isComplexType(t) else 'd->dd'
    with errstate(call=_raise_linalgerror_eigenvalues_nonconvergence,
                  invalid='call', over='ignore', divide='ignore',
                  under='ignore'):
        w, vt = gufunc(a, signature=signature)
    w = w.astype(_realType(result_t), copy=False)
    vt = vt.astype(result_t, copy=False)
    return EighResult(w, wrap(vt))


# Singular value decomposition

def _svd_dispatcher(a, full_matrices=None, compute_uv=None, hermitian=None):
    return (a,)


@array_function_dispatch(_svd_dispatcher)
def svd(a, full_matrices=True, compute_uv=True, hermitian=False):
    """
    Singular Value Decomposition.

    When `a` is a 2D array, and ``full_matrices=False``, then it is
    factorized as ``u @ np.diag(s) @ vh = (u * s) @ vh``, where
    `u` and the Hermitian transpose of `vh` are 2D arrays with
    orthonormal columns and `s` is a 1D array of `a`'s singular
    values. When `a` is higher-dimensional, SVD is applied in
    stacked mode as explained below.

    Parameters
    ----------
    a : (..., M, N) array_like
        A real or complex array with ``a.ndim >= 2``.
    full_matrices : bool, optional
        If True (default), `u` and `vh` have the shapes ``(..., M, M)`` and
        ``(..., N, N)``, respectively.  Otherwise, the shapes are
        ``(..., M, K)`` and ``(..., K, N)``, respectively, where
        ``K = min(M, N)``.
    compute_uv : bool, optional
        Whether or not to compute `u` and `vh` in addition to `s`.  True
        by default.
    hermitian : bool, optional
        If True, `a` is assumed to be Hermitian (symmetric if real-valued),
        enabling a more efficient method for finding singular values.
        Defaults to False.

    Returns
    -------
    When `compute_uv` is True, the result is a namedtuple with the following
    attribute names:

    U : { (..., M, M), (..., M, K) } array
        Unitary array(s). The first ``a.ndim - 2`` dimensions have the same
        size as those of the input `a`. The size of the last two dimensions
        depends on the value of `full_matrices`. Only returned when
        `compute_uv` is True.
    S : (..., K) array
        Vector(s) with the singular values, within each vector sorted in
        descending order. The first ``a.ndim - 2`` dimensions have the same
        size as those of the input `a`.
    Vh : { (..., N, N), (..., K, N) } array
        Unitary array(s). The first ``a.ndim - 2`` dimensions have the same
        size as those of the input `a`. The size of the last two dimensions
        depends on the value of `full_matrices`. Only returned when
        `compute_uv` is True.

    Raises
    ------
    LinAlgError
        If SVD computation does not converge.

    See Also
    --------
    scipy.linalg.svd : Similar function in SciPy.
    scipy.linalg.svdvals : Compute singular values of a matrix.

    Notes
    -----
    The decomposition is performed using LAPACK routine ``_gesdd``.

    SVD is usually described for the factorization of a 2D matrix :math:`A`.
    The higher-dimensional case will be discussed below. In the 2D case, SVD is
    written as :math:`A = U S V^H`, where :math:`A = a`, :math:`U= u`,
    :math:`S= \\mathtt{np.diag}(s)` and :math:`V^H = vh`. The 1D array `s`
    contains the singular values of `a` and `u` and `vh` are unitary. The rows
    of `vh` are the eigenvectors of :math:`A^H A` and the columns of `u` are
    the eigenvectors of :math:`A A^H`. In both cases the corresponding
    (possibly non-zero) eigenvalues are given by ``s**2``.

    If `a` has more than two dimensions, then broadcasting rules apply, as
    explained in :ref:`routines.linalg-broadcasting`. This means that SVD is
    working in "stacked" mode: it iterates over all indices of the first
    ``a.ndim - 2`` dimensions and for each combination SVD is applied to the
    last two indices. The matrix `a` can be reconstructed from the
    decomposition with either ``(u * s[..., None, :]) @ vh`` or
    ``u @ (s[..., None] * vh)``. (The ``@`` operator can be replaced by the
    function ``np.matmul`` for python versions below 3.5.)

    If `a` is a ``matrix`` object (as opposed to an ``ndarray``), then so are
    all the return values.

    Examples
    --------
    >>> import numpy as np
    >>> rng = np.random.default_rng()
    >>> a = rng.normal(size=(9, 6)) + 1j*rng.normal(size=(9, 6))
    >>> b = rng.normal(size=(2, 7, 8, 3)) + 1j*rng.normal(size=(2, 7, 8, 3))


    Reconstruction based on full SVD, 2D case:

    >>> U, S, Vh = np.linalg.svd(a, full_matrices=True)
    >>> U.shape, S.shape, Vh.shape
    ((9, 9), (6,), (6, 6))
    >>> np.allclose(a, np.dot(U[:, :6] * S, Vh))
    True
    >>> smat = np.zeros((9, 6), dtype=complex)
    >>> smat[:6, :6] = np.diag(S)
    >>> np.allclose(a, np.dot(U, np.dot(smat, Vh)))
    True

    Reconstruction based on reduced SVD, 2D case:

    >>> U, S, Vh = np.linalg.svd(a, full_matrices=False)
    >>> U.shape, S.shape, Vh.shape
    ((9, 6), (6,), (6, 6))
    >>> np.allclose(a, np.dot(U * S, Vh))
    True
    >>> smat = np.diag(S)
    >>> np.allclose(a, np.dot(U, np.dot(smat, Vh)))
    True

    Reconstruction based on full SVD, 4D case:

    >>> U, S, Vh = np.linalg.svd(b, full_matrices=True)
    >>> U.shape, S.shape, Vh.shape
    ((2, 7, 8, 8), (2, 7, 3), (2, 7, 3, 3))
    >>> np.allclose(b, np.matmul(U[..., :3] * S[..., None, :], Vh))
    True
    >>> np.allclose(b, np.matmul(U[..., :3], S[..., None] * Vh))
    True

    Reconstruction based on reduced SVD, 4D case:

    >>> U, S, Vh = np.linalg.svd(b, full_matrices=False)
    >>> U.shape, S.shape, Vh.shape
    ((2, 7, 8, 3), (2, 7, 3), (2, 7, 3, 3))
    >>> np.allclose(b, np.matmul(U * S[..., None, :], Vh))
    True
    >>> np.allclose(b, np.matmul(U, S[..., None] * Vh))
    True

    """
    import numpy as np
    a, wrap = _makearray(a)

    if hermitian:
        # note: lapack svd returns eigenvalues with s ** 2 sorted descending,
        # but eig returns s sorted ascending, so we re-order the eigenvalues
        # and related arrays to have the correct order
        if compute_uv:
            s, u = eigh(a)
            sgn = sign(s)
            s = abs(s)
            sidx = argsort(s)[..., ::-1]
            sgn = np.take_along_axis(sgn, sidx, axis=-1)
            s = np.take_along_axis(s, sidx, axis=-1)
            u = np.take_along_axis(u, sidx[..., None, :], axis=-1)
            # singular values are unsigned, move the sign into v
            vt = transpose(u * sgn[..., None, :]).conjugate()
            return SVDResult(wrap(u), s, wrap(vt))
        else:
            s = eigvalsh(a)
            s = abs(s)
            return sort(s)[..., ::-1]

    _assert_stacked_2d(a)
    t, result_t = _commonType(a)

    m, n = a.shape[-2:]
    if compute_uv:
        if full_matrices:
            gufunc = _umath_linalg.svd_f
        else:
            gufunc = _umath_linalg.svd_s

        signature = 'D->DdD' if isComplexType(t) else 'd->ddd'
        with errstate(call=_raise_linalgerror_svd_nonconvergence,
                      invalid='call', over='ignore', divide='ignore',
                      under='ignore'):
            u, s, vh = gufunc(a, signature=signature)
        u = u.astype(result_t, copy=False)
        s = s.astype(_realType(result_t), copy=False)
        vh = vh.astype(result_t, copy=False)
        return SVDResult(wrap(u), s, wrap(vh))
    else:
        signature = 'D->d' if isComplexType(t) else 'd->d'
        with errstate(call=_raise_linalgerror_svd_nonconvergence,
                      invalid='call', over='ignore', divide='ignore',
                      under='ignore'):
            s = _umath_linalg.svd(a, signature=signature)
        s = s.astype(_realType(result_t), copy=False)
        return s


def _svdvals_dispatcher(x):
    return (x,)


@array_function_dispatch(_svdvals_dispatcher)
def svdvals(x, /):
    """
    Returns the singular values of a matrix (or a stack of matrices) ``x``.
    When x is a stack of matrices, the function will compute the singular
    values for each matrix in the stack.

    This function is Array API compatible.

    Calling ``np.svdvals(x)`` to get singular values is the same as
    ``np.svd(x, compute_uv=False, hermitian=False)``.

    Parameters
    ----------
    x : (..., M, N) array_like
        Input array having shape (..., M, N) and whose last two
        dimensions form matrices on which to perform singular value
        decomposition. Should have a floating-point data type.

    Returns
    -------
    out : ndarray
        An array with shape (..., K) that contains the vector(s)
        of singular values of length K, where K = min(M, N).

    See Also
    --------
    scipy.linalg.svdvals : Compute singular values of a matrix.

    Examples
    --------

    >>> np.linalg.svdvals([[1, 2, 3, 4, 5],
    ...                    [1, 4, 9, 16, 25],
    ...                    [1, 8, 27, 64, 125]])
    array([146.68862757,   5.57510612,   0.60393245])

    Determine the rank of a matrix using singular values:

    >>> s = np.linalg.svdvals([[1, 2, 3],
    ...                        [2, 4, 6],
    ...                        [-1, 1, -1]]); s
    array([8.38434191e+00, 1.64402274e+00, 2.31534378e-16])
    >>> np.count_nonzero(s > 1e-10)  # Matrix of rank 2
    2

    """
    return svd(x, compute_uv=False, hermitian=False)


def _cond_dispatcher(x, p=None):
    return (x,)


@array_function_dispatch(_cond_dispatcher)
def cond(x, p=None):
    """
    Compute the condition number of a matrix.

    This function is capable of returning the condition number using
    one of seven different norms, depending on the value of `p` (see
    Parameters below).

    Parameters
    ----------
    x : (..., M, N) array_like
        The matrix whose condition number is sought.
    p : {None, 1, -1, 2, -2, inf, -inf, 'fro'}, optional
        Order of the norm used in the condition number computation:

        =====  ============================
        p      norm for matrices
        =====  ============================
        None   2-norm, computed directly using the ``SVD``
        'fro'  Frobenius norm
        inf    max(sum(abs(x), axis=1))
        -inf   min(sum(abs(x), axis=1))
        1      max(sum(abs(x), axis=0))
        -1     min(sum(abs(x), axis=0))
        2      2-norm (largest sing. value)
        -2     smallest singular value
        =====  ============================

        inf means the `numpy.inf` object, and the Frobenius norm is
        the root-of-sum-of-squares norm.

    Returns
    -------
    c : {float, inf}
        The condition number of the matrix. May be infinite.

    See Also
    --------
    numpy.linalg.norm

    Notes
    -----
    The condition number of `x` is defined as the norm of `x` times the
    norm of the inverse of `x` [1]_; the norm can be the usual L2-norm
    (root-of-sum-of-squares) or one of a number of other matrix norms.

    References
    ----------
    .. [1] G. Strang, *Linear Algebra and Its Applications*, Orlando, FL,
           Academic Press, Inc., 1980, pg. 285.

    Examples
    --------
    >>> import numpy as np
    >>> from numpy import linalg as LA
    >>> a = np.array([[1, 0, -1], [0, 1, 0], [1, 0, 1]])
    >>> a
    array([[ 1,  0, -1],
           [ 0,  1,  0],
           [ 1,  0,  1]])
    >>> LA.cond(a)
    1.4142135623730951
    >>> LA.cond(a, 'fro')
    3.1622776601683795
    >>> LA.cond(a, np.inf)
    2.0
    >>> LA.cond(a, -np.inf)
    1.0
    >>> LA.cond(a, 1)
    2.0
    >>> LA.cond(a, -1)
    1.0
    >>> LA.cond(a, 2)
    1.4142135623730951
    >>> LA.cond(a, -2)
    0.70710678118654746 # may vary
    >>> (min(LA.svd(a, compute_uv=False)) *
    ... min(LA.svd(LA.inv(a), compute_uv=False)))
    0.70710678118654746 # may vary

    """
    x = asarray(x)  # in case we have a matrix
    if _is_empty_2d(x):
        raise LinAlgError("cond is not defined on empty arrays")
    if p is None or p in {2, -2}:
        s = svd(x, compute_uv=False)
        with errstate(all='ignore'):
            if p == -2:
                r = s[..., -1] / s[..., 0]
            else:
                r = s[..., 0] / s[..., -1]
    else:
        # Call inv(x) ignoring errors. The result array will
        # contain nans in the entries where inversion failed.
        _assert_stacked_square(x)
        t, result_t = _commonType(x)
        signature = 'D->D' if isComplexType(t) else 'd->d'
        with errstate(all='ignore'):
            invx = _umath_linalg.inv(x, signature=signature)
            r = norm(x, p, axis=(-2, -1)) * norm(invx, p, axis=(-2, -1))
        r = r.astype(result_t, copy=False)

    # Convert nans to infs unless the original array had nan entries
    r = asarray(r)
    nan_mask = isnan(r)
    if nan_mask.any():
        nan_mask &= ~isnan(x).any(axis=(-2, -1))
        if r.ndim > 0:
            r[nan_mask] = inf
        elif nan_mask:
            r[()] = inf

    # Convention is to return scalars instead of 0d arrays
    if r.ndim == 0:
        r = r[()]

    return r


def _matrix_rank_dispatcher(A, tol=None, hermitian=None, *, rtol=None):
    return (A,)


@array_function_dispatch(_matrix_rank_dispatcher)
def matrix_rank(A, tol=None, hermitian=False, *, rtol=None):
    """
    Return matrix rank of array using SVD method

    Rank of the array is the number of singular values of the array that are
    greater than `tol`.

    Parameters
    ----------
    A : {(M,), (..., M, N)} array_like
        Input vector or stack of matrices.
    tol : (...) array_like, float, optional
        Threshold below which SVD values are considered zero. If `tol` is
        None, and ``S`` is an array with singular values for `M`, and
        ``eps`` is the epsilon value for datatype of ``S``, then `tol` is
        set to ``S.max() * max(M, N) * eps``.
    hermitian : bool, optional
        If True, `A` is assumed to be Hermitian (symmetric if real-valued),
        enabling a more efficient method for finding singular values.
        Defaults to False.
    rtol : (...) array_like, float, optional
        Parameter for the relative tolerance component. Only ``tol`` or
        ``rtol`` can be set at a time. Defaults to ``max(M, N) * eps``.

        .. versionadded:: 2.0.0

    Returns
    -------
    rank : (...) array_like
        Rank of A.

    Notes
    -----
    The default threshold to detect rank deficiency is a test on the magnitude
    of the singular values of `A`.  By default, we identify singular values
    less than ``S.max() * max(M, N) * eps`` as indicating rank deficiency
    (with the symbols defined above). This is the algorithm MATLAB uses [1].
    It also appears in *Numerical recipes* in the discussion of SVD solutions
    for linear least squares [2].

    This default threshold is designed to detect rank deficiency accounting
    for the numerical errors of the SVD computation. Imagine that there
    is a column in `A` that is an exact (in floating point) linear combination
    of other columns in `A`. Computing the SVD on `A` will not produce
    a singular value exactly equal to 0 in general: any difference of
    the smallest SVD value from 0 will be caused by numerical imprecision
    in the calculation of the SVD. Our threshold for small SVD values takes
    this numerical imprecision into account, and the default threshold will
    detect such numerical rank deficiency. The threshold may declare a matrix
    `A` rank deficient even if the linear combination of some columns of `A`
    is not exactly equal to another column of `A` but only numerically very
    close to another column of `A`.

    We chose our default threshold because it is in wide use. Other thresholds
    are possible.  For example, elsewhere in the 2007 edition of *Numerical
    recipes* there is an alternative threshold of ``S.max() *
    np.finfo(A.dtype).eps / 2. * np.sqrt(m + n + 1.)``. The authors describe
    this threshold as being based on "expected roundoff error" (p 71).

    The thresholds above deal with floating point roundoff error in the
    calculation of the SVD.  However, you may have more information about
    the sources of error in `A` that would make you consider other tolerance
    values to detect *effective* rank deficiency. The most useful measure
    of the tolerance depends on the operations you intend to use on your
    matrix. For example, if your data come from uncertain measurements with
    uncertainties greater than floating point epsilon, choosing a tolerance
    near that uncertainty may be preferable. The tolerance may be absolute
    if the uncertainties are absolute rather than relative.

    References
    ----------
    .. [1] MATLAB reference documentation, "Rank"
           https://www.mathworks.com/help/techdoc/ref/rank.html
    .. [2] W. H. Press, S. A. Teukolsky, W. T. Vetterling and B. P. Flannery,
           "Numerical Recipes (3rd edition)", Cambridge University Press, 2007,
           page 795.

    Examples
    --------
    >>> import numpy as np
    >>> from numpy.linalg import matrix_rank
    >>> matrix_rank(np.eye(4)) # Full rank matrix
    4
    >>> I=np.eye(4); I[-1,-1] = 0. # rank deficient matrix
    >>> matrix_rank(I)
    3
    >>> matrix_rank(np.ones((4,))) # 1 dimension - rank 1 unless all 0
    1
    >>> matrix_rank(np.zeros((4,)))
    0
    """
    if rtol is not None and tol is not None:
        raise ValueError("`tol` and `rtol` can't be both set.")

    A = asarray(A)
    if A.ndim < 2:
        return int(not all(A == 0))
    S = svd(A, compute_uv=False, hermitian=hermitian)

    if tol is None:
        if rtol is None:
            rtol = max(A.shape[-2:]) * finfo(S.dtype).eps
        else:
            rtol = asarray(rtol)[..., newaxis]
        tol = S.max(axis=-1, keepdims=True) * rtol
    else:
        tol = asarray(tol)[..., newaxis]

    return count_nonzero(S > tol, axis=-1)


# Generalized inverse

def _pinv_dispatcher(a, rcond=None, hermitian=None, *, rtol=None):
    return (a,)


@array_function_dispatch(_pinv_dispatcher)
def pinv(a, rcond=None, hermitian=False, *, rtol=_NoValue):
    """
    Compute the (Moore-Penrose) pseudo-inverse of a matrix.

    Calculate the generalized inverse of a matrix using its
    singular-value decomposition (SVD) and including all
    *large* singular values.

    Parameters
    ----------
    a : (..., M, N) array_like
        Matrix or stack of matrices to be pseudo-inverted.
    rcond : (...) array_like of float, optional
        Cutoff for small singular values.
        Singular values less than or equal to
        ``rcond * largest_singular_value`` are set to zero.
        Broadcasts against the stack of matrices. Default: ``1e-15``.
    hermitian : bool, optional
        If True, `a` is assumed to be Hermitian (symmetric if real-valued),
        enabling a more efficient method for finding singular values.
        Defaults to False.
    rtol : (...) array_like of float, optional
        Same as `rcond`, but it's an Array API compatible parameter name.
        Only `rcond` or `rtol` can be set at a time. If none of them are
        provided then NumPy's ``1e-15`` default is used. If ``rtol=None``
        is passed then the API standard default is used.

        .. versionadded:: 2.0.0

    Returns
    -------
    B : (..., N, M) ndarray
        The pseudo-inverse of `a`. If `a` is a `matrix` instance, then so
        is `B`.

    Raises
    ------
    LinAlgError
        If the SVD computation does not converge.

    See Also
    --------
    scipy.linalg.pinv : Similar function in SciPy.
    scipy.linalg.pinvh : Compute the (Moore-Penrose) pseudo-inverse of a
                         Hermitian matrix.

    Notes
    -----
    The pseudo-inverse of a matrix A, denoted :math:`A^+`, is
    defined as: "the matrix that 'solves' [the least-squares problem]
    :math:`Ax = b`," i.e., if :math:`\\bar{x}` is said solution, then
    :math:`A^+` is that matrix such that :math:`\\bar{x} = A^+b`.

    It can be shown that if :math:`Q_1 \\Sigma Q_2^T = A` is the singular
    value decomposition of A, then
    :math:`A^+ = Q_2 \\Sigma^+ Q_1^T`, where :math:`Q_{1,2}` are
    orthogonal matrices, :math:`\\Sigma` is a diagonal matrix consisting
    of A's so-called singular values, (followed, typically, by
    zeros), and then :math:`\\Sigma^+` is simply the diagonal matrix
    consisting of the reciprocals of A's singular values
    (again, followed by zeros). [1]_

    References
    ----------
    .. [1] G. Strang, *Linear Algebra and Its Applications*, 2nd Ed., Orlando,
           FL, Academic Press, Inc., 1980, pp. 139-142.

    Examples
    --------
    The following example checks that ``a * a+ * a == a`` and
    ``a+ * a * a+ == a+``:

    >>> import numpy as np
    >>> rng = np.random.default_rng()
    >>> a = rng.normal(size=(9, 6))
    >>> B = np.linalg.pinv(a)
    >>> np.allclose(a, np.dot(a, np.dot(B, a)))
    True
    >>> np.allclose(B, np.dot(B, np.dot(a, B)))
    True

    """
    a, wrap = _makearray(a)
    if rcond is None:
        if rtol is _NoValue:
            rcond = 1e-15
        elif rtol is None:
            rcond = max(a.shape[-2:]) * finfo(a.dtype).eps
        else:
            rcond = rtol
    elif rtol is not _NoValue:
        raise ValueError("`rtol` and `rcond` can't be both set.")
    else:
        # NOTE: Deprecate `rcond` in a few versions.
        pass

    rcond = asarray(rcond)
    if _is_empty_2d(a):
        m, n = a.shape[-2:]
        res = empty(a.shape[:-2] + (n, m), dtype=a.dtype)
        return wrap(res)
    a = a.conjugate()
    u, s, vt = svd(a, full_matrices=False, hermitian=hermitian)

    # discard small singular values
    cutoff = rcond[..., newaxis] * amax(s, axis=-1, keepdims=True)
    large = s > cutoff
    s = divide(1, s, where=large, out=s)
    s[~large] = 0

    res = matmul(transpose(vt), multiply(s[..., newaxis], transpose(u)))
    return wrap(res)


# Determinant


@array_function_dispatch(_unary_dispatcher)
def slogdet(a):
    """
    Compute the sign and (natural) logarithm of the determinant of an array.

    If an array has a very small or very large determinant, then a call to
    `det` may overflow or underflow. This routine is more robust against such
    issues, because it computes the logarithm of the determinant rather than
    the determinant itself.

    Parameters
    ----------
    a : (..., M, M) array_like
        Input array, has to be a square 2-D array.

    Returns
    -------
    A namedtuple with the following attributes:

    sign : (...) array_like
        A number representing the sign of the determinant. For a real matrix,
        this is 1, 0, or -1. For a complex matrix, this is a complex number
        with absolute value 1 (i.e., it is on the unit circle), or else 0.
    logabsdet : (...) array_like
        The natural log of the absolute value of the determinant.

    If the determinant is zero, then `sign` will be 0 and `logabsdet`
    will be -inf. In all cases, the determinant is equal to
    ``sign * np.exp(logabsdet)``.

    See Also
    --------
    det

    Notes
    -----
    Broadcasting rules apply, see the `numpy.linalg` documentation for
    details.

    The determinant is computed via LU factorization using the LAPACK
    routine ``z/dgetrf``.

    Examples
    --------
    The determinant of a 2-D array ``[[a, b], [c, d]]`` is ``ad - bc``:

    >>> import numpy as np
    >>> a = np.array([[1, 2], [3, 4]])
    >>> (sign, logabsdet) = np.linalg.slogdet(a)
    >>> (sign, logabsdet)
    (-1, 0.69314718055994529) # may vary
    >>> sign * np.exp(logabsdet)
    -2.0

    Computing log-determinants for a stack of matrices:

    >>> a = np.array([ [[1, 2], [3, 4]], [[1, 2], [2, 1]], [[1, 3], [3, 1]] ])
    >>> a.shape
    (3, 2, 2)
    >>> sign, logabsdet = np.linalg.slogdet(a)
    >>> (sign, logabsdet)
    (array([-1., -1., -1.]), array([ 0.69314718,  1.09861229,  2.07944154]))
    >>> sign * np.exp(logabsdet)
    array([-2., -3., -8.])

    This routine succeeds where ordinary `det` does not:

    >>> np.linalg.det(np.eye(500) * 0.1)
    0.0
    >>> np.linalg.slogdet(np.eye(500) * 0.1)
    (1, -1151.2925464970228)

    """
    a = asarray(a)
    _assert_stacked_square(a)
    t, result_t = _commonType(a)
    real_t = _realType(result_t)
    signature = 'D->Dd' if isComplexType(t) else 'd->dd'
    sign, logdet = _umath_linalg.slogdet(a, signature=signature)
    sign = sign.astype(result_t, copy=False)
    logdet = logdet.astype(real_t, copy=False)
    return SlogdetResult(sign, logdet)


@array_function_dispatch(_unary_dispatcher)
def det(a):
    """
    Compute the determinant of an array.

    Parameters
    ----------
    a : (..., M, M) array_like
        Input array to compute determinants for.

    Returns
    -------
    det : (...) array_like
        Determinant of `a`.

    See Also
    --------
    slogdet : Another way to represent the determinant, more suitable
      for large matrices where underflow/overflow may occur.
    scipy.linalg.det : Similar function in SciPy.

    Notes
    -----
    Broadcasting rules apply, see the `numpy.linalg` documentation for
    details.

    The determinant is computed via LU factorization using the LAPACK
    routine ``z/dgetrf``.

    Examples
    --------
    The determinant of a 2-D array [[a, b], [c, d]] is ad - bc:

    >>> import numpy as np
    >>> a = np.array([[1, 2], [3, 4]])
    >>> np.linalg.det(a)
    -2.0 # may vary

    Computing determinants for a stack of matrices:

    >>> a = np.array([ [[1, 2], [3, 4]], [[1, 2], [2, 1]], [[1, 3], [3, 1]] ])
    >>> a.shape
    (3, 2, 2)
    >>> np.linalg.det(a)
    array([-2., -3., -8.])

    """
    a = asarray(a)
    _assert_stacked_square(a)
    t, result_t = _commonType(a)
    signature = 'D->D' if isComplexType(t) else 'd->d'
    r = _umath_linalg.det(a, signature=signature)
    r = r.astype(result_t, copy=False)
    return r


# Linear Least Squares

def _lstsq_dispatcher(a, b, rcond=None):
    return (a, b)


@array_function_dispatch(_lstsq_dispatcher)
def lstsq(a, b, rcond=None):
    r"""
    Return the least-squares solution to a linear matrix equation.

    Computes the vector `x` that approximately solves the equation
    ``a @ x = b``. The equation may be under-, well-, or over-determined
    (i.e., the number of linearly independent rows of `a` can be less than,
    equal to, or greater than its number of linearly independent columns).
    If `a` is square and of full rank, then `x` (but for round-off error)
    is the "exact" solution of the equation. Else, `x` minimizes the
    Euclidean 2-norm :math:`||b - ax||`. If there are multiple minimizing
    solutions, the one with the smallest 2-norm :math:`||x||` is returned.

    Parameters
    ----------
    a : (M, N) array_like
        "Coefficient" matrix.
    b : {(M,), (M, K)} array_like
        Ordinate or "dependent variable" values. If `b` is two-dimensional,
        the least-squares solution is calculated for each of the `K` columns
        of `b`.
    rcond : float, optional
        Cut-off ratio for small singular values of `a`.
        For the purposes of rank determination, singular values are treated
        as zero if they are smaller than `rcond` times the largest singular
        value of `a`.
        The default uses the machine precision times ``max(M, N)``.  Passing
        ``-1`` will use machine precision.

        .. versionchanged:: 2.0
            Previously, the default was ``-1``, but a warning was given that
            this would change.

    Returns
    -------
    x : {(N,), (N, K)} ndarray
        Least-squares solution. If `b` is two-dimensional,
        the solutions are in the `K` columns of `x`.
    residuals : {(1,), (K,), (0,)} ndarray
        Sums of squared residuals: Squared Euclidean 2-norm for each column in
        ``b - a @ x``.
        If the rank of `a` is < N or M <= N, this is an empty array.
        If `b` is 1-dimensional, this is a (1,) shape array.
        Otherwise the shape is (K,).
    rank : int
        Rank of matrix `a`.
    s : (min(M, N),) ndarray
        Singular values of `a`.

    Raises
    ------
    LinAlgError
        If computation does not converge.

    See Also
    --------
    scipy.linalg.lstsq : Similar function in SciPy.

    Notes
    -----
    If `b` is a matrix, then all array results are returned as matrices.

    Examples
    --------
    Fit a line, ``y = mx + c``, through some noisy data-points:

    >>> import numpy as np
    >>> x = np.array([0, 1, 2, 3])
    >>> y = np.array([-1, 0.2, 0.9, 2.1])

    By examining the coefficients, we see that the line should have a
    gradient of roughly 1 and cut the y-axis at, more or less, -1.

    We can rewrite the line equation as ``y = Ap``, where ``A = [[x 1]]``
    and ``p = [[m], [c]]``.  Now use `lstsq` to solve for `p`:

    >>> A = np.vstack([x, np.ones(len(x))]).T
    >>> A
    array([[ 0.,  1.],
           [ 1.,  1.],
           [ 2.,  1.],
           [ 3.,  1.]])

    >>> m, c = np.linalg.lstsq(A, y)[0]
    >>> m, c
    (1.0 -0.95) # may vary

    Plot the data along with the fitted line:

    >>> import matplotlib.pyplot as plt
    >>> _ = plt.plot(x, y, 'o', label='Original data', markersize=10)
    >>> _ = plt.plot(x, m*x + c, 'r', label='Fitted line')
    >>> _ = plt.legend()
    >>> plt.show()

    """
    a, _ = _makearray(a)
    b, wrap = _makearray(b)
    is_1d = b.ndim == 1
    if is_1d:
        b = b[:, newaxis]
    _assert_2d(a, b)
    m, n = a.shape[-2:]
    m2, n_rhs = b.shape[-2:]
    if m != m2:
        raise LinAlgError('Incompatible dimensions')

    t, result_t = _commonType(a, b)
    result_real_t = _realType(result_t)

    if rcond is None:
        rcond = finfo(t).eps * max(n, m)

    signature = 'DDd->Ddid' if isComplexType(t) else 'ddd->ddid'
    if n_rhs == 0:
        # lapack can't handle n_rhs = 0 - so allocate
        # the array one larger in that axis
        b = zeros(b.shape[:-2] + (m, n_rhs + 1), dtype=b.dtype)

    with errstate(call=_raise_linalgerror_lstsq, invalid='call',
                  over='ignore', divide='ignore', under='ignore'):
        x, resids, rank, s = _umath_linalg.lstsq(a, b, rcond,
                                                 signature=signature)
    if m == 0:
        x[...] = 0
    if n_rhs == 0:
        # remove the item we added
        x = x[..., :n_rhs]
        resids = resids[..., :n_rhs]

    # remove the axis we added
    if is_1d:
        x = x.squeeze(axis=-1)
        # we probably should squeeze resids too, but we can't
        # without breaking compatibility.

    # as documented
    if rank != n or m <= n:
        resids = array([], result_real_t)

    # coerce output arrays
    s = s.astype(result_real_t, copy=False)
    resids = resids.astype(result_real_t, copy=False)
    # Copying lets the memory in r_parts be freed
    x = x.astype(result_t, copy=True)
    return wrap(x), wrap(resids), rank, s


def _multi_svd_norm(x, row_axis, col_axis, op, initial=None):
    """Compute a function of the singular values of the 2-D matrices in `x`.

    This is a private utility function used by `numpy.linalg.norm()`.

    Parameters
    ----------
    x : ndarray
    row_axis, col_axis : int
        The axes of `x` that hold the 2-D matrices.
    op : callable
        This should be either numpy.amin or `numpy.amax` or `numpy.sum`.

    Returns
    -------
    result : float or ndarray
        If `x` is 2-D, the return values is a float.
        Otherwise, it is an array with ``x.ndim - 2`` dimensions.
        The return values are either the minimum or maximum or sum of the
        singular values of the matrices, depending on whether `op`
        is `numpy.amin` or `numpy.amax` or `numpy.sum`.

    """
    y = moveaxis(x, (row_axis, col_axis), (-2, -1))
    result = op(svd(y, compute_uv=False), axis=-1, initial=initial)
    return result


def _norm_dispatcher(x, ord=None, axis=None, keepdims=None):
    return (x,)


@array_function_dispatch(_norm_dispatcher)
def norm(x, ord=None, axis=None, keepdims=False):
    """
    Matrix or vector norm.

    This function is able to return one of eight different matrix norms,
    or one of an infinite number of vector norms (described below), depending
    on the value of the ``ord`` parameter.

    Parameters
    ----------
    x : array_like
        Input array.  If `axis` is None, `x` must be 1-D or 2-D, unless `ord`
        is None. If both `axis` and `ord` are None, the 2-norm of
        ``x.ravel`` will be returned.
    ord : {int, float, inf, -inf, 'fro', 'nuc'}, optional
        Order of the norm (see table under ``Notes`` for what values are
        supported for matrices and vectors respectively). inf means numpy's
        `inf` object. The default is None.
    axis : {None, int, 2-tuple of ints}, optional.
        If `axis` is an integer, it specifies the axis of `x` along which to
        compute the vector norms.  If `axis` is a 2-tuple, it specifies the
        axes that hold 2-D matrices, and the matrix norms of these matrices
        are computed.  If `axis` is None then either a vector norm (when `x`
        is 1-D) or a matrix norm (when `x` is 2-D) is returned. The default
        is None.

    keepdims : bool, optional
        If this is set to True, the axes which are normed over are left in the
        result as dimensions with size one.  With this option the result will
        broadcast correctly against the original `x`.

    Returns
    -------
    n : float or ndarray
        Norm of the matrix or vector(s).

    See Also
    --------
    scipy.linalg.norm : Similar function in SciPy.

    Notes
    -----
    For values of ``ord < 1``, the result is, strictly speaking, not a
    mathematical 'norm', but it may still be useful for various numerical
    purposes.

    The following norms can be calculated:

    =====  ============================  ==========================
    ord    norm for matrices             norm for vectors
    =====  ============================  ==========================
    None   Frobenius norm                2-norm
    'fro'  Frobenius norm                --
    'nuc'  nuclear norm                  --
    inf    max(sum(abs(x), axis=1))      max(abs(x))
    -inf   min(sum(abs(x), axis=1))      min(abs(x))
    0      --                            sum(x != 0)
    1      max(sum(abs(x), axis=0))      as below
    -1     min(sum(abs(x), axis=0))      as below
    2      2-norm (largest sing. value)  as below
    -2     smallest singular value       as below
    other  --                            sum(abs(x)**ord)**(1./ord)
    =====  ============================  ==========================

    The Frobenius norm is given by [1]_:

    :math:`||A||_F = [\\sum_{i,j} abs(a_{i,j})^2]^{1/2}`

    The nuclear norm is the sum of the singular values.

    Both the Frobenius and nuclear norm orders are only defined for
    matrices and raise a ValueError when ``x.ndim != 2``.

    References
    ----------
    .. [1] G. H. Golub and C. F. Van Loan, *Matrix Computations*,
           Baltimore, MD, Johns Hopkins University Press, 1985, pg. 15

    Examples
    --------

    >>> import numpy as np
    >>> from numpy import linalg as LA
    >>> a = np.arange(9) - 4
    >>> a
    array([-4, -3, -2, ...,  2,  3,  4])
    >>> b = a.reshape((3, 3))
    >>> b
    array([[-4, -3, -2],
           [-1,  0,  1],
           [ 2,  3,  4]])

    >>> LA.norm(a)
    7.745966692414834
    >>> LA.norm(b)
    7.745966692414834
    >>> LA.norm(b, 'fro')
    7.745966692414834
    >>> LA.norm(a, np.inf)
    4.0
    >>> LA.norm(b, np.inf)
    9.0
    >>> LA.norm(a, -np.inf)
    0.0
    >>> LA.norm(b, -np.inf)
    2.0

    >>> LA.norm(a, 1)
    20.0
    >>> LA.norm(b, 1)
    7.0
    >>> LA.norm(a, -1)
    -4.6566128774142013e-010
    >>> LA.norm(b, -1)
    6.0
    >>> LA.norm(a, 2)
    7.745966692414834
    >>> LA.norm(b, 2)
    7.3484692283495345

    >>> LA.norm(a, -2)
    0.0
    >>> LA.norm(b, -2)
    1.8570331885190563e-016 # may vary
    >>> LA.norm(a, 3)
    5.8480354764257312 # may vary
    >>> LA.norm(a, -3)
    0.0

    Using the `axis` argument to compute vector norms:

    >>> c = np.array([[ 1, 2, 3],
    ...               [-1, 1, 4]])
    >>> LA.norm(c, axis=0)
    array([ 1.41421356,  2.23606798,  5.        ])
    >>> LA.norm(c, axis=1)
    array([ 3.74165739,  4.24264069])
    >>> LA.norm(c, ord=1, axis=1)
    array([ 6.,  6.])

    Using the `axis` argument to compute matrix norms:

    >>> m = np.arange(8).reshape(2,2,2)
    >>> LA.norm(m, axis=(1,2))
    array([  3.74165739,  11.22497216])
    >>> LA.norm(m[0, :, :]), LA.norm(m[1, :, :])
    (3.7416573867739413, 11.224972160321824)

    """
    x = asarray(x)

    if not issubclass(x.dtype.type, (inexact, object_)):
        x = x.astype(float)

    # Immediately handle some default, simple, fast, and common cases.
    if axis is None:
        ndim = x.ndim
        if (
            (ord is None) or
            (ord in ('f', 'fro') and ndim == 2) or
            (ord == 2 and ndim == 1)
        ):
            x = x.ravel(order='K')
            if isComplexType(x.dtype.type):
                x_real = x.real
                x_imag = x.imag
                sqnorm = x_real.dot(x_real) + x_imag.dot(x_imag)
            else:
                sqnorm = x.dot(x)
            ret = sqrt(sqnorm)
            if keepdims:
                ret = ret.reshape(ndim * [1])
            return ret

    # Normalize the `axis` argument to a tuple.
    nd = x.ndim
    if axis is None:
        axis = tuple(range(nd))
    elif not isinstance(axis, tuple):
        try:
            axis = int(axis)
        except Exception as e:
            raise TypeError(
                "'axis' must be None, an integer or a tuple of integers"
            ) from e
        axis = (axis,)

    if len(axis) == 1:
        if ord == inf:
            return abs(x).max(axis=axis, keepdims=keepdims, initial=0)
        elif ord == -inf:
            return abs(x).min(axis=axis, keepdims=keepdims)
        elif ord == 0:
            # Zero norm
            return (
                (x != 0)
                .astype(x.real.dtype)
                .sum(axis=axis, keepdims=keepdims)
            )
        elif ord == 1:
            # special case for speedup
            return add.reduce(abs(x), axis=axis, keepdims=keepdims)
        elif ord is None or ord == 2:
            # special case for speedup
            s = (x.conj() * x).real
            return sqrt(add.reduce(s, axis=axis, keepdims=keepdims))
        # None of the str-type keywords for ord ('fro', 'nuc')
        # are valid for vectors
        elif isinstance(ord, str):
            raise ValueError(f"Invalid norm order '{ord}' for vectors")
        else:
            absx = abs(x)
            absx **= ord
            ret = add.reduce(absx, axis=axis, keepdims=keepdims)
            ret **= reciprocal(ord, dtype=ret.dtype)
            return ret
    elif len(axis) == 2:
        row_axis, col_axis = axis
        row_axis = normalize_axis_index(row_axis, nd)
        col_axis = normalize_axis_index(col_axis, nd)
        if row_axis == col_axis:
            raise ValueError('Duplicate axes given.')
        if ord == 2:
            ret = _multi_svd_norm(x, row_axis, col_axis, amax, 0)
        elif ord == -2:
            ret = _multi_svd_norm(x, row_axis, col_axis, amin)
        elif ord == 1:
            if col_axis > row_axis:
                col_axis -= 1
            ret = add.reduce(abs(x), axis=row_axis).max(axis=col_axis, initial=0)
        elif ord == inf:
            if row_axis > col_axis:
                row_axis -= 1
            ret = add.reduce(abs(x), axis=col_axis).max(axis=row_axis, initial=0)
        elif ord == -1:
            if col_axis > row_axis:
                col_axis -= 1
            ret = add.reduce(abs(x), axis=row_axis).min(axis=col_axis)
        elif ord == -inf:
            if row_axis > col_axis:
                row_axis -= 1
            ret = add.reduce(abs(x), axis=col_axis).min(axis=row_axis)
        elif ord in [None, 'fro', 'f']:
            ret = sqrt(add.reduce((x.conj() * x).real, axis=axis))
        elif ord == 'nuc':
            ret = _multi_svd_norm(x, row_axis, col_axis, sum, 0)
        else:
            raise ValueError("Invalid norm order for matrices.")
        if keepdims:
            ret_shape = list(x.shape)
            ret_shape[axis[0]] = 1
            ret_shape[axis[1]] = 1
            ret = ret.reshape(ret_shape)
        return ret
    else:
        raise ValueError("Improper number of dimensions to norm.")


# multi_dot

def _multidot_dispatcher(arrays, *, out=None):
    yield from arrays
    yield out


@array_function_dispatch(_multidot_dispatcher)
def multi_dot(arrays, *, out=None):
    """
    Compute the dot product of two or more arrays in a single function call,
    while automatically selecting the fastest evaluation order.

    `multi_dot` chains `numpy.dot` and uses optimal parenthesization
    of the matrices [1]_ [2]_. Depending on the shapes of the matrices,
    this can speed up the multiplication a lot.

    If the first argument is 1-D it is treated as a row vector.
    If the last argument is 1-D it is treated as a column vector.
    The other arguments must be 2-D.

    Think of `multi_dot` as::

        def multi_dot(arrays): return functools.reduce(np.dot, arrays)


    Parameters
    ----------
    arrays : sequence of array_like
        If the first argument is 1-D it is treated as row vector.
        If the last argument is 1-D it is treated as column vector.
        The other arguments must be 2-D.
    out : ndarray, optional
        Output argument. This must have the exact kind that would be returned
        if it was not used. In particular, it must have the right type, must be
        C-contiguous, and its dtype must be the dtype that would be returned
        for `dot(a, b)`. This is a performance feature. Therefore, if these
        conditions are not met, an exception is raised, instead of attempting
        to be flexible.

    Returns
    -------
    output : ndarray
        Returns the dot product of the supplied arrays.

    See Also
    --------
    numpy.dot : dot multiplication with two arguments.

    References
    ----------

    .. [1] Cormen, "Introduction to Algorithms", Chapter 15.2, p. 370-378
    .. [2] https://en.wikipedia.org/wiki/Matrix_chain_multiplication

    Examples
    --------
    `multi_dot` allows you to write::

    >>> import numpy as np
    >>> from numpy.linalg import multi_dot
    >>> # Prepare some data
    >>> A = np.random.random((10000, 100))
    >>> B = np.random.random((100, 1000))
    >>> C = np.random.random((1000, 5))
    >>> D = np.random.random((5, 333))
    >>> # the actual dot multiplication
    >>> _ = multi_dot([A, B, C, D])

    instead of::

    >>> _ = np.dot(np.dot(np.dot(A, B), C), D)
    >>> # or
    >>> _ = A.dot(B).dot(C).dot(D)

    Notes
    -----
    The cost for a matrix multiplication can be calculated with the
    following function::

        def cost(A, B):
            return A.shape[0] * A.shape[1] * B.shape[1]

    Assume we have three matrices
    :math:`A_{10 \times 100}, B_{100 \times 5}, C_{5 \times 50}`.

    The costs for the two different parenthesizations are as follows::

        cost((AB)C) = 10*100*5 + 10*5*50   = 5000 + 2500   = 7500
        cost(A(BC)) = 10*100*50 + 100*5*50 = 50000 + 25000 = 75000

    """
    n = len(arrays)
    # optimization only makes sense for len(arrays) > 2
    if n < 2:
        raise ValueError("Expecting at least two arrays.")
    elif n == 2:
        return dot(arrays[0], arrays[1], out=out)

    arrays = [asanyarray(a) for a in arrays]

    # save original ndim to reshape the result array into the proper form later
    ndim_first, ndim_last = arrays[0].ndim, arrays[-1].ndim
    # Explicitly convert vectors to 2D arrays to keep the logic of the internal
    # _multi_dot_* functions as simple as possible.
    if arrays[0].ndim == 1:
        arrays[0] = atleast_2d(arrays[0])
    if arrays[-1].ndim == 1:
        arrays[-1] = atleast_2d(arrays[-1]).T
    _assert_2d(*arrays)

    # _multi_dot_three is much faster than _multi_dot_matrix_chain_order
    if n == 3:
        result = _multi_dot_three(arrays[0], arrays[1], arrays[2], out=out)
    else:
        order = _multi_dot_matrix_chain_order(arrays)
        result = _multi_dot(arrays, order, 0, n - 1, out=out)

    # return proper shape
    if ndim_first == 1 and ndim_last == 1:
        return result[0, 0]  # scalar
    elif ndim_first == 1 or ndim_last == 1:
        return result.ravel()  # 1-D
    else:
        return result


def _multi_dot_three(A, B, C, out=None):
    """
    Find the best order for three arrays and do the multiplication.

    For three arguments `_multi_dot_three` is approximately 15 times faster
    than `_multi_dot_matrix_chain_order`

    """
    a0, a1b0 = A.shape
    b1c0, c1 = C.shape
    # cost1 = cost((AB)C) = a0*a1b0*b1c0 + a0*b1c0*c1
    cost1 = a0 * b1c0 * (a1b0 + c1)
    # cost2 = cost(A(BC)) = a1b0*b1c0*c1 + a0*a1b0*c1
    cost2 = a1b0 * c1 * (a0 + b1c0)

    if cost1 < cost2:
        return dot(dot(A, B), C, out=out)
    else:
        return dot(A, dot(B, C), out=out)


def _multi_dot_matrix_chain_order(arrays, return_costs=False):
    """
    Return a np.array that encodes the optimal order of multiplications.

    The optimal order array is then used by `_multi_dot()` to do the
    multiplication.

    Also return the cost matrix if `return_costs` is `True`

    The implementation CLOSELY follows Cormen, "Introduction to Algorithms",
    Chapter 15.2, p. 370-378.  Note that Cormen uses 1-based indices.

        cost[i, j] = min([
            cost[prefix] + cost[suffix] + cost_mult(prefix, suffix)
            for k in range(i, j)])

    """
    n = len(arrays)
    # p stores the dimensions of the matrices
    # Example for p: A_{10x100}, B_{100x5}, C_{5x50} --> p = [10, 100, 5, 50]
    p = [a.shape[0] for a in arrays] + [arrays[-1].shape[1]]
    # m is a matrix of costs of the subproblems
    # m[i,j]: min number of scalar multiplications needed to compute A_{i..j}
    m = zeros((n, n), dtype=double)
    # s is the actual ordering
    # s[i, j] is the value of k at which we split the product A_i..A_j
    s = empty((n, n), dtype=intp)

    for l in range(1, n):
        for i in range(n - l):
            j = i + l
            m[i, j] = inf
            for k in range(i, j):
                q = m[i, k] + m[k + 1, j] + p[i] * p[k + 1] * p[j + 1]
                if q < m[i, j]:
                    m[i, j] = q
                    s[i, j] = k  # Note that Cormen uses 1-based index

    return (s, m) if return_costs else s


def _multi_dot(arrays, order, i, j, out=None):
    """Actually do the multiplication with the given order."""
    if i == j:
        # the initial call with non-None out should never get here
        assert out is None

        return arrays[i]
    else:
        return dot(_multi_dot(arrays, order, i, order[i, j]),
                   _multi_dot(arrays, order, order[i, j] + 1, j),
                   out=out)


# diagonal

def _diagonal_dispatcher(x, /, *, offset=None):
    return (x,)


@array_function_dispatch(_diagonal_dispatcher)
def diagonal(x, /, *, offset=0):
    """
    Returns specified diagonals of a matrix (or a stack of matrices) ``x``.

    This function is Array API compatible, contrary to
    :py:func:`numpy.diagonal`, the matrix is assumed
    to be defined by the last two dimensions.

    Parameters
    ----------
    x : (...,M,N) array_like
        Input array having shape (..., M, N) and whose innermost two
        dimensions form MxN matrices.
    offset : int, optional
        Offset specifying the off-diagonal relative to the main diagonal,
        where::

            * offset = 0: the main diagonal.
            * offset > 0: off-diagonal above the main diagonal.
            * offset < 0: off-diagonal below the main diagonal.

    Returns
    -------
    out : (...,min(N,M)) ndarray
        An array containing the diagonals and whose shape is determined by
        removing the last two dimensions and appending a dimension equal to
        the size of the resulting diagonals. The returned array must have
        the same data type as ``x``.

    See Also
    --------
    numpy.diagonal

    Examples
    --------
    >>> a = np.arange(4).reshape(2, 2); a
    array([[0, 1],
           [2, 3]])
    >>> np.linalg.diagonal(a)
    array([0, 3])

    A 3-D example:

    >>> a = np.arange(8).reshape(2, 2, 2); a
    array([[[0, 1],
            [2, 3]],
           [[4, 5],
            [6, 7]]])
    >>> np.linalg.diagonal(a)
    array([[0, 3],
           [4, 7]])

    Diagonals adjacent to the main diagonal can be obtained by using the
    `offset` argument:

    >>> a = np.arange(9).reshape(3, 3)
    >>> a
    array([[0, 1, 2],
           [3, 4, 5],
           [6, 7, 8]])
    >>> np.linalg.diagonal(a, offset=1)  # First superdiagonal
    array([1, 5])
    >>> np.linalg.diagonal(a, offset=2)  # Second superdiagonal
    array([2])
    >>> np.linalg.diagonal(a, offset=-1)  # First subdiagonal
    array([3, 7])
    >>> np.linalg.diagonal(a, offset=-2)  # Second subdiagonal
    array([6])

    The anti-diagonal can be obtained by reversing the order of elements
    using either `numpy.flipud` or `numpy.fliplr`.

    >>> a = np.arange(9).reshape(3, 3)
    >>> a
    array([[0, 1, 2],
           [3, 4, 5],
           [6, 7, 8]])
    >>> np.linalg.diagonal(np.fliplr(a))  # Horizontal flip
    array([2, 4, 6])
    >>> np.linalg.diagonal(np.flipud(a))  # Vertical flip
    array([6, 4, 2])

    Note that the order in which the diagonal is retrieved varies depending
    on the flip function.

    """
    return _core_diagonal(x, offset, axis1=-2, axis2=-1)


# trace

def _trace_dispatcher(x, /, *, offset=None, dtype=None):
    return (x,)


@array_function_dispatch(_trace_dispatcher)
def trace(x, /, *, offset=0, dtype=None):
    """
    Returns the sum along the specified diagonals of a matrix
    (or a stack of matrices) ``x``.

    This function is Array API compatible, contrary to
    :py:func:`numpy.trace`.

    Parameters
    ----------
    x : (...,M,N) array_like
        Input array having shape (..., M, N) and whose innermost two
        dimensions form MxN matrices.
    offset : int, optional
        Offset specifying the off-diagonal relative to the main diagonal,
        where::

            * offset = 0: the main diagonal.
            * offset > 0: off-diagonal above the main diagonal.
            * offset < 0: off-diagonal below the main diagonal.

    dtype : dtype, optional
        Data type of the returned array.

    Returns
    -------
    out : ndarray
        An array containing the traces and whose shape is determined by
        removing the last two dimensions and storing the traces in the last
        array dimension. For example, if x has rank k and shape:
        (I, J, K, ..., L, M, N), then an output array has rank k-2 and shape:
        (I, J, K, ..., L) where::

            out[i, j, k, ..., l] = trace(a[i, j, k, ..., l, :, :])

        The returned array must have a data type as described by the dtype
        parameter above.

    See Also
    --------
    numpy.trace

    Examples
    --------
    >>> np.linalg.trace(np.eye(3))
    3.0
    >>> a = np.arange(8).reshape((2, 2, 2))
    >>> np.linalg.trace(a)
    array([3, 11])

    Trace is computed with the last two axes as the 2-d sub-arrays.
    This behavior differs from :py:func:`numpy.trace` which uses the first two
    axes by default.

    >>> a = np.arange(24).reshape((3, 2, 2, 2))
    >>> np.linalg.trace(a).shape
    (3, 2)

    Traces adjacent to the main diagonal can be obtained by using the
    `offset` argument:

    >>> a = np.arange(9).reshape((3, 3)); a
    array([[0, 1, 2],
           [3, 4, 5],
           [6, 7, 8]])
    >>> np.linalg.trace(a, offset=1)  # First superdiagonal
    6
    >>> np.linalg.trace(a, offset=2)  # Second superdiagonal
    2
    >>> np.linalg.trace(a, offset=-1)  # First subdiagonal
    10
    >>> np.linalg.trace(a, offset=-2)  # Second subdiagonal
    6

    """
    return _core_trace(x, offset, axis1=-2, axis2=-1, dtype=dtype)


# cross

def _cross_dispatcher(x1, x2, /, *, axis=None):
    return (x1, x2,)


@array_function_dispatch(_cross_dispatcher)
def cross(x1, x2, /, *, axis=-1):
    """
    Returns the cross product of 3-element vectors.

    If ``x1`` and/or ``x2`` are multi-dimensional arrays, then
    the cross-product of each pair of corresponding 3-element vectors
    is independently computed.

    This function is Array API compatible, contrary to
    :func:`numpy.cross`.

    Parameters
    ----------
    x1 : array_like
        The first input array.
    x2 : array_like
        The second input array. Must be compatible with ``x1`` for all
        non-compute axes. The size of the axis over which to compute
        the cross-product must be the same size as the respective axis
        in ``x1``.
    axis : int, optional
        The axis (dimension) of ``x1`` and ``x2`` containing the vectors for
        which to compute the cross-product. Default: ``-1``.

    Returns
    -------
    out : ndarray
        An array containing the cross products.

    See Also
    --------
    numpy.cross

    Examples
    --------
    Vector cross-product.

    >>> x = np.array([1, 2, 3])
    >>> y = np.array([4, 5, 6])
    >>> np.linalg.cross(x, y)
    array([-3,  6, -3])

    Multiple vector cross-products. Note that the direction of the cross
    product vector is defined by the *right-hand rule*.

    >>> x = np.array([[1,2,3], [4,5,6]])
    >>> y = np.array([[4,5,6], [1,2,3]])
    >>> np.linalg.cross(x, y)
    array([[-3,  6, -3],
           [ 3, -6,  3]])

    >>> x = np.array([[1, 2], [3, 4], [5, 6]])
    >>> y = np.array([[4, 5], [6, 1], [2, 3]])
    >>> np.linalg.cross(x, y, axis=0)
    array([[-24,  6],
           [ 18, 24],
           [-6,  -18]])

    """
    x1 = asanyarray(x1)
    x2 = asanyarray(x2)

    if x1.shape[axis] != 3 or x2.shape[axis] != 3:
        raise ValueError(
            "Both input arrays must be (arrays of) 3-dimensional vectors, "
            f"but they are {x1.shape[axis]} and {x2.shape[axis]} "
            "dimensional instead."
        )

    return _core_cross(x1, x2, axis=axis)


# matmul

def _matmul_dispatcher(x1, x2, /):
    return (x1, x2)


@array_function_dispatch(_matmul_dispatcher)
def matmul(x1, x2, /):
    """
    Computes the matrix product.

    This function is Array API compatible, contrary to
    :func:`numpy.matmul`.

    Parameters
    ----------
    x1 : array_like
        The first input array.
    x2 : array_like
        The second input array.

    Returns
    -------
    out : ndarray
        The matrix product of the inputs.
        This is a scalar only when both ``x1``, ``x2`` are 1-d vectors.

    Raises
    ------
    ValueError
        If the last dimension of ``x1`` is not the same size as
        the second-to-last dimension of ``x2``.

        If a scalar value is passed in.

    See Also
    --------
    numpy.matmul

    Examples
    --------
    For 2-D arrays it is the matrix product:

    >>> a = np.array([[1, 0],
    ...               [0, 1]])
    >>> b = np.array([[4, 1],
    ...               [2, 2]])
    >>> np.linalg.matmul(a, b)
    array([[4, 1],
           [2, 2]])

    For 2-D mixed with 1-D, the result is the usual.

    >>> a = np.array([[1, 0],
    ...               [0, 1]])
    >>> b = np.array([1, 2])
    >>> np.linalg.matmul(a, b)
    array([1, 2])
    >>> np.linalg.matmul(b, a)
    array([1, 2])


    Broadcasting is conventional for stacks of arrays

    >>> a = np.arange(2 * 2 * 4).reshape((2, 2, 4))
    >>> b = np.arange(2 * 2 * 4).reshape((2, 4, 2))
    >>> np.linalg.matmul(a,b).shape
    (2, 2, 2)
    >>> np.linalg.matmul(a, b)[0, 1, 1]
    98
    >>> sum(a[0, 1, :] * b[0 , :, 1])
    98

    Vector, vector returns the scalar inner product, but neither argument
    is complex-conjugated:

    >>> np.linalg.matmul([2j, 3j], [2j, 3j])
    (-13+0j)

    Scalar multiplication raises an error.

    >>> np.linalg.matmul([1,2], 3)
    Traceback (most recent call last):
    ...
    ValueError: matmul: Input operand 1 does not have enough dimensions ...

    """
    return _core_matmul(x1, x2)


# tensordot

def _tensordot_dispatcher(x1, x2, /, *, axes=None):
    return (x1, x2)


@array_function_dispatch(_tensordot_dispatcher)
def tensordot(x1, x2, /, *, axes=2):
    return _core_tensordot(x1, x2, axes=axes)


tensordot.__doc__ = _core_tensordot.__doc__


# matrix_transpose

def _matrix_transpose_dispatcher(x):
    return (x,)

@array_function_dispatch(_matrix_transpose_dispatcher)
def matrix_transpose(x, /):
    return _core_matrix_transpose(x)


matrix_transpose.__doc__ = f"""{_core_matrix_transpose.__doc__}

    Notes
    -----
    This function is an alias of `numpy.matrix_transpose`.
"""


# matrix_norm

def _matrix_norm_dispatcher(x, /, *, keepdims=None, ord=None):
    return (x,)

@array_function_dispatch(_matrix_norm_dispatcher)
def matrix_norm(x, /, *, keepdims=False, ord="fro"):
    """
    Computes the matrix norm of a matrix (or a stack of matrices) ``x``.

    This function is Array API compatible.

    Parameters
    ----------
    x : array_like
        Input array having shape (..., M, N) and whose two innermost
        dimensions form ``MxN`` matrices.
    keepdims : bool, optional
        If this is set to True, the axes which are normed over are left in
        the result as dimensions with size one. Default: False.
    ord : {1, -1, 2, -2, inf, -inf, 'fro', 'nuc'}, optional
        The order of the norm. For details see the table under ``Notes``
        in `numpy.linalg.norm`.

    See Also
    --------
    numpy.linalg.norm : Generic norm function

    Examples
    --------
    >>> from numpy import linalg as LA
    >>> a = np.arange(9) - 4
    >>> a
    array([-4, -3, -2, ...,  2,  3,  4])
    >>> b = a.reshape((3, 3))
    >>> b
    array([[-4, -3, -2],
           [-1,  0,  1],
           [ 2,  3,  4]])

    >>> LA.matrix_norm(b)
    7.745966692414834
    >>> LA.matrix_norm(b, ord='fro')
    7.745966692414834
    >>> LA.matrix_norm(b, ord=np.inf)
    9.0
    >>> LA.matrix_norm(b, ord=-np.inf)
    2.0

    >>> LA.matrix_norm(b, ord=1)
    7.0
    >>> LA.matrix_norm(b, ord=-1)
    6.0
    >>> LA.matrix_norm(b, ord=2)
    7.3484692283495345
    >>> LA.matrix_norm(b, ord=-2)
    1.8570331885190563e-016 # may vary

    """
    x = asanyarray(x)
    return norm(x, axis=(-2, -1), keepdims=keepdims, ord=ord)


# vector_norm

def _vector_norm_dispatcher(x, /, *, axis=None, keepdims=None, ord=None):
    return (x,)

@array_function_dispatch(_vector_norm_dispatcher)
def vector_norm(x, /, *, axis=None, keepdims=False, ord=2):
    """
    Computes the vector norm of a vector (or batch of vectors) ``x``.

    This function is Array API compatible.

    Parameters
    ----------
    x : array_like
        Input array.
    axis : {None, int, 2-tuple of ints}, optional
        If an integer, ``axis`` specifies the axis (dimension) along which
        to compute vector norms. If an n-tuple, ``axis`` specifies the axes
        (dimensions) along which to compute batched vector norms. If ``None``,
        the vector norm must be computed over all array values (i.e.,
        equivalent to computing the vector norm of a flattened array).
        Default: ``None``.
    keepdims : bool, optional
        If this is set to True, the axes which are normed over are left in
        the result as dimensions with size one. Default: False.
    ord : {int, float, inf, -inf}, optional
        The order of the norm. For details see the table under ``Notes``
        in `numpy.linalg.norm`.

    See Also
    --------
    numpy.linalg.norm : Generic norm function

    Examples
    --------
    >>> from numpy import linalg as LA
    >>> a = np.arange(9) + 1
    >>> a
    array([1, 2, 3, 4, 5, 6, 7, 8, 9])
    >>> b = a.reshape((3, 3))
    >>> b
    array([[1, 2, 3],
           [4, 5, 6],
           [7, 8, 9]])

    >>> LA.vector_norm(b)
    16.881943016134134
    >>> LA.vector_norm(b, ord=np.inf)
    9.0
    >>> LA.vector_norm(b, ord=-np.inf)
    1.0

    >>> LA.vector_norm(b, ord=0)
    9.0
    >>> LA.vector_norm(b, ord=1)
    45.0
    >>> LA.vector_norm(b, ord=-1)
    0.3534857623790153
    >>> LA.vector_norm(b, ord=2)
    16.881943016134134
    >>> LA.vector_norm(b, ord=-2)
    0.8058837395885292

    """
    x = asanyarray(x)
    shape = list(x.shape)
    if axis is None:
        # Note: np.linalg.norm() doesn't handle 0-D arrays
        x = x.ravel()
        _axis = 0
    elif isinstance(axis, tuple):
        # Note: The axis argument supports any number of axes, whereas
        # np.linalg.norm() only supports a single axis for vector norm.
        normalized_axis = normalize_axis_tuple(axis, x.ndim)
        rest = tuple(i for i in range(x.ndim) if i not in normalized_axis)
        newshape = axis + rest
        x = _core_transpose(x, newshape).reshape(
            (
                prod([x.shape[i] for i in axis], dtype=int),
                *[x.shape[i] for i in rest]
            )
        )
        _axis = 0
    else:
        _axis = axis

    res = norm(x, axis=_axis, ord=ord)

    if keepdims:
        # We can't reuse np.linalg.norm(keepdims) because of the reshape hacks
        # above to avoid matrix norm logic.
        _axis = normalize_axis_tuple(
            range(len(shape)) if axis is None else axis, len(shape)
        )
        for i in _axis:
            shape[i] = 1
        res = res.reshape(tuple(shape))

    return res


# vecdot

def _vecdot_dispatcher(x1, x2, /, *, axis=None):
    return (x1, x2)

@array_function_dispatch(_vecdot_dispatcher)
def vecdot(x1, x2, /, *, axis=-1):
    """
    Computes the vector dot product.

    This function is restricted to arguments compatible with the Array API,
    contrary to :func:`numpy.vecdot`.

    Let :math:`\\mathbf{a}` be a vector in ``x1`` and :math:`\\mathbf{b}` be
    a corresponding vector in ``x2``. The dot product is defined as:

    .. math::
       \\mathbf{a} \\cdot \\mathbf{b} = \\sum_{i=0}^{n-1} \\overline{a_i}b_i

    over the dimension specified by ``axis`` and where :math:`\\overline{a_i}`
    denotes the complex conjugate if :math:`a_i` is complex and the identity
    otherwise.

    Parameters
    ----------
    x1 : array_like
        First input array.
    x2 : array_like
        Second input array.
    axis : int, optional
        Axis over which to compute the dot product. Default: ``-1``.

    Returns
    -------
    output : ndarray
        The vector dot product of the input.

    See Also
    --------
    numpy.vecdot

    Examples
    --------
    Get the projected size along a given normal for an array of vectors.

    >>> v = np.array([[0., 5., 0.], [0., 0., 10.], [0., 6., 8.]])
    >>> n = np.array([0., 0.6, 0.8])
    >>> np.linalg.vecdot(v, n)
    array([ 3.,  8., 10.])

    """
    return _core_vecdot(x1, x2, axis=axis)

# === NexusCore/myenv\Lib\site-packages\pip\_vendor\pkg_resources\__init__.py ===
# TODO: Add Generic type annotations to initialized collections.
# For now we'd simply use implicit Any/Unknown which would add redundant annotations
# mypy: disable-error-code="var-annotated"
"""
Package resource API
--------------------

A resource is a logical file contained within a package, or a logical
subdirectory thereof.  The package resource API expects resource names
to have their path parts separated with ``/``, *not* whatever the local
path separator is.  Do not use os.path operations to manipulate resource
names being passed into the API.

The package resource API is designed to work with normal filesystem packages,
.egg files, and unpacked .egg files.  It can also work in a limited way with
.zip files and with custom PEP 302 loaders that support the ``get_data()``
method.

This module is deprecated. Users are directed to :mod:`importlib.resources`,
:mod:`importlib.metadata` and :pypi:`packaging` instead.
"""

from __future__ import annotations

import sys

if sys.version_info < (3, 8):  # noqa: UP036 # Check for unsupported versions
    raise RuntimeError("Python 3.8 or later is required")

import os
import io
import time
import re
import types
from typing import (
    Any,
    Literal,
    Dict,
    Iterator,
    Mapping,
    MutableSequence,
    NamedTuple,
    NoReturn,
    Tuple,
    Union,
    TYPE_CHECKING,
    Protocol,
    Callable,
    Iterable,
    TypeVar,
    overload,
)
import zipfile
import zipimport
import warnings
import stat
import functools
import pkgutil
import operator
import platform
import collections
import plistlib
import email.parser
import errno
import tempfile
import textwrap
import inspect
import ntpath
import posixpath
import importlib
import importlib.abc
import importlib.machinery
from pkgutil import get_importer

import _imp

# capture these to bypass sandboxing
from os import utime
from os import open as os_open
from os.path import isdir, split

try:
    from os import mkdir, rename, unlink

    WRITE_SUPPORT = True
except ImportError:
    # no write support, probably under GAE
    WRITE_SUPPORT = False

from pip._internal.utils._jaraco_text import (
    yield_lines,
    drop_comment,
    join_continuation,
)
from pip._vendor.packaging import markers as _packaging_markers
from pip._vendor.packaging import requirements as _packaging_requirements
from pip._vendor.packaging import utils as _packaging_utils
from pip._vendor.packaging import version as _packaging_version
from pip._vendor.platformdirs import user_cache_dir as _user_cache_dir

if TYPE_CHECKING:
    from _typeshed import BytesPath, StrPath, StrOrBytesPath
    from pip._vendor.typing_extensions import Self


# Patch: Remove deprecation warning from vendored pkg_resources.
# Setting PYTHONWARNINGS=error to verify builds produce no warnings
# causes immediate exceptions.
# See https://github.com/pypa/pip/issues/12243


_T = TypeVar("_T")
_DistributionT = TypeVar("_DistributionT", bound="Distribution")
# Type aliases
_NestedStr = Union[str, Iterable[Union[str, Iterable["_NestedStr"]]]]
_InstallerTypeT = Callable[["Requirement"], "_DistributionT"]
_InstallerType = Callable[["Requirement"], Union["Distribution", None]]
_PkgReqType = Union[str, "Requirement"]
_EPDistType = Union["Distribution", _PkgReqType]
_MetadataType = Union["IResourceProvider", None]
_ResolvedEntryPoint = Any  # Can be any attribute in the module
_ResourceStream = Any  # TODO / Incomplete: A readable file-like object
# Any object works, but let's indicate we expect something like a module (optionally has __loader__ or __file__)
_ModuleLike = Union[object, types.ModuleType]
# Any: Should be _ModuleLike but we end up with issues where _ModuleLike doesn't have _ZipLoaderModule's __loader__
_ProviderFactoryType = Callable[[Any], "IResourceProvider"]
_DistFinderType = Callable[[_T, str, bool], Iterable["Distribution"]]
_NSHandlerType = Callable[[_T, str, str, types.ModuleType], Union[str, None]]
_AdapterT = TypeVar(
    "_AdapterT", _DistFinderType[Any], _ProviderFactoryType, _NSHandlerType[Any]
)


# Use _typeshed.importlib.LoaderProtocol once available https://github.com/python/typeshed/pull/11890
class _LoaderProtocol(Protocol):
    def load_module(self, fullname: str, /) -> types.ModuleType: ...


class _ZipLoaderModule(Protocol):
    __loader__: zipimport.zipimporter


_PEP440_FALLBACK = re.compile(r"^v?(?P<safe>(?:[0-9]+!)?[0-9]+(?:\.[0-9]+)*)", re.I)


class PEP440Warning(RuntimeWarning):
    """
    Used when there is an issue with a version or specifier not complying with
    PEP 440.
    """


parse_version = _packaging_version.Version


_state_vars: dict[str, str] = {}


def _declare_state(vartype: str, varname: str, initial_value: _T) -> _T:
    _state_vars[varname] = vartype
    return initial_value


def __getstate__() -> dict[str, Any]:
    state = {}
    g = globals()
    for k, v in _state_vars.items():
        state[k] = g['_sget_' + v](g[k])
    return state


def __setstate__(state: dict[str, Any]) -> dict[str, Any]:
    g = globals()
    for k, v in state.items():
        g['_sset_' + _state_vars[k]](k, g[k], v)
    return state


def _sget_dict(val):
    return val.copy()


def _sset_dict(key, ob, state):
    ob.clear()
    ob.update(state)


def _sget_object(val):
    return val.__getstate__()


def _sset_object(key, ob, state):
    ob.__setstate__(state)


_sget_none = _sset_none = lambda *args: None


def get_supported_platform():
    """Return this platform's maximum compatible version.

    distutils.util.get_platform() normally reports the minimum version
    of macOS that would be required to *use* extensions produced by
    distutils.  But what we want when checking compatibility is to know the
    version of macOS that we are *running*.  To allow usage of packages that
    explicitly require a newer version of macOS, we must also know the
    current version of the OS.

    If this condition occurs for any other platform with a version in its
    platform strings, this function should be extended accordingly.
    """
    plat = get_build_platform()
    m = macosVersionString.match(plat)
    if m is not None and sys.platform == "darwin":
        try:
            plat = 'macosx-%s-%s' % ('.'.join(_macos_vers()[:2]), m.group(3))
        except ValueError:
            # not macOS
            pass
    return plat


__all__ = [
    # Basic resource access and distribution/entry point discovery
    'require',
    'run_script',
    'get_provider',
    'get_distribution',
    'load_entry_point',
    'get_entry_map',
    'get_entry_info',
    'iter_entry_points',
    'resource_string',
    'resource_stream',
    'resource_filename',
    'resource_listdir',
    'resource_exists',
    'resource_isdir',
    # Environmental control
    'declare_namespace',
    'working_set',
    'add_activation_listener',
    'find_distributions',
    'set_extraction_path',
    'cleanup_resources',
    'get_default_cache',
    # Primary implementation classes
    'Environment',
    'WorkingSet',
    'ResourceManager',
    'Distribution',
    'Requirement',
    'EntryPoint',
    # Exceptions
    'ResolutionError',
    'VersionConflict',
    'DistributionNotFound',
    'UnknownExtra',
    'ExtractionError',
    # Warnings
    'PEP440Warning',
    # Parsing functions and string utilities
    'parse_requirements',
    'parse_version',
    'safe_name',
    'safe_version',
    'get_platform',
    'compatible_platforms',
    'yield_lines',
    'split_sections',
    'safe_extra',
    'to_filename',
    'invalid_marker',
    'evaluate_marker',
    # filesystem utilities
    'ensure_directory',
    'normalize_path',
    # Distribution "precedence" constants
    'EGG_DIST',
    'BINARY_DIST',
    'SOURCE_DIST',
    'CHECKOUT_DIST',
    'DEVELOP_DIST',
    # "Provider" interfaces, implementations, and registration/lookup APIs
    'IMetadataProvider',
    'IResourceProvider',
    'FileMetadata',
    'PathMetadata',
    'EggMetadata',
    'EmptyProvider',
    'empty_provider',
    'NullProvider',
    'EggProvider',
    'DefaultProvider',
    'ZipProvider',
    'register_finder',
    'register_namespace_handler',
    'register_loader_type',
    'fixup_namespace_packages',
    'get_importer',
    # Warnings
    'PkgResourcesDeprecationWarning',
    # Deprecated/backward compatibility only
    'run_main',
    'AvailableDistributions',
]


class ResolutionError(Exception):
    """Abstract base for dependency resolution errors"""

    def __repr__(self):
        return self.__class__.__name__ + repr(self.args)


class VersionConflict(ResolutionError):
    """
    An already-installed version conflicts with the requested version.

    Should be initialized with the installed Distribution and the requested
    Requirement.
    """

    _template = "{self.dist} is installed but {self.req} is required"

    @property
    def dist(self) -> Distribution:
        return self.args[0]

    @property
    def req(self) -> Requirement:
        return self.args[1]

    def report(self):
        return self._template.format(**locals())

    def with_context(self, required_by: set[Distribution | str]):
        """
        If required_by is non-empty, return a version of self that is a
        ContextualVersionConflict.
        """
        if not required_by:
            return self
        args = self.args + (required_by,)
        return ContextualVersionConflict(*args)


class ContextualVersionConflict(VersionConflict):
    """
    A VersionConflict that accepts a third parameter, the set of the
    requirements that required the installed Distribution.
    """

    _template = VersionConflict._template + ' by {self.required_by}'

    @property
    def required_by(self) -> set[str]:
        return self.args[2]


class DistributionNotFound(ResolutionError):
    """A requested distribution was not found"""

    _template = (
        "The '{self.req}' distribution was not found "
        "and is required by {self.requirers_str}"
    )

    @property
    def req(self) -> Requirement:
        return self.args[0]

    @property
    def requirers(self) -> set[str] | None:
        return self.args[1]

    @property
    def requirers_str(self):
        if not self.requirers:
            return 'the application'
        return ', '.join(self.requirers)

    def report(self):
        return self._template.format(**locals())

    def __str__(self):
        return self.report()


class UnknownExtra(ResolutionError):
    """Distribution doesn't have an "extra feature" of the given name"""


_provider_factories: dict[type[_ModuleLike], _ProviderFactoryType] = {}

PY_MAJOR = '{}.{}'.format(*sys.version_info)
EGG_DIST = 3
BINARY_DIST = 2
SOURCE_DIST = 1
CHECKOUT_DIST = 0
DEVELOP_DIST = -1


def register_loader_type(
    loader_type: type[_ModuleLike], provider_factory: _ProviderFactoryType
):
    """Register `provider_factory` to make providers for `loader_type`

    `loader_type` is the type or class of a PEP 302 ``module.__loader__``,
    and `provider_factory` is a function that, passed a *module* object,
    returns an ``IResourceProvider`` for that module.
    """
    _provider_factories[loader_type] = provider_factory


@overload
def get_provider(moduleOrReq: str) -> IResourceProvider: ...
@overload
def get_provider(moduleOrReq: Requirement) -> Distribution: ...
def get_provider(moduleOrReq: str | Requirement) -> IResourceProvider | Distribution:
    """Return an IResourceProvider for the named module or requirement"""
    if isinstance(moduleOrReq, Requirement):
        return working_set.find(moduleOrReq) or require(str(moduleOrReq))[0]
    try:
        module = sys.modules[moduleOrReq]
    except KeyError:
        __import__(moduleOrReq)
        module = sys.modules[moduleOrReq]
    loader = getattr(module, '__loader__', None)
    return _find_adapter(_provider_factories, loader)(module)


@functools.lru_cache(maxsize=None)
def _macos_vers():
    version = platform.mac_ver()[0]
    # fallback for MacPorts
    if version == '':
        plist = '/System/Library/CoreServices/SystemVersion.plist'
        if os.path.exists(plist):
            with open(plist, 'rb') as fh:
                plist_content = plistlib.load(fh)
            if 'ProductVersion' in plist_content:
                version = plist_content['ProductVersion']
    return version.split('.')


def _macos_arch(machine):
    return {'PowerPC': 'ppc', 'Power_Macintosh': 'ppc'}.get(machine, machine)


def get_build_platform():
    """Return this platform's string for platform-specific distributions

    XXX Currently this is the same as ``distutils.util.get_platform()``, but it
    needs some hacks for Linux and macOS.
    """
    from sysconfig import get_platform

    plat = get_platform()
    if sys.platform == "darwin" and not plat.startswith('macosx-'):
        try:
            version = _macos_vers()
            machine = os.uname()[4].replace(" ", "_")
            return "macosx-%d.%d-%s" % (
                int(version[0]),
                int(version[1]),
                _macos_arch(machine),
            )
        except ValueError:
            # if someone is running a non-Mac darwin system, this will fall
            # through to the default implementation
            pass
    return plat


macosVersionString = re.compile(r"macosx-(\d+)\.(\d+)-(.*)")
darwinVersionString = re.compile(r"darwin-(\d+)\.(\d+)\.(\d+)-(.*)")
# XXX backward compat
get_platform = get_build_platform


def compatible_platforms(provided: str | None, required: str | None):
    """Can code for the `provided` platform run on the `required` platform?

    Returns true if either platform is ``None``, or the platforms are equal.

    XXX Needs compatibility checks for Linux and other unixy OSes.
    """
    if provided is None or required is None or provided == required:
        # easy case
        return True

    # macOS special cases
    reqMac = macosVersionString.match(required)
    if reqMac:
        provMac = macosVersionString.match(provided)

        # is this a Mac package?
        if not provMac:
            # this is backwards compatibility for packages built before
            # setuptools 0.6. All packages built after this point will
            # use the new macOS designation.
            provDarwin = darwinVersionString.match(provided)
            if provDarwin:
                dversion = int(provDarwin.group(1))
                macosversion = "%s.%s" % (reqMac.group(1), reqMac.group(2))
                if (
                    dversion == 7
                    and macosversion >= "10.3"
                    or dversion == 8
                    and macosversion >= "10.4"
                ):
                    return True
            # egg isn't macOS or legacy darwin
            return False

        # are they the same major version and machine type?
        if provMac.group(1) != reqMac.group(1) or provMac.group(3) != reqMac.group(3):
            return False

        # is the required OS major update >= the provided one?
        if int(provMac.group(2)) > int(reqMac.group(2)):
            return False

        return True

    # XXX Linux and other platforms' special cases should go here
    return False


@overload
def get_distribution(dist: _DistributionT) -> _DistributionT: ...
@overload
def get_distribution(dist: _PkgReqType) -> Distribution: ...
def get_distribution(dist: Distribution | _PkgReqType) -> Distribution:
    """Return a current distribution object for a Requirement or string"""
    if isinstance(dist, str):
        dist = Requirement.parse(dist)
    if isinstance(dist, Requirement):
        # Bad type narrowing, dist has to be a Requirement here, so get_provider has to return Distribution
        dist = get_provider(dist)  # type: ignore[assignment]
    if not isinstance(dist, Distribution):
        raise TypeError("Expected str, Requirement, or Distribution", dist)
    return dist


def load_entry_point(dist: _EPDistType, group: str, name: str) -> _ResolvedEntryPoint:
    """Return `name` entry point of `group` for `dist` or raise ImportError"""
    return get_distribution(dist).load_entry_point(group, name)


@overload
def get_entry_map(
    dist: _EPDistType, group: None = None
) -> dict[str, dict[str, EntryPoint]]: ...
@overload
def get_entry_map(dist: _EPDistType, group: str) -> dict[str, EntryPoint]: ...
def get_entry_map(dist: _EPDistType, group: str | None = None):
    """Return the entry point map for `group`, or the full entry map"""
    return get_distribution(dist).get_entry_map(group)


def get_entry_info(dist: _EPDistType, group: str, name: str):
    """Return the EntryPoint object for `group`+`name`, or ``None``"""
    return get_distribution(dist).get_entry_info(group, name)


class IMetadataProvider(Protocol):
    def has_metadata(self, name: str) -> bool:
        """Does the package's distribution contain the named metadata?"""

    def get_metadata(self, name: str) -> str:
        """The named metadata resource as a string"""

    def get_metadata_lines(self, name: str) -> Iterator[str]:
        """Yield named metadata resource as list of non-blank non-comment lines

        Leading and trailing whitespace is stripped from each line, and lines
        with ``#`` as the first non-blank character are omitted."""

    def metadata_isdir(self, name: str) -> bool:
        """Is the named metadata a directory?  (like ``os.path.isdir()``)"""

    def metadata_listdir(self, name: str) -> list[str]:
        """List of metadata names in the directory (like ``os.listdir()``)"""

    def run_script(self, script_name: str, namespace: dict[str, Any]) -> None:
        """Execute the named script in the supplied namespace dictionary"""


class IResourceProvider(IMetadataProvider, Protocol):
    """An object that provides access to package resources"""

    def get_resource_filename(
        self, manager: ResourceManager, resource_name: str
    ) -> str:
        """Return a true filesystem path for `resource_name`

        `manager` must be a ``ResourceManager``"""

    def get_resource_stream(
        self, manager: ResourceManager, resource_name: str
    ) -> _ResourceStream:
        """Return a readable file-like object for `resource_name`

        `manager` must be a ``ResourceManager``"""

    def get_resource_string(
        self, manager: ResourceManager, resource_name: str
    ) -> bytes:
        """Return the contents of `resource_name` as :obj:`bytes`

        `manager` must be a ``ResourceManager``"""

    def has_resource(self, resource_name: str) -> bool:
        """Does the package contain the named resource?"""

    def resource_isdir(self, resource_name: str) -> bool:
        """Is the named resource a directory?  (like ``os.path.isdir()``)"""

    def resource_listdir(self, resource_name: str) -> list[str]:
        """List of resource names in the directory (like ``os.listdir()``)"""


class WorkingSet:
    """A collection of active distributions on sys.path (or a similar list)"""

    def __init__(self, entries: Iterable[str] | None = None):
        """Create working set from list of path entries (default=sys.path)"""
        self.entries: list[str] = []
        self.entry_keys = {}
        self.by_key = {}
        self.normalized_to_canonical_keys = {}
        self.callbacks = []

        if entries is None:
            entries = sys.path

        for entry in entries:
            self.add_entry(entry)

    @classmethod
    def _build_master(cls):
        """
        Prepare the master working set.
        """
        ws = cls()
        try:
            from __main__ import __requires__
        except ImportError:
            # The main program does not list any requirements
            return ws

        # ensure the requirements are met
        try:
            ws.require(__requires__)
        except VersionConflict:
            return cls._build_from_requirements(__requires__)

        return ws

    @classmethod
    def _build_from_requirements(cls, req_spec):
        """
        Build a working set from a requirement spec. Rewrites sys.path.
        """
        # try it without defaults already on sys.path
        # by starting with an empty path
        ws = cls([])
        reqs = parse_requirements(req_spec)
        dists = ws.resolve(reqs, Environment())
        for dist in dists:
            ws.add(dist)

        # add any missing entries from sys.path
        for entry in sys.path:
            if entry not in ws.entries:
                ws.add_entry(entry)

        # then copy back to sys.path
        sys.path[:] = ws.entries
        return ws

    def add_entry(self, entry: str):
        """Add a path item to ``.entries``, finding any distributions on it

        ``find_distributions(entry, True)`` is used to find distributions
        corresponding to the path entry, and they are added.  `entry` is
        always appended to ``.entries``, even if it is already present.
        (This is because ``sys.path`` can contain the same value more than
        once, and the ``.entries`` of the ``sys.path`` WorkingSet should always
        equal ``sys.path``.)
        """
        self.entry_keys.setdefault(entry, [])
        self.entries.append(entry)
        for dist in find_distributions(entry, True):
            self.add(dist, entry, False)

    def __contains__(self, dist: Distribution) -> bool:
        """True if `dist` is the active distribution for its project"""
        return self.by_key.get(dist.key) == dist

    def find(self, req: Requirement) -> Distribution | None:
        """Find a distribution matching requirement `req`

        If there is an active distribution for the requested project, this
        returns it as long as it meets the version requirement specified by
        `req`.  But, if there is an active distribution for the project and it
        does *not* meet the `req` requirement, ``VersionConflict`` is raised.
        If there is no active distribution for the requested project, ``None``
        is returned.
        """
        dist = self.by_key.get(req.key)

        if dist is None:
            canonical_key = self.normalized_to_canonical_keys.get(req.key)

            if canonical_key is not None:
                req.key = canonical_key
                dist = self.by_key.get(canonical_key)

        if dist is not None and dist not in req:
            # XXX add more info
            raise VersionConflict(dist, req)
        return dist

    def iter_entry_points(self, group: str, name: str | None = None):
        """Yield entry point objects from `group` matching `name`

        If `name` is None, yields all entry points in `group` from all
        distributions in the working set, otherwise only ones matching
        both `group` and `name` are yielded (in distribution order).
        """
        return (
            entry
            for dist in self
            for entry in dist.get_entry_map(group).values()
            if name is None or name == entry.name
        )

    def run_script(self, requires: str, script_name: str):
        """Locate distribution for `requires` and run `script_name` script"""
        ns = sys._getframe(1).f_globals
        name = ns['__name__']
        ns.clear()
        ns['__name__'] = name
        self.require(requires)[0].run_script(script_name, ns)

    def __iter__(self) -> Iterator[Distribution]:
        """Yield distributions for non-duplicate projects in the working set

        The yield order is the order in which the items' path entries were
        added to the working set.
        """
        seen = set()
        for item in self.entries:
            if item not in self.entry_keys:
                # workaround a cache issue
                continue

            for key in self.entry_keys[item]:
                if key not in seen:
                    seen.add(key)
                    yield self.by_key[key]

    def add(
        self,
        dist: Distribution,
        entry: str | None = None,
        insert: bool = True,
        replace: bool = False,
    ):
        """Add `dist` to working set, associated with `entry`

        If `entry` is unspecified, it defaults to the ``.location`` of `dist`.
        On exit from this routine, `entry` is added to the end of the working
        set's ``.entries`` (if it wasn't already present).

        `dist` is only added to the working set if it's for a project that
        doesn't already have a distribution in the set, unless `replace=True`.
        If it's added, any callbacks registered with the ``subscribe()`` method
        will be called.
        """
        if insert:
            dist.insert_on(self.entries, entry, replace=replace)

        if entry is None:
            entry = dist.location
        keys = self.entry_keys.setdefault(entry, [])
        keys2 = self.entry_keys.setdefault(dist.location, [])
        if not replace and dist.key in self.by_key:
            # ignore hidden distros
            return

        self.by_key[dist.key] = dist
        normalized_name = _packaging_utils.canonicalize_name(dist.key)
        self.normalized_to_canonical_keys[normalized_name] = dist.key
        if dist.key not in keys:
            keys.append(dist.key)
        if dist.key not in keys2:
            keys2.append(dist.key)
        self._added_new(dist)

    @overload
    def resolve(
        self,
        requirements: Iterable[Requirement],
        env: Environment | None,
        installer: _InstallerTypeT[_DistributionT],
        replace_conflicting: bool = False,
        extras: tuple[str, ...] | None = None,
    ) -> list[_DistributionT]: ...
    @overload
    def resolve(
        self,
        requirements: Iterable[Requirement],
        env: Environment | None = None,
        *,
        installer: _InstallerTypeT[_DistributionT],
        replace_conflicting: bool = False,
        extras: tuple[str, ...] | None = None,
    ) -> list[_DistributionT]: ...
    @overload
    def resolve(
        self,
        requirements: Iterable[Requirement],
        env: Environment | None = None,
        installer: _InstallerType | None = None,
        replace_conflicting: bool = False,
        extras: tuple[str, ...] | None = None,
    ) -> list[Distribution]: ...
    def resolve(
        self,
        requirements: Iterable[Requirement],
        env: Environment | None = None,
        installer: _InstallerType | None | _InstallerTypeT[_DistributionT] = None,
        replace_conflicting: bool = False,
        extras: tuple[str, ...] | None = None,
    ) -> list[Distribution] | list[_DistributionT]:
        """List all distributions needed to (recursively) meet `requirements`

        `requirements` must be a sequence of ``Requirement`` objects.  `env`,
        if supplied, should be an ``Environment`` instance.  If
        not supplied, it defaults to all distributions available within any
        entry or distribution in the working set.  `installer`, if supplied,
        will be invoked with each requirement that cannot be met by an
        already-installed distribution; it should return a ``Distribution`` or
        ``None``.

        Unless `replace_conflicting=True`, raises a VersionConflict exception
        if
        any requirements are found on the path that have the correct name but
        the wrong version.  Otherwise, if an `installer` is supplied it will be
        invoked to obtain the correct version of the requirement and activate
        it.

        `extras` is a list of the extras to be used with these requirements.
        This is important because extra requirements may look like `my_req;
        extra = "my_extra"`, which would otherwise be interpreted as a purely
        optional requirement.  Instead, we want to be able to assert that these
        requirements are truly required.
        """

        # set up the stack
        requirements = list(requirements)[::-1]
        # set of processed requirements
        processed = set()
        # key -> dist
        best = {}
        to_activate = []

        req_extras = _ReqExtras()

        # Mapping of requirement to set of distributions that required it;
        # useful for reporting info about conflicts.
        required_by = collections.defaultdict(set)

        while requirements:
            # process dependencies breadth-first
            req = requirements.pop(0)
            if req in processed:
                # Ignore cyclic or redundant dependencies
                continue

            if not req_extras.markers_pass(req, extras):
                continue

            dist = self._resolve_dist(
                req, best, replace_conflicting, env, installer, required_by, to_activate
            )

            # push the new requirements onto the stack
            new_requirements = dist.requires(req.extras)[::-1]
            requirements.extend(new_requirements)

            # Register the new requirements needed by req
            for new_requirement in new_requirements:
                required_by[new_requirement].add(req.project_name)
                req_extras[new_requirement] = req.extras

            processed.add(req)

        # return list of distros to activate
        return to_activate

    def _resolve_dist(
        self, req, best, replace_conflicting, env, installer, required_by, to_activate
    ) -> Distribution:
        dist = best.get(req.key)
        if dist is None:
            # Find the best distribution and add it to the map
            dist = self.by_key.get(req.key)
            if dist is None or (dist not in req and replace_conflicting):
                ws = self
                if env is None:
                    if dist is None:
                        env = Environment(self.entries)
                    else:
                        # Use an empty environment and workingset to avoid
                        # any further conflicts with the conflicting
                        # distribution
                        env = Environment([])
                        ws = WorkingSet([])
                dist = best[req.key] = env.best_match(
                    req, ws, installer, replace_conflicting=replace_conflicting
                )
                if dist is None:
                    requirers = required_by.get(req, None)
                    raise DistributionNotFound(req, requirers)
            to_activate.append(dist)
        if dist not in req:
            # Oops, the "best" so far conflicts with a dependency
            dependent_req = required_by[req]
            raise VersionConflict(dist, req).with_context(dependent_req)
        return dist

    @overload
    def find_plugins(
        self,
        plugin_env: Environment,
        full_env: Environment | None,
        installer: _InstallerTypeT[_DistributionT],
        fallback: bool = True,
    ) -> tuple[list[_DistributionT], dict[Distribution, Exception]]: ...
    @overload
    def find_plugins(
        self,
        plugin_env: Environment,
        full_env: Environment | None = None,
        *,
        installer: _InstallerTypeT[_DistributionT],
        fallback: bool = True,
    ) -> tuple[list[_DistributionT], dict[Distribution, Exception]]: ...
    @overload
    def find_plugins(
        self,
        plugin_env: Environment,
        full_env: Environment | None = None,
        installer: _InstallerType | None = None,
        fallback: bool = True,
    ) -> tuple[list[Distribution], dict[Distribution, Exception]]: ...
    def find_plugins(
        self,
        plugin_env: Environment,
        full_env: Environment | None = None,
        installer: _InstallerType | None | _InstallerTypeT[_DistributionT] = None,
        fallback: bool = True,
    ) -> tuple[
        list[Distribution] | list[_DistributionT],
        dict[Distribution, Exception],
    ]:
        """Find all activatable distributions in `plugin_env`

        Example usage::

            distributions, errors = working_set.find_plugins(
                Environment(plugin_dirlist)
            )
            # add plugins+libs to sys.path
            map(working_set.add, distributions)
            # display errors
            print('Could not load', errors)

        The `plugin_env` should be an ``Environment`` instance that contains
        only distributions that are in the project's "plugin directory" or
        directories. The `full_env`, if supplied, should be an ``Environment``
        contains all currently-available distributions.  If `full_env` is not
        supplied, one is created automatically from the ``WorkingSet`` this
        method is called on, which will typically mean that every directory on
        ``sys.path`` will be scanned for distributions.

        `installer` is a standard installer callback as used by the
        ``resolve()`` method. The `fallback` flag indicates whether we should
        attempt to resolve older versions of a plugin if the newest version
        cannot be resolved.

        This method returns a 2-tuple: (`distributions`, `error_info`), where
        `distributions` is a list of the distributions found in `plugin_env`
        that were loadable, along with any other distributions that are needed
        to resolve their dependencies.  `error_info` is a dictionary mapping
        unloadable plugin distributions to an exception instance describing the
        error that occurred. Usually this will be a ``DistributionNotFound`` or
        ``VersionConflict`` instance.
        """

        plugin_projects = list(plugin_env)
        # scan project names in alphabetic order
        plugin_projects.sort()

        error_info: dict[Distribution, Exception] = {}
        distributions: dict[Distribution, Exception | None] = {}

        if full_env is None:
            env = Environment(self.entries)
            env += plugin_env
        else:
            env = full_env + plugin_env

        shadow_set = self.__class__([])
        # put all our entries in shadow_set
        list(map(shadow_set.add, self))

        for project_name in plugin_projects:
            for dist in plugin_env[project_name]:
                req = [dist.as_requirement()]

                try:
                    resolvees = shadow_set.resolve(req, env, installer)

                except ResolutionError as v:
                    # save error info
                    error_info[dist] = v
                    if fallback:
                        # try the next older version of project
                        continue
                    else:
                        # give up on this project, keep going
                        break

                else:
                    list(map(shadow_set.add, resolvees))
                    distributions.update(dict.fromkeys(resolvees))

                    # success, no need to try any more versions of this project
                    break

        sorted_distributions = list(distributions)
        sorted_distributions.sort()

        return sorted_distributions, error_info

    def require(self, *requirements: _NestedStr):
        """Ensure that distributions matching `requirements` are activated

        `requirements` must be a string or a (possibly-nested) sequence
        thereof, specifying the distributions and versions required.  The
        return value is a sequence of the distributions that needed to be
        activated to fulfill the requirements; all relevant distributions are
        included, even if they were already activated in this working set.
        """
        needed = self.resolve(parse_requirements(requirements))

        for dist in needed:
            self.add(dist)

        return needed

    def subscribe(
        self, callback: Callable[[Distribution], object], existing: bool = True
    ):
        """Invoke `callback` for all distributions

        If `existing=True` (default),
        call on all existing ones, as well.
        """
        if callback in self.callbacks:
            return
        self.callbacks.append(callback)
        if not existing:
            return
        for dist in self:
            callback(dist)

    def _added_new(self, dist):
        for callback in self.callbacks:
            callback(dist)

    def __getstate__(self):
        return (
            self.entries[:],
            self.entry_keys.copy(),
            self.by_key.copy(),
            self.normalized_to_canonical_keys.copy(),
            self.callbacks[:],
        )

    def __setstate__(self, e_k_b_n_c):
        entries, keys, by_key, normalized_to_canonical_keys, callbacks = e_k_b_n_c
        self.entries = entries[:]
        self.entry_keys = keys.copy()
        self.by_key = by_key.copy()
        self.normalized_to_canonical_keys = normalized_to_canonical_keys.copy()
        self.callbacks = callbacks[:]


class _ReqExtras(Dict["Requirement", Tuple[str, ...]]):
    """
    Map each requirement to the extras that demanded it.
    """

    def markers_pass(self, req: Requirement, extras: tuple[str, ...] | None = None):
        """
        Evaluate markers for req against each extra that
        demanded it.

        Return False if the req has a marker and fails
        evaluation. Otherwise, return True.
        """
        extra_evals = (
            req.marker.evaluate({'extra': extra})
            for extra in self.get(req, ()) + (extras or (None,))
        )
        return not req.marker or any(extra_evals)


class Environment:
    """Searchable snapshot of distributions on a search path"""

    def __init__(
        self,
        search_path: Iterable[str] | None = None,
        platform: str | None = get_supported_platform(),
        python: str | None = PY_MAJOR,
    ):
        """Snapshot distributions available on a search path

        Any distributions found on `search_path` are added to the environment.
        `search_path` should be a sequence of ``sys.path`` items.  If not
        supplied, ``sys.path`` is used.

        `platform` is an optional string specifying the name of the platform
        that platform-specific distributions must be compatible with.  If
        unspecified, it defaults to the current platform.  `python` is an
        optional string naming the desired version of Python (e.g. ``'3.6'``);
        it defaults to the current version.

        You may explicitly set `platform` (and/or `python`) to ``None`` if you
        wish to map *all* distributions, not just those compatible with the
        running platform or Python version.
        """
        self._distmap = {}
        self.platform = platform
        self.python = python
        self.scan(search_path)

    def can_add(self, dist: Distribution):
        """Is distribution `dist` acceptable for this environment?

        The distribution must match the platform and python version
        requirements specified when this environment was created, or False
        is returned.
        """
        py_compat = (
            self.python is None
            or dist.py_version is None
            or dist.py_version == self.python
        )
        return py_compat and compatible_platforms(dist.platform, self.platform)

    def remove(self, dist: Distribution):
        """Remove `dist` from the environment"""
        self._distmap[dist.key].remove(dist)

    def scan(self, search_path: Iterable[str] | None = None):
        """Scan `search_path` for distributions usable in this environment

        Any distributions found are added to the environment.
        `search_path` should be a sequence of ``sys.path`` items.  If not
        supplied, ``sys.path`` is used.  Only distributions conforming to
        the platform/python version defined at initialization are added.
        """
        if search_path is None:
            search_path = sys.path

        for item in search_path:
            for dist in find_distributions(item):
                self.add(dist)

    def __getitem__(self, project_name: str) -> list[Distribution]:
        """Return a newest-to-oldest list of distributions for `project_name`

        Uses case-insensitive `project_name` comparison, assuming all the
        project's distributions use their project's name converted to all
        lowercase as their key.

        """
        distribution_key = project_name.lower()
        return self._distmap.get(distribution_key, [])

    def add(self, dist: Distribution):
        """Add `dist` if we ``can_add()`` it and it has not already been added"""
        if self.can_add(dist) and dist.has_version():
            dists = self._distmap.setdefault(dist.key, [])
            if dist not in dists:
                dists.append(dist)
                dists.sort(key=operator.attrgetter('hashcmp'), reverse=True)

    @overload
    def best_match(
        self,
        req: Requirement,
        working_set: WorkingSet,
        installer: _InstallerTypeT[_DistributionT],
        replace_conflicting: bool = False,
    ) -> _DistributionT: ...
    @overload
    def best_match(
        self,
        req: Requirement,
        working_set: WorkingSet,
        installer: _InstallerType | None = None,
        replace_conflicting: bool = False,
    ) -> Distribution | None: ...
    def best_match(
        self,
        req: Requirement,
        working_set: WorkingSet,
        installer: _InstallerType | None | _InstallerTypeT[_DistributionT] = None,
        replace_conflicting: bool = False,
    ) -> Distribution | None:
        """Find distribution best matching `req` and usable on `working_set`

        This calls the ``find(req)`` method of the `working_set` to see if a
        suitable distribution is already active.  (This may raise
        ``VersionConflict`` if an unsuitable version of the project is already
        active in the specified `working_set`.)  If a suitable distribution
        isn't active, this method returns the newest distribution in the
        environment that meets the ``Requirement`` in `req`.  If no suitable
        distribution is found, and `installer` is supplied, then the result of
        calling the environment's ``obtain(req, installer)`` method will be
        returned.
        """
        try:
            dist = working_set.find(req)
        except VersionConflict:
            if not replace_conflicting:
                raise
            dist = None
        if dist is not None:
            return dist
        for dist in self[req.key]:
            if dist in req:
                return dist
        # try to download/install
        return self.obtain(req, installer)

    @overload
    def obtain(
        self,
        requirement: Requirement,
        installer: _InstallerTypeT[_DistributionT],
    ) -> _DistributionT: ...
    @overload
    def obtain(
        self,
        requirement: Requirement,
        installer: Callable[[Requirement], None] | None = None,
    ) -> None: ...
    @overload
    def obtain(
        self,
        requirement: Requirement,
        installer: _InstallerType | None = None,
    ) -> Distribution | None: ...
    def obtain(
        self,
        requirement: Requirement,
        installer: Callable[[Requirement], None]
        | _InstallerType
        | None
        | _InstallerTypeT[_DistributionT] = None,
    ) -> Distribution | None:
        """Obtain a distribution matching `requirement` (e.g. via download)

        Obtain a distro that matches requirement (e.g. via download).  In the
        base ``Environment`` class, this routine just returns
        ``installer(requirement)``, unless `installer` is None, in which case
        None is returned instead.  This method is a hook that allows subclasses
        to attempt other ways of obtaining a distribution before falling back
        to the `installer` argument."""
        return installer(requirement) if installer else None

    def __iter__(self) -> Iterator[str]:
        """Yield the unique project names of the available distributions"""
        for key in self._distmap.keys():
            if self[key]:
                yield key

    def __iadd__(self, other: Distribution | Environment):
        """In-place addition of a distribution or environment"""
        if isinstance(other, Distribution):
            self.add(other)
        elif isinstance(other, Environment):
            for project in other:
                for dist in other[project]:
                    self.add(dist)
        else:
            raise TypeError("Can't add %r to environment" % (other,))
        return self

    def __add__(self, other: Distribution | Environment):
        """Add an environment or distribution to an environment"""
        new = self.__class__([], platform=None, python=None)
        for env in self, other:
            new += env
        return new


# XXX backward compatibility
AvailableDistributions = Environment


class ExtractionError(RuntimeError):
    """An error occurred extracting a resource

    The following attributes are available from instances of this exception:

    manager
        The resource manager that raised this exception

    cache_path
        The base directory for resource extraction

    original_error
        The exception instance that caused extraction to fail
    """

    manager: ResourceManager
    cache_path: str
    original_error: BaseException | None


class ResourceManager:
    """Manage resource extraction and packages"""

    extraction_path: str | None = None

    def __init__(self):
        self.cached_files = {}

    def resource_exists(self, package_or_requirement: _PkgReqType, resource_name: str):
        """Does the named resource exist?"""
        return get_provider(package_or_requirement).has_resource(resource_name)

    def resource_isdir(self, package_or_requirement: _PkgReqType, resource_name: str):
        """Is the named resource an existing directory?"""
        return get_provider(package_or_requirement).resource_isdir(resource_name)

    def resource_filename(
        self, package_or_requirement: _PkgReqType, resource_name: str
    ):
        """Return a true filesystem path for specified resource"""
        return get_provider(package_or_requirement).get_resource_filename(
            self, resource_name
        )

    def resource_stream(self, package_or_requirement: _PkgReqType, resource_name: str):
        """Return a readable file-like object for specified resource"""
        return get_provider(package_or_requirement).get_resource_stream(
            self, resource_name
        )

    def resource_string(
        self, package_or_requirement: _PkgReqType, resource_name: str
    ) -> bytes:
        """Return specified resource as :obj:`bytes`"""
        return get_provider(package_or_requirement).get_resource_string(
            self, resource_name
        )

    def resource_listdir(self, package_or_requirement: _PkgReqType, resource_name: str):
        """List the contents of the named resource directory"""
        return get_provider(package_or_requirement).resource_listdir(resource_name)

    def extraction_error(self) -> NoReturn:
        """Give an error message for problems extracting file(s)"""

        old_exc = sys.exc_info()[1]
        cache_path = self.extraction_path or get_default_cache()

        tmpl = textwrap.dedent(
            """
            Can't extract file(s) to egg cache

            The following error occurred while trying to extract file(s)
            to the Python egg cache:

              {old_exc}

            The Python egg cache directory is currently set to:

              {cache_path}

            Perhaps your account does not have write access to this directory?
            You can change the cache directory by setting the PYTHON_EGG_CACHE
            environment variable to point to an accessible directory.
            """
        ).lstrip()
        err = ExtractionError(tmpl.format(**locals()))
        err.manager = self
        err.cache_path = cache_path
        err.original_error = old_exc
        raise err

    def get_cache_path(self, archive_name: str, names: Iterable[StrPath] = ()):
        """Return absolute location in cache for `archive_name` and `names`

        The parent directory of the resulting path will be created if it does
        not already exist.  `archive_name` should be the base filename of the
        enclosing egg (which may not be the name of the enclosing zipfile!),
        including its ".egg" extension.  `names`, if provided, should be a
        sequence of path name parts "under" the egg's extraction location.

        This method should only be called by resource providers that need to
        obtain an extraction location, and only for names they intend to
        extract, as it tracks the generated names for possible cleanup later.
        """
        extract_path = self.extraction_path or get_default_cache()
        target_path = os.path.join(extract_path, archive_name + '-tmp', *names)
        try:
            _bypass_ensure_directory(target_path)
        except Exception:
            self.extraction_error()

        self._warn_unsafe_extraction_path(extract_path)

        self.cached_files[target_path] = True
        return target_path

    @staticmethod
    def _warn_unsafe_extraction_path(path):
        """
        If the default extraction path is overridden and set to an insecure
        location, such as /tmp, it opens up an opportunity for an attacker to
        replace an extracted file with an unauthorized payload. Warn the user
        if a known insecure location is used.

        See Distribute #375 for more details.
        """
        if os.name == 'nt' and not path.startswith(os.environ['windir']):
            # On Windows, permissions are generally restrictive by default
            #  and temp directories are not writable by other users, so
            #  bypass the warning.
            return
        mode = os.stat(path).st_mode
        if mode & stat.S_IWOTH or mode & stat.S_IWGRP:
            msg = (
                "Extraction path is writable by group/others "
                "and vulnerable to attack when "
                "used with get_resource_filename ({path}). "
                "Consider a more secure "
                "location (set with .set_extraction_path or the "
                "PYTHON_EGG_CACHE environment variable)."
            ).format(**locals())
            warnings.warn(msg, UserWarning)

    def postprocess(self, tempname: StrOrBytesPath, filename: StrOrBytesPath):
        """Perform any platform-specific postprocessing of `tempname`

        This is where Mac header rewrites should be done; other platforms don't
        have anything special they should do.

        Resource providers should call this method ONLY after successfully
        extracting a compressed resource.  They must NOT call it on resources
        that are already in the filesystem.

        `tempname` is the current (temporary) name of the file, and `filename`
        is the name it will be renamed to by the caller after this routine
        returns.
        """

        if os.name == 'posix':
            # Make the resource executable
            mode = ((os.stat(tempname).st_mode) | 0o555) & 0o7777
            os.chmod(tempname, mode)

    def set_extraction_path(self, path: str):
        """Set the base path where resources will be extracted to, if needed.

        If you do not call this routine before any extractions take place, the
        path defaults to the return value of ``get_default_cache()``.  (Which
        is based on the ``PYTHON_EGG_CACHE`` environment variable, with various
        platform-specific fallbacks.  See that routine's documentation for more
        details.)

        Resources are extracted to subdirectories of this path based upon
        information given by the ``IResourceProvider``.  You may set this to a
        temporary directory, but then you must call ``cleanup_resources()`` to
        delete the extracted files when done.  There is no guarantee that
        ``cleanup_resources()`` will be able to remove all extracted files.

        (Note: you may not change the extraction path for a given resource
        manager once resources have been extracted, unless you first call
        ``cleanup_resources()``.)
        """
        if self.cached_files:
            raise ValueError("Can't change extraction path, files already extracted")

        self.extraction_path = path

    def cleanup_resources(self, force: bool = False) -> list[str]:
        """
        Delete all extracted resource files and directories, returning a list
        of the file and directory names that could not be successfully removed.
        This function does not have any concurrency protection, so it should
        generally only be called when the extraction path is a temporary
        directory exclusive to a single process.  This method is not
        automatically called; you must call it explicitly or register it as an
        ``atexit`` function if you wish to ensure cleanup of a temporary
        directory used for extractions.
        """
        # XXX
        return []


def get_default_cache() -> str:
    """
    Return the ``PYTHON_EGG_CACHE`` environment variable
    or a platform-relevant user cache dir for an app
    named "Python-Eggs".
    """
    return os.environ.get('PYTHON_EGG_CACHE') or _user_cache_dir(appname='Python-Eggs')


def safe_name(name: str):
    """Convert an arbitrary string to a standard distribution name

    Any runs of non-alphanumeric/. characters are replaced with a single '-'.
    """
    return re.sub('[^A-Za-z0-9.]+', '-', name)


def safe_version(version: str):
    """
    Convert an arbitrary string to a standard version string
    """
    try:
        # normalize the version
        return str(_packaging_version.Version(version))
    except _packaging_version.InvalidVersion:
        version = version.replace(' ', '.')
        return re.sub('[^A-Za-z0-9.]+', '-', version)


def _forgiving_version(version):
    """Fallback when ``safe_version`` is not safe enough
    >>> parse_version(_forgiving_version('0.23ubuntu1'))
    <Version('0.23.dev0+sanitized.ubuntu1')>
    >>> parse_version(_forgiving_version('0.23-'))
    <Version('0.23.dev0+sanitized')>
    >>> parse_version(_forgiving_version('0.-_'))
    <Version('0.dev0+sanitized')>
    >>> parse_version(_forgiving_version('42.+?1'))
    <Version('42.dev0+sanitized.1')>
    >>> parse_version(_forgiving_version('hello world'))
    <Version('0.dev0+sanitized.hello.world')>
    """
    version = version.replace(' ', '.')
    match = _PEP440_FALLBACK.search(version)
    if match:
        safe = match["safe"]
        rest = version[len(safe) :]
    else:
        safe = "0"
        rest = version
    local = f"sanitized.{_safe_segment(rest)}".strip(".")
    return f"{safe}.dev0+{local}"


def _safe_segment(segment):
    """Convert an arbitrary string into a safe segment"""
    segment = re.sub('[^A-Za-z0-9.]+', '-', segment)
    segment = re.sub('-[^A-Za-z0-9]+', '-', segment)
    return re.sub(r'\.[^A-Za-z0-9]+', '.', segment).strip(".-")


def safe_extra(extra: str):
    """Convert an arbitrary string to a standard 'extra' name

    Any runs of non-alphanumeric characters are replaced with a single '_',
    and the result is always lowercased.
    """
    return re.sub('[^A-Za-z0-9.-]+', '_', extra).lower()


def to_filename(name: str):
    """Convert a project or version name to its filename-escaped form

    Any '-' characters are currently replaced with '_'.
    """
    return name.replace('-', '_')


def invalid_marker(text: str):
    """
    Validate text as a PEP 508 environment marker; return an exception
    if invalid or False otherwise.
    """
    try:
        evaluate_marker(text)
    except SyntaxError as e:
        e.filename = None
        e.lineno = None
        return e
    return False


def evaluate_marker(text: str, extra: str | None = None) -> bool:
    """
    Evaluate a PEP 508 environment marker.
    Return a boolean indicating the marker result in this environment.
    Raise SyntaxError if marker is invalid.

    This implementation uses the 'pyparsing' module.
    """
    try:
        marker = _packaging_markers.Marker(text)
        return marker.evaluate()
    except _packaging_markers.InvalidMarker as e:
        raise SyntaxError(e) from e


class NullProvider:
    """Try to implement resources and metadata for arbitrary PEP 302 loaders"""

    egg_name: str | None = None
    egg_info: str | None = None
    loader: _LoaderProtocol | None = None

    def __init__(self, module: _ModuleLike):
        self.loader = getattr(module, '__loader__', None)
        self.module_path = os.path.dirname(getattr(module, '__file__', ''))

    def get_resource_filename(self, manager: ResourceManager, resource_name: str):
        return self._fn(self.module_path, resource_name)

    def get_resource_stream(self, manager: ResourceManager, resource_name: str):
        return io.BytesIO(self.get_resource_string(manager, resource_name))

    def get_resource_string(
        self, manager: ResourceManager, resource_name: str
    ) -> bytes:
        return self._get(self._fn(self.module_path, resource_name))

    def has_resource(self, resource_name: str):
        return self._has(self._fn(self.module_path, resource_name))

    def _get_metadata_path(self, name):
        return self._fn(self.egg_info, name)

    def has_metadata(self, name: str) -> bool:
        if not self.egg_info:
            return False

        path = self._get_metadata_path(name)
        return self._has(path)

    def get_metadata(self, name: str):
        if not self.egg_info:
            return ""
        path = self._get_metadata_path(name)
        value = self._get(path)
        try:
            return value.decode('utf-8')
        except UnicodeDecodeError as exc:
            # Include the path in the error message to simplify
            # troubleshooting, and without changing the exception type.
            exc.reason += ' in {} file at path: {}'.format(name, path)
            raise

    def get_metadata_lines(self, name: str) -> Iterator[str]:
        return yield_lines(self.get_metadata(name))

    def resource_isdir(self, resource_name: str):
        return self._isdir(self._fn(self.module_path, resource_name))

    def metadata_isdir(self, name: str) -> bool:
        return bool(self.egg_info and self._isdir(self._fn(self.egg_info, name)))

    def resource_listdir(self, resource_name: str):
        return self._listdir(self._fn(self.module_path, resource_name))

    def metadata_listdir(self, name: str) -> list[str]:
        if self.egg_info:
            return self._listdir(self._fn(self.egg_info, name))
        return []

    def run_script(self, script_name: str, namespace: dict[str, Any]):
        script = 'scripts/' + script_name
        if not self.has_metadata(script):
            raise ResolutionError(
                "Script {script!r} not found in metadata at {self.egg_info!r}".format(
                    **locals()
                ),
            )

        script_text = self.get_metadata(script).replace('\r\n', '\n')
        script_text = script_text.replace('\r', '\n')
        script_filename = self._fn(self.egg_info, script)
        namespace['__file__'] = script_filename
        if os.path.exists(script_filename):
            source = _read_utf8_with_fallback(script_filename)
            code = compile(source, script_filename, 'exec')
            exec(code, namespace, namespace)
        else:
            from linecache import cache

            cache[script_filename] = (
                len(script_text),
                0,
                script_text.split('\n'),
                script_filename,
            )
            script_code = compile(script_text, script_filename, 'exec')
            exec(script_code, namespace, namespace)

    def _has(self, path) -> bool:
        raise NotImplementedError(
            "Can't perform this operation for unregistered loader type"
        )

    def _isdir(self, path) -> bool:
        raise NotImplementedError(
            "Can't perform this operation for unregistered loader type"
        )

    def _listdir(self, path) -> list[str]:
        raise NotImplementedError(
            "Can't perform this operation for unregistered loader type"
        )

    def _fn(self, base: str | None, resource_name: str):
        if base is None:
            raise TypeError(
                "`base` parameter in `_fn` is `None`. Either override this method or check the parameter first."
            )
        self._validate_resource_path(resource_name)
        if resource_name:
            return os.path.join(base, *resource_name.split('/'))
        return base

    @staticmethod
    def _validate_resource_path(path):
        """
        Validate the resource paths according to the docs.
        https://setuptools.pypa.io/en/latest/pkg_resources.html#basic-resource-access

        >>> warned = getfixture('recwarn')
        >>> warnings.simplefilter('always')
        >>> vrp = NullProvider._validate_resource_path
        >>> vrp('foo/bar.txt')
        >>> bool(warned)
        False
        >>> vrp('../foo/bar.txt')
        >>> bool(warned)
        True
        >>> warned.clear()
        >>> vrp('/foo/bar.txt')
        >>> bool(warned)
        True
        >>> vrp('foo/../../bar.txt')
        >>> bool(warned)
        True
        >>> warned.clear()
        >>> vrp('foo/f../bar.txt')
        >>> bool(warned)
        False

        Windows path separators are straight-up disallowed.
        >>> vrp(r'\\foo/bar.txt')
        Traceback (most recent call last):
        ...
        ValueError: Use of .. or absolute path in a resource path \
is not allowed.

        >>> vrp(r'C:\\foo/bar.txt')
        Traceback (most recent call last):
        ...
        ValueError: Use of .. or absolute path in a resource path \
is not allowed.

        Blank values are allowed

        >>> vrp('')
        >>> bool(warned)
        False

        Non-string values are not.

        >>> vrp(None)
        Traceback (most recent call last):
        ...
        AttributeError: ...
        """
        invalid = (
            os.path.pardir in path.split(posixpath.sep)
            or posixpath.isabs(path)
            or ntpath.isabs(path)
            or path.startswith("\\")
        )
        if not invalid:
            return

        msg = "Use of .. or absolute path in a resource path is not allowed."

        # Aggressively disallow Windows absolute paths
        if (path.startswith("\\") or ntpath.isabs(path)) and not posixpath.isabs(path):
            raise ValueError(msg)

        # for compatibility, warn; in future
        # raise ValueError(msg)
        issue_warning(
            msg[:-1] + " and will raise exceptions in a future release.",
            DeprecationWarning,
        )

    def _get(self, path) -> bytes:
        if hasattr(self.loader, 'get_data') and self.loader:
            # Already checked get_data exists
            return self.loader.get_data(path)  # type: ignore[attr-defined]
        raise NotImplementedError(
            "Can't perform this operation for loaders without 'get_data()'"
        )


register_loader_type(object, NullProvider)


def _parents(path):
    """
    yield all parents of path including path
    """
    last = None
    while path != last:
        yield path
        last = path
        path, _ = os.path.split(path)


class EggProvider(NullProvider):
    """Provider based on a virtual filesystem"""

    def __init__(self, module: _ModuleLike):
        super().__init__(module)
        self._setup_prefix()

    def _setup_prefix(self):
        # Assume that metadata may be nested inside a "basket"
        # of multiple eggs and use module_path instead of .archive.
        eggs = filter(_is_egg_path, _parents(self.module_path))
        egg = next(eggs, None)
        egg and self._set_egg(egg)

    def _set_egg(self, path: str):
        self.egg_name = os.path.basename(path)
        self.egg_info = os.path.join(path, 'EGG-INFO')
        self.egg_root = path


class DefaultProvider(EggProvider):
    """Provides access to package resources in the filesystem"""

    def _has(self, path) -> bool:
        return os.path.exists(path)

    def _isdir(self, path) -> bool:
        return os.path.isdir(path)

    def _listdir(self, path):
        return os.listdir(path)

    def get_resource_stream(self, manager: object, resource_name: str):
        return open(self._fn(self.module_path, resource_name), 'rb')

    def _get(self, path) -> bytes:
        with open(path, 'rb') as stream:
            return stream.read()

    @classmethod
    def _register(cls):
        loader_names = (
            'SourceFileLoader',
            'SourcelessFileLoader',
        )
        for name in loader_names:
            loader_cls = getattr(importlib.machinery, name, type(None))
            register_loader_type(loader_cls, cls)


DefaultProvider._register()


class EmptyProvider(NullProvider):
    """Provider that returns nothing for all requests"""

    # A special case, we don't want all Providers inheriting from NullProvider to have a potentially None module_path
    module_path: str | None = None  # type: ignore[assignment]

    _isdir = _has = lambda self, path: False

    def _get(self, path) -> bytes:
        return b''

    def _listdir(self, path):
        return []

    def __init__(self):
        pass


empty_provider = EmptyProvider()


class ZipManifests(Dict[str, "MemoizedZipManifests.manifest_mod"]):
    """
    zip manifest builder
    """

    # `path` could be `StrPath | IO[bytes]` but that violates the LSP for `MemoizedZipManifests.load`
    @classmethod
    def build(cls, path: str):
        """
        Build a dictionary similar to the zipimport directory
        caches, except instead of tuples, store ZipInfo objects.

        Use a platform-specific path separator (os.sep) for the path keys
        for compatibility with pypy on Windows.
        """
        with zipfile.ZipFile(path) as zfile:
            items = (
                (
                    name.replace('/', os.sep),
                    zfile.getinfo(name),
                )
                for name in zfile.namelist()
            )
            return dict(items)

    load = build


class MemoizedZipManifests(ZipManifests):
    """
    Memoized zipfile manifests.
    """

    class manifest_mod(NamedTuple):
        manifest: dict[str, zipfile.ZipInfo]
        mtime: float

    def load(self, path: str) -> dict[str, zipfile.ZipInfo]:  # type: ignore[override] # ZipManifests.load is a classmethod
        """
        Load a manifest at path or return a suitable manifest already loaded.
        """
        path = os.path.normpath(path)
        mtime = os.stat(path).st_mtime

        if path not in self or self[path].mtime != mtime:
            manifest = self.build(path)
            self[path] = self.manifest_mod(manifest, mtime)

        return self[path].manifest


class ZipProvider(EggProvider):
    """Resource support for zips and eggs"""

    eagers: list[str] | None = None
    _zip_manifests = MemoizedZipManifests()
    # ZipProvider's loader should always be a zipimporter or equivalent
    loader: zipimport.zipimporter

    def __init__(self, module: _ZipLoaderModule):
        super().__init__(module)
        self.zip_pre = self.loader.archive + os.sep

    def _zipinfo_name(self, fspath):
        # Convert a virtual filename (full path to file) into a zipfile subpath
        # usable with the zipimport directory cache for our target archive
        fspath = fspath.rstrip(os.sep)
        if fspath == self.loader.archive:
            return ''
        if fspath.startswith(self.zip_pre):
            return fspath[len(self.zip_pre) :]
        raise AssertionError("%s is not a subpath of %s" % (fspath, self.zip_pre))

    def _parts(self, zip_path):
        # Convert a zipfile subpath into an egg-relative path part list.
        # pseudo-fs path
        fspath = self.zip_pre + zip_path
        if fspath.startswith(self.egg_root + os.sep):
            return fspath[len(self.egg_root) + 1 :].split(os.sep)
        raise AssertionError("%s is not a subpath of %s" % (fspath, self.egg_root))

    @property
    def zipinfo(self):
        return self._zip_manifests.load(self.loader.archive)

    def get_resource_filename(self, manager: ResourceManager, resource_name: str):
        if not self.egg_name:
            raise NotImplementedError(
                "resource_filename() only supported for .egg, not .zip"
            )
        # no need to lock for extraction, since we use temp names
        zip_path = self._resource_to_zip(resource_name)
        eagers = self._get_eager_resources()
        if '/'.join(self._parts(zip_path)) in eagers:
            for name in eagers:
                self._extract_resource(manager, self._eager_to_zip(name))
        return self._extract_resource(manager, zip_path)

    @staticmethod
    def _get_date_and_size(zip_stat):
        size = zip_stat.file_size
        # ymdhms+wday, yday, dst
        date_time = zip_stat.date_time + (0, 0, -1)
        # 1980 offset already done
        timestamp = time.mktime(date_time)
        return timestamp, size

    # FIXME: 'ZipProvider._extract_resource' is too complex (12)
    def _extract_resource(self, manager: ResourceManager, zip_path) -> str:  # noqa: C901
        if zip_path in self._index():
            for name in self._index()[zip_path]:
                last = self._extract_resource(manager, os.path.join(zip_path, name))
            # return the extracted directory name
            return os.path.dirname(last)

        timestamp, size = self._get_date_and_size(self.zipinfo[zip_path])

        if not WRITE_SUPPORT:
            raise OSError(
                '"os.rename" and "os.unlink" are not supported on this platform'
            )
        try:
            if not self.egg_name:
                raise OSError(
                    '"egg_name" is empty. This likely means no egg could be found from the "module_path".'
                )
            real_path = manager.get_cache_path(self.egg_name, self._parts(zip_path))

            if self._is_current(real_path, zip_path):
                return real_path

            outf, tmpnam = _mkstemp(
                ".$extract",
                dir=os.path.dirname(real_path),
            )
            os.write(outf, self.loader.get_data(zip_path))
            os.close(outf)
            utime(tmpnam, (timestamp, timestamp))
            manager.postprocess(tmpnam, real_path)

            try:
                rename(tmpnam, real_path)

            except OSError:
                if os.path.isfile(real_path):
                    if self._is_current(real_path, zip_path):
                        # the file became current since it was checked above,
                        #  so proceed.
                        return real_path
                    # Windows, del old file and retry
                    elif os.name == 'nt':
                        unlink(real_path)
                        rename(tmpnam, real_path)
                        return real_path
                raise

        except OSError:
            # report a user-friendly error
            manager.extraction_error()

        return real_path

    def _is_current(self, file_path, zip_path):
        """
        Return True if the file_path is current for this zip_path
        """
        timestamp, size = self._get_date_and_size(self.zipinfo[zip_path])
        if not os.path.isfile(file_path):
            return False
        stat = os.stat(file_path)
        if stat.st_size != size or stat.st_mtime != timestamp:
            return False
        # check that the contents match
        zip_contents = self.loader.get_data(zip_path)
        with open(file_path, 'rb') as f:
            file_contents = f.read()
        return zip_contents == file_contents

    def _get_eager_resources(self):
        if self.eagers is None:
            eagers = []
            for name in ('native_libs.txt', 'eager_resources.txt'):
                if self.has_metadata(name):
                    eagers.extend(self.get_metadata_lines(name))
            self.eagers = eagers
        return self.eagers

    def _index(self):
        try:
            return self._dirindex
        except AttributeError:
            ind = {}
            for path in self.zipinfo:
                parts = path.split(os.sep)
                while parts:
                    parent = os.sep.join(parts[:-1])
                    if parent in ind:
                        ind[parent].append(parts[-1])
                        break
                    else:
                        ind[parent] = [parts.pop()]
            self._dirindex = ind
            return ind

    def _has(self, fspath) -> bool:
        zip_path = self._zipinfo_name(fspath)
        return zip_path in self.zipinfo or zip_path in self._index()

    def _isdir(self, fspath) -> bool:
        return self._zipinfo_name(fspath) in self._index()

    def _listdir(self, fspath):
        return list(self._index().get(self._zipinfo_name(fspath), ()))

    def _eager_to_zip(self, resource_name: str):
        return self._zipinfo_name(self._fn(self.egg_root, resource_name))

    def _resource_to_zip(self, resource_name: str):
        return self._zipinfo_name(self._fn(self.module_path, resource_name))


register_loader_type(zipimport.zipimporter, ZipProvider)


class FileMetadata(EmptyProvider):
    """Metadata handler for standalone PKG-INFO files

    Usage::

        metadata = FileMetadata("/path/to/PKG-INFO")

    This provider rejects all data and metadata requests except for PKG-INFO,
    which is treated as existing, and will be the contents of the file at
    the provided location.
    """

    def __init__(self, path: StrPath):
        self.path = path

    def _get_metadata_path(self, name):
        return self.path

    def has_metadata(self, name: str) -> bool:
        return name == 'PKG-INFO' and os.path.isfile(self.path)

    def get_metadata(self, name: str):
        if name != 'PKG-INFO':
            raise KeyError("No metadata except PKG-INFO is available")

        with open(self.path, encoding='utf-8', errors="replace") as f:
            metadata = f.read()
        self._warn_on_replacement(metadata)
        return metadata

    def _warn_on_replacement(self, metadata):
        replacement_char = '�'
        if replacement_char in metadata:
            tmpl = "{self.path} could not be properly decoded in UTF-8"
            msg = tmpl.format(**locals())
            warnings.warn(msg)

    def get_metadata_lines(self, name: str) -> Iterator[str]:
        return yield_lines(self.get_metadata(name))


class PathMetadata(DefaultProvider):
    """Metadata provider for egg directories

    Usage::

        # Development eggs:

        egg_info = "/path/to/PackageName.egg-info"
        base_dir = os.path.dirname(egg_info)
        metadata = PathMetadata(base_dir, egg_info)
        dist_name = os.path.splitext(os.path.basename(egg_info))[0]
        dist = Distribution(basedir, project_name=dist_name, metadata=metadata)

        # Unpacked egg directories:

        egg_path = "/path/to/PackageName-ver-pyver-etc.egg"
        metadata = PathMetadata(egg_path, os.path.join(egg_path,'EGG-INFO'))
        dist = Distribution.from_filename(egg_path, metadata=metadata)
    """

    def __init__(self, path: str, egg_info: str):
        self.module_path = path
        self.egg_info = egg_info


class EggMetadata(ZipProvider):
    """Metadata provider for .egg files"""

    def __init__(self, importer: zipimport.zipimporter):
        """Create a metadata provider from a zipimporter"""

        self.zip_pre = importer.archive + os.sep
        self.loader = importer
        if importer.prefix:
            self.module_path = os.path.join(importer.archive, importer.prefix)
        else:
            self.module_path = importer.archive
        self._setup_prefix()


_distribution_finders: dict[type, _DistFinderType[Any]] = _declare_state(
    'dict', '_distribution_finders', {}
)


def register_finder(importer_type: type[_T], distribution_finder: _DistFinderType[_T]):
    """Register `distribution_finder` to find distributions in sys.path items

    `importer_type` is the type or class of a PEP 302 "Importer" (sys.path item
    handler), and `distribution_finder` is a callable that, passed a path
    item and the importer instance, yields ``Distribution`` instances found on
    that path item.  See ``pkg_resources.find_on_path`` for an example."""
    _distribution_finders[importer_type] = distribution_finder


def find_distributions(path_item: str, only: bool = False):
    """Yield distributions accessible via `path_item`"""
    importer = get_importer(path_item)
    finder = _find_adapter(_distribution_finders, importer)
    return finder(importer, path_item, only)


def find_eggs_in_zip(
    importer: zipimport.zipimporter, path_item: str, only: bool = False
) -> Iterator[Distribution]:
    """
    Find eggs in zip files; possibly multiple nested eggs.
    """
    if importer.archive.endswith('.whl'):
        # wheels are not supported with this finder
        # they don't have PKG-INFO metadata, and won't ever contain eggs
        return
    metadata = EggMetadata(importer)
    if metadata.has_metadata('PKG-INFO'):
        yield Distribution.from_filename(path_item, metadata=metadata)
    if only:
        # don't yield nested distros
        return
    for subitem in metadata.resource_listdir(''):
        if _is_egg_path(subitem):
            subpath = os.path.join(path_item, subitem)
            dists = find_eggs_in_zip(zipimport.zipimporter(subpath), subpath)
            yield from dists
        elif subitem.lower().endswith(('.dist-info', '.egg-info')):
            subpath = os.path.join(path_item, subitem)
            submeta = EggMetadata(zipimport.zipimporter(subpath))
            submeta.egg_info = subpath
            yield Distribution.from_location(path_item, subitem, submeta)


register_finder(zipimport.zipimporter, find_eggs_in_zip)


def find_nothing(
    importer: object | None, path_item: str | None, only: bool | None = False
):
    return ()


register_finder(object, find_nothing)


def find_on_path(importer: object | None, path_item, only=False):
    """Yield distributions accessible on a sys.path directory"""
    path_item = _normalize_cached(path_item)

    if _is_unpacked_egg(path_item):
        yield Distribution.from_filename(
            path_item,
            metadata=PathMetadata(path_item, os.path.join(path_item, 'EGG-INFO')),
        )
        return

    entries = (os.path.join(path_item, child) for child in safe_listdir(path_item))

    # scan for .egg and .egg-info in directory
    for entry in sorted(entries):
        fullpath = os.path.join(path_item, entry)
        factory = dist_factory(path_item, entry, only)
        yield from factory(fullpath)


def dist_factory(path_item, entry, only):
    """Return a dist_factory for the given entry."""
    lower = entry.lower()
    is_egg_info = lower.endswith('.egg-info')
    is_dist_info = lower.endswith('.dist-info') and os.path.isdir(
        os.path.join(path_item, entry)
    )
    is_meta = is_egg_info or is_dist_info
    return (
        distributions_from_metadata
        if is_meta
        else find_distributions
        if not only and _is_egg_path(entry)
        else resolve_egg_link
        if not only and lower.endswith('.egg-link')
        else NoDists()
    )


class NoDists:
    """
    >>> bool(NoDists())
    False

    >>> list(NoDists()('anything'))
    []
    """

    def __bool__(self):
        return False

    def __call__(self, fullpath):
        return iter(())


def safe_listdir(path: StrOrBytesPath):
    """
    Attempt to list contents of path, but suppress some exceptions.
    """
    try:
        return os.listdir(path)
    except (PermissionError, NotADirectoryError):
        pass
    except OSError as e:
        # Ignore the directory if does not exist, not a directory or
        # permission denied
        if e.errno not in (errno.ENOTDIR, errno.EACCES, errno.ENOENT):
            raise
    return ()


def distributions_from_metadata(path: str):
    root = os.path.dirname(path)
    if os.path.isdir(path):
        if len(os.listdir(path)) == 0:
            # empty metadata dir; skip
            return
        metadata: _MetadataType = PathMetadata(root, path)
    else:
        metadata = FileMetadata(path)
    entry = os.path.basename(path)
    yield Distribution.from_location(
        root,
        entry,
        metadata,
        precedence=DEVELOP_DIST,
    )


def non_empty_lines(path):
    """
    Yield non-empty lines from file at path
    """
    for line in _read_utf8_with_fallback(path).splitlines():
        line = line.strip()
        if line:
            yield line


def resolve_egg_link(path):
    """
    Given a path to an .egg-link, resolve distributions
    present in the referenced path.
    """
    referenced_paths = non_empty_lines(path)
    resolved_paths = (
        os.path.join(os.path.dirname(path), ref) for ref in referenced_paths
    )
    dist_groups = map(find_distributions, resolved_paths)
    return next(dist_groups, ())


if hasattr(pkgutil, 'ImpImporter'):
    register_finder(pkgutil.ImpImporter, find_on_path)

register_finder(importlib.machinery.FileFinder, find_on_path)

_namespace_handlers: dict[type, _NSHandlerType[Any]] = _declare_state(
    'dict', '_namespace_handlers', {}
)
_namespace_packages: dict[str | None, list[str]] = _declare_state(
    'dict', '_namespace_packages', {}
)


def register_namespace_handler(
    importer_type: type[_T], namespace_handler: _NSHandlerType[_T]
):
    """Register `namespace_handler` to declare namespace packages

    `importer_type` is the type or class of a PEP 302 "Importer" (sys.path item
    handler), and `namespace_handler` is a callable like this::

        def namespace_handler(importer, path_entry, moduleName, module):
            # return a path_entry to use for child packages

    Namespace handlers are only called if the importer object has already
    agreed that it can handle the relevant path item, and they should only
    return a subpath if the module __path__ does not already contain an
    equivalent subpath.  For an example namespace handler, see
    ``pkg_resources.file_ns_handler``.
    """
    _namespace_handlers[importer_type] = namespace_handler


def _handle_ns(packageName, path_item):
    """Ensure that named package includes a subpath of path_item (if needed)"""

    importer = get_importer(path_item)
    if importer is None:
        return None

    # use find_spec (PEP 451) and fall-back to find_module (PEP 302)
    try:
        spec = importer.find_spec(packageName)
    except AttributeError:
        # capture warnings due to #1111
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            loader = importer.find_module(packageName)
    else:
        loader = spec.loader if spec else None

    if loader is None:
        return None
    module = sys.modules.get(packageName)
    if module is None:
        module = sys.modules[packageName] = types.ModuleType(packageName)
        module.__path__ = []
        _set_parent_ns(packageName)
    elif not hasattr(module, '__path__'):
        raise TypeError("Not a package:", packageName)
    handler = _find_adapter(_namespace_handlers, importer)
    subpath = handler(importer, path_item, packageName, module)
    if subpath is not None:
        path = module.__path__
        path.append(subpath)
        importlib.import_module(packageName)
        _rebuild_mod_path(path, packageName, module)
    return subpath


def _rebuild_mod_path(orig_path, package_name, module: types.ModuleType):
    """
    Rebuild module.__path__ ensuring that all entries are ordered
    corresponding to their sys.path order
    """
    sys_path = [_normalize_cached(p) for p in sys.path]

    def safe_sys_path_index(entry):
        """
        Workaround for #520 and #513.
        """
        try:
            return sys_path.index(entry)
        except ValueError:
            return float('inf')

    def position_in_sys_path(path):
        """
        Return the ordinal of the path based on its position in sys.path
        """
        path_parts = path.split(os.sep)
        module_parts = package_name.count('.') + 1
        parts = path_parts[:-module_parts]
        return safe_sys_path_index(_normalize_cached(os.sep.join(parts)))

    new_path = sorted(orig_path, key=position_in_sys_path)
    new_path = [_normalize_cached(p) for p in new_path]

    if isinstance(module.__path__, list):
        module.__path__[:] = new_path
    else:
        module.__path__ = new_path


def declare_namespace(packageName: str):
    """Declare that package 'packageName' is a namespace package"""

    msg = (
        f"Deprecated call to `pkg_resources.declare_namespace({packageName!r})`.\n"
        "Implementing implicit namespace packages (as specified in PEP 420) "
        "is preferred to `pkg_resources.declare_namespace`. "
        "See https://setuptools.pypa.io/en/latest/references/"
        "keywords.html#keyword-namespace-packages"
    )
    warnings.warn(msg, DeprecationWarning, stacklevel=2)

    _imp.acquire_lock()
    try:
        if packageName in _namespace_packages:
            return

        path: MutableSequence[str] = sys.path
        parent, _, _ = packageName.rpartition('.')

        if parent:
            declare_namespace(parent)
            if parent not in _namespace_packages:
                __import__(parent)
            try:
                path = sys.modules[parent].__path__
            except AttributeError as e:
                raise TypeError("Not a package:", parent) from e

        # Track what packages are namespaces, so when new path items are added,
        # they can be updated
        _namespace_packages.setdefault(parent or None, []).append(packageName)
        _namespace_packages.setdefault(packageName, [])

        for path_item in path:
            # Ensure all the parent's path items are reflected in the child,
            # if they apply
            _handle_ns(packageName, path_item)

    finally:
        _imp.release_lock()


def fixup_namespace_packages(path_item: str, parent: str | None = None):
    """Ensure that previously-declared namespace packages include path_item"""
    _imp.acquire_lock()
    try:
        for package in _namespace_packages.get(parent, ()):
            subpath = _handle_ns(package, path_item)
            if subpath:
                fixup_namespace_packages(subpath, package)
    finally:
        _imp.release_lock()


def file_ns_handler(
    importer: object,
    path_item: StrPath,
    packageName: str,
    module: types.ModuleType,
):
    """Compute an ns-package subpath for a filesystem or zipfile importer"""

    subpath = os.path.join(path_item, packageName.split('.')[-1])
    normalized = _normalize_cached(subpath)
    for item in module.__path__:
        if _normalize_cached(item) == normalized:
            break
    else:
        # Only return the path if it's not already there
        return subpath


if hasattr(pkgutil, 'ImpImporter'):
    register_namespace_handler(pkgutil.ImpImporter, file_ns_handler)

register_namespace_handler(zipimport.zipimporter, file_ns_handler)
register_namespace_handler(importlib.machinery.FileFinder, file_ns_handler)


def null_ns_handler(
    importer: object,
    path_item: str | None,
    packageName: str | None,
    module: _ModuleLike | None,
):
    return None


register_namespace_handler(object, null_ns_handler)


@overload
def normalize_path(filename: StrPath) -> str: ...
@overload
def normalize_path(filename: BytesPath) -> bytes: ...
def normalize_path(filename: StrOrBytesPath):
    """Normalize a file/dir name for comparison purposes"""
    return os.path.normcase(os.path.realpath(os.path.normpath(_cygwin_patch(filename))))


def _cygwin_patch(filename: StrOrBytesPath):  # pragma: nocover
    """
    Contrary to POSIX 2008, on Cygwin, getcwd (3) contains
    symlink components. Using
    os.path.abspath() works around this limitation. A fix in os.getcwd()
    would probably better, in Cygwin even more so, except
    that this seems to be by design...
    """
    return os.path.abspath(filename) if sys.platform == 'cygwin' else filename


if TYPE_CHECKING:
    # https://github.com/python/mypy/issues/16261
    # https://github.com/python/typeshed/issues/6347
    @overload
    def _normalize_cached(filename: StrPath) -> str: ...
    @overload
    def _normalize_cached(filename: BytesPath) -> bytes: ...
    def _normalize_cached(filename: StrOrBytesPath) -> str | bytes: ...
else:

    @functools.lru_cache(maxsize=None)
    def _normalize_cached(filename):
        return normalize_path(filename)


def _is_egg_path(path):
    """
    Determine if given path appears to be an egg.
    """
    return _is_zip_egg(path) or _is_unpacked_egg(path)


def _is_zip_egg(path):
    return (
        path.lower().endswith('.egg')
        and os.path.isfile(path)
        and zipfile.is_zipfile(path)
    )


def _is_unpacked_egg(path):
    """
    Determine if given path appears to be an unpacked egg.
    """
    return path.lower().endswith('.egg') and os.path.isfile(
        os.path.join(path, 'EGG-INFO', 'PKG-INFO')
    )


def _set_parent_ns(packageName):
    parts = packageName.split('.')
    name = parts.pop()
    if parts:
        parent = '.'.join(parts)
        setattr(sys.modules[parent], name, sys.modules[packageName])


MODULE = re.compile(r"\w+(\.\w+)*$").match
EGG_NAME = re.compile(
    r"""
    (?P<name>[^-]+) (
        -(?P<ver>[^-]+) (
            -py(?P<pyver>[^-]+) (
                -(?P<plat>.+)
            )?
        )?
    )?
    """,
    re.VERBOSE | re.IGNORECASE,
).match


class EntryPoint:
    """Object representing an advertised importable object"""

    def __init__(
        self,
        name: str,
        module_name: str,
        attrs: Iterable[str] = (),
        extras: Iterable[str] = (),
        dist: Distribution | None = None,
    ):
        if not MODULE(module_name):
            raise ValueError("Invalid module name", module_name)
        self.name = name
        self.module_name = module_name
        self.attrs = tuple(attrs)
        self.extras = tuple(extras)
        self.dist = dist

    def __str__(self):
        s = "%s = %s" % (self.name, self.module_name)
        if self.attrs:
            s += ':' + '.'.join(self.attrs)
        if self.extras:
            s += ' [%s]' % ','.join(self.extras)
        return s

    def __repr__(self):
        return "EntryPoint.parse(%r)" % str(self)

    @overload
    def load(
        self,
        require: Literal[True] = True,
        env: Environment | None = None,
        installer: _InstallerType | None = None,
    ) -> _ResolvedEntryPoint: ...
    @overload
    def load(
        self,
        require: Literal[False],
        *args: Any,
        **kwargs: Any,
    ) -> _ResolvedEntryPoint: ...
    def load(
        self,
        require: bool = True,
        *args: Environment | _InstallerType | None,
        **kwargs: Environment | _InstallerType | None,
    ) -> _ResolvedEntryPoint:
        """
        Require packages for this EntryPoint, then resolve it.
        """
        if not require or args or kwargs:
            warnings.warn(
                "Parameters to load are deprecated.  Call .resolve and "
                ".require separately.",
                PkgResourcesDeprecationWarning,
                stacklevel=2,
            )
        if require:
            # We could pass `env` and `installer` directly,
            # but keeping `*args` and `**kwargs` for backwards compatibility
            self.require(*args, **kwargs)  # type: ignore
        return self.resolve()

    def resolve(self) -> _ResolvedEntryPoint:
        """
        Resolve the entry point from its module and attrs.
        """
        module = __import__(self.module_name, fromlist=['__name__'], level=0)
        try:
            return functools.reduce(getattr, self.attrs, module)
        except AttributeError as exc:
            raise ImportError(str(exc)) from exc

    def require(
        self,
        env: Environment | None = None,
        installer: _InstallerType | None = None,
    ):
        if not self.dist:
            error_cls = UnknownExtra if self.extras else AttributeError
            raise error_cls("Can't require() without a distribution", self)

        # Get the requirements for this entry point with all its extras and
        # then resolve them. We have to pass `extras` along when resolving so
        # that the working set knows what extras we want. Otherwise, for
        # dist-info distributions, the working set will assume that the
        # requirements for that extra are purely optional and skip over them.
        reqs = self.dist.requires(self.extras)
        items = working_set.resolve(reqs, env, installer, extras=self.extras)
        list(map(working_set.add, items))

    pattern = re.compile(
        r'\s*'
        r'(?P<name>.+?)\s*'
        r'=\s*'
        r'(?P<module>[\w.]+)\s*'
        r'(:\s*(?P<attr>[\w.]+))?\s*'
        r'(?P<extras>\[.*\])?\s*$'
    )

    @classmethod
    def parse(cls, src: str, dist: Distribution | None = None):
        """Parse a single entry point from string `src`

        Entry point syntax follows the form::

            name = some.module:some.attr [extra1, extra2]

        The entry name and module name are required, but the ``:attrs`` and
        ``[extras]`` parts are optional
        """
        m = cls.pattern.match(src)
        if not m:
            msg = "EntryPoint must be in 'name=module:attrs [extras]' format"
            raise ValueError(msg, src)
        res = m.groupdict()
        extras = cls._parse_extras(res['extras'])
        attrs = res['attr'].split('.') if res['attr'] else ()
        return cls(res['name'], res['module'], attrs, extras, dist)

    @classmethod
    def _parse_extras(cls, extras_spec):
        if not extras_spec:
            return ()
        req = Requirement.parse('x' + extras_spec)
        if req.specs:
            raise ValueError
        return req.extras

    @classmethod
    def parse_group(
        cls,
        group: str,
        lines: _NestedStr,
        dist: Distribution | None = None,
    ):
        """Parse an entry point group"""
        if not MODULE(group):
            raise ValueError("Invalid group name", group)
        this: dict[str, Self] = {}
        for line in yield_lines(lines):
            ep = cls.parse(line, dist)
            if ep.name in this:
                raise ValueError("Duplicate entry point", group, ep.name)
            this[ep.name] = ep
        return this

    @classmethod
    def parse_map(
        cls,
        data: str | Iterable[str] | dict[str, str | Iterable[str]],
        dist: Distribution | None = None,
    ):
        """Parse a map of entry point groups"""
        _data: Iterable[tuple[str | None, str | Iterable[str]]]
        if isinstance(data, dict):
            _data = data.items()
        else:
            _data = split_sections(data)
        maps: dict[str, dict[str, Self]] = {}
        for group, lines in _data:
            if group is None:
                if not lines:
                    continue
                raise ValueError("Entry points must be listed in groups")
            group = group.strip()
            if group in maps:
                raise ValueError("Duplicate group name", group)
            maps[group] = cls.parse_group(group, lines, dist)
        return maps


def _version_from_file(lines):
    """
    Given an iterable of lines from a Metadata file, return
    the value of the Version field, if present, or None otherwise.
    """

    def is_version_line(line):
        return line.lower().startswith('version:')

    version_lines = filter(is_version_line, lines)
    line = next(iter(version_lines), '')
    _, _, value = line.partition(':')
    return safe_version(value.strip()) or None


class Distribution:
    """Wrap an actual or potential sys.path entry w/metadata"""

    PKG_INFO = 'PKG-INFO'

    def __init__(
        self,
        location: str | None = None,
        metadata: _MetadataType = None,
        project_name: str | None = None,
        version: str | None = None,
        py_version: str | None = PY_MAJOR,
        platform: str | None = None,
        precedence: int = EGG_DIST,
    ):
        self.project_name = safe_name(project_name or 'Unknown')
        if version is not None:
            self._version = safe_version(version)
        self.py_version = py_version
        self.platform = platform
        self.location = location
        self.precedence = precedence
        self._provider = metadata or empty_provider

    @classmethod
    def from_location(
        cls,
        location: str,
        basename: StrPath,
        metadata: _MetadataType = None,
        **kw: int,  # We could set `precedence` explicitly, but keeping this as `**kw` for full backwards and subclassing compatibility
    ) -> Distribution:
        project_name, version, py_version, platform = [None] * 4
        basename, ext = os.path.splitext(basename)
        if ext.lower() in _distributionImpl:
            cls = _distributionImpl[ext.lower()]

            match = EGG_NAME(basename)
            if match:
                project_name, version, py_version, platform = match.group(
                    'name', 'ver', 'pyver', 'plat'
                )
        return cls(
            location,
            metadata,
            project_name=project_name,
            version=version,
            py_version=py_version,
            platform=platform,
            **kw,
        )._reload_version()

    def _reload_version(self):
        return self

    @property
    def hashcmp(self):
        return (
            self._forgiving_parsed_version,
            self.precedence,
            self.key,
            self.location,
            self.py_version or '',
            self.platform or '',
        )

    def __hash__(self):
        return hash(self.hashcmp)

    def __lt__(self, other: Distribution):
        return self.hashcmp < other.hashcmp

    def __le__(self, other: Distribution):
        return self.hashcmp <= other.hashcmp

    def __gt__(self, other: Distribution):
        return self.hashcmp > other.hashcmp

    def __ge__(self, other: Distribution):
        return self.hashcmp >= other.hashcmp

    def __eq__(self, other: object):
        if not isinstance(other, self.__class__):
            # It's not a Distribution, so they are not equal
            return False
        return self.hashcmp == other.hashcmp

    def __ne__(self, other: object):
        return not self == other

    # These properties have to be lazy so that we don't have to load any
    # metadata until/unless it's actually needed.  (i.e., some distributions
    # may not know their name or version without loading PKG-INFO)

    @property
    def key(self):
        try:
            return self._key
        except AttributeError:
            self._key = key = self.project_name.lower()
            return key

    @property
    def parsed_version(self):
        if not hasattr(self, "_parsed_version"):
            try:
                self._parsed_version = parse_version(self.version)
            except _packaging_version.InvalidVersion as ex:
                info = f"(package: {self.project_name})"
                if hasattr(ex, "add_note"):
                    ex.add_note(info)  # PEP 678
                    raise
                raise _packaging_version.InvalidVersion(f"{str(ex)} {info}") from None

        return self._parsed_version

    @property
    def _forgiving_parsed_version(self):
        try:
            return self.parsed_version
        except _packaging_version.InvalidVersion as ex:
            self._parsed_version = parse_version(_forgiving_version(self.version))

            notes = "\n".join(getattr(ex, "__notes__", []))  # PEP 678
            msg = f"""!!\n\n
            *************************************************************************
            {str(ex)}\n{notes}

            This is a long overdue deprecation.
            For the time being, `pkg_resources` will use `{self._parsed_version}`
            as a replacement to avoid breaking existing environments,
            but no future compatibility is guaranteed.

            If you maintain package {self.project_name} you should implement
            the relevant changes to adequate the project to PEP 440 immediately.
            *************************************************************************
            \n\n!!
            """
            warnings.warn(msg, DeprecationWarning)

            return self._parsed_version

    @property
    def version(self):
        try:
            return self._version
        except AttributeError as e:
            version = self._get_version()
            if version is None:
                path = self._get_metadata_path_for_display(self.PKG_INFO)
                msg = ("Missing 'Version:' header and/or {} file at path: {}").format(
                    self.PKG_INFO, path
                )
                raise ValueError(msg, self) from e

            return version

    @property
    def _dep_map(self):
        """
        A map of extra to its list of (direct) requirements
        for this distribution, including the null extra.
        """
        try:
            return self.__dep_map
        except AttributeError:
            self.__dep_map = self._filter_extras(self._build_dep_map())
        return self.__dep_map

    @staticmethod
    def _filter_extras(dm: dict[str | None, list[Requirement]]):
        """
        Given a mapping of extras to dependencies, strip off
        environment markers and filter out any dependencies
        not matching the markers.
        """
        for extra in list(filter(None, dm)):
            new_extra: str | None = extra
            reqs = dm.pop(extra)
            new_extra, _, marker = extra.partition(':')
            fails_marker = marker and (
                invalid_marker(marker) or not evaluate_marker(marker)
            )
            if fails_marker:
                reqs = []
            new_extra = safe_extra(new_extra) or None

            dm.setdefault(new_extra, []).extend(reqs)
        return dm

    def _build_dep_map(self):
        dm = {}
        for name in 'requires.txt', 'depends.txt':
            for extra, reqs in split_sections(self._get_metadata(name)):
                dm.setdefault(extra, []).extend(parse_requirements(reqs))
        return dm

    def requires(self, extras: Iterable[str] = ()):
        """List of Requirements needed for this distro if `extras` are used"""
        dm = self._dep_map
        deps: list[Requirement] = []
        deps.extend(dm.get(None, ()))
        for ext in extras:
            try:
                deps.extend(dm[safe_extra(ext)])
            except KeyError as e:
                raise UnknownExtra(
                    "%s has no such extra feature %r" % (self, ext)
                ) from e
        return deps

    def _get_metadata_path_for_display(self, name):
        """
        Return the path to the given metadata file, if available.
        """
        try:
            # We need to access _get_metadata_path() on the provider object
            # directly rather than through this class's __getattr__()
            # since _get_metadata_path() is marked private.
            path = self._provider._get_metadata_path(name)

        # Handle exceptions e.g. in case the distribution's metadata
        # provider doesn't support _get_metadata_path().
        except Exception:
            return '[could not detect]'

        return path

    def _get_metadata(self, name):
        if self.has_metadata(name):
            yield from self.get_metadata_lines(name)

    def _get_version(self):
        lines = self._get_metadata(self.PKG_INFO)
        return _version_from_file(lines)

    def activate(self, path: list[str] | None = None, replace: bool = False):
        """Ensure distribution is importable on `path` (default=sys.path)"""
        if path is None:
            path = sys.path
        self.insert_on(path, replace=replace)
        if path is sys.path and self.location is not None:
            fixup_namespace_packages(self.location)
            for pkg in self._get_metadata('namespace_packages.txt'):
                if pkg in sys.modules:
                    declare_namespace(pkg)

    def egg_name(self):
        """Return what this distribution's standard .egg filename should be"""
        filename = "%s-%s-py%s" % (
            to_filename(self.project_name),
            to_filename(self.version),
            self.py_version or PY_MAJOR,
        )

        if self.platform:
            filename += '-' + self.platform
        return filename

    def __repr__(self):
        if self.location:
            return "%s (%s)" % (self, self.location)
        else:
            return str(self)

    def __str__(self):
        try:
            version = getattr(self, 'version', None)
        except ValueError:
            version = None
        version = version or "[unknown version]"
        return "%s %s" % (self.project_name, version)

    def __getattr__(self, attr):
        """Delegate all unrecognized public attributes to .metadata provider"""
        if attr.startswith('_'):
            raise AttributeError(attr)
        return getattr(self._provider, attr)

    def __dir__(self):
        return list(
            set(super().__dir__())
            | set(attr for attr in self._provider.__dir__() if not attr.startswith('_'))
        )

    @classmethod
    def from_filename(
        cls,
        filename: StrPath,
        metadata: _MetadataType = None,
        **kw: int,  # We could set `precedence` explicitly, but keeping this as `**kw` for full backwards and subclassing compatibility
    ):
        return cls.from_location(
            _normalize_cached(filename), os.path.basename(filename), metadata, **kw
        )

    def as_requirement(self):
        """Return a ``Requirement`` that matches this distribution exactly"""
        if isinstance(self.parsed_version, _packaging_version.Version):
            spec = "%s==%s" % (self.project_name, self.parsed_version)
        else:
            spec = "%s===%s" % (self.project_name, self.parsed_version)

        return Requirement.parse(spec)

    def load_entry_point(self, group: str, name: str) -> _ResolvedEntryPoint:
        """Return the `name` entry point of `group` or raise ImportError"""
        ep = self.get_entry_info(group, name)
        if ep is None:
            raise ImportError("Entry point %r not found" % ((group, name),))
        return ep.load()

    @overload
    def get_entry_map(self, group: None = None) -> dict[str, dict[str, EntryPoint]]: ...
    @overload
    def get_entry_map(self, group: str) -> dict[str, EntryPoint]: ...
    def get_entry_map(self, group: str | None = None):
        """Return the entry point map for `group`, or the full entry map"""
        if not hasattr(self, "_ep_map"):
            self._ep_map = EntryPoint.parse_map(
                self._get_metadata('entry_points.txt'), self
            )
        if group is not None:
            return self._ep_map.get(group, {})
        return self._ep_map

    def get_entry_info(self, group: str, name: str):
        """Return the EntryPoint object for `group`+`name`, or ``None``"""
        return self.get_entry_map(group).get(name)

    # FIXME: 'Distribution.insert_on' is too complex (13)
    def insert_on(  # noqa: C901
        self,
        path: list[str],
        loc=None,
        replace: bool = False,
    ):
        """Ensure self.location is on path

        If replace=False (default):
            - If location is already in path anywhere, do nothing.
            - Else:
              - If it's an egg and its parent directory is on path,
                insert just ahead of the parent.
              - Else: add to the end of path.
        If replace=True:
            - If location is already on path anywhere (not eggs)
              or higher priority than its parent (eggs)
              do nothing.
            - Else:
              - If it's an egg and its parent directory is on path,
                insert just ahead of the parent,
                removing any lower-priority entries.
              - Else: add it to the front of path.
        """

        loc = loc or self.location
        if not loc:
            return

        nloc = _normalize_cached(loc)
        bdir = os.path.dirname(nloc)
        npath = [(p and _normalize_cached(p) or p) for p in path]

        for p, item in enumerate(npath):
            if item == nloc:
                if replace:
                    break
                else:
                    # don't modify path (even removing duplicates) if
                    # found and not replace
                    return
            elif item == bdir and self.precedence == EGG_DIST:
                # if it's an .egg, give it precedence over its directory
                # UNLESS it's already been added to sys.path and replace=False
                if (not replace) and nloc in npath[p:]:
                    return
                if path is sys.path:
                    self.check_version_conflict()
                path.insert(p, loc)
                npath.insert(p, nloc)
                break
        else:
            if path is sys.path:
                self.check_version_conflict()
            if replace:
                path.insert(0, loc)
            else:
                path.append(loc)
            return

        # p is the spot where we found or inserted loc; now remove duplicates
        while True:
            try:
                np = npath.index(nloc, p + 1)
            except ValueError:
                break
            else:
                del npath[np], path[np]
                # ha!
                p = np

        return

    def check_version_conflict(self):
        if self.key == 'setuptools':
            # ignore the inevitable setuptools self-conflicts  :(
            return

        nsp = dict.fromkeys(self._get_metadata('namespace_packages.txt'))
        loc = normalize_path(self.location)
        for modname in self._get_metadata('top_level.txt'):
            if (
                modname not in sys.modules
                or modname in nsp
                or modname in _namespace_packages
            ):
                continue
            if modname in ('pkg_resources', 'setuptools', 'site'):
                continue
            fn = getattr(sys.modules[modname], '__file__', None)
            if fn and (
                normalize_path(fn).startswith(loc) or fn.startswith(self.location)
            ):
                continue
            issue_warning(
                "Module %s was already imported from %s, but %s is being added"
                " to sys.path" % (modname, fn, self.location),
            )

    def has_version(self):
        try:
            self.version
        except ValueError:
            issue_warning("Unbuilt egg for " + repr(self))
            return False
        except SystemError:
            # TODO: remove this except clause when python/cpython#103632 is fixed.
            return False
        return True

    def clone(self, **kw: str | int | IResourceProvider | None):
        """Copy this distribution, substituting in any changed keyword args"""
        names = 'project_name version py_version platform location precedence'
        for attr in names.split():
            kw.setdefault(attr, getattr(self, attr, None))
        kw.setdefault('metadata', self._provider)
        # Unsafely unpacking. But keeping **kw for backwards and subclassing compatibility
        return self.__class__(**kw)  # type:ignore[arg-type]

    @property
    def extras(self):
        return [dep for dep in self._dep_map if dep]


class EggInfoDistribution(Distribution):
    def _reload_version(self):
        """
        Packages installed by distutils (e.g. numpy or scipy),
        which uses an old safe_version, and so
        their version numbers can get mangled when
        converted to filenames (e.g., 1.11.0.dev0+2329eae to
        1.11.0.dev0_2329eae). These distributions will not be
        parsed properly
        downstream by Distribution and safe_version, so
        take an extra step and try to get the version number from
        the metadata file itself instead of the filename.
        """
        md_version = self._get_version()
        if md_version:
            self._version = md_version
        return self


class DistInfoDistribution(Distribution):
    """
    Wrap an actual or potential sys.path entry
    w/metadata, .dist-info style.
    """

    PKG_INFO = 'METADATA'
    EQEQ = re.compile(r"([\(,])\s*(\d.*?)\s*([,\)])")

    @property
    def _parsed_pkg_info(self):
        """Parse and cache metadata"""
        try:
            return self._pkg_info
        except AttributeError:
            metadata = self.get_metadata(self.PKG_INFO)
            self._pkg_info = email.parser.Parser().parsestr(metadata)
            return self._pkg_info

    @property
    def _dep_map(self):
        try:
            return self.__dep_map
        except AttributeError:
            self.__dep_map = self._compute_dependencies()
            return self.__dep_map

    def _compute_dependencies(self) -> dict[str | None, list[Requirement]]:
        """Recompute this distribution's dependencies."""
        self.__dep_map: dict[str | None, list[Requirement]] = {None: []}

        reqs: list[Requirement] = []
        # Including any condition expressions
        for req in self._parsed_pkg_info.get_all('Requires-Dist') or []:
            reqs.extend(parse_requirements(req))

        def reqs_for_extra(extra):
            for req in reqs:
                if not req.marker or req.marker.evaluate({'extra': extra}):
                    yield req

        common = types.MappingProxyType(dict.fromkeys(reqs_for_extra(None)))
        self.__dep_map[None].extend(common)

        for extra in self._parsed_pkg_info.get_all('Provides-Extra') or []:
            s_extra = safe_extra(extra.strip())
            self.__dep_map[s_extra] = [
                r for r in reqs_for_extra(extra) if r not in common
            ]

        return self.__dep_map


_distributionImpl = {
    '.egg': Distribution,
    '.egg-info': EggInfoDistribution,
    '.dist-info': DistInfoDistribution,
}


def issue_warning(*args, **kw):
    level = 1
    g = globals()
    try:
        # find the first stack frame that is *not* code in
        # the pkg_resources module, to use for the warning
        while sys._getframe(level).f_globals is g:
            level += 1
    except ValueError:
        pass
    warnings.warn(stacklevel=level + 1, *args, **kw)


def parse_requirements(strs: _NestedStr):
    """
    Yield ``Requirement`` objects for each specification in `strs`.

    `strs` must be a string, or a (possibly-nested) iterable thereof.
    """
    return map(Requirement, join_continuation(map(drop_comment, yield_lines(strs))))


class RequirementParseError(_packaging_requirements.InvalidRequirement):
    "Compatibility wrapper for InvalidRequirement"


class Requirement(_packaging_requirements.Requirement):
    def __init__(self, requirement_string: str):
        """DO NOT CALL THIS UNDOCUMENTED METHOD; use Requirement.parse()!"""
        super().__init__(requirement_string)
        self.unsafe_name = self.name
        project_name = safe_name(self.name)
        self.project_name, self.key = project_name, project_name.lower()
        self.specs = [(spec.operator, spec.version) for spec in self.specifier]
        # packaging.requirements.Requirement uses a set for its extras. We use a variable-length tuple
        self.extras: tuple[str] = tuple(map(safe_extra, self.extras))
        self.hashCmp = (
            self.key,
            self.url,
            self.specifier,
            frozenset(self.extras),
            str(self.marker) if self.marker else None,
        )
        self.__hash = hash(self.hashCmp)

    def __eq__(self, other: object):
        return isinstance(other, Requirement) and self.hashCmp == other.hashCmp

    def __ne__(self, other):
        return not self == other

    def __contains__(self, item: Distribution | str | tuple[str, ...]) -> bool:
        if isinstance(item, Distribution):
            if item.key != self.key:
                return False

            item = item.version

        # Allow prereleases always in order to match the previous behavior of
        # this method. In the future this should be smarter and follow PEP 440
        # more accurately.
        return self.specifier.contains(item, prereleases=True)

    def __hash__(self):
        return self.__hash

    def __repr__(self):
        return "Requirement.parse(%r)" % str(self)

    @staticmethod
    def parse(s: str | Iterable[str]):
        (req,) = parse_requirements(s)
        return req


def _always_object(classes):
    """
    Ensure object appears in the mro even
    for old-style classes.
    """
    if object not in classes:
        return classes + (object,)
    return classes


def _find_adapter(registry: Mapping[type, _AdapterT], ob: object) -> _AdapterT:
    """Return an adapter factory for `ob` from `registry`"""
    types = _always_object(inspect.getmro(getattr(ob, '__class__', type(ob))))
    for t in types:
        if t in registry:
            return registry[t]
    # _find_adapter would previously return None, and immediately be called.
    # So we're raising a TypeError to keep backward compatibility if anyone depended on that behaviour.
    raise TypeError(f"Could not find adapter for {registry} and {ob}")


def ensure_directory(path: StrOrBytesPath):
    """Ensure that the parent directory of `path` exists"""
    dirname = os.path.dirname(path)
    os.makedirs(dirname, exist_ok=True)


def _bypass_ensure_directory(path):
    """Sandbox-bypassing version of ensure_directory()"""
    if not WRITE_SUPPORT:
        raise OSError('"os.mkdir" not supported on this platform.')
    dirname, filename = split(path)
    if dirname and filename and not isdir(dirname):
        _bypass_ensure_directory(dirname)
        try:
            mkdir(dirname, 0o755)
        except FileExistsError:
            pass


def split_sections(s: _NestedStr) -> Iterator[tuple[str | None, list[str]]]:
    """Split a string or iterable thereof into (section, content) pairs

    Each ``section`` is a stripped version of the section header ("[section]")
    and each ``content`` is a list of stripped lines excluding blank lines and
    comment-only lines.  If there are any such lines before the first section
    header, they're returned in a first ``section`` of ``None``.
    """
    section = None
    content = []
    for line in yield_lines(s):
        if line.startswith("["):
            if line.endswith("]"):
                if section or content:
                    yield section, content
                section = line[1:-1].strip()
                content = []
            else:
                raise ValueError("Invalid section heading", line)
        else:
            content.append(line)

    # wrap up last segment
    yield section, content


def _mkstemp(*args, **kw):
    old_open = os.open
    try:
        # temporarily bypass sandboxing
        os.open = os_open
        return tempfile.mkstemp(*args, **kw)
    finally:
        # and then put it back
        os.open = old_open


# Silence the PEP440Warning by default, so that end users don't get hit by it
# randomly just because they use pkg_resources. We want to append the rule
# because we want earlier uses of filterwarnings to take precedence over this
# one.
warnings.filterwarnings("ignore", category=PEP440Warning, append=True)


class PkgResourcesDeprecationWarning(Warning):
    """
    Base class for warning about deprecations in ``pkg_resources``

    This class is not derived from ``DeprecationWarning``, and as such is
    visible by default.
    """


# Ported from ``setuptools`` to avoid introducing an import inter-dependency:
_LOCALE_ENCODING = "locale" if sys.version_info >= (3, 10) else None


def _read_utf8_with_fallback(file: str, fallback_encoding=_LOCALE_ENCODING) -> str:
    """See setuptools.unicode_utils._read_utf8_with_fallback"""
    try:
        with open(file, "r", encoding="utf-8") as f:
            return f.read()
    except UnicodeDecodeError:  # pragma: no cover
        msg = f"""\
        ********************************************************************************
        `encoding="utf-8"` fails with {file!r}, trying `encoding={fallback_encoding!r}`.

        This fallback behaviour is considered **deprecated** and future versions of
        `setuptools/pkg_resources` may not implement it.

        Please encode {file!r} with "utf-8" to ensure future builds will succeed.

        If this file was produced by `setuptools` itself, cleaning up the cached files
        and re-building/re-installing the package with a newer version of `setuptools`
        (e.g. by updating `build-system.requires` in its `pyproject.toml`)
        might solve the problem.
        ********************************************************************************
        """
        # TODO: Add a deadline?
        #       See comment in setuptools.unicode_utils._Utf8EncodingNeeded
        warnings.warn(msg, PkgResourcesDeprecationWarning, stacklevel=2)
        with open(file, "r", encoding=fallback_encoding) as f:
            return f.read()


# from jaraco.functools 1.3
def _call_aside(f, *args, **kwargs):
    f(*args, **kwargs)
    return f


@_call_aside
def _initialize(g=globals()):
    "Set up global resource manager (deliberately not state-saved)"
    manager = ResourceManager()
    g['_manager'] = manager
    g.update(
        (name, getattr(manager, name))
        for name in dir(manager)
        if not name.startswith('_')
    )


@_call_aside
def _initialize_master_working_set():
    """
    Prepare the master working set and make the ``require()``
    API available.

    This function has explicit effects on the global state
    of pkg_resources. It is intended to be invoked once at
    the initialization of this module.

    Invocation by other packages is unsupported and done
    at their own risk.
    """
    working_set = _declare_state('object', 'working_set', WorkingSet._build_master())

    require = working_set.require
    iter_entry_points = working_set.iter_entry_points
    add_activation_listener = working_set.subscribe
    run_script = working_set.run_script
    # backward compatibility
    run_main = run_script
    # Activate all distributions already on sys.path with replace=False and
    # ensure that all distributions added to the working set in the future
    # (e.g. by calling ``require()``) will get activated as well,
    # with higher priority (replace=True).
    tuple(dist.activate(replace=False) for dist in working_set)
    add_activation_listener(
        lambda dist: dist.activate(replace=True),
        existing=False,
    )
    working_set.entries = []
    # match order
    list(map(working_set.add_entry, sys.path))
    globals().update(locals())


if TYPE_CHECKING:
    # All of these are set by the @_call_aside methods above
    __resource_manager = ResourceManager()  # Won't exist at runtime
    resource_exists = __resource_manager.resource_exists
    resource_isdir = __resource_manager.resource_isdir
    resource_filename = __resource_manager.resource_filename
    resource_stream = __resource_manager.resource_stream
    resource_string = __resource_manager.resource_string
    resource_listdir = __resource_manager.resource_listdir
    set_extraction_path = __resource_manager.set_extraction_path
    cleanup_resources = __resource_manager.cleanup_resources

    working_set = WorkingSet()
    require = working_set.require
    iter_entry_points = working_set.iter_entry_points
    add_activation_listener = working_set.subscribe
    run_script = working_set.run_script
    run_main = run_script