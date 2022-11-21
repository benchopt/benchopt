import re
import time
import tarfile
import tempfile
from pathlib import Path

import click
import pytest
from joblib.memory import _FUNCTION_HASHES
from click.shell_completion import ShellComplete

from benchopt.benchmark import Benchmark
from benchopt.plotting import PLOT_KINDS
from benchopt.utils.stream_redirection import SuppressStd


from benchopt.tests import SELECT_ONE_PGD
from benchopt.tests import SELECT_ONE_SIMULATED
from benchopt.tests import SELECT_ONE_OBJECTIVE
from benchopt.tests import TEST_BENCHMARK_DIR
from benchopt.tests import DUMMY_BENCHMARK
from benchopt.tests import DUMMY_BENCHMARK_PATH
from benchopt.tests import REQUIREMENT_BENCHMARK_PATH
from benchopt.tests.utils import patch_import
from benchopt.tests.utils import CaptureRunOutput


from benchopt.cli.main import run
from benchopt.cli.main import install
from benchopt.cli.helpers import clean
from benchopt.cli.helpers import archive
from benchopt.cli.helpers import check_install
from benchopt.cli.process_results import plot
from benchopt.cli.process_results import generate_results


ALL_BENCHMARKS = [str(p) for p in TEST_BENCHMARK_DIR.glob("*")]

BENCHMARK_COMPLETION_CASES = [
    (str(DUMMY_BENCHMARK_PATH.parent), ALL_BENCHMARKS),
    (str(DUMMY_BENCHMARK_PATH.parent)[:-2], ALL_BENCHMARKS),
    (str(DUMMY_BENCHMARK_PATH)[:-2], [str(DUMMY_BENCHMARK_PATH)])
]
SOLVER_COMPLETION_CASES = [
    ('', [n.lower() for n in DUMMY_BENCHMARK.get_solver_names()]),
    ('sk', ['sklearn']),
    ('pgd', ['julia-pgd', 'python-pgd', 'python-pgd-with-cb', 'r-pgd'])
]
DATASET_COMPLETION_CASES = [
    ('', [n.lower() for n in DUMMY_BENCHMARK.get_dataset_names()]),
    ('simu', ['simulated']),
    ('lated', ['simulated']),
]
CURRENT_DIR = Path.cwd()


def _get_completion(cmd, args, incomplete):
    complete = ShellComplete(cmd, {}, '', '')
    proposals = complete.get_completions(args, incomplete)
    return [c.value for c in proposals]


def _test_shell_completion(cmd, args, test_cases):
    for incomplete, expected in test_cases:
        proposals = _get_completion(cmd, args, incomplete)
        n_res = len(expected)
        assert len(proposals) == n_res, (
            f"Expected {n_res} completion proposal, got '{proposals}'"
        )
        if n_res == 1:
            assert proposals[0] == expected[0], proposals
        elif expected is not None:
            assert set(proposals) == set(expected), proposals


