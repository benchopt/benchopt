import time
import math


from .config import DEBUG
from .utils.colorify import LINE_LENGTH


EPS = 1e-10
PATIENCE = 3


class StoppingCriterion():
    """Class to check if we need to stop an algorithm.

    This base class will check for the timeout and the max_run.
    It should be sub-classed to check for the convergence of the algorithm.

    This class also handles the detection of diverging solvers and prints the
    progress if given a ``prgress_str``.

    Instances of this class should only be created with `cls._get_instance`,
    to make sure the class holds the proper attirbutes. This factory mechanism
    allow for easy subclassing without requesting to call the `super.__init___`
    in the subclass.

    Similarly, sub-classes should implement `check-convergence` to check if the
    algorithm has converged. This function will be called internally as a hook
    in `should_stop_solver`, which also handles `timeout`, `max_runs` and
    plateau detection.
    """

    def __init__(self, *args, **kwargs):
        pass

    @classmethod
    def _get_instance(cls, *args, max_runs=1, timeout=None, progress_str=None,
                      **kwargs):
        # Instanciate the subclass
        stopping_criterion = cls(*args, **kwargs)

        # Store critical parameters for hashing and reconstruction
        stopping_criterion.timeout = timeout
        stopping_criterion.max_runs = max_runs
        stopping_criterion.args = args
        stopping_criterion.kwargs = kwargs

        # Store running arguments
        if timeout is not None:
            stopping_criterion._deadline = time.time() + timeout
        else:
            stopping_criterion._deadline = None
        stopping_criterion._prev_objective_value = 1e100
        stopping_criterion._progress_str = progress_str
        return stopping_criterion

    def should_stop_solver(self, cost_curve):
        """Base call to check if we should stop running a solver.

        This base call checks for the timeout and the max number of runs.
        It also notifies the runner if the curve is too flat, to increase
        the number of points between 2 evaluations of the objective.

        Parameters
        ----------
        cost_curve : list of dict
            List of dict containing the values associated to the objective at
            each evaluated points.

        Returns
        -------
        stop : bool
            Whether or not we should stop the algorithm.
        status : str
            Reason why the algorithm was stopped if stop is True.
        is_flat : bool
            Indicate if 2 successive evaluations yielded the same
            objective value. Useful for moving faster on tolerance.
        """
        # Modify the criterion state:
        # - compute the number of run with the curve. We need to remove 1 as
        #   it contains the initial evaluation.
        # - compute the delta_objective for debugging and stalled progress.
        n_eval = len(cost_curve) - 1
        objective_value = cost_curve[-1]['objective_value']
        delta_objective = self._prev_objective_value - objective_value
        self._prev_objective_value = objective_value

        # default value for is_flat
        is_flat = False

        # check the different conditions:
        #     timeout / max_runs / diverging / stopping_criterion
        if self._deadline is not None and time.time() > self._deadline:
            stop = True
            status = 'timeout'

        elif n_eval == self.max_runs:
            stop = True
            status = 'max_runs'

        elif delta_objective < -1e10:
            stop = True
            status = 'diverged'

        else:
            # Call the sub-class hook, used to check stopping criterion
            # on the curve.
            stop, progress = self.check_convergence(cost_curve)

            # Display the progress if necessary
            progress = max(n_eval / self.max_runs, progress)
            self.show_progress(progress=progress)

            # Compute status and notify the runner if the curve is flat.
            status = 'done' if stop else None
            is_flat = delta_objective == 0

        if stop and DEBUG:
            print(f"DEBUG - Exit with delta_objective = {delta_objective:.2e} "
                  f"and n_eval={n_eval:.1e}.")

        return stop, status, is_flat

    def show_progress(self, progress):
        """Display progress in the CLI interface."""
        if self._progress_str is not None:
            if isinstance(progress, float):
                progress = f'{progress:6.1%}'
            print(
                self._progress_str.format(progress=progress)
                .ljust(LINE_LENGTH) + '\r',
                end='', flush=True
            )

    def check_convergence(self, cost_curve):
        """Check if the solver should be stopped based on the objective curve.

        Parameters
        ----------
        cost_curve : list of dict
            List of dict containing the values associated to the objective at
            each evaluated points.

        Returns
        -------
        stop : bool
            Whether or not we should stop the algorithm.
        progress : float
            Measure of how far the solver is from convergence.
            This should be in [0, 1], 0 meaning no progress and 1 meaning
            that the solver has converged.
        """
        return False, 0

    def __reduce__(self):
        return self._get_instance, self.args, dict(
            max_runs=self.max_runs, timeout=self.timeout,
            **self.kwargs
        )


class SufficientDescentCriterion(StoppingCriterion):
    """Stopping criterion based on sufficient descent.

    The solver will be stopped once successive evaluations do not make enough
    progress. The number of successive evaluation and the definition of
    sufficient progress is controled by ``eps`` and ``patience``.

    Parameters
    ----------
    eps :  float (default: benchopt.stopping_criterion.EPS)
        The objective function change is considered as insufficient when it is
        in the interval ``[-eps, eps]``.
    patience :  float (default: benchopt.stopping_criterion.PATIENCE)
        The solver is stopped after ``patience`` successive insufficient
        updates.
    """
    def __init__(self, eps=EPS, patience=PATIENCE):
        self.eps = eps
        self.patience = patience

        self.delta_objectives = []
        self.prev_objective_value = 1e100

    def check_convergence(self, cost_curve):
        """Check if the solver should be stopped based on the objective curve.

        Parameters
        ----------
        cost_curve : list of dict
            List of dict containing the values associated to the objective at
            each evaluated points.

        Returns
        -------
        stop : bool
            Whether or not we should stop the algorithm.
        progress : float
            Measure of how far the solver is from convergence.
            This should be in [0, 1], 0 meaning no progress and 1 meaning
            that the solver has converged.
        """
        # Compute the current objective
        objective_value = cost_curve[-1]['objective_value']
        delta_objective = self.prev_objective_value - objective_value
        self.delta_objectives.append(delta_objective)

        if len(self.delta_objectives) > self.patience:
            self.delta_objectives.pop(0)
        self.prev_objective_value = objective_value

        delta = max(self.delta_objectives)
        if (-self.eps <= delta <= self.eps):
            return True, 1

        progress = math.log(max(abs(delta), self.eps)) / math.log(self.eps)
        return False, progress
