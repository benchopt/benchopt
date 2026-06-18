import time
from datetime import datetime
from pathlib import Path

from .callback import _Callback
from .benchmark import Benchmark
from .utils.sys_info import get_sys_info
from .utils.pdb_helpers import exception_handler
from .utils.terminal_output import TerminalOutput
from .parallel_backends import parallel_run
from .parallel_backends import check_parallel_config
from .results import save_results
from ._generate_runs import generate_run_kwargs


FAILURE_STATUS = ['diverged', 'error', 'interrupted']
SUCCESS_STATUS = ['done', 'max_runs', 'timeout']


class FailedRun(RuntimeError):
    """Exception raised when a solver run fails."""
    def __init__(self, status):
        super().__init__()
        self.status = status


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
    objective_list = objective(result)

    # Add system info in results
    info = get_sys_info()

    return [
        dict(**meta, stop_val=stop_val, time=delta_t, **objective_dict, **info)
        for objective_dict in objective_list
    ], result


def run_one_to_cvg(benchmark, objective, solver, meta, timeout, max_runs,
                   force=False, terminal=None, run_context=None):
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
    timeout : float
        The maximum duration in seconds of the solver run.
    max_runs : int
        The maximum number of solver runs to perform to estimate the
        convergence curve.
    force : bool
        If force is set to True, ignore the cache and run the computations
        for the solver anyway. Else, use the cache if available.
    terminal : TerminalOutput or None
        Object to format string to display the progress of the solver.
    run_context : RunContext | None
        Per-run context (seeds, artifact path). Ignored by the cache;
        set on objective and solver so user methods can call
        ``get_seed()`` and ``get_run_output_path()``.

    Returns
    -------
    curve : list of Cost
        The cost obtained for all repetitions.
    key : tuple of string
        The key to identify the run in the benchmark results.
    status : 'done' | 'diverged' | 'timeout' | 'max_runs'
        The status on which the solver was stopped.
    """
    # Re-attach the run context after deserialization (it is excluded from
    # pickle via __getstate__ so workers receive components without it).
    run_context.attach(objective, getattr(objective, '_dataset', None), solver)

    pdb = run_context.pdb if run_context is not None else False

    curve = []

    run_key = (
        meta['dataset_name'],
        meta['objective_name'],
        meta['solver_name']
    )

    with exception_handler(terminal, pdb=pdb) as ctx:

        skip, reason = solver._set_objective(objective)
        if skip:
            return [], run_key, 'skip', reason

        stopping_criterion = (
            solver._stopping_criterion.get_runner_instance(
                solver=solver,
                max_runs=max_runs,
                timeout=timeout,
                terminal=terminal,
                run_key=run_key,
            )
        )

        # The warm-up step called for each repetition bit only run once.
        solver._warm_up()

        if solver._solver_strategy == "callback":

            # If sampling_strategy is 'callback', only call once to get the
            # results up to convergence.
            callback = _Callback(
                objective, solver, meta, stopping_criterion
            )
            solver.pre_run_hook(callback)
            callback.start()
            solver.run(callback)
            curve, ctx.status, last_result = callback.get_results()
        else:

            # Create a Memory object to cache the computations in the
            # benchmark folder and handle cases where we force the run.
            # TODO: Skip caching if the sampling strategy is 'run_once'
            # since the call to this function is a single call to
            # run_one_resolution. This needs to be done once stopping
            # criterion does not depend on the terminal anymore.
            run_one_resolution_cached = benchmark.cache(
                run_one_resolution, force,
            )

            # compute initial value
            call_args = dict(objective=objective, solver=solver, meta=meta)

            stop = False
            stop_val = stopping_criterion.init_stop_val()
            while not stop:

                objective_list, last_result = run_one_resolution_cached(
                    stop_val=stop_val, **call_args
                )
                curve.extend(objective_list)

                # Check the stopping criterion and update rho if necessary.
                stop, ctx.status, stop_val = (
                    stopping_criterion.should_stop(stop_val, curve)
                )

        # Save final results if the run did not fail.
        to_save = objective.save_final_results(**last_result)
        if to_save is not None:
            curve[-1]["final_results"] = to_save

    # Make sure to flush so the parallel output is properly display
    print(end='', flush=True)

    # Avoid caching failed runs by raising an exception in this case,
    # and catching it in the monitoring loop.
    if ctx.status in FAILURE_STATUS:
        raise FailedRun(ctx.status)

    return curve, run_key, ctx.status, ""


def _run_benchmark(benchmark, solvers=None, forced_solvers=None,
                   datasets=None, objectives=None, max_runs=10,
                   n_repetitions=1, timeout=100,
                   plot_result=True, display=True, html=True, collect=False,
                   output_file="None", parallel_config=None,
                   show_progress=True, pdb=False):
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
    parallel_config : dict | None
        If not None, launch the job in parallel. The provided config serves to
        set up parallelism using ``joblib.parallel_backend`` or ``submitit``.
        See :ref:`parallel_run` for detailed description.
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
    output_file : str
        Filename for the parquet output. If given, the results will
        be stored at <BENCHMARK>/outputs/<filename>.parquet.

    Returns
    -------
    exit_code : int
        Exit code of the benchmark run. 0 if everything went fine,
        1 otherwise.
    output_file : Path
        Path to the output file where the results have been saved.
    """
    exit_code = 0
    terminal = TerminalOutput(n_repetitions, show_progress)

    # Resolve the output filename stem before runs start so that
    # run_output_base is stable across all workers.
    output_dir = benchmark.get_output_folder()
    if output_file == "None":
        timestamp = datetime.now().strftime('%Y-%m-%d_%Hh%Mm%S')
        output_file = f'benchopt_run_{timestamp}.parquet'
    from .utils.run_context import RunContext
    base_run_context = RunContext(
        pdb=pdb,
        run_output_base=output_dir / Path(output_file).stem,
    )

    run_one_to_cvg_cached = benchmark.cache(
        run_one_to_cvg,
        ignore=['force', 'terminal', 'run_context'],
        collect=collect
    )

    def run_one_to_cvg_final(**kwargs):
        try:
            return run_one_to_cvg_cached(**kwargs)
        except FailedRun as e:
            # If the run fails, return an empty result with the failure status
            # This is done to avoid caching failed runs.
            key = (
                kwargs['meta']['dataset_name'],
                kwargs['meta']['objective_name'],
                kwargs['meta']['solver_name']
            )
            return ([], key, e.status, "")

    total_cvg_kwargs_generator = generate_run_kwargs(
        benchmark, solvers=solvers, forced_solvers=forced_solvers,
        datasets=datasets, objectives=objectives,
        n_repetitions=n_repetitions, max_runs=max_runs, timeout=timeout,
        collect=collect, terminal=terminal, run_context=base_run_context,
    )

    run_statistics = []

    results_generator = parallel_run(
        benchmark, run_one_to_cvg_final, total_cvg_kwargs_generator,
        config=parallel_config, collect=collect
    )
    try:
        for result, key, status, reason in results_generator:
            run_statistics.extend(result)
            terminal.set(dataset=key[0], objective=key[1], solver=key[2])
            terminal.show_status(status=status, reason=reason)
            if status == 'interrupted':
                raise SystemExit(1)
    except KeyboardInterrupt:
        print(end='', flush=True)
        terminal.show_status('interrupted')
        raise

    import pandas as pd
    df = pd.DataFrame(run_statistics)
    if df.empty:
        terminal.savefile_status()
        return 1, None

    # Save output in parquet file in the benchmark folder
    output_file = save_results(df, output_dir / output_file)

    if plot_result:
        try:
            from benchopt.plotting import plot_benchmark
            plot_benchmark(output_file, benchmark, html=html, display=display)
        except Exception as e:
            print(f"Failed to plot the benchmark results: {e}")
            exit_code = 1

    return exit_code, output_file


