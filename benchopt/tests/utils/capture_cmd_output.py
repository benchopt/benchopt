import re
from pathlib import Path

from joblib.executor import get_memmapping_executor

from benchopt.utils.suppress_std import SuppressStd


OUTPUT_FILES_PATTERN = [
    # Run command
    r'Saving result in: (.*\.parquet|.*\.csv)',
    # Plot command - no-html
    r'Save .* as: (.*\.pdf)',
    # Plot command - html || generate results
    r'Writing .* to (.*\.html)',
    # Archive command
    r'Results are in (.*\.tar.gz)',
]


class CaptureCmdOutput(object):
    "Context to capture run cmd output and files."

    def __init__(self, delete_result_files=True, exit=None, debug=False):
        self.delete_result_files = delete_result_files
        self.out = SuppressStd(debug=debug)
        self.exit = exit

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
            "CaptureCmdOutput(\n"
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
        self.out.__exit__(None, None, None)

        suppressed = False
        if exc_class is SystemExit:
            if self.exit == value.args[0]:
                suppressed = True
            else:
                raise value.with_traceback(traceback)
        elif self.exit is not None:
            raise RuntimeError(
                "The cmd exited without exception but expected exit code "
                f"{self.exit}."
            )

        self.output_checker = BenchoptCmdOutputProcessor(
            self.out.output, self.delete_result_files
        )

        # If there was an exception, display the output
        if not suppressed and exc_class is not None:
            print(self.output_checker.output)

        return suppressed

    def check_output(self, pattern, repetition=None):
        self.output_checker.check_output(pattern, repetition)


class BenchoptCmdOutputProcessor:
    def __init__(self, output, delete_result_files=True):
        self.output = output

        # Make sure to delete all the result that created by the run command.
        self.result_files = []
        for pat in OUTPUT_FILES_PATTERN:
            self.result_files.extend(
                re.findall(pat, self.output)
            )
        if len(self.result_files) >= 1 and delete_result_files:
            for result_file in self.result_files:
                result_path = Path(result_file)
                self.safe_unlink(result_path)  # remove result file
                result_dir = result_path.parents[0]
                stem = result_path.stem
                for html_file in result_dir.glob(f'*{stem}*.html'):
                    # remove html files associated with this results
                    self.safe_unlink(html_file)

    def safe_unlink(self, file):
        # Avoid error when the file is no present due to conficting names.
        if file.exists():
            file.unlink()

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
