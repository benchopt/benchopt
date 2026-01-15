import time
import math

# Possible curve sampling strategies
SAMPLING_STRATEGIES = ['iteration', 'tolerance', 'callback', 'run_once']

EPS = 1e-10
PATIENCE = 3


# Define some constants
# TODO: better parametrize this?
MIN_TOL = 1e-15
MAX_ITER = int(1e12)
INFINITY = 3e38  # see: np.finfo('float32').max

RHO = 1.5
RHO_INC = 1.2  # multiplicative update if rho is too small


COMMON_ARGS_DOC = """
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


class StoppingCriterion():
    f"""Class to check if we need to stop an algorithm.

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
        runner.{COMMON_ARGS_DOC}
    """
    kwargs = None

    def __init__(self, strategy=None, key_to_monitor=None, **kwargs):

        if strategy is not None:
            assert strategy in SAMPLING_STRATEGIES, (
                f"strategy should be in {SAMPLING_STRATEGIES}. "
                f"Got '{strategy}'."
            )

        self.kwargs = kwargs
        self.strategy = strategy
        self.key_to_monitor = key_to_monitor
        if self.key_to_monitor is not None:
            self.key_to_monitor_ = (
                key_to_monitor if key_to_monitor.startswith('objective_')
                else f'objective_{key_to_monitor}'
            )
        else:
            self.key_to_monitor_ = None

    def get_runner_instance(self, max_runs=1, timeout=None, terminal=None,
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
        terminal : TerminalOutput or None
            Object to format string to display the progress of the solver.
        solver : BaseSolver
            The solver for which this stopping criterion is called. Used to get
            overridden ``sampling_strategy`` and ``get_next``.

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

        if self.strategy is None:
            if solver is None:
                self.strategy = 'iteration'
            else:
                self.strategy = solver.sampling_strategy or 'iteration'
        elif solver is not None and solver.sampling_strategy is not None:
            assert solver.sampling_strategy == self.strategy, (
                'The strategy is set both in Solver.sampling_strategy and in '
                'its criterion, and it does not match. Only set it once.'
            )

        # Create a new instance of the class
        stopping_criterion = self.__class__(
            strategy=self.strategy, key_to_monitor=self.key_to_monitor,
            **self.kwargs,
        )

        # Set stopping criterion parameters depending on run parameters
        stopping_criterion.rho = RHO
        stopping_criterion.timeout = timeout
        stopping_criterion.max_runs = max_runs
        stopping_criterion.terminal = terminal
        stopping_criterion.solver = solver

        # Override get_next_stop_val if ``get_next`` is implemented for solver.
        if hasattr(solver, 'get_next'):
            if not callable(solver.get_next):
                raise TypeError(
                    f"`get_next` of Solver in {solver.__module__} "
                    "must be callable."
                )

            try:
                solver.get_next(1)
            except TypeError:
                raise ValueError(
                    "get_next(1) throw a TypeError. Verify that `get_next` "
                    "signature is get_next(self, stop_val)"
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

    def should_stop(self, stop_val, objective_list):
        """Base call to check if we should stop running a solver.

        This base call checks for the timeout and the max number of runs.
        It also notifies the runner if the curve is too flat, to increase
        the number of points between 2 evaluations of the objective.

        Parameters
        ----------
        stop_val : int | float
            Corresponds to stopping criterion of the underlying algorithm, such
            as ``tol`` or ``max_iter``.
        objective_list : list of dict
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
            sampling strategy for the solver.
        """
        # Default state
        is_flat = False
        is_diverging = False
        stop = False
        status = 'running'

        # Modify the criterion state:
        # - compute the number of run with the curve. We need to remove 1 as
        #   it contains the initial evaluation.
        # - compute the delta_objective if the stopping_criterion monitors a
        #   given key, for debugging and stalled progress.
        n_eval = len(objective_list) - 1

        if self.key_to_monitor_ is not None:
            # Compatibility with the objective
            if self.key_to_monitor_ not in objective_list[0]:
                key = self.key_to_monitor_.replace("objective_", "")
                key_ok = [
                    k.replace("objective_", "") for k in objective_list[0]
                    if k.startswith("objective_") and k != 'objective_name'
                ]
                raise ValueError(
                    "Objective.evaluate_result() should contain a key named "
                    f"'{key}' to be used with this stopping_criterion. "
                    "The name of this key can be changed via the "
                    f"'key_to_monitor' parameter. Available keys are {key_ok}"
                )

            objective = objective_list[-1][self.key_to_monitor_]
            delta_objective = self._prev_objective - objective
            first_objective = objective_list[0][self.key_to_monitor_]
            if first_objective != 0:
                delta_objective /= abs(first_objective)
            self._prev_objective = objective

            is_diverging = math.isnan(objective) or delta_objective < -1e5
            is_flat = delta_objective == 0

        # check the different conditions:
        #     diverging / timeout / max_runs / stopping_criterion
        if is_diverging:
            stop = True
            status = 'diverged'
        elif self._deadline is not None and time.time() >= self._deadline:
            stop = True
            status = 'timeout'

        elif n_eval == self.max_runs:
            stop = True
            status = 'max_runs'
        else:
            # Call the sub-class hook, used to check stopping criterion
            # on the curve.
            stop, progress = self.check_convergence(objective_list)

            # Display the progress if necessary
            progress = max(n_eval / self.max_runs, progress)

            # Compute status and notify the runner if the curve is flat.
            status = 'done' if stop else 'running'

        if stop:
            suffix = ""
            if self.key_to_monitor_ is not None:
                suffix = f" with delta_objective = {delta_objective:.2e}"
            self.debug(f"Exit after {n_eval=:.1e}{suffix}.")
        elif is_flat:
            self.rho *= RHO_INC
            self.debug(f"curve is flat -> increasing rho: {self.rho}")

        if status == 'running':
            stop_val = self.get_next_stop_val(stop_val)
            self.debug(f"Calling with stop val: {stop_val}")
            self.progress(progress=progress)

        return stop, status, stop_val

    def check_convergence(self, objective_list):
        """Check if the solver should be stopped based on the objective curve.

        Parameters
        ----------
        objective_list : list of dict
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
        if self.terminal is not None:
            self.terminal.debug(msg)

    def progress(self, progress):
        """Helper to print progress messages."""
        if self.terminal is not None:
            self.terminal.progress(progress)

    @staticmethod
    def _reconstruct(klass, kwargs, runner_kwargs):
        criterion = klass(**kwargs)
        if runner_kwargs:
            return criterion.get_runner_instance(**runner_kwargs)
        return criterion

    def __reduce__(self):
        kwargs = dict(
            strategy=self.strategy, key_to_monitor=self.key_to_monitor,
            **self.kwargs
        )
        if getattr(self, 'max_runs', None):
            runner_kwargs = dict(
                max_runs=self.max_runs, timeout=self.timeout,
                terminal=self.terminal, solver=self.solver
            )
        else:
            runner_kwargs = None
        return self._reconstruct, (self.__class__, kwargs, runner_kwargs)

    def get_next_stop_val(self, stop_val):
        if self.strategy == "tolerance":
            return min(1, max(stop_val / self.rho, MIN_TOL))
        else:
            return max(stop_val + 1, min(int(self.rho * stop_val), MAX_ITER))


