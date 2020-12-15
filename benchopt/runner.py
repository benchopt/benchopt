import time
import numpy as np
import pandas as pd
from joblib import Memory
from datetime import datetime

from .viz import plot_benchmark
from .utils import product_param
from .benchmark import is_matched
from .config import get_global_setting
from .benchmark import _check_name_lists
from .utils.files import _get_output_folder
from .utils.pdb_helpers import exception_handler

from .utils.colorify import colorify
from .utils.colorify import LINE_LENGTH, RED, GREEN, YELLOW


# Get config values
DEBUG = get_global_setting('debug')
CACHE_DIR = '__cache__'
RAISE_INSTALL_ERROR = get_global_setting('raise_install_error')


# Define some constants
# TODO: better parametrize this?
PATIENCE = 5
MAX_ITER = int(1e6)
MIN_TOL = 1e-15


##################################
# Time one run of a solver
##################################
def run_one_repetition(objective, solver, meta, stop_val):
    """Run one repetition of the solver.

    Parameters
    ----------
    objective : instance of BaseObjective
        The objective to minimize.
    solver : instance of BaseSolver
        The solver to use.
    meta : dict
        Metadata passed to store in Cost results.
        Contains objective, data, scale, id_rep.
    stop_val : int | float
        Corresponds to stopping criterion, such as
        tol or max_iter for the solver. It depends
        on the stop_strategy for the solver.

    Returns
    -------
    cost : dict
        Details on the run and the objective value obtained.
    objective_value : float
        Value of the objective function reached, used to detect convergence.
    """
    # check if the module caught a failed import
    if not solver.is_installed():
        raise ImportError(
            f"Failure during import in {solver.__module__}.")

    t_start = time.perf_counter()
    solver.run(stop_val)
    delta_t = time.perf_counter() - t_start
    beta_hat_i = solver.get_result()
    objective_dict = objective(beta_hat_i)

    return (dict(**meta, solver_name=str(solver), stop_val=stop_val,
                 time=delta_t, **objective_dict),
            objective_dict['objective_value'])


def run_one_stop_val(benchmark_dir, objective, solver, meta, stop_val,
                     n_repetitions, deadline=None, progress_str=None,
                     force=False):
    """Run all repetitions of the solver for a value of stopping criterion.

    Parameters
    ----------
    benchmark_dir : str
        The path to the benchmark files.
    objective : instance of BaseObjective
        The objective to minimize.
    solver : instance of BaseSolver
        The solver to use.
    meta : dict
        Metadata passed to store in Cost results.
        Contains objective, data, scale.
    stop_val : int | float
        Corresponds to stopping criterion, such as
        tol or max_iter for the solver. It depends
        on the stop_strategy for the solver.
    n_repetitions : int
        The number of repetitions to run.
    deadline : float
        The computer time solver cannot exceed to complete.
    progress_str : str
        The string to display in the progress bar.
    force : bool
        If force is set to True, ignore the cache and run the computations
        for the solver anyway. Else, use the cache if available.

    Returns
    -------
    curve : list of Cost
        The cost obtained for all repetitions.
    max_objective_value : float
        The maximum of the objective values obtained across the repetitions for
        the given stop_val. It is used to detect when to stop adding points to
        the curve.
    """

    # Create a Memory object to cache the computations in the benchmark folder
    mem = Memory(location=benchmark_dir / CACHE_DIR, verbose=0)
    run_one_repetition_cached = mem.cache(run_one_repetition)

    curve = []
    current_objective = []
    for rep in range(n_repetitions):
        if progress_str is not None:
            msg = f"{progress_str} ({rep} / {n_repetitions} repetitions)"
            print(f"{msg.ljust(60)}\r", end='', flush=True)

        meta_rep = dict(**meta, idx_rep=rep)

        # Force the run if needed
        args = (objective, solver, meta_rep, stop_val)
        if force:
            (cost, objective_value), _ = run_one_repetition_cached.call(*args)
        else:
            cost, objective_value = run_one_repetition_cached(*args)

        curve.append(cost)
        current_objective.append(objective_value)

        if deadline is not None and deadline < time.time():
            # Reached the timeout so stop the computation here
            break

    return curve, np.max(current_objective)


