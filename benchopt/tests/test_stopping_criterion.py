import pytest
import numpy as np

from benchopt.cli.main import run
from benchopt.tests.utils import CaptureCmdOutput
from benchopt.utils.temp_benchmark import temp_benchmark

from benchopt.stopping_criterion import SAMPLING_STRATEGIES
from benchopt.stopping_criterion import SingleRunCriterion
from benchopt.stopping_criterion import SufficientDescentCriterion
from benchopt.stopping_criterion import SufficientProgressCriterion

MINIMAL_OBJECTIVE = """from benchopt import BaseObjective

    class Objective(BaseObjective):
        name = "stopping_criterion"
        min_benchopt_version = "0.0.0"

        def set_data(self, X, y): self.X, self.y = X, y
        def get_objective(self): return {}
        def get_one_result(self): return dict(beta=0)
        def evaluate_result(self, beta): return dict(value=1)
"""


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
def test_diverged(criterion_class, strategy):
    "Check that the benchmark stops when diverging."
    criterion = criterion_class(strategy=strategy)

    criterion = criterion.get_runner_instance(max_runs=100)
    stop_val = criterion.init_stop_val()
    objective_list = [{'objective_value': 1}]
    stop, status, stop_val = criterion.should_stop(stop_val, objective_list)
    assert not stop, "Should not have stopped"
    assert status == 'running', "Should  be running"

    objective_list.append({'objective_value': 1e5+2})
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

    objective = f"""from benchopt import BaseObjective

        class Objective(BaseObjective):
            name = "test_obj"
            min_benchopt_version = "0.0.0"

            def set_data(self, X, y): pass
            def get_one_result(self): pass
            def evaluate_result(self, beta): return dict({key}=1)
            def get_objective(self): return dict(X=0, y=0)
    """

    solver = f"""from benchopt import BaseSolver
    from benchopt.stopping_criterion import *

    class Solver(BaseSolver):
        name = "test-solver"
        stopping_criterion = {criterion_class.__name__}(
            key_to_monitor='{key}'
        )
        def set_objective(self, X, y): pass
        def run(self, n_iter): pass
        def get_result(self): return dict(beta=1)
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

    solver = f"""from benchopt import BaseSolver

    class Solver(BaseSolver):
        name = "test-solver"
        sampling_strategy = "{strategy}"
        def set_objective(self): pass
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

        def get_result(self): return dict(beta=1)
    """

    with temp_benchmark(
            objective=MINIMAL_OBJECTIVE,
            solvers=[solver]
    ) as benchmark:
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

    solver = f"""from benchopt import BaseSolver
    from benchopt.stopping_criterion import {criterion_class.__name__}

    class Solver(BaseSolver):
        name = "test-solver"
        stopping_criterion = {criterion_class.__name__}(strategy="{strategy}")
        def set_objective(self): pass
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

        def get_result(self): return dict(beta=1)
    """

    with temp_benchmark(
            objective=MINIMAL_OBJECTIVE,
            solvers=[solver]
    ) as benchmark:
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

    solver = f"""from benchopt import BaseSolver
    from benchopt.stopping_criterion import {criterion_class.__name__}

    class Solver(BaseSolver):
        name = "test-solver"
        sampling_strategy = "{strategy}"
        stopping_criterion = {criterion_class.__name__}()
        def set_objective(self): pass
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

        def get_result(self): return dict(beta=1)
    """

    with temp_benchmark(
            objective=MINIMAL_OBJECTIVE,
            solvers=[solver]
    ) as benchmark:
        with CaptureCmdOutput():
            run([str(benchmark.benchmark_dir),
                *('-s test-solver -d test-dataset --no-plot -n 0').split()],
                standalone_mode=False)


def test_dual_strategy(no_debug_log):

    solver = """from benchopt import BaseSolver
    from benchopt.stopping_criterion import SufficientDescentCriterion

    class Solver(BaseSolver):
        name = "test-solver"
        sampling_strategy = "iteration"
        stopping_criterion = SufficientDescentCriterion(strategy='tolerance')
        def set_objective(self): pass
        def run(self, n_iter): pass
        def get_result(self): return dict(beta=1)
    """

    with temp_benchmark(
            objective=MINIMAL_OBJECTIVE,
            solvers=[solver]
    ) as benchmark:
        with pytest.raises(AssertionError, match="Only set it once."):
            with CaptureCmdOutput():
                run([str(benchmark.benchmark_dir),
                    *('-s test-solver -d test-dataset --no-plot').split()],
                    standalone_mode=False)


def test_objective_equals_zero(no_debug_log):

    objective = """from benchopt import BaseObjective

        class Objective(BaseObjective):
            name = "test_obj"
            min_benchopt_version = "0.0.0"

            def set_data(self, X, y): pass
            def get_one_result(self): pass
            def evaluate_result(self, beta): return dict(value=0)
            def get_objective(self): return dict(X=0, y=0)
    """

    solver = """from benchopt import BaseSolver
    from benchopt.stopping_criterion import SufficientDescentCriterion

    class Solver(BaseSolver):
        name = "test-solver"
        stopping_criterion = SufficientDescentCriterion()
        def set_objective(self, X, y): pass
        def run(self, n_iter): pass
        def get_result(self): return dict(beta=1)
    """

    with temp_benchmark(
            objective=objective,
            solvers=[solver]
    ) as benchmark:
        with CaptureCmdOutput() as out:
            run([str(benchmark.benchmark_dir),
                *('-s test-solver -d test-dataset --no-plot -n 0').split()],
                standalone_mode=False)

    out.check_output('test-solver: done', 1)


@pytest.mark.parametrize('strategy', SAMPLING_STRATEGIES)
def test_global_strategy_override(no_debug_log, strategy):

    objective = MINIMAL_OBJECTIVE.replace(
        '"0.0.0"', f'"0.0.0"\n        sampling_strategy = "{strategy}"'
    )

    solver = """from benchopt import BaseSolver
    class Solver(BaseSolver):
        name = "test-solver"
        def set_objective(self): pass
        def run(self, n_iter): pass
        def get_result(self): return dict(beta=1)
    """

    with temp_benchmark(objective=objective, solvers=[solver]) as bench:
        objective = bench.get_benchmark_objective().get_instance()
        solver = bench.get_solvers()[0].get_instance()
        solver._set_objective(objective)

        assert objective.sampling_strategy == strategy
        assert solver._solver_strategy == strategy


@pytest.mark.parametrize('criterion_class', [
    SufficientDescentCriterion, SufficientProgressCriterion, SingleRunCriterion
])
def test_global_criterion_override(no_debug_log, criterion_class):

    objective = MINIMAL_OBJECTIVE.replace(
        '"0.0.0"',
        f'"0.0.0"\n        stopping_criterion = {criterion_class.__name__}()'
    ).replace(
        "import BaseObjective",
        "import BaseObjective\n    from benchopt.stopping_criterion import "
        f"{criterion_class.__name__}"
    )

    solver = """from benchopt import BaseSolver
    class Solver(BaseSolver):
        name = "test-solver"
        def set_objective(self): pass
        def run(self, n_iter): pass
        def get_result(self): return dict(beta=1)
    """

    with temp_benchmark(objective=objective, solvers=[solver]) as bench:
        objective = bench.get_benchmark_objective().get_instance()
        solver = bench.get_solvers()[0].get_instance()
        solver._set_objective(objective)

        assert isinstance(objective.stopping_criterion, criterion_class)
        assert isinstance(solver._stopping_criterion, criterion_class)