class TestRunCmd:

    @pytest.mark.parametrize('invalid_benchmark, match', [
        ('invalid_benchmark', "Path 'invalid_benchmark' does not exist."),
        ('.', "The folder '.' does not contain `objective.py`"),
        ("", rf"The folder '{CURRENT_DIR}' does not contain `objective.py`")],
        ids=['invalid_path', 'no_objective', "no_objective in default"])
    def test_invalid_benchmark(self, invalid_benchmark, match):
        with pytest.raises(click.BadParameter, match=match):
            if len(invalid_benchmark) > 0:
                run([invalid_benchmark], 'benchopt', standalone_mode=False)
            else:
                run([], 'benchopt', standalone_mode=False)

    def test_invalid_dataset(self):
        with pytest.raises(click.BadParameter, match="invalid_dataset"):
            run([str(DUMMY_BENCHMARK_PATH), '-l', '-d', 'invalid_dataset',
                 '-s', 'pgd'], 'benchopt', standalone_mode=False)

    def test_invalid_solver(self):
        with pytest.raises(click.BadParameter, match="invalid_solver"):
            run([str(DUMMY_BENCHMARK_PATH), '-l', '-s', 'invalid_solver'],
                'benchopt', standalone_mode=False)

    def test_objective_not_installed(self):

        def import_error():
            raise ModuleNotFoundError("no module named 'dummy_package'")

        with patch_import(dummy_package=import_error):
            with pytest.raises(
                    ModuleNotFoundError,
                    match="no module named 'dummy_package'"
            ):
                run(
                    [str(REQUIREMENT_BENCHMARK_PATH), '-n', '1'],
                    'benchopt', standalone_mode=False
                )

    @pytest.mark.parametrize('n_jobs', [1, 2])
    def test_benchopt_run(self, n_jobs):

        with CaptureRunOutput() as out:
            run([str(DUMMY_BENCHMARK_PATH), '-l', '-d', SELECT_ONE_SIMULATED,
                 '-f', SELECT_ONE_PGD, '-n', '1', '-r', '1', '-o',
                 SELECT_ONE_OBJECTIVE, '-j', n_jobs, '--no-plot'],
                'benchopt', standalone_mode=False)

        out.check_output('Simulated', repetition=1)
        out.check_output('Dummy Sparse Regression', repetition=1)
        out.check_output(r'Python-PGD\[step_size=1\]:', repetition=6)
        out.check_output(r'Python-PGD\[step_size=1.5\]:', repetition=0)

        # Make sure the results were saved in a result file
        assert len(out.result_files) == 1, out.output

    def test_benchopt_run_in_env(self, test_env_name):
        with CaptureRunOutput() as out:
            with pytest.raises(SystemExit, match='False'):
                run([str(DUMMY_BENCHMARK_PATH), '--env-name', test_env_name,
                     '-d', SELECT_ONE_SIMULATED, '-f', SELECT_ONE_PGD,
                     '-n', '1', '-r', '1', '-o', SELECT_ONE_OBJECTIVE,
                     '--no-plot'], 'benchopt', standalone_mode=False)

        out.check_output(f'conda activate {test_env_name}')
        out.check_output('Simulated', repetition=1)
        out.check_output('Dummy Sparse Regression', repetition=1)
        out.check_output(r'Python-PGD\[step_size=1\]:', repetition=6)
        out.check_output(r'Python-PGD\[step_size=1.5\]:', repetition=0)

        # Make sure the results were saved in a result file
        assert len(out.result_files) == 1, out.output

    def test_benchopt_run_custom_parameters(self):
        SELECT_DATASETS = r'simulated[n_features=[100, 200]]'
        SELECT_SOLVERS = r'python-pgd-with-cb[use_acceleration=[True, False]]'
        SELECT_OBJECTIVES = r'dummy*[0.1, 0.2]'

        with CaptureRunOutput() as out:
            run([str(DUMMY_BENCHMARK_PATH), '-l', '-d', SELECT_DATASETS,
                 '-f', SELECT_SOLVERS, '-n', '1', '-r', '1', '-o',
                 SELECT_OBJECTIVES, '--no-plot'],
                'benchopt', standalone_mode=False)

        out.check_output(r'Simulated\[n_features=100,', repetition=1)
        out.check_output(r'Simulated\[n_features=200,', repetition=1)
        out.check_output(r'Simulated\[n_features=5000,', repetition=0)
        out.check_output(r'Dummy Sparse Regression\[reg=0.1\]', repetition=2)
        out.check_output(r'Dummy Sparse Regression\[reg=0.2\]', repetition=2)
        out.check_output(r'Dummy Sparse Regression\[reg=0.05\]', repetition=0)
        out.check_output(r'--Python-PGD\[', repetition=0)
        out.check_output(r'--Python-PGD-with-cb\[use_acceleration=False\]:',
                         repetition=28)
        out.check_output(r'--Python-PGD-with-cb\[use_acceleration=True\]:',
                         repetition=28)

    def test_benchopt_run_profile(self):
        with CaptureRunOutput() as out:
            run_cmd = [str(DUMMY_BENCHMARK_PATH),
                       '-d', SELECT_ONE_SIMULATED, '-f', SELECT_ONE_PGD,
                       '-n', '1', '-r', '1', '-o', SELECT_ONE_OBJECTIVE,
                       '--profile', '--no-plot']
            run(run_cmd, 'benchopt', standalone_mode=False)

        out.check_output('using profiling', repetition=1)
        out.check_output("File: .*benchopt/tests/test_benchmarks/"
                         "dummy_benchmark/solvers/python_pgd.py", repetition=1)
        out.check_output(r'\s+'.join([
            "Line #", "Hits", "Time", "Per Hit", "% Time", "Line Contents"
        ]), repetition=1)
        out.check_output(r"def run\(self, n_iter\):", repetition=1)

    def test_benchopt_run_config_file(self):
        tmp = tempfile.NamedTemporaryFile(mode="w+")
        tmp.write("some_unknown_option: 0")
        tmp.flush()
        with pytest.raises(ValueError, match="Invalid config file option"):
            run(f'{str(DUMMY_BENCHMARK_PATH)} --config {tmp.name}'.split(),
                'benchopt', standalone_mode=False)

        config = f"""
        objective-filter:
          - {SELECT_ONE_OBJECTIVE}
        dataset:
          - {SELECT_ONE_SIMULATED}
        n-repetitions: 2
        max-runs: 1
        force-solver:
          - python-pgd[step_size=[2, 3]]
          - Solver-Test[raise_error=False]
        """
        tmp = tempfile.NamedTemporaryFile(mode="w+")
        tmp.write(config)
        tmp.flush()

        run_cmd = [str(DUMMY_BENCHMARK_PATH), '--config', tmp.name,
                   '--no-plot']

        with CaptureRunOutput() as out:
            run(run_cmd, 'benchopt', standalone_mode=False)

        out.check_output(r'Solver-Test\[raise_error=False\]:', repetition=11)
        out.check_output(r'Python-PGD\[step_size=2\]:', repetition=11)
        out.check_output(r'Python-PGD\[step_size=3\]:', repetition=11)

        # test that CLI options take precedence
        with CaptureRunOutput() as out:
            run(run_cmd + ['-f', 'Solver-Test'],
                'benchopt', standalone_mode=False)

        out.check_output(r'Solver-Test\[raise_error=False\]:', repetition=11)
        out.check_output(
            r'Python-PGD\[step_size=1.5\]:', repetition=0)

    @pytest.mark.parametrize('n_rep', [2, 3, 5])
    def test_benchopt_caching(self, n_rep):
        clean([str(DUMMY_BENCHMARK_PATH)], 'benchopt', standalone_mode=False)

        # XXX - remove once this is fixed upstream with joblib/joblib#1289
        _FUNCTION_HASHES.clear()

        # Check that the computation caching is working properly.
        run_cmd = [str(DUMMY_BENCHMARK_PATH), '-l', '-d', SELECT_ONE_SIMULATED,
                   '-s', SELECT_ONE_PGD, '-n', '1', '-r', str(n_rep),
                   '-o', SELECT_ONE_OBJECTIVE, '--no-plot']

        # Make a first run that should be put in cache
        with CaptureRunOutput() as out:
            run(run_cmd, 'benchopt', standalone_mode=False)

        # Check that this run was properly done. If only one is detected, this
        # could indicate that the clean command does not work properly.
        out.check_output(r'Python-PGD\[step_size=1\]:',
                         repetition=5*n_rep+1)

        # Now check that the cache is hit when running the benchmark a
        # second time without force
        with CaptureRunOutput() as out:
            run(run_cmd, 'benchopt', standalone_mode=False)

        out.check_output(r'Python-PGD\[step_size=1\]:',
                         repetition=1)

        # Check that the cache is also hit when running in parallel
        with CaptureRunOutput() as out:
            run(run_cmd + ['-j', 2], 'benchopt', standalone_mode=False)

        out.check_output(r'Python-PGD\[step_size=1\]:',
                         repetition=1)

        # Make sure that -f option forces the re-run for the solver
        run_cmd[4] = '-f'
        with CaptureRunOutput() as out:
            run(run_cmd, 'benchopt', standalone_mode=False)

        out.check_output(r'Python-PGD\[step_size=1\]:',
                         repetition=5*n_rep+1)

    def test_changing_output_name(self):
        command = [
            str(DUMMY_BENCHMARK_PATH), '-l', '-s', SELECT_ONE_PGD,
            '-d', SELECT_ONE_SIMULATED,
            '-n', '1', '--output', 'unique_name',
            '--no-plot'
        ]
        with CaptureRunOutput() as out:
            run(command, 'benchopt', standalone_mode=False)
            run(command, 'benchopt', standalone_mode=False)

        result_files = re.findall(
            r'Saving result in: (.*\.parquet)', out.output
        )
        names = [Path(result_file).stem for result_file in result_files]
        assert names[0] == 'unique_name' and names[1] == 'unique_name_1'

    def test_shell_complete(self):
        # Completion for benchmark name
        _test_shell_completion(run, [], BENCHMARK_COMPLETION_CASES)

        # Completion for solvers
        _test_shell_completion(
            run, [str(DUMMY_BENCHMARK_PATH), '-s'], SOLVER_COMPLETION_CASES
        )

        # Completion for datasets
        _test_shell_completion(
            run, [str(DUMMY_BENCHMARK_PATH), '-d'], DATASET_COMPLETION_CASES
        )


