from benchopt.tests import TEST_SOLVER
from benchopt.tests import TEST_DATASET
from benchopt.tests import TEST_OBJECTIVE


def test_skip_api(capsys):

    dataset = TEST_DATASET._get_instance()
    objective = TEST_OBJECTIVE._get_instance(reg=0)
    objective._set_dataset(dataset)

    solver = TEST_SOLVER._get_instance()

    skip, reason = solver._set_objective(objective)
    assert skip
    assert reason == 'lmbd=0'

    objective = TEST_OBJECTIVE._get_instance(reg=1)
    objective._set_dataset(dataset)

    skip, reason = solver._set_objective(objective)
    assert not skip
    assert reason is None

    dataset = TEST_DATASET._get_instance(skip=True)
    objective = TEST_OBJECTIVE._get_instance()
    skip, reason = objective._set_dataset(dataset)
    assert skip
    assert reason == 'X is all zeros'
