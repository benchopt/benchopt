import re
import tarfile
from pathlib import Path

import click
import pytest
from joblib.memory import _FUNCTION_HASHES

from benchopt.plotting import PLOT_KINDS
from benchopt.utils.temp_benchmark import temp_benchmark


from benchopt.tests.utils import CaptureCmdOutput
from benchopt.tests.utils import patch_var_env

from benchopt.cli.main import run
from benchopt.cli.main import install
from benchopt.cli.helpers import clean
from benchopt.cli.helpers import archive
from benchopt.cli.process_results import plot
from benchopt.cli.process_results import generate_results

from benchopt.cli.tests.completion_cases import _test_shell_completion
from benchopt.cli.tests.completion_cases import (  # noqa: F401
    bench_completion_cases,
    solver_completion_cases,
    dataset_completion_cases
)


CURRENT_DIR = Path.cwd()


class TestRunCmd:

    @pytest.mark.parametrize('invalid_benchmark, match', [
        ('invalid_benchmark', "Path 'invalid_benchmark' does not exist."),
        ('.', "The folder '.' does not contain `objective.py`"),
        ("", rf"The folder '{CURRENT_DIR}' does not contain `objective.py`")],
        ids=['invalid_path', 'no_objective', "no_objective in default"])
    def test_invalid_benchmark(self, invalid_benchmark, match):
        with pytest.raises(click.BadParameter, match=re.escape(match)):
            if len(invalid_benchmark) > 0:
                run([invalid_benchmark], 'benchopt', standalone_mode=False)
            else:
                run([], 'benchopt', standalone_mode=False)

    def test_invalid_dataset(self):
        with temp_benchmark() as bench:
            with pytest.raises(click.BadParameter, match="invalid_dataset"):
                cmd = f"{bench.benchmark_dir} -d invalid_dataset".split()
                run(cmd, 'benchopt', standalone_mode=False)

    def test_invalid_solver(self):
        with temp_benchmark() as bench:
            with pytest.raises(click.BadParameter, match="invalid_solver"):
                cmd = f"{bench.benchmark_dir} -d invalid_solver".split()
                run(cmd, 'benchopt', standalone_mode=False)

    def test_objective_not_installed(self):

        # Make sure that when the Objective is not installed, due to a missing
        # dependency, an error is raised.
        objective = """import fake_module
        from benchopt import BaseObjective

        class Objective(BaseObjective):
            name = 'dummy'
        """
        with pytest.raises(
                ModuleNotFoundError,
                match="No module named 'fake_module'"
        ):
            with temp_benchmark(objective=objective) as benchmark:
                run(
                    [str(benchmark.benchmark_dir), '-n', '1'],
                    'benchopt', standalone_mode=False
                )

    @pytest.mark.parametrize('n_jobs', [1, 2])
    def test_valid_call(self, n_jobs):

        with temp_benchmark() as bench, CaptureCmdOutput() as out:
            cmd = (
                f"{bench.benchmark_dir} -r 1 -n 1 -j {n_jobs} --no-plot "
                "-d test-dataset"
            )
            run(cmd.split(), 'benchopt', standalone_mode=False)

        out.check_output('test-dataset', repetition=1)
        out.check_output('simulated', repetition=0)
        out.check_output('test-objective', repetition=1)
        out.check_output('test-solver:', repetition=6)

        # Make sure the results were saved in a result file
        assert len(out.result_files) == 1, out

    def test_valid_call_in_env(self, test_env_name):
        with temp_benchmark() as bench, CaptureCmdOutput() as out:
            cmd = (
                f"{bench.benchmark_dir} -r 1 -n 1 --no-plot "
                f"-d test-dataset --env-name {test_env_name}"
            )
            with pytest.raises(SystemExit, match='False'):
                run(cmd.split(), 'benchopt', standalone_mode=False)

        out.check_output(f'conda activate "{test_env_name}"')
        # test-dataset appears twice because of the call to the subcommand
        out.check_output('test-dataset', repetition=2)
        out.check_output('simulated', repetition=0)
        out.check_output('test-objective', repetition=1)
        out.check_output('test-solver:', repetition=6)

        # Make sure the results were saved in a result file
        assert len(out.result_files) == 1, out

    @pytest.mark.parametrize('timeout', ['10', '1m', '0.03h', '100s'])
    def test_timeout_in_env(self, test_env_name, timeout):
        with temp_benchmark() as bench, CaptureCmdOutput() as out:
            cmd = (
                f"{bench.benchmark_dir} -r 1 -n 1 --timeout {timeout} "
                f"--no-plot -d test-dataset --env-name {test_env_name}"
            )
            with pytest.raises(SystemExit, match='False'):
                run(cmd.split(), 'benchopt', standalone_mode=False)

        out.check_output(f'conda activate "{test_env_name}"')
        # test-dataset appears twice because of the call to the subcommand
        out.check_output('test-dataset', repetition=2)
        out.check_output('simulated', repetition=0)
        out.check_output('test-objective', repetition=1)
        out.check_output('test-solver:', repetition=6)

        # Make sure the results were saved in a result file
        assert len(out.result_files) == 1, out

    def test_no_timeout(self):
        args = "--no-plot -d test-dataset".split()

        # First test: --timeout==0
        with temp_benchmark() as bench, CaptureCmdOutput() as out:
            run(
                [f"{bench.benchmark_dir}", *args, "--timeout=0"],
                "benchopt", standalone_mode=False
            )
        out.check_output("(timeout)", repetition=1)

        with patch_var_env("BENCHOPT_DEFAULT_TIMEOUT", 0):
            # Second test: no option about timeout, env_var set to 0
            with temp_benchmark() as bench, CaptureCmdOutput() as out:
                run(
                    [f"{bench.benchmark_dir}", *args],
                    "benchopt", standalone_mode=False
                )
            out.check_output("(timeout)", repetition=1)

            # Third test: --no-timeout
            with temp_benchmark() as bench, CaptureCmdOutput() as out:
                run(
                    [f"{bench.benchmark_dir}", *args, "--no-timeout"],
                    "benchopt", standalone_mode=False
                )
            out.check_output("(timeout)", repetition=0)

        # Fourth test: --timeout and --no-timeout both specified
        match = 'You cannot specify both --timeout and --no-timeout options.'

        with pytest.raises(click.BadParameter, match=re.escape(match)):
            with temp_benchmark() as bench, CaptureCmdOutput() as out:
                run(
                    [f"{bench.benchmark_dir}", *args,
                     "--timeout=0", "--no-timeout"],
                    "benchopt", standalone_mode=False
                )

    def test_custom_parameters(self, no_debug_log):
        dataset = """from benchopt import BaseDataset
        class Dataset(BaseDataset):
            name = "test-dataset"
            parameters = {'param1': [0, 1], 'param2': [0, 1]}
            def get_data(self):
                print(f"GET_DATA#{self.param1},{self.param2}")
                return dict(X=None, y=None)
        """

        with temp_benchmark(datasets=dataset) as bench, \
                CaptureCmdOutput() as out:
            run(
                f"{bench.benchmark_dir} -d test-dataset[param1=[2,3]] "
                "-n 1 --no-plot".split(),
                'benchopt', standalone_mode=False
            )

        out.check_output('GET_DATA#0,', repetition=0)
        out.check_output('GET_DATA#1,', repetition=0)
        out.check_output('GET_DATA#2,0', repetition=1)
        out.check_output('GET_DATA#2,1', repetition=1)
        out.check_output('GET_DATA#3,', repetition=2)

    def test_profiling(self, test_env_name, no_debug_log):
        # Run this test in a subprocess as calling the profiler in the same
        # process breaks the coverage collection.
        solver = """from benchopt import BaseSolver
        from benchopt.utils.profiling import profile

        class Solver(BaseSolver):
            name = 'test-solver'
            def set_objective(self, X, y, lmbd): pass
            @profile
            def run(self, n_iter):
                import time
                print("RUN")
                time.sleep(0.1)
            def get_result(self): return dict(beta=None)
        """
        with temp_benchmark(solvers=solver) as bench, \
                CaptureCmdOutput() as out:
            with pytest.raises(SystemExit, match='False'):
                run(
                    f"{bench.benchmark_dir} --env-name {test_env_name} "
                    "-s test-solver -n 1 -r 1 --profile --no-plot".split(),
                    'benchopt', standalone_mode=False
                )
        out.check_output('using profiling', repetition=1)
        out.check_output("File: .*solver_0.py", repetition=1)
        out.check_output(r'\s+'.join([
            "Line #", "Hits", "Time", "Per Hit", "% Time", "Line Contents"
        ]), repetition=1)
        out.check_output(r"def run\(self, n_iter\):", repetition=1)
        out.check_output(r"time.sleep\(0.1\)", repetition=1)

    def test_config_file(self, no_debug_log):
        n_reps = 2
        config = f"""
        objective:
          - test-objective
        dataset:
          - test-dataset
        solver:
          - test-solver[param1=42]
        n-repetitions: {n_reps}
        max-runs: 0
        """

        solver = """from benchopt import BaseSolver

        class Solver(BaseSolver):
            name = "test-solver"
            parameters = {'param1':[0]}
            strategy = "run_once"

            def set_objective(self, X, y, lmbd): pass
            def run(self, _): print(f"Solver#RUN#{self.param1}")
            def get_result(self): return dict(beta=1)
        """

        with temp_benchmark(config=config, solvers=solver) as bench:
            with CaptureCmdOutput() as out:
                run(
                    f"{bench.benchmark_dir} --no-plot --config "
                    f"{bench.benchmark_dir / 'config.yml'}".split(),
                    'benchopt', standalone_mode=False
                )

            out.check_output('test-objective', repetition=1)
            out.check_output('test-dataset', repetition=1)
            out.check_output('simulated', repetition=0)
            out.check_output(r'test-solver\[param1=42\]:', repetition=n_reps+1)
            out.check_output(r'test-solver\[param1=0\]:', repetition=0)

            # test that CLI options take precedence
            with CaptureCmdOutput() as out:

                run(
                    f"{bench.benchmark_dir} --no-plot --config "
                    f"{bench.benchmark_dir / 'config.yml'} "
                    "-s test-solver[param1=27] -r 1".split(),
                    'benchopt', standalone_mode=False)

            out.check_output('test-objective', repetition=1)
            out.check_output('test-dataset', repetition=1)
            out.check_output('simulated', repetition=0)
            out.check_output(r'test-solver\[param1=27\]:', repetition=2)
            out.check_output(r'test-solver\[param1=42\]:', repetition=0)

    @pytest.mark.parametrize('config, msg', [
        ("some_unknown_option: 0", "Invalid config file option"),
        ("solver: [",  "expected the node content"),
    ], ids=['invalid_option', 'invalid_syntax'])
    def test_invalid_config_file(self, config, msg):

        with temp_benchmark(config=config) as bench:
            with pytest.raises(Exception, match=msg):
                run(f'{bench.benchmark_dir} --config '
                    f'{bench.benchmark_dir / "config.yml"}'.split(),
                    'benchopt', standalone_mode=False)

    @pytest.mark.parametrize('n_rep', [1, 2, 4])
    def test_caching(self, n_rep):
        # XXX - remove once this is fixed upstream with joblib/joblib#1289
        _FUNCTION_HASHES.clear()

        with temp_benchmark() as bench:

            # Check that the computation caching is working properly.
            run_cmd = (
                f"{bench.benchmark_dir} -d test-dataset -s test-solver "
                f"-n 1 -r {n_rep} --no-plot"
            ).split()

            # Make a first run that should be put in cache
            with CaptureCmdOutput() as out:
                run(run_cmd, 'benchopt', standalone_mode=False)

            # Check that this run was properly done. If only one is detected,
            # this indicates that the clean command does not work properly.
            out.check_output('test-solver:', repetition=5*n_rep+1)

            # Now check that the cache is hit when running the benchmark a
            # second time without force
            with CaptureCmdOutput() as out:
                run(run_cmd, 'benchopt', standalone_mode=False)

            out.check_output('test-solver:', repetition=1)

            # Check that the cache is also hit when running in parallel
            with CaptureCmdOutput() as out:
                run(run_cmd + ['-j', 2], 'benchopt', standalone_mode=False)

            out.check_output('test-solver:', repetition=1)

            # Make sure that -f option forces the re-run for the solver
            run_cmd[3] = '-f'
            with CaptureCmdOutput() as out:
                run(run_cmd, 'benchopt', standalone_mode=False)

            out.check_output('test-solver:', repetition=5*n_rep+1)

    def test_changing_output_name(self):
        with temp_benchmark() as bench, CaptureCmdOutput() as out:
            command = (
                f"{bench.benchmark_dir} -d test-dataset  -n 1 --no-plot "
                "--output unique_name".split()
            )
            run(command, 'benchopt', standalone_mode=False)
            run(command, 'benchopt', standalone_mode=False)

        names = [Path(result_file).stem for result_file in out.result_files]
        assert names[0] == 'unique_name' and names[1] == 'unique_name_1', out

    def test_handle_class_init_error(self):
        # dataset with a wrong param name
        dataset = """from benchopt import BaseDataset
            class Dataset(BaseDataset):
                name = 'buggy-dataset'
                parameters = {'wrong_param_name': [1]}
                def __init__(self, param=1.): pass
                def get_data(self): return dict()
        """
        with temp_benchmark(datasets=dataset) as bench:
            run_cmd = f"{bench.benchmark_dir} -n 1 --no-plot".split()

            error_match = """Dataset: "buggy-dataset".*'wrong_param_name'"""
            with pytest.raises(TypeError, match=error_match):
                run(run_cmd, 'benchopt', standalone_mode=False)

    def test_result_collection(self, no_debug_log):
        solver = """
            from benchopt import BaseSolver

            class Solver(BaseSolver):
                name = 'test-solver'
                parameters = {'param': [0]}
                def set_objective(self, X, y, lmbd): pass
                def run(self, n_iter): print(f'#RUN{self.param}')
                def get_result(self): return dict(beta=None)
            """

        with temp_benchmark(solvers=[solver]) as bench:
            with CaptureCmdOutput() as out:
                run([str(bench.benchmark_dir),
                    *'-d test-dataset -n 1 -r 1 --no-plot'.split(),
                    *'-s test-solver'.split()],
                    'benchopt', standalone_mode=False)

            out.check_output('#RUN0', repetition=2)
            out.check_output('#RUN1', repetition=0)

            with CaptureCmdOutput() as out:
                run([
                    str(bench.benchmark_dir),
                    *'-d test-dataset -n 1 -r 1 --no-plot --collect'.split(),
                    *'-s test-solver[param=[0,1]]'.split()
                ], 'benchopt', standalone_mode=False)

            # check that no solver where run
            out.check_output('#RUN0', repetition=0)
            out.check_output('#RUN1', repetition=0)

            # check that the results where collected for the correct solvers
            assert len(out.result_files) == 1, out
            out.check_output(r'done \(not enough run\)', repetition=1)
            out.check_output('not run yet', repetition=1)

    def test_complete_bench(self, bench_completion_cases):  # noqa: F811

        # Completion for benchmark name
        _test_shell_completion(run, [], bench_completion_cases)

    def test_complete_solvers(self, solver_completion_cases):  # noqa: F811
        benchmark_dir, solver_completion_cases = solver_completion_cases

        # Completion for solvers
        _test_shell_completion(
            run, [str(benchmark_dir), '-s'], solver_completion_cases
        )

    def test_complete_datasets(self, dataset_completion_cases):  # noqa: F811
        benchmark_dir, dataset_completion_cases = dataset_completion_cases

        # Completion for datasets
        _test_shell_completion(
            run, [str(benchmark_dir), '-d'], dataset_completion_cases
        )


