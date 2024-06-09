# Inspired from the following SO answer
# https://stackoverflow.com/questions/24277488/in-python-how-to-capture-the-stdout-from-a-c-shared-library-to-a-variable/57677370#57677370
import io
import os
import sys
import tempfile
from contextlib import contextmanager

if sys.platform == 'win32':
    from colorama import init
    init()


class SuppressStd_class(object):
    """Context to capture stderr and stdout at C-level.
    """

    def __init__(self):
        self.orig_stdout_fileno = sys.__stdout__.fileno()
        self.orig_stderr_fileno = sys.__stderr__.fileno()
        self.output = None

    def __enter__(self):
        # Redirect the stdout/stderr fd to temp file
        self.orig_stdout_dup = os.dup(self.orig_stdout_fileno)
        self.orig_stderr_dup = os.dup(self.orig_stderr_fileno)
        self.tfile = tempfile.TemporaryFile(mode='w+b')
        os.dup2(self.tfile.fileno(), self.orig_stdout_fileno)
        os.dup2(self.tfile.fileno(), self.orig_stderr_fileno)

        # Store the stdout object and replace it by the temp file.
        self.stdout_obj = sys.stdout
        self.stderr_obj = sys.stderr
        sys.stdout = open(self.tfile.fileno(), 'w')
        sys.stderr = open(self.tfile.fileno(), 'w')

        return self

    def __exit__(self, exc_class, value, traceback):

        # Make sure to flush stdout and stderr
        sys.stdout.flush()
        sys.stderr.flush()

        # Restore the stdout/stderr object.
        sys.stdout = self.stdout_obj
        sys.stderr = self.stderr_obj

        # Restore original stderr and stdout
        os.dup2(self.orig_stdout_dup, self.orig_stdout_fileno)
        os.dup2(self.orig_stderr_dup, self.orig_stderr_fileno)

        # Close duplicate file handle.
        os.close(self.orig_stdout_dup)
        os.close(self.orig_stderr_dup)

        # Copy contents of temporary file to the given stream
        self.tfile.flush()
        self.tfile.seek(0, io.SEEK_SET)
        self.output = self.tfile.read().decode()
        self.tfile.close()


@contextmanager
def SuppressStd():
    suppress = SuppressStd_class()
    try:
        suppress.__enter__()
        yield suppress
    finally:
        suppress.__exit__(None, None, None)