import time
import inspect
import pickle

from datetime import datetime

from joblib import Parallel, delayed, hash

from .callback import _Callback
from .benchmark import Benchmark
from .utils.sys_info import get_sys_info
from .utils.files import uniquify_results
from .utils.pdb_helpers import exception_handler
from .utils.terminal_output import TerminalOutput


FAILURE_STATUS = ['diverged', 'error', 'interrupted']

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
        on the sampling_strategy for the solver.

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

    solver.pre_run_hook(stop_val)
    t_start = time.perf_counter()
    solver.run(stop_val)
    delta_t = time.perf_counter() - t_start
    result = solver.get_result()
    objective_dict = objective(result)

    # Add system info in results
    info = get_sys_info()

    return dict(**meta, stop_val=stop_val, time=delta_t,
                **objective_dict, **info)


def run_one_to_cvg(benchmark, objective, solver, meta, stopping_criterion,
                   force=False, output=None, pdb=False):
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
    pdb : bool
        It pdb is set to True, open a debugger on error.

    Returns
    -------
    curve : list of Cost
        The cost obtained for all repetitions.
    status : 'done' | 'diverged' | 'timeout' | 'max_runs'
        The status on which the solver was stopped.
    """

    # The warm-up step called for each repetition bit only run once.
    solver._warm_up()

    curve = []

    # Augment the metadata with final_results if necessary.
    base_method = getattr(
        super(type(objective), objective),
        'save_final_results', None
    )

    has_save_final_results = objective.save_final_results is not base_method
    if has_save_final_results:
        final_results = benchmark.get_output_folder() / 'final_results'
        final_results /= f"{hash(meta)}.pkl"
        final_results.parent.mkdir(exist_ok=True, parents=True)
        meta["final_results"] = str(final_results)

    with exception_handler(output, pdb=pdb) as ctx:

        if solver._solver_strategy == "callback":

            # If sampling_strategy is 'callback', only call once to get the
            # results up to convergence.
            callback = _Callback(
                objective, solver, meta, stopping_criterion
            )
            solver.pre_run_hook(callback)
            callback.start()
            solver.run(callback)
            curve, ctx.status = callback.get_results()
        else:

            # Create a Memory object to cache the computations in the benchmark
            # folder and handle cases where we force the run.
            run_one_resolution_cached = benchmark.cache(
                run_one_resolution, force
            )

            # compute initial value
            call_args = dict(objective=objective, solver=solver, meta=meta)

            stop = False
            stop_val = stopping_criterion.init_stop_val()
            while not stop:

                cost = run_one_resolution_cached(stop_val=stop_val,
                                                 **call_args)
                curve.append(cost)

                # Check the stopping criterion and update rho if necessary.
                stop, ctx.status, stop_val = stopping_criterion.should_stop(
                    stop_val, curve
                )
        # Only run if save_final_results is defined in the objective.
        if has_save_final_results and ctx.status not in FAILURE_STATUS:
            to_save = objective.save_final_results(**solver.get_result())
            if to_save is not None:
                with open(meta["final_results"], 'wb') as f:
                    pickle.dump(to_save, f)
    if ctx.status in FAILURE_STATUS:
        raise RuntimeError(ctx.status)
    return curve, ctx.status


def run_one_solver(benchmark, dataset, objective, solver, n_repetitions,
                   max_runs, timeout=None, force=False, collect=False,
                   output=None, pdb=False):
    """Run a benchmark for a given dataset, objective and solver.

    Parameters
    ----------
    benchmark : benchopt.Benchmark object
        Object to represent the benchmark.
    dataset : instance of BaseDataset
        The dataset used for this benchmark.
    objective : instance of BaseObjective
        The objective to minimize.
    solver : instance of BaseSolver
        The solver to use.
    n_repetitions : int
        The number of repetitions to run. Defaults to 1.
    max_runs : int
        The maximum number of solver runs to perform to estimate
        the convergence curve.
    timeout : float
        The maximum duration in seconds of the solver run.
    force : bool
        If force is set to True, ignore the cache and run the computations
        for the solver anyway. Else, use the cache if available.
    collect : bool
        If set to True, only collect the results that have been put in cache,
        and ignore the results that are not computed yet, default is False.
    output : TerminalOutput or None
        Object to format string to display the progress of the solver.
    pdb : bool
        It pdb is set to True, open a debugger on error.

    Returns
    -------
    run_statistics : list
        The benchmark results.
    """

    run_one_to_cvg_cached = benchmark.cache(
        run_one_to_cvg, ignore=['force', 'output', 'pdb'], collect=collect
    )
    if collect:
        _run_one_to_cvg_cached = run_one_to_cvg_cached

        def run_one_to_cvg_cached(**kwargs):
            res = _run_one_to_cvg_cached(**kwargs)
            return res if res is not None else ([], 'not run yet')

    # Set objective an skip if necessary.
    skip, reason = objective.set_dataset(dataset)
    if skip:
        output.skip(reason, objective=True)
        return []

    states = []
    run_statistics = []

    # get sampling strategy
    # for plotting purpose consider 'callback' as 'iteration'
    sampling_strategy = solver._solver_strategy
    if sampling_strategy == 'callback':
        sampling_strategy = 'iteration'

    # get objective description
    # use `obj_` instead of `objective_` to avoid conflicts with
    # the name of metrics in Objective.compute
    obj_description = objective.__doc__ or ""

    if n_repetitions is None:
        if hasattr(objective, "cv"):
            n_repetitions = objective.cv.get_n_splits(
                **getattr(objective, "cv_metadata", {})
            )
        else:
            # we set 1 by default so that the solver run at least once
            n_repetitions = 1

    for rep in range(n_repetitions):
        skip = solver._set_objective(objective, output=output)
        if skip:
            return []

        output.set(rep=rep)

        # Get meta
        meta = dict(
            objective_name=str(objective),
            solver_name=str(solver),
            data_name=str(dataset),
            idx_rep=rep,
            sampling_strategy=sampling_strategy.capitalize(),
            obj_description=obj_description,
            solver_description=inspect.cleandoc(solver.__doc__ or ""),
        )

        stopping_criterion = solver._stopping_criterion.get_runner_instance(
            solver=solver,
            max_runs=max_runs,
            timeout=timeout / n_repetitions if timeout is not None else None,
            output=output,
        )

        args_run_one_to_cvg = dict(
            benchmark=benchmark, objective=objective, solver=solver, meta=meta,
            stopping_criterion=stopping_criterion, force=force, output=output,
            pdb=pdb
        )
        try:
            curve, status = run_one_to_cvg_cached(
                **args_run_one_to_cvg
            )
        except RuntimeError as e:
            status = e.args[0]
        if status in ['diverged', 'error', 'interrupted', 'not run yet']:
            run_statistics = []
            break
        run_statistics.extend(curve)
        states.append(status)

    else:
        if 'max_runs' in states:
            status = 'max_runs'
        elif 'timeout' in states:
            status = 'timeout'
        else:
            status = 'done'

    output.show_status(status=status)
    # Make sure to flush so the parallel output is properly display
    print(end='', flush=True)

    # refresh the solver warm up flag so that warm-up is done again
    # when calling the solver with another problem/dataset pair.
    solver._warmup_done = False

    if status == 'interrupted':
        raise SystemExit(1)
    return run_statistics


def _run_benchmark(benchmark, solvers=None, forced_solvers=None,
                   datasets=None, objectives=None, max_runs=10,
                   n_repetitions=1, timeout=None, n_jobs=1, slurm=None,
                   plot_result=True, display=True, html=True,  collect=False,
                   show_progress=True, pdb=False, output_name="None"):
    """Run full benchmark.

    Parameters
    ----------
    benchmark : benchopt.Benchmark object
        Object to represent the benchmark.
    solvers : list | None
        List of solvers to include in the benchmark. If None
        all solvers available are run.
    forced_solvers : list | None
        List of solvers to include in the benchmark and for
        which one forces recomputation.
    datasets : list | None
        List of datasets to include. If None all available
        datasets are used.
    objectives : list | None
        Filters to select specific objective parameters. If None,
        all objective parameters are tested
    max_runs : int
        The maximum number of solver runs to perform to estimate
        the convergence curve.
    n_repetitions : int
        The number of repetitions to run. Defaults to 1.
    timeout : float
        The maximum duration in seconds of the solver run.
    n_jobs : int
        Maximal number of workers to use to run the benchmark in parallel.
    slurm : Path | None
        If not None, launch the job on a slurm cluster using the file to get
        the cluster config parameters.
    plot_result : bool
        If set to True (default), generate the result plot and save them in
        the benchmark directory.
    display : bool
        If set to True (default), open the result plots at the end of the run,
        otherwise, simply save them.
    html : bool
        If set to True (default), display the result plot in HTML, otherwise
        in matplotlib figures, default is True.
    collect : bool
        If set to True, only collect the results that have been put in cache,
        and ignore the results that are not computed yet, default is False.
    show_progress : bool
        If show_progress is set to True, display the progress of the benchmark.
    pdb : bool
        If pdb is set to True, open a debugger on error.
    output_name : str
        Filename for the parquet output. If given, the results will
        be stored at <BENCHMARK>/outputs/<filename>.parquet.

    Returns
    -------
    df : instance of pandas.DataFrame
        The benchmark results. If multiple metrics were computed, each
        one is stored in a separate column. If the number of metrics computed
        by the objective is not the same for all parameters, the missing data
        is set to `NaN`.
    """
    output = TerminalOutput(n_repetitions, show_progress)
    output.set(verbose=True)

    # List all datasets, objective and solvers to run based on the filters
    # provided. Merge the solver_names and forced to run all necessary solvers.
    all_runs = benchmark.get_all_runs(
        solvers, forced_solvers, datasets, objectives,
        output=output
    )
    common_kwargs = dict(
        benchmark=benchmark, n_repetitions=n_repetitions, max_runs=max_runs,
        timeout=timeout, pdb=pdb, collect=collect
    )

    if slurm is not None and not collect:
        from .utils.slurm_executor import run_on_slurm
        results = run_on_slurm(
            benchmark, slurm, run_one_solver, common_kwargs,
            all_runs
        )
    else:
        results = Parallel(n_jobs=n_jobs)(
            delayed(run_one_solver)(**common_kwargs, **kwargs)
            for kwargs in all_runs
        )

    run_statistics = []
    for curve in results:
        run_statistics.extend(curve)

    import pandas as pd
    df = pd.DataFrame(run_statistics)
    if df.empty:
        output.savefile_status()
        raise SystemExit(1)

    # Save output in parquet file in the benchmark folder
    timestamp = datetime.now().strftime('%Y-%m-%d_%Hh%Mm%S')
    output_dir = benchmark.get_output_folder()
    if output_name == "None":
        save_file = output_dir / f'benchopt_run_{timestamp}.parquet'
    else:
        save_file = output_dir / f"{output_name}.parquet"
        save_file = uniquify_results(save_file)
    try:
        df.to_parquet(save_file)
    except Exception:
        # Failed to save the results as a parquet file, falling back
        # to csv. This can be due to mixed types columns or missing
        # dependencies.
        save_file = save_file.with_suffix(".csv")
        df.to_csv(save_file)
    output.savefile_status(save_file=save_file)

    if plot_result:
        from benchopt.plotting import plot_benchmark
        plot_benchmark(save_file, benchmark, html=html, display=display)
    return save_file


def run_benchmark(benchmark_path, solver_names=None, forced_solvers=(),
                  dataset_names=None, objective_filters=None, max_runs=10,
                  n_repetitions=1, timeout=None, n_jobs=1, slurm=None,
                  plot_result=True, display=True, html=True,  collect=False,
                  show_progress=True, pdb=False, output_name="None"):
    """Run full benchmark.

    Parameters
    ----------
    benchmark : benchopt.Benchmark object
        Object to represent the benchmark.
    solver_names : list | None
        List of solver names to include in the benchmark. If None
        all solvers available are run.
    forced_solvers : list | None
        List of solvers to include in the benchmark and for
        which one forces recomputation.
    dataset_names : list | None
        List of dataset names to include. If None all available
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
    n_jobs : int
        Maximal number of workers to use to run the benchmark in parallel.
    slurm : Path | None
        If not None, launch the job on a slurm cluster using the file to get
        the cluster config parameters.
    plot_result : bool
        If set to True (default), generate the result plot and save them in
        the benchmark directory.
    display : bool
        If set to True (default), open the result plots at the end of the run,
        otherwise, simply save them.
    html : bool
        If set to True (default), display the result plot in HTML, otherwise
        in matplotlib figures, default is True.
    collect : bool
        If set to True, only collect the results that have been put in cache,
        and ignore the results that are not computed yet, default is False.
    show_progress : bool
        If show_progress is set to True, display the progress of the benchmark.
    pdb : bool
        If pdb is set to True, open a debugger on error.
    output_name : str
        Filename for the parquet output. If given, the results will
        be stored at <BENCHMARK>/outputs/<filename>.parquet.

    Returns
    -------
    df : instance of pandas.DataFrame
        The benchmark results. If multiple metrics were computed, each
        one is stored in a separate column. If the number of metrics computed
        by the objective is not the same for all parameters, the missing data
        is set to `NaN`.
    """
    benchmark = Benchmark(benchmark_path)
    solvers = benchmark.check_solver_patterns(
        solver_names + list(forced_solvers)
    )
    datasets = benchmark.check_dataset_patterns(dataset_names)
    objective = benchmark.check_objective_filters(objective_filters)

    return _run_benchmark(
        benchmark, solvers, forced_solvers, datasets, objective,
        max_runs, n_repetitions, timeout, n_jobs, slurm,
        plot_result, display, html, collect, show_progress, pdb, output_name
    )
