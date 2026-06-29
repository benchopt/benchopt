from benchopt.utils.temp_benchmark import temp_benchmark

from benchopt.tests.utils import CaptureCmdOutput

from benchopt.cli.helpers import info


DATASET_WITH_CHOICES = """from benchopt import BaseDataset

    class Dataset(BaseDataset):
        name = "with-choices"
        parameters = {'param': ['a']}

        @classmethod
        def get_all_parameter_values(cls, name):
            if name == 'param':
                return ['a', 'b', 'c']
            return super().get_all_parameter_values(name)

        def get_data(self): return dict(X=0)
"""

DATASET_NO_CHOICES = """from benchopt import BaseDataset

    class Dataset(BaseDataset):
        name = "no-choices"
        parameters = {'param': ['a']}

        def get_data(self): return dict(X=0)
"""


class TestCmdInfo:
    def test_info_lists_choices(self):
        # `benchopt info` lists the values declared by
        # get_all_parameter_values, with a total count.
        with temp_benchmark(datasets=[DATASET_WITH_CHOICES]) as bench:
            with CaptureCmdOutput() as out:
                info(
                    [str(bench.benchmark_dir), '-d', 'with-choices'],
                    'benchopt', standalone_mode=False
                )

        out.check_output("param: a", repetition=1)
        out.check_output(r"valid values: a, b, c \(3 total\)", repetition=1)

    def test_info_no_choices(self):
        # Without the hook, `info` does not print a "valid values" line.
        with temp_benchmark(datasets=[DATASET_NO_CHOICES]) as bench:
            with CaptureCmdOutput() as out:
                info(
                    [str(bench.benchmark_dir), '-d', 'no-choices'],
                    'benchopt', standalone_mode=False
                )

        out.check_output("param: a", repetition=1)
        out.check_output("valid values", repetition=0)
