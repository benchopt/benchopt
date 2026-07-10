import pytest

from click.shell_completion import ShellComplete

from benchopt.utils.temp_benchmark import temp_benchmark
from benchopt.utils.dynamic_modules import _unskip_import


@pytest.fixture(scope='module', autouse=True)
def bench_completion_cases():
    with temp_benchmark() as bench:
        benchmark_dir = bench.benchmark_dir

        # Create a second benchmark for completion, and an empty one to test
        # that they are not listed.
        (benchmark_dir.parent / "empty").mkdir()
        (benchmark_dir.parent / "test_bench").mkdir()
        (benchmark_dir.parent / "test_bench" / "objective.py").touch()

        # define benchmark completion cases
        all_benchmarks = [
            str(benchmark_dir), str(benchmark_dir.parent / "test_bench")
        ]

        completion_cases = [
            (str(benchmark_dir.parent), all_benchmarks),
            (str(benchmark_dir.parent)[:-2], all_benchmarks),
            (str(benchmark_dir)[:-2], [str(benchmark_dir)]),
        ]

        yield completion_cases


@pytest.fixture()
def solver_completion_cases():

    solver_names = ['solver1', 'solver2', 's3']
    solver = """
    from benchopt import BaseSolver
    class Solver(BaseSolver):
        name = '{}'
    """
    solvers = [solver.format(name) for name in solver_names]
    with temp_benchmark(solvers=solvers) as bench:
        benchmark_dir = bench.benchmark_dir

        # define solver completion cases
        completion_cases = [
            ('', solver_names),
            ('s', solver_names),
            ('so', ['solver1', 'solver2']),
            ('solver1', ['solver1']),
            ('er1', ['solver1']),
            ('solverX', []),
        ]

        yield benchmark_dir, completion_cases


@pytest.fixture()
def dataset_completion_cases():

    dataset_names = ['dataset1', 'dataset2', 'd3']
    dataset = """
    from benchopt import BaseDataset
    class Dataset(BaseDataset):
        name = '{}'
    """
    datasets = [dataset.format(name) for name in dataset_names]
    with temp_benchmark(datasets=datasets) as bench:
        benchmark_dir = bench.benchmark_dir

        # define dataset completion cases
        completion_cases = [
            ('', dataset_names),
            ('d', dataset_names),
            ('da', ['dataset1', 'dataset2']),
            ('dataset1', ['dataset1']),
            ('set1', ['dataset1']),
            ('datasetX', []),
        ]

        yield benchmark_dir, completion_cases


def _get_completion(cmd, args, incomplete):
    complete = ShellComplete(cmd, {}, '', '')
    proposals = complete.get_completions(args, incomplete)
    return [c.value for c in proposals]


def _test_shell_completion(cmd, args, test_cases):
    for incomplete, expected in test_cases:
        proposals = _get_completion(cmd, args, incomplete)
        n_res = len(expected)
        assert len(proposals) == n_res, (
            f"Expected {n_res} completion proposal, got '{proposals}'"
        )
        if n_res == 1:
            assert proposals[0] == expected[0], proposals
        elif expected is not None:
            assert set(proposals) == set(expected), proposals

    _unskip_import()
