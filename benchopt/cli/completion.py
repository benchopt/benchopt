from pathlib import Path


from benchopt.benchmark import Benchmark
from benchopt.utils.safe_import import skip_import
from benchopt.utils.conda_env_cmd import list_conda_envs


def propose_from_list(candidates, incomplete):
    proposals = [c for c in candidates if str(c).startswith(incomplete)]
    if len(proposals) > 0:
        return proposals
    return [c for c in candidates if incomplete in str(c)]


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
    all_benchmarks = [
        b for b in all_dirs if (Path(b) / "objective.py").exists()
    ]

    # First try to list benchmarks that match the incomplete pattern.
    proposed_benchmarks = propose_from_list(all_benchmarks, incomplete)
    if len(proposed_benchmarks) > 0:
        return proposed_benchmarks

    # Else do completion with sub-directories.
    matching_dirs = propose_from_list(all_dirs, incomplete)
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
    return propose_from_list(solvers, incomplete.lower())


def get_datasets(ctx, args, incomplete):
    "Auto-completion for datasets."
    skip_import()
    benchmark = find_benchmark_in_args(args)
    if benchmark is None:
        return [("", 'Benchmark has not been provided before')]
    datasets = benchmark.list_benchmark_dataset_names()
    datasets = [d.lower() for d in datasets]
    return propose_from_list(datasets, incomplete.lower())


def get_output_files(ctx, args, incomplete):
    "Auto-completion for datasets."
    skip_import()
    benchmark = find_benchmark_in_args(args)
    if benchmark is None:
        return [("", 'Benchmark has not been provided before')]
    output_folder = benchmark.get_output_folder()
    candidates = list(output_folder.glob('*.csv'))
    return propose_from_list(candidates, incomplete)


def get_conda_envs(ctx, args, incomplete):
    "Auto-completion for env-names."
    _, all_envs = list_conda_envs()
    return propose_from_list(all_envs, incomplete)
