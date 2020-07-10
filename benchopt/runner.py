import time
import numpy as np
import pandas as pd
from joblib import Memory


from .base import Cost
from .viz import plot_benchmark
from .util import is_matched
from .util import product_param
from .util import filter_classes_on_name
from .util import list_benchmark_solvers
from .util import list_benchmark_datasets
from .util import get_benchmark_objective
from .config import get_global_setting, get_benchmark_setting


# Get config values
DEBUG = get_global_setting('debug')
CACHE_DIR = get_global_setting('cache_dir')


# Define some constants
# TODO: better parametrize this?
PATIENCE = 5
MAX_ITER = int(1e6)
MIN_TOL = 1e-15


# jobib cache to avoid loosing computations
mem = Memory(location=CACHE_DIR, verbose=0)


###################################
# Helper function for outputs
###################################
BLACK, RED, GREEN, YELLOW, BLUE, MAGENTA, CYAN, WHITE = range(30, 38)


def colorify(message, color=BLUE):
    """Change color of the standard output"""
    return ("\033[1;%dm" % color) + message + "\033[0m"


##################################
# Time one run of a solver
##################################
@mem.cache
def run_repetition(objective, solver_class, solver_parameters, meta, sample):

    # check if the module caught a failed import
    if not solver_class.is_installed():
        raise ImportError(
            f"Failure during import in {solver_class.__module__}.")

    # Instantiate solver here to avoid having weird pickling errors
    solver = solver_class(**solver_parameters)
    solver.set_objective(**objective.to_dict())

    t_start = time.perf_counter()
    solver.run(sample)
    delta_t = time.perf_counter() - t_start
    beta_hat_i = solver.get_result()
    objective_value = objective(beta=beta_hat_i)

    return (Cost(**meta, solver=str(solver), sample=sample, time=delta_t,
                 obj=objective_value), objective_value)


@mem.cache(ignore=['deadline'])
def run_one_sample(objective, solver_class, solver_parameters, meta, sample,
                   n_rep, progress_str, deadline, force=False):

    curve = []
    current_objective = []
    for rep in range(n_rep):
        print(f"{progress_str} ({rep} / {n_rep})\r",
              end='', flush=True)

        meta_rep = dict(**meta, idx_rep=rep)

        # Force the run if needed
        args = (objective, solver_class, solver_parameters, meta_rep, sample)
        if force:
            run_repetition.call(*args)
        cost, objective_value = run_repetition(*args)

        curve.append(cost)
        current_objective.append(objective_value)

        if deadline < time.time():
            # Reached the timeout so stop the computation here
            break

    return curve, np.max(current_objective)


def run_one_solver(objective, solver_class, solver_parameters,
                   meta, max_samples, timeout, n_rep=1, force=False):
    """Minimize a objective function with the given solver for different accuracy
    """

    # TODO: parametrize
    rho = 1.5
    eps = 1e-10

    # Instantiate solver to get its name
    solver_name = str(solver_class(**solver_parameters))
    tag = colorify(f"|----{solver_name}:")

    # Sample the performances for different accuracy, either by varying the
    # tolerance or the maximal number of iterations
    curve = []
    if solver_class.sampling_strategy == 'iteration':
        def get_next(x): return max(x + 1, min(int(rho * x), MAX_ITER))

    elif solver_class.sampling_strategy == 'tolerance':
        def get_next(x): return max(x / rho, MIN_TOL)

    def progress(id_sample, delta):
        return max(id_sample / max_samples,
                   np.log(max(delta, eps)) / np.log(eps))

    # check if the module caught a failed import
    if not solver_class.is_installed():
        status = colorify("failed import", RED)
        print(f"{tag} {status}".ljust(80))
        return curve

    id_sample = 0
    sample = 1
    delta_objectives = [1e15]
    prev_objective_value = np.inf

    deadline = time.time() + timeout

    try:
        for id_sample in range(max_samples):
            if (np.max(delta_objectives) < eps):
                # We are on a plateau and the objective is not improving
                # stop here on the sampling
                status = colorify('done', GREEN)
                break

            p = progress(id_sample, np.max(delta_objectives))
            progress_str = f"{tag} {p:6.1%}"

            call_args = dict(
                objective=objective, solver_class=solver_class,
                solver_parameters=solver_parameters, sample=sample,
                n_rep=n_rep, progress_str=progress_str, meta=meta,
                force=force, deadline=deadline
            )
            if force:
                run_one_sample.call(**call_args)
            sample_curve, objective_value = run_one_sample(**call_args)
            curve.extend(sample_curve)

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
            sample = get_next(sample)
        else:
            status = colorify("done (did not converge)", YELLOW)
        if DEBUG:
            delta = np.max(delta_objectives)
            print(f"{tag} DEBUG - Exit with delta_objective = {delta:.2e} "
                  f"and sampling_parameter={sample:.1e}.")
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
                  dataset_names=None, max_samples=10, timeout=100,
                  n_rep=1):

    # Load the objective class for this benchmark and the datasets
    objective_class = get_benchmark_objective(benchmark)
    datasets = list_benchmark_datasets(benchmark)

    # Load the solvers and filter them to get the one to run
    solver_classes = list_benchmark_solvers(benchmark)
    exclude = get_benchmark_setting(benchmark, 'exclude_solvers')
    solver_classes = filter_classes_on_name(
        solver_classes, include=solver_names,
        forced=forced_solvers, exclude=exclude
    )

    run_statistics = []
    for dataset_class in datasets:
        for dataset_parameters in product_param(dataset_class.parameters):
            dataset = dataset_class(**dataset_parameters)
            if not is_matched(str(dataset), dataset_names):
                continue
            print(f"{dataset}")
            scale, data = dataset.get_data()
            for obj_parameters in product_param(objective_class.parameters):
                objective = objective_class(**obj_parameters)
                print(f"|--{objective}")
                objective.set_dataset(dataset)

                for solver_class in solver_classes:
                    for solver_parameters in product_param(
                            solver_class.parameters):

                        # Get meta
                        meta = dict(
                            objective=str(objective), data=str(dataset),
                            scale=scale
                        )

                        force = solver_class.name.lower() in forced_solvers
                        run_statistics.extend(run_one_solver(
                            objective=objective, solver_class=solver_class,
                            solver_parameters=solver_parameters, meta=meta,
                            max_samples=max_samples, timeout=timeout,
                            n_rep=n_rep, force=force
                        ))
    df = pd.DataFrame(run_statistics)
    plot_benchmark(df, benchmark)
    return df