def run_one_solver(benchmark_dir, objective, solver, meta,
                   max_runs, n_repetitions, timeout,
                   force=False, show_progress=True, pdb=False):
    """Minimize objective function with onesolver for different accuracies.

    Parameters
    ----------
    benchmark_dir : str
        The path to the benchmark files.
    objective : instance of BaseObjective
        The objective to minimize.
    solver : instance of BaseSolver
        The solver to use.
    meta : dict
        Metadata passed to store in Cost results.
        Contains objective, data, scale.
    max_runs : int
        The maximum number of solver runs to perform to estimate
        the convergence curve.
    n_repetitions : int
        The number of repetitions to run. Defaults to 1.
    timeout : float
        The maximum duration in seconds of the solver run.
    force : bool
        If force is set to True, ignore the cache and run the computations
        for the solver anyway. Else, use the cache if available.
    show_progress : bool
        If show_progress is set to True, display the progress of the benchmark.
    pdb : bool
        It pdb is set to True, open a debugger on error.

    Returns
    -------
    curve : list of Cost
        The cost obtained for all repetitions and all stopping criteria.
    """

    # TODO: parametrize
    rho = 1.5
    eps = 1e-10

    # Create a Memory object to cache the computations in the benchmark folder
    mem = Memory(location=benchmark_dir / CACHE_DIR, verbose=0)
    run_one_stop_val_cached = mem.cache(
        run_one_stop_val,
        ignore=['deadline', 'benchmark_dir', 'force', 'progress_str']
    )

    # Get the solver's name
    tag = colorify(f"|----{solver}:")

    # Sample the performances for different accuracy, either by varying the
    # tolerance or the maximal number of iterations
    curve = []
    if solver.stop_strategy == 'iteration':
        def get_next(x): return max(x + 1, min(int(rho * x), MAX_ITER))

    elif solver.stop_strategy == 'tolerance':
        def get_next(x): return max(x / rho, MIN_TOL)

    def progress(id_stop_val, delta):
        return max(id_stop_val / max_runs,
                   np.log(max(delta, eps)) / np.log(eps))

    # check if the module caught a failed import
    if not solver.is_installed(raise_on_not_installed=RAISE_INSTALL_ERROR):
        status = colorify("failed import", RED)
        print(f"{tag} {status}".ljust(LINE_LENGTH))
        return curve

    id_stop_val = 0
    stop_val = 1
    delta_objectives = [1e15]
    prev_objective_value = np.inf

    deadline = time.time() + timeout

    with exception_handler(tag, pdb=pdb):
        for id_stop_val in range(max_runs):
            if (np.max(delta_objectives) < eps):
                # We are on a plateau and the objective is not improving
                # stop here for the stop_val
                status = colorify('done', GREEN)
                break

            p = progress(id_stop_val, np.max(delta_objectives))
            if show_progress:
                progress_str = f"{tag} {p:6.1%}"
            else:
                progress_str = None

            call_args = dict(
                benchmark_dir=benchmark_dir, objective=objective,
                solver=solver, meta=meta, stop_val=stop_val,
                n_repetitions=n_repetitions, deadline=deadline,
                progress_str=progress_str, force=force
            )
            if force:
                (stop_val_curve, objective_value), _ = \
                    run_one_stop_val_cached.call(**call_args)
            else:
                stop_val_curve, objective_value = run_one_stop_val_cached(
                    **call_args
                )
            curve.extend(stop_val_curve)

            if time.time() > deadline:
                # We reached the timeout so stop the computation here
                status = colorify('done (timeout)', YELLOW)
                break

            delta_objective = prev_objective_value - objective_value
            delta_objectives.append(delta_objective)
            if delta_objective == 0:
                rho *= 1.2
            if len(delta_objectives) > PATIENCE:
                delta_objectives.pop(0)
            prev_objective_value = objective_value
            stop_val = get_next(stop_val)
        else:
            status = colorify("done (did not converge)", YELLOW)
        if DEBUG:
            delta = np.max(delta_objectives)
            print(f"{tag} DEBUG - Exit with delta_objective = {delta:.2e} "
                  f"and stop_val={stop_val:.1e}.")
        else:
            print(f"{tag} {status}".ljust(LINE_LENGTH))

    return curve


