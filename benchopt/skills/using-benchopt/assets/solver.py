from benchopt import BaseSolver


class Solver(BaseSolver):
    name = "my-solver"
    requirements = []
    parameters = {}
    # Fast config for `benchopt test` — solver params as top-level keys, with
    # optional "dataset" / "objective" overrides:
    # test_config = {"<param>": <value>, "dataset": {"name": "simulated"}}

    # Set sampling_strategy to "run_once" for fixed-budget / ML solvers.
    # Use "callback" for online monitoring of convergence:
    #   def run(self, callback):
    #       while callback():
    #           ...  # one iteration
    # Use "iteration" (default) for classical iterative solvers:
    #   def run(self, n_iter): ...
    sampling_strategy = "iteration"

    # Override to disable early stopping (e.g. for fixed-budget DL training):
    # stopping_criterion = NoCriterion()

    def set_objective(self, **objective_dict):
        # Called once per (dataset, objective) pair before timed runs.
        # Store everything the solver needs on self.
        # objective_dict = Objective.get_objective()
        pass

    def run(self, n_iter):
        # Do n_iter steps of work. Do NOT return the result here.
        pass

    def get_result(self):
        # Return a dict whose keys match Objective.evaluate_result()'s args.
        return {}

    def skip(self, **objective_dict):
        # Return (True, "reason") to opt out of an incompatible objective.
        return False, None

    # Optional: absorb JIT / compilation cost before timed runs.
    # def warm_up(self):
    #     self.run_once()
