from pathlib import Path

from benchopt.utils.temp_benchmark import temp_benchmark

from benchopt.tests.utils import CaptureCmdOutput

from benchopt.cli.main import run
from benchopt.cli.helpers import clean
from benchopt.cli.process_results import generate_results


class TestGenerateResultCmd:

    @classmethod
    def setup_class(cls):
        "Make sure at least one result file is available"
        cls.ctx = temp_benchmark()
        cls.bench = cls.ctx.__enter__()
        cmd = f"{cls.bench.benchmark_dir} -d test-dataset -n 2 -r 1 --no-plot"
        with CaptureCmdOutput(delete_result_files=False) as out:
            clean([str(cls.bench.benchmark_dir)], standalone_mode=False)
            run(f"{cmd} --output out1".split(), standalone_mode=False)
            run(f"{cmd} --output out2".split(),
                standalone_mode=False)
        assert len(out.result_files) == 2, out
        cls.result_files = out.result_files

    @classmethod
    def teardown_class(cls):
        "Delete the result files created in setup_class."
        for f in cls.result_files:
            Path(f).unlink()

    def test_call(self):

        with CaptureCmdOutput() as out:
            generate_results([
                '--root', str(self.bench.benchmark_dir.parent), '--no-display'
            ], 'benchopt', standalone_mode=False)

        assert len(out.result_files) == 2 + len(self.result_files), out.output
        html_index = [f for f in out.result_files if 'index' in f]
        html_benchmark = [
            f for f in out.result_files
            if f"{self.bench.benchmark_dir.name}.html" in f
        ]
        html_results = [f for f in out.result_files if 'out' in f]
        assert len(html_index) == 1, out.output
        assert len(html_benchmark) == 1, out.output
        assert len(html_results) == len(self.result_files), out.output
        for f in self.result_files:
            basename = Path(f).stem
            assert any(basename in res for res in html_results)
