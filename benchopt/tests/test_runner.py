import pytest
import inspect

from benchopt.cli.main import run
from benchopt.results import read_results
from benchopt.utils.temp_benchmark import temp_benchmark
from benchopt.tests.utils import CaptureCmdOutput


@pytest.mark.parametrize('n_jobs', [1, 2, 4])
def test_skip_api(n_jobs):

    objective = """from benchopt.utils.temp_benchmark import TempObjective

        class Objective(TempObjective):
            name = "Objective-skip"
            parameters = dict(should_skip=[True, False])

            def skip(self, X, y):
                if self.should_skip:
                    return True, "Objective#SKIP"
                return False, None
    """

    solver = """from benchopt.utils.temp_benchmark import TempSolver

    class Solver(TempSolver):
        name = "test-solver"
        sampling_strategy = 'run_once'
        parameters = dict(should_skip=[True, False])
        def run(self, n_iter): print("Solver#RUN")

        def skip(self, **obj):
            if self.should_skip:
                return True, "Solver#SKIP"
            return False, None

    """

    with temp_benchmark(objective=objective, solvers=[solver]) as benchmark:
        with CaptureCmdOutput() as out:
            run([*(
                f'{benchmark.benchmark_dir} -s test-solver -d test-dataset '
                f'-j {n_jobs} --no-plot'
            ).split()], standalone_mode=False)

            # Make sure joblib's executor is shutdown, as otherwise the output
            # might be incomplete.
            from joblib.externals.loky import get_reusable_executor
            get_reusable_executor().shutdown(wait=True)

    out.check_output(r"Objective-skip\[should_skip=True\] skip", repetition=1)
    out.check_output("Reason: Objective#SKIP", repetition=1)

    out.check_output(r"test-solver\[should_skip=True\]: skip", repetition=1)
    out.check_output("Reason: Solver#SKIP", repetition=1)

    out.check_output(r"test-solver\[should_skip=False\]: done", repetition=1)
    out.check_output("Solver#RUN", repetition=1)


# Under windows, the function needs to be pickleable
# for parallel jobs to work with joblib
@pytest.mark.parametrize('n_jobs', [1, 2])
def test_benchopt_run_script(n_jobs, no_debug_log):
    from benchopt import run_benchmark

    with temp_benchmark() as benchmark:
        with CaptureCmdOutput() as out:
            run_benchmark(
                str(benchmark.benchmark_dir),
                solver_names=["test-solver"],
                dataset_names=["simulated"],
                max_runs=2, n_repetitions=1, n_jobs=n_jobs, plot_result=False
            )

    out.check_output('simulated', repetition=1)
    out.check_output('test-objective', repetition=1)
    out.check_output('test-solver:', repetition=4)
    out.check_output('template_solver:', repetition=0)

    # Make sure the results were saved in a result file
    assert len(out.result_files) == 1, out.output


def test_prefix_with_same_parameters():
    from benchopt import run_benchmark

    solver1 = """from benchopt.utils.temp_benchmark import TempSolver

        class Solver(TempSolver):
            name = "solver1"
            sampling_strategy = 'iteration'
            parameters = dict(seed=[3, 27])
    """

    # Different name and extra parameter
    solver2 = (
        solver1.replace("solver1", "solver2")
        .replace('seed=[3, 27]', 'seed=[2, 28], type=["s"]')
    )

    dataset1 = """from benchopt.utils.temp_benchmark import TempDataset

        class Dataset(TempDataset):
            name = "dataset1"
            parameters = dict(seed=[3, 27])
    """

    # Different name and extra parameter
    dataset2 = (
        dataset1.replace("dataset1", "dataset2")
        .replace('seed=[3, 27]', 'seed=[2, 28], type=["d"]')
    )

    objective = """from benchopt.utils.temp_benchmark import TempObjective

        class Objective(TempObjective):
            name = "test_obj"
            parameters = dict(test_p=[4])
    """

    with temp_benchmark(solvers=[solver1, solver2],
                        datasets=[dataset1, dataset2],
                        objective=objective
                        ) as benchmark:
        run_benchmark(
            str(benchmark.benchmark_dir),
            solver_names=["solver1", "solver2"],
            dataset_names=["dataset1", "dataset2"],
            max_runs=1, n_repetitions=1, n_jobs=1, plot_result=False
        )

        df = read_results(benchmark.get_result_files()[0])

        assert "p_solver_seed" in df.columns
        assert "p_solver_type" in df.columns
        assert "p_dataset_seed" in df.columns
        assert "p_dataset_type" in df.columns
        assert "p_obj_test_p" in df.columns

        assert df.query("p_solver_seed.isna()").shape[0] == 0
        no_type = df.query("p_solver_type.isna()")['solver_name'].unique()
        assert all('solver1' in s for s in no_type)

        assert df.query("p_dataset_seed.isna()").shape[0] == 0
        no_type = df.query("p_dataset_type.isna()")['dataset_name'].unique()
        assert all('dataset1' in s for s in no_type)

        assert df.query("p_obj_test_p.isna()").shape[0] == 0

        # No mixing
        assert "d" not in df['p_solver_type'].unique()
        assert "s" in df['p_solver_type'].unique()
        assert "s" not in df['p_dataset_type'].unique()
        assert "d" in df['p_dataset_type'].unique()


