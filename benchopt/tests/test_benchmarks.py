import pytest
import numpy as np

from benchopt.base import SAMPLING_STRATEGIES

from benchopt.util import get_all_solvers
from benchopt.util import get_all_benchmarks
from benchopt.util import load_benchmark_losses


BENCHMARKS = get_all_benchmarks()
SOLVERS = [(benchmark, solver) for benchmark in BENCHMARKS
           for solver in get_all_solvers(benchmark)]


@pytest.mark.parametrize('benchmark_name', BENCHMARKS)
def test_benchmark_loss(benchmark_name):
    """Check that the loss function and the datasets are well defined."""
    loss_function, datasets = load_benchmark_losses(benchmark_name)

    for dataset_name, (get_data, parameters) in datasets.items():
        scale, *loss_parameters = get_data(**parameters)

        # check that the reported scale si correct and that the result of
        # the loss function is a scalar
        beta_hat = np.zeros(scale)
        assert np.isscalar(loss_function(*loss_parameters, beta_hat)), (
            "The output of the loss function should be a scalar."
        )


@pytest.mark.parametrize('benchmark_name, solver', SOLVERS)
def test_solvers(benchmark_name, solver):
    """Check that all installed solvers respects the public API"""

    # Check that the solver exposes a name
    assert hasattr(solver, 'name'), "All solvers should expose a name"
    assert isinstance(solver.name, str), "The solver's name should be a string"

    # Check that the solver uses a valid sampling_strategy
    assert solver.sampling_strategy in SAMPLING_STRATEGIES

    # Check that the solver exposes a known install cmd
    assert solver.install_cmd in [None, 'pip', 'bash']

    # Check that the solver exposes a known install cmd
    if solver.install_cmd == 'pip':
        assert hasattr(solver, 'install_package')
        assert hasattr(solver, 'import_package')
    if solver.install_cmd == 'bash':
        assert hasattr(solver, 'install_script')
        assert hasattr(solver, 'solver_cmd')
