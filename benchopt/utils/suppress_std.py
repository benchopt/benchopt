# Inspired from the following SO answer
# https://stackoverflow.com/questions/24277488/in-python-how-to-capture-the-stdout-from-a-c-shared-library-to-a-variable/57677370#57677370
import io
import os
import sys
import time
import tempfile
import threading


class SuppressStd(object):
    """Context to capture stderr and stdout at C-level.
    """

    def __init__(self, debug=False):
        self.orig_stdout_fileno = sys.__stdout__.fileno()
        self.orig_stderr_fileno = sys.__stderr__.fileno()
        self.debug = debug
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
        sys.stdout = sys.__stdout__
        sys.stderr = sys.__stderr__

        if self.debug:
            self.should_stop = False
            self.thread = threading.Thread(target=self._debug_output)
            self.thread.start()

        return self

    def _debug_output(self):  # pragma: no cover
        """Thread to output captured stdout in real time."""
        last_pos = 0
        while not self.should_stop:
            cur_pos = os.lseek(self.tfile.fileno(), 0, os.SEEK_END)
            if cur_pos > last_pos:
                os.lseek(self.tfile.fileno(), last_pos, os.SEEK_SET)
                data = os.read(self.tfile.fileno(), cur_pos - last_pos)
                if data:
                    try:
                        os.write(self.orig_stdout_dup, data)
                    except OSError:
                        pass
                last_pos = cur_pos
            else:
                time.sleep(0.05)

        cur_pos = os.lseek(self.tfile.fileno(), 0, os.SEEK_END)
        if last_pos < cur_pos:
            os.lseek(self.tfile.fileno(), last_pos, os.SEEK_SET)
            data = os.read(self.tfile.fileno(), cur_pos - last_pos)
            try:
                os.write(self.orig_stdout_dup, data)
            except OSError:
                pass

    def __exit__(self, exc_class, value, traceback):

        # Make sure to flush stdout and stderr
        print(flush=True)
        print(flush=True, file=sys.stderr)

        # Stop debug thread if any
        if self.debug:
            self.should_stop = True
            self.thread.join()

        # Restore the stdout/stderr object.
        sys.stdout = self.stdout_obj
        sys.stderr = self.stderr_obj

        # Close capture file handle
        os.close(self.orig_stdout_fileno)
        os.close(self.orig_stderr_fileno)

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
