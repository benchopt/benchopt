from benchopt.runner import run_one_solver

from benchopt.tests import TEST_SOLVER
from benchopt.tests import TEST_DATASET
from benchopt.tests import TEST_OBJECTIVE
from benchopt.tests import DUMMY_BENCHMARK


def test_skip_api(capsys):

    benchmark = DUMMY_BENCHMARK
    dataset = TEST_DATASET.get_instance()
    objective = TEST_OBJECTIVE.get_instance(reg=0)
    objective.set_dataset(dataset)

    solver = TEST_SOLVER.get_instance()

    res = run_one_solver(
        benchmark_dir=benchmark.benchmark_dir,
        objective=objective, solver=solver, meta={},
        max_runs=1, n_repetitions=1,
        timeout=10000, show_progress=False,
        force=False, pdb=False
    )
    assert len(res) == 0
    out, err = capsys.readouterr()
    assert "skip" in out
    assert "Reason: lmbd=0" in out

    objective = TEST_OBJECTIVE.get_instance(reg=1)
    objective.set_dataset(dataset)
    res = run_one_solver(
        benchmark_dir=benchmark.benchmark_dir,
        objective=objective, solver=solver, meta={},
        max_runs=1, n_repetitions=1,
        timeout=10000, show_progress=False,
        force=False, pdb=False
    )
    assert len(res) == 1
    out, err = capsys.readouterr()
    assert "done (did not converge)" in out
