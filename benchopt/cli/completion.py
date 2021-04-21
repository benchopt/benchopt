from pathlib import Path


from benchopt.benchmark import Benchmark
from benchopt.utils.misc import list_conda_envs
from benchopt.utils.safe_import import skip_import


def get_benchmark(ctx, args, incomplete):
    "Auto-completion for benchmarks."
    skip_import()

    # check the current incomplete path. If it does not exists, use its parent
    # as a starting point for lookup.
    incomplete_path = Path(incomplete)
    if not incomplete_path.exists():
        incomplete_path = incomplete_path.parent

    # List all sub directory
    all_dirs = [d for d in incomplete_path.glob('*') if d.is_dir()]

    # First try to list benchmarks that match the incomplete pattern.
    benchmarks = [
        b for b in all_dirs
        if (Path(b) / "objective.py").exists() and incomplete in str(b)
    ]
    if len(benchmarks) > 0:
        return benchmarks

    # Else do completion with sub-directories.
    matching_dirs = [
        b for b in all_dirs if incomplete in str(b)
    ]
    if len(matching_dirs) == 1:
        # If only one matches, complete the folder name and continue completion
        # from here.
        return get_benchmark(ctx, args, str(matching_dirs[0]))
    return matching_dirs


def find_benchmark_in_args(args):
    "Find the benchmark in preceeding args for benchmark dependent completion."
    for b in args:
        if (Path(b) / "objective.py").exists():
            return Benchmark(b)

    return None


def get_solvers(ctx, args, incomplete):
    "Auto-completion for solvers."
    skip_import()
    benchmark = find_benchmark_in_args(args)
    if benchmark is None:
        return [("", 'Benchmark has not been provided before')]
    solvers = benchmark.list_benchmark_solver_names()
    solvers = [s.lower() for s in solvers]
    return [s for s in solvers if incomplete.lower() in s]


def get_datasets(ctx, args, incomplete):
    "Auto-completion for datasets."
    skip_import()
    benchmark = find_benchmark_in_args(args)
    if benchmark is None:
        return [("", 'Benchmark has not been provided before')]
    datasets = benchmark.list_benchmark_dataset_names()
    datasets = [d.lower() for d in datasets]
    return [d for d in datasets if incomplete.lower() in d]


def get_output_files(ctx, args, incomplete):
    "Auto-completion for datasets."
    skip_import()
    benchmark = find_benchmark_in_args(args)
    if benchmark is None:
        return [("", 'Benchmark has not been provided before')]
    output_folder = benchmark.get_output_folder()
    return [
        f.name for f in output_folder.glob('*.csv') if incomplete in str(f)
    ]


def get_conda_envs(ctx, args, incomplete):
    "Auto-completion for env-names."
    _, all_envs = list_conda_envs()
    return [e for e in all_envs if incomplete in e]