def test_warmup_error(no_debug_log):
    # Non-regression test for benchopt/benchopt#808
    from benchopt import run_benchmark

    solver = """from benchopt.utils.temp_benchmark import TempSolver

        class Solver(TempSolver):
            name = "solver1"
            sampling_strategy = 'iteration'
            def warm_up(self): raise RuntimeError("Warmup error")
    """

    with temp_benchmark(solvers=solver) as benchmark:
        with CaptureCmdOutput() as out, pytest.raises(RuntimeError):
            run_benchmark(
                str(benchmark.benchmark_dir),
                solver_names=["solver1"],
                dataset_names=["test-dataset"],
                max_runs=1, n_repetitions=1, n_jobs=1, plot_result=False
            )
        out.check_output("RuntimeError: Warmup error", repetition=1)
        out.check_output("UnboundLocalError", repetition=0)
        out.check_output("No output produced.", repetition=1)


class TestCache:
    """Test the cache of the benchmark."""

    solver = """from benchopt.utils.temp_benchmark import TempSolver

    class Solver(TempSolver):
        name = "test-solver"
        sampling_strategy = 'run_once'
        def run(self, _): print("#RUN_SOLVER")
    """

    dataset = """from benchopt.utils.temp_benchmark import TempDataset

    class Dataset(TempDataset):
        name = "test-dataset"
    """

    @pytest.mark.parametrize('n_reps', [1, 4])
    def test_cache(self, no_debug_log, n_reps):
        with temp_benchmark(
                solvers=self.solver, datasets=self.dataset
        ) as bench:
            with CaptureCmdOutput() as out:
                for it in range(3):
                    run(f"{bench.benchmark_dir} --no-plot -r {n_reps}".split(),
                        standalone_mode=False)

        # Check that the run are only call once per repetition, but not cached
        # when using multiple repetitions
        out.check_output("#RUN_SOLVER", repetition=n_reps)

    @pytest.mark.parametrize('n_reps', [1, 4])
    def test_no_cache(self, no_debug_log, n_reps):
        with temp_benchmark(
                solvers=self.solver, datasets=self.dataset
        ) as bench:
            with CaptureCmdOutput() as out:
                for it in range(3):
                    run(f"{bench.benchmark_dir} --no-plot -r {n_reps} "
                        "--no-cache".split(), standalone_mode=False)

        # Check that the run is not cached when using --no-cache
        out.check_output("#RUN_SOLVER", repetition=n_reps * 3)

    def test_no_error_caching(self, no_debug_log):

        solver_fail = """from benchopt.utils.temp_benchmark import TempSolver

        class Solver(TempSolver):
            name = "failing-solver"
            def run(self, n_iter):
                raise ValueError('Failing solver.')
        """

        with temp_benchmark(solvers=[self.solver, solver_fail],
                            datasets=self.dataset) as bench:
            with CaptureCmdOutput() as out:
                for it in range(3):
                    run(f"{bench.benchmark_dir} --no-plot -r 1 -n 1".split(),
                        standalone_mode=False)

        # error message should be displayed twice
        out.check_output("ValueError: Failing solver.", repetition=3)

    @pytest.mark.parametrize('n_reps', [1, 4])
    def test_cache_order(self, no_debug_log, n_reps):
        with temp_benchmark(
                datasets=self.dataset,
                solvers=[
                    self.solver,
                    self.solver.replace("test-solver", "test-solver2")
                    .replace("#RUN_SOLVER", "#RUN_2SOLVER")
                ]
        ) as bench:
            with CaptureCmdOutput() as out:
                run([str(bench.benchmark_dir),
                     *"-s test-solver -s test-solver2 "
                     f'--no-plot -r {n_reps}'.split()],
                    standalone_mode=False)
                run([str(bench.benchmark_dir),
                     *"-s test-solver2 -s test-solver "
                    f'--no-plot -r {n_reps}'.split()],
                    standalone_mode=False)

        # Check that the run are only call once per repetition, but not cached
        # when using multiple repetitions
        out.check_output("#RUN_SOLVER", repetition=n_reps)
        out.check_output("#RUN_2SOLVER", repetition=n_reps)

    @pytest.mark.parametrize('n_reps', [1, 4])
    def test_cache_invalid(self, no_debug_log, n_reps):
        with temp_benchmark(
                datasets=self.dataset, solvers=self.solver,
        ) as bench:
            with CaptureCmdOutput() as out:
                run(f"{bench.benchmark_dir} --no-plot -r {n_reps}".split(),
                    standalone_mode=False)
                # Modify the solver, to make the cache invalid
                solver_file = bench.benchmark_dir / 'solvers' / 'solver_0.py'
                modified_solver = inspect.cleandoc(self.solver.replace(
                    "#RUN_SOLVER", "#RUN_SOLVER_MODIFIED"
                ))
                assert solver_file.exists()
                solver_file.write_text(inspect.cleandoc(modified_solver))

                run(f"{bench.benchmark_dir} --no-plot -r {n_reps} -j2".split(),
                    standalone_mode=False)

        # Check that the 2nd run is not cached and the cache is invalidated.
        out.check_output("#RUN_SOLVER_MODIFIED", repetition=n_reps)


