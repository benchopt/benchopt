import time
from datetime import datetime

from .utils import product_param
from .benchmark import is_matched
from .benchmark import _check_name_lists
from .utils.sys_info import get_sys_info
from .utils.pdb_helpers import exception_handler

from .stopping_criterion import SufficientDescentCriterion

from .utils.colorify import colorify
from .utils.colorify import LINE_LENGTH, RED, GREEN, YELLOW


# Get config values
from .config import DEBUG
from .config import RAISE_INSTALL_ERROR


# Define some constants
# TODO: better parametrize this?
MAX_ITER = int(1e12)
MIN_TOL = 1e-15
INFINITY = 3e38  # see: np.finfo('float32').max
RHO = 1.5
RHO_INC = 1.2  # multiplicative update if rho is too small


def get_next(stop_val, rho=RHO, strategy="iteration"):
    if strategy == "iteration":
        return max(stop_val + 1, min(int(rho * stop_val), MAX_ITER))
    else:
        assert strategy == 'tolerance'
        return max(stop_val / rho, MIN_TOL)


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
    """
    # check if the module caught a failed import
    if not solver.is_installed():
        raise ImportError(
            f"Failure during import in {solver.__module__}."
        )

    if DEBUG:
        print(f"DEBUG - Calling solver {solver} with stop val: {stop_val}")

    t_start = time.perf_counter()
    solver.run(stop_val)
    delta_t = time.perf_counter() - t_start
    beta_hat_i = solver.get_result()
    objective_dict = objective(beta_hat_i)

    # Add system info in results
    info = get_sys_info()

    return dict(**meta, stop_val=stop_val, time=delta_t,
                **objective_dict, **info)


def run_one_to_cvg(benchmark, objective, solver, meta, stopping_criterion,
                   force=False):
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
    stopping_criterion : StoppingCriterion
        Object to check if we need to stop a solver.
    force : bool
        If force is set to True, ignore the cache and run the computations
        for the solver anyway. Else, use the cache if available.

    Returns
    -------
    curve : list of Cost
        The cost obtained for all repetitions.
    status : 'done' | 'diverged' | 'timeout' | 'max_runs'
        The status on which the solver was stopped.
    """

    # Create a Memory object to cache the computations in the benchmark folder
    # and handle cases where we force the run.
    run_one_resolution_cached = cache(run_one_resolution, benchmark, force)

    # compute initial value
    stopping_criterion.show_progress('initialization')
    init_stop_val = (0 if solver.stop_strategy == 'iteration' else INFINITY)
    call_args = dict(objective=objective, solver=solver, meta=meta)
    cost = run_one_resolution_cached(stop_val=init_stop_val, **call_args)
    curve = [cost]
    stop, status, is_flat = stopping_criterion.should_stop_solver(curve)

    stop_val = 1
    rho = RHO
    while not stop:

        cost = run_one_resolution_cached(
            stop_val=stop_val, **call_args
        )
        curve.append(cost)

        # Check the stopping criterion and update rho if necessary.
        stop, status, is_flat = stopping_criterion.should_stop_solver(curve)
        if is_flat:
            rho *= RHO_INC
            if DEBUG:
                print("DEBUG - curve is flat -> increasing rho:", rho)

        # compute next evaluation point
        stop_val = get_next(stop_val, rho=rho, strategy=solver.stop_strategy)

    return curve, status


class _Callback:
    """Callback class to monitor convergence.

    Parameters
    ----------
    objective : instance of BaseObjective
        The objective to minimize.
    meta : dict
        Metadata passed to store in Cost results.
        Contains objective and data names, problem dimension, etc.
    stopping_criterion : StoppingCriterion
        Object to check if we need to stop a solver.

    Attributes
    ----------
    objective : instance of BaseObjective
        The objective to minimize.
    stopping_criterion : StoppingCriterion
        Object to check if we need to stop a solver.
    meta : dict
        Metadata passed to store in Cost results.
        Contains objective and data names, problem dimension, etc.
    info : dict
        A dictionary with info from the current system.
    curve : list
        The convergence curve stored as a list of dict.
    status : 'running' | 'done' | 'diverged' | 'timeout' | 'max_runs'
        The status on which the solver is or was stopped.
    time_iter : float
        Computation time to reach the current iteration.
        Excluding the times to evaluate objective.
    it : int
        The number of times the callback has been called. It's
        initialized with 0.
    next_stopval : int
        The next iteration for which the curve should be
        updated.
    time_callback : float
        The time when exiting the callback call.
    """
    def __init__(self, objective, meta, stopping_criterion):
        self.objective = objective
        self.meta = meta
        self.stopping_criterion = stopping_criterion

        # Initialize local variables
        self.info = get_sys_info()
        self.curve = []
        self.status = 'running'
        self.it = 0
        self.rho = RHO
        self.time_iter = 0.
        self.next_stopval = 0
        self.time_callback = time.perf_counter()

    def __call__(self, x):
        # Stop time and update computation time since the begining
        t0 = time.perf_counter()
        self.time_iter += t0 - self.time_callback

        # Evaluate the iteration if necessary.
        if self.it == self.next_stopval:
            objective_dict = self.objective(x)
            self.curve.append(dict(
                **self.meta, stop_val=self.it,
                time=self.time_iter,
                **objective_dict, **self.info
            ))

            # Check the stopping criterion and update rho if necessary.
            stop, status, is_flat = self.stopping_criterion.should_stop_solver(
                self.curve
            )
            if stop:
                self.status = status
                return False

            if is_flat:
                self.rho *= RHO_INC

            # compute next evaluation point
            self.next_stopval = get_next(
                self.next_stopval, rho=self.rho, strategy="iteration"
            )

        # Update iteration number and restart time measurment.
        self.it += 1
        self.time_callback = time.perf_counter()
        return True

    def get_results(self):
        """Get the results stored by the callback

        Returns
        -------
        curve : list
            Details on the run and the objective value obtained.
        status : 'done' | 'diverged' | 'timeout' | 'max_runs'
            The status on which the solver was stopped.
        """
        return self.curve, self.status


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
                                  ignore=['force'])

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

            meta_rep = dict(**meta, idx_rep=rep, solver_name=str(solver))

            stopping_criterion = SufficientDescentCriterion._get_instance(
                max_runs=max_runs, timeout=timeout / n_repetitions,
                progress_str=progress_str
            )

            if solver.stop_strategy == "callback":
                callback = _Callback(
                    objective, meta_rep, stopping_criterion
                )
                solver.run(callback)
                curve_one_rep, status = callback.get_results()
            else:
                curve_one_rep, status = run_one_to_cvg_cached(
                    benchmark=benchmark, objective=objective, solver=solver,
                    meta=meta_rep, stopping_criterion=stopping_criterion,
                    force=force
                )

            curve.extend(curve_one_rep)
            states.append(status)

        if 'diverged' in states:
            final_status = colorify('diverged', RED)
        elif 'timeout' in states:
            final_status = colorify('done (timeout)', YELLOW)
        elif 'max_runs' in states:
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
    print("BenchOpt is running")

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
        raise SystemExit(1)

    # Save output in CSV file in the benchmark folder
    timestamp = datetime.now().strftime('%Y-%m-%d_%Hh%Mm%S')
    output_dir = benchmark.get_output_folder()
    save_file = output_dir / f'benchopt_run_{timestamp}.csv'
    df.to_csv(save_file)
    print(colorify(f'Saving result in: {save_file}', GREEN))

    if plot_result:
        from benchopt.plotting import plot_benchmark
        plot_benchmark(save_file, benchmark)
    return save_file
