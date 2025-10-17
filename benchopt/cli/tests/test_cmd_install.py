import re
import click
import pytest

from benchopt.cli.main import install
from benchopt.tests.utils import CaptureCmdOutput
from benchopt.utils.temp_benchmark import temp_benchmark

from benchopt.cli.tests.completion_cases import _test_shell_completion
from benchopt.cli.tests.completion_cases import (  # noqa: F401
    bench_completion_cases,
    solver_completion_cases,
    dataset_completion_cases
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
        out.check_output("already available ✓", repetition=3)
        out.check_output("- simulated", repetition=0)

    def test_invalid_install_cmd(self):
        # Solver with an invalid install command
        invalid_solver = """
        import fake_module
        from benchopt import BaseSolver

        class Solver(BaseSolver):
            name = "invalid-solver"
            install_cmd = "invalid_command"
            def set_objective(self, X, y, lmbd): pass
            def run(self, n_iter): pass
            def get_result(self): return dict(beta=1)
        """

        with temp_benchmark(solvers=invalid_solver) as bench:
            with pytest.raises(ValueError, match="is not a valid"):
                install(
                    f"{bench.benchmark_dir} -y -s invalid-solver".split(),
                    standalone_mode=False
                )

    def test_conda_default_install_cmd(self):
        # Solver class without the install_cmd attribute
        # Checks if conda is used by default.
        solver_noinstall = """
        from benchopt import BaseSolver

        class Solver(BaseSolver):
            name = "solver-no-install-cmd"
            requirements = []
            def set_objective(self, X, y, lmbd): pass
            def run(self, n_iter): pass
            def get_result(self): return dict(beta=1)
        """

        with temp_benchmark(solvers=[solver_noinstall]) as benchmark:
            SolverClass, _ = benchmark.check_solver_patterns(
                ["solver-no-install-cmd"]
            )[0]
            solver_instance = SolverClass()

            # Check that the default 'install_cmd' is 'conda'
            assert getattr(solver_instance, "install_cmd", None) == "conda"

    def test_download_data(self):

        # solver with missing dependency specified
        dataset = """from benchopt import BaseDataset

            class Dataset(BaseDataset):
                name = 'test_dataset'
                def get_data(self): print("LOAD DATA")
        """
        dataset2 = dataset.replace("dataset", "dataset2")
        with temp_benchmark(datasets=[dataset, dataset2]) as benchmark:
            with CaptureCmdOutput() as out:
                install([
                    *f'{benchmark.benchmark_dir} -d test_dataset '
                    '-y --download'.split()
                ], 'benchopt', standalone_mode=False)

            out.check_output("LOAD DATA", repetition=1)
            out.check_output("Loading data:", repetition=1)

        # Check it works with 2 datasets
            with CaptureCmdOutput() as out:
                install([
                    *f'{benchmark.benchmark_dir} -y --download '
                    '-d test_dataset -d test_dataset2'.split()
                ], 'benchopt', standalone_mode=False)

            out.check_output("LOAD DATA", repetition=2)
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

    def test_benchopt_install_in_env(self, test_env_name, no_debug_log):
        with temp_benchmark() as bench, CaptureCmdOutput() as out:
            install(
                [str(bench.benchmark_dir), '--env-name', test_env_name],
                'benchopt', standalone_mode=False
            )

        out.check_output(
            f"Installing '{bench.name}' requirements"
        )
        out.check_output(
            f"already available in '{test_env_name}' ✓", repetition=4
        )

    def test_benchopt_install_in_env_with_requirements(
        self, test_env_name, uninstall_dummy_package, no_debug_log
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
            with CaptureCmdOutput() as out:
                install(
                    [str(bench.benchmark_dir), '--env-name', test_env_name],
                    'benchopt', standalone_mode=False
                )
            out.check_output(f"Installing '{bench.name}' requirements")
            out.check_output("Checking installed packages... done")
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
        with temp_benchmark(datasets=dataset) as bench:
            match = "not importable:\nDataset\n- buggy-class"
            with CaptureCmdOutput(exit=1) as out:
                install(
                    f'{bench.benchmark_dir} -d buggy-class -y'.split(),
                    'benchopt', standalone_mode=False
                )
            out.check_output(re.escape(match))

        solver = missing_deps_cls.format(Cls='Solver')
        with temp_benchmark(solvers=solver) as bench:
            match = "not importable:\nSolver\n- buggy-class"
            with CaptureCmdOutput(exit=1) as out:
                install(
                    f'{bench.benchmark_dir} -s buggy-class -y'.split(),
                    'benchopt', standalone_mode=False
                )
            out.check_output(re.escape(match))

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

    def test_gpu_flag(self, no_debug_log):

        objective = """from benchopt import BaseObjective

            class Objective(BaseObjective):
                name = "test_obj"
                min_benchopt_version = "0.0.0"

                def set_data(self, X, y): pass
                def get_one_result(self): pass
                def evaluate_result(self, beta): return dict(value=1)
                def get_objective(self): return dict(X=0, y=0)
        """

        solver1 = """from benchopt import BaseSolver

        class Solver(BaseSolver):
            name = "solver1"
            requirements = {"wrong_key": 1, "cpu": []}
        """

        solver2 = """from benchopt import BaseSolver

        class Solver(BaseSolver):
            name = "solver2"
            requirements = {"gpu": [], "cpu": ["unknown_implausible_pkg"]}
            sampling_strategy = 'iteration'
        """

        with temp_benchmark(
                objective=objective, solvers=[solver1, solver2],
        ) as bench:
            err = ("keys should be `cpu` and `gpu`, got ['wrong_key', 'cpu']")
            with CaptureCmdOutput():
                with pytest.raises(ValueError, match=re.escape(err)):
                    install(
                        f"{bench.benchmark_dir} -yf -s solver1 --gpu".split(),
                        standalone_mode=False
                    )

            success_msg = "No new requirements installed"
            # installing without gpu flag installs requirements["cpu"],
            # hence OK
            with CaptureCmdOutput() as out:
                install(f"{bench.benchmark_dir} -yf -s solver1".split(),
                        standalone_mode=False)
            out.check_output(success_msg)

            # all good with requirements["gpu"] for solver2, hence no error
            with CaptureCmdOutput() as out:
                install(f"{bench.benchmark_dir} -yf -s solver2 --gpu".split(),
                        standalone_mode=False)
            out.check_output(success_msg)

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
