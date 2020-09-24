import time
import numpy as np
import pandas as pd
from joblib import Memory
from datetime import datetime


from .base import Cost
from .util import is_matched
from .viz import plot_benchmark
from .util import product_param
from .util import _check_name_lists
from .config import get_global_setting
from .util import list_benchmark_solvers
from .util import list_benchmark_datasets
from .util import get_benchmark_objective
from .utils.files import _get_output_folder
from .utils.checkers import solver_supports_dataset


# Get config values
DEBUG = get_global_setting('debug')
RAISE_INSTALL_ERROR = get_global_setting('raise_install_error')


# Define some constants
# TODO: better parametrize this?
PATIENCE = 5
MAX_ITER = int(1e6)
MIN_TOL = 1e-15


###################################
# Helper function for outputs
###################################
BLACK, RED, GREEN, YELLOW, BLUE, MAGENTA, CYAN, WHITE = range(30, 38)


def colorify(message, color=BLUE):
    """Change color of the standard output.

    Parameters
    ----------
    message : str
        The message to color.

    Returns
    -------
    color_message : str
        The colored message to be displayed in terminal.
    """
    return ("\033[1;%dm" % color) + message + "\033[0m"


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
    cost : instance of Cost
        Details on the cost function reached.
    objective_value : float
        The value of the objective function reached.
    """
    # check if the module caught a failed import
    if not solver.is_installed():
        raise ImportError(
            f"Failure during import in {solver.__module__}.")

    t_start = time.perf_counter()
    solver.run(stop_val)
    delta_t = time.perf_counter() - t_start
    beta_hat_i = solver.get_result()
    objective_value = objective(beta_hat_i)

    return (Cost(**meta, solver=str(solver), stop_val=stop_val, time=delta_t,
                 obj=objective_value), objective_value)


def run_one_stop_val(benchmark, objective, solver, meta, stop_val,
                     n_repetitions, deadline, progress_str=None, force=False):
    """Run all repetitions of the solver for a value of stopping criterion.

    Parameters
    ----------
    benchmark : str
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
    mem = Memory(location=benchmark, verbose=0)
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

        if deadline < time.time():
            # Reached the timeout so stop the computation here
            break

    return curve, np.max(current_objective)


def run_one_solver(benchmark, objective, solver, meta, max_runs, n_repetitions,
                   timeout, force=False, show_progress=True):
    """Minimize objective function with onesolver for different accuracies.

    Parameters
    ----------
    benchmark : str
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

    Returns
    -------
    curve : list of Cost
        The cost obtained for all repetitions and all stopping criteria.
    """

    # TODO: parametrize
    rho = 1.5
    eps = 1e-10

    # Create a Memory object to cache the computations in the benchmark folder
    mem = Memory(location=benchmark, verbose=0)
    run_one_stop_val_cached = mem.cache(
        run_one_stop_val, ignore=['deadline', 'benchmark']
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
        print(f"{tag} {status}".ljust(80))
        return curve

    id_stop_val = 0
    stop_val = 1
    delta_objectives = [1e15]
    prev_objective_value = np.inf

    deadline = time.time() + timeout

    try:
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
                benchmark=benchmark, objective=objective, solver=solver,
                meta=meta, stop_val=stop_val, n_repetitions=n_repetitions,
                deadline=deadline, progress_str=progress_str, force=force
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
            print(f"{tag} {status}".ljust(80))
    except Exception:
        status = colorify("failed", RED)
        print(f"{tag} {status}".ljust(80))

        if DEBUG:
            raise
        else:
            import traceback
            traceback.print_exc()

    return curve


def run_benchmark(benchmark, solver_names=None, forced_solvers=None,
                  dataset_names=None, objective_filters=None,
                  max_runs=10, n_repetitions=1, timeout=100,
                  plot_result=True, show_progress=True):
    """Run full benchmark.

    Parameters
    ----------
    benchmark : str
        The path to the benchmark files.
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

    Returns
    -------
    df : instance of pandas.DataFrame
        The benchmark results.
    """
    # Load the objective class for this benchmark and the datasets
    objective_class = get_benchmark_objective(benchmark)
    datasets = list_benchmark_datasets(benchmark)

    # Load the solvers and filter them to get the one to run
    solver_classes = list_benchmark_solvers(benchmark)
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
                    if not solver_supports_dataset(solver_class, dataset):
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
                            objective=str(objective), data=str(dataset),
                            scale=scale
                        )

                        force = is_matched(str(solver), forced_solvers)
                        run_statistics.extend(run_one_solver(
                            benchmark=benchmark, objective=objective,
                            solver=solver, meta=meta, max_runs=max_runs,
                            n_repetitions=n_repetitions, timeout=timeout,
                            force=force, show_progress=show_progress
                        ))
    df = pd.DataFrame(run_statistics)

    # Save output in CSV file in the benchmark folder
    timestamp = datetime.now().strftime('%Y-%m-%d_%Hh%M:%S')
    output_dir = _get_output_folder(benchmark)
    save_file = output_dir / f'benchopt_run_{timestamp}.csv'
    df.to_csv(save_file)
    print(colorify(f'Saving result in: {save_file}', GREEN))

    if plot_result:
        plot_benchmark(df, benchmark)
    return df
