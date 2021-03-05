import math
import time
from datetime import datetime

from .utils import product_param
from .benchmark import is_matched
from .benchmark import _check_name_lists
from .utils.sys_info import get_sys_info
from .utils.pdb_helpers import exception_handler

from .utils.colorify import colorify
from .utils.colorify import LINE_LENGTH, RED, GREEN, YELLOW


# Get config values
from .config import DEBUG
from .config import RAISE_INSTALL_ERROR


# Define some constants
# TODO: better parametrize this?
PATIENCE = 5
MAX_ITER = int(1e6)
MIN_TOL = 1e-15
INFINITY = 3e38  # see: np.finfo('float32').max


def cache(func, benchmark, force=False, ignore=None):

    # Create a cached function the computations in the benchmark folder
    # and handle cases where we force the run.
    func_cached = benchmark.mem.cache(func, ignore=ignore)
    if force:
        def _func_cached(**kwargs):
            return func_cached.call(**kwargs)[0]

        return _func_cached
    return func_cached


##################################
# Time one run of a solver
##################################
def run_one_resolution(objective, solver, meta, stop_val):
    """Run one resolution of the solver.

    Parameters
    ----------
    objective : instance of BaseObjective
        The objective to minimize.
    solver : instance of BaseSolver
        The solver to use.
    meta : dict
        Metadata passed to store in Cost results.
        Contains objective, data, dimension, id_rep.
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
            f"Failure during import in {solver.__module__}."
        )

    t_start = time.perf_counter()
    solver.run(stop_val)
    delta_t = time.perf_counter() - t_start
    beta_hat_i = solver.get_result()
    objective_dict = objective(beta_hat_i)

    # Add system info in results
    info = get_sys_info()

    return (dict(**meta, solver_name=str(solver), stop_val=stop_val,
                 time=delta_t, **objective_dict, **info),
            objective_dict['objective_value'])


def run_one_to_cvg(benchmark, objective, solver, meta, max_runs, deadline=None,
                   progress_str=None, force=False):
    """Run all repetitions of the solver for a value of stopping criterion.

    Parameters
    ----------
    benchmark : benchopt.Benchmark object
        Object to represent the benchmark.
    objective : instance of BaseObjective
        The objective to minimize.
    solver : instance of BaseSolver
        The solver to use.
    meta : dict
        Metadata passed to store in Cost results.
        Contains objective, data, dimension.
    max_runs : int
        The maximum number of solver runs to perform to estimate
        the convergence curve.
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

    # TODO: parametrize
    rho = 1.5
    eps = 1e-10

    def progress(id_stop_val, delta):
        return max(id_stop_val / max_runs,
                   math.log(max(delta, eps)) / math.log(eps))

    # Select strategy to compute next stop_val
    if solver.stop_strategy == 'iteration':
        def get_next(x): return max(x + 1, min(int(rho * x), MAX_ITER))

    elif solver.stop_strategy == 'tolerance':
        def get_next(x): return max(x / rho, MIN_TOL)

    # Create a Memory object to cache the computations in the benchmark folder
    # and handle cases where we force the run.
    run_one_resolution_cached = cache(run_one_resolution, benchmark, force)

    # compute initial value
    if progress_str is not None:
        print(progress_str.format(progress='initialization').ljust(LINE_LENGTH)
              + '\r', end='', flush=True)
    init_stop_val = (
        0 if solver.stop_strategy == 'iteration' else INFINITY
    )
    call_args = dict(
        objective=objective, solver=solver, meta=meta
    )
    cost, objective_value = run_one_resolution_cached(
        stop_val=init_stop_val, **call_args
    )

    curve = [cost]

    id_stop_val = 0
    stop_val = 1
    delta_objectives = [1e15]
    prev_objective_value = objective_value

    for id_stop_val in range(max_runs):
        if (-eps <= max(delta_objectives) < eps):
            # We are on a plateau and the objective is not improving
            # stop here for the stop_val
            status = 'done'
            break
        if max(delta_objectives) < -1e10:
            # The algorithm is diverging, stopping here
            status = 'diverged'
            break

        if time.time() > deadline:
            # We reached the timeout so stop the computation here
            status = 'timeout'
            break

        if progress_str is not None:
            p = progress(id_stop_val, max(delta_objectives))
            print(progress_str.format(progress=f'{p:6.1%}').ljust(LINE_LENGTH)
                  + '\r', end='', flush=True)
        cost, objective_value = run_one_resolution_cached(
            stop_val=stop_val, **call_args
        )
        curve.append(cost)

        delta_objective = prev_objective_value - objective_value
        delta_objectives.append(delta_objective)
        if delta_objective == 0:
            rho *= 1.2
        if len(delta_objectives) > PATIENCE:
            delta_objectives.pop(0)
        prev_objective_value = objective_value
        stop_val = get_next(stop_val)
    else:
        status = 'unfinished'

    if DEBUG:
        delta = max(*delta_objectives)
        print(f"DEBUG - Exit with delta_objective = {delta:.2e} "
              f"and stop_val={stop_val:.1e}.")

    return curve, status