class TestInstallCmd:

    @pytest.mark.parametrize('invalid_benchmark, match', [
        ('invalid_benchmark', "Path 'invalid_benchmark' does not exist."),
        ('.', "The folder '.' does not contain `objective.py`")],
        ids=['invalid_path', 'no_objective'])
    def test_invalid_benchmark(self, invalid_benchmark, match):
        with pytest.raises(click.BadParameter, match=match):
            install([invalid_benchmark], 'benchopt', standalone_mode=False)

    def test_invalid_dataset(self):
        with pytest.raises(click.BadParameter, match=r"invalid_dataset"):
            install([str(DUMMY_BENCHMARK_PATH), '-d', 'invalid_dataset',
                     '-s', 'pgd'], 'benchopt', standalone_mode=False)

    def test_invalid_solver(self):
        with pytest.raises(click.BadParameter, match=r"invalid_solver"):
            install([str(DUMMY_BENCHMARK_PATH), '-s', 'invalid_solver'],
                    'benchopt', standalone_mode=False)

    def test_existing_empty_env(self, empty_env_name):
        msg = (
            f"`benchopt` is not installed in existing env '{empty_env_name}'"
        )
        with pytest.raises(RuntimeError, match=msg):
            install([str(DUMMY_BENCHMARK_PATH), '--env-name', empty_env_name],
                    'benchopt', standalone_mode=False)

    def test_benchopt_install(self):
        with CaptureRunOutput() as out:
            install(
                [str(DUMMY_BENCHMARK_PATH), '-d', SELECT_ONE_SIMULATED, '-s',
                 SELECT_ONE_PGD, '-y'], 'benchopt', standalone_mode=False
            )

        out.check_output(f"Installing '{DUMMY_BENCHMARK.name}' requirements")
        out.check_output("already available\n", repetition=3)

    def test_benchopt_install_in_env(self, test_env_name):
        with CaptureRunOutput() as out:
            install(
                [str(DUMMY_BENCHMARK_PATH), '-d', SELECT_ONE_SIMULATED, '-s',
                 SELECT_ONE_PGD, '--env-name', test_env_name],
                'benchopt', standalone_mode=False
            )

        out.check_output(
            f"Installing '{DUMMY_BENCHMARK.name}' requirements"
        )
        out.check_output(
            f"already available in '{test_env_name}'\n", repetition=3
        )

    def test_benchopt_install_in_env_with_requirements(self, test_env_name):
        objective = Benchmark(
            REQUIREMENT_BENCHMARK_PATH
        ).get_benchmark_objective()
        out = 'already installed but failed to import.'
        if not objective.is_installed(env_name=test_env_name):
            with CaptureRunOutput() as out:
                install(
                    [str(REQUIREMENT_BENCHMARK_PATH), '--env-name',
                     test_env_name],
                    'benchopt', standalone_mode=False
                )
        assert objective.is_installed(env_name=test_env_name), out
        # XXX: run the bench

        with CaptureRunOutput() as out:
            with pytest.raises(SystemExit, match='False'):
                run_cmd = [str(REQUIREMENT_BENCHMARK_PATH), '--env-name',
                           test_env_name, '-n', '2', '-r', '1', '--no-plot']
                run(run_cmd, 'benchopt', standalone_mode=False)

        out.check_output(r"done \(not enough run\)", repetition=1)

    def test_shell_complete(self):
        # Completion for benchmark name
        _test_shell_completion(install, [], BENCHMARK_COMPLETION_CASES)

        # Completion for solvers
        _test_shell_completion(
            run, [str(DUMMY_BENCHMARK_PATH), '-s'], SOLVER_COMPLETION_CASES
        )

        # Completion for datasets
        _test_shell_completion(
            run, [str(DUMMY_BENCHMARK_PATH), '-d'], DATASET_COMPLETION_CASES
        )


