import time
import math

# Possible stop strategies
STOPPING_STRATEGIES = ['iteration', 'tolerance', 'callback']

EPS = 1e-10
PATIENCE = 3


# Define some constants
# TODO: better parametrize this?
MIN_TOL = 1e-15
MAX_ITER = int(1e12)
INFINITY = 3e38  # see: np.finfo('float32').max

RHO = 1.5
RHO_INC = 1.2  # multiplicative update if rho is too small


class StoppingCriterion():
    """Class to check if we need to stop an algorithm.

    This base class will check for the timeout and the max_run.
    It should be sub-classed to check for the convergence of the algorithm.

    This class also handles the detection of diverging solvers and prints the
    progress if given a ``progress_str``.

    Instances of this class should only be created with class method
    `cls.get_runner_instance`, to make sure the class holds the proper
    attributes. This factory mechanism allows for easy subclassing without
    requesting to call the `super.__init___` in the subclass.

    Similarly, sub-classes should implement `check-convergence` to check if the
    algorithm has converged. This function will be called internally as a hook
    in `should_stop`, which also handles `timeout`, `max_runs` and
    plateau detection.

    Parameters
    ----------
    **kwargs : dict
        All parameters passed when instantiating the StoppingCriterion. This
        will be used to re-create the criterion with extra arguments in the
        runner.
    strategy : str in {'iteration', 'tolerance', 'callback'}
        How the different precision solvers are called. Can be one of:
        - ``'iteration'``: call the run method with max_iter number increasing
        logarithmically to get more an more precise points.
        - ``'tolerance'``: call the run method with tolerance decreasing
        logarithmically to get more and more precise points.
        - ``'callback'``: call the run method with a callback that will compute
        the objective function on a logarithmic scale. After each iteration,
        the callback should be called with the current iterate solution.
    key_to_monitor : str (default: 'objective_value')
        The objective to check for tracking progress.
    """
    kwargs = None

    def __init__(self, strategy=None, key_to_monitor='objective_value',
                 **kwargs):

        assert strategy in STOPPING_STRATEGIES, (
            f"strategy should be in {STOPPING_STRATEGIES}. Got '{strategy}'."
        )

        self.kwargs = kwargs
        self.strategy = strategy
        self.key_to_monitor = key_to_monitor

    def get_runner_instance(self, max_runs=1, timeout=None, output=None,
                            solver=None):
        """Copy the stopping criterion and set the parameters that depends on
        how benchopt runner is called.

        Parameters
        ----------
        max_runs : int
            The maximum number of solver runs to perform to estimate
            the convergence curve.
        timeout : float
            The maximum duration in seconds of the solver run.
        output : TerminalOutput or None
            Object to format string to display the progress of the solver.
        solver : BaseSolver
            The solver for which this stopping criterion is called. Used to get
            overridden ``stopping_strategy`` and ``get_next``.

        Returns
        -------
        stopping_criterion : StoppingCriterion
            The stopping criterion instance to use in the runner, with
            correct timeout and max_runs parameters.
        """

        # Check that the super constructor is correctly called in the
        # sub-classes
        if self.kwargs is None:
            raise ValueError(
                f"{self.__class__.__name__} is a subclass of StoppingCriterion"
                " but did not called super().__init__(**kwargs) with all its "
                "parameters in its constructor. See XXX for details on how "
                "to implement a new StoppingCriterion."
            )

        # Get strategy from solver
        strategy = self.strategy
        if solver is not None:
            strategy = solver._solver_strategy
        assert strategy in STOPPING_STRATEGIES, (
            f"stopping_strategy should be in {STOPPING_STRATEGIES}. "
            f"Got '{strategy}'."
        )

        # Create a new instance of the class
        stopping_criterion = self.__class__(
            strategy=strategy, key_to_monitor=self.key_to_monitor,
            **self.kwargs,
        )

        # Set stopping criterion parameters depending on run parameters
        stopping_criterion.rho = RHO
        stopping_criterion.timeout = timeout
        stopping_criterion.max_runs = max_runs
        stopping_criterion.output = output
        stopping_criterion.solver = solver

        # Override get_next_stop_val if ``get_next`` is implemented for solver.
        if hasattr(solver, 'get_next'):
            assert (
                callable(solver.get_next)
                # and type(solver.get_next) == staticmethod
            ), "if defined, get_next should be a static method of the solver."
            try:
                solver.get_next(0)
            except TypeError:
                raise ValueError(
                    "get_next(0) throw a TypeError. Verify that `get_next` "
                    "signature is get_next(stop_val) and that it is "
                    "a staticmethod."
                )

            stopping_criterion.get_next_stop_val = solver.get_next

        # Store running arguments
        if timeout is not None:
            stopping_criterion._deadline = time.time() + timeout
        else:
            stopping_criterion._deadline = None
        stopping_criterion._prev_objective = 1e100

        return stopping_criterion

    def init_stop_val(self):
        stop_val = (
            INFINITY if self.strategy == 'tolerance' else 0
        )

        self.debug(f"Calling solver {self.solver} with stop val: {stop_val}")
        self.progress('initialization')
        return stop_val

    def should_stop(self, stop_val, cost_curve):
        """Base call to check if we should stop running a solver.

        This base call checks for the timeout and the max number of runs.
        It also notifies the runner if the curve is too flat, to increase
        the number of points between 2 evaluations of the objective.

        Parameters
        ----------
        stop_val : int | float
            Corresponds to stopping criterion of the underlying algorithm, such
            as ``tol`` or ``max_iter``.
        cost_curve : list of dict
            List of dict containing the values associated to the objective at
            each evaluated points.

        Returns
        -------
        stop : bool
            Whether or not we should stop the algorithm.
        status : str
            Reason why the algorithm was stopped if stop is True.
        next_stop_val : int | float
            Next value for the stopping criterion. This value depends on the
            stop strategy for the solver.
        """
        # Modify the criterion state:
        # - compute the number of run with the curve. We need to remove 1 as
        #   it contains the initial evaluation.
        # - compute the delta_objective for debugging and stalled progress.
        n_eval = len(cost_curve) - 1
        objective = cost_curve[-1][self.key_to_monitor]
        delta_objective = self._prev_objective - objective
        delta_objective /= abs(cost_curve[0][self.key_to_monitor])
        self._prev_objective = objective

        # default value for is_flat
        is_flat = False

        # check the different conditions:
        #     diverging / timeout / max_runs / stopping_criterion
        if math.isnan(objective) or delta_objective < -1e5:
            stop = True
            status = 'diverged'
        elif self._deadline is not None and time.time() > self._deadline:
            stop = True
            status = 'timeout'

        elif n_eval == self.max_runs:
            stop = True
            status = 'max_runs'
        else:
            # Call the sub-class hook, used to check stopping criterion
            # on the curve.
            stop, progress = self.check_convergence(cost_curve)

            # Display the progress if necessary
            progress = max(n_eval / self.max_runs, progress)

            # Compute status and notify the runner if the curve is flat.
            status = 'done' if stop else 'running'
            is_flat = delta_objective == 0

        if stop:
            self.debug(
                f"Exit with delta_objective = {delta_objective:.2e} and "
                f"n_eval={n_eval:.1e}."
            )

        if is_flat:
            self.rho *= RHO_INC
            self.debug(f"curve is flat -> increasing rho: {self.rho}")

        if status == 'running':
            stop_val = self.get_next_stop_val(stop_val)
            self.debug(f"Calling with stop val: {stop_val}")
            self.progress(progress=progress)

        return stop, status, stop_val

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

    def debug(self, msg):
        """Helper to print debug messages."""
        if self.output is not None:
            self.output.debug(msg)

    def progress(self, progress):
        """Helper to print progress messages."""
        if self.output is not None:
            self.output.progress(progress)

    @staticmethod
    def _reconstruct(klass, kwargs, runner_kwargs):
        criterion = klass(**kwargs)
        return criterion.get_runner_instance(**runner_kwargs)

    def __reduce__(self):
        kwargs = dict(
            strategy=self.strategy, **self.kwargs
        )
        runner_kwargs = dict(
            max_runs=self.max_runs, timeout=self.timeout,
            output=self.output, solver=self.solver
        )
        return self._reconstruct, (self.__class__, kwargs, runner_kwargs)

    def get_next_stop_val(self, stop_val):
        if self.strategy == "tolerance":
            return min(1, max(stop_val / self.rho, MIN_TOL))
        else:
            return max(stop_val + 1, min(int(self.rho * stop_val), MAX_ITER))