class SufficientDescentCriterion(StoppingCriterion):
    f"""Stopping criterion based on sufficient descent.

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
        updates.{COMMON_ARGS_DOC}
    """

    def __init__(self, eps=EPS, patience=PATIENCE, strategy=None,
                 key_to_monitor='value'):
        self.eps = eps
        self.patience = patience

        self._delta_objectives = []
        self._objective = 1e100

        super().__init__(
            eps=eps, patience=patience, strategy=strategy,
            key_to_monitor=key_to_monitor
        )

    def check_convergence(self, objective_list):
        """Check if the solver should be stopped based on the objective curve.

        Parameters
        ----------
        objective_list : list of dict
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
        objective = objective_list[-1][self.key_to_monitor_]
        delta_objective = self._objective - objective
        delta_objective /= abs(objective_list[0][self.key_to_monitor_])
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
    f"""Stopping criterion based on sufficient progress.

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
        updates.{COMMON_ARGS_DOC}
    """

    def __init__(self, eps=EPS, patience=PATIENCE, strategy=None,
                 key_to_monitor='value'):
        self.eps = eps
        self.patience = patience

        self._progress = []
        self._best_objective = 1e100

        super().__init__(
            eps=eps, patience=patience, strategy=strategy,
            key_to_monitor=key_to_monitor
        )

    def check_convergence(self, objective_list):
        """Check if the solver should be stopped based on the objective curve.

        Parameters
        ----------
        objective_list : list of dict
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
        objective = objective_list[-1][self.key_to_monitor_]
        delta_objective = self._best_objective - objective
        first_objective = objective_list[0][self.key_to_monitor_]
        if first_objective != 0:
            delta_objective /= abs(first_objective)
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


class SingleRunCriterion(StoppingCriterion):
    """Stopping criterion for single run solvers.

    The solver will be stopped after one call to the objective.

    Parameters
    ----------
    stop_val : int or float, (default: 1)
        Value of ``stop_val`` with which the objective function will be called.
        This value will be passed as ``n_iter`` or ``tol`` parameter for the
        ``run`` method of solver with ``sampling_strategy`` respectively equals
        to ``'iteration'`` or ``'tolerance'``, or the number of callback calls
        minus one for the ``'callback'`` strategy.
    """

    def __init__(self, stop_val=1, strategy=None, *args, **kwargs):
        # Necessary as the criterion is given a strategy argument when
        # instanciated for an instance.
        super().__init__(strategy=strategy, stop_val=stop_val)
        self.stop_val = stop_val

    def init_stop_val(self):
        return self.stop_val

    def get_runner_instance(self, max_runs=1, timeout=None, terminal=None,
                            solver=None):

        return super().get_runner_instance(1, timeout, terminal, solver)

    def should_stop(self, stop_val, objective_list):
        return True, 'done', stop_val


class NoCriterion(StoppingCriterion):
    """Run the solvers for a number of time fixed by max_iter and timeout.
    """

    def check_convergence(self, cost_curve):
        return False, 0