class TestInstallCmd:

    @pytest.mark.parametrize('invalid_benchmark, match', [
        ('invalid_benchmark', "Path 'invalid_benchmark' does not exist."),
        ('.', "The folder '.' does not contain `objective.py`")],
        ids=['invalid_path', 'no_objective'])
    def test_invalid_benchmark(self, invalid_benchmark, match):
        with pytest.raises(click.BadParameter, match=re.escape(match)):
            install([invalid_benchmark], 'benchopt', standalone_mode=False)

    def test_invalid_dataset(self):
        with temp_benchmark() as bench:
            with pytest.raises(click.BadParameter, match="invalid_dataset"):
                cmd = f"{bench.benchmark_dir} -d invalid_dataset -y".split()
                install(cmd, 'benchopt', standalone_mode=False)

    def test_invalid_solver(self):
        with temp_benchmark() as bench:
            with pytest.raises(click.BadParameter, match="invalid_solver"):
                cmd = f"{bench.benchmark_dir} -s invalid_solver -y".split()
                install(cmd, 'benchopt', standalone_mode=False)

    def test_valid_call(self):
        with temp_benchmark() as bench, CaptureCmdOutput() as out:
            install(
               f"{bench.benchmark_dir} -d test-dataset -s test-solver "
               "-y".split(), 'benchopt', standalone_mode=False
            )

        out.check_output(f"Installing '{bench.name}' requirements")
        out.check_output("already available\n", repetition=3)
        out.check_output("- simulated", repetition=0)

    def test_download_data(self):

        # solver with missing dependency specified
        dataset = """from benchopt import BaseDataset

            class Dataset(BaseDataset):
                name = 'test_dataset'
                def get_data(self): print("LOAD DATA")
        """
        with temp_benchmark(datasets=[dataset]) as benchmark:
            with CaptureCmdOutput() as out:
                install([
                    *f'{benchmark.benchmark_dir} -d test_dataset '
                    '-y --download'.split()
                ], 'benchopt', standalone_mode=False)

        out.check_output("LOAD DATA", repetition=1)
        out.check_output("Loading data:", repetition=1)

    def test_existing_empty_env(self, empty_env_name):
        msg = (
            f"`benchopt` is not installed in existing env '{empty_env_name}'"
        )
        with temp_benchmark() as bench:
            with pytest.raises(RuntimeError, match=msg):
                install(
                    [str(bench.benchmark_dir), '--env-name', empty_env_name],
                    'benchopt', standalone_mode=False
                )

    def test_benchopt_install_in_env(self, test_env_name):
        with temp_benchmark() as bench, CaptureCmdOutput() as out:
            install(
                [str(bench.benchmark_dir), '--env-name', test_env_name],
                'benchopt', standalone_mode=False
            )

        out.check_output(
            f"Installing '{bench.name}' requirements"
        )
        out.check_output(
            f"already available in '{test_env_name}'\n", repetition=4
        )

    def test_benchopt_install_in_env_with_requirements(
        self, test_env_name, uninstall_dummy_package
    ):

        objective = """
            from benchopt import BaseObjective

            import dummy_package

            class Objective(BaseObjective):
                name = "requires_dummy"
                install_cmd = 'conda'
                requirements = [
                    'pip::git+https://github.com/tommoral/dummy_package'
                ]
                def set_data(self): pass
                def evaluate_result(self, beta): pass
                def get_one_result(self): pass
                def get_objective(self): pass
        """

        with temp_benchmark(objective=objective) as bench:
            objective = bench.get_benchmark_objective()
            if not objective.is_installed(env_name=test_env_name):
                install(
                    [str(bench.benchmark_dir), '--env-name', test_env_name],
                    'benchopt', standalone_mode=False
                )
            assert objective.is_installed(
                env_name=test_env_name, raise_on_not_installed=True
            )

    def test_error_with_missing_requirements(self):

        # solver with missing dependency specified
        missing_deps_cls = """from benchopt import Base{Cls}
            import invalid_module

            class {Cls}(Base{Cls}):
                name = 'buggy-class'
                install_cmd = 'conda'
                def get_data(self): pass
                def set_objective(self): pass
                def run(self): pass
                def get_result(self): pass
        """

        dataset = missing_deps_cls.format(Cls='Dataset')
        with temp_benchmark(datasets=dataset) as benchmark:
            match = "not importable:\nDataset\n- buggy-class"
            with pytest.raises(AttributeError, match=re.escape(match)):
                with CaptureCmdOutput():
                    install(
                        f'{benchmark.benchmark_dir} -d buggy-class -y'.split(),
                        'benchopt', standalone_mode=False
                    )

        solver = missing_deps_cls.format(Cls='Solver')
        with temp_benchmark(solvers=solver) as benchmark:
            match = "not importable:\nSolver\n- buggy-class"
            with pytest.raises(AttributeError, match=re.escape(match)):
                with CaptureCmdOutput():
                    install(
                        f'{benchmark.benchmark_dir} -s buggy-class -y'.split(),
                        'benchopt', standalone_mode=False
                    )

    def test_minimal_installation(
            self, test_env_name, uninstall_dummy_package, no_debug_log
    ):
        objective = """
            import dummy_package
            from benchopt import BaseObjective

            class Objective(BaseObjective):
                name = "requires_dummy"
                requirements = [
                    'pip::git+https://github.com/tommoral/dummy_package'
                ]
                def set_data(self): pass
                def evaluate_result(self, beta): pass
                def get_one_result(self): pass
                def get_objective(self): pass
        """

        solver = """from benchopt import BaseSolver
            import fake_benchopt_package

            class Solver(BaseSolver):
                name = 'solver1'
                requirements = ["fake_benchopt_package"] # raise if installed
                def set_objective(self, X, y, lmbd): pass
                def run(self, n_iter): pass
                def get_result(self): pass
        """

        dataset = """from benchopt import BaseDataset
            import fake_benchopt_package

            class Dataset(BaseDataset):
                name = 'dataset1'
                requirements = ["fake_benchopt_package"] # raise if installed
                def get_data(): pass
        """

        # Install should succeed because of --minimal option that does
        # not install the fake package in solver
        with temp_benchmark(objective=objective,
                            solvers=[solver],
                            datasets=[dataset]) as benchmark:
            with CaptureCmdOutput() as out:
                install([
                    *f'{benchmark.benchmark_dir} -y --minimal '
                    f'--env-name {test_env_name}'.split()
                ], 'benchopt', standalone_mode=False)

        out.check_output('Checking installed packages... done')

    def test_no_error_minimal_requirements(
            self, test_env_name, uninstall_dummy_package
    ):

        objective = """
            import dummy_package
            from benchopt import BaseObjective

            class Objective(BaseObjective):
                name = "requires_dummy"
                install_cmd = 'conda'
                requirements = [
                    'pip::git+https://github.com/tommoral/dummy_package'
                ]
                def set_data(self): pass
                def evaluate_result(self, beta): pass
                def get_one_result(self): pass
                def get_objective(self): pass
        """

        # solver with missing dependency specified
        missing_deps_dataset = """
            import dummy_package
            from benchopt import BaseDataset

            class Dataset(BaseDataset):
                name = 'test-dataset'
                def get_data(self): pass
        """

        with temp_benchmark(
                objective=objective,
                datasets=[missing_deps_dataset]
        ) as benchmark:
            with CaptureCmdOutput() as out:
                install([
                    *f'{benchmark.benchmark_dir} -d test-dataset -y '
                    f'--env-name {test_env_name}'.split()
                ], 'benchopt', standalone_mode=False)
        out.check_output(
            r"git\+https://github.com/tommoral/dummy_package"
        )

    def test_complete_bench(self, bench_completion_cases):  # noqa: F811

        # Completion for benchmark name
        _test_shell_completion(install, [], bench_completion_cases)

    def test_complete_solvers(self, solver_completion_cases):  # noqa: F811
        benchmark_dir, solver_completion_cases = solver_completion_cases

        # Completion for solvers
        _test_shell_completion(
            install, [str(benchmark_dir), '-s'], solver_completion_cases
        )

    def test_complete_datasets(self, dataset_completion_cases):  # noqa: F811
        benchmark_dir, dataset_completion_cases = dataset_completion_cases

        # Completion for datasets
        _test_shell_completion(
            install, [str(benchmark_dir), '-d'], dataset_completion_cases
        )