def run_benchmark(benchmark, solver_names=None, forced_solvers=None,
                  dataset_names=None, objective_filters=None,
                  max_runs=10, n_repetitions=1, timeout=100,
                  plot_result=True, show_progress=True, pdb=False):
    """Run full benchmark.

    Parameters
    ----------
    benchmark : benchopt.Benchmark object
        Object to represent the benchmark.
    solver_names : list | None
        List of solvers to include in the benchmark. If None
        all solvers available are run.
    forced_solvers : list | None
        List of solvers to include in the benchmark and for
        which one forces recomputation.
    dataset_names : list | None
        List of datasets to include. If None all available
        datasets are used.
    objective_filters : list | None
        Filters to select specific objective parameters. If None,
        all objective parameters are tested
    max_runs : int
        The maximum number of solver runs to perform to estimate
        the convergence curve.
    n_repetitions : int
        The number of repetitions to run. Defaults to 1.
    timeout : float
        The maximum duration in seconds of the solver run.
    plot_result : bool
        If set to True (default), display the result plot and save them in
        the benchmark directory.
    show_progress : bool
        If show_progress is set to True, display the progress of the benchmark.
    pdb : bool
        It pdb is set to True, open a debugger on error.

    Returns
    -------
    df : instance of pandas.DataFrame
        The benchmark results. If multiple metrics were computed, each
        one is stored in a separate column. If the number of metrics computed
        by the objective is not the same for all parameters, the missing data
        is set to `NaN`.
    """
    # Load the objective class for this benchmark and the datasets
    objective_class = benchmark.get_benchmark_objective()
    datasets = benchmark.list_benchmark_datasets()

    # Load the solvers and filter them to get the one to run
    solver_classes = benchmark.list_benchmark_solvers()
    included_solvers = _check_name_lists(solver_names, forced_solvers)

    run_statistics = []
    for dataset_class in datasets:
        for dataset_parameters in product_param(dataset_class.parameters):
            dataset = dataset_class.get_instance(**dataset_parameters)
            if not is_matched(str(dataset), dataset_names):
                continue
            print(f"{dataset}")
            scale, data = dataset.get_data()
            for obj_parameters in product_param(objective_class.parameters):
                objective = objective_class.get_instance(**obj_parameters)
                if not is_matched(str(objective), objective_filters):
                    continue
                print(f"|--{objective}")
                objective.set_dataset(dataset)

                for solver_class in solver_classes:
                    if not solver_class.supports_dataset(dataset):
                        continue

                    for solver_parameters in product_param(
                            solver_class.parameters):

                        # Instantiate solver
                        solver = solver_class.get_instance(**solver_parameters)
                        if not is_matched(solver, included_solvers):
                            continue
                        solver._set_objective(objective)

                        # Get meta
                        meta = dict(
                            objective_name=str(objective),
                            data_name=str(dataset),
                            scale=scale
                        )

                        force = (forced_solvers is not None
                                 and len(forced_solvers) > 0
                                 and is_matched(str(solver), forced_solvers))
                        run_statistics.extend(run_one_solver(
                            benchmark_dir=benchmark.benchmark_dir,
                            objective=objective, solver=solver, meta=meta,
                            max_runs=max_runs, n_repetitions=n_repetitions,
                            timeout=timeout, show_progress=show_progress,
                            force=force, pdb=pdb
                        ))
    df = pd.DataFrame(run_statistics)
    if df.empty:
        print(colorify('No output produced.', RED))
        raise SystemExit(1)

    # Save output in CSV file in the benchmark folder
    timestamp = datetime.now().strftime('%Y-%m-%d_%Hh%Mm%S')
    output_dir = _get_output_folder(benchmark.benchmark_dir)
    save_file = output_dir / f'benchopt_run_{timestamp}.csv'
    df.to_csv(save_file)
    print(colorify(f'Saving result in: {save_file}', GREEN))

    if plot_result:
        plot_benchmark(df, benchmark)
    return df
