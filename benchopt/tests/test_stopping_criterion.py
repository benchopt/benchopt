import pytest
import numpy as np

from benchopt.stopping_criterion import STOPPING_STRATEGIES
from benchopt.stopping_criterion import SufficientDescentCriterion
from benchopt.stopping_criterion import SufficientProgressCriterion


@pytest.mark.parametrize('strategy', STOPPING_STRATEGIES)
@pytest.mark.parametrize('criterion_class', [
    SufficientDescentCriterion, SufficientProgressCriterion
])
def test_max_iter(criterion_class, strategy):
    "Check that max_runs stop correctly."
    criterion = criterion_class(strategy=strategy)
    criterion = criterion.get_runner_instance(max_runs=1)

    stop_val = criterion.init_stop_val()
    cost_curve = [{'objective_value': 1}]
    stop, status, stop_val = criterion.should_stop(stop_val, cost_curve)
    assert not stop, "Should not have stopped"
    assert status == 'running', "Should  be running"

    cost_curve.append({'objective_value': .5})
    stop, status, stop_val = criterion.should_stop(stop_val, cost_curve)
    assert stop, "Should have stopped"
    assert status == 'max_runs', "Should stop on max_runs"


@pytest.mark.parametrize('strategy', STOPPING_STRATEGIES)
@pytest.mark.parametrize('criterion_class', [
    SufficientDescentCriterion, SufficientProgressCriterion
])
def test_timeout(criterion_class, strategy):
    "Check that timeout=0 stopsimmediatly."
    criterion = criterion_class(strategy=strategy)
    criterion = criterion.get_runner_instance(timeout=0)

    stop_val = criterion.init_stop_val()
    cost_curve = [{'objective_value': 1}]
    stop, status, stop_val = criterion.should_stop(stop_val, cost_curve)
    assert stop, "Should have stopped"
    assert status == 'timeout', "Should stop on timeout"


@pytest.mark.parametrize('strategy', STOPPING_STRATEGIES)
@pytest.mark.parametrize('criterion_class', [
    SufficientDescentCriterion, SufficientProgressCriterion
])
def test_diverged(criterion_class, strategy):
    "Check that the benchmark stops when diverging."
    criterion = criterion_class(strategy=strategy)

    criterion = criterion.get_runner_instance(max_runs=100)
    stop_val = criterion.init_stop_val()
    cost_curve = [{'objective_value': 1}]
    stop, status, stop_val = criterion.should_stop(stop_val, cost_curve)
    assert not stop, "Should not have stopped"
    assert status == 'running', "Should  be running"

    cost_curve.append({'objective_value': 1e5+2})
    stop, status, stop_val = criterion.should_stop(stop_val, cost_curve)
    assert stop, "Should have stopped"
    assert status == 'diverged', "Should stop on diverged"

    criterion = criterion.get_runner_instance(max_runs=10)
    stop_val = criterion.init_stop_val()
    cost_curve = [{'objective_value': np.nan}]
    stop, status, stop_val = criterion.should_stop(stop_val, cost_curve)
    assert stop, "Should have stopped"
    assert status == 'diverged', "Should stop on diverged"


@pytest.mark.parametrize('strategy', STOPPING_STRATEGIES)
@pytest.mark.parametrize('criterion_class', [
    SufficientDescentCriterion, SufficientProgressCriterion
])
def test_key_to_monitor(criterion_class, strategy):
    "Check that the criterion tracks the right objective key."
    key = 'test'
    criterion = criterion_class(strategy=strategy, key_to_monitor=key)

    criterion = criterion.get_runner_instance(max_runs=10)
    assert criterion.key_to_monitor == key
    stop_val = criterion.init_stop_val()
    cost_curve = [{'objective_value': np.nan, key: 1}]
    stop, status, stop_val = criterion.should_stop(stop_val, cost_curve)
    assert not stop, "Should not have stopped"
    assert status == 'running', "Should stop on diverged"

    cost_curve.append({key: 1e5+2})
    stop, status, stop_val = criterion.should_stop(stop_val, cost_curve)
    assert stop, "Should have stopped"
    assert status == 'diverged', "Should stop on diverged"
