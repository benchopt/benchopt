import numpy as np

import pytest

from benchopt.tests import TEST_SOLVER
from benchopt.tests import TEST_DATASET
from benchopt.tests import TEST_OBJECTIVE


def test_skip_api():

    dataset = TEST_DATASET.get_instance()
    objective = TEST_OBJECTIVE.get_instance(reg=0)
    objective.set_dataset(dataset)

    solver = TEST_SOLVER.get_instance()

    skip, reason = solver._set_objective(objective)
    assert skip
    assert reason == 'lmbd=0'

    objective = TEST_OBJECTIVE.get_instance(reg=1)
    objective.set_dataset(dataset)

    skip, reason = solver._set_objective(objective)
    assert not skip
    assert reason is None

    dataset = TEST_DATASET.get_instance(skip=True)
    objective = TEST_OBJECTIVE.get_instance()
    skip, reason = objective.set_dataset(dataset)
    assert skip
    assert reason == 'X is all zeros'


def test_get_one_solution():
    dataset = TEST_DATASET.get_instance()
    objective = TEST_OBJECTIVE.get_instance()
    objective.set_dataset(dataset)

    one_solution = objective.get_one_solution()
    expected = np.zeros(objective.X.shape[1])
    assert all(one_solution == expected)

    # XXX - Remove in version 1.3
    dataset = TEST_DATASET.get_instance(deprecated_return=True)
    objective = TEST_OBJECTIVE.get_instance(deprecated_dataset=True)

    with pytest.warns(FutureWarning, match="`get_data` should return a dict"):
        objective.set_dataset(dataset)

    with pytest.warns(FutureWarning, match="Objective should have a method"):
        one_solution = objective.get_one_solution()
    expected = np.zeros(objective.X.shape[1])
    assert all(one_solution == expected)
