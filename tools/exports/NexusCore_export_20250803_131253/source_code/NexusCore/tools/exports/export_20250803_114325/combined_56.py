
# === NexusCore/openenv\Lib\site-packages\psutil\_pslinux.py ===
# Copyright (c) 2009, Giampaolo Rodola'. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Linux platform implementation."""

from __future__ import division

import base64
import collections
import errno
import functools
import glob
import os
import re
import socket
import struct
import sys
import warnings
from collections import defaultdict
from collections import namedtuple

from . import _common
from . import _psposix
from . import _psutil_linux as cext
from . import _psutil_posix as cext_posix
from ._common import NIC_DUPLEX_FULL
from ._common import NIC_DUPLEX_HALF
from ._common import NIC_DUPLEX_UNKNOWN
from ._common import AccessDenied
from ._common import NoSuchProcess
from ._common import ZombieProcess
from ._common import bcat
from ._common import cat
from ._common import debug
from ._common import decode
from ._common import get_procfs_path
from ._common import isfile_strict
from ._common import memoize
from ._common import memoize_when_activated
from ._common import open_binary
from ._common import open_text
from ._common import parse_environ_block
from ._common import path_exists_strict
from ._common import supports_ipv6
from ._common import usage_percent
from ._compat import PY3
from ._compat import FileNotFoundError
from ._compat import PermissionError
from ._compat import ProcessLookupError
from ._compat import b
from ._compat import basestring


if PY3:
    import enum
else:
    enum = None


# fmt: off
__extra__all__ = [
    #
    'PROCFS_PATH',
    # io prio constants
    "IOPRIO_CLASS_NONE", "IOPRIO_CLASS_RT", "IOPRIO_CLASS_BE",
    "IOPRIO_CLASS_IDLE",
    # connection status constants
    "CONN_ESTABLISHED", "CONN_SYN_SENT", "CONN_SYN_RECV", "CONN_FIN_WAIT1",
    "CONN_FIN_WAIT2", "CONN_TIME_WAIT", "CONN_CLOSE", "CONN_CLOSE_WAIT",
    "CONN_LAST_ACK", "CONN_LISTEN", "CONN_CLOSING",
]
# fmt: on


# =====================================================================
# --- globals
# =====================================================================


POWER_SUPPLY_PATH = "/sys/class/power_supply"
HAS_PROC_SMAPS = os.path.exists('/proc/%s/smaps' % os.getpid())
HAS_PROC_SMAPS_ROLLUP = os.path.exists('/proc/%s/smaps_rollup' % os.getpid())
HAS_PROC_IO_PRIORITY = hasattr(cext, "proc_ioprio_get")
HAS_CPU_AFFINITY = hasattr(cext, "proc_cpu_affinity_get")

# Number of clock ticks per second
CLOCK_TICKS = os.sysconf("SC_CLK_TCK")
PAGESIZE = cext_posix.getpagesize()
BOOT_TIME = None  # set later
LITTLE_ENDIAN = sys.byteorder == 'little'

# "man iostat" states that sectors are equivalent with blocks and have
# a size of 512 bytes. Despite this value can be queried at runtime
# via /sys/block/{DISK}/queue/hw_sector_size and results may vary
# between 1k, 2k, or 4k... 512 appears to be a magic constant used
# throughout Linux source code:
# * https://stackoverflow.com/a/38136179/376587
# * https://lists.gt.net/linux/kernel/2241060
# * https://github.com/giampaolo/psutil/issues/1305
# * https://github.com/torvalds/linux/blob/
#     4f671fe2f9523a1ea206f63fe60a7c7b3a56d5c7/include/linux/bio.h#L99
# * https://lkml.org/lkml/2015/8/17/234
DISK_SECTOR_SIZE = 512

if enum is None:
    AF_LINK = socket.AF_PACKET
else:
    AddressFamily = enum.IntEnum(
        'AddressFamily', {'AF_LINK': int(socket.AF_PACKET)}
    )
    AF_LINK = AddressFamily.AF_LINK

# ioprio_* constants http://linux.die.net/man/2/ioprio_get
if enum is None:
    IOPRIO_CLASS_NONE = 0
    IOPRIO_CLASS_RT = 1
    IOPRIO_CLASS_BE = 2
    IOPRIO_CLASS_IDLE = 3
else:

    class IOPriority(enum.IntEnum):
        IOPRIO_CLASS_NONE = 0
        IOPRIO_CLASS_RT = 1
        IOPRIO_CLASS_BE = 2
        IOPRIO_CLASS_IDLE = 3

    globals().update(IOPriority.__members__)

# See:
# https://github.com/torvalds/linux/blame/master/fs/proc/array.c
# ...and (TASK_* constants):
# https://github.com/torvalds/linux/blob/master/include/linux/sched.h
PROC_STATUSES = {
    "R": _common.STATUS_RUNNING,
    "S": _common.STATUS_SLEEPING,
    "D": _common.STATUS_DISK_SLEEP,
    "T": _common.STATUS_STOPPED,
    "t": _common.STATUS_TRACING_STOP,
    "Z": _common.STATUS_ZOMBIE,
    "X": _common.STATUS_DEAD,
    "x": _common.STATUS_DEAD,
    "K": _common.STATUS_WAKE_KILL,
    "W": _common.STATUS_WAKING,
    "I": _common.STATUS_IDLE,
    "P": _common.STATUS_PARKED,
}

# https://github.com/torvalds/linux/blob/master/include/net/tcp_states.h
TCP_STATUSES = {
    "01": _common.CONN_ESTABLISHED,
    "02": _common.CONN_SYN_SENT,
    "03": _common.CONN_SYN_RECV,
    "04": _common.CONN_FIN_WAIT1,
    "05": _common.CONN_FIN_WAIT2,
    "06": _common.CONN_TIME_WAIT,
    "07": _common.CONN_CLOSE,
    "08": _common.CONN_CLOSE_WAIT,
    "09": _common.CONN_LAST_ACK,
    "0A": _common.CONN_LISTEN,
    "0B": _common.CONN_CLOSING,
}


# =====================================================================
# --- named tuples
# =====================================================================


# fmt: off
# psutil.virtual_memory()
svmem = namedtuple(
    'svmem', ['total', 'available', 'percent', 'used', 'free',
              'active', 'inactive', 'buffers', 'cached', 'shared', 'slab'])
# psutil.disk_io_counters()
sdiskio = namedtuple(
    'sdiskio', ['read_count', 'write_count',
                'read_bytes', 'write_bytes',
                'read_time', 'write_time',
                'read_merged_count', 'write_merged_count',
                'busy_time'])
# psutil.Process().open_files()
popenfile = namedtuple(
    'popenfile', ['path', 'fd', 'position', 'mode', 'flags'])
# psutil.Process().memory_info()
pmem = namedtuple('pmem', 'rss vms shared text lib data dirty')
# psutil.Process().memory_full_info()
pfullmem = namedtuple('pfullmem', pmem._fields + ('uss', 'pss', 'swap'))
# psutil.Process().memory_maps(grouped=True)
pmmap_grouped = namedtuple(
    'pmmap_grouped',
    ['path', 'rss', 'size', 'pss', 'shared_clean', 'shared_dirty',
     'private_clean', 'private_dirty', 'referenced', 'anonymous', 'swap'])
# psutil.Process().memory_maps(grouped=False)
pmmap_ext = namedtuple(
    'pmmap_ext', 'addr perms ' + ' '.join(pmmap_grouped._fields))
# psutil.Process.io_counters()
pio = namedtuple('pio', ['read_count', 'write_count',
                         'read_bytes', 'write_bytes',
                         'read_chars', 'write_chars'])
# psutil.Process.cpu_times()
pcputimes = namedtuple('pcputimes',
                       ['user', 'system', 'children_user', 'children_system',
                        'iowait'])
# fmt: on


# =====================================================================
# --- utils
# =====================================================================


def readlink(path):
    """Wrapper around os.readlink()."""
    assert isinstance(path, basestring), path
    path = os.readlink(path)
    # readlink() might return paths containing null bytes ('\x00')
    # resulting in "TypeError: must be encoded string without NULL
    # bytes, not str" errors when the string is passed to other
    # fs-related functions (os.*, open(), ...).
    # Apparently everything after '\x00' is garbage (we can have
    # ' (deleted)', 'new' and possibly others), see:
    # https://github.com/giampaolo/psutil/issues/717
    path = path.split('\x00')[0]
    # Certain paths have ' (deleted)' appended. Usually this is
    # bogus as the file actually exists. Even if it doesn't we
    # don't care.
    if path.endswith(' (deleted)') and not path_exists_strict(path):
        path = path[:-10]
    return path


def file_flags_to_mode(flags):
    """Convert file's open() flags into a readable string.
    Used by Process.open_files().
    """
    modes_map = {os.O_RDONLY: 'r', os.O_WRONLY: 'w', os.O_RDWR: 'w+'}
    mode = modes_map[flags & (os.O_RDONLY | os.O_WRONLY | os.O_RDWR)]
    if flags & os.O_APPEND:
        mode = mode.replace('w', 'a', 1)
    mode = mode.replace('w+', 'r+')
    # possible values: r, w, a, r+, a+
    return mode


def is_storage_device(name):
    """Return True if the given name refers to a root device (e.g.
    "sda", "nvme0n1") as opposed to a logical partition (e.g.  "sda1",
    "nvme0n1p1"). If name is a virtual device (e.g. "loop1", "ram")
    return True.
    """
    # Re-adapted from iostat source code, see:
    # https://github.com/sysstat/sysstat/blob/
    #     97912938cd476645b267280069e83b1c8dc0e1c7/common.c#L208
    # Some devices may have a slash in their name (e.g. cciss/c0d0...).
    name = name.replace('/', '!')
    including_virtual = True
    if including_virtual:
        path = "/sys/block/%s" % name
    else:
        path = "/sys/block/%s/device" % name
    return os.access(path, os.F_OK)


@memoize
def set_scputimes_ntuple(procfs_path):
    """Set a namedtuple of variable fields depending on the CPU times
    available on this Linux kernel version which may be:
    (user, nice, system, idle, iowait, irq, softirq, [steal, [guest,
     [guest_nice]]])
    Used by cpu_times() function.
    """
    global scputimes
    with open_binary('%s/stat' % procfs_path) as f:
        values = f.readline().split()[1:]
    fields = ['user', 'nice', 'system', 'idle', 'iowait', 'irq', 'softirq']
    vlen = len(values)
    if vlen >= 8:
        # Linux >= 2.6.11
        fields.append('steal')
    if vlen >= 9:
        # Linux >= 2.6.24
        fields.append('guest')
    if vlen >= 10:
        # Linux >= 3.2.0
        fields.append('guest_nice')
    scputimes = namedtuple('scputimes', fields)


try:
    set_scputimes_ntuple("/proc")
except Exception as err:  # noqa: BLE001
    # Don't want to crash at import time.
    debug("ignoring exception on import: %r" % err)
    scputimes = namedtuple('scputimes', 'user system idle')(0.0, 0.0, 0.0)


# =====================================================================
# --- prlimit
# =====================================================================

# Backport of resource.prlimit() for Python 2. Originally this was done
# in C, but CentOS-6 which we use to create manylinux wheels is too old
# and does not support prlimit() syscall. As such the resulting wheel
# would not include prlimit(), even when installed on newer systems.
# This is the only part of psutil using ctypes.

prlimit = None
try:
    from resource import prlimit  # python >= 3.4
except ImportError:
    import ctypes

    libc = ctypes.CDLL(None, use_errno=True)

    if hasattr(libc, "prlimit"):

        def prlimit(pid, resource_, limits=None):
            class StructRlimit(ctypes.Structure):
                _fields_ = [
                    ('rlim_cur', ctypes.c_longlong),
                    ('rlim_max', ctypes.c_longlong),
                ]

            current = StructRlimit()
            if limits is None:
                # get
                ret = libc.prlimit(pid, resource_, None, ctypes.byref(current))
            else:
                # set
                new = StructRlimit()
                new.rlim_cur = limits[0]
                new.rlim_max = limits[1]
                ret = libc.prlimit(
                    pid, resource_, ctypes.byref(new), ctypes.byref(current)
                )

            if ret != 0:
                errno_ = ctypes.get_errno()
                raise OSError(errno_, os.strerror(errno_))
            return (current.rlim_cur, current.rlim_max)


if prlimit is not None:
    __extra__all__.extend(
        [x for x in dir(cext) if x.startswith('RLIM') and x.isupper()]
    )


# =====================================================================
# --- system memory
# =====================================================================


def calculate_avail_vmem(mems):
    """Fallback for kernels < 3.14 where /proc/meminfo does not provide
    "MemAvailable", see:
    https://blog.famzah.net/2014/09/24/.

    This code reimplements the algorithm outlined here:
    https://git.kernel.org/cgit/linux/kernel/git/torvalds/linux.git/
        commit/?id=34e431b0ae398fc54ea69ff85ec700722c9da773

    We use this function also when "MemAvailable" returns 0 (possibly a
    kernel bug, see: https://github.com/giampaolo/psutil/issues/1915).
    In that case this routine matches "free" CLI tool result ("available"
    column).

    XXX: on recent kernels this calculation may differ by ~1.5% compared
    to "MemAvailable:", as it's calculated slightly differently.
    It is still way more realistic than doing (free + cached) though.
    See:
    * https://gitlab.com/procps-ng/procps/issues/42
    * https://github.com/famzah/linux-memavailable-procfs/issues/2
    """
    # Note about "fallback" value. According to:
    # https://git.kernel.org/cgit/linux/kernel/git/torvalds/linux.git/
    #     commit/?id=34e431b0ae398fc54ea69ff85ec700722c9da773
    # ...long ago "available" memory was calculated as (free + cached),
    # We use fallback when one of these is missing from /proc/meminfo:
    # "Active(file)": introduced in 2.6.28 / Dec 2008
    # "Inactive(file)": introduced in 2.6.28 / Dec 2008
    # "SReclaimable": introduced in 2.6.19 / Nov 2006
    # /proc/zoneinfo: introduced in 2.6.13 / Aug 2005
    free = mems[b'MemFree:']
    fallback = free + mems.get(b"Cached:", 0)
    try:
        lru_active_file = mems[b'Active(file):']
        lru_inactive_file = mems[b'Inactive(file):']
        slab_reclaimable = mems[b'SReclaimable:']
    except KeyError as err:
        debug(
            "%s is missing from /proc/meminfo; using an approximation for "
            "calculating available memory"
            % err.args[0]
        )
        return fallback
    try:
        f = open_binary('%s/zoneinfo' % get_procfs_path())
    except IOError:
        return fallback  # kernel 2.6.13

    watermark_low = 0
    with f:
        for line in f:
            line = line.strip()
            if line.startswith(b'low'):
                watermark_low += int(line.split()[1])
    watermark_low *= PAGESIZE

    avail = free - watermark_low
    pagecache = lru_active_file + lru_inactive_file
    pagecache -= min(pagecache / 2, watermark_low)
    avail += pagecache
    avail += slab_reclaimable - min(slab_reclaimable / 2.0, watermark_low)
    return int(avail)


def virtual_memory():
    """Report virtual memory stats.
    This implementation mimicks procps-ng-3.3.12, aka "free" CLI tool:
    https://gitlab.com/procps-ng/procps/blob/
        24fd2605c51fccc375ab0287cec33aa767f06718/proc/sysinfo.c#L778-791
    The returned values are supposed to match both "free" and "vmstat -s"
    CLI tools.
    """
    missing_fields = []
    mems = {}
    with open_binary('%s/meminfo' % get_procfs_path()) as f:
        for line in f:
            fields = line.split()
            mems[fields[0]] = int(fields[1]) * 1024

    # /proc doc states that the available fields in /proc/meminfo vary
    # by architecture and compile options, but these 3 values are also
    # returned by sysinfo(2); as such we assume they are always there.
    total = mems[b'MemTotal:']
    free = mems[b'MemFree:']
    try:
        buffers = mems[b'Buffers:']
    except KeyError:
        # https://github.com/giampaolo/psutil/issues/1010
        buffers = 0
        missing_fields.append('buffers')
    try:
        cached = mems[b"Cached:"]
    except KeyError:
        cached = 0
        missing_fields.append('cached')
    else:
        # "free" cmdline utility sums reclaimable to cached.
        # Older versions of procps used to add slab memory instead.
        # This got changed in:
        # https://gitlab.com/procps-ng/procps/commit/
        #     05d751c4f076a2f0118b914c5e51cfbb4762ad8e
        cached += mems.get(b"SReclaimable:", 0)  # since kernel 2.6.19

    try:
        shared = mems[b'Shmem:']  # since kernel 2.6.32
    except KeyError:
        try:
            shared = mems[b'MemShared:']  # kernels 2.4
        except KeyError:
            shared = 0
            missing_fields.append('shared')

    try:
        active = mems[b"Active:"]
    except KeyError:
        active = 0
        missing_fields.append('active')

    try:
        inactive = mems[b"Inactive:"]
    except KeyError:
        try:
            inactive = (
                mems[b"Inact_dirty:"]
                + mems[b"Inact_clean:"]
                + mems[b"Inact_laundry:"]
            )
        except KeyError:
            inactive = 0
            missing_fields.append('inactive')

    try:
        slab = mems[b"Slab:"]
    except KeyError:
        slab = 0

    used = total - free - cached - buffers
    if used < 0:
        # May be symptomatic of running within a LCX container where such
        # values will be dramatically distorted over those of the host.
        used = total - free

    # - starting from 4.4.0 we match free's "available" column.
    #   Before 4.4.0 we calculated it as (free + buffers + cached)
    #   which matched htop.
    # - free and htop available memory differs as per:
    #   http://askubuntu.com/a/369589
    #   http://unix.stackexchange.com/a/65852/168884
    # - MemAvailable has been introduced in kernel 3.14
    try:
        avail = mems[b'MemAvailable:']
    except KeyError:
        avail = calculate_avail_vmem(mems)
    else:
        if avail == 0:
            # Yes, it can happen (probably a kernel bug):
            # https://github.com/giampaolo/psutil/issues/1915
            # In this case "free" CLI tool makes an estimate. We do the same,
            # and it matches "free" CLI tool.
            avail = calculate_avail_vmem(mems)

    if avail < 0:
        avail = 0
        missing_fields.append('available')
    elif avail > total:
        # If avail is greater than total or our calculation overflows,
        # that's symptomatic of running within a LCX container where such
        # values will be dramatically distorted over those of the host.
        # https://gitlab.com/procps-ng/procps/blob/
        #     24fd2605c51fccc375ab0287cec33aa767f06718/proc/sysinfo.c#L764
        avail = free

    percent = usage_percent((total - avail), total, round_=1)

    # Warn about missing metrics which are set to 0.
    if missing_fields:
        msg = "%s memory stats couldn't be determined and %s set to 0" % (
            ", ".join(missing_fields),
            "was" if len(missing_fields) == 1 else "were",
        )
        warnings.warn(msg, RuntimeWarning, stacklevel=2)

    return svmem(
        total,
        avail,
        percent,
        used,
        free,
        active,
        inactive,
        buffers,
        cached,
        shared,
        slab,
    )


def swap_memory():
    """Return swap memory metrics."""
    mems = {}
    with open_binary('%s/meminfo' % get_procfs_path()) as f:
        for line in f:
            fields = line.split()
            mems[fields[0]] = int(fields[1]) * 1024
    # We prefer /proc/meminfo over sysinfo() syscall so that
    # psutil.PROCFS_PATH can be used in order to allow retrieval
    # for linux containers, see:
    # https://github.com/giampaolo/psutil/issues/1015
    try:
        total = mems[b'SwapTotal:']
        free = mems[b'SwapFree:']
    except KeyError:
        _, _, _, _, total, free, unit_multiplier = cext.linux_sysinfo()
        total *= unit_multiplier
        free *= unit_multiplier

    used = total - free
    percent = usage_percent(used, total, round_=1)
    # get pgin/pgouts
    try:
        f = open_binary("%s/vmstat" % get_procfs_path())
    except IOError as err:
        # see https://github.com/giampaolo/psutil/issues/722
        msg = (
            "'sin' and 'sout' swap memory stats couldn't "
            + "be determined and were set to 0 (%s)" % str(err)
        )
        warnings.warn(msg, RuntimeWarning, stacklevel=2)
        sin = sout = 0
    else:
        with f:
            sin = sout = None
            for line in f:
                # values are expressed in 4 kilo bytes, we want
                # bytes instead
                if line.startswith(b'pswpin'):
                    sin = int(line.split(b' ')[1]) * 4 * 1024
                elif line.startswith(b'pswpout'):
                    sout = int(line.split(b' ')[1]) * 4 * 1024
                if sin is not None and sout is not None:
                    break
            else:
                # we might get here when dealing with exotic Linux
                # flavors, see:
                # https://github.com/giampaolo/psutil/issues/313
                msg = "'sin' and 'sout' swap memory stats couldn't "
                msg += "be determined and were set to 0"
                warnings.warn(msg, RuntimeWarning, stacklevel=2)
                sin = sout = 0
    return _common.sswap(total, used, free, percent, sin, sout)


# =====================================================================
# --- CPU
# =====================================================================


def cpu_times():
    """Return a named tuple representing the following system-wide
    CPU times:
    (user, nice, system, idle, iowait, irq, softirq [steal, [guest,
     [guest_nice]]])
    Last 3 fields may not be available on all Linux kernel versions.
    """
    procfs_path = get_procfs_path()
    set_scputimes_ntuple(procfs_path)
    with open_binary('%s/stat' % procfs_path) as f:
        values = f.readline().split()
    fields = values[1 : len(scputimes._fields) + 1]
    fields = [float(x) / CLOCK_TICKS for x in fields]
    return scputimes(*fields)


def per_cpu_times():
    """Return a list of namedtuple representing the CPU times
    for every CPU available on the system.
    """
    procfs_path = get_procfs_path()
    set_scputimes_ntuple(procfs_path)
    cpus = []
    with open_binary('%s/stat' % procfs_path) as f:
        # get rid of the first line which refers to system wide CPU stats
        f.readline()
        for line in f:
            if line.startswith(b'cpu'):
                values = line.split()
                fields = values[1 : len(scputimes._fields) + 1]
                fields = [float(x) / CLOCK_TICKS for x in fields]
                entry = scputimes(*fields)
                cpus.append(entry)
        return cpus


def cpu_count_logical():
    """Return the number of logical CPUs in the system."""
    try:
        return os.sysconf("SC_NPROCESSORS_ONLN")
    except ValueError:
        # as a second fallback we try to parse /proc/cpuinfo
        num = 0
        with open_binary('%s/cpuinfo' % get_procfs_path()) as f:
            for line in f:
                if line.lower().startswith(b'processor'):
                    num += 1

        # unknown format (e.g. amrel/sparc architectures), see:
        # https://github.com/giampaolo/psutil/issues/200
        # try to parse /proc/stat as a last resort
        if num == 0:
            search = re.compile(r'cpu\d')
            with open_text('%s/stat' % get_procfs_path()) as f:
                for line in f:
                    line = line.split(' ')[0]
                    if search.match(line):
                        num += 1

        if num == 0:
            # mimic os.cpu_count()
            return None
        return num


def cpu_count_cores():
    """Return the number of CPU cores in the system."""
    # Method #1
    ls = set()
    # These 2 files are the same but */core_cpus_list is newer while
    # */thread_siblings_list is deprecated and may disappear in the future.
    # https://www.kernel.org/doc/Documentation/admin-guide/cputopology.rst
    # https://github.com/giampaolo/psutil/pull/1727#issuecomment-707624964
    # https://lkml.org/lkml/2019/2/26/41
    p1 = "/sys/devices/system/cpu/cpu[0-9]*/topology/core_cpus_list"
    p2 = "/sys/devices/system/cpu/cpu[0-9]*/topology/thread_siblings_list"
    for path in glob.glob(p1) or glob.glob(p2):
        with open_binary(path) as f:
            ls.add(f.read().strip())
    result = len(ls)
    if result != 0:
        return result

    # Method #2
    mapping = {}
    current_info = {}
    with open_binary('%s/cpuinfo' % get_procfs_path()) as f:
        for line in f:
            line = line.strip().lower()
            if not line:
                # new section
                try:
                    mapping[current_info[b'physical id']] = current_info[
                        b'cpu cores'
                    ]
                except KeyError:
                    pass
                current_info = {}
            else:
                # ongoing section
                if line.startswith((b'physical id', b'cpu cores')):
                    key, value = line.split(b'\t:', 1)
                    current_info[key] = int(value)

    result = sum(mapping.values())
    return result or None  # mimic os.cpu_count()


def cpu_stats():
    """Return various CPU stats as a named tuple."""
    with open_binary('%s/stat' % get_procfs_path()) as f:
        ctx_switches = None
        interrupts = None
        soft_interrupts = None
        for line in f:
            if line.startswith(b'ctxt'):
                ctx_switches = int(line.split()[1])
            elif line.startswith(b'intr'):
                interrupts = int(line.split()[1])
            elif line.startswith(b'softirq'):
                soft_interrupts = int(line.split()[1])
            if (
                ctx_switches is not None
                and soft_interrupts is not None
                and interrupts is not None
            ):
                break
    syscalls = 0
    return _common.scpustats(
        ctx_switches, interrupts, soft_interrupts, syscalls
    )


def _cpu_get_cpuinfo_freq():
    """Return current CPU frequency from cpuinfo if available."""
    ret = []
    with open_binary('%s/cpuinfo' % get_procfs_path()) as f:
        for line in f:
            if line.lower().startswith(b'cpu mhz'):
                ret.append(float(line.split(b':', 1)[1]))
    return ret


if os.path.exists("/sys/devices/system/cpu/cpufreq/policy0") or os.path.exists(
    "/sys/devices/system/cpu/cpu0/cpufreq"
):

    def cpu_freq():
        """Return frequency metrics for all CPUs.
        Contrarily to other OSes, Linux updates these values in
        real-time.
        """
        cpuinfo_freqs = _cpu_get_cpuinfo_freq()
        paths = glob.glob(
            "/sys/devices/system/cpu/cpufreq/policy[0-9]*"
        ) or glob.glob("/sys/devices/system/cpu/cpu[0-9]*/cpufreq")
        paths.sort(key=lambda x: int(re.search(r"[0-9]+", x).group()))
        ret = []
        pjoin = os.path.join
        for i, path in enumerate(paths):
            if len(paths) == len(cpuinfo_freqs):
                # take cached value from cpuinfo if available, see:
                # https://github.com/giampaolo/psutil/issues/1851
                curr = cpuinfo_freqs[i] * 1000
            else:
                curr = bcat(pjoin(path, "scaling_cur_freq"), fallback=None)
            if curr is None:
                # Likely an old RedHat, see:
                # https://github.com/giampaolo/psutil/issues/1071
                curr = bcat(pjoin(path, "cpuinfo_cur_freq"), fallback=None)
                if curr is None:
                    msg = "can't find current frequency file"
                    raise NotImplementedError(msg)
            curr = int(curr) / 1000
            max_ = int(bcat(pjoin(path, "scaling_max_freq"))) / 1000
            min_ = int(bcat(pjoin(path, "scaling_min_freq"))) / 1000
            ret.append(_common.scpufreq(curr, min_, max_))
        return ret

else:

    def cpu_freq():
        """Alternate implementation using /proc/cpuinfo.
        min and max frequencies are not available and are set to None.
        """
        return [_common.scpufreq(x, 0.0, 0.0) for x in _cpu_get_cpuinfo_freq()]


# =====================================================================
# --- network
# =====================================================================


net_if_addrs = cext_posix.net_if_addrs


class _Ipv6UnsupportedError(Exception):
    pass


class Connections:
    """A wrapper on top of /proc/net/* files, retrieving per-process
    and system-wide open connections (TCP, UDP, UNIX) similarly to
    "netstat -an".

    Note: in case of UNIX sockets we're only able to determine the
    local endpoint/path, not the one it's connected to.
    According to [1] it would be possible but not easily.

    [1] http://serverfault.com/a/417946
    """

    def __init__(self):
        # The string represents the basename of the corresponding
        # /proc/net/{proto_name} file.
        tcp4 = ("tcp", socket.AF_INET, socket.SOCK_STREAM)
        tcp6 = ("tcp6", socket.AF_INET6, socket.SOCK_STREAM)
        udp4 = ("udp", socket.AF_INET, socket.SOCK_DGRAM)
        udp6 = ("udp6", socket.AF_INET6, socket.SOCK_DGRAM)
        unix = ("unix", socket.AF_UNIX, None)
        self.tmap = {
            "all": (tcp4, tcp6, udp4, udp6, unix),
            "tcp": (tcp4, tcp6),
            "tcp4": (tcp4,),
            "tcp6": (tcp6,),
            "udp": (udp4, udp6),
            "udp4": (udp4,),
            "udp6": (udp6,),
            "unix": (unix,),
            "inet": (tcp4, tcp6, udp4, udp6),
            "inet4": (tcp4, udp4),
            "inet6": (tcp6, udp6),
        }
        self._procfs_path = None

    def get_proc_inodes(self, pid):
        inodes = defaultdict(list)
        for fd in os.listdir("%s/%s/fd" % (self._procfs_path, pid)):
            try:
                inode = readlink("%s/%s/fd/%s" % (self._procfs_path, pid, fd))
            except (FileNotFoundError, ProcessLookupError):
                # ENOENT == file which is gone in the meantime;
                # os.stat('/proc/%s' % self.pid) will be done later
                # to force NSP (if it's the case)
                continue
            except OSError as err:
                if err.errno == errno.EINVAL:
                    # not a link
                    continue
                if err.errno == errno.ENAMETOOLONG:
                    # file name too long
                    debug(err)
                    continue
                raise
            else:
                if inode.startswith('socket:['):
                    # the process is using a socket
                    inode = inode[8:][:-1]
                    inodes[inode].append((pid, int(fd)))
        return inodes

    def get_all_inodes(self):
        inodes = {}
        for pid in pids():
            try:
                inodes.update(self.get_proc_inodes(pid))
            except (FileNotFoundError, ProcessLookupError, PermissionError):
                # os.listdir() is gonna raise a lot of access denied
                # exceptions in case of unprivileged user; that's fine
                # as we'll just end up returning a connection with PID
                # and fd set to None anyway.
                # Both netstat -an and lsof does the same so it's
                # unlikely we can do any better.
                # ENOENT just means a PID disappeared on us.
                continue
        return inodes

    @staticmethod
    def decode_address(addr, family):
        """Accept an "ip:port" address as displayed in /proc/net/*
        and convert it into a human readable form, like:

        "0500000A:0016" -> ("10.0.0.5", 22)
        "0000000000000000FFFF00000100007F:9E49" -> ("::ffff:127.0.0.1", 40521)

        The IP address portion is a little or big endian four-byte
        hexadecimal number; that is, the least significant byte is listed
        first, so we need to reverse the order of the bytes to convert it
        to an IP address.
        The port is represented as a two-byte hexadecimal number.

        Reference:
        http://linuxdevcenter.com/pub/a/linux/2000/11/16/LinuxAdmin.html
        """
        ip, port = addr.split(':')
        port = int(port, 16)
        # this usually refers to a local socket in listen mode with
        # no end-points connected
        if not port:
            return ()
        if PY3:
            ip = ip.encode('ascii')
        if family == socket.AF_INET:
            # see: https://github.com/giampaolo/psutil/issues/201
            if LITTLE_ENDIAN:
                ip = socket.inet_ntop(family, base64.b16decode(ip)[::-1])
            else:
                ip = socket.inet_ntop(family, base64.b16decode(ip))
        else:  # IPv6
            ip = base64.b16decode(ip)
            try:
                # see: https://github.com/giampaolo/psutil/issues/201
                if LITTLE_ENDIAN:
                    ip = socket.inet_ntop(
                        socket.AF_INET6,
                        struct.pack('>4I', *struct.unpack('<4I', ip)),
                    )
                else:
                    ip = socket.inet_ntop(
                        socket.AF_INET6,
                        struct.pack('<4I', *struct.unpack('<4I', ip)),
                    )
            except ValueError:
                # see: https://github.com/giampaolo/psutil/issues/623
                if not supports_ipv6():
                    raise _Ipv6UnsupportedError
                else:
                    raise
        return _common.addr(ip, port)

    @staticmethod
    def process_inet(file, family, type_, inodes, filter_pid=None):
        """Parse /proc/net/tcp* and /proc/net/udp* files."""
        if file.endswith('6') and not os.path.exists(file):
            # IPv6 not supported
            return
        with open_text(file) as f:
            f.readline()  # skip the first line
            for lineno, line in enumerate(f, 1):
                try:
                    _, laddr, raddr, status, _, _, _, _, _, inode = (
                        line.split()[:10]
                    )
                except ValueError:
                    raise RuntimeError(
                        "error while parsing %s; malformed line %s %r"
                        % (file, lineno, line)
                    )
                if inode in inodes:
                    # # We assume inet sockets are unique, so we error
                    # # out if there are multiple references to the
                    # # same inode. We won't do this for UNIX sockets.
                    # if len(inodes[inode]) > 1 and family != socket.AF_UNIX:
                    #     raise ValueError("ambiguous inode with multiple "
                    #                      "PIDs references")
                    pid, fd = inodes[inode][0]
                else:
                    pid, fd = None, -1
                if filter_pid is not None and filter_pid != pid:
                    continue
                else:
                    if type_ == socket.SOCK_STREAM:
                        status = TCP_STATUSES[status]
                    else:
                        status = _common.CONN_NONE
                    try:
                        laddr = Connections.decode_address(laddr, family)
                        raddr = Connections.decode_address(raddr, family)
                    except _Ipv6UnsupportedError:
                        continue
                    yield (fd, family, type_, laddr, raddr, status, pid)

    @staticmethod
    def process_unix(file, family, inodes, filter_pid=None):
        """Parse /proc/net/unix files."""
        with open_text(file) as f:
            f.readline()  # skip the first line
            for line in f:
                tokens = line.split()
                try:
                    _, _, _, _, type_, _, inode = tokens[0:7]
                except ValueError:
                    if ' ' not in line:
                        # see: https://github.com/giampaolo/psutil/issues/766
                        continue
                    raise RuntimeError(
                        "error while parsing %s; malformed line %r"
                        % (file, line)
                    )
                if inode in inodes:  # noqa
                    # With UNIX sockets we can have a single inode
                    # referencing many file descriptors.
                    pairs = inodes[inode]
                else:
                    pairs = [(None, -1)]
                for pid, fd in pairs:
                    if filter_pid is not None and filter_pid != pid:
                        continue
                    else:
                        path = tokens[-1] if len(tokens) == 8 else ''
                        type_ = _common.socktype_to_enum(int(type_))
                        # XXX: determining the remote endpoint of a
                        # UNIX socket on Linux is not possible, see:
                        # https://serverfault.com/questions/252723/
                        raddr = ""
                        status = _common.CONN_NONE
                        yield (fd, family, type_, path, raddr, status, pid)

    def retrieve(self, kind, pid=None):
        if kind not in self.tmap:
            raise ValueError(
                "invalid %r kind argument; choose between %s"
                % (kind, ', '.join([repr(x) for x in self.tmap]))
            )
        self._procfs_path = get_procfs_path()
        if pid is not None:
            inodes = self.get_proc_inodes(pid)
            if not inodes:
                # no connections for this process
                return []
        else:
            inodes = self.get_all_inodes()
        ret = set()
        for proto_name, family, type_ in self.tmap[kind]:
            path = "%s/net/%s" % (self._procfs_path, proto_name)
            if family in (socket.AF_INET, socket.AF_INET6):
                ls = self.process_inet(
                    path, family, type_, inodes, filter_pid=pid
                )
            else:
                ls = self.process_unix(path, family, inodes, filter_pid=pid)
            for fd, family, type_, laddr, raddr, status, bound_pid in ls:
                if pid:
                    conn = _common.pconn(
                        fd, family, type_, laddr, raddr, status
                    )
                else:
                    conn = _common.sconn(
                        fd, family, type_, laddr, raddr, status, bound_pid
                    )
                ret.add(conn)
        return list(ret)


_connections = Connections()


def net_connections(kind='inet'):
    """Return system-wide open connections."""
    return _connections.retrieve(kind)


def net_io_counters():
    """Return network I/O statistics for every network interface
    installed on the system as a dict of raw tuples.
    """
    with open_text("%s/net/dev" % get_procfs_path()) as f:
        lines = f.readlines()
    retdict = {}
    for line in lines[2:]:
        colon = line.rfind(':')
        assert colon > 0, repr(line)
        name = line[:colon].strip()
        fields = line[colon + 1 :].strip().split()

        # in
        (
            bytes_recv,
            packets_recv,
            errin,
            dropin,
            fifoin,  # unused
            framein,  # unused
            compressedin,  # unused
            multicastin,  # unused
            # out
            bytes_sent,
            packets_sent,
            errout,
            dropout,
            fifoout,  # unused
            collisionsout,  # unused
            carrierout,  # unused
            compressedout,
        ) = map(int, fields)

        retdict[name] = (
            bytes_sent,
            bytes_recv,
            packets_sent,
            packets_recv,
            errin,
            errout,
            dropin,
            dropout,
        )
    return retdict


def net_if_stats():
    """Get NIC stats (isup, duplex, speed, mtu)."""
    duplex_map = {
        cext.DUPLEX_FULL: NIC_DUPLEX_FULL,
        cext.DUPLEX_HALF: NIC_DUPLEX_HALF,
        cext.DUPLEX_UNKNOWN: NIC_DUPLEX_UNKNOWN,
    }
    names = net_io_counters().keys()
    ret = {}
    for name in names:
        try:
            mtu = cext_posix.net_if_mtu(name)
            flags = cext_posix.net_if_flags(name)
            duplex, speed = cext.net_if_duplex_speed(name)
        except OSError as err:
            # https://github.com/giampaolo/psutil/issues/1279
            if err.errno != errno.ENODEV:
                raise
            else:
                debug(err)
        else:
            output_flags = ','.join(flags)
            isup = 'running' in flags
            ret[name] = _common.snicstats(
                isup, duplex_map[duplex], speed, mtu, output_flags
            )
    return ret


# =====================================================================
# --- disks
# =====================================================================


disk_usage = _psposix.disk_usage


def disk_io_counters(perdisk=False):
    """Return disk I/O statistics for every disk installed on the
    system as a dict of raw tuples.
    """

    def read_procfs():
        # OK, this is a bit confusing. The format of /proc/diskstats can
        # have 3 variations.
        # On Linux 2.4 each line has always 15 fields, e.g.:
        # "3     0   8 hda 8 8 8 8 8 8 8 8 8 8 8"
        # On Linux 2.6+ each line *usually* has 14 fields, and the disk
        # name is in another position, like this:
        # "3    0   hda 8 8 8 8 8 8 8 8 8 8 8"
        # ...unless (Linux 2.6) the line refers to a partition instead
        # of a disk, in which case the line has less fields (7):
        # "3    1   hda1 8 8 8 8"
        # 4.18+ has 4 fields added:
        # "3    0   hda 8 8 8 8 8 8 8 8 8 8 8 0 0 0 0"
        # 5.5 has 2 more fields.
        # See:
        # https://www.kernel.org/doc/Documentation/iostats.txt
        # https://www.kernel.org/doc/Documentation/ABI/testing/procfs-diskstats
        with open_text("%s/diskstats" % get_procfs_path()) as f:
            lines = f.readlines()
        for line in lines:
            fields = line.split()
            flen = len(fields)
            # fmt: off
            if flen == 15:
                # Linux 2.4
                name = fields[3]
                reads = int(fields[2])
                (reads_merged, rbytes, rtime, writes, writes_merged,
                    wbytes, wtime, _, busy_time, _) = map(int, fields[4:14])
            elif flen == 14 or flen >= 18:
                # Linux 2.6+, line referring to a disk
                name = fields[2]
                (reads, reads_merged, rbytes, rtime, writes, writes_merged,
                    wbytes, wtime, _, busy_time, _) = map(int, fields[3:14])
            elif flen == 7:
                # Linux 2.6+, line referring to a partition
                name = fields[2]
                reads, rbytes, writes, wbytes = map(int, fields[3:])
                rtime = wtime = reads_merged = writes_merged = busy_time = 0
            else:
                raise ValueError("not sure how to interpret line %r" % line)
            yield (name, reads, writes, rbytes, wbytes, rtime, wtime,
                   reads_merged, writes_merged, busy_time)
            # fmt: on

    def read_sysfs():
        for block in os.listdir('/sys/block'):
            for root, _, files in os.walk(os.path.join('/sys/block', block)):
                if 'stat' not in files:
                    continue
                with open_text(os.path.join(root, 'stat')) as f:
                    fields = f.read().strip().split()
                name = os.path.basename(root)
                # fmt: off
                (reads, reads_merged, rbytes, rtime, writes, writes_merged,
                    wbytes, wtime, _, busy_time) = map(int, fields[:10])
                yield (name, reads, writes, rbytes, wbytes, rtime,
                       wtime, reads_merged, writes_merged, busy_time)
                # fmt: on

    if os.path.exists('%s/diskstats' % get_procfs_path()):
        gen = read_procfs()
    elif os.path.exists('/sys/block'):
        gen = read_sysfs()
    else:
        raise NotImplementedError(
            "%s/diskstats nor /sys/block filesystem are available on this "
            "system"
            % get_procfs_path()
        )

    retdict = {}
    for entry in gen:
        # fmt: off
        (name, reads, writes, rbytes, wbytes, rtime, wtime, reads_merged,
            writes_merged, busy_time) = entry
        if not perdisk and not is_storage_device(name):
            # perdisk=False means we want to calculate totals so we skip
            # partitions (e.g. 'sda1', 'nvme0n1p1') and only include
            # base disk devices (e.g. 'sda', 'nvme0n1'). Base disks
            # include a total of all their partitions + some extra size
            # of their own:
            #     $ cat /proc/diskstats
            #     259       0 sda 10485760 ...
            #     259       1 sda1 5186039 ...
            #     259       1 sda2 5082039 ...
            # See:
            # https://github.com/giampaolo/psutil/pull/1313
            continue

        rbytes *= DISK_SECTOR_SIZE
        wbytes *= DISK_SECTOR_SIZE
        retdict[name] = (reads, writes, rbytes, wbytes, rtime, wtime,
                         reads_merged, writes_merged, busy_time)
        # fmt: on

    return retdict


class RootFsDeviceFinder:
    """disk_partitions() may return partitions with device == "/dev/root"
    or "rootfs". This container class uses different strategies to try to
    obtain the real device path. Resources:
    https://bootlin.com/blog/find-root-device/
    https://www.systutorials.com/how-to-find-the-disk-where-root-is-on-in-bash-on-linux/.
    """

    __slots__ = ['major', 'minor']

    def __init__(self):
        dev = os.stat("/").st_dev
        self.major = os.major(dev)
        self.minor = os.minor(dev)

    def ask_proc_partitions(self):
        with open_text("%s/partitions" % get_procfs_path()) as f:
            for line in f.readlines()[2:]:
                fields = line.split()
                if len(fields) < 4:  # just for extra safety
                    continue
                major = int(fields[0]) if fields[0].isdigit() else None
                minor = int(fields[1]) if fields[1].isdigit() else None
                name = fields[3]
                if major == self.major and minor == self.minor:
                    if name:  # just for extra safety
                        return "/dev/%s" % name

    def ask_sys_dev_block(self):
        path = "/sys/dev/block/%s:%s/uevent" % (self.major, self.minor)
        with open_text(path) as f:
            for line in f:
                if line.startswith("DEVNAME="):
                    name = line.strip().rpartition("DEVNAME=")[2]
                    if name:  # just for extra safety
                        return "/dev/%s" % name

    def ask_sys_class_block(self):
        needle = "%s:%s" % (self.major, self.minor)
        files = glob.iglob("/sys/class/block/*/dev")
        for file in files:
            try:
                f = open_text(file)
            except FileNotFoundError:  # race condition
                continue
            else:
                with f:
                    data = f.read().strip()
                    if data == needle:
                        name = os.path.basename(os.path.dirname(file))
                        return "/dev/%s" % name

    def find(self):
        path = None
        if path is None:
            try:
                path = self.ask_proc_partitions()
            except (IOError, OSError) as err:
                debug(err)
        if path is None:
            try:
                path = self.ask_sys_dev_block()
            except (IOError, OSError) as err:
                debug(err)
        if path is None:
            try:
                path = self.ask_sys_class_block()
            except (IOError, OSError) as err:
                debug(err)
        # We use exists() because the "/dev/*" part of the path is hard
        # coded, so we want to be sure.
        if path is not None and os.path.exists(path):
            return path


def disk_partitions(all=False):
    """Return mounted disk partitions as a list of namedtuples."""
    fstypes = set()
    procfs_path = get_procfs_path()
    if not all:
        with open_text("%s/filesystems" % procfs_path) as f:
            for line in f:
                line = line.strip()
                if not line.startswith("nodev"):
                    fstypes.add(line.strip())
                else:
                    # ignore all lines starting with "nodev" except "nodev zfs"
                    fstype = line.split("\t")[1]
                    if fstype == "zfs":
                        fstypes.add("zfs")

    # See: https://github.com/giampaolo/psutil/issues/1307
    if procfs_path == "/proc" and os.path.isfile('/etc/mtab'):
        mounts_path = os.path.realpath("/etc/mtab")
    else:
        mounts_path = os.path.realpath("%s/self/mounts" % procfs_path)

    retlist = []
    partitions = cext.disk_partitions(mounts_path)
    for partition in partitions:
        device, mountpoint, fstype, opts = partition
        if device == 'none':
            device = ''
        if device in ("/dev/root", "rootfs"):
            device = RootFsDeviceFinder().find() or device
        if not all:
            if device == '' or fstype not in fstypes:
                continue
        maxfile = maxpath = None  # set later
        ntuple = _common.sdiskpart(
            device, mountpoint, fstype, opts, maxfile, maxpath
        )
        retlist.append(ntuple)

    return retlist


# =====================================================================
# --- sensors
# =====================================================================


def sensors_temperatures():
    """Return hardware (CPU and others) temperatures as a dict
    including hardware name, label, current, max and critical
    temperatures.

    Implementation notes:
    - /sys/class/hwmon looks like the most recent interface to
      retrieve this info, and this implementation relies on it
      only (old distros will probably use something else)
    - lm-sensors on Ubuntu 16.04 relies on /sys/class/hwmon
    - /sys/class/thermal/thermal_zone* is another one but it's more
      difficult to parse
    """
    ret = collections.defaultdict(list)
    basenames = glob.glob('/sys/class/hwmon/hwmon*/temp*_*')
    # CentOS has an intermediate /device directory:
    # https://github.com/giampaolo/psutil/issues/971
    # https://github.com/nicolargo/glances/issues/1060
    basenames.extend(glob.glob('/sys/class/hwmon/hwmon*/device/temp*_*'))
    basenames = sorted(set([x.split('_')[0] for x in basenames]))

    # Only add the coretemp hwmon entries if they're not already in
    # /sys/class/hwmon/
    # https://github.com/giampaolo/psutil/issues/1708
    # https://github.com/giampaolo/psutil/pull/1648
    basenames2 = glob.glob(
        '/sys/devices/platform/coretemp.*/hwmon/hwmon*/temp*_*'
    )
    repl = re.compile('/sys/devices/platform/coretemp.*/hwmon/')
    for name in basenames2:
        altname = repl.sub('/sys/class/hwmon/', name)
        if altname not in basenames:
            basenames.append(name)

    for base in basenames:
        try:
            path = base + '_input'
            current = float(bcat(path)) / 1000.0
            path = os.path.join(os.path.dirname(base), 'name')
            unit_name = cat(path).strip()
        except (IOError, OSError, ValueError):
            # A lot of things can go wrong here, so let's just skip the
            # whole entry. Sure thing is Linux's /sys/class/hwmon really
            # is a stinky broken mess.
            # https://github.com/giampaolo/psutil/issues/1009
            # https://github.com/giampaolo/psutil/issues/1101
            # https://github.com/giampaolo/psutil/issues/1129
            # https://github.com/giampaolo/psutil/issues/1245
            # https://github.com/giampaolo/psutil/issues/1323
            continue

        high = bcat(base + '_max', fallback=None)
        critical = bcat(base + '_crit', fallback=None)
        label = cat(base + '_label', fallback='').strip()

        if high is not None:
            try:
                high = float(high) / 1000.0
            except ValueError:
                high = None
        if critical is not None:
            try:
                critical = float(critical) / 1000.0
            except ValueError:
                critical = None

        ret[unit_name].append((label, current, high, critical))

    # Indication that no sensors were detected in /sys/class/hwmon/
    if not basenames:
        basenames = glob.glob('/sys/class/thermal/thermal_zone*')
        basenames = sorted(set(basenames))

        for base in basenames:
            try:
                path = os.path.join(base, 'temp')
                current = float(bcat(path)) / 1000.0
                path = os.path.join(base, 'type')
                unit_name = cat(path).strip()
            except (IOError, OSError, ValueError) as err:
                debug(err)
                continue

            trip_paths = glob.glob(base + '/trip_point*')
            trip_points = set([
                '_'.join(os.path.basename(p).split('_')[0:3])
                for p in trip_paths
            ])
            critical = None
            high = None
            for trip_point in trip_points:
                path = os.path.join(base, trip_point + "_type")
                trip_type = cat(path, fallback='').strip()
                if trip_type == 'critical':
                    critical = bcat(
                        os.path.join(base, trip_point + "_temp"), fallback=None
                    )
                elif trip_type == 'high':
                    high = bcat(
                        os.path.join(base, trip_point + "_temp"), fallback=None
                    )

                if high is not None:
                    try:
                        high = float(high) / 1000.0
                    except ValueError:
                        high = None
                if critical is not None:
                    try:
                        critical = float(critical) / 1000.0
                    except ValueError:
                        critical = None

            ret[unit_name].append(('', current, high, critical))

    return dict(ret)


def sensors_fans():
    """Return hardware fans info (for CPU and other peripherals) as a
    dict including hardware label and current speed.

    Implementation notes:
    - /sys/class/hwmon looks like the most recent interface to
      retrieve this info, and this implementation relies on it
      only (old distros will probably use something else)
    - lm-sensors on Ubuntu 16.04 relies on /sys/class/hwmon
    """
    ret = collections.defaultdict(list)
    basenames = glob.glob('/sys/class/hwmon/hwmon*/fan*_*')
    if not basenames:
        # CentOS has an intermediate /device directory:
        # https://github.com/giampaolo/psutil/issues/971
        basenames = glob.glob('/sys/class/hwmon/hwmon*/device/fan*_*')

    basenames = sorted(set([x.split('_')[0] for x in basenames]))
    for base in basenames:
        try:
            current = int(bcat(base + '_input'))
        except (IOError, OSError) as err:
            debug(err)
            continue
        unit_name = cat(os.path.join(os.path.dirname(base), 'name')).strip()
        label = cat(base + '_label', fallback='').strip()
        ret[unit_name].append(_common.sfan(label, current))

    return dict(ret)


def sensors_battery():
    """Return battery information.
    Implementation note: it appears /sys/class/power_supply/BAT0/
    directory structure may vary and provide files with the same
    meaning but under different names, see:
    https://github.com/giampaolo/psutil/issues/966.
    """
    null = object()

    def multi_bcat(*paths):
        """Attempt to read the content of multiple files which may
        not exist. If none of them exist return None.
        """
        for path in paths:
            ret = bcat(path, fallback=null)
            if ret != null:
                try:
                    return int(ret)
                except ValueError:
                    return ret.strip()
        return None

    bats = [
        x
        for x in os.listdir(POWER_SUPPLY_PATH)
        if x.startswith('BAT') or 'battery' in x.lower()
    ]
    if not bats:
        return None
    # Get the first available battery. Usually this is "BAT0", except
    # some rare exceptions:
    # https://github.com/giampaolo/psutil/issues/1238
    root = os.path.join(POWER_SUPPLY_PATH, sorted(bats)[0])

    # Base metrics.
    energy_now = multi_bcat(root + "/energy_now", root + "/charge_now")
    power_now = multi_bcat(root + "/power_now", root + "/current_now")
    energy_full = multi_bcat(root + "/energy_full", root + "/charge_full")
    time_to_empty = multi_bcat(root + "/time_to_empty_now")

    # Percent. If we have energy_full the percentage will be more
    # accurate compared to reading /capacity file (float vs. int).
    if energy_full is not None and energy_now is not None:
        try:
            percent = 100.0 * energy_now / energy_full
        except ZeroDivisionError:
            percent = 0.0
    else:
        percent = int(cat(root + "/capacity", fallback=-1))
        if percent == -1:
            return None

    # Is AC power cable plugged in?
    # Note: AC0 is not always available and sometimes (e.g. CentOS7)
    # it's called "AC".
    power_plugged = None
    online = multi_bcat(
        os.path.join(POWER_SUPPLY_PATH, "AC0/online"),
        os.path.join(POWER_SUPPLY_PATH, "AC/online"),
    )
    if online is not None:
        power_plugged = online == 1
    else:
        status = cat(root + "/status", fallback="").strip().lower()
        if status == "discharging":
            power_plugged = False
        elif status in ("charging", "full"):
            power_plugged = True

    # Seconds left.
    # Note to self: we may also calculate the charging ETA as per:
    # https://github.com/thialfihar/dotfiles/blob/
    #     013937745fd9050c30146290e8f963d65c0179e6/bin/battery.py#L55
    if power_plugged:
        secsleft = _common.POWER_TIME_UNLIMITED
    elif energy_now is not None and power_now is not None:
        try:
            secsleft = int(energy_now / power_now * 3600)
        except ZeroDivisionError:
            secsleft = _common.POWER_TIME_UNKNOWN
    elif time_to_empty is not None:
        secsleft = int(time_to_empty * 60)
        if secsleft < 0:
            secsleft = _common.POWER_TIME_UNKNOWN
    else:
        secsleft = _common.POWER_TIME_UNKNOWN

    return _common.sbattery(percent, secsleft, power_plugged)


# =====================================================================
# --- other system functions
# =====================================================================


def users():
    """Return currently connected users as a list of namedtuples."""
    retlist = []
    rawlist = cext.users()
    for item in rawlist:
        user, tty, hostname, tstamp, pid = item
        nt = _common.suser(user, tty or None, hostname, tstamp, pid)
        retlist.append(nt)
    return retlist


def boot_time():
    """Return the system boot time expressed in seconds since the epoch."""
    global BOOT_TIME
    path = '%s/stat' % get_procfs_path()
    with open_binary(path) as f:
        for line in f:
            if line.startswith(b'btime'):
                ret = float(line.strip().split()[1])
                BOOT_TIME = ret
                return ret
        raise RuntimeError("line 'btime' not found in %s" % path)


# =====================================================================
# --- processes
# =====================================================================


def pids():
    """Returns a list of PIDs currently running on the system."""
    return [int(x) for x in os.listdir(b(get_procfs_path())) if x.isdigit()]


def pid_exists(pid):
    """Check for the existence of a unix PID. Linux TIDs are not
    supported (always return False).
    """
    if not _psposix.pid_exists(pid):
        return False
    else:
        # Linux's apparently does not distinguish between PIDs and TIDs
        # (thread IDs).
        # listdir("/proc") won't show any TID (only PIDs) but
        # os.stat("/proc/{tid}") will succeed if {tid} exists.
        # os.kill() can also be passed a TID. This is quite confusing.
        # In here we want to enforce this distinction and support PIDs
        # only, see:
        # https://github.com/giampaolo/psutil/issues/687
        try:
            # Note: already checked that this is faster than using a
            # regular expr. Also (a lot) faster than doing
            # 'return pid in pids()'
            path = "%s/%s/status" % (get_procfs_path(), pid)
            with open_binary(path) as f:
                for line in f:
                    if line.startswith(b"Tgid:"):
                        tgid = int(line.split()[1])
                        # If tgid and pid are the same then we're
                        # dealing with a process PID.
                        return tgid == pid
                raise ValueError("'Tgid' line not found in %s" % path)
        except (EnvironmentError, ValueError):
            return pid in pids()


def ppid_map():
    """Obtain a {pid: ppid, ...} dict for all running processes in
    one shot. Used to speed up Process.children().
    """
    ret = {}
    procfs_path = get_procfs_path()
    for pid in pids():
        try:
            with open_binary("%s/%s/stat" % (procfs_path, pid)) as f:
                data = f.read()
        except (FileNotFoundError, ProcessLookupError):
            # Note: we should be able to access /stat for all processes
            # aka it's unlikely we'll bump into EPERM, which is good.
            pass
        else:
            rpar = data.rfind(b')')
            dset = data[rpar + 2 :].split()
            ppid = int(dset[1])
            ret[pid] = ppid
    return ret


def wrap_exceptions(fun):
    """Decorator which translates bare OSError and IOError exceptions
    into NoSuchProcess and AccessDenied.
    """

    @functools.wraps(fun)
    def wrapper(self, *args, **kwargs):
        try:
            return fun(self, *args, **kwargs)
        except PermissionError:
            raise AccessDenied(self.pid, self._name)
        except ProcessLookupError:
            self._raise_if_zombie()
            raise NoSuchProcess(self.pid, self._name)
        except FileNotFoundError:
            self._raise_if_zombie()
            if not os.path.exists("%s/%s" % (self._procfs_path, self.pid)):
                raise NoSuchProcess(self.pid, self._name)
            raise

    return wrapper


class Process:
    """Linux process implementation."""

    __slots__ = ["pid", "_name", "_ppid", "_procfs_path", "_cache"]

    def __init__(self, pid):
        self.pid = pid
        self._name = None
        self._ppid = None
        self._procfs_path = get_procfs_path()

    def _is_zombie(self):
        # Note: most of the times Linux is able to return info about the
        # process even if it's a zombie, and /proc/{pid} will exist.
        # There are some exceptions though, like exe(), cmdline() and
        # memory_maps(). In these cases /proc/{pid}/{file} exists but
        # it's empty. Instead of returning a "null" value we'll raise an
        # exception.
        try:
            data = bcat("%s/%s/stat" % (self._procfs_path, self.pid))
        except (IOError, OSError):
            return False
        else:
            rpar = data.rfind(b')')
            status = data[rpar + 2 : rpar + 3]
            return status == b"Z"

    def _raise_if_zombie(self):
        if self._is_zombie():
            raise ZombieProcess(self.pid, self._name, self._ppid)

    def _raise_if_not_alive(self):
        """Raise NSP if the process disappeared on us."""
        # For those C function who do not raise NSP, possibly returning
        # incorrect or incomplete result.
        os.stat('%s/%s' % (self._procfs_path, self.pid))

    @wrap_exceptions
    @memoize_when_activated
    def _parse_stat_file(self):
        """Parse /proc/{pid}/stat file and return a dict with various
        process info.
        Using "man proc" as a reference: where "man proc" refers to
        position N always subtract 3 (e.g ppid position 4 in
        'man proc' == position 1 in here).
        The return value is cached in case oneshot() ctx manager is
        in use.
        """
        data = bcat("%s/%s/stat" % (self._procfs_path, self.pid))
        # Process name is between parentheses. It can contain spaces and
        # other parentheses. This is taken into account by looking for
        # the first occurrence of "(" and the last occurrence of ")".
        rpar = data.rfind(b')')
        name = data[data.find(b'(') + 1 : rpar]
        fields = data[rpar + 2 :].split()

        ret = {}
        ret['name'] = name
        ret['status'] = fields[0]
        ret['ppid'] = fields[1]
        ret['ttynr'] = fields[4]
        ret['utime'] = fields[11]
        ret['stime'] = fields[12]
        ret['children_utime'] = fields[13]
        ret['children_stime'] = fields[14]
        ret['create_time'] = fields[19]
        ret['cpu_num'] = fields[36]
        ret['blkio_ticks'] = fields[39]  # aka 'delayacct_blkio_ticks'

        return ret

    @wrap_exceptions
    @memoize_when_activated
    def _read_status_file(self):
        """Read /proc/{pid}/stat file and return its content.
        The return value is cached in case oneshot() ctx manager is
        in use.
        """
        with open_binary("%s/%s/status" % (self._procfs_path, self.pid)) as f:
            return f.read()

    @wrap_exceptions
    @memoize_when_activated
    def _read_smaps_file(self):
        with open_binary("%s/%s/smaps" % (self._procfs_path, self.pid)) as f:
            return f.read().strip()

    def oneshot_enter(self):
        self._parse_stat_file.cache_activate(self)
        self._read_status_file.cache_activate(self)
        self._read_smaps_file.cache_activate(self)

    def oneshot_exit(self):
        self._parse_stat_file.cache_deactivate(self)
        self._read_status_file.cache_deactivate(self)
        self._read_smaps_file.cache_deactivate(self)

    @wrap_exceptions
    def name(self):
        name = self._parse_stat_file()['name']
        if PY3:
            name = decode(name)
        # XXX - gets changed later and probably needs refactoring
        return name

    @wrap_exceptions
    def exe(self):
        try:
            return readlink("%s/%s/exe" % (self._procfs_path, self.pid))
        except (FileNotFoundError, ProcessLookupError):
            self._raise_if_zombie()
            # no such file error; might be raised also if the
            # path actually exists for system processes with
            # low pids (about 0-20)
            if os.path.lexists("%s/%s" % (self._procfs_path, self.pid)):
                return ""
            raise

    @wrap_exceptions
    def cmdline(self):
        with open_text("%s/%s/cmdline" % (self._procfs_path, self.pid)) as f:
            data = f.read()
        if not data:
            # may happen in case of zombie process
            self._raise_if_zombie()
            return []
        # 'man proc' states that args are separated by null bytes '\0'
        # and last char is supposed to be a null byte. Nevertheless
        # some processes may change their cmdline after being started
        # (via setproctitle() or similar), they are usually not
        # compliant with this rule and use spaces instead. Google
        # Chrome process is an example. See:
        # https://github.com/giampaolo/psutil/issues/1179
        sep = '\x00' if data.endswith('\x00') else ' '
        if data.endswith(sep):
            data = data[:-1]
        cmdline = data.split(sep)
        # Sometimes last char is a null byte '\0' but the args are
        # separated by spaces, see: https://github.com/giampaolo/psutil/
        # issues/1179#issuecomment-552984549
        if sep == '\x00' and len(cmdline) == 1 and ' ' in data:
            cmdline = data.split(' ')
        return cmdline

    @wrap_exceptions
    def environ(self):
        with open_text("%s/%s/environ" % (self._procfs_path, self.pid)) as f:
            data = f.read()
        return parse_environ_block(data)

    @wrap_exceptions
    def terminal(self):
        tty_nr = int(self._parse_stat_file()['ttynr'])
        tmap = _psposix.get_terminal_map()
        try:
            return tmap[tty_nr]
        except KeyError:
            return None

    # May not be available on old kernels.
    if os.path.exists('/proc/%s/io' % os.getpid()):

        @wrap_exceptions
        def io_counters(self):
            fname = "%s/%s/io" % (self._procfs_path, self.pid)
            fields = {}
            with open_binary(fname) as f:
                for line in f:
                    # https://github.com/giampaolo/psutil/issues/1004
                    line = line.strip()
                    if line:
                        try:
                            name, value = line.split(b': ')
                        except ValueError:
                            # https://github.com/giampaolo/psutil/issues/1004
                            continue
                        else:
                            fields[name] = int(value)
            if not fields:
                raise RuntimeError("%s file was empty" % fname)
            try:
                return pio(
                    fields[b'syscr'],  # read syscalls
                    fields[b'syscw'],  # write syscalls
                    fields[b'read_bytes'],  # read bytes
                    fields[b'write_bytes'],  # write bytes
                    fields[b'rchar'],  # read chars
                    fields[b'wchar'],  # write chars
                )
            except KeyError as err:
                raise ValueError(
                    "%r field was not found in %s; found fields are %r"
                    % (err.args[0], fname, fields)
                )

    @wrap_exceptions
    def cpu_times(self):
        values = self._parse_stat_file()
        utime = float(values['utime']) / CLOCK_TICKS
        stime = float(values['stime']) / CLOCK_TICKS
        children_utime = float(values['children_utime']) / CLOCK_TICKS
        children_stime = float(values['children_stime']) / CLOCK_TICKS
        iowait = float(values['blkio_ticks']) / CLOCK_TICKS
        return pcputimes(utime, stime, children_utime, children_stime, iowait)

    @wrap_exceptions
    def cpu_num(self):
        """What CPU the process is on."""
        return int(self._parse_stat_file()['cpu_num'])

    @wrap_exceptions
    def wait(self, timeout=None):
        return _psposix.wait_pid(self.pid, timeout, self._name)

    @wrap_exceptions
    def create_time(self):
        ctime = float(self._parse_stat_file()['create_time'])
        # According to documentation, starttime is in field 21 and the
        # unit is jiffies (clock ticks).
        # We first divide it for clock ticks and then add uptime returning
        # seconds since the epoch.
        # Also use cached value if available.
        bt = BOOT_TIME or boot_time()
        return (ctime / CLOCK_TICKS) + bt

    @wrap_exceptions
    def memory_info(self):
        #  ============================================================
        # | FIELD  | DESCRIPTION                         | AKA  | TOP  |
        #  ============================================================
        # | rss    | resident set size                   |      | RES  |
        # | vms    | total program size                  | size | VIRT |
        # | shared | shared pages (from shared mappings) |      | SHR  |
        # | text   | text ('code')                       | trs  | CODE |
        # | lib    | library (unused in Linux 2.6)       | lrs  |      |
        # | data   | data + stack                        | drs  | DATA |
        # | dirty  | dirty pages (unused in Linux 2.6)   | dt   |      |
        #  ============================================================
        with open_binary("%s/%s/statm" % (self._procfs_path, self.pid)) as f:
            vms, rss, shared, text, lib, data, dirty = (
                int(x) * PAGESIZE for x in f.readline().split()[:7]
            )
        return pmem(rss, vms, shared, text, lib, data, dirty)

    if HAS_PROC_SMAPS_ROLLUP or HAS_PROC_SMAPS:

        def _parse_smaps_rollup(self):
            # /proc/pid/smaps_rollup was added to Linux in 2017. Faster
            # than /proc/pid/smaps. It reports higher PSS than */smaps
            # (from 1k up to 200k higher; tested against all processes).
            # IMPORTANT: /proc/pid/smaps_rollup is weird, because it
            # raises ESRCH / ENOENT for many PIDs, even if they're alive
            # (also as root). In that case we'll use /proc/pid/smaps as
            # fallback, which is slower but has a +50% success rate
            # compared to /proc/pid/smaps_rollup.
            uss = pss = swap = 0
            with open_binary(
                "{}/{}/smaps_rollup".format(self._procfs_path, self.pid)
            ) as f:
                for line in f:
                    if line.startswith(b"Private_"):
                        # Private_Clean, Private_Dirty, Private_Hugetlb
                        uss += int(line.split()[1]) * 1024
                    elif line.startswith(b"Pss:"):
                        pss = int(line.split()[1]) * 1024
                    elif line.startswith(b"Swap:"):
                        swap = int(line.split()[1]) * 1024
            return (uss, pss, swap)

        @wrap_exceptions
        def _parse_smaps(
            self,
            # Gets Private_Clean, Private_Dirty, Private_Hugetlb.
            _private_re=re.compile(br"\nPrivate.*:\s+(\d+)"),
            _pss_re=re.compile(br"\nPss\:\s+(\d+)"),
            _swap_re=re.compile(br"\nSwap\:\s+(\d+)"),
        ):
            # /proc/pid/smaps does not exist on kernels < 2.6.14 or if
            # CONFIG_MMU kernel configuration option is not enabled.

            # Note: using 3 regexes is faster than reading the file
            # line by line.
            # XXX: on Python 3 the 2 regexes are 30% slower than on
            # Python 2 though. Figure out why.
            #
            # You might be tempted to calculate USS by subtracting
            # the "shared" value from the "resident" value in
            # /proc/<pid>/statm. But at least on Linux, statm's "shared"
            # value actually counts pages backed by files, which has
            # little to do with whether the pages are actually shared.
            # /proc/self/smaps on the other hand appears to give us the
            # correct information.
            smaps_data = self._read_smaps_file()
            # Note: smaps file can be empty for certain processes.
            # The code below will not crash though and will result to 0.
            uss = sum(map(int, _private_re.findall(smaps_data))) * 1024
            pss = sum(map(int, _pss_re.findall(smaps_data))) * 1024
            swap = sum(map(int, _swap_re.findall(smaps_data))) * 1024
            return (uss, pss, swap)

        @wrap_exceptions
        def memory_full_info(self):
            if HAS_PROC_SMAPS_ROLLUP:  # faster
                try:
                    uss, pss, swap = self._parse_smaps_rollup()
                except (ProcessLookupError, FileNotFoundError):
                    uss, pss, swap = self._parse_smaps()
            else:
                uss, pss, swap = self._parse_smaps()
            basic_mem = self.memory_info()
            return pfullmem(*basic_mem + (uss, pss, swap))

    else:
        memory_full_info = memory_info

    if HAS_PROC_SMAPS:

        @wrap_exceptions
        def memory_maps(self):
            """Return process's mapped memory regions as a list of named
            tuples. Fields are explained in 'man proc'; here is an updated
            (Apr 2012) version: http://goo.gl/fmebo.

            /proc/{PID}/smaps does not exist on kernels < 2.6.14 or if
            CONFIG_MMU kernel configuration option is not enabled.
            """

            def get_blocks(lines, current_block):
                data = {}
                for line in lines:
                    fields = line.split(None, 5)
                    if not fields[0].endswith(b':'):
                        # new block section
                        yield (current_block.pop(), data)
                        current_block.append(line)
                    else:
                        try:
                            data[fields[0]] = int(fields[1]) * 1024
                        except ValueError:
                            if fields[0].startswith(b'VmFlags:'):
                                # see issue #369
                                continue
                            else:
                                raise ValueError(
                                    "don't know how to interpret line %r"
                                    % line
                                )
                yield (current_block.pop(), data)

            data = self._read_smaps_file()
            # Note: smaps file can be empty for certain processes or for
            # zombies.
            if not data:
                self._raise_if_zombie()
                return []
            lines = data.split(b'\n')
            ls = []
            first_line = lines.pop(0)
            current_block = [first_line]
            for header, data in get_blocks(lines, current_block):
                hfields = header.split(None, 5)
                try:
                    addr, perms, offset, dev, inode, path = hfields
                except ValueError:
                    addr, perms, offset, dev, inode, path = hfields + ['']
                if not path:
                    path = '[anon]'
                else:
                    if PY3:
                        path = decode(path)
                    path = path.strip()
                    if path.endswith(' (deleted)') and not path_exists_strict(
                        path
                    ):
                        path = path[:-10]
                ls.append((
                    decode(addr),
                    decode(perms),
                    path,
                    data.get(b'Rss:', 0),
                    data.get(b'Size:', 0),
                    data.get(b'Pss:', 0),
                    data.get(b'Shared_Clean:', 0),
                    data.get(b'Shared_Dirty:', 0),
                    data.get(b'Private_Clean:', 0),
                    data.get(b'Private_Dirty:', 0),
                    data.get(b'Referenced:', 0),
                    data.get(b'Anonymous:', 0),
                    data.get(b'Swap:', 0),
                ))
            return ls

    @wrap_exceptions
    def cwd(self):
        return readlink("%s/%s/cwd" % (self._procfs_path, self.pid))

    @wrap_exceptions
    def num_ctx_switches(
        self, _ctxsw_re=re.compile(br'ctxt_switches:\t(\d+)')
    ):
        data = self._read_status_file()
        ctxsw = _ctxsw_re.findall(data)
        if not ctxsw:
            raise NotImplementedError(
                "'voluntary_ctxt_switches' and 'nonvoluntary_ctxt_switches'"
                "lines were not found in %s/%s/status; the kernel is "
                "probably older than 2.6.23" % (self._procfs_path, self.pid)
            )
        else:
            return _common.pctxsw(int(ctxsw[0]), int(ctxsw[1]))

    @wrap_exceptions
    def num_threads(self, _num_threads_re=re.compile(br'Threads:\t(\d+)')):
        # Note: on Python 3 using a re is faster than iterating over file
        # line by line. On Python 2 is the exact opposite, and iterating
        # over a file on Python 3 is slower than on Python 2.
        data = self._read_status_file()
        return int(_num_threads_re.findall(data)[0])

    @wrap_exceptions
    def threads(self):
        thread_ids = os.listdir("%s/%s/task" % (self._procfs_path, self.pid))
        thread_ids.sort()
        retlist = []
        hit_enoent = False
        for thread_id in thread_ids:
            fname = "%s/%s/task/%s/stat" % (
                self._procfs_path,
                self.pid,
                thread_id,
            )
            try:
                with open_binary(fname) as f:
                    st = f.read().strip()
            except (FileNotFoundError, ProcessLookupError):
                # no such file or directory or no such process;
                # it means thread disappeared on us
                hit_enoent = True
                continue
            # ignore the first two values ("pid (exe)")
            st = st[st.find(b')') + 2 :]
            values = st.split(b' ')
            utime = float(values[11]) / CLOCK_TICKS
            stime = float(values[12]) / CLOCK_TICKS
            ntuple = _common.pthread(int(thread_id), utime, stime)
            retlist.append(ntuple)
        if hit_enoent:
            self._raise_if_not_alive()
        return retlist

    @wrap_exceptions
    def nice_get(self):
        # with open_text('%s/%s/stat' % (self._procfs_path, self.pid)) as f:
        #   data = f.read()
        #   return int(data.split()[18])

        # Use C implementation
        return cext_posix.getpriority(self.pid)

    @wrap_exceptions
    def nice_set(self, value):
        return cext_posix.setpriority(self.pid, value)

    # starting from CentOS 6.
    if HAS_CPU_AFFINITY:

        @wrap_exceptions
        def cpu_affinity_get(self):
            return cext.proc_cpu_affinity_get(self.pid)

        def _get_eligible_cpus(
            self, _re=re.compile(br"Cpus_allowed_list:\t(\d+)-(\d+)")
        ):
            # See: https://github.com/giampaolo/psutil/issues/956
            data = self._read_status_file()
            match = _re.findall(data)
            if match:
                return list(range(int(match[0][0]), int(match[0][1]) + 1))
            else:
                return list(range(len(per_cpu_times())))

        @wrap_exceptions
        def cpu_affinity_set(self, cpus):
            try:
                cext.proc_cpu_affinity_set(self.pid, cpus)
            except (OSError, ValueError) as err:
                if isinstance(err, ValueError) or err.errno == errno.EINVAL:
                    eligible_cpus = self._get_eligible_cpus()
                    all_cpus = tuple(range(len(per_cpu_times())))
                    for cpu in cpus:
                        if cpu not in all_cpus:
                            raise ValueError(
                                "invalid CPU number %r; choose between %s"
                                % (cpu, eligible_cpus)
                            )
                        if cpu not in eligible_cpus:
                            raise ValueError(
                                "CPU number %r is not eligible; choose "
                                "between %s" % (cpu, eligible_cpus)
                            )
                raise

    # only starting from kernel 2.6.13
    if HAS_PROC_IO_PRIORITY:

        @wrap_exceptions
        def ionice_get(self):
            ioclass, value = cext.proc_ioprio_get(self.pid)
            if enum is not None:
                ioclass = IOPriority(ioclass)
            return _common.pionice(ioclass, value)

        @wrap_exceptions
        def ionice_set(self, ioclass, value):
            if value is None:
                value = 0
            if value and ioclass in (IOPRIO_CLASS_IDLE, IOPRIO_CLASS_NONE):
                raise ValueError("%r ioclass accepts no value" % ioclass)
            if value < 0 or value > 7:
                msg = "value not in 0-7 range"
                raise ValueError(msg)
            return cext.proc_ioprio_set(self.pid, ioclass, value)

    if prlimit is not None:

        @wrap_exceptions
        def rlimit(self, resource_, limits=None):
            # If pid is 0 prlimit() applies to the calling process and
            # we don't want that. We should never get here though as
            # PID 0 is not supported on Linux.
            if self.pid == 0:
                msg = "can't use prlimit() against PID 0 process"
                raise ValueError(msg)
            try:
                if limits is None:
                    # get
                    return prlimit(self.pid, resource_)
                else:
                    # set
                    if len(limits) != 2:
                        msg = (
                            "second argument must be a (soft, hard) "
                            + "tuple, got %s" % repr(limits)
                        )
                        raise ValueError(msg)
                    prlimit(self.pid, resource_, limits)
            except OSError as err:
                if err.errno == errno.ENOSYS:
                    # I saw this happening on Travis:
                    # https://travis-ci.org/giampaolo/psutil/jobs/51368273
                    self._raise_if_zombie()
                raise

    @wrap_exceptions
    def status(self):
        letter = self._parse_stat_file()['status']
        if PY3:
            letter = letter.decode()
        # XXX is '?' legit? (we're not supposed to return it anyway)
        return PROC_STATUSES.get(letter, '?')

    @wrap_exceptions
    def open_files(self):
        retlist = []
        files = os.listdir("%s/%s/fd" % (self._procfs_path, self.pid))
        hit_enoent = False
        for fd in files:
            file = "%s/%s/fd/%s" % (self._procfs_path, self.pid, fd)
            try:
                path = readlink(file)
            except (FileNotFoundError, ProcessLookupError):
                # ENOENT == file which is gone in the meantime
                hit_enoent = True
                continue
            except OSError as err:
                if err.errno == errno.EINVAL:
                    # not a link
                    continue
                if err.errno == errno.ENAMETOOLONG:
                    # file name too long
                    debug(err)
                    continue
                raise
            else:
                # If path is not an absolute there's no way to tell
                # whether it's a regular file or not, so we skip it.
                # A regular file is always supposed to be have an
                # absolute path though.
                if path.startswith('/') and isfile_strict(path):
                    # Get file position and flags.
                    file = "%s/%s/fdinfo/%s" % (
                        self._procfs_path,
                        self.pid,
                        fd,
                    )
                    try:
                        with open_binary(file) as f:
                            pos = int(f.readline().split()[1])
                            flags = int(f.readline().split()[1], 8)
                    except (FileNotFoundError, ProcessLookupError):
                        # fd gone in the meantime; process may
                        # still be alive
                        hit_enoent = True
                    else:
                        mode = file_flags_to_mode(flags)
                        ntuple = popenfile(
                            path, int(fd), int(pos), mode, flags
                        )
                        retlist.append(ntuple)
        if hit_enoent:
            self._raise_if_not_alive()
        return retlist

    @wrap_exceptions
    def connections(self, kind='inet'):
        ret = _connections.retrieve(kind, self.pid)
        self._raise_if_not_alive()
        return ret

    @wrap_exceptions
    def num_fds(self):
        return len(os.listdir("%s/%s/fd" % (self._procfs_path, self.pid)))

    @wrap_exceptions
    def ppid(self):
        return int(self._parse_stat_file()['ppid'])

    @wrap_exceptions
    def uids(self, _uids_re=re.compile(br'Uid:\t(\d+)\t(\d+)\t(\d+)')):
        data = self._read_status_file()
        real, effective, saved = _uids_re.findall(data)[0]
        return _common.puids(int(real), int(effective), int(saved))

    @wrap_exceptions
    def gids(self, _gids_re=re.compile(br'Gid:\t(\d+)\t(\d+)\t(\d+)')):
        data = self._read_status_file()
        real, effective, saved = _gids_re.findall(data)[0]
        return _common.pgids(int(real), int(effective), int(saved))

# === NexusCore/openenv\Lib\site-packages\openai\resources\chat\completions\completions.py ===
# File generated from our OpenAPI spec by Stainless. See CONTRIBUTING.md for details.

from __future__ import annotations

import inspect
from typing import Dict, List, Union, Iterable, Optional
from typing_extensions import Literal, overload

import httpx
import pydantic

from .... import _legacy_response
from .messages import (
    Messages,
    AsyncMessages,
    MessagesWithRawResponse,
    AsyncMessagesWithRawResponse,
    MessagesWithStreamingResponse,
    AsyncMessagesWithStreamingResponse,
)
from ...._types import NOT_GIVEN, Body, Query, Headers, NotGiven
from ...._utils import required_args, maybe_transform, async_maybe_transform
from ...._compat import cached_property
from ...._resource import SyncAPIResource, AsyncAPIResource
from ...._response import to_streamed_response_wrapper, async_to_streamed_response_wrapper
from ...._streaming import Stream, AsyncStream
from ....pagination import SyncCursorPage, AsyncCursorPage
from ....types.chat import (
    ChatCompletionAudioParam,
    completion_list_params,
    completion_create_params,
    completion_update_params,
)
from ...._base_client import AsyncPaginator, make_request_options
from ....types.shared.chat_model import ChatModel
from ....types.chat.chat_completion import ChatCompletion
from ....types.shared_params.metadata import Metadata
from ....types.shared.reasoning_effort import ReasoningEffort
from ....types.chat.chat_completion_chunk import ChatCompletionChunk
from ....types.chat.chat_completion_deleted import ChatCompletionDeleted
from ....types.chat.chat_completion_tool_param import ChatCompletionToolParam
from ....types.chat.chat_completion_audio_param import ChatCompletionAudioParam
from ....types.chat.chat_completion_message_param import ChatCompletionMessageParam
from ....types.chat.chat_completion_stream_options_param import ChatCompletionStreamOptionsParam
from ....types.chat.chat_completion_prediction_content_param import ChatCompletionPredictionContentParam
from ....types.chat.chat_completion_tool_choice_option_param import ChatCompletionToolChoiceOptionParam

__all__ = ["Completions", "AsyncCompletions"]


class Completions(SyncAPIResource):
    @cached_property
    def messages(self) -> Messages:
        return Messages(self._client)

    @cached_property
    def with_raw_response(self) -> CompletionsWithRawResponse:
        """
        This property can be used as a prefix for any HTTP method call to return
        the raw response object instead of the parsed content.

        For more information, see https://www.github.com/openai/openai-python#accessing-raw-response-data-eg-headers
        """
        return CompletionsWithRawResponse(self)

    @cached_property
    def with_streaming_response(self) -> CompletionsWithStreamingResponse:
        """
        An alternative to `.with_raw_response` that doesn't eagerly read the response body.

        For more information, see https://www.github.com/openai/openai-python#with_streaming_response
        """
        return CompletionsWithStreamingResponse(self)

    @overload
    def create(
        self,
        *,
        messages: Iterable[ChatCompletionMessageParam],
        model: Union[str, ChatModel],
        audio: Optional[ChatCompletionAudioParam] | NotGiven = NOT_GIVEN,
        frequency_penalty: Optional[float] | NotGiven = NOT_GIVEN,
        function_call: completion_create_params.FunctionCall | NotGiven = NOT_GIVEN,
        functions: Iterable[completion_create_params.Function] | NotGiven = NOT_GIVEN,
        logit_bias: Optional[Dict[str, int]] | NotGiven = NOT_GIVEN,
        logprobs: Optional[bool] | NotGiven = NOT_GIVEN,
        max_completion_tokens: Optional[int] | NotGiven = NOT_GIVEN,
        max_tokens: Optional[int] | NotGiven = NOT_GIVEN,
        metadata: Optional[Metadata] | NotGiven = NOT_GIVEN,
        modalities: Optional[List[Literal["text", "audio"]]] | NotGiven = NOT_GIVEN,
        n: Optional[int] | NotGiven = NOT_GIVEN,
        parallel_tool_calls: bool | NotGiven = NOT_GIVEN,
        prediction: Optional[ChatCompletionPredictionContentParam] | NotGiven = NOT_GIVEN,
        presence_penalty: Optional[float] | NotGiven = NOT_GIVEN,
        reasoning_effort: Optional[ReasoningEffort] | NotGiven = NOT_GIVEN,
        response_format: completion_create_params.ResponseFormat | NotGiven = NOT_GIVEN,
        seed: Optional[int] | NotGiven = NOT_GIVEN,
        service_tier: Optional[Literal["auto", "default", "flex", "scale"]] | NotGiven = NOT_GIVEN,
        stop: Union[Optional[str], List[str], None] | NotGiven = NOT_GIVEN,
        store: Optional[bool] | NotGiven = NOT_GIVEN,
        stream: Optional[Literal[False]] | NotGiven = NOT_GIVEN,
        stream_options: Optional[ChatCompletionStreamOptionsParam] | NotGiven = NOT_GIVEN,
        temperature: Optional[float] | NotGiven = NOT_GIVEN,
        tool_choice: ChatCompletionToolChoiceOptionParam | NotGiven = NOT_GIVEN,
        tools: Iterable[ChatCompletionToolParam] | NotGiven = NOT_GIVEN,
        top_logprobs: Optional[int] | NotGiven = NOT_GIVEN,
        top_p: Optional[float] | NotGiven = NOT_GIVEN,
        user: str | NotGiven = NOT_GIVEN,
        web_search_options: completion_create_params.WebSearchOptions | NotGiven = NOT_GIVEN,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> ChatCompletion:
        """
        **Starting a new project?** We recommend trying
        [Responses](https://platform.openai.com/docs/api-reference/responses) to take
        advantage of the latest OpenAI platform features. Compare
        [Chat Completions with Responses](https://platform.openai.com/docs/guides/responses-vs-chat-completions?api-mode=responses).

        ---

        Creates a model response for the given chat conversation. Learn more in the
        [text generation](https://platform.openai.com/docs/guides/text-generation),
        [vision](https://platform.openai.com/docs/guides/vision), and
        [audio](https://platform.openai.com/docs/guides/audio) guides.

        Parameter support can differ depending on the model used to generate the
        response, particularly for newer reasoning models. Parameters that are only
        supported for reasoning models are noted below. For the current state of
        unsupported parameters in reasoning models,
        [refer to the reasoning guide](https://platform.openai.com/docs/guides/reasoning).

        Args:
          messages: A list of messages comprising the conversation so far. Depending on the
              [model](https://platform.openai.com/docs/models) you use, different message
              types (modalities) are supported, like
              [text](https://platform.openai.com/docs/guides/text-generation),
              [images](https://platform.openai.com/docs/guides/vision), and
              [audio](https://platform.openai.com/docs/guides/audio).

          model: Model ID used to generate the response, like `gpt-4o` or `o3`. OpenAI offers a
              wide range of models with different capabilities, performance characteristics,
              and price points. Refer to the
              [model guide](https://platform.openai.com/docs/models) to browse and compare
              available models.

          audio: Parameters for audio output. Required when audio output is requested with
              `modalities: ["audio"]`.
              [Learn more](https://platform.openai.com/docs/guides/audio).

          frequency_penalty: Number between -2.0 and 2.0. Positive values penalize new tokens based on their
              existing frequency in the text so far, decreasing the model's likelihood to
              repeat the same line verbatim.

          function_call: Deprecated in favor of `tool_choice`.

              Controls which (if any) function is called by the model.

              `none` means the model will not call a function and instead generates a message.

              `auto` means the model can pick between generating a message or calling a
              function.

              Specifying a particular function via `{"name": "my_function"}` forces the model
              to call that function.

              `none` is the default when no functions are present. `auto` is the default if
              functions are present.

          functions: Deprecated in favor of `tools`.

              A list of functions the model may generate JSON inputs for.

          logit_bias: Modify the likelihood of specified tokens appearing in the completion.

              Accepts a JSON object that maps tokens (specified by their token ID in the
              tokenizer) to an associated bias value from -100 to 100. Mathematically, the
              bias is added to the logits generated by the model prior to sampling. The exact
              effect will vary per model, but values between -1 and 1 should decrease or
              increase likelihood of selection; values like -100 or 100 should result in a ban
              or exclusive selection of the relevant token.

          logprobs: Whether to return log probabilities of the output tokens or not. If true,
              returns the log probabilities of each output token returned in the `content` of
              `message`.

          max_completion_tokens: An upper bound for the number of tokens that can be generated for a completion,
              including visible output tokens and
              [reasoning tokens](https://platform.openai.com/docs/guides/reasoning).

          max_tokens: The maximum number of [tokens](/tokenizer) that can be generated in the chat
              completion. This value can be used to control
              [costs](https://openai.com/api/pricing/) for text generated via API.

              This value is now deprecated in favor of `max_completion_tokens`, and is not
              compatible with
              [o-series models](https://platform.openai.com/docs/guides/reasoning).

          metadata: Set of 16 key-value pairs that can be attached to an object. This can be useful
              for storing additional information about the object in a structured format, and
              querying for objects via API or the dashboard.

              Keys are strings with a maximum length of 64 characters. Values are strings with
              a maximum length of 512 characters.

          modalities: Output types that you would like the model to generate. Most models are capable
              of generating text, which is the default:

              `["text"]`

              The `gpt-4o-audio-preview` model can also be used to
              [generate audio](https://platform.openai.com/docs/guides/audio). To request that
              this model generate both text and audio responses, you can use:

              `["text", "audio"]`

          n: How many chat completion choices to generate for each input message. Note that
              you will be charged based on the number of generated tokens across all of the
              choices. Keep `n` as `1` to minimize costs.

          parallel_tool_calls: Whether to enable
              [parallel function calling](https://platform.openai.com/docs/guides/function-calling#configuring-parallel-function-calling)
              during tool use.

          prediction: Static predicted output content, such as the content of a text file that is
              being regenerated.

          presence_penalty: Number between -2.0 and 2.0. Positive values penalize new tokens based on
              whether they appear in the text so far, increasing the model's likelihood to
              talk about new topics.

          reasoning_effort: **o-series models only**

              Constrains effort on reasoning for
              [reasoning models](https://platform.openai.com/docs/guides/reasoning). Currently
              supported values are `low`, `medium`, and `high`. Reducing reasoning effort can
              result in faster responses and fewer tokens used on reasoning in a response.

          response_format: An object specifying the format that the model must output.

              Setting to `{ "type": "json_schema", "json_schema": {...} }` enables Structured
              Outputs which ensures the model will match your supplied JSON schema. Learn more
              in the
              [Structured Outputs guide](https://platform.openai.com/docs/guides/structured-outputs).

              Setting to `{ "type": "json_object" }` enables the older JSON mode, which
              ensures the message the model generates is valid JSON. Using `json_schema` is
              preferred for models that support it.

          seed: This feature is in Beta. If specified, our system will make a best effort to
              sample deterministically, such that repeated requests with the same `seed` and
              parameters should return the same result. Determinism is not guaranteed, and you
              should refer to the `system_fingerprint` response parameter to monitor changes
              in the backend.

          service_tier: Specifies the latency tier to use for processing the request. This parameter is
              relevant for customers subscribed to the scale tier service:

              - If set to 'auto', and the Project is Scale tier enabled, the system will
                utilize scale tier credits until they are exhausted.
              - If set to 'auto', and the Project is not Scale tier enabled, the request will
                be processed using the default service tier with a lower uptime SLA and no
                latency guarantee.
              - If set to 'default', the request will be processed using the default service
                tier with a lower uptime SLA and no latency guarantee.
              - If set to 'flex', the request will be processed with the Flex Processing
                service tier.
                [Learn more](https://platform.openai.com/docs/guides/flex-processing).
              - When not set, the default behavior is 'auto'.

              When this parameter is set, the response body will include the `service_tier`
              utilized.

          stop: Not supported with latest reasoning models `o3` and `o4-mini`.

              Up to 4 sequences where the API will stop generating further tokens. The
              returned text will not contain the stop sequence.

          store: Whether or not to store the output of this chat completion request for use in
              our [model distillation](https://platform.openai.com/docs/guides/distillation)
              or [evals](https://platform.openai.com/docs/guides/evals) products.

          stream: If set to true, the model response data will be streamed to the client as it is
              generated using
              [server-sent events](https://developer.mozilla.org/en-US/docs/Web/API/Server-sent_events/Using_server-sent_events#Event_stream_format).
              See the
              [Streaming section below](https://platform.openai.com/docs/api-reference/chat/streaming)
              for more information, along with the
              [streaming responses](https://platform.openai.com/docs/guides/streaming-responses)
              guide for more information on how to handle the streaming events.

          stream_options: Options for streaming response. Only set this when you set `stream: true`.

          temperature: What sampling temperature to use, between 0 and 2. Higher values like 0.8 will
              make the output more random, while lower values like 0.2 will make it more
              focused and deterministic. We generally recommend altering this or `top_p` but
              not both.

          tool_choice: Controls which (if any) tool is called by the model. `none` means the model will
              not call any tool and instead generates a message. `auto` means the model can
              pick between generating a message or calling one or more tools. `required` means
              the model must call one or more tools. Specifying a particular tool via
              `{"type": "function", "function": {"name": "my_function"}}` forces the model to
              call that tool.

              `none` is the default when no tools are present. `auto` is the default if tools
              are present.

          tools: A list of tools the model may call. Currently, only functions are supported as a
              tool. Use this to provide a list of functions the model may generate JSON inputs
              for. A max of 128 functions are supported.

          top_logprobs: An integer between 0 and 20 specifying the number of most likely tokens to
              return at each token position, each with an associated log probability.
              `logprobs` must be set to `true` if this parameter is used.

          top_p: An alternative to sampling with temperature, called nucleus sampling, where the
              model considers the results of the tokens with top_p probability mass. So 0.1
              means only the tokens comprising the top 10% probability mass are considered.

              We generally recommend altering this or `temperature` but not both.

          user: A stable identifier for your end-users. Used to boost cache hit rates by better
              bucketing similar requests and to help OpenAI detect and prevent abuse.
              [Learn more](https://platform.openai.com/docs/guides/safety-best-practices#end-user-ids).

          web_search_options: This tool searches the web for relevant results to use in a response. Learn more
              about the
              [web search tool](https://platform.openai.com/docs/guides/tools-web-search?api-mode=chat).

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
        messages: Iterable[ChatCompletionMessageParam],
        model: Union[str, ChatModel],
        stream: Literal[True],
        audio: Optional[ChatCompletionAudioParam] | NotGiven = NOT_GIVEN,
        frequency_penalty: Optional[float] | NotGiven = NOT_GIVEN,
        function_call: completion_create_params.FunctionCall | NotGiven = NOT_GIVEN,
        functions: Iterable[completion_create_params.Function] | NotGiven = NOT_GIVEN,
        logit_bias: Optional[Dict[str, int]] | NotGiven = NOT_GIVEN,
        logprobs: Optional[bool] | NotGiven = NOT_GIVEN,
        max_completion_tokens: Optional[int] | NotGiven = NOT_GIVEN,
        max_tokens: Optional[int] | NotGiven = NOT_GIVEN,
        metadata: Optional[Metadata] | NotGiven = NOT_GIVEN,
        modalities: Optional[List[Literal["text", "audio"]]] | NotGiven = NOT_GIVEN,
        n: Optional[int] | NotGiven = NOT_GIVEN,
        parallel_tool_calls: bool | NotGiven = NOT_GIVEN,
        prediction: Optional[ChatCompletionPredictionContentParam] | NotGiven = NOT_GIVEN,
        presence_penalty: Optional[float] | NotGiven = NOT_GIVEN,
        reasoning_effort: Optional[ReasoningEffort] | NotGiven = NOT_GIVEN,
        response_format: completion_create_params.ResponseFormat | NotGiven = NOT_GIVEN,
        seed: Optional[int] | NotGiven = NOT_GIVEN,
        service_tier: Optional[Literal["auto", "default", "flex", "scale"]] | NotGiven = NOT_GIVEN,
        stop: Union[Optional[str], List[str], None] | NotGiven = NOT_GIVEN,
        store: Optional[bool] | NotGiven = NOT_GIVEN,
        stream_options: Optional[ChatCompletionStreamOptionsParam] | NotGiven = NOT_GIVEN,
        temperature: Optional[float] | NotGiven = NOT_GIVEN,
        tool_choice: ChatCompletionToolChoiceOptionParam | NotGiven = NOT_GIVEN,
        tools: Iterable[ChatCompletionToolParam] | NotGiven = NOT_GIVEN,
        top_logprobs: Optional[int] | NotGiven = NOT_GIVEN,
        top_p: Optional[float] | NotGiven = NOT_GIVEN,
        user: str | NotGiven = NOT_GIVEN,
        web_search_options: completion_create_params.WebSearchOptions | NotGiven = NOT_GIVEN,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> Stream[ChatCompletionChunk]:
        """
        **Starting a new project?** We recommend trying
        [Responses](https://platform.openai.com/docs/api-reference/responses) to take
        advantage of the latest OpenAI platform features. Compare
        [Chat Completions with Responses](https://platform.openai.com/docs/guides/responses-vs-chat-completions?api-mode=responses).

        ---

        Creates a model response for the given chat conversation. Learn more in the
        [text generation](https://platform.openai.com/docs/guides/text-generation),
        [vision](https://platform.openai.com/docs/guides/vision), and
        [audio](https://platform.openai.com/docs/guides/audio) guides.

        Parameter support can differ depending on the model used to generate the
        response, particularly for newer reasoning models. Parameters that are only
        supported for reasoning models are noted below. For the current state of
        unsupported parameters in reasoning models,
        [refer to the reasoning guide](https://platform.openai.com/docs/guides/reasoning).

        Args:
          messages: A list of messages comprising the conversation so far. Depending on the
              [model](https://platform.openai.com/docs/models) you use, different message
              types (modalities) are supported, like
              [text](https://platform.openai.com/docs/guides/text-generation),
              [images](https://platform.openai.com/docs/guides/vision), and
              [audio](https://platform.openai.com/docs/guides/audio).

          model: Model ID used to generate the response, like `gpt-4o` or `o3`. OpenAI offers a
              wide range of models with different capabilities, performance characteristics,
              and price points. Refer to the
              [model guide](https://platform.openai.com/docs/models) to browse and compare
              available models.

          stream: If set to true, the model response data will be streamed to the client as it is
              generated using
              [server-sent events](https://developer.mozilla.org/en-US/docs/Web/API/Server-sent_events/Using_server-sent_events#Event_stream_format).
              See the
              [Streaming section below](https://platform.openai.com/docs/api-reference/chat/streaming)
              for more information, along with the
              [streaming responses](https://platform.openai.com/docs/guides/streaming-responses)
              guide for more information on how to handle the streaming events.

          audio: Parameters for audio output. Required when audio output is requested with
              `modalities: ["audio"]`.
              [Learn more](https://platform.openai.com/docs/guides/audio).

          frequency_penalty: Number between -2.0 and 2.0. Positive values penalize new tokens based on their
              existing frequency in the text so far, decreasing the model's likelihood to
              repeat the same line verbatim.

          function_call: Deprecated in favor of `tool_choice`.

              Controls which (if any) function is called by the model.

              `none` means the model will not call a function and instead generates a message.

              `auto` means the model can pick between generating a message or calling a
              function.

              Specifying a particular function via `{"name": "my_function"}` forces the model
              to call that function.

              `none` is the default when no functions are present. `auto` is the default if
              functions are present.

          functions: Deprecated in favor of `tools`.

              A list of functions the model may generate JSON inputs for.

          logit_bias: Modify the likelihood of specified tokens appearing in the completion.

              Accepts a JSON object that maps tokens (specified by their token ID in the
              tokenizer) to an associated bias value from -100 to 100. Mathematically, the
              bias is added to the logits generated by the model prior to sampling. The exact
              effect will vary per model, but values between -1 and 1 should decrease or
              increase likelihood of selection; values like -100 or 100 should result in a ban
              or exclusive selection of the relevant token.

          logprobs: Whether to return log probabilities of the output tokens or not. If true,
              returns the log probabilities of each output token returned in the `content` of
              `message`.

          max_completion_tokens: An upper bound for the number of tokens that can be generated for a completion,
              including visible output tokens and
              [reasoning tokens](https://platform.openai.com/docs/guides/reasoning).

          max_tokens: The maximum number of [tokens](/tokenizer) that can be generated in the chat
              completion. This value can be used to control
              [costs](https://openai.com/api/pricing/) for text generated via API.

              This value is now deprecated in favor of `max_completion_tokens`, and is not
              compatible with
              [o-series models](https://platform.openai.com/docs/guides/reasoning).

          metadata: Set of 16 key-value pairs that can be attached to an object. This can be useful
              for storing additional information about the object in a structured format, and
              querying for objects via API or the dashboard.

              Keys are strings with a maximum length of 64 characters. Values are strings with
              a maximum length of 512 characters.

          modalities: Output types that you would like the model to generate. Most models are capable
              of generating text, which is the default:

              `["text"]`

              The `gpt-4o-audio-preview` model can also be used to
              [generate audio](https://platform.openai.com/docs/guides/audio). To request that
              this model generate both text and audio responses, you can use:

              `["text", "audio"]`

          n: How many chat completion choices to generate for each input message. Note that
              you will be charged based on the number of generated tokens across all of the
              choices. Keep `n` as `1` to minimize costs.

          parallel_tool_calls: Whether to enable
              [parallel function calling](https://platform.openai.com/docs/guides/function-calling#configuring-parallel-function-calling)
              during tool use.

          prediction: Static predicted output content, such as the content of a text file that is
              being regenerated.

          presence_penalty: Number between -2.0 and 2.0. Positive values penalize new tokens based on
              whether they appear in the text so far, increasing the model's likelihood to
              talk about new topics.

          reasoning_effort: **o-series models only**

              Constrains effort on reasoning for
              [reasoning models](https://platform.openai.com/docs/guides/reasoning). Currently
              supported values are `low`, `medium`, and `high`. Reducing reasoning effort can
              result in faster responses and fewer tokens used on reasoning in a response.

          response_format: An object specifying the format that the model must output.

              Setting to `{ "type": "json_schema", "json_schema": {...} }` enables Structured
              Outputs which ensures the model will match your supplied JSON schema. Learn more
              in the
              [Structured Outputs guide](https://platform.openai.com/docs/guides/structured-outputs).

              Setting to `{ "type": "json_object" }` enables the older JSON mode, which
              ensures the message the model generates is valid JSON. Using `json_schema` is
              preferred for models that support it.

          seed: This feature is in Beta. If specified, our system will make a best effort to
              sample deterministically, such that repeated requests with the same `seed` and
              parameters should return the same result. Determinism is not guaranteed, and you
              should refer to the `system_fingerprint` response parameter to monitor changes
              in the backend.

          service_tier: Specifies the latency tier to use for processing the request. This parameter is
              relevant for customers subscribed to the scale tier service:

              - If set to 'auto', and the Project is Scale tier enabled, the system will
                utilize scale tier credits until they are exhausted.
              - If set to 'auto', and the Project is not Scale tier enabled, the request will
                be processed using the default service tier with a lower uptime SLA and no
                latency guarantee.
              - If set to 'default', the request will be processed using the default service
                tier with a lower uptime SLA and no latency guarantee.
              - If set to 'flex', the request will be processed with the Flex Processing
                service tier.
                [Learn more](https://platform.openai.com/docs/guides/flex-processing).
              - When not set, the default behavior is 'auto'.

              When this parameter is set, the response body will include the `service_tier`
              utilized.

          stop: Not supported with latest reasoning models `o3` and `o4-mini`.

              Up to 4 sequences where the API will stop generating further tokens. The
              returned text will not contain the stop sequence.

          store: Whether or not to store the output of this chat completion request for use in
              our [model distillation](https://platform.openai.com/docs/guides/distillation)
              or [evals](https://platform.openai.com/docs/guides/evals) products.

          stream_options: Options for streaming response. Only set this when you set `stream: true`.

          temperature: What sampling temperature to use, between 0 and 2. Higher values like 0.8 will
              make the output more random, while lower values like 0.2 will make it more
              focused and deterministic. We generally recommend altering this or `top_p` but
              not both.

          tool_choice: Controls which (if any) tool is called by the model. `none` means the model will
              not call any tool and instead generates a message. `auto` means the model can
              pick between generating a message or calling one or more tools. `required` means
              the model must call one or more tools. Specifying a particular tool via
              `{"type": "function", "function": {"name": "my_function"}}` forces the model to
              call that tool.

              `none` is the default when no tools are present. `auto` is the default if tools
              are present.

          tools: A list of tools the model may call. Currently, only functions are supported as a
              tool. Use this to provide a list of functions the model may generate JSON inputs
              for. A max of 128 functions are supported.

          top_logprobs: An integer between 0 and 20 specifying the number of most likely tokens to
              return at each token position, each with an associated log probability.
              `logprobs` must be set to `true` if this parameter is used.

          top_p: An alternative to sampling with temperature, called nucleus sampling, where the
              model considers the results of the tokens with top_p probability mass. So 0.1
              means only the tokens comprising the top 10% probability mass are considered.

              We generally recommend altering this or `temperature` but not both.

          user: A stable identifier for your end-users. Used to boost cache hit rates by better
              bucketing similar requests and to help OpenAI detect and prevent abuse.
              [Learn more](https://platform.openai.com/docs/guides/safety-best-practices#end-user-ids).

          web_search_options: This tool searches the web for relevant results to use in a response. Learn more
              about the
              [web search tool](https://platform.openai.com/docs/guides/tools-web-search?api-mode=chat).

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
        messages: Iterable[ChatCompletionMessageParam],
        model: Union[str, ChatModel],
        stream: bool,
        audio: Optional[ChatCompletionAudioParam] | NotGiven = NOT_GIVEN,
        frequency_penalty: Optional[float] | NotGiven = NOT_GIVEN,
        function_call: completion_create_params.FunctionCall | NotGiven = NOT_GIVEN,
        functions: Iterable[completion_create_params.Function] | NotGiven = NOT_GIVEN,
        logit_bias: Optional[Dict[str, int]] | NotGiven = NOT_GIVEN,
        logprobs: Optional[bool] | NotGiven = NOT_GIVEN,
        max_completion_tokens: Optional[int] | NotGiven = NOT_GIVEN,
        max_tokens: Optional[int] | NotGiven = NOT_GIVEN,
        metadata: Optional[Metadata] | NotGiven = NOT_GIVEN,
        modalities: Optional[List[Literal["text", "audio"]]] | NotGiven = NOT_GIVEN,
        n: Optional[int] | NotGiven = NOT_GIVEN,
        parallel_tool_calls: bool | NotGiven = NOT_GIVEN,
        prediction: Optional[ChatCompletionPredictionContentParam] | NotGiven = NOT_GIVEN,
        presence_penalty: Optional[float] | NotGiven = NOT_GIVEN,
        reasoning_effort: Optional[ReasoningEffort] | NotGiven = NOT_GIVEN,
        response_format: completion_create_params.ResponseFormat | NotGiven = NOT_GIVEN,
        seed: Optional[int] | NotGiven = NOT_GIVEN,
        service_tier: Optional[Literal["auto", "default", "flex", "scale"]] | NotGiven = NOT_GIVEN,
        stop: Union[Optional[str], List[str], None] | NotGiven = NOT_GIVEN,
        store: Optional[bool] | NotGiven = NOT_GIVEN,
        stream_options: Optional[ChatCompletionStreamOptionsParam] | NotGiven = NOT_GIVEN,
        temperature: Optional[float] | NotGiven = NOT_GIVEN,
        tool_choice: ChatCompletionToolChoiceOptionParam | NotGiven = NOT_GIVEN,
        tools: Iterable[ChatCompletionToolParam] | NotGiven = NOT_GIVEN,
        top_logprobs: Optional[int] | NotGiven = NOT_GIVEN,
        top_p: Optional[float] | NotGiven = NOT_GIVEN,
        user: str | NotGiven = NOT_GIVEN,
        web_search_options: completion_create_params.WebSearchOptions | NotGiven = NOT_GIVEN,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> ChatCompletion | Stream[ChatCompletionChunk]:
        """
        **Starting a new project?** We recommend trying
        [Responses](https://platform.openai.com/docs/api-reference/responses) to take
        advantage of the latest OpenAI platform features. Compare
        [Chat Completions with Responses](https://platform.openai.com/docs/guides/responses-vs-chat-completions?api-mode=responses).

        ---

        Creates a model response for the given chat conversation. Learn more in the
        [text generation](https://platform.openai.com/docs/guides/text-generation),
        [vision](https://platform.openai.com/docs/guides/vision), and
        [audio](https://platform.openai.com/docs/guides/audio) guides.

        Parameter support can differ depending on the model used to generate the
        response, particularly for newer reasoning models. Parameters that are only
        supported for reasoning models are noted below. For the current state of
        unsupported parameters in reasoning models,
        [refer to the reasoning guide](https://platform.openai.com/docs/guides/reasoning).

        Args:
          messages: A list of messages comprising the conversation so far. Depending on the
              [model](https://platform.openai.com/docs/models) you use, different message
              types (modalities) are supported, like
              [text](https://platform.openai.com/docs/guides/text-generation),
              [images](https://platform.openai.com/docs/guides/vision), and
              [audio](https://platform.openai.com/docs/guides/audio).

          model: Model ID used to generate the response, like `gpt-4o` or `o3`. OpenAI offers a
              wide range of models with different capabilities, performance characteristics,
              and price points. Refer to the
              [model guide](https://platform.openai.com/docs/models) to browse and compare
              available models.

          stream: If set to true, the model response data will be streamed to the client as it is
              generated using
              [server-sent events](https://developer.mozilla.org/en-US/docs/Web/API/Server-sent_events/Using_server-sent_events#Event_stream_format).
              See the
              [Streaming section below](https://platform.openai.com/docs/api-reference/chat/streaming)
              for more information, along with the
              [streaming responses](https://platform.openai.com/docs/guides/streaming-responses)
              guide for more information on how to handle the streaming events.

          audio: Parameters for audio output. Required when audio output is requested with
              `modalities: ["audio"]`.
              [Learn more](https://platform.openai.com/docs/guides/audio).

          frequency_penalty: Number between -2.0 and 2.0. Positive values penalize new tokens based on their
              existing frequency in the text so far, decreasing the model's likelihood to
              repeat the same line verbatim.

          function_call: Deprecated in favor of `tool_choice`.

              Controls which (if any) function is called by the model.

              `none` means the model will not call a function and instead generates a message.

              `auto` means the model can pick between generating a message or calling a
              function.

              Specifying a particular function via `{"name": "my_function"}` forces the model
              to call that function.

              `none` is the default when no functions are present. `auto` is the default if
              functions are present.

          functions: Deprecated in favor of `tools`.

              A list of functions the model may generate JSON inputs for.

          logit_bias: Modify the likelihood of specified tokens appearing in the completion.

              Accepts a JSON object that maps tokens (specified by their token ID in the
              tokenizer) to an associated bias value from -100 to 100. Mathematically, the
              bias is added to the logits generated by the model prior to sampling. The exact
              effect will vary per model, but values between -1 and 1 should decrease or
              increase likelihood of selection; values like -100 or 100 should result in a ban
              or exclusive selection of the relevant token.

          logprobs: Whether to return log probabilities of the output tokens or not. If true,
              returns the log probabilities of each output token returned in the `content` of
              `message`.

          max_completion_tokens: An upper bound for the number of tokens that can be generated for a completion,
              including visible output tokens and
              [reasoning tokens](https://platform.openai.com/docs/guides/reasoning).

          max_tokens: The maximum number of [tokens](/tokenizer) that can be generated in the chat
              completion. This value can be used to control
              [costs](https://openai.com/api/pricing/) for text generated via API.

              This value is now deprecated in favor of `max_completion_tokens`, and is not
              compatible with
              [o-series models](https://platform.openai.com/docs/guides/reasoning).

          metadata: Set of 16 key-value pairs that can be attached to an object. This can be useful
              for storing additional information about the object in a structured format, and
              querying for objects via API or the dashboard.

              Keys are strings with a maximum length of 64 characters. Values are strings with
              a maximum length of 512 characters.

          modalities: Output types that you would like the model to generate. Most models are capable
              of generating text, which is the default:

              `["text"]`

              The `gpt-4o-audio-preview` model can also be used to
              [generate audio](https://platform.openai.com/docs/guides/audio). To request that
              this model generate both text and audio responses, you can use:

              `["text", "audio"]`

          n: How many chat completion choices to generate for each input message. Note that
              you will be charged based on the number of generated tokens across all of the
              choices. Keep `n` as `1` to minimize costs.

          parallel_tool_calls: Whether to enable
              [parallel function calling](https://platform.openai.com/docs/guides/function-calling#configuring-parallel-function-calling)
              during tool use.

          prediction: Static predicted output content, such as the content of a text file that is
              being regenerated.

          presence_penalty: Number between -2.0 and 2.0. Positive values penalize new tokens based on
              whether they appear in the text so far, increasing the model's likelihood to
              talk about new topics.

          reasoning_effort: **o-series models only**

              Constrains effort on reasoning for
              [reasoning models](https://platform.openai.com/docs/guides/reasoning). Currently
              supported values are `low`, `medium`, and `high`. Reducing reasoning effort can
              result in faster responses and fewer tokens used on reasoning in a response.

          response_format: An object specifying the format that the model must output.

              Setting to `{ "type": "json_schema", "json_schema": {...} }` enables Structured
              Outputs which ensures the model will match your supplied JSON schema. Learn more
              in the
              [Structured Outputs guide](https://platform.openai.com/docs/guides/structured-outputs).

              Setting to `{ "type": "json_object" }` enables the older JSON mode, which
              ensures the message the model generates is valid JSON. Using `json_schema` is
              preferred for models that support it.

          seed: This feature is in Beta. If specified, our system will make a best effort to
              sample deterministically, such that repeated requests with the same `seed` and
              parameters should return the same result. Determinism is not guaranteed, and you
              should refer to the `system_fingerprint` response parameter to monitor changes
              in the backend.

          service_tier: Specifies the latency tier to use for processing the request. This parameter is
              relevant for customers subscribed to the scale tier service:

              - If set to 'auto', and the Project is Scale tier enabled, the system will
                utilize scale tier credits until they are exhausted.
              - If set to 'auto', and the Project is not Scale tier enabled, the request will
                be processed using the default service tier with a lower uptime SLA and no
                latency guarantee.
              - If set to 'default', the request will be processed using the default service
                tier with a lower uptime SLA and no latency guarantee.
              - If set to 'flex', the request will be processed with the Flex Processing
                service tier.
                [Learn more](https://platform.openai.com/docs/guides/flex-processing).
              - When not set, the default behavior is 'auto'.

              When this parameter is set, the response body will include the `service_tier`
              utilized.

          stop: Not supported with latest reasoning models `o3` and `o4-mini`.

              Up to 4 sequences where the API will stop generating further tokens. The
              returned text will not contain the stop sequence.

          store: Whether or not to store the output of this chat completion request for use in
              our [model distillation](https://platform.openai.com/docs/guides/distillation)
              or [evals](https://platform.openai.com/docs/guides/evals) products.

          stream_options: Options for streaming response. Only set this when you set `stream: true`.

          temperature: What sampling temperature to use, between 0 and 2. Higher values like 0.8 will
              make the output more random, while lower values like 0.2 will make it more
              focused and deterministic. We generally recommend altering this or `top_p` but
              not both.

          tool_choice: Controls which (if any) tool is called by the model. `none` means the model will
              not call any tool and instead generates a message. `auto` means the model can
              pick between generating a message or calling one or more tools. `required` means
              the model must call one or more tools. Specifying a particular tool via
              `{"type": "function", "function": {"name": "my_function"}}` forces the model to
              call that tool.

              `none` is the default when no tools are present. `auto` is the default if tools
              are present.

          tools: A list of tools the model may call. Currently, only functions are supported as a
              tool. Use this to provide a list of functions the model may generate JSON inputs
              for. A max of 128 functions are supported.

          top_logprobs: An integer between 0 and 20 specifying the number of most likely tokens to
              return at each token position, each with an associated log probability.
              `logprobs` must be set to `true` if this parameter is used.

          top_p: An alternative to sampling with temperature, called nucleus sampling, where the
              model considers the results of the tokens with top_p probability mass. So 0.1
              means only the tokens comprising the top 10% probability mass are considered.

              We generally recommend altering this or `temperature` but not both.

          user: A stable identifier for your end-users. Used to boost cache hit rates by better
              bucketing similar requests and to help OpenAI detect and prevent abuse.
              [Learn more](https://platform.openai.com/docs/guides/safety-best-practices#end-user-ids).

          web_search_options: This tool searches the web for relevant results to use in a response. Learn more
              about the
              [web search tool](https://platform.openai.com/docs/guides/tools-web-search?api-mode=chat).

          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request, in seconds
        """
        ...

    @required_args(["messages", "model"], ["messages", "model", "stream"])
    def create(
        self,
        *,
        messages: Iterable[ChatCompletionMessageParam],
        model: Union[str, ChatModel],
        audio: Optional[ChatCompletionAudioParam] | NotGiven = NOT_GIVEN,
        frequency_penalty: Optional[float] | NotGiven = NOT_GIVEN,
        function_call: completion_create_params.FunctionCall | NotGiven = NOT_GIVEN,
        functions: Iterable[completion_create_params.Function] | NotGiven = NOT_GIVEN,
        logit_bias: Optional[Dict[str, int]] | NotGiven = NOT_GIVEN,
        logprobs: Optional[bool] | NotGiven = NOT_GIVEN,
        max_completion_tokens: Optional[int] | NotGiven = NOT_GIVEN,
        max_tokens: Optional[int] | NotGiven = NOT_GIVEN,
        metadata: Optional[Metadata] | NotGiven = NOT_GIVEN,
        modalities: Optional[List[Literal["text", "audio"]]] | NotGiven = NOT_GIVEN,
        n: Optional[int] | NotGiven = NOT_GIVEN,
        parallel_tool_calls: bool | NotGiven = NOT_GIVEN,
        prediction: Optional[ChatCompletionPredictionContentParam] | NotGiven = NOT_GIVEN,
        presence_penalty: Optional[float] | NotGiven = NOT_GIVEN,
        reasoning_effort: Optional[ReasoningEffort] | NotGiven = NOT_GIVEN,
        response_format: completion_create_params.ResponseFormat | NotGiven = NOT_GIVEN,
        seed: Optional[int] | NotGiven = NOT_GIVEN,
        service_tier: Optional[Literal["auto", "default", "flex", "scale"]] | NotGiven = NOT_GIVEN,
        stop: Union[Optional[str], List[str], None] | NotGiven = NOT_GIVEN,
        store: Optional[bool] | NotGiven = NOT_GIVEN,
        stream: Optional[Literal[False]] | Literal[True] | NotGiven = NOT_GIVEN,
        stream_options: Optional[ChatCompletionStreamOptionsParam] | NotGiven = NOT_GIVEN,
        temperature: Optional[float] | NotGiven = NOT_GIVEN,
        tool_choice: ChatCompletionToolChoiceOptionParam | NotGiven = NOT_GIVEN,
        tools: Iterable[ChatCompletionToolParam] | NotGiven = NOT_GIVEN,
        top_logprobs: Optional[int] | NotGiven = NOT_GIVEN,
        top_p: Optional[float] | NotGiven = NOT_GIVEN,
        user: str | NotGiven = NOT_GIVEN,
        web_search_options: completion_create_params.WebSearchOptions | NotGiven = NOT_GIVEN,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> ChatCompletion | Stream[ChatCompletionChunk]:
        validate_response_format(response_format)
        return self._post(
            "/chat/completions",
            body=maybe_transform(
                {
                    "messages": messages,
                    "model": model,
                    "audio": audio,
                    "frequency_penalty": frequency_penalty,
                    "function_call": function_call,
                    "functions": functions,
                    "logit_bias": logit_bias,
                    "logprobs": logprobs,
                    "max_completion_tokens": max_completion_tokens,
                    "max_tokens": max_tokens,
                    "metadata": metadata,
                    "modalities": modalities,
                    "n": n,
                    "parallel_tool_calls": parallel_tool_calls,
                    "prediction": prediction,
                    "presence_penalty": presence_penalty,
                    "reasoning_effort": reasoning_effort,
                    "response_format": response_format,
                    "seed": seed,
                    "service_tier": service_tier,
                    "stop": stop,
                    "store": store,
                    "stream": stream,
                    "stream_options": stream_options,
                    "temperature": temperature,
                    "tool_choice": tool_choice,
                    "tools": tools,
                    "top_logprobs": top_logprobs,
                    "top_p": top_p,
                    "user": user,
                    "web_search_options": web_search_options,
                },
                completion_create_params.CompletionCreateParamsStreaming
                if stream
                else completion_create_params.CompletionCreateParamsNonStreaming,
            ),
            options=make_request_options(
                extra_headers=extra_headers, extra_query=extra_query, extra_body=extra_body, timeout=timeout
            ),
            cast_to=ChatCompletion,
            stream=stream or False,
            stream_cls=Stream[ChatCompletionChunk],
        )

    def retrieve(
        self,
        completion_id: str,
        *,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> ChatCompletion:
        """Get a stored chat completion.

        Only Chat Completions that have been created with
        the `store` parameter set to `true` will be returned.

        Args:
          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request, in seconds
        """
        if not completion_id:
            raise ValueError(f"Expected a non-empty value for `completion_id` but received {completion_id!r}")
        return self._get(
            f"/chat/completions/{completion_id}",
            options=make_request_options(
                extra_headers=extra_headers, extra_query=extra_query, extra_body=extra_body, timeout=timeout
            ),
            cast_to=ChatCompletion,
        )

    def update(
        self,
        completion_id: str,
        *,
        metadata: Optional[Metadata],
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> ChatCompletion:
        """Modify a stored chat completion.

        Only Chat Completions that have been created
        with the `store` parameter set to `true` can be modified. Currently, the only
        supported modification is to update the `metadata` field.

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
        if not completion_id:
            raise ValueError(f"Expected a non-empty value for `completion_id` but received {completion_id!r}")
        return self._post(
            f"/chat/completions/{completion_id}",
            body=maybe_transform({"metadata": metadata}, completion_update_params.CompletionUpdateParams),
            options=make_request_options(
                extra_headers=extra_headers, extra_query=extra_query, extra_body=extra_body, timeout=timeout
            ),
            cast_to=ChatCompletion,
        )

    def list(
        self,
        *,
        after: str | NotGiven = NOT_GIVEN,
        limit: int | NotGiven = NOT_GIVEN,
        metadata: Optional[Metadata] | NotGiven = NOT_GIVEN,
        model: str | NotGiven = NOT_GIVEN,
        order: Literal["asc", "desc"] | NotGiven = NOT_GIVEN,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> SyncCursorPage[ChatCompletion]:
        """List stored Chat Completions.

        Only Chat Completions that have been stored with
        the `store` parameter set to `true` will be returned.

        Args:
          after: Identifier for the last chat completion from the previous pagination request.

          limit: Number of Chat Completions to retrieve.

          metadata:
              A list of metadata keys to filter the Chat Completions by. Example:

              `metadata[key1]=value1&metadata[key2]=value2`

          model: The model used to generate the Chat Completions.

          order: Sort order for Chat Completions by timestamp. Use `asc` for ascending order or
              `desc` for descending order. Defaults to `asc`.

          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request, in seconds
        """
        return self._get_api_list(
            "/chat/completions",
            page=SyncCursorPage[ChatCompletion],
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
                        "model": model,
                        "order": order,
                    },
                    completion_list_params.CompletionListParams,
                ),
            ),
            model=ChatCompletion,
        )

    def delete(
        self,
        completion_id: str,
        *,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> ChatCompletionDeleted:
        """Delete a stored chat completion.

        Only Chat Completions that have been created
        with the `store` parameter set to `true` can be deleted.

        Args:
          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request, in seconds
        """
        if not completion_id:
            raise ValueError(f"Expected a non-empty value for `completion_id` but received {completion_id!r}")
        return self._delete(
            f"/chat/completions/{completion_id}",
            options=make_request_options(
                extra_headers=extra_headers, extra_query=extra_query, extra_body=extra_body, timeout=timeout
            ),
            cast_to=ChatCompletionDeleted,
        )


class AsyncCompletions(AsyncAPIResource):
    @cached_property
    def messages(self) -> AsyncMessages:
        return AsyncMessages(self._client)

    @cached_property
    def with_raw_response(self) -> AsyncCompletionsWithRawResponse:
        """
        This property can be used as a prefix for any HTTP method call to return
        the raw response object instead of the parsed content.

        For more information, see https://www.github.com/openai/openai-python#accessing-raw-response-data-eg-headers
        """
        return AsyncCompletionsWithRawResponse(self)

    @cached_property
    def with_streaming_response(self) -> AsyncCompletionsWithStreamingResponse:
        """
        An alternative to `.with_raw_response` that doesn't eagerly read the response body.

        For more information, see https://www.github.com/openai/openai-python#with_streaming_response
        """
        return AsyncCompletionsWithStreamingResponse(self)

    @overload
    async def create(
        self,
        *,
        messages: Iterable[ChatCompletionMessageParam],
        model: Union[str, ChatModel],
        audio: Optional[ChatCompletionAudioParam] | NotGiven = NOT_GIVEN,
        frequency_penalty: Optional[float] | NotGiven = NOT_GIVEN,
        function_call: completion_create_params.FunctionCall | NotGiven = NOT_GIVEN,
        functions: Iterable[completion_create_params.Function] | NotGiven = NOT_GIVEN,
        logit_bias: Optional[Dict[str, int]] | NotGiven = NOT_GIVEN,
        logprobs: Optional[bool] | NotGiven = NOT_GIVEN,
        max_completion_tokens: Optional[int] | NotGiven = NOT_GIVEN,
        max_tokens: Optional[int] | NotGiven = NOT_GIVEN,
        metadata: Optional[Metadata] | NotGiven = NOT_GIVEN,
        modalities: Optional[List[Literal["text", "audio"]]] | NotGiven = NOT_GIVEN,
        n: Optional[int] | NotGiven = NOT_GIVEN,
        parallel_tool_calls: bool | NotGiven = NOT_GIVEN,
        prediction: Optional[ChatCompletionPredictionContentParam] | NotGiven = NOT_GIVEN,
        presence_penalty: Optional[float] | NotGiven = NOT_GIVEN,
        reasoning_effort: Optional[ReasoningEffort] | NotGiven = NOT_GIVEN,
        response_format: completion_create_params.ResponseFormat | NotGiven = NOT_GIVEN,
        seed: Optional[int] | NotGiven = NOT_GIVEN,
        service_tier: Optional[Literal["auto", "default", "flex", "scale"]] | NotGiven = NOT_GIVEN,
        stop: Union[Optional[str], List[str], None] | NotGiven = NOT_GIVEN,
        store: Optional[bool] | NotGiven = NOT_GIVEN,
        stream: Optional[Literal[False]] | NotGiven = NOT_GIVEN,
        stream_options: Optional[ChatCompletionStreamOptionsParam] | NotGiven = NOT_GIVEN,
        temperature: Optional[float] | NotGiven = NOT_GIVEN,
        tool_choice: ChatCompletionToolChoiceOptionParam | NotGiven = NOT_GIVEN,
        tools: Iterable[ChatCompletionToolParam] | NotGiven = NOT_GIVEN,
        top_logprobs: Optional[int] | NotGiven = NOT_GIVEN,
        top_p: Optional[float] | NotGiven = NOT_GIVEN,
        user: str | NotGiven = NOT_GIVEN,
        web_search_options: completion_create_params.WebSearchOptions | NotGiven = NOT_GIVEN,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> ChatCompletion:
        """
        **Starting a new project?** We recommend trying
        [Responses](https://platform.openai.com/docs/api-reference/responses) to take
        advantage of the latest OpenAI platform features. Compare
        [Chat Completions with Responses](https://platform.openai.com/docs/guides/responses-vs-chat-completions?api-mode=responses).

        ---

        Creates a model response for the given chat conversation. Learn more in the
        [text generation](https://platform.openai.com/docs/guides/text-generation),
        [vision](https://platform.openai.com/docs/guides/vision), and
        [audio](https://platform.openai.com/docs/guides/audio) guides.

        Parameter support can differ depending on the model used to generate the
        response, particularly for newer reasoning models. Parameters that are only
        supported for reasoning models are noted below. For the current state of
        unsupported parameters in reasoning models,
        [refer to the reasoning guide](https://platform.openai.com/docs/guides/reasoning).

        Args:
          messages: A list of messages comprising the conversation so far. Depending on the
              [model](https://platform.openai.com/docs/models) you use, different message
              types (modalities) are supported, like
              [text](https://platform.openai.com/docs/guides/text-generation),
              [images](https://platform.openai.com/docs/guides/vision), and
              [audio](https://platform.openai.com/docs/guides/audio).

          model: Model ID used to generate the response, like `gpt-4o` or `o3`. OpenAI offers a
              wide range of models with different capabilities, performance characteristics,
              and price points. Refer to the
              [model guide](https://platform.openai.com/docs/models) to browse and compare
              available models.

          audio: Parameters for audio output. Required when audio output is requested with
              `modalities: ["audio"]`.
              [Learn more](https://platform.openai.com/docs/guides/audio).

          frequency_penalty: Number between -2.0 and 2.0. Positive values penalize new tokens based on their
              existing frequency in the text so far, decreasing the model's likelihood to
              repeat the same line verbatim.

          function_call: Deprecated in favor of `tool_choice`.

              Controls which (if any) function is called by the model.

              `none` means the model will not call a function and instead generates a message.

              `auto` means the model can pick between generating a message or calling a
              function.

              Specifying a particular function via `{"name": "my_function"}` forces the model
              to call that function.

              `none` is the default when no functions are present. `auto` is the default if
              functions are present.

          functions: Deprecated in favor of `tools`.

              A list of functions the model may generate JSON inputs for.

          logit_bias: Modify the likelihood of specified tokens appearing in the completion.

              Accepts a JSON object that maps tokens (specified by their token ID in the
              tokenizer) to an associated bias value from -100 to 100. Mathematically, the
              bias is added to the logits generated by the model prior to sampling. The exact
              effect will vary per model, but values between -1 and 1 should decrease or
              increase likelihood of selection; values like -100 or 100 should result in a ban
              or exclusive selection of the relevant token.

          logprobs: Whether to return log probabilities of the output tokens or not. If true,
              returns the log probabilities of each output token returned in the `content` of
              `message`.

          max_completion_tokens: An upper bound for the number of tokens that can be generated for a completion,
              including visible output tokens and
              [reasoning tokens](https://platform.openai.com/docs/guides/reasoning).

          max_tokens: The maximum number of [tokens](/tokenizer) that can be generated in the chat
              completion. This value can be used to control
              [costs](https://openai.com/api/pricing/) for text generated via API.

              This value is now deprecated in favor of `max_completion_tokens`, and is not
              compatible with
              [o-series models](https://platform.openai.com/docs/guides/reasoning).

          metadata: Set of 16 key-value pairs that can be attached to an object. This can be useful
              for storing additional information about the object in a structured format, and
              querying for objects via API or the dashboard.

              Keys are strings with a maximum length of 64 characters. Values are strings with
              a maximum length of 512 characters.

          modalities: Output types that you would like the model to generate. Most models are capable
              of generating text, which is the default:

              `["text"]`

              The `gpt-4o-audio-preview` model can also be used to
              [generate audio](https://platform.openai.com/docs/guides/audio). To request that
              this model generate both text and audio responses, you can use:

              `["text", "audio"]`

          n: How many chat completion choices to generate for each input message. Note that
              you will be charged based on the number of generated tokens across all of the
              choices. Keep `n` as `1` to minimize costs.

          parallel_tool_calls: Whether to enable
              [parallel function calling](https://platform.openai.com/docs/guides/function-calling#configuring-parallel-function-calling)
              during tool use.

          prediction: Static predicted output content, such as the content of a text file that is
              being regenerated.

          presence_penalty: Number between -2.0 and 2.0. Positive values penalize new tokens based on
              whether they appear in the text so far, increasing the model's likelihood to
              talk about new topics.

          reasoning_effort: **o-series models only**

              Constrains effort on reasoning for
              [reasoning models](https://platform.openai.com/docs/guides/reasoning). Currently
              supported values are `low`, `medium`, and `high`. Reducing reasoning effort can
              result in faster responses and fewer tokens used on reasoning in a response.

          response_format: An object specifying the format that the model must output.

              Setting to `{ "type": "json_schema", "json_schema": {...} }` enables Structured
              Outputs which ensures the model will match your supplied JSON schema. Learn more
              in the
              [Structured Outputs guide](https://platform.openai.com/docs/guides/structured-outputs).

              Setting to `{ "type": "json_object" }` enables the older JSON mode, which
              ensures the message the model generates is valid JSON. Using `json_schema` is
              preferred for models that support it.

          seed: This feature is in Beta. If specified, our system will make a best effort to
              sample deterministically, such that repeated requests with the same `seed` and
              parameters should return the same result. Determinism is not guaranteed, and you
              should refer to the `system_fingerprint` response parameter to monitor changes
              in the backend.

          service_tier: Specifies the latency tier to use for processing the request. This parameter is
              relevant for customers subscribed to the scale tier service:

              - If set to 'auto', and the Project is Scale tier enabled, the system will
                utilize scale tier credits until they are exhausted.
              - If set to 'auto', and the Project is not Scale tier enabled, the request will
                be processed using the default service tier with a lower uptime SLA and no
                latency guarantee.
              - If set to 'default', the request will be processed using the default service
                tier with a lower uptime SLA and no latency guarantee.
              - If set to 'flex', the request will be processed with the Flex Processing
                service tier.
                [Learn more](https://platform.openai.com/docs/guides/flex-processing).
              - When not set, the default behavior is 'auto'.

              When this parameter is set, the response body will include the `service_tier`
              utilized.

          stop: Not supported with latest reasoning models `o3` and `o4-mini`.

              Up to 4 sequences where the API will stop generating further tokens. The
              returned text will not contain the stop sequence.

          store: Whether or not to store the output of this chat completion request for use in
              our [model distillation](https://platform.openai.com/docs/guides/distillation)
              or [evals](https://platform.openai.com/docs/guides/evals) products.

          stream: If set to true, the model response data will be streamed to the client as it is
              generated using
              [server-sent events](https://developer.mozilla.org/en-US/docs/Web/API/Server-sent_events/Using_server-sent_events#Event_stream_format).
              See the
              [Streaming section below](https://platform.openai.com/docs/api-reference/chat/streaming)
              for more information, along with the
              [streaming responses](https://platform.openai.com/docs/guides/streaming-responses)
              guide for more information on how to handle the streaming events.

          stream_options: Options for streaming response. Only set this when you set `stream: true`.

          temperature: What sampling temperature to use, between 0 and 2. Higher values like 0.8 will
              make the output more random, while lower values like 0.2 will make it more
              focused and deterministic. We generally recommend altering this or `top_p` but
              not both.

          tool_choice: Controls which (if any) tool is called by the model. `none` means the model will
              not call any tool and instead generates a message. `auto` means the model can
              pick between generating a message or calling one or more tools. `required` means
              the model must call one or more tools. Specifying a particular tool via
              `{"type": "function", "function": {"name": "my_function"}}` forces the model to
              call that tool.

              `none` is the default when no tools are present. `auto` is the default if tools
              are present.

          tools: A list of tools the model may call. Currently, only functions are supported as a
              tool. Use this to provide a list of functions the model may generate JSON inputs
              for. A max of 128 functions are supported.

          top_logprobs: An integer between 0 and 20 specifying the number of most likely tokens to
              return at each token position, each with an associated log probability.
              `logprobs` must be set to `true` if this parameter is used.

          top_p: An alternative to sampling with temperature, called nucleus sampling, where the
              model considers the results of the tokens with top_p probability mass. So 0.1
              means only the tokens comprising the top 10% probability mass are considered.

              We generally recommend altering this or `temperature` but not both.

          user: A stable identifier for your end-users. Used to boost cache hit rates by better
              bucketing similar requests and to help OpenAI detect and prevent abuse.
              [Learn more](https://platform.openai.com/docs/guides/safety-best-practices#end-user-ids).

          web_search_options: This tool searches the web for relevant results to use in a response. Learn more
              about the
              [web search tool](https://platform.openai.com/docs/guides/tools-web-search?api-mode=chat).

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
        messages: Iterable[ChatCompletionMessageParam],
        model: Union[str, ChatModel],
        stream: Literal[True],
        audio: Optional[ChatCompletionAudioParam] | NotGiven = NOT_GIVEN,
        frequency_penalty: Optional[float] | NotGiven = NOT_GIVEN,
        function_call: completion_create_params.FunctionCall | NotGiven = NOT_GIVEN,
        functions: Iterable[completion_create_params.Function] | NotGiven = NOT_GIVEN,
        logit_bias: Optional[Dict[str, int]] | NotGiven = NOT_GIVEN,
        logprobs: Optional[bool] | NotGiven = NOT_GIVEN,
        max_completion_tokens: Optional[int] | NotGiven = NOT_GIVEN,
        max_tokens: Optional[int] | NotGiven = NOT_GIVEN,
        metadata: Optional[Metadata] | NotGiven = NOT_GIVEN,
        modalities: Optional[List[Literal["text", "audio"]]] | NotGiven = NOT_GIVEN,
        n: Optional[int] | NotGiven = NOT_GIVEN,
        parallel_tool_calls: bool | NotGiven = NOT_GIVEN,
        prediction: Optional[ChatCompletionPredictionContentParam] | NotGiven = NOT_GIVEN,
        presence_penalty: Optional[float] | NotGiven = NOT_GIVEN,
        reasoning_effort: Optional[ReasoningEffort] | NotGiven = NOT_GIVEN,
        response_format: completion_create_params.ResponseFormat | NotGiven = NOT_GIVEN,
        seed: Optional[int] | NotGiven = NOT_GIVEN,
        service_tier: Optional[Literal["auto", "default", "flex", "scale"]] | NotGiven = NOT_GIVEN,
        stop: Union[Optional[str], List[str], None] | NotGiven = NOT_GIVEN,
        store: Optional[bool] | NotGiven = NOT_GIVEN,
        stream_options: Optional[ChatCompletionStreamOptionsParam] | NotGiven = NOT_GIVEN,
        temperature: Optional[float] | NotGiven = NOT_GIVEN,
        tool_choice: ChatCompletionToolChoiceOptionParam | NotGiven = NOT_GIVEN,
        tools: Iterable[ChatCompletionToolParam] | NotGiven = NOT_GIVEN,
        top_logprobs: Optional[int] | NotGiven = NOT_GIVEN,
        top_p: Optional[float] | NotGiven = NOT_GIVEN,
        user: str | NotGiven = NOT_GIVEN,
        web_search_options: completion_create_params.WebSearchOptions | NotGiven = NOT_GIVEN,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> AsyncStream[ChatCompletionChunk]:
        """
        **Starting a new project?** We recommend trying
        [Responses](https://platform.openai.com/docs/api-reference/responses) to take
        advantage of the latest OpenAI platform features. Compare
        [Chat Completions with Responses](https://platform.openai.com/docs/guides/responses-vs-chat-completions?api-mode=responses).

        ---

        Creates a model response for the given chat conversation. Learn more in the
        [text generation](https://platform.openai.com/docs/guides/text-generation),
        [vision](https://platform.openai.com/docs/guides/vision), and
        [audio](https://platform.openai.com/docs/guides/audio) guides.

        Parameter support can differ depending on the model used to generate the
        response, particularly for newer reasoning models. Parameters that are only
        supported for reasoning models are noted below. For the current state of
        unsupported parameters in reasoning models,
        [refer to the reasoning guide](https://platform.openai.com/docs/guides/reasoning).

        Args:
          messages: A list of messages comprising the conversation so far. Depending on the
              [model](https://platform.openai.com/docs/models) you use, different message
              types (modalities) are supported, like
              [text](https://platform.openai.com/docs/guides/text-generation),
              [images](https://platform.openai.com/docs/guides/vision), and
              [audio](https://platform.openai.com/docs/guides/audio).

          model: Model ID used to generate the response, like `gpt-4o` or `o3`. OpenAI offers a
              wide range of models with different capabilities, performance characteristics,
              and price points. Refer to the
              [model guide](https://platform.openai.com/docs/models) to browse and compare
              available models.

          stream: If set to true, the model response data will be streamed to the client as it is
              generated using
              [server-sent events](https://developer.mozilla.org/en-US/docs/Web/API/Server-sent_events/Using_server-sent_events#Event_stream_format).
              See the
              [Streaming section below](https://platform.openai.com/docs/api-reference/chat/streaming)
              for more information, along with the
              [streaming responses](https://platform.openai.com/docs/guides/streaming-responses)
              guide for more information on how to handle the streaming events.

          audio: Parameters for audio output. Required when audio output is requested with
              `modalities: ["audio"]`.
              [Learn more](https://platform.openai.com/docs/guides/audio).

          frequency_penalty: Number between -2.0 and 2.0. Positive values penalize new tokens based on their
              existing frequency in the text so far, decreasing the model's likelihood to
              repeat the same line verbatim.

          function_call: Deprecated in favor of `tool_choice`.

              Controls which (if any) function is called by the model.

              `none` means the model will not call a function and instead generates a message.

              `auto` means the model can pick between generating a message or calling a
              function.

              Specifying a particular function via `{"name": "my_function"}` forces the model
              to call that function.

              `none` is the default when no functions are present. `auto` is the default if
              functions are present.

          functions: Deprecated in favor of `tools`.

              A list of functions the model may generate JSON inputs for.

          logit_bias: Modify the likelihood of specified tokens appearing in the completion.

              Accepts a JSON object that maps tokens (specified by their token ID in the
              tokenizer) to an associated bias value from -100 to 100. Mathematically, the
              bias is added to the logits generated by the model prior to sampling. The exact
              effect will vary per model, but values between -1 and 1 should decrease or
              increase likelihood of selection; values like -100 or 100 should result in a ban
              or exclusive selection of the relevant token.

          logprobs: Whether to return log probabilities of the output tokens or not. If true,
              returns the log probabilities of each output token returned in the `content` of
              `message`.

          max_completion_tokens: An upper bound for the number of tokens that can be generated for a completion,
              including visible output tokens and
              [reasoning tokens](https://platform.openai.com/docs/guides/reasoning).

          max_tokens: The maximum number of [tokens](/tokenizer) that can be generated in the chat
              completion. This value can be used to control
              [costs](https://openai.com/api/pricing/) for text generated via API.

              This value is now deprecated in favor of `max_completion_tokens`, and is not
              compatible with
              [o-series models](https://platform.openai.com/docs/guides/reasoning).

          metadata: Set of 16 key-value pairs that can be attached to an object. This can be useful
              for storing additional information about the object in a structured format, and
              querying for objects via API or the dashboard.

              Keys are strings with a maximum length of 64 characters. Values are strings with
              a maximum length of 512 characters.

          modalities: Output types that you would like the model to generate. Most models are capable
              of generating text, which is the default:

              `["text"]`

              The `gpt-4o-audio-preview` model can also be used to
              [generate audio](https://platform.openai.com/docs/guides/audio). To request that
              this model generate both text and audio responses, you can use:

              `["text", "audio"]`

          n: How many chat completion choices to generate for each input message. Note that
              you will be charged based on the number of generated tokens across all of the
              choices. Keep `n` as `1` to minimize costs.

          parallel_tool_calls: Whether to enable
              [parallel function calling](https://platform.openai.com/docs/guides/function-calling#configuring-parallel-function-calling)
              during tool use.

          prediction: Static predicted output content, such as the content of a text file that is
              being regenerated.

          presence_penalty: Number between -2.0 and 2.0. Positive values penalize new tokens based on
              whether they appear in the text so far, increasing the model's likelihood to
              talk about new topics.

          reasoning_effort: **o-series models only**

              Constrains effort on reasoning for
              [reasoning models](https://platform.openai.com/docs/guides/reasoning). Currently
              supported values are `low`, `medium`, and `high`. Reducing reasoning effort can
              result in faster responses and fewer tokens used on reasoning in a response.

          response_format: An object specifying the format that the model must output.

              Setting to `{ "type": "json_schema", "json_schema": {...} }` enables Structured
              Outputs which ensures the model will match your supplied JSON schema. Learn more
              in the
              [Structured Outputs guide](https://platform.openai.com/docs/guides/structured-outputs).

              Setting to `{ "type": "json_object" }` enables the older JSON mode, which
              ensures the message the model generates is valid JSON. Using `json_schema` is
              preferred for models that support it.

          seed: This feature is in Beta. If specified, our system will make a best effort to
              sample deterministically, such that repeated requests with the same `seed` and
              parameters should return the same result. Determinism is not guaranteed, and you
              should refer to the `system_fingerprint` response parameter to monitor changes
              in the backend.

          service_tier: Specifies the latency tier to use for processing the request. This parameter is
              relevant for customers subscribed to the scale tier service:

              - If set to 'auto', and the Project is Scale tier enabled, the system will
                utilize scale tier credits until they are exhausted.
              - If set to 'auto', and the Project is not Scale tier enabled, the request will
                be processed using the default service tier with a lower uptime SLA and no
                latency guarantee.
              - If set to 'default', the request will be processed using the default service
                tier with a lower uptime SLA and no latency guarantee.
              - If set to 'flex', the request will be processed with the Flex Processing
                service tier.
                [Learn more](https://platform.openai.com/docs/guides/flex-processing).
              - When not set, the default behavior is 'auto'.

              When this parameter is set, the response body will include the `service_tier`
              utilized.

          stop: Not supported with latest reasoning models `o3` and `o4-mini`.

              Up to 4 sequences where the API will stop generating further tokens. The
              returned text will not contain the stop sequence.

          store: Whether or not to store the output of this chat completion request for use in
              our [model distillation](https://platform.openai.com/docs/guides/distillation)
              or [evals](https://platform.openai.com/docs/guides/evals) products.

          stream_options: Options for streaming response. Only set this when you set `stream: true`.

          temperature: What sampling temperature to use, between 0 and 2. Higher values like 0.8 will
              make the output more random, while lower values like 0.2 will make it more
              focused and deterministic. We generally recommend altering this or `top_p` but
              not both.

          tool_choice: Controls which (if any) tool is called by the model. `none` means the model will
              not call any tool and instead generates a message. `auto` means the model can
              pick between generating a message or calling one or more tools. `required` means
              the model must call one or more tools. Specifying a particular tool via
              `{"type": "function", "function": {"name": "my_function"}}` forces the model to
              call that tool.

              `none` is the default when no tools are present. `auto` is the default if tools
              are present.

          tools: A list of tools the model may call. Currently, only functions are supported as a
              tool. Use this to provide a list of functions the model may generate JSON inputs
              for. A max of 128 functions are supported.

          top_logprobs: An integer between 0 and 20 specifying the number of most likely tokens to
              return at each token position, each with an associated log probability.
              `logprobs` must be set to `true` if this parameter is used.

          top_p: An alternative to sampling with temperature, called nucleus sampling, where the
              model considers the results of the tokens with top_p probability mass. So 0.1
              means only the tokens comprising the top 10% probability mass are considered.

              We generally recommend altering this or `temperature` but not both.

          user: A stable identifier for your end-users. Used to boost cache hit rates by better
              bucketing similar requests and to help OpenAI detect and prevent abuse.
              [Learn more](https://platform.openai.com/docs/guides/safety-best-practices#end-user-ids).

          web_search_options: This tool searches the web for relevant results to use in a response. Learn more
              about the
              [web search tool](https://platform.openai.com/docs/guides/tools-web-search?api-mode=chat).

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
        messages: Iterable[ChatCompletionMessageParam],
        model: Union[str, ChatModel],
        stream: bool,
        audio: Optional[ChatCompletionAudioParam] | NotGiven = NOT_GIVEN,
        frequency_penalty: Optional[float] | NotGiven = NOT_GIVEN,
        function_call: completion_create_params.FunctionCall | NotGiven = NOT_GIVEN,
        functions: Iterable[completion_create_params.Function] | NotGiven = NOT_GIVEN,
        logit_bias: Optional[Dict[str, int]] | NotGiven = NOT_GIVEN,
        logprobs: Optional[bool] | NotGiven = NOT_GIVEN,
        max_completion_tokens: Optional[int] | NotGiven = NOT_GIVEN,
        max_tokens: Optional[int] | NotGiven = NOT_GIVEN,
        metadata: Optional[Metadata] | NotGiven = NOT_GIVEN,
        modalities: Optional[List[Literal["text", "audio"]]] | NotGiven = NOT_GIVEN,
        n: Optional[int] | NotGiven = NOT_GIVEN,
        parallel_tool_calls: bool | NotGiven = NOT_GIVEN,
        prediction: Optional[ChatCompletionPredictionContentParam] | NotGiven = NOT_GIVEN,
        presence_penalty: Optional[float] | NotGiven = NOT_GIVEN,
        reasoning_effort: Optional[ReasoningEffort] | NotGiven = NOT_GIVEN,
        response_format: completion_create_params.ResponseFormat | NotGiven = NOT_GIVEN,
        seed: Optional[int] | NotGiven = NOT_GIVEN,
        service_tier: Optional[Literal["auto", "default", "flex", "scale"]] | NotGiven = NOT_GIVEN,
        stop: Union[Optional[str], List[str], None] | NotGiven = NOT_GIVEN,
        store: Optional[bool] | NotGiven = NOT_GIVEN,
        stream_options: Optional[ChatCompletionStreamOptionsParam] | NotGiven = NOT_GIVEN,
        temperature: Optional[float] | NotGiven = NOT_GIVEN,
        tool_choice: ChatCompletionToolChoiceOptionParam | NotGiven = NOT_GIVEN,
        tools: Iterable[ChatCompletionToolParam] | NotGiven = NOT_GIVEN,
        top_logprobs: Optional[int] | NotGiven = NOT_GIVEN,
        top_p: Optional[float] | NotGiven = NOT_GIVEN,
        user: str | NotGiven = NOT_GIVEN,
        web_search_options: completion_create_params.WebSearchOptions | NotGiven = NOT_GIVEN,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> ChatCompletion | AsyncStream[ChatCompletionChunk]:
        """
        **Starting a new project?** We recommend trying
        [Responses](https://platform.openai.com/docs/api-reference/responses) to take
        advantage of the latest OpenAI platform features. Compare
        [Chat Completions with Responses](https://platform.openai.com/docs/guides/responses-vs-chat-completions?api-mode=responses).

        ---

        Creates a model response for the given chat conversation. Learn more in the
        [text generation](https://platform.openai.com/docs/guides/text-generation),
        [vision](https://platform.openai.com/docs/guides/vision), and
        [audio](https://platform.openai.com/docs/guides/audio) guides.

        Parameter support can differ depending on the model used to generate the
        response, particularly for newer reasoning models. Parameters that are only
        supported for reasoning models are noted below. For the current state of
        unsupported parameters in reasoning models,
        [refer to the reasoning guide](https://platform.openai.com/docs/guides/reasoning).

        Args:
          messages: A list of messages comprising the conversation so far. Depending on the
              [model](https://platform.openai.com/docs/models) you use, different message
              types (modalities) are supported, like
              [text](https://platform.openai.com/docs/guides/text-generation),
              [images](https://platform.openai.com/docs/guides/vision), and
              [audio](https://platform.openai.com/docs/guides/audio).

          model: Model ID used to generate the response, like `gpt-4o` or `o3`. OpenAI offers a
              wide range of models with different capabilities, performance characteristics,
              and price points. Refer to the
              [model guide](https://platform.openai.com/docs/models) to browse and compare
              available models.

          stream: If set to true, the model response data will be streamed to the client as it is
              generated using
              [server-sent events](https://developer.mozilla.org/en-US/docs/Web/API/Server-sent_events/Using_server-sent_events#Event_stream_format).
              See the
              [Streaming section below](https://platform.openai.com/docs/api-reference/chat/streaming)
              for more information, along with the
              [streaming responses](https://platform.openai.com/docs/guides/streaming-responses)
              guide for more information on how to handle the streaming events.

          audio: Parameters for audio output. Required when audio output is requested with
              `modalities: ["audio"]`.
              [Learn more](https://platform.openai.com/docs/guides/audio).

          frequency_penalty: Number between -2.0 and 2.0. Positive values penalize new tokens based on their
              existing frequency in the text so far, decreasing the model's likelihood to
              repeat the same line verbatim.

          function_call: Deprecated in favor of `tool_choice`.

              Controls which (if any) function is called by the model.

              `none` means the model will not call a function and instead generates a message.

              `auto` means the model can pick between generating a message or calling a
              function.

              Specifying a particular function via `{"name": "my_function"}` forces the model
              to call that function.

              `none` is the default when no functions are present. `auto` is the default if
              functions are present.

          functions: Deprecated in favor of `tools`.

              A list of functions the model may generate JSON inputs for.

          logit_bias: Modify the likelihood of specified tokens appearing in the completion.

              Accepts a JSON object that maps tokens (specified by their token ID in the
              tokenizer) to an associated bias value from -100 to 100. Mathematically, the
              bias is added to the logits generated by the model prior to sampling. The exact
              effect will vary per model, but values between -1 and 1 should decrease or
              increase likelihood of selection; values like -100 or 100 should result in a ban
              or exclusive selection of the relevant token.

          logprobs: Whether to return log probabilities of the output tokens or not. If true,
              returns the log probabilities of each output token returned in the `content` of
              `message`.

          max_completion_tokens: An upper bound for the number of tokens that can be generated for a completion,
              including visible output tokens and
              [reasoning tokens](https://platform.openai.com/docs/guides/reasoning).

          max_tokens: The maximum number of [tokens](/tokenizer) that can be generated in the chat
              completion. This value can be used to control
              [costs](https://openai.com/api/pricing/) for text generated via API.

              This value is now deprecated in favor of `max_completion_tokens`, and is not
              compatible with
              [o-series models](https://platform.openai.com/docs/guides/reasoning).

          metadata: Set of 16 key-value pairs that can be attached to an object. This can be useful
              for storing additional information about the object in a structured format, and
              querying for objects via API or the dashboard.

              Keys are strings with a maximum length of 64 characters. Values are strings with
              a maximum length of 512 characters.

          modalities: Output types that you would like the model to generate. Most models are capable
              of generating text, which is the default:

              `["text"]`

              The `gpt-4o-audio-preview` model can also be used to
              [generate audio](https://platform.openai.com/docs/guides/audio). To request that
              this model generate both text and audio responses, you can use:

              `["text", "audio"]`

          n: How many chat completion choices to generate for each input message. Note that
              you will be charged based on the number of generated tokens across all of the
              choices. Keep `n` as `1` to minimize costs.

          parallel_tool_calls: Whether to enable
              [parallel function calling](https://platform.openai.com/docs/guides/function-calling#configuring-parallel-function-calling)
              during tool use.

          prediction: Static predicted output content, such as the content of a text file that is
              being regenerated.

          presence_penalty: Number between -2.0 and 2.0. Positive values penalize new tokens based on
              whether they appear in the text so far, increasing the model's likelihood to
              talk about new topics.

          reasoning_effort: **o-series models only**

              Constrains effort on reasoning for
              [reasoning models](https://platform.openai.com/docs/guides/reasoning). Currently
              supported values are `low`, `medium`, and `high`. Reducing reasoning effort can
              result in faster responses and fewer tokens used on reasoning in a response.

          response_format: An object specifying the format that the model must output.

              Setting to `{ "type": "json_schema", "json_schema": {...} }` enables Structured
              Outputs which ensures the model will match your supplied JSON schema. Learn more
              in the
              [Structured Outputs guide](https://platform.openai.com/docs/guides/structured-outputs).

              Setting to `{ "type": "json_object" }` enables the older JSON mode, which
              ensures the message the model generates is valid JSON. Using `json_schema` is
              preferred for models that support it.

          seed: This feature is in Beta. If specified, our system will make a best effort to
              sample deterministically, such that repeated requests with the same `seed` and
              parameters should return the same result. Determinism is not guaranteed, and you
              should refer to the `system_fingerprint` response parameter to monitor changes
              in the backend.

          service_tier: Specifies the latency tier to use for processing the request. This parameter is
              relevant for customers subscribed to the scale tier service:

              - If set to 'auto', and the Project is Scale tier enabled, the system will
                utilize scale tier credits until they are exhausted.
              - If set to 'auto', and the Project is not Scale tier enabled, the request will
                be processed using the default service tier with a lower uptime SLA and no
                latency guarantee.
              - If set to 'default', the request will be processed using the default service
                tier with a lower uptime SLA and no latency guarantee.
              - If set to 'flex', the request will be processed with the Flex Processing
                service tier.
                [Learn more](https://platform.openai.com/docs/guides/flex-processing).
              - When not set, the default behavior is 'auto'.

              When this parameter is set, the response body will include the `service_tier`
              utilized.

          stop: Not supported with latest reasoning models `o3` and `o4-mini`.

              Up to 4 sequences where the API will stop generating further tokens. The
              returned text will not contain the stop sequence.

          store: Whether or not to store the output of this chat completion request for use in
              our [model distillation](https://platform.openai.com/docs/guides/distillation)
              or [evals](https://platform.openai.com/docs/guides/evals) products.

          stream_options: Options for streaming response. Only set this when you set `stream: true`.

          temperature: What sampling temperature to use, between 0 and 2. Higher values like 0.8 will
              make the output more random, while lower values like 0.2 will make it more
              focused and deterministic. We generally recommend altering this or `top_p` but
              not both.

          tool_choice: Controls which (if any) tool is called by the model. `none` means the model will
              not call any tool and instead generates a message. `auto` means the model can
              pick between generating a message or calling one or more tools. `required` means
              the model must call one or more tools. Specifying a particular tool via
              `{"type": "function", "function": {"name": "my_function"}}` forces the model to
              call that tool.

              `none` is the default when no tools are present. `auto` is the default if tools
              are present.

          tools: A list of tools the model may call. Currently, only functions are supported as a
              tool. Use this to provide a list of functions the model may generate JSON inputs
              for. A max of 128 functions are supported.

          top_logprobs: An integer between 0 and 20 specifying the number of most likely tokens to
              return at each token position, each with an associated log probability.
              `logprobs` must be set to `true` if this parameter is used.

          top_p: An alternative to sampling with temperature, called nucleus sampling, where the
              model considers the results of the tokens with top_p probability mass. So 0.1
              means only the tokens comprising the top 10% probability mass are considered.

              We generally recommend altering this or `temperature` but not both.

          user: A stable identifier for your end-users. Used to boost cache hit rates by better
              bucketing similar requests and to help OpenAI detect and prevent abuse.
              [Learn more](https://platform.openai.com/docs/guides/safety-best-practices#end-user-ids).

          web_search_options: This tool searches the web for relevant results to use in a response. Learn more
              about the
              [web search tool](https://platform.openai.com/docs/guides/tools-web-search?api-mode=chat).

          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request, in seconds
        """
        ...

    @required_args(["messages", "model"], ["messages", "model", "stream"])
    async def create(
        self,
        *,
        messages: Iterable[ChatCompletionMessageParam],
        model: Union[str, ChatModel],
        audio: Optional[ChatCompletionAudioParam] | NotGiven = NOT_GIVEN,
        frequency_penalty: Optional[float] | NotGiven = NOT_GIVEN,
        function_call: completion_create_params.FunctionCall | NotGiven = NOT_GIVEN,
        functions: Iterable[completion_create_params.Function] | NotGiven = NOT_GIVEN,
        logit_bias: Optional[Dict[str, int]] | NotGiven = NOT_GIVEN,
        logprobs: Optional[bool] | NotGiven = NOT_GIVEN,
        max_completion_tokens: Optional[int] | NotGiven = NOT_GIVEN,
        max_tokens: Optional[int] | NotGiven = NOT_GIVEN,
        metadata: Optional[Metadata] | NotGiven = NOT_GIVEN,
        modalities: Optional[List[Literal["text", "audio"]]] | NotGiven = NOT_GIVEN,
        n: Optional[int] | NotGiven = NOT_GIVEN,
        parallel_tool_calls: bool | NotGiven = NOT_GIVEN,
        prediction: Optional[ChatCompletionPredictionContentParam] | NotGiven = NOT_GIVEN,
        presence_penalty: Optional[float] | NotGiven = NOT_GIVEN,
        reasoning_effort: Optional[ReasoningEffort] | NotGiven = NOT_GIVEN,
        response_format: completion_create_params.ResponseFormat | NotGiven = NOT_GIVEN,
        seed: Optional[int] | NotGiven = NOT_GIVEN,
        service_tier: Optional[Literal["auto", "default", "flex", "scale"]] | NotGiven = NOT_GIVEN,
        stop: Union[Optional[str], List[str], None] | NotGiven = NOT_GIVEN,
        store: Optional[bool] | NotGiven = NOT_GIVEN,
        stream: Optional[Literal[False]] | Literal[True] | NotGiven = NOT_GIVEN,
        stream_options: Optional[ChatCompletionStreamOptionsParam] | NotGiven = NOT_GIVEN,
        temperature: Optional[float] | NotGiven = NOT_GIVEN,
        tool_choice: ChatCompletionToolChoiceOptionParam | NotGiven = NOT_GIVEN,
        tools: Iterable[ChatCompletionToolParam] | NotGiven = NOT_GIVEN,
        top_logprobs: Optional[int] | NotGiven = NOT_GIVEN,
        top_p: Optional[float] | NotGiven = NOT_GIVEN,
        user: str | NotGiven = NOT_GIVEN,
        web_search_options: completion_create_params.WebSearchOptions | NotGiven = NOT_GIVEN,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> ChatCompletion | AsyncStream[ChatCompletionChunk]:
        validate_response_format(response_format)
        return await self._post(
            "/chat/completions",
            body=await async_maybe_transform(
                {
                    "messages": messages,
                    "model": model,
                    "audio": audio,
                    "frequency_penalty": frequency_penalty,
                    "function_call": function_call,
                    "functions": functions,
                    "logit_bias": logit_bias,
                    "logprobs": logprobs,
                    "max_completion_tokens": max_completion_tokens,
                    "max_tokens": max_tokens,
                    "metadata": metadata,
                    "modalities": modalities,
                    "n": n,
                    "parallel_tool_calls": parallel_tool_calls,
                    "prediction": prediction,
                    "presence_penalty": presence_penalty,
                    "reasoning_effort": reasoning_effort,
                    "response_format": response_format,
                    "seed": seed,
                    "service_tier": service_tier,
                    "stop": stop,
                    "store": store,
                    "stream": stream,
                    "stream_options": stream_options,
                    "temperature": temperature,
                    "tool_choice": tool_choice,
                    "tools": tools,
                    "top_logprobs": top_logprobs,
                    "top_p": top_p,
                    "user": user,
                    "web_search_options": web_search_options,
                },
                completion_create_params.CompletionCreateParamsStreaming
                if stream
                else completion_create_params.CompletionCreateParamsNonStreaming,
            ),
            options=make_request_options(
                extra_headers=extra_headers, extra_query=extra_query, extra_body=extra_body, timeout=timeout
            ),
            cast_to=ChatCompletion,
            stream=stream or False,
            stream_cls=AsyncStream[ChatCompletionChunk],
        )

    async def retrieve(
        self,
        completion_id: str,
        *,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> ChatCompletion:
        """Get a stored chat completion.

        Only Chat Completions that have been created with
        the `store` parameter set to `true` will be returned.

        Args:
          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request, in seconds
        """
        if not completion_id:
            raise ValueError(f"Expected a non-empty value for `completion_id` but received {completion_id!r}")
        return await self._get(
            f"/chat/completions/{completion_id}",
            options=make_request_options(
                extra_headers=extra_headers, extra_query=extra_query, extra_body=extra_body, timeout=timeout
            ),
            cast_to=ChatCompletion,
        )

    async def update(
        self,
        completion_id: str,
        *,
        metadata: Optional[Metadata],
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> ChatCompletion:
        """Modify a stored chat completion.

        Only Chat Completions that have been created
        with the `store` parameter set to `true` can be modified. Currently, the only
        supported modification is to update the `metadata` field.

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
        if not completion_id:
            raise ValueError(f"Expected a non-empty value for `completion_id` but received {completion_id!r}")
        return await self._post(
            f"/chat/completions/{completion_id}",
            body=await async_maybe_transform({"metadata": metadata}, completion_update_params.CompletionUpdateParams),
            options=make_request_options(
                extra_headers=extra_headers, extra_query=extra_query, extra_body=extra_body, timeout=timeout
            ),
            cast_to=ChatCompletion,
        )

    def list(
        self,
        *,
        after: str | NotGiven = NOT_GIVEN,
        limit: int | NotGiven = NOT_GIVEN,
        metadata: Optional[Metadata] | NotGiven = NOT_GIVEN,
        model: str | NotGiven = NOT_GIVEN,
        order: Literal["asc", "desc"] | NotGiven = NOT_GIVEN,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> AsyncPaginator[ChatCompletion, AsyncCursorPage[ChatCompletion]]:
        """List stored Chat Completions.

        Only Chat Completions that have been stored with
        the `store` parameter set to `true` will be returned.

        Args:
          after: Identifier for the last chat completion from the previous pagination request.

          limit: Number of Chat Completions to retrieve.

          metadata:
              A list of metadata keys to filter the Chat Completions by. Example:

              `metadata[key1]=value1&metadata[key2]=value2`

          model: The model used to generate the Chat Completions.

          order: Sort order for Chat Completions by timestamp. Use `asc` for ascending order or
              `desc` for descending order. Defaults to `asc`.

          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request, in seconds
        """
        return self._get_api_list(
            "/chat/completions",
            page=AsyncCursorPage[ChatCompletion],
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
                        "model": model,
                        "order": order,
                    },
                    completion_list_params.CompletionListParams,
                ),
            ),
            model=ChatCompletion,
        )

    async def delete(
        self,
        completion_id: str,
        *,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> ChatCompletionDeleted:
        """Delete a stored chat completion.

        Only Chat Completions that have been created
        with the `store` parameter set to `true` can be deleted.

        Args:
          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request, in seconds
        """
        if not completion_id:
            raise ValueError(f"Expected a non-empty value for `completion_id` but received {completion_id!r}")
        return await self._delete(
            f"/chat/completions/{completion_id}",
            options=make_request_options(
                extra_headers=extra_headers, extra_query=extra_query, extra_body=extra_body, timeout=timeout
            ),
            cast_to=ChatCompletionDeleted,
        )


class CompletionsWithRawResponse:
    def __init__(self, completions: Completions) -> None:
        self._completions = completions

        self.create = _legacy_response.to_raw_response_wrapper(
            completions.create,
        )
        self.retrieve = _legacy_response.to_raw_response_wrapper(
            completions.retrieve,
        )
        self.update = _legacy_response.to_raw_response_wrapper(
            completions.update,
        )
        self.list = _legacy_response.to_raw_response_wrapper(
            completions.list,
        )
        self.delete = _legacy_response.to_raw_response_wrapper(
            completions.delete,
        )

    @cached_property
    def messages(self) -> MessagesWithRawResponse:
        return MessagesWithRawResponse(self._completions.messages)


class AsyncCompletionsWithRawResponse:
    def __init__(self, completions: AsyncCompletions) -> None:
        self._completions = completions

        self.create = _legacy_response.async_to_raw_response_wrapper(
            completions.create,
        )
        self.retrieve = _legacy_response.async_to_raw_response_wrapper(
            completions.retrieve,
        )
        self.update = _legacy_response.async_to_raw_response_wrapper(
            completions.update,
        )
        self.list = _legacy_response.async_to_raw_response_wrapper(
            completions.list,
        )
        self.delete = _legacy_response.async_to_raw_response_wrapper(
            completions.delete,
        )

    @cached_property
    def messages(self) -> AsyncMessagesWithRawResponse:
        return AsyncMessagesWithRawResponse(self._completions.messages)


class CompletionsWithStreamingResponse:
    def __init__(self, completions: Completions) -> None:
        self._completions = completions

        self.create = to_streamed_response_wrapper(
            completions.create,
        )
        self.retrieve = to_streamed_response_wrapper(
            completions.retrieve,
        )
        self.update = to_streamed_response_wrapper(
            completions.update,
        )
        self.list = to_streamed_response_wrapper(
            completions.list,
        )
        self.delete = to_streamed_response_wrapper(
            completions.delete,
        )

    @cached_property
    def messages(self) -> MessagesWithStreamingResponse:
        return MessagesWithStreamingResponse(self._completions.messages)


class AsyncCompletionsWithStreamingResponse:
    def __init__(self, completions: AsyncCompletions) -> None:
        self._completions = completions

        self.create = async_to_streamed_response_wrapper(
            completions.create,
        )
        self.retrieve = async_to_streamed_response_wrapper(
            completions.retrieve,
        )
        self.update = async_to_streamed_response_wrapper(
            completions.update,
        )
        self.list = async_to_streamed_response_wrapper(
            completions.list,
        )
        self.delete = async_to_streamed_response_wrapper(
            completions.delete,
        )

    @cached_property
    def messages(self) -> AsyncMessagesWithStreamingResponse:
        return AsyncMessagesWithStreamingResponse(self._completions.messages)


def validate_response_format(response_format: object) -> None:
    if inspect.isclass(response_format) and issubclass(response_format, pydantic.BaseModel):
        raise TypeError(
            "You tried to pass a `BaseModel` class to `chat.completions.create()`; You must use `beta.chat.completions.parse()` instead"
        )

# === NexusCore/openenv\Lib\site-packages\pygments\lexers\templates.py ===
"""
    pygments.lexers.templates
    ~~~~~~~~~~~~~~~~~~~~~~~~~

    Lexers for various template engines' markup.

    :copyright: Copyright 2006-2025 by the Pygments team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

import re

from pygments.lexers.html import HtmlLexer, XmlLexer
from pygments.lexers.javascript import JavascriptLexer, LassoLexer
from pygments.lexers.css import CssLexer
from pygments.lexers.php import PhpLexer
from pygments.lexers.python import PythonLexer
from pygments.lexers.perl import PerlLexer
from pygments.lexers.jvm import JavaLexer, TeaLangLexer
from pygments.lexers.data import YamlLexer
from pygments.lexers.sql import SqlLexer
from pygments.lexer import Lexer, DelegatingLexer, RegexLexer, bygroups, \
    include, using, this, default, combined
from pygments.token import Error, Punctuation, Whitespace, \
    Text, Comment, Operator, Keyword, Name, String, Number, Other, Token
from pygments.util import html_doctype_matches, looks_like_xml

__all__ = ['HtmlPhpLexer', 'XmlPhpLexer', 'CssPhpLexer',
           'JavascriptPhpLexer', 'ErbLexer', 'RhtmlLexer',
           'XmlErbLexer', 'CssErbLexer', 'JavascriptErbLexer',
           'SmartyLexer', 'HtmlSmartyLexer', 'XmlSmartyLexer',
           'CssSmartyLexer', 'JavascriptSmartyLexer', 'DjangoLexer',
           'HtmlDjangoLexer', 'CssDjangoLexer', 'XmlDjangoLexer',
           'JavascriptDjangoLexer', 'GenshiLexer', 'HtmlGenshiLexer',
           'GenshiTextLexer', 'CssGenshiLexer', 'JavascriptGenshiLexer',
           'MyghtyLexer', 'MyghtyHtmlLexer', 'MyghtyXmlLexer',
           'MyghtyCssLexer', 'MyghtyJavascriptLexer', 'MasonLexer', 'MakoLexer',
           'MakoHtmlLexer', 'MakoXmlLexer', 'MakoJavascriptLexer',
           'MakoCssLexer', 'JspLexer', 'CheetahLexer', 'CheetahHtmlLexer',
           'CheetahXmlLexer', 'CheetahJavascriptLexer', 'EvoqueLexer',
           'EvoqueHtmlLexer', 'EvoqueXmlLexer', 'ColdfusionLexer',
           'ColdfusionHtmlLexer', 'ColdfusionCFCLexer', 'VelocityLexer',
           'VelocityHtmlLexer', 'VelocityXmlLexer', 'SspLexer',
           'TeaTemplateLexer', 'LassoHtmlLexer', 'LassoXmlLexer',
           'LassoCssLexer', 'LassoJavascriptLexer', 'HandlebarsLexer',
           'HandlebarsHtmlLexer', 'YamlJinjaLexer', 'LiquidLexer',
           'TwigLexer', 'TwigHtmlLexer', 'Angular2Lexer', 'Angular2HtmlLexer',
           'SqlJinjaLexer']


class ErbLexer(Lexer):
    """
    Generic ERB (Ruby Templating) lexer.

    Just highlights ruby code between the preprocessor directives, other data
    is left untouched by the lexer.

    All options are also forwarded to the `RubyLexer`.
    """

    name = 'ERB'
    url = 'https://github.com/ruby/erb'
    aliases = ['erb']
    mimetypes = ['application/x-ruby-templating']
    version_added = ''

    _block_re = re.compile(r'(<%%|%%>|<%=|<%#|<%-|<%|-%>|%>|^%[^%].*?$)', re.M)

    def __init__(self, **options):
        from pygments.lexers.ruby import RubyLexer
        self.ruby_lexer = RubyLexer(**options)
        Lexer.__init__(self, **options)

    def get_tokens_unprocessed(self, text):
        """
        Since ERB doesn't allow "<%" and other tags inside of ruby
        blocks we have to use a split approach here that fails for
        that too.
        """
        tokens = self._block_re.split(text)
        tokens.reverse()
        state = idx = 0
        try:
            while True:
                # text
                if state == 0:
                    val = tokens.pop()
                    yield idx, Other, val
                    idx += len(val)
                    state = 1
                # block starts
                elif state == 1:
                    tag = tokens.pop()
                    # literals
                    if tag in ('<%%', '%%>'):
                        yield idx, Other, tag
                        idx += 3
                        state = 0
                    # comment
                    elif tag == '<%#':
                        yield idx, Comment.Preproc, tag
                        val = tokens.pop()
                        yield idx + 3, Comment, val
                        idx += 3 + len(val)
                        state = 2
                    # blocks or output
                    elif tag in ('<%', '<%=', '<%-'):
                        yield idx, Comment.Preproc, tag
                        idx += len(tag)
                        data = tokens.pop()
                        r_idx = 0
                        for r_idx, r_token, r_value in \
                                self.ruby_lexer.get_tokens_unprocessed(data):
                            yield r_idx + idx, r_token, r_value
                        idx += len(data)
                        state = 2
                    elif tag in ('%>', '-%>'):
                        yield idx, Error, tag
                        idx += len(tag)
                        state = 0
                    # % raw ruby statements
                    else:
                        yield idx, Comment.Preproc, tag[0]
                        r_idx = 0
                        for r_idx, r_token, r_value in \
                                self.ruby_lexer.get_tokens_unprocessed(tag[1:]):
                            yield idx + 1 + r_idx, r_token, r_value
                        idx += len(tag)
                        state = 0
                # block ends
                elif state == 2:
                    tag = tokens.pop()
                    if tag not in ('%>', '-%>'):
                        yield idx, Other, tag
                    else:
                        yield idx, Comment.Preproc, tag
                    idx += len(tag)
                    state = 0
        except IndexError:
            return

    def analyse_text(text):
        if '<%' in text and '%>' in text:
            return 0.4


class SmartyLexer(RegexLexer):
    """
    Generic Smarty template lexer.

    Just highlights smarty code between the preprocessor directives, other
    data is left untouched by the lexer.
    """

    name = 'Smarty'
    url = 'https://www.smarty.net/'
    aliases = ['smarty']
    filenames = ['*.tpl']
    mimetypes = ['application/x-smarty']
    version_added = ''

    flags = re.MULTILINE | re.DOTALL

    tokens = {
        'root': [
            (r'[^{]+', Other),
            (r'(\{)(\*.*?\*)(\})',
             bygroups(Comment.Preproc, Comment, Comment.Preproc)),
            (r'(\{php\})(.*?)(\{/php\})',
             bygroups(Comment.Preproc, using(PhpLexer, startinline=True),
                      Comment.Preproc)),
            (r'(\{)(/?[a-zA-Z_]\w*)(\s*)',
             bygroups(Comment.Preproc, Name.Function, Text), 'smarty'),
            (r'\{', Comment.Preproc, 'smarty')
        ],
        'smarty': [
            (r'\s+', Text),
            (r'\{', Comment.Preproc, '#push'),
            (r'\}', Comment.Preproc, '#pop'),
            (r'#[a-zA-Z_]\w*#', Name.Variable),
            (r'\$[a-zA-Z_]\w*(\.\w+)*', Name.Variable),
            (r'[~!%^&*()+=|\[\]:;,.<>/?@-]', Operator),
            (r'(true|false|null)\b', Keyword.Constant),
            (r"[0-9](\.[0-9]*)?(eE[+-][0-9])?[flFLdD]?|"
             r"0[xX][0-9a-fA-F]+[Ll]?", Number),
            (r'"(\\\\|\\[^\\]|[^"\\])*"', String.Double),
            (r"'(\\\\|\\[^\\]|[^'\\])*'", String.Single),
            (r'[a-zA-Z_]\w*', Name.Attribute)
        ]
    }

    def analyse_text(text):
        rv = 0.0
        if re.search(r'\{if\s+.*?\}.*?\{/if\}', text):
            rv += 0.15
        if re.search(r'\{include\s+file=.*?\}', text):
            rv += 0.15
        if re.search(r'\{foreach\s+.*?\}.*?\{/foreach\}', text):
            rv += 0.15
        if re.search(r'\{\$.*?\}', text):
            rv += 0.01
        return rv


class VelocityLexer(RegexLexer):
    """
    Generic Velocity template lexer.

    Just highlights velocity directives and variable references, other
    data is left untouched by the lexer.
    """

    name = 'Velocity'
    url = 'https://velocity.apache.org/'
    aliases = ['velocity']
    filenames = ['*.vm', '*.fhtml']
    version_added = ''

    flags = re.MULTILINE | re.DOTALL

    identifier = r'[a-zA-Z_]\w*'

    tokens = {
        'root': [
            (r'[^{#$]+', Other),
            (r'(#)(\*.*?\*)(#)',
             bygroups(Comment.Preproc, Comment, Comment.Preproc)),
            (r'(##)(.*?$)',
             bygroups(Comment.Preproc, Comment)),
            (r'(#\{?)(' + identifier + r')(\}?)(\s?\()',
             bygroups(Comment.Preproc, Name.Function, Comment.Preproc, Punctuation),
             'directiveparams'),
            (r'(#\{?)(' + identifier + r')(\}|\b)',
             bygroups(Comment.Preproc, Name.Function, Comment.Preproc)),
            (r'\$!?\{?', Punctuation, 'variable')
        ],
        'variable': [
            (identifier, Name.Variable),
            (r'\(', Punctuation, 'funcparams'),
            (r'(\.)(' + identifier + r')',
             bygroups(Punctuation, Name.Variable), '#push'),
            (r'\}', Punctuation, '#pop'),
            default('#pop')
        ],
        'directiveparams': [
            (r'(&&|\|\||==?|!=?|[-<>+*%&|^/])|\b(eq|ne|gt|lt|ge|le|not|in)\b',
             Operator),
            (r'\[', Operator, 'rangeoperator'),
            (r'\b' + identifier + r'\b', Name.Function),
            include('funcparams')
        ],
        'rangeoperator': [
            (r'\.\.', Operator),
            include('funcparams'),
            (r'\]', Operator, '#pop')
        ],
        'funcparams': [
            (r'\$!?\{?', Punctuation, 'variable'),
            (r'\s+', Text),
            (r'[,:]', Punctuation),
            (r'"(\\\\|\\[^\\]|[^"\\])*"', String.Double),
            (r"'(\\\\|\\[^\\]|[^'\\])*'", String.Single),
            (r"0[xX][0-9a-fA-F]+[Ll]?", Number),
            (r"\b[0-9]+\b", Number),
            (r'(true|false|null)\b', Keyword.Constant),
            (r'\(', Punctuation, '#push'),
            (r'\)', Punctuation, '#pop'),
            (r'\{', Punctuation, '#push'),
            (r'\}', Punctuation, '#pop'),
            (r'\[', Punctuation, '#push'),
            (r'\]', Punctuation, '#pop'),
        ]
    }

    def analyse_text(text):
        rv = 0.0
        if re.search(r'#\{?macro\}?\(.*?\).*?#\{?end\}?', text, re.DOTALL):
            rv += 0.25
        if re.search(r'#\{?if\}?\(.+?\).*?#\{?end\}?', text, re.DOTALL):
            rv += 0.15
        if re.search(r'#\{?foreach\}?\(.+?\).*?#\{?end\}?', text, re.DOTALL):
            rv += 0.15
        if re.search(r'\$!?\{?[a-zA-Z_]\w*(\([^)]*\))?'
                     r'(\.\w+(\([^)]*\))?)*\}?', text):
            rv += 0.01
        return rv


class VelocityHtmlLexer(DelegatingLexer):
    """
    Subclass of the `VelocityLexer` that highlights unlexed data
    with the `HtmlLexer`.

    """

    name = 'HTML+Velocity'
    aliases = ['html+velocity']
    version_added = ''
    alias_filenames = ['*.html', '*.fhtml']
    mimetypes = ['text/html+velocity']
    url = 'https://velocity.apache.org/'

    def __init__(self, **options):
        super().__init__(HtmlLexer, VelocityLexer, **options)


class VelocityXmlLexer(DelegatingLexer):
    """
    Subclass of the `VelocityLexer` that highlights unlexed data
    with the `XmlLexer`.

    """

    name = 'XML+Velocity'
    aliases = ['xml+velocity']
    version_added = ''
    alias_filenames = ['*.xml', '*.vm']
    mimetypes = ['application/xml+velocity']
    url = 'https://velocity.apache.org/'

    def __init__(self, **options):
        super().__init__(XmlLexer, VelocityLexer, **options)

    def analyse_text(text):
        rv = VelocityLexer.analyse_text(text) - 0.01
        if looks_like_xml(text):
            rv += 0.4
        return rv


class DjangoLexer(RegexLexer):
    """
    Generic `Django <https://www.djangoproject.com/documentation/templates/>`_
    and `Jinja <https://jinja.palletsprojects.com>`_ template lexer.

    It just highlights django/jinja code between the preprocessor directives,
    other data is left untouched by the lexer.
    """

    name = 'Django/Jinja'
    aliases = ['django', 'jinja']
    mimetypes = ['application/x-django-templating', 'application/x-jinja']
    url = 'https://www.djangoproject.com/documentation/templates'
    version_added = ''

    flags = re.M | re.S

    tokens = {
        'root': [
            (r'[^{]+', Other),
            (r'\{\{', Comment.Preproc, 'var'),
            # jinja/django comments
            (r'\{#.*?#\}', Comment),
            # django comments
            (r'(\{%)(-?\s*)(comment)(\s*-?)(%\})(.*?)'
             r'(\{%)(-?\s*)(endcomment)(\s*-?)(%\})',
             bygroups(Comment.Preproc, Text, Keyword, Text, Comment.Preproc,
                      Comment, Comment.Preproc, Text, Keyword, Text,
                      Comment.Preproc)),
            # raw jinja blocks
            (r'(\{%)(-?\s*)(raw)(\s*-?)(%\})(.*?)'
             r'(\{%)(-?\s*)(endraw)(\s*-?)(%\})',
             bygroups(Comment.Preproc, Text, Keyword, Text, Comment.Preproc,
                      Text, Comment.Preproc, Text, Keyword, Text,
                      Comment.Preproc)),
            # filter blocks
            (r'(\{%)(-?\s*)(filter)(\s+)([a-zA-Z_]\w*)',
             bygroups(Comment.Preproc, Text, Keyword, Text, Name.Function),
             'block'),
            (r'(\{%)(-?\s*)([a-zA-Z_]\w*)',
             bygroups(Comment.Preproc, Text, Keyword), 'block'),
            (r'\{', Other)
        ],
        'varnames': [
            (r'(\|)(\s*)([a-zA-Z_]\w*)',
             bygroups(Operator, Text, Name.Function)),
            (r'(is)(\s+)(not)?(\s+)?([a-zA-Z_]\w*)',
             bygroups(Keyword, Text, Keyword, Text, Name.Function)),
            (r'(_|true|false|none|True|False|None)\b', Keyword.Pseudo),
            (r'(in|as|reversed|recursive|not|and|or|is|if|else|import|'
             r'with(?:(?:out)?\s*context)?|scoped|ignore\s+missing)\b',
             Keyword),
            (r'(loop|block|super|forloop)\b', Name.Builtin),
            (r'[a-zA-Z_][\w-]*', Name.Variable),
            (r'\.\w+', Name.Variable),
            (r':?"(\\\\|\\[^\\]|[^"\\])*"', String.Double),
            (r":?'(\\\\|\\[^\\]|[^'\\])*'", String.Single),
            (r'([{}()\[\]+\-*/%,:~]|[><=]=?|!=)', Operator),
            (r"[0-9](\.[0-9]*)?(eE[+-][0-9])?[flFLdD]?|"
             r"0[xX][0-9a-fA-F]+[Ll]?", Number),
        ],
        'var': [
            (r'\s+', Text),
            (r'(-?)(\}\})', bygroups(Text, Comment.Preproc), '#pop'),
            include('varnames')
        ],
        'block': [
            (r'\s+', Text),
            (r'(-?)(%\})', bygroups(Text, Comment.Preproc), '#pop'),
            include('varnames'),
            (r'.', Punctuation)
        ]
    }

    def analyse_text(text):
        rv = 0.0
        if re.search(r'\{%\s*(block|extends)', text) is not None:
            rv += 0.4
        if re.search(r'\{%\s*if\s*.*?%\}', text) is not None:
            rv += 0.1
        if re.search(r'\{\{.*?\}\}', text) is not None:
            rv += 0.1
        return rv


class MyghtyLexer(RegexLexer):
    """
    Generic myghty templates lexer. Code that isn't Myghty
    markup is yielded as `Token.Other`.
    """

    name = 'Myghty'
    url = 'http://www.myghty.org/'
    aliases = ['myghty']
    filenames = ['*.myt', 'autodelegate']
    mimetypes = ['application/x-myghty']
    version_added = '0.6'

    tokens = {
        'root': [
            (r'\s+', Text),
            (r'(?s)(<%(?:def|method))(\s*)(.*?)(>)(.*?)(</%\2\s*>)',
             bygroups(Name.Tag, Text, Name.Function, Name.Tag,
                      using(this), Name.Tag)),
            (r'(?s)(<%\w+)(.*?)(>)(.*?)(</%\2\s*>)',
             bygroups(Name.Tag, Name.Function, Name.Tag,
                      using(PythonLexer), Name.Tag)),
            (r'(<&[^|])(.*?)(,.*?)?(&>)',
             bygroups(Name.Tag, Name.Function, using(PythonLexer), Name.Tag)),
            (r'(?s)(<&\|)(.*?)(,.*?)?(&>)',
             bygroups(Name.Tag, Name.Function, using(PythonLexer), Name.Tag)),
            (r'</&>', Name.Tag),
            (r'(?s)(<%!?)(.*?)(%>)',
             bygroups(Name.Tag, using(PythonLexer), Name.Tag)),
            (r'(?<=^)#[^\n]*(\n|\Z)', Comment),
            (r'(?<=^)(%)([^\n]*)(\n|\Z)',
             bygroups(Name.Tag, using(PythonLexer), Other)),
            (r"""(?sx)
                 (.+?)               # anything, followed by:
                 (?:
                  (?<=\n)(?=[%#]) |  # an eval or comment line
                  (?=</?[%&]) |      # a substitution or block or
                                     # call start or end
                                     # - don't consume
                  (\\\n) |           # an escaped newline
                  \Z                 # end of string
                 )""", bygroups(Other, Operator)),
        ]
    }


class MyghtyHtmlLexer(DelegatingLexer):
    """
    Subclass of the `MyghtyLexer` that highlights unlexed data
    with the `HtmlLexer`.
    """

    name = 'HTML+Myghty'
    aliases = ['html+myghty']
    mimetypes = ['text/html+myghty']
    url = 'http://www.myghty.org/'
    version_added = '0.6'

    def __init__(self, **options):
        super().__init__(HtmlLexer, MyghtyLexer, **options)


class MyghtyXmlLexer(DelegatingLexer):
    """
    Subclass of the `MyghtyLexer` that highlights unlexed data
    with the `XmlLexer`.
    """

    name = 'XML+Myghty'
    aliases = ['xml+myghty']
    mimetypes = ['application/xml+myghty']
    url = 'http://www.myghty.org/'
    version_added = '0.6'

    def __init__(self, **options):
        super().__init__(XmlLexer, MyghtyLexer, **options)


class MyghtyJavascriptLexer(DelegatingLexer):
    """
    Subclass of the `MyghtyLexer` that highlights unlexed data
    with the `JavascriptLexer`.
    """

    name = 'JavaScript+Myghty'
    aliases = ['javascript+myghty', 'js+myghty']
    mimetypes = ['application/x-javascript+myghty',
                 'text/x-javascript+myghty',
                 'text/javascript+mygthy']
    url = 'http://www.myghty.org/'
    version_added = '0.6'

    def __init__(self, **options):
        super().__init__(JavascriptLexer, MyghtyLexer, **options)


class MyghtyCssLexer(DelegatingLexer):
    """
    Subclass of the `MyghtyLexer` that highlights unlexed data
    with the `CssLexer`.
    """

    name = 'CSS+Myghty'
    aliases = ['css+myghty']
    mimetypes = ['text/css+myghty']
    url = 'http://www.myghty.org/'
    version_added = '0.6'

    def __init__(self, **options):
        super().__init__(CssLexer, MyghtyLexer, **options)


class MasonLexer(RegexLexer):
    """
    Generic mason templates lexer. Stolen from Myghty lexer. Code that isn't
    Mason markup is HTML.
    """
    name = 'Mason'
    url = 'http://www.masonhq.com/'
    aliases = ['mason']
    filenames = ['*.m', '*.mhtml', '*.mc', '*.mi', 'autohandler', 'dhandler']
    mimetypes = ['application/x-mason']
    version_added = '1.4'

    tokens = {
        'root': [
            (r'\s+', Whitespace),
            (r'(?s)(<%doc>)(.*?)(</%doc>)',
             bygroups(Name.Tag, Comment.Multiline, Name.Tag)),
            (r'(?s)(<%(?:def|method))(\s*)(.*?)(>)(.*?)(</%\2\s*>)',
             bygroups(Name.Tag, Whitespace, Name.Function, Name.Tag,
                      using(this), Name.Tag)),
            (r'(?s)(<%(\w+)(.*?)(>))(.*?)(</%\2\s*>)',
             bygroups(Name.Tag, None, None, None, using(PerlLexer), Name.Tag)),
            (r'(?s)(<&[^|])(.*?)(,.*?)?(&>)',
             bygroups(Name.Tag, Name.Function, using(PerlLexer), Name.Tag)),
            (r'(?s)(<&\|)(.*?)(,.*?)?(&>)',
             bygroups(Name.Tag, Name.Function, using(PerlLexer), Name.Tag)),
            (r'</&>', Name.Tag),
            (r'(?s)(<%!?)(.*?)(%>)',
             bygroups(Name.Tag, using(PerlLexer), Name.Tag)),
            (r'(?<=^)#[^\n]*(\n|\Z)', Comment),
            (r'(?<=^)(%)([^\n]*)(\n|\Z)',
             bygroups(Name.Tag, using(PerlLexer), Other)),
            (r"""(?sx)
                 (.+?)               # anything, followed by:
                 (?:
                  (?<=\n)(?=[%#]) |  # an eval or comment line
                  (?=</?[%&]) |      # a substitution or block or
                                     # call start or end
                                     # - don't consume
                  (\\\n) |           # an escaped newline
                  \Z                 # end of string
                 )""", bygroups(using(HtmlLexer), Operator)),
        ]
    }

    def analyse_text(text):
        result = 0.0
        if re.search(r'</%(class|doc|init)>', text) is not None:
            result = 1.0
        elif re.search(r'<&.+&>', text, re.DOTALL) is not None:
            result = 0.11
        return result


class MakoLexer(RegexLexer):
    """
    Generic mako templates lexer. Code that isn't Mako
    markup is yielded as `Token.Other`.
    """

    name = 'Mako'
    url = 'http://www.makotemplates.org/'
    aliases = ['mako']
    filenames = ['*.mao']
    mimetypes = ['application/x-mako']
    version_added = '0.7'

    tokens = {
        'root': [
            (r'(\s*)(%)(\s*end(?:\w+))(\n|\Z)',
             bygroups(Text.Whitespace, Comment.Preproc, Keyword, Other)),
            (r'(\s*)(%)([^\n]*)(\n|\Z)',
             bygroups(Text.Whitespace, Comment.Preproc, using(PythonLexer), Other)),
            (r'(\s*)(##[^\n]*)(\n|\Z)',
             bygroups(Text.Whitespace, Comment.Single, Text.Whitespace)),
            (r'(?s)<%doc>.*?</%doc>', Comment.Multiline),
            (r'(<%)([\w.:]+)',
             bygroups(Comment.Preproc, Name.Builtin), 'tag'),
            (r'(</%)([\w.:]+)(>)',
             bygroups(Comment.Preproc, Name.Builtin, Comment.Preproc)),
            (r'<%(?=([\w.:]+))', Comment.Preproc, 'ondeftags'),
            (r'(?s)(<%(?:!?))(.*?)(%>)',
             bygroups(Comment.Preproc, using(PythonLexer), Comment.Preproc)),
            (r'(\$\{)(.*?)(\})',
             bygroups(Comment.Preproc, using(PythonLexer), Comment.Preproc)),
            (r'''(?sx)
                (.+?)                # anything, followed by:
                (?:
                 (?<=\n)(?=%|\#\#) | # an eval or comment line
                 (?=\#\*) |          # multiline comment
                 (?=</?%) |          # a python block
                                     # call start or end
                 (?=\$\{) |          # a substitution
                 (?<=\n)(?=\s*%) |
                                     # - don't consume
                 (\\\n) |            # an escaped newline
                 \Z                  # end of string
                )
            ''', bygroups(Other, Operator)),
            (r'\s+', Text),
        ],
        'ondeftags': [
            (r'<%', Comment.Preproc),
            (r'(?<=<%)(include|inherit|namespace|page)', Name.Builtin),
            include('tag'),
        ],
        'tag': [
            (r'((?:\w+)\s*=)(\s*)(".*?")',
             bygroups(Name.Attribute, Text, String)),
            (r'/?\s*>', Comment.Preproc, '#pop'),
            (r'\s+', Text),
        ],
        'attr': [
            ('".*?"', String, '#pop'),
            ("'.*?'", String, '#pop'),
            (r'[^\s>]+', String, '#pop'),
        ],
    }


class MakoHtmlLexer(DelegatingLexer):
    """
    Subclass of the `MakoLexer` that highlights unlexed data
    with the `HtmlLexer`.
    """

    name = 'HTML+Mako'
    aliases = ['html+mako']
    mimetypes = ['text/html+mako']
    url = 'http://www.makotemplates.org/'
    version_added = '0.7'

    def __init__(self, **options):
        super().__init__(HtmlLexer, MakoLexer, **options)


class MakoXmlLexer(DelegatingLexer):
    """
    Subclass of the `MakoLexer` that highlights unlexed data
    with the `XmlLexer`.
    """

    name = 'XML+Mako'
    aliases = ['xml+mako']
    mimetypes = ['application/xml+mako']
    url = 'http://www.makotemplates.org/'
    version_added = '0.7'

    def __init__(self, **options):
        super().__init__(XmlLexer, MakoLexer, **options)


class MakoJavascriptLexer(DelegatingLexer):
    """
    Subclass of the `MakoLexer` that highlights unlexed data
    with the `JavascriptLexer`.
    """

    name = 'JavaScript+Mako'
    aliases = ['javascript+mako', 'js+mako']
    mimetypes = ['application/x-javascript+mako',
                 'text/x-javascript+mako',
                 'text/javascript+mako']
    url = 'http://www.makotemplates.org/'
    version_added = '0.7'

    def __init__(self, **options):
        super().__init__(JavascriptLexer, MakoLexer, **options)


class MakoCssLexer(DelegatingLexer):
    """
    Subclass of the `MakoLexer` that highlights unlexed data
    with the `CssLexer`.
    """

    name = 'CSS+Mako'
    aliases = ['css+mako']
    mimetypes = ['text/css+mako']
    url = 'http://www.makotemplates.org/'
    version_added = '0.7'

    def __init__(self, **options):
        super().__init__(CssLexer, MakoLexer, **options)


# Genshi and Cheetah lexers courtesy of Matt Good.

class CheetahPythonLexer(Lexer):
    """
    Lexer for handling Cheetah's special $ tokens in Python syntax.
    """

    def get_tokens_unprocessed(self, text):
        pylexer = PythonLexer(**self.options)
        for pos, type_, value in pylexer.get_tokens_unprocessed(text):
            if type_ == Token.Error and value == '$':
                type_ = Comment.Preproc
            yield pos, type_, value


class CheetahLexer(RegexLexer):
    """
    Generic cheetah templates lexer. Code that isn't Cheetah
    markup is yielded as `Token.Other`.  This also works for
    `spitfire templates`_ which use the same syntax.

    .. _spitfire templates: http://code.google.com/p/spitfire/
    """

    name = 'Cheetah'
    url = 'http://www.cheetahtemplate.org/'
    aliases = ['cheetah', 'spitfire']
    filenames = ['*.tmpl', '*.spt']
    mimetypes = ['application/x-cheetah', 'application/x-spitfire']
    version_added = ''

    tokens = {
        'root': [
            (r'(##[^\n]*)$',
             (bygroups(Comment))),
            (r'#[*](.|\n)*?[*]#', Comment),
            (r'#end[^#\n]*(?:#|$)', Comment.Preproc),
            (r'#slurp$', Comment.Preproc),
            (r'(#[a-zA-Z]+)([^#\n]*)(#|$)',
             (bygroups(Comment.Preproc, using(CheetahPythonLexer),
                       Comment.Preproc))),
            # TODO support other Python syntax like $foo['bar']
            (r'(\$)([a-zA-Z_][\w.]*\w)',
             bygroups(Comment.Preproc, using(CheetahPythonLexer))),
            (r'(?s)(\$\{!?)(.*?)(\})',
             bygroups(Comment.Preproc, using(CheetahPythonLexer),
                      Comment.Preproc)),
            (r'''(?sx)
                (.+?)               # anything, followed by:
                (?:
                 (?=\#[#a-zA-Z]*) | # an eval comment
                 (?=\$[a-zA-Z_{]) | # a substitution
                 \Z                 # end of string
                )
            ''', Other),
            (r'\s+', Text),
        ],
    }


class CheetahHtmlLexer(DelegatingLexer):
    """
    Subclass of the `CheetahLexer` that highlights unlexed data
    with the `HtmlLexer`.
    """

    name = 'HTML+Cheetah'
    aliases = ['html+cheetah', 'html+spitfire', 'htmlcheetah']
    mimetypes = ['text/html+cheetah', 'text/html+spitfire']
    url = 'http://www.cheetahtemplate.org/'
    version_added = ''

    def __init__(self, **options):
        super().__init__(HtmlLexer, CheetahLexer, **options)


class CheetahXmlLexer(DelegatingLexer):
    """
    Subclass of the `CheetahLexer` that highlights unlexed data
    with the `XmlLexer`.
    """

    name = 'XML+Cheetah'
    aliases = ['xml+cheetah', 'xml+spitfire']
    mimetypes = ['application/xml+cheetah', 'application/xml+spitfire']
    url = 'http://www.cheetahtemplate.org/'
    version_added = ''

    def __init__(self, **options):
        super().__init__(XmlLexer, CheetahLexer, **options)


class CheetahJavascriptLexer(DelegatingLexer):
    """
    Subclass of the `CheetahLexer` that highlights unlexed data
    with the `JavascriptLexer`.
    """

    name = 'JavaScript+Cheetah'
    aliases = ['javascript+cheetah', 'js+cheetah',
               'javascript+spitfire', 'js+spitfire']
    mimetypes = ['application/x-javascript+cheetah',
                 'text/x-javascript+cheetah',
                 'text/javascript+cheetah',
                 'application/x-javascript+spitfire',
                 'text/x-javascript+spitfire',
                 'text/javascript+spitfire']
    url = 'http://www.cheetahtemplate.org/'
    version_added = ''

    def __init__(self, **options):
        super().__init__(JavascriptLexer, CheetahLexer, **options)


class GenshiTextLexer(RegexLexer):
    """
    A lexer that highlights genshi text templates.
    """

    name = 'Genshi Text'
    url = 'https://genshi.edgewall.org/'
    aliases = ['genshitext']
    mimetypes = ['application/x-genshi-text', 'text/x-genshi']
    version_added = ''

    tokens = {
        'root': [
            (r'[^#$\s]+', Other),
            (r'^(\s*)(##.*)$', bygroups(Text, Comment)),
            (r'^(\s*)(#)', bygroups(Text, Comment.Preproc), 'directive'),
            include('variable'),
            (r'[#$\s]', Other),
        ],
        'directive': [
            (r'\n', Text, '#pop'),
            (r'(?:def|for|if)\s+.*', using(PythonLexer), '#pop'),
            (r'(choose|when|with)([^\S\n]+)(.*)',
             bygroups(Keyword, Text, using(PythonLexer)), '#pop'),
            (r'(choose|otherwise)\b', Keyword, '#pop'),
            (r'(end\w*)([^\S\n]*)(.*)', bygroups(Keyword, Text, Comment), '#pop'),
        ],
        'variable': [
            (r'(?<!\$)(\$\{)(.+?)(\})',
             bygroups(Comment.Preproc, using(PythonLexer), Comment.Preproc)),
            (r'(?<!\$)(\$)([a-zA-Z_][\w.]*)',
             Name.Variable),
        ]
    }


class GenshiMarkupLexer(RegexLexer):
    """
    Base lexer for Genshi markup, used by `HtmlGenshiLexer` and
    `GenshiLexer`.
    """

    flags = re.DOTALL

    tokens = {
        'root': [
            (r'[^<$]+', Other),
            (r'(<\?python)(.*?)(\?>)',
             bygroups(Comment.Preproc, using(PythonLexer), Comment.Preproc)),
            # yield style and script blocks as Other
            (r'<\s*(script|style)\s*.*?>.*?<\s*/\1\s*>', Other),
            (r'<\s*py:[a-zA-Z0-9]+', Name.Tag, 'pytag'),
            (r'<\s*[a-zA-Z0-9:.]+', Name.Tag, 'tag'),
            include('variable'),
            (r'[<$]', Other),
        ],
        'pytag': [
            (r'\s+', Text),
            (r'[\w:-]+\s*=', Name.Attribute, 'pyattr'),
            (r'/?\s*>', Name.Tag, '#pop'),
        ],
        'pyattr': [
            ('(")(.*?)(")', bygroups(String, using(PythonLexer), String), '#pop'),
            ("(')(.*?)(')", bygroups(String, using(PythonLexer), String), '#pop'),
            (r'[^\s>]+', String, '#pop'),
        ],
        'tag': [
            (r'\s+', Text),
            (r'py:[\w-]+\s*=', Name.Attribute, 'pyattr'),
            (r'[\w:-]+\s*=', Name.Attribute, 'attr'),
            (r'/?\s*>', Name.Tag, '#pop'),
        ],
        'attr': [
            ('"', String, 'attr-dstring'),
            ("'", String, 'attr-sstring'),
            (r'[^\s>]*', String, '#pop')
        ],
        'attr-dstring': [
            ('"', String, '#pop'),
            include('strings'),
            ("'", String)
        ],
        'attr-sstring': [
            ("'", String, '#pop'),
            include('strings'),
            ("'", String)
        ],
        'strings': [
            ('[^"\'$]+', String),
            include('variable')
        ],
        'variable': [
            (r'(?<!\$)(\$\{)(.+?)(\})',
             bygroups(Comment.Preproc, using(PythonLexer), Comment.Preproc)),
            (r'(?<!\$)(\$)([a-zA-Z_][\w\.]*)',
             Name.Variable),
        ]
    }


class HtmlGenshiLexer(DelegatingLexer):
    """
    A lexer that highlights `genshi <https://genshi.edgewall.org/>`_ and
    `kid <http://kid-templating.org/>`_ kid HTML templates.
    """

    name = 'HTML+Genshi'
    aliases = ['html+genshi', 'html+kid']
    version_added = ''
    alias_filenames = ['*.html', '*.htm', '*.xhtml']
    mimetypes = ['text/html+genshi']
    url = 'https://genshi.edgewall.org/'

    def __init__(self, **options):
        super().__init__(HtmlLexer, GenshiMarkupLexer, **options)

    def analyse_text(text):
        rv = 0.0
        if re.search(r'\$\{.*?\}', text) is not None:
            rv += 0.2
        if re.search(r'py:(.*?)=["\']', text) is not None:
            rv += 0.2
        return rv + HtmlLexer.analyse_text(text) - 0.01


class GenshiLexer(DelegatingLexer):
    """
    A lexer that highlights `genshi <https://genshi.edgewall.org/>`_ and
    `kid <http://kid-templating.org/>`_ kid XML templates.
    """

    name = 'Genshi'
    aliases = ['genshi', 'kid', 'xml+genshi', 'xml+kid']
    filenames = ['*.kid']
    version_added = ''
    alias_filenames = ['*.xml']
    mimetypes = ['application/x-genshi', 'application/x-kid']
    url = 'https://genshi.edgewall.org/'

    def __init__(self, **options):
        super().__init__(XmlLexer, GenshiMarkupLexer, **options)

    def analyse_text(text):
        rv = 0.0
        if re.search(r'\$\{.*?\}', text) is not None:
            rv += 0.2
        if re.search(r'py:(.*?)=["\']', text) is not None:
            rv += 0.2
        return rv + XmlLexer.analyse_text(text) - 0.01


class JavascriptGenshiLexer(DelegatingLexer):
    """
    A lexer that highlights javascript code in genshi text templates.
    """

    name = 'JavaScript+Genshi Text'
    aliases = ['js+genshitext', 'js+genshi', 'javascript+genshitext',
               'javascript+genshi']
    version_added = ''
    alias_filenames = ['*.js']
    mimetypes = ['application/x-javascript+genshi',
                 'text/x-javascript+genshi',
                 'text/javascript+genshi']
    url = 'https://genshi.edgewall.org'

    def __init__(self, **options):
        super().__init__(JavascriptLexer, GenshiTextLexer, **options)

    def analyse_text(text):
        return GenshiLexer.analyse_text(text) - 0.05


class CssGenshiLexer(DelegatingLexer):
    """
    A lexer that highlights CSS definitions in genshi text templates.
    """

    name = 'CSS+Genshi Text'
    aliases = ['css+genshitext', 'css+genshi']
    version_added = ''
    alias_filenames = ['*.css']
    mimetypes = ['text/css+genshi']
    url = 'https://genshi.edgewall.org'

    def __init__(self, **options):
        super().__init__(CssLexer, GenshiTextLexer, **options)

    def analyse_text(text):
        return GenshiLexer.analyse_text(text) - 0.05


class RhtmlLexer(DelegatingLexer):
    """
    Subclass of the ERB lexer that highlights the unlexed data with the
    html lexer.

    Nested Javascript and CSS is highlighted too.
    """

    name = 'RHTML'
    aliases = ['rhtml', 'html+erb', 'html+ruby']
    filenames = ['*.rhtml']
    version_added = ''
    alias_filenames = ['*.html', '*.htm', '*.xhtml']
    mimetypes = ['text/html+ruby']
    url = 'https://github.com/ruby/erb'


    def __init__(self, **options):
        super().__init__(HtmlLexer, ErbLexer, **options)

    def analyse_text(text):
        rv = ErbLexer.analyse_text(text) - 0.01
        if html_doctype_matches(text):
            # one more than the XmlErbLexer returns
            rv += 0.5
        return rv


class XmlErbLexer(DelegatingLexer):
    """
    Subclass of `ErbLexer` which highlights data outside preprocessor
    directives with the `XmlLexer`.
    """

    name = 'XML+Ruby'
    aliases = ['xml+ruby', 'xml+erb']
    version_added = ''
    alias_filenames = ['*.xml']
    mimetypes = ['application/xml+ruby']
    url = 'https://github.com/ruby/erb'

    def __init__(self, **options):
        super().__init__(XmlLexer, ErbLexer, **options)

    def analyse_text(text):
        rv = ErbLexer.analyse_text(text) - 0.01
        if looks_like_xml(text):
            rv += 0.4
        return rv


class CssErbLexer(DelegatingLexer):
    """
    Subclass of `ErbLexer` which highlights unlexed data with the `CssLexer`.
    """

    name = 'CSS+Ruby'
    aliases = ['css+ruby', 'css+erb']
    version_added = ''
    alias_filenames = ['*.css']
    mimetypes = ['text/css+ruby']
    url = 'https://github.com/ruby/erb'

    def __init__(self, **options):
        super().__init__(CssLexer, ErbLexer, **options)

    def analyse_text(text):
        return ErbLexer.analyse_text(text) - 0.05


class JavascriptErbLexer(DelegatingLexer):
    """
    Subclass of `ErbLexer` which highlights unlexed data with the
    `JavascriptLexer`.
    """

    name = 'JavaScript+Ruby'
    aliases = ['javascript+ruby', 'js+ruby', 'javascript+erb', 'js+erb']
    version_added = ''
    alias_filenames = ['*.js']
    mimetypes = ['application/x-javascript+ruby',
                 'text/x-javascript+ruby',
                 'text/javascript+ruby']
    url = 'https://github.com/ruby/erb'

    def __init__(self, **options):
        super().__init__(JavascriptLexer, ErbLexer, **options)

    def analyse_text(text):
        return ErbLexer.analyse_text(text) - 0.05


class HtmlPhpLexer(DelegatingLexer):
    """
    Subclass of `PhpLexer` that highlights unhandled data with the `HtmlLexer`.

    Nested Javascript and CSS is highlighted too.
    """

    name = 'HTML+PHP'
    aliases = ['html+php']
    filenames = ['*.phtml']
    version_added = ''
    alias_filenames = ['*.php', '*.html', '*.htm', '*.xhtml',
                       '*.php[345]']
    mimetypes = ['application/x-php',
                 'application/x-httpd-php', 'application/x-httpd-php3',
                 'application/x-httpd-php4', 'application/x-httpd-php5']
    url = 'https://www.php.net'


    def __init__(self, **options):
        super().__init__(HtmlLexer, PhpLexer, **options)

    def analyse_text(text):
        rv = PhpLexer.analyse_text(text) - 0.01
        if html_doctype_matches(text):
            rv += 0.5
        return rv


class XmlPhpLexer(DelegatingLexer):
    """
    Subclass of `PhpLexer` that highlights unhandled data with the `XmlLexer`.
    """

    name = 'XML+PHP'
    aliases = ['xml+php']
    version_added = ''
    alias_filenames = ['*.xml', '*.php', '*.php[345]']
    mimetypes = ['application/xml+php']
    url = 'https://www.php.net'

    def __init__(self, **options):
        super().__init__(XmlLexer, PhpLexer, **options)

    def analyse_text(text):
        rv = PhpLexer.analyse_text(text) - 0.01
        if looks_like_xml(text):
            rv += 0.4
        return rv


class CssPhpLexer(DelegatingLexer):
    """
    Subclass of `PhpLexer` which highlights unmatched data with the `CssLexer`.
    """

    name = 'CSS+PHP'
    aliases = ['css+php']
    version_added = ''
    alias_filenames = ['*.css']
    mimetypes = ['text/css+php']
    url = 'https://www.php.net'

    def __init__(self, **options):
        super().__init__(CssLexer, PhpLexer, **options)

    def analyse_text(text):
        return PhpLexer.analyse_text(text) - 0.05


class JavascriptPhpLexer(DelegatingLexer):
    """
    Subclass of `PhpLexer` which highlights unmatched data with the
    `JavascriptLexer`.
    """

    name = 'JavaScript+PHP'
    aliases = ['javascript+php', 'js+php']
    version_added = ''
    alias_filenames = ['*.js']
    mimetypes = ['application/x-javascript+php',
                 'text/x-javascript+php',
                 'text/javascript+php']
    url = 'https://www.php.net'

    def __init__(self, **options):
        super().__init__(JavascriptLexer, PhpLexer, **options)

    def analyse_text(text):
        return PhpLexer.analyse_text(text)


class HtmlSmartyLexer(DelegatingLexer):
    """
    Subclass of the `SmartyLexer` that highlights unlexed data with the
    `HtmlLexer`.

    Nested Javascript and CSS is highlighted too.
    """

    name = 'HTML+Smarty'
    aliases = ['html+smarty']
    version_added = ''
    alias_filenames = ['*.html', '*.htm', '*.xhtml', '*.tpl']
    mimetypes = ['text/html+smarty']
    url = 'https://www.smarty.net/'

    def __init__(self, **options):
        super().__init__(HtmlLexer, SmartyLexer, **options)

    def analyse_text(text):
        rv = SmartyLexer.analyse_text(text) - 0.01
        if html_doctype_matches(text):
            rv += 0.5
        return rv


class XmlSmartyLexer(DelegatingLexer):
    """
    Subclass of the `SmartyLexer` that highlights unlexed data with the
    `XmlLexer`.
    """

    name = 'XML+Smarty'
    aliases = ['xml+smarty']
    version_added = ''
    alias_filenames = ['*.xml', '*.tpl']
    mimetypes = ['application/xml+smarty']
    url = 'https://www.smarty.net/'

    def __init__(self, **options):
        super().__init__(XmlLexer, SmartyLexer, **options)

    def analyse_text(text):
        rv = SmartyLexer.analyse_text(text) - 0.01
        if looks_like_xml(text):
            rv += 0.4
        return rv


class CssSmartyLexer(DelegatingLexer):
    """
    Subclass of the `SmartyLexer` that highlights unlexed data with the
    `CssLexer`.
    """

    name = 'CSS+Smarty'
    aliases = ['css+smarty']
    version_added = ''
    alias_filenames = ['*.css', '*.tpl']
    mimetypes = ['text/css+smarty']
    url = 'https://www.smarty.net/'

    def __init__(self, **options):
        super().__init__(CssLexer, SmartyLexer, **options)

    def analyse_text(text):
        return SmartyLexer.analyse_text(text) - 0.05


class JavascriptSmartyLexer(DelegatingLexer):
    """
    Subclass of the `SmartyLexer` that highlights unlexed data with the
    `JavascriptLexer`.
    """

    name = 'JavaScript+Smarty'
    aliases = ['javascript+smarty', 'js+smarty']
    version_added = ''
    alias_filenames = ['*.js', '*.tpl']
    mimetypes = ['application/x-javascript+smarty',
                 'text/x-javascript+smarty',
                 'text/javascript+smarty']
    url = 'https://www.smarty.net/'

    def __init__(self, **options):
        super().__init__(JavascriptLexer, SmartyLexer, **options)

    def analyse_text(text):
        return SmartyLexer.analyse_text(text) - 0.05


class HtmlDjangoLexer(DelegatingLexer):
    """
    Subclass of the `DjangoLexer` that highlights unlexed data with the
    `HtmlLexer`.

    Nested Javascript and CSS is highlighted too.
    """

    name = 'HTML+Django/Jinja'
    aliases = ['html+django', 'html+jinja', 'htmldjango']
    filenames = ['*.html.j2', '*.htm.j2', '*.xhtml.j2', '*.html.jinja2', '*.htm.jinja2', '*.xhtml.jinja2']
    version_added = ''
    alias_filenames = ['*.html', '*.htm', '*.xhtml']
    mimetypes = ['text/html+django', 'text/html+jinja']
    url = 'https://www.djangoproject.com/documentation/templates'

    def __init__(self, **options):
        super().__init__(HtmlLexer, DjangoLexer, **options)

    def analyse_text(text):
        rv = DjangoLexer.analyse_text(text) - 0.01
        if html_doctype_matches(text):
            rv += 0.5
        return rv


class XmlDjangoLexer(DelegatingLexer):
    """
    Subclass of the `DjangoLexer` that highlights unlexed data with the
    `XmlLexer`.
    """

    name = 'XML+Django/Jinja'
    aliases = ['xml+django', 'xml+jinja']
    filenames = ['*.xml.j2', '*.xml.jinja2']
    version_added = ''
    alias_filenames = ['*.xml']
    mimetypes = ['application/xml+django', 'application/xml+jinja']
    url = 'https://www.djangoproject.com/documentation/templates'

    def __init__(self, **options):
        super().__init__(XmlLexer, DjangoLexer, **options)

    def analyse_text(text):
        rv = DjangoLexer.analyse_text(text) - 0.01
        if looks_like_xml(text):
            rv += 0.4
        return rv


class CssDjangoLexer(DelegatingLexer):
    """
    Subclass of the `DjangoLexer` that highlights unlexed data with the
    `CssLexer`.
    """

    name = 'CSS+Django/Jinja'
    aliases = ['css+django', 'css+jinja']
    filenames = ['*.css.j2', '*.css.jinja2']
    version_added = ''
    alias_filenames = ['*.css']
    mimetypes = ['text/css+django', 'text/css+jinja']
    url = 'https://www.djangoproject.com/documentation/templates'

    def __init__(self, **options):
        super().__init__(CssLexer, DjangoLexer, **options)

    def analyse_text(text):
        return DjangoLexer.analyse_text(text) - 0.05


class JavascriptDjangoLexer(DelegatingLexer):
    """
    Subclass of the `DjangoLexer` that highlights unlexed data with the
    `JavascriptLexer`.
    """

    name = 'JavaScript+Django/Jinja'
    aliases = ['javascript+django', 'js+django',
               'javascript+jinja', 'js+jinja']
    filenames = ['*.js.j2', '*.js.jinja2']
    version_added = ''
    alias_filenames = ['*.js']
    mimetypes = ['application/x-javascript+django',
                 'application/x-javascript+jinja',
                 'text/x-javascript+django',
                 'text/x-javascript+jinja',
                 'text/javascript+django',
                 'text/javascript+jinja']
    url = 'https://www.djangoproject.com/documentation/templates'

    def __init__(self, **options):
        super().__init__(JavascriptLexer, DjangoLexer, **options)

    def analyse_text(text):
        return DjangoLexer.analyse_text(text) - 0.05


class JspRootLexer(RegexLexer):
    """
    Base for the `JspLexer`. Yields `Token.Other` for area outside of
    JSP tags.

    .. versionadded:: 0.7
    """

    tokens = {
        'root': [
            (r'<%\S?', Keyword, 'sec'),
            # FIXME: I want to make these keywords but still parse attributes.
            (r'</?jsp:(forward|getProperty|include|plugin|setProperty|useBean).*?>',
             Keyword),
            (r'[^<]+', Other),
            (r'<', Other),
        ],
        'sec': [
            (r'%>', Keyword, '#pop'),
            # note: '\w\W' != '.' without DOTALL.
            (r'[\w\W]+?(?=%>|\Z)', using(JavaLexer)),
        ],
    }


class JspLexer(DelegatingLexer):
    """
    Lexer for Java Server Pages.
    """
    name = 'Java Server Page'
    aliases = ['jsp']
    filenames = ['*.jsp']
    mimetypes = ['application/x-jsp']
    url = 'https://projects.eclipse.org/projects/ee4j.jsp'
    version_added = '0.7'

    def __init__(self, **options):
        super().__init__(XmlLexer, JspRootLexer, **options)

    def analyse_text(text):
        rv = JavaLexer.analyse_text(text) - 0.01
        if looks_like_xml(text):
            rv += 0.4
        if '<%' in text and '%>' in text:
            rv += 0.1
        return rv


class EvoqueLexer(RegexLexer):
    """
    For files using the Evoque templating system.
    """
    name = 'Evoque'
    aliases = ['evoque']
    filenames = ['*.evoque']
    mimetypes = ['application/x-evoque']
    url = 'https://gizmojo.org/templating'
    version_added = '1.1'

    flags = re.DOTALL

    tokens = {
        'root': [
            (r'[^#$]+', Other),
            (r'#\[', Comment.Multiline, 'comment'),
            (r'\$\$', Other),
            # svn keywords
            (r'\$\w+:[^$\n]*\$', Comment.Multiline),
            # directives: begin, end
            (r'(\$)(begin|end)(\{(%)?)(.*?)((?(4)%)\})',
             bygroups(Punctuation, Name.Builtin, Punctuation, None,
                      String, Punctuation)),
            # directives: evoque, overlay
            # see doc for handling first name arg: /directives/evoque/
            # + minor inconsistency: the "name" in e.g. $overlay{name=site_base}
            # should be using(PythonLexer), not passed out as String
            (r'(\$)(evoque|overlay)(\{(%)?)(\s*[#\w\-"\'.]+)?'
             r'(.*?)((?(4)%)\})',
             bygroups(Punctuation, Name.Builtin, Punctuation, None,
                      String, using(PythonLexer), Punctuation)),
            # directives: if, for, prefer, test
            (r'(\$)(\w+)(\{(%)?)(.*?)((?(4)%)\})',
             bygroups(Punctuation, Name.Builtin, Punctuation, None,
                      using(PythonLexer), Punctuation)),
            # directive clauses (no {} expression)
            (r'(\$)(else|rof|fi)', bygroups(Punctuation, Name.Builtin)),
            # expressions
            (r'(\$\{(%)?)(.*?)((!)(.*?))?((?(2)%)\})',
             bygroups(Punctuation, None, using(PythonLexer),
                      Name.Builtin, None, None, Punctuation)),
            (r'#', Other),
        ],
        'comment': [
            (r'[^\]#]', Comment.Multiline),
            (r'#\[', Comment.Multiline, '#push'),
            (r'\]#', Comment.Multiline, '#pop'),
            (r'[\]#]', Comment.Multiline)
        ],
    }

    def analyse_text(text):
        """Evoque templates use $evoque, which is unique."""
        if '$evoque' in text:
            return 1

class EvoqueHtmlLexer(DelegatingLexer):
    """
    Subclass of the `EvoqueLexer` that highlights unlexed data with the
    `HtmlLexer`.
    """
    name = 'HTML+Evoque'
    aliases = ['html+evoque']
    alias_filenames = ['*.html']
    mimetypes = ['text/html+evoque']
    url = 'https://gizmojo.org/templating'
    version_added = '1.1'

    def __init__(self, **options):
        super().__init__(HtmlLexer, EvoqueLexer, **options)

    def analyse_text(text):
        return EvoqueLexer.analyse_text(text)


class EvoqueXmlLexer(DelegatingLexer):
    """
    Subclass of the `EvoqueLexer` that highlights unlexed data with the
    `XmlLexer`.
    """
    name = 'XML+Evoque'
    aliases = ['xml+evoque']
    alias_filenames = ['*.xml']
    mimetypes = ['application/xml+evoque']
    url = 'https://gizmojo.org/templating'
    version_added = '1.1'

    def __init__(self, **options):
        super().__init__(XmlLexer, EvoqueLexer, **options)

    def analyse_text(text):
        return EvoqueLexer.analyse_text(text)


class ColdfusionLexer(RegexLexer):
    """
    Coldfusion statements
    """
    name = 'cfstatement'
    aliases = ['cfs']
    filenames = []
    mimetypes = []
    url = 'https://www.adobe.com/products/coldfusion-family.html'
    version_added = ''

    flags = re.IGNORECASE

    tokens = {
        'root': [
            (r'//.*?\n', Comment.Single),
            (r'/\*(?:.|\n)*?\*/', Comment.Multiline),
            (r'\+\+|--', Operator),
            (r'[-+*/^&=!]', Operator),
            (r'<=|>=|<|>|==', Operator),
            (r'mod\b', Operator),
            (r'(eq|lt|gt|lte|gte|not|is|and|or)\b', Operator),
            (r'\|\||&&', Operator),
            (r'\?', Operator),
            (r'"', String.Double, 'string'),
            # There is a special rule for allowing html in single quoted
            # strings, evidently.
            (r"'.*?'", String.Single),
            (r'\d+', Number),
            (r'(if|else|len|var|xml|default|break|switch|component|property|function|do|'
             r'try|catch|in|continue|for|return|while|required|any|array|binary|boolean|'
             r'component|date|guid|numeric|query|string|struct|uuid|case)\b', Keyword),
            (r'(true|false|null)\b', Keyword.Constant),
            (r'(application|session|client|cookie|super|this|variables|arguments)\b',
             Name.Constant),
            (r'([a-z_$][\w.]*)(\s*)(\()',
             bygroups(Name.Function, Text, Punctuation)),
            (r'[a-z_$][\w.]*', Name.Variable),
            (r'[()\[\]{};:,.\\]', Punctuation),
            (r'\s+', Text),
        ],
        'string': [
            (r'""', String.Double),
            (r'#.+?#', String.Interp),
            (r'[^"#]+', String.Double),
            (r'#', String.Double),
            (r'"', String.Double, '#pop'),
        ],
    }


class ColdfusionMarkupLexer(RegexLexer):
    """
    Coldfusion markup only
    """
    name = 'Coldfusion'
    aliases = ['cf']
    filenames = []
    mimetypes = []
    url = 'https://www.adobe.com/products/coldfusion-family.html'

    tokens = {
        'root': [
            (r'[^<]+', Other),
            include('tags'),
            (r'<[^<>]*', Other),
        ],
        'tags': [
            (r'<!---', Comment.Multiline, 'cfcomment'),
            (r'(?s)<!--.*?-->', Comment),
            (r'<cfoutput.*?>', Name.Builtin, 'cfoutput'),
            (r'(?s)(<cfscript.*?>)(.+?)(</cfscript.*?>)',
             bygroups(Name.Builtin, using(ColdfusionLexer), Name.Builtin)),
            # negative lookbehind is for strings with embedded >
            (r'(?s)(</?cf(?:component|include|if|else|elseif|loop|return|'
             r'dbinfo|dump|abort|location|invoke|throw|file|savecontent|'
             r'mailpart|mail|header|content|zip|image|lock|argument|try|'
             r'catch|break|directory|http|set|function|param)\b)(.*?)((?<!\\)>)',
             bygroups(Name.Builtin, using(ColdfusionLexer), Name.Builtin)),
        ],
        'cfoutput': [
            (r'[^#<]+', Other),
            (r'(#)(.*?)(#)', bygroups(Punctuation, using(ColdfusionLexer),
                                      Punctuation)),
            # (r'<cfoutput.*?>', Name.Builtin, '#push'),
            (r'</cfoutput.*?>', Name.Builtin, '#pop'),
            include('tags'),
            (r'(?s)<[^<>]*', Other),
            (r'#', Other),
        ],
        'cfcomment': [
            (r'<!---', Comment.Multiline, '#push'),
            (r'--->', Comment.Multiline, '#pop'),
            (r'([^<-]|<(?!!---)|-(?!-->))+', Comment.Multiline),
        ],
    }


class ColdfusionHtmlLexer(DelegatingLexer):
    """
    Coldfusion markup in html
    """
    name = 'Coldfusion HTML'
    aliases = ['cfm']
    filenames = ['*.cfm', '*.cfml']
    mimetypes = ['application/x-coldfusion']
    url = 'https://www.adobe.com/products/coldfusion-family.html'
    version_added = ''

    def __init__(self, **options):
        super().__init__(HtmlLexer, ColdfusionMarkupLexer, **options)


class ColdfusionCFCLexer(DelegatingLexer):
    """
    Coldfusion markup/script components
    """
    name = 'Coldfusion CFC'
    aliases = ['cfc']
    filenames = ['*.cfc']
    mimetypes = []
    url = 'https://www.adobe.com/products/coldfusion-family.html'
    version_added = '2.0'

    def __init__(self, **options):
        super().__init__(ColdfusionHtmlLexer, ColdfusionLexer, **options)


class SspLexer(DelegatingLexer):
    """
    Lexer for Scalate Server Pages.
    """
    name = 'Scalate Server Page'
    aliases = ['ssp']
    filenames = ['*.ssp']
    mimetypes = ['application/x-ssp']
    url = 'https://scalate.github.io/scalate/'
    version_added = '1.4'

    def __init__(self, **options):
        super().__init__(XmlLexer, JspRootLexer, **options)

    def analyse_text(text):
        rv = 0.0
        if re.search(r'val \w+\s*:', text):
            rv += 0.6
        if looks_like_xml(text):
            rv += 0.2
        if '<%' in text and '%>' in text:
            rv += 0.1
        return rv


class TeaTemplateRootLexer(RegexLexer):
    """
    Base for the `TeaTemplateLexer`. Yields `Token.Other` for area outside of
    code blocks.

    .. versionadded:: 1.5
    """

    tokens = {
        'root': [
            (r'<%\S?', Keyword, 'sec'),
            (r'[^<]+', Other),
            (r'<', Other),
        ],
        'sec': [
            (r'%>', Keyword, '#pop'),
            # note: '\w\W' != '.' without DOTALL.
            (r'[\w\W]+?(?=%>|\Z)', using(TeaLangLexer)),
        ],
    }


class TeaTemplateLexer(DelegatingLexer):
    """
    Lexer for Tea Templates.
    """
    name = 'Tea'
    aliases = ['tea']
    filenames = ['*.tea']
    mimetypes = ['text/x-tea']
    url = 'https://github.com/teatrove/teatrove'
    version_added = '1.5'

    def __init__(self, **options):
        super().__init__(XmlLexer, TeaTemplateRootLexer, **options)

    def analyse_text(text):
        rv = TeaLangLexer.analyse_text(text) - 0.01
        if looks_like_xml(text):
            rv += 0.4
        if '<%' in text and '%>' in text:
            rv += 0.1
        return rv


class LassoHtmlLexer(DelegatingLexer):
    """
    Subclass of the `LassoLexer` which highlights unhandled data with the
    `HtmlLexer`.

    Nested JavaScript and CSS is also highlighted.
    """

    name = 'HTML+Lasso'
    aliases = ['html+lasso']
    version_added = '1.6'
    alias_filenames = ['*.html', '*.htm', '*.xhtml', '*.lasso', '*.lasso[89]',
                       '*.incl', '*.inc', '*.las']
    mimetypes = ['text/html+lasso',
                 'application/x-httpd-lasso',
                 'application/x-httpd-lasso[89]']
    url = 'https://www.lassosoft.com'

    def __init__(self, **options):
        super().__init__(HtmlLexer, LassoLexer, **options)

    def analyse_text(text):
        rv = LassoLexer.analyse_text(text) - 0.01
        if html_doctype_matches(text):  # same as HTML lexer
            rv += 0.5
        return rv


class LassoXmlLexer(DelegatingLexer):
    """
    Subclass of the `LassoLexer` which highlights unhandled data with the
    `XmlLexer`.
    """

    name = 'XML+Lasso'
    aliases = ['xml+lasso']
    version_added = '1.6'
    alias_filenames = ['*.xml', '*.lasso', '*.lasso[89]',
                       '*.incl', '*.inc', '*.las']
    mimetypes = ['application/xml+lasso']
    url = 'https://www.lassosoft.com'

    def __init__(self, **options):
        super().__init__(XmlLexer, LassoLexer, **options)

    def analyse_text(text):
        rv = LassoLexer.analyse_text(text) - 0.01
        if looks_like_xml(text):
            rv += 0.4
        return rv


class LassoCssLexer(DelegatingLexer):
    """
    Subclass of the `LassoLexer` which highlights unhandled data with the
    `CssLexer`.
    """

    name = 'CSS+Lasso'
    aliases = ['css+lasso']
    version_added = '1.6'
    alias_filenames = ['*.css']
    mimetypes = ['text/css+lasso']
    url = 'https://www.lassosoft.com'

    def __init__(self, **options):
        options['requiredelimiters'] = True
        super().__init__(CssLexer, LassoLexer, **options)

    def analyse_text(text):
        rv = LassoLexer.analyse_text(text) - 0.05
        if re.search(r'\w+:[^;]+;', text):
            rv += 0.1
        if 'padding:' in text:
            rv += 0.1
        return rv


class LassoJavascriptLexer(DelegatingLexer):
    """
    Subclass of the `LassoLexer` which highlights unhandled data with the
    `JavascriptLexer`.
    """

    name = 'JavaScript+Lasso'
    aliases = ['javascript+lasso', 'js+lasso']
    version_added = '1.6'
    alias_filenames = ['*.js']
    mimetypes = ['application/x-javascript+lasso',
                 'text/x-javascript+lasso',
                 'text/javascript+lasso']
    url = 'https://www.lassosoft.com'

    def __init__(self, **options):
        options['requiredelimiters'] = True
        super().__init__(JavascriptLexer, LassoLexer, **options)

    def analyse_text(text):
        rv = LassoLexer.analyse_text(text) - 0.05
        return rv


class HandlebarsLexer(RegexLexer):
    """
    Generic handlebars template lexer.

    Highlights only the Handlebars template tags (stuff between `{{` and `}}`).
    Everything else is left for a delegating lexer.
    """

    name = "Handlebars"
    url = 'https://handlebarsjs.com/'
    aliases = ['handlebars']
    version_added = '2.0'

    tokens = {
        'root': [
            (r'[^{]+', Other),

            # Comment start {{!  }} or {{!--
            (r'\{\{!.*\}\}', Comment),

            # HTML Escaping open {{{expression
            (r'(\{\{\{)(\s*)', bygroups(Comment.Special, Text), 'tag'),

            # {{blockOpen {{#blockOpen {{/blockClose with optional tilde ~
            (r'(\{\{)([#~/]+)([^\s}]*)',
             bygroups(Comment.Preproc, Number.Attribute, Number.Attribute), 'tag'),
            (r'(\{\{)(\s*)', bygroups(Comment.Preproc, Text), 'tag'),
        ],

        'tag': [
            (r'\s+', Text),
            # HTML Escaping close }}}
            (r'\}\}\}', Comment.Special, '#pop'),
            # blockClose}}, includes optional tilde ~
            (r'(~?)(\}\})', bygroups(Number, Comment.Preproc), '#pop'),

            # {{opt=something}}
            (r'([^\s}]+)(=)', bygroups(Name.Attribute, Operator)),

            # Partials {{> ...}}
            (r'(>)(\s*)(@partial-block)', bygroups(Keyword, Text, Keyword)),
            (r'(#?>)(\s*)([\w-]+)', bygroups(Keyword, Text, Name.Variable)),
            (r'(>)(\s*)(\()', bygroups(Keyword, Text, Punctuation),
             'dynamic-partial'),

            include('generic'),
        ],
        'dynamic-partial': [
            (r'\s+', Text),
            (r'\)', Punctuation, '#pop'),

            (r'(lookup)(\s+)(\.|this)(\s+)', bygroups(Keyword, Text,
                                                      Name.Variable, Text)),
            (r'(lookup)(\s+)(\S+)', bygroups(Keyword, Text,
                                             using(this, state='variable'))),
            (r'[\w-]+', Name.Function),

            include('generic'),
        ],
        'variable': [
            (r'[()/@a-zA-Z][\w-]*', Name.Variable),
            (r'\.[\w-]+', Name.Variable),
            (r'(this\/|\.\/|(\.\.\/)+)[\w-]+', Name.Variable),
        ],
        'generic': [
            include('variable'),

            # borrowed from DjangoLexer
            (r':?"(\\\\|\\[^\\]|[^"\\])*"', String.Double),
            (r":?'(\\\\|\\[^\\]|[^'\\])*'", String.Single),
            (r"[0-9](\.[0-9]*)?(eE[+-][0-9])?[flFLdD]?|"
             r"0[xX][0-9a-fA-F]+[Ll]?", Number),
        ]
    }


class HandlebarsHtmlLexer(DelegatingLexer):
    """
    Subclass of the `HandlebarsLexer` that highlights unlexed data with the
    `HtmlLexer`.
    """

    name = "HTML+Handlebars"
    aliases = ["html+handlebars"]
    filenames = ['*.handlebars', '*.hbs']
    mimetypes = ['text/html+handlebars', 'text/x-handlebars-template']
    url = 'https://handlebarsjs.com/'
    version_added = '2.0'

    def __init__(self, **options):
        super().__init__(HtmlLexer, HandlebarsLexer, **options)


class YamlJinjaLexer(DelegatingLexer):
    """
    Subclass of the `DjangoLexer` that highlights unlexed data with the
    `YamlLexer`.

    Commonly used in Saltstack salt states.
    """

    name = 'YAML+Jinja'
    aliases = ['yaml+jinja', 'salt', 'sls']
    filenames = ['*.sls', '*.yaml.j2', '*.yml.j2', '*.yaml.jinja2', '*.yml.jinja2']
    mimetypes = ['text/x-yaml+jinja', 'text/x-sls']
    url = 'https://jinja.palletsprojects.com'
    version_added = '2.0'

    def __init__(self, **options):
        super().__init__(YamlLexer, DjangoLexer, **options)


class LiquidLexer(RegexLexer):
    """
    Lexer for Liquid templates.
    """
    name = 'liquid'
    url = 'https://www.rubydoc.info/github/Shopify/liquid'
    aliases = ['liquid']
    filenames = ['*.liquid']
    version_added = '2.0'

    tokens = {
        'root': [
            (r'[^{]+', Text),
            # tags and block tags
            (r'(\{%)(\s*)', bygroups(Punctuation, Whitespace), 'tag-or-block'),
            # output tags
            (r'(\{\{)(\s*)([^\s}]+)',
             bygroups(Punctuation, Whitespace, using(this, state = 'generic')),
             'output'),
            (r'\{', Text)
        ],

        'tag-or-block': [
            # builtin logic blocks
            (r'(if|unless|elsif|case)(?=\s+)', Keyword.Reserved, 'condition'),
            (r'(when)(\s+)', bygroups(Keyword.Reserved, Whitespace),
             combined('end-of-block', 'whitespace', 'generic')),
            (r'(else)(\s*)(%\})',
             bygroups(Keyword.Reserved, Whitespace, Punctuation), '#pop'),

            # other builtin blocks
            (r'(capture)(\s+)([^\s%]+)(\s*)(%\})',
             bygroups(Name.Tag, Whitespace, using(this, state = 'variable'),
                      Whitespace, Punctuation), '#pop'),
            (r'(comment)(\s*)(%\})',
             bygroups(Name.Tag, Whitespace, Punctuation), 'comment'),
            (r'(raw)(\s*)(%\})',
             bygroups(Name.Tag, Whitespace, Punctuation), 'raw'),

            # end of block
            (r'(end(case|unless|if))(\s*)(%\})',
             bygroups(Keyword.Reserved, None, Whitespace, Punctuation), '#pop'),
            (r'(end([^\s%]+))(\s*)(%\})',
             bygroups(Name.Tag, None, Whitespace, Punctuation), '#pop'),

            # builtin tags (assign and include are handled together with usual tags)
            (r'(cycle)(\s+)(?:([^\s:]*)(:))?(\s*)',
             bygroups(Name.Tag, Whitespace,
                      using(this, state='generic'), Punctuation, Whitespace),
             'variable-tag-markup'),

            # other tags or blocks
            (r'([^\s%]+)(\s*)', bygroups(Name.Tag, Whitespace), 'tag-markup')
        ],

        'output': [
            include('whitespace'),
            (r'\}\}', Punctuation, '#pop'),  # end of output

            (r'\|', Punctuation, 'filters')
        ],

        'filters': [
            include('whitespace'),
            (r'\}\}', Punctuation, ('#pop', '#pop')),  # end of filters and output

            (r'([^\s|:]+)(:?)(\s*)',
             bygroups(Name.Function, Punctuation, Whitespace), 'filter-markup')
        ],

        'filter-markup': [
            (r'\|', Punctuation, '#pop'),
            include('end-of-tag'),
            include('default-param-markup')
        ],

        'condition': [
            include('end-of-block'),
            include('whitespace'),

            (r'([^\s=!><]+)(\s*)([=!><]=?)(\s*)(\S+)(\s*)(%\})',
             bygroups(using(this, state = 'generic'), Whitespace, Operator,
                      Whitespace, using(this, state = 'generic'), Whitespace,
                      Punctuation)),
            (r'\b!', Operator),
            (r'\bnot\b', Operator.Word),
            (r'([\w.\'"]+)(\s+)(contains)(\s+)([\w.\'"]+)',
             bygroups(using(this, state = 'generic'), Whitespace, Operator.Word,
                      Whitespace, using(this, state = 'generic'))),

            include('generic'),
            include('whitespace')
        ],

        'generic-value': [
            include('generic'),
            include('end-at-whitespace')
        ],

        'operator': [
            (r'(\s*)((=|!|>|<)=?)(\s*)',
             bygroups(Whitespace, Operator, None, Whitespace), '#pop'),
            (r'(\s*)(\bcontains\b)(\s*)',
             bygroups(Whitespace, Operator.Word, Whitespace), '#pop'),
        ],

        'end-of-tag': [
            (r'\}\}', Punctuation, '#pop')
        ],

        'end-of-block': [
            (r'%\}', Punctuation, ('#pop', '#pop'))
        ],

        'end-at-whitespace': [
            (r'\s+', Whitespace, '#pop')
        ],

        # states for unknown markup
        'param-markup': [
            include('whitespace'),
            # params with colons or equals
            (r'([^\s=:]+)(\s*)(=|:)',
             bygroups(Name.Attribute, Whitespace, Operator)),
            # explicit variables
            (r'(\{\{)(\s*)([^\s}])(\s*)(\}\})',
             bygroups(Punctuation, Whitespace, using(this, state = 'variable'),
                      Whitespace, Punctuation)),

            include('string'),
            include('number'),
            include('keyword'),
            (r',', Punctuation)
        ],

        'default-param-markup': [
            include('param-markup'),
            (r'.', Text)  # fallback for switches / variables / un-quoted strings / ...
        ],

        'variable-param-markup': [
            include('param-markup'),
            include('variable'),
            (r'.', Text)  # fallback
        ],

        'tag-markup': [
            (r'%\}', Punctuation, ('#pop', '#pop')),  # end of tag
            include('default-param-markup')
        ],

        'variable-tag-markup': [
            (r'%\}', Punctuation, ('#pop', '#pop')),  # end of tag
            include('variable-param-markup')
        ],

        # states for different values types
        'keyword': [
            (r'\b(false|true)\b', Keyword.Constant)
        ],

        'variable': [
            (r'[a-zA-Z_]\w*', Name.Variable),
            (r'(?<=\w)\.(?=\w)', Punctuation)
        ],

        'string': [
            (r"'[^']*'", String.Single),
            (r'"[^"]*"', String.Double)
        ],

        'number': [
            (r'\d+\.\d+', Number.Float),
            (r'\d+', Number.Integer)
        ],

        'generic': [  # decides for variable, string, keyword or number
            include('keyword'),
            include('string'),
            include('number'),
            include('variable')
        ],

        'whitespace': [
            (r'[ \t]+', Whitespace)
        ],

        # states for builtin blocks
        'comment': [
            (r'(\{%)(\s*)(endcomment)(\s*)(%\})',
             bygroups(Punctuation, Whitespace, Name.Tag, Whitespace,
                      Punctuation), ('#pop', '#pop')),
            (r'.', Comment)
        ],

        'raw': [
            (r'[^{]+', Text),
            (r'(\{%)(\s*)(endraw)(\s*)(%\})',
             bygroups(Punctuation, Whitespace, Name.Tag, Whitespace,
                      Punctuation), '#pop'),
            (r'\{', Text)
        ],
    }


class TwigLexer(RegexLexer):
    """
    Twig template lexer.

    It just highlights Twig code between the preprocessor directives,
    other data is left untouched by the lexer.
    """

    name = 'Twig'
    aliases = ['twig']
    mimetypes = ['application/x-twig']
    url = 'https://twig.symfony.com'
    version_added = '2.0'

    flags = re.M | re.S

    # Note that a backslash is included in the following two patterns
    # PHP uses a backslash as a namespace separator
    _ident_char = r'[\\\w-]|[^\x00-\x7f]'
    _ident_begin = r'(?:[\\_a-z]|[^\x00-\x7f])'
    _ident_end = r'(?:' + _ident_char + ')*'
    _ident_inner = _ident_begin + _ident_end

    tokens = {
        'root': [
            (r'[^{]+', Other),
            (r'\{\{', Comment.Preproc, 'var'),
            # twig comments
            (r'\{\#.*?\#\}', Comment),
            # raw twig blocks
            (r'(\{%)(-?\s*)(raw)(\s*-?)(%\})(.*?)'
             r'(\{%)(-?\s*)(endraw)(\s*-?)(%\})',
             bygroups(Comment.Preproc, Text, Keyword, Text, Comment.Preproc,
                      Other, Comment.Preproc, Text, Keyword, Text,
                      Comment.Preproc)),
            (r'(\{%)(-?\s*)(verbatim)(\s*-?)(%\})(.*?)'
             r'(\{%)(-?\s*)(endverbatim)(\s*-?)(%\})',
             bygroups(Comment.Preproc, Text, Keyword, Text, Comment.Preproc,
                      Other, Comment.Preproc, Text, Keyword, Text,
                      Comment.Preproc)),
            # filter blocks
            (rf'(\{{%)(-?\s*)(filter)(\s+)({_ident_inner})',
             bygroups(Comment.Preproc, Text, Keyword, Text, Name.Function),
             'tag'),
            (r'(\{%)(-?\s*)([a-zA-Z_]\w*)',
             bygroups(Comment.Preproc, Text, Keyword), 'tag'),
            (r'\{', Other),
        ],
        'varnames': [
            (rf'(\|)(\s*)({_ident_inner})',
             bygroups(Operator, Text, Name.Function)),
            (rf'(is)(\s+)(not)?(\s*)({_ident_inner})',
             bygroups(Keyword, Text, Keyword, Text, Name.Function)),
            (r'(?i)(true|false|none|null)\b', Keyword.Pseudo),
            (r'(in|not|and|b-and|or|b-or|b-xor|is'
             r'if|elseif|else|import'
             r'constant|defined|divisibleby|empty|even|iterable|odd|sameas'
             r'matches|starts\s+with|ends\s+with)\b',
             Keyword),
            (r'(loop|block|parent)\b', Name.Builtin),
            (_ident_inner, Name.Variable),
            (r'\.' + _ident_inner, Name.Variable),
            (r'\.[0-9]+', Number),
            (r':?"(\\\\|\\[^\\]|[^"\\])*"', String.Double),
            (r":?'(\\\\|\\[^\\]|[^'\\])*'", String.Single),
            (r'([{}()\[\]+\-*/,:~%]|\.\.|\?|:|\*\*|\/\/|!=|[><=]=?)', Operator),
            (r"[0-9](\.[0-9]*)?(eE[+-][0-9])?[flFLdD]?|"
             r"0[xX][0-9a-fA-F]+[Ll]?", Number),
        ],
        'var': [
            (r'\s+', Text),
            (r'(-?)(\}\})', bygroups(Text, Comment.Preproc), '#pop'),
            include('varnames')
        ],
        'tag': [
            (r'\s+', Text),
            (r'(-?)(%\})', bygroups(Text, Comment.Preproc), '#pop'),
            include('varnames'),
            (r'.', Punctuation),
        ],
    }


class TwigHtmlLexer(DelegatingLexer):
    """
    Subclass of the `TwigLexer` that highlights unlexed data with the
    `HtmlLexer`.
    """

    name = "HTML+Twig"
    aliases = ["html+twig"]
    filenames = ['*.twig']
    mimetypes = ['text/html+twig']
    url = 'https://twig.symfony.com'
    version_added = '2.0'

    def __init__(self, **options):
        super().__init__(HtmlLexer, TwigLexer, **options)


class Angular2Lexer(RegexLexer):
    """
    Generic angular2 template lexer.

    Highlights only the Angular template tags (stuff between `{{` and `}}` and
    special attributes: '(event)=', '[property]=', '[(twoWayBinding)]=').
    Everything else is left for a delegating lexer.
    """

    name = "Angular2"
    url = 'https://angular.io/guide/template-syntax'
    aliases = ['ng2']
    version_added = '2.1'

    tokens = {
        'root': [
            (r'[^{([*#]+', Other),

            # {{meal.name}}
            (r'(\{\{)(\s*)', bygroups(Comment.Preproc, Text), 'ngExpression'),

            # (click)="deleteOrder()"; [value]="test"; [(twoWayTest)]="foo.bar"
            (r'([([]+)([\w:.-]+)([\])]+)(\s*)(=)(\s*)',
             bygroups(Punctuation, Name.Attribute, Punctuation, Text, Operator, Text),
             'attr'),
            (r'([([]+)([\w:.-]+)([\])]+)(\s*)',
             bygroups(Punctuation, Name.Attribute, Punctuation, Text)),

            # *ngIf="..."; #f="ngForm"
            (r'([*#])([\w:.-]+)(\s*)(=)(\s*)',
             bygroups(Punctuation, Name.Attribute, Text, Operator, Text), 'attr'),
            (r'([*#])([\w:.-]+)(\s*)',
             bygroups(Punctuation, Name.Attribute, Text)),
        ],

        'ngExpression': [
            (r'\s+(\|\s+)?', Text),
            (r'\}\}', Comment.Preproc, '#pop'),

            # Literals
            (r':?(true|false)', String.Boolean),
            (r':?"(\\\\|\\[^\\]|[^"\\])*"', String.Double),
            (r":?'(\\\\|\\[^\\]|[^'\\])*'", String.Single),
            (r"[0-9](\.[0-9]*)?(eE[+-][0-9])?[flFLdD]?|"
             r"0[xX][0-9a-fA-F]+[Ll]?", Number),

            # Variabletext
            (r'[a-zA-Z][\w-]*(\(.*\))?', Name.Variable),
            (r'\.[\w-]+(\(.*\))?', Name.Variable),

            # inline If
            (r'(\?)(\s*)([^}\s]+)(\s*)(:)(\s*)([^}\s]+)(\s*)',
             bygroups(Operator, Text, String, Text, Operator, Text, String, Text)),
        ],
        'attr': [
            ('".*?"', String, '#pop'),
            ("'.*?'", String, '#pop'),
            (r'[^\s>]+', String, '#pop'),
        ],
    }


class Angular2HtmlLexer(DelegatingLexer):
    """
    Subclass of the `Angular2Lexer` that highlights unlexed data with the
    `HtmlLexer`.
    """

    name = "HTML + Angular2"
    aliases = ["html+ng2"]
    filenames = ['*.ng2']
    url = 'https://angular.io/guide/template-syntax'
    version_added = '2.0'

    def __init__(self, **options):
        super().__init__(HtmlLexer, Angular2Lexer, **options)


class SqlJinjaLexer(DelegatingLexer):
    """
    Templated SQL lexer.
    """

    name = 'SQL+Jinja'
    aliases = ['sql+jinja']
    filenames = ['*.sql', '*.sql.j2', '*.sql.jinja2']
    url = 'https://jinja.palletsprojects.com'
    version_added = '2.13'

    def __init__(self, **options):
        super().__init__(SqlLexer, DjangoLexer, **options)

    def analyse_text(text):
        rv = 0.0
        # dbt's ref function
        if re.search(r'\{\{\s*ref\(.*\)\s*\}\}', text):
            rv += 0.4
        # dbt's source function
        if re.search(r'\{\{\s*source\(.*\)\s*\}\}', text):
            rv += 0.25
        # Jinja macro
        if re.search(r'\{%-?\s*macro \w+\(.*\)\s*-?%\}', text):
            rv += 0.15
        return rv

# === NexusCore/openenv\Lib\site-packages\grpc\__init__.py ===
# Copyright 2015-2016 gRPC authors.
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
"""gRPC's Python API."""

import abc
import contextlib
import enum
import logging
import sys

from grpc import _compression
from grpc._cython import cygrpc as _cygrpc
from grpc._runtime_protos import protos
from grpc._runtime_protos import protos_and_services
from grpc._runtime_protos import services

logging.getLogger(__name__).addHandler(logging.NullHandler())

try:
    # pylint: disable=ungrouped-imports
    from grpc._grpcio_metadata import __version__
except ImportError:
    __version__ = "dev0"

############################## Future Interface  ###############################


class FutureTimeoutError(Exception):
    """Indicates that a method call on a Future timed out."""


class FutureCancelledError(Exception):
    """Indicates that the computation underlying a Future was cancelled."""


class Future(abc.ABC):
    """A representation of a computation in another control flow.

    Computations represented by a Future may be yet to be begun,
    may be ongoing, or may have already completed.
    """

    @abc.abstractmethod
    def cancel(self):
        """Attempts to cancel the computation.

        This method does not block.

        Returns:
            bool:
            Returns True if the computation was canceled.

            Returns False under all other circumstances, for example:

            1. computation has begun and could not be canceled.
            2. computation has finished
            3. computation is scheduled for execution and it is impossible
                to determine its state without blocking.
        """
        raise NotImplementedError()

    @abc.abstractmethod
    def cancelled(self):
        """Describes whether the computation was cancelled.

        This method does not block.

        Returns:
            bool:
            Returns True if the computation was cancelled before its result became
            available.

            Returns False under all other circumstances, for example:

            1. computation was not cancelled.
            2. computation's result is available.
        """
        raise NotImplementedError()

    @abc.abstractmethod
    def running(self):
        """Describes whether the computation is taking place.

        This method does not block.

        Returns:
            Returns True if the computation is scheduled for execution or
            currently executing.

            Returns False if the computation already executed or was cancelled.
        """
        raise NotImplementedError()

    @abc.abstractmethod
    def done(self):
        """Describes whether the computation has taken place.

        This method does not block.

        Returns:
            bool:
            Returns True if the computation already executed or was cancelled.
            Returns False if the computation is scheduled for execution or
            currently executing.
            This is exactly opposite of the running() method's result.
        """
        raise NotImplementedError()

    @abc.abstractmethod
    def result(self, timeout=None):
        """Returns the result of the computation or raises its exception.

        This method may return immediately or may block.

        Args:
          timeout: The length of time in seconds to wait for the computation to
            finish or be cancelled. If None, the call will block until the
            computations's termination.

        Returns:
          The return value of the computation.

        Raises:
          FutureTimeoutError: If a timeout value is passed and the computation
            does not terminate within the allotted time.
          FutureCancelledError: If the computation was cancelled.
          Exception: If the computation raised an exception, this call will
            raise the same exception.
        """
        raise NotImplementedError()

    @abc.abstractmethod
    def exception(self, timeout=None):
        """Return the exception raised by the computation.

        This method may return immediately or may block.

        Args:
          timeout: The length of time in seconds to wait for the computation to
            terminate or be cancelled. If None, the call will block until the
            computations's termination.

        Returns:
            The exception raised by the computation, or None if the computation
            did not raise an exception.

        Raises:
          FutureTimeoutError: If a timeout value is passed and the computation
            does not terminate within the allotted time.
          FutureCancelledError: If the computation was cancelled.
        """
        raise NotImplementedError()

    @abc.abstractmethod
    def traceback(self, timeout=None):
        """Access the traceback of the exception raised by the computation.

        This method may return immediately or may block.

        Args:
          timeout: The length of time in seconds to wait for the computation
            to terminate or be cancelled. If None, the call will block until
            the computation's termination.

        Returns:
            The traceback of the exception raised by the computation, or None
            if the computation did not raise an exception.

        Raises:
          FutureTimeoutError: If a timeout value is passed and the computation
            does not terminate within the allotted time.
          FutureCancelledError: If the computation was cancelled.
        """
        raise NotImplementedError()

    @abc.abstractmethod
    def add_done_callback(self, fn):
        """Adds a function to be called at completion of the computation.

        The callback will be passed this Future object describing the outcome
        of the computation.  Callbacks will be invoked after the future is
        terminated, whether successfully or not.

        If the computation has already completed, the callback will be called
        immediately.

        Exceptions raised in the callback will be logged at ERROR level, but
        will not terminate any threads of execution.

        Args:
          fn: A callable taking this Future object as its single parameter.
        """
        raise NotImplementedError()


################################  gRPC Enums  ##################################


@enum.unique
class ChannelConnectivity(enum.Enum):
    """Mirrors grpc_connectivity_state in the gRPC Core.

    Attributes:
      IDLE: The channel is idle.
      CONNECTING: The channel is connecting.
      READY: The channel is ready to conduct RPCs.
      TRANSIENT_FAILURE: The channel has seen a failure from which it expects
        to recover.
      SHUTDOWN: The channel has seen a failure from which it cannot recover.
    """

    IDLE = (_cygrpc.ConnectivityState.idle, "idle")
    CONNECTING = (_cygrpc.ConnectivityState.connecting, "connecting")
    READY = (_cygrpc.ConnectivityState.ready, "ready")
    TRANSIENT_FAILURE = (
        _cygrpc.ConnectivityState.transient_failure,
        "transient failure",
    )
    SHUTDOWN = (_cygrpc.ConnectivityState.shutdown, "shutdown")


@enum.unique
class StatusCode(enum.Enum):
    """Mirrors grpc_status_code in the gRPC Core.

    Attributes:
      OK: Not an error; returned on success
      CANCELLED: The operation was cancelled (typically by the caller).
      UNKNOWN: Unknown error.
      INVALID_ARGUMENT: Client specified an invalid argument.
      DEADLINE_EXCEEDED: Deadline expired before operation could complete.
      NOT_FOUND: Some requested entity (e.g., file or directory) was not found.
      ALREADY_EXISTS: Some entity that we attempted to create (e.g., file or directory)
        already exists.
      PERMISSION_DENIED: The caller does not have permission to execute the specified
        operation.
      UNAUTHENTICATED: The request does not have valid authentication credentials for the
        operation.
      RESOURCE_EXHAUSTED: Some resource has been exhausted, perhaps a per-user quota, or
        perhaps the entire file system is out of space.
      FAILED_PRECONDITION: Operation was rejected because the system is not in a state
        required for the operation's execution.
      ABORTED: The operation was aborted, typically due to a concurrency issue
        like sequencer check failures, transaction aborts, etc.
      UNIMPLEMENTED: Operation is not implemented or not supported/enabled in this service.
      INTERNAL: Internal errors.  Means some invariants expected by underlying
        system has been broken.
      UNAVAILABLE: The service is currently unavailable.
      DATA_LOSS: Unrecoverable data loss or corruption.
    """

    OK = (_cygrpc.StatusCode.ok, "ok")
    CANCELLED = (_cygrpc.StatusCode.cancelled, "cancelled")
    UNKNOWN = (_cygrpc.StatusCode.unknown, "unknown")
    INVALID_ARGUMENT = (_cygrpc.StatusCode.invalid_argument, "invalid argument")
    DEADLINE_EXCEEDED = (
        _cygrpc.StatusCode.deadline_exceeded,
        "deadline exceeded",
    )
    NOT_FOUND = (_cygrpc.StatusCode.not_found, "not found")
    ALREADY_EXISTS = (_cygrpc.StatusCode.already_exists, "already exists")
    PERMISSION_DENIED = (
        _cygrpc.StatusCode.permission_denied,
        "permission denied",
    )
    RESOURCE_EXHAUSTED = (
        _cygrpc.StatusCode.resource_exhausted,
        "resource exhausted",
    )
    FAILED_PRECONDITION = (
        _cygrpc.StatusCode.failed_precondition,
        "failed precondition",
    )
    ABORTED = (_cygrpc.StatusCode.aborted, "aborted")
    OUT_OF_RANGE = (_cygrpc.StatusCode.out_of_range, "out of range")
    UNIMPLEMENTED = (_cygrpc.StatusCode.unimplemented, "unimplemented")
    INTERNAL = (_cygrpc.StatusCode.internal, "internal")
    UNAVAILABLE = (_cygrpc.StatusCode.unavailable, "unavailable")
    DATA_LOSS = (_cygrpc.StatusCode.data_loss, "data loss")
    UNAUTHENTICATED = (_cygrpc.StatusCode.unauthenticated, "unauthenticated")


#############################  gRPC Status  ################################


class Status(abc.ABC):
    """Describes the status of an RPC.

    This is an EXPERIMENTAL API.

    Attributes:
      code: A StatusCode object to be sent to the client.
      details: A UTF-8-encodable string to be sent to the client upon
        termination of the RPC.
      trailing_metadata: The trailing :term:`metadata` in the RPC.
    """


#############################  gRPC Exceptions  ################################


class RpcError(Exception):
    """Raised by the gRPC library to indicate non-OK-status RPC termination."""


##############################  Shared Context  ################################


class RpcContext(abc.ABC):
    """Provides RPC-related information and action."""

    @abc.abstractmethod
    def is_active(self):
        """Describes whether the RPC is active or has terminated.

        Returns:
          bool:
          True if RPC is active, False otherwise.
        """
        raise NotImplementedError()

    @abc.abstractmethod
    def time_remaining(self):
        """Describes the length of allowed time remaining for the RPC.

        Returns:
          A nonnegative float indicating the length of allowed time in seconds
          remaining for the RPC to complete before it is considered to have
          timed out, or None if no deadline was specified for the RPC.
        """
        raise NotImplementedError()

    @abc.abstractmethod
    def cancel(self):
        """Cancels the RPC.

        Idempotent and has no effect if the RPC has already terminated.
        """
        raise NotImplementedError()

    @abc.abstractmethod
    def add_callback(self, callback):
        """Registers a callback to be called on RPC termination.

        Args:
          callback: A no-parameter callable to be called on RPC termination.

        Returns:
          True if the callback was added and will be called later; False if
            the callback was not added and will not be called (because the RPC
            already terminated or some other reason).
        """
        raise NotImplementedError()


#########################  Invocation-Side Context  ############################


class Call(RpcContext, metaclass=abc.ABCMeta):
    """Invocation-side utility object for an RPC."""

    @abc.abstractmethod
    def initial_metadata(self):
        """Accesses the initial metadata sent by the server.

        This method blocks until the value is available.

        Returns:
          The initial :term:`metadata`.
        """
        raise NotImplementedError()

    @abc.abstractmethod
    def trailing_metadata(self):
        """Accesses the trailing metadata sent by the server.

        This method blocks until the value is available.

        Returns:
          The trailing :term:`metadata`.
        """
        raise NotImplementedError()

    @abc.abstractmethod
    def code(self):
        """Accesses the status code sent by the server.

        This method blocks until the value is available.

        Returns:
          The StatusCode value for the RPC.
        """
        raise NotImplementedError()

    @abc.abstractmethod
    def details(self):
        """Accesses the details sent by the server.

        This method blocks until the value is available.

        Returns:
          The details string of the RPC.
        """
        raise NotImplementedError()


##############  Invocation-Side Interceptor Interfaces & Classes  ##############


class ClientCallDetails(abc.ABC):
    """Describes an RPC to be invoked.

    Attributes:
      method: The method name of the RPC.
      timeout: An optional duration of time in seconds to allow for the RPC.
      metadata: Optional :term:`metadata` to be transmitted to
        the service-side of the RPC.
      credentials: An optional CallCredentials for the RPC.
      wait_for_ready: An optional flag to enable :term:`wait_for_ready` mechanism.
      compression: An element of grpc.compression, e.g.
        grpc.compression.Gzip.
    """


class UnaryUnaryClientInterceptor(abc.ABC):
    """Affords intercepting unary-unary invocations."""

    @abc.abstractmethod
    def intercept_unary_unary(self, continuation, client_call_details, request):
        """Intercepts a unary-unary invocation asynchronously.

        Args:
          continuation: A function that proceeds with the invocation by
            executing the next interceptor in chain or invoking the
            actual RPC on the underlying Channel. It is the interceptor's
            responsibility to call it if it decides to move the RPC forward.
            The interceptor can use
            `response_future = continuation(client_call_details, request)`
            to continue with the RPC. `continuation` returns an object that is
            both a Call for the RPC and a Future. In the event of RPC
            completion, the return Call-Future's result value will be
            the response message of the RPC. Should the event terminate
            with non-OK status, the returned Call-Future's exception value
            will be an RpcError.
          client_call_details: A ClientCallDetails object describing the
            outgoing RPC.
          request: The request value for the RPC.

        Returns:
            An object that is both a Call for the RPC and a Future.
            In the event of RPC completion, the return Call-Future's
            result value will be the response message of the RPC.
            Should the event terminate with non-OK status, the returned
            Call-Future's exception value will be an RpcError.
        """
        raise NotImplementedError()


class UnaryStreamClientInterceptor(abc.ABC):
    """Affords intercepting unary-stream invocations."""

    @abc.abstractmethod
    def intercept_unary_stream(
        self, continuation, client_call_details, request
    ):
        """Intercepts a unary-stream invocation.

        Args:
          continuation: A function that proceeds with the invocation by
            executing the next interceptor in chain or invoking the
            actual RPC on the underlying Channel. It is the interceptor's
            responsibility to call it if it decides to move the RPC forward.
            The interceptor can use
            `response_iterator = continuation(client_call_details, request)`
            to continue with the RPC. `continuation` returns an object that is
            both a Call for the RPC and an iterator for response values.
            Drawing response values from the returned Call-iterator may
            raise RpcError indicating termination of the RPC with non-OK
            status.
          client_call_details: A ClientCallDetails object describing the
            outgoing RPC.
          request: The request value for the RPC.

        Returns:
            An object that is both a Call for the RPC and an iterator of
            response values. Drawing response values from the returned
            Call-iterator may raise RpcError indicating termination of
            the RPC with non-OK status. This object *should* also fulfill the
            Future interface, though it may not.
        """
        raise NotImplementedError()


class StreamUnaryClientInterceptor(abc.ABC):
    """Affords intercepting stream-unary invocations."""

    @abc.abstractmethod
    def intercept_stream_unary(
        self, continuation, client_call_details, request_iterator
    ):
        """Intercepts a stream-unary invocation asynchronously.

        Args:
          continuation: A function that proceeds with the invocation by
            executing the next interceptor in chain or invoking the
            actual RPC on the underlying Channel. It is the interceptor's
            responsibility to call it if it decides to move the RPC forward.
            The interceptor can use
            `response_future = continuation(client_call_details, request_iterator)`
            to continue with the RPC. `continuation` returns an object that is
            both a Call for the RPC and a Future. In the event of RPC completion,
            the return Call-Future's result value will be the response message
            of the RPC. Should the event terminate with non-OK status, the
            returned Call-Future's exception value will be an RpcError.
          client_call_details: A ClientCallDetails object describing the
            outgoing RPC.
          request_iterator: An iterator that yields request values for the RPC.

        Returns:
          An object that is both a Call for the RPC and a Future.
          In the event of RPC completion, the return Call-Future's
          result value will be the response message of the RPC.
          Should the event terminate with non-OK status, the returned
          Call-Future's exception value will be an RpcError.
        """
        raise NotImplementedError()


class StreamStreamClientInterceptor(abc.ABC):
    """Affords intercepting stream-stream invocations."""

    @abc.abstractmethod
    def intercept_stream_stream(
        self, continuation, client_call_details, request_iterator
    ):
        """Intercepts a stream-stream invocation.

        Args:
          continuation: A function that proceeds with the invocation by
            executing the next interceptor in chain or invoking the
            actual RPC on the underlying Channel. It is the interceptor's
            responsibility to call it if it decides to move the RPC forward.
            The interceptor can use
            `response_iterator = continuation(client_call_details, request_iterator)`
            to continue with the RPC. `continuation` returns an object that is
            both a Call for the RPC and an iterator for response values.
            Drawing response values from the returned Call-iterator may
            raise RpcError indicating termination of the RPC with non-OK
            status.
          client_call_details: A ClientCallDetails object describing the
            outgoing RPC.
          request_iterator: An iterator that yields request values for the RPC.

        Returns:
          An object that is both a Call for the RPC and an iterator of
          response values. Drawing response values from the returned
          Call-iterator may raise RpcError indicating termination of
          the RPC with non-OK status. This object *should* also fulfill the
          Future interface, though it may not.
        """
        raise NotImplementedError()


############  Authentication & Authorization Interfaces & Classes  #############


class ChannelCredentials(object):
    """An encapsulation of the data required to create a secure Channel.

    This class has no supported interface - it exists to define the type of its
    instances and its instances exist to be passed to other functions. For
    example, ssl_channel_credentials returns an instance of this class and
    secure_channel requires an instance of this class.
    """

    def __init__(self, credentials):
        self._credentials = credentials


class CallCredentials(object):
    """An encapsulation of the data required to assert an identity over a call.

    A CallCredentials has to be used with secure Channel, otherwise the
    metadata will not be transmitted to the server.

    A CallCredentials may be composed with ChannelCredentials to always assert
    identity for every call over that Channel.

    This class has no supported interface - it exists to define the type of its
    instances and its instances exist to be passed to other functions.
    """

    def __init__(self, credentials):
        self._credentials = credentials


class AuthMetadataContext(abc.ABC):
    """Provides information to call credentials metadata plugins.

    Attributes:
      service_url: A string URL of the service being called into.
      method_name: A string of the fully qualified method name being called.
    """


class AuthMetadataPluginCallback(abc.ABC):
    """Callback object received by a metadata plugin."""

    def __call__(self, metadata, error):
        """Passes to the gRPC runtime authentication metadata for an RPC.

        Args:
          metadata: The :term:`metadata` used to construct the CallCredentials.
          error: An Exception to indicate error or None to indicate success.
        """
        raise NotImplementedError()


class AuthMetadataPlugin(abc.ABC):
    """A specification for custom authentication."""

    def __call__(self, context, callback):
        """Implements authentication by passing metadata to a callback.

        This method will be invoked asynchronously in a separate thread.

        Args:
          context: An AuthMetadataContext providing information on the RPC that
            the plugin is being called to authenticate.
          callback: An AuthMetadataPluginCallback to be invoked either
            synchronously or asynchronously.
        """
        raise NotImplementedError()


class ServerCredentials(object):
    """An encapsulation of the data required to open a secure port on a Server.

    This class has no supported interface - it exists to define the type of its
    instances and its instances exist to be passed to other functions.
    """

    def __init__(self, credentials):
        self._credentials = credentials


class ServerCertificateConfiguration(object):
    """A certificate configuration for use with an SSL-enabled Server.

    Instances of this class can be returned in the certificate configuration
    fetching callback.

    This class has no supported interface -- it exists to define the
    type of its instances and its instances exist to be passed to
    other functions.
    """

    def __init__(self, certificate_configuration):
        self._certificate_configuration = certificate_configuration


########################  Multi-Callable Interfaces  ###########################


class UnaryUnaryMultiCallable(abc.ABC):
    """Affords invoking a unary-unary RPC from client-side."""

    @abc.abstractmethod
    def __call__(
        self,
        request,
        timeout=None,
        metadata=None,
        credentials=None,
        wait_for_ready=None,
        compression=None,
    ):
        """Synchronously invokes the underlying RPC.

        Args:
          request: The request value for the RPC.
          timeout: An optional duration of time in seconds to allow
            for the RPC.
          metadata: Optional :term:`metadata` to be transmitted to the
            service-side of the RPC.
          credentials: An optional CallCredentials for the RPC. Only valid for
            secure Channel.
          wait_for_ready: An optional flag to enable :term:`wait_for_ready` mechanism.
          compression: An element of grpc.compression, e.g.
            grpc.compression.Gzip.

        Returns:
          The response value for the RPC.

        Raises:
          RpcError: Indicating that the RPC terminated with non-OK status. The
            raised RpcError will also be a Call for the RPC affording the RPC's
            metadata, status code, and details.
        """
        raise NotImplementedError()

    @abc.abstractmethod
    def with_call(
        self,
        request,
        timeout=None,
        metadata=None,
        credentials=None,
        wait_for_ready=None,
        compression=None,
    ):
        """Synchronously invokes the underlying RPC.

        Args:
          request: The request value for the RPC.
          timeout: An optional durating of time in seconds to allow for
            the RPC.
          metadata: Optional :term:`metadata` to be transmitted to the
            service-side of the RPC.
          credentials: An optional CallCredentials for the RPC. Only valid for
            secure Channel.
          wait_for_ready: An optional flag to enable :term:`wait_for_ready` mechanism.
          compression: An element of grpc.compression, e.g.
            grpc.compression.Gzip.

        Returns:
          The response value for the RPC and a Call value for the RPC.

        Raises:
          RpcError: Indicating that the RPC terminated with non-OK status. The
            raised RpcError will also be a Call for the RPC affording the RPC's
            metadata, status code, and details.
        """
        raise NotImplementedError()

    @abc.abstractmethod
    def future(
        self,
        request,
        timeout=None,
        metadata=None,
        credentials=None,
        wait_for_ready=None,
        compression=None,
    ):
        """Asynchronously invokes the underlying RPC.

        Args:
          request: The request value for the RPC.
          timeout: An optional duration of time in seconds to allow for
            the RPC.
          metadata: Optional :term:`metadata` to be transmitted to the
            service-side of the RPC.
          credentials: An optional CallCredentials for the RPC. Only valid for
            secure Channel.
          wait_for_ready: An optional flag to enable :term:`wait_for_ready` mechanism.
          compression: An element of grpc.compression, e.g.
            grpc.compression.Gzip.

        Returns:
            An object that is both a Call for the RPC and a Future.
            In the event of RPC completion, the return Call-Future's result
            value will be the response message of the RPC.
            Should the event terminate with non-OK status,
            the returned Call-Future's exception value will be an RpcError.
        """
        raise NotImplementedError()


class UnaryStreamMultiCallable(abc.ABC):
    """Affords invoking a unary-stream RPC from client-side."""

    @abc.abstractmethod
    def __call__(
        self,
        request,
        timeout=None,
        metadata=None,
        credentials=None,
        wait_for_ready=None,
        compression=None,
    ):
        """Invokes the underlying RPC.

        Args:
          request: The request value for the RPC.
          timeout: An optional duration of time in seconds to allow for
            the RPC. If None, the timeout is considered infinite.
          metadata: An optional :term:`metadata` to be transmitted to the
            service-side of the RPC.
          credentials: An optional CallCredentials for the RPC. Only valid for
            secure Channel.
          wait_for_ready: An optional flag to enable :term:`wait_for_ready` mechanism.
          compression: An element of grpc.compression, e.g.
            grpc.compression.Gzip.

        Returns:
            An object that is a Call for the RPC, an iterator of response
            values, and a Future for the RPC. Drawing response values from the
            returned Call-iterator may raise RpcError indicating termination of
            the RPC with non-OK status.
        """
        raise NotImplementedError()


class StreamUnaryMultiCallable(abc.ABC):
    """Affords invoking a stream-unary RPC from client-side."""

    @abc.abstractmethod
    def __call__(
        self,
        request_iterator,
        timeout=None,
        metadata=None,
        credentials=None,
        wait_for_ready=None,
        compression=None,
    ):
        """Synchronously invokes the underlying RPC.

        Args:
          request_iterator: An iterator that yields request values for
            the RPC.
          timeout: An optional duration of time in seconds to allow for
            the RPC. If None, the timeout is considered infinite.
          metadata: Optional :term:`metadata` to be transmitted to the
            service-side of the RPC.
          credentials: An optional CallCredentials for the RPC. Only valid for
            secure Channel.
          wait_for_ready: An optional flag to enable :term:`wait_for_ready` mechanism.
          compression: An element of grpc.compression, e.g.
            grpc.compression.Gzip.

        Returns:
          The response value for the RPC.

        Raises:
          RpcError: Indicating that the RPC terminated with non-OK status. The
            raised RpcError will also implement grpc.Call, affording methods
            such as metadata, code, and details.
        """
        raise NotImplementedError()

    @abc.abstractmethod
    def with_call(
        self,
        request_iterator,
        timeout=None,
        metadata=None,
        credentials=None,
        wait_for_ready=None,
        compression=None,
    ):
        """Synchronously invokes the underlying RPC on the client.

        Args:
          request_iterator: An iterator that yields request values for
            the RPC.
          timeout: An optional duration of time in seconds to allow for
            the RPC. If None, the timeout is considered infinite.
          metadata: Optional :term:`metadata` to be transmitted to the
            service-side of the RPC.
          credentials: An optional CallCredentials for the RPC. Only valid for
            secure Channel.
          wait_for_ready: An optional flag to enable :term:`wait_for_ready` mechanism.
          compression: An element of grpc.compression, e.g.
            grpc.compression.Gzip.

        Returns:
          The response value for the RPC and a Call object for the RPC.

        Raises:
          RpcError: Indicating that the RPC terminated with non-OK status. The
            raised RpcError will also be a Call for the RPC affording the RPC's
            metadata, status code, and details.
        """
        raise NotImplementedError()

    @abc.abstractmethod
    def future(
        self,
        request_iterator,
        timeout=None,
        metadata=None,
        credentials=None,
        wait_for_ready=None,
        compression=None,
    ):
        """Asynchronously invokes the underlying RPC on the client.

        Args:
          request_iterator: An iterator that yields request values for the RPC.
          timeout: An optional duration of time in seconds to allow for
            the RPC. If None, the timeout is considered infinite.
          metadata: Optional :term:`metadata` to be transmitted to the
            service-side of the RPC.
          credentials: An optional CallCredentials for the RPC. Only valid for
            secure Channel.
          wait_for_ready: An optional flag to enable :term:`wait_for_ready` mechanism.
          compression: An element of grpc.compression, e.g.
            grpc.compression.Gzip.

        Returns:
            An object that is both a Call for the RPC and a Future.
            In the event of RPC completion, the return Call-Future's result value
            will be the response message of the RPC. Should the event terminate
            with non-OK status, the returned Call-Future's exception value will
            be an RpcError.
        """
        raise NotImplementedError()


class StreamStreamMultiCallable(abc.ABC):
    """Affords invoking a stream-stream RPC on client-side."""

    @abc.abstractmethod
    def __call__(
        self,
        request_iterator,
        timeout=None,
        metadata=None,
        credentials=None,
        wait_for_ready=None,
        compression=None,
    ):
        """Invokes the underlying RPC on the client.

        Args:
          request_iterator: An iterator that yields request values for the RPC.
          timeout: An optional duration of time in seconds to allow for
            the RPC. If not specified, the timeout is considered infinite.
          metadata: Optional :term:`metadata` to be transmitted to the
            service-side of the RPC.
          credentials: An optional CallCredentials for the RPC. Only valid for
            secure Channel.
          wait_for_ready: An optional flag to enable :term:`wait_for_ready` mechanism.
          compression: An element of grpc.compression, e.g.
            grpc.compression.Gzip.

        Returns:
            An object that is a Call for the RPC, an iterator of response
            values, and a Future for the RPC. Drawing response values from the
            returned Call-iterator may raise RpcError indicating termination of
            the RPC with non-OK status.
        """
        raise NotImplementedError()


#############################  Channel Interface  ##############################


class Channel(abc.ABC):
    """Affords RPC invocation via generic methods on client-side.

    Channel objects implement the Context Manager type, although they need not
    support being entered and exited multiple times.
    """

    @abc.abstractmethod
    def subscribe(self, callback, try_to_connect=False):
        """Subscribe to this Channel's connectivity state machine.

        A Channel may be in any of the states described by ChannelConnectivity.
        This method allows application to monitor the state transitions.
        The typical use case is to debug or gain better visibility into gRPC
        runtime's state.

        Args:
          callback: A callable to be invoked with ChannelConnectivity argument.
            ChannelConnectivity describes current state of the channel.
            The callable will be invoked immediately upon subscription
            and again for every change to ChannelConnectivity until it
            is unsubscribed or this Channel object goes out of scope.
          try_to_connect: A boolean indicating whether or not this Channel
            should attempt to connect immediately. If set to False, gRPC
            runtime decides when to connect.
        """
        raise NotImplementedError()

    @abc.abstractmethod
    def unsubscribe(self, callback):
        """Unsubscribes a subscribed callback from this Channel's connectivity.

        Args:
          callback: A callable previously registered with this Channel from
          having been passed to its "subscribe" method.
        """
        raise NotImplementedError()

    @abc.abstractmethod
    def unary_unary(
        self,
        method,
        request_serializer=None,
        response_deserializer=None,
        _registered_method=False,
    ):
        """Creates a UnaryUnaryMultiCallable for a unary-unary method.

        Args:
          method: The name of the RPC method.
          request_serializer: Optional :term:`serializer` for serializing the request
            message. Request goes unserialized in case None is passed.
          response_deserializer: Optional :term:`deserializer` for deserializing the
            response message. Response goes undeserialized in case None
            is passed.
          _registered_method: Implementation Private. A bool representing whether the method
            is registered.

        Returns:
          A UnaryUnaryMultiCallable value for the named unary-unary method.
        """
        raise NotImplementedError()

    @abc.abstractmethod
    def unary_stream(
        self,
        method,
        request_serializer=None,
        response_deserializer=None,
        _registered_method=False,
    ):
        """Creates a UnaryStreamMultiCallable for a unary-stream method.

        Args:
          method: The name of the RPC method.
          request_serializer: Optional :term:`serializer` for serializing the request
            message. Request goes unserialized in case None is passed.
          response_deserializer: Optional :term:`deserializer` for deserializing the
            response message. Response goes undeserialized in case None is
            passed.
          _registered_method: Implementation Private. A bool representing whether the method
            is registered.

        Returns:
          A UnaryStreamMultiCallable value for the name unary-stream method.
        """
        raise NotImplementedError()

    @abc.abstractmethod
    def stream_unary(
        self,
        method,
        request_serializer=None,
        response_deserializer=None,
        _registered_method=False,
    ):
        """Creates a StreamUnaryMultiCallable for a stream-unary method.

        Args:
          method: The name of the RPC method.
          request_serializer: Optional :term:`serializer` for serializing the request
            message. Request goes unserialized in case None is passed.
          response_deserializer: Optional :term:`deserializer` for deserializing the
            response message. Response goes undeserialized in case None is
            passed.
          _registered_method: Implementation Private. A bool representing whether the method
            is registered.

        Returns:
          A StreamUnaryMultiCallable value for the named stream-unary method.
        """
        raise NotImplementedError()

    @abc.abstractmethod
    def stream_stream(
        self,
        method,
        request_serializer=None,
        response_deserializer=None,
        _registered_method=False,
    ):
        """Creates a StreamStreamMultiCallable for a stream-stream method.

        Args:
          method: The name of the RPC method.
          request_serializer: Optional :term:`serializer` for serializing the request
            message. Request goes unserialized in case None is passed.
          response_deserializer: Optional :term:`deserializer` for deserializing the
            response message. Response goes undeserialized in case None
            is passed.
          _registered_method: Implementation Private. A bool representing whether the method
            is registered.

        Returns:
          A StreamStreamMultiCallable value for the named stream-stream method.
        """
        raise NotImplementedError()

    @abc.abstractmethod
    def close(self):
        """Closes this Channel and releases all resources held by it.

        Closing the Channel will immediately terminate all RPCs active with the
        Channel and it is not valid to invoke new RPCs with the Channel.

        This method is idempotent.
        """
        raise NotImplementedError()

    def __enter__(self):
        """Enters the runtime context related to the channel object."""
        raise NotImplementedError()

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exits the runtime context related to the channel object."""
        raise NotImplementedError()


##########################  Service-Side Context  ##############################


class ServicerContext(RpcContext, metaclass=abc.ABCMeta):
    """A context object passed to method implementations."""

    @abc.abstractmethod
    def invocation_metadata(self):
        """Accesses the metadata sent by the client.

        Returns:
          The invocation :term:`metadata`.
        """
        raise NotImplementedError()

    @abc.abstractmethod
    def peer(self):
        """Identifies the peer that invoked the RPC being serviced.

        Returns:
          A string identifying the peer that invoked the RPC being serviced.
          The string format is determined by gRPC runtime.
        """
        raise NotImplementedError()

    @abc.abstractmethod
    def peer_identities(self):
        """Gets one or more peer identity(s).

        Equivalent to
        servicer_context.auth_context().get(servicer_context.peer_identity_key())

        Returns:
          An iterable of the identities, or None if the call is not
          authenticated. Each identity is returned as a raw bytes type.
        """
        raise NotImplementedError()

    @abc.abstractmethod
    def peer_identity_key(self):
        """The auth property used to identify the peer.

        For example, "x509_common_name" or "x509_subject_alternative_name" are
        used to identify an SSL peer.

        Returns:
          The auth property (string) that indicates the
          peer identity, or None if the call is not authenticated.
        """
        raise NotImplementedError()

    @abc.abstractmethod
    def auth_context(self):
        """Gets the auth context for the call.

        Returns:
          A map of strings to an iterable of bytes for each auth property.
        """
        raise NotImplementedError()

    def set_compression(self, compression):
        """Set the compression algorithm to be used for the entire call.

        Args:
          compression: An element of grpc.compression, e.g.
            grpc.compression.Gzip.
        """
        raise NotImplementedError()

    @abc.abstractmethod
    def send_initial_metadata(self, initial_metadata):
        """Sends the initial metadata value to the client.

        This method need not be called by implementations if they have no
        metadata to add to what the gRPC runtime will transmit.

        Args:
          initial_metadata: The initial :term:`metadata`.
        """
        raise NotImplementedError()

    @abc.abstractmethod
    def set_trailing_metadata(self, trailing_metadata):
        """Sets the trailing metadata for the RPC.

        Sets the trailing metadata to be sent upon completion of the RPC.

        If this method is invoked multiple times throughout the lifetime of an
        RPC, the value supplied in the final invocation will be the value sent
        over the wire.

        This method need not be called by implementations if they have no
        metadata to add to what the gRPC runtime will transmit.

        Args:
          trailing_metadata: The trailing :term:`metadata`.
        """
        raise NotImplementedError()

    def trailing_metadata(self):
        """Access value to be used as trailing metadata upon RPC completion.

        This is an EXPERIMENTAL API.

        Returns:
          The trailing :term:`metadata` for the RPC.
        """
        raise NotImplementedError()

    @abc.abstractmethod
    def abort(self, code, details):
        """Raises an exception to terminate the RPC with a non-OK status.

        The code and details passed as arguments will supersede any existing
        ones.

        Args:
          code: A StatusCode object to be sent to the client.
            It must not be StatusCode.OK.
          details: A UTF-8-encodable string to be sent to the client upon
            termination of the RPC.

        Raises:
          Exception: An exception is always raised to signal the abortion the
            RPC to the gRPC runtime.
        """
        raise NotImplementedError()

    @abc.abstractmethod
    def abort_with_status(self, status):
        """Raises an exception to terminate the RPC with a non-OK status.

        The status passed as argument will supersede any existing status code,
        status message and trailing metadata.

        This is an EXPERIMENTAL API.

        Args:
          status: A grpc.Status object. The status code in it must not be
            StatusCode.OK.

        Raises:
          Exception: An exception is always raised to signal the abortion the
            RPC to the gRPC runtime.
        """
        raise NotImplementedError()

    @abc.abstractmethod
    def set_code(self, code):
        """Sets the value to be used as status code upon RPC completion.

        This method need not be called by method implementations if they wish
        the gRPC runtime to determine the status code of the RPC.

        Args:
          code: A StatusCode object to be sent to the client.
        """
        raise NotImplementedError()

    @abc.abstractmethod
    def set_details(self, details):
        """Sets the value to be used as detail string upon RPC completion.

        This method need not be called by method implementations if they have
        no details to transmit.

        Args:
          details: A UTF-8-encodable string to be sent to the client upon
            termination of the RPC.
        """
        raise NotImplementedError()

    def code(self):
        """Accesses the value to be used as status code upon RPC completion.

        This is an EXPERIMENTAL API.

        Returns:
          The StatusCode value for the RPC.
        """
        raise NotImplementedError()

    def details(self):
        """Accesses the value to be used as detail string upon RPC completion.

        This is an EXPERIMENTAL API.

        Returns:
          The details string of the RPC.
        """
        raise NotImplementedError()

    def disable_next_message_compression(self):
        """Disables compression for the next response message.

        This method will override any compression configuration set during
        server creation or set on the call.
        """
        raise NotImplementedError()


#####################  Service-Side Handler Interfaces  ########################


class RpcMethodHandler(abc.ABC):
    """An implementation of a single RPC method.

    Attributes:
      request_streaming: Whether the RPC supports exactly one request message
        or any arbitrary number of request messages.
      response_streaming: Whether the RPC supports exactly one response message
        or any arbitrary number of response messages.
      request_deserializer: A callable :term:`deserializer` that accepts a byte string and
        returns an object suitable to be passed to this object's business
        logic, or None to indicate that this object's business logic should be
        passed the raw request bytes.
      response_serializer: A callable :term:`serializer` that accepts an object produced
        by this object's business logic and returns a byte string, or None to
        indicate that the byte strings produced by this object's business logic
        should be transmitted on the wire as they are.
      unary_unary: This object's application-specific business logic as a
        callable value that takes a request value and a ServicerContext object
        and returns a response value. Only non-None if both request_streaming
        and response_streaming are False.
      unary_stream: This object's application-specific business logic as a
        callable value that takes a request value and a ServicerContext object
        and returns an iterator of response values. Only non-None if
        request_streaming is False and response_streaming is True.
      stream_unary: This object's application-specific business logic as a
        callable value that takes an iterator of request values and a
        ServicerContext object and returns a response value. Only non-None if
        request_streaming is True and response_streaming is False.
      stream_stream: This object's application-specific business logic as a
        callable value that takes an iterator of request values and a
        ServicerContext object and returns an iterator of response values.
        Only non-None if request_streaming and response_streaming are both
        True.
    """


class HandlerCallDetails(abc.ABC):
    """Describes an RPC that has just arrived for service.

    Attributes:
      method: The method name of the RPC.
      invocation_metadata: The :term:`metadata` sent by the client.
    """


class GenericRpcHandler(abc.ABC):
    """An implementation of arbitrarily many RPC methods."""

    @abc.abstractmethod
    def service(self, handler_call_details):
        """Returns the handler for servicing the RPC.

        Args:
          handler_call_details: A HandlerCallDetails describing the RPC.

        Returns:
          An RpcMethodHandler with which the RPC may be serviced if the
          implementation chooses to service this RPC, or None otherwise.
        """
        raise NotImplementedError()


class ServiceRpcHandler(GenericRpcHandler, metaclass=abc.ABCMeta):
    """An implementation of RPC methods belonging to a service.

    A service handles RPC methods with structured names of the form
    '/Service.Name/Service.Method', where 'Service.Name' is the value
    returned by service_name(), and 'Service.Method' is the method
    name.  A service can have multiple method names, but only a single
    service name.
    """

    @abc.abstractmethod
    def service_name(self):
        """Returns this service's name.

        Returns:
          The service name.
        """
        raise NotImplementedError()


####################  Service-Side Interceptor Interfaces  #####################


class ServerInterceptor(abc.ABC):
    """Affords intercepting incoming RPCs on the service-side."""

    @abc.abstractmethod
    def intercept_service(self, continuation, handler_call_details):
        """Intercepts incoming RPCs before handing them over to a handler.

        State can be passed from an interceptor to downstream interceptors
        via contextvars. The first interceptor is called from an empty
        contextvars.Context, and the same Context is used for downstream
        interceptors and for the final handler call. Note that there are no
        guarantees that interceptors and handlers will be called from the
        same thread.

        Args:
          continuation: A function that takes a HandlerCallDetails and
            proceeds to invoke the next interceptor in the chain, if any,
            or the RPC handler lookup logic, with the call details passed
            as an argument, and returns an RpcMethodHandler instance if
            the RPC is considered serviced, or None otherwise.
          handler_call_details: A HandlerCallDetails describing the RPC.

        Returns:
          An RpcMethodHandler with which the RPC may be serviced if the
          interceptor chooses to service this RPC, or None otherwise.
        """
        raise NotImplementedError()


#############################  Server Interface  ###############################


class Server(abc.ABC):
    """Services RPCs."""

    @abc.abstractmethod
    def add_generic_rpc_handlers(self, generic_rpc_handlers):
        """Registers GenericRpcHandlers with this Server.

        This method is only safe to call before the server is started.

        Args:
          generic_rpc_handlers: An iterable of GenericRpcHandlers that will be
          used to service RPCs.
        """
        raise NotImplementedError()

    def add_registered_method_handlers(self, service_name, method_handlers):
        """Registers GenericRpcHandlers with this Server.

        This method is only safe to call before the server is started.

        If the same method have both generic and registered handler,
        registered handler will take precedence.

        Args:
          service_name: The service name.
          method_handlers: A dictionary that maps method names to corresponding
            RpcMethodHandler.
        """

    @abc.abstractmethod
    def add_insecure_port(self, address):
        """Opens an insecure port for accepting RPCs.

        This method may only be called before starting the server.

        Args:
          address: The address for which to open a port. If the port is 0,
            or not specified in the address, then gRPC runtime will choose a port.

        Returns:
          An integer port on which server will accept RPC requests.
        """
        raise NotImplementedError()

    @abc.abstractmethod
    def add_secure_port(self, address, server_credentials):
        """Opens a secure port for accepting RPCs.

        This method may only be called before starting the server.

        Args:
          address: The address for which to open a port.
            if the port is 0, or not specified in the address, then gRPC
            runtime will choose a port.
          server_credentials: A ServerCredentials object.

        Returns:
          An integer port on which server will accept RPC requests.
        """
        raise NotImplementedError()

    @abc.abstractmethod
    def start(self):
        """Starts this Server.

        This method may only be called once. (i.e. it is not idempotent).
        """
        raise NotImplementedError()

    @abc.abstractmethod
    def stop(self, grace):
        """Stops this Server.

        This method immediately stop service of new RPCs in all cases.

        If a grace period is specified, this method waits until all active
        RPCs are finished or until the grace period is reached. RPCs that haven't
        been terminated within the grace period are aborted.
        If a grace period is not specified (by passing None for `grace`),
        all existing RPCs are aborted immediately and this method
        blocks until the last RPC handler terminates.

        This method is idempotent and may be called at any time.
        Passing a smaller grace value in a subsequent call will have
        the effect of stopping the Server sooner (passing None will
        have the effect of stopping the server immediately). Passing
        a larger grace value in a subsequent call *will not* have the
        effect of stopping the server later (i.e. the most restrictive
        grace value is used).

        Args:
          grace: A duration of time in seconds or None.

        Returns:
          A threading.Event that will be set when this Server has completely
          stopped, i.e. when running RPCs either complete or are aborted and
          all handlers have terminated.
        """
        raise NotImplementedError()

    def wait_for_termination(self, timeout=None):
        """Block current thread until the server stops.

        This is an EXPERIMENTAL API.

        The wait will not consume computational resources during blocking, and
        it will block until one of the two following conditions are met:

        1) The server is stopped or terminated;
        2) A timeout occurs if timeout is not `None`.

        The timeout argument works in the same way as `threading.Event.wait()`.
        https://docs.python.org/3/library/threading.html#threading.Event.wait

        Args:
          timeout: A floating point number specifying a timeout for the
            operation in seconds.

        Returns:
          A bool indicates if the operation times out.
        """
        raise NotImplementedError()


#################################  Functions    ################################


def unary_unary_rpc_method_handler(
    behavior, request_deserializer=None, response_serializer=None
):
    """Creates an RpcMethodHandler for a unary-unary RPC method.

    Args:
      behavior: The implementation of an RPC that accepts one request
        and returns one response.
      request_deserializer: An optional :term:`deserializer` for request deserialization.
      response_serializer: An optional :term:`serializer` for response serialization.

    Returns:
      An RpcMethodHandler object that is typically used by grpc.Server.
    """
    from grpc import _utilities  # pylint: disable=cyclic-import

    return _utilities.RpcMethodHandler(
        False,
        False,
        request_deserializer,
        response_serializer,
        behavior,
        None,
        None,
        None,
    )


def unary_stream_rpc_method_handler(
    behavior, request_deserializer=None, response_serializer=None
):
    """Creates an RpcMethodHandler for a unary-stream RPC method.

    Args:
      behavior: The implementation of an RPC that accepts one request
        and returns an iterator of response values.
      request_deserializer: An optional :term:`deserializer` for request deserialization.
      response_serializer: An optional :term:`serializer` for response serialization.

    Returns:
      An RpcMethodHandler object that is typically used by grpc.Server.
    """
    from grpc import _utilities  # pylint: disable=cyclic-import

    return _utilities.RpcMethodHandler(
        False,
        True,
        request_deserializer,
        response_serializer,
        None,
        behavior,
        None,
        None,
    )


def stream_unary_rpc_method_handler(
    behavior, request_deserializer=None, response_serializer=None
):
    """Creates an RpcMethodHandler for a stream-unary RPC method.

    Args:
      behavior: The implementation of an RPC that accepts an iterator of
        request values and returns a single response value.
      request_deserializer: An optional :term:`deserializer` for request deserialization.
      response_serializer: An optional :term:`serializer` for response serialization.

    Returns:
      An RpcMethodHandler object that is typically used by grpc.Server.
    """
    from grpc import _utilities  # pylint: disable=cyclic-import

    return _utilities.RpcMethodHandler(
        True,
        False,
        request_deserializer,
        response_serializer,
        None,
        None,
        behavior,
        None,
    )


def stream_stream_rpc_method_handler(
    behavior, request_deserializer=None, response_serializer=None
):
    """Creates an RpcMethodHandler for a stream-stream RPC method.

    Args:
      behavior: The implementation of an RPC that accepts an iterator of
        request values and returns an iterator of response values.
      request_deserializer: An optional :term:`deserializer` for request deserialization.
      response_serializer: An optional :term:`serializer` for response serialization.

    Returns:
      An RpcMethodHandler object that is typically used by grpc.Server.
    """
    from grpc import _utilities  # pylint: disable=cyclic-import

    return _utilities.RpcMethodHandler(
        True,
        True,
        request_deserializer,
        response_serializer,
        None,
        None,
        None,
        behavior,
    )


def method_handlers_generic_handler(service, method_handlers):
    """Creates a GenericRpcHandler from RpcMethodHandlers.

    Args:
      service: The name of the service that is implemented by the
        method_handlers.
      method_handlers: A dictionary that maps method names to corresponding
        RpcMethodHandler.

    Returns:
      A GenericRpcHandler. This is typically added to the grpc.Server object
      with add_generic_rpc_handlers() before starting the server.
    """
    from grpc import _utilities  # pylint: disable=cyclic-import

    return _utilities.DictionaryGenericHandler(service, method_handlers)


def ssl_channel_credentials(
    root_certificates=None, private_key=None, certificate_chain=None
):
    """Creates a ChannelCredentials for use with an SSL-enabled Channel.

    Args:
      root_certificates: The PEM-encoded root certificates as a byte string,
        or None to retrieve them from a default location chosen by gRPC
        runtime.
      private_key: The PEM-encoded private key as a byte string, or None if no
        private key should be used.
      certificate_chain: The PEM-encoded certificate chain as a byte string
        to use or None if no certificate chain should be used.

    Returns:
      A ChannelCredentials for use with an SSL-enabled Channel.
    """
    return ChannelCredentials(
        _cygrpc.SSLChannelCredentials(
            root_certificates, private_key, certificate_chain
        )
    )


def xds_channel_credentials(fallback_credentials=None):
    """Creates a ChannelCredentials for use with xDS. This is an EXPERIMENTAL
      API.

    Args:
      fallback_credentials: Credentials to use in case it is not possible to
        establish a secure connection via xDS. If no fallback_credentials
        argument is supplied, a default SSLChannelCredentials is used.
    """
    fallback_credentials = (
        ssl_channel_credentials()
        if fallback_credentials is None
        else fallback_credentials
    )
    return ChannelCredentials(
        _cygrpc.XDSChannelCredentials(fallback_credentials._credentials)
    )


def metadata_call_credentials(metadata_plugin, name=None):
    """Construct CallCredentials from an AuthMetadataPlugin.

    Args:
      metadata_plugin: An AuthMetadataPlugin to use for authentication.
      name: An optional name for the plugin.

    Returns:
      A CallCredentials.
    """
    from grpc import _plugin_wrapping  # pylint: disable=cyclic-import

    return _plugin_wrapping.metadata_plugin_call_credentials(
        metadata_plugin, name
    )


def access_token_call_credentials(access_token):
    """Construct CallCredentials from an access token.

    Args:
      access_token: A string to place directly in the http request
        authorization header, for example
        "authorization: Bearer <access_token>".

    Returns:
      A CallCredentials.
    """
    from grpc import _auth  # pylint: disable=cyclic-import
    from grpc import _plugin_wrapping  # pylint: disable=cyclic-import

    return _plugin_wrapping.metadata_plugin_call_credentials(
        _auth.AccessTokenAuthMetadataPlugin(access_token), None
    )


def composite_call_credentials(*call_credentials):
    """Compose multiple CallCredentials to make a new CallCredentials.

    Args:
      *call_credentials: At least two CallCredentials objects.

    Returns:
      A CallCredentials object composed of the given CallCredentials objects.
    """
    return CallCredentials(
        _cygrpc.CompositeCallCredentials(
            tuple(
                single_call_credentials._credentials
                for single_call_credentials in call_credentials
            )
        )
    )


def composite_channel_credentials(channel_credentials, *call_credentials):
    """Compose a ChannelCredentials and one or more CallCredentials objects.

    Args:
      channel_credentials: A ChannelCredentials object.
      *call_credentials: One or more CallCredentials objects.

    Returns:
      A ChannelCredentials composed of the given ChannelCredentials and
        CallCredentials objects.
    """
    return ChannelCredentials(
        _cygrpc.CompositeChannelCredentials(
            tuple(
                single_call_credentials._credentials
                for single_call_credentials in call_credentials
            ),
            channel_credentials._credentials,
        )
    )


def ssl_server_credentials(
    private_key_certificate_chain_pairs,
    root_certificates=None,
    require_client_auth=False,
):
    """Creates a ServerCredentials for use with an SSL-enabled Server.

    Args:
      private_key_certificate_chain_pairs: A list of pairs of the form
        [PEM-encoded private key, PEM-encoded certificate chain].
      root_certificates: An optional byte string of PEM-encoded client root
        certificates that the server will use to verify client authentication.
        If omitted, require_client_auth must also be False.
      require_client_auth: A boolean indicating whether or not to require
        clients to be authenticated. May only be True if root_certificates
        is not None.

    Returns:
      A ServerCredentials for use with an SSL-enabled Server. Typically, this
      object is an argument to add_secure_port() method during server setup.
    """
    if not private_key_certificate_chain_pairs:
        raise ValueError(
            "At least one private key-certificate chain pair is required!"
        )
    elif require_client_auth and root_certificates is None:
        raise ValueError(
            "Illegal to require client auth without providing root"
            " certificates!"
        )
    else:
        return ServerCredentials(
            _cygrpc.server_credentials_ssl(
                root_certificates,
                [
                    _cygrpc.SslPemKeyCertPair(key, pem)
                    for key, pem in private_key_certificate_chain_pairs
                ],
                require_client_auth,
            )
        )


def xds_server_credentials(fallback_credentials):
    """Creates a ServerCredentials for use with xDS. This is an EXPERIMENTAL
      API.

    Args:
      fallback_credentials: Credentials to use in case it is not possible to
        establish a secure connection via xDS. No default value is provided.
    """
    return ServerCredentials(
        _cygrpc.xds_server_credentials(fallback_credentials._credentials)
    )


def insecure_server_credentials():
    """Creates a credentials object directing the server to use no credentials.
      This is an EXPERIMENTAL API.

    This object cannot be used directly in a call to `add_secure_port`.
    Instead, it should be used to construct other credentials objects, e.g.
    with xds_server_credentials.
    """
    return ServerCredentials(_cygrpc.insecure_server_credentials())


def ssl_server_certificate_configuration(
    private_key_certificate_chain_pairs, root_certificates=None
):
    """Creates a ServerCertificateConfiguration for use with a Server.

    Args:
      private_key_certificate_chain_pairs: A collection of pairs of
        the form [PEM-encoded private key, PEM-encoded certificate
        chain].
      root_certificates: An optional byte string of PEM-encoded client root
        certificates that the server will use to verify client authentication.

    Returns:
      A ServerCertificateConfiguration that can be returned in the certificate
        configuration fetching callback.
    """
    if private_key_certificate_chain_pairs:
        return ServerCertificateConfiguration(
            _cygrpc.server_certificate_config_ssl(
                root_certificates,
                [
                    _cygrpc.SslPemKeyCertPair(key, pem)
                    for key, pem in private_key_certificate_chain_pairs
                ],
            )
        )
    else:
        raise ValueError(
            "At least one private key-certificate chain pair is required!"
        )


def dynamic_ssl_server_credentials(
    initial_certificate_configuration,
    certificate_configuration_fetcher,
    require_client_authentication=False,
):
    """Creates a ServerCredentials for use with an SSL-enabled Server.

    Args:
      initial_certificate_configuration (ServerCertificateConfiguration): The
        certificate configuration with which the server will be initialized.
      certificate_configuration_fetcher (callable): A callable that takes no
        arguments and should return a ServerCertificateConfiguration to
        replace the server's current certificate, or None for no change
        (i.e., the server will continue its current certificate
        config). The library will call this callback on *every* new
        client connection before starting the TLS handshake with the
        client, thus allowing the user application to optionally
        return a new ServerCertificateConfiguration that the server will then
        use for the handshake.
      require_client_authentication: A boolean indicating whether or not to
        require clients to be authenticated.

    Returns:
      A ServerCredentials.
    """
    return ServerCredentials(
        _cygrpc.server_credentials_ssl_dynamic_cert_config(
            initial_certificate_configuration,
            certificate_configuration_fetcher,
            require_client_authentication,
        )
    )


@enum.unique
class LocalConnectionType(enum.Enum):
    """Types of local connection for local credential creation.

    Attributes:
      UDS: Unix domain socket connections
      LOCAL_TCP: Local TCP connections.
    """

    UDS = _cygrpc.LocalConnectionType.uds
    LOCAL_TCP = _cygrpc.LocalConnectionType.local_tcp


def local_channel_credentials(local_connect_type=LocalConnectionType.LOCAL_TCP):
    """Creates a local ChannelCredentials used for local connections.

    This is an EXPERIMENTAL API.

    Local credentials are used by local TCP endpoints (e.g. localhost:10000)
    also UDS connections.

    The connections created by local channel credentials are not
    encrypted, but will be checked if they are local or not.
    The UDS connections are considered secure by providing peer authentication
    and data confidentiality while TCP connections are considered insecure.

    It is allowed to transmit call credentials over connections created by
    local channel credentials.

    Local channel credentials are useful for 1) eliminating insecure_channel usage;
    2) enable unit testing for call credentials without setting up secrets.

    Args:
      local_connect_type: Local connection type (either
        grpc.LocalConnectionType.UDS or grpc.LocalConnectionType.LOCAL_TCP)

    Returns:
      A ChannelCredentials for use with a local Channel
    """
    return ChannelCredentials(
        _cygrpc.channel_credentials_local(local_connect_type.value)
    )


def local_server_credentials(local_connect_type=LocalConnectionType.LOCAL_TCP):
    """Creates a local ServerCredentials used for local connections.

    This is an EXPERIMENTAL API.

    Local credentials are used by local TCP endpoints (e.g. localhost:10000)
    also UDS connections.

    The connections created by local server credentials are not
    encrypted, but will be checked if they are local or not.
    The UDS connections are considered secure by providing peer authentication
    and data confidentiality while TCP connections are considered insecure.

    It is allowed to transmit call credentials over connections created by local
    server credentials.

    Local server credentials are useful for 1) eliminating insecure_channel usage;
    2) enable unit testing for call credentials without setting up secrets.

    Args:
      local_connect_type: Local connection type (either
        grpc.LocalConnectionType.UDS or grpc.LocalConnectionType.LOCAL_TCP)

    Returns:
      A ServerCredentials for use with a local Server
    """
    return ServerCredentials(
        _cygrpc.server_credentials_local(local_connect_type.value)
    )


def alts_channel_credentials(service_accounts=None):
    """Creates a ChannelCredentials for use with an ALTS-enabled Channel.

    This is an EXPERIMENTAL API.
    ALTS credentials API can only be used in GCP environment as it relies on
    handshaker service being available. For more info about ALTS see
    https://cloud.google.com/security/encryption-in-transit/application-layer-transport-security

    Args:
      service_accounts: A list of server identities accepted by the client.
        If target service accounts are provided and none of them matches the
        peer identity of the server, handshake will fail. The arg can be empty
        if the client does not have any information about trusted server
        identity.
    Returns:
      A ChannelCredentials for use with an ALTS-enabled Channel
    """
    return ChannelCredentials(
        _cygrpc.channel_credentials_alts(service_accounts or [])
    )


def alts_server_credentials():
    """Creates a ServerCredentials for use with an ALTS-enabled connection.

    This is an EXPERIMENTAL API.
    ALTS credentials API can only be used in GCP environment as it relies on
    handshaker service being available. For more info about ALTS see
    https://cloud.google.com/security/encryption-in-transit/application-layer-transport-security

    Returns:
      A ServerCredentials for use with an ALTS-enabled Server
    """
    return ServerCredentials(_cygrpc.server_credentials_alts())


def compute_engine_channel_credentials(call_credentials):
    """Creates a compute engine channel credential.

    This credential can only be used in a GCP environment as it relies on
    a handshaker service. For more info about ALTS, see
    https://cloud.google.com/security/encryption-in-transit/application-layer-transport-security

    This channel credential is expected to be used as part of a composite
    credential in conjunction with a call credentials that authenticates the
    VM's default service account. If used with any other sort of call
    credential, the connection may suddenly and unexpectedly begin failing RPCs.
    """
    return ChannelCredentials(
        _cygrpc.channel_credentials_compute_engine(
            call_credentials._credentials
        )
    )


def channel_ready_future(channel):
    """Creates a Future that tracks when a Channel is ready.

    Cancelling the Future does not affect the channel's state machine.
    It merely decouples the Future from channel state machine.

    Args:
      channel: A Channel object.

    Returns:
      A Future object that matures when the channel connectivity is
      ChannelConnectivity.READY.
    """
    from grpc import _utilities  # pylint: disable=cyclic-import

    return _utilities.channel_ready_future(channel)


def insecure_channel(target, options=None, compression=None):
    """Creates an insecure Channel to a server.

    The returned Channel is thread-safe.

    Args:
      target: The server address
      options: An optional list of key-value pairs (:term:`channel_arguments`
        in gRPC Core runtime) to configure the channel.
      compression: An optional value indicating the compression method to be
        used over the lifetime of the channel.

    Returns:
      A Channel.
    """
    from grpc import _channel  # pylint: disable=cyclic-import

    return _channel.Channel(
        target, () if options is None else options, None, compression
    )


def secure_channel(target, credentials, options=None, compression=None):
    """Creates a secure Channel to a server.

    The returned Channel is thread-safe.

    Args:
      target: The server address.
      credentials: A ChannelCredentials instance.
      options: An optional list of key-value pairs (:term:`channel_arguments`
        in gRPC Core runtime) to configure the channel.
      compression: An optional value indicating the compression method to be
        used over the lifetime of the channel.

    Returns:
      A Channel.
    """
    from grpc import _channel  # pylint: disable=cyclic-import
    from grpc.experimental import _insecure_channel_credentials

    if credentials._credentials is _insecure_channel_credentials:
        raise ValueError(
            "secure_channel cannot be called with insecure credentials."
            + " Call insecure_channel instead."
        )
    return _channel.Channel(
        target,
        () if options is None else options,
        credentials._credentials,
        compression,
    )


def intercept_channel(channel, *interceptors):
    """Intercepts a channel through a set of interceptors.

    Args:
      channel: A Channel.
      interceptors: Zero or more objects of type
        UnaryUnaryClientInterceptor,
        UnaryStreamClientInterceptor,
        StreamUnaryClientInterceptor, or
        StreamStreamClientInterceptor.
        Interceptors are given control in the order they are listed.

    Returns:
      A Channel that intercepts each invocation via the provided interceptors.

    Raises:
      TypeError: If interceptor does not derive from any of
        UnaryUnaryClientInterceptor,
        UnaryStreamClientInterceptor,
        StreamUnaryClientInterceptor, or
        StreamStreamClientInterceptor.
    """
    from grpc import _interceptor  # pylint: disable=cyclic-import

    return _interceptor.intercept_channel(channel, *interceptors)


def server(
    thread_pool,
    handlers=None,
    interceptors=None,
    options=None,
    maximum_concurrent_rpcs=None,
    compression=None,
    xds=False,
):
    """Creates a Server with which RPCs can be serviced.

    Args:
      thread_pool: A futures.ThreadPoolExecutor to be used by the Server
        to execute RPC handlers.
      handlers: An optional list of GenericRpcHandlers used for executing RPCs.
        More handlers may be added by calling add_generic_rpc_handlers any time
        before the server is started.
      interceptors: An optional list of ServerInterceptor objects that observe
        and optionally manipulate the incoming RPCs before handing them over to
        handlers. The interceptors are given control in the order they are
        specified. This is an EXPERIMENTAL API.
      options: An optional list of key-value pairs (:term:`channel_arguments` in gRPC runtime)
        to configure the channel.
      maximum_concurrent_rpcs: The maximum number of concurrent RPCs this server
        will service before returning RESOURCE_EXHAUSTED status, or None to
        indicate no limit.
      compression: An element of grpc.compression, e.g.
        grpc.compression.Gzip. This compression algorithm will be used for the
        lifetime of the server unless overridden.
      xds: If set to true, retrieves server configuration via xDS. This is an
        EXPERIMENTAL option.

    Returns:
      A Server object.
    """
    from grpc import _server  # pylint: disable=cyclic-import

    return _server.create_server(
        thread_pool,
        () if handlers is None else handlers,
        () if interceptors is None else interceptors,
        () if options is None else options,
        maximum_concurrent_rpcs,
        compression,
        xds,
    )


@contextlib.contextmanager
def _create_servicer_context(rpc_event, state, request_deserializer):
    from grpc import _server  # pylint: disable=cyclic-import

    context = _server._Context(rpc_event, state, request_deserializer)
    yield context
    context._finalize_state()  # pylint: disable=protected-access


@enum.unique
class Compression(enum.IntEnum):
    """Indicates the compression method to be used for an RPC.

    Attributes:
     NoCompression: Do not use compression algorithm.
     Deflate: Use "Deflate" compression algorithm.
     Gzip: Use "Gzip" compression algorithm.
    """

    NoCompression = _compression.NoCompression
    Deflate = _compression.Deflate
    Gzip = _compression.Gzip


###################################  __all__  #################################

__all__ = (
    "FutureTimeoutError",
    "FutureCancelledError",
    "Future",
    "ChannelConnectivity",
    "StatusCode",
    "Status",
    "RpcError",
    "RpcContext",
    "Call",
    "ChannelCredentials",
    "CallCredentials",
    "AuthMetadataContext",
    "AuthMetadataPluginCallback",
    "AuthMetadataPlugin",
    "Compression",
    "ClientCallDetails",
    "ServerCertificateConfiguration",
    "ServerCredentials",
    "LocalConnectionType",
    "UnaryUnaryMultiCallable",
    "UnaryStreamMultiCallable",
    "StreamUnaryMultiCallable",
    "StreamStreamMultiCallable",
    "UnaryUnaryClientInterceptor",
    "UnaryStreamClientInterceptor",
    "StreamUnaryClientInterceptor",
    "StreamStreamClientInterceptor",
    "Channel",
    "ServicerContext",
    "RpcMethodHandler",
    "HandlerCallDetails",
    "GenericRpcHandler",
    "ServiceRpcHandler",
    "Server",
    "ServerInterceptor",
    "unary_unary_rpc_method_handler",
    "unary_stream_rpc_method_handler",
    "stream_unary_rpc_method_handler",
    "stream_stream_rpc_method_handler",
    "method_handlers_generic_handler",
    "ssl_channel_credentials",
    "metadata_call_credentials",
    "access_token_call_credentials",
    "composite_call_credentials",
    "composite_channel_credentials",
    "compute_engine_channel_credentials",
    "local_channel_credentials",
    "local_server_credentials",
    "alts_channel_credentials",
    "alts_server_credentials",
    "ssl_server_credentials",
    "ssl_server_certificate_configuration",
    "dynamic_ssl_server_credentials",
    "channel_ready_future",
    "insecure_channel",
    "secure_channel",
    "intercept_channel",
    "server",
    "protos",
    "services",
    "protos_and_services",
    "xds_channel_credentials",
    "xds_server_credentials",
    "insecure_server_credentials",
)

############################### Extension Shims ################################

# Here to maintain backwards compatibility; avoid using these in new code!
try:
    import grpc_tools

    sys.modules.update({"grpc.tools": grpc_tools})
except ImportError:
    pass
try:
    import grpc_health

    sys.modules.update({"grpc.health": grpc_health})
except ImportError:
    pass
try:
    import grpc_reflection

    sys.modules.update({"grpc.reflection": grpc_reflection})
except ImportError:
    pass

# Prevents import order issue in the case of renamed path.
if sys.version_info >= (3, 6) and __name__ == "grpc":
    from grpc import aio  # pylint: disable=ungrouped-imports

    sys.modules.update({"grpc.aio": aio})

# === NexusCore/openenv\Lib\site-packages\numpy\ma\extras.py ===
"""
Masked arrays add-ons.

A collection of utilities for `numpy.ma`.

:author: Pierre Gerard-Marchant
:contact: pierregm_at_uga_dot_edu

"""
__all__ = [
    'apply_along_axis', 'apply_over_axes', 'atleast_1d', 'atleast_2d',
    'atleast_3d', 'average', 'clump_masked', 'clump_unmasked', 'column_stack',
    'compress_cols', 'compress_nd', 'compress_rowcols', 'compress_rows',
    'count_masked', 'corrcoef', 'cov', 'diagflat', 'dot', 'dstack', 'ediff1d',
    'flatnotmasked_contiguous', 'flatnotmasked_edges', 'hsplit', 'hstack',
    'isin', 'in1d', 'intersect1d', 'mask_cols', 'mask_rowcols', 'mask_rows',
    'masked_all', 'masked_all_like', 'median', 'mr_', 'ndenumerate',
    'notmasked_contiguous', 'notmasked_edges', 'polyfit', 'row_stack',
    'setdiff1d', 'setxor1d', 'stack', 'unique', 'union1d', 'vander', 'vstack',
    ]

import itertools
import warnings

import numpy as np
from numpy import array as nxarray
from numpy import ndarray
from numpy.lib._function_base_impl import _ureduce
from numpy.lib._index_tricks_impl import AxisConcatenator
from numpy.lib.array_utils import normalize_axis_index, normalize_axis_tuple

from . import core as ma
from .core import (  # noqa: F401
    MAError,
    MaskedArray,
    add,
    array,
    asarray,
    concatenate,
    count,
    dot,
    filled,
    get_masked_subclass,
    getdata,
    getmask,
    getmaskarray,
    make_mask_descr,
    mask_or,
    masked,
    masked_array,
    nomask,
    ones,
    sort,
    zeros,
)


def issequence(seq):
    """
    Is seq a sequence (ndarray, list or tuple)?

    """
    return isinstance(seq, (ndarray, tuple, list))


def count_masked(arr, axis=None):
    """
    Count the number of masked elements along the given axis.

    Parameters
    ----------
    arr : array_like
        An array with (possibly) masked elements.
    axis : int, optional
        Axis along which to count. If None (default), a flattened
        version of the array is used.

    Returns
    -------
    count : int, ndarray
        The total number of masked elements (axis=None) or the number
        of masked elements along each slice of the given axis.

    See Also
    --------
    MaskedArray.count : Count non-masked elements.

    Examples
    --------
    >>> import numpy as np
    >>> a = np.arange(9).reshape((3,3))
    >>> a = np.ma.array(a)
    >>> a[1, 0] = np.ma.masked
    >>> a[1, 2] = np.ma.masked
    >>> a[2, 1] = np.ma.masked
    >>> a
    masked_array(
      data=[[0, 1, 2],
            [--, 4, --],
            [6, --, 8]],
      mask=[[False, False, False],
            [ True, False,  True],
            [False,  True, False]],
      fill_value=999999)
    >>> np.ma.count_masked(a)
    3

    When the `axis` keyword is used an array is returned.

    >>> np.ma.count_masked(a, axis=0)
    array([1, 1, 1])
    >>> np.ma.count_masked(a, axis=1)
    array([0, 2, 1])

    """
    m = getmaskarray(arr)
    return m.sum(axis)


def masked_all(shape, dtype=float):
    """
    Empty masked array with all elements masked.

    Return an empty masked array of the given shape and dtype, where all the
    data are masked.

    Parameters
    ----------
    shape : int or tuple of ints
        Shape of the required MaskedArray, e.g., ``(2, 3)`` or ``2``.
    dtype : dtype, optional
        Data type of the output.

    Returns
    -------
    a : MaskedArray
        A masked array with all data masked.

    See Also
    --------
    masked_all_like : Empty masked array modelled on an existing array.

    Notes
    -----
    Unlike other masked array creation functions (e.g. `numpy.ma.zeros`,
    `numpy.ma.ones`, `numpy.ma.full`), `masked_all` does not initialize the
    values of the array, and may therefore be marginally faster. However,
    the values stored in the newly allocated array are arbitrary. For
    reproducible behavior, be sure to set each element of the array before
    reading.

    Examples
    --------
    >>> import numpy as np
    >>> np.ma.masked_all((3, 3))
    masked_array(
      data=[[--, --, --],
            [--, --, --],
            [--, --, --]],
      mask=[[ True,  True,  True],
            [ True,  True,  True],
            [ True,  True,  True]],
      fill_value=1e+20,
      dtype=float64)

    The `dtype` parameter defines the underlying data type.

    >>> a = np.ma.masked_all((3, 3))
    >>> a.dtype
    dtype('float64')
    >>> a = np.ma.masked_all((3, 3), dtype=np.int32)
    >>> a.dtype
    dtype('int32')

    """
    a = masked_array(np.empty(shape, dtype),
                     mask=np.ones(shape, make_mask_descr(dtype)))
    return a


def masked_all_like(arr):
    """
    Empty masked array with the properties of an existing array.

    Return an empty masked array of the same shape and dtype as
    the array `arr`, where all the data are masked.

    Parameters
    ----------
    arr : ndarray
        An array describing the shape and dtype of the required MaskedArray.

    Returns
    -------
    a : MaskedArray
        A masked array with all data masked.

    Raises
    ------
    AttributeError
        If `arr` doesn't have a shape attribute (i.e. not an ndarray)

    See Also
    --------
    masked_all : Empty masked array with all elements masked.

    Notes
    -----
    Unlike other masked array creation functions (e.g. `numpy.ma.zeros_like`,
    `numpy.ma.ones_like`, `numpy.ma.full_like`), `masked_all_like` does not
    initialize the values of the array, and may therefore be marginally
    faster. However, the values stored in the newly allocated array are
    arbitrary. For reproducible behavior, be sure to set each element of the
    array before reading.

    Examples
    --------
    >>> import numpy as np
    >>> arr = np.zeros((2, 3), dtype=np.float32)
    >>> arr
    array([[0., 0., 0.],
           [0., 0., 0.]], dtype=float32)
    >>> np.ma.masked_all_like(arr)
    masked_array(
      data=[[--, --, --],
            [--, --, --]],
      mask=[[ True,  True,  True],
            [ True,  True,  True]],
      fill_value=np.float64(1e+20),
      dtype=float32)

    The dtype of the masked array matches the dtype of `arr`.

    >>> arr.dtype
    dtype('float32')
    >>> np.ma.masked_all_like(arr).dtype
    dtype('float32')

    """
    a = np.empty_like(arr).view(MaskedArray)
    a._mask = np.ones(a.shape, dtype=make_mask_descr(a.dtype))
    return a


#####--------------------------------------------------------------------------
#---- --- Standard functions ---
#####--------------------------------------------------------------------------
class _fromnxfunction:
    """
    Defines a wrapper to adapt NumPy functions to masked arrays.


    An instance of `_fromnxfunction` can be called with the same parameters
    as the wrapped NumPy function. The docstring of `newfunc` is adapted from
    the wrapped function as well, see `getdoc`.

    This class should not be used directly. Instead, one of its extensions that
    provides support for a specific type of input should be used.

    Parameters
    ----------
    funcname : str
        The name of the function to be adapted. The function should be
        in the NumPy namespace (i.e. ``np.funcname``).

    """

    def __init__(self, funcname):
        self.__name__ = funcname
        self.__qualname__ = funcname
        self.__doc__ = self.getdoc()

    def getdoc(self):
        """
        Retrieve the docstring and signature from the function.

        The ``__doc__`` attribute of the function is used as the docstring for
        the new masked array version of the function. A note on application
        of the function to the mask is appended.

        Parameters
        ----------
        None

        """
        npfunc = getattr(np, self.__name__, None)
        doc = getattr(npfunc, '__doc__', None)
        if doc:
            sig = ma.get_object_signature(npfunc)
            doc = ma.doc_note(doc, "The function is applied to both the _data "
                                   "and the _mask, if any.")
            if sig:
                sig = self.__name__ + sig + "\n\n"
            return sig + doc
        return

    def __call__(self, *args, **params):
        pass


class _fromnxfunction_single(_fromnxfunction):
    """
    A version of `_fromnxfunction` that is called with a single array
    argument followed by auxiliary args that are passed verbatim for
    both the data and mask calls.
    """
    def __call__(self, x, *args, **params):
        func = getattr(np, self.__name__)
        if isinstance(x, ndarray):
            _d = func(x.__array__(), *args, **params)
            _m = func(getmaskarray(x), *args, **params)
            return masked_array(_d, mask=_m)
        else:
            _d = func(np.asarray(x), *args, **params)
            _m = func(getmaskarray(x), *args, **params)
            return masked_array(_d, mask=_m)


class _fromnxfunction_seq(_fromnxfunction):
    """
    A version of `_fromnxfunction` that is called with a single sequence
    of arrays followed by auxiliary args that are passed verbatim for
    both the data and mask calls.
    """
    def __call__(self, x, *args, **params):
        func = getattr(np, self.__name__)
        _d = func(tuple(np.asarray(a) for a in x), *args, **params)
        _m = func(tuple(getmaskarray(a) for a in x), *args, **params)
        return masked_array(_d, mask=_m)


class _fromnxfunction_args(_fromnxfunction):
    """
    A version of `_fromnxfunction` that is called with multiple array
    arguments. The first non-array-like input marks the beginning of the
    arguments that are passed verbatim for both the data and mask calls.
    Array arguments are processed independently and the results are
    returned in a list. If only one array is found, the return value is
    just the processed array instead of a list.
    """
    def __call__(self, *args, **params):
        func = getattr(np, self.__name__)
        arrays = []
        args = list(args)
        while len(args) > 0 and issequence(args[0]):
            arrays.append(args.pop(0))
        res = []
        for x in arrays:
            _d = func(np.asarray(x), *args, **params)
            _m = func(getmaskarray(x), *args, **params)
            res.append(masked_array(_d, mask=_m))
        if len(arrays) == 1:
            return res[0]
        return res


class _fromnxfunction_allargs(_fromnxfunction):
    """
    A version of `_fromnxfunction` that is called with multiple array
    arguments. Similar to `_fromnxfunction_args` except that all args
    are converted to arrays even if they are not so already. This makes
    it possible to process scalars as 1-D arrays. Only keyword arguments
    are passed through verbatim for the data and mask calls. Arrays
    arguments are processed independently and the results are returned
    in a list. If only one arg is present, the return value is just the
    processed array instead of a list.
    """
    def __call__(self, *args, **params):
        func = getattr(np, self.__name__)
        res = []
        for x in args:
            _d = func(np.asarray(x), **params)
            _m = func(getmaskarray(x), **params)
            res.append(masked_array(_d, mask=_m))
        if len(args) == 1:
            return res[0]
        return res


atleast_1d = _fromnxfunction_allargs('atleast_1d')
atleast_2d = _fromnxfunction_allargs('atleast_2d')
atleast_3d = _fromnxfunction_allargs('atleast_3d')

vstack = row_stack = _fromnxfunction_seq('vstack')
hstack = _fromnxfunction_seq('hstack')
column_stack = _fromnxfunction_seq('column_stack')
dstack = _fromnxfunction_seq('dstack')
stack = _fromnxfunction_seq('stack')

hsplit = _fromnxfunction_single('hsplit')

diagflat = _fromnxfunction_single('diagflat')


#####--------------------------------------------------------------------------
#----
#####--------------------------------------------------------------------------
def flatten_inplace(seq):
    """Flatten a sequence in place."""
    k = 0
    while (k != len(seq)):
        while hasattr(seq[k], '__iter__'):
            seq[k:(k + 1)] = seq[k]
        k += 1
    return seq


def apply_along_axis(func1d, axis, arr, *args, **kwargs):
    """
    (This docstring should be overwritten)
    """
    arr = array(arr, copy=False, subok=True)
    nd = arr.ndim
    axis = normalize_axis_index(axis, nd)
    ind = [0] * (nd - 1)
    i = np.zeros(nd, 'O')
    indlist = list(range(nd))
    indlist.remove(axis)
    i[axis] = slice(None, None)
    outshape = np.asarray(arr.shape).take(indlist)
    i.put(indlist, ind)
    res = func1d(arr[tuple(i.tolist())], *args, **kwargs)
    #  if res is a number, then we have a smaller output array
    asscalar = np.isscalar(res)
    if not asscalar:
        try:
            len(res)
        except TypeError:
            asscalar = True
    # Note: we shouldn't set the dtype of the output from the first result
    # so we force the type to object, and build a list of dtypes.  We'll
    # just take the largest, to avoid some downcasting
    dtypes = []
    if asscalar:
        dtypes.append(np.asarray(res).dtype)
        outarr = zeros(outshape, object)
        outarr[tuple(ind)] = res
        Ntot = np.prod(outshape)
        k = 1
        while k < Ntot:
            # increment the index
            ind[-1] += 1
            n = -1
            while (ind[n] >= outshape[n]) and (n > (1 - nd)):
                ind[n - 1] += 1
                ind[n] = 0
                n -= 1
            i.put(indlist, ind)
            res = func1d(arr[tuple(i.tolist())], *args, **kwargs)
            outarr[tuple(ind)] = res
            dtypes.append(asarray(res).dtype)
            k += 1
    else:
        res = array(res, copy=False, subok=True)
        j = i.copy()
        j[axis] = ([slice(None, None)] * res.ndim)
        j.put(indlist, ind)
        Ntot = np.prod(outshape)
        holdshape = outshape
        outshape = list(arr.shape)
        outshape[axis] = res.shape
        dtypes.append(asarray(res).dtype)
        outshape = flatten_inplace(outshape)
        outarr = zeros(outshape, object)
        outarr[tuple(flatten_inplace(j.tolist()))] = res
        k = 1
        while k < Ntot:
            # increment the index
            ind[-1] += 1
            n = -1
            while (ind[n] >= holdshape[n]) and (n > (1 - nd)):
                ind[n - 1] += 1
                ind[n] = 0
                n -= 1
            i.put(indlist, ind)
            j.put(indlist, ind)
            res = func1d(arr[tuple(i.tolist())], *args, **kwargs)
            outarr[tuple(flatten_inplace(j.tolist()))] = res
            dtypes.append(asarray(res).dtype)
            k += 1
    max_dtypes = np.dtype(np.asarray(dtypes).max())
    if not hasattr(arr, '_mask'):
        result = np.asarray(outarr, dtype=max_dtypes)
    else:
        result = asarray(outarr, dtype=max_dtypes)
        result.fill_value = ma.default_fill_value(result)
    return result


apply_along_axis.__doc__ = np.apply_along_axis.__doc__


def apply_over_axes(func, a, axes):
    """
    (This docstring will be overwritten)
    """
    val = asarray(a)
    N = a.ndim
    if array(axes).ndim == 0:
        axes = (axes,)
    for axis in axes:
        if axis < 0:
            axis = N + axis
        args = (val, axis)
        res = func(*args)
        if res.ndim == val.ndim:
            val = res
        else:
            res = ma.expand_dims(res, axis)
            if res.ndim == val.ndim:
                val = res
            else:
                raise ValueError("function is not returning "
                        "an array of the correct shape")
    return val


if apply_over_axes.__doc__ is not None:
    apply_over_axes.__doc__ = np.apply_over_axes.__doc__[
        :np.apply_over_axes.__doc__.find('Notes')].rstrip() + \
    """

    Examples
    --------
    >>> import numpy as np
    >>> a = np.ma.arange(24).reshape(2,3,4)
    >>> a[:,0,1] = np.ma.masked
    >>> a[:,1,:] = np.ma.masked
    >>> a
    masked_array(
      data=[[[0, --, 2, 3],
             [--, --, --, --],
             [8, 9, 10, 11]],
            [[12, --, 14, 15],
             [--, --, --, --],
             [20, 21, 22, 23]]],
      mask=[[[False,  True, False, False],
             [ True,  True,  True,  True],
             [False, False, False, False]],
            [[False,  True, False, False],
             [ True,  True,  True,  True],
             [False, False, False, False]]],
      fill_value=999999)
    >>> np.ma.apply_over_axes(np.ma.sum, a, [0,2])
    masked_array(
      data=[[[46],
             [--],
             [124]]],
      mask=[[[False],
             [ True],
             [False]]],
      fill_value=999999)

    Tuple axis arguments to ufuncs are equivalent:

    >>> np.ma.sum(a, axis=(0,2)).reshape((1,-1,1))
    masked_array(
      data=[[[46],
             [--],
             [124]]],
      mask=[[[False],
             [ True],
             [False]]],
      fill_value=999999)
    """


def average(a, axis=None, weights=None, returned=False, *,
            keepdims=np._NoValue):
    """
    Return the weighted average of array over the given axis.

    Parameters
    ----------
    a : array_like
        Data to be averaged.
        Masked entries are not taken into account in the computation.
    axis : None or int or tuple of ints, optional
        Axis or axes along which to average `a`.  The default,
        `axis=None`, will average over all of the elements of the input array.
        If axis is a tuple of ints, averaging is performed on all of the axes
        specified in the tuple instead of a single axis or all the axes as
        before.
    weights : array_like, optional
        An array of weights associated with the values in `a`. Each value in
        `a` contributes to the average according to its associated weight.
        The array of weights must be the same shape as `a` if no axis is
        specified, otherwise the weights must have dimensions and shape
        consistent with `a` along the specified axis.
        If `weights=None`, then all data in `a` are assumed to have a
        weight equal to one.
        The calculation is::

            avg = sum(a * weights) / sum(weights)

        where the sum is over all included elements.
        The only constraint on the values of `weights` is that `sum(weights)`
        must not be 0.
    returned : bool, optional
        Flag indicating whether a tuple ``(result, sum of weights)``
        should be returned as output (True), or just the result (False).
        Default is False.
    keepdims : bool, optional
        If this is set to True, the axes which are reduced are left
        in the result as dimensions with size one. With this option,
        the result will broadcast correctly against the original `a`.
        *Note:* `keepdims` will not work with instances of `numpy.matrix`
        or other classes whose methods do not support `keepdims`.

        .. versionadded:: 1.23.0

    Returns
    -------
    average, [sum_of_weights] : (tuple of) scalar or MaskedArray
        The average along the specified axis. When returned is `True`,
        return a tuple with the average as the first element and the sum
        of the weights as the second element. The return type is `np.float64`
        if `a` is of integer type and floats smaller than `float64`, or the
        input data-type, otherwise. If returned, `sum_of_weights` is always
        `float64`.

    Raises
    ------
    ZeroDivisionError
        When all weights along axis are zero. See `numpy.ma.average` for a
        version robust to this type of error.
    TypeError
        When `weights` does not have the same shape as `a`, and `axis=None`.
    ValueError
        When `weights` does not have dimensions and shape consistent with `a`
        along specified `axis`.

    Examples
    --------
    >>> import numpy as np
    >>> a = np.ma.array([1., 2., 3., 4.], mask=[False, False, True, True])
    >>> np.ma.average(a, weights=[3, 1, 0, 0])
    1.25

    >>> x = np.ma.arange(6.).reshape(3, 2)
    >>> x
    masked_array(
      data=[[0., 1.],
            [2., 3.],
            [4., 5.]],
      mask=False,
      fill_value=1e+20)
    >>> data = np.arange(8).reshape((2, 2, 2))
    >>> data
    array([[[0, 1],
            [2, 3]],
           [[4, 5],
            [6, 7]]])
    >>> np.ma.average(data, axis=(0, 1), weights=[[1./4, 3./4], [1., 1./2]])
    masked_array(data=[3.4, 4.4],
             mask=[False, False],
       fill_value=1e+20)
    >>> np.ma.average(data, axis=0, weights=[[1./4, 3./4], [1., 1./2]])
    Traceback (most recent call last):
        ...
    ValueError: Shape of weights must be consistent
    with shape of a along specified axis.

    >>> avg, sumweights = np.ma.average(x, axis=0, weights=[1, 2, 3],
    ...                                 returned=True)
    >>> avg
    masked_array(data=[2.6666666666666665, 3.6666666666666665],
                 mask=[False, False],
           fill_value=1e+20)

    With ``keepdims=True``, the following result has shape (3, 1).

    >>> np.ma.average(x, axis=1, keepdims=True)
    masked_array(
      data=[[0.5],
            [2.5],
            [4.5]],
      mask=False,
      fill_value=1e+20)
    """
    a = asarray(a)
    m = getmask(a)

    if axis is not None:
        axis = normalize_axis_tuple(axis, a.ndim, argname="axis")

    if keepdims is np._NoValue:
        # Don't pass on the keepdims argument if one wasn't given.
        keepdims_kw = {}
    else:
        keepdims_kw = {'keepdims': keepdims}

    if weights is None:
        avg = a.mean(axis, **keepdims_kw)
        scl = avg.dtype.type(a.count(axis))
    else:
        wgt = asarray(weights)

        if issubclass(a.dtype.type, (np.integer, np.bool)):
            result_dtype = np.result_type(a.dtype, wgt.dtype, 'f8')
        else:
            result_dtype = np.result_type(a.dtype, wgt.dtype)

        # Sanity checks
        if a.shape != wgt.shape:
            if axis is None:
                raise TypeError(
                    "Axis must be specified when shapes of a and weights "
                    "differ.")
            if wgt.shape != tuple(a.shape[ax] for ax in axis):
                raise ValueError(
                    "Shape of weights must be consistent with "
                    "shape of a along specified axis.")

            # setup wgt to broadcast along axis
            wgt = wgt.transpose(np.argsort(axis))
            wgt = wgt.reshape(tuple((s if ax in axis else 1)
                                    for ax, s in enumerate(a.shape)))

        if m is not nomask:
            wgt = wgt * (~a.mask)
            wgt.mask |= a.mask

        scl = wgt.sum(axis=axis, dtype=result_dtype, **keepdims_kw)
        avg = np.multiply(a, wgt,
                          dtype=result_dtype).sum(axis, **keepdims_kw) / scl

    if returned:
        if scl.shape != avg.shape:
            scl = np.broadcast_to(scl, avg.shape).copy()
        return avg, scl
    else:
        return avg


def median(a, axis=None, out=None, overwrite_input=False, keepdims=False):
    """
    Compute the median along the specified axis.

    Returns the median of the array elements.

    Parameters
    ----------
    a : array_like
        Input array or object that can be converted to an array.
    axis : int, optional
        Axis along which the medians are computed. The default (None) is
        to compute the median along a flattened version of the array.
    out : ndarray, optional
        Alternative output array in which to place the result. It must
        have the same shape and buffer length as the expected output
        but the type will be cast if necessary.
    overwrite_input : bool, optional
        If True, then allow use of memory of input array (a) for
        calculations. The input array will be modified by the call to
        median. This will save memory when you do not need to preserve
        the contents of the input array. Treat the input as undefined,
        but it will probably be fully or partially sorted. Default is
        False. Note that, if `overwrite_input` is True, and the input
        is not already an `ndarray`, an error will be raised.
    keepdims : bool, optional
        If this is set to True, the axes which are reduced are left
        in the result as dimensions with size one. With this option,
        the result will broadcast correctly against the input array.

    Returns
    -------
    median : ndarray
        A new array holding the result is returned unless out is
        specified, in which case a reference to out is returned.
        Return data-type is `float64` for integers and floats smaller than
        `float64`, or the input data-type, otherwise.

    See Also
    --------
    mean

    Notes
    -----
    Given a vector ``V`` with ``N`` non masked values, the median of ``V``
    is the middle value of a sorted copy of ``V`` (``Vs``) - i.e.
    ``Vs[(N-1)/2]``, when ``N`` is odd, or ``{Vs[N/2 - 1] + Vs[N/2]}/2``
    when ``N`` is even.

    Examples
    --------
    >>> import numpy as np
    >>> x = np.ma.array(np.arange(8), mask=[0]*4 + [1]*4)
    >>> np.ma.median(x)
    1.5

    >>> x = np.ma.array(np.arange(10).reshape(2, 5), mask=[0]*6 + [1]*4)
    >>> np.ma.median(x)
    2.5
    >>> np.ma.median(x, axis=-1, overwrite_input=True)
    masked_array(data=[2.0, 5.0],
                 mask=[False, False],
           fill_value=1e+20)

    """
    if not hasattr(a, 'mask'):
        m = np.median(getdata(a, subok=True), axis=axis,
                      out=out, overwrite_input=overwrite_input,
                      keepdims=keepdims)
        if isinstance(m, np.ndarray) and 1 <= m.ndim:
            return masked_array(m, copy=False)
        else:
            return m

    return _ureduce(a, func=_median, keepdims=keepdims, axis=axis, out=out,
                    overwrite_input=overwrite_input)


def _median(a, axis=None, out=None, overwrite_input=False):
    # when an unmasked NaN is present return it, so we need to sort the NaN
    # values behind the mask
    if np.issubdtype(a.dtype, np.inexact):
        fill_value = np.inf
    else:
        fill_value = None
    if overwrite_input:
        if axis is None:
            asorted = a.ravel()
            asorted.sort(fill_value=fill_value)
        else:
            a.sort(axis=axis, fill_value=fill_value)
            asorted = a
    else:
        asorted = sort(a, axis=axis, fill_value=fill_value)

    if axis is None:
        axis = 0
    else:
        axis = normalize_axis_index(axis, asorted.ndim)

    if asorted.shape[axis] == 0:
        # for empty axis integer indices fail so use slicing to get same result
        # as median (which is mean of empty slice = nan)
        indexer = [slice(None)] * asorted.ndim
        indexer[axis] = slice(0, 0)
        indexer = tuple(indexer)
        return np.ma.mean(asorted[indexer], axis=axis, out=out)

    if asorted.ndim == 1:
        idx, odd = divmod(count(asorted), 2)
        mid = asorted[idx + odd - 1:idx + 1]
        if np.issubdtype(asorted.dtype, np.inexact) and asorted.size > 0:
            # avoid inf / x = masked
            s = mid.sum(out=out)
            if not odd:
                s = np.true_divide(s, 2., casting='safe', out=out)
            s = np.lib._utils_impl._median_nancheck(asorted, s, axis)
        else:
            s = mid.mean(out=out)

        # if result is masked either the input contained enough
        # minimum_fill_value so that it would be the median or all values
        # masked
        if np.ma.is_masked(s) and not np.all(asorted.mask):
            return np.ma.minimum_fill_value(asorted)
        return s

    counts = count(asorted, axis=axis, keepdims=True)
    h = counts // 2

    # duplicate high if odd number of elements so mean does nothing
    odd = counts % 2 == 1
    l = np.where(odd, h, h - 1)

    lh = np.concatenate([l, h], axis=axis)

    # get low and high median
    low_high = np.take_along_axis(asorted, lh, axis=axis)

    def replace_masked(s):
        # Replace masked entries with minimum_full_value unless it all values
        # are masked. This is required as the sort order of values equal or
        # larger than the fill value is undefined and a valid value placed
        # elsewhere, e.g. [4, --, inf].
        if np.ma.is_masked(s):
            rep = (~np.all(asorted.mask, axis=axis, keepdims=True)) & s.mask
            s.data[rep] = np.ma.minimum_fill_value(asorted)
            s.mask[rep] = False

    replace_masked(low_high)

    if np.issubdtype(asorted.dtype, np.inexact):
        # avoid inf / x = masked
        s = np.ma.sum(low_high, axis=axis, out=out)
        np.true_divide(s.data, 2., casting='unsafe', out=s.data)

        s = np.lib._utils_impl._median_nancheck(asorted, s, axis)
    else:
        s = np.ma.mean(low_high, axis=axis, out=out)

    return s


def compress_nd(x, axis=None):
    """Suppress slices from multiple dimensions which contain masked values.

    Parameters
    ----------
    x : array_like, MaskedArray
        The array to operate on. If not a MaskedArray instance (or if no array
        elements are masked), `x` is interpreted as a MaskedArray with `mask`
        set to `nomask`.
    axis : tuple of ints or int, optional
        Which dimensions to suppress slices from can be configured with this
        parameter.
        - If axis is a tuple of ints, those are the axes to suppress slices from.
        - If axis is an int, then that is the only axis to suppress slices from.
        - If axis is None, all axis are selected.

    Returns
    -------
    compress_array : ndarray
        The compressed array.

    Examples
    --------
    >>> import numpy as np
    >>> arr = [[1, 2], [3, 4]]
    >>> mask = [[0, 1], [0, 0]]
    >>> x = np.ma.array(arr, mask=mask)
    >>> np.ma.compress_nd(x, axis=0)
    array([[3, 4]])
    >>> np.ma.compress_nd(x, axis=1)
    array([[1],
           [3]])
    >>> np.ma.compress_nd(x)
    array([[3]])

    """
    x = asarray(x)
    m = getmask(x)
    # Set axis to tuple of ints
    if axis is None:
        axis = tuple(range(x.ndim))
    else:
        axis = normalize_axis_tuple(axis, x.ndim)

    # Nothing is masked: return x
    if m is nomask or not m.any():
        return x._data
    # All is masked: return empty
    if m.all():
        return nxarray([])
    # Filter elements through boolean indexing
    data = x._data
    for ax in axis:
        axes = tuple(list(range(ax)) + list(range(ax + 1, x.ndim)))
        data = data[(slice(None),) * ax + (~m.any(axis=axes),)]
    return data


def compress_rowcols(x, axis=None):
    """
    Suppress the rows and/or columns of a 2-D array that contain
    masked values.

    The suppression behavior is selected with the `axis` parameter.

    - If axis is None, both rows and columns are suppressed.
    - If axis is 0, only rows are suppressed.
    - If axis is 1 or -1, only columns are suppressed.

    Parameters
    ----------
    x : array_like, MaskedArray
        The array to operate on.  If not a MaskedArray instance (or if no array
        elements are masked), `x` is interpreted as a MaskedArray with
        `mask` set to `nomask`. Must be a 2D array.
    axis : int, optional
        Axis along which to perform the operation. Default is None.

    Returns
    -------
    compressed_array : ndarray
        The compressed array.

    Examples
    --------
    >>> import numpy as np
    >>> x = np.ma.array(np.arange(9).reshape(3, 3), mask=[[1, 0, 0],
    ...                                                   [1, 0, 0],
    ...                                                   [0, 0, 0]])
    >>> x
    masked_array(
      data=[[--, 1, 2],
            [--, 4, 5],
            [6, 7, 8]],
      mask=[[ True, False, False],
            [ True, False, False],
            [False, False, False]],
      fill_value=999999)

    >>> np.ma.compress_rowcols(x)
    array([[7, 8]])
    >>> np.ma.compress_rowcols(x, 0)
    array([[6, 7, 8]])
    >>> np.ma.compress_rowcols(x, 1)
    array([[1, 2],
           [4, 5],
           [7, 8]])

    """
    if asarray(x).ndim != 2:
        raise NotImplementedError("compress_rowcols works for 2D arrays only.")
    return compress_nd(x, axis=axis)


def compress_rows(a):
    """
    Suppress whole rows of a 2-D array that contain masked values.

    This is equivalent to ``np.ma.compress_rowcols(a, 0)``, see
    `compress_rowcols` for details.

    Parameters
    ----------
    x : array_like, MaskedArray
        The array to operate on. If not a MaskedArray instance (or if no array
        elements are masked), `x` is interpreted as a MaskedArray with
        `mask` set to `nomask`. Must be a 2D array.

    Returns
    -------
    compressed_array : ndarray
        The compressed array.

    See Also
    --------
    compress_rowcols

    Examples
    --------
    >>> import numpy as np
    >>> a = np.ma.array(np.arange(9).reshape(3, 3), mask=[[1, 0, 0],
    ...                                                   [1, 0, 0],
    ...                                                   [0, 0, 0]])
    >>> np.ma.compress_rows(a)
    array([[6, 7, 8]])

    """
    a = asarray(a)
    if a.ndim != 2:
        raise NotImplementedError("compress_rows works for 2D arrays only.")
    return compress_rowcols(a, 0)


def compress_cols(a):
    """
    Suppress whole columns of a 2-D array that contain masked values.

    This is equivalent to ``np.ma.compress_rowcols(a, 1)``, see
    `compress_rowcols` for details.

    Parameters
    ----------
    x : array_like, MaskedArray
        The array to operate on.  If not a MaskedArray instance (or if no array
        elements are masked), `x` is interpreted as a MaskedArray with
        `mask` set to `nomask`. Must be a 2D array.

    Returns
    -------
    compressed_array : ndarray
        The compressed array.

    See Also
    --------
    compress_rowcols

    Examples
    --------
    >>> import numpy as np
    >>> a = np.ma.array(np.arange(9).reshape(3, 3), mask=[[1, 0, 0],
    ...                                                   [1, 0, 0],
    ...                                                   [0, 0, 0]])
    >>> np.ma.compress_cols(a)
    array([[1, 2],
           [4, 5],
           [7, 8]])

    """
    a = asarray(a)
    if a.ndim != 2:
        raise NotImplementedError("compress_cols works for 2D arrays only.")
    return compress_rowcols(a, 1)


def mask_rowcols(a, axis=None):
    """
    Mask rows and/or columns of a 2D array that contain masked values.

    Mask whole rows and/or columns of a 2D array that contain
    masked values.  The masking behavior is selected using the
    `axis` parameter.

      - If `axis` is None, rows *and* columns are masked.
      - If `axis` is 0, only rows are masked.
      - If `axis` is 1 or -1, only columns are masked.

    Parameters
    ----------
    a : array_like, MaskedArray
        The array to mask.  If not a MaskedArray instance (or if no array
        elements are masked), the result is a MaskedArray with `mask` set
        to `nomask` (False). Must be a 2D array.
    axis : int, optional
        Axis along which to perform the operation. If None, applies to a
        flattened version of the array.

    Returns
    -------
    a : MaskedArray
        A modified version of the input array, masked depending on the value
        of the `axis` parameter.

    Raises
    ------
    NotImplementedError
        If input array `a` is not 2D.

    See Also
    --------
    mask_rows : Mask rows of a 2D array that contain masked values.
    mask_cols : Mask cols of a 2D array that contain masked values.
    masked_where : Mask where a condition is met.

    Notes
    -----
    The input array's mask is modified by this function.

    Examples
    --------
    >>> import numpy as np
    >>> a = np.zeros((3, 3), dtype=int)
    >>> a[1, 1] = 1
    >>> a
    array([[0, 0, 0],
           [0, 1, 0],
           [0, 0, 0]])
    >>> a = np.ma.masked_equal(a, 1)
    >>> a
    masked_array(
      data=[[0, 0, 0],
            [0, --, 0],
            [0, 0, 0]],
      mask=[[False, False, False],
            [False,  True, False],
            [False, False, False]],
      fill_value=1)
    >>> np.ma.mask_rowcols(a)
    masked_array(
      data=[[0, --, 0],
            [--, --, --],
            [0, --, 0]],
      mask=[[False,  True, False],
            [ True,  True,  True],
            [False,  True, False]],
      fill_value=1)

    """
    a = array(a, subok=False)
    if a.ndim != 2:
        raise NotImplementedError("mask_rowcols works for 2D arrays only.")
    m = getmask(a)
    # Nothing is masked: return a
    if m is nomask or not m.any():
        return a
    maskedval = m.nonzero()
    a._mask = a._mask.copy()
    if not axis:
        a[np.unique(maskedval[0])] = masked
    if axis in [None, 1, -1]:
        a[:, np.unique(maskedval[1])] = masked
    return a


def mask_rows(a, axis=np._NoValue):
    """
    Mask rows of a 2D array that contain masked values.

    This function is a shortcut to ``mask_rowcols`` with `axis` equal to 0.

    See Also
    --------
    mask_rowcols : Mask rows and/or columns of a 2D array.
    masked_where : Mask where a condition is met.

    Examples
    --------
    >>> import numpy as np
    >>> a = np.zeros((3, 3), dtype=int)
    >>> a[1, 1] = 1
    >>> a
    array([[0, 0, 0],
           [0, 1, 0],
           [0, 0, 0]])
    >>> a = np.ma.masked_equal(a, 1)
    >>> a
    masked_array(
      data=[[0, 0, 0],
            [0, --, 0],
            [0, 0, 0]],
      mask=[[False, False, False],
            [False,  True, False],
            [False, False, False]],
      fill_value=1)

    >>> np.ma.mask_rows(a)
    masked_array(
      data=[[0, 0, 0],
            [--, --, --],
            [0, 0, 0]],
      mask=[[False, False, False],
            [ True,  True,  True],
            [False, False, False]],
      fill_value=1)

    """
    if axis is not np._NoValue:
        # remove the axis argument when this deprecation expires
        # NumPy 1.18.0, 2019-11-28
        warnings.warn(
            "The axis argument has always been ignored, in future passing it "
            "will raise TypeError", DeprecationWarning, stacklevel=2)
    return mask_rowcols(a, 0)


def mask_cols(a, axis=np._NoValue):
    """
    Mask columns of a 2D array that contain masked values.

    This function is a shortcut to ``mask_rowcols`` with `axis` equal to 1.

    See Also
    --------
    mask_rowcols : Mask rows and/or columns of a 2D array.
    masked_where : Mask where a condition is met.

    Examples
    --------
    >>> import numpy as np
    >>> a = np.zeros((3, 3), dtype=int)
    >>> a[1, 1] = 1
    >>> a
    array([[0, 0, 0],
           [0, 1, 0],
           [0, 0, 0]])
    >>> a = np.ma.masked_equal(a, 1)
    >>> a
    masked_array(
      data=[[0, 0, 0],
            [0, --, 0],
            [0, 0, 0]],
      mask=[[False, False, False],
            [False,  True, False],
            [False, False, False]],
      fill_value=1)
    >>> np.ma.mask_cols(a)
    masked_array(
      data=[[0, --, 0],
            [0, --, 0],
            [0, --, 0]],
      mask=[[False,  True, False],
            [False,  True, False],
            [False,  True, False]],
      fill_value=1)

    """
    if axis is not np._NoValue:
        # remove the axis argument when this deprecation expires
        # NumPy 1.18.0, 2019-11-28
        warnings.warn(
            "The axis argument has always been ignored, in future passing it "
            "will raise TypeError", DeprecationWarning, stacklevel=2)
    return mask_rowcols(a, 1)


#####--------------------------------------------------------------------------
#---- --- arraysetops ---
#####--------------------------------------------------------------------------

def ediff1d(arr, to_end=None, to_begin=None):
    """
    Compute the differences between consecutive elements of an array.

    This function is the equivalent of `numpy.ediff1d` that takes masked
    values into account, see `numpy.ediff1d` for details.

    See Also
    --------
    numpy.ediff1d : Equivalent function for ndarrays.

    Examples
    --------
    >>> import numpy as np
    >>> arr = np.ma.array([1, 2, 4, 7, 0])
    >>> np.ma.ediff1d(arr)
    masked_array(data=[ 1,  2,  3, -7],
                 mask=False,
           fill_value=999999)

    """
    arr = ma.asanyarray(arr).flat
    ed = arr[1:] - arr[:-1]
    arrays = [ed]
    #
    if to_begin is not None:
        arrays.insert(0, to_begin)
    if to_end is not None:
        arrays.append(to_end)
    #
    if len(arrays) != 1:
        # We'll save ourselves a copy of a potentially large array in the common
        # case where neither to_begin or to_end was given.
        ed = hstack(arrays)
    #
    return ed


def unique(ar1, return_index=False, return_inverse=False):
    """
    Finds the unique elements of an array.

    Masked values are considered the same element (masked). The output array
    is always a masked array. See `numpy.unique` for more details.

    See Also
    --------
    numpy.unique : Equivalent function for ndarrays.

    Examples
    --------
    >>> import numpy as np
    >>> a = [1, 2, 1000, 2, 3]
    >>> mask = [0, 0, 1, 0, 0]
    >>> masked_a = np.ma.masked_array(a, mask)
    >>> masked_a
    masked_array(data=[1, 2, --, 2, 3],
                mask=[False, False,  True, False, False],
        fill_value=999999)
    >>> np.ma.unique(masked_a)
    masked_array(data=[1, 2, 3, --],
                mask=[False, False, False,  True],
        fill_value=999999)
    >>> np.ma.unique(masked_a, return_index=True)
    (masked_array(data=[1, 2, 3, --],
                mask=[False, False, False,  True],
        fill_value=999999), array([0, 1, 4, 2]))
    >>> np.ma.unique(masked_a, return_inverse=True)
    (masked_array(data=[1, 2, 3, --],
                mask=[False, False, False,  True],
        fill_value=999999), array([0, 1, 3, 1, 2]))
    >>> np.ma.unique(masked_a, return_index=True, return_inverse=True)
    (masked_array(data=[1, 2, 3, --],
                mask=[False, False, False,  True],
        fill_value=999999), array([0, 1, 4, 2]), array([0, 1, 3, 1, 2]))
    """
    output = np.unique(ar1,
                       return_index=return_index,
                       return_inverse=return_inverse)
    if isinstance(output, tuple):
        output = list(output)
        output[0] = output[0].view(MaskedArray)
        output = tuple(output)
    else:
        output = output.view(MaskedArray)
    return output


def intersect1d(ar1, ar2, assume_unique=False):
    """
    Returns the unique elements common to both arrays.

    Masked values are considered equal one to the other.
    The output is always a masked array.

    See `numpy.intersect1d` for more details.

    See Also
    --------
    numpy.intersect1d : Equivalent function for ndarrays.

    Examples
    --------
    >>> import numpy as np
    >>> x = np.ma.array([1, 3, 3, 3], mask=[0, 0, 0, 1])
    >>> y = np.ma.array([3, 1, 1, 1], mask=[0, 0, 0, 1])
    >>> np.ma.intersect1d(x, y)
    masked_array(data=[1, 3, --],
                 mask=[False, False,  True],
           fill_value=999999)

    """
    if assume_unique:
        aux = ma.concatenate((ar1, ar2))
    else:
        # Might be faster than unique( intersect1d( ar1, ar2 ) )?
        aux = ma.concatenate((unique(ar1), unique(ar2)))
    aux.sort()
    return aux[:-1][aux[1:] == aux[:-1]]


def setxor1d(ar1, ar2, assume_unique=False):
    """
    Set exclusive-or of 1-D arrays with unique elements.

    The output is always a masked array. See `numpy.setxor1d` for more details.

    See Also
    --------
    numpy.setxor1d : Equivalent function for ndarrays.

    Examples
    --------
    >>> import numpy as np
    >>> ar1 = np.ma.array([1, 2, 3, 2, 4])
    >>> ar2 = np.ma.array([2, 3, 5, 7, 5])
    >>> np.ma.setxor1d(ar1, ar2)
    masked_array(data=[1, 4, 5, 7],
                 mask=False,
           fill_value=999999)

    """
    if not assume_unique:
        ar1 = unique(ar1)
        ar2 = unique(ar2)

    aux = ma.concatenate((ar1, ar2), axis=None)
    if aux.size == 0:
        return aux
    aux.sort()
    auxf = aux.filled()
#    flag = ediff1d( aux, to_end = 1, to_begin = 1 ) == 0
    flag = ma.concatenate(([True], (auxf[1:] != auxf[:-1]), [True]))
#    flag2 = ediff1d( flag ) == 0
    flag2 = (flag[1:] == flag[:-1])
    return aux[flag2]


def in1d(ar1, ar2, assume_unique=False, invert=False):
    """
    Test whether each element of an array is also present in a second
    array.

    The output is always a masked array. See `numpy.in1d` for more details.

    We recommend using :func:`isin` instead of `in1d` for new code.

    See Also
    --------
    isin       : Version of this function that preserves the shape of ar1.
    numpy.in1d : Equivalent function for ndarrays.

    Examples
    --------
    >>> import numpy as np
    >>> ar1 = np.ma.array([0, 1, 2, 5, 0])
    >>> ar2 = [0, 2]
    >>> np.ma.in1d(ar1, ar2)
    masked_array(data=[ True, False,  True, False,  True],
                 mask=False,
           fill_value=True)

    """
    if not assume_unique:
        ar1, rev_idx = unique(ar1, return_inverse=True)
        ar2 = unique(ar2)

    ar = ma.concatenate((ar1, ar2))
    # We need this to be a stable sort, so always use 'mergesort'
    # here. The values from the first array should always come before
    # the values from the second array.
    order = ar.argsort(kind='mergesort')
    sar = ar[order]
    if invert:
        bool_ar = (sar[1:] != sar[:-1])
    else:
        bool_ar = (sar[1:] == sar[:-1])
    flag = ma.concatenate((bool_ar, [invert]))
    indx = order.argsort(kind='mergesort')[:len(ar1)]

    if assume_unique:
        return flag[indx]
    else:
        return flag[indx][rev_idx]


def isin(element, test_elements, assume_unique=False, invert=False):
    """
    Calculates `element in test_elements`, broadcasting over
    `element` only.

    The output is always a masked array of the same shape as `element`.
    See `numpy.isin` for more details.

    See Also
    --------
    in1d       : Flattened version of this function.
    numpy.isin : Equivalent function for ndarrays.

    Examples
    --------
    >>> import numpy as np
    >>> element = np.ma.array([1, 2, 3, 4, 5, 6])
    >>> test_elements = [0, 2]
    >>> np.ma.isin(element, test_elements)
    masked_array(data=[False,  True, False, False, False, False],
                 mask=False,
           fill_value=True)

    """
    element = ma.asarray(element)
    return in1d(element, test_elements, assume_unique=assume_unique,
                invert=invert).reshape(element.shape)


def union1d(ar1, ar2):
    """
    Union of two arrays.

    The output is always a masked array. See `numpy.union1d` for more details.

    See Also
    --------
    numpy.union1d : Equivalent function for ndarrays.

    Examples
    --------
    >>> import numpy as np
    >>> ar1 = np.ma.array([1, 2, 3, 4])
    >>> ar2 = np.ma.array([3, 4, 5, 6])
    >>> np.ma.union1d(ar1, ar2)
    masked_array(data=[1, 2, 3, 4, 5, 6],
             mask=False,
       fill_value=999999)

    """
    return unique(ma.concatenate((ar1, ar2), axis=None))


def setdiff1d(ar1, ar2, assume_unique=False):
    """
    Set difference of 1D arrays with unique elements.

    The output is always a masked array. See `numpy.setdiff1d` for more
    details.

    See Also
    --------
    numpy.setdiff1d : Equivalent function for ndarrays.

    Examples
    --------
    >>> import numpy as np
    >>> x = np.ma.array([1, 2, 3, 4], mask=[0, 1, 0, 1])
    >>> np.ma.setdiff1d(x, [1, 2])
    masked_array(data=[3, --],
                 mask=[False,  True],
           fill_value=999999)

    """
    if assume_unique:
        ar1 = ma.asarray(ar1).ravel()
    else:
        ar1 = unique(ar1)
        ar2 = unique(ar2)
    return ar1[in1d(ar1, ar2, assume_unique=True, invert=True)]


###############################################################################
#                                Covariance                                   #
###############################################################################


def _covhelper(x, y=None, rowvar=True, allow_masked=True):
    """
    Private function for the computation of covariance and correlation
    coefficients.

    """
    x = ma.array(x, ndmin=2, copy=True, dtype=float)
    xmask = ma.getmaskarray(x)
    # Quick exit if we can't process masked data
    if not allow_masked and xmask.any():
        raise ValueError("Cannot process masked data.")
    #
    if x.shape[0] == 1:
        rowvar = True
    # Make sure that rowvar is either 0 or 1
    rowvar = int(bool(rowvar))
    axis = 1 - rowvar
    if rowvar:
        tup = (slice(None), None)
    else:
        tup = (None, slice(None))
    #
    if y is None:
        # Check if we can guarantee that the integers in the (N - ddof)
        # normalisation can be accurately represented with single-precision
        # before computing the dot product.
        if x.shape[0] > 2 ** 24 or x.shape[1] > 2 ** 24:
            xnm_dtype = np.float64
        else:
            xnm_dtype = np.float32
        xnotmask = np.logical_not(xmask).astype(xnm_dtype)
    else:
        y = array(y, copy=False, ndmin=2, dtype=float)
        ymask = ma.getmaskarray(y)
        if not allow_masked and ymask.any():
            raise ValueError("Cannot process masked data.")
        if xmask.any() or ymask.any():
            if y.shape == x.shape:
                # Define some common mask
                common_mask = np.logical_or(xmask, ymask)
                if common_mask is not nomask:
                    xmask = x._mask = y._mask = ymask = common_mask
                    x._sharedmask = False
                    y._sharedmask = False
        x = ma.concatenate((x, y), axis)
        # Check if we can guarantee that the integers in the (N - ddof)
        # normalisation can be accurately represented with single-precision
        # before computing the dot product.
        if x.shape[0] > 2 ** 24 or x.shape[1] > 2 ** 24:
            xnm_dtype = np.float64
        else:
            xnm_dtype = np.float32
        xnotmask = np.logical_not(np.concatenate((xmask, ymask), axis)).astype(
            xnm_dtype
        )
    x -= x.mean(axis=rowvar)[tup]
    return (x, xnotmask, rowvar)


def cov(x, y=None, rowvar=True, bias=False, allow_masked=True, ddof=None):
    """
    Estimate the covariance matrix.

    Except for the handling of missing data this function does the same as
    `numpy.cov`. For more details and examples, see `numpy.cov`.

    By default, masked values are recognized as such. If `x` and `y` have the
    same shape, a common mask is allocated: if ``x[i,j]`` is masked, then
    ``y[i,j]`` will also be masked.
    Setting `allow_masked` to False will raise an exception if values are
    missing in either of the input arrays.

    Parameters
    ----------
    x : array_like
        A 1-D or 2-D array containing multiple variables and observations.
        Each row of `x` represents a variable, and each column a single
        observation of all those variables. Also see `rowvar` below.
    y : array_like, optional
        An additional set of variables and observations. `y` has the same
        shape as `x`.
    rowvar : bool, optional
        If `rowvar` is True (default), then each row represents a
        variable, with observations in the columns. Otherwise, the relationship
        is transposed: each column represents a variable, while the rows
        contain observations.
    bias : bool, optional
        Default normalization (False) is by ``(N-1)``, where ``N`` is the
        number of observations given (unbiased estimate). If `bias` is True,
        then normalization is by ``N``. This keyword can be overridden by
        the keyword ``ddof`` in numpy versions >= 1.5.
    allow_masked : bool, optional
        If True, masked values are propagated pair-wise: if a value is masked
        in `x`, the corresponding value is masked in `y`.
        If False, raises a `ValueError` exception when some values are missing.
    ddof : {None, int}, optional
        If not ``None`` normalization is by ``(N - ddof)``, where ``N`` is
        the number of observations; this overrides the value implied by
        ``bias``. The default value is ``None``.

    Raises
    ------
    ValueError
        Raised if some values are missing and `allow_masked` is False.

    See Also
    --------
    numpy.cov

    Examples
    --------
    >>> import numpy as np
    >>> x = np.ma.array([[0, 1], [1, 1]], mask=[0, 1, 0, 1])
    >>> y = np.ma.array([[1, 0], [0, 1]], mask=[0, 0, 1, 1])
    >>> np.ma.cov(x, y)
    masked_array(
    data=[[--, --, --, --],
          [--, --, --, --],
          [--, --, --, --],
          [--, --, --, --]],
    mask=[[ True,  True,  True,  True],
          [ True,  True,  True,  True],
          [ True,  True,  True,  True],
          [ True,  True,  True,  True]],
    fill_value=1e+20,
    dtype=float64)

    """
    # Check inputs
    if ddof is not None and ddof != int(ddof):
        raise ValueError("ddof must be an integer")
    # Set up ddof
    if ddof is None:
        if bias:
            ddof = 0
        else:
            ddof = 1

    (x, xnotmask, rowvar) = _covhelper(x, y, rowvar, allow_masked)
    if not rowvar:
        fact = np.dot(xnotmask.T, xnotmask) - ddof
        mask = np.less_equal(fact, 0, dtype=bool)
        with np.errstate(divide="ignore", invalid="ignore"):
            data = np.dot(filled(x.T, 0), filled(x.conj(), 0)) / fact
        result = ma.array(data, mask=mask).squeeze()
    else:
        fact = np.dot(xnotmask, xnotmask.T) - ddof
        mask = np.less_equal(fact, 0, dtype=bool)
        with np.errstate(divide="ignore", invalid="ignore"):
            data = np.dot(filled(x, 0), filled(x.T.conj(), 0)) / fact
        result = ma.array(data, mask=mask).squeeze()
    return result


def corrcoef(x, y=None, rowvar=True, bias=np._NoValue, allow_masked=True,
             ddof=np._NoValue):
    """
    Return Pearson product-moment correlation coefficients.

    Except for the handling of missing data this function does the same as
    `numpy.corrcoef`. For more details and examples, see `numpy.corrcoef`.

    Parameters
    ----------
    x : array_like
        A 1-D or 2-D array containing multiple variables and observations.
        Each row of `x` represents a variable, and each column a single
        observation of all those variables. Also see `rowvar` below.
    y : array_like, optional
        An additional set of variables and observations. `y` has the same
        shape as `x`.
    rowvar : bool, optional
        If `rowvar` is True (default), then each row represents a
        variable, with observations in the columns. Otherwise, the relationship
        is transposed: each column represents a variable, while the rows
        contain observations.
    bias : _NoValue, optional
        Has no effect, do not use.

        .. deprecated:: 1.10.0
    allow_masked : bool, optional
        If True, masked values are propagated pair-wise: if a value is masked
        in `x`, the corresponding value is masked in `y`.
        If False, raises an exception.  Because `bias` is deprecated, this
        argument needs to be treated as keyword only to avoid a warning.
    ddof : _NoValue, optional
        Has no effect, do not use.

        .. deprecated:: 1.10.0

    See Also
    --------
    numpy.corrcoef : Equivalent function in top-level NumPy module.
    cov : Estimate the covariance matrix.

    Notes
    -----
    This function accepts but discards arguments `bias` and `ddof`.  This is
    for backwards compatibility with previous versions of this function.  These
    arguments had no effect on the return values of the function and can be
    safely ignored in this and previous versions of numpy.

    Examples
    --------
    >>> import numpy as np
    >>> x = np.ma.array([[0, 1], [1, 1]], mask=[0, 1, 0, 1])
    >>> np.ma.corrcoef(x)
    masked_array(
      data=[[--, --],
            [--, --]],
      mask=[[ True,  True],
            [ True,  True]],
      fill_value=1e+20,
      dtype=float64)

    """
    msg = 'bias and ddof have no effect and are deprecated'
    if bias is not np._NoValue or ddof is not np._NoValue:
        # 2015-03-15, 1.10
        warnings.warn(msg, DeprecationWarning, stacklevel=2)
    # Estimate the covariance matrix.
    corr = cov(x, y, rowvar, allow_masked=allow_masked)
    # The non-masked version returns a masked value for a scalar.
    try:
        std = ma.sqrt(ma.diagonal(corr))
    except ValueError:
        return ma.MaskedConstant()
    corr /= ma.multiply.outer(std, std)
    return corr

#####--------------------------------------------------------------------------
#---- --- Concatenation helpers ---
#####--------------------------------------------------------------------------

class MAxisConcatenator(AxisConcatenator):
    """
    Translate slice objects to concatenation along an axis.

    For documentation on usage, see `mr_class`.

    See Also
    --------
    mr_class

    """
    __slots__ = ()

    concatenate = staticmethod(concatenate)

    @classmethod
    def makemat(cls, arr):
        # There used to be a view as np.matrix here, but we may eventually
        # deprecate that class. In preparation, we use the unmasked version
        # to construct the matrix (with copy=False for backwards compatibility
        # with the .view)
        data = super().makemat(arr.data, copy=False)
        return array(data, mask=arr.mask)

    def __getitem__(self, key):
        # matrix builder syntax, like 'a, b; c, d'
        if isinstance(key, str):
            raise MAError("Unavailable for masked array.")

        return super().__getitem__(key)


class mr_class(MAxisConcatenator):
    """
    Translate slice objects to concatenation along the first axis.

    This is the masked array version of `r_`.

    See Also
    --------
    r_

    Examples
    --------
    >>> import numpy as np
    >>> np.ma.mr_[np.ma.array([1,2,3]), 0, 0, np.ma.array([4,5,6])]
    masked_array(data=[1, 2, 3, ..., 4, 5, 6],
                 mask=False,
           fill_value=999999)

    """
    __slots__ = ()

    def __init__(self):
        MAxisConcatenator.__init__(self, 0)


mr_ = mr_class()


#####--------------------------------------------------------------------------
#---- Find unmasked data ---
#####--------------------------------------------------------------------------

def ndenumerate(a, compressed=True):
    """
    Multidimensional index iterator.

    Return an iterator yielding pairs of array coordinates and values,
    skipping elements that are masked. With `compressed=False`,
    `ma.masked` is yielded as the value of masked elements. This
    behavior differs from that of `numpy.ndenumerate`, which yields the
    value of the underlying data array.

    Notes
    -----
    .. versionadded:: 1.23.0

    Parameters
    ----------
    a : array_like
        An array with (possibly) masked elements.
    compressed : bool, optional
        If True (default), masked elements are skipped.

    See Also
    --------
    numpy.ndenumerate : Equivalent function ignoring any mask.

    Examples
    --------
    >>> import numpy as np
    >>> a = np.ma.arange(9).reshape((3, 3))
    >>> a[1, 0] = np.ma.masked
    >>> a[1, 2] = np.ma.masked
    >>> a[2, 1] = np.ma.masked
    >>> a
    masked_array(
      data=[[0, 1, 2],
            [--, 4, --],
            [6, --, 8]],
      mask=[[False, False, False],
            [ True, False,  True],
            [False,  True, False]],
      fill_value=999999)
    >>> for index, x in np.ma.ndenumerate(a):
    ...     print(index, x)
    (0, 0) 0
    (0, 1) 1
    (0, 2) 2
    (1, 1) 4
    (2, 0) 6
    (2, 2) 8

    >>> for index, x in np.ma.ndenumerate(a, compressed=False):
    ...     print(index, x)
    (0, 0) 0
    (0, 1) 1
    (0, 2) 2
    (1, 0) --
    (1, 1) 4
    (1, 2) --
    (2, 0) 6
    (2, 1) --
    (2, 2) 8
    """
    for it, mask in zip(np.ndenumerate(a), getmaskarray(a).flat):
        if not mask:
            yield it
        elif not compressed:
            yield it[0], masked


def flatnotmasked_edges(a):
    """
    Find the indices of the first and last unmasked values.

    Expects a 1-D `MaskedArray`, returns None if all values are masked.

    Parameters
    ----------
    a : array_like
        Input 1-D `MaskedArray`

    Returns
    -------
    edges : ndarray or None
        The indices of first and last non-masked value in the array.
        Returns None if all values are masked.

    See Also
    --------
    flatnotmasked_contiguous, notmasked_contiguous, notmasked_edges
    clump_masked, clump_unmasked

    Notes
    -----
    Only accepts 1-D arrays.

    Examples
    --------
    >>> import numpy as np
    >>> a = np.ma.arange(10)
    >>> np.ma.flatnotmasked_edges(a)
    array([0, 9])

    >>> mask = (a < 3) | (a > 8) | (a == 5)
    >>> a[mask] = np.ma.masked
    >>> np.array(a[~a.mask])
    array([3, 4, 6, 7, 8])

    >>> np.ma.flatnotmasked_edges(a)
    array([3, 8])

    >>> a[:] = np.ma.masked
    >>> print(np.ma.flatnotmasked_edges(a))
    None

    """
    m = getmask(a)
    if m is nomask or not np.any(m):
        return np.array([0, a.size - 1])
    unmasked = np.flatnonzero(~m)
    if len(unmasked) > 0:
        return unmasked[[0, -1]]
    else:
        return None


def notmasked_edges(a, axis=None):
    """
    Find the indices of the first and last unmasked values along an axis.

    If all values are masked, return None.  Otherwise, return a list
    of two tuples, corresponding to the indices of the first and last
    unmasked values respectively.

    Parameters
    ----------
    a : array_like
        The input array.
    axis : int, optional
        Axis along which to perform the operation.
        If None (default), applies to a flattened version of the array.

    Returns
    -------
    edges : ndarray or list
        An array of start and end indexes if there are any masked data in
        the array. If there are no masked data in the array, `edges` is a
        list of the first and last index.

    See Also
    --------
    flatnotmasked_contiguous, flatnotmasked_edges, notmasked_contiguous
    clump_masked, clump_unmasked

    Examples
    --------
    >>> import numpy as np
    >>> a = np.arange(9).reshape((3, 3))
    >>> m = np.zeros_like(a)
    >>> m[1:, 1:] = 1

    >>> am = np.ma.array(a, mask=m)
    >>> np.array(am[~am.mask])
    array([0, 1, 2, 3, 6])

    >>> np.ma.notmasked_edges(am)
    array([0, 6])

    """
    a = asarray(a)
    if axis is None or a.ndim == 1:
        return flatnotmasked_edges(a)
    m = getmaskarray(a)
    idx = array(np.indices(a.shape), mask=np.asarray([m] * a.ndim))
    return [tuple(idx[i].min(axis).compressed() for i in range(a.ndim)),
            tuple(idx[i].max(axis).compressed() for i in range(a.ndim)), ]


def flatnotmasked_contiguous(a):
    """
    Find contiguous unmasked data in a masked array.

    Parameters
    ----------
    a : array_like
        The input array.

    Returns
    -------
    slice_list : list
        A sorted sequence of `slice` objects (start index, end index).

    See Also
    --------
    flatnotmasked_edges, notmasked_contiguous, notmasked_edges
    clump_masked, clump_unmasked

    Notes
    -----
    Only accepts 2-D arrays at most.

    Examples
    --------
    >>> import numpy as np
    >>> a = np.ma.arange(10)
    >>> np.ma.flatnotmasked_contiguous(a)
    [slice(0, 10, None)]

    >>> mask = (a < 3) | (a > 8) | (a == 5)
    >>> a[mask] = np.ma.masked
    >>> np.array(a[~a.mask])
    array([3, 4, 6, 7, 8])

    >>> np.ma.flatnotmasked_contiguous(a)
    [slice(3, 5, None), slice(6, 9, None)]
    >>> a[:] = np.ma.masked
    >>> np.ma.flatnotmasked_contiguous(a)
    []

    """
    m = getmask(a)
    if m is nomask:
        return [slice(0, a.size)]
    i = 0
    result = []
    for (k, g) in itertools.groupby(m.ravel()):
        n = len(list(g))
        if not k:
            result.append(slice(i, i + n))
        i += n
    return result


def notmasked_contiguous(a, axis=None):
    """
    Find contiguous unmasked data in a masked array along the given axis.

    Parameters
    ----------
    a : array_like
        The input array.
    axis : int, optional
        Axis along which to perform the operation.
        If None (default), applies to a flattened version of the array, and this
        is the same as `flatnotmasked_contiguous`.

    Returns
    -------
    endpoints : list
        A list of slices (start and end indexes) of unmasked indexes
        in the array.

        If the input is 2d and axis is specified, the result is a list of lists.

    See Also
    --------
    flatnotmasked_edges, flatnotmasked_contiguous, notmasked_edges
    clump_masked, clump_unmasked

    Notes
    -----
    Only accepts 2-D arrays at most.

    Examples
    --------
    >>> import numpy as np
    >>> a = np.arange(12).reshape((3, 4))
    >>> mask = np.zeros_like(a)
    >>> mask[1:, :-1] = 1; mask[0, 1] = 1; mask[-1, 0] = 0
    >>> ma = np.ma.array(a, mask=mask)
    >>> ma
    masked_array(
      data=[[0, --, 2, 3],
            [--, --, --, 7],
            [8, --, --, 11]],
      mask=[[False,  True, False, False],
            [ True,  True,  True, False],
            [False,  True,  True, False]],
      fill_value=999999)
    >>> np.array(ma[~ma.mask])
    array([ 0,  2,  3,  7, 8, 11])

    >>> np.ma.notmasked_contiguous(ma)
    [slice(0, 1, None), slice(2, 4, None), slice(7, 9, None), slice(11, 12, None)]

    >>> np.ma.notmasked_contiguous(ma, axis=0)
    [[slice(0, 1, None), slice(2, 3, None)], [], [slice(0, 1, None)], [slice(0, 3, None)]]

    >>> np.ma.notmasked_contiguous(ma, axis=1)
    [[slice(0, 1, None), slice(2, 4, None)], [slice(3, 4, None)], [slice(0, 1, None), slice(3, 4, None)]]

    """  # noqa: E501
    a = asarray(a)
    nd = a.ndim
    if nd > 2:
        raise NotImplementedError("Currently limited to at most 2D array.")
    if axis is None or nd == 1:
        return flatnotmasked_contiguous(a)
    #
    result = []
    #
    other = (axis + 1) % 2
    idx = [0, 0]
    idx[axis] = slice(None, None)
    #
    for i in range(a.shape[other]):
        idx[other] = i
        result.append(flatnotmasked_contiguous(a[tuple(idx)]))
    return result


def _ezclump(mask):
    """
    Finds the clumps (groups of data with the same values) for a 1D bool array.

    Returns a series of slices.
    """
    if mask.ndim > 1:
        mask = mask.ravel()
    idx = (mask[1:] ^ mask[:-1]).nonzero()
    idx = idx[0] + 1

    if mask[0]:
        if len(idx) == 0:
            return [slice(0, mask.size)]

        r = [slice(0, idx[0])]
        r.extend((slice(left, right)
                  for left, right in zip(idx[1:-1:2], idx[2::2])))
    else:
        if len(idx) == 0:
            return []

        r = [slice(left, right) for left, right in zip(idx[:-1:2], idx[1::2])]

    if mask[-1]:
        r.append(slice(idx[-1], mask.size))
    return r


def clump_unmasked(a):
    """
    Return list of slices corresponding to the unmasked clumps of a 1-D array.
    (A "clump" is defined as a contiguous region of the array).

    Parameters
    ----------
    a : ndarray
        A one-dimensional masked array.

    Returns
    -------
    slices : list of slice
        The list of slices, one for each continuous region of unmasked
        elements in `a`.

    See Also
    --------
    flatnotmasked_edges, flatnotmasked_contiguous, notmasked_edges
    notmasked_contiguous, clump_masked

    Examples
    --------
    >>> import numpy as np
    >>> a = np.ma.masked_array(np.arange(10))
    >>> a[[0, 1, 2, 6, 8, 9]] = np.ma.masked
    >>> np.ma.clump_unmasked(a)
    [slice(3, 6, None), slice(7, 8, None)]

    """
    mask = getattr(a, '_mask', nomask)
    if mask is nomask:
        return [slice(0, a.size)]
    return _ezclump(~mask)


def clump_masked(a):
    """
    Returns a list of slices corresponding to the masked clumps of a 1-D array.
    (A "clump" is defined as a contiguous region of the array).

    Parameters
    ----------
    a : ndarray
        A one-dimensional masked array.

    Returns
    -------
    slices : list of slice
        The list of slices, one for each continuous region of masked elements
        in `a`.

    See Also
    --------
    flatnotmasked_edges, flatnotmasked_contiguous, notmasked_edges
    notmasked_contiguous, clump_unmasked

    Examples
    --------
    >>> import numpy as np
    >>> a = np.ma.masked_array(np.arange(10))
    >>> a[[0, 1, 2, 6, 8, 9]] = np.ma.masked
    >>> np.ma.clump_masked(a)
    [slice(0, 3, None), slice(6, 7, None), slice(8, 10, None)]

    """
    mask = ma.getmask(a)
    if mask is nomask:
        return []
    return _ezclump(mask)


###############################################################################
#                              Polynomial fit                                 #
###############################################################################


def vander(x, n=None):
    """
    Masked values in the input array result in rows of zeros.

    """
    _vander = np.vander(x, n)
    m = getmask(x)
    if m is not nomask:
        _vander[m] = 0
    return _vander


vander.__doc__ = ma.doc_note(np.vander.__doc__, vander.__doc__)


def polyfit(x, y, deg, rcond=None, full=False, w=None, cov=False):
    """
    Any masked values in x is propagated in y, and vice-versa.

    """
    x = asarray(x)
    y = asarray(y)

    m = getmask(x)
    if y.ndim == 1:
        m = mask_or(m, getmask(y))
    elif y.ndim == 2:
        my = getmask(mask_rows(y))
        if my is not nomask:
            m = mask_or(m, my[:, 0])
    else:
        raise TypeError("Expected a 1D or 2D array for y!")

    if w is not None:
        w = asarray(w)
        if w.ndim != 1:
            raise TypeError("expected a 1-d array for weights")
        if w.shape[0] != y.shape[0]:
            raise TypeError("expected w and y to have the same length")
        m = mask_or(m, getmask(w))

    if m is not nomask:
        not_m = ~m
        if w is not None:
            w = w[not_m]
        return np.polyfit(x[not_m], y[not_m], deg, rcond, full, w, cov)
    else:
        return np.polyfit(x, y, deg, rcond, full, w, cov)


polyfit.__doc__ = ma.doc_note(np.polyfit.__doc__, polyfit.__doc__)