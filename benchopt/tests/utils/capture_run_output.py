import re
from pathlib import Path

from joblib.executor import get_memmapping_executor

from benchopt.utils.stream_redirection import SuppressStd


class CaptureRunOutput(object):
    "Context to capture run cmd output and files."

    def __init__(self, delete_result_files=True):
        self.out = SuppressStd()
        self.delete_result_files = delete_result_files

    @property
    def output(self):
        if self.output_checker is None:
            raise RuntimeError(
                "Output not available yet, it will be available after "
                "the context manager is exited."
            )
        return self.output_checker.output

    @property
    def result_files(self):
        if self.output_checker is None:
            raise RuntimeError(
                "Output not available yet, it will be available after "
                "the context manager is exited."
            )
        return self.output_checker.result_files

    def __repr__(self):
        return (
            "CaptureRunOutput(\n"
            f"    result_files={self.result_files}\n"
            f"    output=\"\"\"\n{self.output})\n\"\"\"\n"
            ")"
        )

    def __enter__(self):
        # To make it possible to capture stdout in the child worker, we need
        # to make sure the execturor is spawned in the context so shutdown any
        # existing executor.
        e = get_memmapping_executor(2)
        e.shutdown()

        # Redirect the stdout/stderr fd to temp file
        self.out.__enter__()
        return self

    def __exit__(self, exc_class, value, traceback):
        self.out.__exit__(exc_class, value, traceback)
        self.output_checker = BenchoptRunOutputProcessor(
            self.out.output, self.delete_result_files
        )

        # If there was an exception, display the output
        if exc_class is not None:
            print(self.output_checker.output)

    def check_output(self, pattern, repetition=None):
        self.output_checker.check_output(pattern, repetition)


class BenchoptRunOutputProcessor:
    def __init__(self, output, delete_result_files=True):
        self.output = output

        # Make sure to delete all the result that created by the run command.
        self.result_files = re.findall(
            r'Saving result in: (.*\.parquet|.*\.csv)', self.output
        )
        if len(self.result_files) >= 1 and delete_result_files:
            for result_file in self.result_files:
                result_path = Path(result_file)
                result_path.unlink()  # remove result file
                result_dir = result_path.parents[0]
                stem = result_path.stem
                for html_file in result_dir.glob(f'*{stem}*.html'):
                    # remove html files associated with this results
                    html_file.unlink()

    def check_output(self, pattern, repetition=None):

        output = self.output.replace('\r\n', '\n').replace('\r', '\n')

        # Remove color for matches
        for c in range(30, 38):
            output = output.replace(f"\033[1;{c}m", "")
        output = output.replace("\033[0m", "")

        matches = re.findall(pattern, output)

        if repetition is None:
            assert len(matches) > 0, (
                f"Could not find '{pattern}' in output:\n{output}"
            )
        else:
            assert len(matches) == repetition, (
                f"Found {len(matches)} repetitions instead of {repetition} of "
                f"'{pattern}' in output:\n{output}"
            )