class TestPlotCmd:

    @classmethod
    def setup_class(cls):
        "Make sure at least one result file is available"
        with SuppressStd() as out:
            run([str(DUMMY_BENCHMARK_PATH), '-l', '-d', SELECT_ONE_SIMULATED,
                 '-s', SELECT_ONE_PGD, '-n', '2', '-r', '1', '-o',
                 SELECT_ONE_OBJECTIVE, '--no-plot'], 'benchopt',
                standalone_mode=False)
        result_files = re.findall(
            r'Saving result in: (.*\.parquet)', out.output
        )
        assert len(result_files) == 1, out.output
        result_file = result_files[0]
        cls.result_file = result_file
        cls.result_file = str(Path(result_file).relative_to(Path().resolve()))

    @classmethod
    def teardown_class(cls):
        "Make sure at least one result file is available"
        Path(cls.result_file).unlink()

    def test_plot_invalid_file(self):

        with pytest.raises(FileNotFoundError, match=r"invalid_file"):
            plot([str(DUMMY_BENCHMARK_PATH), '-f', 'invalid_file', '--no-html',
                  '--no-display'], 'benchopt', standalone_mode=False)

    def test_plot_invalid_kind(self):

        with pytest.raises(ValueError, match=r"invalid_kind"):
            plot([str(DUMMY_BENCHMARK_PATH), '-k', 'invalid_kind', '--no-html',
                  '--no-display'], 'benchopt', standalone_mode=False)

    def test_plot_html_ignore_kind(self):

        with pytest.warns(UserWarning, match=r"Cannot specify '--kind'"):
            plot([str(DUMMY_BENCHMARK_PATH), '-k', 'invalid_kind', '--html',
                  '--no-display'], 'benchopt', standalone_mode=False)

    @pytest.mark.parametrize('kind', PLOT_KINDS)
    def test_valid_call(self, kind):

        with SuppressStd() as out:
            plot([str(DUMMY_BENCHMARK_PATH), '-f', self.result_file,
                  '-k', kind, '--no-display', '--no-html'],
                 'benchopt', standalone_mode=False)

        saved_files = re.findall(r'Save .* as: (.*\.pdf)', out.output)
        try:
            assert len(saved_files) == 1
            assert kind in saved_files[0]
        finally:
            # Make sure to clean up all files even when the test fails
            for f in saved_files:
                Path(f).unlink()

    def test_valid_call_html(self):

        with SuppressStd() as out:
            plot([str(DUMMY_BENCHMARK_PATH), '-f', self.result_file,
                  '--no-display', '--html'], 'benchopt', standalone_mode=False)

        saved_files = re.findall(
            r'Writing.* results to (.*\.html)', out.output
        )
        try:
            assert len(saved_files) == 2
        finally:
            # Make sure to clean up all files even when the test fails
            for f in saved_files:
                Path(f).unlink()

    def test_shell_complete(self):
        # Completion for benchmark name
        _test_shell_completion(plot, [], BENCHMARK_COMPLETION_CASES)

        # Completion for solvers
        _test_shell_completion(
            plot, [str(DUMMY_BENCHMARK_PATH), '-f'], [
                ('', [self.result_file]),
                (self.result_file[:-4], [self.result_file]),
                ('_invalid_file', []),
            ]
        )


