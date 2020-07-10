import click

from benchopt.util import is_matched
from benchopt.util import product_param
from benchopt.util import get_all_benchmarks
from benchopt.util import list_benchmark_solvers
from benchopt.util import list_benchmark_datasets


def validate_benchmark(ctx, param, value):
    all_benchmarks = get_all_benchmarks()
    if not all_benchmarks:
        raise click.BadArgumentUsage(
            "benchopt should be run in a folder where there is benchmarks "
            "directory with at least one benchmark."
        )
    if value not in all_benchmarks:
        all_benchmarks = '- ' + '\n- '.join(all_benchmarks)
        raise click.BadParameter(
            f"{value} is not a valid benchmark.\n"
            f"Should be one of:\n{all_benchmarks}"
        )
    return value


def _validate_patterns(all_names, patterns, name_type='dataset'):
    """Check that all provided patterns match at least one name.
    """
    if patterns is None:
        return

    # Check that the provided patterns match at least one dataset.
    invalid_patterns = []
    for p in patterns:
        matched = any([is_matched(name, [p]) for name in all_names])
        if not matched:
            invalid_patterns.append(p)

    # If some patterns did not matched any dataset, raise an error
    if len(invalid_patterns) > 0:
        all_names = '- ' + '\n- '.join(all_names)
        raise click.BadParameter(
            f"Patterns {invalid_patterns} did not matched any {name_type}.\n"
            f"Available {name_type}s are:\n{all_names}"
        )


def validate_dataset_patterns(benchmark, dataset_patterns):
    """Check that all provided patterns match at least one dataset"""

    # List all dataset strings.
    datasets = list_benchmark_datasets(benchmark)
    all_datasets = []
    for dataset_class in datasets:
        for dataset_parameters in product_param(dataset_class.parameters):
            all_datasets.append(str(dataset_class(**dataset_parameters)))

    _validate_patterns(all_datasets, dataset_patterns, name_type='dataset')


def validate_solver_patterns(benchmark, solver_patterns):
    """Check that all provided patterns match at least one solver"""

    # List all dataset strings.
    solver = list_benchmark_solvers(benchmark)
    all_solvers = []
    for solver_class in solver:
        for solver_parameters in product_param(solver_class.parameters):
            all_solvers.append(str(solver_class(**solver_parameters)))

    _validate_patterns(all_solvers, solver_patterns, name_type='solver')
