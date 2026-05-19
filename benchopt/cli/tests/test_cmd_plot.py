import pytest
from pathlib import Path
import matplotlib.pyplot as plt
from unittest.mock import patch
from contextlib import nullcontext

from benchopt.cli.main import run
from benchopt.cli.process_results import plot
from benchopt.tests.utils import CaptureCmdOutput
from benchopt.utils.temp_benchmark import temp_benchmark

from benchopt.cli.tests.completion_cases import _test_shell_completion
from benchopt.cli.tests.completion_cases import (  # noqa: F401
    bench_completion_cases
)

N_REP = [1, 2, 4]


class TestPlotCmd:
    custom_plot = """
        from benchopt import BasePlot

        class Plot(BasePlot):
            name = "custom_plot"
            type = "scatter"
            options = {
                "dataset": ...,  # Will fetch the dataset names from the df
            }

            def plot(self, df, dataset):
                df = df[(df['dataset_name'] == dataset)]
                return [
                    {
                        "x": (
                            df[(df['solver_name'] == solver)]
                            ["time"].values.tolist()
                        ),
                        "y": (
                            df[(df['solver_name'] == solver)]
                            ["objective_value"].values.tolist()
                        ),
                        "color": [0,0,0,1],
                        "marker": 0,
                        "label": solver,
                    }
                    for solver in df['solver_name'].unique()
                ]

            def get_metadata(self, df, dataset):
                title = f"Custom Plot - {dataset}"
                return {
                    "title": title,
                    "xlabel": "Custom X-axis",
                    "ylabel": "Custom Y-axis",
                }"""

    image_plot = """
        import numpy as np
        from benchopt import BasePlot

        class Plot(BasePlot):
            name = "image_plot"
            type = "image"
            options = {
                "dataset": ...,
            }

            def plot(self, df, dataset):
                return [
                    {
                        "image": np.random.rand(10, 10),
                        "label": "Test Image"
                    },
                    {
                        "image": [np.random.rand(10, 10) for _ in range(2)],
                        "label": "Test GIF"
                    },
                    {
                        "image": np.random.rand(10, 10, 10),
                        "label": "No Image"
                    },
                    {"image": None, "label": "No Image"},
                    {"image": "not_an_array", "label": "Bad Image"},
                ]

            def get_metadata(self, df, dataset):
                return {
                    "title": f"Image Plot - {dataset}",
                    "ncols": 2,
                }"""

    @classmethod
    def setup_class(cls):
        "Make sure at least one result file is available"
        cls.ctx = temp_benchmark(plots=[cls.custom_plot, cls.image_plot])
        cls.bench = cls.ctx.__enter__()
        with CaptureCmdOutput(delete_result_files=False) as out:
            for n_rep in N_REP:
                run(
                    f"{cls.bench.benchmark_dir} -d test-dataset -r {n_rep} "
                    f"-n 2 --no-plot --output rep{n_rep}".split(),
                    'benchopt', standalone_mode=False
                )
        assert len(out.result_files) == len(N_REP), out
        cls.result_files = {
            Path(f).stem: Path(f).resolve().relative_to(Path().resolve())
            for f in out.result_files
        }
        cls.result_file = str(cls.result_files['rep1'])

    @classmethod
    def teardown_class(cls):
        "Clean up the temp benchmark directory."
        cls.ctx.__exit__(None, None, None)

    def setup_method(self):
        plt.close('all')

    def test_plot_invalid_file(self):

        with pytest.raises(FileNotFoundError, match=r"invalid_file"):
            plot(f"{self.bench.benchmark_dir} -f invalid_file --no-html "
                 f"--no-display".split(), 'benchopt', standalone_mode=False)

    def test_plot_invalid_kind(self):

        with pytest.raises(ValueError, match=r"invalid_kind"):
            plot(f"{self.bench.benchmark_dir} -k invalid_kind --no-html "
                 f"--no-display".split(), 'benchopt', standalone_mode=False)

    def test_plot_html_ignore_kind(self):

        with pytest.warns(UserWarning, match=r"Cannot specify '--kind'"):
            plot(f"{self.bench.benchmark_dir} -k boxplot --html "
                 f"--no-display".split(), 'benchopt', standalone_mode=False)

    @pytest.mark.parametrize(
        ('kind', 'expected_n_files'),
        [
            ("custom_plot", 1),
            ("objective_curve", 2),
            ("boxplot", 4),
            ("bar_chart", 2),
            ("image_plot", 1),
            (None, 10)  # all kinds
        ]
    )
    def test_valid_call_mpl(self, kind, expected_n_files):
        ctx = nullcontext() if kind is not None else pytest.warns(
            UserWarning, match="Plot 'table_test-dataset_test-objective'"
        )

        with CaptureCmdOutput() as out:
            cmd = f"{self.bench.benchmark_dir} -f {self.result_file} "
            cmd += "--no-display --no-html "
            if kind is not None:
                cmd += f"--kind {kind}"
            with ctx:
                plot(cmd.split(), 'benchopt', standalone_mode=False)

        assert len(out.result_files) == expected_n_files
        for file in out.result_files:
            if kind is not None:
                assert kind in file
            assert '.pdf' in file

    def test_valid_call_html(self):

        with CaptureCmdOutput(delete_result_files=False) as out:
            cmd = f"{self.bench.benchmark_dir} -f {self.result_file} "
            cmd += "--no-display --html"
            plot(cmd.split(), 'benchopt', standalone_mode=False)

        assert len(out.result_files) == 2
        assert all('.html' in f for f in out.result_files)

        html_content = Path(out.result_files[0]).read_text()
        for k in [
            "custom_plot", "objective_curve", "boxplot", "bar_chart",
            "image_plot"
        ]:
            assert f"<option value=\"{k}\"" in html_content

        # check image plot gracefully handle errors/null block
        assert '"__incompatible__"' in html_content
        assert '"image": null' in html_content

    @pytest.mark.parametrize("n_rep", N_REP)
    @patch("benchopt.plotting.generate_matplotlib.get_plot_boxplot")
    def test_boxplot_with_repetitions(self, plot_boxplot, n_rep):

        import matplotlib.pyplot as plt
        plot_boxplot.return_value = plt.figure()

        res_file = self.result_files[f"rep{n_rep}"]

        with CaptureCmdOutput(debug=True) as out:
            plot(
                f"{self.bench.benchmark_dir} -f {res_file} "
                "--no-display --no-html --kind boxplot".split(),
                'benchopt', standalone_mode=False
            )

        assert len(out.result_files) == 4
        assert all('boxplot' in f for f in out.result_files)
        assert all('.pdf' in f for f in out.result_files)

        assert plot_boxplot.call_count == 4
        for call_args in plot_boxplot.call_args_list:
            plot_data = call_args[0][0]['data'][0]
            assert len(plot_data['y']) == len(plot_data['x'])
            assert all(len(v) == n_rep for v in plot_data['y'])

    def test_complete_bench(self, bench_completion_cases):  # noqa: F811

        # Completion for benchmark name
        _test_shell_completion(plot, [], bench_completion_cases)

    def test_complete_result_files(self):

        # Completion for result files
        _test_shell_completion(
            plot, f"{self.bench.benchmark_dir} -f".split(), [
                ('', [str(v) for v in self.result_files.values()]),
                (self.result_file[:-4], [str(self.result_file)]),
                ('_invalid_file', []),
            ]
        )
