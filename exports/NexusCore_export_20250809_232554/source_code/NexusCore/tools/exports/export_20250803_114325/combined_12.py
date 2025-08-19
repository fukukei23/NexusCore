
# === NexusCore/src\sandbox_logs\repair_20250713_134136_fixed.py ===
エラーメッセージから見ると、エラーは無効な文字 '、' (U+3001) によるもので、これはPythonが理解できない文字です。このエラーは、通常、非ASCII文字がコード内に含まれている場合に発生します。PythonはデフォルトでASCII文字のみをサポートしており、その他の文字を使用する場合は、ファイルの先頭に特定のエンコーディングを指定する必要があります。

ただし、このエラーメッセージは、Pythonコードとして解釈できない日本語のコメントが含まれているために発生している可能性が高いです。Pythonのコメントは '#' 記号で始まります。

したがって、元のコードには実際のエラーはなく、コメントを正しくフォーマットすれば問題は解決するはずです。

修正後のコードは以下の通りです：

```python
# 以下は、pytest形式のユニットテストの一例です。
def add(a, b):
    return a + b
```

ただし、このエラーメッセージはunittestを使用してテストを実行しようとしたときに発生しているようです。そのため、実際には、この関数をテストするための適切なテストケースが必要になるでしょう。

# === NexusCore/src\sandbox_logs\repair_20250713_134145_original.py ===
エラーメッセージから見ると、エラーは無効な文字 '、' (U+3001) によるもので、これはPythonが理解できない文字です。このエラーは、通常、非ASCII文字がコード内に含まれている場合に発生します。PythonはデフォルトでASCII文字のみをサポートしており、その他の文字を使用する場合は、ファイルの先頭に特定のエンコーディングを指定する必要があります。

ただし、このエラーメッセージは、Pythonコードとして解釈できない日本語のコメントが含まれているために発生している可能性が高いです。Pythonのコメントは '#' 記号で始まります。

したがって、元のコードには実際のエラーはなく、コメントを正しくフォーマットすれば問題は解決するはずです。

修正後のコードは以下の通りです：

```python
# 以下は、pytest形式のユニットテストの一例です。
def add(a, b):
    return a + b
```

ただし、このエラーメッセージはunittestを使用してテストを実行しようとしたときに発生しているようです。そのため、実際には、この関数をテストするための適切なテストケースが必要になるでしょう。

# === NexusCore/src\sandbox_logs\repair_20250713_213259_fixed.py ===
エラーメッセージから見ると、問題はPythonコードではなく、テストコードにあるようです。エラーメッセージは、テストコードの1行目に無効な文字があると指摘しています。これは、PythonがASCII以外の文字を認識できないためです。

ただし、提供された情報からは、テストコードの内容を確認することはできません。したがって、具体的な修正方法を提案することはできません。

ただし、一般的なアドバイスとしては、Pythonコードやテストコードに非ASCII文字（日本語など）を使用する場合は、ファイルの先頭に文字エンコーディングを指定することをお勧めします。これは、Pythonがファイルの文字エンコーディングを正しく認識するために必要です。

以下のように、ファイルの先頭に文字エンコーディングを指定します：

```python
# -*- coding: utf-8 -*-
```

この行を追加すると、PythonはファイルがUTF-8でエンコードされていることを認識し、非ASCII文字を正しく処理できます。

ただし、この修正が問題を解決するかどうかは、テストコードの他の部分にどのような内容が含まれているかによります。

# === NexusCore/src\sandbox_logs\repair_20250713_213319_original.py ===
エラーメッセージから見ると、問題はPythonコードではなく、テストコードにあるようです。エラーメッセージは、テストコードの1行目に無効な文字があると指摘しています。これは、PythonがASCII以外の文字を認識できないためです。

ただし、提供された情報からは、テストコードの内容を確認することはできません。したがって、具体的な修正方法を提案することはできません。

ただし、一般的なアドバイスとしては、Pythonコードやテストコードに非ASCII文字（日本語など）を使用する場合は、ファイルの先頭に文字エンコーディングを指定することをお勧めします。これは、Pythonがファイルの文字エンコーディングを正しく認識するために必要です。

以下のように、ファイルの先頭に文字エンコーディングを指定します：

```python
# -*- coding: utf-8 -*-
```

この行を追加すると、PythonはファイルがUTF-8でエンコードされていることを認識し、非ASCII文字を正しく処理できます。

ただし、この修正が問題を解決するかどうかは、テストコードの他の部分にどのような内容が含まれているかによります。

# === NexusCore/openenv\Lib\site-packages\IPython\lib\backgroundjobs.py ===
# -*- coding: utf-8 -*-
"""Manage background (threaded) jobs conveniently from an interactive shell.

This module provides a BackgroundJobManager class.  This is the main class
meant for public usage, it implements an object which can create and manage
new background jobs.

It also provides the actual job classes managed by these BackgroundJobManager
objects, see their docstrings below.


This system was inspired by discussions with B. Granger and the
BackgroundCommand class described in the book Python Scripting for
Computational Science, by H. P. Langtangen:

http://folk.uio.no/hpl/scripting

(although ultimately no code from this text was used, as IPython's system is a
separate implementation).

An example notebook is provided in our documentation illustrating interactive
use of the system.
"""

#*****************************************************************************
#       Copyright (C) 2005-2006 Fernando Perez <fperez@colorado.edu>
#
#  Distributed under the terms of the BSD License.  The full license is in
#  the file COPYING, distributed as part of this software.
#*****************************************************************************

# Code begins
import sys
import threading

from IPython import get_ipython
from IPython.core.ultratb import AutoFormattedTB
from logging import error, debug


class BackgroundJobManager:
    """Class to manage a pool of backgrounded threaded jobs.

    Below, we assume that 'jobs' is a BackgroundJobManager instance.
    
    Usage summary (see the method docstrings for details):

      jobs.new(...) -> start a new job
      
      jobs() or jobs.status() -> print status summary of all jobs

      jobs[N] -> returns job number N.

      foo = jobs[N].result -> assign to variable foo the result of job N

      jobs[N].traceback() -> print the traceback of dead job N

      jobs.remove(N) -> remove (finished) job N

      jobs.flush() -> remove all finished jobs
      
    As a convenience feature, BackgroundJobManager instances provide the
    utility result and traceback methods which retrieve the corresponding
    information from the jobs list:

      jobs.result(N) <--> jobs[N].result
      jobs.traceback(N) <--> jobs[N].traceback()

    While this appears minor, it allows you to use tab completion
    interactively on the job manager instance.
    """

    def __init__(self):
        # Lists for job management, accessed via a property to ensure they're
        # up to date.x
        self._running  = []
        self._completed = []
        self._dead = []
        # A dict of all jobs, so users can easily access any of them
        self.all = {}
        # For reporting
        self._comp_report = []
        self._dead_report = []
        # Store status codes locally for fast lookups
        self._s_created   = BackgroundJobBase.stat_created_c
        self._s_running   = BackgroundJobBase.stat_running_c
        self._s_completed = BackgroundJobBase.stat_completed_c
        self._s_dead      = BackgroundJobBase.stat_dead_c
        self._current_job_id = 0

    @property
    def running(self):
        self._update_status()
        return self._running

    @property
    def dead(self):
        self._update_status()
        return self._dead

    @property
    def completed(self):
        self._update_status()
        return self._completed

    def new(self, func_or_exp, *args, **kwargs):
        """Add a new background job and start it in a separate thread.

        There are two types of jobs which can be created:

        1. Jobs based on expressions which can be passed to an eval() call.
        The expression must be given as a string.  For example:

          job_manager.new('myfunc(x,y,z=1)'[,glob[,loc]])

        The given expression is passed to eval(), along with the optional
        global/local dicts provided.  If no dicts are given, they are
        extracted automatically from the caller's frame.

        A Python statement is NOT a valid eval() expression.  Basically, you
        can only use as an eval() argument something which can go on the right
        of an '=' sign and be assigned to a variable.

        For example,"print 'hello'" is not valid, but '2+3' is.

        2. Jobs given a function object, optionally passing additional
        positional arguments:

          job_manager.new(myfunc, x, y)

        The function is called with the given arguments.

        If you need to pass keyword arguments to your function, you must
        supply them as a dict named kw:

          job_manager.new(myfunc, x, y, kw=dict(z=1))

        The reason for this asymmetry is that the new() method needs to
        maintain access to its own keywords, and this prevents name collisions
        between arguments to new() and arguments to your own functions.

        In both cases, the result is stored in the job.result field of the
        background job object.

        You can set `daemon` attribute of the thread by giving the keyword
        argument `daemon`.

        Notes and caveats:

        1. All threads running share the same standard output.  Thus, if your
        background jobs generate output, it will come out on top of whatever
        you are currently writing.  For this reason, background jobs are best
        used with silent functions which simply return their output.

        2. Threads also all work within the same global namespace, and this
        system does not lock interactive variables.  So if you send job to the
        background which operates on a mutable object for a long time, and
        start modifying that same mutable object interactively (or in another
        backgrounded job), all sorts of bizarre behaviour will occur.

        3. If a background job is spending a lot of time inside a C extension
        module which does not release the Python Global Interpreter Lock
        (GIL), this will block the IPython prompt.  This is simply because the
        Python interpreter can only switch between threads at Python
        bytecodes.  While the execution is inside C code, the interpreter must
        simply wait unless the extension module releases the GIL.

        4. There is no way, due to limitations in the Python threads library,
        to kill a thread once it has started."""
        
        if callable(func_or_exp):
            kw  = kwargs.get('kw',{})
            job = BackgroundJobFunc(func_or_exp,*args,**kw)
        elif isinstance(func_or_exp, str):
            if not args:
                frame = sys._getframe(1)
                glob, loc = frame.f_globals, frame.f_locals
            elif len(args)==1:
                glob = loc = args[0]
            elif len(args)==2:
                glob,loc = args
            else:
                raise ValueError(
                      'Expression jobs take at most 2 args (globals,locals)')
            job = BackgroundJobExpr(func_or_exp, glob, loc)
        else:
            raise TypeError('invalid args for new job')

        if kwargs.get('daemon', False):
            job.daemon = True
        job.num = self._current_job_id
        self._current_job_id += 1
        self.running.append(job)
        self.all[job.num] = job
        debug('Starting job # %s in a separate thread.' % job.num)
        job.start()
        return job

    def __getitem__(self, job_key):
        num = job_key if isinstance(job_key, int) else job_key.num
        return self.all[num]

    def __call__(self):
        """An alias to self.status(),

        This allows you to simply call a job manager instance much like the
        Unix `jobs` shell command."""

        return self.status()

    def _update_status(self):
        """Update the status of the job lists.

        This method moves finished jobs to one of two lists:
          - self.completed: jobs which completed successfully
          - self.dead: jobs which finished but died.

        It also copies those jobs to corresponding _report lists.  These lists
        are used to report jobs completed/dead since the last update, and are
        then cleared by the reporting function after each call."""

        # Status codes
        srun, scomp, sdead = self._s_running, self._s_completed, self._s_dead
        # State lists, use the actual lists b/c the public names are properties
        # that call this very function on access
        running, completed, dead = self._running, self._completed, self._dead

        # Now, update all state lists
        for num, job in enumerate(running):
            stat = job.stat_code
            if stat == srun:
                continue
            elif stat == scomp:
                completed.append(job)
                self._comp_report.append(job)
                running[num] = False
            elif stat == sdead:
                dead.append(job)
                self._dead_report.append(job)
                running[num] = False
        # Remove dead/completed jobs from running list
        running[:] = filter(None, running)

    def _group_report(self,group,name):
        """Report summary for a given job group.

        Return True if the group had any elements."""

        if group:
            print('%s jobs:' % name)
            for job in group:
                print('%s : %s' % (job.num,job))
            print()
            return True

    def _group_flush(self,group,name):
        """Flush a given job group

        Return True if the group had any elements."""

        njobs = len(group)
        if njobs:
            plural = {1:''}.setdefault(njobs,'s')
            print('Flushing %s %s job%s.' % (njobs,name,plural))
            group[:] = []
            return True
        
    def _status_new(self):
        """Print the status of newly finished jobs.

        Return True if any new jobs are reported.

        This call resets its own state every time, so it only reports jobs
        which have finished since the last time it was called."""

        self._update_status()
        new_comp = self._group_report(self._comp_report, 'Completed')
        new_dead = self._group_report(self._dead_report,
                                      'Dead, call jobs.traceback() for details')
        self._comp_report[:] = []
        self._dead_report[:] = []
        return new_comp or new_dead
                
    def status(self,verbose=0):
        """Print a status of all jobs currently being managed."""

        self._update_status()
        self._group_report(self.running,'Running')
        self._group_report(self.completed,'Completed')
        self._group_report(self.dead,'Dead')
        # Also flush the report queues
        self._comp_report[:] = []
        self._dead_report[:] = []

    def remove(self,num):
        """Remove a finished (completed or dead) job."""

        try:
            job = self.all[num]
        except KeyError:
            error('Job #%s not found' % num)
        else:
            stat_code = job.stat_code
            if stat_code == self._s_running:
                error('Job #%s is still running, it can not be removed.' % num)
                return
            elif stat_code == self._s_completed:
                self.completed.remove(job)
            elif stat_code == self._s_dead:
                self.dead.remove(job)

    def flush(self):
        """Flush all finished jobs (completed and dead) from lists.

        Running jobs are never flushed.

        It first calls _status_new(), to update info. If any jobs have
        completed since the last _status_new() call, the flush operation
        aborts."""

        # Remove the finished jobs from the master dict
        alljobs = self.all
        for job in self.completed+self.dead:
            del(alljobs[job.num])

        # Now flush these lists completely
        fl_comp = self._group_flush(self.completed, 'Completed')
        fl_dead = self._group_flush(self.dead, 'Dead')
        if not (fl_comp or fl_dead):
            print('No jobs to flush.')

    def result(self,num):
        """result(N) -> return the result of job N."""
        try:
            return self.all[num].result
        except KeyError:
            error('Job #%s not found' % num)

    def _traceback(self, job):
        num = job if isinstance(job, int) else job.num
        try:
            self.all[num].traceback()
        except KeyError:
            error('Job #%s not found' % num)

    def traceback(self, job=None):
        if job is None:
            self._update_status()
            for deadjob in self.dead:
                print("Traceback for: %r" % deadjob)
                self._traceback(deadjob)
                print()
        else:
            self._traceback(job)


class BackgroundJobBase(threading.Thread):
    """Base class to build BackgroundJob classes.

    The derived classes must implement:

    - Their own __init__, since the one here raises NotImplementedError.  The
      derived constructor must call self._init() at the end, to provide common
      initialization.

    - A strform attribute used in calls to __str__.

    - A call() method, which will make the actual execution call and must
      return a value to be held in the 'result' field of the job object.
    """

    # Class constants for status, in string and as numerical codes (when
    # updating jobs lists, we don't want to do string comparisons).  This will
    # be done at every user prompt, so it has to be as fast as possible
    stat_created   = 'Created'; stat_created_c = 0
    stat_running   = 'Running'; stat_running_c = 1
    stat_completed = 'Completed'; stat_completed_c = 2
    stat_dead      = 'Dead (Exception), call jobs.traceback() for details'
    stat_dead_c = -1

    def __init__(self):
        """Must be implemented in subclasses.

        Subclasses must call :meth:`_init` for standard initialisation.
        """
        raise NotImplementedError("This class can not be instantiated directly.")

    def _init(self):
        """Common initialization for all BackgroundJob objects"""
        
        for attr in ['call','strform']:
            assert hasattr(self,attr), "Missing attribute <%s>" % attr
        
        # The num tag can be set by an external job manager
        self.num = None
      
        self.status    = BackgroundJobBase.stat_created
        self.stat_code = BackgroundJobBase.stat_created_c
        self.finished  = False
        self.result    = '<BackgroundJob has not completed>'
        
        # reuse the ipython traceback handler if we can get to it, otherwise
        # make a new one
        try:
            make_tb = get_ipython().InteractiveTB.text
        except:
            make_tb = AutoFormattedTB(
                mode="Context", color_scheme="nocolor", tb_offset=1
            ).text
        # Note that the actual API for text() requires the three args to be
        # passed in, so we wrap it in a simple lambda.
        self._make_tb = lambda : make_tb(None, None, None)

        # Hold a formatted traceback if one is generated.
        self._tb = None
        
        threading.Thread.__init__(self)

    def __str__(self):
        return self.strform

    def __repr__(self):
        return '<BackgroundJob #%d: %s>' % (self.num, self.strform)

    def traceback(self):
        print(self._tb)
        
    def run(self):
        try:
            self.status    = BackgroundJobBase.stat_running
            self.stat_code = BackgroundJobBase.stat_running_c
            self.result    = self.call()
        except:
            self.status    = BackgroundJobBase.stat_dead
            self.stat_code = BackgroundJobBase.stat_dead_c
            self.finished  = None
            self.result    = ('<BackgroundJob died, call jobs.traceback() for details>')
            self._tb       = self._make_tb()
        else:
            self.status    = BackgroundJobBase.stat_completed
            self.stat_code = BackgroundJobBase.stat_completed_c
            self.finished  = True


class BackgroundJobExpr(BackgroundJobBase):
    """Evaluate an expression as a background job (uses a separate thread)."""

    def __init__(self, expression, glob=None, loc=None):
        """Create a new job from a string which can be fed to eval().

        global/locals dicts can be provided, which will be passed to the eval
        call."""

        # fail immediately if the given expression can't be compiled
        self.code = compile(expression,'<BackgroundJob compilation>','eval')
                
        glob = {} if glob is None else glob
        loc = {} if loc is None else loc
        self.expression = self.strform = expression
        self.glob = glob
        self.loc = loc
        self._init()
        
    def call(self):
        return eval(self.code,self.glob,self.loc)


class BackgroundJobFunc(BackgroundJobBase):
    """Run a function call as a background job (uses a separate thread)."""

    def __init__(self, func, *args, **kwargs):
        """Create a new job from a callable object.

        Any positional arguments and keyword args given to this constructor
        after the initial callable are passed directly to it."""

        if not callable(func):
            raise TypeError(
                'first argument to BackgroundJobFunc must be callable')
        
        self.func = func
        self.args = args
        self.kwargs = kwargs
        # The string form will only include the function passed, because
        # generating string representations of the arguments is a potentially
        # _very_ expensive operation (e.g. with large arrays).
        self.strform = str(func)
        self._init()

    def call(self):
        return self.func(*self.args, **self.kwargs)

# === NexusCore/exported_projects\app_20250703_223016\app\utils\pricing_calculator.py ===
# app/utils/pricing_calculator.py

def calculate_profit(purchase_price, selling_price, shipping_cost=0, fee_rate=0.15):
    """
    商品の利益を計算します。
    :param purchase_price: 仕入価格
    :param selling_price: 販売価格
    :param shipping_cost: 想定される発送費用 (固定値または動的に計算)
    :param fee_rate: 販売プラットフォームの手数料率 (例: BUYMAの15%)
    :return: 利益
    """
    fees = selling_price * fee_rate
    profit = selling_price - purchase_price - fees - shipping_cost
    return profit

# === NexusCore/exported_projects\project_export_m73owrzi\app\utils\pricing_calculator.py ===
# app/utils/pricing_calculator.py

def calculate_profit(purchase_price, selling_price, shipping_cost=0, fee_rate=0.15):
    """
    商品の利益を計算します。
    :param purchase_price: 仕入価格
    :param selling_price: 販売価格
    :param shipping_cost: 想定される発送費用 (固定値または動的に計算)
    :param fee_rate: 販売プラットフォームの手数料率 (例: BUYMAの15%)
    :return: 利益
    """
    fees = selling_price * fee_rate
    profit = selling_price - purchase_price - fees - shipping_cost
    return profit

# === NexusCore/exported_projects\project_export_xb_l70t8\app\utils\pricing_calculator.py ===
# app/utils/pricing_calculator.py

def calculate_profit(purchase_price, selling_price, shipping_cost=0, fee_rate=0.15):
    """
    商品の利益を計算します。
    :param purchase_price: 仕入価格
    :param selling_price: 販売価格
    :param shipping_cost: 想定される発送費用 (固定値または動的に計算)
    :param fee_rate: 販売プラットフォームの手数料率 (例: BUYMAの15%)
    :return: 利益
    """
    fees = selling_price * fee_rate
    profit = selling_price - purchase_price - fees - shipping_cost
    return profit

# === NexusCore/exported_projects\project_export_y7xxp1v8\app\utils\pricing_calculator.py ===
# app/utils/pricing_calculator.py

def calculate_profit(purchase_price, selling_price, shipping_cost=0, fee_rate=0.15):
    """
    商品の利益を計算します。
    :param purchase_price: 仕入価格
    :param selling_price: 販売価格
    :param shipping_cost: 想定される発送費用 (固定値または動的に計算)
    :param fee_rate: 販売プラットフォームの手数料率 (例: BUYMAの15%)
    :return: 利益
    """
    fees = selling_price * fee_rate
    profit = selling_price - purchase_price - fees - shipping_cost
    return profit

# === NexusCore/quality_gate_test_sandbox\app\calculator.py ===
def add_two_numbers(a: int, b: int) -> int:
    """
    Create a function 'add' that takes two integers 'a' and 'b' and returns their sum.
    """
    return a + b


def test_add_two_numbers():
    """Test cases for add_two_numbers function."""
    assert add_two_numbers(2, 3) == 5
    assert add_two_numbers(-2, 3) == 1
    assert add_two_numbers(2, -3) == -1
    assert add_two_numbers(0, 0) == 0
    assert add_two_numbers(100, 200) == 300

# === NexusCore/src\utils\app.py ===
# ✅ app.py（Flask + Gradio 並行起動）
from flask import Flask
from routes_ai_repair import bp as repair_bp
import threading
from gradio_ui import gradio_launch  # Gradio UI 関数インポート

app = Flask(__name__)
app.register_blueprint(repair_bp)

# Gradio 並行起動（非ブロッキング）
threading.Thread(target=gradio_launch, daemon=True).start()

if __name__ == "__main__":
    app.run(debug=True)

# === NexusCore/openenv\Lib\site-packages\win32\lib\sspicon.py ===
# Generated by h2py from c:\microsoft sdk\include\sspi.h
ISSP_LEVEL = 32
ISSP_MODE = 1


def SEC_SUCCESS(Status):
    return (Status) >= 0


SECPKG_FLAG_INTEGRITY = 1
SECPKG_FLAG_PRIVACY = 2
SECPKG_FLAG_TOKEN_ONLY = 4
SECPKG_FLAG_DATAGRAM = 8
SECPKG_FLAG_CONNECTION = 16
SECPKG_FLAG_MULTI_REQUIRED = 32
SECPKG_FLAG_CLIENT_ONLY = 64
SECPKG_FLAG_EXTENDED_ERROR = 128
SECPKG_FLAG_IMPERSONATION = 256
SECPKG_FLAG_ACCEPT_WIN32_NAME = 512
SECPKG_FLAG_STREAM = 1024
SECPKG_FLAG_NEGOTIABLE = 2048
SECPKG_FLAG_GSS_COMPATIBLE = 4096
SECPKG_FLAG_LOGON = 8192
SECPKG_FLAG_ASCII_BUFFERS = 16384
SECPKG_FLAG_FRAGMENT = 32768
SECPKG_FLAG_MUTUAL_AUTH = 65536
SECPKG_FLAG_DELEGATION = 131072
SECPKG_FLAG_READONLY_WITH_CHECKSUM = 262144
SECPKG_ID_NONE = 65535

SECBUFFER_VERSION = 0
SECBUFFER_EMPTY = 0
SECBUFFER_DATA = 1
SECBUFFER_TOKEN = 2
SECBUFFER_PKG_PARAMS = 3
SECBUFFER_MISSING = 4
SECBUFFER_EXTRA = 5
SECBUFFER_STREAM_TRAILER = 6
SECBUFFER_STREAM_HEADER = 7
SECBUFFER_NEGOTIATION_INFO = 8
SECBUFFER_PADDING = 9
SECBUFFER_STREAM = 10
SECBUFFER_MECHLIST = 11
SECBUFFER_MECHLIST_SIGNATURE = 12
SECBUFFER_TARGET = 13
SECBUFFER_CHANNEL_BINDINGS = 14
SECBUFFER_ATTRMASK = -268435456
SECBUFFER_READONLY = -2147483648
SECBUFFER_READONLY_WITH_CHECKSUM = 268435456
SECBUFFER_RESERVED = 1610612736

SECURITY_NATIVE_DREP = 16
SECURITY_NETWORK_DREP = 0

SECPKG_CRED_INBOUND = 1
SECPKG_CRED_OUTBOUND = 2
SECPKG_CRED_BOTH = 3
SECPKG_CRED_DEFAULT = 4
SECPKG_CRED_RESERVED = -268435456

ISC_REQ_DELEGATE = 1
ISC_REQ_MUTUAL_AUTH = 2
ISC_REQ_REPLAY_DETECT = 4
ISC_REQ_SEQUENCE_DETECT = 8
ISC_REQ_CONFIDENTIALITY = 16
ISC_REQ_USE_SESSION_KEY = 32
ISC_REQ_PROMPT_FOR_CREDS = 64
ISC_REQ_USE_SUPPLIED_CREDS = 128
ISC_REQ_ALLOCATE_MEMORY = 256
ISC_REQ_USE_DCE_STYLE = 512
ISC_REQ_DATAGRAM = 1024
ISC_REQ_CONNECTION = 2048
ISC_REQ_CALL_LEVEL = 4096
ISC_REQ_FRAGMENT_SUPPLIED = 8192
ISC_REQ_EXTENDED_ERROR = 16384
ISC_REQ_STREAM = 32768
ISC_REQ_INTEGRITY = 65536
ISC_REQ_IDENTIFY = 131072
ISC_REQ_NULL_SESSION = 262144
ISC_REQ_MANUAL_CRED_VALIDATION = 524288
ISC_REQ_RESERVED1 = 1048576
ISC_REQ_FRAGMENT_TO_FIT = 2097152
ISC_REQ_HTTP = 0x10000000
ISC_RET_DELEGATE = 1
ISC_RET_MUTUAL_AUTH = 2
ISC_RET_REPLAY_DETECT = 4
ISC_RET_SEQUENCE_DETECT = 8
ISC_RET_CONFIDENTIALITY = 16
ISC_RET_USE_SESSION_KEY = 32
ISC_RET_USED_COLLECTED_CREDS = 64
ISC_RET_USED_SUPPLIED_CREDS = 128
ISC_RET_ALLOCATED_MEMORY = 256
ISC_RET_USED_DCE_STYLE = 512
ISC_RET_DATAGRAM = 1024
ISC_RET_CONNECTION = 2048
ISC_RET_INTERMEDIATE_RETURN = 4096
ISC_RET_CALL_LEVEL = 8192
ISC_RET_EXTENDED_ERROR = 16384
ISC_RET_STREAM = 32768
ISC_RET_INTEGRITY = 65536
ISC_RET_IDENTIFY = 131072
ISC_RET_NULL_SESSION = 262144
ISC_RET_MANUAL_CRED_VALIDATION = 524288
ISC_RET_RESERVED1 = 1048576
ISC_RET_FRAGMENT_ONLY = 2097152

ASC_REQ_DELEGATE = 1
ASC_REQ_MUTUAL_AUTH = 2
ASC_REQ_REPLAY_DETECT = 4
ASC_REQ_SEQUENCE_DETECT = 8
ASC_REQ_CONFIDENTIALITY = 16
ASC_REQ_USE_SESSION_KEY = 32
ASC_REQ_ALLOCATE_MEMORY = 256
ASC_REQ_USE_DCE_STYLE = 512
ASC_REQ_DATAGRAM = 1024
ASC_REQ_CONNECTION = 2048
ASC_REQ_CALL_LEVEL = 4096
ASC_REQ_EXTENDED_ERROR = 32768
ASC_REQ_STREAM = 65536
ASC_REQ_INTEGRITY = 131072
ASC_REQ_LICENSING = 262144
ASC_REQ_IDENTIFY = 524288
ASC_REQ_ALLOW_NULL_SESSION = 1048576
ASC_REQ_ALLOW_NON_USER_LOGONS = 2097152
ASC_REQ_ALLOW_CONTEXT_REPLAY = 4194304
ASC_REQ_FRAGMENT_TO_FIT = 8388608
ASC_REQ_FRAGMENT_SUPPLIED = 8192
ASC_REQ_NO_TOKEN = 16777216
ASC_RET_DELEGATE = 1
ASC_RET_MUTUAL_AUTH = 2
ASC_RET_REPLAY_DETECT = 4
ASC_RET_SEQUENCE_DETECT = 8
ASC_RET_CONFIDENTIALITY = 16
ASC_RET_USE_SESSION_KEY = 32
ASC_RET_ALLOCATED_MEMORY = 256
ASC_RET_USED_DCE_STYLE = 512
ASC_RET_DATAGRAM = 1024
ASC_RET_CONNECTION = 2048
ASC_RET_CALL_LEVEL = 8192
ASC_RET_THIRD_LEG_FAILED = 16384
ASC_RET_EXTENDED_ERROR = 32768
ASC_RET_STREAM = 65536
ASC_RET_INTEGRITY = 131072
ASC_RET_LICENSING = 262144
ASC_RET_IDENTIFY = 524288
ASC_RET_NULL_SESSION = 1048576
ASC_RET_ALLOW_NON_USER_LOGONS = 2097152
ASC_RET_ALLOW_CONTEXT_REPLAY = 4194304
ASC_RET_FRAGMENT_ONLY = 8388608

SECPKG_CRED_ATTR_NAMES = 1
SECPKG_ATTR_SIZES = 0
SECPKG_ATTR_NAMES = 1
SECPKG_ATTR_LIFESPAN = 2
SECPKG_ATTR_DCE_INFO = 3
SECPKG_ATTR_STREAM_SIZES = 4
SECPKG_ATTR_KEY_INFO = 5
SECPKG_ATTR_AUTHORITY = 6
SECPKG_ATTR_PROTO_INFO = 7
SECPKG_ATTR_PASSWORD_EXPIRY = 8
SECPKG_ATTR_SESSION_KEY = 9
SECPKG_ATTR_PACKAGE_INFO = 10
SECPKG_ATTR_USER_FLAGS = 11
SECPKG_ATTR_NEGOTIATION_INFO = 12
SECPKG_ATTR_NATIVE_NAMES = 13
SECPKG_ATTR_FLAGS = 14
SECPKG_ATTR_USE_VALIDATED = 15
SECPKG_ATTR_CREDENTIAL_NAME = 16
SECPKG_ATTR_TARGET_INFORMATION = 17
SECPKG_ATTR_ACCESS_TOKEN = 18
SECPKG_ATTR_TARGET = 19
SECPKG_ATTR_AUTHENTICATION_ID = 20

## attributes from schannel.h
SECPKG_ATTR_REMOTE_CERT_CONTEXT = 83
SECPKG_ATTR_LOCAL_CERT_CONTEXT = 84
SECPKG_ATTR_ROOT_STORE = 85
SECPKG_ATTR_SUPPORTED_ALGS = 86
SECPKG_ATTR_CIPHER_STRENGTHS = 87
SECPKG_ATTR_SUPPORTED_PROTOCOLS = 88
SECPKG_ATTR_ISSUER_LIST_EX = 89
SECPKG_ATTR_CONNECTION_INFO = 90
SECPKG_ATTR_EAP_KEY_BLOCK = 91
SECPKG_ATTR_MAPPED_CRED_ATTR = 92
SECPKG_ATTR_SESSION_INFO = 93
SECPKG_ATTR_APP_DATA = 94

SECPKG_NEGOTIATION_COMPLETE = 0
SECPKG_NEGOTIATION_OPTIMISTIC = 1
SECPKG_NEGOTIATION_IN_PROGRESS = 2
SECPKG_NEGOTIATION_DIRECT = 3
SECPKG_NEGOTIATION_TRY_MULTICRED = 4
SECPKG_CONTEXT_EXPORT_RESET_NEW = 1
SECPKG_CONTEXT_EXPORT_DELETE_OLD = 2
SECQOP_WRAP_NO_ENCRYPT = -2147483647
SECURITY_ENTRYPOINT_ANSIW = "InitSecurityInterfaceW"
SECURITY_ENTRYPOINT_ANSIA = "InitSecurityInterfaceA"
SECURITY_ENTRYPOINT16 = "INITSECURITYINTERFACEA"
SECURITY_ENTRYPOINT = SECURITY_ENTRYPOINT16
SECURITY_ENTRYPOINT_ANSI = SECURITY_ENTRYPOINT16
SECURITY_SUPPORT_PROVIDER_INTERFACE_VERSION = 1
SECURITY_SUPPORT_PROVIDER_INTERFACE_VERSION_2 = 2
SASL_OPTION_SEND_SIZE = 1
SASL_OPTION_RECV_SIZE = 2
SASL_OPTION_AUTHZ_STRING = 3
SASL_OPTION_AUTHZ_PROCESSING = 4
SEC_WINNT_AUTH_IDENTITY_ANSI = 1
SEC_WINNT_AUTH_IDENTITY_UNICODE = 2
SEC_WINNT_AUTH_IDENTITY_VERSION = 512
SEC_WINNT_AUTH_IDENTITY_MARSHALLED = 4
SEC_WINNT_AUTH_IDENTITY_ONLY = 8
SECPKG_OPTIONS_TYPE_UNKNOWN = 0
SECPKG_OPTIONS_TYPE_LSA = 1
SECPKG_OPTIONS_TYPE_SSPI = 2
SECPKG_OPTIONS_PERMANENT = 1

SEC_E_INSUFFICIENT_MEMORY = -2146893056
SEC_E_INVALID_HANDLE = -2146893055
SEC_E_UNSUPPORTED_FUNCTION = -2146893054
SEC_E_TARGET_UNKNOWN = -2146893053
SEC_E_INTERNAL_ERROR = -2146893052
SEC_E_SECPKG_NOT_FOUND = -2146893051
SEC_E_NOT_OWNER = -2146893050
SEC_E_CANNOT_INSTALL = -2146893049
SEC_E_INVALID_TOKEN = -2146893048
SEC_E_CANNOT_PACK = -2146893047
SEC_E_QOP_NOT_SUPPORTED = -2146893046
SEC_E_NO_IMPERSONATION = -2146893045
SEC_E_LOGON_DENIED = -2146893044
SEC_E_UNKNOWN_CREDENTIALS = -2146893043
SEC_E_NO_CREDENTIALS = -2146893042
SEC_E_MESSAGE_ALTERED = -2146893041
SEC_E_OUT_OF_SEQUENCE = -2146893040
SEC_E_NO_AUTHENTICATING_AUTHORITY = -2146893039
SEC_I_CONTINUE_NEEDED = 590610
SEC_I_COMPLETE_NEEDED = 590611
SEC_I_COMPLETE_AND_CONTINUE = 590612
SEC_I_LOCAL_LOGON = 590613
SEC_E_BAD_PKGID = -2146893034
SEC_E_CONTEXT_EXPIRED = -2146893033
SEC_I_CONTEXT_EXPIRED = 590615
SEC_E_INCOMPLETE_MESSAGE = -2146893032
SEC_E_INCOMPLETE_CREDENTIALS = -2146893024
SEC_E_BUFFER_TOO_SMALL = -2146893023
SEC_I_INCOMPLETE_CREDENTIALS = 590624
SEC_I_RENEGOTIATE = 590625
SEC_E_WRONG_PRINCIPAL = -2146893022
SEC_I_NO_LSA_CONTEXT = 590627
SEC_E_TIME_SKEW = -2146893020
SEC_E_UNTRUSTED_ROOT = -2146893019
SEC_E_ILLEGAL_MESSAGE = -2146893018
SEC_E_CERT_UNKNOWN = -2146893017
SEC_E_CERT_EXPIRED = -2146893016
SEC_E_ENCRYPT_FAILURE = -2146893015
SEC_E_DECRYPT_FAILURE = -2146893008
SEC_E_ALGORITHM_MISMATCH = -2146893007
SEC_E_SECURITY_QOS_FAILED = -2146893006
SEC_E_UNFINISHED_CONTEXT_DELETED = -2146893005
SEC_E_NO_TGT_REPLY = -2146893004
SEC_E_NO_IP_ADDRESSES = -2146893003
SEC_E_WRONG_CREDENTIAL_HANDLE = -2146893002
SEC_E_CRYPTO_SYSTEM_INVALID = -2146893001
SEC_E_MAX_REFERRALS_EXCEEDED = -2146893000
SEC_E_MUST_BE_KDC = -2146892999
SEC_E_STRONG_CRYPTO_NOT_SUPPORTED = -2146892998
SEC_E_TOO_MANY_PRINCIPALS = -2146892997
SEC_E_NO_PA_DATA = -2146892996
SEC_E_PKINIT_NAME_MISMATCH = -2146892995
SEC_E_SMARTCARD_LOGON_REQUIRED = -2146892994
SEC_E_SHUTDOWN_IN_PROGRESS = -2146892993
SEC_E_KDC_INVALID_REQUEST = -2146892992
SEC_E_KDC_UNABLE_TO_REFER = -2146892991
SEC_E_KDC_UNKNOWN_ETYPE = -2146892990
SEC_E_UNSUPPORTED_PREAUTH = -2146892989
SEC_E_DELEGATION_REQUIRED = -2146892987
SEC_E_BAD_BINDINGS = -2146892986
SEC_E_MULTIPLE_ACCOUNTS = -2146892985
SEC_E_NO_KERB_KEY = -2146892984

ERROR_IPSEC_QM_POLICY_EXISTS = 13000
ERROR_IPSEC_QM_POLICY_NOT_FOUND = 13001
ERROR_IPSEC_QM_POLICY_IN_USE = 13002
ERROR_IPSEC_MM_POLICY_EXISTS = 13003
ERROR_IPSEC_MM_POLICY_NOT_FOUND = 13004
ERROR_IPSEC_MM_POLICY_IN_USE = 13005
ERROR_IPSEC_MM_FILTER_EXISTS = 13006
ERROR_IPSEC_MM_FILTER_NOT_FOUND = 13007
ERROR_IPSEC_TRANSPORT_FILTER_EXISTS = 13008
ERROR_IPSEC_TRANSPORT_FILTER_NOT_FOUND = 13009
ERROR_IPSEC_MM_AUTH_EXISTS = 13010
ERROR_IPSEC_MM_AUTH_NOT_FOUND = 13011
ERROR_IPSEC_MM_AUTH_IN_USE = 13012
ERROR_IPSEC_DEFAULT_MM_POLICY_NOT_FOUND = 13013
ERROR_IPSEC_DEFAULT_MM_AUTH_NOT_FOUND = 13014
ERROR_IPSEC_DEFAULT_QM_POLICY_NOT_FOUND = 13015
ERROR_IPSEC_TUNNEL_FILTER_EXISTS = 13016
ERROR_IPSEC_TUNNEL_FILTER_NOT_FOUND = 13017
ERROR_IPSEC_MM_FILTER_PENDING_DELETION = 13018
ERROR_IPSEC_TRANSPORT_FILTER_PENDING_DELETION = 13019
ERROR_IPSEC_TUNNEL_FILTER_PENDING_DELETION = 13020
ERROR_IPSEC_MM_POLICY_PENDING_DELETION = 13021
ERROR_IPSEC_MM_AUTH_PENDING_DELETION = 13022
ERROR_IPSEC_QM_POLICY_PENDING_DELETION = 13023
WARNING_IPSEC_MM_POLICY_PRUNED = 13024
WARNING_IPSEC_QM_POLICY_PRUNED = 13025
ERROR_IPSEC_IKE_NEG_STATUS_BEGIN = 13800
ERROR_IPSEC_IKE_AUTH_FAIL = 13801
ERROR_IPSEC_IKE_ATTRIB_FAIL = 13802
ERROR_IPSEC_IKE_NEGOTIATION_PENDING = 13803
ERROR_IPSEC_IKE_GENERAL_PROCESSING_ERROR = 13804
ERROR_IPSEC_IKE_TIMED_OUT = 13805
ERROR_IPSEC_IKE_NO_CERT = 13806
ERROR_IPSEC_IKE_SA_DELETED = 13807
ERROR_IPSEC_IKE_SA_REAPED = 13808
ERROR_IPSEC_IKE_MM_ACQUIRE_DROP = 13809
ERROR_IPSEC_IKE_QM_ACQUIRE_DROP = 13810
ERROR_IPSEC_IKE_QUEUE_DROP_MM = 13811
ERROR_IPSEC_IKE_QUEUE_DROP_NO_MM = 13812
ERROR_IPSEC_IKE_DROP_NO_RESPONSE = 13813
ERROR_IPSEC_IKE_MM_DELAY_DROP = 13814
ERROR_IPSEC_IKE_QM_DELAY_DROP = 13815
ERROR_IPSEC_IKE_ERROR = 13816
ERROR_IPSEC_IKE_CRL_FAILED = 13817
ERROR_IPSEC_IKE_INVALID_KEY_USAGE = 13818
ERROR_IPSEC_IKE_INVALID_CERT_TYPE = 13819
ERROR_IPSEC_IKE_NO_PRIVATE_KEY = 13820
ERROR_IPSEC_IKE_DH_FAIL = 13822
ERROR_IPSEC_IKE_INVALID_HEADER = 13824
ERROR_IPSEC_IKE_NO_POLICY = 13825
ERROR_IPSEC_IKE_INVALID_SIGNATURE = 13826
ERROR_IPSEC_IKE_KERBEROS_ERROR = 13827
ERROR_IPSEC_IKE_NO_PUBLIC_KEY = 13828
ERROR_IPSEC_IKE_PROCESS_ERR = 13829
ERROR_IPSEC_IKE_PROCESS_ERR_SA = 13830
ERROR_IPSEC_IKE_PROCESS_ERR_PROP = 13831
ERROR_IPSEC_IKE_PROCESS_ERR_TRANS = 13832
ERROR_IPSEC_IKE_PROCESS_ERR_KE = 13833
ERROR_IPSEC_IKE_PROCESS_ERR_ID = 13834
ERROR_IPSEC_IKE_PROCESS_ERR_CERT = 13835
ERROR_IPSEC_IKE_PROCESS_ERR_CERT_REQ = 13836
ERROR_IPSEC_IKE_PROCESS_ERR_HASH = 13837
ERROR_IPSEC_IKE_PROCESS_ERR_SIG = 13838
ERROR_IPSEC_IKE_PROCESS_ERR_NONCE = 13839
ERROR_IPSEC_IKE_PROCESS_ERR_NOTIFY = 13840
ERROR_IPSEC_IKE_PROCESS_ERR_DELETE = 13841
ERROR_IPSEC_IKE_PROCESS_ERR_VENDOR = 13842
ERROR_IPSEC_IKE_INVALID_PAYLOAD = 13843
ERROR_IPSEC_IKE_LOAD_SOFT_SA = 13844
ERROR_IPSEC_IKE_SOFT_SA_TORN_DOWN = 13845
ERROR_IPSEC_IKE_INVALID_COOKIE = 13846
ERROR_IPSEC_IKE_NO_PEER_CERT = 13847
ERROR_IPSEC_IKE_PEER_CRL_FAILED = 13848
ERROR_IPSEC_IKE_POLICY_CHANGE = 13849
ERROR_IPSEC_IKE_NO_MM_POLICY = 13850
ERROR_IPSEC_IKE_NOTCBPRIV = 13851
ERROR_IPSEC_IKE_SECLOADFAIL = 13852
ERROR_IPSEC_IKE_FAILSSPINIT = 13853
ERROR_IPSEC_IKE_FAILQUERYSSP = 13854
ERROR_IPSEC_IKE_SRVACQFAIL = 13855
ERROR_IPSEC_IKE_SRVQUERYCRED = 13856
ERROR_IPSEC_IKE_GETSPIFAIL = 13857
ERROR_IPSEC_IKE_INVALID_FILTER = 13858
ERROR_IPSEC_IKE_OUT_OF_MEMORY = 13859
ERROR_IPSEC_IKE_ADD_UPDATE_KEY_FAILED = 13860
ERROR_IPSEC_IKE_INVALID_POLICY = 13861
ERROR_IPSEC_IKE_UNKNOWN_DOI = 13862
ERROR_IPSEC_IKE_INVALID_SITUATION = 13863
ERROR_IPSEC_IKE_DH_FAILURE = 13864
ERROR_IPSEC_IKE_INVALID_GROUP = 13865
ERROR_IPSEC_IKE_ENCRYPT = 13866
ERROR_IPSEC_IKE_DECRYPT = 13867
ERROR_IPSEC_IKE_POLICY_MATCH = 13868
ERROR_IPSEC_IKE_UNSUPPORTED_ID = 13869
ERROR_IPSEC_IKE_INVALID_HASH = 13870
ERROR_IPSEC_IKE_INVALID_HASH_ALG = 13871
ERROR_IPSEC_IKE_INVALID_HASH_SIZE = 13872
ERROR_IPSEC_IKE_INVALID_ENCRYPT_ALG = 13873
ERROR_IPSEC_IKE_INVALID_AUTH_ALG = 13874
ERROR_IPSEC_IKE_INVALID_SIG = 13875
ERROR_IPSEC_IKE_LOAD_FAILED = 13876
ERROR_IPSEC_IKE_RPC_DELETE = 13877
ERROR_IPSEC_IKE_BENIGN_REINIT = 13878
ERROR_IPSEC_IKE_INVALID_RESPONDER_LIFETIME_NOTIFY = 13879
ERROR_IPSEC_IKE_INVALID_CERT_KEYLEN = 13881
ERROR_IPSEC_IKE_MM_LIMIT = 13882
ERROR_IPSEC_IKE_NEGOTIATION_DISABLED = 13883
ERROR_IPSEC_IKE_NEG_STATUS_END = 13884
CRYPT_E_MSG_ERROR = -2146889727
CRYPT_E_UNKNOWN_ALGO = -2146889726
CRYPT_E_OID_FORMAT = -2146889725
CRYPT_E_INVALID_MSG_TYPE = -2146889724
CRYPT_E_UNEXPECTED_ENCODING = -2146889723
CRYPT_E_AUTH_ATTR_MISSING = -2146889722
CRYPT_E_HASH_VALUE = -2146889721
CRYPT_E_INVALID_INDEX = -2146889720
CRYPT_E_ALREADY_DECRYPTED = -2146889719
CRYPT_E_NOT_DECRYPTED = -2146889718
CRYPT_E_RECIPIENT_NOT_FOUND = -2146889717
CRYPT_E_CONTROL_TYPE = -2146889716
CRYPT_E_ISSUER_SERIALNUMBER = -2146889715
CRYPT_E_SIGNER_NOT_FOUND = -2146889714
CRYPT_E_ATTRIBUTES_MISSING = -2146889713
CRYPT_E_STREAM_MSG_NOT_READY = -2146889712
CRYPT_E_STREAM_INSUFFICIENT_DATA = -2146889711
CRYPT_I_NEW_PROTECTION_REQUIRED = 593938
CRYPT_E_BAD_LEN = -2146885631
CRYPT_E_BAD_ENCODE = -2146885630
CRYPT_E_FILE_ERROR = -2146885629
CRYPT_E_NOT_FOUND = -2146885628
CRYPT_E_EXISTS = -2146885627
CRYPT_E_NO_PROVIDER = -2146885626
CRYPT_E_SELF_SIGNED = -2146885625
CRYPT_E_DELETED_PREV = -2146885624
CRYPT_E_NO_MATCH = -2146885623
CRYPT_E_UNEXPECTED_MSG_TYPE = -2146885622
CRYPT_E_NO_KEY_PROPERTY = -2146885621
CRYPT_E_NO_DECRYPT_CERT = -2146885620
CRYPT_E_BAD_MSG = -2146885619
CRYPT_E_NO_SIGNER = -2146885618
CRYPT_E_PENDING_CLOSE = -2146885617
CRYPT_E_REVOKED = -2146885616
CRYPT_E_NO_REVOCATION_DLL = -2146885615
CRYPT_E_NO_REVOCATION_CHECK = -2146885614
CRYPT_E_REVOCATION_OFFLINE = -2146885613
CRYPT_E_NOT_IN_REVOCATION_DATABASE = -2146885612
CRYPT_E_INVALID_NUMERIC_STRING = -2146885600
CRYPT_E_INVALID_PRINTABLE_STRING = -2146885599
CRYPT_E_INVALID_IA5_STRING = -2146885598
CRYPT_E_INVALID_X500_STRING = -2146885597
CRYPT_E_NOT_CHAR_STRING = -2146885596
CRYPT_E_FILERESIZED = -2146885595
CRYPT_E_SECURITY_SETTINGS = -2146885594
CRYPT_E_NO_VERIFY_USAGE_DLL = -2146885593
CRYPT_E_NO_VERIFY_USAGE_CHECK = -2146885592
CRYPT_E_VERIFY_USAGE_OFFLINE = -2146885591
CRYPT_E_NOT_IN_CTL = -2146885590
CRYPT_E_NO_TRUSTED_SIGNER = -2146885589
CRYPT_E_MISSING_PUBKEY_PARA = -2146885588
CRYPT_E_OSS_ERROR = -2146881536

## Kerberos message types for LsaCallAuthenticationPackage (from ntsecapi.h)
KerbDebugRequestMessage = 0
KerbQueryTicketCacheMessage = 1
KerbChangeMachinePasswordMessage = 2
KerbVerifyPacMessage = 3
KerbRetrieveTicketMessage = 4
KerbUpdateAddressesMessage = 5
KerbPurgeTicketCacheMessage = 6
KerbChangePasswordMessage = 7
KerbRetrieveEncodedTicketMessage = 8
KerbDecryptDataMessage = 9
KerbAddBindingCacheEntryMessage = 10
KerbSetPasswordMessage = 11
KerbSetPasswordExMessage = 12
KerbVerifyCredentialsMessage = 13
KerbQueryTicketCacheExMessage = 14
KerbPurgeTicketCacheExMessage = 15
KerbRefreshSmartcardCredentialsMessage = 16
KerbAddExtraCredentialsMessage = 17
KerbQuerySupplementalCredentialsMessage = 18

## messages used with msv1_0 from ntsecapi.h
MsV1_0Lm20ChallengeRequest = 0
MsV1_0Lm20GetChallengeResponse = 1
MsV1_0EnumerateUsers = 2
MsV1_0GetUserInfo = 3
MsV1_0ReLogonUsers = 4
MsV1_0ChangePassword = 5
MsV1_0ChangeCachedPassword = 6
MsV1_0GenericPassthrough = 7
MsV1_0CacheLogon = 8
MsV1_0SubAuth = 9
MsV1_0DeriveCredential = 10
MsV1_0CacheLookup = 11
MsV1_0SetProcessOption = 12

SEC_E_OK = 0

# === NexusCore/openenv\Lib\site-packages\numpy\lib\tests\test_type_check.py ===
import numpy as np
from numpy import (
    common_type,
    iscomplex,
    iscomplexobj,
    isneginf,
    isposinf,
    isreal,
    isrealobj,
    mintypecode,
    nan_to_num,
    real_if_close,
)
from numpy.testing import assert_, assert_array_equal, assert_equal


def assert_all(x):
    assert_(np.all(x), x)


class TestCommonType:
    def test_basic(self):
        ai32 = np.array([[1, 2], [3, 4]], dtype=np.int32)
        af16 = np.array([[1, 2], [3, 4]], dtype=np.float16)
        af32 = np.array([[1, 2], [3, 4]], dtype=np.float32)
        af64 = np.array([[1, 2], [3, 4]], dtype=np.float64)
        acs = np.array([[1 + 5j, 2 + 6j], [3 + 7j, 4 + 8j]], dtype=np.complex64)
        acd = np.array([[1 + 5j, 2 + 6j], [3 + 7j, 4 + 8j]], dtype=np.complex128)
        assert_(common_type(ai32) == np.float64)
        assert_(common_type(af16) == np.float16)
        assert_(common_type(af32) == np.float32)
        assert_(common_type(af64) == np.float64)
        assert_(common_type(acs) == np.complex64)
        assert_(common_type(acd) == np.complex128)


class TestMintypecode:

    def test_default_1(self):
        for itype in '1bcsuwil':
            assert_equal(mintypecode(itype), 'd')
        assert_equal(mintypecode('f'), 'f')
        assert_equal(mintypecode('d'), 'd')
        assert_equal(mintypecode('F'), 'F')
        assert_equal(mintypecode('D'), 'D')

    def test_default_2(self):
        for itype in '1bcsuwil':
            assert_equal(mintypecode(itype + 'f'), 'f')
            assert_equal(mintypecode(itype + 'd'), 'd')
            assert_equal(mintypecode(itype + 'F'), 'F')
            assert_equal(mintypecode(itype + 'D'), 'D')
        assert_equal(mintypecode('ff'), 'f')
        assert_equal(mintypecode('fd'), 'd')
        assert_equal(mintypecode('fF'), 'F')
        assert_equal(mintypecode('fD'), 'D')
        assert_equal(mintypecode('df'), 'd')
        assert_equal(mintypecode('dd'), 'd')
        #assert_equal(mintypecode('dF',savespace=1),'F')
        assert_equal(mintypecode('dF'), 'D')
        assert_equal(mintypecode('dD'), 'D')
        assert_equal(mintypecode('Ff'), 'F')
        #assert_equal(mintypecode('Fd',savespace=1),'F')
        assert_equal(mintypecode('Fd'), 'D')
        assert_equal(mintypecode('FF'), 'F')
        assert_equal(mintypecode('FD'), 'D')
        assert_equal(mintypecode('Df'), 'D')
        assert_equal(mintypecode('Dd'), 'D')
        assert_equal(mintypecode('DF'), 'D')
        assert_equal(mintypecode('DD'), 'D')

    def test_default_3(self):
        assert_equal(mintypecode('fdF'), 'D')
        #assert_equal(mintypecode('fdF',savespace=1),'F')
        assert_equal(mintypecode('fdD'), 'D')
        assert_equal(mintypecode('fFD'), 'D')
        assert_equal(mintypecode('dFD'), 'D')

        assert_equal(mintypecode('ifd'), 'd')
        assert_equal(mintypecode('ifF'), 'F')
        assert_equal(mintypecode('ifD'), 'D')
        assert_equal(mintypecode('idF'), 'D')
        #assert_equal(mintypecode('idF',savespace=1),'F')
        assert_equal(mintypecode('idD'), 'D')


class TestIsscalar:

    def test_basic(self):
        assert_(np.isscalar(3))
        assert_(not np.isscalar([3]))
        assert_(not np.isscalar((3,)))
        assert_(np.isscalar(3j))
        assert_(np.isscalar(4.0))


class TestReal:

    def test_real(self):
        y = np.random.rand(10,)
        assert_array_equal(y, np.real(y))

        y = np.array(1)
        out = np.real(y)
        assert_array_equal(y, out)
        assert_(isinstance(out, np.ndarray))

        y = 1
        out = np.real(y)
        assert_equal(y, out)
        assert_(not isinstance(out, np.ndarray))

    def test_cmplx(self):
        y = np.random.rand(10,) + 1j * np.random.rand(10,)
        assert_array_equal(y.real, np.real(y))

        y = np.array(1 + 1j)
        out = np.real(y)
        assert_array_equal(y.real, out)
        assert_(isinstance(out, np.ndarray))

        y = 1 + 1j
        out = np.real(y)
        assert_equal(1.0, out)
        assert_(not isinstance(out, np.ndarray))


class TestImag:

    def test_real(self):
        y = np.random.rand(10,)
        assert_array_equal(0, np.imag(y))

        y = np.array(1)
        out = np.imag(y)
        assert_array_equal(0, out)
        assert_(isinstance(out, np.ndarray))

        y = 1
        out = np.imag(y)
        assert_equal(0, out)
        assert_(not isinstance(out, np.ndarray))

    def test_cmplx(self):
        y = np.random.rand(10,) + 1j * np.random.rand(10,)
        assert_array_equal(y.imag, np.imag(y))

        y = np.array(1 + 1j)
        out = np.imag(y)
        assert_array_equal(y.imag, out)
        assert_(isinstance(out, np.ndarray))

        y = 1 + 1j
        out = np.imag(y)
        assert_equal(1.0, out)
        assert_(not isinstance(out, np.ndarray))


class TestIscomplex:

    def test_fail(self):
        z = np.array([-1, 0, 1])
        res = iscomplex(z)
        assert_(not np.any(res, axis=0))

    def test_pass(self):
        z = np.array([-1j, 1, 0])
        res = iscomplex(z)
        assert_array_equal(res, [1, 0, 0])


class TestIsreal:

    def test_pass(self):
        z = np.array([-1, 0, 1j])
        res = isreal(z)
        assert_array_equal(res, [1, 1, 0])

    def test_fail(self):
        z = np.array([-1j, 1, 0])
        res = isreal(z)
        assert_array_equal(res, [0, 1, 1])


class TestIscomplexobj:

    def test_basic(self):
        z = np.array([-1, 0, 1])
        assert_(not iscomplexobj(z))
        z = np.array([-1j, 0, -1])
        assert_(iscomplexobj(z))

    def test_scalar(self):
        assert_(not iscomplexobj(1.0))
        assert_(iscomplexobj(1 + 0j))

    def test_list(self):
        assert_(iscomplexobj([3, 1 + 0j, True]))
        assert_(not iscomplexobj([3, 1, True]))

    def test_duck(self):
        class DummyComplexArray:
            @property
            def dtype(self):
                return np.dtype(complex)
        dummy = DummyComplexArray()
        assert_(iscomplexobj(dummy))

    def test_pandas_duck(self):
        # This tests a custom np.dtype duck-typed class, such as used by pandas
        # (pandas.core.dtypes)
        class PdComplex(np.complex128):
            pass

        class PdDtype:
            name = 'category'
            names = None
            type = PdComplex
            kind = 'c'
            str = '<c16'
            base = np.dtype('complex128')

        class DummyPd:
            @property
            def dtype(self):
                return PdDtype
        dummy = DummyPd()
        assert_(iscomplexobj(dummy))

    def test_custom_dtype_duck(self):
        class MyArray(list):
            @property
            def dtype(self):
                return complex

        a = MyArray([1 + 0j, 2 + 0j, 3 + 0j])
        assert_(iscomplexobj(a))


class TestIsrealobj:
    def test_basic(self):
        z = np.array([-1, 0, 1])
        assert_(isrealobj(z))
        z = np.array([-1j, 0, -1])
        assert_(not isrealobj(z))


class TestIsnan:

    def test_goodvalues(self):
        z = np.array((-1., 0., 1.))
        res = np.isnan(z) == 0
        assert_all(np.all(res, axis=0))

    def test_posinf(self):
        with np.errstate(divide='ignore'):
            assert_all(np.isnan(np.array((1.,)) / 0.) == 0)

    def test_neginf(self):
        with np.errstate(divide='ignore'):
            assert_all(np.isnan(np.array((-1.,)) / 0.) == 0)

    def test_ind(self):
        with np.errstate(divide='ignore', invalid='ignore'):
            assert_all(np.isnan(np.array((0.,)) / 0.) == 1)

    def test_integer(self):
        assert_all(np.isnan(1) == 0)

    def test_complex(self):
        assert_all(np.isnan(1 + 1j) == 0)

    def test_complex1(self):
        with np.errstate(divide='ignore', invalid='ignore'):
            assert_all(np.isnan(np.array(0 + 0j) / 0.) == 1)


class TestIsfinite:
    # Fixme, wrong place, isfinite now ufunc

    def test_goodvalues(self):
        z = np.array((-1., 0., 1.))
        res = np.isfinite(z) == 1
        assert_all(np.all(res, axis=0))

    def test_posinf(self):
        with np.errstate(divide='ignore', invalid='ignore'):
            assert_all(np.isfinite(np.array((1.,)) / 0.) == 0)

    def test_neginf(self):
        with np.errstate(divide='ignore', invalid='ignore'):
            assert_all(np.isfinite(np.array((-1.,)) / 0.) == 0)

    def test_ind(self):
        with np.errstate(divide='ignore', invalid='ignore'):
            assert_all(np.isfinite(np.array((0.,)) / 0.) == 0)

    def test_integer(self):
        assert_all(np.isfinite(1) == 1)

    def test_complex(self):
        assert_all(np.isfinite(1 + 1j) == 1)

    def test_complex1(self):
        with np.errstate(divide='ignore', invalid='ignore'):
            assert_all(np.isfinite(np.array(1 + 1j) / 0.) == 0)


class TestIsinf:
    # Fixme, wrong place, isinf now ufunc

    def test_goodvalues(self):
        z = np.array((-1., 0., 1.))
        res = np.isinf(z) == 0
        assert_all(np.all(res, axis=0))

    def test_posinf(self):
        with np.errstate(divide='ignore', invalid='ignore'):
            assert_all(np.isinf(np.array((1.,)) / 0.) == 1)

    def test_posinf_scalar(self):
        with np.errstate(divide='ignore', invalid='ignore'):
            assert_all(np.isinf(np.array(1.,) / 0.) == 1)

    def test_neginf(self):
        with np.errstate(divide='ignore', invalid='ignore'):
            assert_all(np.isinf(np.array((-1.,)) / 0.) == 1)

    def test_neginf_scalar(self):
        with np.errstate(divide='ignore', invalid='ignore'):
            assert_all(np.isinf(np.array(-1.) / 0.) == 1)

    def test_ind(self):
        with np.errstate(divide='ignore', invalid='ignore'):
            assert_all(np.isinf(np.array((0.,)) / 0.) == 0)


class TestIsposinf:

    def test_generic(self):
        with np.errstate(divide='ignore', invalid='ignore'):
            vals = isposinf(np.array((-1., 0, 1)) / 0.)
        assert_(vals[0] == 0)
        assert_(vals[1] == 0)
        assert_(vals[2] == 1)


class TestIsneginf:

    def test_generic(self):
        with np.errstate(divide='ignore', invalid='ignore'):
            vals = isneginf(np.array((-1., 0, 1)) / 0.)
        assert_(vals[0] == 1)
        assert_(vals[1] == 0)
        assert_(vals[2] == 0)


class TestNanToNum:

    def test_generic(self):
        with np.errstate(divide='ignore', invalid='ignore'):
            vals = nan_to_num(np.array((-1., 0, 1)) / 0.)
        assert_all(vals[0] < -1e10) and assert_all(np.isfinite(vals[0]))
        assert_(vals[1] == 0)
        assert_all(vals[2] > 1e10) and assert_all(np.isfinite(vals[2]))
        assert_equal(type(vals), np.ndarray)

        # perform the same tests but with nan, posinf and neginf keywords
        with np.errstate(divide='ignore', invalid='ignore'):
            vals = nan_to_num(np.array((-1., 0, 1)) / 0.,
                              nan=10, posinf=20, neginf=30)
        assert_equal(vals, [30, 10, 20])
        assert_all(np.isfinite(vals[[0, 2]]))
        assert_equal(type(vals), np.ndarray)

        # perform the same test but in-place
        with np.errstate(divide='ignore', invalid='ignore'):
            vals = np.array((-1., 0, 1)) / 0.
        result = nan_to_num(vals, copy=False)

        assert_(result is vals)
        assert_all(vals[0] < -1e10) and assert_all(np.isfinite(vals[0]))
        assert_(vals[1] == 0)
        assert_all(vals[2] > 1e10) and assert_all(np.isfinite(vals[2]))
        assert_equal(type(vals), np.ndarray)

        # perform the same test but in-place
        with np.errstate(divide='ignore', invalid='ignore'):
            vals = np.array((-1., 0, 1)) / 0.
        result = nan_to_num(vals, copy=False, nan=10, posinf=20, neginf=30)

        assert_(result is vals)
        assert_equal(vals, [30, 10, 20])
        assert_all(np.isfinite(vals[[0, 2]]))
        assert_equal(type(vals), np.ndarray)

    def test_array(self):
        vals = nan_to_num([1])
        assert_array_equal(vals, np.array([1], int))
        assert_equal(type(vals), np.ndarray)
        vals = nan_to_num([1], nan=10, posinf=20, neginf=30)
        assert_array_equal(vals, np.array([1], int))
        assert_equal(type(vals), np.ndarray)

    def test_integer(self):
        vals = nan_to_num(1)
        assert_all(vals == 1)
        assert_equal(type(vals), np.int_)
        vals = nan_to_num(1, nan=10, posinf=20, neginf=30)
        assert_all(vals == 1)
        assert_equal(type(vals), np.int_)

    def test_float(self):
        vals = nan_to_num(1.0)
        assert_all(vals == 1.0)
        assert_equal(type(vals), np.float64)
        vals = nan_to_num(1.1, nan=10, posinf=20, neginf=30)
        assert_all(vals == 1.1)
        assert_equal(type(vals), np.float64)

    def test_complex_good(self):
        vals = nan_to_num(1 + 1j)
        assert_all(vals == 1 + 1j)
        assert_equal(type(vals), np.complex128)
        vals = nan_to_num(1 + 1j, nan=10, posinf=20, neginf=30)
        assert_all(vals == 1 + 1j)
        assert_equal(type(vals), np.complex128)

    def test_complex_bad(self):
        with np.errstate(divide='ignore', invalid='ignore'):
            v = 1 + 1j
            v += np.array(0 + 1.j) / 0.
        vals = nan_to_num(v)
        # !! This is actually (unexpectedly) zero
        assert_all(np.isfinite(vals))
        assert_equal(type(vals), np.complex128)

    def test_complex_bad2(self):
        with np.errstate(divide='ignore', invalid='ignore'):
            v = 1 + 1j
            v += np.array(-1 + 1.j) / 0.
        vals = nan_to_num(v)
        assert_all(np.isfinite(vals))
        assert_equal(type(vals), np.complex128)
        # Fixme
        #assert_all(vals.imag > 1e10)  and assert_all(np.isfinite(vals))
        # !! This is actually (unexpectedly) positive
        # !! inf.  Comment out for now, and see if it
        # !! changes
        #assert_all(vals.real < -1e10) and assert_all(np.isfinite(vals))

    def test_do_not_rewrite_previous_keyword(self):
        # This is done to test that when, for instance, nan=np.inf then these
        # values are not rewritten by posinf keyword to the posinf value.
        with np.errstate(divide='ignore', invalid='ignore'):
            vals = nan_to_num(np.array((-1., 0, 1)) / 0., nan=np.inf, posinf=999)
        assert_all(np.isfinite(vals[[0, 2]]))
        assert_all(vals[0] < -1e10)
        assert_equal(vals[[1, 2]], [np.inf, 999])
        assert_equal(type(vals), np.ndarray)


class TestRealIfClose:

    def test_basic(self):
        a = np.random.rand(10)
        b = real_if_close(a + 1e-15j)
        assert_all(isrealobj(b))
        assert_array_equal(a, b)
        b = real_if_close(a + 1e-7j)
        assert_all(iscomplexobj(b))
        b = real_if_close(a + 1e-7j, tol=1e-6)
        assert_all(isrealobj(b))

# === NexusCore/openenv\Lib\site-packages\google\generativeai\notebook\lib\llm_function.py ===
# -*- coding: utf-8 -*-
# Copyright 2023 Google LLC
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
"""LLMFunction."""
from __future__ import annotations

import abc
import dataclasses
from typing import (
    AbstractSet,
    Any,
    Callable,
    Iterable,
    Mapping,
    Optional,
    Sequence,
    Union,
)

from google.generativeai.notebook.lib import llmfn_input_utils
from google.generativeai.notebook.lib import llmfn_output_row
from google.generativeai.notebook.lib import llmfn_outputs
from google.generativeai.notebook.lib import llmfn_post_process
from google.generativeai.notebook.lib import llmfn_post_process_cmds
from google.generativeai.notebook.lib import model as model_lib
from google.generativeai.notebook.lib import prompt_utils


# In the same spirit as post-processing functions (see: llmfn_post_process.py),
# we keep the LLM functions more flexible by providing the entire left- and
# right-hand side rows to the user-defined comparison function.
#
# Possible use-cases include adding a scoring function as a post-process
# command, then comparing the scores.
CompareFn = Callable[
    [llmfn_output_row.LLMFnOutputRowView, llmfn_output_row.LLMFnOutputRowView],
    Any,
]


def _is_equal_fn(
    lhs: llmfn_output_row.LLMFnOutputRowView,
    rhs: llmfn_output_row.LLMFnOutputRowView,
) -> bool:
    """Default function used when comparing outputs."""
    return lhs.result_value() == rhs.result_value()


def _convert_compare_fn_to_batch_add_fn(
    fn: Callable[
        [
            llmfn_output_row.LLMFnOutputRowView,
            llmfn_output_row.LLMFnOutputRowView,
        ],
        Any,
    ]
) -> llmfn_post_process.LLMCompareFnPostProcessBatchAddFn:
    """Vectorize a single-row-based comparison function."""

    def _fn(
        lhs_and_rhs_rows: Sequence[
            tuple[
                llmfn_output_row.LLMFnOutputRowView,
                llmfn_output_row.LLMFnOutputRowView,
            ]
        ]
    ) -> Sequence[Any]:
        return [fn(lhs, rhs) for lhs, rhs in lhs_and_rhs_rows]

    return _fn


@dataclasses.dataclass
class _PromptInfo:
    prompt_num: int
    prompt: str
    input_num: int
    prompt_vars: Mapping[str, str]
    model_input: str


def _generate_prompts(
    prompts: Sequence[str], inputs: llmfn_input_utils.LLMFunctionInputs | None
) -> Iterable[_PromptInfo]:
    """Generate a tuple of fields needed for processing prompts.

    Args:
      prompts: A list of prompts, with optional keyword placeholders.
      inputs: A list of key/value pairs to substitute into placeholders in
        `prompts`.

    Yields:
      A _PromptInfo instance.
    """
    normalized_inputs: Sequence[Mapping[str, str]] = []
    if inputs is not None:
        normalized_inputs = llmfn_input_utils.to_normalized_inputs(inputs)

    # Must have at least one entry so that we execute the prompt at least once.
    if not normalized_inputs:
        normalized_inputs = [{}]

    for prompt_num, prompt in enumerate(prompts):
        for input_num, prompt_vars in enumerate(normalized_inputs):
            # Perform keyword substitution on the prompt based on `prompt_vars`.
            model_input = prompt.format(**prompt_vars)
            yield _PromptInfo(
                prompt_num=prompt_num,
                prompt=prompt,
                input_num=input_num,
                prompt_vars=prompt_vars,
                model_input=model_input,
            )


class LLMFunction(
    Callable[
        [Union[llmfn_input_utils.LLMFunctionInputs, None]],
        llmfn_outputs.LLMFnOutputs,
    ],
    metaclass=abc.ABCMeta,
):
    """Base class for LLMFunctionImpl and LLMCompareFunction."""

    def __init__(
        self,
        outputs_ipython_display_fn: Callable[[llmfn_outputs.LLMFnOutputs], None] | None = None,
    ):
        """Constructor.

        Args:
          outputs_ipython_display_fn: Optional function that will be used to
            override how the outputs of this LLMFunction will be displayed in a
            notebook (See further documentation in LLMFnOutputs.__init__().)
        """
        self._post_process_cmds: list[llmfn_post_process_cmds.LLMFnPostProcessCommand] = []
        self._outputs_ipython_display_fn = outputs_ipython_display_fn

    @abc.abstractmethod
    def get_placeholders(self) -> AbstractSet[str]:
        """Returns the placeholders that should be present in inputs for this function."""

    @abc.abstractmethod
    def _call_impl(
        self, inputs: llmfn_input_utils.LLMFunctionInputs | None
    ) -> Sequence[llmfn_outputs.LLMFnOutputEntry]:
        """Concrete implementation of __call__()."""

    def __call__(
        self, inputs: llmfn_input_utils.LLMFunctionInputs | None = None
    ) -> llmfn_outputs.LLMFnOutputs:
        """Runs and returns results based on `inputs`."""
        outputs = self._call_impl(inputs)

        return llmfn_outputs.LLMFnOutputs(
            outputs=outputs, ipython_display_fn=self._outputs_ipython_display_fn
        )

    def add_post_process_reorder_fn(
        self, name: str, fn: llmfn_post_process.LLMFnPostProcessBatchReorderFn
    ) -> LLMFunction:
        self._post_process_cmds.append(
            llmfn_post_process_cmds.LLMFnPostProcessReorderCommand(name=name, fn=fn)
        )
        return self

    def add_post_process_add_fn(
        self,
        name: str,
        fn: llmfn_post_process.LLMFnPostProcessBatchAddFn,
    ) -> LLMFunction:
        self._post_process_cmds.append(
            llmfn_post_process_cmds.LLMFnPostProcessAddCommand(name=name, fn=fn)
        )
        return self

    def add_post_process_replace_fn(
        self,
        name: str,
        fn: llmfn_post_process.LLMFnPostProcessBatchReplaceFn,
    ) -> LLMFunction:
        self._post_process_cmds.append(
            llmfn_post_process_cmds.LLMFnPostProcessReplaceCommand(name=name, fn=fn)
        )
        return self


class LLMFunctionImpl(LLMFunction):
    """Callable class that executes the contents of a Magics cell.

    An LLMFunction is constructed from the Magics command line and cell contents
    specified by the user. It is defined by:
    - A model instance,
    - Model arguments
    - A prompt template (e.g. "the opposite of hot is {word}") with an optional
      keyword placeholder.

    The LLMFunction takes as its input a sequence of dictionaries containing
    values for keyword replacement, e.g. [{"word": "hot"}, {"word": "tall"}].

    This will cause the model to be executed with the following prompts:
      "The opposite of hot is"
      "The opposite of tall is"

    The results will be returned in a LLMFnOutputs instance.
    """

    def __init__(
        self,
        model: model_lib.AbstractModel,
        prompts: Sequence[str],
        model_args: model_lib.ModelArguments | None = None,
        outputs_ipython_display_fn: Callable[[llmfn_outputs.LLMFnOutputs], None] | None = None,
    ):
        """Constructor.

        Args:
          model: The model that the prompts will execute on.
          prompts: A sequence of prompt templates with optional placeholders. The
            placeholders will be replaced by the inputs passed into this function.
          model_args: Optional set of model arguments to configure how the model
            executes the prompts.
          outputs_ipython_display_fn: See documentation in LLMFunction.__init__().
        """
        super().__init__(outputs_ipython_display_fn=outputs_ipython_display_fn)
        self._model = model
        self._prompts = prompts
        self._model_args = model_lib.ModelArguments() if model_args is None else model_args

        # Compute placeholders.
        self._placeholders = frozenset({})
        for prompt in self._prompts:
            self._placeholders = self._placeholders.union(prompt_utils.get_placeholders(prompt))

    def _run_post_processing_cmds(
        self, results: Sequence[llmfn_output_row.LLMFnOutputRow]
    ) -> Sequence[llmfn_output_row.LLMFnOutputRow]:
        """Runs post-processing commands over `results`."""
        for cmd in self._post_process_cmds:
            try:
                if isinstance(cmd, llmfn_post_process_cmds.LLMFnImplPostProcessCommand):
                    results = cmd.run(results)
                else:
                    raise llmfn_post_process.PostProcessExecutionError(
                        "Unsupported post-process command type: {}".format(type(cmd))
                    )
            except llmfn_post_process.PostProcessExecutionError:
                raise
            except RuntimeError as e:
                raise llmfn_post_process.PostProcessExecutionError(
                    'Error executing "{}", got {}: {}'.format(cmd.name(), type(e).__name__, e)
                )
        return results

    def get_placeholders(self) -> AbstractSet[str]:
        return self._placeholders

    def _call_impl(
        self, inputs: llmfn_input_utils.LLMFunctionInputs | None
    ) -> Sequence[llmfn_outputs.LLMFnOutputEntry]:
        results: list[llmfn_outputs.LLMFnOutputEntry] = []
        for info in _generate_prompts(prompts=self._prompts, inputs=inputs):
            model_results = self._model.call_model(
                model_input=info.model_input, model_args=self._model_args
            )
            output_rows: list[llmfn_output_row.LLMFnOutputRow] = []
            for result_num, text_result in enumerate(model_results.text_results):
                output_rows.append(
                    llmfn_output_row.LLMFnOutputRow(
                        data={
                            llmfn_outputs.ColumnNames.RESULT_NUM: result_num,
                            llmfn_outputs.ColumnNames.TEXT_RESULT: text_result,
                        },
                        result_type=str,
                    )
                )
            results.append(
                llmfn_outputs.LLMFnOutputEntry(
                    prompt_num=info.prompt_num,
                    input_num=info.input_num,
                    prompt=info.prompt,
                    prompt_vars=info.prompt_vars,
                    model_input=info.model_input,
                    model_results=model_results,
                    output_rows=self._run_post_processing_cmds(output_rows),
                )
            )
        return results


class LLMCompareFunction(LLMFunction):
    """LLMFunction for comparisons.

    LLMCompareFunction runs an input over a pair of LLMFunctions and compares the
    result.
    """

    def __init__(
        self,
        lhs_name_and_fn: tuple[str, LLMFunction],
        rhs_name_and_fn: tuple[str, LLMFunction],
        compare_name_and_fns: Sequence[tuple[str, CompareFn]] | None = None,
        outputs_ipython_display_fn: Callable[[llmfn_outputs.LLMFnOutputs], None] | None = None,
    ):
        """Constructor.

        Args:
          lhs_name_and_fn: Name and function for the left-hand side of the
            comparison.
          rhs_name_and_fn: Name and function for the right-hand side of the
            comparison.
          compare_name_and_fns: Optional names and functions for comparing the
            results of the left- and right-hand sides.
          outputs_ipython_display_fn: See documentation in LLMFunction.__init__().
        """
        super().__init__(outputs_ipython_display_fn=outputs_ipython_display_fn)
        self._lhs_name: str = lhs_name_and_fn[0]
        self._lhs_fn: LLMFunction = lhs_name_and_fn[1]
        self._rhs_name: str = rhs_name_and_fn[0]
        self._rhs_fn: LLMFunction = rhs_name_and_fn[1]
        self._placeholders = frozenset(self._lhs_fn.get_placeholders()).union(
            self._rhs_fn.get_placeholders()
        )

        if not compare_name_and_fns:
            self._result_name = "is_equal"
            self._result_compare_fn = _is_equal_fn
        else:
            # Assume the last entry in `compare_name_and_fns` is the one that
            # produces value for the result cell.
            name, fn = compare_name_and_fns[-1]
            self._result_name = name
            self._result_compare_fn = fn

            # Treat the other compare_fns as post-processing operators.
            for name, cmp_fn in compare_name_and_fns[:-1]:
                self.add_compare_post_process_add_fn(
                    name=name, fn=_convert_compare_fn_to_batch_add_fn(cmp_fn)
                )

    def _run_post_processing_cmds(
        self,
        lhs_output_rows: Sequence[llmfn_output_row.LLMFnOutputRow],
        rhs_output_rows: Sequence[llmfn_output_row.LLMFnOutputRow],
        results: Sequence[llmfn_output_row.LLMFnOutputRow],
    ) -> Sequence[llmfn_output_row.LLMFnOutputRow]:
        """Runs post-processing commands over `results`."""
        for cmd in self._post_process_cmds:
            try:
                if isinstance(cmd, llmfn_post_process_cmds.LLMFnImplPostProcessCommand):
                    results = cmd.run(results)
                elif isinstance(cmd, llmfn_post_process_cmds.LLMCompareFnPostProcessCommand):
                    results = cmd.run(list(zip(lhs_output_rows, rhs_output_rows, results)))
                else:
                    raise RuntimeError(
                        "Unsupported post-process command type: {}".format(type(cmd))
                    )
            except llmfn_post_process.PostProcessExecutionError:
                raise
            except RuntimeError as e:
                raise llmfn_post_process.PostProcessExecutionError(
                    'Error executing "{}", got {}: {}'.format(cmd.name(), type(e).__name__, e)
                )
        return results

    def get_placeholders(self) -> AbstractSet[str]:
        return self._placeholders

    def _call_impl(
        self, inputs: llmfn_input_utils.LLMFunctionInputs | None
    ) -> Sequence[llmfn_outputs.LLMFnOutputEntry]:
        lhs_results = self._lhs_fn(inputs)
        rhs_results = self._rhs_fn(inputs)

        # Combine the results.
        outputs: list[llmfn_outputs.LLMFnOutputEntry] = []
        for lhs_entry, rhs_entry in zip(lhs_results, rhs_results):
            if lhs_entry.prompt_num != rhs_entry.prompt_num:
                raise RuntimeError(
                    "Prompt num mismatch: {} vs {}".format(
                        lhs_entry.prompt_num, rhs_entry.prompt_num
                    )
                )
            if lhs_entry.input_num != rhs_entry.input_num:
                raise RuntimeError(
                    "Input num mismatch: {} vs {}".format(lhs_entry.input_num, rhs_entry.input_num)
                )
            if lhs_entry.prompt_vars != rhs_entry.prompt_vars:
                raise RuntimeError(
                    "Prompt vars mismatch: {} vs {}".format(
                        lhs_entry.prompt_vars, rhs_entry.prompt_vars
                    )
                )

            # The two functions may have different numbers of results due to
            # options like candidate_count, so we can only compare up to the
            # minimum of the two.
            num_output_rows = min(len(lhs_entry.output_rows), len(rhs_entry.output_rows))
            lhs_output_rows = lhs_entry.output_rows[:num_output_rows]
            rhs_output_rows = rhs_entry.output_rows[:num_output_rows]
            output_rows: list[llmfn_output_row.LLMFnOutputRow] = []
            for result_num, lhs_and_rhs_output_row in enumerate(
                zip(lhs_output_rows, rhs_output_rows)
            ):
                lhs_output_row, rhs_output_row = lhs_and_rhs_output_row

                # Combine cells from lhs_output_row and rhs_output_row into a
                # single row.
                # Although it is possible for RESULT_NUM (the index of each
                # text_result if a prompt produces multiple text_results) to be
                # different between the left and right sides, we ignore their
                # RESULT_NUM entries and write our own.
                row_data: dict[str, Any] = {
                    llmfn_outputs.ColumnNames.RESULT_NUM: result_num,
                    self._result_name: self._result_compare_fn(lhs_output_row, rhs_output_row),
                }
                output_row = llmfn_output_row.LLMFnOutputRow(data=row_data, result_type=Any)

                # Add the prompt vars.
                output_row.add(llmfn_outputs.ColumnNames.PROMPT_VARS, lhs_entry.prompt_vars)

                # Add the results from the left-hand side and right-hand side.
                for name, row in [
                    (self._lhs_name, lhs_output_row),
                    (self._rhs_name, rhs_output_row),
                ]:
                    for k, v in row.items():
                        if k != llmfn_outputs.ColumnNames.RESULT_NUM:
                            # We use LLMFnOutputRow.add() because it handles column
                            # name collisions.
                            output_row.add("{}_{}".format(name, k), v)

                output_rows.append(output_row)

            outputs.append(
                llmfn_outputs.LLMFnOutputEntry(
                    prompt_num=lhs_entry.prompt_num,
                    input_num=lhs_entry.input_num,
                    prompt_vars=lhs_entry.prompt_vars,
                    output_rows=self._run_post_processing_cmds(
                        lhs_output_rows=lhs_output_rows,
                        rhs_output_rows=rhs_output_rows,
                        results=output_rows,
                    ),
                )
            )
        return outputs

    def add_compare_post_process_add_fn(
        self,
        name: str,
        fn: llmfn_post_process.LLMCompareFnPostProcessBatchAddFn,
    ) -> LLMFunction:
        self._post_process_cmds.append(
            llmfn_post_process_cmds.LLMCompareFnPostProcessAddCommand(name=name, fn=fn)
        )
        return self

# === NexusCore/app\extensions.py ===
from celery import Celery, Task

def celery_init_app(app):
    class ContextTask(Task):
        def __call__(self, *args, **kwargs):
            with app.app_context():
                return self.run(*args, **kwargs)

    celery = Celery(app.import_name)
    celery.config_from_object(app.config["CELERY"])
    celery.Task = ContextTask
    app.celery = celery            # ← 外部から参照できるよう保持
    return celery

# === NexusCore/openenv\Lib\site-packages\anthropic\lib\vertex\_client.py ===
from __future__ import annotations

import os
from typing import TYPE_CHECKING, Any, Union, Mapping, TypeVar
from typing_extensions import Self, override

import httpx

from ... import _exceptions
from ._auth import load_auth, refresh_auth
from ._beta import Beta, AsyncBeta
from ..._types import NOT_GIVEN, NotGiven, Transport, ProxiesTypes, AsyncTransport
from ..._utils import is_dict, asyncify, is_given
from ..._compat import model_copy, typed_cached_property
from ..._models import FinalRequestOptions
from ..._version import __version__
from ..._streaming import Stream, AsyncStream
from ..._exceptions import APIStatusError
from ..._base_client import (
    DEFAULT_MAX_RETRIES,
    DEFAULT_CONNECTION_LIMITS,
    BaseClient,
    SyncAPIClient,
    AsyncAPIClient,
    SyncHttpxClientWrapper,
    AsyncHttpxClientWrapper,
)
from ...resources.messages import Messages, AsyncMessages

if TYPE_CHECKING:
    from google.auth.credentials import Credentials as GoogleCredentials  # type: ignore


DEFAULT_VERSION = "vertex-2023-10-16"

_HttpxClientT = TypeVar("_HttpxClientT", bound=Union[httpx.Client, httpx.AsyncClient])
_DefaultStreamT = TypeVar("_DefaultStreamT", bound=Union[Stream[Any], AsyncStream[Any]])


class BaseVertexClient(BaseClient[_HttpxClientT, _DefaultStreamT]):
    @typed_cached_property
    def region(self) -> str:
        raise RuntimeError("region not set")

    @typed_cached_property
    def project_id(self) -> str | None:
        project_id = os.environ.get("ANTHROPIC_VERTEX_PROJECT_ID")
        if project_id:
            return project_id

        return None

    @override
    def _make_status_error(
        self,
        err_msg: str,
        *,
        body: object,
        response: httpx.Response,
    ) -> APIStatusError:
        if response.status_code == 400:
            return _exceptions.BadRequestError(err_msg, response=response, body=body)

        if response.status_code == 401:
            return _exceptions.AuthenticationError(err_msg, response=response, body=body)

        if response.status_code == 403:
            return _exceptions.PermissionDeniedError(err_msg, response=response, body=body)

        if response.status_code == 404:
            return _exceptions.NotFoundError(err_msg, response=response, body=body)

        if response.status_code == 409:
            return _exceptions.ConflictError(err_msg, response=response, body=body)

        if response.status_code == 422:
            return _exceptions.UnprocessableEntityError(err_msg, response=response, body=body)

        if response.status_code == 429:
            return _exceptions.RateLimitError(err_msg, response=response, body=body)

        if response.status_code >= 500:
            return _exceptions.InternalServerError(err_msg, response=response, body=body)
        return APIStatusError(err_msg, response=response, body=body)


class AnthropicVertex(BaseVertexClient[httpx.Client, Stream[Any]], SyncAPIClient):
    messages: Messages
    beta: Beta

    def __init__(
        self,
        *,
        region: str | NotGiven = NOT_GIVEN,
        project_id: str | NotGiven = NOT_GIVEN,
        access_token: str | None = None,
        credentials: GoogleCredentials | None = None,
        base_url: str | httpx.URL | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
        max_retries: int = DEFAULT_MAX_RETRIES,
        default_headers: Mapping[str, str] | None = None,
        default_query: Mapping[str, object] | None = None,
        # Configure a custom httpx client. See the [httpx documentation](https://www.python-httpx.org/api/#client) for more details.
        http_client: httpx.Client | None = None,
        # See httpx documentation for [custom transports](https://www.python-httpx.org/advanced/#custom-transports)
        transport: Transport | None = None,
        # See httpx documentation for [proxies](https://www.python-httpx.org/advanced/#http-proxying)
        proxies: ProxiesTypes | None = None,
        # See httpx documentation for [limits](https://www.python-httpx.org/advanced/#pool-limit-configuration)
        connection_pool_limits: httpx.Limits | None = None,
        _strict_response_validation: bool = False,
    ) -> None:
        if not is_given(region):
            region = os.environ.get("CLOUD_ML_REGION", NOT_GIVEN)
        if not is_given(region):
            raise ValueError(
                "No region was given. The client should be instantiated with the `region` argument or the `CLOUD_ML_REGION` environment variable should be set."
            )

        if base_url is None:
            base_url = os.environ.get("ANTHROPIC_VERTEX_BASE_URL")
            if base_url is None:
                base_url = f"https://{region}-aiplatform.googleapis.com/v1"

        super().__init__(
            version=__version__,
            base_url=base_url,
            timeout=timeout,
            max_retries=max_retries,
            custom_headers=default_headers,
            custom_query=default_query,
            http_client=http_client,
            transport=transport,
            proxies=proxies,
            limits=connection_pool_limits,
            _strict_response_validation=_strict_response_validation,
        )

        if is_given(project_id):
            self.project_id = project_id

        self.region = region
        self.access_token = access_token
        self.credentials = credentials

        self.messages = Messages(self)
        self.beta = Beta(self)

    @override
    def _prepare_options(self, options: FinalRequestOptions) -> FinalRequestOptions:
        return _prepare_options(options, project_id=self.project_id, region=self.region)

    @override
    def _prepare_request(self, request: httpx.Request) -> None:
        if request.headers.get("Authorization"):
            # already authenticated, nothing for us to do
            return

        request.headers["Authorization"] = f"Bearer {self._ensure_access_token()}"

    def _ensure_access_token(self) -> str:
        if self.access_token is not None:
            return self.access_token

        if not self.credentials:
            self.credentials, project_id = load_auth(project_id=self.project_id)
            if not self.project_id:
                self.project_id = project_id

        if self.credentials.expired or not self.credentials.token:
            refresh_auth(self.credentials)

        if not self.credentials.token:
            raise RuntimeError("Could not resolve API token from the environment")

        assert isinstance(self.credentials.token, str)
        return self.credentials.token

    def copy(
        self,
        *,
        region: str | NotGiven = NOT_GIVEN,
        project_id: str | NotGiven = NOT_GIVEN,
        access_token: str | None = None,
        credentials: GoogleCredentials | None = None,
        base_url: str | httpx.URL | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
        http_client: httpx.Client | None = None,
        connection_pool_limits: httpx.Limits | None = None,
        max_retries: int | NotGiven = NOT_GIVEN,
        default_headers: Mapping[str, str] | None = None,
        set_default_headers: Mapping[str, str] | None = None,
        default_query: Mapping[str, object] | None = None,
        set_default_query: Mapping[str, object] | None = None,
        _extra_kwargs: Mapping[str, Any] = {},
    ) -> Self:
        """
        Create a new client instance re-using the same options given to the current client with optional overriding.
        """
        if default_headers is not None and set_default_headers is not None:
            raise ValueError("The `default_headers` and `set_default_headers` arguments are mutually exclusive")

        if default_query is not None and set_default_query is not None:
            raise ValueError("The `default_query` and `set_default_query` arguments are mutually exclusive")

        headers = self._custom_headers
        if default_headers is not None:
            headers = {**headers, **default_headers}
        elif set_default_headers is not None:
            headers = set_default_headers

        params = self._custom_query
        if default_query is not None:
            params = {**params, **default_query}
        elif set_default_query is not None:
            params = set_default_query

        if connection_pool_limits is not None:
            if http_client is not None:
                raise ValueError("The 'http_client' argument is mutually exclusive with 'connection_pool_limits'")

            if not isinstance(self._client, SyncHttpxClientWrapper):
                raise ValueError(
                    "A custom HTTP client has been set and is mutually exclusive with the 'connection_pool_limits' argument"
                )

            http_client = None
        else:
            if self._limits is not DEFAULT_CONNECTION_LIMITS:
                connection_pool_limits = self._limits
            else:
                connection_pool_limits = None

            http_client = http_client or self._client

        return self.__class__(
            region=region if is_given(region) else self.region,
            project_id=project_id if is_given(project_id) else self.project_id or NOT_GIVEN,
            access_token=access_token or self.access_token,
            credentials=credentials or self.credentials,
            base_url=base_url or self.base_url,
            timeout=self.timeout if isinstance(timeout, NotGiven) else timeout,
            http_client=http_client,
            max_retries=max_retries if is_given(max_retries) else self.max_retries,
            default_headers=headers,
            default_query=params,
            **_extra_kwargs,
        )

    # Alias for `copy` for nicer inline usage, e.g.
    # client.with_options(timeout=10).foo.create(...)
    with_options = copy


class AsyncAnthropicVertex(BaseVertexClient[httpx.AsyncClient, AsyncStream[Any]], AsyncAPIClient):
    messages: AsyncMessages
    beta: AsyncBeta

    def __init__(
        self,
        *,
        region: str | NotGiven = NOT_GIVEN,
        project_id: str | NotGiven = NOT_GIVEN,
        access_token: str | None = None,
        credentials: GoogleCredentials | None = None,
        base_url: str | httpx.URL | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
        max_retries: int = DEFAULT_MAX_RETRIES,
        default_headers: Mapping[str, str] | None = None,
        default_query: Mapping[str, object] | None = None,
        # Configure a custom httpx client. See the [httpx documentation](https://www.python-httpx.org/api/#client) for more details.
        http_client: httpx.AsyncClient | None = None,
        # See httpx documentation for [custom transports](https://www.python-httpx.org/advanced/#custom-transports)
        transport: AsyncTransport | None = None,
        # See httpx documentation for [proxies](https://www.python-httpx.org/advanced/#http-proxying)
        proxies: ProxiesTypes | None = None,
        # See httpx documentation for [limits](https://www.python-httpx.org/advanced/#pool-limit-configuration)
        connection_pool_limits: httpx.Limits | None = None,
        _strict_response_validation: bool = False,
    ) -> None:
        if not is_given(region):
            region = os.environ.get("CLOUD_ML_REGION", NOT_GIVEN)
        if not is_given(region):
            raise ValueError(
                "No region was given. The client should be instantiated with the `region` argument or the `CLOUD_ML_REGION` environment variable should be set."
            )

        if base_url is None:
            base_url = os.environ.get("ANTHROPIC_VERTEX_BASE_URL")
            if base_url is None:
                base_url = f"https://{region}-aiplatform.googleapis.com/v1"

        super().__init__(
            version=__version__,
            base_url=base_url,
            timeout=timeout,
            max_retries=max_retries,
            custom_headers=default_headers,
            custom_query=default_query,
            http_client=http_client,
            transport=transport,
            proxies=proxies,
            limits=connection_pool_limits,
            _strict_response_validation=_strict_response_validation,
        )

        if is_given(project_id):
            self.project_id = project_id

        self.region = region
        self.access_token = access_token
        self.credentials = credentials

        self.messages = AsyncMessages(self)
        self.beta = AsyncBeta(self)

    @override
    async def _prepare_options(self, options: FinalRequestOptions) -> FinalRequestOptions:
        return _prepare_options(options, project_id=self.project_id, region=self.region)

    @override
    async def _prepare_request(self, request: httpx.Request) -> None:
        if request.headers.get("Authorization"):
            # already authenticated, nothing for us to do
            return

        request.headers["Authorization"] = f"Bearer {await self._ensure_access_token()}"

    async def _ensure_access_token(self) -> str:
        if self.access_token is not None:
            return self.access_token

        if not self.credentials:
            self.credentials, project_id = await asyncify(load_auth)(project_id=self.project_id)
            if not self.project_id:
                self.project_id = project_id

        if self.credentials.expired or not self.credentials.token:
            await asyncify(refresh_auth)(self.credentials)

        if not self.credentials.token:
            raise RuntimeError("Could not resolve API token from the environment")

        assert isinstance(self.credentials.token, str)
        return self.credentials.token

    def copy(
        self,
        *,
        region: str | NotGiven = NOT_GIVEN,
        project_id: str | NotGiven = NOT_GIVEN,
        access_token: str | None = None,
        credentials: GoogleCredentials | None = None,
        base_url: str | httpx.URL | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
        http_client: httpx.AsyncClient | None = None,
        connection_pool_limits: httpx.Limits | None = None,
        max_retries: int | NotGiven = NOT_GIVEN,
        default_headers: Mapping[str, str] | None = None,
        set_default_headers: Mapping[str, str] | None = None,
        default_query: Mapping[str, object] | None = None,
        set_default_query: Mapping[str, object] | None = None,
        _extra_kwargs: Mapping[str, Any] = {},
    ) -> Self:
        """
        Create a new client instance re-using the same options given to the current client with optional overriding.
        """
        if default_headers is not None and set_default_headers is not None:
            raise ValueError("The `default_headers` and `set_default_headers` arguments are mutually exclusive")

        if default_query is not None and set_default_query is not None:
            raise ValueError("The `default_query` and `set_default_query` arguments are mutually exclusive")

        headers = self._custom_headers
        if default_headers is not None:
            headers = {**headers, **default_headers}
        elif set_default_headers is not None:
            headers = set_default_headers

        params = self._custom_query
        if default_query is not None:
            params = {**params, **default_query}
        elif set_default_query is not None:
            params = set_default_query

        if connection_pool_limits is not None:
            if http_client is not None:
                raise ValueError("The 'http_client' argument is mutually exclusive with 'connection_pool_limits'")

            if not isinstance(self._client, AsyncHttpxClientWrapper):
                raise ValueError(
                    "A custom HTTP client has been set and is mutually exclusive with the 'connection_pool_limits' argument"
                )

            http_client = None
        else:
            if self._limits is not DEFAULT_CONNECTION_LIMITS:
                connection_pool_limits = self._limits
            else:
                connection_pool_limits = None

            http_client = http_client or self._client

        return self.__class__(
            region=region if is_given(region) else self.region,
            project_id=project_id if is_given(project_id) else self.project_id or NOT_GIVEN,
            access_token=access_token or self.access_token,
            credentials=credentials or self.credentials,
            base_url=base_url or self.base_url,
            timeout=self.timeout if isinstance(timeout, NotGiven) else timeout,
            http_client=http_client,
            max_retries=max_retries if is_given(max_retries) else self.max_retries,
            default_headers=headers,
            default_query=params,
            **_extra_kwargs,
        )

    # Alias for `copy` for nicer inline usage, e.g.
    # client.with_options(timeout=10).foo.create(...)
    with_options = copy


def _prepare_options(input_options: FinalRequestOptions, *, project_id: str | None, region: str) -> FinalRequestOptions:
    options = model_copy(input_options, deep=True)

    if is_dict(options.json_data):
        options.json_data.setdefault("anthropic_version", DEFAULT_VERSION)

    if options.url in {"/v1/messages", "/v1/messages?beta=true"} and options.method == "post":
        if project_id is None:
            raise RuntimeError(
                "No project_id was given and it could not be resolved from credentials. The client should be instantiated with the `project_id` argument or the `ANTHROPIC_VERTEX_PROJECT_ID` environment variable should be set."
            )

        if not is_dict(options.json_data):
            raise RuntimeError("Expected json data to be a dictionary for post /v1/messages")

        model = options.json_data.pop("model")
        stream = options.json_data.get("stream", False)
        specifier = "streamRawPredict" if stream else "rawPredict"

        options.url = f"/projects/{project_id}/locations/{region}/publishers/anthropic/models/{model}:{specifier}"

        if is_dict(options.json_data):
            options.json_data.pop("model", None)

    return options

# === NexusCore/src\modules\diff_viewer.py ===
# modules/diff_viewer.py

import difflib

def generate_diff(old_code: str, new_code: str) -> str:
    diff = difflib.unified_diff(
        old_code.splitlines(),
        new_code.splitlines(),
        fromfile='Before',
        tofile='After',
        lineterm=''
    )
    return "\n".join(diff)

# === NexusCore/src\tests\test_sample.py ===
import pytest
from sample import add_two_integers

def test_add_two_integers():
    assert add_two_integers(1, 2) == 3
    assert add_two_integers(-1, -2) == -3
    assert add_two_integers(0, 0) == 0

    with pytest.raises(TypeError):
        add_two_integers("1", 2)

    with pytest.raises(TypeError):
        add_two_integers(1, "2")

# === NexusCore/openenv\Lib\site-packages\anthropic\lib\streaming\_prompt_caching_beta_messages.py ===
from __future__ import annotations

from types import TracebackType
from typing import TYPE_CHECKING, Any, Callable, cast
from typing_extensions import Self, Iterator, Awaitable, AsyncIterator, assert_never

import httpx

from ...types import ContentBlock
from ..._utils import consume_sync_iterator, consume_async_iterator
from ..._models import build, construct_type
from ..._streaming import Stream, AsyncStream
from ._prompt_caching_beta_types import (
    TextEvent,
    InputJsonEvent,
    MessageStopEvent,
    ContentBlockStopEvent,
    PromptCachingBetaMessageStreamEvent,
)
from ...types.beta.prompt_caching import PromptCachingBetaMessage, RawPromptCachingBetaMessageStreamEvent

if TYPE_CHECKING:
    from ..._client import Anthropic, AsyncAnthropic


class PromptCachingBetaMessageStream:
    text_stream: Iterator[str]
    """Iterator over just the text deltas in the stream.

    ```py
    for text in stream.text_stream:
        print(text, end="", flush=True)
    print()
    ```
    """

    response: httpx.Response

    def __init__(
        self,
        *,
        cast_to: type[RawPromptCachingBetaMessageStreamEvent],
        response: httpx.Response,
        client: Anthropic,
    ) -> None:
        self.response = response
        self._cast_to = cast_to
        self._client = client

        self.text_stream = self.__stream_text__()
        self.__final_message_snapshot: PromptCachingBetaMessage | None = None

        self._iterator = self.__stream__()
        self._raw_stream: Stream[RawPromptCachingBetaMessageStreamEvent] = Stream(
            cast_to=cast_to, response=response, client=client
        )

    def __next__(self) -> PromptCachingBetaMessageStreamEvent:
        return self._iterator.__next__()

    def __iter__(self) -> Iterator[PromptCachingBetaMessageStreamEvent]:
        for item in self._iterator:
            yield item

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        self.close()

    def close(self) -> None:
        """
        Close the response and release the connection.

        Automatically called if the response body is read to completion.
        """
        self.response.close()

    def get_final_message(self) -> PromptCachingBetaMessage:
        """Waits until the stream has been read to completion and returns
        the accumulated `PromptCachingBetaMessage` object.
        """
        self.until_done()
        assert self.__final_message_snapshot is not None
        return self.__final_message_snapshot

    def get_final_text(self) -> str:
        """Returns all `text` content blocks concatenated together.

        > [!NOTE]
        > Currently the API will only respond with a single content block.

        Will raise an error if no `text` content blocks were returned.
        """
        message = self.get_final_message()
        text_blocks: list[str] = []
        for block in message.content:
            if block.type == "text":
                text_blocks.append(block.text)

        if not text_blocks:
            raise RuntimeError("Expected to have received at least 1 text block")

        return "".join(text_blocks)

    def until_done(self) -> None:
        """Blocks until the stream has been consumed"""
        consume_sync_iterator(self)

    # properties
    @property
    def current_message_snapshot(self) -> PromptCachingBetaMessage:
        assert self.__final_message_snapshot is not None
        return self.__final_message_snapshot

    def __stream__(self) -> Iterator[PromptCachingBetaMessageStreamEvent]:
        for sse_event in self._raw_stream:
            self.__final_message_snapshot = accumulate_event(
                event=sse_event,
                current_snapshot=self.__final_message_snapshot,
            )

            events_to_fire = build_events(event=sse_event, message_snapshot=self.current_message_snapshot)
            for event in events_to_fire:
                yield event

    def __stream_text__(self) -> Iterator[str]:
        for chunk in self:
            if chunk.type == "content_block_delta" and chunk.delta.type == "text_delta":
                yield chunk.delta.text


class PromptCachingBetaMessageStreamManager:
    """Wrapper over PromptCachingBetaMessageStream that is returned by `.stream()`.

    ```py
    with client.beta.prompt_caching.messages.stream(...) as stream:
        for chunk in stream:
            ...
    ```
    """

    def __init__(
        self,
        api_request: Callable[[], Stream[RawPromptCachingBetaMessageStreamEvent]],
    ) -> None:
        self.__stream: PromptCachingBetaMessageStream | None = None
        self.__api_request = api_request

    def __enter__(self) -> PromptCachingBetaMessageStream:
        raw_stream = self.__api_request()

        self.__stream = PromptCachingBetaMessageStream(
            cast_to=raw_stream._cast_to,
            response=raw_stream.response,
            client=raw_stream._client,
        )

        return self.__stream

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        if self.__stream is not None:
            self.__stream.close()


class AsyncPromptCachingBetaMessageStream:
    text_stream: AsyncIterator[str]
    """Async iterator over just the text deltas in the stream.

    ```py
    async for text in stream.text_stream:
        print(text, end="", flush=True)
    print()
    ```
    """

    response: httpx.Response

    def __init__(
        self,
        *,
        cast_to: type[RawPromptCachingBetaMessageStreamEvent],
        response: httpx.Response,
        client: AsyncAnthropic,
    ) -> None:
        self.response = response
        self._cast_to = cast_to
        self._client = client

        self.text_stream = self.__stream_text__()
        self.__final_message_snapshot: PromptCachingBetaMessage | None = None

        self._iterator = self.__stream__()
        self._raw_stream: AsyncStream[RawPromptCachingBetaMessageStreamEvent] = AsyncStream(
            cast_to=cast_to, response=response, client=client
        )

    async def __anext__(self) -> PromptCachingBetaMessageStreamEvent:
        return await self._iterator.__anext__()

    async def __aiter__(self) -> AsyncIterator[PromptCachingBetaMessageStreamEvent]:
        async for item in self._iterator:
            yield item

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        await self.close()

    async def close(self) -> None:
        """
        Close the response and release the connection.

        Automatically called if the response body is read to completion.
        """
        await self.response.aclose()

    async def get_final_message(self) -> PromptCachingBetaMessage:
        """Waits until the stream has been read to completion and returns
        the accumulated `PromptCachingBetaMessage` object.
        """
        await self.until_done()
        assert self.__final_message_snapshot is not None
        return self.__final_message_snapshot

    async def get_final_text(self) -> str:
        """Returns all `text` content blocks concatenated together.

        > [!NOTE]
        > Currently the API will only respond with a single content block.

        Will raise an error if no `text` content blocks were returned.
        """
        message = await self.get_final_message()
        text_blocks: list[str] = []
        for block in message.content:
            if block.type == "text":
                text_blocks.append(block.text)

        if not text_blocks:
            raise RuntimeError("Expected to have received at least 1 text block")

        return "".join(text_blocks)

    async def until_done(self) -> None:
        """Waits until the stream has been consumed"""
        await consume_async_iterator(self)

    # properties
    @property
    def current_message_snapshot(self) -> PromptCachingBetaMessage:
        assert self.__final_message_snapshot is not None
        return self.__final_message_snapshot

    async def __stream__(self) -> AsyncIterator[PromptCachingBetaMessageStreamEvent]:
        async for sse_event in self._raw_stream:
            self.__final_message_snapshot = accumulate_event(
                event=sse_event,
                current_snapshot=self.__final_message_snapshot,
            )

            events_to_fire = build_events(event=sse_event, message_snapshot=self.current_message_snapshot)
            for event in events_to_fire:
                yield event

    async def __stream_text__(self) -> AsyncIterator[str]:
        async for chunk in self:
            if chunk.type == "content_block_delta" and chunk.delta.type == "text_delta":
                yield chunk.delta.text


class AsyncPromptCachingBetaMessageStreamManager:
    """Wrapper over AsyncMessageStream that is returned by `.stream()`
    so that an async context manager can be used without `await`ing the
    original client call.

    ```py
    async with client.messages.stream(...) as stream:
        async for chunk in stream:
            ...
    ```
    """

    def __init__(
        self,
        api_request: Awaitable[AsyncStream[RawPromptCachingBetaMessageStreamEvent]],
    ) -> None:
        self.__stream: AsyncPromptCachingBetaMessageStream | None = None
        self.__api_request = api_request

    async def __aenter__(self) -> AsyncPromptCachingBetaMessageStream:
        raw_stream = await self.__api_request

        self.__stream = AsyncPromptCachingBetaMessageStream(
            cast_to=raw_stream._cast_to,
            response=raw_stream.response,
            client=raw_stream._client,
        )

        return self.__stream

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        if self.__stream is not None:
            await self.__stream.close()


def build_events(
    *,
    event: RawPromptCachingBetaMessageStreamEvent,
    message_snapshot: PromptCachingBetaMessage,
) -> list[PromptCachingBetaMessageStreamEvent]:
    events_to_fire: list[PromptCachingBetaMessageStreamEvent] = []

    if event.type == "message_start":
        events_to_fire.append(event)
    elif event.type == "message_delta":
        events_to_fire.append(event)
    elif event.type == "message_stop":
        events_to_fire.append(build(MessageStopEvent, type="message_stop", message=message_snapshot))
    elif event.type == "content_block_start":
        events_to_fire.append(event)
    elif event.type == "content_block_delta":
        events_to_fire.append(event)

        content_block = message_snapshot.content[event.index]
        if event.delta.type == "text_delta" and content_block.type == "text":
            events_to_fire.append(
                build(
                    TextEvent,
                    type="text",
                    text=event.delta.text,
                    snapshot=content_block.text,
                )
            )
        elif event.delta.type == "input_json_delta" and content_block.type == "tool_use":
            events_to_fire.append(
                build(
                    InputJsonEvent,
                    type="input_json",
                    partial_json=event.delta.partial_json,
                    snapshot=content_block.input,
                )
            )
    elif event.type == "content_block_stop":
        content_block = message_snapshot.content[event.index]

        events_to_fire.append(
            build(ContentBlockStopEvent, type="content_block_stop", index=event.index, content_block=content_block),
        )
    else:
        # we only want exhaustive checking for linters, not at runtime
        if TYPE_CHECKING:  # type: ignore[unreachable]
            assert_never(event)

    return events_to_fire


JSON_BUF_PROPERTY = "__json_buf"


def accumulate_event(
    *,
    event: RawPromptCachingBetaMessageStreamEvent,
    current_snapshot: PromptCachingBetaMessage | None,
) -> PromptCachingBetaMessage:
    if current_snapshot is None:
        if event.type == "message_start":
            return PromptCachingBetaMessage.construct(**cast(Any, event.message.to_dict()))

        raise RuntimeError(f'Unexpected event order, got {event.type} before "message_start"')

    if event.type == "content_block_start":
        # TODO: check index
        current_snapshot.content.append(
            cast(
                ContentBlock,
                construct_type(type_=ContentBlock, value=event.content_block.model_dump()),
            ),
        )
    elif event.type == "content_block_delta":
        content = current_snapshot.content[event.index]
        if content.type == "text" and event.delta.type == "text_delta":
            content.text += event.delta.text
        elif content.type == "tool_use" and event.delta.type == "input_json_delta":
            from jiter import from_json

            # we need to keep track of the raw JSON string as well so that we can
            # re-parse it for each delta, for now we just store it as an untyped
            # property on the snapshot
            json_buf = cast(bytes, getattr(content, JSON_BUF_PROPERTY, b""))
            json_buf += bytes(event.delta.partial_json, "utf-8")

            if json_buf:
                content.input = from_json(json_buf, partial_mode=True)

            setattr(content, JSON_BUF_PROPERTY, json_buf)
    elif event.type == "message_delta":
        current_snapshot.stop_reason = event.delta.stop_reason
        current_snapshot.stop_sequence = event.delta.stop_sequence
        current_snapshot.usage.output_tokens = event.usage.output_tokens

    return current_snapshot

# === NexusCore/openenv\Lib\site-packages\anthropic\lib\streaming\_messages.py ===
from __future__ import annotations

from types import TracebackType
from typing import TYPE_CHECKING, Any, Callable, cast
from typing_extensions import Self, Iterator, Awaitable, AsyncIterator, assert_never

import httpx

from ._types import (
    TextEvent,
    InputJsonEvent,
    MessageStopEvent,
    MessageStreamEvent,
    ContentBlockStopEvent,
)
from ...types import Message, ContentBlock, RawMessageStreamEvent
from ..._utils import consume_sync_iterator, consume_async_iterator
from ..._models import build, construct_type
from ..._streaming import Stream, AsyncStream

if TYPE_CHECKING:
    from ..._client import Anthropic, AsyncAnthropic


class MessageStream:
    text_stream: Iterator[str]
    """Iterator over just the text deltas in the stream.

    ```py
    for text in stream.text_stream:
        print(text, end="", flush=True)
    print()
    ```
    """

    response: httpx.Response

    def __init__(
        self,
        *,
        cast_to: type[RawMessageStreamEvent],
        response: httpx.Response,
        client: Anthropic,
    ) -> None:
        self.response = response
        self._cast_to = cast_to
        self._client = client

        self.text_stream = self.__stream_text__()
        self.__final_message_snapshot: Message | None = None

        self._iterator = self.__stream__()
        self._raw_stream: Stream[RawMessageStreamEvent] = Stream(cast_to=cast_to, response=response, client=client)

    def __next__(self) -> MessageStreamEvent:
        return self._iterator.__next__()

    def __iter__(self) -> Iterator[MessageStreamEvent]:
        for item in self._iterator:
            yield item

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        self.close()

    def close(self) -> None:
        """
        Close the response and release the connection.

        Automatically called if the response body is read to completion.
        """
        self.response.close()

    def get_final_message(self) -> Message:
        """Waits until the stream has been read to completion and returns
        the accumulated `Message` object.
        """
        self.until_done()
        assert self.__final_message_snapshot is not None
        return self.__final_message_snapshot

    def get_final_text(self) -> str:
        """Returns all `text` content blocks concatenated together.

        > [!NOTE]
        > Currently the API will only respond with a single content block.

        Will raise an error if no `text` content blocks were returned.
        """
        message = self.get_final_message()
        text_blocks: list[str] = []
        for block in message.content:
            if block.type == "text":
                text_blocks.append(block.text)

        if not text_blocks:
            raise RuntimeError("Expected to have received at least 1 text block")

        return "".join(text_blocks)

    def until_done(self) -> None:
        """Blocks until the stream has been consumed"""
        consume_sync_iterator(self)

    # properties
    @property
    def current_message_snapshot(self) -> Message:
        assert self.__final_message_snapshot is not None
        return self.__final_message_snapshot

    def __stream__(self) -> Iterator[MessageStreamEvent]:
        for sse_event in self._raw_stream:
            self.__final_message_snapshot = accumulate_event(
                event=sse_event,
                current_snapshot=self.__final_message_snapshot,
            )

            events_to_fire = build_events(event=sse_event, message_snapshot=self.current_message_snapshot)
            for event in events_to_fire:
                yield event

    def __stream_text__(self) -> Iterator[str]:
        for chunk in self:
            if chunk.type == "content_block_delta" and chunk.delta.type == "text_delta":
                yield chunk.delta.text


class MessageStreamManager:
    """Wrapper over MessageStream that is returned by `.stream()`.

    ```py
    with client.messages.stream(...) as stream:
        for chunk in stream:
            ...
    ```
    """

    def __init__(
        self,
        api_request: Callable[[], Stream[RawMessageStreamEvent]],
    ) -> None:
        self.__stream: MessageStream | None = None
        self.__api_request = api_request

    def __enter__(self) -> MessageStream:
        raw_stream = self.__api_request()

        self.__stream = MessageStream(
            cast_to=raw_stream._cast_to,
            response=raw_stream.response,
            client=raw_stream._client,
        )

        return self.__stream

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        if self.__stream is not None:
            self.__stream.close()


class AsyncMessageStream:
    text_stream: AsyncIterator[str]
    """Async iterator over just the text deltas in the stream.

    ```py
    async for text in stream.text_stream:
        print(text, end="", flush=True)
    print()
    ```
    """

    response: httpx.Response

    def __init__(
        self,
        *,
        cast_to: type[RawMessageStreamEvent],
        response: httpx.Response,
        client: AsyncAnthropic,
    ) -> None:
        self.response = response
        self._cast_to = cast_to
        self._client = client

        self.text_stream = self.__stream_text__()
        self.__final_message_snapshot: Message | None = None

        self._iterator = self.__stream__()
        self._raw_stream: AsyncStream[RawMessageStreamEvent] = AsyncStream(
            cast_to=cast_to, response=response, client=client
        )

    async def __anext__(self) -> MessageStreamEvent:
        return await self._iterator.__anext__()

    async def __aiter__(self) -> AsyncIterator[MessageStreamEvent]:
        async for item in self._iterator:
            yield item

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        await self.close()

    async def close(self) -> None:
        """
        Close the response and release the connection.

        Automatically called if the response body is read to completion.
        """
        await self.response.aclose()

    async def get_final_message(self) -> Message:
        """Waits until the stream has been read to completion and returns
        the accumulated `Message` object.
        """
        await self.until_done()
        assert self.__final_message_snapshot is not None
        return self.__final_message_snapshot

    async def get_final_text(self) -> str:
        """Returns all `text` content blocks concatenated together.

        > [!NOTE]
        > Currently the API will only respond with a single content block.

        Will raise an error if no `text` content blocks were returned.
        """
        message = await self.get_final_message()
        text_blocks: list[str] = []
        for block in message.content:
            if block.type == "text":
                text_blocks.append(block.text)

        if not text_blocks:
            raise RuntimeError("Expected to have received at least 1 text block")

        return "".join(text_blocks)

    async def until_done(self) -> None:
        """Waits until the stream has been consumed"""
        await consume_async_iterator(self)

    # properties
    @property
    def current_message_snapshot(self) -> Message:
        assert self.__final_message_snapshot is not None
        return self.__final_message_snapshot

    async def __stream__(self) -> AsyncIterator[MessageStreamEvent]:
        async for sse_event in self._raw_stream:
            self.__final_message_snapshot = accumulate_event(
                event=sse_event,
                current_snapshot=self.__final_message_snapshot,
            )

            events_to_fire = build_events(event=sse_event, message_snapshot=self.current_message_snapshot)
            for event in events_to_fire:
                yield event

    async def __stream_text__(self) -> AsyncIterator[str]:
        async for chunk in self:
            if chunk.type == "content_block_delta" and chunk.delta.type == "text_delta":
                yield chunk.delta.text


class AsyncMessageStreamManager:
    """Wrapper over AsyncMessageStream that is returned by `.stream()`
    so that an async context manager can be used without `await`ing the
    original client call.

    ```py
    async with client.messages.stream(...) as stream:
        async for chunk in stream:
            ...
    ```
    """

    def __init__(
        self,
        api_request: Awaitable[AsyncStream[RawMessageStreamEvent]],
    ) -> None:
        self.__stream: AsyncMessageStream | None = None
        self.__api_request = api_request

    async def __aenter__(self) -> AsyncMessageStream:
        raw_stream = await self.__api_request

        self.__stream = AsyncMessageStream(
            cast_to=raw_stream._cast_to,
            response=raw_stream.response,
            client=raw_stream._client,
        )

        return self.__stream

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        if self.__stream is not None:
            await self.__stream.close()


def build_events(
    *,
    event: RawMessageStreamEvent,
    message_snapshot: Message,
) -> list[MessageStreamEvent]:
    events_to_fire: list[MessageStreamEvent] = []

    if event.type == "message_start":
        events_to_fire.append(event)
    elif event.type == "message_delta":
        events_to_fire.append(event)
    elif event.type == "message_stop":
        events_to_fire.append(build(MessageStopEvent, type="message_stop", message=message_snapshot))
    elif event.type == "content_block_start":
        events_to_fire.append(event)
    elif event.type == "content_block_delta":
        events_to_fire.append(event)

        content_block = message_snapshot.content[event.index]
        if event.delta.type == "text_delta" and content_block.type == "text":
            events_to_fire.append(
                build(
                    TextEvent,
                    type="text",
                    text=event.delta.text,
                    snapshot=content_block.text,
                )
            )
        elif event.delta.type == "input_json_delta" and content_block.type == "tool_use":
            events_to_fire.append(
                build(
                    InputJsonEvent,
                    type="input_json",
                    partial_json=event.delta.partial_json,
                    snapshot=content_block.input,
                )
            )
    elif event.type == "content_block_stop":
        content_block = message_snapshot.content[event.index]

        events_to_fire.append(
            build(ContentBlockStopEvent, type="content_block_stop", index=event.index, content_block=content_block),
        )
    else:
        # we only want exhaustive checking for linters, not at runtime
        if TYPE_CHECKING:  # type: ignore[unreachable]
            assert_never(event)

    return events_to_fire


JSON_BUF_PROPERTY = "__json_buf"


def accumulate_event(
    *,
    event: RawMessageStreamEvent,
    current_snapshot: Message | None,
) -> Message:
    if current_snapshot is None:
        if event.type == "message_start":
            return Message.construct(**cast(Any, event.message.to_dict()))

        raise RuntimeError(f'Unexpected event order, got {event.type} before "message_start"')

    if event.type == "content_block_start":
        # TODO: check index
        current_snapshot.content.append(
            cast(
                ContentBlock,
                construct_type(type_=ContentBlock, value=event.content_block.model_dump()),
            ),
        )
    elif event.type == "content_block_delta":
        content = current_snapshot.content[event.index]
        if content.type == "text" and event.delta.type == "text_delta":
            content.text += event.delta.text
        elif content.type == "tool_use" and event.delta.type == "input_json_delta":
            from jiter import from_json

            # we need to keep track of the raw JSON string as well so that we can
            # re-parse it for each delta, for now we just store it as an untyped
            # property on the snapshot
            json_buf = cast(bytes, getattr(content, JSON_BUF_PROPERTY, b""))
            json_buf += bytes(event.delta.partial_json, "utf-8")

            if json_buf:
                content.input = from_json(json_buf, partial_mode=True)

            setattr(content, JSON_BUF_PROPERTY, json_buf)
    elif event.type == "message_delta":
        current_snapshot.stop_reason = event.delta.stop_reason
        current_snapshot.stop_sequence = event.delta.stop_sequence
        current_snapshot.usage.output_tokens = event.usage.output_tokens

    return current_snapshot

# === NexusCore/sandbox_repo\app\main.py ===
def add(a, b):
    """
    Add two numbers and return the result.

    Args:
    a (int or float): The first number.
    b (int or float): The second number.

    Returns:
    int or float: The sum of the two numbers.
    """
    return a + b

# === NexusCore/src\sandbox_logs\repair_20250713_125710_fixed.py ===
エラーの内容から見ると、Pythonのコードではなく、コメント部分に非ASCII文字（日本語）が含まれていることが原因でSyntaxErrorが発生しています。Pythonのコメントは基本的にASCII文字のみを使用するべきです。

また、関数の内容自体も間違っているようです。addという関数名から推測するに、この関数は2つの数値を加算することが期待されますが、現在の実装では引き算を行っています。

これらの問題を修正したコードは以下の通りです。

```python
def add(a, b):
    return a + b  # Corrected from subtraction to addition
```

ただし、エラーメッセージにはユニットテストの実行に関する情報も含まれています。この情報から推測するに、このコードはユニットテストの一部として実行されている可能性があります。その場合、テストコードも同様に修正する必要があります。ただし、具体的なテストコードが示されていないため、その部分については具体的な修正案を提供できません。

# === NexusCore/src\sandbox_logs\repair_20250713_125723_original.py ===
エラーの内容から見ると、Pythonのコードではなく、コメント部分に非ASCII文字（日本語）が含まれていることが原因でSyntaxErrorが発生しています。Pythonのコメントは基本的にASCII文字のみを使用するべきです。

また、関数の内容自体も間違っているようです。addという関数名から推測するに、この関数は2つの数値を加算することが期待されますが、現在の実装では引き算を行っています。

これらの問題を修正したコードは以下の通りです。

```python
def add(a, b):
    return a + b  # Corrected from subtraction to addition
```

ただし、エラーメッセージにはユニットテストの実行に関する情報も含まれています。この情報から推測するに、このコードはユニットテストの一部として実行されている可能性があります。その場合、テストコードも同様に修正する必要があります。ただし、具体的なテストコードが示されていないため、その部分については具体的な修正案を提供できません。

# === NexusCore/openenv\Lib\site-packages\win32\lib\sspi.py ===
"""
Helper classes for SSPI authentication via the win32security module.

SSPI authentication involves a token-exchange "dance", the exact details
of which depends on the authentication provider used.  There are also
a number of complex flags and constants that need to be used - in most
cases, there are reasonable defaults.

These classes attempt to hide these details from you until you really need
to know.  They are not designed to handle all cases, just the common ones.
If you need finer control than offered here, just use the win32security
functions directly.
"""

# Based on Roger Upole's sspi demos.
# $Id$
import sspicon
import win32security

error = win32security.error  # Re-exported alias


class _BaseAuth:
    def __init__(self):
        self.reset()

    def reset(self):
        """Reset everything to an unauthorized state"""
        self.ctxt: win32security.PyCtxtHandleType | None = None
        self.authenticated = False
        self.initiator_name = None
        self.service_name = None

        # The next seq_num for an encrypt/sign operation
        self.next_seq_num = 0

    def _get_next_seq_num(self):
        """Get the next sequence number for a transmission.  Default
        implementation is to increment a counter
        """
        ret = self.next_seq_num
        self.next_seq_num += 1
        return ret

    def encrypt(self, data):
        """Encrypt a string, returning a tuple of (encrypted_data, trailer).
        These can be passed to decrypt to get back the original string.
        """
        pkg_size_info = self.ctxt.QueryContextAttributes(sspicon.SECPKG_ATTR_SIZES)
        trailersize = pkg_size_info["SecurityTrailer"]

        encbuf = win32security.PySecBufferDescType()
        encbuf.append(win32security.PySecBufferType(len(data), sspicon.SECBUFFER_DATA))
        encbuf.append(
            win32security.PySecBufferType(trailersize, sspicon.SECBUFFER_TOKEN)
        )
        encbuf[0].Buffer = data
        self.ctxt.EncryptMessage(0, encbuf, self._get_next_seq_num())
        return encbuf[0].Buffer, encbuf[1].Buffer

    def decrypt(self, data, trailer):
        """Decrypt a previously encrypted string, returning the orignal data"""
        encbuf = win32security.PySecBufferDescType()
        encbuf.append(win32security.PySecBufferType(len(data), sspicon.SECBUFFER_DATA))
        encbuf.append(
            win32security.PySecBufferType(len(trailer), sspicon.SECBUFFER_TOKEN)
        )
        encbuf[0].Buffer = data
        encbuf[1].Buffer = trailer
        self.ctxt.DecryptMessage(encbuf, self._get_next_seq_num())
        return encbuf[0].Buffer

    def sign(self, data):
        """sign a string suitable for transmission, returning the signature.
        Passing the data and signature to verify will determine if the data
        is unchanged.
        """
        pkg_size_info = self.ctxt.QueryContextAttributes(sspicon.SECPKG_ATTR_SIZES)
        sigsize = pkg_size_info["MaxSignature"]
        sigbuf = win32security.PySecBufferDescType()
        sigbuf.append(win32security.PySecBufferType(len(data), sspicon.SECBUFFER_DATA))
        sigbuf.append(win32security.PySecBufferType(sigsize, sspicon.SECBUFFER_TOKEN))
        sigbuf[0].Buffer = data

        self.ctxt.MakeSignature(0, sigbuf, self._get_next_seq_num())
        return sigbuf[1].Buffer

    def verify(self, data, sig):
        """Verifies data and its signature.  If verification fails, an sspi.error
        will be raised.
        """
        sigbuf = win32security.PySecBufferDescType()
        sigbuf.append(win32security.PySecBufferType(len(data), sspicon.SECBUFFER_DATA))
        sigbuf.append(win32security.PySecBufferType(len(sig), sspicon.SECBUFFER_TOKEN))

        sigbuf[0].Buffer = data
        sigbuf[1].Buffer = sig
        self.ctxt.VerifySignature(sigbuf, self._get_next_seq_num())

    def unwrap(self, token):
        """
        GSSAPI's unwrap with SSPI.
        https://learn.microsoft.com/en-us/windows/win32/secauthn/sspi-kerberos-interoperability-with-gssapi

        Usable mainly with Kerberos SSPI package, but this is not enforced.

        Return the clear text, and a boolean that is True if the token was encrypted.
        """
        buffer = win32security.PySecBufferDescType()
        # This buffer will contain a "stream", which is the token coming from the other side
        buffer.append(
            win32security.PySecBufferType(len(token), sspicon.SECBUFFER_STREAM)
        )
        buffer[0].Buffer = token

        # This buffer will receive the clear, or just unwrapped text if no encryption was used.
        # Will be resized by the lib.
        buffer.append(win32security.PySecBufferType(0, sspicon.SECBUFFER_DATA))

        pfQOP = self.ctxt.DecryptMessage(buffer, self._get_next_seq_num())

        r = buffer[1].Buffer
        return r, not (pfQOP == sspicon.SECQOP_WRAP_NO_ENCRYPT)

    def wrap(self, msg, encrypt=False):
        """
        GSSAPI's wrap with SSPI.
        https://learn.microsoft.com/en-us/windows/win32/secauthn/sspi-kerberos-interoperability-with-gssapi

        Usable mainly with Kerberos SSPI package, but this is not enforced.

        Wrap a message to be sent to the other side. Encrypted if encrypt is True.
        """

        size_info = self.ctxt.QueryContextAttributes(sspicon.SECPKG_ATTR_SIZES)
        trailer_size = size_info["SecurityTrailer"]
        block_size = size_info["BlockSize"]

        buffer = win32security.PySecBufferDescType()

        # This buffer will contain unencrypted data to wrap, and maybe encrypt.
        buffer.append(win32security.PySecBufferType(len(msg), sspicon.SECBUFFER_DATA))
        buffer[0].Buffer = msg

        # Will receive the token that forms the beginning of the msg
        buffer.append(
            win32security.PySecBufferType(trailer_size, sspicon.SECBUFFER_TOKEN)
        )

        # The trailer is needed in case of block encryption
        buffer.append(
            win32security.PySecBufferType(block_size, sspicon.SECBUFFER_PADDING)
        )

        fQOP = 0 if encrypt else sspicon.SECQOP_WRAP_NO_ENCRYPT
        self.ctxt.EncryptMessage(fQOP, buffer, self._get_next_seq_num())

        # Sec token, then data, then padding
        r = buffer[1].Buffer + buffer[0].Buffer + buffer[2].Buffer
        return r

    def _amend_ctx_name(self):
        """Adds initiator and service names in the security context for ease of use"""
        if not self.authenticated:
            raise ValueError("Sec context is not completely authenticated")

        try:
            names = self.ctxt.QueryContextAttributes(sspicon.SECPKG_ATTR_NATIVE_NAMES)
        except error:
            # The SSP doesn't provide these attributes.
            pass
        else:
            self.initiator_name, self.service_name = names


class ClientAuth(_BaseAuth):
    """Manages the client side of an SSPI authentication handshake"""

    def __init__(
        self,
        pkg_name,  # Name of the package to used.
        client_name=None,  # User for whom credentials are used.
        auth_info=None,  # or a tuple of (username, domain, password)
        targetspn=None,  # Target security context provider name.
        scflags=None,  # security context flags
        datarep=sspicon.SECURITY_NETWORK_DREP,
    ):
        if scflags is None:
            scflags = (
                sspicon.ISC_REQ_INTEGRITY
                | sspicon.ISC_REQ_SEQUENCE_DETECT
                | sspicon.ISC_REQ_REPLAY_DETECT
                | sspicon.ISC_REQ_CONFIDENTIALITY
            )
        self.scflags = scflags
        self.datarep = datarep
        self.targetspn = targetspn
        self.pkg_info = win32security.QuerySecurityPackageInfo(pkg_name)
        (
            self.credentials,
            self.credentials_expiry,
        ) = win32security.AcquireCredentialsHandle(
            client_name,
            self.pkg_info["Name"],
            sspicon.SECPKG_CRED_OUTBOUND,
            None,
            auth_info,
        )
        _BaseAuth.__init__(self)

    def authorize(self, sec_buffer_in):
        """Perform *one* step of the client authentication process. Pass None for the first round"""
        if sec_buffer_in is not None and not isinstance(
            sec_buffer_in, win32security.PySecBufferDescType
        ):
            # User passed us the raw data - wrap it into a SecBufferDesc
            sec_buffer_new = win32security.PySecBufferDescType()
            tokenbuf = win32security.PySecBufferType(
                self.pkg_info["MaxToken"], sspicon.SECBUFFER_TOKEN
            )
            tokenbuf.Buffer = sec_buffer_in
            sec_buffer_new.append(tokenbuf)
            sec_buffer_in = sec_buffer_new
        sec_buffer_out = win32security.PySecBufferDescType()
        tokenbuf = win32security.PySecBufferType(
            self.pkg_info["MaxToken"], sspicon.SECBUFFER_TOKEN
        )
        sec_buffer_out.append(tokenbuf)
        ## input context handle should be NULL on first call
        ctxtin = self.ctxt
        if self.ctxt is None:
            self.ctxt = win32security.PyCtxtHandleType()
        err, attr, exp = win32security.InitializeSecurityContext(
            self.credentials,
            ctxtin,
            self.targetspn,
            self.scflags,
            self.datarep,
            sec_buffer_in,
            self.ctxt,
            sec_buffer_out,
        )
        # Stash these away incase someone needs to know the state from the
        # final call.
        self.ctxt_attr = attr
        self.ctxt_expiry = exp

        if err in (sspicon.SEC_I_COMPLETE_NEEDED, sspicon.SEC_I_COMPLETE_AND_CONTINUE):
            self.ctxt.CompleteAuthToken(sec_buffer_out)

        self.authenticated = err == 0
        if self.authenticated:
            self._amend_ctx_name()

        return err, sec_buffer_out


class ServerAuth(_BaseAuth):
    """Manages the server side of an SSPI authentication handshake"""

    def __init__(
        self, pkg_name, spn=None, scflags=None, datarep=sspicon.SECURITY_NETWORK_DREP
    ):
        self.spn = spn
        self.datarep = datarep

        if scflags is None:
            scflags = (
                sspicon.ASC_REQ_INTEGRITY
                | sspicon.ASC_REQ_SEQUENCE_DETECT
                | sspicon.ASC_REQ_REPLAY_DETECT
                | sspicon.ASC_REQ_CONFIDENTIALITY
            )
        # Should we default to sspicon.KerbAddExtraCredentialsMessage
        # if pkg_name=='Kerberos'?
        self.scflags = scflags

        self.pkg_info = win32security.QuerySecurityPackageInfo(pkg_name)

        (
            self.credentials,
            self.credentials_expiry,
        ) = win32security.AcquireCredentialsHandle(
            spn, self.pkg_info["Name"], sspicon.SECPKG_CRED_INBOUND, None, None
        )
        _BaseAuth.__init__(self)

    def authorize(self, sec_buffer_in):
        """Perform *one* step of the server authentication process."""
        if sec_buffer_in is not None and not isinstance(
            sec_buffer_in, win32security.PySecBufferDescType
        ):
            # User passed us the raw data - wrap it into a SecBufferDesc
            sec_buffer_new = win32security.PySecBufferDescType()
            tokenbuf = win32security.PySecBufferType(
                self.pkg_info["MaxToken"], sspicon.SECBUFFER_TOKEN
            )
            tokenbuf.Buffer = sec_buffer_in
            sec_buffer_new.append(tokenbuf)
            sec_buffer_in = sec_buffer_new

        sec_buffer_out = win32security.PySecBufferDescType()
        tokenbuf = win32security.PySecBufferType(
            self.pkg_info["MaxToken"], sspicon.SECBUFFER_TOKEN
        )
        sec_buffer_out.append(tokenbuf)
        ## input context handle is None initially, then handle returned from last call thereafter
        ctxtin = self.ctxt
        if self.ctxt is None:
            self.ctxt = win32security.PyCtxtHandleType()
        err, attr, exp = win32security.AcceptSecurityContext(
            self.credentials,
            ctxtin,
            sec_buffer_in,
            self.scflags,
            self.datarep,
            self.ctxt,
            sec_buffer_out,
        )

        # Stash these away incase someone needs to know the state from the
        # final call.
        self.ctxt_attr = attr
        self.ctxt_expiry = exp

        if err in (sspicon.SEC_I_COMPLETE_NEEDED, sspicon.SEC_I_COMPLETE_AND_CONTINUE):
            self.ctxt.CompleteAuthToken(sec_buffer_out)

        self.authenticated = err == 0
        if self.authenticated:
            self._amend_ctx_name()

        return err, sec_buffer_out


if __name__ == "__main__":
    # This is the security package (the security support provider / the security backend)
    # we want to use for this example.
    ssp = "Kerberos"  # or "NTLM" or "Negotiate" which enable negotiation between
    # Kerberos (prefered) and NTLM (if not supported on the other side).

    flags = (
        sspicon.ISC_REQ_MUTUAL_AUTH
        | sspicon.ISC_REQ_INTEGRITY  # mutual authentication
        | sspicon.ISC_REQ_SEQUENCE_DETECT  # check for integrity
        | sspicon.ISC_REQ_CONFIDENTIALITY  # enable out-of-order messages
        | sspicon.ISC_REQ_REPLAY_DETECT  # request confidentiality  # request replay detection
    )

    # Get our identity, mandatory for the Kerberos case *for this example*
    # Kerberos cannot be used if we don't tell it the target we want
    # to authenticate to.
    cred_handle, exp = win32security.AcquireCredentialsHandle(
        None, ssp, sspicon.SECPKG_CRED_INBOUND, None, None
    )
    cred = cred_handle.QueryCredentialsAttributes(sspicon.SECPKG_CRED_ATTR_NAMES)
    print("We are:", cred)

    # Setup the 2 contexts. In real life, only one is needed: the other one is
    # created in the process we want to communicate with.
    sspiclient = ClientAuth(ssp, scflags=flags, targetspn=cred)
    sspiserver = ServerAuth(ssp, scflags=flags)

    print(
        "SSP : {} ({})".format(
            sspiclient.pkg_info["Name"], sspiclient.pkg_info["Comment"]
        )
    )

    # Perform the authentication dance, each loop exchanging more information
    # on the way to completing authentication.
    sec_buffer = None
    client_step = 0
    server_step = 0
    while not sspiclient.authenticated or (sec_buffer and len(sec_buffer[0].Buffer)):
        client_step += 1
        err, sec_buffer = sspiclient.authorize(sec_buffer)
        print("Client step %s" % client_step)
        if sspiserver.authenticated and len(sec_buffer[0].Buffer) == 0:
            break

        server_step += 1
        err, sec_buffer = sspiserver.authorize(sec_buffer)
        print("Server step %s" % server_step)

    # Authentication process is finished.
    print("Initiator name from the service side:", sspiserver.initiator_name)
    print("Service name from the client side:   ", sspiclient.service_name)

    data = b"hello"

    # Simple signature, not compatible with GSSAPI.
    sig = sspiclient.sign(data)
    sspiserver.verify(data, sig)

    # Encryption
    encrypted, sig = sspiclient.encrypt(data)
    decrypted = sspiserver.decrypt(encrypted, sig)
    assert decrypted == data

    # GSSAPI wrapping, no encryption (NTLM always encrypts)
    wrapped = sspiclient.wrap(data)
    unwrapped, was_encrypted = sspiserver.unwrap(wrapped)
    print("encrypted ?", was_encrypted)
    assert data == unwrapped

    # GSSAPI wrapping, with encryption
    wrapped = sspiserver.wrap(data, encrypt=True)
    unwrapped, was_encrypted = sspiclient.unwrap(wrapped)
    print("encrypted ?", was_encrypted)
    assert data == unwrapped

    print("cool!")

# === NexusCore/openenv\Lib\site-packages\win32\lib\regutil.py ===
# Some registry helpers.
import os
import sys

import win32api
import win32con

# A .py file has a CLSID associated with it (why? - dunno!)
CLSIDPyFile = "{b51df050-06ae-11cf-ad3b-524153480001}"

RegistryIDPyFile = "Python.File"  # The registry "file type" of a .py file
RegistryIDPycFile = "Python.CompiledFile"  # The registry "file type" of a .pyc file


def BuildDefaultPythonKey():
    """Builds a string containing the path to the current registry key.

    The Python registry key contains the Python version.  This function
    uses the version of the DLL used by the current process to get the
    registry key currently in use.
    """
    return "Software\\Python\\PythonCore\\" + sys.winver


def GetRootKey():
    """Retrieves the Registry root in use by Python."""
    keyname = BuildDefaultPythonKey()
    try:
        k = win32api.RegOpenKey(win32con.HKEY_CURRENT_USER, keyname)
        k.close()
        return win32con.HKEY_CURRENT_USER
    except win32api.error:
        return win32con.HKEY_LOCAL_MACHINE


def GetRegistryDefaultValue(subkey, rootkey=None):
    """A helper to return the default value for a key in the registry."""
    if rootkey is None:
        rootkey = GetRootKey()
    return win32api.RegQueryValue(rootkey, subkey)


def SetRegistryDefaultValue(subKey, value, rootkey=None):
    """A helper to set the default value for a key in the registry"""
    if rootkey is None:
        rootkey = GetRootKey()
    if isinstance(value, str):
        typeId = win32con.REG_SZ
    elif isinstance(value, int):
        typeId = win32con.REG_DWORD
    else:
        raise TypeError(f"Value must be string or integer - was passed {value!r}")

    win32api.RegSetValue(rootkey, subKey, typeId, value)


def GetAppPathsKey():
    return "Software\\Microsoft\\Windows\\CurrentVersion\\App Paths"


def RegisterPythonExe(exeFullPath, exeAlias=None, exeAppPath=None):
    """Register a .exe file that uses Python.

    Registers the .exe with the OS.  This allows the specified .exe to
    be run from the command-line or start button without using the full path,
    and also to setup application specific path (ie, os.environ['PATH']).

    Currently the exeAppPath is not supported, so this function is general
    purpose, and not specific to Python at all.  Later, exeAppPath may provide
    a reasonable default that is used.

    exeFullPath -- The full path to the .exe
    exeAlias = None -- An alias for the exe - if none, the base portion
              of the filename is used.
    exeAppPath -- Not supported.
    """
    # Note - Don't work on win32s (but we don't care anymore!)
    if exeAppPath:
        raise ValueError("Do not support exeAppPath argument currently")
    if exeAlias is None:
        exeAlias = os.path.basename(exeFullPath)
    win32api.RegSetValue(
        GetRootKey(), GetAppPathsKey() + "\\" + exeAlias, win32con.REG_SZ, exeFullPath
    )


def GetRegisteredExe(exeAlias):
    """Get a registered .exe"""
    return win32api.RegQueryValue(GetRootKey(), GetAppPathsKey() + "\\" + exeAlias)


def UnregisterPythonExe(exeAlias):
    """Unregister a .exe file that uses Python."""
    try:
        win32api.RegDeleteKey(GetRootKey(), GetAppPathsKey() + "\\" + exeAlias)
    except win32api.error as exc:
        import winerror

        if exc.winerror != winerror.ERROR_FILE_NOT_FOUND:
            raise
        return


def RegisterNamedPath(name, path):
    """Register a named path - ie, a named PythonPath entry."""
    keyStr = BuildDefaultPythonKey() + "\\PythonPath"
    if name:
        keyStr += "\\" + name
    win32api.RegSetValue(GetRootKey(), keyStr, win32con.REG_SZ, path)


def UnregisterNamedPath(name):
    """Unregister a named path - ie, a named PythonPath entry."""
    keyStr = BuildDefaultPythonKey() + "\\PythonPath\\" + name
    try:
        win32api.RegDeleteKey(GetRootKey(), keyStr)
    except win32api.error as exc:
        import winerror

        if exc.winerror != winerror.ERROR_FILE_NOT_FOUND:
            raise
        return


def GetRegisteredNamedPath(name):
    """Get a registered named path, or None if it doesn't exist."""
    keyStr = BuildDefaultPythonKey() + "\\PythonPath"
    if name:
        keyStr += "\\" + name
    try:
        return win32api.RegQueryValue(GetRootKey(), keyStr)
    except win32api.error as exc:
        import winerror

        if exc.winerror != winerror.ERROR_FILE_NOT_FOUND:
            raise
        return None


def RegisterModule(modName, modPath):
    """Register an explicit module in the registry.  This forces the Python import
    mechanism to locate this module directly, without a sys.path search.  Thus
    a registered module need not appear in sys.path at all.

    modName -- The name of the module, as used by import.
    modPath -- The full path and file name of the module.
    """
    try:
        import os

        os.stat(modPath)
    except OSError:
        print("Warning: Registering non-existant module %s" % modPath)
    win32api.RegSetValue(
        GetRootKey(),
        BuildDefaultPythonKey() + "\\Modules\\%s" % modName,
        win32con.REG_SZ,
        modPath,
    )


def UnregisterModule(modName):
    """Unregister an explicit module in the registry.

    modName -- The name of the module, as used by import.
    """
    try:
        win32api.RegDeleteKey(
            GetRootKey(), BuildDefaultPythonKey() + "\\Modules\\%s" % modName
        )
    except win32api.error as exc:
        import winerror

        if exc.winerror != winerror.ERROR_FILE_NOT_FOUND:
            raise


def GetRegisteredHelpFile(helpDesc):
    """Given a description, return the registered entry."""
    try:
        return GetRegistryDefaultValue(BuildDefaultPythonKey() + "\\Help\\" + helpDesc)
    except win32api.error:
        try:
            return GetRegistryDefaultValue(
                BuildDefaultPythonKey() + "\\Help\\" + helpDesc,
                win32con.HKEY_CURRENT_USER,
            )
        except win32api.error:
            pass
    return None


def RegisterHelpFile(helpFile, helpPath, helpDesc=None, bCheckFile=1):
    """Register a help file in the registry.

      Note that this used to support writing to the Windows Help
      key, however this is no longer done, as it seems to be incompatible.

    helpFile -- the base name of the help file.
    helpPath -- the path to the help file
    helpDesc -- A description for the help file.  If None, the helpFile param is used.
    bCheckFile -- A flag indicating if the file existence should be checked.
    """
    if helpDesc is None:
        helpDesc = helpFile
    fullHelpFile = os.path.join(helpPath, helpFile)
    try:
        if bCheckFile:
            os.stat(fullHelpFile)
    except OSError:
        raise ValueError("Help file does not exist")
    # Now register with Python itself.
    win32api.RegSetValue(
        GetRootKey(),
        BuildDefaultPythonKey() + "\\Help\\%s" % helpDesc,
        win32con.REG_SZ,
        fullHelpFile,
    )


def UnregisterHelpFile(helpFile, helpDesc=None):
    """Unregister a help file in the registry.

    helpFile -- the base name of the help file.
    helpDesc -- A description for the help file.  If None, the helpFile param is used.
    """
    key = win32api.RegOpenKey(
        win32con.HKEY_LOCAL_MACHINE,
        "Software\\Microsoft\\Windows\\Help",
        0,
        win32con.KEY_ALL_ACCESS,
    )
    try:
        try:
            win32api.RegDeleteValue(key, helpFile)
        except win32api.error as exc:
            import winerror

            if exc.winerror != winerror.ERROR_FILE_NOT_FOUND:
                raise
    finally:
        win32api.RegCloseKey(key)

    # Now de-register with Python itself.
    if helpDesc is None:
        helpDesc = helpFile
    try:
        win32api.RegDeleteKey(
            GetRootKey(), BuildDefaultPythonKey() + "\\Help\\%s" % helpDesc
        )
    except win32api.error as exc:
        import winerror

        if exc.winerror != winerror.ERROR_FILE_NOT_FOUND:
            raise


def RegisterCoreDLL(coredllName=None):
    """Registers the core DLL in the registry.

    If no params are passed, the name of the Python DLL used in
    the current process is used and registered.
    """
    if coredllName is None:
        coredllName = win32api.GetModuleFileName(sys.dllhandle)
        # must exist!
    else:
        try:
            os.stat(coredllName)
        except OSError:
            print("Warning: Registering non-existant core DLL %s" % coredllName)

    hKey = win32api.RegCreateKey(GetRootKey(), BuildDefaultPythonKey())
    try:
        win32api.RegSetValue(hKey, "Dll", win32con.REG_SZ, coredllName)
    finally:
        win32api.RegCloseKey(hKey)
    # Lastly, setup the current version to point to me.
    win32api.RegSetValue(
        GetRootKey(),
        "Software\\Python\\PythonCore\\CurrentVersion",
        win32con.REG_SZ,
        sys.winver,
    )


def RegisterFileExtensions(defPyIcon, defPycIcon, runCommand):
    """Register the core Python file extensions.

    defPyIcon -- The default icon to use for .py files, in 'fname,offset' format.
    defPycIcon -- The default icon to use for .pyc files, in 'fname,offset' format.
    runCommand -- The command line to use for running .py files
    """
    # Register the file extensions.
    pythonFileId = RegistryIDPyFile
    win32api.RegSetValue(
        win32con.HKEY_CLASSES_ROOT, ".py", win32con.REG_SZ, pythonFileId
    )
    win32api.RegSetValue(
        win32con.HKEY_CLASSES_ROOT, pythonFileId, win32con.REG_SZ, "Python File"
    )
    win32api.RegSetValue(
        win32con.HKEY_CLASSES_ROOT,
        "%s\\CLSID" % pythonFileId,
        win32con.REG_SZ,
        CLSIDPyFile,
    )
    win32api.RegSetValue(
        win32con.HKEY_CLASSES_ROOT,
        "%s\\DefaultIcon" % pythonFileId,
        win32con.REG_SZ,
        defPyIcon,
    )
    base = "%s\\Shell" % RegistryIDPyFile
    win32api.RegSetValue(
        win32con.HKEY_CLASSES_ROOT, base + "\\Open", win32con.REG_SZ, "Run"
    )
    win32api.RegSetValue(
        win32con.HKEY_CLASSES_ROOT,
        base + "\\Open\\Command",
        win32con.REG_SZ,
        runCommand,
    )

    # Register the .PYC.
    pythonFileId = RegistryIDPycFile
    win32api.RegSetValue(
        win32con.HKEY_CLASSES_ROOT, ".pyc", win32con.REG_SZ, pythonFileId
    )
    win32api.RegSetValue(
        win32con.HKEY_CLASSES_ROOT,
        pythonFileId,
        win32con.REG_SZ,
        "Compiled Python File",
    )
    win32api.RegSetValue(
        win32con.HKEY_CLASSES_ROOT,
        "%s\\DefaultIcon" % pythonFileId,
        win32con.REG_SZ,
        defPycIcon,
    )
    base = "%s\\Shell" % pythonFileId
    win32api.RegSetValue(
        win32con.HKEY_CLASSES_ROOT, base + "\\Open", win32con.REG_SZ, "Run"
    )
    win32api.RegSetValue(
        win32con.HKEY_CLASSES_ROOT,
        base + "\\Open\\Command",
        win32con.REG_SZ,
        runCommand,
    )


def RegisterShellCommand(shellCommand, exeCommand, shellUserCommand=None):
    # Last param for "Open" - for a .py file to be executed by the command line
    # or shell execute (eg, just entering "foo.py"), the Command must be "Open",
    # but you may associate a different name for the right-click menu.
    # In our case, normally we have "Open=Run"
    base = "%s\\Shell" % RegistryIDPyFile
    if shellUserCommand:
        win32api.RegSetValue(
            win32con.HKEY_CLASSES_ROOT,
            base + "\\%s" % (shellCommand),
            win32con.REG_SZ,
            shellUserCommand,
        )

    win32api.RegSetValue(
        win32con.HKEY_CLASSES_ROOT,
        base + "\\%s\\Command" % (shellCommand),
        win32con.REG_SZ,
        exeCommand,
    )


def RegisterDDECommand(shellCommand, ddeApp, ddeTopic, ddeCommand):
    base = "%s\\Shell" % RegistryIDPyFile
    win32api.RegSetValue(
        win32con.HKEY_CLASSES_ROOT,
        base + "\\%s\\ddeexec" % (shellCommand),
        win32con.REG_SZ,
        ddeCommand,
    )
    win32api.RegSetValue(
        win32con.HKEY_CLASSES_ROOT,
        base + "\\%s\\ddeexec\\Application" % (shellCommand),
        win32con.REG_SZ,
        ddeApp,
    )
    win32api.RegSetValue(
        win32con.HKEY_CLASSES_ROOT,
        base + "\\%s\\ddeexec\\Topic" % (shellCommand),
        win32con.REG_SZ,
        ddeTopic,
    )

# === NexusCore/src\sandbox_logs\repair_20250713_114552_fixed.py ===
ここでのエラーはPythonのコード自体に問題があるわけではなく、テストモジュールのインポートに失敗していることが原因となっています。したがって、Pythonのコードを修正することで解決する問題ではありません。

エラーメッセージを見ると、'C:\\Users\\USER\\AppData\\Local\\Temp\\tmpjgrmw9nh\\test_main'というモジュールが見つからないという内容です。これは、テストを実行する際に必要なモジュールが適切な場所に存在しない、または適切な名前で存在しない可能性があります。

解決策としては、以下のことを確認してみてください。

1. テストモジュールが正しい場所に存在しているか確認する。
2. テストモジュールの名前が正しいか確認する。
3. Pythonのパス設定が正しいか確認する。

これらを確認・修正した上で再度テストを実行してみてください。

# === NexusCore/src\sandbox_logs\repair_20250713_124402_fixed.py ===
元のコードには二つの問題があります。一つは、関数`add`が実際には引数を減算していること、もう一つは、エラーメッセージから見て、Pythonのコードが日本語のコメントで始まっていることです。PythonはデフォルトでASCII文字しか受け付けないため、日本語のコメントが原因でエラーが発生しています。

以下に修正したコードを示します：

```python
# 以下は、指定されたPythonコードに対するpytest形式のユニットテストです。
def add(a, b):
    return a + b  # 修正：return a - bからreturn a + bへ
```

この修正により、関数`add`は引数を正しく加算し、日本語のコメントもASCII文字に変換されてエラーが解消されます。

# === NexusCore/src\sandbox_logs\repair_20250713_124414_original.py ===
元のコードには二つの問題があります。一つは、関数`add`が実際には引数を減算していること、もう一つは、エラーメッセージから見て、Pythonのコードが日本語のコメントで始まっていることです。PythonはデフォルトでASCII文字しか受け付けないため、日本語のコメントが原因でエラーが発生しています。

以下に修正したコードを示します：

```python
# 以下は、指定されたPythonコードに対するpytest形式のユニットテストです。
def add(a, b):
    return a + b  # 修正：return a - bからreturn a + bへ
```

この修正により、関数`add`は引数を正しく加算し、日本語のコメントもASCII文字に変換されてエラーが解消されます。

# === NexusCore/src\sandbox_logs\repair_20250713_213319_fixed.py ===
申し訳ありませんが、テスト対象のPythonコードが具体的に提供されていないため、具体的な修正コードを生成することができません。ただし、エラーメッセージから推測するに、テストコードの先頭に非ASCII文字（この場合は日本語）が含まれていることが問題のようです。

Pythonのソースコードに非ASCII文字を使用する場合、ファイルの先頭に文字エンコーディングを指定することが一般的です。以下のように、ファイルの先頭に文字エンコーディングを指定します：

```python
# -*- coding: utf-8 -*-
```

この行を追加すると、PythonはファイルがUTF-8でエンコードされていることを認識し、非ASCII文字を正しく処理できます。

ただし、この修正が問題を解決するかどうかは、テストコードの他の部分にどのような内容が含まれているかによります。

# === NexusCore/src\sandbox_logs\repair_20250713_213331_original.py ===
申し訳ありませんが、テスト対象のPythonコードが具体的に提供されていないため、具体的な修正コードを生成することができません。ただし、エラーメッセージから推測するに、テストコードの先頭に非ASCII文字（この場合は日本語）が含まれていることが問題のようです。

Pythonのソースコードに非ASCII文字を使用する場合、ファイルの先頭に文字エンコーディングを指定することが一般的です。以下のように、ファイルの先頭に文字エンコーディングを指定します：

```python
# -*- coding: utf-8 -*-
```

この行を追加すると、PythonはファイルがUTF-8でエンコードされていることを認識し、非ASCII文字を正しく処理できます。

ただし、この修正が問題を解決するかどうかは、テストコードの他の部分にどのような内容が含まれているかによります。

# === NexusCore/openenv\Lib\site-packages\anthropic\lib\bedrock\_client.py ===
from __future__ import annotations

import os
from typing import Any, Union, Mapping, TypeVar
from typing_extensions import Self, override

import httpx

from ... import _exceptions
from ._beta import Beta, AsyncBeta
from ..._types import NOT_GIVEN, Timeout, NotGiven
from ..._utils import is_dict, is_given
from ..._compat import model_copy
from ..._version import __version__
from ..._streaming import Stream, AsyncStream
from ..._exceptions import APIStatusError
from ..._base_client import (
    DEFAULT_MAX_RETRIES,
    BaseClient,
    SyncAPIClient,
    AsyncAPIClient,
    FinalRequestOptions,
)
from ._stream_decoder import AWSEventStreamDecoder
from ...resources.messages import Messages, AsyncMessages
from ...resources.completions import Completions, AsyncCompletions

DEFAULT_VERSION = "bedrock-2023-05-31"

_HttpxClientT = TypeVar("_HttpxClientT", bound=Union[httpx.Client, httpx.AsyncClient])
_DefaultStreamT = TypeVar("_DefaultStreamT", bound=Union[Stream[Any], AsyncStream[Any]])


def _prepare_options(input_options: FinalRequestOptions) -> FinalRequestOptions:
    options = model_copy(input_options, deep=True)

    if is_dict(options.json_data):
        options.json_data.setdefault("anthropic_version", DEFAULT_VERSION)

        if is_given(options.headers):
            betas = options.headers.get("anthropic-beta")
            if betas:
                options.json_data.setdefault("anthropic_beta", betas.split(","))

    if options.url in {"/v1/complete", "/v1/messages", "/v1/messages?beta=true"} and options.method == "post":
        if not is_dict(options.json_data):
            raise RuntimeError("Expected dictionary json_data for post /completions endpoint")

        model = options.json_data.pop("model", None)
        stream = options.json_data.pop("stream", False)
        if stream:
            options.url = f"/model/{model}/invoke-with-response-stream"
        else:
            options.url = f"/model/{model}/invoke"

    return options


class BaseBedrockClient(BaseClient[_HttpxClientT, _DefaultStreamT]):
    @override
    def _make_status_error(
        self,
        err_msg: str,
        *,
        body: object,
        response: httpx.Response,
    ) -> APIStatusError:
        if response.status_code == 400:
            return _exceptions.BadRequestError(err_msg, response=response, body=body)

        if response.status_code == 401:
            return _exceptions.AuthenticationError(err_msg, response=response, body=body)

        if response.status_code == 403:
            return _exceptions.PermissionDeniedError(err_msg, response=response, body=body)

        if response.status_code == 404:
            return _exceptions.NotFoundError(err_msg, response=response, body=body)

        if response.status_code == 409:
            return _exceptions.ConflictError(err_msg, response=response, body=body)

        if response.status_code == 422:
            return _exceptions.UnprocessableEntityError(err_msg, response=response, body=body)

        if response.status_code == 429:
            return _exceptions.RateLimitError(err_msg, response=response, body=body)

        if response.status_code >= 500:
            return _exceptions.InternalServerError(err_msg, response=response, body=body)
        return APIStatusError(err_msg, response=response, body=body)


class AnthropicBedrock(BaseBedrockClient[httpx.Client, Stream[Any]], SyncAPIClient):
    messages: Messages
    completions: Completions
    beta: Beta

    def __init__(
        self,
        aws_secret_key: str | None = None,
        aws_access_key: str | None = None,
        aws_region: str | None = None,
        aws_profile: str | None = None,
        aws_session_token: str | None = None,
        base_url: str | httpx.URL | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
        max_retries: int = DEFAULT_MAX_RETRIES,
        default_headers: Mapping[str, str] | None = None,
        default_query: Mapping[str, object] | None = None,
        # Configure a custom httpx client. See the [httpx documentation](https://www.python-httpx.org/api/#client) for more details.
        http_client: httpx.Client | None = None,
        # Enable or disable schema validation for data returned by the API.
        # When enabled an error APIResponseValidationError is raised
        # if the API responds with invalid data for the expected schema.
        #
        # This parameter may be removed or changed in the future.
        # If you rely on this feature, please open a GitHub issue
        # outlining your use-case to help us decide if it should be
        # part of our public interface in the future.
        _strict_response_validation: bool = False,
    ) -> None:
        self.aws_secret_key = aws_secret_key

        self.aws_access_key = aws_access_key

        if aws_region is None:
            aws_region = os.environ.get("AWS_REGION") or "us-east-1"
        self.aws_region = aws_region
        self.aws_profile = aws_profile

        self.aws_session_token = aws_session_token

        if base_url is None:
            base_url = os.environ.get("ANTHROPIC_BEDROCK_BASE_URL")
        if base_url is None:
            base_url = f"https://bedrock-runtime.{self.aws_region}.amazonaws.com"

        super().__init__(
            version=__version__,
            base_url=base_url,
            timeout=timeout,
            max_retries=max_retries,
            custom_headers=default_headers,
            custom_query=default_query,
            http_client=http_client,
            _strict_response_validation=_strict_response_validation,
        )

        self.beta = Beta(self)
        self.messages = Messages(self)
        self.completions = Completions(self)

    @override
    def _make_sse_decoder(self) -> AWSEventStreamDecoder:
        return AWSEventStreamDecoder()

    @override
    def _prepare_options(self, options: FinalRequestOptions) -> FinalRequestOptions:
        return _prepare_options(options)

    @override
    def _prepare_request(self, request: httpx.Request) -> None:
        from ._auth import get_auth_headers

        data = request.read().decode()

        headers = get_auth_headers(
            method=request.method,
            url=str(request.url),
            headers=request.headers,
            aws_access_key=self.aws_access_key,
            aws_secret_key=self.aws_secret_key,
            aws_session_token=self.aws_session_token,
            region=self.aws_region or "us-east-1",
            profile=self.aws_profile,
            data=data,
        )
        request.headers.update(headers)

    def copy(
        self,
        *,
        aws_secret_key: str | None = None,
        aws_access_key: str | None = None,
        aws_region: str | None = None,
        aws_session_token: str | None = None,
        base_url: str | httpx.URL | None = None,
        timeout: float | Timeout | None | NotGiven = NOT_GIVEN,
        http_client: httpx.Client | None = None,
        max_retries: int | NotGiven = NOT_GIVEN,
        default_headers: Mapping[str, str] | None = None,
        set_default_headers: Mapping[str, str] | None = None,
        default_query: Mapping[str, object] | None = None,
        set_default_query: Mapping[str, object] | None = None,
        _extra_kwargs: Mapping[str, Any] = {},
    ) -> Self:
        """
        Create a new client instance re-using the same options given to the current client with optional overriding.
        """
        if default_headers is not None and set_default_headers is not None:
            raise ValueError("The `default_headers` and `set_default_headers` arguments are mutually exclusive")

        if default_query is not None and set_default_query is not None:
            raise ValueError("The `default_query` and `set_default_query` arguments are mutually exclusive")

        headers = self._custom_headers
        if default_headers is not None:
            headers = {**headers, **default_headers}
        elif set_default_headers is not None:
            headers = set_default_headers

        params = self._custom_query
        if default_query is not None:
            params = {**params, **default_query}
        elif set_default_query is not None:
            params = set_default_query

        return self.__class__(
            aws_secret_key=aws_secret_key or self.aws_secret_key,
            aws_access_key=aws_access_key or self.aws_access_key,
            aws_region=aws_region or self.aws_region,
            aws_session_token=aws_session_token or self.aws_session_token,
            base_url=base_url or self.base_url,
            timeout=self.timeout if isinstance(timeout, NotGiven) else timeout,
            http_client=http_client,
            max_retries=max_retries if is_given(max_retries) else self.max_retries,
            default_headers=headers,
            default_query=params,
            **_extra_kwargs,
        )

    # Alias for `copy` for nicer inline usage, e.g.
    # client.with_options(timeout=10).foo.create(...)
    with_options = copy


class AsyncAnthropicBedrock(BaseBedrockClient[httpx.AsyncClient, AsyncStream[Any]], AsyncAPIClient):
    messages: AsyncMessages
    completions: AsyncCompletions
    beta: AsyncBeta

    def __init__(
        self,
        aws_secret_key: str | None = None,
        aws_access_key: str | None = None,
        aws_region: str | None = None,
        aws_profile: str | None = None,
        aws_session_token: str | None = None,
        base_url: str | httpx.URL | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
        max_retries: int = DEFAULT_MAX_RETRIES,
        default_headers: Mapping[str, str] | None = None,
        default_query: Mapping[str, object] | None = None,
        # Configure a custom httpx client. See the [httpx documentation](https://www.python-httpx.org/api/#client) for more details.
        http_client: httpx.AsyncClient | None = None,
        # Enable or disable schema validation for data returned by the API.
        # When enabled an error APIResponseValidationError is raised
        # if the API responds with invalid data for the expected schema.
        #
        # This parameter may be removed or changed in the future.
        # If you rely on this feature, please open a GitHub issue
        # outlining your use-case to help us decide if it should be
        # part of our public interface in the future.
        _strict_response_validation: bool = False,
    ) -> None:
        self.aws_secret_key = aws_secret_key

        self.aws_access_key = aws_access_key

        if aws_region is None:
            aws_region = os.environ.get("AWS_REGION") or "us-east-1"
        self.aws_region = aws_region
        self.aws_profile = aws_profile

        self.aws_session_token = aws_session_token

        if base_url is None:
            base_url = os.environ.get("ANTHROPIC_BEDROCK_BASE_URL")
        if base_url is None:
            base_url = f"https://bedrock-runtime.{self.aws_region}.amazonaws.com"

        super().__init__(
            version=__version__,
            base_url=base_url,
            timeout=timeout,
            max_retries=max_retries,
            custom_headers=default_headers,
            custom_query=default_query,
            http_client=http_client,
            _strict_response_validation=_strict_response_validation,
        )

        self.messages = AsyncMessages(self)
        self.completions = AsyncCompletions(self)
        self.beta = AsyncBeta(self)

    @override
    def _make_sse_decoder(self) -> AWSEventStreamDecoder:
        return AWSEventStreamDecoder()

    @override
    async def _prepare_options(self, options: FinalRequestOptions) -> FinalRequestOptions:
        return _prepare_options(options)

    @override
    async def _prepare_request(self, request: httpx.Request) -> None:
        from ._auth import get_auth_headers

        data = request.read().decode()

        headers = get_auth_headers(
            method=request.method,
            url=str(request.url),
            headers=request.headers,
            aws_access_key=self.aws_access_key,
            aws_secret_key=self.aws_secret_key,
            aws_session_token=self.aws_session_token,
            region=self.aws_region or "us-east-1",
            profile=self.aws_profile,
            data=data,
        )
        request.headers.update(headers)

    def copy(
        self,
        *,
        aws_secret_key: str | None = None,
        aws_access_key: str | None = None,
        aws_region: str | None = None,
        aws_session_token: str | None = None,
        base_url: str | httpx.URL | None = None,
        timeout: float | Timeout | None | NotGiven = NOT_GIVEN,
        http_client: httpx.AsyncClient | None = None,
        max_retries: int | NotGiven = NOT_GIVEN,
        default_headers: Mapping[str, str] | None = None,
        set_default_headers: Mapping[str, str] | None = None,
        default_query: Mapping[str, object] | None = None,
        set_default_query: Mapping[str, object] | None = None,
        _extra_kwargs: Mapping[str, Any] = {},
    ) -> Self:
        """
        Create a new client instance re-using the same options given to the current client with optional overriding.
        """
        if default_headers is not None and set_default_headers is not None:
            raise ValueError("The `default_headers` and `set_default_headers` arguments are mutually exclusive")

        if default_query is not None and set_default_query is not None:
            raise ValueError("The `default_query` and `set_default_query` arguments are mutually exclusive")

        headers = self._custom_headers
        if default_headers is not None:
            headers = {**headers, **default_headers}
        elif set_default_headers is not None:
            headers = set_default_headers

        params = self._custom_query
        if default_query is not None:
            params = {**params, **default_query}
        elif set_default_query is not None:
            params = set_default_query

        return self.__class__(
            aws_secret_key=aws_secret_key or self.aws_secret_key,
            aws_access_key=aws_access_key or self.aws_access_key,
            aws_region=aws_region or self.aws_region,
            aws_session_token=aws_session_token or self.aws_session_token,
            base_url=base_url or self.base_url,
            timeout=self.timeout if isinstance(timeout, NotGiven) else timeout,
            http_client=http_client,
            max_retries=max_retries if is_given(max_retries) else self.max_retries,
            default_headers=headers,
            default_query=params,
            **_extra_kwargs,
        )

    # Alias for `copy` for nicer inline usage, e.g.
    # client.with_options(timeout=10).foo.create(...)
    with_options = copy

# === NexusCore/openenv\Lib\site-packages\numpy\lib\tests\test_packbits.py ===
from itertools import chain

import pytest

import numpy as np
from numpy.testing import assert_array_equal, assert_equal, assert_raises


def test_packbits():
    # Copied from the docstring.
    a = [[[1, 0, 1], [0, 1, 0]],
         [[1, 1, 0], [0, 0, 1]]]
    for dt in '?bBhHiIlLqQ':
        arr = np.array(a, dtype=dt)
        b = np.packbits(arr, axis=-1)
        assert_equal(b.dtype, np.uint8)
        assert_array_equal(b, np.array([[[160], [64]], [[192], [32]]]))

    assert_raises(TypeError, np.packbits, np.array(a, dtype=float))


def test_packbits_empty():
    shapes = [
        (0,), (10, 20, 0), (10, 0, 20), (0, 10, 20), (20, 0, 0), (0, 20, 0),
        (0, 0, 20), (0, 0, 0),
    ]
    for dt in '?bBhHiIlLqQ':
        for shape in shapes:
            a = np.empty(shape, dtype=dt)
            b = np.packbits(a)
            assert_equal(b.dtype, np.uint8)
            assert_equal(b.shape, (0,))


def test_packbits_empty_with_axis():
    # Original shapes and lists of packed shapes for different axes.
    shapes = [
        ((0,), [(0,)]),
        ((10, 20, 0), [(2, 20, 0), (10, 3, 0), (10, 20, 0)]),
        ((10, 0, 20), [(2, 0, 20), (10, 0, 20), (10, 0, 3)]),
        ((0, 10, 20), [(0, 10, 20), (0, 2, 20), (0, 10, 3)]),
        ((20, 0, 0), [(3, 0, 0), (20, 0, 0), (20, 0, 0)]),
        ((0, 20, 0), [(0, 20, 0), (0, 3, 0), (0, 20, 0)]),
        ((0, 0, 20), [(0, 0, 20), (0, 0, 20), (0, 0, 3)]),
        ((0, 0, 0), [(0, 0, 0), (0, 0, 0), (0, 0, 0)]),
    ]
    for dt in '?bBhHiIlLqQ':
        for in_shape, out_shapes in shapes:
            for ax, out_shape in enumerate(out_shapes):
                a = np.empty(in_shape, dtype=dt)
                b = np.packbits(a, axis=ax)
                assert_equal(b.dtype, np.uint8)
                assert_equal(b.shape, out_shape)

@pytest.mark.parametrize('bitorder', ('little', 'big'))
def test_packbits_large(bitorder):
    # test data large enough for 16 byte vectorization
    a = np.array([1, 1, 0, 1, 1, 1, 0, 0, 0, 0, 1, 1, 1, 0, 0, 1, 1, 1, 0, 0,
                  0, 0, 0, 1, 0, 1, 1, 1, 0, 0, 0, 0, 0, 1, 0, 0, 0, 1, 1, 1,
                  1, 1, 0, 1, 0, 1, 1, 0, 0, 0, 1, 1, 1, 1, 0, 0, 0, 1, 0, 0,
                  1, 1, 0, 0, 0, 1, 0, 1, 1, 0, 0, 0, 1, 0, 0, 1, 1, 1, 1, 1,
                  1, 0, 1, 0, 1, 0, 0, 1, 0, 1, 1, 0, 1, 0, 1, 1, 0, 1, 0, 1,
                  1, 0, 1, 0, 1, 0, 1, 1, 0, 0, 0, 0, 1, 0, 1, 0, 0, 0, 1, 1,
                  1, 0, 0, 0, 1, 0, 1, 0, 1, 1, 0, 1, 0, 0, 1, 0, 1, 1, 1, 1,
                  0, 1, 1, 0, 0, 0, 1, 1, 0, 0, 1, 0, 1, 0, 0, 1, 0, 0, 1, 1,
                  1, 1, 1, 1, 1, 1, 0, 1, 1, 0, 0, 0, 1, 0, 0, 0, 0, 1, 1, 0,
                  1, 1, 0, 0, 0, 0, 1, 1, 1, 1, 0, 1, 0, 0, 0, 0, 0, 1, 1, 1,
                  1, 0, 0, 0, 0, 1, 1, 1, 1, 1, 0, 1, 1, 0, 1, 1, 0, 0, 0, 0,
                  0, 1, 0, 0, 1, 1, 0, 0, 1, 0, 1, 1, 0, 0, 0, 0, 1, 1, 0, 1,
                  1, 1, 0, 1, 0, 1, 1, 1, 0, 0, 1, 0, 0, 0, 1, 0, 1, 1, 0, 0,
                  1, 0, 0, 1, 0, 0, 0, 1, 0, 1, 1, 1, 1, 1, 1, 0, 1, 0, 1, 0,
                  1, 0, 1, 0, 0, 1, 1, 0, 1, 0, 1, 0, 0, 1, 0, 1, 0, 1, 1, 0])
    a = a.repeat(3)
    for dtype in '?bBhHiIlLqQ':
        arr = np.array(a, dtype=dtype)
        b = np.packbits(arr, axis=None, bitorder=bitorder)
        assert_equal(b.dtype, np.uint8)
        r = [252, 127, 192, 3, 254, 7, 252, 0, 7, 31, 240, 0, 28, 1, 255, 252,
             113, 248, 3, 255, 192, 28, 15, 192, 28, 126, 0, 224, 127, 255,
             227, 142, 7, 31, 142, 63, 28, 126, 56, 227, 240, 0, 227, 128, 63,
             224, 14, 56, 252, 112, 56, 255, 241, 248, 3, 240, 56, 224, 112,
             63, 255, 255, 199, 224, 14, 0, 31, 143, 192, 3, 255, 199, 0, 1,
             255, 224, 1, 255, 252, 126, 63, 0, 1, 192, 252, 14, 63, 0, 15,
             199, 252, 113, 255, 3, 128, 56, 252, 14, 7, 0, 113, 255, 255, 142, 56, 227,
             129, 248, 227, 129, 199, 31, 128]
        if bitorder == 'big':
            assert_array_equal(b, r)
        # equal for size being multiple of 8
        assert_array_equal(np.unpackbits(b, bitorder=bitorder)[:-4], a)

        # check last byte of different remainders (16 byte vectorization)
        b = [np.packbits(arr[:-i], axis=None)[-1] for i in range(1, 16)]
        assert_array_equal(b, [128, 128, 128, 31, 30, 28, 24, 16, 0, 0, 0, 199,
                               198, 196, 192])

        arr = arr.reshape(36, 25)
        b = np.packbits(arr, axis=0)
        assert_equal(b.dtype, np.uint8)
        assert_array_equal(b, [[190, 186, 178, 178, 150, 215, 87, 83, 83, 195,
                                199, 206, 204, 204, 140, 140, 136, 136, 8, 40, 105,
                                107, 75, 74, 88],
                               [72, 216, 248, 241, 227, 195, 202, 90, 90, 83,
                                83, 119, 127, 109, 73, 64, 208, 244, 189, 45,
                                41, 104, 122, 90, 18],
                               [113, 120, 248, 216, 152, 24, 60, 52, 182, 150,
                                150, 150, 146, 210, 210, 246, 255, 255, 223,
                                151, 21, 17, 17, 131, 163],
                               [214, 210, 210, 64, 68, 5, 5, 1, 72, 88, 92,
                                92, 78, 110, 39, 181, 149, 220, 222, 218, 218,
                                202, 234, 170, 168],
                               [0, 128, 128, 192, 80, 112, 48, 160, 160, 224,
                                240, 208, 144, 128, 160, 224, 240, 208, 144,
                                144, 176, 240, 224, 192, 128]])

        b = np.packbits(arr, axis=1)
        assert_equal(b.dtype, np.uint8)
        assert_array_equal(b, [[252, 127, 192,   0],
                               [  7, 252,  15, 128],
                               [240,   0,  28,   0],
                               [255, 128,   0, 128],
                               [192,  31, 255, 128],
                               [142,  63,   0,   0],
                               [255, 240,   7,   0],
                               [  7, 224,  14,   0],
                               [126,   0, 224,   0],
                               [255, 255, 199,   0],
                               [ 56,  28, 126,   0],
                               [113, 248, 227, 128],
                               [227, 142,  63,   0],
                               [  0,  28, 112,   0],
                               [ 15, 248,   3, 128],
                               [ 28, 126,  56,   0],
                               [ 56, 255, 241, 128],
                               [240,   7, 224,   0],
                               [227, 129, 192, 128],
                               [255, 255, 254,   0],
                               [126,   0, 224,   0],
                               [  3, 241, 248,   0],
                               [  0, 255, 241, 128],
                               [128,   0, 255, 128],
                               [224,   1, 255, 128],
                               [248, 252, 126,   0],
                               [  0,   7,   3, 128],
                               [224, 113, 248,   0],
                               [  0, 252, 127, 128],
                               [142,  63, 224,   0],
                               [224,  14,  63,   0],
                               [  7,   3, 128,   0],
                               [113, 255, 255, 128],
                               [ 28, 113, 199,   0],
                               [  7, 227, 142,   0],
                               [ 14,  56, 252,   0]])

        arr = arr.T.copy()
        b = np.packbits(arr, axis=0)
        assert_equal(b.dtype, np.uint8)
        assert_array_equal(b, [[252, 7, 240, 255, 192, 142, 255, 7, 126, 255,
                                56, 113, 227, 0, 15, 28, 56, 240, 227, 255,
                                126, 3, 0, 128, 224, 248, 0, 224, 0, 142, 224,
                                7, 113, 28, 7, 14],
                                [127, 252, 0, 128, 31, 63, 240, 224, 0, 255,
                                 28, 248, 142, 28, 248, 126, 255, 7, 129, 255,
                                 0, 241, 255, 0, 1, 252, 7, 113, 252, 63, 14,
                                 3, 255, 113, 227, 56],
                                [192, 15, 28, 0, 255, 0, 7, 14, 224, 199, 126,
                                 227, 63, 112, 3, 56, 241, 224, 192, 254, 224,
                                 248, 241, 255, 255, 126, 3, 248, 127, 224, 63,
                                 128, 255, 199, 142, 252],
                                [0, 128, 0, 128, 128, 0, 0, 0, 0, 0, 0, 128, 0,
                                 0, 128, 0, 128, 0, 128, 0, 0, 0, 128, 128,
                                 128, 0, 128, 0, 128, 0, 0, 0, 128, 0, 0, 0]])

        b = np.packbits(arr, axis=1)
        assert_equal(b.dtype, np.uint8)
        assert_array_equal(b, [[190,  72, 113, 214,   0],
                               [186, 216, 120, 210, 128],
                               [178, 248, 248, 210, 128],
                               [178, 241, 216,  64, 192],
                               [150, 227, 152,  68,  80],
                               [215, 195,  24,   5, 112],
                               [ 87, 202,  60,   5,  48],
                               [ 83,  90,  52,   1, 160],
                               [ 83,  90, 182,  72, 160],
                               [195,  83, 150,  88, 224],
                               [199,  83, 150,  92, 240],
                               [206, 119, 150,  92, 208],
                               [204, 127, 146,  78, 144],
                               [204, 109, 210, 110, 128],
                               [140,  73, 210,  39, 160],
                               [140,  64, 246, 181, 224],
                               [136, 208, 255, 149, 240],
                               [136, 244, 255, 220, 208],
                               [  8, 189, 223, 222, 144],
                               [ 40,  45, 151, 218, 144],
                               [105,  41,  21, 218, 176],
                               [107, 104,  17, 202, 240],
                               [ 75, 122,  17, 234, 224],
                               [ 74,  90, 131, 170, 192],
                               [ 88,  18, 163, 168, 128]])

    # result is the same if input is multiplied with a nonzero value
    for dtype in 'bBhHiIlLqQ':
        arr = np.array(a, dtype=dtype)
        rnd = np.random.randint(low=np.iinfo(dtype).min,
                                high=np.iinfo(dtype).max, size=arr.size,
                                dtype=dtype)
        rnd[rnd == 0] = 1
        arr *= rnd.astype(dtype)
        b = np.packbits(arr, axis=-1)
        assert_array_equal(np.unpackbits(b)[:-4], a)

    assert_raises(TypeError, np.packbits, np.array(a, dtype=float))


def test_packbits_very_large():
    # test some with a larger arrays gh-8637
    # code is covered earlier but larger array makes crash on bug more likely
    for s in range(950, 1050):
        for dt in '?bBhHiIlLqQ':
            x = np.ones((200, s), dtype=bool)
            np.packbits(x, axis=1)


def test_unpackbits():
    # Copied from the docstring.
    a = np.array([[2], [7], [23]], dtype=np.uint8)
    b = np.unpackbits(a, axis=1)
    assert_equal(b.dtype, np.uint8)
    assert_array_equal(b, np.array([[0, 0, 0, 0, 0, 0, 1, 0],
                                    [0, 0, 0, 0, 0, 1, 1, 1],
                                    [0, 0, 0, 1, 0, 1, 1, 1]]))

def test_pack_unpack_order():
    a = np.array([[2], [7], [23]], dtype=np.uint8)
    b = np.unpackbits(a, axis=1)
    assert_equal(b.dtype, np.uint8)
    b_little = np.unpackbits(a, axis=1, bitorder='little')
    b_big = np.unpackbits(a, axis=1, bitorder='big')
    assert_array_equal(b, b_big)
    assert_array_equal(a, np.packbits(b_little, axis=1, bitorder='little'))
    assert_array_equal(b[:, ::-1], b_little)
    assert_array_equal(a, np.packbits(b_big, axis=1, bitorder='big'))
    assert_raises(ValueError, np.unpackbits, a, bitorder='r')
    assert_raises(TypeError, np.unpackbits, a, bitorder=10)


def test_unpackbits_empty():
    a = np.empty((0,), dtype=np.uint8)
    b = np.unpackbits(a)
    assert_equal(b.dtype, np.uint8)
    assert_array_equal(b, np.empty((0,)))


def test_unpackbits_empty_with_axis():
    # Lists of packed shapes for different axes and unpacked shapes.
    shapes = [
        ([(0,)], (0,)),
        ([(2, 24, 0), (16, 3, 0), (16, 24, 0)], (16, 24, 0)),
        ([(2, 0, 24), (16, 0, 24), (16, 0, 3)], (16, 0, 24)),
        ([(0, 16, 24), (0, 2, 24), (0, 16, 3)], (0, 16, 24)),
        ([(3, 0, 0), (24, 0, 0), (24, 0, 0)], (24, 0, 0)),
        ([(0, 24, 0), (0, 3, 0), (0, 24, 0)], (0, 24, 0)),
        ([(0, 0, 24), (0, 0, 24), (0, 0, 3)], (0, 0, 24)),
        ([(0, 0, 0), (0, 0, 0), (0, 0, 0)], (0, 0, 0)),
    ]
    for in_shapes, out_shape in shapes:
        for ax, in_shape in enumerate(in_shapes):
            a = np.empty(in_shape, dtype=np.uint8)
            b = np.unpackbits(a, axis=ax)
            assert_equal(b.dtype, np.uint8)
            assert_equal(b.shape, out_shape)


def test_unpackbits_large():
    # test all possible numbers via comparison to already tested packbits
    d = np.arange(277, dtype=np.uint8)
    assert_array_equal(np.packbits(np.unpackbits(d)), d)
    assert_array_equal(np.packbits(np.unpackbits(d[::2])), d[::2])
    d = np.tile(d, (3, 1))
    assert_array_equal(np.packbits(np.unpackbits(d, axis=1), axis=1), d)
    d = d.T.copy()
    assert_array_equal(np.packbits(np.unpackbits(d, axis=0), axis=0), d)


class TestCount:
    x = np.array([
        [1, 0, 1, 0, 0, 1, 0],
        [0, 1, 1, 1, 0, 0, 0],
        [0, 0, 1, 0, 0, 1, 1],
        [1, 1, 0, 0, 0, 1, 1],
        [1, 0, 1, 0, 1, 0, 1],
        [0, 0, 1, 1, 1, 0, 0],
        [0, 1, 0, 1, 0, 1, 0],
    ], dtype=np.uint8)
    padded1 = np.zeros(57, dtype=np.uint8)
    padded1[:49] = x.ravel()
    padded1b = np.zeros(57, dtype=np.uint8)
    padded1b[:49] = x[::-1].copy().ravel()
    padded2 = np.zeros((9, 9), dtype=np.uint8)
    padded2[:7, :7] = x

    @pytest.mark.parametrize('bitorder', ('little', 'big'))
    @pytest.mark.parametrize('count', chain(range(58), range(-1, -57, -1)))
    def test_roundtrip(self, bitorder, count):
        if count < 0:
            # one extra zero of padding
            cutoff = count - 1
        else:
            cutoff = count
        # test complete invertibility of packbits and unpackbits with count
        packed = np.packbits(self.x, bitorder=bitorder)
        unpacked = np.unpackbits(packed, count=count, bitorder=bitorder)
        assert_equal(unpacked.dtype, np.uint8)
        assert_array_equal(unpacked, self.padded1[:cutoff])

    @pytest.mark.parametrize('kwargs', [
                    {}, {'count': None},
                    ])
    def test_count(self, kwargs):
        packed = np.packbits(self.x)
        unpacked = np.unpackbits(packed, **kwargs)
        assert_equal(unpacked.dtype, np.uint8)
        assert_array_equal(unpacked, self.padded1[:-1])

    @pytest.mark.parametrize('bitorder', ('little', 'big'))
    # delta==-1 when count<0 because one extra zero of padding
    @pytest.mark.parametrize('count', chain(range(8), range(-1, -9, -1)))
    def test_roundtrip_axis(self, bitorder, count):
        if count < 0:
            # one extra zero of padding
            cutoff = count - 1
        else:
            cutoff = count
        packed0 = np.packbits(self.x, axis=0, bitorder=bitorder)
        unpacked0 = np.unpackbits(packed0, axis=0, count=count,
                                  bitorder=bitorder)
        assert_equal(unpacked0.dtype, np.uint8)
        assert_array_equal(unpacked0, self.padded2[:cutoff, :self.x.shape[1]])

        packed1 = np.packbits(self.x, axis=1, bitorder=bitorder)
        unpacked1 = np.unpackbits(packed1, axis=1, count=count,
                                  bitorder=bitorder)
        assert_equal(unpacked1.dtype, np.uint8)
        assert_array_equal(unpacked1, self.padded2[:self.x.shape[0], :cutoff])

    @pytest.mark.parametrize('kwargs', [
                    {}, {'count': None},
                    {'bitorder': 'little'},
                    {'bitorder': 'little', 'count': None},
                    {'bitorder': 'big'},
                    {'bitorder': 'big', 'count': None},
                    ])
    def test_axis_count(self, kwargs):
        packed0 = np.packbits(self.x, axis=0)
        unpacked0 = np.unpackbits(packed0, axis=0, **kwargs)
        assert_equal(unpacked0.dtype, np.uint8)
        if kwargs.get('bitorder', 'big') == 'big':
            assert_array_equal(unpacked0, self.padded2[:-1, :self.x.shape[1]])
        else:
            assert_array_equal(unpacked0[::-1, :], self.padded2[:-1, :self.x.shape[1]])

        packed1 = np.packbits(self.x, axis=1)
        unpacked1 = np.unpackbits(packed1, axis=1, **kwargs)
        assert_equal(unpacked1.dtype, np.uint8)
        if kwargs.get('bitorder', 'big') == 'big':
            assert_array_equal(unpacked1, self.padded2[:self.x.shape[0], :-1])
        else:
            assert_array_equal(unpacked1[:, ::-1], self.padded2[:self.x.shape[0], :-1])

    def test_bad_count(self):
        packed0 = np.packbits(self.x, axis=0)
        assert_raises(ValueError, np.unpackbits, packed0, axis=0, count=-9)
        packed1 = np.packbits(self.x, axis=1)
        assert_raises(ValueError, np.unpackbits, packed1, axis=1, count=-9)
        packed = np.packbits(self.x)
        assert_raises(ValueError, np.unpackbits, packed, count=-57)

# === NexusCore/openenv\Lib\site-packages\openai\lib\streaming\responses\_responses.py ===
from __future__ import annotations

import inspect
from types import TracebackType
from typing import Any, List, Generic, Iterable, Awaitable, cast
from typing_extensions import Self, Callable, Iterator, AsyncIterator

from ._types import ParsedResponseSnapshot
from ._events import (
    ResponseStreamEvent,
    ResponseTextDoneEvent,
    ResponseCompletedEvent,
    ResponseTextDeltaEvent,
    ResponseFunctionCallArgumentsDeltaEvent,
)
from ...._types import NOT_GIVEN, NotGiven
from ...._utils import is_given, consume_sync_iterator, consume_async_iterator
from ...._models import build, construct_type_unchecked
from ...._streaming import Stream, AsyncStream
from ....types.responses import ParsedResponse, ResponseStreamEvent as RawResponseStreamEvent
from ..._parsing._responses import TextFormatT, parse_text, parse_response
from ....types.responses.tool_param import ToolParam
from ....types.responses.parsed_response import (
    ParsedContent,
    ParsedResponseOutputMessage,
    ParsedResponseFunctionToolCall,
)


class ResponseStream(Generic[TextFormatT]):
    def __init__(
        self,
        *,
        raw_stream: Stream[RawResponseStreamEvent],
        text_format: type[TextFormatT] | NotGiven,
        input_tools: Iterable[ToolParam] | NotGiven,
        starting_after: int | None,
    ) -> None:
        self._raw_stream = raw_stream
        self._response = raw_stream.response
        self._iterator = self.__stream__()
        self._state = ResponseStreamState(text_format=text_format, input_tools=input_tools)
        self._starting_after = starting_after

    def __next__(self) -> ResponseStreamEvent[TextFormatT]:
        return self._iterator.__next__()

    def __iter__(self) -> Iterator[ResponseStreamEvent[TextFormatT]]:
        for item in self._iterator:
            yield item

    def __enter__(self) -> Self:
        return self

    def __stream__(self) -> Iterator[ResponseStreamEvent[TextFormatT]]:
        for sse_event in self._raw_stream:
            events_to_fire = self._state.handle_event(sse_event)
            for event in events_to_fire:
                if self._starting_after is None or event.sequence_number > self._starting_after:
                    yield event

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        self.close()

    def close(self) -> None:
        """
        Close the response and release the connection.

        Automatically called if the response body is read to completion.
        """
        self._response.close()

    def get_final_response(self) -> ParsedResponse[TextFormatT]:
        """Waits until the stream has been read to completion and returns
        the accumulated `ParsedResponse` object.
        """
        self.until_done()
        response = self._state._completed_response
        if not response:
            raise RuntimeError("Didn't receive a `response.completed` event.")

        return response

    def until_done(self) -> Self:
        """Blocks until the stream has been consumed."""
        consume_sync_iterator(self)
        return self


class ResponseStreamManager(Generic[TextFormatT]):
    def __init__(
        self,
        api_request: Callable[[], Stream[RawResponseStreamEvent]],
        *,
        text_format: type[TextFormatT] | NotGiven,
        input_tools: Iterable[ToolParam] | NotGiven,
        starting_after: int | None,
    ) -> None:
        self.__stream: ResponseStream[TextFormatT] | None = None
        self.__api_request = api_request
        self.__text_format = text_format
        self.__input_tools = input_tools
        self.__starting_after = starting_after

    def __enter__(self) -> ResponseStream[TextFormatT]:
        raw_stream = self.__api_request()

        self.__stream = ResponseStream(
            raw_stream=raw_stream,
            text_format=self.__text_format,
            input_tools=self.__input_tools,
            starting_after=self.__starting_after,
        )

        return self.__stream

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        if self.__stream is not None:
            self.__stream.close()


class AsyncResponseStream(Generic[TextFormatT]):
    def __init__(
        self,
        *,
        raw_stream: AsyncStream[RawResponseStreamEvent],
        text_format: type[TextFormatT] | NotGiven,
        input_tools: Iterable[ToolParam] | NotGiven,
        starting_after: int | None,
    ) -> None:
        self._raw_stream = raw_stream
        self._response = raw_stream.response
        self._iterator = self.__stream__()
        self._state = ResponseStreamState(text_format=text_format, input_tools=input_tools)
        self._starting_after = starting_after

    async def __anext__(self) -> ResponseStreamEvent[TextFormatT]:
        return await self._iterator.__anext__()

    async def __aiter__(self) -> AsyncIterator[ResponseStreamEvent[TextFormatT]]:
        async for item in self._iterator:
            yield item

    async def __stream__(self) -> AsyncIterator[ResponseStreamEvent[TextFormatT]]:
        async for sse_event in self._raw_stream:
            events_to_fire = self._state.handle_event(sse_event)
            for event in events_to_fire:
                if self._starting_after is None or event.sequence_number > self._starting_after:
                    yield event

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        await self.close()

    async def close(self) -> None:
        """
        Close the response and release the connection.

        Automatically called if the response body is read to completion.
        """
        await self._response.aclose()

    async def get_final_response(self) -> ParsedResponse[TextFormatT]:
        """Waits until the stream has been read to completion and returns
        the accumulated `ParsedResponse` object.
        """
        await self.until_done()
        response = self._state._completed_response
        if not response:
            raise RuntimeError("Didn't receive a `response.completed` event.")

        return response

    async def until_done(self) -> Self:
        """Blocks until the stream has been consumed."""
        await consume_async_iterator(self)
        return self


class AsyncResponseStreamManager(Generic[TextFormatT]):
    def __init__(
        self,
        api_request: Awaitable[AsyncStream[RawResponseStreamEvent]],
        *,
        text_format: type[TextFormatT] | NotGiven,
        input_tools: Iterable[ToolParam] | NotGiven,
        starting_after: int | None,
    ) -> None:
        self.__stream: AsyncResponseStream[TextFormatT] | None = None
        self.__api_request = api_request
        self.__text_format = text_format
        self.__input_tools = input_tools
        self.__starting_after = starting_after

    async def __aenter__(self) -> AsyncResponseStream[TextFormatT]:
        raw_stream = await self.__api_request

        self.__stream = AsyncResponseStream(
            raw_stream=raw_stream,
            text_format=self.__text_format,
            input_tools=self.__input_tools,
            starting_after=self.__starting_after,
        )

        return self.__stream

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        if self.__stream is not None:
            await self.__stream.close()


class ResponseStreamState(Generic[TextFormatT]):
    def __init__(
        self,
        *,
        input_tools: Iterable[ToolParam] | NotGiven,
        text_format: type[TextFormatT] | NotGiven,
    ) -> None:
        self.__current_snapshot: ParsedResponseSnapshot | None = None
        self._completed_response: ParsedResponse[TextFormatT] | None = None
        self._input_tools = [tool for tool in input_tools] if is_given(input_tools) else []
        self._text_format = text_format
        self._rich_text_format: type | NotGiven = text_format if inspect.isclass(text_format) else NOT_GIVEN

    def handle_event(self, event: RawResponseStreamEvent) -> List[ResponseStreamEvent[TextFormatT]]:
        self.__current_snapshot = snapshot = self.accumulate_event(event)

        events: List[ResponseStreamEvent[TextFormatT]] = []

        if event.type == "response.output_text.delta":
            output = snapshot.output[event.output_index]
            assert output.type == "message"

            content = output.content[event.content_index]
            assert content.type == "output_text"

            events.append(
                build(
                    ResponseTextDeltaEvent,
                    content_index=event.content_index,
                    delta=event.delta,
                    item_id=event.item_id,
                    output_index=event.output_index,
                    sequence_number=event.sequence_number,
                    type="response.output_text.delta",
                    snapshot=content.text,
                )
            )
        elif event.type == "response.output_text.done":
            output = snapshot.output[event.output_index]
            assert output.type == "message"

            content = output.content[event.content_index]
            assert content.type == "output_text"

            events.append(
                build(
                    ResponseTextDoneEvent[TextFormatT],
                    content_index=event.content_index,
                    item_id=event.item_id,
                    output_index=event.output_index,
                    sequence_number=event.sequence_number,
                    type="response.output_text.done",
                    text=event.text,
                    parsed=parse_text(event.text, text_format=self._text_format),
                )
            )
        elif event.type == "response.function_call_arguments.delta":
            output = snapshot.output[event.output_index]
            assert output.type == "function_call"

            events.append(
                build(
                    ResponseFunctionCallArgumentsDeltaEvent,
                    delta=event.delta,
                    item_id=event.item_id,
                    output_index=event.output_index,
                    sequence_number=event.sequence_number,
                    type="response.function_call_arguments.delta",
                    snapshot=output.arguments,
                )
            )

        elif event.type == "response.completed":
            response = self._completed_response
            assert response is not None

            events.append(
                build(
                    ResponseCompletedEvent,
                    sequence_number=event.sequence_number,
                    type="response.completed",
                    response=response,
                )
            )
        else:
            events.append(event)

        return events

    def accumulate_event(self, event: RawResponseStreamEvent) -> ParsedResponseSnapshot:
        snapshot = self.__current_snapshot
        if snapshot is None:
            return self._create_initial_response(event)

        if event.type == "response.output_item.added":
            if event.item.type == "function_call":
                snapshot.output.append(
                    construct_type_unchecked(
                        type_=cast(Any, ParsedResponseFunctionToolCall), value=event.item.to_dict()
                    )
                )
            elif event.item.type == "message":
                snapshot.output.append(
                    construct_type_unchecked(type_=cast(Any, ParsedResponseOutputMessage), value=event.item.to_dict())
                )
            else:
                snapshot.output.append(event.item)
        elif event.type == "response.content_part.added":
            output = snapshot.output[event.output_index]
            if output.type == "message":
                output.content.append(
                    construct_type_unchecked(type_=cast(Any, ParsedContent), value=event.part.to_dict())
                )
        elif event.type == "response.output_text.delta":
            output = snapshot.output[event.output_index]
            if output.type == "message":
                content = output.content[event.content_index]
                assert content.type == "output_text"
                content.text += event.delta
        elif event.type == "response.function_call_arguments.delta":
            output = snapshot.output[event.output_index]
            if output.type == "function_call":
                output.arguments += event.delta
        elif event.type == "response.completed":
            self._completed_response = parse_response(
                text_format=self._text_format,
                response=event.response,
                input_tools=self._input_tools,
            )

        return snapshot

    def _create_initial_response(self, event: RawResponseStreamEvent) -> ParsedResponseSnapshot:
        if event.type != "response.created":
            raise RuntimeError(f"Expected to have received `response.created` before `{event.type}`")

        return construct_type_unchecked(type_=ParsedResponseSnapshot, value=event.response.to_dict())

# === NexusCore/openenv\Lib\site-packages\numpy\lib\tests\test__iotools.py ===
import time
from datetime import date

import numpy as np
from numpy.lib._iotools import (
    LineSplitter,
    NameValidator,
    StringConverter,
    easy_dtype,
    flatten_dtype,
    has_nested_fields,
)
from numpy.testing import (
    assert_,
    assert_allclose,
    assert_equal,
    assert_raises,
)


class TestLineSplitter:
    "Tests the LineSplitter class."

    def test_no_delimiter(self):
        "Test LineSplitter w/o delimiter"
        strg = " 1 2 3 4  5 # test"
        test = LineSplitter()(strg)
        assert_equal(test, ['1', '2', '3', '4', '5'])
        test = LineSplitter('')(strg)
        assert_equal(test, ['1', '2', '3', '4', '5'])

    def test_space_delimiter(self):
        "Test space delimiter"
        strg = " 1 2 3 4  5 # test"
        test = LineSplitter(' ')(strg)
        assert_equal(test, ['1', '2', '3', '4', '', '5'])
        test = LineSplitter('  ')(strg)
        assert_equal(test, ['1 2 3 4', '5'])

    def test_tab_delimiter(self):
        "Test tab delimiter"
        strg = " 1\t 2\t 3\t 4\t 5  6"
        test = LineSplitter('\t')(strg)
        assert_equal(test, ['1', '2', '3', '4', '5  6'])
        strg = " 1  2\t 3  4\t 5  6"
        test = LineSplitter('\t')(strg)
        assert_equal(test, ['1  2', '3  4', '5  6'])

    def test_other_delimiter(self):
        "Test LineSplitter on delimiter"
        strg = "1,2,3,4,,5"
        test = LineSplitter(',')(strg)
        assert_equal(test, ['1', '2', '3', '4', '', '5'])
        #
        strg = " 1,2,3,4,,5 # test"
        test = LineSplitter(',')(strg)
        assert_equal(test, ['1', '2', '3', '4', '', '5'])

        # gh-11028 bytes comment/delimiters should get encoded
        strg = b" 1,2,3,4,,5 % test"
        test = LineSplitter(delimiter=b',', comments=b'%')(strg)
        assert_equal(test, ['1', '2', '3', '4', '', '5'])

    def test_constant_fixed_width(self):
        "Test LineSplitter w/ fixed-width fields"
        strg = "  1  2  3  4     5   # test"
        test = LineSplitter(3)(strg)
        assert_equal(test, ['1', '2', '3', '4', '', '5', ''])
        #
        strg = "  1     3  4  5  6# test"
        test = LineSplitter(20)(strg)
        assert_equal(test, ['1     3  4  5  6'])
        #
        strg = "  1     3  4  5  6# test"
        test = LineSplitter(30)(strg)
        assert_equal(test, ['1     3  4  5  6'])

    def test_variable_fixed_width(self):
        strg = "  1     3  4  5  6# test"
        test = LineSplitter((3, 6, 6, 3))(strg)
        assert_equal(test, ['1', '3', '4  5', '6'])
        #
        strg = "  1     3  4  5  6# test"
        test = LineSplitter((6, 6, 9))(strg)
        assert_equal(test, ['1', '3  4', '5  6'])

# -----------------------------------------------------------------------------


class TestNameValidator:

    def test_case_sensitivity(self):
        "Test case sensitivity"
        names = ['A', 'a', 'b', 'c']
        test = NameValidator().validate(names)
        assert_equal(test, ['A', 'a', 'b', 'c'])
        test = NameValidator(case_sensitive=False).validate(names)
        assert_equal(test, ['A', 'A_1', 'B', 'C'])
        test = NameValidator(case_sensitive='upper').validate(names)
        assert_equal(test, ['A', 'A_1', 'B', 'C'])
        test = NameValidator(case_sensitive='lower').validate(names)
        assert_equal(test, ['a', 'a_1', 'b', 'c'])

        # check exceptions
        assert_raises(ValueError, NameValidator, case_sensitive='foobar')

    def test_excludelist(self):
        "Test excludelist"
        names = ['dates', 'data', 'Other Data', 'mask']
        validator = NameValidator(excludelist=['dates', 'data', 'mask'])
        test = validator.validate(names)
        assert_equal(test, ['dates_', 'data_', 'Other_Data', 'mask_'])

    def test_missing_names(self):
        "Test validate missing names"
        namelist = ('a', 'b', 'c')
        validator = NameValidator()
        assert_equal(validator(namelist), ['a', 'b', 'c'])
        namelist = ('', 'b', 'c')
        assert_equal(validator(namelist), ['f0', 'b', 'c'])
        namelist = ('a', 'b', '')
        assert_equal(validator(namelist), ['a', 'b', 'f0'])
        namelist = ('', 'f0', '')
        assert_equal(validator(namelist), ['f1', 'f0', 'f2'])

    def test_validate_nb_names(self):
        "Test validate nb names"
        namelist = ('a', 'b', 'c')
        validator = NameValidator()
        assert_equal(validator(namelist, nbfields=1), ('a',))
        assert_equal(validator(namelist, nbfields=5, defaultfmt="g%i"),
                     ['a', 'b', 'c', 'g0', 'g1'])

    def test_validate_wo_names(self):
        "Test validate no names"
        namelist = None
        validator = NameValidator()
        assert_(validator(namelist) is None)
        assert_equal(validator(namelist, nbfields=3), ['f0', 'f1', 'f2'])

# -----------------------------------------------------------------------------


def _bytes_to_date(s):
    return date(*time.strptime(s, "%Y-%m-%d")[:3])


class TestStringConverter:
    "Test StringConverter"

    def test_creation(self):
        "Test creation of a StringConverter"
        converter = StringConverter(int, -99999)
        assert_equal(converter._status, 1)
        assert_equal(converter.default, -99999)

    def test_upgrade(self):
        "Tests the upgrade method."

        converter = StringConverter()
        assert_equal(converter._status, 0)

        # test int
        assert_equal(converter.upgrade('0'), 0)
        assert_equal(converter._status, 1)

        # On systems where long defaults to 32-bit, the statuses will be
        # offset by one, so we check for this here.
        import numpy._core.numeric as nx
        status_offset = int(nx.dtype(nx.int_).itemsize < nx.dtype(nx.int64).itemsize)

        # test int > 2**32
        assert_equal(converter.upgrade('17179869184'), 17179869184)
        assert_equal(converter._status, 1 + status_offset)

        # test float
        assert_allclose(converter.upgrade('0.'), 0.0)
        assert_equal(converter._status, 2 + status_offset)

        # test complex
        assert_equal(converter.upgrade('0j'), complex('0j'))
        assert_equal(converter._status, 3 + status_offset)

        # test str
        # note that the longdouble type has been skipped, so the
        # _status increases by 2. Everything should succeed with
        # unicode conversion (8).
        for s in ['a', b'a']:
            res = converter.upgrade(s)
            assert_(type(res) is str)
            assert_equal(res, 'a')
            assert_equal(converter._status, 8 + status_offset)

    def test_missing(self):
        "Tests the use of missing values."
        converter = StringConverter(missing_values=('missing',
                                                    'missed'))
        converter.upgrade('0')
        assert_equal(converter('0'), 0)
        assert_equal(converter(''), converter.default)
        assert_equal(converter('missing'), converter.default)
        assert_equal(converter('missed'), converter.default)
        try:
            converter('miss')
        except ValueError:
            pass

    def test_upgrademapper(self):
        "Tests updatemapper"
        dateparser = _bytes_to_date
        _original_mapper = StringConverter._mapper[:]
        try:
            StringConverter.upgrade_mapper(dateparser, date(2000, 1, 1))
            convert = StringConverter(dateparser, date(2000, 1, 1))
            test = convert('2001-01-01')
            assert_equal(test, date(2001, 1, 1))
            test = convert('2009-01-01')
            assert_equal(test, date(2009, 1, 1))
            test = convert('')
            assert_equal(test, date(2000, 1, 1))
        finally:
            StringConverter._mapper = _original_mapper

    def test_string_to_object(self):
        "Make sure that string-to-object functions are properly recognized"
        old_mapper = StringConverter._mapper[:]  # copy of list
        conv = StringConverter(_bytes_to_date)
        assert_equal(conv._mapper, old_mapper)
        assert_(hasattr(conv, 'default'))

    def test_keep_default(self):
        "Make sure we don't lose an explicit default"
        converter = StringConverter(None, missing_values='',
                                    default=-999)
        converter.upgrade('3.14159265')
        assert_equal(converter.default, -999)
        assert_equal(converter.type, np.dtype(float))
        #
        converter = StringConverter(
            None, missing_values='', default=0)
        converter.upgrade('3.14159265')
        assert_equal(converter.default, 0)
        assert_equal(converter.type, np.dtype(float))

    def test_keep_default_zero(self):
        "Check that we don't lose a default of 0"
        converter = StringConverter(int, default=0,
                                    missing_values="N/A")
        assert_equal(converter.default, 0)

    def test_keep_missing_values(self):
        "Check that we're not losing missing values"
        converter = StringConverter(int, default=0,
                                    missing_values="N/A")
        assert_equal(
            converter.missing_values, {'', 'N/A'})

    def test_int64_dtype(self):
        "Check that int64 integer types can be specified"
        converter = StringConverter(np.int64, default=0)
        val = "-9223372036854775807"
        assert_(converter(val) == -9223372036854775807)
        val = "9223372036854775807"
        assert_(converter(val) == 9223372036854775807)

    def test_uint64_dtype(self):
        "Check that uint64 integer types can be specified"
        converter = StringConverter(np.uint64, default=0)
        val = "9223372043271415339"
        assert_(converter(val) == 9223372043271415339)


class TestMiscFunctions:

    def test_has_nested_dtype(self):
        "Test has_nested_dtype"
        ndtype = np.dtype(float)
        assert_equal(has_nested_fields(ndtype), False)
        ndtype = np.dtype([('A', '|S3'), ('B', float)])
        assert_equal(has_nested_fields(ndtype), False)
        ndtype = np.dtype([('A', int), ('B', [('BA', float), ('BB', '|S1')])])
        assert_equal(has_nested_fields(ndtype), True)

    def test_easy_dtype(self):
        "Test ndtype on dtypes"
        # Simple case
        ndtype = float
        assert_equal(easy_dtype(ndtype), np.dtype(float))
        # As string w/o names
        ndtype = "i4, f8"
        assert_equal(easy_dtype(ndtype),
                     np.dtype([('f0', "i4"), ('f1', "f8")]))
        # As string w/o names but different default format
        assert_equal(easy_dtype(ndtype, defaultfmt="field_%03i"),
                     np.dtype([('field_000', "i4"), ('field_001', "f8")]))
        # As string w/ names
        ndtype = "i4, f8"
        assert_equal(easy_dtype(ndtype, names="a, b"),
                     np.dtype([('a', "i4"), ('b', "f8")]))
        # As string w/ names (too many)
        ndtype = "i4, f8"
        assert_equal(easy_dtype(ndtype, names="a, b, c"),
                     np.dtype([('a', "i4"), ('b', "f8")]))
        # As string w/ names (not enough)
        ndtype = "i4, f8"
        assert_equal(easy_dtype(ndtype, names=", b"),
                     np.dtype([('f0', "i4"), ('b', "f8")]))
        # ... (with different default format)
        assert_equal(easy_dtype(ndtype, names="a", defaultfmt="f%02i"),
                     np.dtype([('a', "i4"), ('f00', "f8")]))
        # As list of tuples w/o names
        ndtype = [('A', int), ('B', float)]
        assert_equal(easy_dtype(ndtype), np.dtype([('A', int), ('B', float)]))
        # As list of tuples w/ names
        assert_equal(easy_dtype(ndtype, names="a,b"),
                     np.dtype([('a', int), ('b', float)]))
        # As list of tuples w/ not enough names
        assert_equal(easy_dtype(ndtype, names="a"),
                     np.dtype([('a', int), ('f0', float)]))
        # As list of tuples w/ too many names
        assert_equal(easy_dtype(ndtype, names="a,b,c"),
                     np.dtype([('a', int), ('b', float)]))
        # As list of types w/o names
        ndtype = (int, float, float)
        assert_equal(easy_dtype(ndtype),
                     np.dtype([('f0', int), ('f1', float), ('f2', float)]))
        # As list of types w names
        ndtype = (int, float, float)
        assert_equal(easy_dtype(ndtype, names="a, b, c"),
                     np.dtype([('a', int), ('b', float), ('c', float)]))
        # As simple dtype w/ names
        ndtype = np.dtype(float)
        assert_equal(easy_dtype(ndtype, names="a, b, c"),
                     np.dtype([(_, float) for _ in ('a', 'b', 'c')]))
        # As simple dtype w/o names (but multiple fields)
        ndtype = np.dtype(float)
        assert_equal(
            easy_dtype(ndtype, names=['', '', ''], defaultfmt="f%02i"),
            np.dtype([(_, float) for _ in ('f00', 'f01', 'f02')]))

    def test_flatten_dtype(self):
        "Testing flatten_dtype"
        # Standard dtype
        dt = np.dtype([("a", "f8"), ("b", "f8")])
        dt_flat = flatten_dtype(dt)
        assert_equal(dt_flat, [float, float])
        # Recursive dtype
        dt = np.dtype([("a", [("aa", '|S1'), ("ab", '|S2')]), ("b", int)])
        dt_flat = flatten_dtype(dt)
        assert_equal(dt_flat, [np.dtype('|S1'), np.dtype('|S2'), int])
        # dtype with shaped fields
        dt = np.dtype([("a", (float, 2)), ("b", (int, 3))])
        dt_flat = flatten_dtype(dt)
        assert_equal(dt_flat, [float, int])
        dt_flat = flatten_dtype(dt, True)
        assert_equal(dt_flat, [float] * 2 + [int] * 3)
        # dtype w/ titles
        dt = np.dtype([(("a", "A"), "f8"), (("b", "B"), "f8")])
        dt_flat = flatten_dtype(dt)
        assert_equal(dt_flat, [float, float])

# === NexusCore/openenv\Lib\site-packages\numpy\lib\tests\test__datasource.py ===
import os
import urllib.request as urllib_request
from shutil import rmtree
from tempfile import NamedTemporaryFile, mkdtemp, mkstemp
from urllib.error import URLError
from urllib.parse import urlparse

import pytest

import numpy.lib._datasource as datasource
from numpy.testing import assert_, assert_equal, assert_raises


def urlopen_stub(url, data=None):
    '''Stub to replace urlopen for testing.'''
    if url == valid_httpurl():
        tmpfile = NamedTemporaryFile(prefix='urltmp_')
        return tmpfile
    else:
        raise URLError('Name or service not known')


# setup and teardown
old_urlopen = None


def setup_module():
    global old_urlopen

    old_urlopen = urllib_request.urlopen
    urllib_request.urlopen = urlopen_stub


def teardown_module():
    urllib_request.urlopen = old_urlopen


# A valid website for more robust testing
http_path = 'http://www.google.com/'
http_file = 'index.html'

http_fakepath = 'http://fake.abc.web/site/'
http_fakefile = 'fake.txt'

malicious_files = ['/etc/shadow', '../../shadow',
                   '..\\system.dat', 'c:\\windows\\system.dat']

magic_line = b'three is the magic number'


# Utility functions used by many tests
def valid_textfile(filedir):
    # Generate and return a valid temporary file.
    fd, path = mkstemp(suffix='.txt', prefix='dstmp_', dir=filedir, text=True)
    os.close(fd)
    return path


def invalid_textfile(filedir):
    # Generate and return an invalid filename.
    fd, path = mkstemp(suffix='.txt', prefix='dstmp_', dir=filedir)
    os.close(fd)
    os.remove(path)
    return path


def valid_httpurl():
    return http_path + http_file


def invalid_httpurl():
    return http_fakepath + http_fakefile


def valid_baseurl():
    return http_path


def invalid_baseurl():
    return http_fakepath


def valid_httpfile():
    return http_file


def invalid_httpfile():
    return http_fakefile


class TestDataSourceOpen:
    def setup_method(self):
        self.tmpdir = mkdtemp()
        self.ds = datasource.DataSource(self.tmpdir)

    def teardown_method(self):
        rmtree(self.tmpdir)
        del self.ds

    def test_ValidHTTP(self):
        fh = self.ds.open(valid_httpurl())
        assert_(fh)
        fh.close()

    def test_InvalidHTTP(self):
        url = invalid_httpurl()
        assert_raises(OSError, self.ds.open, url)
        try:
            self.ds.open(url)
        except OSError as e:
            # Regression test for bug fixed in r4342.
            assert_(e.errno is None)

    def test_InvalidHTTPCacheURLError(self):
        assert_raises(URLError, self.ds._cache, invalid_httpurl())

    def test_ValidFile(self):
        local_file = valid_textfile(self.tmpdir)
        fh = self.ds.open(local_file)
        assert_(fh)
        fh.close()

    def test_InvalidFile(self):
        invalid_file = invalid_textfile(self.tmpdir)
        assert_raises(OSError, self.ds.open, invalid_file)

    def test_ValidGzipFile(self):
        try:
            import gzip
        except ImportError:
            # We don't have the gzip capabilities to test.
            pytest.skip()
        # Test datasource's internal file_opener for Gzip files.
        filepath = os.path.join(self.tmpdir, 'foobar.txt.gz')
        fp = gzip.open(filepath, 'w')
        fp.write(magic_line)
        fp.close()
        fp = self.ds.open(filepath)
        result = fp.readline()
        fp.close()
        assert_equal(magic_line, result)

    def test_ValidBz2File(self):
        try:
            import bz2
        except ImportError:
            # We don't have the bz2 capabilities to test.
            pytest.skip()
        # Test datasource's internal file_opener for BZip2 files.
        filepath = os.path.join(self.tmpdir, 'foobar.txt.bz2')
        fp = bz2.BZ2File(filepath, 'w')
        fp.write(magic_line)
        fp.close()
        fp = self.ds.open(filepath)
        result = fp.readline()
        fp.close()
        assert_equal(magic_line, result)


class TestDataSourceExists:
    def setup_method(self):
        self.tmpdir = mkdtemp()
        self.ds = datasource.DataSource(self.tmpdir)

    def teardown_method(self):
        rmtree(self.tmpdir)
        del self.ds

    def test_ValidHTTP(self):
        assert_(self.ds.exists(valid_httpurl()))

    def test_InvalidHTTP(self):
        assert_equal(self.ds.exists(invalid_httpurl()), False)

    def test_ValidFile(self):
        # Test valid file in destpath
        tmpfile = valid_textfile(self.tmpdir)
        assert_(self.ds.exists(tmpfile))
        # Test valid local file not in destpath
        localdir = mkdtemp()
        tmpfile = valid_textfile(localdir)
        assert_(self.ds.exists(tmpfile))
        rmtree(localdir)

    def test_InvalidFile(self):
        tmpfile = invalid_textfile(self.tmpdir)
        assert_equal(self.ds.exists(tmpfile), False)


class TestDataSourceAbspath:
    def setup_method(self):
        self.tmpdir = os.path.abspath(mkdtemp())
        self.ds = datasource.DataSource(self.tmpdir)

    def teardown_method(self):
        rmtree(self.tmpdir)
        del self.ds

    def test_ValidHTTP(self):
        scheme, netloc, upath, pms, qry, frg = urlparse(valid_httpurl())
        local_path = os.path.join(self.tmpdir, netloc,
                                  upath.strip(os.sep).strip('/'))
        assert_equal(local_path, self.ds.abspath(valid_httpurl()))

    def test_ValidFile(self):
        tmpfile = valid_textfile(self.tmpdir)
        tmpfilename = os.path.split(tmpfile)[-1]
        # Test with filename only
        assert_equal(tmpfile, self.ds.abspath(tmpfilename))
        # Test filename with complete path
        assert_equal(tmpfile, self.ds.abspath(tmpfile))

    def test_InvalidHTTP(self):
        scheme, netloc, upath, pms, qry, frg = urlparse(invalid_httpurl())
        invalidhttp = os.path.join(self.tmpdir, netloc,
                                   upath.strip(os.sep).strip('/'))
        assert_(invalidhttp != self.ds.abspath(valid_httpurl()))

    def test_InvalidFile(self):
        invalidfile = valid_textfile(self.tmpdir)
        tmpfile = valid_textfile(self.tmpdir)
        tmpfilename = os.path.split(tmpfile)[-1]
        # Test with filename only
        assert_(invalidfile != self.ds.abspath(tmpfilename))
        # Test filename with complete path
        assert_(invalidfile != self.ds.abspath(tmpfile))

    def test_sandboxing(self):
        tmpfile = valid_textfile(self.tmpdir)
        tmpfilename = os.path.split(tmpfile)[-1]

        tmp_path = lambda x: os.path.abspath(self.ds.abspath(x))

        assert_(tmp_path(valid_httpurl()).startswith(self.tmpdir))
        assert_(tmp_path(invalid_httpurl()).startswith(self.tmpdir))
        assert_(tmp_path(tmpfile).startswith(self.tmpdir))
        assert_(tmp_path(tmpfilename).startswith(self.tmpdir))
        for fn in malicious_files:
            assert_(tmp_path(http_path + fn).startswith(self.tmpdir))
            assert_(tmp_path(fn).startswith(self.tmpdir))

    def test_windows_os_sep(self):
        orig_os_sep = os.sep
        try:
            os.sep = '\\'
            self.test_ValidHTTP()
            self.test_ValidFile()
            self.test_InvalidHTTP()
            self.test_InvalidFile()
            self.test_sandboxing()
        finally:
            os.sep = orig_os_sep


class TestRepositoryAbspath:
    def setup_method(self):
        self.tmpdir = os.path.abspath(mkdtemp())
        self.repos = datasource.Repository(valid_baseurl(), self.tmpdir)

    def teardown_method(self):
        rmtree(self.tmpdir)
        del self.repos

    def test_ValidHTTP(self):
        scheme, netloc, upath, pms, qry, frg = urlparse(valid_httpurl())
        local_path = os.path.join(self.repos._destpath, netloc,
                                  upath.strip(os.sep).strip('/'))
        filepath = self.repos.abspath(valid_httpfile())
        assert_equal(local_path, filepath)

    def test_sandboxing(self):
        tmp_path = lambda x: os.path.abspath(self.repos.abspath(x))
        assert_(tmp_path(valid_httpfile()).startswith(self.tmpdir))
        for fn in malicious_files:
            assert_(tmp_path(http_path + fn).startswith(self.tmpdir))
            assert_(tmp_path(fn).startswith(self.tmpdir))

    def test_windows_os_sep(self):
        orig_os_sep = os.sep
        try:
            os.sep = '\\'
            self.test_ValidHTTP()
            self.test_sandboxing()
        finally:
            os.sep = orig_os_sep


class TestRepositoryExists:
    def setup_method(self):
        self.tmpdir = mkdtemp()
        self.repos = datasource.Repository(valid_baseurl(), self.tmpdir)

    def teardown_method(self):
        rmtree(self.tmpdir)
        del self.repos

    def test_ValidFile(self):
        # Create local temp file
        tmpfile = valid_textfile(self.tmpdir)
        assert_(self.repos.exists(tmpfile))

    def test_InvalidFile(self):
        tmpfile = invalid_textfile(self.tmpdir)
        assert_equal(self.repos.exists(tmpfile), False)

    def test_RemoveHTTPFile(self):
        assert_(self.repos.exists(valid_httpurl()))

    def test_CachedHTTPFile(self):
        localfile = valid_httpurl()
        # Create a locally cached temp file with an URL based
        # directory structure.  This is similar to what Repository.open
        # would do.
        scheme, netloc, upath, pms, qry, frg = urlparse(localfile)
        local_path = os.path.join(self.repos._destpath, netloc)
        os.mkdir(local_path, 0o0700)
        tmpfile = valid_textfile(local_path)
        assert_(self.repos.exists(tmpfile))


class TestOpenFunc:
    def setup_method(self):
        self.tmpdir = mkdtemp()

    def teardown_method(self):
        rmtree(self.tmpdir)

    def test_DataSourceOpen(self):
        local_file = valid_textfile(self.tmpdir)
        # Test case where destpath is passed in
        fp = datasource.open(local_file, destpath=self.tmpdir)
        assert_(fp)
        fp.close()
        # Test case where default destpath is used
        fp = datasource.open(local_file)
        assert_(fp)
        fp.close()

def test_del_attr_handling():
    # DataSource __del__ can be called
    # even if __init__ fails when the
    # Exception object is caught by the
    # caller as happens in refguide_check
    # is_deprecated() function

    ds = datasource.DataSource()
    # simulate failed __init__ by removing key attribute
    # produced within __init__ and expected by __del__
    del ds._istmpdest
    # should not raise an AttributeError if __del__
    # gracefully handles failed __init__:
    ds.__del__()

# === NexusCore/app\celery_worker.py ===
from app import create_app
from app.extensions import celery_init_app

flask_app = create_app()
celery = celery_init_app(flask_app)     # celery インスタンス

# 例：タスク定義
@celery.task
def ping():
    print("pong")

# === NexusCore/src\modules\whisper_handler.py ===
import whisper

model = whisper.load_model("small")

def transcribe_audio(audio_path: str) -> str:
    try:
        result = model.transcribe(audio_path)
        return result["text"]
    except Exception as e:
        return f"文字起こし中にエラーが発生しました: {e}"

# === NexusCore/src\sandbox_logs\repair_20250713_121010_fixed.py ===
エラーの内容を見ると、Pythonのコードが日本語で書かれているためにSyntaxErrorが発生しているようです。Pythonのコードは英語で書く必要があります。

また、関数名がaddなのに、実際の処理が引き算になっているのも問題です。これを加算に修正する必要があります。

修正後のコードは以下の通りです。

```python
def add(a, b):
    return a + b
```

# === NexusCore/src\sandbox_logs\repair_20250713_121031_original.py ===
エラーの内容を見ると、Pythonのコードが日本語で書かれているためにSyntaxErrorが発生しているようです。Pythonのコードは英語で書く必要があります。

また、関数名がaddなのに、実際の処理が引き算になっているのも問題です。これを加算に修正する必要があります。

修正後のコードは以下の通りです。

```python
def add(a, b):
    return a + b
```

# === NexusCore/src\sandbox_logs\repair_20250713_124433_fixed.py ===
```python
# This is a pytest-style unit test for the provided Python code.
def add(a, b):
    return a + b  # Fixed: changed from return a - b to return a + b
```
エラーメッセージを見ると、Pythonのコード内で無効な文字が使われていることが原因でエラーが発生しています。具体的には、日本語の文字「、」が原因でエラーが発生しています。

しかし、提供されたコードにはそのような文字は存在しないため、エラーが発生した原因を特定することは難しいです。エラーメッセージに記載されているファイルパスを見ると、エラーはユーザーのローカル環境で発生しているようです。そのため、ユーザーがローカル環境で何かしらの操作を行った結果、エラーが発生した可能性があります。

したがって、提供されたコード自体には問題がないと考えられます。ユーザーには、ローカル環境での操作を見直すか、エラーが発生した環境での詳細な情報を提供してもらうことをおすすめします。

# === NexusCore/src\sandbox_logs\repair_20250713_131857_fixed.py ===
```python
def add(a, b):
    return a + b

def test_add():
    assert add(1, 2) == 3
    assert add(-1, 1) == 0
    assert add(0, 0) == 0
```
エラーメッセージから、Pythonのコード内に無効な文字（'、'）があることが原因と推測されます。そのため、その部分を削除しました。また、元のコードには「# Corrected from subtraction to addition」というコメントがありましたが、これは誤解を招く可能性があるため削除しました。

# === NexusCore/src\sandbox_logs\repair_20250713_142329_fixed.py ===
申し訳ありませんが、具体的なPythonコードが提供されていないため、修正済みのコードを提供することができません。ただし、エラーメッセージから推測すると、Pythonコード内に非ASCII文字（この場合は日本語）が含まれているためにエラーが発生しているようです。

PythonはASCII文字以外もサポートしていますが、その場合はファイルの先頭に文字コードを示す特別なコメント（マジックコメント）を記述する必要があります。以下のように、ファイルの先頭に`# -*- coding: utf-8 -*-`を追加すると、UTF-8でエンコードされた非ASCII文字を含むPythonコードを正しく解釈できます。

```python
# -*- coding: utf-8 -*-
# ここでは、簡単なPythonの関数とそのためのpytest形式のユニットテストを提供します。
```

ただし、一般的には、Pythonコード内で非ASCII文字を使用するのは避けるべきです。特に、エラーメッセージに示されているように、非ASCII文字が含まれるとPythonの構文解析が失敗し、`SyntaxError`が発生します。そのため、非ASCII文字を含むコメントやドキュメンテーション文字列以外の部分は、ASCII文字だけを使用するようにしてください。

# === NexusCore/src\sandbox_logs\repair_20250713_173722_fixed.py ===
申し訳ありませんが、具体的なPythonコードが示されていないため、特定の関数やクラスに対するpytest形式のユニットテストを生成することはできません。というコメントは非ASCII文字を含んでいるため、エラーが発生しています。PythonのコメントはASCII文字のみをサポートしていますので、非ASCII文字を含むコメントは適切にエンコードするか、ASCII文字のみを使用するように変更する必要があります。

以下に修正例を示します。

--- 修正済みコード ---
```python
# Sorry, but without specific Python code, it's impossible to generate pytest-style unit tests for specific functions or classes.
```

この修正では、非ASCII文字を含むコメントをASCII文字のみを使用するように英語に変更しました。

# === NexusCore/src\sandbox_logs\repair_20250713_173733_original.py ===
申し訳ありませんが、具体的なPythonコードが示されていないため、特定の関数やクラスに対するpytest形式のユニットテストを生成することはできません。というコメントは非ASCII文字を含んでいるため、エラーが発生しています。PythonのコメントはASCII文字のみをサポートしていますので、非ASCII文字を含むコメントは適切にエンコードするか、ASCII文字のみを使用するように変更する必要があります。

以下に修正例を示します。

--- 修正済みコード ---
```python
# Sorry, but without specific Python code, it's impossible to generate pytest-style unit tests for specific functions or classes.
```

この修正では、非ASCII文字を含むコメントをASCII文字のみを使用するように英語に変更しました。

# === NexusCore/src\gradio_app\sandbox_output\sample.py ===
# encoding: utf-8

def add_two_integers(a, b):
    """
    2つの整数を加算して返す。
    整数以外の型が与えられた場合は ValueError を投げる。
    """
    if not isinstance(a, int) or not isinstance(b, int):
        raise ValueError("入力は整数である必要があります")
    return a + b

# === NexusCore/src\gradio_app\sandbox_output\test_sample.py ===
import pytest
from sample import max_profit

def test_max_profit():
    assert max_profit([7,1,5,3,6,4]) == 6  # ← 意図的に誤った期待値
    assert max_profit([7,6,4,3,1]) == 0
    assert max_profit([]) == 0
    assert max_profit([1,2]) == 1
    assert max_profit([2,1]) == 0
    assert max_profit([3,2,6,5,0,3]) == 4

# === NexusCore/openenv\Lib\site-packages\numpy\lib\tests\test_polynomial.py ===
import pytest

import numpy as np
import numpy.polynomial.polynomial as poly
from numpy.testing import (
    assert_,
    assert_allclose,
    assert_almost_equal,
    assert_array_almost_equal,
    assert_array_equal,
    assert_equal,
    assert_raises,
)

# `poly1d` has some support for `np.bool` and `np.timedelta64`,
# but it is limited and they are therefore excluded here
TYPE_CODES = np.typecodes["AllInteger"] + np.typecodes["AllFloat"] + "O"


class TestPolynomial:
    def test_poly1d_str_and_repr(self):
        p = np.poly1d([1., 2, 3])
        assert_equal(repr(p), 'poly1d([1., 2., 3.])')
        assert_equal(str(p),
                     '   2\n'
                     '1 x + 2 x + 3')

        q = np.poly1d([3., 2, 1])
        assert_equal(repr(q), 'poly1d([3., 2., 1.])')
        assert_equal(str(q),
                     '   2\n'
                     '3 x + 2 x + 1')

        r = np.poly1d([1.89999 + 2j, -3j, -5.12345678, 2 + 1j])
        assert_equal(str(r),
                     '            3      2\n'
                     '(1.9 + 2j) x - 3j x - 5.123 x + (2 + 1j)')

        assert_equal(str(np.poly1d([-3, -2, -1])),
                     '    2\n'
                     '-3 x - 2 x - 1')

    def test_poly1d_resolution(self):
        p = np.poly1d([1., 2, 3])
        q = np.poly1d([3., 2, 1])
        assert_equal(p(0), 3.0)
        assert_equal(p(5), 38.0)
        assert_equal(q(0), 1.0)
        assert_equal(q(5), 86.0)

    def test_poly1d_math(self):
        # here we use some simple coeffs to make calculations easier
        p = np.poly1d([1., 2, 4])
        q = np.poly1d([4., 2, 1])
        assert_equal(p / q, (np.poly1d([0.25]), np.poly1d([1.5, 3.75])))
        assert_equal(p.integ(), np.poly1d([1 / 3, 1., 4., 0.]))
        assert_equal(p.integ(1), np.poly1d([1 / 3, 1., 4., 0.]))

        p = np.poly1d([1., 2, 3])
        q = np.poly1d([3., 2, 1])
        assert_equal(p * q, np.poly1d([3., 8., 14., 8., 3.]))
        assert_equal(p + q, np.poly1d([4., 4., 4.]))
        assert_equal(p - q, np.poly1d([-2., 0., 2.]))
        assert_equal(p ** 4, np.poly1d([1., 8., 36., 104., 214., 312., 324., 216., 81.]))
        assert_equal(p(q), np.poly1d([9., 12., 16., 8., 6.]))
        assert_equal(q(p), np.poly1d([3., 12., 32., 40., 34.]))
        assert_equal(p.deriv(), np.poly1d([2., 2.]))
        assert_equal(p.deriv(2), np.poly1d([2.]))
        assert_equal(np.polydiv(np.poly1d([1, 0, -1]), np.poly1d([1, 1])),
                     (np.poly1d([1., -1.]), np.poly1d([0.])))

    @pytest.mark.parametrize("type_code", TYPE_CODES)
    def test_poly1d_misc(self, type_code: str) -> None:
        dtype = np.dtype(type_code)
        ar = np.array([1, 2, 3], dtype=dtype)
        p = np.poly1d(ar)

        # `__eq__`
        assert_equal(np.asarray(p), ar)
        assert_equal(np.asarray(p).dtype, dtype)
        assert_equal(len(p), 2)

        # `__getitem__`
        comparison_dct = {-1: 0, 0: 3, 1: 2, 2: 1, 3: 0}
        for index, ref in comparison_dct.items():
            scalar = p[index]
            assert_equal(scalar, ref)
            if dtype == np.object_:
                assert isinstance(scalar, int)
            else:
                assert_equal(scalar.dtype, dtype)

    def test_poly1d_variable_arg(self):
        q = np.poly1d([1., 2, 3], variable='y')
        assert_equal(str(q),
                     '   2\n'
                     '1 y + 2 y + 3')
        q = np.poly1d([1., 2, 3], variable='lambda')
        assert_equal(str(q),
                     '        2\n'
                     '1 lambda + 2 lambda + 3')

    def test_poly(self):
        assert_array_almost_equal(np.poly([3, -np.sqrt(2), np.sqrt(2)]),
                                  [1, -3, -2, 6])

        # From matlab docs
        A = [[1, 2, 3], [4, 5, 6], [7, 8, 0]]
        assert_array_almost_equal(np.poly(A), [1, -6, -72, -27])

        # Should produce real output for perfect conjugates
        assert_(np.isrealobj(np.poly([+1.082j, +2.613j, -2.613j, -1.082j])))
        assert_(np.isrealobj(np.poly([0 + 1j, -0 + -1j, 1 + 2j,
                                      1 - 2j, 1. + 3.5j, 1 - 3.5j])))
        assert_(np.isrealobj(np.poly([1j, -1j, 1 + 2j, 1 - 2j, 1 + 3j, 1 - 3.j])))
        assert_(np.isrealobj(np.poly([1j, -1j, 1 + 2j, 1 - 2j])))
        assert_(np.isrealobj(np.poly([1j, -1j, 2j, -2j])))
        assert_(np.isrealobj(np.poly([1j, -1j])))
        assert_(np.isrealobj(np.poly([1, -1])))

        assert_(np.iscomplexobj(np.poly([1j, -1.0000001j])))

        np.random.seed(42)
        a = np.random.randn(100) + 1j * np.random.randn(100)
        assert_(np.isrealobj(np.poly(np.concatenate((a, np.conjugate(a))))))

    def test_roots(self):
        assert_array_equal(np.roots([1, 0, 0]), [0, 0])

        # Testing for larger root values
        for i in np.logspace(10, 25, num=1000, base=10):
            tgt = np.array([-1, 1, i])
            res = np.sort(np.roots(poly.polyfromroots(tgt)[::-1]))
            assert_almost_equal(res, tgt, 14 - int(np.log10(i)))    # Adapting the expected precision according to the root value, to take into account numerical calculation error

        for i in np.logspace(10, 25, num=1000, base=10):
            tgt = np.array([-1, 1.01, i])
            res = np.sort(np.roots(poly.polyfromroots(tgt)[::-1]))
            assert_almost_equal(res, tgt, 14 - int(np.log10(i)))    # Adapting the expected precision according to the root value, to take into account numerical calculation error

    def test_str_leading_zeros(self):
        p = np.poly1d([4, 3, 2, 1])
        p[3] = 0
        assert_equal(str(p),
                     "   2\n"
                     "3 x + 2 x + 1")

        p = np.poly1d([1, 2])
        p[0] = 0
        p[1] = 0
        assert_equal(str(p), " \n0")

    def test_polyfit(self):
        c = np.array([3., 2., 1.])
        x = np.linspace(0, 2, 7)
        y = np.polyval(c, x)
        err = [1, -1, 1, -1, 1, -1, 1]
        weights = np.arange(8, 1, -1)**2 / 7.0

        # Check exception when too few points for variance estimate. Note that
        # the estimate requires the number of data points to exceed
        # degree + 1
        assert_raises(ValueError, np.polyfit,
                      [1], [1], deg=0, cov=True)

        # check 1D case
        m, cov = np.polyfit(x, y + err, 2, cov=True)
        est = [3.8571, 0.2857, 1.619]
        assert_almost_equal(est, m, decimal=4)
        val0 = [[ 1.4694, -2.9388,  0.8163],
                [-2.9388,  6.3673, -2.1224],
                [ 0.8163, -2.1224,  1.161 ]]  # noqa: E202
        assert_almost_equal(val0, cov, decimal=4)

        m2, cov2 = np.polyfit(x, y + err, 2, w=weights, cov=True)
        assert_almost_equal([4.8927, -1.0177, 1.7768], m2, decimal=4)
        val = [[ 4.3964, -5.0052,  0.4878],
               [-5.0052,  6.8067, -0.9089],
               [ 0.4878, -0.9089,  0.3337]]
        assert_almost_equal(val, cov2, decimal=4)

        m3, cov3 = np.polyfit(x, y + err, 2, w=weights, cov="unscaled")
        assert_almost_equal([4.8927, -1.0177, 1.7768], m3, decimal=4)
        val = [[ 0.1473, -0.1677,  0.0163],
               [-0.1677,  0.228 , -0.0304],  # noqa: E203
               [ 0.0163, -0.0304,  0.0112]]
        assert_almost_equal(val, cov3, decimal=4)

        # check 2D (n,1) case
        y = y[:, np.newaxis]
        c = c[:, np.newaxis]
        assert_almost_equal(c, np.polyfit(x, y, 2))
        # check 2D (n,2) case
        yy = np.concatenate((y, y), axis=1)
        cc = np.concatenate((c, c), axis=1)
        assert_almost_equal(cc, np.polyfit(x, yy, 2))

        m, cov = np.polyfit(x, yy + np.array(err)[:, np.newaxis], 2, cov=True)
        assert_almost_equal(est, m[:, 0], decimal=4)
        assert_almost_equal(est, m[:, 1], decimal=4)
        assert_almost_equal(val0, cov[:, :, 0], decimal=4)
        assert_almost_equal(val0, cov[:, :, 1], decimal=4)

        # check order 1 (deg=0) case, were the analytic results are simple
        np.random.seed(123)
        y = np.random.normal(size=(4, 10000))
        mean, cov = np.polyfit(np.zeros(y.shape[0]), y, deg=0, cov=True)
        # Should get sigma_mean = sigma/sqrt(N) = 1./sqrt(4) = 0.5.
        assert_allclose(mean.std(), 0.5, atol=0.01)
        assert_allclose(np.sqrt(cov.mean()), 0.5, atol=0.01)
        # Without scaling, since reduced chi2 is 1, the result should be the same.
        mean, cov = np.polyfit(np.zeros(y.shape[0]), y, w=np.ones(y.shape[0]),
                               deg=0, cov="unscaled")
        assert_allclose(mean.std(), 0.5, atol=0.01)
        assert_almost_equal(np.sqrt(cov.mean()), 0.5)
        # If we estimate our errors wrong, no change with scaling:
        w = np.full(y.shape[0], 1. / 0.5)
        mean, cov = np.polyfit(np.zeros(y.shape[0]), y, w=w, deg=0, cov=True)
        assert_allclose(mean.std(), 0.5, atol=0.01)
        assert_allclose(np.sqrt(cov.mean()), 0.5, atol=0.01)
        # But if we do not scale, our estimate for the error in the mean will
        # differ.
        mean, cov = np.polyfit(np.zeros(y.shape[0]), y, w=w, deg=0, cov="unscaled")
        assert_allclose(mean.std(), 0.5, atol=0.01)
        assert_almost_equal(np.sqrt(cov.mean()), 0.25)

    def test_objects(self):
        from decimal import Decimal
        p = np.poly1d([Decimal('4.0'), Decimal('3.0'), Decimal('2.0')])
        p2 = p * Decimal('1.333333333333333')
        assert_(p2[1] == Decimal("3.9999999999999990"))
        p2 = p.deriv()
        assert_(p2[1] == Decimal('8.0'))
        p2 = p.integ()
        assert_(p2[3] == Decimal("1.333333333333333333333333333"))
        assert_(p2[2] == Decimal('1.5'))
        assert_(np.issubdtype(p2.coeffs.dtype, np.object_))
        p = np.poly([Decimal(1), Decimal(2)])
        assert_equal(np.poly([Decimal(1), Decimal(2)]),
                     [1, Decimal(-3), Decimal(2)])

    def test_complex(self):
        p = np.poly1d([3j, 2j, 1j])
        p2 = p.integ()
        assert_((p2.coeffs == [1j, 1j, 1j, 0]).all())
        p2 = p.deriv()
        assert_((p2.coeffs == [6j, 2j]).all())

    def test_integ_coeffs(self):
        p = np.poly1d([3, 2, 1])
        p2 = p.integ(3, k=[9, 7, 6])
        assert_(
            (p2.coeffs == [1 / 4. / 5., 1 / 3. / 4., 1 / 2. / 3., 9 / 1. / 2., 7, 6]).all())

    def test_zero_dims(self):
        try:
            np.poly(np.zeros((0, 0)))
        except ValueError:
            pass

    def test_poly_int_overflow(self):
        """
        Regression test for gh-5096.
        """
        v = np.arange(1, 21)
        assert_almost_equal(np.poly(v), np.poly(np.diag(v)))

    def test_zero_poly_dtype(self):
        """
        Regression test for gh-16354.
        """
        z = np.array([0, 0, 0])
        p = np.poly1d(z.astype(np.int64))
        assert_equal(p.coeffs.dtype, np.int64)

        p = np.poly1d(z.astype(np.float32))
        assert_equal(p.coeffs.dtype, np.float32)

        p = np.poly1d(z.astype(np.complex64))
        assert_equal(p.coeffs.dtype, np.complex64)

    def test_poly_eq(self):
        p = np.poly1d([1, 2, 3])
        p2 = np.poly1d([1, 2, 4])
        assert_equal(p == None, False)  # noqa: E711
        assert_equal(p != None, True)  # noqa: E711
        assert_equal(p == p, True)
        assert_equal(p == p2, False)
        assert_equal(p != p2, True)

    def test_polydiv(self):
        b = np.poly1d([2, 6, 6, 1])
        a = np.poly1d([-1j, (1 + 2j), -(2 + 1j), 1])
        q, r = np.polydiv(b, a)
        assert_equal(q.coeffs.dtype, np.complex128)
        assert_equal(r.coeffs.dtype, np.complex128)
        assert_equal(q * a + r, b)

        c = [1, 2, 3]
        d = np.poly1d([1, 2, 3])
        s, t = np.polydiv(c, d)
        assert isinstance(s, np.poly1d)
        assert isinstance(t, np.poly1d)
        u, v = np.polydiv(d, c)
        assert isinstance(u, np.poly1d)
        assert isinstance(v, np.poly1d)

    def test_poly_coeffs_mutable(self):
        """ Coefficients should be modifiable """
        p = np.poly1d([1, 2, 3])

        p.coeffs += 1
        assert_equal(p.coeffs, [2, 3, 4])

        p.coeffs[2] += 10
        assert_equal(p.coeffs, [2, 3, 14])

        # this never used to be allowed - let's not add features to deprecated
        # APIs
        assert_raises(AttributeError, setattr, p, 'coeffs', np.array(1))

# === NexusCore/src\file_creator.py ===
# src/file_creator.py
import os

def create_code_file(filename: str, code: str, folder: str = "src/generated") -> str:
    os.makedirs(folder, exist_ok=True)
    path = os.path.join(folder, filename)
    with open(path, "w", encoding="utf-8") as f:
        f.write(code)
    return path

# === NexusCore/my-crm-app\app\models.py ===
# TODO: Define database models

from . import db

class Customer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    # TODO: Add more fields as necessary

# === NexusCore/src\sandbox_logs\repair_20250713_114519_fixed.py ===
エラーメッセージを見ると、テストモジュールのインポートに失敗しているようです。これはPythonのコードに問題があるというよりは、テスト環境の設定やファイルの配置に問題がある可能性が高いです。ユーザーが提供したコードの中には、確かに間違いがありますが、それがこのエラーの原因ではないようです。

ただし、ユーザーが指摘した通り、関数addの中の演算が間違っています。正しくは以下のようになります。

--- 修正済みコード ---
```python
def add(a, b):
    return a + b  # ✔️ a + b
```

# === NexusCore/src\sandbox_logs\repair_20250713_114534_original.py ===
エラーメッセージを見ると、テストモジュールのインポートに失敗しているようです。これはPythonのコードに問題があるというよりは、テスト環境の設定やファイルの配置に問題がある可能性が高いです。ユーザーが提供したコードの中には、確かに間違いがありますが、それがこのエラーの原因ではないようです。

ただし、ユーザーが指摘した通り、関数addの中の演算が間違っています。正しくは以下のようになります。

--- 修正済みコード ---
```python
def add(a, b):
    return a + b  # ✔️ a + b
```

# === NexusCore/src\sandbox_logs\repair_20250713_131843_fixed.py ===
```python
def add(a, b):
    return a + b  # Corrected from subtraction to addition

def test_add():
    assert add(1, 2) == 3
    assert add(-1, 1) == 0
    assert add(0, 0) == 0
```

# === NexusCore/src\sandbox_logs\repair_20250713_131857_original.py ===
```python
def add(a, b):
    return a + b  # Corrected from subtraction to addition

def test_add():
    assert add(1, 2) == 3
    assert add(-1, 1) == 0
    assert add(0, 0) == 0
```

# === NexusCore/openenv\Lib\site-packages\huggingface_hub\hf_api.py ===
# coding=utf-8
# Copyright 2019-present, the HuggingFace Inc. team.
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
from __future__ import annotations

import inspect
import io
import json
import re
import struct
import warnings
from collections import defaultdict
from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import asdict, dataclass, field
from datetime import datetime
from functools import wraps
from itertools import islice
from pathlib import Path
from typing import (
    TYPE_CHECKING,
    Any,
    BinaryIO,
    Callable,
    Dict,
    Iterable,
    Iterator,
    List,
    Literal,
    Optional,
    Tuple,
    Type,
    TypeVar,
    Union,
    overload,
)
from urllib.parse import quote, unquote

import requests
from requests.exceptions import HTTPError
from tqdm.auto import tqdm as base_tqdm
from tqdm.contrib.concurrent import thread_map

from . import constants
from ._commit_api import (
    CommitOperation,
    CommitOperationAdd,
    CommitOperationCopy,
    CommitOperationDelete,
    _fetch_files_to_copy,
    _fetch_upload_modes,
    _prepare_commit_payload,
    _upload_lfs_files,
    _upload_xet_files,
    _warn_on_overwriting_operations,
)
from ._inference_endpoints import InferenceEndpoint, InferenceEndpointType
from ._space_api import SpaceHardware, SpaceRuntime, SpaceStorage, SpaceVariable
from ._upload_large_folder import upload_large_folder_internal
from .community import (
    Discussion,
    DiscussionComment,
    DiscussionStatusChange,
    DiscussionTitleChange,
    DiscussionWithDetails,
    deserialize_event,
)
from .constants import (
    DEFAULT_ETAG_TIMEOUT,  # noqa: F401 # kept for backward compatibility
    DEFAULT_REQUEST_TIMEOUT,  # noqa: F401 # kept for backward compatibility
    DEFAULT_REVISION,  # noqa: F401 # kept for backward compatibility
    DISCUSSION_STATUS,  # noqa: F401 # kept for backward compatibility
    DISCUSSION_TYPES,  # noqa: F401 # kept for backward compatibility
    ENDPOINT,  # noqa: F401 # kept for backward compatibility
    INFERENCE_ENDPOINTS_ENDPOINT,  # noqa: F401 # kept for backward compatibility
    REGEX_COMMIT_OID,  # noqa: F401 # kept for backward compatibility
    REPO_TYPE_MODEL,  # noqa: F401 # kept for backward compatibility
    REPO_TYPES,  # noqa: F401 # kept for backward compatibility
    REPO_TYPES_MAPPING,  # noqa: F401 # kept for backward compatibility
    REPO_TYPES_URL_PREFIXES,  # noqa: F401 # kept for backward compatibility
    SAFETENSORS_INDEX_FILE,  # noqa: F401 # kept for backward compatibility
    SAFETENSORS_MAX_HEADER_LENGTH,  # noqa: F401 # kept for backward compatibility
    SAFETENSORS_SINGLE_FILE,  # noqa: F401 # kept for backward compatibility
    SPACES_SDK_TYPES,  # noqa: F401 # kept for backward compatibility
    WEBHOOK_DOMAIN_T,  # noqa: F401 # kept for backward compatibility
    DiscussionStatusFilter,  # noqa: F401 # kept for backward compatibility
    DiscussionTypeFilter,  # noqa: F401 # kept for backward compatibility
)
from .errors import (
    BadRequestError,
    EntryNotFoundError,
    GatedRepoError,
    HfHubHTTPError,
    RepositoryNotFoundError,
    RevisionNotFoundError,
)
from .file_download import HfFileMetadata, get_hf_file_metadata, hf_hub_url
from .repocard_data import DatasetCardData, ModelCardData, SpaceCardData
from .utils import (
    DEFAULT_IGNORE_PATTERNS,
    HfFolder,  # noqa: F401 # kept for backward compatibility
    LocalTokenNotFoundError,
    NotASafetensorsRepoError,
    SafetensorsFileMetadata,
    SafetensorsParsingError,
    SafetensorsRepoMetadata,
    TensorInfo,
    build_hf_headers,
    chunk_iterable,
    experimental,
    filter_repo_objects,
    fix_hf_endpoint_in_url,
    get_session,
    get_token,
    hf_raise_for_status,
    logging,
    paginate,
    parse_datetime,
    validate_hf_hub_args,
)
from .utils import tqdm as hf_tqdm
from .utils._auth import _get_token_from_environment, _get_token_from_file, _get_token_from_google_colab
from .utils._deprecation import _deprecate_method
from .utils._runtime import is_xet_available
from .utils._typing import CallableT
from .utils.endpoint_helpers import _is_emission_within_threshold


if TYPE_CHECKING:
    from .inference._providers import PROVIDER_T

R = TypeVar("R")  # Return type
CollectionItemType_T = Literal["model", "dataset", "space", "paper", "collection"]

ExpandModelProperty_T = Literal[
    "author",
    "baseModels",
    "cardData",
    "childrenModelCount",
    "config",
    "createdAt",
    "disabled",
    "downloads",
    "downloadsAllTime",
    "gated",
    "gguf",
    "inference",
    "inferenceProviderMapping",
    "lastModified",
    "library_name",
    "likes",
    "mask_token",
    "model-index",
    "pipeline_tag",
    "private",
    "resourceGroup",
    "safetensors",
    "sha",
    "siblings",
    "spaces",
    "tags",
    "transformersInfo",
    "trendingScore",
    "usedStorage",
    "widgetData",
    "xetEnabled",
]

ExpandDatasetProperty_T = Literal[
    "author",
    "cardData",
    "citation",
    "createdAt",
    "description",
    "disabled",
    "downloads",
    "downloadsAllTime",
    "gated",
    "lastModified",
    "likes",
    "paperswithcode_id",
    "private",
    "resourceGroup",
    "sha",
    "siblings",
    "tags",
    "trendingScore",
    "usedStorage",
    "xetEnabled",
]

ExpandSpaceProperty_T = Literal[
    "author",
    "cardData",
    "createdAt",
    "datasets",
    "disabled",
    "lastModified",
    "likes",
    "models",
    "private",
    "resourceGroup",
    "runtime",
    "sdk",
    "sha",
    "siblings",
    "subdomain",
    "tags",
    "trendingScore",
    "usedStorage",
    "xetEnabled",
]

USERNAME_PLACEHOLDER = "hf_user"
_REGEX_DISCUSSION_URL = re.compile(r".*/discussions/(\d+)$")

_CREATE_COMMIT_NO_REPO_ERROR_MESSAGE = (
    "\nNote: Creating a commit assumes that the repo already exists on the"
    " Huggingface Hub. Please use `create_repo` if it's not the case."
)
_AUTH_CHECK_NO_REPO_ERROR_MESSAGE = (
    "\nNote: The repository either does not exist or you do not have access rights."
    " Please check the repository ID and your access permissions."
    " If this is a private repository, ensure that your token is correct."
)
logger = logging.get_logger(__name__)


def repo_type_and_id_from_hf_id(hf_id: str, hub_url: Optional[str] = None) -> Tuple[Optional[str], Optional[str], str]:
    """
    Returns the repo type and ID from a huggingface.co URL linking to a
    repository

    Args:
        hf_id (`str`):
            An URL or ID of a repository on the HF hub. Accepted values are:

            - https://huggingface.co/<repo_type>/<namespace>/<repo_id>
            - https://huggingface.co/<namespace>/<repo_id>
            - hf://<repo_type>/<namespace>/<repo_id>
            - hf://<namespace>/<repo_id>
            - <repo_type>/<namespace>/<repo_id>
            - <namespace>/<repo_id>
            - <repo_id>
        hub_url (`str`, *optional*):
            The URL of the HuggingFace Hub, defaults to https://huggingface.co

    Returns:
        A tuple with three items: repo_type (`str` or `None`), namespace (`str` or
        `None`) and repo_id (`str`).

    Raises:
        [`ValueError`](https://docs.python.org/3/library/exceptions.html#ValueError)
            If URL cannot be parsed.
        [`ValueError`](https://docs.python.org/3/library/exceptions.html#ValueError)
            If `repo_type` is unknown.
    """
    input_hf_id = hf_id

    hub_url = re.sub(r"https?://", "", hub_url if hub_url is not None else constants.ENDPOINT)
    is_hf_url = hub_url in hf_id and "@" not in hf_id

    HFFS_PREFIX = "hf://"
    if hf_id.startswith(HFFS_PREFIX):  # Remove "hf://" prefix if exists
        hf_id = hf_id[len(HFFS_PREFIX) :]

    url_segments = hf_id.split("/")
    is_hf_id = len(url_segments) <= 3

    namespace: Optional[str]
    if is_hf_url:
        namespace, repo_id = url_segments[-2:]
        if namespace == hub_url:
            namespace = None
        if len(url_segments) > 2 and hub_url not in url_segments[-3]:
            repo_type = url_segments[-3]
        elif namespace in constants.REPO_TYPES_MAPPING:
            # Mean canonical dataset or model
            repo_type = constants.REPO_TYPES_MAPPING[namespace]
            namespace = None
        else:
            repo_type = None
    elif is_hf_id:
        if len(url_segments) == 3:
            # Passed <repo_type>/<user>/<model_id> or <repo_type>/<org>/<model_id>
            repo_type, namespace, repo_id = url_segments[-3:]
        elif len(url_segments) == 2:
            if url_segments[0] in constants.REPO_TYPES_MAPPING:
                # Passed '<model_id>' or 'datasets/<dataset_id>' for a canonical model or dataset
                repo_type = constants.REPO_TYPES_MAPPING[url_segments[0]]
                namespace = None
                repo_id = hf_id.split("/")[-1]
            else:
                # Passed <user>/<model_id> or <org>/<model_id>
                namespace, repo_id = hf_id.split("/")[-2:]
                repo_type = None
        else:
            # Passed <model_id>
            repo_id = url_segments[0]
            namespace, repo_type = None, None
    else:
        raise ValueError(f"Unable to retrieve user and repo ID from the passed HF ID: {hf_id}")

    # Check if repo type is known (mapping "spaces" => "space" + empty value => `None`)
    if repo_type in constants.REPO_TYPES_MAPPING:
        repo_type = constants.REPO_TYPES_MAPPING[repo_type]
    if repo_type == "":
        repo_type = None
    if repo_type not in constants.REPO_TYPES:
        raise ValueError(f"Unknown `repo_type`: '{repo_type}' ('{input_hf_id}')")

    return repo_type, namespace, repo_id


@dataclass
class LastCommitInfo(dict):
    oid: str
    title: str
    date: datetime

    def __post_init__(self):  # hack to make LastCommitInfo backward compatible
        self.update(asdict(self))


@dataclass
class BlobLfsInfo(dict):
    size: int
    sha256: str
    pointer_size: int

    def __post_init__(self):  # hack to make BlobLfsInfo backward compatible
        self.update(asdict(self))


@dataclass
class BlobSecurityInfo(dict):
    safe: bool  # duplicate information with "status" field, keeping it for backward compatibility
    status: str
    av_scan: Optional[Dict]
    pickle_import_scan: Optional[Dict]

    def __post_init__(self):  # hack to make BlogSecurityInfo backward compatible
        self.update(asdict(self))


@dataclass
class TransformersInfo(dict):
    auto_model: str
    custom_class: Optional[str] = None
    # possible `pipeline_tag` values: https://github.com/huggingface/huggingface.js/blob/3ee32554b8620644a6287e786b2a83bf5caf559c/packages/tasks/src/pipelines.ts#L72
    pipeline_tag: Optional[str] = None
    processor: Optional[str] = None

    def __post_init__(self):  # hack to make TransformersInfo backward compatible
        self.update(asdict(self))


@dataclass
class SafeTensorsInfo(dict):
    parameters: Dict[str, int]
    total: int

    def __post_init__(self):  # hack to make SafeTensorsInfo backward compatible
        self.update(asdict(self))


@dataclass
class CommitInfo(str):
    """Data structure containing information about a newly created commit.

    Returned by any method that creates a commit on the Hub: [`create_commit`], [`upload_file`], [`upload_folder`],
    [`delete_file`], [`delete_folder`]. It inherits from `str` for backward compatibility but using methods specific
    to `str` is deprecated.

    Attributes:
        commit_url (`str`):
            Url where to find the commit.

        commit_message (`str`):
            The summary (first line) of the commit that has been created.

        commit_description (`str`):
            Description of the commit that has been created. Can be empty.

        oid (`str`):
            Commit hash id. Example: `"91c54ad1727ee830252e457677f467be0bfd8a57"`.

        pr_url (`str`, *optional*):
            Url to the PR that has been created, if any. Populated when `create_pr=True`
            is passed.

        pr_revision (`str`, *optional*):
            Revision of the PR that has been created, if any. Populated when
            `create_pr=True` is passed. Example: `"refs/pr/1"`.

        pr_num (`int`, *optional*):
            Number of the PR discussion that has been created, if any. Populated when
            `create_pr=True` is passed. Can be passed as `discussion_num` in
            [`get_discussion_details`]. Example: `1`.

        repo_url (`RepoUrl`):
            Repo URL of the commit containing info like repo_id, repo_type, etc.

        _url (`str`, *optional*):
            Legacy url for `str` compatibility. Can be the url to the uploaded file on the Hub (if returned by
            [`upload_file`]), to the uploaded folder on the Hub (if returned by [`upload_folder`]) or to the commit on
            the Hub (if returned by [`create_commit`]). Defaults to `commit_url`. It is deprecated to use this
            attribute. Please use `commit_url` instead.
    """

    commit_url: str
    commit_message: str
    commit_description: str
    oid: str
    pr_url: Optional[str] = None

    # Computed from `commit_url` in `__post_init__`
    repo_url: RepoUrl = field(init=False)

    # Computed from `pr_url` in `__post_init__`
    pr_revision: Optional[str] = field(init=False)
    pr_num: Optional[str] = field(init=False)

    # legacy url for `str` compatibility (ex: url to uploaded file, url to uploaded folder, url to PR, etc.)
    _url: str = field(repr=False, default=None)  # type: ignore  # defaults to `commit_url`

    def __new__(cls, *args, commit_url: str, _url: Optional[str] = None, **kwargs):
        return str.__new__(cls, _url or commit_url)

    def __post_init__(self):
        """Populate pr-related fields after initialization.

        See https://docs.python.org/3.10/library/dataclasses.html#post-init-processing.
        """
        # Repo info
        self.repo_url = RepoUrl(self.commit_url.split("/commit/")[0])

        # PR info
        if self.pr_url is not None:
            self.pr_revision = _parse_revision_from_pr_url(self.pr_url)
            self.pr_num = int(self.pr_revision.split("/")[-1])
        else:
            self.pr_revision = None
            self.pr_num = None


@dataclass
class AccessRequest:
    """Data structure containing information about a user access request.

    Attributes:
        username (`str`):
            Username of the user who requested access.
        fullname (`str`):
            Fullname of the user who requested access.
        email (`Optional[str]`):
            Email of the user who requested access.
            Can only be `None` in the /accepted list if the user was granted access manually.
        timestamp (`datetime`):
            Timestamp of the request.
        status (`Literal["pending", "accepted", "rejected"]`):
            Status of the request. Can be one of `["pending", "accepted", "rejected"]`.
        fields (`Dict[str, Any]`, *optional*):
            Additional fields filled by the user in the gate form.
    """

    username: str
    fullname: str
    email: Optional[str]
    timestamp: datetime
    status: Literal["pending", "accepted", "rejected"]

    # Additional fields filled by the user in the gate form
    fields: Optional[Dict[str, Any]] = None


@dataclass
class WebhookWatchedItem:
    """Data structure containing information about the items watched by a webhook.

    Attributes:
        type (`Literal["dataset", "model", "org", "space", "user"]`):
            Type of the item to be watched. Can be one of `["dataset", "model", "org", "space", "user"]`.
        name (`str`):
            Name of the item to be watched. Can be the username, organization name, model name, dataset name or space name.
    """

    type: Literal["dataset", "model", "org", "space", "user"]
    name: str


@dataclass
class WebhookInfo:
    """Data structure containing information about a webhook.

    Attributes:
        id (`str`):
            ID of the webhook.
        url (`str`):
            URL of the webhook.
        watched (`List[WebhookWatchedItem]`):
            List of items watched by the webhook, see [`WebhookWatchedItem`].
        domains (`List[WEBHOOK_DOMAIN_T]`):
            List of domains the webhook is watching. Can be one of `["repo", "discussions"]`.
        secret (`str`, *optional*):
            Secret of the webhook.
        disabled (`bool`):
            Whether the webhook is disabled or not.
    """

    id: str
    url: str
    watched: List[WebhookWatchedItem]
    domains: List[constants.WEBHOOK_DOMAIN_T]
    secret: Optional[str]
    disabled: bool


class RepoUrl(str):
    """Subclass of `str` describing a repo URL on the Hub.

    `RepoUrl` is returned by `HfApi.create_repo`. It inherits from `str` for backward
    compatibility. At initialization, the URL is parsed to populate properties:
    - endpoint (`str`)
    - namespace (`Optional[str]`)
    - repo_name (`str`)
    - repo_id (`str`)
    - repo_type (`Literal["model", "dataset", "space"]`)
    - url (`str`)

    Args:
        url (`Any`):
            String value of the repo url.
        endpoint (`str`, *optional*):
            Endpoint of the Hub. Defaults to <https://huggingface.co>.

    Example:
    ```py
    >>> RepoUrl('https://huggingface.co/gpt2')
    RepoUrl('https://huggingface.co/gpt2', endpoint='https://huggingface.co', repo_type='model', repo_id='gpt2')

    >>> RepoUrl('https://hub-ci.huggingface.co/datasets/dummy_user/dummy_dataset', endpoint='https://hub-ci.huggingface.co')
    RepoUrl('https://hub-ci.huggingface.co/datasets/dummy_user/dummy_dataset', endpoint='https://hub-ci.huggingface.co', repo_type='dataset', repo_id='dummy_user/dummy_dataset')

    >>> RepoUrl('hf://datasets/my-user/my-dataset')
    RepoUrl('hf://datasets/my-user/my-dataset', endpoint='https://huggingface.co', repo_type='dataset', repo_id='user/dataset')

    >>> HfApi.create_repo("dummy_model")
    RepoUrl('https://huggingface.co/Wauplin/dummy_model', endpoint='https://huggingface.co', repo_type='model', repo_id='Wauplin/dummy_model')
    ```

    Raises:
        [`ValueError`](https://docs.python.org/3/library/exceptions.html#ValueError)
            If URL cannot be parsed.
        [`ValueError`](https://docs.python.org/3/library/exceptions.html#ValueError)
            If `repo_type` is unknown.
    """

    def __new__(cls, url: Any, endpoint: Optional[str] = None):
        url = fix_hf_endpoint_in_url(url, endpoint=endpoint)
        return super(RepoUrl, cls).__new__(cls, url)

    def __init__(self, url: Any, endpoint: Optional[str] = None) -> None:
        super().__init__()
        # Parse URL
        self.endpoint = endpoint or constants.ENDPOINT
        repo_type, namespace, repo_name = repo_type_and_id_from_hf_id(self, hub_url=self.endpoint)

        # Populate fields
        self.namespace = namespace
        self.repo_name = repo_name
        self.repo_id = repo_name if namespace is None else f"{namespace}/{repo_name}"
        self.repo_type = repo_type or constants.REPO_TYPE_MODEL
        self.url = str(self)  # just in case it's needed

    def __repr__(self) -> str:
        return f"RepoUrl('{self}', endpoint='{self.endpoint}', repo_type='{self.repo_type}', repo_id='{self.repo_id}')"


@dataclass
class RepoSibling:
    """
    Contains basic information about a repo file inside a repo on the Hub.

    <Tip>

    All attributes of this class are optional except `rfilename`. This is because only the file names are returned when
    listing repositories on the Hub (with [`list_models`], [`list_datasets`] or [`list_spaces`]). If you need more
    information like file size, blob id or lfs details, you must request them specifically from one repo at a time
    (using [`model_info`], [`dataset_info`] or [`space_info`]) as it adds more constraints on the backend server to
    retrieve these.

    </Tip>

    Attributes:
        rfilename (str):
            file name, relative to the repo root.
        size (`int`, *optional*):
            The file's size, in bytes. This attribute is defined when `files_metadata` argument of [`repo_info`] is set
            to `True`. It's `None` otherwise.
        blob_id (`str`, *optional*):
            The file's git OID. This attribute is defined when `files_metadata` argument of [`repo_info`] is set to
            `True`. It's `None` otherwise.
        lfs (`BlobLfsInfo`, *optional*):
            The file's LFS metadata. This attribute is defined when`files_metadata` argument of [`repo_info`] is set to
            `True` and the file is stored with Git LFS. It's `None` otherwise.
    """

    rfilename: str
    size: Optional[int] = None
    blob_id: Optional[str] = None
    lfs: Optional[BlobLfsInfo] = None


@dataclass
class RepoFile:
    """
    Contains information about a file on the Hub.

    Attributes:
        path (str):
            file path relative to the repo root.
        size (`int`):
            The file's size, in bytes.
        blob_id (`str`):
            The file's git OID.
        lfs (`BlobLfsInfo`):
            The file's LFS metadata.
        last_commit (`LastCommitInfo`, *optional*):
            The file's last commit metadata. Only defined if [`list_repo_tree`] and [`get_paths_info`]
            are called with `expand=True`.
        security (`BlobSecurityInfo`, *optional*):
            The file's security scan metadata. Only defined if [`list_repo_tree`] and [`get_paths_info`]
            are called with `expand=True`.
    """

    path: str
    size: int
    blob_id: str
    lfs: Optional[BlobLfsInfo] = None
    last_commit: Optional[LastCommitInfo] = None
    security: Optional[BlobSecurityInfo] = None

    def __init__(self, **kwargs):
        self.path = kwargs.pop("path")
        self.size = kwargs.pop("size")
        self.blob_id = kwargs.pop("oid")
        lfs = kwargs.pop("lfs", None)
        if lfs is not None:
            lfs = BlobLfsInfo(size=lfs["size"], sha256=lfs["oid"], pointer_size=lfs["pointerSize"])
        self.lfs = lfs
        last_commit = kwargs.pop("lastCommit", None) or kwargs.pop("last_commit", None)
        if last_commit is not None:
            last_commit = LastCommitInfo(
                oid=last_commit["id"], title=last_commit["title"], date=parse_datetime(last_commit["date"])
            )
        self.last_commit = last_commit
        security = kwargs.pop("securityFileStatus", None)
        if security is not None:
            safe = security["status"] == "safe"
            security = BlobSecurityInfo(
                safe=safe,
                status=security["status"],
                av_scan=security["avScan"],
                pickle_import_scan=security["pickleImportScan"],
            )
        self.security = security

        # backwards compatibility
        self.rfilename = self.path
        self.lastCommit = self.last_commit


@dataclass
class RepoFolder:
    """
    Contains information about a folder on the Hub.

    Attributes:
        path (str):
            folder path relative to the repo root.
        tree_id (`str`):
            The folder's git OID.
        last_commit (`LastCommitInfo`, *optional*):
            The folder's last commit metadata. Only defined if [`list_repo_tree`] and [`get_paths_info`]
            are called with `expand=True`.
    """

    path: str
    tree_id: str
    last_commit: Optional[LastCommitInfo] = None

    def __init__(self, **kwargs):
        self.path = kwargs.pop("path")
        self.tree_id = kwargs.pop("oid")
        last_commit = kwargs.pop("lastCommit", None) or kwargs.pop("last_commit", None)
        if last_commit is not None:
            last_commit = LastCommitInfo(
                oid=last_commit["id"], title=last_commit["title"], date=parse_datetime(last_commit["date"])
            )
        self.last_commit = last_commit


@dataclass
class InferenceProviderMapping:
    provider: "PROVIDER_T"  # Provider name
    hf_model_id: str  # ID of the model on the Hugging Face Hub
    provider_id: str  # ID of the model on the provider's side
    status: Literal["error", "live", "staging"]
    task: str

    adapter: Optional[str] = None
    adapter_weights_path: Optional[str] = None
    type: Optional[Literal["single-model", "tag-filter"]] = None

    def __init__(self, **kwargs):
        self.provider = kwargs.pop("provider")
        self.hf_model_id = kwargs.pop("hf_model_id")
        self.provider_id = kwargs.pop("providerId")
        self.status = kwargs.pop("status")
        self.task = kwargs.pop("task")

        self.adapter = kwargs.pop("adapter", None)
        self.adapter_weights_path = kwargs.pop("adapterWeightsPath", None)
        self.type = kwargs.pop("type", None)
        self.__dict__.update(**kwargs)


@dataclass
class ModelInfo:
    """
    Contains information about a model on the Hub.

    <Tip>

    Most attributes of this class are optional. This is because the data returned by the Hub depends on the query made.
    In general, the more specific the query, the more information is returned. On the contrary, when listing models
    using [`list_models`] only a subset of the attributes are returned.

    </Tip>

    Attributes:
        id (`str`):
            ID of model.
        author (`str`, *optional*):
            Author of the model.
        sha (`str`, *optional*):
            Repo SHA at this particular revision.
        created_at (`datetime`, *optional*):
            Date of creation of the repo on the Hub. Note that the lowest value is `2022-03-02T23:29:04.000Z`,
            corresponding to the date when we began to store creation dates.
        last_modified (`datetime`, *optional*):
            Date of last commit to the repo.
        private (`bool`):
            Is the repo private.
        disabled (`bool`, *optional*):
            Is the repo disabled.
        downloads (`int`):
            Number of downloads of the model over the last 30 days.
        downloads_all_time (`int`):
            Cumulated number of downloads of the model since its creation.
        gated (`Literal["auto", "manual", False]`, *optional*):
            Is the repo gated.
            If so, whether there is manual or automatic approval.
        gguf (`Dict`, *optional*):
            GGUF information of the model.
        inference (`Literal["warm"]`, *optional*):
            Status of the model on Inference Providers. Warm if the model is served by at least one provider.
        inference_provider_mapping (`List[InferenceProviderMapping]`, *optional*):
            A list of [`InferenceProviderMapping`] ordered after the user's provider order.
        likes (`int`):
            Number of likes of the model.
        library_name (`str`, *optional*):
            Library associated with the model.
        tags (`List[str]`):
            List of tags of the model. Compared to `card_data.tags`, contains extra tags computed by the Hub
            (e.g. supported libraries, model's arXiv).
        pipeline_tag (`str`, *optional*):
            Pipeline tag associated with the model.
        mask_token (`str`, *optional*):
            Mask token used by the model.
        widget_data (`Any`, *optional*):
            Widget data associated with the model.
        model_index (`Dict`, *optional*):
            Model index for evaluation.
        config (`Dict`, *optional*):
            Model configuration.
        transformers_info (`TransformersInfo`, *optional*):
            Transformers-specific info (auto class, processor, etc.) associated with the model.
        trending_score (`int`, *optional*):
            Trending score of the model.
        card_data (`ModelCardData`, *optional*):
            Model Card Metadata  as a [`huggingface_hub.repocard_data.ModelCardData`] object.
        siblings (`List[RepoSibling]`):
            List of [`huggingface_hub.hf_api.RepoSibling`] objects that constitute the model.
        spaces (`List[str]`, *optional*):
            List of spaces using the model.
        safetensors (`SafeTensorsInfo`, *optional*):
            Model's safetensors information.
        security_repo_status (`Dict`, *optional*):
            Model's security scan status.
    """

    id: str
    author: Optional[str]
    sha: Optional[str]
    created_at: Optional[datetime]
    last_modified: Optional[datetime]
    private: Optional[bool]
    disabled: Optional[bool]
    downloads: Optional[int]
    downloads_all_time: Optional[int]
    gated: Optional[Literal["auto", "manual", False]]
    gguf: Optional[Dict]
    inference: Optional[Literal["warm"]]
    inference_provider_mapping: Optional[List[InferenceProviderMapping]]
    likes: Optional[int]
    library_name: Optional[str]
    tags: Optional[List[str]]
    pipeline_tag: Optional[str]
    mask_token: Optional[str]
    card_data: Optional[ModelCardData]
    widget_data: Optional[Any]
    model_index: Optional[Dict]
    config: Optional[Dict]
    transformers_info: Optional[TransformersInfo]
    trending_score: Optional[int]
    siblings: Optional[List[RepoSibling]]
    spaces: Optional[List[str]]
    safetensors: Optional[SafeTensorsInfo]
    security_repo_status: Optional[Dict]
    xet_enabled: Optional[bool]

    def __init__(self, **kwargs):
        self.id = kwargs.pop("id")
        self.author = kwargs.pop("author", None)
        self.sha = kwargs.pop("sha", None)
        last_modified = kwargs.pop("lastModified", None) or kwargs.pop("last_modified", None)
        self.last_modified = parse_datetime(last_modified) if last_modified else None
        created_at = kwargs.pop("createdAt", None) or kwargs.pop("created_at", None)
        self.created_at = parse_datetime(created_at) if created_at else None
        self.private = kwargs.pop("private", None)
        self.gated = kwargs.pop("gated", None)
        self.disabled = kwargs.pop("disabled", None)
        self.downloads = kwargs.pop("downloads", None)
        self.downloads_all_time = kwargs.pop("downloadsAllTime", None)
        self.likes = kwargs.pop("likes", None)
        self.library_name = kwargs.pop("library_name", None)
        self.gguf = kwargs.pop("gguf", None)

        self.inference = kwargs.pop("inference", None)

        # little hack to simplify Inference Providers logic and make it backward and forward compatible
        # right now, API returns a dict on model_info and a list on list_models. Let's harmonize to list.
        mapping = kwargs.pop("inferenceProviderMapping", None)
        if isinstance(mapping, list):
            self.inference_provider_mapping = [
                InferenceProviderMapping(**{**value, "hf_model_id": self.id}) for value in mapping
            ]
        elif isinstance(mapping, dict):
            self.inference_provider_mapping = [
                InferenceProviderMapping(**{**value, "hf_model_id": self.id, "provider": provider})
                for provider, value in mapping.items()
            ]
        elif mapping is None:
            self.inference_provider_mapping = None
        else:
            raise ValueError(
                f"Unexpected type for `inferenceProviderMapping`. Expecting `dict` or `list`. Got {mapping}."
            )

        self.tags = kwargs.pop("tags", None)
        self.pipeline_tag = kwargs.pop("pipeline_tag", None)
        self.mask_token = kwargs.pop("mask_token", None)
        self.trending_score = kwargs.pop("trendingScore", None)

        card_data = kwargs.pop("cardData", None) or kwargs.pop("card_data", None)
        self.card_data = (
            ModelCardData(**card_data, ignore_metadata_errors=True) if isinstance(card_data, dict) else card_data
        )

        self.widget_data = kwargs.pop("widgetData", None)
        self.model_index = kwargs.pop("model-index", None) or kwargs.pop("model_index", None)
        self.config = kwargs.pop("config", None)
        transformers_info = kwargs.pop("transformersInfo", None) or kwargs.pop("transformers_info", None)
        self.transformers_info = TransformersInfo(**transformers_info) if transformers_info else None
        siblings = kwargs.pop("siblings", None)
        self.siblings = (
            [
                RepoSibling(
                    rfilename=sibling["rfilename"],
                    size=sibling.get("size"),
                    blob_id=sibling.get("blobId"),
                    lfs=(
                        BlobLfsInfo(
                            size=sibling["lfs"]["size"],
                            sha256=sibling["lfs"]["sha256"],
                            pointer_size=sibling["lfs"]["pointerSize"],
                        )
                        if sibling.get("lfs")
                        else None
                    ),
                )
                for sibling in siblings
            ]
            if siblings is not None
            else None
        )
        self.spaces = kwargs.pop("spaces", None)
        safetensors = kwargs.pop("safetensors", None)
        self.safetensors = (
            SafeTensorsInfo(
                parameters=safetensors["parameters"],
                total=safetensors["total"],
            )
            if safetensors
            else None
        )
        self.security_repo_status = kwargs.pop("securityRepoStatus", None)
        self.xet_enabled = kwargs.pop("xetEnabled", None)
        # backwards compatibility
        self.lastModified = self.last_modified
        self.cardData = self.card_data
        self.transformersInfo = self.transformers_info
        self.__dict__.update(**kwargs)


@dataclass
class DatasetInfo:
    """
    Contains information about a dataset on the Hub.

    <Tip>

    Most attributes of this class are optional. This is because the data returned by the Hub depends on the query made.
    In general, the more specific the query, the more information is returned. On the contrary, when listing datasets
    using [`list_datasets`] only a subset of the attributes are returned.

    </Tip>

    Attributes:
        id (`str`):
            ID of dataset.
        author (`str`):
            Author of the dataset.
        sha (`str`):
            Repo SHA at this particular revision.
        created_at (`datetime`, *optional*):
            Date of creation of the repo on the Hub. Note that the lowest value is `2022-03-02T23:29:04.000Z`,
            corresponding to the date when we began to store creation dates.
        last_modified (`datetime`, *optional*):
            Date of last commit to the repo.
        private (`bool`):
            Is the repo private.
        disabled (`bool`, *optional*):
            Is the repo disabled.
        gated (`Literal["auto", "manual", False]`, *optional*):
            Is the repo gated.
            If so, whether there is manual or automatic approval.
        downloads (`int`):
            Number of downloads of the dataset over the last 30 days.
        downloads_all_time (`int`):
            Cumulated number of downloads of the model since its creation.
        likes (`int`):
            Number of likes of the dataset.
        tags (`List[str]`):
            List of tags of the dataset.
        card_data (`DatasetCardData`, *optional*):
            Model Card Metadata  as a [`huggingface_hub.repocard_data.DatasetCardData`] object.
        siblings (`List[RepoSibling]`):
            List of [`huggingface_hub.hf_api.RepoSibling`] objects that constitute the dataset.
        paperswithcode_id (`str`, *optional*):
            Papers with code ID of the dataset.
        trending_score (`int`, *optional*):
            Trending score of the dataset.
    """

    id: str
    author: Optional[str]
    sha: Optional[str]
    created_at: Optional[datetime]
    last_modified: Optional[datetime]
    private: Optional[bool]
    gated: Optional[Literal["auto", "manual", False]]
    disabled: Optional[bool]
    downloads: Optional[int]
    downloads_all_time: Optional[int]
    likes: Optional[int]
    paperswithcode_id: Optional[str]
    tags: Optional[List[str]]
    trending_score: Optional[int]
    card_data: Optional[DatasetCardData]
    siblings: Optional[List[RepoSibling]]
    xet_enabled: Optional[bool]

    def __init__(self, **kwargs):
        self.id = kwargs.pop("id")
        self.author = kwargs.pop("author", None)
        self.sha = kwargs.pop("sha", None)
        created_at = kwargs.pop("createdAt", None) or kwargs.pop("created_at", None)
        self.created_at = parse_datetime(created_at) if created_at else None
        last_modified = kwargs.pop("lastModified", None) or kwargs.pop("last_modified", None)
        self.last_modified = parse_datetime(last_modified) if last_modified else None
        self.private = kwargs.pop("private", None)
        self.gated = kwargs.pop("gated", None)
        self.disabled = kwargs.pop("disabled", None)
        self.downloads = kwargs.pop("downloads", None)
        self.downloads_all_time = kwargs.pop("downloadsAllTime", None)
        self.likes = kwargs.pop("likes", None)
        self.paperswithcode_id = kwargs.pop("paperswithcode_id", None)
        self.tags = kwargs.pop("tags", None)
        self.trending_score = kwargs.pop("trendingScore", None)

        card_data = kwargs.pop("cardData", None) or kwargs.pop("card_data", None)
        self.card_data = (
            DatasetCardData(**card_data, ignore_metadata_errors=True) if isinstance(card_data, dict) else card_data
        )
        siblings = kwargs.pop("siblings", None)
        self.siblings = (
            [
                RepoSibling(
                    rfilename=sibling["rfilename"],
                    size=sibling.get("size"),
                    blob_id=sibling.get("blobId"),
                    lfs=(
                        BlobLfsInfo(
                            size=sibling["lfs"]["size"],
                            sha256=sibling["lfs"]["sha256"],
                            pointer_size=sibling["lfs"]["pointerSize"],
                        )
                        if sibling.get("lfs")
                        else None
                    ),
                )
                for sibling in siblings
            ]
            if siblings is not None
            else None
        )
        self.xet_enabled = kwargs.pop("xetEnabled", None)
        # backwards compatibility
        self.lastModified = self.last_modified
        self.cardData = self.card_data
        self.__dict__.update(**kwargs)


@dataclass
class SpaceInfo:
    """
    Contains information about a Space on the Hub.

    <Tip>

    Most attributes of this class are optional. This is because the data returned by the Hub depends on the query made.
    In general, the more specific the query, the more information is returned. On the contrary, when listing spaces
    using [`list_spaces`] only a subset of the attributes are returned.

    </Tip>

    Attributes:
        id (`str`):
            ID of the Space.
        author (`str`, *optional*):
            Author of the Space.
        sha (`str`, *optional*):
            Repo SHA at this particular revision.
        created_at (`datetime`, *optional*):
            Date of creation of the repo on the Hub. Note that the lowest value is `2022-03-02T23:29:04.000Z`,
            corresponding to the date when we began to store creation dates.
        last_modified (`datetime`, *optional*):
            Date of last commit to the repo.
        private (`bool`):
            Is the repo private.
        gated (`Literal["auto", "manual", False]`, *optional*):
            Is the repo gated.
            If so, whether there is manual or automatic approval.
        disabled (`bool`, *optional*):
            Is the Space disabled.
        host (`str`, *optional*):
            Host URL of the Space.
        subdomain (`str`, *optional*):
            Subdomain of the Space.
        likes (`int`):
            Number of likes of the Space.
        tags (`List[str]`):
            List of tags of the Space.
        siblings (`List[RepoSibling]`):
            List of [`huggingface_hub.hf_api.RepoSibling`] objects that constitute the Space.
        card_data (`SpaceCardData`, *optional*):
            Space Card Metadata  as a [`huggingface_hub.repocard_data.SpaceCardData`] object.
        runtime (`SpaceRuntime`, *optional*):
            Space runtime information as a [`huggingface_hub.hf_api.SpaceRuntime`] object.
        sdk (`str`, *optional*):
            SDK used by the Space.
        models (`List[str]`, *optional*):
            List of models used by the Space.
        datasets (`List[str]`, *optional*):
            List of datasets used by the Space.
        trending_score (`int`, *optional*):
            Trending score of the Space.
    """

    id: str
    author: Optional[str]
    sha: Optional[str]
    created_at: Optional[datetime]
    last_modified: Optional[datetime]
    private: Optional[bool]
    gated: Optional[Literal["auto", "manual", False]]
    disabled: Optional[bool]
    host: Optional[str]
    subdomain: Optional[str]
    likes: Optional[int]
    sdk: Optional[str]
    tags: Optional[List[str]]
    siblings: Optional[List[RepoSibling]]
    trending_score: Optional[int]
    card_data: Optional[SpaceCardData]
    runtime: Optional[SpaceRuntime]
    models: Optional[List[str]]
    datasets: Optional[List[str]]
    xet_enabled: Optional[bool]

    def __init__(self, **kwargs):
        self.id = kwargs.pop("id")
        self.author = kwargs.pop("author", None)
        self.sha = kwargs.pop("sha", None)
        created_at = kwargs.pop("createdAt", None) or kwargs.pop("created_at", None)
        self.created_at = parse_datetime(created_at) if created_at else None
        last_modified = kwargs.pop("lastModified", None) or kwargs.pop("last_modified", None)
        self.last_modified = parse_datetime(last_modified) if last_modified else None
        self.private = kwargs.pop("private", None)
        self.gated = kwargs.pop("gated", None)
        self.disabled = kwargs.pop("disabled", None)
        self.host = kwargs.pop("host", None)
        self.subdomain = kwargs.pop("subdomain", None)
        self.likes = kwargs.pop("likes", None)
        self.sdk = kwargs.pop("sdk", None)
        self.tags = kwargs.pop("tags", None)
        self.trending_score = kwargs.pop("trendingScore", None)
        card_data = kwargs.pop("cardData", None) or kwargs.pop("card_data", None)
        self.card_data = (
            SpaceCardData(**card_data, ignore_metadata_errors=True) if isinstance(card_data, dict) else card_data
        )
        siblings = kwargs.pop("siblings", None)
        self.siblings = (
            [
                RepoSibling(
                    rfilename=sibling["rfilename"],
                    size=sibling.get("size"),
                    blob_id=sibling.get("blobId"),
                    lfs=(
                        BlobLfsInfo(
                            size=sibling["lfs"]["size"],
                            sha256=sibling["lfs"]["sha256"],
                            pointer_size=sibling["lfs"]["pointerSize"],
                        )
                        if sibling.get("lfs")
                        else None
                    ),
                )
                for sibling in siblings
            ]
            if siblings is not None
            else None
        )
        runtime = kwargs.pop("runtime", None)
        self.runtime = SpaceRuntime(runtime) if runtime else None
        self.models = kwargs.pop("models", None)
        self.datasets = kwargs.pop("datasets", None)
        self.xet_enabled = kwargs.pop("xetEnabled", None)
        # backwards compatibility
        self.lastModified = self.last_modified
        self.cardData = self.card_data
        self.__dict__.update(**kwargs)


@dataclass
class CollectionItem:
    """
    Contains information about an item of a Collection (model, dataset, Space, paper or collection).

    Attributes:
        item_object_id (`str`):
            Unique ID of the item in the collection.
        item_id (`str`):
            ID of the underlying object on the Hub. Can be either a repo_id, a paper id or a collection slug.
            e.g. `"jbilcke-hf/ai-comic-factory"`, `"2307.09288"`, `"celinah/cerebras-function-calling-682607169c35fbfa98b30b9a"`.
        item_type (`str`):
            Type of the underlying object. Can be one of `"model"`, `"dataset"`, `"space"`, `"paper"` or `"collection"`.
        position (`int`):
            Position of the item in the collection.
        note (`str`, *optional*):
            Note associated with the item, as plain text.
    """

    item_object_id: str  # id in database
    item_id: str  # repo_id or paper id
    item_type: str
    position: int
    note: Optional[str] = None

    def __init__(
        self,
        _id: str,
        id: str,
        type: CollectionItemType_T,
        position: int,
        note: Optional[Dict] = None,
        **kwargs,
    ) -> None:
        self.item_object_id: str = _id  # id in database
        self.item_id: str = id  # repo_id or paper id
        # if the item is a collection, override item_id with the slug
        slug = kwargs.get("slug")
        if slug is not None:
            self.item_id = slug  # collection slug
        self.item_type: CollectionItemType_T = type
        self.position: int = position
        self.note: str = note["text"] if note is not None else None


@dataclass
class Collection:
    """
    Contains information about a Collection on the Hub.

    Attributes:
        slug (`str`):
            Slug of the collection. E.g. `"TheBloke/recent-models-64f9a55bb3115b4f513ec026"`.
        title (`str`):
            Title of the collection. E.g. `"Recent models"`.
        owner (`str`):
            Owner of the collection. E.g. `"TheBloke"`.
        items (`List[CollectionItem]`):
            List of items in the collection.
        last_updated (`datetime`):
            Date of the last update of the collection.
        position (`int`):
            Position of the collection in the list of collections of the owner.
        private (`bool`):
            Whether the collection is private or not.
        theme (`str`):
            Theme of the collection. E.g. `"green"`.
        upvotes (`int`):
            Number of upvotes of the collection.
        description (`str`, *optional*):
            Description of the collection, as plain text.
        url (`str`):
            (property) URL of the collection on the Hub.
    """

    slug: str
    title: str
    owner: str
    items: List[CollectionItem]
    last_updated: datetime
    position: int
    private: bool
    theme: str
    upvotes: int
    description: Optional[str] = None

    def __init__(self, **kwargs) -> None:
        self.slug = kwargs.pop("slug")
        self.title = kwargs.pop("title")
        self.owner = kwargs.pop("owner")
        self.items = [CollectionItem(**item) for item in kwargs.pop("items")]
        self.last_updated = parse_datetime(kwargs.pop("lastUpdated"))
        self.position = kwargs.pop("position")
        self.private = kwargs.pop("private")
        self.theme = kwargs.pop("theme")
        self.upvotes = kwargs.pop("upvotes")
        self.description = kwargs.pop("description", None)
        endpoint = kwargs.pop("endpoint", None)
        if endpoint is None:
            endpoint = constants.ENDPOINT
        self._url = f"{endpoint}/collections/{self.slug}"

    @property
    def url(self) -> str:
        """Returns the URL of the collection on the Hub."""
        return self._url


@dataclass
class GitRefInfo:
    """
    Contains information about a git reference for a repo on the Hub.

    Attributes:
        name (`str`):
            Name of the reference (e.g. tag name or branch name).
        ref (`str`):
            Full git ref on the Hub (e.g. `"refs/heads/main"` or `"refs/tags/v1.0"`).
        target_commit (`str`):
            OID of the target commit for the ref (e.g. `"e7da7f221d5bf496a48136c0cd264e630fe9fcc8"`)
    """

    name: str
    ref: str
    target_commit: str


@dataclass
class GitRefs:
    """
    Contains information about all git references for a repo on the Hub.

    Object is returned by [`list_repo_refs`].

    Attributes:
        branches (`List[GitRefInfo]`):
            A list of [`GitRefInfo`] containing information about branches on the repo.
        converts (`List[GitRefInfo]`):
            A list of [`GitRefInfo`] containing information about "convert" refs on the repo.
            Converts are refs used (internally) to push preprocessed data in Dataset repos.
        tags (`List[GitRefInfo]`):
            A list of [`GitRefInfo`] containing information about tags on the repo.
        pull_requests (`List[GitRefInfo]`, *optional*):
            A list of [`GitRefInfo`] containing information about pull requests on the repo.
            Only returned if `include_prs=True` is set.
    """

    branches: List[GitRefInfo]
    converts: List[GitRefInfo]
    tags: List[GitRefInfo]
    pull_requests: Optional[List[GitRefInfo]] = None


@dataclass
class GitCommitInfo:
    """
    Contains information about a git commit for a repo on the Hub. Check out [`list_repo_commits`] for more details.

    Attributes:
        commit_id (`str`):
            OID of the commit (e.g. `"e7da7f221d5bf496a48136c0cd264e630fe9fcc8"`)
        authors (`List[str]`):
            List of authors of the commit.
        created_at (`datetime`):
            Datetime when the commit was created.
        title (`str`):
            Title of the commit. This is a free-text value entered by the authors.
        message (`str`):
            Description of the commit. This is a free-text value entered by the authors.
        formatted_title (`str`):
            Title of the commit formatted as HTML. Only returned if `formatted=True` is set.
        formatted_message (`str`):
            Description of the commit formatted as HTML. Only returned if `formatted=True` is set.
    """

    commit_id: str

    authors: List[str]
    created_at: datetime
    title: str
    message: str

    formatted_title: Optional[str]
    formatted_message: Optional[str]


@dataclass
class UserLikes:
    """
    Contains information about a user likes on the Hub.

    Attributes:
        user (`str`):
            Name of the user for which we fetched the likes.
        total (`int`):
            Total number of likes.
        datasets (`List[str]`):
            List of datasets liked by the user (as repo_ids).
        models (`List[str]`):
            List of models liked by the user (as repo_ids).
        spaces (`List[str]`):
            List of spaces liked by the user (as repo_ids).
    """

    # Metadata
    user: str
    total: int

    # User likes
    datasets: List[str]
    models: List[str]
    spaces: List[str]


@dataclass
class Organization:
    """
    Contains information about an organization on the Hub.

    Attributes:
        avatar_url (`str`):
            URL of the organization's avatar.
        name (`str`):
            Name of the organization on the Hub (unique).
        fullname (`str`):
            Organization's full name.
    """

    avatar_url: str
    name: str
    fullname: str

    def __init__(self, **kwargs) -> None:
        self.avatar_url = kwargs.pop("avatarUrl", "")
        self.name = kwargs.pop("name", "")
        self.fullname = kwargs.pop("fullname", "")

        # forward compatibility
        self.__dict__.update(**kwargs)


@dataclass
class User:
    """
    Contains information about a user on the Hub.

    Attributes:
        username (`str`):
            Name of the user on the Hub (unique).
        fullname (`str`):
            User's full name.
        avatar_url (`str`):
            URL of the user's avatar.
        details (`str`, *optional*):
            User's details.
        is_following (`bool`, *optional*):
            Whether the authenticated user is following this user.
        is_pro (`bool`, *optional*):
            Whether the user is a pro user.
        num_models (`int`, *optional*):
            Number of models created by the user.
        num_datasets (`int`, *optional*):
            Number of datasets created by the user.
        num_spaces (`int`, *optional*):
            Number of spaces created by the user.
        num_discussions (`int`, *optional*):
            Number of discussions initiated by the user.
        num_papers (`int`, *optional*):
            Number of papers authored by the user.
        num_upvotes (`int`, *optional*):
            Number of upvotes received by the user.
        num_likes (`int`, *optional*):
            Number of likes given by the user.
        num_following (`int`, *optional*):
            Number of users this user is following.
        num_followers (`int`, *optional*):
            Number of users following this user.
        orgs (list of [`Organization`]):
            List of organizations the user is part of.
    """

    # Metadata
    username: str
    fullname: str
    avatar_url: str
    details: Optional[str] = None
    is_following: Optional[bool] = None
    is_pro: Optional[bool] = None
    num_models: Optional[int] = None
    num_datasets: Optional[int] = None
    num_spaces: Optional[int] = None
    num_discussions: Optional[int] = None
    num_papers: Optional[int] = None
    num_upvotes: Optional[int] = None
    num_likes: Optional[int] = None
    num_following: Optional[int] = None
    num_followers: Optional[int] = None
    orgs: List[Organization] = field(default_factory=list)

    def __init__(self, **kwargs) -> None:
        self.username = kwargs.pop("user", "")
        self.fullname = kwargs.pop("fullname", "")
        self.avatar_url = kwargs.pop("avatarUrl", "")
        self.is_following = kwargs.pop("isFollowing", None)
        self.is_pro = kwargs.pop("isPro", None)
        self.details = kwargs.pop("details", None)
        self.num_models = kwargs.pop("numModels", None)
        self.num_datasets = kwargs.pop("numDatasets", None)
        self.num_spaces = kwargs.pop("numSpaces", None)
        self.num_discussions = kwargs.pop("numDiscussions", None)
        self.num_papers = kwargs.pop("numPapers", None)
        self.num_upvotes = kwargs.pop("numUpvotes", None)
        self.num_likes = kwargs.pop("numLikes", None)
        self.num_following = kwargs.pop("numFollowing", None)
        self.num_followers = kwargs.pop("numFollowers", None)
        self.user_type = kwargs.pop("type", None)
        self.orgs = [Organization(**org) for org in kwargs.pop("orgs", [])]

        # forward compatibility
        self.__dict__.update(**kwargs)


@dataclass
class PaperInfo:
    """
    Contains information about a paper on the Hub.

    Attributes:
        id (`str`):
            arXiv paper ID.
        authors (`List[str]`, **optional**):
            Names of paper authors
        published_at (`datetime`, **optional**):
            Date paper published.
        title (`str`, **optional**):
            Title of the paper.
        summary (`str`, **optional**):
            Summary of the paper.
        upvotes (`int`, **optional**):
            Number of upvotes for the paper on the Hub.
        discussion_id (`str`, **optional**):
            Discussion ID for the paper on the Hub.
        source (`str`, **optional**):
            Source of the paper.
        comments (`int`, **optional**):
            Number of comments for the paper on the Hub.
        submitted_at (`datetime`, **optional**):
            Date paper appeared in daily papers on the Hub.
        submitted_by (`User`, **optional**):
            Information about who submitted the daily paper.
    """

    id: str
    authors: Optional[List[str]]
    published_at: Optional[datetime]
    title: Optional[str]
    summary: Optional[str]
    upvotes: Optional[int]
    discussion_id: Optional[str]
    source: Optional[str]
    comments: Optional[int]
    submitted_at: Optional[datetime]
    submitted_by: Optional[User]

    def __init__(self, **kwargs) -> None:
        paper = kwargs.pop("paper", {})
        self.id = kwargs.pop("id", None) or paper.pop("id", None)
        authors = paper.pop("authors", None) or kwargs.pop("authors", None)
        self.authors = [author.pop("name", None) for author in authors] if authors else None
        published_at = paper.pop("publishedAt", None) or kwargs.pop("publishedAt", None)
        self.published_at = parse_datetime(published_at) if published_at else None
        self.title = kwargs.pop("title", None)
        self.source = kwargs.pop("source", None)
        self.summary = paper.pop("summary", None) or kwargs.pop("summary", None)
        self.upvotes = paper.pop("upvotes", None) or kwargs.pop("upvotes", None)
        self.discussion_id = paper.pop("discussionId", None) or kwargs.pop("discussionId", None)
        self.comments = kwargs.pop("numComments", 0)
        submitted_at = kwargs.pop("publishedAt", None) or kwargs.pop("submittedOnDailyAt", None)
        self.submitted_at = parse_datetime(submitted_at) if submitted_at else None
        submitted_by = kwargs.pop("submittedBy", None) or kwargs.pop("submittedOnDailyBy", None)
        self.submitted_by = User(**submitted_by) if submitted_by else None

        # forward compatibility
        self.__dict__.update(**kwargs)


@dataclass
class LFSFileInfo:
    """
    Contains information about a file stored as LFS on a repo on the Hub.

    Used in the context of listing and permanently deleting LFS files from a repo to free-up space.
    See [`list_lfs_files`] and [`permanently_delete_lfs_files`] for more details.

    Git LFS files are tracked using SHA-256 object IDs, rather than file paths, to optimize performance
    This approach is necessary because a single object can be referenced by multiple paths across different commits,
    making it impractical to search and resolve these connections. Check out [our documentation](https://huggingface.co/docs/hub/storage-limits#advanced-track-lfs-file-references)
    to learn how to know which filename(s) is(are) associated with each SHA.

    Attributes:
        file_oid (`str`):
            SHA-256 object ID of the file. This is the identifier to pass when permanently deleting the file.
        filename (`str`):
            Possible filename for the LFS object. See the note above for more information.
        oid (`str`):
            OID of the LFS object.
        pushed_at (`datetime`):
            Date the LFS object was pushed to the repo.
        ref (`str`, *optional*):
            Ref where the LFS object has been pushed (if any).
        size (`int`):
            Size of the LFS object.

    Example:
        ```py
        >>> from huggingface_hub import HfApi
        >>> api = HfApi()
        >>> lfs_files = api.list_lfs_files("username/my-cool-repo")

        # Filter files files to delete based on a combination of `filename`, `pushed_at`, `ref` or `size`.
        # e.g. select only LFS files in the "checkpoints" folder
        >>> lfs_files_to_delete = (lfs_file for lfs_file in lfs_files if lfs_file.filename.startswith("checkpoints/"))

        # Permanently delete LFS files
        >>> api.permanently_delete_lfs_files("username/my-cool-repo", lfs_files_to_delete)
        ```
    """

    file_oid: str
    filename: str
    oid: str
    pushed_at: datetime
    ref: Optional[str]
    size: int

    def __init__(self, **kwargs) -> None:
        self.file_oid = kwargs.pop("fileOid")
        self.filename = kwargs.pop("filename")
        self.oid = kwargs.pop("oid")
        self.pushed_at = parse_datetime(kwargs.pop("pushedAt"))
        self.ref = kwargs.pop("ref", None)
        self.size = kwargs.pop("size")

        # forward compatibility
        self.__dict__.update(**kwargs)


def future_compatible(fn: CallableT) -> CallableT:
    """Wrap a method of `HfApi` to handle `run_as_future=True`.

    A method flagged as "future_compatible" will be called in a thread if `run_as_future=True` and return a
    `concurrent.futures.Future` instance. Otherwise, it will be called normally and return the result.
    """
    sig = inspect.signature(fn)
    args_params = list(sig.parameters)[1:]  # remove "self" from list

    @wraps(fn)
    def _inner(self, *args, **kwargs):
        # Get `run_as_future` value if provided (default to False)
        if "run_as_future" in kwargs:
            run_as_future = kwargs["run_as_future"]
            kwargs["run_as_future"] = False  # avoid recursion error
        else:
            run_as_future = False
            for param, value in zip(args_params, args):
                if param == "run_as_future":
                    run_as_future = value
                    break

        # Call the function in a thread if `run_as_future=True`
        if run_as_future:
            return self.run_as_future(fn, self, *args, **kwargs)

        # Otherwise, call the function normally
        return fn(self, *args, **kwargs)

    _inner.is_future_compatible = True  # type: ignore
    return _inner  # type: ignore


class HfApi:
    """
    Client to interact with the Hugging Face Hub via HTTP.

    The client is initialized with some high-level settings used in all requests
    made to the Hub (HF endpoint, authentication, user agents...). Using the `HfApi`
    client is preferred but not mandatory as all of its public methods are exposed
    directly at the root of `huggingface_hub`.

    Args:
        endpoint (`str`, *optional*):
            Endpoint of the Hub. Defaults to <https://huggingface.co>.
        token (Union[bool, str, None], optional):
            A valid user access token (string). Defaults to the locally saved
            token, which is the recommended method for authentication (see
            https://huggingface.co/docs/huggingface_hub/quick-start#authentication).
            To disable authentication, pass `False`.
        library_name (`str`, *optional*):
            The name of the library that is making the HTTP request. Will be added to
            the user-agent header. Example: `"transformers"`.
        library_version (`str`, *optional*):
            The version of the library that is making the HTTP request. Will be added
            to the user-agent header. Example: `"4.24.0"`.
        user_agent (`str`, `dict`, *optional*):
            The user agent info in the form of a dictionary or a single string. It will
            be completed with information about the installed packages.
        headers (`dict`, *optional*):
            Additional headers to be sent with each request. Example: `{"X-My-Header": "value"}`.
            Headers passed here are taking precedence over the default headers.
    """

    def __init__(
        self,
        endpoint: Optional[str] = None,
        token: Union[str, bool, None] = None,
        library_name: Optional[str] = None,
        library_version: Optional[str] = None,
        user_agent: Union[Dict, str, None] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> None:
        self.endpoint = endpoint if endpoint is not None else constants.ENDPOINT
        self.token = token
        self.library_name = library_name
        self.library_version = library_version
        self.user_agent = user_agent
        self.headers = headers
        self._thread_pool: Optional[ThreadPoolExecutor] = None

    def run_as_future(self, fn: Callable[..., R], *args, **kwargs) -> Future[R]:
        """
        Run a method in the background and return a Future instance.

        The main goal is to run methods without blocking the main thread (e.g. to push data during a training).
        Background jobs are queued to preserve order but are not ran in parallel. If you need to speed-up your scripts
        by parallelizing lots of call to the API, you must setup and use your own [ThreadPoolExecutor](https://docs.python.org/3/library/concurrent.futures.html#threadpoolexecutor).

        Note: Most-used methods like [`upload_file`], [`upload_folder`] and [`create_commit`] have a `run_as_future: bool`
        argument to directly call them in the background. This is equivalent to calling `api.run_as_future(...)` on them
        but less verbose.

        Args:
            fn (`Callable`):
                The method to run in the background.
            *args, **kwargs:
                Arguments with which the method will be called.

        Return:
            `Future`: a [Future](https://docs.python.org/3/library/concurrent.futures.html#future-objects) instance to
            get the result of the task.

        Example:
            ```py
            >>> from huggingface_hub import HfApi
            >>> api = HfApi()
            >>> future = api.run_as_future(api.whoami) # instant
            >>> future.done()
            False
            >>> future.result() # wait until complete and return result
            (...)
            >>> future.done()
            True
            ```
        """
        if self._thread_pool is None:
            self._thread_pool = ThreadPoolExecutor(max_workers=1)
        self._thread_pool
        return self._thread_pool.submit(fn, *args, **kwargs)

    @validate_hf_hub_args
    def whoami(self, token: Union[bool, str, None] = None) -> Dict:
        """
        Call HF API to know "whoami".

        Args:
            token (Union[bool, str, None], optional):
                A valid user access token (string). Defaults to the locally saved
                token, which is the recommended method for authentication (see
                https://huggingface.co/docs/huggingface_hub/quick-start#authentication).
                To disable authentication, pass `False`.
        """
        # Get the effective token using the helper function get_token
        effective_token = token or self.token or get_token() or True
        r = get_session().get(
            f"{self.endpoint}/api/whoami-v2",
            headers=self._build_hf_headers(token=effective_token),
        )
        try:
            hf_raise_for_status(r)
        except HTTPError as e:
            error_message = "Invalid user token."
            # Check which token is the effective one and generate the error message accordingly
            if effective_token == _get_token_from_google_colab():
                error_message += " The token from Google Colab vault is invalid. Please update it from the UI."
            elif effective_token == _get_token_from_environment():
                error_message += (
                    " The token from HF_TOKEN environment variable is invalid. "
                    "Note that HF_TOKEN takes precedence over `huggingface-cli login`."
                )
            elif effective_token == _get_token_from_file():
                error_message += " The token stored is invalid. Please run `huggingface-cli login` to update it."
            raise HTTPError(error_message, request=e.request, response=e.response) from e
        return r.json()

    @_deprecate_method(
        version="1.0",
        message=(
            "Permissions are more complex than when `get_token_permission` was first introduced. "
            "OAuth and fine-grain tokens allows for more detailed permissions. "
            "If you need to know the permissions associated with a token, please use `whoami` and check the `'auth'` key."
        ),
    )
    def get_token_permission(
        self, token: Union[bool, str, None] = None
    ) -> Literal["read", "write", "fineGrained", None]:
        """
        Check if a given `token` is valid and return its permissions.

        <Tip warning={true}>

        This method is deprecated and will be removed in version 1.0. Permissions are more complex than when
        `get_token_permission` was first introduced. OAuth and fine-grain tokens allows for more detailed permissions.
        If you need to know the permissions associated with a token, please use `whoami` and check the `'auth'` key.

        </Tip>

        For more details about tokens, please refer to https://huggingface.co/docs/hub/security-tokens#what-are-user-access-tokens.

        Args:
            token (Union[bool, str, None], optional):
                A valid user access token (string). Defaults to the locally saved
                token, which is the recommended method for authentication (see
                https://huggingface.co/docs/huggingface_hub/quick-start#authentication).
                To disable authentication, pass `False`.

        Returns:
            `Literal["read", "write", "fineGrained", None]`: Permission granted by the token ("read" or "write"). Returns `None` if no
            token passed, if token is invalid or if role is not returned by the server. This typically happens when the token is an OAuth token.
        """
        try:
            return self.whoami(token=token)["auth"]["accessToken"]["role"]
        except (LocalTokenNotFoundError, HTTPError, KeyError):
            return None

    def get_model_tags(self) -> Dict:
        """
        List all valid model tags as a nested namespace object
        """
        path = f"{self.endpoint}/api/models-tags-by-type"
        r = get_session().get(path)
        hf_raise_for_status(r)
        return r.json()

    def get_dataset_tags(self) -> Dict:
        """
        List all valid dataset tags as a nested namespace object.
        """
        path = f"{self.endpoint}/api/datasets-tags-by-type"
        r = get_session().get(path)
        hf_raise_for_status(r)
        return r.json()

    @validate_hf_hub_args
    def list_models(
        self,
        *,
        # Search-query parameter
        filter: Union[str, Iterable[str], None] = None,
        author: Optional[str] = None,
        gated: Optional[bool] = None,
        inference: Optional[Literal["warm"]] = None,
        inference_provider: Optional[Union[Literal["all"], "PROVIDER_T", List["PROVIDER_T"]]] = None,
        library: Optional[Union[str, List[str]]] = None,
        language: Optional[Union[str, List[str]]] = None,
        model_name: Optional[str] = None,
        task: Optional[Union[str, List[str]]] = None,
        trained_dataset: Optional[Union[str, List[str]]] = None,
        tags: Optional[Union[str, List[str]]] = None,
        search: Optional[str] = None,
        pipeline_tag: Optional[str] = None,
        emissions_thresholds: Optional[Tuple[float, float]] = None,
        # Sorting and pagination parameters
        sort: Union[Literal["last_modified"], str, None] = None,
        direction: Optional[Literal[-1]] = None,
        limit: Optional[int] = None,
        # Additional data to fetch
        expand: Optional[List[ExpandModelProperty_T]] = None,
        full: Optional[bool] = None,
        cardData: bool = False,
        fetch_config: bool = False,
        token: Union[bool, str, None] = None,
    ) -> Iterable[ModelInfo]:
        """
        List models hosted on the Huggingface Hub, given some filters.

        Args:
            filter (`str` or `Iterable[str]`, *optional*):
                A string or list of string to filter models on the Hub.
            author (`str`, *optional*):
                A string which identify the author (user or organization) of the
                returned models.
            gated (`bool`, *optional*):
                A boolean to filter models on the Hub that are gated or not. By default, all models are returned.
                If `gated=True` is passed, only gated models are returned.
                If `gated=False` is passed, only non-gated models are returned.
            inference (`Literal["warm"]`, *optional*):
                If "warm", filter models on the Hub currently served by at least one provider.
            inference_provider (`Literal["all"]` or `str`, *optional*):
                A string to filter models on the Hub that are served by a specific provider.
                Pass `"all"` to get all models served by at least one provider.
            library (`str` or `List`, *optional*):
                A string or list of strings of foundational libraries models were
                originally trained from, such as pytorch, tensorflow, or allennlp.
            language (`str` or `List`, *optional*):
                A string or list of strings of languages, both by name and country
                code, such as "en" or "English"
            model_name (`str`, *optional*):
                A string that contain complete or partial names for models on the
                Hub, such as "bert" or "bert-base-cased"
            task (`str` or `List`, *optional*):
                A string or list of strings of tasks models were designed for, such
                as: "fill-mask" or "automatic-speech-recognition"
            trained_dataset (`str` or `List`, *optional*):
                A string tag or a list of string tags of the trained dataset for a
                model on the Hub.
            tags (`str` or `List`, *optional*):
                A string tag or a list of tags to filter models on the Hub by, such
                as `text-generation` or `spacy`.
            search (`str`, *optional*):
                A string that will be contained in the returned model ids.
            pipeline_tag (`str`, *optional*):
                A string pipeline tag to filter models on the Hub by, such as `summarization`.
            emissions_thresholds (`Tuple`, *optional*):
                A tuple of two ints or floats representing a minimum and maximum
                carbon footprint to filter the resulting models with in grams.
            sort (`Literal["last_modified"]` or `str`, *optional*):
                The key with which to sort the resulting models. Possible values are "last_modified", "trending_score",
                "created_at", "downloads" and "likes".
            direction (`Literal[-1]` or `int`, *optional*):
                Direction in which to sort. The value `-1` sorts by descending
                order while all other values sort by ascending order.
            limit (`int`, *optional*):
                The limit on the number of models fetched. Leaving this option
                to `None` fetches all models.
            expand (`List[ExpandModelProperty_T]`, *optional*):
                List properties to return in the response. When used, only the properties in the list will be returned.
                This parameter cannot be used if `full`, `cardData` or `fetch_config` are passed.
                Possible values are `"author"`, `"baseModels"`, `"cardData"`, `"childrenModelCount"`, `"config"`, `"createdAt"`, `"disabled"`, `"downloads"`, `"downloadsAllTime"`, `"gated"`, `"gguf"`, `"inference"`, `"inferenceProviderMapping"`, `"lastModified"`, `"library_name"`, `"likes"`, `"mask_token"`, `"model-index"`, `"pipeline_tag"`, `"private"`, `"safetensors"`, `"sha"`, `"siblings"`, `"spaces"`, `"tags"`, `"transformersInfo"`, `"trendingScore"`, `"widgetData"`, `"usedStorage"`, `"resourceGroup"` and `"xetEnabled"`.
            full (`bool`, *optional*):
                Whether to fetch all model data, including the `last_modified`,
                the `sha`, the files and the `tags`. This is set to `True` by
                default when using a filter.
            cardData (`bool`, *optional*):
                Whether to grab the metadata for the model as well. Can contain
                useful information such as carbon emissions, metrics, and
                datasets trained on.
            fetch_config (`bool`, *optional*):
                Whether to fetch the model configs as well. This is not included
                in `full` due to its size.
            token (Union[bool, str, None], optional):
                A valid user access token (string). Defaults to the locally saved
                token, which is the recommended method for authentication (see
                https://huggingface.co/docs/huggingface_hub/quick-start#authentication).
                To disable authentication, pass `False`.


        Returns:
            `Iterable[ModelInfo]`: an iterable of [`huggingface_hub.hf_api.ModelInfo`] objects.

        Example:

        ```python
        >>> from huggingface_hub import HfApi

        >>> api = HfApi()

        # List all models
        >>> api.list_models()

        # List text classification models
        >>> api.list_models(filter="text-classification")

        # List models from the KerasHub library
        >>> api.list_models(filter="keras-hub")

        # List models served by Cohere
        >>> api.list_models(inference_provider="cohere")

        # List models with "bert" in their name
        >>> api.list_models(search="bert")

        # List models with "bert" in their name and pushed by google
        >>> api.list_models(search="bert", author="google")
        ```
        """
        if expand and (full or cardData or fetch_config):
            raise ValueError("`expand` cannot be used if `full`, `cardData` or `fetch_config` are passed.")

        if emissions_thresholds is not None and cardData is None:
            raise ValueError("`emissions_thresholds` were passed without setting `cardData=True`.")

        path = f"{self.endpoint}/api/models"
        headers = self._build_hf_headers(token=token)
        params: Dict[str, Any] = {}

        # Build the filter list
        filter_list: List[str] = []
        if filter:
            filter_list.extend([filter] if isinstance(filter, str) else filter)
        if library:
            filter_list.extend([library] if isinstance(library, str) else library)
        if task:
            filter_list.extend([task] if isinstance(task, str) else task)
        if trained_dataset:
            if isinstance(trained_dataset, str):
                trained_dataset = [trained_dataset]
            for dataset in trained_dataset:
                if not dataset.startswith("dataset:"):
                    dataset = f"dataset:{dataset}"
                filter_list.append(dataset)
        if language:
            filter_list.extend([language] if isinstance(language, str) else language)
        if tags:
            filter_list.extend([tags] if isinstance(tags, str) else tags)
        if len(filter_list) > 0:
            params["filter"] = filter_list

        # Handle other query params
        if author:
            params["author"] = author
        if gated is not None:
            params["gated"] = gated
        if inference is not None:
            params["inference"] = inference
        if inference_provider is not None:
            params["inference_provider"] = inference_provider
        if pipeline_tag:
            params["pipeline_tag"] = pipeline_tag
        search_list = []
        if model_name:
            search_list.append(model_name)
        if search:
            search_list.append(search)
        if len(search_list) > 0:
            params["search"] = search_list
        if sort is not None:
            params["sort"] = (
                "lastModified"
                if sort == "last_modified"
                else "trendingScore"
                if sort == "trending_score"
                else "createdAt"
                if sort == "created_at"
                else sort
            )
        if direction is not None:
            params["direction"] = direction
        if limit is not None:
            params["limit"] = limit

        # Request additional data
        if full:
            params["full"] = True
        if fetch_config:
            params["config"] = True
        if cardData:
            params["cardData"] = True
        if expand:
            params["expand"] = expand

        # `items` is a generator
        items = paginate(path, params=params, headers=headers)
        if limit is not None:
            items = islice(items, limit)  # Do not iterate over all pages
        for item in items:
            if "siblings" not in item:
                item["siblings"] = None
            model_info = ModelInfo(**item)
            if emissions_thresholds is None or _is_emission_within_threshold(model_info, *emissions_thresholds):
                yield model_info

    @validate_hf_hub_args
    def list_datasets(
        self,
        *,
        # Search-query parameter
        filter: Union[str, Iterable[str], None] = None,
        author: Optional[str] = None,
        benchmark: Optional[Union[str, List[str]]] = None,
        dataset_name: Optional[str] = None,
        gated: Optional[bool] = None,
        language_creators: Optional[Union[str, List[str]]] = None,
        language: Optional[Union[str, List[str]]] = None,
        multilinguality: Optional[Union[str, List[str]]] = None,
        size_categories: Optional[Union[str, List[str]]] = None,
        tags: Optional[Union[str, List[str]]] = None,
        task_categories: Optional[Union[str, List[str]]] = None,
        task_ids: Optional[Union[str, List[str]]] = None,
        search: Optional[str] = None,
        # Sorting and pagination parameters
        sort: Optional[Union[Literal["last_modified"], str]] = None,
        direction: Optional[Literal[-1]] = None,
        limit: Optional[int] = None,
        # Additional data to fetch
        expand: Optional[List[ExpandDatasetProperty_T]] = None,
        full: Optional[bool] = None,
        token: Union[bool, str, None] = None,
    ) -> Iterable[DatasetInfo]:
        """
        List datasets hosted on the Huggingface Hub, given some filters.

        Args:
            filter (`str` or `Iterable[str]`, *optional*):
                A string or list of string to filter datasets on the hub.
            author (`str`, *optional*):
                A string which identify the author of the returned datasets.
            benchmark (`str` or `List`, *optional*):
                A string or list of strings that can be used to identify datasets on
                the Hub by their official benchmark.
            dataset_name (`str`, *optional*):
                A string or list of strings that can be used to identify datasets on
                the Hub by its name, such as `SQAC` or `wikineural`
            gated (`bool`, *optional*):
                A boolean to filter datasets on the Hub that are gated or not. By default, all datasets are returned.
                If `gated=True` is passed, only gated datasets are returned.
                If `gated=False` is passed, only non-gated datasets are returned.
            language_creators (`str` or `List`, *optional*):
                A string or list of strings that can be used to identify datasets on
                the Hub with how the data was curated, such as `crowdsourced` or
                `machine_generated`.
            language (`str` or `List`, *optional*):
                A string or list of strings representing a two-character language to
                filter datasets by on the Hub.
            multilinguality (`str` or `List`, *optional*):
                A string or list of strings representing a filter for datasets that
                contain multiple languages.
            size_categories (`str` or `List`, *optional*):
                A string or list of strings that can be used to identify datasets on
                the Hub by the size of the dataset such as `100K<n<1M` or
                `1M<n<10M`.
            tags (`str` or `List`, *optional*):
                A string tag or a list of tags to filter datasets on the Hub.
            task_categories (`str` or `List`, *optional*):
                A string or list of strings that can be used to identify datasets on
                the Hub by the designed task, such as `audio_classification` or
                `named_entity_recognition`.
            task_ids (`str` or `List`, *optional*):
                A string or list of strings that can be used to identify datasets on
                the Hub by the specific task such as `speech_emotion_recognition` or
                `paraphrase`.
            search (`str`, *optional*):
                A string that will be contained in the returned datasets.
            sort (`Literal["last_modified"]` or `str`, *optional*):
                The key with which to sort the resulting models. Possible values are "last_modified", "trending_score",
                "created_at", "downloads" and "likes".
            direction (`Literal[-1]` or `int`, *optional*):
                Direction in which to sort. The value `-1` sorts by descending
                order while all other values sort by ascending order.
            limit (`int`, *optional*):
                The limit on the number of datasets fetched. Leaving this option
                to `None` fetches all datasets.
            expand (`List[ExpandDatasetProperty_T]`, *optional*):
                List properties to return in the response. When used, only the properties in the list will be returned.
                This parameter cannot be used if `full` is passed.
                Possible values are `"author"`, `"cardData"`, `"citation"`, `"createdAt"`, `"disabled"`, `"description"`, `"downloads"`, `"downloadsAllTime"`, `"gated"`, `"lastModified"`, `"likes"`, `"paperswithcode_id"`, `"private"`, `"siblings"`, `"sha"`, `"tags"`, `"trendingScore"`, `"usedStorage"`, `"resourceGroup"` and `"xetEnabled"`.
            full (`bool`, *optional*):
                Whether to fetch all dataset data, including the `last_modified`,
                the `card_data` and  the files. Can contain useful information such as the
                PapersWithCode ID.
            token (Union[bool, str, None], optional):
                A valid user access token (string). Defaults to the locally saved
                token, which is the recommended method for authentication (see
                https://huggingface.co/docs/huggingface_hub/quick-start#authentication).
                To disable authentication, pass `False`.

        Returns:
            `Iterable[DatasetInfo]`: an iterable of [`huggingface_hub.hf_api.DatasetInfo`] objects.

        Example usage with the `filter` argument:

        ```python
        >>> from huggingface_hub import HfApi

        >>> api = HfApi()

        # List all datasets
        >>> api.list_datasets()


        # List only the text classification datasets
        >>> api.list_datasets(filter="task_categories:text-classification")


        # List only the datasets in russian for language modeling
        >>> api.list_datasets(
        ...     filter=("language:ru", "task_ids:language-modeling")
        ... )

        # List FiftyOne datasets (identified by the tag "fiftyone" in dataset card)
        >>> api.list_datasets(tags="fiftyone")
        ```

        Example usage with the `search` argument:

        ```python
        >>> from huggingface_hub import HfApi

        >>> api = HfApi()

        # List all datasets with "text" in their name
        >>> api.list_datasets(search="text")

        # List all datasets with "text" in their name made by google
        >>> api.list_datasets(search="text", author="google")
        ```
        """
        if expand and full:
            raise ValueError("`expand` cannot be used if `full` is passed.")

        path = f"{self.endpoint}/api/datasets"
        headers = self._build_hf_headers(token=token)
        params: Dict[str, Any] = {}

        # Build `filter` list
        filter_list = []
        if filter is not None:
            if isinstance(filter, str):
                filter_list.append(filter)
            else:
                filter_list.extend(filter)
        for key, value in (
            ("benchmark", benchmark),
            ("language_creators", language_creators),
            ("language", language),
            ("multilinguality", multilinguality),
            ("size_categories", size_categories),
            ("task_categories", task_categories),
            ("task_ids", task_ids),
        ):
            if value:
                if isinstance(value, str):
                    value = [value]
                for value_item in value:
                    if not value_item.startswith(f"{key}:"):
                        data = f"{key}:{value_item}"
                    filter_list.append(data)
        if tags is not None:
            filter_list.extend([tags] if isinstance(tags, str) else tags)
        if len(filter_list) > 0:
            params["filter"] = filter_list

        # Handle other query params
        if author:
            params["author"] = author
        if gated is not None:
            params["gated"] = gated
        search_list = []
        if dataset_name:
            search_list.append(dataset_name)
        if search:
            search_list.append(search)
        if len(search_list) > 0:
            params["search"] = search_list
        if sort is not None:
            params["sort"] = (
                "lastModified"
                if sort == "last_modified"
                else "trendingScore"
                if sort == "trending_score"
                else "createdAt"
                if sort == "created_at"
                else sort
            )
        if direction is not None:
            params["direction"] = direction
        if limit is not None:
            params["limit"] = limit

        # Request additional data
        if expand:
            params["expand"] = expand
        if full:
            params["full"] = True

        items = paginate(path, params=params, headers=headers)
        if limit is not None:
            items = islice(items, limit)  # Do not iterate over all pages
        for item in items:
            if "siblings" not in item:
                item["siblings"] = None
            yield DatasetInfo(**item)

    @validate_hf_hub_args
    def list_spaces(
        self,
        *,
        # Search-query parameter
        filter: Union[str, Iterable[str], None] = None,
        author: Optional[str] = None,
        search: Optional[str] = None,
        datasets: Union[str, Iterable[str], None] = None,
        models: Union[str, Iterable[str], None] = None,
        linked: bool = False,
        # Sorting and pagination parameters
        sort: Union[Literal["last_modified"], str, None] = None,
        direction: Optional[Literal[-1]] = None,
        limit: Optional[int] = None,
        # Additional data to fetch
        expand: Optional[List[ExpandSpaceProperty_T]] = None,
        full: Optional[bool] = None,
        token: Union[bool, str, None] = None,
    ) -> Iterable[SpaceInfo]:
        """
        List spaces hosted on the Huggingface Hub, given some filters.

        Args:
            filter (`str` or `Iterable`, *optional*):
                A string tag or list of tags that can be used to identify Spaces on the Hub.
            author (`str`, *optional*):
                A string which identify the author of the returned Spaces.
            search (`str`, *optional*):
                A string that will be contained in the returned Spaces.
            datasets (`str` or `Iterable`, *optional*):
                Whether to return Spaces that make use of a dataset.
                The name of a specific dataset can be passed as a string.
            models (`str` or `Iterable`, *optional*):
                Whether to return Spaces that make use of a model.
                The name of a specific model can be passed as a string.
            linked (`bool`, *optional*):
                Whether to return Spaces that make use of either a model or a dataset.
            sort (`Literal["last_modified"]` or `str`, *optional*):
                The key with which to sort the resulting models. Possible values are "last_modified", "trending_score",
                "created_at" and "likes".
            direction (`Literal[-1]` or `int`, *optional*):
                Direction in which to sort. The value `-1` sorts by descending
                order while all other values sort by ascending order.
            limit (`int`, *optional*):
                The limit on the number of Spaces fetched. Leaving this option
                to `None` fetches all Spaces.
            expand (`List[ExpandSpaceProperty_T]`, *optional*):
                List properties to return in the response. When used, only the properties in the list will be returned.
                This parameter cannot be used if `full` is passed.
                Possible values are `"author"`, `"cardData"`, `"datasets"`, `"disabled"`, `"lastModified"`, `"createdAt"`, `"likes"`, `"models"`, `"private"`, `"runtime"`, `"sdk"`, `"siblings"`, `"sha"`, `"subdomain"`, `"tags"`, `"trendingScore"`, `"usedStorage"`, `"resourceGroup"` and `"xetEnabled"`.
            full (`bool`, *optional*):
                Whether to fetch all Spaces data, including the `last_modified`, `siblings`
                and `card_data` fields.
            token (Union[bool, str, None], optional):
                A valid user access token (string). Defaults to the locally saved
                token, which is the recommended method for authentication (see
                https://huggingface.co/docs/huggingface_hub/quick-start#authentication).
                To disable authentication, pass `False`.

        Returns:
            `Iterable[SpaceInfo]`: an iterable of [`huggingface_hub.hf_api.SpaceInfo`] objects.
        """
        if expand and full:
            raise ValueError("`expand` cannot be used if `full` is passed.")

        path = f"{self.endpoint}/api/spaces"
        headers = self._build_hf_headers(token=token)
        params: Dict[str, Any] = {}
        if filter is not None:
            params["filter"] = filter
        if author is not None:
            params["author"] = author
        if search is not None:
            params["search"] = search
        if sort is not None:
            params["sort"] = (
                "lastModified"
                if sort == "last_modified"
                else "trendingScore"
                if sort == "trending_score"
                else "createdAt"
                if sort == "created_at"
                else sort
            )
        if direction is not None:
            params["direction"] = direction
        if limit is not None:
            params["limit"] = limit
        if linked:
            params["linked"] = True
        if datasets is not None:
            params["datasets"] = datasets
        if models is not None:
            params["models"] = models

        # Request additional data
        if expand:
            params["expand"] = expand
        if full:
            params["full"] = True

        items = paginate(path, params=params, headers=headers)
        if limit is not None:
            items = islice(items, limit)  # Do not iterate over all pages
        for item in items:
            if "siblings" not in item:
                item["siblings"] = None
            yield SpaceInfo(**item)

    @validate_hf_hub_args
    def unlike(
        self,
        repo_id: str,
        *,
        token: Union[bool, str, None] = None,
        repo_type: Optional[str] = None,
    ) -> None:
        """
        Unlike a given repo on the Hub (e.g. remove from favorite list).

        To prevent spam usage, it is not possible to `like` a repository from a script.

        See also [`list_liked_repos`].

        Args:
            repo_id (`str`):
                The repository to unlike. Example: `"user/my-cool-model"`.

            token (Union[bool, str, None], optional):
                A valid user access token (string). Defaults to the locally saved
                token, which is the recommended method for authentication (see
                https://huggingface.co/docs/huggingface_hub/quick-start#authentication).
                To disable authentication, pass `False`.

            repo_type (`str`, *optional*):
                Set to `"dataset"` or `"space"` if unliking a dataset or space, `None` or
                `"model"` if unliking a model. Default is `None`.

        Raises:
            [`~utils.RepositoryNotFoundError`]:
                If repository is not found (error 404): wrong repo_id/repo_type, private
                but not authenticated or repo does not exist.

        Example:
        ```python
        >>> from huggingface_hub import list_liked_repos, unlike
        >>> "gpt2" in list_liked_repos().models # we assume you have already liked gpt2
        True
        >>> unlike("gpt2")
        >>> "gpt2" in list_liked_repos().models
        False
        ```
        """
        if repo_type is None:
            repo_type = constants.REPO_TYPE_MODEL
        response = get_session().delete(
            url=f"{self.endpoint}/api/{repo_type}s/{repo_id}/like", headers=self._build_hf_headers(token=token)
        )
        hf_raise_for_status(response)

    @validate_hf_hub_args
    def list_liked_repos(
        self,
        user: Optional[str] = None,
        *,
        token: Union[bool, str, None] = None,
    ) -> UserLikes:
        """
        List all public repos liked by a user on huggingface.co.

        This list is public so token is optional. If `user` is not passed, it defaults to
        the logged in user.

        See also [`unlike`].

        Args:
            user (`str`, *optional*):
                Name of the user for which you want to fetch the likes.
            token (Union[bool, str, None], optional):
                A valid user access token (string). Defaults to the locally saved
                token, which is the recommended method for authentication (see
                https://huggingface.co/docs/huggingface_hub/quick-start#authentication).
                To disable authentication, pass `False`.

        Returns:
            [`UserLikes`]: object containing the user name and 3 lists of repo ids (1 for
            models, 1 for datasets and 1 for Spaces).

        Raises:
            [`ValueError`](https://docs.python.org/3/library/exceptions.html#ValueError)
                If `user` is not passed and no token found (either from argument or from machine).

        Example:
        ```python
        >>> from huggingface_hub import list_liked_repos

        >>> likes = list_liked_repos("julien-c")

        >>> likes.user
        "julien-c"

        >>> likes.models
        ["osanseviero/streamlit_1.15", "Xhaheen/ChatGPT_HF", ...]
        ```
        """
        # User is either provided explicitly or retrieved from current token.
        if user is None:
            me = self.whoami(token=token)
            if me["type"] == "user":
                user = me["name"]
            else:
                raise ValueError(
                    "Cannot list liked repos. You must provide a 'user' as input or be logged in as a user."
                )

        path = f"{self.endpoint}/api/users/{user}/likes"
        headers = self._build_hf_headers(token=token)

        likes = list(paginate(path, params={}, headers=headers))
        # Looping over a list of items similar to:
        #   {
        #       'createdAt': '2021-09-09T21:53:27.000Z',
        #       'repo': {
        #           'name': 'PaddlePaddle/PaddleOCR',
        #           'type': 'space'
        #        }
        #   }
        # Let's loop 3 times over the received list. Less efficient but more straightforward to read.
        return UserLikes(
            user=user,
            total=len(likes),
            models=[like["repo"]["name"] for like in likes if like["repo"]["type"] == "model"],
            datasets=[like["repo"]["name"] for like in likes if like["repo"]["type"] == "dataset"],
            spaces=[like["repo"]["name"] for like in likes if like["repo"]["type"] == "space"],
        )

    @validate_hf_hub_args
    def list_repo_likers(
        self,
        repo_id: str,
        *,
        repo_type: Optional[str] = None,
        token: Union[bool, str, None] = None,
    ) -> Iterable[User]:
        """
        List all users who liked a given repo on the hugging Face Hub.

        See also [`list_liked_repos`].

        Args:
            repo_id (`str`):
                The repository to retrieve . Example: `"user/my-cool-model"`.

            token (Union[bool, str, None], optional):
                A valid user access token (string). Defaults to the locally saved
                token, which is the recommended method for authentication (see
                https://huggingface.co/docs/huggingface_hub/quick-start#authentication).
                To disable authentication, pass `False`.

            repo_type (`str`, *optional*):
                Set to `"dataset"` or `"space"` if uploading to a dataset or
                space, `None` or `"model"` if uploading to a model. Default is
                `None`.

        Returns:
            `Iterable[User]`: an iterable of [`huggingface_hub.hf_api.User`] objects.
        """

        # Construct the API endpoint
        if repo_type is None:
            repo_type = constants.REPO_TYPE_MODEL
        path = f"{self.endpoint}/api/{repo_type}s/{repo_id}/likers"
        for liker in paginate(path, params={}, headers=self._build_hf_headers(token=token)):
            yield User(username=liker["user"], fullname=liker["fullname"], avatar_url=liker["avatarUrl"])

    @validate_hf_hub_args
    def model_info(
        self,
        repo_id: str,
        *,
        revision: Optional[str] = None,
        timeout: Optional[float] = None,
        securityStatus: Optional[bool] = None,
        files_metadata: bool = False,
        expand: Optional[List[ExpandModelProperty_T]] = None,
        token: Union[bool, str, None] = None,
    ) -> ModelInfo:
        """
        Get info on one specific model on huggingface.co

        Model can be private if you pass an acceptable token or are logged in.

        Args:
            repo_id (`str`):
                A namespace (user or an organization) and a repo name separated
                by a `/`.
            revision (`str`, *optional*):
                The revision of the model repository from which to get the
                information.
            timeout (`float`, *optional*):
                Whether to set a timeout for the request to the Hub.
            securityStatus (`bool`, *optional*):
                Whether to retrieve the security status from the model
                repository as well. The security status will be returned in the `security_repo_status` field.
            files_metadata (`bool`, *optional*):
                Whether or not to retrieve metadata for files in the repository
                (size, LFS metadata, etc). Defaults to `False`.
            expand (`List[ExpandModelProperty_T]`, *optional*):
                List properties to return in the response. When used, only the properties in the list will be returned.
                This parameter cannot be used if `securityStatus` or `files_metadata` are passed.
                Possible values are `"author"`, `"baseModels"`, `"cardData"`, `"childrenModelCount"`, `"config"`, `"createdAt"`, `"disabled"`, `"downloads"`, `"downloadsAllTime"`, `"gated"`, `"gguf"`, `"inference"`, `"inferenceProviderMapping"`, `"lastModified"`, `"library_name"`, `"likes"`, `"mask_token"`, `"model-index"`, `"pipeline_tag"`, `"private"`, `"safetensors"`, `"sha"`, `"siblings"`, `"spaces"`, `"tags"`, `"transformersInfo"`, `"trendingScore"`, `"widgetData"`, `"usedStorage"`, `"resourceGroup"` and `"xetEnabled"`.
            token (Union[bool, str, None], optional):
                A valid user access token (string). Defaults to the locally saved
                token, which is the recommended method for authentication (see
                https://huggingface.co/docs/huggingface_hub/quick-start#authentication).
                To disable authentication, pass `False`.

        Returns:
            [`huggingface_hub.hf_api.ModelInfo`]: The model repository information.

        <Tip>

        Raises the following errors:

            - [`~utils.RepositoryNotFoundError`]
              If the repository to download from cannot be found. This may be because it doesn't exist,
              or because it is set to `private` and you do not have access.
            - [`~utils.RevisionNotFoundError`]
              If the revision to download from cannot be found.

        </Tip>
        """
        if expand and (securityStatus or files_metadata):
            raise ValueError("`expand` cannot be used if `securityStatus` or `files_metadata` are set.")

        headers = self._build_hf_headers(token=token)
        path = (
            f"{self.endpoint}/api/models/{repo_id}"
            if revision is None
            else (f"{self.endpoint}/api/models/{repo_id}/revision/{quote(revision, safe='')}")
        )
        params: Dict = {}
        if securityStatus:
            params["securityStatus"] = True
        if files_metadata:
            params["blobs"] = True
        if expand:
            params["expand"] = expand
        r = get_session().get(path, headers=headers, timeout=timeout, params=params)
        hf_raise_for_status(r)
        data = r.json()
        return ModelInfo(**data)

    @validate_hf_hub_args
    def dataset_info(
        self,
        repo_id: str,
        *,
        revision: Optional[str] = None,
        timeout: Optional[float] = None,
        files_metadata: bool = False,
        expand: Optional[List[ExpandDatasetProperty_T]] = None,
        token: Union[bool, str, None] = None,
    ) -> DatasetInfo:
        """
        Get info on one specific dataset on huggingface.co.

        Dataset can be private if you pass an acceptable token.

        Args:
            repo_id (`str`):
                A namespace (user or an organization) and a repo name separated
                by a `/`.
            revision (`str`, *optional*):
                The revision of the dataset repository from which to get the
                information.
            timeout (`float`, *optional*):
                Whether to set a timeout for the request to the Hub.
            files_metadata (`bool`, *optional*):
                Whether or not to retrieve metadata for files in the repository
                (size, LFS metadata, etc). Defaults to `False`.
            expand (`List[ExpandDatasetProperty_T]`, *optional*):
                List properties to return in the response. When used, only the properties in the list will be returned.
                This parameter cannot be used if `files_metadata` is passed.
                Possible values are `"author"`, `"cardData"`, `"citation"`, `"createdAt"`, `"disabled"`, `"description"`, `"downloads"`, `"downloadsAllTime"`, `"gated"`, `"lastModified"`, `"likes"`, `"paperswithcode_id"`, `"private"`, `"siblings"`, `"sha"`, `"tags"`, `"trendingScore"`,`"usedStorage"`, `"resourceGroup"` and `"xetEnabled"`.
            token (Union[bool, str, None], optional):
                A valid user access token (string). Defaults to the locally saved
                token, which is the recommended method for authentication (see
                https://huggingface.co/docs/huggingface_hub/quick-start#authentication).
                To disable authentication, pass `False`.

        Returns:
            [`hf_api.DatasetInfo`]: The dataset repository information.

        <Tip>

        Raises the following errors:

            - [`~utils.RepositoryNotFoundError`]
              If the repository to download from cannot be found. This may be because it doesn't exist,
              or because it is set to `private` and you do not have access.
            - [`~utils.RevisionNotFoundError`]
              If the revision to download from cannot be found.

        </Tip>
        """
        if expand and files_metadata:
            raise ValueError("`expand` cannot be used if `files_metadata` is set.")

        headers = self._build_hf_headers(token=token)
        path = (
            f"{self.endpoint}/api/datasets/{repo_id}"
            if revision is None
            else (f"{self.endpoint}/api/datasets/{repo_id}/revision/{quote(revision, safe='')}")
        )
        params: Dict = {}
        if files_metadata:
            params["blobs"] = True
        if expand:
            params["expand"] = expand

        r = get_session().get(path, headers=headers, timeout=timeout, params=params)
        hf_raise_for_status(r)
        data = r.json()
        return DatasetInfo(**data)

    @validate_hf_hub_args
    def space_info(
        self,
        repo_id: str,
        *,
        revision: Optional[str] = None,
        timeout: Optional[float] = None,
        files_metadata: bool = False,
        expand: Optional[List[ExpandSpaceProperty_T]] = None,
        token: Union[bool, str, None] = None,
    ) -> SpaceInfo:
        """
        Get info on one specific Space on huggingface.co.

        Space can be private if you pass an acceptable token.

        Args:
            repo_id (`str`):
                A namespace (user or an organization) and a repo name separated
                by a `/`.
            revision (`str`, *optional*):
                The revision of the space repository from which to get the
                information.
            timeout (`float`, *optional*):
                Whether to set a timeout for the request to the Hub.
            files_metadata (`bool`, *optional*):
                Whether or not to retrieve metadata for files in the repository
                (size, LFS metadata, etc). Defaults to `False`.
            expand (`List[ExpandSpaceProperty_T]`, *optional*):
                List properties to return in the response. When used, only the properties in the list will be returned.
                This parameter cannot be used if `full` is passed.
                Possible values are `"author"`, `"cardData"`, `"createdAt"`, `"datasets"`, `"disabled"`, `"lastModified"`, `"likes"`, `"models"`, `"private"`, `"runtime"`, `"sdk"`, `"siblings"`, `"sha"`, `"subdomain"`, `"tags"`, `"trendingScore"`, `"usedStorage"`, `"resourceGroup"` and `"xetEnabled"`.
            token (Union[bool, str, None], optional):
                A valid user access token (string). Defaults to the locally saved
                token, which is the recommended method for authentication (see
                https://huggingface.co/docs/huggingface_hub/quick-start#authentication).
                To disable authentication, pass `False`.

        Returns:
            [`~hf_api.SpaceInfo`]: The space repository information.

        <Tip>

        Raises the following errors:

            - [`~utils.RepositoryNotFoundError`]
              If the repository to download from cannot be found. This may be because it doesn't exist,
              or because it is set to `private` and you do not have access.
            - [`~utils.RevisionNotFoundError`]
              If the revision to download from cannot be found.

        </Tip>
        """
        if expand and files_metadata:
            raise ValueError("`expand` cannot be used if `files_metadata` is set.")

        headers = self._build_hf_headers(token=token)
        path = (
            f"{self.endpoint}/api/spaces/{repo_id}"
            if revision is None
            else (f"{self.endpoint}/api/spaces/{repo_id}/revision/{quote(revision, safe='')}")
        )
        params: Dict = {}
        if files_metadata:
            params["blobs"] = True
        if expand:
            params["expand"] = expand

        r = get_session().get(path, headers=headers, timeout=timeout, params=params)
        hf_raise_for_status(r)
        data = r.json()
        return SpaceInfo(**data)

    @validate_hf_hub_args
    def repo_info(
        self,
        repo_id: str,
        *,
        revision: Optional[str] = None,
        repo_type: Optional[str] = None,
        timeout: Optional[float] = None,
        files_metadata: bool = False,
        expand: Optional[Union[ExpandModelProperty_T, ExpandDatasetProperty_T, ExpandSpaceProperty_T]] = None,
        token: Union[bool, str, None] = None,
    ) -> Union[ModelInfo, DatasetInfo, SpaceInfo]:
        """
        Get the info object for a given repo of a given type.

        Args:
            repo_id (`str`):
                A namespace (user or an organization) and a repo name separated
                by a `/`.
            revision (`str`, *optional*):
                The revision of the repository from which to get the
                information.
            repo_type (`str`, *optional*):
                Set to `"dataset"` or `"space"` if getting repository info from a dataset or a space,
                `None` or `"model"` if getting repository info from a model. Default is `None`.
            timeout (`float`, *optional*):
                Whether to set a timeout for the request to the Hub.
            expand (`ExpandModelProperty_T` or `ExpandDatasetProperty_T` or `ExpandSpaceProperty_T`, *optional*):
                List properties to return in the response. When used, only the properties in the list will be returned.
                This parameter cannot be used if `files_metadata` is passed.
                For an exhaustive list of available properties, check out [`model_info`], [`dataset_info`] or [`space_info`].
            files_metadata (`bool`, *optional*):
                Whether or not to retrieve metadata for files in the repository
                (size, LFS metadata, etc). Defaults to `False`.
            token (Union[bool, str, None], optional):
                A valid user access token (string). Defaults to the locally saved
                token, which is the recommended method for authentication (see
                https://huggingface.co/docs/huggingface_hub/quick-start#authentication).
                To disable authentication, pass `False`.

        Returns:
            `Union[SpaceInfo, DatasetInfo, ModelInfo]`: The repository information, as a
            [`huggingface_hub.hf_api.DatasetInfo`], [`huggingface_hub.hf_api.ModelInfo`]
            or [`huggingface_hub.hf_api.SpaceInfo`] object.

        <Tip>

        Raises the following errors:

            - [`~utils.RepositoryNotFoundError`]
              If the repository to download from cannot be found. This may be because it doesn't exist,
              or because it is set to `private` and you do not have access.
            - [`~utils.RevisionNotFoundError`]
              If the revision to download from cannot be found.

        </Tip>
        """
        if repo_type is None or repo_type == "model":
            method = self.model_info
        elif repo_type == "dataset":
            method = self.dataset_info  # type: ignore
        elif repo_type == "space":
            method = self.space_info  # type: ignore
        else:
            raise ValueError("Unsupported repo type.")
        return method(
            repo_id,
            revision=revision,
            token=token,
            timeout=timeout,
            expand=expand,  # type: ignore[arg-type]
            files_metadata=files_metadata,
        )

    @validate_hf_hub_args
    def repo_exists(
        self,
        repo_id: str,
        *,
        repo_type: Optional[str] = None,
        token: Union[str, bool, None] = None,
    ) -> bool:
        """
        Checks if a repository exists on the Hugging Face Hub.

        Args:
            repo_id (`str`):
                A namespace (user or an organization) and a repo name separated
                by a `/`.
            repo_type (`str`, *optional*):
                Set to `"dataset"` or `"space"` if getting repository info from a dataset or a space,
                `None` or `"model"` if getting repository info from a model. Default is `None`.
            token (Union[bool, str, None], optional):
                A valid user access token (string). Defaults to the locally saved
                token, which is the recommended method for authentication (see
                https://huggingface.co/docs/huggingface_hub/quick-start#authentication).
                To disable authentication, pass `False`.

        Returns:
            True if the repository exists, False otherwise.

        Examples:
            ```py
            >>> from huggingface_hub import repo_exists
            >>> repo_exists("google/gemma-7b")
            True
            >>> repo_exists("google/not-a-repo")
            False
            ```
        """
        try:
            self.repo_info(repo_id=repo_id, repo_type=repo_type, token=token)
            return True
        except GatedRepoError:
            return True  # we don't have access but it exists
        except RepositoryNotFoundError:
            return False

    @validate_hf_hub_args
    def revision_exists(
        self,
        repo_id: str,
        revision: str,
        *,
        repo_type: Optional[str] = None,
        token: Union[str, bool, None] = None,
    ) -> bool:
        """
        Checks if a specific revision exists on a repo on the Hugging Face Hub.

        Args:
            repo_id (`str`):
                A namespace (user or an organization) and a repo name separated
                by a `/`.
            revision (`str`):
                The revision of the repository to check.
            repo_type (`str`, *optional*):
                Set to `"dataset"` or `"space"` if getting repository info from a dataset or a space,
                `None` or `"model"` if getting repository info from a model. Default is `None`.
            token (Union[bool, str, None], optional):
                A valid user access token (string). Defaults to the locally saved
                token, which is the recommended method for authentication (see
                https://huggingface.co/docs/huggingface_hub/quick-start#authentication).
                To disable authentication, pass `False`.

        Returns:
            True if the repository and the revision exists, False otherwise.

        Examples:
            ```py
            >>> from huggingface_hub import revision_exists
            >>> revision_exists("google/gemma-7b", "float16")
            True
            >>> revision_exists("google/gemma-7b", "not-a-revision")
            False
            ```
        """
        try:
            self.repo_info(repo_id=repo_id, revision=revision, repo_type=repo_type, token=token)
            return True
        except RevisionNotFoundError:
            return False
        except RepositoryNotFoundError:
            return False

    @validate_hf_hub_args
    def file_exists(
        self,
        repo_id: str,
        filename: str,
        *,
        repo_type: Optional[str] = None,
        revision: Optional[str] = None,
        token: Union[str, bool, None] = None,
    ) -> bool:
        """
        Checks if a file exists in a repository on the Hugging Face Hub.

        Args:
            repo_id (`str`):
                A namespace (user or an organization) and a repo name separated
                by a `/`.
            filename (`str`):
                The name of the file to check, for example:
                `"config.json"`
            repo_type (`str`, *optional*):
                Set to `"dataset"` or `"space"` if getting repository info from a dataset or a space,
                `None` or `"model"` if getting repository info from a model. Default is `None`.
            revision (`str`, *optional*):
                The revision of the repository from which to get the information. Defaults to `"main"` branch.
            token (Union[bool, str, None], optional):
                A valid user access token (string). Defaults to the locally saved
                token, which is the recommended method for authentication (see
                https://huggingface.co/docs/huggingface_hub/quick-start#authentication).
                To disable authentication, pass `False`.

        Returns:
            True if the file exists, False otherwise.

        Examples:
            ```py
            >>> from huggingface_hub import file_exists
            >>> file_exists("bigcode/starcoder", "config.json")
            True
            >>> file_exists("bigcode/starcoder", "not-a-file")
            False
            >>> file_exists("bigcode/not-a-repo", "config.json")
            False
            ```
        """
        url = hf_hub_url(
            repo_id=repo_id, repo_type=repo_type, revision=revision, filename=filename, endpoint=self.endpoint
        )
        try:
            if token is None:
                token = self.token
            get_hf_file_metadata(url, token=token)
            return True
        except GatedRepoError:  # raise specifically on gated repo
            raise
        except (RepositoryNotFoundError, EntryNotFoundError, RevisionNotFoundError):
            return False

    @validate_hf_hub_args
    def list_repo_files(
        self,
        repo_id: str,
        *,
        revision: Optional[str] = None,
        repo_type: Optional[str] = None,
        token: Union[str, bool, None] = None,
    ) -> List[str]:
        """
        Get the list of files in a given repo.

        Args:
            repo_id (`str`):
                A namespace (user or an organization) and a repo name separated by a `/`.
            revision (`str`, *optional*):
                The revision of the repository from which to get the information.
            repo_type (`str`, *optional*):
                Set to `"dataset"` or `"space"` if uploading to a dataset or space, `None` or `"model"` if uploading to
                a model. Default is `None`.
            token (Union[bool, str, None], optional):
                A valid user access token (string). Defaults to the locally saved
                token, which is the recommended method for authentication (see
                https://huggingface.co/docs/huggingface_hub/quick-start#authentication).
                To disable authentication, pass `False`.

        Returns:
            `List[str]`: the list of files in a given repository.
        """
        return [
            f.rfilename
            for f in self.list_repo_tree(
                repo_id=repo_id, recursive=True, revision=revision, repo_type=repo_type, token=token
            )
            if isinstance(f, RepoFile)
        ]

    @validate_hf_hub_args
    def list_repo_tree(
        self,
        repo_id: str,
        path_in_repo: Optional[str] = None,
        *,
        recursive: bool = False,
        expand: bool = False,
        revision: Optional[str] = None,
        repo_type: Optional[str] = None,
        token: Union[str, bool, None] = None,
    ) -> Iterable[Union[RepoFile, RepoFolder]]:
        """
        List a repo tree's files and folders and get information about them.

        Args:
            repo_id (`str`):
                A namespace (user or an organization) and a repo name separated by a `/`.
            path_in_repo (`str`, *optional*):
                Relative path of the tree (folder) in the repo, for example:
                `"checkpoints/1fec34a/results"`. Will default to the root tree (folder) of the repository.
            recursive (`bool`, *optional*, defaults to `False`):
                Whether to list tree's files and folders recursively.
            expand (`bool`, *optional*, defaults to `False`):
                Whether to fetch more information about the tree's files and folders (e.g. last commit and files' security scan results). This
                operation is more expensive for the server so only 50 results are returned per page (instead of 1000).
                As pagination is implemented in `huggingface_hub`, this is transparent for you except for the time it
                takes to get the results.
            revision (`str`, *optional*):
                The revision of the repository from which to get the tree. Defaults to `"main"` branch.
            repo_type (`str`, *optional*):
                The type of the repository from which to get the tree (`"model"`, `"dataset"` or `"space"`.
                Defaults to `"model"`.
            token (Union[bool, str, None], optional):
                A valid user access token (string). Defaults to the locally saved
                token, which is the recommended method for authentication (see
                https://huggingface.co/docs/huggingface_hub/quick-start#authentication).
                To disable authentication, pass `False`.

        Returns:
            `Iterable[Union[RepoFile, RepoFolder]]`:
                The information about the tree's files and folders, as an iterable of [`RepoFile`] and [`RepoFolder`] objects. The order of the files and folders is
                not guaranteed.

        Raises:
            [`~utils.RepositoryNotFoundError`]:
                If repository is not found (error 404): wrong repo_id/repo_type, private but not authenticated or repo
                does not exist.
            [`~utils.RevisionNotFoundError`]:
                If revision is not found (error 404) on the repo.
            [`~utils.EntryNotFoundError`]:
                If the tree (folder) does not exist (error 404) on the repo.

        Examples:

            Get information about a repo's tree.
            ```py
            >>> from huggingface_hub import list_repo_tree
            >>> repo_tree = list_repo_tree("lysandre/arxiv-nlp")
            >>> repo_tree
            <generator object HfApi.list_repo_tree at 0x7fa4088e1ac0>
            >>> list(repo_tree)
            [
                RepoFile(path='.gitattributes', size=391, blob_id='ae8c63daedbd4206d7d40126955d4e6ab1c80f8f', lfs=None, last_commit=None, security=None),
                RepoFile(path='README.md', size=391, blob_id='43bd404b159de6fba7c2f4d3264347668d43af25', lfs=None, last_commit=None, security=None),
                RepoFile(path='config.json', size=554, blob_id='2f9618c3a19b9a61add74f70bfb121335aeef666', lfs=None, last_commit=None, security=None),
                RepoFile(
                    path='flax_model.msgpack', size=497764107, blob_id='8095a62ccb4d806da7666fcda07467e2d150218e',
                    lfs={'size': 497764107, 'sha256': 'd88b0d6a6ff9c3f8151f9d3228f57092aaea997f09af009eefd7373a77b5abb9', 'pointer_size': 134}, last_commit=None, security=None
                ),
                RepoFile(path='merges.txt', size=456318, blob_id='226b0752cac7789c48f0cb3ec53eda48b7be36cc', lfs=None, last_commit=None, security=None),
                RepoFile(
                    path='pytorch_model.bin', size=548123560, blob_id='64eaa9c526867e404b68f2c5d66fd78e27026523',
                    lfs={'size': 548123560, 'sha256': '9be78edb5b928eba33aa88f431551348f7466ba9f5ef3daf1d552398722a5436', 'pointer_size': 134}, last_commit=None, security=None
                ),
                RepoFile(path='vocab.json', size=898669, blob_id='b00361fece0387ca34b4b8b8539ed830d644dbeb', lfs=None, last_commit=None, security=None)]
            ]
            ```

            Get even more information about a repo's tree (last commit and files' security scan results)
            ```py
            >>> from huggingface_hub import list_repo_tree
            >>> repo_tree = list_repo_tree("prompthero/openjourney-v4", expand=True)
            >>> list(repo_tree)
            [
                RepoFolder(
                    path='feature_extractor',
                    tree_id='aa536c4ea18073388b5b0bc791057a7296a00398',
                    last_commit={
                        'oid': '47b62b20b20e06b9de610e840282b7e6c3d51190',
                        'title': 'Upload diffusers weights (#48)',
                        'date': datetime.datetime(2023, 3, 21, 9, 5, 27, tzinfo=datetime.timezone.utc)
                    }
                ),
                RepoFolder(
                    path='safety_checker',
                    tree_id='65aef9d787e5557373fdf714d6c34d4fcdd70440',
                    last_commit={
                        'oid': '47b62b20b20e06b9de610e840282b7e6c3d51190',
                        'title': 'Upload diffusers weights (#48)',
                        'date': datetime.datetime(2023, 3, 21, 9, 5, 27, tzinfo=datetime.timezone.utc)
                    }
                ),
                RepoFile(
                    path='model_index.json',
                    size=582,
                    blob_id='d3d7c1e8c3e78eeb1640b8e2041ee256e24c9ee1',
                    lfs=None,
                    last_commit={
                        'oid': 'b195ed2d503f3eb29637050a886d77bd81d35f0e',
                        'title': 'Fix deprecation warning by changing `CLIPFeatureExtractor` to `CLIPImageProcessor`. (#54)',
                        'date': datetime.datetime(2023, 5, 15, 21, 41, 59, tzinfo=datetime.timezone.utc)
                    },
                    security={
                        'safe': True,
                        'av_scan': {'virusFound': False, 'virusNames': None},
                        'pickle_import_scan': None
                    }
                )
                ...
            ]
            ```
        """
        repo_type = repo_type or constants.REPO_TYPE_MODEL
        revision = quote(revision, safe="") if revision is not None else constants.DEFAULT_REVISION
        headers = self._build_hf_headers(token=token)

        encoded_path_in_repo = "/" + quote(path_in_repo, safe="") if path_in_repo else ""
        tree_url = f"{self.endpoint}/api/{repo_type}s/{repo_id}/tree/{revision}{encoded_path_in_repo}"
        for path_info in paginate(path=tree_url, headers=headers, params={"recursive": recursive, "expand": expand}):
            yield (RepoFile(**path_info) if path_info["type"] == "file" else RepoFolder(**path_info))

    @validate_hf_hub_args
    def list_repo_refs(
        self,
        repo_id: str,
        *,
        repo_type: Optional[str] = None,
        include_pull_requests: bool = False,
        token: Union[str, bool, None] = None,
    ) -> GitRefs:
        """
        Get the list of refs of a given repo (both tags and branches).

        Args:
            repo_id (`str`):
                A namespace (user or an organization) and a repo name separated
                by a `/`.
            repo_type (`str`, *optional*):
                Set to `"dataset"` or `"space"` if listing refs from a dataset or a Space,
                `None` or `"model"` if listing from a model. Default is `None`.
            include_pull_requests (`bool`, *optional*):
                Whether to include refs from pull requests in the list. Defaults to `False`.
            token (Union[bool, str, None], optional):
                A valid user access token (string). Defaults to the locally saved
                token, which is the recommended method for authentication (see
                https://huggingface.co/docs/huggingface_hub/quick-start#authentication).
                To disable authentication, pass `False`.

        Example:
        ```py
        >>> from huggingface_hub import HfApi
        >>> api = HfApi()
        >>> api.list_repo_refs("gpt2")
        GitRefs(branches=[GitRefInfo(name='main', ref='refs/heads/main', target_commit='e7da7f221d5bf496a48136c0cd264e630fe9fcc8')], converts=[], tags=[])

        >>> api.list_repo_refs("bigcode/the-stack", repo_type='dataset')
        GitRefs(
            branches=[
                GitRefInfo(name='main', ref='refs/heads/main', target_commit='18edc1591d9ce72aa82f56c4431b3c969b210ae3'),
                GitRefInfo(name='v1.1.a1', ref='refs/heads/v1.1.a1', target_commit='f9826b862d1567f3822d3d25649b0d6d22ace714')
            ],
            converts=[],
            tags=[
                GitRefInfo(name='v1.0', ref='refs/tags/v1.0', target_commit='c37a8cd1e382064d8aced5e05543c5f7753834da')
            ]
        )
        ```

        Returns:
            [`GitRefs`]: object containing all information about branches and tags for a
            repo on the Hub.
        """
        repo_type = repo_type or constants.REPO_TYPE_MODEL
        response = get_session().get(
            f"{self.endpoint}/api/{repo_type}s/{repo_id}/refs",
            headers=self._build_hf_headers(token=token),
            params={"include_prs": 1} if include_pull_requests else {},
        )
        hf_raise_for_status(response)
        data = response.json()

        def _format_as_git_ref_info(item: Dict) -> GitRefInfo:
            return GitRefInfo(name=item["name"], ref=item["ref"], target_commit=item["targetCommit"])

        return GitRefs(
            branches=[_format_as_git_ref_info(item) for item in data["branches"]],
            converts=[_format_as_git_ref_info(item) for item in data["converts"]],
            tags=[_format_as_git_ref_info(item) for item in data["tags"]],
            pull_requests=[_format_as_git_ref_info(item) for item in data["pullRequests"]]
            if include_pull_requests
            else None,
        )

    @validate_hf_hub_args
    def list_repo_commits(
        self,
        repo_id: str,
        *,
        repo_type: Optional[str] = None,
        token: Union[bool, str, None] = None,
        revision: Optional[str] = None,
        formatted: bool = False,
    ) -> List[GitCommitInfo]:
        """
        Get the list of commits of a given revision for a repo on the Hub.

        Commits are sorted by date (last commit first).

        Args:
            repo_id (`str`):
                A namespace (user or an organization) and a repo name separated by a `/`.
            repo_type (`str`, *optional*):
                Set to `"dataset"` or `"space"` if listing commits from a dataset or a Space, `None` or `"model"` if
                listing from a model. Default is `None`.
            token (Union[bool, str, None], optional):
                A valid user access token (string). Defaults to the locally saved
                token, which is the recommended method for authentication (see
                https://huggingface.co/docs/huggingface_hub/quick-start#authentication).
                To disable authentication, pass `False`.
            revision (`str`, *optional*):
                The git revision to commit from. Defaults to the head of the `"main"` branch.
            formatted (`bool`):
                Whether to return the HTML-formatted title and description of the commits. Defaults to False.

        Example:
        ```py
        >>> from huggingface_hub import HfApi
        >>> api = HfApi()

        # Commits are sorted by date (last commit first)
        >>> initial_commit = api.list_repo_commits("gpt2")[-1]

        # Initial commit is always a system commit containing the `.gitattributes` file.
        >>> initial_commit
        GitCommitInfo(
            commit_id='9b865efde13a30c13e0a33e536cf3e4a5a9d71d8',
            authors=['system'],
            created_at=datetime.datetime(2019, 2, 18, 10, 36, 15, tzinfo=datetime.timezone.utc),
            title='initial commit',
            message='',
            formatted_title=None,
            formatted_message=None
        )

        # Create an empty branch by deriving from initial commit
        >>> api.create_branch("gpt2", "new_empty_branch", revision=initial_commit.commit_id)
        ```

        Returns:
            List[[`GitCommitInfo`]]: list of objects containing information about the commits for a repo on the Hub.

        Raises:
            [`~utils.RepositoryNotFoundError`]:
                If repository is not found (error 404): wrong repo_id/repo_type, private but not authenticated or repo
                does not exist.
            [`~utils.RevisionNotFoundError`]:
                If revision is not found (error 404) on the repo.
        """
        repo_type = repo_type or constants.REPO_TYPE_MODEL
        revision = quote(revision, safe="") if revision is not None else constants.DEFAULT_REVISION

        # Paginate over results and return the list of commits.
        return [
            GitCommitInfo(
                commit_id=item["id"],
                authors=[author["user"] for author in item["authors"]],
                created_at=parse_datetime(item["date"]),
                title=item["title"],
                message=item["message"],
                formatted_title=item.get("formatted", {}).get("title"),
                formatted_message=item.get("formatted", {}).get("message"),
            )
            for item in paginate(
                f"{self.endpoint}/api/{repo_type}s/{repo_id}/commits/{revision}",
                headers=self._build_hf_headers(token=token),
                params={"expand[]": "formatted"} if formatted else {},
            )
        ]

    @validate_hf_hub_args
    def get_paths_info(
        self,
        repo_id: str,
        paths: Union[List[str], str],
        *,
        expand: bool = False,
        revision: Optional[str] = None,
        repo_type: Optional[str] = None,
        token: Union[str, bool, None] = None,
    ) -> List[Union[RepoFile, RepoFolder]]:
        """
        Get information about a repo's paths.

        Args:
            repo_id (`str`):
                A namespace (user or an organization) and a repo name separated by a `/`.
            paths (`Union[List[str], str]`, *optional*):
                The paths to get information about. If a path do not exist, it is ignored without raising
                an exception.
            expand (`bool`, *optional*, defaults to `False`):
                Whether to fetch more information about the paths (e.g. last commit and files' security scan results). This
                operation is more expensive for the server so only 50 results are returned per page (instead of 1000).
                As pagination is implemented in `huggingface_hub`, this is transparent for you except for the time it
                takes to get the results.
            revision (`str`, *optional*):
                The revision of the repository from which to get the information. Defaults to `"main"` branch.
            repo_type (`str`, *optional*):
                The type of the repository from which to get the information (`"model"`, `"dataset"` or `"space"`.
                Defaults to `"model"`.
            token (Union[bool, str, None], optional):
                A valid user access token (string). Defaults to the locally saved
                token, which is the recommended method for authentication (see
                https://huggingface.co/docs/huggingface_hub/quick-start#authentication).
                To disable authentication, pass `False`.

        Returns:
            `List[Union[RepoFile, RepoFolder]]`:
                The information about the paths, as a list of [`RepoFile`] and [`RepoFolder`] objects.

        Raises:
            [`~utils.RepositoryNotFoundError`]:
                If repository is not found (error 404): wrong repo_id/repo_type, private but not authenticated or repo
                does not exist.
            [`~utils.RevisionNotFoundError`]:
                If revision is not found (error 404) on the repo.

        Example:
        ```py
        >>> from huggingface_hub import get_paths_info
        >>> paths_info = get_paths_info("allenai/c4", ["README.md", "en"], repo_type="dataset")
        >>> paths_info
        [
            RepoFile(path='README.md', size=2379, blob_id='f84cb4c97182890fc1dbdeaf1a6a468fd27b4fff', lfs=None, last_commit=None, security=None),
            RepoFolder(path='en', tree_id='dc943c4c40f53d02b31ced1defa7e5f438d5862e', last_commit=None)
        ]
        ```
        """
        repo_type = repo_type or constants.REPO_TYPE_MODEL
        revision = quote(revision, safe="") if revision is not None else constants.DEFAULT_REVISION
        headers = self._build_hf_headers(token=token)

        response = get_session().post(
            f"{self.endpoint}/api/{repo_type}s/{repo_id}/paths-info/{revision}",
            data={
                "paths": paths if isinstance(paths, list) else [paths],
                "expand": expand,
            },
            headers=headers,
        )
        hf_raise_for_status(response)
        paths_info = response.json()
        return [
            RepoFile(**path_info) if path_info["type"] == "file" else RepoFolder(**path_info)
            for path_info in paths_info
        ]

    @validate_hf_hub_args
    def super_squash_history(
        self,
        repo_id: str,
        *,
        branch: Optional[str] = None,
        commit_message: Optional[str] = None,
        repo_type: Optional[str] = None,
        token: Union[str, bool, None] = None,
    ) -> None:
        """Squash commit history on a branch for a repo on the Hub.

        Squashing the repo history is useful when you know you'll make hundreds of commits and you don't want to
        clutter the history. Squashing commits can only be performed from the head of a branch.

        <Tip warning={true}>

        Once squashed, the commit history cannot be retrieved. This is a non-revertible operation.

        </Tip>

        <Tip warning={true}>

        Once the history of a branch has been squashed, it is not possible to merge it back into another branch since
        their history will have diverged.

        </Tip>

        Args:
            repo_id (`str`):
                A namespace (user or an organization) and a repo name separated by a `/`.
            branch (`str`, *optional*):
                The branch to squash. Defaults to the head of the `"main"` branch.
            commit_message (`str`, *optional*):
                The commit message to use for the squashed commit.
            repo_type (`str`, *optional*):
                Set to `"dataset"` or `"space"` if listing commits from a dataset or a Space, `None` or `"model"` if
                listing from a model. Default is `None`.
            token (Union[bool, str, None], optional):
                A valid user access token (string). Defaults to the locally saved
                token, which is the recommended method for authentication (see
                https://huggingface.co/docs/huggingface_hub/quick-start#authentication).
                To disable authentication, pass `False`.

        Raises:
            [`~utils.RepositoryNotFoundError`]:
                If repository is not found (error 404): wrong repo_id/repo_type, private but not authenticated or repo
                does not exist.
            [`~utils.RevisionNotFoundError`]:
                If the branch to squash cannot be found.
            [`~utils.BadRequestError`]:
                If invalid reference for a branch. You cannot squash history on tags.

        Example:
        ```py
        >>> from huggingface_hub import HfApi
        >>> api = HfApi()

        # Create repo
        >>> repo_id = api.create_repo("test-squash").repo_id

        # Make a lot of commits.
        >>> api.upload_file(repo_id=repo_id, path_in_repo="file.txt", path_or_fileobj=b"content")
        >>> api.upload_file(repo_id=repo_id, path_in_repo="lfs.bin", path_or_fileobj=b"content")
        >>> api.upload_file(repo_id=repo_id, path_in_repo="file.txt", path_or_fileobj=b"another_content")

        # Squash history
        >>> api.super_squash_history(repo_id=repo_id)
        ```
        """
        if repo_type is None:
            repo_type = constants.REPO_TYPE_MODEL
        if repo_type not in constants.REPO_TYPES:
            raise ValueError("Invalid repo type")
        if branch is None:
            branch = constants.DEFAULT_REVISION

        # Prepare request
        url = f"{self.endpoint}/api/{repo_type}s/{repo_id}/super-squash/{quote(branch, safe='')}"
        headers = self._build_hf_headers(token=token)
        commit_message = commit_message or f"Super-squash branch '{branch}' using huggingface_hub"

        # Super-squash
        response = get_session().post(url=url, headers=headers, json={"message": commit_message})
        hf_raise_for_status(response)

    @validate_hf_hub_args
    def list_lfs_files(
        self,
        repo_id: str,
        *,
        repo_type: Optional[str] = None,
        token: Union[bool, str, None] = None,
    ) -> Iterable[LFSFileInfo]:
        """
        List all LFS files in a repo on the Hub.

        This is primarily useful to count how much storage a repo is using and to eventually clean up large files
        with [`permanently_delete_lfs_files`]. Note that this would be a permanent action that will affect all commits
        referencing this deleted files and that cannot be undone.

        Args:
            repo_id (`str`):
                The repository for which you are listing LFS files.
            repo_type (`str`, *optional*):
                Type of repository. Set to `"dataset"` or `"space"` if listing from a dataset or space, `None` or
                `"model"` if listing from a model. Default is `None`.
            token (Union[bool, str, None], optional):
                A valid user access token (string). Defaults to the locally saved
                token, which is the recommended method for authentication (see
                https://huggingface.co/docs/huggingface_hub/quick-start#authentication).
                To disable authentication, pass `False`.

        Returns:
            `Iterable[LFSFileInfo]`: An iterator of [`LFSFileInfo`] objects.

        Example:
            ```py
            >>> from huggingface_hub import HfApi
            >>> api = HfApi()
            >>> lfs_files = api.list_lfs_files("username/my-cool-repo")

            # Filter files files to delete based on a combination of `filename`, `pushed_at`, `ref` or `size`.
            # e.g. select only LFS files in the "checkpoints" folder
            >>> lfs_files_to_delete = (lfs_file for lfs_file in lfs_files if lfs_file.filename.startswith("checkpoints/"))

            # Permanently delete LFS files
            >>> api.permanently_delete_lfs_files("username/my-cool-repo", lfs_files_to_delete)
            ```
        """
        # Prepare request
        if repo_type is None:
            repo_type = constants.REPO_TYPE_MODEL
        url = f"{self.endpoint}/api/{repo_type}s/{repo_id}/lfs-files"
        headers = self._build_hf_headers(token=token)

        # Paginate over LFS items
        for item in paginate(url, params={}, headers=headers):
            yield LFSFileInfo(**item)

    @validate_hf_hub_args
    def permanently_delete_lfs_files(
        self,
        repo_id: str,
        lfs_files: Iterable[LFSFileInfo],
        *,
        rewrite_history: bool = True,
        repo_type: Optional[str] = None,
        token: Union[bool, str, None] = None,
    ) -> None:
        """
        Permanently delete LFS files from a repo on the Hub.

        <Tip warning={true}>

        This is a permanent action that will affect all commits referencing the deleted files and might corrupt your
        repository. This is a non-revertible operation. Use it only if you know what you are doing.

        </Tip>

        Args:
            repo_id (`str`):
                The repository for which you are listing LFS files.
            lfs_files (`Iterable[LFSFileInfo]`):
                An iterable of [`LFSFileInfo`] items to permanently delete from the repo. Use [`list_lfs_files`] to list
                all LFS files from a repo.
            rewrite_history (`bool`, *optional*, default to `True`):
                Whether to rewrite repository history to remove file pointers referencing the deleted LFS files (recommended).
            repo_type (`str`, *optional*):
                Type of repository. Set to `"dataset"` or `"space"` if listing from a dataset or space, `None` or
                `"model"` if listing from a model. Default is `None`.
            token (Union[bool, str, None], optional):
                A valid user access token (string). Defaults to the locally saved
                token, which is the recommended method for authentication (see
                https://huggingface.co/docs/huggingface_hub/quick-start#authentication).
                To disable authentication, pass `False`.

        Example:
            ```py
            >>> from huggingface_hub import HfApi
            >>> api = HfApi()
            >>> lfs_files = api.list_lfs_files("username/my-cool-repo")

            # Filter files files to delete based on a combination of `filename`, `pushed_at`, `ref` or `size`.
            # e.g. select only LFS files in the "checkpoints" folder
            >>> lfs_files_to_delete = (lfs_file for lfs_file in lfs_files if lfs_file.filename.startswith("checkpoints/"))

            # Permanently delete LFS files
            >>> api.permanently_delete_lfs_files("username/my-cool-repo", lfs_files_to_delete)
            ```
        """
        # Prepare request
        if repo_type is None:
            repo_type = constants.REPO_TYPE_MODEL
        url = f"{self.endpoint}/api/{repo_type}s/{repo_id}/lfs-files/batch"
        headers = self._build_hf_headers(token=token)

        # Delete LFS items by batches of 1000
        for batch in chunk_iterable(lfs_files, 1000):
            shas = [item.file_oid for item in batch]
            if len(shas) == 0:
                return
            payload = {
                "deletions": {
                    "sha": shas,
                    "rewriteHistory": rewrite_history,
                }
            }
            response = get_session().post(url, headers=headers, json=payload)
            hf_raise_for_status(response)

    @validate_hf_hub_args
    def create_repo(
        self,
        repo_id: str,
        *,
        token: Union[str, bool, None] = None,
        private: Optional[bool] = None,
        repo_type: Optional[str] = None,
        exist_ok: bool = False,
        resource_group_id: Optional[str] = None,
        space_sdk: Optional[str] = None,
        space_hardware: Optional[SpaceHardware] = None,
        space_storage: Optional[SpaceStorage] = None,
        space_sleep_time: Optional[int] = None,
        space_secrets: Optional[List[Dict[str, str]]] = None,
        space_variables: Optional[List[Dict[str, str]]] = None,
    ) -> RepoUrl:
        """Create an empty repo on the HuggingFace Hub.

        Args:
            repo_id (`str`):
                A namespace (user or an organization) and a repo name separated
                by a `/`.
            token (Union[bool, str, None], optional):
                A valid user access token (string). Defaults to the locally saved
                token, which is the recommended method for authentication (see
                https://huggingface.co/docs/huggingface_hub/quick-start#authentication).
                To disable authentication, pass `False`.
            private (`bool`, *optional*):
                Whether to make the repo private. If `None` (default), the repo will be public unless the organization's default is private. This value is ignored if the repo already exists.
            repo_type (`str`, *optional*):
                Set to `"dataset"` or `"space"` if uploading to a dataset or
                space, `None` or `"model"` if uploading to a model. Default is
                `None`.
            exist_ok (`bool`, *optional*, defaults to `False`):
                If `True`, do not raise an error if repo already exists.
            resource_group_id (`str`, *optional*):
                Resource group in which to create the repo. Resource groups is only available for Enterprise Hub organizations and
                allow to define which members of the organization can access the resource. The ID of a resource group
                can be found in the URL of the resource's page on the Hub (e.g. `"66670e5163145ca562cb1988"`).
                To learn more about resource groups, see https://huggingface.co/docs/hub/en/security-resource-groups.
            space_sdk (`str`, *optional*):
                Choice of SDK to use if repo_type is "space". Can be "streamlit", "gradio", "docker", or "static".
            space_hardware (`SpaceHardware` or `str`, *optional*):
                Choice of Hardware if repo_type is "space". See [`SpaceHardware`] for a complete list.
            space_storage (`SpaceStorage` or `str`, *optional*):
                Choice of persistent storage tier. Example: `"small"`. See [`SpaceStorage`] for a complete list.
            space_sleep_time (`int`, *optional*):
                Number of seconds of inactivity to wait before a Space is put to sleep. Set to `-1` if you don't want
                your Space to sleep (default behavior for upgraded hardware). For free hardware, you can't configure
                the sleep time (value is fixed to 48 hours of inactivity).
                See https://huggingface.co/docs/hub/spaces-gpus#sleep-time for more details.
            space_secrets (`List[Dict[str, str]]`, *optional*):
                A list of secret keys to set in your Space. Each item is in the form `{"key": ..., "value": ..., "description": ...}` where description is optional.
                For more details, see https://huggingface.co/docs/hub/spaces-overview#managing-secrets.
            space_variables (`List[Dict[str, str]]`, *optional*):
                A list of public environment variables to set in your Space. Each item is in the form `{"key": ..., "value": ..., "description": ...}` where description is optional.
                For more details, see https://huggingface.co/docs/hub/spaces-overview#managing-secrets-and-environment-variables.

        Returns:
            [`RepoUrl`]: URL to the newly created repo. Value is a subclass of `str` containing
            attributes like `endpoint`, `repo_type` and `repo_id`.
        """
        organization, name = repo_id.split("/") if "/" in repo_id else (None, repo_id)

        path = f"{self.endpoint}/api/repos/create"

        if repo_type not in constants.REPO_TYPES:
            raise ValueError("Invalid repo type")

        json: Dict[str, Any] = {"name": name, "organization": organization}
        if private is not None:
            json["private"] = private
        if repo_type is not None:
            json["type"] = repo_type
        if repo_type == "space":
            if space_sdk is None:
                raise ValueError(
                    "No space_sdk provided. `create_repo` expects space_sdk to be one"
                    f" of {constants.SPACES_SDK_TYPES} when repo_type is 'space'`"
                )
            if space_sdk not in constants.SPACES_SDK_TYPES:
                raise ValueError(f"Invalid space_sdk. Please choose one of {constants.SPACES_SDK_TYPES}.")
            json["sdk"] = space_sdk

        if space_sdk is not None and repo_type != "space":
            warnings.warn("Ignoring provided space_sdk because repo_type is not 'space'.")

        function_args = [
            "space_hardware",
            "space_storage",
            "space_sleep_time",
            "space_secrets",
            "space_variables",
        ]
        json_keys = ["hardware", "storageTier", "sleepTimeSeconds", "secrets", "variables"]
        values = [space_hardware, space_storage, space_sleep_time, space_secrets, space_variables]

        if repo_type == "space":
            json.update({k: v for k, v in zip(json_keys, values) if v is not None})
        else:
            provided_space_args = [key for key, value in zip(function_args, values) if value is not None]

            if provided_space_args:
                warnings.warn(f"Ignoring provided {', '.join(provided_space_args)} because repo_type is not 'space'.")

        if getattr(self, "_lfsmultipartthresh", None):
            # Testing purposes only.
            # See https://github.com/huggingface/huggingface_hub/pull/733/files#r820604472
            json["lfsmultipartthresh"] = self._lfsmultipartthresh  # type: ignore

        if resource_group_id is not None:
            json["resourceGroupId"] = resource_group_id

        headers = self._build_hf_headers(token=token)
        while True:
            r = get_session().post(path, headers=headers, json=json)
            if r.status_code == 409 and "Cannot create repo: another conflicting operation is in progress" in r.text:
                # Since https://github.com/huggingface/moon-landing/pull/7272 (private repo), it is not possible to
                # concurrently create repos on the Hub for a same user. This is rarely an issue, except when running
                # tests. To avoid any inconvenience, we retry to create the repo for this specific error.
                # NOTE: This could have being fixed directly in the tests but adding it here should fixed CIs for all
                # dependent libraries.
                # NOTE: If a fix is implemented server-side, we should be able to remove this retry mechanism.
                logger.debug("Create repo failed due to a concurrency issue. Retrying...")
                continue
            break

        try:
            hf_raise_for_status(r)
        except HTTPError as err:
            if exist_ok and err.response.status_code == 409:
                # Repo already exists and `exist_ok=True`
                pass
            elif exist_ok and err.response.status_code == 403:
                # No write permission on the namespace but repo might already exist
                try:
                    self.repo_info(repo_id=repo_id, repo_type=repo_type, token=token)
                    if repo_type is None or repo_type == constants.REPO_TYPE_MODEL:
                        return RepoUrl(f"{self.endpoint}/{repo_id}")
                    return RepoUrl(f"{self.endpoint}/{repo_type}/{repo_id}")
                except HfHubHTTPError:
                    raise err
            else:
                raise

        d = r.json()
        return RepoUrl(d["url"], endpoint=self.endpoint)

    @validate_hf_hub_args
    def delete_repo(
        self,
        repo_id: str,
        *,
        token: Union[str, bool, None] = None,
        repo_type: Optional[str] = None,
        missing_ok: bool = False,
    ) -> None:
        """
        Delete a repo from the HuggingFace Hub. CAUTION: this is irreversible.

        Args:
            repo_id (`str`):
                A namespace (user or an organization) and a repo name separated
                by a `/`.
            token (Union[bool, str, None], optional):
                A valid user access token (string). Defaults to the locally saved
                token, which is the recommended method for authentication (see
                https://huggingface.co/docs/huggingface_hub/quick-start#authentication).
                To disable authentication, pass `False`.
            repo_type (`str`, *optional*):
                Set to `"dataset"` or `"space"` if uploading to a dataset or
                space, `None` or `"model"` if uploading to a model.
            missing_ok (`bool`, *optional*, defaults to `False`):
                If `True`, do not raise an error if repo does not exist.

        Raises:
            [`~utils.RepositoryNotFoundError`]
              If the repository to delete from cannot be found and `missing_ok` is set to False (default).
        """
        organization, name = repo_id.split("/") if "/" in repo_id else (None, repo_id)

        path = f"{self.endpoint}/api/repos/delete"

        if repo_type not in constants.REPO_TYPES:
            raise ValueError("Invalid repo type")

        json = {"name": name, "organization": organization}
        if repo_type is not None:
            json["type"] = repo_type

        headers = self._build_hf_headers(token=token)
        r = get_session().delete(path, headers=headers, json=json)
        try:
            hf_raise_for_status(r)
        except RepositoryNotFoundError:
            if not missing_ok:
                raise

    @_deprecate_method(version="0.32", message="Please use `update_repo_settings` instead.")
    @validate_hf_hub_args
    def update_repo_visibility(
        self,
        repo_id: str,
        private: bool = False,
        *,
        token: Union[str, bool, None] = None,
        repo_type: Optional[str] = None,
    ) -> Dict[str, bool]:
        """Update the visibility setting of a repository.

        Deprecated. Use `update_repo_settings` instead.

        Args:
            repo_id (`str`, *optional*):
                A namespace (user or an organization) and a repo name separated by a `/`.
            private (`bool`, *optional*, defaults to `False`):
                Whether the repository should be private.
            token (Union[bool, str, None], optional):
                A valid user access token (string). Defaults to the locally saved
                token, which is the recommended method for authentication (see
                https://huggingface.co/docs/huggingface_hub/quick-start#authentication).
                To disable authentication, pass `False`.
            repo_type (`str`, *optional*):
                Set to `"dataset"` or `"space"` if uploading to a dataset or
                space, `None` or `"model"` if uploading to a model. Default is
                `None`.

        Returns:
            The HTTP response in json.

        <Tip>

        Raises the following errors:

            - [`~utils.RepositoryNotFoundError`]
              If the repository to download from cannot be found. This may be because it doesn't exist,
              or because it is set to `private` and you do not have access.

        </Tip>
        """
        if repo_type not in constants.REPO_TYPES:
            raise ValueError(f"Invalid repo type, must be one of {constants.REPO_TYPES}")
        if repo_type is None:
            repo_type = constants.REPO_TYPE_MODEL  # default repo type

        r = get_session().put(
            url=f"{self.endpoint}/api/{repo_type}s/{repo_id}/settings",
            headers=self._build_hf_headers(token=token),
            json={"private": private},
        )
        hf_raise_for_status(r)
        return r.json()

    @validate_hf_hub_args
    def update_repo_settings(
        self,
        repo_id: str,
        *,
        gated: Optional[Literal["auto", "manual", False]] = None,
        private: Optional[bool] = None,
        token: Union[str, bool, None] = None,
        repo_type: Optional[str] = None,
        xet_enabled: Optional[bool] = None,
    ) -> None:
        """
        Update the settings of a repository, including gated access and visibility.

        To give more control over how repos are used, the Hub allows repo authors to enable
        access requests for their repos, and also to set the visibility of the repo to private.

        Args:
            repo_id (`str`):
                A namespace (user or an organization) and a repo name separated by a /.
            gated (`Literal["auto", "manual", False]`, *optional*):
                The gated status for the repository. If set to `None` (default), the `gated` setting of the repository won't be updated.
                * "auto": The repository is gated, and access requests are automatically approved or denied based on predefined criteria.
                * "manual": The repository is gated, and access requests require manual approval.
                * False : The repository is not gated, and anyone can access it.
            private (`bool`, *optional*):
                Whether the repository should be private.
            token (`Union[str, bool, None]`, *optional*):
                A valid user access token (string). Defaults to the locally saved token,
                which is the recommended method for authentication (see
                https://huggingface.co/docs/huggingface_hub/quick-start#authentication).
                To disable authentication, pass False.
            repo_type (`str`, *optional*):
                The type of the repository to update settings from (`"model"`, `"dataset"` or `"space"`).
                Defaults to `"model"`.
            xet_enabled (`bool`, *optional*):
                Whether the repository should be enabled for Xet Storage.
        Raises:
            [`ValueError`](https://docs.python.org/3/library/exceptions.html#ValueError)
                If gated is not one of "auto", "manual", or False.
            [`ValueError`](https://docs.python.org/3/library/exceptions.html#ValueError)
                If repo_type is not one of the values in constants.REPO_TYPES.
            [`~utils.HfHubHTTPError`]:
                If the request to the Hugging Face Hub API fails.
            [`~utils.RepositoryNotFoundError`]
                If the repository to download from cannot be found. This may be because it doesn't exist,
                or because it is set to `private` and you do not have access.
        """

        if repo_type not in constants.REPO_TYPES:
            raise ValueError(f"Invalid repo type, must be one of {constants.REPO_TYPES}")
        if repo_type is None:
            repo_type = constants.REPO_TYPE_MODEL  # default repo type

        # Prepare the JSON payload for the PUT request
        payload: Dict = {}

        if gated is not None:
            if gated not in ["auto", "manual", False]:
                raise ValueError(f"Invalid gated status, must be one of 'auto', 'manual', or False. Got '{gated}'.")
            payload["gated"] = gated

        if private is not None:
            payload["private"] = private

        if xet_enabled is not None:
            payload["xetEnabled"] = xet_enabled

        if len(payload) == 0:
            raise ValueError("At least one setting must be updated.")

        # Build headers
        headers = self._build_hf_headers(token=token)

        r = get_session().put(
            url=f"{self.endpoint}/api/{repo_type}s/{repo_id}/settings",
            headers=headers,
            json=payload,
        )
        hf_raise_for_status(r)

    def move_repo(
        self,
        from_id: str,
        to_id: str,
        *,
        repo_type: Optional[str] = None,
        token: Union[str, bool, None] = None,
    ):
        """
        Moving a repository from namespace1/repo_name1 to namespace2/repo_name2

        Note there are certain limitations. For more information about moving
        repositories, please see
        https://hf.co/docs/hub/repositories-settings#renaming-or-transferring-a-repo.

        Args:
            from_id (`str`):
                A namespace (user or an organization) and a repo name separated
                by a `/`. Original repository identifier.
            to_id (`str`):
                A namespace (user or an organization) and a repo name separated
                by a `/`. Final repository identifier.
            repo_type (`str`, *optional*):
                Set to `"dataset"` or `"space"` if uploading to a dataset or
                space, `None` or `"model"` if uploading to a model. Default is
                `None`.
            token (Union[bool, str, None], optional):
                A valid user access token (string). Defaults to the locally saved
                token, which is the recommended method for authentication (see
                https://huggingface.co/docs/huggingface_hub/quick-start#authentication).
                To disable authentication, pass `False`.

        <Tip>

        Raises the following errors:

            - [`~utils.RepositoryNotFoundError`]
              If the repository to download from cannot be found. This may be because it doesn't exist,
              or because it is set to `private` and you do not have access.

        </Tip>
        """
        if len(from_id.split("/")) != 2:
            raise ValueError(f"Invalid repo_id: {from_id}. It should have a namespace (:namespace:/:repo_name:)")

        if len(to_id.split("/")) != 2:
            raise ValueError(f"Invalid repo_id: {to_id}. It should have a namespace (:namespace:/:repo_name:)")

        if repo_type is None:
            repo_type = constants.REPO_TYPE_MODEL  # Hub won't accept `None`.

        json = {"fromRepo": from_id, "toRepo": to_id, "type": repo_type}

        path = f"{self.endpoint}/api/repos/move"
        headers = self._build_hf_headers(token=token)
        r = get_session().post(path, headers=headers, json=json)
        try:
            hf_raise_for_status(r)
        except HfHubHTTPError as e:
            e.append_to_message(
                "\nFor additional documentation please see"
                " https://hf.co/docs/hub/repositories-settings#renaming-or-transferring-a-repo."
            )
            raise

    @overload
    def create_commit(  # type: ignore
        self,
        repo_id: str,
        operations: Iterable[CommitOperation],
        *,
        commit_message: str,
        commit_description: Optional[str] = None,
        token: Union[str, bool, None] = None,
        repo_type: Optional[str] = None,
        revision: Optional[str] = None,
        create_pr: Optional[bool] = None,
        num_threads: int = 5,
        parent_commit: Optional[str] = None,
        run_as_future: Literal[False] = ...,
    ) -> CommitInfo: ...

    @overload
    def create_commit(
        self,
        repo_id: str,
        operations: Iterable[CommitOperation],
        *,
        commit_message: str,
        commit_description: Optional[str] = None,
        token: Union[str, bool, None] = None,
        repo_type: Optional[str] = None,
        revision: Optional[str] = None,
        create_pr: Optional[bool] = None,
        num_threads: int = 5,
        parent_commit: Optional[str] = None,
        run_as_future: Literal[True] = ...,
    ) -> Future[CommitInfo]: ...

    @validate_hf_hub_args
    @future_compatible
    def create_commit(
        self,
        repo_id: str,
        operations: Iterable[CommitOperation],
        *,
        commit_message: str,
        commit_description: Optional[str] = None,
        token: Union[str, bool, None] = None,
        repo_type: Optional[str] = None,
        revision: Optional[str] = None,
        create_pr: Optional[bool] = None,
        num_threads: int = 5,
        parent_commit: Optional[str] = None,
        run_as_future: bool = False,
    ) -> Union[CommitInfo, Future[CommitInfo]]:
        """
        Creates a commit in the given repo, deleting & uploading files as needed.

        <Tip warning={true}>

        The input list of `CommitOperation` will be mutated during the commit process. Do not reuse the same objects
        for multiple commits.

        </Tip>

        <Tip warning={true}>

        `create_commit` assumes that the repo already exists on the Hub. If you get a
        Client error 404, please make sure you are authenticated and that `repo_id` and
        `repo_type` are set correctly. If repo does not exist, create it first using
        [`~hf_api.create_repo`].

        </Tip>

        <Tip warning={true}>

        `create_commit` is limited to 25k LFS files and a 1GB payload for regular files.

        </Tip>

        Args:
            repo_id (`str`):
                The repository in which the commit will be created, for example:
                `"username/custom_transformers"`

            operations (`Iterable` of [`~hf_api.CommitOperation`]):
                An iterable of operations to include in the commit, either:

                    - [`~hf_api.CommitOperationAdd`] to upload a file
                    - [`~hf_api.CommitOperationDelete`] to delete a file
                    - [`~hf_api.CommitOperationCopy`] to copy a file

                Operation objects will be mutated to include information relative to the upload. Do not reuse the
                same objects for multiple commits.

            commit_message (`str`):
                The summary (first line) of the commit that will be created.

            commit_description (`str`, *optional*):
                The description of the commit that will be created

            token (Union[bool, str, None], optional):
                A valid user access token (string). Defaults to the locally saved
                token, which is the recommended method for authentication (see
                https://huggingface.co/docs/huggingface_hub/quick-start#authentication).
                To disable authentication, pass `False`.

            repo_type (`str`, *optional*):
                Set to `"dataset"` or `"space"` if uploading to a dataset or
                space, `None` or `"model"` if uploading to a model. Default is
                `None`.

            revision (`str`, *optional*):
                The git revision to commit from. Defaults to the head of the `"main"` branch.

            create_pr (`boolean`, *optional*):
                Whether or not to create a Pull Request with that commit. Defaults to `False`.
                If `revision` is not set, PR is opened against the `"main"` branch. If
                `revision` is set and is a branch, PR is opened against this branch. If
                `revision` is set and is not a branch name (example: a commit oid), an
                `RevisionNotFoundError` is returned by the server.

            num_threads (`int`, *optional*):
                Number of concurrent threads for uploading files. Defaults to 5.
                Setting it to 2 means at most 2 files will be uploaded concurrently.

            parent_commit (`str`, *optional*):
                The OID / SHA of the parent commit, as a hexadecimal string.
                Shorthands (7 first characters) are also supported. If specified and `create_pr` is `False`,
                the commit will fail if `revision` does not point to `parent_commit`. If specified and `create_pr`
                is `True`, the pull request will be created from `parent_commit`. Specifying `parent_commit`
                ensures the repo has not changed before committing the changes, and can be especially useful
                if the repo is updated / committed to concurrently.
            run_as_future (`bool`, *optional*):
                Whether or not to run this method in the background. Background jobs are run sequentially without
                blocking the main thread. Passing `run_as_future=True` will return a [Future](https://docs.python.org/3/library/concurrent.futures.html#future-objects)
                object. Defaults to `False`.

        Returns:
            [`CommitInfo`] or `Future`:
                Instance of [`CommitInfo`] containing information about the newly created commit (commit hash, commit
                url, pr url, commit message,...). If `run_as_future=True` is passed, returns a Future object which will
                contain the result when executed.

        Raises:
            [`ValueError`](https://docs.python.org/3/library/exceptions.html#ValueError)
                If commit message is empty.
            [`ValueError`](https://docs.python.org/3/library/exceptions.html#ValueError)
                If parent commit is not a valid commit OID.
            [`ValueError`](https://docs.python.org/3/library/exceptions.html#ValueError)
                If a README.md file with an invalid metadata section is committed. In this case, the commit will fail
                early, before trying to upload any file.
            [`ValueError`](https://docs.python.org/3/library/exceptions.html#ValueError)
                If `create_pr` is `True` and revision is neither `None` nor `"main"`.
            [`~utils.RepositoryNotFoundError`]:
                If repository is not found (error 404): wrong repo_id/repo_type, private
                but not authenticated or repo does not exist.
        """
        if parent_commit is not None and not constants.REGEX_COMMIT_OID.fullmatch(parent_commit):
            raise ValueError(
                f"`parent_commit` is not a valid commit OID. It must match the following regex: {constants.REGEX_COMMIT_OID}"
            )

        if commit_message is None or len(commit_message) == 0:
            raise ValueError("`commit_message` can't be empty, please pass a value.")

        commit_description = commit_description if commit_description is not None else ""
        repo_type = repo_type if repo_type is not None else constants.REPO_TYPE_MODEL
        if repo_type not in constants.REPO_TYPES:
            raise ValueError(f"Invalid repo type, must be one of {constants.REPO_TYPES}")
        unquoted_revision = revision or constants.DEFAULT_REVISION
        revision = quote(unquoted_revision, safe="")
        create_pr = create_pr if create_pr is not None else False

        headers = self._build_hf_headers(token=token)

        operations = list(operations)
        additions = [op for op in operations if isinstance(op, CommitOperationAdd)]
        copies = [op for op in operations if isinstance(op, CommitOperationCopy)]
        nb_additions = len(additions)
        nb_copies = len(copies)
        nb_deletions = len(operations) - nb_additions - nb_copies

        for addition in additions:
            if addition._is_committed:
                raise ValueError(
                    f"CommitOperationAdd {addition} has already being committed and cannot be reused. Please create a"
                    " new CommitOperationAdd object if you want to create a new commit."
                )

        if repo_type != "dataset":
            for addition in additions:
                if addition.path_in_repo.endswith((".arrow", ".parquet")):
                    warnings.warn(
                        f"It seems that you are about to commit a data file ({addition.path_in_repo}) to a {repo_type}"
                        " repository. You are sure this is intended? If you are trying to upload a dataset, please"
                        " set `repo_type='dataset'` or `--repo-type=dataset` in a CLI."
                    )

        logger.debug(
            f"About to commit to the hub: {len(additions)} addition(s), {len(copies)} copie(s) and"
            f" {nb_deletions} deletion(s)."
        )

        # If updating a README.md file, make sure the metadata format is valid
        # It's better to fail early than to fail after all the files have been uploaded.
        for addition in additions:
            if addition.path_in_repo == "README.md":
                with addition.as_file() as file:
                    content = file.read().decode()
                self._validate_yaml(content, repo_type=repo_type, token=token)
                # Skip other additions after `README.md` has been processed
                break

        # If updating twice the same file or update then delete a file in a single commit
        _warn_on_overwriting_operations(operations)

        self.preupload_lfs_files(
            repo_id=repo_id,
            additions=additions,
            token=token,
            repo_type=repo_type,
            revision=unquoted_revision,  # first-class methods take unquoted revision
            create_pr=create_pr,
            num_threads=num_threads,
            free_memory=False,  # do not remove `CommitOperationAdd.path_or_fileobj` on LFS files for "normal" users
        )

        files_to_copy = _fetch_files_to_copy(
            copies=copies,
            repo_type=repo_type,
            repo_id=repo_id,
            headers=headers,
            revision=unquoted_revision,
            endpoint=self.endpoint,
        )
        # Remove no-op operations (files that have not changed)
        operations_without_no_op = []
        for operation in operations:
            if (
                isinstance(operation, CommitOperationAdd)
                and operation._remote_oid is not None
                and operation._remote_oid == operation._local_oid
            ):
                # File already exists on the Hub and has not changed: we can skip it.
                logger.debug(f"Skipping upload for '{operation.path_in_repo}' as the file has not changed.")
                continue
            if (
                isinstance(operation, CommitOperationCopy)
                and operation._dest_oid is not None
                and operation._dest_oid == operation._src_oid
            ):
                # Source and destination files are identical - skip
                logger.debug(
                    f"Skipping copy for '{operation.src_path_in_repo}' -> '{operation.path_in_repo}' as the content of the source file is the same as the destination file."
                )
                continue
            operations_without_no_op.append(operation)
        if len(operations) != len(operations_without_no_op):
            logger.info(
                f"Removing {len(operations) - len(operations_without_no_op)} file(s) from commit that have not changed."
            )

        # Return early if empty commit
        if len(operations_without_no_op) == 0:
            logger.warning("No files have been modified since last commit. Skipping to prevent empty commit.")

            # Get latest commit info
            try:
                info = self.repo_info(repo_id=repo_id, repo_type=repo_type, revision=unquoted_revision, token=token)
            except RepositoryNotFoundError as e:
                e.append_to_message(_CREATE_COMMIT_NO_REPO_ERROR_MESSAGE)
                raise

            # Return commit info based on latest commit
            url_prefix = self.endpoint
            if repo_type is not None and repo_type != constants.REPO_TYPE_MODEL:
                url_prefix = f"{url_prefix}/{repo_type}s"
            return CommitInfo(
                commit_url=f"{url_prefix}/{repo_id}/commit/{info.sha}",
                commit_message=commit_message,
                commit_description=commit_description,
                oid=info.sha,  # type: ignore[arg-type]
            )

        commit_payload = _prepare_commit_payload(
            operations=operations,
            files_to_copy=files_to_copy,
            commit_message=commit_message,
            commit_description=commit_description,
            parent_commit=parent_commit,
        )
        commit_url = f"{self.endpoint}/api/{repo_type}s/{repo_id}/commit/{revision}"

        def _payload_as_ndjson() -> Iterable[bytes]:
            for item in commit_payload:
                yield json.dumps(item).encode()
                yield b"\n"

        headers = {
            # See https://github.com/huggingface/huggingface_hub/issues/1085#issuecomment-1265208073
            "Content-Type": "application/x-ndjson",
            **headers,
        }
        data = b"".join(_payload_as_ndjson())
        params = {"create_pr": "1"} if create_pr else None

        try:
            commit_resp = get_session().post(url=commit_url, headers=headers, data=data, params=params)
            hf_raise_for_status(commit_resp, endpoint_name="commit")
        except RepositoryNotFoundError as e:
            e.append_to_message(_CREATE_COMMIT_NO_REPO_ERROR_MESSAGE)
            raise
        except EntryNotFoundError as e:
            if nb_deletions > 0 and "A file with this name doesn't exist" in str(e):
                e.append_to_message(
                    "\nMake sure to differentiate file and folder paths in delete"
                    " operations with a trailing '/' or using `is_folder=True/False`."
                )
            raise

        # Mark additions as committed (cannot be reused in another commit)
        for addition in additions:
            addition._is_committed = True

        commit_data = commit_resp.json()
        return CommitInfo(
            commit_url=commit_data["commitUrl"],
            commit_message=commit_message,
            commit_description=commit_description,
            oid=commit_data["commitOid"],
            pr_url=commit_data["pullRequestUrl"] if create_pr else None,
        )

    def preupload_lfs_files(
        self,
        repo_id: str,
        additions: Iterable[CommitOperationAdd],
        *,
        token: Union[str, bool, None] = None,
        repo_type: Optional[str] = None,
        revision: Optional[str] = None,
        create_pr: Optional[bool] = None,
        num_threads: int = 5,
        free_memory: bool = True,
        gitignore_content: Optional[str] = None,
    ):
        """Pre-upload LFS files to S3 in preparation on a future commit.

        This method is useful if you are generating the files to upload on-the-fly and you don't want to store them
        in memory before uploading them all at once.

        <Tip warning={true}>

        This is a power-user method. You shouldn't need to call it directly to make a normal commit.
        Use [`create_commit`] directly instead.

        </Tip>

        <Tip warning={true}>

        Commit operations will be mutated during the process. In particular, the attached `path_or_fileobj` will be
        removed after the upload to save memory (and replaced by an empty `bytes` object). Do not reuse the same
        objects except to pass them to [`create_commit`]. If you don't want to remove the attached content from the
        commit operation object, pass `free_memory=False`.

        </Tip>

        Args:
            repo_id (`str`):
                The repository in which you will commit the files, for example: `"username/custom_transformers"`.

            operations (`Iterable` of [`CommitOperationAdd`]):
                The list of files to upload. Warning: the objects in this list will be mutated to include information
                relative to the upload. Do not reuse the same objects for multiple commits.

            token (Union[bool, str, None], optional):
                A valid user access token (string). Defaults to the locally saved
                token, which is the recommended method for authentication (see
                https://huggingface.co/docs/huggingface_hub/quick-start#authentication).
                To disable authentication, pass `False`.

            repo_type (`str`, *optional*):
                The type of repository to upload to (e.g. `"model"` -default-, `"dataset"` or `"space"`).

            revision (`str`, *optional*):
                The git revision to commit from. Defaults to the head of the `"main"` branch.

            create_pr (`boolean`, *optional*):
                Whether or not you plan to create a Pull Request with that commit. Defaults to `False`.

            num_threads (`int`, *optional*):
                Number of concurrent threads for uploading files. Defaults to 5.
                Setting it to 2 means at most 2 files will be uploaded concurrently.

            gitignore_content (`str`, *optional*):
                The content of the `.gitignore` file to know which files should be ignored. The order of priority
                is to first check if `gitignore_content` is passed, then check if the `.gitignore` file is present
                in the list of files to commit and finally default to the `.gitignore` file already hosted on the Hub
                (if any).

        Example:
        ```py
        >>> from huggingface_hub import CommitOperationAdd, preupload_lfs_files, create_commit, create_repo

        >>> repo_id = create_repo("test_preupload").repo_id

        # Generate and preupload LFS files one by one
        >>> operations = [] # List of all `CommitOperationAdd` objects that will be generated
        >>> for i in range(5):
        ...     content = ... # generate binary content
        ...     addition = CommitOperationAdd(path_in_repo=f"shard_{i}_of_5.bin", path_or_fileobj=content)
        ...     preupload_lfs_files(repo_id, additions=[addition]) # upload + free memory
        ...     operations.append(addition)

        # Create commit
        >>> create_commit(repo_id, operations=operations, commit_message="Commit all shards")
        ```
        """
        repo_type = repo_type if repo_type is not None else constants.REPO_TYPE_MODEL
        if repo_type not in constants.REPO_TYPES:
            raise ValueError(f"Invalid repo type, must be one of {constants.REPO_TYPES}")
        revision = quote(revision, safe="") if revision is not None else constants.DEFAULT_REVISION
        create_pr = create_pr if create_pr is not None else False
        headers = self._build_hf_headers(token=token)

        # Check if a `gitignore` file is being committed to the Hub.
        additions = list(additions)
        if gitignore_content is None:
            for addition in additions:
                if addition.path_in_repo == ".gitignore":
                    with addition.as_file() as f:
                        gitignore_content = f.read().decode()
                        break

        # Filter out already uploaded files
        new_additions = [addition for addition in additions if not addition._is_uploaded]

        # Check which new files are LFS
        # For some items, we might have already fetched the upload mode (in case of upload_large_folder)
        additions_no_upload_mode = [addition for addition in new_additions if addition._upload_mode is None]
        if len(additions_no_upload_mode) > 0:
            try:
                _fetch_upload_modes(
                    additions=additions_no_upload_mode,
                    repo_type=repo_type,
                    repo_id=repo_id,
                    headers=headers,
                    revision=revision,
                    endpoint=self.endpoint,
                    create_pr=create_pr or False,
                    gitignore_content=gitignore_content,
                )
            except RepositoryNotFoundError as e:
                e.append_to_message(_CREATE_COMMIT_NO_REPO_ERROR_MESSAGE)
                raise

        # Filter out regular files
        new_lfs_additions = [addition for addition in new_additions if addition._upload_mode == "lfs"]

        # Filter out files listed in .gitignore
        new_lfs_additions_to_upload = []
        for addition in new_lfs_additions:
            if addition._should_ignore:
                logger.debug(f"Skipping upload for LFS file '{addition.path_in_repo}' (ignored by gitignore file).")
            else:
                new_lfs_additions_to_upload.append(addition)
        if len(new_lfs_additions) != len(new_lfs_additions_to_upload):
            logger.info(
                f"Skipped upload for {len(new_lfs_additions) - len(new_lfs_additions_to_upload)} LFS file(s) "
                "(ignored by gitignore file)."
            )
        # Prepare upload parameters
        upload_kwargs = {
            "additions": new_lfs_additions_to_upload,
            "repo_type": repo_type,
            "repo_id": repo_id,
            "headers": headers,
            "endpoint": self.endpoint,
            # If `create_pr`, we don't want to check user permission on the revision as users with read permission
            # should still be able to create PRs even if they don't have write permission on the target branch of the
            # PR (i.e. `revision`).
            "revision": revision if not create_pr else None,
        }
        # Upload files using Xet protocol if all of the following are true:
        # - xet is enabled for the repo,
        # - the files are provided as str or paths objects,
        # - the library is installed.
        # Otherwise, default back to LFS.
        xet_enabled = self.repo_info(
            repo_id=repo_id,
            repo_type=repo_type,
            revision=unquote(revision) if revision is not None else revision,
            expand="xetEnabled",
            token=token,
        ).xet_enabled
        has_buffered_io_data = any(
            isinstance(addition.path_or_fileobj, io.BufferedIOBase) for addition in new_lfs_additions_to_upload
        )
        if xet_enabled and not has_buffered_io_data and is_xet_available():
            logger.debug("Uploading files using Xet Storage..")
            _upload_xet_files(**upload_kwargs, create_pr=create_pr)  # type: ignore [arg-type]
        else:
            if xet_enabled and is_xet_available():
                if has_buffered_io_data:
                    logger.warning(
                        "Uploading files as a binary IO buffer is not supported by Xet Storage. "
                        "Falling back to HTTP upload."
                    )
            _upload_lfs_files(**upload_kwargs, num_threads=num_threads)  # type: ignore [arg-type]
        for addition in new_lfs_additions_to_upload:
            addition._is_uploaded = True
            if free_memory:
                addition.path_or_fileobj = b""

    @overload
    def upload_file(  # type: ignore
        self,
        *,
        path_or_fileobj: Union[str, Path, bytes, BinaryIO],
        path_in_repo: str,
        repo_id: str,
        token: Union[str, bool, None] = None,
        repo_type: Optional[str] = None,
        revision: Optional[str] = None,
        commit_message: Optional[str] = None,
        commit_description: Optional[str] = None,
        create_pr: Optional[bool] = None,
        parent_commit: Optional[str] = None,
        run_as_future: Literal[False] = ...,
    ) -> CommitInfo: ...

    @overload
    def upload_file(
        self,
        *,
        path_or_fileobj: Union[str, Path, bytes, BinaryIO],
        path_in_repo: str,
        repo_id: str,
        token: Union[str, bool, None] = None,
        repo_type: Optional[str] = None,
        revision: Optional[str] = None,
        commit_message: Optional[str] = None,
        commit_description: Optional[str] = None,
        create_pr: Optional[bool] = None,
        parent_commit: Optional[str] = None,
        run_as_future: Literal[True] = ...,
    ) -> Future[CommitInfo]: ...

    @validate_hf_hub_args
    @future_compatible
    def upload_file(
        self,
        *,
        path_or_fileobj: Union[str, Path, bytes, BinaryIO],
        path_in_repo: str,
        repo_id: str,
        token: Union[str, bool, None] = None,
        repo_type: Optional[str] = None,
        revision: Optional[str] = None,
        commit_message: Optional[str] = None,
        commit_description: Optional[str] = None,
        create_pr: Optional[bool] = None,
        parent_commit: Optional[str] = None,
        run_as_future: bool = False,
    ) -> Union[CommitInfo, Future[CommitInfo]]:
        """
        Upload a local file (up to 50 GB) to the given repo. The upload is done
        through a HTTP post request, and doesn't require git or git-lfs to be
        installed.

        Args:
            path_or_fileobj (`str`, `Path`, `bytes`, or `IO`):
                Path to a file on the local machine or binary data stream /
                fileobj / buffer.
            path_in_repo (`str`):
                Relative filepath in the repo, for example:
                `"checkpoints/1fec34a/weights.bin"`
            repo_id (`str`):
                The repository to which the file will be uploaded, for example:
                `"username/custom_transformers"`
            token (Union[bool, str, None], optional):
                A valid user access token (string). Defaults to the locally saved
                token, which is the recommended method for authentication (see
                https://huggingface.co/docs/huggingface_hub/quick-start#authentication).
                To disable authentication, pass `False`.
            repo_type (`str`, *optional*):
                Set to `"dataset"` or `"space"` if uploading to a dataset or
                space, `None` or `"model"` if uploading to a model. Default is
                `None`.
            revision (`str`, *optional*):
                The git revision to commit from. Defaults to the head of the `"main"` branch.
            commit_message (`str`, *optional*):
                The summary / title / first line of the generated commit
            commit_description (`str` *optional*)
                The description of the generated commit
            create_pr (`boolean`, *optional*):
                Whether or not to create a Pull Request with that commit. Defaults to `False`.
                If `revision` is not set, PR is opened against the `"main"` branch. If
                `revision` is set and is a branch, PR is opened against this branch. If
                `revision` is set and is not a branch name (example: a commit oid), an
                `RevisionNotFoundError` is returned by the server.
            parent_commit (`str`, *optional*):
                The OID / SHA of the parent commit, as a hexadecimal string. Shorthands (7 first characters) are also supported.
                If specified and `create_pr` is `False`, the commit will fail if `revision` does not point to `parent_commit`.
                If specified and `create_pr` is `True`, the pull request will be created from `parent_commit`.
                Specifying `parent_commit` ensures the repo has not changed before committing the changes, and can be
                especially useful if the repo is updated / committed to concurrently.
            run_as_future (`bool`, *optional*):
                Whether or not to run this method in the background. Background jobs are run sequentially without
                blocking the main thread. Passing `run_as_future=True` will return a [Future](https://docs.python.org/3/library/concurrent.futures.html#future-objects)
                object. Defaults to `False`.


        Returns:
            [`CommitInfo`] or `Future`:
                Instance of [`CommitInfo`] containing information about the newly created commit (commit hash, commit
                url, pr url, commit message,...). If `run_as_future=True` is passed, returns a Future object which will
                contain the result when executed.
        <Tip>

        Raises the following errors:

            - [`HTTPError`](https://requests.readthedocs.io/en/latest/api/#requests.HTTPError)
              if the HuggingFace API returned an error
            - [`ValueError`](https://docs.python.org/3/library/exceptions.html#ValueError)
              if some parameter value is invalid
            - [`~utils.RepositoryNotFoundError`]
              If the repository to download from cannot be found. This may be because it doesn't exist,
              or because it is set to `private` and you do not have access.
            - [`~utils.RevisionNotFoundError`]
              If the revision to download from cannot be found.

        </Tip>

        <Tip warning={true}>

        `upload_file` assumes that the repo already exists on the Hub. If you get a
        Client error 404, please make sure you are authenticated and that `repo_id` and
        `repo_type` are set correctly. If repo does not exist, create it first using
        [`~hf_api.create_repo`].

        </Tip>

        Example:

        ```python
        >>> from huggingface_hub import upload_file

        >>> with open("./local/filepath", "rb") as fobj:
        ...     upload_file(
        ...         path_or_fileobj=fileobj,
        ...         path_in_repo="remote/file/path.h5",
        ...         repo_id="username/my-dataset",
        ...         repo_type="dataset",
        ...         token="my_token",
        ...     )
        "https://huggingface.co/datasets/username/my-dataset/blob/main/remote/file/path.h5"

        >>> upload_file(
        ...     path_or_fileobj=".\\\\local\\\\file\\\\path",
        ...     path_in_repo="remote/file/path.h5",
        ...     repo_id="username/my-model",
        ...     token="my_token",
        ... )
        "https://huggingface.co/username/my-model/blob/main/remote/file/path.h5"

        >>> upload_file(
        ...     path_or_fileobj=".\\\\local\\\\file\\\\path",
        ...     path_in_repo="remote/file/path.h5",
        ...     repo_id="username/my-model",
        ...     token="my_token",
        ...     create_pr=True,
        ... )
        "https://huggingface.co/username/my-model/blob/refs%2Fpr%2F1/remote/file/path.h5"
        ```
        """
        if repo_type not in constants.REPO_TYPES:
            raise ValueError(f"Invalid repo type, must be one of {constants.REPO_TYPES}")

        commit_message = (
            commit_message if commit_message is not None else f"Upload {path_in_repo} with huggingface_hub"
        )
        operation = CommitOperationAdd(
            path_or_fileobj=path_or_fileobj,
            path_in_repo=path_in_repo,
        )

        commit_info = self.create_commit(
            repo_id=repo_id,
            repo_type=repo_type,
            operations=[operation],
            commit_message=commit_message,
            commit_description=commit_description,
            token=token,
            revision=revision,
            create_pr=create_pr,
            parent_commit=parent_commit,
        )

        if commit_info.pr_url is not None:
            revision = quote(_parse_revision_from_pr_url(commit_info.pr_url), safe="")
        if repo_type in constants.REPO_TYPES_URL_PREFIXES:
            repo_id = constants.REPO_TYPES_URL_PREFIXES[repo_type] + repo_id
        revision = revision if revision is not None else constants.DEFAULT_REVISION

        return CommitInfo(
            commit_url=commit_info.commit_url,
            commit_message=commit_info.commit_message,
            commit_description=commit_info.commit_description,
            oid=commit_info.oid,
            pr_url=commit_info.pr_url,
            # Similar to `hf_hub_url` but it's "blob" instead of "resolve"
            # TODO: remove this in v1.0
            _url=f"{self.endpoint}/{repo_id}/blob/{revision}/{path_in_repo}",
        )

    @overload
    def upload_folder(  # type: ignore
        self,
        *,
        repo_id: str,
        folder_path: Union[str, Path],
        path_in_repo: Optional[str] = None,
        commit_message: Optional[str] = None,
        commit_description: Optional[str] = None,
        token: Union[str, bool, None] = None,
        repo_type: Optional[str] = None,
        revision: Optional[str] = None,
        create_pr: Optional[bool] = None,
        parent_commit: Optional[str] = None,
        allow_patterns: Optional[Union[List[str], str]] = None,
        ignore_patterns: Optional[Union[List[str], str]] = None,
        delete_patterns: Optional[Union[List[str], str]] = None,
        run_as_future: Literal[False] = ...,
    ) -> CommitInfo: ...

    @overload
    def upload_folder(  # type: ignore
        self,
        *,
        repo_id: str,
        folder_path: Union[str, Path],
        path_in_repo: Optional[str] = None,
        commit_message: Optional[str] = None,
        commit_description: Optional[str] = None,
        token: Union[str, bool, None] = None,
        repo_type: Optional[str] = None,
        revision: Optional[str] = None,
        create_pr: Optional[bool] = None,
        parent_commit: Optional[str] = None,
        allow_patterns: Optional[Union[List[str], str]] = None,
        ignore_patterns: Optional[Union[List[str], str]] = None,
        delete_patterns: Optional[Union[List[str], str]] = None,
        run_as_future: Literal[True] = ...,
    ) -> Future[CommitInfo]: ...

    @validate_hf_hub_args
    @future_compatible
    def upload_folder(
        self,
        *,
        repo_id: str,
        folder_path: Union[str, Path],
        path_in_repo: Optional[str] = None,
        commit_message: Optional[str] = None,
        commit_description: Optional[str] = None,
        token: Union[str, bool, None] = None,
        repo_type: Optional[str] = None,
        revision: Optional[str] = None,
        create_pr: Optional[bool] = None,
        parent_commit: Optional[str] = None,
        allow_patterns: Optional[Union[List[str], str]] = None,
        ignore_patterns: Optional[Union[List[str], str]] = None,
        delete_patterns: Optional[Union[List[str], str]] = None,
        run_as_future: bool = False,
    ) -> Union[CommitInfo, Future[CommitInfo]]:
        """
        Upload a local folder to the given repo. The upload is done through a HTTP requests, and doesn't require git or
        git-lfs to be installed.

        The structure of the folder will be preserved. Files with the same name already present in the repository will
        be overwritten. Others will be left untouched.

        Use the `allow_patterns` and `ignore_patterns` arguments to specify which files to upload. These parameters
        accept either a single pattern or a list of patterns. Patterns are Standard Wildcards (globbing patterns) as
        documented [here](https://tldp.org/LDP/GNU-Linux-Tools-Summary/html/x11655.htm). If both `allow_patterns` and
        `ignore_patterns` are provided, both constraints apply. By default, all files from the folder are uploaded.

        Use the `delete_patterns` argument to specify remote files you want to delete. Input type is the same as for
        `allow_patterns` (see above). If `path_in_repo` is also provided, the patterns are matched against paths
        relative to this folder. For example, `upload_folder(..., path_in_repo="experiment", delete_patterns="logs/*")`
        will delete any remote file under `./experiment/logs/`. Note that the `.gitattributes` file will not be deleted
        even if it matches the patterns.

        Any `.git/` folder present in any subdirectory will be ignored. However, please be aware that the `.gitignore`
        file is not taken into account.

        Uses `HfApi.create_commit` under the hood.

        Args:
            repo_id (`str`):
                The repository to which the file will be uploaded, for example:
                `"username/custom_transformers"`
            folder_path (`str` or `Path`):
                Path to the folder to upload on the local file system
            path_in_repo (`str`, *optional*):
                Relative path of the directory in the repo, for example:
                `"checkpoints/1fec34a/results"`. Will default to the root folder of the repository.
            token (Union[bool, str, None], optional):
                A valid user access token (string). Defaults to the locally saved
                token, which is the recommended method for authentication (see
                https://huggingface.co/docs/huggingface_hub/quick-start#authentication).
                To disable authentication, pass `False`.
            repo_type (`str`, *optional*):
                Set to `"dataset"` or `"space"` if uploading to a dataset or
                space, `None` or `"model"` if uploading to a model. Default is
                `None`.
            revision (`str`, *optional*):
                The git revision to commit from. Defaults to the head of the `"main"` branch.
            commit_message (`str`, *optional*):
                The summary / title / first line of the generated commit. Defaults to:
                `f"Upload {path_in_repo} with huggingface_hub"`
            commit_description (`str` *optional*):
                The description of the generated commit
            create_pr (`boolean`, *optional*):
                Whether or not to create a Pull Request with that commit. Defaults to `False`. If `revision` is not
                set, PR is opened against the `"main"` branch. If `revision` is set and is a branch, PR is opened
                against this branch. If `revision` is set and is not a branch name (example: a commit oid), an
                `RevisionNotFoundError` is returned by the server.
            parent_commit (`str`, *optional*):
                The OID / SHA of the parent commit, as a hexadecimal string. Shorthands (7 first characters) are also supported.
                If specified and `create_pr` is `False`, the commit will fail if `revision` does not point to `parent_commit`.
                If specified and `create_pr` is `True`, the pull request will be created from `parent_commit`.
                Specifying `parent_commit` ensures the repo has not changed before committing the changes, and can be
                especially useful if the repo is updated / committed to concurrently.
            allow_patterns (`List[str]` or `str`, *optional*):
                If provided, only files matching at least one pattern are uploaded.
            ignore_patterns (`List[str]` or `str`, *optional*):
                If provided, files matching any of the patterns are not uploaded.
            delete_patterns (`List[str]` or `str`, *optional*):
                If provided, remote files matching any of the patterns will be deleted from the repo while committing
                new files. This is useful if you don't know which files have already been uploaded.
                Note: to avoid discrepancies the `.gitattributes` file is not deleted even if it matches the pattern.
            run_as_future (`bool`, *optional*):
                Whether or not to run this method in the background. Background jobs are run sequentially without
                blocking the main thread. Passing `run_as_future=True` will return a [Future](https://docs.python.org/3/library/concurrent.futures.html#future-objects)
                object. Defaults to `False`.

        Returns:
            [`CommitInfo`] or `Future`:
                Instance of [`CommitInfo`] containing information about the newly created commit (commit hash, commit
                url, pr url, commit message,...). If `run_as_future=True` is passed, returns a Future object which will
                contain the result when executed.

        <Tip>

        Raises the following errors:

            - [`HTTPError`](https://requests.readthedocs.io/en/latest/api/#requests.HTTPError)
            if the HuggingFace API returned an error
            - [`ValueError`](https://docs.python.org/3/library/exceptions.html#ValueError)
            if some parameter value is invalid

        </Tip>

        <Tip warning={true}>

        `upload_folder` assumes that the repo already exists on the Hub. If you get a Client error 404, please make
        sure you are authenticated and that `repo_id` and `repo_type` are set correctly. If repo does not exist, create
        it first using [`~hf_api.create_repo`].

        </Tip>

        <Tip>

        When dealing with a large folder (thousands of files or hundreds of GB), we recommend using [`~hf_api.upload_large_folder`] instead.

        </Tip>

        Example:

        ```python
        # Upload checkpoints folder except the log files
        >>> upload_folder(
        ...     folder_path="local/checkpoints",
        ...     path_in_repo="remote/experiment/checkpoints",
        ...     repo_id="username/my-dataset",
        ...     repo_type="datasets",
        ...     token="my_token",
        ...     ignore_patterns="**/logs/*.txt",
        ... )
        # "https://huggingface.co/datasets/username/my-dataset/tree/main/remote/experiment/checkpoints"

        # Upload checkpoints folder including logs while deleting existing logs from the repo
        # Useful if you don't know exactly which log files have already being pushed
        >>> upload_folder(
        ...     folder_path="local/checkpoints",
        ...     path_in_repo="remote/experiment/checkpoints",
        ...     repo_id="username/my-dataset",
        ...     repo_type="datasets",
        ...     token="my_token",
        ...     delete_patterns="**/logs/*.txt",
        ... )
        "https://huggingface.co/datasets/username/my-dataset/tree/main/remote/experiment/checkpoints"

        # Upload checkpoints folder while creating a PR
        >>> upload_folder(
        ...     folder_path="local/checkpoints",
        ...     path_in_repo="remote/experiment/checkpoints",
        ...     repo_id="username/my-dataset",
        ...     repo_type="datasets",
        ...     token="my_token",
        ...     create_pr=True,
        ... )
        "https://huggingface.co/datasets/username/my-dataset/tree/refs%2Fpr%2F1/remote/experiment/checkpoints"

        ```
        """
        if repo_type not in constants.REPO_TYPES:
            raise ValueError(f"Invalid repo type, must be one of {constants.REPO_TYPES}")

        # By default, upload folder to the root directory in repo.
        if path_in_repo is None:
            path_in_repo = ""

        # Do not upload .git folder
        if ignore_patterns is None:
            ignore_patterns = []
        elif isinstance(ignore_patterns, str):
            ignore_patterns = [ignore_patterns]
        ignore_patterns += DEFAULT_IGNORE_PATTERNS

        delete_operations = self._prepare_folder_deletions(
            repo_id=repo_id,
            repo_type=repo_type,
            revision=constants.DEFAULT_REVISION if create_pr else revision,
            token=token,
            path_in_repo=path_in_repo,
            delete_patterns=delete_patterns,
        )
        add_operations = self._prepare_upload_folder_additions(
            folder_path,
            path_in_repo,
            allow_patterns=allow_patterns,
            ignore_patterns=ignore_patterns,
            token=token,
            repo_type=repo_type,
        )

        # Optimize operations: if some files will be overwritten, we don't need to delete them first
        if len(add_operations) > 0:
            added_paths = set(op.path_in_repo for op in add_operations)
            delete_operations = [
                delete_op for delete_op in delete_operations if delete_op.path_in_repo not in added_paths
            ]
        commit_operations = delete_operations + add_operations

        commit_message = commit_message or "Upload folder using huggingface_hub"

        commit_info = self.create_commit(
            repo_type=repo_type,
            repo_id=repo_id,
            operations=commit_operations,
            commit_message=commit_message,
            commit_description=commit_description,
            token=token,
            revision=revision,
            create_pr=create_pr,
            parent_commit=parent_commit,
        )

        # Create url to uploaded folder (for legacy return value)
        if create_pr and commit_info.pr_url is not None:
            revision = quote(_parse_revision_from_pr_url(commit_info.pr_url), safe="")
        if repo_type in constants.REPO_TYPES_URL_PREFIXES:
            repo_id = constants.REPO_TYPES_URL_PREFIXES[repo_type] + repo_id
        revision = revision if revision is not None else constants.DEFAULT_REVISION

        return CommitInfo(
            commit_url=commit_info.commit_url,
            commit_message=commit_info.commit_message,
            commit_description=commit_info.commit_description,
            oid=commit_info.oid,
            pr_url=commit_info.pr_url,
            # Similar to `hf_hub_url` but it's "tree" instead of "resolve"
            # TODO: remove this in v1.0
            _url=f"{self.endpoint}/{repo_id}/tree/{revision}/{path_in_repo}",
        )

    @validate_hf_hub_args
    def delete_file(
        self,
        path_in_repo: str,
        repo_id: str,
        *,
        token: Union[str, bool, None] = None,
        repo_type: Optional[str] = None,
        revision: Optional[str] = None,
        commit_message: Optional[str] = None,
        commit_description: Optional[str] = None,
        create_pr: Optional[bool] = None,
        parent_commit: Optional[str] = None,
    ) -> CommitInfo:
        """
        Deletes a file in the given repo.

        Args:
            path_in_repo (`str`):
                Relative filepath in the repo, for example:
                `"checkpoints/1fec34a/weights.bin"`
            repo_id (`str`):
                The repository from which the file will be deleted, for example:
                `"username/custom_transformers"`
            token (Union[bool, str, None], optional):
                A valid user access token (string). Defaults to the locally saved
                token, which is the recommended method for authentication (see
                https://huggingface.co/docs/huggingface_hub/quick-start#authentication).
                To disable authentication, pass `False`.
            repo_type (`str`, *optional*):
                Set to `"dataset"` or `"space"` if the file is in a dataset or
                space, `None` or `"model"` if in a model. Default is `None`.
            revision (`str`, *optional*):
                The git revision to commit from. Defaults to the head of the `"main"` branch.
            commit_message (`str`, *optional*):
                The summary / title / first line of the generated commit. Defaults to
                `f"Delete {path_in_repo} with huggingface_hub"`.
            commit_description (`str` *optional*)
                The description of the generated commit
            create_pr (`boolean`, *optional*):
                Whether or not to create a Pull Request with that commit. Defaults to `False`.
                If `revision` is not set, PR is opened against the `"main"` branch. If
                `revision` is set and is a branch, PR is opened against this branch. If
                `revision` is set and is not a branch name (example: a commit oid), an
                `RevisionNotFoundError` is returned by the server.
            parent_commit (`str`, *optional*):
                The OID / SHA of the parent commit, as a hexadecimal string. Shorthands (7 first characters) are also supported.
                If specified and `create_pr` is `False`, the commit will fail if `revision` does not point to `parent_commit`.
                If specified and `create_pr` is `True`, the pull request will be created from `parent_commit`.
                Specifying `parent_commit` ensures the repo has not changed before committing the changes, and can be
                especially useful if the repo is updated / committed to concurrently.


        <Tip>

        Raises the following errors:

            - [`HTTPError`](https://requests.readthedocs.io/en/latest/api/#requests.HTTPError)
              if the HuggingFace API returned an error
            - [`ValueError`](https://docs.python.org/3/library/exceptions.html#ValueError)
              if some parameter value is invalid
            - [`~utils.RepositoryNotFoundError`]
              If the repository to download from cannot be found. This may be because it doesn't exist,
              or because it is set to `private` and you do not have access.
            - [`~utils.RevisionNotFoundError`]
              If the revision to download from cannot be found.
            - [`~utils.EntryNotFoundError`]
              If the file to download cannot be found.

        </Tip>

        """
        commit_message = (
            commit_message if commit_message is not None else f"Delete {path_in_repo} with huggingface_hub"
        )

        operations = [CommitOperationDelete(path_in_repo=path_in_repo)]

        return self.create_commit(
            repo_id=repo_id,
            repo_type=repo_type,
            token=token,
            operations=operations,
            revision=revision,
            commit_message=commit_message,
            commit_description=commit_description,
            create_pr=create_pr,
            parent_commit=parent_commit,
        )

    @validate_hf_hub_args
    def delete_files(
        self,
        repo_id: str,
        delete_patterns: List[str],
        *,
        token: Union[bool, str, None] = None,
        repo_type: Optional[str] = None,
        revision: Optional[str] = None,
        commit_message: Optional[str] = None,
        commit_description: Optional[str] = None,
        create_pr: Optional[bool] = None,
        parent_commit: Optional[str] = None,
    ) -> CommitInfo:
        """
        Delete files from a repository on the Hub.

        If a folder path is provided, the entire folder is deleted as well as
        all files it contained.

        Args:
            repo_id (`str`):
                The repository from which the folder will be deleted, for example:
                `"username/custom_transformers"`
            delete_patterns (`List[str]`):
                List of files or folders to delete. Each string can either be
                a file path, a folder path or a Unix shell-style wildcard.
                E.g. `["file.txt", "folder/", "data/*.parquet"]`
            token (Union[bool, str, None], optional):
                A valid user access token (string). Defaults to the locally saved
                token, which is the recommended method for authentication (see
                https://huggingface.co/docs/huggingface_hub/quick-start#authentication).
                To disable authentication, pass `False`.
                to the stored token.
            repo_type (`str`, *optional*):
                Type of the repo to delete files from. Can be `"model"`,
                `"dataset"` or `"space"`. Defaults to `"model"`.
            revision (`str`, *optional*):
                The git revision to commit from. Defaults to the head of the `"main"` branch.
            commit_message (`str`, *optional*):
                The summary (first line) of the generated commit. Defaults to
                `f"Delete files using huggingface_hub"`.
            commit_description (`str` *optional*)
                The description of the generated commit.
            create_pr (`boolean`, *optional*):
                Whether or not to create a Pull Request with that commit. Defaults to `False`.
                If `revision` is not set, PR is opened against the `"main"` branch. If
                `revision` is set and is a branch, PR is opened against this branch. If
                `revision` is set and is not a branch name (example: a commit oid), an
                `RevisionNotFoundError` is returned by the server.
            parent_commit (`str`, *optional*):
                The OID / SHA of the parent commit, as a hexadecimal string. Shorthands (7 first characters) are also supported.
                If specified and `create_pr` is `False`, the commit will fail if `revision` does not point to `parent_commit`.
                If specified and `create_pr` is `True`, the pull request will be created from `parent_commit`.
                Specifying `parent_commit` ensures the repo has not changed before committing the changes, and can be
                especially useful if the repo is updated / committed to concurrently.
        """
        operations = self._prepare_folder_deletions(
            repo_id=repo_id, repo_type=repo_type, delete_patterns=delete_patterns, path_in_repo="", revision=revision
        )

        if commit_message is None:
            commit_message = f"Delete files {' '.join(delete_patterns)} with huggingface_hub"

        return self.create_commit(
            repo_id=repo_id,
            repo_type=repo_type,
            token=token,
            operations=operations,
            revision=revision,
            commit_message=commit_message,
            commit_description=commit_description,
            create_pr=create_pr,
            parent_commit=parent_commit,
        )

    @validate_hf_hub_args
    def delete_folder(
        self,
        path_in_repo: str,
        repo_id: str,
        *,
        token: Union[bool, str, None] = None,
        repo_type: Optional[str] = None,
        revision: Optional[str] = None,
        commit_message: Optional[str] = None,
        commit_description: Optional[str] = None,
        create_pr: Optional[bool] = None,
        parent_commit: Optional[str] = None,
    ) -> CommitInfo:
        """
        Deletes a folder in the given repo.

        Simple wrapper around [`create_commit`] method.

        Args:
            path_in_repo (`str`):
                Relative folder path in the repo, for example: `"checkpoints/1fec34a"`.
            repo_id (`str`):
                The repository from which the folder will be deleted, for example:
                `"username/custom_transformers"`
            token (Union[bool, str, None], optional):
                A valid user access token (string). Defaults to the locally saved
                token, which is the recommended method for authentication (see
                https://huggingface.co/docs/huggingface_hub/quick-start#authentication).
                To disable authentication, pass `False`.
                to the stored token.
            repo_type (`str`, *optional*):
                Set to `"dataset"` or `"space"` if the folder is in a dataset or
                space, `None` or `"model"` if in a model. Default is `None`.
            revision (`str`, *optional*):
                The git revision to commit from. Defaults to the head of the `"main"` branch.
            commit_message (`str`, *optional*):
                The summary / title / first line of the generated commit. Defaults to
                `f"Delete folder {path_in_repo} with huggingface_hub"`.
            commit_description (`str` *optional*)
                The description of the generated commit.
            create_pr (`boolean`, *optional*):
                Whether or not to create a Pull Request with that commit. Defaults to `False`.
                If `revision` is not set, PR is opened against the `"main"` branch. If
                `revision` is set and is a branch, PR is opened against this branch. If
                `revision` is set and is not a branch name (example: a commit oid), an
                `RevisionNotFoundError` is returned by the server.
            parent_commit (`str`, *optional*):
                The OID / SHA of the parent commit, as a hexadecimal string. Shorthands (7 first characters) are also supported.
                If specified and `create_pr` is `False`, the commit will fail if `revision` does not point to `parent_commit`.
                If specified and `create_pr` is `True`, the pull request will be created from `parent_commit`.
                Specifying `parent_commit` ensures the repo has not changed before committing the changes, and can be
                especially useful if the repo is updated / committed to concurrently.
        """
        return self.create_commit(
            repo_id=repo_id,
            repo_type=repo_type,
            token=token,
            operations=[CommitOperationDelete(path_in_repo=path_in_repo, is_folder=True)],
            revision=revision,
            commit_message=(
                commit_message if commit_message is not None else f"Delete folder {path_in_repo} with huggingface_hub"
            ),
            commit_description=commit_description,
            create_pr=create_pr,
            parent_commit=parent_commit,
        )

    def upload_large_folder(
        self,
        repo_id: str,
        folder_path: Union[str, Path],
        *,
        repo_type: str,  # Repo type is required!
        revision: Optional[str] = None,
        private: Optional[bool] = None,
        allow_patterns: Optional[Union[List[str], str]] = None,
        ignore_patterns: Optional[Union[List[str], str]] = None,
        num_workers: Optional[int] = None,
        print_report: bool = True,
        print_report_every: int = 60,
    ) -> None:
        """Upload a large folder to the Hub in the most resilient way possible.

        Several workers are started to upload files in an optimized way. Before being committed to a repo, files must be
        hashed and be pre-uploaded if they are LFS files. Workers will perform these tasks for each file in the folder.
        At each step, some metadata information about the upload process is saved in the folder under `.cache/.huggingface/`
        to be able to resume the process if interrupted. The whole process might result in several commits.

        Args:
            repo_id (`str`):
                The repository to which the file will be uploaded.
                E.g. `"HuggingFaceTB/smollm-corpus"`.
            folder_path (`str` or `Path`):
                Path to the folder to upload on the local file system.
            repo_type (`str`):
                Type of the repository. Must be one of `"model"`, `"dataset"` or `"space"`.
                Unlike in all other `HfApi` methods, `repo_type` is explicitly required here. This is to avoid
                any mistake when uploading a large folder to the Hub, and therefore prevent from having to re-upload
                everything.
            revision (`str`, `optional`):
                The branch to commit to. If not provided, the `main` branch will be used.
            private (`bool`, `optional`):
                Whether the repository should be private.
                If `None` (default), the repo will be public unless the organization's default is private.
            allow_patterns (`List[str]` or `str`, *optional*):
                If provided, only files matching at least one pattern are uploaded.
            ignore_patterns (`List[str]` or `str`, *optional*):
                If provided, files matching any of the patterns are not uploaded.
            num_workers (`int`, *optional*):
                Number of workers to start. Defaults to `os.cpu_count() - 2` (minimum 2).
                A higher number of workers may speed up the process if your machine allows it. However, on machines with a
                slower connection, it is recommended to keep the number of workers low to ensure better resumability.
                Indeed, partially uploaded files will have to be completely re-uploaded if the process is interrupted.
            print_report (`bool`, *optional*):
                Whether to print a report of the upload progress. Defaults to True.
                Report is printed to `sys.stdout` every X seconds (60 by defaults) and overwrites the previous report.
            print_report_every (`int`, *optional*):
                Frequency at which the report is printed. Defaults to 60 seconds.

        <Tip>

        A few things to keep in mind:
            - Repository limits still apply: https://huggingface.co/docs/hub/repositories-recommendations
            - Do not start several processes in parallel.
            - You can interrupt and resume the process at any time.
            - Do not upload the same folder to several repositories. If you need to do so, you must delete the local `.cache/.huggingface/` folder first.

        </Tip>

        <Tip warning={true}>

        While being much more robust to upload large folders, `upload_large_folder` is more limited than [`upload_folder`] feature-wise. In practice:
            - you cannot set a custom `path_in_repo`. If you want to upload to a subfolder, you need to set the proper structure locally.
            - you cannot set a custom `commit_message` and `commit_description` since multiple commits are created.
            - you cannot delete from the repo while uploading. Please make a separate commit first.
            - you cannot create a PR directly. Please create a PR first (from the UI or using [`create_pull_request`]) and then commit to it by passing `revision`.

        </Tip>

        **Technical details:**

        `upload_large_folder` process is as follow:
            1. (Check parameters and setup.)
            2. Create repo if missing.
            3. List local files to upload.
            4. Start workers. Workers can perform the following tasks:
                - Hash a file.
                - Get upload mode (regular or LFS) for a list of files.
                - Pre-upload an LFS file.
                - Commit a bunch of files.
            Once a worker finishes a task, it will move on to the next task based on the priority list (see below) until
            all files are uploaded and committed.
            5. While workers are up, regularly print a report to sys.stdout.

        Order of priority:
            1. Commit if more than 5 minutes since last commit attempt (and at least 1 file).
            2. Commit if at least 150 files are ready to commit.
            3. Get upload mode if at least 10 files have been hashed.
            4. Pre-upload LFS file if at least 1 file and no worker is pre-uploading.
            5. Hash file if at least 1 file and no worker is hashing.
            6. Get upload mode if at least 1 file and no worker is getting upload mode.
            7. Pre-upload LFS file if at least 1 file (exception: if hf_transfer is enabled, only 1 worker can preupload LFS at a time).
            8. Hash file if at least 1 file to hash.
            9. Get upload mode if at least 1 file to get upload mode.
            10. Commit if at least 1 file to commit and at least 1 min since last commit attempt.
            11. Commit if at least 1 file to commit and all other queues are empty.

        Special rules:
            - If `hf_transfer` is enabled, only 1 LFS uploader at a time. Otherwise the CPU would be bloated by `hf_transfer`.
            - Only one worker can commit at a time.
            - If no tasks are available, the worker waits for 10 seconds before checking again.
        """
        return upload_large_folder_internal(
            self,
            repo_id=repo_id,
            folder_path=folder_path,
            repo_type=repo_type,
            revision=revision,
            private=private,
            allow_patterns=allow_patterns,
            ignore_patterns=ignore_patterns,
            num_workers=num_workers,
            print_report=print_report,
            print_report_every=print_report_every,
        )

    @validate_hf_hub_args
    def get_hf_file_metadata(
        self,
        *,
        url: str,
        token: Union[bool, str, None] = None,
        proxies: Optional[Dict] = None,
        timeout: Optional[float] = constants.DEFAULT_REQUEST_TIMEOUT,
    ) -> HfFileMetadata:
        """Fetch metadata of a file versioned on the Hub for a given url.

        Args:
            url (`str`):
                File url, for example returned by [`hf_hub_url`].
            token (Union[bool, str, None], optional):
                A valid user access token (string). Defaults to the locally saved
                token, which is the recommended method for authentication (see
                https://huggingface.co/docs/huggingface_hub/quick-start#authentication).
                To disable authentication, pass `False`.
            proxies (`dict`, *optional*):
                Dictionary mapping protocol to the URL of the proxy passed to `requests.request`.
            timeout (`float`, *optional*, defaults to 10):
                How many seconds to wait for the server to send metadata before giving up.

        Returns:
            A [`HfFileMetadata`] object containing metadata such as location, etag, size and commit_hash.
        """
        if token is None:
            # Cannot do `token = token or self.token` as token can be `False`.
            token = self.token

        return get_hf_file_metadata(
            url=url,
            token=token,
            proxies=proxies,
            timeout=timeout,
            library_name=self.library_name,
            library_version=self.library_version,
            user_agent=self.user_agent,
        )

    @validate_hf_hub_args
    def hf_hub_download(
        self,
        repo_id: str,
        filename: str,
        *,
        subfolder: Optional[str] = None,
        repo_type: Optional[str] = None,
        revision: Optional[str] = None,
        cache_dir: Union[str, Path, None] = None,
        local_dir: Union[str, Path, None] = None,
        force_download: bool = False,
        proxies: Optional[Dict] = None,
        etag_timeout: float = constants.DEFAULT_ETAG_TIMEOUT,
        token: Union[bool, str, None] = None,
        local_files_only: bool = False,
        # Deprecated args
        resume_download: Optional[bool] = None,
        force_filename: Optional[str] = None,
        local_dir_use_symlinks: Union[bool, Literal["auto"]] = "auto",
    ) -> str:
        """Download a given file if it's not already present in the local cache.

        The new cache file layout looks like this:
        - The cache directory contains one subfolder per repo_id (namespaced by repo type)
        - inside each repo folder:
            - refs is a list of the latest known revision => commit_hash pairs
            - blobs contains the actual file blobs (identified by their git-sha or sha256, depending on
            whether they're LFS files or not)
            - snapshots contains one subfolder per commit, each "commit" contains the subset of the files
            that have been resolved at that particular commit. Each filename is a symlink to the blob
            at that particular commit.

        ```
        [  96]  .
        └── [ 160]  models--julien-c--EsperBERTo-small
            ├── [ 160]  blobs
            │   ├── [321M]  403450e234d65943a7dcf7e05a771ce3c92faa84dd07db4ac20f592037a1e4bd
            │   ├── [ 398]  7cb18dc9bafbfcf74629a4b760af1b160957a83e
            │   └── [1.4K]  d7edf6bd2a681fb0175f7735299831ee1b22b812
            ├── [  96]  refs
            │   └── [  40]  main
            └── [ 128]  snapshots
                ├── [ 128]  2439f60ef33a0d46d85da5001d52aeda5b00ce9f
                │   ├── [  52]  README.md -> ../../blobs/d7edf6bd2a681fb0175f7735299831ee1b22b812
                │   └── [  76]  pytorch_model.bin -> ../../blobs/403450e234d65943a7dcf7e05a771ce3c92faa84dd07db4ac20f592037a1e4bd
                └── [ 128]  bbc77c8132af1cc5cf678da3f1ddf2de43606d48
                    ├── [  52]  README.md -> ../../blobs/7cb18dc9bafbfcf74629a4b760af1b160957a83e
                    └── [  76]  pytorch_model.bin -> ../../blobs/403450e234d65943a7dcf7e05a771ce3c92faa84dd07db4ac20f592037a1e4bd
        ```

        If `local_dir` is provided, the file structure from the repo will be replicated in this location. When using this
        option, the `cache_dir` will not be used and a `.cache/huggingface/` folder will be created at the root of `local_dir`
        to store some metadata related to the downloaded files. While this mechanism is not as robust as the main
        cache-system, it's optimized for regularly pulling the latest version of a repository.

        Args:
            repo_id (`str`):
                A user or an organization name and a repo name separated by a `/`.
            filename (`str`):
                The name of the file in the repo.
            subfolder (`str`, *optional*):
                An optional value corresponding to a folder inside the repository.
            repo_type (`str`, *optional*):
                Set to `"dataset"` or `"space"` if downloading from a dataset or space,
                `None` or `"model"` if downloading from a model. Default is `None`.
            revision (`str`, *optional*):
                An optional Git revision id which can be a branch name, a tag, or a
                commit hash.
            cache_dir (`str`, `Path`, *optional*):
                Path to the folder where cached files are stored.
            local_dir (`str` or `Path`, *optional*):
                If provided, the downloaded file will be placed under this directory.
            force_download (`bool`, *optional*, defaults to `False`):
                Whether the file should be downloaded even if it already exists in
                the local cache.
            proxies (`dict`, *optional*):
                Dictionary mapping protocol to the URL of the proxy passed to
                `requests.request`.
            etag_timeout (`float`, *optional*, defaults to `10`):
                When fetching ETag, how many seconds to wait for the server to send
                data before giving up which is passed to `requests.request`.
            token (Union[bool, str, None], optional):
                A valid user access token (string). Defaults to the locally saved
                token, which is the recommended method for authentication (see
                https://huggingface.co/docs/huggingface_hub/quick-start#authentication).
                To disable authentication, pass `False`.
            local_files_only (`bool`, *optional*, defaults to `False`):
                If `True`, avoid downloading the file and return the path to the
                local cached file if it exists.

        Returns:
            `str`: Local path of file or if networking is off, last version of file cached on disk.

        Raises:
            [`~utils.RepositoryNotFoundError`]
                If the repository to download from cannot be found. This may be because it doesn't exist,
                or because it is set to `private` and you do not have access.
            [`~utils.RevisionNotFoundError`]
                If the revision to download from cannot be found.
            [`~utils.EntryNotFoundError`]
                If the file to download cannot be found.
            [`~utils.LocalEntryNotFoundError`]
                If network is disabled or unavailable and file is not found in cache.
            [`EnvironmentError`](https://docs.python.org/3/library/exceptions.html#EnvironmentError)
                If `token=True` but the token cannot be found.
            [`OSError`](https://docs.python.org/3/library/exceptions.html#OSError)
                If ETag cannot be determined.
            [`ValueError`](https://docs.python.org/3/library/exceptions.html#ValueError)
                If some parameter value is invalid.
        """
        from .file_download import hf_hub_download

        if token is None:
            # Cannot do `token = token or self.token` as token can be `False`.
            token = self.token

        return hf_hub_download(
            repo_id=repo_id,
            filename=filename,
            subfolder=subfolder,
            repo_type=repo_type,
            revision=revision,
            endpoint=self.endpoint,
            library_name=self.library_name,
            library_version=self.library_version,
            cache_dir=cache_dir,
            local_dir=local_dir,
            local_dir_use_symlinks=local_dir_use_symlinks,
            user_agent=self.user_agent,
            force_download=force_download,
            force_filename=force_filename,
            proxies=proxies,
            etag_timeout=etag_timeout,
            resume_download=resume_download,
            token=token,
            headers=self.headers,
            local_files_only=local_files_only,
        )

    @validate_hf_hub_args
    def snapshot_download(
        self,
        repo_id: str,
        *,
        repo_type: Optional[str] = None,
        revision: Optional[str] = None,
        cache_dir: Union[str, Path, None] = None,
        local_dir: Union[str, Path, None] = None,
        proxies: Optional[Dict] = None,
        etag_timeout: float = constants.DEFAULT_ETAG_TIMEOUT,
        force_download: bool = False,
        token: Union[bool, str, None] = None,
        local_files_only: bool = False,
        allow_patterns: Optional[Union[List[str], str]] = None,
        ignore_patterns: Optional[Union[List[str], str]] = None,
        max_workers: int = 8,
        tqdm_class: Optional[Type[base_tqdm]] = None,
        # Deprecated args
        local_dir_use_symlinks: Union[bool, Literal["auto"]] = "auto",
        resume_download: Optional[bool] = None,
    ) -> str:
        """Download repo files.

        Download a whole snapshot of a repo's files at the specified revision. This is useful when you want all files from
        a repo, because you don't know which ones you will need a priori. All files are nested inside a folder in order
        to keep their actual filename relative to that folder. You can also filter which files to download using
        `allow_patterns` and `ignore_patterns`.

        If `local_dir` is provided, the file structure from the repo will be replicated in this location. When using this
        option, the `cache_dir` will not be used and a `.cache/huggingface/` folder will be created at the root of `local_dir`
        to store some metadata related to the downloaded files.While this mechanism is not as robust as the main
        cache-system, it's optimized for regularly pulling the latest version of a repository.

        An alternative would be to clone the repo but this requires git and git-lfs to be installed and properly
        configured. It is also not possible to filter which files to download when cloning a repository using git.

        Args:
            repo_id (`str`):
                A user or an organization name and a repo name separated by a `/`.
            repo_type (`str`, *optional*):
                Set to `"dataset"` or `"space"` if downloading from a dataset or space,
                `None` or `"model"` if downloading from a model. Default is `None`.
            revision (`str`, *optional*):
                An optional Git revision id which can be a branch name, a tag, or a
                commit hash.
            cache_dir (`str`, `Path`, *optional*):
                Path to the folder where cached files are stored.
            local_dir (`str` or `Path`, *optional*):
                If provided, the downloaded files will be placed under this directory.
            proxies (`dict`, *optional*):
                Dictionary mapping protocol to the URL of the proxy passed to
                `requests.request`.
            etag_timeout (`float`, *optional*, defaults to `10`):
                When fetching ETag, how many seconds to wait for the server to send
                data before giving up which is passed to `requests.request`.
            force_download (`bool`, *optional*, defaults to `False`):
                Whether the file should be downloaded even if it already exists in the local cache.
            token (Union[bool, str, None], optional):
                A valid user access token (string). Defaults to the locally saved
                token, which is the recommended method for authentication (see
                https://huggingface.co/docs/huggingface_hub/quick-start#authentication).
                To disable authentication, pass `False`.
            local_files_only (`bool`, *optional*, defaults to `False`):
                If `True`, avoid downloading the file and return the path to the
                local cached file if it exists.
            allow_patterns (`List[str]` or `str`, *optional*):
                If provided, only files matching at least one pattern are downloaded.
            ignore_patterns (`List[str]` or `str`, *optional*):
                If provided, files matching any of the patterns are not downloaded.
            max_workers (`int`, *optional*):
                Number of concurrent threads to download files (1 thread = 1 file download).
                Defaults to 8.
            tqdm_class (`tqdm`, *optional*):
                If provided, overwrites the default behavior for the progress bar. Passed
                argument must inherit from `tqdm.auto.tqdm` or at least mimic its behavior.
                Note that the `tqdm_class` is not passed to each individual download.
                Defaults to the custom HF progress bar that can be disabled by setting
                `HF_HUB_DISABLE_PROGRESS_BARS` environment variable.

        Returns:
            `str`: folder path of the repo snapshot.

        Raises:
            [`~utils.RepositoryNotFoundError`]
                If the repository to download from cannot be found. This may be because it doesn't exist,
                or because it is set to `private` and you do not have access.
            [`~utils.RevisionNotFoundError`]
                If the revision to download from cannot be found.
            [`EnvironmentError`](https://docs.python.org/3/library/exceptions.html#EnvironmentError)
                If `token=True` and the token cannot be found.
            [`OSError`](https://docs.python.org/3/library/exceptions.html#OSError) if
                ETag cannot be determined.
            [`ValueError`](https://docs.python.org/3/library/exceptions.html#ValueError)
                if some parameter value is invalid.
        """
        from ._snapshot_download import snapshot_download

        if token is None:
            # Cannot do `token = token or self.token` as token can be `False`.
            token = self.token

        return snapshot_download(
            repo_id=repo_id,
            repo_type=repo_type,
            revision=revision,
            endpoint=self.endpoint,
            cache_dir=cache_dir,
            local_dir=local_dir,
            local_dir_use_symlinks=local_dir_use_symlinks,
            library_name=self.library_name,
            library_version=self.library_version,
            user_agent=self.user_agent,
            proxies=proxies,
            etag_timeout=etag_timeout,
            resume_download=resume_download,
            force_download=force_download,
            token=token,
            local_files_only=local_files_only,
            allow_patterns=allow_patterns,
            ignore_patterns=ignore_patterns,
            max_workers=max_workers,
            tqdm_class=tqdm_class,
        )

    def get_safetensors_metadata(
        self,
        repo_id: str,
        *,
        repo_type: Optional[str] = None,
        revision: Optional[str] = None,
        token: Union[bool, str, None] = None,
    ) -> SafetensorsRepoMetadata:
        """
        Parse metadata for a safetensors repo on the Hub.

        We first check if the repo has a single safetensors file or a sharded safetensors repo. If it's a single
        safetensors file, we parse the metadata from this file. If it's a sharded safetensors repo, we parse the
        metadata from the index file and then parse the metadata from each shard.

        To parse metadata from a single safetensors file, use [`parse_safetensors_file_metadata`].

        For more details regarding the safetensors format, check out https://huggingface.co/docs/safetensors/index#format.

        Args:
            repo_id (`str`):
                A user or an organization name and a repo name separated by a `/`.
            repo_type (`str`, *optional*):
                Set to `"dataset"` or `"space"` if the file is in a dataset or space, `None` or `"model"` if in a
                model. Default is `None`.
            revision (`str`, *optional*):
                The git revision to fetch the file from. Can be a branch name, a tag, or a commit hash. Defaults to the
                head of the `"main"` branch.
            token (Union[bool, str, None], optional):
                A valid user access token (string). Defaults to the locally saved
                token, which is the recommended method for authentication (see
                https://huggingface.co/docs/huggingface_hub/quick-start#authentication).
                To disable authentication, pass `False`.

        Returns:
            [`SafetensorsRepoMetadata`]: information related to safetensors repo.

        Raises:
            [`NotASafetensorsRepoError`]
                If the repo is not a safetensors repo i.e. doesn't have either a
              `model.safetensors` or a `model.safetensors.index.json` file.
            [`SafetensorsParsingError`]
                If a safetensors file header couldn't be parsed correctly.

        Example:
            ```py
            # Parse repo with single weights file
            >>> metadata = get_safetensors_metadata("bigscience/bloomz-560m")
            >>> metadata
            SafetensorsRepoMetadata(
                metadata=None,
                sharded=False,
                weight_map={'h.0.input_layernorm.bias': 'model.safetensors', ...},
                files_metadata={'model.safetensors': SafetensorsFileMetadata(...)}
            )
            >>> metadata.files_metadata["model.safetensors"].metadata
            {'format': 'pt'}

            # Parse repo with sharded model
            >>> metadata = get_safetensors_metadata("bigscience/bloom")
            Parse safetensors files: 100%|██████████████████████████████████████████| 72/72 [00:12<00:00,  5.78it/s]
            >>> metadata
            SafetensorsRepoMetadata(metadata={'total_size': 352494542848}, sharded=True, weight_map={...}, files_metadata={...})
            >>> len(metadata.files_metadata)
            72  # All safetensors files have been fetched

            # Parse repo with sharded model
            >>> get_safetensors_metadata("runwayml/stable-diffusion-v1-5")
            NotASafetensorsRepoError: 'runwayml/stable-diffusion-v1-5' is not a safetensors repo. Couldn't find 'model.safetensors.index.json' or 'model.safetensors' files.
            ```
        """
        if self.file_exists(  # Single safetensors file => non-sharded model
            repo_id=repo_id,
            filename=constants.SAFETENSORS_SINGLE_FILE,
            repo_type=repo_type,
            revision=revision,
            token=token,
        ):
            file_metadata = self.parse_safetensors_file_metadata(
                repo_id=repo_id,
                filename=constants.SAFETENSORS_SINGLE_FILE,
                repo_type=repo_type,
                revision=revision,
                token=token,
            )
            return SafetensorsRepoMetadata(
                metadata=None,
                sharded=False,
                weight_map={
                    tensor_name: constants.SAFETENSORS_SINGLE_FILE for tensor_name in file_metadata.tensors.keys()
                },
                files_metadata={constants.SAFETENSORS_SINGLE_FILE: file_metadata},
            )
        elif self.file_exists(  # Multiple safetensors files => sharded with index
            repo_id=repo_id,
            filename=constants.SAFETENSORS_INDEX_FILE,
            repo_type=repo_type,
            revision=revision,
            token=token,
        ):
            # Fetch index
            index_file = self.hf_hub_download(
                repo_id=repo_id,
                filename=constants.SAFETENSORS_INDEX_FILE,
                repo_type=repo_type,
                revision=revision,
                token=token,
            )
            with open(index_file) as f:
                index = json.load(f)

            weight_map = index.get("weight_map", {})

            # Fetch metadata per shard
            files_metadata = {}

            def _parse(filename: str) -> None:
                files_metadata[filename] = self.parse_safetensors_file_metadata(
                    repo_id=repo_id, filename=filename, repo_type=repo_type, revision=revision, token=token
                )

            thread_map(
                _parse,
                set(weight_map.values()),
                desc="Parse safetensors files",
                tqdm_class=hf_tqdm,
            )

            return SafetensorsRepoMetadata(
                metadata=index.get("metadata", None),
                sharded=True,
                weight_map=weight_map,
                files_metadata=files_metadata,
            )
        else:
            # Not a safetensors repo
            raise NotASafetensorsRepoError(
                f"'{repo_id}' is not a safetensors repo. Couldn't find '{constants.SAFETENSORS_INDEX_FILE}' or '{constants.SAFETENSORS_SINGLE_FILE}' files."
            )

    def parse_safetensors_file_metadata(
        self,
        repo_id: str,
        filename: str,
        *,
        repo_type: Optional[str] = None,
        revision: Optional[str] = None,
        token: Union[bool, str, None] = None,
    ) -> SafetensorsFileMetadata:
        """
        Parse metadata from a safetensors file on the Hub.

        To parse metadata from all safetensors files in a repo at once, use [`get_safetensors_metadata`].

        For more details regarding the safetensors format, check out https://huggingface.co/docs/safetensors/index#format.

        Args:
            repo_id (`str`):
                A user or an organization name and a repo name separated by a `/`.
            filename (`str`):
                The name of the file in the repo.
            repo_type (`str`, *optional*):
                Set to `"dataset"` or `"space"` if the file is in a dataset or space, `None` or `"model"` if in a
                model. Default is `None`.
            revision (`str`, *optional*):
                The git revision to fetch the file from. Can be a branch name, a tag, or a commit hash. Defaults to the
                head of the `"main"` branch.
            token (Union[bool, str, None], optional):
                A valid user access token (string). Defaults to the locally saved
                token, which is the recommended method for authentication (see
                https://huggingface.co/docs/huggingface_hub/quick-start#authentication).
                To disable authentication, pass `False`.

        Returns:
            [`SafetensorsFileMetadata`]: information related to a safetensors file.

        Raises:
            [`NotASafetensorsRepoError`]:
                If the repo is not a safetensors repo i.e. doesn't have either a
              `model.safetensors` or a `model.safetensors.index.json` file.
            [`SafetensorsParsingError`]:
                If a safetensors file header couldn't be parsed correctly.
        """
        url = hf_hub_url(
            repo_id=repo_id, filename=filename, repo_type=repo_type, revision=revision, endpoint=self.endpoint
        )
        _headers = self._build_hf_headers(token=token)

        # 1. Fetch first 100kb
        # Empirically, 97% of safetensors files have a metadata size < 100kb (over the top 1000 models on the Hub).
        # We assume fetching 100kb is faster than making 2 GET requests. Therefore we always fetch the first 100kb to
        # avoid the 2nd GET in most cases.
        # See https://github.com/huggingface/huggingface_hub/pull/1855#discussion_r1404286419.
        response = get_session().get(url, headers={**_headers, "range": "bytes=0-100000"})
        hf_raise_for_status(response)

        # 2. Parse metadata size
        metadata_size = struct.unpack("<Q", response.content[:8])[0]
        if metadata_size > constants.SAFETENSORS_MAX_HEADER_LENGTH:
            raise SafetensorsParsingError(
                f"Failed to parse safetensors header for '{filename}' (repo '{repo_id}', revision "
                f"'{revision or constants.DEFAULT_REVISION}'): safetensors header is too big. Maximum supported size is "
                f"{constants.SAFETENSORS_MAX_HEADER_LENGTH} bytes (got {metadata_size})."
            )

        # 3.a. Get metadata from payload
        if metadata_size <= 100000:
            metadata_as_bytes = response.content[8 : 8 + metadata_size]
        else:  # 3.b. Request full metadata
            response = get_session().get(url, headers={**_headers, "range": f"bytes=8-{metadata_size + 7}"})
            hf_raise_for_status(response)
            metadata_as_bytes = response.content

        # 4. Parse json header
        try:
            metadata_as_dict = json.loads(metadata_as_bytes.decode(errors="ignore"))
        except json.JSONDecodeError as e:
            raise SafetensorsParsingError(
                f"Failed to parse safetensors header for '{filename}' (repo '{repo_id}', revision "
                f"'{revision or constants.DEFAULT_REVISION}'): header is not json-encoded string. Please make sure this is a "
                "correctly formatted safetensors file."
            ) from e

        try:
            return SafetensorsFileMetadata(
                metadata=metadata_as_dict.get("__metadata__", {}),
                tensors={
                    key: TensorInfo(
                        dtype=tensor["dtype"],
                        shape=tensor["shape"],
                        data_offsets=tuple(tensor["data_offsets"]),  # type: ignore
                    )
                    for key, tensor in metadata_as_dict.items()
                    if key != "__metadata__"
                },
            )
        except (KeyError, IndexError) as e:
            raise SafetensorsParsingError(
                f"Failed to parse safetensors header for '{filename}' (repo '{repo_id}', revision "
                f"'{revision or constants.DEFAULT_REVISION}'): header format not recognized. Please make sure this is a correctly"
                " formatted safetensors file."
            ) from e

    @validate_hf_hub_args
    def create_branch(
        self,
        repo_id: str,
        *,
        branch: str,
        revision: Optional[str] = None,
        token: Union[bool, str, None] = None,
        repo_type: Optional[str] = None,
        exist_ok: bool = False,
    ) -> None:
        """
        Create a new branch for a repo on the Hub, starting from the specified revision (defaults to `main`).
        To find a revision suiting your needs, you can use [`list_repo_refs`] or [`list_repo_commits`].

        Args:
            repo_id (`str`):
                The repository in which the branch will be created.
                Example: `"user/my-cool-model"`.

            branch (`str`):
                The name of the branch to create.

            revision (`str`, *optional*):
                The git revision to create the branch from. It can be a branch name or
                the OID/SHA of a commit, as a hexadecimal string. Defaults to the head
                of the `"main"` branch.

            token (Union[bool, str, None], optional):
                A valid user access token (string). Defaults to the locally saved
                token, which is the recommended method for authentication (see
                https://huggingface.co/docs/huggingface_hub/quick-start#authentication).
                To disable authentication, pass `False`.

            repo_type (`str`, *optional*):
                Set to `"dataset"` or `"space"` if creating a branch on a dataset or
                space, `None` or `"model"` if tagging a model. Default is `None`.

            exist_ok (`bool`, *optional*, defaults to `False`):
                If `True`, do not raise an error if branch already exists.

        Raises:
            [`~utils.RepositoryNotFoundError`]:
                If repository is not found (error 404): wrong repo_id/repo_type, private
                but not authenticated or repo does not exist.
            [`~utils.BadRequestError`]:
                If invalid reference for a branch. Ex: `refs/pr/5` or 'refs/foo/bar'.
            [`~utils.HfHubHTTPError`]:
                If the branch already exists on the repo (error 409) and `exist_ok` is
                set to `False`.
        """
        if repo_type is None:
            repo_type = constants.REPO_TYPE_MODEL
        branch = quote(branch, safe="")

        # Prepare request
        branch_url = f"{self.endpoint}/api/{repo_type}s/{repo_id}/branch/{branch}"
        headers = self._build_hf_headers(token=token)
        payload = {}
        if revision is not None:
            payload["startingPoint"] = revision

        # Create branch
        response = get_session().post(url=branch_url, headers=headers, json=payload)
        try:
            hf_raise_for_status(response)
        except HfHubHTTPError as e:
            if exist_ok and e.response.status_code == 409:
                return
            elif exist_ok and e.response.status_code == 403:
                # No write permission on the namespace but branch might already exist
                try:
                    refs = self.list_repo_refs(repo_id=repo_id, repo_type=repo_type, token=token)
                    for branch_ref in refs.branches:
                        if branch_ref.name == branch:
                            return  # Branch already exists => do not raise
                except HfHubHTTPError:
                    pass  # We raise the original error if the branch does not exist
            raise

    @validate_hf_hub_args
    def delete_branch(
        self,
        repo_id: str,
        *,
        branch: str,
        token: Union[bool, str, None] = None,
        repo_type: Optional[str] = None,
    ) -> None:
        """
        Delete a branch from a repo on the Hub.

        Args:
            repo_id (`str`):
                The repository in which a branch will be deleted.
                Example: `"user/my-cool-model"`.

            branch (`str`):
                The name of the branch to delete.

            token (Union[bool, str, None], optional):
                A valid user access token (string). Defaults to the locally saved
                token, which is the recommended method for authentication (see
                https://huggingface.co/docs/huggingface_hub/quick-start#authentication).
                To disable authentication, pass `False`.

            repo_type (`str`, *optional*):
                Set to `"dataset"` or `"space"` if creating a branch on a dataset or
                space, `None` or `"model"` if tagging a model. Default is `None`.

        Raises:
            [`~utils.RepositoryNotFoundError`]:
                If repository is not found (error 404): wrong repo_id/repo_type, private
                but not authenticated or repo does not exist.
            [`~utils.HfHubHTTPError`]:
                If trying to delete a protected branch. Ex: `main` cannot be deleted.
            [`~utils.HfHubHTTPError`]:
                If trying to delete a branch that does not exist.

        """
        if repo_type is None:
            repo_type = constants.REPO_TYPE_MODEL
        branch = quote(branch, safe="")

        # Prepare request
        branch_url = f"{self.endpoint}/api/{repo_type}s/{repo_id}/branch/{branch}"
        headers = self._build_hf_headers(token=token)

        # Delete branch
        response = get_session().delete(url=branch_url, headers=headers)
        hf_raise_for_status(response)

    @validate_hf_hub_args
    def create_tag(
        self,
        repo_id: str,
        *,
        tag: str,
        tag_message: Optional[str] = None,
        revision: Optional[str] = None,
        token: Union[bool, str, None] = None,
        repo_type: Optional[str] = None,
        exist_ok: bool = False,
    ) -> None:
        """
        Tag a given commit of a repo on the Hub.

        Args:
            repo_id (`str`):
                The repository in which a commit will be tagged.
                Example: `"user/my-cool-model"`.

            tag (`str`):
                The name of the tag to create.

            tag_message (`str`, *optional*):
                The description of the tag to create.

            revision (`str`, *optional*):
                The git revision to tag. It can be a branch name or the OID/SHA of a
                commit, as a hexadecimal string. Shorthands (7 first characters) are
                also supported. Defaults to the head of the `"main"` branch.

            token (Union[bool, str, None], optional):
                A valid user access token (string). Defaults to the locally saved
                token, which is the recommended method for authentication (see
                https://huggingface.co/docs/huggingface_hub/quick-start#authentication).
                To disable authentication, pass `False`.

            repo_type (`str`, *optional*):
                Set to `"dataset"` or `"space"` if tagging a dataset or
                space, `None` or `"model"` if tagging a model. Default is
                `None`.

            exist_ok (`bool`, *optional*, defaults to `False`):
                If `True`, do not raise an error if tag already exists.

        Raises:
            [`~utils.RepositoryNotFoundError`]:
                If repository is not found (error 404): wrong repo_id/repo_type, private
                but not authenticated or repo does not exist.
            [`~utils.RevisionNotFoundError`]:
                If revision is not found (error 404) on the repo.
            [`~utils.HfHubHTTPError`]:
                If the branch already exists on the repo (error 409) and `exist_ok` is
                set to `False`.
        """
        if repo_type is None:
            repo_type = constants.REPO_TYPE_MODEL
        revision = quote(revision, safe="") if revision is not None else constants.DEFAULT_REVISION

        # Prepare request
        tag_url = f"{self.endpoint}/api/{repo_type}s/{repo_id}/tag/{revision}"
        headers = self._build_hf_headers(token=token)
        payload = {"tag": tag}
        if tag_message is not None:
            payload["message"] = tag_message

        # Tag
        response = get_session().post(url=tag_url, headers=headers, json=payload)
        try:
            hf_raise_for_status(response)
        except HfHubHTTPError as e:
            if not (e.response.status_code == 409 and exist_ok):
                raise

    @validate_hf_hub_args
    def delete_tag(
        self,
        repo_id: str,
        *,
        tag: str,
        token: Union[bool, str, None] = None,
        repo_type: Optional[str] = None,
    ) -> None:
        """
        Delete a tag from a repo on the Hub.

        Args:
            repo_id (`str`):
                The repository in which a tag will be deleted.
                Example: `"user/my-cool-model"`.

            tag (`str`):
                The name of the tag to delete.

            token (Union[bool, str, None], optional):
                A valid user access token (string). Defaults to the locally saved
                token, which is the recommended method for authentication (see
                https://huggingface.co/docs/huggingface_hub/quick-start#authentication).
                To disable authentication, pass `False`.

            repo_type (`str`, *optional*):
                Set to `"dataset"` or `"space"` if tagging a dataset or space, `None` or
                `"model"` if tagging a model. Default is `None`.

        Raises:
            [`~utils.RepositoryNotFoundError`]:
                If repository is not found (error 404): wrong repo_id/repo_type, private
                but not authenticated or repo does not exist.
            [`~utils.RevisionNotFoundError`]:
                If tag is not found.
        """
        if repo_type is None:
            repo_type = constants.REPO_TYPE_MODEL
        tag = quote(tag, safe="")

        # Prepare request
        tag_url = f"{self.endpoint}/api/{repo_type}s/{repo_id}/tag/{tag}"
        headers = self._build_hf_headers(token=token)

        # Un-tag
        response = get_session().delete(url=tag_url, headers=headers)
        hf_raise_for_status(response)

    @validate_hf_hub_args
    def get_full_repo_name(
        self,
        model_id: str,
        *,
        organization: Optional[str] = None,
        token: Union[bool, str, None] = None,
    ):
        """
        Returns the repository name for a given model ID and optional
        organization.

        Args:
            model_id (`str`):
                The name of the model.
            organization (`str`, *optional*):
                If passed, the repository name will be in the organization
                namespace instead of the user namespace.
            token (Union[bool, str, None], optional):
                A valid user access token (string). Defaults to the locally saved
                token, which is the recommended method for authentication (see
                https://huggingface.co/docs/huggingface_hub/quick-start#authentication).
                To disable authentication, pass `False`.

        Returns:
            `str`: The repository name in the user's namespace
            ({username}/{model_id}) if no organization is passed, and under the
            organization namespace ({organization}/{model_id}) otherwise.
        """
        if organization is None:
            if "/" in model_id:
                username = model_id.split("/")[0]
            else:
                username = self.whoami(token=token)["name"]  # type: ignore
            return f"{username}/{model_id}"
        else:
            return f"{organization}/{model_id}"

    @validate_hf_hub_args
    def get_repo_discussions(
        self,
        repo_id: str,
        *,
        author: Optional[str] = None,
        discussion_type: Optional[constants.DiscussionTypeFilter] = None,
        discussion_status: Optional[constants.DiscussionStatusFilter] = None,
        repo_type: Optional[str] = None,
        token: Union[bool, str, None] = None,
    ) -> Iterator[Discussion]:
        """
        Fetches Discussions and Pull Requests for the given repo.

        Args:
            repo_id (`str`):
                A namespace (user or an organization) and a repo name separated
                by a `/`.
            author (`str`, *optional*):
                Pass a value to filter by discussion author. `None` means no filter.
                Default is `None`.
            discussion_type (`str`, *optional*):
                Set to `"pull_request"` to fetch only pull requests, `"discussion"`
                to fetch only discussions. Set to `"all"` or `None` to fetch both.
                Default is `None`.
            discussion_status (`str`, *optional*):
                Set to `"open"` (respectively `"closed"`) to fetch only open
                (respectively closed) discussions. Set to `"all"` or `None`
                to fetch both.
                Default is `None`.
            repo_type (`str`, *optional*):
                Set to `"dataset"` or `"space"` if fetching from a dataset or
                space, `None` or `"model"` if fetching from a model. Default is
                `None`.
            token (Union[bool, str, None], optional):
                A valid user access token (string). Defaults to the locally saved
                token, which is the recommended method for authentication (see
                https://huggingface.co/docs/huggingface_hub/quick-start#authentication).
                To disable authentication, pass `False`.

        Returns:
            `Iterator[Discussion]`: An iterator of [`Discussion`] objects.

        Example:
            Collecting all discussions of a repo in a list:

            ```python
            >>> from huggingface_hub import get_repo_discussions
            >>> discussions_list = list(get_repo_discussions(repo_id="bert-base-uncased"))
            ```

            Iterating over discussions of a repo:

            ```python
            >>> from huggingface_hub import get_repo_discussions
            >>> for discussion in get_repo_discussions(repo_id="bert-base-uncased"):
            ...     print(discussion.num, discussion.title)
            ```
        """
        if repo_type not in constants.REPO_TYPES:
            raise ValueError(f"Invalid repo type, must be one of {constants.REPO_TYPES}")
        if repo_type is None:
            repo_type = constants.REPO_TYPE_MODEL
        if discussion_type is not None and discussion_type not in constants.DISCUSSION_TYPES:
            raise ValueError(f"Invalid discussion_type, must be one of {constants.DISCUSSION_TYPES}")
        if discussion_status is not None and discussion_status not in constants.DISCUSSION_STATUS:
            raise ValueError(f"Invalid discussion_status, must be one of {constants.DISCUSSION_STATUS}")

        headers = self._build_hf_headers(token=token)
        path = f"{self.endpoint}/api/{repo_type}s/{repo_id}/discussions"

        params: Dict[str, Union[str, int]] = {}
        if discussion_type is not None:
            params["type"] = discussion_type
        if discussion_status is not None:
            params["status"] = discussion_status
        if author is not None:
            params["author"] = author

        def _fetch_discussion_page(page_index: int):
            params["p"] = page_index
            resp = get_session().get(path, headers=headers, params=params)
            hf_raise_for_status(resp)
            paginated_discussions = resp.json()
            total = paginated_discussions["count"]
            start = paginated_discussions["start"]
            discussions = paginated_discussions["discussions"]
            has_next = (start + len(discussions)) < total
            return discussions, has_next

        has_next, page_index = True, 0

        while has_next:
            discussions, has_next = _fetch_discussion_page(page_index=page_index)
            for discussion in discussions:
                yield Discussion(
                    title=discussion["title"],
                    num=discussion["num"],
                    author=discussion.get("author", {}).get("name", "deleted"),
                    created_at=parse_datetime(discussion["createdAt"]),
                    status=discussion["status"],
                    repo_id=discussion["repo"]["name"],
                    repo_type=discussion["repo"]["type"],
                    is_pull_request=discussion["isPullRequest"],
                    endpoint=self.endpoint,
                )
            page_index = page_index + 1

    @validate_hf_hub_args
    def get_discussion_details(
        self,
        repo_id: str,
        discussion_num: int,
        *,
        repo_type: Optional[str] = None,
        token: Union[bool, str, None] = None,
    ) -> DiscussionWithDetails:
        """Fetches a Discussion's / Pull Request 's details from the Hub.

        Args:
            repo_id (`str`):
                A namespace (user or an organization) and a repo name separated
                by a `/`.
            discussion_num (`int`):
                The number of the Discussion or Pull Request . Must be a strictly positive integer.
            repo_type (`str`, *optional*):
                Set to `"dataset"` or `"space"` if uploading to a dataset or
                space, `None` or `"model"` if uploading to a model. Default is
                `None`.
            token (Union[bool, str, None], optional):
                A valid user access token (string). Defaults to the locally saved
                token, which is the recommended method for authentication (see
                https://huggingface.co/docs/huggingface_hub/quick-start#authentication).
                To disable authentication, pass `False`.

        Returns: [`DiscussionWithDetails`]

        <Tip>

        Raises the following errors:

            - [`HTTPError`](https://requests.readthedocs.io/en/latest/api/#requests.HTTPError)
              if the HuggingFace API returned an error
            - [`ValueError`](https://docs.python.org/3/library/exceptions.html#ValueError)
              if some parameter value is invalid
            - [`~utils.RepositoryNotFoundError`]
              If the repository to download from cannot be found. This may be because it doesn't exist,
              or because it is set to `private` and you do not have access.

        </Tip>
        """
        if not isinstance(discussion_num, int) or discussion_num <= 0:
            raise ValueError("Invalid discussion_num, must be a positive integer")
        if repo_type not in constants.REPO_TYPES:
            raise ValueError(f"Invalid repo type, must be one of {constants.REPO_TYPES}")
        if repo_type is None:
            repo_type = constants.REPO_TYPE_MODEL

        path = f"{self.endpoint}/api/{repo_type}s/{repo_id}/discussions/{discussion_num}"
        headers = self._build_hf_headers(token=token)
        resp = get_session().get(path, params={"diff": "1"}, headers=headers)
        hf_raise_for_status(resp)

        discussion_details = resp.json()
        is_pull_request = discussion_details["isPullRequest"]

        target_branch = discussion_details["changes"]["base"] if is_pull_request else None
        conflicting_files = discussion_details["filesWithConflicts"] if is_pull_request else None
        merge_commit_oid = discussion_details["changes"].get("mergeCommitId", None) if is_pull_request else None

        return DiscussionWithDetails(
            title=discussion_details["title"],
            num=discussion_details["num"],
            author=discussion_details.get("author", {}).get("name", "deleted"),
            created_at=parse_datetime(discussion_details["createdAt"]),
            status=discussion_details["status"],
            repo_id=discussion_details["repo"]["name"],
            repo_type=discussion_details["repo"]["type"],
            is_pull_request=discussion_details["isPullRequest"],
            events=[deserialize_event(evt) for evt in discussion_details["events"]],
            conflicting_files=conflicting_files,
            target_branch=target_branch,
            merge_commit_oid=merge_commit_oid,
            diff=discussion_details.get("diff"),
            endpoint=self.endpoint,
        )

    @validate_hf_hub_args
    def create_discussion(
        self,
        repo_id: str,
        title: str,
        *,
        token: Union[bool, str, None] = None,
        description: Optional[str] = None,
        repo_type: Optional[str] = None,
        pull_request: bool = False,
    ) -> DiscussionWithDetails:
        """Creates a Discussion or Pull Request.

        Pull Requests created programmatically will be in `"draft"` status.

        Creating a Pull Request with changes can also be done at once with [`HfApi.create_commit`].

        Args:
            repo_id (`str`):
                A namespace (user or an organization) and a repo name separated
                by a `/`.
            title (`str`):
                The title of the discussion. It can be up to 200 characters long,
                and must be at least 3 characters long. Leading and trailing whitespaces
                will be stripped.
            token (Union[bool, str, None], optional):
                A valid user access token (string). Defaults to the locally saved
                token, which is the recommended method for authentication (see
                https://huggingface.co/docs/huggingface_hub/quick-start#authentication).
                To disable authentication, pass `False`.
            description (`str`, *optional*):
                An optional description for the Pull Request.
                Defaults to `"Discussion opened with the huggingface_hub Python library"`
            pull_request (`bool`, *optional*):
                Whether to create a Pull Request or discussion. If `True`, creates a Pull Request.
                If `False`, creates a discussion. Defaults to `False`.
            repo_type (`str`, *optional*):
                Set to `"dataset"` or `"space"` if uploading to a dataset or
                space, `None` or `"model"` if uploading to a model. Default is
                `None`.

        Returns: [`DiscussionWithDetails`]

        <Tip>

        Raises the following errors:

            - [`HTTPError`](https://requests.readthedocs.io/en/latest/api/#requests.HTTPError)
              if the HuggingFace API returned an error
            - [`ValueError`](https://docs.python.org/3/library/exceptions.html#ValueError)
              if some parameter value is invalid
            - [`~utils.RepositoryNotFoundError`]
              If the repository to download from cannot be found. This may be because it doesn't exist,
              or because it is set to `private` and you do not have access.

        </Tip>"""
        if repo_type not in constants.REPO_TYPES:
            raise ValueError(f"Invalid repo type, must be one of {constants.REPO_TYPES}")
        if repo_type is None:
            repo_type = constants.REPO_TYPE_MODEL

        if description is not None:
            description = description.strip()
        description = (
            description
            if description
            else (
                f"{'Pull Request' if pull_request else 'Discussion'} opened with the"
                " [huggingface_hub Python"
                " library](https://huggingface.co/docs/huggingface_hub)"
            )
        )

        headers = self._build_hf_headers(token=token)
        resp = get_session().post(
            f"{self.endpoint}/api/{repo_type}s/{repo_id}/discussions",
            json={
                "title": title.strip(),
                "description": description,
                "pullRequest": pull_request,
            },
            headers=headers,
        )
        hf_raise_for_status(resp)
        num = resp.json()["num"]
        return self.get_discussion_details(
            repo_id=repo_id,
            repo_type=repo_type,
            discussion_num=num,
            token=token,
        )

    @validate_hf_hub_args
    def create_pull_request(
        self,
        repo_id: str,
        title: str,
        *,
        token: Union[bool, str, None] = None,
        description: Optional[str] = None,
        repo_type: Optional[str] = None,
    ) -> DiscussionWithDetails:
        """Creates a Pull Request . Pull Requests created programmatically will be in `"draft"` status.

        Creating a Pull Request with changes can also be done at once with [`HfApi.create_commit`];

        This is a wrapper around [`HfApi.create_discussion`].

        Args:
            repo_id (`str`):
                A namespace (user or an organization) and a repo name separated
                by a `/`.
            title (`str`):
                The title of the discussion. It can be up to 200 characters long,
                and must be at least 3 characters long. Leading and trailing whitespaces
                will be stripped.
            token (Union[bool, str, None], optional):
                A valid user access token (string). Defaults to the locally saved
                token, which is the recommended method for authentication (see
                https://huggingface.co/docs/huggingface_hub/quick-start#authentication).
                To disable authentication, pass `False`.
            description (`str`, *optional*):
                An optional description for the Pull Request.
                Defaults to `"Discussion opened with the huggingface_hub Python library"`
            repo_type (`str`, *optional*):
                Set to `"dataset"` or `"space"` if uploading to a dataset or
                space, `None` or `"model"` if uploading to a model. Default is
                `None`.

        Returns: [`DiscussionWithDetails`]

        <Tip>

        Raises the following errors:

            - [`HTTPError`](https://requests.readthedocs.io/en/latest/api/#requests.HTTPError)
              if the HuggingFace API returned an error
            - [`ValueError`](https://docs.python.org/3/library/exceptions.html#ValueError)
              if some parameter value is invalid
            - [`~utils.RepositoryNotFoundError`]
              If the repository to download from cannot be found. This may be because it doesn't exist,
              or because it is set to `private` and you do not have access.

        </Tip>"""
        return self.create_discussion(
            repo_id=repo_id,
            title=title,
            token=token,
            description=description,
            repo_type=repo_type,
            pull_request=True,
        )

    def _post_discussion_changes(
        self,
        *,
        repo_id: str,
        discussion_num: int,
        resource: str,
        body: Optional[dict] = None,
        token: Union[bool, str, None] = None,
        repo_type: Optional[str] = None,
    ) -> requests.Response:
        """Internal utility to POST changes to a Discussion or Pull Request"""
        if not isinstance(discussion_num, int) or discussion_num <= 0:
            raise ValueError("Invalid discussion_num, must be a positive integer")
        if repo_type not in constants.REPO_TYPES:
            raise ValueError(f"Invalid repo type, must be one of {constants.REPO_TYPES}")
        if repo_type is None:
            repo_type = constants.REPO_TYPE_MODEL
        repo_id = f"{repo_type}s/{repo_id}"

        path = f"{self.endpoint}/api/{repo_id}/discussions/{discussion_num}/{resource}"

        headers = self._build_hf_headers(token=token)
        resp = requests.post(path, headers=headers, json=body)
        hf_raise_for_status(resp)
        return resp

    @validate_hf_hub_args
    def comment_discussion(
        self,
        repo_id: str,
        discussion_num: int,
        comment: str,
        *,
        token: Union[bool, str, None] = None,
        repo_type: Optional[str] = None,
    ) -> DiscussionComment:
        """Creates a new comment on the given Discussion.

        Args:
            repo_id (`str`):
                A namespace (user or an organization) and a repo name separated
                by a `/`.
            discussion_num (`int`):
                The number of the Discussion or Pull Request . Must be a strictly positive integer.
            comment (`str`):
                The content of the comment to create. Comments support markdown formatting.
            repo_type (`str`, *optional*):
                Set to `"dataset"` or `"space"` if uploading to a dataset or
                space, `None` or `"model"` if uploading to a model. Default is
                `None`.
            token (Union[bool, str, None], optional):
                A valid user access token (string). Defaults to the locally saved
                token, which is the recommended method for authentication (see
                https://huggingface.co/docs/huggingface_hub/quick-start#authentication).
                To disable authentication, pass `False`.

        Returns:
            [`DiscussionComment`]: the newly created comment


        Examples:
            ```python

            >>> comment = \"\"\"
            ... Hello @otheruser!
            ...
            ... # This is a title
            ...
            ... **This is bold**, *this is italic* and ~this is strikethrough~
            ... And [this](http://url) is a link
            ... \"\"\"

            >>> HfApi().comment_discussion(
            ...     repo_id="username/repo_name",
            ...     discussion_num=34
            ...     comment=comment
            ... )
            # DiscussionComment(id='deadbeef0000000', type='comment', ...)

            ```

        <Tip>

        Raises the following errors:

            - [`HTTPError`](https://requests.readthedocs.io/en/latest/api/#requests.HTTPError)
              if the HuggingFace API returned an error
            - [`ValueError`](https://docs.python.org/3/library/exceptions.html#ValueError)
              if some parameter value is invalid
            - [`~utils.RepositoryNotFoundError`]
              If the repository to download from cannot be found. This may be because it doesn't exist,
              or because it is set to `private` and you do not have access.

        </Tip>
        """
        resp = self._post_discussion_changes(
            repo_id=repo_id,
            repo_type=repo_type,
            discussion_num=discussion_num,
            token=token,
            resource="comment",
            body={"comment": comment},
        )
        return deserialize_event(resp.json()["newMessage"])  # type: ignore

    @validate_hf_hub_args
    def rename_discussion(
        self,
        repo_id: str,
        discussion_num: int,
        new_title: str,
        *,
        token: Union[bool, str, None] = None,
        repo_type: Optional[str] = None,
    ) -> DiscussionTitleChange:
        """Renames a Discussion.

        Args:
            repo_id (`str`):
                A namespace (user or an organization) and a repo name separated
                by a `/`.
            discussion_num (`int`):
                The number of the Discussion or Pull Request . Must be a strictly positive integer.
            new_title (`str`):
                The new title for the discussion
            repo_type (`str`, *optional*):
                Set to `"dataset"` or `"space"` if uploading to a dataset or
                space, `None` or `"model"` if uploading to a model. Default is
                `None`.
            token (Union[bool, str, None], optional):
                A valid user access token (string). Defaults to the locally saved
                token, which is the recommended method for authentication (see
                https://huggingface.co/docs/huggingface_hub/quick-start#authentication).
                To disable authentication, pass `False`.

        Returns:
            [`DiscussionTitleChange`]: the title change event


        Examples:
            ```python
            >>> new_title = "New title, fixing a typo"
            >>> HfApi().rename_discussion(
            ...     repo_id="username/repo_name",
            ...     discussion_num=34
            ...     new_title=new_title
            ... )
            # DiscussionTitleChange(id='deadbeef0000000', type='title-change', ...)

            ```

        <Tip>

        Raises the following errors:

            - [`HTTPError`](https://requests.readthedocs.io/en/latest/api/#requests.HTTPError)
              if the HuggingFace API returned an error
            - [`ValueError`](https://docs.python.org/3/library/exceptions.html#ValueError)
              if some parameter value is invalid
            - [`~utils.RepositoryNotFoundError`]
              If the repository to download from cannot be found. This may be because it doesn't exist,
              or because it is set to `private` and you do not have access.

        </Tip>
        """
        resp = self._post_discussion_changes(
            repo_id=repo_id,
            repo_type=repo_type,
            discussion_num=discussion_num,
            token=token,
            resource="title",
            body={"title": new_title},
        )
        return deserialize_event(resp.json()["newTitle"])  # type: ignore

    @validate_hf_hub_args
    def change_discussion_status(
        self,
        repo_id: str,
        discussion_num: int,
        new_status: Literal["open", "closed"],
        *,
        token: Union[bool, str, None] = None,
        comment: Optional[str] = None,
        repo_type: Optional[str] = None,
    ) -> DiscussionStatusChange:
        """Closes or re-opens a Discussion or Pull Request.

        Args:
            repo_id (`str`):
                A namespace (user or an organization) and a repo name separated
                by a `/`.
            discussion_num (`int`):
                The number of the Discussion or Pull Request . Must be a strictly positive integer.
            new_status (`str`):
                The new status for the discussion, either `"open"` or `"closed"`.
            comment (`str`, *optional*):
                An optional comment to post with the status change.
            repo_type (`str`, *optional*):
                Set to `"dataset"` or `"space"` if uploading to a dataset or
                space, `None` or `"model"` if uploading to a model. Default is
                `None`.
            token (Union[bool, str, None], optional):
                A valid user access token (string). Defaults to the locally saved
                token, which is the recommended method for authentication (see
                https://huggingface.co/docs/huggingface_hub/quick-start#authentication).
                To disable authentication, pass `False`.

        Returns:
            [`DiscussionStatusChange`]: the status change event


        Examples:
            ```python
            >>> new_title = "New title, fixing a typo"
            >>> HfApi().rename_discussion(
            ...     repo_id="username/repo_name",
            ...     discussion_num=34
            ...     new_title=new_title
            ... )
            # DiscussionStatusChange(id='deadbeef0000000', type='status-change', ...)

            ```

        <Tip>

        Raises the following errors:

            - [`HTTPError`](https://requests.readthedocs.io/en/latest/api/#requests.HTTPError)
              if the HuggingFace API returned an error
            - [`ValueError`](https://docs.python.org/3/library/exceptions.html#ValueError)
              if some parameter value is invalid
            - [`~utils.RepositoryNotFoundError`]
              If the repository to download from cannot be found. This may be because it doesn't exist,
              or because it is set to `private` and you do not have access.

        </Tip>
        """
        if new_status not in ["open", "closed"]:
            raise ValueError("Invalid status, valid statuses are: 'open' and 'closed'")
        body: Dict[str, str] = {"status": new_status}
        if comment and comment.strip():
            body["comment"] = comment.strip()
        resp = self._post_discussion_changes(
            repo_id=repo_id,
            repo_type=repo_type,
            discussion_num=discussion_num,
            token=token,
            resource="status",
            body=body,
        )
        return deserialize_event(resp.json()["newStatus"])  # type: ignore

    @validate_hf_hub_args
    def merge_pull_request(
        self,
        repo_id: str,
        discussion_num: int,
        *,
        token: Union[bool, str, None] = None,
        comment: Optional[str] = None,
        repo_type: Optional[str] = None,
    ):
        """Merges a Pull Request.

        Args:
            repo_id (`str`):
                A namespace (user or an organization) and a repo name separated
                by a `/`.
            discussion_num (`int`):
                The number of the Discussion or Pull Request . Must be a strictly positive integer.
            comment (`str`, *optional*):
                An optional comment to post with the status change.
            repo_type (`str`, *optional*):
                Set to `"dataset"` or `"space"` if uploading to a dataset or
                space, `None` or `"model"` if uploading to a model. Default is
                `None`.
            token (Union[bool, str, None], optional):
                A valid user access token (string). Defaults to the locally saved
                token, which is the recommended method for authentication (see
                https://huggingface.co/docs/huggingface_hub/quick-start#authentication).
                To disable authentication, pass `False`.

        Returns:
            [`DiscussionStatusChange`]: the status change event

        <Tip>

        Raises the following errors:

            - [`HTTPError`](https://requests.readthedocs.io/en/latest/api/#requests.HTTPError)
              if the HuggingFace API returned an error
            - [`ValueError`](https://docs.python.org/3/library/exceptions.html#ValueError)
              if some parameter value is invalid
            - [`~utils.RepositoryNotFoundError`]
              If the repository to download from cannot be found. This may be because it doesn't exist,
              or because it is set to `private` and you do not have access.

        </Tip>
        """
        self._post_discussion_changes(
            repo_id=repo_id,
            repo_type=repo_type,
            discussion_num=discussion_num,
            token=token,
            resource="merge",
            body={"comment": comment.strip()} if comment and comment.strip() else None,
        )

    @validate_hf_hub_args
    def edit_discussion_comment(
        self,
        repo_id: str,
        discussion_num: int,
        comment_id: str,
        new_content: str,
        *,
        token: Union[bool, str, None] = None,
        repo_type: Optional[str] = None,
    ) -> DiscussionComment:
        """Edits a comment on a Discussion / Pull Request.

        Args:
            repo_id (`str`):
                A namespace (user or an organization) and a repo name separated
                by a `/`.
            discussion_num (`int`):
                The number of the Discussion or Pull Request . Must be a strictly positive integer.
            comment_id (`str`):
                The ID of the comment to edit.
            new_content (`str`):
                The new content of the comment. Comments support markdown formatting.
            repo_type (`str`, *optional*):
                Set to `"dataset"` or `"space"` if uploading to a dataset or
                space, `None` or `"model"` if uploading to a model. Default is
                `None`.
            token (Union[bool, str, None], optional):
                A valid user access token (string). Defaults to the locally saved
                token, which is the recommended method for authentication (see
                https://huggingface.co/docs/huggingface_hub/quick-start#authentication).
                To disable authentication, pass `False`.

        Returns:
            [`DiscussionComment`]: the edited comment

        <Tip>

        Raises the following errors:

            - [`HTTPError`](https://requests.readthedocs.io/en/latest/api/#requests.HTTPError)
              if the HuggingFace API returned an error
            - [`ValueError`](https://docs.python.org/3/library/exceptions.html#ValueError)
              if some parameter value is invalid
            - [`~utils.RepositoryNotFoundError`]
              If the repository to download from cannot be found. This may be because it doesn't exist,
              or because it is set to `private` and you do not have access.

        </Tip>
        """
        resp = self._post_discussion_changes(
            repo_id=repo_id,
            repo_type=repo_type,
            discussion_num=discussion_num,
            token=token,
            resource=f"comment/{comment_id.lower()}/edit",
            body={"content": new_content},
        )
        return deserialize_event(resp.json()["updatedComment"])  # type: ignore

    @validate_hf_hub_args
    def hide_discussion_comment(
        self,
        repo_id: str,
        discussion_num: int,
        comment_id: str,
        *,
        token: Union[bool, str, None] = None,
        repo_type: Optional[str] = None,
    ) -> DiscussionComment:
        """Hides a comment on a Discussion / Pull Request.

        <Tip warning={true}>
        Hidden comments' content cannot be retrieved anymore. Hiding a comment is irreversible.
        </Tip>

        Args:
            repo_id (`str`):
                A namespace (user or an organization) and a repo name separated
                by a `/`.
            discussion_num (`int`):
                The number of the Discussion or Pull Request . Must be a strictly positive integer.
            comment_id (`str`):
                The ID of the comment to edit.
            repo_type (`str`, *optional*):
                Set to `"dataset"` or `"space"` if uploading to a dataset or
                space, `None` or `"model"` if uploading to a model. Default is
                `None`.
            token (Union[bool, str, None], optional):
                A valid user access token (string). Defaults to the locally saved
                token, which is the recommended method for authentication (see
                https://huggingface.co/docs/huggingface_hub/quick-start#authentication).
                To disable authentication, pass `False`.

        Returns:
            [`DiscussionComment`]: the hidden comment

        <Tip>

        Raises the following errors:

            - [`HTTPError`](https://requests.readthedocs.io/en/latest/api/#requests.HTTPError)
              if the HuggingFace API returned an error
            - [`ValueError`](https://docs.python.org/3/library/exceptions.html#ValueError)
              if some parameter value is invalid
            - [`~utils.RepositoryNotFoundError`]
              If the repository to download from cannot be found. This may be because it doesn't exist,
              or because it is set to `private` and you do not have access.

        </Tip>
        """
        warnings.warn(
            "Hidden comments' content cannot be retrieved anymore. Hiding a comment is irreversible.",
            UserWarning,
        )
        resp = self._post_discussion_changes(
            repo_id=repo_id,
            repo_type=repo_type,
            discussion_num=discussion_num,
            token=token,
            resource=f"comment/{comment_id.lower()}/hide",
        )
        return deserialize_event(resp.json()["updatedComment"])  # type: ignore

    @validate_hf_hub_args
    def add_space_secret(
        self,
        repo_id: str,
        key: str,
        value: str,
        *,
        description: Optional[str] = None,
        token: Union[bool, str, None] = None,
    ) -> None:
        """Adds or updates a secret in a Space.

        Secrets allow to set secret keys or tokens to a Space without hardcoding them.
        For more details, see https://huggingface.co/docs/hub/spaces-overview#managing-secrets.

        Args:
            repo_id (`str`):
                ID of the repo to update. Example: `"bigcode/in-the-stack"`.
            key (`str`):
                Secret key. Example: `"GITHUB_API_KEY"`
            value (`str`):
                Secret value. Example: `"your_github_api_key"`.
            description (`str`, *optional*):
                Secret description. Example: `"Github API key to access the Github API"`.
            token (Union[bool, str, None], optional):
                A valid user access token (string). Defaults to the locally saved
                token, which is the recommended method for authentication (see
                https://huggingface.co/docs/huggingface_hub/quick-start#authentication).
                To disable authentication, pass `False`.
        """
        payload = {"key": key, "value": value}
        if description is not None:
            payload["description"] = description
        r = get_session().post(
            f"{self.endpoint}/api/spaces/{repo_id}/secrets",
            headers=self._build_hf_headers(token=token),
            json=payload,
        )
        hf_raise_for_status(r)

    @validate_hf_hub_args
    def delete_space_secret(self, repo_id: str, key: str, *, token: Union[bool, str, None] = None) -> None:
        """Deletes a secret from a Space.

        Secrets allow to set secret keys or tokens to a Space without hardcoding them.
        For more details, see https://huggingface.co/docs/hub/spaces-overview#managing-secrets.

        Args:
            repo_id (`str`):
                ID of the repo to update. Example: `"bigcode/in-the-stack"`.
            key (`str`):
                Secret key. Example: `"GITHUB_API_KEY"`.
            token (Union[bool, str, None], optional):
                A valid user access token (string). Defaults to the locally saved
                token, which is the recommended method for authentication (see
                https://huggingface.co/docs/huggingface_hub/quick-start#authentication).
                To disable authentication, pass `False`.
        """
        r = get_session().delete(
            f"{self.endpoint}/api/spaces/{repo_id}/secrets",
            headers=self._build_hf_headers(token=token),
            json={"key": key},
        )
        hf_raise_for_status(r)

    @validate_hf_hub_args
    def get_space_variables(self, repo_id: str, *, token: Union[bool, str, None] = None) -> Dict[str, SpaceVariable]:
        """Gets all variables from a Space.

        Variables allow to set environment variables to a Space without hardcoding them.
        For more details, see https://huggingface.co/docs/hub/spaces-overview#managing-secrets-and-environment-variables

        Args:
            repo_id (`str`):
                ID of the repo to query. Example: `"bigcode/in-the-stack"`.
            token (Union[bool, str, None], optional):
                A valid user access token (string). Defaults to the locally saved
                token, which is the recommended method for authentication (see
                https://huggingface.co/docs/huggingface_hub/quick-start#authentication).
                To disable authentication, pass `False`.
        """
        r = get_session().get(
            f"{self.endpoint}/api/spaces/{repo_id}/variables",
            headers=self._build_hf_headers(token=token),
        )
        hf_raise_for_status(r)
        return {k: SpaceVariable(k, v) for k, v in r.json().items()}

    @validate_hf_hub_args
    def add_space_variable(
        self,
        repo_id: str,
        key: str,
        value: str,
        *,
        description: Optional[str] = None,
        token: Union[bool, str, None] = None,
    ) -> Dict[str, SpaceVariable]:
        """Adds or updates a variable in a Space.

        Variables allow to set environment variables to a Space without hardcoding them.
        For more details, see https://huggingface.co/docs/hub/spaces-overview#managing-secrets-and-environment-variables

        Args:
            repo_id (`str`):
                ID of the repo to update. Example: `"bigcode/in-the-stack"`.
            key (`str`):
                Variable key. Example: `"MODEL_REPO_ID"`
            value (`str`):
                Variable value. Example: `"the_model_repo_id"`.
            description (`str`):
                Description of the variable. Example: `"Model Repo ID of the implemented model"`.
            token (Union[bool, str, None], optional):
                A valid user access token (string). Defaults to the locally saved
                token, which is the recommended method for authentication (see
                https://huggingface.co/docs/huggingface_hub/quick-start#authentication).
                To disable authentication, pass `False`.
        """
        payload = {"key": key, "value": value}
        if description is not None:
            payload["description"] = description
        r = get_session().post(
            f"{self.endpoint}/api/spaces/{repo_id}/variables",
            headers=self._build_hf_headers(token=token),
            json=payload,
        )
        hf_raise_for_status(r)
        return {k: SpaceVariable(k, v) for k, v in r.json().items()}

    @validate_hf_hub_args
    def delete_space_variable(
        self, repo_id: str, key: str, *, token: Union[bool, str, None] = None
    ) -> Dict[str, SpaceVariable]:
        """Deletes a variable from a Space.

        Variables allow to set environment variables to a Space without hardcoding them.
        For more details, see https://huggingface.co/docs/hub/spaces-overview#managing-secrets-and-environment-variables

        Args:
            repo_id (`str`):
                ID of the repo to update. Example: `"bigcode/in-the-stack"`.
            key (`str`):
                Variable key. Example: `"MODEL_REPO_ID"`
            token (Union[bool, str, None], optional):
                A valid user access token (string). Defaults to the locally saved
                token, which is the recommended method for authentication (see
                https://huggingface.co/docs/huggingface_hub/quick-start#authentication).
                To disable authentication, pass `False`.
        """
        r = get_session().delete(
            f"{self.endpoint}/api/spaces/{repo_id}/variables",
            headers=self._build_hf_headers(token=token),
            json={"key": key},
        )
        hf_raise_for_status(r)
        return {k: SpaceVariable(k, v) for k, v in r.json().items()}

    @validate_hf_hub_args
    def get_space_runtime(self, repo_id: str, *, token: Union[bool, str, None] = None) -> SpaceRuntime:
        """Gets runtime information about a Space.

        Args:
            repo_id (`str`):
                ID of the repo to update. Example: `"bigcode/in-the-stack"`.
            token (Union[bool, str, None], optional):
                A valid user access token (string). Defaults to the locally saved
                token, which is the recommended method for authentication (see
                https://huggingface.co/docs/huggingface_hub/quick-start#authentication).
                To disable authentication, pass `False`.
        Returns:
            [`SpaceRuntime`]: Runtime information about a Space including Space stage and hardware.
        """
        r = get_session().get(
            f"{self.endpoint}/api/spaces/{repo_id}/runtime", headers=self._build_hf_headers(token=token)
        )
        hf_raise_for_status(r)
        return SpaceRuntime(r.json())

    @validate_hf_hub_args
    def request_space_hardware(
        self,
        repo_id: str,
        hardware: SpaceHardware,
        *,
        token: Union[bool, str, None] = None,
        sleep_time: Optional[int] = None,
    ) -> SpaceRuntime:
        """Request new hardware for a Space.

        Args:
            repo_id (`str`):
                ID of the repo to update. Example: `"bigcode/in-the-stack"`.
            hardware (`str` or [`SpaceHardware`]):
                Hardware on which to run the Space. Example: `"t4-medium"`.
            token (Union[bool, str, None], optional):
                A valid user access token (string). Defaults to the locally saved
                token, which is the recommended method for authentication (see
                https://huggingface.co/docs/huggingface_hub/quick-start#authentication).
                To disable authentication, pass `False`.
            sleep_time (`int`, *optional*):
                Number of seconds of inactivity to wait before a Space is put to sleep. Set to `-1` if you don't want
                your Space to sleep (default behavior for upgraded hardware). For free hardware, you can't configure
                the sleep time (value is fixed to 48 hours of inactivity).
                See https://huggingface.co/docs/hub/spaces-gpus#sleep-time for more details.
        Returns:
            [`SpaceRuntime`]: Runtime information about a Space including Space stage and hardware.

        <Tip>

        It is also possible to request hardware directly when creating the Space repo! See [`create_repo`] for details.

        </Tip>
        """
        if sleep_time is not None and hardware == SpaceHardware.CPU_BASIC:
            warnings.warn(
                "If your Space runs on the default 'cpu-basic' hardware, it will go to sleep if inactive for more"
                " than 48 hours. This value is not configurable. If you don't want your Space to deactivate or if"
                " you want to set a custom sleep time, you need to upgrade to a paid Hardware.",
                UserWarning,
            )
        payload: Dict[str, Any] = {"flavor": hardware}
        if sleep_time is not None:
            payload["sleepTimeSeconds"] = sleep_time
        r = get_session().post(
            f"{self.endpoint}/api/spaces/{repo_id}/hardware",
            headers=self._build_hf_headers(token=token),
            json=payload,
        )
        hf_raise_for_status(r)
        return SpaceRuntime(r.json())

    @validate_hf_hub_args
    def set_space_sleep_time(
        self, repo_id: str, sleep_time: int, *, token: Union[bool, str, None] = None
    ) -> SpaceRuntime:
        """Set a custom sleep time for a Space running on upgraded hardware..

        Your Space will go to sleep after X seconds of inactivity. You are not billed when your Space is in "sleep"
        mode. If a new visitor lands on your Space, it will "wake it up". Only upgraded hardware can have a
        configurable sleep time. To know more about the sleep stage, please refer to
        https://huggingface.co/docs/hub/spaces-gpus#sleep-time.

        Args:
            repo_id (`str`):
                ID of the repo to update. Example: `"bigcode/in-the-stack"`.
            sleep_time (`int`, *optional*):
                Number of seconds of inactivity to wait before a Space is put to sleep. Set to `-1` if you don't want
                your Space to pause (default behavior for upgraded hardware). For free hardware, you can't configure
                the sleep time (value is fixed to 48 hours of inactivity).
                See https://huggingface.co/docs/hub/spaces-gpus#sleep-time for more details.
            token (Union[bool, str, None], optional):
                A valid user access token (string). Defaults to the locally saved
                token, which is the recommended method for authentication (see
                https://huggingface.co/docs/huggingface_hub/quick-start#authentication).
                To disable authentication, pass `False`.
        Returns:
            [`SpaceRuntime`]: Runtime information about a Space including Space stage and hardware.

        <Tip>

        It is also possible to set a custom sleep time when requesting hardware with [`request_space_hardware`].

        </Tip>
        """
        r = get_session().post(
            f"{self.endpoint}/api/spaces/{repo_id}/sleeptime",
            headers=self._build_hf_headers(token=token),
            json={"seconds": sleep_time},
        )
        hf_raise_for_status(r)
        runtime = SpaceRuntime(r.json())

        hardware = runtime.requested_hardware or runtime.hardware
        if hardware == SpaceHardware.CPU_BASIC:
            warnings.warn(
                "If your Space runs on the default 'cpu-basic' hardware, it will go to sleep if inactive for more"
                " than 48 hours. This value is not configurable. If you don't want your Space to deactivate or if"
                " you want to set a custom sleep time, you need to upgrade to a paid Hardware.",
                UserWarning,
            )
        return runtime

    @validate_hf_hub_args
    def pause_space(self, repo_id: str, *, token: Union[bool, str, None] = None) -> SpaceRuntime:
        """Pause your Space.

        A paused Space stops executing until manually restarted by its owner. This is different from the sleeping
        state in which free Spaces go after 48h of inactivity. Paused time is not billed to your account, no matter the
        hardware you've selected. To restart your Space, use [`restart_space`] and go to your Space settings page.

        For more details, please visit [the docs](https://huggingface.co/docs/hub/spaces-gpus#pause).

        Args:
            repo_id (`str`):
                ID of the Space to pause. Example: `"Salesforce/BLIP2"`.
            token (Union[bool, str, None], optional):
                A valid user access token (string). Defaults to the locally saved
                token, which is the recommended method for authentication (see
                https://huggingface.co/docs/huggingface_hub/quick-start#authentication).
                To disable authentication, pass `False`.

        Returns:
            [`SpaceRuntime`]: Runtime information about your Space including `stage=PAUSED` and requested hardware.

        Raises:
            [`~utils.RepositoryNotFoundError`]:
                If your Space is not found (error 404). Most probably wrong repo_id or your space is private but you
                are not authenticated.
            [`~utils.HfHubHTTPError`]:
                403 Forbidden: only the owner of a Space can pause it. If you want to manage a Space that you don't
                own, either ask the owner by opening a Discussion or duplicate the Space.
            [`~utils.BadRequestError`]:
                If your Space is a static Space. Static Spaces are always running and never billed. If you want to hide
                a static Space, you can set it to private.
        """
        r = get_session().post(
            f"{self.endpoint}/api/spaces/{repo_id}/pause", headers=self._build_hf_headers(token=token)
        )
        hf_raise_for_status(r)
        return SpaceRuntime(r.json())

    @validate_hf_hub_args
    def restart_space(
        self, repo_id: str, *, token: Union[bool, str, None] = None, factory_reboot: bool = False
    ) -> SpaceRuntime:
        """Restart your Space.

        This is the only way to programmatically restart a Space if you've put it on Pause (see [`pause_space`]). You
        must be the owner of the Space to restart it. If you are using an upgraded hardware, your account will be
        billed as soon as the Space is restarted. You can trigger a restart no matter the current state of a Space.

        For more details, please visit [the docs](https://huggingface.co/docs/hub/spaces-gpus#pause).

        Args:
            repo_id (`str`):
                ID of the Space to restart. Example: `"Salesforce/BLIP2"`.
            token (Union[bool, str, None], optional):
                A valid user access token (string). Defaults to the locally saved
                token, which is the recommended method for authentication (see
                https://huggingface.co/docs/huggingface_hub/quick-start#authentication).
                To disable authentication, pass `False`.
            factory_reboot (`bool`, *optional*):
                If `True`, the Space will be rebuilt from scratch without caching any requirements.

        Returns:
            [`SpaceRuntime`]: Runtime information about your Space.

        Raises:
            [`~utils.RepositoryNotFoundError`]:
                If your Space is not found (error 404). Most probably wrong repo_id or your space is private but you
                are not authenticated.
            [`~utils.HfHubHTTPError`]:
                403 Forbidden: only the owner of a Space can restart it. If you want to restart a Space that you don't
                own, either ask the owner by opening a Discussion or duplicate the Space.
            [`~utils.BadRequestError`]:
                If your Space is a static Space. Static Spaces are always running and never billed. If you want to hide
                a static Space, you can set it to private.
        """
        params = {}
        if factory_reboot:
            params["factory"] = "true"
        r = get_session().post(
            f"{self.endpoint}/api/spaces/{repo_id}/restart", headers=self._build_hf_headers(token=token), params=params
        )
        hf_raise_for_status(r)
        return SpaceRuntime(r.json())

    @validate_hf_hub_args
    def duplicate_space(
        self,
        from_id: str,
        to_id: Optional[str] = None,
        *,
        private: Optional[bool] = None,
        token: Union[bool, str, None] = None,
        exist_ok: bool = False,
        hardware: Optional[SpaceHardware] = None,
        storage: Optional[SpaceStorage] = None,
        sleep_time: Optional[int] = None,
        secrets: Optional[List[Dict[str, str]]] = None,
        variables: Optional[List[Dict[str, str]]] = None,
    ) -> RepoUrl:
        """Duplicate a Space.

        Programmatically duplicate a Space. The new Space will be created in your account and will be in the same state
        as the original Space (running or paused). You can duplicate a Space no matter the current state of a Space.

        Args:
            from_id (`str`):
                ID of the Space to duplicate. Example: `"pharma/CLIP-Interrogator"`.
            to_id (`str`, *optional*):
                ID of the new Space. Example: `"dog/CLIP-Interrogator"`. If not provided, the new Space will have the same
                name as the original Space, but in your account.
            private (`bool`, *optional*):
                Whether the new Space should be private or not. Defaults to the same privacy as the original Space.
            token (Union[bool, str, None], optional):
                A valid user access token (string). Defaults to the locally saved
                token, which is the recommended method for authentication (see
                https://huggingface.co/docs/huggingface_hub/quick-start#authentication).
                To disable authentication, pass `False`.
            exist_ok (`bool`, *optional*, defaults to `False`):
                If `True`, do not raise an error if repo already exists.
            hardware (`SpaceHardware` or `str`, *optional*):
                Choice of Hardware. Example: `"t4-medium"`. See [`SpaceHardware`] for a complete list.
            storage (`SpaceStorage` or `str`, *optional*):
                Choice of persistent storage tier. Example: `"small"`. See [`SpaceStorage`] for a complete list.
            sleep_time (`int`, *optional*):
                Number of seconds of inactivity to wait before a Space is put to sleep. Set to `-1` if you don't want
                your Space to sleep (default behavior for upgraded hardware). For free hardware, you can't configure
                the sleep time (value is fixed to 48 hours of inactivity).
                See https://huggingface.co/docs/hub/spaces-gpus#sleep-time for more details.
            secrets (`List[Dict[str, str]]`, *optional*):
                A list of secret keys to set in your Space. Each item is in the form `{"key": ..., "value": ..., "description": ...}` where description is optional.
                For more details, see https://huggingface.co/docs/hub/spaces-overview#managing-secrets.
            variables (`List[Dict[str, str]]`, *optional*):
                A list of public environment variables to set in your Space. Each item is in the form `{"key": ..., "value": ..., "description": ...}` where description is optional.
                For more details, see https://huggingface.co/docs/hub/spaces-overview#managing-secrets-and-environment-variables.

        Returns:
            [`RepoUrl`]: URL to the newly created repo. Value is a subclass of `str` containing
            attributes like `endpoint`, `repo_type` and `repo_id`.

        Raises:
            [`~utils.RepositoryNotFoundError`]:
              If one of `from_id` or `to_id` cannot be found. This may be because it doesn't exist,
              or because it is set to `private` and you do not have access.
            [`HTTPError`](https://requests.readthedocs.io/en/latest/api/#requests.HTTPError):
              If the HuggingFace API returned an error

        Example:
        ```python
        >>> from huggingface_hub import duplicate_space

        # Duplicate a Space to your account
        >>> duplicate_space("multimodalart/dreambooth-training")
        RepoUrl('https://huggingface.co/spaces/nateraw/dreambooth-training',...)

        # Can set custom destination id and visibility flag.
        >>> duplicate_space("multimodalart/dreambooth-training", to_id="my-dreambooth", private=True)
        RepoUrl('https://huggingface.co/spaces/nateraw/my-dreambooth',...)
        ```
        """
        # Parse to_id if provided
        parsed_to_id = RepoUrl(to_id) if to_id is not None else None

        # Infer target repo_id
        to_namespace = (  # set namespace manually or default to username
            parsed_to_id.namespace
            if parsed_to_id is not None and parsed_to_id.namespace is not None
            else self.whoami(token)["name"]
        )
        to_repo_name = parsed_to_id.repo_name if to_id is not None else RepoUrl(from_id).repo_name  # type: ignore

        # repository must be a valid repo_id (namespace/repo_name).
        payload: Dict[str, Any] = {"repository": f"{to_namespace}/{to_repo_name}"}

        keys = ["private", "hardware", "storageTier", "sleepTimeSeconds", "secrets", "variables"]
        values = [private, hardware, storage, sleep_time, secrets, variables]
        payload.update({k: v for k, v in zip(keys, values) if v is not None})

        if sleep_time is not None and hardware == SpaceHardware.CPU_BASIC:
            warnings.warn(
                "If your Space runs on the default 'cpu-basic' hardware, it will go to sleep if inactive for more"
                " than 48 hours. This value is not configurable. If you don't want your Space to deactivate or if"
                " you want to set a custom sleep time, you need to upgrade to a paid Hardware.",
                UserWarning,
            )

        r = get_session().post(
            f"{self.endpoint}/api/spaces/{from_id}/duplicate",
            headers=self._build_hf_headers(token=token),
            json=payload,
        )

        try:
            hf_raise_for_status(r)
        except HTTPError as err:
            if exist_ok and err.response.status_code == 409:
                # Repo already exists and `exist_ok=True`
                pass
            else:
                raise

        return RepoUrl(r.json()["url"], endpoint=self.endpoint)

    @validate_hf_hub_args
    def request_space_storage(
        self,
        repo_id: str,
        storage: SpaceStorage,
        *,
        token: Union[bool, str, None] = None,
    ) -> SpaceRuntime:
        """Request persistent storage for a Space.

        Args:
            repo_id (`str`):
                ID of the Space to update. Example: `"open-llm-leaderboard/open_llm_leaderboard"`.
            storage (`str` or [`SpaceStorage`]):
               Storage tier. Either 'small', 'medium', or 'large'.
            token (Union[bool, str, None], optional):
                A valid user access token (string). Defaults to the locally saved
                token, which is the recommended method for authentication (see
                https://huggingface.co/docs/huggingface_hub/quick-start#authentication).
                To disable authentication, pass `False`.
        Returns:
            [`SpaceRuntime`]: Runtime information about a Space including Space stage and hardware.

        <Tip>

        It is not possible to decrease persistent storage after its granted. To do so, you must delete it
        via [`delete_space_storage`].

        </Tip>
        """
        payload: Dict[str, SpaceStorage] = {"tier": storage}
        r = get_session().post(
            f"{self.endpoint}/api/spaces/{repo_id}/storage",
            headers=self._build_hf_headers(token=token),
            json=payload,
        )
        hf_raise_for_status(r)
        return SpaceRuntime(r.json())

    @validate_hf_hub_args
    def delete_space_storage(
        self,
        repo_id: str,
        *,
        token: Union[bool, str, None] = None,
    ) -> SpaceRuntime:
        """Delete persistent storage for a Space.

        Args:
            repo_id (`str`):
                ID of the Space to update. Example: `"open-llm-leaderboard/open_llm_leaderboard"`.
            token (Union[bool, str, None], optional):
                A valid user access token (string). Defaults to the locally saved
                token, which is the recommended method for authentication (see
                https://huggingface.co/docs/huggingface_hub/quick-start#authentication).
                To disable authentication, pass `False`.
        Returns:
            [`SpaceRuntime`]: Runtime information about a Space including Space stage and hardware.
        Raises:
            [`BadRequestError`]
                If space has no persistent storage.

        """
        r = get_session().delete(
            f"{self.endpoint}/api/spaces/{repo_id}/storage",
            headers=self._build_hf_headers(token=token),
        )
        hf_raise_for_status(r)
        return SpaceRuntime(r.json())

    #######################
    # Inference Endpoints #
    #######################

    def list_inference_endpoints(
        self, namespace: Optional[str] = None, *, token: Union[bool, str, None] = None
    ) -> List[InferenceEndpoint]:
        """Lists all inference endpoints for the given namespace.

        Args:
            namespace (`str`, *optional*):
                The namespace to list endpoints for. Defaults to the current user. Set to `"*"` to list all endpoints
                from all namespaces (i.e. personal namespace and all orgs the user belongs to).
            token (Union[bool, str, None], optional):
                A valid user access token (string). Defaults to the locally saved
                token, which is the recommended method for authentication (see
                https://huggingface.co/docs/huggingface_hub/quick-start#authentication).
                To disable authentication, pass `False`.

        Returns:
            List[`InferenceEndpoint`]: A list of all inference endpoints for the given namespace.

        Example:
        ```python
        >>> from huggingface_hub import HfApi
        >>> api = HfApi()
        >>> api.list_inference_endpoints()
        [InferenceEndpoint(name='my-endpoint', ...), ...]
        ```
        """
        # Special case: list all endpoints for all namespaces the user has access to
        if namespace == "*":
            user = self.whoami(token=token)

            # List personal endpoints first
            endpoints: List[InferenceEndpoint] = list_inference_endpoints(namespace=self._get_namespace(token=token))

            # Then list endpoints for all orgs the user belongs to and ignore 401 errors (no billing or no access)
            for org in user.get("orgs", []):
                try:
                    endpoints += list_inference_endpoints(namespace=org["name"], token=token)
                except HfHubHTTPError as error:
                    if error.response.status_code == 401:  # Either no billing or user don't have access)
                        logger.debug("Cannot list Inference Endpoints for org '%s': %s", org["name"], error)
                    pass

            return endpoints

        # Normal case: list endpoints for a specific namespace
        namespace = namespace or self._get_namespace(token=token)

        response = get_session().get(
            f"{constants.INFERENCE_ENDPOINTS_ENDPOINT}/endpoint/{namespace}",
            headers=self._build_hf_headers(token=token),
        )
        hf_raise_for_status(response)

        return [
            InferenceEndpoint.from_raw(endpoint, namespace=namespace, token=token)
            for endpoint in response.json()["items"]
        ]

    def create_inference_endpoint(
        self,
        name: str,
        *,
        repository: str,
        framework: str,
        accelerator: str,
        instance_size: str,
        instance_type: str,
        region: str,
        vendor: str,
        account_id: Optional[str] = None,
        min_replica: int = 1,
        max_replica: int = 1,
        scale_to_zero_timeout: Optional[int] = None,
        revision: Optional[str] = None,
        task: Optional[str] = None,
        custom_image: Optional[Dict] = None,
        env: Optional[Dict[str, str]] = None,
        secrets: Optional[Dict[str, str]] = None,
        type: InferenceEndpointType = InferenceEndpointType.PROTECTED,
        domain: Optional[str] = None,
        path: Optional[str] = None,
        cache_http_responses: Optional[bool] = None,
        tags: Optional[List[str]] = None,
        namespace: Optional[str] = None,
        token: Union[bool, str, None] = None,
    ) -> InferenceEndpoint:
        """Create a new Inference Endpoint.

        Args:
            name (`str`):
                The unique name for the new Inference Endpoint.
            repository (`str`):
                The name of the model repository associated with the Inference Endpoint (e.g. `"gpt2"`).
            framework (`str`):
                The machine learning framework used for the model (e.g. `"custom"`).
            accelerator (`str`):
                The hardware accelerator to be used for inference (e.g. `"cpu"`).
            instance_size (`str`):
                The size or type of the instance to be used for hosting the model (e.g. `"x4"`).
            instance_type (`str`):
                The cloud instance type where the Inference Endpoint will be deployed (e.g. `"intel-icl"`).
            region (`str`):
                The cloud region in which the Inference Endpoint will be created (e.g. `"us-east-1"`).
            vendor (`str`):
                The cloud provider or vendor where the Inference Endpoint will be hosted (e.g. `"aws"`).
            account_id (`str`, *optional*):
                The account ID used to link a VPC to a private Inference Endpoint (if applicable).
            min_replica (`int`, *optional*):
                The minimum number of replicas (instances) to keep running for the Inference Endpoint. To enable
                scaling to zero, set this value to 0 and adjust `scale_to_zero_timeout` accordingly. Defaults to 1.
            max_replica (`int`, *optional*):
                The maximum number of replicas (instances) to scale to for the Inference Endpoint. Defaults to 1.
            scale_to_zero_timeout (`int`, *optional*):
                The duration in minutes before an inactive endpoint is scaled to zero, or no scaling to zero if
                set to None and `min_replica` is not 0. Defaults to None.
            revision (`str`, *optional*):
                The specific model revision to deploy on the Inference Endpoint (e.g. `"6c0e6080953db56375760c0471a8c5f2929baf11"`).
            task (`str`, *optional*):
                The task on which to deploy the model (e.g. `"text-classification"`).
            custom_image (`Dict`, *optional*):
                A custom Docker image to use for the Inference Endpoint. This is useful if you want to deploy an
                Inference Endpoint running on the `text-generation-inference` (TGI) framework (see examples).
            env (`Dict[str, str]`, *optional*):
                Non-secret environment variables to inject in the container environment.
            secrets (`Dict[str, str]`, *optional*):
                Secret values to inject in the container environment.
            type ([`InferenceEndpointType]`, *optional*):
                The type of the Inference Endpoint, which can be `"protected"` (default), `"public"` or `"private"`.
            domain (`str`, *optional*):
                The custom domain for the Inference Endpoint deployment, if setup the inference endpoint will be available at this domain (e.g. `"my-new-domain.cool-website.woof"`).
            path (`str`, *optional*):
                The custom path to the deployed model, should start with a `/` (e.g. `"/models/google-bert/bert-base-uncased"`).
            cache_http_responses (`bool`, *optional*):
                Whether to cache HTTP responses from the Inference Endpoint. Defaults to `False`.
            tags (`List[str]`, *optional*):
                A list of tags to associate with the Inference Endpoint.
            namespace (`str`, *optional*):
                The namespace where the Inference Endpoint will be created. Defaults to the current user's namespace.
            token (Union[bool, str, None], optional):
                A valid user access token (string). Defaults to the locally saved
                token, which is the recommended method for authentication (see
                https://huggingface.co/docs/huggingface_hub/quick-start#authentication).
                To disable authentication, pass `False`.

            Returns:
                [`InferenceEndpoint`]: information about the updated Inference Endpoint.

            Example:
            ```python
            >>> from huggingface_hub import HfApi
            >>> api = HfApi()
            >>> endpoint = api.create_inference_endpoint(
            ...     "my-endpoint-name",
            ...     repository="gpt2",
            ...     framework="pytorch",
            ...     task="text-generation",
            ...     accelerator="cpu",
            ...     vendor="aws",
            ...     region="us-east-1",
            ...     type="protected",
            ...     instance_size="x2",
            ...     instance_type="intel-icl",
            ... )
            >>> endpoint
            InferenceEndpoint(name='my-endpoint-name', status="pending",...)

            # Run inference on the endpoint
            >>> endpoint.client.text_generation(...)
            "..."
            ```

            ```python
            # Start an Inference Endpoint running Zephyr-7b-beta on TGI
            >>> from huggingface_hub import HfApi
            >>> api = HfApi()
            >>> endpoint = api.create_inference_endpoint(
            ...     "aws-zephyr-7b-beta-0486",
            ...     repository="HuggingFaceH4/zephyr-7b-beta",
            ...     framework="pytorch",
            ...     task="text-generation",
            ...     accelerator="gpu",
            ...     vendor="aws",
            ...     region="us-east-1",
            ...     type="protected",
            ...     instance_size="x1",
            ...     instance_type="nvidia-a10g",
            ...     env={
            ...           "MAX_BATCH_PREFILL_TOKENS": "2048",
            ...           "MAX_INPUT_LENGTH": "1024",
            ...           "MAX_TOTAL_TOKENS": "1512",
            ...           "MODEL_ID": "/repository"
            ...         },
            ...     custom_image={
            ...         "health_route": "/health",
            ...         "url": "ghcr.io/huggingface/text-generation-inference:1.1.0",
            ...     },
            ...    secrets={"MY_SECRET_KEY": "secret_value"},
            ...    tags=["dev", "text-generation"],
            ... )
            ```

            ```python
            # Start an Inference Endpoint running ProsusAI/finbert while scaling to zero in 15 minutes
            >>> from huggingface_hub import HfApi
            >>> api = HfApi()
            >>> endpoint = api.create_inference_endpoint(
            ...     "finbert-classifier",
            ...     repository="ProsusAI/finbert",
            ...     framework="pytorch",
            ...     task="text-classification",
            ...     min_replica=0,
            ...     scale_to_zero_timeout=15,
            ...     accelerator="cpu",
            ...     vendor="aws",
            ...     region="us-east-1",
            ...     type="protected",
            ...     instance_size="x2",
            ...     instance_type="intel-icl",
            ... )
            >>> endpoint.wait(timeout=300)
            # Run inference on the endpoint
            >>> endpoint.client.text_generation(...)
            TextClassificationOutputElement(label='positive', score=0.8983615040779114)
            ```

        """
        namespace = namespace or self._get_namespace(token=token)

        if custom_image is not None:
            image = (
                custom_image
                if next(iter(custom_image)) in constants.INFERENCE_ENDPOINT_IMAGE_KEYS
                else {"custom": custom_image}
            )
        else:
            image = {"huggingface": {}}

        payload: Dict = {
            "accountId": account_id,
            "compute": {
                "accelerator": accelerator,
                "instanceSize": instance_size,
                "instanceType": instance_type,
                "scaling": {
                    "maxReplica": max_replica,
                    "minReplica": min_replica,
                    "scaleToZeroTimeout": scale_to_zero_timeout,
                },
            },
            "model": {
                "framework": framework,
                "repository": repository,
                "revision": revision,
                "task": task,
                "image": image,
            },
            "name": name,
            "provider": {
                "region": region,
                "vendor": vendor,
            },
            "type": type,
        }
        if env:
            payload["model"]["env"] = env
        if secrets:
            payload["model"]["secrets"] = secrets
        if domain is not None or path is not None:
            payload["route"] = {}
            if domain is not None:
                payload["route"]["domain"] = domain
            if path is not None:
                payload["route"]["path"] = path
        if cache_http_responses is not None:
            payload["cacheHttpResponses"] = cache_http_responses
        if tags is not None:
            payload["tags"] = tags

        response = get_session().post(
            f"{constants.INFERENCE_ENDPOINTS_ENDPOINT}/endpoint/{namespace}",
            headers=self._build_hf_headers(token=token),
            json=payload,
        )
        hf_raise_for_status(response)

        return InferenceEndpoint.from_raw(response.json(), namespace=namespace, token=token)

    @experimental
    @validate_hf_hub_args
    def create_inference_endpoint_from_catalog(
        self,
        repo_id: str,
        *,
        name: Optional[str] = None,
        token: Union[bool, str, None] = None,
        namespace: Optional[str] = None,
    ) -> InferenceEndpoint:
        """Create a new Inference Endpoint from a model in the Hugging Face Inference Catalog.

        The goal of the Inference Catalog is to provide a curated list of models that are optimized for inference
        and for which default configurations have been tested. See https://endpoints.huggingface.co/catalog for a list
        of available models in the catalog.

        Args:
            repo_id (`str`):
                The ID of the model in the catalog to deploy as an Inference Endpoint.
            name (`str`, *optional*):
                The unique name for the new Inference Endpoint. If not provided, a random name will be generated.
            token (Union[bool, str, None], optional):
                A valid user access token (string). Defaults to the locally saved
                token, which is the recommended method for authentication (see
                https://huggingface.co/docs/huggingface_hub/quick-start#authentication).
            namespace (`str`, *optional*):
                The namespace where the Inference Endpoint will be created. Defaults to the current user's namespace.

        Returns:
            [`InferenceEndpoint`]: information about the new Inference Endpoint.

        <Tip warning={true}>

        `create_inference_endpoint_from_catalog` is experimental. Its API is subject to change in the future. Please provide feedback
        if you have any suggestions or requests.

        </Tip>
        """
        token = token or self.token or get_token()
        payload: Dict = {
            "namespace": namespace or self._get_namespace(token=token),
            "repoId": repo_id,
        }
        if name is not None:
            payload["endpointName"] = name

        response = get_session().post(
            f"{constants.INFERENCE_CATALOG_ENDPOINT}/deploy",
            headers=self._build_hf_headers(token=token),
            json=payload,
        )
        hf_raise_for_status(response)
        data = response.json()["endpoint"]
        return InferenceEndpoint.from_raw(data, namespace=data["name"], token=token)

    @experimental
    @validate_hf_hub_args
    def list_inference_catalog(self, *, token: Union[bool, str, None] = None) -> List[str]:
        """List models available in the Hugging Face Inference Catalog.

        The goal of the Inference Catalog is to provide a curated list of models that are optimized for inference
        and for which default configurations have been tested. See https://endpoints.huggingface.co/catalog for a list
        of available models in the catalog.

        Use [`create_inference_endpoint_from_catalog`] to deploy a model from the catalog.

        Args:
            token (Union[bool, str, None], optional):
                A valid user access token (string). Defaults to the locally saved
                token, which is the recommended method for authentication (see
                https://huggingface.co/docs/huggingface_hub/quick-start#authentication).

        Returns:
            List[`str`]: A list of model IDs available in the catalog.
        <Tip warning={true}>

        `list_inference_catalog` is experimental. Its API is subject to change in the future. Please provide feedback
        if you have any suggestions or requests.

        </Tip>
        """
        response = get_session().get(
            f"{constants.INFERENCE_CATALOG_ENDPOINT}/repo-list",
            headers=self._build_hf_headers(token=token),
        )
        hf_raise_for_status(response)
        return response.json()["models"]

    def get_inference_endpoint(
        self, name: str, *, namespace: Optional[str] = None, token: Union[bool, str, None] = None
    ) -> InferenceEndpoint:
        """Get information about an Inference Endpoint.

        Args:
            name (`str`):
                The name of the Inference Endpoint to retrieve information about.
            namespace (`str`, *optional*):
                The namespace in which the Inference Endpoint is located. Defaults to the current user.
            token (Union[bool, str, None], optional):
                A valid user access token (string). Defaults to the locally saved
                token, which is the recommended method for authentication (see
                https://huggingface.co/docs/huggingface_hub/quick-start#authentication).
                To disable authentication, pass `False`.

        Returns:
            [`InferenceEndpoint`]: information about the requested Inference Endpoint.

        Example:
        ```python
        >>> from huggingface_hub import HfApi
        >>> api = HfApi()
        >>> endpoint = api.get_inference_endpoint("my-text-to-image")
        >>> endpoint
        InferenceEndpoint(name='my-text-to-image', ...)

        # Get status
        >>> endpoint.status
        'running'
        >>> endpoint.url
        'https://my-text-to-image.region.vendor.endpoints.huggingface.cloud'

        # Run inference
        >>> endpoint.client.text_to_image(...)
        ```
        """
        namespace = namespace or self._get_namespace(token=token)

        response = get_session().get(
            f"{constants.INFERENCE_ENDPOINTS_ENDPOINT}/endpoint/{namespace}/{name}",
            headers=self._build_hf_headers(token=token),
        )
        hf_raise_for_status(response)

        return InferenceEndpoint.from_raw(response.json(), namespace=namespace, token=token)

    def update_inference_endpoint(
        self,
        name: str,
        *,
        # Compute update
        accelerator: Optional[str] = None,
        instance_size: Optional[str] = None,
        instance_type: Optional[str] = None,
        min_replica: Optional[int] = None,
        max_replica: Optional[int] = None,
        scale_to_zero_timeout: Optional[int] = None,
        # Model update
        repository: Optional[str] = None,
        framework: Optional[str] = None,
        revision: Optional[str] = None,
        task: Optional[str] = None,
        custom_image: Optional[Dict] = None,
        env: Optional[Dict[str, str]] = None,
        secrets: Optional[Dict[str, str]] = None,
        # Route update
        domain: Optional[str] = None,
        path: Optional[str] = None,
        # Other
        cache_http_responses: Optional[bool] = None,
        tags: Optional[List[str]] = None,
        namespace: Optional[str] = None,
        token: Union[bool, str, None] = None,
    ) -> InferenceEndpoint:
        """Update an Inference Endpoint.

        This method allows the update of either the compute configuration, the deployed model, the route, or any combination.
        All arguments are optional but at least one must be provided.

        For convenience, you can also update an Inference Endpoint using [`InferenceEndpoint.update`].

        Args:
            name (`str`):
                The name of the Inference Endpoint to update.

            accelerator (`str`, *optional*):
                The hardware accelerator to be used for inference (e.g. `"cpu"`).
            instance_size (`str`, *optional*):
                The size or type of the instance to be used for hosting the model (e.g. `"x4"`).
            instance_type (`str`, *optional*):
                The cloud instance type where the Inference Endpoint will be deployed (e.g. `"intel-icl"`).
            min_replica (`int`, *optional*):
                The minimum number of replicas (instances) to keep running for the Inference Endpoint.
            max_replica (`int`, *optional*):
                The maximum number of replicas (instances) to scale to for the Inference Endpoint.
            scale_to_zero_timeout (`int`, *optional*):
                The duration in minutes before an inactive endpoint is scaled to zero.

            repository (`str`, *optional*):
                The name of the model repository associated with the Inference Endpoint (e.g. `"gpt2"`).
            framework (`str`, *optional*):
                The machine learning framework used for the model (e.g. `"custom"`).
            revision (`str`, *optional*):
                The specific model revision to deploy on the Inference Endpoint (e.g. `"6c0e6080953db56375760c0471a8c5f2929baf11"`).
            task (`str`, *optional*):
                The task on which to deploy the model (e.g. `"text-classification"`).
            custom_image (`Dict`, *optional*):
                A custom Docker image to use for the Inference Endpoint. This is useful if you want to deploy an
                Inference Endpoint running on the `text-generation-inference` (TGI) framework (see examples).
            env (`Dict[str, str]`, *optional*):
                Non-secret environment variables to inject in the container environment
            secrets (`Dict[str, str]`, *optional*):
                Secret values to inject in the container environment.

            domain (`str`, *optional*):
                The custom domain for the Inference Endpoint deployment, if setup the inference endpoint will be available at this domain (e.g. `"my-new-domain.cool-website.woof"`).
            path (`str`, *optional*):
                The custom path to the deployed model, should start with a `/` (e.g. `"/models/google-bert/bert-base-uncased"`).

            cache_http_responses (`bool`, *optional*):
                Whether to cache HTTP responses from the Inference Endpoint.
            tags (`List[str]`, *optional*):
                A list of tags to associate with the Inference Endpoint.

            namespace (`str`, *optional*):
                The namespace where the Inference Endpoint will be updated. Defaults to the current user's namespace.
            token (Union[bool, str, None], optional):
                A valid user access token (string). Defaults to the locally saved
                token, which is the recommended method for authentication (see
                https://huggingface.co/docs/huggingface_hub/quick-start#authentication).
                To disable authentication, pass `False`.

        Returns:
            [`InferenceEndpoint`]: information about the updated Inference Endpoint.
        """
        namespace = namespace or self._get_namespace(token=token)

        # Populate only the fields that are not None
        payload: Dict = defaultdict(lambda: defaultdict(dict))
        if accelerator is not None:
            payload["compute"]["accelerator"] = accelerator
        if instance_size is not None:
            payload["compute"]["instanceSize"] = instance_size
        if instance_type is not None:
            payload["compute"]["instanceType"] = instance_type
        if max_replica is not None:
            payload["compute"]["scaling"]["maxReplica"] = max_replica
        if min_replica is not None:
            payload["compute"]["scaling"]["minReplica"] = min_replica
        if scale_to_zero_timeout is not None:
            payload["compute"]["scaling"]["scaleToZeroTimeout"] = scale_to_zero_timeout
        if repository is not None:
            payload["model"]["repository"] = repository
        if framework is not None:
            payload["model"]["framework"] = framework
        if revision is not None:
            payload["model"]["revision"] = revision
        if task is not None:
            payload["model"]["task"] = task
        if custom_image is not None:
            payload["model"]["image"] = {"custom": custom_image}
        if env is not None:
            payload["model"]["env"] = env
        if secrets is not None:
            payload["model"]["secrets"] = secrets
        if domain is not None:
            payload["route"]["domain"] = domain
        if path is not None:
            payload["route"]["path"] = path
        if cache_http_responses is not None:
            payload["cacheHttpResponses"] = cache_http_responses
        if tags is not None:
            payload["tags"] = tags

        response = get_session().put(
            f"{constants.INFERENCE_ENDPOINTS_ENDPOINT}/endpoint/{namespace}/{name}",
            headers=self._build_hf_headers(token=token),
            json=payload,
        )
        hf_raise_for_status(response)

        return InferenceEndpoint.from_raw(response.json(), namespace=namespace, token=token)

    def delete_inference_endpoint(
        self, name: str, *, namespace: Optional[str] = None, token: Union[bool, str, None] = None
    ) -> None:
        """Delete an Inference Endpoint.

        This operation is not reversible. If you don't want to be charged for an Inference Endpoint, it is preferable
        to pause it with [`pause_inference_endpoint`] or scale it to zero with [`scale_to_zero_inference_endpoint`].

        For convenience, you can also delete an Inference Endpoint using [`InferenceEndpoint.delete`].

        Args:
            name (`str`):
                The name of the Inference Endpoint to delete.
            namespace (`str`, *optional*):
                The namespace in which the Inference Endpoint is located. Defaults to the current user.
            token (Union[bool, str, None], optional):
                A valid user access token (string). Defaults to the locally saved
                token, which is the recommended method for authentication (see
                https://huggingface.co/docs/huggingface_hub/quick-start#authentication).
                To disable authentication, pass `False`.
        """
        namespace = namespace or self._get_namespace(token=token)
        response = get_session().delete(
            f"{constants.INFERENCE_ENDPOINTS_ENDPOINT}/endpoint/{namespace}/{name}",
            headers=self._build_hf_headers(token=token),
        )
        hf_raise_for_status(response)

    def pause_inference_endpoint(
        self, name: str, *, namespace: Optional[str] = None, token: Union[bool, str, None] = None
    ) -> InferenceEndpoint:
        """Pause an Inference Endpoint.

        A paused Inference Endpoint will not be charged. It can be resumed at any time using [`resume_inference_endpoint`].
        This is different than scaling the Inference Endpoint to zero with [`scale_to_zero_inference_endpoint`], which
        would be automatically restarted when a request is made to it.

        For convenience, you can also pause an Inference Endpoint using [`pause_inference_endpoint`].

        Args:
            name (`str`):
                The name of the Inference Endpoint to pause.
            namespace (`str`, *optional*):
                The namespace in which the Inference Endpoint is located. Defaults to the current user.
            token (Union[bool, str, None], optional):
                A valid user access token (string). Defaults to the locally saved
                token, which is the recommended method for authentication (see
                https://huggingface.co/docs/huggingface_hub/quick-start#authentication).
                To disable authentication, pass `False`.

        Returns:
            [`InferenceEndpoint`]: information about the paused Inference Endpoint.
        """
        namespace = namespace or self._get_namespace(token=token)

        response = get_session().post(
            f"{constants.INFERENCE_ENDPOINTS_ENDPOINT}/endpoint/{namespace}/{name}/pause",
            headers=self._build_hf_headers(token=token),
        )
        hf_raise_for_status(response)

        return InferenceEndpoint.from_raw(response.json(), namespace=namespace, token=token)

    def resume_inference_endpoint(
        self,
        name: str,
        *,
        namespace: Optional[str] = None,
        running_ok: bool = True,
        token: Union[bool, str, None] = None,
    ) -> InferenceEndpoint:
        """Resume an Inference Endpoint.

        For convenience, you can also resume an Inference Endpoint using [`InferenceEndpoint.resume`].

        Args:
            name (`str`):
                The name of the Inference Endpoint to resume.
            namespace (`str`, *optional*):
                The namespace in which the Inference Endpoint is located. Defaults to the current user.
            running_ok (`bool`, *optional*):
                If `True`, the method will not raise an error if the Inference Endpoint is already running. Defaults to
                `True`.
            token (Union[bool, str, None], optional):
                A valid user access token (string). Defaults to the locally saved
                token, which is the recommended method for authentication (see
                https://huggingface.co/docs/huggingface_hub/quick-start#authentication).
                To disable authentication, pass `False`.

        Returns:
            [`InferenceEndpoint`]: information about the resumed Inference Endpoint.
        """
        namespace = namespace or self._get_namespace(token=token)

        response = get_session().post(
            f"{constants.INFERENCE_ENDPOINTS_ENDPOINT}/endpoint/{namespace}/{name}/resume",
            headers=self._build_hf_headers(token=token),
        )
        try:
            hf_raise_for_status(response)
        except HfHubHTTPError as error:
            # If already running (and it's ok), then fetch current status and return
            if running_ok and error.response.status_code == 400 and "already running" in error.response.text:
                return self.get_inference_endpoint(name, namespace=namespace, token=token)
            # Otherwise, raise the error
            raise

        return InferenceEndpoint.from_raw(response.json(), namespace=namespace, token=token)

    def scale_to_zero_inference_endpoint(
        self, name: str, *, namespace: Optional[str] = None, token: Union[bool, str, None] = None
    ) -> InferenceEndpoint:
        """Scale Inference Endpoint to zero.

        An Inference Endpoint scaled to zero will not be charged. It will be resume on the next request to it, with a
        cold start delay. This is different than pausing the Inference Endpoint with [`pause_inference_endpoint`], which
        would require a manual resume with [`resume_inference_endpoint`].

        For convenience, you can also scale an Inference Endpoint to zero using [`InferenceEndpoint.scale_to_zero`].

        Args:
            name (`str`):
                The name of the Inference Endpoint to scale to zero.
            namespace (`str`, *optional*):
                The namespace in which the Inference Endpoint is located. Defaults to the current user.
            token (Union[bool, str, None], optional):
                A valid user access token (string). Defaults to the locally saved
                token, which is the recommended method for authentication (see
                https://huggingface.co/docs/huggingface_hub/quick-start#authentication).
                To disable authentication, pass `False`.

        Returns:
            [`InferenceEndpoint`]: information about the scaled-to-zero Inference Endpoint.
        """
        namespace = namespace or self._get_namespace(token=token)

        response = get_session().post(
            f"{constants.INFERENCE_ENDPOINTS_ENDPOINT}/endpoint/{namespace}/{name}/scale-to-zero",
            headers=self._build_hf_headers(token=token),
        )
        hf_raise_for_status(response)

        return InferenceEndpoint.from_raw(response.json(), namespace=namespace, token=token)

    def _get_namespace(self, token: Union[bool, str, None] = None) -> str:
        """Get the default namespace for the current user."""
        me = self.whoami(token=token)
        if me["type"] == "user":
            return me["name"]
        else:
            raise ValueError(
                "Cannot determine default namespace. You must provide a 'namespace' as input or be logged in as a"
                " user."
            )

    ########################
    # Collection Endpoints #
    ########################
    @validate_hf_hub_args
    def list_collections(
        self,
        *,
        owner: Union[List[str], str, None] = None,
        item: Union[List[str], str, None] = None,
        sort: Optional[Literal["lastModified", "trending", "upvotes"]] = None,
        limit: Optional[int] = None,
        token: Union[bool, str, None] = None,
    ) -> Iterable[Collection]:
        """List collections on the Huggingface Hub, given some filters.

        <Tip warning={true}>

        When listing collections, the item list per collection is truncated to 4 items maximum. To retrieve all items
        from a collection, you must use [`get_collection`].

        </Tip>

        Args:
            owner (`List[str]` or `str`, *optional*):
                Filter by owner's username.
            item (`List[str]` or `str`, *optional*):
                Filter collections containing a particular items. Example: `"models/teknium/OpenHermes-2.5-Mistral-7B"`, `"datasets/squad"` or `"papers/2311.12983"`.
            sort (`Literal["lastModified", "trending", "upvotes"]`, *optional*):
                Sort collections by last modified, trending or upvotes.
            limit (`int`, *optional*):
                Maximum number of collections to be returned.
            token (Union[bool, str, None], optional):
                A valid user access token (string). Defaults to the locally saved
                token, which is the recommended method for authentication (see
                https://huggingface.co/docs/huggingface_hub/quick-start#authentication).
                To disable authentication, pass `False`.

        Returns:
            `Iterable[Collection]`: an iterable of [`Collection`] objects.
        """
        # Construct the API endpoint
        path = f"{self.endpoint}/api/collections"
        headers = self._build_hf_headers(token=token)
        params: Dict = {}
        if owner is not None:
            params.update({"owner": owner})
        if item is not None:
            params.update({"item": item})
        if sort is not None:
            params.update({"sort": sort})
        if limit is not None:
            params.update({"limit": limit})

        # Paginate over the results until limit is reached
        items = paginate(path, headers=headers, params=params)
        if limit is not None:
            items = islice(items, limit)  # Do not iterate over all pages

        # Parse as Collection and return
        for position, collection_data in enumerate(items):
            yield Collection(position=position, **collection_data)

    def get_collection(self, collection_slug: str, *, token: Union[bool, str, None] = None) -> Collection:
        """Gets information about a Collection on the Hub.

        Args:
            collection_slug (`str`):
                Slug of the collection of the Hub. Example: `"TheBloke/recent-models-64f9a55bb3115b4f513ec026"`.
            token (Union[bool, str, None], optional):
                A valid user access token (string). Defaults to the locally saved
                token, which is the recommended method for authentication (see
                https://huggingface.co/docs/huggingface_hub/quick-start#authentication).
                To disable authentication, pass `False`.

        Returns: [`Collection`]

        Example:

        ```py
        >>> from huggingface_hub import get_collection
        >>> collection = get_collection("TheBloke/recent-models-64f9a55bb3115b4f513ec026")
        >>> collection.title
        'Recent models'
        >>> len(collection.items)
        37
        >>> collection.items[0]
        CollectionItem(
            item_object_id='651446103cd773a050bf64c2',
            item_id='TheBloke/U-Amethyst-20B-AWQ',
            item_type='model',
            position=88,
            note=None
        )
        ```
        """
        r = get_session().get(
            f"{self.endpoint}/api/collections/{collection_slug}", headers=self._build_hf_headers(token=token)
        )
        hf_raise_for_status(r)
        return Collection(**{**r.json(), "endpoint": self.endpoint})

    def create_collection(
        self,
        title: str,
        *,
        namespace: Optional[str] = None,
        description: Optional[str] = None,
        private: bool = False,
        exists_ok: bool = False,
        token: Union[bool, str, None] = None,
    ) -> Collection:
        """Create a new Collection on the Hub.

        Args:
            title (`str`):
                Title of the collection to create. Example: `"Recent models"`.
            namespace (`str`, *optional*):
                Namespace of the collection to create (username or org). Will default to the owner name.
            description (`str`, *optional*):
                Description of the collection to create.
            private (`bool`, *optional*):
                Whether the collection should be private or not. Defaults to `False` (i.e. public collection).
            exists_ok (`bool`, *optional*):
                If `True`, do not raise an error if collection already exists.
            token (Union[bool, str, None], optional):
                A valid user access token (string). Defaults to the locally saved
                token, which is the recommended method for authentication (see
                https://huggingface.co/docs/huggingface_hub/quick-start#authentication).
                To disable authentication, pass `False`.

        Returns: [`Collection`]

        Example:

        ```py
        >>> from huggingface_hub import create_collection
        >>> collection = create_collection(
        ...     title="ICCV 2023",
        ...     description="Portfolio of models, papers and demos I presented at ICCV 2023",
        ... )
        >>> collection.slug
        "username/iccv-2023-64f9a55bb3115b4f513ec026"
        ```
        """
        if namespace is None:
            namespace = self.whoami(token)["name"]

        payload = {
            "title": title,
            "namespace": namespace,
            "private": private,
        }
        if description is not None:
            payload["description"] = description

        r = get_session().post(
            f"{self.endpoint}/api/collections", headers=self._build_hf_headers(token=token), json=payload
        )
        try:
            hf_raise_for_status(r)
        except HTTPError as err:
            if exists_ok and err.response.status_code == 409:
                # Collection already exists and `exists_ok=True`
                slug = r.json()["slug"]
                return self.get_collection(slug, token=token)
            else:
                raise
        return Collection(**{**r.json(), "endpoint": self.endpoint})

    def update_collection_metadata(
        self,
        collection_slug: str,
        *,
        title: Optional[str] = None,
        description: Optional[str] = None,
        position: Optional[int] = None,
        private: Optional[bool] = None,
        theme: Optional[str] = None,
        token: Union[bool, str, None] = None,
    ) -> Collection:
        """Update metadata of a collection on the Hub.

        All arguments are optional. Only provided metadata will be updated.

        Args:
            collection_slug (`str`):
                Slug of the collection to update. Example: `"TheBloke/recent-models-64f9a55bb3115b4f513ec026"`.
            title (`str`):
                Title of the collection to update.
            description (`str`, *optional*):
                Description of the collection to update.
            position (`int`, *optional*):
                New position of the collection in the list of collections of the user.
            private (`bool`, *optional*):
                Whether the collection should be private or not.
            theme (`str`, *optional*):
                Theme of the collection on the Hub.
            token (Union[bool, str, None], optional):
                A valid user access token (string). Defaults to the locally saved
                token, which is the recommended method for authentication (see
                https://huggingface.co/docs/huggingface_hub/quick-start#authentication).
                To disable authentication, pass `False`.

        Returns: [`Collection`]

        Example:

        ```py
        >>> from huggingface_hub import update_collection_metadata
        >>> collection = update_collection_metadata(
        ...     collection_slug="username/iccv-2023-64f9a55bb3115b4f513ec026",
        ...     title="ICCV Oct. 2023"
        ...     description="Portfolio of models, datasets, papers and demos I presented at ICCV Oct. 2023",
        ...     private=False,
        ...     theme="pink",
        ... )
        >>> collection.slug
        "username/iccv-oct-2023-64f9a55bb3115b4f513ec026"
        # ^collection slug got updated but not the trailing ID
        ```
        """
        payload = {
            "position": position,
            "private": private,
            "theme": theme,
            "title": title,
            "description": description,
        }
        r = get_session().patch(
            f"{self.endpoint}/api/collections/{collection_slug}",
            headers=self._build_hf_headers(token=token),
            # Only send not-none values to the API
            json={key: value for key, value in payload.items() if value is not None},
        )
        hf_raise_for_status(r)
        return Collection(**{**r.json()["data"], "endpoint": self.endpoint})

    def delete_collection(
        self, collection_slug: str, *, missing_ok: bool = False, token: Union[bool, str, None] = None
    ) -> None:
        """Delete a collection on the Hub.

        Args:
            collection_slug (`str`):
                Slug of the collection to delete. Example: `"TheBloke/recent-models-64f9a55bb3115b4f513ec026"`.
            missing_ok (`bool`, *optional*):
                If `True`, do not raise an error if collection doesn't exists.
            token (Union[bool, str, None], optional):
                A valid user access token (string). Defaults to the locally saved
                token, which is the recommended method for authentication (see
                https://huggingface.co/docs/huggingface_hub/quick-start#authentication).
                To disable authentication, pass `False`.

        Example:

        ```py
        >>> from huggingface_hub import delete_collection
        >>> collection = delete_collection("username/useless-collection-64f9a55bb3115b4f513ec026", missing_ok=True)
        ```

        <Tip warning={true}>

        This is a non-revertible action. A deleted collection cannot be restored.

        </Tip>
        """
        r = get_session().delete(
            f"{self.endpoint}/api/collections/{collection_slug}", headers=self._build_hf_headers(token=token)
        )
        try:
            hf_raise_for_status(r)
        except HTTPError as err:
            if missing_ok and err.response.status_code == 404:
                # Collection doesn't exists and `missing_ok=True`
                return
            else:
                raise

    def add_collection_item(
        self,
        collection_slug: str,
        item_id: str,
        item_type: CollectionItemType_T,
        *,
        note: Optional[str] = None,
        exists_ok: bool = False,
        token: Union[bool, str, None] = None,
    ) -> Collection:
        """Add an item to a collection on the Hub.

        Args:
            collection_slug (`str`):
                Slug of the collection to update. Example: `"TheBloke/recent-models-64f9a55bb3115b4f513ec026"`.
            item_id (`str`):
                ID of the item to add to the collection. It can be the ID of a repo on the Hub (e.g. `"facebook/bart-large-mnli"`)
                or a paper id (e.g. `"2307.09288"`).
            item_type (`str`):
                Type of the item to add. Can be one of `"model"`, `"dataset"`, `"space"` or `"paper"`.
            note (`str`, *optional*):
                A note to attach to the item in the collection. The maximum size for a note is 500 characters.
            exists_ok (`bool`, *optional*):
                If `True`, do not raise an error if item already exists.
            token (Union[bool, str, None], optional):
                A valid user access token (string). Defaults to the locally saved
                token, which is the recommended method for authentication (see
                https://huggingface.co/docs/huggingface_hub/quick-start#authentication).
                To disable authentication, pass `False`.

        Returns: [`Collection`]

        Raises:
            [`HTTPError`](https://requests.readthedocs.io/en/latest/api/#requests.HTTPError):
                HTTP 403 if you only have read-only access to the repo. This can be the case if you don't have `write`
                or `admin` role in the organization the repo belongs to or if you passed a `read` token.
            [`HTTPError`](https://requests.readthedocs.io/en/latest/api/#requests.HTTPError):
                HTTP 404 if the item you try to add to the collection does not exist on the Hub.
            [`HTTPError`](https://requests.readthedocs.io/en/latest/api/#requests.HTTPError):
                HTTP 409 if the item you try to add to the collection is already in the collection (and exists_ok=False)

        Example:

        ```py
        >>> from huggingface_hub import add_collection_item
        >>> collection = add_collection_item(
        ...     collection_slug="davanstrien/climate-64f99dc2a5067f6b65531bab",
        ...     item_id="pierre-loic/climate-news-articles",
        ...     item_type="dataset"
        ... )
        >>> collection.items[-1].item_id
        "pierre-loic/climate-news-articles"
        # ^item got added to the collection on last position

        # Add item with a note
        >>> add_collection_item(
        ...     collection_slug="davanstrien/climate-64f99dc2a5067f6b65531bab",
        ...     item_id="datasets/climate_fever",
        ...     item_type="dataset"
        ...     note="This dataset adopts the FEVER methodology that consists of 1,535 real-world claims regarding climate-change collected on the internet."
        ... )
        (...)
        ```
        """
        payload: Dict[str, Any] = {"item": {"id": item_id, "type": item_type}}
        if note is not None:
            payload["note"] = note
        r = get_session().post(
            f"{self.endpoint}/api/collections/{collection_slug}/items",
            headers=self._build_hf_headers(token=token),
            json=payload,
        )
        try:
            hf_raise_for_status(r)
        except HTTPError as err:
            if exists_ok and err.response.status_code == 409:
                # Item already exists and `exists_ok=True`
                return self.get_collection(collection_slug, token=token)
            else:
                raise
        return Collection(**{**r.json(), "endpoint": self.endpoint})

    def update_collection_item(
        self,
        collection_slug: str,
        item_object_id: str,
        *,
        note: Optional[str] = None,
        position: Optional[int] = None,
        token: Union[bool, str, None] = None,
    ) -> None:
        """Update an item in a collection.

        Args:
            collection_slug (`str`):
                Slug of the collection to update. Example: `"TheBloke/recent-models-64f9a55bb3115b4f513ec026"`.
            item_object_id (`str`):
                ID of the item in the collection. This is not the id of the item on the Hub (repo_id or paper id).
                It must be retrieved from a [`CollectionItem`] object. Example: `collection.items[0].item_object_id`.
            note (`str`, *optional*):
                A note to attach to the item in the collection. The maximum size for a note is 500 characters.
            position (`int`, *optional*):
                New position of the item in the collection.
            token (Union[bool, str, None], optional):
                A valid user access token (string). Defaults to the locally saved
                token, which is the recommended method for authentication (see
                https://huggingface.co/docs/huggingface_hub/quick-start#authentication).
                To disable authentication, pass `False`.

        Example:

        ```py
        >>> from huggingface_hub import get_collection, update_collection_item

        # Get collection first
        >>> collection = get_collection("TheBloke/recent-models-64f9a55bb3115b4f513ec026")

        # Update item based on its ID (add note + update position)
        >>> update_collection_item(
        ...     collection_slug="TheBloke/recent-models-64f9a55bb3115b4f513ec026",
        ...     item_object_id=collection.items[-1].item_object_id,
        ...     note="Newly updated model!"
        ...     position=0,
        ... )
        ```
        """
        payload = {"position": position, "note": note}
        r = get_session().patch(
            f"{self.endpoint}/api/collections/{collection_slug}/items/{item_object_id}",
            headers=self._build_hf_headers(token=token),
            # Only send not-none values to the API
            json={key: value for key, value in payload.items() if value is not None},
        )
        hf_raise_for_status(r)

    def delete_collection_item(
        self,
        collection_slug: str,
        item_object_id: str,
        *,
        missing_ok: bool = False,
        token: Union[bool, str, None] = None,
    ) -> None:
        """Delete an item from a collection.

        Args:
            collection_slug (`str`):
                Slug of the collection to update. Example: `"TheBloke/recent-models-64f9a55bb3115b4f513ec026"`.
            item_object_id (`str`):
                ID of the item in the collection. This is not the id of the item on the Hub (repo_id or paper id).
                It must be retrieved from a [`CollectionItem`] object. Example: `collection.items[0].item_object_id`.
            missing_ok (`bool`, *optional*):
                If `True`, do not raise an error if item doesn't exists.
            token (Union[bool, str, None], optional):
                A valid user access token (string). Defaults to the locally saved
                token, which is the recommended method for authentication (see
                https://huggingface.co/docs/huggingface_hub/quick-start#authentication).
                To disable authentication, pass `False`.

        Example:

        ```py
        >>> from huggingface_hub import get_collection, delete_collection_item

        # Get collection first
        >>> collection = get_collection("TheBloke/recent-models-64f9a55bb3115b4f513ec026")

        # Delete item based on its ID
        >>> delete_collection_item(
        ...     collection_slug="TheBloke/recent-models-64f9a55bb3115b4f513ec026",
        ...     item_object_id=collection.items[-1].item_object_id,
        ... )
        ```
        """
        r = get_session().delete(
            f"{self.endpoint}/api/collections/{collection_slug}/items/{item_object_id}",
            headers=self._build_hf_headers(token=token),
        )
        try:
            hf_raise_for_status(r)
        except HTTPError as err:
            if missing_ok and err.response.status_code == 404:
                # Item already deleted and `missing_ok=True`
                return
            else:
                raise

    ##########################
    # Manage access requests #
    ##########################

    @validate_hf_hub_args
    def list_pending_access_requests(
        self, repo_id: str, *, repo_type: Optional[str] = None, token: Union[bool, str, None] = None
    ) -> List[AccessRequest]:
        """
        Get pending access requests for a given gated repo.

        A pending request means the user has requested access to the repo but the request has not been processed yet.
        If the approval mode is automatic, this list should be empty. Pending requests can be accepted or rejected
        using [`accept_access_request`] and [`reject_access_request`].

        For more info about gated repos, see https://huggingface.co/docs/hub/models-gated.

        Args:
            repo_id (`str`):
                The id of the repo to get access requests for.
            repo_type (`str`, *optional*):
                The type of the repo to get access requests for. Must be one of `model`, `dataset` or `space`.
                Defaults to `model`.
            token (Union[bool, str, None], optional):
                A valid user access token (string). Defaults to the locally saved
                token, which is the recommended method for authentication (see
                https://huggingface.co/docs/huggingface_hub/quick-start#authentication).
                To disable authentication, pass `False`.

        Returns:
            `List[AccessRequest]`: A list of [`AccessRequest`] objects. Each time contains a `username`, `email`,
            `status` and `timestamp` attribute. If the gated repo has a custom form, the `fields` attribute will
            be populated with user's answers.

        Raises:
            [`HTTPError`](https://requests.readthedocs.io/en/latest/api/#requests.HTTPError):
                HTTP 400 if the repo is not gated.
            [`HTTPError`](https://requests.readthedocs.io/en/latest/api/#requests.HTTPError):
                HTTP 403 if you only have read-only access to the repo. This can be the case if you don't have `write`
                or `admin` role in the organization the repo belongs to or if you passed a `read` token.

        Example:
        ```py
        >>> from huggingface_hub import list_pending_access_requests, accept_access_request

        # List pending requests
        >>> requests = list_pending_access_requests("meta-llama/Llama-2-7b")
        >>> len(requests)
        411
        >>> requests[0]
        [
            AccessRequest(
                username='clem',
                fullname='Clem 🤗',
                email='***',
                timestamp=datetime.datetime(2023, 11, 23, 18, 4, 53, 828000, tzinfo=datetime.timezone.utc),
                status='pending',
                fields=None,
            ),
            ...
        ]

        # Accept Clem's request
        >>> accept_access_request("meta-llama/Llama-2-7b", "clem")
        ```
        """
        return self._list_access_requests(repo_id, "pending", repo_type=repo_type, token=token)

    @validate_hf_hub_args
    def list_accepted_access_requests(
        self, repo_id: str, *, repo_type: Optional[str] = None, token: Union[bool, str, None] = None
    ) -> List[AccessRequest]:
        """
        Get accepted access requests for a given gated repo.

        An accepted request means the user has requested access to the repo and the request has been accepted. The user
        can download any file of the repo. If the approval mode is automatic, this list should contains by default all
        requests. Accepted requests can be cancelled or rejected at any time using [`cancel_access_request`] and
        [`reject_access_request`]. A cancelled request will go back to the pending list while a rejected request will
        go to the rejected list. In both cases, the user will lose access to the repo.

        For more info about gated repos, see https://huggingface.co/docs/hub/models-gated.

        Args:
            repo_id (`str`):
                The id of the repo to get access requests for.
            repo_type (`str`, *optional*):
                The type of the repo to get access requests for. Must be one of `model`, `dataset` or `space`.
                Defaults to `model`.
            token (Union[bool, str, None], optional):
                A valid user access token (string). Defaults to the locally saved
                token, which is the recommended method for authentication (see
                https://huggingface.co/docs/huggingface_hub/quick-start#authentication).
                To disable authentication, pass `False`.

        Returns:
            `List[AccessRequest]`: A list of [`AccessRequest`] objects. Each time contains a `username`, `email`,
            `status` and `timestamp` attribute. If the gated repo has a custom form, the `fields` attribute will
            be populated with user's answers.

        Raises:
            [`HTTPError`](https://requests.readthedocs.io/en/latest/api/#requests.HTTPError):
                HTTP 400 if the repo is not gated.
            [`HTTPError`](https://requests.readthedocs.io/en/latest/api/#requests.HTTPError):
                HTTP 403 if you only have read-only access to the repo. This can be the case if you don't have `write`
                or `admin` role in the organization the repo belongs to or if you passed a `read` token.

        Example:
        ```py
        >>> from huggingface_hub import list_accepted_access_requests

        >>> requests = list_accepted_access_requests("meta-llama/Llama-2-7b")
        >>> len(requests)
        411
        >>> requests[0]
        [
            AccessRequest(
                username='clem',
                fullname='Clem 🤗',
                email='***',
                timestamp=datetime.datetime(2023, 11, 23, 18, 4, 53, 828000, tzinfo=datetime.timezone.utc),
                status='accepted',
                fields=None,
            ),
            ...
        ]
        ```
        """
        return self._list_access_requests(repo_id, "accepted", repo_type=repo_type, token=token)

    @validate_hf_hub_args
    def list_rejected_access_requests(
        self, repo_id: str, *, repo_type: Optional[str] = None, token: Union[bool, str, None] = None
    ) -> List[AccessRequest]:
        """
        Get rejected access requests for a given gated repo.

        A rejected request means the user has requested access to the repo and the request has been explicitly rejected
        by a repo owner (either you or another user from your organization). The user cannot download any file of the
        repo. Rejected requests can be accepted or cancelled at any time using [`accept_access_request`] and
        [`cancel_access_request`]. A cancelled request will go back to the pending list while an accepted request will
        go to the accepted list.

        For more info about gated repos, see https://huggingface.co/docs/hub/models-gated.

        Args:
            repo_id (`str`):
                The id of the repo to get access requests for.
            repo_type (`str`, *optional*):
                The type of the repo to get access requests for. Must be one of `model`, `dataset` or `space`.
                Defaults to `model`.
            token (Union[bool, str, None], optional):
                A valid user access token (string). Defaults to the locally saved
                token, which is the recommended method for authentication (see
                https://huggingface.co/docs/huggingface_hub/quick-start#authentication).
                To disable authentication, pass `False`.

        Returns:
            `List[AccessRequest]`: A list of [`AccessRequest`] objects. Each time contains a `username`, `email`,
            `status` and `timestamp` attribute. If the gated repo has a custom form, the `fields` attribute will
            be populated with user's answers.

        Raises:
            [`HTTPError`](https://requests.readthedocs.io/en/latest/api/#requests.HTTPError):
                HTTP 400 if the repo is not gated.
            [`HTTPError`](https://requests.readthedocs.io/en/latest/api/#requests.HTTPError):
                HTTP 403 if you only have read-only access to the repo. This can be the case if you don't have `write`
                or `admin` role in the organization the repo belongs to or if you passed a `read` token.

        Example:
        ```py
        >>> from huggingface_hub import list_rejected_access_requests

        >>> requests = list_rejected_access_requests("meta-llama/Llama-2-7b")
        >>> len(requests)
        411
        >>> requests[0]
        [
            AccessRequest(
                username='clem',
                fullname='Clem 🤗',
                email='***',
                timestamp=datetime.datetime(2023, 11, 23, 18, 4, 53, 828000, tzinfo=datetime.timezone.utc),
                status='rejected',
                fields=None,
            ),
            ...
        ]
        ```
        """
        return self._list_access_requests(repo_id, "rejected", repo_type=repo_type, token=token)

    def _list_access_requests(
        self,
        repo_id: str,
        status: Literal["accepted", "rejected", "pending"],
        repo_type: Optional[str] = None,
        token: Union[bool, str, None] = None,
    ) -> List[AccessRequest]:
        if repo_type not in constants.REPO_TYPES:
            raise ValueError(f"Invalid repo type, must be one of {constants.REPO_TYPES}")
        if repo_type is None:
            repo_type = constants.REPO_TYPE_MODEL

        response = get_session().get(
            f"{constants.ENDPOINT}/api/{repo_type}s/{repo_id}/user-access-request/{status}",
            headers=self._build_hf_headers(token=token),
        )
        hf_raise_for_status(response)
        return [
            AccessRequest(
                username=request["user"]["user"],
                fullname=request["user"]["fullname"],
                email=request["user"].get("email"),
                status=request["status"],
                timestamp=parse_datetime(request["timestamp"]),
                fields=request.get("fields"),  # only if custom fields in form
            )
            for request in response.json()
        ]

    @validate_hf_hub_args
    def cancel_access_request(
        self, repo_id: str, user: str, *, repo_type: Optional[str] = None, token: Union[bool, str, None] = None
    ) -> None:
        """
        Cancel an access request from a user for a given gated repo.

        A cancelled request will go back to the pending list and the user will lose access to the repo.

        For more info about gated repos, see https://huggingface.co/docs/hub/models-gated.

        Args:
            repo_id (`str`):
                The id of the repo to cancel access request for.
            user (`str`):
                The username of the user which access request should be cancelled.
            repo_type (`str`, *optional*):
                The type of the repo to cancel access request for. Must be one of `model`, `dataset` or `space`.
                Defaults to `model`.
            token (Union[bool, str, None], optional):
                A valid user access token (string). Defaults to the locally saved
                token, which is the recommended method for authentication (see
                https://huggingface.co/docs/huggingface_hub/quick-start#authentication).
                To disable authentication, pass `False`.

        Raises:
            [`HTTPError`](https://requests.readthedocs.io/en/latest/api/#requests.HTTPError):
                HTTP 400 if the repo is not gated.
            [`HTTPError`](https://requests.readthedocs.io/en/latest/api/#requests.HTTPError):
                HTTP 403 if you only have read-only access to the repo. This can be the case if you don't have `write`
                or `admin` role in the organization the repo belongs to or if you passed a `read` token.
            [`HTTPError`](https://requests.readthedocs.io/en/latest/api/#requests.HTTPError):
                HTTP 404 if the user does not exist on the Hub.
            [`HTTPError`](https://requests.readthedocs.io/en/latest/api/#requests.HTTPError):
                HTTP 404 if the user access request cannot be found.
            [`HTTPError`](https://requests.readthedocs.io/en/latest/api/#requests.HTTPError):
                HTTP 404 if the user access request is already in the pending list.
        """
        self._handle_access_request(repo_id, user, "pending", repo_type=repo_type, token=token)

    @validate_hf_hub_args
    def accept_access_request(
        self, repo_id: str, user: str, *, repo_type: Optional[str] = None, token: Union[bool, str, None] = None
    ) -> None:
        """
        Accept an access request from a user for a given gated repo.

        Once the request is accepted, the user will be able to download any file of the repo and access the community
        tab. If the approval mode is automatic, you don't have to accept requests manually. An accepted request can be
        cancelled or rejected at any time using [`cancel_access_request`] and [`reject_access_request`].

        For more info about gated repos, see https://huggingface.co/docs/hub/models-gated.

        Args:
            repo_id (`str`):
                The id of the repo to accept access request for.
            user (`str`):
                The username of the user which access request should be accepted.
            repo_type (`str`, *optional*):
                The type of the repo to accept access request for. Must be one of `model`, `dataset` or `space`.
                Defaults to `model`.
            token (Union[bool, str, None], optional):
                A valid user access token (string). Defaults to the locally saved
                token, which is the recommended method for authentication (see
                https://huggingface.co/docs/huggingface_hub/quick-start#authentication).
                To disable authentication, pass `False`.

        Raises:
            [`HTTPError`](https://requests.readthedocs.io/en/latest/api/#requests.HTTPError):
                HTTP 400 if the repo is not gated.
            [`HTTPError`](https://requests.readthedocs.io/en/latest/api/#requests.HTTPError):
                HTTP 403 if you only have read-only access to the repo. This can be the case if you don't have `write`
                or `admin` role in the organization the repo belongs to or if you passed a `read` token.
            [`HTTPError`](https://requests.readthedocs.io/en/latest/api/#requests.HTTPError):
                HTTP 404 if the user does not exist on the Hub.
            [`HTTPError`](https://requests.readthedocs.io/en/latest/api/#requests.HTTPError):
                HTTP 404 if the user access request cannot be found.
            [`HTTPError`](https://requests.readthedocs.io/en/latest/api/#requests.HTTPError):
                HTTP 404 if the user access request is already in the accepted list.
        """
        self._handle_access_request(repo_id, user, "accepted", repo_type=repo_type, token=token)

    @validate_hf_hub_args
    def reject_access_request(
        self,
        repo_id: str,
        user: str,
        *,
        repo_type: Optional[str] = None,
        rejection_reason: Optional[str],
        token: Union[bool, str, None] = None,
    ) -> None:
        """
        Reject an access request from a user for a given gated repo.

        A rejected request will go to the rejected list. The user cannot download any file of the repo. Rejected
        requests can be accepted or cancelled at any time using [`accept_access_request`] and [`cancel_access_request`].
        A cancelled request will go back to the pending list while an accepted request will go to the accepted list.

        For more info about gated repos, see https://huggingface.co/docs/hub/models-gated.

        Args:
            repo_id (`str`):
                The id of the repo to reject access request for.
            user (`str`):
                The username of the user which access request should be rejected.
            repo_type (`str`, *optional*):
                The type of the repo to reject access request for. Must be one of `model`, `dataset` or `space`.
                Defaults to `model`.
            rejection_reason (`str`, *optional*):
                Optional rejection reason that will be visible to the user (max 200 characters).
            token (Union[bool, str, None], optional):
                A valid user access token (string). Defaults to the locally saved
                token, which is the recommended method for authentication (see
                https://huggingface.co/docs/huggingface_hub/quick-start#authentication).
                To disable authentication, pass `False`.

        Raises:
            [`HTTPError`](https://requests.readthedocs.io/en/latest/api/#requests.HTTPError):
                HTTP 400 if the repo is not gated.
            [`HTTPError`](https://requests.readthedocs.io/en/latest/api/#requests.HTTPError):
                HTTP 403 if you only have read-only access to the repo. This can be the case if you don't have `write`
                or `admin` role in the organization the repo belongs to or if you passed a `read` token.
            [`HTTPError`](https://requests.readthedocs.io/en/latest/api/#requests.HTTPError):
                HTTP 404 if the user does not exist on the Hub.
            [`HTTPError`](https://requests.readthedocs.io/en/latest/api/#requests.HTTPError):
                HTTP 404 if the user access request cannot be found.
            [`HTTPError`](https://requests.readthedocs.io/en/latest/api/#requests.HTTPError):
                HTTP 404 if the user access request is already in the rejected list.
        """
        self._handle_access_request(
            repo_id, user, "rejected", repo_type=repo_type, rejection_reason=rejection_reason, token=token
        )

    @validate_hf_hub_args
    def _handle_access_request(
        self,
        repo_id: str,
        user: str,
        status: Literal["accepted", "rejected", "pending"],
        repo_type: Optional[str] = None,
        rejection_reason: Optional[str] = None,
        token: Union[bool, str, None] = None,
    ) -> None:
        if repo_type not in constants.REPO_TYPES:
            raise ValueError(f"Invalid repo type, must be one of {constants.REPO_TYPES}")
        if repo_type is None:
            repo_type = constants.REPO_TYPE_MODEL

        payload = {"user": user, "status": status}

        if rejection_reason is not None:
            if status != "rejected":
                raise ValueError("`rejection_reason` can only be passed when rejecting an access request.")
            payload["rejectionReason"] = rejection_reason

        response = get_session().post(
            f"{constants.ENDPOINT}/api/{repo_type}s/{repo_id}/user-access-request/handle",
            headers=self._build_hf_headers(token=token),
            json=payload,
        )
        hf_raise_for_status(response)

    @validate_hf_hub_args
    def grant_access(
        self, repo_id: str, user: str, *, repo_type: Optional[str] = None, token: Union[bool, str, None] = None
    ) -> None:
        """
        Grant access to a user for a given gated repo.

        Granting access don't require for the user to send an access request by themselves. The user is automatically
        added to the accepted list meaning they can download the files You can revoke the granted access at any time
        using [`cancel_access_request`] or [`reject_access_request`].

        For more info about gated repos, see https://huggingface.co/docs/hub/models-gated.

        Args:
            repo_id (`str`):
                The id of the repo to grant access to.
            user (`str`):
                The username of the user to grant access.
            repo_type (`str`, *optional*):
                The type of the repo to grant access to. Must be one of `model`, `dataset` or `space`.
                Defaults to `model`.
            token (Union[bool, str, None], optional):
                A valid user access token (string). Defaults to the locally saved
                token, which is the recommended method for authentication (see
                https://huggingface.co/docs/huggingface_hub/quick-start#authentication).
                To disable authentication, pass `False`.

        Raises:
            [`HTTPError`](https://requests.readthedocs.io/en/latest/api/#requests.HTTPError):
                HTTP 400 if the repo is not gated.
            [`HTTPError`](https://requests.readthedocs.io/en/latest/api/#requests.HTTPError):
                HTTP 400 if the user already has access to the repo.
            [`HTTPError`](https://requests.readthedocs.io/en/latest/api/#requests.HTTPError):
                HTTP 403 if you only have read-only access to the repo. This can be the case if you don't have `write`
                or `admin` role in the organization the repo belongs to or if you passed a `read` token.
            [`HTTPError`](https://requests.readthedocs.io/en/latest/api/#requests.HTTPError):
                HTTP 404 if the user does not exist on the Hub.
        """
        if repo_type not in constants.REPO_TYPES:
            raise ValueError(f"Invalid repo type, must be one of {constants.REPO_TYPES}")
        if repo_type is None:
            repo_type = constants.REPO_TYPE_MODEL

        response = get_session().post(
            f"{constants.ENDPOINT}/api/{repo_type}s/{repo_id}/user-access-request/grant",
            headers=self._build_hf_headers(token=token),
            json={"user": user},
        )
        hf_raise_for_status(response)
        return response.json()

    ###################
    # Manage webhooks #
    ###################

    @validate_hf_hub_args
    def get_webhook(self, webhook_id: str, *, token: Union[bool, str, None] = None) -> WebhookInfo:
        """Get a webhook by its id.

        Args:
            webhook_id (`str`):
                The unique identifier of the webhook to get.
            token (Union[bool, str, None], optional):
                A valid user access token (string). Defaults to the locally saved token, which is the recommended
                method for authentication (see https://huggingface.co/docs/huggingface_hub/quick-start#authentication).
                To disable authentication, pass `False`.

        Returns:
            [`WebhookInfo`]:
                Info about the webhook.

        Example:
            ```python
            >>> from huggingface_hub import get_webhook
            >>> webhook = get_webhook("654bbbc16f2ec14d77f109cc")
            >>> print(webhook)
            WebhookInfo(
                id="654bbbc16f2ec14d77f109cc",
                watched=[WebhookWatchedItem(type="user", name="julien-c"), WebhookWatchedItem(type="org", name="HuggingFaceH4")],
                url="https://webhook.site/a2176e82-5720-43ee-9e06-f91cb4c91548",
                secret="my-secret",
                domains=["repo", "discussion"],
                disabled=False,
            )
            ```
        """
        response = get_session().get(
            f"{constants.ENDPOINT}/api/settings/webhooks/{webhook_id}",
            headers=self._build_hf_headers(token=token),
        )
        hf_raise_for_status(response)
        webhook_data = response.json()["webhook"]

        watched_items = [WebhookWatchedItem(type=item["type"], name=item["name"]) for item in webhook_data["watched"]]

        webhook = WebhookInfo(
            id=webhook_data["id"],
            url=webhook_data["url"],
            watched=watched_items,
            domains=webhook_data["domains"],
            secret=webhook_data.get("secret"),
            disabled=webhook_data["disabled"],
        )

        return webhook

    @validate_hf_hub_args
    def list_webhooks(self, *, token: Union[bool, str, None] = None) -> List[WebhookInfo]:
        """List all configured webhooks.

        Args:
            token (Union[bool, str, None], optional):
                A valid user access token (string). Defaults to the locally saved token, which is the recommended
                method for authentication (see https://huggingface.co/docs/huggingface_hub/quick-start#authentication).
                To disable authentication, pass `False`.

        Returns:
            `List[WebhookInfo]`:
                List of webhook info objects.

        Example:
            ```python
            >>> from huggingface_hub import list_webhooks
            >>> webhooks = list_webhooks()
            >>> len(webhooks)
            2
            >>> webhooks[0]
            WebhookInfo(
                id="654bbbc16f2ec14d77f109cc",
                watched=[WebhookWatchedItem(type="user", name="julien-c"), WebhookWatchedItem(type="org", name="HuggingFaceH4")],
                url="https://webhook.site/a2176e82-5720-43ee-9e06-f91cb4c91548",
                secret="my-secret",
                domains=["repo", "discussion"],
                disabled=False,
            )
            ```
        """
        response = get_session().get(
            f"{constants.ENDPOINT}/api/settings/webhooks",
            headers=self._build_hf_headers(token=token),
        )
        hf_raise_for_status(response)
        webhooks_data = response.json()

        return [
            WebhookInfo(
                id=webhook["id"],
                url=webhook["url"],
                watched=[WebhookWatchedItem(type=item["type"], name=item["name"]) for item in webhook["watched"]],
                domains=webhook["domains"],
                secret=webhook.get("secret"),
                disabled=webhook["disabled"],
            )
            for webhook in webhooks_data
        ]

    @validate_hf_hub_args
    def create_webhook(
        self,
        *,
        url: str,
        watched: List[Union[Dict, WebhookWatchedItem]],
        domains: Optional[List[constants.WEBHOOK_DOMAIN_T]] = None,
        secret: Optional[str] = None,
        token: Union[bool, str, None] = None,
    ) -> WebhookInfo:
        """Create a new webhook.

        Args:
            url (`str`):
                URL to send the payload to.
            watched (`List[WebhookWatchedItem]`):
                List of [`WebhookWatchedItem`] to be watched by the webhook. It can be users, orgs, models, datasets or spaces.
                Watched items can also be provided as plain dictionaries.
            domains (`List[Literal["repo", "discussion"]]`, optional):
                List of domains to watch. It can be "repo", "discussion" or both.
            secret (`str`, optional):
                A secret to sign the payload with.
            token (Union[bool, str, None], optional):
                A valid user access token (string). Defaults to the locally saved token, which is the recommended
                method for authentication (see https://huggingface.co/docs/huggingface_hub/quick-start#authentication).
                To disable authentication, pass `False`.

        Returns:
            [`WebhookInfo`]:
                Info about the newly created webhook.

        Example:
            ```python
            >>> from huggingface_hub import create_webhook
            >>> payload = create_webhook(
            ...     watched=[{"type": "user", "name": "julien-c"}, {"type": "org", "name": "HuggingFaceH4"}],
            ...     url="https://webhook.site/a2176e82-5720-43ee-9e06-f91cb4c91548",
            ...     domains=["repo", "discussion"],
            ...     secret="my-secret",
            ... )
            >>> print(payload)
            WebhookInfo(
                id="654bbbc16f2ec14d77f109cc",
                url="https://webhook.site/a2176e82-5720-43ee-9e06-f91cb4c91548",
                watched=[WebhookWatchedItem(type="user", name="julien-c"), WebhookWatchedItem(type="org", name="HuggingFaceH4")],
                domains=["repo", "discussion"],
                secret="my-secret",
                disabled=False,
            )
            ```
        """
        watched_dicts = [asdict(item) if isinstance(item, WebhookWatchedItem) else item for item in watched]

        response = get_session().post(
            f"{constants.ENDPOINT}/api/settings/webhooks",
            json={"watched": watched_dicts, "url": url, "domains": domains, "secret": secret},
            headers=self._build_hf_headers(token=token),
        )
        hf_raise_for_status(response)
        webhook_data = response.json()["webhook"]
        watched_items = [WebhookWatchedItem(type=item["type"], name=item["name"]) for item in webhook_data["watched"]]

        webhook = WebhookInfo(
            id=webhook_data["id"],
            url=webhook_data["url"],
            watched=watched_items,
            domains=webhook_data["domains"],
            secret=webhook_data.get("secret"),
            disabled=webhook_data["disabled"],
        )

        return webhook

    @validate_hf_hub_args
    def update_webhook(
        self,
        webhook_id: str,
        *,
        url: Optional[str] = None,
        watched: Optional[List[Union[Dict, WebhookWatchedItem]]] = None,
        domains: Optional[List[constants.WEBHOOK_DOMAIN_T]] = None,
        secret: Optional[str] = None,
        token: Union[bool, str, None] = None,
    ) -> WebhookInfo:
        """Update an existing webhook.

        Args:
            webhook_id (`str`):
                The unique identifier of the webhook to be updated.
            url (`str`, optional):
                The URL to which the payload will be sent.
            watched (`List[WebhookWatchedItem]`, optional):
                List of items to watch. It can be users, orgs, models, datasets, or spaces.
                Refer to [`WebhookWatchedItem`] for more details. Watched items can also be provided as plain dictionaries.
            domains (`List[Literal["repo", "discussion"]]`, optional):
                The domains to watch. This can include "repo", "discussion", or both.
            secret (`str`, optional):
                A secret to sign the payload with, providing an additional layer of security.
            token (Union[bool, str, None], optional):
                A valid user access token (string). Defaults to the locally saved token, which is the recommended
                method for authentication (see https://huggingface.co/docs/huggingface_hub/quick-start#authentication).
                To disable authentication, pass `False`.

        Returns:
            [`WebhookInfo`]:
                Info about the updated webhook.

        Example:
            ```python
            >>> from huggingface_hub import update_webhook
            >>> updated_payload = update_webhook(
            ...     webhook_id="654bbbc16f2ec14d77f109cc",
            ...     url="https://new.webhook.site/a2176e82-5720-43ee-9e06-f91cb4c91548",
            ...     watched=[{"type": "user", "name": "julien-c"}, {"type": "org", "name": "HuggingFaceH4"}],
            ...     domains=["repo"],
            ...     secret="my-secret",
            ... )
            >>> print(updated_payload)
            WebhookInfo(
                id="654bbbc16f2ec14d77f109cc",
                url="https://new.webhook.site/a2176e82-5720-43ee-9e06-f91cb4c91548",
                watched=[WebhookWatchedItem(type="user", name="julien-c"), WebhookWatchedItem(type="org", name="HuggingFaceH4")],
                domains=["repo"],
                secret="my-secret",
                disabled=False,
            ```
        """
        if watched is None:
            watched = []
        watched_dicts = [asdict(item) if isinstance(item, WebhookWatchedItem) else item for item in watched]

        response = get_session().post(
            f"{constants.ENDPOINT}/api/settings/webhooks/{webhook_id}",
            json={"watched": watched_dicts, "url": url, "domains": domains, "secret": secret},
            headers=self._build_hf_headers(token=token),
        )
        hf_raise_for_status(response)
        webhook_data = response.json()["webhook"]

        watched_items = [WebhookWatchedItem(type=item["type"], name=item["name"]) for item in webhook_data["watched"]]

        webhook = WebhookInfo(
            id=webhook_data["id"],
            url=webhook_data["url"],
            watched=watched_items,
            domains=webhook_data["domains"],
            secret=webhook_data.get("secret"),
            disabled=webhook_data["disabled"],
        )

        return webhook

    @validate_hf_hub_args
    def enable_webhook(self, webhook_id: str, *, token: Union[bool, str, None] = None) -> WebhookInfo:
        """Enable a webhook (makes it "active").

        Args:
            webhook_id (`str`):
                The unique identifier of the webhook to enable.
            token (Union[bool, str, None], optional):
                A valid user access token (string). Defaults to the locally saved token, which is the recommended
                method for authentication (see https://huggingface.co/docs/huggingface_hub/quick-start#authentication).
                To disable authentication, pass `False`.

        Returns:
            [`WebhookInfo`]:
                Info about the enabled webhook.

        Example:
            ```python
            >>> from huggingface_hub import enable_webhook
            >>> enabled_webhook = enable_webhook("654bbbc16f2ec14d77f109cc")
            >>> enabled_webhook
            WebhookInfo(
                id="654bbbc16f2ec14d77f109cc",
                url="https://webhook.site/a2176e82-5720-43ee-9e06-f91cb4c91548",
                watched=[WebhookWatchedItem(type="user", name="julien-c"), WebhookWatchedItem(type="org", name="HuggingFaceH4")],
                domains=["repo", "discussion"],
                secret="my-secret",
                disabled=False,
            )
            ```
        """
        response = get_session().post(
            f"{constants.ENDPOINT}/api/settings/webhooks/{webhook_id}/enable",
            headers=self._build_hf_headers(token=token),
        )
        hf_raise_for_status(response)
        webhook_data = response.json()["webhook"]

        watched_items = [WebhookWatchedItem(type=item["type"], name=item["name"]) for item in webhook_data["watched"]]

        webhook = WebhookInfo(
            id=webhook_data["id"],
            url=webhook_data["url"],
            watched=watched_items,
            domains=webhook_data["domains"],
            secret=webhook_data.get("secret"),
            disabled=webhook_data["disabled"],
        )

        return webhook

    @validate_hf_hub_args
    def disable_webhook(self, webhook_id: str, *, token: Union[bool, str, None] = None) -> WebhookInfo:
        """Disable a webhook (makes it "disabled").

        Args:
            webhook_id (`str`):
                The unique identifier of the webhook to disable.
            token (Union[bool, str, None], optional):
                A valid user access token (string). Defaults to the locally saved token, which is the recommended
                method for authentication (see https://huggingface.co/docs/huggingface_hub/quick-start#authentication).
                To disable authentication, pass `False`.

        Returns:
            [`WebhookInfo`]:
                Info about the disabled webhook.

        Example:
            ```python
            >>> from huggingface_hub import disable_webhook
            >>> disabled_webhook = disable_webhook("654bbbc16f2ec14d77f109cc")
            >>> disabled_webhook
            WebhookInfo(
                id="654bbbc16f2ec14d77f109cc",
                url="https://webhook.site/a2176e82-5720-43ee-9e06-f91cb4c91548",
                watched=[WebhookWatchedItem(type="user", name="julien-c"), WebhookWatchedItem(type="org", name="HuggingFaceH4")],
                domains=["repo", "discussion"],
                secret="my-secret",
                disabled=True,
            )
            ```
        """
        response = get_session().post(
            f"{constants.ENDPOINT}/api/settings/webhooks/{webhook_id}/disable",
            headers=self._build_hf_headers(token=token),
        )
        hf_raise_for_status(response)
        webhook_data = response.json()["webhook"]

        watched_items = [WebhookWatchedItem(type=item["type"], name=item["name"]) for item in webhook_data["watched"]]

        webhook = WebhookInfo(
            id=webhook_data["id"],
            url=webhook_data["url"],
            watched=watched_items,
            domains=webhook_data["domains"],
            secret=webhook_data.get("secret"),
            disabled=webhook_data["disabled"],
        )

        return webhook

    @validate_hf_hub_args
    def delete_webhook(self, webhook_id: str, *, token: Union[bool, str, None] = None) -> None:
        """Delete a webhook.

        Args:
            webhook_id (`str`):
                The unique identifier of the webhook to delete.
            token (Union[bool, str, None], optional):
                A valid user access token (string). Defaults to the locally saved token, which is the recommended
                method for authentication (see https://huggingface.co/docs/huggingface_hub/quick-start#authentication).
                To disable authentication, pass `False`.

        Returns:
            `None`

        Example:
            ```python
            >>> from huggingface_hub import delete_webhook
            >>> delete_webhook("654bbbc16f2ec14d77f109cc")
            ```
        """
        response = get_session().delete(
            f"{constants.ENDPOINT}/api/settings/webhooks/{webhook_id}",
            headers=self._build_hf_headers(token=token),
        )
        hf_raise_for_status(response)

    #############
    # Internals #
    #############

    def _build_hf_headers(
        self,
        token: Union[bool, str, None] = None,
        library_name: Optional[str] = None,
        library_version: Optional[str] = None,
        user_agent: Union[Dict, str, None] = None,
    ) -> Dict[str, str]:
        """
        Alias for [`build_hf_headers`] that uses the token from [`HfApi`] client
        when `token` is not provided.
        """
        if token is None:
            # Cannot do `token = token or self.token` as token can be `False`.
            token = self.token
        return build_hf_headers(
            token=token,
            library_name=library_name or self.library_name,
            library_version=library_version or self.library_version,
            user_agent=user_agent or self.user_agent,
            headers=self.headers,
        )

    def _prepare_folder_deletions(
        self,
        repo_id: str,
        repo_type: Optional[str],
        revision: Optional[str],
        path_in_repo: str,
        delete_patterns: Optional[Union[List[str], str]],
        token: Union[bool, str, None] = None,
    ) -> List[CommitOperationDelete]:
        """Generate the list of Delete operations for a commit to delete files from a repo.

        List remote files and match them against the `delete_patterns` constraints. Returns a list of [`CommitOperationDelete`]
        with the matching items.

        Note: `.gitattributes` file is essential to make a repo work properly on the Hub. This file will always be
              kept even if it matches the `delete_patterns` constraints.
        """
        if delete_patterns is None:
            # If no delete patterns, no need to list and filter remote files
            return []

        # List remote files
        filenames = self.list_repo_files(repo_id=repo_id, revision=revision, repo_type=repo_type, token=token)

        # Compute relative path in repo
        if path_in_repo and path_in_repo not in (".", "./"):
            path_in_repo = path_in_repo.strip("/") + "/"  # harmonize
            relpath_to_abspath = {
                file[len(path_in_repo) :]: file for file in filenames if file.startswith(path_in_repo)
            }
        else:
            relpath_to_abspath = {file: file for file in filenames}

        # Apply filter on relative paths and return
        return [
            CommitOperationDelete(path_in_repo=relpath_to_abspath[relpath], is_folder=False)
            for relpath in filter_repo_objects(relpath_to_abspath.keys(), allow_patterns=delete_patterns)
            if relpath_to_abspath[relpath] != ".gitattributes"
        ]

    def _prepare_upload_folder_additions(
        self,
        folder_path: Union[str, Path],
        path_in_repo: str,
        allow_patterns: Optional[Union[List[str], str]] = None,
        ignore_patterns: Optional[Union[List[str], str]] = None,
        repo_type: Optional[str] = None,
        token: Union[bool, str, None] = None,
    ) -> List[CommitOperationAdd]:
        """Generate the list of Add operations for a commit to upload a folder.

        Files not matching the `allow_patterns` (allowlist) and `ignore_patterns` (denylist)
        constraints are discarded.
        """

        folder_path = Path(folder_path).expanduser().resolve()
        if not folder_path.is_dir():
            raise ValueError(f"Provided path: '{folder_path}' is not a directory")

        # List files from folder
        relpath_to_abspath = {
            path.relative_to(folder_path).as_posix(): path
            for path in sorted(folder_path.glob("**/*"))  # sorted to be deterministic
            if path.is_file()
        }

        # Filter files
        # Patterns are applied on the path relative to `folder_path`. `path_in_repo` is prefixed after the filtering.
        filtered_repo_objects = list(
            filter_repo_objects(
                relpath_to_abspath.keys(), allow_patterns=allow_patterns, ignore_patterns=ignore_patterns
            )
        )

        prefix = f"{path_in_repo.strip('/')}/" if path_in_repo else ""

        # If updating a README.md file, make sure the metadata format is valid
        # It's better to fail early than to fail after all the files have been hashed.
        if "README.md" in filtered_repo_objects:
            self._validate_yaml(
                content=relpath_to_abspath["README.md"].read_text(encoding="utf8"),
                repo_type=repo_type,
                token=token,
            )
        if len(filtered_repo_objects) > 30:
            log = logger.warning if len(filtered_repo_objects) > 200 else logger.info
            log(
                "It seems you are trying to upload a large folder at once. This might take some time and then fail if "
                "the folder is too large. For such cases, it is recommended to upload in smaller batches or to use "
                "`HfApi().upload_large_folder(...)`/`huggingface-cli upload-large-folder` instead. For more details, "
                "check out https://huggingface.co/docs/huggingface_hub/main/en/guides/upload#upload-a-large-folder."
            )

        logger.info(f"Start hashing {len(filtered_repo_objects)} files.")
        operations = [
            CommitOperationAdd(
                path_or_fileobj=relpath_to_abspath[relpath],  # absolute path on disk
                path_in_repo=prefix + relpath,  # "absolute" path in repo
            )
            for relpath in filtered_repo_objects
        ]
        logger.info(f"Finished hashing {len(filtered_repo_objects)} files.")
        return operations

    def _validate_yaml(self, content: str, *, repo_type: Optional[str] = None, token: Union[bool, str, None] = None):
        """
        Validate YAML from `README.md`, used before file hashing and upload.

        Args:
            content (`str`):
                Content of `README.md` to validate.
            repo_type (`str`, *optional*):
                The type of the repo to grant access to. Must be one of `model`, `dataset` or `space`.
                Defaults to `model`.
            token (Union[bool, str, None], optional):
                A valid user access token (string). Defaults to the locally saved
                token, which is the recommended method for authentication (see
                https://huggingface.co/docs/huggingface_hub/quick-start#authentication).
                To disable authentication, pass `False`.

        Raises:
            - [`ValueError`](https://docs.python.org/3/library/exceptions.html#ValueError)
              if YAML is invalid
        """
        repo_type = repo_type if repo_type is not None else constants.REPO_TYPE_MODEL
        headers = self._build_hf_headers(token=token)

        response = get_session().post(
            f"{self.endpoint}/api/validate-yaml",
            json={"content": content, "repoType": repo_type},
            headers=headers,
        )
        # Handle warnings (example: empty metadata)
        response_content = response.json()
        message = "\n".join([f"- {warning.get('message')}" for warning in response_content.get("warnings", [])])
        if message:
            warnings.warn(f"Warnings while validating metadata in README.md:\n{message}")

        # Raise on errors
        try:
            hf_raise_for_status(response)
        except BadRequestError as e:
            errors = response_content.get("errors", [])
            message = "\n".join([f"- {error.get('message')}" for error in errors])
            raise ValueError(f"Invalid metadata in README.md.\n{message}") from e

    def get_user_overview(self, username: str, token: Union[bool, str, None] = None) -> User:
        """
        Get an overview of a user on the Hub.

        Args:
            username (`str`):
                Username of the user to get an overview of.
            token (Union[bool, str, None], optional):
                A valid user access token (string). Defaults to the locally saved
                token, which is the recommended method for authentication (see
                https://huggingface.co/docs/huggingface_hub/quick-start#authentication).
                To disable authentication, pass `False`.

        Returns:
            `User`: A [`User`] object with the user's overview.

        Raises:
            [`HTTPError`](https://requests.readthedocs.io/en/latest/api/#requests.HTTPError):
                HTTP 404 If the user does not exist on the Hub.
        """
        r = get_session().get(
            f"{constants.ENDPOINT}/api/users/{username}/overview", headers=self._build_hf_headers(token=token)
        )
        hf_raise_for_status(r)
        return User(**r.json())

    def list_organization_members(self, organization: str, token: Union[bool, str, None] = None) -> Iterable[User]:
        """
        List of members of an organization on the Hub.

        Args:
            organization (`str`):
                Name of the organization to get the members of.
            token (Union[bool, str, None], optional):
                A valid user access token (string). Defaults to the locally saved
                token, which is the recommended method for authentication (see
                https://huggingface.co/docs/huggingface_hub/quick-start#authentication).
                To disable authentication, pass `False`.

        Returns:
            `Iterable[User]`: A list of [`User`] objects with the members of the organization.

        Raises:
            [`HTTPError`](https://requests.readthedocs.io/en/latest/api/#requests.HTTPError):
                HTTP 404 If the organization does not exist on the Hub.

        """
        for member in paginate(
            path=f"{constants.ENDPOINT}/api/organizations/{organization}/members",
            params={},
            headers=self._build_hf_headers(token=token),
        ):
            yield User(**member)

    def list_user_followers(self, username: str, token: Union[bool, str, None] = None) -> Iterable[User]:
        """
        Get the list of followers of a user on the Hub.

        Args:
            username (`str`):
                Username of the user to get the followers of.
            token (Union[bool, str, None], optional):
                A valid user access token (string). Defaults to the locally saved
                token, which is the recommended method for authentication (see
                https://huggingface.co/docs/huggingface_hub/quick-start#authentication).
                To disable authentication, pass `False`.

        Returns:
            `Iterable[User]`: A list of [`User`] objects with the followers of the user.

        Raises:
            [`HTTPError`](https://requests.readthedocs.io/en/latest/api/#requests.HTTPError):
                HTTP 404 If the user does not exist on the Hub.

        """
        for follower in paginate(
            path=f"{constants.ENDPOINT}/api/users/{username}/followers",
            params={},
            headers=self._build_hf_headers(token=token),
        ):
            yield User(**follower)

    def list_user_following(self, username: str, token: Union[bool, str, None] = None) -> Iterable[User]:
        """
        Get the list of users followed by a user on the Hub.

        Args:
            username (`str`):
                Username of the user to get the users followed by.
            token (Union[bool, str, None], optional):
                A valid user access token (string). Defaults to the locally saved
                token, which is the recommended method for authentication (see
                https://huggingface.co/docs/huggingface_hub/quick-start#authentication).
                To disable authentication, pass `False`.

        Returns:
            `Iterable[User]`: A list of [`User`] objects with the users followed by the user.

        Raises:
            [`HTTPError`](https://requests.readthedocs.io/en/latest/api/#requests.HTTPError):
                HTTP 404 If the user does not exist on the Hub.

        """
        for followed_user in paginate(
            path=f"{constants.ENDPOINT}/api/users/{username}/following",
            params={},
            headers=self._build_hf_headers(token=token),
        ):
            yield User(**followed_user)

    def list_papers(
        self,
        *,
        query: Optional[str] = None,
        token: Union[bool, str, None] = None,
    ) -> Iterable[PaperInfo]:
        """
        List daily papers on the Hugging Face Hub given a search query.

        Args:
            query (`str`, *optional*):
                A search query string to find papers.
                If provided, returns papers that match the query.
            token (Union[bool, str, None], *optional*):
                A valid user access token (string). Defaults to the locally saved
                token, which is the recommended method for authentication (see
                https://huggingface.co/docs/huggingface_hub/quick-start#authentication).
                To disable authentication, pass `False`.

        Returns:
            `Iterable[PaperInfo]`: an iterable of [`huggingface_hub.hf_api.PaperInfo`] objects.

        Example:

        ```python
        >>> from huggingface_hub import HfApi

        >>> api = HfApi()

        # List all papers with "attention" in their title
        >>> api.list_papers(query="attention")
        ```
        """
        path = f"{self.endpoint}/api/papers/search"
        params = {}
        if query:
            params["q"] = query
        r = get_session().get(
            path,
            params=params,
            headers=self._build_hf_headers(token=token),
        )
        hf_raise_for_status(r)
        for paper in r.json():
            yield PaperInfo(**paper)

    def paper_info(self, id: str) -> PaperInfo:
        """
        Get information for a paper on the Hub.

        Args:
            id (`str`, **optional**):
                ArXiv id of the paper.

        Returns:
            `PaperInfo`: A `PaperInfo` object.

        Raises:
            [`HTTPError`](https://requests.readthedocs.io/en/latest/api/#requests.HTTPError):
                HTTP 404 If the paper does not exist on the Hub.
        """
        path = f"{self.endpoint}/api/papers/{id}"
        r = get_session().get(path)
        hf_raise_for_status(r)
        return PaperInfo(**r.json())

    def auth_check(
        self, repo_id: str, *, repo_type: Optional[str] = None, token: Union[bool, str, None] = None
    ) -> None:
        """
        Check if the provided user token has access to a specific repository on the Hugging Face Hub.

        This method verifies whether the user, authenticated via the provided token, has access to the specified
        repository. If the repository is not found or if the user lacks the required permissions to access it,
        the method raises an appropriate exception.

        Args:
            repo_id (`str`):
                The repository to check for access. Format should be `"user/repo_name"`.
                Example: `"user/my-cool-model"`.

            repo_type (`str`, *optional*):
                The type of the repository. Should be one of `"model"`, `"dataset"`, or `"space"`.
                If not specified, the default is `"model"`.

            token `(Union[bool, str, None]`, *optional*):
                A valid user access token. If not provided, the locally saved token will be used, which is the
                recommended authentication method. Set to `False` to disable authentication.
                Refer to: https://huggingface.co/docs/huggingface_hub/quick-start#authentication.

        Raises:
            [`~utils.RepositoryNotFoundError`]:
                Raised if the repository does not exist, is private, or the user does not have access. This can
                occur if the `repo_id` or `repo_type` is incorrect or if the repository is private but the user
                is not authenticated.

            [`~utils.GatedRepoError`]:
                Raised if the repository exists but is gated and the user is not authorized to access it.

        Example:
            Check if the user has access to a repository:

            ```python
            >>> from huggingface_hub import auth_check
            >>> from huggingface_hub.utils import GatedRepoError, RepositoryNotFoundError

            try:
                auth_check("user/my-cool-model")
            except GatedRepoError:
                # Handle gated repository error
                print("You do not have permission to access this gated repository.")
            except RepositoryNotFoundError:
                # Handle repository not found error
                print("The repository was not found or you do not have access.")
            ```

            In this example:
            - If the user has access, the method completes successfully.
            - If the repository is gated or does not exist, appropriate exceptions are raised, allowing the user
            to handle them accordingly.
        """
        headers = self._build_hf_headers(token=token)
        if repo_type is None:
            repo_type = constants.REPO_TYPE_MODEL
        if repo_type not in constants.REPO_TYPES:
            raise ValueError(f"Invalid repo type, must be one of {constants.REPO_TYPES}")
        path = f"{self.endpoint}/api/{repo_type}s/{repo_id}/auth-check"
        r = get_session().get(path, headers=headers)
        hf_raise_for_status(r)


def _parse_revision_from_pr_url(pr_url: str) -> str:
    """Safely parse revision number from a PR url.

    Example:
    ```py
    >>> _parse_revision_from_pr_url("https://huggingface.co/bigscience/bloom/discussions/2")
    "refs/pr/2"
    ```
    """
    re_match = re.match(_REGEX_DISCUSSION_URL, pr_url)
    if re_match is None:
        raise RuntimeError(f"Unexpected response from the hub, expected a Pull Request URL but got: '{pr_url}'")
    return f"refs/pr/{re_match[1]}"


api = HfApi()

whoami = api.whoami
auth_check = api.auth_check
get_token_permission = api.get_token_permission

list_models = api.list_models
model_info = api.model_info

list_datasets = api.list_datasets
dataset_info = api.dataset_info

list_spaces = api.list_spaces
space_info = api.space_info

list_papers = api.list_papers
paper_info = api.paper_info

repo_exists = api.repo_exists
revision_exists = api.revision_exists
file_exists = api.file_exists
repo_info = api.repo_info
list_repo_files = api.list_repo_files
list_repo_refs = api.list_repo_refs
list_repo_commits = api.list_repo_commits
list_repo_tree = api.list_repo_tree
get_paths_info = api.get_paths_info

get_model_tags = api.get_model_tags
get_dataset_tags = api.get_dataset_tags

create_commit = api.create_commit
create_repo = api.create_repo
delete_repo = api.delete_repo
update_repo_visibility = api.update_repo_visibility
update_repo_settings = api.update_repo_settings
move_repo = api.move_repo
upload_file = api.upload_file
upload_folder = api.upload_folder
delete_file = api.delete_file
delete_folder = api.delete_folder
delete_files = api.delete_files
upload_large_folder = api.upload_large_folder
preupload_lfs_files = api.preupload_lfs_files
create_branch = api.create_branch
delete_branch = api.delete_branch
create_tag = api.create_tag
delete_tag = api.delete_tag
get_full_repo_name = api.get_full_repo_name

# Danger-zone API
super_squash_history = api.super_squash_history
list_lfs_files = api.list_lfs_files
permanently_delete_lfs_files = api.permanently_delete_lfs_files

# Safetensors helpers
get_safetensors_metadata = api.get_safetensors_metadata
parse_safetensors_file_metadata = api.parse_safetensors_file_metadata

# Background jobs
run_as_future = api.run_as_future

# Activity API
list_liked_repos = api.list_liked_repos
list_repo_likers = api.list_repo_likers
unlike = api.unlike

# Community API
get_discussion_details = api.get_discussion_details
get_repo_discussions = api.get_repo_discussions
create_discussion = api.create_discussion
create_pull_request = api.create_pull_request
change_discussion_status = api.change_discussion_status
comment_discussion = api.comment_discussion
edit_discussion_comment = api.edit_discussion_comment
rename_discussion = api.rename_discussion
merge_pull_request = api.merge_pull_request

# Space API
add_space_secret = api.add_space_secret
delete_space_secret = api.delete_space_secret
get_space_variables = api.get_space_variables
add_space_variable = api.add_space_variable
delete_space_variable = api.delete_space_variable
get_space_runtime = api.get_space_runtime
request_space_hardware = api.request_space_hardware
set_space_sleep_time = api.set_space_sleep_time
pause_space = api.pause_space
restart_space = api.restart_space
duplicate_space = api.duplicate_space
request_space_storage = api.request_space_storage
delete_space_storage = api.delete_space_storage

# Inference Endpoint API
list_inference_endpoints = api.list_inference_endpoints
create_inference_endpoint = api.create_inference_endpoint
get_inference_endpoint = api.get_inference_endpoint
update_inference_endpoint = api.update_inference_endpoint
delete_inference_endpoint = api.delete_inference_endpoint
pause_inference_endpoint = api.pause_inference_endpoint
resume_inference_endpoint = api.resume_inference_endpoint
scale_to_zero_inference_endpoint = api.scale_to_zero_inference_endpoint
create_inference_endpoint_from_catalog = api.create_inference_endpoint_from_catalog
list_inference_catalog = api.list_inference_catalog

# Collections API
get_collection = api.get_collection
list_collections = api.list_collections
create_collection = api.create_collection
update_collection_metadata = api.update_collection_metadata
delete_collection = api.delete_collection
add_collection_item = api.add_collection_item
update_collection_item = api.update_collection_item
delete_collection_item = api.delete_collection_item
delete_collection_item = api.delete_collection_item

# Access requests API
list_pending_access_requests = api.list_pending_access_requests
list_accepted_access_requests = api.list_accepted_access_requests
list_rejected_access_requests = api.list_rejected_access_requests
cancel_access_request = api.cancel_access_request
accept_access_request = api.accept_access_request
reject_access_request = api.reject_access_request
grant_access = api.grant_access

# Webhooks API
create_webhook = api.create_webhook
disable_webhook = api.disable_webhook
delete_webhook = api.delete_webhook
enable_webhook = api.enable_webhook
get_webhook = api.get_webhook
list_webhooks = api.list_webhooks
update_webhook = api.update_webhook


# User API
get_user_overview = api.get_user_overview
list_organization_members = api.list_organization_members
list_user_followers = api.list_user_followers
list_user_following = api.list_user_following