class TestGenerateResultCmd:

    @classmethod
    def setup_class(cls):
        "Make sure at least one result file is available"
        with SuppressStd() as out:
            clean([str(DUMMY_BENCHMARK_PATH)],
                  'benchopt', standalone_mode=False)
            clean([str(REQUIREMENT_BENCHMARK_PATH)],
                  'benchopt', standalone_mode=False)
            run([str(DUMMY_BENCHMARK_PATH), '-l', '-d', SELECT_ONE_SIMULATED,
                 '-s', SELECT_ONE_PGD, '-n', '2', '-r', '1', '-o',
                 SELECT_ONE_OBJECTIVE, '--no-plot'], 'benchopt',
                standalone_mode=False)
            time.sleep(1)  # Make sure there is 2 separate files
            run([str(DUMMY_BENCHMARK_PATH), '-l', '-d', SELECT_ONE_SIMULATED,
                 '-s', SELECT_ONE_PGD, '-n', '2', '-r', '1', '-o',
                 SELECT_ONE_OBJECTIVE, '--no-plot'], 'benchopt',
                standalone_mode=False)
        result_files = re.findall(
            r'Saving result in: (.*\.parquet)', out.output
        )
        assert len(result_files) == 2, out.output
        cls.result_files = result_files

    @classmethod
    def teardown_class(cls):
        "Make sure at least one result file is available"
        for f in cls.result_files:
            Path(f).unlink()

    def test_call(self):

        with SuppressStd() as out:
            generate_results([
                '--root', str(DUMMY_BENCHMARK_PATH.parent), '--no-display'
            ], 'benchopt', standalone_mode=False)
        html_results = re.findall(r'Writing results to (.*\.html)', out.output)
        html_benchmark = re.findall(
            rf'Writing {DUMMY_BENCHMARK.name} results to (.*\.html)',
            out.output
        )
        html_index = re.findall(r'Writing index to (.*\.html)', out.output)
        try:
            assert len(html_index) == 1, out.output
            assert len(html_benchmark) == 1, out.output
            assert len(html_results) == len(self.result_files), out.output
            print(out.output)
            for f in self.result_files:
                basename = Path(f).stem
                assert any(basename in res for res in html_results)
        finally:
            # Make sure to clean up all files even when the test fails
            for f in html_results + html_benchmark + html_index:
                Path(f).unlink()


