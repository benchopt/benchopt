from benchopt.plotting.generate_html import plot_benchmark_html
from benchopt.benchmark import Benchmark

from pathlib import Path


DIR_BENCH = "data_resnet"


class PseudoBenchmark:

    def __init__(self):
        self.name = 'generated'

    def get_output_folder(self):
        return Path(DIR_BENCH)


fname = Path(
    f'{DIR_BENCH}/benchmark_resnet_classif_benchopt_run_2022-05-03_10h31m54.csv')

plot_benchmark_html(
    fname,
    benchmark=PseudoBenchmark(),
    kinds={'name': "setting_name", 'config_file': 'config_file',
           'benchmark_name': 'benchmark_name'}
)
