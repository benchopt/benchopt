from benchopt import BaseObjective, safe_import_context

with safe_import_context() as import_ctx:
    import numpy as np


class Objective(BaseObjective):
    name = "my-objective"
    min_benchopt_version = "1.5"
    requirements = []
    parameters = {}

    # Set benchmark-wide defaults here so all solvers inherit them:
    # sampling_strategy = "run_once"     # for fixed-budget / ML benchmarks
    # stopping_criterion = NoCriterion() # disable early-stopping

    # Name of the dataset used by `benchopt test`:
    # test_dataset_name = "simulated-small"

    def set_data(self, X, y):
        # Receives Objective.get_data()'s dict unpacked as kwargs.
        self.X, self.y = X, y

    def get_objective(self):
        # Returns the dict unpacked as kwargs into Solver.set_objective().
        return dict(X=self.X, y=self.y)

    def evaluate_result(self, beta):
        # Receives Solver.get_result()'s dict unpacked as kwargs.
        # Must return a dict with at least a scalar "value" key
        # (the quantity benchopt minimises for convergence curves).
        residual = self.y - self.X @ beta
        return dict(value=0.5 * float(np.dot(residual, residual)))

    def get_one_result(self):
        # Returns a dummy solver result for `benchopt test` to validate
        # evaluate_result() without running a real solver.
        return dict(beta=np.zeros(self.X.shape[1]))

    # Optional: skip incompatible dataset/objective combinations.
    # def skip(self, X, y):
    #     if X.shape[0] < X.shape[1]:
    #         return True, "underdetermined system not supported"
    #     return False, None

    # Optional: save artefacts (models, arrays) alongside the parquet.
    # def save_final_results(self, beta):
    #     np.save(self._cache_path / "beta.npy", beta)
