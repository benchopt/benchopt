from benchopt.utils.temp_benchmark import temp_benchmark


def test_dataset_name_default():
    # When test_dataset_name is None (the default), get_test_dataset_names
    # picks the sole dataset for single-dataset benchmarks, and falls back
    # to 'simulated' when multiple datasets are available.
    only_data = """from benchopt import BaseDataset
    class Dataset(BaseDataset):
        name = "only-data"
    """
    # For a benchmark with a single dataset, test_datset_name is this dataset
    with temp_benchmark(datasets=only_data) as bench:
        assert len(bench.get_dataset_names()) == 1
        assert bench.get_test_dataset_names() == ['only-data']

    # For a benchmark with multiple datasets, default is 'simulated'.
    # temp_benchmark add a simulated dataset by default when passed a dict.
    with temp_benchmark(datasets={'only-data': only_data}) as bench:
        assert len(bench.get_dataset_names()) > 1
        assert bench.get_test_dataset_names() == ['simulated']


def test_get_n_configs():
    # get_n_configs counts the parametrized (dataset, objective, solver)
    # combinations that `_get_all_runs` yields.
    from benchopt._generate_runs import _get_all_runs
    from benchopt.utils.terminal_output import TerminalOutput

    solver = """from benchopt import BaseSolver
    class Solver(BaseSolver):
        name = "solver"
        parameters = {'p': [1, 2, 3]}
        sampling_strategy = 'run_once'
        def set_objective(self, X, y): pass
        def run(self, n_iter): pass
        def get_result(self): return dict(beta=1)
    """
    dataset = """from benchopt import BaseDataset
    class Dataset(BaseDataset):
        name = "data"
        parameters = {'n': [10, 20]}
        def get_data(self): return dict(X=0, y=0)
    """
    with temp_benchmark(solvers=solver, datasets=dataset) as bench:
        solvers = bench.check_solver_patterns(None)
        datasets = bench.check_dataset_patterns(None)
        objectives = bench.check_objective_filters(None)
        n_runs = len(list(_get_all_runs(
            bench, solvers, None, datasets, objectives,
            terminal=TerminalOutput(1, False)
        )))
        assert bench.get_n_configs(solvers, datasets, objectives) == n_runs
        assert n_runs == 6