class TestPlotCmd:

    @classmethod
    def setup_class(cls):
        "Make sure at least one result file is available"
        cls.ctx = temp_benchmark()
        cls.bench = cls.ctx.__enter__()
        with CaptureCmdOutput(delete_result_files=False) as out:
            run(
                f"{cls.bench.benchmark_dir} -d test-dataset -n 2 -r 1 "
                "--no-plot".split(), 'benchopt', standalone_mode=False
            )
        assert len(out.result_files) == 1, out
        result_file = out.result_files[0]
        cls.result_file = result_file
        cls.result_file = str(
            Path(result_file).resolve().relative_to(Path().resolve())
        )

    @classmethod
    def teardown_class(cls):
        "Make sure at least one result file is available"
        cls.ctx.__exit__(None, None, None)

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
            plot(f"{self.bench.benchmark_dir} -k invalid_kind --html "
                 f"--no-display".split(), 'benchopt', standalone_mode=False)

    @pytest.mark.parametrize('kind', PLOT_KINDS)
    def test_valid_call(self, kind):

        with CaptureCmdOutput() as out:
            plot(f"{self.bench.benchmark_dir} -f {self.result_file} -k {kind} "
                 "--no-display --no-html".split(),
                 'benchopt', standalone_mode=False)

        assert len(out.result_files) == 1
        assert kind in out.result_files[0]
        assert '.pdf' in out.result_files[0]

    def test_valid_call_html(self):

        with CaptureCmdOutput() as out:
            plot(f"{self.bench.benchmark_dir} -f {self.result_file} "
                 "--no-display --html".split(),
                 'benchopt', standalone_mode=False)

        assert len(out.result_files) == 2
        assert all('.html' in f for f in out.result_files)

    def test_complete_bench(self, bench_completion_cases):  # noqa: F811

        # Completion for benchmark name
        _test_shell_completion(plot, [], bench_completion_cases)

    def test_complete_result_files(self):

        # Completion for result files
        _test_shell_completion(
            plot, f"{self.bench.benchmark_dir} -f".split(), [
                ('', [self.result_file]),
                (self.result_file[:-4], [self.result_file]),
                ('_invalid_file', []),
            ]
        )


