import multiprocessing
import sys
import traceback
from io import StringIO


class TimeoutException(Exception):
    pass


class Process(multiprocessing.Process):
    def __init__(self, *args, **kwargs):
        multiprocessing.Process.__init__(self, *args, **kwargs)
        self._exc_pipe_out, self._exc_pipe_in = multiprocessing.Pipe()
        self._stdout_pipe_out, self._stdout_pipe_in = multiprocessing.Pipe()
        self._exception = None
        self._stdout = None

    def run(self):
        orig_stdout = sys.stdout
        sys.stdout = buffer = StringIO()
        try:
            multiprocessing.Process.run(self)
            self._exc_pipe_in.send(None)
            self._stdout_pipe_in.send(buffer.getvalue().strip())
        except Exception as e:
            tb = traceback.format_exc()
            self._exc_pipe_in.send((e, tb))
        finally:
            sys.stdout = orig_stdout

    @property
    def exception(self):
        if self._exc_pipe_out.poll():
            self._exception = self._exc_pipe_out.recv()
        return self._exception

    @property
    def stdout(self):
        if self._stdout_pipe_out.poll():
            self._stdout = self._stdout_pipe_out.recv()
        return self._stdout


def run_with_time_limit(seconds, callable):
    process = Process(target=callable)
    process.start()
    process.join(seconds)
    if process.exitcode is None:
        process.terminate()
        raise TimeoutException("Code timed out.")
    if process.exception:
        raise process.exception[0]
    return process.stdout