def run_one_solver(benchmark, objective, solver, meta, max_runs, n_repetitions,
                   timeout=None, tag=None, show_progress=True, force=False,
                   pdb=False):
    """Run all repetitions of the solver for a value of stopping criterion.

    Parameters
    ----------
    benchmark : benchopt.Benchmark object
        Object to represent the benchmark.
    objective : instance of BaseObjective
        The objective to minimize.
    solver : instance of BaseSolver
        The solver to use.
    meta : dict
        Metadata passed to store in Cost results.
        Contains objective, data, dimension.
    max_runs : int
        The maximum number of solver runs to perform to estimate
        the convergence curve.
    n_repetitions : int
        The number of repetitions to run.
    timeout : float
        The maximum duration in seconds of the solver run.
    tag : str
        The solver name.
    show_progress : bool
        If set to True displays the current state of the repetitions.
    force : bool
        If force is set to True, ignore the cache and run the computations
        for the solver anyway. Else, use the cache if available.
    pdb : bool
        If pdb is set to True, open a debugger on error.

    Returns
    -------
    curve : list of Cost
        The cost obtained for all repetitions and all stop values.
    """

    # Create a Memory object to cache the computations in the benchmark folder
    run_one_to_cvg_cached = cache(run_one_to_cvg, benchmark, force,
                                  ignore=['deadline', 'force', 'progress_str'])

    curve = []
    states = []

    with exception_handler(tag, pdb=pdb):
        for rep in range(n_repetitions):
            if show_progress:
                progress_str = (
                    f"{tag} {{progress}} ({rep} / {n_repetitions} reps)"
                )
            else:
                progress_str = None

            meta_rep = dict(**meta, idx_rep=rep)

            # Force the run if needed
            deadline = time.time() + timeout / n_repetitions

            curve_one_rep, status = run_one_to_cvg_cached(
                benchmark=benchmark, objective=objective, solver=solver,
                meta=meta_rep, max_runs=max_runs, deadline=deadline,
                progress_str=progress_str, force=force
            )

            curve.extend(curve_one_rep)
            states.append(status)

            if deadline is not None and deadline < time.time():
                # Reached the timeout so stop the computation here
                break

        if 'diverged' in states:
            final_status = colorify('diverged', RED)
        elif 'timeout' in states:
            final_status = colorify('done (timeout)', YELLOW)
        elif 'unfinished' in states:
            final_status = colorify("done (not enough run)", YELLOW)
        else:
            final_status = colorify('done', GREEN)

        print(f"{tag} {final_status}".ljust(LINE_LENGTH))
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
            print(f"{dataset}".ljust(LINE_LENGTH))
            if not dataset.is_installed(
                    raise_on_not_installed=RAISE_INSTALL_ERROR):
                print(colorify(f"Dataset {dataset} is not installed.", RED)
                      .ljust(LINE_LENGTH))
                continue

            dimension, data = dataset._get_data()
            for obj_parameters in product_param(objective_class.parameters):
                objective = objective_class.get_instance(**obj_parameters)
                if not is_matched(str(objective), objective_filters):
                    continue
                print(f"|--{objective}".ljust(LINE_LENGTH))
                objective.set_dataset(dataset)

                for solver_class in solver_classes:

                    for solver_parameters in product_param(
                            solver_class.parameters
                    ):

                        # Instantiate solver
                        solver = solver_class.get_instance(**solver_parameters)
                        if not is_matched(solver, included_solvers):
                            continue

                        # Get the solver's name
                        tag = colorify(f"|----{solver}:")

                        # check if the module caught a failed import
                        if not solver.is_installed(
                                raise_on_not_installed=RAISE_INSTALL_ERROR
                        ):
                            status = colorify("not installed", RED)
                            print(f"{tag} {status}".ljust(LINE_LENGTH))
                            continue

                        # Set objective an skip if necessary.
                        skip, reason = solver._set_objective(objective)
                        if skip:
                            print(f"{tag} {colorify('skip', YELLOW)}"
                                  .ljust(LINE_LENGTH))
                            if reason is not None:
                                print(f'Reason: {reason}')
                            continue

                        # Get meta
                        meta = dict(
                            objective_name=str(objective),
                            data_name=str(dataset),
                            dimension=dimension
                        )

                        force = (forced_solvers is not None
                                 and len(forced_solvers) > 0
                                 and is_matched(str(solver), forced_solvers))

                        run_statistics.extend(run_one_solver(
                            benchmark=benchmark, objective=objective,
                            solver=solver, meta=meta, tag=tag,
                            max_runs=max_runs, n_repetitions=n_repetitions,
                            timeout=timeout, show_progress=show_progress,
                            force=force, pdb=pdb
                        ))

    import pandas as pd
    df = pd.DataFrame(run_statistics)
    if df.empty:
        print(colorify('No output produced.', RED).ljust(LINE_LENGTH))
        return
        # raise SystemExit(1)

    # Save output in CSV file in the benchmark folder
    timestamp = datetime.now().strftime('%Y-%m-%d_%Hh%Mm%S')
    output_dir = benchmark.get_output_folder()
    save_file = output_dir / f'benchopt_run_{timestamp}.csv'
    df.to_csv(save_file)
    print(colorify(f'Saving result in: {save_file}', GREEN))

    if plot_result:
        from benchopt.plotting import plot_benchmark
        plot_benchmark(df, benchmark)
    return df
