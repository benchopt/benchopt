import time
import numpy as np
import pandas as pd
from joblib import Memory


from .base import Cost
from .viz import plot_benchmark
from .util import filter_solvers
from .util import get_parameter_product
from .util import list_benchmark_solvers
from .util import list_benchmark_datasets
from .util import get_benchmark_objective
from .config import get_global_setting, get_benchmark_setting


DEBUG = get_global_setting('debug')
CACHE_DIR = get_global_setting('cache_dir')
mem = Memory(location=CACHE_DIR, verbose=0)


SAMPLING_STRATEGIES = ['iteration', 'tolerance']
PATIENCE = 5
MAX_ITER = int(1e6)
MIN_TOL = 1e-15


@mem.cache(ignore=['progress'])
def run_one_sample(objective, solver_class, solver_parameters,
                   sample, n_rep=1, meta={}, progress=None):
    # Instantiate the solver
    solver = solver_class(**solver_parameters)
    solver.set_objective(**objective.to_dict())

    curve = []
    current_objective = []
    for rep in range(n_rep):
        print(f"|--{solver}: {progress:6.1%} ({rep} / {n_rep})\r",
              end='', flush=True)
        t_start = time.time()
        solver.run(sample)
        delta_t = time.time() - t_start
        beta_hat_i = solver.get_result()
        objective_value = objective(beta=beta_hat_i)
        current_objective.append(objective_value)
        curve.append(Cost(**meta, solver=str(solver), sample=sample,
                          time=delta_t, objective=objective_value,
                          repetition=rep))

    return curve, np.max(current_objective)


def run_one_solver(objective, solver_class, solver_parameters,
                   max_samples, n_rep=1, force=False, meta={}):
    """Minimize a objective function with the given solver for different accuracy
    """

    # TODO: parametrize
    rho = 1.5
    eps = 1e-10

    # Instantiate the solver
    solver = solver_class(**solver_parameters)

    # Sample the performances for different accuracy, either by varying the
    # tolerance or the maximal number of iterations
    curve = []
    if solver.sampling_strategy == 'iteration':
        def get_next(x): return max(x + 1, min(int(rho * x), MAX_ITER))

    elif solver.sampling_strategy == 'tolerance':
        def get_next(x): return max(x / rho, MIN_TOL)

    def progress(id_sample, delta):
        return max(id_sample / max_samples,
                   np.log(max(delta, eps)) / np.log(eps))

    id_sample = 0
    sample = 1
    delta_objectives = [1e100]
    prev_objective_value = np.inf

    for id_sample in range(max_samples):
        if (np.max(delta_objectives) < eps):
            # We are on a plateau and the objective is not improving
            # stop here on the sampling
            print(f"|--{solver}: done".ljust(40))
            break

        p = progress(id_sample, np.max(delta_objectives))

        run_args = dict(
            objective=objective, solver_class=solver_class,
            solver_parameters=solver_parameters, sample=sample,
            n_rep=n_rep, progress=p, meta=meta
        )
        if force:
            run_one_sample.call(**run_args)

        sample_curve, objective_value = run_one_sample(**run_args)
        curve.extend(sample_curve)

        # objective_value = np.mean(current_objective)
        delta_objective = prev_objective_value - objective_value
        delta_objectives.append(delta_objective)
        if delta_objective == 0:
            rho *= 1.2
        if len(delta_objectives) > PATIENCE:
            delta_objectives.pop(0)
        prev_objective_value = objective_value
        sample = get_next(sample)
    else:
        print(f"|--{solver}: done (did not converged)".ljust(40))

    if DEBUG:
        delta = np.max(delta_objectives)
        print(f"|    Exit with delta_objective = {delta:.2e} and "
              f"sampling_parameter={sample}.")
    return curve


def run_benchmark(benchmark, solver_names=None, forced_solvers=None,
                  max_samples=10, n_rep=1):

    # Load the benchmark function and the datasets
    objective_class = get_benchmark_objective(benchmark)
    it_obj_parameters = get_parameter_product(objective_class.parameters)

    datasets = list_benchmark_datasets(benchmark)

    # Load the solvers to execute
    solver_classes = list_benchmark_solvers(benchmark)
    exclude = get_benchmark_setting(benchmark, 'exclude_solvers')
    solver_classes = filter_solvers(solver_classes, solver_names=solver_names,
                                    forced_solvers=forced_solvers,
                                    exclude=exclude)

    res = []
    for dataset_class in datasets:
        it_data_parameters = get_parameter_product(dataset_class.parameters)
        for dataset_parameters in it_data_parameters:
            dataset = dataset_class(**dataset_parameters)
            print(dataset)
            scale, data = dataset.get_data()
            for obj_parameters in it_obj_parameters:
                objective = objective_class(**obj_parameters)
                print(objective)
                objective.set_data(**data)
                meta = dict(data=str(dataset), scale=scale)
                for solver in solver_classes:
                    it_solver_parameters = get_parameter_product(
                        solver.parameters)
                    for solver_parameters in it_solver_parameters:

                        force = solver.name.lower() in forced_solvers
                        try:
                            res.extend(run_one_solver(
                                objective=objective, solver_class=solver,
                                solver_parameters=solver_parameters,
                                max_samples=max_samples, n_rep=n_rep,
                                force=force, meta=meta
                            ))
                        except Exception:
                            import traceback
                            traceback.print_exc()
    df = pd.DataFrame(res)
    plot_benchmark(df, benchmark)