class TestGenerateResultCmd:

    @classmethod
    def setup_class(cls):
        "Make sure at least one result file is available"
        cls.ctx = temp_benchmark()
        cls.bench = cls.ctx.__enter__()
        with CaptureCmdOutput(delete_result_files=False) as out:
            clean([str(cls.bench.benchmark_dir)],
                  'benchopt', standalone_mode=False)
            run(f"{cls.bench.benchmark_dir} -d test-dataset -n 2 -r 1 "
                "--no-plot --output out1".split(),
                'benchopt', standalone_mode=False)
            run(f"{cls.bench.benchmark_dir} -d test-dataset -n 2 -r 1 "
                "--no-plot --output out2".split(),
                'benchopt', standalone_mode=False)
        assert len(out.result_files) == 2, out
        cls.result_files = out.result_files

    @classmethod
    def teardown_class(cls):
        "Make sure at least one result file is available"
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


class TestArchiveCmd:

    @classmethod
    def setup_class(cls):
        "Make sure at least one result file is available"
        cls.ctx = temp_benchmark(extra_files={"README": ""})
        cls.bench = cls.ctx.__enter__()
        with CaptureCmdOutput(delete_result_files=False) as out:
            run(
                f"{cls.bench.benchmark_dir} -d test-dataset -n 2 -r 1 "
                "--no-plot".split(), 'benchopt', standalone_mode=False
            )
        assert len(out.result_files) == 1, out
        cls.result_file = out.result_files[0]

    @classmethod
    def teardown_class(cls):
        "Clean up the result file."
        cls.ctx.__exit__(None, None, None)

    @pytest.mark.parametrize('invalid_benchmark, match', [
        ('invalid_benchmark', "Path 'invalid_benchmark' does not exist."),
        ('.', "The folder '.' does not contain `objective.py`"),
        ("", rf"The folder '{CURRENT_DIR}' does not contain `objective.py`")],
        ids=['invalid_path', 'no_objective', "no_objective in default"])
    def test_invalid_benchmark(self, invalid_benchmark, match):
        with pytest.raises(click.BadParameter, match=re.escape(match)):
            if len(invalid_benchmark) > 0:
                run([invalid_benchmark], 'benchopt', standalone_mode=False)
            else:
                run([], 'benchopt', standalone_mode=False)

    def count_files_in_archive(self, archive_file):
        counts = {k: 0 for k in [
            "__pycache__", "outputs", "objective.py", "datasets",
            "solvers", "README"
        ]}

        with tarfile.open(archive_file, "r:gz") as tar:
            for elem in tar.getmembers():
                for k in counts:
                    counts[k] += k in elem.name
                assert elem.uname == "benchopt"
        return counts

    def test_call(self):

        with CaptureCmdOutput(delete_result_files=False) as out:
            archive([str(self.bench.benchmark_dir)], 'benchopt',
                    standalone_mode=False)

        try:
            assert len(out.result_files) == 1
            saved_file = out.result_files[0]
            counts = self.count_files_in_archive(saved_file)
        finally:
            # Make sure to clean up all files even when the test fails
            for f in out.result_files:
                Path(f).unlink()

        assert counts["README"] == 1, counts
        assert counts["objective.py"] == 1, counts
        assert counts["datasets"] >= 1, counts
        assert counts["solvers"] >= 1, counts
        assert counts["outputs"] == 0, counts
        assert counts["__pycache__"] == 0, counts

    def test_call_with_outputs(self):

        with CaptureCmdOutput(delete_result_files=False) as out:
            archive(f"{self.bench.benchmark_dir} --with-outputs".split(),
                    'benchopt', standalone_mode=False)
        saved_files = re.findall(r'Results are in (.*\.tar.gz)', out.output)
        try:
            assert len(out.result_files) == 1
            saved_file = out.result_files[0]
            counts = self.count_files_in_archive(saved_file)
        finally:
            # Make sure to clean up all files even when the test fails
            for f in saved_files:
                Path(f).unlink()

        assert counts["README"] == 1, counts
        assert counts["objective.py"] == 1, counts
        assert counts["datasets"] >= 1, counts
        assert counts["solvers"] >= 1, counts
        assert counts["outputs"] >= 1, counts
        assert counts["__pycache__"] == 0, counts

    def test_complete_bench(self, bench_completion_cases):  # noqa: F811
        # Completion for benchmark name
        _test_shell_completion(archive, [], bench_completion_cases)
