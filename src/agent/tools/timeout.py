import multiprocessing


class TimeoutException(Exception):
    pass


class Process(multiprocessing.Process):
    def __init__(self, *args, **kwargs):
        multiprocessing.Process.__init__(self, *args, **kwargs)
        self._pconn, self._cconn = multiprocessing.Pipe()
        self._exception = None

    def run(self):
        try:
            multiprocessing.Process.run(self)
            self._cconn.send(None)
        except Exception as e:
            self._cconn.send(e)

    @property
    def exception(self):
        if self._pconn.poll():
            self._exception = self._pconn.recv()
        return self._exception


def run_with_time_limit(seconds, callable):
    process = Process(target=callable)
    process.start()
    process.join(seconds)
    if process.exitcode is None:
        process.terminate()
        raise TimeoutException("Code timed out.")
    if process.exception:
        raise process.exception