class SufficientDescentCriterion(StoppingCriterion):
    """Stopping criterion based on sufficient descent.

    The solver will be stopped once successive evaluations do not make enough
    progress. The number of successive evaluation and the definition of
    sufficient progress is controlled by ``eps`` and ``patience``.

    Parameters
    ----------
    eps :  float (default: benchopt.stopping_criterion.EPS)
        The objective function change is considered as insufficient when it is
        in the interval ``[-eps, eps]``.
    patience :  float (default: benchopt.stopping_criterion.PATIENCE)
        The solver is stopped after ``patience`` successive insufficient
        updates.
    strategy : str in {'iteration', 'tolerance', 'callback'}
        (default: 'iteration')
        How the different precision solvers are called. Can be one of:
        - ``'iteration'``: call the run method with max_iter number increasing
        logarithmically to get more an more precise points.
        - ``'tolerance'``: call the run method with tolerance decreasing
        logarithmically to get more and more precise points.
        - ``'callback'``: call the run method with a callback that will compute
        the objective function on a logarithmic scale. After each iteration,
        the callback should be called with the current iterate solution.
    key_to_monitor : str (default: 'objective_value')
        The objective to check for tracking progress.
    """

    def __init__(self, eps=EPS, patience=PATIENCE, strategy='iteration',
                 key_to_monitor='objective_value'):
        self.eps = eps
        self.patience = patience

        self._delta_objectives = []
        self._objective = 1e100

        super().__init__(
            eps=eps, patience=patience, strategy=strategy,
            key_to_monitor=key_to_monitor
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
        # Compute the current objective
        objective = cost_curve[-1][self.key_to_monitor]
        delta_objective = self._objective - objective
        delta_objective /= abs(cost_curve[0][self.key_to_monitor])
        self._objective = objective

        # Store only the last ``patience`` values for progress
        self._delta_objectives.append(delta_objective)
        if len(self._delta_objectives) > self.patience:
            self._delta_objectives.pop(0)

        delta = max(self._delta_objectives)
        if (-self.eps <= delta <= self.eps):
            self.debug(f"Exit with delta_objective = {delta:.2e}.")
            return True, 1

        progress = math.log(max(abs(delta), self.eps)) / math.log(self.eps)
        return False, progress


class SufficientProgressCriterion(StoppingCriterion):
    """Stopping criterion based on sufficient progress.

    The solver will be stopped once successive evaluations do not make enough
    progress. The number of successive evaluation and the definition of
    sufficient progress is controlled by ``eps`` and ``patience``.

    Parameters
    ----------
    eps :  float (default: benchopt.stopping_criterion.EPS)
        The progress between two steps is considered as insufficient when it is
        smaller than ``eps``.
    patience :  float (default: benchopt.stopping_criterion.PATIENCE)
        The solver is stopped after ``patience`` successive insufficient
        updates.
    strategy : str in {'iteration', 'tolerance', 'callback'}
        (default: 'iteration')
        How the different precision solvers are called. Can be one of:
        - ``'iteration'``: call the run method with max_iter number increasing
        logarithmically to get more an more precise points.
        - ``'tolerance'``: call the run method with tolerance decreasing
        logarithmically to get more and more precise points.
        - ``'callback'``: call the run method with a callback that will compute
        the objective function on a logarithmic scale. After each iteration,
        the callback should be called with the current iterate solution.
    key_to_monitor : str (default: 'objective_value')
        The objective to check for tracking progress.
    """

    def __init__(self, eps=EPS, patience=PATIENCE, strategy='iteration',
                 key_to_monitor='objective_value'):
        self.eps = eps
        self.patience = patience

        self._progress = []
        self._best_objective = 1e100

        super().__init__(
            eps=eps, patience=patience, strategy=strategy,
            key_to_monitor=key_to_monitor
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
        # Compute the current objective and update best value
        objective = cost_curve[-1][self.key_to_monitor]
        delta_objective = self._best_objective - objective
        delta_objective /= abs(cost_curve[0][self.key_to_monitor])
        self._best_objective = min(
            objective, self._best_objective
        )

        # Store only the last ``patience`` values for progress
        self._progress.append(delta_objective)
        if len(self._progress) > self.patience:
            self._progress.pop(0)

        delta = max(self._progress)
        if delta <= self.eps * self._best_objective:
            self.debug(f"Exit with delta = {delta:.2e}.")
            return True, 1

        progress = math.log(max(abs(delta), self.eps)) / math.log(self.eps)
        return False, progress
