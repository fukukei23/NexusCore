
# === NexusCore/tools\exports\export_20250803_114325\combined_138.py ===

# === NexusCore/openenv\Lib\site-packages\joblib\_parallel_backends.py ===
"""
Backends for embarrassingly parallel code.
"""

import contextlib
import gc
import os
import threading
import warnings
from abc import ABCMeta, abstractmethod

from ._multiprocessing_helpers import mp
from ._utils import (
    _retrieve_traceback_capturing_wrapped_call,
    _TracebackCapturingWrapper,
)

if mp is not None:
    from multiprocessing.pool import ThreadPool

    from .executor import get_memmapping_executor

    # Import loky only if multiprocessing is present
    from .externals.loky import cpu_count, process_executor
    from .externals.loky.process_executor import ShutdownExecutorError
    from .pool import MemmappingPool


class ParallelBackendBase(metaclass=ABCMeta):
    """Helper abc which defines all methods a ParallelBackend must implement"""

    default_n_jobs = 1

    supports_inner_max_num_threads = False

    # This flag was introduced for backward compatibility reasons.
    # New backends should always set it to True and implement the
    # `retrieve_result_callback` method.
    supports_retrieve_callback = False

    @property
    def supports_return_generator(self):
        return self.supports_retrieve_callback

    @property
    def supports_timeout(self):
        return self.supports_retrieve_callback

    nesting_level = None

    def __init__(
        self, nesting_level=None, inner_max_num_threads=None, **backend_kwargs
    ):
        super().__init__()
        self.nesting_level = nesting_level
        self.inner_max_num_threads = inner_max_num_threads
        self.backend_kwargs = backend_kwargs

    MAX_NUM_THREADS_VARS = [
        "OMP_NUM_THREADS",
        "OPENBLAS_NUM_THREADS",
        "MKL_NUM_THREADS",
        "BLIS_NUM_THREADS",
        "VECLIB_MAXIMUM_THREADS",
        "NUMBA_NUM_THREADS",
        "NUMEXPR_NUM_THREADS",
    ]

    TBB_ENABLE_IPC_VAR = "ENABLE_IPC"

    @abstractmethod
    def effective_n_jobs(self, n_jobs):
        """Determine the number of jobs that can actually run in parallel

        n_jobs is the number of workers requested by the callers. Passing
        n_jobs=-1 means requesting all available workers for instance matching
        the number of CPU cores on the worker host(s).

        This method should return a guesstimate of the number of workers that
        can actually perform work concurrently. The primary use case is to make
        it possible for the caller to know in how many chunks to slice the
        work.

        In general working on larger data chunks is more efficient (less
        scheduling overhead and better use of CPU cache prefetching heuristics)
        as long as all the workers have enough work to do.
        """

    def apply_async(self, func, callback=None):
        """Deprecated: implement `submit` instead."""
        raise NotImplementedError("Implement `submit` instead.")

    def submit(self, func, callback=None):
        """Schedule a function to be run and return a future-like object.

        This method should return a future-like object that allow tracking
        the progress of the task.

        If ``supports_retrieve_callback`` is False, the return value of this
        method is passed to ``retrieve_result`` instead of calling
        ``retrieve_result_callback``.

        Parameters
        ----------
        func: callable
            The function to be run in parallel.

        callback: callable
            A callable that will be called when the task is completed. This callable
            is a wrapper around ``retrieve_result_callback``. This should be added
            to the future-like object returned by this method, so that the callback
            is called when the task is completed.

            For future-like backends, this can be achieved with something like
            ``future.add_done_callback(callback)``.

        Returns
        -------
        future: future-like
            A future-like object to track the execution of the submitted function.
        """
        warnings.warn(
            "`apply_async` is deprecated, implement and use `submit` instead.",
            DeprecationWarning,
        )
        return self.apply_async(func, callback)

    def retrieve_result_callback(self, out):
        """Called within the callback function passed to `submit`.

        This method can customise how the result of the function is retrieved
        from the future-like object.

        Parameters
        ----------
        future: future-like
            The future-like object returned by the `submit` method.

        Returns
        -------
        result: object
            The result of the function executed in parallel.
        """

    def retrieve_result(self, out, timeout=None):
        """Hook to retrieve the result when support_retrieve_callback=False.

        The argument `out` is the result of the `submit` call. This method
        should return the result of the computation or raise an exception if
        the computation failed.
        """
        if self.supports_timeout:
            return out.get(timeout=timeout)
        else:
            return out.get()

    def configure(
        self, n_jobs=1, parallel=None, prefer=None, require=None, **backend_kwargs
    ):
        """Reconfigure the backend and return the number of workers.

        This makes it possible to reuse an existing backend instance for
        successive independent calls to Parallel with different parameters.
        """
        self.parallel = parallel
        return self.effective_n_jobs(n_jobs)

    def start_call(self):
        """Call-back method called at the beginning of a Parallel call"""

    def stop_call(self):
        """Call-back method called at the end of a Parallel call"""

    def terminate(self):
        """Shutdown the workers and free the shared memory."""

    def compute_batch_size(self):
        """Determine the optimal batch size"""
        return 1

    def batch_completed(self, batch_size, duration):
        """Callback indicate how long it took to run a batch"""

    def abort_everything(self, ensure_ready=True):
        """Abort any running tasks

        This is called when an exception has been raised when executing a task
        and all the remaining tasks will be ignored and can therefore be
        aborted to spare computation resources.

        If ensure_ready is True, the backend should be left in an operating
        state as future tasks might be re-submitted via that same backend
        instance.

        If ensure_ready is False, the implementer of this method can decide
        to leave the backend in a closed / terminated state as no new task
        are expected to be submitted to this backend.

        Setting ensure_ready to False is an optimization that can be leveraged
        when aborting tasks via killing processes from a local process pool
        managed by the backend it-self: if we expect no new tasks, there is no
        point in re-creating new workers.
        """
        # Does nothing by default: to be overridden in subclasses when
        # canceling tasks is possible.
        pass

    def get_nested_backend(self):
        """Backend instance to be used by nested Parallel calls.

        By default a thread-based backend is used for the first level of
        nesting. Beyond, switch to sequential backend to avoid spawning too
        many threads on the host.
        """
        nesting_level = getattr(self, "nesting_level", 0) + 1
        if nesting_level > 1:
            return SequentialBackend(nesting_level=nesting_level), None
        else:
            return ThreadingBackend(nesting_level=nesting_level), None

    def _prepare_worker_env(self, n_jobs):
        """Return environment variables limiting threadpools in external libs.

        This function return a dict containing environment variables to pass
        when creating a pool of process. These environment variables limit the
        number of threads to `n_threads` for OpenMP, MKL, Accelerated and
        OpenBLAS libraries in the child processes.
        """
        explicit_n_threads = self.inner_max_num_threads
        default_n_threads = max(cpu_count() // n_jobs, 1)

        # Set the inner environment variables to self.inner_max_num_threads if
        # it is given. Else, default to cpu_count // n_jobs unless the variable
        # is already present in the parent process environment.
        env = {}
        for var in self.MAX_NUM_THREADS_VARS:
            if explicit_n_threads is None:
                var_value = os.environ.get(var, default_n_threads)
            else:
                var_value = explicit_n_threads

            env[var] = str(var_value)

        if self.TBB_ENABLE_IPC_VAR not in os.environ:
            # To avoid over-subscription when using TBB, let the TBB schedulers
            # use Inter Process Communication to coordinate:
            env[self.TBB_ENABLE_IPC_VAR] = "1"
        return env

    @contextlib.contextmanager
    def retrieval_context(self):
        """Context manager to manage an execution context.

        Calls to Parallel.retrieve will be made inside this context.

        By default, this does nothing. It may be useful for subclasses to
        handle nested parallelism. In particular, it may be required to avoid
        deadlocks if a backend manages a fixed number of workers, when those
        workers may be asked to do nested Parallel calls. Without
        'retrieval_context' this could lead to deadlock, as all the workers
        managed by the backend may be "busy" waiting for the nested parallel
        calls to finish, but the backend has no free workers to execute those
        tasks.
        """
        yield

    @staticmethod
    def in_main_thread():
        return isinstance(threading.current_thread(), threading._MainThread)


class SequentialBackend(ParallelBackendBase):
    """A ParallelBackend which will execute all batches sequentially.

    Does not use/create any threading objects, and hence has minimal
    overhead. Used when n_jobs == 1.
    """

    uses_threads = True
    supports_timeout = False
    supports_retrieve_callback = False
    supports_sharedmem = True

    def effective_n_jobs(self, n_jobs):
        """Determine the number of jobs which are going to run in parallel"""
        if n_jobs == 0:
            raise ValueError("n_jobs == 0 in Parallel has no meaning")
        return 1

    def submit(self, func, callback=None):
        """Schedule a func to be run"""
        raise RuntimeError("Should never be called for SequentialBackend.")

    def retrieve_result_callback(self, out):
        raise RuntimeError("Should never be called for SequentialBackend.")

    def get_nested_backend(self):
        # import is not top level to avoid cyclic import errors.
        from .parallel import get_active_backend

        # SequentialBackend should neither change the nesting level, the
        # default backend or the number of jobs. Just return the current one.
        return get_active_backend()


class PoolManagerMixin(object):
    """A helper class for managing pool of workers."""

    _pool = None

    def effective_n_jobs(self, n_jobs):
        """Determine the number of jobs which are going to run in parallel"""
        if n_jobs == 0:
            raise ValueError("n_jobs == 0 in Parallel has no meaning")
        elif mp is None or n_jobs is None:
            # multiprocessing is not available or disabled, fallback
            # to sequential mode
            return 1
        elif n_jobs < 0:
            n_jobs = max(cpu_count() + 1 + n_jobs, 1)
        return n_jobs

    def terminate(self):
        """Shutdown the process or thread pool"""
        if self._pool is not None:
            self._pool.close()
            self._pool.terminate()  # terminate does a join()
            self._pool = None

    def _get_pool(self):
        """Used by `submit` to make it possible to implement lazy init"""
        return self._pool

    def submit(self, func, callback=None):
        """Schedule a func to be run"""
        # Here, we need a wrapper to avoid crashes on KeyboardInterruptErrors.
        # We also call the callback on error, to make sure the pool does not
        # wait on crashed jobs.
        return self._get_pool().apply_async(
            _TracebackCapturingWrapper(func),
            (),
            callback=callback,
            error_callback=callback,
        )

    def retrieve_result_callback(self, result):
        """Mimic concurrent.futures results, raising an error if needed."""
        # In the multiprocessing Pool API, the callback are called with the
        # result value as an argument so `result`(`out`) is the output of
        # job.get(). It's either the result or the exception raised while
        # collecting the result.
        return _retrieve_traceback_capturing_wrapped_call(result)

    def abort_everything(self, ensure_ready=True):
        """Shutdown the pool and restart a new one with the same parameters"""
        self.terminate()
        if ensure_ready:
            self.configure(
                n_jobs=self.parallel.n_jobs,
                parallel=self.parallel,
                **self.parallel._backend_kwargs,
            )


class AutoBatchingMixin(object):
    """A helper class for automagically batching jobs."""

    # In seconds, should be big enough to hide multiprocessing dispatching
    # overhead.
    # This settings was found by running benchmarks/bench_auto_batching.py
    # with various parameters on various platforms.
    MIN_IDEAL_BATCH_DURATION = 0.2

    # Should not be too high to avoid stragglers: long jobs running alone
    # on a single worker while other workers have no work to process any more.
    MAX_IDEAL_BATCH_DURATION = 2

    # Batching counters default values
    _DEFAULT_EFFECTIVE_BATCH_SIZE = 1
    _DEFAULT_SMOOTHED_BATCH_DURATION = 0.0

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._effective_batch_size = self._DEFAULT_EFFECTIVE_BATCH_SIZE
        self._smoothed_batch_duration = self._DEFAULT_SMOOTHED_BATCH_DURATION

    def compute_batch_size(self):
        """Determine the optimal batch size"""
        old_batch_size = self._effective_batch_size
        batch_duration = self._smoothed_batch_duration
        if batch_duration > 0 and batch_duration < self.MIN_IDEAL_BATCH_DURATION:
            # The current batch size is too small: the duration of the
            # processing of a batch of task is not large enough to hide
            # the scheduling overhead.
            ideal_batch_size = int(
                old_batch_size * self.MIN_IDEAL_BATCH_DURATION / batch_duration
            )
            # Multiply by two to limit oscilations between min and max.
            ideal_batch_size *= 2

            # dont increase the batch size too fast to limit huge batch sizes
            # potentially leading to starving worker
            batch_size = min(2 * old_batch_size, ideal_batch_size)

            batch_size = max(batch_size, 1)

            self._effective_batch_size = batch_size
            if self.parallel.verbose >= 10:
                self.parallel._print(
                    f"Batch computation too fast ({batch_duration}s.) "
                    f"Setting batch_size={batch_size}."
                )
        elif batch_duration > self.MAX_IDEAL_BATCH_DURATION and old_batch_size >= 2:
            # The current batch size is too big. If we schedule overly long
            # running batches some CPUs might wait with nothing left to do
            # while a couple of CPUs a left processing a few long running
            # batches. Better reduce the batch size a bit to limit the
            # likelihood of scheduling such stragglers.

            # decrease the batch size quickly to limit potential starving
            ideal_batch_size = int(
                old_batch_size * self.MIN_IDEAL_BATCH_DURATION / batch_duration
            )
            # Multiply by two to limit oscilations between min and max.
            batch_size = max(2 * ideal_batch_size, 1)
            self._effective_batch_size = batch_size
            if self.parallel.verbose >= 10:
                self.parallel._print(
                    f"Batch computation too slow ({batch_duration}s.) "
                    f"Setting batch_size={batch_size}."
                )
        else:
            # No batch size adjustment
            batch_size = old_batch_size

        if batch_size != old_batch_size:
            # Reset estimation of the smoothed mean batch duration: this
            # estimate is updated in the multiprocessing apply_async
            # CallBack as long as the batch_size is constant. Therefore
            # we need to reset the estimate whenever we re-tune the batch
            # size.
            self._smoothed_batch_duration = self._DEFAULT_SMOOTHED_BATCH_DURATION

        return batch_size

    def batch_completed(self, batch_size, duration):
        """Callback indicate how long it took to run a batch"""
        if batch_size == self._effective_batch_size:
            # Update the smoothed streaming estimate of the duration of a batch
            # from dispatch to completion
            old_duration = self._smoothed_batch_duration
            if old_duration == self._DEFAULT_SMOOTHED_BATCH_DURATION:
                # First record of duration for this batch size after the last
                # reset.
                new_duration = duration
            else:
                # Update the exponentially weighted average of the duration of
                # batch for the current effective size.
                new_duration = 0.8 * old_duration + 0.2 * duration
            self._smoothed_batch_duration = new_duration

    def reset_batch_stats(self):
        """Reset batch statistics to default values.

        This avoids interferences with future jobs.
        """
        self._effective_batch_size = self._DEFAULT_EFFECTIVE_BATCH_SIZE
        self._smoothed_batch_duration = self._DEFAULT_SMOOTHED_BATCH_DURATION


class ThreadingBackend(PoolManagerMixin, ParallelBackendBase):
    """A ParallelBackend which will use a thread pool to execute batches in.

    This is a low-overhead backend but it suffers from the Python Global
    Interpreter Lock if the called function relies a lot on Python objects.
    Mostly useful when the execution bottleneck is a compiled extension that
    explicitly releases the GIL (for instance a Cython loop wrapped in a "with
    nogil" block or an expensive call to a library such as NumPy).

    The actual thread pool is lazily initialized: the actual thread pool
    construction is delayed to the first call to apply_async.

    ThreadingBackend is used as the default backend for nested calls.
    """

    supports_retrieve_callback = True
    uses_threads = True
    supports_sharedmem = True

    def configure(self, n_jobs=1, parallel=None, **backend_kwargs):
        """Build a process or thread pool and return the number of workers"""
        n_jobs = self.effective_n_jobs(n_jobs)
        if n_jobs == 1:
            # Avoid unnecessary overhead and use sequential backend instead.
            raise FallbackToBackend(SequentialBackend(nesting_level=self.nesting_level))
        self.parallel = parallel
        self._n_jobs = n_jobs
        return n_jobs

    def _get_pool(self):
        """Lazily initialize the thread pool

        The actual pool of worker threads is only initialized at the first
        call to apply_async.
        """
        if self._pool is None:
            self._pool = ThreadPool(self._n_jobs)
        return self._pool


class MultiprocessingBackend(PoolManagerMixin, AutoBatchingMixin, ParallelBackendBase):
    """A ParallelBackend which will use a multiprocessing.Pool.

    Will introduce some communication and memory overhead when exchanging
    input and output data with the with the worker Python processes.
    However, does not suffer from the Python Global Interpreter Lock.
    """

    supports_retrieve_callback = True
    supports_return_generator = False

    def effective_n_jobs(self, n_jobs):
        """Determine the number of jobs which are going to run in parallel.

        This also checks if we are attempting to create a nested parallel
        loop.
        """
        if mp is None:
            return 1

        if mp.current_process().daemon:
            # Daemonic processes cannot have children
            if n_jobs != 1:
                if inside_dask_worker():
                    msg = (
                        "Inside a Dask worker with daemon=True, "
                        "setting n_jobs=1.\nPossible work-arounds:\n"
                        "- dask.config.set("
                        "{'distributed.worker.daemon': False})"
                        "- set the environment variable "
                        "DASK_DISTRIBUTED__WORKER__DAEMON=False\n"
                        "before creating your Dask cluster."
                    )
                else:
                    msg = (
                        "Multiprocessing-backed parallel loops "
                        "cannot be nested, setting n_jobs=1"
                    )
                warnings.warn(msg, stacklevel=3)
            return 1

        if process_executor._CURRENT_DEPTH > 0:
            # Mixing loky and multiprocessing in nested loop is not supported
            if n_jobs != 1:
                warnings.warn(
                    "Multiprocessing-backed parallel loops cannot be nested,"
                    " below loky, setting n_jobs=1",
                    stacklevel=3,
                )
            return 1

        elif not (self.in_main_thread() or self.nesting_level == 0):
            # Prevent posix fork inside in non-main posix threads
            if n_jobs != 1:
                warnings.warn(
                    "Multiprocessing-backed parallel loops cannot be nested"
                    " below threads, setting n_jobs=1",
                    stacklevel=3,
                )
            return 1

        return super(MultiprocessingBackend, self).effective_n_jobs(n_jobs)

    def configure(
        self,
        n_jobs=1,
        parallel=None,
        prefer=None,
        require=None,
        **memmapping_pool_kwargs,
    ):
        """Build a process or thread pool and return the number of workers"""
        n_jobs = self.effective_n_jobs(n_jobs)
        if n_jobs == 1:
            raise FallbackToBackend(SequentialBackend(nesting_level=self.nesting_level))

        memmapping_pool_kwargs = {
            **self.backend_kwargs,
            **memmapping_pool_kwargs,
        }

        # Make sure to free as much memory as possible before forking
        gc.collect()
        self._pool = MemmappingPool(n_jobs, **memmapping_pool_kwargs)
        self.parallel = parallel
        return n_jobs

    def terminate(self):
        """Shutdown the process or thread pool"""
        super(MultiprocessingBackend, self).terminate()
        self.reset_batch_stats()


class LokyBackend(AutoBatchingMixin, ParallelBackendBase):
    """Managing pool of workers with loky instead of multiprocessing."""

    supports_retrieve_callback = True
    supports_inner_max_num_threads = True

    def configure(
        self,
        n_jobs=1,
        parallel=None,
        prefer=None,
        require=None,
        idle_worker_timeout=None,
        **memmapping_executor_kwargs,
    ):
        """Build a process executor and return the number of workers"""
        n_jobs = self.effective_n_jobs(n_jobs)
        if n_jobs == 1:
            raise FallbackToBackend(SequentialBackend(nesting_level=self.nesting_level))

        memmapping_executor_kwargs = {
            **self.backend_kwargs,
            **memmapping_executor_kwargs,
        }

        # Prohibit the use of 'timeout' in the LokyBackend, as 'idle_worker_timeout'
        # better describes the backend's behavior.
        if "timeout" in memmapping_executor_kwargs:
            raise ValueError(
                "The 'timeout' parameter is not supported by the LokyBackend. "
                "Please use the `idle_worker_timeout` parameter instead."
            )
        if idle_worker_timeout is None:
            idle_worker_timeout = self.backend_kwargs.get("idle_worker_timeout", 300)

        self._workers = get_memmapping_executor(
            n_jobs,
            timeout=idle_worker_timeout,
            env=self._prepare_worker_env(n_jobs=n_jobs),
            context_id=parallel._id,
            **memmapping_executor_kwargs,
        )
        self.parallel = parallel
        return n_jobs

    def effective_n_jobs(self, n_jobs):
        """Determine the number of jobs which are going to run in parallel"""
        if n_jobs == 0:
            raise ValueError("n_jobs == 0 in Parallel has no meaning")
        elif mp is None or n_jobs is None:
            # multiprocessing is not available or disabled, fallback
            # to sequential mode
            return 1
        elif mp.current_process().daemon:
            # Daemonic processes cannot have children
            if n_jobs != 1:
                if inside_dask_worker():
                    msg = (
                        "Inside a Dask worker with daemon=True, "
                        "setting n_jobs=1.\nPossible work-arounds:\n"
                        "- dask.config.set("
                        "{'distributed.worker.daemon': False})\n"
                        "- set the environment variable "
                        "DASK_DISTRIBUTED__WORKER__DAEMON=False\n"
                        "before creating your Dask cluster."
                    )
                else:
                    msg = (
                        "Loky-backed parallel loops cannot be called in a"
                        " multiprocessing, setting n_jobs=1"
                    )
                warnings.warn(msg, stacklevel=3)

            return 1
        elif not (self.in_main_thread() or self.nesting_level == 0):
            # Prevent posix fork inside in non-main posix threads
            if n_jobs != 1:
                warnings.warn(
                    "Loky-backed parallel loops cannot be nested below "
                    "threads, setting n_jobs=1",
                    stacklevel=3,
                )
            return 1
        elif n_jobs < 0:
            n_jobs = max(cpu_count() + 1 + n_jobs, 1)
        return n_jobs

    def submit(self, func, callback=None):
        """Schedule a func to be run"""
        future = self._workers.submit(func)
        if callback is not None:
            future.add_done_callback(callback)
        return future

    def retrieve_result_callback(self, future):
        """Retrieve the result, here out is the future given by submit"""
        try:
            return future.result()
        except ShutdownExecutorError:
            raise RuntimeError(
                "The executor underlying Parallel has been shutdown. "
                "This is likely due to the garbage collection of a previous "
                "generator from a call to Parallel with return_as='generator'."
                " Make sure the generator is not garbage collected when "
                "submitting a new job or that it is first properly exhausted."
            )

    def terminate(self):
        if self._workers is not None:
            # Don't terminate the workers as we want to reuse them in later
            # calls, but cleanup the temporary resources that the Parallel call
            # created. This 'hack' requires a private, low-level operation.
            self._workers._temp_folder_manager._clean_temporary_resources(
                context_id=self.parallel._id, force=False
            )
            self._workers = None

        self.reset_batch_stats()

    def abort_everything(self, ensure_ready=True):
        """Shutdown the workers and restart a new one with the same parameters"""
        self._workers.terminate(kill_workers=True)
        self._workers = None

        if ensure_ready:
            self.configure(n_jobs=self.parallel.n_jobs, parallel=self.parallel)


class FallbackToBackend(Exception):
    """Raised when configuration should fallback to another backend"""

    def __init__(self, backend):
        self.backend = backend


def inside_dask_worker():
    """Check whether the current function is executed inside a Dask worker."""
    # This function can not be in joblib._dask because there would be a
    # circular import:
    # _dask imports _parallel_backend that imports _dask ...
    try:
        from distributed import get_worker
    except ImportError:
        return False

    try:
        get_worker()
        return True
    except ValueError:
        return False

# === NexusCore/openenv\Lib\site-packages\debugpy\_vendored\pydevd\pydevd_attach_to_process\winappdbg\window.py ===
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
Window instrumentation.

@group Instrumentation:
    Window
"""

__revision__ = "$Id$"

__all__ = ["Window"]

from winappdbg import win32

# delayed imports
Process = None
Thread = None

# ==============================================================================

# Unlike Process, Thread and Module, there's no container for Window objects.
# That's because Window objects don't really store any data besides the handle.

# XXX TODO
# * implement sending fake user input (mouse and keyboard messages)
# * maybe implement low-level hooks? (they don't require a dll to be injected)

# XXX TODO
#
# Will it be possible to implement window hooks too? That requires a DLL to be
# injected in the target process. Perhaps with CPython it could be done easier,
# compiling a native extension is the safe bet, but both require having a non
# pure Python module, which is something I was trying to avoid so far.
#
# Another possibility would be to malloc some CC's in the target process and
# point the hook callback to it. We'd need to have the remote procedure call
# feature first as (I believe) the hook can't be set remotely in this case.


class Window(object):
    """
    Interface to an open window in the current desktop.

    @group Properties:
        get_handle, get_pid, get_tid,
        get_process, get_thread,
        set_process, set_thread,
        get_classname, get_style, get_extended_style,
        get_text, set_text,
        get_placement, set_placement,
        get_screen_rect, get_client_rect,
        screen_to_client, client_to_screen

    @group State:
        is_valid, is_visible, is_enabled, is_maximized, is_minimized, is_child,
        is_zoomed, is_iconic

    @group Navigation:
        get_parent, get_children, get_root, get_tree,
        get_child_at

    @group Instrumentation:
        enable, disable, show, hide, maximize, minimize, restore, move, kill

    @group Low-level access:
        send, post

    @type hWnd: int
    @ivar hWnd: Window handle.

    @type dwProcessId: int
    @ivar dwProcessId: Global ID of the process that owns this window.

    @type dwThreadId: int
    @ivar dwThreadId: Global ID of the thread that owns this window.

    @type process: L{Process}
    @ivar process: Process that owns this window.
        Use the L{get_process} method instead.

    @type thread: L{Thread}
    @ivar thread: Thread that owns this window.
        Use the L{get_thread} method instead.

    @type classname: str
    @ivar classname: Window class name.

    @type text: str
    @ivar text: Window text (caption).

    @type placement: L{win32.WindowPlacement}
    @ivar placement: Window placement in the desktop.
    """

    def __init__(self, hWnd=None, process=None, thread=None):
        """
        @type  hWnd: int or L{win32.HWND}
        @param hWnd: Window handle.

        @type  process: L{Process}
        @param process: (Optional) Process that owns this window.

        @type  thread: L{Thread}
        @param thread: (Optional) Thread that owns this window.
        """
        self.hWnd = hWnd
        self.dwProcessId = None
        self.dwThreadId = None
        self.set_process(process)
        self.set_thread(thread)

    @property
    def _as_parameter_(self):
        """
        Compatibility with ctypes.
        Allows passing transparently a Window object to an API call.
        """
        return self.get_handle()

    def get_handle(self):
        """
        @rtype:  int
        @return: Window handle.
        @raise ValueError: No window handle set.
        """
        if self.hWnd is None:
            raise ValueError("No window handle set!")
        return self.hWnd

    def get_pid(self):
        """
        @rtype:  int
        @return: Global ID of the process that owns this window.
        """
        if self.dwProcessId is not None:
            return self.dwProcessId
        self.__get_pid_and_tid()
        return self.dwProcessId

    def get_tid(self):
        """
        @rtype:  int
        @return: Global ID of the thread that owns this window.
        """
        if self.dwThreadId is not None:
            return self.dwThreadId
        self.__get_pid_and_tid()
        return self.dwThreadId

    def __get_pid_and_tid(self):
        "Internally used by get_pid() and get_tid()."
        self.dwThreadId, self.dwProcessId = win32.GetWindowThreadProcessId(self.get_handle())

    def __load_Process_class(self):
        global Process  # delayed import
        if Process is None:
            from winappdbg.process import Process

    def __load_Thread_class(self):
        global Thread  # delayed import
        if Thread is None:
            from winappdbg.thread import Thread

    def get_process(self):
        """
        @rtype:  L{Process}
        @return: Parent Process object.
        """
        if self.__process is not None:
            return self.__process
        self.__load_Process_class()
        self.__process = Process(self.get_pid())
        return self.__process

    def set_process(self, process=None):
        """
        Manually set the parent process. Use with care!

        @type  process: L{Process}
        @param process: (Optional) Process object. Use C{None} to autodetect.
        """
        if process is None:
            self.__process = None
        else:
            self.__load_Process_class()
            if not isinstance(process, Process):
                msg = "Parent process must be a Process instance, "
                msg += "got %s instead" % type(process)
                raise TypeError(msg)
            self.dwProcessId = process.get_pid()
            self.__process = process

    def get_thread(self):
        """
        @rtype:  L{Thread}
        @return: Parent Thread object.
        """
        if self.__thread is not None:
            return self.__thread
        self.__load_Thread_class()
        self.__thread = Thread(self.get_tid())
        return self.__thread

    def set_thread(self, thread=None):
        """
        Manually set the thread process. Use with care!

        @type  thread: L{Thread}
        @param thread: (Optional) Thread object. Use C{None} to autodetect.
        """
        if thread is None:
            self.__thread = None
        else:
            self.__load_Thread_class()
            if not isinstance(thread, Thread):
                msg = "Parent thread must be a Thread instance, "
                msg += "got %s instead" % type(thread)
                raise TypeError(msg)
            self.dwThreadId = thread.get_tid()
            self.__thread = thread

    def __get_window(self, hWnd):
        """
        User internally to get another Window from this one.
        It'll try to copy the parent Process and Thread references if possible.
        """
        window = Window(hWnd)
        if window.get_pid() == self.get_pid():
            window.set_process(self.get_process())
        if window.get_tid() == self.get_tid():
            window.set_thread(self.get_thread())
        return window

    # ------------------------------------------------------------------------------

    def get_classname(self):
        """
        @rtype:  str
        @return: Window class name.

        @raise WindowsError: An error occured while processing this request.
        """
        return win32.GetClassName(self.get_handle())

    def get_style(self):
        """
        @rtype:  int
        @return: Window style mask.

        @raise WindowsError: An error occured while processing this request.
        """
        return win32.GetWindowLongPtr(self.get_handle(), win32.GWL_STYLE)

    def get_extended_style(self):
        """
        @rtype:  int
        @return: Window extended style mask.

        @raise WindowsError: An error occured while processing this request.
        """
        return win32.GetWindowLongPtr(self.get_handle(), win32.GWL_EXSTYLE)

    def get_text(self):
        """
        @see:    L{set_text}
        @rtype:  str
        @return: Window text (caption) on success, C{None} on error.
        """
        try:
            return win32.GetWindowText(self.get_handle())
        except WindowsError:
            return None

    def set_text(self, text):
        """
        Set the window text (caption).

        @see: L{get_text}

        @type  text: str
        @param text: New window text.

        @raise WindowsError: An error occured while processing this request.
        """
        win32.SetWindowText(self.get_handle(), text)

    def get_placement(self):
        """
        Retrieve the window placement in the desktop.

        @see: L{set_placement}

        @rtype:  L{win32.WindowPlacement}
        @return: Window placement in the desktop.

        @raise WindowsError: An error occured while processing this request.
        """
        return win32.GetWindowPlacement(self.get_handle())

    def set_placement(self, placement):
        """
        Set the window placement in the desktop.

        @see: L{get_placement}

        @type  placement: L{win32.WindowPlacement}
        @param placement: Window placement in the desktop.

        @raise WindowsError: An error occured while processing this request.
        """
        win32.SetWindowPlacement(self.get_handle(), placement)

    def get_screen_rect(self):
        """
        Get the window coordinates in the desktop.

        @rtype:  L{win32.Rect}
        @return: Rectangle occupied by the window in the desktop.

        @raise WindowsError: An error occured while processing this request.
        """
        return win32.GetWindowRect(self.get_handle())

    def get_client_rect(self):
        """
        Get the window's client area coordinates in the desktop.

        @rtype:  L{win32.Rect}
        @return: Rectangle occupied by the window's client area in the desktop.

        @raise WindowsError: An error occured while processing this request.
        """
        cr = win32.GetClientRect(self.get_handle())
        cr.left, cr.top = self.client_to_screen(cr.left, cr.top)
        cr.right, cr.bottom = self.client_to_screen(cr.right, cr.bottom)
        return cr

    # XXX TODO
    # * properties x, y, width, height
    # * properties left, top, right, bottom

    process = property(get_process, set_process, doc="")
    thread = property(get_thread, set_thread, doc="")
    classname = property(get_classname, doc="")
    style = property(get_style, doc="")
    exstyle = property(get_extended_style, doc="")
    text = property(get_text, set_text, doc="")
    placement = property(get_placement, set_placement, doc="")

    # ------------------------------------------------------------------------------

    def client_to_screen(self, x, y):
        """
        Translates window client coordinates to screen coordinates.

        @note: This is a simplified interface to some of the functionality of
            the L{win32.Point} class.

        @see: {win32.Point.client_to_screen}

        @type  x: int
        @param x: Horizontal coordinate.
        @type  y: int
        @param y: Vertical coordinate.

        @rtype:  tuple( int, int )
        @return: Translated coordinates in a tuple (x, y).

        @raise WindowsError: An error occured while processing this request.
        """
        return tuple(win32.ClientToScreen(self.get_handle(), (x, y)))

    def screen_to_client(self, x, y):
        """
        Translates window screen coordinates to client coordinates.

        @note: This is a simplified interface to some of the functionality of
            the L{win32.Point} class.

        @see: {win32.Point.screen_to_client}

        @type  x: int
        @param x: Horizontal coordinate.
        @type  y: int
        @param y: Vertical coordinate.

        @rtype:  tuple( int, int )
        @return: Translated coordinates in a tuple (x, y).

        @raise WindowsError: An error occured while processing this request.
        """
        return tuple(win32.ScreenToClient(self.get_handle(), (x, y)))

    # ------------------------------------------------------------------------------

    def get_parent(self):
        """
        @see:    L{get_children}
        @rtype:  L{Window} or None
        @return: Parent window. Returns C{None} if the window has no parent.
        @raise WindowsError: An error occured while processing this request.
        """
        hWnd = win32.GetParent(self.get_handle())
        if hWnd:
            return self.__get_window(hWnd)

    def get_children(self):
        """
        @see:    L{get_parent}
        @rtype:  list( L{Window} )
        @return: List of child windows.
        @raise WindowsError: An error occured while processing this request.
        """
        return [self.__get_window(hWnd) for hWnd in win32.EnumChildWindows(self.get_handle())]

    def get_tree(self):
        """
        @see:    L{get_root}
        @rtype:  dict( L{Window} S{->} dict( ... ) )
        @return: Dictionary of dictionaries forming a tree of child windows.
        @raise WindowsError: An error occured while processing this request.
        """
        subtree = dict()
        for aWindow in self.get_children():
            subtree[aWindow] = aWindow.get_tree()
        return subtree

    def get_root(self):
        """
        @see:    L{get_tree}
        @rtype:  L{Window}
        @return: If this is a child window, return the top-level window it
            belongs to.
            If this window is already a top-level window, returns itself.
        @raise WindowsError: An error occured while processing this request.
        """
        hWnd = self.get_handle()
        history = set()
        hPrevWnd = hWnd
        while hWnd and hWnd not in history:
            history.add(hWnd)
            hPrevWnd = hWnd
            hWnd = win32.GetParent(hWnd)
        if hWnd in history:
            # See: https://docs.google.com/View?id=dfqd62nk_228h28szgz
            return self
        if hPrevWnd != self.get_handle():
            return self.__get_window(hPrevWnd)
        return self

    def get_child_at(self, x, y, bAllowTransparency=True):
        """
        Get the child window located at the given coordinates. If no such
        window exists an exception is raised.

        @see: L{get_children}

        @type  x: int
        @param x: Horizontal coordinate.

        @type  y: int
        @param y: Vertical coordinate.

        @type  bAllowTransparency: bool
        @param bAllowTransparency: If C{True} transparent areas in windows are
            ignored, returning the window behind them. If C{False} transparent
            areas are treated just like any other area.

        @rtype:  L{Window}
        @return: Child window at the requested position, or C{None} if there
            is no window at those coordinates.
        """
        try:
            if bAllowTransparency:
                hWnd = win32.RealChildWindowFromPoint(self.get_handle(), (x, y))
            else:
                hWnd = win32.ChildWindowFromPoint(self.get_handle(), (x, y))
            if hWnd:
                return self.__get_window(hWnd)
        except WindowsError:
            pass
        return None

    # ------------------------------------------------------------------------------

    def is_valid(self):
        """
        @rtype:  bool
        @return: C{True} if the window handle is still valid.
        """
        return win32.IsWindow(self.get_handle())

    def is_visible(self):
        """
        @see: {show}, {hide}
        @rtype:  bool
        @return: C{True} if the window is in a visible state.
        """
        return win32.IsWindowVisible(self.get_handle())

    def is_enabled(self):
        """
        @see: {enable}, {disable}
        @rtype:  bool
        @return: C{True} if the window is in an enabled state.
        """
        return win32.IsWindowEnabled(self.get_handle())

    def is_maximized(self):
        """
        @see: L{maximize}
        @rtype:  bool
        @return: C{True} if the window is maximized.
        """
        return win32.IsZoomed(self.get_handle())

    def is_minimized(self):
        """
        @see: L{minimize}
        @rtype:  bool
        @return: C{True} if the window is minimized.
        """
        return win32.IsIconic(self.get_handle())

    def is_child(self):
        """
        @see: L{get_parent}
        @rtype:  bool
        @return: C{True} if the window is a child window.
        """
        return win32.IsChild(self.get_handle())

    is_zoomed = is_maximized
    is_iconic = is_minimized

    # ------------------------------------------------------------------------------

    def enable(self):
        """
        Enable the user input for the window.

        @see: L{disable}

        @raise WindowsError: An error occured while processing this request.
        """
        win32.EnableWindow(self.get_handle(), True)

    def disable(self):
        """
        Disable the user input for the window.

        @see: L{enable}

        @raise WindowsError: An error occured while processing this request.
        """
        win32.EnableWindow(self.get_handle(), False)

    def show(self, bAsync=True):
        """
        Make the window visible.

        @see: L{hide}

        @type  bAsync: bool
        @param bAsync: Perform the request asynchronously.

        @raise WindowsError: An error occured while processing this request.
        """
        if bAsync:
            win32.ShowWindowAsync(self.get_handle(), win32.SW_SHOW)
        else:
            win32.ShowWindow(self.get_handle(), win32.SW_SHOW)

    def hide(self, bAsync=True):
        """
        Make the window invisible.

        @see: L{show}

        @type  bAsync: bool
        @param bAsync: Perform the request asynchronously.

        @raise WindowsError: An error occured while processing this request.
        """
        if bAsync:
            win32.ShowWindowAsync(self.get_handle(), win32.SW_HIDE)
        else:
            win32.ShowWindow(self.get_handle(), win32.SW_HIDE)

    def maximize(self, bAsync=True):
        """
        Maximize the window.

        @see: L{minimize}, L{restore}

        @type  bAsync: bool
        @param bAsync: Perform the request asynchronously.

        @raise WindowsError: An error occured while processing this request.
        """
        if bAsync:
            win32.ShowWindowAsync(self.get_handle(), win32.SW_MAXIMIZE)
        else:
            win32.ShowWindow(self.get_handle(), win32.SW_MAXIMIZE)

    def minimize(self, bAsync=True):
        """
        Minimize the window.

        @see: L{maximize}, L{restore}

        @type  bAsync: bool
        @param bAsync: Perform the request asynchronously.

        @raise WindowsError: An error occured while processing this request.
        """
        if bAsync:
            win32.ShowWindowAsync(self.get_handle(), win32.SW_MINIMIZE)
        else:
            win32.ShowWindow(self.get_handle(), win32.SW_MINIMIZE)

    def restore(self, bAsync=True):
        """
        Unmaximize and unminimize the window.

        @see: L{maximize}, L{minimize}

        @type  bAsync: bool
        @param bAsync: Perform the request asynchronously.

        @raise WindowsError: An error occured while processing this request.
        """
        if bAsync:
            win32.ShowWindowAsync(self.get_handle(), win32.SW_RESTORE)
        else:
            win32.ShowWindow(self.get_handle(), win32.SW_RESTORE)

    def move(self, x=None, y=None, width=None, height=None, bRepaint=True):
        """
        Moves and/or resizes the window.

        @note: This is request is performed syncronously.

        @type  x: int
        @param x: (Optional) New horizontal coordinate.

        @type  y: int
        @param y: (Optional) New vertical coordinate.

        @type  width: int
        @param width: (Optional) Desired window width.

        @type  height: int
        @param height: (Optional) Desired window height.

        @type  bRepaint: bool
        @param bRepaint:
            (Optional) C{True} if the window should be redrawn afterwards.

        @raise WindowsError: An error occured while processing this request.
        """
        if None in (x, y, width, height):
            rect = self.get_screen_rect()
            if x is None:
                x = rect.left
            if y is None:
                y = rect.top
            if width is None:
                width = rect.right - rect.left
            if height is None:
                height = rect.bottom - rect.top
        win32.MoveWindow(self.get_handle(), x, y, width, height, bRepaint)

    def kill(self):
        """
        Signals the program to quit.

        @note: This is an asyncronous request.

        @raise WindowsError: An error occured while processing this request.
        """
        self.post(win32.WM_QUIT)

    def send(self, uMsg, wParam=None, lParam=None, dwTimeout=None):
        """
        Send a low-level window message syncronically.

        @type  uMsg: int
        @param uMsg: Message code.

        @param wParam:
            The type and meaning of this parameter depends on the message.

        @param lParam:
            The type and meaning of this parameter depends on the message.

        @param dwTimeout: Optional timeout for the operation.
            Use C{None} to wait indefinitely.

        @rtype:  int
        @return: The meaning of the return value depends on the window message.
            Typically a value of C{0} means an error occured. You can get the
            error code by calling L{win32.GetLastError}.
        """
        if dwTimeout is None:
            return win32.SendMessage(self.get_handle(), uMsg, wParam, lParam)
        return win32.SendMessageTimeout(self.get_handle(), uMsg, wParam, lParam, win32.SMTO_ABORTIFHUNG | win32.SMTO_ERRORONEXIT, dwTimeout)

    def post(self, uMsg, wParam=None, lParam=None):
        """
        Post a low-level window message asyncronically.

        @type  uMsg: int
        @param uMsg: Message code.

        @param wParam:
            The type and meaning of this parameter depends on the message.

        @param lParam:
            The type and meaning of this parameter depends on the message.

        @raise WindowsError: An error occured while sending the message.
        """
        win32.PostMessage(self.get_handle(), uMsg, wParam, lParam)

# === NexusCore/openenv\Lib\site-packages\openai\resources\images.py ===
# File generated from our OpenAPI spec by Stainless. See CONTRIBUTING.md for details.

from __future__ import annotations

from typing import List, Union, Mapping, Optional, cast
from typing_extensions import Literal

import httpx

from .. import _legacy_response
from ..types import image_edit_params, image_generate_params, image_create_variation_params
from .._types import NOT_GIVEN, Body, Query, Headers, NotGiven, FileTypes
from .._utils import extract_files, maybe_transform, deepcopy_minimal, async_maybe_transform
from .._compat import cached_property
from .._resource import SyncAPIResource, AsyncAPIResource
from .._response import to_streamed_response_wrapper, async_to_streamed_response_wrapper
from .._base_client import make_request_options
from ..types.image_model import ImageModel
from ..types.images_response import ImagesResponse

__all__ = ["Images", "AsyncImages"]


class Images(SyncAPIResource):
    @cached_property
    def with_raw_response(self) -> ImagesWithRawResponse:
        """
        This property can be used as a prefix for any HTTP method call to return
        the raw response object instead of the parsed content.

        For more information, see https://www.github.com/openai/openai-python#accessing-raw-response-data-eg-headers
        """
        return ImagesWithRawResponse(self)

    @cached_property
    def with_streaming_response(self) -> ImagesWithStreamingResponse:
        """
        An alternative to `.with_raw_response` that doesn't eagerly read the response body.

        For more information, see https://www.github.com/openai/openai-python#with_streaming_response
        """
        return ImagesWithStreamingResponse(self)

    def create_variation(
        self,
        *,
        image: FileTypes,
        model: Union[str, ImageModel, None] | NotGiven = NOT_GIVEN,
        n: Optional[int] | NotGiven = NOT_GIVEN,
        response_format: Optional[Literal["url", "b64_json"]] | NotGiven = NOT_GIVEN,
        size: Optional[Literal["256x256", "512x512", "1024x1024"]] | NotGiven = NOT_GIVEN,
        user: str | NotGiven = NOT_GIVEN,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> ImagesResponse:
        """Creates a variation of a given image.

        This endpoint only supports `dall-e-2`.

        Args:
          image: The image to use as the basis for the variation(s). Must be a valid PNG file,
              less than 4MB, and square.

          model: The model to use for image generation. Only `dall-e-2` is supported at this
              time.

          n: The number of images to generate. Must be between 1 and 10.

          response_format: The format in which the generated images are returned. Must be one of `url` or
              `b64_json`. URLs are only valid for 60 minutes after the image has been
              generated.

          size: The size of the generated images. Must be one of `256x256`, `512x512`, or
              `1024x1024`.

          user: A unique identifier representing your end-user, which can help OpenAI to monitor
              and detect abuse.
              [Learn more](https://platform.openai.com/docs/guides/safety-best-practices#end-user-ids).

          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request, in seconds
        """
        body = deepcopy_minimal(
            {
                "image": image,
                "model": model,
                "n": n,
                "response_format": response_format,
                "size": size,
                "user": user,
            }
        )
        files = extract_files(cast(Mapping[str, object], body), paths=[["image"]])
        # It should be noted that the actual Content-Type header that will be
        # sent to the server will contain a `boundary` parameter, e.g.
        # multipart/form-data; boundary=---abc--
        extra_headers = {"Content-Type": "multipart/form-data", **(extra_headers or {})}
        return self._post(
            "/images/variations",
            body=maybe_transform(body, image_create_variation_params.ImageCreateVariationParams),
            files=files,
            options=make_request_options(
                extra_headers=extra_headers, extra_query=extra_query, extra_body=extra_body, timeout=timeout
            ),
            cast_to=ImagesResponse,
        )

    def edit(
        self,
        *,
        image: Union[FileTypes, List[FileTypes]],
        prompt: str,
        background: Optional[Literal["transparent", "opaque", "auto"]] | NotGiven = NOT_GIVEN,
        mask: FileTypes | NotGiven = NOT_GIVEN,
        model: Union[str, ImageModel, None] | NotGiven = NOT_GIVEN,
        n: Optional[int] | NotGiven = NOT_GIVEN,
        output_compression: Optional[int] | NotGiven = NOT_GIVEN,
        output_format: Optional[Literal["png", "jpeg", "webp"]] | NotGiven = NOT_GIVEN,
        quality: Optional[Literal["standard", "low", "medium", "high", "auto"]] | NotGiven = NOT_GIVEN,
        response_format: Optional[Literal["url", "b64_json"]] | NotGiven = NOT_GIVEN,
        size: Optional[Literal["256x256", "512x512", "1024x1024", "1536x1024", "1024x1536", "auto"]]
        | NotGiven = NOT_GIVEN,
        user: str | NotGiven = NOT_GIVEN,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> ImagesResponse:
        """Creates an edited or extended image given one or more source images and a
        prompt.

        This endpoint only supports `gpt-image-1` and `dall-e-2`.

        Args:
          image: The image(s) to edit. Must be a supported image file or an array of images.

              For `gpt-image-1`, each image should be a `png`, `webp`, or `jpg` file less than
              50MB. You can provide up to 16 images.

              For `dall-e-2`, you can only provide one image, and it should be a square `png`
              file less than 4MB.

          prompt: A text description of the desired image(s). The maximum length is 1000
              characters for `dall-e-2`, and 32000 characters for `gpt-image-1`.

          background: Allows to set transparency for the background of the generated image(s). This
              parameter is only supported for `gpt-image-1`. Must be one of `transparent`,
              `opaque` or `auto` (default value). When `auto` is used, the model will
              automatically determine the best background for the image.

              If `transparent`, the output format needs to support transparency, so it should
              be set to either `png` (default value) or `webp`.

          mask: An additional image whose fully transparent areas (e.g. where alpha is zero)
              indicate where `image` should be edited. If there are multiple images provided,
              the mask will be applied on the first image. Must be a valid PNG file, less than
              4MB, and have the same dimensions as `image`.

          model: The model to use for image generation. Only `dall-e-2` and `gpt-image-1` are
              supported. Defaults to `dall-e-2` unless a parameter specific to `gpt-image-1`
              is used.

          n: The number of images to generate. Must be between 1 and 10.

          output_compression: The compression level (0-100%) for the generated images. This parameter is only
              supported for `gpt-image-1` with the `webp` or `jpeg` output formats, and
              defaults to 100.

          output_format: The format in which the generated images are returned. This parameter is only
              supported for `gpt-image-1`. Must be one of `png`, `jpeg`, or `webp`. The
              default value is `png`.

          quality: The quality of the image that will be generated. `high`, `medium` and `low` are
              only supported for `gpt-image-1`. `dall-e-2` only supports `standard` quality.
              Defaults to `auto`.

          response_format: The format in which the generated images are returned. Must be one of `url` or
              `b64_json`. URLs are only valid for 60 minutes after the image has been
              generated. This parameter is only supported for `dall-e-2`, as `gpt-image-1`
              will always return base64-encoded images.

          size: The size of the generated images. Must be one of `1024x1024`, `1536x1024`
              (landscape), `1024x1536` (portrait), or `auto` (default value) for
              `gpt-image-1`, and one of `256x256`, `512x512`, or `1024x1024` for `dall-e-2`.

          user: A unique identifier representing your end-user, which can help OpenAI to monitor
              and detect abuse.
              [Learn more](https://platform.openai.com/docs/guides/safety-best-practices#end-user-ids).

          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request, in seconds
        """
        body = deepcopy_minimal(
            {
                "image": image,
                "prompt": prompt,
                "background": background,
                "mask": mask,
                "model": model,
                "n": n,
                "output_compression": output_compression,
                "output_format": output_format,
                "quality": quality,
                "response_format": response_format,
                "size": size,
                "user": user,
            }
        )
        files = extract_files(cast(Mapping[str, object], body), paths=[["image"], ["image", "<array>"], ["mask"]])
        # It should be noted that the actual Content-Type header that will be
        # sent to the server will contain a `boundary` parameter, e.g.
        # multipart/form-data; boundary=---abc--
        extra_headers = {"Content-Type": "multipart/form-data", **(extra_headers or {})}
        return self._post(
            "/images/edits",
            body=maybe_transform(body, image_edit_params.ImageEditParams),
            files=files,
            options=make_request_options(
                extra_headers=extra_headers, extra_query=extra_query, extra_body=extra_body, timeout=timeout
            ),
            cast_to=ImagesResponse,
        )

    def generate(
        self,
        *,
        prompt: str,
        background: Optional[Literal["transparent", "opaque", "auto"]] | NotGiven = NOT_GIVEN,
        model: Union[str, ImageModel, None] | NotGiven = NOT_GIVEN,
        moderation: Optional[Literal["low", "auto"]] | NotGiven = NOT_GIVEN,
        n: Optional[int] | NotGiven = NOT_GIVEN,
        output_compression: Optional[int] | NotGiven = NOT_GIVEN,
        output_format: Optional[Literal["png", "jpeg", "webp"]] | NotGiven = NOT_GIVEN,
        quality: Optional[Literal["standard", "hd", "low", "medium", "high", "auto"]] | NotGiven = NOT_GIVEN,
        response_format: Optional[Literal["url", "b64_json"]] | NotGiven = NOT_GIVEN,
        size: Optional[
            Literal["auto", "1024x1024", "1536x1024", "1024x1536", "256x256", "512x512", "1792x1024", "1024x1792"]
        ]
        | NotGiven = NOT_GIVEN,
        style: Optional[Literal["vivid", "natural"]] | NotGiven = NOT_GIVEN,
        user: str | NotGiven = NOT_GIVEN,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> ImagesResponse:
        """
        Creates an image given a prompt.
        [Learn more](https://platform.openai.com/docs/guides/images).

        Args:
          prompt: A text description of the desired image(s). The maximum length is 32000
              characters for `gpt-image-1`, 1000 characters for `dall-e-2` and 4000 characters
              for `dall-e-3`.

          background: Allows to set transparency for the background of the generated image(s). This
              parameter is only supported for `gpt-image-1`. Must be one of `transparent`,
              `opaque` or `auto` (default value). When `auto` is used, the model will
              automatically determine the best background for the image.

              If `transparent`, the output format needs to support transparency, so it should
              be set to either `png` (default value) or `webp`.

          model: The model to use for image generation. One of `dall-e-2`, `dall-e-3`, or
              `gpt-image-1`. Defaults to `dall-e-2` unless a parameter specific to
              `gpt-image-1` is used.

          moderation: Control the content-moderation level for images generated by `gpt-image-1`. Must
              be either `low` for less restrictive filtering or `auto` (default value).

          n: The number of images to generate. Must be between 1 and 10. For `dall-e-3`, only
              `n=1` is supported.

          output_compression: The compression level (0-100%) for the generated images. This parameter is only
              supported for `gpt-image-1` with the `webp` or `jpeg` output formats, and
              defaults to 100.

          output_format: The format in which the generated images are returned. This parameter is only
              supported for `gpt-image-1`. Must be one of `png`, `jpeg`, or `webp`.

          quality: The quality of the image that will be generated.

              - `auto` (default value) will automatically select the best quality for the
                given model.
              - `high`, `medium` and `low` are supported for `gpt-image-1`.
              - `hd` and `standard` are supported for `dall-e-3`.
              - `standard` is the only option for `dall-e-2`.

          response_format: The format in which generated images with `dall-e-2` and `dall-e-3` are
              returned. Must be one of `url` or `b64_json`. URLs are only valid for 60 minutes
              after the image has been generated. This parameter isn't supported for
              `gpt-image-1` which will always return base64-encoded images.

          size: The size of the generated images. Must be one of `1024x1024`, `1536x1024`
              (landscape), `1024x1536` (portrait), or `auto` (default value) for
              `gpt-image-1`, one of `256x256`, `512x512`, or `1024x1024` for `dall-e-2`, and
              one of `1024x1024`, `1792x1024`, or `1024x1792` for `dall-e-3`.

          style: The style of the generated images. This parameter is only supported for
              `dall-e-3`. Must be one of `vivid` or `natural`. Vivid causes the model to lean
              towards generating hyper-real and dramatic images. Natural causes the model to
              produce more natural, less hyper-real looking images.

          user: A unique identifier representing your end-user, which can help OpenAI to monitor
              and detect abuse.
              [Learn more](https://platform.openai.com/docs/guides/safety-best-practices#end-user-ids).

          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request, in seconds
        """
        return self._post(
            "/images/generations",
            body=maybe_transform(
                {
                    "prompt": prompt,
                    "background": background,
                    "model": model,
                    "moderation": moderation,
                    "n": n,
                    "output_compression": output_compression,
                    "output_format": output_format,
                    "quality": quality,
                    "response_format": response_format,
                    "size": size,
                    "style": style,
                    "user": user,
                },
                image_generate_params.ImageGenerateParams,
            ),
            options=make_request_options(
                extra_headers=extra_headers, extra_query=extra_query, extra_body=extra_body, timeout=timeout
            ),
            cast_to=ImagesResponse,
        )


class AsyncImages(AsyncAPIResource):
    @cached_property
    def with_raw_response(self) -> AsyncImagesWithRawResponse:
        """
        This property can be used as a prefix for any HTTP method call to return
        the raw response object instead of the parsed content.

        For more information, see https://www.github.com/openai/openai-python#accessing-raw-response-data-eg-headers
        """
        return AsyncImagesWithRawResponse(self)

    @cached_property
    def with_streaming_response(self) -> AsyncImagesWithStreamingResponse:
        """
        An alternative to `.with_raw_response` that doesn't eagerly read the response body.

        For more information, see https://www.github.com/openai/openai-python#with_streaming_response
        """
        return AsyncImagesWithStreamingResponse(self)

    async def create_variation(
        self,
        *,
        image: FileTypes,
        model: Union[str, ImageModel, None] | NotGiven = NOT_GIVEN,
        n: Optional[int] | NotGiven = NOT_GIVEN,
        response_format: Optional[Literal["url", "b64_json"]] | NotGiven = NOT_GIVEN,
        size: Optional[Literal["256x256", "512x512", "1024x1024"]] | NotGiven = NOT_GIVEN,
        user: str | NotGiven = NOT_GIVEN,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> ImagesResponse:
        """Creates a variation of a given image.

        This endpoint only supports `dall-e-2`.

        Args:
          image: The image to use as the basis for the variation(s). Must be a valid PNG file,
              less than 4MB, and square.

          model: The model to use for image generation. Only `dall-e-2` is supported at this
              time.

          n: The number of images to generate. Must be between 1 and 10.

          response_format: The format in which the generated images are returned. Must be one of `url` or
              `b64_json`. URLs are only valid for 60 minutes after the image has been
              generated.

          size: The size of the generated images. Must be one of `256x256`, `512x512`, or
              `1024x1024`.

          user: A unique identifier representing your end-user, which can help OpenAI to monitor
              and detect abuse.
              [Learn more](https://platform.openai.com/docs/guides/safety-best-practices#end-user-ids).

          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request, in seconds
        """
        body = deepcopy_minimal(
            {
                "image": image,
                "model": model,
                "n": n,
                "response_format": response_format,
                "size": size,
                "user": user,
            }
        )
        files = extract_files(cast(Mapping[str, object], body), paths=[["image"]])
        # It should be noted that the actual Content-Type header that will be
        # sent to the server will contain a `boundary` parameter, e.g.
        # multipart/form-data; boundary=---abc--
        extra_headers = {"Content-Type": "multipart/form-data", **(extra_headers or {})}
        return await self._post(
            "/images/variations",
            body=await async_maybe_transform(body, image_create_variation_params.ImageCreateVariationParams),
            files=files,
            options=make_request_options(
                extra_headers=extra_headers, extra_query=extra_query, extra_body=extra_body, timeout=timeout
            ),
            cast_to=ImagesResponse,
        )

    async def edit(
        self,
        *,
        image: Union[FileTypes, List[FileTypes]],
        prompt: str,
        background: Optional[Literal["transparent", "opaque", "auto"]] | NotGiven = NOT_GIVEN,
        mask: FileTypes | NotGiven = NOT_GIVEN,
        model: Union[str, ImageModel, None] | NotGiven = NOT_GIVEN,
        n: Optional[int] | NotGiven = NOT_GIVEN,
        output_compression: Optional[int] | NotGiven = NOT_GIVEN,
        output_format: Optional[Literal["png", "jpeg", "webp"]] | NotGiven = NOT_GIVEN,
        quality: Optional[Literal["standard", "low", "medium", "high", "auto"]] | NotGiven = NOT_GIVEN,
        response_format: Optional[Literal["url", "b64_json"]] | NotGiven = NOT_GIVEN,
        size: Optional[Literal["256x256", "512x512", "1024x1024", "1536x1024", "1024x1536", "auto"]]
        | NotGiven = NOT_GIVEN,
        user: str | NotGiven = NOT_GIVEN,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> ImagesResponse:
        """Creates an edited or extended image given one or more source images and a
        prompt.

        This endpoint only supports `gpt-image-1` and `dall-e-2`.

        Args:
          image: The image(s) to edit. Must be a supported image file or an array of images.

              For `gpt-image-1`, each image should be a `png`, `webp`, or `jpg` file less than
              50MB. You can provide up to 16 images.

              For `dall-e-2`, you can only provide one image, and it should be a square `png`
              file less than 4MB.

          prompt: A text description of the desired image(s). The maximum length is 1000
              characters for `dall-e-2`, and 32000 characters for `gpt-image-1`.

          background: Allows to set transparency for the background of the generated image(s). This
              parameter is only supported for `gpt-image-1`. Must be one of `transparent`,
              `opaque` or `auto` (default value). When `auto` is used, the model will
              automatically determine the best background for the image.

              If `transparent`, the output format needs to support transparency, so it should
              be set to either `png` (default value) or `webp`.

          mask: An additional image whose fully transparent areas (e.g. where alpha is zero)
              indicate where `image` should be edited. If there are multiple images provided,
              the mask will be applied on the first image. Must be a valid PNG file, less than
              4MB, and have the same dimensions as `image`.

          model: The model to use for image generation. Only `dall-e-2` and `gpt-image-1` are
              supported. Defaults to `dall-e-2` unless a parameter specific to `gpt-image-1`
              is used.

          n: The number of images to generate. Must be between 1 and 10.

          output_compression: The compression level (0-100%) for the generated images. This parameter is only
              supported for `gpt-image-1` with the `webp` or `jpeg` output formats, and
              defaults to 100.

          output_format: The format in which the generated images are returned. This parameter is only
              supported for `gpt-image-1`. Must be one of `png`, `jpeg`, or `webp`. The
              default value is `png`.

          quality: The quality of the image that will be generated. `high`, `medium` and `low` are
              only supported for `gpt-image-1`. `dall-e-2` only supports `standard` quality.
              Defaults to `auto`.

          response_format: The format in which the generated images are returned. Must be one of `url` or
              `b64_json`. URLs are only valid for 60 minutes after the image has been
              generated. This parameter is only supported for `dall-e-2`, as `gpt-image-1`
              will always return base64-encoded images.

          size: The size of the generated images. Must be one of `1024x1024`, `1536x1024`
              (landscape), `1024x1536` (portrait), or `auto` (default value) for
              `gpt-image-1`, and one of `256x256`, `512x512`, or `1024x1024` for `dall-e-2`.

          user: A unique identifier representing your end-user, which can help OpenAI to monitor
              and detect abuse.
              [Learn more](https://platform.openai.com/docs/guides/safety-best-practices#end-user-ids).

          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request, in seconds
        """
        body = deepcopy_minimal(
            {
                "image": image,
                "prompt": prompt,
                "background": background,
                "mask": mask,
                "model": model,
                "n": n,
                "output_compression": output_compression,
                "output_format": output_format,
                "quality": quality,
                "response_format": response_format,
                "size": size,
                "user": user,
            }
        )
        files = extract_files(cast(Mapping[str, object], body), paths=[["image"], ["image", "<array>"], ["mask"]])
        # It should be noted that the actual Content-Type header that will be
        # sent to the server will contain a `boundary` parameter, e.g.
        # multipart/form-data; boundary=---abc--
        extra_headers = {"Content-Type": "multipart/form-data", **(extra_headers or {})}
        return await self._post(
            "/images/edits",
            body=await async_maybe_transform(body, image_edit_params.ImageEditParams),
            files=files,
            options=make_request_options(
                extra_headers=extra_headers, extra_query=extra_query, extra_body=extra_body, timeout=timeout
            ),
            cast_to=ImagesResponse,
        )

    async def generate(
        self,
        *,
        prompt: str,
        background: Optional[Literal["transparent", "opaque", "auto"]] | NotGiven = NOT_GIVEN,
        model: Union[str, ImageModel, None] | NotGiven = NOT_GIVEN,
        moderation: Optional[Literal["low", "auto"]] | NotGiven = NOT_GIVEN,
        n: Optional[int] | NotGiven = NOT_GIVEN,
        output_compression: Optional[int] | NotGiven = NOT_GIVEN,
        output_format: Optional[Literal["png", "jpeg", "webp"]] | NotGiven = NOT_GIVEN,
        quality: Optional[Literal["standard", "hd", "low", "medium", "high", "auto"]] | NotGiven = NOT_GIVEN,
        response_format: Optional[Literal["url", "b64_json"]] | NotGiven = NOT_GIVEN,
        size: Optional[
            Literal["auto", "1024x1024", "1536x1024", "1024x1536", "256x256", "512x512", "1792x1024", "1024x1792"]
        ]
        | NotGiven = NOT_GIVEN,
        style: Optional[Literal["vivid", "natural"]] | NotGiven = NOT_GIVEN,
        user: str | NotGiven = NOT_GIVEN,
        # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> ImagesResponse:
        """
        Creates an image given a prompt.
        [Learn more](https://platform.openai.com/docs/guides/images).

        Args:
          prompt: A text description of the desired image(s). The maximum length is 32000
              characters for `gpt-image-1`, 1000 characters for `dall-e-2` and 4000 characters
              for `dall-e-3`.

          background: Allows to set transparency for the background of the generated image(s). This
              parameter is only supported for `gpt-image-1`. Must be one of `transparent`,
              `opaque` or `auto` (default value). When `auto` is used, the model will
              automatically determine the best background for the image.

              If `transparent`, the output format needs to support transparency, so it should
              be set to either `png` (default value) or `webp`.

          model: The model to use for image generation. One of `dall-e-2`, `dall-e-3`, or
              `gpt-image-1`. Defaults to `dall-e-2` unless a parameter specific to
              `gpt-image-1` is used.

          moderation: Control the content-moderation level for images generated by `gpt-image-1`. Must
              be either `low` for less restrictive filtering or `auto` (default value).

          n: The number of images to generate. Must be between 1 and 10. For `dall-e-3`, only
              `n=1` is supported.

          output_compression: The compression level (0-100%) for the generated images. This parameter is only
              supported for `gpt-image-1` with the `webp` or `jpeg` output formats, and
              defaults to 100.

          output_format: The format in which the generated images are returned. This parameter is only
              supported for `gpt-image-1`. Must be one of `png`, `jpeg`, or `webp`.

          quality: The quality of the image that will be generated.

              - `auto` (default value) will automatically select the best quality for the
                given model.
              - `high`, `medium` and `low` are supported for `gpt-image-1`.
              - `hd` and `standard` are supported for `dall-e-3`.
              - `standard` is the only option for `dall-e-2`.

          response_format: The format in which generated images with `dall-e-2` and `dall-e-3` are
              returned. Must be one of `url` or `b64_json`. URLs are only valid for 60 minutes
              after the image has been generated. This parameter isn't supported for
              `gpt-image-1` which will always return base64-encoded images.

          size: The size of the generated images. Must be one of `1024x1024`, `1536x1024`
              (landscape), `1024x1536` (portrait), or `auto` (default value) for
              `gpt-image-1`, one of `256x256`, `512x512`, or `1024x1024` for `dall-e-2`, and
              one of `1024x1024`, `1792x1024`, or `1024x1792` for `dall-e-3`.

          style: The style of the generated images. This parameter is only supported for
              `dall-e-3`. Must be one of `vivid` or `natural`. Vivid causes the model to lean
              towards generating hyper-real and dramatic images. Natural causes the model to
              produce more natural, less hyper-real looking images.

          user: A unique identifier representing your end-user, which can help OpenAI to monitor
              and detect abuse.
              [Learn more](https://platform.openai.com/docs/guides/safety-best-practices#end-user-ids).

          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request, in seconds
        """
        return await self._post(
            "/images/generations",
            body=await async_maybe_transform(
                {
                    "prompt": prompt,
                    "background": background,
                    "model": model,
                    "moderation": moderation,
                    "n": n,
                    "output_compression": output_compression,
                    "output_format": output_format,
                    "quality": quality,
                    "response_format": response_format,
                    "size": size,
                    "style": style,
                    "user": user,
                },
                image_generate_params.ImageGenerateParams,
            ),
            options=make_request_options(
                extra_headers=extra_headers, extra_query=extra_query, extra_body=extra_body, timeout=timeout
            ),
            cast_to=ImagesResponse,
        )


class ImagesWithRawResponse:
    def __init__(self, images: Images) -> None:
        self._images = images

        self.create_variation = _legacy_response.to_raw_response_wrapper(
            images.create_variation,
        )
        self.edit = _legacy_response.to_raw_response_wrapper(
            images.edit,
        )
        self.generate = _legacy_response.to_raw_response_wrapper(
            images.generate,
        )


class AsyncImagesWithRawResponse:
    def __init__(self, images: AsyncImages) -> None:
        self._images = images

        self.create_variation = _legacy_response.async_to_raw_response_wrapper(
            images.create_variation,
        )
        self.edit = _legacy_response.async_to_raw_response_wrapper(
            images.edit,
        )
        self.generate = _legacy_response.async_to_raw_response_wrapper(
            images.generate,
        )


class ImagesWithStreamingResponse:
    def __init__(self, images: Images) -> None:
        self._images = images

        self.create_variation = to_streamed_response_wrapper(
            images.create_variation,
        )
        self.edit = to_streamed_response_wrapper(
            images.edit,
        )
        self.generate = to_streamed_response_wrapper(
            images.generate,
        )


class AsyncImagesWithStreamingResponse:
    def __init__(self, images: AsyncImages) -> None:
        self._images = images

        self.create_variation = async_to_streamed_response_wrapper(
            images.create_variation,
        )
        self.edit = async_to_streamed_response_wrapper(
            images.edit,
        )
        self.generate = async_to_streamed_response_wrapper(
            images.generate,
        )

# === NexusCore/openenv\Lib\site-packages\selenium\webdriver\common\devtools\v137\target.py ===
# DO NOT EDIT THIS FILE!
#
# This file is generated from the CDP specification. If you need to make
# changes, edit the generator and regenerate all of the modules.
#
# CDP domain: Target
from __future__ import annotations
from .util import event_class, T_JSON_DICT
from dataclasses import dataclass
import enum
import typing
from . import browser
from . import page


class TargetID(str):
    def to_json(self) -> str:
        return self

    @classmethod
    def from_json(cls, json: str) -> TargetID:
        return cls(json)

    def __repr__(self):
        return 'TargetID({})'.format(super().__repr__())


class SessionID(str):
    '''
    Unique identifier of attached debugging session.
    '''
    def to_json(self) -> str:
        return self

    @classmethod
    def from_json(cls, json: str) -> SessionID:
        return cls(json)

    def __repr__(self):
        return 'SessionID({})'.format(super().__repr__())


@dataclass
class TargetInfo:
    target_id: TargetID

    #: List of types: https://source.chromium.org/chromium/chromium/src/+/main:content/browser/devtools/devtools_agent_host_impl.cc?ss=chromium&q=f:devtools%20-f:out%20%22::kTypeTab%5B%5D%22
    type_: str

    title: str

    url: str

    #: Whether the target has an attached client.
    attached: bool

    #: Whether the target has access to the originating window.
    can_access_opener: bool

    #: Opener target Id
    opener_id: typing.Optional[TargetID] = None

    #: Frame id of originating window (is only set if target has an opener).
    opener_frame_id: typing.Optional[page.FrameId] = None

    browser_context_id: typing.Optional[browser.BrowserContextID] = None

    #: Provides additional details for specific target types. For example, for
    #: the type of "page", this may be set to "prerender".
    subtype: typing.Optional[str] = None

    def to_json(self):
        json = dict()
        json['targetId'] = self.target_id.to_json()
        json['type'] = self.type_
        json['title'] = self.title
        json['url'] = self.url
        json['attached'] = self.attached
        json['canAccessOpener'] = self.can_access_opener
        if self.opener_id is not None:
            json['openerId'] = self.opener_id.to_json()
        if self.opener_frame_id is not None:
            json['openerFrameId'] = self.opener_frame_id.to_json()
        if self.browser_context_id is not None:
            json['browserContextId'] = self.browser_context_id.to_json()
        if self.subtype is not None:
            json['subtype'] = self.subtype
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            target_id=TargetID.from_json(json['targetId']),
            type_=str(json['type']),
            title=str(json['title']),
            url=str(json['url']),
            attached=bool(json['attached']),
            can_access_opener=bool(json['canAccessOpener']),
            opener_id=TargetID.from_json(json['openerId']) if 'openerId' in json else None,
            opener_frame_id=page.FrameId.from_json(json['openerFrameId']) if 'openerFrameId' in json else None,
            browser_context_id=browser.BrowserContextID.from_json(json['browserContextId']) if 'browserContextId' in json else None,
            subtype=str(json['subtype']) if 'subtype' in json else None,
        )


@dataclass
class FilterEntry:
    '''
    A filter used by target query/discovery/auto-attach operations.
    '''
    #: If set, causes exclusion of matching targets from the list.
    exclude: typing.Optional[bool] = None

    #: If not present, matches any type.
    type_: typing.Optional[str] = None

    def to_json(self):
        json = dict()
        if self.exclude is not None:
            json['exclude'] = self.exclude
        if self.type_ is not None:
            json['type'] = self.type_
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            exclude=bool(json['exclude']) if 'exclude' in json else None,
            type_=str(json['type']) if 'type' in json else None,
        )


class TargetFilter(list):
    '''
    The entries in TargetFilter are matched sequentially against targets and
    the first entry that matches determines if the target is included or not,
    depending on the value of ``exclude`` field in the entry.
    If filter is not specified, the one assumed is
    [{type: "browser", exclude: true}, {type: "tab", exclude: true}, {}]
    (i.e. include everything but ``browser`` and ``tab``).
    '''
    def to_json(self) -> typing.List[FilterEntry]:
        return self

    @classmethod
    def from_json(cls, json: typing.List[FilterEntry]) -> TargetFilter:
        return cls(json)

    def __repr__(self):
        return 'TargetFilter({})'.format(super().__repr__())


@dataclass
class RemoteLocation:
    host: str

    port: int

    def to_json(self):
        json = dict()
        json['host'] = self.host
        json['port'] = self.port
        return json

    @classmethod
    def from_json(cls, json):
        return cls(
            host=str(json['host']),
            port=int(json['port']),
        )


class WindowState(enum.Enum):
    '''
    The state of the target window.
    '''
    NORMAL = "normal"
    MINIMIZED = "minimized"
    MAXIMIZED = "maximized"
    FULLSCREEN = "fullscreen"

    def to_json(self):
        return self.value

    @classmethod
    def from_json(cls, json):
        return cls(json)


def activate_target(
        target_id: TargetID
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Activates (focuses) the target.

    :param target_id:
    '''
    params: T_JSON_DICT = dict()
    params['targetId'] = target_id.to_json()
    cmd_dict: T_JSON_DICT = {
        'method': 'Target.activateTarget',
        'params': params,
    }
    json = yield cmd_dict


def attach_to_target(
        target_id: TargetID,
        flatten: typing.Optional[bool] = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,SessionID]:
    '''
    Attaches to the target with given id.

    :param target_id:
    :param flatten: *(Optional)* Enables "flat" access to the session via specifying sessionId attribute in the commands. We plan to make this the default, deprecate non-flattened mode, and eventually retire it. See crbug.com/991325.
    :returns: Id assigned to the session.
    '''
    params: T_JSON_DICT = dict()
    params['targetId'] = target_id.to_json()
    if flatten is not None:
        params['flatten'] = flatten
    cmd_dict: T_JSON_DICT = {
        'method': 'Target.attachToTarget',
        'params': params,
    }
    json = yield cmd_dict
    return SessionID.from_json(json['sessionId'])


def attach_to_browser_target() -> typing.Generator[T_JSON_DICT,T_JSON_DICT,SessionID]:
    '''
    Attaches to the browser target, only uses flat sessionId mode.

    **EXPERIMENTAL**

    :returns: Id assigned to the session.
    '''
    cmd_dict: T_JSON_DICT = {
        'method': 'Target.attachToBrowserTarget',
    }
    json = yield cmd_dict
    return SessionID.from_json(json['sessionId'])


def close_target(
        target_id: TargetID
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,bool]:
    '''
    Closes the target. If the target is a page that gets closed too.

    :param target_id:
    :returns: Always set to true. If an error occurs, the response indicates protocol error.
    '''
    params: T_JSON_DICT = dict()
    params['targetId'] = target_id.to_json()
    cmd_dict: T_JSON_DICT = {
        'method': 'Target.closeTarget',
        'params': params,
    }
    json = yield cmd_dict
    return bool(json['success'])


def expose_dev_tools_protocol(
        target_id: TargetID,
        binding_name: typing.Optional[str] = None,
        inherit_permissions: typing.Optional[bool] = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Inject object to the target's main frame that provides a communication
    channel with browser target.

    Injected object will be available as ``window[bindingName]``.

    The object has the following API:
    - ``binding.send(json)`` - a method to send messages over the remote debugging protocol
    - ``binding.onmessage = json => handleMessage(json)`` - a callback that will be called for the protocol notifications and command responses.

    **EXPERIMENTAL**

    :param target_id:
    :param binding_name: *(Optional)* Binding name, 'cdp' if not specified.
    :param inherit_permissions: *(Optional)* If true, inherits the current root session's permissions (default: false).
    '''
    params: T_JSON_DICT = dict()
    params['targetId'] = target_id.to_json()
    if binding_name is not None:
        params['bindingName'] = binding_name
    if inherit_permissions is not None:
        params['inheritPermissions'] = inherit_permissions
    cmd_dict: T_JSON_DICT = {
        'method': 'Target.exposeDevToolsProtocol',
        'params': params,
    }
    json = yield cmd_dict


def create_browser_context(
        dispose_on_detach: typing.Optional[bool] = None,
        proxy_server: typing.Optional[str] = None,
        proxy_bypass_list: typing.Optional[str] = None,
        origins_with_universal_network_access: typing.Optional[typing.List[str]] = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,browser.BrowserContextID]:
    '''
    Creates a new empty BrowserContext. Similar to an incognito profile but you can have more than
    one.

    :param dispose_on_detach: **(EXPERIMENTAL)** *(Optional)* If specified, disposes this context when debugging session disconnects.
    :param proxy_server: **(EXPERIMENTAL)** *(Optional)* Proxy server, similar to the one passed to --proxy-server
    :param proxy_bypass_list: **(EXPERIMENTAL)** *(Optional)* Proxy bypass list, similar to the one passed to --proxy-bypass-list
    :param origins_with_universal_network_access: **(EXPERIMENTAL)** *(Optional)* An optional list of origins to grant unlimited cross-origin access to. Parts of the URL other than those constituting origin are ignored.
    :returns: The id of the context created.
    '''
    params: T_JSON_DICT = dict()
    if dispose_on_detach is not None:
        params['disposeOnDetach'] = dispose_on_detach
    if proxy_server is not None:
        params['proxyServer'] = proxy_server
    if proxy_bypass_list is not None:
        params['proxyBypassList'] = proxy_bypass_list
    if origins_with_universal_network_access is not None:
        params['originsWithUniversalNetworkAccess'] = [i for i in origins_with_universal_network_access]
    cmd_dict: T_JSON_DICT = {
        'method': 'Target.createBrowserContext',
        'params': params,
    }
    json = yield cmd_dict
    return browser.BrowserContextID.from_json(json['browserContextId'])


def get_browser_contexts() -> typing.Generator[T_JSON_DICT,T_JSON_DICT,typing.List[browser.BrowserContextID]]:
    '''
    Returns all browser contexts created with ``Target.createBrowserContext`` method.

    :returns: An array of browser context ids.
    '''
    cmd_dict: T_JSON_DICT = {
        'method': 'Target.getBrowserContexts',
    }
    json = yield cmd_dict
    return [browser.BrowserContextID.from_json(i) for i in json['browserContextIds']]


def create_target(
        url: str,
        left: typing.Optional[int] = None,
        top: typing.Optional[int] = None,
        width: typing.Optional[int] = None,
        height: typing.Optional[int] = None,
        window_state: typing.Optional[WindowState] = None,
        browser_context_id: typing.Optional[browser.BrowserContextID] = None,
        enable_begin_frame_control: typing.Optional[bool] = None,
        new_window: typing.Optional[bool] = None,
        background: typing.Optional[bool] = None,
        for_tab: typing.Optional[bool] = None,
        hidden: typing.Optional[bool] = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,TargetID]:
    '''
    Creates a new page.

    :param url: The initial URL the page will be navigated to. An empty string indicates about:blank.
    :param left: **(EXPERIMENTAL)** *(Optional)* Frame left origin in DIP (requires newWindow to be true or headless shell).
    :param top: **(EXPERIMENTAL)** *(Optional)* Frame top origin in DIP (requires newWindow to be true or headless shell).
    :param width: *(Optional)* Frame width in DIP (requires newWindow to be true or headless shell).
    :param height: *(Optional)* Frame height in DIP (requires newWindow to be true or headless shell).
    :param window_state: *(Optional)* Frame window state (requires newWindow to be true or headless shell). Default is normal.
    :param browser_context_id: **(EXPERIMENTAL)** *(Optional)* The browser context to create the page in.
    :param enable_begin_frame_control: **(EXPERIMENTAL)** *(Optional)* Whether BeginFrames for this target will be controlled via DevTools (headless shell only, not supported on MacOS yet, false by default).
    :param new_window: *(Optional)* Whether to create a new Window or Tab (false by default, not supported by headless shell).
    :param background: *(Optional)* Whether to create the target in background or foreground (false by default, not supported by headless shell).
    :param for_tab: **(EXPERIMENTAL)** *(Optional)* Whether to create the target of type "tab".
    :param hidden: **(EXPERIMENTAL)** *(Optional)* Whether to create a hidden target. The hidden target is observable via protocol, but not present in the tab UI strip. Cannot be created with ```forTab: true````, ````newWindow: true```` or ````background: false```. The life-time of the tab is limited to the life-time of the session.
    :returns: The id of the page opened.
    '''
    params: T_JSON_DICT = dict()
    params['url'] = url
    if left is not None:
        params['left'] = left
    if top is not None:
        params['top'] = top
    if width is not None:
        params['width'] = width
    if height is not None:
        params['height'] = height
    if window_state is not None:
        params['windowState'] = window_state.to_json()
    if browser_context_id is not None:
        params['browserContextId'] = browser_context_id.to_json()
    if enable_begin_frame_control is not None:
        params['enableBeginFrameControl'] = enable_begin_frame_control
    if new_window is not None:
        params['newWindow'] = new_window
    if background is not None:
        params['background'] = background
    if for_tab is not None:
        params['forTab'] = for_tab
    if hidden is not None:
        params['hidden'] = hidden
    cmd_dict: T_JSON_DICT = {
        'method': 'Target.createTarget',
        'params': params,
    }
    json = yield cmd_dict
    return TargetID.from_json(json['targetId'])


def detach_from_target(
        session_id: typing.Optional[SessionID] = None,
        target_id: typing.Optional[TargetID] = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Detaches session with given id.

    :param session_id: *(Optional)* Session to detach.
    :param target_id: *(Optional)* Deprecated.
    '''
    params: T_JSON_DICT = dict()
    if session_id is not None:
        params['sessionId'] = session_id.to_json()
    if target_id is not None:
        params['targetId'] = target_id.to_json()
    cmd_dict: T_JSON_DICT = {
        'method': 'Target.detachFromTarget',
        'params': params,
    }
    json = yield cmd_dict


def dispose_browser_context(
        browser_context_id: browser.BrowserContextID
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Deletes a BrowserContext. All the belonging pages will be closed without calling their
    beforeunload hooks.

    :param browser_context_id:
    '''
    params: T_JSON_DICT = dict()
    params['browserContextId'] = browser_context_id.to_json()
    cmd_dict: T_JSON_DICT = {
        'method': 'Target.disposeBrowserContext',
        'params': params,
    }
    json = yield cmd_dict


def get_target_info(
        target_id: typing.Optional[TargetID] = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,TargetInfo]:
    '''
    Returns information about a target.

    **EXPERIMENTAL**

    :param target_id: *(Optional)*
    :returns: 
    '''
    params: T_JSON_DICT = dict()
    if target_id is not None:
        params['targetId'] = target_id.to_json()
    cmd_dict: T_JSON_DICT = {
        'method': 'Target.getTargetInfo',
        'params': params,
    }
    json = yield cmd_dict
    return TargetInfo.from_json(json['targetInfo'])


def get_targets(
        filter_: typing.Optional[TargetFilter] = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,typing.List[TargetInfo]]:
    '''
    Retrieves a list of available targets.

    :param filter_: **(EXPERIMENTAL)** *(Optional)* Only targets matching filter will be reported. If filter is not specified and target discovery is currently enabled, a filter used for target discovery is used for consistency.
    :returns: The list of targets.
    '''
    params: T_JSON_DICT = dict()
    if filter_ is not None:
        params['filter'] = filter_.to_json()
    cmd_dict: T_JSON_DICT = {
        'method': 'Target.getTargets',
        'params': params,
    }
    json = yield cmd_dict
    return [TargetInfo.from_json(i) for i in json['targetInfos']]


def send_message_to_target(
        message: str,
        session_id: typing.Optional[SessionID] = None,
        target_id: typing.Optional[TargetID] = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Sends protocol message over session with given id.
    Consider using flat mode instead; see commands attachToTarget, setAutoAttach,
    and crbug.com/991325.

    :param message:
    :param session_id: *(Optional)* Identifier of the session.
    :param target_id: *(Optional)* Deprecated.
    '''
    params: T_JSON_DICT = dict()
    params['message'] = message
    if session_id is not None:
        params['sessionId'] = session_id.to_json()
    if target_id is not None:
        params['targetId'] = target_id.to_json()
    cmd_dict: T_JSON_DICT = {
        'method': 'Target.sendMessageToTarget',
        'params': params,
    }
    json = yield cmd_dict


def set_auto_attach(
        auto_attach: bool,
        wait_for_debugger_on_start: bool,
        flatten: typing.Optional[bool] = None,
        filter_: typing.Optional[TargetFilter] = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Controls whether to automatically attach to new targets which are considered
    to be directly related to this one (for example, iframes or workers).
    When turned on, attaches to all existing related targets as well. When turned off,
    automatically detaches from all currently attached targets.
    This also clears all targets added by ``autoAttachRelated`` from the list of targets to watch
    for creation of related targets.
    You might want to call this recursively for auto-attached targets to attach
    to all available targets.

    :param auto_attach: Whether to auto-attach to related targets.
    :param wait_for_debugger_on_start: Whether to pause new targets when attaching to them. Use ```Runtime.runIfWaitingForDebugger``` to run paused targets.
    :param flatten: **(EXPERIMENTAL)** *(Optional)* Enables "flat" access to the session via specifying sessionId attribute in the commands. We plan to make this the default, deprecate non-flattened mode, and eventually retire it. See crbug.com/991325.
    :param filter_: **(EXPERIMENTAL)** *(Optional)* Only targets matching filter will be attached.
    '''
    params: T_JSON_DICT = dict()
    params['autoAttach'] = auto_attach
    params['waitForDebuggerOnStart'] = wait_for_debugger_on_start
    if flatten is not None:
        params['flatten'] = flatten
    if filter_ is not None:
        params['filter'] = filter_.to_json()
    cmd_dict: T_JSON_DICT = {
        'method': 'Target.setAutoAttach',
        'params': params,
    }
    json = yield cmd_dict


def auto_attach_related(
        target_id: TargetID,
        wait_for_debugger_on_start: bool,
        filter_: typing.Optional[TargetFilter] = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Adds the specified target to the list of targets that will be monitored for any related target
    creation (such as child frames, child workers and new versions of service worker) and reported
    through ``attachedToTarget``. The specified target is also auto-attached.
    This cancels the effect of any previous ``setAutoAttach`` and is also cancelled by subsequent
    ``setAutoAttach``. Only available at the Browser target.

    **EXPERIMENTAL**

    :param target_id:
    :param wait_for_debugger_on_start: Whether to pause new targets when attaching to them. Use ```Runtime.runIfWaitingForDebugger``` to run paused targets.
    :param filter_: **(EXPERIMENTAL)** *(Optional)* Only targets matching filter will be attached.
    '''
    params: T_JSON_DICT = dict()
    params['targetId'] = target_id.to_json()
    params['waitForDebuggerOnStart'] = wait_for_debugger_on_start
    if filter_ is not None:
        params['filter'] = filter_.to_json()
    cmd_dict: T_JSON_DICT = {
        'method': 'Target.autoAttachRelated',
        'params': params,
    }
    json = yield cmd_dict


def set_discover_targets(
        discover: bool,
        filter_: typing.Optional[TargetFilter] = None
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Controls whether to discover available targets and notify via
    ``targetCreated/targetInfoChanged/targetDestroyed`` events.

    :param discover: Whether to discover available targets.
    :param filter_: **(EXPERIMENTAL)** *(Optional)* Only targets matching filter will be attached. If ```discover```` is false, ````filter``` must be omitted or empty.
    '''
    params: T_JSON_DICT = dict()
    params['discover'] = discover
    if filter_ is not None:
        params['filter'] = filter_.to_json()
    cmd_dict: T_JSON_DICT = {
        'method': 'Target.setDiscoverTargets',
        'params': params,
    }
    json = yield cmd_dict


def set_remote_locations(
        locations: typing.List[RemoteLocation]
    ) -> typing.Generator[T_JSON_DICT,T_JSON_DICT,None]:
    '''
    Enables target discovery for the specified locations, when ``setDiscoverTargets`` was set to
    ``true``.

    **EXPERIMENTAL**

    :param locations: List of remote locations.
    '''
    params: T_JSON_DICT = dict()
    params['locations'] = [i.to_json() for i in locations]
    cmd_dict: T_JSON_DICT = {
        'method': 'Target.setRemoteLocations',
        'params': params,
    }
    json = yield cmd_dict


@event_class('Target.attachedToTarget')
@dataclass
class AttachedToTarget:
    '''
    **EXPERIMENTAL**

    Issued when attached to target because of auto-attach or ``attachToTarget`` command.
    '''
    #: Identifier assigned to the session used to send/receive messages.
    session_id: SessionID
    target_info: TargetInfo
    waiting_for_debugger: bool

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> AttachedToTarget:
        return cls(
            session_id=SessionID.from_json(json['sessionId']),
            target_info=TargetInfo.from_json(json['targetInfo']),
            waiting_for_debugger=bool(json['waitingForDebugger'])
        )


@event_class('Target.detachedFromTarget')
@dataclass
class DetachedFromTarget:
    '''
    **EXPERIMENTAL**

    Issued when detached from target for any reason (including ``detachFromTarget`` command). Can be
    issued multiple times per target if multiple sessions have been attached to it.
    '''
    #: Detached session identifier.
    session_id: SessionID
    #: Deprecated.
    target_id: typing.Optional[TargetID]

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> DetachedFromTarget:
        return cls(
            session_id=SessionID.from_json(json['sessionId']),
            target_id=TargetID.from_json(json['targetId']) if 'targetId' in json else None
        )


@event_class('Target.receivedMessageFromTarget')
@dataclass
class ReceivedMessageFromTarget:
    '''
    Notifies about a new protocol message received from the session (as reported in
    ``attachedToTarget`` event).
    '''
    #: Identifier of a session which sends a message.
    session_id: SessionID
    message: str
    #: Deprecated.
    target_id: typing.Optional[TargetID]

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> ReceivedMessageFromTarget:
        return cls(
            session_id=SessionID.from_json(json['sessionId']),
            message=str(json['message']),
            target_id=TargetID.from_json(json['targetId']) if 'targetId' in json else None
        )


@event_class('Target.targetCreated')
@dataclass
class TargetCreated:
    '''
    Issued when a possible inspection target is created.
    '''
    target_info: TargetInfo

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> TargetCreated:
        return cls(
            target_info=TargetInfo.from_json(json['targetInfo'])
        )


@event_class('Target.targetDestroyed')
@dataclass
class TargetDestroyed:
    '''
    Issued when a target is destroyed.
    '''
    target_id: TargetID

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> TargetDestroyed:
        return cls(
            target_id=TargetID.from_json(json['targetId'])
        )


@event_class('Target.targetCrashed')
@dataclass
class TargetCrashed:
    '''
    Issued when a target has crashed.
    '''
    target_id: TargetID
    #: Termination status type.
    status: str
    #: Termination error code.
    error_code: int

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> TargetCrashed:
        return cls(
            target_id=TargetID.from_json(json['targetId']),
            status=str(json['status']),
            error_code=int(json['errorCode'])
        )


@event_class('Target.targetInfoChanged')
@dataclass
class TargetInfoChanged:
    '''
    Issued when some information about a target has changed. This only happens between
    ``targetCreated`` and ``targetDestroyed``.
    '''
    target_info: TargetInfo

    @classmethod
    def from_json(cls, json: T_JSON_DICT) -> TargetInfoChanged:
        return cls(
            target_info=TargetInfo.from_json(json['targetInfo'])
        )

# === NexusCore/openenv\Lib\site-packages\tornado\platform\asyncio.py ===
"""Bridges between the `asyncio` module and Tornado IOLoop.

.. versionadded:: 3.2

This module integrates Tornado with the ``asyncio`` module introduced
in Python 3.4. This makes it possible to combine the two libraries on
the same event loop.

.. deprecated:: 5.0

   While the code in this module is still used, it is now enabled
   automatically when `asyncio` is available, so applications should
   no longer need to refer to this module directly.

.. note::

   Tornado is designed to use a selector-based event loop. On Windows,
   where a proactor-based event loop has been the default since Python 3.8,
   a selector event loop is emulated by running ``select`` on a separate thread.
   Configuring ``asyncio`` to use a selector event loop may improve performance
   of Tornado (but may reduce performance of other ``asyncio``-based libraries
   in the same process).
"""

import asyncio
import atexit
import concurrent.futures
import contextvars
import errno
import functools
import select
import socket
import sys
import threading
import typing
import warnings
from tornado.gen import convert_yielded
from tornado.ioloop import IOLoop, _Selectable

from typing import (
    Any,
    Callable,
    Dict,
    List,
    Optional,
    Protocol,
    Set,
    Tuple,
    TypeVar,
    Union,
)

if typing.TYPE_CHECKING:
    from typing_extensions import TypeVarTuple, Unpack


class _HasFileno(Protocol):
    def fileno(self) -> int:
        pass


_FileDescriptorLike = Union[int, _HasFileno]

_T = TypeVar("_T")

if typing.TYPE_CHECKING:
    _Ts = TypeVarTuple("_Ts")

# Collection of selector thread event loops to shut down on exit.
_selector_loops: Set["SelectorThread"] = set()


def _atexit_callback() -> None:
    for loop in _selector_loops:
        with loop._select_cond:
            loop._closing_selector = True
            loop._select_cond.notify()
        try:
            loop._waker_w.send(b"a")
        except BlockingIOError:
            pass
        if loop._thread is not None:
            # If we don't join our (daemon) thread here, we may get a deadlock
            # during interpreter shutdown. I don't really understand why. This
            # deadlock happens every time in CI (both travis and appveyor) but
            # I've never been able to reproduce locally.
            loop._thread.join()
    _selector_loops.clear()


atexit.register(_atexit_callback)


class BaseAsyncIOLoop(IOLoop):
    def initialize(  # type: ignore
        self, asyncio_loop: asyncio.AbstractEventLoop, **kwargs: Any
    ) -> None:
        # asyncio_loop is always the real underlying IOLoop. This is used in
        # ioloop.py to maintain the asyncio-to-ioloop mappings.
        self.asyncio_loop = asyncio_loop
        # selector_loop is an event loop that implements the add_reader family of
        # methods. Usually the same as asyncio_loop but differs on platforms such
        # as windows where the default event loop does not implement these methods.
        self.selector_loop = asyncio_loop
        if hasattr(asyncio, "ProactorEventLoop") and isinstance(
            asyncio_loop, asyncio.ProactorEventLoop
        ):
            # Ignore this line for mypy because the abstract method checker
            # doesn't understand dynamic proxies.
            self.selector_loop = AddThreadSelectorEventLoop(asyncio_loop)  # type: ignore
        # Maps fd to (fileobj, handler function) pair (as in IOLoop.add_handler)
        self.handlers: Dict[int, Tuple[Union[int, _Selectable], Callable]] = {}
        # Set of fds listening for reads/writes
        self.readers: Set[int] = set()
        self.writers: Set[int] = set()
        self.closing = False
        # If an asyncio loop was closed through an asyncio interface
        # instead of IOLoop.close(), we'd never hear about it and may
        # have left a dangling reference in our map. In case an
        # application (or, more likely, a test suite) creates and
        # destroys a lot of event loops in this way, check here to
        # ensure that we don't have a lot of dead loops building up in
        # the map.
        #
        # TODO(bdarnell): consider making self.asyncio_loop a weakref
        # for AsyncIOMainLoop and make _ioloop_for_asyncio a
        # WeakKeyDictionary.
        for loop in IOLoop._ioloop_for_asyncio.copy():
            if loop.is_closed():
                try:
                    del IOLoop._ioloop_for_asyncio[loop]
                except KeyError:
                    pass

        # Make sure we don't already have an IOLoop for this asyncio loop
        existing_loop = IOLoop._ioloop_for_asyncio.setdefault(asyncio_loop, self)
        if existing_loop is not self:
            raise RuntimeError(
                f"IOLoop {existing_loop} already associated with asyncio loop {asyncio_loop}"
            )

        super().initialize(**kwargs)

    def close(self, all_fds: bool = False) -> None:
        self.closing = True
        for fd in list(self.handlers):
            fileobj, handler_func = self.handlers[fd]
            self.remove_handler(fd)
            if all_fds:
                self.close_fd(fileobj)
        # Remove the mapping before closing the asyncio loop. If this
        # happened in the other order, we could race against another
        # initialize() call which would see the closed asyncio loop,
        # assume it was closed from the asyncio side, and do this
        # cleanup for us, leading to a KeyError.
        del IOLoop._ioloop_for_asyncio[self.asyncio_loop]
        if self.selector_loop is not self.asyncio_loop:
            self.selector_loop.close()
        self.asyncio_loop.close()

    def add_handler(
        self, fd: Union[int, _Selectable], handler: Callable[..., None], events: int
    ) -> None:
        fd, fileobj = self.split_fd(fd)
        if fd in self.handlers:
            raise ValueError("fd %s added twice" % fd)
        self.handlers[fd] = (fileobj, handler)
        if events & IOLoop.READ:
            self.selector_loop.add_reader(fd, self._handle_events, fd, IOLoop.READ)
            self.readers.add(fd)
        if events & IOLoop.WRITE:
            self.selector_loop.add_writer(fd, self._handle_events, fd, IOLoop.WRITE)
            self.writers.add(fd)

    def update_handler(self, fd: Union[int, _Selectable], events: int) -> None:
        fd, fileobj = self.split_fd(fd)
        if events & IOLoop.READ:
            if fd not in self.readers:
                self.selector_loop.add_reader(fd, self._handle_events, fd, IOLoop.READ)
                self.readers.add(fd)
        else:
            if fd in self.readers:
                self.selector_loop.remove_reader(fd)
                self.readers.remove(fd)
        if events & IOLoop.WRITE:
            if fd not in self.writers:
                self.selector_loop.add_writer(fd, self._handle_events, fd, IOLoop.WRITE)
                self.writers.add(fd)
        else:
            if fd in self.writers:
                self.selector_loop.remove_writer(fd)
                self.writers.remove(fd)

    def remove_handler(self, fd: Union[int, _Selectable]) -> None:
        fd, fileobj = self.split_fd(fd)
        if fd not in self.handlers:
            return
        if fd in self.readers:
            self.selector_loop.remove_reader(fd)
            self.readers.remove(fd)
        if fd in self.writers:
            self.selector_loop.remove_writer(fd)
            self.writers.remove(fd)
        del self.handlers[fd]

    def _handle_events(self, fd: int, events: int) -> None:
        fileobj, handler_func = self.handlers[fd]
        handler_func(fileobj, events)

    def start(self) -> None:
        self.asyncio_loop.run_forever()

    def stop(self) -> None:
        self.asyncio_loop.stop()

    def call_at(
        self, when: float, callback: Callable, *args: Any, **kwargs: Any
    ) -> object:
        # asyncio.call_at supports *args but not **kwargs, so bind them here.
        # We do not synchronize self.time and asyncio_loop.time, so
        # convert from absolute to relative.
        return self.asyncio_loop.call_later(
            max(0, when - self.time()),
            self._run_callback,
            functools.partial(callback, *args, **kwargs),
        )

    def remove_timeout(self, timeout: object) -> None:
        timeout.cancel()  # type: ignore

    def add_callback(self, callback: Callable, *args: Any, **kwargs: Any) -> None:
        try:
            if asyncio.get_running_loop() is self.asyncio_loop:
                call_soon = self.asyncio_loop.call_soon
            else:
                call_soon = self.asyncio_loop.call_soon_threadsafe
        except RuntimeError:
            call_soon = self.asyncio_loop.call_soon_threadsafe

        try:
            call_soon(self._run_callback, functools.partial(callback, *args, **kwargs))
        except RuntimeError:
            # "Event loop is closed". Swallow the exception for
            # consistency with PollIOLoop (and logical consistency
            # with the fact that we can't guarantee that an
            # add_callback that completes without error will
            # eventually execute).
            pass
        except AttributeError:
            # ProactorEventLoop may raise this instead of RuntimeError
            # if call_soon_threadsafe races with a call to close().
            # Swallow it too for consistency.
            pass

    def add_callback_from_signal(
        self, callback: Callable, *args: Any, **kwargs: Any
    ) -> None:
        warnings.warn("add_callback_from_signal is deprecated", DeprecationWarning)
        try:
            self.asyncio_loop.call_soon_threadsafe(
                self._run_callback, functools.partial(callback, *args, **kwargs)
            )
        except RuntimeError:
            pass

    def run_in_executor(
        self,
        executor: Optional[concurrent.futures.Executor],
        func: Callable[..., _T],
        *args: Any,
    ) -> "asyncio.Future[_T]":
        return self.asyncio_loop.run_in_executor(executor, func, *args)

    def set_default_executor(self, executor: concurrent.futures.Executor) -> None:
        return self.asyncio_loop.set_default_executor(executor)


class AsyncIOMainLoop(BaseAsyncIOLoop):
    """``AsyncIOMainLoop`` creates an `.IOLoop` that corresponds to the
    current ``asyncio`` event loop (i.e. the one returned by
    ``asyncio.get_event_loop()``).

    .. deprecated:: 5.0

       Now used automatically when appropriate; it is no longer necessary
       to refer to this class directly.

    .. versionchanged:: 5.0

       Closing an `AsyncIOMainLoop` now closes the underlying asyncio loop.
    """

    def initialize(self, **kwargs: Any) -> None:  # type: ignore
        super().initialize(asyncio.get_event_loop(), **kwargs)

    def _make_current(self) -> None:
        # AsyncIOMainLoop already refers to the current asyncio loop so
        # nothing to do here.
        pass


class AsyncIOLoop(BaseAsyncIOLoop):
    """``AsyncIOLoop`` is an `.IOLoop` that runs on an ``asyncio`` event loop.
    This class follows the usual Tornado semantics for creating new
    ``IOLoops``; these loops are not necessarily related to the
    ``asyncio`` default event loop.

    Each ``AsyncIOLoop`` creates a new ``asyncio.EventLoop``; this object
    can be accessed with the ``asyncio_loop`` attribute.

    .. versionchanged:: 6.2

       Support explicit ``asyncio_loop`` argument
       for specifying the asyncio loop to attach to,
       rather than always creating a new one with the default policy.

    .. versionchanged:: 5.0

       When an ``AsyncIOLoop`` becomes the current `.IOLoop`, it also sets
       the current `asyncio` event loop.

    .. deprecated:: 5.0

       Now used automatically when appropriate; it is no longer necessary
       to refer to this class directly.
    """

    def initialize(self, **kwargs: Any) -> None:  # type: ignore
        self.is_current = False
        loop = None
        if "asyncio_loop" not in kwargs:
            kwargs["asyncio_loop"] = loop = asyncio.new_event_loop()
        try:
            super().initialize(**kwargs)
        except Exception:
            # If initialize() does not succeed (taking ownership of the loop),
            # we have to close it.
            if loop is not None:
                loop.close()
            raise

    def close(self, all_fds: bool = False) -> None:
        if self.is_current:
            self._clear_current()
        super().close(all_fds=all_fds)

    def _make_current(self) -> None:
        if not self.is_current:
            try:
                self.old_asyncio = asyncio.get_event_loop()
            except (RuntimeError, AssertionError):
                self.old_asyncio = None  # type: ignore
            self.is_current = True
        asyncio.set_event_loop(self.asyncio_loop)

    def _clear_current_hook(self) -> None:
        if self.is_current:
            asyncio.set_event_loop(self.old_asyncio)
            self.is_current = False


def to_tornado_future(asyncio_future: asyncio.Future) -> asyncio.Future:
    """Convert an `asyncio.Future` to a `tornado.concurrent.Future`.

    .. versionadded:: 4.1

    .. deprecated:: 5.0
       Tornado ``Futures`` have been merged with `asyncio.Future`,
       so this method is now a no-op.
    """
    return asyncio_future


def to_asyncio_future(tornado_future: asyncio.Future) -> asyncio.Future:
    """Convert a Tornado yieldable object to an `asyncio.Future`.

    .. versionadded:: 4.1

    .. versionchanged:: 4.3
       Now accepts any yieldable object, not just
       `tornado.concurrent.Future`.

    .. deprecated:: 5.0
       Tornado ``Futures`` have been merged with `asyncio.Future`,
       so this method is now equivalent to `tornado.gen.convert_yielded`.
    """
    return convert_yielded(tornado_future)


_AnyThreadEventLoopPolicy = None


def __getattr__(name: str) -> typing.Any:
    # The event loop policy system is deprecated in Python 3.14; simply accessing
    # the name asyncio.DefaultEventLoopPolicy will raise a warning. Lazily create
    # the AnyThreadEventLoopPolicy class so that the warning is only raised if
    # the policy is used.
    if name != "AnyThreadEventLoopPolicy":
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

    global _AnyThreadEventLoopPolicy
    if _AnyThreadEventLoopPolicy is None:
        if sys.platform == "win32" and hasattr(
            asyncio, "WindowsSelectorEventLoopPolicy"
        ):
            # "Any thread" and "selector" should be orthogonal, but there's not a clean
            # interface for composing policies so pick the right base.
            _BasePolicy = asyncio.WindowsSelectorEventLoopPolicy  # type: ignore
        else:
            _BasePolicy = asyncio.DefaultEventLoopPolicy

        class AnyThreadEventLoopPolicy(_BasePolicy):  # type: ignore
            """Event loop policy that allows loop creation on any thread.

            The default `asyncio` event loop policy only automatically creates
            event loops in the main threads. Other threads must create event
            loops explicitly or `asyncio.get_event_loop` (and therefore
            `.IOLoop.current`) will fail. Installing this policy allows event
            loops to be created automatically on any thread, matching the
            behavior of Tornado versions prior to 5.0 (or 5.0 on Python 2).

            Usage::

                asyncio.set_event_loop_policy(AnyThreadEventLoopPolicy())

            .. versionadded:: 5.0

            .. deprecated:: 6.2

                ``AnyThreadEventLoopPolicy`` affects the implicit creation
                of an event loop, which is deprecated in Python 3.10 and
                will be removed in a future version of Python. At that time
                ``AnyThreadEventLoopPolicy`` will no longer be useful.
                If you are relying on it, use `asyncio.new_event_loop`
                or `asyncio.run` explicitly in any non-main threads that
                need event loops.
            """

            def __init__(self) -> None:
                super().__init__()
                warnings.warn(
                    "AnyThreadEventLoopPolicy is deprecated, use asyncio.run "
                    "or asyncio.new_event_loop instead",
                    DeprecationWarning,
                    stacklevel=2,
                )

            def get_event_loop(self) -> asyncio.AbstractEventLoop:
                try:
                    return super().get_event_loop()
                except RuntimeError:
                    # "There is no current event loop in thread %r"
                    loop = self.new_event_loop()
                    self.set_event_loop(loop)
                    return loop

        _AnyThreadEventLoopPolicy = AnyThreadEventLoopPolicy

    return _AnyThreadEventLoopPolicy


class SelectorThread:
    """Define ``add_reader`` methods to be called in a background select thread.

    Instances of this class start a second thread to run a selector.
    This thread is completely hidden from the user;
    all callbacks are run on the wrapped event loop's thread.

    Typically used via ``AddThreadSelectorEventLoop``,
    but can be attached to a running asyncio loop.
    """

    _closed = False

    def __init__(self, real_loop: asyncio.AbstractEventLoop) -> None:
        self._main_thread_ctx = contextvars.copy_context()

        self._real_loop = real_loop

        self._select_cond = threading.Condition()
        self._select_args: Optional[
            Tuple[List[_FileDescriptorLike], List[_FileDescriptorLike]]
        ] = None
        self._closing_selector = False
        self._thread: Optional[threading.Thread] = None
        self._thread_manager_handle = self._thread_manager()

        async def thread_manager_anext() -> None:
            # the anext builtin wasn't added until 3.10. We just need to iterate
            # this generator one step.
            await self._thread_manager_handle.__anext__()

        # When the loop starts, start the thread. Not too soon because we can't
        # clean up if we get to this point but the event loop is closed without
        # starting.
        self._real_loop.call_soon(
            lambda: self._real_loop.create_task(thread_manager_anext()),
            context=self._main_thread_ctx,
        )

        self._readers: Dict[_FileDescriptorLike, Callable] = {}
        self._writers: Dict[_FileDescriptorLike, Callable] = {}

        # Writing to _waker_w will wake up the selector thread, which
        # watches for _waker_r to be readable.
        self._waker_r, self._waker_w = socket.socketpair()
        self._waker_r.setblocking(False)
        self._waker_w.setblocking(False)
        _selector_loops.add(self)
        self.add_reader(self._waker_r, self._consume_waker)

    def close(self) -> None:
        if self._closed:
            return
        with self._select_cond:
            self._closing_selector = True
            self._select_cond.notify()
        self._wake_selector()
        if self._thread is not None:
            self._thread.join()
        _selector_loops.discard(self)
        self.remove_reader(self._waker_r)
        self._waker_r.close()
        self._waker_w.close()
        self._closed = True

    async def _thread_manager(self) -> typing.AsyncGenerator[None, None]:
        # Create a thread to run the select system call. We manage this thread
        # manually so we can trigger a clean shutdown from an atexit hook. Note
        # that due to the order of operations at shutdown, only daemon threads
        # can be shut down in this way (non-daemon threads would require the
        # introduction of a new hook: https://bugs.python.org/issue41962)
        self._thread = threading.Thread(
            name="Tornado selector",
            daemon=True,
            target=self._run_select,
        )
        self._thread.start()
        self._start_select()
        try:
            # The presense of this yield statement means that this coroutine
            # is actually an asynchronous generator, which has a special
            # shutdown protocol. We wait at this yield point until the
            # event loop's shutdown_asyncgens method is called, at which point
            # we will get a GeneratorExit exception and can shut down the
            # selector thread.
            yield
        except GeneratorExit:
            self.close()
            raise

    def _wake_selector(self) -> None:
        if self._closed:
            return
        try:
            self._waker_w.send(b"a")
        except BlockingIOError:
            pass

    def _consume_waker(self) -> None:
        try:
            self._waker_r.recv(1024)
        except BlockingIOError:
            pass

    def _start_select(self) -> None:
        # Capture reader and writer sets here in the event loop
        # thread to avoid any problems with concurrent
        # modification while the select loop uses them.
        with self._select_cond:
            assert self._select_args is None
            self._select_args = (list(self._readers.keys()), list(self._writers.keys()))
            self._select_cond.notify()

    def _run_select(self) -> None:
        while True:
            with self._select_cond:
                while self._select_args is None and not self._closing_selector:
                    self._select_cond.wait()
                if self._closing_selector:
                    return
                assert self._select_args is not None
                to_read, to_write = self._select_args
                self._select_args = None

            # We use the simpler interface of the select module instead of
            # the more stateful interface in the selectors module because
            # this class is only intended for use on windows, where
            # select.select is the only option. The selector interface
            # does not have well-documented thread-safety semantics that
            # we can rely on so ensuring proper synchronization would be
            # tricky.
            try:
                # On windows, selecting on a socket for write will not
                # return the socket when there is an error (but selecting
                # for reads works). Also select for errors when selecting
                # for writes, and merge the results.
                #
                # This pattern is also used in
                # https://github.com/python/cpython/blob/v3.8.0/Lib/selectors.py#L312-L317
                rs, ws, xs = select.select(to_read, to_write, to_write)
                ws = ws + xs
            except OSError as e:
                # After remove_reader or remove_writer is called, the file
                # descriptor may subsequently be closed on the event loop
                # thread. It's possible that this select thread hasn't
                # gotten into the select system call by the time that
                # happens in which case (at least on macOS), select may
                # raise a "bad file descriptor" error. If we get that
                # error, check and see if we're also being woken up by
                # polling the waker alone. If we are, just return to the
                # event loop and we'll get the updated set of file
                # descriptors on the next iteration. Otherwise, raise the
                # original error.
                if e.errno == getattr(errno, "WSAENOTSOCK", errno.EBADF):
                    rs, _, _ = select.select([self._waker_r.fileno()], [], [], 0)
                    if rs:
                        ws = []
                    else:
                        raise
                else:
                    raise

            try:
                self._real_loop.call_soon_threadsafe(
                    self._handle_select, rs, ws, context=self._main_thread_ctx
                )
            except RuntimeError:
                # "Event loop is closed". Swallow the exception for
                # consistency with PollIOLoop (and logical consistency
                # with the fact that we can't guarantee that an
                # add_callback that completes without error will
                # eventually execute).
                pass
            except AttributeError:
                # ProactorEventLoop may raise this instead of RuntimeError
                # if call_soon_threadsafe races with a call to close().
                # Swallow it too for consistency.
                pass

    def _handle_select(
        self, rs: List[_FileDescriptorLike], ws: List[_FileDescriptorLike]
    ) -> None:
        for r in rs:
            self._handle_event(r, self._readers)
        for w in ws:
            self._handle_event(w, self._writers)
        self._start_select()

    def _handle_event(
        self,
        fd: _FileDescriptorLike,
        cb_map: Dict[_FileDescriptorLike, Callable],
    ) -> None:
        try:
            callback = cb_map[fd]
        except KeyError:
            return
        callback()

    def add_reader(
        self, fd: _FileDescriptorLike, callback: Callable[..., None], *args: Any
    ) -> None:
        self._readers[fd] = functools.partial(callback, *args)
        self._wake_selector()

    def add_writer(
        self, fd: _FileDescriptorLike, callback: Callable[..., None], *args: Any
    ) -> None:
        self._writers[fd] = functools.partial(callback, *args)
        self._wake_selector()

    def remove_reader(self, fd: _FileDescriptorLike) -> bool:
        try:
            del self._readers[fd]
        except KeyError:
            return False
        self._wake_selector()
        return True

    def remove_writer(self, fd: _FileDescriptorLike) -> bool:
        try:
            del self._writers[fd]
        except KeyError:
            return False
        self._wake_selector()
        return True


class AddThreadSelectorEventLoop(asyncio.AbstractEventLoop):
    """Wrap an event loop to add implementations of the ``add_reader`` method family.

    Instances of this class start a second thread to run a selector.
    This thread is completely hidden from the user; all callbacks are
    run on the wrapped event loop's thread.

    This class is used automatically by Tornado; applications should not need
    to refer to it directly.

    It is safe to wrap any event loop with this class, although it only makes sense
    for event loops that do not implement the ``add_reader`` family of methods
    themselves (i.e. ``WindowsProactorEventLoop``)

    Closing the ``AddThreadSelectorEventLoop`` also closes the wrapped event loop.

    """

    # This class is a __getattribute__-based proxy. All attributes other than those
    # in this set are proxied through to the underlying loop.
    MY_ATTRIBUTES = {
        "_real_loop",
        "_selector",
        "add_reader",
        "add_writer",
        "close",
        "remove_reader",
        "remove_writer",
    }

    def __getattribute__(self, name: str) -> Any:
        if name in AddThreadSelectorEventLoop.MY_ATTRIBUTES:
            return super().__getattribute__(name)
        return getattr(self._real_loop, name)

    def __init__(self, real_loop: asyncio.AbstractEventLoop) -> None:
        self._real_loop = real_loop
        self._selector = SelectorThread(real_loop)

    def close(self) -> None:
        self._selector.close()
        self._real_loop.close()

    def add_reader(
        self,
        fd: "_FileDescriptorLike",
        callback: Callable[..., None],
        *args: "Unpack[_Ts]",
    ) -> None:
        return self._selector.add_reader(fd, callback, *args)

    def add_writer(
        self,
        fd: "_FileDescriptorLike",
        callback: Callable[..., None],
        *args: "Unpack[_Ts]",
    ) -> None:
        return self._selector.add_writer(fd, callback, *args)

    def remove_reader(self, fd: "_FileDescriptorLike") -> bool:
        return self._selector.remove_reader(fd)

    def remove_writer(self, fd: "_FileDescriptorLike") -> bool:
        return self._selector.remove_writer(fd)

# === NexusCore/myenv\Lib\site-packages\pip\_vendor\rich\segment.py ===
from enum import IntEnum
from functools import lru_cache
from itertools import filterfalse
from logging import getLogger
from operator import attrgetter
from typing import (
    TYPE_CHECKING,
    Dict,
    Iterable,
    List,
    NamedTuple,
    Optional,
    Sequence,
    Tuple,
    Type,
    Union,
)

from .cells import (
    _is_single_cell_widths,
    cached_cell_len,
    cell_len,
    get_character_cell_size,
    set_cell_size,
)
from .repr import Result, rich_repr
from .style import Style

if TYPE_CHECKING:
    from .console import Console, ConsoleOptions, RenderResult

log = getLogger("rich")


class ControlType(IntEnum):
    """Non-printable control codes which typically translate to ANSI codes."""

    BELL = 1
    CARRIAGE_RETURN = 2
    HOME = 3
    CLEAR = 4
    SHOW_CURSOR = 5
    HIDE_CURSOR = 6
    ENABLE_ALT_SCREEN = 7
    DISABLE_ALT_SCREEN = 8
    CURSOR_UP = 9
    CURSOR_DOWN = 10
    CURSOR_FORWARD = 11
    CURSOR_BACKWARD = 12
    CURSOR_MOVE_TO_COLUMN = 13
    CURSOR_MOVE_TO = 14
    ERASE_IN_LINE = 15
    SET_WINDOW_TITLE = 16


ControlCode = Union[
    Tuple[ControlType],
    Tuple[ControlType, Union[int, str]],
    Tuple[ControlType, int, int],
]


@rich_repr()
class Segment(NamedTuple):
    """A piece of text with associated style. Segments are produced by the Console render process and
    are ultimately converted in to strings to be written to the terminal.

    Args:
        text (str): A piece of text.
        style (:class:`~rich.style.Style`, optional): An optional style to apply to the text.
        control (Tuple[ControlCode], optional): Optional sequence of control codes.

    Attributes:
        cell_length (int): The cell length of this Segment.
    """

    text: str
    style: Optional[Style] = None
    control: Optional[Sequence[ControlCode]] = None

    @property
    def cell_length(self) -> int:
        """The number of terminal cells required to display self.text.

        Returns:
            int: A number of cells.
        """
        text, _style, control = self
        return 0 if control else cell_len(text)

    def __rich_repr__(self) -> Result:
        yield self.text
        if self.control is None:
            if self.style is not None:
                yield self.style
        else:
            yield self.style
            yield self.control

    def __bool__(self) -> bool:
        """Check if the segment contains text."""
        return bool(self.text)

    @property
    def is_control(self) -> bool:
        """Check if the segment contains control codes."""
        return self.control is not None

    @classmethod
    @lru_cache(1024 * 16)
    def _split_cells(cls, segment: "Segment", cut: int) -> Tuple["Segment", "Segment"]:
        """Split a segment in to two at a given cell position.

        Note that splitting a double-width character, may result in that character turning
        into two spaces.

        Args:
            segment (Segment): A segment to split.
            cut (int): A cell position to cut on.

        Returns:
            A tuple of two segments.
        """
        text, style, control = segment
        _Segment = Segment
        cell_length = segment.cell_length
        if cut >= cell_length:
            return segment, _Segment("", style, control)

        cell_size = get_character_cell_size

        pos = int((cut / cell_length) * len(text))

        while True:
            before = text[:pos]
            cell_pos = cell_len(before)
            out_by = cell_pos - cut
            if not out_by:
                return (
                    _Segment(before, style, control),
                    _Segment(text[pos:], style, control),
                )
            if out_by == -1 and cell_size(text[pos]) == 2:
                return (
                    _Segment(text[:pos] + " ", style, control),
                    _Segment(" " + text[pos + 1 :], style, control),
                )
            if out_by == +1 and cell_size(text[pos - 1]) == 2:
                return (
                    _Segment(text[: pos - 1] + " ", style, control),
                    _Segment(" " + text[pos:], style, control),
                )
            if cell_pos < cut:
                pos += 1
            else:
                pos -= 1

    def split_cells(self, cut: int) -> Tuple["Segment", "Segment"]:
        """Split segment in to two segments at the specified column.

        If the cut point falls in the middle of a 2-cell wide character then it is replaced
        by two spaces, to preserve the display width of the parent segment.

        Args:
            cut (int): Offset within the segment to cut.

        Returns:
            Tuple[Segment, Segment]: Two segments.
        """
        text, style, control = self
        assert cut >= 0

        if _is_single_cell_widths(text):
            # Fast path with all 1 cell characters
            if cut >= len(text):
                return self, Segment("", style, control)
            return (
                Segment(text[:cut], style, control),
                Segment(text[cut:], style, control),
            )

        return self._split_cells(self, cut)

    @classmethod
    def line(cls) -> "Segment":
        """Make a new line segment."""
        return cls("\n")

    @classmethod
    def apply_style(
        cls,
        segments: Iterable["Segment"],
        style: Optional[Style] = None,
        post_style: Optional[Style] = None,
    ) -> Iterable["Segment"]:
        """Apply style(s) to an iterable of segments.

        Returns an iterable of segments where the style is replaced by ``style + segment.style + post_style``.

        Args:
            segments (Iterable[Segment]): Segments to process.
            style (Style, optional): Base style. Defaults to None.
            post_style (Style, optional): Style to apply on top of segment style. Defaults to None.

        Returns:
            Iterable[Segments]: A new iterable of segments (possibly the same iterable).
        """
        result_segments = segments
        if style:
            apply = style.__add__
            result_segments = (
                cls(text, None if control else apply(_style), control)
                for text, _style, control in result_segments
            )
        if post_style:
            result_segments = (
                cls(
                    text,
                    (
                        None
                        if control
                        else (_style + post_style if _style else post_style)
                    ),
                    control,
                )
                for text, _style, control in result_segments
            )
        return result_segments

    @classmethod
    def filter_control(
        cls, segments: Iterable["Segment"], is_control: bool = False
    ) -> Iterable["Segment"]:
        """Filter segments by ``is_control`` attribute.

        Args:
            segments (Iterable[Segment]): An iterable of Segment instances.
            is_control (bool, optional): is_control flag to match in search.

        Returns:
            Iterable[Segment]: And iterable of Segment instances.

        """
        if is_control:
            return filter(attrgetter("control"), segments)
        else:
            return filterfalse(attrgetter("control"), segments)

    @classmethod
    def split_lines(cls, segments: Iterable["Segment"]) -> Iterable[List["Segment"]]:
        """Split a sequence of segments in to a list of lines.

        Args:
            segments (Iterable[Segment]): Segments potentially containing line feeds.

        Yields:
            Iterable[List[Segment]]: Iterable of segment lists, one per line.
        """
        line: List[Segment] = []
        append = line.append

        for segment in segments:
            if "\n" in segment.text and not segment.control:
                text, style, _ = segment
                while text:
                    _text, new_line, text = text.partition("\n")
                    if _text:
                        append(cls(_text, style))
                    if new_line:
                        yield line
                        line = []
                        append = line.append
            else:
                append(segment)
        if line:
            yield line

    @classmethod
    def split_and_crop_lines(
        cls,
        segments: Iterable["Segment"],
        length: int,
        style: Optional[Style] = None,
        pad: bool = True,
        include_new_lines: bool = True,
    ) -> Iterable[List["Segment"]]:
        """Split segments in to lines, and crop lines greater than a given length.

        Args:
            segments (Iterable[Segment]): An iterable of segments, probably
                generated from console.render.
            length (int): Desired line length.
            style (Style, optional): Style to use for any padding.
            pad (bool): Enable padding of lines that are less than `length`.

        Returns:
            Iterable[List[Segment]]: An iterable of lines of segments.
        """
        line: List[Segment] = []
        append = line.append

        adjust_line_length = cls.adjust_line_length
        new_line_segment = cls("\n")

        for segment in segments:
            if "\n" in segment.text and not segment.control:
                text, segment_style, _ = segment
                while text:
                    _text, new_line, text = text.partition("\n")
                    if _text:
                        append(cls(_text, segment_style))
                    if new_line:
                        cropped_line = adjust_line_length(
                            line, length, style=style, pad=pad
                        )
                        if include_new_lines:
                            cropped_line.append(new_line_segment)
                        yield cropped_line
                        line.clear()
            else:
                append(segment)
        if line:
            yield adjust_line_length(line, length, style=style, pad=pad)

    @classmethod
    def adjust_line_length(
        cls,
        line: List["Segment"],
        length: int,
        style: Optional[Style] = None,
        pad: bool = True,
    ) -> List["Segment"]:
        """Adjust a line to a given width (cropping or padding as required).

        Args:
            segments (Iterable[Segment]): A list of segments in a single line.
            length (int): The desired width of the line.
            style (Style, optional): The style of padding if used (space on the end). Defaults to None.
            pad (bool, optional): Pad lines with spaces if they are shorter than `length`. Defaults to True.

        Returns:
            List[Segment]: A line of segments with the desired length.
        """
        line_length = sum(segment.cell_length for segment in line)
        new_line: List[Segment]

        if line_length < length:
            if pad:
                new_line = line + [cls(" " * (length - line_length), style)]
            else:
                new_line = line[:]
        elif line_length > length:
            new_line = []
            append = new_line.append
            line_length = 0
            for segment in line:
                segment_length = segment.cell_length
                if line_length + segment_length < length or segment.control:
                    append(segment)
                    line_length += segment_length
                else:
                    text, segment_style, _ = segment
                    text = set_cell_size(text, length - line_length)
                    append(cls(text, segment_style))
                    break
        else:
            new_line = line[:]
        return new_line

    @classmethod
    def get_line_length(cls, line: List["Segment"]) -> int:
        """Get the length of list of segments.

        Args:
            line (List[Segment]): A line encoded as a list of Segments (assumes no '\\\\n' characters),

        Returns:
            int: The length of the line.
        """
        _cell_len = cell_len
        return sum(_cell_len(text) for text, style, control in line if not control)

    @classmethod
    def get_shape(cls, lines: List[List["Segment"]]) -> Tuple[int, int]:
        """Get the shape (enclosing rectangle) of a list of lines.

        Args:
            lines (List[List[Segment]]): A list of lines (no '\\\\n' characters).

        Returns:
            Tuple[int, int]: Width and height in characters.
        """
        get_line_length = cls.get_line_length
        max_width = max(get_line_length(line) for line in lines) if lines else 0
        return (max_width, len(lines))

    @classmethod
    def set_shape(
        cls,
        lines: List[List["Segment"]],
        width: int,
        height: Optional[int] = None,
        style: Optional[Style] = None,
        new_lines: bool = False,
    ) -> List[List["Segment"]]:
        """Set the shape of a list of lines (enclosing rectangle).

        Args:
            lines (List[List[Segment]]): A list of lines.
            width (int): Desired width.
            height (int, optional): Desired height or None for no change.
            style (Style, optional): Style of any padding added.
            new_lines (bool, optional): Padded lines should include "\n". Defaults to False.

        Returns:
            List[List[Segment]]: New list of lines.
        """
        _height = height or len(lines)

        blank = (
            [cls(" " * width + "\n", style)] if new_lines else [cls(" " * width, style)]
        )

        adjust_line_length = cls.adjust_line_length
        shaped_lines = lines[:_height]
        shaped_lines[:] = [
            adjust_line_length(line, width, style=style) for line in lines
        ]
        if len(shaped_lines) < _height:
            shaped_lines.extend([blank] * (_height - len(shaped_lines)))
        return shaped_lines

    @classmethod
    def align_top(
        cls: Type["Segment"],
        lines: List[List["Segment"]],
        width: int,
        height: int,
        style: Style,
        new_lines: bool = False,
    ) -> List[List["Segment"]]:
        """Aligns lines to top (adds extra lines to bottom as required).

        Args:
            lines (List[List[Segment]]): A list of lines.
            width (int): Desired width.
            height (int, optional): Desired height or None for no change.
            style (Style): Style of any padding added.
            new_lines (bool, optional): Padded lines should include "\n". Defaults to False.

        Returns:
            List[List[Segment]]: New list of lines.
        """
        extra_lines = height - len(lines)
        if not extra_lines:
            return lines[:]
        lines = lines[:height]
        blank = cls(" " * width + "\n", style) if new_lines else cls(" " * width, style)
        lines = lines + [[blank]] * extra_lines
        return lines

    @classmethod
    def align_bottom(
        cls: Type["Segment"],
        lines: List[List["Segment"]],
        width: int,
        height: int,
        style: Style,
        new_lines: bool = False,
    ) -> List[List["Segment"]]:
        """Aligns render to bottom (adds extra lines above as required).

        Args:
            lines (List[List[Segment]]): A list of lines.
            width (int): Desired width.
            height (int, optional): Desired height or None for no change.
            style (Style): Style of any padding added. Defaults to None.
            new_lines (bool, optional): Padded lines should include "\n". Defaults to False.

        Returns:
            List[List[Segment]]: New list of lines.
        """
        extra_lines = height - len(lines)
        if not extra_lines:
            return lines[:]
        lines = lines[:height]
        blank = cls(" " * width + "\n", style) if new_lines else cls(" " * width, style)
        lines = [[blank]] * extra_lines + lines
        return lines

    @classmethod
    def align_middle(
        cls: Type["Segment"],
        lines: List[List["Segment"]],
        width: int,
        height: int,
        style: Style,
        new_lines: bool = False,
    ) -> List[List["Segment"]]:
        """Aligns lines to middle (adds extra lines to above and below as required).

        Args:
            lines (List[List[Segment]]): A list of lines.
            width (int): Desired width.
            height (int, optional): Desired height or None for no change.
            style (Style): Style of any padding added.
            new_lines (bool, optional): Padded lines should include "\n". Defaults to False.

        Returns:
            List[List[Segment]]: New list of lines.
        """
        extra_lines = height - len(lines)
        if not extra_lines:
            return lines[:]
        lines = lines[:height]
        blank = cls(" " * width + "\n", style) if new_lines else cls(" " * width, style)
        top_lines = extra_lines // 2
        bottom_lines = extra_lines - top_lines
        lines = [[blank]] * top_lines + lines + [[blank]] * bottom_lines
        return lines

    @classmethod
    def simplify(cls, segments: Iterable["Segment"]) -> Iterable["Segment"]:
        """Simplify an iterable of segments by combining contiguous segments with the same style.

        Args:
            segments (Iterable[Segment]): An iterable of segments.

        Returns:
            Iterable[Segment]: A possibly smaller iterable of segments that will render the same way.
        """
        iter_segments = iter(segments)
        try:
            last_segment = next(iter_segments)
        except StopIteration:
            return

        _Segment = Segment
        for segment in iter_segments:
            if last_segment.style == segment.style and not segment.control:
                last_segment = _Segment(
                    last_segment.text + segment.text, last_segment.style
                )
            else:
                yield last_segment
                last_segment = segment
        yield last_segment

    @classmethod
    def strip_links(cls, segments: Iterable["Segment"]) -> Iterable["Segment"]:
        """Remove all links from an iterable of styles.

        Args:
            segments (Iterable[Segment]): An iterable segments.

        Yields:
            Segment: Segments with link removed.
        """
        for segment in segments:
            if segment.control or segment.style is None:
                yield segment
            else:
                text, style, _control = segment
                yield cls(text, style.update_link(None) if style else None)

    @classmethod
    def strip_styles(cls, segments: Iterable["Segment"]) -> Iterable["Segment"]:
        """Remove all styles from an iterable of segments.

        Args:
            segments (Iterable[Segment]): An iterable segments.

        Yields:
            Segment: Segments with styles replace with None
        """
        for text, _style, control in segments:
            yield cls(text, None, control)

    @classmethod
    def remove_color(cls, segments: Iterable["Segment"]) -> Iterable["Segment"]:
        """Remove all color from an iterable of segments.

        Args:
            segments (Iterable[Segment]): An iterable segments.

        Yields:
            Segment: Segments with colorless style.
        """

        cache: Dict[Style, Style] = {}
        for text, style, control in segments:
            if style:
                colorless_style = cache.get(style)
                if colorless_style is None:
                    colorless_style = style.without_color
                    cache[style] = colorless_style
                yield cls(text, colorless_style, control)
            else:
                yield cls(text, None, control)

    @classmethod
    def divide(
        cls, segments: Iterable["Segment"], cuts: Iterable[int]
    ) -> Iterable[List["Segment"]]:
        """Divides an iterable of segments in to portions.

        Args:
            cuts (Iterable[int]): Cell positions where to divide.

        Yields:
            [Iterable[List[Segment]]]: An iterable of Segments in List.
        """
        split_segments: List["Segment"] = []
        add_segment = split_segments.append

        iter_cuts = iter(cuts)

        while True:
            cut = next(iter_cuts, -1)
            if cut == -1:
                return
            if cut != 0:
                break
            yield []
        pos = 0

        segments_clear = split_segments.clear
        segments_copy = split_segments.copy

        _cell_len = cached_cell_len
        for segment in segments:
            text, _style, control = segment
            while text:
                end_pos = pos if control else pos + _cell_len(text)
                if end_pos < cut:
                    add_segment(segment)
                    pos = end_pos
                    break

                if end_pos == cut:
                    add_segment(segment)
                    yield segments_copy()
                    segments_clear()
                    pos = end_pos

                    cut = next(iter_cuts, -1)
                    if cut == -1:
                        if split_segments:
                            yield segments_copy()
                        return

                    break

                else:
                    before, segment = segment.split_cells(cut - pos)
                    text, _style, control = segment
                    add_segment(before)
                    yield segments_copy()
                    segments_clear()
                    pos = cut

                cut = next(iter_cuts, -1)
                if cut == -1:
                    if split_segments:
                        yield segments_copy()
                    return

        yield segments_copy()


class Segments:
    """A simple renderable to render an iterable of segments. This class may be useful if
    you want to print segments outside of a __rich_console__ method.

    Args:
        segments (Iterable[Segment]): An iterable of segments.
        new_lines (bool, optional): Add new lines between segments. Defaults to False.
    """

    def __init__(self, segments: Iterable[Segment], new_lines: bool = False) -> None:
        self.segments = list(segments)
        self.new_lines = new_lines

    def __rich_console__(
        self, console: "Console", options: "ConsoleOptions"
    ) -> "RenderResult":
        if self.new_lines:
            line = Segment.line()
            for segment in self.segments:
                yield segment
                yield line
        else:
            yield from self.segments


class SegmentLines:
    def __init__(self, lines: Iterable[List[Segment]], new_lines: bool = False) -> None:
        """A simple renderable containing a number of lines of segments. May be used as an intermediate
        in rendering process.

        Args:
            lines (Iterable[List[Segment]]): Lists of segments forming lines.
            new_lines (bool, optional): Insert new lines after each line. Defaults to False.
        """
        self.lines = list(lines)
        self.new_lines = new_lines

    def __rich_console__(
        self, console: "Console", options: "ConsoleOptions"
    ) -> "RenderResult":
        if self.new_lines:
            new_line = Segment.line()
            for line in self.lines:
                yield from line
                yield new_line
        else:
            for line in self.lines:
                yield from line


if __name__ == "__main__":  # pragma: no cover
    from pip._vendor.rich.console import Console
    from pip._vendor.rich.syntax import Syntax
    from pip._vendor.rich.text import Text

    code = """from rich.console import Console
console = Console()
text = Text.from_markup("Hello, [bold magenta]World[/]!")
console.print(text)"""

    text = Text.from_markup("Hello, [bold magenta]World[/]!")

    console = Console()

    console.rule("rich.Segment")
    console.print(
        "A Segment is the last step in the Rich render process before generating text with ANSI codes."
    )
    console.print("\nConsider the following code:\n")
    console.print(Syntax(code, "python", line_numbers=True))
    console.print()
    console.print(
        "When you call [b]print()[/b], Rich [i]renders[/i] the object in to the following:\n"
    )
    fragments = list(console.render(text))
    console.print(fragments)
    console.print()
    console.print("The Segments are then processed to produce the following output:\n")
    console.print(text)
    console.print(
        "\nYou will only need to know this if you are implementing your own Rich renderables."
    )

# === NexusCore/openenv\Lib\site-packages\rich\segment.py ===
from enum import IntEnum
from functools import lru_cache
from itertools import filterfalse
from logging import getLogger
from operator import attrgetter
from typing import (
    TYPE_CHECKING,
    Dict,
    Iterable,
    List,
    NamedTuple,
    Optional,
    Sequence,
    Tuple,
    Type,
    Union,
)

from .cells import (
    _is_single_cell_widths,
    cached_cell_len,
    cell_len,
    get_character_cell_size,
    set_cell_size,
)
from .repr import Result, rich_repr
from .style import Style

if TYPE_CHECKING:
    from .console import Console, ConsoleOptions, RenderResult

log = getLogger("rich")


class ControlType(IntEnum):
    """Non-printable control codes which typically translate to ANSI codes."""

    BELL = 1
    CARRIAGE_RETURN = 2
    HOME = 3
    CLEAR = 4
    SHOW_CURSOR = 5
    HIDE_CURSOR = 6
    ENABLE_ALT_SCREEN = 7
    DISABLE_ALT_SCREEN = 8
    CURSOR_UP = 9
    CURSOR_DOWN = 10
    CURSOR_FORWARD = 11
    CURSOR_BACKWARD = 12
    CURSOR_MOVE_TO_COLUMN = 13
    CURSOR_MOVE_TO = 14
    ERASE_IN_LINE = 15
    SET_WINDOW_TITLE = 16


ControlCode = Union[
    Tuple[ControlType],
    Tuple[ControlType, Union[int, str]],
    Tuple[ControlType, int, int],
]


@rich_repr()
class Segment(NamedTuple):
    """A piece of text with associated style. Segments are produced by the Console render process and
    are ultimately converted in to strings to be written to the terminal.

    Args:
        text (str): A piece of text.
        style (:class:`~rich.style.Style`, optional): An optional style to apply to the text.
        control (Tuple[ControlCode], optional): Optional sequence of control codes.

    Attributes:
        cell_length (int): The cell length of this Segment.
    """

    text: str
    style: Optional[Style] = None
    control: Optional[Sequence[ControlCode]] = None

    @property
    def cell_length(self) -> int:
        """The number of terminal cells required to display self.text.

        Returns:
            int: A number of cells.
        """
        text, _style, control = self
        return 0 if control else cell_len(text)

    def __rich_repr__(self) -> Result:
        yield self.text
        if self.control is None:
            if self.style is not None:
                yield self.style
        else:
            yield self.style
            yield self.control

    def __bool__(self) -> bool:
        """Check if the segment contains text."""
        return bool(self.text)

    @property
    def is_control(self) -> bool:
        """Check if the segment contains control codes."""
        return self.control is not None

    @classmethod
    @lru_cache(1024 * 16)
    def _split_cells(cls, segment: "Segment", cut: int) -> Tuple["Segment", "Segment"]:
        """Split a segment in to two at a given cell position.

        Note that splitting a double-width character, may result in that character turning
        into two spaces.

        Args:
            segment (Segment): A segment to split.
            cut (int): A cell position to cut on.

        Returns:
            A tuple of two segments.
        """
        text, style, control = segment
        _Segment = Segment
        cell_length = segment.cell_length
        if cut >= cell_length:
            return segment, _Segment("", style, control)

        cell_size = get_character_cell_size

        pos = int((cut / cell_length) * len(text))

        while True:
            before = text[:pos]
            cell_pos = cell_len(before)
            out_by = cell_pos - cut
            if not out_by:
                return (
                    _Segment(before, style, control),
                    _Segment(text[pos:], style, control),
                )
            if out_by == -1 and cell_size(text[pos]) == 2:
                return (
                    _Segment(text[:pos] + " ", style, control),
                    _Segment(" " + text[pos + 1 :], style, control),
                )
            if out_by == +1 and cell_size(text[pos - 1]) == 2:
                return (
                    _Segment(text[: pos - 1] + " ", style, control),
                    _Segment(" " + text[pos:], style, control),
                )
            if cell_pos < cut:
                pos += 1
            else:
                pos -= 1

    def split_cells(self, cut: int) -> Tuple["Segment", "Segment"]:
        """Split segment in to two segments at the specified column.

        If the cut point falls in the middle of a 2-cell wide character then it is replaced
        by two spaces, to preserve the display width of the parent segment.

        Args:
            cut (int): Offset within the segment to cut.

        Returns:
            Tuple[Segment, Segment]: Two segments.
        """
        text, style, control = self
        assert cut >= 0

        if _is_single_cell_widths(text):
            # Fast path with all 1 cell characters
            if cut >= len(text):
                return self, Segment("", style, control)
            return (
                Segment(text[:cut], style, control),
                Segment(text[cut:], style, control),
            )

        return self._split_cells(self, cut)

    @classmethod
    def line(cls) -> "Segment":
        """Make a new line segment."""
        return cls("\n")

    @classmethod
    def apply_style(
        cls,
        segments: Iterable["Segment"],
        style: Optional[Style] = None,
        post_style: Optional[Style] = None,
    ) -> Iterable["Segment"]:
        """Apply style(s) to an iterable of segments.

        Returns an iterable of segments where the style is replaced by ``style + segment.style + post_style``.

        Args:
            segments (Iterable[Segment]): Segments to process.
            style (Style, optional): Base style. Defaults to None.
            post_style (Style, optional): Style to apply on top of segment style. Defaults to None.

        Returns:
            Iterable[Segments]: A new iterable of segments (possibly the same iterable).
        """
        result_segments = segments
        if style:
            apply = style.__add__
            result_segments = (
                cls(text, None if control else apply(_style), control)
                for text, _style, control in result_segments
            )
        if post_style:
            result_segments = (
                cls(
                    text,
                    (
                        None
                        if control
                        else (_style + post_style if _style else post_style)
                    ),
                    control,
                )
                for text, _style, control in result_segments
            )
        return result_segments

    @classmethod
    def filter_control(
        cls, segments: Iterable["Segment"], is_control: bool = False
    ) -> Iterable["Segment"]:
        """Filter segments by ``is_control`` attribute.

        Args:
            segments (Iterable[Segment]): An iterable of Segment instances.
            is_control (bool, optional): is_control flag to match in search.

        Returns:
            Iterable[Segment]: And iterable of Segment instances.

        """
        if is_control:
            return filter(attrgetter("control"), segments)
        else:
            return filterfalse(attrgetter("control"), segments)

    @classmethod
    def split_lines(cls, segments: Iterable["Segment"]) -> Iterable[List["Segment"]]:
        """Split a sequence of segments in to a list of lines.

        Args:
            segments (Iterable[Segment]): Segments potentially containing line feeds.

        Yields:
            Iterable[List[Segment]]: Iterable of segment lists, one per line.
        """
        line: List[Segment] = []
        append = line.append

        for segment in segments:
            if "\n" in segment.text and not segment.control:
                text, style, _ = segment
                while text:
                    _text, new_line, text = text.partition("\n")
                    if _text:
                        append(cls(_text, style))
                    if new_line:
                        yield line
                        line = []
                        append = line.append
            else:
                append(segment)
        if line:
            yield line

    @classmethod
    def split_and_crop_lines(
        cls,
        segments: Iterable["Segment"],
        length: int,
        style: Optional[Style] = None,
        pad: bool = True,
        include_new_lines: bool = True,
    ) -> Iterable[List["Segment"]]:
        """Split segments in to lines, and crop lines greater than a given length.

        Args:
            segments (Iterable[Segment]): An iterable of segments, probably
                generated from console.render.
            length (int): Desired line length.
            style (Style, optional): Style to use for any padding.
            pad (bool): Enable padding of lines that are less than `length`.

        Returns:
            Iterable[List[Segment]]: An iterable of lines of segments.
        """
        line: List[Segment] = []
        append = line.append

        adjust_line_length = cls.adjust_line_length
        new_line_segment = cls("\n")

        for segment in segments:
            if "\n" in segment.text and not segment.control:
                text, segment_style, _ = segment
                while text:
                    _text, new_line, text = text.partition("\n")
                    if _text:
                        append(cls(_text, segment_style))
                    if new_line:
                        cropped_line = adjust_line_length(
                            line, length, style=style, pad=pad
                        )
                        if include_new_lines:
                            cropped_line.append(new_line_segment)
                        yield cropped_line
                        line.clear()
            else:
                append(segment)
        if line:
            yield adjust_line_length(line, length, style=style, pad=pad)

    @classmethod
    def adjust_line_length(
        cls,
        line: List["Segment"],
        length: int,
        style: Optional[Style] = None,
        pad: bool = True,
    ) -> List["Segment"]:
        """Adjust a line to a given width (cropping or padding as required).

        Args:
            segments (Iterable[Segment]): A list of segments in a single line.
            length (int): The desired width of the line.
            style (Style, optional): The style of padding if used (space on the end). Defaults to None.
            pad (bool, optional): Pad lines with spaces if they are shorter than `length`. Defaults to True.

        Returns:
            List[Segment]: A line of segments with the desired length.
        """
        line_length = sum(segment.cell_length for segment in line)
        new_line: List[Segment]

        if line_length < length:
            if pad:
                new_line = line + [cls(" " * (length - line_length), style)]
            else:
                new_line = line[:]
        elif line_length > length:
            new_line = []
            append = new_line.append
            line_length = 0
            for segment in line:
                segment_length = segment.cell_length
                if line_length + segment_length < length or segment.control:
                    append(segment)
                    line_length += segment_length
                else:
                    text, segment_style, _ = segment
                    text = set_cell_size(text, length - line_length)
                    append(cls(text, segment_style))
                    break
        else:
            new_line = line[:]
        return new_line

    @classmethod
    def get_line_length(cls, line: List["Segment"]) -> int:
        """Get the length of list of segments.

        Args:
            line (List[Segment]): A line encoded as a list of Segments (assumes no '\\\\n' characters),

        Returns:
            int: The length of the line.
        """
        _cell_len = cell_len
        return sum(_cell_len(text) for text, style, control in line if not control)

    @classmethod
    def get_shape(cls, lines: List[List["Segment"]]) -> Tuple[int, int]:
        """Get the shape (enclosing rectangle) of a list of lines.

        Args:
            lines (List[List[Segment]]): A list of lines (no '\\\\n' characters).

        Returns:
            Tuple[int, int]: Width and height in characters.
        """
        get_line_length = cls.get_line_length
        max_width = max(get_line_length(line) for line in lines) if lines else 0
        return (max_width, len(lines))

    @classmethod
    def set_shape(
        cls,
        lines: List[List["Segment"]],
        width: int,
        height: Optional[int] = None,
        style: Optional[Style] = None,
        new_lines: bool = False,
    ) -> List[List["Segment"]]:
        """Set the shape of a list of lines (enclosing rectangle).

        Args:
            lines (List[List[Segment]]): A list of lines.
            width (int): Desired width.
            height (int, optional): Desired height or None for no change.
            style (Style, optional): Style of any padding added.
            new_lines (bool, optional): Padded lines should include "\n". Defaults to False.

        Returns:
            List[List[Segment]]: New list of lines.
        """
        _height = height or len(lines)

        blank = (
            [cls(" " * width + "\n", style)] if new_lines else [cls(" " * width, style)]
        )

        adjust_line_length = cls.adjust_line_length
        shaped_lines = lines[:_height]
        shaped_lines[:] = [
            adjust_line_length(line, width, style=style) for line in lines
        ]
        if len(shaped_lines) < _height:
            shaped_lines.extend([blank] * (_height - len(shaped_lines)))
        return shaped_lines

    @classmethod
    def align_top(
        cls: Type["Segment"],
        lines: List[List["Segment"]],
        width: int,
        height: int,
        style: Style,
        new_lines: bool = False,
    ) -> List[List["Segment"]]:
        """Aligns lines to top (adds extra lines to bottom as required).

        Args:
            lines (List[List[Segment]]): A list of lines.
            width (int): Desired width.
            height (int, optional): Desired height or None for no change.
            style (Style): Style of any padding added.
            new_lines (bool, optional): Padded lines should include "\n". Defaults to False.

        Returns:
            List[List[Segment]]: New list of lines.
        """
        extra_lines = height - len(lines)
        if not extra_lines:
            return lines[:]
        lines = lines[:height]
        blank = cls(" " * width + "\n", style) if new_lines else cls(" " * width, style)
        lines = lines + [[blank]] * extra_lines
        return lines

    @classmethod
    def align_bottom(
        cls: Type["Segment"],
        lines: List[List["Segment"]],
        width: int,
        height: int,
        style: Style,
        new_lines: bool = False,
    ) -> List[List["Segment"]]:
        """Aligns render to bottom (adds extra lines above as required).

        Args:
            lines (List[List[Segment]]): A list of lines.
            width (int): Desired width.
            height (int, optional): Desired height or None for no change.
            style (Style): Style of any padding added. Defaults to None.
            new_lines (bool, optional): Padded lines should include "\n". Defaults to False.

        Returns:
            List[List[Segment]]: New list of lines.
        """
        extra_lines = height - len(lines)
        if not extra_lines:
            return lines[:]
        lines = lines[:height]
        blank = cls(" " * width + "\n", style) if new_lines else cls(" " * width, style)
        lines = [[blank]] * extra_lines + lines
        return lines

    @classmethod
    def align_middle(
        cls: Type["Segment"],
        lines: List[List["Segment"]],
        width: int,
        height: int,
        style: Style,
        new_lines: bool = False,
    ) -> List[List["Segment"]]:
        """Aligns lines to middle (adds extra lines to above and below as required).

        Args:
            lines (List[List[Segment]]): A list of lines.
            width (int): Desired width.
            height (int, optional): Desired height or None for no change.
            style (Style): Style of any padding added.
            new_lines (bool, optional): Padded lines should include "\n". Defaults to False.

        Returns:
            List[List[Segment]]: New list of lines.
        """
        extra_lines = height - len(lines)
        if not extra_lines:
            return lines[:]
        lines = lines[:height]
        blank = cls(" " * width + "\n", style) if new_lines else cls(" " * width, style)
        top_lines = extra_lines // 2
        bottom_lines = extra_lines - top_lines
        lines = [[blank]] * top_lines + lines + [[blank]] * bottom_lines
        return lines

    @classmethod
    def simplify(cls, segments: Iterable["Segment"]) -> Iterable["Segment"]:
        """Simplify an iterable of segments by combining contiguous segments with the same style.

        Args:
            segments (Iterable[Segment]): An iterable of segments.

        Returns:
            Iterable[Segment]: A possibly smaller iterable of segments that will render the same way.
        """
        iter_segments = iter(segments)
        try:
            last_segment = next(iter_segments)
        except StopIteration:
            return

        _Segment = Segment
        for segment in iter_segments:
            if last_segment.style == segment.style and not segment.control:
                last_segment = _Segment(
                    last_segment.text + segment.text, last_segment.style
                )
            else:
                yield last_segment
                last_segment = segment
        yield last_segment

    @classmethod
    def strip_links(cls, segments: Iterable["Segment"]) -> Iterable["Segment"]:
        """Remove all links from an iterable of styles.

        Args:
            segments (Iterable[Segment]): An iterable segments.

        Yields:
            Segment: Segments with link removed.
        """
        for segment in segments:
            if segment.control or segment.style is None:
                yield segment
            else:
                text, style, _control = segment
                yield cls(text, style.update_link(None) if style else None)

    @classmethod
    def strip_styles(cls, segments: Iterable["Segment"]) -> Iterable["Segment"]:
        """Remove all styles from an iterable of segments.

        Args:
            segments (Iterable[Segment]): An iterable segments.

        Yields:
            Segment: Segments with styles replace with None
        """
        for text, _style, control in segments:
            yield cls(text, None, control)

    @classmethod
    def remove_color(cls, segments: Iterable["Segment"]) -> Iterable["Segment"]:
        """Remove all color from an iterable of segments.

        Args:
            segments (Iterable[Segment]): An iterable segments.

        Yields:
            Segment: Segments with colorless style.
        """

        cache: Dict[Style, Style] = {}
        for text, style, control in segments:
            if style:
                colorless_style = cache.get(style)
                if colorless_style is None:
                    colorless_style = style.without_color
                    cache[style] = colorless_style
                yield cls(text, colorless_style, control)
            else:
                yield cls(text, None, control)

    @classmethod
    def divide(
        cls, segments: Iterable["Segment"], cuts: Iterable[int]
    ) -> Iterable[List["Segment"]]:
        """Divides an iterable of segments in to portions.

        Args:
            cuts (Iterable[int]): Cell positions where to divide.

        Yields:
            [Iterable[List[Segment]]]: An iterable of Segments in List.
        """
        split_segments: List["Segment"] = []
        add_segment = split_segments.append

        iter_cuts = iter(cuts)

        while True:
            cut = next(iter_cuts, -1)
            if cut == -1:
                return
            if cut != 0:
                break
            yield []
        pos = 0

        segments_clear = split_segments.clear
        segments_copy = split_segments.copy

        _cell_len = cached_cell_len
        for segment in segments:
            text, _style, control = segment
            while text:
                end_pos = pos if control else pos + _cell_len(text)
                if end_pos < cut:
                    add_segment(segment)
                    pos = end_pos
                    break

                if end_pos == cut:
                    add_segment(segment)
                    yield segments_copy()
                    segments_clear()
                    pos = end_pos

                    cut = next(iter_cuts, -1)
                    if cut == -1:
                        if split_segments:
                            yield segments_copy()
                        return

                    break

                else:
                    before, segment = segment.split_cells(cut - pos)
                    text, _style, control = segment
                    add_segment(before)
                    yield segments_copy()
                    segments_clear()
                    pos = cut

                cut = next(iter_cuts, -1)
                if cut == -1:
                    if split_segments:
                        yield segments_copy()
                    return

        yield segments_copy()


class Segments:
    """A simple renderable to render an iterable of segments. This class may be useful if
    you want to print segments outside of a __rich_console__ method.

    Args:
        segments (Iterable[Segment]): An iterable of segments.
        new_lines (bool, optional): Add new lines between segments. Defaults to False.
    """

    def __init__(self, segments: Iterable[Segment], new_lines: bool = False) -> None:
        self.segments = list(segments)
        self.new_lines = new_lines

    def __rich_console__(
        self, console: "Console", options: "ConsoleOptions"
    ) -> "RenderResult":
        if self.new_lines:
            line = Segment.line()
            for segment in self.segments:
                yield segment
                yield line
        else:
            yield from self.segments


class SegmentLines:
    def __init__(self, lines: Iterable[List[Segment]], new_lines: bool = False) -> None:
        """A simple renderable containing a number of lines of segments. May be used as an intermediate
        in rendering process.

        Args:
            lines (Iterable[List[Segment]]): Lists of segments forming lines.
            new_lines (bool, optional): Insert new lines after each line. Defaults to False.
        """
        self.lines = list(lines)
        self.new_lines = new_lines

    def __rich_console__(
        self, console: "Console", options: "ConsoleOptions"
    ) -> "RenderResult":
        if self.new_lines:
            new_line = Segment.line()
            for line in self.lines:
                yield from line
                yield new_line
        else:
            for line in self.lines:
                yield from line


if __name__ == "__main__":  # pragma: no cover
    from rich.console import Console
    from rich.syntax import Syntax
    from rich.text import Text

    code = """from rich.console import Console
console = Console()
text = Text.from_markup("Hello, [bold magenta]World[/]!")
console.print(text)"""

    text = Text.from_markup("Hello, [bold magenta]World[/]!")

    console = Console()

    console.rule("rich.Segment")
    console.print(
        "A Segment is the last step in the Rich render process before generating text with ANSI codes."
    )
    console.print("\nConsider the following code:\n")
    console.print(Syntax(code, "python", line_numbers=True))
    console.print()
    console.print(
        "When you call [b]print()[/b], Rich [i]renders[/i] the object in to the following:\n"
    )
    fragments = list(console.render(text))
    console.print(fragments)
    console.print()
    console.print("The Segments are then processed to produce the following output:\n")
    console.print(text)
    console.print(
        "\nYou will only need to know this if you are implementing your own Rich renderables."
    )

# === NexusCore/openenv\Lib\site-packages\fontTools\ttLib\tables\O_S_2f_2.py ===
from fontTools.misc import sstruct
from fontTools.misc.roundTools import otRound
from fontTools.misc.textTools import safeEval, num2binary, binary2num
from fontTools.ttLib.tables import DefaultTable
import bisect
import logging


log = logging.getLogger(__name__)

# panose classification

panoseFormat = """
	bFamilyType:        B
	bSerifStyle:        B
	bWeight:            B
	bProportion:        B
	bContrast:          B
	bStrokeVariation:   B
	bArmStyle:          B
	bLetterForm:        B
	bMidline:           B
	bXHeight:           B
"""


class Panose(object):
    def __init__(self, **kwargs):
        _, names, _ = sstruct.getformat(panoseFormat)
        for name in names:
            setattr(self, name, kwargs.pop(name, 0))
        for k in kwargs:
            raise TypeError(f"Panose() got an unexpected keyword argument {k!r}")

    def toXML(self, writer, ttFont):
        formatstring, names, fixes = sstruct.getformat(panoseFormat)
        for name in names:
            writer.simpletag(name, value=getattr(self, name))
            writer.newline()

    def fromXML(self, name, attrs, content, ttFont):
        setattr(self, name, safeEval(attrs["value"]))


# 'sfnt' OS/2 and Windows Metrics table - 'OS/2'

OS2_format_0 = """
	>   # big endian
	version:                H       # version
	xAvgCharWidth:          h       # average character width
	usWeightClass:          H       # degree of thickness of strokes
	usWidthClass:           H       # aspect ratio
	fsType:                 H       # type flags
	ySubscriptXSize:        h       # subscript horizontal font size
	ySubscriptYSize:        h       # subscript vertical font size
	ySubscriptXOffset:      h       # subscript x offset
	ySubscriptYOffset:      h       # subscript y offset
	ySuperscriptXSize:      h       # superscript horizontal font size
	ySuperscriptYSize:      h       # superscript vertical font size
	ySuperscriptXOffset:    h       # superscript x offset
	ySuperscriptYOffset:    h       # superscript y offset
	yStrikeoutSize:         h       # strikeout size
	yStrikeoutPosition:     h       # strikeout position
	sFamilyClass:           h       # font family class and subclass
	panose:                 10s     # panose classification number
	ulUnicodeRange1:        L       # character range
	ulUnicodeRange2:        L       # character range
	ulUnicodeRange3:        L       # character range
	ulUnicodeRange4:        L       # character range
	achVendID:              4s      # font vendor identification
	fsSelection:            H       # font selection flags
	usFirstCharIndex:       H       # first unicode character index
	usLastCharIndex:        H       # last unicode character index
	sTypoAscender:          h       # typographic ascender
	sTypoDescender:         h       # typographic descender
	sTypoLineGap:           h       # typographic line gap
	usWinAscent:            H       # Windows ascender
	usWinDescent:           H       # Windows descender
"""

OS2_format_1_addition = """
	ulCodePageRange1:   L
	ulCodePageRange2:   L
"""

OS2_format_2_addition = (
    OS2_format_1_addition
    + """
	sxHeight:           h
	sCapHeight:         h
	usDefaultChar:      H
	usBreakChar:        H
	usMaxContext:       H
"""
)

OS2_format_5_addition = (
    OS2_format_2_addition
    + """
	usLowerOpticalPointSize:    H
	usUpperOpticalPointSize:    H
"""
)

bigendian = "	>	# big endian\n"

OS2_format_1 = OS2_format_0 + OS2_format_1_addition
OS2_format_2 = OS2_format_0 + OS2_format_2_addition
OS2_format_5 = OS2_format_0 + OS2_format_5_addition
OS2_format_1_addition = bigendian + OS2_format_1_addition
OS2_format_2_addition = bigendian + OS2_format_2_addition
OS2_format_5_addition = bigendian + OS2_format_5_addition


class table_O_S_2f_2(DefaultTable.DefaultTable):
    """OS/2 and Windows Metrics table

    The ``OS/2`` table contains a variety of font-wide metrics and
    parameters that may be useful to an operating system or other
    software for system-integration purposes.

    See also https://learn.microsoft.com/en-us/typography/opentype/spec/os2
    """

    dependencies = ["head"]

    def decompile(self, data, ttFont):
        dummy, data = sstruct.unpack2(OS2_format_0, data, self)

        if self.version == 1:
            dummy, data = sstruct.unpack2(OS2_format_1_addition, data, self)
        elif self.version in (2, 3, 4):
            dummy, data = sstruct.unpack2(OS2_format_2_addition, data, self)
        elif self.version == 5:
            dummy, data = sstruct.unpack2(OS2_format_5_addition, data, self)
            self.usLowerOpticalPointSize /= 20
            self.usUpperOpticalPointSize /= 20
        elif self.version != 0:
            from fontTools import ttLib

            raise ttLib.TTLibError(
                "unknown format for OS/2 table: version %s" % self.version
            )
        if len(data):
            log.warning("too much 'OS/2' table data")

        self.panose = sstruct.unpack(panoseFormat, self.panose, Panose())

    def compile(self, ttFont):
        self.updateFirstAndLastCharIndex(ttFont)
        panose = self.panose
        head = ttFont["head"]
        if (self.fsSelection & 1) and not (head.macStyle & 1 << 1):
            log.warning(
                "fsSelection bit 0 (italic) and "
                "head table macStyle bit 1 (italic) should match"
            )
        if (self.fsSelection & 1 << 5) and not (head.macStyle & 1):
            log.warning(
                "fsSelection bit 5 (bold) and "
                "head table macStyle bit 0 (bold) should match"
            )
        if (self.fsSelection & 1 << 6) and (self.fsSelection & 1 + (1 << 5)):
            log.warning(
                "fsSelection bit 6 (regular) is set, "
                "bits 0 (italic) and 5 (bold) must be clear"
            )
        if self.version < 4 and self.fsSelection & 0b1110000000:
            log.warning(
                "fsSelection bits 7, 8 and 9 are only defined in "
                "OS/2 table version 4 and up: version %s",
                self.version,
            )
        self.panose = sstruct.pack(panoseFormat, self.panose)
        if self.version == 0:
            data = sstruct.pack(OS2_format_0, self)
        elif self.version == 1:
            data = sstruct.pack(OS2_format_1, self)
        elif self.version in (2, 3, 4):
            data = sstruct.pack(OS2_format_2, self)
        elif self.version == 5:
            d = self.__dict__.copy()
            d["usLowerOpticalPointSize"] = round(self.usLowerOpticalPointSize * 20)
            d["usUpperOpticalPointSize"] = round(self.usUpperOpticalPointSize * 20)
            data = sstruct.pack(OS2_format_5, d)
        else:
            from fontTools import ttLib

            raise ttLib.TTLibError(
                "unknown format for OS/2 table: version %s" % self.version
            )
        self.panose = panose
        return data

    def toXML(self, writer, ttFont):
        writer.comment(
            "The fields 'usFirstCharIndex' and 'usLastCharIndex'\n"
            "will be recalculated by the compiler"
        )
        writer.newline()
        if self.version == 1:
            format = OS2_format_1
        elif self.version in (2, 3, 4):
            format = OS2_format_2
        elif self.version == 5:
            format = OS2_format_5
        else:
            format = OS2_format_0
        formatstring, names, fixes = sstruct.getformat(format)
        for name in names:
            value = getattr(self, name)
            if name == "panose":
                writer.begintag("panose")
                writer.newline()
                value.toXML(writer, ttFont)
                writer.endtag("panose")
            elif name in (
                "ulUnicodeRange1",
                "ulUnicodeRange2",
                "ulUnicodeRange3",
                "ulUnicodeRange4",
                "ulCodePageRange1",
                "ulCodePageRange2",
            ):
                writer.simpletag(name, value=num2binary(value))
            elif name in ("fsType", "fsSelection"):
                writer.simpletag(name, value=num2binary(value, 16))
            elif name == "achVendID":
                writer.simpletag(name, value=repr(value)[1:-1])
            else:
                writer.simpletag(name, value=value)
            writer.newline()

    def fromXML(self, name, attrs, content, ttFont):
        if name == "panose":
            self.panose = panose = Panose()
            for element in content:
                if isinstance(element, tuple):
                    name, attrs, content = element
                    panose.fromXML(name, attrs, content, ttFont)
        elif name in (
            "ulUnicodeRange1",
            "ulUnicodeRange2",
            "ulUnicodeRange3",
            "ulUnicodeRange4",
            "ulCodePageRange1",
            "ulCodePageRange2",
            "fsType",
            "fsSelection",
        ):
            setattr(self, name, binary2num(attrs["value"]))
        elif name == "achVendID":
            setattr(self, name, safeEval("'''" + attrs["value"] + "'''"))
        else:
            setattr(self, name, safeEval(attrs["value"]))

    def updateFirstAndLastCharIndex(self, ttFont):
        if "cmap" not in ttFont:
            return
        codes = set()
        for table in getattr(ttFont["cmap"], "tables", []):
            if table.isUnicode():
                codes.update(table.cmap.keys())
        if codes:
            minCode = min(codes)
            maxCode = max(codes)
            # USHORT cannot hold codepoints greater than 0xFFFF
            self.usFirstCharIndex = min(0xFFFF, minCode)
            self.usLastCharIndex = min(0xFFFF, maxCode)

    # misspelled attributes kept for legacy reasons

    @property
    def usMaxContex(self):
        return self.usMaxContext

    @usMaxContex.setter
    def usMaxContex(self, value):
        self.usMaxContext = value

    @property
    def fsFirstCharIndex(self):
        return self.usFirstCharIndex

    @fsFirstCharIndex.setter
    def fsFirstCharIndex(self, value):
        self.usFirstCharIndex = value

    @property
    def fsLastCharIndex(self):
        return self.usLastCharIndex

    @fsLastCharIndex.setter
    def fsLastCharIndex(self, value):
        self.usLastCharIndex = value

    def getUnicodeRanges(self):
        """Return the set of 'ulUnicodeRange*' bits currently enabled."""
        bits = set()
        ul1, ul2 = self.ulUnicodeRange1, self.ulUnicodeRange2
        ul3, ul4 = self.ulUnicodeRange3, self.ulUnicodeRange4
        for i in range(32):
            if ul1 & (1 << i):
                bits.add(i)
            if ul2 & (1 << i):
                bits.add(i + 32)
            if ul3 & (1 << i):
                bits.add(i + 64)
            if ul4 & (1 << i):
                bits.add(i + 96)
        return bits

    def setUnicodeRanges(self, bits):
        """Set the 'ulUnicodeRange*' fields to the specified 'bits'."""
        ul1, ul2, ul3, ul4 = 0, 0, 0, 0
        for bit in bits:
            if 0 <= bit < 32:
                ul1 |= 1 << bit
            elif 32 <= bit < 64:
                ul2 |= 1 << (bit - 32)
            elif 64 <= bit < 96:
                ul3 |= 1 << (bit - 64)
            elif 96 <= bit < 123:
                ul4 |= 1 << (bit - 96)
            else:
                raise ValueError("expected 0 <= int <= 122, found: %r" % bit)
        self.ulUnicodeRange1, self.ulUnicodeRange2 = ul1, ul2
        self.ulUnicodeRange3, self.ulUnicodeRange4 = ul3, ul4

    def recalcUnicodeRanges(self, ttFont, pruneOnly=False):
        """Intersect the codepoints in the font's Unicode cmap subtables with
        the Unicode block ranges defined in the OpenType specification (v1.7),
        and set the respective 'ulUnicodeRange*' bits if there is at least ONE
        intersection.
        If 'pruneOnly' is True, only clear unused bits with NO intersection.
        """
        unicodes = set()
        for table in ttFont["cmap"].tables:
            if table.isUnicode():
                unicodes.update(table.cmap.keys())
        if pruneOnly:
            empty = intersectUnicodeRanges(unicodes, inverse=True)
            bits = self.getUnicodeRanges() - empty
        else:
            bits = intersectUnicodeRanges(unicodes)
        self.setUnicodeRanges(bits)
        return bits

    def getCodePageRanges(self):
        """Return the set of 'ulCodePageRange*' bits currently enabled."""
        bits = set()
        if self.version < 1:
            return bits
        ul1, ul2 = self.ulCodePageRange1, self.ulCodePageRange2
        for i in range(32):
            if ul1 & (1 << i):
                bits.add(i)
            if ul2 & (1 << i):
                bits.add(i + 32)
        return bits

    def setCodePageRanges(self, bits):
        """Set the 'ulCodePageRange*' fields to the specified 'bits'."""
        ul1, ul2 = 0, 0
        for bit in bits:
            if 0 <= bit < 32:
                ul1 |= 1 << bit
            elif 32 <= bit < 64:
                ul2 |= 1 << (bit - 32)
            else:
                raise ValueError(f"expected 0 <= int <= 63, found: {bit:r}")
        if self.version < 1:
            self.version = 1
        self.ulCodePageRange1, self.ulCodePageRange2 = ul1, ul2

    def recalcCodePageRanges(self, ttFont, pruneOnly=False):
        unicodes = set()
        for table in ttFont["cmap"].tables:
            if table.isUnicode():
                unicodes.update(table.cmap.keys())
        bits = calcCodePageRanges(unicodes)
        if pruneOnly:
            bits &= self.getCodePageRanges()
        # when no codepage ranges can be enabled, fall back to enabling bit 0
        # (Latin 1) so that the font works in MS Word:
        # https://github.com/googlei18n/fontmake/issues/468
        if not bits:
            bits = {0}
        self.setCodePageRanges(bits)
        return bits

    def recalcAvgCharWidth(self, ttFont):
        """Recalculate xAvgCharWidth using metrics from ttFont's 'hmtx' table.

        Set it to 0 if the unlikely event 'hmtx' table is not found.
        """
        avg_width = 0
        hmtx = ttFont.get("hmtx")
        if hmtx is not None:
            widths = [width for width, _ in hmtx.metrics.values() if width > 0]
            if widths:
                avg_width = otRound(sum(widths) / len(widths))
        self.xAvgCharWidth = avg_width
        return avg_width


# Unicode ranges data from the OpenType OS/2 table specification v1.7

OS2_UNICODE_RANGES = (
    (("Basic Latin", (0x0000, 0x007F)),),
    (("Latin-1 Supplement", (0x0080, 0x00FF)),),
    (("Latin Extended-A", (0x0100, 0x017F)),),
    (("Latin Extended-B", (0x0180, 0x024F)),),
    (
        ("IPA Extensions", (0x0250, 0x02AF)),
        ("Phonetic Extensions", (0x1D00, 0x1D7F)),
        ("Phonetic Extensions Supplement", (0x1D80, 0x1DBF)),
    ),
    (
        ("Spacing Modifier Letters", (0x02B0, 0x02FF)),
        ("Modifier Tone Letters", (0xA700, 0xA71F)),
    ),
    (
        ("Combining Diacritical Marks", (0x0300, 0x036F)),
        ("Combining Diacritical Marks Supplement", (0x1DC0, 0x1DFF)),
    ),
    (("Greek and Coptic", (0x0370, 0x03FF)),),
    (("Coptic", (0x2C80, 0x2CFF)),),
    (
        ("Cyrillic", (0x0400, 0x04FF)),
        ("Cyrillic Supplement", (0x0500, 0x052F)),
        ("Cyrillic Extended-A", (0x2DE0, 0x2DFF)),
        ("Cyrillic Extended-B", (0xA640, 0xA69F)),
    ),
    (("Armenian", (0x0530, 0x058F)),),
    (("Hebrew", (0x0590, 0x05FF)),),
    (("Vai", (0xA500, 0xA63F)),),
    (("Arabic", (0x0600, 0x06FF)), ("Arabic Supplement", (0x0750, 0x077F))),
    (("NKo", (0x07C0, 0x07FF)),),
    (("Devanagari", (0x0900, 0x097F)),),
    (("Bengali", (0x0980, 0x09FF)),),
    (("Gurmukhi", (0x0A00, 0x0A7F)),),
    (("Gujarati", (0x0A80, 0x0AFF)),),
    (("Oriya", (0x0B00, 0x0B7F)),),
    (("Tamil", (0x0B80, 0x0BFF)),),
    (("Telugu", (0x0C00, 0x0C7F)),),
    (("Kannada", (0x0C80, 0x0CFF)),),
    (("Malayalam", (0x0D00, 0x0D7F)),),
    (("Thai", (0x0E00, 0x0E7F)),),
    (("Lao", (0x0E80, 0x0EFF)),),
    (("Georgian", (0x10A0, 0x10FF)), ("Georgian Supplement", (0x2D00, 0x2D2F))),
    (("Balinese", (0x1B00, 0x1B7F)),),
    (("Hangul Jamo", (0x1100, 0x11FF)),),
    (
        ("Latin Extended Additional", (0x1E00, 0x1EFF)),
        ("Latin Extended-C", (0x2C60, 0x2C7F)),
        ("Latin Extended-D", (0xA720, 0xA7FF)),
    ),
    (("Greek Extended", (0x1F00, 0x1FFF)),),
    (
        ("General Punctuation", (0x2000, 0x206F)),
        ("Supplemental Punctuation", (0x2E00, 0x2E7F)),
    ),
    (("Superscripts And Subscripts", (0x2070, 0x209F)),),
    (("Currency Symbols", (0x20A0, 0x20CF)),),
    (("Combining Diacritical Marks For Symbols", (0x20D0, 0x20FF)),),
    (("Letterlike Symbols", (0x2100, 0x214F)),),
    (("Number Forms", (0x2150, 0x218F)),),
    (
        ("Arrows", (0x2190, 0x21FF)),
        ("Supplemental Arrows-A", (0x27F0, 0x27FF)),
        ("Supplemental Arrows-B", (0x2900, 0x297F)),
        ("Miscellaneous Symbols and Arrows", (0x2B00, 0x2BFF)),
    ),
    (
        ("Mathematical Operators", (0x2200, 0x22FF)),
        ("Supplemental Mathematical Operators", (0x2A00, 0x2AFF)),
        ("Miscellaneous Mathematical Symbols-A", (0x27C0, 0x27EF)),
        ("Miscellaneous Mathematical Symbols-B", (0x2980, 0x29FF)),
    ),
    (("Miscellaneous Technical", (0x2300, 0x23FF)),),
    (("Control Pictures", (0x2400, 0x243F)),),
    (("Optical Character Recognition", (0x2440, 0x245F)),),
    (("Enclosed Alphanumerics", (0x2460, 0x24FF)),),
    (("Box Drawing", (0x2500, 0x257F)),),
    (("Block Elements", (0x2580, 0x259F)),),
    (("Geometric Shapes", (0x25A0, 0x25FF)),),
    (("Miscellaneous Symbols", (0x2600, 0x26FF)),),
    (("Dingbats", (0x2700, 0x27BF)),),
    (("CJK Symbols And Punctuation", (0x3000, 0x303F)),),
    (("Hiragana", (0x3040, 0x309F)),),
    (
        ("Katakana", (0x30A0, 0x30FF)),
        ("Katakana Phonetic Extensions", (0x31F0, 0x31FF)),
    ),
    (("Bopomofo", (0x3100, 0x312F)), ("Bopomofo Extended", (0x31A0, 0x31BF))),
    (("Hangul Compatibility Jamo", (0x3130, 0x318F)),),
    (("Phags-pa", (0xA840, 0xA87F)),),
    (("Enclosed CJK Letters And Months", (0x3200, 0x32FF)),),
    (("CJK Compatibility", (0x3300, 0x33FF)),),
    (("Hangul Syllables", (0xAC00, 0xD7AF)),),
    (("Non-Plane 0 *", (0xD800, 0xDFFF)),),
    (("Phoenician", (0x10900, 0x1091F)),),
    (
        ("CJK Unified Ideographs", (0x4E00, 0x9FFF)),
        ("CJK Radicals Supplement", (0x2E80, 0x2EFF)),
        ("Kangxi Radicals", (0x2F00, 0x2FDF)),
        ("Ideographic Description Characters", (0x2FF0, 0x2FFF)),
        ("CJK Unified Ideographs Extension A", (0x3400, 0x4DBF)),
        ("CJK Unified Ideographs Extension B", (0x20000, 0x2A6DF)),
        ("Kanbun", (0x3190, 0x319F)),
    ),
    (("Private Use Area (plane 0)", (0xE000, 0xF8FF)),),
    (
        ("CJK Strokes", (0x31C0, 0x31EF)),
        ("CJK Compatibility Ideographs", (0xF900, 0xFAFF)),
        ("CJK Compatibility Ideographs Supplement", (0x2F800, 0x2FA1F)),
    ),
    (("Alphabetic Presentation Forms", (0xFB00, 0xFB4F)),),
    (("Arabic Presentation Forms-A", (0xFB50, 0xFDFF)),),
    (("Combining Half Marks", (0xFE20, 0xFE2F)),),
    (
        ("Vertical Forms", (0xFE10, 0xFE1F)),
        ("CJK Compatibility Forms", (0xFE30, 0xFE4F)),
    ),
    (("Small Form Variants", (0xFE50, 0xFE6F)),),
    (("Arabic Presentation Forms-B", (0xFE70, 0xFEFF)),),
    (("Halfwidth And Fullwidth Forms", (0xFF00, 0xFFEF)),),
    (("Specials", (0xFFF0, 0xFFFF)),),
    (("Tibetan", (0x0F00, 0x0FFF)),),
    (("Syriac", (0x0700, 0x074F)),),
    (("Thaana", (0x0780, 0x07BF)),),
    (("Sinhala", (0x0D80, 0x0DFF)),),
    (("Myanmar", (0x1000, 0x109F)),),
    (
        ("Ethiopic", (0x1200, 0x137F)),
        ("Ethiopic Supplement", (0x1380, 0x139F)),
        ("Ethiopic Extended", (0x2D80, 0x2DDF)),
    ),
    (("Cherokee", (0x13A0, 0x13FF)),),
    (("Unified Canadian Aboriginal Syllabics", (0x1400, 0x167F)),),
    (("Ogham", (0x1680, 0x169F)),),
    (("Runic", (0x16A0, 0x16FF)),),
    (("Khmer", (0x1780, 0x17FF)), ("Khmer Symbols", (0x19E0, 0x19FF))),
    (("Mongolian", (0x1800, 0x18AF)),),
    (("Braille Patterns", (0x2800, 0x28FF)),),
    (("Yi Syllables", (0xA000, 0xA48F)), ("Yi Radicals", (0xA490, 0xA4CF))),
    (
        ("Tagalog", (0x1700, 0x171F)),
        ("Hanunoo", (0x1720, 0x173F)),
        ("Buhid", (0x1740, 0x175F)),
        ("Tagbanwa", (0x1760, 0x177F)),
    ),
    (("Old Italic", (0x10300, 0x1032F)),),
    (("Gothic", (0x10330, 0x1034F)),),
    (("Deseret", (0x10400, 0x1044F)),),
    (
        ("Byzantine Musical Symbols", (0x1D000, 0x1D0FF)),
        ("Musical Symbols", (0x1D100, 0x1D1FF)),
        ("Ancient Greek Musical Notation", (0x1D200, 0x1D24F)),
    ),
    (("Mathematical Alphanumeric Symbols", (0x1D400, 0x1D7FF)),),
    (
        ("Private Use (plane 15)", (0xF0000, 0xFFFFD)),
        ("Private Use (plane 16)", (0x100000, 0x10FFFD)),
    ),
    (
        ("Variation Selectors", (0xFE00, 0xFE0F)),
        ("Variation Selectors Supplement", (0xE0100, 0xE01EF)),
    ),
    (("Tags", (0xE0000, 0xE007F)),),
    (("Limbu", (0x1900, 0x194F)),),
    (("Tai Le", (0x1950, 0x197F)),),
    (("New Tai Lue", (0x1980, 0x19DF)),),
    (("Buginese", (0x1A00, 0x1A1F)),),
    (("Glagolitic", (0x2C00, 0x2C5F)),),
    (("Tifinagh", (0x2D30, 0x2D7F)),),
    (("Yijing Hexagram Symbols", (0x4DC0, 0x4DFF)),),
    (("Syloti Nagri", (0xA800, 0xA82F)),),
    (
        ("Linear B Syllabary", (0x10000, 0x1007F)),
        ("Linear B Ideograms", (0x10080, 0x100FF)),
        ("Aegean Numbers", (0x10100, 0x1013F)),
    ),
    (("Ancient Greek Numbers", (0x10140, 0x1018F)),),
    (("Ugaritic", (0x10380, 0x1039F)),),
    (("Old Persian", (0x103A0, 0x103DF)),),
    (("Shavian", (0x10450, 0x1047F)),),
    (("Osmanya", (0x10480, 0x104AF)),),
    (("Cypriot Syllabary", (0x10800, 0x1083F)),),
    (("Kharoshthi", (0x10A00, 0x10A5F)),),
    (("Tai Xuan Jing Symbols", (0x1D300, 0x1D35F)),),
    (
        ("Cuneiform", (0x12000, 0x123FF)),
        ("Cuneiform Numbers and Punctuation", (0x12400, 0x1247F)),
    ),
    (("Counting Rod Numerals", (0x1D360, 0x1D37F)),),
    (("Sundanese", (0x1B80, 0x1BBF)),),
    (("Lepcha", (0x1C00, 0x1C4F)),),
    (("Ol Chiki", (0x1C50, 0x1C7F)),),
    (("Saurashtra", (0xA880, 0xA8DF)),),
    (("Kayah Li", (0xA900, 0xA92F)),),
    (("Rejang", (0xA930, 0xA95F)),),
    (("Cham", (0xAA00, 0xAA5F)),),
    (("Ancient Symbols", (0x10190, 0x101CF)),),
    (("Phaistos Disc", (0x101D0, 0x101FF)),),
    (
        ("Carian", (0x102A0, 0x102DF)),
        ("Lycian", (0x10280, 0x1029F)),
        ("Lydian", (0x10920, 0x1093F)),
    ),
    (("Domino Tiles", (0x1F030, 0x1F09F)), ("Mahjong Tiles", (0x1F000, 0x1F02F))),
)


_unicodeStarts = []
_unicodeValues = [None]


def _getUnicodeRanges():
    # build the ranges of codepoints for each unicode range bit, and cache result
    if not _unicodeStarts:
        unicodeRanges = [
            (start, (stop, bit))
            for bit, blocks in enumerate(OS2_UNICODE_RANGES)
            for _, (start, stop) in blocks
        ]
        for start, (stop, bit) in sorted(unicodeRanges):
            _unicodeStarts.append(start)
            _unicodeValues.append((stop, bit))
    return _unicodeStarts, _unicodeValues


def intersectUnicodeRanges(unicodes, inverse=False):
    """Intersect a sequence of (int) Unicode codepoints with the Unicode block
    ranges defined in the OpenType specification v1.7, and return the set of
    'ulUnicodeRanges' bits for which there is at least ONE intersection.
    If 'inverse' is True, return the the bits for which there is NO intersection.

    >>> intersectUnicodeRanges([0x0410]) == {9}
    True
    >>> intersectUnicodeRanges([0x0410, 0x1F000]) == {9, 57, 122}
    True
    >>> intersectUnicodeRanges([0x0410, 0x1F000], inverse=True) == (
    ...     set(range(len(OS2_UNICODE_RANGES))) - {9, 57, 122})
    True
    """
    unicodes = set(unicodes)
    unicodestarts, unicodevalues = _getUnicodeRanges()
    bits = set()
    for code in unicodes:
        stop, bit = unicodevalues[bisect.bisect(unicodestarts, code)]
        if code <= stop:
            bits.add(bit)
    # The spec says that bit 57 ("Non Plane 0") implies that there's
    # at least one codepoint beyond the BMP; so I also include all
    # the non-BMP codepoints here
    if any(0x10000 <= code < 0x110000 for code in unicodes):
        bits.add(57)
    return set(range(len(OS2_UNICODE_RANGES))) - bits if inverse else bits


def calcCodePageRanges(unicodes):
    """Given a set of Unicode codepoints (integers), calculate the
    corresponding OS/2 CodePage range bits.
    This is a direct translation of FontForge implementation:
    https://github.com/fontforge/fontforge/blob/7b2c074/fontforge/tottf.c#L3158
    """
    bits = set()
    hasAscii = set(range(0x20, 0x7E)).issubset(unicodes)
    hasLineart = ord("┤") in unicodes

    for uni in unicodes:
        if uni == ord("Þ") and hasAscii:
            bits.add(0)  # Latin 1
        elif uni == ord("Ľ") and hasAscii:
            bits.add(1)  # Latin 2: Eastern Europe
            if hasLineart:
                bits.add(58)  # Latin 2
        elif uni == ord("Б"):
            bits.add(2)  # Cyrillic
            if ord("Ѕ") in unicodes and hasLineart:
                bits.add(57)  # IBM Cyrillic
            if ord("╜") in unicodes and hasLineart:
                bits.add(49)  # MS-DOS Russian
        elif uni == ord("Ά"):
            bits.add(3)  # Greek
            if hasLineart and ord("½") in unicodes:
                bits.add(48)  # IBM Greek
            if hasLineart and ord("√") in unicodes:
                bits.add(60)  # Greek, former 437 G
        elif uni == ord("İ") and hasAscii:
            bits.add(4)  # Turkish
            if hasLineart:
                bits.add(56)  # IBM turkish
        elif uni == ord("א"):
            bits.add(5)  # Hebrew
            if hasLineart and ord("√") in unicodes:
                bits.add(53)  # Hebrew
        elif uni == ord("ر"):
            bits.add(6)  # Arabic
            if ord("√") in unicodes:
                bits.add(51)  # Arabic
            if hasLineart:
                bits.add(61)  # Arabic; ASMO 708
        elif uni == ord("ŗ") and hasAscii:
            bits.add(7)  # Windows Baltic
            if hasLineart:
                bits.add(59)  # MS-DOS Baltic
        elif uni == ord("₫") and hasAscii:
            bits.add(8)  # Vietnamese
        elif uni == ord("ๅ"):
            bits.add(16)  # Thai
        elif uni == ord("エ"):
            bits.add(17)  # JIS/Japan
        elif uni == ord("ㄅ"):
            bits.add(18)  # Chinese: Simplified
        elif uni == ord("ㄱ"):
            bits.add(19)  # Korean wansung
        elif uni == ord("央"):
            bits.add(20)  # Chinese: Traditional
        elif uni == ord("곴"):
            bits.add(21)  # Korean Johab
        elif uni == ord("♥") and hasAscii:
            bits.add(30)  # OEM Character Set
        # TODO: Symbol bit has a special meaning (check the spec), we need
        # to confirm if this is wanted by default.
        # elif chr(0xF000) <= char <= chr(0xF0FF):
        #    codepageRanges.add(31)          # Symbol Character Set
        elif uni == ord("þ") and hasAscii and hasLineart:
            bits.add(54)  # MS-DOS Icelandic
        elif uni == ord("╚") and hasAscii:
            bits.add(62)  # WE/Latin 1
            bits.add(63)  # US
        elif hasAscii and hasLineart and ord("√") in unicodes:
            if uni == ord("Å"):
                bits.add(50)  # MS-DOS Nordic
            elif uni == ord("é"):
                bits.add(52)  # MS-DOS Canadian French
            elif uni == ord("õ"):
                bits.add(55)  # MS-DOS Portuguese

    if hasAscii and ord("‰") in unicodes and ord("∑") in unicodes:
        bits.add(29)  # Macintosh Character Set (US Roman)

    return bits


if __name__ == "__main__":
    import doctest, sys

    sys.exit(doctest.testmod().failed)

# === NexusCore/openenv\Lib\site-packages\IPython\extensions\autoreload.py ===
"""IPython extension to reload modules before executing user code.

``autoreload`` reloads modules automatically before entering the execution of
code typed at the IPython prompt.

This makes for example the following workflow possible:

.. sourcecode:: ipython

   In [1]: %load_ext autoreload

   In [2]: %autoreload 2

   In [3]: from foo import some_function

   In [4]: some_function()
   Out[4]: 42

   In [5]: # open foo.py in an editor and change some_function to return 43

   In [6]: some_function()
   Out[6]: 43

The module was reloaded without reloading it explicitly, and the object
imported with ``from foo import ...`` was also updated.

Usage
=====

The following magic commands are provided:

``%autoreload``, ``%autoreload now``

    Reload all modules (except those excluded by ``%aimport``)
    automatically now.

``%autoreload 0``, ``%autoreload off``

    Disable automatic reloading.

``%autoreload 1``, ``%autoreload explicit``

    Reload all modules imported with ``%aimport`` every time before
    executing the Python code typed.

``%autoreload 2``, ``%autoreload all``

    Reload all modules (except those excluded by ``%aimport``) every
    time before executing the Python code typed.

``%autoreload 3``, ``%autoreload complete``

    Same as 2/all, but also adds any new objects in the module. See
    unit test at IPython/extensions/tests/test_autoreload.py::test_autoload_newly_added_objects

  Adding ``--print`` or ``-p`` to the ``%autoreload`` line will print autoreload activity to
  standard out. ``--log`` or ``-l`` will do it to the log at INFO level; both can be used
  simultaneously.

``%aimport``

    List modules which are to be automatically imported or not to be imported.

``%aimport foo``

    Import module 'foo' and mark it to be autoreloaded for ``%autoreload 1``

``%aimport foo, bar``

    Import modules 'foo', 'bar' and mark them to be autoreloaded for ``%autoreload 1``

``%aimport -foo``

    Mark module 'foo' to not be autoreloaded.

Caveats
=======

Reloading Python modules in a reliable way is in general difficult,
and unexpected things may occur. ``%autoreload`` tries to work around
common pitfalls by replacing function code objects and parts of
classes previously in the module with new versions. This makes the
following things to work:

- Functions and classes imported via 'from xxx import foo' are upgraded
  to new versions when 'xxx' is reloaded.

- Methods and properties of classes are upgraded on reload, so that
  calling 'c.foo()' on an object 'c' created before the reload causes
  the new code for 'foo' to be executed.

Some of the known remaining caveats are:

- Replacing code objects does not always succeed: changing a @property
  in a class to an ordinary method or a method to a member variable
  can cause problems (but in old objects only).

- Functions that are removed (eg. via monkey-patching) from a module
  before it is reloaded are not upgraded.

- C extension modules cannot be reloaded, and so cannot be autoreloaded.

- While comparing Enum and Flag, the 'is' Identity Operator is used (even in the case '==' has been used (Similar to the 'None' keyword)).

- Reloading a module, or importing the same module by a different name, creates new Enums. These may look the same, but are not.
"""

from IPython.core import magic_arguments
from IPython.core.magic import Magics, magics_class, line_magic
from IPython.extensions.deduperreload.deduperreload import DeduperReloader

__skip_doctest__ = True

# -----------------------------------------------------------------------------
#  Copyright (C) 2000 Thomas Heller
#  Copyright (C) 2008 Pauli Virtanen <pav@iki.fi>
#  Copyright (C) 2012  The IPython Development Team
#
#  Distributed under the terms of the BSD License.  The full license is in
#  the file COPYING, distributed as part of this software.
# -----------------------------------------------------------------------------
#
# This IPython module is written by Pauli Virtanen, based on the autoreload
# code by Thomas Heller.

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------

import os
import sys
import traceback
import types
import weakref
import gc
import logging
from importlib import import_module, reload
from importlib.util import source_from_cache

# ------------------------------------------------------------------------------
# Autoreload functionality
# ------------------------------------------------------------------------------


class ModuleReloader:
    enabled = False
    """Whether this reloader is enabled"""

    check_all = True
    """Autoreload all modules, not just those listed in 'modules'"""

    autoload_obj = False
    """Autoreload all modules AND autoload all new objects"""

    def __init__(self, shell=None):
        # Modules that failed to reload: {module: mtime-on-failed-reload, ...}
        self.failed = {}
        # Modules specially marked as autoreloadable.
        self.modules = {}
        # Modules specially marked as not autoreloadable.
        self.skip_modules = {}
        # (module-name, name) -> weakref, for replacing old code objects
        self.old_objects = {}
        # Module modification timestamps
        self.modules_mtimes = {}
        self.shell = shell

        # Reporting callable for verbosity
        self._report = lambda msg: None  # by default, be quiet.

        # Deduper reloader
        self.deduper_reloader = DeduperReloader()

        # Cache module modification times
        self.check(check_all=True, do_reload=False)

        # To hide autoreload errors
        self.hide_errors = False

    def mark_module_skipped(self, module_name):
        """Skip reloading the named module in the future"""
        try:
            del self.modules[module_name]
        except KeyError:
            pass
        self.skip_modules[module_name] = True

    def mark_module_reloadable(self, module_name):
        """Reload the named module in the future (if it is imported)"""
        try:
            del self.skip_modules[module_name]
        except KeyError:
            pass
        self.modules[module_name] = True

    def aimport_module(self, module_name):
        """Import a module, and mark it reloadable

        Returns
        -------
        top_module : module
            The imported module if it is top-level, or the top-level
        top_name : module
            Name of top_module

        """
        self.mark_module_reloadable(module_name)

        import_module(module_name)
        top_name = module_name.split(".")[0]
        top_module = sys.modules[top_name]
        return top_module, top_name

    def filename_and_mtime(self, module):
        if not hasattr(module, "__file__") or module.__file__ is None:
            return None, None

        if getattr(module, "__name__", None) in [None, "__mp_main__", "__main__"]:
            # we cannot reload(__main__) or reload(__mp_main__)
            return None, None

        filename = module.__file__
        path, ext = os.path.splitext(filename)

        if ext.lower() == ".py":
            py_filename = filename
        else:
            try:
                py_filename = source_from_cache(filename)
            except ValueError:
                return None, None

        try:
            pymtime = os.stat(py_filename).st_mtime
        except OSError:
            return None, None

        return py_filename, pymtime

    def check(self, check_all=False, do_reload=True):
        """Check whether some modules need to be reloaded."""

        if not self.enabled and not check_all:
            return

        if check_all or self.check_all:
            modules = list(sys.modules.keys())
        else:
            modules = list(self.modules.keys())

        for modname in modules:
            m = sys.modules.get(modname, None)

            if modname in self.skip_modules:
                continue

            py_filename, pymtime = self.filename_and_mtime(m)
            if py_filename is None:
                continue

            try:
                if pymtime <= self.modules_mtimes[modname]:
                    continue
            except KeyError:
                self.modules_mtimes[modname] = pymtime
                continue
            else:
                if self.failed.get(py_filename, None) == pymtime:
                    continue

            self.modules_mtimes[modname] = pymtime

            # If we've reached this point, we should try to reload the module
            if do_reload:
                self._report(f"Reloading '{modname}'.")
                try:
                    if self.autoload_obj:
                        superreload(m, reload, self.old_objects, self.shell)
                    # if not using autoload, check if deduperreload is viable for this module
                    elif self.deduper_reloader.maybe_reload_module(m):
                        pass
                    else:
                        superreload(m, reload, self.old_objects)
                    if py_filename in self.failed:
                        del self.failed[py_filename]
                except:
                    if not self.hide_errors:
                        print(
                            "[autoreload of {} failed: {}]".format(
                                modname, traceback.format_exc(10)
                            ),
                            file=sys.stderr,
                        )
                    self.failed[py_filename] = pymtime
        self.deduper_reloader.update_sources()


# ------------------------------------------------------------------------------
# superreload
# ------------------------------------------------------------------------------


func_attrs = [
    "__code__",
    "__defaults__",
    "__doc__",
    "__closure__",
    "__globals__",
    "__dict__",
]


def update_function(old, new):
    """Upgrade the code object of a function"""
    for name in func_attrs:
        try:
            setattr(old, name, getattr(new, name))
        except (AttributeError, TypeError):
            pass


def update_instances(old, new):
    """Use garbage collector to find all instances that refer to the old
    class definition and update their __class__ to point to the new class
    definition"""

    refs = gc.get_referrers(old)

    for ref in refs:
        if type(ref) is old:
            object.__setattr__(ref, "__class__", new)


def update_class(old, new):
    """Replace stuff in the __dict__ of a class, and upgrade
    method code objects, and add new methods, if any"""
    for key in list(old.__dict__.keys()):
        old_obj = getattr(old, key)
        try:
            new_obj = getattr(new, key)
            # explicitly checking that comparison returns True to handle
            # cases where `==` doesn't return a boolean.
            if (old_obj == new_obj) is True:
                continue
        except AttributeError:
            # obsolete attribute: remove it
            try:
                delattr(old, key)
            except (AttributeError, TypeError):
                pass
            continue
        except ValueError:
            # can't compare nested structures containing
            # numpy arrays using `==`
            pass

        if update_generic(old_obj, new_obj):
            continue

        try:
            setattr(old, key, getattr(new, key))
        except (AttributeError, TypeError):
            pass  # skip non-writable attributes

    for key in list(new.__dict__.keys()):
        if key not in list(old.__dict__.keys()):
            try:
                setattr(old, key, getattr(new, key))
            except (AttributeError, TypeError):
                pass  # skip non-writable attributes

    # update all instances of class
    update_instances(old, new)


def update_property(old, new):
    """Replace get/set/del functions of a property"""
    update_generic(old.fdel, new.fdel)
    update_generic(old.fget, new.fget)
    update_generic(old.fset, new.fset)


def isinstance2(a, b, typ):
    return isinstance(a, typ) and isinstance(b, typ)


UPDATE_RULES = [
    (lambda a, b: isinstance2(a, b, type), update_class),
    (lambda a, b: isinstance2(a, b, types.FunctionType), update_function),
    (lambda a, b: isinstance2(a, b, property), update_property),
]
UPDATE_RULES.extend(
    [
        (
            lambda a, b: isinstance2(a, b, types.MethodType),
            lambda a, b: update_function(a.__func__, b.__func__),
        ),
    ]
)


def update_generic(a, b):
    for type_check, update in UPDATE_RULES:
        if type_check(a, b):
            update(a, b)
            return True
    return False


class StrongRef:
    def __init__(self, obj):
        self.obj = obj

    def __call__(self):
        return self.obj


mod_attrs = [
    "__name__",
    "__doc__",
    "__package__",
    "__loader__",
    "__spec__",
    "__file__",
    "__cached__",
    "__builtins__",
]


def append_obj(module, d, name, obj, autoload=False):
    in_module = hasattr(obj, "__module__") and obj.__module__ == module.__name__
    if autoload:
        # check needed for module global built-ins
        if not in_module and name in mod_attrs:
            return False
    else:
        if not in_module:
            return False

    key = (module.__name__, name)
    try:
        d.setdefault(key, []).append(weakref.ref(obj))
    except TypeError:
        pass
    return True


def superreload(module, reload=reload, old_objects=None, shell=None):
    """Enhanced version of the builtin reload function.

    superreload remembers objects previously in the module, and

    - upgrades the class dictionary of every old class in the module
    - upgrades the code object of every old function and method
    - clears the module's namespace before reloading

    """
    if old_objects is None:
        old_objects = {}

    # collect old objects in the module
    for name, obj in list(module.__dict__.items()):
        if not append_obj(module, old_objects, name, obj):
            continue
        key = (module.__name__, name)
        try:
            old_objects.setdefault(key, []).append(weakref.ref(obj))
        except TypeError:
            pass

    # reload module
    try:
        # clear namespace first from old cruft
        old_dict = module.__dict__.copy()
        old_name = module.__name__
        module.__dict__.clear()
        module.__dict__["__name__"] = old_name
        module.__dict__["__loader__"] = old_dict["__loader__"]
    except (TypeError, AttributeError, KeyError):
        pass

    try:
        module = reload(module)
    except:
        # restore module dictionary on failed reload
        module.__dict__.update(old_dict)
        raise

    # iterate over all objects and update functions & classes
    for name, new_obj in list(module.__dict__.items()):
        key = (module.__name__, name)
        if key not in old_objects:
            # here 'shell' acts both as a flag and as an output var
            if (
                shell is None
                or name == "Enum"
                or not append_obj(module, old_objects, name, new_obj, True)
            ):
                continue
            shell.user_ns[name] = new_obj

        new_refs = []
        for old_ref in old_objects[key]:
            old_obj = old_ref()
            if old_obj is None:
                continue
            new_refs.append(old_ref)
            update_generic(old_obj, new_obj)

        if new_refs:
            old_objects[key] = new_refs
        else:
            del old_objects[key]

    return module


# ------------------------------------------------------------------------------
# IPython connectivity
# ------------------------------------------------------------------------------


@magics_class
class AutoreloadMagics(Magics):
    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        self._reloader = ModuleReloader(self.shell)
        self._reloader.check_all = False
        self._reloader.autoload_obj = False
        self.loaded_modules = set(sys.modules)

    @line_magic
    @magic_arguments.magic_arguments()
    @magic_arguments.argument(
        "mode",
        type=str,
        default="now",
        nargs="?",
        help="""blank or 'now' - Reload all modules (except those excluded by %%aimport)
             automatically now.

             '0' or 'off' - Disable automatic reloading.

             '1' or 'explicit' - Reload only modules imported with %%aimport every
             time before executing the Python code typed.

             '2' or 'all' - Reload all modules (except those excluded by %%aimport)
             every time before executing the Python code typed.

             '3' or 'complete' - Same as 2/all, but also adds any new
             objects in the module.
             
             By default, a newer autoreload algorithm that diffs the module's source code
             with the previous version and only reloads changed parts is applied for modes
             2 and below. To use the original algorithm, add the `-` suffix to the mode,
             e.g. '%autoreload 2-', or pass in --full.
             """,
    )
    @magic_arguments.argument(
        "-p",
        "--print",
        action="store_true",
        default=False,
        help="Show autoreload activity using `print` statements",
    )
    @magic_arguments.argument(
        "-l",
        "--log",
        action="store_true",
        default=False,
        help="Show autoreload activity using the logger",
    )
    @magic_arguments.argument(
        "--hide-errors",
        action="store_true",
        default=False,
        help="Hide autoreload errors",
    )
    @magic_arguments.argument(
        "--full",
        action="store_true",
        default=False,
        help="Don't ever use new diffing algorithm",
    )
    def autoreload(self, line=""):
        r"""%autoreload => Reload modules automatically

        %autoreload or %autoreload now
        Reload all modules (except those excluded by %aimport) automatically
        now.

        %autoreload 0 or %autoreload off
        Disable automatic reloading.

        %autoreload 1 or %autoreload explicit
        Reload only modules imported with %aimport every time before executing
        the Python code typed.

        %autoreload 2 or %autoreload all
        Reload all modules (except those excluded by %aimport) every time
        before executing the Python code typed.

        %autoreload 3 or %autoreload complete
        Same as 2/all, but also but also adds any new objects in the module. See
        unit test at IPython/extensions/tests/test_autoreload.py::test_autoload_newly_added_objects

        The optional arguments --print and --log control display of autoreload activity. The default
        is to act silently; --print (or -p) will print out the names of modules that are being
        reloaded, and --log (or -l) outputs them to the log at INFO level.

        The optional argument --hide-errors hides any errors that can happen when trying to
        reload code.

        Reloading Python modules in a reliable way is in general
        difficult, and unexpected things may occur. %autoreload tries to
        work around common pitfalls by replacing function code objects and
        parts of classes previously in the module with new versions. This
        makes the following things to work:

        - Functions and classes imported via 'from xxx import foo' are upgraded
          to new versions when 'xxx' is reloaded.

        - Methods and properties of classes are upgraded on reload, so that
          calling 'c.foo()' on an object 'c' created before the reload causes
          the new code for 'foo' to be executed.

        Some of the known remaining caveats are:

        - Replacing code objects does not always succeed: changing a @property
          in a class to an ordinary method or a method to a member variable
          can cause problems (but in old objects only).

        - Functions that are removed (eg. via monkey-patching) from a module
          before it is reloaded are not upgraded.

        - C extension modules cannot be reloaded, and so cannot be
          autoreloaded.

        """
        args = magic_arguments.parse_argstring(self.autoreload, line)
        mode = args.mode.lower()

        enable_deduperreload = not args.full
        if mode.endswith("-"):
            enable_deduperreload = False
            mode = mode[:-1]
        self._reloader.deduper_reloader.enabled = enable_deduperreload

        p = print

        logger = logging.getLogger("autoreload")

        l = logger.info

        def pl(msg):
            p(msg)
            l(msg)

        if args.print is False and args.log is False:
            self._reloader._report = lambda msg: None
        elif args.print is True:
            if args.log is True:
                self._reloader._report = pl
            else:
                self._reloader._report = p
        elif args.log is True:
            self._reloader._report = l

        self._reloader.hide_errors = args.hide_errors

        if mode == "" or mode == "now":
            self._reloader.check(True)
        elif mode == "0" or mode == "off":
            self._reloader.enabled = False
        elif mode == "1" or mode == "explicit":
            self._reloader.enabled = True
            self._reloader.check_all = False
            self._reloader.autoload_obj = False
        elif mode == "2" or mode == "all":
            self._reloader.enabled = True
            self._reloader.check_all = True
            self._reloader.autoload_obj = False
        elif mode == "3" or mode == "complete":
            self._reloader.enabled = True
            self._reloader.check_all = True
            self._reloader.autoload_obj = True
        else:
            raise ValueError(f'Unrecognized autoreload mode "{mode}".')

    @line_magic
    def aimport(self, parameter_s="", stream=None):
        """%aimport => Import modules for automatic reloading.

        %aimport
        List modules to automatically import and not to import.

        %aimport foo
        Import module 'foo' and mark it to be autoreloaded for %autoreload explicit

        %aimport foo, bar
        Import modules 'foo', 'bar' and mark them to be autoreloaded for %autoreload explicit

        %aimport -foo, bar
        Mark module 'foo' to not be autoreloaded for %autoreload explicit, all, or complete, and 'bar'
        to be autoreloaded for mode explicit.
        """
        modname = parameter_s
        if not modname:
            to_reload = sorted(self._reloader.modules.keys())
            to_skip = sorted(self._reloader.skip_modules.keys())
            if stream is None:
                stream = sys.stdout
            if self._reloader.check_all:
                stream.write("Modules to reload:\nall-except-skipped\n")
            else:
                stream.write("Modules to reload:\n%s\n" % " ".join(to_reload))
            stream.write("\nModules to skip:\n%s\n" % " ".join(to_skip))
        else:
            for _module in [_.strip() for _ in modname.split(",")]:
                if _module.startswith("-"):
                    _module = _module[1:].strip()
                    self._reloader.mark_module_skipped(_module)
                else:
                    top_module, top_name = self._reloader.aimport_module(_module)

                    # Inject module to user namespace
                    self.shell.push({top_name: top_module})

    def pre_run_cell(self, info):
        if self._reloader.enabled:
            try:
                self._reloader.check()
            except:
                pass

    def post_execute_hook(self):
        """Cache the modification times of any modules imported in this execution"""
        newly_loaded_modules = set(sys.modules) - self.loaded_modules
        for modname in newly_loaded_modules:
            _, pymtime = self._reloader.filename_and_mtime(sys.modules[modname])
            if pymtime is not None:
                self._reloader.modules_mtimes[modname] = pymtime

        self.loaded_modules.update(newly_loaded_modules)


def load_ipython_extension(ip):
    """Load the extension in IPython."""
    auto_reload = AutoreloadMagics(ip)
    ip.register_magics(auto_reload)
    ip.events.register("pre_run_cell", auto_reload.pre_run_cell)
    ip.events.register("post_execute", auto_reload.post_execute_hook)

# === NexusCore/openenv\Lib\site-packages\pip\_vendor\rich\segment.py ===
from enum import IntEnum
from functools import lru_cache
from itertools import filterfalse
from logging import getLogger
from operator import attrgetter
from typing import (
    TYPE_CHECKING,
    Dict,
    Iterable,
    List,
    NamedTuple,
    Optional,
    Sequence,
    Tuple,
    Type,
    Union,
)

from .cells import (
    _is_single_cell_widths,
    cached_cell_len,
    cell_len,
    get_character_cell_size,
    set_cell_size,
)
from .repr import Result, rich_repr
from .style import Style

if TYPE_CHECKING:
    from .console import Console, ConsoleOptions, RenderResult

log = getLogger("rich")


class ControlType(IntEnum):
    """Non-printable control codes which typically translate to ANSI codes."""

    BELL = 1
    CARRIAGE_RETURN = 2
    HOME = 3
    CLEAR = 4
    SHOW_CURSOR = 5
    HIDE_CURSOR = 6
    ENABLE_ALT_SCREEN = 7
    DISABLE_ALT_SCREEN = 8
    CURSOR_UP = 9
    CURSOR_DOWN = 10
    CURSOR_FORWARD = 11
    CURSOR_BACKWARD = 12
    CURSOR_MOVE_TO_COLUMN = 13
    CURSOR_MOVE_TO = 14
    ERASE_IN_LINE = 15
    SET_WINDOW_TITLE = 16


ControlCode = Union[
    Tuple[ControlType],
    Tuple[ControlType, Union[int, str]],
    Tuple[ControlType, int, int],
]


@rich_repr()
class Segment(NamedTuple):
    """A piece of text with associated style. Segments are produced by the Console render process and
    are ultimately converted in to strings to be written to the terminal.

    Args:
        text (str): A piece of text.
        style (:class:`~rich.style.Style`, optional): An optional style to apply to the text.
        control (Tuple[ControlCode], optional): Optional sequence of control codes.

    Attributes:
        cell_length (int): The cell length of this Segment.
    """

    text: str
    style: Optional[Style] = None
    control: Optional[Sequence[ControlCode]] = None

    @property
    def cell_length(self) -> int:
        """The number of terminal cells required to display self.text.

        Returns:
            int: A number of cells.
        """
        text, _style, control = self
        return 0 if control else cell_len(text)

    def __rich_repr__(self) -> Result:
        yield self.text
        if self.control is None:
            if self.style is not None:
                yield self.style
        else:
            yield self.style
            yield self.control

    def __bool__(self) -> bool:
        """Check if the segment contains text."""
        return bool(self.text)

    @property
    def is_control(self) -> bool:
        """Check if the segment contains control codes."""
        return self.control is not None

    @classmethod
    @lru_cache(1024 * 16)
    def _split_cells(cls, segment: "Segment", cut: int) -> Tuple["Segment", "Segment"]:
        """Split a segment in to two at a given cell position.

        Note that splitting a double-width character, may result in that character turning
        into two spaces.

        Args:
            segment (Segment): A segment to split.
            cut (int): A cell position to cut on.

        Returns:
            A tuple of two segments.
        """
        text, style, control = segment
        _Segment = Segment
        cell_length = segment.cell_length
        if cut >= cell_length:
            return segment, _Segment("", style, control)

        cell_size = get_character_cell_size

        pos = int((cut / cell_length) * len(text))

        while True:
            before = text[:pos]
            cell_pos = cell_len(before)
            out_by = cell_pos - cut
            if not out_by:
                return (
                    _Segment(before, style, control),
                    _Segment(text[pos:], style, control),
                )
            if out_by == -1 and cell_size(text[pos]) == 2:
                return (
                    _Segment(text[:pos] + " ", style, control),
                    _Segment(" " + text[pos + 1 :], style, control),
                )
            if out_by == +1 and cell_size(text[pos - 1]) == 2:
                return (
                    _Segment(text[: pos - 1] + " ", style, control),
                    _Segment(" " + text[pos:], style, control),
                )
            if cell_pos < cut:
                pos += 1
            else:
                pos -= 1

    def split_cells(self, cut: int) -> Tuple["Segment", "Segment"]:
        """Split segment in to two segments at the specified column.

        If the cut point falls in the middle of a 2-cell wide character then it is replaced
        by two spaces, to preserve the display width of the parent segment.

        Args:
            cut (int): Offset within the segment to cut.

        Returns:
            Tuple[Segment, Segment]: Two segments.
        """
        text, style, control = self
        assert cut >= 0

        if _is_single_cell_widths(text):
            # Fast path with all 1 cell characters
            if cut >= len(text):
                return self, Segment("", style, control)
            return (
                Segment(text[:cut], style, control),
                Segment(text[cut:], style, control),
            )

        return self._split_cells(self, cut)

    @classmethod
    def line(cls) -> "Segment":
        """Make a new line segment."""
        return cls("\n")

    @classmethod
    def apply_style(
        cls,
        segments: Iterable["Segment"],
        style: Optional[Style] = None,
        post_style: Optional[Style] = None,
    ) -> Iterable["Segment"]:
        """Apply style(s) to an iterable of segments.

        Returns an iterable of segments where the style is replaced by ``style + segment.style + post_style``.

        Args:
            segments (Iterable[Segment]): Segments to process.
            style (Style, optional): Base style. Defaults to None.
            post_style (Style, optional): Style to apply on top of segment style. Defaults to None.

        Returns:
            Iterable[Segments]: A new iterable of segments (possibly the same iterable).
        """
        result_segments = segments
        if style:
            apply = style.__add__
            result_segments = (
                cls(text, None if control else apply(_style), control)
                for text, _style, control in result_segments
            )
        if post_style:
            result_segments = (
                cls(
                    text,
                    (
                        None
                        if control
                        else (_style + post_style if _style else post_style)
                    ),
                    control,
                )
                for text, _style, control in result_segments
            )
        return result_segments

    @classmethod
    def filter_control(
        cls, segments: Iterable["Segment"], is_control: bool = False
    ) -> Iterable["Segment"]:
        """Filter segments by ``is_control`` attribute.

        Args:
            segments (Iterable[Segment]): An iterable of Segment instances.
            is_control (bool, optional): is_control flag to match in search.

        Returns:
            Iterable[Segment]: And iterable of Segment instances.

        """
        if is_control:
            return filter(attrgetter("control"), segments)
        else:
            return filterfalse(attrgetter("control"), segments)

    @classmethod
    def split_lines(cls, segments: Iterable["Segment"]) -> Iterable[List["Segment"]]:
        """Split a sequence of segments in to a list of lines.

        Args:
            segments (Iterable[Segment]): Segments potentially containing line feeds.

        Yields:
            Iterable[List[Segment]]: Iterable of segment lists, one per line.
        """
        line: List[Segment] = []
        append = line.append

        for segment in segments:
            if "\n" in segment.text and not segment.control:
                text, style, _ = segment
                while text:
                    _text, new_line, text = text.partition("\n")
                    if _text:
                        append(cls(_text, style))
                    if new_line:
                        yield line
                        line = []
                        append = line.append
            else:
                append(segment)
        if line:
            yield line

    @classmethod
    def split_and_crop_lines(
        cls,
        segments: Iterable["Segment"],
        length: int,
        style: Optional[Style] = None,
        pad: bool = True,
        include_new_lines: bool = True,
    ) -> Iterable[List["Segment"]]:
        """Split segments in to lines, and crop lines greater than a given length.

        Args:
            segments (Iterable[Segment]): An iterable of segments, probably
                generated from console.render.
            length (int): Desired line length.
            style (Style, optional): Style to use for any padding.
            pad (bool): Enable padding of lines that are less than `length`.

        Returns:
            Iterable[List[Segment]]: An iterable of lines of segments.
        """
        line: List[Segment] = []
        append = line.append

        adjust_line_length = cls.adjust_line_length
        new_line_segment = cls("\n")

        for segment in segments:
            if "\n" in segment.text and not segment.control:
                text, segment_style, _ = segment
                while text:
                    _text, new_line, text = text.partition("\n")
                    if _text:
                        append(cls(_text, segment_style))
                    if new_line:
                        cropped_line = adjust_line_length(
                            line, length, style=style, pad=pad
                        )
                        if include_new_lines:
                            cropped_line.append(new_line_segment)
                        yield cropped_line
                        line.clear()
            else:
                append(segment)
        if line:
            yield adjust_line_length(line, length, style=style, pad=pad)

    @classmethod
    def adjust_line_length(
        cls,
        line: List["Segment"],
        length: int,
        style: Optional[Style] = None,
        pad: bool = True,
    ) -> List["Segment"]:
        """Adjust a line to a given width (cropping or padding as required).

        Args:
            segments (Iterable[Segment]): A list of segments in a single line.
            length (int): The desired width of the line.
            style (Style, optional): The style of padding if used (space on the end). Defaults to None.
            pad (bool, optional): Pad lines with spaces if they are shorter than `length`. Defaults to True.

        Returns:
            List[Segment]: A line of segments with the desired length.
        """
        line_length = sum(segment.cell_length for segment in line)
        new_line: List[Segment]

        if line_length < length:
            if pad:
                new_line = line + [cls(" " * (length - line_length), style)]
            else:
                new_line = line[:]
        elif line_length > length:
            new_line = []
            append = new_line.append
            line_length = 0
            for segment in line:
                segment_length = segment.cell_length
                if line_length + segment_length < length or segment.control:
                    append(segment)
                    line_length += segment_length
                else:
                    text, segment_style, _ = segment
                    text = set_cell_size(text, length - line_length)
                    append(cls(text, segment_style))
                    break
        else:
            new_line = line[:]
        return new_line

    @classmethod
    def get_line_length(cls, line: List["Segment"]) -> int:
        """Get the length of list of segments.

        Args:
            line (List[Segment]): A line encoded as a list of Segments (assumes no '\\\\n' characters),

        Returns:
            int: The length of the line.
        """
        _cell_len = cell_len
        return sum(_cell_len(text) for text, style, control in line if not control)

    @classmethod
    def get_shape(cls, lines: List[List["Segment"]]) -> Tuple[int, int]:
        """Get the shape (enclosing rectangle) of a list of lines.

        Args:
            lines (List[List[Segment]]): A list of lines (no '\\\\n' characters).

        Returns:
            Tuple[int, int]: Width and height in characters.
        """
        get_line_length = cls.get_line_length
        max_width = max(get_line_length(line) for line in lines) if lines else 0
        return (max_width, len(lines))

    @classmethod
    def set_shape(
        cls,
        lines: List[List["Segment"]],
        width: int,
        height: Optional[int] = None,
        style: Optional[Style] = None,
        new_lines: bool = False,
    ) -> List[List["Segment"]]:
        """Set the shape of a list of lines (enclosing rectangle).

        Args:
            lines (List[List[Segment]]): A list of lines.
            width (int): Desired width.
            height (int, optional): Desired height or None for no change.
            style (Style, optional): Style of any padding added.
            new_lines (bool, optional): Padded lines should include "\n". Defaults to False.

        Returns:
            List[List[Segment]]: New list of lines.
        """
        _height = height or len(lines)

        blank = (
            [cls(" " * width + "\n", style)] if new_lines else [cls(" " * width, style)]
        )

        adjust_line_length = cls.adjust_line_length
        shaped_lines = lines[:_height]
        shaped_lines[:] = [
            adjust_line_length(line, width, style=style) for line in lines
        ]
        if len(shaped_lines) < _height:
            shaped_lines.extend([blank] * (_height - len(shaped_lines)))
        return shaped_lines

    @classmethod
    def align_top(
        cls: Type["Segment"],
        lines: List[List["Segment"]],
        width: int,
        height: int,
        style: Style,
        new_lines: bool = False,
    ) -> List[List["Segment"]]:
        """Aligns lines to top (adds extra lines to bottom as required).

        Args:
            lines (List[List[Segment]]): A list of lines.
            width (int): Desired width.
            height (int, optional): Desired height or None for no change.
            style (Style): Style of any padding added.
            new_lines (bool, optional): Padded lines should include "\n". Defaults to False.

        Returns:
            List[List[Segment]]: New list of lines.
        """
        extra_lines = height - len(lines)
        if not extra_lines:
            return lines[:]
        lines = lines[:height]
        blank = cls(" " * width + "\n", style) if new_lines else cls(" " * width, style)
        lines = lines + [[blank]] * extra_lines
        return lines

    @classmethod
    def align_bottom(
        cls: Type["Segment"],
        lines: List[List["Segment"]],
        width: int,
        height: int,
        style: Style,
        new_lines: bool = False,
    ) -> List[List["Segment"]]:
        """Aligns render to bottom (adds extra lines above as required).

        Args:
            lines (List[List[Segment]]): A list of lines.
            width (int): Desired width.
            height (int, optional): Desired height or None for no change.
            style (Style): Style of any padding added. Defaults to None.
            new_lines (bool, optional): Padded lines should include "\n". Defaults to False.

        Returns:
            List[List[Segment]]: New list of lines.
        """
        extra_lines = height - len(lines)
        if not extra_lines:
            return lines[:]
        lines = lines[:height]
        blank = cls(" " * width + "\n", style) if new_lines else cls(" " * width, style)
        lines = [[blank]] * extra_lines + lines
        return lines

    @classmethod
    def align_middle(
        cls: Type["Segment"],
        lines: List[List["Segment"]],
        width: int,
        height: int,
        style: Style,
        new_lines: bool = False,
    ) -> List[List["Segment"]]:
        """Aligns lines to middle (adds extra lines to above and below as required).

        Args:
            lines (List[List[Segment]]): A list of lines.
            width (int): Desired width.
            height (int, optional): Desired height or None for no change.
            style (Style): Style of any padding added.
            new_lines (bool, optional): Padded lines should include "\n". Defaults to False.

        Returns:
            List[List[Segment]]: New list of lines.
        """
        extra_lines = height - len(lines)
        if not extra_lines:
            return lines[:]
        lines = lines[:height]
        blank = cls(" " * width + "\n", style) if new_lines else cls(" " * width, style)
        top_lines = extra_lines // 2
        bottom_lines = extra_lines - top_lines
        lines = [[blank]] * top_lines + lines + [[blank]] * bottom_lines
        return lines

    @classmethod
    def simplify(cls, segments: Iterable["Segment"]) -> Iterable["Segment"]:
        """Simplify an iterable of segments by combining contiguous segments with the same style.

        Args:
            segments (Iterable[Segment]): An iterable of segments.

        Returns:
            Iterable[Segment]: A possibly smaller iterable of segments that will render the same way.
        """
        iter_segments = iter(segments)
        try:
            last_segment = next(iter_segments)
        except StopIteration:
            return

        _Segment = Segment
        for segment in iter_segments:
            if last_segment.style == segment.style and not segment.control:
                last_segment = _Segment(
                    last_segment.text + segment.text, last_segment.style
                )
            else:
                yield last_segment
                last_segment = segment
        yield last_segment

    @classmethod
    def strip_links(cls, segments: Iterable["Segment"]) -> Iterable["Segment"]:
        """Remove all links from an iterable of styles.

        Args:
            segments (Iterable[Segment]): An iterable segments.

        Yields:
            Segment: Segments with link removed.
        """
        for segment in segments:
            if segment.control or segment.style is None:
                yield segment
            else:
                text, style, _control = segment
                yield cls(text, style.update_link(None) if style else None)

    @classmethod
    def strip_styles(cls, segments: Iterable["Segment"]) -> Iterable["Segment"]:
        """Remove all styles from an iterable of segments.

        Args:
            segments (Iterable[Segment]): An iterable segments.

        Yields:
            Segment: Segments with styles replace with None
        """
        for text, _style, control in segments:
            yield cls(text, None, control)

    @classmethod
    def remove_color(cls, segments: Iterable["Segment"]) -> Iterable["Segment"]:
        """Remove all color from an iterable of segments.

        Args:
            segments (Iterable[Segment]): An iterable segments.

        Yields:
            Segment: Segments with colorless style.
        """

        cache: Dict[Style, Style] = {}
        for text, style, control in segments:
            if style:
                colorless_style = cache.get(style)
                if colorless_style is None:
                    colorless_style = style.without_color
                    cache[style] = colorless_style
                yield cls(text, colorless_style, control)
            else:
                yield cls(text, None, control)

    @classmethod
    def divide(
        cls, segments: Iterable["Segment"], cuts: Iterable[int]
    ) -> Iterable[List["Segment"]]:
        """Divides an iterable of segments in to portions.

        Args:
            cuts (Iterable[int]): Cell positions where to divide.

        Yields:
            [Iterable[List[Segment]]]: An iterable of Segments in List.
        """
        split_segments: List["Segment"] = []
        add_segment = split_segments.append

        iter_cuts = iter(cuts)

        while True:
            cut = next(iter_cuts, -1)
            if cut == -1:
                return
            if cut != 0:
                break
            yield []
        pos = 0

        segments_clear = split_segments.clear
        segments_copy = split_segments.copy

        _cell_len = cached_cell_len
        for segment in segments:
            text, _style, control = segment
            while text:
                end_pos = pos if control else pos + _cell_len(text)
                if end_pos < cut:
                    add_segment(segment)
                    pos = end_pos
                    break

                if end_pos == cut:
                    add_segment(segment)
                    yield segments_copy()
                    segments_clear()
                    pos = end_pos

                    cut = next(iter_cuts, -1)
                    if cut == -1:
                        if split_segments:
                            yield segments_copy()
                        return

                    break

                else:
                    before, segment = segment.split_cells(cut - pos)
                    text, _style, control = segment
                    add_segment(before)
                    yield segments_copy()
                    segments_clear()
                    pos = cut

                cut = next(iter_cuts, -1)
                if cut == -1:
                    if split_segments:
                        yield segments_copy()
                    return

        yield segments_copy()


class Segments:
    """A simple renderable to render an iterable of segments. This class may be useful if
    you want to print segments outside of a __rich_console__ method.

    Args:
        segments (Iterable[Segment]): An iterable of segments.
        new_lines (bool, optional): Add new lines between segments. Defaults to False.
    """

    def __init__(self, segments: Iterable[Segment], new_lines: bool = False) -> None:
        self.segments = list(segments)
        self.new_lines = new_lines

    def __rich_console__(
        self, console: "Console", options: "ConsoleOptions"
    ) -> "RenderResult":
        if self.new_lines:
            line = Segment.line()
            for segment in self.segments:
                yield segment
                yield line
        else:
            yield from self.segments


class SegmentLines:
    def __init__(self, lines: Iterable[List[Segment]], new_lines: bool = False) -> None:
        """A simple renderable containing a number of lines of segments. May be used as an intermediate
        in rendering process.

        Args:
            lines (Iterable[List[Segment]]): Lists of segments forming lines.
            new_lines (bool, optional): Insert new lines after each line. Defaults to False.
        """
        self.lines = list(lines)
        self.new_lines = new_lines

    def __rich_console__(
        self, console: "Console", options: "ConsoleOptions"
    ) -> "RenderResult":
        if self.new_lines:
            new_line = Segment.line()
            for line in self.lines:
                yield from line
                yield new_line
        else:
            for line in self.lines:
                yield from line


if __name__ == "__main__":  # pragma: no cover
    from pip._vendor.rich.console import Console
    from pip._vendor.rich.syntax import Syntax
    from pip._vendor.rich.text import Text

    code = """from rich.console import Console
console = Console()
text = Text.from_markup("Hello, [bold magenta]World[/]!")
console.print(text)"""

    text = Text.from_markup("Hello, [bold magenta]World[/]!")

    console = Console()

    console.rule("rich.Segment")
    console.print(
        "A Segment is the last step in the Rich render process before generating text with ANSI codes."
    )
    console.print("\nConsider the following code:\n")
    console.print(Syntax(code, "python", line_numbers=True))
    console.print()
    console.print(
        "When you call [b]print()[/b], Rich [i]renders[/i] the object in to the following:\n"
    )
    fragments = list(console.render(text))
    console.print(fragments)
    console.print()
    console.print("The Segments are then processed to produce the following output:\n")
    console.print(text)
    console.print(
        "\nYou will only need to know this if you are implementing your own Rich renderables."
    )

# === NexusCore/openenv\Lib\site-packages\pyasn1\type\constraint.py ===
#
# This file is part of pyasn1 software.
#
# Copyright (c) 2005-2020, Ilya Etingof <etingof@gmail.com>
# License: https://pyasn1.readthedocs.io/en/latest/license.html
#
# Original concept and code by Mike C. Fletcher.
#
import sys

from pyasn1.type import error

__all__ = ['SingleValueConstraint', 'ContainedSubtypeConstraint',
           'ValueRangeConstraint', 'ValueSizeConstraint',
           'PermittedAlphabetConstraint', 'InnerTypeConstraint',
           'ConstraintsExclusion', 'ConstraintsIntersection',
           'ConstraintsUnion']


class AbstractConstraint(object):

    def __init__(self, *values):
        self._valueMap = set()
        self._setValues(values)
        self.__hash = hash((self.__class__.__name__, self._values))

    def __call__(self, value, idx=None):
        if not self._values:
            return

        try:
            self._testValue(value, idx)

        except error.ValueConstraintError as exc:
            raise error.ValueConstraintError(
                '%s failed at: %r' % (self, exc)
            )

    def __repr__(self):
        representation = '%s object' % (self.__class__.__name__)

        if self._values:
            representation += ', consts %s' % ', '.join(
                [repr(x) for x in self._values])

        return '<%s>' % representation

    def __eq__(self, other):
        if self is other:
            return True
        return self._values == other

    def __ne__(self, other):
        return self._values != other

    def __lt__(self, other):
        return self._values < other

    def __le__(self, other):
        return self._values <= other

    def __gt__(self, other):
        return self._values > other

    def __ge__(self, other):
        return self._values >= other

    def __bool__(self):
        return bool(self._values)

    def __hash__(self):
        return self.__hash

    def _setValues(self, values):
        self._values = values

    def _testValue(self, value, idx):
        raise error.ValueConstraintError(value)

    # Constraints derivation logic
    def getValueMap(self):
        return self._valueMap

    def isSuperTypeOf(self, otherConstraint):
        # TODO: fix possible comparison of set vs scalars here
        return (otherConstraint is self or
                not self._values or
                otherConstraint == self or
                self in otherConstraint.getValueMap())

    def isSubTypeOf(self, otherConstraint):
        return (otherConstraint is self or
                not self or
                otherConstraint == self or
                otherConstraint in self._valueMap)


class SingleValueConstraint(AbstractConstraint):
    """Create a SingleValueConstraint object.

    The SingleValueConstraint satisfies any value that
    is present in the set of permitted values.

    Objects of this type are iterable (emitting constraint values) and
    can act as operands for some arithmetic operations e.g. addition
    and subtraction. The latter can be used for combining multiple
    SingleValueConstraint objects into one.

    The SingleValueConstraint object can be applied to
    any ASN.1 type.

    Parameters
    ----------
    *values: :class:`int`
        Full set of values permitted by this constraint object.

    Examples
    --------
    .. code-block:: python

        class DivisorOfSix(Integer):
            '''
            ASN.1 specification:

            Divisor-Of-6 ::= INTEGER (1 | 2 | 3 | 6)
            '''
            subtypeSpec = SingleValueConstraint(1, 2, 3, 6)

        # this will succeed
        divisor_of_six = DivisorOfSix(1)

        # this will raise ValueConstraintError
        divisor_of_six = DivisorOfSix(7)
    """
    def _setValues(self, values):
        self._values = values
        self._set = set(values)

    def _testValue(self, value, idx):
        if value not in self._set:
            raise error.ValueConstraintError(value)

    # Constrains can be merged or reduced

    def __contains__(self, item):
        return item in self._set

    def __iter__(self):
        return iter(self._set)

    def __add__(self, constraint):
        return self.__class__(*(self._set.union(constraint)))

    def __sub__(self, constraint):
        return self.__class__(*(self._set.difference(constraint)))


class ContainedSubtypeConstraint(AbstractConstraint):
    """Create a ContainedSubtypeConstraint object.

    The ContainedSubtypeConstraint satisfies any value that
    is present in the set of permitted values and also
    satisfies included constraints.

    The ContainedSubtypeConstraint object can be applied to
    any ASN.1 type.

    Parameters
    ----------
    *values:
        Full set of values and constraint objects permitted
        by this constraint object.

    Examples
    --------
    .. code-block:: python

        class DivisorOfEighteen(Integer):
            '''
            ASN.1 specification:

            Divisors-of-18 ::= INTEGER (INCLUDES Divisors-of-6 | 9 | 18)
            '''
            subtypeSpec = ContainedSubtypeConstraint(
                SingleValueConstraint(1, 2, 3, 6), 9, 18
            )

        # this will succeed
        divisor_of_eighteen = DivisorOfEighteen(9)

        # this will raise ValueConstraintError
        divisor_of_eighteen = DivisorOfEighteen(10)
    """
    def _testValue(self, value, idx):
        for constraint in self._values:
            if isinstance(constraint, AbstractConstraint):
                constraint(value, idx)
            elif value not in self._set:
                raise error.ValueConstraintError(value)


class ValueRangeConstraint(AbstractConstraint):
    """Create a ValueRangeConstraint object.

    The ValueRangeConstraint satisfies any value that
    falls in the range of permitted values.

    The ValueRangeConstraint object can only be applied
    to :class:`~pyasn1.type.univ.Integer` and
    :class:`~pyasn1.type.univ.Real` types.

    Parameters
    ----------
    start: :class:`int`
        Minimum permitted value in the range (inclusive)

    end: :class:`int`
        Maximum permitted value in the range (inclusive)

    Examples
    --------
    .. code-block:: python

        class TeenAgeYears(Integer):
            '''
            ASN.1 specification:

            TeenAgeYears ::= INTEGER (13 .. 19)
            '''
            subtypeSpec = ValueRangeConstraint(13, 19)

        # this will succeed
        teen_year = TeenAgeYears(18)

        # this will raise ValueConstraintError
        teen_year = TeenAgeYears(20)
    """
    def _testValue(self, value, idx):
        if value < self.start or value > self.stop:
            raise error.ValueConstraintError(value)

    def _setValues(self, values):
        if len(values) != 2:
            raise error.PyAsn1Error(
                '%s: bad constraint values' % (self.__class__.__name__,)
            )
        self.start, self.stop = values
        if self.start > self.stop:
            raise error.PyAsn1Error(
                '%s: screwed constraint values (start > stop): %s > %s' % (
                    self.__class__.__name__,
                    self.start, self.stop
                )
            )
        AbstractConstraint._setValues(self, values)


class ValueSizeConstraint(ValueRangeConstraint):
    """Create a ValueSizeConstraint object.

    The ValueSizeConstraint satisfies any value for
    as long as its size falls within the range of
    permitted sizes.

    The ValueSizeConstraint object can be applied
    to :class:`~pyasn1.type.univ.BitString`,
    :class:`~pyasn1.type.univ.OctetString` (including
    all :ref:`character ASN.1 types <type.char>`),
    :class:`~pyasn1.type.univ.SequenceOf`
    and :class:`~pyasn1.type.univ.SetOf` types.

    Parameters
    ----------
    minimum: :class:`int`
        Minimum permitted size of the value (inclusive)

    maximum: :class:`int`
        Maximum permitted size of the value (inclusive)

    Examples
    --------
    .. code-block:: python

        class BaseballTeamRoster(SetOf):
            '''
            ASN.1 specification:

            BaseballTeamRoster ::= SET SIZE (1..25) OF PlayerNames
            '''
            componentType = PlayerNames()
            subtypeSpec = ValueSizeConstraint(1, 25)

        # this will succeed
        team = BaseballTeamRoster()
        team.extend(['Jan', 'Matej'])
        encode(team)

        # this will raise ValueConstraintError
        team = BaseballTeamRoster()
        team.extend(['Jan'] * 26)
        encode(team)

    Note
    ----
    Whenever ValueSizeConstraint is applied to mutable types
    (e.g. :class:`~pyasn1.type.univ.SequenceOf`,
    :class:`~pyasn1.type.univ.SetOf`), constraint
    validation only happens at the serialisation phase rather
    than schema instantiation phase (as it is with immutable
    types).
    """
    def _testValue(self, value, idx):
        valueSize = len(value)
        if valueSize < self.start or valueSize > self.stop:
            raise error.ValueConstraintError(value)


class PermittedAlphabetConstraint(SingleValueConstraint):
    """Create a PermittedAlphabetConstraint object.

    The PermittedAlphabetConstraint satisfies any character
    string for as long as all its characters are present in
    the set of permitted characters.

    Objects of this type are iterable (emitting constraint values) and
    can act as operands for some arithmetic operations e.g. addition
    and subtraction.

    The PermittedAlphabetConstraint object can only be applied
    to the :ref:`character ASN.1 types <type.char>` such as
    :class:`~pyasn1.type.char.IA5String`.

    Parameters
    ----------
    *alphabet: :class:`str`
        Full set of characters permitted by this constraint object.

    Example
    -------
    .. code-block:: python

        class BooleanValue(IA5String):
            '''
            ASN.1 specification:

            BooleanValue ::= IA5String (FROM ('T' | 'F'))
            '''
            subtypeSpec = PermittedAlphabetConstraint('T', 'F')

        # this will succeed
        truth = BooleanValue('T')
        truth = BooleanValue('TF')

        # this will raise ValueConstraintError
        garbage = BooleanValue('TAF')

    ASN.1 `FROM ... EXCEPT ...` clause can be modelled by combining multiple
    PermittedAlphabetConstraint objects into one:

    Example
    -------
    .. code-block:: python

        class Lipogramme(IA5String):
            '''
            ASN.1 specification:

            Lipogramme ::=
                IA5String (FROM (ALL EXCEPT ("e"|"E")))
            '''
            subtypeSpec = (
                PermittedAlphabetConstraint(*string.printable) -
                PermittedAlphabetConstraint('e', 'E')
            )

        # this will succeed
        lipogramme = Lipogramme('A work of fiction?')

        # this will raise ValueConstraintError
        lipogramme = Lipogramme('Eel')

    Note
    ----
    Although `ConstraintsExclusion` object could seemingly be used for this
    purpose, practically, for it to work, it needs to represent its operand
    constraints as sets and intersect one with the other. That would require
    the insight into the constraint values (and their types) that are otherwise
    hidden inside the constraint object.

    Therefore it's more practical to model `EXCEPT` clause at
    `PermittedAlphabetConstraint` level instead.
    """
    def _setValues(self, values):
        self._values = values
        self._set = set(values)

    def _testValue(self, value, idx):
        if not self._set.issuperset(value):
            raise error.ValueConstraintError(value)


class ComponentPresentConstraint(AbstractConstraint):
    """Create a ComponentPresentConstraint object.

    The ComponentPresentConstraint is only satisfied when the value
    is not `None`.

    The ComponentPresentConstraint object is typically used with
    `WithComponentsConstraint`.

    Examples
    --------
    .. code-block:: python

        present = ComponentPresentConstraint()

        # this will succeed
        present('whatever')

        # this will raise ValueConstraintError
        present(None)
    """
    def _setValues(self, values):
        self._values = ('<must be present>',)

        if values:
            raise error.PyAsn1Error('No arguments expected')

    def _testValue(self, value, idx):
        if value is None:
            raise error.ValueConstraintError(
                'Component is not present:')


class ComponentAbsentConstraint(AbstractConstraint):
    """Create a ComponentAbsentConstraint object.

    The ComponentAbsentConstraint is only satisfied when the value
    is `None`.

    The ComponentAbsentConstraint object is typically used with
    `WithComponentsConstraint`.

    Examples
    --------
    .. code-block:: python

        absent = ComponentAbsentConstraint()

        # this will succeed
        absent(None)

        # this will raise ValueConstraintError
        absent('whatever')
    """
    def _setValues(self, values):
        self._values = ('<must be absent>',)

        if values:
            raise error.PyAsn1Error('No arguments expected')

    def _testValue(self, value, idx):
        if value is not None:
            raise error.ValueConstraintError(
                'Component is not absent: %r' % value)


class WithComponentsConstraint(AbstractConstraint):
    """Create a WithComponentsConstraint object.

    The `WithComponentsConstraint` satisfies any mapping object that has
    constrained fields present or absent, what is indicated by
    `ComponentPresentConstraint` and `ComponentAbsentConstraint`
    objects respectively.

    The `WithComponentsConstraint` object is typically applied
    to  :class:`~pyasn1.type.univ.Set` or
    :class:`~pyasn1.type.univ.Sequence` types.

    Parameters
    ----------
    *fields: :class:`tuple`
        Zero or more tuples of (`field`, `constraint`) indicating constrained
        fields.

    Notes
    -----
    On top of the primary use of `WithComponentsConstraint` (ensuring presence
    or absence of particular components of a :class:`~pyasn1.type.univ.Set` or
    :class:`~pyasn1.type.univ.Sequence`), it is also possible to pass any other
    constraint objects or their combinations. In case of scalar fields, these
    constraints will be verified in addition to the constraints belonging to
    scalar components themselves. However, formally, these additional
    constraints do not change the type of these ASN.1 objects.

    Examples
    --------

    .. code-block:: python

        class Item(Sequence):  #  Set is similar
            '''
            ASN.1 specification:

            Item ::= SEQUENCE {
                id    INTEGER OPTIONAL,
                name  OCTET STRING OPTIONAL
            } WITH COMPONENTS id PRESENT, name ABSENT | id ABSENT, name PRESENT
            '''
            componentType = NamedTypes(
                OptionalNamedType('id', Integer()),
                OptionalNamedType('name', OctetString())
            )
            withComponents = ConstraintsUnion(
                WithComponentsConstraint(
                    ('id', ComponentPresentConstraint()),
                    ('name', ComponentAbsentConstraint())
                ),
                WithComponentsConstraint(
                    ('id', ComponentAbsentConstraint()),
                    ('name', ComponentPresentConstraint())
                )
            )

        item = Item()

        # This will succeed
        item['id'] = 1

        # This will succeed
        item.reset()
        item['name'] = 'John'

        # This will fail (on encoding)
        item.reset()
        descr['id'] = 1
        descr['name'] = 'John'
    """
    def _testValue(self, value, idx):
        for field, constraint in self._values:
            constraint(value.get(field))

    def _setValues(self, values):
        AbstractConstraint._setValues(self, values)


# This is a bit kludgy, meaning two op modes within a single constraint
class InnerTypeConstraint(AbstractConstraint):
    """Value must satisfy the type and presence constraints"""

    def _testValue(self, value, idx):
        if self.__singleTypeConstraint:
            self.__singleTypeConstraint(value)
        elif self.__multipleTypeConstraint:
            if idx not in self.__multipleTypeConstraint:
                raise error.ValueConstraintError(value)
            constraint, status = self.__multipleTypeConstraint[idx]
            if status == 'ABSENT':  # XXX presence is not checked!
                raise error.ValueConstraintError(value)
            constraint(value)

    def _setValues(self, values):
        self.__multipleTypeConstraint = {}
        self.__singleTypeConstraint = None
        for v in values:
            if isinstance(v, tuple):
                self.__multipleTypeConstraint[v[0]] = v[1], v[2]
            else:
                self.__singleTypeConstraint = v
        AbstractConstraint._setValues(self, values)


# Logic operations on constraints

class ConstraintsExclusion(AbstractConstraint):
    """Create a ConstraintsExclusion logic operator object.

    The ConstraintsExclusion logic operator succeeds when the
    value does *not* satisfy the operand constraint.

    The ConstraintsExclusion object can be applied to
    any constraint and logic operator object.

    Parameters
    ----------
    *constraints:
        Constraint or logic operator objects.

    Examples
    --------
    .. code-block:: python

        class LuckyNumber(Integer):
            subtypeSpec = ConstraintsExclusion(
                SingleValueConstraint(13)
            )

        # this will succeed
        luckyNumber = LuckyNumber(12)

        # this will raise ValueConstraintError
        luckyNumber = LuckyNumber(13)

    Note
    ----
    The `FROM ... EXCEPT ...` ASN.1 clause should be modeled by combining
    constraint objects into one. See `PermittedAlphabetConstraint` for more
    information.
    """
    def _testValue(self, value, idx):
        for constraint in self._values:
            try:
                constraint(value, idx)

            except error.ValueConstraintError:
                continue

            raise error.ValueConstraintError(value)

    def _setValues(self, values):
        AbstractConstraint._setValues(self, values)


class AbstractConstraintSet(AbstractConstraint):

    def __getitem__(self, idx):
        return self._values[idx]

    def __iter__(self):
        return iter(self._values)

    def __add__(self, value):
        return self.__class__(*(self._values + (value,)))

    def __radd__(self, value):
        return self.__class__(*((value,) + self._values))

    def __len__(self):
        return len(self._values)

    # Constraints inclusion in sets

    def _setValues(self, values):
        self._values = values
        for constraint in values:
            if constraint:
                self._valueMap.add(constraint)
                self._valueMap.update(constraint.getValueMap())


class ConstraintsIntersection(AbstractConstraintSet):
    """Create a ConstraintsIntersection logic operator object.

    The ConstraintsIntersection logic operator only succeeds
    if *all* its operands succeed.

    The ConstraintsIntersection object can be applied to
    any constraint and logic operator objects.

    The ConstraintsIntersection object duck-types the immutable
    container object like Python :py:class:`tuple`.

    Parameters
    ----------
    *constraints:
        Constraint or logic operator objects.

    Examples
    --------
    .. code-block:: python

        class CapitalAndSmall(IA5String):
            '''
            ASN.1 specification:

            CapitalAndSmall ::=
                IA5String (FROM ("A".."Z"|"a".."z"))
            '''
            subtypeSpec = ConstraintsIntersection(
                PermittedAlphabetConstraint('A', 'Z'),
                PermittedAlphabetConstraint('a', 'z')
            )

        # this will succeed
        capital_and_small = CapitalAndSmall('Hello')

        # this will raise ValueConstraintError
        capital_and_small = CapitalAndSmall('hello')
    """
    def _testValue(self, value, idx):
        for constraint in self._values:
            constraint(value, idx)


class ConstraintsUnion(AbstractConstraintSet):
    """Create a ConstraintsUnion logic operator object.

    The ConstraintsUnion logic operator succeeds if
    *at least* a single operand succeeds.

    The ConstraintsUnion object can be applied to
    any constraint and logic operator objects.

    The ConstraintsUnion object duck-types the immutable
    container object like Python :py:class:`tuple`.

    Parameters
    ----------
    *constraints:
        Constraint or logic operator objects.

    Examples
    --------
    .. code-block:: python

        class CapitalOrSmall(IA5String):
            '''
            ASN.1 specification:

            CapitalOrSmall ::=
                IA5String (FROM ("A".."Z") | FROM ("a".."z"))
            '''
            subtypeSpec = ConstraintsUnion(
                PermittedAlphabetConstraint('A', 'Z'),
                PermittedAlphabetConstraint('a', 'z')
            )

        # this will succeed
        capital_or_small = CapitalAndSmall('Hello')

        # this will raise ValueConstraintError
        capital_or_small = CapitalOrSmall('hello!')
    """
    def _testValue(self, value, idx):
        for constraint in self._values:
            try:
                constraint(value, idx)
            except error.ValueConstraintError:
                pass
            else:
                return

        raise error.ValueConstraintError(
            'all of %s failed for "%s"' % (self._values, value)
        )

# TODO:
# refactor InnerTypeConstraint
# add tests for type check
# implement other constraint types
# make constraint validation easy to skip

# === NexusCore/myenv\Lib\site-packages\pip\_vendor\distlib\version.py ===
# -*- coding: utf-8 -*-
#
# Copyright (C) 2012-2023 The Python Software Foundation.
# See LICENSE.txt and CONTRIBUTORS.txt.
#
"""
Implementation of a flexible versioning scheme providing support for PEP-440,
setuptools-compatible and semantic versioning.
"""

import logging
import re

from .compat import string_types
from .util import parse_requirement

__all__ = ['NormalizedVersion', 'NormalizedMatcher',
           'LegacyVersion', 'LegacyMatcher',
           'SemanticVersion', 'SemanticMatcher',
           'UnsupportedVersionError', 'get_scheme']

logger = logging.getLogger(__name__)


class UnsupportedVersionError(ValueError):
    """This is an unsupported version."""
    pass


class Version(object):
    def __init__(self, s):
        self._string = s = s.strip()
        self._parts = parts = self.parse(s)
        assert isinstance(parts, tuple)
        assert len(parts) > 0

    def parse(self, s):
        raise NotImplementedError('please implement in a subclass')

    def _check_compatible(self, other):
        if type(self) != type(other):
            raise TypeError('cannot compare %r and %r' % (self, other))

    def __eq__(self, other):
        self._check_compatible(other)
        return self._parts == other._parts

    def __ne__(self, other):
        return not self.__eq__(other)

    def __lt__(self, other):
        self._check_compatible(other)
        return self._parts < other._parts

    def __gt__(self, other):
        return not (self.__lt__(other) or self.__eq__(other))

    def __le__(self, other):
        return self.__lt__(other) or self.__eq__(other)

    def __ge__(self, other):
        return self.__gt__(other) or self.__eq__(other)

    # See http://docs.python.org/reference/datamodel#object.__hash__
    def __hash__(self):
        return hash(self._parts)

    def __repr__(self):
        return "%s('%s')" % (self.__class__.__name__, self._string)

    def __str__(self):
        return self._string

    @property
    def is_prerelease(self):
        raise NotImplementedError('Please implement in subclasses.')


class Matcher(object):
    version_class = None

    # value is either a callable or the name of a method
    _operators = {
        '<': lambda v, c, p: v < c,
        '>': lambda v, c, p: v > c,
        '<=': lambda v, c, p: v == c or v < c,
        '>=': lambda v, c, p: v == c or v > c,
        '==': lambda v, c, p: v == c,
        '===': lambda v, c, p: v == c,
        # by default, compatible => >=.
        '~=': lambda v, c, p: v == c or v > c,
        '!=': lambda v, c, p: v != c,
    }

    # this is a method only to support alternative implementations
    # via overriding
    def parse_requirement(self, s):
        return parse_requirement(s)

    def __init__(self, s):
        if self.version_class is None:
            raise ValueError('Please specify a version class')
        self._string = s = s.strip()
        r = self.parse_requirement(s)
        if not r:
            raise ValueError('Not valid: %r' % s)
        self.name = r.name
        self.key = self.name.lower()    # for case-insensitive comparisons
        clist = []
        if r.constraints:
            # import pdb; pdb.set_trace()
            for op, s in r.constraints:
                if s.endswith('.*'):
                    if op not in ('==', '!='):
                        raise ValueError('\'.*\' not allowed for '
                                         '%r constraints' % op)
                    # Could be a partial version (e.g. for '2.*') which
                    # won't parse as a version, so keep it as a string
                    vn, prefix = s[:-2], True
                    # Just to check that vn is a valid version
                    self.version_class(vn)
                else:
                    # Should parse as a version, so we can create an
                    # instance for the comparison
                    vn, prefix = self.version_class(s), False
                clist.append((op, vn, prefix))
        self._parts = tuple(clist)

    def match(self, version):
        """
        Check if the provided version matches the constraints.

        :param version: The version to match against this instance.
        :type version: String or :class:`Version` instance.
        """
        if isinstance(version, string_types):
            version = self.version_class(version)
        for operator, constraint, prefix in self._parts:
            f = self._operators.get(operator)
            if isinstance(f, string_types):
                f = getattr(self, f)
            if not f:
                msg = ('%r not implemented '
                       'for %s' % (operator, self.__class__.__name__))
                raise NotImplementedError(msg)
            if not f(version, constraint, prefix):
                return False
        return True

    @property
    def exact_version(self):
        result = None
        if len(self._parts) == 1 and self._parts[0][0] in ('==', '==='):
            result = self._parts[0][1]
        return result

    def _check_compatible(self, other):
        if type(self) != type(other) or self.name != other.name:
            raise TypeError('cannot compare %s and %s' % (self, other))

    def __eq__(self, other):
        self._check_compatible(other)
        return self.key == other.key and self._parts == other._parts

    def __ne__(self, other):
        return not self.__eq__(other)

    # See http://docs.python.org/reference/datamodel#object.__hash__
    def __hash__(self):
        return hash(self.key) + hash(self._parts)

    def __repr__(self):
        return "%s(%r)" % (self.__class__.__name__, self._string)

    def __str__(self):
        return self._string


PEP440_VERSION_RE = re.compile(r'^v?(\d+!)?(\d+(\.\d+)*)((a|alpha|b|beta|c|rc|pre|preview)(\d+)?)?'
                               r'(\.(post|r|rev)(\d+)?)?([._-]?(dev)(\d+)?)?'
                               r'(\+([a-zA-Z\d]+(\.[a-zA-Z\d]+)?))?$', re.I)


def _pep_440_key(s):
    s = s.strip()
    m = PEP440_VERSION_RE.match(s)
    if not m:
        raise UnsupportedVersionError('Not a valid version: %s' % s)
    groups = m.groups()
    nums = tuple(int(v) for v in groups[1].split('.'))
    while len(nums) > 1 and nums[-1] == 0:
        nums = nums[:-1]

    if not groups[0]:
        epoch = 0
    else:
        epoch = int(groups[0][:-1])
    pre = groups[4:6]
    post = groups[7:9]
    dev = groups[10:12]
    local = groups[13]
    if pre == (None, None):
        pre = ()
    else:
        if pre[1] is None:
            pre = pre[0], 0
        else:
            pre = pre[0], int(pre[1])
    if post == (None, None):
        post = ()
    else:
        if post[1] is None:
            post = post[0], 0
        else:
            post = post[0], int(post[1])
    if dev == (None, None):
        dev = ()
    else:
        if dev[1] is None:
            dev = dev[0], 0
        else:
            dev = dev[0], int(dev[1])
    if local is None:
        local = ()
    else:
        parts = []
        for part in local.split('.'):
            # to ensure that numeric compares as > lexicographic, avoid
            # comparing them directly, but encode a tuple which ensures
            # correct sorting
            if part.isdigit():
                part = (1, int(part))
            else:
                part = (0, part)
            parts.append(part)
        local = tuple(parts)
    if not pre:
        # either before pre-release, or final release and after
        if not post and dev:
            # before pre-release
            pre = ('a', -1)     # to sort before a0
        else:
            pre = ('z',)        # to sort after all pre-releases
    # now look at the state of post and dev.
    if not post:
        post = ('_',)   # sort before 'a'
    if not dev:
        dev = ('final',)

    return epoch, nums, pre, post, dev, local


_normalized_key = _pep_440_key


class NormalizedVersion(Version):
    """A rational version.

    Good:
        1.2         # equivalent to "1.2.0"
        1.2.0
        1.2a1
        1.2.3a2
        1.2.3b1
        1.2.3c1
        1.2.3.4
        TODO: fill this out

    Bad:
        1           # minimum two numbers
        1.2a        # release level must have a release serial
        1.2.3b
    """
    def parse(self, s):
        result = _normalized_key(s)
        # _normalized_key loses trailing zeroes in the release
        # clause, since that's needed to ensure that X.Y == X.Y.0 == X.Y.0.0
        # However, PEP 440 prefix matching needs it: for example,
        # (~= 1.4.5.0) matches differently to (~= 1.4.5.0.0).
        m = PEP440_VERSION_RE.match(s)      # must succeed
        groups = m.groups()
        self._release_clause = tuple(int(v) for v in groups[1].split('.'))
        return result

    PREREL_TAGS = set(['a', 'b', 'c', 'rc', 'dev'])

    @property
    def is_prerelease(self):
        return any(t[0] in self.PREREL_TAGS for t in self._parts if t)


def _match_prefix(x, y):
    x = str(x)
    y = str(y)
    if x == y:
        return True
    if not x.startswith(y):
        return False
    n = len(y)
    return x[n] == '.'


class NormalizedMatcher(Matcher):
    version_class = NormalizedVersion

    # value is either a callable or the name of a method
    _operators = {
        '~=': '_match_compatible',
        '<': '_match_lt',
        '>': '_match_gt',
        '<=': '_match_le',
        '>=': '_match_ge',
        '==': '_match_eq',
        '===': '_match_arbitrary',
        '!=': '_match_ne',
    }

    def _adjust_local(self, version, constraint, prefix):
        if prefix:
            strip_local = '+' not in constraint and version._parts[-1]
        else:
            # both constraint and version are
            # NormalizedVersion instances.
            # If constraint does not have a local component,
            # ensure the version doesn't, either.
            strip_local = not constraint._parts[-1] and version._parts[-1]
        if strip_local:
            s = version._string.split('+', 1)[0]
            version = self.version_class(s)
        return version, constraint

    def _match_lt(self, version, constraint, prefix):
        version, constraint = self._adjust_local(version, constraint, prefix)
        if version >= constraint:
            return False
        release_clause = constraint._release_clause
        pfx = '.'.join([str(i) for i in release_clause])
        return not _match_prefix(version, pfx)

    def _match_gt(self, version, constraint, prefix):
        version, constraint = self._adjust_local(version, constraint, prefix)
        if version <= constraint:
            return False
        release_clause = constraint._release_clause
        pfx = '.'.join([str(i) for i in release_clause])
        return not _match_prefix(version, pfx)

    def _match_le(self, version, constraint, prefix):
        version, constraint = self._adjust_local(version, constraint, prefix)
        return version <= constraint

    def _match_ge(self, version, constraint, prefix):
        version, constraint = self._adjust_local(version, constraint, prefix)
        return version >= constraint

    def _match_eq(self, version, constraint, prefix):
        version, constraint = self._adjust_local(version, constraint, prefix)
        if not prefix:
            result = (version == constraint)
        else:
            result = _match_prefix(version, constraint)
        return result

    def _match_arbitrary(self, version, constraint, prefix):
        return str(version) == str(constraint)

    def _match_ne(self, version, constraint, prefix):
        version, constraint = self._adjust_local(version, constraint, prefix)
        if not prefix:
            result = (version != constraint)
        else:
            result = not _match_prefix(version, constraint)
        return result

    def _match_compatible(self, version, constraint, prefix):
        version, constraint = self._adjust_local(version, constraint, prefix)
        if version == constraint:
            return True
        if version < constraint:
            return False
#        if not prefix:
#            return True
        release_clause = constraint._release_clause
        if len(release_clause) > 1:
            release_clause = release_clause[:-1]
        pfx = '.'.join([str(i) for i in release_clause])
        return _match_prefix(version, pfx)


_REPLACEMENTS = (
    (re.compile('[.+-]$'), ''),                     # remove trailing puncts
    (re.compile(r'^[.](\d)'), r'0.\1'),             # .N -> 0.N at start
    (re.compile('^[.-]'), ''),                      # remove leading puncts
    (re.compile(r'^\((.*)\)$'), r'\1'),             # remove parentheses
    (re.compile(r'^v(ersion)?\s*(\d+)'), r'\2'),    # remove leading v(ersion)
    (re.compile(r'^r(ev)?\s*(\d+)'), r'\2'),        # remove leading v(ersion)
    (re.compile('[.]{2,}'), '.'),                   # multiple runs of '.'
    (re.compile(r'\b(alfa|apha)\b'), 'alpha'),      # misspelt alpha
    (re.compile(r'\b(pre-alpha|prealpha)\b'),
        'pre.alpha'),                               # standardise
    (re.compile(r'\(beta\)$'), 'beta'),             # remove parentheses
)

_SUFFIX_REPLACEMENTS = (
    (re.compile('^[:~._+-]+'), ''),                   # remove leading puncts
    (re.compile('[,*")([\\]]'), ''),                  # remove unwanted chars
    (re.compile('[~:+_ -]'), '.'),                    # replace illegal chars
    (re.compile('[.]{2,}'), '.'),                   # multiple runs of '.'
    (re.compile(r'\.$'), ''),                       # trailing '.'
)

_NUMERIC_PREFIX = re.compile(r'(\d+(\.\d+)*)')


def _suggest_semantic_version(s):
    """
    Try to suggest a semantic form for a version for which
    _suggest_normalized_version couldn't come up with anything.
    """
    result = s.strip().lower()
    for pat, repl in _REPLACEMENTS:
        result = pat.sub(repl, result)
    if not result:
        result = '0.0.0'

    # Now look for numeric prefix, and separate it out from
    # the rest.
    # import pdb; pdb.set_trace()
    m = _NUMERIC_PREFIX.match(result)
    if not m:
        prefix = '0.0.0'
        suffix = result
    else:
        prefix = m.groups()[0].split('.')
        prefix = [int(i) for i in prefix]
        while len(prefix) < 3:
            prefix.append(0)
        if len(prefix) == 3:
            suffix = result[m.end():]
        else:
            suffix = '.'.join([str(i) for i in prefix[3:]]) + result[m.end():]
            prefix = prefix[:3]
        prefix = '.'.join([str(i) for i in prefix])
        suffix = suffix.strip()
    if suffix:
        # import pdb; pdb.set_trace()
        # massage the suffix.
        for pat, repl in _SUFFIX_REPLACEMENTS:
            suffix = pat.sub(repl, suffix)

    if not suffix:
        result = prefix
    else:
        sep = '-' if 'dev' in suffix else '+'
        result = prefix + sep + suffix
    if not is_semver(result):
        result = None
    return result


def _suggest_normalized_version(s):
    """Suggest a normalized version close to the given version string.

    If you have a version string that isn't rational (i.e. NormalizedVersion
    doesn't like it) then you might be able to get an equivalent (or close)
    rational version from this function.

    This does a number of simple normalizations to the given string, based
    on observation of versions currently in use on PyPI. Given a dump of
    those version during PyCon 2009, 4287 of them:
    - 2312 (53.93%) match NormalizedVersion without change
      with the automatic suggestion
    - 3474 (81.04%) match when using this suggestion method

    @param s {str} An irrational version string.
    @returns A rational version string, or None, if couldn't determine one.
    """
    try:
        _normalized_key(s)
        return s   # already rational
    except UnsupportedVersionError:
        pass

    rs = s.lower()

    # part of this could use maketrans
    for orig, repl in (('-alpha', 'a'), ('-beta', 'b'), ('alpha', 'a'),
                       ('beta', 'b'), ('rc', 'c'), ('-final', ''),
                       ('-pre', 'c'),
                       ('-release', ''), ('.release', ''), ('-stable', ''),
                       ('+', '.'), ('_', '.'), (' ', ''), ('.final', ''),
                       ('final', '')):
        rs = rs.replace(orig, repl)

    # if something ends with dev or pre, we add a 0
    rs = re.sub(r"pre$", r"pre0", rs)
    rs = re.sub(r"dev$", r"dev0", rs)

    # if we have something like "b-2" or "a.2" at the end of the
    # version, that is probably beta, alpha, etc
    # let's remove the dash or dot
    rs = re.sub(r"([abc]|rc)[\-\.](\d+)$", r"\1\2", rs)

    # 1.0-dev-r371 -> 1.0.dev371
    # 0.1-dev-r79 -> 0.1.dev79
    rs = re.sub(r"[\-\.](dev)[\-\.]?r?(\d+)$", r".\1\2", rs)

    # Clean: 2.0.a.3, 2.0.b1, 0.9.0~c1
    rs = re.sub(r"[.~]?([abc])\.?", r"\1", rs)

    # Clean: v0.3, v1.0
    if rs.startswith('v'):
        rs = rs[1:]

    # Clean leading '0's on numbers.
    # TODO: unintended side-effect on, e.g., "2003.05.09"
    # PyPI stats: 77 (~2%) better
    rs = re.sub(r"\b0+(\d+)(?!\d)", r"\1", rs)

    # Clean a/b/c with no version. E.g. "1.0a" -> "1.0a0". Setuptools infers
    # zero.
    # PyPI stats: 245 (7.56%) better
    rs = re.sub(r"(\d+[abc])$", r"\g<1>0", rs)

    # the 'dev-rNNN' tag is a dev tag
    rs = re.sub(r"\.?(dev-r|dev\.r)\.?(\d+)$", r".dev\2", rs)

    # clean the - when used as a pre delimiter
    rs = re.sub(r"-(a|b|c)(\d+)$", r"\1\2", rs)

    # a terminal "dev" or "devel" can be changed into ".dev0"
    rs = re.sub(r"[\.\-](dev|devel)$", r".dev0", rs)

    # a terminal "dev" can be changed into ".dev0"
    rs = re.sub(r"(?![\.\-])dev$", r".dev0", rs)

    # a terminal "final" or "stable" can be removed
    rs = re.sub(r"(final|stable)$", "", rs)

    # The 'r' and the '-' tags are post release tags
    #   0.4a1.r10       ->  0.4a1.post10
    #   0.9.33-17222    ->  0.9.33.post17222
    #   0.9.33-r17222   ->  0.9.33.post17222
    rs = re.sub(r"\.?(r|-|-r)\.?(\d+)$", r".post\2", rs)

    # Clean 'r' instead of 'dev' usage:
    #   0.9.33+r17222   ->  0.9.33.dev17222
    #   1.0dev123       ->  1.0.dev123
    #   1.0.git123      ->  1.0.dev123
    #   1.0.bzr123      ->  1.0.dev123
    #   0.1a0dev.123    ->  0.1a0.dev123
    # PyPI stats:  ~150 (~4%) better
    rs = re.sub(r"\.?(dev|git|bzr)\.?(\d+)$", r".dev\2", rs)

    # Clean '.pre' (normalized from '-pre' above) instead of 'c' usage:
    #   0.2.pre1        ->  0.2c1
    #   0.2-c1         ->  0.2c1
    #   1.0preview123   ->  1.0c123
    # PyPI stats: ~21 (0.62%) better
    rs = re.sub(r"\.?(pre|preview|-c)(\d+)$", r"c\g<2>", rs)

    # Tcl/Tk uses "px" for their post release markers
    rs = re.sub(r"p(\d+)$", r".post\1", rs)

    try:
        _normalized_key(rs)
    except UnsupportedVersionError:
        rs = None
    return rs

#
#   Legacy version processing (distribute-compatible)
#


_VERSION_PART = re.compile(r'([a-z]+|\d+|[\.-])', re.I)
_VERSION_REPLACE = {
    'pre': 'c',
    'preview': 'c',
    '-': 'final-',
    'rc': 'c',
    'dev': '@',
    '': None,
    '.': None,
}


def _legacy_key(s):
    def get_parts(s):
        result = []
        for p in _VERSION_PART.split(s.lower()):
            p = _VERSION_REPLACE.get(p, p)
            if p:
                if '0' <= p[:1] <= '9':
                    p = p.zfill(8)
                else:
                    p = '*' + p
                result.append(p)
        result.append('*final')
        return result

    result = []
    for p in get_parts(s):
        if p.startswith('*'):
            if p < '*final':
                while result and result[-1] == '*final-':
                    result.pop()
            while result and result[-1] == '00000000':
                result.pop()
        result.append(p)
    return tuple(result)


class LegacyVersion(Version):
    def parse(self, s):
        return _legacy_key(s)

    @property
    def is_prerelease(self):
        result = False
        for x in self._parts:
            if (isinstance(x, string_types) and x.startswith('*') and x < '*final'):
                result = True
                break
        return result


class LegacyMatcher(Matcher):
    version_class = LegacyVersion

    _operators = dict(Matcher._operators)
    _operators['~='] = '_match_compatible'

    numeric_re = re.compile(r'^(\d+(\.\d+)*)')

    def _match_compatible(self, version, constraint, prefix):
        if version < constraint:
            return False
        m = self.numeric_re.match(str(constraint))
        if not m:
            logger.warning('Cannot compute compatible match for version %s '
                           ' and constraint %s', version, constraint)
            return True
        s = m.groups()[0]
        if '.' in s:
            s = s.rsplit('.', 1)[0]
        return _match_prefix(version, s)

#
#   Semantic versioning
#


_SEMVER_RE = re.compile(r'^(\d+)\.(\d+)\.(\d+)'
                        r'(-[a-z0-9]+(\.[a-z0-9-]+)*)?'
                        r'(\+[a-z0-9]+(\.[a-z0-9-]+)*)?$', re.I)


def is_semver(s):
    return _SEMVER_RE.match(s)


def _semantic_key(s):
    def make_tuple(s, absent):
        if s is None:
            result = (absent,)
        else:
            parts = s[1:].split('.')
            # We can't compare ints and strings on Python 3, so fudge it
            # by zero-filling numeric values so simulate a numeric comparison
            result = tuple([p.zfill(8) if p.isdigit() else p for p in parts])
        return result

    m = is_semver(s)
    if not m:
        raise UnsupportedVersionError(s)
    groups = m.groups()
    major, minor, patch = [int(i) for i in groups[:3]]
    # choose the '|' and '*' so that versions sort correctly
    pre, build = make_tuple(groups[3], '|'), make_tuple(groups[5], '*')
    return (major, minor, patch), pre, build


class SemanticVersion(Version):
    def parse(self, s):
        return _semantic_key(s)

    @property
    def is_prerelease(self):
        return self._parts[1][0] != '|'


class SemanticMatcher(Matcher):
    version_class = SemanticVersion


class VersionScheme(object):
    def __init__(self, key, matcher, suggester=None):
        self.key = key
        self.matcher = matcher
        self.suggester = suggester

    def is_valid_version(self, s):
        try:
            self.matcher.version_class(s)
            result = True
        except UnsupportedVersionError:
            result = False
        return result

    def is_valid_matcher(self, s):
        try:
            self.matcher(s)
            result = True
        except UnsupportedVersionError:
            result = False
        return result

    def is_valid_constraint_list(self, s):
        """
        Used for processing some metadata fields
        """
        # See issue #140. Be tolerant of a single trailing comma.
        if s.endswith(','):
            s = s[:-1]
        return self.is_valid_matcher('dummy_name (%s)' % s)

    def suggest(self, s):
        if self.suggester is None:
            result = None
        else:
            result = self.suggester(s)
        return result


_SCHEMES = {
    'normalized': VersionScheme(_normalized_key, NormalizedMatcher,
                                _suggest_normalized_version),
    'legacy': VersionScheme(_legacy_key, LegacyMatcher, lambda self, s: s),
    'semantic': VersionScheme(_semantic_key, SemanticMatcher,
                              _suggest_semantic_version),
}

_SCHEMES['default'] = _SCHEMES['normalized']


def get_scheme(name):
    if name not in _SCHEMES:
        raise ValueError('unknown scheme name: %r' % name)
    return _SCHEMES[name]

# === NexusCore/openenv\Lib\site-packages\mpl_toolkits\mplot3d\axis3d.py ===
# axis3d.py, original mplot3d version by John Porter
# Created: 23 Sep 2005
# Parts rewritten by Reinier Heeres <reinier@heeres.eu>

import inspect

import numpy as np

import matplotlib as mpl
from matplotlib import (
    _api, artist, lines as mlines, axis as maxis, patches as mpatches,
    transforms as mtransforms, colors as mcolors)
from . import art3d, proj3d


def _move_from_center(coord, centers, deltas, axmask=(True, True, True)):
    """
    For each coordinate where *axmask* is True, move *coord* away from
    *centers* by *deltas*.
    """
    coord = np.asarray(coord)
    return coord + axmask * np.copysign(1, coord - centers) * deltas


def _tick_update_position(tick, tickxs, tickys, labelpos):
    """Update tick line and label position and style."""

    tick.label1.set_position(labelpos)
    tick.label2.set_position(labelpos)
    tick.tick1line.set_visible(True)
    tick.tick2line.set_visible(False)
    tick.tick1line.set_linestyle('-')
    tick.tick1line.set_marker('')
    tick.tick1line.set_data(tickxs, tickys)
    tick.gridline.set_data([0], [0])


class Axis(maxis.XAxis):
    """An Axis class for the 3D plots."""
    # These points from the unit cube make up the x, y and z-planes
    _PLANES = (
        (0, 3, 7, 4), (1, 2, 6, 5),  # yz planes
        (0, 1, 5, 4), (3, 2, 6, 7),  # xz planes
        (0, 1, 2, 3), (4, 5, 6, 7),  # xy planes
    )

    # Some properties for the axes
    _AXINFO = {
        'x': {'i': 0, 'tickdir': 1, 'juggled': (1, 0, 2)},
        'y': {'i': 1, 'tickdir': 0, 'juggled': (0, 1, 2)},
        'z': {'i': 2, 'tickdir': 0, 'juggled': (0, 2, 1)},
    }

    def _old_init(self, adir, v_intervalx, d_intervalx, axes, *args,
                  rotate_label=None, **kwargs):
        return locals()

    def _new_init(self, axes, *, rotate_label=None, **kwargs):
        return locals()

    def __init__(self, *args, **kwargs):
        params = _api.select_matching_signature(
            [self._old_init, self._new_init], *args, **kwargs)
        if "adir" in params:
            _api.warn_deprecated(
                "3.6", message=f"The signature of 3D Axis constructors has "
                f"changed in %(since)s; the new signature is "
                f"{inspect.signature(type(self).__init__)}", pending=True)
            if params["adir"] != self.axis_name:
                raise ValueError(f"Cannot instantiate {type(self).__name__} "
                                 f"with adir={params['adir']!r}")
        axes = params["axes"]
        rotate_label = params["rotate_label"]
        args = params.get("args", ())
        kwargs = params["kwargs"]

        name = self.axis_name

        self._label_position = 'default'
        self._tick_position = 'default'

        # This is a temporary member variable.
        # Do not depend on this existing in future releases!
        self._axinfo = self._AXINFO[name].copy()
        # Common parts
        self._axinfo.update({
            'label': {'va': 'center', 'ha': 'center',
                      'rotation_mode': 'anchor'},
            'color': mpl.rcParams[f'axes3d.{name}axis.panecolor'],
            'tick': {
                'inward_factor': 0.2,
                'outward_factor': 0.1,
            },
        })

        if mpl.rcParams['_internal.classic_mode']:
            self._axinfo.update({
                'axisline': {'linewidth': 0.75, 'color': (0, 0, 0, 1)},
                'grid': {
                    'color': (0.9, 0.9, 0.9, 1),
                    'linewidth': 1.0,
                    'linestyle': '-',
                },
            })
            self._axinfo['tick'].update({
                'linewidth': {
                    True: mpl.rcParams['lines.linewidth'],  # major
                    False: mpl.rcParams['lines.linewidth'],  # minor
                }
            })
        else:
            self._axinfo.update({
                'axisline': {
                    'linewidth': mpl.rcParams['axes.linewidth'],
                    'color': mpl.rcParams['axes.edgecolor'],
                },
                'grid': {
                    'color': mpl.rcParams['grid.color'],
                    'linewidth': mpl.rcParams['grid.linewidth'],
                    'linestyle': mpl.rcParams['grid.linestyle'],
                },
            })
            self._axinfo['tick'].update({
                'linewidth': {
                    True: (  # major
                        mpl.rcParams['xtick.major.width'] if name in 'xz'
                        else mpl.rcParams['ytick.major.width']),
                    False: (  # minor
                        mpl.rcParams['xtick.minor.width'] if name in 'xz'
                        else mpl.rcParams['ytick.minor.width']),
                }
            })

        super().__init__(axes, *args, **kwargs)

        # data and viewing intervals for this direction
        if "d_intervalx" in params:
            self.set_data_interval(*params["d_intervalx"])
        if "v_intervalx" in params:
            self.set_view_interval(*params["v_intervalx"])
        self.set_rotate_label(rotate_label)
        self._init3d()  # Inline after init3d deprecation elapses.

    __init__.__signature__ = inspect.signature(_new_init)
    adir = _api.deprecated("3.6", pending=True)(
        property(lambda self: self.axis_name))

    def _init3d(self):
        self.line = mlines.Line2D(
            xdata=(0, 0), ydata=(0, 0),
            linewidth=self._axinfo['axisline']['linewidth'],
            color=self._axinfo['axisline']['color'],
            antialiased=True)

        # Store dummy data in Polygon object
        self.pane = mpatches.Polygon([[0, 0], [0, 1]], closed=False)
        self.set_pane_color(self._axinfo['color'])

        self.axes._set_artist_props(self.line)
        self.axes._set_artist_props(self.pane)
        self.gridlines = art3d.Line3DCollection([])
        self.axes._set_artist_props(self.gridlines)
        self.axes._set_artist_props(self.label)
        self.axes._set_artist_props(self.offsetText)
        # Need to be able to place the label at the correct location
        self.label._transform = self.axes.transData
        self.offsetText._transform = self.axes.transData

    @_api.deprecated("3.6", pending=True)
    def init3d(self):  # After deprecation elapses, inline _init3d to __init__.
        self._init3d()

    def get_major_ticks(self, numticks=None):
        ticks = super().get_major_ticks(numticks)
        for t in ticks:
            for obj in [
                    t.tick1line, t.tick2line, t.gridline, t.label1, t.label2]:
                obj.set_transform(self.axes.transData)
        return ticks

    def get_minor_ticks(self, numticks=None):
        ticks = super().get_minor_ticks(numticks)
        for t in ticks:
            for obj in [
                    t.tick1line, t.tick2line, t.gridline, t.label1, t.label2]:
                obj.set_transform(self.axes.transData)
        return ticks

    def set_ticks_position(self, position):
        """
        Set the ticks position.

        Parameters
        ----------
        position : {'lower', 'upper', 'both', 'default', 'none'}
            The position of the bolded axis lines, ticks, and tick labels.
        """
        _api.check_in_list(['lower', 'upper', 'both', 'default', 'none'],
                           position=position)
        self._tick_position = position

    def get_ticks_position(self):
        """
        Get the ticks position.

        Returns
        -------
        str : {'lower', 'upper', 'both', 'default', 'none'}
            The position of the bolded axis lines, ticks, and tick labels.
        """
        return self._tick_position

    def set_label_position(self, position):
        """
        Set the label position.

        Parameters
        ----------
        position : {'lower', 'upper', 'both', 'default', 'none'}
            The position of the axis label.
        """
        _api.check_in_list(['lower', 'upper', 'both', 'default', 'none'],
                           position=position)
        self._label_position = position

    def get_label_position(self):
        """
        Get the label position.

        Returns
        -------
        str : {'lower', 'upper', 'both', 'default', 'none'}
            The position of the axis label.
        """
        return self._label_position

    def set_pane_color(self, color, alpha=None):
        """
        Set pane color.

        Parameters
        ----------
        color : :mpltype:`color`
            Color for axis pane.
        alpha : float, optional
            Alpha value for axis pane. If None, base it on *color*.
        """
        color = mcolors.to_rgba(color, alpha)
        self._axinfo['color'] = color
        self.pane.set_edgecolor(color)
        self.pane.set_facecolor(color)
        self.pane.set_alpha(color[-1])
        self.stale = True

    def set_rotate_label(self, val):
        """
        Whether to rotate the axis label: True, False or None.
        If set to None the label will be rotated if longer than 4 chars.
        """
        self._rotate_label = val
        self.stale = True

    def get_rotate_label(self, text):
        if self._rotate_label is not None:
            return self._rotate_label
        else:
            return len(text) > 4

    def _get_coord_info(self):
        mins, maxs = np.array([
            self.axes.get_xbound(),
            self.axes.get_ybound(),
            self.axes.get_zbound(),
        ]).T

        # Project the bounds along the current position of the cube:
        bounds = mins[0], maxs[0], mins[1], maxs[1], mins[2], maxs[2]
        bounds_proj = self.axes._transformed_cube(bounds)

        # Determine which one of the parallel planes are higher up:
        means_z0 = np.zeros(3)
        means_z1 = np.zeros(3)
        for i in range(3):
            means_z0[i] = np.mean(bounds_proj[self._PLANES[2 * i], 2])
            means_z1[i] = np.mean(bounds_proj[self._PLANES[2 * i + 1], 2])
        highs = means_z0 < means_z1

        # Special handling for edge-on views
        equals = np.abs(means_z0 - means_z1) <= np.finfo(float).eps
        if np.sum(equals) == 2:
            vertical = np.where(~equals)[0][0]
            if vertical == 2:  # looking at XY plane
                highs = np.array([True, True, highs[2]])
            elif vertical == 1:  # looking at XZ plane
                highs = np.array([True, highs[1], False])
            elif vertical == 0:  # looking at YZ plane
                highs = np.array([highs[0], False, False])

        return mins, maxs, bounds_proj, highs

    def _calc_centers_deltas(self, maxs, mins):
        centers = 0.5 * (maxs + mins)
        # In mpl3.8, the scale factor was 1/12. mpl3.9 changes this to
        # 1/12 * 24/25 = 0.08 to compensate for the change in automargin
        # behavior and keep appearance the same. The 24/25 factor is from the
        # 1/48 padding added to each side of the axis in mpl3.8.
        scale = 0.08
        deltas = (maxs - mins) * scale
        return centers, deltas

    def _get_axis_line_edge_points(self, minmax, maxmin, position=None):
        """Get the edge points for the black bolded axis line."""
        # When changing vertical axis some of the axes has to be
        # moved to the other plane so it looks the same as if the z-axis
        # was the vertical axis.
        mb = [minmax, maxmin]  # line from origin to nearest corner to camera
        mb_rev = mb[::-1]
        mm = [[mb, mb_rev, mb_rev], [mb_rev, mb_rev, mb], [mb, mb, mb]]
        mm = mm[self.axes._vertical_axis][self._axinfo["i"]]

        juggled = self._axinfo["juggled"]
        edge_point_0 = mm[0].copy()  # origin point

        if ((position == 'lower' and mm[1][juggled[-1]] < mm[0][juggled[-1]]) or
                (position == 'upper' and mm[1][juggled[-1]] > mm[0][juggled[-1]])):
            edge_point_0[juggled[-1]] = mm[1][juggled[-1]]
        else:
            edge_point_0[juggled[0]] = mm[1][juggled[0]]

        edge_point_1 = edge_point_0.copy()
        edge_point_1[juggled[1]] = mm[1][juggled[1]]

        return edge_point_0, edge_point_1

    def _get_all_axis_line_edge_points(self, minmax, maxmin, axis_position=None):
        # Determine edge points for the axis lines
        edgep1s = []
        edgep2s = []
        position = []
        if axis_position in (None, 'default'):
            edgep1, edgep2 = self._get_axis_line_edge_points(minmax, maxmin)
            edgep1s = [edgep1]
            edgep2s = [edgep2]
            position = ['default']
        else:
            edgep1_l, edgep2_l = self._get_axis_line_edge_points(minmax, maxmin,
                                                                 position='lower')
            edgep1_u, edgep2_u = self._get_axis_line_edge_points(minmax, maxmin,
                                                                 position='upper')
            if axis_position in ('lower', 'both'):
                edgep1s.append(edgep1_l)
                edgep2s.append(edgep2_l)
                position.append('lower')
            if axis_position in ('upper', 'both'):
                edgep1s.append(edgep1_u)
                edgep2s.append(edgep2_u)
                position.append('upper')
        return edgep1s, edgep2s, position

    def _get_tickdir(self, position):
        """
        Get the direction of the tick.

        Parameters
        ----------
        position : str, optional : {'upper', 'lower', 'default'}
            The position of the axis.

        Returns
        -------
        tickdir : int
            Index which indicates which coordinate the tick line will
            align with.
        """
        _api.check_in_list(('upper', 'lower', 'default'), position=position)

        # TODO: Move somewhere else where it's triggered less:
        tickdirs_base = [v["tickdir"] for v in self._AXINFO.values()]  # default
        elev_mod = np.mod(self.axes.elev + 180, 360) - 180
        azim_mod = np.mod(self.axes.azim, 360)
        if position == 'upper':
            if elev_mod >= 0:
                tickdirs_base = [2, 2, 0]
            else:
                tickdirs_base = [1, 0, 0]
            if 0 <= azim_mod < 180:
                tickdirs_base[2] = 1
        elif position == 'lower':
            if elev_mod >= 0:
                tickdirs_base = [1, 0, 1]
            else:
                tickdirs_base = [2, 2, 1]
            if 0 <= azim_mod < 180:
                tickdirs_base[2] = 0
        info_i = [v["i"] for v in self._AXINFO.values()]

        i = self._axinfo["i"]
        vert_ax = self.axes._vertical_axis
        j = vert_ax - 2
        # default: tickdir = [[1, 2, 1], [2, 2, 0], [1, 0, 0]][vert_ax][i]
        tickdir = np.roll(info_i, -j)[np.roll(tickdirs_base, j)][i]
        return tickdir

    def active_pane(self):
        mins, maxs, tc, highs = self._get_coord_info()
        info = self._axinfo
        index = info['i']
        if not highs[index]:
            loc = mins[index]
            plane = self._PLANES[2 * index]
        else:
            loc = maxs[index]
            plane = self._PLANES[2 * index + 1]
        xys = np.array([tc[p] for p in plane])
        return xys, loc

    def draw_pane(self, renderer):
        """
        Draw pane.

        Parameters
        ----------
        renderer : `~matplotlib.backend_bases.RendererBase` subclass
        """
        renderer.open_group('pane3d', gid=self.get_gid())
        xys, loc = self.active_pane()
        self.pane.xy = xys[:, :2]
        self.pane.draw(renderer)
        renderer.close_group('pane3d')

    def _axmask(self):
        axmask = [True, True, True]
        axmask[self._axinfo["i"]] = False
        return axmask

    def _draw_ticks(self, renderer, edgep1, centers, deltas, highs,
                    deltas_per_point, pos):
        ticks = self._update_ticks()
        info = self._axinfo
        index = info["i"]
        juggled = info["juggled"]

        mins, maxs, tc, highs = self._get_coord_info()
        centers, deltas = self._calc_centers_deltas(maxs, mins)

        # Draw ticks:
        tickdir = self._get_tickdir(pos)
        tickdelta = deltas[tickdir] if highs[tickdir] else -deltas[tickdir]

        tick_info = info['tick']
        tick_out = tick_info['outward_factor'] * tickdelta
        tick_in = tick_info['inward_factor'] * tickdelta
        tick_lw = tick_info['linewidth']
        edgep1_tickdir = edgep1[tickdir]
        out_tickdir = edgep1_tickdir + tick_out
        in_tickdir = edgep1_tickdir - tick_in

        default_label_offset = 8.  # A rough estimate
        points = deltas_per_point * deltas
        for tick in ticks:
            # Get tick line positions
            pos = edgep1.copy()
            pos[index] = tick.get_loc()
            pos[tickdir] = out_tickdir
            x1, y1, z1 = proj3d.proj_transform(*pos, self.axes.M)
            pos[tickdir] = in_tickdir
            x2, y2, z2 = proj3d.proj_transform(*pos, self.axes.M)

            # Get position of label
            labeldeltas = (tick.get_pad() + default_label_offset) * points

            pos[tickdir] = edgep1_tickdir
            pos = _move_from_center(pos, centers, labeldeltas, self._axmask())
            lx, ly, lz = proj3d.proj_transform(*pos, self.axes.M)

            _tick_update_position(tick, (x1, x2), (y1, y2), (lx, ly))
            tick.tick1line.set_linewidth(tick_lw[tick._major])
            tick.draw(renderer)

    def _draw_offset_text(self, renderer, edgep1, edgep2, labeldeltas, centers,
                          highs, pep, dx, dy):
        # Get general axis information:
        info = self._axinfo
        index = info["i"]
        juggled = info["juggled"]
        tickdir = info["tickdir"]

        # Which of the two edge points do we want to
        # use for locating the offset text?
        if juggled[2] == 2:
            outeredgep = edgep1
            outerindex = 0
        else:
            outeredgep = edgep2
            outerindex = 1

        pos = _move_from_center(outeredgep, centers, labeldeltas,
                                self._axmask())
        olx, oly, olz = proj3d.proj_transform(*pos, self.axes.M)
        self.offsetText.set_text(self.major.formatter.get_offset())
        self.offsetText.set_position((olx, oly))
        angle = art3d._norm_text_angle(np.rad2deg(np.arctan2(dy, dx)))
        self.offsetText.set_rotation(angle)
        # Must set rotation mode to "anchor" so that
        # the alignment point is used as the "fulcrum" for rotation.
        self.offsetText.set_rotation_mode('anchor')

        # ----------------------------------------------------------------------
        # Note: the following statement for determining the proper alignment of
        # the offset text. This was determined entirely by trial-and-error
        # and should not be in any way considered as "the way".  There are
        # still some edge cases where alignment is not quite right, but this
        # seems to be more of a geometry issue (in other words, I might be
        # using the wrong reference points).
        #
        # (TT, FF, TF, FT) are the shorthand for the tuple of
        #   (centpt[tickdir] <= pep[tickdir, outerindex],
        #    centpt[index] <= pep[index, outerindex])
        #
        # Three-letters (e.g., TFT, FTT) are short-hand for the array of bools
        # from the variable 'highs'.
        # ---------------------------------------------------------------------
        centpt = proj3d.proj_transform(*centers, self.axes.M)
        if centpt[tickdir] > pep[tickdir, outerindex]:
            # if FT and if highs has an even number of Trues
            if (centpt[index] <= pep[index, outerindex]
                    and np.count_nonzero(highs) % 2 == 0):
                # Usually, this means align right, except for the FTT case,
                # in which offset for axis 1 and 2 are aligned left.
                if highs.tolist() == [False, True, True] and index in (1, 2):
                    align = 'left'
                else:
                    align = 'right'
            else:
                # The FF case
                align = 'left'
        else:
            # if TF and if highs has an even number of Trues
            if (centpt[index] > pep[index, outerindex]
                    and np.count_nonzero(highs) % 2 == 0):
                # Usually mean align left, except if it is axis 2
                align = 'right' if index == 2 else 'left'
            else:
                # The TT case
                align = 'right'

        self.offsetText.set_va('center')
        self.offsetText.set_ha(align)
        self.offsetText.draw(renderer)

    def _draw_labels(self, renderer, edgep1, edgep2, labeldeltas, centers, dx, dy):
        label = self._axinfo["label"]

        # Draw labels
        lxyz = 0.5 * (edgep1 + edgep2)
        lxyz = _move_from_center(lxyz, centers, labeldeltas, self._axmask())
        tlx, tly, tlz = proj3d.proj_transform(*lxyz, self.axes.M)
        self.label.set_position((tlx, tly))
        if self.get_rotate_label(self.label.get_text()):
            angle = art3d._norm_text_angle(np.rad2deg(np.arctan2(dy, dx)))
            self.label.set_rotation(angle)
        self.label.set_va(label['va'])
        self.label.set_ha(label['ha'])
        self.label.set_rotation_mode(label['rotation_mode'])
        self.label.draw(renderer)

    @artist.allow_rasterization
    def draw(self, renderer):
        self.label._transform = self.axes.transData
        self.offsetText._transform = self.axes.transData
        renderer.open_group("axis3d", gid=self.get_gid())

        # Get general axis information:
        mins, maxs, tc, highs = self._get_coord_info()
        centers, deltas = self._calc_centers_deltas(maxs, mins)

        # Calculate offset distances
        # A rough estimate; points are ambiguous since 3D plots rotate
        reltoinches = self.get_figure(root=False).dpi_scale_trans.inverted()
        ax_inches = reltoinches.transform(self.axes.bbox.size)
        ax_points_estimate = sum(72. * ax_inches)
        deltas_per_point = 48 / ax_points_estimate
        default_offset = 21.
        labeldeltas = (self.labelpad + default_offset) * deltas_per_point * deltas

        # Determine edge points for the axis lines
        minmax = np.where(highs, maxs, mins)  # "origin" point
        maxmin = np.where(~highs, maxs, mins)  # "opposite" corner near camera

        for edgep1, edgep2, pos in zip(*self._get_all_axis_line_edge_points(
                                           minmax, maxmin, self._tick_position)):
            # Project the edge points along the current position
            pep = proj3d._proj_trans_points([edgep1, edgep2], self.axes.M)
            pep = np.asarray(pep)

            # The transAxes transform is used because the Text object
            # rotates the text relative to the display coordinate system.
            # Therefore, if we want the labels to remain parallel to the
            # axis regardless of the aspect ratio, we need to convert the
            # edge points of the plane to display coordinates and calculate
            # an angle from that.
            # TODO: Maybe Text objects should handle this themselves?
            dx, dy = (self.axes.transAxes.transform([pep[0:2, 1]]) -
                      self.axes.transAxes.transform([pep[0:2, 0]]))[0]

            # Draw the lines
            self.line.set_data(pep[0], pep[1])
            self.line.draw(renderer)

            # Draw ticks
            self._draw_ticks(renderer, edgep1, centers, deltas, highs,
                             deltas_per_point, pos)

            # Draw Offset text
            self._draw_offset_text(renderer, edgep1, edgep2, labeldeltas,
                                   centers, highs, pep, dx, dy)

        for edgep1, edgep2, pos in zip(*self._get_all_axis_line_edge_points(
                                           minmax, maxmin, self._label_position)):
            # See comments above
            pep = proj3d._proj_trans_points([edgep1, edgep2], self.axes.M)
            pep = np.asarray(pep)
            dx, dy = (self.axes.transAxes.transform([pep[0:2, 1]]) -
                      self.axes.transAxes.transform([pep[0:2, 0]]))[0]

            # Draw labels
            self._draw_labels(renderer, edgep1, edgep2, labeldeltas, centers, dx, dy)

        renderer.close_group('axis3d')
        self.stale = False

    @artist.allow_rasterization
    def draw_grid(self, renderer):
        if not self.axes._draw_grid:
            return

        renderer.open_group("grid3d", gid=self.get_gid())

        ticks = self._update_ticks()
        if len(ticks):
            # Get general axis information:
            info = self._axinfo
            index = info["i"]

            mins, maxs, tc, highs = self._get_coord_info()

            minmax = np.where(highs, maxs, mins)
            maxmin = np.where(~highs, maxs, mins)

            # Grid points where the planes meet
            xyz0 = np.tile(minmax, (len(ticks), 1))
            xyz0[:, index] = [tick.get_loc() for tick in ticks]

            # Grid lines go from the end of one plane through the plane
            # intersection (at xyz0) to the end of the other plane.  The first
            # point (0) differs along dimension index-2 and the last (2) along
            # dimension index-1.
            lines = np.stack([xyz0, xyz0, xyz0], axis=1)
            lines[:, 0, index - 2] = maxmin[index - 2]
            lines[:, 2, index - 1] = maxmin[index - 1]
            self.gridlines.set_segments(lines)
            gridinfo = info['grid']
            self.gridlines.set_color(gridinfo['color'])
            self.gridlines.set_linewidth(gridinfo['linewidth'])
            self.gridlines.set_linestyle(gridinfo['linestyle'])
            self.gridlines.do_3d_projection()
            self.gridlines.draw(renderer)

        renderer.close_group('grid3d')

    # TODO: Get this to work (more) properly when mplot3d supports the
    #       transforms framework.
    def get_tightbbox(self, renderer=None, *, for_layout_only=False):
        # docstring inherited
        if not self.get_visible():
            return
        # We have to directly access the internal data structures
        # (and hope they are up to date) because at draw time we
        # shift the ticks and their labels around in (x, y) space
        # based on the projection, the current view port, and their
        # position in 3D space. If we extend the transforms framework
        # into 3D we would not need to do this different book keeping
        # than we do in the normal axis
        major_locs = self.get_majorticklocs()
        minor_locs = self.get_minorticklocs()

        ticks = [*self.get_minor_ticks(len(minor_locs)),
                 *self.get_major_ticks(len(major_locs))]
        view_low, view_high = self.get_view_interval()
        if view_low > view_high:
            view_low, view_high = view_high, view_low
        interval_t = self.get_transform().transform([view_low, view_high])

        ticks_to_draw = []
        for tick in ticks:
            try:
                loc_t = self.get_transform().transform(tick.get_loc())
            except AssertionError:
                # Transform.transform doesn't allow masked values but
                # some scales might make them, so we need this try/except.
                pass
            else:
                if mtransforms._interval_contains_close(interval_t, loc_t):
                    ticks_to_draw.append(tick)

        ticks = ticks_to_draw

        bb_1, bb_2 = self._get_ticklabel_bboxes(ticks, renderer)
        other = []

        if self.line.get_visible():
            other.append(self.line.get_window_extent(renderer))
        if (self.label.get_visible() and not for_layout_only and
                self.label.get_text()):
            other.append(self.label.get_window_extent(renderer))

        return mtransforms.Bbox.union([*bb_1, *bb_2, *other])

    d_interval = _api.deprecated(
        "3.6", alternative="get_data_interval", pending=True)(
            property(lambda self: self.get_data_interval(),
                     lambda self, minmax: self.set_data_interval(*minmax)))
    v_interval = _api.deprecated(
        "3.6", alternative="get_view_interval", pending=True)(
            property(lambda self: self.get_view_interval(),
                     lambda self, minmax: self.set_view_interval(*minmax)))


class XAxis(Axis):
    axis_name = "x"
    get_view_interval, set_view_interval = maxis._make_getset_interval(
        "view", "xy_viewLim", "intervalx")
    get_data_interval, set_data_interval = maxis._make_getset_interval(
        "data", "xy_dataLim", "intervalx")


class YAxis(Axis):
    axis_name = "y"
    get_view_interval, set_view_interval = maxis._make_getset_interval(
        "view", "xy_viewLim", "intervaly")
    get_data_interval, set_data_interval = maxis._make_getset_interval(
        "data", "xy_dataLim", "intervaly")


class ZAxis(Axis):
    axis_name = "z"
    get_view_interval, set_view_interval = maxis._make_getset_interval(
        "view", "zz_viewLim", "intervalx")
    get_data_interval, set_data_interval = maxis._make_getset_interval(
        "data", "zz_dataLim", "intervalx")

# === NexusCore/openenv\Lib\site-packages\pip\_vendor\distlib\version.py ===
# -*- coding: utf-8 -*-
#
# Copyright (C) 2012-2023 The Python Software Foundation.
# See LICENSE.txt and CONTRIBUTORS.txt.
#
"""
Implementation of a flexible versioning scheme providing support for PEP-440,
setuptools-compatible and semantic versioning.
"""

import logging
import re

from .compat import string_types
from .util import parse_requirement

__all__ = ['NormalizedVersion', 'NormalizedMatcher',
           'LegacyVersion', 'LegacyMatcher',
           'SemanticVersion', 'SemanticMatcher',
           'UnsupportedVersionError', 'get_scheme']

logger = logging.getLogger(__name__)


class UnsupportedVersionError(ValueError):
    """This is an unsupported version."""
    pass


class Version(object):
    def __init__(self, s):
        self._string = s = s.strip()
        self._parts = parts = self.parse(s)
        assert isinstance(parts, tuple)
        assert len(parts) > 0

    def parse(self, s):
        raise NotImplementedError('please implement in a subclass')

    def _check_compatible(self, other):
        if type(self) != type(other):
            raise TypeError('cannot compare %r and %r' % (self, other))

    def __eq__(self, other):
        self._check_compatible(other)
        return self._parts == other._parts

    def __ne__(self, other):
        return not self.__eq__(other)

    def __lt__(self, other):
        self._check_compatible(other)
        return self._parts < other._parts

    def __gt__(self, other):
        return not (self.__lt__(other) or self.__eq__(other))

    def __le__(self, other):
        return self.__lt__(other) or self.__eq__(other)

    def __ge__(self, other):
        return self.__gt__(other) or self.__eq__(other)

    # See http://docs.python.org/reference/datamodel#object.__hash__
    def __hash__(self):
        return hash(self._parts)

    def __repr__(self):
        return "%s('%s')" % (self.__class__.__name__, self._string)

    def __str__(self):
        return self._string

    @property
    def is_prerelease(self):
        raise NotImplementedError('Please implement in subclasses.')


class Matcher(object):
    version_class = None

    # value is either a callable or the name of a method
    _operators = {
        '<': lambda v, c, p: v < c,
        '>': lambda v, c, p: v > c,
        '<=': lambda v, c, p: v == c or v < c,
        '>=': lambda v, c, p: v == c or v > c,
        '==': lambda v, c, p: v == c,
        '===': lambda v, c, p: v == c,
        # by default, compatible => >=.
        '~=': lambda v, c, p: v == c or v > c,
        '!=': lambda v, c, p: v != c,
    }

    # this is a method only to support alternative implementations
    # via overriding
    def parse_requirement(self, s):
        return parse_requirement(s)

    def __init__(self, s):
        if self.version_class is None:
            raise ValueError('Please specify a version class')
        self._string = s = s.strip()
        r = self.parse_requirement(s)
        if not r:
            raise ValueError('Not valid: %r' % s)
        self.name = r.name
        self.key = self.name.lower()    # for case-insensitive comparisons
        clist = []
        if r.constraints:
            # import pdb; pdb.set_trace()
            for op, s in r.constraints:
                if s.endswith('.*'):
                    if op not in ('==', '!='):
                        raise ValueError('\'.*\' not allowed for '
                                         '%r constraints' % op)
                    # Could be a partial version (e.g. for '2.*') which
                    # won't parse as a version, so keep it as a string
                    vn, prefix = s[:-2], True
                    # Just to check that vn is a valid version
                    self.version_class(vn)
                else:
                    # Should parse as a version, so we can create an
                    # instance for the comparison
                    vn, prefix = self.version_class(s), False
                clist.append((op, vn, prefix))
        self._parts = tuple(clist)

    def match(self, version):
        """
        Check if the provided version matches the constraints.

        :param version: The version to match against this instance.
        :type version: String or :class:`Version` instance.
        """
        if isinstance(version, string_types):
            version = self.version_class(version)
        for operator, constraint, prefix in self._parts:
            f = self._operators.get(operator)
            if isinstance(f, string_types):
                f = getattr(self, f)
            if not f:
                msg = ('%r not implemented '
                       'for %s' % (operator, self.__class__.__name__))
                raise NotImplementedError(msg)
            if not f(version, constraint, prefix):
                return False
        return True

    @property
    def exact_version(self):
        result = None
        if len(self._parts) == 1 and self._parts[0][0] in ('==', '==='):
            result = self._parts[0][1]
        return result

    def _check_compatible(self, other):
        if type(self) != type(other) or self.name != other.name:
            raise TypeError('cannot compare %s and %s' % (self, other))

    def __eq__(self, other):
        self._check_compatible(other)
        return self.key == other.key and self._parts == other._parts

    def __ne__(self, other):
        return not self.__eq__(other)

    # See http://docs.python.org/reference/datamodel#object.__hash__
    def __hash__(self):
        return hash(self.key) + hash(self._parts)

    def __repr__(self):
        return "%s(%r)" % (self.__class__.__name__, self._string)

    def __str__(self):
        return self._string


PEP440_VERSION_RE = re.compile(r'^v?(\d+!)?(\d+(\.\d+)*)((a|alpha|b|beta|c|rc|pre|preview)(\d+)?)?'
                               r'(\.(post|r|rev)(\d+)?)?([._-]?(dev)(\d+)?)?'
                               r'(\+([a-zA-Z\d]+(\.[a-zA-Z\d]+)?))?$', re.I)


def _pep_440_key(s):
    s = s.strip()
    m = PEP440_VERSION_RE.match(s)
    if not m:
        raise UnsupportedVersionError('Not a valid version: %s' % s)
    groups = m.groups()
    nums = tuple(int(v) for v in groups[1].split('.'))
    while len(nums) > 1 and nums[-1] == 0:
        nums = nums[:-1]

    if not groups[0]:
        epoch = 0
    else:
        epoch = int(groups[0][:-1])
    pre = groups[4:6]
    post = groups[7:9]
    dev = groups[10:12]
    local = groups[13]
    if pre == (None, None):
        pre = ()
    else:
        if pre[1] is None:
            pre = pre[0], 0
        else:
            pre = pre[0], int(pre[1])
    if post == (None, None):
        post = ()
    else:
        if post[1] is None:
            post = post[0], 0
        else:
            post = post[0], int(post[1])
    if dev == (None, None):
        dev = ()
    else:
        if dev[1] is None:
            dev = dev[0], 0
        else:
            dev = dev[0], int(dev[1])
    if local is None:
        local = ()
    else:
        parts = []
        for part in local.split('.'):
            # to ensure that numeric compares as > lexicographic, avoid
            # comparing them directly, but encode a tuple which ensures
            # correct sorting
            if part.isdigit():
                part = (1, int(part))
            else:
                part = (0, part)
            parts.append(part)
        local = tuple(parts)
    if not pre:
        # either before pre-release, or final release and after
        if not post and dev:
            # before pre-release
            pre = ('a', -1)     # to sort before a0
        else:
            pre = ('z',)        # to sort after all pre-releases
    # now look at the state of post and dev.
    if not post:
        post = ('_',)   # sort before 'a'
    if not dev:
        dev = ('final',)

    return epoch, nums, pre, post, dev, local


_normalized_key = _pep_440_key


class NormalizedVersion(Version):
    """A rational version.

    Good:
        1.2         # equivalent to "1.2.0"
        1.2.0
        1.2a1
        1.2.3a2
        1.2.3b1
        1.2.3c1
        1.2.3.4
        TODO: fill this out

    Bad:
        1           # minimum two numbers
        1.2a        # release level must have a release serial
        1.2.3b
    """
    def parse(self, s):
        result = _normalized_key(s)
        # _normalized_key loses trailing zeroes in the release
        # clause, since that's needed to ensure that X.Y == X.Y.0 == X.Y.0.0
        # However, PEP 440 prefix matching needs it: for example,
        # (~= 1.4.5.0) matches differently to (~= 1.4.5.0.0).
        m = PEP440_VERSION_RE.match(s)      # must succeed
        groups = m.groups()
        self._release_clause = tuple(int(v) for v in groups[1].split('.'))
        return result

    PREREL_TAGS = set(['a', 'b', 'c', 'rc', 'dev'])

    @property
    def is_prerelease(self):
        return any(t[0] in self.PREREL_TAGS for t in self._parts if t)


def _match_prefix(x, y):
    x = str(x)
    y = str(y)
    if x == y:
        return True
    if not x.startswith(y):
        return False
    n = len(y)
    return x[n] == '.'


class NormalizedMatcher(Matcher):
    version_class = NormalizedVersion

    # value is either a callable or the name of a method
    _operators = {
        '~=': '_match_compatible',
        '<': '_match_lt',
        '>': '_match_gt',
        '<=': '_match_le',
        '>=': '_match_ge',
        '==': '_match_eq',
        '===': '_match_arbitrary',
        '!=': '_match_ne',
    }

    def _adjust_local(self, version, constraint, prefix):
        if prefix:
            strip_local = '+' not in constraint and version._parts[-1]
        else:
            # both constraint and version are
            # NormalizedVersion instances.
            # If constraint does not have a local component,
            # ensure the version doesn't, either.
            strip_local = not constraint._parts[-1] and version._parts[-1]
        if strip_local:
            s = version._string.split('+', 1)[0]
            version = self.version_class(s)
        return version, constraint

    def _match_lt(self, version, constraint, prefix):
        version, constraint = self._adjust_local(version, constraint, prefix)
        if version >= constraint:
            return False
        release_clause = constraint._release_clause
        pfx = '.'.join([str(i) for i in release_clause])
        return not _match_prefix(version, pfx)

    def _match_gt(self, version, constraint, prefix):
        version, constraint = self._adjust_local(version, constraint, prefix)
        if version <= constraint:
            return False
        release_clause = constraint._release_clause
        pfx = '.'.join([str(i) for i in release_clause])
        return not _match_prefix(version, pfx)

    def _match_le(self, version, constraint, prefix):
        version, constraint = self._adjust_local(version, constraint, prefix)
        return version <= constraint

    def _match_ge(self, version, constraint, prefix):
        version, constraint = self._adjust_local(version, constraint, prefix)
        return version >= constraint

    def _match_eq(self, version, constraint, prefix):
        version, constraint = self._adjust_local(version, constraint, prefix)
        if not prefix:
            result = (version == constraint)
        else:
            result = _match_prefix(version, constraint)
        return result

    def _match_arbitrary(self, version, constraint, prefix):
        return str(version) == str(constraint)

    def _match_ne(self, version, constraint, prefix):
        version, constraint = self._adjust_local(version, constraint, prefix)
        if not prefix:
            result = (version != constraint)
        else:
            result = not _match_prefix(version, constraint)
        return result

    def _match_compatible(self, version, constraint, prefix):
        version, constraint = self._adjust_local(version, constraint, prefix)
        if version == constraint:
            return True
        if version < constraint:
            return False
#        if not prefix:
#            return True
        release_clause = constraint._release_clause
        if len(release_clause) > 1:
            release_clause = release_clause[:-1]
        pfx = '.'.join([str(i) for i in release_clause])
        return _match_prefix(version, pfx)


_REPLACEMENTS = (
    (re.compile('[.+-]$'), ''),                     # remove trailing puncts
    (re.compile(r'^[.](\d)'), r'0.\1'),             # .N -> 0.N at start
    (re.compile('^[.-]'), ''),                      # remove leading puncts
    (re.compile(r'^\((.*)\)$'), r'\1'),             # remove parentheses
    (re.compile(r'^v(ersion)?\s*(\d+)'), r'\2'),    # remove leading v(ersion)
    (re.compile(r'^r(ev)?\s*(\d+)'), r'\2'),        # remove leading v(ersion)
    (re.compile('[.]{2,}'), '.'),                   # multiple runs of '.'
    (re.compile(r'\b(alfa|apha)\b'), 'alpha'),      # misspelt alpha
    (re.compile(r'\b(pre-alpha|prealpha)\b'),
        'pre.alpha'),                               # standardise
    (re.compile(r'\(beta\)$'), 'beta'),             # remove parentheses
)

_SUFFIX_REPLACEMENTS = (
    (re.compile('^[:~._+-]+'), ''),                   # remove leading puncts
    (re.compile('[,*")([\\]]'), ''),                  # remove unwanted chars
    (re.compile('[~:+_ -]'), '.'),                    # replace illegal chars
    (re.compile('[.]{2,}'), '.'),                   # multiple runs of '.'
    (re.compile(r'\.$'), ''),                       # trailing '.'
)

_NUMERIC_PREFIX = re.compile(r'(\d+(\.\d+)*)')


def _suggest_semantic_version(s):
    """
    Try to suggest a semantic form for a version for which
    _suggest_normalized_version couldn't come up with anything.
    """
    result = s.strip().lower()
    for pat, repl in _REPLACEMENTS:
        result = pat.sub(repl, result)
    if not result:
        result = '0.0.0'

    # Now look for numeric prefix, and separate it out from
    # the rest.
    # import pdb; pdb.set_trace()
    m = _NUMERIC_PREFIX.match(result)
    if not m:
        prefix = '0.0.0'
        suffix = result
    else:
        prefix = m.groups()[0].split('.')
        prefix = [int(i) for i in prefix]
        while len(prefix) < 3:
            prefix.append(0)
        if len(prefix) == 3:
            suffix = result[m.end():]
        else:
            suffix = '.'.join([str(i) for i in prefix[3:]]) + result[m.end():]
            prefix = prefix[:3]
        prefix = '.'.join([str(i) for i in prefix])
        suffix = suffix.strip()
    if suffix:
        # import pdb; pdb.set_trace()
        # massage the suffix.
        for pat, repl in _SUFFIX_REPLACEMENTS:
            suffix = pat.sub(repl, suffix)

    if not suffix:
        result = prefix
    else:
        sep = '-' if 'dev' in suffix else '+'
        result = prefix + sep + suffix
    if not is_semver(result):
        result = None
    return result


def _suggest_normalized_version(s):
    """Suggest a normalized version close to the given version string.

    If you have a version string that isn't rational (i.e. NormalizedVersion
    doesn't like it) then you might be able to get an equivalent (or close)
    rational version from this function.

    This does a number of simple normalizations to the given string, based
    on observation of versions currently in use on PyPI. Given a dump of
    those version during PyCon 2009, 4287 of them:
    - 2312 (53.93%) match NormalizedVersion without change
      with the automatic suggestion
    - 3474 (81.04%) match when using this suggestion method

    @param s {str} An irrational version string.
    @returns A rational version string, or None, if couldn't determine one.
    """
    try:
        _normalized_key(s)
        return s   # already rational
    except UnsupportedVersionError:
        pass

    rs = s.lower()

    # part of this could use maketrans
    for orig, repl in (('-alpha', 'a'), ('-beta', 'b'), ('alpha', 'a'),
                       ('beta', 'b'), ('rc', 'c'), ('-final', ''),
                       ('-pre', 'c'),
                       ('-release', ''), ('.release', ''), ('-stable', ''),
                       ('+', '.'), ('_', '.'), (' ', ''), ('.final', ''),
                       ('final', '')):
        rs = rs.replace(orig, repl)

    # if something ends with dev or pre, we add a 0
    rs = re.sub(r"pre$", r"pre0", rs)
    rs = re.sub(r"dev$", r"dev0", rs)

    # if we have something like "b-2" or "a.2" at the end of the
    # version, that is probably beta, alpha, etc
    # let's remove the dash or dot
    rs = re.sub(r"([abc]|rc)[\-\.](\d+)$", r"\1\2", rs)

    # 1.0-dev-r371 -> 1.0.dev371
    # 0.1-dev-r79 -> 0.1.dev79
    rs = re.sub(r"[\-\.](dev)[\-\.]?r?(\d+)$", r".\1\2", rs)

    # Clean: 2.0.a.3, 2.0.b1, 0.9.0~c1
    rs = re.sub(r"[.~]?([abc])\.?", r"\1", rs)

    # Clean: v0.3, v1.0
    if rs.startswith('v'):
        rs = rs[1:]

    # Clean leading '0's on numbers.
    # TODO: unintended side-effect on, e.g., "2003.05.09"
    # PyPI stats: 77 (~2%) better
    rs = re.sub(r"\b0+(\d+)(?!\d)", r"\1", rs)

    # Clean a/b/c with no version. E.g. "1.0a" -> "1.0a0". Setuptools infers
    # zero.
    # PyPI stats: 245 (7.56%) better
    rs = re.sub(r"(\d+[abc])$", r"\g<1>0", rs)

    # the 'dev-rNNN' tag is a dev tag
    rs = re.sub(r"\.?(dev-r|dev\.r)\.?(\d+)$", r".dev\2", rs)

    # clean the - when used as a pre delimiter
    rs = re.sub(r"-(a|b|c)(\d+)$", r"\1\2", rs)

    # a terminal "dev" or "devel" can be changed into ".dev0"
    rs = re.sub(r"[\.\-](dev|devel)$", r".dev0", rs)

    # a terminal "dev" can be changed into ".dev0"
    rs = re.sub(r"(?![\.\-])dev$", r".dev0", rs)

    # a terminal "final" or "stable" can be removed
    rs = re.sub(r"(final|stable)$", "", rs)

    # The 'r' and the '-' tags are post release tags
    #   0.4a1.r10       ->  0.4a1.post10
    #   0.9.33-17222    ->  0.9.33.post17222
    #   0.9.33-r17222   ->  0.9.33.post17222
    rs = re.sub(r"\.?(r|-|-r)\.?(\d+)$", r".post\2", rs)

    # Clean 'r' instead of 'dev' usage:
    #   0.9.33+r17222   ->  0.9.33.dev17222
    #   1.0dev123       ->  1.0.dev123
    #   1.0.git123      ->  1.0.dev123
    #   1.0.bzr123      ->  1.0.dev123
    #   0.1a0dev.123    ->  0.1a0.dev123
    # PyPI stats:  ~150 (~4%) better
    rs = re.sub(r"\.?(dev|git|bzr)\.?(\d+)$", r".dev\2", rs)

    # Clean '.pre' (normalized from '-pre' above) instead of 'c' usage:
    #   0.2.pre1        ->  0.2c1
    #   0.2-c1         ->  0.2c1
    #   1.0preview123   ->  1.0c123
    # PyPI stats: ~21 (0.62%) better
    rs = re.sub(r"\.?(pre|preview|-c)(\d+)$", r"c\g<2>", rs)

    # Tcl/Tk uses "px" for their post release markers
    rs = re.sub(r"p(\d+)$", r".post\1", rs)

    try:
        _normalized_key(rs)
    except UnsupportedVersionError:
        rs = None
    return rs

#
#   Legacy version processing (distribute-compatible)
#


_VERSION_PART = re.compile(r'([a-z]+|\d+|[\.-])', re.I)
_VERSION_REPLACE = {
    'pre': 'c',
    'preview': 'c',
    '-': 'final-',
    'rc': 'c',
    'dev': '@',
    '': None,
    '.': None,
}


def _legacy_key(s):
    def get_parts(s):
        result = []
        for p in _VERSION_PART.split(s.lower()):
            p = _VERSION_REPLACE.get(p, p)
            if p:
                if '0' <= p[:1] <= '9':
                    p = p.zfill(8)
                else:
                    p = '*' + p
                result.append(p)
        result.append('*final')
        return result

    result = []
    for p in get_parts(s):
        if p.startswith('*'):
            if p < '*final':
                while result and result[-1] == '*final-':
                    result.pop()
            while result and result[-1] == '00000000':
                result.pop()
        result.append(p)
    return tuple(result)


class LegacyVersion(Version):
    def parse(self, s):
        return _legacy_key(s)

    @property
    def is_prerelease(self):
        result = False
        for x in self._parts:
            if (isinstance(x, string_types) and x.startswith('*') and x < '*final'):
                result = True
                break
        return result


class LegacyMatcher(Matcher):
    version_class = LegacyVersion

    _operators = dict(Matcher._operators)
    _operators['~='] = '_match_compatible'

    numeric_re = re.compile(r'^(\d+(\.\d+)*)')

    def _match_compatible(self, version, constraint, prefix):
        if version < constraint:
            return False
        m = self.numeric_re.match(str(constraint))
        if not m:
            logger.warning('Cannot compute compatible match for version %s '
                           ' and constraint %s', version, constraint)
            return True
        s = m.groups()[0]
        if '.' in s:
            s = s.rsplit('.', 1)[0]
        return _match_prefix(version, s)

#
#   Semantic versioning
#


_SEMVER_RE = re.compile(r'^(\d+)\.(\d+)\.(\d+)'
                        r'(-[a-z0-9]+(\.[a-z0-9-]+)*)?'
                        r'(\+[a-z0-9]+(\.[a-z0-9-]+)*)?$', re.I)


def is_semver(s):
    return _SEMVER_RE.match(s)


def _semantic_key(s):
    def make_tuple(s, absent):
        if s is None:
            result = (absent,)
        else:
            parts = s[1:].split('.')
            # We can't compare ints and strings on Python 3, so fudge it
            # by zero-filling numeric values so simulate a numeric comparison
            result = tuple([p.zfill(8) if p.isdigit() else p for p in parts])
        return result

    m = is_semver(s)
    if not m:
        raise UnsupportedVersionError(s)
    groups = m.groups()
    major, minor, patch = [int(i) for i in groups[:3]]
    # choose the '|' and '*' so that versions sort correctly
    pre, build = make_tuple(groups[3], '|'), make_tuple(groups[5], '*')
    return (major, minor, patch), pre, build


class SemanticVersion(Version):
    def parse(self, s):
        return _semantic_key(s)

    @property
    def is_prerelease(self):
        return self._parts[1][0] != '|'


class SemanticMatcher(Matcher):
    version_class = SemanticVersion


class VersionScheme(object):
    def __init__(self, key, matcher, suggester=None):
        self.key = key
        self.matcher = matcher
        self.suggester = suggester

    def is_valid_version(self, s):
        try:
            self.matcher.version_class(s)
            result = True
        except UnsupportedVersionError:
            result = False
        return result

    def is_valid_matcher(self, s):
        try:
            self.matcher(s)
            result = True
        except UnsupportedVersionError:
            result = False
        return result

    def is_valid_constraint_list(self, s):
        """
        Used for processing some metadata fields
        """
        # See issue #140. Be tolerant of a single trailing comma.
        if s.endswith(','):
            s = s[:-1]
        return self.is_valid_matcher('dummy_name (%s)' % s)

    def suggest(self, s):
        if self.suggester is None:
            result = None
        else:
            result = self.suggester(s)
        return result


_SCHEMES = {
    'normalized': VersionScheme(_normalized_key, NormalizedMatcher,
                                _suggest_normalized_version),
    'legacy': VersionScheme(_legacy_key, LegacyMatcher, lambda self, s: s),
    'semantic': VersionScheme(_semantic_key, SemanticMatcher,
                              _suggest_semantic_version),
}

_SCHEMES['default'] = _SCHEMES['normalized']


def get_scheme(name):
    if name not in _SCHEMES:
        raise ValueError('unknown scheme name: %r' % name)
    return _SCHEMES[name]