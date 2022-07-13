from pathlib import Path


from benchopt.benchmark import Benchmark
from benchopt.utils.safe_import import skip_import
from benchopt.utils.conda_env_cmd import list_conda_envs


def propose_from_list(candidates, incomplete):
    candidates = [str(c) for c in candidates]
    proposals = [c for c in candidates if c.startswith(incomplete)]
    if len(proposals) > 0:
        return proposals
    return [c for c in candidates if incomplete in c]


def complete_benchmarks(ctx, param, incomplete):
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
        return complete_benchmarks(ctx, param, matching_dirs[0])
    return matching_dirs


def find_benchmark_in_args(args):
    "Find the benchmark in preceeding args for benchmark dependent completion."
    args.extend([Path.cwd()])  # default path is current working directory
    for b in args:
        if (Path(b) / "objective.py").exists():
            return Benchmark(b)

    return None


def complete_solvers(ctx, param, incomplete):
    "Auto-completion for solvers."
    skip_import()
    benchmark = find_benchmark_in_args(ctx.args)
    if benchmark is None:
        return []
    solvers = [s.lower() for s in benchmark.get_solver_names()]
    return propose_from_list(solvers, incomplete.lower())


def complete_datasets(ctx, param, incomplete):
    "Auto-completion for datasets."
    skip_import()
    benchmark = find_benchmark_in_args(ctx.args)
    if benchmark is None:
        return []
    datasets = [d.lower() for d in benchmark.get_dataset_names()]
    return propose_from_list(datasets, incomplete.lower())


def complete_output_files(ctx, param, incomplete):
    "Auto-completion for output files."
    skip_import()
    benchmark = find_benchmark_in_args(ctx.args)
    if benchmark is None:
        return []
    output_folder = benchmark.get_output_folder()

    # Only use absolute path to make sure we can use relative_to to
    # autocompletion with relative paths
    cwd = Path().resolve()
    candidates = [
        p.resolve().relative_to(cwd) for ext in ['csv', 'parquet']
        for p in output_folder.glob(f"*.{ext}")
    ]
    return propose_from_list(candidates, incomplete)


def complete_config_files(ctx, param, incomplete):
    "Auto-completion for configuration files."
    skip_import()
    benchmark = find_benchmark_in_args(ctx.args)
    if benchmark is None:
        return []
    benchmark_folder = benchmark.benchmark_dir

    # Only use absolute path to make sure we can use relative_to to
    # autocompletion with relative paths
    cwd = Path().resolve()
    candidates = [
        p.resolve().relative_to(cwd) for p in benchmark_folder.glob('*.yml')
    ]
    return propose_from_list(candidates, incomplete)


def complete_conda_envs(ctx, param, incomplete):
    "Auto-completion for env-names."
    _, all_envs = list_conda_envs()
    return propose_from_list(all_envs, incomplete)
