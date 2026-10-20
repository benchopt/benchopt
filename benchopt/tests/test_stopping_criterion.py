import pytest
import numpy as np

from benchopt.cli.main import run
from benchopt._generate_runs import get_solver_kwargs
from benchopt.tests.utils import CaptureCmdOutput
from benchopt.utils.temp_benchmark import temp_benchmark
from benchopt.utils.terminal_output import TerminalOutput

from benchopt.stopping_criterion import SAMPLING_STRATEGIES
from benchopt.stopping_criterion import SingleRunCriterion
from benchopt.stopping_criterion import SufficientDescentCriterion
from benchopt.stopping_criterion import SufficientProgressCriterion


@pytest.mark.parametrize('strategy', SAMPLING_STRATEGIES)
@pytest.mark.parametrize('criterion_class', [
    SufficientDescentCriterion, SufficientProgressCriterion
])
def test_max_iter(criterion_class, strategy):
    "Check that max_runs stop correctly."
    criterion = criterion_class(strategy=strategy)
    criterion = criterion.get_runner_instance(max_runs=1)

    stop_val = criterion.init_stop_val()
    objective_list = [{'objective_value': 1}]
    stop, status, stop_val = criterion.should_stop(stop_val, objective_list)
    assert not stop, "Should not have stopped"
    assert status == 'running', "Should  be running"

    objective_list.append({'objective_value': .5})
    stop, status, stop_val = criterion.should_stop(stop_val, objective_list)
    assert stop, "Should have stopped"
    assert status == 'max_runs', "Should stop on max_runs"


@pytest.mark.parametrize('strategy', SAMPLING_STRATEGIES)
@pytest.mark.parametrize('criterion_class', [
    SufficientDescentCriterion, SufficientProgressCriterion
])
def test_timeout(criterion_class, strategy):
    "Check that timeout=0 stopsimmediatly."
    criterion = criterion_class(strategy=strategy)
    criterion = criterion.get_runner_instance(timeout=0)

    stop_val = criterion.init_stop_val()
    objective_list = [{'objective_value': 1}]
    stop, status, stop_val = criterion.should_stop(stop_val, objective_list)
    assert stop, "Should have stopped"
    assert status == 'timeout', "Should stop on timeout"


@pytest.mark.parametrize('strategy', SAMPLING_STRATEGIES)
@pytest.mark.parametrize('criterion_class', [
    SufficientDescentCriterion, SufficientProgressCriterion
])
@pytest.mark.parametrize('minimize', [True, False])
def test_diverged(criterion_class, strategy, minimize):
    "Check that the benchmark stops when diverging."
    criterion = criterion_class(strategy=strategy, minimize=minimize)

    criterion = criterion.get_runner_instance(max_runs=100)
    stop_val = criterion.init_stop_val()
    objective_list = [{'objective_value': 1}]
    stop, status, stop_val = criterion.should_stop(stop_val, objective_list)
    assert not stop, "Should not have stopped"
    assert status == 'running', "Should  be running"

    val = 1e5+2 if minimize else -1e5-2
    objective_list.append({'objective_value': val})
    stop, status, stop_val = criterion.should_stop(stop_val, objective_list)
    assert stop, "Should have stopped"
    assert status == 'diverged', "Should stop on diverged"

    criterion = criterion.get_runner_instance(max_runs=10)
    stop_val = criterion.init_stop_val()
    objective_list = [{'objective_value': np.nan}]
    stop, status, stop_val = criterion.should_stop(stop_val, objective_list)
    assert stop, "Should have stopped"
    assert status == 'diverged', "Should stop on diverged"


@pytest.mark.parametrize('strategy', SAMPLING_STRATEGIES)
@pytest.mark.parametrize('criterion_class', [
    SufficientDescentCriterion, SufficientProgressCriterion
])
def test_key_to_monitor(criterion_class, strategy):
    "Check that the criterion tracks the right objective key."
    key = 'test'
    criterion = criterion_class(strategy=strategy, key_to_monitor=key)

    criterion = criterion.get_runner_instance(max_runs=10)
    assert criterion.key_to_monitor == key
    assert criterion.key_to_monitor_ == f"objective_{key}"
    stop_val = criterion.init_stop_val()
    objective_list = [{'objective_value': np.nan, f"objective_{key}": 1}]
    stop, status, stop_val = criterion.should_stop(stop_val, objective_list)
    assert not stop, "Should not have stopped"
    assert status == 'running', "Should stop on diverged"

    objective_list.append({f"objective_{key}": 1e5+2})
    stop, status, stop_val = criterion.should_stop(stop_val, objective_list)
    assert stop, "Should have stopped"
    assert status == 'diverged', "Should stop on diverged"


