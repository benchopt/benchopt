
from benchopt.utils.temp_benchmark import temp_benchmark
from benchopt.tests.utils import CaptureRunOutput
from benchopt.cli.main import run
import time


def test_cv_loops(no_debug_log):

    objective = """from benchopt import safe_import_context
    from benchopt.helpers.cv_loops import NestedCVObjective

    class Objective(NestedCVObjective):
        name = "Test CV loops"
        requirements = ['scikit-learn']
        def get_scoring(self):
            return 'accuracy'

    """

    solver1 = """from benchopt import safe_import_context
    from benchopt.helpers.cv_loops import CVSolver

    with safe_import_context() as import_ctx:
        from sklearn.linear_model import LogisticRegression

    class Solver(CVSolver):

        name = 'LR'
        param_grid = {'C' : [0.1, 1, 10]}

        # The function that return the estimator class. It should follow the sklearn
        # Estimator API for supervised learning.
        def get_estimator(self):
            return LogisticRegression()
    """

    solver2 = """from benchopt import BaseSolver

    class Solver(BaseSolver):
        name = "normal-solver"
        sampling_strategy = 'iteration'
        def set_objective(self, X, y): pass
        def run(self, n_iter): pass
        def get_result(self): return dict(beta=1)
    """

    dataset = """from benchopt import BaseDataset, safe_import_context

    with safe_import_context() as import_ctx:
        from sklearn.datasets import make_classification

    class Dataset(BaseDataset):
        name = "Simulated"

        parameters = {
            'n_samples, n_features': [(100, 10),],
        }

        def get_data(self):
            X, y = make_classification(n_samples=self.n_samples, n_features=self.n_features, n_informative=1,
                                    n_redundant=0, n_clusters_per_class=1, random_state=0)

            # The dictionary defines the keyword arguments for `Objective.set_data`
            return dict(X=X, y=y)

    """

    with temp_benchmark(objective=objective,
                        solvers=[solver1, ],
                        datasets=[dataset]) as benchmark:
        with CaptureRunOutput() as out:
            for it in range(2):
                run([str(benchmark.benchmark_dir), ],
                    standalone_mode=False)
                # benchmark is too quick to run, without sleep output files
                # have the same name and the unlinking fails:
                if it == 0:
                    time.sleep(1.1)

    # error message should be displayed twice
    out.check_output("done", repetition=2)