class TestArchiveCmd:

    @classmethod
    def setup_class(cls):
        "Make sure at least one result file is available"
        with SuppressStd() as out:
            run([str(DUMMY_BENCHMARK_PATH), '-l', '-d', SELECT_ONE_SIMULATED,
                 '-s', SELECT_ONE_PGD, '-n', '2', '-r', '1', '-o',
                 SELECT_ONE_OBJECTIVE, '--no-plot'], 'benchopt',
                standalone_mode=False)
        result_file = re.findall(
            r'Saving result in: (.*\.parquet)', out.output
        )
        assert len(result_file) == 1, out.output
        cls.result_file = result_file[0]

    @classmethod
    def teardown_class(cls):
        "Clean up the result file."
        Path(cls.result_file).unlink()

    @pytest.mark.parametrize('invalid_benchmark, match', [
        ('invalid_benchmark', "Path 'invalid_benchmark' does not exist."),
        ('.', "The folder '.' does not contain `objective.py`"),
        ("", rf"The folder '{CURRENT_DIR}' does not contain `objective.py`")],
        ids=['invalid_path', 'no_objective', "no_objective in default"])
    def test_invalid_benchmark(self, invalid_benchmark, match):
        with pytest.raises(click.BadParameter, match=match):
            if len(invalid_benchmark) > 0:
                run([invalid_benchmark], 'benchopt', standalone_mode=False)
            else:
                run([], 'benchopt', standalone_mode=False)

    def test_call(self):

        with SuppressStd() as out:
            archive([str(DUMMY_BENCHMARK_PATH)], 'benchopt',
                    standalone_mode=False)
        saved_files = re.findall(r'Results are in (.*\.tar.gz)', out.output)
        try:
            assert len(saved_files) == 1
            saved_file = saved_files[0]

            counts = {k: 0 for k in [
                "__pycache__", "outputs", "objective.py", "datasets",
                "solvers", "README"
            ]}

            with tarfile.open(saved_file, "r:gz") as tar:
                for elem in tar.getmembers():
                    for k in counts:
                        counts[k] += k in elem.name
                    assert elem.uname == "benchopt"

            assert counts["README"] == 1, counts
            assert counts["objective.py"] == 1, counts
            assert counts["datasets"] >= 1, counts
            assert counts["solvers"] >= 1, counts
            assert counts["outputs"] == 0, counts
            assert counts["__pycache__"] == 0, counts
        finally:
            # Make sure to clean up all files even when the test fails
            for f in saved_files:
                Path(f).unlink()

    def test_call_with_outputs(self):

        with SuppressStd() as out:
            archive([str(DUMMY_BENCHMARK_PATH), "--with-outputs"], 'benchopt',
                    standalone_mode=False)
        saved_files = re.findall(r'Results are in (.*\.tar.gz)', out.output)
        try:
            assert len(saved_files) == 1
            saved_file = saved_files[0]

            counts = {k: 0 for k in [
                "__pycache__", "outputs", "objective.py", "datasets",
                "solvers", "README"
            ]}

            with tarfile.open(saved_file, "r:gz") as tar:
                for elem in tar.getmembers():
                    for k in counts:
                        counts[k] += k in elem.name
                    assert elem.uname == "benchopt"

            assert counts["README"] == 1, counts
            assert counts["objective.py"] == 1, counts
            assert counts["datasets"] >= 1, counts
            assert counts["solvers"] >= 1, counts
            assert counts["outputs"] >= 1, counts
            assert counts["__pycache__"] == 0, counts
        finally:
            # Make sure to clean up all files even when the test fails
            for f in saved_files:
                Path(f).unlink()

    def test_shell_complete(self):
        # Completion for benchmark name
        _test_shell_completion(archive, [], BENCHMARK_COMPLETION_CASES)