@pytest.mark.parametrize('strategy', SAMPLING_STRATEGIES)
@pytest.mark.parametrize('criterion_class', [
    SufficientDescentCriterion, SufficientProgressCriterion
])
def test_key_to_monitor_objective(no_debug_log, criterion_class, strategy):
    "Check that the criterion tracks the right objective key."
    key = 'test_key'

    objective = f"""from benchopt.utils.temp_benchmark import TempObjective

        class Objective(TempObjective):
            def evaluate_result(self, beta): return dict({key}=1)
    """

    solver = f"""from benchopt.utils.temp_benchmark import TempSolver
    from benchopt.stopping_criterion import *

    class Solver(TempSolver):
        name = "test-solver"
        stopping_criterion = {criterion_class.__name__}(
            key_to_monitor='{key}'
        )
    """

    with temp_benchmark(objective=objective, solvers=[solver]) as benchmark:
        with CaptureCmdOutput() as out:
            run([str(benchmark.benchmark_dir),
                *'-s test-solver -d test-dataset -n 10 -r 1 --no-display'
                .split()], standalone_mode=False)

    out.check_output('test-solver', 5)
    out.check_output('test-solver: done', 1)


@pytest.mark.parametrize('strategy', SAMPLING_STRATEGIES)
def test_solver_strategy(no_debug_log, strategy):

    solver = f"""from benchopt.utils.temp_benchmark import TempSolver

    class Solver(TempSolver):
        name = "test-solver"
        sampling_strategy = "{strategy}"
        def run(self, n_iter):
            assert self._solver_strategy == "{strategy}", self._solver_strategy
            if self._solver_strategy in "iteration":
                assert n_iter == 0, n_iter
            elif self._solver_strategy in "tolerance":
                assert n_iter == 3e38, n_iter
            elif self._solver_strategy in "run_once":
                assert n_iter == 1, n_iter
            elif self._solver_strategy in "callback":
                assert callable(n_iter)
                while n_iter(): pass
    """

    with temp_benchmark(solvers=[solver]) as benchmark:
        with CaptureCmdOutput():
            run([str(benchmark.benchmark_dir),
                *('-s test-solver -d test-dataset --no-plot -n 0').split()],
                standalone_mode=False)


@pytest.mark.parametrize('strategy', SAMPLING_STRATEGIES)
@pytest.mark.parametrize('criterion_class', [
    SufficientDescentCriterion, SufficientProgressCriterion
])
def test_stopping_criterion_strategy(no_debug_log, criterion_class, strategy):

    if strategy == "run_once":
        criterion_class = SingleRunCriterion

    solver = f"""from benchopt.utils.temp_benchmark import TempSolver
    from benchopt.stopping_criterion import {criterion_class.__name__}

    class Solver(TempSolver):
        name = "test-solver"
        stopping_criterion = {criterion_class.__name__}(strategy="{strategy}")
        def run(self, n_iter):
            assert self._solver_strategy == "{strategy}", self._solver_strategy
            if self._solver_strategy in "iteration":
                assert n_iter == 0, n_iter
            elif self._solver_strategy in "tolerance":
                assert n_iter == 3e38, n_iter
            elif self._solver_strategy in "run_once":
                assert n_iter == 1, n_iter
            elif self._solver_strategy in "callback":
                assert callable(n_iter)
                while n_iter(): pass
    """

    with temp_benchmark(solvers=[solver]) as benchmark:
        with CaptureCmdOutput():
            run([str(benchmark.benchmark_dir),
                *('-s test-solver -d test-dataset --no-plot -n 0').split()],
                standalone_mode=False)


@pytest.mark.parametrize('strategy', SAMPLING_STRATEGIES)
@pytest.mark.parametrize('criterion_class', [
    SufficientDescentCriterion, SufficientProgressCriterion
])
def test_solver_override_strategy(no_debug_log, criterion_class, strategy):

    if strategy == "run_once":
        criterion_class = SingleRunCriterion

    solver = f"""from benchopt.utils.temp_benchmark import TempSolver
    from benchopt.stopping_criterion import {criterion_class.__name__}

    class Solver(TempSolver):
        name = "test-solver"
        sampling_strategy = "{strategy}"
        stopping_criterion = {criterion_class.__name__}()
        def run(self, n_iter):
            assert self._solver_strategy == "{strategy}", self._solver_strategy
            if self._solver_strategy in "iteration":
                assert n_iter == 0, n_iter
            elif self._solver_strategy in "tolerance":
                assert n_iter == 3e38, n_iter
            elif self._solver_strategy in "run_once":
                assert n_iter == 1, n_iter
            elif self._solver_strategy in "callback":
                assert callable(n_iter)
                while n_iter(): pass
    """

    with temp_benchmark(solvers=[solver]) as benchmark:
        with CaptureCmdOutput():
            run([str(benchmark.benchmark_dir),
                *('-s test-solver -d test-dataset --no-plot -n 0').split()],
                standalone_mode=False)