def run_benchmark(benchmark_path, solver_names=None, forced_solvers=(),
                  dataset_names=None, objective_filters=None, max_runs=10,
                  n_repetitions=1, timeout=None,
                  n_jobs=None, parallel_config=None,
                  plot_result=True, display=True, html=True,  collect=False,
                  show_progress=True, pdb=False, no_cache=False,
                  output_file="None"):
    """Run full benchmark.

    Parameters
    ----------
    benchmark_path : str | Path | Benchmark
        Path to the benchmark directory, **or** an already-constructed
        :class:`~benchopt.Benchmark` instance (e.g. from
        :func:`benchopt.mini.get_benchmark`).  When a ``Benchmark`` instance
        is passed directly, ``no_cache`` is ignored (use the instance's own
        setting).
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
    parallel_config : dict | None
        If not None, launch the job in parallel. The provided config serves to
        set up parallelism using ``joblib.parallel_backend`` or ``submitit``.
        See :ref:`parallel_run` for detailed description.
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
    no_cache : bool
        If set to True, this deactivates the caching mechanism integrated in
        benchopt. Note that this makes the run less tolerant to errors, use it
        with caution.
    output_file : str
        Filename for the parquet output. If given, the results will
        be stored at <BENCHMARK>/outputs/<filename>.parquet.

    Returns
    -------
    exit_code : int
        Exit code of the benchmark run. 0 if everything went fine,
        1 otherwise.
    output_file : Path
        Path to the output file where the results have been saved.
    """
    if isinstance(benchmark_path, Benchmark):
        benchmark = benchmark_path
    else:
        benchmark = Benchmark(benchmark_path, no_cache=no_cache)
    if solver_names is None:
        solver_names = []
    solvers = benchmark.check_solver_patterns(
        solver_names + list(forced_solvers)
    )
    datasets = benchmark.check_dataset_patterns(dataset_names)
    objectives = benchmark.check_objective_filters(objective_filters)

    parallel_config = check_parallel_config(parallel_config, n_jobs)

    exit_code, output_file = _run_benchmark(
        benchmark=benchmark,
        solvers=solvers,
        forced_solvers=forced_solvers,
        datasets=datasets,
        objectives=objectives,
        max_runs=max_runs,
        n_repetitions=n_repetitions,
        timeout=timeout,
        plot_result=plot_result,
        display=display,
        html=html,
        collect=collect,
        show_progress=show_progress,
        parallel_config=parallel_config,
        pdb=pdb,
        output_file=output_file
    )
    if exit_code != 0:
        raise RuntimeError("Benchmark failed, check the terminal output.")
    return output_file