class TestCheckInstallCmd:
    def test_solver_installed(self):
        pgd_solver = DUMMY_BENCHMARK_PATH / 'solvers' / 'python_pgd.py'
        with pytest.raises(SystemExit, match=r'0'):
            check_install([
                str(DUMMY_BENCHMARK_PATH), str(pgd_solver.resolve()), 'Solver'
            ], 'benchopt')

    def test_solver_does_not_exists(self):
        pgd_solver = DUMMY_BENCHMARK_PATH / 'solvers' / 'invalid.py'
        with pytest.raises(FileNotFoundError, match=r'invalid.py'):
            check_install([
                str(DUMMY_BENCHMARK_PATH), str(pgd_solver.resolve()), 'Solver'
            ], 'benchopt')

    def test_dataset_installed(self):
        pgd_solver = DUMMY_BENCHMARK_PATH / 'datasets' / 'simulated.py'
        with pytest.raises(SystemExit, match=r'0'):
            check_install([
                str(DUMMY_BENCHMARK_PATH), str(pgd_solver.resolve()), 'Dataset'
            ], 'benchopt')

    def test_dataset_does_not_exists(self):
        pgd_solver = DUMMY_BENCHMARK_PATH / 'datasets' / 'invalid.py'
        with pytest.raises(FileNotFoundError, match=r'invalid.py'):
            check_install([
                str(DUMMY_BENCHMARK_PATH), str(pgd_solver.resolve()), 'Dataset'
            ], 'benchopt')