def test_dual_strategy(no_debug_log):

    solver = """from benchopt.utils.temp_benchmark import TempSolver
    from benchopt.stopping_criterion import SufficientDescentCriterion

    class Solver(TempSolver):
        name = "test-solver"
        sampling_strategy = "iteration"
        stopping_criterion = SufficientDescentCriterion(strategy='tolerance')
    """

    with temp_benchmark(solvers=[solver]) as benchmark:
        with CaptureCmdOutput(exit=1) as out:
            run([str(benchmark.benchmark_dir),
                *('-s test-solver -d test-dataset --no-plot').split()],
                standalone_mode=False)
        out.check_output("Only set it once.", repetition=1)


def test_objective_equals_zero(no_debug_log):

    objective = """from benchopt.utils.temp_benchmark import TempObjective

        class Objective(TempObjective):
            name = "test_obj"
            def evaluate_result(self, beta): return dict(value=0)
    """

    solver = """from benchopt.utils.temp_benchmark import TempSolver
    from benchopt.stopping_criterion import SufficientDescentCriterion

    class Solver(TempSolver):
        name = "test-solver"
        stopping_criterion = SufficientDescentCriterion()
    """

    with temp_benchmark(
            objective=objective, solvers=[solver]
    ) as benchmark:
        with CaptureCmdOutput() as out:
            run([str(benchmark.benchmark_dir),
                *('-s test-solver -d test-dataset --no-plot -n 0').split()],
                standalone_mode=False)

    out.check_output('test-solver: done', 1)


@pytest.mark.parametrize('strategy', SAMPLING_STRATEGIES)
def test_global_strategy_override(no_debug_log, strategy):

    objective = f"""from benchopt.utils.temp_benchmark import TempObjective

    class Objective(TempObjective):
        name = "test_obj"
        sampling_strategy = "{strategy}"
    """

    with temp_benchmark(objective=objective) as bench:
        objective = bench.get_benchmark_objective().get_instance()
        solver = bench.get_solvers()[0].get_instance()
        solver._set_objective(objective)

        assert objective.sampling_strategy == strategy
        assert solver._solver_strategy == strategy


@pytest.mark.parametrize('criterion_class', [
    SufficientDescentCriterion, SufficientProgressCriterion, SingleRunCriterion
])
def test_global_criterion_override(no_debug_log, criterion_class):

    objective = f"""from benchopt.utils.temp_benchmark import TempObjective
    from benchopt.stopping_criterion import {criterion_class.__name__}

    class Objective(TempObjective):
        name = "test_obj"
        stopping_criterion = {criterion_class.__name__}()
    """

    with temp_benchmark(objective=objective) as bench:
        objective = bench.get_benchmark_objective().get_instance()
        solver = bench.get_solvers()[0].get_instance()
        solver._set_objective(objective)

        assert isinstance(objective.stopping_criterion, criterion_class)
        assert isinstance(solver._stopping_criterion, criterion_class)


def test_global_sampling_strategy(no_debug_log):
    # non-regression test that soler inherits the sampling strategy from
    # the objective. If not, this will fail as it will exptect a 'value' key

    objective = """from benchopt.utils.temp_benchmark import TempObjective

    class Objective(TempObjective):
        name = "test_obj"
        sampling_strategy = "run_once"
        def evaluate_result(self, **kwargs): return dict(test=1)
    """

    with temp_benchmark(objective=objective) as bench:
        run(f'{bench.benchmark_dir} -s test-solver -d test-dataset -n 1 '
            "--no-plot".split(), standalone_mode=False)


