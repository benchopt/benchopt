import re

import click
import pytest

from benchopt.utils.temp_benchmark import temp_benchmark

from benchopt.tests.utils import CaptureCmdOutput
from benchopt.utils.shell_cmd import _run_shell_in_conda_env

from benchopt.cli.main import test as benchopt_test

from benchopt.cli.tests.completion_cases import _test_shell_completion
from benchopt.cli.tests.completion_cases import (  # noqa: F401
    bench_completion_cases
)


class TestCmdTest:

    @pytest.mark.parametrize('invalid_benchmark, match', [
        ('invalid_benchmark', "Path 'invalid_benchmark' does not exist."),
        ('.', "The folder '.' does not contain `objective.py`")],
        ids=['invalid_path', 'no_objective'])
    def test_invalid_benchmark(self, invalid_benchmark, match):
        with pytest.raises(click.BadParameter, match=re.escape(match)):
            benchopt_test(
                [invalid_benchmark], 'benchopt', standalone_mode=False
            )

    def test_valid_call(self):
        with temp_benchmark() as bench, CaptureCmdOutput() as out:
            benchopt_test(
                f"{bench.benchmark_dir} --skip-install".split(),
                'benchopt', standalone_mode=False
            )

        out.check_output("test session starts", repetition=1)
        out.check_output("PASSED")
        out.check_output("FAILED", repetition=0)

        # Skip install tests (one per solver/dataset ->3)..
        out.check_output("SKIPPED", repetition=3)

        # Default temp benchmark has at least one passing ``test_solver_run``
        # variant, so the all-skipped error must not appear.
        out.check_output(
            "Skipped every test_solver_run variants", repetition=0
        )

    def test_valid_call_fail(self):
        solver = """
        from benchopt.utils.temp_benchmark import TempSolver
        class Solver(TempSolver):
            name = "failing-solver"
            def run(self, _): raise ValueError("Intentional Error")
        """
        with temp_benchmark(solvers=solver) as bench:
            with CaptureCmdOutput(exit=1) as out:
                benchopt_test(
                    f"{bench.benchmark_dir} --skip-install".split(),
                    'benchopt', standalone_mode=False
                )

        out.check_output("test session starts", repetition=1)
        out.check_output("PASSED")
        out.check_output("FAILED", repetition=2)
        # Skip install tests (one per solver/dataset ->3).
        out.check_output("SKIPPED", repetition=3)

    def test_invalid_benchmark_config_is_detected(self):
        config = """
        invalid_bench_key: true
        """

        with temp_benchmark(config=config) as bench:
            with CaptureCmdOutput(exit=1) as out:
                benchopt_test(
                    f"{bench.benchmark_dir} --skip-install -rN "
                    "-k test_benchmark_config_validity".split(),
                    'benchopt', standalone_mode=False
                )

        out.check_output("test session starts", repetition=1)
        out.check_output("FAILED", repetition=1)
        out.check_output("Invalid benchmark config.yml detected", repetition=2)
        out.check_output("invalid_bench_key .*config.yml", repetition=1)

    @pytest.mark.parametrize('t, pat, pat_new, error_type', [
        ("data", "", "", None),
        ("data", "test_parameters", "wrong_parameters", "AssertionError"),
        ("data", "[True]", "[False]", "AssertionError"),
        ("obj", "test_dataset_name = \"my_test_data\"", "", "TypeError"),
        ("obj", "my_test_data", "simulated", "TypeError"),
        ("obj", "my_test_data", "invalid_data", "AssertionError")
    ], ids=[
        "valid", "data_no_test_params", "data_wrong_test_params",
        "obj_no_test_dataset", "obj_wrong_test_dataset",
        "obj_invalid_test_dataset"
    ])
    def test_setting_test_dataset_and_params(
            self, t, pat, pat_new, error_type
    ):
        dataset = """
        from benchopt import BaseDataset
        class Dataset(BaseDataset):
            name = "my_test_data"
            parameters = {'p': [False]}
            test_parameters = {'p': [True]}
            def get_data(self):
                assert self.p
                return dict(X=None, y=None)
        """
        # This one should fail if called
        dataset2 = """
        from benchopt import BaseDataset
        class Dataset(BaseDataset):
            name = "simulated"
            def get_data(self): return dict(no_data=0)
        """
        objective = """
        from benchopt.utils.temp_benchmark import TempObjective
        class Objective(TempObjective):
            name = "test obj"
            test_dataset_name = "my_test_data"
        """

        n_pass = 0 if error_type is not None else 1
        n_fail = 2 if error_type is not None else 0
        exit_code = 1 if error_type is not None else None

        # Now check that when not set properly, or to otther values, this fails
        dataset_, objective_ = dataset, objective
        if t == "data":
            dataset_ = dataset_.replace(pat, pat_new)
        else:
            objective_ = objective_.replace(pat, pat_new)
        with temp_benchmark(
                datasets=[dataset_, dataset2], objective=objective_
        ) as bench:
            with CaptureCmdOutput(exit=exit_code) as out:
                benchopt_test(
                    f"{bench.benchmark_dir} --skip-install "
                    "-k test_benchmark_objective".split(),
                    'benchopt', standalone_mode=False
                )

            out.check_output("test session starts", repetition=1)
            out.check_output("PASSED", repetition=n_pass)
            out.check_output("FAILED", repetition=n_fail)
            if error_type is not None:
                out.check_output(error_type, repetition=3)

    @pytest.mark.parametrize('params, exit_code, n_data', [
        ([0], None, 1),
        ([0, 1, 2], None, 1),
        ([2, 1, 0], None, 3),
        ([1], 1, 1),
        ([3, 2, 1], 1, 3),
    ], ids=[
        "valid", "first", "last", "invalid", "invalid_multiple"
    ])
    def test_setting_test_parameters(
            self, params, exit_code, n_data
    ):
        dataset = """
        from benchopt.utils.temp_benchmark import TempDataset
        class Dataset(TempDataset):
            name = "my_test_data"
            parameters = {'p': [False]}
            test_parameters = {'p': #TEST_PARAMS}
            def get_data(self):
                print(f"Dataset#{self.p}")
                return dict(p=self.p)
        """.replace("#TEST_PARAMS", str(params))
        objective = """
        from benchopt.utils.temp_benchmark import TempObjective
        class Objective(TempObjective):
            name = "test obj"
            def set_data(self, p): self.p = p
            def get_objective(self): return dict(p=self.p)
        """
        solver = """
        from benchopt.utils.temp_benchmark import TempSolver
        class Solver(TempSolver):
            name = "test solver"
            def skip(self, p):
                if p > 0: return True, "skip for p > 0"
                return False, None
            def set_objective(self, p): self.p = p
        """

        with temp_benchmark(
                datasets=dataset, objective=objective, solvers=solver
        ) as bench:
            with CaptureCmdOutput(exit=exit_code) as out:
                benchopt_test(
                    f"{bench.benchmark_dir} --skip-install "
                    "-sk test_solver_run".split(),
                    'benchopt', standalone_mode=False
                )

            out.check_output("test session starts", repetition=1)
            out.check_output("Dataset#", repetition=n_data)
            if exit_code is not None:
                out.check_output("Skipped every test_solver_run variants")
                out.check_output("skip for p > 0")

    # Exepected corresponds to solver, objective and dataset p respectively.
    @pytest.mark.parametrize('d_conf, o_conf, s_conf, expected', [
        (None, None, None, (0, 0, 0)),
        (1, None, None, (0, 0, 1)),
        (None, (1, 1), None, (0, 1, 1)),
        (1, (2, 2), None, (0, 2, 2)),
        (None, None, (1, 1, None), (1, 1, 0)),
        (None, (2, 2), (1, 1, None), (1, 1, 2)),
        (None, None, (1, None, 1), (1, 0, 1)),
        (3, (2, 2), (1, None, 1), (1, 2, 1)),
        (None, None, (1, 1, 1), (1, 1, 1)),
        (3, (2, 2), (1, 1, 1), (1, 1, 1)),
        (3, (2, None), (1, None, None), (1, 2, 3)),
    ], ids=[
        'no_test_config', 'dataset_specifies_config',
        'objective_specifies_dataset', 'objective_overrides_dataset',
        'solver_specifies_objective', 'solver_overrides_objective',
        'solver_specifies_dataset', 'solver_override_dataset',
        'solver_specifies_all', 'solver_overrides_all',
        'all_specifies_config',
    ])
    def test_setting_test_config(self, d_conf, o_conf, s_conf, expected):
        dataset = """
        from benchopt import BaseDataset
        class Dataset(BaseDataset):
            name = "simulated"
            parameters = {'p': [0]}
            # TEST_CONFIG
            def get_data(self):
                print(f"Dataset#{self.p}")
                return dict(data=None)
        """
        objective = """
        from benchopt.utils.temp_benchmark import TempObjective
        class Objective(TempObjective):
            name = "test-objective"
            parameters = {'p': [0]}
            # TEST_CONFIG
            def set_data(self, data): print(f"Objective#{self.p}")
        """
        solver = """
        from benchopt.utils.temp_benchmark import TempSolver
        class Solver(TempSolver):
            name = "test-solver"
            parameters = {'p': [0]}
            # TEST_CONFIG
            def run(self, _): print(f"Solver#{self.p}")
        """
        # Setup dataset test_config
        if d_conf is not None:
            d_conf = {'p': d_conf}
            dataset = dataset.replace(
                '# TEST_CONFIG', f"test_config = {d_conf}"
            )
        if o_conf is not None:
            o_conf = {
                k: (v if k == "p" else {'p': v})
                for k, v in zip(['p', 'dataset'], o_conf)
                if v is not None
            }
            objective = objective.replace(
                '# TEST_CONFIG', f"test_config = {o_conf}"
            )
        if s_conf is not None:
            s_conf = {
                k: (v if k == "p" else {'p': v})
                for k, v in zip(['p', 'objective', 'dataset'], s_conf)
                if v is not None
            }
            solver = solver.replace(
                '# TEST_CONFIG', f"test_config = {s_conf}"
            )

        with temp_benchmark(
            datasets=dataset, objective=objective, solvers=solver
        ) as bench:
            with CaptureCmdOutput() as out:
                benchopt_test(
                    f"{bench.benchmark_dir} -sk test_solver_run".split(),
                    'benchopt', standalone_mode=False
                )
        for k, v in zip(['Solver', 'Objective', 'Dataset'], expected):
            out.check_output(f"{k}#{v}", repetition=1)

    @pytest.mark.parametrize('source, value, expected', [
        ('objective', "'data_a'", ['data_a']),
        ('objective', "['data_a', 'data_b']", ['data_a', 'data_b']),
        ('solver', "'data_b'", ['data_b']),
        ('solver', "['data_a', 'data_b']", ['data_a', 'data_b']),
    ], ids=[
        'objective_str', 'objective_list',
        'solver_str', 'solver_list',
    ])
    def test_test_config_dataset_name(self, source, value, expected):
        # ``Solver``/``Objective`` can pick the test dataset via
        # ``test_config['dataset']['name']``, accepting either a string or
        # a list. A list parametrizes the test once per name.
        dataset_a = """from benchopt import BaseDataset
        class Dataset(BaseDataset):
            name = "data_a"
            def get_data(self):
                print("Selected#data_a")
                return dict(X=None, y=None)
        """
        dataset_b = dataset_a.replace("data_a", "data_b")
        objective = """from benchopt.utils.temp_benchmark import TempObjective
        class Objective(TempObjective):
            name = "test-objective"
            test_dataset_name = "data_a"
            # TEST_CONFIG
        """
        solver = """from benchopt.utils.temp_benchmark import TempSolver
        class Solver(TempSolver):
            name = "test-solver"
            # TEST_CONFIG
        """
        cfg = f"test_config = {{'dataset': {{'name': {value}}}}}"
        if source == 'objective':
            objective = objective.replace('# TEST_CONFIG', cfg)
        else:
            solver = solver.replace('# TEST_CONFIG', cfg)

        with temp_benchmark(
            datasets=[dataset_a, dataset_b], objective=objective,
            solvers=solver,
        ) as bench, CaptureCmdOutput() as out:
            benchopt_test(
                f"{bench.benchmark_dir} --skip-install "
                "-sk test_solver_run".split(),
                'benchopt', standalone_mode=False
            )
        for name in expected:
            out.check_output(f"Selected#{name}", repetition=1)

    def test_solver_skip_without_test_parameters_no_crash(self):
        # Non-regression: when a solver skips the default test config and
        # the dataset has no ``test_parameters``, ``test_solver_run`` should
        # skip cleanly and the session-finish hook should flag the solver,
        # rather than crashing on the malformed default config.
        solver = """from benchopt.utils.temp_benchmark import TempSolver
        class Solver(TempSolver):
            name = "always-skip-solver"
            def skip(self, **kwargs): return True, "incompatible by design"
        """
        with temp_benchmark(solvers=solver) as bench:
            with CaptureCmdOutput(exit=1) as out:
                benchopt_test(
                    f"{bench.benchmark_dir} --skip-install "
                    "-k test_solver_run".split(),
                    'benchopt', standalone_mode=False
                )
        out.check_output("Skipped every test_solver_run variants")
        out.check_output("incompatible by design")
        out.check_output("AttributeError", repetition=0)

    def test_interaction_with_run_seeding(self):
        # non-regression for benchopt/benchopt#890, where the seeding was not
        # properly initialized for the test commands.
        dataset = """
        from benchopt import BaseDataset
        class Dataset(BaseDataset):
            name = "simulated"
            def get_data(self):
                seed = self.get_seed()
                print(f"Dataset#seed={seed}")
                return dict(X=None, y=None)
        """
        with temp_benchmark(datasets=dataset) as bench:
            with CaptureCmdOutput() as out:
                benchopt_test(
                    f"{bench.benchmark_dir} -s --skip-install".split(),
                    'benchopt', standalone_mode=False
                )
            out.check_output("Dataset#seed=123370572", repetition=4)

    def test_valid_call_in_env_no_pytest(self, test_env_name, no_pytest):
        with temp_benchmark() as bench:
            msg = f"pytest is not installed in conda env {test_env_name}"
            with pytest.raises(ModuleNotFoundError, match=msg):
                assert 1 == _run_shell_in_conda_env(
                    "which pytest", env_name=test_env_name
                )
                benchopt_test(
                   f"{bench.benchmark_dir} --env-name {test_env_name}".split(),
                   'benchopt', standalone_mode=False
                )

    def test_valid_call_in_env_minimal_requirements(
            self, test_env_name, uninstall_dummy_package
    ):
        # Check that launching the tests in a conda env install minimal reqs
        objective = """from benchopt.utils.temp_benchmark import TempObjective
        import dummy_package
        class Objective(TempObjective):
            requirements = [
                'pip::git+https://github.com/tommoral/dummy_package'
            ]
        """
        with temp_benchmark(objective=objective) as bench:
            with CaptureCmdOutput(debug=True) as out:
                benchopt_test(
                   f"{bench.benchmark_dir} --env-name {test_env_name} "
                   "--skip-env".split(),
                   'benchopt', standalone_mode=False
                )
            out.check_output("Installing required packages.*\n- objective")

    def test_invalid_test_dataset_name(self, test_env_name):
        # Check that launching the tests in a conda env install minimal reqs
        objective = """from benchopt.utils.temp_benchmark import TempObjective
        class Objective(TempObjective):
            test_dataset_name = "invalid-dataset"
        """
        msg = "Bad test dataset names:.*'invalid-dataset'"
        with temp_benchmark(objective=objective) as bench:
            with pytest.raises(ValueError, match=msg):
                benchopt_test(
                   f"{bench.benchmark_dir} --env-name {test_env_name} "
                   "--skip-env".split(),
                   'benchopt', standalone_mode=False
                )

    @pytest.mark.parametrize('set_name', ['test_dataset_name', 'test_config'])
    def test_valid_call_in_env_dataset_requirements(
            self, test_env_name, uninstall_dummy_package, set_name
    ):
        # Check that launching tests in a conda env install dataset reqs
        dataset = """from benchopt.utils.temp_benchmark import TempDataset
        import dummy_package
        class Dataset(TempDataset):
            name = "reqs-dataset"
            install_cmd = 'conda'
            requirements = [
                'pip::git+https://github.com/tommoral/dummy_package'
            ]
        """
        dataset_name = (
            "test_dataset_name = 'reqs-dataset'"
            if set_name == 'test_dataset_name' else
            "test_config = {'dataset': {'name': 'reqs-dataset'}}"
        )

        objective = f"""from benchopt.utils.temp_benchmark import TempObjective
        # Non-regression: even when objective is not installed, the test
        # dataset requirements should be installed.
        import dummy_package

        class Objective(TempObjective):
            {dataset_name}
            # Need a requirement to avoid error on collect
            requirements = [""]
        """
        with temp_benchmark(
                datasets=dataset, objective=objective,
        ) as bench, CaptureCmdOutput(debug=True) as out:
            benchopt_test(
                f"{bench.benchmark_dir} --env-name {test_env_name} "
                "--skip-env".split(),
                'benchopt', standalone_mode=False,
            )
            assert bench.check_dataset_patterns(
                "reqs-dataset", class_only=True
            ).pop().is_installed(
                env_name=test_env_name, raise_on_not_installed=True,
            )
        out.check_output("Installing required packages.*\n.*\n- reqs-dataset")

    @pytest.mark.parametrize('test_name, arg, n_test', [
        ("test_dataset_get_data", "dataset_class", 2),
        ("test_dataset_get_data", "dataset", 2),
        ("test_solver_run", "solver_class", 1),
        ("test_solver_run", "solver", 1),
    ])
    @pytest.mark.parametrize('action', ['skip', 'xfail'])
    def test_check_test(self, no_debug_log, action, test_name, arg, n_test):
        test_config = f"""import pytest

        def check_{test_name}(benchmark, {arg}):
            pytest.{action}("skip for TEST")
        """

        with temp_benchmark(
            extra_files={'test_config.py': test_config}
        ) as bench, CaptureCmdOutput() as out:
            benchopt_test(
                f"{bench.benchmark_dir} -k {test_name}".split(),
                'benchopt', standalone_mode=False
            )

        out.check_output("test session starts", repetition=1)
        out.check_output(test_name, repetition=n_test)
        out.check_output(action.upper(), repetition=n_test)
        # Skips emitted from a user-provided ``check_TESTNAME`` hook happen
        # during fixture setup, so they must not trigger the per-solver
        # all-skipped failure path.
        out.check_output(
            "Every test_solver_run variant was skipped", repetition=0
        )

    def test_deprecated_check_test_solver(self):
        test_config = """import pytest

        def check_test_solver(benchmark, solver_class):
            pytest.xfail("xfail for TEST")
        """
        with temp_benchmark(
            extra_files={'test_config.py': test_config}
        ) as bench, CaptureCmdOutput() as out:
            benchopt_test(
                [str(bench.benchmark_dir), "-k", "test_solver_run"],
                'benchopt', standalone_mode=False
            )
        out.check_output("XFAIL", repetition=1)

    def test_all_skipped_error_absent_uninstalled_solver(self):
        # An uninstalled solver legitimately skips every ``test_solver_run``
        # variant with "Solver is not installed"; this is the only expected
        # reason and must not trigger the all-skipped error.
        solver = """from benchopt.utils.temp_benchmark import TempSolver
        class Solver(TempSolver):
            name = "uninstalled-solver"
            @classmethod
            def is_installed(cls, **kwargs): return False
        """
        with temp_benchmark(solvers=solver) as bench, \
                CaptureCmdOutput() as out:
            benchopt_test(
                f"{bench.benchmark_dir} --skip-install".split(),
                'benchopt', standalone_mode=False
            )
        out.check_output(
            "Skipped every test_solver_run variants", repetition=0
        )
        out.check_output("Solver is not installed", repetition=1)

    def test_all_skipped_error_on_unexpected_skip(self):
        # When every ``test_solver_run`` variant skips for a reason other
        # than "Solver is not installed", the session is flagged and exits 1.
        solver = """from benchopt.utils.temp_benchmark import TempSolver
        import pytest
        class Solver(TempSolver):
            name = "skip-solver"
            @classmethod
            def skip(cls, **kwargs): pytest.skip("incompatible")
        """
        with temp_benchmark(
                solvers=solver
        ) as bench, CaptureCmdOutput(exit=1) as out:
            benchopt_test(
                f"{bench.benchmark_dir} --skip-install".split(),
                'benchopt', standalone_mode=False
            )
        out.check_output("Skipped every test_solver_run variants")
        out.check_output("skip-solver")
        out.check_output("incompatible")

    def test_test_dataset_not_installed_skip_message(self):
        # Check that the correct error message is displayed when the test
        # dataset is not installed.
        dataset = """from benchopt.utils.temp_benchmark import TempDataset
        class Dataset(TempDataset):
            name = "my-test-dataset"
            @classmethod
            def is_installed(cls, **kwargs): return False
        """
        objective = """from benchopt.utils.temp_benchmark import TempObjective
        class Objective(TempObjective):
            name = "test obj"
            test_dataset_name = "my-test-dataset"
        """
        with temp_benchmark(
                datasets=dataset, objective=objective
        ) as bench, CaptureCmdOutput(exit=1) as out:
            benchopt_test(
                f"{bench.benchmark_dir} --skip-install".split(),
                'benchopt', standalone_mode=False
            )
        out.check_output("Test dataset 'my-test-dataset' is not installed")
        out.check_output("Skipped every test_solver_run variants")

    def test_complete_bench(self, bench_completion_cases):  # noqa: F811

        # Completion for benchmark name
        _test_shell_completion(benchopt_test, [], bench_completion_cases)
