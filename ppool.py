"""
A Wrapper around multiprocessing.pool that separates output by worker

Works with both Threads and Processes
"""

import time
import sys
import tempfile
from multiprocessing import pool, RLock, current_process
from threading import current_thread
from contextlib import redirect_stdout


class MultiStdOut:
    """
    Stdout proxy housing multiple streams

    Each thread or process will get it's own stream. The main process will
    always write to the real stdout.
    """
    o_out = sys.stdout
    outs = {}
    lock = RLock()

    def __init__(self, buffered=True, *_ignored):
        self.buffered = buffered

    def __enter__(self):
        with self.lock:
            s_id = self.id
            if not self.buffered or s_id == 'MainThread':
                self.outs[s_id] = self.o_out
            else:
                self.outs[s_id] = tempfile.SpooledTemporaryFile(mode='w+')
        return self

    def __exit__(self, *args):
        self._dump()
        with self.lock:
            del self.outs[self.id]

    @property
    def id(self):
        """
        The id of the current Worker
        """
        if current_process().name == 'MainProcess':
            ret = current_thread()
        else:
            ret = current_process()
        return ret.name

    @property
    def c_out(self):
        """
        The current output stream
        """
        return self.outs[self.id]

    def __getattr__(self, name):
        return getattr(self.o_out, name)

    def write(self, *args, real=False, **kwargs):
        """
        Highjack sys.stdout.write
        """
        with self.lock:
            s_id = self.id
            out = self.o_out if real else self.c_out
            return out.write(*args, **kwargs)

    def _dump(self):
        """
        Write all accumulated output to the real sys.stdout at once
        """
        out = self.c_out
        if out is self.o_out:
            return
        out.seek(0)
        with self.lock:
            # self.o_out.write(self.id + '\n')
            return self.o_out.write(out.read())


class ThreadedCallable:
    def __init__(self, func, buffered=True):
        self.func = func
        self.buffered = buffered

    def __call__(self, *args, **kwargs):
        with MultiStdOut(self.buffered) as out:
            return self.func(*args, **kwargs)

class ProcessCallable(ThreadedCallable):
    def __call__(self, *args, **kwargs):
        with MultiStdOut(self.buffered) as out:
            with redirect_stdout(out):
                return self.func(*args, **kwargs)

def map(func, iterable, threaded=True, fg=False, buffered=True, star=False, **poolargs):
    """
    A replacement for pool.map which can run with either threads or processes
    and can allocate seperate buffers for different workers.
    """
    poolcls = getattr(pool, 'ThreadPool' if threaded else 'Pool')
    poolargs.setdefault('processes', len(iterable))

    if fg:
        poolcls = pool.ThreadPool
        poolargs['processes'] = 1
        buffered = False

    call = ThreadedCallable(func, buffered) if threaded else ProcessCallable(func, buffered)
    with poolcls(**poolargs) as mypool:
        mapfunc = mypool.starmap if star else mypool.map
        with MultiStdOut(buffered) as out:
            with redirect_stdout(out):
                mapfunc(call, iterable)


def _test_func(i):
    import time
    import random
    print(i)
    time.sleep(random.randint(0,3))
    print(i)
    time.sleep(random.randint(0,3))
    print(i)

def _main():
    print("Buffered, Threaded")
    map(_test_func, range(5))

    print("Buffered, Processes")
    map(_test_func, range(5), threaded=False)

    print("Non-buffered, Threaded")
    map(_test_func, range(5), buffered=False)

    print("Non-buffered, Processes")
    map(_test_func, range(5), buffered=False, threaded=False)

    print("Foreground")
    map(_test_func, range(5), fg=True)

if __name__ == "__main__":
    _main()