def test_sampling_strategy_meta_independent_of_execution_order(no_debug_log):
    # Non-regression test: `Solver.sampling_strategy` is a *class* attribute
    # that `_inherit_stopping_criterion` only resolves from `None` to the
    # objective's value as a side effect of actually running `_set_objective`.
    # `meta['sampling_strategy']`, part of the joblib cache key, must not
    # depend on whether some *other* (solver, dataset) pair already ran in
    # this process -- otherwise a second process (e.g. `--collect`) computes
    # a different cache key and reports valid cache entries as missing.
    objective = """from benchopt.utils.temp_benchmark import TempObjective

    class Objective(TempObjective):
        name = "test_obj"
        sampling_strategy = "run_once"
    """

    solver = """from benchopt.utils.temp_benchmark import TempSolver

    class Solver(TempSolver):
        name = "test-solver"
    """

    dataset1 = """from benchopt.utils.temp_benchmark import TempDataset

    class Dataset(TempDataset):
        name = "dataset1"
    """

    dataset2 = """from benchopt.utils.temp_benchmark import TempDataset

    class Dataset(TempDataset):
        name = "dataset2"
    """

    with temp_benchmark(
        objective=objective, solvers=[solver],
        datasets=[dataset1, dataset2], no_default=True,
    ) as bench:
        solver_class = bench.get_solvers()[0]
        objective_instance = bench.get_benchmark_objective().get_instance()
        datasets = {d.name: d for d in bench.get_datasets()}

        def sampling_strategy_for(dataset_name):
            dataset = datasets[dataset_name].get_instance()
            terminal = TerminalOutput(1, False)
            terminal.set(
                solver=solver_class, dataset=dataset,
                objective=objective_instance, i_solver=0
            )
            kwargs = next(get_solver_kwargs(
                benchmark=bench, dataset=dataset, objective=objective_instance,
                solver=solver_class.get_instance(), n_repetitions=1,
                max_runs=1, terminal=terminal,
            ))
            return kwargs['meta']['sampling_strategy']

        # Computed while `Solver.sampling_strategy` is still pristine (`None`)
        # -- mirrors what a fresh process (e.g. `benchopt run --collect`)
        # would see.
        strategy_pristine = sampling_strategy_for("dataset2")

        # Actually run the solver against `dataset1`. This mutates the
        # *class* attribute `Solver.sampling_strategy` as a side effect.
        solver_instance = solver_class.get_instance()
        dataset1_instance = datasets["dataset1"].get_instance()
        objective_instance._set_dataset(dataset1_instance)
        solver_instance._set_objective(objective_instance)

        # Recomputing for `dataset2` must give the same, correct value --
        # unaffected by the unrelated `dataset1` run that happened in between.
        strategy_after_other_run = sampling_strategy_for("dataset2")

        assert strategy_pristine == "Run_once"
        assert strategy_after_other_run == "Run_once"


@pytest.mark.parametrize('strategy', SAMPLING_STRATEGIES)
@pytest.mark.parametrize('criterion_class', [
    SufficientDescentCriterion, SufficientProgressCriterion
])
@pytest.mark.parametrize('minimize', [True, False])
@pytest.mark.parametrize('negative', [True, False])
def test_minimize_flag(criterion_class, strategy, minimize, negative):
    """Check that minimize parameter correctly handles maximization."""
    # Test with minimize=False (Maximize)
    criterion = criterion_class(
        strategy=strategy, patience=2, minimize=minimize
    )
    criterion = criterion.get_runner_instance(max_runs=20)
    stop_val = criterion.init_stop_val()

    objectives = [1.0, 1.1, 1.2]
    if negative:
        objectives = [-val for val in objectives]

    stop = False
    objective_list = []
    for val in objectives:
        assert not stop, "Should not have stopped yet"
        objective_list.append({'objective_value': val})
        stop, status, stop_val = criterion.should_stop(
            stop_val, objective_list
        )

    if minimize:
        assert stop == (not negative), "Minimization stopping failed"
    else:
        assert stop == negative, "Maximization stopping failed"


@pytest.mark.parametrize('strategy', SAMPLING_STRATEGIES)
@pytest.mark.parametrize('criterion_class', [
    SufficientDescentCriterion, SufficientProgressCriterion
])
@pytest.mark.parametrize('minimize', [True, False])
def test_minimize_flag_plateau(criterion_class, strategy, minimize):
    criterion = criterion_class(
        strategy=strategy, patience=2, minimize=minimize
    )
    criterion = criterion.get_runner_instance(max_runs=20)
    stop_val = criterion.init_stop_val()

    objective_list = []
    for _ in range(criterion.patience + 2):
        objective_list.append({'objective_value': 0.8})
        stop, status, stop_val = criterion.should_stop(
            stop_val, objective_list
        )

    assert stop, "Did not stop on plateau"