class TestSeed:
    """Test the seeding."""

    def get_objective(
        self, name="test-objective", use_objective=True,
        use_dataset=True, use_solver=True
    ):
        seed_args = (
            f"{use_objective},{use_dataset},{use_solver},use_repetition=True"
        )
        return (
            f"""from benchopt.utils.temp_benchmark import TempObjective

            class Objective(TempObjective):
                name = "{name}"

                def evaluate_result(self, beta):
                    print(
                        '#SEED-obj=',
                        self.get_seed({seed_args})
                    )
                    return dict(value=1)
            """
        )

    def get_dataset(
        self, name="test-dataset", use_objective=True,
        use_dataset=True, use_solver=True, use_repetition=True
    ):
        seed_args = (
            f"{use_objective},{use_dataset},{use_solver},{use_repetition}"
        )
        return (
            f"""from benchopt import BaseDataset

            class Dataset(BaseDataset):
                name = "{name}"
                def get_data(self):
                    print(
                        '#SEED-data=',
                        self.get_seed({seed_args})
                    )
                    return dict(X=0, y=1)
            """
        )

    def get_solver(
        self, name="test-solver", use_objective=True,
        use_dataset=True, use_solver=True
    ):
        seed_args = (
            f"{use_objective},{use_dataset},{use_solver},use_repetition=True"
        )
        return (
            f"""from benchopt.utils.temp_benchmark import TempSolver

            class Solver(TempSolver):
                name = "{name}"
                sampling_strategy = 'run_once'
                def run(self, _):
                    print('#SEED-sol=',
                        self.get_seed({seed_args})
                    )
                    return
            """
        )

    @pytest.mark.parametrize('use_objective', [True, False])
    @pytest.mark.parametrize('use_dataset', [True, False])
    @pytest.mark.parametrize('use_solver', [True, False])
    @pytest.mark.parametrize('objective_name', ["objective1", "objective2"])
    @pytest.mark.parametrize('dataset_name', ["dataset1", "dataset2"])
    @pytest.mark.parametrize('solver_name', ["solver1", "solver2"])
    def test_ignore(
        self, no_debug_log, use_objective, use_dataset, use_solver,
        objective_name, dataset_name, solver_name
    ):
        seeds = []

        for o_name, d_name, s_name in [
            ("objective1", "dataset1", "solver1"),
            (objective_name, dataset_name, solver_name)
        ]:
            # Only check for solver as all classes use the same mixin
            with temp_benchmark(
                objective=self.get_objective(
                    name=o_name,
                ),
                solvers=self.get_solver(
                    name=s_name,
                    use_objective=use_objective,
                    use_dataset=use_dataset,
                    use_solver=use_solver
                ),
                datasets=self.get_dataset(name=d_name)
            ) as bench:
                with CaptureCmdOutput() as out:
                    cmd_str = f"{bench.benchmark_dir} --no-cache "
                    cmd_str += "--no-plot"
                    run(cmd_str.split(), standalone_mode=False)

            parsed_output = out.output.split("\n")
            for s in parsed_output:
                if s.startswith("#SEED-sol="):
                    seeds.append(s)

        assert len(seeds) == 2

        if (
            (objective_name == "objective1" or not use_objective) and
            (dataset_name == "dataset1" or not use_dataset) and
            (solver_name == "solver1" or not use_solver)
        ):
            assert seeds[0] == seeds[1]
        else:
            assert seeds[0] != seeds[1]

    def test_objective_simple(self, no_debug_log):
        with temp_benchmark(
            objective=self.get_objective(),
            solvers=self.get_solver(),
            datasets=self.get_dataset()
        ) as bench:
            with CaptureCmdOutput() as out:
                cmd_str = f"{bench.benchmark_dir} --no-cache "
                cmd_str += "--no-plot"
                for it in range(2):
                    run(cmd_str.split(),
                        standalone_mode=False)

        parsed_output = out.output.split("\n")
        seeds = []
        for s in parsed_output:
            if s.startswith("#SEED-obj="):
                seeds.append(s)

        assert len(seeds) == 2, f"Found {len(seeds)} seeds instead of 2"
        assert seeds[0] == seeds[1], "Seeds should be equal"

    def test_dataset_simple(self, no_debug_log):
        with temp_benchmark(
            objective=self.get_objective(),
            solvers=self.get_solver(),
            datasets=self.get_dataset()
        ) as bench:
            with CaptureCmdOutput() as out:
                cmd_str = f"{bench.benchmark_dir} --no-cache "
                cmd_str += "--no-plot"
                for it in range(2):
                    run(cmd_str.split(),
                        standalone_mode=False)

        parsed_output = out.output.split("\n")
        seeds = []
        for s in parsed_output:
            if s.startswith("#SEED-data="):
                seeds.append(s)

        assert len(seeds) == 2, f"Found {len(seeds)} seeds instead of 2"
        assert seeds[0] == seeds[1], "Seeds are not equal"

    def test_seed_different(self, no_debug_log):
        with temp_benchmark(
            objective=self.get_objective(),
            solvers=self.get_solver(),
            datasets=self.get_dataset()
        ) as bench:
            with CaptureCmdOutput() as out:
                cmd_str = f"{bench.benchmark_dir} --no-cache --no-plot "
                for it in range(2):
                    run((cmd_str+f"--seed {it}").split(),
                        standalone_mode=False)

        parsed_output = out.output.split("\n")
        seeds = []
        for s in parsed_output:
            if s.startswith("#SEED-sol="):
                seeds.append(s)

        assert len(seeds) == 2, f"Found {len(seeds)} seeds instead of 2"
        assert seeds[0] != seeds[1]

    def test_seed_repetition(self, no_debug_log):
        with temp_benchmark(
            objective=self.get_objective(),
            solvers=self.get_solver(),
            datasets=self.get_dataset()
        ) as bench:
            with CaptureCmdOutput() as out:
                cmd_str = f"{bench.benchmark_dir} --no-cache "
                cmd_str += "--no-plot -r 2"
                for it in range(2):
                    run(cmd_str.split(),
                        standalone_mode=False)

        parsed_output = out.output.split("\n")
        seeds = []
        for s in parsed_output:
            if s.startswith("#SEED-sol="):
                seeds.append(s)

        assert len(seeds) == 4, f"Found {len(seeds)} seeds instead of 4"
        assert seeds[0] == seeds[2], "Seeds are not equal"
        assert seeds[1] == seeds[3], "Seeds are not equal"
        assert seeds[0] != seeds[1], (
            "Seeds for different repetitions should not be equal"
        )

    def test_cache(self, no_debug_log):
        with temp_benchmark(
            objective=self.get_objective(),
            solvers=self.get_solver(),
            datasets=self.get_dataset()
        ) as bench:
            with CaptureCmdOutput() as out:
                for _ in range(2):
                    cmd_str = f"{bench.benchmark_dir} --seed 0 --no-plot -r 3"
                    run(cmd_str.split(), standalone_mode=False)

        # Check that the runs are cached when seed is the same
        out.check_output("#SEED-sol=", repetition=3)

        with temp_benchmark(
            objective=self.get_objective(),
            solvers=self.get_solver(),
            datasets=self.get_dataset()
        ) as bench:
            with CaptureCmdOutput() as out:
                for seed in range(2):
                    cmd_str = (
                        f"{bench.benchmark_dir} --seed {seed} --no-plot -r 3"
                    )
                    run(cmd_str.split(), standalone_mode=False)

        # Runs should not be cached when seed is different
        out.check_output("#SEED-sol=", repetition=6)

    def test_cache_dataset(self, no_debug_log):
        with temp_benchmark(
            objective=self.get_objective(),
            solvers=self.get_solver(),
            datasets=self.get_dataset(use_repetition=False)
        ) as bench:
            with CaptureCmdOutput() as out:
                cmd_str = f"{bench.benchmark_dir} --no-plot -r 3"
                run(cmd_str.split(), standalone_mode=False)

        # Dataset should be loaded only once when seed is independant of rep
        out.check_output("#SEED-data=", repetition=1)

        with temp_benchmark(
            objective=self.get_objective(),
            solvers=self.get_solver(),
            datasets=self.get_dataset(use_repetition=True)
        ) as bench:
            with CaptureCmdOutput() as out:
                cmd_str = f"{bench.benchmark_dir} --no-plot -r 3"
                run(cmd_str.split(), standalone_mode=False)

        # Dataset should be computed for each repetition when seed
        # is different for each repetition
        out.check_output("#SEED-data=", repetition=3)
